
# === NexusCore/tools\exports\export_20250803_114325\combined_111.py ===

# === NexusCore/openenv\Lib\site-packages\trio\testing\_raises_group.py ===
from __future__ import annotations

import re
import sys
from abc import ABC, abstractmethod
from re import Pattern
from textwrap import indent
from typing import (
    TYPE_CHECKING,
    Generic,
    Literal,
    cast,
    overload,
)

from trio._util import final

if TYPE_CHECKING:
    import builtins

    # sphinx will *only* work if we use types.TracebackType, and import
    # *inside* TYPE_CHECKING. No other combination works.....
    import types
    from collections.abc import Callable, Sequence

    from _pytest._code.code import ExceptionChainRepr, ReprExceptionInfo, Traceback
    from typing_extensions import TypeGuard, TypeVar

    # this conditional definition is because we want to allow a TypeVar default
    MatchE = TypeVar(
        "MatchE",
        bound=BaseException,
        default=BaseException,
        covariant=True,
    )
else:
    from typing import TypeVar

    MatchE = TypeVar("MatchE", bound=BaseException, covariant=True)

# RaisesGroup doesn't work with a default.
BaseExcT_co = TypeVar("BaseExcT_co", bound=BaseException, covariant=True)
BaseExcT_1 = TypeVar("BaseExcT_1", bound=BaseException)
BaseExcT_2 = TypeVar("BaseExcT_2", bound=BaseException)
ExcT_1 = TypeVar("ExcT_1", bound=Exception)
ExcT_2 = TypeVar("ExcT_2", bound=Exception)

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup


@final
class _ExceptionInfo(Generic[MatchE]):
    """Minimal re-implementation of pytest.ExceptionInfo, only used if pytest is not available. Supports a subset of its features necessary for functionality of :class:`trio.testing.RaisesGroup` and :class:`trio.testing.Matcher`."""

    _excinfo: tuple[type[MatchE], MatchE, types.TracebackType] | None

    def __init__(
        self,
        excinfo: tuple[type[MatchE], MatchE, types.TracebackType] | None,
    ) -> None:
        self._excinfo = excinfo

    def fill_unfilled(
        self,
        exc_info: tuple[type[MatchE], MatchE, types.TracebackType],
    ) -> None:
        """Fill an unfilled ExceptionInfo created with ``for_later()``."""
        assert self._excinfo is None, "ExceptionInfo was already filled"
        self._excinfo = exc_info

    @classmethod
    def for_later(cls) -> _ExceptionInfo[MatchE]:
        """Return an unfilled ExceptionInfo."""
        return cls(None)

    # Note, special cased in sphinx config, since "type" conflicts.
    @property
    def type(self) -> type[MatchE]:
        """The exception class."""
        assert (
            self._excinfo is not None
        ), ".type can only be used after the context manager exits"
        return self._excinfo[0]

    @property
    def value(self) -> MatchE:
        """The exception value."""
        assert (
            self._excinfo is not None
        ), ".value can only be used after the context manager exits"
        return self._excinfo[1]

    @property
    def tb(self) -> types.TracebackType:
        """The exception raw traceback."""
        assert (
            self._excinfo is not None
        ), ".tb can only be used after the context manager exits"
        return self._excinfo[2]

    def exconly(self, tryshort: bool = False) -> str:
        raise NotImplementedError(
            "This is a helper method only available if you use RaisesGroup with the pytest package installed",
        )

    def errisinstance(
        self,
        exc: builtins.type[BaseException] | tuple[builtins.type[BaseException], ...],
    ) -> bool:
        raise NotImplementedError(
            "This is a helper method only available if you use RaisesGroup with the pytest package installed",
        )

    def getrepr(
        self,
        showlocals: bool = False,
        style: str = "long",
        abspath: bool = False,
        tbfilter: bool | Callable[[_ExceptionInfo], Traceback] = True,
        funcargs: bool = False,
        truncate_locals: bool = True,
        chain: bool = True,
    ) -> ReprExceptionInfo | ExceptionChainRepr:
        raise NotImplementedError(
            "This is a helper method only available if you use RaisesGroup with the pytest package installed",
        )


# Type checkers are not able to do conditional types depending on installed packages, so
# we've added signatures for all helpers to _ExceptionInfo, and then always use that.
# If this ends up leading to problems, we can resort to always using _ExceptionInfo and
# users that want to use getrepr/errisinstance/exconly can write helpers on their own, or
# we reimplement them ourselves...or get this merged in upstream pytest.
if TYPE_CHECKING:
    ExceptionInfo = _ExceptionInfo

else:
    try:
        from pytest import ExceptionInfo  # noqa: PT013
    except ImportError:  # pragma: no cover
        ExceptionInfo = _ExceptionInfo


# copied from pytest.ExceptionInfo
def _stringify_exception(exc: BaseException) -> str:
    return "\n".join(
        [
            getattr(exc, "message", str(exc)),
            *getattr(exc, "__notes__", []),
        ],
    )


# String patterns default to including the unicode flag.
_REGEX_NO_FLAGS = re.compile(r"").flags


def _match_pattern(match: Pattern[str]) -> str | Pattern[str]:
    """helper function to remove redundant `re.compile` calls when printing regex"""
    return match.pattern if match.flags == _REGEX_NO_FLAGS else match


def repr_callable(fun: Callable[[BaseExcT_1], bool]) -> str:
    """Get the repr of a ``check`` parameter.

    Split out so it can be monkeypatched (e.g. by our hypothesis plugin)
    """
    return repr(fun)


def _exception_type_name(e: type[BaseException]) -> str:
    return repr(e.__name__)


def _check_raw_type(
    expected_type: type[BaseException] | None,
    exception: BaseException,
) -> str | None:
    if expected_type is None:
        return None

    if not isinstance(
        exception,
        expected_type,
    ):
        actual_type_str = _exception_type_name(type(exception))
        expected_type_str = _exception_type_name(expected_type)
        if isinstance(exception, BaseExceptionGroup) and not issubclass(
            expected_type, BaseExceptionGroup
        ):
            return f"Unexpected nested {actual_type_str}, expected {expected_type_str}"
        return f"{actual_type_str} is not of type {expected_type_str}"
    return None


class AbstractMatcher(ABC, Generic[BaseExcT_co]):
    """ABC with common functionality shared between Matcher and RaisesGroup"""

    def __init__(
        self,
        match: str | Pattern[str] | None,
        check: Callable[[BaseExcT_co], bool] | None,
    ) -> None:
        if isinstance(match, str):
            self.match: Pattern[str] | None = re.compile(match)
        else:
            self.match = match
        self.check = check
        self._fail_reason: str | None = None

        # used to suppress repeated printing of `repr(self.check)`
        self._nested: bool = False

    @property
    def fail_reason(self) -> str | None:
        """Set after a call to `matches` to give a human-readable
        reason for why the match failed.
        When used as a context manager the string will be given as the text of an
        `AssertionError`"""
        return self._fail_reason

    def _check_check(
        self: AbstractMatcher[BaseExcT_1],
        exception: BaseExcT_1,
    ) -> bool:
        if self.check is None:
            return True

        if self.check(exception):
            return True

        check_repr = "" if self._nested else " " + repr_callable(self.check)
        self._fail_reason = f"check{check_repr} did not return True"
        return False

    def _check_match(self, e: BaseException) -> bool:
        if self.match is None or re.search(
            self.match,
            stringified_exception := _stringify_exception(e),
        ):
            return True

        maybe_specify_type = (
            f" of {_exception_type_name(type(e))}"
            if isinstance(e, BaseExceptionGroup)
            else ""
        )
        self._fail_reason = f"Regex pattern {_match_pattern(self.match)!r} did not match {stringified_exception!r}{maybe_specify_type}"
        if _match_pattern(self.match) == stringified_exception:
            self._fail_reason += "\n  Did you mean to `re.escape()` the regex?"
        return False

    # TODO: when transitioning to pytest, harmonize Matcher and RaisesGroup
    # signatures. One names the parameter `exc_val` and the other `exception`
    @abstractmethod
    def matches(
        self: AbstractMatcher[BaseExcT_1], exc_val: BaseException
    ) -> TypeGuard[BaseExcT_1]:
        """Check if an exception matches the requirements of this AbstractMatcher.
        If it fails, `AbstractMatcher.fail_reason` should be set.
        """


@final
class Matcher(AbstractMatcher[MatchE]):
    """Helper class to be used together with RaisesGroups when you want to specify requirements on sub-exceptions. Only specifying the type is redundant, and it's also unnecessary when the type is a nested `RaisesGroup` since it supports the same arguments.
    The type is checked with `isinstance`, and does not need to be an exact match. If that is wanted you can use the ``check`` parameter.
    :meth:`Matcher.matches` can also be used standalone to check individual exceptions.

    Examples::

        with RaisesGroups(Matcher(ValueError, match="string")):
            ...
        with RaisesGroups(Matcher(check=lambda x: x.args == (3, "hello"))):
            ...
        with RaisesGroups(Matcher(check=lambda x: type(x) is ValueError)):
            ...

    Tip: if you install ``hypothesis`` and import it in ``conftest.py`` you will get
    readable ``repr``s of ``check`` callables in the output.
    """

    # At least one of the three parameters must be passed.
    @overload
    def __init__(
        self,
        exception_type: type[MatchE],
        match: str | Pattern[str] = ...,
        check: Callable[[MatchE], bool] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self: Matcher[BaseException],  # Give E a value.
        *,
        match: str | Pattern[str],
        # If exception_type is not provided, check() must do any typechecks itself.
        check: Callable[[BaseException], bool] = ...,
    ) -> None: ...

    @overload
    def __init__(self, *, check: Callable[[BaseException], bool]) -> None: ...

    def __init__(
        self,
        exception_type: type[MatchE] | None = None,
        match: str | Pattern[str] | None = None,
        check: Callable[[MatchE], bool] | None = None,
    ):
        super().__init__(match, check)
        if exception_type is None and match is None and check is None:
            raise ValueError("You must specify at least one parameter to match on.")
        if exception_type is not None and not issubclass(exception_type, BaseException):
            raise ValueError(
                f"exception_type {exception_type} must be a subclass of BaseException",
            )
        self.exception_type = exception_type

    def matches(
        self,
        exception: BaseException,
    ) -> TypeGuard[MatchE]:
        """Check if an exception matches the requirements of this Matcher.
        If it fails, `Matcher.fail_reason` will be set.

        Examples::

            assert Matcher(ValueError).matches(my_exception)
            # is equivalent to
            assert isinstance(my_exception, ValueError)

            # this can be useful when checking e.g. the ``__cause__`` of an exception.
            with pytest.raises(ValueError) as excinfo:
                ...
            assert Matcher(SyntaxError, match="foo").matches(excinfo.value.__cause__)
            # above line is equivalent to
            assert isinstance(excinfo.value.__cause__, SyntaxError)
            assert re.search("foo", str(excinfo.value.__cause__))

        """
        if not self._check_type(exception):
            return False

        if not self._check_match(exception):
            return False

        return self._check_check(exception)

    def __repr__(self) -> str:
        parameters = []
        if self.exception_type is not None:
            parameters.append(self.exception_type.__name__)
        if self.match is not None:
            # If no flags were specified, discard the redundant re.compile() here.
            parameters.append(
                f"match={_match_pattern(self.match)!r}",
            )
        if self.check is not None:
            parameters.append(f"check={repr_callable(self.check)}")
        return f'Matcher({", ".join(parameters)})'

    def _check_type(self, exception: BaseException) -> TypeGuard[MatchE]:
        self._fail_reason = _check_raw_type(self.exception_type, exception)
        return self._fail_reason is None


@final
class RaisesGroup(AbstractMatcher[BaseExceptionGroup[BaseExcT_co]]):
    """Contextmanager for checking for an expected `ExceptionGroup`.
    This works similar to ``pytest.raises``, and a version of it will hopefully be added upstream, after which this can be deprecated and removed. See https://github.com/pytest-dev/pytest/issues/11538


    The catching behaviour differs from :ref:`except* <except_star>` in multiple different ways, being much stricter by default. By using ``allow_unwrapped=True`` and ``flatten_subgroups=True`` you can match ``except*`` fully when expecting a single exception.

    #. All specified exceptions must be present, *and no others*.

       * If you expect a variable number of exceptions you need to use ``pytest.raises(ExceptionGroup)`` and manually check the contained exceptions. Consider making use of :func:`Matcher.matches`.

    #. It will only catch exceptions wrapped in an exceptiongroup by default.

       * With ``allow_unwrapped=True`` you can specify a single expected exception or `Matcher` and it will match the exception even if it is not inside an `ExceptionGroup`. If you expect one of several different exception types you need to use a `Matcher` object.

    #. By default it cares about the full structure with nested `ExceptionGroup`'s. You can specify nested `ExceptionGroup`'s by passing `RaisesGroup` objects as expected exceptions.

       * With ``flatten_subgroups=True`` it will "flatten" the raised `ExceptionGroup`, extracting all exceptions inside any nested :class:`ExceptionGroup`, before matching.

    It does not care about the order of the exceptions, so ``RaisesGroups(ValueError, TypeError)`` is equivalent to ``RaisesGroups(TypeError, ValueError)``.

    Examples::

        with RaisesGroups(ValueError):
            raise ExceptionGroup("", (ValueError(),))
        with RaisesGroups(ValueError, ValueError, Matcher(TypeError, match="expected int")):
            ...
        with RaisesGroups(KeyboardInterrupt, match="hello", check=lambda x: type(x) is BaseExceptionGroup):
            ...
        with RaisesGroups(RaisesGroups(ValueError)):
            raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))

        # flatten_subgroups
        with RaisesGroups(ValueError, flatten_subgroups=True):
            raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))

        # allow_unwrapped
        with RaisesGroups(ValueError, allow_unwrapped=True):
            raise ValueError


    `RaisesGroup.matches` can also be used directly to check a standalone exception group.


    The matching algorithm is greedy, which means cases such as this may fail::

        with RaisesGroups(ValueError, Matcher(ValueError, match="hello")):
            raise ExceptionGroup("", (ValueError("hello"), ValueError("goodbye")))

    even though it generally does not care about the order of the exceptions in the group.
    To avoid the above you should specify the first ValueError with a Matcher as well.

    Tip: if you install ``hypothesis`` and import it in ``conftest.py`` you will get
    readable ``repr``s of ``check`` callables in the output.
    """

    # allow_unwrapped=True requires: singular exception, exception not being
    # RaisesGroup instance, match is None, check is None
    @overload
    def __init__(
        self,
        exception: type[BaseExcT_co] | Matcher[BaseExcT_co],
        *,
        allow_unwrapped: Literal[True],
        flatten_subgroups: bool = False,
    ) -> None: ...

    # flatten_subgroups = True also requires no nested RaisesGroup
    @overload
    def __init__(
        self,
        exception: type[BaseExcT_co] | Matcher[BaseExcT_co],
        *other_exceptions: type[BaseExcT_co] | Matcher[BaseExcT_co],
        flatten_subgroups: Literal[True],
        match: str | Pattern[str] | None = None,
        check: Callable[[BaseExceptionGroup[BaseExcT_co]], bool] | None = None,
    ) -> None: ...

    # simplify the typevars if possible (the following 3 are equivalent but go simpler->complicated)
    # ... the first handles RaisesGroup[ValueError], the second RaisesGroup[ExceptionGroup[ValueError]],
    #     the third RaisesGroup[ValueError | ExceptionGroup[ValueError]].
    # ... otherwise, we will get results like RaisesGroup[ValueError | ExceptionGroup[Never]] (I think)
    #     (technically correct but misleading)
    @overload
    def __init__(
        self: RaisesGroup[ExcT_1],
        exception: type[ExcT_1] | Matcher[ExcT_1],
        *other_exceptions: type[ExcT_1] | Matcher[ExcT_1],
        match: str | Pattern[str] | None = None,
        check: Callable[[ExceptionGroup[ExcT_1]], bool] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self: RaisesGroup[ExceptionGroup[ExcT_2]],
        exception: RaisesGroup[ExcT_2],
        *other_exceptions: RaisesGroup[ExcT_2],
        match: str | Pattern[str] | None = None,
        check: Callable[[ExceptionGroup[ExceptionGroup[ExcT_2]]], bool] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self: RaisesGroup[ExcT_1 | ExceptionGroup[ExcT_2]],
        exception: type[ExcT_1] | Matcher[ExcT_1] | RaisesGroup[ExcT_2],
        *other_exceptions: type[ExcT_1] | Matcher[ExcT_1] | RaisesGroup[ExcT_2],
        match: str | Pattern[str] | None = None,
        check: (
            Callable[[ExceptionGroup[ExcT_1 | ExceptionGroup[ExcT_2]]], bool] | None
        ) = None,
    ) -> None: ...

    # same as the above 3 but handling BaseException
    @overload
    def __init__(
        self: RaisesGroup[BaseExcT_1],
        exception: type[BaseExcT_1] | Matcher[BaseExcT_1],
        *other_exceptions: type[BaseExcT_1] | Matcher[BaseExcT_1],
        match: str | Pattern[str] | None = None,
        check: Callable[[BaseExceptionGroup[BaseExcT_1]], bool] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self: RaisesGroup[BaseExceptionGroup[BaseExcT_2]],
        exception: RaisesGroup[BaseExcT_2],
        *other_exceptions: RaisesGroup[BaseExcT_2],
        match: str | Pattern[str] | None = None,
        check: (
            Callable[[BaseExceptionGroup[BaseExceptionGroup[BaseExcT_2]]], bool] | None
        ) = None,
    ) -> None: ...

    @overload
    def __init__(
        self: RaisesGroup[BaseExcT_1 | BaseExceptionGroup[BaseExcT_2]],
        exception: type[BaseExcT_1] | Matcher[BaseExcT_1] | RaisesGroup[BaseExcT_2],
        *other_exceptions: type[BaseExcT_1]
        | Matcher[BaseExcT_1]
        | RaisesGroup[BaseExcT_2],
        match: str | Pattern[str] | None = None,
        check: (
            Callable[
                [BaseExceptionGroup[BaseExcT_1 | BaseExceptionGroup[BaseExcT_2]]],
                bool,
            ]
            | None
        ) = None,
    ) -> None: ...

    def __init__(
        self: RaisesGroup[ExcT_1 | BaseExcT_1 | BaseExceptionGroup[BaseExcT_2]],
        exception: type[BaseExcT_1] | Matcher[BaseExcT_1] | RaisesGroup[BaseExcT_2],
        *other_exceptions: type[BaseExcT_1]
        | Matcher[BaseExcT_1]
        | RaisesGroup[BaseExcT_2],
        allow_unwrapped: bool = False,
        flatten_subgroups: bool = False,
        match: str | Pattern[str] | None = None,
        check: (
            Callable[[BaseExceptionGroup[BaseExcT_1]], bool]
            | Callable[[ExceptionGroup[ExcT_1]], bool]
            | None
        ) = None,
    ):
        # The type hint on the `self` and `check` parameters uses different formats
        # that are *very* hard to reconcile while adhering to the overloads, so we cast
        # it to avoid an error when passing it to super().__init__
        check = cast(
            "Callable[["
            "BaseExceptionGroup[ExcT_1|BaseExcT_1|BaseExceptionGroup[BaseExcT_2]]"
            "], bool]",
            check,
        )
        super().__init__(match, check)
        self.expected_exceptions: tuple[
            type[BaseExcT_co] | Matcher[BaseExcT_co] | RaisesGroup[BaseException], ...
        ] = (
            exception,
            *other_exceptions,
        )
        self.allow_unwrapped = allow_unwrapped
        self.flatten_subgroups: bool = flatten_subgroups
        self.is_baseexceptiongroup: bool = False

        if allow_unwrapped and other_exceptions:
            raise ValueError(
                "You cannot specify multiple exceptions with `allow_unwrapped=True.`"
                " If you want to match one of multiple possible exceptions you should"
                " use a `Matcher`."
                " E.g. `Matcher(check=lambda e: isinstance(e, (...)))`",
            )
        if allow_unwrapped and isinstance(exception, RaisesGroup):
            raise ValueError(
                "`allow_unwrapped=True` has no effect when expecting a `RaisesGroup`."
                " You might want it in the expected `RaisesGroup`, or"
                " `flatten_subgroups=True` if you don't care about the structure.",
            )
        if allow_unwrapped and (match is not None or check is not None):
            raise ValueError(
                "`allow_unwrapped=True` bypasses the `match` and `check` parameters"
                " if the exception is unwrapped. If you intended to match/check the"
                " exception you should use a `Matcher` object. If you want to match/check"
                " the exceptiongroup when the exception *is* wrapped you need to"
                " do e.g. `if isinstance(exc.value, ExceptionGroup):"
                " assert RaisesGroup(...).matches(exc.value)` afterwards.",
            )

        # verify `expected_exceptions` and set `self.is_baseexceptiongroup`
        for exc in self.expected_exceptions:
            if isinstance(exc, RaisesGroup):
                if self.flatten_subgroups:
                    raise ValueError(
                        "You cannot specify a nested structure inside a RaisesGroup with"
                        " `flatten_subgroups=True`. The parameter will flatten subgroups"
                        " in the raised exceptiongroup before matching, which would never"
                        " match a nested structure.",
                    )
                self.is_baseexceptiongroup |= exc.is_baseexceptiongroup
                exc._nested = True
            elif isinstance(exc, Matcher):
                if exc.exception_type is not None:
                    # Matcher __init__ assures it's a subclass of BaseException
                    self.is_baseexceptiongroup |= not issubclass(
                        exc.exception_type,
                        Exception,
                    )
                exc._nested = True
            elif isinstance(exc, type) and issubclass(exc, BaseException):
                self.is_baseexceptiongroup |= not issubclass(exc, Exception)
            else:
                raise ValueError(
                    f'Invalid argument "{exc!r}" must be exception type, Matcher, or'
                    " RaisesGroup.",
                )

    @overload
    def __enter__(
        self: RaisesGroup[ExcT_1],
    ) -> ExceptionInfo[ExceptionGroup[ExcT_1]]: ...
    @overload
    def __enter__(
        self: RaisesGroup[BaseExcT_1],
    ) -> ExceptionInfo[BaseExceptionGroup[BaseExcT_1]]: ...

    def __enter__(self) -> ExceptionInfo[BaseExceptionGroup[BaseException]]:
        self.excinfo: ExceptionInfo[BaseExceptionGroup[BaseExcT_co]] = (
            ExceptionInfo.for_later()
        )
        return self.excinfo

    def __repr__(self) -> str:
        parameters = [
            e.__name__ if isinstance(e, type) else repr(e)
            for e in self.expected_exceptions
        ]
        if self.allow_unwrapped:
            parameters.append(f"allow_unwrapped={self.allow_unwrapped}")
        if self.flatten_subgroups:
            parameters.append(f"flatten_subgroups={self.flatten_subgroups}")
        if self.match is not None:
            # If no flags were specified, discard the redundant re.compile() here.
            parameters.append(f"match={_match_pattern(self.match)!r}")
        if self.check is not None:
            parameters.append(f"check={repr_callable(self.check)}")
        return f"RaisesGroup({', '.join(parameters)})"

    def _unroll_exceptions(
        self,
        exceptions: Sequence[BaseException],
    ) -> Sequence[BaseException]:
        """Used if `flatten_subgroups=True`."""
        res: list[BaseException] = []
        for exc in exceptions:
            if isinstance(exc, BaseExceptionGroup):
                res.extend(self._unroll_exceptions(exc.exceptions))

            else:
                res.append(exc)
        return res

    @overload
    def matches(
        self: RaisesGroup[ExcT_1],
        exc_val: BaseException | None,
    ) -> TypeGuard[ExceptionGroup[ExcT_1]]: ...
    @overload
    def matches(
        self: RaisesGroup[BaseExcT_1],
        exc_val: BaseException | None,
    ) -> TypeGuard[BaseExceptionGroup[BaseExcT_1]]: ...

    def matches(
        self,
        exc_val: BaseException | None,
    ) -> TypeGuard[BaseExceptionGroup[BaseExcT_co]]:
        """Check if an exception matches the requirements of this RaisesGroup.
        If it fails, `RaisesGroup.fail_reason` will be set.

        Example::

            with pytest.raises(TypeError) as excinfo:
                ...
            assert RaisesGroups(ValueError).matches(excinfo.value.__cause__)
            # the above line is equivalent to
            myexc = excinfo.value.__cause
            assert isinstance(myexc, BaseExceptionGroup)
            assert len(myexc.exceptions) == 1
            assert isinstance(myexc.exceptions[0], ValueError)
        """
        self._fail_reason = None
        if exc_val is None:
            self._fail_reason = "exception is None"
            return False
        if not isinstance(exc_val, BaseExceptionGroup):
            # we opt to only print type of the exception here, as the repr would
            # likely be quite long
            not_group_msg = f"{type(exc_val).__name__!r} is not an exception group"
            if len(self.expected_exceptions) > 1:
                self._fail_reason = not_group_msg
                return False
            # if we have 1 expected exception, check if it would work even if
            # allow_unwrapped is not set
            res = self._check_expected(self.expected_exceptions[0], exc_val)
            if res is None and self.allow_unwrapped:
                return True

            if res is None:
                self._fail_reason = (
                    f"{not_group_msg}, but would match with `allow_unwrapped=True`"
                )
            elif self.allow_unwrapped:
                self._fail_reason = res
            else:
                self._fail_reason = not_group_msg
            return False

        actual_exceptions: Sequence[BaseException] = exc_val.exceptions
        if self.flatten_subgroups:
            actual_exceptions = self._unroll_exceptions(actual_exceptions)

        if not self._check_match(exc_val):
            old_reason = self._fail_reason
            if (
                len(actual_exceptions) == len(self.expected_exceptions) == 1
                and isinstance(expected := self.expected_exceptions[0], type)
                and isinstance(actual := actual_exceptions[0], expected)
                and self._check_match(actual)
            ):
                assert self.match is not None, "can't be None if _check_match failed"
                assert self._fail_reason is old_reason is not None
                self._fail_reason += f", but matched the expected {self._repr_expected(expected)}. You might want RaisesGroup(Matcher({expected.__name__}, match={_match_pattern(self.match)!r}))"
            else:
                self._fail_reason = old_reason
            return False

        # do the full check on expected exceptions
        if not self._check_exceptions(
            exc_val,
            actual_exceptions,
        ):
            assert self._fail_reason is not None
            old_reason = self._fail_reason
            # if we're not expecting a nested structure, and there is one, do a second
            # pass where we try flattening it
            if (
                not self.flatten_subgroups
                and not any(
                    isinstance(e, RaisesGroup) for e in self.expected_exceptions
                )
                and any(isinstance(e, BaseExceptionGroup) for e in actual_exceptions)
                and self._check_exceptions(
                    exc_val,
                    self._unroll_exceptions(exc_val.exceptions),
                )
            ):
                # only indent if it's a single-line reason. In a multi-line there's already
                # indented lines that this does not belong to.
                indent = "  " if "\n" not in self._fail_reason else ""
                self._fail_reason = (
                    old_reason
                    + f"\n{indent}Did you mean to use `flatten_subgroups=True`?"
                )
            else:
                self._fail_reason = old_reason
            return False

        # Only run `self.check` once we know `exc_val` is of the correct type.
        # TODO: if this fails, we should say the *group* did not match
        return self._check_check(exc_val)

    @staticmethod
    def _check_expected(
        expected_type: (
            type[BaseException] | Matcher[BaseException] | RaisesGroup[BaseException]
        ),
        exception: BaseException,
    ) -> str | None:
        """Helper method for `RaisesGroup.matches` and `RaisesGroup._check_exceptions`
        to check one of potentially several expected exceptions."""
        if isinstance(expected_type, type):
            return _check_raw_type(expected_type, exception)
        res = expected_type.matches(exception)
        if res:
            return None
        assert expected_type.fail_reason is not None
        if expected_type.fail_reason.startswith("\n"):
            return f"\n{expected_type!r}: {indent(expected_type.fail_reason, '  ')}"
        return f"{expected_type!r}: {expected_type.fail_reason}"

    @staticmethod
    def _repr_expected(e: type[BaseException] | AbstractMatcher[BaseException]) -> str:
        """Get the repr of an expected type/Matcher/RaisesGroup, but we only want
        the name if it's a type"""
        if isinstance(e, type):
            return _exception_type_name(e)
        return repr(e)

    @overload
    def _check_exceptions(
        self: RaisesGroup[ExcT_1],
        _exc_val: Exception,
        actual_exceptions: Sequence[Exception],
    ) -> TypeGuard[ExceptionGroup[ExcT_1]]: ...
    @overload
    def _check_exceptions(
        self: RaisesGroup[BaseExcT_1],
        _exc_val: BaseException,
        actual_exceptions: Sequence[BaseException],
    ) -> TypeGuard[BaseExceptionGroup[BaseExcT_1]]: ...

    def _check_exceptions(
        self,
        _exc_val: BaseException,
        actual_exceptions: Sequence[BaseException],
    ) -> TypeGuard[BaseExceptionGroup[BaseExcT_co]]:
        """helper method for RaisesGroup.matches that attempts to pair up expected and actual exceptions"""
        # full table with all results
        results = ResultHolder(self.expected_exceptions, actual_exceptions)

        # (indexes of) raised exceptions that haven't (yet) found an expected
        remaining_actual = list(range(len(actual_exceptions)))
        # (indexes of) expected exceptions that haven't found a matching raised
        failed_expected: list[int] = []
        # successful greedy matches
        matches: dict[int, int] = {}

        # loop over expected exceptions first to get a more predictable result
        for i_exp, expected in enumerate(self.expected_exceptions):
            for i_rem in remaining_actual:
                res = self._check_expected(expected, actual_exceptions[i_rem])
                results.set_result(i_exp, i_rem, res)
                if res is None:
                    remaining_actual.remove(i_rem)
                    matches[i_exp] = i_rem
                    break
            else:
                failed_expected.append(i_exp)

        # All exceptions matched up successfully
        if not remaining_actual and not failed_expected:
            return True

        # in case of a single expected and single raised we simplify the output
        if 1 == len(actual_exceptions) == len(self.expected_exceptions):
            assert not matches
            self._fail_reason = res
            return False

        # The test case is failing, so we can do a slow and exhaustive check to find
        # duplicate matches etc that will be helpful in debugging
        for i_exp, expected in enumerate(self.expected_exceptions):
            for i_actual, actual in enumerate(actual_exceptions):
                if results.has_result(i_exp, i_actual):
                    continue
                results.set_result(
                    i_exp, i_actual, self._check_expected(expected, actual)
                )

        successful_str = (
            f"{len(matches)} matched exception{'s' if len(matches) > 1 else ''}. "
            if matches
            else ""
        )

        # all expected were found
        if not failed_expected and results.no_match_for_actual(remaining_actual):
            self._fail_reason = f"{successful_str}Unexpected exception(s): {[actual_exceptions[i] for i in remaining_actual]!r}"
            return False
        # all raised exceptions were expected
        if not remaining_actual and results.no_match_for_expected(failed_expected):
            self._fail_reason = f"{successful_str}Too few exceptions raised, found no match for: [{', '.join(self._repr_expected(self.expected_exceptions[i]) for i in failed_expected)}]"
            return False

        # if there's only one remaining and one failed, and the unmatched didn't match anything else,
        # we elect to only print why the remaining and the failed didn't match.
        if (
            1 == len(remaining_actual) == len(failed_expected)
            and results.no_match_for_actual(remaining_actual)
            and results.no_match_for_expected(failed_expected)
        ):
            self._fail_reason = f"{successful_str}{results.get_result(failed_expected[0], remaining_actual[0])}"
            return False

        # there's both expected and raised exceptions without matches
        s = ""
        if matches:
            s += f"\n{successful_str}"
        indent_1 = " " * 2
        indent_2 = " " * 4

        if not remaining_actual:
            s += "\nToo few exceptions raised!"
        elif not failed_expected:
            s += "\nUnexpected exception(s)!"

        if failed_expected:
            s += "\nThe following expected exceptions did not find a match:"
            rev_matches = {v: k for k, v in matches.items()}
        for i_failed in failed_expected:
            s += (
                f"\n{indent_1}{self._repr_expected(self.expected_exceptions[i_failed])}"
            )
            for i_actual, actual in enumerate(actual_exceptions):
                if results.get_result(i_exp, i_actual) is None:
                    # we print full repr of match target
                    s += f"\n{indent_2}It matches {actual!r} which was paired with {self._repr_expected(self.expected_exceptions[rev_matches[i_actual]])}"

        if remaining_actual:
            s += "\nThe following raised exceptions did not find a match"
        for i_actual in remaining_actual:
            s += f"\n{indent_1}{actual_exceptions[i_actual]!r}:"
            for i_exp, expected in enumerate(self.expected_exceptions):
                res = results.get_result(i_exp, i_actual)
                if i_exp in failed_expected:
                    assert res is not None
                    if res[0] != "\n":
                        s += "\n"
                    s += indent(res, indent_2)
                if res is None:
                    # we print full repr of match target
                    s += f"\n{indent_2}It matches {self._repr_expected(expected)} which was paired with {actual_exceptions[matches[i_exp]]!r}"

        if len(self.expected_exceptions) == len(actual_exceptions) and possible_match(
            results
        ):
            s += "\nThere exist a possible match when attempting an exhaustive check, but RaisesGroup uses a greedy algorithm. Please make your expected exceptions more stringent with `Matcher` etc so the greedy algorithm can function."
        self._fail_reason = s
        return False

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool:
        __tracebackhide__ = True
        assert (
            exc_type is not None
        ), f"DID NOT RAISE any exception, expected {self.expected_type()}"
        assert (
            self.excinfo is not None
        ), "Internal error - should have been constructed in __enter__"

        group_str = (
            "(group)"
            if self.allow_unwrapped and not issubclass(exc_type, BaseExceptionGroup)
            else "group"
        )

        assert self.matches(
            exc_val,
        ), f"Raised exception {group_str} did not match: {self._fail_reason}"

        # Cast to narrow the exception type now that it's verified.
        exc_info = cast(
            "tuple[type[BaseExceptionGroup[BaseExcT_co]], BaseExceptionGroup[BaseExcT_co], types.TracebackType]",
            (exc_type, exc_val, exc_tb),
        )
        self.excinfo.fill_unfilled(exc_info)
        return True

    def expected_type(self) -> str:
        subexcs = []
        for e in self.expected_exceptions:
            if isinstance(e, Matcher):
                subexcs.append(str(e))
            elif isinstance(e, RaisesGroup):
                subexcs.append(e.expected_type())
            elif isinstance(e, type):
                subexcs.append(e.__name__)
            else:  # pragma: no cover
                raise AssertionError("unknown type")
        group_type = "Base" if self.is_baseexceptiongroup else ""
        return f"{group_type}ExceptionGroup({', '.join(subexcs)})"


@final
class NotChecked: ...


class ResultHolder:
    def __init__(
        self,
        expected_exceptions: tuple[
            type[BaseException] | AbstractMatcher[BaseException], ...
        ],
        actual_exceptions: Sequence[BaseException],
    ) -> None:
        self.results: list[list[str | type[NotChecked] | None]] = [
            [NotChecked for _ in expected_exceptions] for _ in actual_exceptions
        ]

    def set_result(self, expected: int, actual: int, result: str | None) -> None:
        self.results[actual][expected] = result

    def get_result(self, expected: int, actual: int) -> str | None:
        res = self.results[actual][expected]
        # mypy doesn't support `assert res is not NotChecked`
        assert not isinstance(res, type)
        return res

    def has_result(self, expected: int, actual: int) -> bool:
        return self.results[actual][expected] is not NotChecked

    def no_match_for_expected(self, expected: list[int]) -> bool:
        for i in expected:
            for actual_results in self.results:
                assert actual_results[i] is not NotChecked
                if actual_results[i] is None:
                    return False
        return True

    def no_match_for_actual(self, actual: list[int]) -> bool:
        for i in actual:
            for res in self.results[i]:
                assert res is not NotChecked
                if res is None:
                    return False
        return True


def possible_match(results: ResultHolder, used: set[int] | None = None) -> bool:
    if used is None:
        used = set()
    curr_row = len(used)
    if curr_row == len(results.results):
        return True

    for i, val in enumerate(results.results[curr_row]):
        if val is None and i not in used and possible_match(results, used | {i}):
            return True
    return False

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\packaging\specifiers.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""
.. testsetup::

    from pip._vendor.packaging.specifiers import Specifier, SpecifierSet, InvalidSpecifier
    from pip._vendor.packaging.version import Version
"""

from __future__ import annotations

import abc
import itertools
import re
from typing import Callable, Iterable, Iterator, TypeVar, Union

from .utils import canonicalize_version
from .version import Version

UnparsedVersion = Union[Version, str]
UnparsedVersionVar = TypeVar("UnparsedVersionVar", bound=UnparsedVersion)
CallableOperator = Callable[[Version, str], bool]


def _coerce_version(version: UnparsedVersion) -> Version:
    if not isinstance(version, Version):
        version = Version(version)
    return version


class InvalidSpecifier(ValueError):
    """
    Raised when attempting to create a :class:`Specifier` with a specifier
    string that is invalid.

    >>> Specifier("lolwat")
    Traceback (most recent call last):
        ...
    packaging.specifiers.InvalidSpecifier: Invalid specifier: 'lolwat'
    """


class BaseSpecifier(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self) -> str:
        """
        Returns the str representation of this Specifier-like object. This
        should be representative of the Specifier itself.
        """

    @abc.abstractmethod
    def __hash__(self) -> int:
        """
        Returns a hash value for this Specifier-like object.
        """

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        """
        Returns a boolean representing whether or not the two Specifier-like
        objects are equal.

        :param other: The other object to check against.
        """

    @property
    @abc.abstractmethod
    def prereleases(self) -> bool | None:
        """Whether or not pre-releases as a whole are allowed.

        This can be set to either ``True`` or ``False`` to explicitly enable or disable
        prereleases or it can be set to ``None`` (the default) to use default semantics.
        """

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        """Setter for :attr:`prereleases`.

        :param value: The value to set.
        """

    @abc.abstractmethod
    def contains(self, item: str, prereleases: bool | None = None) -> bool:
        """
        Determines if the given item is contained within this specifier.
        """

    @abc.abstractmethod
    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """
        Takes an iterable of items and filters them so that only items which
        are contained within this specifier are allowed in it.
        """


class Specifier(BaseSpecifier):
    """This class abstracts handling of version specifiers.

    .. tip::

        It is generally not required to instantiate this manually. You should instead
        prefer to work with :class:`SpecifierSet` instead, which can parse
        comma-separated version specifiers (which is what package metadata contains).
    """

    _operator_regex_str = r"""
        (?P<operator>(~=|==|!=|<=|>=|<|>|===))
        """
    _version_regex_str = r"""
        (?P<version>
            (?:
                # The identity operators allow for an escape hatch that will
                # do an exact string match of the version you wish to install.
                # This will not be parsed by PEP 440 and we cannot determine
                # any semantic meaning from it. This operator is discouraged
                # but included entirely as an escape hatch.
                (?<====)  # Only match for the identity operator
                \s*
                [^\s;)]*  # The arbitrary version can be just about anything,
                          # we match everything except for whitespace, a
                          # semi-colon for marker support, and a closing paren
                          # since versions can be enclosed in them.
            )
            |
            (?:
                # The (non)equality operators allow for wild card and local
                # versions to be specified so we have to define these two
                # operators separately to enable that.
                (?<===|!=)            # Only match for equals and not equals

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)*   # release

                # You cannot use a wild card and a pre-release, post-release, a dev or
                # local version together so group them with a | and make them optional.
                (?:
                    \.\*  # Wild card syntax of .*
                    |
                    (?:                                  # pre release
                        [-_\.]?
                        (alpha|beta|preview|pre|a|b|c|rc)
                        [-_\.]?
                        [0-9]*
                    )?
                    (?:                                  # post release
                        (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                    )?
                    (?:[-_\.]?dev[-_\.]?[0-9]*)?         # dev release
                    (?:\+[a-z0-9]+(?:[-_\.][a-z0-9]+)*)? # local
                )?
            )
            |
            (?:
                # The compatible operator requires at least two digits in the
                # release segment.
                (?<=~=)               # Only match for the compatible operator

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)+   # release  (We have a + instead of a *)
                (?:                   # pre release
                    [-_\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                )?
                (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
            )
            |
            (?:
                # All other operators only allow a sub set of what the
                # (non)equality operators do. Specifically they do not allow
                # local versions to be specified nor do they allow the prefix
                # matching wild cards.
                (?<!==|!=|~=)         # We have special cases for these
                                      # operators so we want to make sure they
                                      # don't match here.

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)*   # release
                (?:                   # pre release
                    [-_\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                )?
                (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
            )
        )
        """

    _regex = re.compile(
        r"^\s*" + _operator_regex_str + _version_regex_str + r"\s*$",
        re.VERBOSE | re.IGNORECASE,
    )

    _operators = {
        "~=": "compatible",
        "==": "equal",
        "!=": "not_equal",
        "<=": "less_than_equal",
        ">=": "greater_than_equal",
        "<": "less_than",
        ">": "greater_than",
        "===": "arbitrary",
    }

    def __init__(self, spec: str = "", prereleases: bool | None = None) -> None:
        """Initialize a Specifier instance.

        :param spec:
            The string representation of a specifier which will be parsed and
            normalized before use.
        :param prereleases:
            This tells the specifier if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.
        :raises InvalidSpecifier:
            If the given specifier is invalid (i.e. bad syntax).
        """
        match = self._regex.search(spec)
        if not match:
            raise InvalidSpecifier(f"Invalid specifier: {spec!r}")

        self._spec: tuple[str, str] = (
            match.group("operator").strip(),
            match.group("version").strip(),
        )

        # Store whether or not this Specifier should accept prereleases
        self._prereleases = prereleases

    # https://github.com/python/mypy/pull/13475#pullrequestreview-1079784515
    @property  # type: ignore[override]
    def prereleases(self) -> bool:
        # If there is an explicit prereleases set for this, then we'll just
        # blindly use that.
        if self._prereleases is not None:
            return self._prereleases

        # Look at all of our specifiers and determine if they are inclusive
        # operators, and if they are if they are including an explicit
        # prerelease.
        operator, version = self._spec
        if operator in ["==", ">=", "<=", "~=", "===", ">", "<"]:
            # The == specifier can include a trailing .*, if it does we
            # want to remove before parsing.
            if operator == "==" and version.endswith(".*"):
                version = version[:-2]

            # Parse the version, and if it is a pre-release than this
            # specifier allows pre-releases.
            if Version(version).is_prerelease:
                return True

        return False

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    @property
    def operator(self) -> str:
        """The operator of this specifier.

        >>> Specifier("==1.2.3").operator
        '=='
        """
        return self._spec[0]

    @property
    def version(self) -> str:
        """The version of this specifier.

        >>> Specifier("==1.2.3").version
        '1.2.3'
        """
        return self._spec[1]

    def __repr__(self) -> str:
        """A representation of the Specifier that shows all internal state.

        >>> Specifier('>=1.0.0')
        <Specifier('>=1.0.0')>
        >>> Specifier('>=1.0.0', prereleases=False)
        <Specifier('>=1.0.0', prereleases=False)>
        >>> Specifier('>=1.0.0', prereleases=True)
        <Specifier('>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<{self.__class__.__name__}({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the Specifier that can be round-tripped.

        >>> str(Specifier('>=1.0.0'))
        '>=1.0.0'
        >>> str(Specifier('>=1.0.0', prereleases=False))
        '>=1.0.0'
        """
        return "{}{}".format(*self._spec)

    @property
    def _canonical_spec(self) -> tuple[str, str]:
        canonical_version = canonicalize_version(
            self._spec[1],
            strip_trailing_zero=(self._spec[0] != "~="),
        )
        return self._spec[0], canonical_version

    def __hash__(self) -> int:
        return hash(self._canonical_spec)

    def __eq__(self, other: object) -> bool:
        """Whether or not the two Specifier-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> Specifier("==1.2.3") == Specifier("== 1.2.3.0")
        True
        >>> (Specifier("==1.2.3", prereleases=False) ==
        ...  Specifier("==1.2.3", prereleases=True))
        True
        >>> Specifier("==1.2.3") == "==1.2.3"
        True
        >>> Specifier("==1.2.3") == Specifier("==1.2.4")
        False
        >>> Specifier("==1.2.3") == Specifier("~=1.2.3")
        False
        """
        if isinstance(other, str):
            try:
                other = self.__class__(str(other))
            except InvalidSpecifier:
                return NotImplemented
        elif not isinstance(other, self.__class__):
            return NotImplemented

        return self._canonical_spec == other._canonical_spec

    def _get_operator(self, op: str) -> CallableOperator:
        operator_callable: CallableOperator = getattr(
            self, f"_compare_{self._operators[op]}"
        )
        return operator_callable

    def _compare_compatible(self, prospective: Version, spec: str) -> bool:
        # Compatible releases have an equivalent combination of >= and ==. That
        # is that ~=2.2 is equivalent to >=2.2,==2.*. This allows us to
        # implement this in terms of the other specifiers instead of
        # implementing it ourselves. The only thing we need to do is construct
        # the other specifiers.

        # We want everything but the last item in the version, but we want to
        # ignore suffix segments.
        prefix = _version_join(
            list(itertools.takewhile(_is_not_suffix, _version_split(spec)))[:-1]
        )

        # Add the prefix notation to the end of our string
        prefix += ".*"

        return self._get_operator(">=")(prospective, spec) and self._get_operator("==")(
            prospective, prefix
        )

    def _compare_equal(self, prospective: Version, spec: str) -> bool:
        # We need special logic to handle prefix matching
        if spec.endswith(".*"):
            # In the case of prefix matching we want to ignore local segment.
            normalized_prospective = canonicalize_version(
                prospective.public, strip_trailing_zero=False
            )
            # Get the normalized version string ignoring the trailing .*
            normalized_spec = canonicalize_version(spec[:-2], strip_trailing_zero=False)
            # Split the spec out by bangs and dots, and pretend that there is
            # an implicit dot in between a release segment and a pre-release segment.
            split_spec = _version_split(normalized_spec)

            # Split the prospective version out by bangs and dots, and pretend
            # that there is an implicit dot in between a release segment and
            # a pre-release segment.
            split_prospective = _version_split(normalized_prospective)

            # 0-pad the prospective version before shortening it to get the correct
            # shortened version.
            padded_prospective, _ = _pad_version(split_prospective, split_spec)

            # Shorten the prospective version to be the same length as the spec
            # so that we can determine if the specifier is a prefix of the
            # prospective version or not.
            shortened_prospective = padded_prospective[: len(split_spec)]

            return shortened_prospective == split_spec
        else:
            # Convert our spec string into a Version
            spec_version = Version(spec)

            # If the specifier does not have a local segment, then we want to
            # act as if the prospective version also does not have a local
            # segment.
            if not spec_version.local:
                prospective = Version(prospective.public)

            return prospective == spec_version

    def _compare_not_equal(self, prospective: Version, spec: str) -> bool:
        return not self._compare_equal(prospective, spec)

    def _compare_less_than_equal(self, prospective: Version, spec: str) -> bool:
        # NB: Local version identifiers are NOT permitted in the version
        # specifier, so local version labels can be universally removed from
        # the prospective version.
        return Version(prospective.public) <= Version(spec)

    def _compare_greater_than_equal(self, prospective: Version, spec: str) -> bool:
        # NB: Local version identifiers are NOT permitted in the version
        # specifier, so local version labels can be universally removed from
        # the prospective version.
        return Version(prospective.public) >= Version(spec)

    def _compare_less_than(self, prospective: Version, spec_str: str) -> bool:
        # Convert our spec to a Version instance, since we'll want to work with
        # it as a version.
        spec = Version(spec_str)

        # Check to see if the prospective version is less than the spec
        # version. If it's not we can short circuit and just return False now
        # instead of doing extra unneeded work.
        if not prospective < spec:
            return False

        # This special case is here so that, unless the specifier itself
        # includes is a pre-release version, that we do not accept pre-release
        # versions for the version mentioned in the specifier (e.g. <3.1 should
        # not match 3.1.dev0, but should match 3.0.dev0).
        if not spec.is_prerelease and prospective.is_prerelease:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # If we've gotten to here, it means that prospective version is both
        # less than the spec version *and* it's not a pre-release of the same
        # version in the spec.
        return True

    def _compare_greater_than(self, prospective: Version, spec_str: str) -> bool:
        # Convert our spec to a Version instance, since we'll want to work with
        # it as a version.
        spec = Version(spec_str)

        # Check to see if the prospective version is greater than the spec
        # version. If it's not we can short circuit and just return False now
        # instead of doing extra unneeded work.
        if not prospective > spec:
            return False

        # This special case is here so that, unless the specifier itself
        # includes is a post-release version, that we do not accept
        # post-release versions for the version mentioned in the specifier
        # (e.g. >3.1 should not match 3.0.post0, but should match 3.2.post0).
        if not spec.is_postrelease and prospective.is_postrelease:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # Ensure that we do not allow a local version of the version mentioned
        # in the specifier, which is technically greater than, to match.
        if prospective.local is not None:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # If we've gotten to here, it means that prospective version is both
        # greater than the spec version *and* it's not a pre-release of the
        # same version in the spec.
        return True

    def _compare_arbitrary(self, prospective: Version, spec: str) -> bool:
        return str(prospective).lower() == str(spec).lower()

    def __contains__(self, item: str | Version) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in Specifier(">=1.2.3")
        True
        >>> Version("1.2.3") in Specifier(">=1.2.3")
        True
        >>> "1.0.0" in Specifier(">=1.2.3")
        False
        >>> "1.3.0a1" in Specifier(">=1.2.3")
        False
        >>> "1.3.0a1" in Specifier(">=1.2.3", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(self, item: UnparsedVersion, prereleases: bool | None = None) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item:
            The item to check for, which can be a version string or a
            :class:`Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this Specifier. If set to
            ``None`` (the default), it uses :attr:`prereleases` to determine
            whether or not prereleases are allowed.

        >>> Specifier(">=1.2.3").contains("1.2.3")
        True
        >>> Specifier(">=1.2.3").contains(Version("1.2.3"))
        True
        >>> Specifier(">=1.2.3").contains("1.0.0")
        False
        >>> Specifier(">=1.2.3").contains("1.3.0a1")
        False
        >>> Specifier(">=1.2.3", prereleases=True).contains("1.3.0a1")
        True
        >>> Specifier(">=1.2.3").contains("1.3.0a1", prereleases=True)
        True
        """

        # Determine if prereleases are to be allowed or not.
        if prereleases is None:
            prereleases = self.prereleases

        # Normalize item to a Version, this allows us to have a shortcut for
        # "2.0" in Specifier(">=2")
        normalized_item = _coerce_version(item)

        # Determine if we should be supporting prereleases in this specifier
        # or not, if we do not support prereleases than we can short circuit
        # logic if this version is a prereleases.
        if normalized_item.is_prerelease and not prereleases:
            return False

        # Actually do the comparison to determine if this item is contained
        # within this Specifier or not.
        operator_callable: CallableOperator = self._get_operator(self.operator)
        return operator_callable(normalized_item, self.version)

    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """Filter items in the given iterable, that match the specifier.

        :param iterable:
            An iterable that can contain version strings and :class:`Version` instances.
            The items in the iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will be intelligently decide whether to allow
            prereleases or not (based on the :attr:`prereleases` attribute, and
            whether the only versions matching are prereleases).

        This method is smarter than just ``filter(Specifier().contains, [...])``
        because it implements the rule from :pep:`440` that a prerelease item
        SHOULD be accepted if no other versions match the given specifier.

        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.2.3", "1.3", Version("1.4")]))
        ['1.2.3', '1.3', <Version('1.4')>]
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.5a1"]))
        ['1.5a1']
        >>> list(Specifier(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(Specifier(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        """

        yielded = False
        found_prereleases = []

        kw = {"prereleases": prereleases if prereleases is not None else True}

        # Attempt to iterate over all the values in the iterable and if any of
        # them match, yield them.
        for version in iterable:
            parsed_version = _coerce_version(version)

            if self.contains(parsed_version, **kw):
                # If our version is a prerelease, and we were not set to allow
                # prereleases, then we'll store it for later in case nothing
                # else matches this specifier.
                if parsed_version.is_prerelease and not (
                    prereleases or self.prereleases
                ):
                    found_prereleases.append(version)
                # Either this is not a prerelease, or we should have been
                # accepting prereleases from the beginning.
                else:
                    yielded = True
                    yield version

        # Now that we've iterated over everything, determine if we've yielded
        # any values, and if we have not and we have any prereleases stored up
        # then we will go ahead and yield the prereleases.
        if not yielded and found_prereleases:
            for version in found_prereleases:
                yield version


_prefix_regex = re.compile(r"^([0-9]+)((?:a|b|c|rc)[0-9]+)$")


def _version_split(version: str) -> list[str]:
    """Split version into components.

    The split components are intended for version comparison. The logic does
    not attempt to retain the original version string, so joining the
    components back with :func:`_version_join` may not produce the original
    version string.
    """
    result: list[str] = []

    epoch, _, rest = version.rpartition("!")
    result.append(epoch or "0")

    for item in rest.split("."):
        match = _prefix_regex.search(item)
        if match:
            result.extend(match.groups())
        else:
            result.append(item)
    return result


def _version_join(components: list[str]) -> str:
    """Join split version components into a version string.

    This function assumes the input came from :func:`_version_split`, where the
    first component must be the epoch (either empty or numeric), and all other
    components numeric.
    """
    epoch, *rest = components
    return f"{epoch}!{'.'.join(rest)}"


def _is_not_suffix(segment: str) -> bool:
    return not any(
        segment.startswith(prefix) for prefix in ("dev", "a", "b", "rc", "post")
    )


def _pad_version(left: list[str], right: list[str]) -> tuple[list[str], list[str]]:
    left_split, right_split = [], []

    # Get the release segment of our versions
    left_split.append(list(itertools.takewhile(lambda x: x.isdigit(), left)))
    right_split.append(list(itertools.takewhile(lambda x: x.isdigit(), right)))

    # Get the rest of our versions
    left_split.append(left[len(left_split[0]) :])
    right_split.append(right[len(right_split[0]) :])

    # Insert our padding
    left_split.insert(1, ["0"] * max(0, len(right_split[0]) - len(left_split[0])))
    right_split.insert(1, ["0"] * max(0, len(left_split[0]) - len(right_split[0])))

    return (
        list(itertools.chain.from_iterable(left_split)),
        list(itertools.chain.from_iterable(right_split)),
    )


class SpecifierSet(BaseSpecifier):
    """This class abstracts handling of a set of version specifiers.

    It can be passed a single specifier (``>=3.0``), a comma-separated list of
    specifiers (``>=3.0,!=3.1``), or no specifier at all.
    """

    def __init__(
        self,
        specifiers: str | Iterable[Specifier] = "",
        prereleases: bool | None = None,
    ) -> None:
        """Initialize a SpecifierSet instance.

        :param specifiers:
            The string representation of a specifier or a comma-separated list of
            specifiers which will be parsed and normalized before use.
            May also be an iterable of ``Specifier`` instances, which will be used
            as is.
        :param prereleases:
            This tells the SpecifierSet if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.

        :raises InvalidSpecifier:
            If the given ``specifiers`` are not parseable than this exception will be
            raised.
        """

        if isinstance(specifiers, str):
            # Split on `,` to break each individual specifier into its own item, and
            # strip each item to remove leading/trailing whitespace.
            split_specifiers = [s.strip() for s in specifiers.split(",") if s.strip()]

            # Make each individual specifier a Specifier and save in a frozen set
            # for later.
            self._specs = frozenset(map(Specifier, split_specifiers))
        else:
            # Save the supplied specifiers in a frozen set.
            self._specs = frozenset(specifiers)

        # Store our prereleases value so we can use it later to determine if
        # we accept prereleases or not.
        self._prereleases = prereleases

    @property
    def prereleases(self) -> bool | None:
        # If we have been given an explicit prerelease modifier, then we'll
        # pass that through here.
        if self._prereleases is not None:
            return self._prereleases

        # If we don't have any specifiers, and we don't have a forced value,
        # then we'll just return None since we don't know if this should have
        # pre-releases or not.
        if not self._specs:
            return None

        # Otherwise we'll see if any of the given specifiers accept
        # prereleases, if any of them do we'll return True, otherwise False.
        return any(s.prereleases for s in self._specs)

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    def __repr__(self) -> str:
        """A representation of the specifier set that shows all internal state.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> SpecifierSet('>=1.0.0,!=2.0.0')
        <SpecifierSet('!=2.0.0,>=1.0.0')>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=False)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=False)>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=True)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<SpecifierSet({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the specifier set that can be round-tripped.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> str(SpecifierSet(">=1.0.0,!=1.0.1"))
        '!=1.0.1,>=1.0.0'
        >>> str(SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False))
        '!=1.0.1,>=1.0.0'
        """
        return ",".join(sorted(str(s) for s in self._specs))

    def __hash__(self) -> int:
        return hash(self._specs)

    def __and__(self, other: SpecifierSet | str) -> SpecifierSet:
        """Return a SpecifierSet which is a combination of the two sets.

        :param other: The other object to combine with.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") & '<=2.0.0,!=2.0.1'
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        >>> SpecifierSet(">=1.0.0,!=1.0.1") & SpecifierSet('<=2.0.0,!=2.0.1')
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        """
        if isinstance(other, str):
            other = SpecifierSet(other)
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        specifier = SpecifierSet()
        specifier._specs = frozenset(self._specs | other._specs)

        if self._prereleases is None and other._prereleases is not None:
            specifier._prereleases = other._prereleases
        elif self._prereleases is not None and other._prereleases is None:
            specifier._prereleases = self._prereleases
        elif self._prereleases == other._prereleases:
            specifier._prereleases = self._prereleases
        else:
            raise ValueError(
                "Cannot combine SpecifierSets with True and False prerelease "
                "overrides."
            )

        return specifier

    def __eq__(self, other: object) -> bool:
        """Whether or not the two SpecifierSet-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> (SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False) ==
        ...  SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == ">=1.0.0,!=1.0.1"
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.2")
        False
        """
        if isinstance(other, (str, Specifier)):
            other = SpecifierSet(str(other))
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        return self._specs == other._specs

    def __len__(self) -> int:
        """Returns the number of specifiers in this specifier set."""
        return len(self._specs)

    def __iter__(self) -> Iterator[Specifier]:
        """
        Returns an iterator over all the underlying :class:`Specifier` instances
        in this specifier set.

        >>> sorted(SpecifierSet(">=1.0.0,!=1.0.1"), key=str)
        [<Specifier('!=1.0.1')>, <Specifier('>=1.0.0')>]
        """
        return iter(self._specs)

    def __contains__(self, item: UnparsedVersion) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> Version("1.2.3") in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> "1.0.1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(
        self,
        item: UnparsedVersion,
        prereleases: bool | None = None,
        installed: bool | None = None,
    ) -> bool:
        """Return whether or not the item is contained in this SpecifierSet.

        :param item:
            The item to check for, which can be a version string or a
            :class:`Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this SpecifierSet. If set to
            ``None`` (the default), it uses :attr:`prereleases` to determine
            whether or not prereleases are allowed.

        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.2.3")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains(Version("1.2.3"))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.0.1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True).contains("1.3.0a1")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1", prereleases=True)
        True
        """
        # Ensure that our item is a Version instance.
        if not isinstance(item, Version):
            item = Version(item)

        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None:
            prereleases = self.prereleases

        # We can determine if we're going to allow pre-releases by looking to
        # see if any of the underlying items supports them. If none of them do
        # and this item is a pre-release then we do not allow it and we can
        # short circuit that here.
        # Note: This means that 1.0.dev1 would not be contained in something
        #       like >=1.0.devabc however it would be in >=1.0.debabc,>0.0.dev0
        if not prereleases and item.is_prerelease:
            return False

        if installed and item.is_prerelease:
            item = Version(item.base_version)

        # We simply dispatch to the underlying specs here to make sure that the
        # given version is contained within all of them.
        # Note: This use of all() here means that an empty set of specifiers
        #       will always return True, this is an explicit design decision.
        return all(s.contains(item, prereleases=prereleases) for s in self._specs)

    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """Filter items in the given iterable, that match the specifiers in this set.

        :param iterable:
            An iterable that can contain version strings and :class:`Version` instances.
            The items in the iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will be intelligently decide whether to allow
            prereleases or not (based on the :attr:`prereleases` attribute, and
            whether the only versions matching are prereleases).

        This method is smarter than just ``filter(SpecifierSet(...).contains, [...])``
        because it implements the rule from :pep:`440` that a prerelease item
        SHOULD be accepted if no other versions match the given specifier.

        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", Version("1.4")]))
        ['1.3', <Version('1.4')>]
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.5a1"]))
        []
        >>> list(SpecifierSet(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']

        An "empty" SpecifierSet will filter items based on the presence of prerelease
        versions in the set.

        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet("").filter(["1.5a1"]))
        ['1.5a1']
        >>> list(SpecifierSet("", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        """
        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None:
            prereleases = self.prereleases

        # If we have any specifiers, then we want to wrap our iterable in the
        # filter method for each one, this will act as a logical AND amongst
        # each specifier.
        if self._specs:
            for spec in self._specs:
                iterable = spec.filter(iterable, prereleases=bool(prereleases))
            return iter(iterable)
        # If we do not have any specifiers, then we need to have a rough filter
        # which will filter out any pre-releases, unless there are no final
        # releases.
        else:
            filtered: list[UnparsedVersionVar] = []
            found_prereleases: list[UnparsedVersionVar] = []

            for item in iterable:
                parsed_version = _coerce_version(item)

                # Store any item which is a pre-release for later unless we've
                # already found a final version or we are accepting prereleases
                if parsed_version.is_prerelease and not prereleases:
                    if not filtered:
                        found_prereleases.append(item)
                else:
                    filtered.append(item)

            # If we've found no items except for pre-releases, then we'll go
            # ahead and use the pre-releases
            if not filtered and found_prereleases and prereleases is None:
                return iter(found_prereleases)

            return iter(filtered)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\packaging\specifiers.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""
.. testsetup::

    from pip._vendor.packaging.specifiers import Specifier, SpecifierSet, InvalidSpecifier
    from pip._vendor.packaging.version import Version
"""

from __future__ import annotations

import abc
import itertools
import re
from typing import Callable, Iterable, Iterator, TypeVar, Union

from .utils import canonicalize_version
from .version import Version

UnparsedVersion = Union[Version, str]
UnparsedVersionVar = TypeVar("UnparsedVersionVar", bound=UnparsedVersion)
CallableOperator = Callable[[Version, str], bool]


def _coerce_version(version: UnparsedVersion) -> Version:
    if not isinstance(version, Version):
        version = Version(version)
    return version


class InvalidSpecifier(ValueError):
    """
    Raised when attempting to create a :class:`Specifier` with a specifier
    string that is invalid.

    >>> Specifier("lolwat")
    Traceback (most recent call last):
        ...
    packaging.specifiers.InvalidSpecifier: Invalid specifier: 'lolwat'
    """


class BaseSpecifier(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self) -> str:
        """
        Returns the str representation of this Specifier-like object. This
        should be representative of the Specifier itself.
        """

    @abc.abstractmethod
    def __hash__(self) -> int:
        """
        Returns a hash value for this Specifier-like object.
        """

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        """
        Returns a boolean representing whether or not the two Specifier-like
        objects are equal.

        :param other: The other object to check against.
        """

    @property
    @abc.abstractmethod
    def prereleases(self) -> bool | None:
        """Whether or not pre-releases as a whole are allowed.

        This can be set to either ``True`` or ``False`` to explicitly enable or disable
        prereleases or it can be set to ``None`` (the default) to use default semantics.
        """

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        """Setter for :attr:`prereleases`.

        :param value: The value to set.
        """

    @abc.abstractmethod
    def contains(self, item: str, prereleases: bool | None = None) -> bool:
        """
        Determines if the given item is contained within this specifier.
        """

    @abc.abstractmethod
    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """
        Takes an iterable of items and filters them so that only items which
        are contained within this specifier are allowed in it.
        """


class Specifier(BaseSpecifier):
    """This class abstracts handling of version specifiers.

    .. tip::

        It is generally not required to instantiate this manually. You should instead
        prefer to work with :class:`SpecifierSet` instead, which can parse
        comma-separated version specifiers (which is what package metadata contains).
    """

    _operator_regex_str = r"""
        (?P<operator>(~=|==|!=|<=|>=|<|>|===))
        """
    _version_regex_str = r"""
        (?P<version>
            (?:
                # The identity operators allow for an escape hatch that will
                # do an exact string match of the version you wish to install.
                # This will not be parsed by PEP 440 and we cannot determine
                # any semantic meaning from it. This operator is discouraged
                # but included entirely as an escape hatch.
                (?<====)  # Only match for the identity operator
                \s*
                [^\s;)]*  # The arbitrary version can be just about anything,
                          # we match everything except for whitespace, a
                          # semi-colon for marker support, and a closing paren
                          # since versions can be enclosed in them.
            )
            |
            (?:
                # The (non)equality operators allow for wild card and local
                # versions to be specified so we have to define these two
                # operators separately to enable that.
                (?<===|!=)            # Only match for equals and not equals

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)*   # release

                # You cannot use a wild card and a pre-release, post-release, a dev or
                # local version together so group them with a | and make them optional.
                (?:
                    \.\*  # Wild card syntax of .*
                    |
                    (?:                                  # pre release
                        [-_\.]?
                        (alpha|beta|preview|pre|a|b|c|rc)
                        [-_\.]?
                        [0-9]*
                    )?
                    (?:                                  # post release
                        (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                    )?
                    (?:[-_\.]?dev[-_\.]?[0-9]*)?         # dev release
                    (?:\+[a-z0-9]+(?:[-_\.][a-z0-9]+)*)? # local
                )?
            )
            |
            (?:
                # The compatible operator requires at least two digits in the
                # release segment.
                (?<=~=)               # Only match for the compatible operator

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)+   # release  (We have a + instead of a *)
                (?:                   # pre release
                    [-_\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                )?
                (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
            )
            |
            (?:
                # All other operators only allow a sub set of what the
                # (non)equality operators do. Specifically they do not allow
                # local versions to be specified nor do they allow the prefix
                # matching wild cards.
                (?<!==|!=|~=)         # We have special cases for these
                                      # operators so we want to make sure they
                                      # don't match here.

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)*   # release
                (?:                   # pre release
                    [-_\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                )?
                (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
            )
        )
        """

    _regex = re.compile(
        r"^\s*" + _operator_regex_str + _version_regex_str + r"\s*$",
        re.VERBOSE | re.IGNORECASE,
    )

    _operators = {
        "~=": "compatible",
        "==": "equal",
        "!=": "not_equal",
        "<=": "less_than_equal",
        ">=": "greater_than_equal",
        "<": "less_than",
        ">": "greater_than",
        "===": "arbitrary",
    }

    def __init__(self, spec: str = "", prereleases: bool | None = None) -> None:
        """Initialize a Specifier instance.

        :param spec:
            The string representation of a specifier which will be parsed and
            normalized before use.
        :param prereleases:
            This tells the specifier if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.
        :raises InvalidSpecifier:
            If the given specifier is invalid (i.e. bad syntax).
        """
        match = self._regex.search(spec)
        if not match:
            raise InvalidSpecifier(f"Invalid specifier: {spec!r}")

        self._spec: tuple[str, str] = (
            match.group("operator").strip(),
            match.group("version").strip(),
        )

        # Store whether or not this Specifier should accept prereleases
        self._prereleases = prereleases

    # https://github.com/python/mypy/pull/13475#pullrequestreview-1079784515
    @property  # type: ignore[override]
    def prereleases(self) -> bool:
        # If there is an explicit prereleases set for this, then we'll just
        # blindly use that.
        if self._prereleases is not None:
            return self._prereleases

        # Look at all of our specifiers and determine if they are inclusive
        # operators, and if they are if they are including an explicit
        # prerelease.
        operator, version = self._spec
        if operator in ["==", ">=", "<=", "~=", "===", ">", "<"]:
            # The == specifier can include a trailing .*, if it does we
            # want to remove before parsing.
            if operator == "==" and version.endswith(".*"):
                version = version[:-2]

            # Parse the version, and if it is a pre-release than this
            # specifier allows pre-releases.
            if Version(version).is_prerelease:
                return True

        return False

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    @property
    def operator(self) -> str:
        """The operator of this specifier.

        >>> Specifier("==1.2.3").operator
        '=='
        """
        return self._spec[0]

    @property
    def version(self) -> str:
        """The version of this specifier.

        >>> Specifier("==1.2.3").version
        '1.2.3'
        """
        return self._spec[1]

    def __repr__(self) -> str:
        """A representation of the Specifier that shows all internal state.

        >>> Specifier('>=1.0.0')
        <Specifier('>=1.0.0')>
        >>> Specifier('>=1.0.0', prereleases=False)
        <Specifier('>=1.0.0', prereleases=False)>
        >>> Specifier('>=1.0.0', prereleases=True)
        <Specifier('>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<{self.__class__.__name__}({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the Specifier that can be round-tripped.

        >>> str(Specifier('>=1.0.0'))
        '>=1.0.0'
        >>> str(Specifier('>=1.0.0', prereleases=False))
        '>=1.0.0'
        """
        return "{}{}".format(*self._spec)

    @property
    def _canonical_spec(self) -> tuple[str, str]:
        canonical_version = canonicalize_version(
            self._spec[1],
            strip_trailing_zero=(self._spec[0] != "~="),
        )
        return self._spec[0], canonical_version

    def __hash__(self) -> int:
        return hash(self._canonical_spec)

    def __eq__(self, other: object) -> bool:
        """Whether or not the two Specifier-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> Specifier("==1.2.3") == Specifier("== 1.2.3.0")
        True
        >>> (Specifier("==1.2.3", prereleases=False) ==
        ...  Specifier("==1.2.3", prereleases=True))
        True
        >>> Specifier("==1.2.3") == "==1.2.3"
        True
        >>> Specifier("==1.2.3") == Specifier("==1.2.4")
        False
        >>> Specifier("==1.2.3") == Specifier("~=1.2.3")
        False
        """
        if isinstance(other, str):
            try:
                other = self.__class__(str(other))
            except InvalidSpecifier:
                return NotImplemented
        elif not isinstance(other, self.__class__):
            return NotImplemented

        return self._canonical_spec == other._canonical_spec

    def _get_operator(self, op: str) -> CallableOperator:
        operator_callable: CallableOperator = getattr(
            self, f"_compare_{self._operators[op]}"
        )
        return operator_callable

    def _compare_compatible(self, prospective: Version, spec: str) -> bool:
        # Compatible releases have an equivalent combination of >= and ==. That
        # is that ~=2.2 is equivalent to >=2.2,==2.*. This allows us to
        # implement this in terms of the other specifiers instead of
        # implementing it ourselves. The only thing we need to do is construct
        # the other specifiers.

        # We want everything but the last item in the version, but we want to
        # ignore suffix segments.
        prefix = _version_join(
            list(itertools.takewhile(_is_not_suffix, _version_split(spec)))[:-1]
        )

        # Add the prefix notation to the end of our string
        prefix += ".*"

        return self._get_operator(">=")(prospective, spec) and self._get_operator("==")(
            prospective, prefix
        )

    def _compare_equal(self, prospective: Version, spec: str) -> bool:
        # We need special logic to handle prefix matching
        if spec.endswith(".*"):
            # In the case of prefix matching we want to ignore local segment.
            normalized_prospective = canonicalize_version(
                prospective.public, strip_trailing_zero=False
            )
            # Get the normalized version string ignoring the trailing .*
            normalized_spec = canonicalize_version(spec[:-2], strip_trailing_zero=False)
            # Split the spec out by bangs and dots, and pretend that there is
            # an implicit dot in between a release segment and a pre-release segment.
            split_spec = _version_split(normalized_spec)

            # Split the prospective version out by bangs and dots, and pretend
            # that there is an implicit dot in between a release segment and
            # a pre-release segment.
            split_prospective = _version_split(normalized_prospective)

            # 0-pad the prospective version before shortening it to get the correct
            # shortened version.
            padded_prospective, _ = _pad_version(split_prospective, split_spec)

            # Shorten the prospective version to be the same length as the spec
            # so that we can determine if the specifier is a prefix of the
            # prospective version or not.
            shortened_prospective = padded_prospective[: len(split_spec)]

            return shortened_prospective == split_spec
        else:
            # Convert our spec string into a Version
            spec_version = Version(spec)

            # If the specifier does not have a local segment, then we want to
            # act as if the prospective version also does not have a local
            # segment.
            if not spec_version.local:
                prospective = Version(prospective.public)

            return prospective == spec_version

    def _compare_not_equal(self, prospective: Version, spec: str) -> bool:
        return not self._compare_equal(prospective, spec)

    def _compare_less_than_equal(self, prospective: Version, spec: str) -> bool:
        # NB: Local version identifiers are NOT permitted in the version
        # specifier, so local version labels can be universally removed from
        # the prospective version.
        return Version(prospective.public) <= Version(spec)

    def _compare_greater_than_equal(self, prospective: Version, spec: str) -> bool:
        # NB: Local version identifiers are NOT permitted in the version
        # specifier, so local version labels can be universally removed from
        # the prospective version.
        return Version(prospective.public) >= Version(spec)

    def _compare_less_than(self, prospective: Version, spec_str: str) -> bool:
        # Convert our spec to a Version instance, since we'll want to work with
        # it as a version.
        spec = Version(spec_str)

        # Check to see if the prospective version is less than the spec
        # version. If it's not we can short circuit and just return False now
        # instead of doing extra unneeded work.
        if not prospective < spec:
            return False

        # This special case is here so that, unless the specifier itself
        # includes is a pre-release version, that we do not accept pre-release
        # versions for the version mentioned in the specifier (e.g. <3.1 should
        # not match 3.1.dev0, but should match 3.0.dev0).
        if not spec.is_prerelease and prospective.is_prerelease:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # If we've gotten to here, it means that prospective version is both
        # less than the spec version *and* it's not a pre-release of the same
        # version in the spec.
        return True

    def _compare_greater_than(self, prospective: Version, spec_str: str) -> bool:
        # Convert our spec to a Version instance, since we'll want to work with
        # it as a version.
        spec = Version(spec_str)

        # Check to see if the prospective version is greater than the spec
        # version. If it's not we can short circuit and just return False now
        # instead of doing extra unneeded work.
        if not prospective > spec:
            return False

        # This special case is here so that, unless the specifier itself
        # includes is a post-release version, that we do not accept
        # post-release versions for the version mentioned in the specifier
        # (e.g. >3.1 should not match 3.0.post0, but should match 3.2.post0).
        if not spec.is_postrelease and prospective.is_postrelease:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # Ensure that we do not allow a local version of the version mentioned
        # in the specifier, which is technically greater than, to match.
        if prospective.local is not None:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # If we've gotten to here, it means that prospective version is both
        # greater than the spec version *and* it's not a pre-release of the
        # same version in the spec.
        return True

    def _compare_arbitrary(self, prospective: Version, spec: str) -> bool:
        return str(prospective).lower() == str(spec).lower()

    def __contains__(self, item: str | Version) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in Specifier(">=1.2.3")
        True
        >>> Version("1.2.3") in Specifier(">=1.2.3")
        True
        >>> "1.0.0" in Specifier(">=1.2.3")
        False
        >>> "1.3.0a1" in Specifier(">=1.2.3")
        False
        >>> "1.3.0a1" in Specifier(">=1.2.3", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(self, item: UnparsedVersion, prereleases: bool | None = None) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item:
            The item to check for, which can be a version string or a
            :class:`Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this Specifier. If set to
            ``None`` (the default), it uses :attr:`prereleases` to determine
            whether or not prereleases are allowed.

        >>> Specifier(">=1.2.3").contains("1.2.3")
        True
        >>> Specifier(">=1.2.3").contains(Version("1.2.3"))
        True
        >>> Specifier(">=1.2.3").contains("1.0.0")
        False
        >>> Specifier(">=1.2.3").contains("1.3.0a1")
        False
        >>> Specifier(">=1.2.3", prereleases=True).contains("1.3.0a1")
        True
        >>> Specifier(">=1.2.3").contains("1.3.0a1", prereleases=True)
        True
        """

        # Determine if prereleases are to be allowed or not.
        if prereleases is None:
            prereleases = self.prereleases

        # Normalize item to a Version, this allows us to have a shortcut for
        # "2.0" in Specifier(">=2")
        normalized_item = _coerce_version(item)

        # Determine if we should be supporting prereleases in this specifier
        # or not, if we do not support prereleases than we can short circuit
        # logic if this version is a prereleases.
        if normalized_item.is_prerelease and not prereleases:
            return False

        # Actually do the comparison to determine if this item is contained
        # within this Specifier or not.
        operator_callable: CallableOperator = self._get_operator(self.operator)
        return operator_callable(normalized_item, self.version)

    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """Filter items in the given iterable, that match the specifier.

        :param iterable:
            An iterable that can contain version strings and :class:`Version` instances.
            The items in the iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will be intelligently decide whether to allow
            prereleases or not (based on the :attr:`prereleases` attribute, and
            whether the only versions matching are prereleases).

        This method is smarter than just ``filter(Specifier().contains, [...])``
        because it implements the rule from :pep:`440` that a prerelease item
        SHOULD be accepted if no other versions match the given specifier.

        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.2.3", "1.3", Version("1.4")]))
        ['1.2.3', '1.3', <Version('1.4')>]
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.5a1"]))
        ['1.5a1']
        >>> list(Specifier(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(Specifier(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        """

        yielded = False
        found_prereleases = []

        kw = {"prereleases": prereleases if prereleases is not None else True}

        # Attempt to iterate over all the values in the iterable and if any of
        # them match, yield them.
        for version in iterable:
            parsed_version = _coerce_version(version)

            if self.contains(parsed_version, **kw):
                # If our version is a prerelease, and we were not set to allow
                # prereleases, then we'll store it for later in case nothing
                # else matches this specifier.
                if parsed_version.is_prerelease and not (
                    prereleases or self.prereleases
                ):
                    found_prereleases.append(version)
                # Either this is not a prerelease, or we should have been
                # accepting prereleases from the beginning.
                else:
                    yielded = True
                    yield version

        # Now that we've iterated over everything, determine if we've yielded
        # any values, and if we have not and we have any prereleases stored up
        # then we will go ahead and yield the prereleases.
        if not yielded and found_prereleases:
            for version in found_prereleases:
                yield version


_prefix_regex = re.compile(r"^([0-9]+)((?:a|b|c|rc)[0-9]+)$")


def _version_split(version: str) -> list[str]:
    """Split version into components.

    The split components are intended for version comparison. The logic does
    not attempt to retain the original version string, so joining the
    components back with :func:`_version_join` may not produce the original
    version string.
    """
    result: list[str] = []

    epoch, _, rest = version.rpartition("!")
    result.append(epoch or "0")

    for item in rest.split("."):
        match = _prefix_regex.search(item)
        if match:
            result.extend(match.groups())
        else:
            result.append(item)
    return result


def _version_join(components: list[str]) -> str:
    """Join split version components into a version string.

    This function assumes the input came from :func:`_version_split`, where the
    first component must be the epoch (either empty or numeric), and all other
    components numeric.
    """
    epoch, *rest = components
    return f"{epoch}!{'.'.join(rest)}"


def _is_not_suffix(segment: str) -> bool:
    return not any(
        segment.startswith(prefix) for prefix in ("dev", "a", "b", "rc", "post")
    )


def _pad_version(left: list[str], right: list[str]) -> tuple[list[str], list[str]]:
    left_split, right_split = [], []

    # Get the release segment of our versions
    left_split.append(list(itertools.takewhile(lambda x: x.isdigit(), left)))
    right_split.append(list(itertools.takewhile(lambda x: x.isdigit(), right)))

    # Get the rest of our versions
    left_split.append(left[len(left_split[0]) :])
    right_split.append(right[len(right_split[0]) :])

    # Insert our padding
    left_split.insert(1, ["0"] * max(0, len(right_split[0]) - len(left_split[0])))
    right_split.insert(1, ["0"] * max(0, len(left_split[0]) - len(right_split[0])))

    return (
        list(itertools.chain.from_iterable(left_split)),
        list(itertools.chain.from_iterable(right_split)),
    )


class SpecifierSet(BaseSpecifier):
    """This class abstracts handling of a set of version specifiers.

    It can be passed a single specifier (``>=3.0``), a comma-separated list of
    specifiers (``>=3.0,!=3.1``), or no specifier at all.
    """

    def __init__(
        self,
        specifiers: str | Iterable[Specifier] = "",
        prereleases: bool | None = None,
    ) -> None:
        """Initialize a SpecifierSet instance.

        :param specifiers:
            The string representation of a specifier or a comma-separated list of
            specifiers which will be parsed and normalized before use.
            May also be an iterable of ``Specifier`` instances, which will be used
            as is.
        :param prereleases:
            This tells the SpecifierSet if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.

        :raises InvalidSpecifier:
            If the given ``specifiers`` are not parseable than this exception will be
            raised.
        """

        if isinstance(specifiers, str):
            # Split on `,` to break each individual specifier into its own item, and
            # strip each item to remove leading/trailing whitespace.
            split_specifiers = [s.strip() for s in specifiers.split(",") if s.strip()]

            # Make each individual specifier a Specifier and save in a frozen set
            # for later.
            self._specs = frozenset(map(Specifier, split_specifiers))
        else:
            # Save the supplied specifiers in a frozen set.
            self._specs = frozenset(specifiers)

        # Store our prereleases value so we can use it later to determine if
        # we accept prereleases or not.
        self._prereleases = prereleases

    @property
    def prereleases(self) -> bool | None:
        # If we have been given an explicit prerelease modifier, then we'll
        # pass that through here.
        if self._prereleases is not None:
            return self._prereleases

        # If we don't have any specifiers, and we don't have a forced value,
        # then we'll just return None since we don't know if this should have
        # pre-releases or not.
        if not self._specs:
            return None

        # Otherwise we'll see if any of the given specifiers accept
        # prereleases, if any of them do we'll return True, otherwise False.
        return any(s.prereleases for s in self._specs)

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    def __repr__(self) -> str:
        """A representation of the specifier set that shows all internal state.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> SpecifierSet('>=1.0.0,!=2.0.0')
        <SpecifierSet('!=2.0.0,>=1.0.0')>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=False)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=False)>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=True)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<SpecifierSet({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the specifier set that can be round-tripped.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> str(SpecifierSet(">=1.0.0,!=1.0.1"))
        '!=1.0.1,>=1.0.0'
        >>> str(SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False))
        '!=1.0.1,>=1.0.0'
        """
        return ",".join(sorted(str(s) for s in self._specs))

    def __hash__(self) -> int:
        return hash(self._specs)

    def __and__(self, other: SpecifierSet | str) -> SpecifierSet:
        """Return a SpecifierSet which is a combination of the two sets.

        :param other: The other object to combine with.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") & '<=2.0.0,!=2.0.1'
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        >>> SpecifierSet(">=1.0.0,!=1.0.1") & SpecifierSet('<=2.0.0,!=2.0.1')
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        """
        if isinstance(other, str):
            other = SpecifierSet(other)
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        specifier = SpecifierSet()
        specifier._specs = frozenset(self._specs | other._specs)

        if self._prereleases is None and other._prereleases is not None:
            specifier._prereleases = other._prereleases
        elif self._prereleases is not None and other._prereleases is None:
            specifier._prereleases = self._prereleases
        elif self._prereleases == other._prereleases:
            specifier._prereleases = self._prereleases
        else:
            raise ValueError(
                "Cannot combine SpecifierSets with True and False prerelease "
                "overrides."
            )

        return specifier

    def __eq__(self, other: object) -> bool:
        """Whether or not the two SpecifierSet-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> (SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False) ==
        ...  SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == ">=1.0.0,!=1.0.1"
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.2")
        False
        """
        if isinstance(other, (str, Specifier)):
            other = SpecifierSet(str(other))
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        return self._specs == other._specs

    def __len__(self) -> int:
        """Returns the number of specifiers in this specifier set."""
        return len(self._specs)

    def __iter__(self) -> Iterator[Specifier]:
        """
        Returns an iterator over all the underlying :class:`Specifier` instances
        in this specifier set.

        >>> sorted(SpecifierSet(">=1.0.0,!=1.0.1"), key=str)
        [<Specifier('!=1.0.1')>, <Specifier('>=1.0.0')>]
        """
        return iter(self._specs)

    def __contains__(self, item: UnparsedVersion) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> Version("1.2.3") in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> "1.0.1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(
        self,
        item: UnparsedVersion,
        prereleases: bool | None = None,
        installed: bool | None = None,
    ) -> bool:
        """Return whether or not the item is contained in this SpecifierSet.

        :param item:
            The item to check for, which can be a version string or a
            :class:`Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this SpecifierSet. If set to
            ``None`` (the default), it uses :attr:`prereleases` to determine
            whether or not prereleases are allowed.

        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.2.3")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains(Version("1.2.3"))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.0.1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True).contains("1.3.0a1")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1", prereleases=True)
        True
        """
        # Ensure that our item is a Version instance.
        if not isinstance(item, Version):
            item = Version(item)

        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None:
            prereleases = self.prereleases

        # We can determine if we're going to allow pre-releases by looking to
        # see if any of the underlying items supports them. If none of them do
        # and this item is a pre-release then we do not allow it and we can
        # short circuit that here.
        # Note: This means that 1.0.dev1 would not be contained in something
        #       like >=1.0.devabc however it would be in >=1.0.debabc,>0.0.dev0
        if not prereleases and item.is_prerelease:
            return False

        if installed and item.is_prerelease:
            item = Version(item.base_version)

        # We simply dispatch to the underlying specs here to make sure that the
        # given version is contained within all of them.
        # Note: This use of all() here means that an empty set of specifiers
        #       will always return True, this is an explicit design decision.
        return all(s.contains(item, prereleases=prereleases) for s in self._specs)

    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """Filter items in the given iterable, that match the specifiers in this set.

        :param iterable:
            An iterable that can contain version strings and :class:`Version` instances.
            The items in the iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will be intelligently decide whether to allow
            prereleases or not (based on the :attr:`prereleases` attribute, and
            whether the only versions matching are prereleases).

        This method is smarter than just ``filter(SpecifierSet(...).contains, [...])``
        because it implements the rule from :pep:`440` that a prerelease item
        SHOULD be accepted if no other versions match the given specifier.

        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", Version("1.4")]))
        ['1.3', <Version('1.4')>]
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.5a1"]))
        []
        >>> list(SpecifierSet(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']

        An "empty" SpecifierSet will filter items based on the presence of prerelease
        versions in the set.

        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet("").filter(["1.5a1"]))
        ['1.5a1']
        >>> list(SpecifierSet("", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        """
        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None:
            prereleases = self.prereleases

        # If we have any specifiers, then we want to wrap our iterable in the
        # filter method for each one, this will act as a logical AND amongst
        # each specifier.
        if self._specs:
            for spec in self._specs:
                iterable = spec.filter(iterable, prereleases=bool(prereleases))
            return iter(iterable)
        # If we do not have any specifiers, then we need to have a rough filter
        # which will filter out any pre-releases, unless there are no final
        # releases.
        else:
            filtered: list[UnparsedVersionVar] = []
            found_prereleases: list[UnparsedVersionVar] = []

            for item in iterable:
                parsed_version = _coerce_version(item)

                # Store any item which is a pre-release for later unless we've
                # already found a final version or we are accepting prereleases
                if parsed_version.is_prerelease and not prereleases:
                    if not filtered:
                        found_prereleases.append(item)
                else:
                    filtered.append(item)

            # If we've found no items except for pre-releases, then we'll go
            # ahead and use the pre-releases
            if not filtered and found_prereleases and prereleases is None:
                return iter(found_prereleases)

            return iter(filtered)

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\packaging\specifiers.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""
.. testsetup::

    from packaging.specifiers import Specifier, SpecifierSet, InvalidSpecifier
    from packaging.version import Version
"""

from __future__ import annotations

import abc
import itertools
import re
from typing import Callable, Iterable, Iterator, TypeVar, Union

from .utils import canonicalize_version
from .version import Version

UnparsedVersion = Union[Version, str]
UnparsedVersionVar = TypeVar("UnparsedVersionVar", bound=UnparsedVersion)
CallableOperator = Callable[[Version, str], bool]


def _coerce_version(version: UnparsedVersion) -> Version:
    if not isinstance(version, Version):
        version = Version(version)
    return version


class InvalidSpecifier(ValueError):
    """
    Raised when attempting to create a :class:`Specifier` with a specifier
    string that is invalid.

    >>> Specifier("lolwat")
    Traceback (most recent call last):
        ...
    packaging.specifiers.InvalidSpecifier: Invalid specifier: 'lolwat'
    """


class BaseSpecifier(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self) -> str:
        """
        Returns the str representation of this Specifier-like object. This
        should be representative of the Specifier itself.
        """

    @abc.abstractmethod
    def __hash__(self) -> int:
        """
        Returns a hash value for this Specifier-like object.
        """

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        """
        Returns a boolean representing whether or not the two Specifier-like
        objects are equal.

        :param other: The other object to check against.
        """

    @property
    @abc.abstractmethod
    def prereleases(self) -> bool | None:
        """Whether or not pre-releases as a whole are allowed.

        This can be set to either ``True`` or ``False`` to explicitly enable or disable
        prereleases or it can be set to ``None`` (the default) to use default semantics.
        """

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        """Setter for :attr:`prereleases`.

        :param value: The value to set.
        """

    @abc.abstractmethod
    def contains(self, item: str, prereleases: bool | None = None) -> bool:
        """
        Determines if the given item is contained within this specifier.
        """

    @abc.abstractmethod
    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """
        Takes an iterable of items and filters them so that only items which
        are contained within this specifier are allowed in it.
        """


class Specifier(BaseSpecifier):
    """This class abstracts handling of version specifiers.

    .. tip::

        It is generally not required to instantiate this manually. You should instead
        prefer to work with :class:`SpecifierSet` instead, which can parse
        comma-separated version specifiers (which is what package metadata contains).
    """

    _operator_regex_str = r"""
        (?P<operator>(~=|==|!=|<=|>=|<|>|===))
        """
    _version_regex_str = r"""
        (?P<version>
            (?:
                # The identity operators allow for an escape hatch that will
                # do an exact string match of the version you wish to install.
                # This will not be parsed by PEP 440 and we cannot determine
                # any semantic meaning from it. This operator is discouraged
                # but included entirely as an escape hatch.
                (?<====)  # Only match for the identity operator
                \s*
                [^\s;)]*  # The arbitrary version can be just about anything,
                          # we match everything except for whitespace, a
                          # semi-colon for marker support, and a closing paren
                          # since versions can be enclosed in them.
            )
            |
            (?:
                # The (non)equality operators allow for wild card and local
                # versions to be specified so we have to define these two
                # operators separately to enable that.
                (?<===|!=)            # Only match for equals and not equals

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)*   # release

                # You cannot use a wild card and a pre-release, post-release, a dev or
                # local version together so group them with a | and make them optional.
                (?:
                    \.\*  # Wild card syntax of .*
                    |
                    (?:                                  # pre release
                        [-_\.]?
                        (alpha|beta|preview|pre|a|b|c|rc)
                        [-_\.]?
                        [0-9]*
                    )?
                    (?:                                  # post release
                        (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                    )?
                    (?:[-_\.]?dev[-_\.]?[0-9]*)?         # dev release
                    (?:\+[a-z0-9]+(?:[-_\.][a-z0-9]+)*)? # local
                )?
            )
            |
            (?:
                # The compatible operator requires at least two digits in the
                # release segment.
                (?<=~=)               # Only match for the compatible operator

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)+   # release  (We have a + instead of a *)
                (?:                   # pre release
                    [-_\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                )?
                (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
            )
            |
            (?:
                # All other operators only allow a sub set of what the
                # (non)equality operators do. Specifically they do not allow
                # local versions to be specified nor do they allow the prefix
                # matching wild cards.
                (?<!==|!=|~=)         # We have special cases for these
                                      # operators so we want to make sure they
                                      # don't match here.

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)*   # release
                (?:                   # pre release
                    [-_\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                )?
                (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
            )
        )
        """

    _regex = re.compile(
        r"^\s*" + _operator_regex_str + _version_regex_str + r"\s*$",
        re.VERBOSE | re.IGNORECASE,
    )

    _operators = {
        "~=": "compatible",
        "==": "equal",
        "!=": "not_equal",
        "<=": "less_than_equal",
        ">=": "greater_than_equal",
        "<": "less_than",
        ">": "greater_than",
        "===": "arbitrary",
    }

    def __init__(self, spec: str = "", prereleases: bool | None = None) -> None:
        """Initialize a Specifier instance.

        :param spec:
            The string representation of a specifier which will be parsed and
            normalized before use.
        :param prereleases:
            This tells the specifier if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.
        :raises InvalidSpecifier:
            If the given specifier is invalid (i.e. bad syntax).
        """
        match = self._regex.search(spec)
        if not match:
            raise InvalidSpecifier(f"Invalid specifier: {spec!r}")

        self._spec: tuple[str, str] = (
            match.group("operator").strip(),
            match.group("version").strip(),
        )

        # Store whether or not this Specifier should accept prereleases
        self._prereleases = prereleases

    # https://github.com/python/mypy/pull/13475#pullrequestreview-1079784515
    @property  # type: ignore[override]
    def prereleases(self) -> bool:
        # If there is an explicit prereleases set for this, then we'll just
        # blindly use that.
        if self._prereleases is not None:
            return self._prereleases

        # Look at all of our specifiers and determine if they are inclusive
        # operators, and if they are if they are including an explicit
        # prerelease.
        operator, version = self._spec
        if operator in ["==", ">=", "<=", "~=", "===", ">", "<"]:
            # The == specifier can include a trailing .*, if it does we
            # want to remove before parsing.
            if operator == "==" and version.endswith(".*"):
                version = version[:-2]

            # Parse the version, and if it is a pre-release than this
            # specifier allows pre-releases.
            if Version(version).is_prerelease:
                return True

        return False

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    @property
    def operator(self) -> str:
        """The operator of this specifier.

        >>> Specifier("==1.2.3").operator
        '=='
        """
        return self._spec[0]

    @property
    def version(self) -> str:
        """The version of this specifier.

        >>> Specifier("==1.2.3").version
        '1.2.3'
        """
        return self._spec[1]

    def __repr__(self) -> str:
        """A representation of the Specifier that shows all internal state.

        >>> Specifier('>=1.0.0')
        <Specifier('>=1.0.0')>
        >>> Specifier('>=1.0.0', prereleases=False)
        <Specifier('>=1.0.0', prereleases=False)>
        >>> Specifier('>=1.0.0', prereleases=True)
        <Specifier('>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<{self.__class__.__name__}({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the Specifier that can be round-tripped.

        >>> str(Specifier('>=1.0.0'))
        '>=1.0.0'
        >>> str(Specifier('>=1.0.0', prereleases=False))
        '>=1.0.0'
        """
        return "{}{}".format(*self._spec)

    @property
    def _canonical_spec(self) -> tuple[str, str]:
        canonical_version = canonicalize_version(
            self._spec[1],
            strip_trailing_zero=(self._spec[0] != "~="),
        )
        return self._spec[0], canonical_version

    def __hash__(self) -> int:
        return hash(self._canonical_spec)

    def __eq__(self, other: object) -> bool:
        """Whether or not the two Specifier-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> Specifier("==1.2.3") == Specifier("== 1.2.3.0")
        True
        >>> (Specifier("==1.2.3", prereleases=False) ==
        ...  Specifier("==1.2.3", prereleases=True))
        True
        >>> Specifier("==1.2.3") == "==1.2.3"
        True
        >>> Specifier("==1.2.3") == Specifier("==1.2.4")
        False
        >>> Specifier("==1.2.3") == Specifier("~=1.2.3")
        False
        """
        if isinstance(other, str):
            try:
                other = self.__class__(str(other))
            except InvalidSpecifier:
                return NotImplemented
        elif not isinstance(other, self.__class__):
            return NotImplemented

        return self._canonical_spec == other._canonical_spec

    def _get_operator(self, op: str) -> CallableOperator:
        operator_callable: CallableOperator = getattr(
            self, f"_compare_{self._operators[op]}"
        )
        return operator_callable

    def _compare_compatible(self, prospective: Version, spec: str) -> bool:
        # Compatible releases have an equivalent combination of >= and ==. That
        # is that ~=2.2 is equivalent to >=2.2,==2.*. This allows us to
        # implement this in terms of the other specifiers instead of
        # implementing it ourselves. The only thing we need to do is construct
        # the other specifiers.

        # We want everything but the last item in the version, but we want to
        # ignore suffix segments.
        prefix = _version_join(
            list(itertools.takewhile(_is_not_suffix, _version_split(spec)))[:-1]
        )

        # Add the prefix notation to the end of our string
        prefix += ".*"

        return self._get_operator(">=")(prospective, spec) and self._get_operator("==")(
            prospective, prefix
        )

    def _compare_equal(self, prospective: Version, spec: str) -> bool:
        # We need special logic to handle prefix matching
        if spec.endswith(".*"):
            # In the case of prefix matching we want to ignore local segment.
            normalized_prospective = canonicalize_version(
                prospective.public, strip_trailing_zero=False
            )
            # Get the normalized version string ignoring the trailing .*
            normalized_spec = canonicalize_version(spec[:-2], strip_trailing_zero=False)
            # Split the spec out by bangs and dots, and pretend that there is
            # an implicit dot in between a release segment and a pre-release segment.
            split_spec = _version_split(normalized_spec)

            # Split the prospective version out by bangs and dots, and pretend
            # that there is an implicit dot in between a release segment and
            # a pre-release segment.
            split_prospective = _version_split(normalized_prospective)

            # 0-pad the prospective version before shortening it to get the correct
            # shortened version.
            padded_prospective, _ = _pad_version(split_prospective, split_spec)

            # Shorten the prospective version to be the same length as the spec
            # so that we can determine if the specifier is a prefix of the
            # prospective version or not.
            shortened_prospective = padded_prospective[: len(split_spec)]

            return shortened_prospective == split_spec
        else:
            # Convert our spec string into a Version
            spec_version = Version(spec)

            # If the specifier does not have a local segment, then we want to
            # act as if the prospective version also does not have a local
            # segment.
            if not spec_version.local:
                prospective = Version(prospective.public)

            return prospective == spec_version

    def _compare_not_equal(self, prospective: Version, spec: str) -> bool:
        return not self._compare_equal(prospective, spec)

    def _compare_less_than_equal(self, prospective: Version, spec: str) -> bool:
        # NB: Local version identifiers are NOT permitted in the version
        # specifier, so local version labels can be universally removed from
        # the prospective version.
        return Version(prospective.public) <= Version(spec)

    def _compare_greater_than_equal(self, prospective: Version, spec: str) -> bool:
        # NB: Local version identifiers are NOT permitted in the version
        # specifier, so local version labels can be universally removed from
        # the prospective version.
        return Version(prospective.public) >= Version(spec)

    def _compare_less_than(self, prospective: Version, spec_str: str) -> bool:
        # Convert our spec to a Version instance, since we'll want to work with
        # it as a version.
        spec = Version(spec_str)

        # Check to see if the prospective version is less than the spec
        # version. If it's not we can short circuit and just return False now
        # instead of doing extra unneeded work.
        if not prospective < spec:
            return False

        # This special case is here so that, unless the specifier itself
        # includes is a pre-release version, that we do not accept pre-release
        # versions for the version mentioned in the specifier (e.g. <3.1 should
        # not match 3.1.dev0, but should match 3.0.dev0).
        if not spec.is_prerelease and prospective.is_prerelease:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # If we've gotten to here, it means that prospective version is both
        # less than the spec version *and* it's not a pre-release of the same
        # version in the spec.
        return True

    def _compare_greater_than(self, prospective: Version, spec_str: str) -> bool:
        # Convert our spec to a Version instance, since we'll want to work with
        # it as a version.
        spec = Version(spec_str)

        # Check to see if the prospective version is greater than the spec
        # version. If it's not we can short circuit and just return False now
        # instead of doing extra unneeded work.
        if not prospective > spec:
            return False

        # This special case is here so that, unless the specifier itself
        # includes is a post-release version, that we do not accept
        # post-release versions for the version mentioned in the specifier
        # (e.g. >3.1 should not match 3.0.post0, but should match 3.2.post0).
        if not spec.is_postrelease and prospective.is_postrelease:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # Ensure that we do not allow a local version of the version mentioned
        # in the specifier, which is technically greater than, to match.
        if prospective.local is not None:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # If we've gotten to here, it means that prospective version is both
        # greater than the spec version *and* it's not a pre-release of the
        # same version in the spec.
        return True

    def _compare_arbitrary(self, prospective: Version, spec: str) -> bool:
        return str(prospective).lower() == str(spec).lower()

    def __contains__(self, item: str | Version) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in Specifier(">=1.2.3")
        True
        >>> Version("1.2.3") in Specifier(">=1.2.3")
        True
        >>> "1.0.0" in Specifier(">=1.2.3")
        False
        >>> "1.3.0a1" in Specifier(">=1.2.3")
        False
        >>> "1.3.0a1" in Specifier(">=1.2.3", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(self, item: UnparsedVersion, prereleases: bool | None = None) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item:
            The item to check for, which can be a version string or a
            :class:`Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this Specifier. If set to
            ``None`` (the default), it uses :attr:`prereleases` to determine
            whether or not prereleases are allowed.

        >>> Specifier(">=1.2.3").contains("1.2.3")
        True
        >>> Specifier(">=1.2.3").contains(Version("1.2.3"))
        True
        >>> Specifier(">=1.2.3").contains("1.0.0")
        False
        >>> Specifier(">=1.2.3").contains("1.3.0a1")
        False
        >>> Specifier(">=1.2.3", prereleases=True).contains("1.3.0a1")
        True
        >>> Specifier(">=1.2.3").contains("1.3.0a1", prereleases=True)
        True
        """

        # Determine if prereleases are to be allowed or not.
        if prereleases is None:
            prereleases = self.prereleases

        # Normalize item to a Version, this allows us to have a shortcut for
        # "2.0" in Specifier(">=2")
        normalized_item = _coerce_version(item)

        # Determine if we should be supporting prereleases in this specifier
        # or not, if we do not support prereleases than we can short circuit
        # logic if this version is a prereleases.
        if normalized_item.is_prerelease and not prereleases:
            return False

        # Actually do the comparison to determine if this item is contained
        # within this Specifier or not.
        operator_callable: CallableOperator = self._get_operator(self.operator)
        return operator_callable(normalized_item, self.version)

    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """Filter items in the given iterable, that match the specifier.

        :param iterable:
            An iterable that can contain version strings and :class:`Version` instances.
            The items in the iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will be intelligently decide whether to allow
            prereleases or not (based on the :attr:`prereleases` attribute, and
            whether the only versions matching are prereleases).

        This method is smarter than just ``filter(Specifier().contains, [...])``
        because it implements the rule from :pep:`440` that a prerelease item
        SHOULD be accepted if no other versions match the given specifier.

        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.2.3", "1.3", Version("1.4")]))
        ['1.2.3', '1.3', <Version('1.4')>]
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.5a1"]))
        ['1.5a1']
        >>> list(Specifier(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(Specifier(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        """

        yielded = False
        found_prereleases = []

        kw = {"prereleases": prereleases if prereleases is not None else True}

        # Attempt to iterate over all the values in the iterable and if any of
        # them match, yield them.
        for version in iterable:
            parsed_version = _coerce_version(version)

            if self.contains(parsed_version, **kw):
                # If our version is a prerelease, and we were not set to allow
                # prereleases, then we'll store it for later in case nothing
                # else matches this specifier.
                if parsed_version.is_prerelease and not (
                    prereleases or self.prereleases
                ):
                    found_prereleases.append(version)
                # Either this is not a prerelease, or we should have been
                # accepting prereleases from the beginning.
                else:
                    yielded = True
                    yield version

        # Now that we've iterated over everything, determine if we've yielded
        # any values, and if we have not and we have any prereleases stored up
        # then we will go ahead and yield the prereleases.
        if not yielded and found_prereleases:
            for version in found_prereleases:
                yield version


_prefix_regex = re.compile(r"^([0-9]+)((?:a|b|c|rc)[0-9]+)$")


def _version_split(version: str) -> list[str]:
    """Split version into components.

    The split components are intended for version comparison. The logic does
    not attempt to retain the original version string, so joining the
    components back with :func:`_version_join` may not produce the original
    version string.
    """
    result: list[str] = []

    epoch, _, rest = version.rpartition("!")
    result.append(epoch or "0")

    for item in rest.split("."):
        match = _prefix_regex.search(item)
        if match:
            result.extend(match.groups())
        else:
            result.append(item)
    return result


def _version_join(components: list[str]) -> str:
    """Join split version components into a version string.

    This function assumes the input came from :func:`_version_split`, where the
    first component must be the epoch (either empty or numeric), and all other
    components numeric.
    """
    epoch, *rest = components
    return f"{epoch}!{'.'.join(rest)}"


def _is_not_suffix(segment: str) -> bool:
    return not any(
        segment.startswith(prefix) for prefix in ("dev", "a", "b", "rc", "post")
    )


def _pad_version(left: list[str], right: list[str]) -> tuple[list[str], list[str]]:
    left_split, right_split = [], []

    # Get the release segment of our versions
    left_split.append(list(itertools.takewhile(lambda x: x.isdigit(), left)))
    right_split.append(list(itertools.takewhile(lambda x: x.isdigit(), right)))

    # Get the rest of our versions
    left_split.append(left[len(left_split[0]) :])
    right_split.append(right[len(right_split[0]) :])

    # Insert our padding
    left_split.insert(1, ["0"] * max(0, len(right_split[0]) - len(left_split[0])))
    right_split.insert(1, ["0"] * max(0, len(left_split[0]) - len(right_split[0])))

    return (
        list(itertools.chain.from_iterable(left_split)),
        list(itertools.chain.from_iterable(right_split)),
    )


class SpecifierSet(BaseSpecifier):
    """This class abstracts handling of a set of version specifiers.

    It can be passed a single specifier (``>=3.0``), a comma-separated list of
    specifiers (``>=3.0,!=3.1``), or no specifier at all.
    """

    def __init__(
        self,
        specifiers: str | Iterable[Specifier] = "",
        prereleases: bool | None = None,
    ) -> None:
        """Initialize a SpecifierSet instance.

        :param specifiers:
            The string representation of a specifier or a comma-separated list of
            specifiers which will be parsed and normalized before use.
            May also be an iterable of ``Specifier`` instances, which will be used
            as is.
        :param prereleases:
            This tells the SpecifierSet if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.

        :raises InvalidSpecifier:
            If the given ``specifiers`` are not parseable than this exception will be
            raised.
        """

        if isinstance(specifiers, str):
            # Split on `,` to break each individual specifier into its own item, and
            # strip each item to remove leading/trailing whitespace.
            split_specifiers = [s.strip() for s in specifiers.split(",") if s.strip()]

            # Make each individual specifier a Specifier and save in a frozen set
            # for later.
            self._specs = frozenset(map(Specifier, split_specifiers))
        else:
            # Save the supplied specifiers in a frozen set.
            self._specs = frozenset(specifiers)

        # Store our prereleases value so we can use it later to determine if
        # we accept prereleases or not.
        self._prereleases = prereleases

    @property
    def prereleases(self) -> bool | None:
        # If we have been given an explicit prerelease modifier, then we'll
        # pass that through here.
        if self._prereleases is not None:
            return self._prereleases

        # If we don't have any specifiers, and we don't have a forced value,
        # then we'll just return None since we don't know if this should have
        # pre-releases or not.
        if not self._specs:
            return None

        # Otherwise we'll see if any of the given specifiers accept
        # prereleases, if any of them do we'll return True, otherwise False.
        return any(s.prereleases for s in self._specs)

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    def __repr__(self) -> str:
        """A representation of the specifier set that shows all internal state.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> SpecifierSet('>=1.0.0,!=2.0.0')
        <SpecifierSet('!=2.0.0,>=1.0.0')>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=False)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=False)>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=True)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<SpecifierSet({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the specifier set that can be round-tripped.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> str(SpecifierSet(">=1.0.0,!=1.0.1"))
        '!=1.0.1,>=1.0.0'
        >>> str(SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False))
        '!=1.0.1,>=1.0.0'
        """
        return ",".join(sorted(str(s) for s in self._specs))

    def __hash__(self) -> int:
        return hash(self._specs)

    def __and__(self, other: SpecifierSet | str) -> SpecifierSet:
        """Return a SpecifierSet which is a combination of the two sets.

        :param other: The other object to combine with.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") & '<=2.0.0,!=2.0.1'
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        >>> SpecifierSet(">=1.0.0,!=1.0.1") & SpecifierSet('<=2.0.0,!=2.0.1')
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        """
        if isinstance(other, str):
            other = SpecifierSet(other)
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        specifier = SpecifierSet()
        specifier._specs = frozenset(self._specs | other._specs)

        if self._prereleases is None and other._prereleases is not None:
            specifier._prereleases = other._prereleases
        elif self._prereleases is not None and other._prereleases is None:
            specifier._prereleases = self._prereleases
        elif self._prereleases == other._prereleases:
            specifier._prereleases = self._prereleases
        else:
            raise ValueError(
                "Cannot combine SpecifierSets with True and False prerelease "
                "overrides."
            )

        return specifier

    def __eq__(self, other: object) -> bool:
        """Whether or not the two SpecifierSet-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> (SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False) ==
        ...  SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == ">=1.0.0,!=1.0.1"
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.2")
        False
        """
        if isinstance(other, (str, Specifier)):
            other = SpecifierSet(str(other))
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        return self._specs == other._specs

    def __len__(self) -> int:
        """Returns the number of specifiers in this specifier set."""
        return len(self._specs)

    def __iter__(self) -> Iterator[Specifier]:
        """
        Returns an iterator over all the underlying :class:`Specifier` instances
        in this specifier set.

        >>> sorted(SpecifierSet(">=1.0.0,!=1.0.1"), key=str)
        [<Specifier('!=1.0.1')>, <Specifier('>=1.0.0')>]
        """
        return iter(self._specs)

    def __contains__(self, item: UnparsedVersion) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> Version("1.2.3") in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> "1.0.1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(
        self,
        item: UnparsedVersion,
        prereleases: bool | None = None,
        installed: bool | None = None,
    ) -> bool:
        """Return whether or not the item is contained in this SpecifierSet.

        :param item:
            The item to check for, which can be a version string or a
            :class:`Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this SpecifierSet. If set to
            ``None`` (the default), it uses :attr:`prereleases` to determine
            whether or not prereleases are allowed.

        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.2.3")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains(Version("1.2.3"))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.0.1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True).contains("1.3.0a1")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1", prereleases=True)
        True
        """
        # Ensure that our item is a Version instance.
        if not isinstance(item, Version):
            item = Version(item)

        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None:
            prereleases = self.prereleases

        # We can determine if we're going to allow pre-releases by looking to
        # see if any of the underlying items supports them. If none of them do
        # and this item is a pre-release then we do not allow it and we can
        # short circuit that here.
        # Note: This means that 1.0.dev1 would not be contained in something
        #       like >=1.0.devabc however it would be in >=1.0.debabc,>0.0.dev0
        if not prereleases and item.is_prerelease:
            return False

        if installed and item.is_prerelease:
            item = Version(item.base_version)

        # We simply dispatch to the underlying specs here to make sure that the
        # given version is contained within all of them.
        # Note: This use of all() here means that an empty set of specifiers
        #       will always return True, this is an explicit design decision.
        return all(s.contains(item, prereleases=prereleases) for s in self._specs)

    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """Filter items in the given iterable, that match the specifiers in this set.

        :param iterable:
            An iterable that can contain version strings and :class:`Version` instances.
            The items in the iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will be intelligently decide whether to allow
            prereleases or not (based on the :attr:`prereleases` attribute, and
            whether the only versions matching are prereleases).

        This method is smarter than just ``filter(SpecifierSet(...).contains, [...])``
        because it implements the rule from :pep:`440` that a prerelease item
        SHOULD be accepted if no other versions match the given specifier.

        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", Version("1.4")]))
        ['1.3', <Version('1.4')>]
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.5a1"]))
        []
        >>> list(SpecifierSet(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']

        An "empty" SpecifierSet will filter items based on the presence of prerelease
        versions in the set.

        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet("").filter(["1.5a1"]))
        ['1.5a1']
        >>> list(SpecifierSet("", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        """
        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None:
            prereleases = self.prereleases

        # If we have any specifiers, then we want to wrap our iterable in the
        # filter method for each one, this will act as a logical AND amongst
        # each specifier.
        if self._specs:
            for spec in self._specs:
                iterable = spec.filter(iterable, prereleases=bool(prereleases))
            return iter(iterable)
        # If we do not have any specifiers, then we need to have a rough filter
        # which will filter out any pre-releases, unless there are no final
        # releases.
        else:
            filtered: list[UnparsedVersionVar] = []
            found_prereleases: list[UnparsedVersionVar] = []

            for item in iterable:
                parsed_version = _coerce_version(item)

                # Store any item which is a pre-release for later unless we've
                # already found a final version or we are accepting prereleases
                if parsed_version.is_prerelease and not prereleases:
                    if not filtered:
                        found_prereleases.append(item)
                else:
                    filtered.append(item)

            # If we've found no items except for pre-releases, then we'll go
            # ahead and use the pre-releases
            if not filtered and found_prereleases and prereleases is None:
                return iter(found_prereleases)

            return iter(filtered)

# === NexusCore/openenv\Lib\site-packages\packaging\specifiers.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""
.. testsetup::

    from packaging.specifiers import Specifier, SpecifierSet, InvalidSpecifier
    from packaging.version import Version
"""

from __future__ import annotations

import abc
import itertools
import re
from typing import Callable, Iterable, Iterator, TypeVar, Union

from .utils import canonicalize_version
from .version import Version

UnparsedVersion = Union[Version, str]
UnparsedVersionVar = TypeVar("UnparsedVersionVar", bound=UnparsedVersion)
CallableOperator = Callable[[Version, str], bool]


def _coerce_version(version: UnparsedVersion) -> Version:
    if not isinstance(version, Version):
        version = Version(version)
    return version


class InvalidSpecifier(ValueError):
    """
    Raised when attempting to create a :class:`Specifier` with a specifier
    string that is invalid.

    >>> Specifier("lolwat")
    Traceback (most recent call last):
        ...
    packaging.specifiers.InvalidSpecifier: Invalid specifier: 'lolwat'
    """


class BaseSpecifier(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __str__(self) -> str:
        """
        Returns the str representation of this Specifier-like object. This
        should be representative of the Specifier itself.
        """

    @abc.abstractmethod
    def __hash__(self) -> int:
        """
        Returns a hash value for this Specifier-like object.
        """

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        """
        Returns a boolean representing whether or not the two Specifier-like
        objects are equal.

        :param other: The other object to check against.
        """

    @property
    @abc.abstractmethod
    def prereleases(self) -> bool | None:
        """Whether or not pre-releases as a whole are allowed.

        This can be set to either ``True`` or ``False`` to explicitly enable or disable
        prereleases or it can be set to ``None`` (the default) to use default semantics.
        """

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        """Setter for :attr:`prereleases`.

        :param value: The value to set.
        """

    @abc.abstractmethod
    def contains(self, item: str, prereleases: bool | None = None) -> bool:
        """
        Determines if the given item is contained within this specifier.
        """

    @abc.abstractmethod
    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """
        Takes an iterable of items and filters them so that only items which
        are contained within this specifier are allowed in it.
        """


class Specifier(BaseSpecifier):
    """This class abstracts handling of version specifiers.

    .. tip::

        It is generally not required to instantiate this manually. You should instead
        prefer to work with :class:`SpecifierSet` instead, which can parse
        comma-separated version specifiers (which is what package metadata contains).
    """

    _operator_regex_str = r"""
        (?P<operator>(~=|==|!=|<=|>=|<|>|===))
        """
    _version_regex_str = r"""
        (?P<version>
            (?:
                # The identity operators allow for an escape hatch that will
                # do an exact string match of the version you wish to install.
                # This will not be parsed by PEP 440 and we cannot determine
                # any semantic meaning from it. This operator is discouraged
                # but included entirely as an escape hatch.
                (?<====)  # Only match for the identity operator
                \s*
                [^\s;)]*  # The arbitrary version can be just about anything,
                          # we match everything except for whitespace, a
                          # semi-colon for marker support, and a closing paren
                          # since versions can be enclosed in them.
            )
            |
            (?:
                # The (non)equality operators allow for wild card and local
                # versions to be specified so we have to define these two
                # operators separately to enable that.
                (?<===|!=)            # Only match for equals and not equals

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)*   # release

                # You cannot use a wild card and a pre-release, post-release, a dev or
                # local version together so group them with a | and make them optional.
                (?:
                    \.\*  # Wild card syntax of .*
                    |
                    (?:                                  # pre release
                        [-_\.]?
                        (alpha|beta|preview|pre|a|b|c|rc)
                        [-_\.]?
                        [0-9]*
                    )?
                    (?:                                  # post release
                        (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                    )?
                    (?:[-_\.]?dev[-_\.]?[0-9]*)?         # dev release
                    (?:\+[a-z0-9]+(?:[-_\.][a-z0-9]+)*)? # local
                )?
            )
            |
            (?:
                # The compatible operator requires at least two digits in the
                # release segment.
                (?<=~=)               # Only match for the compatible operator

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)+   # release  (We have a + instead of a *)
                (?:                   # pre release
                    [-_\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                )?
                (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
            )
            |
            (?:
                # All other operators only allow a sub set of what the
                # (non)equality operators do. Specifically they do not allow
                # local versions to be specified nor do they allow the prefix
                # matching wild cards.
                (?<!==|!=|~=)         # We have special cases for these
                                      # operators so we want to make sure they
                                      # don't match here.

                \s*
                v?
                (?:[0-9]+!)?          # epoch
                [0-9]+(?:\.[0-9]+)*   # release
                (?:                   # pre release
                    [-_\.]?
                    (alpha|beta|preview|pre|a|b|c|rc)
                    [-_\.]?
                    [0-9]*
                )?
                (?:                                   # post release
                    (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                )?
                (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
            )
        )
        """

    _regex = re.compile(
        r"^\s*" + _operator_regex_str + _version_regex_str + r"\s*$",
        re.VERBOSE | re.IGNORECASE,
    )

    _operators = {
        "~=": "compatible",
        "==": "equal",
        "!=": "not_equal",
        "<=": "less_than_equal",
        ">=": "greater_than_equal",
        "<": "less_than",
        ">": "greater_than",
        "===": "arbitrary",
    }

    def __init__(self, spec: str = "", prereleases: bool | None = None) -> None:
        """Initialize a Specifier instance.

        :param spec:
            The string representation of a specifier which will be parsed and
            normalized before use.
        :param prereleases:
            This tells the specifier if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.
        :raises InvalidSpecifier:
            If the given specifier is invalid (i.e. bad syntax).
        """
        match = self._regex.search(spec)
        if not match:
            raise InvalidSpecifier(f"Invalid specifier: {spec!r}")

        self._spec: tuple[str, str] = (
            match.group("operator").strip(),
            match.group("version").strip(),
        )

        # Store whether or not this Specifier should accept prereleases
        self._prereleases = prereleases

    # https://github.com/python/mypy/pull/13475#pullrequestreview-1079784515
    @property  # type: ignore[override]
    def prereleases(self) -> bool:
        # If there is an explicit prereleases set for this, then we'll just
        # blindly use that.
        if self._prereleases is not None:
            return self._prereleases

        # Look at all of our specifiers and determine if they are inclusive
        # operators, and if they are if they are including an explicit
        # prerelease.
        operator, version = self._spec
        if operator in ["==", ">=", "<=", "~=", "===", ">", "<"]:
            # The == specifier can include a trailing .*, if it does we
            # want to remove before parsing.
            if operator == "==" and version.endswith(".*"):
                version = version[:-2]

            # Parse the version, and if it is a pre-release than this
            # specifier allows pre-releases.
            if Version(version).is_prerelease:
                return True

        return False

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    @property
    def operator(self) -> str:
        """The operator of this specifier.

        >>> Specifier("==1.2.3").operator
        '=='
        """
        return self._spec[0]

    @property
    def version(self) -> str:
        """The version of this specifier.

        >>> Specifier("==1.2.3").version
        '1.2.3'
        """
        return self._spec[1]

    def __repr__(self) -> str:
        """A representation of the Specifier that shows all internal state.

        >>> Specifier('>=1.0.0')
        <Specifier('>=1.0.0')>
        >>> Specifier('>=1.0.0', prereleases=False)
        <Specifier('>=1.0.0', prereleases=False)>
        >>> Specifier('>=1.0.0', prereleases=True)
        <Specifier('>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<{self.__class__.__name__}({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the Specifier that can be round-tripped.

        >>> str(Specifier('>=1.0.0'))
        '>=1.0.0'
        >>> str(Specifier('>=1.0.0', prereleases=False))
        '>=1.0.0'
        """
        return "{}{}".format(*self._spec)

    @property
    def _canonical_spec(self) -> tuple[str, str]:
        canonical_version = canonicalize_version(
            self._spec[1],
            strip_trailing_zero=(self._spec[0] != "~="),
        )
        return self._spec[0], canonical_version

    def __hash__(self) -> int:
        return hash(self._canonical_spec)

    def __eq__(self, other: object) -> bool:
        """Whether or not the two Specifier-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> Specifier("==1.2.3") == Specifier("== 1.2.3.0")
        True
        >>> (Specifier("==1.2.3", prereleases=False) ==
        ...  Specifier("==1.2.3", prereleases=True))
        True
        >>> Specifier("==1.2.3") == "==1.2.3"
        True
        >>> Specifier("==1.2.3") == Specifier("==1.2.4")
        False
        >>> Specifier("==1.2.3") == Specifier("~=1.2.3")
        False
        """
        if isinstance(other, str):
            try:
                other = self.__class__(str(other))
            except InvalidSpecifier:
                return NotImplemented
        elif not isinstance(other, self.__class__):
            return NotImplemented

        return self._canonical_spec == other._canonical_spec

    def _get_operator(self, op: str) -> CallableOperator:
        operator_callable: CallableOperator = getattr(
            self, f"_compare_{self._operators[op]}"
        )
        return operator_callable

    def _compare_compatible(self, prospective: Version, spec: str) -> bool:
        # Compatible releases have an equivalent combination of >= and ==. That
        # is that ~=2.2 is equivalent to >=2.2,==2.*. This allows us to
        # implement this in terms of the other specifiers instead of
        # implementing it ourselves. The only thing we need to do is construct
        # the other specifiers.

        # We want everything but the last item in the version, but we want to
        # ignore suffix segments.
        prefix = _version_join(
            list(itertools.takewhile(_is_not_suffix, _version_split(spec)))[:-1]
        )

        # Add the prefix notation to the end of our string
        prefix += ".*"

        return self._get_operator(">=")(prospective, spec) and self._get_operator("==")(
            prospective, prefix
        )

    def _compare_equal(self, prospective: Version, spec: str) -> bool:
        # We need special logic to handle prefix matching
        if spec.endswith(".*"):
            # In the case of prefix matching we want to ignore local segment.
            normalized_prospective = canonicalize_version(
                prospective.public, strip_trailing_zero=False
            )
            # Get the normalized version string ignoring the trailing .*
            normalized_spec = canonicalize_version(spec[:-2], strip_trailing_zero=False)
            # Split the spec out by bangs and dots, and pretend that there is
            # an implicit dot in between a release segment and a pre-release segment.
            split_spec = _version_split(normalized_spec)

            # Split the prospective version out by bangs and dots, and pretend
            # that there is an implicit dot in between a release segment and
            # a pre-release segment.
            split_prospective = _version_split(normalized_prospective)

            # 0-pad the prospective version before shortening it to get the correct
            # shortened version.
            padded_prospective, _ = _pad_version(split_prospective, split_spec)

            # Shorten the prospective version to be the same length as the spec
            # so that we can determine if the specifier is a prefix of the
            # prospective version or not.
            shortened_prospective = padded_prospective[: len(split_spec)]

            return shortened_prospective == split_spec
        else:
            # Convert our spec string into a Version
            spec_version = Version(spec)

            # If the specifier does not have a local segment, then we want to
            # act as if the prospective version also does not have a local
            # segment.
            if not spec_version.local:
                prospective = Version(prospective.public)

            return prospective == spec_version

    def _compare_not_equal(self, prospective: Version, spec: str) -> bool:
        return not self._compare_equal(prospective, spec)

    def _compare_less_than_equal(self, prospective: Version, spec: str) -> bool:
        # NB: Local version identifiers are NOT permitted in the version
        # specifier, so local version labels can be universally removed from
        # the prospective version.
        return Version(prospective.public) <= Version(spec)

    def _compare_greater_than_equal(self, prospective: Version, spec: str) -> bool:
        # NB: Local version identifiers are NOT permitted in the version
        # specifier, so local version labels can be universally removed from
        # the prospective version.
        return Version(prospective.public) >= Version(spec)

    def _compare_less_than(self, prospective: Version, spec_str: str) -> bool:
        # Convert our spec to a Version instance, since we'll want to work with
        # it as a version.
        spec = Version(spec_str)

        # Check to see if the prospective version is less than the spec
        # version. If it's not we can short circuit and just return False now
        # instead of doing extra unneeded work.
        if not prospective < spec:
            return False

        # This special case is here so that, unless the specifier itself
        # includes is a pre-release version, that we do not accept pre-release
        # versions for the version mentioned in the specifier (e.g. <3.1 should
        # not match 3.1.dev0, but should match 3.0.dev0).
        if not spec.is_prerelease and prospective.is_prerelease:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # If we've gotten to here, it means that prospective version is both
        # less than the spec version *and* it's not a pre-release of the same
        # version in the spec.
        return True

    def _compare_greater_than(self, prospective: Version, spec_str: str) -> bool:
        # Convert our spec to a Version instance, since we'll want to work with
        # it as a version.
        spec = Version(spec_str)

        # Check to see if the prospective version is greater than the spec
        # version. If it's not we can short circuit and just return False now
        # instead of doing extra unneeded work.
        if not prospective > spec:
            return False

        # This special case is here so that, unless the specifier itself
        # includes is a post-release version, that we do not accept
        # post-release versions for the version mentioned in the specifier
        # (e.g. >3.1 should not match 3.0.post0, but should match 3.2.post0).
        if not spec.is_postrelease and prospective.is_postrelease:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # Ensure that we do not allow a local version of the version mentioned
        # in the specifier, which is technically greater than, to match.
        if prospective.local is not None:
            if Version(prospective.base_version) == Version(spec.base_version):
                return False

        # If we've gotten to here, it means that prospective version is both
        # greater than the spec version *and* it's not a pre-release of the
        # same version in the spec.
        return True

    def _compare_arbitrary(self, prospective: Version, spec: str) -> bool:
        return str(prospective).lower() == str(spec).lower()

    def __contains__(self, item: str | Version) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in Specifier(">=1.2.3")
        True
        >>> Version("1.2.3") in Specifier(">=1.2.3")
        True
        >>> "1.0.0" in Specifier(">=1.2.3")
        False
        >>> "1.3.0a1" in Specifier(">=1.2.3")
        False
        >>> "1.3.0a1" in Specifier(">=1.2.3", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(self, item: UnparsedVersion, prereleases: bool | None = None) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item:
            The item to check for, which can be a version string or a
            :class:`Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this Specifier. If set to
            ``None`` (the default), it uses :attr:`prereleases` to determine
            whether or not prereleases are allowed.

        >>> Specifier(">=1.2.3").contains("1.2.3")
        True
        >>> Specifier(">=1.2.3").contains(Version("1.2.3"))
        True
        >>> Specifier(">=1.2.3").contains("1.0.0")
        False
        >>> Specifier(">=1.2.3").contains("1.3.0a1")
        False
        >>> Specifier(">=1.2.3", prereleases=True).contains("1.3.0a1")
        True
        >>> Specifier(">=1.2.3").contains("1.3.0a1", prereleases=True)
        True
        """

        # Determine if prereleases are to be allowed or not.
        if prereleases is None:
            prereleases = self.prereleases

        # Normalize item to a Version, this allows us to have a shortcut for
        # "2.0" in Specifier(">=2")
        normalized_item = _coerce_version(item)

        # Determine if we should be supporting prereleases in this specifier
        # or not, if we do not support prereleases than we can short circuit
        # logic if this version is a prereleases.
        if normalized_item.is_prerelease and not prereleases:
            return False

        # Actually do the comparison to determine if this item is contained
        # within this Specifier or not.
        operator_callable: CallableOperator = self._get_operator(self.operator)
        return operator_callable(normalized_item, self.version)

    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """Filter items in the given iterable, that match the specifier.

        :param iterable:
            An iterable that can contain version strings and :class:`Version` instances.
            The items in the iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will be intelligently decide whether to allow
            prereleases or not (based on the :attr:`prereleases` attribute, and
            whether the only versions matching are prereleases).

        This method is smarter than just ``filter(Specifier().contains, [...])``
        because it implements the rule from :pep:`440` that a prerelease item
        SHOULD be accepted if no other versions match the given specifier.

        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.2.3", "1.3", Version("1.4")]))
        ['1.2.3', '1.3', <Version('1.4')>]
        >>> list(Specifier(">=1.2.3").filter(["1.2", "1.5a1"]))
        ['1.5a1']
        >>> list(Specifier(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(Specifier(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        """

        yielded = False
        found_prereleases = []

        kw = {"prereleases": prereleases if prereleases is not None else True}

        # Attempt to iterate over all the values in the iterable and if any of
        # them match, yield them.
        for version in iterable:
            parsed_version = _coerce_version(version)

            if self.contains(parsed_version, **kw):
                # If our version is a prerelease, and we were not set to allow
                # prereleases, then we'll store it for later in case nothing
                # else matches this specifier.
                if parsed_version.is_prerelease and not (
                    prereleases or self.prereleases
                ):
                    found_prereleases.append(version)
                # Either this is not a prerelease, or we should have been
                # accepting prereleases from the beginning.
                else:
                    yielded = True
                    yield version

        # Now that we've iterated over everything, determine if we've yielded
        # any values, and if we have not and we have any prereleases stored up
        # then we will go ahead and yield the prereleases.
        if not yielded and found_prereleases:
            for version in found_prereleases:
                yield version


_prefix_regex = re.compile(r"^([0-9]+)((?:a|b|c|rc)[0-9]+)$")


def _version_split(version: str) -> list[str]:
    """Split version into components.

    The split components are intended for version comparison. The logic does
    not attempt to retain the original version string, so joining the
    components back with :func:`_version_join` may not produce the original
    version string.
    """
    result: list[str] = []

    epoch, _, rest = version.rpartition("!")
    result.append(epoch or "0")

    for item in rest.split("."):
        match = _prefix_regex.search(item)
        if match:
            result.extend(match.groups())
        else:
            result.append(item)
    return result


def _version_join(components: list[str]) -> str:
    """Join split version components into a version string.

    This function assumes the input came from :func:`_version_split`, where the
    first component must be the epoch (either empty or numeric), and all other
    components numeric.
    """
    epoch, *rest = components
    return f"{epoch}!{'.'.join(rest)}"


def _is_not_suffix(segment: str) -> bool:
    return not any(
        segment.startswith(prefix) for prefix in ("dev", "a", "b", "rc", "post")
    )


def _pad_version(left: list[str], right: list[str]) -> tuple[list[str], list[str]]:
    left_split, right_split = [], []

    # Get the release segment of our versions
    left_split.append(list(itertools.takewhile(lambda x: x.isdigit(), left)))
    right_split.append(list(itertools.takewhile(lambda x: x.isdigit(), right)))

    # Get the rest of our versions
    left_split.append(left[len(left_split[0]) :])
    right_split.append(right[len(right_split[0]) :])

    # Insert our padding
    left_split.insert(1, ["0"] * max(0, len(right_split[0]) - len(left_split[0])))
    right_split.insert(1, ["0"] * max(0, len(left_split[0]) - len(right_split[0])))

    return (
        list(itertools.chain.from_iterable(left_split)),
        list(itertools.chain.from_iterable(right_split)),
    )


class SpecifierSet(BaseSpecifier):
    """This class abstracts handling of a set of version specifiers.

    It can be passed a single specifier (``>=3.0``), a comma-separated list of
    specifiers (``>=3.0,!=3.1``), or no specifier at all.
    """

    def __init__(
        self,
        specifiers: str | Iterable[Specifier] = "",
        prereleases: bool | None = None,
    ) -> None:
        """Initialize a SpecifierSet instance.

        :param specifiers:
            The string representation of a specifier or a comma-separated list of
            specifiers which will be parsed and normalized before use.
            May also be an iterable of ``Specifier`` instances, which will be used
            as is.
        :param prereleases:
            This tells the SpecifierSet if it should accept prerelease versions if
            applicable or not. The default of ``None`` will autodetect it from the
            given specifiers.

        :raises InvalidSpecifier:
            If the given ``specifiers`` are not parseable than this exception will be
            raised.
        """

        if isinstance(specifiers, str):
            # Split on `,` to break each individual specifier into its own item, and
            # strip each item to remove leading/trailing whitespace.
            split_specifiers = [s.strip() for s in specifiers.split(",") if s.strip()]

            # Make each individual specifier a Specifier and save in a frozen set
            # for later.
            self._specs = frozenset(map(Specifier, split_specifiers))
        else:
            # Save the supplied specifiers in a frozen set.
            self._specs = frozenset(specifiers)

        # Store our prereleases value so we can use it later to determine if
        # we accept prereleases or not.
        self._prereleases = prereleases

    @property
    def prereleases(self) -> bool | None:
        # If we have been given an explicit prerelease modifier, then we'll
        # pass that through here.
        if self._prereleases is not None:
            return self._prereleases

        # If we don't have any specifiers, and we don't have a forced value,
        # then we'll just return None since we don't know if this should have
        # pre-releases or not.
        if not self._specs:
            return None

        # Otherwise we'll see if any of the given specifiers accept
        # prereleases, if any of them do we'll return True, otherwise False.
        return any(s.prereleases for s in self._specs)

    @prereleases.setter
    def prereleases(self, value: bool) -> None:
        self._prereleases = value

    def __repr__(self) -> str:
        """A representation of the specifier set that shows all internal state.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> SpecifierSet('>=1.0.0,!=2.0.0')
        <SpecifierSet('!=2.0.0,>=1.0.0')>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=False)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=False)>
        >>> SpecifierSet('>=1.0.0,!=2.0.0', prereleases=True)
        <SpecifierSet('!=2.0.0,>=1.0.0', prereleases=True)>
        """
        pre = (
            f", prereleases={self.prereleases!r}"
            if self._prereleases is not None
            else ""
        )

        return f"<SpecifierSet({str(self)!r}{pre})>"

    def __str__(self) -> str:
        """A string representation of the specifier set that can be round-tripped.

        Note that the ordering of the individual specifiers within the set may not
        match the input string.

        >>> str(SpecifierSet(">=1.0.0,!=1.0.1"))
        '!=1.0.1,>=1.0.0'
        >>> str(SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False))
        '!=1.0.1,>=1.0.0'
        """
        return ",".join(sorted(str(s) for s in self._specs))

    def __hash__(self) -> int:
        return hash(self._specs)

    def __and__(self, other: SpecifierSet | str) -> SpecifierSet:
        """Return a SpecifierSet which is a combination of the two sets.

        :param other: The other object to combine with.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") & '<=2.0.0,!=2.0.1'
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        >>> SpecifierSet(">=1.0.0,!=1.0.1") & SpecifierSet('<=2.0.0,!=2.0.1')
        <SpecifierSet('!=1.0.1,!=2.0.1,<=2.0.0,>=1.0.0')>
        """
        if isinstance(other, str):
            other = SpecifierSet(other)
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        specifier = SpecifierSet()
        specifier._specs = frozenset(self._specs | other._specs)

        if self._prereleases is None and other._prereleases is not None:
            specifier._prereleases = other._prereleases
        elif self._prereleases is not None and other._prereleases is None:
            specifier._prereleases = self._prereleases
        elif self._prereleases == other._prereleases:
            specifier._prereleases = self._prereleases
        else:
            raise ValueError(
                "Cannot combine SpecifierSets with True and False prerelease overrides."
            )

        return specifier

    def __eq__(self, other: object) -> bool:
        """Whether or not the two SpecifierSet-like objects are equal.

        :param other: The other object to check against.

        The value of :attr:`prereleases` is ignored.

        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> (SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False) ==
        ...  SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == ">=1.0.0,!=1.0.1"
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1") == SpecifierSet(">=1.0.0,!=1.0.2")
        False
        """
        if isinstance(other, (str, Specifier)):
            other = SpecifierSet(str(other))
        elif not isinstance(other, SpecifierSet):
            return NotImplemented

        return self._specs == other._specs

    def __len__(self) -> int:
        """Returns the number of specifiers in this specifier set."""
        return len(self._specs)

    def __iter__(self) -> Iterator[Specifier]:
        """
        Returns an iterator over all the underlying :class:`Specifier` instances
        in this specifier set.

        >>> sorted(SpecifierSet(">=1.0.0,!=1.0.1"), key=str)
        [<Specifier('!=1.0.1')>, <Specifier('>=1.0.0')>]
        """
        return iter(self._specs)

    def __contains__(self, item: UnparsedVersion) -> bool:
        """Return whether or not the item is contained in this specifier.

        :param item: The item to check for.

        This is used for the ``in`` operator and behaves the same as
        :meth:`contains` with no ``prereleases`` argument passed.

        >>> "1.2.3" in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> Version("1.2.3") in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> "1.0.1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(
        self,
        item: UnparsedVersion,
        prereleases: bool | None = None,
        installed: bool | None = None,
    ) -> bool:
        """Return whether or not the item is contained in this SpecifierSet.

        :param item:
            The item to check for, which can be a version string or a
            :class:`Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this SpecifierSet. If set to
            ``None`` (the default), it uses :attr:`prereleases` to determine
            whether or not prereleases are allowed.

        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.2.3")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains(Version("1.2.3"))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.0.1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True).contains("1.3.0a1")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1", prereleases=True)
        True
        """
        # Ensure that our item is a Version instance.
        if not isinstance(item, Version):
            item = Version(item)

        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None:
            prereleases = self.prereleases

        # We can determine if we're going to allow pre-releases by looking to
        # see if any of the underlying items supports them. If none of them do
        # and this item is a pre-release then we do not allow it and we can
        # short circuit that here.
        # Note: This means that 1.0.dev1 would not be contained in something
        #       like >=1.0.devabc however it would be in >=1.0.debabc,>0.0.dev0
        if not prereleases and item.is_prerelease:
            return False

        if installed and item.is_prerelease:
            item = Version(item.base_version)

        # We simply dispatch to the underlying specs here to make sure that the
        # given version is contained within all of them.
        # Note: This use of all() here means that an empty set of specifiers
        #       will always return True, this is an explicit design decision.
        return all(s.contains(item, prereleases=prereleases) for s in self._specs)

    def filter(
        self, iterable: Iterable[UnparsedVersionVar], prereleases: bool | None = None
    ) -> Iterator[UnparsedVersionVar]:
        """Filter items in the given iterable, that match the specifiers in this set.

        :param iterable:
            An iterable that can contain version strings and :class:`Version` instances.
            The items in the iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will be intelligently decide whether to allow
            prereleases or not (based on the :attr:`prereleases` attribute, and
            whether the only versions matching are prereleases).

        This method is smarter than just ``filter(SpecifierSet(...).contains, [...])``
        because it implements the rule from :pep:`440` that a prerelease item
        SHOULD be accepted if no other versions match the given specifier.

        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", Version("1.4")]))
        ['1.3', <Version('1.4')>]
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.5a1"]))
        []
        >>> list(SpecifierSet(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']

        An "empty" SpecifierSet will filter items based on the presence of prerelease
        versions in the set.

        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet("").filter(["1.5a1"]))
        ['1.5a1']
        >>> list(SpecifierSet("", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        """
        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None:
            prereleases = self.prereleases

        # If we have any specifiers, then we want to wrap our iterable in the
        # filter method for each one, this will act as a logical AND amongst
        # each specifier.
        if self._specs:
            for spec in self._specs:
                iterable = spec.filter(iterable, prereleases=bool(prereleases))
            return iter(iterable)
        # If we do not have any specifiers, then we need to have a rough filter
        # which will filter out any pre-releases, unless there are no final
        # releases.
        else:
            filtered: list[UnparsedVersionVar] = []
            found_prereleases: list[UnparsedVersionVar] = []

            for item in iterable:
                parsed_version = _coerce_version(item)

                # Store any item which is a pre-release for later unless we've
                # already found a final version or we are accepting prereleases
                if parsed_version.is_prerelease and not prereleases:
                    if not filtered:
                        found_prereleases.append(item)
                else:
                    filtered.append(item)

            # If we've found no items except for pre-releases, then we'll go
            # ahead and use the pre-releases
            if not filtered and found_prereleases and prereleases is None:
                return iter(found_prereleases)

            return iter(filtered)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\support\expected_conditions.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import re
from collections.abc import Iterable
from typing import Any, Callable, List, Literal, Tuple, TypeVar, Union

from selenium.common.exceptions import (
    NoAlertPresentException,
    NoSuchElementException,
    NoSuchFrameException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.remote.webdriver import WebDriver, WebElement

"""
 * Canned "Expected Conditions" which are generally useful within webdriver
 * tests.
"""

D = TypeVar("D")
T = TypeVar("T")

WebDriverOrWebElement = Union[WebDriver, WebElement]


def title_is(title: str) -> Callable[[WebDriver], bool]:
    """An expectation for checking the title of a page.

    Parameters:
    -----------
    title : str
        The expected title, which must be an exact match.

    Returns:
    -------
    boolean : True if the title matches, False otherwise.
    """

    def _predicate(driver: WebDriver):
        return driver.title == title

    return _predicate


def title_contains(title: str) -> Callable[[WebDriver], bool]:
    """An expectation for checking that the title contains a case-sensitive
    substring.

    Parameters:
    -----------
    title : str
        The fragment of title expected.

    Returns:
    -------
    boolean : True when the title matches, False otherwise.
    """

    def _predicate(driver: WebDriver):
        return title in driver.title

    return _predicate


def presence_of_element_located(locator: Tuple[str, str]) -> Callable[[WebDriverOrWebElement], WebElement]:
    """An expectation for checking that an element is present on the DOM of a
    page. This does not necessarily mean that the element is visible.

    Parameters:
    -----------
    locator : Tuple[str, str]
        Used to find the element.

    Returns:
    -------
    WebElement : The WebElement once it is located.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "q")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        return driver.find_element(*locator)

    return _predicate


def url_contains(url: str) -> Callable[[WebDriver], bool]:
    """An expectation for checking that the current url contains a case-
    sensitive substring.

    Parameters:
    -----------
    url : str
        The fragment of url expected.

    Returns:
    -------
    boolean : True when the url matches, False otherwise.
    """

    def _predicate(driver: WebDriver):
        return url in driver.current_url

    return _predicate


def url_matches(pattern: str) -> Callable[[WebDriver], bool]:
    """An expectation for checking the current url.

    Parameters:
    -----------
    pattern : str
        The pattern to match with the current url.

    Returns:
    -------
    boolean : True when the pattern matches, False otherwise.

    Notes:
    ------
    More powerful than url_contains, as it allows for regular expressions.
    """

    def _predicate(driver: WebDriver):
        return re.search(pattern, driver.current_url) is not None

    return _predicate


def url_to_be(url: str) -> Callable[[WebDriver], bool]:
    """An expectation for checking the current url.

    Parameters:
    -----------
    url : str
        The expected url, which must be an exact match.

    Returns:
    -------
    boolean : True when the url matches, False otherwise.
    """

    def _predicate(driver: WebDriver):
        return url == driver.current_url

    return _predicate


def url_changes(url: str) -> Callable[[WebDriver], bool]:
    """An expectation for checking the current url is different than a given
    string.

    Parameters:
    -----------
    url : str
        The expected url, which must not be an exact match.

    Returns:
    -------
    boolean : True when the url does not match, False otherwise
    """

    def _predicate(driver: WebDriver):
        return url != driver.current_url

    return _predicate


def visibility_of_element_located(
    locator: Tuple[str, str],
) -> Callable[[WebDriverOrWebElement], Union[Literal[False], WebElement]]:
    """An expectation for checking that an element is present on the DOM of a
    page and visible. Visibility means that the element is not only displayed
    but also has a height and width that is greater than 0.

    Parameters:
    -----------
    locator : Tuple[str, str]
        Used to find the element.

    Returns:
    -------
    WebElement : The WebElement once it is located and visible.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> element = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, "q")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            return _element_if_visible(driver.find_element(*locator))
        except StaleElementReferenceException:
            return False

    return _predicate


def visibility_of(element: WebElement) -> Callable[[Any], Union[Literal[False], WebElement]]:
    """An expectation for checking that an element, known to be present on the
    DOM of a page, is visible.

    Parameters:
    -----------
    element : WebElement
        The WebElement to check.

    Returns:
    -------
    WebElement : The WebElement once it is visible.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> element = WebDriverWait(driver, 10).until(EC.visibility_of(driver.find_element(By.NAME, "q")))

    Notes:
    ------
    Visibility means that the element is not only displayed but also has
    a height and width that is greater than 0. element is the WebElement
    returns the (same) WebElement once it is visible
    """

    def _predicate(_):
        return _element_if_visible(element)

    return _predicate


def _element_if_visible(element: WebElement, visibility: bool = True) -> Union[Literal[False], WebElement]:
    """An expectation for checking that an element, known to be present on the
    DOM of a page, is of the expected visibility.

    Parameters:
    -----------
    element : WebElement
        The WebElement to check.
    visibility : bool
        The expected visibility of the element.

    Returns:
    -------
    WebElement : The WebElement once it is visible or not visible.
    """
    return element if element.is_displayed() == visibility else False


def presence_of_all_elements_located(locator: Tuple[str, str]) -> Callable[[WebDriverOrWebElement], List[WebElement]]:
    """An expectation for checking that there is at least one element present
    on a web page.

    Parameters:
    -----------
    locator : Tuple[str, str]
        Used to find the element.

    Returns:
    -------
    List[WebElement] : The list of WebElements once they are located.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> elements = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "foo")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        return driver.find_elements(*locator)

    return _predicate


def visibility_of_any_elements_located(locator: Tuple[str, str]) -> Callable[[WebDriverOrWebElement], List[WebElement]]:
    """An expectation for checking that there is at least one element visible
    on a web page.

    Parameters:
    -----------
    locator : Tuple[str, str]
        Used to find the element.

    Returns:
    -------
    List[WebElement] : The list of WebElements once they are located and visible.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> elements = WebDriverWait(driver, 10).until(EC.visibility_of_any_elements_located((By.CLASS_NAME, "foo")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        return [element for element in driver.find_elements(*locator) if _element_if_visible(element)]

    return _predicate


def visibility_of_all_elements_located(
    locator: Tuple[str, str],
) -> Callable[[WebDriverOrWebElement], Union[List[WebElement], Literal[False]]]:
    """An expectation for checking that all elements are present on the DOM of
    a page and visible. Visibility means that the elements are not only
    displayed but also has a height and width that is greater than 0.

    Parameters:
    -----------
    locator : Tuple[str, str]
        Used to find the elements.

    Returns:
    -------
    List[WebElement] : The list of WebElements once they are located and visible.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> elements = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, "foo")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            elements = driver.find_elements(*locator)
            for element in elements:
                if _element_if_visible(element, visibility=False):
                    return False
            return elements
        except StaleElementReferenceException:
            return False

    return _predicate


def text_to_be_present_in_element(locator: Tuple[str, str], text_: str) -> Callable[[WebDriverOrWebElement], bool]:
    """An expectation for checking if the given text is present in the
    specified element.

    Parameters:
    -----------
    locator : Tuple[str, str]
        Used to find the element.
    text_ : str
        The text to be present in the element.

    Returns:
    -------
    boolean : True when the text is present, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_text_in_element = WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.CLASS_NAME, "foo"), "bar")
        )
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            element_text = driver.find_element(*locator).text
            return text_ in element_text
        except StaleElementReferenceException:
            return False

    return _predicate


def text_to_be_present_in_element_value(
    locator: Tuple[str, str], text_: str
) -> Callable[[WebDriverOrWebElement], bool]:
    """An expectation for checking if the given text is present in the
    element's value.

    Parameters:
    -----------
    locator : Tuple[str, str]
        Used to find the element.
    text_ : str
        The text to be present in the element's value.

    Returns:
    -------
    boolean : True when the text is present, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_text_in_element_value = WebDriverWait(driver, 10).until(
    ...     EC.text_to_be_present_in_element_value((By.CLASS_NAME, "foo"), "bar")
    ... )
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            element_text = driver.find_element(*locator).get_attribute("value")
            return text_ in element_text
        except StaleElementReferenceException:
            return False

    return _predicate


def text_to_be_present_in_element_attribute(
    locator: Tuple[str, str], attribute_: str, text_: str
) -> Callable[[WebDriverOrWebElement], bool]:
    """An expectation for checking if the given text is present in the
    element's attribute.

    Parameters:
    -----------
    locator : Tuple[str, str]
        Used to find the element.
    attribute_ : str
        The attribute to check the text in.
    text_ : str
        The text to be present in the element's attribute.

    Returns:
    -------
    boolean : True when the text is present, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_text_in_element_attribute = WebDriverWait(driver, 10).until(
    ...     EC.text_to_be_present_in_element_attribute((By.CLASS_NAME, "foo"), "bar", "baz")
    ... )
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            element_text = driver.find_element(*locator).get_attribute(attribute_)
            if element_text is None:
                return False
            return text_ in element_text
        except StaleElementReferenceException:
            return False

    return _predicate


def frame_to_be_available_and_switch_to_it(
    locator: Union[Tuple[str, str], str, WebElement],
) -> Callable[[WebDriver], bool]:
    """An expectation for checking whether the given frame is available to
    switch to.

    Parameters:
    -----------
    locator : Union[Tuple[str, str], str, WebElement]
        Used to find the frame.

    Returns:
    -------
    boolean : True when the frame is available, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it("frame_name"))

    Notes:
    ------
    If the frame is available it switches the given driver to the
    specified frame.
    """

    def _predicate(driver: WebDriver):
        try:
            if isinstance(locator, Iterable) and not isinstance(locator, str):
                driver.switch_to.frame(driver.find_element(*locator))
            else:
                driver.switch_to.frame(locator)
            return True
        except NoSuchFrameException:
            return False

    return _predicate


def invisibility_of_element_located(
    locator: Union[WebElement, Tuple[str, str]],
) -> Callable[[WebDriverOrWebElement], Union[WebElement, bool]]:
    """An Expectation for checking that an element is either invisible or not
    present on the DOM.

    Parameters:
    -----------
    locator : Union[WebElement, Tuple[str, str]]
        Used to find the element.

    Returns:
    -------
    boolean : True when the element is invisible or not present, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_invisible = WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.CLASS_NAME, "foo")))

    Notes:
    ------
    - In the case of NoSuchElement, returns true because the element is not
    present in DOM. The try block checks if the element is present but is
    invisible.
    - In the case of StaleElementReference, returns true because stale element
    reference implies that element is no longer visible.
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            target = locator
            if not isinstance(target, WebElement):
                target = driver.find_element(*target)
            return _element_if_visible(target, visibility=False)
        except (NoSuchElementException, StaleElementReferenceException):
            # In the case of NoSuchElement, returns true because the element is
            # not present in DOM. The try block checks if the element is present
            # but is invisible.
            # In the case of StaleElementReference, returns true because stale
            # element reference implies that element is no longer visible.
            return True

    return _predicate


def invisibility_of_element(
    element: Union[WebElement, Tuple[str, str]],
) -> Callable[[WebDriverOrWebElement], Union[WebElement, bool]]:
    """An Expectation for checking that an element is either invisible or not
    present on the DOM.

    Parameters:
    -----------
    element : Union[WebElement, Tuple[str, str]]
        Used to find the element.

    Returns:
    -------
    boolean : True when the element is invisible or not present, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_invisible_or_not_present = WebDriverWait(driver, 10).until(
    ...     EC.invisibility_of_element(driver.find_element(By.CLASS_NAME, "foo"))
    ... )
    """
    return invisibility_of_element_located(element)


def element_to_be_clickable(
    mark: Union[WebElement, Tuple[str, str]],
) -> Callable[[WebDriverOrWebElement], Union[Literal[False], WebElement]]:
    """An Expectation for checking an element is visible and enabled such that
    you can click it.

    Parameters:
    -----------
    mark : Union[WebElement, Tuple[str, str]]
        Used to find the element.

    Returns:
    -------
    WebElement : The WebElement once it is located and clickable.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "foo")))
    """

    # renamed argument to 'mark', to indicate that both locator
    # and WebElement args are valid
    def _predicate(driver: WebDriverOrWebElement):
        target = mark
        if not isinstance(target, WebElement):  # if given locator instead of WebElement
            target = driver.find_element(*target)  # grab element at locator
        element = visibility_of(target)(driver)
        if element and element.is_enabled():
            return element
        return False

    return _predicate


def staleness_of(element: WebElement) -> Callable[[Any], bool]:
    """Wait until an element is no longer attached to the DOM.

    Parameters:
    -----------
    element : WebElement
        The element to wait for.

    Returns:
    -------
    boolean : False if the element is still attached to the DOM, true otherwise.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_element_stale = WebDriverWait(driver, 10).until(EC.staleness_of(driver.find_element(By.CLASS_NAME, "foo")))
    """

    def _predicate(_):
        try:
            # Calling any method forces a staleness check
            element.is_enabled()
            return False
        except StaleElementReferenceException:
            return True

    return _predicate


def element_to_be_selected(element: WebElement) -> Callable[[Any], bool]:
    """An expectation for checking the selection is selected.

    Parameters:
    -----------
    element : WebElement
        The WebElement to check.

    Returns:
    -------
    boolean : True if the element is selected, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_selected = WebDriverWait(driver, 10).until(EC.element_to_be_selected(driver.find_element(
            By.CLASS_NAME, "foo"))
        )
    """

    def _predicate(_):
        return element.is_selected()

    return _predicate


def element_located_to_be_selected(locator: Tuple[str, str]) -> Callable[[WebDriverOrWebElement], bool]:
    """An expectation for the element to be located is selected.

    Parameters:
    -----------
    locator : Tuple[str, str]
        Used to find the element.

    Returns:
    -------
    boolean : True if the element is selected, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_selected = WebDriverWait(driver, 10).until(EC.element_located_to_be_selected((By.CLASS_NAME, "foo")))
    """

    def _predicate(driver: WebDriverOrWebElement):
        return driver.find_element(*locator).is_selected()

    return _predicate


def element_selection_state_to_be(element: WebElement, is_selected: bool) -> Callable[[Any], bool]:
    """An expectation for checking if the given element is selected.

    Parameters:
    -----------
    element : WebElement
        The WebElement to check.
    is_selected : bool

    Returns:
    -------
    boolean : True if the element's selection state is the same as is_selected

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_selected = WebDriverWait(driver, 10).until(
    ...     EC.element_selection_state_to_be(driver.find_element(By.CLASS_NAME, "foo"), True)
    ... )
    """

    def _predicate(_):
        return element.is_selected() == is_selected

    return _predicate


def element_located_selection_state_to_be(
    locator: Tuple[str, str], is_selected: bool
) -> Callable[[WebDriverOrWebElement], bool]:
    """An expectation to locate an element and check if the selection state
    specified is in that state.

    Parameters:
    -----------
    locator : Tuple[str, str]
        Used to find the element.
    is_selected : bool

    Returns:
    -------
    boolean : True if the element's selection state is the same as is_selected

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_selected = WebDriverWait(driver, 10).until(EC.element_located_selection_state_to_be(
            (By.CLASS_NAME, "foo"), True)
        )
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            element = driver.find_element(*locator)
            return element.is_selected() == is_selected
        except StaleElementReferenceException:
            return False

    return _predicate


def number_of_windows_to_be(num_windows: int) -> Callable[[WebDriver], bool]:
    """An expectation for the number of windows to be a certain value.

    Parameters:
    -----------
    num_windows : int
        The expected number of windows.

    Returns:
    -------
    boolean : True when the number of windows matches, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_number_of_windows = WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
    """

    def _predicate(driver: WebDriver):
        return len(driver.window_handles) == num_windows

    return _predicate


def new_window_is_opened(current_handles: List[str]) -> Callable[[WebDriver], bool]:
    """An expectation that a new window will be opened and have the number of
    windows handles increase.

    Parameters:
    -----------
    current_handles : List[str]
        The current window handles.

    Returns:
    -------
    boolean : True when a new window is opened, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.support.ui import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_new_window_opened = WebDriverWait(driver, 10).until(EC.new_window_is_opened(driver.window_handles))
    """

    def _predicate(driver: WebDriver):
        return len(driver.window_handles) > len(current_handles)

    return _predicate


def alert_is_present() -> Callable[[WebDriver], Union[Alert, Literal[False]]]:
    """An expectation for checking if an alert is currently present and
    switching to it.

    Returns:
    -------
    Alert : The Alert once it is located.

    Example:
    --------
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> alert = WebDriverWait(driver, 10).until(EC.alert_is_present())

    Notes:
    ------
    If the alert is present it switches the given driver to it.
    """

    def _predicate(driver: WebDriver):
        try:
            return driver.switch_to.alert
        except NoAlertPresentException:
            return False

    return _predicate


def element_attribute_to_include(locator: Tuple[str, str], attribute_: str) -> Callable[[WebDriverOrWebElement], bool]:
    """An expectation for checking if the given attribute is included in the
    specified element.

    Parameters:
    -----------
    locator : Tuple[str, str]
        Used to find the element.
    attribute_ : str
        The attribute to check.

    Returns:
    -------
    boolean : True when the attribute is included, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> is_attribute_in_element = WebDriverWait(driver, 10).until(
    ...     EC.element_attribute_to_include((By.CLASS_NAME, "foo"), "bar")
    ... )
    """

    def _predicate(driver: WebDriverOrWebElement):
        try:
            element_attribute = driver.find_element(*locator).get_attribute(attribute_)
            return element_attribute is not None
        except StaleElementReferenceException:
            return False

    return _predicate


def any_of(*expected_conditions: Callable[[D], T]) -> Callable[[D], Union[Literal[False], T]]:
    """An expectation that any of multiple expected conditions is true.

    Parameters:
    -----------
    expected_conditions : Callable[[D], T]
        The list of expected conditions to check.

    Returns:
    -------
    T : The result of the first matching condition, or False if none do.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> element = WebDriverWait(driver, 10).until(
    ... EC.any_of(EC.presence_of_element_located((By.NAME, "q"),
    ... EC.visibility_of_element_located((By.NAME, "q"))))

    Notes:
    ------
    Equivalent to a logical 'OR'. Returns results of the first matching
    condition, or False if none do.
    """

    def any_of_condition(driver: D):
        for expected_condition in expected_conditions:
            try:
                result = expected_condition(driver)
                if result:
                    return result
            except WebDriverException:
                pass
        return False

    return any_of_condition


def all_of(
    *expected_conditions: Callable[[D], Union[T, Literal[False]]],
) -> Callable[[D], Union[List[T], Literal[False]]]:
    """An expectation that all of multiple expected conditions is true.

    Parameters:
    -----------
    expected_conditions : Callable[[D], Union[T, Literal[False]]]
        The list of expected conditions to check.

    Returns:
    -------
    List[T] : The results of all the matching conditions, or False if any do not.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> elements = WebDriverWait(driver, 10).until(
    ... EC.all_of(EC.presence_of_element_located((By.NAME, "q"),
    ... EC.visibility_of_element_located((By.NAME, "q"))))

    Notes:
    ------
    Equivalent to a logical 'AND'.
    Returns: When any ExpectedCondition is not met: False.
    When all ExpectedConditions are met: A List with each ExpectedCondition's return value.
    """

    def all_of_condition(driver: D):
        results: List[T] = []
        for expected_condition in expected_conditions:
            try:
                result = expected_condition(driver)
                if not result:
                    return False
                results.append(result)
            except WebDriverException:
                return False
        return results

    return all_of_condition


def none_of(*expected_conditions: Callable[[D], Any]) -> Callable[[D], bool]:
    """An expectation that none of 1 or multiple expected conditions is true.

    Parameters:
    -----------
    expected_conditions : Callable[[D], Any]
        The list of expected conditions to check.

    Returns:
    -------
    boolean : True if none of the conditions are true, False otherwise.

    Example:
    --------
    >>> from selenium.webdriver.common.by import By
    >>> from selenium.webdriver.support.ui import WebDriverWait
    >>> from selenium.webdriver.support import expected_conditions as EC
    >>> element = WebDriverWait(driver, 10).until(
    ... EC.none_of(EC.presence_of_element_located((By.NAME, "q"),
    ... EC.visibility_of_element_located((By.NAME, "q"))))

    Notes:
    ------
    Equivalent to a logical 'NOT-OR'. Returns a Boolean
    """

    def none_of_condition(driver: D):
        for expected_condition in expected_conditions:
            try:
                result = expected_condition(driver)
                if result:
                    return False
            except WebDriverException:
                pass
        return True

    return none_of_condition

# === NexusCore/openenv\Lib\site-packages\win32com\makegw\makegwparse.py ===
"""Utilities for makegw - Parse a header file to build an interface

This module contains the core code for parsing a header file describing a
COM interface, and building it into an "Interface" structure.

Each Interface has methods, and each method has arguments.

Each argument knows how to use Py_BuildValue or Py_ParseTuple to
exchange itself with Python.

See the @win32com.makegw@ module for information in building a COM
interface
"""

from __future__ import annotations

import re
import traceback


class error_not_found(Exception):
    def __init__(self, msg="The requested item could not be found"):
        super().__init__(msg)


class error_not_supported(Exception):
    def __init__(self, msg="The required functionality is not supported"):
        super().__init__(msg)


VERBOSE = 0
DEBUG = 0

## NOTE : For interfaces as params to work correctly, you must
## make sure any PythonCOM extensions which expose the interface are loaded
## before generating.


class ArgFormatter:
    """An instance for a specific type of argument. Knows how to convert itself"""

    def __init__(self, arg, builtinIndirection, declaredIndirection=0):
        # print("init:", arg.name, builtinIndirection, declaredIndirection, arg.indirectionLevel)
        self.arg = arg
        self.builtinIndirection = builtinIndirection
        self.declaredIndirection = declaredIndirection
        self.gatewayMode = 0

    def _IndirectPrefix(self, indirectionFrom, indirectionTo):
        """Given the indirection level I was declared at (0=Normal, 1=*, 2=**)
        return a string prefix so I can pass to a function with the
        required indirection (where the default is the indirection of the method's param.

        eg, assuming my arg has indirection level of 2, if this function was passed 1
        it would return "&", so that a variable declared with indirection of 1
        can be prefixed with this to turn it into the indirection level required of 2
        """
        dif = indirectionFrom - indirectionTo
        if dif == 0:
            return ""
        elif dif == -1:
            return "&"
        elif dif == 1:
            return "*"
        else:
            return "?? (%d)" % (dif,)
            raise error_not_supported("Can't indirect this far - please fix me :-)")

    def GetIndirectedArgName(self, indirectFrom, indirectionTo):
        # print(
        #     "get:",
        #     self.arg.name,
        #     indirectFrom,
        #     self._GetDeclaredIndirection() + self.builtinIndirection,
        #     indirectionTo,
        #     self.arg.indirectionLevel,
        # )

        if indirectFrom is None:
            ### ACK! this does not account for [in][out] variables.
            ### when this method is called, we need to know which
            indirectFrom = self._GetDeclaredIndirection() + self.builtinIndirection

        return self._IndirectPrefix(indirectFrom, indirectionTo) + self.arg.name

    def GetBuildValueArg(self):
        "Get the argument to be passes to Py_BuildValue"
        return self.arg.name

    def GetParseTupleArg(self):
        "Get the argument to be passed to PyArg_ParseTuple"
        if self.gatewayMode:
            # use whatever they were declared with
            return self.GetIndirectedArgName(None, 1)
        # local declarations have just their builtin indirection
        return self.GetIndirectedArgName(self.builtinIndirection, 1)

    def GetInterfaceCppObjectInfo(self):
        """Provide information about the C++ object used.

        Simple variables (such as integers) can declare their type (eg an integer)
        and use it as the target of both PyArg_ParseTuple and the COM function itself.

        More complex types require a PyObject * declared as the target of PyArg_ParseTuple,
        then some conversion routine to the C++ object which is actually passed to COM.

        This method provides the name, and optionally the type of that C++ variable.
        If the type if provided, the caller will likely generate a variable declaration.
        The name must always be returned.

        Result is a tuple of (variableName, [DeclareType|None|""])
        """

        # the first return element is the variable to be passed as
        # 	 an argument to an interface method. the variable was
        # 	 declared with only its builtin indirection level. when
        # 	 we pass it, we'll need to pass in whatever amount of
        # 	 indirection was applied (plus the builtin amount)
        # the second return element is the variable declaration; it
        # 	 should simply be builtin indirection
        return (
            self.GetIndirectedArgName(
                self.builtinIndirection,
                self.arg.indirectionLevel + self.builtinIndirection,
            ),
            f"{self.GetUnconstType()} {self.arg.name}",
        )

    def GetInterfaceArgCleanup(self):
        "Return cleanup code for C++ args passed to the interface method."
        if DEBUG:
            return "/* GetInterfaceArgCleanup output goes here: %s */\n" % self.arg.name
        else:
            return ""

    def GetInterfaceArgCleanupGIL(self):
        """Return cleanup code for C++ args passed to the interface
        method that must be executed with the GIL held"""
        if DEBUG:
            return (
                "/* GetInterfaceArgCleanup (GIL held) output goes here: %s */\n"
                % self.arg.name
            )
        else:
            return ""

    def GetUnconstType(self):
        return self.arg.unc_type

    def SetGatewayMode(self):
        self.gatewayMode = 1

    def _GetDeclaredIndirection(self):
        return self.arg.indirectionLevel
        print("declared:", self.arg.name, self.gatewayMode)
        if self.gatewayMode:
            return self.arg.indirectionLevel
        else:
            return self.declaredIndirection

    def DeclareParseArgTupleInputConverter(self):
        "Declare the variable used as the PyArg_ParseTuple param for a gateway"
        # Only declare it??
        # if self.arg.indirectionLevel==0:
        # 	return "\t%s %s;\n" % (self.arg.type, self.arg.name)
        # else:
        if DEBUG:
            return (
                "/* Declare ParseArgTupleInputConverter goes here: %s */\n"
                % self.arg.name
            )
        else:
            return ""

    def GetParsePostCode(self):
        "Get a string of C++ code to be executed after (ie, to finalise) the PyArg_ParseTuple conversion"
        if DEBUG:
            return "/* GetParsePostCode code goes here: %s */\n" % self.arg.name
        else:
            return ""

    def GetBuildForInterfacePreCode(self):
        "Get a string of C++ code to be executed before (ie, to initialise) the Py_BuildValue conversion for Interfaces"
        if DEBUG:
            return "/* GetBuildForInterfacePreCode goes here: %s */\n" % self.arg.name
        else:
            return ""

    def GetBuildForGatewayPreCode(self):
        "Get a string of C++ code to be executed before (ie, to initialise) the Py_BuildValue conversion for Gateways"
        s = self.GetBuildForInterfacePreCode()  # Usually the same
        if DEBUG:
            if s[:4] == "/* G":
                s = "/* GetBuildForGatewayPreCode goes here: %s */\n" % self.arg.name
        return s

    def GetBuildForInterfacePostCode(self):
        "Get a string of C++ code to be executed after (ie, to finalise) the Py_BuildValue conversion for Interfaces"
        if DEBUG:
            return "/* GetBuildForInterfacePostCode goes here: %s */\n" % self.arg.name
        return ""

    def GetBuildForGatewayPostCode(self):
        "Get a string of C++ code to be executed after (ie, to finalise) the Py_BuildValue conversion for Gateways"
        s = self.GetBuildForInterfacePostCode()  # Usually the same
        if DEBUG:
            if s[:4] == "/* G":
                s = "/* GetBuildForGatewayPostCode goes here: %s */\n" % self.arg.name
        return s

    def GetAutoduckString(self):
        return "// @pyparm {}|{}||Description for {}".format(
            self._GetPythonTypeDesc(),
            self.arg.name,
            self.arg.name,
        )

    def _GetPythonTypeDesc(self):
        "Returns a string with the description of the type. Used for doco purposes"
        return None

    def NeedUSES_CONVERSION(self):
        "Determines if this arg forces a USES_CONVERSION macro"
        return 0


# Special formatter for floats since they're smaller than Python floats.
class ArgFormatterFloat(ArgFormatter):
    def GetFormatChar(self):
        return "f"

    def DeclareParseArgTupleInputConverter(self):
        # Declare a double variable
        return "\tdouble dbl%s;\n" % self.arg.name

    def GetParseTupleArg(self):
        return "&dbl" + self.arg.name

    def _GetPythonTypeDesc(self):
        return "float"

    def GetBuildValueArg(self):
        return "&dbl" + self.arg.name

    def GetBuildForInterfacePreCode(self):
        return "\tdbl" + self.arg.name + " = " + self.arg.name + ";\n"

    def GetBuildForGatewayPreCode(self):
        return (
            "\tdbl%s = " % self.arg.name
            + self._IndirectPrefix(self._GetDeclaredIndirection(), 0)
            + self.arg.name
            + ";\n"
        )

    def GetParsePostCode(self):
        s = "\t"
        if self.gatewayMode:
            s += self._IndirectPrefix(self._GetDeclaredIndirection(), 0)
        s += self.arg.name
        s += " = (float)dbl%s;\n" % self.arg.name
        return s


# Special formatter for Shorts because they're
# a different size than Python ints!
class ArgFormatterShort(ArgFormatter):
    def GetFormatChar(self):
        return "i"

    def DeclareParseArgTupleInputConverter(self):
        # Declare a double variable
        return "\tINT i%s;\n" % self.arg.name

    def GetParseTupleArg(self):
        return "&i" + self.arg.name

    def _GetPythonTypeDesc(self):
        return "int"

    def GetBuildValueArg(self):
        return "&i" + self.arg.name

    def GetBuildForInterfacePreCode(self):
        return "\ti" + self.arg.name + " = " + self.arg.name + ";\n"

    def GetBuildForGatewayPreCode(self):
        return (
            "\ti%s = " % self.arg.name
            + self._IndirectPrefix(self._GetDeclaredIndirection(), 0)
            + self.arg.name
            + ";\n"
        )

    def GetParsePostCode(self):
        s = "\t"
        if self.gatewayMode:
            s += self._IndirectPrefix(self._GetDeclaredIndirection(), 0)
        s += self.arg.name
        s += " = i%s;\n" % self.arg.name
        return s


# for types which are 64bits on AMD64 - eg, HWND
class ArgFormatterLONG_PTR(ArgFormatter):
    def GetFormatChar(self):
        return "O"

    def DeclareParseArgTupleInputConverter(self):
        # Declare a PyObject variable
        return "\tPyObject *ob%s;\n" % self.arg.name

    def GetParseTupleArg(self):
        return "&ob" + self.arg.name

    def _GetPythonTypeDesc(self):
        return "int/long"

    def GetBuildValueArg(self):
        return "ob" + self.arg.name

    def GetBuildForInterfacePostCode(self):
        return "\tPy_XDECREF(ob%s);\n" % self.arg.name

    def GetParsePostCode(self):
        return "\tif (bPythonIsHappy && !PyWinLong_AsULONG_PTR(ob{}, (ULONG_PTR *){})) bPythonIsHappy = FALSE;\n".format(
            self.arg.name, self.GetIndirectedArgName(None, 2)
        )

    def GetBuildForInterfacePreCode(self):
        notdirected = self.GetIndirectedArgName(None, 1)
        return f"\tob{self.arg.name} = PyWinObject_FromULONG_PTR({notdirected});\n"

    def GetBuildForGatewayPostCode(self):
        return "\tPy_XDECREF(ob%s);\n" % self.arg.name


class ArgFormatterPythonCOM(ArgFormatter):
    """An arg formatter for types exposed in the PythonCOM module"""

    def GetFormatChar(self):
        return "O"

    # def GetInterfaceCppObjectInfo(self):
    # 	return ArgFormatter.GetInterfaceCppObjectInfo(self)[0], \
    # 		"%s %s%s" % (self.arg.unc_type, "*" * self._GetDeclaredIndirection(), self.arg.name)
    def DeclareParseArgTupleInputConverter(self):
        # Declare a PyObject variable
        return "\tPyObject *ob%s;\n" % self.arg.name

    def GetParseTupleArg(self):
        return "&ob" + self.arg.name

    def _GetPythonTypeDesc(self):
        return "<o Py%s>" % self.arg.type

    def GetBuildValueArg(self):
        return "ob" + self.arg.name

    def GetBuildForInterfacePostCode(self):
        return "\tPy_XDECREF(ob%s);\n" % self.arg.name


class ArgFormatterBSTR(ArgFormatterPythonCOM):
    def _GetPythonTypeDesc(self):
        return "<o unicode>"

    def GetParsePostCode(self):
        return "\tif (bPythonIsHappy && !PyWinObject_AsBstr(ob{}, {})) bPythonIsHappy = FALSE;\n".format(
            self.arg.name, self.GetIndirectedArgName(None, 2)
        )

    def GetBuildForInterfacePreCode(self):
        notdirected = self.GetIndirectedArgName(None, 1)
        return f"\tob{self.arg.name} = MakeBstrToObj({notdirected});\n"

    def GetBuildForInterfacePostCode(self):
        return (
            f"\tSysFreeString({self.arg.name});\n"
            + ArgFormatterPythonCOM.GetBuildForInterfacePostCode(self)
        )

    def GetBuildForGatewayPostCode(self):
        return "\tPy_XDECREF(ob%s);\n" % self.arg.name


class ArgFormatterOLECHAR(ArgFormatterPythonCOM):
    def _GetPythonTypeDesc(self):
        return "<o unicode>"

    def GetUnconstType(self):
        if self.arg.type[:3] == "LPC":
            return self.arg.type[:2] + self.arg.type[3:]
        else:
            return self.arg.unc_type

    def GetParsePostCode(self):
        return "\tif (bPythonIsHappy && !PyWinObject_AsBstr(ob{}, {})) bPythonIsHappy = FALSE;\n".format(
            self.arg.name, self.GetIndirectedArgName(None, 2)
        )

    def GetInterfaceArgCleanup(self):
        return "\tSysFreeString(%s);\n" % self.GetIndirectedArgName(None, 1)

    def GetBuildForInterfacePreCode(self):
        # the variable was declared with just its builtin indirection
        notdirected = self.GetIndirectedArgName(self.builtinIndirection, 1)
        return f"\tob{self.arg.name} = MakeOLECHARToObj({notdirected});\n"

    def GetBuildForInterfacePostCode(self):
        # memory returned into an OLECHAR should be freed
        return (
            f"\tCoTaskMemFree({self.arg.name});\n"
            + ArgFormatterPythonCOM.GetBuildForInterfacePostCode(self)
        )

    def GetBuildForGatewayPostCode(self):
        return "\tPy_XDECREF(ob%s);\n" % self.arg.name


class ArgFormatterTCHAR(ArgFormatterPythonCOM):
    def _GetPythonTypeDesc(self):
        return "string/<o unicode>"

    def GetUnconstType(self):
        if self.arg.type[:3] == "LPC":
            return self.arg.type[:2] + self.arg.type[3:]
        else:
            return self.arg.unc_type

    def GetParsePostCode(self):
        return "\tif (bPythonIsHappy && !PyWinObject_AsTCHAR(ob{}, {})) bPythonIsHappy = FALSE;\n".format(
            self.arg.name, self.GetIndirectedArgName(None, 2)
        )

    def GetInterfaceArgCleanup(self):
        return "\tPyWinObject_FreeTCHAR(%s);\n" % self.GetIndirectedArgName(None, 1)

    def GetBuildForInterfacePreCode(self):
        # the variable was declared with just its builtin indirection
        notdirected = self.GetIndirectedArgName(self.builtinIndirection, 1)
        return f"\tob{self.arg.name} = PyWinObject_FromTCHAR({notdirected});\n"

    def GetBuildForInterfacePostCode(self):
        return "// ??? - TCHAR post code\n"

    def GetBuildForGatewayPostCode(self):
        return "\tPy_XDECREF(ob%s);\n" % self.arg.name


class ArgFormatterIID(ArgFormatterPythonCOM):
    def _GetPythonTypeDesc(self):
        return "<o PyIID>"

    def GetParsePostCode(self):
        return "\tif (!PyWinObject_AsIID(ob{}, &{})) bPythonIsHappy = FALSE;\n".format(
            self.arg.name,
            self.arg.name,
        )

    def GetBuildForInterfacePreCode(self):
        # 		notdirected = self.GetIndirectedArgName(self.arg.indirectionLevel, 0)
        notdirected = self.GetIndirectedArgName(None, 0)
        return f"\tob{self.arg.name} = PyWinObject_FromIID({notdirected});\n"

    def GetInterfaceCppObjectInfo(self):
        return self.arg.name, "IID %s" % (self.arg.name)


class ArgFormatterTime(ArgFormatterPythonCOM):
    def __init__(self, arg, builtinIndirection, declaredIndirection=0):
        # we don't want to declare LPSYSTEMTIME / LPFILETIME objects
        if arg.indirectionLevel == 0 and arg.unc_type[:2] == "LP":
            arg.unc_type = arg.unc_type[2:]
            # reduce the builtin and increment the declaration
            arg.indirectionLevel += 1
            builtinIndirection = 0
        ArgFormatterPythonCOM.__init__(
            self, arg, builtinIndirection, declaredIndirection
        )

    def _GetPythonTypeDesc(self):
        return "<o PyDateTime>"

    def GetParsePostCode(self):
        # variable was declared with only the builtinIndirection
        ### NOTE: this is an [in] ... so use only builtin
        return '\tif (!PyTime_Check(ob{})) {{\n\t\tPyErr_SetString(PyExc_TypeError, "The argument must be a PyTime object");\n\t\tbPythonIsHappy = FALSE;\n\t}}\n\tif (!((PyTime *)ob{})->GetTime({})) bPythonIsHappy = FALSE;\n'.format(
            self.arg.name,
            self.arg.name,
            self.GetIndirectedArgName(self.builtinIndirection, 1),
        )

    def GetBuildForInterfacePreCode(self):
        ### use just the builtinIndirection again...
        notdirected = self.GetIndirectedArgName(self.builtinIndirection, 0)
        return f"\tob{self.arg.name} = new PyTime({notdirected});\n"

    def GetBuildForInterfacePostCode(self):
        ### hack to determine if we need to free stuff
        ret = ""
        if self.builtinIndirection + self.arg.indirectionLevel > 1:
            # memory returned into an OLECHAR should be freed
            ret = "\tCoTaskMemFree(%s);\n" % self.arg.name
        return ret + ArgFormatterPythonCOM.GetBuildForInterfacePostCode(self)


class ArgFormatterSTATSTG(ArgFormatterPythonCOM):
    def _GetPythonTypeDesc(self):
        return "<o STATSTG>"

    def GetParsePostCode(self):
        return "\tif (!PyCom_PyObjectAsSTATSTG(ob{}, {}, 0/*flags*/)) bPythonIsHappy = FALSE;\n".format(
            self.arg.name, self.GetIndirectedArgName(None, 1)
        )

    def GetBuildForInterfacePreCode(self):
        notdirected = self.GetIndirectedArgName(None, 1)
        return "\tob{} = PyCom_PyObjectFromSTATSTG({});\n\t// STATSTG doco says our responsibility to free\n\tif (({}).pwcsName) CoTaskMemFree(({}).pwcsName);\n".format(
            self.arg.name,
            self.GetIndirectedArgName(None, 1),
            notdirected,
            notdirected,
        )


class ArgFormatterGeneric(ArgFormatterPythonCOM):
    def _GetPythonTypeDesc(self):
        return "<o %s>" % self.arg.type

    def GetParsePostCode(self):
        return "\tif (!PyObject_As{}(ob{}, &{}) bPythonIsHappy = FALSE;\n".format(
            self.arg.type,
            self.arg.name,
            self.GetIndirectedArgName(None, 1),
        )

    def GetInterfaceArgCleanup(self):
        return f"\tPyObject_Free{self.arg.type}({self.arg.name});\n"

    def GetBuildForInterfacePreCode(self):
        notdirected = self.GetIndirectedArgName(None, 1)
        return "\tob{} = PyObject_From{}({});\n".format(
            self.arg.name,
            self.arg.type,
            self.GetIndirectedArgName(None, 1),
        )


class ArgFormatterIDLIST(ArgFormatterPythonCOM):
    def _GetPythonTypeDesc(self):
        return "<o PyIDL>"

    def GetParsePostCode(self):
        return "\tif (bPythonIsHappy && !PyObject_AsPIDL(ob{}, &{})) bPythonIsHappy = FALSE;\n".format(
            self.arg.name, self.GetIndirectedArgName(None, 1)
        )

    def GetInterfaceArgCleanup(self):
        return f"\tPyObject_FreePIDL({self.arg.name});\n"

    def GetBuildForInterfacePreCode(self):
        notdirected = self.GetIndirectedArgName(None, 1)
        return "\tob{} = PyObject_FromPIDL({});\n".format(
            self.arg.name,
            self.GetIndirectedArgName(None, 1),
        )


class ArgFormatterHANDLE(ArgFormatterPythonCOM):
    def _GetPythonTypeDesc(self):
        return "<o PyHANDLE>"

    def GetParsePostCode(self):
        return "\tif (!PyWinObject_AsHANDLE(ob{}, &{}, FALSE) bPythonIsHappy = FALSE;\n".format(
            self.arg.name, self.GetIndirectedArgName(None, 1)
        )

    def GetBuildForInterfacePreCode(self):
        notdirected = self.GetIndirectedArgName(None, 1)
        return "\tob{} = PyWinObject_FromHANDLE({});\n".format(
            self.arg.name,
            self.GetIndirectedArgName(None, 0),
        )


class ArgFormatterLARGE_INTEGER(ArgFormatterPythonCOM):
    def GetKeyName(self):
        return "LARGE_INTEGER"

    def _GetPythonTypeDesc(self):
        return "<o %s>" % self.GetKeyName()

    def GetParsePostCode(self):
        return "\tif (!PyWinObject_As{}(ob{}, {})) bPythonIsHappy = FALSE;\n".format(
            self.GetKeyName(),
            self.arg.name,
            self.GetIndirectedArgName(None, 1),
        )

    def GetBuildForInterfacePreCode(self):
        notdirected = self.GetIndirectedArgName(None, 0)
        return "\tob{} = PyWinObject_From{}({});\n".format(
            self.arg.name,
            self.GetKeyName(),
            notdirected,
        )


class ArgFormatterULARGE_INTEGER(ArgFormatterLARGE_INTEGER):
    def GetKeyName(self):
        return "ULARGE_INTEGER"


class ArgFormatterInterface(ArgFormatterPythonCOM):
    def GetInterfaceCppObjectInfo(self):
        return self.GetIndirectedArgName(
            1, self.arg.indirectionLevel
        ), "{} * {}".format(
            self.GetUnconstType(),
            self.arg.name,
        )

    def GetParsePostCode(self):
        # This gets called for out params in gateway mode
        if self.gatewayMode:
            sArg = self.GetIndirectedArgName(None, 2)
        else:
            # vs. in params for interface mode.
            sArg = self.GetIndirectedArgName(1, 2)
        return "\tif (bPythonIsHappy && !PyCom_InterfaceFromPyInstanceOrObject(ob{}, IID_{}, (void **){}, TRUE /* bNoneOK */))\n\t\t bPythonIsHappy = FALSE;\n".format(
            self.arg.name, self.arg.type, sArg
        )

    def GetBuildForInterfacePreCode(self):
        return "\tob{} = PyCom_PyObjectFromIUnknown({}, IID_{}, FALSE);\n".format(
            self.arg.name,
            self.arg.name,
            self.arg.type,
        )

    def GetBuildForGatewayPreCode(self):
        sPrefix = self._IndirectPrefix(self._GetDeclaredIndirection(), 1)
        return "\tob{} = PyCom_PyObjectFromIUnknown({}{}, IID_{}, TRUE);\n".format(
            self.arg.name,
            sPrefix,
            self.arg.name,
            self.arg.type,
        )

    def GetInterfaceArgCleanup(self):
        return f"\tif ({self.arg.name}) {self.arg.name}->Release();\n"


class ArgFormatterVARIANT(ArgFormatterPythonCOM):
    def GetParsePostCode(self):
        return "\tif ( !PyCom_VariantFromPyObject(ob{}, {}) )\n\t\tbPythonIsHappy = FALSE;\n".format(
            self.arg.name, self.GetIndirectedArgName(None, 1)
        )

    def GetBuildForGatewayPreCode(self):
        notdirected = self.GetIndirectedArgName(None, 1)
        return f"\tob{self.arg.name} = PyCom_PyObjectFromVariant({notdirected});\n"

    def GetBuildForGatewayPostCode(self):
        return "\tPy_XDECREF(ob%s);\n" % self.arg.name

        # Key :		, Python Type Description, ParseTuple format char


ConvertSimpleTypes = {
    "BOOL": ("BOOL", "int", "i"),
    "UINT": ("UINT", "int", "i"),
    "BYTE": ("BYTE", "int", "i"),
    "INT": ("INT", "int", "i"),
    "DWORD": ("DWORD", "int", "l"),
    "HRESULT": ("HRESULT", "int", "l"),
    "ULONG": ("ULONG", "int", "l"),
    "LONG": ("LONG", "int", "l"),
    "int": ("int", "int", "i"),
    "long": ("long", "int", "l"),
    "DISPID": ("DISPID", "long", "l"),
    "APPBREAKFLAGS": ("int", "int", "i"),
    "BREAKRESUMEACTION": ("int", "int", "i"),
    "ERRORRESUMEACTION": ("int", "int", "i"),
    "BREAKREASON": ("int", "int", "i"),
    "BREAKPOINT_STATE": ("int", "int", "i"),
    "BREAKRESUME_ACTION": ("int", "int", "i"),
    "SOURCE_TEXT_ATTR": ("int", "int", "i"),
    "TEXT_DOC_ATTR": ("int", "int", "i"),
    "QUERYOPTION": ("int", "int", "i"),
    "PARSEACTION": ("int", "int", "i"),
}


class ArgFormatterSimple(ArgFormatter):
    """An arg formatter for simple integer etc types"""

    def GetFormatChar(self):
        return ConvertSimpleTypes[self.arg.type][2]

    def _GetPythonTypeDesc(self):
        return ConvertSimpleTypes[self.arg.type][1]


AllConverters: dict[
    str, tuple[type[ArgFormatter], int, int] | tuple[type[ArgFormatter], int]
] = {
    "const OLECHAR": (ArgFormatterOLECHAR, 0, 1),
    "WCHAR": (ArgFormatterOLECHAR, 0, 1),
    "OLECHAR": (ArgFormatterOLECHAR, 0, 1),
    "LPCOLESTR": (ArgFormatterOLECHAR, 1, 1),
    "LPOLESTR": (ArgFormatterOLECHAR, 1, 1),
    "LPCWSTR": (ArgFormatterOLECHAR, 1, 1),
    "LPWSTR": (ArgFormatterOLECHAR, 1, 1),
    "LPCSTR": (ArgFormatterOLECHAR, 1, 1),
    "LPTSTR": (ArgFormatterTCHAR, 1, 1),
    "LPCTSTR": (ArgFormatterTCHAR, 1, 1),
    "HANDLE": (ArgFormatterHANDLE, 0),
    "BSTR": (ArgFormatterBSTR, 1, 0),
    "const IID": (ArgFormatterIID, 0),
    "CLSID": (ArgFormatterIID, 0),
    "IID": (ArgFormatterIID, 0),
    "GUID": (ArgFormatterIID, 0),
    "const GUID": (ArgFormatterIID, 0),
    "const IID": (ArgFormatterIID, 0),
    "REFCLSID": (ArgFormatterIID, 0),
    "REFIID": (ArgFormatterIID, 0),
    "REFGUID": (ArgFormatterIID, 0),
    "const FILETIME": (ArgFormatterTime, 0),
    "const SYSTEMTIME": (ArgFormatterTime, 0),
    "const LPSYSTEMTIME": (ArgFormatterTime, 1, 1),
    "LPSYSTEMTIME": (ArgFormatterTime, 1, 1),
    "FILETIME": (ArgFormatterTime, 0),
    "SYSTEMTIME": (ArgFormatterTime, 0),
    "STATSTG": (ArgFormatterSTATSTG, 0),
    "LARGE_INTEGER": (ArgFormatterLARGE_INTEGER, 0),
    "ULARGE_INTEGER": (ArgFormatterULARGE_INTEGER, 0),
    "VARIANT": (ArgFormatterVARIANT, 0),
    "float": (ArgFormatterFloat, 0),
    "single": (ArgFormatterFloat, 0),
    "short": (ArgFormatterShort, 0),
    "WORD": (ArgFormatterShort, 0),
    "VARIANT_BOOL": (ArgFormatterShort, 0),
    "HWND": (ArgFormatterLONG_PTR, 1),
    "HMENU": (ArgFormatterLONG_PTR, 1),
    "HOLEMENU": (ArgFormatterLONG_PTR, 1),
    "HICON": (ArgFormatterLONG_PTR, 1),
    "HDC": (ArgFormatterLONG_PTR, 1),
    "LPARAM": (ArgFormatterLONG_PTR, 1),
    "WPARAM": (ArgFormatterLONG_PTR, 1),
    "LRESULT": (ArgFormatterLONG_PTR, 1),
    "UINT": (ArgFormatterShort, 0),
    "SVSIF": (ArgFormatterShort, 0),
    "Control": (ArgFormatterInterface, 0, 1),
    "DataObject": (ArgFormatterInterface, 0, 1),
    "_PropertyBag": (ArgFormatterInterface, 0, 1),
    "AsyncProp": (ArgFormatterInterface, 0, 1),
    "DataSource": (ArgFormatterInterface, 0, 1),
    "DataFormat": (ArgFormatterInterface, 0, 1),
    "void **": (ArgFormatterInterface, 2, 2),
    "ITEMIDLIST": (ArgFormatterIDLIST, 0, 0),
    "LPITEMIDLIST": (ArgFormatterIDLIST, 0, 1),
    "LPCITEMIDLIST": (ArgFormatterIDLIST, 0, 1),
    "const ITEMIDLIST": (ArgFormatterIDLIST, 0, 1),
    "PITEMID_CHILD": (ArgFormatterIDLIST, 1),
    "const PITEMID_CHILD": (ArgFormatterIDLIST, 0),
    "PCITEMID_CHILD": (ArgFormatterIDLIST, 0),
    "PUITEMID_CHILD": (ArgFormatterIDLIST, 1),
    "PCUITEMID_CHILD": (ArgFormatterIDLIST, 0),
    "const PUITEMID_CHILD": (ArgFormatterIDLIST, 0),
    "PCUITEMID_CHILD_ARRAY": (ArgFormatterIDLIST, 2),
    "const PCUITEMID_CHILD_ARRAY": (ArgFormatterIDLIST, 2),
    # Auto-add all the simple types
    **{key: (ArgFormatterSimple, 0) for key in ConvertSimpleTypes},
}


def make_arg_converter(arg):
    try:
        clz = AllConverters[arg.type][0]
        bin = AllConverters[arg.type][1]
        decl = 0
        if len(AllConverters[arg.type]) > 2:
            decl = AllConverters[arg.type][2]
        return clz(arg, bin, decl)
    except KeyError:
        if arg.type[0] == "I":
            return ArgFormatterInterface(arg, 0, 1)

        raise error_not_supported(f"The type '{arg.type}' ({arg.name}) is unknown.")


#############################################################
#
# The instances that represent the args, methods and interface
class Argument:
    """A representation of an argument to a COM method

    This class contains information about a specific argument to a method.
    In addition, methods exist so that an argument knows how to convert itself
    to/from Python arguments.
    """

    # 									  in,out					  type			  name			 [	]
    # 								   --------------				--------	  ------------		------
    regex = re.compile(r"/\* \[([^\]]*.*?)] \*/[ \t](.*[* ]+)(\w+)(\[ *])?[\),]")

    @classmethod
    def drop_rpc_metadata(cls, type_):
        return " ".join(e for e in type_.split(" ") if not e.startswith("__RPC_"))

    def __init__(self, good_interface_names):
        self.good_interface_names = good_interface_names
        self.inout = None
        self.name = None
        self.type = None
        self.raw_type = None
        self.unc_type = None
        self.const = 0
        self.arrayDecl = 0
        self.indirectionLevel = 0

    def BuildFromFile(self, file):
        """Parse and build my data from a file

        Reads the next line in the file, and matches it as an argument
        description.  If not a valid argument line, an error_not_found exception
        is raised.
        """
        line = file.readline()
        mo = self.regex.search(line)
        if not mo:
            raise error_not_found
        self.name = mo.group(3)
        self.inout = mo.group(1).split("][")
        typ = mo.group(2).strip()
        self.raw_type = typ
        if mo.group(4):  # Has "[ ]" decl
            self.arrayDecl = 1
            typ_no_rpc = self.drop_rpc_metadata(typ)
            if typ != typ_no_rpc:
                self.indirectionLevel += 1

        typ = self.drop_rpc_metadata(typ)
        while 1:
            try:
                pos = typ.rindex("*")
                self.indirectionLevel += 1
                typ = typ[:pos].strip()
            except ValueError:
                break
        self.type = typ
        if self.type[:6] == "const ":
            self.unc_type = self.type[6:]
        else:
            self.unc_type = self.type

        if VERBOSE:
            print(
                "       Arg {} of type {}{} ({})".format(
                    self.name, self.type, "*" * self.indirectionLevel, self.inout
                )
            )

    def HasAttribute(self, typ):
        """Determines if the argument has the specific attribute.

        Argument attributes are specified in the header file, such as
        "[in][out][retval]" etc.  You can pass a specific string (eg "out")
        to find if this attribute was specified for the argument
        """
        return typ in self.inout

    def GetRawDeclaration(self):
        ret = f"{self.raw_type} {self.name}"
        if self.arrayDecl:
            ret += "[]"
        return ret


class Method:
    """A representation of a C++ method on a COM interface

    This class contains information about a specific method, as well as
    a list of all @Argument@s
    """

    # 										 options	 ret type callconv	 name
    # 								   ----------------- -------- -------- --------
    regex = re.compile(r"virtual (/\*.*?\*/ )?(.*?) (.*?) (.*?)\(\w?")

    def __init__(self, good_interface_names):
        self.good_interface_names = good_interface_names
        self.name = self.result = self.callconv = None
        self.args = []

    def BuildFromFile(self, file):
        """Parse and build my data from a file

        Reads the next line in the file, and matches it as a method
        description.  If not a valid method line, an error_not_found exception
        is raised.
        """
        line = file.readline()
        mo = self.regex.search(line)
        if not mo:
            raise error_not_found
        self.name = mo.group(4)
        self.result = mo.group(2)
        if self.result != "HRESULT":
            if self.result == "DWORD":  # DWORD is for old old stuff?
                print(
                    "Warning: Old style interface detected - compilation errors likely!"
                )
            else:
                print(
                    "Method %s - Only HRESULT return types are supported." % self.name
                )
            # 				raise error_not_supported,		if VERBOSE:
            print(f"     Method {self.result} {self.name}(")
        while 1:
            arg = Argument(self.good_interface_names)
            try:
                arg.BuildFromFile(file)
                self.args.append(arg)
            except error_not_found:
                break


class Interface:
    """A representation of a C++ COM Interface

    This class contains information about a specific interface, as well as
    a list of all @Method@s
    """

    # 									  name				 base
    # 									 --------		   --------
    regex = re.compile(r"(interface|) ([^ ]*) : public (.*)$")

    def __init__(self, mo):
        self.methods = []
        self.name = mo.group(2)
        self.base = mo.group(3)
        if VERBOSE:
            print(f"Interface {self.name} : public {self.base}")

    def BuildMethods(self, file):
        """Build all sub-methods for this interface"""
        # skip the next 2 lines.
        file.readline()
        file.readline()
        while 1:
            try:
                method = Method([self.name])
                method.BuildFromFile(file)
                self.methods.append(method)
            except error_not_found:
                break


def find_interface(interfaceName, file):
    """Find and return an interface in a file

    Given an interface name and file, search for the specified interface.

    Upon return, the interface itself has been built,
    but not the methods.
    """
    interface = None
    line = file.readline()
    while line:
        mo = Interface.regex.search(line)
        if mo:
            name = mo.group(2)
            print(name)
            AllConverters[name] = (ArgFormatterInterface, 0, 1)
            if name == interfaceName:
                interface = Interface(mo)
                interface.BuildMethods(file)
        line = file.readline()
    if interface:
        return interface
    raise error_not_found


def parse_interface_info(interfaceName, file):
    """Find, parse and return an interface in a file

    Given an interface name and file, search for the specified interface.

    Upon return, the interface itself is fully built,
    """
    try:
        return find_interface(interfaceName, file)
    except re.error:
        traceback.print_exc()
        print("The interface could not be built, as the regular expression failed!")


def test():
    f = open("d:\\msdev\\include\\objidl.h")
    try:
        parse_interface_info("IPersistStream", f)
    finally:
        f.close()


def test_regex(r, text):
    res = r.search(text, 0)
    if res == -1:
        print("** Not found")
    else:
        print(
            "%d\n%s\n%s\n%s\n%s" % (res, r.group(1), r.group(2), r.group(3), r.group(4))
        )

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\pretty.py ===
import builtins
import collections
import dataclasses
import inspect
import os
import reprlib
import sys
from array import array
from collections import Counter, UserDict, UserList, defaultdict, deque
from dataclasses import dataclass, fields, is_dataclass
from inspect import isclass
from itertools import islice
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Deque,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from pip._vendor.rich.repr import RichReprResult

try:
    import attr as _attr_module

    _has_attrs = hasattr(_attr_module, "ib")
except ImportError:  # pragma: no cover
    _has_attrs = False

from . import get_console
from ._loop import loop_last
from ._pick import pick_bool
from .abc import RichRenderable
from .cells import cell_len
from .highlighter import ReprHighlighter
from .jupyter import JupyterMixin, JupyterRenderable
from .measure import Measurement
from .text import Text

if TYPE_CHECKING:
    from .console import (
        Console,
        ConsoleOptions,
        HighlighterType,
        JustifyMethod,
        OverflowMethod,
        RenderResult,
    )


def _is_attr_object(obj: Any) -> bool:
    """Check if an object was created with attrs module."""
    return _has_attrs and _attr_module.has(type(obj))


def _get_attr_fields(obj: Any) -> Sequence["_attr_module.Attribute[Any]"]:
    """Get fields for an attrs object."""
    return _attr_module.fields(type(obj)) if _has_attrs else []


def _is_dataclass_repr(obj: object) -> bool:
    """Check if an instance of a dataclass contains the default repr.

    Args:
        obj (object): A dataclass instance.

    Returns:
        bool: True if the default repr is used, False if there is a custom repr.
    """
    # Digging in to a lot of internals here
    # Catching all exceptions in case something is missing on a non CPython implementation
    try:
        return obj.__repr__.__code__.co_filename in (
            dataclasses.__file__,
            reprlib.__file__,
        )
    except Exception:  # pragma: no coverage
        return False


_dummy_namedtuple = collections.namedtuple("_dummy_namedtuple", [])


def _has_default_namedtuple_repr(obj: object) -> bool:
    """Check if an instance of namedtuple contains the default repr

    Args:
        obj (object): A namedtuple

    Returns:
        bool: True if the default repr is used, False if there's a custom repr.
    """
    obj_file = None
    try:
        obj_file = inspect.getfile(obj.__repr__)
    except (OSError, TypeError):
        # OSError handles case where object is defined in __main__ scope, e.g. REPL - no filename available.
        # TypeError trapped defensively, in case of object without filename slips through.
        pass
    default_repr_file = inspect.getfile(_dummy_namedtuple.__repr__)
    return obj_file == default_repr_file


def _ipy_display_hook(
    value: Any,
    console: Optional["Console"] = None,
    overflow: "OverflowMethod" = "ignore",
    crop: bool = False,
    indent_guides: bool = False,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> Union[str, None]:
    # needed here to prevent circular import:
    from .console import ConsoleRenderable

    # always skip rich generated jupyter renderables or None values
    if _safe_isinstance(value, JupyterRenderable) or value is None:
        return None

    console = console or get_console()

    with console.capture() as capture:
        # certain renderables should start on a new line
        if _safe_isinstance(value, ConsoleRenderable):
            console.line()
        console.print(
            (
                value
                if _safe_isinstance(value, RichRenderable)
                else Pretty(
                    value,
                    overflow=overflow,
                    indent_guides=indent_guides,
                    max_length=max_length,
                    max_string=max_string,
                    max_depth=max_depth,
                    expand_all=expand_all,
                    margin=12,
                )
            ),
            crop=crop,
            new_line_start=True,
            end="",
        )
    # strip trailing newline, not usually part of a text repr
    # I'm not sure if this should be prevented at a lower level
    return capture.get().rstrip("\n")


def _safe_isinstance(
    obj: object, class_or_tuple: Union[type, Tuple[type, ...]]
) -> bool:
    """isinstance can fail in rare cases, for example types with no __class__"""
    try:
        return isinstance(obj, class_or_tuple)
    except Exception:
        return False


def install(
    console: Optional["Console"] = None,
    overflow: "OverflowMethod" = "ignore",
    crop: bool = False,
    indent_guides: bool = False,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> None:
    """Install automatic pretty printing in the Python REPL.

    Args:
        console (Console, optional): Console instance or ``None`` to use global console. Defaults to None.
        overflow (Optional[OverflowMethod], optional): Overflow method. Defaults to "ignore".
        crop (Optional[bool], optional): Enable cropping of long lines. Defaults to False.
        indent_guides (bool, optional): Enable indentation guides. Defaults to False.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable. Defaults to None.
        max_depth (int, optional): Maximum depth of nested data structures, or None for no maximum. Defaults to None.
        expand_all (bool, optional): Expand all containers. Defaults to False.
        max_frames (int): Maximum number of frames to show in a traceback, 0 for no maximum. Defaults to 100.
    """
    from pip._vendor.rich import get_console

    console = console or get_console()
    assert console is not None

    def display_hook(value: Any) -> None:
        """Replacement sys.displayhook which prettifies objects with Rich."""
        if value is not None:
            assert console is not None
            builtins._ = None  # type: ignore[attr-defined]
            console.print(
                (
                    value
                    if _safe_isinstance(value, RichRenderable)
                    else Pretty(
                        value,
                        overflow=overflow,
                        indent_guides=indent_guides,
                        max_length=max_length,
                        max_string=max_string,
                        max_depth=max_depth,
                        expand_all=expand_all,
                    )
                ),
                crop=crop,
            )
            builtins._ = value  # type: ignore[attr-defined]

    try:
        ip = get_ipython()  # type: ignore[name-defined]
    except NameError:
        sys.displayhook = display_hook
    else:
        from IPython.core.formatters import BaseFormatter

        class RichFormatter(BaseFormatter):  # type: ignore[misc]
            pprint: bool = True

            def __call__(self, value: Any) -> Any:
                if self.pprint:
                    return _ipy_display_hook(
                        value,
                        console=get_console(),
                        overflow=overflow,
                        indent_guides=indent_guides,
                        max_length=max_length,
                        max_string=max_string,
                        max_depth=max_depth,
                        expand_all=expand_all,
                    )
                else:
                    return repr(value)

        # replace plain text formatter with rich formatter
        rich_formatter = RichFormatter()
        ip.display_formatter.formatters["text/plain"] = rich_formatter


class Pretty(JupyterMixin):
    """A rich renderable that pretty prints an object.

    Args:
        _object (Any): An object to pretty print.
        highlighter (HighlighterType, optional): Highlighter object to apply to result, or None for ReprHighlighter. Defaults to None.
        indent_size (int, optional): Number of spaces in indent. Defaults to 4.
        justify (JustifyMethod, optional): Justify method, or None for default. Defaults to None.
        overflow (OverflowMethod, optional): Overflow method, or None for default. Defaults to None.
        no_wrap (Optional[bool], optional): Disable word wrapping. Defaults to False.
        indent_guides (bool, optional): Enable indentation guides. Defaults to False.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable. Defaults to None.
        max_depth (int, optional): Maximum depth of nested data structures, or None for no maximum. Defaults to None.
        expand_all (bool, optional): Expand all containers. Defaults to False.
        margin (int, optional): Subtrace a margin from width to force containers to expand earlier. Defaults to 0.
        insert_line (bool, optional): Insert a new line if the output has multiple new lines. Defaults to False.
    """

    def __init__(
        self,
        _object: Any,
        highlighter: Optional["HighlighterType"] = None,
        *,
        indent_size: int = 4,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = False,
        indent_guides: bool = False,
        max_length: Optional[int] = None,
        max_string: Optional[int] = None,
        max_depth: Optional[int] = None,
        expand_all: bool = False,
        margin: int = 0,
        insert_line: bool = False,
    ) -> None:
        self._object = _object
        self.highlighter = highlighter or ReprHighlighter()
        self.indent_size = indent_size
        self.justify: Optional["JustifyMethod"] = justify
        self.overflow: Optional["OverflowMethod"] = overflow
        self.no_wrap = no_wrap
        self.indent_guides = indent_guides
        self.max_length = max_length
        self.max_string = max_string
        self.max_depth = max_depth
        self.expand_all = expand_all
        self.margin = margin
        self.insert_line = insert_line

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        pretty_str = pretty_repr(
            self._object,
            max_width=options.max_width - self.margin,
            indent_size=self.indent_size,
            max_length=self.max_length,
            max_string=self.max_string,
            max_depth=self.max_depth,
            expand_all=self.expand_all,
        )
        pretty_text = Text.from_ansi(
            pretty_str,
            justify=self.justify or options.justify,
            overflow=self.overflow or options.overflow,
            no_wrap=pick_bool(self.no_wrap, options.no_wrap),
            style="pretty",
        )
        pretty_text = (
            self.highlighter(pretty_text)
            if pretty_text
            else Text(
                f"{type(self._object)}.__repr__ returned empty string",
                style="dim italic",
            )
        )
        if self.indent_guides and not options.ascii_only:
            pretty_text = pretty_text.with_indent_guides(
                self.indent_size, style="repr.indent"
            )
        if self.insert_line and "\n" in pretty_text:
            yield ""
        yield pretty_text

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        pretty_str = pretty_repr(
            self._object,
            max_width=options.max_width,
            indent_size=self.indent_size,
            max_length=self.max_length,
            max_string=self.max_string,
            max_depth=self.max_depth,
            expand_all=self.expand_all,
        )
        text_width = (
            max(cell_len(line) for line in pretty_str.splitlines()) if pretty_str else 0
        )
        return Measurement(text_width, text_width)


def _get_braces_for_defaultdict(_object: DefaultDict[Any, Any]) -> Tuple[str, str, str]:
    return (
        f"defaultdict({_object.default_factory!r}, {{",
        "})",
        f"defaultdict({_object.default_factory!r}, {{}})",
    )


def _get_braces_for_deque(_object: Deque[Any]) -> Tuple[str, str, str]:
    if _object.maxlen is None:
        return ("deque([", "])", "deque()")
    return (
        "deque([",
        f"], maxlen={_object.maxlen})",
        f"deque(maxlen={_object.maxlen})",
    )


def _get_braces_for_array(_object: "array[Any]") -> Tuple[str, str, str]:
    return (f"array({_object.typecode!r}, [", "])", f"array({_object.typecode!r})")


_BRACES: Dict[type, Callable[[Any], Tuple[str, str, str]]] = {
    os._Environ: lambda _object: ("environ({", "})", "environ({})"),
    array: _get_braces_for_array,
    defaultdict: _get_braces_for_defaultdict,
    Counter: lambda _object: ("Counter({", "})", "Counter()"),
    deque: _get_braces_for_deque,
    dict: lambda _object: ("{", "}", "{}"),
    UserDict: lambda _object: ("{", "}", "{}"),
    frozenset: lambda _object: ("frozenset({", "})", "frozenset()"),
    list: lambda _object: ("[", "]", "[]"),
    UserList: lambda _object: ("[", "]", "[]"),
    set: lambda _object: ("{", "}", "set()"),
    tuple: lambda _object: ("(", ")", "()"),
    MappingProxyType: lambda _object: ("mappingproxy({", "})", "mappingproxy({})"),
}
_CONTAINERS = tuple(_BRACES.keys())
_MAPPING_CONTAINERS = (dict, os._Environ, MappingProxyType, UserDict)


def is_expandable(obj: Any) -> bool:
    """Check if an object may be expanded by pretty print."""
    return (
        _safe_isinstance(obj, _CONTAINERS)
        or (is_dataclass(obj))
        or (hasattr(obj, "__rich_repr__"))
        or _is_attr_object(obj)
    ) and not isclass(obj)


@dataclass
class Node:
    """A node in a repr tree. May be atomic or a container."""

    key_repr: str = ""
    value_repr: str = ""
    open_brace: str = ""
    close_brace: str = ""
    empty: str = ""
    last: bool = False
    is_tuple: bool = False
    is_namedtuple: bool = False
    children: Optional[List["Node"]] = None
    key_separator: str = ": "
    separator: str = ", "

    def iter_tokens(self) -> Iterable[str]:
        """Generate tokens for this node."""
        if self.key_repr:
            yield self.key_repr
            yield self.key_separator
        if self.value_repr:
            yield self.value_repr
        elif self.children is not None:
            if self.children:
                yield self.open_brace
                if self.is_tuple and not self.is_namedtuple and len(self.children) == 1:
                    yield from self.children[0].iter_tokens()
                    yield ","
                else:
                    for child in self.children:
                        yield from child.iter_tokens()
                        if not child.last:
                            yield self.separator
                yield self.close_brace
            else:
                yield self.empty

    def check_length(self, start_length: int, max_length: int) -> bool:
        """Check the length fits within a limit.

        Args:
            start_length (int): Starting length of the line (indent, prefix, suffix).
            max_length (int): Maximum length.

        Returns:
            bool: True if the node can be rendered within max length, otherwise False.
        """
        total_length = start_length
        for token in self.iter_tokens():
            total_length += cell_len(token)
            if total_length > max_length:
                return False
        return True

    def __str__(self) -> str:
        repr_text = "".join(self.iter_tokens())
        return repr_text

    def render(
        self, max_width: int = 80, indent_size: int = 4, expand_all: bool = False
    ) -> str:
        """Render the node to a pretty repr.

        Args:
            max_width (int, optional): Maximum width of the repr. Defaults to 80.
            indent_size (int, optional): Size of indents. Defaults to 4.
            expand_all (bool, optional): Expand all levels. Defaults to False.

        Returns:
            str: A repr string of the original object.
        """
        lines = [_Line(node=self, is_root=True)]
        line_no = 0
        while line_no < len(lines):
            line = lines[line_no]
            if line.expandable and not line.expanded:
                if expand_all or not line.check_length(max_width):
                    lines[line_no : line_no + 1] = line.expand(indent_size)
            line_no += 1

        repr_str = "\n".join(str(line) for line in lines)
        return repr_str


@dataclass
class _Line:
    """A line in repr output."""

    parent: Optional["_Line"] = None
    is_root: bool = False
    node: Optional[Node] = None
    text: str = ""
    suffix: str = ""
    whitespace: str = ""
    expanded: bool = False
    last: bool = False

    @property
    def expandable(self) -> bool:
        """Check if the line may be expanded."""
        return bool(self.node is not None and self.node.children)

    def check_length(self, max_length: int) -> bool:
        """Check this line fits within a given number of cells."""
        start_length = (
            len(self.whitespace) + cell_len(self.text) + cell_len(self.suffix)
        )
        assert self.node is not None
        return self.node.check_length(start_length, max_length)

    def expand(self, indent_size: int) -> Iterable["_Line"]:
        """Expand this line by adding children on their own line."""
        node = self.node
        assert node is not None
        whitespace = self.whitespace
        assert node.children
        if node.key_repr:
            new_line = yield _Line(
                text=f"{node.key_repr}{node.key_separator}{node.open_brace}",
                whitespace=whitespace,
            )
        else:
            new_line = yield _Line(text=node.open_brace, whitespace=whitespace)
        child_whitespace = self.whitespace + " " * indent_size
        tuple_of_one = node.is_tuple and len(node.children) == 1
        for last, child in loop_last(node.children):
            separator = "," if tuple_of_one else node.separator
            line = _Line(
                parent=new_line,
                node=child,
                whitespace=child_whitespace,
                suffix=separator,
                last=last and not tuple_of_one,
            )
            yield line

        yield _Line(
            text=node.close_brace,
            whitespace=whitespace,
            suffix=self.suffix,
            last=self.last,
        )

    def __str__(self) -> str:
        if self.last:
            return f"{self.whitespace}{self.text}{self.node or ''}"
        else:
            return (
                f"{self.whitespace}{self.text}{self.node or ''}{self.suffix.rstrip()}"
            )


def _is_namedtuple(obj: Any) -> bool:
    """Checks if an object is most likely a namedtuple. It is possible
    to craft an object that passes this check and isn't a namedtuple, but
    there is only a minuscule chance of this happening unintentionally.

    Args:
        obj (Any): The object to test

    Returns:
        bool: True if the object is a namedtuple. False otherwise.
    """
    try:
        fields = getattr(obj, "_fields", None)
    except Exception:
        # Being very defensive - if we cannot get the attr then its not a namedtuple
        return False
    return isinstance(obj, tuple) and isinstance(fields, tuple)


def traverse(
    _object: Any,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
) -> Node:
    """Traverse object and generate a tree.

    Args:
        _object (Any): Object to be traversed.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable truncating.
            Defaults to None.
        max_depth (int, optional): Maximum depth of data structures, or None for no maximum.
            Defaults to None.

    Returns:
        Node: The root of a tree structure which can be used to render a pretty repr.
    """

    def to_repr(obj: Any) -> str:
        """Get repr string for an object, but catch errors."""
        if (
            max_string is not None
            and _safe_isinstance(obj, (bytes, str))
            and len(obj) > max_string
        ):
            truncated = len(obj) - max_string
            obj_repr = f"{obj[:max_string]!r}+{truncated}"
        else:
            try:
                obj_repr = repr(obj)
            except Exception as error:
                obj_repr = f"<repr-error {str(error)!r}>"
        return obj_repr

    visited_ids: Set[int] = set()
    push_visited = visited_ids.add
    pop_visited = visited_ids.remove

    def _traverse(obj: Any, root: bool = False, depth: int = 0) -> Node:
        """Walk the object depth first."""

        obj_id = id(obj)
        if obj_id in visited_ids:
            # Recursion detected
            return Node(value_repr="...")

        obj_type = type(obj)
        children: List[Node]
        reached_max_depth = max_depth is not None and depth >= max_depth

        def iter_rich_args(rich_args: Any) -> Iterable[Union[Any, Tuple[str, Any]]]:
            for arg in rich_args:
                if _safe_isinstance(arg, tuple):
                    if len(arg) == 3:
                        key, child, default = arg
                        if default == child:
                            continue
                        yield key, child
                    elif len(arg) == 2:
                        key, child = arg
                        yield key, child
                    elif len(arg) == 1:
                        yield arg[0]
                else:
                    yield arg

        try:
            fake_attributes = hasattr(
                obj, "awehoi234_wdfjwljet234_234wdfoijsdfmmnxpi492"
            )
        except Exception:
            fake_attributes = False

        rich_repr_result: Optional[RichReprResult] = None
        if not fake_attributes:
            try:
                if hasattr(obj, "__rich_repr__") and not isclass(obj):
                    rich_repr_result = obj.__rich_repr__()
            except Exception:
                pass

        if rich_repr_result is not None:
            push_visited(obj_id)
            angular = getattr(obj.__rich_repr__, "angular", False)
            args = list(iter_rich_args(rich_repr_result))
            class_name = obj.__class__.__name__

            if args:
                children = []
                append = children.append

                if reached_max_depth:
                    if angular:
                        node = Node(value_repr=f"<{class_name}...>")
                    else:
                        node = Node(value_repr=f"{class_name}(...)")
                else:
                    if angular:
                        node = Node(
                            open_brace=f"<{class_name} ",
                            close_brace=">",
                            children=children,
                            last=root,
                            separator=" ",
                        )
                    else:
                        node = Node(
                            open_brace=f"{class_name}(",
                            close_brace=")",
                            children=children,
                            last=root,
                        )
                    for last, arg in loop_last(args):
                        if _safe_isinstance(arg, tuple):
                            key, child = arg
                            child_node = _traverse(child, depth=depth + 1)
                            child_node.last = last
                            child_node.key_repr = key
                            child_node.key_separator = "="
                            append(child_node)
                        else:
                            child_node = _traverse(arg, depth=depth + 1)
                            child_node.last = last
                            append(child_node)
            else:
                node = Node(
                    value_repr=f"<{class_name}>" if angular else f"{class_name}()",
                    children=[],
                    last=root,
                )
            pop_visited(obj_id)
        elif _is_attr_object(obj) and not fake_attributes:
            push_visited(obj_id)
            children = []
            append = children.append

            attr_fields = _get_attr_fields(obj)
            if attr_fields:
                if reached_max_depth:
                    node = Node(value_repr=f"{obj.__class__.__name__}(...)")
                else:
                    node = Node(
                        open_brace=f"{obj.__class__.__name__}(",
                        close_brace=")",
                        children=children,
                        last=root,
                    )

                    def iter_attrs() -> (
                        Iterable[Tuple[str, Any, Optional[Callable[[Any], str]]]]
                    ):
                        """Iterate over attr fields and values."""
                        for attr in attr_fields:
                            if attr.repr:
                                try:
                                    value = getattr(obj, attr.name)
                                except Exception as error:
                                    # Can happen, albeit rarely
                                    yield (attr.name, error, None)
                                else:
                                    yield (
                                        attr.name,
                                        value,
                                        attr.repr if callable(attr.repr) else None,
                                    )

                    for last, (name, value, repr_callable) in loop_last(iter_attrs()):
                        if repr_callable:
                            child_node = Node(value_repr=str(repr_callable(value)))
                        else:
                            child_node = _traverse(value, depth=depth + 1)
                        child_node.last = last
                        child_node.key_repr = name
                        child_node.key_separator = "="
                        append(child_node)
            else:
                node = Node(
                    value_repr=f"{obj.__class__.__name__}()", children=[], last=root
                )
            pop_visited(obj_id)
        elif (
            is_dataclass(obj)
            and not _safe_isinstance(obj, type)
            and not fake_attributes
            and _is_dataclass_repr(obj)
        ):
            push_visited(obj_id)
            children = []
            append = children.append
            if reached_max_depth:
                node = Node(value_repr=f"{obj.__class__.__name__}(...)")
            else:
                node = Node(
                    open_brace=f"{obj.__class__.__name__}(",
                    close_brace=")",
                    children=children,
                    last=root,
                    empty=f"{obj.__class__.__name__}()",
                )

                for last, field in loop_last(
                    field
                    for field in fields(obj)
                    if field.repr and hasattr(obj, field.name)
                ):
                    child_node = _traverse(getattr(obj, field.name), depth=depth + 1)
                    child_node.key_repr = field.name
                    child_node.last = last
                    child_node.key_separator = "="
                    append(child_node)

            pop_visited(obj_id)
        elif _is_namedtuple(obj) and _has_default_namedtuple_repr(obj):
            push_visited(obj_id)
            class_name = obj.__class__.__name__
            if reached_max_depth:
                # If we've reached the max depth, we still show the class name, but not its contents
                node = Node(
                    value_repr=f"{class_name}(...)",
                )
            else:
                children = []
                append = children.append
                node = Node(
                    open_brace=f"{class_name}(",
                    close_brace=")",
                    children=children,
                    empty=f"{class_name}()",
                )
                for last, (key, value) in loop_last(obj._asdict().items()):
                    child_node = _traverse(value, depth=depth + 1)
                    child_node.key_repr = key
                    child_node.last = last
                    child_node.key_separator = "="
                    append(child_node)
            pop_visited(obj_id)
        elif _safe_isinstance(obj, _CONTAINERS):
            for container_type in _CONTAINERS:
                if _safe_isinstance(obj, container_type):
                    obj_type = container_type
                    break

            push_visited(obj_id)

            open_brace, close_brace, empty = _BRACES[obj_type](obj)

            if reached_max_depth:
                node = Node(value_repr=f"{open_brace}...{close_brace}")
            elif obj_type.__repr__ != type(obj).__repr__:
                node = Node(value_repr=to_repr(obj), last=root)
            elif obj:
                children = []
                node = Node(
                    open_brace=open_brace,
                    close_brace=close_brace,
                    children=children,
                    last=root,
                )
                append = children.append
                num_items = len(obj)
                last_item_index = num_items - 1

                if _safe_isinstance(obj, _MAPPING_CONTAINERS):
                    iter_items = iter(obj.items())
                    if max_length is not None:
                        iter_items = islice(iter_items, max_length)
                    for index, (key, child) in enumerate(iter_items):
                        child_node = _traverse(child, depth=depth + 1)
                        child_node.key_repr = to_repr(key)
                        child_node.last = index == last_item_index
                        append(child_node)
                else:
                    iter_values = iter(obj)
                    if max_length is not None:
                        iter_values = islice(iter_values, max_length)
                    for index, child in enumerate(iter_values):
                        child_node = _traverse(child, depth=depth + 1)
                        child_node.last = index == last_item_index
                        append(child_node)
                if max_length is not None and num_items > max_length:
                    append(Node(value_repr=f"... +{num_items - max_length}", last=True))
            else:
                node = Node(empty=empty, children=[], last=root)

            pop_visited(obj_id)
        else:
            node = Node(value_repr=to_repr(obj), last=root)
        node.is_tuple = type(obj) == tuple
        node.is_namedtuple = _is_namedtuple(obj)
        return node

    node = _traverse(_object, root=True)
    return node


def pretty_repr(
    _object: Any,
    *,
    max_width: int = 80,
    indent_size: int = 4,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> str:
    """Prettify repr string by expanding on to new lines to fit within a given width.

    Args:
        _object (Any): Object to repr.
        max_width (int, optional): Desired maximum width of repr string. Defaults to 80.
        indent_size (int, optional): Number of spaces to indent. Defaults to 4.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable truncating.
            Defaults to None.
        max_depth (int, optional): Maximum depth of nested data structure, or None for no depth.
            Defaults to None.
        expand_all (bool, optional): Expand all containers regardless of available width. Defaults to False.

    Returns:
        str: A possibly multi-line representation of the object.
    """

    if _safe_isinstance(_object, Node):
        node = _object
    else:
        node = traverse(
            _object, max_length=max_length, max_string=max_string, max_depth=max_depth
        )
    repr_str: str = node.render(
        max_width=max_width, indent_size=indent_size, expand_all=expand_all
    )
    return repr_str


def pprint(
    _object: Any,
    *,
    console: Optional["Console"] = None,
    indent_guides: bool = True,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> None:
    """A convenience function for pretty printing.

    Args:
        _object (Any): Object to pretty print.
        console (Console, optional): Console instance, or None to use default. Defaults to None.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of strings before truncating, or None to disable. Defaults to None.
        max_depth (int, optional): Maximum depth for nested data structures, or None for unlimited depth. Defaults to None.
        indent_guides (bool, optional): Enable indentation guides. Defaults to True.
        expand_all (bool, optional): Expand all containers. Defaults to False.
    """
    _console = get_console() if console is None else console
    _console.print(
        Pretty(
            _object,
            max_length=max_length,
            max_string=max_string,
            max_depth=max_depth,
            indent_guides=indent_guides,
            expand_all=expand_all,
            overflow="ignore",
        ),
        soft_wrap=True,
    )


if __name__ == "__main__":  # pragma: no cover

    class BrokenRepr:
        def __repr__(self) -> str:
            1 / 0
            return "this will fail"

    from typing import NamedTuple

    class StockKeepingUnit(NamedTuple):
        name: str
        description: str
        price: float
        category: str
        reviews: List[str]

    d = defaultdict(int)
    d["foo"] = 5
    data = {
        "foo": [
            1,
            "Hello World!",
            100.123,
            323.232,
            432324.0,
            {5, 6, 7, (1, 2, 3, 4), 8},
        ],
        "bar": frozenset({1, 2, 3}),
        "defaultdict": defaultdict(
            list, {"crumble": ["apple", "rhubarb", "butter", "sugar", "flour"]}
        ),
        "counter": Counter(
            [
                "apple",
                "orange",
                "pear",
                "kumquat",
                "kumquat",
                "durian" * 100,
            ]
        ),
        "atomic": (False, True, None),
        "namedtuple": StockKeepingUnit(
            "Sparkling British Spring Water",
            "Carbonated spring water",
            0.9,
            "water",
            ["its amazing!", "its terrible!"],
        ),
        "Broken": BrokenRepr(),
    }
    data["foo"].append(data)  # type: ignore[attr-defined]

    from pip._vendor.rich import print

    print(Pretty(data, indent_guides=True, max_string=20))

    class Thing:
        def __repr__(self) -> str:
            return "Hello\x1b[38;5;239m World!"

    print(Pretty(Thing()))

# === NexusCore/openenv\Lib\site-packages\rich\pretty.py ===
import builtins
import collections
import dataclasses
import inspect
import os
import reprlib
import sys
from array import array
from collections import Counter, UserDict, UserList, defaultdict, deque
from dataclasses import dataclass, fields, is_dataclass
from inspect import isclass
from itertools import islice
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Deque,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from rich.repr import RichReprResult

try:
    import attr as _attr_module

    _has_attrs = hasattr(_attr_module, "ib")
except ImportError:  # pragma: no cover
    _has_attrs = False

from . import get_console
from ._loop import loop_last
from ._pick import pick_bool
from .abc import RichRenderable
from .cells import cell_len
from .highlighter import ReprHighlighter
from .jupyter import JupyterMixin, JupyterRenderable
from .measure import Measurement
from .text import Text

if TYPE_CHECKING:
    from .console import (
        Console,
        ConsoleOptions,
        HighlighterType,
        JustifyMethod,
        OverflowMethod,
        RenderResult,
    )


def _is_attr_object(obj: Any) -> bool:
    """Check if an object was created with attrs module."""
    return _has_attrs and _attr_module.has(type(obj))


def _get_attr_fields(obj: Any) -> Sequence["_attr_module.Attribute[Any]"]:
    """Get fields for an attrs object."""
    return _attr_module.fields(type(obj)) if _has_attrs else []


def _is_dataclass_repr(obj: object) -> bool:
    """Check if an instance of a dataclass contains the default repr.

    Args:
        obj (object): A dataclass instance.

    Returns:
        bool: True if the default repr is used, False if there is a custom repr.
    """
    # Digging in to a lot of internals here
    # Catching all exceptions in case something is missing on a non CPython implementation
    try:
        return obj.__repr__.__code__.co_filename in (
            dataclasses.__file__,
            reprlib.__file__,
        )
    except Exception:  # pragma: no coverage
        return False


_dummy_namedtuple = collections.namedtuple("_dummy_namedtuple", [])


def _has_default_namedtuple_repr(obj: object) -> bool:
    """Check if an instance of namedtuple contains the default repr

    Args:
        obj (object): A namedtuple

    Returns:
        bool: True if the default repr is used, False if there's a custom repr.
    """
    obj_file = None
    try:
        obj_file = inspect.getfile(obj.__repr__)
    except (OSError, TypeError):
        # OSError handles case where object is defined in __main__ scope, e.g. REPL - no filename available.
        # TypeError trapped defensively, in case of object without filename slips through.
        pass
    default_repr_file = inspect.getfile(_dummy_namedtuple.__repr__)
    return obj_file == default_repr_file


def _ipy_display_hook(
    value: Any,
    console: Optional["Console"] = None,
    overflow: "OverflowMethod" = "ignore",
    crop: bool = False,
    indent_guides: bool = False,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> Union[str, None]:
    # needed here to prevent circular import:
    from .console import ConsoleRenderable

    # always skip rich generated jupyter renderables or None values
    if _safe_isinstance(value, JupyterRenderable) or value is None:
        return None

    console = console or get_console()

    with console.capture() as capture:
        # certain renderables should start on a new line
        if _safe_isinstance(value, ConsoleRenderable):
            console.line()
        console.print(
            (
                value
                if _safe_isinstance(value, RichRenderable)
                else Pretty(
                    value,
                    overflow=overflow,
                    indent_guides=indent_guides,
                    max_length=max_length,
                    max_string=max_string,
                    max_depth=max_depth,
                    expand_all=expand_all,
                    margin=12,
                )
            ),
            crop=crop,
            new_line_start=True,
            end="",
        )
    # strip trailing newline, not usually part of a text repr
    # I'm not sure if this should be prevented at a lower level
    return capture.get().rstrip("\n")


def _safe_isinstance(
    obj: object, class_or_tuple: Union[type, Tuple[type, ...]]
) -> bool:
    """isinstance can fail in rare cases, for example types with no __class__"""
    try:
        return isinstance(obj, class_or_tuple)
    except Exception:
        return False


def install(
    console: Optional["Console"] = None,
    overflow: "OverflowMethod" = "ignore",
    crop: bool = False,
    indent_guides: bool = False,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> None:
    """Install automatic pretty printing in the Python REPL.

    Args:
        console (Console, optional): Console instance or ``None`` to use global console. Defaults to None.
        overflow (Optional[OverflowMethod], optional): Overflow method. Defaults to "ignore".
        crop (Optional[bool], optional): Enable cropping of long lines. Defaults to False.
        indent_guides (bool, optional): Enable indentation guides. Defaults to False.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable. Defaults to None.
        max_depth (int, optional): Maximum depth of nested data structures, or None for no maximum. Defaults to None.
        expand_all (bool, optional): Expand all containers. Defaults to False.
        max_frames (int): Maximum number of frames to show in a traceback, 0 for no maximum. Defaults to 100.
    """
    from rich import get_console

    console = console or get_console()
    assert console is not None

    def display_hook(value: Any) -> None:
        """Replacement sys.displayhook which prettifies objects with Rich."""
        if value is not None:
            assert console is not None
            builtins._ = None  # type: ignore[attr-defined]
            console.print(
                (
                    value
                    if _safe_isinstance(value, RichRenderable)
                    else Pretty(
                        value,
                        overflow=overflow,
                        indent_guides=indent_guides,
                        max_length=max_length,
                        max_string=max_string,
                        max_depth=max_depth,
                        expand_all=expand_all,
                    )
                ),
                crop=crop,
            )
            builtins._ = value  # type: ignore[attr-defined]

    try:
        ip = get_ipython()  # type: ignore[name-defined]
    except NameError:
        sys.displayhook = display_hook
    else:
        from IPython.core.formatters import BaseFormatter

        class RichFormatter(BaseFormatter):  # type: ignore[misc]
            pprint: bool = True

            def __call__(self, value: Any) -> Any:
                if self.pprint:
                    return _ipy_display_hook(
                        value,
                        console=get_console(),
                        overflow=overflow,
                        indent_guides=indent_guides,
                        max_length=max_length,
                        max_string=max_string,
                        max_depth=max_depth,
                        expand_all=expand_all,
                    )
                else:
                    return repr(value)

        # replace plain text formatter with rich formatter
        rich_formatter = RichFormatter()
        ip.display_formatter.formatters["text/plain"] = rich_formatter


class Pretty(JupyterMixin):
    """A rich renderable that pretty prints an object.

    Args:
        _object (Any): An object to pretty print.
        highlighter (HighlighterType, optional): Highlighter object to apply to result, or None for ReprHighlighter. Defaults to None.
        indent_size (int, optional): Number of spaces in indent. Defaults to 4.
        justify (JustifyMethod, optional): Justify method, or None for default. Defaults to None.
        overflow (OverflowMethod, optional): Overflow method, or None for default. Defaults to None.
        no_wrap (Optional[bool], optional): Disable word wrapping. Defaults to False.
        indent_guides (bool, optional): Enable indentation guides. Defaults to False.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable. Defaults to None.
        max_depth (int, optional): Maximum depth of nested data structures, or None for no maximum. Defaults to None.
        expand_all (bool, optional): Expand all containers. Defaults to False.
        margin (int, optional): Subtrace a margin from width to force containers to expand earlier. Defaults to 0.
        insert_line (bool, optional): Insert a new line if the output has multiple new lines. Defaults to False.
    """

    def __init__(
        self,
        _object: Any,
        highlighter: Optional["HighlighterType"] = None,
        *,
        indent_size: int = 4,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = False,
        indent_guides: bool = False,
        max_length: Optional[int] = None,
        max_string: Optional[int] = None,
        max_depth: Optional[int] = None,
        expand_all: bool = False,
        margin: int = 0,
        insert_line: bool = False,
    ) -> None:
        self._object = _object
        self.highlighter = highlighter or ReprHighlighter()
        self.indent_size = indent_size
        self.justify: Optional["JustifyMethod"] = justify
        self.overflow: Optional["OverflowMethod"] = overflow
        self.no_wrap = no_wrap
        self.indent_guides = indent_guides
        self.max_length = max_length
        self.max_string = max_string
        self.max_depth = max_depth
        self.expand_all = expand_all
        self.margin = margin
        self.insert_line = insert_line

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        pretty_str = pretty_repr(
            self._object,
            max_width=options.max_width - self.margin,
            indent_size=self.indent_size,
            max_length=self.max_length,
            max_string=self.max_string,
            max_depth=self.max_depth,
            expand_all=self.expand_all,
        )
        pretty_text = Text.from_ansi(
            pretty_str,
            justify=self.justify or options.justify,
            overflow=self.overflow or options.overflow,
            no_wrap=pick_bool(self.no_wrap, options.no_wrap),
            style="pretty",
        )
        pretty_text = (
            self.highlighter(pretty_text)
            if pretty_text
            else Text(
                f"{type(self._object)}.__repr__ returned empty string",
                style="dim italic",
            )
        )
        if self.indent_guides and not options.ascii_only:
            pretty_text = pretty_text.with_indent_guides(
                self.indent_size, style="repr.indent"
            )
        if self.insert_line and "\n" in pretty_text:
            yield ""
        yield pretty_text

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        pretty_str = pretty_repr(
            self._object,
            max_width=options.max_width,
            indent_size=self.indent_size,
            max_length=self.max_length,
            max_string=self.max_string,
            max_depth=self.max_depth,
            expand_all=self.expand_all,
        )
        text_width = (
            max(cell_len(line) for line in pretty_str.splitlines()) if pretty_str else 0
        )
        return Measurement(text_width, text_width)


def _get_braces_for_defaultdict(_object: DefaultDict[Any, Any]) -> Tuple[str, str, str]:
    return (
        f"defaultdict({_object.default_factory!r}, {{",
        "})",
        f"defaultdict({_object.default_factory!r}, {{}})",
    )


def _get_braces_for_deque(_object: Deque[Any]) -> Tuple[str, str, str]:
    if _object.maxlen is None:
        return ("deque([", "])", "deque()")
    return (
        "deque([",
        f"], maxlen={_object.maxlen})",
        f"deque(maxlen={_object.maxlen})",
    )


def _get_braces_for_array(_object: "array[Any]") -> Tuple[str, str, str]:
    return (f"array({_object.typecode!r}, [", "])", f"array({_object.typecode!r})")


_BRACES: Dict[type, Callable[[Any], Tuple[str, str, str]]] = {
    os._Environ: lambda _object: ("environ({", "})", "environ({})"),
    array: _get_braces_for_array,
    defaultdict: _get_braces_for_defaultdict,
    Counter: lambda _object: ("Counter({", "})", "Counter()"),
    deque: _get_braces_for_deque,
    dict: lambda _object: ("{", "}", "{}"),
    UserDict: lambda _object: ("{", "}", "{}"),
    frozenset: lambda _object: ("frozenset({", "})", "frozenset()"),
    list: lambda _object: ("[", "]", "[]"),
    UserList: lambda _object: ("[", "]", "[]"),
    set: lambda _object: ("{", "}", "set()"),
    tuple: lambda _object: ("(", ")", "()"),
    MappingProxyType: lambda _object: ("mappingproxy({", "})", "mappingproxy({})"),
}
_CONTAINERS = tuple(_BRACES.keys())
_MAPPING_CONTAINERS = (dict, os._Environ, MappingProxyType, UserDict)


def is_expandable(obj: Any) -> bool:
    """Check if an object may be expanded by pretty print."""
    return (
        _safe_isinstance(obj, _CONTAINERS)
        or (is_dataclass(obj))
        or (hasattr(obj, "__rich_repr__"))
        or _is_attr_object(obj)
    ) and not isclass(obj)


@dataclass
class Node:
    """A node in a repr tree. May be atomic or a container."""

    key_repr: str = ""
    value_repr: str = ""
    open_brace: str = ""
    close_brace: str = ""
    empty: str = ""
    last: bool = False
    is_tuple: bool = False
    is_namedtuple: bool = False
    children: Optional[List["Node"]] = None
    key_separator: str = ": "
    separator: str = ", "

    def iter_tokens(self) -> Iterable[str]:
        """Generate tokens for this node."""
        if self.key_repr:
            yield self.key_repr
            yield self.key_separator
        if self.value_repr:
            yield self.value_repr
        elif self.children is not None:
            if self.children:
                yield self.open_brace
                if self.is_tuple and not self.is_namedtuple and len(self.children) == 1:
                    yield from self.children[0].iter_tokens()
                    yield ","
                else:
                    for child in self.children:
                        yield from child.iter_tokens()
                        if not child.last:
                            yield self.separator
                yield self.close_brace
            else:
                yield self.empty

    def check_length(self, start_length: int, max_length: int) -> bool:
        """Check the length fits within a limit.

        Args:
            start_length (int): Starting length of the line (indent, prefix, suffix).
            max_length (int): Maximum length.

        Returns:
            bool: True if the node can be rendered within max length, otherwise False.
        """
        total_length = start_length
        for token in self.iter_tokens():
            total_length += cell_len(token)
            if total_length > max_length:
                return False
        return True

    def __str__(self) -> str:
        repr_text = "".join(self.iter_tokens())
        return repr_text

    def render(
        self, max_width: int = 80, indent_size: int = 4, expand_all: bool = False
    ) -> str:
        """Render the node to a pretty repr.

        Args:
            max_width (int, optional): Maximum width of the repr. Defaults to 80.
            indent_size (int, optional): Size of indents. Defaults to 4.
            expand_all (bool, optional): Expand all levels. Defaults to False.

        Returns:
            str: A repr string of the original object.
        """
        lines = [_Line(node=self, is_root=True)]
        line_no = 0
        while line_no < len(lines):
            line = lines[line_no]
            if line.expandable and not line.expanded:
                if expand_all or not line.check_length(max_width):
                    lines[line_no : line_no + 1] = line.expand(indent_size)
            line_no += 1

        repr_str = "\n".join(str(line) for line in lines)
        return repr_str


@dataclass
class _Line:
    """A line in repr output."""

    parent: Optional["_Line"] = None
    is_root: bool = False
    node: Optional[Node] = None
    text: str = ""
    suffix: str = ""
    whitespace: str = ""
    expanded: bool = False
    last: bool = False

    @property
    def expandable(self) -> bool:
        """Check if the line may be expanded."""
        return bool(self.node is not None and self.node.children)

    def check_length(self, max_length: int) -> bool:
        """Check this line fits within a given number of cells."""
        start_length = (
            len(self.whitespace) + cell_len(self.text) + cell_len(self.suffix)
        )
        assert self.node is not None
        return self.node.check_length(start_length, max_length)

    def expand(self, indent_size: int) -> Iterable["_Line"]:
        """Expand this line by adding children on their own line."""
        node = self.node
        assert node is not None
        whitespace = self.whitespace
        assert node.children
        if node.key_repr:
            new_line = yield _Line(
                text=f"{node.key_repr}{node.key_separator}{node.open_brace}",
                whitespace=whitespace,
            )
        else:
            new_line = yield _Line(text=node.open_brace, whitespace=whitespace)
        child_whitespace = self.whitespace + " " * indent_size
        tuple_of_one = node.is_tuple and len(node.children) == 1
        for last, child in loop_last(node.children):
            separator = "," if tuple_of_one else node.separator
            line = _Line(
                parent=new_line,
                node=child,
                whitespace=child_whitespace,
                suffix=separator,
                last=last and not tuple_of_one,
            )
            yield line

        yield _Line(
            text=node.close_brace,
            whitespace=whitespace,
            suffix=self.suffix,
            last=self.last,
        )

    def __str__(self) -> str:
        if self.last:
            return f"{self.whitespace}{self.text}{self.node or ''}"
        else:
            return (
                f"{self.whitespace}{self.text}{self.node or ''}{self.suffix.rstrip()}"
            )


def _is_namedtuple(obj: Any) -> bool:
    """Checks if an object is most likely a namedtuple. It is possible
    to craft an object that passes this check and isn't a namedtuple, but
    there is only a minuscule chance of this happening unintentionally.

    Args:
        obj (Any): The object to test

    Returns:
        bool: True if the object is a namedtuple. False otherwise.
    """
    try:
        fields = getattr(obj, "_fields", None)
    except Exception:
        # Being very defensive - if we cannot get the attr then its not a namedtuple
        return False
    return isinstance(obj, tuple) and isinstance(fields, tuple)


def traverse(
    _object: Any,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
) -> Node:
    """Traverse object and generate a tree.

    Args:
        _object (Any): Object to be traversed.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable truncating.
            Defaults to None.
        max_depth (int, optional): Maximum depth of data structures, or None for no maximum.
            Defaults to None.

    Returns:
        Node: The root of a tree structure which can be used to render a pretty repr.
    """

    def to_repr(obj: Any) -> str:
        """Get repr string for an object, but catch errors."""
        if (
            max_string is not None
            and _safe_isinstance(obj, (bytes, str))
            and len(obj) > max_string
        ):
            truncated = len(obj) - max_string
            obj_repr = f"{obj[:max_string]!r}+{truncated}"
        else:
            try:
                obj_repr = repr(obj)
            except Exception as error:
                obj_repr = f"<repr-error {str(error)!r}>"
        return obj_repr

    visited_ids: Set[int] = set()
    push_visited = visited_ids.add
    pop_visited = visited_ids.remove

    def _traverse(obj: Any, root: bool = False, depth: int = 0) -> Node:
        """Walk the object depth first."""

        obj_id = id(obj)
        if obj_id in visited_ids:
            # Recursion detected
            return Node(value_repr="...")

        obj_type = type(obj)
        children: List[Node]
        reached_max_depth = max_depth is not None and depth >= max_depth

        def iter_rich_args(rich_args: Any) -> Iterable[Union[Any, Tuple[str, Any]]]:
            for arg in rich_args:
                if _safe_isinstance(arg, tuple):
                    if len(arg) == 3:
                        key, child, default = arg
                        if default == child:
                            continue
                        yield key, child
                    elif len(arg) == 2:
                        key, child = arg
                        yield key, child
                    elif len(arg) == 1:
                        yield arg[0]
                else:
                    yield arg

        try:
            fake_attributes = hasattr(
                obj, "awehoi234_wdfjwljet234_234wdfoijsdfmmnxpi492"
            )
        except Exception:
            fake_attributes = False

        rich_repr_result: Optional[RichReprResult] = None
        if not fake_attributes:
            try:
                if hasattr(obj, "__rich_repr__") and not isclass(obj):
                    rich_repr_result = obj.__rich_repr__()
            except Exception:
                pass

        if rich_repr_result is not None:
            push_visited(obj_id)
            angular = getattr(obj.__rich_repr__, "angular", False)
            args = list(iter_rich_args(rich_repr_result))
            class_name = obj.__class__.__name__

            if args:
                children = []
                append = children.append

                if reached_max_depth:
                    if angular:
                        node = Node(value_repr=f"<{class_name}...>")
                    else:
                        node = Node(value_repr=f"{class_name}(...)")
                else:
                    if angular:
                        node = Node(
                            open_brace=f"<{class_name} ",
                            close_brace=">",
                            children=children,
                            last=root,
                            separator=" ",
                        )
                    else:
                        node = Node(
                            open_brace=f"{class_name}(",
                            close_brace=")",
                            children=children,
                            last=root,
                        )
                    for last, arg in loop_last(args):
                        if _safe_isinstance(arg, tuple):
                            key, child = arg
                            child_node = _traverse(child, depth=depth + 1)
                            child_node.last = last
                            child_node.key_repr = key
                            child_node.key_separator = "="
                            append(child_node)
                        else:
                            child_node = _traverse(arg, depth=depth + 1)
                            child_node.last = last
                            append(child_node)
            else:
                node = Node(
                    value_repr=f"<{class_name}>" if angular else f"{class_name}()",
                    children=[],
                    last=root,
                )
            pop_visited(obj_id)
        elif _is_attr_object(obj) and not fake_attributes:
            push_visited(obj_id)
            children = []
            append = children.append

            attr_fields = _get_attr_fields(obj)
            if attr_fields:
                if reached_max_depth:
                    node = Node(value_repr=f"{obj.__class__.__name__}(...)")
                else:
                    node = Node(
                        open_brace=f"{obj.__class__.__name__}(",
                        close_brace=")",
                        children=children,
                        last=root,
                    )

                    def iter_attrs() -> (
                        Iterable[Tuple[str, Any, Optional[Callable[[Any], str]]]]
                    ):
                        """Iterate over attr fields and values."""
                        for attr in attr_fields:
                            if attr.repr:
                                try:
                                    value = getattr(obj, attr.name)
                                except Exception as error:
                                    # Can happen, albeit rarely
                                    yield (attr.name, error, None)
                                else:
                                    yield (
                                        attr.name,
                                        value,
                                        attr.repr if callable(attr.repr) else None,
                                    )

                    for last, (name, value, repr_callable) in loop_last(iter_attrs()):
                        if repr_callable:
                            child_node = Node(value_repr=str(repr_callable(value)))
                        else:
                            child_node = _traverse(value, depth=depth + 1)
                        child_node.last = last
                        child_node.key_repr = name
                        child_node.key_separator = "="
                        append(child_node)
            else:
                node = Node(
                    value_repr=f"{obj.__class__.__name__}()", children=[], last=root
                )
            pop_visited(obj_id)
        elif (
            is_dataclass(obj)
            and not _safe_isinstance(obj, type)
            and not fake_attributes
            and _is_dataclass_repr(obj)
        ):
            push_visited(obj_id)
            children = []
            append = children.append
            if reached_max_depth:
                node = Node(value_repr=f"{obj.__class__.__name__}(...)")
            else:
                node = Node(
                    open_brace=f"{obj.__class__.__name__}(",
                    close_brace=")",
                    children=children,
                    last=root,
                    empty=f"{obj.__class__.__name__}()",
                )

                for last, field in loop_last(
                    field
                    for field in fields(obj)
                    if field.repr and hasattr(obj, field.name)
                ):
                    child_node = _traverse(getattr(obj, field.name), depth=depth + 1)
                    child_node.key_repr = field.name
                    child_node.last = last
                    child_node.key_separator = "="
                    append(child_node)

            pop_visited(obj_id)
        elif _is_namedtuple(obj) and _has_default_namedtuple_repr(obj):
            push_visited(obj_id)
            class_name = obj.__class__.__name__
            if reached_max_depth:
                # If we've reached the max depth, we still show the class name, but not its contents
                node = Node(
                    value_repr=f"{class_name}(...)",
                )
            else:
                children = []
                append = children.append
                node = Node(
                    open_brace=f"{class_name}(",
                    close_brace=")",
                    children=children,
                    empty=f"{class_name}()",
                )
                for last, (key, value) in loop_last(obj._asdict().items()):
                    child_node = _traverse(value, depth=depth + 1)
                    child_node.key_repr = key
                    child_node.last = last
                    child_node.key_separator = "="
                    append(child_node)
            pop_visited(obj_id)
        elif _safe_isinstance(obj, _CONTAINERS):
            for container_type in _CONTAINERS:
                if _safe_isinstance(obj, container_type):
                    obj_type = container_type
                    break

            push_visited(obj_id)

            open_brace, close_brace, empty = _BRACES[obj_type](obj)

            if reached_max_depth:
                node = Node(value_repr=f"{open_brace}...{close_brace}")
            elif obj_type.__repr__ != type(obj).__repr__:
                node = Node(value_repr=to_repr(obj), last=root)
            elif obj:
                children = []
                node = Node(
                    open_brace=open_brace,
                    close_brace=close_brace,
                    children=children,
                    last=root,
                )
                append = children.append
                num_items = len(obj)
                last_item_index = num_items - 1

                if _safe_isinstance(obj, _MAPPING_CONTAINERS):
                    iter_items = iter(obj.items())
                    if max_length is not None:
                        iter_items = islice(iter_items, max_length)
                    for index, (key, child) in enumerate(iter_items):
                        child_node = _traverse(child, depth=depth + 1)
                        child_node.key_repr = to_repr(key)
                        child_node.last = index == last_item_index
                        append(child_node)
                else:
                    iter_values = iter(obj)
                    if max_length is not None:
                        iter_values = islice(iter_values, max_length)
                    for index, child in enumerate(iter_values):
                        child_node = _traverse(child, depth=depth + 1)
                        child_node.last = index == last_item_index
                        append(child_node)
                if max_length is not None and num_items > max_length:
                    append(Node(value_repr=f"... +{num_items - max_length}", last=True))
            else:
                node = Node(empty=empty, children=[], last=root)

            pop_visited(obj_id)
        else:
            node = Node(value_repr=to_repr(obj), last=root)
        node.is_tuple = type(obj) == tuple
        node.is_namedtuple = _is_namedtuple(obj)
        return node

    node = _traverse(_object, root=True)
    return node


def pretty_repr(
    _object: Any,
    *,
    max_width: int = 80,
    indent_size: int = 4,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> str:
    """Prettify repr string by expanding on to new lines to fit within a given width.

    Args:
        _object (Any): Object to repr.
        max_width (int, optional): Desired maximum width of repr string. Defaults to 80.
        indent_size (int, optional): Number of spaces to indent. Defaults to 4.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of string before truncating, or None to disable truncating.
            Defaults to None.
        max_depth (int, optional): Maximum depth of nested data structure, or None for no depth.
            Defaults to None.
        expand_all (bool, optional): Expand all containers regardless of available width. Defaults to False.

    Returns:
        str: A possibly multi-line representation of the object.
    """

    if _safe_isinstance(_object, Node):
        node = _object
    else:
        node = traverse(
            _object, max_length=max_length, max_string=max_string, max_depth=max_depth
        )
    repr_str: str = node.render(
        max_width=max_width, indent_size=indent_size, expand_all=expand_all
    )
    return repr_str


def pprint(
    _object: Any,
    *,
    console: Optional["Console"] = None,
    indent_guides: bool = True,
    max_length: Optional[int] = None,
    max_string: Optional[int] = None,
    max_depth: Optional[int] = None,
    expand_all: bool = False,
) -> None:
    """A convenience function for pretty printing.

    Args:
        _object (Any): Object to pretty print.
        console (Console, optional): Console instance, or None to use default. Defaults to None.
        max_length (int, optional): Maximum length of containers before abbreviating, or None for no abbreviation.
            Defaults to None.
        max_string (int, optional): Maximum length of strings before truncating, or None to disable. Defaults to None.
        max_depth (int, optional): Maximum depth for nested data structures, or None for unlimited depth. Defaults to None.
        indent_guides (bool, optional): Enable indentation guides. Defaults to True.
        expand_all (bool, optional): Expand all containers. Defaults to False.
    """
    _console = get_console() if console is None else console
    _console.print(
        Pretty(
            _object,
            max_length=max_length,
            max_string=max_string,
            max_depth=max_depth,
            indent_guides=indent_guides,
            expand_all=expand_all,
            overflow="ignore",
        ),
        soft_wrap=True,
    )


if __name__ == "__main__":  # pragma: no cover

    class BrokenRepr:
        def __repr__(self) -> str:
            1 / 0
            return "this will fail"

    from typing import NamedTuple

    class StockKeepingUnit(NamedTuple):
        name: str
        description: str
        price: float
        category: str
        reviews: List[str]

    d = defaultdict(int)
    d["foo"] = 5
    data = {
        "foo": [
            1,
            "Hello World!",
            100.123,
            323.232,
            432324.0,
            {5, 6, 7, (1, 2, 3, 4), 8},
        ],
        "bar": frozenset({1, 2, 3}),
        "defaultdict": defaultdict(
            list, {"crumble": ["apple", "rhubarb", "butter", "sugar", "flour"]}
        ),
        "counter": Counter(
            [
                "apple",
                "orange",
                "pear",
                "kumquat",
                "kumquat",
                "durian" * 100,
            ]
        ),
        "atomic": (False, True, None),
        "namedtuple": StockKeepingUnit(
            "Sparkling British Spring Water",
            "Carbonated spring water",
            0.9,
            "water",
            ["its amazing!", "its terrible!"],
        ),
        "Broken": BrokenRepr(),
    }
    data["foo"].append(data)  # type: ignore[attr-defined]

    from rich import print

    print(Pretty(data, indent_guides=True, max_string=20))

    class Thing:
        def __repr__(self) -> str:
            return "Hello\x1b[38;5;239m World!"

    print(Pretty(Thing()))

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\text_service\client.py ===
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
import os
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
    cast,
)
import warnings

from google.api_core import client_options as client_options_lib
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.exceptions import MutualTLSChannelError  # type: ignore
from google.auth.transport import mtls  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta2 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore

from google.ai.generativelanguage_v1beta2.types import safety, text_service

from .transports.base import DEFAULT_CLIENT_INFO, TextServiceTransport
from .transports.grpc import TextServiceGrpcTransport
from .transports.grpc_asyncio import TextServiceGrpcAsyncIOTransport
from .transports.rest import TextServiceRestTransport


class TextServiceClientMeta(type):
    """Metaclass for the TextService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = OrderedDict()  # type: Dict[str, Type[TextServiceTransport]]
    _transport_registry["grpc"] = TextServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = TextServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = TextServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[TextServiceTransport]:
        """Returns an appropriate transport class.

        Args:
            label: The name of the desired transport. If none is
                provided, then the first transport in the registry is used.

        Returns:
            The transport class to use.
        """
        # If a specific transport is requested, return that one.
        if label:
            return cls._transport_registry[label]

        # No transport is requested; return the default (that is, the first one
        # in the dictionary).
        return next(iter(cls._transport_registry.values()))


class TextServiceClient(metaclass=TextServiceClientMeta):
    """API for using Generative Language Models (GLMs) trained to
    generate text.
    Also known as Large Language Models (LLM)s, these generate text
    given an input prompt from the user.
    """

    @staticmethod
    def _get_default_mtls_endpoint(api_endpoint):
        """Converts api endpoint to mTLS endpoint.

        Convert "*.sandbox.googleapis.com" and "*.googleapis.com" to
        "*.mtls.sandbox.googleapis.com" and "*.mtls.googleapis.com" respectively.
        Args:
            api_endpoint (Optional[str]): the api endpoint to convert.
        Returns:
            str: converted mTLS api endpoint.
        """
        if not api_endpoint:
            return api_endpoint

        mtls_endpoint_re = re.compile(
            r"(?P<name>[^.]+)(?P<mtls>\.mtls)?(?P<sandbox>\.sandbox)?(?P<googledomain>\.googleapis\.com)?"
        )

        m = mtls_endpoint_re.match(api_endpoint)
        name, mtls, sandbox, googledomain = m.groups()
        if mtls or not googledomain:
            return api_endpoint

        if sandbox:
            return api_endpoint.replace(
                "sandbox.googleapis.com", "mtls.sandbox.googleapis.com"
            )

        return api_endpoint.replace(".googleapis.com", ".mtls.googleapis.com")

    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = "generativelanguage.googleapis.com"
    DEFAULT_MTLS_ENDPOINT = _get_default_mtls_endpoint.__func__(  # type: ignore
        DEFAULT_ENDPOINT
    )

    _DEFAULT_ENDPOINT_TEMPLATE = "generativelanguage.{UNIVERSE_DOMAIN}"
    _DEFAULT_UNIVERSE = "googleapis.com"

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            TextServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_info(info)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

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
            TextServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> TextServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            TextServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def model_path(
        model: str,
    ) -> str:
        """Returns a fully-qualified model string."""
        return "models/{model}".format(
            model=model,
        )

    @staticmethod
    def parse_model_path(path: str) -> Dict[str, str]:
        """Parses a model path into its component segments."""
        m = re.match(r"^models/(?P<model>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_billing_account_path(
        billing_account: str,
    ) -> str:
        """Returns a fully-qualified billing_account string."""
        return "billingAccounts/{billing_account}".format(
            billing_account=billing_account,
        )

    @staticmethod
    def parse_common_billing_account_path(path: str) -> Dict[str, str]:
        """Parse a billing_account path into its component segments."""
        m = re.match(r"^billingAccounts/(?P<billing_account>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_folder_path(
        folder: str,
    ) -> str:
        """Returns a fully-qualified folder string."""
        return "folders/{folder}".format(
            folder=folder,
        )

    @staticmethod
    def parse_common_folder_path(path: str) -> Dict[str, str]:
        """Parse a folder path into its component segments."""
        m = re.match(r"^folders/(?P<folder>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_organization_path(
        organization: str,
    ) -> str:
        """Returns a fully-qualified organization string."""
        return "organizations/{organization}".format(
            organization=organization,
        )

    @staticmethod
    def parse_common_organization_path(path: str) -> Dict[str, str]:
        """Parse a organization path into its component segments."""
        m = re.match(r"^organizations/(?P<organization>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_project_path(
        project: str,
    ) -> str:
        """Returns a fully-qualified project string."""
        return "projects/{project}".format(
            project=project,
        )

    @staticmethod
    def parse_common_project_path(path: str) -> Dict[str, str]:
        """Parse a project path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_location_path(
        project: str,
        location: str,
    ) -> str:
        """Returns a fully-qualified location string."""
        return "projects/{project}/locations/{location}".format(
            project=project,
            location=location,
        )

    @staticmethod
    def parse_common_location_path(path: str) -> Dict[str, str]:
        """Parse a location path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)/locations/(?P<location>.+?)$", path)
        return m.groupdict() if m else {}

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[client_options_lib.ClientOptions] = None
    ):
        """Deprecated. Return the API endpoint and client cert source for mutual TLS.

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

        warnings.warn(
            "get_mtls_endpoint_and_cert_source is deprecated. Use the api_endpoint property instead.",
            DeprecationWarning,
        )
        if client_options is None:
            client_options = client_options_lib.ClientOptions()
        use_client_cert = os.getenv("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )

        # Figure out the client cert source to use.
        client_cert_source = None
        if use_client_cert == "true":
            if client_options.client_cert_source:
                client_cert_source = client_options.client_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()

        # Figure out which api endpoint to use.
        if client_options.api_endpoint is not None:
            api_endpoint = client_options.api_endpoint
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            api_endpoint = cls.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = cls.DEFAULT_ENDPOINT

        return api_endpoint, client_cert_source

    @staticmethod
    def _read_environment_variables():
        """Returns the environment variables used by the client.

        Returns:
            Tuple[bool, str, str]: returns the GOOGLE_API_USE_CLIENT_CERTIFICATE,
            GOOGLE_API_USE_MTLS_ENDPOINT, and GOOGLE_CLOUD_UNIVERSE_DOMAIN environment variables.

        Raises:
            ValueError: If GOOGLE_API_USE_CLIENT_CERTIFICATE is not
                any of ["true", "false"].
            google.auth.exceptions.MutualTLSChannelError: If GOOGLE_API_USE_MTLS_ENDPOINT
                is not any of ["auto", "never", "always"].
        """
        use_client_cert = os.getenv(
            "GOOGLE_API_USE_CLIENT_CERTIFICATE", "false"
        ).lower()
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto").lower()
        universe_domain_env = os.getenv("GOOGLE_CLOUD_UNIVERSE_DOMAIN")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )
        return use_client_cert == "true", use_mtls_endpoint, universe_domain_env

    @staticmethod
    def _get_client_cert_source(provided_cert_source, use_cert_flag):
        """Return the client cert source to be used by the client.

        Args:
            provided_cert_source (bytes): The client certificate source provided.
            use_cert_flag (bool): A flag indicating whether to use the client certificate.

        Returns:
            bytes or None: The client cert source to be used by the client.
        """
        client_cert_source = None
        if use_cert_flag:
            if provided_cert_source:
                client_cert_source = provided_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()
        return client_cert_source

    @staticmethod
    def _get_api_endpoint(
        api_override, client_cert_source, universe_domain, use_mtls_endpoint
    ):
        """Return the API endpoint used by the client.

        Args:
            api_override (str): The API endpoint override. If specified, this is always
                the return value of this function and the other arguments are not used.
            client_cert_source (bytes): The client certificate source used by the client.
            universe_domain (str): The universe domain used by the client.
            use_mtls_endpoint (str): How to use the mTLS endpoint, which depends also on the other parameters.
                Possible values are "always", "auto", or "never".

        Returns:
            str: The API endpoint to be used by the client.
        """
        if api_override is not None:
            api_endpoint = api_override
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            _default_universe = TextServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = TextServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = TextServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
                UNIVERSE_DOMAIN=universe_domain
            )
        return api_endpoint

    @staticmethod
    def _get_universe_domain(
        client_universe_domain: Optional[str], universe_domain_env: Optional[str]
    ) -> str:
        """Return the universe domain used by the client.

        Args:
            client_universe_domain (Optional[str]): The universe domain configured via the client options.
            universe_domain_env (Optional[str]): The universe domain configured via the "GOOGLE_CLOUD_UNIVERSE_DOMAIN" environment variable.

        Returns:
            str: The universe domain to be used by the client.

        Raises:
            ValueError: If the universe domain is an empty string.
        """
        universe_domain = TextServiceClient._DEFAULT_UNIVERSE
        if client_universe_domain is not None:
            universe_domain = client_universe_domain
        elif universe_domain_env is not None:
            universe_domain = universe_domain_env
        if len(universe_domain.strip()) == 0:
            raise ValueError("Universe Domain cannot be an empty string.")
        return universe_domain

    @staticmethod
    def _compare_universes(
        client_universe: str, credentials: ga_credentials.Credentials
    ) -> bool:
        """Returns True iff the universe domains used by the client and credentials match.

        Args:
            client_universe (str): The universe domain configured via the client options.
            credentials (ga_credentials.Credentials): The credentials being used in the client.

        Returns:
            bool: True iff client_universe matches the universe in credentials.

        Raises:
            ValueError: when client_universe does not match the universe in credentials.
        """

        default_universe = TextServiceClient._DEFAULT_UNIVERSE
        credentials_universe = getattr(credentials, "universe_domain", default_universe)

        if client_universe != credentials_universe:
            raise ValueError(
                "The configured universe domain "
                f"({client_universe}) does not match the universe domain "
                f"found in the credentials ({credentials_universe}). "
                "If you haven't configured the universe domain explicitly, "
                f"`{default_universe}` is the default."
            )
        return True

    def _validate_universe_domain(self):
        """Validates client's and credentials' universe domains are consistent.

        Returns:
            bool: True iff the configured universe domain is valid.

        Raises:
            ValueError: If the configured universe domain is not valid.
        """
        self._is_universe_domain_valid = (
            self._is_universe_domain_valid
            or TextServiceClient._compare_universes(
                self.universe_domain, self.transport._credentials
            )
        )
        return self._is_universe_domain_valid

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used by the client instance.
        """
        return self._universe_domain

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, TextServiceTransport, Callable[..., TextServiceTransport]]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the text service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,TextServiceTransport,Callable[..., TextServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the TextServiceTransport constructor.
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
                default "googleapis.com" universe. Note that the ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client_options = client_options
        if isinstance(self._client_options, dict):
            self._client_options = client_options_lib.from_dict(self._client_options)
        if self._client_options is None:
            self._client_options = client_options_lib.ClientOptions()
        self._client_options = cast(
            client_options_lib.ClientOptions, self._client_options
        )

        universe_domain_opt = getattr(self._client_options, "universe_domain", None)

        (
            self._use_client_cert,
            self._use_mtls_endpoint,
            self._universe_domain_env,
        ) = TextServiceClient._read_environment_variables()
        self._client_cert_source = TextServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = TextServiceClient._get_universe_domain(
            universe_domain_opt, self._universe_domain_env
        )
        self._api_endpoint = None  # updated below, depending on `transport`

        # Initialize the universe domain validation.
        self._is_universe_domain_valid = False

        api_key_value = getattr(self._client_options, "api_key", None)
        if api_key_value and credentials:
            raise ValueError(
                "client_options.api_key and credentials are mutually exclusive"
            )

        # Save or instantiate the transport.
        # Ordinarily, we provide the transport, but allowing a custom transport
        # instance provides an extensibility point for unusual situations.
        transport_provided = isinstance(transport, TextServiceTransport)
        if transport_provided:
            # transport is a TextServiceTransport instance.
            if credentials or self._client_options.credentials_file or api_key_value:
                raise ValueError(
                    "When providing a transport instance, "
                    "provide its credentials directly."
                )
            if self._client_options.scopes:
                raise ValueError(
                    "When providing a transport instance, provide its scopes "
                    "directly."
                )
            self._transport = cast(TextServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = self._api_endpoint or TextServiceClient._get_api_endpoint(
            self._client_options.api_endpoint,
            self._client_cert_source,
            self._universe_domain,
            self._use_mtls_endpoint,
        )

        if not transport_provided:
            import google.auth._default  # type: ignore

            if api_key_value and hasattr(
                google.auth._default, "get_api_key_credentials"
            ):
                credentials = google.auth._default.get_api_key_credentials(
                    api_key_value
                )

            transport_init: Union[
                Type[TextServiceTransport], Callable[..., TextServiceTransport]
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., TextServiceTransport], transport)
            )
            # initialize with the provided callable or the passed in class
            self._transport = transport_init(
                credentials=credentials,
                credentials_file=self._client_options.credentials_file,
                host=self._api_endpoint,
                scopes=self._client_options.scopes,
                client_cert_source_for_mtls=self._client_cert_source,
                quota_project_id=self._client_options.quota_project_id,
                client_info=client_info,
                always_use_jwt_access=True,
                api_audience=self._client_options.api_audience,
            )

    def generate_text(
        self,
        request: Optional[Union[text_service.GenerateTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[text_service.TextPrompt] = None,
        temperature: Optional[float] = None,
        candidate_count: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.GenerateTextResponse:
        r"""Generates a response from the model given an input
        message.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta2

            def sample_generate_text():
                # Create a client
                client = generativelanguage_v1beta2.TextServiceClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta2.TextPrompt()
                prompt.text = "text_value"

                request = generativelanguage_v1beta2.GenerateTextRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = client.generate_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta2.types.GenerateTextRequest, dict]):
                The request object. Request to generate a text completion
                response from the model.
            model (str):
                Required. The model name to use with
                the format name=models/{model}.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (google.ai.generativelanguage_v1beta2.types.TextPrompt):
                Required. The free-form input text
                given to the model as a prompt.
                Given a prompt, the model will generate
                a TextCompletion response it predicts as
                the completion of the input text.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            temperature (float):
                Controls the randomness of the output. Note: The default
                value varies by model, see the ``Model.temperature``
                attribute of the ``Model`` returned the ``getModel``
                function.

                Values can range from [0.0,1.0], inclusive. A value
                closer to 1.0 will produce responses that are more
                varied and creative, while a value closer to 0.0 will
                typically result in more straightforward responses from
                the model.

                This corresponds to the ``temperature`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            candidate_count (int):
                Number of generated responses to return.

                This value must be between [1, 8], inclusive. If unset,
                this will default to 1.

                This corresponds to the ``candidate_count`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            max_output_tokens (int):
                The maximum number of tokens to
                include in a candidate.
                If unset, this will default to 64.

                This corresponds to the ``max_output_tokens`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_p (float):
                The maximum cumulative probability of tokens to consider
                when sampling.

                The model uses combined Top-k and nucleus sampling.

                Tokens are sorted based on their assigned probabilities
                so that only the most liekly tokens are considered.
                Top-k sampling directly limits the maximum number of
                tokens to consider, while Nucleus sampling limits number
                of tokens based on the cumulative probability.

                Note: The default value varies by model, see the
                ``Model.top_p`` attribute of the ``Model`` returned the
                ``getModel`` function.

                This corresponds to the ``top_p`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_k (int):
                The maximum number of tokens to consider when sampling.

                The model uses combined Top-k and nucleus sampling.

                Top-k sampling considers the set of ``top_k`` most
                probable tokens. Defaults to 40.

                Note: The default value varies by model, see the
                ``Model.top_k`` attribute of the ``Model`` returned the
                ``getModel`` function.

                This corresponds to the ``top_k`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta2.types.GenerateTextResponse:
                The response from the model,
                including candidate completions.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any(
            [
                model,
                prompt,
                temperature,
                candidate_count,
                max_output_tokens,
                top_p,
                top_k,
            ]
        )
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.GenerateTextRequest):
            request = text_service.GenerateTextRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if prompt is not None:
                request.prompt = prompt
            if temperature is not None:
                request.temperature = temperature
            if candidate_count is not None:
                request.candidate_count = candidate_count
            if max_output_tokens is not None:
                request.max_output_tokens = max_output_tokens
            if top_p is not None:
                request.top_p = top_p
            if top_k is not None:
                request.top_k = top_k

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.generate_text]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def embed_text(
        self,
        request: Optional[Union[text_service.EmbedTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        text: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.EmbedTextResponse:
        r"""Generates an embedding from the model given an input
        message.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta2

            def sample_embed_text():
                # Create a client
                client = generativelanguage_v1beta2.TextServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta2.EmbedTextRequest(
                    model="model_value",
                    text="text_value",
                )

                # Make the request
                response = client.embed_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta2.types.EmbedTextRequest, dict]):
                The request object. Request to get a text embedding from
                the model.
            model (str):
                Required. The model name to use with
                the format model=models/{model}.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            text (str):
                Required. The free-form input text
                that the model will turn into an
                embedding.

                This corresponds to the ``text`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta2.types.EmbedTextResponse:
                The response to a EmbedTextRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, text])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.EmbedTextRequest):
            request = text_service.EmbedTextRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if text is not None:
                request.text = text

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.embed_text]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def __enter__(self) -> "TextServiceClient":
        return self

    def __exit__(self, type, value, traceback):
        """Releases underlying transport's resources.

        .. warning::
            ONLY use as a context manager if the transport is NOT shared
            with other clients! Exiting the with block will CLOSE the transport
            and may cause errors in other clients!
        """
        self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("TextServiceClient",)