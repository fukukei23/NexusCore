
# === NexusCore/openenv\Lib\site-packages\click\types.py ===
from __future__ import annotations

import collections.abc as cabc
import enum
import os
import stat
import sys
import typing as t
from datetime import datetime
from gettext import gettext as _
from gettext import ngettext

from ._compat import _get_argv_encoding
from ._compat import open_stream
from .exceptions import BadParameter
from .utils import format_filename
from .utils import LazyFile
from .utils import safecall

if t.TYPE_CHECKING:
    import typing_extensions as te

    from .core import Context
    from .core import Parameter
    from .shell_completion import CompletionItem

ParamTypeValue = t.TypeVar("ParamTypeValue")


class ParamType:
    """Represents the type of a parameter. Validates and converts values
    from the command line or Python into the correct type.

    To implement a custom type, subclass and implement at least the
    following:

    -   The :attr:`name` class attribute must be set.
    -   Calling an instance of the type with ``None`` must return
        ``None``. This is already implemented by default.
    -   :meth:`convert` must convert string values to the correct type.
    -   :meth:`convert` must accept values that are already the correct
        type.
    -   It must be able to convert a value if the ``ctx`` and ``param``
        arguments are ``None``. This can occur when converting prompt
        input.
    """

    is_composite: t.ClassVar[bool] = False
    arity: t.ClassVar[int] = 1

    #: the descriptive name of this type
    name: str

    #: if a list of this type is expected and the value is pulled from a
    #: string environment variable, this is what splits it up.  `None`
    #: means any whitespace.  For all parameters the general rule is that
    #: whitespace splits them up.  The exception are paths and files which
    #: are split by ``os.path.pathsep`` by default (":" on Unix and ";" on
    #: Windows).
    envvar_list_splitter: t.ClassVar[str | None] = None

    def to_info_dict(self) -> dict[str, t.Any]:
        """Gather information that could be useful for a tool generating
        user-facing documentation.

        Use :meth:`click.Context.to_info_dict` to traverse the entire
        CLI structure.

        .. versionadded:: 8.0
        """
        # The class name without the "ParamType" suffix.
        param_type = type(self).__name__.partition("ParamType")[0]
        param_type = param_type.partition("ParameterType")[0]

        # Custom subclasses might not remember to set a name.
        if hasattr(self, "name"):
            name = self.name
        else:
            name = param_type

        return {"param_type": param_type, "name": name}

    def __call__(
        self,
        value: t.Any,
        param: Parameter | None = None,
        ctx: Context | None = None,
    ) -> t.Any:
        if value is not None:
            return self.convert(value, param, ctx)

    def get_metavar(self, param: Parameter, ctx: Context) -> str | None:
        """Returns the metavar default for this param if it provides one."""

    def get_missing_message(self, param: Parameter, ctx: Context | None) -> str | None:
        """Optionally might return extra information about a missing
        parameter.

        .. versionadded:: 2.0
        """

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> t.Any:
        """Convert the value to the correct type. This is not called if
        the value is ``None`` (the missing value).

        This must accept string values from the command line, as well as
        values that are already the correct type. It may also convert
        other compatible types.

        The ``param`` and ``ctx`` arguments may be ``None`` in certain
        situations, such as when converting prompt input.

        If the value cannot be converted, call :meth:`fail` with a
        descriptive message.

        :param value: The value to convert.
        :param param: The parameter that is using this type to convert
            its value. May be ``None``.
        :param ctx: The current context that arrived at this value. May
            be ``None``.
        """
        return value

    def split_envvar_value(self, rv: str) -> cabc.Sequence[str]:
        """Given a value from an environment variable this splits it up
        into small chunks depending on the defined envvar list splitter.

        If the splitter is set to `None`, which means that whitespace splits,
        then leading and trailing whitespace is ignored.  Otherwise, leading
        and trailing splitters usually lead to empty items being included.
        """
        return (rv or "").split(self.envvar_list_splitter)

    def fail(
        self,
        message: str,
        param: Parameter | None = None,
        ctx: Context | None = None,
    ) -> t.NoReturn:
        """Helper method to fail with an invalid value message."""
        raise BadParameter(message, ctx=ctx, param=param)

    def shell_complete(
        self, ctx: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        """Return a list of
        :class:`~click.shell_completion.CompletionItem` objects for the
        incomplete value. Most types do not provide completions, but
        some do, and this allows custom types to provide custom
        completions as well.

        :param ctx: Invocation context for this command.
        :param param: The parameter that is requesting completion.
        :param incomplete: Value being completed. May be empty.

        .. versionadded:: 8.0
        """
        return []


class CompositeParamType(ParamType):
    is_composite = True

    @property
    def arity(self) -> int:  # type: ignore
        raise NotImplementedError()


class FuncParamType(ParamType):
    def __init__(self, func: t.Callable[[t.Any], t.Any]) -> None:
        self.name: str = func.__name__
        self.func = func

    def to_info_dict(self) -> dict[str, t.Any]:
        info_dict = super().to_info_dict()
        info_dict["func"] = self.func
        return info_dict

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> t.Any:
        try:
            return self.func(value)
        except ValueError:
            try:
                value = str(value)
            except UnicodeError:
                value = value.decode("utf-8", "replace")

            self.fail(value, param, ctx)


class UnprocessedParamType(ParamType):
    name = "text"

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> t.Any:
        return value

    def __repr__(self) -> str:
        return "UNPROCESSED"


class StringParamType(ParamType):
    name = "text"

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> t.Any:
        if isinstance(value, bytes):
            enc = _get_argv_encoding()
            try:
                value = value.decode(enc)
            except UnicodeError:
                fs_enc = sys.getfilesystemencoding()
                if fs_enc != enc:
                    try:
                        value = value.decode(fs_enc)
                    except UnicodeError:
                        value = value.decode("utf-8", "replace")
                else:
                    value = value.decode("utf-8", "replace")
            return value
        return str(value)

    def __repr__(self) -> str:
        return "STRING"


class Choice(ParamType, t.Generic[ParamTypeValue]):
    """The choice type allows a value to be checked against a fixed set
    of supported values.

    You may pass any iterable value which will be converted to a tuple
    and thus will only be iterated once.

    The resulting value will always be one of the originally passed choices.
    See :meth:`normalize_choice` for more info on the mapping of strings
    to choices. See :ref:`choice-opts` for an example.

    :param case_sensitive: Set to false to make choices case
        insensitive. Defaults to true.

    .. versionchanged:: 8.2.0
        Non-``str`` ``choices`` are now supported. It can additionally be any
        iterable. Before you were not recommended to pass anything but a list or
        tuple.

    .. versionadded:: 8.2.0
        Choice normalization can be overridden via :meth:`normalize_choice`.
    """

    name = "choice"

    def __init__(
        self, choices: cabc.Iterable[ParamTypeValue], case_sensitive: bool = True
    ) -> None:
        self.choices: cabc.Sequence[ParamTypeValue] = tuple(choices)
        self.case_sensitive = case_sensitive

    def to_info_dict(self) -> dict[str, t.Any]:
        info_dict = super().to_info_dict()
        info_dict["choices"] = self.choices
        info_dict["case_sensitive"] = self.case_sensitive
        return info_dict

    def _normalized_mapping(
        self, ctx: Context | None = None
    ) -> cabc.Mapping[ParamTypeValue, str]:
        """
        Returns mapping where keys are the original choices and the values are
        the normalized values that are accepted via the command line.

        This is a simple wrapper around :meth:`normalize_choice`, use that
        instead which is supported.
        """
        return {
            choice: self.normalize_choice(
                choice=choice,
                ctx=ctx,
            )
            for choice in self.choices
        }

    def normalize_choice(self, choice: ParamTypeValue, ctx: Context | None) -> str:
        """
        Normalize a choice value, used to map a passed string to a choice.
        Each choice must have a unique normalized value.

        By default uses :meth:`Context.token_normalize_func` and if not case
        sensitive, convert it to a casefolded value.

        .. versionadded:: 8.2.0
        """
        normed_value = choice.name if isinstance(choice, enum.Enum) else str(choice)

        if ctx is not None and ctx.token_normalize_func is not None:
            normed_value = ctx.token_normalize_func(normed_value)

        if not self.case_sensitive:
            normed_value = normed_value.casefold()

        return normed_value

    def get_metavar(self, param: Parameter, ctx: Context) -> str | None:
        if param.param_type_name == "option" and not param.show_choices:  # type: ignore
            choice_metavars = [
                convert_type(type(choice)).name.upper() for choice in self.choices
            ]
            choices_str = "|".join([*dict.fromkeys(choice_metavars)])
        else:
            choices_str = "|".join(
                [str(i) for i in self._normalized_mapping(ctx=ctx).values()]
            )

        # Use curly braces to indicate a required argument.
        if param.required and param.param_type_name == "argument":
            return f"{{{choices_str}}}"

        # Use square braces to indicate an option or optional argument.
        return f"[{choices_str}]"

    def get_missing_message(self, param: Parameter, ctx: Context | None) -> str:
        """
        Message shown when no choice is passed.

        .. versionchanged:: 8.2.0 Added ``ctx`` argument.
        """
        return _("Choose from:\n\t{choices}").format(
            choices=",\n\t".join(self._normalized_mapping(ctx=ctx).values())
        )

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> ParamTypeValue:
        """
        For a given value from the parser, normalize it and find its
        matching normalized value in the list of choices. Then return the
        matched "original" choice.
        """
        normed_value = self.normalize_choice(choice=value, ctx=ctx)
        normalized_mapping = self._normalized_mapping(ctx=ctx)

        try:
            return next(
                original
                for original, normalized in normalized_mapping.items()
                if normalized == normed_value
            )
        except StopIteration:
            self.fail(
                self.get_invalid_choice_message(value=value, ctx=ctx),
                param=param,
                ctx=ctx,
            )

    def get_invalid_choice_message(self, value: t.Any, ctx: Context | None) -> str:
        """Get the error message when the given choice is invalid.

        :param value: The invalid value.

        .. versionadded:: 8.2
        """
        choices_str = ", ".join(map(repr, self._normalized_mapping(ctx=ctx).values()))
        return ngettext(
            "{value!r} is not {choice}.",
            "{value!r} is not one of {choices}.",
            len(self.choices),
        ).format(value=value, choice=choices_str, choices=choices_str)

    def __repr__(self) -> str:
        return f"Choice({list(self.choices)})"

    def shell_complete(
        self, ctx: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        """Complete choices that start with the incomplete value.

        :param ctx: Invocation context for this command.
        :param param: The parameter that is requesting completion.
        :param incomplete: Value being completed. May be empty.

        .. versionadded:: 8.0
        """
        from click.shell_completion import CompletionItem

        str_choices = map(str, self.choices)

        if self.case_sensitive:
            matched = (c for c in str_choices if c.startswith(incomplete))
        else:
            incomplete = incomplete.lower()
            matched = (c for c in str_choices if c.lower().startswith(incomplete))

        return [CompletionItem(c) for c in matched]


class DateTime(ParamType):
    """The DateTime type converts date strings into `datetime` objects.

    The format strings which are checked are configurable, but default to some
    common (non-timezone aware) ISO 8601 formats.

    When specifying *DateTime* formats, you should only pass a list or a tuple.
    Other iterables, like generators, may lead to surprising results.

    The format strings are processed using ``datetime.strptime``, and this
    consequently defines the format strings which are allowed.

    Parsing is tried using each format, in order, and the first format which
    parses successfully is used.

    :param formats: A list or tuple of date format strings, in the order in
                    which they should be tried. Defaults to
                    ``'%Y-%m-%d'``, ``'%Y-%m-%dT%H:%M:%S'``,
                    ``'%Y-%m-%d %H:%M:%S'``.
    """

    name = "datetime"

    def __init__(self, formats: cabc.Sequence[str] | None = None):
        self.formats: cabc.Sequence[str] = formats or [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]

    def to_info_dict(self) -> dict[str, t.Any]:
        info_dict = super().to_info_dict()
        info_dict["formats"] = self.formats
        return info_dict

    def get_metavar(self, param: Parameter, ctx: Context) -> str | None:
        return f"[{'|'.join(self.formats)}]"

    def _try_to_convert_date(self, value: t.Any, format: str) -> datetime | None:
        try:
            return datetime.strptime(value, format)
        except ValueError:
            return None

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> t.Any:
        if isinstance(value, datetime):
            return value

        for format in self.formats:
            converted = self._try_to_convert_date(value, format)

            if converted is not None:
                return converted

        formats_str = ", ".join(map(repr, self.formats))
        self.fail(
            ngettext(
                "{value!r} does not match the format {format}.",
                "{value!r} does not match the formats {formats}.",
                len(self.formats),
            ).format(value=value, format=formats_str, formats=formats_str),
            param,
            ctx,
        )

    def __repr__(self) -> str:
        return "DateTime"


class _NumberParamTypeBase(ParamType):
    _number_class: t.ClassVar[type[t.Any]]

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> t.Any:
        try:
            return self._number_class(value)
        except ValueError:
            self.fail(
                _("{value!r} is not a valid {number_type}.").format(
                    value=value, number_type=self.name
                ),
                param,
                ctx,
            )


class _NumberRangeBase(_NumberParamTypeBase):
    def __init__(
        self,
        min: float | None = None,
        max: float | None = None,
        min_open: bool = False,
        max_open: bool = False,
        clamp: bool = False,
    ) -> None:
        self.min = min
        self.max = max
        self.min_open = min_open
        self.max_open = max_open
        self.clamp = clamp

    def to_info_dict(self) -> dict[str, t.Any]:
        info_dict = super().to_info_dict()
        info_dict.update(
            min=self.min,
            max=self.max,
            min_open=self.min_open,
            max_open=self.max_open,
            clamp=self.clamp,
        )
        return info_dict

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> t.Any:
        import operator

        rv = super().convert(value, param, ctx)
        lt_min: bool = self.min is not None and (
            operator.le if self.min_open else operator.lt
        )(rv, self.min)
        gt_max: bool = self.max is not None and (
            operator.ge if self.max_open else operator.gt
        )(rv, self.max)

        if self.clamp:
            if lt_min:
                return self._clamp(self.min, 1, self.min_open)  # type: ignore

            if gt_max:
                return self._clamp(self.max, -1, self.max_open)  # type: ignore

        if lt_min or gt_max:
            self.fail(
                _("{value} is not in the range {range}.").format(
                    value=rv, range=self._describe_range()
                ),
                param,
                ctx,
            )

        return rv

    def _clamp(self, bound: float, dir: t.Literal[1, -1], open: bool) -> float:
        """Find the valid value to clamp to bound in the given
        direction.

        :param bound: The boundary value.
        :param dir: 1 or -1 indicating the direction to move.
        :param open: If true, the range does not include the bound.
        """
        raise NotImplementedError

    def _describe_range(self) -> str:
        """Describe the range for use in help text."""
        if self.min is None:
            op = "<" if self.max_open else "<="
            return f"x{op}{self.max}"

        if self.max is None:
            op = ">" if self.min_open else ">="
            return f"x{op}{self.min}"

        lop = "<" if self.min_open else "<="
        rop = "<" if self.max_open else "<="
        return f"{self.min}{lop}x{rop}{self.max}"

    def __repr__(self) -> str:
        clamp = " clamped" if self.clamp else ""
        return f"<{type(self).__name__} {self._describe_range()}{clamp}>"


class IntParamType(_NumberParamTypeBase):
    name = "integer"
    _number_class = int

    def __repr__(self) -> str:
        return "INT"


class IntRange(_NumberRangeBase, IntParamType):
    """Restrict an :data:`click.INT` value to a range of accepted
    values. See :ref:`ranges`.

    If ``min`` or ``max`` are not passed, any value is accepted in that
    direction. If ``min_open`` or ``max_open`` are enabled, the
    corresponding boundary is not included in the range.

    If ``clamp`` is enabled, a value outside the range is clamped to the
    boundary instead of failing.

    .. versionchanged:: 8.0
        Added the ``min_open`` and ``max_open`` parameters.
    """

    name = "integer range"

    def _clamp(  # type: ignore
        self, bound: int, dir: t.Literal[1, -1], open: bool
    ) -> int:
        if not open:
            return bound

        return bound + dir


class FloatParamType(_NumberParamTypeBase):
    name = "float"
    _number_class = float

    def __repr__(self) -> str:
        return "FLOAT"


class FloatRange(_NumberRangeBase, FloatParamType):
    """Restrict a :data:`click.FLOAT` value to a range of accepted
    values. See :ref:`ranges`.

    If ``min`` or ``max`` are not passed, any value is accepted in that
    direction. If ``min_open`` or ``max_open`` are enabled, the
    corresponding boundary is not included in the range.

    If ``clamp`` is enabled, a value outside the range is clamped to the
    boundary instead of failing. This is not supported if either
    boundary is marked ``open``.

    .. versionchanged:: 8.0
        Added the ``min_open`` and ``max_open`` parameters.
    """

    name = "float range"

    def __init__(
        self,
        min: float | None = None,
        max: float | None = None,
        min_open: bool = False,
        max_open: bool = False,
        clamp: bool = False,
    ) -> None:
        super().__init__(
            min=min, max=max, min_open=min_open, max_open=max_open, clamp=clamp
        )

        if (min_open or max_open) and clamp:
            raise TypeError("Clamping is not supported for open bounds.")

    def _clamp(self, bound: float, dir: t.Literal[1, -1], open: bool) -> float:
        if not open:
            return bound

        # Could use math.nextafter here, but clamping an
        # open float range doesn't seem to be particularly useful. It's
        # left up to the user to write a callback to do it if needed.
        raise RuntimeError("Clamping is not supported for open bounds.")


class BoolParamType(ParamType):
    name = "boolean"

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> t.Any:
        if value in {False, True}:
            return bool(value)

        norm = value.strip().lower()

        if norm in {"1", "true", "t", "yes", "y", "on"}:
            return True

        if norm in {"0", "false", "f", "no", "n", "off"}:
            return False

        self.fail(
            _("{value!r} is not a valid boolean.").format(value=value), param, ctx
        )

    def __repr__(self) -> str:
        return "BOOL"


class UUIDParameterType(ParamType):
    name = "uuid"

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> t.Any:
        import uuid

        if isinstance(value, uuid.UUID):
            return value

        value = value.strip()

        try:
            return uuid.UUID(value)
        except ValueError:
            self.fail(
                _("{value!r} is not a valid UUID.").format(value=value), param, ctx
            )

    def __repr__(self) -> str:
        return "UUID"


class File(ParamType):
    """Declares a parameter to be a file for reading or writing.  The file
    is automatically closed once the context tears down (after the command
    finished working).

    Files can be opened for reading or writing.  The special value ``-``
    indicates stdin or stdout depending on the mode.

    By default, the file is opened for reading text data, but it can also be
    opened in binary mode or for writing.  The encoding parameter can be used
    to force a specific encoding.

    The `lazy` flag controls if the file should be opened immediately or upon
    first IO. The default is to be non-lazy for standard input and output
    streams as well as files opened for reading, `lazy` otherwise. When opening a
    file lazily for reading, it is still opened temporarily for validation, but
    will not be held open until first IO. lazy is mainly useful when opening
    for writing to avoid creating the file until it is needed.

    Files can also be opened atomically in which case all writes go into a
    separate file in the same folder and upon completion the file will
    be moved over to the original location.  This is useful if a file
    regularly read by other users is modified.

    See :ref:`file-args` for more information.

    .. versionchanged:: 2.0
        Added the ``atomic`` parameter.
    """

    name = "filename"
    envvar_list_splitter: t.ClassVar[str] = os.path.pathsep

    def __init__(
        self,
        mode: str = "r",
        encoding: str | None = None,
        errors: str | None = "strict",
        lazy: bool | None = None,
        atomic: bool = False,
    ) -> None:
        self.mode = mode
        self.encoding = encoding
        self.errors = errors
        self.lazy = lazy
        self.atomic = atomic

    def to_info_dict(self) -> dict[str, t.Any]:
        info_dict = super().to_info_dict()
        info_dict.update(mode=self.mode, encoding=self.encoding)
        return info_dict

    def resolve_lazy_flag(self, value: str | os.PathLike[str]) -> bool:
        if self.lazy is not None:
            return self.lazy
        if os.fspath(value) == "-":
            return False
        elif "w" in self.mode:
            return True
        return False

    def convert(
        self,
        value: str | os.PathLike[str] | t.IO[t.Any],
        param: Parameter | None,
        ctx: Context | None,
    ) -> t.IO[t.Any]:
        if _is_file_like(value):
            return value

        value = t.cast("str | os.PathLike[str]", value)

        try:
            lazy = self.resolve_lazy_flag(value)

            if lazy:
                lf = LazyFile(
                    value, self.mode, self.encoding, self.errors, atomic=self.atomic
                )

                if ctx is not None:
                    ctx.call_on_close(lf.close_intelligently)

                return t.cast("t.IO[t.Any]", lf)

            f, should_close = open_stream(
                value, self.mode, self.encoding, self.errors, atomic=self.atomic
            )

            # If a context is provided, we automatically close the file
            # at the end of the context execution (or flush out).  If a
            # context does not exist, it's the caller's responsibility to
            # properly close the file.  This for instance happens when the
            # type is used with prompts.
            if ctx is not None:
                if should_close:
                    ctx.call_on_close(safecall(f.close))
                else:
                    ctx.call_on_close(safecall(f.flush))

            return f
        except OSError as e:
            self.fail(f"'{format_filename(value)}': {e.strerror}", param, ctx)

    def shell_complete(
        self, ctx: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        """Return a special completion marker that tells the completion
        system to use the shell to provide file path completions.

        :param ctx: Invocation context for this command.
        :param param: The parameter that is requesting completion.
        :param incomplete: Value being completed. May be empty.

        .. versionadded:: 8.0
        """
        from click.shell_completion import CompletionItem

        return [CompletionItem(incomplete, type="file")]


def _is_file_like(value: t.Any) -> te.TypeGuard[t.IO[t.Any]]:
    return hasattr(value, "read") or hasattr(value, "write")


class Path(ParamType):
    """The ``Path`` type is similar to the :class:`File` type, but
    returns the filename instead of an open file. Various checks can be
    enabled to validate the type of file and permissions.

    :param exists: The file or directory needs to exist for the value to
        be valid. If this is not set to ``True``, and the file does not
        exist, then all further checks are silently skipped.
    :param file_okay: Allow a file as a value.
    :param dir_okay: Allow a directory as a value.
    :param readable: if true, a readable check is performed.
    :param writable: if true, a writable check is performed.
    :param executable: if true, an executable check is performed.
    :param resolve_path: Make the value absolute and resolve any
        symlinks. A ``~`` is not expanded, as this is supposed to be
        done by the shell only.
    :param allow_dash: Allow a single dash as a value, which indicates
        a standard stream (but does not open it). Use
        :func:`~click.open_file` to handle opening this value.
    :param path_type: Convert the incoming path value to this type. If
        ``None``, keep Python's default, which is ``str``. Useful to
        convert to :class:`pathlib.Path`.

    .. versionchanged:: 8.1
        Added the ``executable`` parameter.

    .. versionchanged:: 8.0
        Allow passing ``path_type=pathlib.Path``.

    .. versionchanged:: 6.0
        Added the ``allow_dash`` parameter.
    """

    envvar_list_splitter: t.ClassVar[str] = os.path.pathsep

    def __init__(
        self,
        exists: bool = False,
        file_okay: bool = True,
        dir_okay: bool = True,
        writable: bool = False,
        readable: bool = True,
        resolve_path: bool = False,
        allow_dash: bool = False,
        path_type: type[t.Any] | None = None,
        executable: bool = False,
    ):
        self.exists = exists
        self.file_okay = file_okay
        self.dir_okay = dir_okay
        self.readable = readable
        self.writable = writable
        self.executable = executable
        self.resolve_path = resolve_path
        self.allow_dash = allow_dash
        self.type = path_type

        if self.file_okay and not self.dir_okay:
            self.name: str = _("file")
        elif self.dir_okay and not self.file_okay:
            self.name = _("directory")
        else:
            self.name = _("path")

    def to_info_dict(self) -> dict[str, t.Any]:
        info_dict = super().to_info_dict()
        info_dict.update(
            exists=self.exists,
            file_okay=self.file_okay,
            dir_okay=self.dir_okay,
            writable=self.writable,
            readable=self.readable,
            allow_dash=self.allow_dash,
        )
        return info_dict

    def coerce_path_result(
        self, value: str | os.PathLike[str]
    ) -> str | bytes | os.PathLike[str]:
        if self.type is not None and not isinstance(value, self.type):
            if self.type is str:
                return os.fsdecode(value)
            elif self.type is bytes:
                return os.fsencode(value)
            else:
                return t.cast("os.PathLike[str]", self.type(value))

        return value

    def convert(
        self,
        value: str | os.PathLike[str],
        param: Parameter | None,
        ctx: Context | None,
    ) -> str | bytes | os.PathLike[str]:
        rv = value

        is_dash = self.file_okay and self.allow_dash and rv in (b"-", "-")

        if not is_dash:
            if self.resolve_path:
                rv = os.path.realpath(rv)

            try:
                st = os.stat(rv)
            except OSError:
                if not self.exists:
                    return self.coerce_path_result(rv)
                self.fail(
                    _("{name} {filename!r} does not exist.").format(
                        name=self.name.title(), filename=format_filename(value)
                    ),
                    param,
                    ctx,
                )

            if not self.file_okay and stat.S_ISREG(st.st_mode):
                self.fail(
                    _("{name} {filename!r} is a file.").format(
                        name=self.name.title(), filename=format_filename(value)
                    ),
                    param,
                    ctx,
                )
            if not self.dir_okay and stat.S_ISDIR(st.st_mode):
                self.fail(
                    _("{name} {filename!r} is a directory.").format(
                        name=self.name.title(), filename=format_filename(value)
                    ),
                    param,
                    ctx,
                )

            if self.readable and not os.access(rv, os.R_OK):
                self.fail(
                    _("{name} {filename!r} is not readable.").format(
                        name=self.name.title(), filename=format_filename(value)
                    ),
                    param,
                    ctx,
                )

            if self.writable and not os.access(rv, os.W_OK):
                self.fail(
                    _("{name} {filename!r} is not writable.").format(
                        name=self.name.title(), filename=format_filename(value)
                    ),
                    param,
                    ctx,
                )

            if self.executable and not os.access(value, os.X_OK):
                self.fail(
                    _("{name} {filename!r} is not executable.").format(
                        name=self.name.title(), filename=format_filename(value)
                    ),
                    param,
                    ctx,
                )

        return self.coerce_path_result(rv)

    def shell_complete(
        self, ctx: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        """Return a special completion marker that tells the completion
        system to use the shell to provide path completions for only
        directories or any paths.

        :param ctx: Invocation context for this command.
        :param param: The parameter that is requesting completion.
        :param incomplete: Value being completed. May be empty.

        .. versionadded:: 8.0
        """
        from click.shell_completion import CompletionItem

        type = "dir" if self.dir_okay and not self.file_okay else "file"
        return [CompletionItem(incomplete, type=type)]


class Tuple(CompositeParamType):
    """The default behavior of Click is to apply a type on a value directly.
    This works well in most cases, except for when `nargs` is set to a fixed
    count and different types should be used for different items.  In this
    case the :class:`Tuple` type can be used.  This type can only be used
    if `nargs` is set to a fixed number.

    For more information see :ref:`tuple-type`.

    This can be selected by using a Python tuple literal as a type.

    :param types: a list of types that should be used for the tuple items.
    """

    def __init__(self, types: cabc.Sequence[type[t.Any] | ParamType]) -> None:
        self.types: cabc.Sequence[ParamType] = [convert_type(ty) for ty in types]

    def to_info_dict(self) -> dict[str, t.Any]:
        info_dict = super().to_info_dict()
        info_dict["types"] = [t.to_info_dict() for t in self.types]
        return info_dict

    @property
    def name(self) -> str:  # type: ignore
        return f"<{' '.join(ty.name for ty in self.types)}>"

    @property
    def arity(self) -> int:  # type: ignore
        return len(self.types)

    def convert(
        self, value: t.Any, param: Parameter | None, ctx: Context | None
    ) -> t.Any:
        len_type = len(self.types)
        len_value = len(value)

        if len_value != len_type:
            self.fail(
                ngettext(
                    "{len_type} values are required, but {len_value} was given.",
                    "{len_type} values are required, but {len_value} were given.",
                    len_value,
                ).format(len_type=len_type, len_value=len_value),
                param=param,
                ctx=ctx,
            )

        return tuple(
            ty(x, param, ctx) for ty, x in zip(self.types, value, strict=False)
        )


def convert_type(ty: t.Any | None, default: t.Any | None = None) -> ParamType:
    """Find the most appropriate :class:`ParamType` for the given Python
    type. If the type isn't provided, it can be inferred from a default
    value.
    """
    guessed_type = False

    if ty is None and default is not None:
        if isinstance(default, (tuple, list)):
            # If the default is empty, ty will remain None and will
            # return STRING.
            if default:
                item = default[0]

                # A tuple of tuples needs to detect the inner types.
                # Can't call convert recursively because that would
                # incorrectly unwind the tuple to a single type.
                if isinstance(item, (tuple, list)):
                    ty = tuple(map(type, item))
                else:
                    ty = type(item)
        else:
            ty = type(default)

        guessed_type = True

    if isinstance(ty, tuple):
        return Tuple(ty)

    if isinstance(ty, ParamType):
        return ty

    if ty is str or ty is None:
        return STRING

    if ty is int:
        return INT

    if ty is float:
        return FLOAT

    if ty is bool:
        return BOOL

    if guessed_type:
        return STRING

    if __debug__:
        try:
            if issubclass(ty, ParamType):
                raise AssertionError(
                    f"Attempted to use an uninstantiated parameter type ({ty})."
                )
        except TypeError:
            # ty is an instance (correct), so issubclass fails.
            pass

    return FuncParamType(ty)


#: A dummy parameter type that just does nothing.  From a user's
#: perspective this appears to just be the same as `STRING` but
#: internally no string conversion takes place if the input was bytes.
#: This is usually useful when working with file paths as they can
#: appear in bytes and unicode.
#:
#: For path related uses the :class:`Path` type is a better choice but
#: there are situations where an unprocessed type is useful which is why
#: it is is provided.
#:
#: .. versionadded:: 4.0
UNPROCESSED = UnprocessedParamType()

#: A unicode string parameter type which is the implicit default.  This
#: can also be selected by using ``str`` as type.
STRING = StringParamType()

#: An integer parameter.  This can also be selected by using ``int`` as
#: type.
INT = IntParamType()

#: A floating point value parameter.  This can also be selected by using
#: ``float`` as type.
FLOAT = FloatParamType()

#: A boolean parameter.  This is the default for boolean flags.  This can
#: also be selected by using ``bool`` as a type.
BOOL = BoolParamType()

#: A UUID parameter.
UUID = UUIDParameterType()


class OptionHelpExtra(t.TypedDict, total=False):
    envvars: tuple[str, ...]
    default: str
    range: str
    required: str

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\schema.py ===
import re
import warnings
from collections import defaultdict
from dataclasses import is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    ForwardRef,
    FrozenSet,
    Generic,
    Iterable,
    List,
    Optional,
    Pattern,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

from typing_extensions import Annotated, Literal

from pydantic.v1.fields import (
    MAPPING_LIKE_SHAPES,
    SHAPE_DEQUE,
    SHAPE_FROZENSET,
    SHAPE_GENERIC,
    SHAPE_ITERABLE,
    SHAPE_LIST,
    SHAPE_SEQUENCE,
    SHAPE_SET,
    SHAPE_SINGLETON,
    SHAPE_TUPLE,
    SHAPE_TUPLE_ELLIPSIS,
    FieldInfo,
    ModelField,
)
from pydantic.v1.json import pydantic_encoder
from pydantic.v1.networks import AnyUrl, EmailStr
from pydantic.v1.types import (
    ConstrainedDecimal,
    ConstrainedFloat,
    ConstrainedFrozenSet,
    ConstrainedInt,
    ConstrainedList,
    ConstrainedSet,
    ConstrainedStr,
    SecretBytes,
    SecretStr,
    StrictBytes,
    StrictStr,
    conbytes,
    condecimal,
    confloat,
    confrozenset,
    conint,
    conlist,
    conset,
    constr,
)
from pydantic.v1.typing import (
    all_literal_values,
    get_args,
    get_origin,
    get_sub_types,
    is_callable_type,
    is_literal_type,
    is_namedtuple,
    is_none_type,
    is_union,
)
from pydantic.v1.utils import ROOT_KEY, get_model, lenient_issubclass

if TYPE_CHECKING:
    from pydantic.v1.dataclasses import Dataclass
    from pydantic.v1.main import BaseModel

default_prefix = '#/definitions/'
default_ref_template = '#/definitions/{model}'

TypeModelOrEnum = Union[Type['BaseModel'], Type[Enum]]
TypeModelSet = Set[TypeModelOrEnum]


def _apply_modify_schema(
    modify_schema: Callable[..., None], field: Optional[ModelField], field_schema: Dict[str, Any]
) -> None:
    from inspect import signature

    sig = signature(modify_schema)
    args = set(sig.parameters.keys())
    if 'field' in args or 'kwargs' in args:
        modify_schema(field_schema, field=field)
    else:
        modify_schema(field_schema)


def schema(
    models: Sequence[Union[Type['BaseModel'], Type['Dataclass']]],
    *,
    by_alias: bool = True,
    title: Optional[str] = None,
    description: Optional[str] = None,
    ref_prefix: Optional[str] = None,
    ref_template: str = default_ref_template,
) -> Dict[str, Any]:
    """
    Process a list of models and generate a single JSON Schema with all of them defined in the ``definitions``
    top-level JSON key, including their sub-models.

    :param models: a list of models to include in the generated JSON Schema
    :param by_alias: generate the schemas using the aliases defined, if any
    :param title: title for the generated schema that includes the definitions
    :param description: description for the generated schema
    :param ref_prefix: the JSON Pointer prefix for schema references with ``$ref``, if None, will be set to the
      default of ``#/definitions/``. Update it if you want the schemas to reference the definitions somewhere
      else, e.g. for OpenAPI use ``#/components/schemas/``. The resulting generated schemas will still be at the
      top-level key ``definitions``, so you can extract them from there. But all the references will have the set
      prefix.
    :param ref_template: Use a ``string.format()`` template for ``$ref`` instead of a prefix. This can be useful
      for references that cannot be represented by ``ref_prefix`` such as a definition stored in another file. For
      a sibling json file in a ``/schemas`` directory use ``"/schemas/${model}.json#"``.
    :return: dict with the JSON Schema with a ``definitions`` top-level key including the schema definitions for
      the models and sub-models passed in ``models``.
    """
    clean_models = [get_model(model) for model in models]
    flat_models = get_flat_models_from_models(clean_models)
    model_name_map = get_model_name_map(flat_models)
    definitions = {}
    output_schema: Dict[str, Any] = {}
    if title:
        output_schema['title'] = title
    if description:
        output_schema['description'] = description
    for model in clean_models:
        m_schema, m_definitions, m_nested_models = model_process_schema(
            model,
            by_alias=by_alias,
            model_name_map=model_name_map,
            ref_prefix=ref_prefix,
            ref_template=ref_template,
        )
        definitions.update(m_definitions)
        model_name = model_name_map[model]
        definitions[model_name] = m_schema
    if definitions:
        output_schema['definitions'] = definitions
    return output_schema


def model_schema(
    model: Union[Type['BaseModel'], Type['Dataclass']],
    by_alias: bool = True,
    ref_prefix: Optional[str] = None,
    ref_template: str = default_ref_template,
) -> Dict[str, Any]:
    """
    Generate a JSON Schema for one model. With all the sub-models defined in the ``definitions`` top-level
    JSON key.

    :param model: a Pydantic model (a class that inherits from BaseModel)
    :param by_alias: generate the schemas using the aliases defined, if any
    :param ref_prefix: the JSON Pointer prefix for schema references with ``$ref``, if None, will be set to the
      default of ``#/definitions/``. Update it if you want the schemas to reference the definitions somewhere
      else, e.g. for OpenAPI use ``#/components/schemas/``. The resulting generated schemas will still be at the
      top-level key ``definitions``, so you can extract them from there. But all the references will have the set
      prefix.
    :param ref_template: Use a ``string.format()`` template for ``$ref`` instead of a prefix. This can be useful for
      references that cannot be represented by ``ref_prefix`` such as a definition stored in another file. For a
      sibling json file in a ``/schemas`` directory use ``"/schemas/${model}.json#"``.
    :return: dict with the JSON Schema for the passed ``model``
    """
    model = get_model(model)
    flat_models = get_flat_models_from_model(model)
    model_name_map = get_model_name_map(flat_models)
    model_name = model_name_map[model]
    m_schema, m_definitions, nested_models = model_process_schema(
        model, by_alias=by_alias, model_name_map=model_name_map, ref_prefix=ref_prefix, ref_template=ref_template
    )
    if model_name in nested_models:
        # model_name is in Nested models, it has circular references
        m_definitions[model_name] = m_schema
        m_schema = get_schema_ref(model_name, ref_prefix, ref_template, False)
    if m_definitions:
        m_schema.update({'definitions': m_definitions})
    return m_schema


def get_field_info_schema(field: ModelField, schema_overrides: bool = False) -> Tuple[Dict[str, Any], bool]:
    # If no title is explicitly set, we don't set title in the schema for enums.
    # The behaviour is the same as `BaseModel` reference, where the default title
    # is in the definitions part of the schema.
    schema_: Dict[str, Any] = {}
    if field.field_info.title or not lenient_issubclass(field.type_, Enum):
        schema_['title'] = field.field_info.title or field.alias.title().replace('_', ' ')

    if field.field_info.title:
        schema_overrides = True

    if field.field_info.description:
        schema_['description'] = field.field_info.description
        schema_overrides = True

    if not field.required and field.default is not None and not is_callable_type(field.outer_type_):
        schema_['default'] = encode_default(field.default)
        schema_overrides = True

    return schema_, schema_overrides


def field_schema(
    field: ModelField,
    *,
    by_alias: bool = True,
    model_name_map: Dict[TypeModelOrEnum, str],
    ref_prefix: Optional[str] = None,
    ref_template: str = default_ref_template,
    known_models: Optional[TypeModelSet] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Set[str]]:
    """
    Process a Pydantic field and return a tuple with a JSON Schema for it as the first item.
    Also return a dictionary of definitions with models as keys and their schemas as values. If the passed field
    is a model and has sub-models, and those sub-models don't have overrides (as ``title``, ``default``, etc), they
    will be included in the definitions and referenced in the schema instead of included recursively.

    :param field: a Pydantic ``ModelField``
    :param by_alias: use the defined alias (if any) in the returned schema
    :param model_name_map: used to generate the JSON Schema references to other models included in the definitions
    :param ref_prefix: the JSON Pointer prefix to use for references to other schemas, if None, the default of
      #/definitions/ will be used
    :param ref_template: Use a ``string.format()`` template for ``$ref`` instead of a prefix. This can be useful for
      references that cannot be represented by ``ref_prefix`` such as a definition stored in another file. For a
      sibling json file in a ``/schemas`` directory use ``"/schemas/${model}.json#"``.
    :param known_models: used to solve circular references
    :return: tuple of the schema for this field and additional definitions
    """
    s, schema_overrides = get_field_info_schema(field)

    validation_schema = get_field_schema_validations(field)
    if validation_schema:
        s.update(validation_schema)
        schema_overrides = True

    f_schema, f_definitions, f_nested_models = field_type_schema(
        field,
        by_alias=by_alias,
        model_name_map=model_name_map,
        schema_overrides=schema_overrides,
        ref_prefix=ref_prefix,
        ref_template=ref_template,
        known_models=known_models or set(),
    )

    # $ref will only be returned when there are no schema_overrides
    if '$ref' in f_schema:
        return f_schema, f_definitions, f_nested_models
    else:
        s.update(f_schema)
        return s, f_definitions, f_nested_models


numeric_types = (int, float, Decimal)
_str_types_attrs: Tuple[Tuple[str, Union[type, Tuple[type, ...]], str], ...] = (
    ('max_length', numeric_types, 'maxLength'),
    ('min_length', numeric_types, 'minLength'),
    ('regex', str, 'pattern'),
)

_numeric_types_attrs: Tuple[Tuple[str, Union[type, Tuple[type, ...]], str], ...] = (
    ('gt', numeric_types, 'exclusiveMinimum'),
    ('lt', numeric_types, 'exclusiveMaximum'),
    ('ge', numeric_types, 'minimum'),
    ('le', numeric_types, 'maximum'),
    ('multiple_of', numeric_types, 'multipleOf'),
)


def get_field_schema_validations(field: ModelField) -> Dict[str, Any]:
    """
    Get the JSON Schema validation keywords for a ``field`` with an annotation of
    a Pydantic ``FieldInfo`` with validation arguments.
    """
    f_schema: Dict[str, Any] = {}

    if lenient_issubclass(field.type_, Enum):
        # schema is already updated by `enum_process_schema`; just update with field extra
        if field.field_info.extra:
            f_schema.update(field.field_info.extra)
        return f_schema

    if lenient_issubclass(field.type_, (str, bytes)):
        for attr_name, t, keyword in _str_types_attrs:
            attr = getattr(field.field_info, attr_name, None)
            if isinstance(attr, t):
                f_schema[keyword] = attr
    if lenient_issubclass(field.type_, numeric_types) and not issubclass(field.type_, bool):
        for attr_name, t, keyword in _numeric_types_attrs:
            attr = getattr(field.field_info, attr_name, None)
            if isinstance(attr, t):
                f_schema[keyword] = attr
    if field.field_info is not None and field.field_info.const:
        f_schema['const'] = field.default
    if field.field_info.extra:
        f_schema.update(field.field_info.extra)
    modify_schema = getattr(field.outer_type_, '__modify_schema__', None)
    if modify_schema:
        _apply_modify_schema(modify_schema, field, f_schema)
    return f_schema


def get_model_name_map(unique_models: TypeModelSet) -> Dict[TypeModelOrEnum, str]:
    """
    Process a set of models and generate unique names for them to be used as keys in the JSON Schema
    definitions. By default the names are the same as the class name. But if two models in different Python
    modules have the same name (e.g. "users.Model" and "items.Model"), the generated names will be
    based on the Python module path for those conflicting models to prevent name collisions.

    :param unique_models: a Python set of models
    :return: dict mapping models to names
    """
    name_model_map = {}
    conflicting_names: Set[str] = set()
    for model in unique_models:
        model_name = normalize_name(model.__name__)
        if model_name in conflicting_names:
            model_name = get_long_model_name(model)
            name_model_map[model_name] = model
        elif model_name in name_model_map:
            conflicting_names.add(model_name)
            conflicting_model = name_model_map.pop(model_name)
            name_model_map[get_long_model_name(conflicting_model)] = conflicting_model
            name_model_map[get_long_model_name(model)] = model
        else:
            name_model_map[model_name] = model
    return {v: k for k, v in name_model_map.items()}


def get_flat_models_from_model(model: Type['BaseModel'], known_models: Optional[TypeModelSet] = None) -> TypeModelSet:
    """
    Take a single ``model`` and generate a set with itself and all the sub-models in the tree. I.e. if you pass
    model ``Foo`` (subclass of Pydantic ``BaseModel``) as ``model``, and it has a field of type ``Bar`` (also
    subclass of ``BaseModel``) and that model ``Bar`` has a field of type ``Baz`` (also subclass of ``BaseModel``),
    the return value will be ``set([Foo, Bar, Baz])``.

    :param model: a Pydantic ``BaseModel`` subclass
    :param known_models: used to solve circular references
    :return: a set with the initial model and all its sub-models
    """
    known_models = known_models or set()
    flat_models: TypeModelSet = set()
    flat_models.add(model)
    known_models |= flat_models
    fields = cast(Sequence[ModelField], model.__fields__.values())
    flat_models |= get_flat_models_from_fields(fields, known_models=known_models)
    return flat_models


def get_flat_models_from_field(field: ModelField, known_models: TypeModelSet) -> TypeModelSet:
    """
    Take a single Pydantic ``ModelField`` (from a model) that could have been declared as a subclass of BaseModel
    (so, it could be a submodel), and generate a set with its model and all the sub-models in the tree.
    I.e. if you pass a field that was declared to be of type ``Foo`` (subclass of BaseModel) as ``field``, and that
    model ``Foo`` has a field of type ``Bar`` (also subclass of ``BaseModel``) and that model ``Bar`` has a field of
    type ``Baz`` (also subclass of ``BaseModel``), the return value will be ``set([Foo, Bar, Baz])``.

    :param field: a Pydantic ``ModelField``
    :param known_models: used to solve circular references
    :return: a set with the model used in the declaration for this field, if any, and all its sub-models
    """
    from pydantic.v1.main import BaseModel

    flat_models: TypeModelSet = set()

    field_type = field.type_
    if lenient_issubclass(getattr(field_type, '__pydantic_model__', None), BaseModel):
        field_type = field_type.__pydantic_model__

    if field.sub_fields and not lenient_issubclass(field_type, BaseModel):
        flat_models |= get_flat_models_from_fields(field.sub_fields, known_models=known_models)
    elif lenient_issubclass(field_type, BaseModel) and field_type not in known_models:
        flat_models |= get_flat_models_from_model(field_type, known_models=known_models)
    elif lenient_issubclass(field_type, Enum):
        flat_models.add(field_type)
    return flat_models


def get_flat_models_from_fields(fields: Sequence[ModelField], known_models: TypeModelSet) -> TypeModelSet:
    """
    Take a list of Pydantic  ``ModelField``s (from a model) that could have been declared as subclasses of ``BaseModel``
    (so, any of them could be a submodel), and generate a set with their models and all the sub-models in the tree.
    I.e. if you pass a the fields of a model ``Foo`` (subclass of ``BaseModel``) as ``fields``, and on of them has a
    field of type ``Bar`` (also subclass of ``BaseModel``) and that model ``Bar`` has a field of type ``Baz`` (also
    subclass of ``BaseModel``), the return value will be ``set([Foo, Bar, Baz])``.

    :param fields: a list of Pydantic ``ModelField``s
    :param known_models: used to solve circular references
    :return: a set with any model declared in the fields, and all their sub-models
    """
    flat_models: TypeModelSet = set()
    for field in fields:
        flat_models |= get_flat_models_from_field(field, known_models=known_models)
    return flat_models


def get_flat_models_from_models(models: Sequence[Type['BaseModel']]) -> TypeModelSet:
    """
    Take a list of ``models`` and generate a set with them and all their sub-models in their trees. I.e. if you pass
    a list of two models, ``Foo`` and ``Bar``, both subclasses of Pydantic ``BaseModel`` as models, and ``Bar`` has
    a field of type ``Baz`` (also subclass of ``BaseModel``), the return value will be ``set([Foo, Bar, Baz])``.
    """
    flat_models: TypeModelSet = set()
    for model in models:
        flat_models |= get_flat_models_from_model(model)
    return flat_models


def get_long_model_name(model: TypeModelOrEnum) -> str:
    return f'{model.__module__}__{model.__qualname__}'.replace('.', '__')


def field_type_schema(
    field: ModelField,
    *,
    by_alias: bool,
    model_name_map: Dict[TypeModelOrEnum, str],
    ref_template: str,
    schema_overrides: bool = False,
    ref_prefix: Optional[str] = None,
    known_models: TypeModelSet,
) -> Tuple[Dict[str, Any], Dict[str, Any], Set[str]]:
    """
    Used by ``field_schema()``, you probably should be using that function.

    Take a single ``field`` and generate the schema for its type only, not including additional
    information as title, etc. Also return additional schema definitions, from sub-models.
    """
    from pydantic.v1.main import BaseModel  # noqa: F811

    definitions = {}
    nested_models: Set[str] = set()
    f_schema: Dict[str, Any]
    if field.shape in {
        SHAPE_LIST,
        SHAPE_TUPLE_ELLIPSIS,
        SHAPE_SEQUENCE,
        SHAPE_SET,
        SHAPE_FROZENSET,
        SHAPE_ITERABLE,
        SHAPE_DEQUE,
    }:
        items_schema, f_definitions, f_nested_models = field_singleton_schema(
            field,
            by_alias=by_alias,
            model_name_map=model_name_map,
            ref_prefix=ref_prefix,
            ref_template=ref_template,
            known_models=known_models,
        )
        definitions.update(f_definitions)
        nested_models.update(f_nested_models)
        f_schema = {'type': 'array', 'items': items_schema}
        if field.shape in {SHAPE_SET, SHAPE_FROZENSET}:
            f_schema['uniqueItems'] = True

    elif field.shape in MAPPING_LIKE_SHAPES:
        f_schema = {'type': 'object'}
        key_field = cast(ModelField, field.key_field)
        regex = getattr(key_field.type_, 'regex', None)
        items_schema, f_definitions, f_nested_models = field_singleton_schema(
            field,
            by_alias=by_alias,
            model_name_map=model_name_map,
            ref_prefix=ref_prefix,
            ref_template=ref_template,
            known_models=known_models,
        )
        definitions.update(f_definitions)
        nested_models.update(f_nested_models)
        if regex:
            # Dict keys have a regex pattern
            # items_schema might be a schema or empty dict, add it either way
            f_schema['patternProperties'] = {ConstrainedStr._get_pattern(regex): items_schema}
        if items_schema:
            # The dict values are not simply Any, so they need a schema
            f_schema['additionalProperties'] = items_schema
    elif field.shape == SHAPE_TUPLE or (field.shape == SHAPE_GENERIC and not issubclass(field.type_, BaseModel)):
        sub_schema = []
        sub_fields = cast(List[ModelField], field.sub_fields)
        for sf in sub_fields:
            sf_schema, sf_definitions, sf_nested_models = field_type_schema(
                sf,
                by_alias=by_alias,
                model_name_map=model_name_map,
                ref_prefix=ref_prefix,
                ref_template=ref_template,
                known_models=known_models,
            )
            definitions.update(sf_definitions)
            nested_models.update(sf_nested_models)
            sub_schema.append(sf_schema)

        sub_fields_len = len(sub_fields)
        if field.shape == SHAPE_GENERIC:
            all_of_schemas = sub_schema[0] if sub_fields_len == 1 else {'type': 'array', 'items': sub_schema}
            f_schema = {'allOf': [all_of_schemas]}
        else:
            f_schema = {
                'type': 'array',
                'minItems': sub_fields_len,
                'maxItems': sub_fields_len,
            }
            if sub_fields_len >= 1:
                f_schema['items'] = sub_schema
    else:
        assert field.shape in {SHAPE_SINGLETON, SHAPE_GENERIC}, field.shape
        f_schema, f_definitions, f_nested_models = field_singleton_schema(
            field,
            by_alias=by_alias,
            model_name_map=model_name_map,
            schema_overrides=schema_overrides,
            ref_prefix=ref_prefix,
            ref_template=ref_template,
            known_models=known_models,
        )
        definitions.update(f_definitions)
        nested_models.update(f_nested_models)

    # check field type to avoid repeated calls to the same __modify_schema__ method
    if field.type_ != field.outer_type_:
        if field.shape == SHAPE_GENERIC:
            field_type = field.type_
        else:
            field_type = field.outer_type_
        modify_schema = getattr(field_type, '__modify_schema__', None)
        if modify_schema:
            _apply_modify_schema(modify_schema, field, f_schema)
    return f_schema, definitions, nested_models


def model_process_schema(
    model: TypeModelOrEnum,
    *,
    by_alias: bool = True,
    model_name_map: Dict[TypeModelOrEnum, str],
    ref_prefix: Optional[str] = None,
    ref_template: str = default_ref_template,
    known_models: Optional[TypeModelSet] = None,
    field: Optional[ModelField] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Set[str]]:
    """
    Used by ``model_schema()``, you probably should be using that function.

    Take a single ``model`` and generate its schema. Also return additional schema definitions, from sub-models. The
    sub-models of the returned schema will be referenced, but their definitions will not be included in the schema. All
    the definitions are returned as the second value.
    """
    from inspect import getdoc, signature

    known_models = known_models or set()
    if lenient_issubclass(model, Enum):
        model = cast(Type[Enum], model)
        s = enum_process_schema(model, field=field)
        return s, {}, set()
    model = cast(Type['BaseModel'], model)
    s = {'title': model.__config__.title or model.__name__}
    doc = getdoc(model)
    if doc:
        s['description'] = doc
    known_models.add(model)
    m_schema, m_definitions, nested_models = model_type_schema(
        model,
        by_alias=by_alias,
        model_name_map=model_name_map,
        ref_prefix=ref_prefix,
        ref_template=ref_template,
        known_models=known_models,
    )
    s.update(m_schema)
    schema_extra = model.__config__.schema_extra
    if callable(schema_extra):
        if len(signature(schema_extra).parameters) == 1:
            schema_extra(s)
        else:
            schema_extra(s, model)
    else:
        s.update(schema_extra)
    return s, m_definitions, nested_models


def model_type_schema(
    model: Type['BaseModel'],
    *,
    by_alias: bool,
    model_name_map: Dict[TypeModelOrEnum, str],
    ref_template: str,
    ref_prefix: Optional[str] = None,
    known_models: TypeModelSet,
) -> Tuple[Dict[str, Any], Dict[str, Any], Set[str]]:
    """
    You probably should be using ``model_schema()``, this function is indirectly used by that function.

    Take a single ``model`` and generate the schema for its type only, not including additional
    information as title, etc. Also return additional schema definitions, from sub-models.
    """
    properties = {}
    required = []
    definitions: Dict[str, Any] = {}
    nested_models: Set[str] = set()
    for k, f in model.__fields__.items():
        try:
            f_schema, f_definitions, f_nested_models = field_schema(
                f,
                by_alias=by_alias,
                model_name_map=model_name_map,
                ref_prefix=ref_prefix,
                ref_template=ref_template,
                known_models=known_models,
            )
        except SkipField as skip:
            warnings.warn(skip.message, UserWarning)
            continue
        definitions.update(f_definitions)
        nested_models.update(f_nested_models)
        if by_alias:
            properties[f.alias] = f_schema
            if f.required:
                required.append(f.alias)
        else:
            properties[k] = f_schema
            if f.required:
                required.append(k)
    if ROOT_KEY in properties:
        out_schema = properties[ROOT_KEY]
        out_schema['title'] = model.__config__.title or model.__name__
    else:
        out_schema = {'type': 'object', 'properties': properties}
        if required:
            out_schema['required'] = required
    if model.__config__.extra == 'forbid':
        out_schema['additionalProperties'] = False
    return out_schema, definitions, nested_models


def enum_process_schema(enum: Type[Enum], *, field: Optional[ModelField] = None) -> Dict[str, Any]:
    """
    Take a single `enum` and generate its schema.

    This is similar to the `model_process_schema` function, but applies to ``Enum`` objects.
    """
    import inspect

    schema_: Dict[str, Any] = {
        'title': enum.__name__,
        # Python assigns all enums a default docstring value of 'An enumeration', so
        # all enums will have a description field even if not explicitly provided.
        'description': inspect.cleandoc(enum.__doc__ or 'An enumeration.'),
        # Add enum values and the enum field type to the schema.
        'enum': [item.value for item in cast(Iterable[Enum], enum)],
    }

    add_field_type_to_schema(enum, schema_)

    modify_schema = getattr(enum, '__modify_schema__', None)
    if modify_schema:
        _apply_modify_schema(modify_schema, field, schema_)

    return schema_


def field_singleton_sub_fields_schema(
    field: ModelField,
    *,
    by_alias: bool,
    model_name_map: Dict[TypeModelOrEnum, str],
    ref_template: str,
    schema_overrides: bool = False,
    ref_prefix: Optional[str] = None,
    known_models: TypeModelSet,
) -> Tuple[Dict[str, Any], Dict[str, Any], Set[str]]:
    """
    This function is indirectly used by ``field_schema()``, you probably should be using that function.

    Take a list of Pydantic ``ModelField`` from the declaration of a type with parameters, and generate their
    schema. I.e., fields used as "type parameters", like ``str`` and ``int`` in ``Tuple[str, int]``.
    """
    sub_fields = cast(List[ModelField], field.sub_fields)
    definitions = {}
    nested_models: Set[str] = set()
    if len(sub_fields) == 1:
        return field_type_schema(
            sub_fields[0],
            by_alias=by_alias,
            model_name_map=model_name_map,
            schema_overrides=schema_overrides,
            ref_prefix=ref_prefix,
            ref_template=ref_template,
            known_models=known_models,
        )
    else:
        s: Dict[str, Any] = {}
        # https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#discriminator-object
        field_has_discriminator: bool = field.discriminator_key is not None
        if field_has_discriminator:
            assert field.sub_fields_mapping is not None

            discriminator_models_refs: Dict[str, Union[str, Dict[str, Any]]] = {}

            for discriminator_value, sub_field in field.sub_fields_mapping.items():
                if isinstance(discriminator_value, Enum):
                    discriminator_value = str(discriminator_value.value)
                # sub_field is either a `BaseModel` or directly an `Annotated` `Union` of many
                if is_union(get_origin(sub_field.type_)):
                    sub_models = get_sub_types(sub_field.type_)
                    discriminator_models_refs[discriminator_value] = {
                        model_name_map[sub_model]: get_schema_ref(
                            model_name_map[sub_model], ref_prefix, ref_template, False
                        )
                        for sub_model in sub_models
                    }
                else:
                    sub_field_type = sub_field.type_
                    if hasattr(sub_field_type, '__pydantic_model__'):
                        sub_field_type = sub_field_type.__pydantic_model__

                    discriminator_model_name = model_name_map[sub_field_type]
                    discriminator_model_ref = get_schema_ref(discriminator_model_name, ref_prefix, ref_template, False)
                    discriminator_models_refs[discriminator_value] = discriminator_model_ref['$ref']

            s['discriminator'] = {
                'propertyName': field.discriminator_alias if by_alias else field.discriminator_key,
                'mapping': discriminator_models_refs,
            }

        sub_field_schemas = []
        for sf in sub_fields:
            sub_schema, sub_definitions, sub_nested_models = field_type_schema(
                sf,
                by_alias=by_alias,
                model_name_map=model_name_map,
                schema_overrides=schema_overrides,
                ref_prefix=ref_prefix,
                ref_template=ref_template,
                known_models=known_models,
            )
            definitions.update(sub_definitions)
            if schema_overrides and 'allOf' in sub_schema:
                # if the sub_field is a referenced schema we only need the referenced
                # object. Otherwise we will end up with several allOf inside anyOf/oneOf.
                # See https://github.com/pydantic/pydantic/issues/1209
                sub_schema = sub_schema['allOf'][0]

            if sub_schema.keys() == {'discriminator', 'oneOf'}:
                # we don't want discriminator information inside oneOf choices, this is dealt with elsewhere
                sub_schema.pop('discriminator')
            sub_field_schemas.append(sub_schema)
            nested_models.update(sub_nested_models)
        s['oneOf' if field_has_discriminator else 'anyOf'] = sub_field_schemas
        return s, definitions, nested_models


# Order is important, e.g. subclasses of str must go before str
# this is used only for standard library types, custom types should use __modify_schema__ instead
field_class_to_schema: Tuple[Tuple[Any, Dict[str, Any]], ...] = (
    (Path, {'type': 'string', 'format': 'path'}),
    (datetime, {'type': 'string', 'format': 'date-time'}),
    (date, {'type': 'string', 'format': 'date'}),
    (time, {'type': 'string', 'format': 'time'}),
    (timedelta, {'type': 'number', 'format': 'time-delta'}),
    (IPv4Network, {'type': 'string', 'format': 'ipv4network'}),
    (IPv6Network, {'type': 'string', 'format': 'ipv6network'}),
    (IPv4Interface, {'type': 'string', 'format': 'ipv4interface'}),
    (IPv6Interface, {'type': 'string', 'format': 'ipv6interface'}),
    (IPv4Address, {'type': 'string', 'format': 'ipv4'}),
    (IPv6Address, {'type': 'string', 'format': 'ipv6'}),
    (Pattern, {'type': 'string', 'format': 'regex'}),
    (str, {'type': 'string'}),
    (bytes, {'type': 'string', 'format': 'binary'}),
    (bool, {'type': 'boolean'}),
    (int, {'type': 'integer'}),
    (float, {'type': 'number'}),
    (Decimal, {'type': 'number'}),
    (UUID, {'type': 'string', 'format': 'uuid'}),
    (dict, {'type': 'object'}),
    (list, {'type': 'array', 'items': {}}),
    (tuple, {'type': 'array', 'items': {}}),
    (set, {'type': 'array', 'items': {}, 'uniqueItems': True}),
    (frozenset, {'type': 'array', 'items': {}, 'uniqueItems': True}),
)

json_scheme = {'type': 'string', 'format': 'json-string'}


def add_field_type_to_schema(field_type: Any, schema_: Dict[str, Any]) -> None:
    """
    Update the given `schema` with the type-specific metadata for the given `field_type`.

    This function looks through `field_class_to_schema` for a class that matches the given `field_type`,
    and then modifies the given `schema` with the information from that type.
    """
    for type_, t_schema in field_class_to_schema:
        # Fallback for `typing.Pattern` and `re.Pattern` as they are not a valid class
        if lenient_issubclass(field_type, type_) or field_type is type_ is Pattern:
            schema_.update(t_schema)
            break


def get_schema_ref(name: str, ref_prefix: Optional[str], ref_template: str, schema_overrides: bool) -> Dict[str, Any]:
    if ref_prefix:
        schema_ref = {'$ref': ref_prefix + name}
    else:
        schema_ref = {'$ref': ref_template.format(model=name)}
    return {'allOf': [schema_ref]} if schema_overrides else schema_ref


def field_singleton_schema(  # noqa: C901 (ignore complexity)
    field: ModelField,
    *,
    by_alias: bool,
    model_name_map: Dict[TypeModelOrEnum, str],
    ref_template: str,
    schema_overrides: bool = False,
    ref_prefix: Optional[str] = None,
    known_models: TypeModelSet,
) -> Tuple[Dict[str, Any], Dict[str, Any], Set[str]]:
    """
    This function is indirectly used by ``field_schema()``, you should probably be using that function.

    Take a single Pydantic ``ModelField``, and return its schema and any additional definitions from sub-models.
    """
    from pydantic.v1.main import BaseModel

    definitions: Dict[str, Any] = {}
    nested_models: Set[str] = set()
    field_type = field.type_

    # Recurse into this field if it contains sub_fields and is NOT a
    # BaseModel OR that BaseModel is a const
    if field.sub_fields and (
        (field.field_info and field.field_info.const) or not lenient_issubclass(field_type, BaseModel)
    ):
        return field_singleton_sub_fields_schema(
            field,
            by_alias=by_alias,
            model_name_map=model_name_map,
            schema_overrides=schema_overrides,
            ref_prefix=ref_prefix,
            ref_template=ref_template,
            known_models=known_models,
        )
    if field_type is Any or field_type is object or field_type.__class__ == TypeVar or get_origin(field_type) is type:
        return {}, definitions, nested_models  # no restrictions
    if is_none_type(field_type):
        return {'type': 'null'}, definitions, nested_models
    if is_callable_type(field_type):
        raise SkipField(f'Callable {field.name} was excluded from schema since JSON schema has no equivalent type.')
    f_schema: Dict[str, Any] = {}
    if field.field_info is not None and field.field_info.const:
        f_schema['const'] = field.default

    if is_literal_type(field_type):
        values = tuple(x.value if isinstance(x, Enum) else x for x in all_literal_values(field_type))

        if len({v.__class__ for v in values}) > 1:
            return field_schema(
                multitypes_literal_field_for_schema(values, field),
                by_alias=by_alias,
                model_name_map=model_name_map,
                ref_prefix=ref_prefix,
                ref_template=ref_template,
                known_models=known_models,
            )

        # All values have the same type
        field_type = values[0].__class__
        f_schema['enum'] = list(values)
        add_field_type_to_schema(field_type, f_schema)
    elif lenient_issubclass(field_type, Enum):
        enum_name = model_name_map[field_type]
        f_schema, schema_overrides = get_field_info_schema(field, schema_overrides)
        f_schema.update(get_schema_ref(enum_name, ref_prefix, ref_template, schema_overrides))
        definitions[enum_name] = enum_process_schema(field_type, field=field)
    elif is_namedtuple(field_type):
        sub_schema, *_ = model_process_schema(
            field_type.__pydantic_model__,
            by_alias=by_alias,
            model_name_map=model_name_map,
            ref_prefix=ref_prefix,
            ref_template=ref_template,
            known_models=known_models,
            field=field,
        )
        items_schemas = list(sub_schema['properties'].values())
        f_schema.update(
            {
                'type': 'array',
                'items': items_schemas,
                'minItems': len(items_schemas),
                'maxItems': len(items_schemas),
            }
        )
    elif not hasattr(field_type, '__pydantic_model__'):
        add_field_type_to_schema(field_type, f_schema)

        modify_schema = getattr(field_type, '__modify_schema__', None)
        if modify_schema:
            _apply_modify_schema(modify_schema, field, f_schema)

    if f_schema:
        return f_schema, definitions, nested_models

    # Handle dataclass-based models
    if lenient_issubclass(getattr(field_type, '__pydantic_model__', None), BaseModel):
        field_type = field_type.__pydantic_model__

    if issubclass(field_type, BaseModel):
        model_name = model_name_map[field_type]
        if field_type not in known_models:
            sub_schema, sub_definitions, sub_nested_models = model_process_schema(
                field_type,
                by_alias=by_alias,
                model_name_map=model_name_map,
                ref_prefix=ref_prefix,
                ref_template=ref_template,
                known_models=known_models,
                field=field,
            )
            definitions.update(sub_definitions)
            definitions[model_name] = sub_schema
            nested_models.update(sub_nested_models)
        else:
            nested_models.add(model_name)
        schema_ref = get_schema_ref(model_name, ref_prefix, ref_template, schema_overrides)
        return schema_ref, definitions, nested_models

    # For generics with no args
    args = get_args(field_type)
    if args is not None and not args and Generic in field_type.__bases__:
        return f_schema, definitions, nested_models

    raise ValueError(f'Value not declarable with JSON Schema, field: {field}')


def multitypes_literal_field_for_schema(values: Tuple[Any, ...], field: ModelField) -> ModelField:
    """
    To support `Literal` with values of different types, we split it into multiple `Literal` with same type
    e.g. `Literal['qwe', 'asd', 1, 2]` becomes `Union[Literal['qwe', 'asd'], Literal[1, 2]]`
    """
    literal_distinct_types = defaultdict(list)
    for v in values:
        literal_distinct_types[v.__class__].append(v)
    distinct_literals = (Literal[tuple(same_type_values)] for same_type_values in literal_distinct_types.values())

    return ModelField(
        name=field.name,
        type_=Union[tuple(distinct_literals)],  # type: ignore
        class_validators=field.class_validators,
        model_config=field.model_config,
        default=field.default,
        required=field.required,
        alias=field.alias,
        field_info=field.field_info,
    )


def encode_default(dft: Any) -> Any:
    from pydantic.v1.main import BaseModel

    if isinstance(dft, BaseModel) or is_dataclass(dft):
        dft = cast('dict[str, Any]', pydantic_encoder(dft))

    if isinstance(dft, dict):
        return {encode_default(k): encode_default(v) for k, v in dft.items()}
    elif isinstance(dft, Enum):
        return dft.value
    elif isinstance(dft, (int, float, str)):
        return dft
    elif isinstance(dft, (list, tuple)):
        t = dft.__class__
        seq_args = (encode_default(v) for v in dft)
        return t(*seq_args) if is_namedtuple(t) else t(seq_args)
    elif dft is None:
        return None
    else:
        return pydantic_encoder(dft)


_map_types_constraint: Dict[Any, Callable[..., type]] = {int: conint, float: confloat, Decimal: condecimal}


def get_annotation_from_field_info(
    annotation: Any, field_info: FieldInfo, field_name: str, validate_assignment: bool = False
) -> Type[Any]:
    """
    Get an annotation with validation implemented for numbers and strings based on the field_info.
    :param annotation: an annotation from a field specification, as ``str``, ``ConstrainedStr``
    :param field_info: an instance of FieldInfo, possibly with declarations for validations and JSON Schema
    :param field_name: name of the field for use in error messages
    :param validate_assignment: default False, flag for BaseModel Config value of validate_assignment
    :return: the same ``annotation`` if unmodified or a new annotation with validation in place
    """
    constraints = field_info.get_constraints()
    used_constraints: Set[str] = set()
    if constraints:
        annotation, used_constraints = get_annotation_with_constraints(annotation, field_info)
    if validate_assignment:
        used_constraints.add('allow_mutation')

    unused_constraints = constraints - used_constraints
    if unused_constraints:
        raise ValueError(
            f'On field "{field_name}" the following field constraints are set but not enforced: '
            f'{", ".join(unused_constraints)}. '
            f'\nFor more details see https://docs.pydantic.dev/usage/schema/#unenforced-field-constraints'
        )

    return annotation


def get_annotation_with_constraints(annotation: Any, field_info: FieldInfo) -> Tuple[Type[Any], Set[str]]:  # noqa: C901
    """
    Get an annotation with used constraints implemented for numbers and strings based on the field_info.

    :param annotation: an annotation from a field specification, as ``str``, ``ConstrainedStr``
    :param field_info: an instance of FieldInfo, possibly with declarations for validations and JSON Schema
    :return: the same ``annotation`` if unmodified or a new annotation along with the used constraints.
    """
    used_constraints: Set[str] = set()

    def go(type_: Any) -> Type[Any]:
        if (
            is_literal_type(type_)
            or isinstance(type_, ForwardRef)
            or lenient_issubclass(type_, (ConstrainedList, ConstrainedSet, ConstrainedFrozenSet))
        ):
            return type_
        origin = get_origin(type_)
        if origin is not None:
            args: Tuple[Any, ...] = get_args(type_)
            if any(isinstance(a, ForwardRef) for a in args):
                # forward refs cause infinite recursion below
                return type_

            if origin is Annotated:
                return go(args[0])
            if is_union(origin):
                return Union[tuple(go(a) for a in args)]  # type: ignore

            if issubclass(origin, List) and (
                field_info.min_items is not None
                or field_info.max_items is not None
                or field_info.unique_items is not None
            ):
                used_constraints.update({'min_items', 'max_items', 'unique_items'})
                return conlist(
                    go(args[0]),
                    min_items=field_info.min_items,
                    max_items=field_info.max_items,
                    unique_items=field_info.unique_items,
                )

            if issubclass(origin, Set) and (field_info.min_items is not None or field_info.max_items is not None):
                used_constraints.update({'min_items', 'max_items'})
                return conset(go(args[0]), min_items=field_info.min_items, max_items=field_info.max_items)

            if issubclass(origin, FrozenSet) and (field_info.min_items is not None or field_info.max_items is not None):
                used_constraints.update({'min_items', 'max_items'})
                return confrozenset(go(args[0]), min_items=field_info.min_items, max_items=field_info.max_items)

            for t in (Tuple, List, Set, FrozenSet, Sequence):
                if issubclass(origin, t):  # type: ignore
                    return t[tuple(go(a) for a in args)]  # type: ignore

            if issubclass(origin, Dict):
                return Dict[args[0], go(args[1])]  # type: ignore

        attrs: Optional[Tuple[str, ...]] = None
        constraint_func: Optional[Callable[..., type]] = None
        if isinstance(type_, type):
            if issubclass(type_, (SecretStr, SecretBytes)):
                attrs = ('max_length', 'min_length')

                def constraint_func(**kw: Any) -> Type[Any]:  # noqa: F811
                    return type(type_.__name__, (type_,), kw)

            elif issubclass(type_, str) and not issubclass(type_, (EmailStr, AnyUrl)):
                attrs = ('max_length', 'min_length', 'regex')
                if issubclass(type_, StrictStr):

                    def constraint_func(**kw: Any) -> Type[Any]:
                        return type(type_.__name__, (type_,), kw)

                else:
                    constraint_func = constr
            elif issubclass(type_, bytes):
                attrs = ('max_length', 'min_length', 'regex')
                if issubclass(type_, StrictBytes):

                    def constraint_func(**kw: Any) -> Type[Any]:
                        return type(type_.__name__, (type_,), kw)

                else:
                    constraint_func = conbytes
            elif issubclass(type_, numeric_types) and not issubclass(
                type_,
                (
                    ConstrainedInt,
                    ConstrainedFloat,
                    ConstrainedDecimal,
                    ConstrainedList,
                    ConstrainedSet,
                    ConstrainedFrozenSet,
                    bool,
                ),
            ):
                # Is numeric type
                attrs = ('gt', 'lt', 'ge', 'le', 'multiple_of')
                if issubclass(type_, float):
                    attrs += ('allow_inf_nan',)
                if issubclass(type_, Decimal):
                    attrs += ('max_digits', 'decimal_places')
                numeric_type = next(t for t in numeric_types if issubclass(type_, t))  # pragma: no branch
                constraint_func = _map_types_constraint[numeric_type]

        if attrs:
            used_constraints.update(set(attrs))
            kwargs = {
                attr_name: attr
                for attr_name, attr in ((attr_name, getattr(field_info, attr_name)) for attr_name in attrs)
                if attr is not None
            }
            if kwargs:
                constraint_func = cast(Callable[..., type], constraint_func)
                return constraint_func(**kwargs)
        return type_

    return go(annotation), used_constraints


def normalize_name(name: str) -> str:
    """
    Normalizes the given name. This can be applied to either a model *or* enum.
    """
    return re.sub(r'[^a-zA-Z0-9.\-_]', '_', name)


class SkipField(Exception):
    """
    Utility exception used to exclude fields from schema.
    """

    def __init__(self, message: str) -> None:
        self.message = message

# === NexusCore/openenv\Lib\site-packages\executing\executing.py ===
"""
MIT License

Copyright (c) 2021 Alex Hall

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import __future__
import ast
import dis
import inspect
import io
import linecache
import re
import sys
import types
from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
from itertools import islice
from itertools import zip_longest
from operator import attrgetter
from pathlib import Path
from threading import RLock
from tokenize import detect_encoding
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Sized, Tuple, \
    Type, TypeVar, Union, cast

if TYPE_CHECKING:  # pragma: no cover
    from asttokens import ASTTokens, ASTText
    from asttokens.asttokens import ASTTextBase


function_node_types = (ast.FunctionDef, ast.AsyncFunctionDef) # type: Tuple[Type, ...]

cache = lru_cache(maxsize=None)

# Type class used to expand out the definition of AST to include fields added by this library
# It's not actually used for anything other than type checking though!
class EnhancedAST(ast.AST):
    parent = None  # type: EnhancedAST


class Instruction(dis.Instruction):
    lineno = None  # type: int


# Type class used to expand out the definition of AST to include fields added by this library
# It's not actually used for anything other than type checking though!
class EnhancedInstruction(Instruction):
    _copied = None # type: bool



def assert_(condition, message=""):
    # type: (Any, str) -> None
    """
    Like an assert statement, but unaffected by -O
    :param condition: value that is expected to be truthy
    :type message: Any
    """
    if not condition:
        raise AssertionError(str(message))


def get_instructions(co):
    # type: (types.CodeType) -> Iterator[EnhancedInstruction]
    lineno = co.co_firstlineno
    for inst in dis.get_instructions(co):
        inst = cast(EnhancedInstruction, inst)
        lineno = inst.starts_line or lineno
        assert_(lineno)
        inst.lineno = lineno
        yield inst


TESTING = 0


class NotOneValueFound(Exception):
    def __init__(self,msg,values=[]):
        # type: (str, Sequence) -> None
        self.values=values
        super(NotOneValueFound,self).__init__(msg)

T = TypeVar('T')


def only(it):
    # type: (Iterable[T]) -> T
    if isinstance(it, Sized):
        if len(it) != 1:
            raise NotOneValueFound('Expected one value, found %s' % len(it))
        # noinspection PyTypeChecker
        return list(it)[0]

    lst = tuple(islice(it, 2))
    if len(lst) == 0:
        raise NotOneValueFound('Expected one value, found 0')
    if len(lst) > 1:
        raise NotOneValueFound('Expected one value, found several',lst)
    return lst[0]


class Source(object):
    """
    The source code of a single file and associated metadata.

    The main method of interest is the classmethod `executing(frame)`.

    If you want an instance of this class, don't construct it.
    Ideally use the classmethod `for_frame(frame)`.
    If you don't have a frame, use `for_filename(filename [, module_globals])`.
    These methods cache instances by filename, so at most one instance exists per filename.

    Attributes:
        - filename
        - text
        - lines
        - tree: AST parsed from text, or None if text is not valid Python
            All nodes in the tree have an extra `parent` attribute

    Other methods of interest:
        - statements_at_line
        - asttokens
        - code_qualname
    """

    def __init__(self, filename, lines):
        # type: (str, Sequence[str]) -> None
        """
        Don't call this constructor, see the class docstring.
        """

        self.filename = filename
        self.text = ''.join(lines)
        self.lines = [line.rstrip('\r\n') for line in lines]

        self._nodes_by_line = defaultdict(list)
        self.tree = None
        self._qualnames = {}
        self._asttokens = None  # type: Optional[ASTTokens]
        self._asttext = None  # type: Optional[ASTText]

        try:
            self.tree = ast.parse(self.text, filename=filename)
        except (SyntaxError, ValueError):
            pass
        else:
            for node in ast.walk(self.tree):
                for child in ast.iter_child_nodes(node):
                    cast(EnhancedAST, child).parent = cast(EnhancedAST, node)
                for lineno in node_linenos(node):
                    self._nodes_by_line[lineno].append(node)

            visitor = QualnameVisitor()
            visitor.visit(self.tree)
            self._qualnames = visitor.qualnames

    @classmethod
    def for_frame(cls, frame, use_cache=True):
        # type: (types.FrameType, bool) -> "Source"
        """
        Returns the `Source` object corresponding to the file the frame is executing in.
        """
        return cls.for_filename(frame.f_code.co_filename, frame.f_globals or {}, use_cache)

    @classmethod
    def for_filename(
        cls,
        filename,
        module_globals=None,
        use_cache=True,  # noqa no longer used
    ):
        # type: (Union[str, Path], Optional[Dict[str, Any]], bool) -> "Source"
        if isinstance(filename, Path):
            filename = str(filename)

        def get_lines():
            # type: () -> List[str]
            return linecache.getlines(cast(str, filename), module_globals)

        # Save the current linecache entry, then ensure the cache is up to date.
        entry = linecache.cache.get(filename) # type: ignore[attr-defined]
        linecache.checkcache(filename)
        lines = get_lines()
        if entry is not None and not lines:
            # There was an entry, checkcache removed it, and nothing replaced it.
            # This means the file wasn't simply changed (because the `lines` wouldn't be empty)
            # but rather the file was found not to exist, probably because `filename` was fake.
            # Restore the original entry so that we still have something.
            linecache.cache[filename] = entry # type: ignore[attr-defined]
            lines = get_lines()

        return cls._for_filename_and_lines(filename, tuple(lines))

    @classmethod
    def _for_filename_and_lines(cls, filename, lines):
        # type: (str, Sequence[str]) -> "Source"
        source_cache = cls._class_local('__source_cache_with_lines', {}) # type: Dict[Tuple[str, Sequence[str]], Source]
        try:
            return source_cache[(filename, lines)]
        except KeyError:
            pass

        result = source_cache[(filename, lines)] = cls(filename, lines)
        return result

    @classmethod
    def lazycache(cls, frame):
        # type: (types.FrameType) -> None
        linecache.lazycache(frame.f_code.co_filename, frame.f_globals)

    @classmethod
    def executing(cls, frame_or_tb):
        # type: (Union[types.TracebackType, types.FrameType]) -> "Executing"
        """
        Returns an `Executing` object representing the operation
        currently executing in the given frame or traceback object.
        """
        if isinstance(frame_or_tb, types.TracebackType):
            # https://docs.python.org/3/reference/datamodel.html#traceback-objects
            # "tb_lineno gives the line number where the exception occurred;
            #  tb_lasti indicates the precise instruction.
            #  The line number and last instruction in the traceback may differ
            #  from the line number of its frame object
            #  if the exception occurred in a try statement with no matching except clause
            #  or with a finally clause."
            tb = frame_or_tb
            frame = tb.tb_frame
            lineno = tb.tb_lineno
            lasti = tb.tb_lasti
        else:
            frame = frame_or_tb
            lineno = frame.f_lineno
            lasti = frame.f_lasti



        code = frame.f_code
        key = (code, id(code), lasti)
        executing_cache = cls._class_local('__executing_cache', {}) # type: Dict[Tuple[types.CodeType, int, int], Any]

        args = executing_cache.get(key)
        if not args:
            node = stmts = decorator = None
            source = cls.for_frame(frame)
            tree = source.tree
            if tree:
                try:
                    stmts = source.statements_at_line(lineno)
                    if stmts:
                        if is_ipython_cell_code(code):
                            decorator, node = find_node_ipython(frame, lasti, stmts, source)
                        else:
                            node_finder = NodeFinder(frame, stmts, tree, lasti, source)
                            node = node_finder.result
                            decorator = node_finder.decorator

                    if node:
                        new_stmts = {statement_containing_node(node)}
                        assert_(new_stmts <= stmts)
                        stmts = new_stmts
                except Exception:
                    if TESTING:
                        raise

            executing_cache[key] = args = source, node, stmts, decorator

        return Executing(frame, *args)

    @classmethod
    def _class_local(cls, name, default):
        # type: (str, T) -> T
        """
        Returns an attribute directly associated with this class
        (as opposed to subclasses), setting default if necessary
        """
        # classes have a mappingproxy preventing us from using setdefault
        result = cls.__dict__.get(name, default)
        setattr(cls, name, result)
        return result

    @cache
    def statements_at_line(self, lineno):
        # type: (int) -> Set[EnhancedAST]
        """
        Returns the statement nodes overlapping the given line.

        Returns at most one statement unless semicolons are present.

        If the `text` attribute is not valid python, meaning
        `tree` is None, returns an empty set.

        Otherwise, `Source.for_frame(frame).statements_at_line(frame.f_lineno)`
        should return at least one statement.
        """

        return {
            statement_containing_node(node)
            for node in
            self._nodes_by_line[lineno]
        }

    def asttext(self):
        # type: () -> ASTText
        """
        Returns an ASTText object for getting the source of specific AST nodes.

        See http://asttokens.readthedocs.io/en/latest/api-index.html
        """
        from asttokens import ASTText  # must be installed separately

        if self._asttext is None:
            self._asttext = ASTText(self.text, tree=self.tree, filename=self.filename)

        return self._asttext

    def asttokens(self):
        # type: () -> ASTTokens
        """
        Returns an ASTTokens object for getting the source of specific AST nodes.

        See http://asttokens.readthedocs.io/en/latest/api-index.html
        """
        import asttokens  # must be installed separately

        if self._asttokens is None:
            if hasattr(asttokens, 'ASTText'):
                self._asttokens = self.asttext().asttokens
            else:  # pragma: no cover
                self._asttokens = asttokens.ASTTokens(self.text, tree=self.tree, filename=self.filename)
        return self._asttokens

    def _asttext_base(self):
        # type: () -> ASTTextBase
        import asttokens  # must be installed separately

        if hasattr(asttokens, 'ASTText'):
            return self.asttext()
        else:  # pragma: no cover
            return self.asttokens()

    @staticmethod
    def decode_source(source):
        # type: (Union[str, bytes]) -> str
        if isinstance(source, bytes):
            encoding = Source.detect_encoding(source)
            return source.decode(encoding)
        else:
            return source

    @staticmethod
    def detect_encoding(source):
        # type: (bytes) -> str
        return detect_encoding(io.BytesIO(source).readline)[0]

    def code_qualname(self, code):
        # type: (types.CodeType) -> str
        """
        Imitates the __qualname__ attribute of functions for code objects.
        Given:

            - A function `func`
            - A frame `frame` for an execution of `func`, meaning:
                `frame.f_code is func.__code__`

        `Source.for_frame(frame).code_qualname(frame.f_code)`
        will be equal to `func.__qualname__`*. Works for Python 2 as well,
        where of course no `__qualname__` attribute exists.

        Falls back to `code.co_name` if there is no appropriate qualname.

        Based on https://github.com/wbolster/qualname

        (* unless `func` is a lambda
        nested inside another lambda on the same line, in which case
        the outer lambda's qualname will be returned for the codes
        of both lambdas)
        """
        assert_(code.co_filename == self.filename)
        return self._qualnames.get((code.co_name, code.co_firstlineno), code.co_name)


class Executing(object):
    """
    Information about the operation a frame is currently executing.

    Generally you will just want `node`, which is the AST node being executed,
    or None if it's unknown.

    If a decorator is currently being called, then:
        - `node` is a function or class definition
        - `decorator` is the expression in `node.decorator_list` being called
        - `statements == {node}`
    """

    def __init__(self, frame, source, node, stmts, decorator):
        # type: (types.FrameType, Source, EnhancedAST, Set[ast.stmt], Optional[EnhancedAST]) -> None
        self.frame = frame
        self.source = source
        self.node = node
        self.statements = stmts
        self.decorator = decorator

    def code_qualname(self):
        # type: () -> str
        return self.source.code_qualname(self.frame.f_code)

    def text(self):
        # type: () -> str
        return self.source._asttext_base().get_text(self.node)

    def text_range(self):
        # type: () -> Tuple[int, int]
        return self.source._asttext_base().get_text_range(self.node)


class QualnameVisitor(ast.NodeVisitor):
    def __init__(self):
        # type: () -> None
        super(QualnameVisitor, self).__init__()
        self.stack = [] # type: List[str]
        self.qualnames = {} # type: Dict[Tuple[str, int], str]

    def add_qualname(self, node, name=None):
        # type: (ast.AST, Optional[str]) -> None
        name = name or node.name # type: ignore[attr-defined]
        self.stack.append(name)
        if getattr(node, 'decorator_list', ()):
            lineno = node.decorator_list[0].lineno # type: ignore[attr-defined]
        else:
            lineno = node.lineno # type: ignore[attr-defined]
        self.qualnames.setdefault((name, lineno), ".".join(self.stack))

    def visit_FunctionDef(self, node, name=None):
        # type: (ast.AST, Optional[str]) -> None
        assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)), node
        self.add_qualname(node, name)
        self.stack.append('<locals>')
        children = [] # type: Sequence[ast.AST]
        if isinstance(node, ast.Lambda):
            children = [node.body]
        else:
            children = node.body
        for child in children:
            self.visit(child)
        self.stack.pop()
        self.stack.pop()

        # Find lambdas in the function definition outside the body,
        # e.g. decorators or default arguments
        # Based on iter_child_nodes
        for field, child in ast.iter_fields(node):
            if field == 'body':
                continue
            if isinstance(child, ast.AST):
                self.visit(child)
            elif isinstance(child, list):
                for grandchild in child:
                    if isinstance(grandchild, ast.AST):
                        self.visit(grandchild)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        # type: (ast.AST) -> None
        assert isinstance(node, ast.Lambda)
        self.visit_FunctionDef(node, '<lambda>')

    def visit_ClassDef(self, node):
        # type: (ast.AST) -> None
        assert isinstance(node, ast.ClassDef)
        self.add_qualname(node)
        self.generic_visit(node)
        self.stack.pop()





future_flags = sum(
    getattr(__future__, fname).compiler_flag for fname in __future__.all_feature_names
)


def compile_similar_to(source, matching_code):
    # type: (ast.Module, types.CodeType) -> Any
    return compile(
        source,
        matching_code.co_filename,
        'exec',
        flags=future_flags & matching_code.co_flags,
        dont_inherit=True,
    )


sentinel = 'io8urthglkjdghvljusketgIYRFYUVGHFRTBGVHKGF78678957647698'

def is_rewritten_by_pytest(code):
    # type: (types.CodeType) -> bool
    return any(
        bc.opname != "LOAD_CONST" and isinstance(bc.argval,str) and bc.argval.startswith("@py")
        for bc in get_instructions(code)
    )


class SentinelNodeFinder(object):
    result = None # type: EnhancedAST

    def __init__(self, frame, stmts, tree, lasti, source):
        # type: (types.FrameType, Set[EnhancedAST], ast.Module, int, Source) -> None
        assert_(stmts)
        self.frame = frame
        self.tree = tree
        self.code = code = frame.f_code
        self.is_pytest = is_rewritten_by_pytest(code)

        if self.is_pytest:
            self.ignore_linenos = frozenset(assert_linenos(tree))
        else:
            self.ignore_linenos = frozenset()

        self.decorator = None

        self.instruction = instruction = self.get_actual_current_instruction(lasti)
        op_name = instruction.opname
        extra_filter = lambda e: True # type: Callable[[Any], bool]
        ctx = type(None) # type: Type

        typ = type(None) # type: Type
        if op_name.startswith('CALL_'):
            typ = ast.Call
        elif op_name.startswith(('BINARY_SUBSCR', 'SLICE+')):
            typ = ast.Subscript
            ctx = ast.Load
        elif op_name.startswith('BINARY_'):
            typ = ast.BinOp
            op_type = dict(
                BINARY_POWER=ast.Pow,
                BINARY_MULTIPLY=ast.Mult,
                BINARY_MATRIX_MULTIPLY=getattr(ast, "MatMult", ()),
                BINARY_FLOOR_DIVIDE=ast.FloorDiv,
                BINARY_TRUE_DIVIDE=ast.Div,
                BINARY_MODULO=ast.Mod,
                BINARY_ADD=ast.Add,
                BINARY_SUBTRACT=ast.Sub,
                BINARY_LSHIFT=ast.LShift,
                BINARY_RSHIFT=ast.RShift,
                BINARY_AND=ast.BitAnd,
                BINARY_XOR=ast.BitXor,
                BINARY_OR=ast.BitOr,
            )[op_name]
            extra_filter = lambda e: isinstance(e.op, op_type)
        elif op_name.startswith('UNARY_'):
            typ = ast.UnaryOp
            op_type = dict(
                UNARY_POSITIVE=ast.UAdd,
                UNARY_NEGATIVE=ast.USub,
                UNARY_NOT=ast.Not,
                UNARY_INVERT=ast.Invert,
            )[op_name]
            extra_filter = lambda e: isinstance(e.op, op_type)
        elif op_name in ('LOAD_ATTR', 'LOAD_METHOD', 'LOOKUP_METHOD'):
            typ = ast.Attribute
            ctx = ast.Load
            extra_filter = lambda e: attr_names_match(e.attr, instruction.argval)
        elif op_name in ('LOAD_NAME', 'LOAD_GLOBAL', 'LOAD_FAST', 'LOAD_DEREF', 'LOAD_CLASSDEREF'):
            typ = ast.Name
            ctx = ast.Load
            extra_filter = lambda e: e.id == instruction.argval
        elif op_name in ('COMPARE_OP', 'IS_OP', 'CONTAINS_OP'):
            typ = ast.Compare
            extra_filter = lambda e: len(e.ops) == 1
        elif op_name.startswith(('STORE_SLICE', 'STORE_SUBSCR')):
            ctx = ast.Store
            typ = ast.Subscript
        elif op_name.startswith('STORE_ATTR'):
            ctx = ast.Store
            typ = ast.Attribute
            extra_filter = lambda e: attr_names_match(e.attr, instruction.argval)
        else:
            raise RuntimeError(op_name)

        with lock:
            exprs = {
                cast(EnhancedAST, node)
                for stmt in stmts
                for node in ast.walk(stmt)
                if isinstance(node, typ)
                if isinstance(getattr(node, "ctx", None), ctx)
                if extra_filter(node)
                if statement_containing_node(node) == stmt
            }

            if ctx == ast.Store:
                # No special bytecode tricks here.
                # We can handle multiple assigned attributes with different names,
                # but only one assigned subscript.
                self.result = only(exprs)
                return

            matching = list(self.matching_nodes(exprs))
            if not matching and typ == ast.Call:
                self.find_decorator(stmts)
            else:
                self.result = only(matching)

    def find_decorator(self, stmts):
        # type: (Union[List[EnhancedAST], Set[EnhancedAST]]) -> None
        stmt = only(stmts)
        assert_(isinstance(stmt, (ast.ClassDef, function_node_types)))
        decorators = stmt.decorator_list # type: ignore[attr-defined]
        assert_(decorators)
        line_instructions = [
            inst
            for inst in self.clean_instructions(self.code)
            if inst.lineno == self.frame.f_lineno
        ]
        last_decorator_instruction_index = [
            i
            for i, inst in enumerate(line_instructions)
            if inst.opname == "CALL_FUNCTION"
        ][-1]
        assert_(
            line_instructions[last_decorator_instruction_index + 1].opname.startswith(
                "STORE_"
            )
        )
        decorator_instructions = line_instructions[
            last_decorator_instruction_index
            - len(decorators)
            + 1 : last_decorator_instruction_index
            + 1
        ]
        assert_({inst.opname for inst in decorator_instructions} == {"CALL_FUNCTION"})
        decorator_index = decorator_instructions.index(self.instruction)
        decorator = decorators[::-1][decorator_index]
        self.decorator = decorator
        self.result = stmt

    def clean_instructions(self, code):
        # type: (types.CodeType) -> List[EnhancedInstruction]
        return [
            inst
            for inst in get_instructions(code)
            if inst.opname not in ("EXTENDED_ARG", "NOP")
            if inst.lineno not in self.ignore_linenos
        ]

    def get_original_clean_instructions(self):
        # type: () -> List[EnhancedInstruction]
        result = self.clean_instructions(self.code)

        # pypy sometimes (when is not clear)
        # inserts JUMP_IF_NOT_DEBUG instructions in bytecode
        # If they're not present in our compiled instructions,
        # ignore them in the original bytecode
        if not any(
                inst.opname == "JUMP_IF_NOT_DEBUG"
                for inst in self.compile_instructions()
        ):
            result = [
                inst for inst in result
                if inst.opname != "JUMP_IF_NOT_DEBUG"
            ]

        return result

    def matching_nodes(self, exprs):
        # type: (Set[EnhancedAST]) -> Iterator[EnhancedAST]
        original_instructions = self.get_original_clean_instructions()
        original_index = only(
            i
            for i, inst in enumerate(original_instructions)
            if inst == self.instruction
        )
        for expr_index, expr in enumerate(exprs):
            setter = get_setter(expr)
            assert setter is not None
            # noinspection PyArgumentList
            replacement = ast.BinOp(
                left=expr,
                op=ast.Pow(),
                right=ast.Str(s=sentinel),
            )
            ast.fix_missing_locations(replacement)
            setter(replacement)
            try:
                instructions = self.compile_instructions()
            finally:
                setter(expr)

            if sys.version_info >= (3, 10):
                try:
                    handle_jumps(instructions, original_instructions)
                except Exception:
                    # Give other candidates a chance
                    if TESTING or expr_index < len(exprs) - 1:
                        continue
                    raise

            indices = [
                i
                for i, instruction in enumerate(instructions)
                if instruction.argval == sentinel
            ]

            # There can be several indices when the bytecode is duplicated,
            # as happens in a finally block in 3.9+
            # First we remove the opcodes caused by our modifications
            for index_num, sentinel_index in enumerate(indices):
                # Adjustment for removing sentinel instructions below
                # in past iterations
                sentinel_index -= index_num * 2

                assert_(instructions.pop(sentinel_index).opname == 'LOAD_CONST')
                assert_(instructions.pop(sentinel_index).opname == 'BINARY_POWER')

            # Then we see if any of the instruction indices match
            for index_num, sentinel_index in enumerate(indices):
                sentinel_index -= index_num * 2
                new_index = sentinel_index - 1

                if new_index != original_index:
                    continue

                original_inst = original_instructions[original_index]
                new_inst = instructions[new_index]

                # In Python 3.9+, changing 'not x in y' to 'not sentinel_transformation(x in y)'
                # changes a CONTAINS_OP(invert=1) to CONTAINS_OP(invert=0),<sentinel stuff>,UNARY_NOT
                if (
                        original_inst.opname == new_inst.opname in ('CONTAINS_OP', 'IS_OP')
                        and original_inst.arg != new_inst.arg # type: ignore[attr-defined]
                        and (
                        original_instructions[original_index + 1].opname
                        != instructions[new_index + 1].opname == 'UNARY_NOT'
                )):
                    # Remove the difference for the upcoming assert
                    instructions.pop(new_index + 1)

                # Check that the modified instructions don't have anything unexpected
                # 3.10 is a bit too weird to assert this in all cases but things still work
                if sys.version_info < (3, 10):
                    for inst1, inst2 in zip_longest(
                        original_instructions, instructions
                    ):
                        assert_(inst1 and inst2 and opnames_match(inst1, inst2))

                yield expr

    def compile_instructions(self):
        # type: () -> List[EnhancedInstruction]
        module_code = compile_similar_to(self.tree, self.code)
        code = only(self.find_codes(module_code))
        return self.clean_instructions(code)

    def find_codes(self, root_code):
        # type: (types.CodeType) -> list
        checks = [
            attrgetter('co_firstlineno'),
            attrgetter('co_freevars'),
            attrgetter('co_cellvars'),
            lambda c: is_ipython_cell_code_name(c.co_name) or c.co_name,
        ] # type: List[Callable]
        if not self.is_pytest:
            checks += [
                attrgetter('co_names'),
                attrgetter('co_varnames'),
            ]

        def matches(c):
            # type: (types.CodeType) -> bool
            return all(
                f(c) == f(self.code)
                for f in checks
            )

        code_options = []
        if matches(root_code):
            code_options.append(root_code)

        def finder(code):
            # type: (types.CodeType) -> None
            for const in code.co_consts:
                if not inspect.iscode(const):
                    continue

                if matches(const):
                    code_options.append(const)
                finder(const)

        finder(root_code)
        return code_options

    def get_actual_current_instruction(self, lasti):
        # type: (int) -> EnhancedInstruction
        """
        Get the instruction corresponding to the current
        frame offset, skipping EXTENDED_ARG instructions
        """
        # Don't use get_original_clean_instructions
        # because we need the actual instructions including
        # EXTENDED_ARG
        instructions = list(get_instructions(self.code))
        index = only(
            i
            for i, inst in enumerate(instructions)
            if inst.offset == lasti
        )

        while True:
            instruction = instructions[index]
            if instruction.opname != "EXTENDED_ARG":
                return instruction
            index += 1



def non_sentinel_instructions(instructions, start):
    # type: (List[EnhancedInstruction], int) -> Iterator[Tuple[int, EnhancedInstruction]]
    """
    Yields (index, instruction) pairs excluding the basic
    instructions introduced by the sentinel transformation
    """
    skip_power = False
    for i, inst in islice(enumerate(instructions), start, None):
        if inst.argval == sentinel:
            assert_(inst.opname == "LOAD_CONST")
            skip_power = True
            continue
        elif skip_power:
            assert_(inst.opname == "BINARY_POWER")
            skip_power = False
            continue
        yield i, inst


def walk_both_instructions(original_instructions, original_start, instructions, start):
    # type: (List[EnhancedInstruction], int, List[EnhancedInstruction], int) -> Iterator[Tuple[int, EnhancedInstruction, int, EnhancedInstruction]]
    """
    Yields matching indices and instructions from the new and original instructions,
    leaving out changes made by the sentinel transformation.
    """
    original_iter = islice(enumerate(original_instructions), original_start, None)
    new_iter = non_sentinel_instructions(instructions, start)
    inverted_comparison = False
    while True:
        try:
            original_i, original_inst = next(original_iter)
            new_i, new_inst = next(new_iter)
        except StopIteration:
            return
        if (
            inverted_comparison
            and original_inst.opname != new_inst.opname == "UNARY_NOT"
        ):
            new_i, new_inst = next(new_iter)
        inverted_comparison = (
            original_inst.opname == new_inst.opname in ("CONTAINS_OP", "IS_OP")
            and original_inst.arg != new_inst.arg # type: ignore[attr-defined]
        )
        yield original_i, original_inst, new_i, new_inst


def handle_jumps(instructions, original_instructions):
    # type: (List[EnhancedInstruction], List[EnhancedInstruction]) -> None
    """
    Transforms instructions in place until it looks more like original_instructions.
    This is only needed in 3.10+ where optimisations lead to more drastic changes
    after the sentinel transformation.
    Replaces JUMP instructions that aren't also present in original_instructions
    with the sections that they jump to until a raise or return.
    In some other cases duplication found in `original_instructions`
    is replicated in `instructions`.
    """
    while True:
        for original_i, original_inst, new_i, new_inst in walk_both_instructions(
            original_instructions, 0, instructions, 0
        ):
            if opnames_match(original_inst, new_inst):
                continue

            if "JUMP" in new_inst.opname and "JUMP" not in original_inst.opname:
                # Find where the new instruction is jumping to, ignoring
                # instructions which have been copied in previous iterations
                start = only(
                    i
                    for i, inst in enumerate(instructions)
                    if inst.offset == new_inst.argval
                    and not getattr(inst, "_copied", False)
                )
                # Replace the jump instruction with the jumped to section of instructions
                # That section may also be deleted if it's not similarly duplicated
                # in original_instructions
                new_instructions = handle_jump(
                    original_instructions, original_i, instructions, start
                )
                assert new_instructions is not None
                instructions[new_i : new_i + 1] = new_instructions            
            else:
                # Extract a section of original_instructions from original_i to return/raise
                orig_section = []
                for section_inst in original_instructions[original_i:]:
                    orig_section.append(section_inst)
                    if section_inst.opname in ("RETURN_VALUE", "RAISE_VARARGS"):
                        break
                else:
                    # No return/raise - this is just a mismatch we can't handle
                    raise AssertionError

                instructions[new_i:new_i] = only(find_new_matching(orig_section, instructions))

            # instructions has been modified, the for loop can't sensibly continue
            # Restart it from the beginning, checking for other issues
            break

        else:  # No mismatched jumps found, we're done
            return


def find_new_matching(orig_section, instructions):
    # type: (List[EnhancedInstruction], List[EnhancedInstruction]) -> Iterator[List[EnhancedInstruction]]
    """
    Yields sections of `instructions` which match `orig_section`.
    The yielded sections include sentinel instructions, but these
    are ignored when checking for matches.
    """
    for start in range(len(instructions) - len(orig_section)):
        indices, dup_section = zip(
            *islice(
                non_sentinel_instructions(instructions, start),
                len(orig_section),
            )
        )
        if len(dup_section) < len(orig_section):
            return
        if sections_match(orig_section, dup_section):
            yield instructions[start:indices[-1] + 1]


def handle_jump(original_instructions, original_start, instructions, start):
    # type: (List[EnhancedInstruction], int, List[EnhancedInstruction], int) -> Optional[List[EnhancedInstruction]]
    """
    Returns the section of instructions starting at `start` and ending
    with a RETURN_VALUE or RAISE_VARARGS instruction.
    There should be a matching section in original_instructions starting at original_start.
    If that section doesn't appear elsewhere in original_instructions,
    then also delete the returned section of instructions.
    """
    for original_j, original_inst, new_j, new_inst in walk_both_instructions(
        original_instructions, original_start, instructions, start
    ):
        assert_(opnames_match(original_inst, new_inst))
        if original_inst.opname in ("RETURN_VALUE", "RAISE_VARARGS"):
            inlined = deepcopy(instructions[start : new_j + 1])
            for inl in inlined:
                inl._copied = True
            orig_section = original_instructions[original_start : original_j + 1]
            if not check_duplicates(
                original_start, orig_section, original_instructions
            ):
                instructions[start : new_j + 1] = []
            return inlined
    
    return None


def check_duplicates(original_i, orig_section, original_instructions):
    # type: (int, List[EnhancedInstruction], List[EnhancedInstruction]) -> bool
    """
    Returns True if a section of original_instructions starting somewhere other
    than original_i and matching orig_section is found, i.e. orig_section is duplicated.
    """
    for dup_start in range(len(original_instructions)):
        if dup_start == original_i:
            continue
        dup_section = original_instructions[dup_start : dup_start + len(orig_section)]
        if len(dup_section) < len(orig_section):
            return False
        if sections_match(orig_section, dup_section):
            return True
    
    return False

def sections_match(orig_section, dup_section):
    # type: (List[EnhancedInstruction], List[EnhancedInstruction]) -> bool
    """
    Returns True if the given lists of instructions have matching linenos and opnames.
    """
    return all(
        (
            orig_inst.lineno == dup_inst.lineno
            # POP_BLOCKs have been found to have differing linenos in innocent cases
            or "POP_BLOCK" == orig_inst.opname == dup_inst.opname
        )
        and opnames_match(orig_inst, dup_inst)
        for orig_inst, dup_inst in zip(orig_section, dup_section)
    )


def opnames_match(inst1, inst2):
    # type: (Instruction, Instruction) -> bool
    return (
        inst1.opname == inst2.opname
        or "JUMP" in inst1.opname
        and "JUMP" in inst2.opname
        or (inst1.opname == "PRINT_EXPR" and inst2.opname == "POP_TOP")
        or (
            inst1.opname in ("LOAD_METHOD", "LOOKUP_METHOD")
            and inst2.opname == "LOAD_ATTR"
        )
        or (inst1.opname == "CALL_METHOD" and inst2.opname == "CALL_FUNCTION")
    )


def get_setter(node):
    # type: (EnhancedAST) -> Optional[Callable[[ast.AST], None]]
    parent = node.parent
    for name, field in ast.iter_fields(parent):
        if field is node:
            def setter(new_node):
                # type: (ast.AST) -> None
                return setattr(parent, name, new_node)
            return setter
        elif isinstance(field, list):
            for i, item in enumerate(field):
                if item is node:
                    def setter(new_node):
                        # type: (ast.AST) -> None
                        field[i] = new_node

                    return setter
    return None

lock = RLock()


@cache
def statement_containing_node(node):
    # type: (ast.AST) -> EnhancedAST
    while not isinstance(node, ast.stmt):
        node = cast(EnhancedAST, node).parent
    return cast(EnhancedAST, node)


def assert_linenos(tree):
    # type: (ast.AST) -> Iterator[int]
    for node in ast.walk(tree):
        if (
                hasattr(node, 'parent') and
                isinstance(statement_containing_node(node), ast.Assert)
        ):
            for lineno in node_linenos(node):
                yield lineno


def _extract_ipython_statement(stmt):
    # type: (EnhancedAST) -> ast.Module
    # IPython separates each statement in a cell to be executed separately
    # So NodeFinder should only compile one statement at a time or it
    # will find a code mismatch.
    while not isinstance(stmt.parent, ast.Module):
        stmt = stmt.parent
    # use `ast.parse` instead of `ast.Module` for better portability
    # python3.8 changes the signature of `ast.Module`
    # Inspired by https://github.com/pallets/werkzeug/pull/1552/files
    tree = ast.parse("")
    tree.body = [cast(ast.stmt, stmt)]
    ast.copy_location(tree, stmt)
    return tree


def is_ipython_cell_code_name(code_name):
    # type: (str) -> bool
    return bool(re.match(r"(<module>|<cell line: \d+>)$", code_name))


def is_ipython_cell_filename(filename):
    # type: (str) -> bool
    return bool(re.search(r"<ipython-input-|[/\\]ipykernel_\d+[/\\]", filename))


def is_ipython_cell_code(code_obj):
    # type: (types.CodeType) -> bool
    return (
        is_ipython_cell_filename(code_obj.co_filename) and
        is_ipython_cell_code_name(code_obj.co_name)
    )


def find_node_ipython(frame, lasti, stmts, source):
    # type: (types.FrameType, int, Set[EnhancedAST], Source) -> Tuple[Optional[Any], Optional[Any]]
    node = decorator = None
    for stmt in stmts:
        tree = _extract_ipython_statement(stmt)
        try:
            node_finder = NodeFinder(frame, stmts, tree, lasti, source)
            if (node or decorator) and (node_finder.result or node_finder.decorator):
                # Found potential nodes in separate statements,
                # cannot resolve ambiguity, give up here
                return None, None

            node = node_finder.result
            decorator = node_finder.decorator
        except Exception:
            pass
    return decorator, node


def attr_names_match(attr, argval):
    # type: (str, str) -> bool
    """
    Checks that the user-visible attr (from ast) can correspond to
    the argval in the bytecode, i.e. the real attribute fetched internally,
    which may be mangled for private attributes.
    """
    if attr == argval:
        return True
    if not attr.startswith("__"):
        return False
    return bool(re.match(r"^_\w+%s$" % attr, argval))


def node_linenos(node):
    # type: (ast.AST) -> Iterator[int]
    if hasattr(node, "lineno"):
        linenos = [] # type: Sequence[int]
        if hasattr(node, "end_lineno") and isinstance(node, ast.expr):
            assert node.end_lineno is not None # type: ignore[attr-defined]
            linenos = range(node.lineno, node.end_lineno + 1) # type: ignore[attr-defined]
        else:
            linenos = [node.lineno] # type: ignore[attr-defined]
        for lineno in linenos:
            yield lineno


if sys.version_info >= (3, 11):
    from ._position_node_finder import PositionNodeFinder as NodeFinder
else:
    NodeFinder = SentinelNodeFinder


# === NexusCore/openenv\Lib\site-packages\openai\resources\completions.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, List, Union, Iterable, Optional
from typing_extensions import Literal, overload

import httpx

from .. import _legacy_response
from ..types import completion_create_params
from .._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from .._utils import required_args, maybe_transform, async_maybe_transform
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from .._streaming import Stream, AsyncStream
from .._base_client import (
    make_request_options,
)
from ..types.completion import Completion
from ..types.chat.chat_completion_stream_options_param import ChatCompletionStreamOptionsParam

__all__ = ["Completions", "AsyncCompletions"]


class Completions(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> CompletionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return CompletionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> CompletionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return CompletionsWithStreamingResponse(self)

    @overload
    def create(
        self,
        *,
        model: Union[str, Literal["gpt-3.5-turbo-instruct", "davinci-002", "babbage-002"]],
        prompt: Union[str, List[str], Iterable[int], Iterable[Iterable[int]], None],
        best_of: Optional[int] | NotGiven = NOT_GIVEN,
        echo: Optional[bool] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        suffix: Optional[str] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion:
        """
        Creates a completion for the provided prompt and parameters.

        Args:
          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          prompt: The prompt(s) to generate completions for, encoded as a string, array of
              strings, array of tokens, or array of token arrays.

              Note that <|endoftext|> is the document separator that the model sees during
              training, so if a prompt is not specified the model will generate as if from the
              beginning of a new document.

          best_of: Generates `best_of` completions server-side and returns the "best" (the one with
              the highest log probability per token). Results cannot be streamed.

              When used with `n`, `best_of` controls the number of candidate completions and
              `n` specifies how many to return – `best_of` must be greater than `n`.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          echo: Echo back the prompt in addition to the completion

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the GPT
              tokenizer) to an associated bias value from -100 to 100. You can use this
              [tokenizer tool](/tokenizer?view=bpe) to convert text to token IDs.
              Mathematically, the bias is added to the logits generated by the model prior to
              sampling. The exact effect will vary per model, but values between -1 and 1
              should decrease or increase likelihood of selection; values like -100 or 100
              should result in a ban or exclusive selection of the relevant token.

              As an example, you can pass `{"50256": -100}` to prevent the <|endoftext|> token
              from being generated.

          logprobs: Include the log probabilities on the `logprobs` most likely output tokens, as
              well the chosen tokens. For example, if `logprobs` is 5, the API will return a
              list of the 5 most likely tokens. The API will always return the `logprob` of
              the sampled token, so there may be up to `logprobs+1` elements in the response.

              The maximum value for `logprobs` is 5.

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the
              completion.

              The token count of your prompt plus `max_tokens` cannot exceed the model's
              context length.
              [Example Python code](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
              for counting tokens.

          n: How many completions to generate for each prompt.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          seed: If specified, our system will make a best effort to sample deterministically,
              such that repeated requests with the same `seed` and parameters should return
              the same result.

              Determinism is not guaranteed, and you should refer to the `system_fingerprint`
              response parameter to monitor changes in the backend.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          stream: Whether to stream back partial progress. If set, tokens will be sent as
              data-only
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format)
              as they become available, with the stream terminated by a `data: [DONE]`
              message.
              [Example Python code](https://cookbook.openai.com/examples/how_to_stream_completions).

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          suffix: The suffix that comes after a completion of inserted text.

              This parameter is only supported for `gpt-3.5-turbo-instruct`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

              We generally recommend altering this or `top_p` but not both.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def create(
        self,
        *,
        model: Union[str, Literal["gpt-3.5-turbo-instruct", "davinci-002", "babbage-002"]],
        prompt: Union[str, List[str], Iterable[int], Iterable[Iterable[int]], None],
        stream: Literal[True],
        best_of: Optional[int] | NotGiven = NOT_GIVEN,
        echo: Optional[bool] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        suffix: Optional[str] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[Completion]:
        """
        Creates a completion for the provided prompt and parameters.

        Args:
          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          prompt: The prompt(s) to generate completions for, encoded as a string, array of
              strings, array of tokens, or array of token arrays.

              Note that <|endoftext|> is the document separator that the model sees during
              training, so if a prompt is not specified the model will generate as if from the
              beginning of a new document.

          stream: Whether to stream back partial progress. If set, tokens will be sent as
              data-only
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format)
              as they become available, with the stream terminated by a `data: [DONE]`
              message.
              [Example Python code](https://cookbook.openai.com/examples/how_to_stream_completions).

          best_of: Generates `best_of` completions server-side and returns the "best" (the one with
              the highest log probability per token). Results cannot be streamed.

              When used with `n`, `best_of` controls the number of candidate completions and
              `n` specifies how many to return – `best_of` must be greater than `n`.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          echo: Echo back the prompt in addition to the completion

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the GPT
              tokenizer) to an associated bias value from -100 to 100. You can use this
              [tokenizer tool](/tokenizer?view=bpe) to convert text to token IDs.
              Mathematically, the bias is added to the logits generated by the model prior to
              sampling. The exact effect will vary per model, but values between -1 and 1
              should decrease or increase likelihood of selection; values like -100 or 100
              should result in a ban or exclusive selection of the relevant token.

              As an example, you can pass `{"50256": -100}` to prevent the <|endoftext|> token
              from being generated.

          logprobs: Include the log probabilities on the `logprobs` most likely output tokens, as
              well the chosen tokens. For example, if `logprobs` is 5, the API will return a
              list of the 5 most likely tokens. The API will always return the `logprob` of
              the sampled token, so there may be up to `logprobs+1` elements in the response.

              The maximum value for `logprobs` is 5.

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the
              completion.

              The token count of your prompt plus `max_tokens` cannot exceed the model's
              context length.
              [Example Python code](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
              for counting tokens.

          n: How many completions to generate for each prompt.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          seed: If specified, our system will make a best effort to sample deterministically,
              such that repeated requests with the same `seed` and parameters should return
              the same result.

              Determinism is not guaranteed, and you should refer to the `system_fingerprint`
              response parameter to monitor changes in the backend.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          suffix: The suffix that comes after a completion of inserted text.

              This parameter is only supported for `gpt-3.5-turbo-instruct`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

              We generally recommend altering this or `top_p` but not both.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def create(
        self,
        *,
        model: Union[str, Literal["gpt-3.5-turbo-instruct", "davinci-002", "babbage-002"]],
        prompt: Union[str, List[str], Iterable[int], Iterable[Iterable[int]], None],
        stream: bool,
        best_of: Optional[int] | NotGiven = NOT_GIVEN,
        echo: Optional[bool] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        suffix: Optional[str] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion | Stream[Completion]:
        """
        Creates a completion for the provided prompt and parameters.

        Args:
          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          prompt: The prompt(s) to generate completions for, encoded as a string, array of
              strings, array of tokens, or array of token arrays.

              Note that <|endoftext|> is the document separator that the model sees during
              training, so if a prompt is not specified the model will generate as if from the
              beginning of a new document.

          stream: Whether to stream back partial progress. If set, tokens will be sent as
              data-only
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format)
              as they become available, with the stream terminated by a `data: [DONE]`
              message.
              [Example Python code](https://cookbook.openai.com/examples/how_to_stream_completions).

          best_of: Generates `best_of` completions server-side and returns the "best" (the one with
              the highest log probability per token). Results cannot be streamed.

              When used with `n`, `best_of` controls the number of candidate completions and
              `n` specifies how many to return – `best_of` must be greater than `n`.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          echo: Echo back the prompt in addition to the completion

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the GPT
              tokenizer) to an associated bias value from -100 to 100. You can use this
              [tokenizer tool](/tokenizer?view=bpe) to convert text to token IDs.
              Mathematically, the bias is added to the logits generated by the model prior to
              sampling. The exact effect will vary per model, but values between -1 and 1
              should decrease or increase likelihood of selection; values like -100 or 100
              should result in a ban or exclusive selection of the relevant token.

              As an example, you can pass `{"50256": -100}` to prevent the <|endoftext|> token
              from being generated.

          logprobs: Include the log probabilities on the `logprobs` most likely output tokens, as
              well the chosen tokens. For example, if `logprobs` is 5, the API will return a
              list of the 5 most likely tokens. The API will always return the `logprob` of
              the sampled token, so there may be up to `logprobs+1` elements in the response.

              The maximum value for `logprobs` is 5.

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the
              completion.

              The token count of your prompt plus `max_tokens` cannot exceed the model's
              context length.
              [Example Python code](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
              for counting tokens.

          n: How many completions to generate for each prompt.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          seed: If specified, our system will make a best effort to sample deterministically,
              such that repeated requests with the same `seed` and parameters should return
              the same result.

              Determinism is not guaranteed, and you should refer to the `system_fingerprint`
              response parameter to monitor changes in the backend.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          suffix: The suffix that comes after a completion of inserted text.

              This parameter is only supported for `gpt-3.5-turbo-instruct`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

              We generally recommend altering this or `top_p` but not both.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["model", "prompt"], ["model", "prompt", "stream"])
    def create(
        self,
        *,
        model: Union[str, Literal["gpt-3.5-turbo-instruct", "davinci-002", "babbage-002"]],
        prompt: Union[str, List[str], Iterable[int], Iterable[Iterable[int]], None],
        best_of: Optional[int] | NotGiven = NOT_GIVEN,
        echo: Optional[bool] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        suffix: Optional[str] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion | Stream[Completion]:
        return self._post(
            "/completions",
            body=maybe_transform(
                {
                    "model": model,
                    "prompt": prompt,
                    "best_of": best_of,
                    "echo": echo,
                    "frequency_penalty": frequency_penalty,
                    "logit_bias": logit_bias,
                    "logprobs": logprobs,
                    "max_tokens": max_tokens,
                    "n": n,
                    "presence_penalty": presence_penalty,
                    "seed": seed,
                    "stop": stop,
                    "stream": stream,
                    "stream_options": stream_options,
                    "suffix": suffix,
                    "temperature": temperature,
                    "top_p": top_p,
                    "user": user,
                },
                completion_create_params.CompletionCreateParamsStreaming
                if stream
                else completion_create_params.CompletionCreateParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Completion,
            stream=stream or False,
            stream_cls=Stream[Completion],
        )


class AsyncCompletions(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncCompletionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncCompletionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncCompletionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncCompletionsWithStreamingResponse(self)

    @overload
    async def create(
        self,
        *,
        model: Union[str, Literal["gpt-3.5-turbo-instruct", "davinci-002", "babbage-002"]],
        prompt: Union[str, List[str], Iterable[int], Iterable[Iterable[int]], None],
        best_of: Optional[int] | NotGiven = NOT_GIVEN,
        echo: Optional[bool] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        suffix: Optional[str] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion:
        """
        Creates a completion for the provided prompt and parameters.

        Args:
          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          prompt: The prompt(s) to generate completions for, encoded as a string, array of
              strings, array of tokens, or array of token arrays.

              Note that <|endoftext|> is the document separator that the model sees during
              training, so if a prompt is not specified the model will generate as if from the
              beginning of a new document.

          best_of: Generates `best_of` completions server-side and returns the "best" (the one with
              the highest log probability per token). Results cannot be streamed.

              When used with `n`, `best_of` controls the number of candidate completions and
              `n` specifies how many to return – `best_of` must be greater than `n`.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          echo: Echo back the prompt in addition to the completion

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the GPT
              tokenizer) to an associated bias value from -100 to 100. You can use this
              [tokenizer tool](/tokenizer?view=bpe) to convert text to token IDs.
              Mathematically, the bias is added to the logits generated by the model prior to
              sampling. The exact effect will vary per model, but values between -1 and 1
              should decrease or increase likelihood of selection; values like -100 or 100
              should result in a ban or exclusive selection of the relevant token.

              As an example, you can pass `{"50256": -100}` to prevent the <|endoftext|> token
              from being generated.

          logprobs: Include the log probabilities on the `logprobs` most likely output tokens, as
              well the chosen tokens. For example, if `logprobs` is 5, the API will return a
              list of the 5 most likely tokens. The API will always return the `logprob` of
              the sampled token, so there may be up to `logprobs+1` elements in the response.

              The maximum value for `logprobs` is 5.

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the
              completion.

              The token count of your prompt plus `max_tokens` cannot exceed the model's
              context length.
              [Example Python code](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
              for counting tokens.

          n: How many completions to generate for each prompt.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          seed: If specified, our system will make a best effort to sample deterministically,
              such that repeated requests with the same `seed` and parameters should return
              the same result.

              Determinism is not guaranteed, and you should refer to the `system_fingerprint`
              response parameter to monitor changes in the backend.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          stream: Whether to stream back partial progress. If set, tokens will be sent as
              data-only
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format)
              as they become available, with the stream terminated by a `data: [DONE]`
              message.
              [Example Python code](https://cookbook.openai.com/examples/how_to_stream_completions).

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          suffix: The suffix that comes after a completion of inserted text.

              This parameter is only supported for `gpt-3.5-turbo-instruct`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

              We generally recommend altering this or `top_p` but not both.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def create(
        self,
        *,
        model: Union[str, Literal["gpt-3.5-turbo-instruct", "davinci-002", "babbage-002"]],
        prompt: Union[str, List[str], Iterable[int], Iterable[Iterable[int]], None],
        stream: Literal[True],
        best_of: Optional[int] | NotGiven = NOT_GIVEN,
        echo: Optional[bool] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        suffix: Optional[str] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[Completion]:
        """
        Creates a completion for the provided prompt and parameters.

        Args:
          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          prompt: The prompt(s) to generate completions for, encoded as a string, array of
              strings, array of tokens, or array of token arrays.

              Note that <|endoftext|> is the document separator that the model sees during
              training, so if a prompt is not specified the model will generate as if from the
              beginning of a new document.

          stream: Whether to stream back partial progress. If set, tokens will be sent as
              data-only
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format)
              as they become available, with the stream terminated by a `data: [DONE]`
              message.
              [Example Python code](https://cookbook.openai.com/examples/how_to_stream_completions).

          best_of: Generates `best_of` completions server-side and returns the "best" (the one with
              the highest log probability per token). Results cannot be streamed.

              When used with `n`, `best_of` controls the number of candidate completions and
              `n` specifies how many to return – `best_of` must be greater than `n`.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          echo: Echo back the prompt in addition to the completion

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the GPT
              tokenizer) to an associated bias value from -100 to 100. You can use this
              [tokenizer tool](/tokenizer?view=bpe) to convert text to token IDs.
              Mathematically, the bias is added to the logits generated by the model prior to
              sampling. The exact effect will vary per model, but values between -1 and 1
              should decrease or increase likelihood of selection; values like -100 or 100
              should result in a ban or exclusive selection of the relevant token.

              As an example, you can pass `{"50256": -100}` to prevent the <|endoftext|> token
              from being generated.

          logprobs: Include the log probabilities on the `logprobs` most likely output tokens, as
              well the chosen tokens. For example, if `logprobs` is 5, the API will return a
              list of the 5 most likely tokens. The API will always return the `logprob` of
              the sampled token, so there may be up to `logprobs+1` elements in the response.

              The maximum value for `logprobs` is 5.

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the
              completion.

              The token count of your prompt plus `max_tokens` cannot exceed the model's
              context length.
              [Example Python code](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
              for counting tokens.

          n: How many completions to generate for each prompt.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          seed: If specified, our system will make a best effort to sample deterministically,
              such that repeated requests with the same `seed` and parameters should return
              the same result.

              Determinism is not guaranteed, and you should refer to the `system_fingerprint`
              response parameter to monitor changes in the backend.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          suffix: The suffix that comes after a completion of inserted text.

              This parameter is only supported for `gpt-3.5-turbo-instruct`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

              We generally recommend altering this or `top_p` but not both.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def create(
        self,
        *,
        model: Union[str, Literal["gpt-3.5-turbo-instruct", "davinci-002", "babbage-002"]],
        prompt: Union[str, List[str], Iterable[int], Iterable[Iterable[int]], None],
        stream: bool,
        best_of: Optional[int] | NotGiven = NOT_GIVEN,
        echo: Optional[bool] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        suffix: Optional[str] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion | AsyncStream[Completion]:
        """
        Creates a completion for the provided prompt and parameters.

        Args:
          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          prompt: The prompt(s) to generate completions for, encoded as a string, array of
              strings, array of tokens, or array of token arrays.

              Note that <|endoftext|> is the document separator that the model sees during
              training, so if a prompt is not specified the model will generate as if from the
              beginning of a new document.

          stream: Whether to stream back partial progress. If set, tokens will be sent as
              data-only
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format)
              as they become available, with the stream terminated by a `data: [DONE]`
              message.
              [Example Python code](https://cookbook.openai.com/examples/how_to_stream_completions).

          best_of: Generates `best_of` completions server-side and returns the "best" (the one with
              the highest log probability per token). Results cannot be streamed.

              When used with `n`, `best_of` controls the number of candidate completions and
              `n` specifies how many to return – `best_of` must be greater than `n`.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          echo: Echo back the prompt in addition to the completion

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the GPT
              tokenizer) to an associated bias value from -100 to 100. You can use this
              [tokenizer tool](/tokenizer?view=bpe) to convert text to token IDs.
              Mathematically, the bias is added to the logits generated by the model prior to
              sampling. The exact effect will vary per model, but values between -1 and 1
              should decrease or increase likelihood of selection; values like -100 or 100
              should result in a ban or exclusive selection of the relevant token.

              As an example, you can pass `{"50256": -100}` to prevent the <|endoftext|> token
              from being generated.

          logprobs: Include the log probabilities on the `logprobs` most likely output tokens, as
              well the chosen tokens. For example, if `logprobs` is 5, the API will return a
              list of the 5 most likely tokens. The API will always return the `logprob` of
              the sampled token, so there may be up to `logprobs+1` elements in the response.

              The maximum value for `logprobs` is 5.

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the
              completion.

              The token count of your prompt plus `max_tokens` cannot exceed the model's
              context length.
              [Example Python code](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
              for counting tokens.

          n: How many completions to generate for each prompt.

              **Note:** Because this parameter generates many completions, it can quickly
              consume your token quota. Use carefully and ensure that you have reasonable
              settings for `max_tokens` and `stop`.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

              [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)

          seed: If specified, our system will make a best effort to sample deterministically,
              such that repeated requests with the same `seed` and parameters should return
              the same result.

              Determinism is not guaranteed, and you should refer to the `system_fingerprint`
              response parameter to monitor changes in the backend.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          suffix: The suffix that comes after a completion of inserted text.

              This parameter is only supported for `gpt-3.5-turbo-instruct`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

              We generally recommend altering this or `top_p` but not both.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["model", "prompt"], ["model", "prompt", "stream"])
    async def create(
        self,
        *,
        model: Union[str, Literal["gpt-3.5-turbo-instruct", "davinci-002", "babbage-002"]],
        prompt: Union[str, List[str], Iterable[int], Iterable[Iterable[int]], None],
        best_of: Optional[int] | NotGiven = NOT_GIVEN,
        echo: Optional[bool] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        suffix: Optional[str] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion | AsyncStream[Completion]:
        return await self._post(
            "/completions",
            body=await async_maybe_transform(
                {
                    "model": model,
                    "prompt": prompt,
                    "best_of": best_of,
                    "echo": echo,
                    "frequency_penalty": frequency_penalty,
                    "logit_bias": logit_bias,
                    "logprobs": logprobs,
                    "max_tokens": max_tokens,
                    "n": n,
                    "presence_penalty": presence_penalty,
                    "seed": seed,
                    "stop": stop,
                    "stream": stream,
                    "stream_options": stream_options,
                    "suffix": suffix,
                    "temperature": temperature,
                    "top_p": top_p,
                    "user": user,
                },
                completion_create_params.CompletionCreateParamsStreaming
                if stream
                else completion_create_params.CompletionCreateParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Completion,
            stream=stream or False,
            stream_cls=AsyncStream[Completion],
        )


class CompletionsWithRawResponse:
    def __init__(self, completions: Completions) -> None:
        self._completions = completions

        self.create = _legacy_response.to_raw_response_wrapper(
            completions.create,
        )


class AsyncCompletionsWithRawResponse:
    def __init__(self, completions: AsyncCompletions) -> None:
        self._completions = completions

        self.create = _legacy_response.async_to_raw_response_wrapper(
            completions.create,
        )


class CompletionsWithStreamingResponse:
    def __init__(self, completions: Completions) -> None:
        self._completions = completions

        self.create = to_streamed_response_wrapper(
            completions.create,
        )


class AsyncCompletionsWithStreamingResponse:
    def __init__(self, completions: AsyncCompletions) -> None:
        self._completions = completions

        self.create = async_to_streamed_response_wrapper(
            completions.create,
        )

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\ttFont.py ===
from fontTools.config import Config
from fontTools.misc import xmlWriter
from fontTools.misc.configTools import AbstractConfig
from fontTools.misc.textTools import Tag, byteord, tostr
from fontTools.misc.loggingTools import deprecateArgument
from fontTools.ttLib import TTLibError
from fontTools.ttLib.ttGlyphSet import (
    _TTGlyph,
    _TTGlyphSetCFF,
    _TTGlyphSetGlyf,
    _TTGlyphSetVARC,
)
from fontTools.ttLib.sfnt import SFNTReader, SFNTWriter
from io import BytesIO, StringIO, UnsupportedOperation
import os
import logging
import traceback

log = logging.getLogger(__name__)


class TTFont(object):
    """Represents a TrueType font.

    The object manages file input and output, and offers a convenient way of
    accessing tables. Tables will be only decompiled when necessary, ie. when
    they're actually accessed. This means that simple operations can be extremely fast.

    Example usage:

    .. code-block:: pycon

        >>>
        >> from fontTools import ttLib
        >> tt = ttLib.TTFont("afont.ttf") # Load an existing font file
        >> tt['maxp'].numGlyphs
        242
        >> tt['OS/2'].achVendID
        'B&H\000'
        >> tt['head'].unitsPerEm
        2048

    For details of the objects returned when accessing each table, see the
    :doc:`tables </ttLib/tables>` documentation.
    To add a table to the font, use the :py:func:`newTable` function:

    .. code-block:: pycon

        >>>
        >> os2 = newTable("OS/2")
        >> os2.version = 4
        >> # set other attributes
        >> font["OS/2"] = os2

    TrueType fonts can also be serialized to and from XML format (see also the
    :doc:`ttx </ttx>` binary):

    .. code-block:: pycon

        >>
        >> tt.saveXML("afont.ttx")
        Dumping 'LTSH' table...
        Dumping 'OS/2' table...
        [...]

        >> tt2 = ttLib.TTFont() # Create a new font object
        >> tt2.importXML("afont.ttx")
        >> tt2['maxp'].numGlyphs
        242

    The TTFont object may be used as a context manager; this will cause the file
    reader to be closed after the context ``with`` block is exited::

            with TTFont(filename) as f:
                    # Do stuff

    Args:
            file: When reading a font from disk, either a pathname pointing to a file,
                    or a readable file object.
            res_name_or_index: If running on a Macintosh, either a sfnt resource name or
                    an sfnt resource index number. If the index number is zero, TTLib will
                    autodetect whether the file is a flat file or a suitcase. (If it is a suitcase,
                    only the first 'sfnt' resource will be read.)
            sfntVersion (str): When constructing a font object from scratch, sets the four-byte
                    sfnt magic number to be used. Defaults to ``\0\1\0\0`` (TrueType). To create
                    an OpenType file, use ``OTTO``.
            flavor (str): Set this to ``woff`` when creating a WOFF file or ``woff2`` for a WOFF2
                    file.
            checkChecksums (int): How checksum data should be treated. Default is 0
                    (no checking). Set to 1 to check and warn on wrong checksums; set to 2 to
                    raise an exception if any wrong checksums are found.
            recalcBBoxes (bool): If true (the default), recalculates ``glyf``, ``CFF ``,
                    ``head`` bounding box values and ``hhea``/``vhea`` min/max values on save.
                    Also compiles the glyphs on importing, which saves memory consumption and
                    time.
            ignoreDecompileErrors (bool): If true, exceptions raised during table decompilation
                    will be ignored, and the binary data will be returned for those tables instead.
            recalcTimestamp (bool): If true (the default), sets the ``modified`` timestamp in
                    the ``head`` table on save.
            fontNumber (int): The index of the font in a TrueType Collection file.
            lazy (bool): If lazy is set to True, many data structures are loaded lazily, upon
                    access only. If it is set to False, many data structures are loaded immediately.
                    The default is ``lazy=None`` which is somewhere in between.
    """

    def __init__(
        self,
        file=None,
        res_name_or_index=None,
        sfntVersion="\000\001\000\000",
        flavor=None,
        checkChecksums=0,
        verbose=None,
        recalcBBoxes=True,
        allowVID=NotImplemented,
        ignoreDecompileErrors=False,
        recalcTimestamp=True,
        fontNumber=-1,
        lazy=None,
        quiet=None,
        _tableCache=None,
        cfg={},
    ):
        for name in ("verbose", "quiet"):
            val = locals().get(name)
            if val is not None:
                deprecateArgument(name, "configure logging instead")
            setattr(self, name, val)

        self.lazy = lazy
        self.recalcBBoxes = recalcBBoxes
        self.recalcTimestamp = recalcTimestamp
        self.tables = {}
        self.reader = None
        self.cfg = cfg.copy() if isinstance(cfg, AbstractConfig) else Config(cfg)
        self.ignoreDecompileErrors = ignoreDecompileErrors

        if not file:
            self.sfntVersion = sfntVersion
            self.flavor = flavor
            self.flavorData = None
            return
        seekable = True
        if not hasattr(file, "read"):
            closeStream = True
            # assume file is a string
            if res_name_or_index is not None:
                # see if it contains 'sfnt' resources in the resource or data fork
                from . import macUtils

                if res_name_or_index == 0:
                    if macUtils.getSFNTResIndices(file):
                        # get the first available sfnt font.
                        file = macUtils.SFNTResourceReader(file, 1)
                    else:
                        file = open(file, "rb")
                else:
                    file = macUtils.SFNTResourceReader(file, res_name_or_index)
            else:
                file = open(file, "rb")
        else:
            # assume "file" is a readable file object
            closeStream = False
            # SFNTReader wants the input file to be seekable.
            # SpooledTemporaryFile has no seekable() on < 3.11, but still can seek:
            # https://github.com/fonttools/fonttools/issues/3052
            if hasattr(file, "seekable"):
                seekable = file.seekable()
            elif hasattr(file, "seek"):
                try:
                    file.seek(0)
                except UnsupportedOperation:
                    seekable = False

        if not self.lazy:
            # read input file in memory and wrap a stream around it to allow overwriting
            if seekable:
                file.seek(0)
            tmp = BytesIO(file.read())
            if hasattr(file, "name"):
                # save reference to input file name
                tmp.name = file.name
            if closeStream:
                file.close()
            file = tmp
        elif not seekable:
            raise TTLibError("Input file must be seekable when lazy=True")
        self._tableCache = _tableCache
        self.reader = SFNTReader(file, checkChecksums, fontNumber=fontNumber)
        self.sfntVersion = self.reader.sfntVersion
        self.flavor = self.reader.flavor
        self.flavorData = self.reader.flavorData

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        """If we still have a reader object, close it."""
        if self.reader is not None:
            self.reader.close()

    def save(self, file, reorderTables=True):
        """Save the font to disk.

        Args:
                file: Similarly to the constructor, can be either a pathname or a writable
                        file object.
                reorderTables (Option[bool]): If true (the default), reorder the tables,
                        sorting them by tag (recommended by the OpenType specification). If
                        false, retain the original font order. If None, reorder by table
                        dependency (fastest).
        """
        if not hasattr(file, "write"):
            if self.lazy and self.reader.file.name == file:
                raise TTLibError("Can't overwrite TTFont when 'lazy' attribute is True")
            createStream = True
        else:
            # assume "file" is a writable file object
            createStream = False

        tmp = BytesIO()

        writer_reordersTables = self._save(tmp)

        if not (
            reorderTables is None
            or writer_reordersTables
            or (reorderTables is False and self.reader is None)
        ):
            if reorderTables is False:
                # sort tables using the original font's order
                tableOrder = list(self.reader.keys())
            else:
                # use the recommended order from the OpenType specification
                tableOrder = None
            tmp.flush()
            tmp2 = BytesIO()
            reorderFontTables(tmp, tmp2, tableOrder)
            tmp.close()
            tmp = tmp2

        if createStream:
            # "file" is a path
            with open(file, "wb") as file:
                file.write(tmp.getvalue())
        else:
            file.write(tmp.getvalue())

        tmp.close()

    def _save(self, file, tableCache=None):
        """Internal function, to be shared by save() and TTCollection.save()"""

        if self.recalcTimestamp and "head" in self:
            self[
                "head"
            ]  # make sure 'head' is loaded so the recalculation is actually done

        tags = list(self.keys())
        if "GlyphOrder" in tags:
            tags.remove("GlyphOrder")
        numTables = len(tags)
        # write to a temporary stream to allow saving to unseekable streams
        writer = SFNTWriter(
            file, numTables, self.sfntVersion, self.flavor, self.flavorData
        )

        done = []
        for tag in tags:
            self._writeTable(tag, writer, done, tableCache)

        writer.close()

        return writer.reordersTables()

    def saveXML(self, fileOrPath, newlinestr="\n", **kwargs):
        """Export the font as TTX (an XML-based text file), or as a series of text
        files when splitTables is true. In the latter case, the 'fileOrPath'
        argument should be a path to a directory.
        The 'tables' argument must either be false (dump all tables) or a
        list of tables to dump. The 'skipTables' argument may be a list of tables
        to skip, but only when the 'tables' argument is false.
        """

        writer = xmlWriter.XMLWriter(fileOrPath, newlinestr=newlinestr)
        self._saveXML(writer, **kwargs)
        writer.close()

    def _saveXML(
        self,
        writer,
        writeVersion=True,
        quiet=None,
        tables=None,
        skipTables=None,
        splitTables=False,
        splitGlyphs=False,
        disassembleInstructions=True,
        bitmapGlyphDataFormat="raw",
    ):
        if quiet is not None:
            deprecateArgument("quiet", "configure logging instead")

        self.disassembleInstructions = disassembleInstructions
        self.bitmapGlyphDataFormat = bitmapGlyphDataFormat
        if not tables:
            tables = list(self.keys())
            if "GlyphOrder" not in tables:
                tables = ["GlyphOrder"] + tables
            if skipTables:
                for tag in skipTables:
                    if tag in tables:
                        tables.remove(tag)
        numTables = len(tables)

        if writeVersion:
            from fontTools import version

            version = ".".join(version.split(".")[:2])
            writer.begintag(
                "ttFont",
                sfntVersion=repr(tostr(self.sfntVersion))[1:-1],
                ttLibVersion=version,
            )
        else:
            writer.begintag("ttFont", sfntVersion=repr(tostr(self.sfntVersion))[1:-1])
        writer.newline()

        # always splitTables if splitGlyphs is enabled
        splitTables = splitTables or splitGlyphs

        if not splitTables:
            writer.newline()
        else:
            path, ext = os.path.splitext(writer.filename)

        for i in range(numTables):
            tag = tables[i]
            if splitTables:
                tablePath = path + "." + tagToIdentifier(tag) + ext
                tableWriter = xmlWriter.XMLWriter(
                    tablePath, newlinestr=writer.newlinestr
                )
                tableWriter.begintag("ttFont", ttLibVersion=version)
                tableWriter.newline()
                tableWriter.newline()
                writer.simpletag(tagToXML(tag), src=os.path.basename(tablePath))
                writer.newline()
            else:
                tableWriter = writer
            self._tableToXML(tableWriter, tag, splitGlyphs=splitGlyphs)
            if splitTables:
                tableWriter.endtag("ttFont")
                tableWriter.newline()
                tableWriter.close()
        writer.endtag("ttFont")
        writer.newline()

    def _tableToXML(self, writer, tag, quiet=None, splitGlyphs=False):
        if quiet is not None:
            deprecateArgument("quiet", "configure logging instead")
        if tag in self:
            table = self[tag]
            report = "Dumping '%s' table..." % tag
        else:
            report = "No '%s' table found." % tag
        log.info(report)
        if tag not in self:
            return
        xmlTag = tagToXML(tag)
        attrs = dict()
        if hasattr(table, "ERROR"):
            attrs["ERROR"] = "decompilation error"
        from .tables.DefaultTable import DefaultTable

        if table.__class__ == DefaultTable:
            attrs["raw"] = True
        writer.begintag(xmlTag, **attrs)
        writer.newline()
        if tag == "glyf":
            table.toXML(writer, self, splitGlyphs=splitGlyphs)
        else:
            table.toXML(writer, self)
        writer.endtag(xmlTag)
        writer.newline()
        writer.newline()

    def importXML(self, fileOrPath, quiet=None):
        """Import a TTX file (an XML-based text format), so as to recreate
        a font object.
        """
        if quiet is not None:
            deprecateArgument("quiet", "configure logging instead")

        if "maxp" in self and "post" in self:
            # Make sure the glyph order is loaded, as it otherwise gets
            # lost if the XML doesn't contain the glyph order, yet does
            # contain the table which was originally used to extract the
            # glyph names from (ie. 'post', 'cmap' or 'CFF ').
            self.getGlyphOrder()

        from fontTools.misc import xmlReader

        reader = xmlReader.XMLReader(fileOrPath, self)
        reader.read()

    def isLoaded(self, tag):
        """Return true if the table identified by ``tag`` has been
        decompiled and loaded into memory."""
        return tag in self.tables

    def has_key(self, tag):
        """Test if the table identified by ``tag`` is present in the font.

        As well as this method, ``tag in font`` can also be used to determine the
        presence of the table."""
        if self.isLoaded(tag):
            return True
        elif self.reader and tag in self.reader:
            return True
        elif tag == "GlyphOrder":
            return True
        else:
            return False

    __contains__ = has_key

    def keys(self):
        """Returns the list of tables in the font, along with the ``GlyphOrder`` pseudo-table."""
        keys = list(self.tables.keys())
        if self.reader:
            for key in list(self.reader.keys()):
                if key not in keys:
                    keys.append(key)

        if "GlyphOrder" in keys:
            keys.remove("GlyphOrder")
        keys = sortedTagList(keys)
        return ["GlyphOrder"] + keys

    def ensureDecompiled(self, recurse=None):
        """Decompile all the tables, even if a TTFont was opened in 'lazy' mode."""
        for tag in self.keys():
            table = self[tag]
            if recurse is None:
                recurse = self.lazy is not False
            if recurse and hasattr(table, "ensureDecompiled"):
                table.ensureDecompiled(recurse=recurse)
        self.lazy = False

    def __len__(self):
        return len(list(self.keys()))

    def __getitem__(self, tag):
        tag = Tag(tag)
        table = self.tables.get(tag)
        if table is None:
            if tag == "GlyphOrder":
                table = GlyphOrder(tag)
                self.tables[tag] = table
            elif self.reader is not None:
                table = self._readTable(tag)
            else:
                raise KeyError("'%s' table not found" % tag)
        return table

    def _readTable(self, tag):
        log.debug("Reading '%s' table from disk", tag)
        data = self.reader[tag]
        if self._tableCache is not None:
            table = self._tableCache.get((tag, data))
            if table is not None:
                return table
        tableClass = getTableClass(tag)
        table = tableClass(tag)
        self.tables[tag] = table
        log.debug("Decompiling '%s' table", tag)
        try:
            table.decompile(data, self)
        except Exception:
            if not self.ignoreDecompileErrors:
                raise
            # fall back to DefaultTable, retaining the binary table data
            log.exception(
                "An exception occurred during the decompilation of the '%s' table", tag
            )
            from .tables.DefaultTable import DefaultTable

            file = StringIO()
            traceback.print_exc(file=file)
            table = DefaultTable(tag)
            table.ERROR = file.getvalue()
            self.tables[tag] = table
            table.decompile(data, self)
        if self._tableCache is not None:
            self._tableCache[(tag, data)] = table
        return table

    def __setitem__(self, tag, table):
        self.tables[Tag(tag)] = table

    def __delitem__(self, tag):
        if tag not in self:
            raise KeyError("'%s' table not found" % tag)
        if tag in self.tables:
            del self.tables[tag]
        if self.reader and tag in self.reader:
            del self.reader[tag]

    def get(self, tag, default=None):
        """Returns the table if it exists or (optionally) a default if it doesn't."""
        try:
            return self[tag]
        except KeyError:
            return default

    def setGlyphOrder(self, glyphOrder):
        """Set the glyph order

        Args:
                glyphOrder ([str]): List of glyph names in order.
        """
        self.glyphOrder = glyphOrder
        if hasattr(self, "_reverseGlyphOrderDict"):
            del self._reverseGlyphOrderDict
        if self.isLoaded("glyf"):
            self["glyf"].setGlyphOrder(glyphOrder)

    def getGlyphOrder(self):
        """Returns a list of glyph names ordered by their position in the font."""
        try:
            return self.glyphOrder
        except AttributeError:
            pass
        if "CFF " in self:
            cff = self["CFF "]
            self.glyphOrder = cff.getGlyphOrder()
        elif "post" in self:
            # TrueType font
            glyphOrder = self["post"].getGlyphOrder()
            if glyphOrder is None:
                #
                # No names found in the 'post' table.
                # Try to create glyph names from the unicode cmap (if available)
                # in combination with the Adobe Glyph List (AGL).
                #
                self._getGlyphNamesFromCmap()
            elif len(glyphOrder) < self["maxp"].numGlyphs:
                #
                # Not enough names found in the 'post' table.
                # Can happen when 'post' format 1 is improperly used on a font that
                # has more than 258 glyphs (the length of 'standardGlyphOrder').
                #
                log.warning(
                    "Not enough names found in the 'post' table, generating them from cmap instead"
                )
                self._getGlyphNamesFromCmap()
            else:
                self.glyphOrder = glyphOrder
        else:
            self._getGlyphNamesFromCmap()
        return self.glyphOrder

    def _getGlyphNamesFromCmap(self):
        #
        # This is rather convoluted, but then again, it's an interesting problem:
        # - we need to use the unicode values found in the cmap table to
        #   build glyph names (eg. because there is only a minimal post table,
        #   or none at all).
        # - but the cmap parser also needs glyph names to work with...
        # So here's what we do:
        # - make up glyph names based on glyphID
        # - load a temporary cmap table based on those names
        # - extract the unicode values, build the "real" glyph names
        # - unload the temporary cmap table
        #
        if self.isLoaded("cmap"):
            # Bootstrapping: we're getting called by the cmap parser
            # itself. This means self.tables['cmap'] contains a partially
            # loaded cmap, making it impossible to get at a unicode
            # subtable here. We remove the partially loaded cmap and
            # restore it later.
            # This only happens if the cmap table is loaded before any
            # other table that does f.getGlyphOrder()  or f.getGlyphName().
            cmapLoading = self.tables["cmap"]
            del self.tables["cmap"]
        else:
            cmapLoading = None
        # Make up glyph names based on glyphID, which will be used by the
        # temporary cmap and by the real cmap in case we don't find a unicode
        # cmap.
        numGlyphs = int(self["maxp"].numGlyphs)
        glyphOrder = ["glyph%.5d" % i for i in range(numGlyphs)]
        glyphOrder[0] = ".notdef"
        # Set the glyph order, so the cmap parser has something
        # to work with (so we don't get called recursively).
        self.glyphOrder = glyphOrder

        # Make up glyph names based on the reversed cmap table. Because some
        # glyphs (eg. ligatures or alternates) may not be reachable via cmap,
        # this naming table will usually not cover all glyphs in the font.
        # If the font has no Unicode cmap table, reversecmap will be empty.
        if "cmap" in self:
            reversecmap = self["cmap"].buildReversedMin()
        else:
            reversecmap = {}
        useCount = {}
        for i in range(numGlyphs):
            tempName = glyphOrder[i]
            if tempName in reversecmap:
                # If a font maps both U+0041 LATIN CAPITAL LETTER A and
                # U+0391 GREEK CAPITAL LETTER ALPHA to the same glyph,
                # we prefer naming the glyph as "A".
                glyphName = self._makeGlyphName(reversecmap[tempName])
                numUses = useCount[glyphName] = useCount.get(glyphName, 0) + 1
                if numUses > 1:
                    glyphName = "%s.alt%d" % (glyphName, numUses - 1)
                glyphOrder[i] = glyphName

        if "cmap" in self:
            # Delete the temporary cmap table from the cache, so it can
            # be parsed again with the right names.
            del self.tables["cmap"]
            self.glyphOrder = glyphOrder
            if cmapLoading:
                # restore partially loaded cmap, so it can continue loading
                # using the proper names.
                self.tables["cmap"] = cmapLoading

    @staticmethod
    def _makeGlyphName(codepoint):
        from fontTools import agl  # Adobe Glyph List

        if codepoint in agl.UV2AGL:
            return agl.UV2AGL[codepoint]
        elif codepoint <= 0xFFFF:
            return "uni%04X" % codepoint
        else:
            return "u%X" % codepoint

    def getGlyphNames(self):
        """Get a list of glyph names, sorted alphabetically."""
        glyphNames = sorted(self.getGlyphOrder())
        return glyphNames

    def getGlyphNames2(self):
        """Get a list of glyph names, sorted alphabetically,
        but not case sensitive.
        """
        from fontTools.misc import textTools

        return textTools.caselessSort(self.getGlyphOrder())

    def getGlyphName(self, glyphID):
        """Returns the name for the glyph with the given ID.

        If no name is available, synthesises one with the form ``glyphXXXXX``` where
        ```XXXXX`` is the zero-padded glyph ID.
        """
        try:
            return self.getGlyphOrder()[glyphID]
        except IndexError:
            return "glyph%.5d" % glyphID

    def getGlyphNameMany(self, lst):
        """Converts a list of glyph IDs into a list of glyph names."""
        glyphOrder = self.getGlyphOrder()
        cnt = len(glyphOrder)
        return [glyphOrder[gid] if gid < cnt else "glyph%.5d" % gid for gid in lst]

    def getGlyphID(self, glyphName):
        """Returns the ID of the glyph with the given name."""
        try:
            return self.getReverseGlyphMap()[glyphName]
        except KeyError:
            if glyphName[:5] == "glyph":
                try:
                    return int(glyphName[5:])
                except (NameError, ValueError):
                    raise KeyError(glyphName)
            raise

    def getGlyphIDMany(self, lst):
        """Converts a list of glyph names into a list of glyph IDs."""
        d = self.getReverseGlyphMap()
        try:
            return [d[glyphName] for glyphName in lst]
        except KeyError:
            getGlyphID = self.getGlyphID
            return [getGlyphID(glyphName) for glyphName in lst]

    def getReverseGlyphMap(self, rebuild=False):
        """Returns a mapping of glyph names to glyph IDs."""
        if rebuild or not hasattr(self, "_reverseGlyphOrderDict"):
            self._buildReverseGlyphOrderDict()
        return self._reverseGlyphOrderDict

    def _buildReverseGlyphOrderDict(self):
        self._reverseGlyphOrderDict = d = {}
        for glyphID, glyphName in enumerate(self.getGlyphOrder()):
            d[glyphName] = glyphID
        return d

    def _writeTable(self, tag, writer, done, tableCache=None):
        """Internal helper function for self.save(). Keeps track of
        inter-table dependencies.
        """
        if tag in done:
            return
        tableClass = getTableClass(tag)
        for masterTable in tableClass.dependencies:
            if masterTable not in done:
                if masterTable in self:
                    self._writeTable(masterTable, writer, done, tableCache)
                else:
                    done.append(masterTable)
        done.append(tag)
        tabledata = self.getTableData(tag)
        if tableCache is not None:
            entry = tableCache.get((Tag(tag), tabledata))
            if entry is not None:
                log.debug("reusing '%s' table", tag)
                writer.setEntry(tag, entry)
                return
        log.debug("Writing '%s' table to disk", tag)
        writer[tag] = tabledata
        if tableCache is not None:
            tableCache[(Tag(tag), tabledata)] = writer[tag]

    def getTableData(self, tag):
        """Returns the binary representation of a table.

        If the table is currently loaded and in memory, the data is compiled to
        binary and returned; if it is not currently loaded, the binary data is
        read from the font file and returned.
        """
        tag = Tag(tag)
        if self.isLoaded(tag):
            log.debug("Compiling '%s' table", tag)
            return self.tables[tag].compile(self)
        elif self.reader and tag in self.reader:
            log.debug("Reading '%s' table from disk", tag)
            return self.reader[tag]
        else:
            raise KeyError(tag)

    def getGlyphSet(
        self, preferCFF=True, location=None, normalized=False, recalcBounds=True
    ):
        """Return a generic GlyphSet, which is a dict-like object
        mapping glyph names to glyph objects. The returned glyph objects
        have a ``.draw()`` method that supports the Pen protocol, and will
        have an attribute named 'width'.

        If the font is CFF-based, the outlines will be taken from the ``CFF ``
        or ``CFF2`` tables. Otherwise the outlines will be taken from the
        ``glyf`` table.

        If the font contains both a ``CFF ``/``CFF2`` and a ``glyf`` table, you
        can use the ``preferCFF`` argument to specify which one should be taken.
        If the font contains both a ``CFF `` and a ``CFF2`` table, the latter is
        taken.

        If the ``location`` parameter is set, it should be a dictionary mapping
        four-letter variation tags to their float values, and the returned
        glyph-set will represent an instance of a variable font at that
        location.

        If the ``normalized`` variable is set to True, that location is
        interpreted as in the normalized (-1..+1) space, otherwise it is in the
        font's defined axes space.
        """
        if location and "fvar" not in self:
            location = None
        if location and not normalized:
            location = self.normalizeLocation(location)
        glyphSet = None
        if ("CFF " in self or "CFF2" in self) and (preferCFF or "glyf" not in self):
            glyphSet = _TTGlyphSetCFF(self, location)
        elif "glyf" in self:
            glyphSet = _TTGlyphSetGlyf(self, location, recalcBounds=recalcBounds)
        else:
            raise TTLibError("Font contains no outlines")
        if "VARC" in self:
            glyphSet = _TTGlyphSetVARC(self, location, glyphSet)
        return glyphSet

    def normalizeLocation(self, location):
        """Normalize a ``location`` from the font's defined axes space (also
        known as user space) into the normalized (-1..+1) space. It applies
        ``avar`` mapping if the font contains an ``avar`` table.

        The ``location`` parameter should be a dictionary mapping four-letter
        variation tags to their float values.

        Raises ``TTLibError`` if the font is not a variable font.
        """
        from fontTools.varLib.models import normalizeLocation

        if "fvar" not in self:
            raise TTLibError("Not a variable font")

        axes = self["fvar"].getAxes()
        location = normalizeLocation(location, axes)
        if "avar" in self:
            location = self["avar"].renormalizeLocation(location, self)
        return location

    def getBestCmap(
        self,
        cmapPreferences=(
            (3, 10),
            (0, 6),
            (0, 4),
            (3, 1),
            (0, 3),
            (0, 2),
            (0, 1),
            (0, 0),
        ),
    ):
        """Returns the 'best' Unicode cmap dictionary available in the font
        or ``None``, if no Unicode cmap subtable is available.

        By default it will search for the following (platformID, platEncID)
        pairs in order::

                        (3, 10), # Windows Unicode full repertoire
                        (0, 6),  # Unicode full repertoire (format 13 subtable)
                        (0, 4),  # Unicode 2.0 full repertoire
                        (3, 1),  # Windows Unicode BMP
                        (0, 3),  # Unicode 2.0 BMP
                        (0, 2),  # Unicode ISO/IEC 10646
                        (0, 1),  # Unicode 1.1
                        (0, 0)   # Unicode 1.0

        This particular order matches what HarfBuzz uses to choose what
        subtable to use by default. This order prefers the largest-repertoire
        subtable, and among those, prefers the Windows-platform over the
        Unicode-platform as the former has wider support.

        This order can be customized via the ``cmapPreferences`` argument.
        """
        return self["cmap"].getBestCmap(cmapPreferences=cmapPreferences)

    def reorderGlyphs(self, new_glyph_order):
        from .reorderGlyphs import reorderGlyphs

        reorderGlyphs(self, new_glyph_order)


class GlyphOrder(object):
    """A pseudo table. The glyph order isn't in the font as a separate
    table, but it's nice to present it as such in the TTX format.
    """

    def __init__(self, tag=None):
        pass

    def toXML(self, writer, ttFont):
        glyphOrder = ttFont.getGlyphOrder()
        writer.comment(
            "The 'id' attribute is only for humans; " "it is ignored when parsed."
        )
        writer.newline()
        for i in range(len(glyphOrder)):
            glyphName = glyphOrder[i]
            writer.simpletag("GlyphID", id=i, name=glyphName)
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if not hasattr(self, "glyphOrder"):
            self.glyphOrder = []
        if name == "GlyphID":
            self.glyphOrder.append(attrs["name"])
        ttFont.setGlyphOrder(self.glyphOrder)


def getTableModule(tag):
    """Fetch the packer/unpacker module for a table.
    Return None when no module is found.
    """
    from . import tables

    pyTag = tagToIdentifier(tag)
    try:
        __import__("fontTools.ttLib.tables." + pyTag)
    except ImportError as err:
        # If pyTag is found in the ImportError message,
        # means table is not implemented.  If it's not
        # there, then some other module is missing, don't
        # suppress the error.
        if str(err).find(pyTag) >= 0:
            return None
        else:
            raise err
    else:
        return getattr(tables, pyTag)


# Registry for custom table packer/unpacker classes. Keys are table
# tags, values are (moduleName, className) tuples.
# See registerCustomTableClass() and getCustomTableClass()
_customTableRegistry = {}


def registerCustomTableClass(tag, moduleName, className=None):
    """Register a custom packer/unpacker class for a table.

    The 'moduleName' must be an importable module. If no 'className'
    is given, it is derived from the tag, for example it will be
    ``table_C_U_S_T_`` for a 'CUST' tag.

    The registered table class should be a subclass of
    :py:class:`fontTools.ttLib.tables.DefaultTable.DefaultTable`
    """
    if className is None:
        className = "table_" + tagToIdentifier(tag)
    _customTableRegistry[tag] = (moduleName, className)


def unregisterCustomTableClass(tag):
    """Unregister the custom packer/unpacker class for a table."""
    del _customTableRegistry[tag]


def getCustomTableClass(tag):
    """Return the custom table class for tag, if one has been registered
    with 'registerCustomTableClass()'. Else return None.
    """
    if tag not in _customTableRegistry:
        return None
    import importlib

    moduleName, className = _customTableRegistry[tag]
    module = importlib.import_module(moduleName)
    return getattr(module, className)


def getTableClass(tag):
    """Fetch the packer/unpacker class for a table."""
    tableClass = getCustomTableClass(tag)
    if tableClass is not None:
        return tableClass
    module = getTableModule(tag)
    if module is None:
        from .tables.DefaultTable import DefaultTable

        return DefaultTable
    pyTag = tagToIdentifier(tag)
    tableClass = getattr(module, "table_" + pyTag)
    return tableClass


def getClassTag(klass):
    """Fetch the table tag for a class object."""
    name = klass.__name__
    assert name[:6] == "table_"
    name = name[6:]  # Chop 'table_'
    return identifierToTag(name)


def newTable(tag):
    """Return a new instance of a table."""
    tableClass = getTableClass(tag)
    return tableClass(tag)


def _escapechar(c):
    """Helper function for tagToIdentifier()"""
    import re

    if re.match("[a-z0-9]", c):
        return "_" + c
    elif re.match("[A-Z]", c):
        return c + "_"
    else:
        return hex(byteord(c))[2:]


def tagToIdentifier(tag):
    """Convert a table tag to a valid (but UGLY) python identifier,
    as well as a filename that's guaranteed to be unique even on a
    caseless file system. Each character is mapped to two characters.
    Lowercase letters get an underscore before the letter, uppercase
    letters get an underscore after the letter. Trailing spaces are
    trimmed. Illegal characters are escaped as two hex bytes. If the
    result starts with a number (as the result of a hex escape), an
    extra underscore is prepended. Examples:
    .. code-block:: pycon

        >>>
        >> tagToIdentifier('glyf')
        '_g_l_y_f'
        >> tagToIdentifier('cvt ')
        '_c_v_t'
        >> tagToIdentifier('OS/2')
        'O_S_2f_2'
    """
    import re

    tag = Tag(tag)
    if tag == "GlyphOrder":
        return tag
    assert len(tag) == 4, "tag should be 4 characters long"
    while len(tag) > 1 and tag[-1] == " ":
        tag = tag[:-1]
    ident = ""
    for c in tag:
        ident = ident + _escapechar(c)
    if re.match("[0-9]", ident):
        ident = "_" + ident
    return ident


def identifierToTag(ident):
    """the opposite of tagToIdentifier()"""
    if ident == "GlyphOrder":
        return ident
    if len(ident) % 2 and ident[0] == "_":
        ident = ident[1:]
    assert not (len(ident) % 2)
    tag = ""
    for i in range(0, len(ident), 2):
        if ident[i] == "_":
            tag = tag + ident[i + 1]
        elif ident[i + 1] == "_":
            tag = tag + ident[i]
        else:
            # assume hex
            tag = tag + chr(int(ident[i : i + 2], 16))
    # append trailing spaces
    tag = tag + (4 - len(tag)) * " "
    return Tag(tag)


def tagToXML(tag):
    """Similarly to tagToIdentifier(), this converts a TT tag
    to a valid XML element name. Since XML element names are
    case sensitive, this is a fairly simple/readable translation.
    """
    import re

    tag = Tag(tag)
    if tag == "OS/2":
        return "OS_2"
    elif tag == "GlyphOrder":
        return tag
    if re.match("[A-Za-z_][A-Za-z_0-9]* *$", tag):
        return tag.strip()
    else:
        return tagToIdentifier(tag)


def xmlToTag(tag):
    """The opposite of tagToXML()"""
    if tag == "OS_2":
        return Tag("OS/2")
    if len(tag) == 8:
        return identifierToTag(tag)
    else:
        return Tag(tag + " " * (4 - len(tag)))


# Table order as recommended in the OpenType specification 1.4
TTFTableOrder = [
    "head",
    "hhea",
    "maxp",
    "OS/2",
    "hmtx",
    "LTSH",
    "VDMX",
    "hdmx",
    "cmap",
    "fpgm",
    "prep",
    "cvt ",
    "loca",
    "glyf",
    "kern",
    "name",
    "post",
    "gasp",
    "PCLT",
]

OTFTableOrder = ["head", "hhea", "maxp", "OS/2", "name", "cmap", "post", "CFF "]


def sortedTagList(tagList, tableOrder=None):
    """Return a sorted copy of tagList, sorted according to the OpenType
    specification, or according to a custom tableOrder. If given and not
    None, tableOrder needs to be a list of tag names.
    """
    tagList = sorted(tagList)
    if tableOrder is None:
        if "DSIG" in tagList:
            # DSIG should be last (XXX spec reference?)
            tagList.remove("DSIG")
            tagList.append("DSIG")
        if "CFF " in tagList:
            tableOrder = OTFTableOrder
        else:
            tableOrder = TTFTableOrder
    orderedTables = []
    for tag in tableOrder:
        if tag in tagList:
            orderedTables.append(tag)
            tagList.remove(tag)
    orderedTables.extend(tagList)
    return orderedTables


def reorderFontTables(inFile, outFile, tableOrder=None, checkChecksums=False):
    """Rewrite a font file, ordering the tables as recommended by the
    OpenType specification 1.4.
    """
    inFile.seek(0)
    outFile.seek(0)
    reader = SFNTReader(inFile, checkChecksums=checkChecksums)
    writer = SFNTWriter(
        outFile,
        len(reader.tables),
        reader.sfntVersion,
        reader.flavor,
        reader.flavorData,
    )
    tables = list(reader.keys())
    for tag in sortedTagList(tables, tableOrder):
        writer[tag] = reader[tag]
    writer.close()


def maxPowerOfTwo(x):
    """Return the highest exponent of two, so that
    (2 ** exponent) <= x.  Return 0 if x is 0.
    """
    exponent = 0
    while x:
        x = x >> 1
        exponent = exponent + 1
    return max(exponent - 1, 0)


def getSearchRange(n, itemSize=16):
    """Calculate searchRange, entrySelector, rangeShift."""
    # itemSize defaults to 16, for backward compatibility
    # with upstream fonttools.
    exponent = maxPowerOfTwo(n)
    searchRange = (2**exponent) * itemSize
    entrySelector = exponent
    rangeShift = max(0, n * itemSize - searchRange)
    return searchRange, entrySelector, rangeShift

# === NexusCore/openenv\Lib\site-packages\adodbapi\adodbapi.py ===
"""adodbapi - A python DB API 2.0 (PEP 249) interface to Microsoft ADO

Copyright (C) 2002 Henrik Ekelund, versions 2.1 and later by Vernon Cole
* https://sourceforge.net/projects/pywin32
* https://github.com/mhammond/pywin32
* https://sourceforge.net/projects/adodbapi

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

    django adaptations and refactoring by Adam Vandenberg

DB-API 2.0 specification: https://peps.python.org/pep-0249/

This module source should run correctly in CPython versions 2.7 and later,
or CPython 3.4 or later.
"""

__version__ = "2.6.2.0"
version = "adodbapi v" + __version__

import copy
import decimal
import os
import sys
import weakref

from . import ado_consts as adc, apibase as api, process_connect_string

try:
    verbose = int(os.environ["ADODBAPI_VERBOSE"])
except:
    verbose = False
if verbose:
    print(version)

try:
    import pythoncom
    import pywintypes
    from win32com.client import Dispatch
except ImportError:
    import warnings

    warnings.warn("pywin32 package required for adodbapi.", ImportWarning)


def getIndexedValue(obj, index):
    return obj(index)


from collections.abc import Mapping


# -----------------  The .connect method -----------------
def make_COM_connecter():
    try:
        pythoncom.CoInitialize()  # v2.1 Paj
        c = Dispatch("ADODB.Connection")  # connect _after_ CoInitialize v2.1.1 adamvan
    except:
        raise api.InterfaceError(
            "Windows COM Error: Dispatch('ADODB.Connection') failed."
        )
    return c


def connect(*args, **kwargs):  # --> a db-api connection object
    """Connect to a database.

    call using:
    :connection_string -- An ADODB formatted connection string, see:
         * https://www.connectionstrings.com
         * https://www.codeguru.com/dotnet/whats-in-an-ado-connection-string/
         * https://learn.microsoft.com/en-us/dotnet/framework/data/adonet/connection-strings
    :timeout -- A command timeout value, in seconds (default 30 seconds)
    """
    co = Connection()  # make an empty connection object

    kwargs = process_connect_string.process(args, kwargs, True)

    try:  # connect to the database, using the connection information in kwargs
        co.connect(kwargs)
        return co
    except Exception as e:
        message = 'Error opening connection to "%s"' % co.connection_string
        raise api.OperationalError(e, message)


# so you could use something like:
#   myConnection.paramstyle = 'named'
# The programmer may also change the default.
#   For example, if I were using django, I would say:
#     import adodbapi as Database
#     Database.adodbapi.paramstyle = 'format'

# ------- other module level defaults --------
defaultIsolationLevel = adc.adXactReadCommitted
#  Set defaultIsolationLevel on module level before creating the connection.
#   For example:
#   import adodbapi, ado_consts
#   adodbapi.adodbapi.defaultIsolationLevel=ado_consts.adXactBrowse"
#
#  Set defaultCursorLocation on module level before creating the connection.
# It may be one of the "adUse..." consts.
defaultCursorLocation = adc.adUseClient  # changed from adUseServer as of v 2.3.0

dateconverter = api.pythonDateTimeConverter()  # default


def format_parameters(ADOparameters, show_value=False):
    """Format a collection of ADO Command Parameters.

    Used by error reporting in _execute_command.
    """
    try:
        if show_value:
            desc = [
                'Name: %s, Dir.: %s, Type: %s, Size: %s, Value: "%s", Precision: %s, NumericScale: %s'
                % (
                    p.Name,
                    adc.directions[p.Direction],
                    adc.adTypeNames.get(p.Type, str(p.Type) + " (unknown type)"),
                    p.Size,
                    p.Value,
                    p.Precision,
                    p.NumericScale,
                )
                for p in ADOparameters
            ]
        else:
            desc = [
                "Name: %s, Dir.: %s, Type: %s, Size: %s, Precision: %s, NumericScale: %s"
                % (
                    p.Name,
                    adc.directions[p.Direction],
                    adc.adTypeNames.get(p.Type, str(p.Type) + " (unknown type)"),
                    p.Size,
                    p.Precision,
                    p.NumericScale,
                )
                for p in ADOparameters
            ]
        return "[" + "\n".join(desc) + "]"
    except:
        return "[]"


def _configure_parameter(p, value, adotype, settings_known):
    """Configure the given ADO Parameter 'p' with the Python 'value'."""

    if adotype in api.adoBinaryTypes:
        p.Size = len(value)
        p.AppendChunk(value)

    elif isinstance(value, str):  # v2.1 Jevon
        length = len(value)
        if adotype in api.adoStringTypes:  # v2.2.1 Cole
            if settings_known:
                length = min(length, p.Size)  # v2.1 Cole limit data to defined size
            p.Value = value[:length]  # v2.1 Jevon & v2.1 Cole
        else:
            p.Value = value  # don't limit if db column is numeric
        if length > 0:  # v2.1 Cole something does not like p.Size as Zero
            p.Size = length  # v2.1 Jevon

    elif isinstance(value, decimal.Decimal):
        p.Value = value
        exponent = value.as_tuple()[2]
        digit_count = len(value.as_tuple()[1])
        p.Precision = digit_count
        if exponent == 0:
            p.NumericScale = 0
        elif exponent < 0:
            p.NumericScale = -exponent
            if p.Precision < p.NumericScale:
                p.Precision = p.NumericScale
        else:  # exponent > 0:
            p.NumericScale = 0
            p.Precision = digit_count + exponent

    elif type(value) in dateconverter.types:
        if settings_known and adotype in api.adoDateTimeTypes:
            p.Value = dateconverter.COMDate(value)
        else:  # probably a string
            # provide the date as a string in the format 'YYYY-MM-dd'
            s = dateconverter.DateObjectToIsoFormatString(value)
            p.Value = s
            p.Size = len(s)

    elif adotype == adc.adEmpty:  # ADO will not let you specify a null column
        p.Type = (
            adc.adInteger
        )  # so we will fake it to be an integer (just to have something)
        p.Value = None  # and pass in a Null *value*

        # For any other type, set the value and let pythoncom do the right thing.
    else:
        p.Value = value


# # # # # ----- the Class that defines a connection ----- # # # # #
class Connection:
    # include connection attributes as class attributes required by api definition.
    Warning = api.Warning
    Error = api.Error
    InterfaceError = api.InterfaceError
    DataError = api.DataError
    DatabaseError = api.DatabaseError
    OperationalError = api.OperationalError
    IntegrityError = api.IntegrityError
    InternalError = api.InternalError
    NotSupportedError = api.NotSupportedError
    ProgrammingError = api.ProgrammingError
    FetchFailedError = api.FetchFailedError  # (special for django)
    # ...class attributes... (can be overridden by instance attributes)
    verbose = api.verbose

    @property
    def dbapi(self):  # a proposed db-api version 3 extension.
        "Return a reference to the DBAPI module for this Connection."
        return api

    def __init__(self):  # now define the instance attributes
        self.connector = None
        self.paramstyle = api.paramstyle
        self.supportsTransactions = False
        self.connection_string = ""
        self.cursors = weakref.WeakValueDictionary[int, Cursor]()
        self.dbms_name = ""
        self.dbms_version = ""
        self.errorhandler = None  # use the standard error handler for this instance
        self.transaction_level = 0  # 0 == Not in a transaction, at the top level
        self._autocommit = False

    def connect(self, kwargs, connection_maker=make_COM_connecter):
        if verbose > 9:
            print(f"kwargs={kwargs!r}")
        try:
            self.connection_string = (
                kwargs["connection_string"] % kwargs
            )  # insert keyword arguments
        except Exception as e:
            self._raiseConnectionError(
                KeyError, "Python string format error in connection string->"
            )
        self.timeout = kwargs.get("timeout", 30)
        self.mode = kwargs.get("mode", adc.adModeUnknown)
        self.kwargs = kwargs
        if verbose:
            print('%s attempting: "%s"' % (version, self.connection_string))
        self.connector = connection_maker()
        self.connector.ConnectionTimeout = self.timeout
        self.connector.ConnectionString = self.connection_string
        self.connector.Mode = self.mode

        try:
            self.connector.Open()  # Open the ADO connection
        except api.Error:
            self._raiseConnectionError(
                api.DatabaseError,
                "ADO error trying to Open=%s" % self.connection_string,
            )

        try:  # Stefan Fuchs; support WINCCOLEDBProvider
            if getIndexedValue(self.connector.Properties, "Transaction DDL").Value != 0:
                self.supportsTransactions = True
        except pywintypes.com_error:
            pass  # Stefan Fuchs
        self.dbms_name = getIndexedValue(self.connector.Properties, "DBMS Name").Value
        try:  # Stefan Fuchs
            self.dbms_version = getIndexedValue(
                self.connector.Properties, "DBMS Version"
            ).Value
        except pywintypes.com_error:
            pass  # Stefan Fuchs
        self.connector.CursorLocation = defaultCursorLocation  # v2.1 Rose
        if self.supportsTransactions:
            self.connector.IsolationLevel = defaultIsolationLevel
            self._autocommit = bool(kwargs.get("autocommit", False))
            if not self._autocommit:
                self.transaction_level = (
                    self.connector.BeginTrans()
                )  # Disables autocommit & inits transaction_level
        else:
            self._autocommit = True
        if "paramstyle" in kwargs:
            self.paramstyle = kwargs["paramstyle"]  # let setattr do the error checking
        self.messages = []
        if verbose:
            print("adodbapi New connection at %X" % id(self))

    def _raiseConnectionError(self, errorclass, errorvalue):
        eh = self.errorhandler
        if eh is None:
            eh = api.standardErrorHandler
        eh(self, None, errorclass, errorvalue)

    def _closeAdoConnection(self):  # all v2.1 Rose
        """close the underlying ADO Connection object,
        rolling it back first if it supports transactions."""
        if self.connector is None:
            return
        if not self._autocommit:
            if self.transaction_level:
                try:
                    self.connector.RollbackTrans()
                except:
                    pass
        self.connector.Close()
        if verbose:
            print("adodbapi Closed connection at %X" % id(self))

    def close(self):
        """Close the connection now (rather than whenever __del__ is called).

        The connection will be unusable from this point forward;
        an Error (or subclass) exception will be raised if any operation is attempted with the connection.
        The same applies to all cursor objects trying to use the connection.
        """
        for crsr in list(self.cursors.values())[
            :
        ]:  # copy the list, then close each one
            crsr.close(dont_tell_me=True)  # close without back-link clearing
        self.messages = []
        try:
            self._closeAdoConnection()  # v2.1 Rose
        except Exception as e:
            self._raiseConnectionError(sys.exc_info()[0], sys.exc_info()[1])

        self.connector = None  # v2.4.2.2 fix subtle timeout bug
        # per M.Hammond: "I expect the benefits of uninitializing are probably fairly small,
        #    so never uninitializing will probably not cause any problems."

    def commit(self):
        """Commit any pending transaction to the database.

        Note that if the database supports an auto-commit feature,
        this must be initially off. An interface method may be provided to turn it back on.
        Database modules that do not support transactions should implement this method with void functionality.
        """
        self.messages = []
        if not self.supportsTransactions:
            return

        try:
            self.transaction_level = self.connector.CommitTrans()
            if verbose > 1:
                print("commit done on connection at %X" % id(self))
            if not (
                self._autocommit
                or (self.connector.Attributes & adc.adXactAbortRetaining)
            ):
                # If attributes has adXactCommitRetaining it performs retaining commits that is,
                # calling CommitTrans automatically starts a new transaction. Not all providers support this.
                # If not, we will have to start a new transaction by this command:
                self.transaction_level = self.connector.BeginTrans()
        except Exception as e:
            self._raiseConnectionError(api.ProgrammingError, e)

    def _rollback(self):
        """In case a database does provide transactions this method causes the the database to roll back to
        the start of any pending transaction. Closing a connection without committing the changes first will
        cause an implicit rollback to be performed.

        If the database does not support the functionality required by the method, the interface should
        throw an exception in case the method is used.
        The preferred approach is to not implement the method and thus have Python generate
        an AttributeError in case the method is requested. This allows the programmer to check for database
        capabilities using the standard hasattr() function.

        For some dynamically configured interfaces it may not be appropriate to require dynamically making
        the method available. These interfaces should then raise a NotSupportedError to indicate the
        non-ability to perform the roll back when the method is invoked.
        """
        self.messages = []
        if (
            self.transaction_level
        ):  # trying to roll back with no open transaction causes an error
            try:
                self.transaction_level = self.connector.RollbackTrans()
                if verbose > 1:
                    print("rollback done on connection at %X" % id(self))
                if not self._autocommit and not (
                    self.connector.Attributes & adc.adXactAbortRetaining
                ):
                    # If attributes has adXactAbortRetaining it performs retaining aborts that is,
                    # calling RollbackTrans automatically starts a new transaction. Not all providers support this.
                    # If not, we will have to start a new transaction by this command:
                    if not self.transaction_level:
                        self.transaction_level = self.connector.BeginTrans()
            except Exception as e:
                self._raiseConnectionError(api.ProgrammingError, e)

    def __setattr__(self, name, value):
        if name == "autocommit":  # extension: allow user to turn autocommit on or off
            if self.supportsTransactions:
                object.__setattr__(self, "_autocommit", bool(value))
                try:
                    self._rollback()  # must clear any outstanding transactions
                except:
                    pass
            return
        elif name == "paramstyle":
            if value not in api.accepted_paramstyles:
                self._raiseConnectionError(
                    api.NotSupportedError,
                    f"paramstyle={value!r} not in:{api.accepted_paramstyles!r}",
                )
        elif name == "variantConversions":
            # make a new copy -- no changes in the default, please
            value = copy.copy(value)
        object.__setattr__(self, name, value)

    def __getattr__(self, item):
        if (
            item == "rollback"
        ):  # the rollback method only appears if the database supports transactions
            if self.supportsTransactions:
                return (
                    self._rollback
                )  # return the rollback method so the caller can execute it.
            else:
                raise AttributeError("this data provider does not support Rollback")
        elif item == "autocommit":
            return self._autocommit
        else:
            raise AttributeError(
                'no such attribute in ADO connection object as="%s"' % item
            )

    def cursor(self):
        "Return a new Cursor Object using the connection."
        self.messages = []
        c = Cursor(self)
        return c

    def _i_am_here(self, crsr):
        "message from a new cursor proclaiming its existence"
        oid = id(crsr)
        self.cursors[oid] = crsr

    def _i_am_closing(self, crsr):
        "message from a cursor giving connection a chance to clean up"
        try:
            del self.cursors[id(crsr)]
        except:
            pass

    def printADOerrors(self):
        j = self.connector.Errors.Count
        if j:
            print("ADO Errors:(%i)" % j)
        for e in self.connector.Errors:
            print("Description: %s" % e.Description)
            print("Error: %s %s " % (e.Number, adc.adoErrors.get(e.Number, "unknown")))
            if e.Number == adc.ado_error_TIMEOUT:
                print(
                    "Timeout Error: Try using adodbpi.connect(constr,timeout=Nseconds)"
                )
            print("Source: %s" % e.Source)
            print("NativeError: %s" % e.NativeError)
            print("SQL State: %s" % e.SQLState)

    def _suggest_error_class(self):
        """Introspect the current ADO Errors and determine an appropriate error class.

        Error.SQLState is a SQL-defined error condition, per the SQL specification:
        https://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt

        The 23000 class of errors are integrity errors.
        Error 40002 is a transactional integrity error.
        """
        if self.connector is not None:
            for e in self.connector.Errors:
                state = str(e.SQLState)
                if state.startswith("23") or state == "40002":
                    return api.IntegrityError
        return api.DatabaseError

    def __del__(self):
        try:
            self._closeAdoConnection()  # v2.1 Rose
        except:
            pass
        self.connector = None

    def __enter__(self):  # Connections are context managers
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._rollback()  # automatic rollback on errors
        else:
            self.commit()

    def get_table_names(self):
        schema = self.connector.OpenSchema(20)  # constant = adSchemaTables

        tables = []
        while not schema.EOF:
            name = getIndexedValue(schema.Fields, "TABLE_NAME").Value
            tables.append(name)
            schema.MoveNext()
        del schema
        return tables


# # # # # ----- the Class that defines a cursor ----- # # # # #
class Cursor:
    ## ** api required attributes:
    ## description...
    ##    This read-only attribute is a sequence of 7-item sequences.
    ##    Each of these sequences contains information describing one result column:
    ##        (name, type_code, display_size, internal_size, precision, scale, null_ok).
    ##    This attribute will be None for operations that do not return rows or if the
    ##    cursor has not had an operation invoked via the executeXXX() method yet.
    ##    The type_code can be interpreted by comparing it to the Type Objects specified in the section below.
    ## rowcount...
    ##    This read-only attribute specifies the number of rows that the last executeXXX() produced
    ##    (for DQL statements like select) or affected (for DML statements like update or insert).
    ##    The attribute is -1 in case no executeXXX() has been performed on the cursor or
    ##    the rowcount of the last operation is not determinable by the interface.[7]
    ## arraysize...
    ##    This read/write attribute specifies the number of rows to fetch at a time with fetchmany().
    ##    It defaults to 1 meaning to fetch a single row at a time.
    ##    Implementations must observe this value with respect to the fetchmany() method,
    ##    but are free to interact with the database a single row at a time.
    ##    It may also be used in the implementation of executemany().
    ## ** extension attributes:
    ## paramstyle...
    ##   allows the programmer to override the connection's default paramstyle
    ## errorhandler...
    ##   allows the programmer to override the connection's default error handler

    def __init__(self, connection):
        self.command = None
        self._ado_prepared = False
        self.messages = []
        self.connection = connection
        self.paramstyle = connection.paramstyle  # used for overriding the paramstyle
        self._parameter_names = []
        self.recordset_is_remote = False
        self.rs = None  # the ADO recordset for this cursor
        self.converters = []  # conversion function for each column
        self.columnNames = {}  # names of columns {lowercase name : number,...}
        self.numberOfColumns = 0
        self._description = None
        self.rowcount = -1
        self.errorhandler = connection.errorhandler
        self.arraysize = 1
        connection._i_am_here(self)
        if verbose:
            print(
                "%s New cursor at %X on conn %X"
                % (version, id(self), id(self.connection))
            )

    def __iter__(self):  # [2.1 Zamarev]
        return iter(self.fetchone, None)  # [2.1 Zamarev]

    def prepare(self, operation):
        self.command = operation
        self._description = None
        self._ado_prepared = "setup"

    def __next__(self):
        r = self.fetchone()
        if r:
            return r
        raise StopIteration

    def __enter__(self):
        "Allow database cursors to be used with context managers."
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        "Allow database cursors to be used with context managers."
        self.close()

    def _raiseCursorError(self, errorclass, errorvalue):
        eh = self.errorhandler
        if eh is None:
            eh = api.standardErrorHandler
        eh(self.connection, self, errorclass, errorvalue)

    def build_column_info(self, recordset):
        self.converters = []  # conversion function for each column
        self.columnNames = {}  # names of columns {lowercase name : number,...}
        self._description = None

        # if EOF and BOF are true at the same time, there are no records in the recordset
        if (recordset is None) or (recordset.State == adc.adStateClosed):
            self.rs = None
            self.numberOfColumns = 0
            return
        self.rs = recordset  # v2.1.1 bkline
        self.recordset_format = api.RS_WIN_32
        self.numberOfColumns = recordset.Fields.Count
        try:
            varCon = self.connection.variantConversions
        except AttributeError:
            varCon = api.variantConversions
        for i in range(self.numberOfColumns):
            f = getIndexedValue(self.rs.Fields, i)
            try:
                self.converters.append(
                    varCon[f.Type]
                )  # conversion function for this column
            except KeyError:
                self._raiseCursorError(
                    api.InternalError, "Data column of Unknown ADO type=%s" % f.Type
                )
            self.columnNames[f.Name.lower()] = i  # columnNames lookup

    def _makeDescriptionFromRS(self):
        # Abort if closed or no recordset.
        if self.rs is None:
            self._description = None
            return
        desc = []
        for i in range(self.numberOfColumns):
            f = getIndexedValue(self.rs.Fields, i)
            if self.rs.EOF or self.rs.BOF:
                display_size = None
            else:
                # TODO: Is this the correct defintion according to the DB API 2 Spec ?
                display_size = f.ActualSize
            null_ok = bool(f.Attributes & adc.adFldMayBeNull)  # v2.1 Cole
            desc.append(
                (
                    f.Name,
                    f.Type,
                    display_size,
                    f.DefinedSize,
                    f.Precision,
                    f.NumericScale,
                    null_ok,
                )
            )
        self._description = desc

    def get_description(self):
        if not self._description:
            self._makeDescriptionFromRS()
        return self._description

    def __getattr__(self, item):
        if item == "description":
            return self.get_description()
        object.__getattribute__(
            self, item
        )  # may get here on Remote attribute calls for existing attributes

    def format_description(self, d):
        """Format db_api description tuple for printing."""
        if self.description is None:
            self._makeDescriptionFromRS()
        if isinstance(d, int):
            d = self.description[d]
        desc = (
            "Name= %s, Type= %s, DispSize= %s, IntSize= %s, Precision= %s, Scale= %s NullOK=%s"
            % (
                d[0],
                adc.adTypeNames.get(d[1], str(d[1]) + " (unknown type)"),
                d[2],
                d[3],
                d[4],
                d[5],
                d[6],
            )
        )
        return desc

    def close(self, dont_tell_me=False):
        """Close the cursor now (rather than whenever __del__ is called).
        The cursor will be unusable from this point forward; an Error (or subclass)
        exception will be raised if any operation is attempted with the cursor.
        """
        if self.connection is None:
            return
        self.messages = []
        if (
            self.rs and self.rs.State != adc.adStateClosed
        ):  # rs exists and is open      #v2.1 Rose
            self.rs.Close()  # v2.1 Rose
            self.rs = None  # let go of the recordset so ADO will let it be disposed #v2.1 Rose
        if not dont_tell_me:
            self.connection._i_am_closing(
                self
            )  # take me off the connection's cursors list
        self.connection = (
            None  # this will make all future method calls on me throw an exception
        )
        if verbose:
            print("adodbapi Closed cursor at %X" % id(self))

    def __del__(self):
        try:
            self.close()
        except:
            pass

    def _new_command(self, command_type=adc.adCmdText):
        self.cmd = None
        self.messages = []

        if self.connection is None:
            self._raiseCursorError(api.InterfaceError, None)
            return
        try:
            self.cmd = Dispatch("ADODB.Command")
            self.cmd.ActiveConnection = self.connection.connector
            self.cmd.CommandTimeout = self.connection.timeout
            self.cmd.CommandType = command_type
            self.cmd.CommandText = self.commandText
            self.cmd.Prepared = bool(self._ado_prepared)
        except:
            self._raiseCursorError(
                api.DatabaseError,
                f"Error creating new ADODB.Command object for {self.commandText!r}",
            )

    def _execute_command(self):
        # Stored procedures may have an integer return value
        self.return_value = None
        recordset = None
        count = -1  # default value
        if verbose:
            print('Executing command="%s"' % self.commandText)
        try:
            # ----- the actual SQL is executed here ---
            recordset, count = self.cmd.Execute()
            # ----- ------------------------------- ---
        except Exception as e:
            _message = ""
            if hasattr(e, "args"):
                _message += str(e.args) + "\n"
            _message += "Command:\n%s\nParameters:\n%s" % (
                self.commandText,
                format_parameters(self.cmd.Parameters, True),
            )
            klass = self.connection._suggest_error_class()
            self._raiseCursorError(klass, _message)
        try:
            self.rowcount = recordset.RecordCount
        except:
            self.rowcount = count
        self.build_column_info(recordset)

        # The ADO documentation hints that obtaining the recordcount may be timeconsuming
        #   "If the Recordset object does not support approximate positioning, this property
        #    may be a significant drain on resources # [ekelund]
        # Therefore, COM will not return rowcount for server-side cursors. [Cole]
        # Client-side cursors (the default since v2.8) will force a static
        # cursor, and rowcount will then be set accurately [Cole]

    def get_rowcount(self):
        return self.rowcount

    def get_returned_parameters(self):
        """with some providers, returned parameters and the .return_value are not available until
        after the last recordset has been read.  In that case, you must coll nextset() until it
        returns None, then call this method to get your returned information."""

        # store procedures may return altered parameters, including an added "return value" item
        retLst = []
        for p in tuple(self.cmd.Parameters):
            if verbose > 2:
                print(
                    'Returned=Name: %s, Dir.: %s, Type: %s, Size: %s, Value: "%s",'
                    " Precision: %s, NumericScale: %s"
                    % (
                        p.Name,
                        adc.directions[p.Direction],
                        adc.adTypeNames.get(p.Type, str(p.Type) + " (unknown type)"),
                        p.Size,
                        p.Value,
                        p.Precision,
                        p.NumericScale,
                    )
                )
            pyObject = api.convert_to_python(p.Value, api.variantConversions[p.Type])
            if p.Direction == adc.adParamReturnValue:
                self.returnValue = (
                    pyObject  # also load the undocumented attribute (Vernon's Error!)
                )
                self.return_value = pyObject
            else:
                retLst.append(pyObject)
        return retLst  # return the parameter list to the caller

    def callproc(self, procname, parameters=None):
        """Call a stored database procedure with the given name.
        The sequence of parameters must contain one entry for each
        argument that the sproc expects. The result of the
        call is returned as modified copy of the input
        sequence.  Input parameters are left untouched, output and
        input/output parameters replaced with possibly new values.

        The sproc may also provide a result set as output,
        which is available through the standard .fetch*() methods.
        Extension: A "return_value" property may be set on the
        cursor if the sproc defines an integer return value.
        """
        self._parameter_names = []
        self.commandText = procname
        self._new_command(command_type=adc.adCmdStoredProc)
        self._buildADOparameterList(parameters, sproc=True)
        if verbose > 2:
            print(
                "Calling Stored Proc with Params=",
                format_parameters(self.cmd.Parameters, True),
            )
        self._execute_command()
        return self.get_returned_parameters()

    def _reformat_operation(self, operation, parameters):
        if self.paramstyle in ("format", "pyformat"):  # convert %s to ?
            operation, self._parameter_names = api.changeFormatToQmark(operation)
        elif self.paramstyle == "named" or (
            self.paramstyle == "dynamic" and isinstance(parameters, Mapping)
        ):
            operation, self._parameter_names = api.changeNamedToQmark(
                operation
            )  # convert :name to ?
        return operation

    def _buildADOparameterList(self, parameters, sproc=False):
        self.parameters = parameters
        if parameters is None:
            parameters = []

        # Note: ADO does not preserve the parameter list, even if "Prepared" is True, so we must build every time.
        parameters_known = False
        if sproc:  # needed only if we are calling a stored procedure
            try:  # attempt to use ADO's parameter list
                self.cmd.Parameters.Refresh()
                if verbose > 2:
                    print(
                        "ADO detected Params=",
                        format_parameters(self.cmd.Parameters, True),
                    )
                    print(f"Program Parameters={parameters!r}")
                parameters_known = True
            except api.Error:
                if verbose:
                    print("ADO Parameter Refresh failed")
                pass
            else:
                if len(parameters) != self.cmd.Parameters.Count - 1:
                    raise api.ProgrammingError(
                        "You must supply %d parameters for this stored procedure"
                        % (self.cmd.Parameters.Count - 1)
                    )
        if sproc or parameters != []:
            i = 0
            if parameters_known:  # use ado parameter list
                if self._parameter_names:  # named parameters
                    for i, pm_name in enumerate(self._parameter_names):
                        p = getIndexedValue(self.cmd.Parameters, i)
                        try:
                            _configure_parameter(
                                p, parameters[pm_name], p.Type, parameters_known
                            )
                        except Exception as e:
                            _message = "Error Converting Parameter {}: {}, {} <- {!r}\n".format(
                                p.Name,
                                adc.ado_type_name(p.Type),
                                p.Value,
                                parameters[pm_name],
                            )
                            self._raiseCursorError(
                                api.DataError, f"{_message}->{e.args!r}"
                            )
                else:  # regular sequence of parameters
                    for value in parameters:
                        p = getIndexedValue(self.cmd.Parameters, i)
                        if (
                            p.Direction == adc.adParamReturnValue
                        ):  # this is an extra parameter added by ADO
                            i += 1  # skip the extra
                            p = getIndexedValue(self.cmd.Parameters, i)
                        try:
                            _configure_parameter(p, value, p.Type, parameters_known)
                        except Exception as e:
                            _message = "Error Converting Parameter {}: {}, {} <- {!r}\n".format(
                                p.Name,
                                adc.ado_type_name(p.Type),
                                p.Value,
                                value,
                            )
                            self._raiseCursorError(
                                api.DataError, f"{_message}->{e.args!r}"
                            )
                        i += 1
            else:  # -- build own parameter list
                # we expect a dictionary of parameters, this is the list of expected names
                if self._parameter_names:
                    for parm_name in self._parameter_names:
                        elem = parameters[parm_name]
                        adotype = api.pyTypeToADOType(elem)
                        p = self.cmd.CreateParameter(
                            parm_name, adotype, adc.adParamInput
                        )
                        _configure_parameter(p, elem, adotype, parameters_known)
                        try:
                            self.cmd.Parameters.Append(p)
                        except Exception as e:
                            _message = (
                                "Error Building Parameter {}: {}, {} <- {!r}\n".format(
                                    p.Name,
                                    adc.ado_type_name(p.Type),
                                    p.Value,
                                    elem,
                                )
                            )
                            self._raiseCursorError(
                                api.DataError, f"{_message}->{e.args!r}"
                            )
                else:  # expecting the usual sequence of parameters
                    if sproc:
                        p = self.cmd.CreateParameter(
                            "@RETURN_VALUE", adc.adInteger, adc.adParamReturnValue
                        )
                        self.cmd.Parameters.Append(p)

                    for elem in parameters:
                        name = "p%i" % i
                        adotype = api.pyTypeToADOType(elem)
                        p = self.cmd.CreateParameter(
                            name, adotype, adc.adParamInput
                        )  # Name, Type, Direction, Size, Value
                        _configure_parameter(p, elem, adotype, parameters_known)
                        try:
                            self.cmd.Parameters.Append(p)
                        except Exception as e:
                            _message = (
                                "Error Building Parameter {}: {}, {} <- {!r}\n".format(
                                    p.Name,
                                    adc.ado_type_name(p.Type),
                                    p.Value,
                                    elem,
                                )
                            )
                            self._raiseCursorError(
                                api.DataError, f"{_message}->{e.args!r}"
                            )
                        i += 1
                if self._ado_prepared == "setup":
                    self._ado_prepared = (
                        True  # parameters will be "known" by ADO next loop
                    )

    def execute(self, operation, parameters=None):
        """Prepare and execute a database operation (query or command).

        Parameters may be provided as sequence or mapping and will be bound to variables in the operation.
        Variables are specified in a database-specific notation
        (see the module's paramstyle attribute for details). [5]
        A reference to the operation will be retained by the cursor.
        If the same operation object is passed in again, then the cursor
        can optimize its behavior. This is most effective for algorithms
        where the same operation is used, but different parameters are bound to it (many times).

        For maximum efficiency when reusing an operation, it is best to use
        the setinputsizes() method to specify the parameter types and sizes ahead of time.
        It is legal for a parameter to not match the predefined information;
        the implementation should compensate, possibly with a loss of efficiency.

        The parameters may also be specified as list of tuples to e.g. insert multiple rows in
        a single operation, but this kind of usage is depreciated: executemany() should be used instead.

        Return value is not defined.

        [5] The module will use the __getitem__ method of the parameters object to map either positions
        (integers) or names (strings) to parameter values. This allows for both sequences and mappings
        to be used as input.
        The term "bound" refers to the process of binding an input value to a database execution buffer.
        In practical terms, this means that the input value is directly used as a value in the operation.
        The client should not be required to "escape" the value so that it can be used -- the value
        should be equal to the actual database value."""
        if (
            self.command is not operation
            or self._ado_prepared == "setup"
            or not hasattr(self, "commandText")
        ):
            if self.command is not operation:
                self._ado_prepared = False
                self.command = operation
            self._parameter_names = []
            self.commandText = (
                operation
                if (self.paramstyle == "qmark" or not parameters)
                else self._reformat_operation(operation, parameters)
            )
        self._new_command()
        self._buildADOparameterList(parameters)
        if verbose > 3:
            print("Params=", format_parameters(self.cmd.Parameters, True))
        self._execute_command()

    def executemany(self, operation, seq_of_parameters):
        """Prepare a database operation (query or command)
        and then execute it against all parameter sequences or mappings found in the sequence seq_of_parameters.

            Return values are not defined.
        """
        self.messages = list()
        total_recordcount = 0

        self.prepare(operation)
        for params in seq_of_parameters:
            self.execute(self.command, params)
            if self.rowcount == -1:
                total_recordcount = -1
            if total_recordcount != -1:
                total_recordcount += self.rowcount
        self.rowcount = total_recordcount

    def _fetch(self, limit=None):
        """Fetch rows from the current recordset.

        limit -- Number of rows to fetch, or None (default) to fetch all rows.
        """
        if self.connection is None or self.rs is None:
            self._raiseCursorError(
                api.FetchFailedError, "fetch() on closed connection or empty query set"
            )
            return

        if self.rs.State == adc.adStateClosed or self.rs.BOF or self.rs.EOF:
            return list()
        if limit:  # limit number of rows retrieved
            ado_results = self.rs.GetRows(limit)
        else:  # get all rows
            ado_results = self.rs.GetRows()
        if (
            self.recordset_format == api.RS_ARRAY
        ):  # result of GetRows is a two-dimension array
            length = (
                len(ado_results) // self.numberOfColumns
            )  # length of first dimension
        else:  # pywin32
            length = len(ado_results[0])  # result of GetRows is tuples in a tuple
        fetchObject = api.SQLrows(
            ado_results, length, self
        )  # new object to hold the results of the fetch
        return fetchObject

    def fetchone(self):
        """Fetch the next row of a query result set, returning a single sequence,
        or None when no more data is available.

        An Error (or subclass) exception is raised if the previous call to executeXXX()
        did not produce any result set or no call was issued yet.
        """
        self.messages = []
        result = self._fetch(1)
        if result:  # return record (not list of records)
            return result[0]
        return None

    def fetchmany(self, size=None):
        """Fetch the next set of rows of a query result, returning a list of tuples. An empty sequence is returned when no more rows are available.

        The number of rows to fetch per call is specified by the parameter.
        If it is not given, the cursor's arraysize determines the number of rows to be fetched.
        The method should try to fetch as many rows as indicated by the size parameter.
        If this is not possible due to the specified number of rows not being available,
        fewer rows may be returned.

        An Error (or subclass) exception is raised if the previous call to executeXXX()
        did not produce any result set or no call was issued yet.

        Note there are performance considerations involved with the size parameter.
        For optimal performance, it is usually best to use the arraysize attribute.
        If the size parameter is used, then it is best for it to retain the same value from
        one fetchmany() call to the next.
        """
        self.messages = []
        if size is None:
            size = self.arraysize
        return self._fetch(size)

    def fetchall(self):
        """Fetch all (remaining) rows of a query result, returning them as a sequence of sequences (e.g. a list of tuples).

        Note that the cursor's arraysize attribute
        can affect the performance of this operation.
        An Error (or subclass) exception is raised if the previous call to executeXXX()
        did not produce any result set or no call was issued yet.
        """
        self.messages = []
        return self._fetch()

    def nextset(self):
        """Skip to the next available recordset, discarding any remaining rows from the current recordset.

        If there are no more sets, the method returns None. Otherwise, it returns a true
        value and subsequent calls to the fetch methods will return rows from the next result set.

        An Error (or subclass) exception is raised if the previous call to executeXXX()
        did not produce any result set or no call was issued yet.
        """
        self.messages = []
        if self.connection is None or self.rs is None:
            self._raiseCursorError(
                api.OperationalError,
                ("nextset() on closed connection or empty query set"),
            )
            return None

        try:  # [begin 2.1 ekelund]
            rsTuple = self.rs.NextRecordset()  #
        except pywintypes.com_error as exc:  # return appropriate error
            self._raiseCursorError(api.NotSupportedError, exc.args)  # [end 2.1 ekelund]
        recordset = rsTuple[0]
        if recordset is None:
            return None
        self.build_column_info(recordset)
        return True

    def setinputsizes(self, sizes):
        pass

    def setoutputsize(self, size, column=None):
        pass

    def _last_query(self):  # let the programmer see what query we actually used
        try:
            if self.parameters is None:
                ret = self.commandText
            else:
                ret = f"{self.commandText},parameters={self.parameters!r}"
        except:
            ret = None
        return ret

    query = property(_last_query, None, None, "returns the last query executed")


if __name__ == "__main__":
    raise api.ProgrammingError(version + " cannot be run as a main program.")

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_sourcemod_builtins.py ===
"""
    pygments.lexers._sourcemod_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This file contains the names of SourceMod functions.

    Do not edit the FUNCTIONS list by hand.

    Run with `python -I` to regenerate.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

FUNCTIONS = (
    'OnEntityCreated',
    'OnEntityDestroyed',
    'OnGetGameDescription',
    'OnLevelInit',
    'SDKHook',
    'SDKHookEx',
    'SDKUnhook',
    'SDKHooks_TakeDamage',
    'SDKHooks_DropWeapon',
    'TopMenuHandler',
    'CreateTopMenu',
    'LoadTopMenuConfig',
    'AddToTopMenu',
    'GetTopMenuInfoString',
    'GetTopMenuObjName',
    'RemoveFromTopMenu',
    'DisplayTopMenu',
    'DisplayTopMenuCategory',
    'FindTopMenuCategory',
    'SetTopMenuTitleCaching',
    'OnAdminMenuCreated',
    'OnAdminMenuReady',
    'GetAdminTopMenu',
    'AddTargetsToMenu',
    'AddTargetsToMenu2',
    'RedisplayAdminMenu',
    'TEHook',
    'AddTempEntHook',
    'RemoveTempEntHook',
    'TE_Start',
    'TE_IsValidProp',
    'TE_WriteNum',
    'TE_ReadNum',
    'TE_WriteFloat',
    'TE_ReadFloat',
    'TE_WriteVector',
    'TE_ReadVector',
    'TE_WriteAngles',
    'TE_WriteFloatArray',
    'TE_Send',
    'TE_WriteEncodedEnt',
    'TE_SendToAll',
    'TE_SendToClient',
    'CreateKeyValues',
    'KvSetString',
    'KvSetNum',
    'KvSetUInt64',
    'KvSetFloat',
    'KvSetColor',
    'KvSetVector',
    'KvGetString',
    'KvGetNum',
    'KvGetFloat',
    'KvGetColor',
    'KvGetUInt64',
    'KvGetVector',
    'KvJumpToKey',
    'KvJumpToKeySymbol',
    'KvGotoFirstSubKey',
    'KvGotoNextKey',
    'KvSavePosition',
    'KvDeleteKey',
    'KvDeleteThis',
    'KvGoBack',
    'KvRewind',
    'KvGetSectionName',
    'KvSetSectionName',
    'KvGetDataType',
    'KeyValuesToFile',
    'FileToKeyValues',
    'StringToKeyValues',
    'KvSetEscapeSequences',
    'KvNodesInStack',
    'KvCopySubkeys',
    'KvFindKeyById',
    'KvGetNameSymbol',
    'KvGetSectionSymbol',
    'TE_SetupSparks',
    'TE_SetupSmoke',
    'TE_SetupDust',
    'TE_SetupMuzzleFlash',
    'TE_SetupMetalSparks',
    'TE_SetupEnergySplash',
    'TE_SetupArmorRicochet',
    'TE_SetupGlowSprite',
    'TE_SetupExplosion',
    'TE_SetupBloodSprite',
    'TE_SetupBeamRingPoint',
    'TE_SetupBeamPoints',
    'TE_SetupBeamLaser',
    'TE_SetupBeamRing',
    'TE_SetupBeamFollow',
    'HookEvent',
    'HookEventEx',
    'UnhookEvent',
    'CreateEvent',
    'FireEvent',
    'CancelCreatedEvent',
    'GetEventBool',
    'SetEventBool',
    'GetEventInt',
    'SetEventInt',
    'GetEventFloat',
    'SetEventFloat',
    'GetEventString',
    'SetEventString',
    'GetEventName',
    'SetEventBroadcast',
    'GetUserMessageType',
    'GetUserMessageId',
    'GetUserMessageName',
    'StartMessage',
    'StartMessageEx',
    'EndMessage',
    'MsgHook',
    'MsgPostHook',
    'HookUserMessage',
    'UnhookUserMessage',
    'StartMessageAll',
    'StartMessageOne',
    'InactivateClient',
    'ReconnectClient',
    'GetMaxEntities',
    'GetEntityCount',
    'IsValidEntity',
    'IsValidEdict',
    'IsEntNetworkable',
    'CreateEdict',
    'RemoveEdict',
    'GetEdictFlags',
    'SetEdictFlags',
    'GetEdictClassname',
    'GetEntityNetClass',
    'ChangeEdictState',
    'GetEntData',
    'SetEntData',
    'GetEntDataFloat',
    'SetEntDataFloat',
    'GetEntDataEnt2',
    'SetEntDataEnt2',
    'GetEntDataVector',
    'SetEntDataVector',
    'GetEntDataString',
    'SetEntDataString',
    'FindSendPropOffs',
    'FindSendPropInfo',
    'FindDataMapOffs',
    'FindDataMapInfo',
    'GetEntSendPropOffs',
    'GetEntProp',
    'SetEntProp',
    'GetEntPropFloat',
    'SetEntPropFloat',
    'GetEntPropEnt',
    'SetEntPropEnt',
    'GetEntPropVector',
    'SetEntPropVector',
    'GetEntPropString',
    'SetEntPropString',
    'GetEntPropArraySize',
    'GetEntDataArray',
    'SetEntDataArray',
    'GetEntityAddress',
    'GetEntityClassname',
    'float',
    'FloatMul',
    'FloatDiv',
    'FloatAdd',
    'FloatSub',
    'FloatFraction',
    'RoundToZero',
    'RoundToCeil',
    'RoundToFloor',
    'RoundToNearest',
    'FloatCompare',
    'SquareRoot',
    'Pow',
    'Exponential',
    'Logarithm',
    'Sine',
    'Cosine',
    'Tangent',
    'FloatAbs',
    'ArcTangent',
    'ArcCosine',
    'ArcSine',
    'ArcTangent2',
    'RoundFloat',
    'operator%',
    'DegToRad',
    'RadToDeg',
    'GetURandomInt',
    'GetURandomFloat',
    'SetURandomSeed',
    'SetURandomSeedSimple',
    'RemovePlayerItem',
    'GivePlayerItem',
    'GetPlayerWeaponSlot',
    'IgniteEntity',
    'ExtinguishEntity',
    'TeleportEntity',
    'ForcePlayerSuicide',
    'SlapPlayer',
    'FindEntityByClassname',
    'GetClientEyeAngles',
    'CreateEntityByName',
    'DispatchSpawn',
    'DispatchKeyValue',
    'DispatchKeyValueFloat',
    'DispatchKeyValueVector',
    'GetClientAimTarget',
    'GetTeamCount',
    'GetTeamName',
    'GetTeamScore',
    'SetTeamScore',
    'GetTeamClientCount',
    'SetEntityModel',
    'GetPlayerDecalFile',
    'GetPlayerJingleFile',
    'GetServerNetStats',
    'EquipPlayerWeapon',
    'ActivateEntity',
    'SetClientInfo',
    'GivePlayerAmmo',
    'SetClientListeningFlags',
    'GetClientListeningFlags',
    'SetListenOverride',
    'GetListenOverride',
    'IsClientMuted',
    'TR_GetPointContents',
    'TR_GetPointContentsEnt',
    'TR_TraceRay',
    'TR_TraceHull',
    'TR_TraceRayFilter',
    'TR_TraceHullFilter',
    'TR_TraceRayEx',
    'TR_TraceHullEx',
    'TR_TraceRayFilterEx',
    'TR_TraceHullFilterEx',
    'TR_GetFraction',
    'TR_GetEndPosition',
    'TR_GetEntityIndex',
    'TR_DidHit',
    'TR_GetHitGroup',
    'TR_GetPlaneNormal',
    'TR_PointOutsideWorld',
    'SortIntegers',
    'SortFloats',
    'SortStrings',
    'SortFunc1D',
    'SortCustom1D',
    'SortCustom2D',
    'SortADTArray',
    'SortFuncADTArray',
    'SortADTArrayCustom',
    'CompileRegex',
    'MatchRegex',
    'GetRegexSubString',
    'SimpleRegexMatch',
    'TF2_GetPlayerClass',
    'TF2_SetPlayerClass',
    'TF2_RemoveWeaponSlot',
    'TF2_RemoveAllWeapons',
    'TF2_IsPlayerInCondition',
    'TF2_GetObjectType',
    'TF2_GetObjectMode',
    'NominateMap',
    'RemoveNominationByMap',
    'RemoveNominationByOwner',
    'GetExcludeMapList',
    'GetNominatedMapList',
    'CanMapChooserStartVote',
    'InitiateMapChooserVote',
    'HasEndOfMapVoteFinished',
    'EndOfMapVoteEnabled',
    'OnNominationRemoved',
    'OnMapVoteStarted',
    'CreateTimer',
    'KillTimer',
    'TriggerTimer',
    'GetTickedTime',
    'GetMapTimeLeft',
    'GetMapTimeLimit',
    'ExtendMapTimeLimit',
    'GetTickInterval',
    'OnMapTimeLeftChanged',
    'IsServerProcessing',
    'CreateDataTimer',
    'ByteCountToCells',
    'CreateArray',
    'ClearArray',
    'CloneArray',
    'ResizeArray',
    'GetArraySize',
    'PushArrayCell',
    'PushArrayString',
    'PushArrayArray',
    'GetArrayCell',
    'GetArrayString',
    'GetArrayArray',
    'SetArrayCell',
    'SetArrayString',
    'SetArrayArray',
    'ShiftArrayUp',
    'RemoveFromArray',
    'SwapArrayItems',
    'FindStringInArray',
    'FindValueInArray',
    'ProcessTargetString',
    'ReplyToTargetError',
    'MultiTargetFilter',
    'AddMultiTargetFilter',
    'RemoveMultiTargetFilter',
    'OnBanClient',
    'OnBanIdentity',
    'OnRemoveBan',
    'BanClient',
    'BanIdentity',
    'RemoveBan',
    'CreateTrie',
    'SetTrieValue',
    'SetTrieArray',
    'SetTrieString',
    'GetTrieValue',
    'GetTrieArray',
    'GetTrieString',
    'RemoveFromTrie',
    'ClearTrie',
    'GetTrieSize',
    'GetFunctionByName',
    'CreateGlobalForward',
    'CreateForward',
    'GetForwardFunctionCount',
    'AddToForward',
    'RemoveFromForward',
    'RemoveAllFromForward',
    'Call_StartForward',
    'Call_StartFunction',
    'Call_PushCell',
    'Call_PushCellRef',
    'Call_PushFloat',
    'Call_PushFloatRef',
    'Call_PushArray',
    'Call_PushArrayEx',
    'Call_PushString',
    'Call_PushStringEx',
    'Call_Finish',
    'Call_Cancel',
    'NativeCall',
    'CreateNative',
    'ThrowNativeError',
    'GetNativeStringLength',
    'GetNativeString',
    'SetNativeString',
    'GetNativeCell',
    'GetNativeCellRef',
    'SetNativeCellRef',
    'GetNativeArray',
    'SetNativeArray',
    'FormatNativeString',
    'RequestFrameCallback',
    'RequestFrame',
    'OnRebuildAdminCache',
    'DumpAdminCache',
    'AddCommandOverride',
    'GetCommandOverride',
    'UnsetCommandOverride',
    'CreateAdmGroup',
    'FindAdmGroup',
    'SetAdmGroupAddFlag',
    'GetAdmGroupAddFlag',
    'GetAdmGroupAddFlags',
    'SetAdmGroupImmuneFrom',
    'GetAdmGroupImmuneCount',
    'GetAdmGroupImmuneFrom',
    'AddAdmGroupCmdOverride',
    'GetAdmGroupCmdOverride',
    'RegisterAuthIdentType',
    'CreateAdmin',
    'GetAdminUsername',
    'BindAdminIdentity',
    'SetAdminFlag',
    'GetAdminFlag',
    'GetAdminFlags',
    'AdminInheritGroup',
    'GetAdminGroupCount',
    'GetAdminGroup',
    'SetAdminPassword',
    'GetAdminPassword',
    'FindAdminByIdentity',
    'RemoveAdmin',
    'FlagBitsToBitArray',
    'FlagBitArrayToBits',
    'FlagArrayToBits',
    'FlagBitsToArray',
    'FindFlagByName',
    'FindFlagByChar',
    'FindFlagChar',
    'ReadFlagString',
    'CanAdminTarget',
    'CreateAuthMethod',
    'SetAdmGroupImmunityLevel',
    'GetAdmGroupImmunityLevel',
    'SetAdminImmunityLevel',
    'GetAdminImmunityLevel',
    'FlagToBit',
    'BitToFlag',
    'ServerCommand',
    'ServerCommandEx',
    'InsertServerCommand',
    'ServerExecute',
    'ClientCommand',
    'FakeClientCommand',
    'FakeClientCommandEx',
    'PrintToServer',
    'PrintToConsole',
    'ReplyToCommand',
    'GetCmdReplySource',
    'SetCmdReplySource',
    'IsChatTrigger',
    'ShowActivity2',
    'ShowActivity',
    'ShowActivityEx',
    'FormatActivitySource',
    'SrvCmd',
    'RegServerCmd',
    'ConCmd',
    'RegConsoleCmd',
    'RegAdminCmd',
    'GetCmdArgs',
    'GetCmdArg',
    'GetCmdArgString',
    'CreateConVar',
    'FindConVar',
    'ConVarChanged',
    'HookConVarChange',
    'UnhookConVarChange',
    'GetConVarBool',
    'SetConVarBool',
    'GetConVarInt',
    'SetConVarInt',
    'GetConVarFloat',
    'SetConVarFloat',
    'GetConVarString',
    'SetConVarString',
    'ResetConVar',
    'GetConVarDefault',
    'GetConVarFlags',
    'SetConVarFlags',
    'GetConVarBounds',
    'SetConVarBounds',
    'GetConVarName',
    'QueryClientConVar',
    'GetCommandIterator',
    'ReadCommandIterator',
    'CheckCommandAccess',
    'CheckAccess',
    'IsValidConVarChar',
    'GetCommandFlags',
    'SetCommandFlags',
    'FindFirstConCommand',
    'FindNextConCommand',
    'SendConVarValue',
    'AddServerTag',
    'RemoveServerTag',
    'CommandListener',
    'AddCommandListener',
    'RemoveCommandListener',
    'CommandExists',
    'OnClientSayCommand',
    'OnClientSayCommand_Post',
    'TF2_IgnitePlayer',
    'TF2_RespawnPlayer',
    'TF2_RegeneratePlayer',
    'TF2_AddCondition',
    'TF2_RemoveCondition',
    'TF2_SetPlayerPowerPlay',
    'TF2_DisguisePlayer',
    'TF2_RemovePlayerDisguise',
    'TF2_StunPlayer',
    'TF2_MakeBleed',
    'TF2_GetClass',
    'TF2_CalcIsAttackCritical',
    'TF2_OnIsHolidayActive',
    'TF2_IsHolidayActive',
    'TF2_IsPlayerInDuel',
    'TF2_RemoveWearable',
    'TF2_OnConditionAdded',
    'TF2_OnConditionRemoved',
    'TF2_OnWaitingForPlayersStart',
    'TF2_OnWaitingForPlayersEnd',
    'TF2_OnPlayerTeleport',
    'SQL_Connect',
    'SQL_DefConnect',
    'SQL_ConnectCustom',
    'SQLite_UseDatabase',
    'SQL_CheckConfig',
    'SQL_GetDriver',
    'SQL_ReadDriver',
    'SQL_GetDriverIdent',
    'SQL_GetDriverProduct',
    'SQL_SetCharset',
    'SQL_GetAffectedRows',
    'SQL_GetInsertId',
    'SQL_GetError',
    'SQL_EscapeString',
    'SQL_QuoteString',
    'SQL_FastQuery',
    'SQL_Query',
    'SQL_PrepareQuery',
    'SQL_FetchMoreResults',
    'SQL_HasResultSet',
    'SQL_GetRowCount',
    'SQL_GetFieldCount',
    'SQL_FieldNumToName',
    'SQL_FieldNameToNum',
    'SQL_FetchRow',
    'SQL_MoreRows',
    'SQL_Rewind',
    'SQL_FetchString',
    'SQL_FetchFloat',
    'SQL_FetchInt',
    'SQL_IsFieldNull',
    'SQL_FetchSize',
    'SQL_BindParamInt',
    'SQL_BindParamFloat',
    'SQL_BindParamString',
    'SQL_Execute',
    'SQL_LockDatabase',
    'SQL_UnlockDatabase',
    'SQLTCallback',
    'SQL_IsSameConnection',
    'SQL_TConnect',
    'SQL_TQuery',
    'SQL_CreateTransaction',
    'SQL_AddQuery',
    'SQLTxnSuccess',
    'SQLTxnFailure',
    'SQL_ExecuteTransaction',
    'CloseHandle',
    'CloneHandle',
    'MenuHandler',
    'CreateMenu',
    'DisplayMenu',
    'DisplayMenuAtItem',
    'AddMenuItem',
    'InsertMenuItem',
    'RemoveMenuItem',
    'RemoveAllMenuItems',
    'GetMenuItem',
    'GetMenuSelectionPosition',
    'GetMenuItemCount',
    'SetMenuPagination',
    'GetMenuPagination',
    'GetMenuStyle',
    'SetMenuTitle',
    'GetMenuTitle',
    'CreatePanelFromMenu',
    'GetMenuExitButton',
    'SetMenuExitButton',
    'GetMenuExitBackButton',
    'SetMenuExitBackButton',
    'SetMenuNoVoteButton',
    'CancelMenu',
    'GetMenuOptionFlags',
    'SetMenuOptionFlags',
    'IsVoteInProgress',
    'CancelVote',
    'VoteMenu',
    'VoteMenuToAll',
    'VoteHandler',
    'SetVoteResultCallback',
    'CheckVoteDelay',
    'IsClientInVotePool',
    'RedrawClientVoteMenu',
    'GetMenuStyleHandle',
    'CreatePanel',
    'CreateMenuEx',
    'GetClientMenu',
    'CancelClientMenu',
    'GetMaxPageItems',
    'GetPanelStyle',
    'SetPanelTitle',
    'DrawPanelItem',
    'DrawPanelText',
    'CanPanelDrawFlags',
    'SetPanelKeys',
    'SendPanelToClient',
    'GetPanelTextRemaining',
    'GetPanelCurrentKey',
    'SetPanelCurrentKey',
    'RedrawMenuItem',
    'InternalShowMenu',
    'GetMenuVoteInfo',
    'IsNewVoteAllowed',
    'PrefetchSound',
    'EmitAmbientSound',
    'FadeClientVolume',
    'StopSound',
    'EmitSound',
    'EmitSentence',
    'GetDistGainFromSoundLevel',
    'AmbientSHook',
    'NormalSHook',
    'AddAmbientSoundHook',
    'AddNormalSoundHook',
    'RemoveAmbientSoundHook',
    'RemoveNormalSoundHook',
    'EmitSoundToClient',
    'EmitSoundToAll',
    'ATTN_TO_SNDLEVEL',
    'GetGameSoundParams',
    'EmitGameSound',
    'EmitAmbientGameSound',
    'EmitGameSoundToClient',
    'EmitGameSoundToAll',
    'PrecacheScriptSound',
    'strlen',
    'StrContains',
    'strcmp',
    'strncmp',
    'StrEqual',
    'strcopy',
    'Format',
    'FormatEx',
    'VFormat',
    'StringToInt',
    'StringToIntEx',
    'IntToString',
    'StringToFloat',
    'StringToFloatEx',
    'FloatToString',
    'BreakString',
    'TrimString',
    'SplitString',
    'ReplaceString',
    'ReplaceStringEx',
    'GetCharBytes',
    'IsCharAlpha',
    'IsCharNumeric',
    'IsCharSpace',
    'IsCharMB',
    'IsCharUpper',
    'IsCharLower',
    'StripQuotes',
    'CharToUpper',
    'CharToLower',
    'FindCharInString',
    'StrCat',
    'ExplodeString',
    'ImplodeStrings',
    'GetVectorLength',
    'GetVectorDistance',
    'GetVectorDotProduct',
    'GetVectorCrossProduct',
    'NormalizeVector',
    'GetAngleVectors',
    'GetVectorAngles',
    'GetVectorVectors',
    'AddVectors',
    'SubtractVectors',
    'ScaleVector',
    'NegateVector',
    'MakeVectorFromPoints',
    'BaseComm_IsClientGagged',
    'BaseComm_IsClientMuted',
    'BaseComm_SetClientGag',
    'BaseComm_SetClientMute',
    'FormatUserLogText',
    'FindPluginByFile',
    'FindTarget',
    'AcceptEntityInput',
    'SetVariantBool',
    'SetVariantString',
    'SetVariantInt',
    'SetVariantFloat',
    'SetVariantVector3D',
    'SetVariantPosVector3D',
    'SetVariantColor',
    'SetVariantEntity',
    'GameRules_GetProp',
    'GameRules_SetProp',
    'GameRules_GetPropFloat',
    'GameRules_SetPropFloat',
    'GameRules_GetPropEnt',
    'GameRules_SetPropEnt',
    'GameRules_GetPropVector',
    'GameRules_SetPropVector',
    'GameRules_GetPropString',
    'GameRules_SetPropString',
    'GameRules_GetRoundState',
    'OnClientConnect',
    'OnClientConnected',
    'OnClientPutInServer',
    'OnClientDisconnect',
    'OnClientDisconnect_Post',
    'OnClientCommand',
    'OnClientSettingsChanged',
    'OnClientAuthorized',
    'OnClientPreAdminCheck',
    'OnClientPostAdminFilter',
    'OnClientPostAdminCheck',
    'GetMaxClients',
    'GetMaxHumanPlayers',
    'GetClientCount',
    'GetClientName',
    'GetClientIP',
    'GetClientAuthString',
    'GetClientAuthId',
    'GetSteamAccountID',
    'GetClientUserId',
    'IsClientConnected',
    'IsClientInGame',
    'IsClientInKickQueue',
    'IsClientAuthorized',
    'IsFakeClient',
    'IsClientSourceTV',
    'IsClientReplay',
    'IsClientObserver',
    'IsPlayerAlive',
    'GetClientInfo',
    'GetClientTeam',
    'SetUserAdmin',
    'GetUserAdmin',
    'AddUserFlags',
    'RemoveUserFlags',
    'SetUserFlagBits',
    'GetUserFlagBits',
    'CanUserTarget',
    'RunAdminCacheChecks',
    'NotifyPostAdminCheck',
    'CreateFakeClient',
    'SetFakeClientConVar',
    'GetClientHealth',
    'GetClientModel',
    'GetClientWeapon',
    'GetClientMaxs',
    'GetClientMins',
    'GetClientAbsAngles',
    'GetClientAbsOrigin',
    'GetClientArmor',
    'GetClientDeaths',
    'GetClientFrags',
    'GetClientDataRate',
    'IsClientTimingOut',
    'GetClientTime',
    'GetClientLatency',
    'GetClientAvgLatency',
    'GetClientAvgLoss',
    'GetClientAvgChoke',
    'GetClientAvgData',
    'GetClientAvgPackets',
    'GetClientOfUserId',
    'KickClient',
    'KickClientEx',
    'ChangeClientTeam',
    'GetClientSerial',
    'GetClientFromSerial',
    'FindStringTable',
    'GetNumStringTables',
    'GetStringTableNumStrings',
    'GetStringTableMaxStrings',
    'GetStringTableName',
    'FindStringIndex',
    'ReadStringTable',
    'GetStringTableDataLength',
    'GetStringTableData',
    'SetStringTableData',
    'AddToStringTable',
    'LockStringTables',
    'AddFileToDownloadsTable',
    'GetEntityFlags',
    'SetEntityFlags',
    'GetEntityMoveType',
    'SetEntityMoveType',
    'GetEntityRenderMode',
    'SetEntityRenderMode',
    'GetEntityRenderFx',
    'SetEntityRenderFx',
    'SetEntityRenderColor',
    'GetEntityGravity',
    'SetEntityGravity',
    'SetEntityHealth',
    'GetClientButtons',
    'EntityOutput',
    'HookEntityOutput',
    'UnhookEntityOutput',
    'HookSingleEntityOutput',
    'UnhookSingleEntityOutput',
    'SMC_CreateParser',
    'SMC_ParseFile',
    'SMC_GetErrorString',
    'SMC_ParseStart',
    'SMC_SetParseStart',
    'SMC_ParseEnd',
    'SMC_SetParseEnd',
    'SMC_NewSection',
    'SMC_KeyValue',
    'SMC_EndSection',
    'SMC_SetReaders',
    'SMC_RawLine',
    'SMC_SetRawLine',
    'BfWriteBool',
    'BfWriteByte',
    'BfWriteChar',
    'BfWriteShort',
    'BfWriteWord',
    'BfWriteNum',
    'BfWriteFloat',
    'BfWriteString',
    'BfWriteEntity',
    'BfWriteAngle',
    'BfWriteCoord',
    'BfWriteVecCoord',
    'BfWriteVecNormal',
    'BfWriteAngles',
    'BfReadBool',
    'BfReadByte',
    'BfReadChar',
    'BfReadShort',
    'BfReadWord',
    'BfReadNum',
    'BfReadFloat',
    'BfReadString',
    'BfReadEntity',
    'BfReadAngle',
    'BfReadCoord',
    'BfReadVecCoord',
    'BfReadVecNormal',
    'BfReadAngles',
    'BfGetNumBytesLeft',
    'CreateProfiler',
    'StartProfiling',
    'StopProfiling',
    'GetProfilerTime',
    'OnPluginStart',
    'AskPluginLoad2',
    'OnPluginEnd',
    'OnPluginPauseChange',
    'OnGameFrame',
    'OnMapStart',
    'OnMapEnd',
    'OnConfigsExecuted',
    'OnAutoConfigsBuffered',
    'OnAllPluginsLoaded',
    'GetMyHandle',
    'GetPluginIterator',
    'MorePlugins',
    'ReadPlugin',
    'GetPluginStatus',
    'GetPluginFilename',
    'IsPluginDebugging',
    'GetPluginInfo',
    'FindPluginByNumber',
    'SetFailState',
    'ThrowError',
    'GetTime',
    'FormatTime',
    'LoadGameConfigFile',
    'GameConfGetOffset',
    'GameConfGetKeyValue',
    'GameConfGetAddress',
    'GetSysTickCount',
    'AutoExecConfig',
    'RegPluginLibrary',
    'LibraryExists',
    'GetExtensionFileStatus',
    'OnLibraryAdded',
    'OnLibraryRemoved',
    'ReadMapList',
    'SetMapListCompatBind',
    'OnClientFloodCheck',
    'OnClientFloodResult',
    'CanTestFeatures',
    'GetFeatureStatus',
    'RequireFeature',
    'LoadFromAddress',
    'StoreToAddress',
    'CreateStack',
    'PushStackCell',
    'PushStackString',
    'PushStackArray',
    'PopStackCell',
    'PopStackString',
    'PopStackArray',
    'IsStackEmpty',
    'PopStack',
    'OnPlayerRunCmd',
    'BuildPath',
    'OpenDirectory',
    'ReadDirEntry',
    'OpenFile',
    'DeleteFile',
    'ReadFileLine',
    'ReadFile',
    'ReadFileString',
    'WriteFile',
    'WriteFileString',
    'WriteFileLine',
    'ReadFileCell',
    'WriteFileCell',
    'IsEndOfFile',
    'FileSeek',
    'FilePosition',
    'FileExists',
    'RenameFile',
    'DirExists',
    'FileSize',
    'FlushFile',
    'RemoveDir',
    'CreateDirectory',
    'GetFileTime',
    'LogToOpenFile',
    'LogToOpenFileEx',
    'PbReadInt',
    'PbReadFloat',
    'PbReadBool',
    'PbReadString',
    'PbReadColor',
    'PbReadAngle',
    'PbReadVector',
    'PbReadVector2D',
    'PbGetRepeatedFieldCount',
    'PbSetInt',
    'PbSetFloat',
    'PbSetBool',
    'PbSetString',
    'PbSetColor',
    'PbSetAngle',
    'PbSetVector',
    'PbSetVector2D',
    'PbAddInt',
    'PbAddFloat',
    'PbAddBool',
    'PbAddString',
    'PbAddColor',
    'PbAddAngle',
    'PbAddVector',
    'PbAddVector2D',
    'PbRemoveRepeatedFieldValue',
    'PbReadMessage',
    'PbReadRepeatedMessage',
    'PbAddMessage',
    'SetNextMap',
    'GetNextMap',
    'ForceChangeLevel',
    'GetMapHistorySize',
    'GetMapHistory',
    'GeoipCode2',
    'GeoipCode3',
    'GeoipCountry',
    'MarkNativeAsOptional',
    'RegClientCookie',
    'FindClientCookie',
    'SetClientCookie',
    'GetClientCookie',
    'SetAuthIdCookie',
    'AreClientCookiesCached',
    'OnClientCookiesCached',
    'CookieMenuHandler',
    'SetCookiePrefabMenu',
    'SetCookieMenuItem',
    'ShowCookieMenu',
    'GetCookieIterator',
    'ReadCookieIterator',
    'GetCookieAccess',
    'GetClientCookieTime',
    'LoadTranslations',
    'SetGlobalTransTarget',
    'GetClientLanguage',
    'GetServerLanguage',
    'GetLanguageCount',
    'GetLanguageInfo',
    'SetClientLanguage',
    'GetLanguageByCode',
    'GetLanguageByName',
    'CS_OnBuyCommand',
    'CS_OnCSWeaponDrop',
    'CS_OnGetWeaponPrice',
    'CS_OnTerminateRound',
    'CS_RespawnPlayer',
    'CS_SwitchTeam',
    'CS_DropWeapon',
    'CS_TerminateRound',
    'CS_GetTranslatedWeaponAlias',
    'CS_GetWeaponPrice',
    'CS_GetClientClanTag',
    'CS_SetClientClanTag',
    'CS_GetTeamScore',
    'CS_SetTeamScore',
    'CS_GetMVPCount',
    'CS_SetMVPCount',
    'CS_GetClientContributionScore',
    'CS_SetClientContributionScore',
    'CS_GetClientAssists',
    'CS_SetClientAssists',
    'CS_AliasToWeaponID',
    'CS_WeaponIDToAlias',
    'CS_IsValidWeaponID',
    'CS_UpdateClientModel',
    'LogToGame',
    'SetRandomSeed',
    'GetRandomFloat',
    'GetRandomInt',
    'IsMapValid',
    'IsDedicatedServer',
    'GetEngineTime',
    'GetGameTime',
    'GetGameTickCount',
    'GetGameDescription',
    'GetGameFolderName',
    'GetCurrentMap',
    'PrecacheModel',
    'PrecacheSentenceFile',
    'PrecacheDecal',
    'PrecacheGeneric',
    'IsModelPrecached',
    'IsDecalPrecached',
    'IsGenericPrecached',
    'PrecacheSound',
    'IsSoundPrecached',
    'CreateDialog',
    'GetEngineVersion',
    'PrintToChat',
    'PrintToChatAll',
    'PrintCenterText',
    'PrintCenterTextAll',
    'PrintHintText',
    'PrintHintTextToAll',
    'ShowVGUIPanel',
    'CreateHudSynchronizer',
    'SetHudTextParams',
    'SetHudTextParamsEx',
    'ShowSyncHudText',
    'ClearSyncHud',
    'ShowHudText',
    'ShowMOTDPanel',
    'DisplayAskConnectBox',
    'EntIndexToEntRef',
    'EntRefToEntIndex',
    'MakeCompatEntRef',
    'SetClientViewEntity',
    'SetLightStyle',
    'GetClientEyePosition',
    'CreateDataPack',
    'WritePackCell',
    'WritePackFloat',
    'WritePackString',
    'ReadPackCell',
    'ReadPackFloat',
    'ReadPackString',
    'ResetPack',
    'GetPackPosition',
    'SetPackPosition',
    'IsPackReadable',
    'LogMessage',
    'LogToFile',
    'LogToFileEx',
    'LogAction',
    'LogError',
    'OnLogAction',
    'GameLogHook',
    'AddGameLogHook',
    'RemoveGameLogHook',
    'FindTeamByName',
    'StartPrepSDKCall',
    'PrepSDKCall_SetVirtual',
    'PrepSDKCall_SetSignature',
    'PrepSDKCall_SetAddress',
    'PrepSDKCall_SetFromConf',
    'PrepSDKCall_SetReturnInfo',
    'PrepSDKCall_AddParameter',
    'EndPrepSDKCall',
    'SDKCall',
    'GetPlayerResourceEntity',
)


if __name__ == '__main__':  # pragma: no cover
    import re
    from urllib.request import FancyURLopener

    from pygments.util import format_lines

    class Opener(FancyURLopener):
        version = 'Mozilla/5.0 (Pygments Sourcemod Builtins Update)'

    opener = Opener()

    def get_version():
        f = opener.open('http://docs.sourcemod.net/api/index.php')
        r = re.compile(r'SourceMod v\.<b>([\d\.]+(?:-\w+)?)</td>')
        for line in f:
            m = r.search(line.decode())
            if m is not None:
                return m.groups()[0]
        raise ValueError('No version in api docs')

    def get_sm_functions():
        f = opener.open('http://docs.sourcemod.net/api/SMfuncs.js')
        r = re.compile(r'SMfunctions\[\d+\] = Array \("(?:public )?([^,]+)",".+"\);')
        functions = []
        for line in f:
            m = r.match(line.decode())
            if m is not None:
                functions.append(m.groups()[0])
        return functions

    def regenerate(filename, natives):
        with open(filename, encoding='utf-8') as fp:
            content = fp.read()

        header = content[:content.find('FUNCTIONS = (')]
        footer = content[content.find("if __name__ == '__main__':")-1:]


        with open(filename, 'w', encoding='utf-8') as fp:
            fp.write(header)
            fp.write(format_lines('FUNCTIONS', natives))
            fp.write('\n\n' + footer)

    def run():
        version = get_version()
        print(f'> Downloading function index for SourceMod {version}')
        functions = get_sm_functions()
        print('> %d functions found:' % len(functions))

        functionlist = []
        for full_function_name in functions:
            print(f'>> {full_function_name}')
            functionlist.append(full_function_name)

        regenerate(__file__, functionlist)


    run()

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_threads.py ===
from __future__ import annotations

import contextvars
import queue as stdlib_queue
import re
import sys
import threading
import time
import weakref
from functools import partial
from typing import (
    TYPE_CHECKING,
    NoReturn,
    TypeVar,
    Union,
)

import pytest
import sniffio

from .. import (
    CancelScope,
    CapacityLimiter,
    Event,
    _core,
    fail_after,
    move_on_after,
    sleep,
    sleep_forever,
)
from .._core._tests.test_ki import ki_self
from .._core._tests.tutil import slow
from .._threads import (
    active_thread_count,
    current_default_thread_limiter,
    from_thread_check_cancelled,
    from_thread_run,
    from_thread_run_sync,
    to_thread_run_sync,
    wait_all_threads_completed,
)
from ..testing import wait_all_tasks_blocked

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable

    from outcome import Outcome

    from ..lowlevel import Task

RecordType = list[tuple[str, Union[threading.Thread, type[BaseException]]]]
T = TypeVar("T")


async def test_do_in_trio_thread() -> None:
    trio_thread = threading.current_thread()

    async def check_case(  # type: ignore[explicit-any]
        do_in_trio_thread: Callable[..., threading.Thread],
        fn: Callable[..., T | Awaitable[T]],
        expected: tuple[str, T],
        trio_token: _core.TrioToken | None = None,
    ) -> None:
        record: RecordType = []

        def threadfn() -> None:
            try:
                record.append(("start", threading.current_thread()))
                x = do_in_trio_thread(fn, record, trio_token=trio_token)
                record.append(("got", x))
            except BaseException as exc:
                print(exc)
                record.append(("error", type(exc)))

        child_thread = threading.Thread(target=threadfn, daemon=True)
        child_thread.start()
        while child_thread.is_alive():
            print("yawn")
            await sleep(0.01)
        assert record == [("start", child_thread), ("f", trio_thread), expected]

    token = _core.current_trio_token()

    def f1(record: RecordType) -> int:
        assert not _core.currently_ki_protected()
        record.append(("f", threading.current_thread()))
        return 2

    await check_case(from_thread_run_sync, f1, ("got", 2), trio_token=token)

    def f2(record: RecordType) -> NoReturn:
        assert not _core.currently_ki_protected()
        record.append(("f", threading.current_thread()))
        raise ValueError

    await check_case(from_thread_run_sync, f2, ("error", ValueError), trio_token=token)

    async def f3(record: RecordType) -> int:
        assert not _core.currently_ki_protected()
        await _core.checkpoint()
        record.append(("f", threading.current_thread()))
        return 3

    await check_case(from_thread_run, f3, ("got", 3), trio_token=token)

    async def f4(record: RecordType) -> NoReturn:
        assert not _core.currently_ki_protected()
        await _core.checkpoint()
        record.append(("f", threading.current_thread()))
        raise KeyError

    await check_case(from_thread_run, f4, ("error", KeyError), trio_token=token)


async def test_do_in_trio_thread_from_trio_thread() -> None:
    with pytest.raises(RuntimeError):
        from_thread_run_sync(lambda: None)  # pragma: no branch

    async def foo() -> None:  # pragma: no cover
        pass

    with pytest.raises(RuntimeError):
        from_thread_run(foo)


def test_run_in_trio_thread_ki() -> None:
    # if we get a control-C during a run_in_trio_thread, then it propagates
    # back to the caller (slick!)
    record = set()

    async def check_run_in_trio_thread() -> None:
        token = _core.current_trio_token()

        def trio_thread_fn() -> None:
            print("in Trio thread")
            assert not _core.currently_ki_protected()
            print("ki_self")
            try:
                ki_self()
            finally:
                import sys

                print("finally", sys.exc_info())

        async def trio_thread_afn() -> None:
            trio_thread_fn()

        def external_thread_fn() -> None:
            try:
                print("running")
                from_thread_run_sync(trio_thread_fn, trio_token=token)
            except KeyboardInterrupt:
                print("ok1")
                record.add("ok1")
            try:
                from_thread_run(trio_thread_afn, trio_token=token)
            except KeyboardInterrupt:
                print("ok2")
                record.add("ok2")

        thread = threading.Thread(target=external_thread_fn)
        thread.start()
        print("waiting")
        while thread.is_alive():  # noqa: ASYNC110
            await sleep(0.01)  # Fine to poll in tests.
        print("waited, joining")
        thread.join()
        print("done")

    _core.run(check_run_in_trio_thread)
    assert record == {"ok1", "ok2"}


def test_await_in_trio_thread_while_main_exits() -> None:
    record = []
    ev = Event()

    async def trio_fn() -> None:
        record.append("sleeping")
        ev.set()
        await _core.wait_task_rescheduled(lambda _: _core.Abort.SUCCEEDED)

    def thread_fn(token: _core.TrioToken) -> None:
        try:
            from_thread_run(trio_fn, trio_token=token)
        except _core.Cancelled:
            record.append("cancelled")

    async def main() -> threading.Thread:
        token = _core.current_trio_token()
        thread = threading.Thread(target=thread_fn, args=(token,))
        thread.start()
        await ev.wait()
        assert record == ["sleeping"]
        return thread

    thread = _core.run(main)
    thread.join()
    assert record == ["sleeping", "cancelled"]


async def test_named_thread() -> None:
    ending = " from trio._tests.test_threads.test_named_thread"

    def inner(name: str = "inner" + ending) -> threading.Thread:
        assert threading.current_thread().name == name
        return threading.current_thread()

    def f(name: str) -> Callable[[], threading.Thread]:
        return partial(inner, name)

    # test defaults
    await to_thread_run_sync(inner)
    await to_thread_run_sync(inner, thread_name=None)

    # functools.partial doesn't have __name__, so defaults to None
    await to_thread_run_sync(f("None" + ending))

    # test that you can set a custom name, and that it's reset afterwards
    async def test_thread_name(name: str) -> None:
        thread = await to_thread_run_sync(f(name), thread_name=name)
        assert re.match(r"Trio thread [0-9]*", thread.name)

    await test_thread_name("")
    await test_thread_name("fobiedoo")
    await test_thread_name("name_longer_than_15_characters")

    await test_thread_name("💙")


def _get_thread_name(ident: int | None = None) -> str | None:
    import ctypes
    import ctypes.util

    libpthread_path = ctypes.util.find_library("pthread")
    if not libpthread_path:
        # musl includes pthread functions directly in libc.so
        # (but note that find_library("c") does not work on musl,
        #  see: https://github.com/python/cpython/issues/65821)
        # so try that library instead
        # if it doesn't exist, CDLL() will fail below
        libpthread_path = "libc.so"
    try:
        libpthread = ctypes.CDLL(libpthread_path)
    except Exception:
        print(f"no pthread on {sys.platform}")
        return None

    pthread_getname_np = getattr(libpthread, "pthread_getname_np", None)

    # this should never fail on any platforms afaik
    assert pthread_getname_np

    # thankfully getname signature doesn't differ between platforms
    pthread_getname_np.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_size_t,
    ]
    pthread_getname_np.restype = ctypes.c_int

    name_buffer = ctypes.create_string_buffer(b"", size=16)
    if ident is None:
        ident = threading.get_ident()
    assert pthread_getname_np(ident, name_buffer, 16) == 0
    try:
        return name_buffer.value.decode()
    except UnicodeDecodeError as e:  # pragma: no cover
        # used for debugging when testing via CI
        pytest.fail(f"value: {name_buffer.value!r}, exception: {e}")


# test os thread naming
# this depends on pthread being available, which is the case on 99.9% of linux machines
# and most mac machines. So unless the platform is linux it will just skip
# in case it fails to fetch the os thread name.
async def test_named_thread_os() -> None:
    def inner(name: str) -> threading.Thread:
        os_thread_name = _get_thread_name()
        if os_thread_name is None and sys.platform != "linux":
            pytest.skip(f"no pthread OS support on {sys.platform}")
        else:
            assert os_thread_name == name[:15]

        return threading.current_thread()

    def f(name: str) -> Callable[[], threading.Thread]:
        return partial(inner, name)

    # test defaults
    default = "None from trio._tests.test_threads.test_named_thread"
    await to_thread_run_sync(f(default))
    await to_thread_run_sync(f(default), thread_name=None)

    # test that you can set a custom name, and that it's reset afterwards
    async def test_thread_name(name: str, expected: str | None = None) -> None:
        if expected is None:
            expected = name
        thread = await to_thread_run_sync(f(expected), thread_name=name)

        os_thread_name = _get_thread_name(thread.ident)
        assert os_thread_name is not None, "should skip earlier if this is the case"
        assert re.match(r"Trio thread [0-9]*", os_thread_name)

    await test_thread_name("")
    await test_thread_name("fobiedoo")
    await test_thread_name("name_longer_than_15_characters")

    await test_thread_name("💙", expected="?")


def test_has_pthread_setname_np() -> None:
    from trio._core._thread_cache import get_os_thread_name_func

    k = get_os_thread_name_func()
    if k is None:
        assert sys.platform != "linux"
        pytest.skip(f"no pthread_setname_np on {sys.platform}")


async def test_run_in_worker_thread() -> None:
    trio_thread = threading.current_thread()

    def f(x: T) -> tuple[T, threading.Thread]:
        return (x, threading.current_thread())

    x, child_thread = await to_thread_run_sync(f, 1)
    assert x == 1
    assert child_thread != trio_thread

    def g() -> NoReturn:
        raise ValueError(threading.current_thread())

    with pytest.raises(
        ValueError,
        match=r"^<Thread\(Trio thread \d+, started daemon \d+\)>$",
    ) as excinfo:
        await to_thread_run_sync(g)
    print(excinfo.value.args)
    assert excinfo.value.args[0] != trio_thread


async def test_run_in_worker_thread_cancellation() -> None:
    register: list[str | None] = [None]

    def f(q: stdlib_queue.Queue[None]) -> None:
        # Make the thread block for a controlled amount of time
        register[0] = "blocking"
        q.get()
        register[0] = "finished"

    async def child(q: stdlib_queue.Queue[None], abandon_on_cancel: bool) -> None:
        record.append("start")
        try:
            return await to_thread_run_sync(f, q, abandon_on_cancel=abandon_on_cancel)
        finally:
            record.append("exit")

    record: list[str] = []
    q: stdlib_queue.Queue[None] = stdlib_queue.Queue()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(child, q, True)
        # Give it a chance to get started. (This is important because
        # to_thread_run_sync does a checkpoint_if_cancelled before
        # blocking on the thread, and we don't want to trigger this.)
        await wait_all_tasks_blocked()
        assert record == ["start"]
        # Then cancel it.
        nursery.cancel_scope.cancel()
    # The task exited, but the thread didn't:
    assert register[0] != "finished"
    # Put the thread out of its misery:
    q.put(None)
    while register[0] != "finished":
        time.sleep(0.01)  # noqa: ASYNC251  # Need to wait for OS thread

    # This one can't be cancelled
    record = []
    register[0] = None
    async with _core.open_nursery() as nursery:
        nursery.start_soon(child, q, False)
        await wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()
        with _core.CancelScope(shield=True):
            for _ in range(10):
                await _core.checkpoint()
        # It's still running
        assert record == ["start"]
        q.put(None)
        # Now it exits

    # But if we cancel *before* it enters, the entry is itself a cancellation
    # point
    with _core.CancelScope() as scope:
        scope.cancel()
        await child(q, False)
    assert scope.cancelled_caught


# Make sure that if trio.run exits, and then the thread finishes, then that's
# handled gracefully. (Requires that the thread result machinery be prepared
# for call_soon to raise RunFinishedError.)
def test_run_in_worker_thread_abandoned(
    capfd: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_core._thread_cache, "IDLE_TIMEOUT", 0.01)

    q1: stdlib_queue.Queue[None] = stdlib_queue.Queue()
    q2: stdlib_queue.Queue[threading.Thread] = stdlib_queue.Queue()

    def thread_fn() -> None:
        q1.get()
        q2.put(threading.current_thread())

    async def main() -> None:
        async def child() -> None:
            await to_thread_run_sync(thread_fn, abandon_on_cancel=True)

        async with _core.open_nursery() as nursery:
            nursery.start_soon(child)
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()

    _core.run(main)

    q1.put(None)
    # This makes sure:
    # - the thread actually ran
    # - that thread has finished before we check for its output
    thread = q2.get()
    while thread.is_alive():
        time.sleep(0.01)  # pragma: no cover

    # Make sure we don't have a "Exception in thread ..." dump to the console:
    out, err = capfd.readouterr()
    assert "Exception in thread" not in out
    assert "Exception in thread" not in err


@pytest.mark.parametrize("MAX", [3, 5, 10])
@pytest.mark.parametrize("cancel", [False, True])
@pytest.mark.parametrize("use_default_limiter", [False, True])
async def test_run_in_worker_thread_limiter(
    MAX: int,
    cancel: bool,
    use_default_limiter: bool,
) -> None:
    # This test is a bit tricky. The goal is to make sure that if we set
    # limiter=CapacityLimiter(MAX), then in fact only MAX threads are ever
    # running at a time, even if there are more concurrent calls to
    # to_thread_run_sync, and even if some of those are cancelled. And
    # also to make sure that the default limiter actually limits.
    COUNT = 2 * MAX
    gate = threading.Event()
    lock = threading.Lock()
    if use_default_limiter:
        c = current_default_thread_limiter()
        orig_total_tokens = c.total_tokens
        c.total_tokens = MAX
        limiter_arg = None
    else:
        c = CapacityLimiter(MAX)
        orig_total_tokens = MAX
        limiter_arg = c
    try:
        # We used to use regular variables and 'nonlocal' here, but it turns
        # out that it's not safe to assign to closed-over variables that are
        # visible in multiple threads, at least as of CPython 3.10 and PyPy
        # 7.3:
        #
        #   https://bugs.python.org/issue30744
        #   https://bitbucket.org/pypy/pypy/issues/2591/
        #
        # Mutating them in-place is OK though (as long as you use proper
        # locking etc.).
        class state:
            ran: int
            high_water: int
            running: int
            parked: int

        state.ran = 0
        state.high_water = 0
        state.running = 0
        state.parked = 0

        token = _core.current_trio_token()

        def thread_fn(cancel_scope: CancelScope) -> None:
            print("thread_fn start")
            from_thread_run_sync(cancel_scope.cancel, trio_token=token)
            with lock:
                state.ran += 1
                state.running += 1
                state.high_water = max(state.high_water, state.running)
                # The Trio thread below watches this value and uses it as a
                # signal that all the stats calculations have finished.
                state.parked += 1
            gate.wait()
            with lock:
                state.parked -= 1
                state.running -= 1
            print("thread_fn exiting")

        async def run_thread(event: Event) -> None:
            with _core.CancelScope() as cancel_scope:
                await to_thread_run_sync(
                    thread_fn,
                    cancel_scope,
                    abandon_on_cancel=cancel,
                    limiter=limiter_arg,
                )
            print("run_thread finished, cancelled:", cancel_scope.cancelled_caught)
            event.set()

        async with _core.open_nursery() as nursery:
            print("spawning")
            events = []
            for _ in range(COUNT):
                events.append(Event())
                nursery.start_soon(run_thread, events[-1])
                await wait_all_tasks_blocked()
            # In the cancel case, we in particular want to make sure that the
            # cancelled tasks don't release the semaphore. So let's wait until
            # at least one of them has exited, and that everything has had a
            # chance to settle down from this, before we check that everyone
            # who's supposed to be waiting is waiting:
            if cancel:
                print("waiting for first cancellation to clear")
                await events[0].wait()
                await wait_all_tasks_blocked()
            # Then wait until the first MAX threads are parked in gate.wait(),
            # and the next MAX threads are parked on the semaphore, to make
            # sure no-one is sneaking past, and to make sure the high_water
            # check below won't fail due to scheduling issues. (It could still
            # fail if too many threads are let through here.)
            while (  # noqa: ASYNC110
                state.parked != MAX or c.statistics().tasks_waiting != MAX
            ):
                await sleep(0.01)  # pragma: no cover
            # Then release the threads
            gate.set()

        assert state.high_water == MAX

        if cancel:
            # Some threads might still be running; need to wait to them to
            # finish before checking that all threads ran. We can do this
            # using the CapacityLimiter.
            while c.borrowed_tokens > 0:  # noqa: ASYNC110
                await sleep(0.01)  # pragma: no cover

        assert state.ran == COUNT
        assert state.running == 0
    finally:
        c.total_tokens = orig_total_tokens


async def test_run_in_worker_thread_custom_limiter() -> None:
    # Basically just checking that we only call acquire_on_behalf_of and
    # release_on_behalf_of, since that's part of our documented API.
    record = []

    class CustomLimiter:
        async def acquire_on_behalf_of(self, borrower: Task) -> None:
            record.append("acquire")
            self._borrower = borrower

        def release_on_behalf_of(self, borrower: Task) -> None:
            record.append("release")
            assert borrower == self._borrower

    # TODO: should CapacityLimiter have an abc or protocol so users can modify it?
    # because currently it's `final` so writing code like this is not allowed.
    await to_thread_run_sync(lambda: None, limiter=CustomLimiter())  # type: ignore[arg-type]
    assert record == ["acquire", "release"]


async def test_run_in_worker_thread_limiter_error() -> None:
    record = []

    class BadCapacityLimiter:
        async def acquire_on_behalf_of(self, borrower: Task) -> None:
            record.append("acquire")

        def release_on_behalf_of(self, borrower: Task) -> NoReturn:
            record.append("release")
            raise ValueError("release on behalf")

    bs = BadCapacityLimiter()

    with pytest.raises(ValueError, match=r"^release on behalf$") as excinfo:
        await to_thread_run_sync(lambda: None, limiter=bs)  # type: ignore[arg-type]
    assert excinfo.value.__context__ is None
    assert record == ["acquire", "release"]
    record = []

    # If the original function raised an error, then the semaphore error
    # chains with it
    d: dict[str, object] = {}
    with pytest.raises(ValueError, match=r"^release on behalf$") as excinfo:
        await to_thread_run_sync(lambda: d["x"], limiter=bs)  # type: ignore[arg-type]
    assert isinstance(excinfo.value.__context__, KeyError)
    assert record == ["acquire", "release"]


async def test_run_in_worker_thread_fail_to_spawn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Test the unlikely but possible case where trying to spawn a thread fails
    def bad_start(self: object, *args: object) -> NoReturn:
        raise RuntimeError("the engines canna take it captain")

    monkeypatch.setattr(_core._thread_cache.ThreadCache, "start_thread_soon", bad_start)

    limiter = current_default_thread_limiter()
    assert limiter.borrowed_tokens == 0

    # We get an appropriate error, and the limiter is cleanly released
    with pytest.raises(RuntimeError) as excinfo:
        await to_thread_run_sync(lambda: None)  # pragma: no cover
    assert "engines" in str(excinfo.value)

    assert limiter.borrowed_tokens == 0


async def test_trio_to_thread_run_sync_token() -> None:
    # Test that to_thread_run_sync automatically injects the current trio token
    # into a spawned thread
    def thread_fn() -> _core.TrioToken:
        callee_token = from_thread_run_sync(_core.current_trio_token)
        return callee_token

    caller_token = _core.current_trio_token()
    callee_token = await to_thread_run_sync(thread_fn)
    assert callee_token == caller_token


async def test_trio_to_thread_run_sync_expected_error() -> None:
    # Test correct error when passed async function
    async def async_fn() -> None:  # pragma: no cover
        pass

    with pytest.raises(TypeError, match="expected a sync function"):
        await to_thread_run_sync(async_fn)  # type: ignore[unused-coroutine]


trio_test_contextvar: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trio_test_contextvar",
)


async def test_trio_to_thread_run_sync_contextvars() -> None:
    trio_thread = threading.current_thread()
    trio_test_contextvar.set("main")

    def f() -> tuple[str, threading.Thread]:
        value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()
        return (value, threading.current_thread())

    value, child_thread = await to_thread_run_sync(f)
    assert value == "main"
    assert child_thread != trio_thread

    def g() -> tuple[str, str, threading.Thread]:
        parent_value = trio_test_contextvar.get()
        trio_test_contextvar.set("worker")
        inner_value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()
        return (
            parent_value,
            inner_value,
            threading.current_thread(),
        )

    parent_value, inner_value, child_thread = await to_thread_run_sync(g)
    current_value = trio_test_contextvar.get()
    assert parent_value == "main"
    assert inner_value == "worker"
    assert current_value == "main", (
        "The contextvar value set on the worker would not propagate back to the main"
        " thread"
    )
    assert sniffio.current_async_library() == "trio"


async def test_trio_from_thread_run_sync() -> None:
    # Test that to_thread_run_sync correctly "hands off" the trio token to
    # trio.from_thread.run_sync()
    def thread_fn_1() -> float:
        trio_time = from_thread_run_sync(_core.current_time)
        return trio_time

    trio_time = await to_thread_run_sync(thread_fn_1)
    assert isinstance(trio_time, float)

    # Test correct error when passed async function
    async def async_fn() -> None:  # pragma: no cover
        pass

    def thread_fn_2() -> None:
        from_thread_run_sync(async_fn)  # type: ignore[unused-coroutine]

    with pytest.raises(TypeError, match="expected a synchronous function"):
        await to_thread_run_sync(thread_fn_2)


async def test_trio_from_thread_run() -> None:
    # Test that to_thread_run_sync correctly "hands off" the trio token to
    # trio.from_thread.run()
    record = []

    async def back_in_trio_fn() -> None:
        _core.current_time()  # implicitly checks that we're in trio
        record.append("back in trio")

    def thread_fn() -> None:
        record.append("in thread")
        from_thread_run(back_in_trio_fn)

    await to_thread_run_sync(thread_fn)
    assert record == ["in thread", "back in trio"]

    # Test correct error when passed sync function
    def sync_fn() -> None:  # pragma: no cover
        pass

    with pytest.raises(TypeError, match="appears to be synchronous"):
        await to_thread_run_sync(from_thread_run, sync_fn)  # type: ignore[arg-type]


async def test_trio_from_thread_token() -> None:
    # Test that to_thread_run_sync and spawned trio.from_thread.run_sync()
    # share the same Trio token
    def thread_fn() -> _core.TrioToken:
        callee_token = from_thread_run_sync(_core.current_trio_token)
        return callee_token

    caller_token = _core.current_trio_token()
    callee_token = await to_thread_run_sync(thread_fn)
    assert callee_token == caller_token


async def test_trio_from_thread_token_kwarg() -> None:
    # Test that to_thread_run_sync and spawned trio.from_thread.run_sync() can
    # use an explicitly defined token
    def thread_fn(token: _core.TrioToken) -> _core.TrioToken:
        callee_token = from_thread_run_sync(_core.current_trio_token, trio_token=token)
        return callee_token

    caller_token = _core.current_trio_token()
    callee_token = await to_thread_run_sync(thread_fn, caller_token)
    assert callee_token == caller_token


async def test_from_thread_no_token() -> None:
    # Test that a "raw call" to trio.from_thread.run() fails because no token
    # has been provided

    with pytest.raises(RuntimeError):
        from_thread_run_sync(_core.current_time)


async def test_trio_from_thread_run_sync_contextvars() -> None:
    trio_test_contextvar.set("main")

    def thread_fn() -> tuple[str, str, str, str, str]:
        thread_parent_value = trio_test_contextvar.get()
        trio_test_contextvar.set("worker")
        thread_current_value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()

        def back_in_main() -> tuple[str, str]:
            back_parent_value = trio_test_contextvar.get()
            trio_test_contextvar.set("back_in_main")
            back_current_value = trio_test_contextvar.get()
            assert sniffio.current_async_library() == "trio"
            return back_parent_value, back_current_value

        back_parent_value, back_current_value = from_thread_run_sync(back_in_main)
        thread_after_value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()
        return (
            thread_parent_value,
            thread_current_value,
            thread_after_value,
            back_parent_value,
            back_current_value,
        )

    (
        thread_parent_value,
        thread_current_value,
        thread_after_value,
        back_parent_value,
        back_current_value,
    ) = await to_thread_run_sync(thread_fn)
    current_value = trio_test_contextvar.get()
    assert current_value == thread_parent_value == "main"
    assert thread_current_value == back_parent_value == thread_after_value == "worker"
    assert sniffio.current_async_library() == "trio"
    assert back_current_value == "back_in_main"


async def test_trio_from_thread_run_contextvars() -> None:
    trio_test_contextvar.set("main")

    def thread_fn() -> tuple[str, str, str, str, str]:
        thread_parent_value = trio_test_contextvar.get()
        trio_test_contextvar.set("worker")
        thread_current_value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()

        async def async_back_in_main() -> tuple[str, str]:
            back_parent_value = trio_test_contextvar.get()
            trio_test_contextvar.set("back_in_main")
            back_current_value = trio_test_contextvar.get()
            assert sniffio.current_async_library() == "trio"
            return back_parent_value, back_current_value

        back_parent_value, back_current_value = from_thread_run(async_back_in_main)
        thread_after_value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()
        return (
            thread_parent_value,
            thread_current_value,
            thread_after_value,
            back_parent_value,
            back_current_value,
        )

    (
        thread_parent_value,
        thread_current_value,
        thread_after_value,
        back_parent_value,
        back_current_value,
    ) = await to_thread_run_sync(thread_fn)
    current_value = trio_test_contextvar.get()
    assert current_value == thread_parent_value == "main"
    assert thread_current_value == back_parent_value == thread_after_value == "worker"
    assert back_current_value == "back_in_main"
    assert sniffio.current_async_library() == "trio"


def test_run_fn_as_system_task_caught_badly_typed_token() -> None:
    with pytest.raises(RuntimeError):
        from_thread_run_sync(
            _core.current_time,
            trio_token="Not TrioTokentype",  # type: ignore[arg-type]
        )


async def test_from_thread_inside_trio_thread() -> None:
    def not_called() -> None:  # pragma: no cover
        raise AssertionError()

    trio_token = _core.current_trio_token()
    with pytest.raises(RuntimeError):
        from_thread_run_sync(not_called, trio_token=trio_token)


def test_from_thread_run_during_shutdown() -> None:
    save = []
    record = []

    async def agen(token: _core.TrioToken | None) -> AsyncGenerator[None, None]:
        try:
            yield
        finally:
            with _core.CancelScope(shield=True):
                try:
                    await to_thread_run_sync(
                        partial(from_thread_run, sleep, 0, trio_token=token),
                    )
                except _core.RunFinishedError:
                    record.append("finished")
                else:
                    record.append("clean")

    async def main(use_system_task: bool) -> None:
        save.append(agen(_core.current_trio_token() if use_system_task else None))
        await save[-1].asend(None)

    _core.run(main, True)  # System nursery will be closed and raise RunFinishedError
    _core.run(main, False)  # host task will be rescheduled as normal
    assert record == ["finished", "clean"]


async def test_trio_token_weak_referenceable() -> None:
    token = _core.current_trio_token()
    assert isinstance(token, _core.TrioToken)
    weak_reference = weakref.ref(token)
    assert token is weak_reference()


async def test_unsafe_abandon_on_cancel_kwarg() -> None:
    # This is a stand in for a numpy ndarray or other objects
    # that (maybe surprisingly) lack a notion of truthiness
    class BadBool:
        def __bool__(self) -> bool:
            raise NotImplementedError

    with pytest.raises(NotImplementedError):
        await to_thread_run_sync(int, abandon_on_cancel=BadBool())  # type: ignore[arg-type]


async def test_from_thread_reuses_task() -> None:
    task = _core.current_task()

    async def async_current_task() -> _core.Task:
        return _core.current_task()

    assert task is await to_thread_run_sync(from_thread_run_sync, _core.current_task)
    assert task is await to_thread_run_sync(from_thread_run, async_current_task)


async def test_recursive_to_thread() -> None:
    tid = None

    def get_tid_then_reenter() -> int:
        nonlocal tid
        tid = threading.get_ident()
        return from_thread_run(to_thread_run_sync, threading.get_ident)

    assert tid != await to_thread_run_sync(get_tid_then_reenter)


async def test_from_thread_host_cancelled() -> None:
    queue: stdlib_queue.Queue[bool] = stdlib_queue.Queue()

    def sync_check() -> None:
        from_thread_run_sync(cancel_scope.cancel)
        try:
            from_thread_run_sync(bool)
        except _core.Cancelled:  # pragma: no cover
            queue.put(True)  # sync functions don't raise Cancelled
        else:
            queue.put(False)

    with _core.CancelScope() as cancel_scope:
        await to_thread_run_sync(sync_check)

    assert not cancel_scope.cancelled_caught
    assert not queue.get_nowait()

    with _core.CancelScope() as cancel_scope:
        await to_thread_run_sync(sync_check, abandon_on_cancel=True)

    assert cancel_scope.cancelled_caught
    assert not await to_thread_run_sync(partial(queue.get, timeout=1))

    async def no_checkpoint() -> bool:
        return True

    def async_check() -> None:
        from_thread_run_sync(cancel_scope.cancel)
        try:
            assert from_thread_run(no_checkpoint)
        except _core.Cancelled:  # pragma: no cover
            queue.put(True)  # async functions raise Cancelled at checkpoints
        else:
            queue.put(False)

    with _core.CancelScope() as cancel_scope:
        await to_thread_run_sync(async_check)

    assert not cancel_scope.cancelled_caught
    assert not queue.get_nowait()

    with _core.CancelScope() as cancel_scope:
        await to_thread_run_sync(async_check, abandon_on_cancel=True)

    assert cancel_scope.cancelled_caught
    assert not await to_thread_run_sync(partial(queue.get, timeout=1))

    async def async_time_bomb() -> None:
        cancel_scope.cancel()
        with fail_after(10):
            await sleep_forever()

    with _core.CancelScope() as cancel_scope:
        await to_thread_run_sync(from_thread_run, async_time_bomb)

    assert cancel_scope.cancelled_caught


async def test_from_thread_check_cancelled() -> None:
    q: stdlib_queue.Queue[str] = stdlib_queue.Queue()

    async def child(abandon_on_cancel: bool, scope: CancelScope) -> None:
        with scope:
            record.append("start")
            try:
                return await to_thread_run_sync(f, abandon_on_cancel=abandon_on_cancel)
            except _core.Cancelled:
                record.append("cancel")
                raise
            finally:
                record.append("exit")

    def f() -> None:
        try:
            from_thread_check_cancelled()
        except _core.Cancelled:  # pragma: no cover, test failure path
            q.put("Cancelled")
        else:
            q.put("Not Cancelled")
        ev.wait()
        return from_thread_check_cancelled()

    # Base case: nothing cancelled so we shouldn't see cancels anywhere
    record: list[str] = []
    ev = threading.Event()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(child, False, _core.CancelScope())
        await wait_all_tasks_blocked()
        assert record[0] == "start"
        assert q.get(timeout=1) == "Not Cancelled"
        ev.set()
    # implicit assertion, Cancelled not raised via nursery
    assert record[1] == "exit"

    # abandon_on_cancel=False case: a cancel will pop out but be handled by
    # the appropriate cancel scope
    record = []
    ev = threading.Event()
    scope = _core.CancelScope()  # Nursery cancel scope gives false positives
    async with _core.open_nursery() as nursery:
        nursery.start_soon(child, False, scope)
        await wait_all_tasks_blocked()
        assert record[0] == "start"
        assert q.get(timeout=1) == "Not Cancelled"
        scope.cancel()
        ev.set()
    assert scope.cancelled_caught
    assert "cancel" in record
    assert record[-1] == "exit"

    # abandon_on_cancel=True case: slightly different thread behavior needed
    # check thread is cancelled "soon" after abandonment
    def f() -> None:  # type: ignore[no-redef] # noqa: F811
        ev.wait()
        try:
            from_thread_check_cancelled()
        except _core.Cancelled:
            q.put("Cancelled")
        else:  # pragma: no cover, test failure path
            q.put("Not Cancelled")

    record = []
    ev = threading.Event()
    scope = _core.CancelScope()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(child, True, scope)
        await wait_all_tasks_blocked()
        assert record[0] == "start"
        scope.cancel()
        ev.set()
    assert scope.cancelled_caught
    assert "cancel" in record
    assert record[-1] == "exit"
    assert q.get(timeout=1) == "Cancelled"


def test_from_thread_check_cancelled_raises_in_foreign_threads() -> None:
    with pytest.raises(RuntimeError):
        from_thread_check_cancelled()
    q: stdlib_queue.Queue[Outcome[object]] = stdlib_queue.Queue()
    _core.start_thread_soon(from_thread_check_cancelled, lambda _: q.put(_))
    with pytest.raises(RuntimeError):
        q.get(timeout=1).unwrap()


@slow
async def test_reentry_doesnt_deadlock() -> None:
    # Regression test for issue noticed in GH-2827
    # The failure mode is to hang the whole test suite, unfortunately.
    # XXX consider running this in a subprocess with a timeout, if it comes up again!

    async def child() -> None:
        while True:
            await to_thread_run_sync(from_thread_run, sleep, 0, abandon_on_cancel=False)

    with move_on_after(2):
        async with _core.open_nursery() as nursery:
            for _ in range(4):
                nursery.start_soon(child)


async def test_wait_all_threads_completed() -> None:
    no_threads_left = False
    e1 = Event()
    e2 = Event()

    e1_exited = Event()
    e2_exited = Event()

    async def wait_event(e: Event, e_exit: Event) -> None:
        def thread() -> None:
            from_thread_run(e.wait)

        await to_thread_run_sync(thread)
        e_exit.set()

    async def wait_no_threads_left() -> None:
        nonlocal no_threads_left
        await wait_all_threads_completed()
        no_threads_left = True

    async with _core.open_nursery() as nursery:
        nursery.start_soon(wait_event, e1, e1_exited)
        nursery.start_soon(wait_event, e2, e2_exited)
        await wait_all_tasks_blocked()
        nursery.start_soon(wait_no_threads_left)
        await wait_all_tasks_blocked()
        assert not no_threads_left
        assert active_thread_count() == 2

        e1.set()
        await e1_exited.wait()
        await wait_all_tasks_blocked()
        assert not no_threads_left
        assert active_thread_count() == 1

        e2.set()
        await e2_exited.wait()
        await wait_all_tasks_blocked()
        assert no_threads_left
        assert active_thread_count() == 0


async def test_wait_all_threads_completed_no_threads() -> None:
    await wait_all_threads_completed()
    assert active_thread_count() == 0

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\hf_file_system.py ===
import os
import re
import tempfile
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Any, Dict, Iterator, List, NoReturn, Optional, Tuple, Union
from urllib.parse import quote, unquote

import fsspec
from fsspec.callbacks import _DEFAULT_CALLBACK, NoOpCallback, TqdmCallback
from fsspec.utils import isfilelike
from requests import Response

from . import constants
from ._commit_api import CommitOperationCopy, CommitOperationDelete
from .errors import EntryNotFoundError, RepositoryNotFoundError, RevisionNotFoundError
from .file_download import hf_hub_url, http_get
from .hf_api import HfApi, LastCommitInfo, RepoFile
from .utils import HFValidationError, hf_raise_for_status, http_backoff


# Regex used to match special revisions with "/" in them (see #1710)
SPECIAL_REFS_REVISION_REGEX = re.compile(
    r"""
    (^refs\/convert\/\w+)     # `refs/convert/parquet` revisions
    |
    (^refs\/pr\/\d+)          # PR revisions
    """,
    re.VERBOSE,
)


@dataclass
class HfFileSystemResolvedPath:
    """Data structure containing information about a resolved Hugging Face file system path."""

    repo_type: str
    repo_id: str
    revision: str
    path_in_repo: str
    # The part placed after '@' in the initial path. It can be a quoted or unquoted refs revision.
    # Used to reconstruct the unresolved path to return to the user.
    _raw_revision: Optional[str] = field(default=None, repr=False)

    def unresolve(self) -> str:
        repo_path = constants.REPO_TYPES_URL_PREFIXES.get(self.repo_type, "") + self.repo_id
        if self._raw_revision:
            return f"{repo_path}@{self._raw_revision}/{self.path_in_repo}".rstrip("/")
        elif self.revision != constants.DEFAULT_REVISION:
            return f"{repo_path}@{safe_revision(self.revision)}/{self.path_in_repo}".rstrip("/")
        else:
            return f"{repo_path}/{self.path_in_repo}".rstrip("/")


class HfFileSystem(fsspec.AbstractFileSystem):
    """
    Access a remote Hugging Face Hub repository as if were a local file system.

    <Tip warning={true}>

        [`HfFileSystem`] provides fsspec compatibility, which is useful for libraries that require it (e.g., reading
        Hugging Face datasets directly with `pandas`). However, it introduces additional overhead due to this compatibility
        layer. For better performance and reliability, it's recommended to use `HfApi` methods when possible.

    </Tip>

    Args:
        token (`str` or `bool`, *optional*):
            A valid user access token (string). Defaults to the locally saved
            token, which is the recommended method for authentication (see
            https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
            To disable authentication, pass `False`.
        endpoint (`str`, *optional*):
            Endpoint of the Hub. Defaults to <https://huggingface.co>.
    Usage:

    ```python
    >>> from huggingface_hub import HfFileSystem

    >>> fs = HfFileSystem()

    >>> # List files
    >>> fs.glob("my-username/my-model/*.bin")
    ['my-username/my-model/pytorch_model.bin']
    >>> fs.ls("datasets/my-username/my-dataset", detail=False)
    ['datasets/my-username/my-dataset/.gitattributes', 'datasets/my-username/my-dataset/README.md', 'datasets/my-username/my-dataset/data.json']

    >>> # Read/write files
    >>> with fs.open("my-username/my-model/pytorch_model.bin") as f:
    ...     data = f.read()
    >>> with fs.open("my-username/my-model/pytorch_model.bin", "wb") as f:
    ...     f.write(data)
    ```
    """

    root_marker = ""
    protocol = "hf"

    def __init__(
        self,
        *args,
        endpoint: Optional[str] = None,
        token: Union[bool, str, None] = None,
        **storage_options,
    ):
        super().__init__(*args, **storage_options)
        self.endpoint = endpoint or constants.ENDPOINT
        self.token = token
        self._api = HfApi(endpoint=endpoint, token=token)
        # Maps (repo_type, repo_id, revision) to a 2-tuple with:
        #  * the 1st element indicating whether the repositoy and the revision exist
        #  * the 2nd element being the exception raised if the repository or revision doesn't exist
        self._repo_and_revision_exists_cache: Dict[
            Tuple[str, str, Optional[str]], Tuple[bool, Optional[Exception]]
        ] = {}

    def _repo_and_revision_exist(
        self, repo_type: str, repo_id: str, revision: Optional[str]
    ) -> Tuple[bool, Optional[Exception]]:
        if (repo_type, repo_id, revision) not in self._repo_and_revision_exists_cache:
            try:
                self._api.repo_info(
                    repo_id, revision=revision, repo_type=repo_type, timeout=constants.HF_HUB_ETAG_TIMEOUT
                )
            except (RepositoryNotFoundError, HFValidationError) as e:
                self._repo_and_revision_exists_cache[(repo_type, repo_id, revision)] = False, e
                self._repo_and_revision_exists_cache[(repo_type, repo_id, None)] = False, e
            except RevisionNotFoundError as e:
                self._repo_and_revision_exists_cache[(repo_type, repo_id, revision)] = False, e
                self._repo_and_revision_exists_cache[(repo_type, repo_id, None)] = True, None
            else:
                self._repo_and_revision_exists_cache[(repo_type, repo_id, revision)] = True, None
                self._repo_and_revision_exists_cache[(repo_type, repo_id, None)] = True, None
        return self._repo_and_revision_exists_cache[(repo_type, repo_id, revision)]

    def resolve_path(self, path: str, revision: Optional[str] = None) -> HfFileSystemResolvedPath:
        """
        Resolve a Hugging Face file system path into its components.

        Args:
            path (`str`):
                Path to resolve.
            revision (`str`, *optional*):
                The revision of the repo to resolve. Defaults to the revision specified in the path.

        Returns:
            [`HfFileSystemResolvedPath`]: Resolved path information containing `repo_type`, `repo_id`, `revision` and `path_in_repo`.

        Raises:
            `ValueError`:
                If path contains conflicting revision information.
            `NotImplementedError`:
                If trying to list repositories.
        """

        def _align_revision_in_path_with_revision(
            revision_in_path: Optional[str], revision: Optional[str]
        ) -> Optional[str]:
            if revision is not None:
                if revision_in_path is not None and revision_in_path != revision:
                    raise ValueError(
                        f'Revision specified in path ("{revision_in_path}") and in `revision` argument ("{revision}")'
                        " are not the same."
                    )
            else:
                revision = revision_in_path
            return revision

        path = self._strip_protocol(path)
        if not path:
            # can't list repositories at root
            raise NotImplementedError("Access to repositories lists is not implemented.")
        elif path.split("/")[0] + "/" in constants.REPO_TYPES_URL_PREFIXES.values():
            if "/" not in path:
                # can't list repositories at the repository type level
                raise NotImplementedError("Access to repositories lists is not implemented.")
            repo_type, path = path.split("/", 1)
            repo_type = constants.REPO_TYPES_MAPPING[repo_type]
        else:
            repo_type = constants.REPO_TYPE_MODEL
        if path.count("/") > 0:
            if "@" in path:
                repo_id, revision_in_path = path.split("@", 1)
                if "/" in revision_in_path:
                    match = SPECIAL_REFS_REVISION_REGEX.search(revision_in_path)
                    if match is not None and revision in (None, match.group()):
                        # Handle `refs/convert/parquet` and PR revisions separately
                        path_in_repo = SPECIAL_REFS_REVISION_REGEX.sub("", revision_in_path).lstrip("/")
                        revision_in_path = match.group()
                    else:
                        revision_in_path, path_in_repo = revision_in_path.split("/", 1)
                else:
                    path_in_repo = ""
                revision = _align_revision_in_path_with_revision(unquote(revision_in_path), revision)
                repo_and_revision_exist, err = self._repo_and_revision_exist(repo_type, repo_id, revision)
                if not repo_and_revision_exist:
                    _raise_file_not_found(path, err)
            else:
                revision_in_path = None
                repo_id_with_namespace = "/".join(path.split("/")[:2])
                path_in_repo_with_namespace = "/".join(path.split("/")[2:])
                repo_id_without_namespace = path.split("/")[0]
                path_in_repo_without_namespace = "/".join(path.split("/")[1:])
                repo_id = repo_id_with_namespace
                path_in_repo = path_in_repo_with_namespace
                repo_and_revision_exist, err = self._repo_and_revision_exist(repo_type, repo_id, revision)
                if not repo_and_revision_exist:
                    if isinstance(err, (RepositoryNotFoundError, HFValidationError)):
                        repo_id = repo_id_without_namespace
                        path_in_repo = path_in_repo_without_namespace
                        repo_and_revision_exist, _ = self._repo_and_revision_exist(repo_type, repo_id, revision)
                        if not repo_and_revision_exist:
                            _raise_file_not_found(path, err)
                    else:
                        _raise_file_not_found(path, err)
        else:
            repo_id = path
            path_in_repo = ""
            if "@" in path:
                repo_id, revision_in_path = path.split("@", 1)
                revision = _align_revision_in_path_with_revision(unquote(revision_in_path), revision)
            else:
                revision_in_path = None
            repo_and_revision_exist, _ = self._repo_and_revision_exist(repo_type, repo_id, revision)
            if not repo_and_revision_exist:
                raise NotImplementedError("Access to repositories lists is not implemented.")

        revision = revision if revision is not None else constants.DEFAULT_REVISION
        return HfFileSystemResolvedPath(repo_type, repo_id, revision, path_in_repo, _raw_revision=revision_in_path)

    def invalidate_cache(self, path: Optional[str] = None) -> None:
        """
        Clear the cache for a given path.

        For more details, refer to [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.invalidate_cache).

        Args:
            path (`str`, *optional*):
                Path to clear from cache. If not provided, clear the entire cache.

        """
        if not path:
            self.dircache.clear()
            self._repo_and_revision_exists_cache.clear()
        else:
            resolved_path = self.resolve_path(path)
            path = resolved_path.unresolve()
            while path:
                self.dircache.pop(path, None)
                path = self._parent(path)

            # Only clear repo cache if path is to repo root
            if not resolved_path.path_in_repo:
                self._repo_and_revision_exists_cache.pop((resolved_path.repo_type, resolved_path.repo_id, None), None)
                self._repo_and_revision_exists_cache.pop(
                    (resolved_path.repo_type, resolved_path.repo_id, resolved_path.revision), None
                )

    def _open(
        self,
        path: str,
        mode: str = "rb",
        revision: Optional[str] = None,
        block_size: Optional[int] = None,
        **kwargs,
    ) -> "HfFileSystemFile":
        if "a" in mode:
            raise NotImplementedError("Appending to remote files is not yet supported.")
        if block_size == 0:
            return HfFileSystemStreamFile(self, path, mode=mode, revision=revision, block_size=block_size, **kwargs)
        else:
            return HfFileSystemFile(self, path, mode=mode, revision=revision, block_size=block_size, **kwargs)

    def _rm(self, path: str, revision: Optional[str] = None, **kwargs) -> None:
        resolved_path = self.resolve_path(path, revision=revision)
        self._api.delete_file(
            path_in_repo=resolved_path.path_in_repo,
            repo_id=resolved_path.repo_id,
            token=self.token,
            repo_type=resolved_path.repo_type,
            revision=resolved_path.revision,
            commit_message=kwargs.get("commit_message"),
            commit_description=kwargs.get("commit_description"),
        )
        self.invalidate_cache(path=resolved_path.unresolve())

    def rm(
        self,
        path: str,
        recursive: bool = False,
        maxdepth: Optional[int] = None,
        revision: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Delete files from a repository.

        For more details, refer to [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.rm).

        <Tip warning={true}>

            Note: When possible, use `HfApi.delete_file()` for better performance.

        </Tip>

        Args:
            path (`str`):
                Path to delete.
            recursive (`bool`, *optional*):
                If True, delete directory and all its contents. Defaults to False.
            maxdepth (`int`, *optional*):
                Maximum number of subdirectories to visit when deleting recursively.
            revision (`str`, *optional*):
                The git revision to delete from.

        """
        resolved_path = self.resolve_path(path, revision=revision)
        paths = self.expand_path(path, recursive=recursive, maxdepth=maxdepth, revision=revision)
        paths_in_repo = [self.resolve_path(path).path_in_repo for path in paths if not self.isdir(path)]
        operations = [CommitOperationDelete(path_in_repo=path_in_repo) for path_in_repo in paths_in_repo]
        commit_message = f"Delete {path} "
        commit_message += "recursively " if recursive else ""
        commit_message += f"up to depth {maxdepth} " if maxdepth is not None else ""
        # TODO: use `commit_description` to list all the deleted paths?
        self._api.create_commit(
            repo_id=resolved_path.repo_id,
            repo_type=resolved_path.repo_type,
            token=self.token,
            operations=operations,
            revision=resolved_path.revision,
            commit_message=kwargs.get("commit_message", commit_message),
            commit_description=kwargs.get("commit_description"),
        )
        self.invalidate_cache(path=resolved_path.unresolve())

    def ls(
        self, path: str, detail: bool = True, refresh: bool = False, revision: Optional[str] = None, **kwargs
    ) -> List[Union[str, Dict[str, Any]]]:
        """
        List the contents of a directory.

        For more details, refer to [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.ls).

        <Tip warning={true}>

            Note: When possible, use `HfApi.list_repo_tree()` for better performance.

        </Tip>

        Args:
            path (`str`):
                Path to the directory.
            detail (`bool`, *optional*):
                If True, returns a list of dictionaries containing file information. If False,
                returns a list of file paths. Defaults to True.
            refresh (`bool`, *optional*):
                If True, bypass the cache and fetch the latest data. Defaults to False.
            revision (`str`, *optional*):
                The git revision to list from.

        Returns:
            `List[Union[str, Dict[str, Any]]]`: List of file paths (if detail=False) or list of file information
            dictionaries (if detail=True).
        """
        resolved_path = self.resolve_path(path, revision=revision)
        path = resolved_path.unresolve()
        kwargs = {"expand_info": detail, **kwargs}
        try:
            out = self._ls_tree(path, refresh=refresh, revision=revision, **kwargs)
        except EntryNotFoundError:
            # Path could be a file
            if not resolved_path.path_in_repo:
                _raise_file_not_found(path, None)
            out = self._ls_tree(self._parent(path), refresh=refresh, revision=revision, **kwargs)
            out = [o for o in out if o["name"] == path]
            if len(out) == 0:
                _raise_file_not_found(path, None)
        return out if detail else [o["name"] for o in out]

    def _ls_tree(
        self,
        path: str,
        recursive: bool = False,
        refresh: bool = False,
        revision: Optional[str] = None,
        expand_info: bool = True,
    ):
        resolved_path = self.resolve_path(path, revision=revision)
        path = resolved_path.unresolve()
        root_path = HfFileSystemResolvedPath(
            resolved_path.repo_type,
            resolved_path.repo_id,
            resolved_path.revision,
            path_in_repo="",
            _raw_revision=resolved_path._raw_revision,
        ).unresolve()

        out = []
        if path in self.dircache and not refresh:
            cached_path_infos = self.dircache[path]
            out.extend(cached_path_infos)
            dirs_not_in_dircache = []
            if recursive:
                # Use BFS to traverse the cache and build the "recursive "output
                # (The Hub uses a so-called "tree first" strategy for the tree endpoint but we sort the output to follow the spec so the result is (eventually) the same)
                dirs_to_visit = deque(
                    [path_info for path_info in cached_path_infos if path_info["type"] == "directory"]
                )
                while dirs_to_visit:
                    dir_info = dirs_to_visit.popleft()
                    if dir_info["name"] not in self.dircache:
                        dirs_not_in_dircache.append(dir_info["name"])
                    else:
                        cached_path_infos = self.dircache[dir_info["name"]]
                        out.extend(cached_path_infos)
                        dirs_to_visit.extend(
                            [path_info for path_info in cached_path_infos if path_info["type"] == "directory"]
                        )

            dirs_not_expanded = []
            if expand_info:
                # Check if there are directories with non-expanded entries
                dirs_not_expanded = [self._parent(o["name"]) for o in out if o["last_commit"] is None]

            if (recursive and dirs_not_in_dircache) or (expand_info and dirs_not_expanded):
                # If the dircache is incomplete, find the common path of the missing and non-expanded entries
                # and extend the output with the result of `_ls_tree(common_path, recursive=True)`
                common_prefix = os.path.commonprefix(dirs_not_in_dircache + dirs_not_expanded)
                # Get the parent directory if the common prefix itself is not a directory
                common_path = (
                    common_prefix.rstrip("/")
                    if common_prefix.endswith("/")
                    or common_prefix == root_path
                    or common_prefix in chain(dirs_not_in_dircache, dirs_not_expanded)
                    else self._parent(common_prefix)
                )
                out = [o for o in out if not o["name"].startswith(common_path + "/")]
                for cached_path in self.dircache:
                    if cached_path.startswith(common_path + "/"):
                        self.dircache.pop(cached_path, None)
                self.dircache.pop(common_path, None)
                out.extend(
                    self._ls_tree(
                        common_path,
                        recursive=recursive,
                        refresh=True,
                        revision=revision,
                        expand_info=expand_info,
                    )
                )
        else:
            tree = self._api.list_repo_tree(
                resolved_path.repo_id,
                resolved_path.path_in_repo,
                recursive=recursive,
                expand=expand_info,
                revision=resolved_path.revision,
                repo_type=resolved_path.repo_type,
            )
            for path_info in tree:
                if isinstance(path_info, RepoFile):
                    cache_path_info = {
                        "name": root_path + "/" + path_info.path,
                        "size": path_info.size,
                        "type": "file",
                        "blob_id": path_info.blob_id,
                        "lfs": path_info.lfs,
                        "last_commit": path_info.last_commit,
                        "security": path_info.security,
                    }
                else:
                    cache_path_info = {
                        "name": root_path + "/" + path_info.path,
                        "size": 0,
                        "type": "directory",
                        "tree_id": path_info.tree_id,
                        "last_commit": path_info.last_commit,
                    }
                parent_path = self._parent(cache_path_info["name"])
                self.dircache.setdefault(parent_path, []).append(cache_path_info)
                out.append(cache_path_info)
        return out

    def walk(self, path: str, *args, **kwargs) -> Iterator[Tuple[str, List[str], List[str]]]:
        """
        Return all files below the given path.

        For more details, refer to [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.walk).

        Args:
            path (`str`):
                Root path to list files from.

        Returns:
            `Iterator[Tuple[str, List[str], List[str]]]`: An iterator of (path, list of directory names, list of file names) tuples.
        """
        # Set expand_info=False by default to get a x10 speed boost
        kwargs = {"expand_info": kwargs.get("detail", False), **kwargs}
        path = self.resolve_path(path, revision=kwargs.get("revision")).unresolve()
        yield from super().walk(path, *args, **kwargs)

    def glob(self, path: str, **kwargs) -> List[str]:
        """
        Find files by glob-matching.

        For more details, refer to [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.glob).

        Args:
            path (`str`):
                Path pattern to match.

        Returns:
            `List[str]`: List of paths matching the pattern.
        """
        # Set expand_info=False by default to get a x10 speed boost
        kwargs = {"expand_info": kwargs.get("detail", False), **kwargs}
        path = self.resolve_path(path, revision=kwargs.get("revision")).unresolve()
        return super().glob(path, **kwargs)

    def find(
        self,
        path: str,
        maxdepth: Optional[int] = None,
        withdirs: bool = False,
        detail: bool = False,
        refresh: bool = False,
        revision: Optional[str] = None,
        **kwargs,
    ) -> Union[List[str], Dict[str, Dict[str, Any]]]:
        """
        List all files below path.

        For more details, refer to [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.find).

        Args:
            path (`str`):
                Root path to list files from.
            maxdepth (`int`, *optional*):
                Maximum depth to descend into subdirectories.
            withdirs (`bool`, *optional*):
                Include directory paths in the output. Defaults to False.
            detail (`bool`, *optional*):
                If True, returns a dict mapping paths to file information. Defaults to False.
            refresh (`bool`, *optional*):
                If True, bypass the cache and fetch the latest data. Defaults to False.
            revision (`str`, *optional*):
                The git revision to list from.

        Returns:
            `Union[List[str], Dict[str, Dict[str, Any]]]`: List of paths or dict of file information.
        """
        if maxdepth:
            return super().find(
                path, maxdepth=maxdepth, withdirs=withdirs, detail=detail, refresh=refresh, revision=revision, **kwargs
            )
        resolved_path = self.resolve_path(path, revision=revision)
        path = resolved_path.unresolve()
        kwargs = {"expand_info": detail, **kwargs}
        try:
            out = self._ls_tree(path, recursive=True, refresh=refresh, revision=resolved_path.revision, **kwargs)
        except EntryNotFoundError:
            # Path could be a file
            if self.info(path, revision=revision, **kwargs)["type"] == "file":
                out = {path: {}}
            else:
                out = {}
        else:
            if not withdirs:
                out = [o for o in out if o["type"] != "directory"]
            else:
                # If `withdirs=True`, include the directory itself to be consistent with the spec
                path_info = self.info(path, revision=resolved_path.revision, **kwargs)
                out = [path_info] + out if path_info["type"] == "directory" else out
            out = {o["name"]: o for o in out}
        names = sorted(out)
        if not detail:
            return names
        else:
            return {name: out[name] for name in names}

    def cp_file(self, path1: str, path2: str, revision: Optional[str] = None, **kwargs) -> None:
        """
        Copy a file within or between repositories.

        <Tip warning={true}>

            Note: When possible, use `HfApi.upload_file()` for better performance.

        </Tip>

        Args:
            path1 (`str`):
                Source path to copy from.
            path2 (`str`):
                Destination path to copy to.
            revision (`str`, *optional*):
                The git revision to copy from.

        """
        resolved_path1 = self.resolve_path(path1, revision=revision)
        resolved_path2 = self.resolve_path(path2, revision=revision)

        same_repo = (
            resolved_path1.repo_type == resolved_path2.repo_type and resolved_path1.repo_id == resolved_path2.repo_id
        )

        if same_repo:
            commit_message = f"Copy {path1} to {path2}"
            self._api.create_commit(
                repo_id=resolved_path1.repo_id,
                repo_type=resolved_path1.repo_type,
                revision=resolved_path2.revision,
                commit_message=kwargs.get("commit_message", commit_message),
                commit_description=kwargs.get("commit_description", ""),
                operations=[
                    CommitOperationCopy(
                        src_path_in_repo=resolved_path1.path_in_repo,
                        path_in_repo=resolved_path2.path_in_repo,
                        src_revision=resolved_path1.revision,
                    )
                ],
            )
        else:
            with self.open(path1, "rb", revision=resolved_path1.revision) as f:
                content = f.read()
            commit_message = f"Copy {path1} to {path2}"
            self._api.upload_file(
                path_or_fileobj=content,
                path_in_repo=resolved_path2.path_in_repo,
                repo_id=resolved_path2.repo_id,
                token=self.token,
                repo_type=resolved_path2.repo_type,
                revision=resolved_path2.revision,
                commit_message=kwargs.get("commit_message", commit_message),
                commit_description=kwargs.get("commit_description"),
            )
        self.invalidate_cache(path=resolved_path1.unresolve())
        self.invalidate_cache(path=resolved_path2.unresolve())

    def modified(self, path: str, **kwargs) -> datetime:
        """
        Get the last modified time of a file.

        For more details, refer to [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.modified).

        Args:
            path (`str`):
                Path to the file.

        Returns:
            `datetime`: Last commit date of the file.
        """
        info = self.info(path, **kwargs)
        return info["last_commit"]["date"]

    def info(self, path: str, refresh: bool = False, revision: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Get information about a file or directory.

        For more details, refer to [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.info).

        <Tip warning={true}>

            Note: When possible, use `HfApi.get_paths_info()` or `HfApi.repo_info()`  for better performance.

        </Tip>

        Args:
            path (`str`):
                Path to get info for.
            refresh (`bool`, *optional*):
                If True, bypass the cache and fetch the latest data. Defaults to False.
            revision (`str`, *optional*):
                The git revision to get info from.

        Returns:
            `Dict[str, Any]`: Dictionary containing file information (type, size, commit info, etc.).

        """
        resolved_path = self.resolve_path(path, revision=revision)
        path = resolved_path.unresolve()
        expand_info = kwargs.get(
            "expand_info", True
        )  # don't expose it as a parameter in the public API to follow the spec
        if not resolved_path.path_in_repo:
            # Path is the root directory
            out = {
                "name": path,
                "size": 0,
                "type": "directory",
            }
            if expand_info:
                last_commit = self._api.list_repo_commits(
                    resolved_path.repo_id, repo_type=resolved_path.repo_type, revision=resolved_path.revision
                )[-1]
                out = {
                    **out,
                    "tree_id": None,  # TODO: tree_id of the root directory?
                    "last_commit": LastCommitInfo(
                        oid=last_commit.commit_id, title=last_commit.title, date=last_commit.created_at
                    ),
                }
        else:
            out = None
            parent_path = self._parent(path)
            if not expand_info and parent_path not in self.dircache:
                # Fill the cache with cheap call
                self.ls(parent_path, expand_info=False)
            if parent_path in self.dircache:
                # Check if the path is in the cache
                out1 = [o for o in self.dircache[parent_path] if o["name"] == path]
                if not out1:
                    _raise_file_not_found(path, None)
                out = out1[0]
            if refresh or out is None or (expand_info and out and out["last_commit"] is None):
                paths_info = self._api.get_paths_info(
                    resolved_path.repo_id,
                    resolved_path.path_in_repo,
                    expand=expand_info,
                    revision=resolved_path.revision,
                    repo_type=resolved_path.repo_type,
                )
                if not paths_info:
                    _raise_file_not_found(path, None)
                path_info = paths_info[0]
                root_path = HfFileSystemResolvedPath(
                    resolved_path.repo_type,
                    resolved_path.repo_id,
                    resolved_path.revision,
                    path_in_repo="",
                    _raw_revision=resolved_path._raw_revision,
                ).unresolve()
                if isinstance(path_info, RepoFile):
                    out = {
                        "name": root_path + "/" + path_info.path,
                        "size": path_info.size,
                        "type": "file",
                        "blob_id": path_info.blob_id,
                        "lfs": path_info.lfs,
                        "last_commit": path_info.last_commit,
                        "security": path_info.security,
                    }
                else:
                    out = {
                        "name": root_path + "/" + path_info.path,
                        "size": 0,
                        "type": "directory",
                        "tree_id": path_info.tree_id,
                        "last_commit": path_info.last_commit,
                    }
                if not expand_info:
                    out = {k: out[k] for k in ["name", "size", "type"]}
        assert out is not None
        return out

    def exists(self, path, **kwargs):
        """
        Check if a file exists.

        For more details, refer to [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.exists).

        <Tip warning={true}>

            Note: When possible, use `HfApi.file_exists()` for better performance.

        </Tip>

        Args:
            path (`str`):
                Path to check.

        Returns:
            `bool`: True if file exists, False otherwise.
        """
        try:
            if kwargs.get("refresh", False):
                self.invalidate_cache(path)

            self.info(path, **{**kwargs, "expand_info": False})
            return True
        except:  # noqa: E722
            return False

    def isdir(self, path):
        """
        Check if a path is a directory.

        For more details, refer to [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.isdir).

        Args:
            path (`str`):
                Path to check.

        Returns:
            `bool`: True if path is a directory, False otherwise.
        """
        try:
            return self.info(path, expand_info=False)["type"] == "directory"
        except OSError:
            return False

    def isfile(self, path):
        """
        Check if a path is a file.

        For more details, refer to [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.isfile).

        Args:
            path (`str`):
                Path to check.

        Returns:
            `bool`: True if path is a file, False otherwise.
        """
        try:
            return self.info(path, expand_info=False)["type"] == "file"
        except:  # noqa: E722
            return False

    def url(self, path: str) -> str:
        """
        Get the HTTP URL of the given path.

        Args:
            path (`str`):
                Path to get URL for.

        Returns:
            `str`: HTTP URL to access the file or directory on the Hub.
        """
        resolved_path = self.resolve_path(path)
        url = hf_hub_url(
            resolved_path.repo_id,
            resolved_path.path_in_repo,
            repo_type=resolved_path.repo_type,
            revision=resolved_path.revision,
            endpoint=self.endpoint,
        )
        if self.isdir(path):
            url = url.replace("/resolve/", "/tree/", 1)
        return url

    def get_file(self, rpath, lpath, callback=_DEFAULT_CALLBACK, outfile=None, **kwargs) -> None:
        """
        Copy single remote file to local.

        <Tip warning={true}>

            Note: When possible, use `HfApi.hf_hub_download()` for better performance.

        </Tip>

        Args:
            rpath (`str`):
                Remote path to download from.
            lpath (`str`):
                Local path to download to.
            callback (`Callback`, *optional*):
                Optional callback to track download progress. Defaults to no callback.
            outfile (`IO`, *optional*):
                Optional file-like object to write to. If provided, `lpath` is ignored.

        """
        revision = kwargs.get("revision")
        unhandled_kwargs = set(kwargs.keys()) - {"revision"}
        if not isinstance(callback, (NoOpCallback, TqdmCallback)) or len(unhandled_kwargs) > 0:
            # for now, let's not handle custom callbacks
            # and let's not handle custom kwargs
            return super().get_file(rpath, lpath, callback=callback, outfile=outfile, **kwargs)

        # Taken from https://github.com/fsspec/filesystem_spec/blob/47b445ae4c284a82dd15e0287b1ffc410e8fc470/fsspec/spec.py#L883
        if isfilelike(lpath):
            outfile = lpath
        elif self.isdir(rpath):
            os.makedirs(lpath, exist_ok=True)
            return None

        if isinstance(lpath, (str, Path)):  # otherwise, let's assume it's a file-like object
            os.makedirs(os.path.dirname(lpath), exist_ok=True)

        # Open file if not already open
        close_file = False
        if outfile is None:
            outfile = open(lpath, "wb")
            close_file = True
        initial_pos = outfile.tell()

        # Custom implementation of `get_file` to use `http_get`.
        resolve_remote_path = self.resolve_path(rpath, revision=revision)
        expected_size = self.info(rpath, revision=revision)["size"]
        callback.set_size(expected_size)
        try:
            http_get(
                url=hf_hub_url(
                    repo_id=resolve_remote_path.repo_id,
                    revision=resolve_remote_path.revision,
                    filename=resolve_remote_path.path_in_repo,
                    repo_type=resolve_remote_path.repo_type,
                    endpoint=self.endpoint,
                ),
                temp_file=outfile,
                displayed_filename=rpath,
                expected_size=expected_size,
                resume_size=0,
                headers=self._api._build_hf_headers(),
                _tqdm_bar=callback.tqdm if isinstance(callback, TqdmCallback) else None,
            )
            outfile.seek(initial_pos)
        finally:
            # Close file only if we opened it ourselves
            if close_file:
                outfile.close()

    @property
    def transaction(self):
        """A context within which files are committed together upon exit

        Requires the file class to implement `.commit()` and `.discard()`
        for the normal and exception cases.
        """
        # Taken from https://github.com/fsspec/filesystem_spec/blob/3fbb6fee33b46cccb015607630843dea049d3243/fsspec/spec.py#L231
        # See https://github.com/huggingface/huggingface_hub/issues/1733
        raise NotImplementedError("Transactional commits are not supported.")

    def start_transaction(self):
        """Begin write transaction for deferring files, non-context version"""
        # Taken from https://github.com/fsspec/filesystem_spec/blob/3fbb6fee33b46cccb015607630843dea049d3243/fsspec/spec.py#L241
        # See https://github.com/huggingface/huggingface_hub/issues/1733
        raise NotImplementedError("Transactional commits are not supported.")


class HfFileSystemFile(fsspec.spec.AbstractBufferedFile):
    def __init__(self, fs: HfFileSystem, path: str, revision: Optional[str] = None, **kwargs):
        try:
            self.resolved_path = fs.resolve_path(path, revision=revision)
        except FileNotFoundError as e:
            if "w" in kwargs.get("mode", ""):
                raise FileNotFoundError(
                    f"{e}.\nMake sure the repository and revision exist before writing data."
                ) from e
            raise
        # avoid an unnecessary .info() call with expensive expand_info=True to instantiate .details
        if kwargs.get("mode", "rb") == "rb":
            self.details = fs.info(self.resolved_path.unresolve(), expand_info=False)
        super().__init__(fs, self.resolved_path.unresolve(), **kwargs)
        self.fs: HfFileSystem

    def __del__(self):
        if not hasattr(self, "resolved_path"):
            # Means that the constructor failed. Nothing to do.
            return
        return super().__del__()

    def _fetch_range(self, start: int, end: int) -> bytes:
        headers = {
            "range": f"bytes={start}-{end - 1}",
            **self.fs._api._build_hf_headers(),
        }
        url = hf_hub_url(
            repo_id=self.resolved_path.repo_id,
            revision=self.resolved_path.revision,
            filename=self.resolved_path.path_in_repo,
            repo_type=self.resolved_path.repo_type,
            endpoint=self.fs.endpoint,
        )
        r = http_backoff(
            "GET",
            url,
            headers=headers,
            retry_on_status_codes=(500, 502, 503, 504),
            timeout=constants.HF_HUB_DOWNLOAD_TIMEOUT,
        )
        hf_raise_for_status(r)
        return r.content

    def _initiate_upload(self) -> None:
        self.temp_file = tempfile.NamedTemporaryFile(prefix="hffs-", delete=False)

    def _upload_chunk(self, final: bool = False) -> None:
        self.buffer.seek(0)
        block = self.buffer.read()
        self.temp_file.write(block)
        if final:
            self.temp_file.close()
            self.fs._api.upload_file(
                path_or_fileobj=self.temp_file.name,
                path_in_repo=self.resolved_path.path_in_repo,
                repo_id=self.resolved_path.repo_id,
                token=self.fs.token,
                repo_type=self.resolved_path.repo_type,
                revision=self.resolved_path.revision,
                commit_message=self.kwargs.get("commit_message"),
                commit_description=self.kwargs.get("commit_description"),
            )
            os.remove(self.temp_file.name)
            self.fs.invalidate_cache(
                path=self.resolved_path.unresolve(),
            )

    def read(self, length=-1):
        """Read remote file.

        If `length` is not provided or is -1, the entire file is downloaded and read. On POSIX systems and if
        `hf_transfer` is not enabled, the file is loaded in memory directly. Otherwise, the file is downloaded to a
        temporary file and read from there.
        """
        if self.mode == "rb" and (length is None or length == -1) and self.loc == 0:
            with self.fs.open(self.path, "rb", block_size=0) as f:  # block_size=0 enables fast streaming
                out = f.read()
                self.loc += len(out)
                return out
        return super().read(length)

    def url(self) -> str:
        return self.fs.url(self.path)


class HfFileSystemStreamFile(fsspec.spec.AbstractBufferedFile):
    def __init__(
        self,
        fs: HfFileSystem,
        path: str,
        mode: str = "rb",
        revision: Optional[str] = None,
        block_size: int = 0,
        cache_type: str = "none",
        **kwargs,
    ):
        if block_size != 0:
            raise ValueError(f"HfFileSystemStreamFile only supports block_size=0 but got {block_size}")
        if cache_type != "none":
            raise ValueError(f"HfFileSystemStreamFile only supports cache_type='none' but got {cache_type}")
        if "w" in mode:
            raise ValueError(f"HfFileSystemStreamFile only supports reading but got mode='{mode}'")
        try:
            self.resolved_path = fs.resolve_path(path, revision=revision)
        except FileNotFoundError as e:
            if "w" in kwargs.get("mode", ""):
                raise FileNotFoundError(
                    f"{e}.\nMake sure the repository and revision exist before writing data."
                ) from e
        # avoid an unnecessary .info() call to instantiate .details
        self.details = {"name": self.resolved_path.unresolve(), "size": None}
        super().__init__(
            fs, self.resolved_path.unresolve(), mode=mode, block_size=block_size, cache_type=cache_type, **kwargs
        )
        self.response: Optional[Response] = None
        self.fs: HfFileSystem

    def seek(self, loc: int, whence: int = 0):
        if loc == 0 and whence == 1:
            return
        if loc == self.loc and whence == 0:
            return
        raise ValueError("Cannot seek streaming HF file")

    def read(self, length: int = -1):
        read_args = (length,) if length >= 0 else ()
        if self.response is None:
            url = hf_hub_url(
                repo_id=self.resolved_path.repo_id,
                revision=self.resolved_path.revision,
                filename=self.resolved_path.path_in_repo,
                repo_type=self.resolved_path.repo_type,
                endpoint=self.fs.endpoint,
            )
            self.response = http_backoff(
                "GET",
                url,
                headers=self.fs._api._build_hf_headers(),
                retry_on_status_codes=(500, 502, 503, 504),
                stream=True,
                timeout=constants.HF_HUB_DOWNLOAD_TIMEOUT,
            )
            hf_raise_for_status(self.response)
        try:
            out = self.response.raw.read(*read_args)
        except Exception:
            self.response.close()

            # Retry by recreating the connection
            url = hf_hub_url(
                repo_id=self.resolved_path.repo_id,
                revision=self.resolved_path.revision,
                filename=self.resolved_path.path_in_repo,
                repo_type=self.resolved_path.repo_type,
                endpoint=self.fs.endpoint,
            )
            self.response = http_backoff(
                "GET",
                url,
                headers={"Range": "bytes=%d-" % self.loc, **self.fs._api._build_hf_headers()},
                retry_on_status_codes=(500, 502, 503, 504),
                stream=True,
                timeout=constants.HF_HUB_DOWNLOAD_TIMEOUT,
            )
            hf_raise_for_status(self.response)
            try:
                out = self.response.raw.read(*read_args)
            except Exception:
                self.response.close()
                raise
        self.loc += len(out)
        return out

    def url(self) -> str:
        return self.fs.url(self.path)

    def __del__(self):
        if not hasattr(self, "resolved_path"):
            # Means that the constructor failed. Nothing to do.
            return
        return super().__del__()

    def __reduce__(self):
        return reopen, (self.fs, self.path, self.mode, self.blocksize, self.cache.name)


def safe_revision(revision: str) -> str:
    return revision if SPECIAL_REFS_REVISION_REGEX.match(revision) else safe_quote(revision)


def safe_quote(s: str) -> str:
    return quote(s, safe="")


def _raise_file_not_found(path: str, err: Optional[Exception]) -> NoReturn:
    msg = path
    if isinstance(err, RepositoryNotFoundError):
        msg = f"{path} (repository not found)"
    elif isinstance(err, RevisionNotFoundError):
        msg = f"{path} (revision not found)"
    elif isinstance(err, HFValidationError):
        msg = f"{path} (invalid repository id)"
    raise FileNotFoundError(msg) from err


def reopen(fs: HfFileSystem, path: str, mode: str, block_size: int, cache_type: str):
    return fs.open(path, mode=mode, block_size=block_size, cache_type=cache_type)