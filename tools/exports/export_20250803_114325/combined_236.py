
# === NexusCore/openenv\Lib\site-packages\attr\_cmp.py ===
# SPDX-License-Identifier: MIT


import functools
import types

from ._make import __ne__


_operation_names = {"eq": "==", "lt": "<", "le": "<=", "gt": ">", "ge": ">="}


def cmp_using(
    eq=None,
    lt=None,
    le=None,
    gt=None,
    ge=None,
    require_same_type=True,
    class_name="Comparable",
):
    """
    Create a class that can be passed into `attrs.field`'s ``eq``, ``order``,
    and ``cmp`` arguments to customize field comparison.

    The resulting class will have a full set of ordering methods if at least
    one of ``{lt, le, gt, ge}`` and ``eq``  are provided.

    Args:
        eq (typing.Callable | None):
            Callable used to evaluate equality of two objects.

        lt (typing.Callable | None):
            Callable used to evaluate whether one object is less than another
            object.

        le (typing.Callable | None):
            Callable used to evaluate whether one object is less than or equal
            to another object.

        gt (typing.Callable | None):
            Callable used to evaluate whether one object is greater than
            another object.

        ge (typing.Callable | None):
            Callable used to evaluate whether one object is greater than or
            equal to another object.

        require_same_type (bool):
            When `True`, equality and ordering methods will return
            `NotImplemented` if objects are not of the same type.

        class_name (str | None): Name of class. Defaults to "Comparable".

    See `comparison` for more details.

    .. versionadded:: 21.1.0
    """

    body = {
        "__slots__": ["value"],
        "__init__": _make_init(),
        "_requirements": [],
        "_is_comparable_to": _is_comparable_to,
    }

    # Add operations.
    num_order_functions = 0
    has_eq_function = False

    if eq is not None:
        has_eq_function = True
        body["__eq__"] = _make_operator("eq", eq)
        body["__ne__"] = __ne__

    if lt is not None:
        num_order_functions += 1
        body["__lt__"] = _make_operator("lt", lt)

    if le is not None:
        num_order_functions += 1
        body["__le__"] = _make_operator("le", le)

    if gt is not None:
        num_order_functions += 1
        body["__gt__"] = _make_operator("gt", gt)

    if ge is not None:
        num_order_functions += 1
        body["__ge__"] = _make_operator("ge", ge)

    type_ = types.new_class(
        class_name, (object,), {}, lambda ns: ns.update(body)
    )

    # Add same type requirement.
    if require_same_type:
        type_._requirements.append(_check_same_type)

    # Add total ordering if at least one operation was defined.
    if 0 < num_order_functions < 4:
        if not has_eq_function:
            # functools.total_ordering requires __eq__ to be defined,
            # so raise early error here to keep a nice stack.
            msg = "eq must be define is order to complete ordering from lt, le, gt, ge."
            raise ValueError(msg)
        type_ = functools.total_ordering(type_)

    return type_


def _make_init():
    """
    Create __init__ method.
    """

    def __init__(self, value):
        """
        Initialize object with *value*.
        """
        self.value = value

    return __init__


def _make_operator(name, func):
    """
    Create operator method.
    """

    def method(self, other):
        if not self._is_comparable_to(other):
            return NotImplemented

        result = func(self.value, other.value)
        if result is NotImplemented:
            return NotImplemented

        return result

    method.__name__ = f"__{name}__"
    method.__doc__ = (
        f"Return a {_operation_names[name]} b.  Computed by attrs."
    )

    return method


def _is_comparable_to(self, other):
    """
    Check whether `other` is comparable to `self`.
    """
    return all(func(self, other) for func in self._requirements)


def _check_same_type(self, other):
    """
    Return True if *self* and *other* are of the same type, False otherwise.
    """
    return other.value.__class__ is self.value.__class__

# === NexusCore/openenv\Lib\site-packages\PIL\ImageStat.py ===
#
# The Python Imaging Library.
# $Id$
#
# global image statistics
#
# History:
# 1996-04-05 fl   Created
# 1997-05-21 fl   Added mask; added rms, var, stddev attributes
# 1997-08-05 fl   Added median
# 1998-07-05 hk   Fixed integer overflow error
#
# Notes:
# This class shows how to implement delayed evaluation of attributes.
# To get a certain value, simply access the corresponding attribute.
# The __getattr__ dispatcher takes care of the rest.
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1996-97.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import math
from functools import cached_property

from . import Image


class Stat:
    def __init__(
        self, image_or_list: Image.Image | list[int], mask: Image.Image | None = None
    ) -> None:
        """
        Calculate statistics for the given image. If a mask is included,
        only the regions covered by that mask are included in the
        statistics. You can also pass in a previously calculated histogram.

        :param image: A PIL image, or a precalculated histogram.

            .. note::

                For a PIL image, calculations rely on the
                :py:meth:`~PIL.Image.Image.histogram` method. The pixel counts are
                grouped into 256 bins, even if the image has more than 8 bits per
                channel. So ``I`` and ``F`` mode images have a maximum ``mean``,
                ``median`` and ``rms`` of 255, and cannot have an ``extrema`` maximum
                of more than 255.

        :param mask: An optional mask.
        """
        if isinstance(image_or_list, Image.Image):
            self.h = image_or_list.histogram(mask)
        elif isinstance(image_or_list, list):
            self.h = image_or_list
        else:
            msg = "first argument must be image or list"  # type: ignore[unreachable]
            raise TypeError(msg)
        self.bands = list(range(len(self.h) // 256))

    @cached_property
    def extrema(self) -> list[tuple[int, int]]:
        """
        Min/max values for each band in the image.

        .. note::
            This relies on the :py:meth:`~PIL.Image.Image.histogram` method, and
            simply returns the low and high bins used. This is correct for
            images with 8 bits per channel, but fails for other modes such as
            ``I`` or ``F``. Instead, use :py:meth:`~PIL.Image.Image.getextrema` to
            return per-band extrema for the image. This is more correct and
            efficient because, for non-8-bit modes, the histogram method uses
            :py:meth:`~PIL.Image.Image.getextrema` to determine the bins used.
        """

        def minmax(histogram: list[int]) -> tuple[int, int]:
            res_min, res_max = 255, 0
            for i in range(256):
                if histogram[i]:
                    res_min = i
                    break
            for i in range(255, -1, -1):
                if histogram[i]:
                    res_max = i
                    break
            return res_min, res_max

        return [minmax(self.h[i:]) for i in range(0, len(self.h), 256)]

    @cached_property
    def count(self) -> list[int]:
        """Total number of pixels for each band in the image."""
        return [sum(self.h[i : i + 256]) for i in range(0, len(self.h), 256)]

    @cached_property
    def sum(self) -> list[float]:
        """Sum of all pixels for each band in the image."""

        v = []
        for i in range(0, len(self.h), 256):
            layer_sum = 0.0
            for j in range(256):
                layer_sum += j * self.h[i + j]
            v.append(layer_sum)
        return v

    @cached_property
    def sum2(self) -> list[float]:
        """Squared sum of all pixels for each band in the image."""

        v = []
        for i in range(0, len(self.h), 256):
            sum2 = 0.0
            for j in range(256):
                sum2 += (j**2) * float(self.h[i + j])
            v.append(sum2)
        return v

    @cached_property
    def mean(self) -> list[float]:
        """Average (arithmetic mean) pixel level for each band in the image."""
        return [self.sum[i] / self.count[i] for i in self.bands]

    @cached_property
    def median(self) -> list[int]:
        """Median pixel level for each band in the image."""

        v = []
        for i in self.bands:
            s = 0
            half = self.count[i] // 2
            b = i * 256
            for j in range(256):
                s = s + self.h[b + j]
                if s > half:
                    break
            v.append(j)
        return v

    @cached_property
    def rms(self) -> list[float]:
        """RMS (root-mean-square) for each band in the image."""
        return [math.sqrt(self.sum2[i] / self.count[i]) for i in self.bands]

    @cached_property
    def var(self) -> list[float]:
        """Variance for each band in the image."""
        return [
            (self.sum2[i] - (self.sum[i] ** 2.0) / self.count[i]) / self.count[i]
            for i in self.bands
        ]

    @cached_property
    def stddev(self) -> list[float]:
        """Standard deviation for each band in the image."""
        return [math.sqrt(self.var[i]) for i in self.bands]


Global = Stat  # compatibility

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_h_m_t_x.py ===
from fontTools.misc.roundTools import otRound
from fontTools import ttLib
from fontTools.misc.textTools import safeEval
from . import DefaultTable
import sys
import struct
import array
import logging


log = logging.getLogger(__name__)


class table__h_m_t_x(DefaultTable.DefaultTable):
    """Horizontal Metrics table

    The ``hmtx`` table contains per-glyph metrics for the glyphs in a
    ``glyf``, ``CFF ``, or ``CFF2`` table, as needed for horizontal text
    layout.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/hmtx
    """

    headerTag = "hhea"
    advanceName = "width"
    sideBearingName = "lsb"
    numberOfMetricsName = "numberOfHMetrics"
    longMetricFormat = "Hh"

    def decompile(self, data, ttFont):
        numGlyphs = ttFont["maxp"].numGlyphs
        headerTable = ttFont.get(self.headerTag)
        if headerTable is not None:
            numberOfMetrics = int(getattr(headerTable, self.numberOfMetricsName))
        else:
            numberOfMetrics = numGlyphs
        if numberOfMetrics > numGlyphs:
            log.warning(
                "The %s.%s exceeds the maxp.numGlyphs"
                % (self.headerTag, self.numberOfMetricsName)
            )
            numberOfMetrics = numGlyphs
        if len(data) < 4 * numberOfMetrics:
            raise ttLib.TTLibError("not enough '%s' table data" % self.tableTag)
        # Note: advanceWidth is unsigned, but some font editors might
        # read/write as signed. We can't be sure whether it was a mistake
        # or not, so we read as unsigned but also issue a warning...
        metricsFmt = ">" + self.longMetricFormat * numberOfMetrics
        metrics = struct.unpack(metricsFmt, data[: 4 * numberOfMetrics])
        data = data[4 * numberOfMetrics :]
        numberOfSideBearings = numGlyphs - numberOfMetrics
        sideBearings = array.array("h", data[: 2 * numberOfSideBearings])
        data = data[2 * numberOfSideBearings :]

        if sys.byteorder != "big":
            sideBearings.byteswap()
        if data:
            log.warning("too much '%s' table data" % self.tableTag)
        self.metrics = {}
        glyphOrder = ttFont.getGlyphOrder()
        for i in range(numberOfMetrics):
            glyphName = glyphOrder[i]
            advanceWidth, lsb = metrics[i * 2 : i * 2 + 2]
            if advanceWidth > 32767:
                log.warning(
                    "Glyph %r has a huge advance %s (%d); is it intentional or "
                    "an (invalid) negative value?",
                    glyphName,
                    self.advanceName,
                    advanceWidth,
                )
            self.metrics[glyphName] = (advanceWidth, lsb)
        lastAdvance = metrics[-2]
        for i in range(numberOfSideBearings):
            glyphName = glyphOrder[i + numberOfMetrics]
            self.metrics[glyphName] = (lastAdvance, sideBearings[i])

    def compile(self, ttFont):
        metrics = []
        hasNegativeAdvances = False
        for glyphName in ttFont.getGlyphOrder():
            advanceWidth, sideBearing = self.metrics[glyphName]
            if advanceWidth < 0:
                log.error(
                    "Glyph %r has negative advance %s" % (glyphName, self.advanceName)
                )
                hasNegativeAdvances = True
            metrics.append([advanceWidth, sideBearing])

        headerTable = ttFont.get(self.headerTag)
        if headerTable is not None:
            lastAdvance = metrics[-1][0]
            lastIndex = len(metrics)
            while metrics[lastIndex - 2][0] == lastAdvance:
                lastIndex -= 1
                if lastIndex <= 1:
                    # all advances are equal
                    lastIndex = 1
                    break
            additionalMetrics = metrics[lastIndex:]
            additionalMetrics = [otRound(sb) for _, sb in additionalMetrics]
            metrics = metrics[:lastIndex]
            numberOfMetrics = len(metrics)
            setattr(headerTable, self.numberOfMetricsName, numberOfMetrics)
        else:
            # no hhea/vhea, can't store numberOfMetrics; assume == numGlyphs
            numberOfMetrics = ttFont["maxp"].numGlyphs
            additionalMetrics = []

        allMetrics = []
        for advance, sb in metrics:
            allMetrics.extend([otRound(advance), otRound(sb)])
        metricsFmt = ">" + self.longMetricFormat * numberOfMetrics
        try:
            data = struct.pack(metricsFmt, *allMetrics)
        except struct.error as e:
            if "out of range" in str(e) and hasNegativeAdvances:
                raise ttLib.TTLibError(
                    "'%s' table can't contain negative advance %ss"
                    % (self.tableTag, self.advanceName)
                )
            else:
                raise
        additionalMetrics = array.array("h", additionalMetrics)
        if sys.byteorder != "big":
            additionalMetrics.byteswap()
        data = data + additionalMetrics.tobytes()
        return data

    def toXML(self, writer, ttFont):
        names = sorted(self.metrics.keys())
        for glyphName in names:
            advance, sb = self.metrics[glyphName]
            writer.simpletag(
                "mtx",
                [
                    ("name", glyphName),
                    (self.advanceName, advance),
                    (self.sideBearingName, sb),
                ],
            )
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if not hasattr(self, "metrics"):
            self.metrics = {}
        if name == "mtx":
            self.metrics[attrs["name"]] = (
                safeEval(attrs[self.advanceName]),
                safeEval(attrs[self.sideBearingName]),
            )

    def __delitem__(self, glyphName):
        del self.metrics[glyphName]

    def __getitem__(self, glyphName):
        return self.metrics[glyphName]

    def __setitem__(self, glyphName, advance_sb_pair):
        self.metrics[glyphName] = tuple(advance_sb_pair)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\oobabooga\chat\oobabooga.py ===
import json
from typing import Any, Callable, Optional

import litellm
from litellm.llms.custom_httpx.http_handler import _get_httpx_client
from litellm.utils import EmbeddingResponse, ModelResponse, Usage

from ..common_utils import OobaboogaError
from .transformation import OobaboogaConfig

oobabooga_config = OobaboogaConfig()


def completion(
    model: str,
    messages: list,
    api_base: Optional[str],
    model_response: ModelResponse,
    print_verbose: Callable,
    encoding,
    api_key,
    logging_obj,
    optional_params: dict,
    litellm_params: dict,
    custom_prompt_dict={},
    logger_fn=None,
    default_max_tokens_to_sample=None,
):
    headers = oobabooga_config.validate_environment(
        api_key=api_key,
        headers={},
        model=model,
        messages=messages,
        optional_params=optional_params,
        litellm_params=litellm_params,
    )
    if "https" in model:
        completion_url = model
    elif api_base:
        completion_url = api_base
    else:
        raise OobaboogaError(
            status_code=404,
            message="API Base not set. Set one via completion(..,api_base='your-api-url')",
        )
    model = model

    completion_url = completion_url + "/v1/chat/completions"
    data = oobabooga_config.transform_request(
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
        additional_args={"complete_input_dict": data},
    )
    ## COMPLETION CALL
    client = _get_httpx_client()
    response = client.post(
        completion_url,
        headers=headers,
        data=json.dumps(data),
        stream=optional_params["stream"] if "stream" in optional_params else False,
    )
    if "stream" in optional_params and optional_params["stream"] is True:
        return response.iter_lines()
    else:
        return oobabooga_config.transform_response(
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
        )


def embedding(
    model: str,
    input: list,
    model_response: EmbeddingResponse,
    api_key: Optional[str],
    api_base: Optional[str],
    logging_obj: Any,
    optional_params: dict,
    encoding=None,
):
    # Create completion URL
    if "https" in model:
        embeddings_url = model
    elif api_base:
        embeddings_url = f"{api_base}/v1/embeddings"
    else:
        raise OobaboogaError(
            status_code=404,
            message="API Base not set. Set one via completion(..,api_base='your-api-url')",
        )

    # Prepare request data
    data = {"input": input}
    if optional_params:
        data.update(optional_params)

    # Logging before API call
    if logging_obj:
        logging_obj.pre_call(
            input=input, api_key=api_key, additional_args={"complete_input_dict": data}
        )

    # Send POST request
    headers = oobabooga_config.validate_environment(
        api_key=api_key,
        headers={},
        model=model,
        messages=[],
        optional_params=optional_params,
        litellm_params={},
    )
    response = litellm.module_level_client.post(
        embeddings_url, headers=headers, json=data
    )
    completion_response = response.json()

    # Check for errors in response
    if "error" in completion_response:
        raise OobaboogaError(
            message=completion_response["error"],
            status_code=completion_response.get("status_code", 500),
        )

    # Process response data
    model_response.data = [
        {
            "embedding": completion_response["data"][0]["embedding"],
            "index": 0,
            "object": "embedding",
        }
    ]

    num_tokens = len(completion_response["data"][0]["embedding"])
    # Adding metadata to response
    setattr(
        model_response,
        "usage",
        Usage(prompt_tokens=num_tokens, total_tokens=num_tokens),
    )
    model_response.object = "list"
    model_response.model = model

    return model_response

# === NexusCore/openenv\Lib\site-packages\nltk\chat\iesha.py ===
# Natural Language Toolkit: Teen Chatbot
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Selina Dennis <sjmd@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This chatbot is a tongue-in-cheek take on the average teen
anime junky that frequents YahooMessenger or MSNM.
All spelling mistakes and flawed grammar are intentional.
"""

from nltk.chat.util import Chat

reflections = {
    "am": "r",
    "was": "were",
    "i": "u",
    "i'd": "u'd",
    "i've": "u'v",
    "ive": "u'v",
    "i'll": "u'll",
    "my": "ur",
    "are": "am",
    "you're": "im",
    "you've": "ive",
    "you'll": "i'll",
    "your": "my",
    "yours": "mine",
    "you": "me",
    "u": "me",
    "ur": "my",
    "urs": "mine",
    "me": "u",
}

# Note: %1/2/etc are used without spaces prior as the chat bot seems
# to add a superfluous space when matching.

pairs = (
    (
        r"I\'m (.*)",
        (
            "ur%1?? that's so cool! kekekekeke ^_^ tell me more!",
            "ur%1? neat!! kekeke >_<",
        ),
    ),
    (
        r"(.*) don\'t you (.*)",
        (
            r"u think I can%2??! really?? kekeke \<_\<",
            "what do u mean%2??!",
            "i could if i wanted, don't you think!! kekeke",
        ),
    ),
    (r"ye[as] [iI] (.*)", ("u%1? cool!! how?", "how come u%1??", "u%1? so do i!!")),
    (
        r"do (you|u) (.*)\??",
        ("do i%2? only on tuesdays! kekeke *_*", "i dunno! do u%2??"),
    ),
    (
        r"(.*)\?",
        (
            "man u ask lots of questions!",
            "booooring! how old r u??",
            "boooooring!! ur not very fun",
        ),
    ),
    (
        r"(cos|because) (.*)",
        ("hee! i don't believe u! >_<", "nuh-uh! >_<", "ooooh i agree!"),
    ),
    (
        r"why can\'t [iI] (.*)",
        (
            "i dunno! y u askin me for!",
            "try harder, silly! hee! ^_^",
            "i dunno! but when i can't%1 i jump up and down!",
        ),
    ),
    (
        r"I can\'t (.*)",
        (
            "u can't what??! >_<",
            "that's ok! i can't%1 either! kekekekeke ^_^",
            "try harder, silly! hee! ^&^",
        ),
    ),
    (
        r"(.*) (like|love|watch) anime",
        (
            "omg i love anime!! do u like sailor moon??! ^&^",
            "anime yay! anime rocks sooooo much!",
            "oooh anime! i love anime more than anything!",
            "anime is the bestest evar! evangelion is the best!",
            "hee anime is the best! do you have ur fav??",
        ),
    ),
    (
        r"I (like|love|watch|play) (.*)",
        ("yay! %2 rocks!", "yay! %2 is neat!", "cool! do u like other stuff?? ^_^"),
    ),
    (
        r"anime sucks|(.*) (hate|detest) anime",
        (
            "ur a liar! i'm not gonna talk to u nemore if u h8 anime *;*",
            "no way! anime is the best ever!",
            "nuh-uh, anime is the best!",
        ),
    ),
    (
        r"(are|r) (you|u) (.*)",
        ("am i%1??! how come u ask that!", "maybe!  y shud i tell u?? kekeke >_>"),
    ),
    (
        r"what (.*)",
        ("hee u think im gonna tell u? .v.", "booooooooring! ask me somethin else!"),
    ),
    (r"how (.*)", ("not tellin!! kekekekekeke ^_^",)),
    (r"(hi|hello|hey) (.*)", ("hi!!! how r u!!",)),
    (
        r"quit",
        (
            "mom says i have to go eat dinner now :,( bye!!",
            "awww u have to go?? see u next time!!",
            "how to see u again soon! ^_^",
        ),
    ),
    (
        r"(.*)",
        (
            "ur funny! kekeke",
            "boooooring! talk about something else! tell me wat u like!",
            "do u like anime??",
            "do u watch anime? i like sailor moon! ^_^",
            "i wish i was a kitty!! kekekeke ^_^",
        ),
    ),
)

iesha_chatbot = Chat(pairs, reflections)


def iesha_chat():
    print("Iesha the TeenBoT\n---------")
    print("Talk to the program by typing in plain English, using normal upper-")
    print('and lower-case letters and punctuation.  Enter "quit" when done.')
    print("=" * 72)
    print("hi!! i'm iesha! who r u??!")

    iesha_chatbot.converse()


def demo():
    iesha_chat()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\test_disagreement.py ===
import unittest

from nltk.metrics.agreement import AnnotationTask


class TestDisagreement(unittest.TestCase):
    """
    Class containing unit tests for nltk.metrics.agreement.Disagreement.
    """

    def test_easy(self):
        """
        Simple test, based on
        https://github.com/foolswood/krippendorffs_alpha/raw/master/krippendorff.pdf.
        """
        data = [
            ("coder1", "dress1", "YES"),
            ("coder2", "dress1", "NO"),
            ("coder3", "dress1", "NO"),
            ("coder1", "dress2", "YES"),
            ("coder2", "dress2", "NO"),
            ("coder3", "dress3", "NO"),
        ]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), -0.3333333)

    def test_easy2(self):
        """
        Same simple test with 1 rating removed.
        Removal of that rating should not matter: K-Apha ignores items with
        only 1 rating.
        """
        data = [
            ("coder1", "dress1", "YES"),
            ("coder2", "dress1", "NO"),
            ("coder3", "dress1", "NO"),
            ("coder1", "dress2", "YES"),
            ("coder2", "dress2", "NO"),
        ]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), -0.3333333)

    def test_easy3(self):
        """
        If expected disagreement is 0, K-Apha should be 1.
        """
        data = [
            ("coder1", "1", 1),
            ("coder2", "1", 1),
            ("coder1", "2", 2),
            ("coder2", "2", 2),
        ]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), 1.0)

        data = [("coder1", "1", 1), ("coder2", "1", 1), ("coder1", "2", 2)]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), 1.0)

    def test_advanced(self):
        """
        More advanced test, based on
        http://www.agreestat.com/research_papers/onkrippendorffalpha.pdf
        """
        data = [
            ("A", "1", "1"),
            ("B", "1", "1"),
            ("D", "1", "1"),
            ("A", "2", "2"),
            ("B", "2", "2"),
            ("C", "2", "3"),
            ("D", "2", "2"),
            ("A", "3", "3"),
            ("B", "3", "3"),
            ("C", "3", "3"),
            ("D", "3", "3"),
            ("A", "4", "3"),
            ("B", "4", "3"),
            ("C", "4", "3"),
            ("D", "4", "3"),
            ("A", "5", "2"),
            ("B", "5", "2"),
            ("C", "5", "2"),
            ("D", "5", "2"),
            ("A", "6", "1"),
            ("B", "6", "2"),
            ("C", "6", "3"),
            ("D", "6", "4"),
            ("A", "7", "4"),
            ("B", "7", "4"),
            ("C", "7", "4"),
            ("D", "7", "4"),
            ("A", "8", "1"),
            ("B", "8", "1"),
            ("C", "8", "2"),
            ("D", "8", "1"),
            ("A", "9", "2"),
            ("B", "9", "2"),
            ("C", "9", "2"),
            ("D", "9", "2"),
            ("B", "10", "5"),
            ("C", "10", "5"),
            ("D", "10", "5"),
            ("C", "11", "1"),
            ("D", "11", "1"),
            ("C", "12", "3"),
        ]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), 0.743421052632)

    def test_advanced2(self):
        """
        Same more advanced example, but with 1 rating removed.
        Again, removal of that 1 rating should not matter.
        """
        data = [
            ("A", "1", "1"),
            ("B", "1", "1"),
            ("D", "1", "1"),
            ("A", "2", "2"),
            ("B", "2", "2"),
            ("C", "2", "3"),
            ("D", "2", "2"),
            ("A", "3", "3"),
            ("B", "3", "3"),
            ("C", "3", "3"),
            ("D", "3", "3"),
            ("A", "4", "3"),
            ("B", "4", "3"),
            ("C", "4", "3"),
            ("D", "4", "3"),
            ("A", "5", "2"),
            ("B", "5", "2"),
            ("C", "5", "2"),
            ("D", "5", "2"),
            ("A", "6", "1"),
            ("B", "6", "2"),
            ("C", "6", "3"),
            ("D", "6", "4"),
            ("A", "7", "4"),
            ("B", "7", "4"),
            ("C", "7", "4"),
            ("D", "7", "4"),
            ("A", "8", "1"),
            ("B", "8", "1"),
            ("C", "8", "2"),
            ("D", "8", "1"),
            ("A", "9", "2"),
            ("B", "9", "2"),
            ("C", "9", "2"),
            ("D", "9", "2"),
            ("B", "10", "5"),
            ("C", "10", "5"),
            ("D", "10", "5"),
            ("C", "11", "1"),
            ("D", "11", "1"),
            ("C", "12", "3"),
        ]
        annotation_task = AnnotationTask(data)
        self.assertAlmostEqual(annotation_task.alpha(), 0.743421052632)

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\translate\test_ibm5.py ===
"""
Tests for IBM Model 5 training methods
"""

import unittest
from collections import defaultdict

from nltk.translate import AlignedSent, IBMModel, IBMModel4, IBMModel5
from nltk.translate.ibm_model import AlignmentInfo


class TestIBMModel5(unittest.TestCase):
    def test_set_uniform_vacancy_probabilities_of_max_displacements(self):
        # arrange
        src_classes = {"schinken": 0, "eier": 0, "spam": 1}
        trg_classes = {"ham": 0, "eggs": 1, "spam": 2}
        corpus = [
            AlignedSent(["ham", "eggs"], ["schinken", "schinken", "eier"]),
            AlignedSent(["spam", "spam", "spam", "spam"], ["spam", "spam"]),
        ]
        model5 = IBMModel5(corpus, 0, src_classes, trg_classes)

        # act
        model5.set_uniform_probabilities(corpus)

        # assert
        # number of vacancy difference values =
        #     2 * number of words in longest target sentence
        expected_prob = 1.0 / (2 * 4)

        # examine the boundary values for (dv, max_v, trg_class)
        self.assertEqual(model5.head_vacancy_table[4][4][0], expected_prob)
        self.assertEqual(model5.head_vacancy_table[-3][1][2], expected_prob)
        self.assertEqual(model5.non_head_vacancy_table[4][4][0], expected_prob)
        self.assertEqual(model5.non_head_vacancy_table[-3][1][2], expected_prob)

    def test_set_uniform_vacancy_probabilities_of_non_domain_values(self):
        # arrange
        src_classes = {"schinken": 0, "eier": 0, "spam": 1}
        trg_classes = {"ham": 0, "eggs": 1, "spam": 2}
        corpus = [
            AlignedSent(["ham", "eggs"], ["schinken", "schinken", "eier"]),
            AlignedSent(["spam", "spam", "spam", "spam"], ["spam", "spam"]),
        ]
        model5 = IBMModel5(corpus, 0, src_classes, trg_classes)

        # act
        model5.set_uniform_probabilities(corpus)

        # assert
        # examine dv and max_v values that are not in the training data domain
        self.assertEqual(model5.head_vacancy_table[5][4][0], IBMModel.MIN_PROB)
        self.assertEqual(model5.head_vacancy_table[-4][1][2], IBMModel.MIN_PROB)
        self.assertEqual(model5.head_vacancy_table[4][0][0], IBMModel.MIN_PROB)
        self.assertEqual(model5.non_head_vacancy_table[5][4][0], IBMModel.MIN_PROB)
        self.assertEqual(model5.non_head_vacancy_table[-4][1][2], IBMModel.MIN_PROB)

    def test_prob_t_a_given_s(self):
        # arrange
        src_sentence = ["ich", "esse", "ja", "gern", "räucherschinken"]
        trg_sentence = ["i", "love", "to", "eat", "smoked", "ham"]
        src_classes = {"räucherschinken": 0, "ja": 1, "ich": 2, "esse": 3, "gern": 4}
        trg_classes = {"ham": 0, "smoked": 1, "i": 3, "love": 4, "to": 2, "eat": 4}
        corpus = [AlignedSent(trg_sentence, src_sentence)]
        alignment_info = AlignmentInfo(
            (0, 1, 4, 0, 2, 5, 5),
            [None] + src_sentence,
            ["UNUSED"] + trg_sentence,
            [[3], [1], [4], [], [2], [5, 6]],
        )

        head_vacancy_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )
        head_vacancy_table[1 - 0][6][3] = 0.97  # ich -> i
        head_vacancy_table[3 - 0][5][4] = 0.97  # esse -> eat
        head_vacancy_table[1 - 2][4][4] = 0.97  # gern -> love
        head_vacancy_table[2 - 0][2][1] = 0.97  # räucherschinken -> smoked

        non_head_vacancy_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )
        non_head_vacancy_table[1 - 0][1][0] = 0.96  # räucherschinken -> ham

        translation_table = defaultdict(lambda: defaultdict(float))
        translation_table["i"]["ich"] = 0.98
        translation_table["love"]["gern"] = 0.98
        translation_table["to"][None] = 0.98
        translation_table["eat"]["esse"] = 0.98
        translation_table["smoked"]["räucherschinken"] = 0.98
        translation_table["ham"]["räucherschinken"] = 0.98

        fertility_table = defaultdict(lambda: defaultdict(float))
        fertility_table[1]["ich"] = 0.99
        fertility_table[1]["esse"] = 0.99
        fertility_table[0]["ja"] = 0.99
        fertility_table[1]["gern"] = 0.99
        fertility_table[2]["räucherschinken"] = 0.999
        fertility_table[1][None] = 0.99

        probabilities = {
            "p1": 0.167,
            "translation_table": translation_table,
            "fertility_table": fertility_table,
            "head_vacancy_table": head_vacancy_table,
            "non_head_vacancy_table": non_head_vacancy_table,
            "head_distortion_table": None,
            "non_head_distortion_table": None,
            "alignment_table": None,
        }

        model5 = IBMModel5(corpus, 0, src_classes, trg_classes, probabilities)

        # act
        probability = model5.prob_t_a_given_s(alignment_info)

        # assert
        null_generation = 5 * pow(0.167, 1) * pow(0.833, 4)
        fertility = 1 * 0.99 * 1 * 0.99 * 1 * 0.99 * 1 * 0.99 * 2 * 0.999
        lexical_translation = 0.98 * 0.98 * 0.98 * 0.98 * 0.98 * 0.98
        vacancy = 0.97 * 0.97 * 1 * 0.97 * 0.97 * 0.96
        expected_probability = (
            null_generation * fertility * lexical_translation * vacancy
        )
        self.assertEqual(round(probability, 4), round(expected_probability, 4))

    def test_prune(self):
        # arrange
        alignment_infos = [
            AlignmentInfo((1, 1), None, None, None),
            AlignmentInfo((1, 2), None, None, None),
            AlignmentInfo((2, 1), None, None, None),
            AlignmentInfo((2, 2), None, None, None),
            AlignmentInfo((0, 0), None, None, None),
        ]
        min_factor = IBMModel5.MIN_SCORE_FACTOR
        best_score = 0.9
        scores = {
            (1, 1): min(min_factor * 1.5, 1) * best_score,  # above threshold
            (1, 2): best_score,
            (2, 1): min_factor * best_score,  # at threshold
            (2, 2): min_factor * best_score * 0.5,  # low score
            (0, 0): min(min_factor * 1.1, 1) * 1.2,  # above threshold
        }
        corpus = [AlignedSent(["a"], ["b"])]
        original_prob_function = IBMModel4.model4_prob_t_a_given_s
        # mock static method
        IBMModel4.model4_prob_t_a_given_s = staticmethod(
            lambda a, model: scores[a.alignment]
        )
        model5 = IBMModel5(corpus, 0, None, None)

        # act
        pruned_alignments = model5.prune(alignment_infos)

        # assert
        self.assertEqual(len(pruned_alignments), 3)

        # restore static method
        IBMModel4.model4_prob_t_a_given_s = original_prob_function

# === NexusCore/openenv\Lib\site-packages\openai\cli\_api\chat\completions.py ===
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, List, Optional, cast
from argparse import ArgumentParser
from typing_extensions import Literal, NamedTuple

from ..._utils import get_client
from ..._models import BaseModel
from ...._streaming import Stream
from ....types.chat import (
    ChatCompletionRole,
    ChatCompletionChunk,
    CompletionCreateParams,
)
from ....types.chat.completion_create_params import (
    CompletionCreateParamsStreaming,
    CompletionCreateParamsNonStreaming,
)

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def register(subparser: _SubParsersAction[ArgumentParser]) -> None:
    sub = subparser.add_parser("chat.completions.create")

    sub._action_groups.pop()
    req = sub.add_argument_group("required arguments")
    opt = sub.add_argument_group("optional arguments")

    req.add_argument(
        "-g",
        "--message",
        action="append",
        nargs=2,
        metavar=("ROLE", "CONTENT"),
        help="A message in `{role} {content}` format. Use this argument multiple times to add multiple messages.",
        required=True,
    )
    req.add_argument(
        "-m",
        "--model",
        help="The model to use.",
        required=True,
    )

    opt.add_argument(
        "-n",
        "--n",
        help="How many completions to generate for the conversation.",
        type=int,
    )
    opt.add_argument("-M", "--max-tokens", help="The maximum number of tokens to generate.", type=int)
    opt.add_argument(
        "-t",
        "--temperature",
        help="""What sampling temperature to use. Higher values means the model will take more risks. Try 0.9 for more creative applications, and 0 (argmax sampling) for ones with a well-defined answer.

Mutually exclusive with `top_p`.""",
        type=float,
    )
    opt.add_argument(
        "-P",
        "--top_p",
        help="""An alternative to sampling with temperature, called nucleus sampling, where the considers the results of the tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10%% probability mass are considered.

            Mutually exclusive with `temperature`.""",
        type=float,
    )
    opt.add_argument(
        "--stop",
        help="A stop sequence at which to stop generating tokens for the message.",
    )
    opt.add_argument("--stream", help="Stream messages as they're ready.", action="store_true")
    sub.set_defaults(func=CLIChatCompletion.create, args_model=CLIChatCompletionCreateArgs)


class CLIMessage(NamedTuple):
    role: ChatCompletionRole
    content: str


class CLIChatCompletionCreateArgs(BaseModel):
    message: List[CLIMessage]
    model: str
    n: Optional[int] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stop: Optional[str] = None
    stream: bool = False


class CLIChatCompletion:
    @staticmethod
    def create(args: CLIChatCompletionCreateArgs) -> None:
        params: CompletionCreateParams = {
            "model": args.model,
            "messages": [
                {"role": cast(Literal["user"], message.role), "content": message.content} for message in args.message
            ],
            # type checkers are not good at inferring union types so we have to set stream afterwards
            "stream": False,
        }
        if args.temperature is not None:
            params["temperature"] = args.temperature
        if args.stop is not None:
            params["stop"] = args.stop
        if args.top_p is not None:
            params["top_p"] = args.top_p
        if args.n is not None:
            params["n"] = args.n
        if args.stream:
            params["stream"] = args.stream  # type: ignore
        if args.max_tokens is not None:
            params["max_tokens"] = args.max_tokens

        if args.stream:
            return CLIChatCompletion._stream_create(cast(CompletionCreateParamsStreaming, params))

        return CLIChatCompletion._create(cast(CompletionCreateParamsNonStreaming, params))

    @staticmethod
    def _create(params: CompletionCreateParamsNonStreaming) -> None:
        completion = get_client().chat.completions.create(**params)
        should_print_header = len(completion.choices) > 1
        for choice in completion.choices:
            if should_print_header:
                sys.stdout.write("===== Chat Completion {} =====\n".format(choice.index))

            content = choice.message.content if choice.message.content is not None else "None"
            sys.stdout.write(content)

            if should_print_header or not content.endswith("\n"):
                sys.stdout.write("\n")

            sys.stdout.flush()

    @staticmethod
    def _stream_create(params: CompletionCreateParamsStreaming) -> None:
        # cast is required for mypy
        stream = cast(  # pyright: ignore[reportUnnecessaryCast]
            Stream[ChatCompletionChunk], get_client().chat.completions.create(**params)
        )
        for chunk in stream:
            should_print_header = len(chunk.choices) > 1
            for choice in chunk.choices:
                if should_print_header:
                    sys.stdout.write("===== Chat Completion {} =====\n".format(choice.index))

                content = choice.delta.content or ""
                sys.stdout.write(content)

                if should_print_header:
                    sys.stdout.write("\n")

                sys.stdout.flush()

        sys.stdout.write("\n")

# === NexusCore/openenv\Lib\site-packages\parso\pgen2\grammar_parser.py ===
# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

# Modifications:
# Copyright David Halter and Contributors
# Modifications are dual-licensed: MIT and PSF.
from typing import Optional, Iterator, Tuple, List

from parso.python.tokenize import tokenize
from parso.utils import parse_version_string
from parso.python.token import PythonTokenTypes


class NFAArc:
    def __init__(self, next_: 'NFAState', nonterminal_or_string: Optional[str]):
        self.next: NFAState = next_
        self.nonterminal_or_string: Optional[str] = nonterminal_or_string

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.nonterminal_or_string)


class NFAState:
    def __init__(self, from_rule: str):
        self.from_rule: str = from_rule
        self.arcs: List[NFAArc] = []

    def add_arc(self, next_, nonterminal_or_string=None):
        assert nonterminal_or_string is None or isinstance(nonterminal_or_string, str)
        assert isinstance(next_, NFAState)
        self.arcs.append(NFAArc(next_, nonterminal_or_string))

    def __repr__(self):
        return '<%s: from %s>' % (self.__class__.__name__, self.from_rule)


class GrammarParser:
    """
    The parser for Python grammar files.
    """
    def __init__(self, bnf_grammar: str):
        self._bnf_grammar = bnf_grammar
        self.generator = tokenize(
            bnf_grammar,
            version_info=parse_version_string('3.9')
        )
        self._gettoken()  # Initialize lookahead

    def parse(self) -> Iterator[Tuple[NFAState, NFAState]]:
        # grammar: (NEWLINE | rule)* ENDMARKER
        while self.type != PythonTokenTypes.ENDMARKER:
            while self.type == PythonTokenTypes.NEWLINE:
                self._gettoken()

            # rule: NAME ':' rhs NEWLINE
            self._current_rule_name = self._expect(PythonTokenTypes.NAME)
            self._expect(PythonTokenTypes.OP, ':')

            a, z = self._parse_rhs()
            self._expect(PythonTokenTypes.NEWLINE)

            yield a, z

    def _parse_rhs(self):
        # rhs: items ('|' items)*
        a, z = self._parse_items()
        if self.value != "|":
            return a, z
        else:
            aa = NFAState(self._current_rule_name)
            zz = NFAState(self._current_rule_name)
            while True:
                # Add the possibility to go into the state of a and come back
                # to finish.
                aa.add_arc(a)
                z.add_arc(zz)
                if self.value != "|":
                    break

                self._gettoken()
                a, z = self._parse_items()
            return aa, zz

    def _parse_items(self):
        # items: item+
        a, b = self._parse_item()
        while self.type in (PythonTokenTypes.NAME, PythonTokenTypes.STRING) \
                or self.value in ('(', '['):
            c, d = self._parse_item()
            # Need to end on the next item.
            b.add_arc(c)
            b = d
        return a, b

    def _parse_item(self):
        # item: '[' rhs ']' | atom ['+' | '*']
        if self.value == "[":
            self._gettoken()
            a, z = self._parse_rhs()
            self._expect(PythonTokenTypes.OP, ']')
            # Make it also possible that there is no token and change the
            # state.
            a.add_arc(z)
            return a, z
        else:
            a, z = self._parse_atom()
            value = self.value
            if value not in ("+", "*"):
                return a, z
            self._gettoken()
            # Make it clear that we can go back to the old state and repeat.
            z.add_arc(a)
            if value == "+":
                return a, z
            else:
                # The end state is the same as the beginning, nothing must
                # change.
                return a, a

    def _parse_atom(self):
        # atom: '(' rhs ')' | NAME | STRING
        if self.value == "(":
            self._gettoken()
            a, z = self._parse_rhs()
            self._expect(PythonTokenTypes.OP, ')')
            return a, z
        elif self.type in (PythonTokenTypes.NAME, PythonTokenTypes.STRING):
            a = NFAState(self._current_rule_name)
            z = NFAState(self._current_rule_name)
            # Make it clear that the state transition requires that value.
            a.add_arc(z, self.value)
            self._gettoken()
            return a, z
        else:
            self._raise_error("expected (...) or NAME or STRING, got %s/%s",
                              self.type, self.value)

    def _expect(self, type_, value=None):
        if self.type != type_:
            self._raise_error("expected %s, got %s [%s]",
                              type_, self.type, self.value)
        if value is not None and self.value != value:
            self._raise_error("expected %s, got %s", value, self.value)
        value = self.value
        self._gettoken()
        return value

    def _gettoken(self):
        tup = next(self.generator)
        self.type, self.value, self.begin, prefix = tup

    def _raise_error(self, msg, *args):
        if args:
            try:
                msg = msg % args
            except:
                msg = " ".join([msg] + list(map(str, args)))
        line = self._bnf_grammar.splitlines()[self.begin[0] - 1]
        raise SyntaxError(msg, ('<grammar>', self.begin[0],
                                self.begin[1], line))

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\formatters\other.py ===
"""
    pygments.formatters.other
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Other formatters: NullFormatter, RawTokenFormatter.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.util import get_choice_opt
from pip._vendor.pygments.token import Token
from pip._vendor.pygments.console import colorize

__all__ = ['NullFormatter', 'RawTokenFormatter', 'TestcaseFormatter']


class NullFormatter(Formatter):
    """
    Output the text unchanged without any formatting.
    """
    name = 'Text only'
    aliases = ['text', 'null']
    filenames = ['*.txt']

    def format(self, tokensource, outfile):
        enc = self.encoding
        for ttype, value in tokensource:
            if enc:
                outfile.write(value.encode(enc))
            else:
                outfile.write(value)


class RawTokenFormatter(Formatter):
    r"""
    Format tokens as a raw representation for storing token streams.

    The format is ``tokentype<TAB>repr(tokenstring)\n``. The output can later
    be converted to a token stream with the `RawTokenLexer`, described in the
    :doc:`lexer list <lexers>`.

    Only two options are accepted:

    `compress`
        If set to ``'gz'`` or ``'bz2'``, compress the output with the given
        compression algorithm after encoding (default: ``''``).
    `error_color`
        If set to a color name, highlight error tokens using that color.  If
        set but with no value, defaults to ``'red'``.

        .. versionadded:: 0.11

    """
    name = 'Raw tokens'
    aliases = ['raw', 'tokens']
    filenames = ['*.raw']

    unicodeoutput = False

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        # We ignore self.encoding if it is set, since it gets set for lexer
        # and formatter if given with -Oencoding on the command line.
        # The RawTokenFormatter outputs only ASCII. Override here.
        self.encoding = 'ascii'  # let pygments.format() do the right thing
        self.compress = get_choice_opt(options, 'compress',
                                       ['', 'none', 'gz', 'bz2'], '')
        self.error_color = options.get('error_color', None)
        if self.error_color is True:
            self.error_color = 'red'
        if self.error_color is not None:
            try:
                colorize(self.error_color, '')
            except KeyError:
                raise ValueError(f"Invalid color {self.error_color!r} specified")

    def format(self, tokensource, outfile):
        try:
            outfile.write(b'')
        except TypeError:
            raise TypeError('The raw tokens formatter needs a binary '
                            'output file')
        if self.compress == 'gz':
            import gzip
            outfile = gzip.GzipFile('', 'wb', 9, outfile)

            write = outfile.write
            flush = outfile.close
        elif self.compress == 'bz2':
            import bz2
            compressor = bz2.BZ2Compressor(9)

            def write(text):
                outfile.write(compressor.compress(text))

            def flush():
                outfile.write(compressor.flush())
                outfile.flush()
        else:
            write = outfile.write
            flush = outfile.flush

        if self.error_color:
            for ttype, value in tokensource:
                line = b"%r\t%r\n" % (ttype, value)
                if ttype is Token.Error:
                    write(colorize(self.error_color, line))
                else:
                    write(line)
        else:
            for ttype, value in tokensource:
                write(b"%r\t%r\n" % (ttype, value))
        flush()


TESTCASE_BEFORE = '''\
    def testNeedsName(lexer):
        fragment = %r
        tokens = [
'''
TESTCASE_AFTER = '''\
        ]
        assert list(lexer.get_tokens(fragment)) == tokens
'''


class TestcaseFormatter(Formatter):
    """
    Format tokens as appropriate for a new testcase.

    .. versionadded:: 2.0
    """
    name = 'Testcase'
    aliases = ['testcase']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        if self.encoding is not None and self.encoding != 'utf-8':
            raise ValueError("Only None and utf-8 are allowed encodings.")

    def format(self, tokensource, outfile):
        indentation = ' ' * 12
        rawbuf = []
        outbuf = []
        for ttype, value in tokensource:
            rawbuf.append(value)
            outbuf.append(f'{indentation}({ttype}, {value!r}),\n')

        before = TESTCASE_BEFORE % (''.join(rawbuf),)
        during = ''.join(outbuf)
        after = TESTCASE_AFTER
        if self.encoding is None:
            outfile.write(before + during + after)
        else:
            outfile.write(before.encode('utf-8'))
            outfile.write(during.encode('utf-8'))
            outfile.write(after.encode('utf-8'))
        outfile.flush()

# === NexusCore/openenv\Lib\site-packages\pygments\formatters\other.py ===
"""
    pygments.formatters.other
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Other formatters: NullFormatter, RawTokenFormatter.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.formatter import Formatter
from pygments.util import get_choice_opt
from pygments.token import Token
from pygments.console import colorize

__all__ = ['NullFormatter', 'RawTokenFormatter', 'TestcaseFormatter']


class NullFormatter(Formatter):
    """
    Output the text unchanged without any formatting.
    """
    name = 'Text only'
    aliases = ['text', 'null']
    filenames = ['*.txt']

    def format(self, tokensource, outfile):
        enc = self.encoding
        for ttype, value in tokensource:
            if enc:
                outfile.write(value.encode(enc))
            else:
                outfile.write(value)


class RawTokenFormatter(Formatter):
    r"""
    Format tokens as a raw representation for storing token streams.

    The format is ``tokentype<TAB>repr(tokenstring)\n``. The output can later
    be converted to a token stream with the `RawTokenLexer`, described in the
    :doc:`lexer list <lexers>`.

    Only two options are accepted:

    `compress`
        If set to ``'gz'`` or ``'bz2'``, compress the output with the given
        compression algorithm after encoding (default: ``''``).
    `error_color`
        If set to a color name, highlight error tokens using that color.  If
        set but with no value, defaults to ``'red'``.

        .. versionadded:: 0.11

    """
    name = 'Raw tokens'
    aliases = ['raw', 'tokens']
    filenames = ['*.raw']

    unicodeoutput = False

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        # We ignore self.encoding if it is set, since it gets set for lexer
        # and formatter if given with -Oencoding on the command line.
        # The RawTokenFormatter outputs only ASCII. Override here.
        self.encoding = 'ascii'  # let pygments.format() do the right thing
        self.compress = get_choice_opt(options, 'compress',
                                       ['', 'none', 'gz', 'bz2'], '')
        self.error_color = options.get('error_color', None)
        if self.error_color is True:
            self.error_color = 'red'
        if self.error_color is not None:
            try:
                colorize(self.error_color, '')
            except KeyError:
                raise ValueError(f"Invalid color {self.error_color!r} specified")

    def format(self, tokensource, outfile):
        try:
            outfile.write(b'')
        except TypeError:
            raise TypeError('The raw tokens formatter needs a binary '
                            'output file')
        if self.compress == 'gz':
            import gzip
            outfile = gzip.GzipFile('', 'wb', 9, outfile)

            write = outfile.write
            flush = outfile.close
        elif self.compress == 'bz2':
            import bz2
            compressor = bz2.BZ2Compressor(9)

            def write(text):
                outfile.write(compressor.compress(text))

            def flush():
                outfile.write(compressor.flush())
                outfile.flush()
        else:
            write = outfile.write
            flush = outfile.flush

        if self.error_color:
            for ttype, value in tokensource:
                line = b"%r\t%r\n" % (ttype, value)
                if ttype is Token.Error:
                    write(colorize(self.error_color, line))
                else:
                    write(line)
        else:
            for ttype, value in tokensource:
                write(b"%r\t%r\n" % (ttype, value))
        flush()


TESTCASE_BEFORE = '''\
    def testNeedsName(lexer):
        fragment = %r
        tokens = [
'''
TESTCASE_AFTER = '''\
        ]
        assert list(lexer.get_tokens(fragment)) == tokens
'''


class TestcaseFormatter(Formatter):
    """
    Format tokens as appropriate for a new testcase.

    .. versionadded:: 2.0
    """
    name = 'Testcase'
    aliases = ['testcase']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        if self.encoding is not None and self.encoding != 'utf-8':
            raise ValueError("Only None and utf-8 are allowed encodings.")

    def format(self, tokensource, outfile):
        indentation = ' ' * 12
        rawbuf = []
        outbuf = []
        for ttype, value in tokensource:
            rawbuf.append(value)
            outbuf.append(f'{indentation}({ttype}, {value!r}),\n')

        before = TESTCASE_BEFORE % (''.join(rawbuf),)
        during = ''.join(outbuf)
        after = TESTCASE_AFTER
        if self.encoding is None:
            outfile.write(before + during + after)
        else:
            outfile.write(before.encode('utf-8'))
            outfile.write(during.encode('utf-8'))
            outfile.write(after.encode('utf-8'))
        outfile.flush()

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\typst.py ===
"""
    pygments.lexers.typst
    ~~~~~~~~~~~~~~~~~~~~~

    Lexers for Typst language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, words, bygroups, include
from pygments.token import Comment, Keyword, Name, String, Punctuation, \
    Whitespace, Generic, Operator, Number, Text
from pygments.util import get_choice_opt

__all__ = ['TypstLexer']


class TypstLexer(RegexLexer):
    """
    For Typst code.

    Additional options accepted:

    `start`
        Specifies the starting state of the lexer (one of 'markup', 'math',
        'code'). The default is 'markup'.
    """

    name = 'Typst'
    aliases = ['typst']
    filenames = ['*.typ']
    mimetypes = ['text/x-typst']
    url = 'https://typst.app'
    version_added = '2.18'

    MATH_SHORTHANDS = (
        '[|', '|]', '||', '*', ':=', '::=', '...', '\'', '-', '=:', '!=', '>>',
        '>=', '>>>', '<<', '<=', '<<<', '->', '|->', '=>', '|=>', '==>',
        '-->', '~~>', '~>', '>->', '->>', '<-', '<==', '<--', '<~~', '<~',
        '<-<','<<-','<->','<=>','<==>','<-->', '>', '<', '~', ':', '|'
    )

    tokens = {
        'root': [
            include('markup'),
        ],
        # common cases going from math/markup into code mode
        'into_code': [
            (words(('#let', '#set', '#show'), suffix=r'\b'), Keyword.Declaration, 'inline_code'),
            (words(('#import', '#include'), suffix=r'\b'), Keyword.Namespace, 'inline_code'),
            (words(('#if', '#for', '#while', '#export'), suffix=r'\b'), Keyword.Reserved, 'inline_code'),
            (r'#\{', Punctuation, 'code'),
            (r'#\(', Punctuation, 'code'),
            (r'(#[a-zA-Z_][a-zA-Z0-9_-]*)(\[)', bygroups(Name.Function, Punctuation), 'markup'),
            (r'(#[a-zA-Z_][a-zA-Z0-9_-]*)(\()', bygroups(Name.Function, Punctuation), 'code'),
            (words(('#true', '#false', '#none', '#auto'), suffix=r'\b'), Keyword.Constant),
            (r'#[a-zA-Z_][a-zA-Z0-9_]*', Name.Variable),
            (r'#0x[0-9a-fA-F]+', Number.Hex),
            (r'#0b[01]+', Number.Bin),
            (r'#0o[0-7]+', Number.Oct),
            (r'#[0-9]+[\.e][0-9]+', Number.Float),
            (r'#[0-9]+', Number.Integer),
        ],
        'markup': [
            include('comment'),
            (r'^\s*=+.*$', Generic.Heading),
            (r'[*][^*]*[*]', Generic.Strong),
            (r'_[^_]*_', Generic.Emph),
            (r'\$', Punctuation, 'math'),
            (r'`[^`]*`', String.Backtick),  # inline code
            (r'^(\s*)(-)(\s+)', bygroups(Whitespace, Punctuation, Whitespace)),  # unnumbered list
            (r'^(\s*)(\+)(\s+)', bygroups(Whitespace, Punctuation, Whitespace)),  # numbered list
            (r'^(\s*)([0-9]+\.)', bygroups(Whitespace, Punctuation)),  # numbered list variant
            (r'^(\s*)(/)(\s+)([^:]+)(:)', bygroups(Whitespace, Punctuation, Whitespace, Name.Variable, Punctuation)),  # definitions
            (r'<[a-zA-Z_][a-zA-Z0-9_-]*>', Name.Label),  # label
            (r'@[a-zA-Z_][a-zA-Z0-9_-]*', Name.Label),  # reference
            (r'\\#', Text), # escaped
            include('into_code'),
            (r'```(?:.|\n)*?```', String.Backtick),  # code block
            (r'https?://[0-9a-zA-Z~/%#&=\',;.+?]*', Generic.Emph),  # links
            (words(('---', '\\', '~', '--', '...'), suffix=r'\B'), Punctuation),  # special chars shorthand
            (r'\\\[', Punctuation),  # escaped
            (r'\\\]', Punctuation),  # escaped
            (r'\[', Punctuation, '#push'),
            (r'\]', Punctuation, '#pop'),
            (r'[ \t]+\n?|\n', Whitespace),
            (r'((?![*_$`<@\\#\] ]|https?://).)+', Text),
        ],
        'math': [
            include('comment'),
            (words(('\\_', '\\^', '\\&')), Text), # escapes
            (words(('_', '^', '&', ';')), Punctuation),
            (words(('+', '/', '=') + MATH_SHORTHANDS), Operator),
            (r'\\', Punctuation), # line break
            (r'\\\$', Punctuation),  # escaped
            (r'\$', Punctuation, '#pop'),  # end of math mode
            include('into_code'),
            (r'([a-zA-Z][a-zA-Z0-9-]*)(\s*)(\()', bygroups(Name.Function, Whitespace, Punctuation)),
            (r'([a-zA-Z][a-zA-Z0-9-]*)(:)', bygroups(Name.Variable, Punctuation)), # named arguments in math functions
            (r'([a-zA-Z][a-zA-Z0-9-]*)', Name.Variable), # both variables and symbols (_ isn't supported for variables)
            (r'[0-9]+(\.[0-9]+)?', Number),
            (r'\.{1,3}|\(|\)|,|\{|\}', Punctuation),
            (r'"[^"]*"', String.Double),
            (r'[ \t\n]+', Whitespace),
        ],
        'comment': [
            (r'//.*$', Comment.Single),
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
        ],
        'code': [
            include('comment'),
            (r'\[', Punctuation, 'markup'),
            (r'\(|\{', Punctuation, 'code'),
            (r'\)|\}', Punctuation, '#pop'),
            (r'"[^"]*"', String.Double),
            (r',|\.{1,2}', Punctuation),
            (r'=', Operator),
            (words(('and', 'or', 'not'), suffix=r'\b'), Operator.Word),
            (r'=>|<=|==|!=|>|<|-=|\+=|\*=|/=|\+|-|\\|\*', Operator), # comparisons
            (r'([a-zA-Z_][a-zA-Z0-9_-]*)(:)', bygroups(Name.Variable, Punctuation)),
            (r'([a-zA-Z_][a-zA-Z0-9_-]*)(\()', bygroups(Name.Function, Punctuation), 'code'),
            (words(('as', 'break', 'export', 'continue', 'else', 'for', 'if',
                    'in', 'return', 'while'), suffix=r'\b'),
             Keyword.Reserved),
             (words(('import', 'include'), suffix=r'\b'), Keyword.Namespace),
            (words(('auto', 'none', 'true', 'false'), suffix=r'\b'), Keyword.Constant),
            (r'([0-9.]+)(mm|pt|cm|in|em|fr|%)', bygroups(Number, Keyword.Reserved)),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'0b[01]+', Number.Bin),
            (r'0o[0-7]+', Number.Oct),
            (r'[0-9]+[\.e][0-9]+', Number.Float),
            (r'[0-9]+', Number.Integer),
            (words(('let', 'set', 'show'), suffix=r'\b'), Keyword.Declaration),
            # FIXME: make this work
            ## (r'(import|include)( *)(")([^"])(")',
            ##  bygroups(Keyword.Reserved, Text, Punctuation, String.Double, Punctuation)),
            (r'([a-zA-Z_][a-zA-Z0-9_-]*)', Name.Variable),
            (r'[ \t\n]+', Whitespace),
            (r':', Punctuation), # from imports like "import a: b" or "show: text.with(..)"
        ],
        'inline_code': [
            (r';\b', Punctuation, '#pop'),
            (r'\n', Whitespace, '#pop'),
            include('code'),
        ],
    }

    def __init__(self, **options):
        self.start_state = get_choice_opt(
            options, 'start', ['markup', 'code', 'math'], 'markup', True)

        RegexLexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        stack = ['root']
        if self.start_state != 'markup': # markup is equivalent to root
            stack.append(self.start_state)

        yield from RegexLexer.get_tokens_unprocessed(self, text, stack)

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\command\build_scripts.py ===
"""distutils.command.build_scripts

Implements the Distutils 'build_scripts' command."""

import os
import re
import tokenize
from distutils._log import log
from stat import ST_MODE
from typing import ClassVar

from .._modified import newer
from ..core import Command
from ..util import convert_path

shebang_pattern = re.compile('^#!.*python[0-9.]*([ \t].*)?$')
"""
Pattern matching a Python interpreter indicated in first line of a script.
"""

# for Setuptools compatibility
first_line_re = shebang_pattern


class build_scripts(Command):
    description = "\"build\" scripts (copy and fixup #! line)"

    user_options: ClassVar[list[tuple[str, str, str]]] = [
        ('build-dir=', 'd', "directory to \"build\" (copy) to"),
        ('force', 'f', "forcibly build everything (ignore file timestamps"),
        ('executable=', 'e', "specify final destination interpreter path"),
    ]

    boolean_options: ClassVar[list[str]] = ['force']

    def initialize_options(self):
        self.build_dir = None
        self.scripts = None
        self.force = None
        self.executable = None

    def finalize_options(self):
        self.set_undefined_options(
            'build',
            ('build_scripts', 'build_dir'),
            ('force', 'force'),
            ('executable', 'executable'),
        )
        self.scripts = self.distribution.scripts

    def get_source_files(self):
        return self.scripts

    def run(self):
        if not self.scripts:
            return
        self.copy_scripts()

    def copy_scripts(self):
        """
        Copy each script listed in ``self.scripts``.

        If a script is marked as a Python script (first line matches
        'shebang_pattern', i.e. starts with ``#!`` and contains
        "python"), then adjust in the copy the first line to refer to
        the current Python interpreter.
        """
        self.mkpath(self.build_dir)
        outfiles = []
        updated_files = []
        for script in self.scripts:
            self._copy_script(script, outfiles, updated_files)

        self._change_modes(outfiles)

        return outfiles, updated_files

    def _copy_script(self, script, outfiles, updated_files):
        shebang_match = None
        script = convert_path(script)
        outfile = os.path.join(self.build_dir, os.path.basename(script))
        outfiles.append(outfile)

        if not self.force and not newer(script, outfile):
            log.debug("not copying %s (up-to-date)", script)
            return

        # Always open the file, but ignore failures in dry-run mode
        # in order to attempt to copy directly.
        try:
            f = tokenize.open(script)
        except OSError:
            if not self.dry_run:
                raise
            f = None
        else:
            first_line = f.readline()
            if not first_line:
                self.warn(f"{script} is an empty file (skipping)")
                return

            shebang_match = shebang_pattern.match(first_line)

        updated_files.append(outfile)
        if shebang_match:
            log.info("copying and adjusting %s -> %s", script, self.build_dir)
            if not self.dry_run:
                post_interp = shebang_match.group(1) or ''
                shebang = "#!" + self.executable + post_interp + "\n"
                self._validate_shebang(shebang, f.encoding)
                with open(outfile, "w", encoding=f.encoding) as outf:
                    outf.write(shebang)
                    outf.writelines(f.readlines())
            if f:
                f.close()
        else:
            if f:
                f.close()
            self.copy_file(script, outfile)

    def _change_modes(self, outfiles):
        if os.name != 'posix':
            return

        for file in outfiles:
            self._change_mode(file)

    def _change_mode(self, file):
        if self.dry_run:
            log.info("changing mode of %s", file)
            return

        oldmode = os.stat(file)[ST_MODE] & 0o7777
        newmode = (oldmode | 0o555) & 0o7777
        if newmode != oldmode:
            log.info("changing mode of %s from %o to %o", file, oldmode, newmode)
            os.chmod(file, newmode)

    @staticmethod
    def _validate_shebang(shebang, encoding):
        # Python parser starts to read a script using UTF-8 until
        # it gets a #coding:xxx cookie. The shebang has to be the
        # first line of a file, the #coding:xxx cookie cannot be
        # written before. So the shebang has to be encodable to
        # UTF-8.
        try:
            shebang.encode('utf-8')
        except UnicodeEncodeError:
            raise ValueError(f"The shebang ({shebang!r}) is not encodable to utf-8")

        # If the script is encoded to a custom encoding (use a
        # #coding:xxx cookie), the shebang has to be encodable to
        # the script encoding too.
        try:
            shebang.encode(encoding)
        except UnicodeEncodeError:
            raise ValueError(
                f"The shebang ({shebang!r}) is not encodable "
                f"to the script encoding ({encoding})"
            )

# === NexusCore/openenv\Lib\site-packages\win32com\test\testMarshal.py ===
"""Testing pasing object between multiple COM threads

Uses standard COM marshalling to pass objects between threads.  Even
though Python generally seems to work when you just pass COM objects
between threads, it shouldn't.

This shows the "correct" way to do it.

It shows that although we create new threads to use the Python.Interpreter,
COM marshalls back all calls to that object to the main Python thread,
which must be running a message loop (as this sample does).

When this test is run in "free threaded" mode (at this stage, you must
manually mark the COM objects as "ThreadingModel=Free", or run from a
service which has marked itself as free-threaded), then no marshalling
is done, and the Python.Interpreter object start doing the "expected" thing
- ie, it reports being on the same thread as its caller!

Python.exe needs a good way to mark itself as FreeThreaded - at the moment
this is a pain in the but!

"""

import threading
import unittest

import pythoncom
import win32api
import win32com.client
import win32event

from .testServers import InterpCase

freeThreaded = 1


class ThreadInterpCase(InterpCase):
    def _testInterpInThread(self, stopEvent, interp):
        try:
            self._doTestInThread(interp)
        finally:
            win32event.SetEvent(stopEvent)

    def _doTestInThread(self, interp):
        pythoncom.CoInitialize()
        myThread = win32api.GetCurrentThreadId()

        if freeThreaded:
            interp = pythoncom.CoGetInterfaceAndReleaseStream(
                interp, pythoncom.IID_IDispatch
            )
            interp = win32com.client.Dispatch(interp)

        interp.Exec("import win32api")
        # print(f"The test thread id is {myThread}, Python.Interpreter's thread ID is {interp.Eval('win32api.GetCurrentThreadId()')}")
        pythoncom.CoUninitialize()

    def BeginThreadsSimpleMarshal(self, numThreads):
        """Creates multiple threads using simple (but slower) marshalling.

        Single interpreter object, but a new stream is created per thread.

        Returns the handles the threads will set when complete.
        """
        interp = win32com.client.Dispatch("Python.Interpreter")
        events = []
        threads = []
        for i in range(numThreads):
            hEvent = win32event.CreateEvent(None, 0, 0, None)
            events.append(hEvent)
            interpStream = pythoncom.CoMarshalInterThreadInterfaceInStream(
                pythoncom.IID_IDispatch, interp._oleobj_
            )
            t = threading.Thread(
                target=self._testInterpInThread, args=(hEvent, interpStream)
            )
            t.setDaemon(1)  # so errors don't cause shutdown hang
            t.start()
            threads.append(t)
        interp = None
        return threads, events

    #
    # NOTE - this doesn't quite work - I'm not even sure it should, but Greg reckons
    # you should be able to avoid the marshal per thread!
    # I think that refers to CoMarshalInterface though...
    def BeginThreadsFastMarshal(self, numThreads):
        """Creates multiple threads using fast (but complex) marshalling.

        The marshal stream is created once, and each thread uses the same stream

        Returns the handles the threads will set when complete.
        """
        interp = win32com.client.Dispatch("Python.Interpreter")
        if freeThreaded:
            interp = pythoncom.CoMarshalInterThreadInterfaceInStream(
                pythoncom.IID_IDispatch, interp._oleobj_
            )
        events = []
        threads = []
        for i in range(numThreads):
            hEvent = win32event.CreateEvent(None, 0, 0, None)
            t = threading.Thread(target=self._testInterpInThread, args=(hEvent, interp))
            t.setDaemon(1)  # so errors don't cause shutdown hang
            t.start()
            events.append(hEvent)
            threads.append(t)
        return threads, events

    def _DoTestMarshal(self, fn, bCoWait=0):
        # print(f"The main thread is {win32api.GetCurrentThreadId()}")
        threads, events = fn(2)
        numFinished = 0
        while 1:
            try:
                if bCoWait:
                    rc = pythoncom.CoWaitForMultipleHandles(0, 2000, events)
                else:
                    # Specifying "bWaitAll" here will wait for messages *and* all events
                    # (which is pretty useless)
                    rc = win32event.MsgWaitForMultipleObjects(
                        events, 0, 2000, win32event.QS_ALLINPUT
                    )
                if (
                    rc >= win32event.WAIT_OBJECT_0
                    and rc < win32event.WAIT_OBJECT_0 + len(events)
                ):
                    numFinished += 1
                    if numFinished >= len(events):
                        break
                elif rc == win32event.WAIT_OBJECT_0 + len(events):  # a message
                    # This is critical - whole apartment model demo will hang.
                    pythoncom.PumpWaitingMessages()
                else:  # Timeout
                    print(
                        "Waiting for thread to stop with interfaces=%d, gateways=%d"
                        % (pythoncom._GetInterfaceCount(), pythoncom._GetGatewayCount())
                    )
            except KeyboardInterrupt:
                break
        for t in threads:
            t.join(2)
            self.assertFalse(t.is_alive(), "thread failed to stop!?")
        threads = None  # threads hold references to args
        # Seems to be a leak here I can't locate :(
        # self.assertEqual(pythoncom._GetInterfaceCount(), 0)
        # self.assertEqual(pythoncom._GetGatewayCount(), 0)

    def testSimpleMarshal(self):
        self._DoTestMarshal(self.BeginThreadsSimpleMarshal)

    def testSimpleMarshalCoWait(self):
        self._DoTestMarshal(self.BeginThreadsSimpleMarshal, 1)


#    def testFastMarshal(self):
#        self._DoTestMarshal(self.BeginThreadsFastMarshal)

if __name__ == "__main__":
    unittest.main("testMarshal")

# === NexusCore/myenv\Lib\site-packages\pip\_internal\cli\spinners.py ===
import contextlib
import itertools
import logging
import sys
import time
from typing import IO, Generator, Optional

from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.logging import get_indentation

logger = logging.getLogger(__name__)


class SpinnerInterface:
    def spin(self) -> None:
        raise NotImplementedError()

    def finish(self, final_status: str) -> None:
        raise NotImplementedError()


class InteractiveSpinner(SpinnerInterface):
    def __init__(
        self,
        message: str,
        file: Optional[IO[str]] = None,
        spin_chars: str = "-\\|/",
        # Empirically, 8 updates/second looks nice
        min_update_interval_seconds: float = 0.125,
    ):
        self._message = message
        if file is None:
            file = sys.stdout
        self._file = file
        self._rate_limiter = RateLimiter(min_update_interval_seconds)
        self._finished = False

        self._spin_cycle = itertools.cycle(spin_chars)

        self._file.write(" " * get_indentation() + self._message + " ... ")
        self._width = 0

    def _write(self, status: str) -> None:
        assert not self._finished
        # Erase what we wrote before by backspacing to the beginning, writing
        # spaces to overwrite the old text, and then backspacing again
        backup = "\b" * self._width
        self._file.write(backup + " " * self._width + backup)
        # Now we have a blank slate to add our status
        self._file.write(status)
        self._width = len(status)
        self._file.flush()
        self._rate_limiter.reset()

    def spin(self) -> None:
        if self._finished:
            return
        if not self._rate_limiter.ready():
            return
        self._write(next(self._spin_cycle))

    def finish(self, final_status: str) -> None:
        if self._finished:
            return
        self._write(final_status)
        self._file.write("\n")
        self._file.flush()
        self._finished = True


# Used for dumb terminals, non-interactive installs (no tty), etc.
# We still print updates occasionally (once every 60 seconds by default) to
# act as a keep-alive for systems like Travis-CI that take lack-of-output as
# an indication that a task has frozen.
class NonInteractiveSpinner(SpinnerInterface):
    def __init__(self, message: str, min_update_interval_seconds: float = 60.0) -> None:
        self._message = message
        self._finished = False
        self._rate_limiter = RateLimiter(min_update_interval_seconds)
        self._update("started")

    def _update(self, status: str) -> None:
        assert not self._finished
        self._rate_limiter.reset()
        logger.info("%s: %s", self._message, status)

    def spin(self) -> None:
        if self._finished:
            return
        if not self._rate_limiter.ready():
            return
        self._update("still running...")

    def finish(self, final_status: str) -> None:
        if self._finished:
            return
        self._update(f"finished with status '{final_status}'")
        self._finished = True


class RateLimiter:
    def __init__(self, min_update_interval_seconds: float) -> None:
        self._min_update_interval_seconds = min_update_interval_seconds
        self._last_update: float = 0

    def ready(self) -> bool:
        now = time.time()
        delta = now - self._last_update
        return delta >= self._min_update_interval_seconds

    def reset(self) -> None:
        self._last_update = time.time()


@contextlib.contextmanager
def open_spinner(message: str) -> Generator[SpinnerInterface, None, None]:
    # Interactive spinner goes directly to sys.stdout rather than being routed
    # through the logging system, but it acts like it has level INFO,
    # i.e. it's only displayed if we're at level INFO or better.
    # Non-interactive spinner goes through the logging system, so it is always
    # in sync with logging configuration.
    if sys.stdout.isatty() and logger.getEffectiveLevel() <= logging.INFO:
        spinner: SpinnerInterface = InteractiveSpinner(message)
    else:
        spinner = NonInteractiveSpinner(message)
    try:
        with hidden_cursor(sys.stdout):
            yield spinner
    except KeyboardInterrupt:
        spinner.finish("canceled")
        raise
    except Exception:
        spinner.finish("error")
        raise
    else:
        spinner.finish("done")


HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"


@contextlib.contextmanager
def hidden_cursor(file: IO[str]) -> Generator[None, None, None]:
    # The Windows terminal does not support the hide/show cursor ANSI codes,
    # even via colorama. So don't even try.
    if WINDOWS:
        yield
    # We don't want to clutter the output with control characters if we're
    # writing to a file, or if the user is running with --quiet.
    # See https://github.com/pypa/pip/issues/3418
    elif not file.isatty() or logger.getEffectiveLevel() > logging.INFO:
        yield
    else:
        file.write(HIDE_CURSOR)
        try:
            yield
        finally:
            file.write(SHOW_CURSOR)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\_ratio.py ===
import sys
from fractions import Fraction
from math import ceil
from typing import cast, List, Optional, Sequence

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from pip._vendor.typing_extensions import Protocol  # pragma: no cover


class Edge(Protocol):
    """Any object that defines an edge (such as Layout)."""

    size: Optional[int] = None
    ratio: int = 1
    minimum_size: int = 1


def ratio_resolve(total: int, edges: Sequence[Edge]) -> List[int]:
    """Divide total space to satisfy size, ratio, and minimum_size, constraints.

    The returned list of integers should add up to total in most cases, unless it is
    impossible to satisfy all the constraints. For instance, if there are two edges
    with a minimum size of 20 each and `total` is 30 then the returned list will be
    greater than total. In practice, this would mean that a Layout object would
    clip the rows that would overflow the screen height.

    Args:
        total (int): Total number of characters.
        edges (List[Edge]): Edges within total space.

    Returns:
        List[int]: Number of characters for each edge.
    """
    # Size of edge or None for yet to be determined
    sizes = [(edge.size or None) for edge in edges]

    _Fraction = Fraction

    # While any edges haven't been calculated
    while None in sizes:
        # Get flexible edges and index to map these back on to sizes list
        flexible_edges = [
            (index, edge)
            for index, (size, edge) in enumerate(zip(sizes, edges))
            if size is None
        ]
        # Remaining space in total
        remaining = total - sum(size or 0 for size in sizes)
        if remaining <= 0:
            # No room for flexible edges
            return [
                ((edge.minimum_size or 1) if size is None else size)
                for size, edge in zip(sizes, edges)
            ]
        # Calculate number of characters in a ratio portion
        portion = _Fraction(
            remaining, sum((edge.ratio or 1) for _, edge in flexible_edges)
        )

        # If any edges will be less than their minimum, replace size with the minimum
        for index, edge in flexible_edges:
            if portion * edge.ratio <= edge.minimum_size:
                sizes[index] = edge.minimum_size
                # New fixed size will invalidate calculations, so we need to repeat the process
                break
        else:
            # Distribute flexible space and compensate for rounding error
            # Since edge sizes can only be integers we need to add the remainder
            # to the following line
            remainder = _Fraction(0)
            for index, edge in flexible_edges:
                size, remainder = divmod(portion * edge.ratio + remainder, 1)
                sizes[index] = size
            break
    # Sizes now contains integers only
    return cast(List[int], sizes)


def ratio_reduce(
    total: int, ratios: List[int], maximums: List[int], values: List[int]
) -> List[int]:
    """Divide an integer total in to parts based on ratios.

    Args:
        total (int): The total to divide.
        ratios (List[int]): A list of integer ratios.
        maximums (List[int]): List of maximums values for each slot.
        values (List[int]): List of values

    Returns:
        List[int]: A list of integers guaranteed to sum to total.
    """
    ratios = [ratio if _max else 0 for ratio, _max in zip(ratios, maximums)]
    total_ratio = sum(ratios)
    if not total_ratio:
        return values[:]
    total_remaining = total
    result: List[int] = []
    append = result.append
    for ratio, maximum, value in zip(ratios, maximums, values):
        if ratio and total_ratio > 0:
            distributed = min(maximum, round(ratio * total_remaining / total_ratio))
            append(value - distributed)
            total_remaining -= distributed
            total_ratio -= ratio
        else:
            append(value)
    return result


def ratio_distribute(
    total: int, ratios: List[int], minimums: Optional[List[int]] = None
) -> List[int]:
    """Distribute an integer total in to parts based on ratios.

    Args:
        total (int): The total to divide.
        ratios (List[int]): A list of integer ratios.
        minimums (List[int]): List of minimum values for each slot.

    Returns:
        List[int]: A list of integers guaranteed to sum to total.
    """
    if minimums:
        ratios = [ratio if _min else 0 for ratio, _min in zip(ratios, minimums)]
    total_ratio = sum(ratios)
    assert total_ratio > 0, "Sum of ratios must be > 0"

    total_remaining = total
    distributed_total: List[int] = []
    append = distributed_total.append
    if minimums is None:
        _minimums = [0] * len(ratios)
    else:
        _minimums = minimums
    for ratio, minimum in zip(ratios, _minimums):
        if total_ratio > 0:
            distributed = max(minimum, ceil(ratio * total_remaining / total_ratio))
        else:
            distributed = total_remaining
        append(distributed)
        total_ratio -= ratio
        total_remaining -= distributed
    return distributed_total


if __name__ == "__main__":
    from dataclasses import dataclass

    @dataclass
    class E:
        size: Optional[int] = None
        ratio: int = 1
        minimum_size: int = 1

    resolved = ratio_resolve(110, [E(None, 1, 1), E(None, 1, 1), E(None, 1, 1)])
    print(sum(resolved))

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\util\ssl_match_hostname.py ===
"""The match_hostname() function from Python 3.3.3, essential when using SSL."""

# Note: This file is under the PSF license as the code comes from the python
# stdlib.   http://docs.python.org/3/license.html

import re
import sys

# ipaddress has been backported to 2.6+ in pypi.  If it is installed on the
# system, use it to handle IPAddress ServerAltnames (this was added in
# python-3.5) otherwise only do DNS matching.  This allows
# util.ssl_match_hostname to continue to be used in Python 2.7.
try:
    import ipaddress
except ImportError:
    ipaddress = None

__version__ = "3.5.0.1"


class CertificateError(ValueError):
    pass


def _dnsname_match(dn, hostname, max_wildcards=1):
    """Matching according to RFC 6125, section 6.4.3

    http://tools.ietf.org/html/rfc6125#section-6.4.3
    """
    pats = []
    if not dn:
        return False

    # Ported from python3-syntax:
    # leftmost, *remainder = dn.split(r'.')
    parts = dn.split(r".")
    leftmost = parts[0]
    remainder = parts[1:]

    wildcards = leftmost.count("*")
    if wildcards > max_wildcards:
        # Issue #17980: avoid denials of service by refusing more
        # than one wildcard per fragment.  A survey of established
        # policy among SSL implementations showed it to be a
        # reasonable choice.
        raise CertificateError(
            "too many wildcards in certificate DNS name: " + repr(dn)
        )

    # speed up common case w/o wildcards
    if not wildcards:
        return dn.lower() == hostname.lower()

    # RFC 6125, section 6.4.3, subitem 1.
    # The client SHOULD NOT attempt to match a presented identifier in which
    # the wildcard character comprises a label other than the left-most label.
    if leftmost == "*":
        # When '*' is a fragment by itself, it matches a non-empty dotless
        # fragment.
        pats.append("[^.]+")
    elif leftmost.startswith("xn--") or hostname.startswith("xn--"):
        # RFC 6125, section 6.4.3, subitem 3.
        # The client SHOULD NOT attempt to match a presented identifier
        # where the wildcard character is embedded within an A-label or
        # U-label of an internationalized domain name.
        pats.append(re.escape(leftmost))
    else:
        # Otherwise, '*' matches any dotless string, e.g. www*
        pats.append(re.escape(leftmost).replace(r"\*", "[^.]*"))

    # add the remaining fragments, ignore any wildcards
    for frag in remainder:
        pats.append(re.escape(frag))

    pat = re.compile(r"\A" + r"\.".join(pats) + r"\Z", re.IGNORECASE)
    return pat.match(hostname)


def _to_unicode(obj):
    if isinstance(obj, str) and sys.version_info < (3,):
        # ignored flake8 # F821 to support python 2.7 function
        obj = unicode(obj, encoding="ascii", errors="strict")  # noqa: F821
    return obj


def _ipaddress_match(ipname, host_ip):
    """Exact matching of IP addresses.

    RFC 6125 explicitly doesn't define an algorithm for this
    (section 1.7.2 - "Out of Scope").
    """
    # OpenSSL may add a trailing newline to a subjectAltName's IP address
    # Divergence from upstream: ipaddress can't handle byte str
    ip = ipaddress.ip_address(_to_unicode(ipname).rstrip())
    return ip == host_ip


def match_hostname(cert, hostname):
    """Verify that *cert* (in decoded format as returned by
    SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 and RFC 6125
    rules are followed, but IP addresses are not accepted for *hostname*.

    CertificateError is raised on failure. On success, the function
    returns nothing.
    """
    if not cert:
        raise ValueError(
            "empty or no certificate, match_hostname needs a "
            "SSL socket or SSL context with either "
            "CERT_OPTIONAL or CERT_REQUIRED"
        )
    try:
        # Divergence from upstream: ipaddress can't handle byte str
        host_ip = ipaddress.ip_address(_to_unicode(hostname))
    except (UnicodeError, ValueError):
        # ValueError: Not an IP address (common case)
        # UnicodeError: Divergence from upstream: Have to deal with ipaddress not taking
        # byte strings.  addresses should be all ascii, so we consider it not
        # an ipaddress in this case
        host_ip = None
    except AttributeError:
        # Divergence from upstream: Make ipaddress library optional
        if ipaddress is None:
            host_ip = None
        else:  # Defensive
            raise
    dnsnames = []
    san = cert.get("subjectAltName", ())
    for key, value in san:
        if key == "DNS":
            if host_ip is None and _dnsname_match(value, hostname):
                return
            dnsnames.append(value)
        elif key == "IP Address":
            if host_ip is not None and _ipaddress_match(value, host_ip):
                return
            dnsnames.append(value)
    if not dnsnames:
        # The subject is only checked when there is no dNSName entry
        # in subjectAltName
        for sub in cert.get("subject", ()):
            for key, value in sub:
                # XXX according to RFC 2818, the most specific Common Name
                # must be used.
                if key == "commonName":
                    if _dnsname_match(value, hostname):
                        return
                    dnsnames.append(value)
    if len(dnsnames) > 1:
        raise CertificateError(
            "hostname %r "
            "doesn't match either of %s" % (hostname, ", ".join(map(repr, dnsnames)))
        )
    elif len(dnsnames) == 1:
        raise CertificateError("hostname %r doesn't match %r" % (hostname, dnsnames[0]))
    else:
        raise CertificateError(
            "no appropriate commonName or subjectAltName fields were found"
        )

# === NexusCore/openenv\Lib\site-packages\joblib\logger.py ===
"""
Helpers for logging.

This module needs much love to become useful.
"""

# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2008 Gael Varoquaux
# License: BSD Style, 3 clauses.

from __future__ import print_function

import logging
import os
import pprint
import shutil
import sys
import time

from .disk import mkdirp


def _squeeze_time(t):
    """Remove .1s to the time under Windows: this is the time it take to
    stat files. This is needed to make results similar to timings under
    Unix, for tests
    """
    if sys.platform.startswith("win"):
        return max(0, t - 0.1)
    else:
        return t


def format_time(t):
    t = _squeeze_time(t)
    return "%.1fs, %.1fmin" % (t, t / 60.0)


def short_format_time(t):
    t = _squeeze_time(t)
    if t > 60:
        return "%4.1fmin" % (t / 60.0)
    else:
        return " %5.1fs" % (t)


def pformat(obj, indent=0, depth=3):
    if "numpy" in sys.modules:
        import numpy as np

        print_options = np.get_printoptions()
        np.set_printoptions(precision=6, threshold=64, edgeitems=1)
    else:
        print_options = None
    out = pprint.pformat(obj, depth=depth, indent=indent)
    if print_options:
        np.set_printoptions(**print_options)
    return out


###############################################################################
# class `Logger`
###############################################################################
class Logger(object):
    """Base class for logging messages."""

    def __init__(self, depth=3, name=None):
        """
        Parameters
        ----------
        depth: int, optional
            The depth of objects printed.
        name: str, optional
            The namespace to log to. If None, defaults to joblib.
        """
        self.depth = depth
        self._name = name if name else "joblib"

    def warn(self, msg):
        logging.getLogger(self._name).warning("[%s]: %s" % (self, msg))

    def info(self, msg):
        logging.info("[%s]: %s" % (self, msg))

    def debug(self, msg):
        # XXX: This conflicts with the debug flag used in children class
        logging.getLogger(self._name).debug("[%s]: %s" % (self, msg))

    def format(self, obj, indent=0):
        """Return the formatted representation of the object."""
        return pformat(obj, indent=indent, depth=self.depth)


###############################################################################
# class `PrintTime`
###############################################################################
class PrintTime(object):
    """Print and log messages while keeping track of time."""

    def __init__(self, logfile=None, logdir=None):
        if logfile is not None and logdir is not None:
            raise ValueError("Cannot specify both logfile and logdir")
        # XXX: Need argument docstring
        self.last_time = time.time()
        self.start_time = self.last_time
        if logdir is not None:
            logfile = os.path.join(logdir, "joblib.log")
        self.logfile = logfile
        if logfile is not None:
            mkdirp(os.path.dirname(logfile))
            if os.path.exists(logfile):
                # Rotate the logs
                for i in range(1, 9):
                    try:
                        shutil.move(logfile + ".%i" % i, logfile + ".%i" % (i + 1))
                    except:  # noqa: E722
                        "No reason failing here"
                # Use a copy rather than a move, so that a process
                # monitoring this file does not get lost.
                try:
                    shutil.copy(logfile, logfile + ".1")
                except:  # noqa: E722
                    "No reason failing here"
            try:
                with open(logfile, "w") as logfile:
                    logfile.write("\nLogging joblib python script\n")
                    logfile.write("\n---%s---\n" % time.ctime(self.last_time))
            except:  # noqa: E722
                """ Multiprocessing writing to files can create race
                    conditions. Rather fail silently than crash the
                    computation.
                """
                # XXX: We actually need a debug flag to disable this
                # silent failure.

    def __call__(self, msg="", total=False):
        """Print the time elapsed between the last call and the current
        call, with an optional message.
        """
        if not total:
            time_lapse = time.time() - self.last_time
            full_msg = "%s: %s" % (msg, format_time(time_lapse))
        else:
            # FIXME: Too much logic duplicated
            time_lapse = time.time() - self.start_time
            full_msg = "%s: %.2fs, %.1f min" % (msg, time_lapse, time_lapse / 60)
        print(full_msg, file=sys.stderr)
        if self.logfile is not None:
            try:
                with open(self.logfile, "a") as f:
                    print(full_msg, file=f)
            except:  # noqa: E722
                """ Multiprocessing writing to files can create race
                    conditions. Rather fail silently than crash the
                    calculation.
                """
                # XXX: We actually need a debug flag to disable this
                # silent failure.
        self.last_time = time.time()

# === NexusCore/openenv\Lib\site-packages\rich\_ratio.py ===
import sys
from fractions import Fraction
from math import ceil
from typing import cast, List, Optional, Sequence

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol  # pragma: no cover


class Edge(Protocol):
    """Any object that defines an edge (such as Layout)."""

    size: Optional[int] = None
    ratio: int = 1
    minimum_size: int = 1


def ratio_resolve(total: int, edges: Sequence[Edge]) -> List[int]:
    """Divide total space to satisfy size, ratio, and minimum_size, constraints.

    The returned list of integers should add up to total in most cases, unless it is
    impossible to satisfy all the constraints. For instance, if there are two edges
    with a minimum size of 20 each and `total` is 30 then the returned list will be
    greater than total. In practice, this would mean that a Layout object would
    clip the rows that would overflow the screen height.

    Args:
        total (int): Total number of characters.
        edges (List[Edge]): Edges within total space.

    Returns:
        List[int]: Number of characters for each edge.
    """
    # Size of edge or None for yet to be determined
    sizes = [(edge.size or None) for edge in edges]

    _Fraction = Fraction

    # While any edges haven't been calculated
    while None in sizes:
        # Get flexible edges and index to map these back on to sizes list
        flexible_edges = [
            (index, edge)
            for index, (size, edge) in enumerate(zip(sizes, edges))
            if size is None
        ]
        # Remaining space in total
        remaining = total - sum(size or 0 for size in sizes)
        if remaining <= 0:
            # No room for flexible edges
            return [
                ((edge.minimum_size or 1) if size is None else size)
                for size, edge in zip(sizes, edges)
            ]
        # Calculate number of characters in a ratio portion
        portion = _Fraction(
            remaining, sum((edge.ratio or 1) for _, edge in flexible_edges)
        )

        # If any edges will be less than their minimum, replace size with the minimum
        for index, edge in flexible_edges:
            if portion * edge.ratio <= edge.minimum_size:
                sizes[index] = edge.minimum_size
                # New fixed size will invalidate calculations, so we need to repeat the process
                break
        else:
            # Distribute flexible space and compensate for rounding error
            # Since edge sizes can only be integers we need to add the remainder
            # to the following line
            remainder = _Fraction(0)
            for index, edge in flexible_edges:
                size, remainder = divmod(portion * edge.ratio + remainder, 1)
                sizes[index] = size
            break
    # Sizes now contains integers only
    return cast(List[int], sizes)


def ratio_reduce(
    total: int, ratios: List[int], maximums: List[int], values: List[int]
) -> List[int]:
    """Divide an integer total in to parts based on ratios.

    Args:
        total (int): The total to divide.
        ratios (List[int]): A list of integer ratios.
        maximums (List[int]): List of maximums values for each slot.
        values (List[int]): List of values

    Returns:
        List[int]: A list of integers guaranteed to sum to total.
    """
    ratios = [ratio if _max else 0 for ratio, _max in zip(ratios, maximums)]
    total_ratio = sum(ratios)
    if not total_ratio:
        return values[:]
    total_remaining = total
    result: List[int] = []
    append = result.append
    for ratio, maximum, value in zip(ratios, maximums, values):
        if ratio and total_ratio > 0:
            distributed = min(maximum, round(ratio * total_remaining / total_ratio))
            append(value - distributed)
            total_remaining -= distributed
            total_ratio -= ratio
        else:
            append(value)
    return result


def ratio_distribute(
    total: int, ratios: List[int], minimums: Optional[List[int]] = None
) -> List[int]:
    """Distribute an integer total in to parts based on ratios.

    Args:
        total (int): The total to divide.
        ratios (List[int]): A list of integer ratios.
        minimums (List[int]): List of minimum values for each slot.

    Returns:
        List[int]: A list of integers guaranteed to sum to total.
    """
    if minimums:
        ratios = [ratio if _min else 0 for ratio, _min in zip(ratios, minimums)]
    total_ratio = sum(ratios)
    assert total_ratio > 0, "Sum of ratios must be > 0"

    total_remaining = total
    distributed_total: List[int] = []
    append = distributed_total.append
    if minimums is None:
        _minimums = [0] * len(ratios)
    else:
        _minimums = minimums
    for ratio, minimum in zip(ratios, _minimums):
        if total_ratio > 0:
            distributed = max(minimum, ceil(ratio * total_remaining / total_ratio))
        else:
            distributed = total_remaining
        append(distributed)
        total_ratio -= ratio
        total_remaining -= distributed
    return distributed_total


if __name__ == "__main__":
    from dataclasses import dataclass

    @dataclass
    class E:
        size: Optional[int] = None
        ratio: int = 1
        minimum_size: int = 1

    resolved = ratio_resolve(110, [E(None, 1, 1), E(None, 1, 1), E(None, 1, 1)])
    print(sum(resolved))

# === NexusCore/openenv\Lib\site-packages\httpcore\_backends\trio.py ===
from __future__ import annotations

import ssl
import typing

import trio

from .._exceptions import (
    ConnectError,
    ConnectTimeout,
    ExceptionMapping,
    ReadError,
    ReadTimeout,
    WriteError,
    WriteTimeout,
    map_exceptions,
)
from .base import SOCKET_OPTION, AsyncNetworkBackend, AsyncNetworkStream


class TrioStream(AsyncNetworkStream):
    def __init__(self, stream: trio.abc.Stream) -> None:
        self._stream = stream

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        timeout_or_inf = float("inf") if timeout is None else timeout
        exc_map: ExceptionMapping = {
            trio.TooSlowError: ReadTimeout,
            trio.BrokenResourceError: ReadError,
            trio.ClosedResourceError: ReadError,
        }
        with map_exceptions(exc_map):
            with trio.fail_after(timeout_or_inf):
                data: bytes = await self._stream.receive_some(max_bytes=max_bytes)
                return data

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        if not buffer:
            return

        timeout_or_inf = float("inf") if timeout is None else timeout
        exc_map: ExceptionMapping = {
            trio.TooSlowError: WriteTimeout,
            trio.BrokenResourceError: WriteError,
            trio.ClosedResourceError: WriteError,
        }
        with map_exceptions(exc_map):
            with trio.fail_after(timeout_or_inf):
                await self._stream.send_all(data=buffer)

    async def aclose(self) -> None:
        await self._stream.aclose()

    async def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> AsyncNetworkStream:
        timeout_or_inf = float("inf") if timeout is None else timeout
        exc_map: ExceptionMapping = {
            trio.TooSlowError: ConnectTimeout,
            trio.BrokenResourceError: ConnectError,
        }
        ssl_stream = trio.SSLStream(
            self._stream,
            ssl_context=ssl_context,
            server_hostname=server_hostname,
            https_compatible=True,
            server_side=False,
        )
        with map_exceptions(exc_map):
            try:
                with trio.fail_after(timeout_or_inf):
                    await ssl_stream.do_handshake()
            except Exception as exc:  # pragma: nocover
                await self.aclose()
                raise exc
        return TrioStream(ssl_stream)

    def get_extra_info(self, info: str) -> typing.Any:
        if info == "ssl_object" and isinstance(self._stream, trio.SSLStream):
            # Type checkers cannot see `_ssl_object` attribute because trio._ssl.SSLStream uses __getattr__/__setattr__.
            # Tracked at https://github.com/python-trio/trio/issues/542
            return self._stream._ssl_object  # type: ignore[attr-defined]
        if info == "client_addr":
            return self._get_socket_stream().socket.getsockname()
        if info == "server_addr":
            return self._get_socket_stream().socket.getpeername()
        if info == "socket":
            stream = self._stream
            while isinstance(stream, trio.SSLStream):
                stream = stream.transport_stream
            assert isinstance(stream, trio.SocketStream)
            return stream.socket
        if info == "is_readable":
            socket = self.get_extra_info("socket")
            return socket.is_readable()
        return None

    def _get_socket_stream(self) -> trio.SocketStream:
        stream = self._stream
        while isinstance(stream, trio.SSLStream):
            stream = stream.transport_stream
        assert isinstance(stream, trio.SocketStream)
        return stream


class TrioBackend(AsyncNetworkBackend):
    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> AsyncNetworkStream:
        # By default for TCP sockets, trio enables TCP_NODELAY.
        # https://trio.readthedocs.io/en/stable/reference-io.html#trio.SocketStream
        if socket_options is None:
            socket_options = []  # pragma: no cover
        timeout_or_inf = float("inf") if timeout is None else timeout
        exc_map: ExceptionMapping = {
            trio.TooSlowError: ConnectTimeout,
            trio.BrokenResourceError: ConnectError,
            OSError: ConnectError,
        }
        with map_exceptions(exc_map):
            with trio.fail_after(timeout_or_inf):
                stream: trio.abc.Stream = await trio.open_tcp_stream(
                    host=host, port=port, local_address=local_address
                )
                for option in socket_options:
                    stream.setsockopt(*option)  # type: ignore[attr-defined] # pragma: no cover
        return TrioStream(stream)

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> AsyncNetworkStream:  # pragma: nocover
        if socket_options is None:
            socket_options = []
        timeout_or_inf = float("inf") if timeout is None else timeout
        exc_map: ExceptionMapping = {
            trio.TooSlowError: ConnectTimeout,
            trio.BrokenResourceError: ConnectError,
            OSError: ConnectError,
        }
        with map_exceptions(exc_map):
            with trio.fail_after(timeout_or_inf):
                stream: trio.abc.Stream = await trio.open_unix_socket(path)
                for option in socket_options:
                    stream.setsockopt(*option)  # type: ignore[attr-defined] # pragma: no cover
        return TrioStream(stream)

    async def sleep(self, seconds: float) -> None:
        await trio.sleep(seconds)  # pragma: nocover

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\commands\tag.py ===
# coding=utf-8
# Copyright 2024-present, the HuggingFace Inc. team.
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

"""Contains commands to perform tag management with the CLI.

Usage Examples:
    - Create a tag:
        $ huggingface-cli tag user/my-model 1.0 --message "First release"
        $ huggingface-cli tag user/my-model 1.0 -m "First release" --revision develop
        $ huggingface-cli tag user/my-dataset 1.0 -m "First release" --repo-type dataset
        $ huggingface-cli tag user/my-space 1.0
    - List all tags:
        $ huggingface-cli tag -l user/my-model
        $ huggingface-cli tag --list user/my-dataset --repo-type dataset
    - Delete a tag:
        $ huggingface-cli tag -d user/my-model 1.0
        $ huggingface-cli tag --delete user/my-dataset 1.0 --repo-type dataset
        $ huggingface-cli tag -d user/my-space 1.0 -y
"""

from argparse import Namespace, _SubParsersAction

from requests.exceptions import HTTPError

from huggingface_hub.commands import BaseHuggingfaceCLICommand
from huggingface_hub.constants import (
    REPO_TYPES,
)
from huggingface_hub.hf_api import HfApi

from ..errors import HfHubHTTPError, RepositoryNotFoundError, RevisionNotFoundError
from ._cli_utils import ANSI


class TagCommands(BaseHuggingfaceCLICommand):
    @staticmethod
    def register_subcommand(parser: _SubParsersAction):
        tag_parser = parser.add_parser("tag", help="(create, list, delete) tags for a repo in the hub")

        tag_parser.add_argument("repo_id", type=str, help="The ID of the repo to tag (e.g. `username/repo-name`).")
        tag_parser.add_argument("tag", nargs="?", type=str, help="The name of the tag for creation or deletion.")
        tag_parser.add_argument("-m", "--message", type=str, help="The description of the tag to create.")
        tag_parser.add_argument("--revision", type=str, help="The git revision to tag.")
        tag_parser.add_argument(
            "--token", type=str, help="A User Access Token generated from https://huggingface.co/settings/tokens."
        )
        tag_parser.add_argument(
            "--repo-type",
            choices=["model", "dataset", "space"],
            default="model",
            help="Set the type of repository (model, dataset, or space).",
        )
        tag_parser.add_argument("-y", "--yes", action="store_true", help="Answer Yes to prompts automatically.")

        tag_parser.add_argument("-l", "--list", action="store_true", help="List tags for a repository.")
        tag_parser.add_argument("-d", "--delete", action="store_true", help="Delete a tag for a repository.")

        tag_parser.set_defaults(func=lambda args: handle_commands(args))


def handle_commands(args: Namespace):
    if args.list:
        return TagListCommand(args)
    elif args.delete:
        return TagDeleteCommand(args)
    else:
        return TagCreateCommand(args)


class TagCommand:
    def __init__(self, args: Namespace):
        self.args = args
        self.api = HfApi(token=self.args.token)
        self.repo_id = self.args.repo_id
        self.repo_type = self.args.repo_type
        if self.repo_type not in REPO_TYPES:
            print("Invalid repo --repo-type")
            exit(1)


class TagCreateCommand(TagCommand):
    def run(self):
        print(f"You are about to create tag {ANSI.bold(self.args.tag)} on {self.repo_type} {ANSI.bold(self.repo_id)}")

        try:
            self.api.create_tag(
                repo_id=self.repo_id,
                tag=self.args.tag,
                tag_message=self.args.message,
                revision=self.args.revision,
                repo_type=self.repo_type,
            )
        except RepositoryNotFoundError:
            print(f"{self.repo_type.capitalize()} {ANSI.bold(self.repo_id)} not found.")
            exit(1)
        except RevisionNotFoundError:
            print(f"Revision {ANSI.bold(self.args.revision)} not found.")
            exit(1)
        except HfHubHTTPError as e:
            if e.response.status_code == 409:
                print(f"Tag {ANSI.bold(self.args.tag)} already exists on {ANSI.bold(self.repo_id)}")
                exit(1)
            raise e

        print(f"Tag {ANSI.bold(self.args.tag)} created on {ANSI.bold(self.repo_id)}")


class TagListCommand(TagCommand):
    def run(self):
        try:
            refs = self.api.list_repo_refs(
                repo_id=self.repo_id,
                repo_type=self.repo_type,
            )
        except RepositoryNotFoundError:
            print(f"{self.repo_type.capitalize()} {ANSI.bold(self.repo_id)} not found.")
            exit(1)
        except HTTPError as e:
            print(e)
            print(ANSI.red(e.response.text))
            exit(1)
        if len(refs.tags) == 0:
            print("No tags found")
            exit(0)
        print(f"Tags for {self.repo_type} {ANSI.bold(self.repo_id)}:")
        for tag in refs.tags:
            print(tag.name)


class TagDeleteCommand(TagCommand):
    def run(self):
        print(f"You are about to delete tag {ANSI.bold(self.args.tag)} on {self.repo_type} {ANSI.bold(self.repo_id)}")

        if not self.args.yes:
            choice = input("Proceed? [Y/n] ").lower()
            if choice not in ("", "y", "yes"):
                print("Abort")
                exit()
        try:
            self.api.delete_tag(repo_id=self.repo_id, tag=self.args.tag, repo_type=self.repo_type)
        except RepositoryNotFoundError:
            print(f"{self.repo_type.capitalize()} {ANSI.bold(self.repo_id)} not found.")
            exit(1)
        except RevisionNotFoundError:
            print(f"Tag {ANSI.bold(self.args.tag)} not found on {ANSI.bold(self.repo_id)}")
            exit(1)
        print(f"Tag {ANSI.bold(self.args.tag)} deleted on {ANSI.bold(self.repo_id)}")

# === NexusCore/openenv\Lib\site-packages\litellm\caching\s3_cache.py ===
"""
S3 Cache implementation
WARNING: DO NOT USE THIS IN PRODUCTION - This is not ASYNC

Has 4 methods:
    - set_cache
    - get_cache
    - async_set_cache
    - async_get_cache
"""

import ast
import asyncio
import json
from typing import Optional

from litellm._logging import print_verbose, verbose_logger

from .base_cache import BaseCache


class S3Cache(BaseCache):
    def __init__(
        self,
        s3_bucket_name,
        s3_region_name=None,
        s3_api_version=None,
        s3_use_ssl: Optional[bool] = True,
        s3_verify=None,
        s3_endpoint_url=None,
        s3_aws_access_key_id=None,
        s3_aws_secret_access_key=None,
        s3_aws_session_token=None,
        s3_config=None,
        s3_path=None,
        **kwargs,
    ):
        import boto3

        self.bucket_name = s3_bucket_name
        self.key_prefix = s3_path.rstrip("/") + "/" if s3_path else ""
        # Create an S3 client with custom endpoint URL

        self.s3_client = boto3.client(
            "s3",
            region_name=s3_region_name,
            endpoint_url=s3_endpoint_url,
            api_version=s3_api_version,
            use_ssl=s3_use_ssl,
            verify=s3_verify,
            aws_access_key_id=s3_aws_access_key_id,
            aws_secret_access_key=s3_aws_secret_access_key,
            aws_session_token=s3_aws_session_token,
            config=s3_config,
            **kwargs,
        )

    def set_cache(self, key, value, **kwargs):
        try:
            print_verbose(f"LiteLLM SET Cache - S3. Key={key}. Value={value}")
            ttl = kwargs.get("ttl", None)
            # Convert value to JSON before storing in S3
            serialized_value = json.dumps(value)
            key = self.key_prefix + key

            if ttl is not None:
                cache_control = f"immutable, max-age={ttl}, s-maxage={ttl}"
                import datetime

                # Calculate expiration time
                expiration_time = datetime.datetime.now() + ttl

                # Upload the data to S3 with the calculated expiration time
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=serialized_value,
                    Expires=expiration_time,
                    CacheControl=cache_control,
                    ContentType="application/json",
                    ContentLanguage="en",
                    ContentDisposition=f'inline; filename="{key}.json"',
                )
            else:
                cache_control = "immutable, max-age=31536000, s-maxage=31536000"
                # Upload the data to S3 without specifying Expires
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=serialized_value,
                    CacheControl=cache_control,
                    ContentType="application/json",
                    ContentLanguage="en",
                    ContentDisposition=f'inline; filename="{key}.json"',
                )
        except Exception as e:
            # NON blocking - notify users S3 is throwing an exception
            print_verbose(f"S3 Caching: set_cache() - Got exception from S3: {e}")

    async def async_set_cache(self, key, value, **kwargs):
        self.set_cache(key=key, value=value, **kwargs)

    def get_cache(self, key, **kwargs):
        import botocore

        try:
            key = self.key_prefix + key

            print_verbose(f"Get S3 Cache: key: {key}")
            # Download the data from S3
            cached_response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=key
            )

            if cached_response is not None:
                # cached_response is in `b{} convert it to ModelResponse
                cached_response = (
                    cached_response["Body"].read().decode("utf-8")
                )  # Convert bytes to string
                try:
                    cached_response = json.loads(
                        cached_response
                    )  # Convert string to dictionary
                except Exception:
                    cached_response = ast.literal_eval(cached_response)
            if not isinstance(cached_response, dict):
                cached_response = dict(cached_response)
            verbose_logger.debug(
                f"Got S3 Cache: key: {key}, cached_response {cached_response}. Type Response {type(cached_response)}"
            )

            return cached_response
        except botocore.exceptions.ClientError as e:  # type: ignore
            if e.response["Error"]["Code"] == "NoSuchKey":
                verbose_logger.debug(
                    f"S3 Cache: The specified key '{key}' does not exist in the S3 bucket."
                )
                return None

        except Exception as e:
            # NON blocking - notify users S3 is throwing an exception
            verbose_logger.error(
                f"S3 Caching: get_cache() - Got exception from S3: {e}"
            )

    async def async_get_cache(self, key, **kwargs):
        return self.get_cache(key=key, **kwargs)

    def flush_cache(self):
        pass

    async def disconnect(self):
        pass

    async def async_set_cache_pipeline(self, cache_list, **kwargs):
        tasks = []
        for val in cache_list:
            tasks.append(self.async_set_cache(val[0], val[1], **kwargs))
        await asyncio.gather(*tasks)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai_like\chat\transformation.py ===
"""
OpenAI-like chat completion transformation
"""

from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

import httpx

from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllMessageValues, ChatCompletionAssistantMessage
from litellm.types.utils import ModelResponse

from ...openai.chat.gpt_transformation import OpenAIGPTConfig

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class OpenAILikeChatConfig(OpenAIGPTConfig):
    def _get_openai_compatible_provider_info(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        api_base = api_base or get_secret_str("OPENAI_LIKE_API_BASE")  # type: ignore
        dynamic_api_key = (
            api_key or get_secret_str("OPENAI_LIKE_API_KEY") or ""
        )  # vllm does not require an api key
        return api_base, dynamic_api_key

    @staticmethod
    def _json_mode_convert_tool_response_to_message(
        message: ChatCompletionAssistantMessage, json_mode: bool
    ) -> ChatCompletionAssistantMessage:
        """
        if json_mode is true, convert the returned tool call response to a content with json str

        e.g. input:

        {"role": "assistant", "tool_calls": [{"id": "call_5ms4", "type": "function", "function": {"name": "json_tool_call", "arguments": "{\"key\": \"question\", \"value\": \"What is the capital of France?\"}"}}]}

        output:

        {"role": "assistant", "content": "{\"key\": \"question\", \"value\": \"What is the capital of France?\"}"}
        """
        if not json_mode:
            return message

        _tool_calls = message.get("tool_calls")

        if _tool_calls is None or len(_tool_calls) != 1:
            return message

        message["content"] = _tool_calls[0]["function"].get("arguments") or ""
        message["tool_calls"] = None

        return message

    @staticmethod
    def _transform_response(
        model: str,
        response: httpx.Response,
        model_response: ModelResponse,
        stream: bool,
        logging_obj: LiteLLMLoggingObj,
        optional_params: dict,
        api_key: Optional[str],
        data: Union[dict, str],
        messages: List,
        print_verbose,
        encoding,
        json_mode: Optional[bool],
        custom_llm_provider: Optional[str],
        base_model: Optional[str],
    ) -> ModelResponse:
        response_json = response.json()
        logging_obj.post_call(
            input=messages,
            api_key="",
            original_response=response_json,
            additional_args={"complete_input_dict": data},
        )

        if json_mode:
            for choice in response_json["choices"]:
                message = (
                    OpenAILikeChatConfig._json_mode_convert_tool_response_to_message(
                        choice.get("message"), json_mode
                    )
                )
                choice["message"] = message

        returned_response = ModelResponse(**response_json)

        if custom_llm_provider is not None:
            returned_response.model = (
                custom_llm_provider + "/" + (returned_response.model or "")
            )

        if base_model is not None:
            returned_response._hidden_params["model"] = base_model
        return returned_response

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        return OpenAILikeChatConfig._transform_response(
            model=model,
            response=raw_response,
            model_response=model_response,
            stream=optional_params.get("stream", False),
            logging_obj=logging_obj,
            optional_params=optional_params,
            api_key=api_key,
            data=request_data,
            messages=messages,
            print_verbose=None,
            encoding=None,
            json_mode=json_mode,
            custom_llm_provider=None,
            base_model=None,
        )

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
        replace_max_completion_tokens_with_max_tokens: bool = True,
    ) -> dict:
        mapped_params = super().map_openai_params(
            non_default_params, optional_params, model, drop_params
        )
        if (
            "max_completion_tokens" in non_default_params
            and replace_max_completion_tokens_with_max_tokens
        ):
            mapped_params["max_tokens"] = non_default_params[
                "max_completion_tokens"
            ]  # most openai-compatible providers support 'max_tokens' not 'max_completion_tokens'
            mapped_params.pop("max_completion_tokens", None)

        return mapped_params

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\qt_compat.py ===
"""
Qt binding and backend selector.

The selection logic is as follows:
- if any of PyQt6, PySide6, PyQt5, or PySide2 have already been
  imported (checked in that order), use it;
- otherwise, if the QT_API environment variable (used by Enthought) is set, use
  it to determine which binding to use;
- otherwise, use whatever the rcParams indicate.
"""

import operator
import os
import platform
import sys

from packaging.version import parse as parse_version

import matplotlib as mpl

from . import _QT_FORCE_QT5_BINDING

QT_API_PYQT6 = "PyQt6"
QT_API_PYSIDE6 = "PySide6"
QT_API_PYQT5 = "PyQt5"
QT_API_PYSIDE2 = "PySide2"
QT_API_ENV = os.environ.get("QT_API")
if QT_API_ENV is not None:
    QT_API_ENV = QT_API_ENV.lower()
_ETS = {  # Mapping of QT_API_ENV to requested binding.
    "pyqt6": QT_API_PYQT6, "pyside6": QT_API_PYSIDE6,
    "pyqt5": QT_API_PYQT5, "pyside2": QT_API_PYSIDE2,
}
# First, check if anything is already imported.
if sys.modules.get("PyQt6.QtCore"):
    QT_API = QT_API_PYQT6
elif sys.modules.get("PySide6.QtCore"):
    QT_API = QT_API_PYSIDE6
elif sys.modules.get("PyQt5.QtCore"):
    QT_API = QT_API_PYQT5
elif sys.modules.get("PySide2.QtCore"):
    QT_API = QT_API_PYSIDE2
# Otherwise, check the QT_API environment variable (from Enthought).  This can
# only override the binding, not the backend (in other words, we check that the
# requested backend actually matches).  Use _get_backend_or_none to avoid
# triggering backend resolution (which can result in a partially but
# incompletely imported backend_qt5).
elif (mpl.rcParams._get_backend_or_none() or "").lower().startswith("qt5"):
    if QT_API_ENV in ["pyqt5", "pyside2"]:
        QT_API = _ETS[QT_API_ENV]
    else:
        _QT_FORCE_QT5_BINDING = True  # noqa: F811
        QT_API = None
# A non-Qt backend was selected but we still got there (possible, e.g., when
# fully manually embedding Matplotlib in a Qt app without using pyplot).
elif QT_API_ENV is None:
    QT_API = None
elif QT_API_ENV in _ETS:
    QT_API = _ETS[QT_API_ENV]
else:
    raise RuntimeError(
        "The environment variable QT_API has the unrecognized value {!r}; "
        "valid values are {}".format(QT_API_ENV, ", ".join(_ETS)))


def _setup_pyqt5plus():
    global QtCore, QtGui, QtWidgets, __version__
    global _isdeleted, _to_int

    if QT_API == QT_API_PYQT6:
        from PyQt6 import QtCore, QtGui, QtWidgets, sip
        __version__ = QtCore.PYQT_VERSION_STR
        QtCore.Signal = QtCore.pyqtSignal
        QtCore.Slot = QtCore.pyqtSlot
        QtCore.Property = QtCore.pyqtProperty
        _isdeleted = sip.isdeleted
        _to_int = operator.attrgetter('value')
    elif QT_API == QT_API_PYSIDE6:
        from PySide6 import QtCore, QtGui, QtWidgets, __version__
        import shiboken6
        def _isdeleted(obj): return not shiboken6.isValid(obj)
        if parse_version(__version__) >= parse_version('6.4'):
            _to_int = operator.attrgetter('value')
        else:
            _to_int = int
    elif QT_API == QT_API_PYQT5:
        from PyQt5 import QtCore, QtGui, QtWidgets
        import sip
        __version__ = QtCore.PYQT_VERSION_STR
        QtCore.Signal = QtCore.pyqtSignal
        QtCore.Slot = QtCore.pyqtSlot
        QtCore.Property = QtCore.pyqtProperty
        _isdeleted = sip.isdeleted
        _to_int = int
    elif QT_API == QT_API_PYSIDE2:
        from PySide2 import QtCore, QtGui, QtWidgets, __version__
        try:
            from PySide2 import shiboken2
        except ImportError:
            import shiboken2
        def _isdeleted(obj):
            return not shiboken2.isValid(obj)
        _to_int = int
    else:
        raise AssertionError(f"Unexpected QT_API: {QT_API}")


if QT_API in [QT_API_PYQT6, QT_API_PYQT5, QT_API_PYSIDE6, QT_API_PYSIDE2]:
    _setup_pyqt5plus()
elif QT_API is None:  # See above re: dict.__getitem__.
    if _QT_FORCE_QT5_BINDING:
        _candidates = [
            (_setup_pyqt5plus, QT_API_PYQT5),
            (_setup_pyqt5plus, QT_API_PYSIDE2),
        ]
    else:
        _candidates = [
            (_setup_pyqt5plus, QT_API_PYQT6),
            (_setup_pyqt5plus, QT_API_PYSIDE6),
            (_setup_pyqt5plus, QT_API_PYQT5),
            (_setup_pyqt5plus, QT_API_PYSIDE2),
        ]
    for _setup, QT_API in _candidates:
        try:
            _setup()
        except ImportError:
            continue
        break
    else:
        raise ImportError(
            "Failed to import any of the following Qt binding modules: {}"
            .format(", ".join([QT_API for _, QT_API in _candidates]))
        )
else:  # We should not get there.
    raise AssertionError(f"Unexpected QT_API: {QT_API}")
_version_info = tuple(QtCore.QLibraryInfo.version().segments())


if _version_info < (5, 12):
    raise ImportError(
        f"The Qt version imported is "
        f"{QtCore.QLibraryInfo.version().toString()} but Matplotlib requires "
        f"Qt>=5.12")


# Fixes issues with Big Sur
# https://bugreports.qt.io/browse/QTBUG-87014, fixed in qt 5.15.2
if (sys.platform == 'darwin' and
        parse_version(platform.mac_ver()[0]) >= parse_version("10.16") and
        _version_info < (5, 15, 2)):
    os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")


# Backports.


def _exec(obj):
    # exec on PyQt6, exec_ elsewhere.
    obj.exec() if hasattr(obj, "exec") else obj.exec_()

# === NexusCore/openenv\Lib\site-packages\pip\_internal\cli\spinners.py ===
import contextlib
import itertools
import logging
import sys
import time
from typing import IO, Generator, Optional

from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.logging import get_indentation

logger = logging.getLogger(__name__)


class SpinnerInterface:
    def spin(self) -> None:
        raise NotImplementedError()

    def finish(self, final_status: str) -> None:
        raise NotImplementedError()


class InteractiveSpinner(SpinnerInterface):
    def __init__(
        self,
        message: str,
        file: Optional[IO[str]] = None,
        spin_chars: str = "-\\|/",
        # Empirically, 8 updates/second looks nice
        min_update_interval_seconds: float = 0.125,
    ):
        self._message = message
        if file is None:
            file = sys.stdout
        self._file = file
        self._rate_limiter = RateLimiter(min_update_interval_seconds)
        self._finished = False

        self._spin_cycle = itertools.cycle(spin_chars)

        self._file.write(" " * get_indentation() + self._message + " ... ")
        self._width = 0

    def _write(self, status: str) -> None:
        assert not self._finished
        # Erase what we wrote before by backspacing to the beginning, writing
        # spaces to overwrite the old text, and then backspacing again
        backup = "\b" * self._width
        self._file.write(backup + " " * self._width + backup)
        # Now we have a blank slate to add our status
        self._file.write(status)
        self._width = len(status)
        self._file.flush()
        self._rate_limiter.reset()

    def spin(self) -> None:
        if self._finished:
            return
        if not self._rate_limiter.ready():
            return
        self._write(next(self._spin_cycle))

    def finish(self, final_status: str) -> None:
        if self._finished:
            return
        self._write(final_status)
        self._file.write("\n")
        self._file.flush()
        self._finished = True


# Used for dumb terminals, non-interactive installs (no tty), etc.
# We still print updates occasionally (once every 60 seconds by default) to
# act as a keep-alive for systems like Travis-CI that take lack-of-output as
# an indication that a task has frozen.
class NonInteractiveSpinner(SpinnerInterface):
    def __init__(self, message: str, min_update_interval_seconds: float = 60.0) -> None:
        self._message = message
        self._finished = False
        self._rate_limiter = RateLimiter(min_update_interval_seconds)
        self._update("started")

    def _update(self, status: str) -> None:
        assert not self._finished
        self._rate_limiter.reset()
        logger.info("%s: %s", self._message, status)

    def spin(self) -> None:
        if self._finished:
            return
        if not self._rate_limiter.ready():
            return
        self._update("still running...")

    def finish(self, final_status: str) -> None:
        if self._finished:
            return
        self._update(f"finished with status '{final_status}'")
        self._finished = True


class RateLimiter:
    def __init__(self, min_update_interval_seconds: float) -> None:
        self._min_update_interval_seconds = min_update_interval_seconds
        self._last_update: float = 0

    def ready(self) -> bool:
        now = time.time()
        delta = now - self._last_update
        return delta >= self._min_update_interval_seconds

    def reset(self) -> None:
        self._last_update = time.time()


@contextlib.contextmanager
def open_spinner(message: str) -> Generator[SpinnerInterface, None, None]:
    # Interactive spinner goes directly to sys.stdout rather than being routed
    # through the logging system, but it acts like it has level INFO,
    # i.e. it's only displayed if we're at level INFO or better.
    # Non-interactive spinner goes through the logging system, so it is always
    # in sync with logging configuration.
    if sys.stdout.isatty() and logger.getEffectiveLevel() <= logging.INFO:
        spinner: SpinnerInterface = InteractiveSpinner(message)
    else:
        spinner = NonInteractiveSpinner(message)
    try:
        with hidden_cursor(sys.stdout):
            yield spinner
    except KeyboardInterrupt:
        spinner.finish("canceled")
        raise
    except Exception:
        spinner.finish("error")
        raise
    else:
        spinner.finish("done")


HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"


@contextlib.contextmanager
def hidden_cursor(file: IO[str]) -> Generator[None, None, None]:
    # The Windows terminal does not support the hide/show cursor ANSI codes,
    # even via colorama. So don't even try.
    if WINDOWS:
        yield
    # We don't want to clutter the output with control characters if we're
    # writing to a file, or if the user is running with --quiet.
    # See https://github.com/pypa/pip/issues/3418
    elif not file.isatty() or logger.getEffectiveLevel() > logging.INFO:
        yield
    else:
        file.write(HIDE_CURSOR)
        try:
            yield
        finally:
            file.write(SHOW_CURSOR)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\_ratio.py ===
import sys
from fractions import Fraction
from math import ceil
from typing import cast, List, Optional, Sequence

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from pip._vendor.typing_extensions import Protocol  # pragma: no cover


class Edge(Protocol):
    """Any object that defines an edge (such as Layout)."""

    size: Optional[int] = None
    ratio: int = 1
    minimum_size: int = 1


def ratio_resolve(total: int, edges: Sequence[Edge]) -> List[int]:
    """Divide total space to satisfy size, ratio, and minimum_size, constraints.

    The returned list of integers should add up to total in most cases, unless it is
    impossible to satisfy all the constraints. For instance, if there are two edges
    with a minimum size of 20 each and `total` is 30 then the returned list will be
    greater than total. In practice, this would mean that a Layout object would
    clip the rows that would overflow the screen height.

    Args:
        total (int): Total number of characters.
        edges (List[Edge]): Edges within total space.

    Returns:
        List[int]: Number of characters for each edge.
    """
    # Size of edge or None for yet to be determined
    sizes = [(edge.size or None) for edge in edges]

    _Fraction = Fraction

    # While any edges haven't been calculated
    while None in sizes:
        # Get flexible edges and index to map these back on to sizes list
        flexible_edges = [
            (index, edge)
            for index, (size, edge) in enumerate(zip(sizes, edges))
            if size is None
        ]
        # Remaining space in total
        remaining = total - sum(size or 0 for size in sizes)
        if remaining <= 0:
            # No room for flexible edges
            return [
                ((edge.minimum_size or 1) if size is None else size)
                for size, edge in zip(sizes, edges)
            ]
        # Calculate number of characters in a ratio portion
        portion = _Fraction(
            remaining, sum((edge.ratio or 1) for _, edge in flexible_edges)
        )

        # If any edges will be less than their minimum, replace size with the minimum
        for index, edge in flexible_edges:
            if portion * edge.ratio <= edge.minimum_size:
                sizes[index] = edge.minimum_size
                # New fixed size will invalidate calculations, so we need to repeat the process
                break
        else:
            # Distribute flexible space and compensate for rounding error
            # Since edge sizes can only be integers we need to add the remainder
            # to the following line
            remainder = _Fraction(0)
            for index, edge in flexible_edges:
                size, remainder = divmod(portion * edge.ratio + remainder, 1)
                sizes[index] = size
            break
    # Sizes now contains integers only
    return cast(List[int], sizes)


def ratio_reduce(
    total: int, ratios: List[int], maximums: List[int], values: List[int]
) -> List[int]:
    """Divide an integer total in to parts based on ratios.

    Args:
        total (int): The total to divide.
        ratios (List[int]): A list of integer ratios.
        maximums (List[int]): List of maximums values for each slot.
        values (List[int]): List of values

    Returns:
        List[int]: A list of integers guaranteed to sum to total.
    """
    ratios = [ratio if _max else 0 for ratio, _max in zip(ratios, maximums)]
    total_ratio = sum(ratios)
    if not total_ratio:
        return values[:]
    total_remaining = total
    result: List[int] = []
    append = result.append
    for ratio, maximum, value in zip(ratios, maximums, values):
        if ratio and total_ratio > 0:
            distributed = min(maximum, round(ratio * total_remaining / total_ratio))
            append(value - distributed)
            total_remaining -= distributed
            total_ratio -= ratio
        else:
            append(value)
    return result


def ratio_distribute(
    total: int, ratios: List[int], minimums: Optional[List[int]] = None
) -> List[int]:
    """Distribute an integer total in to parts based on ratios.

    Args:
        total (int): The total to divide.
        ratios (List[int]): A list of integer ratios.
        minimums (List[int]): List of minimum values for each slot.

    Returns:
        List[int]: A list of integers guaranteed to sum to total.
    """
    if minimums:
        ratios = [ratio if _min else 0 for ratio, _min in zip(ratios, minimums)]
    total_ratio = sum(ratios)
    assert total_ratio > 0, "Sum of ratios must be > 0"

    total_remaining = total
    distributed_total: List[int] = []
    append = distributed_total.append
    if minimums is None:
        _minimums = [0] * len(ratios)
    else:
        _minimums = minimums
    for ratio, minimum in zip(ratios, _minimums):
        if total_ratio > 0:
            distributed = max(minimum, ceil(ratio * total_remaining / total_ratio))
        else:
            distributed = total_remaining
        append(distributed)
        total_ratio -= ratio
        total_remaining -= distributed
    return distributed_total


if __name__ == "__main__":
    from dataclasses import dataclass

    @dataclass
    class E:
        size: Optional[int] = None
        ratio: int = 1
        minimum_size: int = 1

    resolved = ratio_resolve(110, [E(None, 1, 1), E(None, 1, 1), E(None, 1, 1)])
    print(sum(resolved))

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\util\ssl_match_hostname.py ===
"""The match_hostname() function from Python 3.3.3, essential when using SSL."""

# Note: This file is under the PSF license as the code comes from the python
# stdlib.   http://docs.python.org/3/license.html

import re
import sys

# ipaddress has been backported to 2.6+ in pypi.  If it is installed on the
# system, use it to handle IPAddress ServerAltnames (this was added in
# python-3.5) otherwise only do DNS matching.  This allows
# util.ssl_match_hostname to continue to be used in Python 2.7.
try:
    import ipaddress
except ImportError:
    ipaddress = None

__version__ = "3.5.0.1"


class CertificateError(ValueError):
    pass


def _dnsname_match(dn, hostname, max_wildcards=1):
    """Matching according to RFC 6125, section 6.4.3

    http://tools.ietf.org/html/rfc6125#section-6.4.3
    """
    pats = []
    if not dn:
        return False

    # Ported from python3-syntax:
    # leftmost, *remainder = dn.split(r'.')
    parts = dn.split(r".")
    leftmost = parts[0]
    remainder = parts[1:]

    wildcards = leftmost.count("*")
    if wildcards > max_wildcards:
        # Issue #17980: avoid denials of service by refusing more
        # than one wildcard per fragment.  A survey of established
        # policy among SSL implementations showed it to be a
        # reasonable choice.
        raise CertificateError(
            "too many wildcards in certificate DNS name: " + repr(dn)
        )

    # speed up common case w/o wildcards
    if not wildcards:
        return dn.lower() == hostname.lower()

    # RFC 6125, section 6.4.3, subitem 1.
    # The client SHOULD NOT attempt to match a presented identifier in which
    # the wildcard character comprises a label other than the left-most label.
    if leftmost == "*":
        # When '*' is a fragment by itself, it matches a non-empty dotless
        # fragment.
        pats.append("[^.]+")
    elif leftmost.startswith("xn--") or hostname.startswith("xn--"):
        # RFC 6125, section 6.4.3, subitem 3.
        # The client SHOULD NOT attempt to match a presented identifier
        # where the wildcard character is embedded within an A-label or
        # U-label of an internationalized domain name.
        pats.append(re.escape(leftmost))
    else:
        # Otherwise, '*' matches any dotless string, e.g. www*
        pats.append(re.escape(leftmost).replace(r"\*", "[^.]*"))

    # add the remaining fragments, ignore any wildcards
    for frag in remainder:
        pats.append(re.escape(frag))

    pat = re.compile(r"\A" + r"\.".join(pats) + r"\Z", re.IGNORECASE)
    return pat.match(hostname)


def _to_unicode(obj):
    if isinstance(obj, str) and sys.version_info < (3,):
        # ignored flake8 # F821 to support python 2.7 function
        obj = unicode(obj, encoding="ascii", errors="strict")  # noqa: F821
    return obj


def _ipaddress_match(ipname, host_ip):
    """Exact matching of IP addresses.

    RFC 6125 explicitly doesn't define an algorithm for this
    (section 1.7.2 - "Out of Scope").
    """
    # OpenSSL may add a trailing newline to a subjectAltName's IP address
    # Divergence from upstream: ipaddress can't handle byte str
    ip = ipaddress.ip_address(_to_unicode(ipname).rstrip())
    return ip == host_ip


def match_hostname(cert, hostname):
    """Verify that *cert* (in decoded format as returned by
    SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 and RFC 6125
    rules are followed, but IP addresses are not accepted for *hostname*.

    CertificateError is raised on failure. On success, the function
    returns nothing.
    """
    if not cert:
        raise ValueError(
            "empty or no certificate, match_hostname needs a "
            "SSL socket or SSL context with either "
            "CERT_OPTIONAL or CERT_REQUIRED"
        )
    try:
        # Divergence from upstream: ipaddress can't handle byte str
        host_ip = ipaddress.ip_address(_to_unicode(hostname))
    except (UnicodeError, ValueError):
        # ValueError: Not an IP address (common case)
        # UnicodeError: Divergence from upstream: Have to deal with ipaddress not taking
        # byte strings.  addresses should be all ascii, so we consider it not
        # an ipaddress in this case
        host_ip = None
    except AttributeError:
        # Divergence from upstream: Make ipaddress library optional
        if ipaddress is None:
            host_ip = None
        else:  # Defensive
            raise
    dnsnames = []
    san = cert.get("subjectAltName", ())
    for key, value in san:
        if key == "DNS":
            if host_ip is None and _dnsname_match(value, hostname):
                return
            dnsnames.append(value)
        elif key == "IP Address":
            if host_ip is not None and _ipaddress_match(value, host_ip):
                return
            dnsnames.append(value)
    if not dnsnames:
        # The subject is only checked when there is no dNSName entry
        # in subjectAltName
        for sub in cert.get("subject", ()):
            for key, value in sub:
                # XXX according to RFC 2818, the most specific Common Name
                # must be used.
                if key == "commonName":
                    if _dnsname_match(value, hostname):
                        return
                    dnsnames.append(value)
    if len(dnsnames) > 1:
        raise CertificateError(
            "hostname %r "
            "doesn't match either of %s" % (hostname, ", ".join(map(repr, dnsnames)))
        )
    elif len(dnsnames) == 1:
        raise CertificateError("hostname %r doesn't match %r" % (hostname, dnsnames[0]))
    else:
        raise CertificateError(
            "no appropriate commonName or subjectAltName fields were found"
        )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\bibtex.py ===
"""
    pygments.lexers.bibtex
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for BibTeX bibliography data and styles

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, ExtendedRegexLexer, include, default, \
    words
from pygments.token import Name, Comment, String, Error, Number, Keyword, \
    Punctuation, Whitespace

__all__ = ['BibTeXLexer', 'BSTLexer']


class BibTeXLexer(ExtendedRegexLexer):
    """
    A lexer for BibTeX bibliography data format.
    """

    name = 'BibTeX'
    aliases = ['bibtex', 'bib']
    filenames = ['*.bib']
    mimetypes = ["text/x-bibtex"]
    version_added = '2.2'
    flags = re.IGNORECASE
    url = 'https://texfaq.org/FAQ-BibTeXing'

    ALLOWED_CHARS = r'@!$&*+\-./:;<>?\[\\\]^`|~'
    IDENTIFIER = '[{}][{}]*'.format('a-z_' + ALLOWED_CHARS, r'\w' + ALLOWED_CHARS)

    def open_brace_callback(self, match, ctx):
        opening_brace = match.group()
        ctx.opening_brace = opening_brace
        yield match.start(), Punctuation, opening_brace
        ctx.pos = match.end()

    def close_brace_callback(self, match, ctx):
        closing_brace = match.group()
        if (
            ctx.opening_brace == '{' and closing_brace != '}' or
            ctx.opening_brace == '(' and closing_brace != ')'
        ):
            yield match.start(), Error, closing_brace
        else:
            yield match.start(), Punctuation, closing_brace
        del ctx.opening_brace
        ctx.pos = match.end()

    tokens = {
        'root': [
            include('whitespace'),
            (r'@comment(?!ary)', Comment),
            ('@preamble', Name.Class, ('closing-brace', 'value', 'opening-brace')),
            ('@string', Name.Class, ('closing-brace', 'field', 'opening-brace')),
            ('@' + IDENTIFIER, Name.Class,
             ('closing-brace', 'command-body', 'opening-brace')),
            ('.+', Comment),
        ],
        'opening-brace': [
            include('whitespace'),
            (r'[{(]', open_brace_callback, '#pop'),
        ],
        'closing-brace': [
            include('whitespace'),
            (r'[})]', close_brace_callback, '#pop'),
        ],
        'command-body': [
            include('whitespace'),
            (r'[^\s\,\}]+', Name.Label, ('#pop', 'fields')),
        ],
        'fields': [
            include('whitespace'),
            (',', Punctuation, 'field'),
            default('#pop'),
        ],
        'field': [
            include('whitespace'),
            (IDENTIFIER, Name.Attribute, ('value', '=')),
            default('#pop'),
        ],
        '=': [
            include('whitespace'),
            ('=', Punctuation, '#pop'),
        ],
        'value': [
            include('whitespace'),
            (IDENTIFIER, Name.Variable),
            ('"', String, 'quoted-string'),
            (r'\{', String, 'braced-string'),
            (r'[\d]+', Number),
            ('#', Punctuation),
            default('#pop'),
        ],
        'quoted-string': [
            (r'\{', String, 'braced-string'),
            ('"', String, '#pop'),
            (r'[^\{\"]+', String),
        ],
        'braced-string': [
            (r'\{', String, '#push'),
            (r'\}', String, '#pop'),
            (r'[^\{\}]+', String),
        ],
        'whitespace': [
            (r'\s+', Whitespace),
        ],
    }


class BSTLexer(RegexLexer):
    """
    A lexer for BibTeX bibliography styles.
    """

    name = 'BST'
    aliases = ['bst', 'bst-pybtex']
    filenames = ['*.bst']
    version_added = '2.2'
    flags = re.IGNORECASE | re.MULTILINE
    url = 'https://texfaq.org/FAQ-BibTeXing'

    tokens = {
        'root': [
            include('whitespace'),
            (words(['read', 'sort']), Keyword),
            (words(['execute', 'integers', 'iterate', 'reverse', 'strings']),
             Keyword, ('group')),
            (words(['function', 'macro']), Keyword, ('group', 'group')),
            (words(['entry']), Keyword, ('group', 'group', 'group')),
        ],
        'group': [
            include('whitespace'),
            (r'\{', Punctuation, ('#pop', 'group-end', 'body')),
        ],
        'group-end': [
            include('whitespace'),
            (r'\}', Punctuation, '#pop'),
        ],
        'body': [
            include('whitespace'),
            (r"\'[^#\"\{\}\s]+", Name.Function),
            (r'[^#\"\{\}\s]+\$', Name.Builtin),
            (r'[^#\"\{\}\s]+', Name.Variable),
            (r'"[^\"]*"', String),
            (r'#-?\d+', Number),
            (r'\{', Punctuation, ('group-end', 'body')),
            default('#pop'),
        ],
        'whitespace': [
            (r'\s+', Whitespace),
            ('%.*?$', Comment.Single),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\Demos\ocx\msoffice.py ===
# This demo uses some of the Microsoft Office components.
#
# It was taken from an MSDN article showing how to embed excel.
# It is not comlpete yet, but it _does_ show an Excel spreadsheet in a frame!
#

import win32con
import win32ui
import win32uiole
from pywin.mfc import activex, docview, object, window
from win32com.client import gencache


class OleClientItem(object.CmdTarget):
    def __init__(self, doc):
        object.CmdTarget.__init__(self, win32uiole.CreateOleClientItem(doc))

    def OnGetItemPosition(self):
        # For now return a hard-coded rect.
        return (10, 10, 210, 210)

    def OnActivate(self):
        # Allow only one inplace activate item per frame
        view = self.GetActiveView()
        item = self.GetDocument().GetInPlaceActiveItem(view)
        if item is not None and item._obj_ != self._obj_:
            item.Close()
        self._obj_.OnActivate()

    def OnChange(self, oleNotification, dwParam):
        self._obj_.OnChange(oleNotification, dwParam)
        self.GetDocument().UpdateAllViews(None)

    def OnChangeItemPosition(self, rect):
        # During in-place activation CEmbed_ExcelCntrItem::OnChangeItemPosition
        #  is called by the server to change the position of the in-place
        #  window.  Usually, this is a result of the data in the server
        #  document changing such that the extent has changed or as a result
        #  of in-place resizing.
        #
        # The default here is to call the base class, which will call
        #  COleClientItem::SetItemRects to move the item
        #  to the new position.
        if not self._obj_.OnChangeItemPosition(self, rect):
            return 0

        # TODO: update any cache you may have of the item's rectangle/extent
        return 1


class OleDocument(object.CmdTarget):
    def __init__(self, template):
        object.CmdTarget.__init__(self, win32uiole.CreateOleDocument(template))
        self.EnableCompoundFile()


class ExcelView(docview.ScrollView):
    def OnInitialUpdate(self):
        self.HookMessage(self.OnSetFocus, win32con.WM_SETFOCUS)
        self.HookMessage(self.OnSize, win32con.WM_SIZE)

        self.SetScrollSizes(win32con.MM_TEXT, (100, 100))
        rc = self._obj_.OnInitialUpdate()
        self.EmbedExcel()
        return rc

    def EmbedExcel(self):
        doc = self.GetDocument()
        self.clientItem = OleClientItem(doc)
        self.clientItem.CreateNewItem("Excel.Sheet")
        self.clientItem.DoVerb(-1, self)
        doc.UpdateAllViews(None)

    def OnDraw(self, dc):
        doc = self.GetDocument()
        pos = doc.GetStartPosition()
        clientItem, pos = doc.GetNextItem(pos)
        clientItem.Draw(dc, (10, 10, 210, 210))

    # Special handling of OnSetFocus and OnSize are required for a container
    #  when an object is being edited in-place.
    def OnSetFocus(self, msg):
        item = self.GetDocument().GetInPlaceActiveItem(self)
        if (
            item is not None
            and item.GetItemState() == win32uiole.COleClientItem_activeUIState
        ):
            wnd = item.GetInPlaceWindow()
            if wnd is not None:
                wnd.SetFocus()
            return 0  # Don't get the base version called.
        return 1  # Call the base version.

    def OnSize(self, params):
        item = self.GetDocument().GetInPlaceActiveItem(self)
        if item is not None:
            item.SetItemRects()
        return 1  # do call the base!


class OleTemplate(docview.DocTemplate):
    def __init__(
        self, resourceId=None, MakeDocument=None, MakeFrame=None, MakeView=None
    ):
        if MakeDocument is None:
            MakeDocument = OleDocument
        if MakeView is None:
            MakeView = ExcelView
        docview.DocTemplate.__init__(
            self, resourceId, MakeDocument, MakeFrame, MakeView
        )


class WordFrame(window.MDIChildWnd):
    def __init__(self, doc=None):
        self._obj_ = win32ui.CreateMDIChild()
        self._obj_.AttachObject(self)
        # Don't call base class doc/view version...

    def Create(self, title, rect=None, parent=None):
        WordModule = gencache.EnsureModule(
            "{00020905-0000-0000-C000-000000000046}", 1033, 8, 0
        )
        if WordModule is None:
            raise ImportError(
                "Microsoft Word version 8 does not appear to be installed."
            )

        # WordModule.Word doesn't exist in WordModule, WordModule.Words does, but CreateControl still fails
        class MyWordControl(activex.Control, WordModule.Word): ...

        style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW
        self._obj_.CreateWindow(None, title, style, rect, parent)

        rect = self.GetClientRect()
        rect = (0, 0, rect[2] - rect[0], rect[3] - rect[1])
        self.ocx = MyWordControl()
        self.ocx.CreateControl(
            "Microsoft Word", win32con.WS_VISIBLE | win32con.WS_CHILD, rect, self, 20000
        )


def Demo():
    import sys

    import win32api

    docName = None
    if len(sys.argv) > 1:
        docName = win32api.GetFullPathName(sys.argv[1])
    OleTemplate().OpenDocumentFile(docName)

    # ActiveX not currently working
    # f = WordFrame(docName)
    # f.Create("Microsoft Office")


if __name__ == "__main__":
    Demo()

# === NexusCore/openenv\Lib\site-packages\tornado\test\locale_test.py ===
import datetime
import os
import shutil
import tempfile
import unittest

import tornado.locale
from tornado.escape import utf8, to_unicode
from tornado.util import unicode_type


class TranslationLoaderTest(unittest.TestCase):
    # TODO: less hacky way to get isolated tests
    SAVE_VARS = ["_translations", "_supported_locales", "_use_gettext"]

    def clear_locale_cache(self):
        tornado.locale.Locale._cache = {}

    def setUp(self):
        self.saved = {}  # type: dict
        for var in TranslationLoaderTest.SAVE_VARS:
            self.saved[var] = getattr(tornado.locale, var)
        self.clear_locale_cache()

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(tornado.locale, k, v)
        self.clear_locale_cache()

    def test_csv(self):
        tornado.locale.load_translations(
            os.path.join(os.path.dirname(__file__), "csv_translations")
        )
        locale = tornado.locale.get("fr_FR")
        self.assertTrue(isinstance(locale, tornado.locale.CSVLocale))
        self.assertEqual(locale.translate("school"), "\u00e9cole")

    def test_csv_bom(self):
        with open(
            os.path.join(os.path.dirname(__file__), "csv_translations", "fr_FR.csv"),
            "rb",
        ) as f:
            char_data = to_unicode(f.read())
        # Re-encode our input data (which is utf-8 without BOM) in
        # encodings that use the BOM and ensure that we can still load
        # it. Note that utf-16-le and utf-16-be do not write a BOM,
        # so we only test whichver variant is native to our platform.
        for encoding in ["utf-8-sig", "utf-16"]:
            tmpdir = tempfile.mkdtemp()
            try:
                with open(os.path.join(tmpdir, "fr_FR.csv"), "wb") as f:
                    f.write(char_data.encode(encoding))
                tornado.locale.load_translations(tmpdir)
                locale = tornado.locale.get("fr_FR")
                self.assertIsInstance(locale, tornado.locale.CSVLocale)
                self.assertEqual(locale.translate("school"), "\u00e9cole")
            finally:
                shutil.rmtree(tmpdir)

    def test_gettext(self):
        tornado.locale.load_gettext_translations(
            os.path.join(os.path.dirname(__file__), "gettext_translations"),
            "tornado_test",
        )
        locale = tornado.locale.get("fr_FR")
        self.assertTrue(isinstance(locale, tornado.locale.GettextLocale))
        self.assertEqual(locale.translate("school"), "\u00e9cole")
        self.assertEqual(locale.pgettext("law", "right"), "le droit")
        self.assertEqual(locale.pgettext("good", "right"), "le bien")
        self.assertEqual(locale.pgettext("organization", "club", "clubs", 1), "le club")
        self.assertEqual(
            locale.pgettext("organization", "club", "clubs", 2), "les clubs"
        )
        self.assertEqual(locale.pgettext("stick", "club", "clubs", 1), "le b\xe2ton")
        self.assertEqual(locale.pgettext("stick", "club", "clubs", 2), "les b\xe2tons")


class LocaleDataTest(unittest.TestCase):
    def test_non_ascii_name(self):
        name = tornado.locale.LOCALE_NAMES["es_LA"]["name"]
        self.assertTrue(isinstance(name, unicode_type))
        self.assertEqual(name, "Espa\u00f1ol")
        self.assertEqual(utf8(name), b"Espa\xc3\xb1ol")


class EnglishTest(unittest.TestCase):
    def test_format_date(self):
        locale = tornado.locale.get("en_US")
        date = datetime.datetime(2013, 4, 28, 18, 35)
        self.assertEqual(
            locale.format_date(date, full_format=True), "April 28, 2013 at 6:35 pm"
        )

        aware_dt = datetime.datetime.now(datetime.timezone.utc)
        naive_dt = aware_dt.replace(tzinfo=None)
        for name, now in {"aware": aware_dt, "naive": naive_dt}.items():
            with self.subTest(dt=name):
                self.assertEqual(
                    locale.format_date(
                        now - datetime.timedelta(seconds=2), full_format=False
                    ),
                    "2 seconds ago",
                )
                self.assertEqual(
                    locale.format_date(
                        now - datetime.timedelta(minutes=2), full_format=False
                    ),
                    "2 minutes ago",
                )
                self.assertEqual(
                    locale.format_date(
                        now - datetime.timedelta(hours=2), full_format=False
                    ),
                    "2 hours ago",
                )

                self.assertEqual(
                    locale.format_date(
                        now - datetime.timedelta(days=1),
                        full_format=False,
                        shorter=True,
                    ),
                    "yesterday",
                )

                date = now - datetime.timedelta(days=2)
                self.assertEqual(
                    locale.format_date(date, full_format=False, shorter=True),
                    locale._weekdays[date.weekday()],
                )

                date = now - datetime.timedelta(days=300)
                self.assertEqual(
                    locale.format_date(date, full_format=False, shorter=True),
                    "%s %d" % (locale._months[date.month - 1], date.day),
                )

                date = now - datetime.timedelta(days=500)
                self.assertEqual(
                    locale.format_date(date, full_format=False, shorter=True),
                    "%s %d, %d" % (locale._months[date.month - 1], date.day, date.year),
                )

    def test_friendly_number(self):
        locale = tornado.locale.get("en_US")
        self.assertEqual(locale.friendly_number(1000000), "1,000,000")

    def test_list(self):
        locale = tornado.locale.get("en_US")
        self.assertEqual(locale.list([]), "")
        self.assertEqual(locale.list(["A"]), "A")
        self.assertEqual(locale.list(["A", "B"]), "A and B")
        self.assertEqual(locale.list(["A", "B", "C"]), "A, B and C")

    def test_format_day(self):
        locale = tornado.locale.get("en_US")
        date = datetime.datetime(2013, 4, 28, 18, 35)
        self.assertEqual(locale.format_day(date=date, dow=True), "Sunday, April 28")
        self.assertEqual(locale.format_day(date=date, dow=False), "April 28")

# === NexusCore/openenv\Lib\site-packages\urllib3\util\ssl_match_hostname.py ===
"""The match_hostname() function from Python 3.5, essential when using SSL."""

# Note: This file is under the PSF license as the code comes from the python
# stdlib.   http://docs.python.org/3/license.html
# It is modified to remove commonName support.

from __future__ import annotations

import ipaddress
import re
import typing
from ipaddress import IPv4Address, IPv6Address

if typing.TYPE_CHECKING:
    from .ssl_ import _TYPE_PEER_CERT_RET_DICT

__version__ = "3.5.0.1"


class CertificateError(ValueError):
    pass


def _dnsname_match(
    dn: typing.Any, hostname: str, max_wildcards: int = 1
) -> typing.Match[str] | None | bool:
    """Matching according to RFC 6125, section 6.4.3

    http://tools.ietf.org/html/rfc6125#section-6.4.3
    """
    pats = []
    if not dn:
        return False

    # Ported from python3-syntax:
    # leftmost, *remainder = dn.split(r'.')
    parts = dn.split(r".")
    leftmost = parts[0]
    remainder = parts[1:]

    wildcards = leftmost.count("*")
    if wildcards > max_wildcards:
        # Issue #17980: avoid denials of service by refusing more
        # than one wildcard per fragment.  A survey of established
        # policy among SSL implementations showed it to be a
        # reasonable choice.
        raise CertificateError(
            "too many wildcards in certificate DNS name: " + repr(dn)
        )

    # speed up common case w/o wildcards
    if not wildcards:
        return bool(dn.lower() == hostname.lower())

    # RFC 6125, section 6.4.3, subitem 1.
    # The client SHOULD NOT attempt to match a presented identifier in which
    # the wildcard character comprises a label other than the left-most label.
    if leftmost == "*":
        # When '*' is a fragment by itself, it matches a non-empty dotless
        # fragment.
        pats.append("[^.]+")
    elif leftmost.startswith("xn--") or hostname.startswith("xn--"):
        # RFC 6125, section 6.4.3, subitem 3.
        # The client SHOULD NOT attempt to match a presented identifier
        # where the wildcard character is embedded within an A-label or
        # U-label of an internationalized domain name.
        pats.append(re.escape(leftmost))
    else:
        # Otherwise, '*' matches any dotless string, e.g. www*
        pats.append(re.escape(leftmost).replace(r"\*", "[^.]*"))

    # add the remaining fragments, ignore any wildcards
    for frag in remainder:
        pats.append(re.escape(frag))

    pat = re.compile(r"\A" + r"\.".join(pats) + r"\Z", re.IGNORECASE)
    return pat.match(hostname)


def _ipaddress_match(ipname: str, host_ip: IPv4Address | IPv6Address) -> bool:
    """Exact matching of IP addresses.

    RFC 9110 section 4.3.5: "A reference identity of IP-ID contains the decoded
    bytes of the IP address. An IP version 4 address is 4 octets, and an IP
    version 6 address is 16 octets. [...] A reference identity of type IP-ID
    matches if the address is identical to an iPAddress value of the
    subjectAltName extension of the certificate."
    """
    # OpenSSL may add a trailing newline to a subjectAltName's IP address
    # Divergence from upstream: ipaddress can't handle byte str
    ip = ipaddress.ip_address(ipname.rstrip())
    return bool(ip.packed == host_ip.packed)


def match_hostname(
    cert: _TYPE_PEER_CERT_RET_DICT | None,
    hostname: str,
    hostname_checks_common_name: bool = False,
) -> None:
    """Verify that *cert* (in decoded format as returned by
    SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 and RFC 6125
    rules are followed, but IP addresses are not accepted for *hostname*.

    CertificateError is raised on failure. On success, the function
    returns nothing.
    """
    if not cert:
        raise ValueError(
            "empty or no certificate, match_hostname needs a "
            "SSL socket or SSL context with either "
            "CERT_OPTIONAL or CERT_REQUIRED"
        )
    try:
        # Divergence from upstream: ipaddress can't handle byte str
        #
        # The ipaddress module shipped with Python < 3.9 does not support
        # scoped IPv6 addresses so we unconditionally strip the Zone IDs for
        # now. Once we drop support for Python 3.9 we can remove this branch.
        if "%" in hostname:
            host_ip = ipaddress.ip_address(hostname[: hostname.rfind("%")])
        else:
            host_ip = ipaddress.ip_address(hostname)

    except ValueError:
        # Not an IP address (common case)
        host_ip = None
    dnsnames = []
    san: tuple[tuple[str, str], ...] = cert.get("subjectAltName", ())
    key: str
    value: str
    for key, value in san:
        if key == "DNS":
            if host_ip is None and _dnsname_match(value, hostname):
                return
            dnsnames.append(value)
        elif key == "IP Address":
            if host_ip is not None and _ipaddress_match(value, host_ip):
                return
            dnsnames.append(value)

    # We only check 'commonName' if it's enabled and we're not verifying
    # an IP address. IP addresses aren't valid within 'commonName'.
    if hostname_checks_common_name and host_ip is None and not dnsnames:
        for sub in cert.get("subject", ()):
            for key, value in sub:
                if key == "commonName":
                    if _dnsname_match(value, hostname):
                        return
                    dnsnames.append(value)  # Defensive: for Python < 3.9.3

    if len(dnsnames) > 1:
        raise CertificateError(
            "hostname %r "
            "doesn't match either of %s" % (hostname, ", ".join(map(repr, dnsnames)))
        )
    elif len(dnsnames) == 1:
        raise CertificateError(f"hostname {hostname!r} doesn't match {dnsnames[0]!r}")
    else:
        raise CertificateError("no appropriate subjectAltName fields were found")

# === NexusCore/openenv\Lib\site-packages\win32com\test\testCollections.py ===
# testCollections.py
#
# This code tests both the client and server side of collections
# and enumerators.
#
# Also has the side effect of testing some of the PythonCOM error semantics.
import sys
import unittest

import pythoncom
import win32com.client
import win32com.server.util
import win32com.test.util
import winerror


def MakeEmptyEnum():
    # create the Python enumerator object as a real COM object
    o = win32com.server.util.wrap(win32com.server.util.Collection())
    return win32com.client.Dispatch(o)


def MakeTestEnum():
    # create a sub-collection, just to make sure it works :-)
    sub = win32com.server.util.wrap(
        win32com.server.util.Collection(["Sub1", 2, "Sub3"])
    )
    # create the Python enumerator object as a real COM object
    o = win32com.server.util.wrap(win32com.server.util.Collection([1, "Two", 3, sub]))
    return win32com.client.Dispatch(o)


def TestEnumAgainst(o, check):
    for i in range(len(check)):
        assert (
            o(i) == check[i]
        ), f"Using default method gave the incorrect value - {o(i)!r}/{check[i]!r}"

    for i in range(len(check)):
        assert (
            o.Item(i) == check[i]
        ), f"Using Item method gave the incorrect value - {o(i)!r}/{check[i]!r}"

    # First try looping.
    cmp = []
    for s in o:
        cmp.append(s)

    assert (
        cmp[: len(check)] == check
    ), f"Result after looping isn't correct - {cmp[: len(check)]!r}/{check!r}"

    for i in range(len(check)):
        assert o[i] == check[i], "Using indexing gave the incorrect value"


def TestEnum(quiet=None):
    if quiet is None:
        quiet = not "-v" in sys.argv
    if not quiet:
        print("Simple enum test")
    o = MakeTestEnum()
    check = [1, "Two", 3]
    TestEnumAgainst(o, check)

    if not quiet:
        print("sub-collection test")
    sub = o[3]
    TestEnumAgainst(sub, ["Sub1", 2, "Sub3"])

    # Remove the sublist for this test!
    o.Remove(o.Count() - 1)

    if not quiet:
        print("Remove item test")
    del check[1]
    o.Remove(1)
    TestEnumAgainst(o, check)

    if not quiet:
        print("Add item test")
    o.Add("New Item")
    check.append("New Item")
    TestEnumAgainst(o, check)

    if not quiet:
        print("Insert item test")
    o.Insert(2, -1)
    check.insert(2, -1)
    TestEnumAgainst(o, check)

    ### This does not work!
    # if not quiet: print("Indexed replace item test")
    # o[2] = 'Replaced Item'
    # check[2] = 'Replaced Item'
    # TestEnumAgainst(o, check)

    try:
        o()
        raise AssertionError(
            "default method with no args worked when it shouldn't have!"
        )
    except pythoncom.com_error as exc:
        assert (
            exc.hresult == winerror.DISP_E_BADPARAMCOUNT
        ), f"Expected DISP_E_BADPARAMCOUNT - got {exc}"

    try:
        o.Insert("foo", 2)
        raise AssertionError("Insert worked when it shouldn't have!")
    except pythoncom.com_error as exc:
        assert (
            exc.hresult == winerror.DISP_E_TYPEMISMATCH
        ), f"Expected DISP_E_TYPEMISMATCH - got {exc}"

    # Remove the sublist for this test!
    try:
        o.Remove(o.Count())
        raise AssertionError("Remove worked when it shouldn't have!")
    except pythoncom.com_error as exc:
        assert (
            exc.hresult == winerror.DISP_E_BADINDEX
        ), f"Expected DISP_E_BADINDEX - got {exc}"

    # Test an empty collection
    if not quiet:
        print("Empty collection test")
    o = MakeEmptyEnum()
    for item in o:
        raise AssertionError("Empty list performed an iteration")

    try:
        ob = o[1]
        raise AssertionError("Empty list could be indexed")
    except IndexError:
        pass

    try:
        ob = o[0]
        raise AssertionError("Empty list could be indexed")
    except IndexError:
        pass

    try:
        ob = o(0)
        raise AssertionError("Empty list could be indexed")
    except pythoncom.com_error as exc:
        assert (
            exc.hresult == winerror.DISP_E_BADINDEX
        ), f"Expected DISP_E_BADINDEX - got {exc}"


class TestCase(win32com.test.util.TestCase):
    def testEnum(self):
        TestEnum()


if __name__ == "__main__":
    unittest.main()

# === NexusCore/myenv\Lib\site-packages\pip\_internal\distributions\sdist.py ===
import logging
from typing import TYPE_CHECKING, Iterable, Optional, Set, Tuple

from pip._internal.build_env import BuildEnvironment
from pip._internal.distributions.base import AbstractDistribution
from pip._internal.exceptions import InstallationError
from pip._internal.metadata import BaseDistribution
from pip._internal.utils.subprocess import runner_with_spinner_message

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder

logger = logging.getLogger(__name__)


class SourceDistribution(AbstractDistribution):
    """Represents a source distribution.

    The preparation step for these needs metadata for the packages to be
    generated, either using PEP 517 or using the legacy `setup.py egg_info`.
    """

    @property
    def build_tracker_id(self) -> Optional[str]:
        """Identify this requirement uniquely by its link."""
        assert self.req.link
        return self.req.link.url_without_fragment

    def get_metadata_distribution(self) -> BaseDistribution:
        return self.req.get_dist()

    def prepare_distribution_metadata(
        self,
        finder: "PackageFinder",
        build_isolation: bool,
        check_build_deps: bool,
    ) -> None:
        # Load pyproject.toml, to determine whether PEP 517 is to be used
        self.req.load_pyproject_toml()

        # Set up the build isolation, if this requirement should be isolated
        should_isolate = self.req.use_pep517 and build_isolation
        if should_isolate:
            # Setup an isolated environment and install the build backend static
            # requirements in it.
            self._prepare_build_backend(finder)
            # Check that if the requirement is editable, it either supports PEP 660 or
            # has a setup.py or a setup.cfg. This cannot be done earlier because we need
            # to setup the build backend to verify it supports build_editable, nor can
            # it be done later, because we want to avoid installing build requirements
            # needlessly. Doing it here also works around setuptools generating
            # UNKNOWN.egg-info when running get_requires_for_build_wheel on a directory
            # without setup.py nor setup.cfg.
            self.req.isolated_editable_sanity_check()
            # Install the dynamic build requirements.
            self._install_build_reqs(finder)
        # Check if the current environment provides build dependencies
        should_check_deps = self.req.use_pep517 and check_build_deps
        if should_check_deps:
            pyproject_requires = self.req.pyproject_requires
            assert pyproject_requires is not None
            conflicting, missing = self.req.build_env.check_requirements(
                pyproject_requires
            )
            if conflicting:
                self._raise_conflicts("the backend dependencies", conflicting)
            if missing:
                self._raise_missing_reqs(missing)
        self.req.prepare_metadata()

    def _prepare_build_backend(self, finder: "PackageFinder") -> None:
        # Isolate in a BuildEnvironment and install the build-time
        # requirements.
        pyproject_requires = self.req.pyproject_requires
        assert pyproject_requires is not None

        self.req.build_env = BuildEnvironment()
        self.req.build_env.install_requirements(
            finder, pyproject_requires, "overlay", kind="build dependencies"
        )
        conflicting, missing = self.req.build_env.check_requirements(
            self.req.requirements_to_check
        )
        if conflicting:
            self._raise_conflicts("PEP 517/518 supported requirements", conflicting)
        if missing:
            logger.warning(
                "Missing build requirements in pyproject.toml for %s.",
                self.req,
            )
            logger.warning(
                "The project does not specify a build backend, and "
                "pip cannot fall back to setuptools without %s.",
                " and ".join(map(repr, sorted(missing))),
            )

    def _get_build_requires_wheel(self) -> Iterable[str]:
        with self.req.build_env:
            runner = runner_with_spinner_message("Getting requirements to build wheel")
            backend = self.req.pep517_backend
            assert backend is not None
            with backend.subprocess_runner(runner):
                return backend.get_requires_for_build_wheel()

    def _get_build_requires_editable(self) -> Iterable[str]:
        with self.req.build_env:
            runner = runner_with_spinner_message(
                "Getting requirements to build editable"
            )
            backend = self.req.pep517_backend
            assert backend is not None
            with backend.subprocess_runner(runner):
                return backend.get_requires_for_build_editable()

    def _install_build_reqs(self, finder: "PackageFinder") -> None:
        # Install any extra build dependencies that the backend requests.
        # This must be done in a second pass, as the pyproject.toml
        # dependencies must be installed before we can call the backend.
        if (
            self.req.editable
            and self.req.permit_editable_wheels
            and self.req.supports_pyproject_editable
        ):
            build_reqs = self._get_build_requires_editable()
        else:
            build_reqs = self._get_build_requires_wheel()
        conflicting, missing = self.req.build_env.check_requirements(build_reqs)
        if conflicting:
            self._raise_conflicts("the backend dependencies", conflicting)
        self.req.build_env.install_requirements(
            finder, missing, "normal", kind="backend dependencies"
        )

    def _raise_conflicts(
        self, conflicting_with: str, conflicting_reqs: Set[Tuple[str, str]]
    ) -> None:
        format_string = (
            "Some build dependencies for {requirement} "
            "conflict with {conflicting_with}: {description}."
        )
        error_message = format_string.format(
            requirement=self.req,
            conflicting_with=conflicting_with,
            description=", ".join(
                f"{installed} is incompatible with {wanted}"
                for installed, wanted in sorted(conflicting_reqs)
            ),
        )
        raise InstallationError(error_message)

    def _raise_missing_reqs(self, missing: Set[str]) -> None:
        format_string = (
            "Some build dependencies for {requirement} are missing: {missing}."
        )
        error_message = format_string.format(
            requirement=self.req, missing=", ".join(map(repr, sorted(missing)))
        )
        raise InstallationError(error_message)

# === NexusCore/openenv\Lib\site-packages\jinxed\has_key.py ===
"""
key mapping numeric to cap
"""

from jinxed import _keys


_capability_names = {  # pylint: disable=invalid-name
    _keys.KEY_A1: 'ka1',
    _keys.KEY_A3: 'ka3',
    _keys.KEY_B2: 'kb2',
    _keys.KEY_BACKSPACE: 'kbs',
    _keys.KEY_BEG: 'kbeg',
    _keys.KEY_BTAB: 'kcbt',
    _keys.KEY_C1: 'kc1',
    _keys.KEY_C3: 'kc3',
    _keys.KEY_CANCEL: 'kcan',
    _keys.KEY_CATAB: 'ktbc',
    _keys.KEY_CLEAR: 'kclr',
    _keys.KEY_CLOSE: 'kclo',
    _keys.KEY_COMMAND: 'kcmd',
    _keys.KEY_COPY: 'kcpy',
    _keys.KEY_CREATE: 'kcrt',
    _keys.KEY_CTAB: 'kctab',
    _keys.KEY_DC: 'kdch1',
    _keys.KEY_DL: 'kdl1',
    _keys.KEY_DOWN: 'kcud1',
    _keys.KEY_EIC: 'krmir',
    _keys.KEY_END: 'kend',
    _keys.KEY_ENTER: 'kent',
    _keys.KEY_EOL: 'kel',
    _keys.KEY_EOS: 'ked',
    _keys.KEY_EXIT: 'kext',
    _keys.KEY_F0: 'kf0',
    _keys.KEY_F1: 'kf1',
    _keys.KEY_F10: 'kf10',
    _keys.KEY_F11: 'kf11',
    _keys.KEY_F12: 'kf12',
    _keys.KEY_F13: 'kf13',
    _keys.KEY_F14: 'kf14',
    _keys.KEY_F15: 'kf15',
    _keys.KEY_F16: 'kf16',
    _keys.KEY_F17: 'kf17',
    _keys.KEY_F18: 'kf18',
    _keys.KEY_F19: 'kf19',
    _keys.KEY_F2: 'kf2',
    _keys.KEY_F20: 'kf20',
    _keys.KEY_F21: 'kf21',
    _keys.KEY_F22: 'kf22',
    _keys.KEY_F23: 'kf23',
    _keys.KEY_F24: 'kf24',
    _keys.KEY_F25: 'kf25',
    _keys.KEY_F26: 'kf26',
    _keys.KEY_F27: 'kf27',
    _keys.KEY_F28: 'kf28',
    _keys.KEY_F29: 'kf29',
    _keys.KEY_F3: 'kf3',
    _keys.KEY_F30: 'kf30',
    _keys.KEY_F31: 'kf31',
    _keys.KEY_F32: 'kf32',
    _keys.KEY_F33: 'kf33',
    _keys.KEY_F34: 'kf34',
    _keys.KEY_F35: 'kf35',
    _keys.KEY_F36: 'kf36',
    _keys.KEY_F37: 'kf37',
    _keys.KEY_F38: 'kf38',
    _keys.KEY_F39: 'kf39',
    _keys.KEY_F4: 'kf4',
    _keys.KEY_F40: 'kf40',
    _keys.KEY_F41: 'kf41',
    _keys.KEY_F42: 'kf42',
    _keys.KEY_F43: 'kf43',
    _keys.KEY_F44: 'kf44',
    _keys.KEY_F45: 'kf45',
    _keys.KEY_F46: 'kf46',
    _keys.KEY_F47: 'kf47',
    _keys.KEY_F48: 'kf48',
    _keys.KEY_F49: 'kf49',
    _keys.KEY_F5: 'kf5',
    _keys.KEY_F50: 'kf50',
    _keys.KEY_F51: 'kf51',
    _keys.KEY_F52: 'kf52',
    _keys.KEY_F53: 'kf53',
    _keys.KEY_F54: 'kf54',
    _keys.KEY_F55: 'kf55',
    _keys.KEY_F56: 'kf56',
    _keys.KEY_F57: 'kf57',
    _keys.KEY_F58: 'kf58',
    _keys.KEY_F59: 'kf59',
    _keys.KEY_F6: 'kf6',
    _keys.KEY_F60: 'kf60',
    _keys.KEY_F61: 'kf61',
    _keys.KEY_F62: 'kf62',
    _keys.KEY_F63: 'kf63',
    _keys.KEY_F7: 'kf7',
    _keys.KEY_F8: 'kf8',
    _keys.KEY_F9: 'kf9',
    _keys.KEY_FIND: 'kfnd',
    _keys.KEY_HELP: 'khlp',
    _keys.KEY_HOME: 'khome',
    _keys.KEY_IC: 'kich1',
    _keys.KEY_IL: 'kil1',
    _keys.KEY_LEFT: 'kcub1',
    _keys.KEY_LL: 'kll',
    _keys.KEY_MARK: 'kmrk',
    _keys.KEY_MESSAGE: 'kmsg',
    _keys.KEY_MOVE: 'kmov',
    _keys.KEY_NEXT: 'knxt',
    _keys.KEY_NPAGE: 'knp',
    _keys.KEY_OPEN: 'kopn',
    _keys.KEY_OPTIONS: 'kopt',
    _keys.KEY_PPAGE: 'kpp',
    _keys.KEY_PREVIOUS: 'kprv',
    _keys.KEY_PRINT: 'kprt',
    _keys.KEY_REDO: 'krdo',
    _keys.KEY_REFERENCE: 'kref',
    _keys.KEY_REFRESH: 'krfr',
    _keys.KEY_REPLACE: 'krpl',
    _keys.KEY_RESTART: 'krst',
    _keys.KEY_RESUME: 'kres',
    _keys.KEY_RIGHT: 'kcuf1',
    _keys.KEY_SAVE: 'ksav',
    _keys.KEY_SBEG: 'kBEG',
    _keys.KEY_SCANCEL: 'kCAN',
    _keys.KEY_SCOMMAND: 'kCMD',
    _keys.KEY_SCOPY: 'kCPY',
    _keys.KEY_SCREATE: 'kCRT',
    _keys.KEY_SDC: 'kDC',
    _keys.KEY_SDL: 'kDL',
    _keys.KEY_SELECT: 'kslt',
    _keys.KEY_SEND: 'kEND',
    _keys.KEY_SEOL: 'kEOL',
    _keys.KEY_SEXIT: 'kEXT',
    _keys.KEY_SF: 'kind',
    _keys.KEY_SFIND: 'kFND',
    _keys.KEY_SHELP: 'kHLP',
    _keys.KEY_SHOME: 'kHOM',
    _keys.KEY_SIC: 'kIC',
    _keys.KEY_SLEFT: 'kLFT',
    _keys.KEY_SMESSAGE: 'kMSG',
    _keys.KEY_SMOVE: 'kMOV',
    _keys.KEY_SNEXT: 'kNXT',
    _keys.KEY_SOPTIONS: 'kOPT',
    _keys.KEY_SPREVIOUS: 'kPRV',
    _keys.KEY_SPRINT: 'kPRT',
    _keys.KEY_SR: 'kri',
    _keys.KEY_SREDO: 'kRDO',
    _keys.KEY_SREPLACE: 'kRPL',
    _keys.KEY_SRIGHT: 'kRIT',
    _keys.KEY_SRSUME: 'kRES',
    _keys.KEY_SSAVE: 'kSAV',
    _keys.KEY_SSUSPEND: 'kSPD',
    _keys.KEY_STAB: 'khts',
    _keys.KEY_SUNDO: 'kUND',
    _keys.KEY_SUSPEND: 'kspd',
    _keys.KEY_UNDO: 'kund',
    _keys.KEY_UP: 'kcuu1'
    }

# === NexusCore/openenv\Lib\site-packages\anyio\_core\_tasks.py ===
from __future__ import annotations

import math
from collections.abc import Generator
from contextlib import contextmanager
from types import TracebackType

from ..abc._tasks import TaskGroup, TaskStatus
from ._eventloop import get_async_backend


class _IgnoredTaskStatus(TaskStatus[object]):
    def started(self, value: object = None) -> None:
        pass


TASK_STATUS_IGNORED = _IgnoredTaskStatus()


class CancelScope:
    """
    Wraps a unit of work that can be made separately cancellable.

    :param deadline: The time (clock value) when this scope is cancelled automatically
    :param shield: ``True`` to shield the cancel scope from external cancellation
    """

    def __new__(
        cls, *, deadline: float = math.inf, shield: bool = False
    ) -> CancelScope:
        return get_async_backend().create_cancel_scope(shield=shield, deadline=deadline)

    def cancel(self) -> None:
        """Cancel this scope immediately."""
        raise NotImplementedError

    @property
    def deadline(self) -> float:
        """
        The time (clock value) when this scope is cancelled automatically.

        Will be ``float('inf')`` if no timeout has been set.

        """
        raise NotImplementedError

    @deadline.setter
    def deadline(self, value: float) -> None:
        raise NotImplementedError

    @property
    def cancel_called(self) -> bool:
        """``True`` if :meth:`cancel` has been called."""
        raise NotImplementedError

    @property
    def cancelled_caught(self) -> bool:
        """
        ``True`` if this scope suppressed a cancellation exception it itself raised.

        This is typically used to check if any work was interrupted, or to see if the
        scope was cancelled due to its deadline being reached. The value will, however,
        only be ``True`` if the cancellation was triggered by the scope itself (and not
        an outer scope).

        """
        raise NotImplementedError

    @property
    def shield(self) -> bool:
        """
        ``True`` if this scope is shielded from external cancellation.

        While a scope is shielded, it will not receive cancellations from outside.

        """
        raise NotImplementedError

    @shield.setter
    def shield(self, value: bool) -> None:
        raise NotImplementedError

    def __enter__(self) -> CancelScope:
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        raise NotImplementedError


@contextmanager
def fail_after(
    delay: float | None, shield: bool = False
) -> Generator[CancelScope, None, None]:
    """
    Create a context manager which raises a :class:`TimeoutError` if does not finish in
    time.

    :param delay: maximum allowed time (in seconds) before raising the exception, or
        ``None`` to disable the timeout
    :param shield: ``True`` to shield the cancel scope from external cancellation
    :return: a context manager that yields a cancel scope
    :rtype: :class:`~typing.ContextManager`\\[:class:`~anyio.CancelScope`\\]

    """
    current_time = get_async_backend().current_time
    deadline = (current_time() + delay) if delay is not None else math.inf
    with get_async_backend().create_cancel_scope(
        deadline=deadline, shield=shield
    ) as cancel_scope:
        yield cancel_scope

    if cancel_scope.cancelled_caught and current_time() >= cancel_scope.deadline:
        raise TimeoutError


def move_on_after(delay: float | None, shield: bool = False) -> CancelScope:
    """
    Create a cancel scope with a deadline that expires after the given delay.

    :param delay: maximum allowed time (in seconds) before exiting the context block, or
        ``None`` to disable the timeout
    :param shield: ``True`` to shield the cancel scope from external cancellation
    :return: a cancel scope

    """
    deadline = (
        (get_async_backend().current_time() + delay) if delay is not None else math.inf
    )
    return get_async_backend().create_cancel_scope(deadline=deadline, shield=shield)


def current_effective_deadline() -> float:
    """
    Return the nearest deadline among all the cancel scopes effective for the current
    task.

    :return: a clock value from the event loop's internal clock (or ``float('inf')`` if
        there is no deadline in effect, or ``float('-inf')`` if the current scope has
        been cancelled)
    :rtype: float

    """
    return get_async_backend().current_effective_deadline()


def create_task_group() -> TaskGroup:
    """
    Create a task group.

    :return: a task group

    """
    return get_async_backend().create_task_group()

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\D_S_I_G_.py ===
from fontTools.misc.textTools import bytesjoin, strjoin, tobytes, tostr, safeEval
from fontTools.misc import sstruct
from . import DefaultTable
import base64

DSIG_HeaderFormat = """
	> # big endian
	ulVersion:      L
	usNumSigs:      H
	usFlag:         H
"""
# followed by an array of usNumSigs DSIG_Signature records
DSIG_SignatureFormat = """
	> # big endian
	ulFormat:       L
	ulLength:       L # length includes DSIG_SignatureBlock header
	ulOffset:       L
"""
# followed by an array of usNumSigs DSIG_SignatureBlock records,
# each followed immediately by the pkcs7 bytes
DSIG_SignatureBlockFormat = """
	> # big endian
	usReserved1:    H
	usReserved2:    H
	cbSignature:    l # length of following raw pkcs7 data
"""

#
# NOTE
# the DSIG table format allows for SignatureBlocks residing
# anywhere in the table and possibly in a different order as
# listed in the array after the first table header
#
# this implementation does not keep track of any gaps and/or data
# before or after the actual signature blocks while decompiling,
# and puts them in the same physical order as listed in the header
# on compilation with no padding whatsoever.
#


class table_D_S_I_G_(DefaultTable.DefaultTable):
    """Digital Signature table

    The ``DSIG`` table contains cryptographic signatures for the font.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/dsig
    """

    def decompile(self, data, ttFont):
        dummy, newData = sstruct.unpack2(DSIG_HeaderFormat, data, self)
        assert self.ulVersion == 1, "DSIG ulVersion must be 1"
        assert self.usFlag & ~1 == 0, "DSIG usFlag must be 0x1 or 0x0"
        self.signatureRecords = sigrecs = []
        for n in range(self.usNumSigs):
            sigrec, newData = sstruct.unpack2(
                DSIG_SignatureFormat, newData, SignatureRecord()
            )
            assert sigrec.ulFormat == 1, (
                "DSIG signature record #%d ulFormat must be 1" % n
            )
            sigrecs.append(sigrec)
        for sigrec in sigrecs:
            dummy, newData = sstruct.unpack2(
                DSIG_SignatureBlockFormat, data[sigrec.ulOffset :], sigrec
            )
            assert sigrec.usReserved1 == 0, (
                "DSIG signature record #%d usReserverd1 must be 0" % n
            )
            assert sigrec.usReserved2 == 0, (
                "DSIG signature record #%d usReserverd2 must be 0" % n
            )
            sigrec.pkcs7 = newData[: sigrec.cbSignature]

    def compile(self, ttFont):
        packed = sstruct.pack(DSIG_HeaderFormat, self)
        headers = [packed]
        offset = len(packed) + self.usNumSigs * sstruct.calcsize(DSIG_SignatureFormat)
        data = []
        for sigrec in self.signatureRecords:
            # first pack signature block
            sigrec.cbSignature = len(sigrec.pkcs7)
            packed = sstruct.pack(DSIG_SignatureBlockFormat, sigrec) + sigrec.pkcs7
            data.append(packed)
            # update redundant length field
            sigrec.ulLength = len(packed)
            # update running table offset
            sigrec.ulOffset = offset
            headers.append(sstruct.pack(DSIG_SignatureFormat, sigrec))
            offset += sigrec.ulLength
        if offset % 2:
            # Pad to even bytes
            data.append(b"\0")
        return bytesjoin(headers + data)

    def toXML(self, xmlWriter, ttFont):
        xmlWriter.comment(
            "note that the Digital Signature will be invalid after recompilation!"
        )
        xmlWriter.newline()
        xmlWriter.simpletag(
            "tableHeader",
            version=self.ulVersion,
            numSigs=self.usNumSigs,
            flag="0x%X" % self.usFlag,
        )
        for sigrec in self.signatureRecords:
            xmlWriter.newline()
            sigrec.toXML(xmlWriter, ttFont)
        xmlWriter.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "tableHeader":
            self.signatureRecords = []
            self.ulVersion = safeEval(attrs["version"])
            self.usNumSigs = safeEval(attrs["numSigs"])
            self.usFlag = safeEval(attrs["flag"])
            return
        if name == "SignatureRecord":
            sigrec = SignatureRecord()
            sigrec.fromXML(name, attrs, content, ttFont)
            self.signatureRecords.append(sigrec)


pem_spam = lambda l, spam={
    "-----BEGIN PKCS7-----": True,
    "-----END PKCS7-----": True,
    "": True,
}: not spam.get(l.strip())


def b64encode(b):
    s = base64.b64encode(b)
    # Line-break at 76 chars.
    items = []
    while s:
        items.append(tostr(s[:76]))
        items.append("\n")
        s = s[76:]
    return strjoin(items)


class SignatureRecord(object):
    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.__dict__)

    def toXML(self, writer, ttFont):
        writer.begintag(self.__class__.__name__, format=self.ulFormat)
        writer.newline()
        writer.write_noindent("-----BEGIN PKCS7-----\n")
        writer.write_noindent(b64encode(self.pkcs7))
        writer.write_noindent("-----END PKCS7-----\n")
        writer.endtag(self.__class__.__name__)

    def fromXML(self, name, attrs, content, ttFont):
        self.ulFormat = safeEval(attrs["format"])
        self.usReserved1 = safeEval(attrs.get("reserved1", "0"))
        self.usReserved2 = safeEval(attrs.get("reserved2", "0"))
        self.pkcs7 = base64.b64decode(tobytes(strjoin(filter(pem_spam, content))))

# === NexusCore/openenv\Lib\site-packages\google\generativeai\operations.py ===
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
from __future__ import annotations

import functools
from typing import Iterator

from google.generativeai import protos

from google.generativeai import client as client_lib
from google.generativeai.types import model_types
from google.api_core import operation as operation_lib

import tqdm.auto as tqdm


def list_operations(*, client=None) -> Iterator[CreateTunedModelOperation]:
    """Calls the API to list all operations"""

    if client is None:
        client = client_lib.get_default_operations_client()

    # The client returns an iterator of Operation protos (`Iterator[google.longrunning.operations_pb2.Operation]`)
    # not a gapic Operation object (`google.api_core.operation.Operation`)
    operations = (
        CreateTunedModelOperation.from_proto(op, client)
        for op in client.list_operations(name="", filter_="")
    )

    return operations


def get_operation(name: str, *, client=None) -> CreateTunedModelOperation:
    """Calls the API to get a specific operation"""
    if client is None:
        client = client_lib.get_default_operations_client()

    op = client.get_operation(name=name)
    return CreateTunedModelOperation.from_proto(op, client)


def delete_operation(name: str, *, client=None):
    """Calls the API to delete a specific operation"""

    # Raises:google.api_core.exceptions.MethodNotImplemented: Not implemented.
    if client is None:
        client = client_lib.get_default_operations_client()

    return client.delete_operation(name=name)


class CreateTunedModelOperation(operation_lib.Operation):
    @classmethod
    def from_proto(cls, proto, client):
        """
        result = getattr(proto, 'result', None)
        if result is not None:
            if result.value == b'':
                del proto.result
        """

        return from_gapic(
            cls=CreateTunedModelOperation,
            operation=proto,
            operations_client=client,
            result_type=protos.TunedModel,
            metadata_type=protos.CreateTunedModelMetadata,
        )

    @classmethod
    def from_core_operation(
        cls,
        operation: operation_lib.Operation,
    ):
        polling = getattr(operation, "_polling", None)
        retry = getattr(operation, "_retry", None)
        if polling is not None:
            # google.api_core v 2.11
            kwargs = {"polling": polling}
        elif retry is not None:
            # google.api_core v 2.10
            kwargs = {"retry": retry}
        else:
            kwargs = {}
        return cls(
            operation=operation._operation,
            refresh=operation._refresh,
            cancel=operation._cancel,
            result_type=operation._result_type,
            metadata_type=operation._metadata_type,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return self._operation.name

    def update(self):
        """Refresh the current statuses in metadata/result/error"""
        self._refresh_and_update()

    def wait_bar(self, **kwargs) -> Iterator[protos.CreateTunedModelMetadata]:
        """A tqdm wait bar, yields `Operation` statuses until complete.

        Args:
            **kwargs: passed through to `tqdm.auto.tqdm(..., **kwargs)`

        Yields:
            Operation statuses as `protos.CreateTunedModelMetadata` objects.
        """
        bar = tqdm.tqdm(total=self.metadata.total_steps, initial=0, **kwargs)

        # done() includes a `_refresh_and_update`
        while not self.done():
            metadata = self.metadata
            bar.update(self.metadata.completed_steps - bar.n)
            yield metadata
        metadata = self.metadata
        bar.update(self.metadata.completed_steps - bar.n)
        return self.result()

    def set_result(self, result: protos.TunedModel):
        result = model_types.decode_tuned_model(result)
        super().set_result(result)


def from_gapic(
    cls,
    *,
    operation,
    operations_client,
    result_type,
    metadata_type,
    grpc_metadata=None,
    **kwargs,
):
    """`google.api_core.operation.from_gapic`, patched to allow subclasses."""
    refresh = functools.partial(
        operations_client.get_operation, operation.name, metadata=grpc_metadata
    )
    cancel = functools.partial(
        operations_client.cancel_operation,
        operation.name,
        metadata=grpc_metadata,
    )
    return cls(operation, refresh, cancel, result_type, metadata_type, **kwargs)

# === NexusCore/openenv\Lib\site-packages\IPython\core\events.py ===
"""Infrastructure for registering and firing callbacks on application events.

Unlike :mod:`IPython.core.hooks`, which lets end users set single functions to
be called at specific times, or a collection of alternative methods to try,
callbacks are designed to be used by extension authors. A number of callbacks
can be registered for the same event without needing to be aware of one another.

The functions defined in this module are no-ops indicating the names of available
events and the arguments which will be passed to them.

.. note::

   This API is experimental in IPython 2.0, and may be revised in future versions.
"""


class EventManager:
    """Manage a collection of events and a sequence of callbacks for each.
    
    This is attached to :class:`~IPython.core.interactiveshell.InteractiveShell`
    instances as an ``events`` attribute.
    
    .. note::

       This API is experimental in IPython 2.0, and may be revised in future versions.
    """

    def __init__(self, shell, available_events, print_on_error=True):
        """Initialise the :class:`CallbackManager`.

        Parameters
        ----------
        shell
            The :class:`~IPython.core.interactiveshell.InteractiveShell` instance
        available_events
            An iterable of names for callback events.
        print_on_error:
            A boolean flag to set whether the EventManager will print a warning which a event errors.
        """
        self.shell = shell
        self.callbacks = {n:[] for n in available_events}
        self.print_on_error = print_on_error
    
    def register(self, event, function):
        """Register a new event callback.

        Parameters
        ----------
        event : str
            The event for which to register this callback.
        function : callable
            A function to be called on the given event. It should take the same
            parameters as the appropriate callback prototype.

        Raises
        ------
        TypeError
            If ``function`` is not callable.
        KeyError
            If ``event`` is not one of the known events.
        """
        if not callable(function):
            raise TypeError('Need a callable, got %r' % function)
        if function not in self.callbacks[event]:
            self.callbacks[event].append(function)
    
    def unregister(self, event, function):
        """Remove a callback from the given event."""
        if function in self.callbacks[event]:
            return self.callbacks[event].remove(function)

        raise ValueError('Function {!r} is not registered as a {} callback'.format(function, event))

    def trigger(self, event, *args, **kwargs):
        """Call callbacks for ``event``.

        Any additional arguments are passed to all callbacks registered for this
        event. Exceptions raised by callbacks are caught, and a message printed.
        """
        for func in self.callbacks[event][:]:
            try:
                func(*args, **kwargs)
            except (Exception, KeyboardInterrupt):
                if self.print_on_error:
                    print(
                        "Error in callback {} (for {}), with arguments args {},kwargs {}:".format(
                            func, event, args, kwargs
                        )
                    )
                self.shell.showtraceback()

# event_name -> prototype mapping
available_events = {}

def _define_event(callback_function):
    available_events[callback_function.__name__] = callback_function
    return callback_function

# ------------------------------------------------------------------------------
# Callback prototypes
#
# No-op functions which describe the names of available events and the
# signatures of callbacks for those events.
# ------------------------------------------------------------------------------

@_define_event
def pre_execute():
    """Fires before code is executed in response to user/frontend action.

    This includes comm and widget messages and silent execution, as well as user
    code cells.
    """
    pass

@_define_event
def pre_run_cell(info):
    """Fires before user-entered code runs.

    Parameters
    ----------
    info : :class:`~IPython.core.interactiveshell.ExecutionInfo`
        An object containing information used for the code execution.
    """
    pass

@_define_event
def post_execute():
    """Fires after code is executed in response to user/frontend action.

    This includes comm and widget messages and silent execution, as well as user
    code cells.
    """
    pass

@_define_event
def post_run_cell(result):
    """Fires after user-entered code runs.

    Parameters
    ----------
    result : :class:`~IPython.core.interactiveshell.ExecutionResult`
        The object which will be returned as the execution result.
    """
    pass

@_define_event
def shell_initialized(ip):
    """Fires after initialisation of :class:`~IPython.core.interactiveshell.InteractiveShell`.

    This is before extensions and startup scripts are loaded, so it can only be
    set by subclassing.

    Parameters
    ----------
    ip : :class:`~IPython.core.interactiveshell.InteractiveShell`
        The newly initialised shell.
    """
    pass

# === NexusCore/openenv\Lib\site-packages\IPython\core\historyapp.py ===
# encoding: utf-8
"""
An application for managing IPython history.

To be invoked as the `ipython history` subcommand.
"""

import sqlite3
from pathlib import Path

from traitlets.config.application import Application
from .application import BaseIPythonApplication
from traitlets import Bool, Int, Dict
from ..utils.io import ask_yes_no

trim_hist_help = """Trim the IPython history database to the last 1000 entries.

This actually copies the last 1000 entries to a new database, and then replaces
the old file with the new. Use the `--keep=` argument to specify a number
other than 1000.
"""

clear_hist_help = """Clear the IPython history database, deleting all entries.

Because this is a destructive operation, IPython will prompt the user if they
really want to do this. Passing a `-f` flag will force clearing without a
prompt.

This is an handy alias to `ipython history trim --keep=0`
"""


class HistoryTrim(BaseIPythonApplication):
    description = trim_hist_help

    backup = Bool(False, help="Keep the old history file as history.sqlite.<N>").tag(
        config=True
    )

    keep = Int(1000, help="Number of recent lines to keep in the database.").tag(
        config=True
    )

    flags = Dict(  # type: ignore
        dict(backup=({"HistoryTrim": {"backup": True}}, backup.help))
    )

    aliases = Dict(dict(keep="HistoryTrim.keep"))  # type: ignore

    def start(self):
        profile_dir = Path(self.profile_dir.location)
        hist_file = profile_dir / "history.sqlite"
        con = sqlite3.connect(hist_file)

        # Grab the recent history from the current database.
        inputs = list(con.execute('SELECT session, line, source, source_raw FROM '
                                'history ORDER BY session DESC, line DESC LIMIT ?', (self.keep+1,)))
        if len(inputs) <= self.keep:
            print("There are already at most %d entries in the history database." % self.keep)
            print("Not doing anything. Use --keep= argument to keep fewer entries")
            return

        print("Trimming history to the most recent %d entries." % self.keep)

        inputs.pop() # Remove the extra element we got to check the length.
        inputs.reverse()
        if inputs:
            first_session = inputs[0][0]
            outputs = list(con.execute('SELECT session, line, output FROM '
                                       'output_history WHERE session >= ?', (first_session,)))
            sessions = list(con.execute('SELECT session, start, end, num_cmds, remark FROM '
                                        'sessions WHERE session >= ?', (first_session,)))
        con.close()

        # Create the new history database.
        new_hist_file = profile_dir / "history.sqlite.new"
        i = 0
        while new_hist_file.exists():
            # Make sure we don't interfere with an existing file.
            i += 1
            new_hist_file = profile_dir / ("history.sqlite.new" + str(i))
        new_db = sqlite3.connect(new_hist_file)
        new_db.execute("""CREATE TABLE IF NOT EXISTS sessions (session integer
                            primary key autoincrement, start timestamp,
                            end timestamp, num_cmds integer, remark text)""")
        new_db.execute("""CREATE TABLE IF NOT EXISTS history
                        (session integer, line integer, source text, source_raw text,
                        PRIMARY KEY (session, line))""")
        new_db.execute("""CREATE TABLE IF NOT EXISTS output_history
                        (session integer, line integer, output text,
                        PRIMARY KEY (session, line))""")
        new_db.commit()


        if inputs:
            with new_db:
                # Add the recent history into the new database.
                new_db.executemany('insert into sessions values (?,?,?,?,?)', sessions)
                new_db.executemany('insert into history values (?,?,?,?)', inputs)
                new_db.executemany('insert into output_history values (?,?,?)', outputs)
        new_db.close()

        if self.backup:
            i = 1
            backup_hist_file = profile_dir / ("history.sqlite.old.%d" % i)
            while backup_hist_file.exists():
                i += 1
                backup_hist_file = profile_dir / ("history.sqlite.old.%d" % i)
            hist_file.rename(backup_hist_file)
            print("Backed up longer history file to", backup_hist_file)
        else:
            hist_file.unlink()

        new_hist_file.rename(hist_file)


class HistoryClear(HistoryTrim):
    description = clear_hist_help
    keep = Int(0, help="Number of recent lines to keep in the database.")

    force = Bool(False, help="Don't prompt user for confirmation").tag(config=True)

    flags = Dict(  # type: ignore
        dict(
            force=({"HistoryClear": {"force": True}}, force.help),
            f=({"HistoryTrim": {"force": True}}, force.help),
        )
    )
    aliases = Dict()  # type: ignore

    def start(self):
        if self.force or ask_yes_no(
            "Really delete all ipython history? ", default="no", interrupt="no"
        ):
            HistoryTrim.start(self)


class HistoryApp(Application):
    name = "ipython-history"
    description = "Manage the IPython history database."

    subcommands = Dict(dict(
        trim = (HistoryTrim, HistoryTrim.description.splitlines()[0]),
        clear = (HistoryClear, HistoryClear.description.splitlines()[0]),
    ))

    def start(self):
        if self.subapp is None:
            print(
                "No subcommand specified. Must specify one of: "
                + ", ".join(map(repr, self.subcommands))
                + ".\n"
            )
            self.print_description()
            self.print_subcommands()
            self.exit(1)
        else:
            return self.subapp.start()

# === NexusCore/openenv\Lib\site-packages\IPython\core\hooks.py ===
"""Hooks for IPython.

In Python, it is possible to overwrite any method of any object if you really
want to.  But IPython exposes a few 'hooks', methods which are *designed* to
be overwritten by users for customization purposes.  This module defines the
default versions of all such hooks, which get used by IPython if not
overridden by the user.

Hooks are simple functions, but they should be declared with ``self`` as their
first argument, because when activated they are registered into IPython as
instance methods. The self argument will be the IPython running instance
itself, so hooks have full access to the entire IPython object.

If you wish to define a new hook and activate it, you can make an :doc:`extension
</config/extensions/index>` or a :ref:`startup script <startup_files>`. For
example, you could use a startup file like this::

    import os

    def calljed(self,filename, linenum):
        "My editor hook calls the jed editor directly."
        print("Calling my own editor, jed ...")
        if os.system('jed +%d %s' % (linenum,filename)) != 0:
            raise TryNext()

    def load_ipython_extension(ip):
        ip.set_hook('editor', calljed)

"""

#*****************************************************************************
#       Copyright (C) 2005 Fernando Perez. <fperez@colorado.edu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

import os
import subprocess
import sys

from .error import TryNext

# List here all the default hooks.  For now it's just the editor functions
# but over time we'll move here all the public API for user-accessible things.

__all__ = [
    "editor",
    "synchronize_with_editor",
    "show_in_pager",
    "clipboard_get",
]

def editor(self, filename, linenum=None, wait=True):
    """Open the default editor at the given filename and linenumber.

    This is IPython's default editor hook, you can use it as an example to
    write your own modified one.  To set your own editor function as the
    new editor hook, call ip.set_hook('editor',yourfunc)."""

    # IPython configures a default editor at startup by reading $EDITOR from
    # the environment, and falling back on vi (unix) or notepad (win32).
    editor = self.editor

    # marker for at which line to open the file (for existing objects)
    if linenum is None or editor=='notepad':
        linemark = ''
    else:
        linemark = '+%d' % int(linenum)

    # Enclose in quotes if necessary and legal
    if ' ' in editor and os.path.isfile(editor) and editor[0] != '"':
        editor = '"%s"' % editor

    # Call the actual editor
    proc = subprocess.Popen('%s %s %s' % (editor, linemark, filename),
                            shell=True)
    if wait and proc.wait() != 0:
        raise TryNext()


def synchronize_with_editor(self, filename, linenum, column):
        pass


class CommandChainDispatcher:
    """ Dispatch calls to a chain of commands until some func can handle it

    Usage: instantiate, execute "add" to add commands (with optional
    priority), execute normally via f() calling mechanism.

    """
    def __init__(self,commands=None):
        if commands is None:
            self.chain = []
        else:
            self.chain = commands


    def __call__(self,*args, **kw):
        """ Command chain is called just like normal func.

        This will call all funcs in chain with the same args as were given to
        this function, and return the result of first func that didn't raise
        TryNext"""
        last_exc = TryNext()
        for prio,cmd in self.chain:
            # print("prio",prio,"cmd",cmd)  # dbg
            try:
                return cmd(*args, **kw)
            except TryNext as exc:
                last_exc = exc
        # if no function will accept it, raise TryNext up to the caller
        raise last_exc

    def __str__(self):
        return str(self.chain)

    def add(self, func, priority=0):
        """ Add a func to the cmd chain with given priority """
        self.chain.append((priority, func))
        self.chain.sort(key=lambda x: x[0])

    def __iter__(self):
        """ Return all objects in chain.

        Handy if the objects are not callable.
        """
        return iter(self.chain)


def show_in_pager(self, data, start, screen_lines):
    """ Run a string through pager """
    # raising TryNext here will use the default paging functionality
    raise TryNext



def clipboard_get(self):
    """ Get text from the clipboard.
    """
    from ..lib.clipboard import (
        osx_clipboard_get,
        tkinter_clipboard_get,
        win32_clipboard_get,
        wayland_clipboard_get,
    )
    if sys.platform == 'win32':
        chain = [win32_clipboard_get, tkinter_clipboard_get]
    elif sys.platform == 'darwin':
        chain = [osx_clipboard_get, tkinter_clipboard_get]
    else:
        chain = [wayland_clipboard_get, tkinter_clipboard_get]
    dispatcher = CommandChainDispatcher()
    for func in chain:
        dispatcher.add(func)
    text = dispatcher()
    return text

# === NexusCore/openenv\Lib\site-packages\jinxed\terminfo\ansicon.py ===
"""
Ansicon virtual terminal codes

Information sourced from:
    https://github.com/adoxa/ansicon/blob/master/sequences.txt

A best effort has been made, but not all information was available
"""

from .xterm_256color import BOOL_CAPS, NUM_CAPS, STR_CAPS

BOOL_CAPS = BOOL_CAPS[:]
NUM_CAPS = NUM_CAPS.copy()
STR_CAPS = STR_CAPS.copy()


# Added
STR_CAPS['cht'] = b'\x1b[%p1%dI'
STR_CAPS['cnl'] = b'\x1b[%p1%dE'
STR_CAPS['cpl'] = b'\x1b[%p1%dF'
STR_CAPS['da1'] = b'\x1b[0c'
STR_CAPS['dsr'] = b'\x1b[5n'
STR_CAPS['hvp'] = b'\x1b[%i%p1%d;%p2%df'  # Same as cup
STR_CAPS['setb'] = b'\x1b[48;5;%p1%dm'
STR_CAPS['setf'] = b'\x1b[38;5;%p1%dm'

# Removed - These do not appear to be supported
del STR_CAPS['dim']
del STR_CAPS['flash']
del STR_CAPS['invis']
del STR_CAPS['kcbt']
del STR_CAPS['kEND']
del STR_CAPS['kf37']
del STR_CAPS['kf38']
del STR_CAPS['kf39']
del STR_CAPS['kf40']
del STR_CAPS['kf41']
del STR_CAPS['kf42']
del STR_CAPS['kf43']
del STR_CAPS['kf44']
del STR_CAPS['kf45']
del STR_CAPS['kf46']
del STR_CAPS['kf47']
del STR_CAPS['kf48']
del STR_CAPS['kf61']
del STR_CAPS['kf62']
del STR_CAPS['kf63']
del STR_CAPS['kIC']
del STR_CAPS['kind']
del STR_CAPS['kLFT']
del STR_CAPS['kmous']
del STR_CAPS['kNXT']
del STR_CAPS['kPRV']
del STR_CAPS['kri']
del STR_CAPS['kRIT']
del STR_CAPS['meml']
del STR_CAPS['memu']
del STR_CAPS['ritm']
del STR_CAPS['rmam']
del STR_CAPS['rmcup']
del STR_CAPS['rmir']
del STR_CAPS['rmkx']
del STR_CAPS['rmm']
del STR_CAPS['sitm']
del STR_CAPS['smam']
del STR_CAPS['smcup']
del STR_CAPS['smir']
del STR_CAPS['smkx']
del STR_CAPS['smm']

# Modified
NUM_CAPS['colors'] = 16
NUM_CAPS['cols'] = 80
NUM_CAPS['lines'] = 30
NUM_CAPS['pairs'] = 256
STR_CAPS['cbt'] = b'\x1b[%p1%dZ'
STR_CAPS['cnorm'] = b'\x1b[?25h'
STR_CAPS['csr'] = b'\x1b[%p1%{1}%+%d;%?%p2%t%p2%{1}%+%dr'
STR_CAPS['cub1'] = b'\x1b[D'
STR_CAPS['cud1'] = b'\x1b[B'
STR_CAPS['cvvis'] = b'\x1b[?25h'
STR_CAPS['initc'] = b'\x1b]4;%p1%d;rgb] =%p2%d/%p3%d/%p4%d\x1b'
STR_CAPS['is2'] = b'\x1b[!p\x1b>'
STR_CAPS['ka1'] = b'\x00G'   # upper left of keypad
STR_CAPS['ka3'] = b'\x00I'   # lower right of keypad
STR_CAPS['kbs'] = b'\x08'
STR_CAPS['kc1'] = b'\x00O'   # lower left of keypad
STR_CAPS['kc3'] = b'\x00Q'   # lower right of keypad
STR_CAPS['kcub1'] = b'\xe0K'
STR_CAPS['kcud1'] = b'\xe0P'
STR_CAPS['kcuf1'] = b'\xe0M'
STR_CAPS['kcuu1'] = b'\xe0H'
STR_CAPS['kDC'] = b'\xe0S'
STR_CAPS['kdch1'] = b'\x0eQ'
STR_CAPS['kend'] = b'\xe0O'
STR_CAPS['kent'] = b'\r'
STR_CAPS['kf1'] = b'\x00;'
STR_CAPS['kf2'] = b'\x00<'
STR_CAPS['kf3'] = b'\x00='
STR_CAPS['kf4'] = b'\x00>'
STR_CAPS['kf5'] = b'\x00?'
STR_CAPS['kf6'] = b'\x00@'
STR_CAPS['kf7'] = b'\x00A'
STR_CAPS['kf8'] = b'\x00B'
STR_CAPS['kf9'] = b'\x00C'
STR_CAPS['kf10'] = b'\x00D'
STR_CAPS['kf11'] = b'\xe0\x85'
STR_CAPS['kf12'] = b'\xe0\x86'
STR_CAPS['kf13'] = b'\x00T'
STR_CAPS['kf14'] = b'\x00U'
STR_CAPS['kf15'] = b'\x00V'
STR_CAPS['kf16'] = b'\x00W'
STR_CAPS['kf17'] = b'\x00X'
STR_CAPS['kf18'] = b'\x00Y'
STR_CAPS['kf19'] = b'\x00Z'
STR_CAPS['kf20'] = b'\x00['
STR_CAPS['kf21'] = b'\x00\\'
STR_CAPS['kf22'] = b'\x00]'
STR_CAPS['kf23'] = b'\xe0\x87'
STR_CAPS['kf24'] = b'\xe0\x88'
STR_CAPS['kf25'] = b'\x00^'
STR_CAPS['kf26'] = b'\x00_'
STR_CAPS['kf27'] = b'\x00`'
STR_CAPS['kf28'] = b'\x00a'
STR_CAPS['kf29'] = b'\x00b'
STR_CAPS['kf30'] = b'\x00c'
STR_CAPS['kf31'] = b'\x00d'
STR_CAPS['kf32'] = b'\x00e'
STR_CAPS['kf33'] = b'\x00f'
STR_CAPS['kf34'] = b'\x00g'
STR_CAPS['kf35'] = b'\xe0\x89'
STR_CAPS['kf36'] = b'\xe0\x8a'
# Missing F37 - F48
STR_CAPS['kf49'] = b'\x00h'
STR_CAPS['kf50'] = b'\x00i'
STR_CAPS['kf51'] = b'\x00j'
STR_CAPS['kf52'] = b'\x00k'
STR_CAPS['kf53'] = b'\x00l'
STR_CAPS['kf54'] = b'\x00m'
STR_CAPS['kf55'] = b'\x00n'
STR_CAPS['kf56'] = b'\x00o'
STR_CAPS['kf57'] = b'\x00p'
STR_CAPS['kf58'] = b'\x00q'
STR_CAPS['kf59'] = b'\xe0\x8b'
STR_CAPS['kf60'] = b'\xe0\x8b'
# Missing F61 - F63
STR_CAPS['khome'] = b'\xe0G'
STR_CAPS['kich1'] = b'\xe0R'
STR_CAPS['knp'] = b'\xe0Q'
STR_CAPS['kpp'] = b'\xe0I'
STR_CAPS['rs1'] = b'\x1bc\x1b]104ST'
STR_CAPS['rs2'] = b'\x1b[!p'
STR_CAPS['sgr'] = b'\x1b[%p1%d%?%p2%t;%p2%d%;%?%p3%t;%p3%d%;%?%p4%t;%p4%d%;%?%p5%t;%p5%d%;' \
                  b'%?%p6%t;%p6%d%;%?%p7%t;%p7%d%;%?%p8%t;%p8%d%;%?%p9%t;%p9%d%;m'

# Need info - Left in, but unsure
# acsc (covers some, but maybe not all)
# mc0/mc4/mc5 (print screen/off/on)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\base_llm\files\transformation.py ===
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import httpx

from litellm.proxy._types import UserAPIKeyAuth
from litellm.types.llms.openai import (
    AllMessageValues,
    CreateFileRequest,
    OpenAICreateFileRequestOptionalParams,
    OpenAIFileObject,
    OpenAIFilesPurpose,
)
from litellm.types.utils import LlmProviders, ModelResponse

from ..chat.transformation import BaseConfig

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj
    from litellm.router import Router as _Router

    LiteLLMLoggingObj = _LiteLLMLoggingObj
    Span = Any
    Router = _Router
else:
    LiteLLMLoggingObj = Any
    Span = Any
    Router = Any


class BaseFilesConfig(BaseConfig):
    @property
    @abstractmethod
    def custom_llm_provider(self) -> LlmProviders:
        pass

    @abstractmethod
    def get_supported_openai_params(
        self, model: str
    ) -> List[OpenAICreateFileRequestOptionalParams]:
        pass

    def get_complete_file_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        data: CreateFileRequest,
    ):
        return self.get_complete_url(
            api_base=api_base,
            api_key=api_key,
            model=model,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

    @abstractmethod
    def transform_create_file_request(
        self,
        model: str,
        create_file_data: CreateFileRequest,
        optional_params: dict,
        litellm_params: dict,
    ) -> Union[dict, str, bytes]:
        pass

    @abstractmethod
    def transform_create_file_response(
        self,
        model: Optional[str],
        raw_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
        litellm_params: dict,
    ) -> OpenAIFileObject:
        pass

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        raise NotImplementedError(
            "AudioTranscriptionConfig does not need a request transformation for audio transcription models"
        )

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        raise NotImplementedError(
            "AudioTranscriptionConfig does not need a response transformation for audio transcription models"
        )


class BaseFileEndpoints(ABC):
    @abstractmethod
    async def acreate_file(
        self,
        create_file_request: CreateFileRequest,
        llm_router: Router,
        target_model_names_list: List[str],
        litellm_parent_otel_span: Span,
        user_api_key_dict: UserAPIKeyAuth,
    ) -> OpenAIFileObject:
        pass

    @abstractmethod
    async def afile_retrieve(
        self,
        file_id: str,
        litellm_parent_otel_span: Optional[Span],
    ) -> OpenAIFileObject:
        pass

    @abstractmethod
    async def afile_list(
        self,
        purpose: Optional[OpenAIFilesPurpose],
        litellm_parent_otel_span: Optional[Span],
        **data: Dict,
    ) -> List[OpenAIFileObject]:
        pass

    @abstractmethod
    async def afile_delete(
        self,
        file_id: str,
        litellm_parent_otel_span: Optional[Span],
        llm_router: Router,
        **data: Dict,
    ) -> OpenAIFileObject:
        pass

    @abstractmethod
    async def afile_content(
        self,
        file_id: str,
        litellm_parent_otel_span: Optional[Span],
        llm_router: Router,
        **data: Dict,
    ) -> str:
        pass

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai\completion\transformation.py ===
"""
Support for gpt model family 
"""

from typing import List, Optional, Union

from litellm.llms.base_llm.completion.transformation import BaseTextCompletionConfig
from litellm.types.llms.openai import AllMessageValues, OpenAITextCompletionUserMessage
from litellm.types.utils import Choices, Message, ModelResponse, TextCompletionResponse

from ..chat.gpt_transformation import OpenAIGPTConfig
from .utils import _transform_prompt


class OpenAITextCompletionConfig(BaseTextCompletionConfig, OpenAIGPTConfig):
    """
    Reference: https://platform.openai.com/docs/api-reference/completions/create

    The class `OpenAITextCompletionConfig` provides configuration for the OpenAI's text completion API interface. Below are the parameters:

    - `best_of` (integer or null): This optional parameter generates server-side completions and returns the one with the highest log probability per token.

    - `echo` (boolean or null): This optional parameter will echo back the prompt in addition to the completion.

    - `frequency_penalty` (number or null): Defaults to 0. It is a numbers from -2.0 to 2.0, where positive values decrease the model's likelihood to repeat the same line.

    - `logit_bias` (map): This optional parameter modifies the likelihood of specified tokens appearing in the completion.

    - `logprobs` (integer or null): This optional parameter includes the log probabilities on the most likely tokens as well as the chosen tokens.

    - `max_tokens` (integer or null): This optional parameter sets the maximum number of tokens to generate in the completion.

    - `n` (integer or null): This optional parameter sets how many completions to generate for each prompt.

    - `presence_penalty` (number or null): Defaults to 0 and can be between -2.0 and 2.0. Positive values increase the model's likelihood to talk about new topics.

    - `stop` (string / array / null): Specifies up to 4 sequences where the API will stop generating further tokens.

    - `suffix` (string or null): Defines the suffix that comes after a completion of inserted text.

    - `temperature` (number or null): This optional parameter defines the sampling temperature to use.

    - `top_p` (number or null): An alternative to sampling with temperature, used for nucleus sampling.
    """

    best_of: Optional[int] = None
    echo: Optional[bool] = None
    frequency_penalty: Optional[int] = None
    logit_bias: Optional[dict] = None
    logprobs: Optional[int] = None
    max_tokens: Optional[int] = None
    n: Optional[int] = None
    presence_penalty: Optional[int] = None
    stop: Optional[Union[str, list]] = None
    suffix: Optional[str] = None

    def __init__(
        self,
        best_of: Optional[int] = None,
        echo: Optional[bool] = None,
        frequency_penalty: Optional[int] = None,
        logit_bias: Optional[dict] = None,
        logprobs: Optional[int] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[int] = None,
        stop: Optional[Union[str, list]] = None,
        suffix: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def convert_to_chat_model_response_object(
        self,
        response_object: Optional[TextCompletionResponse] = None,
        model_response_object: Optional[ModelResponse] = None,
    ):
        try:
            ## RESPONSE OBJECT
            if response_object is None or model_response_object is None:
                raise ValueError("Error in response object format")
            choice_list = []
            for idx, choice in enumerate(response_object["choices"]):
                message = Message(
                    content=choice["text"],
                    role="assistant",
                )
                choice = Choices(
                    finish_reason=choice["finish_reason"],
                    index=idx,
                    message=message,
                    logprobs=choice.get("logprobs", None),
                )
                choice_list.append(choice)
            model_response_object.choices = choice_list

            if "usage" in response_object:
                setattr(model_response_object, "usage", response_object["usage"])

            if "id" in response_object:
                model_response_object.id = response_object["id"]

            if "model" in response_object:
                model_response_object.model = response_object["model"]

            model_response_object._hidden_params[
                "original_response"
            ] = response_object  # track original response, if users make a litellm.text_completion() request, we can return the original response
            return model_response_object
        except Exception as e:
            raise e

    def get_supported_openai_params(self, model: str) -> List:
        return [
            "functions",
            "function_call",
            "temperature",
            "top_p",
            "n",
            "stream",
            "stream_options",
            "stop",
            "max_tokens",
            "presence_penalty",
            "frequency_penalty",
            "logit_bias",
            "user",
            "response_format",
            "seed",
            "tools",
            "tool_choice",
            "max_retries",
            "logprobs",
            "top_logprobs",
            "extra_headers",
        ]

    def transform_text_completion_request(
        self,
        model: str,
        messages: Union[List[AllMessageValues], List[OpenAITextCompletionUserMessage]],
        optional_params: dict,
        headers: dict,
    ) -> dict:
        prompt = _transform_prompt(messages)
        return {
            "model": model,
            "prompt": prompt,
            **optional_params,
        }

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\client\cli\commands\keys.py ===
import json
from typing import Literal, Optional

import click
import rich
import requests
from rich.table import Table

from ...keys import KeysManagementClient


@click.group()
def keys():
    """Manage API keys for the LiteLLM proxy server"""
    pass


@keys.command()
@click.option("--page", type=int, help="Page number for pagination")
@click.option("--size", type=int, help="Number of items per page")
@click.option("--user-id", type=str, help="Filter keys by user ID")
@click.option("--team-id", type=str, help="Filter keys by team ID")
@click.option("--organization-id", type=str, help="Filter keys by organization ID")
@click.option("--key-hash", type=str, help="Filter by specific key hash")
@click.option("--key-alias", type=str, help="Filter by key alias")
@click.option("--return-full-object", is_flag=True, default=True, help="Return the full key object")
@click.option("--include-team-keys", is_flag=True, help="Include team keys in the response")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format (table or json)",
)
@click.pass_context
def list(
    ctx: click.Context,
    page: Optional[int],
    size: Optional[int],
    user_id: Optional[str],
    team_id: Optional[str],
    organization_id: Optional[str],
    key_hash: Optional[str],
    key_alias: Optional[str],
    include_team_keys: bool,
    output_format: Literal["table", "json"],
    return_full_object: bool,
):
    """List all API keys"""
    client = KeysManagementClient(ctx.obj["base_url"], ctx.obj["api_key"])
    response = client.list(
        page=page,
        size=size,
        user_id=user_id,
        team_id=team_id,
        organization_id=organization_id,
        key_hash=key_hash,
        key_alias=key_alias,
        return_full_object=return_full_object,
        include_team_keys=include_team_keys,
    )
    assert isinstance(response, dict)

    if output_format == "json":
        rich.print_json(data=response)
    else:
        rich.print(f"Showing {len(response.get('keys', []))} keys out of {response.get('total_count', 0)}")
        table = Table(title="API Keys")
        table.add_column("Key Hash", style="cyan")
        table.add_column("Alias", style="green")
        table.add_column("User ID", style="magenta")
        table.add_column("Team ID", style="yellow")
        table.add_column("Spend", style="red")
        for key in response.get("keys", []):
            table.add_row(
                str(key.get("token", "")),
                str(key.get("key_alias", "")),
                str(key.get("user_id", "")),
                str(key.get("team_id", "")),
                str(key.get("spend", "")),
            )
        rich.print(table)


@keys.command()
@click.option("--models", type=str, help="Comma-separated list of allowed models")
@click.option("--aliases", type=str, help="JSON string of model alias mappings")
@click.option("--spend", type=float, help="Maximum spend limit for this key")
@click.option("--duration", type=str, help="Duration for which the key is valid (e.g. '24h', '7d')")
@click.option("--key-alias", type=str, help="Alias/name for the key")
@click.option("--team-id", type=str, help="Team ID to associate the key with")
@click.option("--user-id", type=str, help="User ID to associate the key with")
@click.option("--budget-id", type=str, help="Budget ID to associate the key with")
@click.option("--config", type=str, help="JSON string of additional configuration parameters")
@click.pass_context
def generate(
    ctx: click.Context,
    models: Optional[str],
    aliases: Optional[str],
    spend: Optional[float],
    duration: Optional[str],
    key_alias: Optional[str],
    team_id: Optional[str],
    user_id: Optional[str],
    budget_id: Optional[str],
    config: Optional[str],
):
    """Generate a new API key"""
    client = KeysManagementClient(ctx.obj["base_url"], ctx.obj["api_key"])
    try:
        models_list = [m.strip() for m in models.split(",")] if models else None
        aliases_dict = json.loads(aliases) if aliases else None
        config_dict = json.loads(config) if config else None
    except json.JSONDecodeError as e:
        raise click.BadParameter(f"Invalid JSON: {str(e)}")
    try:
        response = client.generate(
            models=models_list,
            aliases=aliases_dict,
            spend=spend,
            duration=duration,
            key_alias=key_alias,
            team_id=team_id,
            user_id=user_id,
            budget_id=budget_id,
            config=config_dict,
        )
        rich.print_json(data=response)
    except requests.exceptions.HTTPError as e:
        click.echo(f"Error: HTTP {e.response.status_code}", err=True)
        try:
            error_body = e.response.json()
            rich.print_json(data=error_body)
        except json.JSONDecodeError:
            click.echo(e.response.text, err=True)
        raise click.Abort()


@keys.command()
@click.option("--keys", type=str, help="Comma-separated list of API keys to delete")
@click.option("--key-aliases", type=str, help="Comma-separated list of key aliases to delete")
@click.pass_context
def delete(ctx: click.Context, keys: Optional[str], key_aliases: Optional[str]):
    """Delete API keys by key or alias"""
    client = KeysManagementClient(ctx.obj["base_url"], ctx.obj["api_key"])
    keys_list = [k.strip() for k in keys.split(",")] if keys else None
    aliases_list = [a.strip() for a in key_aliases.split(",")] if key_aliases else None
    try:
        response = client.delete(keys=keys_list, key_aliases=aliases_list)
        rich.print_json(data=response)
    except requests.exceptions.HTTPError as e:
        click.echo(f"Error: HTTP {e.response.status_code}", err=True)
        try:
            error_body = e.response.json()
            rich.print_json(data=error_body)
        except json.JSONDecodeError:
            click.echo(e.response.text, err=True)
        raise click.Abort()

# === NexusCore/openenv\Lib\site-packages\pip\_internal\distributions\sdist.py ===
import logging
from typing import TYPE_CHECKING, Iterable, Optional, Set, Tuple

from pip._internal.build_env import BuildEnvironment
from pip._internal.distributions.base import AbstractDistribution
from pip._internal.exceptions import InstallationError
from pip._internal.metadata import BaseDistribution
from pip._internal.utils.subprocess import runner_with_spinner_message

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder

logger = logging.getLogger(__name__)


class SourceDistribution(AbstractDistribution):
    """Represents a source distribution.

    The preparation step for these needs metadata for the packages to be
    generated, either using PEP 517 or using the legacy `setup.py egg_info`.
    """

    @property
    def build_tracker_id(self) -> Optional[str]:
        """Identify this requirement uniquely by its link."""
        assert self.req.link
        return self.req.link.url_without_fragment

    def get_metadata_distribution(self) -> BaseDistribution:
        return self.req.get_dist()

    def prepare_distribution_metadata(
        self,
        finder: "PackageFinder",
        build_isolation: bool,
        check_build_deps: bool,
    ) -> None:
        # Load pyproject.toml, to determine whether PEP 517 is to be used
        self.req.load_pyproject_toml()

        # Set up the build isolation, if this requirement should be isolated
        should_isolate = self.req.use_pep517 and build_isolation
        if should_isolate:
            # Setup an isolated environment and install the build backend static
            # requirements in it.
            self._prepare_build_backend(finder)
            # Check that if the requirement is editable, it either supports PEP 660 or
            # has a setup.py or a setup.cfg. This cannot be done earlier because we need
            # to setup the build backend to verify it supports build_editable, nor can
            # it be done later, because we want to avoid installing build requirements
            # needlessly. Doing it here also works around setuptools generating
            # UNKNOWN.egg-info when running get_requires_for_build_wheel on a directory
            # without setup.py nor setup.cfg.
            self.req.isolated_editable_sanity_check()
            # Install the dynamic build requirements.
            self._install_build_reqs(finder)
        # Check if the current environment provides build dependencies
        should_check_deps = self.req.use_pep517 and check_build_deps
        if should_check_deps:
            pyproject_requires = self.req.pyproject_requires
            assert pyproject_requires is not None
            conflicting, missing = self.req.build_env.check_requirements(
                pyproject_requires
            )
            if conflicting:
                self._raise_conflicts("the backend dependencies", conflicting)
            if missing:
                self._raise_missing_reqs(missing)
        self.req.prepare_metadata()

    def _prepare_build_backend(self, finder: "PackageFinder") -> None:
        # Isolate in a BuildEnvironment and install the build-time
        # requirements.
        pyproject_requires = self.req.pyproject_requires
        assert pyproject_requires is not None

        self.req.build_env = BuildEnvironment()
        self.req.build_env.install_requirements(
            finder, pyproject_requires, "overlay", kind="build dependencies"
        )
        conflicting, missing = self.req.build_env.check_requirements(
            self.req.requirements_to_check
        )
        if conflicting:
            self._raise_conflicts("PEP 517/518 supported requirements", conflicting)
        if missing:
            logger.warning(
                "Missing build requirements in pyproject.toml for %s.",
                self.req,
            )
            logger.warning(
                "The project does not specify a build backend, and "
                "pip cannot fall back to setuptools without %s.",
                " and ".join(map(repr, sorted(missing))),
            )

    def _get_build_requires_wheel(self) -> Iterable[str]:
        with self.req.build_env:
            runner = runner_with_spinner_message("Getting requirements to build wheel")
            backend = self.req.pep517_backend
            assert backend is not None
            with backend.subprocess_runner(runner):
                return backend.get_requires_for_build_wheel()

    def _get_build_requires_editable(self) -> Iterable[str]:
        with self.req.build_env:
            runner = runner_with_spinner_message(
                "Getting requirements to build editable"
            )
            backend = self.req.pep517_backend
            assert backend is not None
            with backend.subprocess_runner(runner):
                return backend.get_requires_for_build_editable()

    def _install_build_reqs(self, finder: "PackageFinder") -> None:
        # Install any extra build dependencies that the backend requests.
        # This must be done in a second pass, as the pyproject.toml
        # dependencies must be installed before we can call the backend.
        if (
            self.req.editable
            and self.req.permit_editable_wheels
            and self.req.supports_pyproject_editable
        ):
            build_reqs = self._get_build_requires_editable()
        else:
            build_reqs = self._get_build_requires_wheel()
        conflicting, missing = self.req.build_env.check_requirements(build_reqs)
        if conflicting:
            self._raise_conflicts("the backend dependencies", conflicting)
        self.req.build_env.install_requirements(
            finder, missing, "normal", kind="backend dependencies"
        )

    def _raise_conflicts(
        self, conflicting_with: str, conflicting_reqs: Set[Tuple[str, str]]
    ) -> None:
        format_string = (
            "Some build dependencies for {requirement} "
            "conflict with {conflicting_with}: {description}."
        )
        error_message = format_string.format(
            requirement=self.req,
            conflicting_with=conflicting_with,
            description=", ".join(
                f"{installed} is incompatible with {wanted}"
                for installed, wanted in sorted(conflicting_reqs)
            ),
        )
        raise InstallationError(error_message)

    def _raise_missing_reqs(self, missing: Set[str]) -> None:
        format_string = (
            "Some build dependencies for {requirement} are missing: {missing}."
        )
        error_message = format_string.format(
            requirement=self.req, missing=", ".join(map(repr, sorted(missing)))
        )
        raise InstallationError(error_message)

# === NexusCore/openenv\Lib\site-packages\win32\Demos\service\pipeTestServiceClient.py ===
# A Test Program for pipeTestService.py
#
# Install and start the Pipe Test service, then run this test
# either from the same machine, or from another using the "-s" param.
#
# Eg: pipeTestServiceClient.py -s server_name Hi There
# Should work.

import os
import sys
import traceback

import pywintypes
import win32api
import winerror

# # Use "import *" to keep this looking as much as a "normal" service
# as possible.  Real code shouldn't do this.
from win32event import *  # nopycln: import
from win32file import *  # nopycln: import
from win32pipe import *  # nopycln: import

verbose = 0

# def ReadFromPipe(pipeName):
# Could (Should?) use CallNamedPipe, but this technique allows variable size
# messages (whereas you must supply a buffer size for CallNamedPipe!
#       hPipe = CreateFile(pipeName, GENERIC_WRITE, 0, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, 0)
#       more = 1
#       while more:
#               hr = ReadFile(hPipe, 256)
#               if hr==0:
#                       more = 0
#               except win32api.error (hr, fn, desc):
#                       if hr==winerror.ERROR_MORE_DATA:
#                               data = dat
#


def CallPipe(fn, args):
    ret = None
    retryCount = 0
    while retryCount < 8:  # Keep looping until user cancels.
        retryCount += 1
        try:
            return fn(*args)
        except win32api.error as exc:
            if exc.winerror == winerror.ERROR_PIPE_BUSY:
                win32api.Sleep(5000)
                continue
            else:
                raise

    raise RuntimeError("Could not make a connection to the server")


def testClient(server, msg):
    if verbose:
        print("Sending", msg)
    data = CallPipe(
        CallNamedPipe,
        ("\\\\%s\\pipe\\PyPipeTest" % server, msg, 256, NMPWAIT_WAIT_FOREVER),
    )
    if verbose:
        print("Server sent back '%s'" % data)
    print("Sent and received a message!")


def testLargeMessage(server, size=4096):
    if verbose:
        print("Sending message of size %d" % (size))
    msg = "*" * size
    data = CallPipe(
        CallNamedPipe,
        ("\\\\%s\\pipe\\PyPipeTest" % server, msg, 512, NMPWAIT_WAIT_FOREVER),
    )
    if len(data) - size:
        print("Sizes are all wrong - send %d, got back %d" % (size, len(data)))


def stressThread(server, numMessages, wait):
    try:
        try:
            for i in range(numMessages):
                r = CallPipe(
                    CallNamedPipe,
                    (
                        "\\\\%s\\pipe\\PyPipeTest" % server,
                        "#" * 512,
                        1024,
                        NMPWAIT_WAIT_FOREVER,
                    ),
                )
        except:
            traceback.print_exc()
            print("Failed after %d messages" % i)
    finally:
        SetEvent(wait)


def stressTestClient(server, numThreads, numMessages):
    import _thread

    thread_waits = []
    for t_num in range(numThreads):
        # Note I could just wait on thread handles (after calling DuplicateHandle)
        # See the service itself for an example of waiting for the clients...
        wait = CreateEvent(None, 0, 0, None)
        thread_waits.append(wait)
        _thread.start_new_thread(stressThread, (server, numMessages, wait))
    # Wait for all threads to finish.
    WaitForMultipleObjects(thread_waits, 1, INFINITE)


def main():
    import getopt

    server = "."
    thread_count = 0
    msg_count = 500
    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:t:m:vl")
        for o, a in opts:
            if o == "-s":
                server = a
            if o == "-m":
                msg_count = int(a)
            if o == "-t":
                thread_count = int(a)
            if o == "-v":
                global verbose
                verbose = 1
            if o == "-l":
                testLargeMessage(server)
        msg = " ".join(args).encode("mbcs")
    except getopt.error as msg:
        print(msg)
        my_name = os.path.split(sys.argv[0])[1]
        print(
            "Usage: %s [-v] [-s server] [-t thread_count=0] [-m msg_count=500] msg ..."
            % my_name
        )
        print("       -v = verbose")
        print(
            "       Specifying a value for -t will stress test using that many threads."
        )
        return
    testClient(server, msg)
    if thread_count > 0:
        print(
            "Spawning %d threads each sending %d messages..."
            % (thread_count, msg_count)
        )
        stressTestClient(server, thread_count, msg_count)


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\win32\Demos\security\sspi\fetch_url.py ===
"""
Fetches a URL from a web-server supporting NTLM authentication
eg, IIS.

If no arguments are specified, a default of http://localhost/localstart.asp
is used.  This script does follow simple 302 redirections, so pointing at the
root of an IIS server is should work.
"""

import http.client  # sorry, this demo needs 2.3+
import optparse
import urllib.error
import urllib.parse
import urllib.request
from base64 import decodestring, encodestring

from sspi import ClientAuth

options = None  # set to optparse options object


def open_url(host, url):
    h = http.client.HTTPConnection(host)
    #    h.set_debuglevel(9)
    h.putrequest("GET", url)
    h.endheaders()
    resp = h.getresponse()
    print("Initial response is", resp.status, resp.reason)
    body = resp.read()
    if resp.status == 302:  # object moved
        url = "/" + resp.msg["location"]
        resp.close()
        h.putrequest("GET", url)
        h.endheaders()
        resp = h.getresponse()
        print("After redirect response is", resp.status, resp.reason)
    if options.show_headers:
        print("Initial response headers:")
        for name, val in resp.msg.items():
            print(f" {name}: {val}")
    if options.show_body:
        print(body)
    if resp.status == 401:
        # 401: Unauthorized - here is where the real work starts
        auth_info = None
        if options.user or options.domain or options.password:
            auth_info = options.user, options.domain, options.password
        ca = ClientAuth("NTLM", auth_info=auth_info)
        auth_scheme = ca.pkg_info["Name"]
        data = None
        while 1:
            err, out_buf = ca.authorize(data)
            data = out_buf[0].Buffer
            # Encode it as base64 as required by HTTP
            auth = encodestring(data).replace("\012", "")
            h.putrequest("GET", url)
            h.putheader("Authorization", auth_scheme + " " + auth)
            h.putheader("Content-Length", "0")
            h.endheaders()
            resp = h.getresponse()
            if options.show_headers:
                print("Token dance headers:")
                for name, val in resp.msg.items():
                    print(f" {name}: {val}")

            if err == 0:
                break
            else:
                if resp.status != 401:
                    print("Eeek - got response", resp.status)
                    cl = resp.msg.get("content-length")
                    if cl:
                        print(repr(resp.read(int(cl))))
                    else:
                        print("no content!")

                assert resp.status == 401, resp.status

            assert not resp.will_close, "NTLM is per-connection - must not close"
            schemes = [
                s.strip() for s in resp.msg.get("WWW-Authenticate", "").split(",")
            ]
            for scheme in schemes:
                if scheme.startswith(auth_scheme):
                    data = decodestring(scheme[len(auth_scheme) + 1 :])
                    break
            else:
                print(f"Could not find scheme '{auth_scheme}' in schemes {schemes!r}")
                break

            resp.read()
    print("Final response status is", resp.status, resp.reason)
    if resp.status == 200:
        # Worked!
        # Check we can read it again without re-authenticating.
        if resp.will_close:
            print(
                "EEEK - response will close, but NTLM is per connection - it must stay open"
            )
        body = resp.read()
        if options.show_body:
            print("Final response body:")
            print(body)
        h.putrequest("GET", url)
        h.endheaders()
        resp = h.getresponse()
        print("Second fetch response is", resp.status, resp.reason)
        if options.show_headers:
            print("Second response headers:")
            for name, val in resp.msg.items():
                print(f" {name}: {val}")

        resp.read(int(resp.msg.get("content-length", 0)))
    elif resp.status == 500:
        print("Error text")
        print(resp.read())
    else:
        if options.show_body:
            cl = resp.msg.get("content-length")
            print(resp.read(int(cl)))


if __name__ == "__main__":
    parser = optparse.OptionParser(description=__doc__)

    parser.add_option(
        "",
        "--show-body",
        action="store_true",
        help="print the body of each response as it is received",
    )

    parser.add_option(
        "",
        "--show-headers",
        action="store_true",
        help="print the headers of each response as it is received",
    )

    parser.add_option("", "--user", action="store", help="The username to login with")

    parser.add_option(
        "", "--password", action="store", help="The password to login with"
    )

    parser.add_option("", "--domain", action="store", help="The domain to login to")

    options, args = parser.parse_args()
    if not args:
        print("Run with --help for usage details")
        args = ["http://localhost/localstart.asp"]
    for url in args:
        scheme, netloc, path, params, query, fragment = urllib.parse.urlparse(url)
        if (scheme != "http") or params or query or fragment:
            parser.error("Scheme must be http, URL must be simple")

        print(f"Opening '{path}' from '{netloc}'")
        r = open_url(netloc, path)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\cachecontrol\heuristics.py ===
# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import calendar
import time
from datetime import datetime, timedelta, timezone
from email.utils import formatdate, parsedate, parsedate_tz
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from pip._vendor.urllib3 import HTTPResponse

TIME_FMT = "%a, %d %b %Y %H:%M:%S GMT"


def expire_after(delta: timedelta, date: datetime | None = None) -> datetime:
    date = date or datetime.now(timezone.utc)
    return date + delta


def datetime_to_header(dt: datetime) -> str:
    return formatdate(calendar.timegm(dt.timetuple()))


class BaseHeuristic:
    def warning(self, response: HTTPResponse) -> str | None:
        """
        Return a valid 1xx warning header value describing the cache
        adjustments.

        The response is provided too allow warnings like 113
        http://tools.ietf.org/html/rfc7234#section-5.5.4 where we need
        to explicitly say response is over 24 hours old.
        """
        return '110 - "Response is Stale"'

    def update_headers(self, response: HTTPResponse) -> dict[str, str]:
        """Update the response headers with any new headers.

        NOTE: This SHOULD always include some Warning header to
              signify that the response was cached by the client, not
              by way of the provided headers.
        """
        return {}

    def apply(self, response: HTTPResponse) -> HTTPResponse:
        updated_headers = self.update_headers(response)

        if updated_headers:
            response.headers.update(updated_headers)
            warning_header_value = self.warning(response)
            if warning_header_value is not None:
                response.headers.update({"Warning": warning_header_value})

        return response


class OneDayCache(BaseHeuristic):
    """
    Cache the response by providing an expires 1 day in the
    future.
    """

    def update_headers(self, response: HTTPResponse) -> dict[str, str]:
        headers = {}

        if "expires" not in response.headers:
            date = parsedate(response.headers["date"])
            expires = expire_after(
                timedelta(days=1),
                date=datetime(*date[:6], tzinfo=timezone.utc),  # type: ignore[index,misc]
            )
            headers["expires"] = datetime_to_header(expires)
            headers["cache-control"] = "public"
        return headers


class ExpiresAfter(BaseHeuristic):
    """
    Cache **all** requests for a defined time period.
    """

    def __init__(self, **kw: Any) -> None:
        self.delta = timedelta(**kw)

    def update_headers(self, response: HTTPResponse) -> dict[str, str]:
        expires = expire_after(self.delta)
        return {"expires": datetime_to_header(expires), "cache-control": "public"}

    def warning(self, response: HTTPResponse) -> str | None:
        tmpl = "110 - Automatically cached for %s. Response might be stale"
        return tmpl % self.delta


class LastModified(BaseHeuristic):
    """
    If there is no Expires header already, fall back on Last-Modified
    using the heuristic from
    http://tools.ietf.org/html/rfc7234#section-4.2.2
    to calculate a reasonable value.

    Firefox also does something like this per
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching_FAQ
    http://lxr.mozilla.org/mozilla-release/source/netwerk/protocol/http/nsHttpResponseHead.cpp#397
    Unlike mozilla we limit this to 24-hr.
    """

    cacheable_by_default_statuses = {
        200,
        203,
        204,
        206,
        300,
        301,
        404,
        405,
        410,
        414,
        501,
    }

    def update_headers(self, resp: HTTPResponse) -> dict[str, str]:
        headers: Mapping[str, str] = resp.headers

        if "expires" in headers:
            return {}

        if "cache-control" in headers and headers["cache-control"] != "public":
            return {}

        if resp.status not in self.cacheable_by_default_statuses:
            return {}

        if "date" not in headers or "last-modified" not in headers:
            return {}

        time_tuple = parsedate_tz(headers["date"])
        assert time_tuple is not None
        date = calendar.timegm(time_tuple[:6])
        last_modified = parsedate(headers["last-modified"])
        if last_modified is None:
            return {}

        now = time.time()
        current_age = max(0, now - date)
        delta = date - calendar.timegm(last_modified)
        freshness_lifetime = max(0, min(delta / 10, 24 * 3600))
        if freshness_lifetime <= current_age:
            return {}

        expires = date + freshness_lifetime
        return {"expires": time.strftime(TIME_FMT, time.gmtime(expires))}

    def warning(self, resp: HTTPResponse) -> str | None:
        return None

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\requests\api.py ===
"""
requests.api
~~~~~~~~~~~~

This module implements the Requests API.

:copyright: (c) 2012 by Kenneth Reitz.
:license: Apache2, see LICENSE for more details.
"""

from . import sessions


def request(method, url, **kwargs):
    """Constructs and sends a :class:`Request <Request>`.

    :param method: method for the new :class:`Request` object: ``GET``, ``OPTIONS``, ``HEAD``, ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
    :param files: (optional) Dictionary of ``'name': file-like-objects`` (or ``{'name': file-tuple}``) for multipart encoding upload.
        ``file-tuple`` can be a 2-tuple ``('filename', fileobj)``, 3-tuple ``('filename', fileobj, 'content_type')``
        or a 4-tuple ``('filename', fileobj, 'content_type', custom_headers)``, where ``'content_type'`` is a string
        defining the content type of the given file and ``custom_headers`` a dict-like object containing additional headers
        to add for the file.
    :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
    :param timeout: (optional) How many seconds to wait for the server to send data
        before giving up, as a float, or a :ref:`(connect timeout, read
        timeout) <timeouts>` tuple.
    :type timeout: float or tuple
    :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection. Defaults to ``True``.
    :type allow_redirects: bool
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``.
    :param stream: (optional) if ``False``, the response content will be immediately downloaded.
    :param cert: (optional) if String, path to ssl client cert file (.pem). If Tuple, ('cert', 'key') pair.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response

    Usage::

      >>> import requests
      >>> req = requests.request('GET', 'https://httpbin.org/get')
      >>> req
      <Response [200]>
    """

    # By using the 'with' statement we are sure the session is closed, thus we
    # avoid leaving sockets open which can trigger a ResourceWarning in some
    # cases, and look like a memory leak in others.
    with sessions.Session() as session:
        return session.request(method=method, url=url, **kwargs)


def get(url, params=None, **kwargs):
    r"""Sends a GET request.

    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("get", url, params=params, **kwargs)


def options(url, **kwargs):
    r"""Sends an OPTIONS request.

    :param url: URL for the new :class:`Request` object.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("options", url, **kwargs)


def head(url, **kwargs):
    r"""Sends a HEAD request.

    :param url: URL for the new :class:`Request` object.
    :param \*\*kwargs: Optional arguments that ``request`` takes. If
        `allow_redirects` is not provided, it will be set to `False` (as
        opposed to the default :meth:`request` behavior).
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    kwargs.setdefault("allow_redirects", False)
    return request("head", url, **kwargs)


def post(url, data=None, json=None, **kwargs):
    r"""Sends a POST request.

    :param url: URL for the new :class:`Request` object.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("post", url, data=data, json=json, **kwargs)


def put(url, data=None, **kwargs):
    r"""Sends a PUT request.

    :param url: URL for the new :class:`Request` object.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("put", url, data=data, **kwargs)


def patch(url, data=None, **kwargs):
    r"""Sends a PATCH request.

    :param url: URL for the new :class:`Request` object.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("patch", url, data=data, **kwargs)


def delete(url, **kwargs):
    r"""Sends a DELETE request.

    :param url: URL for the new :class:`Request` object.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("delete", url, **kwargs)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\formatters\__init__.py ===
"""
    pygments.formatters
    ~~~~~~~~~~~~~~~~~~~

    Pygments formatters.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import sys
import types
import fnmatch
from os.path import basename

from pip._vendor.pygments.formatters._mapping import FORMATTERS
from pip._vendor.pygments.plugin import find_plugin_formatters
from pip._vendor.pygments.util import ClassNotFound

__all__ = ['get_formatter_by_name', 'get_formatter_for_filename',
           'get_all_formatters', 'load_formatter_from_file'] + list(FORMATTERS)

_formatter_cache = {}  # classes by name
_pattern_cache = {}


def _fn_matches(fn, glob):
    """Return whether the supplied file name fn matches pattern filename."""
    if glob not in _pattern_cache:
        pattern = _pattern_cache[glob] = re.compile(fnmatch.translate(glob))
        return pattern.match(fn)
    return _pattern_cache[glob].match(fn)


def _load_formatters(module_name):
    """Load a formatter (and all others in the module too)."""
    mod = __import__(module_name, None, None, ['__all__'])
    for formatter_name in mod.__all__:
        cls = getattr(mod, formatter_name)
        _formatter_cache[cls.name] = cls


def get_all_formatters():
    """Return a generator for all formatter classes."""
    # NB: this returns formatter classes, not info like get_all_lexers().
    for info in FORMATTERS.values():
        if info[1] not in _formatter_cache:
            _load_formatters(info[0])
        yield _formatter_cache[info[1]]
    for _, formatter in find_plugin_formatters():
        yield formatter


def find_formatter_class(alias):
    """Lookup a formatter by alias.

    Returns None if not found.
    """
    for module_name, name, aliases, _, _ in FORMATTERS.values():
        if alias in aliases:
            if name not in _formatter_cache:
                _load_formatters(module_name)
            return _formatter_cache[name]
    for _, cls in find_plugin_formatters():
        if alias in cls.aliases:
            return cls


def get_formatter_by_name(_alias, **options):
    """
    Return an instance of a :class:`.Formatter` subclass that has `alias` in its
    aliases list. The formatter is given the `options` at its instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if no formatter with that
    alias is found.
    """
    cls = find_formatter_class(_alias)
    if cls is None:
        raise ClassNotFound(f"no formatter found for name {_alias!r}")
    return cls(**options)


def load_formatter_from_file(filename, formattername="CustomFormatter", **options):
    """
    Return a `Formatter` subclass instance loaded from the provided file, relative
    to the current directory.

    The file is expected to contain a Formatter class named ``formattername``
    (by default, CustomFormatter). Users should be very careful with the input, because
    this method is equivalent to running ``eval()`` on the input file. The formatter is
    given the `options` at its instantiation.

    :exc:`pygments.util.ClassNotFound` is raised if there are any errors loading
    the formatter.

    .. versionadded:: 2.2
    """
    try:
        # This empty dict will contain the namespace for the exec'd file
        custom_namespace = {}
        with open(filename, 'rb') as f:
            exec(f.read(), custom_namespace)
        # Retrieve the class `formattername` from that namespace
        if formattername not in custom_namespace:
            raise ClassNotFound(f'no valid {formattername} class found in {filename}')
        formatter_class = custom_namespace[formattername]
        # And finally instantiate it with the options
        return formatter_class(**options)
    except OSError as err:
        raise ClassNotFound(f'cannot read {filename}: {err}')
    except ClassNotFound:
        raise
    except Exception as err:
        raise ClassNotFound(f'error when loading custom formatter: {err}')


def get_formatter_for_filename(fn, **options):
    """
    Return a :class:`.Formatter` subclass instance that has a filename pattern
    matching `fn`. The formatter is given the `options` at its instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if no formatter for that filename
    is found.
    """
    fn = basename(fn)
    for modname, name, _, filenames, _ in FORMATTERS.values():
        for filename in filenames:
            if _fn_matches(fn, filename):
                if name not in _formatter_cache:
                    _load_formatters(modname)
                return _formatter_cache[name](**options)
    for _name, cls in find_plugin_formatters():
        for filename in cls.filenames:
            if _fn_matches(fn, filename):
                return cls(**options)
    raise ClassNotFound(f"no formatter found for file name {fn!r}")


class _automodule(types.ModuleType):
    """Automatically import formatters."""

    def __getattr__(self, name):
        info = FORMATTERS.get(name)
        if info:
            _load_formatters(info[0])
            cls = _formatter_cache[info[1]]
            setattr(self, name, cls)
            return cls
        raise AttributeError(name)


oldmod = sys.modules[__name__]
newmod = _automodule(__name__)
newmod.__dict__.update(oldmod.__dict__)
sys.modules[__name__] = newmod
del newmod.newmod, newmod.oldmod, newmod.sys, newmod.types

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc5753.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Elliptic Curve Cryptography (ECC) Algorithms in the CMS
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc5753.txt
#

from pyasn1.type import univ, char, namedtype, namedval, tag, constraint, useful

from pyasn1_modules import rfc5280
from pyasn1_modules import rfc5480
from pyasn1_modules import rfc5652
from pyasn1_modules import rfc5751
from pyasn1_modules import rfc8018


# Imports from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier


# Imports from RFC 5652

OriginatorPublicKey = rfc5652.OriginatorPublicKey

UserKeyingMaterial = rfc5652.UserKeyingMaterial


# Imports from RFC 5480

ECDSA_Sig_Value = rfc5480.ECDSA_Sig_Value

ECParameters = rfc5480.ECParameters

ECPoint = rfc5480.ECPoint

id_ecPublicKey = rfc5480.id_ecPublicKey


# Imports from RFC 8018

id_hmacWithSHA224 = rfc8018.id_hmacWithSHA224

id_hmacWithSHA256 = rfc8018.id_hmacWithSHA256

id_hmacWithSHA384 = rfc8018.id_hmacWithSHA384

id_hmacWithSHA512 = rfc8018.id_hmacWithSHA512


# Object Identifier arcs

x9_63_scheme = univ.ObjectIdentifier('1.3.133.16.840.63.0')

secg_scheme = univ.ObjectIdentifier('1.3.132.1')


# Object Identifiers for the algorithms

dhSinglePass_cofactorDH_sha1kdf_scheme = x9_63_scheme + (3, )

dhSinglePass_cofactorDH_sha224kdf_scheme = secg_scheme + (14, 0, )

dhSinglePass_cofactorDH_sha256kdf_scheme = secg_scheme + (14, 1, )

dhSinglePass_cofactorDH_sha384kdf_scheme = secg_scheme + (14, 2, )

dhSinglePass_cofactorDH_sha512kdf_scheme = secg_scheme + (14, 3, )

dhSinglePass_stdDH_sha1kdf_scheme = x9_63_scheme + (2, )

dhSinglePass_stdDH_sha224kdf_scheme = secg_scheme + (11, 0, )

dhSinglePass_stdDH_sha256kdf_scheme = secg_scheme + (11, 1, )

dhSinglePass_stdDH_sha384kdf_scheme = secg_scheme + (11, 2, )

dhSinglePass_stdDH_sha512kdf_scheme = secg_scheme + (11, 3, )

mqvSinglePass_sha1kdf_scheme = x9_63_scheme + (16, )

mqvSinglePass_sha224kdf_scheme = secg_scheme + (15, 0, )

mqvSinglePass_sha256kdf_scheme = secg_scheme + (15, 1, )

mqvSinglePass_sha384kdf_scheme = secg_scheme + (15, 2, )

mqvSinglePass_sha512kdf_scheme = secg_scheme + (15, 3, )


# Structures for parameters and key derivation

class IV(univ.OctetString):
    # Exactly 8 octets
    pass


class CBCParameter(IV):
    pass


class KeyWrapAlgorithm(AlgorithmIdentifier):
    pass


class ECC_CMS_SharedInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('keyInfo', KeyWrapAlgorithm()),
        namedtype.OptionalNamedType('entityUInfo',
            univ.OctetString().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('suppPubInfo',
            univ.OctetString().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class MQVuserKeyingMaterial(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('ephemeralPublicKey', OriginatorPublicKey()),
        namedtype.OptionalNamedType('addedukm',
            UserKeyingMaterial().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


# Update the Algorithm Identifier map in rfc5280.py and
# Update the SMIMECapabilities Attribute Map in rfc5751.py

_algorithmIdentifierMapUpdate = {
    dhSinglePass_stdDH_sha1kdf_scheme: KeyWrapAlgorithm(),
    dhSinglePass_stdDH_sha224kdf_scheme: KeyWrapAlgorithm(),
    dhSinglePass_stdDH_sha256kdf_scheme: KeyWrapAlgorithm(),
    dhSinglePass_stdDH_sha384kdf_scheme: KeyWrapAlgorithm(),
    dhSinglePass_stdDH_sha512kdf_scheme: KeyWrapAlgorithm(),
    dhSinglePass_cofactorDH_sha1kdf_scheme: KeyWrapAlgorithm(),
    dhSinglePass_cofactorDH_sha224kdf_scheme: KeyWrapAlgorithm(),
    dhSinglePass_cofactorDH_sha256kdf_scheme: KeyWrapAlgorithm(),
    dhSinglePass_cofactorDH_sha384kdf_scheme: KeyWrapAlgorithm(),
    dhSinglePass_cofactorDH_sha512kdf_scheme: KeyWrapAlgorithm(),
    mqvSinglePass_sha1kdf_scheme: KeyWrapAlgorithm(),
    mqvSinglePass_sha224kdf_scheme: KeyWrapAlgorithm(),
    mqvSinglePass_sha256kdf_scheme: KeyWrapAlgorithm(),
    mqvSinglePass_sha384kdf_scheme: KeyWrapAlgorithm(),
    mqvSinglePass_sha512kdf_scheme: KeyWrapAlgorithm(),
}

rfc5280.algorithmIdentifierMap.update(_algorithmIdentifierMapUpdate)

rfc5751.smimeCapabilityMap.update(_algorithmIdentifierMapUpdate)

# === NexusCore/openenv\Lib\site-packages\pydantic\root_model.py ===
"""RootModel class and type definitions."""

from __future__ import annotations as _annotations

import typing
from copy import copy, deepcopy

from pydantic_core import PydanticUndefined

from . import PydanticUserError
from ._internal import _model_construction, _repr
from .main import BaseModel, _object_setattr

if typing.TYPE_CHECKING:
    from typing import Any, Literal

    from typing_extensions import Self, dataclass_transform

    from .fields import Field as PydanticModelField
    from .fields import PrivateAttr as PydanticModelPrivateAttr

    # dataclass_transform could be applied to RootModel directly, but `ModelMetaclass`'s dataclass_transform
    # takes priority (at least with pyright). We trick type checkers into thinking we apply dataclass_transform
    # on a new metaclass.
    @dataclass_transform(kw_only_default=False, field_specifiers=(PydanticModelField, PydanticModelPrivateAttr))
    class _RootModelMetaclass(_model_construction.ModelMetaclass): ...
else:
    _RootModelMetaclass = _model_construction.ModelMetaclass

__all__ = ('RootModel',)

RootModelRootType = typing.TypeVar('RootModelRootType')


class RootModel(BaseModel, typing.Generic[RootModelRootType], metaclass=_RootModelMetaclass):
    """!!! abstract "Usage Documentation"
        [`RootModel` and Custom Root Types](../concepts/models.md#rootmodel-and-custom-root-types)

    A Pydantic `BaseModel` for the root object of the model.

    Attributes:
        root: The root object of the model.
        __pydantic_root_model__: Whether the model is a RootModel.
        __pydantic_private__: Private fields in the model.
        __pydantic_extra__: Extra fields in the model.

    """

    __pydantic_root_model__ = True
    __pydantic_private__ = None
    __pydantic_extra__ = None

    root: RootModelRootType

    def __init_subclass__(cls, **kwargs):
        extra = cls.model_config.get('extra')
        if extra is not None:
            raise PydanticUserError(
                "`RootModel` does not support setting `model_config['extra']`", code='root-model-extra'
            )
        super().__init_subclass__(**kwargs)

    def __init__(self, /, root: RootModelRootType = PydanticUndefined, **data) -> None:  # type: ignore
        __tracebackhide__ = True
        if data:
            if root is not PydanticUndefined:
                raise ValueError(
                    '"RootModel.__init__" accepts either a single positional argument or arbitrary keyword arguments'
                )
            root = data  # type: ignore
        self.__pydantic_validator__.validate_python(root, self_instance=self)

    __init__.__pydantic_base_init__ = True  # pyright: ignore[reportFunctionMemberAccess]

    @classmethod
    def model_construct(cls, root: RootModelRootType, _fields_set: set[str] | None = None) -> Self:  # type: ignore
        """Create a new model using the provided root object and update fields set.

        Args:
            root: The root object of the model.
            _fields_set: The set of fields to be updated.

        Returns:
            The new model.

        Raises:
            NotImplemented: If the model is not a subclass of `RootModel`.
        """
        return super().model_construct(root=root, _fields_set=_fields_set)

    def __getstate__(self) -> dict[Any, Any]:
        return {
            '__dict__': self.__dict__,
            '__pydantic_fields_set__': self.__pydantic_fields_set__,
        }

    def __setstate__(self, state: dict[Any, Any]) -> None:
        _object_setattr(self, '__pydantic_fields_set__', state['__pydantic_fields_set__'])
        _object_setattr(self, '__dict__', state['__dict__'])

    def __copy__(self) -> Self:
        """Returns a shallow copy of the model."""
        cls = type(self)
        m = cls.__new__(cls)
        _object_setattr(m, '__dict__', copy(self.__dict__))
        _object_setattr(m, '__pydantic_fields_set__', copy(self.__pydantic_fields_set__))
        return m

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> Self:
        """Returns a deep copy of the model."""
        cls = type(self)
        m = cls.__new__(cls)
        _object_setattr(m, '__dict__', deepcopy(self.__dict__, memo=memo))
        # This next line doesn't need a deepcopy because __pydantic_fields_set__ is a set[str],
        # and attempting a deepcopy would be marginally slower.
        _object_setattr(m, '__pydantic_fields_set__', copy(self.__pydantic_fields_set__))
        return m

    if typing.TYPE_CHECKING:

        def model_dump(  # type: ignore
            self,
            *,
            mode: Literal['json', 'python'] | str = 'python',
            include: Any = None,
            exclude: Any = None,
            context: dict[str, Any] | None = None,
            by_alias: bool | None = None,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            round_trip: bool = False,
            warnings: bool | Literal['none', 'warn', 'error'] = True,
            serialize_as_any: bool = False,
        ) -> Any:
            """This method is included just to get a more accurate return type for type checkers.
            It is included in this `if TYPE_CHECKING:` block since no override is actually necessary.

            See the documentation of `BaseModel.model_dump` for more details about the arguments.

            Generally, this method will have a return type of `RootModelRootType`, assuming that `RootModelRootType` is
            not a `BaseModel` subclass. If `RootModelRootType` is a `BaseModel` subclass, then the return
            type will likely be `dict[str, Any]`, as `model_dump` calls are recursive. The return type could
            even be something different, in the case of a custom serializer.
            Thus, `Any` is used here to catch all of these cases.
            """
            ...

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, RootModel):
            return NotImplemented
        return self.__pydantic_fields__['root'].annotation == other.__pydantic_fields__[
            'root'
        ].annotation and super().__eq__(other)

    def __repr_args__(self) -> _repr.ReprArgs:
        yield 'root', self.root

# === NexusCore/openenv\Lib\site-packages\requests\api.py ===
"""
requests.api
~~~~~~~~~~~~

This module implements the Requests API.

:copyright: (c) 2012 by Kenneth Reitz.
:license: Apache2, see LICENSE for more details.
"""

from . import sessions


def request(method, url, **kwargs):
    """Constructs and sends a :class:`Request <Request>`.

    :param method: method for the new :class:`Request` object: ``GET``, ``OPTIONS``, ``HEAD``, ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
    :param files: (optional) Dictionary of ``'name': file-like-objects`` (or ``{'name': file-tuple}``) for multipart encoding upload.
        ``file-tuple`` can be a 2-tuple ``('filename', fileobj)``, 3-tuple ``('filename', fileobj, 'content_type')``
        or a 4-tuple ``('filename', fileobj, 'content_type', custom_headers)``, where ``'content_type'`` is a string
        defining the content type of the given file and ``custom_headers`` a dict-like object containing additional headers
        to add for the file.
    :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
    :param timeout: (optional) How many seconds to wait for the server to send data
        before giving up, as a float, or a :ref:`(connect timeout, read
        timeout) <timeouts>` tuple.
    :type timeout: float or tuple
    :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection. Defaults to ``True``.
    :type allow_redirects: bool
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``.
    :param stream: (optional) if ``False``, the response content will be immediately downloaded.
    :param cert: (optional) if String, path to ssl client cert file (.pem). If Tuple, ('cert', 'key') pair.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response

    Usage::

      >>> import requests
      >>> req = requests.request('GET', 'https://httpbin.org/get')
      >>> req
      <Response [200]>
    """

    # By using the 'with' statement we are sure the session is closed, thus we
    # avoid leaving sockets open which can trigger a ResourceWarning in some
    # cases, and look like a memory leak in others.
    with sessions.Session() as session:
        return session.request(method=method, url=url, **kwargs)


def get(url, params=None, **kwargs):
    r"""Sends a GET request.

    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("get", url, params=params, **kwargs)


def options(url, **kwargs):
    r"""Sends an OPTIONS request.

    :param url: URL for the new :class:`Request` object.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("options", url, **kwargs)


def head(url, **kwargs):
    r"""Sends a HEAD request.

    :param url: URL for the new :class:`Request` object.
    :param \*\*kwargs: Optional arguments that ``request`` takes. If
        `allow_redirects` is not provided, it will be set to `False` (as
        opposed to the default :meth:`request` behavior).
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    kwargs.setdefault("allow_redirects", False)
    return request("head", url, **kwargs)


def post(url, data=None, json=None, **kwargs):
    r"""Sends a POST request.

    :param url: URL for the new :class:`Request` object.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("post", url, data=data, json=json, **kwargs)


def put(url, data=None, **kwargs):
    r"""Sends a PUT request.

    :param url: URL for the new :class:`Request` object.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("put", url, data=data, **kwargs)


def patch(url, data=None, **kwargs):
    r"""Sends a PATCH request.

    :param url: URL for the new :class:`Request` object.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("patch", url, data=data, **kwargs)


def delete(url, **kwargs):
    r"""Sends a DELETE request.

    :param url: URL for the new :class:`Request` object.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("delete", url, **kwargs)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\types\model.py ===
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
        "Model",
    },
)


class Model(proto.Message):
    r"""Information about a Generative Language Model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        name (str):
            Required. The resource name of the ``Model``.

            Format: ``models/{model}`` with a ``{model}`` naming
            convention of:

            -  "{base_model_id}-{version}"

            Examples:

            -  ``models/chat-bison-001``
        base_model_id (str):
            Required. The name of the base model, pass this to the
            generation request.

            Examples:

            -  ``chat-bison``
        version (str):
            Required. The version number of the model.

            This represents the major version
        display_name (str):
            The human-readable name of the model. E.g.
            "Chat Bison".
            The name can be up to 128 characters long and
            can consist of any UTF-8 characters.
        description (str):
            A short description of the model.
        input_token_limit (int):
            Maximum number of input tokens allowed for
            this model.
        output_token_limit (int):
            Maximum number of output tokens available for
            this model.
        supported_generation_methods (MutableSequence[str]):
            The model's supported generation methods.

            The method names are defined as Pascal case strings, such as
            ``generateMessage`` which correspond to API methods.
        temperature (float):
            Controls the randomness of the output.

            Values can range over ``[0.0,1.0]``, inclusive. A value
            closer to ``1.0`` will produce responses that are more
            varied, while a value closer to ``0.0`` will typically
            result in less surprising responses from the model. This
            value specifies default to be used by the backend while
            making the call to the model.

            This field is a member of `oneof`_ ``_temperature``.
        top_p (float):
            For Nucleus sampling.

            Nucleus sampling considers the smallest set of tokens whose
            probability sum is at least ``top_p``. This value specifies
            default to be used by the backend while making the call to
            the model.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            For Top-k sampling.

            Top-k sampling considers the set of ``top_k`` most probable
            tokens. This value specifies default to be used by the
            backend while making the call to the model. If empty,
            indicates the model doesn't use top-k sampling, and
            ``top_k`` isn't allowed as a generation parameter.

            This field is a member of `oneof`_ ``_top_k``.
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    base_model_id: str = proto.Field(
        proto.STRING,
        number=2,
    )
    version: str = proto.Field(
        proto.STRING,
        number=3,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=4,
    )
    description: str = proto.Field(
        proto.STRING,
        number=5,
    )
    input_token_limit: int = proto.Field(
        proto.INT32,
        number=6,
    )
    output_token_limit: int = proto.Field(
        proto.INT32,
        number=7,
    )
    supported_generation_methods: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=8,
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=9,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=10,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=11,
        optional=True,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\interpreter\computer_use\tools\bash.py ===
import asyncio
import os
from typing import ClassVar, Literal

from anthropic.types.beta import BetaToolBash20241022Param

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult


class _BashSession:
    """A session of a bash shell."""

    _started: bool
    _process: asyncio.subprocess.Process

    command: str = "/bin/bash"
    _output_delay: float = 0.2  # seconds
    _timeout: float = 120.0  # seconds
    _sentinel: str = "<<exit>>"

    def __init__(self):
        self._started = False
        self._timed_out = False

    async def start(self):
        if self._started:
            return

        self._process = await asyncio.create_subprocess_shell(
            self.command,
            preexec_fn=os.setsid,
            shell=True,
            bufsize=0,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        self._started = True

    def stop(self):
        """Terminate the bash shell."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return
        self._process.terminate()

    async def run(self, command: str):
        """Execute a command in the bash shell."""
        # Ask for user permission before executing the command
        print(f"Do you want to execute the following command?\n{command}")
        user_input = input("Enter 'yes' to proceed, anything else to cancel: ")

        if user_input.lower() != "yes":
            return ToolResult(
                system="Command execution cancelled by user",
                error="User did not provide permission to execute the command.",
            )
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return ToolResult(
                system="tool must be restarted",
                error=f"bash has exited with returncode {self._process.returncode}",
            )
        if self._timed_out:
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            )

        # we know these are not None because we created the process with PIPEs
        assert self._process.stdin
        assert self._process.stdout
        assert self._process.stderr

        # send command to the process
        self._process.stdin.write(
            command.encode() + f"; echo '{self._sentinel}'\n".encode()
        )
        await self._process.stdin.drain()

        # read output from the process, until the sentinel is found
        try:
            async with asyncio.timeout(self._timeout):
                while True:
                    await asyncio.sleep(self._output_delay)
                    # if we read directly from stdout/stderr, it will wait forever for
                    # EOF. use the StreamReader buffer directly instead.
                    output = (
                        self._process.stdout._buffer.decode()
                    )  # pyright: ignore[reportAttributeAccessIssue]
                    if self._sentinel in output:
                        # strip the sentinel and break
                        output = output[: output.index(self._sentinel)]
                        break
        except asyncio.TimeoutError:
            self._timed_out = True
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            ) from None

        if output.endswith("\n"):
            output = output[:-1]

        error = (
            self._process.stderr._buffer.decode()
        )  # pyright: ignore[reportAttributeAccessIssue]
        if error.endswith("\n"):
            error = error[:-1]

        # clear the buffers so that the next output can be read correctly
        self._process.stdout._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]
        self._process.stderr._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]

        return CLIResult(output=output, error=error)


class BashTool(BaseAnthropicTool):
    """
    A tool that allows the agent to run bash commands.
    The tool parameters are defined by Anthropic and are not editable.
    """

    _session: _BashSession | None
    name: ClassVar[Literal["bash"]] = "bash"
    api_type: ClassVar[Literal["bash_20241022"]] = "bash_20241022"

    def __init__(self):
        self._session = None
        super().__init__()

    async def __call__(
        self, command: str | None = None, restart: bool = False, **kwargs
    ):
        if restart:
            if self._session:
                self._session.stop()
            self._session = _BashSession()
            await self._session.start()

            return ToolResult(system="tool has been restarted.")

        if self._session is None:
            self._session = _BashSession()
            await self._session.start()

        if command is not None:
            return await self._session.run(command)

        raise ToolError("no command provided.")

    def to_params(self) -> BetaToolBash20241022Param:
        return {
            "type": self.api_type,
            "name": self.name,
        }

# === NexusCore/openenv\Lib\site-packages\joblib\test\test_config.py ===
import os

from joblib._parallel_backends import (
    LokyBackend,
    MultiprocessingBackend,
    ThreadingBackend,
)
from joblib.parallel import (
    BACKENDS,
    DEFAULT_BACKEND,
    EXTERNAL_BACKENDS,
    Parallel,
    delayed,
    parallel_backend,
    parallel_config,
)
from joblib.test.common import np, with_multiprocessing, with_numpy
from joblib.test.test_parallel import check_memmap
from joblib.testing import parametrize, raises


@parametrize("context", [parallel_config, parallel_backend])
def test_global_parallel_backend(context):
    default = Parallel()._backend

    pb = context("threading")
    try:
        assert isinstance(Parallel()._backend, ThreadingBackend)
    finally:
        pb.unregister()
    assert type(Parallel()._backend) is type(default)


@parametrize("context", [parallel_config, parallel_backend])
def test_external_backends(context):
    def register_foo():
        BACKENDS["foo"] = ThreadingBackend

    EXTERNAL_BACKENDS["foo"] = register_foo
    try:
        with context("foo"):
            assert isinstance(Parallel()._backend, ThreadingBackend)
    finally:
        del EXTERNAL_BACKENDS["foo"]


@with_numpy
@with_multiprocessing
def test_parallel_config_no_backend(tmpdir):
    # Check that parallel_config allows to change the config
    # even if no backend is set.
    with parallel_config(n_jobs=2, max_nbytes=1, temp_folder=tmpdir):
        with Parallel(prefer="processes") as p:
            assert isinstance(p._backend, LokyBackend)
            assert p.n_jobs == 2

            # Checks that memmapping is enabled
            p(delayed(check_memmap)(a) for a in [np.random.random(10)] * 2)
            assert len(os.listdir(tmpdir)) > 0


@with_numpy
@with_multiprocessing
def test_parallel_config_params_explicit_set(tmpdir):
    with parallel_config(n_jobs=3, max_nbytes=1, temp_folder=tmpdir):
        with Parallel(n_jobs=2, prefer="processes", max_nbytes="1M") as p:
            assert isinstance(p._backend, LokyBackend)
            assert p.n_jobs == 2

            # Checks that memmapping is disabled
            with raises(TypeError, match="Expected np.memmap instance"):
                p(delayed(check_memmap)(a) for a in [np.random.random(10)] * 2)


@parametrize("param", ["prefer", "require"])
def test_parallel_config_bad_params(param):
    # Check that an error is raised when setting a wrong backend
    # hint or constraint
    with raises(ValueError, match=f"{param}=wrong is not a valid"):
        with parallel_config(**{param: "wrong"}):
            Parallel()


def test_parallel_config_constructor_params():
    # Check that an error is raised when backend is None
    # but backend constructor params are given
    with raises(ValueError, match="only supported when backend is not None"):
        with parallel_config(inner_max_num_threads=1):
            pass

    with raises(ValueError, match="only supported when backend is not None"):
        with parallel_config(backend_param=1):
            pass

    with raises(ValueError, match="only supported when backend is a string"):
        with parallel_config(backend=BACKENDS[DEFAULT_BACKEND], backend_param=1):
            pass


def test_parallel_config_nested():
    # Check that nested configuration retrieves the info from the
    # parent config and do not reset them.

    with parallel_config(n_jobs=2):
        p = Parallel()
        assert isinstance(p._backend, BACKENDS[DEFAULT_BACKEND])
        assert p.n_jobs == 2

    with parallel_config(backend="threading"):
        with parallel_config(n_jobs=2):
            p = Parallel()
            assert isinstance(p._backend, ThreadingBackend)
            assert p.n_jobs == 2

    with parallel_config(verbose=100):
        with parallel_config(n_jobs=2):
            p = Parallel()
            assert p.verbose == 100
            assert p.n_jobs == 2


@with_numpy
@with_multiprocessing
@parametrize(
    "backend",
    ["multiprocessing", "threading", MultiprocessingBackend(), ThreadingBackend()],
)
@parametrize("context", [parallel_config, parallel_backend])
def test_threadpool_limitation_in_child_context_error(context, backend):
    with raises(AssertionError, match=r"does not acc.*inner_max_num_threads"):
        context(backend, inner_max_num_threads=1)


@parametrize("context", [parallel_config, parallel_backend])
def test_parallel_n_jobs_none(context):
    # Check that n_jobs=None is interpreted as "unset" in Parallel
    # non regression test for #1473
    with context(backend="threading", n_jobs=2):
        with Parallel(n_jobs=None) as p:
            assert p.n_jobs == 2

    with context(backend="threading"):
        default_n_jobs = Parallel().n_jobs
        with Parallel(n_jobs=None) as p:
            assert p.n_jobs == default_n_jobs


@parametrize("context", [parallel_config, parallel_backend])
def test_parallel_config_n_jobs_none(context):
    # Check that n_jobs=None is interpreted as "explicitly set" in
    # parallel_(config/backend)
    # non regression test for #1473
    with context(backend="threading", n_jobs=2):
        with context(backend="threading", n_jobs=None):
            # n_jobs=None resets n_jobs to backend's default
            with Parallel() as p:
                assert p.n_jobs == 1

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\galileo.py ===
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

import litellm
from litellm._logging import verbose_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)


# from here: https://docs.rungalileo.io/galileo/gen-ai-studio-products/galileo-observe/how-to/logging-data-via-restful-apis#structuring-your-records
class LLMResponse(BaseModel):
    latency_ms: int
    status_code: int
    input_text: str
    output_text: str
    node_type: str
    model: str
    num_input_tokens: int
    num_output_tokens: int
    output_logprobs: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional. When available, logprobs are used to compute Uncertainty.",
    )
    created_at: str = Field(
        ..., description='timestamp constructed in "%Y-%m-%dT%H:%M:%S" format'
    )
    tags: Optional[List[str]] = None
    user_metadata: Optional[Dict[str, Any]] = None


class GalileoObserve(CustomLogger):
    def __init__(self) -> None:
        self.in_memory_records: List[dict] = []
        self.batch_size = 1
        self.base_url = os.getenv("GALILEO_BASE_URL", None)
        self.project_id = os.getenv("GALILEO_PROJECT_ID", None)
        self.headers: Optional[Dict[str, str]] = None
        self.async_httpx_handler = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.LoggingCallback
        )
        pass

    def set_galileo_headers(self):
        # following https://docs.rungalileo.io/galileo/gen-ai-studio-products/galileo-observe/how-to/logging-data-via-restful-apis#logging-your-records

        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        galileo_login_response = litellm.module_level_client.post(
            url=f"{self.base_url}/login",
            headers=headers,
            data={
                "username": os.getenv("GALILEO_USERNAME"),
                "password": os.getenv("GALILEO_PASSWORD"),
            },
        )

        access_token = galileo_login_response.json()["access_token"]

        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

    def get_output_str_from_response(self, response_obj, kwargs):
        output = None
        if response_obj is not None and (
            kwargs.get("call_type", None) == "embedding"
            or isinstance(response_obj, litellm.EmbeddingResponse)
        ):
            output = None
        elif response_obj is not None and isinstance(
            response_obj, litellm.ModelResponse
        ):
            output = response_obj["choices"][0]["message"].json()
        elif response_obj is not None and isinstance(
            response_obj, litellm.TextCompletionResponse
        ):
            output = response_obj.choices[0].text
        elif response_obj is not None and isinstance(
            response_obj, litellm.ImageResponse
        ):
            output = response_obj["data"]

        return output

    async def async_log_success_event(
        self, kwargs: Any, response_obj: Any, start_time: Any, end_time: Any
    ):
        verbose_logger.debug("On Async Success")

        _latency_ms = int((end_time - start_time).total_seconds() * 1000)
        _call_type = kwargs.get("call_type", "litellm")
        input_text = litellm.utils.get_formatted_prompt(
            data=kwargs, call_type=_call_type
        )

        _usage = response_obj.get("usage", {}) or {}
        num_input_tokens = _usage.get("prompt_tokens", 0)
        num_output_tokens = _usage.get("completion_tokens", 0)

        output_text = self.get_output_str_from_response(
            response_obj=response_obj, kwargs=kwargs
        )

        if output_text is not None:
            request_record = LLMResponse(
                latency_ms=_latency_ms,
                status_code=200,
                input_text=input_text,
                output_text=output_text,
                node_type=_call_type,
                model=kwargs.get("model", "-"),
                num_input_tokens=num_input_tokens,
                num_output_tokens=num_output_tokens,
                created_at=start_time.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),  # timestamp str constructed in "%Y-%m-%dT%H:%M:%S" format
            )

            # dump to dict
            request_dict = request_record.model_dump()
            self.in_memory_records.append(request_dict)

            if len(self.in_memory_records) >= self.batch_size:
                await self.flush_in_memory_records()

    async def flush_in_memory_records(self):
        verbose_logger.debug("flushing in memory records")
        response = await self.async_httpx_handler.post(
            url=f"{self.base_url}/projects/{self.project_id}/observe/ingest",
            headers=self.headers,
            json={"records": self.in_memory_records},
        )

        if response.status_code == 200:
            verbose_logger.debug(
                "Galileo Logger:successfully flushed in memory records"
            )
            self.in_memory_records = []
        else:
            verbose_logger.debug("Galileo Logger: failed to flush in memory records")
            verbose_logger.debug(
                "Galileo Logger error=%s, status code=%s",
                response.text,
                response.status_code,
            )

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        verbose_logger.debug("On Async Failure")

# === NexusCore/openenv\Lib\site-packages\litellm\responses\litellm_completion_transformation\streaming_iterator.py ===
from typing import List, Optional, Union

import litellm
from litellm.main import stream_chunk_builder
from litellm.responses.litellm_completion_transformation.transformation import (
    LiteLLMCompletionResponsesConfig,
)
from litellm.responses.streaming_iterator import ResponsesAPIStreamingIterator
from litellm.types.llms.openai import (
    OutputTextDeltaEvent,
    ResponseCompletedEvent,
    ResponseInputParam,
    ResponsesAPIOptionalRequestParams,
    ResponsesAPIStreamEvents,
    ResponsesAPIStreamingResponse,
)
from litellm.types.utils import Delta as ChatCompletionDelta
from litellm.types.utils import (
    ModelResponse,
    ModelResponseStream,
    StreamingChoices,
    TextCompletionResponse,
)


class LiteLLMCompletionStreamingIterator(ResponsesAPIStreamingIterator):
    """
    Async iterator for processing streaming responses from the Responses API.
    """

    def __init__(
        self,
        litellm_custom_stream_wrapper: litellm.CustomStreamWrapper,
        request_input: Union[str, ResponseInputParam],
        responses_api_request: ResponsesAPIOptionalRequestParams,
    ):
        self.litellm_custom_stream_wrapper: litellm.CustomStreamWrapper = (
            litellm_custom_stream_wrapper
        )
        self.request_input: Union[str, ResponseInputParam] = request_input
        self.responses_api_request: ResponsesAPIOptionalRequestParams = (
            responses_api_request
        )
        self.collected_chat_completion_chunks: List[ModelResponseStream] = []
        self.finished: bool = False

    async def __anext__(
        self,
    ) -> Union[ResponsesAPIStreamingResponse, ResponseCompletedEvent]:
        try:
            while True:
                if self.finished is True:
                    raise StopAsyncIteration
                # Get the next chunk from the stream
                try:
                    chunk = await self.litellm_custom_stream_wrapper.__anext__()
                    self.collected_chat_completion_chunks.append(chunk)
                    response_api_chunk = (
                        self._transform_chat_completion_chunk_to_response_api_chunk(
                            chunk
                        )
                    )
                    if response_api_chunk:
                        return response_api_chunk
                except StopAsyncIteration:
                    self.finished = True
                    response_completed_event = self._emit_response_completed_event()
                    if response_completed_event:
                        return response_completed_event
                    else:
                        raise StopAsyncIteration

        except Exception as e:
            # Handle HTTP errors
            self.finished = True
            raise e

    def __iter__(self):
        return self

    def __next__(
        self,
    ) -> Union[ResponsesAPIStreamingResponse, ResponseCompletedEvent]:
        try:
            while True:
                if self.finished is True:
                    raise StopIteration
                # Get the next chunk from the stream
                try:
                    chunk = self.litellm_custom_stream_wrapper.__next__()
                    self.collected_chat_completion_chunks.append(chunk)
                    response_api_chunk = (
                        self._transform_chat_completion_chunk_to_response_api_chunk(
                            chunk
                        )
                    )
                    if response_api_chunk:
                        return response_api_chunk
                except StopIteration:
                    self.finished = True
                    response_completed_event = self._emit_response_completed_event()
                    if response_completed_event:
                        return response_completed_event
                    else:
                        raise StopIteration

        except Exception as e:
            # Handle HTTP errors
            self.finished = True
            raise e

    def _transform_chat_completion_chunk_to_response_api_chunk(
        self, chunk: ModelResponseStream
    ) -> Optional[ResponsesAPIStreamingResponse]:
        """
        Transform a chat completion chunk to a response API chunk.

        This currently only handles emitting the OutputTextDeltaEvent, which is used by other tools using the responses API.
        """
        return OutputTextDeltaEvent(
            type=ResponsesAPIStreamEvents.OUTPUT_TEXT_DELTA,
            item_id=chunk.id,
            output_index=0,
            content_index=0,
            delta=self._get_delta_string_from_streaming_choices(chunk.choices),
        )

    def _get_delta_string_from_streaming_choices(
        self, choices: List[StreamingChoices]
    ) -> str:
        """
        Get the delta string from the streaming choices

        For now this collected the first choice's delta string.

        It's unclear how users expect litellm to translate multiple-choices-per-chunk to the responses API output.
        """
        choice = choices[0]
        chat_completion_delta: ChatCompletionDelta = choice.delta
        return chat_completion_delta.content or ""

    def _emit_response_completed_event(self) -> Optional[ResponseCompletedEvent]:
        litellm_model_response: Optional[
            Union[ModelResponse, TextCompletionResponse]
        ] = stream_chunk_builder(chunks=self.collected_chat_completion_chunks)
        if litellm_model_response and isinstance(litellm_model_response, ModelResponse):

            return ResponseCompletedEvent(
                type=ResponsesAPIStreamEvents.RESPONSE_COMPLETED,
                response=LiteLLMCompletionResponsesConfig.transform_chat_completion_response_to_responses_api_response(
                    request_input=self.request_input,
                    chat_completion_response=litellm_model_response,
                    responses_api_request=self.responses_api_request,
                ),
            )
        else:
            return None

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axes_grid1\axes_rgb.py ===
from types import MethodType

import numpy as np

from .axes_divider import make_axes_locatable, Size
from .mpl_axes import Axes, SimpleAxisArtist


def make_rgb_axes(ax, pad=0.01, axes_class=None, **kwargs):
    """
    Parameters
    ----------
    ax : `~matplotlib.axes.Axes`
        Axes instance to create the RGB Axes in.
    pad : float, optional
        Fraction of the Axes height to pad.
    axes_class : `matplotlib.axes.Axes` or None, optional
        Axes class to use for the R, G, and B Axes. If None, use
        the same class as *ax*.
    **kwargs
        Forwarded to *axes_class* init for the R, G, and B Axes.
    """

    divider = make_axes_locatable(ax)

    pad_size = pad * Size.AxesY(ax)

    xsize = ((1-2*pad)/3) * Size.AxesX(ax)
    ysize = ((1-2*pad)/3) * Size.AxesY(ax)

    divider.set_horizontal([Size.AxesX(ax), pad_size, xsize])
    divider.set_vertical([ysize, pad_size, ysize, pad_size, ysize])

    ax.set_axes_locator(divider.new_locator(0, 0, ny1=-1))

    ax_rgb = []
    if axes_class is None:
        axes_class = type(ax)

    for ny in [4, 2, 0]:
        ax1 = axes_class(ax.get_figure(), ax.get_position(original=True),
                         sharex=ax, sharey=ax, **kwargs)
        locator = divider.new_locator(nx=2, ny=ny)
        ax1.set_axes_locator(locator)
        for t in ax1.yaxis.get_ticklabels() + ax1.xaxis.get_ticklabels():
            t.set_visible(False)
        try:
            for axis in ax1.axis.values():
                axis.major_ticklabels.set_visible(False)
        except AttributeError:
            pass

        ax_rgb.append(ax1)

    fig = ax.get_figure()
    for ax1 in ax_rgb:
        fig.add_axes(ax1)

    return ax_rgb


class RGBAxes:
    """
    4-panel `~.Axes.imshow` (RGB, R, G, B).

    Layout::

        ┌───────────────┬─────┐
        │               │  R  │
        │               ├─────┤
        │      RGB      │  G  │
        │               ├─────┤
        │               │  B  │
        └───────────────┴─────┘

    Subclasses can override the ``_defaultAxesClass`` attribute.
    By default RGBAxes uses `.mpl_axes.Axes`.

    Attributes
    ----------
    RGB : ``_defaultAxesClass``
        The Axes object for the three-channel `~.Axes.imshow`.
    R : ``_defaultAxesClass``
        The Axes object for the red channel `~.Axes.imshow`.
    G : ``_defaultAxesClass``
        The Axes object for the green channel `~.Axes.imshow`.
    B : ``_defaultAxesClass``
        The Axes object for the blue channel `~.Axes.imshow`.
    """

    _defaultAxesClass = Axes

    def __init__(self, *args, pad=0, **kwargs):
        """
        Parameters
        ----------
        pad : float, default: 0
            Fraction of the Axes height to put as padding.
        axes_class : `~matplotlib.axes.Axes`
            Axes class to use. If not provided, ``_defaultAxesClass`` is used.
        *args
            Forwarded to *axes_class* init for the RGB Axes
        **kwargs
            Forwarded to *axes_class* init for the RGB, R, G, and B Axes
        """
        axes_class = kwargs.pop("axes_class", self._defaultAxesClass)
        self.RGB = ax = axes_class(*args, **kwargs)
        ax.get_figure().add_axes(ax)
        self.R, self.G, self.B = make_rgb_axes(
            ax, pad=pad, axes_class=axes_class, **kwargs)
        # Set the line color and ticks for the axes.
        for ax1 in [self.RGB, self.R, self.G, self.B]:
            if isinstance(ax1.axis, MethodType):
                ad = Axes.AxisDict(self)
                ad.update(
                    bottom=SimpleAxisArtist(ax1.xaxis, 1, ax1.spines["bottom"]),
                    top=SimpleAxisArtist(ax1.xaxis, 2, ax1.spines["top"]),
                    left=SimpleAxisArtist(ax1.yaxis, 1, ax1.spines["left"]),
                    right=SimpleAxisArtist(ax1.yaxis, 2, ax1.spines["right"]))
            else:
                ad = ax1.axis
            ad[:].line.set_color("w")
            ad[:].major_ticks.set_markeredgecolor("w")

    def imshow_rgb(self, r, g, b, **kwargs):
        """
        Create the four images {rgb, r, g, b}.

        Parameters
        ----------
        r, g, b : array-like
            The red, green, and blue arrays.
        **kwargs
            Forwarded to `~.Axes.imshow` calls for the four images.

        Returns
        -------
        rgb : `~matplotlib.image.AxesImage`
        r : `~matplotlib.image.AxesImage`
        g : `~matplotlib.image.AxesImage`
        b : `~matplotlib.image.AxesImage`
        """
        if not (r.shape == g.shape == b.shape):
            raise ValueError(
                f'Input shapes ({r.shape}, {g.shape}, {b.shape}) do not match')
        RGB = np.dstack([r, g, b])
        R = np.zeros_like(RGB)
        R[:, :, 0] = r
        G = np.zeros_like(RGB)
        G[:, :, 1] = g
        B = np.zeros_like(RGB)
        B[:, :, 2] = b
        im_rgb = self.RGB.imshow(RGB, **kwargs)
        im_r = self.R.imshow(R, **kwargs)
        im_g = self.G.imshow(G, **kwargs)
        im_b = self.B.imshow(B, **kwargs)
        return im_rgb, im_r, im_g, im_b

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\test_stem.py ===
import unittest
from contextlib import closing

from nltk import data
from nltk.stem.porter import PorterStemmer
from nltk.stem.snowball import SnowballStemmer


class SnowballTest(unittest.TestCase):
    def test_arabic(self):
        """
        this unit testing for test the snowball arabic light stemmer
        this stemmer deals with prefixes and suffixes
        """
        # Test where the ignore_stopwords=True.
        ar_stemmer = SnowballStemmer("arabic", True)
        assert ar_stemmer.stem("الْعَرَبِــــــيَّة") == "عرب"
        assert ar_stemmer.stem("العربية") == "عرب"
        assert ar_stemmer.stem("فقالوا") == "قال"
        assert ar_stemmer.stem("الطالبات") == "طالب"
        assert ar_stemmer.stem("فالطالبات") == "طالب"
        assert ar_stemmer.stem("والطالبات") == "طالب"
        assert ar_stemmer.stem("الطالبون") == "طالب"
        assert ar_stemmer.stem("اللذان") == "اللذان"
        assert ar_stemmer.stem("من") == "من"
        # Test where the ignore_stopwords=False.
        ar_stemmer = SnowballStemmer("arabic", False)
        assert ar_stemmer.stem("اللذان") == "اللذ"  # this is a stop word
        assert ar_stemmer.stem("الطالبات") == "طالب"
        assert ar_stemmer.stem("الكلمات") == "كلم"
        # test where create the arabic stemmer without given init value to ignore_stopwords
        ar_stemmer = SnowballStemmer("arabic")
        assert ar_stemmer.stem("الْعَرَبِــــــيَّة") == "عرب"
        assert ar_stemmer.stem("العربية") == "عرب"
        assert ar_stemmer.stem("فقالوا") == "قال"
        assert ar_stemmer.stem("الطالبات") == "طالب"
        assert ar_stemmer.stem("الكلمات") == "كلم"

    def test_russian(self):
        stemmer_russian = SnowballStemmer("russian")
        assert stemmer_russian.stem("авантненькая") == "авантненьк"

    def test_german(self):
        stemmer_german = SnowballStemmer("german")
        stemmer_german2 = SnowballStemmer("german", ignore_stopwords=True)

        assert stemmer_german.stem("Schr\xe4nke") == "schrank"
        assert stemmer_german2.stem("Schr\xe4nke") == "schrank"

        assert stemmer_german.stem("keinen") == "kein"
        assert stemmer_german2.stem("keinen") == "keinen"

    def test_spanish(self):
        stemmer = SnowballStemmer("spanish")

        assert stemmer.stem("Visionado") == "vision"

        # The word 'algue' was raising an IndexError
        assert stemmer.stem("algue") == "algu"

    def test_short_strings_bug(self):
        stemmer = SnowballStemmer("english")
        assert stemmer.stem("y's") == "y"


class PorterTest(unittest.TestCase):
    def _vocabulary(self):
        with closing(
            data.find("stemmers/porter_test/porter_vocabulary.txt").open(
                encoding="utf-8"
            )
        ) as fp:
            return fp.read().splitlines()

    def _test_against_expected_output(self, stemmer_mode, expected_stems):
        stemmer = PorterStemmer(mode=stemmer_mode)
        for word, true_stem in zip(self._vocabulary(), expected_stems):
            our_stem = stemmer.stem(word)
            assert (
                our_stem == true_stem
            ), "{} should stem to {} in {} mode but got {}".format(
                word,
                true_stem,
                stemmer_mode,
                our_stem,
            )

    def test_vocabulary_martin_mode(self):
        """Tests all words from the test vocabulary provided by M Porter

        The sample vocabulary and output were sourced from
        https://tartarus.org/martin/PorterStemmer/voc.txt and
        https://tartarus.org/martin/PorterStemmer/output.txt
        and are linked to from the Porter Stemmer algorithm's homepage
        at https://tartarus.org/martin/PorterStemmer/
        """
        with closing(
            data.find("stemmers/porter_test/porter_martin_output.txt").open(
                encoding="utf-8"
            )
        ) as fp:
            self._test_against_expected_output(
                PorterStemmer.MARTIN_EXTENSIONS, fp.read().splitlines()
            )

    def test_vocabulary_nltk_mode(self):
        with closing(
            data.find("stemmers/porter_test/porter_nltk_output.txt").open(
                encoding="utf-8"
            )
        ) as fp:
            self._test_against_expected_output(
                PorterStemmer.NLTK_EXTENSIONS, fp.read().splitlines()
            )

    def test_vocabulary_original_mode(self):
        # The list of stems for this test was generated by taking the
        # Martin-blessed stemmer from
        # https://tartarus.org/martin/PorterStemmer/c.txt
        # and removing all the --DEPARTURE-- sections from it and
        # running it against Martin's test vocabulary.

        with closing(
            data.find("stemmers/porter_test/porter_original_output.txt").open(
                encoding="utf-8"
            )
        ) as fp:
            self._test_against_expected_output(
                PorterStemmer.ORIGINAL_ALGORITHM, fp.read().splitlines()
            )

        self._test_against_expected_output(
            PorterStemmer.ORIGINAL_ALGORITHM,
            data.find("stemmers/porter_test/porter_original_output.txt")
            .open(encoding="utf-8")
            .read()
            .splitlines(),
        )

    def test_oed_bug(self):
        """Test for bug https://github.com/nltk/nltk/issues/1581

        Ensures that 'oed' can be stemmed without throwing an error.
        """
        assert PorterStemmer().stem("oed") == "o"

    def test_lowercase_option(self):
        """Test for improvement on https://github.com/nltk/nltk/issues/2507

        Ensures that stems are lowercased when `to_lowercase=True`
        """
        porter = PorterStemmer()
        assert porter.stem("On") == "on"
        assert porter.stem("I") == "i"
        assert porter.stem("I", to_lowercase=False) == "I"
        assert porter.stem("Github") == "github"
        assert porter.stem("Github", to_lowercase=False) == "Github"

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\cachecontrol\heuristics.py ===
# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import calendar
import time
from datetime import datetime, timedelta, timezone
from email.utils import formatdate, parsedate, parsedate_tz
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from pip._vendor.urllib3 import HTTPResponse

TIME_FMT = "%a, %d %b %Y %H:%M:%S GMT"


def expire_after(delta: timedelta, date: datetime | None = None) -> datetime:
    date = date or datetime.now(timezone.utc)
    return date + delta


def datetime_to_header(dt: datetime) -> str:
    return formatdate(calendar.timegm(dt.timetuple()))


class BaseHeuristic:
    def warning(self, response: HTTPResponse) -> str | None:
        """
        Return a valid 1xx warning header value describing the cache
        adjustments.

        The response is provided too allow warnings like 113
        http://tools.ietf.org/html/rfc7234#section-5.5.4 where we need
        to explicitly say response is over 24 hours old.
        """
        return '110 - "Response is Stale"'

    def update_headers(self, response: HTTPResponse) -> dict[str, str]:
        """Update the response headers with any new headers.

        NOTE: This SHOULD always include some Warning header to
              signify that the response was cached by the client, not
              by way of the provided headers.
        """
        return {}

    def apply(self, response: HTTPResponse) -> HTTPResponse:
        updated_headers = self.update_headers(response)

        if updated_headers:
            response.headers.update(updated_headers)
            warning_header_value = self.warning(response)
            if warning_header_value is not None:
                response.headers.update({"Warning": warning_header_value})

        return response


class OneDayCache(BaseHeuristic):
    """
    Cache the response by providing an expires 1 day in the
    future.
    """

    def update_headers(self, response: HTTPResponse) -> dict[str, str]:
        headers = {}

        if "expires" not in response.headers:
            date = parsedate(response.headers["date"])
            expires = expire_after(
                timedelta(days=1),
                date=datetime(*date[:6], tzinfo=timezone.utc),  # type: ignore[index,misc]
            )
            headers["expires"] = datetime_to_header(expires)
            headers["cache-control"] = "public"
        return headers


class ExpiresAfter(BaseHeuristic):
    """
    Cache **all** requests for a defined time period.
    """

    def __init__(self, **kw: Any) -> None:
        self.delta = timedelta(**kw)

    def update_headers(self, response: HTTPResponse) -> dict[str, str]:
        expires = expire_after(self.delta)
        return {"expires": datetime_to_header(expires), "cache-control": "public"}

    def warning(self, response: HTTPResponse) -> str | None:
        tmpl = "110 - Automatically cached for %s. Response might be stale"
        return tmpl % self.delta


class LastModified(BaseHeuristic):
    """
    If there is no Expires header already, fall back on Last-Modified
    using the heuristic from
    http://tools.ietf.org/html/rfc7234#section-4.2.2
    to calculate a reasonable value.

    Firefox also does something like this per
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching_FAQ
    http://lxr.mozilla.org/mozilla-release/source/netwerk/protocol/http/nsHttpResponseHead.cpp#397
    Unlike mozilla we limit this to 24-hr.
    """

    cacheable_by_default_statuses = {
        200,
        203,
        204,
        206,
        300,
        301,
        404,
        405,
        410,
        414,
        501,
    }

    def update_headers(self, resp: HTTPResponse) -> dict[str, str]:
        headers: Mapping[str, str] = resp.headers

        if "expires" in headers:
            return {}

        if "cache-control" in headers and headers["cache-control"] != "public":
            return {}

        if resp.status not in self.cacheable_by_default_statuses:
            return {}

        if "date" not in headers or "last-modified" not in headers:
            return {}

        time_tuple = parsedate_tz(headers["date"])
        assert time_tuple is not None
        date = calendar.timegm(time_tuple[:6])
        last_modified = parsedate(headers["last-modified"])
        if last_modified is None:
            return {}

        now = time.time()
        current_age = max(0, now - date)
        delta = date - calendar.timegm(last_modified)
        freshness_lifetime = max(0, min(delta / 10, 24 * 3600))
        if freshness_lifetime <= current_age:
            return {}

        expires = date + freshness_lifetime
        return {"expires": time.strftime(TIME_FMT, time.gmtime(expires))}

    def warning(self, resp: HTTPResponse) -> str | None:
        return None

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\requests\api.py ===
"""
requests.api
~~~~~~~~~~~~

This module implements the Requests API.

:copyright: (c) 2012 by Kenneth Reitz.
:license: Apache2, see LICENSE for more details.
"""

from . import sessions


def request(method, url, **kwargs):
    """Constructs and sends a :class:`Request <Request>`.

    :param method: method for the new :class:`Request` object: ``GET``, ``OPTIONS``, ``HEAD``, ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
    :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
    :param files: (optional) Dictionary of ``'name': file-like-objects`` (or ``{'name': file-tuple}``) for multipart encoding upload.
        ``file-tuple`` can be a 2-tuple ``('filename', fileobj)``, 3-tuple ``('filename', fileobj, 'content_type')``
        or a 4-tuple ``('filename', fileobj, 'content_type', custom_headers)``, where ``'content_type'`` is a string
        defining the content type of the given file and ``custom_headers`` a dict-like object containing additional headers
        to add for the file.
    :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
    :param timeout: (optional) How many seconds to wait for the server to send data
        before giving up, as a float, or a :ref:`(connect timeout, read
        timeout) <timeouts>` tuple.
    :type timeout: float or tuple
    :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection. Defaults to ``True``.
    :type allow_redirects: bool
    :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
    :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``.
    :param stream: (optional) if ``False``, the response content will be immediately downloaded.
    :param cert: (optional) if String, path to ssl client cert file (.pem). If Tuple, ('cert', 'key') pair.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response

    Usage::

      >>> import requests
      >>> req = requests.request('GET', 'https://httpbin.org/get')
      >>> req
      <Response [200]>
    """

    # By using the 'with' statement we are sure the session is closed, thus we
    # avoid leaving sockets open which can trigger a ResourceWarning in some
    # cases, and look like a memory leak in others.
    with sessions.Session() as session:
        return session.request(method=method, url=url, **kwargs)


def get(url, params=None, **kwargs):
    r"""Sends a GET request.

    :param url: URL for the new :class:`Request` object.
    :param params: (optional) Dictionary, list of tuples or bytes to send
        in the query string for the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("get", url, params=params, **kwargs)


def options(url, **kwargs):
    r"""Sends an OPTIONS request.

    :param url: URL for the new :class:`Request` object.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("options", url, **kwargs)


def head(url, **kwargs):
    r"""Sends a HEAD request.

    :param url: URL for the new :class:`Request` object.
    :param \*\*kwargs: Optional arguments that ``request`` takes. If
        `allow_redirects` is not provided, it will be set to `False` (as
        opposed to the default :meth:`request` behavior).
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    kwargs.setdefault("allow_redirects", False)
    return request("head", url, **kwargs)


def post(url, data=None, json=None, **kwargs):
    r"""Sends a POST request.

    :param url: URL for the new :class:`Request` object.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("post", url, data=data, json=json, **kwargs)


def put(url, data=None, **kwargs):
    r"""Sends a PUT request.

    :param url: URL for the new :class:`Request` object.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("put", url, data=data, **kwargs)


def patch(url, data=None, **kwargs):
    r"""Sends a PATCH request.

    :param url: URL for the new :class:`Request` object.
    :param data: (optional) Dictionary, list of tuples, bytes, or file-like
        object to send in the body of the :class:`Request`.
    :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("patch", url, data=data, **kwargs)


def delete(url, **kwargs):
    r"""Sends a DELETE request.

    :param url: URL for the new :class:`Request` object.
    :param \*\*kwargs: Optional arguments that ``request`` takes.
    :return: :class:`Response <Response>` object
    :rtype: requests.Response
    """

    return request("delete", url, **kwargs)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\formatters\__init__.py ===
"""
    pygments.formatters
    ~~~~~~~~~~~~~~~~~~~

    Pygments formatters.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import sys
import types
import fnmatch
from os.path import basename

from pip._vendor.pygments.formatters._mapping import FORMATTERS
from pip._vendor.pygments.plugin import find_plugin_formatters
from pip._vendor.pygments.util import ClassNotFound

__all__ = ['get_formatter_by_name', 'get_formatter_for_filename',
           'get_all_formatters', 'load_formatter_from_file'] + list(FORMATTERS)

_formatter_cache = {}  # classes by name
_pattern_cache = {}


def _fn_matches(fn, glob):
    """Return whether the supplied file name fn matches pattern filename."""
    if glob not in _pattern_cache:
        pattern = _pattern_cache[glob] = re.compile(fnmatch.translate(glob))
        return pattern.match(fn)
    return _pattern_cache[glob].match(fn)


def _load_formatters(module_name):
    """Load a formatter (and all others in the module too)."""
    mod = __import__(module_name, None, None, ['__all__'])
    for formatter_name in mod.__all__:
        cls = getattr(mod, formatter_name)
        _formatter_cache[cls.name] = cls


def get_all_formatters():
    """Return a generator for all formatter classes."""
    # NB: this returns formatter classes, not info like get_all_lexers().
    for info in FORMATTERS.values():
        if info[1] not in _formatter_cache:
            _load_formatters(info[0])
        yield _formatter_cache[info[1]]
    for _, formatter in find_plugin_formatters():
        yield formatter


def find_formatter_class(alias):
    """Lookup a formatter by alias.

    Returns None if not found.
    """
    for module_name, name, aliases, _, _ in FORMATTERS.values():
        if alias in aliases:
            if name not in _formatter_cache:
                _load_formatters(module_name)
            return _formatter_cache[name]
    for _, cls in find_plugin_formatters():
        if alias in cls.aliases:
            return cls


def get_formatter_by_name(_alias, **options):
    """
    Return an instance of a :class:`.Formatter` subclass that has `alias` in its
    aliases list. The formatter is given the `options` at its instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if no formatter with that
    alias is found.
    """
    cls = find_formatter_class(_alias)
    if cls is None:
        raise ClassNotFound(f"no formatter found for name {_alias!r}")
    return cls(**options)


def load_formatter_from_file(filename, formattername="CustomFormatter", **options):
    """
    Return a `Formatter` subclass instance loaded from the provided file, relative
    to the current directory.

    The file is expected to contain a Formatter class named ``formattername``
    (by default, CustomFormatter). Users should be very careful with the input, because
    this method is equivalent to running ``eval()`` on the input file. The formatter is
    given the `options` at its instantiation.

    :exc:`pygments.util.ClassNotFound` is raised if there are any errors loading
    the formatter.

    .. versionadded:: 2.2
    """
    try:
        # This empty dict will contain the namespace for the exec'd file
        custom_namespace = {}
        with open(filename, 'rb') as f:
            exec(f.read(), custom_namespace)
        # Retrieve the class `formattername` from that namespace
        if formattername not in custom_namespace:
            raise ClassNotFound(f'no valid {formattername} class found in {filename}')
        formatter_class = custom_namespace[formattername]
        # And finally instantiate it with the options
        return formatter_class(**options)
    except OSError as err:
        raise ClassNotFound(f'cannot read {filename}: {err}')
    except ClassNotFound:
        raise
    except Exception as err:
        raise ClassNotFound(f'error when loading custom formatter: {err}')


def get_formatter_for_filename(fn, **options):
    """
    Return a :class:`.Formatter` subclass instance that has a filename pattern
    matching `fn`. The formatter is given the `options` at its instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if no formatter for that filename
    is found.
    """
    fn = basename(fn)
    for modname, name, _, filenames, _ in FORMATTERS.values():
        for filename in filenames:
            if _fn_matches(fn, filename):
                if name not in _formatter_cache:
                    _load_formatters(modname)
                return _formatter_cache[name](**options)
    for _name, cls in find_plugin_formatters():
        for filename in cls.filenames:
            if _fn_matches(fn, filename):
                return cls(**options)
    raise ClassNotFound(f"no formatter found for file name {fn!r}")


class _automodule(types.ModuleType):
    """Automatically import formatters."""

    def __getattr__(self, name):
        info = FORMATTERS.get(name)
        if info:
            _load_formatters(info[0])
            cls = _formatter_cache[info[1]]
            setattr(self, name, cls)
            return cls
        raise AttributeError(name)


oldmod = sys.modules[__name__]
newmod = _automodule(__name__)
newmod.__dict__.update(oldmod.__dict__)
sys.modules[__name__] = newmod
del newmod.newmod, newmod.oldmod, newmod.sys, newmod.types