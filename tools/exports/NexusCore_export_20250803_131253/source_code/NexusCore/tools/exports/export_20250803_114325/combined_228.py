
# === NexusCore/openenv\Lib\site-packages\nltk\translate\phrase_based.py ===
# Natural Language Toolkit: Phrase Extraction Algorithm
#
# Copyright (C) 2001-2024 NLTK Project
# Authors: Liling Tan, Fredrik Hedman, Petra Barancikova
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT


def extract(
    f_start,
    f_end,
    e_start,
    e_end,
    alignment,
    f_aligned,
    srctext,
    trgtext,
    srclen,
    trglen,
    max_phrase_length,
):
    """
    This function checks for alignment point consistency and extracts
    phrases using the chunk of consistent phrases.

    A phrase pair (e, f ) is consistent with an alignment A if and only if:

    (i) No English words in the phrase pair are aligned to words outside it.

           ∀e i ∈ e, (e i , f j ) ∈ A ⇒ f j ∈ f

    (ii) No Foreign words in the phrase pair are aligned to words outside it.

            ∀f j ∈ f , (e i , f j ) ∈ A ⇒ e i ∈ e

    (iii) The phrase pair contains at least one alignment point.

            ∃e i ∈ e  ̄ , f j ∈ f  ̄ s.t. (e i , f j ) ∈ A

    :type f_start: int
    :param f_start: Starting index of the possible foreign language phrases
    :type f_end: int
    :param f_end: End index of the possible foreign language phrases
    :type e_start: int
    :param e_start: Starting index of the possible source language phrases
    :type e_end: int
    :param e_end: End index of the possible source language phrases
    :type srctext: list
    :param srctext: The source language tokens, a list of string.
    :type trgtext: list
    :param trgtext: The target language tokens, a list of string.
    :type srclen: int
    :param srclen: The number of tokens in the source language tokens.
    :type trglen: int
    :param trglen: The number of tokens in the target language tokens.
    """

    if f_end < 0:  # 0-based indexing.
        return {}
    # Check if alignment points are consistent.
    for e, f in alignment:
        if (f_start <= f <= f_end) and (e < e_start or e > e_end):
            return {}

    # Add phrase pairs (incl. additional unaligned f)
    phrases = set()
    fs = f_start
    while True:
        fe = min(f_end, f_start + max_phrase_length - 1)
        while True:
            # add phrase pair ([e_start, e_end], [fs, fe]) to set E
            # Need to +1 in range  to include the end-point.
            src_phrase = " ".join(srctext[e_start : e_end + 1])
            trg_phrase = " ".join(trgtext[fs : fe + 1])
            # Include more data for later ordering.
            phrases.add(((e_start, e_end + 1), (fs, fe + 1), src_phrase, trg_phrase))
            fe += 1
            if fe in f_aligned or fe >= trglen:
                break
        fs -= 1
        if fs in f_aligned or fs < 0:
            break
    return phrases


def phrase_extraction(srctext, trgtext, alignment, max_phrase_length=0):
    """
    Phrase extraction algorithm extracts all consistent phrase pairs from
    a word-aligned sentence pair.

    The idea is to loop over all possible source language (e) phrases and find
    the minimal foreign phrase (f) that matches each of them. Matching is done
    by identifying all alignment points for the source phrase and finding the
    shortest foreign phrase that includes all the foreign counterparts for the
    source words.

    In short, a phrase alignment has to
    (a) contain all alignment points for all covered words
    (b) contain at least one alignment point

    >>> srctext = "michael assumes that he will stay in the house"
    >>> trgtext = "michael geht davon aus , dass er im haus bleibt"
    >>> alignment = [(0,0), (1,1), (1,2), (1,3), (2,5), (3,6), (4,9),
    ... (5,9), (6,7), (7,7), (8,8)]
    >>> phrases = phrase_extraction(srctext, trgtext, alignment)
    >>> for i in sorted(phrases):
    ...    print(i)
    ...
    ((0, 1), (0, 1), 'michael', 'michael')
    ((0, 2), (0, 4), 'michael assumes', 'michael geht davon aus')
    ((0, 2), (0, 5), 'michael assumes', 'michael geht davon aus ,')
    ((0, 3), (0, 6), 'michael assumes that', 'michael geht davon aus , dass')
    ((0, 4), (0, 7), 'michael assumes that he', 'michael geht davon aus , dass er')
    ((0, 9), (0, 10), 'michael assumes that he will stay in the house', 'michael geht davon aus , dass er im haus bleibt')
    ((1, 2), (1, 4), 'assumes', 'geht davon aus')
    ((1, 2), (1, 5), 'assumes', 'geht davon aus ,')
    ((1, 3), (1, 6), 'assumes that', 'geht davon aus , dass')
    ((1, 4), (1, 7), 'assumes that he', 'geht davon aus , dass er')
    ((1, 9), (1, 10), 'assumes that he will stay in the house', 'geht davon aus , dass er im haus bleibt')
    ((2, 3), (4, 6), 'that', ', dass')
    ((2, 3), (5, 6), 'that', 'dass')
    ((2, 4), (4, 7), 'that he', ', dass er')
    ((2, 4), (5, 7), 'that he', 'dass er')
    ((2, 9), (4, 10), 'that he will stay in the house', ', dass er im haus bleibt')
    ((2, 9), (5, 10), 'that he will stay in the house', 'dass er im haus bleibt')
    ((3, 4), (6, 7), 'he', 'er')
    ((3, 9), (6, 10), 'he will stay in the house', 'er im haus bleibt')
    ((4, 6), (9, 10), 'will stay', 'bleibt')
    ((4, 9), (7, 10), 'will stay in the house', 'im haus bleibt')
    ((6, 8), (7, 8), 'in the', 'im')
    ((6, 9), (7, 9), 'in the house', 'im haus')
    ((8, 9), (8, 9), 'house', 'haus')

    :type srctext: str
    :param srctext: The sentence string from the source language.
    :type trgtext: str
    :param trgtext: The sentence string from the target language.
    :type alignment: list(tuple)
    :param alignment: The word alignment outputs as list of tuples, where
        the first elements of tuples are the source words' indices and
        second elements are the target words' indices. This is also the output
        format of nltk.translate.ibm1
    :rtype: list(tuple)
    :return: A list of tuples, each element in a list is a phrase and each
        phrase is a tuple made up of (i) its source location, (ii) its target
        location, (iii) the source phrase and (iii) the target phrase. The phrase
        list of tuples represents all the possible phrases extracted from the
        word alignments.
    :type max_phrase_length: int
    :param max_phrase_length: maximal phrase length, if 0 or not specified
        it is set to a length of the longer sentence (srctext or trgtext).
    """

    srctext = srctext.split()  # e
    trgtext = trgtext.split()  # f
    srclen = len(srctext)  # len(e)
    trglen = len(trgtext)  # len(f)
    # Keeps an index of which source/target words that are aligned.
    f_aligned = [j for _, j in alignment]
    max_phrase_length = max_phrase_length or max(srclen, trglen)

    # set of phrase pairs BP
    bp = set()

    for e_start in range(srclen):
        max_idx = min(srclen, e_start + max_phrase_length)
        for e_end in range(e_start, max_idx):
            # // find the minimally matching foreign phrase
            # (f start , f end ) = ( length(f), 0 )
            # f_start ∈ [0, len(f) - 1]; f_end ∈ [0, len(f) - 1]
            f_start, f_end = trglen - 1, -1  #  0-based indexing

            for e, f in alignment:
                if e_start <= e <= e_end:
                    f_start = min(f, f_start)
                    f_end = max(f, f_end)
            # add extract (f start , f end , e start , e end ) to set BP
            phrases = extract(
                f_start,
                f_end,
                e_start,
                e_end,
                alignment,
                f_aligned,
                srctext,
                trgtext,
                srclen,
                trglen,
                max_phrase_length,
            )
            if phrases:
                bp.update(phrases)
    return bp

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\test_mock_clock.py ===
import time
from math import inf

import pytest

from trio import sleep

from ... import _core
from .. import wait_all_tasks_blocked
from .._mock_clock import MockClock
from .._run import GLOBAL_RUN_CONTEXT
from .tutil import slow


def test_mock_clock() -> None:
    REAL_NOW = 123.0
    c = MockClock()
    c._real_clock = lambda: REAL_NOW
    repr(c)  # smoke test
    assert c.rate == 0
    assert c.current_time() == 0
    c.jump(1.2)
    assert c.current_time() == 1.2
    with pytest.raises(ValueError, match=r"^time can't go backwards$"):
        c.jump(-1)
    assert c.current_time() == 1.2
    assert c.deadline_to_sleep_time(1.1) == 0
    assert c.deadline_to_sleep_time(1.2) == 0
    assert c.deadline_to_sleep_time(1.3) > 999999

    with pytest.raises(ValueError, match=r"^rate must be >= 0$"):
        c.rate = -1
    assert c.rate == 0

    c.rate = 2
    assert c.current_time() == 1.2
    REAL_NOW += 1
    assert c.current_time() == 3.2
    assert c.deadline_to_sleep_time(3.1) == 0
    assert c.deadline_to_sleep_time(3.2) == 0
    assert c.deadline_to_sleep_time(4.2) == 0.5

    c.rate = 0.5
    assert c.current_time() == 3.2
    assert c.deadline_to_sleep_time(3.1) == 0
    assert c.deadline_to_sleep_time(3.2) == 0
    assert c.deadline_to_sleep_time(4.2) == 2.0

    c.jump(0.8)
    assert c.current_time() == 4.0
    REAL_NOW += 1
    assert c.current_time() == 4.5

    c2 = MockClock(rate=3)
    assert c2.rate == 3
    assert c2.current_time() < 10


async def test_mock_clock_autojump(mock_clock: MockClock) -> None:
    assert mock_clock.autojump_threshold == inf

    mock_clock.autojump_threshold = 0
    assert mock_clock.autojump_threshold == 0

    real_start = time.perf_counter()

    virtual_start = _core.current_time()
    for i in range(10):
        print(f"sleeping {10 * i} seconds")
        await sleep(10 * i)
        print("woke up!")
        assert virtual_start + 10 * i == _core.current_time()
        virtual_start = _core.current_time()

    real_duration = time.perf_counter() - real_start
    print(f"Slept {10 * sum(range(10))} seconds in {real_duration} seconds")
    assert real_duration < 1

    mock_clock.autojump_threshold = 0.02
    t = _core.current_time()
    # this should wake up before the autojump threshold triggers, so time
    # shouldn't change
    await wait_all_tasks_blocked()
    assert t == _core.current_time()
    # this should too
    await wait_all_tasks_blocked(0.01)
    assert t == _core.current_time()

    # set up a situation where the autojump task is blocked for a long long
    # time, to make sure that cancel-and-adjust-threshold logic is working
    mock_clock.autojump_threshold = 10000
    await wait_all_tasks_blocked()
    mock_clock.autojump_threshold = 0
    # if the above line didn't take affect immediately, then this would be
    # bad:
    # ignore ASYNC116, not sleep_forever, trying to test a large but finite sleep
    await sleep(100000)  # noqa: ASYNC116


async def test_mock_clock_autojump_interference(mock_clock: MockClock) -> None:
    mock_clock.autojump_threshold = 0.02

    mock_clock2 = MockClock()
    # messing with the autojump threshold of a clock that isn't actually
    # installed in the run loop shouldn't do anything.
    mock_clock2.autojump_threshold = 0.01

    # if the autojump_threshold of 0.01 were in effect, then the next line
    # would block forever, as the autojump task kept waking up to try to
    # jump the clock.
    await wait_all_tasks_blocked(0.015)

    # but the 0.02 limit does apply
    # ignore ASYNC116, not sleep_forever, trying to test a large but finite sleep
    await sleep(100000)  # noqa: ASYNC116


def test_mock_clock_autojump_preset() -> None:
    # Check that we can set the autojump_threshold before the clock is
    # actually in use, and it gets picked up
    mock_clock = MockClock(autojump_threshold=0.1)
    mock_clock.autojump_threshold = 0.01
    real_start = time.perf_counter()
    _core.run(sleep, 10000, clock=mock_clock)
    assert time.perf_counter() - real_start < 1


async def test_mock_clock_autojump_0_and_wait_all_tasks_blocked_0(
    mock_clock: MockClock,
) -> None:
    # Checks that autojump_threshold=0 doesn't interfere with
    # calling wait_all_tasks_blocked with the default cushion=0.

    mock_clock.autojump_threshold = 0

    record = []

    async def sleeper() -> None:
        await sleep(100)
        record.append("yawn")

    async def waiter() -> None:
        await wait_all_tasks_blocked()
        record.append("waiter woke")
        await sleep(1000)
        record.append("waiter done")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(sleeper)
        nursery.start_soon(waiter)

    assert record == ["waiter woke", "yawn", "waiter done"]


@slow
async def test_mock_clock_autojump_0_and_wait_all_tasks_blocked_nonzero(
    mock_clock: MockClock,
) -> None:
    # Checks that autojump_threshold=0 doesn't interfere with
    # calling wait_all_tasks_blocked with a non-zero cushion.

    mock_clock.autojump_threshold = 0

    record = []

    async def sleeper() -> None:
        await sleep(100)
        record.append("yawn")

    async def waiter() -> None:
        await wait_all_tasks_blocked(1)
        record.append("waiter done")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(sleeper)
        nursery.start_soon(waiter)

    assert record == ["waiter done", "yawn"]


async def test_initialization_doesnt_mutate_runner() -> None:
    before = (
        GLOBAL_RUN_CONTEXT.runner.clock,
        GLOBAL_RUN_CONTEXT.runner.clock_autojump_threshold,
    )

    MockClock(autojump_threshold=2, rate=3)

    after = (
        GLOBAL_RUN_CONTEXT.runner.clock,
        GLOBAL_RUN_CONTEXT.runner.clock_autojump_threshold,
    )
    assert before == after

# === NexusCore/openenv\Lib\site-packages\jupyter_client\jsonutil.py ===
"""Utilities to manipulate JSON objects."""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import math
import numbers
import re
import types
import warnings
from binascii import b2a_base64
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Optional, Union

from dateutil.parser import isoparse as _dateutil_parse
from dateutil.tz import tzlocal

next_attr_name = "__next__"  # Not sure what downstream library uses this, but left it to be safe

# -----------------------------------------------------------------------------
# Globals and constants
# -----------------------------------------------------------------------------

# timestamp formats
ISO8601 = "%Y-%m-%dT%H:%M:%S.%f"
ISO8601_PAT = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d{1,6})?(Z|([\+\-]\d{2}:?\d{2}))?$"
)

# holy crap, strptime is not threadsafe.
# Calling it once at import seems to help.
datetime.strptime("2000-01-01", "%Y-%m-%d")  # noqa

# -----------------------------------------------------------------------------
# Classes and functions
# -----------------------------------------------------------------------------


def _ensure_tzinfo(dt: datetime) -> datetime:
    """Ensure a datetime object has tzinfo

    If no tzinfo is present, add tzlocal
    """
    if not dt.tzinfo:
        # No more naïve datetime objects!
        warnings.warn(
            "Interpreting naive datetime as local %s. Please add timezone info to timestamps." % dt,
            DeprecationWarning,
            stacklevel=4,
        )
        dt = dt.replace(tzinfo=tzlocal())
    return dt


def parse_date(s: Optional[str]) -> Optional[Union[str, datetime]]:
    """parse an ISO8601 date string

    If it is None or not a valid ISO8601 timestamp,
    it will be returned unmodified.
    Otherwise, it will return a datetime object.
    """
    if s is None:
        return s
    m = ISO8601_PAT.match(s)
    if m:
        dt = _dateutil_parse(s)
        return _ensure_tzinfo(dt)
    return s


def extract_dates(obj: Any) -> Any:
    """extract ISO8601 dates from unpacked JSON"""
    if isinstance(obj, dict):
        new_obj = {}  # don't clobber
        for k, v in obj.items():
            new_obj[k] = extract_dates(v)
        obj = new_obj
    elif isinstance(obj, (list, tuple)):
        obj = [extract_dates(o) for o in obj]
    elif isinstance(obj, str):
        obj = parse_date(obj)
    return obj


def squash_dates(obj: Any) -> Any:
    """squash datetime objects into ISO8601 strings"""
    if isinstance(obj, dict):
        obj = dict(obj)  # don't clobber
        for k, v in obj.items():
            obj[k] = squash_dates(v)
    elif isinstance(obj, (list, tuple)):
        obj = [squash_dates(o) for o in obj]
    elif isinstance(obj, datetime):
        obj = obj.isoformat()
    return obj


def date_default(obj: Any) -> Any:
    """DEPRECATED: Use jupyter_client.jsonutil.json_default"""
    warnings.warn(
        "date_default is deprecated since jupyter_client 7.0.0."
        " Use jupyter_client.jsonutil.json_default.",
        stacklevel=2,
    )
    return json_default(obj)


def json_default(obj: Any) -> Any:
    """default function for packing objects in JSON."""
    if isinstance(obj, datetime):
        obj = _ensure_tzinfo(obj)
        return obj.isoformat().replace("+00:00", "Z")

    if isinstance(obj, bytes):
        return b2a_base64(obj, newline=False).decode("ascii")

    if isinstance(obj, Iterable):
        return list(obj)

    if isinstance(obj, numbers.Integral):
        return int(obj)

    if isinstance(obj, numbers.Real):
        return float(obj)

    raise TypeError("%r is not JSON serializable" % obj)


# Copy of the old ipykernel's json_clean
# This is temporary, it should be removed when we deprecate support for
# non-valid JSON messages
def json_clean(obj: Any) -> Any:
    # types that are 'atomic' and ok in json as-is.
    atomic_ok = (str, type(None))

    # containers that we need to convert into lists
    container_to_list = (tuple, set, types.GeneratorType)

    # Since bools are a subtype of Integrals, which are a subtype of Reals,
    # we have to check them in that order.

    if isinstance(obj, bool):
        return obj

    if isinstance(obj, numbers.Integral):
        # cast int to int, in case subclasses override __str__ (e.g. boost enum, #4598)
        return int(obj)

    if isinstance(obj, numbers.Real):
        # cast out-of-range floats to their reprs
        if math.isnan(obj) or math.isinf(obj):
            return repr(obj)
        return float(obj)

    if isinstance(obj, atomic_ok):
        return obj

    if isinstance(obj, bytes):
        # unanmbiguous binary data is base64-encoded
        # (this probably should have happened upstream)
        return b2a_base64(obj, newline=False).decode("ascii")

    if isinstance(obj, container_to_list) or (
        hasattr(obj, "__iter__") and hasattr(obj, next_attr_name)
    ):
        obj = list(obj)

    if isinstance(obj, list):
        return [json_clean(x) for x in obj]

    if isinstance(obj, dict):
        # First, validate that the dict won't lose data in conversion due to
        # key collisions after stringification.  This can happen with keys like
        # True and 'true' or 1 and '1', which collide in JSON.
        nkeys = len(obj)
        nkeys_collapsed = len(set(map(str, obj)))
        if nkeys != nkeys_collapsed:
            msg = (
                "dict cannot be safely converted to JSON: "
                "key collision would lead to dropped values"
            )
            raise ValueError(msg)
        # If all OK, proceed by making the new dict that will be json-safe
        out = {}
        for k, v in obj.items():
            out[str(k)] = json_clean(v)
        return out

    if isinstance(obj, datetime):
        return obj.strftime(ISO8601)

    # we don't understand it, it's probably an unserializable object
    raise ValueError("Can't clean for JSON: %r" % obj)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\validation.py ===
"""
Input validation for a `Buffer`.
(Validators will be called before accepting input.)
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Callable

from prompt_toolkit.eventloop import run_in_executor_with_context

from .document import Document
from .filters import FilterOrBool, to_filter

__all__ = [
    "ConditionalValidator",
    "ValidationError",
    "Validator",
    "ThreadedValidator",
    "DummyValidator",
    "DynamicValidator",
]


class ValidationError(Exception):
    """
    Error raised by :meth:`.Validator.validate`.

    :param cursor_position: The cursor position where the error occurred.
    :param message: Text.
    """

    def __init__(self, cursor_position: int = 0, message: str = "") -> None:
        super().__init__(message)
        self.cursor_position = cursor_position
        self.message = message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(cursor_position={self.cursor_position!r}, message={self.message!r})"


class Validator(metaclass=ABCMeta):
    """
    Abstract base class for an input validator.

    A validator is typically created in one of the following two ways:

    - Either by overriding this class and implementing the `validate` method.
    - Or by passing a callable to `Validator.from_callable`.

    If the validation takes some time and needs to happen in a background
    thread, this can be wrapped in a :class:`.ThreadedValidator`.
    """

    @abstractmethod
    def validate(self, document: Document) -> None:
        """
        Validate the input.
        If invalid, this should raise a :class:`.ValidationError`.

        :param document: :class:`~prompt_toolkit.document.Document` instance.
        """
        pass

    async def validate_async(self, document: Document) -> None:
        """
        Return a `Future` which is set when the validation is ready.
        This function can be overloaded in order to provide an asynchronous
        implementation.
        """
        try:
            self.validate(document)
        except ValidationError:
            raise

    @classmethod
    def from_callable(
        cls,
        validate_func: Callable[[str], bool],
        error_message: str = "Invalid input",
        move_cursor_to_end: bool = False,
    ) -> Validator:
        """
        Create a validator from a simple validate callable. E.g.:

        .. code:: python

            def is_valid(text):
                return text in ['hello', 'world']
            Validator.from_callable(is_valid, error_message='Invalid input')

        :param validate_func: Callable that takes the input string, and returns
            `True` if the input is valid input.
        :param error_message: Message to be displayed if the input is invalid.
        :param move_cursor_to_end: Move the cursor to the end of the input, if
            the input is invalid.
        """
        return _ValidatorFromCallable(validate_func, error_message, move_cursor_to_end)


class _ValidatorFromCallable(Validator):
    """
    Validate input from a simple callable.
    """

    def __init__(
        self, func: Callable[[str], bool], error_message: str, move_cursor_to_end: bool
    ) -> None:
        self.func = func
        self.error_message = error_message
        self.move_cursor_to_end = move_cursor_to_end

    def __repr__(self) -> str:
        return f"Validator.from_callable({self.func!r})"

    def validate(self, document: Document) -> None:
        if not self.func(document.text):
            if self.move_cursor_to_end:
                index = len(document.text)
            else:
                index = 0

            raise ValidationError(cursor_position=index, message=self.error_message)


class ThreadedValidator(Validator):
    """
    Wrapper that runs input validation in a thread.
    (Use this to prevent the user interface from becoming unresponsive if the
    input validation takes too much time.)
    """

    def __init__(self, validator: Validator) -> None:
        self.validator = validator

    def validate(self, document: Document) -> None:
        self.validator.validate(document)

    async def validate_async(self, document: Document) -> None:
        """
        Run the `validate` function in a thread.
        """

        def run_validation_thread() -> None:
            return self.validate(document)

        await run_in_executor_with_context(run_validation_thread)


class DummyValidator(Validator):
    """
    Validator class that accepts any input.
    """

    def validate(self, document: Document) -> None:
        pass  # Don't raise any exception.


class ConditionalValidator(Validator):
    """
    Validator that can be switched on/off according to
    a filter. (This wraps around another validator.)
    """

    def __init__(self, validator: Validator, filter: FilterOrBool) -> None:
        self.validator = validator
        self.filter = to_filter(filter)

    def validate(self, document: Document) -> None:
        # Call the validator only if the filter is active.
        if self.filter():
            self.validator.validate(document)


class DynamicValidator(Validator):
    """
    Validator class that can dynamically returns any Validator.

    :param get_validator: Callable that returns a :class:`.Validator` instance.
    """

    def __init__(self, get_validator: Callable[[], Validator | None]) -> None:
        self.get_validator = get_validator

    def validate(self, document: Document) -> None:
        validator = self.get_validator() or DummyValidator()
        validator.validate(document)

    async def validate_async(self, document: Document) -> None:
        validator = self.get_validator() or DummyValidator()
        await validator.validate_async(document)

# === NexusCore/openenv\Lib\site-packages\typer\utils.py ===
import inspect
import sys
from copy import copy
from typing import Any, Callable, Dict, List, Tuple, Type, cast

from typing_extensions import Annotated, get_type_hints

from ._typing import get_args, get_origin
from .models import ArgumentInfo, OptionInfo, ParameterInfo, ParamMeta


def _param_type_to_user_string(param_type: Type[ParameterInfo]) -> str:
    # Render a `ParameterInfo` subclass for use in error messages.
    # User code doesn't call `*Info` directly, so errors should present the classes how
    # they were (probably) defined in the user code.
    if param_type is OptionInfo:
        return "`Option`"
    elif param_type is ArgumentInfo:
        return "`Argument`"
    # This line shouldn't be reachable during normal use.
    return f"`{param_type.__name__}`"  # pragma: no cover


class AnnotatedParamWithDefaultValueError(Exception):
    argument_name: str
    param_type: Type[ParameterInfo]

    def __init__(self, argument_name: str, param_type: Type[ParameterInfo]):
        self.argument_name = argument_name
        self.param_type = param_type

    def __str__(self) -> str:
        param_type_str = _param_type_to_user_string(self.param_type)
        return (
            f"{param_type_str} default value cannot be set in `Annotated`"
            f" for {self.argument_name!r}. Set the default value with `=` instead."
        )


class MixedAnnotatedAndDefaultStyleError(Exception):
    argument_name: str
    annotated_param_type: Type[ParameterInfo]
    default_param_type: Type[ParameterInfo]

    def __init__(
        self,
        argument_name: str,
        annotated_param_type: Type[ParameterInfo],
        default_param_type: Type[ParameterInfo],
    ):
        self.argument_name = argument_name
        self.annotated_param_type = annotated_param_type
        self.default_param_type = default_param_type

    def __str__(self) -> str:
        annotated_param_type_str = _param_type_to_user_string(self.annotated_param_type)
        default_param_type_str = _param_type_to_user_string(self.default_param_type)
        msg = f"Cannot specify {annotated_param_type_str} in `Annotated` and"
        if self.annotated_param_type is self.default_param_type:
            msg += " default value"
        else:
            msg += f" {default_param_type_str} as a default value"
        msg += f" together for {self.argument_name!r}"
        return msg


class MultipleTyperAnnotationsError(Exception):
    argument_name: str

    def __init__(self, argument_name: str):
        self.argument_name = argument_name

    def __str__(self) -> str:
        return (
            "Cannot specify multiple `Annotated` Typer arguments"
            f" for {self.argument_name!r}"
        )


class DefaultFactoryAndDefaultValueError(Exception):
    argument_name: str
    param_type: Type[ParameterInfo]

    def __init__(self, argument_name: str, param_type: Type[ParameterInfo]):
        self.argument_name = argument_name
        self.param_type = param_type

    def __str__(self) -> str:
        param_type_str = _param_type_to_user_string(self.param_type)
        return (
            "Cannot specify `default_factory` and a default value together"
            f" for {param_type_str}"
        )


def _split_annotation_from_typer_annotations(
    base_annotation: Type[Any],
) -> Tuple[Type[Any], List[ParameterInfo]]:
    if get_origin(base_annotation) is not Annotated:  # type: ignore
        return base_annotation, []
    base_annotation, *maybe_typer_annotations = get_args(base_annotation)
    return base_annotation, [
        annotation
        for annotation in maybe_typer_annotations
        if isinstance(annotation, ParameterInfo)
    ]


def get_params_from_function(func: Callable[..., Any]) -> Dict[str, ParamMeta]:
    if sys.version_info >= (3, 10):
        signature = inspect.signature(func, eval_str=True)
    else:
        signature = inspect.signature(func)

    type_hints = get_type_hints(func)
    params = {}
    for param in signature.parameters.values():
        annotation, typer_annotations = _split_annotation_from_typer_annotations(
            param.annotation,
        )
        if len(typer_annotations) > 1:
            raise MultipleTyperAnnotationsError(param.name)

        default = param.default
        if typer_annotations:
            # It's something like `my_param: Annotated[str, Argument()]`
            [parameter_info] = typer_annotations

            # Forbid `my_param: Annotated[str, Argument()] = Argument("...")`
            if isinstance(param.default, ParameterInfo):
                raise MixedAnnotatedAndDefaultStyleError(
                    argument_name=param.name,
                    annotated_param_type=type(parameter_info),
                    default_param_type=type(param.default),
                )

            parameter_info = copy(parameter_info)

            # When used as a default, `Option` takes a default value and option names
            # as positional arguments:
            #   `Option(some_value, "--some-argument", "-s")`
            # When used in `Annotated` (ie, what this is handling), `Option` just takes
            # option names as positional arguments:
            #   `Option("--some-argument", "-s")`
            # In this case, the `default` attribute of `parameter_info` is actually
            # meant to be the first item of `param_decls`.
            if (
                isinstance(parameter_info, OptionInfo)
                and parameter_info.default is not ...
            ):
                parameter_info.param_decls = (
                    cast(str, parameter_info.default),
                    *(parameter_info.param_decls or ()),
                )
                parameter_info.default = ...

            # Forbid `my_param: Annotated[str, Argument('some-default')]`
            if parameter_info.default is not ...:
                raise AnnotatedParamWithDefaultValueError(
                    param_type=type(parameter_info),
                    argument_name=param.name,
                )
            if param.default is not param.empty:
                # Put the parameter's default (set by `=`) into `parameter_info`, where
                # typer can find it.
                parameter_info.default = param.default

            default = parameter_info
        elif param.name in type_hints:
            # Resolve forward references.
            annotation = type_hints[param.name]

        if isinstance(default, ParameterInfo):
            parameter_info = copy(default)
            # Click supports `default` as either
            # - an actual value; or
            # - a factory function (returning a default value.)
            # The two are not interchangeable for static typing, so typer allows
            # specifying `default_factory`. Move the `default_factory` into `default`
            # so click can find it.
            if parameter_info.default is ... and parameter_info.default_factory:
                parameter_info.default = parameter_info.default_factory
            elif parameter_info.default_factory:
                raise DefaultFactoryAndDefaultValueError(
                    argument_name=param.name, param_type=type(parameter_info)
                )
            default = parameter_info

        params[param.name] = ParamMeta(
            name=param.name, default=default, annotation=annotation
        )
    return params

# === NexusCore/openenv\Lib\site-packages\typer\_completion_classes.py ===
import os
import re
import sys
from typing import Any, Dict, List, Tuple

import click
import click.parser
import click.shell_completion

from ._completion_shared import (
    COMPLETION_SCRIPT_BASH,
    COMPLETION_SCRIPT_FISH,
    COMPLETION_SCRIPT_POWER_SHELL,
    COMPLETION_SCRIPT_ZSH,
    Shells,
)

try:
    import shellingham
except ImportError:  # pragma: no cover
    shellingham = None


class BashComplete(click.shell_completion.BashComplete):
    name = Shells.bash.value
    source_template = COMPLETION_SCRIPT_BASH

    def source_vars(self) -> Dict[str, Any]:
        return {
            "complete_func": self.func_name,
            "autocomplete_var": self.complete_var,
            "prog_name": self.prog_name,
        }

    def get_completion_args(self) -> Tuple[List[str], str]:
        cwords = click.parser.split_arg_string(os.environ["COMP_WORDS"])
        cword = int(os.environ["COMP_CWORD"])
        args = cwords[1:cword]

        try:
            incomplete = cwords[cword]
        except IndexError:
            incomplete = ""

        return args, incomplete

    def format_completion(self, item: click.shell_completion.CompletionItem) -> str:
        # TODO: Explore replicating the new behavior from Click, with item types and
        # triggering completion for files and directories
        # return f"{item.type},{item.value}"
        return f"{item.value}"

    def complete(self) -> str:
        args, incomplete = self.get_completion_args()
        completions = self.get_completions(args, incomplete)
        out = [self.format_completion(item) for item in completions]
        return "\n".join(out)


class ZshComplete(click.shell_completion.ZshComplete):
    name = Shells.zsh.value
    source_template = COMPLETION_SCRIPT_ZSH

    def source_vars(self) -> Dict[str, Any]:
        return {
            "complete_func": self.func_name,
            "autocomplete_var": self.complete_var,
            "prog_name": self.prog_name,
        }

    def get_completion_args(self) -> Tuple[List[str], str]:
        completion_args = os.getenv("_TYPER_COMPLETE_ARGS", "")
        cwords = click.parser.split_arg_string(completion_args)
        args = cwords[1:]
        if args and not completion_args.endswith(" "):
            incomplete = args[-1]
            args = args[:-1]
        else:
            incomplete = ""
        return args, incomplete

    def format_completion(self, item: click.shell_completion.CompletionItem) -> str:
        def escape(s: str) -> str:
            return (
                s.replace('"', '""')
                .replace("'", "''")
                .replace("$", "\\$")
                .replace("`", "\\`")
            )

        # TODO: Explore replicating the new behavior from Click, pay attention to
        # the difference with and without escape
        # return f"{item.type}\n{item.value}\n{item.help if item.help else '_'}"
        if item.help:
            return f'"{escape(item.value)}":"{escape(item.help)}"'
        else:
            return f'"{escape(item.value)}"'

    def complete(self) -> str:
        args, incomplete = self.get_completion_args()
        completions = self.get_completions(args, incomplete)
        res = [self.format_completion(item) for item in completions]
        if res:
            args_str = "\n".join(res)
            return f"_arguments '*: :(({args_str}))'"
        else:
            return "_files"


class FishComplete(click.shell_completion.FishComplete):
    name = Shells.fish.value
    source_template = COMPLETION_SCRIPT_FISH

    def source_vars(self) -> Dict[str, Any]:
        return {
            "complete_func": self.func_name,
            "autocomplete_var": self.complete_var,
            "prog_name": self.prog_name,
        }

    def get_completion_args(self) -> Tuple[List[str], str]:
        completion_args = os.getenv("_TYPER_COMPLETE_ARGS", "")
        cwords = click.parser.split_arg_string(completion_args)
        args = cwords[1:]
        if args and not completion_args.endswith(" "):
            incomplete = args[-1]
            args = args[:-1]
        else:
            incomplete = ""
        return args, incomplete

    def format_completion(self, item: click.shell_completion.CompletionItem) -> str:
        # TODO: Explore replicating the new behavior from Click, pay attention to
        # the difference with and without formatted help
        # if item.help:
        #     return f"{item.type},{item.value}\t{item.help}"

        # return f"{item.type},{item.value}
        if item.help:
            formatted_help = re.sub(r"\s", " ", item.help)
            return f"{item.value}\t{formatted_help}"
        else:
            return f"{item.value}"

    def complete(self) -> str:
        complete_action = os.getenv("_TYPER_COMPLETE_FISH_ACTION", "")
        args, incomplete = self.get_completion_args()
        completions = self.get_completions(args, incomplete)
        show_args = [self.format_completion(item) for item in completions]
        if complete_action == "get-args":
            if show_args:
                return "\n".join(show_args)
        elif complete_action == "is-args":
            if show_args:
                # Activate complete args (no files)
                sys.exit(0)
            else:
                # Deactivate complete args (allow files)
                sys.exit(1)
        return ""  # pragma: no cover


class PowerShellComplete(click.shell_completion.ShellComplete):
    name = Shells.powershell.value
    source_template = COMPLETION_SCRIPT_POWER_SHELL

    def source_vars(self) -> Dict[str, Any]:
        return {
            "complete_func": self.func_name,
            "autocomplete_var": self.complete_var,
            "prog_name": self.prog_name,
        }

    def get_completion_args(self) -> Tuple[List[str], str]:
        completion_args = os.getenv("_TYPER_COMPLETE_ARGS", "")
        incomplete = os.getenv("_TYPER_COMPLETE_WORD_TO_COMPLETE", "")
        cwords = click.parser.split_arg_string(completion_args)
        args = cwords[1:-1] if incomplete else cwords[1:]
        return args, incomplete

    def format_completion(self, item: click.shell_completion.CompletionItem) -> str:
        return f"{item.value}:::{item.help or ' '}"


def completion_init() -> None:
    click.shell_completion.add_completion_class(BashComplete, Shells.bash.value)
    click.shell_completion.add_completion_class(ZshComplete, Shells.zsh.value)
    click.shell_completion.add_completion_class(FishComplete, Shells.fish.value)
    click.shell_completion.add_completion_class(
        PowerShellComplete, Shells.powershell.value
    )
    click.shell_completion.add_completion_class(PowerShellComplete, Shells.pwsh.value)

# === NexusCore/openenv\Lib\site-packages\fontTools\pens\pointInsidePen.py ===
"""fontTools.pens.pointInsidePen -- Pen implementing "point inside" testing
for shapes.
"""

from fontTools.pens.basePen import BasePen
from fontTools.misc.bezierTools import solveQuadratic, solveCubic


__all__ = ["PointInsidePen"]


class PointInsidePen(BasePen):
    """This pen implements "point inside" testing: to test whether
    a given point lies inside the shape (black) or outside (white).
    Instances of this class can be recycled, as long as the
    setTestPoint() method is used to set the new point to test.

    :Example:
        .. code-block::

            pen = PointInsidePen(glyphSet, (100, 200))
            outline.draw(pen)
            isInside = pen.getResult()

    Both the even-odd algorithm and the non-zero-winding-rule
    algorithm are implemented. The latter is the default, specify
    True for the evenOdd argument of __init__ or setTestPoint
    to use the even-odd algorithm.
    """

    # This class implements the classical "shoot a ray from the test point
    # to infinity and count how many times it intersects the outline" (as well
    # as the non-zero variant, where the counter is incremented if the outline
    # intersects the ray in one direction and decremented if it intersects in
    # the other direction).
    # I found an amazingly clear explanation of the subtleties involved in
    # implementing this correctly for polygons here:
    #   http://graphics.cs.ucdavis.edu/~okreylos/TAship/Spring2000/PointInPolygon.html
    # I extended the principles outlined on that page to curves.

    def __init__(self, glyphSet, testPoint, evenOdd=False):
        BasePen.__init__(self, glyphSet)
        self.setTestPoint(testPoint, evenOdd)

    def setTestPoint(self, testPoint, evenOdd=False):
        """Set the point to test. Call this _before_ the outline gets drawn."""
        self.testPoint = testPoint
        self.evenOdd = evenOdd
        self.firstPoint = None
        self.intersectionCount = 0

    def getWinding(self):
        if self.firstPoint is not None:
            # always make sure the sub paths are closed; the algorithm only works
            # for closed paths.
            self.closePath()
        return self.intersectionCount

    def getResult(self):
        """After the shape has been drawn, getResult() returns True if the test
        point lies within the (black) shape, and False if it doesn't.
        """
        winding = self.getWinding()
        if self.evenOdd:
            result = winding % 2
        else:  # non-zero
            result = self.intersectionCount != 0
        return not not result

    def _addIntersection(self, goingUp):
        if self.evenOdd or goingUp:
            self.intersectionCount += 1
        else:
            self.intersectionCount -= 1

    def _moveTo(self, point):
        if self.firstPoint is not None:
            # always make sure the sub paths are closed; the algorithm only works
            # for closed paths.
            self.closePath()
        self.firstPoint = point

    def _lineTo(self, point):
        x, y = self.testPoint
        x1, y1 = self._getCurrentPoint()
        x2, y2 = point

        if x1 < x and x2 < x:
            return
        if y1 < y and y2 < y:
            return
        if y1 >= y and y2 >= y:
            return

        dx = x2 - x1
        dy = y2 - y1
        t = (y - y1) / dy
        ix = dx * t + x1
        if ix < x:
            return
        self._addIntersection(y2 > y1)

    def _curveToOne(self, bcp1, bcp2, point):
        x, y = self.testPoint
        x1, y1 = self._getCurrentPoint()
        x2, y2 = bcp1
        x3, y3 = bcp2
        x4, y4 = point

        if x1 < x and x2 < x and x3 < x and x4 < x:
            return
        if y1 < y and y2 < y and y3 < y and y4 < y:
            return
        if y1 >= y and y2 >= y and y3 >= y and y4 >= y:
            return

        dy = y1
        cy = (y2 - dy) * 3.0
        by = (y3 - y2) * 3.0 - cy
        ay = y4 - dy - cy - by
        solutions = sorted(solveCubic(ay, by, cy, dy - y))
        solutions = [t for t in solutions if -0.0 <= t <= 1.0]
        if not solutions:
            return

        dx = x1
        cx = (x2 - dx) * 3.0
        bx = (x3 - x2) * 3.0 - cx
        ax = x4 - dx - cx - bx

        above = y1 >= y
        lastT = None
        for t in solutions:
            if t == lastT:
                continue
            lastT = t
            t2 = t * t
            t3 = t2 * t

            direction = 3 * ay * t2 + 2 * by * t + cy
            incomingGoingUp = outgoingGoingUp = direction > 0.0
            if direction == 0.0:
                direction = 6 * ay * t + 2 * by
                outgoingGoingUp = direction > 0.0
                incomingGoingUp = not outgoingGoingUp
                if direction == 0.0:
                    direction = ay
                    incomingGoingUp = outgoingGoingUp = direction > 0.0

            xt = ax * t3 + bx * t2 + cx * t + dx
            if xt < x:
                continue

            if t in (0.0, -0.0):
                if not outgoingGoingUp:
                    self._addIntersection(outgoingGoingUp)
            elif t == 1.0:
                if incomingGoingUp:
                    self._addIntersection(incomingGoingUp)
            else:
                if incomingGoingUp == outgoingGoingUp:
                    self._addIntersection(outgoingGoingUp)
                # else:
                #   we're not really intersecting, merely touching

    def _qCurveToOne_unfinished(self, bcp, point):
        # XXX need to finish this, for now doing it through a cubic
        # (BasePen implements _qCurveTo in terms of a cubic) will
        # have to do.
        x, y = self.testPoint
        x1, y1 = self._getCurrentPoint()
        x2, y2 = bcp
        x3, y3 = point
        c = y1
        b = (y2 - c) * 2.0
        a = y3 - c - b
        solutions = sorted(solveQuadratic(a, b, c - y))
        solutions = [
            t for t in solutions if ZERO_MINUS_EPSILON <= t <= ONE_PLUS_EPSILON
        ]
        if not solutions:
            return
        # XXX

    def _closePath(self):
        if self._getCurrentPoint() != self.firstPoint:
            self.lineTo(self.firstPoint)
        self.firstPoint = None

    def _endPath(self):
        """Insideness is not defined for open contours."""
        raise NotImplementedError

# === NexusCore/openenv\Lib\site-packages\gitdb\test\lib.py ===
# Copyright (C) 2010, 2011 Sebastian Thiel (byronimo@gmail.com) and contributors
#
# This module is part of GitDB and is released under
# the New BSD License: https://opensource.org/license/bsd-3-clause/
"""Utilities used in ODB testing"""
from gitdb import OStream

import sys
import random
from array import array

from io import BytesIO

import glob
import unittest
import tempfile
import shutil
import os
import gc
import logging
from functools import wraps


#{ Bases

class TestBase(unittest.TestCase):
    """Base class for all tests

    TestCase providing access to readonly repositories using the following member variables.

    * gitrepopath

     * read-only base path of the git source repository, i.e. .../git/.git
    """

    #{ Invvariants
    k_env_git_repo = "GITDB_TEST_GIT_REPO_BASE"
    #} END invariants

    @classmethod
    def setUpClass(cls):
        try:
            super().setUpClass()
        except AttributeError:
            pass

        cls.gitrepopath = os.environ.get(cls.k_env_git_repo)
        if not cls.gitrepopath:
            logging.info(
                "You can set the %s environment variable to a .git repository of your choice - defaulting to the gitdb repository", cls.k_env_git_repo)
            ospd = os.path.dirname
            cls.gitrepopath = os.path.join(ospd(ospd(ospd(__file__))), '.git')
        # end assure gitrepo is set
        assert cls.gitrepopath.endswith('.git')


#} END bases

#{ Decorators

def with_rw_directory(func):
    """Create a temporary directory which can be written to, remove it if the
    test succeeds, but leave it otherwise to aid additional debugging"""

    def wrapper(self):
        path = tempfile.mktemp(prefix=func.__name__)
        os.mkdir(path)
        keep = False
        try:
            try:
                return func(self, path)
            except Exception:
                sys.stderr.write(f"Test {type(self).__name__}.{func.__name__} failed, output is at {path!r}\n")
                keep = True
                raise
        finally:
            # Need to collect here to be sure all handles have been closed. It appears
            # a windows-only issue. In fact things should be deleted, as well as
            # memory maps closed, once objects go out of scope. For some reason
            # though this is not the case here unless we collect explicitly.
            if not keep:
                gc.collect()
                shutil.rmtree(path)
        # END handle exception
    # END wrapper

    wrapper.__name__ = func.__name__
    return wrapper


def with_packs_rw(func):
    """Function that provides a path into which the packs for testing should be
    copied. Will pass on the path to the actual function afterwards"""

    def wrapper(self, path):
        src_pack_glob = fixture_path('packs/*')
        copy_files_globbed(src_pack_glob, path, hard_link_ok=True)
        return func(self, path)
    # END wrapper

    wrapper.__name__ = func.__name__
    return wrapper

#} END decorators

#{ Routines


def fixture_path(relapath=''):
    """:return: absolute path into the fixture directory
    :param relapath: relative path into the fixtures directory, or ''
        to obtain the fixture directory itself"""
    return os.path.join(os.path.dirname(__file__), 'fixtures', relapath)


def copy_files_globbed(source_glob, target_dir, hard_link_ok=False):
    """Copy all files found according to the given source glob into the target directory
    :param hard_link_ok: if True, hard links will be created if possible. Otherwise
        the files will be copied"""
    for src_file in glob.glob(source_glob):
        if hard_link_ok and hasattr(os, 'link'):
            target = os.path.join(target_dir, os.path.basename(src_file))
            try:
                os.link(src_file, target)
            except OSError:
                shutil.copy(src_file, target_dir)
            # END handle cross device links ( and resulting failure )
        else:
            shutil.copy(src_file, target_dir)
        # END try hard link
    # END for each file to copy


def make_bytes(size_in_bytes, randomize=False):
    """:return: string with given size in bytes
    :param randomize: try to produce a very random stream"""
    actual_size = size_in_bytes // 4
    producer = range(actual_size)
    if randomize:
        producer = list(producer)
        random.shuffle(producer)
    # END randomize
    a = array('i', producer)
    return a.tobytes()


def make_object(type, data):
    """:return: bytes resembling an uncompressed object"""
    odata = "blob %i\0" % len(data)
    return odata.encode("ascii") + data


def make_memory_file(size_in_bytes, randomize=False):
    """:return: tuple(size_of_stream, stream)
    :param randomize: try to produce a very random stream"""
    d = make_bytes(size_in_bytes, randomize)
    return len(d), BytesIO(d)

#} END routines

#{ Stream Utilities


class DummyStream:

    def __init__(self):
        self.was_read = False
        self.bytes = 0
        self.closed = False

    def read(self, size):
        self.was_read = True
        self.bytes = size

    def close(self):
        self.closed = True

    def _assert(self):
        assert self.was_read


class DeriveTest(OStream):

    def __init__(self, sha, type, size, stream, *args, **kwargs):
        self.myarg = kwargs.pop('myarg')
        self.args = args

    def _assert(self):
        assert self.args
        assert self.myarg

#} END stream utilitiess

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\types\safety.py ===
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
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1",
    manifest={
        "HarmCategory",
        "SafetyRating",
        "SafetySetting",
    },
)


class HarmCategory(proto.Enum):
    r"""The category of a rating.

    These categories cover various kinds of harms that developers
    may wish to adjust.

    Values:
        HARM_CATEGORY_UNSPECIFIED (0):
            Category is unspecified.
        HARM_CATEGORY_DEROGATORY (1):
            Negative or harmful comments targeting
            identity and/or protected attribute.
        HARM_CATEGORY_TOXICITY (2):
            Content that is rude, disrespectful, or
            profane.
        HARM_CATEGORY_VIOLENCE (3):
            Describes scenarios depicting violence
            against an individual or group, or general
            descriptions of gore.
        HARM_CATEGORY_SEXUAL (4):
            Contains references to sexual acts or other
            lewd content.
        HARM_CATEGORY_MEDICAL (5):
            Promotes unchecked medical advice.
        HARM_CATEGORY_DANGEROUS (6):
            Dangerous content that promotes, facilitates,
            or encourages harmful acts.
        HARM_CATEGORY_HARASSMENT (7):
            Harasment content.
        HARM_CATEGORY_HATE_SPEECH (8):
            Hate speech and content.
        HARM_CATEGORY_SEXUALLY_EXPLICIT (9):
            Sexually explicit content.
        HARM_CATEGORY_DANGEROUS_CONTENT (10):
            Dangerous content.
    """
    HARM_CATEGORY_UNSPECIFIED = 0
    HARM_CATEGORY_DEROGATORY = 1
    HARM_CATEGORY_TOXICITY = 2
    HARM_CATEGORY_VIOLENCE = 3
    HARM_CATEGORY_SEXUAL = 4
    HARM_CATEGORY_MEDICAL = 5
    HARM_CATEGORY_DANGEROUS = 6
    HARM_CATEGORY_HARASSMENT = 7
    HARM_CATEGORY_HATE_SPEECH = 8
    HARM_CATEGORY_SEXUALLY_EXPLICIT = 9
    HARM_CATEGORY_DANGEROUS_CONTENT = 10


class SafetyRating(proto.Message):
    r"""Safety rating for a piece of content.

    The safety rating contains the category of harm and the harm
    probability level in that category for a piece of content.
    Content is classified for safety across a number of harm
    categories and the probability of the harm classification is
    included here.

    Attributes:
        category (google.ai.generativelanguage_v1.types.HarmCategory):
            Required. The category for this rating.
        probability (google.ai.generativelanguage_v1.types.SafetyRating.HarmProbability):
            Required. The probability of harm for this
            content.
        blocked (bool):
            Was this content blocked because of this
            rating?
    """

    class HarmProbability(proto.Enum):
        r"""The probability that a piece of content is harmful.

        The classification system gives the probability of the content
        being unsafe. This does not indicate the severity of harm for a
        piece of content.

        Values:
            HARM_PROBABILITY_UNSPECIFIED (0):
                Probability is unspecified.
            NEGLIGIBLE (1):
                Content has a negligible chance of being
                unsafe.
            LOW (2):
                Content has a low chance of being unsafe.
            MEDIUM (3):
                Content has a medium chance of being unsafe.
            HIGH (4):
                Content has a high chance of being unsafe.
        """
        HARM_PROBABILITY_UNSPECIFIED = 0
        NEGLIGIBLE = 1
        LOW = 2
        MEDIUM = 3
        HIGH = 4

    category: "HarmCategory" = proto.Field(
        proto.ENUM,
        number=3,
        enum="HarmCategory",
    )
    probability: HarmProbability = proto.Field(
        proto.ENUM,
        number=4,
        enum=HarmProbability,
    )
    blocked: bool = proto.Field(
        proto.BOOL,
        number=5,
    )


class SafetySetting(proto.Message):
    r"""Safety setting, affecting the safety-blocking behavior.

    Passing a safety setting for a category changes the allowed
    probability that content is blocked.

    Attributes:
        category (google.ai.generativelanguage_v1.types.HarmCategory):
            Required. The category for this setting.
        threshold (google.ai.generativelanguage_v1.types.SafetySetting.HarmBlockThreshold):
            Required. Controls the probability threshold
            at which harm is blocked.
    """

    class HarmBlockThreshold(proto.Enum):
        r"""Block at and beyond a specified harm probability.

        Values:
            HARM_BLOCK_THRESHOLD_UNSPECIFIED (0):
                Threshold is unspecified.
            BLOCK_LOW_AND_ABOVE (1):
                Content with NEGLIGIBLE will be allowed.
            BLOCK_MEDIUM_AND_ABOVE (2):
                Content with NEGLIGIBLE and LOW will be
                allowed.
            BLOCK_ONLY_HIGH (3):
                Content with NEGLIGIBLE, LOW, and MEDIUM will
                be allowed.
            BLOCK_NONE (4):
                All content will be allowed.
        """
        HARM_BLOCK_THRESHOLD_UNSPECIFIED = 0
        BLOCK_LOW_AND_ABOVE = 1
        BLOCK_MEDIUM_AND_ABOVE = 2
        BLOCK_ONLY_HIGH = 3
        BLOCK_NONE = 4

    category: "HarmCategory" = proto.Field(
        proto.ENUM,
        number=3,
        enum="HarmCategory",
    )
    threshold: HarmBlockThreshold = proto.Field(
        proto.ENUM,
        number=4,
        enum=HarmBlockThreshold,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\ai\ai.py ===
from concurrent.futures import ThreadPoolExecutor

import tiktoken


def split_into_chunks(text, tokens, llm, overlap):
    try:
        encoding = tiktoken.encoding_for_model(llm.model)
        tokenized_text = encoding.encode(text)
        chunks = []
        for i in range(0, len(tokenized_text), tokens - overlap):
            chunk = encoding.decode(tokenized_text[i : i + tokens])
            chunks.append(chunk)
    except Exception:
        chunks = []
        for i in range(0, len(text), tokens * 4 - overlap):
            chunk = text[i : i + tokens * 4]
            chunks.append(chunk)
    return chunks


def chunk_responses(responses, tokens, llm):
    try:
        encoding = tiktoken.encoding_for_model(llm.model)
        chunked_responses = []
        current_chunk = ""
        current_tokens = 0

        for response in responses:
            tokenized_response = encoding.encode(response)
            new_tokens = current_tokens + len(tokenized_response)

            # If the new token count exceeds the limit, handle the current chunk
            if new_tokens > tokens:
                # If current chunk is empty or response alone exceeds limit, add response as standalone
                if current_tokens == 0 or len(tokenized_response) > tokens:
                    chunked_responses.append(response)
                else:
                    chunked_responses.append(current_chunk)
                    current_chunk = response
                    current_tokens = len(tokenized_response)
                continue

            # Add response to the current chunk
            current_chunk += "\n\n" + response if current_chunk else response
            current_tokens = new_tokens

        # Add remaining chunk if not empty
        if current_chunk:
            chunked_responses.append(current_chunk)
    except Exception:
        chunked_responses = []
        current_chunk = ""
        current_chars = 0

        for response in responses:
            new_chars = current_chars + len(response)

            # If the new char count exceeds the limit, handle the current chunk
            if new_chars > tokens * 4:
                # If current chunk is empty or response alone exceeds limit, add response as standalone
                if current_chars == 0 or len(response) > tokens * 4:
                    chunked_responses.append(response)
                else:
                    chunked_responses.append(current_chunk)
                    current_chunk = response
                    current_chars = len(response)
                continue

            # Add response to the current chunk
            current_chunk += "\n\n" + response if current_chunk else response
            current_chars = new_chars

        # Add remaining chunk if not empty
        if current_chunk:
            chunked_responses.append(current_chunk)
    return chunked_responses


def fast_llm(llm, system_message, user_message):
    old_messages = llm.interpreter.messages
    old_system_message = llm.interpreter.system_message
    try:
        llm.interpreter.system_message = system_message
        llm.interpreter.messages = []
        response = llm.interpreter.chat(user_message)
    finally:
        llm.interpreter.messages = old_messages
        llm.interpreter.system_message = old_system_message
        return response[-1].get("content")


def query_map_chunks(chunks, llm, query):
    """Query the chunks of text using query_chunk_map."""
    with ThreadPoolExecutor() as executor:
        responses = list(
            executor.map(lambda chunk: fast_llm(llm, query, chunk), chunks)
        )
    return responses


def query_reduce_chunks(responses, llm, chunk_size, query):
    """Reduce query responses in a while loop."""
    while len(responses) > 1:
        chunks = chunk_responses(responses, chunk_size, llm)

        # Use multithreading to summarize each chunk simultaneously
        with ThreadPoolExecutor() as executor:
            summaries = list(
                executor.map(lambda chunk: fast_llm(llm, query, chunk), chunks)
            )

    return summaries[0]


class Ai:
    def __init__(self, computer):
        self.computer = computer

    def chat(self, text, base64=None):
        messages = [
            {
                "role": "system",
                "type": "message",
                "content": "You are a helpful AI assistant.",
            },
            {"role": "user", "type": "message", "content": text},
        ]
        if base64:
            messages.append(
                {"role": "user", "type": "image", "format": "base64", "content": base64}
            )
        response = ""
        for chunk in self.computer.interpreter.llm.run(messages):
            if "content" in chunk:
                response += chunk.get("content")
        return response

        # Old way
        old_messages = self.computer.interpreter.llm.interpreter.messages
        old_system_message = self.computer.interpreter.llm.interpreter.system_message
        old_import_computer_api = self.computer.import_computer_api
        old_execution_instructions = (
            self.computer.interpreter.llm.execution_instructions
        )
        try:
            self.computer.interpreter.llm.interpreter.system_message = (
                "You are an AI assistant."
            )
            self.computer.interpreter.llm.interpreter.messages = []
            self.computer.import_computer_api = False
            self.computer.interpreter.llm.execution_instructions = ""

            response = self.computer.interpreter.llm.interpreter.chat(text)
        finally:
            self.computer.interpreter.llm.interpreter.messages = old_messages
            self.computer.interpreter.llm.interpreter.system_message = (
                old_system_message
            )
            self.computer.import_computer_api = old_import_computer_api
            self.computer.interpreter.llm.execution_instructions = (
                old_execution_instructions
            )

            return response[-1].get("content")

    def query(self, text, query, custom_reduce_query=None):
        if custom_reduce_query == None:
            custom_reduce_query = query

        chunk_size = 2000
        overlap = 50

        # Split the text into chunks
        chunks = split_into_chunks(
            text, chunk_size, self.computer.interpreter.llm, overlap
        )

        # (Map) Query each chunk
        responses = query_map_chunks(chunks, self.computer.interpreter.llm, query)

        # (Reduce) Compress the responses
        response = query_reduce_chunks(
            responses, self.computer.interpreter.llm, chunk_size, custom_reduce_query
        )

        return response

    def summarize(self, text):
        query = "You are a highly skilled AI trained in language comprehension and summarization. I would like you to read the following text and summarize it into a concise abstract paragraph. Aim to retain the most important points, providing a coherent and readable summary that could help a person understand the main points of the discussion without needing to read the entire text. Please avoid unnecessary details or tangential points."
        custom_reduce_query = "You are tasked with taking multiple summarized texts and merging them into one unified and concise summary. Maintain the core essence of the content and provide a clear and comprehensive summary that encapsulates all the main points from the individual summaries."
        return self.query(text, query, custom_reduce_query)

# === NexusCore/openenv\Lib\site-packages\IPython\core\compilerop.py ===
"""Compiler tools with improved interactive support.

Provides compilation machinery similar to codeop, but with caching support so
we can provide interactive tracebacks.

Authors
-------
* Robert Kern
* Fernando Perez
* Thomas Kluyver
"""

# Note: though it might be more natural to name this module 'compiler', that
# name is in the stdlib and name collisions with the stdlib tend to produce
# weird problems (often with third-party tools).

#-----------------------------------------------------------------------------
#  Copyright (C) 2010-2011 The IPython Development Team.
#
#  Distributed under the terms of the BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib imports
import __future__
from ast import PyCF_ONLY_AST
import codeop
import functools
import hashlib
import linecache
import operator
import time
from contextlib import contextmanager

#-----------------------------------------------------------------------------
# Constants
#-----------------------------------------------------------------------------

# Roughly equal to PyCF_MASK | PyCF_MASK_OBSOLETE as defined in pythonrun.h,
# this is used as a bitmask to extract future-related code flags.
PyCF_MASK = functools.reduce(operator.or_,
                             (getattr(__future__, fname).compiler_flag
                              for fname in __future__.all_feature_names))

#-----------------------------------------------------------------------------
# Local utilities
#-----------------------------------------------------------------------------

def code_name(code, number=0):
    """ Compute a (probably) unique name for code for caching.

    This now expects code to be unicode.
    """
    hash_digest = hashlib.sha1(code.encode("utf-8")).hexdigest()
    # Include the number and 12 characters of the hash in the name.  It's
    # pretty much impossible that in a single session we'll have collisions
    # even with truncated hashes, and the full one makes tracebacks too long
    return '<ipython-input-{0}-{1}>'.format(number, hash_digest[:12])

#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------

class CachingCompiler(codeop.Compile):
    """A compiler that caches code compiled from interactive statements.
    """

    def __init__(self):
        codeop.Compile.__init__(self)

        # Caching a dictionary { filename: execution_count } for nicely
        # rendered tracebacks. The filename corresponds to the filename
        # argument used for the builtins.compile function.
        self._filename_map = {}

    def ast_parse(self, source, filename='<unknown>', symbol='exec'):
        """Parse code to an AST with the current compiler flags active.

        Arguments are exactly the same as ast.parse (in the standard library),
        and are passed to the built-in compile function."""
        return compile(source, filename, symbol, self.flags | PyCF_ONLY_AST, 1)

    def reset_compiler_flags(self):
        """Reset compiler flags to default state."""
        # This value is copied from codeop.Compile.__init__, so if that ever
        # changes, it will need to be updated.
        self.flags = codeop.PyCF_DONT_IMPLY_DEDENT

    @property
    def compiler_flags(self):
        """Flags currently active in the compilation process.
        """
        return self.flags

    def get_code_name(self, raw_code, transformed_code, number):
        """Compute filename given the code, and the cell number.

        Parameters
        ----------
        raw_code : str
            The raw cell code.
        transformed_code : str
            The executable Python source code to cache and compile.
        number : int
            A number which forms part of the code's name. Used for the execution
            counter.

        Returns
        -------
        The computed filename.
        """
        return code_name(transformed_code, number)

    def format_code_name(self, name):
        """Return a user-friendly label and name for a code block.

        Parameters
        ----------
        name : str
            The name for the code block returned from get_code_name

        Returns
        -------
        A (label, name) pair that can be used in tracebacks, or None if the default formatting should be used.
        """
        if name in self._filename_map:
            return "Cell", "In[%s]" % self._filename_map[name]

    def cache(self, transformed_code, number=0, raw_code=None):
        """Make a name for a block of code, and cache the code.

        Parameters
        ----------
        transformed_code : str
            The executable Python source code to cache and compile.
        number : int
            A number which forms part of the code's name. Used for the execution
            counter.
        raw_code : str
            The raw code before transformation, if None, set to `transformed_code`.

        Returns
        -------
        The name of the cached code (as a string). Pass this as the filename
        argument to compilation, so that tracebacks are correctly hooked up.
        """
        if raw_code is None:
            raw_code = transformed_code

        name = self.get_code_name(raw_code, transformed_code, number)

        # Save the execution count
        self._filename_map[name] = number

        # Since Python 2.5, setting mtime to `None` means the lines will
        # never be removed by `linecache.checkcache`.  This means all the
        # monkeypatching has *never* been necessary, since this code was
        # only added in 2010, at which point IPython had already stopped
        # supporting Python 2.4.
        #
        # Note that `linecache.clearcache` and `linecache.updatecache` may
        # still remove our code from the cache, but those show explicit
        # intent, and we should not try to interfere.  Normally the former
        # is never called except when out of memory, and the latter is only
        # called for lines *not* in the cache.
        entry = (
            len(transformed_code),
            None,
            [line + "\n" for line in transformed_code.splitlines()],
            name,
        )
        linecache.cache[name] = entry
        return name

    @contextmanager
    def extra_flags(self, flags):
        ## bits that we'll set to 1
        turn_on_bits = ~self.flags & flags


        self.flags = self.flags | flags
        try:
            yield
        finally:
            # turn off only the bits we turned on so that something like
            # __future__ that set flags stays.
            self.flags &= ~turn_on_bits

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\hooks\model_max_budget_limiter.py ===
import json
from typing import List, Optional

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching.caching import DualCache
from litellm.integrations.custom_logger import Span
from litellm.proxy._types import UserAPIKeyAuth
from litellm.router_strategy.budget_limiter import RouterBudgetLimiting
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import (
    BudgetConfig,
    GenericBudgetConfigType,
    StandardLoggingPayload,
)

VIRTUAL_KEY_SPEND_CACHE_KEY_PREFIX = "virtual_key_spend"


class _PROXY_VirtualKeyModelMaxBudgetLimiter(RouterBudgetLimiting):
    """
    Handles budgets for model + virtual key

    Example: key=sk-1234567890, model=gpt-4o, max_budget=100, time_period=1d
    """

    def __init__(self, dual_cache: DualCache):
        self.dual_cache = dual_cache
        self.redis_increment_operation_queue = []

    async def is_key_within_model_budget(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        model: str,
    ) -> bool:
        """
        Check if the user_api_key_dict is within the model budget

        Raises:
            BudgetExceededError: If the user_api_key_dict has exceeded the model budget
        """
        _model_max_budget = user_api_key_dict.model_max_budget
        internal_model_max_budget: GenericBudgetConfigType = {}

        for _model, _budget_info in _model_max_budget.items():
            internal_model_max_budget[_model] = BudgetConfig(**_budget_info)

        verbose_proxy_logger.debug(
            "internal_model_max_budget %s",
            json.dumps(internal_model_max_budget, indent=4, default=str),
        )

        # check if current model is in internal_model_max_budget
        _current_model_budget_info = self._get_request_model_budget_config(
            model=model, internal_model_max_budget=internal_model_max_budget
        )
        if _current_model_budget_info is None:
            verbose_proxy_logger.debug(
                f"Model {model} not found in internal_model_max_budget"
            )
            return True

        # check if current model is within budget
        if (
            _current_model_budget_info.max_budget
            and _current_model_budget_info.max_budget > 0
        ):
            _current_spend = await self._get_virtual_key_spend_for_model(
                user_api_key_hash=user_api_key_dict.token,
                model=model,
                key_budget_config=_current_model_budget_info,
            )
            if (
                _current_spend is not None
                and _current_model_budget_info.max_budget is not None
                and _current_spend > _current_model_budget_info.max_budget
            ):
                raise litellm.BudgetExceededError(
                    message=f"LiteLLM Virtual Key: {user_api_key_dict.token}, key_alias: {user_api_key_dict.key_alias}, exceeded budget for model={model}",
                    current_cost=_current_spend,
                    max_budget=_current_model_budget_info.max_budget,
                )

        return True

    async def _get_virtual_key_spend_for_model(
        self,
        user_api_key_hash: Optional[str],
        model: str,
        key_budget_config: BudgetConfig,
    ) -> Optional[float]:
        """
        Get the current spend for a virtual key for a model

        Lookup model in this order:
            1. model: directly look up `model`
            2. If 1, does not exist, check if passed as {custom_llm_provider}/model
        """

        # 1. model: directly look up `model`
        virtual_key_model_spend_cache_key = f"{VIRTUAL_KEY_SPEND_CACHE_KEY_PREFIX}:{user_api_key_hash}:{model}:{key_budget_config.budget_duration}"
        _current_spend = await self.dual_cache.async_get_cache(
            key=virtual_key_model_spend_cache_key,
        )

        if _current_spend is None:
            # 2. If 1, does not exist, check if passed as {custom_llm_provider}/model
            # if "/" in model, remove first part before "/" - eg. openai/o1-preview -> o1-preview
            virtual_key_model_spend_cache_key = f"{VIRTUAL_KEY_SPEND_CACHE_KEY_PREFIX}:{user_api_key_hash}:{self._get_model_without_custom_llm_provider(model)}:{key_budget_config.budget_duration}"
            _current_spend = await self.dual_cache.async_get_cache(
                key=virtual_key_model_spend_cache_key,
            )
        return _current_spend

    def _get_request_model_budget_config(
        self, model: str, internal_model_max_budget: GenericBudgetConfigType
    ) -> Optional[BudgetConfig]:
        """
        Get the budget config for the request model

        1. Check if `model` is in `internal_model_max_budget`
        2. If not, check if `model` without custom llm provider is in `internal_model_max_budget`
        """
        return internal_model_max_budget.get(
            model, None
        ) or internal_model_max_budget.get(
            self._get_model_without_custom_llm_provider(model), None
        )

    def _get_model_without_custom_llm_provider(self, model: str) -> str:
        if "/" in model:
            return model.split("/")[-1]
        return model

    async def async_filter_deployments(
        self,
        model: str,
        healthy_deployments: List,
        messages: Optional[List[AllMessageValues]],
        request_kwargs: Optional[dict] = None,
        parent_otel_span: Optional[Span] = None,  # type: ignore
    ) -> List[dict]:
        return healthy_deployments

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """
        Track spend for virtual key + model in DualCache

        Example: key=sk-1234567890, model=gpt-4o, max_budget=100, time_period=1d
        """
        verbose_proxy_logger.debug("in RouterBudgetLimiting.async_log_success_event")
        standard_logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
            "standard_logging_object", None
        )
        if standard_logging_payload is None:
            raise ValueError("standard_logging_payload is required")

        _litellm_params: dict = kwargs.get("litellm_params", {}) or {}
        _metadata: dict = _litellm_params.get("metadata", {}) or {}
        user_api_key_model_max_budget: Optional[dict] = _metadata.get(
            "user_api_key_model_max_budget", None
        )
        if (
            user_api_key_model_max_budget is None
            or len(user_api_key_model_max_budget) == 0
        ):
            verbose_proxy_logger.debug(
                "Not running _PROXY_VirtualKeyModelMaxBudgetLimiter.async_log_success_event because user_api_key_model_max_budget is None or empty. `user_api_key_model_max_budget`=%s",
                user_api_key_model_max_budget,
            )
            return
        response_cost: float = standard_logging_payload.get("response_cost", 0)
        model = standard_logging_payload.get("model")

        virtual_key = standard_logging_payload.get("metadata").get("user_api_key_hash")
        model = standard_logging_payload.get("model")
        if virtual_key is not None:
            budget_config = BudgetConfig(time_period="1d", budget_limit=0.1)
            virtual_spend_key = f"{VIRTUAL_KEY_SPEND_CACHE_KEY_PREFIX}:{virtual_key}:{model}:{budget_config.budget_duration}"
            virtual_start_time_key = f"virtual_key_budget_start_time:{virtual_key}"
            await self._increment_spend_for_key(
                budget_config=budget_config,
                spend_key=virtual_spend_key,
                start_time_key=virtual_start_time_key,
                response_cost=response_cost,
            )
        verbose_proxy_logger.debug(
            "current state of in memory cache %s",
            json.dumps(
                self.dual_cache.in_memory_cache.cache_dict, indent=4, default=str
            ),
        )

# === NexusCore/openenv\Lib\site-packages\numpy\_utils\_inspect.py ===
"""Subset of inspect module from upstream python

We use this instead of upstream because upstream inspect is slow to import, and
significantly contributes to numpy import times. Importing this copy has almost
no overhead.

"""
import types

__all__ = ['getargspec', 'formatargspec']

# ----------------------------------------------------------- type-checking
def ismethod(object):
    """Return true if the object is an instance method.

    Instance method objects provide these attributes:
        __doc__         documentation string
        __name__        name with which this method was defined
        im_class        class object in which this method belongs
        im_func         function object containing implementation of method
        im_self         instance to which this method is bound, or None

    """
    return isinstance(object, types.MethodType)

def isfunction(object):
    """Return true if the object is a user-defined function.

    Function objects provide these attributes:
        __doc__         documentation string
        __name__        name with which this function was defined
        func_code       code object containing compiled function bytecode
        func_defaults   tuple of any default values for arguments
        func_doc        (same as __doc__)
        func_globals    global namespace in which this function was defined
        func_name       (same as __name__)

    """
    return isinstance(object, types.FunctionType)

def iscode(object):
    """Return true if the object is a code object.

    Code objects provide these attributes:
        co_argcount     number of arguments (not including * or ** args)
        co_code         string of raw compiled bytecode
        co_consts       tuple of constants used in the bytecode
        co_filename     name of file in which this code object was created
        co_firstlineno  number of first line in Python source code
        co_flags        bitmap: 1=optimized | 2=newlocals | 4=*arg | 8=**arg
        co_lnotab       encoded mapping of line numbers to bytecode indices
        co_name         name with which this code object was defined
        co_names        tuple of names of local variables
        co_nlocals      number of local variables
        co_stacksize    virtual machine stack space required
        co_varnames     tuple of names of arguments and local variables

    """
    return isinstance(object, types.CodeType)


# ------------------------------------------------ argument list extraction
# These constants are from Python's compile.h.
CO_OPTIMIZED, CO_NEWLOCALS, CO_VARARGS, CO_VARKEYWORDS = 1, 2, 4, 8

def getargs(co):
    """Get information about the arguments accepted by a code object.

    Three things are returned: (args, varargs, varkw), where 'args' is
    a list of argument names (possibly containing nested lists), and
    'varargs' and 'varkw' are the names of the * and ** arguments or None.

    """

    if not iscode(co):
        raise TypeError('arg is not a code object')

    nargs = co.co_argcount
    names = co.co_varnames
    args = list(names[:nargs])

    # The following acrobatics are for anonymous (tuple) arguments.
    # Which we do not need to support, so remove to avoid importing
    # the dis module.
    for i in range(nargs):
        if args[i][:1] in ['', '.']:
            raise TypeError("tuple function arguments are not supported")
    varargs = None
    if co.co_flags & CO_VARARGS:
        varargs = co.co_varnames[nargs]
        nargs = nargs + 1
    varkw = None
    if co.co_flags & CO_VARKEYWORDS:
        varkw = co.co_varnames[nargs]
    return args, varargs, varkw

def getargspec(func):
    """Get the names and default values of a function's arguments.

    A tuple of four things is returned: (args, varargs, varkw, defaults).
    'args' is a list of the argument names (it may contain nested lists).
    'varargs' and 'varkw' are the names of the * and ** arguments or None.
    'defaults' is an n-tuple of the default values of the last n arguments.

    """

    if ismethod(func):
        func = func.__func__
    if not isfunction(func):
        raise TypeError('arg is not a Python function')
    args, varargs, varkw = getargs(func.__code__)
    return args, varargs, varkw, func.__defaults__

def getargvalues(frame):
    """Get information about arguments passed into a particular frame.

    A tuple of four things is returned: (args, varargs, varkw, locals).
    'args' is a list of the argument names (it may contain nested lists).
    'varargs' and 'varkw' are the names of the * and ** arguments or None.
    'locals' is the locals dictionary of the given frame.

    """
    args, varargs, varkw = getargs(frame.f_code)
    return args, varargs, varkw, frame.f_locals

def joinseq(seq):
    if len(seq) == 1:
        return '(' + seq[0] + ',)'
    else:
        return '(' + ', '.join(seq) + ')'

def strseq(object, convert, join=joinseq):
    """Recursively walk a sequence, stringifying each element.

    """
    if type(object) in [list, tuple]:
        return join([strseq(_o, convert, join) for _o in object])
    else:
        return convert(object)

def formatargspec(args, varargs=None, varkw=None, defaults=None,
                  formatarg=str,
                  formatvarargs=lambda name: '*' + name,
                  formatvarkw=lambda name: '**' + name,
                  formatvalue=lambda value: '=' + repr(value),
                  join=joinseq):
    """Format an argument spec from the 4 values returned by getargspec.

    The first four arguments are (args, varargs, varkw, defaults).  The
    other four arguments are the corresponding optional formatting functions
    that are called to turn names and values into strings.  The ninth
    argument is an optional function to format the sequence of arguments.

    """
    specs = []
    if defaults:
        firstdefault = len(args) - len(defaults)
    for i in range(len(args)):
        spec = strseq(args[i], formatarg, join)
        if defaults and i >= firstdefault:
            spec = spec + formatvalue(defaults[i - firstdefault])
        specs.append(spec)
    if varargs is not None:
        specs.append(formatvarargs(varargs))
    if varkw is not None:
        specs.append(formatvarkw(varkw))
    return '(' + ', '.join(specs) + ')'

def formatargvalues(args, varargs, varkw, locals,
                    formatarg=str,
                    formatvarargs=lambda name: '*' + name,
                    formatvarkw=lambda name: '**' + name,
                    formatvalue=lambda value: '=' + repr(value),
                    join=joinseq):
    """Format an argument spec from the 4 values returned by getargvalues.

    The first four arguments are (args, varargs, varkw, locals).  The
    next four arguments are the corresponding optional formatting functions
    that are called to turn names and values into strings.  The ninth
    argument is an optional function to format the sequence of arguments.

    """
    def convert(name, locals=locals,
                formatarg=formatarg, formatvalue=formatvalue):
        return formatarg(name) + formatvalue(locals[name])
    specs = [strseq(arg, convert, join) for arg in args]

    if varargs:
        specs.append(formatvarargs(varargs) + formatvalue(locals[varargs]))
    if varkw:
        specs.append(formatvarkw(varkw) + formatvalue(locals[varkw]))
    return '(' + ', '.join(specs) + ')'

# === NexusCore/openenv\Lib\site-packages\pyasn1\type\namedval.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
# ASN.1 named integers
#
from pyasn1 import error

__all__ = ['NamedValues']


class NamedValues(object):
    """Create named values object.

    The |NamedValues| object represents a collection of string names
    associated with numeric IDs. These objects are used for giving
    names to otherwise numerical values.

    |NamedValues| objects are immutable and duck-type Python
    :class:`dict` object mapping ID to name and vice-versa.

    Parameters
    ----------
    *args: variable number of two-element :py:class:`tuple`

        name: :py:class:`str`
            Value label

        value: :py:class:`int`
            Numeric value

    Keyword Args
    ------------
    name: :py:class:`str`
        Value label

    value: :py:class:`int`
        Numeric value

    Examples
    --------

    .. code-block:: pycon

        >>> nv = NamedValues('a', 'b', ('c', 0), d=1)
        >>> nv
        >>> {'c': 0, 'd': 1, 'a': 2, 'b': 3}
        >>> nv[0]
        'c'
        >>> nv['a']
        2
    """
    def __init__(self, *args, **kwargs):
        self.__names = {}
        self.__numbers = {}

        anonymousNames = []

        for namedValue in args:
            if isinstance(namedValue, (tuple, list)):
                try:
                    name, number = namedValue

                except ValueError:
                    raise error.PyAsn1Error('Not a proper attribute-value pair %r' % (namedValue,))

            else:
                anonymousNames.append(namedValue)
                continue

            if name in self.__names:
                raise error.PyAsn1Error('Duplicate name %s' % (name,))

            if number in self.__numbers:
                raise error.PyAsn1Error('Duplicate number  %s=%s' % (name, number))

            self.__names[name] = number
            self.__numbers[number] = name

        for name, number in kwargs.items():
            if name in self.__names:
                raise error.PyAsn1Error('Duplicate name %s' % (name,))

            if number in self.__numbers:
                raise error.PyAsn1Error('Duplicate number  %s=%s' % (name, number))

            self.__names[name] = number
            self.__numbers[number] = name

        if anonymousNames:

            number = self.__numbers and max(self.__numbers) + 1 or 0

            for name in anonymousNames:

                if name in self.__names:
                    raise error.PyAsn1Error('Duplicate name %s' % (name,))

                self.__names[name] = number
                self.__numbers[number] = name

                number += 1

    def __repr__(self):
        representation = ', '.join(['%s=%d' % x for x in self.items()])

        if len(representation) > 64:
            representation = representation[:32] + '...' + representation[-32:]

        return '<%s object, enums %s>' % (
            self.__class__.__name__, representation)

    def __eq__(self, other):
        return dict(self) == other

    def __ne__(self, other):
        return dict(self) != other

    def __lt__(self, other):
        return dict(self) < other

    def __le__(self, other):
        return dict(self) <= other

    def __gt__(self, other):
        return dict(self) > other

    def __ge__(self, other):
        return dict(self) >= other

    def __hash__(self):
        return hash(self.items())

    # Python dict protocol (read-only)

    def __getitem__(self, key):
        try:
            return self.__numbers[key]

        except KeyError:
            return self.__names[key]

    def __len__(self):
        return len(self.__names)

    def __contains__(self, key):
        return key in self.__names or key in self.__numbers

    def __iter__(self):
        return iter(self.__names)

    def values(self):
        return iter(self.__numbers)

    def keys(self):
        return iter(self.__names)

    def items(self):
        for name in self.__names:
            yield name, self.__names[name]

    # support merging

    def __add__(self, namedValues):
        return self.__class__(*tuple(self.items()) + tuple(namedValues.items()))

    # XXX clone/subtype?

    def clone(self, *args, **kwargs):
        new = self.__class__(*args, **kwargs)
        return self + new

    # legacy protocol

    def getName(self, value):
        if value in self.__numbers:
            return self.__numbers[value]

    def getValue(self, name):
        if name in self.__names:
            return self.__names[name]

    def getValues(self, *names):
        try:
            return [self.__names[name] for name in names]

        except KeyError:
            raise error.PyAsn1Error(
                'Unknown bit identifier(s): %s' % (set(names).difference(self.__names),)
            )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\bidi\browser.py ===
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

from typing import Dict, List

from selenium.webdriver.common.bidi.common import command_builder


class ClientWindowState:
    """Represents a window state."""

    FULLSCREEN = "fullscreen"
    MAXIMIZED = "maximized"
    MINIMIZED = "minimized"
    NORMAL = "normal"


class ClientWindowInfo:
    """Represents a client window information."""

    def __init__(
        self,
        client_window: str,
        state: str,
        width: int,
        height: int,
        x: int,
        y: int,
        active: bool,
    ):
        self.client_window = client_window
        self.state = state
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.active = active

    def get_state(self) -> str:
        """Gets the state of the client window.

        Returns:
        -------
            str: The state of the client window (one of the ClientWindowState constants).
        """
        return self.state

    def get_client_window(self) -> str:
        """Gets the client window identifier.

        Returns:
        -------
            str: The client window identifier.
        """
        return self.client_window

    def get_width(self) -> int:
        """Gets the width of the client window.

        Returns:
        -------
            int: The width of the client window.
        """
        return self.width

    def get_height(self) -> int:
        """Gets the height of the client window.

        Returns:
        -------
            int: The height of the client window.
        """
        return self.height

    def get_x(self) -> int:
        """Gets the x coordinate of the client window.

        Returns:
        -------
            int: The x coordinate of the client window.
        """
        return self.x

    def get_y(self) -> int:
        """Gets the y coordinate of the client window.

        Returns:
        -------
            int: The y coordinate of the client window.
        """
        return self.y

    def is_active(self) -> bool:
        """Checks if the client window is active.

        Returns:
        -------
            bool: True if the client window is active, False otherwise.
        """
        return self.active

    @classmethod
    def from_dict(cls, data: Dict) -> "ClientWindowInfo":
        """Creates a ClientWindowInfo instance from a dictionary.

        Parameters:
        -----------
            data: A dictionary containing the client window information.

        Returns:
        -------
            ClientWindowInfo: A new instance of ClientWindowInfo.
        """
        return cls(
            client_window=data.get("clientWindow"),
            state=data.get("state"),
            width=data.get("width"),
            height=data.get("height"),
            x=data.get("x"),
            y=data.get("y"),
            active=data.get("active"),
        )


class Browser:
    """
    BiDi implementation of the browser module.
    """

    def __init__(self, conn):
        self.conn = conn

    def create_user_context(self) -> str:
        """Creates a new user context.

        Returns:
        -------
            str: The ID of the created user context.
        """
        result = self.conn.execute(command_builder("browser.createUserContext", {}))
        return result["userContext"]

    def get_user_contexts(self) -> List[str]:
        """Gets all user contexts.

        Returns:
        -------
            List[str]: A list of user context IDs.
        """
        result = self.conn.execute(command_builder("browser.getUserContexts", {}))
        return [context_info["userContext"] for context_info in result["userContexts"]]

    def remove_user_context(self, user_context_id: str) -> None:
        """Removes a user context.

        Parameters:
        -----------
            user_context_id: The ID of the user context to remove.

        Raises:
        ------
            Exception: If the user context ID is "default" or does not exist.
        """
        if user_context_id == "default":
            raise Exception("Cannot remove the default user context")

        params = {"userContext": user_context_id}
        self.conn.execute(command_builder("browser.removeUserContext", params))

    def get_client_windows(self) -> List[ClientWindowInfo]:
        """Gets all client windows.

        Returns:
        -------
            List[ClientWindowInfo]: A list of client window information.
        """
        result = self.conn.execute(command_builder("browser.getClientWindows", {}))
        return [ClientWindowInfo.from_dict(window) for window in result["clientWindows"]]

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\_tokenizer.py ===
import contextlib
import re
from dataclasses import dataclass
from typing import Dict, Iterator, NoReturn, Optional, Tuple, Union

from .specifiers import Specifier


@dataclass
class Token:
    name: str
    text: str
    position: int


class ParserSyntaxError(Exception):
    """The provided source text could not be parsed correctly."""

    def __init__(
        self,
        message: str,
        *,
        source: str,
        span: Tuple[int, int],
    ) -> None:
        self.span = span
        self.message = message
        self.source = source

        super().__init__()

    def __str__(self) -> str:
        marker = " " * self.span[0] + "~" * (self.span[1] - self.span[0]) + "^"
        return "\n    ".join([self.message, self.source, marker])


DEFAULT_RULES: "Dict[str, Union[str, re.Pattern[str]]]" = {
    "LEFT_PARENTHESIS": r"\(",
    "RIGHT_PARENTHESIS": r"\)",
    "LEFT_BRACKET": r"\[",
    "RIGHT_BRACKET": r"\]",
    "SEMICOLON": r";",
    "COMMA": r",",
    "QUOTED_STRING": re.compile(
        r"""
            (
                ('[^']*')
                |
                ("[^"]*")
            )
        """,
        re.VERBOSE,
    ),
    "OP": r"(===|==|~=|!=|<=|>=|<|>)",
    "BOOLOP": r"\b(or|and)\b",
    "IN": r"\bin\b",
    "NOT": r"\bnot\b",
    "VARIABLE": re.compile(
        r"""
            \b(
                python_version
                |python_full_version
                |os[._]name
                |sys[._]platform
                |platform_(release|system)
                |platform[._](version|machine|python_implementation)
                |python_implementation
                |implementation_(name|version)
                |extra
            )\b
        """,
        re.VERBOSE,
    ),
    "SPECIFIER": re.compile(
        Specifier._operator_regex_str + Specifier._version_regex_str,
        re.VERBOSE | re.IGNORECASE,
    ),
    "AT": r"\@",
    "URL": r"[^ \t]+",
    "IDENTIFIER": r"\b[a-zA-Z0-9][a-zA-Z0-9._-]*\b",
    "VERSION_PREFIX_TRAIL": r"\.\*",
    "VERSION_LOCAL_LABEL_TRAIL": r"\+[a-z0-9]+(?:[-_\.][a-z0-9]+)*",
    "WS": r"[ \t]+",
    "END": r"$",
}


class Tokenizer:
    """Context-sensitive token parsing.

    Provides methods to examine the input stream to check whether the next token
    matches.
    """

    def __init__(
        self,
        source: str,
        *,
        rules: "Dict[str, Union[str, re.Pattern[str]]]",
    ) -> None:
        self.source = source
        self.rules: Dict[str, re.Pattern[str]] = {
            name: re.compile(pattern) for name, pattern in rules.items()
        }
        self.next_token: Optional[Token] = None
        self.position = 0

    def consume(self, name: str) -> None:
        """Move beyond provided token name, if at current position."""
        if self.check(name):
            self.read()

    def check(self, name: str, *, peek: bool = False) -> bool:
        """Check whether the next token has the provided name.

        By default, if the check succeeds, the token *must* be read before
        another check. If `peek` is set to `True`, the token is not loaded and
        would need to be checked again.
        """
        assert (
            self.next_token is None
        ), f"Cannot check for {name!r}, already have {self.next_token!r}"
        assert name in self.rules, f"Unknown token name: {name!r}"

        expression = self.rules[name]

        match = expression.match(self.source, self.position)
        if match is None:
            return False
        if not peek:
            self.next_token = Token(name, match[0], self.position)
        return True

    def expect(self, name: str, *, expected: str) -> Token:
        """Expect a certain token name next, failing with a syntax error otherwise.

        The token is *not* read.
        """
        if not self.check(name):
            raise self.raise_syntax_error(f"Expected {expected}")
        return self.read()

    def read(self) -> Token:
        """Consume the next token and return it."""
        token = self.next_token
        assert token is not None

        self.position += len(token.text)
        self.next_token = None

        return token

    def raise_syntax_error(
        self,
        message: str,
        *,
        span_start: Optional[int] = None,
        span_end: Optional[int] = None,
    ) -> NoReturn:
        """Raise ParserSyntaxError at the given position."""
        span = (
            self.position if span_start is None else span_start,
            self.position if span_end is None else span_end,
        )
        raise ParserSyntaxError(
            message,
            source=self.source,
            span=span,
        )

    @contextlib.contextmanager
    def enclosing_tokens(
        self, open_token: str, close_token: str, *, around: str
    ) -> Iterator[None]:
        if self.check(open_token):
            open_position = self.position
            self.read()
        else:
            open_position = None

        yield

        if open_position is None:
            return

        if not self.check(close_token):
            self.raise_syntax_error(
                f"Expected matching {close_token} for {open_token}, after {around}",
                span_start=open_position,
            )

        self.read()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\default_styles.py ===
from typing import Dict

from .style import Style

DEFAULT_STYLES: Dict[str, Style] = {
    "none": Style.null(),
    "reset": Style(
        color="default",
        bgcolor="default",
        dim=False,
        bold=False,
        italic=False,
        underline=False,
        blink=False,
        blink2=False,
        reverse=False,
        conceal=False,
        strike=False,
    ),
    "dim": Style(dim=True),
    "bright": Style(dim=False),
    "bold": Style(bold=True),
    "strong": Style(bold=True),
    "code": Style(reverse=True, bold=True),
    "italic": Style(italic=True),
    "emphasize": Style(italic=True),
    "underline": Style(underline=True),
    "blink": Style(blink=True),
    "blink2": Style(blink2=True),
    "reverse": Style(reverse=True),
    "strike": Style(strike=True),
    "black": Style(color="black"),
    "red": Style(color="red"),
    "green": Style(color="green"),
    "yellow": Style(color="yellow"),
    "magenta": Style(color="magenta"),
    "cyan": Style(color="cyan"),
    "white": Style(color="white"),
    "inspect.attr": Style(color="yellow", italic=True),
    "inspect.attr.dunder": Style(color="yellow", italic=True, dim=True),
    "inspect.callable": Style(bold=True, color="red"),
    "inspect.async_def": Style(italic=True, color="bright_cyan"),
    "inspect.def": Style(italic=True, color="bright_cyan"),
    "inspect.class": Style(italic=True, color="bright_cyan"),
    "inspect.error": Style(bold=True, color="red"),
    "inspect.equals": Style(),
    "inspect.help": Style(color="cyan"),
    "inspect.doc": Style(dim=True),
    "inspect.value.border": Style(color="green"),
    "live.ellipsis": Style(bold=True, color="red"),
    "layout.tree.row": Style(dim=False, color="red"),
    "layout.tree.column": Style(dim=False, color="blue"),
    "logging.keyword": Style(bold=True, color="yellow"),
    "logging.level.notset": Style(dim=True),
    "logging.level.debug": Style(color="green"),
    "logging.level.info": Style(color="blue"),
    "logging.level.warning": Style(color="yellow"),
    "logging.level.error": Style(color="red", bold=True),
    "logging.level.critical": Style(color="red", bold=True, reverse=True),
    "log.level": Style.null(),
    "log.time": Style(color="cyan", dim=True),
    "log.message": Style.null(),
    "log.path": Style(dim=True),
    "repr.ellipsis": Style(color="yellow"),
    "repr.indent": Style(color="green", dim=True),
    "repr.error": Style(color="red", bold=True),
    "repr.str": Style(color="green", italic=False, bold=False),
    "repr.brace": Style(bold=True),
    "repr.comma": Style(bold=True),
    "repr.ipv4": Style(bold=True, color="bright_green"),
    "repr.ipv6": Style(bold=True, color="bright_green"),
    "repr.eui48": Style(bold=True, color="bright_green"),
    "repr.eui64": Style(bold=True, color="bright_green"),
    "repr.tag_start": Style(bold=True),
    "repr.tag_name": Style(color="bright_magenta", bold=True),
    "repr.tag_contents": Style(color="default"),
    "repr.tag_end": Style(bold=True),
    "repr.attrib_name": Style(color="yellow", italic=False),
    "repr.attrib_equal": Style(bold=True),
    "repr.attrib_value": Style(color="magenta", italic=False),
    "repr.number": Style(color="cyan", bold=True, italic=False),
    "repr.number_complex": Style(color="cyan", bold=True, italic=False),  # same
    "repr.bool_true": Style(color="bright_green", italic=True),
    "repr.bool_false": Style(color="bright_red", italic=True),
    "repr.none": Style(color="magenta", italic=True),
    "repr.url": Style(underline=True, color="bright_blue", italic=False, bold=False),
    "repr.uuid": Style(color="bright_yellow", bold=False),
    "repr.call": Style(color="magenta", bold=True),
    "repr.path": Style(color="magenta"),
    "repr.filename": Style(color="bright_magenta"),
    "rule.line": Style(color="bright_green"),
    "rule.text": Style.null(),
    "json.brace": Style(bold=True),
    "json.bool_true": Style(color="bright_green", italic=True),
    "json.bool_false": Style(color="bright_red", italic=True),
    "json.null": Style(color="magenta", italic=True),
    "json.number": Style(color="cyan", bold=True, italic=False),
    "json.str": Style(color="green", italic=False, bold=False),
    "json.key": Style(color="blue", bold=True),
    "prompt": Style.null(),
    "prompt.choices": Style(color="magenta", bold=True),
    "prompt.default": Style(color="cyan", bold=True),
    "prompt.invalid": Style(color="red"),
    "prompt.invalid.choice": Style(color="red"),
    "pretty": Style.null(),
    "scope.border": Style(color="blue"),
    "scope.key": Style(color="yellow", italic=True),
    "scope.key.special": Style(color="yellow", italic=True, dim=True),
    "scope.equals": Style(color="red"),
    "table.header": Style(bold=True),
    "table.footer": Style(bold=True),
    "table.cell": Style.null(),
    "table.title": Style(italic=True),
    "table.caption": Style(italic=True, dim=True),
    "traceback.error": Style(color="red", italic=True),
    "traceback.border.syntax_error": Style(color="bright_red"),
    "traceback.border": Style(color="red"),
    "traceback.text": Style.null(),
    "traceback.title": Style(color="red", bold=True),
    "traceback.exc_type": Style(color="bright_red", bold=True),
    "traceback.exc_value": Style.null(),
    "traceback.offset": Style(color="bright_red", bold=True),
    "traceback.error_range": Style(underline=True, bold=True, dim=False),
    "bar.back": Style(color="grey23"),
    "bar.complete": Style(color="rgb(249,38,114)"),
    "bar.finished": Style(color="rgb(114,156,31)"),
    "bar.pulse": Style(color="rgb(249,38,114)"),
    "progress.description": Style.null(),
    "progress.filesize": Style(color="green"),
    "progress.filesize.total": Style(color="green"),
    "progress.download": Style(color="green"),
    "progress.elapsed": Style(color="yellow"),
    "progress.percentage": Style(color="magenta"),
    "progress.remaining": Style(color="cyan"),
    "progress.data.speed": Style(color="red"),
    "progress.spinner": Style(color="green"),
    "status.spinner": Style(color="green"),
    "tree": Style(),
    "tree.line": Style(),
    "markdown.paragraph": Style(),
    "markdown.text": Style(),
    "markdown.em": Style(italic=True),
    "markdown.emph": Style(italic=True),  # For commonmark backwards compatibility
    "markdown.strong": Style(bold=True),
    "markdown.code": Style(bold=True, color="cyan", bgcolor="black"),
    "markdown.code_block": Style(color="cyan", bgcolor="black"),
    "markdown.block_quote": Style(color="magenta"),
    "markdown.list": Style(color="cyan"),
    "markdown.item": Style(),
    "markdown.item.bullet": Style(color="yellow", bold=True),
    "markdown.item.number": Style(color="yellow", bold=True),
    "markdown.hr": Style(color="yellow"),
    "markdown.h1.border": Style(),
    "markdown.h1": Style(bold=True),
    "markdown.h2": Style(bold=True, underline=True),
    "markdown.h3": Style(bold=True),
    "markdown.h4": Style(bold=True, dim=True),
    "markdown.h5": Style(underline=True),
    "markdown.h6": Style(italic=True),
    "markdown.h7": Style(italic=True, dim=True),
    "markdown.link": Style(color="bright_blue"),
    "markdown.link_url": Style(color="blue", underline=True),
    "markdown.s": Style(strike=True),
    "iso8601.date": Style(color="blue"),
    "iso8601.time": Style(color="magenta"),
    "iso8601.timezone": Style(color="yellow"),
}


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import io

    from pip._vendor.rich.console import Console
    from pip._vendor.rich.table import Table
    from pip._vendor.rich.text import Text

    parser = argparse.ArgumentParser()
    parser.add_argument("--html", action="store_true", help="Export as HTML table")
    args = parser.parse_args()
    html: bool = args.html
    console = Console(record=True, width=70, file=io.StringIO()) if html else Console()

    table = Table("Name", "Styling")

    for style_name, style in DEFAULT_STYLES.items():
        table.add_row(Text(style_name, style=style), str(style))

    console.print(table)
    if html:
        print(console.export_html(inline_styles=True))

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\request.py ===
from __future__ import absolute_import

import sys

from .filepost import encode_multipart_formdata
from .packages import six
from .packages.six.moves.urllib.parse import urlencode

__all__ = ["RequestMethods"]


class RequestMethods(object):
    """
    Convenience mixin for classes who implement a :meth:`urlopen` method, such
    as :class:`urllib3.HTTPConnectionPool` and
    :class:`urllib3.PoolManager`.

    Provides behavior for making common types of HTTP request methods and
    decides which type of request field encoding to use.

    Specifically,

    :meth:`.request_encode_url` is for sending requests whose fields are
    encoded in the URL (such as GET, HEAD, DELETE).

    :meth:`.request_encode_body` is for sending requests whose fields are
    encoded in the *body* of the request using multipart or www-form-urlencoded
    (such as for POST, PUT, PATCH).

    :meth:`.request` is for making any kind of request, it will look up the
    appropriate encoding format and use one of the above two methods to make
    the request.

    Initializer parameters:

    :param headers:
        Headers to include with all requests, unless other headers are given
        explicitly.
    """

    _encode_url_methods = {"DELETE", "GET", "HEAD", "OPTIONS"}

    def __init__(self, headers=None):
        self.headers = headers or {}

    def urlopen(
        self,
        method,
        url,
        body=None,
        headers=None,
        encode_multipart=True,
        multipart_boundary=None,
        **kw
    ):  # Abstract
        raise NotImplementedError(
            "Classes extending RequestMethods must implement "
            "their own ``urlopen`` method."
        )

    def request(self, method, url, fields=None, headers=None, **urlopen_kw):
        """
        Make a request using :meth:`urlopen` with the appropriate encoding of
        ``fields`` based on the ``method`` used.

        This is a convenience method that requires the least amount of manual
        effort. It can be used in most situations, while still having the
        option to drop down to more specific methods when necessary, such as
        :meth:`request_encode_url`, :meth:`request_encode_body`,
        or even the lowest level :meth:`urlopen`.
        """
        method = method.upper()

        urlopen_kw["request_url"] = url

        if method in self._encode_url_methods:
            return self.request_encode_url(
                method, url, fields=fields, headers=headers, **urlopen_kw
            )
        else:
            return self.request_encode_body(
                method, url, fields=fields, headers=headers, **urlopen_kw
            )

    def request_encode_url(self, method, url, fields=None, headers=None, **urlopen_kw):
        """
        Make a request using :meth:`urlopen` with the ``fields`` encoded in
        the url. This is useful for request methods like GET, HEAD, DELETE, etc.
        """
        if headers is None:
            headers = self.headers

        extra_kw = {"headers": headers}
        extra_kw.update(urlopen_kw)

        if fields:
            url += "?" + urlencode(fields)

        return self.urlopen(method, url, **extra_kw)

    def request_encode_body(
        self,
        method,
        url,
        fields=None,
        headers=None,
        encode_multipart=True,
        multipart_boundary=None,
        **urlopen_kw
    ):
        """
        Make a request using :meth:`urlopen` with the ``fields`` encoded in
        the body. This is useful for request methods like POST, PUT, PATCH, etc.

        When ``encode_multipart=True`` (default), then
        :func:`urllib3.encode_multipart_formdata` is used to encode
        the payload with the appropriate content type. Otherwise
        :func:`urllib.parse.urlencode` is used with the
        'application/x-www-form-urlencoded' content type.

        Multipart encoding must be used when posting files, and it's reasonably
        safe to use it in other times too. However, it may break request
        signing, such as with OAuth.

        Supports an optional ``fields`` parameter of key/value strings AND
        key/filetuple. A filetuple is a (filename, data, MIME type) tuple where
        the MIME type is optional. For example::

            fields = {
                'foo': 'bar',
                'fakefile': ('foofile.txt', 'contents of foofile'),
                'realfile': ('barfile.txt', open('realfile').read()),
                'typedfile': ('bazfile.bin', open('bazfile').read(),
                              'image/jpeg'),
                'nonamefile': 'contents of nonamefile field',
            }

        When uploading a file, providing a filename (the first parameter of the
        tuple) is optional but recommended to best mimic behavior of browsers.

        Note that if ``headers`` are supplied, the 'Content-Type' header will
        be overwritten because it depends on the dynamic random boundary string
        which is used to compose the body of the request. The random boundary
        string can be explicitly set with the ``multipart_boundary`` parameter.
        """
        if headers is None:
            headers = self.headers

        extra_kw = {"headers": {}}

        if fields:
            if "body" in urlopen_kw:
                raise TypeError(
                    "request got values for both 'fields' and 'body', can only specify one."
                )

            if encode_multipart:
                body, content_type = encode_multipart_formdata(
                    fields, boundary=multipart_boundary
                )
            else:
                body, content_type = (
                    urlencode(fields),
                    "application/x-www-form-urlencoded",
                )

            extra_kw["body"] = body
            extra_kw["headers"] = {"Content-Type": content_type}

        extra_kw["headers"].update(headers)
        extra_kw.update(urlopen_kw)

        return self.urlopen(method, url, **extra_kw)


if not six.PY2:

    class RequestModule(sys.modules[__name__].__class__):
        def __call__(self, *args, **kwargs):
            """
            If user tries to call this module directly urllib3 v2.x style raise an error to the user
            suggesting they may need urllib3 v2
            """
            raise TypeError(
                "'module' object is not callable\n"
                "urllib3.request() method is not supported in this release, "
                "upgrade to urllib3 v2 to use it\n"
                "see https://urllib3.readthedocs.io/en/stable/v2-migration-guide.html"
            )

    sys.modules[__name__].__class__ = RequestModule

# === NexusCore/openenv\Lib\site-packages\isapi\threaded_extension.py ===
"""An ISAPI extension base class implemented using a thread-pool."""

# $Id$

import sys
import threading
import time
import traceback

from pywintypes import OVERLAPPED
from win32event import INFINITE
from win32file import (
    CloseHandle,
    CreateIoCompletionPort,
    GetQueuedCompletionStatus,
    PostQueuedCompletionStatus,
)
from win32security import SetThreadToken

import isapi.simple
from isapi import ExtensionError, isapicon

ISAPI_REQUEST = 1
ISAPI_SHUTDOWN = 2


class WorkerThread(threading.Thread):
    def __init__(self, extension, io_req_port):
        self.running = False
        self.io_req_port = io_req_port
        self.extension = extension
        threading.Thread.__init__(self)
        # We wait 15 seconds for a thread to terminate, but if it fails to,
        # we don't want the process to hang at exit waiting for it...
        self.setDaemon(True)

    def run(self):
        self.running = True
        while self.running:
            errCode, bytes, key, overlapped = GetQueuedCompletionStatus(
                self.io_req_port, INFINITE
            )
            if key == ISAPI_SHUTDOWN and overlapped is None:
                break

            # Let the parent extension handle the command.
            dispatcher = self.extension.dispatch_map.get(key)
            if dispatcher is None:
                raise RuntimeError(f"Bad request '{key}'")

            dispatcher(errCode, bytes, key, overlapped)

    def call_handler(self, cblock):
        self.extension.Dispatch(cblock)


# A generic thread-pool based extension, using IO Completion Ports.
# Sub-classes can override one method to implement a simple extension, or
# may leverage the CompletionPort to queue their own requests, and implement a
# fully asynch extension.
class ThreadPoolExtension(isapi.simple.SimpleExtension):
    "Base class for an ISAPI extension based around a thread-pool"

    max_workers = 20
    worker_shutdown_wait = 15000  # 15 seconds for workers to quit...

    def __init__(self):
        self.workers = []
        # extensible dispatch map, for sub-classes that need to post their
        # own requests to the completion port.
        # Each of these functions is called with the result of
        # GetQueuedCompletionStatus for our port.
        self.dispatch_map = {
            ISAPI_REQUEST: self.DispatchConnection,
        }

    def GetExtensionVersion(self, vi):
        isapi.simple.SimpleExtension.GetExtensionVersion(self, vi)
        # As per Q192800, the CompletionPort should be created with the number
        # of processors, even if the number of worker threads is much larger.
        # Passing 0 means the system picks the number.
        self.io_req_port = CreateIoCompletionPort(-1, None, 0, 0)
        # start up the workers
        self.workers = []
        for i in range(self.max_workers):
            worker = WorkerThread(self, self.io_req_port)
            worker.start()
            self.workers.append(worker)

    def HttpExtensionProc(self, control_block):
        overlapped = OVERLAPPED()
        overlapped.object = control_block
        PostQueuedCompletionStatus(self.io_req_port, 0, ISAPI_REQUEST, overlapped)
        return isapicon.HSE_STATUS_PENDING

    def TerminateExtension(self, status):
        for worker in self.workers:
            worker.running = False
        for worker in self.workers:
            PostQueuedCompletionStatus(self.io_req_port, 0, ISAPI_SHUTDOWN, None)
        # wait for them to terminate - pity we aren't using 'native' threads
        # as then we could do a smart wait - but now we need to poll....
        end_time = time.time() + self.worker_shutdown_wait / 1000
        alive = self.workers
        while alive:
            if time.time() > end_time:
                # xxx - might be nice to log something here.
                break
            time.sleep(0.2)
            alive = [w for w in alive if w.is_alive()]
        self.dispatch_map = {}  # break circles
        CloseHandle(self.io_req_port)

    # This is the one operation the base class supports - a simple
    # Connection request.  We setup the thread-token, and dispatch to the
    # sub-class's 'Dispatch' method.
    def DispatchConnection(self, errCode, bytes, key, overlapped):
        control_block = overlapped.object
        # setup the correct user for this request
        hRequestToken = control_block.GetImpersonationToken()
        SetThreadToken(None, hRequestToken)
        try:
            try:
                self.Dispatch(control_block)
            except:
                self.HandleDispatchError(control_block)
        finally:
            # reset the security context
            SetThreadToken(None, None)

    def Dispatch(self, ecb):
        """Overridden by the sub-class to handle connection requests.

        This class creates a thread-pool using a Windows completion port,
        and dispatches requests via this port.  Sub-classes can generally
        implement each connection request using blocking reads and writes, and
        the thread-pool will still provide decent response to the end user.

        The sub-class can set a max_workers attribute (default is 20).  Note
        that this generally does *not* mean 20 threads will all be concurrently
        running, via the magic of Windows completion ports.

        There is no default implementation - sub-classes must implement this.
        """
        raise NotImplementedError("sub-classes should override Dispatch")

    def HandleDispatchError(self, ecb):
        """Handles errors in the Dispatch method.

        When a Dispatch method call fails, this method is called to handle
        the exception.  The default implementation formats the traceback
        in the browser.
        """
        ecb.HttpStatusCode = isapicon.HSE_STATUS_ERROR
        # control_block.LogData = "we failed!"
        exc_typ, exc_val, exc_tb = sys.exc_info()
        limit = None
        try:
            try:
                import html

                ecb.SendResponseHeaders(
                    "200 OK", "Content-type: text/html\r\n\r\n", False
                )
                print(file=ecb)
                print("<H3>Traceback (most recent call last):</H3>", file=ecb)
                list = traceback.format_tb(
                    exc_tb, limit
                ) + traceback.format_exception_only(exc_typ, exc_val)
                bold = list.pop()
                print(
                    "<PRE>{}<B>{}</B></PRE>".format(
                        html.escape("".join(list)),
                        html.escape(bold),
                    ),
                    file=ecb,
                )
            except ExtensionError:
                # The client disconnected without reading the error body -
                # it's probably not a real browser at the other end, ignore it.
                pass
            except:
                print("FAILED to render the error message!")
                traceback.print_exc()
                print("ORIGINAL extension error:")
                traceback.print_exception(exc_typ, exc_val, exc_tb)
        finally:
            # holding tracebacks in a local of a frame that may itself be
            # part of a traceback used to be evil and cause leaks!
            exc_tb = None
            ecb.DoneWithSession()

# === NexusCore/openenv\Lib\site-packages\jinja2\debug.py ===
import sys
import typing as t
from types import CodeType
from types import TracebackType

from .exceptions import TemplateSyntaxError
from .utils import internal_code
from .utils import missing

if t.TYPE_CHECKING:
    from .runtime import Context


def rewrite_traceback_stack(source: t.Optional[str] = None) -> BaseException:
    """Rewrite the current exception to replace any tracebacks from
    within compiled template code with tracebacks that look like they
    came from the template source.

    This must be called within an ``except`` block.

    :param source: For ``TemplateSyntaxError``, the original source if
        known.
    :return: The original exception with the rewritten traceback.
    """
    _, exc_value, tb = sys.exc_info()
    exc_value = t.cast(BaseException, exc_value)
    tb = t.cast(TracebackType, tb)

    if isinstance(exc_value, TemplateSyntaxError) and not exc_value.translated:
        exc_value.translated = True
        exc_value.source = source
        # Remove the old traceback, otherwise the frames from the
        # compiler still show up.
        exc_value.with_traceback(None)
        # Outside of runtime, so the frame isn't executing template
        # code, but it still needs to point at the template.
        tb = fake_traceback(
            exc_value, None, exc_value.filename or "<unknown>", exc_value.lineno
        )
    else:
        # Skip the frame for the render function.
        tb = tb.tb_next

    stack = []

    # Build the stack of traceback object, replacing any in template
    # code with the source file and line information.
    while tb is not None:
        # Skip frames decorated with @internalcode. These are internal
        # calls that aren't useful in template debugging output.
        if tb.tb_frame.f_code in internal_code:
            tb = tb.tb_next
            continue

        template = tb.tb_frame.f_globals.get("__jinja_template__")

        if template is not None:
            lineno = template.get_corresponding_lineno(tb.tb_lineno)
            fake_tb = fake_traceback(exc_value, tb, template.filename, lineno)
            stack.append(fake_tb)
        else:
            stack.append(tb)

        tb = tb.tb_next

    tb_next = None

    # Assign tb_next in reverse to avoid circular references.
    for tb in reversed(stack):
        tb.tb_next = tb_next
        tb_next = tb

    return exc_value.with_traceback(tb_next)


def fake_traceback(  # type: ignore
    exc_value: BaseException, tb: t.Optional[TracebackType], filename: str, lineno: int
) -> TracebackType:
    """Produce a new traceback object that looks like it came from the
    template source instead of the compiled code. The filename, line
    number, and location name will point to the template, and the local
    variables will be the current template context.

    :param exc_value: The original exception to be re-raised to create
        the new traceback.
    :param tb: The original traceback to get the local variables and
        code info from.
    :param filename: The template filename.
    :param lineno: The line number in the template source.
    """
    if tb is not None:
        # Replace the real locals with the context that would be
        # available at that point in the template.
        locals = get_template_locals(tb.tb_frame.f_locals)
        locals.pop("__jinja_exception__", None)
    else:
        locals = {}

    globals = {
        "__name__": filename,
        "__file__": filename,
        "__jinja_exception__": exc_value,
    }
    # Raise an exception at the correct line number.
    code: CodeType = compile(
        "\n" * (lineno - 1) + "raise __jinja_exception__", filename, "exec"
    )

    # Build a new code object that points to the template file and
    # replaces the location with a block name.
    location = "template"

    if tb is not None:
        function = tb.tb_frame.f_code.co_name

        if function == "root":
            location = "top-level template code"
        elif function.startswith("block_"):
            location = f"block {function[6:]!r}"

    if sys.version_info >= (3, 8):
        code = code.replace(co_name=location)
    else:
        code = CodeType(
            code.co_argcount,
            code.co_kwonlyargcount,
            code.co_nlocals,
            code.co_stacksize,
            code.co_flags,
            code.co_code,
            code.co_consts,
            code.co_names,
            code.co_varnames,
            code.co_filename,
            location,
            code.co_firstlineno,
            code.co_lnotab,
            code.co_freevars,
            code.co_cellvars,
        )

    # Execute the new code, which is guaranteed to raise, and return
    # the new traceback without this frame.
    try:
        exec(code, globals, locals)
    except BaseException:
        return sys.exc_info()[2].tb_next  # type: ignore


def get_template_locals(real_locals: t.Mapping[str, t.Any]) -> t.Dict[str, t.Any]:
    """Based on the runtime locals, get the context that would be
    available at that point in the template.
    """
    # Start with the current template context.
    ctx: t.Optional[Context] = real_locals.get("context")

    if ctx is not None:
        data: t.Dict[str, t.Any] = ctx.get_all().copy()
    else:
        data = {}

    # Might be in a derived context that only sets local variables
    # rather than pushing a context. Local variables follow the scheme
    # l_depth_name. Find the highest-depth local that has a value for
    # each name.
    local_overrides: t.Dict[str, t.Tuple[int, t.Any]] = {}

    for name, value in real_locals.items():
        if not name.startswith("l_") or value is missing:
            # Not a template variable, or no longer relevant.
            continue

        try:
            _, depth_str, name = name.split("_", 2)
            depth = int(depth_str)
        except ValueError:
            continue

        cur_depth = local_overrides.get(name, (-1,))[0]

        if cur_depth < depth:
            local_overrides[name] = (depth, value)

    # Modify the context with any derived context.
    for name, (_, value) in local_overrides.items():
        if value is missing:
            data.pop(name, None)
        else:
            data[name] = value

    return data

# === NexusCore/openenv\Lib\site-packages\rich\default_styles.py ===
from typing import Dict

from .style import Style

DEFAULT_STYLES: Dict[str, Style] = {
    "none": Style.null(),
    "reset": Style(
        color="default",
        bgcolor="default",
        dim=False,
        bold=False,
        italic=False,
        underline=False,
        blink=False,
        blink2=False,
        reverse=False,
        conceal=False,
        strike=False,
    ),
    "dim": Style(dim=True),
    "bright": Style(dim=False),
    "bold": Style(bold=True),
    "strong": Style(bold=True),
    "code": Style(reverse=True, bold=True),
    "italic": Style(italic=True),
    "emphasize": Style(italic=True),
    "underline": Style(underline=True),
    "blink": Style(blink=True),
    "blink2": Style(blink2=True),
    "reverse": Style(reverse=True),
    "strike": Style(strike=True),
    "black": Style(color="black"),
    "red": Style(color="red"),
    "green": Style(color="green"),
    "yellow": Style(color="yellow"),
    "magenta": Style(color="magenta"),
    "cyan": Style(color="cyan"),
    "white": Style(color="white"),
    "inspect.attr": Style(color="yellow", italic=True),
    "inspect.attr.dunder": Style(color="yellow", italic=True, dim=True),
    "inspect.callable": Style(bold=True, color="red"),
    "inspect.async_def": Style(italic=True, color="bright_cyan"),
    "inspect.def": Style(italic=True, color="bright_cyan"),
    "inspect.class": Style(italic=True, color="bright_cyan"),
    "inspect.error": Style(bold=True, color="red"),
    "inspect.equals": Style(),
    "inspect.help": Style(color="cyan"),
    "inspect.doc": Style(dim=True),
    "inspect.value.border": Style(color="green"),
    "live.ellipsis": Style(bold=True, color="red"),
    "layout.tree.row": Style(dim=False, color="red"),
    "layout.tree.column": Style(dim=False, color="blue"),
    "logging.keyword": Style(bold=True, color="yellow"),
    "logging.level.notset": Style(dim=True),
    "logging.level.debug": Style(color="green"),
    "logging.level.info": Style(color="blue"),
    "logging.level.warning": Style(color="yellow"),
    "logging.level.error": Style(color="red", bold=True),
    "logging.level.critical": Style(color="red", bold=True, reverse=True),
    "log.level": Style.null(),
    "log.time": Style(color="cyan", dim=True),
    "log.message": Style.null(),
    "log.path": Style(dim=True),
    "repr.ellipsis": Style(color="yellow"),
    "repr.indent": Style(color="green", dim=True),
    "repr.error": Style(color="red", bold=True),
    "repr.str": Style(color="green", italic=False, bold=False),
    "repr.brace": Style(bold=True),
    "repr.comma": Style(bold=True),
    "repr.ipv4": Style(bold=True, color="bright_green"),
    "repr.ipv6": Style(bold=True, color="bright_green"),
    "repr.eui48": Style(bold=True, color="bright_green"),
    "repr.eui64": Style(bold=True, color="bright_green"),
    "repr.tag_start": Style(bold=True),
    "repr.tag_name": Style(color="bright_magenta", bold=True),
    "repr.tag_contents": Style(color="default"),
    "repr.tag_end": Style(bold=True),
    "repr.attrib_name": Style(color="yellow", italic=False),
    "repr.attrib_equal": Style(bold=True),
    "repr.attrib_value": Style(color="magenta", italic=False),
    "repr.number": Style(color="cyan", bold=True, italic=False),
    "repr.number_complex": Style(color="cyan", bold=True, italic=False),  # same
    "repr.bool_true": Style(color="bright_green", italic=True),
    "repr.bool_false": Style(color="bright_red", italic=True),
    "repr.none": Style(color="magenta", italic=True),
    "repr.url": Style(underline=True, color="bright_blue", italic=False, bold=False),
    "repr.uuid": Style(color="bright_yellow", bold=False),
    "repr.call": Style(color="magenta", bold=True),
    "repr.path": Style(color="magenta"),
    "repr.filename": Style(color="bright_magenta"),
    "rule.line": Style(color="bright_green"),
    "rule.text": Style.null(),
    "json.brace": Style(bold=True),
    "json.bool_true": Style(color="bright_green", italic=True),
    "json.bool_false": Style(color="bright_red", italic=True),
    "json.null": Style(color="magenta", italic=True),
    "json.number": Style(color="cyan", bold=True, italic=False),
    "json.str": Style(color="green", italic=False, bold=False),
    "json.key": Style(color="blue", bold=True),
    "prompt": Style.null(),
    "prompt.choices": Style(color="magenta", bold=True),
    "prompt.default": Style(color="cyan", bold=True),
    "prompt.invalid": Style(color="red"),
    "prompt.invalid.choice": Style(color="red"),
    "pretty": Style.null(),
    "scope.border": Style(color="blue"),
    "scope.key": Style(color="yellow", italic=True),
    "scope.key.special": Style(color="yellow", italic=True, dim=True),
    "scope.equals": Style(color="red"),
    "table.header": Style(bold=True),
    "table.footer": Style(bold=True),
    "table.cell": Style.null(),
    "table.title": Style(italic=True),
    "table.caption": Style(italic=True, dim=True),
    "traceback.error": Style(color="red", italic=True),
    "traceback.border.syntax_error": Style(color="bright_red"),
    "traceback.border": Style(color="red"),
    "traceback.text": Style.null(),
    "traceback.title": Style(color="red", bold=True),
    "traceback.exc_type": Style(color="bright_red", bold=True),
    "traceback.exc_value": Style.null(),
    "traceback.offset": Style(color="bright_red", bold=True),
    "traceback.error_range": Style(underline=True, bold=True, dim=False),
    "bar.back": Style(color="grey23"),
    "bar.complete": Style(color="rgb(249,38,114)"),
    "bar.finished": Style(color="rgb(114,156,31)"),
    "bar.pulse": Style(color="rgb(249,38,114)"),
    "progress.description": Style.null(),
    "progress.filesize": Style(color="green"),
    "progress.filesize.total": Style(color="green"),
    "progress.download": Style(color="green"),
    "progress.elapsed": Style(color="yellow"),
    "progress.percentage": Style(color="magenta"),
    "progress.remaining": Style(color="cyan"),
    "progress.data.speed": Style(color="red"),
    "progress.spinner": Style(color="green"),
    "status.spinner": Style(color="green"),
    "tree": Style(),
    "tree.line": Style(),
    "markdown.paragraph": Style(),
    "markdown.text": Style(),
    "markdown.em": Style(italic=True),
    "markdown.emph": Style(italic=True),  # For commonmark backwards compatibility
    "markdown.strong": Style(bold=True),
    "markdown.code": Style(bold=True, color="cyan", bgcolor="black"),
    "markdown.code_block": Style(color="cyan", bgcolor="black"),
    "markdown.block_quote": Style(color="magenta"),
    "markdown.list": Style(color="cyan"),
    "markdown.item": Style(),
    "markdown.item.bullet": Style(color="yellow", bold=True),
    "markdown.item.number": Style(color="yellow", bold=True),
    "markdown.hr": Style(color="yellow"),
    "markdown.h1.border": Style(),
    "markdown.h1": Style(bold=True),
    "markdown.h2": Style(bold=True, underline=True),
    "markdown.h3": Style(bold=True),
    "markdown.h4": Style(bold=True, dim=True),
    "markdown.h5": Style(underline=True),
    "markdown.h6": Style(italic=True),
    "markdown.h7": Style(italic=True, dim=True),
    "markdown.link": Style(color="bright_blue"),
    "markdown.link_url": Style(color="blue", underline=True),
    "markdown.s": Style(strike=True),
    "iso8601.date": Style(color="blue"),
    "iso8601.time": Style(color="magenta"),
    "iso8601.timezone": Style(color="yellow"),
}


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import io

    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    parser = argparse.ArgumentParser()
    parser.add_argument("--html", action="store_true", help="Export as HTML table")
    args = parser.parse_args()
    html: bool = args.html
    console = Console(record=True, width=70, file=io.StringIO()) if html else Console()

    table = Table("Name", "Styling")

    for style_name, style in DEFAULT_STYLES.items():
        table.add_row(Text(style_name, style=style), str(style))

    console.print(table)
    if html:
        print(console.export_html(inline_styles=True))

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_a_v_a_r.py ===
from fontTools.misc import sstruct
from fontTools.misc.fixedTools import (
    fixedToFloat as fi2fl,
    floatToFixed as fl2fi,
    floatToFixedToStr as fl2str,
    strToFixedToFloat as str2fl,
)
from fontTools.misc.textTools import bytesjoin, safeEval
from fontTools.misc.roundTools import otRound
from fontTools.varLib.models import piecewiseLinearMap
from fontTools.varLib.varStore import VarStoreInstancer, NO_VARIATION_INDEX
from fontTools.ttLib import TTLibError
from . import DefaultTable
from . import otTables
import struct
import logging


log = logging.getLogger(__name__)

from .otBase import BaseTTXConverter


class table__a_v_a_r(BaseTTXConverter):
    """Axis Variations table

    This class represents the ``avar`` table of a variable font. The object has one
    substantive attribute, ``segments``, which maps axis tags to a segments dictionary::

        >>> font["avar"].segments   # doctest: +SKIP
        {'wght': {-1.0: -1.0,
          0.0: 0.0,
          0.125: 0.11444091796875,
          0.25: 0.23492431640625,
          0.5: 0.35540771484375,
          0.625: 0.5,
          0.75: 0.6566162109375,
          0.875: 0.81927490234375,
          1.0: 1.0},
         'ital': {-1.0: -1.0, 0.0: 0.0, 1.0: 1.0}}

    Notice that the segments dictionary is made up of normalized values. A valid
    ``avar`` segment mapping must contain the entries ``-1.0: -1.0, 0.0: 0.0, 1.0: 1.0``.
    fontTools does not enforce this, so it is your responsibility to ensure that
    mappings are valid.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/avar
    """

    dependencies = ["fvar"]

    def __init__(self, tag=None):
        super().__init__(tag)
        self.segments = {}

    def compile(self, ttFont):
        axisTags = [axis.axisTag for axis in ttFont["fvar"].axes]
        if not hasattr(self, "table"):
            self.table = otTables.avar()
        if not hasattr(self.table, "Reserved"):
            self.table.Reserved = 0
        self.table.Version = (getattr(self, "majorVersion", 1) << 16) | getattr(
            self, "minorVersion", 0
        )
        self.table.AxisCount = len(axisTags)
        self.table.AxisSegmentMap = []
        for axis in axisTags:
            mappings = self.segments[axis]
            segmentMap = otTables.AxisSegmentMap()
            segmentMap.PositionMapCount = len(mappings)
            segmentMap.AxisValueMap = []
            for key, value in sorted(mappings.items()):
                valueMap = otTables.AxisValueMap()
                valueMap.FromCoordinate = key
                valueMap.ToCoordinate = value
                segmentMap.AxisValueMap.append(valueMap)
            self.table.AxisSegmentMap.append(segmentMap)
        return super().compile(ttFont)

    def decompile(self, data, ttFont):
        super().decompile(data, ttFont)
        self.majorVersion = self.table.Version >> 16
        self.minorVersion = self.table.Version & 0xFFFF
        if self.majorVersion not in (1, 2):
            raise NotImplementedError("Unknown avar table version")
        axisTags = [axis.axisTag for axis in ttFont["fvar"].axes]
        for axis in axisTags:
            self.segments[axis] = {}
        for axis, segmentMap in zip(axisTags, self.table.AxisSegmentMap):
            segments = self.segments[axis] = {}
            for segment in segmentMap.AxisValueMap:
                segments[segment.FromCoordinate] = segment.ToCoordinate

    def toXML(self, writer, ttFont):
        writer.simpletag(
            "version",
            major=getattr(self, "majorVersion", 1),
            minor=getattr(self, "minorVersion", 0),
        )
        writer.newline()
        axisTags = [axis.axisTag for axis in ttFont["fvar"].axes]
        for axis in axisTags:
            writer.begintag("segment", axis=axis)
            writer.newline()
            for key, value in sorted(self.segments[axis].items()):
                key = fl2str(key, 14)
                value = fl2str(value, 14)
                writer.simpletag("mapping", **{"from": key, "to": value})
                writer.newline()
            writer.endtag("segment")
            writer.newline()
        if getattr(self, "majorVersion", 1) >= 2:
            if self.table.VarIdxMap:
                self.table.VarIdxMap.toXML(writer, ttFont, name="VarIdxMap")
            if self.table.VarStore:
                self.table.VarStore.toXML(writer, ttFont)

    def fromXML(self, name, attrs, content, ttFont):
        if not hasattr(self, "table"):
            self.table = otTables.avar()
        if not hasattr(self.table, "Reserved"):
            self.table.Reserved = 0
        if name == "version":
            self.majorVersion = safeEval(attrs["major"])
            self.minorVersion = safeEval(attrs["minor"])
            self.table.Version = (getattr(self, "majorVersion", 1) << 16) | getattr(
                self, "minorVersion", 0
            )
        elif name == "segment":
            axis = attrs["axis"]
            segment = self.segments[axis] = {}
            for element in content:
                if isinstance(element, tuple):
                    elementName, elementAttrs, _ = element
                    if elementName == "mapping":
                        fromValue = str2fl(elementAttrs["from"], 14)
                        toValue = str2fl(elementAttrs["to"], 14)
                        if fromValue in segment:
                            log.warning(
                                "duplicate entry for %s in axis '%s'", fromValue, axis
                            )
                        segment[fromValue] = toValue
        else:
            super().fromXML(name, attrs, content, ttFont)

    def renormalizeLocation(self, location, font):

        majorVersion = getattr(self, "majorVersion", 1)

        if majorVersion not in (1, 2):
            raise NotImplementedError("Unknown avar table version")

        avarSegments = self.segments
        mappedLocation = {}
        for axisTag, value in location.items():
            avarMapping = avarSegments.get(axisTag, None)
            if avarMapping is not None:
                value = piecewiseLinearMap(value, avarMapping)
            mappedLocation[axisTag] = value

        if majorVersion < 2:
            return mappedLocation

        # Version 2

        varIdxMap = self.table.VarIdxMap
        varStore = self.table.VarStore
        axes = font["fvar"].axes
        if varStore is not None:
            instancer = VarStoreInstancer(varStore, axes, mappedLocation)

        coords = list(fl2fi(mappedLocation.get(axis.axisTag, 0), 14) for axis in axes)

        out = []
        for varIdx, v in enumerate(coords):

            if varIdxMap is not None:
                varIdx = varIdxMap[varIdx]

            if varStore is not None:
                delta = instancer[varIdx]
                v += otRound(delta)
                v = min(max(v, -(1 << 14)), +(1 << 14))

            out.append(v)

        mappedLocation = {
            axis.axisTag: fi2fl(v, 14) for v, axis in zip(out, axes) if v != 0
        }

        return mappedLocation

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_generated\types\__init__.py ===
# This file is auto-generated by `utils/generate_inference_types.py`.
# Do not modify it manually.
#
# ruff: noqa: F401

from .audio_classification import (
    AudioClassificationInput,
    AudioClassificationOutputElement,
    AudioClassificationOutputTransform,
    AudioClassificationParameters,
)
from .audio_to_audio import AudioToAudioInput, AudioToAudioOutputElement
from .automatic_speech_recognition import (
    AutomaticSpeechRecognitionEarlyStoppingEnum,
    AutomaticSpeechRecognitionGenerationParameters,
    AutomaticSpeechRecognitionInput,
    AutomaticSpeechRecognitionOutput,
    AutomaticSpeechRecognitionOutputChunk,
    AutomaticSpeechRecognitionParameters,
)
from .base import BaseInferenceType
from .chat_completion import (
    ChatCompletionInput,
    ChatCompletionInputFunctionDefinition,
    ChatCompletionInputFunctionName,
    ChatCompletionInputGrammarType,
    ChatCompletionInputJSONSchema,
    ChatCompletionInputMessage,
    ChatCompletionInputMessageChunk,
    ChatCompletionInputMessageChunkType,
    ChatCompletionInputResponseFormatJSONObject,
    ChatCompletionInputResponseFormatJSONSchema,
    ChatCompletionInputResponseFormatText,
    ChatCompletionInputStreamOptions,
    ChatCompletionInputTool,
    ChatCompletionInputToolCall,
    ChatCompletionInputToolChoiceClass,
    ChatCompletionInputToolChoiceEnum,
    ChatCompletionInputURL,
    ChatCompletionOutput,
    ChatCompletionOutputComplete,
    ChatCompletionOutputFunctionDefinition,
    ChatCompletionOutputLogprob,
    ChatCompletionOutputLogprobs,
    ChatCompletionOutputMessage,
    ChatCompletionOutputToolCall,
    ChatCompletionOutputTopLogprob,
    ChatCompletionOutputUsage,
    ChatCompletionStreamOutput,
    ChatCompletionStreamOutputChoice,
    ChatCompletionStreamOutputDelta,
    ChatCompletionStreamOutputDeltaToolCall,
    ChatCompletionStreamOutputFunction,
    ChatCompletionStreamOutputLogprob,
    ChatCompletionStreamOutputLogprobs,
    ChatCompletionStreamOutputTopLogprob,
    ChatCompletionStreamOutputUsage,
)
from .depth_estimation import DepthEstimationInput, DepthEstimationOutput
from .document_question_answering import (
    DocumentQuestionAnsweringInput,
    DocumentQuestionAnsweringInputData,
    DocumentQuestionAnsweringOutputElement,
    DocumentQuestionAnsweringParameters,
)
from .feature_extraction import FeatureExtractionInput, FeatureExtractionInputTruncationDirection
from .fill_mask import FillMaskInput, FillMaskOutputElement, FillMaskParameters
from .image_classification import (
    ImageClassificationInput,
    ImageClassificationOutputElement,
    ImageClassificationOutputTransform,
    ImageClassificationParameters,
)
from .image_segmentation import (
    ImageSegmentationInput,
    ImageSegmentationOutputElement,
    ImageSegmentationParameters,
    ImageSegmentationSubtask,
)
from .image_to_image import ImageToImageInput, ImageToImageOutput, ImageToImageParameters, ImageToImageTargetSize
from .image_to_text import (
    ImageToTextEarlyStoppingEnum,
    ImageToTextGenerationParameters,
    ImageToTextInput,
    ImageToTextOutput,
    ImageToTextParameters,
)
from .object_detection import (
    ObjectDetectionBoundingBox,
    ObjectDetectionInput,
    ObjectDetectionOutputElement,
    ObjectDetectionParameters,
)
from .question_answering import (
    QuestionAnsweringInput,
    QuestionAnsweringInputData,
    QuestionAnsweringOutputElement,
    QuestionAnsweringParameters,
)
from .sentence_similarity import SentenceSimilarityInput, SentenceSimilarityInputData
from .summarization import (
    SummarizationInput,
    SummarizationOutput,
    SummarizationParameters,
    SummarizationTruncationStrategy,
)
from .table_question_answering import (
    Padding,
    TableQuestionAnsweringInput,
    TableQuestionAnsweringInputData,
    TableQuestionAnsweringOutputElement,
    TableQuestionAnsweringParameters,
)
from .text2text_generation import (
    Text2TextGenerationInput,
    Text2TextGenerationOutput,
    Text2TextGenerationParameters,
    Text2TextGenerationTruncationStrategy,
)
from .text_classification import (
    TextClassificationInput,
    TextClassificationOutputElement,
    TextClassificationOutputTransform,
    TextClassificationParameters,
)
from .text_generation import (
    TextGenerationInput,
    TextGenerationInputGenerateParameters,
    TextGenerationInputGrammarType,
    TextGenerationOutput,
    TextGenerationOutputBestOfSequence,
    TextGenerationOutputDetails,
    TextGenerationOutputFinishReason,
    TextGenerationOutputPrefillToken,
    TextGenerationOutputToken,
    TextGenerationStreamOutput,
    TextGenerationStreamOutputStreamDetails,
    TextGenerationStreamOutputToken,
    TypeEnum,
)
from .text_to_audio import (
    TextToAudioEarlyStoppingEnum,
    TextToAudioGenerationParameters,
    TextToAudioInput,
    TextToAudioOutput,
    TextToAudioParameters,
)
from .text_to_image import TextToImageInput, TextToImageOutput, TextToImageParameters
from .text_to_speech import (
    TextToSpeechEarlyStoppingEnum,
    TextToSpeechGenerationParameters,
    TextToSpeechInput,
    TextToSpeechOutput,
    TextToSpeechParameters,
)
from .text_to_video import TextToVideoInput, TextToVideoOutput, TextToVideoParameters
from .token_classification import (
    TokenClassificationAggregationStrategy,
    TokenClassificationInput,
    TokenClassificationOutputElement,
    TokenClassificationParameters,
)
from .translation import TranslationInput, TranslationOutput, TranslationParameters, TranslationTruncationStrategy
from .video_classification import (
    VideoClassificationInput,
    VideoClassificationOutputElement,
    VideoClassificationOutputTransform,
    VideoClassificationParameters,
)
from .visual_question_answering import (
    VisualQuestionAnsweringInput,
    VisualQuestionAnsweringInputData,
    VisualQuestionAnsweringOutputElement,
    VisualQuestionAnsweringParameters,
)
from .zero_shot_classification import (
    ZeroShotClassificationInput,
    ZeroShotClassificationOutputElement,
    ZeroShotClassificationParameters,
)
from .zero_shot_image_classification import (
    ZeroShotImageClassificationInput,
    ZeroShotImageClassificationOutputElement,
    ZeroShotImageClassificationParameters,
)
from .zero_shot_object_detection import (
    ZeroShotObjectDetectionBoundingBox,
    ZeroShotObjectDetectionInput,
    ZeroShotObjectDetectionOutputElement,
    ZeroShotObjectDetectionParameters,
)

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\helicone.py ===
#### What this does ####
#    On success, logs events to Helicone
import os
import traceback

import litellm


class HeliconeLogger:
    # Class variables or attributes
    helicone_model_list = [
        "gpt",
        "claude",
        "command-r",
        "command-r-plus",
        "command-light",
        "command-medium",
        "command-medium-beta",
        "command-xlarge-nightly",
        "command-nightly",
    ]

    def __init__(self):
        # Instance variables
        self.provider_url = "https://api.openai.com/v1"
        self.key = os.getenv("HELICONE_API_KEY")
        self.api_base = os.getenv("HELICONE_API_BASE") or "https://api.hconeai.com"
        if self.api_base.endswith("/"):
            self.api_base = self.api_base[:-1]

    def claude_mapping(self, model, messages, response_obj):
        from anthropic import AI_PROMPT, HUMAN_PROMPT

        prompt = f"{HUMAN_PROMPT}"
        for message in messages:
            if "role" in message:
                if message["role"] == "user":
                    prompt += f"{HUMAN_PROMPT}{message['content']}"
                else:
                    prompt += f"{AI_PROMPT}{message['content']}"
            else:
                prompt += f"{HUMAN_PROMPT}{message['content']}"
        prompt += f"{AI_PROMPT}"

        choice = response_obj["choices"][0]
        message = choice["message"]

        content = []
        if "tool_calls" in message and message["tool_calls"]:
            for tool_call in message["tool_calls"]:
                content.append(
                    {
                        "type": "tool_use",
                        "id": tool_call["id"],
                        "name": tool_call["function"]["name"],
                        "input": tool_call["function"]["arguments"],
                    }
                )
        elif "content" in message and message["content"]:
            content = [{"type": "text", "text": message["content"]}]

        claude_response_obj = {
            "id": response_obj["id"],
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": content,
            "stop_reason": choice["finish_reason"],
            "stop_sequence": None,
            "usage": {
                "input_tokens": response_obj["usage"]["prompt_tokens"],
                "output_tokens": response_obj["usage"]["completion_tokens"],
            },
        }

        return claude_response_obj

    @staticmethod
    def add_metadata_from_header(litellm_params: dict, metadata: dict) -> dict:
        """
        Adds metadata from proxy request headers to Helicone logging if keys start with "helicone_"
        and overwrites litellm_params.metadata if already included.

        For example if you want to add custom property to your request, send
        `headers: { ..., helicone-property-something: 1234 }` via proxy request.
        """
        if litellm_params is None:
            return metadata

        if litellm_params.get("proxy_server_request") is None:
            return metadata

        if metadata is None:
            metadata = {}

        proxy_headers = (
            litellm_params.get("proxy_server_request", {}).get("headers", {}) or {}
        )

        for header_key in proxy_headers:
            if header_key.startswith("helicone_"):
                metadata[header_key] = proxy_headers.get(header_key)

        return metadata

    def log_success(
        self, model, messages, response_obj, start_time, end_time, print_verbose, kwargs
    ):
        # Method definition
        try:
            print_verbose(
                f"Helicone Logging - Enters logging function for model {model}"
            )
            litellm_params = kwargs.get("litellm_params", {})
            kwargs.get("litellm_call_id", None)
            metadata = litellm_params.get("metadata", {}) or {}
            metadata = self.add_metadata_from_header(litellm_params, metadata)
            model = (
                model
                if any(
                    accepted_model in model
                    for accepted_model in self.helicone_model_list
                )
                else "gpt-3.5-turbo"
            )
            provider_request = {"model": model, "messages": messages}
            if isinstance(response_obj, litellm.EmbeddingResponse) or isinstance(
                response_obj, litellm.ModelResponse
            ):
                response_obj = response_obj.json()

            if "claude" in model:
                response_obj = self.claude_mapping(
                    model=model, messages=messages, response_obj=response_obj
                )

            providerResponse = {
                "json": response_obj,
                "headers": {"openai-version": "2020-10-01"},
                "status": 200,
            }

            # Code to be executed
            provider_url = self.provider_url
            url = f"{self.api_base}/oai/v1/log"
            if "claude" in model:
                url = f"{self.api_base}/anthropic/v1/log"
                provider_url = "https://api.anthropic.com/v1/messages"
            headers = {
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
            }
            start_time_seconds = int(start_time.timestamp())
            start_time_milliseconds = int(
                (start_time.timestamp() - start_time_seconds) * 1000
            )
            end_time_seconds = int(end_time.timestamp())
            end_time_milliseconds = int(
                (end_time.timestamp() - end_time_seconds) * 1000
            )
            meta = {"Helicone-Auth": f"Bearer {self.key}"}
            meta.update(metadata)
            data = {
                "providerRequest": {
                    "url": provider_url,
                    "json": provider_request,
                    "meta": meta,
                },
                "providerResponse": providerResponse,
                "timing": {
                    "startTime": {
                        "seconds": start_time_seconds,
                        "milliseconds": start_time_milliseconds,
                    },
                    "endTime": {
                        "seconds": end_time_seconds,
                        "milliseconds": end_time_milliseconds,
                    },
                },  # {"seconds": .., "milliseconds": ..}
            }
            response = litellm.module_level_client.post(url, headers=headers, json=data)
            if response.status_code == 200:
                print_verbose("Helicone Logging - Success!")
            else:
                print_verbose(
                    f"Helicone Logging - Error Request was not successful. Status Code: {response.status_code}"
                )
                print_verbose(f"Helicone Logging - Error {response.text}")
        except Exception:
            print_verbose(f"Helicone Logging Error - {traceback.format_exc()}")
            pass

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\default_styles.py ===
from typing import Dict

from .style import Style

DEFAULT_STYLES: Dict[str, Style] = {
    "none": Style.null(),
    "reset": Style(
        color="default",
        bgcolor="default",
        dim=False,
        bold=False,
        italic=False,
        underline=False,
        blink=False,
        blink2=False,
        reverse=False,
        conceal=False,
        strike=False,
    ),
    "dim": Style(dim=True),
    "bright": Style(dim=False),
    "bold": Style(bold=True),
    "strong": Style(bold=True),
    "code": Style(reverse=True, bold=True),
    "italic": Style(italic=True),
    "emphasize": Style(italic=True),
    "underline": Style(underline=True),
    "blink": Style(blink=True),
    "blink2": Style(blink2=True),
    "reverse": Style(reverse=True),
    "strike": Style(strike=True),
    "black": Style(color="black"),
    "red": Style(color="red"),
    "green": Style(color="green"),
    "yellow": Style(color="yellow"),
    "magenta": Style(color="magenta"),
    "cyan": Style(color="cyan"),
    "white": Style(color="white"),
    "inspect.attr": Style(color="yellow", italic=True),
    "inspect.attr.dunder": Style(color="yellow", italic=True, dim=True),
    "inspect.callable": Style(bold=True, color="red"),
    "inspect.async_def": Style(italic=True, color="bright_cyan"),
    "inspect.def": Style(italic=True, color="bright_cyan"),
    "inspect.class": Style(italic=True, color="bright_cyan"),
    "inspect.error": Style(bold=True, color="red"),
    "inspect.equals": Style(),
    "inspect.help": Style(color="cyan"),
    "inspect.doc": Style(dim=True),
    "inspect.value.border": Style(color="green"),
    "live.ellipsis": Style(bold=True, color="red"),
    "layout.tree.row": Style(dim=False, color="red"),
    "layout.tree.column": Style(dim=False, color="blue"),
    "logging.keyword": Style(bold=True, color="yellow"),
    "logging.level.notset": Style(dim=True),
    "logging.level.debug": Style(color="green"),
    "logging.level.info": Style(color="blue"),
    "logging.level.warning": Style(color="yellow"),
    "logging.level.error": Style(color="red", bold=True),
    "logging.level.critical": Style(color="red", bold=True, reverse=True),
    "log.level": Style.null(),
    "log.time": Style(color="cyan", dim=True),
    "log.message": Style.null(),
    "log.path": Style(dim=True),
    "repr.ellipsis": Style(color="yellow"),
    "repr.indent": Style(color="green", dim=True),
    "repr.error": Style(color="red", bold=True),
    "repr.str": Style(color="green", italic=False, bold=False),
    "repr.brace": Style(bold=True),
    "repr.comma": Style(bold=True),
    "repr.ipv4": Style(bold=True, color="bright_green"),
    "repr.ipv6": Style(bold=True, color="bright_green"),
    "repr.eui48": Style(bold=True, color="bright_green"),
    "repr.eui64": Style(bold=True, color="bright_green"),
    "repr.tag_start": Style(bold=True),
    "repr.tag_name": Style(color="bright_magenta", bold=True),
    "repr.tag_contents": Style(color="default"),
    "repr.tag_end": Style(bold=True),
    "repr.attrib_name": Style(color="yellow", italic=False),
    "repr.attrib_equal": Style(bold=True),
    "repr.attrib_value": Style(color="magenta", italic=False),
    "repr.number": Style(color="cyan", bold=True, italic=False),
    "repr.number_complex": Style(color="cyan", bold=True, italic=False),  # same
    "repr.bool_true": Style(color="bright_green", italic=True),
    "repr.bool_false": Style(color="bright_red", italic=True),
    "repr.none": Style(color="magenta", italic=True),
    "repr.url": Style(underline=True, color="bright_blue", italic=False, bold=False),
    "repr.uuid": Style(color="bright_yellow", bold=False),
    "repr.call": Style(color="magenta", bold=True),
    "repr.path": Style(color="magenta"),
    "repr.filename": Style(color="bright_magenta"),
    "rule.line": Style(color="bright_green"),
    "rule.text": Style.null(),
    "json.brace": Style(bold=True),
    "json.bool_true": Style(color="bright_green", italic=True),
    "json.bool_false": Style(color="bright_red", italic=True),
    "json.null": Style(color="magenta", italic=True),
    "json.number": Style(color="cyan", bold=True, italic=False),
    "json.str": Style(color="green", italic=False, bold=False),
    "json.key": Style(color="blue", bold=True),
    "prompt": Style.null(),
    "prompt.choices": Style(color="magenta", bold=True),
    "prompt.default": Style(color="cyan", bold=True),
    "prompt.invalid": Style(color="red"),
    "prompt.invalid.choice": Style(color="red"),
    "pretty": Style.null(),
    "scope.border": Style(color="blue"),
    "scope.key": Style(color="yellow", italic=True),
    "scope.key.special": Style(color="yellow", italic=True, dim=True),
    "scope.equals": Style(color="red"),
    "table.header": Style(bold=True),
    "table.footer": Style(bold=True),
    "table.cell": Style.null(),
    "table.title": Style(italic=True),
    "table.caption": Style(italic=True, dim=True),
    "traceback.error": Style(color="red", italic=True),
    "traceback.border.syntax_error": Style(color="bright_red"),
    "traceback.border": Style(color="red"),
    "traceback.text": Style.null(),
    "traceback.title": Style(color="red", bold=True),
    "traceback.exc_type": Style(color="bright_red", bold=True),
    "traceback.exc_value": Style.null(),
    "traceback.offset": Style(color="bright_red", bold=True),
    "traceback.error_range": Style(underline=True, bold=True, dim=False),
    "bar.back": Style(color="grey23"),
    "bar.complete": Style(color="rgb(249,38,114)"),
    "bar.finished": Style(color="rgb(114,156,31)"),
    "bar.pulse": Style(color="rgb(249,38,114)"),
    "progress.description": Style.null(),
    "progress.filesize": Style(color="green"),
    "progress.filesize.total": Style(color="green"),
    "progress.download": Style(color="green"),
    "progress.elapsed": Style(color="yellow"),
    "progress.percentage": Style(color="magenta"),
    "progress.remaining": Style(color="cyan"),
    "progress.data.speed": Style(color="red"),
    "progress.spinner": Style(color="green"),
    "status.spinner": Style(color="green"),
    "tree": Style(),
    "tree.line": Style(),
    "markdown.paragraph": Style(),
    "markdown.text": Style(),
    "markdown.em": Style(italic=True),
    "markdown.emph": Style(italic=True),  # For commonmark backwards compatibility
    "markdown.strong": Style(bold=True),
    "markdown.code": Style(bold=True, color="cyan", bgcolor="black"),
    "markdown.code_block": Style(color="cyan", bgcolor="black"),
    "markdown.block_quote": Style(color="magenta"),
    "markdown.list": Style(color="cyan"),
    "markdown.item": Style(),
    "markdown.item.bullet": Style(color="yellow", bold=True),
    "markdown.item.number": Style(color="yellow", bold=True),
    "markdown.hr": Style(color="yellow"),
    "markdown.h1.border": Style(),
    "markdown.h1": Style(bold=True),
    "markdown.h2": Style(bold=True, underline=True),
    "markdown.h3": Style(bold=True),
    "markdown.h4": Style(bold=True, dim=True),
    "markdown.h5": Style(underline=True),
    "markdown.h6": Style(italic=True),
    "markdown.h7": Style(italic=True, dim=True),
    "markdown.link": Style(color="bright_blue"),
    "markdown.link_url": Style(color="blue", underline=True),
    "markdown.s": Style(strike=True),
    "iso8601.date": Style(color="blue"),
    "iso8601.time": Style(color="magenta"),
    "iso8601.timezone": Style(color="yellow"),
}


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import io

    from pip._vendor.rich.console import Console
    from pip._vendor.rich.table import Table
    from pip._vendor.rich.text import Text

    parser = argparse.ArgumentParser()
    parser.add_argument("--html", action="store_true", help="Export as HTML table")
    args = parser.parse_args()
    html: bool = args.html
    console = Console(record=True, width=70, file=io.StringIO()) if html else Console()

    table = Table("Name", "Styling")

    for style_name, style in DEFAULT_STYLES.items():
        table.add_row(Text(style_name, style=style), str(style))

    console.print(table)
    if html:
        print(console.export_html(inline_styles=True))

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\request.py ===
from __future__ import absolute_import

import sys

from .filepost import encode_multipart_formdata
from .packages import six
from .packages.six.moves.urllib.parse import urlencode

__all__ = ["RequestMethods"]


class RequestMethods(object):
    """
    Convenience mixin for classes who implement a :meth:`urlopen` method, such
    as :class:`urllib3.HTTPConnectionPool` and
    :class:`urllib3.PoolManager`.

    Provides behavior for making common types of HTTP request methods and
    decides which type of request field encoding to use.

    Specifically,

    :meth:`.request_encode_url` is for sending requests whose fields are
    encoded in the URL (such as GET, HEAD, DELETE).

    :meth:`.request_encode_body` is for sending requests whose fields are
    encoded in the *body* of the request using multipart or www-form-urlencoded
    (such as for POST, PUT, PATCH).

    :meth:`.request` is for making any kind of request, it will look up the
    appropriate encoding format and use one of the above two methods to make
    the request.

    Initializer parameters:

    :param headers:
        Headers to include with all requests, unless other headers are given
        explicitly.
    """

    _encode_url_methods = {"DELETE", "GET", "HEAD", "OPTIONS"}

    def __init__(self, headers=None):
        self.headers = headers or {}

    def urlopen(
        self,
        method,
        url,
        body=None,
        headers=None,
        encode_multipart=True,
        multipart_boundary=None,
        **kw
    ):  # Abstract
        raise NotImplementedError(
            "Classes extending RequestMethods must implement "
            "their own ``urlopen`` method."
        )

    def request(self, method, url, fields=None, headers=None, **urlopen_kw):
        """
        Make a request using :meth:`urlopen` with the appropriate encoding of
        ``fields`` based on the ``method`` used.

        This is a convenience method that requires the least amount of manual
        effort. It can be used in most situations, while still having the
        option to drop down to more specific methods when necessary, such as
        :meth:`request_encode_url`, :meth:`request_encode_body`,
        or even the lowest level :meth:`urlopen`.
        """
        method = method.upper()

        urlopen_kw["request_url"] = url

        if method in self._encode_url_methods:
            return self.request_encode_url(
                method, url, fields=fields, headers=headers, **urlopen_kw
            )
        else:
            return self.request_encode_body(
                method, url, fields=fields, headers=headers, **urlopen_kw
            )

    def request_encode_url(self, method, url, fields=None, headers=None, **urlopen_kw):
        """
        Make a request using :meth:`urlopen` with the ``fields`` encoded in
        the url. This is useful for request methods like GET, HEAD, DELETE, etc.
        """
        if headers is None:
            headers = self.headers

        extra_kw = {"headers": headers}
        extra_kw.update(urlopen_kw)

        if fields:
            url += "?" + urlencode(fields)

        return self.urlopen(method, url, **extra_kw)

    def request_encode_body(
        self,
        method,
        url,
        fields=None,
        headers=None,
        encode_multipart=True,
        multipart_boundary=None,
        **urlopen_kw
    ):
        """
        Make a request using :meth:`urlopen` with the ``fields`` encoded in
        the body. This is useful for request methods like POST, PUT, PATCH, etc.

        When ``encode_multipart=True`` (default), then
        :func:`urllib3.encode_multipart_formdata` is used to encode
        the payload with the appropriate content type. Otherwise
        :func:`urllib.parse.urlencode` is used with the
        'application/x-www-form-urlencoded' content type.

        Multipart encoding must be used when posting files, and it's reasonably
        safe to use it in other times too. However, it may break request
        signing, such as with OAuth.

        Supports an optional ``fields`` parameter of key/value strings AND
        key/filetuple. A filetuple is a (filename, data, MIME type) tuple where
        the MIME type is optional. For example::

            fields = {
                'foo': 'bar',
                'fakefile': ('foofile.txt', 'contents of foofile'),
                'realfile': ('barfile.txt', open('realfile').read()),
                'typedfile': ('bazfile.bin', open('bazfile').read(),
                              'image/jpeg'),
                'nonamefile': 'contents of nonamefile field',
            }

        When uploading a file, providing a filename (the first parameter of the
        tuple) is optional but recommended to best mimic behavior of browsers.

        Note that if ``headers`` are supplied, the 'Content-Type' header will
        be overwritten because it depends on the dynamic random boundary string
        which is used to compose the body of the request. The random boundary
        string can be explicitly set with the ``multipart_boundary`` parameter.
        """
        if headers is None:
            headers = self.headers

        extra_kw = {"headers": {}}

        if fields:
            if "body" in urlopen_kw:
                raise TypeError(
                    "request got values for both 'fields' and 'body', can only specify one."
                )

            if encode_multipart:
                body, content_type = encode_multipart_formdata(
                    fields, boundary=multipart_boundary
                )
            else:
                body, content_type = (
                    urlencode(fields),
                    "application/x-www-form-urlencoded",
                )

            extra_kw["body"] = body
            extra_kw["headers"] = {"Content-Type": content_type}

        extra_kw["headers"].update(headers)
        extra_kw.update(urlopen_kw)

        return self.urlopen(method, url, **extra_kw)


if not six.PY2:

    class RequestModule(sys.modules[__name__].__class__):
        def __call__(self, *args, **kwargs):
            """
            If user tries to call this module directly urllib3 v2.x style raise an error to the user
            suggesting they may need urllib3 v2
            """
            raise TypeError(
                "'module' object is not callable\n"
                "urllib3.request() method is not supported in this release, "
                "upgrade to urllib3 v2 to use it\n"
                "see https://urllib3.readthedocs.io/en/stable/v2-migration-guide.html"
            )

    sys.modules[__name__].__class__ = RequestModule

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\eventloop\inputhook.py ===
"""
Similar to `PyOS_InputHook` of the Python API, we can plug in an input hook in
the asyncio event loop.

The way this works is by using a custom 'selector' that runs the other event
loop until the real selector is ready.

It's the responsibility of this event hook to return when there is input ready.
There are two ways to detect when input is ready:

The inputhook itself is a callable that receives an `InputHookContext`. This
callable should run the other event loop, and return when the main loop has
stuff to do. There are two ways to detect when to return:

- Call the `input_is_ready` method periodically. Quit when this returns `True`.

- Add the `fileno` as a watch to the external eventloop. Quit when file descriptor
  becomes readable. (But don't read from it.)

  Note that this is not the same as checking for `sys.stdin.fileno()`. The
  eventloop of prompt-toolkit allows thread-based executors, for example for
  asynchronous autocompletion. When the completion for instance is ready, we
  also want prompt-toolkit to gain control again in order to display that.
"""

from __future__ import annotations

import asyncio
import os
import select
import selectors
import sys
import threading
from asyncio import AbstractEventLoop, get_running_loop
from selectors import BaseSelector, SelectorKey
from typing import TYPE_CHECKING, Any, Callable, Mapping

__all__ = [
    "new_eventloop_with_inputhook",
    "set_eventloop_with_inputhook",
    "InputHookSelector",
    "InputHookContext",
    "InputHook",
]

if TYPE_CHECKING:
    from _typeshed import FileDescriptorLike
    from typing_extensions import TypeAlias

    _EventMask = int


class InputHookContext:
    """
    Given as a parameter to the inputhook.
    """

    def __init__(self, fileno: int, input_is_ready: Callable[[], bool]) -> None:
        self._fileno = fileno
        self.input_is_ready = input_is_ready

    def fileno(self) -> int:
        return self._fileno


InputHook: TypeAlias = Callable[[InputHookContext], None]


def new_eventloop_with_inputhook(
    inputhook: Callable[[InputHookContext], None],
) -> AbstractEventLoop:
    """
    Create a new event loop with the given inputhook.
    """
    selector = InputHookSelector(selectors.DefaultSelector(), inputhook)
    loop = asyncio.SelectorEventLoop(selector)
    return loop


def set_eventloop_with_inputhook(
    inputhook: Callable[[InputHookContext], None],
) -> AbstractEventLoop:
    """
    Create a new event loop with the given inputhook, and activate it.
    """
    # Deprecated!

    loop = new_eventloop_with_inputhook(inputhook)
    asyncio.set_event_loop(loop)
    return loop


class InputHookSelector(BaseSelector):
    """
    Usage:

        selector = selectors.SelectSelector()
        loop = asyncio.SelectorEventLoop(InputHookSelector(selector, inputhook))
        asyncio.set_event_loop(loop)
    """

    def __init__(
        self, selector: BaseSelector, inputhook: Callable[[InputHookContext], None]
    ) -> None:
        self.selector = selector
        self.inputhook = inputhook
        self._r, self._w = os.pipe()

    def register(
        self, fileobj: FileDescriptorLike, events: _EventMask, data: Any = None
    ) -> SelectorKey:
        return self.selector.register(fileobj, events, data=data)

    def unregister(self, fileobj: FileDescriptorLike) -> SelectorKey:
        return self.selector.unregister(fileobj)

    def modify(
        self, fileobj: FileDescriptorLike, events: _EventMask, data: Any = None
    ) -> SelectorKey:
        return self.selector.modify(fileobj, events, data=None)

    def select(
        self, timeout: float | None = None
    ) -> list[tuple[SelectorKey, _EventMask]]:
        # If there are tasks in the current event loop,
        # don't run the input hook.
        if len(getattr(get_running_loop(), "_ready", [])) > 0:
            return self.selector.select(timeout=timeout)

        ready = False
        result = None

        # Run selector in other thread.
        def run_selector() -> None:
            nonlocal ready, result
            result = self.selector.select(timeout=timeout)
            os.write(self._w, b"x")
            ready = True

        th = threading.Thread(target=run_selector)
        th.start()

        def input_is_ready() -> bool:
            return ready

        # Call inputhook.
        # The inputhook function is supposed to return when our selector
        # becomes ready. The inputhook can do that by registering the fd in its
        # own loop, or by checking the `input_is_ready` function regularly.
        self.inputhook(InputHookContext(self._r, input_is_ready))

        # Flush the read end of the pipe.
        try:
            # Before calling 'os.read', call select.select. This is required
            # when the gevent monkey patch has been applied. 'os.read' is never
            # monkey patched and won't be cooperative, so that would block all
            # other select() calls otherwise.
            # See: http://www.gevent.org/gevent.os.html

            # Note: On Windows, this is apparently not an issue.
            #       However, if we would ever want to add a select call, it
            #       should use `windll.kernel32.WaitForMultipleObjects`,
            #       because `select.select` can't wait for a pipe on Windows.
            if sys.platform != "win32":
                select.select([self._r], [], [], None)

            os.read(self._r, 1024)
        except OSError:
            # This happens when the window resizes and a SIGWINCH was received.
            # We get 'Error: [Errno 4] Interrupted system call'
            # Just ignore.
            pass

        # Wait for the real selector to be done.
        th.join()
        assert result is not None
        return result

    def close(self) -> None:
        """
        Clean up resources.
        """
        if self._r:
            os.close(self._r)
            os.close(self._w)

        self._r = self._w = -1
        self.selector.close()

    def get_map(self) -> Mapping[FileDescriptorLike, SelectorKey]:
        return self.selector.get_map()

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\config.py ===
import json
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, ForwardRef, Optional, Tuple, Type, Union

from typing_extensions import Literal, Protocol

from pydantic.v1.typing import AnyArgTCallable, AnyCallable
from pydantic.v1.utils import GetterDict
from pydantic.v1.version import compiled

if TYPE_CHECKING:
    from typing import overload

    from pydantic.v1.fields import ModelField
    from pydantic.v1.main import BaseModel

    ConfigType = Type['BaseConfig']

    class SchemaExtraCallable(Protocol):
        @overload
        def __call__(self, schema: Dict[str, Any]) -> None:
            pass

        @overload
        def __call__(self, schema: Dict[str, Any], model_class: Type[BaseModel]) -> None:
            pass

else:
    SchemaExtraCallable = Callable[..., None]

__all__ = 'BaseConfig', 'ConfigDict', 'get_config', 'Extra', 'inherit_config', 'prepare_config'


class Extra(str, Enum):
    allow = 'allow'
    ignore = 'ignore'
    forbid = 'forbid'


# https://github.com/cython/cython/issues/4003
# Fixed in Cython 3 and Pydantic v1 won't support Cython 3.
# Pydantic v2 doesn't depend on Cython at all.
if not compiled:
    from typing_extensions import TypedDict

    class ConfigDict(TypedDict, total=False):
        title: Optional[str]
        anystr_lower: bool
        anystr_strip_whitespace: bool
        min_anystr_length: int
        max_anystr_length: Optional[int]
        validate_all: bool
        extra: Extra
        allow_mutation: bool
        frozen: bool
        allow_population_by_field_name: bool
        use_enum_values: bool
        fields: Dict[str, Union[str, Dict[str, str]]]
        validate_assignment: bool
        error_msg_templates: Dict[str, str]
        arbitrary_types_allowed: bool
        orm_mode: bool
        getter_dict: Type[GetterDict]
        alias_generator: Optional[Callable[[str], str]]
        keep_untouched: Tuple[type, ...]
        schema_extra: Union[Dict[str, object], 'SchemaExtraCallable']
        json_loads: Callable[[str], object]
        json_dumps: AnyArgTCallable[str]
        json_encoders: Dict[Type[object], AnyCallable]
        underscore_attrs_are_private: bool
        allow_inf_nan: bool
        copy_on_model_validation: Literal['none', 'deep', 'shallow']
        # whether dataclass `__post_init__` should be run after validation
        post_init_call: Literal['before_validation', 'after_validation']

else:
    ConfigDict = dict  # type: ignore


class BaseConfig:
    title: Optional[str] = None
    anystr_lower: bool = False
    anystr_upper: bool = False
    anystr_strip_whitespace: bool = False
    min_anystr_length: int = 0
    max_anystr_length: Optional[int] = None
    validate_all: bool = False
    extra: Extra = Extra.ignore
    allow_mutation: bool = True
    frozen: bool = False
    allow_population_by_field_name: bool = False
    use_enum_values: bool = False
    fields: Dict[str, Union[str, Dict[str, str]]] = {}
    validate_assignment: bool = False
    error_msg_templates: Dict[str, str] = {}
    arbitrary_types_allowed: bool = False
    orm_mode: bool = False
    getter_dict: Type[GetterDict] = GetterDict
    alias_generator: Optional[Callable[[str], str]] = None
    keep_untouched: Tuple[type, ...] = ()
    schema_extra: Union[Dict[str, Any], 'SchemaExtraCallable'] = {}
    json_loads: Callable[[str], Any] = json.loads
    json_dumps: Callable[..., str] = json.dumps
    json_encoders: Dict[Union[Type[Any], str, ForwardRef], AnyCallable] = {}
    underscore_attrs_are_private: bool = False
    allow_inf_nan: bool = True

    # whether inherited models as fields should be reconstructed as base model,
    # and whether such a copy should be shallow or deep
    copy_on_model_validation: Literal['none', 'deep', 'shallow'] = 'shallow'

    # whether `Union` should check all allowed types before even trying to coerce
    smart_union: bool = False
    # whether dataclass `__post_init__` should be run before or after validation
    post_init_call: Literal['before_validation', 'after_validation'] = 'before_validation'

    @classmethod
    def get_field_info(cls, name: str) -> Dict[str, Any]:
        """
        Get properties of FieldInfo from the `fields` property of the config class.
        """

        fields_value = cls.fields.get(name)

        if isinstance(fields_value, str):
            field_info: Dict[str, Any] = {'alias': fields_value}
        elif isinstance(fields_value, dict):
            field_info = fields_value
        else:
            field_info = {}

        if 'alias' in field_info:
            field_info.setdefault('alias_priority', 2)

        if field_info.get('alias_priority', 0) <= 1 and cls.alias_generator:
            alias = cls.alias_generator(name)
            if not isinstance(alias, str):
                raise TypeError(f'Config.alias_generator must return str, not {alias.__class__}')
            field_info.update(alias=alias, alias_priority=1)
        return field_info

    @classmethod
    def prepare_field(cls, field: 'ModelField') -> None:
        """
        Optional hook to check or modify fields during model creation.
        """
        pass


def get_config(config: Union[ConfigDict, Type[object], None]) -> Type[BaseConfig]:
    if config is None:
        return BaseConfig

    else:
        config_dict = (
            config
            if isinstance(config, dict)
            else {k: getattr(config, k) for k in dir(config) if not k.startswith('__')}
        )

        class Config(BaseConfig):
            ...

        for k, v in config_dict.items():
            setattr(Config, k, v)
        return Config


def inherit_config(self_config: 'ConfigType', parent_config: 'ConfigType', **namespace: Any) -> 'ConfigType':
    if not self_config:
        base_classes: Tuple['ConfigType', ...] = (parent_config,)
    elif self_config == parent_config:
        base_classes = (self_config,)
    else:
        base_classes = self_config, parent_config

    namespace['json_encoders'] = {
        **getattr(parent_config, 'json_encoders', {}),
        **getattr(self_config, 'json_encoders', {}),
        **namespace.get('json_encoders', {}),
    }

    return type('Config', base_classes, namespace)


def prepare_config(config: Type[BaseConfig], cls_name: str) -> None:
    if not isinstance(config.extra, Extra):
        try:
            config.extra = Extra(config.extra)
        except ValueError:
            raise ValueError(f'"{cls_name}": {config.extra} is not a valid value for "extra"')

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\actions\action_builder.py ===
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

from typing import List, Optional, Union

from selenium.webdriver.remote.command import Command

from . import interaction
from .key_actions import KeyActions
from .key_input import KeyInput
from .pointer_actions import PointerActions
from .pointer_input import PointerInput
from .wheel_actions import WheelActions
from .wheel_input import WheelInput


class ActionBuilder:
    def __init__(
        self,
        driver,
        mouse: Optional[PointerInput] = None,
        wheel: Optional[WheelInput] = None,
        keyboard: Optional[KeyInput] = None,
        duration: int = 250,
    ) -> None:
        mouse = mouse or PointerInput(interaction.POINTER_MOUSE, "mouse")
        keyboard = keyboard or KeyInput(interaction.KEY)
        wheel = wheel or WheelInput(interaction.WHEEL)
        self.devices = [mouse, keyboard, wheel]
        self._key_action = KeyActions(keyboard)
        self._pointer_action = PointerActions(mouse, duration=duration)
        self._wheel_action = WheelActions(wheel)
        self.driver = driver

    def get_device_with(self, name: str) -> Optional[Union["WheelInput", "PointerInput", "KeyInput"]]:
        """Get the device with the given name.

        Parameters:
        -----------
        name : str
            The name of the device to get.

        Returns:
        --------
        Optional[Union[WheelInput, PointerInput, KeyInput]] : The device with the given name.
        """
        return next(filter(lambda x: x == name, self.devices), None)

    @property
    def pointer_inputs(self) -> List[PointerInput]:
        return [device for device in self.devices if device.type == interaction.POINTER]

    @property
    def key_inputs(self) -> List[KeyInput]:
        return [device for device in self.devices if device.type == interaction.KEY]

    @property
    def key_action(self) -> KeyActions:
        return self._key_action

    @property
    def pointer_action(self) -> PointerActions:
        return self._pointer_action

    @property
    def wheel_action(self) -> WheelActions:
        return self._wheel_action

    def add_key_input(self, name: str) -> KeyInput:
        """Add a new key input device to the action builder.

        Parameters:
        -----------
        name : str
            The name of the key input device.

        Returns:
        --------
        KeyInput : The newly created key input device.

        Example:
        --------
        >>> action_builder = ActionBuilder(driver)
        >>> action_builder.add_key_input(name="keyboard2")
        """
        new_input = KeyInput(name)
        self._add_input(new_input)
        return new_input

    def add_pointer_input(self, kind: str, name: str) -> PointerInput:
        """Add a new pointer input device to the action builder.

        Parameters:
        -----------
        kind : str
            The kind of pointer input device.
                - "mouse"
                - "touch"
                - "pen"

        name : str
            The name of the pointer input device.

        Returns:
        --------
        PointerInput : The newly created pointer input device.

        Example:
        --------
        >>> action_builder = ActionBuilder(driver)
        >>> action_builder.add_pointer_input(kind="mouse", name="mouse")
        """
        new_input = PointerInput(kind, name)
        self._add_input(new_input)
        return new_input

    def add_wheel_input(self, name: str) -> WheelInput:
        """Add a new wheel input device to the action builder.

        Parameters:
        -----------
        name : str
            The name of the wheel input device.

        Returns:
        --------
        WheelInput : The newly created wheel input device.

        Example:
        --------
        >>> action_builder = ActionBuilder(driver)
        >>> action_builder.add_wheel_input(name="wheel2")
        """
        new_input = WheelInput(name)
        self._add_input(new_input)
        return new_input

    def perform(self) -> None:
        """Performs all stored actions.

        Example:
        --------
        >>> action_builder = ActionBuilder(driver)
        >>> keyboard = action_builder.key_input
        >>> el = driver.find_element(id: "some_id")
        >>> action_builder.click(el).pause(keyboard).pause(keyboard).pause(keyboard).send_keys("keys").perform()
        """
        enc = {"actions": []}
        for device in self.devices:
            encoded = device.encode()
            if encoded["actions"]:
                enc["actions"].append(encoded)
                device.actions = []
        self.driver.execute(Command.W3C_ACTIONS, enc)

    def clear_actions(self) -> None:
        """Clears actions that are already stored on the remote end.

        Example:
        --------
        >>> action_builder = ActionBuilder(driver)
        >>> keyboard = action_builder.key_input
        >>> el = driver.find_element(By.ID, "some_id")
        >>> action_builder.click(el).pause(keyboard).pause(keyboard).pause(keyboard).send_keys("keys")
        >>> action_builder.clear_actions()
        """
        self.driver.execute(Command.W3C_CLEAR_ACTIONS)

    def _add_input(self, new_input: Union[KeyInput, PointerInput, WheelInput]) -> None:
        """Add a new input device to the action builder.

        Parameters:
        -----------
        new_input : Union[KeyInput, PointerInput, WheelInput]
            The new input device to add.
        """
        self.devices.append(new_input)

# === NexusCore/openenv\Lib\site-packages\dotenv\cli.py ===
import json
import os
import shlex
import sys
from contextlib import contextmanager
from typing import Any, Dict, IO, Iterator, List, Optional

try:
    import click
except ImportError:
    sys.stderr.write('It seems python-dotenv is not installed with cli option. \n'
                     'Run pip install "python-dotenv[cli]" to fix this.')
    sys.exit(1)

from .main import dotenv_values, set_key, unset_key
from .version import __version__


def enumerate_env() -> Optional[str]:
    """
    Return a path for the ${pwd}/.env file.

    If pwd does not exist, return None.
    """
    try:
        cwd = os.getcwd()
    except FileNotFoundError:
        return None
    path = os.path.join(cwd, '.env')
    return path


@click.group()
@click.option('-f', '--file', default=enumerate_env(),
              type=click.Path(file_okay=True),
              help="Location of the .env file, defaults to .env file in current working directory.")
@click.option('-q', '--quote', default='always',
              type=click.Choice(['always', 'never', 'auto']),
              help="Whether to quote or not the variable values. Default mode is always. This does not affect parsing.")
@click.option('-e', '--export', default=False,
              type=click.BOOL,
              help="Whether to write the dot file as an executable bash script.")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context, file: Any, quote: Any, export: Any) -> None:
    """This script is used to set, get or unset values from a .env file."""
    ctx.obj = {'QUOTE': quote, 'EXPORT': export, 'FILE': file}


@contextmanager
def stream_file(path: os.PathLike) -> Iterator[IO[str]]:
    """
    Open a file and yield the corresponding (decoded) stream.

    Exits with error code 2 if the file cannot be opened.
    """

    try:
        with open(path) as stream:
            yield stream
    except OSError as exc:
        print(f"Error opening env file: {exc}", file=sys.stderr)
        exit(2)


@cli.command()
@click.pass_context
@click.option('--format', default='simple',
              type=click.Choice(['simple', 'json', 'shell', 'export']),
              help="The format in which to display the list. Default format is simple, "
                   "which displays name=value without quotes.")
def list(ctx: click.Context, format: bool) -> None:
    """Display all the stored key/value."""
    file = ctx.obj['FILE']

    with stream_file(file) as stream:
        values = dotenv_values(stream=stream)

    if format == 'json':
        click.echo(json.dumps(values, indent=2, sort_keys=True))
    else:
        prefix = 'export ' if format == 'export' else ''
        for k in sorted(values):
            v = values[k]
            if v is not None:
                if format in ('export', 'shell'):
                    v = shlex.quote(v)
                click.echo(f'{prefix}{k}={v}')


@cli.command()
@click.pass_context
@click.argument('key', required=True)
@click.argument('value', required=True)
def set(ctx: click.Context, key: Any, value: Any) -> None:
    """Store the given key/value."""
    file = ctx.obj['FILE']
    quote = ctx.obj['QUOTE']
    export = ctx.obj['EXPORT']
    success, key, value = set_key(file, key, value, quote, export)
    if success:
        click.echo(f'{key}={value}')
    else:
        exit(1)


@cli.command()
@click.pass_context
@click.argument('key', required=True)
def get(ctx: click.Context, key: Any) -> None:
    """Retrieve the value for the given key."""
    file = ctx.obj['FILE']

    with stream_file(file) as stream:
        values = dotenv_values(stream=stream)

    stored_value = values.get(key)
    if stored_value:
        click.echo(stored_value)
    else:
        exit(1)


@cli.command()
@click.pass_context
@click.argument('key', required=True)
def unset(ctx: click.Context, key: Any) -> None:
    """Removes the given key."""
    file = ctx.obj['FILE']
    quote = ctx.obj['QUOTE']
    success, key = unset_key(file, key, quote)
    if success:
        click.echo(f"Successfully removed {key}")
    else:
        exit(1)


@cli.command(context_settings={'ignore_unknown_options': True})
@click.pass_context
@click.option(
    "--override/--no-override",
    default=True,
    help="Override variables from the environment file with those from the .env file.",
)
@click.argument('commandline', nargs=-1, type=click.UNPROCESSED)
def run(ctx: click.Context, override: bool, commandline: List[str]) -> None:
    """Run command with environment variables present."""
    file = ctx.obj['FILE']
    if not os.path.isfile(file):
        raise click.BadParameter(
            f'Invalid value for \'-f\' "{file}" does not exist.',
            ctx=ctx
        )
    dotenv_as_dict = {
        k: v
        for (k, v) in dotenv_values(file).items()
        if v is not None and (override or k not in os.environ)
    }

    if not commandline:
        click.echo('No command given.')
        exit(1)
    run_command(commandline, dotenv_as_dict)


def run_command(command: List[str], env: Dict[str, str]) -> None:
    """Replace the current process with the specified command.

    Replaces the current process with the specified command and the variables from `env`
    added in the current environment variables.

    Parameters
    ----------
    command: List[str]
        The command and it's parameters
    env: Dict
        The additional environment variables

    Returns
    -------
    None
        This function does not return any value. It replaces the current process with the new one.

    """
    # copy the current environment variables and add the vales from
    # `env`
    cmd_env = os.environ.copy()
    cmd_env.update(env)

    os.execvpe(command[0], args=command, env=cmd_env)

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc5480.py ===
# This file is being contributed to pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
# Modified by Russ Housley to add maps for opentypes.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Elliptic Curve Cryptography Subject Public Key Information
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc5480.txt


# What can be imported from rfc4055.py ?

from pyasn1.type import namedtype
from pyasn1.type import univ

from pyasn1_modules import rfc3279
from pyasn1_modules import rfc5280


# These structures are the same as RFC 3279.

DHPublicKey = rfc3279.DHPublicKey

DSAPublicKey = rfc3279.DSAPublicKey

ValidationParms = rfc3279.ValidationParms

DomainParameters = rfc3279.DomainParameters

ECDSA_Sig_Value = rfc3279.ECDSA_Sig_Value

ECPoint = rfc3279.ECPoint

KEA_Parms_Id = rfc3279.KEA_Parms_Id

RSAPublicKey = rfc3279.RSAPublicKey


# RFC 5480 changed the names of these structures from RFC 3279.

DSS_Parms = rfc3279.Dss_Parms

DSA_Sig_Value = rfc3279.Dss_Sig_Value


# RFC 3279 defines a more complex alternative for ECParameters.
# RFC 5480 narrows the definition to a single CHOICE: namedCurve.

class ECParameters(univ.Choice):
    pass

ECParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('namedCurve', univ.ObjectIdentifier())
)


# OIDs for Message Digest Algorithms

id_md2 = univ.ObjectIdentifier('1.2.840.113549.2.2')

id_md5 = univ.ObjectIdentifier('1.2.840.113549.2.5')

id_sha1 = univ.ObjectIdentifier('1.3.14.3.2.26')

id_sha224 = univ.ObjectIdentifier('2.16.840.1.101.3.4.2.4')

id_sha256 = univ.ObjectIdentifier('2.16.840.1.101.3.4.2.1')

id_sha384 = univ.ObjectIdentifier('2.16.840.1.101.3.4.2.2')

id_sha512 = univ.ObjectIdentifier('2.16.840.1.101.3.4.2.3')


# OID for RSA PK Algorithm and Key

rsaEncryption = univ.ObjectIdentifier('1.2.840.113549.1.1.1')


# OID for DSA PK Algorithm, Key, and Parameters

id_dsa = univ.ObjectIdentifier('1.2.840.10040.4.1')


# OID for Diffie-Hellman PK Algorithm, Key, and Parameters

dhpublicnumber = univ.ObjectIdentifier('1.2.840.10046.2.1')

# OID for KEA PK Algorithm and Parameters

id_keyExchangeAlgorithm = univ.ObjectIdentifier('2.16.840.1.101.2.1.1.22')


# OIDs for Elliptic Curve Algorithm ID, Key, and Parameters
# Note that ECDSA keys always use this OID

id_ecPublicKey = univ.ObjectIdentifier('1.2.840.10045.2.1')

id_ecDH = univ.ObjectIdentifier('1.3.132.1.12')

id_ecMQV = univ.ObjectIdentifier('1.3.132.1.13')


# OIDs for RSA Signature Algorithms

md2WithRSAEncryption = univ.ObjectIdentifier('1.2.840.113549.1.1.2')

md5WithRSAEncryption = univ.ObjectIdentifier('1.2.840.113549.1.1.4')

sha1WithRSAEncryption = univ.ObjectIdentifier('1.2.840.113549.1.1.5')


# OIDs for DSA Signature Algorithms

id_dsa_with_sha1 = univ.ObjectIdentifier('1.2.840.10040.4.3')

id_dsa_with_sha224 = univ.ObjectIdentifier('2.16.840.1.101.3.4.3.1')

id_dsa_with_sha256 = univ.ObjectIdentifier('2.16.840.1.101.3.4.3.2')


# OIDs for ECDSA Signature Algorithms

ecdsa_with_SHA1 = univ.ObjectIdentifier('1.2.840.10045.4.1')

ecdsa_with_SHA224 = univ.ObjectIdentifier('1.2.840.10045.4.3.1')

ecdsa_with_SHA256 = univ.ObjectIdentifier('1.2.840.10045.4.3.2')

ecdsa_with_SHA384 = univ.ObjectIdentifier('1.2.840.10045.4.3.3')

ecdsa_with_SHA512 = univ.ObjectIdentifier('1.2.840.10045.4.3.4')


# OIDs for Named Elliptic Curves

secp192r1 = univ.ObjectIdentifier('1.2.840.10045.3.1.1')

sect163k1 = univ.ObjectIdentifier('1.3.132.0.1')

sect163r2 = univ.ObjectIdentifier('1.3.132.0.15')

secp224r1 = univ.ObjectIdentifier('1.3.132.0.33')

sect233k1 = univ.ObjectIdentifier('1.3.132.0.26')

sect233r1 = univ.ObjectIdentifier('1.3.132.0.27')

secp256r1 = univ.ObjectIdentifier('1.2.840.10045.3.1.7')

sect283k1 = univ.ObjectIdentifier('1.3.132.0.16')

sect283r1 = univ.ObjectIdentifier('1.3.132.0.17')

secp384r1 = univ.ObjectIdentifier('1.3.132.0.34')

sect409k1 = univ.ObjectIdentifier('1.3.132.0.36')

sect409r1 = univ.ObjectIdentifier('1.3.132.0.37')

secp521r1 = univ.ObjectIdentifier('1.3.132.0.35')

sect571k1 = univ.ObjectIdentifier('1.3.132.0.38')

sect571r1 = univ.ObjectIdentifier('1.3.132.0.39')


# Map of Algorithm Identifier OIDs to Parameters
# The algorithm is not included if the parameters MUST be absent

_algorithmIdentifierMapUpdate = {
    rsaEncryption: univ.Null(),
    md2WithRSAEncryption: univ.Null(),
    md5WithRSAEncryption: univ.Null(),
    sha1WithRSAEncryption: univ.Null(),
    id_dsa: DSS_Parms(),
    dhpublicnumber: DomainParameters(),
    id_keyExchangeAlgorithm: KEA_Parms_Id(),
    id_ecPublicKey: ECParameters(),
    id_ecDH: ECParameters(),
    id_ecMQV: ECParameters(),
}


# Add these Algorithm Identifier map entries to the ones in rfc5280.py

rfc5280.algorithmIdentifierMap.update(_algorithmIdentifierMapUpdate)

# === NexusCore/openenv\Lib\site-packages\websocket\_url.py ===
import os
import socket
import struct
from typing import Optional
from urllib.parse import unquote, urlparse
from ._exceptions import WebSocketProxyException

"""
_url.py
websocket - WebSocket client library for Python

Copyright 2024 engn33r

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

__all__ = ["parse_url", "get_proxy_info"]


def parse_url(url: str) -> tuple:
    """
    parse url and the result is tuple of
    (hostname, port, resource path and the flag of secure mode)

    Parameters
    ----------
    url: str
        url string.
    """
    if ":" not in url:
        raise ValueError("url is invalid")

    scheme, url = url.split(":", 1)

    parsed = urlparse(url, scheme="http")
    if parsed.hostname:
        hostname = parsed.hostname
    else:
        raise ValueError("hostname is invalid")
    port = 0
    if parsed.port:
        port = parsed.port

    is_secure = False
    if scheme == "ws":
        if not port:
            port = 80
    elif scheme == "wss":
        is_secure = True
        if not port:
            port = 443
    else:
        raise ValueError("scheme %s is invalid" % scheme)

    if parsed.path:
        resource = parsed.path
    else:
        resource = "/"

    if parsed.query:
        resource += f"?{parsed.query}"

    return hostname, port, resource, is_secure


DEFAULT_NO_PROXY_HOST = ["localhost", "127.0.0.1"]


def _is_ip_address(addr: str) -> bool:
    try:
        socket.inet_aton(addr)
    except socket.error:
        return False
    else:
        return True


def _is_subnet_address(hostname: str) -> bool:
    try:
        addr, netmask = hostname.split("/")
        return _is_ip_address(addr) and 0 <= int(netmask) < 32
    except ValueError:
        return False


def _is_address_in_network(ip: str, net: str) -> bool:
    ipaddr: int = struct.unpack("!I", socket.inet_aton(ip))[0]
    netaddr, netmask = net.split("/")
    netaddr: int = struct.unpack("!I", socket.inet_aton(netaddr))[0]

    netmask = (0xFFFFFFFF << (32 - int(netmask))) & 0xFFFFFFFF
    return ipaddr & netmask == netaddr


def _is_no_proxy_host(hostname: str, no_proxy: Optional[list]) -> bool:
    if not no_proxy:
        if v := os.environ.get("no_proxy", os.environ.get("NO_PROXY", "")).replace(
            " ", ""
        ):
            no_proxy = v.split(",")
    if not no_proxy:
        no_proxy = DEFAULT_NO_PROXY_HOST

    if "*" in no_proxy:
        return True
    if hostname in no_proxy:
        return True
    if _is_ip_address(hostname):
        return any(
            [
                _is_address_in_network(hostname, subnet)
                for subnet in no_proxy
                if _is_subnet_address(subnet)
            ]
        )
    for domain in [domain for domain in no_proxy if domain.startswith(".")]:
        if hostname.endswith(domain):
            return True
    return False


def get_proxy_info(
    hostname: str,
    is_secure: bool,
    proxy_host: Optional[str] = None,
    proxy_port: int = 0,
    proxy_auth: Optional[tuple] = None,
    no_proxy: Optional[list] = None,
    proxy_type: str = "http",
) -> tuple:
    """
    Try to retrieve proxy host and port from environment
    if not provided in options.
    Result is (proxy_host, proxy_port, proxy_auth).
    proxy_auth is tuple of username and password
    of proxy authentication information.

    Parameters
    ----------
    hostname: str
        Websocket server name.
    is_secure: bool
        Is the connection secure? (wss) looks for "https_proxy" in env
        instead of "http_proxy"
    proxy_host: str
        http proxy host name.
    proxy_port: str or int
        http proxy port.
    no_proxy: list
        Whitelisted host names that don't use the proxy.
    proxy_auth: tuple
        HTTP proxy auth information. Tuple of username and password. Default is None.
    proxy_type: str
        Specify the proxy protocol (http, socks4, socks4a, socks5, socks5h). Default is "http".
        Use socks4a or socks5h if you want to send DNS requests through the proxy.
    """
    if _is_no_proxy_host(hostname, no_proxy):
        return None, 0, None

    if proxy_host:
        if not proxy_port:
            raise WebSocketProxyException("Cannot use port 0 when proxy_host specified")
        port = proxy_port
        auth = proxy_auth
        return proxy_host, port, auth

    env_key = "https_proxy" if is_secure else "http_proxy"
    value = os.environ.get(env_key, os.environ.get(env_key.upper(), "")).replace(
        " ", ""
    )
    if value:
        proxy = urlparse(value)
        auth = (
            (unquote(proxy.username), unquote(proxy.password))
            if proxy.username
            else None
        )
        return proxy.hostname, proxy.port, auth

    return None, 0, None

# === NexusCore/openenv\Lib\site-packages\zmq\decorators.py ===
"""Decorators for running functions with context/sockets.

.. versionadded:: 15.3

Like using Contexts and Sockets as context managers, but with decorator syntax.
Context and sockets are closed at the end of the function.

For example::

    from zmq.decorators import context, socket

    @context()
    @socket(zmq.PUSH)
    def work(ctx, push):
        ...
"""

from __future__ import annotations

# Copyright (c) PyZMQ Developers.
# Distributed under the terms of the Modified BSD License.

__all__ = (
    'context',
    'socket',
)

from functools import wraps

import zmq


class _Decorator:
    '''The mini decorator factory'''

    def __init__(self, target=None):
        self._target = target

    def __call__(self, *dec_args, **dec_kwargs):
        """
        The main logic of decorator

        Here is how those arguments works::

            @out_decorator(*dec_args, *dec_kwargs)
            def func(*wrap_args, **wrap_kwargs):
                ...

        And in the ``wrapper``, we simply create ``self.target`` instance via
        ``with``::

            target = self.get_target(*args, **kwargs)
            with target(*dec_args, **dec_kwargs) as obj:
                ...

        """
        kw_name, dec_args, dec_kwargs = self.process_decorator_args(
            *dec_args, **dec_kwargs
        )

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                target = self.get_target(*args, **kwargs)

                with target(*dec_args, **dec_kwargs) as obj:
                    # insert our object into args
                    if kw_name and kw_name not in kwargs:
                        kwargs[kw_name] = obj
                    elif kw_name and kw_name in kwargs:
                        raise TypeError(
                            f"{func.__name__}() got multiple values for"
                            f" argument '{kw_name}'"
                        )
                    else:
                        args = args + (obj,)

                    return func(*args, **kwargs)

            return wrapper

        return decorator

    def get_target(self, *args, **kwargs):
        """Return the target function

        Allows modifying args/kwargs to be passed.
        """
        return self._target

    def process_decorator_args(self, *args, **kwargs):
        """Process args passed to the decorator.

        args not consumed by the decorator will be passed to the target factory
        (Context/Socket constructor).
        """
        kw_name = None

        if isinstance(kwargs.get('name'), str):
            kw_name = kwargs.pop('name')
        elif len(args) >= 1 and isinstance(args[0], str):
            kw_name = args[0]
            args = args[1:]

        return kw_name, args, kwargs


class _ContextDecorator(_Decorator):
    """Decorator subclass for Contexts"""

    def __init__(self):
        super().__init__(zmq.Context)


class _SocketDecorator(_Decorator):
    """Decorator subclass for sockets

    Gets the context from other args.
    """

    def process_decorator_args(self, *args, **kwargs):
        """Also grab context_name out of kwargs"""
        kw_name, args, kwargs = super().process_decorator_args(*args, **kwargs)
        self.context_name = kwargs.pop('context_name', 'context')
        return kw_name, args, kwargs

    def get_target(self, *args, **kwargs):
        """Get context, based on call-time args"""
        context = self._get_context(*args, **kwargs)
        return context.socket

    def _get_context(self, *args, **kwargs):
        """
        Find the ``zmq.Context`` from ``args`` and ``kwargs`` at call time.

        First, if there is an keyword argument named ``context`` and it is a
        ``zmq.Context`` instance , we will take it.

        Second, we check all the ``args``, take the first ``zmq.Context``
        instance.

        Finally, we will provide default Context -- ``zmq.Context.instance``

        :return: a ``zmq.Context`` instance
        """
        if self.context_name in kwargs:
            ctx = kwargs[self.context_name]

            if isinstance(ctx, zmq.Context):
                return ctx

        for arg in args:
            if isinstance(arg, zmq.Context):
                return arg
        # not specified by any decorator
        return zmq.Context.instance()


def context(*args, **kwargs):
    """Decorator for adding a Context to a function.

    Usage::

        @context()
        def foo(ctx):
            ...

    .. versionadded:: 15.3

    :param str name: the keyword argument passed to decorated function
    """
    return _ContextDecorator()(*args, **kwargs)


def socket(*args, **kwargs):
    """Decorator for adding a socket to a function.

    Usage::

        @socket(zmq.PUSH)
        def foo(push):
            ...

    .. versionadded:: 15.3

    :param str name: the keyword argument passed to decorated function
    :param str context_name: the keyword only argument to identify context
                             object
    """
    return _SocketDecorator()(*args, **kwargs)

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\instancer\featureVars.py ===
from fontTools.ttLib.tables import otTables as ot
from copy import deepcopy
import logging


log = logging.getLogger("fontTools.varLib.instancer")


def _featureVariationRecordIsUnique(rec, seen):
    conditionSet = []
    conditionSets = (
        rec.ConditionSet.ConditionTable if rec.ConditionSet is not None else []
    )
    for cond in conditionSets:
        if cond.Format != 1:
            # can't tell whether this is duplicate, assume is unique
            return True
        conditionSet.append(
            (cond.AxisIndex, cond.FilterRangeMinValue, cond.FilterRangeMaxValue)
        )
    # besides the set of conditions, we also include the FeatureTableSubstitution
    # version to identify unique FeatureVariationRecords, even though only one
    # version is currently defined. It's theoretically possible that multiple
    # records with same conditions but different substitution table version be
    # present in the same font for backward compatibility.
    recordKey = frozenset([rec.FeatureTableSubstitution.Version] + conditionSet)
    if recordKey in seen:
        return False
    else:
        seen.add(recordKey)  # side effect
        return True


def _limitFeatureVariationConditionRange(condition, axisLimit):
    minValue = condition.FilterRangeMinValue
    maxValue = condition.FilterRangeMaxValue

    if (
        minValue > maxValue
        or minValue > axisLimit.maximum
        or maxValue < axisLimit.minimum
    ):
        # condition invalid or out of range
        return

    return tuple(
        axisLimit.renormalizeValue(v, extrapolate=False) for v in (minValue, maxValue)
    )


def _instantiateFeatureVariationRecord(
    record, recIdx, axisLimits, fvarAxes, axisIndexMap
):
    applies = True
    shouldKeep = False
    newConditions = []
    from fontTools.varLib.instancer import NormalizedAxisTripleAndDistances

    default_triple = NormalizedAxisTripleAndDistances(-1, 0, +1)
    if record.ConditionSet is None:
        record.ConditionSet = ot.ConditionSet()
        record.ConditionSet.ConditionTable = []
        record.ConditionSet.ConditionCount = 0
    for i, condition in enumerate(record.ConditionSet.ConditionTable):
        if condition.Format == 1:
            axisIdx = condition.AxisIndex
            axisTag = fvarAxes[axisIdx].axisTag

            minValue = condition.FilterRangeMinValue
            maxValue = condition.FilterRangeMaxValue
            triple = axisLimits.get(axisTag, default_triple)

            if not (minValue <= triple.default <= maxValue):
                applies = False

            # if condition not met, remove entire record
            if triple.minimum > maxValue or triple.maximum < minValue:
                newConditions = None
                break

            if axisTag in axisIndexMap:
                # remap axis index
                condition.AxisIndex = axisIndexMap[axisTag]

                # remap condition limits
                newRange = _limitFeatureVariationConditionRange(condition, triple)
                if newRange:
                    # keep condition with updated limits
                    minimum, maximum = newRange
                    condition.FilterRangeMinValue = minimum
                    condition.FilterRangeMaxValue = maximum
                    shouldKeep = True
                    if minimum != -1 or maximum != +1:
                        newConditions.append(condition)
                else:
                    # condition out of range, remove entire record
                    newConditions = None
                    break

        else:
            log.warning(
                "Condition table {0} of FeatureVariationRecord {1} has "
                "unsupported format ({2}); ignored".format(i, recIdx, condition.Format)
            )
            applies = False
            newConditions.append(condition)

    if newConditions is not None and shouldKeep:
        record.ConditionSet.ConditionTable = newConditions
        if not newConditions:
            record.ConditionSet = None
        shouldKeep = True
    else:
        shouldKeep = False

    # Does this *always* apply?
    universal = shouldKeep and not newConditions

    return applies, shouldKeep, universal


def _instantiateFeatureVariations(table, fvarAxes, axisLimits):
    pinnedAxes = set(axisLimits.pinnedLocation())
    axisOrder = [axis.axisTag for axis in fvarAxes if axis.axisTag not in pinnedAxes]
    axisIndexMap = {axisTag: axisOrder.index(axisTag) for axisTag in axisOrder}

    featureVariationApplied = False
    uniqueRecords = set()
    newRecords = []
    defaultsSubsts = None

    for i, record in enumerate(table.FeatureVariations.FeatureVariationRecord):
        applies, shouldKeep, universal = _instantiateFeatureVariationRecord(
            record, i, axisLimits, fvarAxes, axisIndexMap
        )

        if shouldKeep and _featureVariationRecordIsUnique(record, uniqueRecords):
            newRecords.append(record)

        if applies and not featureVariationApplied:
            assert record.FeatureTableSubstitution.Version == 0x00010000
            defaultsSubsts = deepcopy(record.FeatureTableSubstitution)
            for default, rec in zip(
                defaultsSubsts.SubstitutionRecord,
                record.FeatureTableSubstitution.SubstitutionRecord,
            ):
                default.Feature = deepcopy(
                    table.FeatureList.FeatureRecord[rec.FeatureIndex].Feature
                )
                table.FeatureList.FeatureRecord[rec.FeatureIndex].Feature = deepcopy(
                    rec.Feature
                )
            # Set variations only once
            featureVariationApplied = True

        # Further records don't have a chance to apply after a universal record
        if universal:
            break

    # Insert a catch-all record to reinstate the old features if necessary
    if featureVariationApplied and newRecords and not universal:
        defaultRecord = ot.FeatureVariationRecord()
        defaultRecord.ConditionSet = ot.ConditionSet()
        defaultRecord.ConditionSet.ConditionTable = []
        defaultRecord.ConditionSet.ConditionCount = 0
        defaultRecord.FeatureTableSubstitution = defaultsSubsts

        newRecords.append(defaultRecord)

    if newRecords:
        table.FeatureVariations.FeatureVariationRecord = newRecords
        table.FeatureVariations.FeatureVariationCount = len(newRecords)
    else:
        del table.FeatureVariations
        # downgrade table version if there are no FeatureVariations left
        table.Version = 0x00010000


def instantiateFeatureVariations(varfont, axisLimits):
    for tableTag in ("GPOS", "GSUB"):
        if tableTag not in varfont or not getattr(
            varfont[tableTag].table, "FeatureVariations", None
        ):
            continue
        log.info("Instantiating FeatureVariations of %s table", tableTag)
        _instantiateFeatureVariations(
            varfont[tableTag].table, varfont["fvar"].axes, axisLimits
        )
        # remove unreferenced lookups
        varfont[tableTag].prune_lookups()

# === NexusCore/openenv\Lib\site-packages\google\auth\aio\transport\aiohttp.py ===
# Copyright 2024 Google LLC
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

"""Transport adapter for Asynchronous HTTP Requests based on aiohttp.
"""

import asyncio
import logging
from typing import AsyncGenerator, Mapping, Optional

try:
    import aiohttp  # type: ignore
except ImportError as caught_exc:  # pragma: NO COVER
    raise ImportError(
        "The aiohttp library is not installed from please install the aiohttp package to use the aiohttp transport."
    ) from caught_exc

from google.auth import _helpers
from google.auth import exceptions
from google.auth.aio import _helpers as _helpers_async
from google.auth.aio import transport

_LOGGER = logging.getLogger(__name__)


class Response(transport.Response):
    """
    Represents an HTTP response and its data. It is returned by ``google.auth.aio.transport.sessions.AsyncAuthorizedSession``.

    Args:
        response (aiohttp.ClientResponse): An instance of aiohttp.ClientResponse.

    Attributes:
        status_code (int): The HTTP status code of the response.
        headers (Mapping[str, str]): The HTTP headers of the response.
    """

    def __init__(self, response: aiohttp.ClientResponse):
        self._response = response

    @property
    @_helpers.copy_docstring(transport.Response)
    def status_code(self) -> int:
        return self._response.status

    @property
    @_helpers.copy_docstring(transport.Response)
    def headers(self) -> Mapping[str, str]:
        return {key: value for key, value in self._response.headers.items()}

    @_helpers.copy_docstring(transport.Response)
    async def content(self, chunk_size: int = 1024) -> AsyncGenerator[bytes, None]:
        try:
            async for chunk in self._response.content.iter_chunked(
                chunk_size
            ):  # pragma: no branch
                yield chunk
        except aiohttp.ClientPayloadError as exc:
            raise exceptions.ResponseError(
                "Failed to read from the payload stream."
            ) from exc

    @_helpers.copy_docstring(transport.Response)
    async def read(self) -> bytes:
        try:
            return await self._response.read()
        except aiohttp.ClientResponseError as exc:
            raise exceptions.ResponseError("Failed to read the response body.") from exc

    @_helpers.copy_docstring(transport.Response)
    async def close(self):
        self._response.close()


class Request(transport.Request):
    """Asynchronous Requests request adapter.

    This class is used internally for making requests using aiohttp
    in a consistent way. If you use :class:`google.auth.aio.transport.sessions.AsyncAuthorizedSession`
    you do not need to construct or use this class directly.

    This class can be useful if you want to configure a Request callable
    with a custom ``aiohttp.ClientSession`` in :class:`AuthorizedSession` or if
    you want to manually refresh a :class:`~google.auth.aio.credentials.Credentials` instance::

        import aiohttp
        import google.auth.aio.transport.aiohttp

        # Default example:
        request = google.auth.aio.transport.aiohttp.Request()
        await credentials.refresh(request)

        # Custom aiohttp Session Example:
        session = session=aiohttp.ClientSession(auto_decompress=False)
        request = google.auth.aio.transport.aiohttp.Request(session=session)
        auth_sesion = google.auth.aio.transport.sessions.AsyncAuthorizedSession(auth_request=request)

    Args:
        session (aiohttp.ClientSession): An instance :class:`aiohttp.ClientSession` used
            to make HTTP requests. If not specified, a session will be created.

    .. automethod:: __call__
    """

    def __init__(self, session: aiohttp.ClientSession = None):
        self._session = session
        self._closed = False

    async def __call__(
        self,
        url: str,
        method: str = "GET",
        body: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: float = transport._DEFAULT_TIMEOUT_SECONDS,
        **kwargs,
    ) -> transport.Response:
        """
        Make an HTTP request using aiohttp.

        Args:
            url (str): The URL to be requested.
            method (Optional[str]):
                The HTTP method to use for the request. Defaults to 'GET'.
            body (Optional[bytes]):
                The payload or body in HTTP request.
            headers (Optional[Mapping[str, str]]):
                Request headers.
            timeout (float): The number of seconds to wait for a
                response from the server. If not specified or if None, the
                requests default timeout will be used.
            kwargs: Additional arguments passed through to the underlying
                aiohttp :meth:`aiohttp.Session.request` method.

        Returns:
            google.auth.aio.transport.Response: The HTTP response.

        Raises:
            - google.auth.exceptions.TransportError: If the request fails or if the session is closed.
            - google.auth.exceptions.TimeoutError: If the request times out.
        """

        try:
            if self._closed:
                raise exceptions.TransportError("session is closed.")

            if not self._session:
                self._session = aiohttp.ClientSession()

            client_timeout = aiohttp.ClientTimeout(total=timeout)
            _helpers.request_log(_LOGGER, method, url, body, headers)
            response = await self._session.request(
                method,
                url,
                data=body,
                headers=headers,
                timeout=client_timeout,
                **kwargs,
            )
            await _helpers_async.response_log_async(_LOGGER, response)
            return Response(response)

        except aiohttp.ClientError as caught_exc:
            client_exc = exceptions.TransportError(f"Failed to send request to {url}.")
            raise client_exc from caught_exc

        except asyncio.TimeoutError as caught_exc:
            timeout_exc = exceptions.TimeoutError(
                f"Request timed out after {timeout} seconds."
            )
            raise timeout_exc from caught_exc

    async def close(self) -> None:
        """
        Close the underlying aiohttp session to release the acquired resources.
        """
        if not self._closed and self._session:
            await self._session.close()
        self._closed = True

# === NexusCore/openenv\Lib\site-packages\litellm\llms\base_llm\base_utils.py ===
"""
Utility functions for base LLM classes.
"""

import copy
import json
from abc import ABC, abstractmethod
from typing import List, Optional, Type, Union

from openai.lib import _parsing, _pydantic
from pydantic import BaseModel

from litellm._logging import verbose_logger
from litellm.types.llms.openai import AllMessageValues, ChatCompletionToolCallChunk
from litellm.types.utils import Message, ProviderSpecificModelInfo


class BaseLLMModelInfo(ABC):
    def get_provider_info(
        self,
        model: str,
    ) -> Optional[ProviderSpecificModelInfo]:
        """
        Default values all models of this provider support.
        """
        return None

    @abstractmethod
    def get_models(
        self, api_key: Optional[str] = None, api_base: Optional[str] = None
    ) -> List[str]:
        """
        Returns a list of models supported by this provider.
        """
        return []

    @staticmethod
    @abstractmethod
    def get_api_key(api_key: Optional[str] = None) -> Optional[str]:
        pass

    @staticmethod
    @abstractmethod
    def get_api_base(api_base: Optional[str] = None) -> Optional[str]:
        pass

    @abstractmethod
    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        pass

    @staticmethod
    @abstractmethod
    def get_base_model(model: str) -> Optional[str]:
        """
        Returns the base model name from the given model name.

        Some providers like bedrock - can receive model=`invoke/anthropic.claude-3-opus-20240229-v1:0` or `converse/anthropic.claude-3-opus-20240229-v1:0`
            This function will return `anthropic.claude-3-opus-20240229-v1:0`
        """
        pass


def _convert_tool_response_to_message(
    tool_calls: List[ChatCompletionToolCallChunk],
) -> Optional[Message]:
    """
    In JSON mode, Anthropic API returns JSON schema as a tool call, we need to convert it to a message to follow the OpenAI format

    """
    ## HANDLE JSON MODE - anthropic returns single function call
    json_mode_content_str: Optional[str] = tool_calls[0]["function"].get("arguments")
    try:
        if json_mode_content_str is not None:
            args = json.loads(json_mode_content_str)
            if isinstance(args, dict) and (values := args.get("values")) is not None:
                _message = Message(content=json.dumps(values))
                return _message
            else:
                # a lot of the times the `values` key is not present in the tool response
                # relevant issue: https://github.com/BerriAI/litellm/issues/6741
                _message = Message(content=json.dumps(args))
                return _message
    except json.JSONDecodeError:
        # json decode error does occur, return the original tool response str
        return Message(content=json_mode_content_str)
    return None


def _dict_to_response_format_helper(
    response_format: dict, ref_template: Optional[str] = None
) -> dict:
    if ref_template is not None and response_format.get("type") == "json_schema":
        # Deep copy to avoid modifying original
        modified_format = copy.deepcopy(response_format)
        schema = modified_format["json_schema"]["schema"]

        # Update all $ref values in the schema
        def update_refs(schema):
            stack = [(schema, [])]
            visited = set()

            while stack:
                obj, path = stack.pop()
                obj_id = id(obj)

                if obj_id in visited:
                    continue
                visited.add(obj_id)

                if isinstance(obj, dict):
                    if "$ref" in obj:
                        ref_path = obj["$ref"]
                        model_name = ref_path.split("/")[-1]
                        obj["$ref"] = ref_template.format(model=model_name)

                    for k, v in obj.items():
                        if isinstance(v, (dict, list)):
                            stack.append((v, path + [k]))

                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            stack.append((item, path + [i]))

        update_refs(schema)
        return modified_format
    return response_format


def type_to_response_format_param(
    response_format: Optional[Union[Type[BaseModel], dict]],
    ref_template: Optional[str] = None,
) -> Optional[dict]:
    """
    Re-implementation of openai's 'type_to_response_format_param' function

    Used for converting pydantic object to api schema.
    """
    if response_format is None:
        return None

    if isinstance(response_format, dict):
        return _dict_to_response_format_helper(response_format, ref_template)

    # type checkers don't narrow the negation of a `TypeGuard` as it isn't
    # a safe default behaviour but we know that at this point the `response_format`
    # can only be a `type`
    if not _parsing._completions.is_basemodel_type(response_format):
        raise TypeError(f"Unsupported response_format type - {response_format}")

    if ref_template is not None:
        schema = response_format.model_json_schema(ref_template=ref_template)
    else:
        schema = _pydantic.to_strict_json_schema(response_format)

    return {
        "type": "json_schema",
        "json_schema": {
            "schema": schema,
            "name": response_format.__name__,
            "strict": True,
        },
    }


def map_developer_role_to_system_role(
    messages: List[AllMessageValues],
) -> List[AllMessageValues]:
    """
    Translate `developer` role to `system` role for non-OpenAI providers.
    """
    new_messages: List[AllMessageValues] = []
    for m in messages:
        if m["role"] == "developer":
            verbose_logger.debug(
                "Translating developer role to system role for non-OpenAI providers."
            )  # ensure user knows what's happening with their input.
            new_messages.append({"role": "system", "content": m["content"]})
        else:
            new_messages.append(m)
    return new_messages

# === NexusCore/openenv\Lib\site-packages\nltk\translate\gleu_score.py ===
# Natural Language Toolkit: GLEU Score
#
# Copyright (C) 2001-2024 NLTK Project
# Authors:
# Contributors: Mike Schuster, Michael Wayne Goodman, Liling Tan
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

""" GLEU score implementation. """

from collections import Counter

from nltk.util import everygrams, ngrams


def sentence_gleu(references, hypothesis, min_len=1, max_len=4):
    """
    Calculates the sentence level GLEU (Google-BLEU) score described in

        Yonghui Wu, Mike Schuster, Zhifeng Chen, Quoc V. Le, Mohammad Norouzi,
        Wolfgang Macherey, Maxim Krikun, Yuan Cao, Qin Gao, Klaus Macherey,
        Jeff Klingner, Apurva Shah, Melvin Johnson, Xiaobing Liu, Lukasz Kaiser,
        Stephan Gouws, Yoshikiyo Kato, Taku Kudo, Hideto Kazawa, Keith Stevens,
        George Kurian, Nishant Patil, Wei Wang, Cliff Young, Jason Smith,
        Jason Riesa, Alex Rudnick, Oriol Vinyals, Greg Corrado, Macduff Hughes,
        Jeffrey Dean. (2016) Google’s Neural Machine Translation System:
        Bridging the Gap between Human and Machine Translation.
        eprint arXiv:1609.08144. https://arxiv.org/pdf/1609.08144v2.pdf
        Retrieved on 27 Oct 2016.

    From Wu et al. (2016):
        "The BLEU score has some undesirable properties when used for single
         sentences, as it was designed to be a corpus measure. We therefore
         use a slightly different score for our RL experiments which we call
         the 'GLEU score'. For the GLEU score, we record all sub-sequences of
         1, 2, 3 or 4 tokens in output and target sequence (n-grams). We then
         compute a recall, which is the ratio of the number of matching n-grams
         to the number of total n-grams in the target (ground truth) sequence,
         and a precision, which is the ratio of the number of matching n-grams
         to the number of total n-grams in the generated output sequence. Then
         GLEU score is simply the minimum of recall and precision. This GLEU
         score's range is always between 0 (no matches) and 1 (all match) and
         it is symmetrical when switching output and target. According to
         our experiments, GLEU score correlates quite well with the BLEU
         metric on a corpus level but does not have its drawbacks for our per
         sentence reward objective."

    Note: The initial implementation only allowed a single reference, but now
          a list of references is required (which is consistent with
          bleu_score.sentence_bleu()).

    The infamous "the the the ... " example

        >>> ref = 'the cat is on the mat'.split()
        >>> hyp = 'the the the the the the the'.split()
        >>> sentence_gleu([ref], hyp)  # doctest: +ELLIPSIS
        0.0909...

    An example to evaluate normal machine translation outputs

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands').split()
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party').split()
        >>> hyp2 = str('It is to insure the troops forever hearing the activity '
        ...            'guidebook that party direct').split()
        >>> sentence_gleu([ref1], hyp1) # doctest: +ELLIPSIS
        0.4393...
        >>> sentence_gleu([ref1], hyp2) # doctest: +ELLIPSIS
        0.1206...

    :param references: a list of reference sentences
    :type references: list(list(str))
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :return: the sentence level GLEU score.
    :rtype: float
    """
    return corpus_gleu([references], [hypothesis], min_len=min_len, max_len=max_len)


def corpus_gleu(list_of_references, hypotheses, min_len=1, max_len=4):
    """
    Calculate a single corpus-level GLEU score (aka. system-level GLEU) for all
    the hypotheses and their respective references.

    Instead of averaging the sentence level GLEU scores (i.e. macro-average
    precision), Wu et al. (2016) sum up the matching tokens and the max of
    hypothesis and reference tokens for each sentence, then compute using the
    aggregate values.

    From Mike Schuster (via email):
        "For the corpus, we just add up the two statistics n_match and
         n_all = max(n_all_output, n_all_target) for all sentences, then
         calculate gleu_score = n_match / n_all, so it is not just a mean of
         the sentence gleu scores (in our case, longer sentences count more,
         which I think makes sense as they are more difficult to translate)."

    >>> hyp1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...         'ensures', 'that', 'the', 'military', 'always',
    ...         'obeys', 'the', 'commands', 'of', 'the', 'party']
    >>> ref1a = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...          'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...          'heed', 'Party', 'commands']
    >>> ref1b = ['It', 'is', 'the', 'guiding', 'principle', 'which',
    ...          'guarantees', 'the', 'military', 'forces', 'always',
    ...          'being', 'under', 'the', 'command', 'of', 'the', 'Party']
    >>> ref1c = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
    ...          'army', 'always', 'to', 'heed', 'the', 'directions',
    ...          'of', 'the', 'party']

    >>> hyp2 = ['he', 'read', 'the', 'book', 'because', 'he', 'was',
    ...         'interested', 'in', 'world', 'history']
    >>> ref2a = ['he', 'was', 'interested', 'in', 'world', 'history',
    ...          'because', 'he', 'read', 'the', 'book']

    >>> list_of_references = [[ref1a, ref1b, ref1c], [ref2a]]
    >>> hypotheses = [hyp1, hyp2]
    >>> corpus_gleu(list_of_references, hypotheses) # doctest: +ELLIPSIS
    0.5673...

    The example below show that corpus_gleu() is different from averaging
    sentence_gleu() for hypotheses

    >>> score1 = sentence_gleu([ref1a], hyp1)
    >>> score2 = sentence_gleu([ref2a], hyp2)
    >>> (score1 + score2) / 2 # doctest: +ELLIPSIS
    0.6144...

    :param list_of_references: a list of reference sentences, w.r.t. hypotheses
    :type list_of_references: list(list(list(str)))
    :param hypotheses: a list of hypothesis sentences
    :type hypotheses: list(list(str))
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :return: The corpus-level GLEU score.
    :rtype: float
    """
    # sanity check
    assert len(list_of_references) == len(
        hypotheses
    ), "The number of hypotheses and their reference(s) should be the same"

    # sum matches and max-token-lengths over all sentences
    corpus_n_match = 0
    corpus_n_all = 0

    for references, hypothesis in zip(list_of_references, hypotheses):
        hyp_ngrams = Counter(everygrams(hypothesis, min_len, max_len))
        tpfp = sum(hyp_ngrams.values())  # True positives + False positives.

        hyp_counts = []
        for reference in references:
            ref_ngrams = Counter(everygrams(reference, min_len, max_len))
            tpfn = sum(ref_ngrams.values())  # True positives + False negatives.

            overlap_ngrams = ref_ngrams & hyp_ngrams
            tp = sum(overlap_ngrams.values())  # True positives.

            # While GLEU is defined as the minimum of precision and
            # recall, we can reduce the number of division operations by one by
            # instead finding the maximum of the denominators for the precision
            # and recall formulae, since the numerators are the same:
            #     precision = tp / tpfp
            #     recall = tp / tpfn
            #     gleu_score = min(precision, recall) == tp / max(tpfp, tpfn)
            n_all = max(tpfp, tpfn)

            if n_all > 0:
                hyp_counts.append((tp, n_all))

        # use the reference yielding the highest score
        if hyp_counts:
            n_match, n_all = max(hyp_counts, key=lambda hc: hc[0] / hc[1])
            corpus_n_match += n_match
            corpus_n_all += n_all

    # corner case: empty corpus or empty references---don't divide by zero!
    if corpus_n_all == 0:
        gleu_score = 0.0
    else:
        gleu_score = corpus_n_match / corpus_n_all

    return gleu_score

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\key_binding\bindings\scroll.py ===
"""
Key bindings, for scrolling up and down through pages.

This are separate bindings, because GNU readline doesn't have them, but
they are very useful for navigating through long multiline buffers, like in
Vi, Emacs, etc...
"""

from __future__ import annotations

from prompt_toolkit.key_binding.key_processor import KeyPressEvent

__all__ = [
    "scroll_forward",
    "scroll_backward",
    "scroll_half_page_up",
    "scroll_half_page_down",
    "scroll_one_line_up",
    "scroll_one_line_down",
]

E = KeyPressEvent


def scroll_forward(event: E, half: bool = False) -> None:
    """
    Scroll window down.
    """
    w = event.app.layout.current_window
    b = event.app.current_buffer

    if w and w.render_info:
        info = w.render_info
        ui_content = info.ui_content

        # Height to scroll.
        scroll_height = info.window_height
        if half:
            scroll_height //= 2

        # Calculate how many lines is equivalent to that vertical space.
        y = b.document.cursor_position_row + 1
        height = 0
        while y < ui_content.line_count:
            line_height = info.get_height_for_line(y)

            if height + line_height < scroll_height:
                height += line_height
                y += 1
            else:
                break

        b.cursor_position = b.document.translate_row_col_to_index(y, 0)


def scroll_backward(event: E, half: bool = False) -> None:
    """
    Scroll window up.
    """
    w = event.app.layout.current_window
    b = event.app.current_buffer

    if w and w.render_info:
        info = w.render_info

        # Height to scroll.
        scroll_height = info.window_height
        if half:
            scroll_height //= 2

        # Calculate how many lines is equivalent to that vertical space.
        y = max(0, b.document.cursor_position_row - 1)
        height = 0
        while y > 0:
            line_height = info.get_height_for_line(y)

            if height + line_height < scroll_height:
                height += line_height
                y -= 1
            else:
                break

        b.cursor_position = b.document.translate_row_col_to_index(y, 0)


def scroll_half_page_down(event: E) -> None:
    """
    Same as ControlF, but only scroll half a page.
    """
    scroll_forward(event, half=True)


def scroll_half_page_up(event: E) -> None:
    """
    Same as ControlB, but only scroll half a page.
    """
    scroll_backward(event, half=True)


def scroll_one_line_down(event: E) -> None:
    """
    scroll_offset += 1
    """
    w = event.app.layout.current_window
    b = event.app.current_buffer

    if w:
        # When the cursor is at the top, move to the next line. (Otherwise, only scroll.)
        if w.render_info:
            info = w.render_info

            if w.vertical_scroll < info.content_height - info.window_height:
                if info.cursor_position.y <= info.configured_scroll_offsets.top:
                    b.cursor_position += b.document.get_cursor_down_position()

                w.vertical_scroll += 1


def scroll_one_line_up(event: E) -> None:
    """
    scroll_offset -= 1
    """
    w = event.app.layout.current_window
    b = event.app.current_buffer

    if w:
        # When the cursor is at the bottom, move to the previous line. (Otherwise, only scroll.)
        if w.render_info:
            info = w.render_info

            if w.vertical_scroll > 0:
                first_line_height = info.get_height_for_line(info.first_visible_line())

                cursor_up = info.cursor_position.y - (
                    info.window_height
                    - 1
                    - first_line_height
                    - info.configured_scroll_offsets.bottom
                )

                # Move cursor up, as many steps as the height of the first line.
                # TODO: not entirely correct yet, in case of line wrapping and many long lines.
                for _ in range(max(0, cursor_up)):
                    b.cursor_position += b.document.get_cursor_up_position()

                # Scroll window
                w.vertical_scroll -= 1


def scroll_page_down(event: E) -> None:
    """
    Scroll page down. (Prefer the cursor at the top of the page, after scrolling.)
    """
    w = event.app.layout.current_window
    b = event.app.current_buffer

    if w and w.render_info:
        # Scroll down one page.
        line_index = max(w.render_info.last_visible_line(), w.vertical_scroll + 1)
        w.vertical_scroll = line_index

        b.cursor_position = b.document.translate_row_col_to_index(line_index, 0)
        b.cursor_position += b.document.get_start_of_line_position(
            after_whitespace=True
        )


def scroll_page_up(event: E) -> None:
    """
    Scroll page up. (Prefer the cursor at the bottom of the page, after scrolling.)
    """
    w = event.app.layout.current_window
    b = event.app.current_buffer

    if w and w.render_info:
        # Put cursor at the first visible line. (But make sure that the cursor
        # moves at least one line up.)
        line_index = max(
            0,
            min(w.render_info.first_visible_line(), b.document.cursor_position_row - 1),
        )

        b.cursor_position = b.document.translate_row_col_to_index(line_index, 0)
        b.cursor_position += b.document.get_start_of_line_position(
            after_whitespace=True
        )

        # Set the scroll offset. We can safely set it to zero; the Window will
        # make sure that it scrolls at least until the cursor becomes visible.
        w.vertical_scroll = 0

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\scintilla\keycodes.py ===
import win32api
import win32con
import win32ui

MAPVK_VK_TO_CHAR = 2

key_name_to_vk = {}
key_code_to_name = {}

_better_names = {
    "escape": "esc",
    "return": "enter",
    "back": "pgup",
    "next": "pgdn",
}


def _fillvkmap():
    # Pull the VK_names from win32con
    names = [entry for entry in win32con.__dict__ if entry.startswith("VK_")]
    for name in names:
        code = getattr(win32con, name)
        n = name[3:].lower()
        key_name_to_vk[n] = code
        if n in _better_names:
            n = _better_names[n]
            key_name_to_vk[n] = code
        key_code_to_name[code] = n


_fillvkmap()


def get_vk(chardesc):
    if len(chardesc) == 1:
        # it is a character.
        info = win32api.VkKeyScan(chardesc)
        if info == -1:
            # Note: returning None, None causes an error when keyboard layout is non-English, see the report below
            # https://stackoverflow.com/questions/45138084/pythonwin-occasionally-gives-an-error-on-opening
            return 0, 0
        vk = win32api.LOBYTE(info)
        state = win32api.HIBYTE(info)
        modifiers = 0
        if state & 0x1:
            modifiers |= win32con.SHIFT_PRESSED
        if state & 0x2:
            modifiers |= win32con.LEFT_CTRL_PRESSED | win32con.RIGHT_CTRL_PRESSED
        if state & 0x4:
            modifiers |= win32con.LEFT_ALT_PRESSED | win32con.RIGHT_ALT_PRESSED
        return vk, modifiers
    # must be a 'key name'
    return key_name_to_vk.get(chardesc.lower()), 0


modifiers = {
    "alt": win32con.LEFT_ALT_PRESSED | win32con.RIGHT_ALT_PRESSED,
    "lalt": win32con.LEFT_ALT_PRESSED,
    "ralt": win32con.RIGHT_ALT_PRESSED,
    "ctrl": win32con.LEFT_CTRL_PRESSED | win32con.RIGHT_CTRL_PRESSED,
    "ctl": win32con.LEFT_CTRL_PRESSED | win32con.RIGHT_CTRL_PRESSED,
    "control": win32con.LEFT_CTRL_PRESSED | win32con.RIGHT_CTRL_PRESSED,
    "lctrl": win32con.LEFT_CTRL_PRESSED,
    "lctl": win32con.LEFT_CTRL_PRESSED,
    "rctrl": win32con.RIGHT_CTRL_PRESSED,
    "rctl": win32con.RIGHT_CTRL_PRESSED,
    "shift": win32con.SHIFT_PRESSED,
    "key": 0,  # ignore key tag.
}


def parse_key_name(name):
    name += "-"  # Add a sentinel
    start = pos = 0
    max = len(name)
    toks = []
    while pos < max:
        if name[pos] in "+-":
            tok = name[start:pos]
            # use the ascii lower() version of tok, so ascii chars require
            # an explicit shift modifier - ie 'Ctrl+G' should be treated as
            # 'ctrl+g' - 'ctrl+shift+g' would be needed if desired.
            # This is mainly to avoid changing all the old keystroke defs
            toks.append(tok.lower())
            pos += 1  # skip the sep
            start = pos
        pos += 1
    flags = 0
    # do the modifiers
    for tok in toks[:-1]:
        mod = modifiers.get(tok.lower())
        if mod is not None:
            flags |= mod
    # the key name
    vk, this_flags = get_vk(toks[-1])
    return vk, flags | this_flags


_checks = [
    [  # Shift
        ("Shift", win32con.SHIFT_PRESSED),
    ],
    [  # Ctrl key
        ("Ctrl", win32con.LEFT_CTRL_PRESSED | win32con.RIGHT_CTRL_PRESSED),
        ("LCtrl", win32con.LEFT_CTRL_PRESSED),
        ("RCtrl", win32con.RIGHT_CTRL_PRESSED),
    ],
    [  # Alt key
        ("Alt", win32con.LEFT_ALT_PRESSED | win32con.RIGHT_ALT_PRESSED),
        ("LAlt", win32con.LEFT_ALT_PRESSED),
        ("RAlt", win32con.RIGHT_ALT_PRESSED),
    ],
]


def make_key_name(vk, flags):
    # Check alt keys.
    flags_done = 0
    parts = []
    for moddata in _checks:
        for name, checkflag in moddata:
            if flags & checkflag:
                parts.append(name)
                flags_done &= checkflag
                break
    if flags_done & flags:
        parts.append(hex(flags & ~flags_done))
    # Now the key name.
    if vk is None:
        parts.append("<Unknown scan code>")
    else:
        try:
            parts.append(key_code_to_name[vk])
        except KeyError:
            # Not in our virtual key map - ask Windows what character this
            # key corresponds to.
            scancode = win32api.MapVirtualKey(vk, MAPVK_VK_TO_CHAR)
            parts.append(chr(scancode))
    sep = "+"
    if sep in parts:
        sep = "-"
    return sep.join([p.capitalize() for p in parts])


def _psc(char):
    sc, mods = get_vk(char)
    print(f"Char {char!r} -> {sc} -> {key_code_to_name.get(sc)}")


def test1():
    for ch in """aA0/?[{}];:'"`~_-+=\\|,<.>/?""":
        _psc(ch)
    for code in ["Home", "End", "Left", "Right", "Up", "Down", "Menu", "Next"]:
        _psc(code)


def _pkn(n):
    vk, flags = parse_key_name(n)
    print(f"{n} -> {vk},{flags} -> {make_key_name(vk, flags)}")


def test2():
    _pkn("ctrl+alt-shift+x")
    _pkn("ctrl-home")
    _pkn("Shift-+")
    _pkn("Shift--")
    _pkn("Shift+-")
    _pkn("Shift++")
    _pkn("LShift-+")
    _pkn("ctl+home")
    _pkn("ctl+enter")
    _pkn("alt+return")
    _pkn("Alt+/")
    _pkn("Alt+BadKeyName")
    _pkn("A")  # an ascii char - should be seen as 'a'
    _pkn("a")
    _pkn("Shift-A")
    _pkn("Shift-a")
    _pkn("a")
    _pkn("(")
    _pkn("Ctrl+(")
    _pkn("Ctrl+Shift-8")
    _pkn("Ctrl+*")
    _pkn("{")
    _pkn("!")
    _pkn(".")


if __name__ == "__main__":
    test2()

# === NexusCore/myenv\Lib\site-packages\pip\_internal\metadata\importlib\_envs.py ===
import functools
import importlib.metadata
import logging
import os
import pathlib
import sys
import zipfile
import zipimport
from typing import Iterator, List, Optional, Sequence, Set, Tuple

from pip._vendor.packaging.utils import NormalizedName, canonicalize_name

from pip._internal.metadata.base import BaseDistribution, BaseEnvironment
from pip._internal.models.wheel import Wheel
from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.filetypes import WHEEL_EXTENSION

from ._compat import BadMetadata, BasePath, get_dist_canonical_name, get_info_location
from ._dists import Distribution

logger = logging.getLogger(__name__)


def _looks_like_wheel(location: str) -> bool:
    if not location.endswith(WHEEL_EXTENSION):
        return False
    if not os.path.isfile(location):
        return False
    if not Wheel.wheel_file_re.match(os.path.basename(location)):
        return False
    return zipfile.is_zipfile(location)


class _DistributionFinder:
    """Finder to locate distributions.

    The main purpose of this class is to memoize found distributions' names, so
    only one distribution is returned for each package name. At lot of pip code
    assumes this (because it is setuptools's behavior), and not doing the same
    can potentially cause a distribution in lower precedence path to override a
    higher precedence one if the caller is not careful.

    Eventually we probably want to make it possible to see lower precedence
    installations as well. It's useful feature, after all.
    """

    FoundResult = Tuple[importlib.metadata.Distribution, Optional[BasePath]]

    def __init__(self) -> None:
        self._found_names: Set[NormalizedName] = set()

    def _find_impl(self, location: str) -> Iterator[FoundResult]:
        """Find distributions in a location."""
        # Skip looking inside a wheel. Since a package inside a wheel is not
        # always valid (due to .data directories etc.), its .dist-info entry
        # should not be considered an installed distribution.
        if _looks_like_wheel(location):
            return
        # To know exactly where we find a distribution, we have to feed in the
        # paths one by one, instead of dumping the list to importlib.metadata.
        for dist in importlib.metadata.distributions(path=[location]):
            info_location = get_info_location(dist)
            try:
                name = get_dist_canonical_name(dist)
            except BadMetadata as e:
                logger.warning("Skipping %s due to %s", info_location, e.reason)
                continue
            if name in self._found_names:
                continue
            self._found_names.add(name)
            yield dist, info_location

    def find(self, location: str) -> Iterator[BaseDistribution]:
        """Find distributions in a location.

        The path can be either a directory, or a ZIP archive.
        """
        for dist, info_location in self._find_impl(location):
            if info_location is None:
                installed_location: Optional[BasePath] = None
            else:
                installed_location = info_location.parent
            yield Distribution(dist, info_location, installed_location)

    def find_linked(self, location: str) -> Iterator[BaseDistribution]:
        """Read location in egg-link files and return distributions in there.

        The path should be a directory; otherwise this returns nothing. This
        follows how setuptools does this for compatibility. The first non-empty
        line in the egg-link is read as a path (resolved against the egg-link's
        containing directory if relative). Distributions found at that linked
        location are returned.
        """
        path = pathlib.Path(location)
        if not path.is_dir():
            return
        for child in path.iterdir():
            if child.suffix != ".egg-link":
                continue
            with child.open() as f:
                lines = (line.strip() for line in f)
                target_rel = next((line for line in lines if line), "")
            if not target_rel:
                continue
            target_location = str(path.joinpath(target_rel))
            for dist, info_location in self._find_impl(target_location):
                yield Distribution(dist, info_location, path)

    def _find_eggs_in_dir(self, location: str) -> Iterator[BaseDistribution]:
        from pip._vendor.pkg_resources import find_distributions

        from pip._internal.metadata import pkg_resources as legacy

        with os.scandir(location) as it:
            for entry in it:
                if not entry.name.endswith(".egg"):
                    continue
                for dist in find_distributions(entry.path):
                    yield legacy.Distribution(dist)

    def _find_eggs_in_zip(self, location: str) -> Iterator[BaseDistribution]:
        from pip._vendor.pkg_resources import find_eggs_in_zip

        from pip._internal.metadata import pkg_resources as legacy

        try:
            importer = zipimport.zipimporter(location)
        except zipimport.ZipImportError:
            return
        for dist in find_eggs_in_zip(importer, location):
            yield legacy.Distribution(dist)

    def find_eggs(self, location: str) -> Iterator[BaseDistribution]:
        """Find eggs in a location.

        This actually uses the old *pkg_resources* backend. We likely want to
        deprecate this so we can eventually remove the *pkg_resources*
        dependency entirely. Before that, this should first emit a deprecation
        warning for some versions when using the fallback since importing
        *pkg_resources* is slow for those who don't need it.
        """
        if os.path.isdir(location):
            yield from self._find_eggs_in_dir(location)
        if zipfile.is_zipfile(location):
            yield from self._find_eggs_in_zip(location)


@functools.lru_cache(maxsize=None)  # Warn a distribution exactly once.
def _emit_egg_deprecation(location: Optional[str]) -> None:
    deprecated(
        reason=f"Loading egg at {location} is deprecated.",
        replacement="to use pip for package installation",
        gone_in="25.1",
        issue=12330,
    )


class Environment(BaseEnvironment):
    def __init__(self, paths: Sequence[str]) -> None:
        self._paths = paths

    @classmethod
    def default(cls) -> BaseEnvironment:
        return cls(sys.path)

    @classmethod
    def from_paths(cls, paths: Optional[List[str]]) -> BaseEnvironment:
        if paths is None:
            return cls(sys.path)
        return cls(paths)

    def _iter_distributions(self) -> Iterator[BaseDistribution]:
        finder = _DistributionFinder()
        for location in self._paths:
            yield from finder.find(location)
            for dist in finder.find_eggs(location):
                _emit_egg_deprecation(dist.location)
                yield dist
            # This must go last because that's how pkg_resources tie-breaks.
            yield from finder.find_linked(location)

    def get_distribution(self, name: str) -> Optional[BaseDistribution]:
        canonical_name = canonicalize_name(name)
        matches = (
            distribution
            for distribution in self.iter_all_distributions()
            if distribution.canonical_name == canonical_name
        )
        return next(matches, None)

# === NexusCore/openenv\Lib\site-packages\pydantic\errors.py ===
"""Pydantic-specific errors."""

from __future__ import annotations as _annotations

import re
from typing import Any, ClassVar, Literal

from typing_extensions import Self
from typing_inspection.introspection import Qualifier

from pydantic._internal import _repr

from ._migration import getattr_migration
from .version import version_short

__all__ = (
    'PydanticUserError',
    'PydanticUndefinedAnnotation',
    'PydanticImportError',
    'PydanticSchemaGenerationError',
    'PydanticInvalidForJsonSchema',
    'PydanticForbiddenQualifier',
    'PydanticErrorCodes',
)

# We use this URL to allow for future flexibility about how we host the docs, while allowing for Pydantic
# code in the while with "old" URLs to still work.
# 'u' refers to "user errors" - e.g. errors caused by developers using pydantic, as opposed to validation errors.
DEV_ERROR_DOCS_URL = f'https://errors.pydantic.dev/{version_short()}/u/'
PydanticErrorCodes = Literal[
    'class-not-fully-defined',
    'custom-json-schema',
    'decorator-missing-field',
    'discriminator-no-field',
    'discriminator-alias-type',
    'discriminator-needs-literal',
    'discriminator-alias',
    'discriminator-validator',
    'callable-discriminator-no-tag',
    'typed-dict-version',
    'model-field-overridden',
    'model-field-missing-annotation',
    'config-both',
    'removed-kwargs',
    'circular-reference-schema',
    'invalid-for-json-schema',
    'json-schema-already-used',
    'base-model-instantiated',
    'undefined-annotation',
    'schema-for-unknown-type',
    'import-error',
    'create-model-field-definitions',
    'validator-no-fields',
    'validator-invalid-fields',
    'validator-instance-method',
    'validator-input-type',
    'root-validator-pre-skip',
    'model-serializer-instance-method',
    'validator-field-config-info',
    'validator-v1-signature',
    'validator-signature',
    'field-serializer-signature',
    'model-serializer-signature',
    'multiple-field-serializers',
    'invalid-annotated-type',
    'type-adapter-config-unused',
    'root-model-extra',
    'unevaluable-type-annotation',
    'dataclass-init-false-extra-allow',
    'clashing-init-and-init-var',
    'model-config-invalid-field-name',
    'with-config-on-model',
    'dataclass-on-model',
    'validate-call-type',
    'unpack-typed-dict',
    'overlapping-unpack-typed-dict',
    'invalid-self-type',
    'validate-by-alias-and-name-false',
]


class PydanticErrorMixin:
    """A mixin class for common functionality shared by all Pydantic-specific errors.

    Attributes:
        message: A message describing the error.
        code: An optional error code from PydanticErrorCodes enum.
    """

    def __init__(self, message: str, *, code: PydanticErrorCodes | None) -> None:
        self.message = message
        self.code = code

    def __str__(self) -> str:
        if self.code is None:
            return self.message
        else:
            return f'{self.message}\n\nFor further information visit {DEV_ERROR_DOCS_URL}{self.code}'


class PydanticUserError(PydanticErrorMixin, TypeError):
    """An error raised due to incorrect use of Pydantic."""


class PydanticUndefinedAnnotation(PydanticErrorMixin, NameError):
    """A subclass of `NameError` raised when handling undefined annotations during `CoreSchema` generation.

    Attributes:
        name: Name of the error.
        message: Description of the error.
    """

    def __init__(self, name: str, message: str) -> None:
        self.name = name
        super().__init__(message=message, code='undefined-annotation')

    @classmethod
    def from_name_error(cls, name_error: NameError) -> Self:
        """Convert a `NameError` to a `PydanticUndefinedAnnotation` error.

        Args:
            name_error: `NameError` to be converted.

        Returns:
            Converted `PydanticUndefinedAnnotation` error.
        """
        try:
            name = name_error.name  # type: ignore  # python > 3.10
        except AttributeError:
            name = re.search(r".*'(.+?)'", str(name_error)).group(1)  # type: ignore[union-attr]
        return cls(name=name, message=str(name_error))


class PydanticImportError(PydanticErrorMixin, ImportError):
    """An error raised when an import fails due to module changes between V1 and V2.

    Attributes:
        message: Description of the error.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, code='import-error')


class PydanticSchemaGenerationError(PydanticUserError):
    """An error raised during failures to generate a `CoreSchema` for some type.

    Attributes:
        message: Description of the error.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, code='schema-for-unknown-type')


class PydanticInvalidForJsonSchema(PydanticUserError):
    """An error raised during failures to generate a JSON schema for some `CoreSchema`.

    Attributes:
        message: Description of the error.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, code='invalid-for-json-schema')


class PydanticForbiddenQualifier(PydanticUserError):
    """An error raised if a forbidden type qualifier is found in a type annotation."""

    _qualifier_repr_map: ClassVar[dict[Qualifier, str]] = {
        'required': 'typing.Required',
        'not_required': 'typing.NotRequired',
        'read_only': 'typing.ReadOnly',
        'class_var': 'typing.ClassVar',
        'init_var': 'dataclasses.InitVar',
        'final': 'typing.Final',
    }

    def __init__(self, qualifier: Qualifier, annotation: Any) -> None:
        super().__init__(
            message=(
                f'The annotation {_repr.display_as_type(annotation)!r} contains the {self._qualifier_repr_map[qualifier]!r} '
                f'type qualifier, which is invalid in the context it is defined.'
            ),
            code=None,
        )


__getattr__ = getattr_migration(__name__)

# === NexusCore/openenv\Lib\site-packages\wsproto\connection.py ===
"""
wsproto/connection
~~~~~~~~~~~~~~~~~~

An implementation of a WebSocket connection.
"""

from collections import deque
from enum import Enum
from typing import Deque, Generator, List, Optional

from .events import (
    BytesMessage,
    CloseConnection,
    Event,
    Message,
    Ping,
    Pong,
    TextMessage,
)
from .extensions import Extension
from .frame_protocol import CloseReason, FrameProtocol, Opcode, ParseFailed
from .utilities import LocalProtocolError


class ConnectionState(Enum):
    """
    RFC 6455, Section 4 - Opening Handshake
    """

    #: The opening handshake is in progress.
    CONNECTING = 0
    #: The opening handshake is complete.
    OPEN = 1
    #: The remote WebSocket has initiated a connection close.
    REMOTE_CLOSING = 2
    #: The local WebSocket (i.e. this instance) has initiated a connection close.
    LOCAL_CLOSING = 3
    #: The closing handshake has completed.
    CLOSED = 4
    #: The connection was rejected during the opening handshake.
    REJECTING = 5


class ConnectionType(Enum):
    """An enumeration of connection types."""

    #: This connection will act as client and talk to a remote server
    CLIENT = 1

    #: This connection will as as server and waits for client connections
    SERVER = 2


CLIENT = ConnectionType.CLIENT
SERVER = ConnectionType.SERVER


class Connection:
    """
    A low-level WebSocket connection object.

    This wraps two other protocol objects, an HTTP/1.1 protocol object used
    to do the initial HTTP upgrade handshake and a WebSocket frame protocol
    object used to exchange messages and other control frames.

    :param conn_type: Whether this object is on the client- or server-side of
        a connection. To initialise as a client pass ``CLIENT`` otherwise
        pass ``SERVER``.
    :type conn_type: ``ConnectionType``
    """

    def __init__(
        self,
        connection_type: ConnectionType,
        extensions: Optional[List[Extension]] = None,
        trailing_data: bytes = b"",
    ) -> None:
        self.client = connection_type is ConnectionType.CLIENT
        self._events: Deque[Event] = deque()
        self._proto = FrameProtocol(self.client, extensions or [])
        self._state = ConnectionState.OPEN
        self.receive_data(trailing_data)

    @property
    def state(self) -> ConnectionState:
        return self._state

    def send(self, event: Event) -> bytes:
        data = b""
        if isinstance(event, Message) and self.state == ConnectionState.OPEN:
            data += self._proto.send_data(event.data, event.message_finished)
        elif isinstance(event, Ping) and self.state == ConnectionState.OPEN:
            data += self._proto.ping(event.payload)
        elif isinstance(event, Pong) and self.state == ConnectionState.OPEN:
            data += self._proto.pong(event.payload)
        elif isinstance(event, CloseConnection) and self.state in {
            ConnectionState.OPEN,
            ConnectionState.REMOTE_CLOSING,
        }:
            data += self._proto.close(event.code, event.reason)
            if self.state == ConnectionState.REMOTE_CLOSING:
                self._state = ConnectionState.CLOSED
            else:
                self._state = ConnectionState.LOCAL_CLOSING
        else:
            raise LocalProtocolError(
                f"Event {event} cannot be sent in state {self.state}."
            )
        return data

    def receive_data(self, data: Optional[bytes]) -> None:
        """
        Pass some received data to the connection for handling.

        A list of events that the remote peer triggered by sending this data can
        be retrieved with :meth:`~wsproto.connection.Connection.events`.

        :param data: The data received from the remote peer on the network.
        :type data: ``bytes``
        """

        if data is None:
            # "If _The WebSocket Connection is Closed_ and no Close control
            # frame was received by the endpoint (such as could occur if the
            # underlying transport connection is lost), _The WebSocket
            # Connection Close Code_ is considered to be 1006."
            self._events.append(CloseConnection(code=CloseReason.ABNORMAL_CLOSURE))
            self._state = ConnectionState.CLOSED
            return

        if self.state in (ConnectionState.OPEN, ConnectionState.LOCAL_CLOSING):
            self._proto.receive_bytes(data)
        elif self.state is ConnectionState.CLOSED:
            raise LocalProtocolError("Connection already closed.")
        else:
            pass  # pragma: no cover

    def events(self) -> Generator[Event, None, None]:
        """
        Return a generator that provides any events that have been generated
        by protocol activity.

        :returns: generator of :class:`Event <wsproto.events.Event>` subclasses
        """
        while self._events:
            yield self._events.popleft()

        try:
            for frame in self._proto.received_frames():
                if frame.opcode is Opcode.PING:
                    assert frame.frame_finished and frame.message_finished
                    assert isinstance(frame.payload, (bytes, bytearray))
                    yield Ping(payload=frame.payload)

                elif frame.opcode is Opcode.PONG:
                    assert frame.frame_finished and frame.message_finished
                    assert isinstance(frame.payload, (bytes, bytearray))
                    yield Pong(payload=frame.payload)

                elif frame.opcode is Opcode.CLOSE:
                    assert isinstance(frame.payload, tuple)
                    code, reason = frame.payload
                    if self.state is ConnectionState.LOCAL_CLOSING:
                        self._state = ConnectionState.CLOSED
                    else:
                        self._state = ConnectionState.REMOTE_CLOSING
                    yield CloseConnection(code=code, reason=reason)

                elif frame.opcode is Opcode.TEXT:
                    assert isinstance(frame.payload, str)
                    yield TextMessage(
                        data=frame.payload,
                        frame_finished=frame.frame_finished,
                        message_finished=frame.message_finished,
                    )

                elif frame.opcode is Opcode.BINARY:
                    assert isinstance(frame.payload, (bytes, bytearray))
                    yield BytesMessage(
                        data=frame.payload,
                        frame_finished=frame.frame_finished,
                        message_finished=frame.message_finished,
                    )

                else:
                    pass  # pragma: no cover
        except ParseFailed as exc:
            yield CloseConnection(code=exc.code, reason=str(exc))

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\_backend_pdf_ps.py ===
"""
Common functionality between the PDF and PS backends.
"""

from io import BytesIO
import functools
import logging

from fontTools import subset

import matplotlib as mpl
from .. import font_manager, ft2font
from .._afm import AFM
from ..backend_bases import RendererBase


@functools.lru_cache(50)
def _cached_get_afm_from_fname(fname):
    with open(fname, "rb") as fh:
        return AFM(fh)


def get_glyphs_subset(fontfile, characters):
    """
    Subset a TTF font

    Reads the named fontfile and restricts the font to the characters.

    Parameters
    ----------
    fontfile : str
        Path to the font file
    characters : str
        Continuous set of characters to include in subset

    Returns
    -------
    fontTools.ttLib.ttFont.TTFont
        An open font object representing the subset, which needs to
        be closed by the caller.
    """

    options = subset.Options(glyph_names=True, recommended_glyphs=True)

    # Prevent subsetting extra tables.
    options.drop_tables += [
        'FFTM',  # FontForge Timestamp.
        'PfEd',  # FontForge personal table.
        'BDF',  # X11 BDF header.
        'meta',  # Metadata stores design/supported languages (meaningless for subsets).
        'MERG',  # Merge Table.
        'TSIV',  # Microsoft Visual TrueType extension.
        'Zapf',  # Information about the individual glyphs in the font.
        'bdat',  # The bitmap data table.
        'bloc',  # The bitmap location table.
        'cidg',  # CID to Glyph ID table (Apple Advanced Typography).
        'fdsc',  # The font descriptors table.
        'feat',  # Feature name table (Apple Advanced Typography).
        'fmtx',  # The Font Metrics Table.
        'fond',  # Data-fork font information (Apple Advanced Typography).
        'just',  # The justification table (Apple Advanced Typography).
        'kerx',  # An extended kerning table (Apple Advanced Typography).
        'ltag',  # Language Tag.
        'morx',  # Extended Glyph Metamorphosis Table.
        'trak',  # Tracking table.
        'xref',  # The cross-reference table (some Apple font tooling information).
    ]
    # if fontfile is a ttc, specify font number
    if fontfile.endswith(".ttc"):
        options.font_number = 0

    font = subset.load_font(fontfile, options)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=characters)
    subsetter.subset(font)
    return font


def font_as_file(font):
    """
    Convert a TTFont object into a file-like object.

    Parameters
    ----------
    font : fontTools.ttLib.ttFont.TTFont
        A font object

    Returns
    -------
    BytesIO
        A file object with the font saved into it
    """
    fh = BytesIO()
    font.save(fh, reorderTables=False)
    return fh


class CharacterTracker:
    """
    Helper for font subsetting by the pdf and ps backends.

    Maintains a mapping of font paths to the set of character codepoints that
    are being used from that font.
    """

    def __init__(self):
        self.used = {}

    def track(self, font, s):
        """Record that string *s* is being typeset using font *font*."""
        char_to_font = font._get_fontmap(s)
        for _c, _f in char_to_font.items():
            self.used.setdefault(_f.fname, set()).add(ord(_c))

    def track_glyph(self, font, glyph):
        """Record that codepoint *glyph* is being typeset using font *font*."""
        self.used.setdefault(font.fname, set()).add(glyph)


class RendererPDFPSBase(RendererBase):
    # The following attributes must be defined by the subclasses:
    # - _afm_font_dir
    # - _use_afm_rc_name

    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height

    def flipy(self):
        # docstring inherited
        return False  # y increases from bottom to top.

    def option_scale_image(self):
        # docstring inherited
        return True  # PDF and PS support arbitrary image scaling.

    def option_image_nocomposite(self):
        # docstring inherited
        # Decide whether to composite image based on rcParam value.
        return not mpl.rcParams["image.composite_image"]

    def get_canvas_width_height(self):
        # docstring inherited
        return self.width * 72.0, self.height * 72.0

    def get_text_width_height_descent(self, s, prop, ismath):
        # docstring inherited
        if ismath == "TeX":
            return super().get_text_width_height_descent(s, prop, ismath)
        elif ismath:
            parse = self._text2path.mathtext_parser.parse(s, 72, prop)
            return parse.width, parse.height, parse.depth
        elif mpl.rcParams[self._use_afm_rc_name]:
            font = self._get_font_afm(prop)
            l, b, w, h, d = font.get_str_bbox_and_descent(s)
            scale = prop.get_size_in_points() / 1000
            w *= scale
            h *= scale
            d *= scale
            return w, h, d
        else:
            font = self._get_font_ttf(prop)
            font.set_text(s, 0.0, flags=ft2font.LoadFlags.NO_HINTING)
            w, h = font.get_width_height()
            d = font.get_descent()
            scale = 1 / 64
            w *= scale
            h *= scale
            d *= scale
            return w, h, d

    def _get_font_afm(self, prop):
        fname = font_manager.findfont(
            prop, fontext="afm", directory=self._afm_font_dir)
        return _cached_get_afm_from_fname(fname)

    def _get_font_ttf(self, prop):
        fnames = font_manager.fontManager._find_fonts_by_props(prop)
        try:
            font = font_manager.get_font(fnames)
            font.clear()
            font.set_size(prop.get_size_in_points(), 72)
            return font
        except RuntimeError:
            logging.getLogger(__name__).warning(
                "The PostScript/PDF backend does not currently "
                "support the selected font (%s).", fnames)
            raise

# === NexusCore/openenv\Lib\site-packages\pip\_internal\metadata\importlib\_envs.py ===
import functools
import importlib.metadata
import logging
import os
import pathlib
import sys
import zipfile
import zipimport
from typing import Iterator, List, Optional, Sequence, Set, Tuple

from pip._vendor.packaging.utils import NormalizedName, canonicalize_name

from pip._internal.metadata.base import BaseDistribution, BaseEnvironment
from pip._internal.models.wheel import Wheel
from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.filetypes import WHEEL_EXTENSION

from ._compat import BadMetadata, BasePath, get_dist_canonical_name, get_info_location
from ._dists import Distribution

logger = logging.getLogger(__name__)


def _looks_like_wheel(location: str) -> bool:
    if not location.endswith(WHEEL_EXTENSION):
        return False
    if not os.path.isfile(location):
        return False
    if not Wheel.wheel_file_re.match(os.path.basename(location)):
        return False
    return zipfile.is_zipfile(location)


class _DistributionFinder:
    """Finder to locate distributions.

    The main purpose of this class is to memoize found distributions' names, so
    only one distribution is returned for each package name. At lot of pip code
    assumes this (because it is setuptools's behavior), and not doing the same
    can potentially cause a distribution in lower precedence path to override a
    higher precedence one if the caller is not careful.

    Eventually we probably want to make it possible to see lower precedence
    installations as well. It's useful feature, after all.
    """

    FoundResult = Tuple[importlib.metadata.Distribution, Optional[BasePath]]

    def __init__(self) -> None:
        self._found_names: Set[NormalizedName] = set()

    def _find_impl(self, location: str) -> Iterator[FoundResult]:
        """Find distributions in a location."""
        # Skip looking inside a wheel. Since a package inside a wheel is not
        # always valid (due to .data directories etc.), its .dist-info entry
        # should not be considered an installed distribution.
        if _looks_like_wheel(location):
            return
        # To know exactly where we find a distribution, we have to feed in the
        # paths one by one, instead of dumping the list to importlib.metadata.
        for dist in importlib.metadata.distributions(path=[location]):
            info_location = get_info_location(dist)
            try:
                name = get_dist_canonical_name(dist)
            except BadMetadata as e:
                logger.warning("Skipping %s due to %s", info_location, e.reason)
                continue
            if name in self._found_names:
                continue
            self._found_names.add(name)
            yield dist, info_location

    def find(self, location: str) -> Iterator[BaseDistribution]:
        """Find distributions in a location.

        The path can be either a directory, or a ZIP archive.
        """
        for dist, info_location in self._find_impl(location):
            if info_location is None:
                installed_location: Optional[BasePath] = None
            else:
                installed_location = info_location.parent
            yield Distribution(dist, info_location, installed_location)

    def find_linked(self, location: str) -> Iterator[BaseDistribution]:
        """Read location in egg-link files and return distributions in there.

        The path should be a directory; otherwise this returns nothing. This
        follows how setuptools does this for compatibility. The first non-empty
        line in the egg-link is read as a path (resolved against the egg-link's
        containing directory if relative). Distributions found at that linked
        location are returned.
        """
        path = pathlib.Path(location)
        if not path.is_dir():
            return
        for child in path.iterdir():
            if child.suffix != ".egg-link":
                continue
            with child.open() as f:
                lines = (line.strip() for line in f)
                target_rel = next((line for line in lines if line), "")
            if not target_rel:
                continue
            target_location = str(path.joinpath(target_rel))
            for dist, info_location in self._find_impl(target_location):
                yield Distribution(dist, info_location, path)

    def _find_eggs_in_dir(self, location: str) -> Iterator[BaseDistribution]:
        from pip._vendor.pkg_resources import find_distributions

        from pip._internal.metadata import pkg_resources as legacy

        with os.scandir(location) as it:
            for entry in it:
                if not entry.name.endswith(".egg"):
                    continue
                for dist in find_distributions(entry.path):
                    yield legacy.Distribution(dist)

    def _find_eggs_in_zip(self, location: str) -> Iterator[BaseDistribution]:
        from pip._vendor.pkg_resources import find_eggs_in_zip

        from pip._internal.metadata import pkg_resources as legacy

        try:
            importer = zipimport.zipimporter(location)
        except zipimport.ZipImportError:
            return
        for dist in find_eggs_in_zip(importer, location):
            yield legacy.Distribution(dist)

    def find_eggs(self, location: str) -> Iterator[BaseDistribution]:
        """Find eggs in a location.

        This actually uses the old *pkg_resources* backend. We likely want to
        deprecate this so we can eventually remove the *pkg_resources*
        dependency entirely. Before that, this should first emit a deprecation
        warning for some versions when using the fallback since importing
        *pkg_resources* is slow for those who don't need it.
        """
        if os.path.isdir(location):
            yield from self._find_eggs_in_dir(location)
        if zipfile.is_zipfile(location):
            yield from self._find_eggs_in_zip(location)


@functools.lru_cache(maxsize=None)  # Warn a distribution exactly once.
def _emit_egg_deprecation(location: Optional[str]) -> None:
    deprecated(
        reason=f"Loading egg at {location} is deprecated.",
        replacement="to use pip for package installation",
        gone_in="25.1",
        issue=12330,
    )


class Environment(BaseEnvironment):
    def __init__(self, paths: Sequence[str]) -> None:
        self._paths = paths

    @classmethod
    def default(cls) -> BaseEnvironment:
        return cls(sys.path)

    @classmethod
    def from_paths(cls, paths: Optional[List[str]]) -> BaseEnvironment:
        if paths is None:
            return cls(sys.path)
        return cls(paths)

    def _iter_distributions(self) -> Iterator[BaseDistribution]:
        finder = _DistributionFinder()
        for location in self._paths:
            yield from finder.find(location)
            for dist in finder.find_eggs(location):
                _emit_egg_deprecation(dist.location)
                yield dist
            # This must go last because that's how pkg_resources tie-breaks.
            yield from finder.find_linked(location)

    def get_distribution(self, name: str) -> Optional[BaseDistribution]:
        canonical_name = canonicalize_name(name)
        matches = (
            distribution
            for distribution in self.iter_all_distributions()
            if distribution.canonical_name == canonical_name
        )
        return next(matches, None)

# === NexusCore/openenv\Lib\site-packages\proto\marshal\collections\repeated.py ===
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import copy
from typing import Iterable

from proto.utils import cached_property


class Repeated(collections.abc.MutableSequence):
    """A view around a mutable sequence in protocol buffers.

    This implements the full Python MutableSequence interface, but all methods
    modify the underlying field container directly.
    """

    def __init__(self, sequence, *, marshal, proto_type=None):
        """Initialize a wrapper around a protobuf repeated field.

        Args:
            sequence: A protocol buffers repeated field.
            marshal (~.MarshalRegistry): An instantiated marshal, used to
                convert values going to and from this map.
        """
        self._pb = sequence
        self._marshal = marshal
        self._proto_type = proto_type

    def __copy__(self):
        """Copy this object and return the copy."""
        return type(self)(self.pb[:], marshal=self._marshal)

    def __delitem__(self, key):
        """Delete the given item."""
        del self.pb[key]

    def __eq__(self, other):
        if hasattr(other, "pb"):
            return tuple(self.pb) == tuple(other.pb)
        return tuple(self.pb) == tuple(other) if isinstance(other, Iterable) else False

    def __getitem__(self, key):
        """Return the given item."""
        return self.pb[key]

    def __len__(self):
        """Return the length of the sequence."""
        return len(self.pb)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return repr([*self])

    def __setitem__(self, key, value):
        self.pb[key] = value

    def insert(self, index: int, value):
        """Insert ``value`` in the sequence before ``index``."""
        self.pb.insert(index, value)

    def sort(self, *, key: str = None, reverse: bool = False):
        """Stable sort *IN PLACE*."""
        self.pb.sort(key=key, reverse=reverse)

    @property
    def pb(self):
        return self._pb


class RepeatedComposite(Repeated):
    """A view around a mutable sequence of messages in protocol buffers.

    This implements the full Python MutableSequence interface, but all methods
    modify the underlying field container directly.
    """

    @cached_property
    def _pb_type(self):
        """Return the protocol buffer type for this sequence."""
        # Provide the marshal-given proto_type, if any.
        # Used for RepeatedComposite of Enum.
        if self._proto_type is not None:
            return self._proto_type

        # There is no public-interface mechanism to determine the type
        # of what should go in the list (and the C implementation seems to
        # have no exposed mechanism at all).
        #
        # If the list has members, use the existing list members to
        # determine the type.
        if len(self.pb) > 0:
            return type(self.pb[0])

        # We have no members in the list, so we get the type from the attributes.
        if hasattr(self.pb, "_message_descriptor") and hasattr(
            self.pb._message_descriptor, "_concrete_class"
        ):
            return self.pb._message_descriptor._concrete_class

        # Fallback logic in case attributes are not available
        # In order to get the type, we create a throw-away copy and add a
        # blank member to it.
        canary = copy.deepcopy(self.pb).add()
        return type(canary)

    def __eq__(self, other):
        if super().__eq__(other):
            return True
        return (
            tuple([i for i in self]) == tuple(other)
            if isinstance(other, Iterable)
            else False
        )

    def __getitem__(self, key):
        return self._marshal.to_python(self._pb_type, self.pb[key])

    def __setitem__(self, key, value):
        # The underlying protocol buffer does not define __setitem__, so we
        # have to implement all the operations on our own.

        # If ``key`` is an integer, as in list[index] = value:
        if isinstance(key, int):
            if -len(self) <= key < len(self):
                self.pop(key)  # Delete the old item.
                self.insert(key, value)  # Insert the new item in its place.
            else:
                raise IndexError("list assignment index out of range")

        # If ``key`` is a slice object, as in list[start:stop:step] = [values]:
        elif isinstance(key, slice):
            start, stop, step = key.indices(len(self))

            if not isinstance(value, collections.abc.Iterable):
                raise TypeError("can only assign an iterable")

            if step == 1:  # Is not an extended slice.
                # Assign all the new values to the sliced part, replacing the
                # old values, if any, and unconditionally inserting those
                # values whose indices already exceed the slice length.
                for index, item in enumerate(value):
                    if start + index < stop:
                        self.pop(start + index)
                    self.insert(start + index, item)

                # If there are less values than the length of the slice, remove
                # the remaining elements so that the slice adapts to the
                # newly provided values.
                for _ in range(stop - start - len(value)):
                    self.pop(start + len(value))

            else:  # Is an extended slice.
                indices = range(start, stop, step)

                if len(value) != len(indices):  # XXX: Use PEP 572 on 3.8+
                    raise ValueError(
                        f"attempt to assign sequence of size "
                        f"{len(value)} to extended slice of size "
                        f"{len(indices)}"
                    )

                # Assign each value to its index, calling this function again
                # with individual integer indexes that get processed above.
                for index, item in zip(indices, value):
                    self[index] = item

        else:
            raise TypeError(
                f"list indices must be integers or slices, not {type(key).__name__}"
            )

    def insert(self, index: int, value):
        """Insert ``value`` in the sequence before ``index``."""
        pb_value = self._marshal.to_proto(self._pb_type, value)
        self.pb.insert(index, pb_value)

# === NexusCore/openenv\Lib\site-packages\pyasn1\type\useful.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import datetime

from pyasn1 import error
from pyasn1.type import char
from pyasn1.type import tag
from pyasn1.type import univ

__all__ = ['ObjectDescriptor', 'GeneralizedTime', 'UTCTime']

NoValue = univ.NoValue
noValue = univ.noValue


class ObjectDescriptor(char.GraphicString):
    __doc__ = char.GraphicString.__doc__

    #: Default :py:class:`~pyasn1.type.tag.TagSet` object for |ASN.1| objects
    tagSet = char.GraphicString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 7)
    )

    # Optimization for faster codec lookup
    typeId = char.GraphicString.getTypeId()


class TimeMixIn(object):

    _yearsDigits = 4
    _hasSubsecond = False
    _optionalMinutes = False
    _shortTZ = False

    class FixedOffset(datetime.tzinfo):
        """Fixed offset in minutes east from UTC."""

        # defaulted arguments required
        # https: // docs.python.org / 2.3 / lib / datetime - tzinfo.html
        def __init__(self, offset=0, name='UTC'):
            self.__offset = datetime.timedelta(minutes=offset)
            self.__name = name

        def utcoffset(self, dt):
            return self.__offset

        def tzname(self, dt):
            return self.__name

        def dst(self, dt):
            return datetime.timedelta(0)

    UTC = FixedOffset()

    @property
    def asDateTime(self):
        """Create :py:class:`datetime.datetime` object from a |ASN.1| object.

        Returns
        -------
        :
            new instance of :py:class:`datetime.datetime` object
        """
        text = str(self)
        if text.endswith('Z'):
            tzinfo = TimeMixIn.UTC
            text = text[:-1]

        elif '-' in text or '+' in text:
            if '+' in text:
                text, plusminus, tz = text.partition('+')
            else:
                text, plusminus, tz = text.partition('-')

            if self._shortTZ and len(tz) == 2:
                tz += '00'

            if len(tz) != 4:
                raise error.PyAsn1Error('malformed time zone offset %s' % tz)

            try:
                minutes = int(tz[:2]) * 60 + int(tz[2:])
                if plusminus == '-':
                    minutes *= -1

            except ValueError:
                raise error.PyAsn1Error('unknown time specification %s' % self)

            tzinfo = TimeMixIn.FixedOffset(minutes, '?')

        else:
            tzinfo = None

        if '.' in text or ',' in text:
            if '.' in text:
                text, _, ms = text.partition('.')
            else:
                text, _, ms = text.partition(',')

            try:
                ms = int(ms) * 1000

            except ValueError:
                raise error.PyAsn1Error('bad sub-second time specification %s' % self)

        else:
            ms = 0

        if self._optionalMinutes and len(text) - self._yearsDigits == 6:
            text += '0000'
        elif len(text) - self._yearsDigits == 8:
            text += '00'

        try:
            dt = datetime.datetime.strptime(text, self._yearsDigits == 4 and '%Y%m%d%H%M%S' or '%y%m%d%H%M%S')

        except ValueError:
            raise error.PyAsn1Error('malformed datetime format %s' % self)

        return dt.replace(microsecond=ms, tzinfo=tzinfo)

    @classmethod
    def fromDateTime(cls, dt):
        """Create |ASN.1| object from a :py:class:`datetime.datetime` object.

        Parameters
        ----------
        dt: :py:class:`datetime.datetime` object
            The `datetime.datetime` object to initialize the |ASN.1| object
            from

        Returns
        -------
        :
            new instance of |ASN.1| value
        """
        text = dt.strftime(cls._yearsDigits == 4 and '%Y%m%d%H%M%S' or '%y%m%d%H%M%S')
        if cls._hasSubsecond:
            text += '.%d' % (dt.microsecond // 1000)

        if dt.utcoffset():
            seconds = dt.utcoffset().seconds
            if seconds < 0:
                text += '-'
            else:
                text += '+'
            text += '%.2d%.2d' % (seconds // 3600, seconds % 3600)
        else:
            text += 'Z'

        return cls(text)


class GeneralizedTime(char.VisibleString, TimeMixIn):
    __doc__ = char.VisibleString.__doc__

    #: Default :py:class:`~pyasn1.type.tag.TagSet` object for |ASN.1| objects
    tagSet = char.VisibleString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 24)
    )

    # Optimization for faster codec lookup
    typeId = char.VideotexString.getTypeId()

    _yearsDigits = 4
    _hasSubsecond = True
    _optionalMinutes = True
    _shortTZ = True


class UTCTime(char.VisibleString, TimeMixIn):
    __doc__ = char.VisibleString.__doc__

    #: Default :py:class:`~pyasn1.type.tag.TagSet` object for |ASN.1| objects
    tagSet = char.VisibleString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 23)
    )

    # Optimization for faster codec lookup
    typeId = char.VideotexString.getTypeId()

    _yearsDigits = 2
    _hasSubsecond = False
    _optionalMinutes = False
    _shortTZ = False

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\gdscript.py ===
"""
    pygments.lexers.gdscript
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for GDScript.

    Modified by Daniel J. Ramirez <djrmuv@gmail.com> based on the original
    python.py.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, default, words, \
    combined
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

__all__ = ["GDScriptLexer"]


class GDScriptLexer(RegexLexer):
    """
    For GDScript source code.
    """

    name = "GDScript"
    url = 'https://www.godotengine.org'
    aliases = ["gdscript", "gd"]
    filenames = ["*.gd"]
    mimetypes = ["text/x-gdscript", "application/x-gdscript"]
    version_added = ''

    def innerstring_rules(ttype):
        return [
            # the old style '%s' % (...) string formatting
            (r"%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?"
             "[hlL]?[E-GXc-giorsux%]",
             String.Interpol),
            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"%\n]+', ttype),
            (r'[\'"\\]', ttype),
            # unhandled string formatting sign
            (r"%", ttype),
            # newlines are an error (use "nl" state)
        ]

    tokens = {
        "root": [
            (r"\n", Whitespace),
            (r'^(\s*)([rRuUbB]{,2})("""(?:.|\n)*?""")',
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r"^(\s*)([rRuUbB]{,2})('''(?:.|\n)*?''')",
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r"[^\S\n]+", Whitespace),
            (r"#.*$", Comment.Single),
            (r"[]{}:(),;[]", Punctuation),
            (r"(\\)(\n)", bygroups(Text, Whitespace)),
            (r"\\", Text),
            (r"(in|and|or|not)\b", Operator.Word),
            (r"!=|==|<<|>>|&&|\+=|-=|\*=|/=|%=|&=|\|=|\|\||[-~+/*%=<>&^.!|$]",
             Operator),
            include("keywords"),
            (r"(func)(\s+)", bygroups(Keyword, Whitespace), "funcname"),
            (r"(class)(\s+)", bygroups(Keyword, Whitespace), "classname"),
            include("builtins"),
            ('([rR]|[uUbB][rR]|[rR][uUbB])(""")',
             bygroups(String.Affix, String.Double),
             "tdqs"),
            ("([rR]|[uUbB][rR]|[rR][uUbB])(''')",
             bygroups(String.Affix, String.Single),
             "tsqs"),
            ('([rR]|[uUbB][rR]|[rR][uUbB])(")',
             bygroups(String.Affix, String.Double),
             "dqs"),
            ("([rR]|[uUbB][rR]|[rR][uUbB])(')",
             bygroups(String.Affix, String.Single),
             "sqs"),
            ('([uUbB]?)(""")',
             bygroups(String.Affix, String.Double),
             combined("stringescape", "tdqs")),
            ("([uUbB]?)(''')",
             bygroups(String.Affix, String.Single),
             combined("stringescape", "tsqs")),
            ('([uUbB]?)(")',
             bygroups(String.Affix, String.Double),
             combined("stringescape", "dqs")),
            ("([uUbB]?)(')",
             bygroups(String.Affix, String.Single),
             combined("stringescape", "sqs")),
            include("name"),
            include("numbers"),
        ],
        "keywords": [
            (words(("and", "in", "not", "or", "as", "breakpoint", "class",
                    "class_name", "extends", "is", "func", "setget", "signal",
                    "tool", "const", "enum", "export", "onready", "static",
                    "var", "break", "continue", "if", "elif", "else", "for",
                    "pass", "return", "match", "while", "remote", "master",
                    "puppet", "remotesync", "mastersync", "puppetsync"),
                   suffix=r"\b"), Keyword),
        ],
        "builtins": [
            (words(("Color8", "ColorN", "abs", "acos", "asin", "assert", "atan",
                    "atan2", "bytes2var", "ceil", "char", "clamp", "convert",
                    "cos", "cosh", "db2linear", "decimals", "dectime", "deg2rad",
                    "dict2inst", "ease", "exp", "floor", "fmod", "fposmod",
                    "funcref", "hash", "inst2dict", "instance_from_id", "is_inf",
                    "is_nan", "lerp", "linear2db", "load", "log", "max", "min",
                    "nearest_po2", "pow", "preload", "print", "print_stack",
                    "printerr", "printraw", "prints", "printt", "rad2deg",
                    "rand_range", "rand_seed", "randf", "randi", "randomize",
                    "range", "round", "seed", "sign", "sin", "sinh", "sqrt",
                    "stepify", "str", "str2var", "tan", "tan", "tanh",
                    "type_exist", "typeof", "var2bytes", "var2str", "weakref",
                    "yield"), prefix=r"(?<!\.)", suffix=r"\b"),
             Name.Builtin),
            (r"((?<!\.)(self|false|true)|(PI|TAU|NAN|INF)" r")\b",
             Name.Builtin.Pseudo),
            (words(("bool", "int", "float", "String", "NodePath", "Vector2",
                    "Rect2", "Transform2D", "Vector3", "Rect3", "Plane", "Quat",
                    "Basis", "Transform", "Color", "RID", "Object", "NodePath",
                    "Dictionary", "Array", "PackedByteArray", "PackedInt32Array",
                    "PackedInt64Array", "PackedFloat32Array", "PackedFloat64Array",
                    "PackedStringArray", "PackedVector2Array", "PackedVector3Array",
                    "PackedColorArray", "null", "void"),
                   prefix=r"(?<!\.)", suffix=r"\b"),
             Name.Builtin.Type),
        ],
        "numbers": [
            (r"(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?j?", Number.Float),
            (r"\d+[eE][+-]?[0-9]+j?", Number.Float),
            (r"0[xX][a-fA-F0-9]+", Number.Hex),
            (r"\d+j?", Number.Integer),
        ],
        "name": [(r"[a-zA-Z_]\w*", Name)],
        "funcname": [(r"[a-zA-Z_]\w*", Name.Function, "#pop"), default("#pop")],
        "classname": [(r"[a-zA-Z_]\w*", Name.Class, "#pop")],
        "stringescape": [
            (
                r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
                r"U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})",
                String.Escape,
            )
        ],
        "strings-single": innerstring_rules(String.Single),
        "strings-double": innerstring_rules(String.Double),
        "dqs": [
            (r'"', String.Double, "#pop"),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include("strings-double"),
        ],
        "sqs": [
            (r"'", String.Single, "#pop"),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include("strings-single"),
        ],
        "tdqs": [
            (r'"""', String.Double, "#pop"),
            include("strings-double"),
            (r"\n", Whitespace),
        ],
        "tsqs": [
            (r"'''", String.Single, "#pop"),
            include("strings-single"),
            (r"\n", Whitespace),
        ],
    }

    def analyse_text(text):
        score = 0.0

        if re.search(
            r"func (_ready|_init|_input|_process|_unhandled_input)", text
        ):
            score += 0.8

        if re.search(
            r"(extends |class_name |onready |preload|load|setget|func [^_])",
            text
        ):
            score += 0.4

        if re.search(r"(var|const|enum|export|signal|tool)", text):
            score += 0.2

        return min(score, 1.0)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\varnish.py ===
"""
    pygments.lexers.varnish
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Varnish configuration

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, bygroups, using, this, \
    inherit, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Literal, Whitespace

__all__ = ['VCLLexer', 'VCLSnippetLexer']


class VCLLexer(RegexLexer):
    """
    For Varnish Configuration Language (VCL).
    """
    name = 'VCL'
    aliases = ['vcl']
    filenames = ['*.vcl']
    mimetypes = ['text/x-vclsrc']
    url = 'https://www.varnish-software.com/developers/tutorials/varnish-configuration-language-vcl'
    version_added = '2.2'

    def analyse_text(text):
        # If the very first line is 'vcl 4.0;' it's pretty much guaranteed
        # that this is VCL
        if text.startswith('vcl 4.0;'):
            return 1.0
        # Skip over comments and blank lines
        # This is accurate enough that returning 0.9 is reasonable.
        # Almost no VCL files start without some comments.
        elif '\nvcl 4.0;' in text[:1000]:
            return 0.9

    tokens = {
        'probe': [
            include('whitespace'),
            include('comments'),
            (r'(\.\w+)(\s*=\s*)([^;]*)(;)',
             bygroups(Name.Attribute, Operator, using(this), Punctuation)),
            (r'\}', Punctuation, '#pop'),
        ],
        'acl': [
            include('whitespace'),
            include('comments'),
            (r'[!/]+', Operator),
            (r';', Punctuation),
            (r'\d+', Number),
            (r'\}', Punctuation, '#pop'),
        ],
        'backend': [
            include('whitespace'),
            (r'(\.probe)(\s*=\s*)(\w+)(;)',
             bygroups(Name.Attribute, Operator, Name.Variable.Global, Punctuation)),
            (r'(\.probe)(\s*=\s*)(\{)',
             bygroups(Name.Attribute, Operator, Punctuation), 'probe'),
            (r'(\.\w+\b)(\s*=\s*)([^;\s]*)(\s*;)',
             bygroups(Name.Attribute, Operator, using(this), Punctuation)),
            (r'\{', Punctuation, '#push'),
            (r'\}', Punctuation, '#pop'),
        ],
        'statements': [
            (r'(\d\.)?\d+[sdwhmy]', Literal.Date),
            (r'(\d\.)?\d+ms', Literal.Date),
            (r'(vcl_pass|vcl_hash|vcl_hit|vcl_init|vcl_backend_fetch|vcl_pipe|'
             r'vcl_backend_response|vcl_synth|vcl_deliver|vcl_backend_error|'
             r'vcl_fini|vcl_recv|vcl_purge|vcl_miss)\b', Name.Function),
            (r'(pipe|retry|hash|synth|deliver|purge|abandon|lookup|pass|fail|ok|'
             r'miss|fetch|restart)\b', Name.Constant),
            (r'(beresp|obj|resp|req|req_top|bereq)\.http\.[a-zA-Z_-]+\b', Name.Variable),
            (words((
                'obj.status', 'req.hash_always_miss', 'beresp.backend', 'req.esi_level',
                'req.can_gzip', 'beresp.ttl', 'obj.uncacheable', 'req.ttl', 'obj.hits',
                'client.identity', 'req.hash_ignore_busy', 'obj.reason', 'req.xid',
                'req_top.proto', 'beresp.age', 'obj.proto', 'obj.age', 'local.ip',
                'beresp.uncacheable', 'req.method', 'beresp.backend.ip', 'now',
                'obj.grace', 'req.restarts', 'beresp.keep', 'req.proto', 'resp.proto',
                'bereq.xid', 'bereq.between_bytes_timeout', 'req.esi',
                'bereq.first_byte_timeout', 'bereq.method', 'bereq.connect_timeout',
                'beresp.do_gzip',  'resp.status', 'beresp.do_gunzip',
                'beresp.storage_hint', 'resp.is_streaming', 'beresp.do_stream',
                'req_top.method', 'bereq.backend', 'beresp.backend.name', 'beresp.status',
                'req.url', 'obj.keep', 'obj.ttl', 'beresp.reason', 'bereq.retries',
                'resp.reason', 'bereq.url', 'beresp.do_esi', 'beresp.proto', 'client.ip',
                'bereq.proto', 'server.hostname', 'remote.ip', 'req.backend_hint',
                'server.identity', 'req_top.url', 'beresp.grace', 'beresp.was_304',
                'server.ip', 'bereq.uncacheable'), suffix=r'\b'),
             Name.Variable),
            (r'[!%&+*\-,/<.}{>=|~]+', Operator),
            (r'[();]', Punctuation),

            (r'[,]+', Punctuation),
            (words(('hash_data', 'regsub', 'regsuball', 'if', 'else',
                    'elsif', 'elif', 'synth', 'synthetic', 'ban',
                    'return', 'set', 'unset', 'import', 'include', 'new',
                    'rollback', 'call'), suffix=r'\b'),
             Keyword),
            (r'storage\.\w+\.\w+\b', Name.Variable),
            (words(('true', 'false')), Name.Builtin),
            (r'\d+\b', Number),
            (r'(backend)(\s+\w+)(\s*\{)',
             bygroups(Keyword, Name.Variable.Global, Punctuation), 'backend'),
            (r'(probe\s)(\s*\w+\s)(\{)',
             bygroups(Keyword, Name.Variable.Global, Punctuation), 'probe'),
            (r'(acl\s)(\s*\w+\s)(\{)',
             bygroups(Keyword, Name.Variable.Global, Punctuation), 'acl'),
            (r'(vcl )(4.0)(;)$',
             bygroups(Keyword.Reserved, Name.Constant, Punctuation)),
            (r'(sub\s+)([a-zA-Z]\w*)(\s*\{)',
                bygroups(Keyword, Name.Function, Punctuation)),
            (r'([a-zA-Z_]\w*)'
             r'(\.)'
             r'([a-zA-Z_]\w*)'
             r'(\s*\(.*\))',
             bygroups(Name.Function, Punctuation, Name.Function, using(this))),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'comment': [
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ],
        'comments': [
            (r'#.*$', Comment),
            (r'/\*', Comment.Multiline, 'comment'),
            (r'//.*$', Comment),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'[^"\n]+', String),  # all other characters
        ],
        'multistring': [
            (r'[^"}]', String),
            (r'"\}', String, '#pop'),
            (r'["}]', String),
        ],
        'whitespace': [
            (r'L?"', String, 'string'),
            (r'\{"', String, 'multistring'),
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            (r'\\\n', Text),  # line continuation
        ],
        'root': [
            include('whitespace'),
            include('comments'),
            include('statements'),
            (r'\s+', Whitespace),
        ],
    }


class VCLSnippetLexer(VCLLexer):
    """
    For Varnish Configuration Language snippets.
    """
    name = 'VCLSnippets'
    aliases = ['vclsnippets', 'vclsnippet']
    mimetypes = ['text/x-vclsnippet']
    filenames = []
    url = 'https://www.varnish-software.com/developers/tutorials/varnish-configuration-language-vcl'
    version_added = '2.2'

    def analyse_text(text):
        # override method inherited from VCLLexer
        return 0

    tokens = {
        'snippetspre': [
            (r'\.\.\.+', Comment),
            (r'(bereq|req|req_top|resp|beresp|obj|client|server|local|remote|'
             r'storage)($|\.\*)', Name.Variable),
        ],
        'snippetspost': [
            (r'(backend)\b', Keyword.Reserved),
        ],
        'root': [
            include('snippetspre'),
            inherit,
            include('snippetspost'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\Demos\threadedgui.py ===
# Demo of using just windows, without documents and views.

# Also demo of a GUI thread, pretty much direct from the MFC C++ sample MTMDI.

import timer
import win32api
import win32con
import win32ui
from pywin.mfc import window
from pywin.mfc.thread import WinThread

WM_USER_PREPARE_TO_CLOSE = win32con.WM_USER + 32

# font is a dictionary in which the following elements matter:
# (the best matching font to supplied parameters is returned)
#   name		string name of the font as known by Windows
#   size		point size of font in logical units
#   weight		weight of font (win32con.FW_NORMAL, win32con.FW_BOLD)
#   italic		boolean; true if set to anything but None
#   underline	boolean; true if set to anything but None


# This window is a child window of a frame.  It is not the frame window itself.
class FontWindow(window.Wnd):
    def __init__(self, text="Python Rules!"):
        window.Wnd.__init__(self)
        self.text = text
        self.index = 0
        self.incr = 1
        self.width = self.height = 0
        self.ChangeAttributes()
        # set up message handlers

    def Create(self, title, style, rect, parent):
        classStyle = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        className = win32ui.RegisterWndClass(
            classStyle, 0, win32con.COLOR_WINDOW + 1, 0
        )
        self._obj_ = win32ui.CreateWnd()
        self._obj_.AttachObject(self)
        self._obj_.CreateWindow(
            className, title, style, rect, parent, win32ui.AFX_IDW_PANE_FIRST
        )
        self.HookMessage(self.OnSize, win32con.WM_SIZE)
        self.HookMessage(self.OnPrepareToClose, WM_USER_PREPARE_TO_CLOSE)
        self.HookMessage(self.OnDestroy, win32con.WM_DESTROY)
        self.timerid = timer.set_timer(100, self.OnTimer)
        self.InvalidateRect()

    def OnDestroy(self, msg):
        timer.kill_timer(self.timerid)

    def OnTimer(self, id, timeVal):
        self.index += self.incr
        if self.index > len(self.text):
            self.incr = -1
            self.index = len(self.text)
        elif self.index < 0:
            self.incr = 1
            self.index = 0
        self.InvalidateRect()

    def OnPaint(self):
        # print("Paint message from thread", win32api.GetCurrentThreadId())
        dc, paintStruct = self.BeginPaint()
        self.OnPrepareDC(dc, None)

        if self.width == 0 and self.height == 0:
            left, top, right, bottom = self.GetClientRect()
            self.width = right - left
            self.height = bottom - top
        x, y = self.width // 2, self.height // 2
        dc.TextOut(x, y, self.text[: self.index])
        self.EndPaint(paintStruct)

    def ChangeAttributes(self):
        font_spec = {"name": "Arial", "height": 42}
        self.font = win32ui.CreateFont(font_spec)

    def OnPrepareToClose(self, params):
        self.DestroyWindow()

    def OnSize(self, params):
        lParam = params[3]
        self.width = win32api.LOWORD(lParam)
        self.height = win32api.HIWORD(lParam)

    def OnPrepareDC(self, dc, printinfo):
        # Set up the DC for forthcoming OnDraw call
        dc.SetTextColor(win32api.RGB(0, 0, 255))
        dc.SetBkColor(win32api.GetSysColor(win32con.COLOR_WINDOW))
        dc.SelectObject(self.font)
        dc.SetTextAlign(win32con.TA_CENTER | win32con.TA_BASELINE)


class FontFrame(window.MDIChildWnd):
    def __init__(self):
        pass  # Don't call base class doc/view version...

    def Create(self, title, rect=None, parent=None):
        style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW
        self._obj_ = win32ui.CreateMDIChild()
        self._obj_.AttachObject(self)

        self._obj_.CreateWindow(None, title, style, rect, parent)
        rect = self.GetClientRect()
        rect = (0, 0, rect[2] - rect[0], rect[3] - rect[1])
        self.child = FontWindow("Not threaded")
        self.child.Create(
            "FontDemo", win32con.WS_CHILD | win32con.WS_VISIBLE, rect, self
        )


class TestThread(WinThread):
    def __init__(self, parentWindow):
        self.parentWindow = parentWindow
        self.child = None
        WinThread.__init__(self)

    def InitInstance(self):
        rect = self.parentWindow.GetClientRect()
        rect = (0, 0, rect[2] - rect[0], rect[3] - rect[1])

        self.child = FontWindow()
        self.child.Create(
            "FontDemo", win32con.WS_CHILD | win32con.WS_VISIBLE, rect, self.parentWindow
        )
        self.SetMainFrame(self.child)
        return WinThread.InitInstance(self)

    def ExitInstance(self):
        return 0


class ThreadedFontFrame(window.MDIChildWnd):
    def __init__(self):
        pass  # Don't call base class doc/view version...
        self.thread = None

    def Create(self, title, rect=None, parent=None):
        style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW
        self._obj_ = win32ui.CreateMDIChild()
        self._obj_.CreateWindow(None, title, style, rect, parent)
        self._obj_.HookMessage(self.OnDestroy, win32con.WM_DESTROY)
        self._obj_.HookMessage(self.OnSize, win32con.WM_SIZE)

        self.thread = TestThread(self)
        self.thread.CreateThread()

    def OnSize(self, msg):
        pass

    def OnDestroy(self, msg):
        win32ui.OutputDebugString("OnDestroy\n")
        if self.thread and self.thread.child:
            child = self.thread.child
            child.SendMessage(WM_USER_PREPARE_TO_CLOSE, 0, 0)
            win32ui.OutputDebugString("Destroyed\n")


def Demo():
    f = FontFrame()
    f.Create("Font Demo")


def ThreadedDemo():
    rect = win32ui.GetMainFrame().GetMDIClient().GetClientRect()
    rect = rect[0], int(rect[3] * 3 / 4), int(rect[2] / 4), rect[3]
    incr = rect[2]
    for i in range(4):
        if i == 0:
            f = FontFrame()
            title = "Not threaded"
        else:
            f = ThreadedFontFrame()
            title = "Threaded GUI Demo"
        f.Create(title, rect)
        rect = rect[0] + incr, rect[1], rect[2] + incr, rect[3]
    # Givem a chance to start
    win32api.Sleep(100)
    win32ui.PumpWaitingMessages()


if __name__ == "__main__":
    import demoutils

    if demoutils.NeedGoodGUI():
        ThreadedDemo()
# 		Demo()

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_highlevel_serve_listeners.py ===
from __future__ import annotations

import errno
from functools import partial
from typing import TYPE_CHECKING, NoReturn, cast

import attrs

import trio
from trio import Nursery, StapledStream, TaskStatus
from trio.testing import (
    Matcher,
    MemoryReceiveStream,
    MemorySendStream,
    MockClock,
    RaisesGroup,
    memory_stream_pair,
    wait_all_tasks_blocked,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest

    from trio._channel import MemoryReceiveChannel, MemorySendChannel
    from trio.abc import Stream

# types are somewhat tentative - I just bruteforced them until I got something that didn't
# give errors
StapledMemoryStream = StapledStream[MemorySendStream, MemoryReceiveStream]


@attrs.define(eq=False, slots=False)
class MemoryListener(trio.abc.Listener[StapledMemoryStream]):
    closed: bool = False
    accepted_streams: list[trio.abc.Stream] = attrs.Factory(list)
    queued_streams: tuple[
        MemorySendChannel[StapledMemoryStream],
        MemoryReceiveChannel[StapledMemoryStream],
    ] = attrs.Factory(lambda: trio.open_memory_channel[StapledMemoryStream](1))
    accept_hook: Callable[[], Awaitable[object]] | None = None

    async def connect(self) -> StapledMemoryStream:
        assert not self.closed
        client, server = memory_stream_pair()
        await self.queued_streams[0].send(server)
        return client

    async def accept(self) -> StapledMemoryStream:
        await trio.lowlevel.checkpoint()
        assert not self.closed
        if self.accept_hook is not None:
            await self.accept_hook()
        stream = await self.queued_streams[1].receive()
        self.accepted_streams.append(stream)
        return stream

    async def aclose(self) -> None:
        self.closed = True
        await trio.lowlevel.checkpoint()


async def test_serve_listeners_basic() -> None:
    listeners = [MemoryListener(), MemoryListener()]

    record = []

    def close_hook() -> None:
        # Make sure this is a forceful close
        assert trio.current_effective_deadline() == float("-inf")
        record.append("closed")

    async def handler(stream: StapledMemoryStream) -> None:
        await stream.send_all(b"123")
        assert await stream.receive_some(10) == b"456"
        stream.send_stream.close_hook = close_hook
        stream.receive_stream.close_hook = close_hook

    async def client(listener: MemoryListener) -> None:
        s = await listener.connect()
        assert await s.receive_some(10) == b"123"
        await s.send_all(b"456")

    async def do_tests(parent_nursery: Nursery) -> None:
        async with trio.open_nursery() as nursery:
            for listener in listeners:
                for _ in range(3):
                    nursery.start_soon(client, listener)

        await wait_all_tasks_blocked()

        # verifies that all 6 streams x 2 directions each were closed ok
        assert len(record) == 12

        parent_nursery.cancel_scope.cancel()

    async with trio.open_nursery() as nursery:
        value = await nursery.start(
            trio.serve_listeners,
            handler,
            listeners,
        )
        assert isinstance(value, list)
        l2 = cast("list[MemoryListener]", value)
        assert l2 == listeners
        # This is just split into another function because gh-136 isn't
        # implemented yet
        nursery.start_soon(do_tests, nursery)

    for listener in listeners:
        assert listener.closed


async def test_serve_listeners_accept_unrecognized_error() -> None:
    for error in [KeyError(), OSError(errno.ECONNABORTED, "ECONNABORTED")]:
        listener = MemoryListener()

        async def raise_error() -> NoReturn:
            raise error  # noqa: B023  # Set from loop

        def check_error(e: BaseException) -> bool:
            return e is error  # noqa: B023

        listener.accept_hook = raise_error

        with RaisesGroup(Matcher(check=check_error)):
            await trio.serve_listeners(None, [listener])  # type: ignore[arg-type]


async def test_serve_listeners_accept_capacity_error(
    autojump_clock: MockClock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    listener = MemoryListener()

    async def raise_EMFILE() -> NoReturn:
        raise OSError(errno.EMFILE, "out of file descriptors")

    listener.accept_hook = raise_EMFILE

    # It retries every 100 ms, so in 950 ms it will retry at 0, 100, ..., 900
    # = 10 times total
    with trio.move_on_after(0.950):
        await trio.serve_listeners(None, [listener])  # type: ignore[arg-type]

    assert len(caplog.records) == 10
    for record in caplog.records:
        assert "retrying" in record.msg
        assert record.exc_info is not None
        assert isinstance(record.exc_info[1], OSError)
        assert record.exc_info[1].errno == errno.EMFILE


async def test_serve_listeners_connection_nursery(autojump_clock: MockClock) -> None:
    listener = MemoryListener()

    async def handler(stream: Stream) -> None:
        await trio.sleep(1)

    class Done(Exception):
        pass

    async def connection_watcher(
        *,
        task_status: TaskStatus[Nursery] = trio.TASK_STATUS_IGNORED,
    ) -> NoReturn:
        async with trio.open_nursery() as nursery:
            task_status.started(nursery)
            await wait_all_tasks_blocked()
            assert len(nursery.child_tasks) == 10
            raise Done

    # the exception is wrapped twice because we open two nested nurseries
    with RaisesGroup(RaisesGroup(Done)):
        async with trio.open_nursery() as nursery:
            value = await nursery.start(connection_watcher)
            assert isinstance(value, trio.Nursery)
            handler_nursery: trio.Nursery = value
            await nursery.start(
                partial(
                    trio.serve_listeners,
                    handler,
                    [listener],
                    handler_nursery=handler_nursery,
                ),
            )
            for _ in range(10):
                nursery.start_soon(listener.connect)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\utils\compatibility_tags.py ===
"""Generate and work with PEP 425 Compatibility Tags.
"""

import re
from typing import List, Optional, Tuple

from pip._vendor.packaging.tags import (
    PythonVersion,
    Tag,
    compatible_tags,
    cpython_tags,
    generic_tags,
    interpreter_name,
    interpreter_version,
    ios_platforms,
    mac_platforms,
)

_apple_arch_pat = re.compile(r"(.+)_(\d+)_(\d+)_(.+)")


def version_info_to_nodot(version_info: Tuple[int, ...]) -> str:
    # Only use up to the first two numbers.
    return "".join(map(str, version_info[:2]))


def _mac_platforms(arch: str) -> List[str]:
    match = _apple_arch_pat.match(arch)
    if match:
        name, major, minor, actual_arch = match.groups()
        mac_version = (int(major), int(minor))
        arches = [
            # Since we have always only checked that the platform starts
            # with "macosx", for backwards-compatibility we extract the
            # actual prefix provided by the user in case they provided
            # something like "macosxcustom_". It may be good to remove
            # this as undocumented or deprecate it in the future.
            "{}_{}".format(name, arch[len("macosx_") :])
            for arch in mac_platforms(mac_version, actual_arch)
        ]
    else:
        # arch pattern didn't match (?!)
        arches = [arch]
    return arches


def _ios_platforms(arch: str) -> List[str]:
    match = _apple_arch_pat.match(arch)
    if match:
        name, major, minor, actual_multiarch = match.groups()
        ios_version = (int(major), int(minor))
        arches = [
            # Since we have always only checked that the platform starts
            # with "ios", for backwards-compatibility we extract the
            # actual prefix provided by the user in case they provided
            # something like "ioscustom_". It may be good to remove
            # this as undocumented or deprecate it in the future.
            "{}_{}".format(name, arch[len("ios_") :])
            for arch in ios_platforms(ios_version, actual_multiarch)
        ]
    else:
        # arch pattern didn't match (?!)
        arches = [arch]
    return arches


def _custom_manylinux_platforms(arch: str) -> List[str]:
    arches = [arch]
    arch_prefix, arch_sep, arch_suffix = arch.partition("_")
    if arch_prefix == "manylinux2014":
        # manylinux1/manylinux2010 wheels run on most manylinux2014 systems
        # with the exception of wheels depending on ncurses. PEP 599 states
        # manylinux1/manylinux2010 wheels should be considered
        # manylinux2014 wheels:
        # https://www.python.org/dev/peps/pep-0599/#backwards-compatibility-with-manylinux2010-wheels
        if arch_suffix in {"i686", "x86_64"}:
            arches.append("manylinux2010" + arch_sep + arch_suffix)
            arches.append("manylinux1" + arch_sep + arch_suffix)
    elif arch_prefix == "manylinux2010":
        # manylinux1 wheels run on most manylinux2010 systems with the
        # exception of wheels depending on ncurses. PEP 571 states
        # manylinux1 wheels should be considered manylinux2010 wheels:
        # https://www.python.org/dev/peps/pep-0571/#backwards-compatibility-with-manylinux1-wheels
        arches.append("manylinux1" + arch_sep + arch_suffix)
    return arches


def _get_custom_platforms(arch: str) -> List[str]:
    arch_prefix, arch_sep, arch_suffix = arch.partition("_")
    if arch.startswith("macosx"):
        arches = _mac_platforms(arch)
    elif arch.startswith("ios"):
        arches = _ios_platforms(arch)
    elif arch_prefix in ["manylinux2014", "manylinux2010"]:
        arches = _custom_manylinux_platforms(arch)
    else:
        arches = [arch]
    return arches


def _expand_allowed_platforms(platforms: Optional[List[str]]) -> Optional[List[str]]:
    if not platforms:
        return None

    seen = set()
    result = []

    for p in platforms:
        if p in seen:
            continue
        additions = [c for c in _get_custom_platforms(p) if c not in seen]
        seen.update(additions)
        result.extend(additions)

    return result


def _get_python_version(version: str) -> PythonVersion:
    if len(version) > 1:
        return int(version[0]), int(version[1:])
    else:
        return (int(version[0]),)


def _get_custom_interpreter(
    implementation: Optional[str] = None, version: Optional[str] = None
) -> str:
    if implementation is None:
        implementation = interpreter_name()
    if version is None:
        version = interpreter_version()
    return f"{implementation}{version}"


def get_supported(
    version: Optional[str] = None,
    platforms: Optional[List[str]] = None,
    impl: Optional[str] = None,
    abis: Optional[List[str]] = None,
) -> List[Tag]:
    """Return a list of supported tags for each version specified in
    `versions`.

    :param version: a string version, of the form "33" or "32",
        or None. The version will be assumed to support our ABI.
    :param platform: specify a list of platforms you want valid
        tags for, or None. If None, use the local system platform.
    :param impl: specify the exact implementation you want valid
        tags for, or None. If None, use the local interpreter impl.
    :param abis: specify a list of abis you want valid
        tags for, or None. If None, use the local interpreter abi.
    """
    supported: List[Tag] = []

    python_version: Optional[PythonVersion] = None
    if version is not None:
        python_version = _get_python_version(version)

    interpreter = _get_custom_interpreter(impl, version)

    platforms = _expand_allowed_platforms(platforms)

    is_cpython = (impl or interpreter_name()) == "cp"
    if is_cpython:
        supported.extend(
            cpython_tags(
                python_version=python_version,
                abis=abis,
                platforms=platforms,
            )
        )
    else:
        supported.extend(
            generic_tags(
                interpreter=interpreter,
                abis=abis,
                platforms=platforms,
            )
        )
    supported.extend(
        compatible_tags(
            python_version=python_version,
            interpreter=interpreter,
            platforms=platforms,
        )
    )

    return supported

# === NexusCore/openenv\Lib\site-packages\setuptools\_static.py ===
from functools import wraps
from typing import TypeVar

import packaging.specifiers

from .warnings import SetuptoolsDeprecationWarning


class Static:
    """
    Wrapper for built-in object types that are allow setuptools to identify
    static core metadata (in opposition to ``Dynamic``, as defined :pep:`643`).

    The trick is to mark values with :class:`Static` when they come from
    ``pyproject.toml`` or ``setup.cfg``, so if any plugin overwrite the value
    with a built-in, setuptools will be able to recognise the change.

    We inherit from built-in classes, so that we don't need to change the existing
    code base to deal with the new types.
    We also should strive for immutability objects to avoid changes after the
    initial parsing.
    """

    _mutated_: bool = False  # TODO: Remove after deprecation warning is solved


def _prevent_modification(target: type, method: str, copying: str) -> None:
    """
    Because setuptools is very flexible we cannot fully prevent
    plugins and user customizations from modifying static values that were
    parsed from config files.
    But we can attempt to block "in-place" mutations and identify when they
    were done.
    """
    fn = getattr(target, method, None)
    if fn is None:
        return

    @wraps(fn)
    def _replacement(self: Static, *args, **kwargs):
        # TODO: After deprecation period raise NotImplementedError instead of warning
        #       which obviated the existence and checks of the `_mutated_` attribute.
        self._mutated_ = True
        SetuptoolsDeprecationWarning.emit(
            "Direct modification of value will be disallowed",
            f"""
            In an effort to implement PEP 643, direct/in-place changes of static values
            that come from configuration files are deprecated.
            If you need to modify this value, please first create a copy with {copying}
            and make sure conform to all relevant standards when overriding setuptools
            functionality (https://packaging.python.org/en/latest/specifications/).
            """,
            due_date=(2025, 10, 10),  # Initially introduced in 2024-09-06
        )
        return fn(self, *args, **kwargs)

    _replacement.__doc__ = ""  # otherwise doctest may fail.
    setattr(target, method, _replacement)


class Str(str, Static):
    pass


class Tuple(tuple, Static):
    pass


class List(list, Static):
    """
    :meta private:
    >>> x = List([1, 2, 3])
    >>> is_static(x)
    True
    >>> x += [0]  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    SetuptoolsDeprecationWarning: Direct modification ...
    >>> is_static(x)  # no longer static after modification
    False
    >>> y = list(x)
    >>> y.clear()
    >>> y
    []
    >>> y == x
    False
    >>> is_static(List(y))
    True
    """


# Make `List` immutable-ish
# (certain places of setuptools/distutils issue a warn if we use tuple instead of list)
for _method in (
    '__delitem__',
    '__iadd__',
    '__setitem__',
    'append',
    'clear',
    'extend',
    'insert',
    'remove',
    'reverse',
    'pop',
):
    _prevent_modification(List, _method, "`list(value)`")


class Dict(dict, Static):
    """
    :meta private:
    >>> x = Dict({'a': 1, 'b': 2})
    >>> is_static(x)
    True
    >>> x['c'] = 0  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    SetuptoolsDeprecationWarning: Direct modification ...
    >>> x._mutated_
    True
    >>> is_static(x)  # no longer static after modification
    False
    >>> y = dict(x)
    >>> y.popitem()
    ('b', 2)
    >>> y == x
    False
    >>> is_static(Dict(y))
    True
    """


# Make `Dict` immutable-ish (we cannot inherit from types.MappingProxyType):
for _method in (
    '__delitem__',
    '__ior__',
    '__setitem__',
    'clear',
    'pop',
    'popitem',
    'setdefault',
    'update',
):
    _prevent_modification(Dict, _method, "`dict(value)`")


class SpecifierSet(packaging.specifiers.SpecifierSet, Static):
    """Not exactly a built-in type but useful for ``requires-python``"""


T = TypeVar("T")


def noop(value: T) -> T:
    """
    >>> noop(42)
    42
    """
    return value


_CONVERSIONS = {str: Str, tuple: Tuple, list: List, dict: Dict}


def attempt_conversion(value: T) -> T:
    """
    >>> is_static(attempt_conversion("hello"))
    True
    >>> is_static(object())
    False
    """
    return _CONVERSIONS.get(type(value), noop)(value)  # type: ignore[call-overload]


def is_static(value: object) -> bool:
    """
    >>> is_static(a := Dict({'a': 1}))
    True
    >>> is_static(dict(a))
    False
    >>> is_static(b := List([1, 2, 3]))
    True
    >>> is_static(list(b))
    False
    """
    return isinstance(value, Static) and not value._mutated_


EMPTY_LIST = List()
EMPTY_DICT = Dict()

# === NexusCore/openenv\Lib\site-packages\websocket\_socket.py ===
import errno
import selectors
import socket
from typing import Union

from ._exceptions import (
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
)
from ._ssl_compat import SSLError, SSLWantReadError, SSLWantWriteError
from ._utils import extract_error_code, extract_err_message

"""
_socket.py
websocket - WebSocket client library for Python

Copyright 2024 engn33r

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

DEFAULT_SOCKET_OPTION = [(socket.SOL_TCP, socket.TCP_NODELAY, 1)]
if hasattr(socket, "SO_KEEPALIVE"):
    DEFAULT_SOCKET_OPTION.append((socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1))
if hasattr(socket, "TCP_KEEPIDLE"):
    DEFAULT_SOCKET_OPTION.append((socket.SOL_TCP, socket.TCP_KEEPIDLE, 30))
if hasattr(socket, "TCP_KEEPINTVL"):
    DEFAULT_SOCKET_OPTION.append((socket.SOL_TCP, socket.TCP_KEEPINTVL, 10))
if hasattr(socket, "TCP_KEEPCNT"):
    DEFAULT_SOCKET_OPTION.append((socket.SOL_TCP, socket.TCP_KEEPCNT, 3))

_default_timeout = None

__all__ = [
    "DEFAULT_SOCKET_OPTION",
    "sock_opt",
    "setdefaulttimeout",
    "getdefaulttimeout",
    "recv",
    "recv_line",
    "send",
]


class sock_opt:
    def __init__(self, sockopt: list, sslopt: dict) -> None:
        if sockopt is None:
            sockopt = []
        if sslopt is None:
            sslopt = {}
        self.sockopt = sockopt
        self.sslopt = sslopt
        self.timeout = None


def setdefaulttimeout(timeout: Union[int, float, None]) -> None:
    """
    Set the global timeout setting to connect.

    Parameters
    ----------
    timeout: int or float
        default socket timeout time (in seconds)
    """
    global _default_timeout
    _default_timeout = timeout


def getdefaulttimeout() -> Union[int, float, None]:
    """
    Get default timeout

    Returns
    ----------
    _default_timeout: int or float
        Return the global timeout setting (in seconds) to connect.
    """
    return _default_timeout


def recv(sock: socket.socket, bufsize: int) -> bytes:
    if not sock:
        raise WebSocketConnectionClosedException("socket is already closed.")

    def _recv():
        try:
            return sock.recv(bufsize)
        except SSLWantReadError:
            pass
        except socket.error as exc:
            error_code = extract_error_code(exc)
            if error_code not in [errno.EAGAIN, errno.EWOULDBLOCK]:
                raise

        sel = selectors.DefaultSelector()
        sel.register(sock, selectors.EVENT_READ)

        r = sel.select(sock.gettimeout())
        sel.close()

        if r:
            return sock.recv(bufsize)

    try:
        if sock.gettimeout() == 0:
            bytes_ = sock.recv(bufsize)
        else:
            bytes_ = _recv()
    except TimeoutError:
        raise WebSocketTimeoutException("Connection timed out")
    except socket.timeout as e:
        message = extract_err_message(e)
        raise WebSocketTimeoutException(message)
    except SSLError as e:
        message = extract_err_message(e)
        if isinstance(message, str) and "timed out" in message:
            raise WebSocketTimeoutException(message)
        else:
            raise

    if not bytes_:
        raise WebSocketConnectionClosedException("Connection to remote host was lost.")

    return bytes_


def recv_line(sock: socket.socket) -> bytes:
    line = []
    while True:
        c = recv(sock, 1)
        line.append(c)
        if c == b"\n":
            break
    return b"".join(line)


def send(sock: socket.socket, data: Union[bytes, str]) -> int:
    if isinstance(data, str):
        data = data.encode("utf-8")

    if not sock:
        raise WebSocketConnectionClosedException("socket is already closed.")

    def _send():
        try:
            return sock.send(data)
        except SSLWantWriteError:
            pass
        except socket.error as exc:
            error_code = extract_error_code(exc)
            if error_code is None:
                raise
            if error_code not in [errno.EAGAIN, errno.EWOULDBLOCK]:
                raise

        sel = selectors.DefaultSelector()
        sel.register(sock, selectors.EVENT_WRITE)

        w = sel.select(sock.gettimeout())
        sel.close()

        if w:
            return sock.send(data)

    try:
        if sock.gettimeout() == 0:
            return sock.send(data)
        else:
            return _send()
    except socket.timeout as e:
        message = extract_err_message(e)
        raise WebSocketTimeoutException(message)
    except Exception as e:
        message = extract_err_message(e)
        if isinstance(message, str) and "timed out" in message:
            raise WebSocketTimeoutException(message)
        else:
            raise