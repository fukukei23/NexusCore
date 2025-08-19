
# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_mixins.py ===
import numbers
import operator

import numpy as np
from numpy.testing import assert_, assert_equal, assert_raises

# NOTE: This class should be kept as an exact copy of the example from the
# docstring for NDArrayOperatorsMixin.

class ArrayLike(np.lib.mixins.NDArrayOperatorsMixin):
    def __init__(self, value):
        self.value = np.asarray(value)

    # One might also consider adding the built-in list type to this
    # list, to support operations like np.add(array_like, list)
    _HANDLED_TYPES = (np.ndarray, numbers.Number)

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        out = kwargs.get('out', ())
        for x in inputs + out:
            # Only support operations with instances of _HANDLED_TYPES.
            # Use ArrayLike instead of type(self) for isinstance to
            # allow subclasses that don't override __array_ufunc__ to
            # handle ArrayLike objects.
            if not isinstance(x, self._HANDLED_TYPES + (ArrayLike,)):
                return NotImplemented

        # Defer to the implementation of the ufunc on unwrapped values.
        inputs = tuple(x.value if isinstance(x, ArrayLike) else x
                       for x in inputs)
        if out:
            kwargs['out'] = tuple(
                x.value if isinstance(x, ArrayLike) else x
                for x in out)
        result = getattr(ufunc, method)(*inputs, **kwargs)

        if type(result) is tuple:
            # multiple return values
            return tuple(type(self)(x) for x in result)
        elif method == 'at':
            # no return value
            return None
        else:
            # one return value
            return type(self)(result)

    def __repr__(self):
        return f'{type(self).__name__}({self.value!r})'


def wrap_array_like(result):
    if type(result) is tuple:
        return tuple(ArrayLike(r) for r in result)
    else:
        return ArrayLike(result)


def _assert_equal_type_and_value(result, expected, err_msg=None):
    assert_equal(type(result), type(expected), err_msg=err_msg)
    if isinstance(result, tuple):
        assert_equal(len(result), len(expected), err_msg=err_msg)
        for result_item, expected_item in zip(result, expected):
            _assert_equal_type_and_value(result_item, expected_item, err_msg)
    else:
        assert_equal(result.value, expected.value, err_msg=err_msg)
        assert_equal(getattr(result.value, 'dtype', None),
                     getattr(expected.value, 'dtype', None), err_msg=err_msg)


_ALL_BINARY_OPERATORS = [
    operator.lt,
    operator.le,
    operator.eq,
    operator.ne,
    operator.gt,
    operator.ge,
    operator.add,
    operator.sub,
    operator.mul,
    operator.truediv,
    operator.floordiv,
    operator.mod,
    divmod,
    pow,
    operator.lshift,
    operator.rshift,
    operator.and_,
    operator.xor,
    operator.or_,
]


class TestNDArrayOperatorsMixin:

    def test_array_like_add(self):

        def check(result):
            _assert_equal_type_and_value(result, ArrayLike(0))

        check(ArrayLike(0) + 0)
        check(0 + ArrayLike(0))

        check(ArrayLike(0) + np.array(0))
        check(np.array(0) + ArrayLike(0))

        check(ArrayLike(np.array(0)) + 0)
        check(0 + ArrayLike(np.array(0)))

        check(ArrayLike(np.array(0)) + np.array(0))
        check(np.array(0) + ArrayLike(np.array(0)))

    def test_inplace(self):
        array_like = ArrayLike(np.array([0]))
        array_like += 1
        _assert_equal_type_and_value(array_like, ArrayLike(np.array([1])))

        array = np.array([0])
        array += ArrayLike(1)
        _assert_equal_type_and_value(array, ArrayLike(np.array([1])))

    def test_opt_out(self):

        class OptOut:
            """Object that opts out of __array_ufunc__."""
            __array_ufunc__ = None

            def __add__(self, other):
                return self

            def __radd__(self, other):
                return self

        array_like = ArrayLike(1)
        opt_out = OptOut()

        # supported operations
        assert_(array_like + opt_out is opt_out)
        assert_(opt_out + array_like is opt_out)

        # not supported
        with assert_raises(TypeError):
            # don't use the Python default, array_like = array_like + opt_out
            array_like += opt_out
        with assert_raises(TypeError):
            array_like - opt_out
        with assert_raises(TypeError):
            opt_out - array_like

    def test_subclass(self):

        class SubArrayLike(ArrayLike):
            """Should take precedence over ArrayLike."""

        x = ArrayLike(0)
        y = SubArrayLike(1)
        _assert_equal_type_and_value(x + y, y)
        _assert_equal_type_and_value(y + x, y)

    def test_object(self):
        x = ArrayLike(0)
        obj = object()
        with assert_raises(TypeError):
            x + obj
        with assert_raises(TypeError):
            obj + x
        with assert_raises(TypeError):
            x += obj

    def test_unary_methods(self):
        array = np.array([-1, 0, 1, 2])
        array_like = ArrayLike(array)
        for op in [operator.neg,
                   operator.pos,
                   abs,
                   operator.invert]:
            _assert_equal_type_and_value(op(array_like), ArrayLike(op(array)))

    def test_forward_binary_methods(self):
        array = np.array([-1, 0, 1, 2])
        array_like = ArrayLike(array)
        for op in _ALL_BINARY_OPERATORS:
            expected = wrap_array_like(op(array, 1))
            actual = op(array_like, 1)
            err_msg = f'failed for operator {op}'
            _assert_equal_type_and_value(expected, actual, err_msg=err_msg)

    def test_reflected_binary_methods(self):
        for op in _ALL_BINARY_OPERATORS:
            expected = wrap_array_like(op(2, 1))
            actual = op(2, ArrayLike(1))
            err_msg = f'failed for operator {op}'
            _assert_equal_type_and_value(expected, actual, err_msg=err_msg)

    def test_matmul(self):
        array = np.array([1, 2], dtype=np.float64)
        array_like = ArrayLike(array)
        expected = ArrayLike(np.float64(5))
        _assert_equal_type_and_value(expected, np.matmul(array_like, array))
        _assert_equal_type_and_value(
            expected, operator.matmul(array_like, array))
        _assert_equal_type_and_value(
            expected, operator.matmul(array, array_like))

    def test_ufunc_at(self):
        array = ArrayLike(np.array([1, 2, 3, 4]))
        assert_(np.negative.at(array, np.array([0, 1])) is None)
        _assert_equal_type_and_value(array, ArrayLike([-1, -2, 3, 4]))

    def test_ufunc_two_outputs(self):
        mantissa, exponent = np.frexp(2 ** -3)
        expected = (ArrayLike(mantissa), ArrayLike(exponent))
        _assert_equal_type_and_value(
            np.frexp(ArrayLike(2 ** -3)), expected)
        _assert_equal_type_and_value(
            np.frexp(ArrayLike(np.array(2 ** -3))), expected)

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32pdhutil.py ===
"""Utilities for the win32 Performance Data Helper module

Example:
  To get a single bit of data:
  >>> import win32pdhutil
  >>> win32pdhutil.GetPerformanceAttributes("Memory", "Available Bytes")
  6053888
  >>> win32pdhutil.FindPerformanceAttributesByName("python", counter="Virtual Bytes")
  [22278144]

  First example returns data which is not associated with any specific instance.

  The second example reads data for a specific instance - hence the list return -
  it would return one result for each instance of Python running.

  In general, it can be tricky finding exactly the "name" of the data you wish to query.
  Although you can use <om win32pdh.EnumObjectItems>(None,None,(eg)"Memory", -1) to do this,
  the easiest way is often to simply use PerfMon to find out the names.
"""

from __future__ import annotations

import time

import win32pdh

error = win32pdh.error  # Re-exported alias

# Handle some localization issues.
# see https://www.betaarchive.com/wiki/index.php?title=Microsoft_KB_Archive/287159
# Build a map of english_counter_name: counter_id
counter_english_map: dict[str, int] = {}


def find_pdh_counter_localized_name(english_name, machine_name=None):
    if not counter_english_map:
        import win32api
        import win32con

        counter_reg_value = win32api.RegQueryValueEx(
            win32con.HKEY_PERFORMANCE_DATA, "Counter 009"
        )
        counter_list = counter_reg_value[0]
        for i in range(0, len(counter_list) - 1, 2):
            try:
                counter_id = int(counter_list[i])
            except ValueError:
                continue
            counter_english_map[counter_list[i + 1].lower()] = counter_id
    return win32pdh.LookupPerfNameByIndex(
        machine_name, counter_english_map[english_name.lower()]
    )


def GetPerformanceAttributes(
    object, counter, instance=None, inum=-1, format=win32pdh.PDH_FMT_LONG, machine=None
):
    # NOTE: Many counters require 2 samples to give accurate results,
    # including "% Processor Time" (as by definition, at any instant, a
    # thread's CPU usage is either 0 or 100).  To read counters like this,
    # you should copy this function, but keep the counter open, and call
    # CollectQueryData() each time you need to know.
    # See https://www.betaarchive.com/wiki/index.php?title=Microsoft_KB_Archive/262938
    # and https://web.archive.org/web/20040926105842/http://msdn.microsoft.com:80/library/en-us/dnperfmo/html/perfmonpt2.asp
    # My older explanation for this was that the "AddCounter" process forced
    # the CPU to 100%, but the above makes more sense :)
    path = win32pdh.MakeCounterPath((machine, object, instance, None, inum, counter))
    hq = win32pdh.OpenQuery()
    try:
        hc = win32pdh.AddCounter(hq, path)
        try:
            win32pdh.CollectQueryData(hq)
            type, val = win32pdh.GetFormattedCounterValue(hc, format)
            return val
        finally:
            win32pdh.RemoveCounter(hc)
    finally:
        win32pdh.CloseQuery(hq)


def FindPerformanceAttributesByName(
    instanceName,
    object=None,
    counter=None,
    format=win32pdh.PDH_FMT_LONG,
    machine=None,
    bRefresh=0,
):
    """Find performance attributes by (case insensitive) instance name.

    Given a process name, return a list with the requested attributes.
    Most useful for returning a tuple of PIDs given a process name.
    """
    if object is None:
        object = find_pdh_counter_localized_name("Process", machine)
    if counter is None:
        counter = find_pdh_counter_localized_name("ID Process", machine)
    if bRefresh:  # PDH docs say this is how you do a refresh.
        win32pdh.EnumObjects(None, machine, 0, 1)
    instanceName = instanceName.lower()
    items, instances = win32pdh.EnumObjectItems(None, None, object, -1)
    # Track multiple instances.
    instance_dict = {}
    for instance in instances:
        try:
            instance_dict[instance] += 1
        except KeyError:
            instance_dict[instance] = 0

    ret = []
    for instance, max_instances in instance_dict.items():
        for inum in range(max_instances + 1):
            if instance.lower() == instanceName:
                ret.append(
                    GetPerformanceAttributes(
                        object, counter, instance, inum, format, machine
                    )
                )
    return ret


def ShowAllProcesses():
    object = find_pdh_counter_localized_name("Process")
    items, instances = win32pdh.EnumObjectItems(
        None, None, object, win32pdh.PERF_DETAIL_WIZARD
    )
    # Need to track multiple instances of the same name.
    instance_dict = {}
    for instance in instances:
        try:
            instance_dict[instance] += 1
        except KeyError:
            instance_dict[instance] = 0

    # Bit of a hack to get useful info.
    items = [find_pdh_counter_localized_name("ID Process")] + items[:5]
    print("Process Name", ",".join(items))
    for instance, max_instances in instance_dict.items():
        for inum in range(max_instances + 1):
            hq = win32pdh.OpenQuery()
            hcs = []
            for item in items:
                path = win32pdh.MakeCounterPath(
                    (None, object, instance, None, inum, item)
                )
                hcs.append(win32pdh.AddCounter(hq, path))
            win32pdh.CollectQueryData(hq)
            # as per https://www.betaarchive.com/wiki/index.php?title=Microsoft_KB_Archive/262938
            # some "%" based  counters need two collections
            time.sleep(0.01)
            win32pdh.CollectQueryData(hq)
            print("%-15s\t" % (instance[:15]), end=" ")
            for hc in hcs:
                type, val = win32pdh.GetFormattedCounterValue(hc, win32pdh.PDH_FMT_LONG)
                print("%5d" % (val), end=" ")
                win32pdh.RemoveCounter(hc)
            print()
            win32pdh.CloseQuery(hq)


# NOTE: This BrowseCallback doesn't seem to work on Vista for markh.
# XXX - look at why!?
# Some counters on Vista require elevation, and callback would previously
# clear exceptions without printing them.
def BrowseCallBackDemo(counters):
    ## BrowseCounters can now return multiple counter paths
    for counter in counters:
        (
            machine,
            object,
            instance,
            parentInstance,
            index,
            counterName,
        ) = win32pdh.ParseCounterPath(counter)

        result = GetPerformanceAttributes(
            object, counterName, instance, index, win32pdh.PDH_FMT_DOUBLE, machine
        )
        print("Value of '%s' is" % counter, result)
        print(
            "Added '%s' on object '%s' (machine %s), instance %s(%d)-parent of %s"
            % (counterName, object, machine, instance, index, parentInstance)
        )
    return 0


def browse(
    callback=BrowseCallBackDemo,
    title="Python Browser",
    level=win32pdh.PERF_DETAIL_WIZARD,
):
    win32pdh.BrowseCounters(None, 0, callback, level, title, ReturnMultiple=True)


if __name__ == "__main__":
    ShowAllProcesses()
    # Show how to get a couple of attributes by name.
    counter = find_pdh_counter_localized_name("Virtual Bytes")
    print(
        "Virtual Bytes = ", FindPerformanceAttributesByName("python", counter=counter)
    )
    print(
        "Available Bytes = ",
        GetPerformanceAttributes(
            find_pdh_counter_localized_name("Memory"),
            find_pdh_counter_localized_name("Available Bytes"),
        ),
    )
    # And a browser.
    print("Browsing for counters...")
    browse()

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_ufunclike_impl.py ===
"""
Module of functions that are like ufuncs in acting on arrays and optionally
storing results in an output array.

"""
__all__ = ['fix', 'isneginf', 'isposinf']

import numpy._core.numeric as nx
from numpy._core.overrides import array_function_dispatch


def _dispatcher(x, out=None):
    return (x, out)


@array_function_dispatch(_dispatcher, verify=False, module='numpy')
def fix(x, out=None):
    """
    Round to nearest integer towards zero.

    Round an array of floats element-wise to nearest integer towards zero.
    The rounded values have the same data-type as the input.

    Parameters
    ----------
    x : array_like
        An array to be rounded
    out : ndarray, optional
        A location into which the result is stored. If provided, it must have
        a shape that the input broadcasts to. If not provided or None, a
        freshly-allocated array is returned.

    Returns
    -------
    out : ndarray of floats
        An array with the same dimensions and data-type as the input.
        If second argument is not supplied then a new array is returned
        with the rounded values.

        If a second argument is supplied the result is stored there.
        The return value ``out`` is then a reference to that array.

    See Also
    --------
    rint, trunc, floor, ceil
    around : Round to given number of decimals

    Examples
    --------
    >>> import numpy as np
    >>> np.fix(3.14)
    3.0
    >>> np.fix(3)
    3
    >>> np.fix([2.1, 2.9, -2.1, -2.9])
    array([ 2.,  2., -2., -2.])

    """
    # promote back to an array if flattened
    res = nx.asanyarray(nx.ceil(x, out=out))
    res = nx.floor(x, out=res, where=nx.greater_equal(x, 0))

    # when no out argument is passed and no subclasses are involved, flatten
    # scalars
    if out is None and type(res) is nx.ndarray:
        res = res[()]
    return res


@array_function_dispatch(_dispatcher, verify=False, module='numpy')
def isposinf(x, out=None):
    """
    Test element-wise for positive infinity, return result as bool array.

    Parameters
    ----------
    x : array_like
        The input array.
    out : array_like, optional
        A location into which the result is stored. If provided, it must have a
        shape that the input broadcasts to. If not provided or None, a
        freshly-allocated boolean array is returned.

    Returns
    -------
    out : ndarray
        A boolean array with the same dimensions as the input.
        If second argument is not supplied then a boolean array is returned
        with values True where the corresponding element of the input is
        positive infinity and values False where the element of the input is
        not positive infinity.

        If a second argument is supplied the result is stored there. If the
        type of that array is a numeric type the result is represented as zeros
        and ones, if the type is boolean then as False and True.
        The return value `out` is then a reference to that array.

    See Also
    --------
    isinf, isneginf, isfinite, isnan

    Notes
    -----
    NumPy uses the IEEE Standard for Binary Floating-Point for Arithmetic
    (IEEE 754).

    Errors result if the second argument is also supplied when x is a scalar
    input, if first and second arguments have different shapes, or if the
    first argument has complex values

    Examples
    --------
    >>> import numpy as np
    >>> np.isposinf(np.inf)
    True
    >>> np.isposinf(-np.inf)
    False
    >>> np.isposinf([-np.inf, 0., np.inf])
    array([False, False,  True])

    >>> x = np.array([-np.inf, 0., np.inf])
    >>> y = np.array([2, 2, 2])
    >>> np.isposinf(x, y)
    array([0, 0, 1])
    >>> y
    array([0, 0, 1])

    """
    is_inf = nx.isinf(x)
    try:
        signbit = ~nx.signbit(x)
    except TypeError as e:
        dtype = nx.asanyarray(x).dtype
        raise TypeError(f'This operation is not supported for {dtype} values '
                        'because it would be ambiguous.') from e
    else:
        return nx.logical_and(is_inf, signbit, out)


@array_function_dispatch(_dispatcher, verify=False, module='numpy')
def isneginf(x, out=None):
    """
    Test element-wise for negative infinity, return result as bool array.

    Parameters
    ----------
    x : array_like
        The input array.
    out : array_like, optional
        A location into which the result is stored. If provided, it must have a
        shape that the input broadcasts to. If not provided or None, a
        freshly-allocated boolean array is returned.

    Returns
    -------
    out : ndarray
        A boolean array with the same dimensions as the input.
        If second argument is not supplied then a numpy boolean array is
        returned with values True where the corresponding element of the
        input is negative infinity and values False where the element of
        the input is not negative infinity.

        If a second argument is supplied the result is stored there. If the
        type of that array is a numeric type the result is represented as
        zeros and ones, if the type is boolean then as False and True. The
        return value `out` is then a reference to that array.

    See Also
    --------
    isinf, isposinf, isnan, isfinite

    Notes
    -----
    NumPy uses the IEEE Standard for Binary Floating-Point for Arithmetic
    (IEEE 754).

    Errors result if the second argument is also supplied when x is a scalar
    input, if first and second arguments have different shapes, or if the
    first argument has complex values.

    Examples
    --------
    >>> import numpy as np
    >>> np.isneginf(-np.inf)
    True
    >>> np.isneginf(np.inf)
    False
    >>> np.isneginf([-np.inf, 0., np.inf])
    array([ True, False, False])

    >>> x = np.array([-np.inf, 0., np.inf])
    >>> y = np.array([2, 2, 2])
    >>> np.isneginf(x, y)
    array([1, 0, 0])
    >>> y
    array([1, 0, 0])

    """
    is_inf = nx.isinf(x)
    try:
        signbit = nx.signbit(x)
    except TypeError as e:
        dtype = nx.asanyarray(x).dtype
        raise TypeError(f'This operation is not supported for {dtype} values '
                        'because it would be ambiguous.') from e
    else:
        return nx.logical_and(is_inf, signbit, out)

# === NexusCore/openenv\Lib\site-packages\litellm\router.py ===
# +-----------------------------------------------+
# |                                               |
# |           Give Feedback / Get Help            |
# | https://github.com/BerriAI/litellm/issues/new |
# |                                               |
# +-----------------------------------------------+
#
#  Thank you ! We ❤️ you! - Krrish & Ishaan

import asyncio
import copy
import enum
import hashlib
import inspect
import json
import logging
import threading
import time
import traceback
import uuid
from collections import defaultdict
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
)

import httpx
import openai
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing_extensions import overload

import litellm
import litellm.litellm_core_utils
import litellm.litellm_core_utils.exception_mapping_utils
from litellm import get_secret_str
from litellm._logging import verbose_router_logger
from litellm.caching.caching import (
    DualCache,
    InMemoryCache,
    RedisCache,
    RedisClusterCache,
)
from litellm.constants import DEFAULT_MAX_LRU_CACHE_SIZE
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.asyncify import run_async_function
from litellm.litellm_core_utils.core_helpers import _get_parent_otel_span_from_kwargs
from litellm.litellm_core_utils.credential_accessor import CredentialAccessor
from litellm.litellm_core_utils.dd_tracing import tracer
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLogging
from litellm.router_strategy.budget_limiter import RouterBudgetLimiting
from litellm.router_strategy.least_busy import LeastBusyLoggingHandler
from litellm.router_strategy.lowest_cost import LowestCostLoggingHandler
from litellm.router_strategy.lowest_latency import LowestLatencyLoggingHandler
from litellm.router_strategy.lowest_tpm_rpm import LowestTPMLoggingHandler
from litellm.router_strategy.lowest_tpm_rpm_v2 import LowestTPMLoggingHandler_v2
from litellm.router_strategy.simple_shuffle import simple_shuffle
from litellm.router_strategy.tag_based_routing import get_deployments_for_tag
from litellm.router_utils.add_retry_fallback_headers import (
    add_fallback_headers_to_response,
    add_retry_headers_to_response,
)
from litellm.router_utils.batch_utils import (
    _get_router_metadata_variable_name,
    replace_model_in_jsonl,
    should_replace_model_in_jsonl,
)
from litellm.router_utils.client_initalization_utils import InitalizeCachedClient
from litellm.router_utils.clientside_credential_handler import (
    get_dynamic_litellm_params,
    is_clientside_credential,
)
from litellm.router_utils.cooldown_cache import CooldownCache
from litellm.router_utils.cooldown_handlers import (
    DEFAULT_COOLDOWN_TIME_SECONDS,
    _async_get_cooldown_deployments,
    _async_get_cooldown_deployments_with_debug_info,
    _get_cooldown_deployments,
    _set_cooldown_deployments,
)
from litellm.router_utils.fallback_event_handlers import (
    _check_non_standard_fallback_format,
    get_fallback_model_group,
    run_async_fallback,
)
from litellm.router_utils.get_retry_from_policy import (
    get_num_retries_from_retry_policy as _get_num_retries_from_retry_policy,
)
from litellm.router_utils.handle_error import (
    async_raise_no_deployment_exception,
    send_llm_exception_alert,
)
from litellm.router_utils.pre_call_checks.prompt_caching_deployment_check import (
    PromptCachingDeploymentCheck,
)
from litellm.router_utils.pre_call_checks.responses_api_deployment_check import (
    ResponsesApiDeploymentCheck,
)
from litellm.router_utils.router_callbacks.track_deployment_metrics import (
    increment_deployment_failures_for_current_minute,
    increment_deployment_successes_for_current_minute,
)
from litellm.scheduler import FlowItem, Scheduler
from litellm.types.llms.openai import (
    AllMessageValues,
    FileTypes,
    OpenAIFileObject,
    OpenAIFilesPurpose,
)
from litellm.types.router import (
    CONFIGURABLE_CLIENTSIDE_AUTH_PARAMS,
    VALID_LITELLM_ENVIRONMENTS,
    AlertingConfig,
    AllowedFailsPolicy,
    AssistantsTypedDict,
    CredentialLiteLLMParams,
    CustomPricingLiteLLMParams,
    CustomRoutingStrategyBase,
    Deployment,
    DeploymentTypedDict,
    LiteLLM_Params,
    ModelGroupInfo,
    OptionalPreCallChecks,
    RetryPolicy,
    RouterCacheEnum,
    RouterGeneralSettings,
    RouterModelGroupAliasItem,
    RouterRateLimitError,
    RouterRateLimitErrorBasic,
    RoutingStrategy,
)
from litellm.types.services import ServiceTypes
from litellm.types.utils import GenericBudgetConfigType, LiteLLMBatch
from litellm.types.utils import ModelInfo
from litellm.types.utils import ModelInfo as ModelMapInfo
from litellm.types.utils import StandardLoggingPayload
from litellm.utils import (
    CustomStreamWrapper,
    EmbeddingResponse,
    ModelResponse,
    Rules,
    function_setup,
    get_llm_provider,
    get_non_default_completion_params,
    get_secret,
    get_utc_datetime,
    is_region_allowed,
)

from .router_utils.pattern_match_deployments import PatternMatchRouter

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = Union[_Span, Any]
else:
    Span = Any


class RoutingArgs(enum.Enum):
    ttl = 60  # 1min (RPM/TPM expire key)


class Router:
    model_names: List = []
    cache_responses: Optional[bool] = False
    default_cache_time_seconds: int = 1 * 60 * 60  # 1 hour
    tenacity = None
    leastbusy_logger: Optional[LeastBusyLoggingHandler] = None
    lowesttpm_logger: Optional[LowestTPMLoggingHandler] = None

    def __init__(  # noqa: PLR0915
        self,
        model_list: Optional[
            Union[List[DeploymentTypedDict], List[Dict[str, Any]]]
        ] = None,
        ## ASSISTANTS API ##
        assistants_config: Optional[AssistantsTypedDict] = None,
        ## CACHING ##
        redis_url: Optional[str] = None,
        redis_host: Optional[str] = None,
        redis_port: Optional[int] = None,
        redis_password: Optional[str] = None,
        cache_responses: Optional[bool] = False,
        cache_kwargs: dict = {},  # additional kwargs to pass to RedisCache (see caching.py)
        caching_groups: Optional[
            List[tuple]
        ] = None,  # if you want to cache across model groups
        client_ttl: int = 3600,  # ttl for cached clients - will re-initialize after this time in seconds
        ## SCHEDULER ##
        polling_interval: Optional[float] = None,
        default_priority: Optional[int] = None,
        ## RELIABILITY ##
        num_retries: Optional[int] = None,
        max_fallbacks: Optional[
            int
        ] = None,  # max fallbacks to try before exiting the call. Defaults to 5.
        timeout: Optional[float] = None,
        stream_timeout: Optional[float] = None,
        default_litellm_params: Optional[
            dict
        ] = None,  # default params for Router.chat.completion.create
        default_max_parallel_requests: Optional[int] = None,
        set_verbose: bool = False,
        debug_level: Literal["DEBUG", "INFO"] = "INFO",
        default_fallbacks: Optional[
            List[str]
        ] = None,  # generic fallbacks, works across all deployments
        fallbacks: List = [],
        context_window_fallbacks: List = [],
        content_policy_fallbacks: List = [],
        model_group_alias: Optional[
            Dict[str, Union[str, RouterModelGroupAliasItem]]
        ] = {},
        enable_pre_call_checks: bool = False,
        enable_tag_filtering: bool = False,
        retry_after: int = 0,  # min time to wait before retrying a failed request
        retry_policy: Optional[
            Union[RetryPolicy, dict]
        ] = None,  # set custom retries for different exceptions
        model_group_retry_policy: Dict[
            str, RetryPolicy
        ] = {},  # set custom retry policies based on model group
        allowed_fails: Optional[
            int
        ] = None,  # Number of times a deployment can failbefore being added to cooldown
        allowed_fails_policy: Optional[
            AllowedFailsPolicy
        ] = None,  # set custom allowed fails policy
        cooldown_time: Optional[
            float
        ] = None,  # (seconds) time to cooldown a deployment after failure
        disable_cooldowns: Optional[bool] = None,
        routing_strategy: Literal[
            "simple-shuffle",
            "least-busy",
            "usage-based-routing",
            "latency-based-routing",
            "cost-based-routing",
            "usage-based-routing-v2",
        ] = "simple-shuffle",
        optional_pre_call_checks: Optional[OptionalPreCallChecks] = None,
        routing_strategy_args: dict = {},  # just for latency-based
        provider_budget_config: Optional[GenericBudgetConfigType] = None,
        alerting_config: Optional[AlertingConfig] = None,
        router_general_settings: Optional[
            RouterGeneralSettings
        ] = RouterGeneralSettings(),
        ignore_invalid_deployments: bool = False,
    ) -> None:
        """
        Initialize the Router class with the given parameters for caching, reliability, and routing strategy.

        Args:
            model_list (Optional[list]): List of models to be used. Defaults to None.
            redis_url (Optional[str]): URL of the Redis server. Defaults to None.
            redis_host (Optional[str]): Hostname of the Redis server. Defaults to None.
            redis_port (Optional[int]): Port of the Redis server. Defaults to None.
            redis_password (Optional[str]): Password of the Redis server. Defaults to None.
            cache_responses (Optional[bool]): Flag to enable caching of responses. Defaults to False.
            cache_kwargs (dict): Additional kwargs to pass to RedisCache. Defaults to {}.
            caching_groups (Optional[List[tuple]]): List of model groups for caching across model groups. Defaults to None.
            client_ttl (int): Time-to-live for cached clients in seconds. Defaults to 3600.
            polling_interval: (Optional[float]): frequency of polling queue. Only for '.scheduler_acompletion()'. Default is 3ms.
            default_priority: (Optional[int]): the default priority for a request. Only for '.scheduler_acompletion()'. Default is None.
            num_retries (Optional[int]): Number of retries for failed requests. Defaults to 2.
            timeout (Optional[float]): Timeout for requests. Defaults to None.
            default_litellm_params (dict): Default parameters for Router.chat.completion.create. Defaults to {}.
            set_verbose (bool): Flag to set verbose mode. Defaults to False.
            debug_level (Literal["DEBUG", "INFO"]): Debug level for logging. Defaults to "INFO".
            fallbacks (List): List of fallback options. Defaults to [].
            context_window_fallbacks (List): List of context window fallback options. Defaults to [].
            enable_pre_call_checks (boolean): Filter out deployments which are outside context window limits for a given prompt
            model_group_alias (Optional[dict]): Alias for model groups. Defaults to {}.
            retry_after (int): Minimum time to wait before retrying a failed request. Defaults to 0.
            allowed_fails (Optional[int]): Number of allowed fails before adding to cooldown. Defaults to None.
            cooldown_time (float): Time to cooldown a deployment after failure in seconds. Defaults to 1.
            routing_strategy (Literal["simple-shuffle", "least-busy", "usage-based-routing", "latency-based-routing", "cost-based-routing"]): Routing strategy. Defaults to "simple-shuffle".
            routing_strategy_args (dict): Additional args for latency-based routing. Defaults to {}.
            alerting_config (AlertingConfig): Slack alerting configuration. Defaults to None.
            provider_budget_config (ProviderBudgetConfig): Provider budget configuration. Use this to set llm_provider budget limits. example $100/day to OpenAI, $100/day to Azure, etc. Defaults to None.
            ignore_invalid_deployments (bool): Ignores invalid deployments, and continues with other deployments. Default is to raise an error.
        Returns:
            Router: An instance of the litellm.Router class.

        Example Usage:
        ```python
        from litellm import Router
        model_list = [
        {
            "model_name": "azure-gpt-3.5-turbo", # model alias
            "litellm_params": { # params for litellm completion/embedding call
                "model": "azure/<your-deployment-name-1>",
                "api_key": <your-api-key>,
                "api_version": <your-api-version>,
                "api_base": <your-api-base>
            },
        },
        {
            "model_name": "azure-gpt-3.5-turbo", # model alias
            "litellm_params": { # params for litellm completion/embedding call
                "model": "azure/<your-deployment-name-2>",
                "api_key": <your-api-key>,
                "api_version": <your-api-version>,
                "api_base": <your-api-base>
            },
        },
        {
            "model_name": "openai-gpt-3.5-turbo", # model alias
            "litellm_params": { # params for litellm completion/embedding call
                "model": "gpt-3.5-turbo",
                "api_key": <your-api-key>,
            },
        ]

        router = Router(model_list=model_list, fallbacks=[{"azure-gpt-3.5-turbo": "openai-gpt-3.5-turbo"}])
        ```
        """

        from litellm._service_logger import ServiceLogging

        self.set_verbose = set_verbose
        self.ignore_invalid_deployments = ignore_invalid_deployments
        self.debug_level = debug_level
        self.enable_pre_call_checks = enable_pre_call_checks
        self.enable_tag_filtering = enable_tag_filtering
        litellm.suppress_debug_info = True  # prevents 'Give Feedback/Get help' message from being emitted on Router - Relevant Issue: https://github.com/BerriAI/litellm/issues/5942
        if self.set_verbose is True:
            if debug_level == "INFO":
                verbose_router_logger.setLevel(logging.INFO)
            elif debug_level == "DEBUG":
                verbose_router_logger.setLevel(logging.DEBUG)
        self.router_general_settings: RouterGeneralSettings = (
            router_general_settings or RouterGeneralSettings()
        )

        self.assistants_config = assistants_config
        self.deployment_names: List = (
            []
        )  # names of models under litellm_params. ex. azure/chatgpt-v-2
        self.deployment_latency_map = {}
        ### CACHING ###
        cache_type: Literal["local", "redis", "redis-semantic", "s3", "disk"] = (
            "local"  # default to an in-memory cache
        )
        redis_cache = None
        cache_config: Dict[str, Any] = {}

        self.client_ttl = client_ttl
        if redis_url is not None or (redis_host is not None and redis_port is not None):
            cache_type = "redis"

            if redis_url is not None:
                cache_config["url"] = redis_url

            if redis_host is not None:
                cache_config["host"] = redis_host

            if redis_port is not None:
                cache_config["port"] = str(redis_port)  # type: ignore

            if redis_password is not None:
                cache_config["password"] = redis_password

            # Add additional key-value pairs from cache_kwargs
            cache_config.update(cache_kwargs)
            redis_cache = self._create_redis_cache(cache_config)

        if cache_responses:
            if litellm.cache is None:
                # the cache can be initialized on the proxy server. We should not overwrite it
                litellm.cache = litellm.Cache(type=cache_type, **cache_config)  # type: ignore
            self.cache_responses = cache_responses
        self.cache = DualCache(
            redis_cache=redis_cache, in_memory_cache=InMemoryCache()
        )  # use a dual cache (Redis+In-Memory) for tracking cooldowns, usage, etc.

        ### SCHEDULER ###
        self.scheduler = Scheduler(
            polling_interval=polling_interval, redis_cache=redis_cache
        )
        self.default_priority = default_priority
        self.default_deployment = None  # use this to track the users default deployment, when they want to use model = *
        self.default_max_parallel_requests = default_max_parallel_requests
        self.provider_default_deployment_ids: List[str] = []
        self.pattern_router = PatternMatchRouter()

        if model_list is not None:
            model_list = copy.deepcopy(model_list)
            self.set_model_list(model_list)
            self.healthy_deployments: List = self.model_list  # type: ignore
            for m in model_list:
                if "model" in m["litellm_params"]:
                    self.deployment_latency_map[m["litellm_params"]["model"]] = 0
        else:
            self.model_list: List = (
                []
            )  # initialize an empty list - to allow _add_deployment and delete_deployment to work

        if allowed_fails is not None:
            self.allowed_fails = allowed_fails
        else:
            self.allowed_fails = litellm.allowed_fails
        self.cooldown_time = cooldown_time or DEFAULT_COOLDOWN_TIME_SECONDS
        self.cooldown_cache = CooldownCache(
            cache=self.cache, default_cooldown_time=self.cooldown_time
        )
        self.disable_cooldowns = disable_cooldowns
        self.failed_calls = (
            InMemoryCache()
        )  # cache to track failed call per deployment, if num failed calls within 1 minute > allowed fails, then add it to cooldown

        if num_retries is not None:
            self.num_retries = num_retries
        elif litellm.num_retries is not None:
            self.num_retries = litellm.num_retries
        else:
            self.num_retries = openai.DEFAULT_MAX_RETRIES

        if max_fallbacks is not None:
            self.max_fallbacks = max_fallbacks
        elif litellm.max_fallbacks is not None:
            self.max_fallbacks = litellm.max_fallbacks
        else:
            self.max_fallbacks = litellm.ROUTER_MAX_FALLBACKS

        self.timeout = timeout or litellm.request_timeout
        self.stream_timeout = stream_timeout

        self.retry_after = retry_after
        self.routing_strategy = routing_strategy

        ## SETTING FALLBACKS ##
        ### validate if it's set + in correct format
        _fallbacks = fallbacks or litellm.fallbacks

        self.validate_fallbacks(fallback_param=_fallbacks)
        ### set fallbacks
        self.fallbacks = _fallbacks

        if default_fallbacks is not None or litellm.default_fallbacks is not None:
            _fallbacks = default_fallbacks or litellm.default_fallbacks
            if self.fallbacks is not None:
                self.fallbacks.append({"*": _fallbacks})
            else:
                self.fallbacks = [{"*": _fallbacks}]

        self.context_window_fallbacks = (
            context_window_fallbacks or litellm.context_window_fallbacks
        )

        _content_policy_fallbacks = (
            content_policy_fallbacks or litellm.content_policy_fallbacks
        )
        self.validate_fallbacks(fallback_param=_content_policy_fallbacks)
        self.content_policy_fallbacks = _content_policy_fallbacks
        self.total_calls: defaultdict = defaultdict(
            int
        )  # dict to store total calls made to each model
        self.fail_calls: defaultdict = defaultdict(
            int
        )  # dict to store fail_calls made to each model
        self.success_calls: defaultdict = defaultdict(
            int
        )  # dict to store success_calls  made to each model
        self.previous_models: List = (
            []
        )  # list to store failed calls (passed in as metadata to next call)
        self.model_group_alias: Dict[str, Union[str, RouterModelGroupAliasItem]] = (
            model_group_alias or {}
        )  # dict to store aliases for router, ex. {"gpt-4": "gpt-3.5-turbo"}, all requests with gpt-4 -> get routed to gpt-3.5-turbo group

        # make Router.chat.completions.create compatible for openai.chat.completions.create
        default_litellm_params = default_litellm_params or {}
        self.chat = litellm.Chat(params=default_litellm_params, router_obj=self)

        # default litellm args
        self.default_litellm_params = default_litellm_params
        self.default_litellm_params.setdefault("timeout", timeout)
        self.default_litellm_params.setdefault("max_retries", 0)
        self.default_litellm_params.setdefault("metadata", {}).update(
            {"caching_groups": caching_groups}
        )

        self.deployment_stats: dict = {}  # used for debugging load balancing
        """
        deployment_stats = {
            "122999-2828282-277:
            {
                "model": "gpt-3",
                "api_base": "http://localhost:4000",
                "num_requests": 20,
                "avg_latency": 0.001,
                "num_failures": 0,
                "num_successes": 20
            }
        }
        """

        ### ROUTING SETUP ###
        self.routing_strategy_init(
            routing_strategy=routing_strategy,
            routing_strategy_args=routing_strategy_args,
        )
        self.access_groups = None
        ## USAGE TRACKING ##
        if isinstance(litellm._async_success_callback, list):
            litellm.logging_callback_manager.add_litellm_async_success_callback(
                self.deployment_callback_on_success
            )
        else:
            litellm.logging_callback_manager.add_litellm_async_success_callback(
                self.deployment_callback_on_success
            )
        if isinstance(litellm.success_callback, list):
            litellm.logging_callback_manager.add_litellm_success_callback(
                self.sync_deployment_callback_on_success
            )
        else:
            litellm.success_callback = [self.sync_deployment_callback_on_success]
        if isinstance(litellm._async_failure_callback, list):
            litellm.logging_callback_manager.add_litellm_async_failure_callback(
                self.async_deployment_callback_on_failure
            )
        else:
            litellm._async_failure_callback = [
                self.async_deployment_callback_on_failure
            ]
        ## COOLDOWNS ##
        if isinstance(litellm.failure_callback, list):
            litellm.logging_callback_manager.add_litellm_failure_callback(
                self.deployment_callback_on_failure
            )
        else:
            litellm.failure_callback = [self.deployment_callback_on_failure]
        verbose_router_logger.debug(
            f"Intialized router with Routing strategy: {self.routing_strategy}\n\n"
            f"Routing enable_pre_call_checks: {self.enable_pre_call_checks}\n\n"
            f"Routing fallbacks: {self.fallbacks}\n\n"
            f"Routing content fallbacks: {self.content_policy_fallbacks}\n\n"
            f"Routing context window fallbacks: {self.context_window_fallbacks}\n\n"
            f"Router Redis Caching={self.cache.redis_cache}\n"
        )
        self.service_logger_obj = ServiceLogging()
        self.routing_strategy_args = routing_strategy_args
        self.provider_budget_config = provider_budget_config
        self.router_budget_logger: Optional[RouterBudgetLimiting] = None
        if RouterBudgetLimiting.should_init_router_budget_limiter(
            model_list=model_list, provider_budget_config=self.provider_budget_config
        ):
            if optional_pre_call_checks is not None:
                optional_pre_call_checks.append("router_budget_limiting")
            else:
                optional_pre_call_checks = ["router_budget_limiting"]
        self.retry_policy: Optional[RetryPolicy] = None
        if retry_policy is not None:
            if isinstance(retry_policy, dict):
                self.retry_policy = RetryPolicy(**retry_policy)
            elif isinstance(retry_policy, RetryPolicy):
                self.retry_policy = retry_policy
            verbose_router_logger.info(
                "\033[32mRouter Custom Retry Policy Set:\n{}\033[0m".format(
                    self.retry_policy.model_dump(exclude_none=True)
                )
            )

        self.model_group_retry_policy: Optional[Dict[str, RetryPolicy]] = (
            model_group_retry_policy
        )

        self.allowed_fails_policy: Optional[AllowedFailsPolicy] = None
        if allowed_fails_policy is not None:
            if isinstance(allowed_fails_policy, dict):
                self.allowed_fails_policy = AllowedFailsPolicy(**allowed_fails_policy)
            elif isinstance(allowed_fails_policy, AllowedFailsPolicy):
                self.allowed_fails_policy = allowed_fails_policy

            verbose_router_logger.info(
                "\033[32mRouter Custom Allowed Fails Policy Set:\n{}\033[0m".format(
                    self.allowed_fails_policy.model_dump(exclude_none=True)
                )
            )

        self.alerting_config: Optional[AlertingConfig] = alerting_config

        if optional_pre_call_checks is not None:
            self.add_optional_pre_call_checks(optional_pre_call_checks)

        if self.alerting_config is not None:
            self._initialize_alerting()

        self.initialize_assistants_endpoint()
        self.initialize_router_endpoints()

    def discard(self):
        """
        Pseudo-destructor to be invoked to clean up global data structures when router is no longer used.
        For now, unhook router's callbacks from all lists
        """
        litellm.logging_callback_manager.remove_callback_from_list_by_object(
            litellm._async_success_callback, self
        )
        litellm.logging_callback_manager.remove_callback_from_list_by_object(
            litellm.success_callback, self
        )
        litellm.logging_callback_manager.remove_callback_from_list_by_object(
            litellm._async_failure_callback, self
        )
        litellm.logging_callback_manager.remove_callback_from_list_by_object(
            litellm.failure_callback, self
        )
        litellm.logging_callback_manager.remove_callback_from_list_by_object(
            litellm.input_callback, self
        )
        litellm.logging_callback_manager.remove_callback_from_list_by_object(
            litellm.service_callback, self
        )
        litellm.logging_callback_manager.remove_callback_from_list_by_object(
            litellm.callbacks, self
        )

    @staticmethod
    def _create_redis_cache(
        cache_config: Dict[str, Any],
    ) -> Union[RedisCache, RedisClusterCache]:
        """
        Initializes either a RedisCache or RedisClusterCache based on the cache_config.
        """
        if cache_config.get("startup_nodes"):
            return RedisClusterCache(**cache_config)
        else:
            return RedisCache(**cache_config)

    def _update_redis_cache(self, cache: RedisCache):
        """
        Update the redis cache for the router, if none set.

        Allows proxy user to just do
        ```yaml
        litellm_settings:
            cache: true
        ```
        and caching to just work.
        """
        if self.cache.redis_cache is None:
            self.cache.redis_cache = cache

    def routing_strategy_init(
        self, routing_strategy: Union[RoutingStrategy, str], routing_strategy_args: dict
    ):
        verbose_router_logger.info(f"Routing strategy: {routing_strategy}")
        if (
            routing_strategy == RoutingStrategy.LEAST_BUSY.value
            or routing_strategy == RoutingStrategy.LEAST_BUSY
        ):
            self.leastbusy_logger = LeastBusyLoggingHandler(
                router_cache=self.cache, model_list=self.model_list
            )
            ## add callback
            if isinstance(litellm.input_callback, list):
                litellm.input_callback.append(self.leastbusy_logger)  # type: ignore
            else:
                litellm.input_callback = [self.leastbusy_logger]  # type: ignore
            if isinstance(litellm.callbacks, list):
                litellm.logging_callback_manager.add_litellm_callback(self.leastbusy_logger)  # type: ignore
        elif (
            routing_strategy == RoutingStrategy.USAGE_BASED_ROUTING.value
            or routing_strategy == RoutingStrategy.USAGE_BASED_ROUTING
        ):
            self.lowesttpm_logger = LowestTPMLoggingHandler(
                router_cache=self.cache,
                model_list=self.model_list,
                routing_args=routing_strategy_args,
            )
            if isinstance(litellm.callbacks, list):
                litellm.logging_callback_manager.add_litellm_callback(self.lowesttpm_logger)  # type: ignore
        elif (
            routing_strategy == RoutingStrategy.USAGE_BASED_ROUTING_V2.value
            or routing_strategy == RoutingStrategy.USAGE_BASED_ROUTING_V2
        ):
            self.lowesttpm_logger_v2 = LowestTPMLoggingHandler_v2(
                router_cache=self.cache,
                model_list=self.model_list,
                routing_args=routing_strategy_args,
            )
            if isinstance(litellm.callbacks, list):
                litellm.logging_callback_manager.add_litellm_callback(self.lowesttpm_logger_v2)  # type: ignore
        elif (
            routing_strategy == RoutingStrategy.LATENCY_BASED.value
            or routing_strategy == RoutingStrategy.LATENCY_BASED
        ):
            self.lowestlatency_logger = LowestLatencyLoggingHandler(
                router_cache=self.cache,
                model_list=self.model_list,
                routing_args=routing_strategy_args,
            )
            if isinstance(litellm.callbacks, list):
                litellm.logging_callback_manager.add_litellm_callback(self.lowestlatency_logger)  # type: ignore
        elif (
            routing_strategy == RoutingStrategy.COST_BASED.value
            or routing_strategy == RoutingStrategy.COST_BASED
        ):
            self.lowestcost_logger = LowestCostLoggingHandler(
                router_cache=self.cache,
                model_list=self.model_list,
                routing_args={},
            )
            if isinstance(litellm.callbacks, list):
                litellm.logging_callback_manager.add_litellm_callback(self.lowestcost_logger)  # type: ignore
        else:
            pass

    def initialize_assistants_endpoint(self):
        ## INITIALIZE PASS THROUGH ASSISTANTS ENDPOINT ##
        self.acreate_assistants = self.factory_function(litellm.acreate_assistants)
        self.adelete_assistant = self.factory_function(litellm.adelete_assistant)
        self.aget_assistants = self.factory_function(litellm.aget_assistants)
        self.acreate_thread = self.factory_function(litellm.acreate_thread)
        self.aget_thread = self.factory_function(litellm.aget_thread)
        self.a_add_message = self.factory_function(litellm.a_add_message)
        self.aget_messages = self.factory_function(litellm.aget_messages)
        self.arun_thread = self.factory_function(litellm.arun_thread)

    def initialize_router_endpoints(self):
        self.amoderation = self.factory_function(
            litellm.amoderation, call_type="moderation"
        )
        self.aanthropic_messages = self.factory_function(
            litellm.anthropic_messages, call_type="anthropic_messages"
        )
        self.aresponses = self.factory_function(
            litellm.aresponses, call_type="aresponses"
        )
        self.afile_delete = self.factory_function(
            litellm.afile_delete, call_type="afile_delete"
        )
        self.afile_content = self.factory_function(
            litellm.afile_content, call_type="afile_content"
        )
        self.responses = self.factory_function(litellm.responses, call_type="responses")
        self.aget_responses = self.factory_function(
            litellm.aget_responses, call_type="aget_responses"
        )
        self.adelete_responses = self.factory_function(
            litellm.adelete_responses, call_type="adelete_responses"
        )
        self.alist_input_items = self.factory_function(
            litellm.alist_input_items, call_type="alist_input_items"
        )
        self._arealtime = self.factory_function(
            litellm._arealtime, call_type="_arealtime"
        )
        self.acreate_fine_tuning_job = self.factory_function(
            litellm.acreate_fine_tuning_job, call_type="acreate_fine_tuning_job"
        )
        self.acancel_fine_tuning_job = self.factory_function(
            litellm.acancel_fine_tuning_job, call_type="acancel_fine_tuning_job"
        )
        self.alist_fine_tuning_jobs = self.factory_function(
            litellm.alist_fine_tuning_jobs, call_type="alist_fine_tuning_jobs"
        )
        self.aretrieve_fine_tuning_job = self.factory_function(
            litellm.aretrieve_fine_tuning_job, call_type="aretrieve_fine_tuning_job"
        )
        self.afile_list = self.factory_function(
            litellm.afile_list, call_type="alist_files"
        )
        self.aimage_edit = self.factory_function(
            litellm.aimage_edit, call_type="aimage_edit"
        )
        self.allm_passthrough_route = self.factory_function(
            litellm.allm_passthrough_route, call_type="allm_passthrough_route"
        )

    def validate_fallbacks(self, fallback_param: Optional[List]):
        """
        Validate the fallbacks parameter.
        """
        if fallback_param is None:
            return
        for fallback_dict in fallback_param:
            if not isinstance(fallback_dict, dict):
                raise ValueError(f"Item '{fallback_dict}' is not a dictionary.")
            if len(fallback_dict) != 1:
                raise ValueError(
                    f"Dictionary '{fallback_dict}' must have exactly one key, but has {len(fallback_dict)} keys."
                )

    def add_optional_pre_call_checks(
        self, optional_pre_call_checks: Optional[OptionalPreCallChecks]
    ):
        if optional_pre_call_checks is not None:
            for pre_call_check in optional_pre_call_checks:
                _callback: Optional[CustomLogger] = None
                if pre_call_check == "prompt_caching":
                    _callback = PromptCachingDeploymentCheck(cache=self.cache)
                elif pre_call_check == "router_budget_limiting":
                    _callback = RouterBudgetLimiting(
                        dual_cache=self.cache,
                        provider_budget_config=self.provider_budget_config,
                        model_list=self.model_list,
                    )
                elif pre_call_check == "responses_api_deployment_check":
                    _callback = ResponsesApiDeploymentCheck()
                if _callback is not None:
                    litellm.logging_callback_manager.add_litellm_callback(_callback)

    def print_deployment(self, deployment: dict):
        """
        returns a copy of the deployment with the api key masked

        Only returns 2 characters of the api key and masks the rest with * (10 *).
        """
        try:
            _deployment_copy = copy.deepcopy(deployment)
            litellm_params: dict = _deployment_copy["litellm_params"]
            if "api_key" in litellm_params:
                litellm_params["api_key"] = litellm_params["api_key"][:2] + "*" * 10
            return _deployment_copy
        except Exception as e:
            verbose_router_logger.debug(
                f"Error occurred while printing deployment - {str(e)}"
            )
            raise e

    ### COMPLETION, EMBEDDING, IMG GENERATION FUNCTIONS

    def completion(
        self, model: str, messages: List[Dict[str, str]], **kwargs
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        """
        Example usage:
        response = router.completion(model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Hey, how's it going?"}]
        """
        try:
            verbose_router_logger.debug(f"router.completion(model={model},..)")
            kwargs["model"] = model
            kwargs["messages"] = messages
            kwargs["original_function"] = self._completion
            self._update_kwargs_before_fallbacks(model=model, kwargs=kwargs)

            response = self.function_with_fallbacks(**kwargs)
            return response
        except Exception as e:
            raise e

    def _completion(
        self, model: str, messages: List[Dict[str, str]], **kwargs
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        model_name = None
        try:
            # pick the one that is available (lowest TPM/RPM)
            deployment = self.get_available_deployment(
                model=model,
                messages=messages,
                specific_deployment=kwargs.pop("specific_deployment", None),
                request_kwargs=kwargs,
            )
            self._update_kwargs_with_deployment(deployment=deployment, kwargs=kwargs)

            data = deployment["litellm_params"].copy()
            model_name = data["model"]
            potential_model_client = self._get_client(
                deployment=deployment, kwargs=kwargs
            )
            # check if provided keys == client keys #
            dynamic_api_key = kwargs.get("api_key", None)
            if (
                dynamic_api_key is not None
                and potential_model_client is not None
                and dynamic_api_key != potential_model_client.api_key
            ):
                model_client = None
            else:
                model_client = potential_model_client

            ### DEPLOYMENT-SPECIFIC PRE-CALL CHECKS ### (e.g. update rpm pre-call. Raise error, if deployment over limit)
            ## only run if model group given, not model id
            if model not in self.get_model_ids():
                self.routing_strategy_pre_call_checks(deployment=deployment)

            response = litellm.completion(
                **{
                    **data,
                    "messages": messages,
                    "caching": self.cache_responses,
                    "client": model_client,
                    **kwargs,
                }
            )
            verbose_router_logger.info(
                f"litellm.completion(model={model_name})\033[32m 200 OK\033[0m"
            )

            ## CHECK CONTENT FILTER ERROR ##
            if isinstance(response, ModelResponse):
                _should_raise = self._should_raise_content_policy_error(
                    model=model, response=response, kwargs=kwargs
                )
                if _should_raise:
                    raise litellm.ContentPolicyViolationError(
                        message="Response output was blocked.",
                        model=model,
                        llm_provider="",
                    )

            return response
        except Exception as e:
            verbose_router_logger.info(
                f"litellm.completion(model={model_name})\033[31m Exception {str(e)}\033[0m"
            )
            raise e

    # fmt: off

    @overload
    async def acompletion(
        self, model: str, messages: List[AllMessageValues], stream: Literal[True], **kwargs
    ) -> CustomStreamWrapper: 
        ...

    @overload
    async def acompletion(
        self, model: str, messages: List[AllMessageValues], stream: Literal[False] = False, **kwargs
    ) -> ModelResponse: 
        ...

    @overload
    async def acompletion(
        self, model: str, messages: List[AllMessageValues], stream: Union[Literal[True], Literal[False]] = False, **kwargs
    ) -> Union[CustomStreamWrapper, ModelResponse]: 
        ...

    # fmt: on

    # The actual implementation of the function
    async def acompletion(
        self,
        model: str,
        messages: List[AllMessageValues],
        stream: bool = False,
        **kwargs,
    ):
        try:
            kwargs["model"] = model
            kwargs["messages"] = messages
            kwargs["stream"] = stream
            kwargs["original_function"] = self._acompletion

            self._update_kwargs_before_fallbacks(model=model, kwargs=kwargs)
            request_priority = kwargs.get("priority") or self.default_priority
            start_time = time.time()
            _is_prompt_management_model = self._is_prompt_management_model(model)

            if _is_prompt_management_model:
                return await self._prompt_management_factory(
                    model=model,
                    messages=messages,
                    kwargs=kwargs,
                )
            if request_priority is not None and isinstance(request_priority, int):
                response = await self.schedule_acompletion(**kwargs)
            else:
                response = await self.async_function_with_fallbacks(**kwargs)
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.ROUTER,
                    duration=_duration,
                    call_type="acompletion",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                )
            )

            return response
        except Exception as e:
            asyncio.create_task(
                send_llm_exception_alert(
                    litellm_router_instance=self,
                    request_kwargs=kwargs,
                    error_traceback_str=traceback.format_exc(),
                    original_exception=e,
                )
            )
            raise e

    async def _acompletion(
        self, model: str, messages: List[Dict[str, str]], **kwargs
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        """
        - Get an available deployment
        - call it with a semaphore over the call
        - semaphore specific to it's rpm
        - in the semaphore,  make a check against it's local rpm before running
        """
        model_name = None
        _timeout_debug_deployment_dict = (
            {}
        )  # this is a temporary dict to debug timeout issues
        try:
            verbose_router_logger.debug(
                f"Inside _acompletion()- model: {model}; kwargs: {kwargs}"
            )
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
            start_time = time.time()
            deployment = await self.async_get_available_deployment(
                model=model,
                messages=messages,
                specific_deployment=kwargs.pop("specific_deployment", None),
                request_kwargs=kwargs,
            )

            _timeout_debug_deployment_dict = deployment
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.ROUTER,
                    duration=_duration,
                    call_type="async_get_available_deployment",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                )
            )

            # debug how often this deployment picked

            self._track_deployment_metrics(
                deployment=deployment, parent_otel_span=parent_otel_span
            )
            self._update_kwargs_with_deployment(deployment=deployment, kwargs=kwargs)
            data = deployment["litellm_params"].copy()

            model_name = data["model"]

            model_client = self._get_async_openai_model_client(
                deployment=deployment,
                kwargs=kwargs,
            )
            self.total_calls[model_name] += 1

            _response = litellm.acompletion(
                **{
                    **data,
                    "messages": messages,
                    "caching": self.cache_responses,
                    "client": model_client,
                    **kwargs,
                }
            )

            logging_obj: Optional[LiteLLMLogging] = kwargs.get(
                "litellm_logging_obj", None
            )

            rpm_semaphore = self._get_client(
                deployment=deployment,
                kwargs=kwargs,
                client_type="max_parallel_requests",
            )
            if rpm_semaphore is not None and isinstance(
                rpm_semaphore, asyncio.Semaphore
            ):
                async with rpm_semaphore:
                    """
                    - Check rpm limits before making the call
                    - If allowed, increment the rpm limit (allows global value to be updated, concurrency-safe)
                    """
                    await self.async_routing_strategy_pre_call_checks(
                        deployment=deployment,
                        logging_obj=logging_obj,
                        parent_otel_span=parent_otel_span,
                    )
                    response = await _response
            else:
                await self.async_routing_strategy_pre_call_checks(
                    deployment=deployment,
                    logging_obj=logging_obj,
                    parent_otel_span=parent_otel_span,
                )

                response = await _response

            ## CHECK CONTENT FILTER ERROR ##
            if isinstance(response, ModelResponse):
                _should_raise = self._should_raise_content_policy_error(
                    model=model, response=response, kwargs=kwargs
                )
                if _should_raise:
                    raise litellm.ContentPolicyViolationError(
                        message="Response output was blocked.",
                        model=model,
                        llm_provider="",
                    )

            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"litellm.acompletion(model={model_name})\033[32m 200 OK\033[0m"
            )
            # debug how often this deployment picked
            self._track_deployment_metrics(
                deployment=deployment,
                response=response,
                parent_otel_span=parent_otel_span,
            )

            return response
        except litellm.Timeout as e:
            deployment_request_timeout_param = _timeout_debug_deployment_dict.get(
                "litellm_params", {}
            ).get("request_timeout", None)
            deployment_timeout_param = _timeout_debug_deployment_dict.get(
                "litellm_params", {}
            ).get("timeout", None)
            e.message += f"\n\nDeployment Info: request_timeout: {deployment_request_timeout_param}\ntimeout: {deployment_timeout_param}"
            raise e
        except Exception as e:
            verbose_router_logger.info(
                f"litellm.acompletion(model={model_name})\033[31m Exception {str(e)}\033[0m"
            )
            if model_name is not None:
                self.fail_calls[model_name] += 1
            raise e

    def _update_kwargs_before_fallbacks(
        self,
        model: str,
        kwargs: dict,
        metadata_variable_name: Optional[str] = "metadata",
    ) -> None:
        """
        Adds/updates to kwargs:
        - num_retries
        - litellm_trace_id
        - metadata
        """
        kwargs["num_retries"] = kwargs.get("num_retries", self.num_retries)
        kwargs.setdefault("litellm_trace_id", str(uuid.uuid4()))
        kwargs.setdefault(metadata_variable_name, {}).update({"model_group": model})

    def _update_kwargs_with_default_litellm_params(
        self, kwargs: dict, metadata_variable_name: Optional[str] = "metadata"
    ) -> None:
        """
        Adds default litellm params to kwargs, if set.

        Handles inserting this as either "metadata" or "litellm_metadata" depending on the metadata_variable_name
        """
        # 1) copy your defaults and pull out metadata
        defaults = self.default_litellm_params.copy()
        metadata_defaults = defaults.pop("metadata", {}) or {}

        # 2) add any non-metadata defaults that aren't already in kwargs
        for key, value in defaults.items():
            if value is None:
                continue
            kwargs.setdefault(key, value)

        # 3) merge in metadata, this handles inserting this as either "metadata" or "litellm_metadata"
        kwargs.setdefault(metadata_variable_name, {}).update(metadata_defaults)

    def _handle_clientside_credential(
        self, deployment: dict, kwargs: dict
    ) -> Deployment:
        """
        Handle clientside credential
        """
        model_info = deployment.get("model_info", {}).copy()
        litellm_params = deployment["litellm_params"].copy()
        dynamic_litellm_params = get_dynamic_litellm_params(
            litellm_params=litellm_params, request_kwargs=kwargs
        )
        metadata = kwargs.get("metadata", {})
        model_group = cast(str, metadata.get("model_group"))
        _model_id = self._generate_model_id(
            model_group=model_group, litellm_params=dynamic_litellm_params
        )
        original_model_id = model_info.get("id")
        model_info["id"] = _model_id
        model_info["original_model_id"] = original_model_id
        deployment_pydantic_obj = Deployment(
            model_name=model_group,
            litellm_params=LiteLLM_Params(**dynamic_litellm_params),
            model_info=model_info,
        )
        self.upsert_deployment(
            deployment=deployment_pydantic_obj
        )  # add new deployment to router
        return deployment_pydantic_obj

    def _update_kwargs_with_deployment(
        self,
        deployment: dict,
        kwargs: dict,
        function_name: Optional[str] = None,
    ) -> None:
        """
        2 jobs:
        - Adds selected deployment, model_info and api_base to kwargs["metadata"] (used for logging)
        - Adds default litellm params to kwargs, if set.
        """
        model_info = deployment.get("model_info", {}).copy()
        deployment_model_name = deployment["litellm_params"]["model"]
        deployment_api_base = deployment["litellm_params"].get("api_base")
        if is_clientside_credential(request_kwargs=kwargs):
            deployment_pydantic_obj = self._handle_clientside_credential(
                deployment=deployment, kwargs=kwargs
            )
            model_info = deployment_pydantic_obj.model_info.model_dump()
            deployment_model_name = deployment_pydantic_obj.litellm_params.model
            deployment_api_base = deployment_pydantic_obj.litellm_params.api_base

        metadata_variable_name = _get_router_metadata_variable_name(
            function_name=function_name,
        )

        kwargs.setdefault(metadata_variable_name, {}).update(
            {
                "deployment": deployment_model_name,
                "model_info": model_info,
                "api_base": deployment_api_base,
            }
        )
        kwargs["model_info"] = model_info

        kwargs["timeout"] = self._get_timeout(
            kwargs=kwargs, data=deployment["litellm_params"]
        )

        self._update_kwargs_with_default_litellm_params(
            kwargs=kwargs, metadata_variable_name=metadata_variable_name
        )

    def _get_async_openai_model_client(self, deployment: dict, kwargs: dict):
        """
        Helper to get AsyncOpenAI or AsyncAzureOpenAI client that was created for the deployment

        The same OpenAI client is re-used to optimize latency / performance in production

        If dynamic api key is provided:
            Do not re-use the client. Pass model_client=None. The OpenAI/ AzureOpenAI client will be recreated in the handler for the llm provider
        """
        potential_model_client = self._get_client(
            deployment=deployment, kwargs=kwargs, client_type="async"
        )

        # check if provided keys == client keys #
        dynamic_api_key = kwargs.get("api_key", None)
        if (
            dynamic_api_key is not None
            and potential_model_client is not None
            and dynamic_api_key != potential_model_client.api_key
        ):
            model_client = None
        else:
            model_client = potential_model_client

        return model_client

    def _get_stream_timeout(
        self, kwargs: dict, data: dict
    ) -> Optional[Union[float, int]]:
        """Helper to get stream timeout from kwargs or deployment params"""
        return (
            kwargs.get("stream_timeout", None)  # the params dynamically set by user
            or data.get(
                "stream_timeout", None
            )  # timeout set on litellm_params for this deployment
            or self.stream_timeout  # timeout set on router
            or self.default_litellm_params.get("stream_timeout", None)
        )

    def _get_non_stream_timeout(
        self, kwargs: dict, data: dict
    ) -> Optional[Union[float, int]]:
        """Helper to get non-stream timeout from kwargs or deployment params"""
        timeout = (
            kwargs.get("timeout", None)  # the params dynamically set by user
            or kwargs.get("request_timeout", None)  # the params dynamically set by user
            or data.get(
                "timeout", None
            )  # timeout set on litellm_params for this deployment
            or data.get(
                "request_timeout", None
            )  # timeout set on litellm_params for this deployment
            or self.timeout  # timeout set on router
            or self.default_litellm_params.get("timeout", None)
        )
        return timeout

    def _get_timeout(self, kwargs: dict, data: dict) -> Optional[Union[float, int]]:
        """Helper to get timeout from kwargs or deployment params"""
        timeout: Optional[Union[float, int]] = None
        if kwargs.get("stream", False):
            timeout = self._get_stream_timeout(kwargs=kwargs, data=data)
        if timeout is None:
            timeout = self._get_non_stream_timeout(
                kwargs=kwargs, data=data
            )  # default to this if no stream specific timeout set
        return timeout

    async def abatch_completion(
        self,
        models: List[str],
        messages: Union[List[Dict[str, str]], List[List[Dict[str, str]]]],
        **kwargs,
    ):
        """
        Async Batch Completion. Used for 2 scenarios:
        1. Batch Process 1 request to N models on litellm.Router. Pass messages as List[Dict[str, str]] to use this
        2. Batch Process N requests to M models on litellm.Router. Pass messages as List[List[Dict[str, str]]] to use this

        Example Request for 1 request to N models:
        ```
            response = await router.abatch_completion(
                models=["gpt-3.5-turbo", "groq-llama"],
                messages=[
                    {"role": "user", "content": "is litellm becoming a better product ?"}
                ],
                max_tokens=15,
            )
        ```


        Example Request for N requests to M models:
        ```
            response = await router.abatch_completion(
                models=["gpt-3.5-turbo", "groq-llama"],
                messages=[
                    [{"role": "user", "content": "is litellm becoming a better product ?"}],
                    [{"role": "user", "content": "who is this"}],
                ],
            )
        ```
        """
        ############## Helpers for async completion ##################

        async def _async_completion_no_exceptions(
            model: str, messages: List[AllMessageValues], **kwargs
        ):
            """
            Wrapper around self.async_completion that catches exceptions and returns them as a result
            """
            try:
                return await self.acompletion(model=model, messages=messages, **kwargs)
            except Exception as e:
                return e

        async def _async_completion_no_exceptions_return_idx(
            model: str,
            messages: List[AllMessageValues],
            idx: int,  # index of message this response corresponds to
            **kwargs,
        ):
            """
            Wrapper around self.async_completion that catches exceptions and returns them as a result
            """
            try:
                return (
                    await self.acompletion(model=model, messages=messages, **kwargs),
                    idx,
                )
            except Exception as e:
                return e, idx

        ############## Helpers for async completion ##################

        if isinstance(messages, list) and all(isinstance(m, dict) for m in messages):
            _tasks = []
            for model in models:
                # add each task but if the task fails
                _tasks.append(_async_completion_no_exceptions(model=model, messages=messages, **kwargs))  # type: ignore
            response = await asyncio.gather(*_tasks)
            return response
        elif isinstance(messages, list) and all(isinstance(m, list) for m in messages):
            _tasks = []
            for idx, message in enumerate(messages):
                for model in models:
                    # Request Number X, Model Number Y
                    _tasks.append(
                        _async_completion_no_exceptions_return_idx(
                            model=model, idx=idx, messages=message, **kwargs  # type: ignore
                        )
                    )
            responses = await asyncio.gather(*_tasks)
            final_responses: List[List[Any]] = [[] for _ in range(len(messages))]
            for response in responses:
                if isinstance(response, tuple):
                    final_responses[response[1]].append(response[0])
                else:
                    final_responses[0].append(response)
            return final_responses

    async def abatch_completion_one_model_multiple_requests(
        self, model: str, messages: List[List[AllMessageValues]], **kwargs
    ):
        """
        Async Batch Completion - Batch Process multiple Messages to one model_group on litellm.Router

        Use this for sending multiple requests to 1 model

        Args:
            model (List[str]): model group
            messages (List[List[Dict[str, str]]]): list of messages. Each element in the list is one request
            **kwargs: additional kwargs
        Usage:
            response = await self.abatch_completion_one_model_multiple_requests(
                model="gpt-3.5-turbo",
                messages=[
                    [{"role": "user", "content": "hello"}, {"role": "user", "content": "tell me something funny"}],
                    [{"role": "user", "content": "hello good mornign"}],
                ]
            )
        """

        async def _async_completion_no_exceptions(
            model: str, messages: List[AllMessageValues], **kwargs
        ):
            """
            Wrapper around self.async_completion that catches exceptions and returns them as a result
            """
            try:
                return await self.acompletion(model=model, messages=messages, **kwargs)
            except Exception as e:
                return e

        _tasks = []
        for message_request in messages:
            # add each task but if the task fails
            _tasks.append(
                _async_completion_no_exceptions(
                    model=model, messages=message_request, **kwargs
                )
            )

        response = await asyncio.gather(*_tasks)
        return response

    # fmt: off

    @overload
    async def abatch_completion_fastest_response(
        self, model: str, messages: List[Dict[str, str]], stream: Literal[True], **kwargs
    ) -> CustomStreamWrapper:
        ...



    @overload
    async def abatch_completion_fastest_response(
        self, model: str, messages: List[Dict[str, str]], stream: Literal[False] = False, **kwargs
    ) -> ModelResponse:
        ...

    # fmt: on

    async def abatch_completion_fastest_response(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs,
    ):
        """
        model - List of comma-separated model names. E.g. model="gpt-4, gpt-3.5-turbo"

        Returns fastest response from list of model names. OpenAI-compatible endpoint.
        """
        models = [m.strip() for m in model.split(",")]

        async def _async_completion_no_exceptions(
            model: str, messages: List[Dict[str, str]], stream: bool, **kwargs: Any
        ) -> Union[ModelResponse, CustomStreamWrapper, Exception]:
            """
            Wrapper around self.acompletion that catches exceptions and returns them as a result
            """
            try:
                return await self.acompletion(model=model, messages=messages, stream=stream, **kwargs)  # type: ignore
            except asyncio.CancelledError:
                verbose_router_logger.debug(
                    "Received 'task.cancel'. Cancelling call w/ model={}.".format(model)
                )
                raise
            except Exception as e:
                return e

        pending_tasks = []  # type: ignore

        async def check_response(task: asyncio.Task):
            nonlocal pending_tasks
            try:
                result = await task
                if isinstance(result, (ModelResponse, CustomStreamWrapper)):
                    verbose_router_logger.debug(
                        "Received successful response. Cancelling other LLM API calls."
                    )
                    # If a desired response is received, cancel all other pending tasks
                    for t in pending_tasks:
                        t.cancel()
                    return result
            except Exception:
                # Ignore exceptions, let the loop handle them
                pass
            finally:
                # Remove the task from pending tasks if it finishes
                try:
                    pending_tasks.remove(task)
                except KeyError:
                    pass

        for model in models:
            task = asyncio.create_task(
                _async_completion_no_exceptions(
                    model=model, messages=messages, stream=stream, **kwargs
                )
            )
            pending_tasks.append(task)

        # Await the first task to complete successfully
        while pending_tasks:
            done, pending_tasks = await asyncio.wait(  # type: ignore
                pending_tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for completed_task in done:
                result = await check_response(completed_task)
                if result is not None:
                    # Return the first successful result
                    result._hidden_params["fastest_response_batch_completion"] = True
                    return result

        # If we exit the loop without returning, all tasks failed
        raise Exception("All tasks failed")

    ### SCHEDULER ###

    # fmt: off

    @overload
    async def schedule_acompletion(
        self, model: str, messages: List[AllMessageValues], priority: int, stream: Literal[False] = False, **kwargs
    ) -> ModelResponse: 
        ...
    
    @overload
    async def schedule_acompletion(
        self, model: str, messages: List[AllMessageValues], priority: int, stream: Literal[True], **kwargs
    ) -> CustomStreamWrapper: 
        ...

    # fmt: on

    async def schedule_acompletion(
        self,
        model: str,
        messages: List[AllMessageValues],
        priority: int,
        stream=False,
        **kwargs,
    ):
        parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
        ### FLOW ITEM ###
        _request_id = str(uuid.uuid4())
        item = FlowItem(
            priority=priority,  # 👈 SET PRIORITY FOR REQUEST
            request_id=_request_id,  # 👈 SET REQUEST ID
            model_name="gpt-3.5-turbo",  # 👈 SAME as 'Router'
        )
        ### [fin] ###

        ## ADDS REQUEST TO QUEUE ##
        await self.scheduler.add_request(request=item)

        ## POLL QUEUE
        end_time = time.time() + self.timeout
        curr_time = time.time()
        poll_interval = self.scheduler.polling_interval  # poll every 3ms
        make_request = False

        while curr_time < end_time:
            _healthy_deployments, _ = await self._async_get_healthy_deployments(
                model=model, parent_otel_span=parent_otel_span
            )
            make_request = await self.scheduler.poll(  ## POLL QUEUE ## - returns 'True' if there's healthy deployments OR if request is at top of queue
                id=item.request_id,
                model_name=item.model_name,
                health_deployments=_healthy_deployments,
            )
            if make_request:  ## IF TRUE -> MAKE REQUEST
                break
            else:  ## ELSE -> loop till default_timeout
                await asyncio.sleep(poll_interval)
                curr_time = time.time()

        if make_request:
            try:
                _response = await self.acompletion(
                    model=model, messages=messages, stream=stream, **kwargs
                )
                _response._hidden_params.setdefault("additional_headers", {})
                _response._hidden_params["additional_headers"].update(
                    {"x-litellm-request-prioritization-used": True}
                )
                return _response
            except Exception as e:
                setattr(e, "priority", priority)
                raise e
        else:
            raise litellm.Timeout(
                message="Request timed out while polling queue",
                model=model,
                llm_provider="openai",
            )

    async def _schedule_factory(
        self,
        model: str,
        priority: int,
        original_function: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ):
        parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
        ### FLOW ITEM ###
        _request_id = str(uuid.uuid4())
        item = FlowItem(
            priority=priority,  # 👈 SET PRIORITY FOR REQUEST
            request_id=_request_id,  # 👈 SET REQUEST ID
            model_name=model,  # 👈 SAME as 'Router'
        )
        ### [fin] ###

        ## ADDS REQUEST TO QUEUE ##
        await self.scheduler.add_request(request=item)

        ## POLL QUEUE
        end_time = time.time() + self.timeout
        curr_time = time.time()
        poll_interval = self.scheduler.polling_interval  # poll every 3ms
        make_request = False

        while curr_time < end_time:
            _healthy_deployments, _ = await self._async_get_healthy_deployments(
                model=model, parent_otel_span=parent_otel_span
            )
            make_request = await self.scheduler.poll(  ## POLL QUEUE ## - returns 'True' if there's healthy deployments OR if request is at top of queue
                id=item.request_id,
                model_name=item.model_name,
                health_deployments=_healthy_deployments,
            )
            if make_request:  ## IF TRUE -> MAKE REQUEST
                break
            else:  ## ELSE -> loop till default_timeout
                await asyncio.sleep(poll_interval)
                curr_time = time.time()

        if make_request:
            try:
                _response = await original_function(*args, **kwargs)
                if isinstance(_response._hidden_params, dict):
                    _response._hidden_params.setdefault("additional_headers", {})
                    _response._hidden_params["additional_headers"].update(
                        {"x-litellm-request-prioritization-used": True}
                    )
                return _response
            except Exception as e:
                setattr(e, "priority", priority)
                raise e
        else:
            raise litellm.Timeout(
                message="Request timed out while polling queue",
                model=model,
                llm_provider="openai",
            )

    def _is_prompt_management_model(self, model: str) -> bool:
        model_list = self.get_model_list(model_name=model)
        if model_list is None:
            return False
        if len(model_list) != 1:
            return False

        litellm_model = model_list[0]["litellm_params"].get("model", None)

        if litellm_model is None:
            return False

        if "/" in litellm_model:
            split_litellm_model = litellm_model.split("/")[0]
            if split_litellm_model in litellm._known_custom_logger_compatible_callbacks:
                return True
        return False

    async def _prompt_management_factory(
        self,
        model: str,
        messages: List[AllMessageValues],
        kwargs: Dict[str, Any],
    ):
        litellm_logging_object = kwargs.get("litellm_logging_obj", None)
        if litellm_logging_object is None:
            litellm_logging_object, kwargs = function_setup(
                **{
                    "original_function": "acompletion",
                    "rules_obj": Rules(),
                    "start_time": get_utc_datetime(),
                    **kwargs,
                }
            )
        litellm_logging_object = cast(LiteLLMLogging, litellm_logging_object)
        prompt_management_deployment = self.get_available_deployment(
            model=model,
            messages=[{"role": "user", "content": "prompt"}],
            specific_deployment=kwargs.pop("specific_deployment", None),
        )

        self._update_kwargs_with_deployment(
            deployment=prompt_management_deployment, kwargs=kwargs
        )
        data = prompt_management_deployment["litellm_params"].copy()

        litellm_model = data.get("model", None)

        prompt_id = kwargs.get("prompt_id") or prompt_management_deployment[
            "litellm_params"
        ].get("prompt_id", None)
        prompt_variables = kwargs.get(
            "prompt_variables"
        ) or prompt_management_deployment["litellm_params"].get(
            "prompt_variables", None
        )
        prompt_label = kwargs.get("prompt_label", None) or prompt_management_deployment[
            "litellm_params"
        ].get("prompt_label", None)

        if prompt_id is None or not isinstance(prompt_id, str):
            raise ValueError(
                f"Prompt ID is not set or not a string. Got={prompt_id}, type={type(prompt_id)}"
            )
        if prompt_variables is not None and not isinstance(prompt_variables, dict):
            raise ValueError(
                f"Prompt variables is set but not a dictionary. Got={prompt_variables}, type={type(prompt_variables)}"
            )

        (
            model,
            messages,
            optional_params,
        ) = litellm_logging_object.get_chat_completion_prompt(
            model=litellm_model,
            messages=messages,
            non_default_params=get_non_default_completion_params(kwargs=kwargs),
            prompt_id=prompt_id,
            prompt_variables=prompt_variables,
            prompt_label=prompt_label,
        )

        kwargs = {**data, **kwargs, **optional_params}
        kwargs["model"] = model
        kwargs["messages"] = messages
        kwargs["litellm_logging_obj"] = litellm_logging_object
        kwargs["prompt_id"] = prompt_id
        kwargs["prompt_variables"] = prompt_variables
        kwargs["prompt_label"] = prompt_label

        _model_list = self.get_model_list(model_name=model)
        if _model_list is None or len(_model_list) == 0:  # if direct call to model
            kwargs.pop("original_function")
            return await litellm.acompletion(**kwargs)

        return await self.async_function_with_fallbacks(**kwargs)

    def image_generation(self, prompt: str, model: str, **kwargs):
        try:
            kwargs["model"] = model
            kwargs["prompt"] = prompt
            kwargs["original_function"] = self._image_generation
            kwargs["num_retries"] = kwargs.get("num_retries", self.num_retries)
            kwargs.setdefault("metadata", {}).update({"model_group": model})
            response = self.function_with_fallbacks(**kwargs)

            return response
        except Exception as e:
            raise e

    def _image_generation(self, prompt: str, model: str, **kwargs):
        model_name = ""
        try:
            verbose_router_logger.debug(
                f"Inside _image_generation()- model: {model}; kwargs: {kwargs}"
            )
            deployment = self.get_available_deployment(
                model=model,
                messages=[{"role": "user", "content": "prompt"}],
                specific_deployment=kwargs.pop("specific_deployment", None),
            )
            self._update_kwargs_with_deployment(deployment=deployment, kwargs=kwargs)
            data = deployment["litellm_params"].copy()

            model_client = self._get_async_openai_model_client(
                deployment=deployment,
                kwargs=kwargs,
            )

            self.total_calls[model_name] += 1

            ### DEPLOYMENT-SPECIFIC PRE-CALL CHECKS ### (e.g. update rpm pre-call. Raise error, if deployment over limit)
            self.routing_strategy_pre_call_checks(deployment=deployment)

            response = litellm.image_generation(
                **{
                    **data,
                    "prompt": prompt,
                    "caching": self.cache_responses,
                    "client": model_client,
                    **kwargs,
                }
            )
            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"litellm.image_generation(model={model_name})\033[32m 200 OK\033[0m"
            )
            return response
        except Exception as e:
            verbose_router_logger.info(
                f"litellm.image_generation(model={model_name})\033[31m Exception {str(e)}\033[0m"
            )
            if model_name is not None:
                self.fail_calls[model_name] += 1
            raise e

    async def aimage_generation(self, prompt: str, model: str, **kwargs):
        try:
            kwargs["model"] = model
            kwargs["prompt"] = prompt
            kwargs["original_function"] = self._aimage_generation
            kwargs["num_retries"] = kwargs.get("num_retries", self.num_retries)
            self._update_kwargs_before_fallbacks(model=model, kwargs=kwargs)
            response = await self.async_function_with_fallbacks(**kwargs)

            return response
        except Exception as e:
            asyncio.create_task(
                send_llm_exception_alert(
                    litellm_router_instance=self,
                    request_kwargs=kwargs,
                    error_traceback_str=traceback.format_exc(),
                    original_exception=e,
                )
            )
            raise e

    async def _aimage_generation(self, prompt: str, model: str, **kwargs):
        model_name = model
        try:
            verbose_router_logger.debug(
                f"Inside _image_generation()- model: {model}; kwargs: {kwargs}"
            )
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
            deployment = await self.async_get_available_deployment(
                model=model,
                messages=[{"role": "user", "content": "prompt"}],
                specific_deployment=kwargs.pop("specific_deployment", None),
                request_kwargs=kwargs,
            )
            self._update_kwargs_with_deployment(deployment=deployment, kwargs=kwargs)

            data = deployment["litellm_params"].copy()
            model_name = data["model"]

            model_client = self._get_async_openai_model_client(
                deployment=deployment,
                kwargs=kwargs,
            )

            self.total_calls[model_name] += 1
            response = litellm.aimage_generation(
                **{
                    **data,
                    "prompt": prompt,
                    "caching": self.cache_responses,
                    "client": model_client,
                    **kwargs,
                }
            )

            ### CONCURRENCY-SAFE RPM CHECKS ###
            rpm_semaphore = self._get_client(
                deployment=deployment,
                kwargs=kwargs,
                client_type="max_parallel_requests",
            )

            if rpm_semaphore is not None and isinstance(
                rpm_semaphore, asyncio.Semaphore
            ):
                async with rpm_semaphore:
                    """
                    - Check rpm limits before making the call
                    - If allowed, increment the rpm limit (allows global value to be updated, concurrency-safe)
                    """
                    await self.async_routing_strategy_pre_call_checks(
                        deployment=deployment, parent_otel_span=parent_otel_span
                    )
                    response = await response
            else:
                await self.async_routing_strategy_pre_call_checks(
                    deployment=deployment, parent_otel_span=parent_otel_span
                )
                response = await response

            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"litellm.aimage_generation(model={model_name})\033[32m 200 OK\033[0m"
            )
            return response
        except Exception as e:
            verbose_router_logger.info(
                f"litellm.aimage_generation(model={model_name})\033[31m Exception {str(e)}\033[0m"
            )
            if model_name is not None:
                self.fail_calls[model_name] += 1
            raise e

    async def atranscription(self, file: FileTypes, model: str, **kwargs):
        """
        Example Usage:

        ```
        from litellm import Router
        client = Router(model_list = [
            {
                "model_name": "whisper",
                "litellm_params": {
                    "model": "whisper-1",
                },
            },
        ])

        audio_file = open("speech.mp3", "rb")
        transcript = await client.atranscription(
        model="whisper",
        file=audio_file
        )

        ```
        """
        try:
            kwargs["model"] = model
            kwargs["file"] = file
            kwargs["original_function"] = self._atranscription
            self._update_kwargs_before_fallbacks(model=model, kwargs=kwargs)
            response = await self.async_function_with_fallbacks(**kwargs)

            return response
        except Exception as e:
            asyncio.create_task(
                send_llm_exception_alert(
                    litellm_router_instance=self,
                    request_kwargs=kwargs,
                    error_traceback_str=traceback.format_exc(),
                    original_exception=e,
                )
            )
            raise e

    async def _atranscription(self, file: FileTypes, model: str, **kwargs):
        model_name = model
        try:
            verbose_router_logger.debug(
                f"Inside _atranscription()- model: {model}; kwargs: {kwargs}"
            )
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
            deployment = await self.async_get_available_deployment(
                model=model,
                messages=[{"role": "user", "content": "prompt"}],
                specific_deployment=kwargs.pop("specific_deployment", None),
                request_kwargs=kwargs,
            )

            self._update_kwargs_with_deployment(deployment=deployment, kwargs=kwargs)
            data = deployment["litellm_params"].copy()
            model_client = self._get_async_openai_model_client(
                deployment=deployment,
                kwargs=kwargs,
            )

            self.total_calls[model_name] += 1
            response = litellm.atranscription(
                **{
                    **data,
                    "file": file,
                    "caching": self.cache_responses,
                    "client": model_client,
                    **kwargs,
                }
            )

            ### CONCURRENCY-SAFE RPM CHECKS ###
            rpm_semaphore = self._get_client(
                deployment=deployment,
                kwargs=kwargs,
                client_type="max_parallel_requests",
            )

            if rpm_semaphore is not None and isinstance(
                rpm_semaphore, asyncio.Semaphore
            ):
                async with rpm_semaphore:
                    """
                    - Check rpm limits before making the call
                    - If allowed, increment the rpm limit (allows global value to be updated, concurrency-safe)
                    """
                    await self.async_routing_strategy_pre_call_checks(
                        deployment=deployment, parent_otel_span=parent_otel_span
                    )
                    response = await response
            else:
                await self.async_routing_strategy_pre_call_checks(
                    deployment=deployment, parent_otel_span=parent_otel_span
                )
                response = await response

            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"litellm.atranscription(model={model_name})\033[32m 200 OK\033[0m"
            )
            return response
        except Exception as e:
            verbose_router_logger.info(
                f"litellm.atranscription(model={model_name})\033[31m Exception {str(e)}\033[0m"
            )
            if model_name is not None:
                self.fail_calls[model_name] += 1
            raise e

    async def aspeech(self, model: str, input: str, voice: str, **kwargs):
        """
        Example Usage:

        ```
        from litellm import Router
        client = Router(model_list = [
            {
                "model_name": "tts",
                "litellm_params": {
                    "model": "tts-1",
                },
            },
        ])

        async with client.aspeech(
            model="tts",
            voice="alloy",
            input="the quick brown fox jumped over the lazy dogs",
            api_base=None,
            api_key=None,
            organization=None,
            project=None,
            max_retries=1,
            timeout=600,
            client=None,
            optional_params={},
        ) as response:
            response.stream_to_file(speech_file_path)

        ```
        """
        try:
            kwargs["input"] = input
            kwargs["voice"] = voice

            deployment = await self.async_get_available_deployment(
                model=model,
                messages=[{"role": "user", "content": "prompt"}],
                specific_deployment=kwargs.pop("specific_deployment", None),
                request_kwargs=kwargs,
            )
            self._update_kwargs_before_fallbacks(model=model, kwargs=kwargs)
            data = deployment["litellm_params"].copy()
            data["model"]
            for k, v in self.default_litellm_params.items():
                if (
                    k not in kwargs
                ):  # prioritize model-specific params > default router params
                    kwargs[k] = v
                elif k == "metadata":
                    kwargs[k].update(v)

            potential_model_client = self._get_client(
                deployment=deployment, kwargs=kwargs, client_type="async"
            )
            # check if provided keys == client keys #
            dynamic_api_key = kwargs.get("api_key", None)
            if (
                dynamic_api_key is not None
                and potential_model_client is not None
                and dynamic_api_key != potential_model_client.api_key
            ):
                model_client = None
            else:
                model_client = potential_model_client

            response = await litellm.aspeech(
                **{
                    **data,
                    "client": model_client,
                    **kwargs,
                }
            )
            return response
        except Exception as e:
            asyncio.create_task(
                send_llm_exception_alert(
                    litellm_router_instance=self,
                    request_kwargs=kwargs,
                    error_traceback_str=traceback.format_exc(),
                    original_exception=e,
                )
            )
            raise e

    async def arerank(self, model: str, **kwargs):
        try:
            kwargs["model"] = model
            kwargs["input"] = input
            kwargs["original_function"] = self._arerank
            self._update_kwargs_before_fallbacks(model=model, kwargs=kwargs)

            response = await self.async_function_with_fallbacks(**kwargs)

            return response
        except Exception as e:
            asyncio.create_task(
                send_llm_exception_alert(
                    litellm_router_instance=self,
                    request_kwargs=kwargs,
                    error_traceback_str=traceback.format_exc(),
                    original_exception=e,
                )
            )
            raise e

    async def _arerank(self, model: str, **kwargs):
        model_name = None
        try:
            verbose_router_logger.debug(
                f"Inside _rerank()- model: {model}; kwargs: {kwargs}"
            )
            deployment = await self.async_get_available_deployment(
                model=model,
                specific_deployment=kwargs.pop("specific_deployment", None),
                request_kwargs=kwargs,
            )
            self._update_kwargs_with_deployment(deployment=deployment, kwargs=kwargs)
            data = deployment["litellm_params"].copy()
            model_name = data["model"]

            model_client = self._get_async_openai_model_client(
                deployment=deployment,
                kwargs=kwargs,
            )
            self.total_calls[model_name] += 1

            response = await litellm.arerank(
                **{
                    **data,
                    "caching": self.cache_responses,
                    "client": model_client,
                    **kwargs,
                }
            )

            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"litellm.arerank(model={model_name})\033[32m 200 OK\033[0m"
            )
            return response
        except Exception as e:
            verbose_router_logger.info(
                f"litellm.arerank(model={model_name})\033[31m Exception {str(e)}\033[0m"
            )
            if model_name is not None:
                self.fail_calls[model_name] += 1
            raise e

    def text_completion(
        self,
        model: str,
        prompt: str,
        is_retry: Optional[bool] = False,
        is_fallback: Optional[bool] = False,
        is_async: Optional[bool] = False,
        **kwargs,
    ):
        messages = [{"role": "user", "content": prompt}]
        try:
            kwargs["model"] = model
            kwargs["prompt"] = prompt
            kwargs["num_retries"] = kwargs.get("num_retries", self.num_retries)
            kwargs.setdefault("metadata", {}).update({"model_group": model})

            # pick the one that is available (lowest TPM/RPM)
            deployment = self.get_available_deployment(
                model=model,
                messages=messages,
                specific_deployment=kwargs.pop("specific_deployment", None),
            )

            data = deployment["litellm_params"].copy()
            for k, v in self.default_litellm_params.items():
                if (
                    k not in kwargs
                ):  # prioritize model-specific params > default router params
                    kwargs[k] = v
                elif k == "metadata":
                    kwargs[k].update(v)

            # call via litellm.completion()
            return litellm.text_completion(**{**data, "prompt": prompt, "caching": self.cache_responses, **kwargs})  # type: ignore
        except Exception as e:
            raise e

    async def atext_completion(
        self,
        model: str,
        prompt: str,
        is_retry: Optional[bool] = False,
        is_fallback: Optional[bool] = False,
        is_async: Optional[bool] = False,
        **kwargs,
    ):
        if kwargs.get("priority", None) is not None:
            return await self._schedule_factory(
                model=model,
                priority=kwargs.pop("priority"),
                original_function=self.atext_completion,
                args=(model, prompt),
                kwargs=kwargs,
            )
        try:
            kwargs["model"] = model
            kwargs["prompt"] = prompt
            kwargs["original_function"] = self._atext_completion

            self._update_kwargs_before_fallbacks(model=model, kwargs=kwargs)
            response = await self.async_function_with_fallbacks(**kwargs)

            return response
        except Exception as e:
            asyncio.create_task(
                send_llm_exception_alert(
                    litellm_router_instance=self,
                    request_kwargs=kwargs,
                    error_traceback_str=traceback.format_exc(),
                    original_exception=e,
                )
            )
            raise e

    async def _atext_completion(self, model: str, prompt: str, **kwargs):
        try:
            verbose_router_logger.debug(
                f"Inside _atext_completion()- model: {model}; kwargs: {kwargs}"
            )
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
            deployment = await self.async_get_available_deployment(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                specific_deployment=kwargs.pop("specific_deployment", None),
                request_kwargs=kwargs,
            )
            self._update_kwargs_with_deployment(deployment=deployment, kwargs=kwargs)

            data = deployment["litellm_params"].copy()
            model_name = data["model"]

            model_client = self._get_async_openai_model_client(
                deployment=deployment,
                kwargs=kwargs,
            )
            self.total_calls[model_name] += 1

            response = litellm.atext_completion(
                **{
                    **data,
                    "prompt": prompt,
                    "caching": self.cache_responses,
                    "client": model_client,
                    **kwargs,
                }
            )

            rpm_semaphore = self._get_client(
                deployment=deployment,
                kwargs=kwargs,
                client_type="max_parallel_requests",
            )

            if rpm_semaphore is not None and isinstance(
                rpm_semaphore, asyncio.Semaphore
            ):
                async with rpm_semaphore:
                    """
                    - Check rpm limits before making the call
                    - If allowed, increment the rpm limit (allows global value to be updated, concurrency-safe)
                    """
                    await self.async_routing_strategy_pre_call_checks(
                        deployment=deployment, parent_otel_span=parent_otel_span
                    )
                    response = await response
            else:
                await self.async_routing_strategy_pre_call_checks(
                    deployment=deployment, parent_otel_span=parent_otel_span
                )
                response = await response

            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"litellm.atext_completion(model={model_name})\033[32m 200 OK\033[0m"
            )
            return response
        except Exception as e:
            verbose_router_logger.info(
                f"litellm.atext_completion(model={model})\033[31m Exception {str(e)}\033[0m"
            )
            if model is not None:
                self.fail_calls[model] += 1
            raise e

    async def aadapter_completion(
        self,
        adapter_id: str,
        model: str,
        is_retry: Optional[bool] = False,
        is_fallback: Optional[bool] = False,
        is_async: Optional[bool] = False,
        **kwargs,
    ):
        try:
            kwargs["model"] = model
            kwargs["adapter_id"] = adapter_id
            kwargs["original_function"] = self._aadapter_completion
            kwargs["num_retries"] = kwargs.get("num_retries", self.num_retries)
            kwargs.setdefault("metadata", {}).update({"model_group": model})
            response = await self.async_function_with_fallbacks(**kwargs)

            return response
        except Exception as e:
            asyncio.create_task(
                send_llm_exception_alert(
                    litellm_router_instance=self,
                    request_kwargs=kwargs,
                    error_traceback_str=traceback.format_exc(),
                    original_exception=e,
                )
            )
            raise e

    async def _aadapter_completion(self, adapter_id: str, model: str, **kwargs):
        try:
            verbose_router_logger.debug(
                f"Inside _aadapter_completion()- model: {model}; kwargs: {kwargs}"
            )
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
            deployment = await self.async_get_available_deployment(
                model=model,
                messages=[{"role": "user", "content": "default text"}],
                specific_deployment=kwargs.pop("specific_deployment", None),
                request_kwargs=kwargs,
            )
            self._update_kwargs_with_deployment(deployment=deployment, kwargs=kwargs)

            data = deployment["litellm_params"].copy()
            model_name = data["model"]

            model_client = self._get_async_openai_model_client(
                deployment=deployment,
                kwargs=kwargs,
            )
            self.total_calls[model_name] += 1

            response = litellm.aadapter_completion(
                **{
                    **data,
                    "adapter_id": adapter_id,
                    "caching": self.cache_responses,
                    "client": model_client,
                    **kwargs,
                }
            )

            rpm_semaphore = self._get_client(
                deployment=deployment,
                kwargs=kwargs,
                client_type="max_parallel_requests",
            )

            if rpm_semaphore is not None and isinstance(
                rpm_semaphore, asyncio.Semaphore
            ):
                async with rpm_semaphore:
                    """
                    - Check rpm limits before making the call
                    - If allowed, increment the rpm limit (allows global value to be updated, concurrency-safe)
                    """
                    await self.async_routing_strategy_pre_call_checks(
                        deployment=deployment, parent_otel_span=parent_otel_span
                    )
                    response = await response  # type: ignore
            else:
                await self.async_routing_strategy_pre_call_checks(
                    deployment=deployment, parent_otel_span=parent_otel_span
                )
                response = await response  # type: ignore

            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"litellm.aadapter_completion(model={model_name})\033[32m 200 OK\033[0m"
            )
            return response
        except Exception as e:
            verbose_router_logger.info(
                f"litellm.aadapter_completion(model={model})\033[31m Exception {str(e)}\033[0m"
            )
            if model is not None:
                self.fail_calls[model] += 1
            raise e

    async def _ageneric_api_call_with_fallbacks(
        self, model: str, original_function: Callable, **kwargs
    ):
        """
        Make a generic LLM API call through the router, this allows you to use retries/fallbacks with litellm router

        Args:
            model: The model to use
            handler_function: The handler function to call (e.g., litellm.anthropic_messages)
            **kwargs: Additional arguments to pass to the handler function

        Returns:
            The response from the handler function
        """
        handler_name = original_function.__name__
        function_name = "_ageneric_api_call_with_fallbacks"
        self._update_kwargs_before_fallbacks(
            model=model,
            kwargs=kwargs,
            metadata_variable_name = _get_router_metadata_variable_name(
                function_name=function_name
            )
        )
        try:
            verbose_router_logger.debug(
                f"Inside _ageneric_api_call() - handler: {handler_name}, model: {model}; kwargs: {kwargs}"
            )
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
            deployment = await self.async_get_available_deployment(
                model=model,
                request_kwargs=kwargs,
                messages=kwargs.get("messages", None),
                specific_deployment=kwargs.pop("specific_deployment", None),
            )

            self._update_kwargs_with_deployment(
                deployment=deployment, kwargs=kwargs, function_name=function_name
            )

            data = deployment["litellm_params"].copy()
            model_name = data["model"]
            self.total_calls[model_name] += 1

            ### get custom

            response = original_function(
                **{
                    **data,
                    "caching": self.cache_responses,
                    **kwargs,
                }
            )

            rpm_semaphore = self._get_client(
                deployment=deployment,
                kwargs=kwargs,
                client_type="max_parallel_requests",
            )

            if rpm_semaphore is not None and isinstance(
                rpm_semaphore, asyncio.Semaphore
            ):
                async with rpm_semaphore:
                    """
                    - Check rpm limits before making the call
                    - If allowed, increment the rpm limit (allows global value to be updated, concurrency-safe)
                    """
                    await self.async_routing_strategy_pre_call_checks(
                        deployment=deployment, parent_otel_span=parent_otel_span
                    )
                    response = await response  # type: ignore
            else:
                await self.async_routing_strategy_pre_call_checks(
                    deployment=deployment, parent_otel_span=parent_otel_span
                )
                response = await response  # type: ignore

            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"{handler_name}(model={model_name})\033[32m 200 OK\033[0m"
            )
            return response
        except Exception as e:
            verbose_router_logger.info(
                f"{handler_name}(model={model})\033[31m Exception {str(e)}\033[0m"
            )
            if model is not None:
                self.fail_calls[model] += 1
            raise e

    def _generic_api_call_with_fallbacks(
        self, model: str, original_function: Callable, **kwargs
    ):
        """
        Make a generic LLM API call through the router, this allows you to use retries/fallbacks with litellm router
        Args:
            model: The model to use
            original_function: The handler function to call (e.g., litellm.completion)
            **kwargs: Additional arguments to pass to the handler function
        Returns:
            The response from the handler function
        """
        handler_name = original_function.__name__
        try:
            verbose_router_logger.debug(
                f"Inside _generic_api_call() - handler: {handler_name}, model: {model}; kwargs: {kwargs}"
            )
            deployment = self.get_available_deployment(
                model=model,
                messages=kwargs.get("messages", None),
                specific_deployment=kwargs.pop("specific_deployment", None),
            )
            self._update_kwargs_with_deployment(
                deployment=deployment, kwargs=kwargs, function_name="generic_api_call"
            )

            data = deployment["litellm_params"].copy()
            model_name = data["model"]

            self.total_calls[model_name] += 1

            # Perform pre-call checks for routing strategy
            self.routing_strategy_pre_call_checks(deployment=deployment)

            try:
                _, custom_llm_provider, _, _ = get_llm_provider(model=data["model"])
            except Exception:
                custom_llm_provider = None

            response = original_function(
                **{
                    **data,
                    "custom_llm_provider": custom_llm_provider,
                    "caching": self.cache_responses,
                    **kwargs,
                }
            )

            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"{handler_name}(model={model_name})\033[32m 200 OK\033[0m"
            )
            return response
        except Exception as e:
            verbose_router_logger.info(
                f"{handler_name}(model={model})\033[31m Exception {str(e)}\033[0m"
            )
            if model is not None:
                self.fail_calls[model] += 1
            raise e

    def embedding(
        self,
        model: str,
        input: Union[str, List],
        is_async: Optional[bool] = False,
        **kwargs,
    ) -> EmbeddingResponse:
        try:
            kwargs["model"] = model
            kwargs["input"] = input
            kwargs["original_function"] = self._embedding
            kwargs["num_retries"] = kwargs.get("num_retries", self.num_retries)
            kwargs.setdefault("metadata", {}).update({"model_group": model})
            response = self.function_with_fallbacks(**kwargs)
            return response
        except Exception as e:
            raise e

    def _embedding(self, input: Union[str, List], model: str, **kwargs):
        model_name = None
        try:
            verbose_router_logger.debug(
                f"Inside embedding()- model: {model}; kwargs: {kwargs}"
            )
            deployment = self.get_available_deployment(
                model=model,
                input=input,
                specific_deployment=kwargs.pop("specific_deployment", None),
            )
            self._update_kwargs_with_deployment(deployment=deployment, kwargs=kwargs)
            data = deployment["litellm_params"].copy()
            model_name = data["model"]

            potential_model_client = self._get_client(
                deployment=deployment, kwargs=kwargs, client_type="sync"
            )
            # check if provided keys == client keys #
            dynamic_api_key = kwargs.get("api_key", None)
            if (
                dynamic_api_key is not None
                and potential_model_client is not None
                and dynamic_api_key != potential_model_client.api_key
            ):
                model_client = None
            else:
                model_client = potential_model_client

            self.total_calls[model_name] += 1

            ### DEPLOYMENT-SPECIFIC PRE-CALL CHECKS ### (e.g. update rpm pre-call. Raise error, if deployment over limit)
            self.routing_strategy_pre_call_checks(deployment=deployment)

            response = litellm.embedding(
                **{
                    **data,
                    "input": input,
                    "caching": self.cache_responses,
                    "client": model_client,
                    **kwargs,
                }
            )
            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"litellm.embedding(model={model_name})\033[32m 200 OK\033[0m"
            )
            return response
        except Exception as e:
            verbose_router_logger.info(
                f"litellm.embedding(model={model_name})\033[31m Exception {str(e)}\033[0m"
            )
            if model_name is not None:
                self.fail_calls[model_name] += 1
            raise e

    async def aembedding(
        self,
        model: str,
        input: Union[str, List],
        is_async: Optional[bool] = True,
        **kwargs,
    ) -> EmbeddingResponse:
        try:
            kwargs["model"] = model
            kwargs["input"] = input
            kwargs["original_function"] = self._aembedding
            self._update_kwargs_before_fallbacks(model=model, kwargs=kwargs)
            response = await self.async_function_with_fallbacks(**kwargs)
            return response
        except Exception as e:
            asyncio.create_task(
                send_llm_exception_alert(
                    litellm_router_instance=self,
                    request_kwargs=kwargs,
                    error_traceback_str=traceback.format_exc(),
                    original_exception=e,
                )
            )
            raise e

    async def _aembedding(self, input: Union[str, List], model: str, **kwargs):
        model_name = None
        try:
            verbose_router_logger.debug(
                f"Inside _aembedding()- model: {model}; kwargs: {kwargs}"
            )
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
            deployment = await self.async_get_available_deployment(
                model=model,
                input=input,
                specific_deployment=kwargs.pop("specific_deployment", None),
                request_kwargs=kwargs,
            )
            self._update_kwargs_with_deployment(deployment=deployment, kwargs=kwargs)
            data = deployment["litellm_params"].copy()
            model_name = data["model"]
            model_client = self._get_async_openai_model_client(
                deployment=deployment,
                kwargs=kwargs,
            )

            self.total_calls[model_name] += 1
            response = litellm.aembedding(
                **{
                    **data,
                    "input": input,
                    "caching": self.cache_responses,
                    "client": model_client,
                    **kwargs,
                }
            )

            ### CONCURRENCY-SAFE RPM CHECKS ###
            rpm_semaphore = self._get_client(
                deployment=deployment,
                kwargs=kwargs,
                client_type="max_parallel_requests",
            )

            if rpm_semaphore is not None and isinstance(
                rpm_semaphore, asyncio.Semaphore
            ):
                async with rpm_semaphore:
                    """
                    - Check rpm limits before making the call
                    - If allowed, increment the rpm limit (allows global value to be updated, concurrency-safe)
                    """
                    await self.async_routing_strategy_pre_call_checks(
                        deployment=deployment, parent_otel_span=parent_otel_span
                    )
                    response = await response
            else:
                await self.async_routing_strategy_pre_call_checks(
                    deployment=deployment, parent_otel_span=parent_otel_span
                )
                response = await response

            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"litellm.aembedding(model={model_name})\033[32m 200 OK\033[0m"
            )
            return response
        except Exception as e:
            verbose_router_logger.info(
                f"litellm.aembedding(model={model_name})\033[31m Exception {str(e)}\033[0m"
            )
            if model_name is not None:
                self.fail_calls[model_name] += 1
            raise e

    #### FILES API ####
    async def acreate_file(
        self,
        model: str,
        **kwargs,
    ) -> OpenAIFileObject:
        try:
            kwargs["model"] = model
            kwargs["original_function"] = self._acreate_file
            kwargs["num_retries"] = kwargs.get("num_retries", self.num_retries)
            self._update_kwargs_before_fallbacks(model=model, kwargs=kwargs)
            response = await self.async_function_with_fallbacks(**kwargs)

            return response
        except Exception as e:
            asyncio.create_task(
                send_llm_exception_alert(
                    litellm_router_instance=self,
                    request_kwargs=kwargs,
                    error_traceback_str=traceback.format_exc(),
                    original_exception=e,
                )
            )
            raise e

    async def _acreate_file(
        self,
        model: str,
        **kwargs,
    ) -> OpenAIFileObject:
        try:
            verbose_router_logger.debug(
                f"Inside _atext_completion()- model: {model}; kwargs: {kwargs}"
            )
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
            healthy_deployments = await self.async_get_healthy_deployments(
                model=model,
                messages=[{"role": "user", "content": "files-api-fake-text"}],
                specific_deployment=kwargs.pop("specific_deployment", None),
                request_kwargs=kwargs,
                parent_otel_span=parent_otel_span,
            )

            async def create_file_for_deployment(deployment: dict) -> OpenAIFileObject:
                kwargs_copy = copy.deepcopy(kwargs)
                self._update_kwargs_with_deployment(
                    deployment=deployment,
                    kwargs=kwargs_copy,
                    function_name="acreate_file",
                )
                data = deployment["litellm_params"].copy()
                model_name = data["model"]

                model_client = self._get_async_openai_model_client(
                    deployment=deployment,
                    kwargs=kwargs_copy,
                )
                self.total_calls[model_name] += 1

                ## REPLACE MODEL IN FILE WITH SELECTED DEPLOYMENT ##
                stripped_model, custom_llm_provider, _, _ = get_llm_provider(
                    model=data["model"]
                )

                ## REPLACE MODEL IN FILE WITH SELECTED DEPLOYMENT ##
                purpose = cast(Optional[OpenAIFilesPurpose], kwargs.get("purpose"))
                file = cast(Optional[FileTypes], kwargs.get("file"))
                if not file or not purpose:
                    raise Exception(
                        "file and file_purpose are required for create_file"
                    )

                replace_model_in_jsonl_bool = should_replace_model_in_jsonl(
                    purpose=purpose,
                )
                if replace_model_in_jsonl_bool:
                    file = replace_model_in_jsonl(
                        file_content=file,
                        new_model_name=stripped_model,
                    )

                    kwargs_copy["file"] = file

                response = litellm.acreate_file(
                    **{
                        **data,
                        "custom_llm_provider": custom_llm_provider,
                        "caching": self.cache_responses,
                        "client": model_client,
                        **kwargs_copy,
                    }
                )

                rpm_semaphore = self._get_client(
                    deployment=deployment,
                    kwargs=kwargs_copy,
                    client_type="max_parallel_requests",
                )

                if rpm_semaphore is not None and isinstance(
                    rpm_semaphore, asyncio.Semaphore
                ):
                    async with rpm_semaphore:
                        """
                        - Check rpm limits before making the call
                        - If allowed, increment the rpm limit (allows global value to be updated, concurrency-safe)
                        """
                        await self.async_routing_strategy_pre_call_checks(
                            deployment=deployment, parent_otel_span=parent_otel_span
                        )
                        response = await response  # type: ignore
                else:
                    await self.async_routing_strategy_pre_call_checks(
                        deployment=deployment, parent_otel_span=parent_otel_span
                    )
                    response = await response  # type: ignore

                self.success_calls[model_name] += 1
                verbose_router_logger.info(
                    f"litellm.acreate_file(model={model_name})\033[32m 200 OK\033[0m"
                )

                return response

            tasks = []
            if isinstance(healthy_deployments, dict):
                tasks.append(create_file_for_deployment(healthy_deployments))
            else:
                for deployment in healthy_deployments:
                    tasks.append(create_file_for_deployment(deployment))

            responses = await asyncio.gather(*tasks)

            if len(responses) == 0:
                raise Exception("No healthy deployments found.")
            return responses[0]
        except Exception as e:
            verbose_router_logger.exception(
                f"litellm.acreate_file(model={model}, {kwargs})\033[31m Exception {str(e)}\033[0m"
            )
            if model is not None:
                self.fail_calls[model] += 1
            raise e

    async def acreate_batch(
        self,
        model: str,
        **kwargs,
    ) -> LiteLLMBatch:
        try:
            kwargs["model"] = model
            kwargs["original_function"] = self._acreate_batch
            kwargs["num_retries"] = kwargs.get("num_retries", self.num_retries)
            metadata_variable_name = _get_router_metadata_variable_name(
                function_name="_acreate_batch"
            )
            self._update_kwargs_before_fallbacks(
                model=model,
                kwargs=kwargs,
                metadata_variable_name=metadata_variable_name,
            )
            response = await self.async_function_with_fallbacks(**kwargs)

            return response
        except Exception as e:
            asyncio.create_task(
                send_llm_exception_alert(
                    litellm_router_instance=self,
                    request_kwargs=kwargs,
                    error_traceback_str=traceback.format_exc(),
                    original_exception=e,
                )
            )
            raise e

    async def _acreate_batch(
        self,
        model: str,
        **kwargs,
    ) -> LiteLLMBatch:
        try:
            verbose_router_logger.debug(
                f"Inside _acreate_batch()- model: {model}; kwargs: {kwargs}"
            )
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
            deployment = await self.async_get_available_deployment(
                model=model,
                messages=[{"role": "user", "content": "files-api-fake-text"}],
                specific_deployment=kwargs.pop("specific_deployment", None),
                request_kwargs=kwargs,
            )

            data = deployment["litellm_params"].copy()
            model_name = data["model"]
            self._update_kwargs_with_deployment(
                deployment=deployment, kwargs=kwargs, function_name="_acreate_batch"
            )

            model_client = self._get_async_openai_model_client(
                deployment=deployment,
                kwargs=kwargs,
            )
            self.total_calls[model_name] += 1

            ## SET CUSTOM PROVIDER TO SELECTED DEPLOYMENT ##
            _, custom_llm_provider, _, _ = get_llm_provider(model=data["model"])

            response = litellm.acreate_batch(
                **{
                    **data,
                    "custom_llm_provider": custom_llm_provider,
                    "caching": self.cache_responses,
                    "client": model_client,
                    **kwargs,
                }
            )

            rpm_semaphore = self._get_client(
                deployment=deployment,
                kwargs=kwargs,
                client_type="max_parallel_requests",
            )

            if rpm_semaphore is not None and isinstance(
                rpm_semaphore, asyncio.Semaphore
            ):
                async with rpm_semaphore:
                    """
                    - Check rpm limits before making the call
                    - If allowed, increment the rpm limit (allows global value to be updated, concurrency-safe)
                    """
                    await self.async_routing_strategy_pre_call_checks(
                        deployment=deployment, parent_otel_span=parent_otel_span
                    )
                    response = await response  # type: ignore
            else:
                await self.async_routing_strategy_pre_call_checks(
                    deployment=deployment, parent_otel_span=parent_otel_span
                )
                response = await response  # type: ignore

            self.success_calls[model_name] += 1
            verbose_router_logger.info(
                f"litellm.acreate_batch(model={model_name})\033[32m 200 OK\033[0m"
            )

            return response  # type: ignore
        except Exception as e:
            verbose_router_logger.exception(
                f"litellm._acreate_batch(model={model}, {kwargs})\033[31m Exception {str(e)}\033[0m"
            )
            if model is not None:
                self.fail_calls[model] += 1
            raise e

    async def aretrieve_batch(
        self,
        model: Optional[str] = None,
        **kwargs,
    ) -> LiteLLMBatch:
        """
        Iterate through all models in a model group to check for batch

        Future Improvement - cache the result.
        """
        try:
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
            if model is not None:
                filtered_model_list: Optional[
                    Union[List[DeploymentTypedDict], List[Dict], Dict]
                ] = await self.async_get_healthy_deployments(
                    model=model,
                    messages=[{"role": "user", "content": "retrieve-api-fake-text"}],
                    specific_deployment=kwargs.pop("specific_deployment", None),
                    request_kwargs=kwargs,
                    parent_otel_span=parent_otel_span,
                )
            else:
                filtered_model_list = self.get_model_list()
            if filtered_model_list is None:
                raise Exception("Router not yet initialized.")

            receieved_exceptions = []

            async def try_retrieve_batch(model_name: DeploymentTypedDict):
                try:
                    model = model_name["litellm_params"].get("model")
                    data = model_name["litellm_params"].copy()
                    custom_llm_provider = data.get("custom_llm_provider")
                    if model is None:
                        raise Exception(
                            f"Model not found in litellm_params for deployment: {model_name}"
                        )
                    # Update kwargs with the current model name or any other model-specific adjustments
                    ## SET CUSTOM PROVIDER TO SELECTED DEPLOYMENT ##
                    if not custom_llm_provider:
                        _, custom_llm_provider, _, _ = get_llm_provider(  # type: ignore
                            model=model
                        )
                    new_kwargs = copy.deepcopy(kwargs)
                    self._update_kwargs_with_deployment(
                        deployment=cast(dict, model_name),
                        kwargs=new_kwargs,
                        function_name="aretrieve_batch",
                    )
                    new_kwargs.pop("custom_llm_provider", None)
                    data.pop("custom_llm_provider", None)
                    return await litellm.aretrieve_batch(
                        **{
                            **data,
                            "custom_llm_provider": custom_llm_provider,
                            **new_kwargs,  # type: ignore
                        },
                    )
                except Exception as e:
                    import traceback

                    traceback.print_exc()
                    receieved_exceptions.append(e)
                    return None

            # Check all models in parallel
            if (
                filtered_model_list is not None
                and isinstance(filtered_model_list, list)
                and len(filtered_model_list) > 0
            ):
                results = await asyncio.gather(
                    *[
                        try_retrieve_batch(cast(DeploymentTypedDict, model))
                        for model in filtered_model_list
                    ],
                    return_exceptions=True,
                )
            elif filtered_model_list is not None and isinstance(
                filtered_model_list, dict
            ):
                results = await try_retrieve_batch(
                    cast(DeploymentTypedDict, filtered_model_list)
                )
            else:
                raise Exception("No healthy deployments found.")

            # Check for successful responses and handle exceptions
            if results is not None:
                if isinstance(results, LiteLLMBatch):
                    return results
                elif isinstance(results, list):
                    for result in results:
                        if isinstance(result, LiteLLMBatch):
                            return result

            # If no valid Batch response was found, raise the first encountered exception
            if receieved_exceptions:
                raise receieved_exceptions[0]  # Raising the first exception encountered

            # If no exceptions were encountered, raise a generic exception
            raise Exception(
                "Unable to find batch in any model. Received errors - {}".format(
                    receieved_exceptions
                )
            )
        except Exception as e:
            asyncio.create_task(
                send_llm_exception_alert(
                    litellm_router_instance=self,
                    request_kwargs=kwargs,
                    error_traceback_str=traceback.format_exc(),
                    original_exception=e,
                )
            )
            raise e

    async def alist_batches(
        self,
        model: str,
        **kwargs,
    ):
        """
        Return all the batches across all deployments of a model group.
        """

        filtered_model_list = self.get_model_list(model_name=model)
        if filtered_model_list is None:
            raise Exception("Router not yet initialized.")

        async def try_retrieve_batch(model: DeploymentTypedDict):
            try:
                # Update kwargs with the current model name or any other model-specific adjustments
                return await litellm.alist_batches(
                    **{**model["litellm_params"], **kwargs}
                )
            except Exception:
                return None

        # Check all models in parallel
        results = await asyncio.gather(
            *[try_retrieve_batch(model) for model in filtered_model_list]
        )

        final_results = {
            "object": "list",
            "data": [],
            "first_id": None,
            "last_id": None,
            "has_more": False,
        }

        for result in results:
            if result is not None:
                ## check batch id
                if final_results["first_id"] is None and hasattr(result, "first_id"):
                    final_results["first_id"] = getattr(result, "first_id")
                final_results["last_id"] = getattr(result, "last_id")
                final_results["data"].extend(result.data)  # type: ignore

                ## check 'has_more'
                if getattr(result, "has_more", False) is True:
                    final_results["has_more"] = True

        return final_results

    #### PASSTHROUGH API ####

    async def _pass_through_moderation_endpoint_factory(
        self,
        original_function: Callable,
        **kwargs,
    ):
        # update kwargs with model_group
        self._update_kwargs_before_fallbacks(
            model=kwargs.get("model", ""),
            kwargs=kwargs,
        )
        if kwargs.get("model") and self.get_model_list(model_name=kwargs["model"]):
            deployment = await self.async_get_available_deployment(
                model=kwargs["model"],
                request_kwargs=kwargs,
            )
            kwargs["model"] = deployment["litellm_params"]["model"]
            data = deployment["litellm_params"].copy()
            self._update_kwargs_with_deployment(
                deployment=deployment,
                kwargs=kwargs,
            )
            kwargs.update(data)

        return await original_function(**kwargs)

    def factory_function(
        self,
        original_function: Callable,
        call_type: Literal[
            "assistants",
            "moderation",
            "anthropic_messages",
            "aresponses",
            "responses",
            "aget_responses",
            "adelete_responses",
            "afile_delete",
            "afile_content",
            "_arealtime",
            "acreate_fine_tuning_job",
            "acancel_fine_tuning_job",
            "alist_fine_tuning_jobs",
            "aretrieve_fine_tuning_job",
            "alist_files",
            "aimage_edit",
            "allm_passthrough_route",
            "alist_input_items",
        ] = "assistants",
    ):
        """
        Creates appropriate wrapper functions for different API call types.

        Returns:
            - A synchronous function for synchronous call types
            - An asynchronous function for asynchronous call types
        """
        # Handle synchronous call types
        if call_type == "responses":

            def sync_wrapper(
                custom_llm_provider: Optional[
                    Literal["openai", "azure", "anthropic"]
                ] = None,
                client: Optional[Any] = None,
                **kwargs,
            ):
                return self._generic_api_call_with_fallbacks(
                    original_function=original_function, **kwargs
                )

            return sync_wrapper

        # Handle asynchronous call types
        async def async_wrapper(
            custom_llm_provider: Optional[
                Literal["openai", "azure", "anthropic"]
            ] = None,
            client: Optional[Any] = None,
            **kwargs,
        ):
            if call_type == "assistants":
                return await self._pass_through_assistants_endpoint_factory(
                    original_function=original_function,
                    custom_llm_provider=custom_llm_provider,
                    client=client,
                    **kwargs,
                )
            elif call_type == "moderation":
                return await self._pass_through_moderation_endpoint_factory(
                    original_function=original_function, **kwargs
                )
            elif call_type in (
                "anthropic_messages",
                "aresponses",
                "_arealtime",
                "acreate_fine_tuning_job",
                "acancel_fine_tuning_job",
                "alist_fine_tuning_jobs",
                "aretrieve_fine_tuning_job",
                "alist_files",
                "aimage_edit",
                "allm_passthrough_route",
            ):
                return await self._ageneric_api_call_with_fallbacks(
                    original_function=original_function,
                    **kwargs,
                )
            elif call_type in (
                "aget_responses",
                "adelete_responses",
                "alist_input_items",
            ):
                return await self._init_responses_api_endpoints(
                    original_function=original_function,
                    **kwargs,
                )
            elif call_type in ("afile_delete", "afile_content"):
                return await self._ageneric_api_call_with_fallbacks(
                    original_function=original_function,
                    custom_llm_provider=custom_llm_provider,
                    client=client,
                    **kwargs,
                )

        return async_wrapper

    async def _init_responses_api_endpoints(
        self,
        original_function: Callable,
        **kwargs,
    ):
        """
        Initialize the Responses API endpoints on the router.

        GET, DELETE Responses API Requests encode the model_id in the response_id, this function decodes the response_id and sets the model to the model_id.
        """
        from litellm.responses.utils import ResponsesAPIRequestUtils

        model_id = ResponsesAPIRequestUtils.get_model_id_from_response_id(
            kwargs.get("response_id")
        )
        if model_id is not None:
            kwargs["model"] = model_id
        return await self._ageneric_api_call_with_fallbacks(
            original_function=original_function,
            **kwargs,
        )

    async def _pass_through_assistants_endpoint_factory(
        self,
        original_function: Callable,
        custom_llm_provider: Optional[Literal["openai", "azure", "anthropic"]] = None,
        client: Optional[AsyncOpenAI] = None,
        **kwargs,
    ):
        """Internal helper function to pass through the assistants endpoint"""
        if custom_llm_provider is None:
            if self.assistants_config is not None:
                custom_llm_provider = self.assistants_config["custom_llm_provider"]
                kwargs.update(self.assistants_config["litellm_params"])
            else:
                raise Exception(
                    "'custom_llm_provider' must be set. Either via:\n `Router(assistants_config={'custom_llm_provider': ..})` \nor\n `router.arun_thread(custom_llm_provider=..)`"
                )
        return await original_function(  # type: ignore
            custom_llm_provider=custom_llm_provider, client=client, **kwargs
        )

    #### [END] ASSISTANTS API ####

    @tracer.wrap()
    async def async_function_with_fallbacks(self, *args, **kwargs):  # noqa: PLR0915
        """
        Try calling the function_with_retries
        If it fails after num_retries, fall back to another model group
        """
        model_group: Optional[str] = kwargs.get("model")
        disable_fallbacks: Optional[bool] = kwargs.pop("disable_fallbacks", False)
        fallbacks: Optional[List] = kwargs.get("fallbacks", self.fallbacks)
        context_window_fallbacks: Optional[List] = kwargs.get(
            "context_window_fallbacks", self.context_window_fallbacks
        )
        content_policy_fallbacks: Optional[List] = kwargs.get(
            "content_policy_fallbacks", self.content_policy_fallbacks
        )

        mock_timeout = kwargs.pop("mock_timeout", None)

        try:
            self._handle_mock_testing_fallbacks(
                kwargs=kwargs,
                model_group=model_group,
                fallbacks=fallbacks,
                context_window_fallbacks=context_window_fallbacks,
                content_policy_fallbacks=content_policy_fallbacks,
            )

            if mock_timeout is not None:
                response = await self.async_function_with_retries(
                    *args, **kwargs, mock_timeout=mock_timeout
                )
            else:
                response = await self.async_function_with_retries(*args, **kwargs)
            verbose_router_logger.debug(f"Async Response: {response}")
            response = add_fallback_headers_to_response(
                response=response,
                attempted_fallbacks=0,
            )
            return response
        except Exception as e:
            verbose_router_logger.debug(f"Traceback{traceback.format_exc()}")
            original_exception = e
            fallback_model_group = None
            original_model_group: Optional[str] = kwargs.get("model")  # type: ignore
            fallback_failure_exception_str = ""

            if disable_fallbacks is True or original_model_group is None:
                raise e

            input_kwargs = {
                "litellm_router": self,
                "original_exception": original_exception,
                **kwargs,
            }

            if "max_fallbacks" not in input_kwargs:
                input_kwargs["max_fallbacks"] = self.max_fallbacks
            if "fallback_depth" not in input_kwargs:
                input_kwargs["fallback_depth"] = 0

            try:
                verbose_router_logger.info("Trying to fallback b/w models")

                # check if client-side fallbacks are used (e.g. fallbacks = ["gpt-3.5-turbo", "claude-3-haiku"] or fallbacks=[{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hey, how's it going?"}]}]
                is_non_standard_fallback_format = _check_non_standard_fallback_format(
                    fallbacks=fallbacks
                )

                if is_non_standard_fallback_format:
                    input_kwargs.update(
                        {
                            "fallback_model_group": fallbacks,
                            "original_model_group": original_model_group,
                        }
                    )

                    response = await run_async_fallback(
                        *args,
                        **input_kwargs,
                    )

                    return response

                if isinstance(e, litellm.ContextWindowExceededError):
                    if context_window_fallbacks is not None:
                        fallback_model_group: Optional[List[str]] = (
                            self._get_fallback_model_group_from_fallbacks(
                                fallbacks=context_window_fallbacks,
                                model_group=model_group,
                            )
                        )
                        if fallback_model_group is None:
                            raise original_exception

                        input_kwargs.update(
                            {
                                "fallback_model_group": fallback_model_group,
                                "original_model_group": original_model_group,
                            }
                        )

                        response = await run_async_fallback(
                            *args,
                            **input_kwargs,
                        )
                        return response

                    else:
                        error_message = "model={}. context_window_fallbacks={}. fallbacks={}.\n\nSet 'context_window_fallback' - https://docs.litellm.ai/docs/routing#fallbacks".format(
                            model_group, context_window_fallbacks, fallbacks
                        )
                        verbose_router_logger.info(
                            msg="Got 'ContextWindowExceededError'. No context_window_fallback set. Defaulting \
                            to fallbacks, if available.{}".format(
                                error_message
                            )
                        )

                        e.message += "\n{}".format(error_message)
                elif isinstance(e, litellm.ContentPolicyViolationError):
                    if content_policy_fallbacks is not None:
                        fallback_model_group: Optional[List[str]] = (
                            self._get_fallback_model_group_from_fallbacks(
                                fallbacks=content_policy_fallbacks,
                                model_group=model_group,
                            )
                        )
                        if fallback_model_group is None:
                            raise original_exception

                        input_kwargs.update(
                            {
                                "fallback_model_group": fallback_model_group,
                                "original_model_group": original_model_group,
                            }
                        )

                        response = await run_async_fallback(
                            *args,
                            **input_kwargs,
                        )
                        return response
                    else:
                        error_message = "model={}. content_policy_fallback={}. fallbacks={}.\n\nSet 'content_policy_fallback' - https://docs.litellm.ai/docs/routing#fallbacks".format(
                            model_group, content_policy_fallbacks, fallbacks
                        )
                        verbose_router_logger.info(
                            msg="Got 'ContentPolicyViolationError'. No content_policy_fallback set. Defaulting \
                            to fallbacks, if available.{}".format(
                                error_message
                            )
                        )

                        e.message += "\n{}".format(error_message)
                if fallbacks is not None and model_group is not None:
                    verbose_router_logger.debug(f"inside model fallbacks: {fallbacks}")
                    (
                        fallback_model_group,
                        generic_fallback_idx,
                    ) = get_fallback_model_group(
                        fallbacks=fallbacks,  # if fallbacks = [{"gpt-3.5-turbo": ["claude-3-haiku"]}]
                        model_group=cast(str, model_group),
                    )
                    ## if none, check for generic fallback
                    if (
                        fallback_model_group is None
                        and generic_fallback_idx is not None
                    ):
                        fallback_model_group = fallbacks[generic_fallback_idx]["*"]

                    if fallback_model_group is None:
                        verbose_router_logger.info(
                            f"No fallback model group found for original model_group={model_group}. Fallbacks={fallbacks}"
                        )
                        if hasattr(original_exception, "message"):
                            original_exception.message += f"No fallback model group found for original model_group={model_group}. Fallbacks={fallbacks}"  # type: ignore
                        raise original_exception

                    input_kwargs.update(
                        {
                            "fallback_model_group": fallback_model_group,
                            "original_model_group": original_model_group,
                        }
                    )

                    response = await run_async_fallback(
                        *args,
                        **input_kwargs,
                    )

                    return response
            except Exception as new_exception:
                parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
                verbose_router_logger.error(
                    "litellm.router.py::async_function_with_fallbacks() - Error occurred while trying to do fallbacks - {}\n{}\n\nDebug Information:\nCooldown Deployments={}".format(
                        str(new_exception),
                        traceback.format_exc(),
                        await _async_get_cooldown_deployments_with_debug_info(
                            litellm_router_instance=self,
                            parent_otel_span=parent_otel_span,
                        ),
                    )
                )
                fallback_failure_exception_str = str(new_exception)

            if hasattr(original_exception, "message"):
                # add the available fallbacks to the exception
                original_exception.message += ". Received Model Group={}\nAvailable Model Group Fallbacks={}".format(  # type: ignore
                    model_group,
                    fallback_model_group,
                )
                if len(fallback_failure_exception_str) > 0:
                    original_exception.message += (  # type: ignore
                        "\nError doing the fallback: {}".format(
                            fallback_failure_exception_str
                        )
                    )

            raise original_exception

    def _handle_mock_testing_fallbacks(
        self,
        kwargs: dict,
        model_group: Optional[str] = None,
        fallbacks: Optional[List] = None,
        context_window_fallbacks: Optional[List] = None,
        content_policy_fallbacks: Optional[List] = None,
    ):
        """
        Helper function to raise a litellm Error for mock testing purposes.

        Raises:
            litellm.InternalServerError: when `mock_testing_fallbacks=True` passed in request params
            litellm.ContextWindowExceededError: when `mock_testing_context_fallbacks=True` passed in request params
            litellm.ContentPolicyViolationError: when `mock_testing_content_policy_fallbacks=True` passed in request params
        """
        mock_testing_fallbacks = kwargs.pop("mock_testing_fallbacks", None)
        mock_testing_context_fallbacks = kwargs.pop(
            "mock_testing_context_fallbacks", None
        )
        mock_testing_content_policy_fallbacks = kwargs.pop(
            "mock_testing_content_policy_fallbacks", None
        )

        if mock_testing_fallbacks is not None and mock_testing_fallbacks is True:
            raise litellm.InternalServerError(
                model=model_group,
                llm_provider="",
                message=f"This is a mock exception for model={model_group}, to trigger a fallback. Fallbacks={fallbacks}",
            )
        elif (
            mock_testing_context_fallbacks is not None
            and mock_testing_context_fallbacks is True
        ):
            raise litellm.ContextWindowExceededError(
                model=model_group,
                llm_provider="",
                message=f"This is a mock exception for model={model_group}, to trigger a fallback. \
                    Context_Window_Fallbacks={context_window_fallbacks}",
            )
        elif (
            mock_testing_content_policy_fallbacks is not None
            and mock_testing_content_policy_fallbacks is True
        ):
            raise litellm.ContentPolicyViolationError(
                model=model_group,
                llm_provider="",
                message=f"This is a mock exception for model={model_group}, to trigger a fallback. \
                    Context_Policy_Fallbacks={content_policy_fallbacks}",
            )

    @tracer.wrap()
    async def async_function_with_retries(self, *args, **kwargs):  # noqa: PLR0915
        verbose_router_logger.debug("Inside async function with retries.")
        original_function = kwargs.pop("original_function")
        fallbacks = kwargs.pop("fallbacks", self.fallbacks)
        parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
        context_window_fallbacks = kwargs.pop(
            "context_window_fallbacks", self.context_window_fallbacks
        )
        content_policy_fallbacks = kwargs.pop(
            "content_policy_fallbacks", self.content_policy_fallbacks
        )
        model_group: Optional[str] = kwargs.get("model")
        num_retries = kwargs.pop("num_retries")

        ## ADD MODEL GROUP SIZE TO METADATA - used for model_group_rate_limit_error tracking
        _metadata: dict = kwargs.get("litellm_metadata", kwargs.get("metadata")) or {}
        if "model_group" in _metadata and isinstance(_metadata["model_group"], str):
            model_list = self.get_model_list(model_name=_metadata["model_group"])
            if model_list is not None:
                _metadata.update({"model_group_size": len(model_list)})

        verbose_router_logger.debug(
            f"async function w/ retries: original_function - {original_function}, num_retries - {num_retries}"
        )
        try:
            self._handle_mock_testing_rate_limit_error(
                model_group=model_group, kwargs=kwargs
            )
            # if the function call is successful, no exception will be raised and we'll break out of the loop
            response = await self.make_call(original_function, *args, **kwargs)
            response = add_retry_headers_to_response(
                response=response, attempted_retries=0, max_retries=None
            )
            return response
        except Exception as e:
            current_attempt = None
            original_exception = e
            deployment_num_retries = getattr(e, "num_retries", None)

            if deployment_num_retries is not None and isinstance(
                deployment_num_retries, int
            ):
                num_retries = deployment_num_retries
            """
            Retry Logic
            """
            (
                _healthy_deployments,
                _all_deployments,
            ) = await self._async_get_healthy_deployments(
                model=kwargs.get("model") or "",
                parent_otel_span=parent_otel_span,
            )

            # raises an exception if this error should not be retries
            self.should_retry_this_error(
                error=e,
                healthy_deployments=_healthy_deployments,
                all_deployments=_all_deployments,
                context_window_fallbacks=context_window_fallbacks,
                regular_fallbacks=fallbacks,
                content_policy_fallbacks=content_policy_fallbacks,
            )

            if (
                self.retry_policy is not None
                or self.model_group_retry_policy is not None
            ):
                # get num_retries from retry policy
                _retry_policy_retries = self.get_num_retries_from_retry_policy(
                    exception=original_exception, model_group=kwargs.get("model")
                )
                if _retry_policy_retries is not None:
                    num_retries = _retry_policy_retries
            ## LOGGING
            if num_retries > 0:
                kwargs = self.log_retry(kwargs=kwargs, e=original_exception)
            else:
                raise

            verbose_router_logger.info(
                f"Retrying request with num_retries: {num_retries}"
            )
            # decides how long to sleep before retry
            retry_after = self._time_to_sleep_before_retry(
                e=original_exception,
                remaining_retries=num_retries,
                num_retries=num_retries,
                healthy_deployments=_healthy_deployments,
                all_deployments=_all_deployments,
            )

            await asyncio.sleep(retry_after)

            for current_attempt in range(num_retries):
                try:
                    # if the function call is successful, no exception will be raised and we'll break out of the loop
                    response = await self.make_call(original_function, *args, **kwargs)
                    if inspect.iscoroutinefunction(
                        response
                    ):  # async errors are often returned as coroutines
                        response = await response

                    response = add_retry_headers_to_response(
                        response=response,
                        attempted_retries=current_attempt + 1,
                        max_retries=num_retries,
                    )
                    return response

                except Exception as e:
                    ## LOGGING
                    kwargs = self.log_retry(kwargs=kwargs, e=e)
                    remaining_retries = num_retries - current_attempt
                    _model: Optional[str] = kwargs.get("model")  # type: ignore
                    if _model is not None:
                        (
                            _healthy_deployments,
                            _,
                        ) = await self._async_get_healthy_deployments(
                            model=_model,
                            parent_otel_span=parent_otel_span,
                        )
                    else:
                        _healthy_deployments = []
                    _timeout = self._time_to_sleep_before_retry(
                        e=original_exception,
                        remaining_retries=remaining_retries,
                        num_retries=num_retries,
                        healthy_deployments=_healthy_deployments,
                        all_deployments=_all_deployments,
                    )
                    await asyncio.sleep(_timeout)

            if type(original_exception) in litellm.LITELLM_EXCEPTION_TYPES:
                setattr(original_exception, "max_retries", num_retries)
                setattr(original_exception, "num_retries", current_attempt)

            raise original_exception

    async def make_call(self, original_function: Any, *args, **kwargs):
        """
        Handler for making a call to the .completion()/.embeddings()/etc. functions.
        """
        model_group = kwargs.get("model")
        response = original_function(*args, **kwargs)
        if inspect.iscoroutinefunction(response) or inspect.isawaitable(response):
            response = await response
        ## PROCESS RESPONSE HEADERS
        response = await self.set_response_headers(
            response=response, model_group=model_group
        )

        return response

    def _handle_mock_testing_rate_limit_error(
        self, kwargs: dict, model_group: Optional[str] = None
    ):
        """
        Helper function to raise a mock litellm.RateLimitError error for testing purposes.

        Raises:
            litellm.RateLimitError error when `mock_testing_rate_limit_error=True` passed in request params
        """
        mock_testing_rate_limit_error: Optional[bool] = kwargs.pop(
            "mock_testing_rate_limit_error", None
        )

        available_models = self.get_model_list(model_name=model_group)
        num_retries: Optional[int] = None

        if available_models is not None and len(available_models) == 1:
            num_retries = cast(
                Optional[int], available_models[0]["litellm_params"].get("num_retries")
            )

        if (
            mock_testing_rate_limit_error is not None
            and mock_testing_rate_limit_error is True
        ):
            verbose_router_logger.info(
                f"litellm.router.py::_mock_rate_limit_error() - Raising mock RateLimitError for model={model_group}"
            )
            raise litellm.RateLimitError(
                model=model_group,
                llm_provider="",
                message=f"This is a mock exception for model={model_group}, to trigger a rate limit error.",
                num_retries=num_retries,
            )

    def should_retry_this_error(
        self,
        error: Exception,
        healthy_deployments: Optional[List] = None,
        all_deployments: Optional[List] = None,
        context_window_fallbacks: Optional[List] = None,
        content_policy_fallbacks: Optional[List] = None,
        regular_fallbacks: Optional[List] = None,
    ):
        """
        1. raise an exception for ContextWindowExceededError if context_window_fallbacks is not None
        2. raise an exception for ContentPolicyViolationError if content_policy_fallbacks is not None

        2. raise an exception for RateLimitError if
            - there are no fallbacks
            - there are no healthy deployments in the same model group
        """
        _num_healthy_deployments = 0
        if healthy_deployments is not None and isinstance(healthy_deployments, list):
            _num_healthy_deployments = len(healthy_deployments)

        _num_all_deployments = 0
        if all_deployments is not None and isinstance(all_deployments, list):
            _num_all_deployments = len(all_deployments)

        ### CHECK IF RATE LIMIT / CONTEXT WINDOW ERROR / CONTENT POLICY VIOLATION ERROR w/ fallbacks available / Bad Request Error
        if (
            isinstance(error, litellm.ContextWindowExceededError)
            and context_window_fallbacks is not None
        ):
            raise error

        if (
            isinstance(error, litellm.ContentPolicyViolationError)
            and content_policy_fallbacks is not None
        ):
            raise error

        if isinstance(error, litellm.NotFoundError):
            raise error
        # Error we should only retry if there are other deployments
        if isinstance(error, openai.RateLimitError):
            if (
                _num_healthy_deployments <= 0  # if no healthy deployments
                and regular_fallbacks is not None  # and fallbacks available
                and len(regular_fallbacks) > 0
            ):
                raise error  # then raise the error

        if isinstance(error, openai.AuthenticationError):
            """
            - if other deployments available -> retry
            - else -> raise error
            """
            if (
                _num_all_deployments <= 1
            ):  # if there is only 1 deployment for this model group then don't retry
                raise error  # then raise error

        # Do not retry if there are no healthy deployments
        # just raise the error
        if _num_healthy_deployments <= 0:  # if no healthy deployments
            raise error

        return True

    def function_with_fallbacks(self, *args, **kwargs):
        """
        Sync wrapper for async_function_with_fallbacks

        Wrapped to reduce code duplication and prevent bugs.
        """
        return run_async_function(self.async_function_with_fallbacks, *args, **kwargs)

    def _get_fallback_model_group_from_fallbacks(
        self,
        fallbacks: List[Dict[str, List[str]]],
        model_group: Optional[str] = None,
    ) -> Optional[List[str]]:
        """
        Returns the list of fallback models to use for a given model group

        If no fallback model group is found, returns None

        Example:
            fallbacks = [{"gpt-3.5-turbo": ["gpt-4"]}, {"gpt-4o": ["gpt-3.5-turbo"]}]
            model_group = "gpt-3.5-turbo"
            returns: ["gpt-4"]
        """
        if model_group is None:
            return None

        fallback_model_group: Optional[List[str]] = None
        for item in fallbacks:  # [{"gpt-3.5-turbo": ["gpt-4"]}]
            if list(item.keys())[0] == model_group:
                fallback_model_group = item[model_group]
                break
        return fallback_model_group

    def _time_to_sleep_before_retry(
        self,
        e: Exception,
        remaining_retries: int,
        num_retries: int,
        healthy_deployments: Optional[List] = None,
        all_deployments: Optional[List] = None,
    ) -> Union[int, float]:
        """
        Calculate back-off, then retry

        It should instantly retry only when:
            1. there are healthy deployments in the same model group
            2. there are fallbacks for the completion call
        """

        ## base case - single deployment
        if all_deployments is not None and len(all_deployments) == 1:
            pass
        elif (
            healthy_deployments is not None
            and isinstance(healthy_deployments, list)
            and len(healthy_deployments) > 0
        ):
            return 0

        response_headers: Optional[httpx.Headers] = None
        if hasattr(e, "response") and hasattr(e.response, "headers"):  # type: ignore
            response_headers = e.response.headers  # type: ignore
        if hasattr(e, "litellm_response_headers"):
            response_headers = e.litellm_response_headers  # type: ignore

        if response_headers is not None:
            timeout = litellm._calculate_retry_after(
                remaining_retries=remaining_retries,
                max_retries=num_retries,
                response_headers=response_headers,
                min_timeout=self.retry_after,
            )

        else:
            timeout = litellm._calculate_retry_after(
                remaining_retries=remaining_retries,
                max_retries=num_retries,
                min_timeout=self.retry_after,
            )

        return timeout

    ### HELPER FUNCTIONS

    async def deployment_callback_on_success(
        self,
        kwargs,  # kwargs to completion
        completion_response,  # response from completion
        start_time,
        end_time,  # start/end time
    ):
        """
        Track remaining tpm/rpm quota for model in model_list
        """
        try:
            standard_logging_object: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object", None
            )
            if standard_logging_object is None:
                raise ValueError("standard_logging_object is None")
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                deployment_name = kwargs["litellm_params"]["metadata"].get(
                    "deployment", None
                )  # stable name - works for wildcard routes as well
                model_group = standard_logging_object.get("model_group", None)
                id = standard_logging_object.get("model_id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
                total_tokens: float = standard_logging_object.get("total_tokens", 0)

                # ------------
                # Setup values
                # ------------
                dt = get_utc_datetime()
                current_minute = dt.strftime(
                    "%H-%M"
                )  # use the same timezone regardless of system clock

                tpm_key = RouterCacheEnum.TPM.value.format(
                    id=id, current_minute=current_minute, model=deployment_name
                )
                # ------------
                # Update usage
                # ------------
                # update cache

                ## TPM
                await self.cache.async_increment_cache(
                    key=tpm_key,
                    value=total_tokens,
                    parent_otel_span=parent_otel_span,
                    ttl=RoutingArgs.ttl.value,
                )

                ## RPM
                rpm_key = RouterCacheEnum.RPM.value.format(
                    id=id, current_minute=current_minute, model=deployment_name
                )
                await self.cache.async_increment_cache(
                    key=rpm_key,
                    value=1,
                    parent_otel_span=parent_otel_span,
                    ttl=RoutingArgs.ttl.value,
                )

                increment_deployment_successes_for_current_minute(
                    litellm_router_instance=self,
                    deployment_id=id,
                )

                return tpm_key

        except Exception as e:
            verbose_router_logger.exception(
                "litellm.router.Router::deployment_callback_on_success(): Exception occured - {}".format(
                    str(e)
                )
            )
            pass

    def sync_deployment_callback_on_success(
        self,
        kwargs,  # kwargs to completion
        completion_response,  # response from completion
        start_time,
        end_time,  # start/end time
    ) -> Optional[str]:
        """
        Tracks the number of successes for a deployment in the current minute (using in-memory cache)

        Returns:
        - key: str - The key used to increment the cache
        - None: if no key is found
        """
        id = None
        if kwargs["litellm_params"].get("metadata") is None:
            pass
        else:
            model_group = kwargs["litellm_params"]["metadata"].get("model_group", None)
            model_info = kwargs["litellm_params"].get("model_info", {}) or {}
            id = model_info.get("id", None)
            if model_group is None or id is None:
                return None
            elif isinstance(id, int):
                id = str(id)

        if id is not None:
            key = increment_deployment_successes_for_current_minute(
                litellm_router_instance=self,
                deployment_id=id,
            )
            return key

        return None

    def deployment_callback_on_failure(
        self,
        kwargs,  # kwargs to completion
        completion_response,  # response from completion
        start_time,
        end_time,  # start/end time
    ) -> bool:
        """
        2 jobs:
        - Tracks the number of failures for a deployment in the current minute (using in-memory cache)
        - Puts the deployment in cooldown if it exceeds the allowed fails / minute

        Returns:
        - True if the deployment should be put in cooldown
        - False if the deployment should not be put in cooldown
        """
        verbose_router_logger.debug("Router: Entering 'deployment_callback_on_failure'")
        try:
            exception = kwargs.get("exception", None)
            exception_status = getattr(exception, "status_code", "")
            _model_info = kwargs.get("litellm_params", {}).get("model_info", {})

            exception_headers = litellm.litellm_core_utils.exception_mapping_utils._get_response_headers(
                original_exception=exception
            )

            _time_to_cooldown = kwargs.get("litellm_params", {}).get(
                "cooldown_time", self.cooldown_time
            )

            if exception_headers is not None:
                _time_to_cooldown = (
                    litellm.utils._get_retry_after_from_exception_header(
                        response_headers=exception_headers
                    )
                )

                if _time_to_cooldown is None or _time_to_cooldown < 0:
                    # if the response headers did not read it -> set to default cooldown time
                    _time_to_cooldown = self.cooldown_time

            if isinstance(_model_info, dict):
                deployment_id = _model_info.get("id", None)
                increment_deployment_failures_for_current_minute(
                    litellm_router_instance=self,
                    deployment_id=deployment_id,
                )
                result = _set_cooldown_deployments(
                    litellm_router_instance=self,
                    exception_status=exception_status,
                    original_exception=exception,
                    deployment=deployment_id,
                    time_to_cooldown=_time_to_cooldown,
                )  # setting deployment_id in cooldown deployments

                return result
            else:
                verbose_router_logger.debug(
                    "Router: Exiting 'deployment_callback_on_failure' without cooldown. No model_info found."
                )
                return False

        except Exception as e:
            raise e

    async def async_deployment_callback_on_failure(
        self, kwargs, completion_response: Optional[Any], start_time, end_time
    ):
        """
        Update RPM usage for a deployment
        """
        deployment_name = kwargs["litellm_params"]["metadata"].get(
            "deployment", None
        )  # handles wildcard routes - by giving the original name sent to `litellm.completion`
        model_group = kwargs["litellm_params"]["metadata"].get("model_group", None)
        model_info = kwargs["litellm_params"].get("model_info", {}) or {}
        id = model_info.get("id", None)
        if model_group is None or id is None:
            return
        elif isinstance(id, int):
            id = str(id)
        parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)

        dt = get_utc_datetime()
        current_minute = dt.strftime(
            "%H-%M"
        )  # use the same timezone regardless of system clock

        ## RPM
        rpm_key = RouterCacheEnum.RPM.value.format(
            id=id, current_minute=current_minute, model=deployment_name
        )
        await self.cache.async_increment_cache(
            key=rpm_key,
            value=1,
            parent_otel_span=parent_otel_span,
            ttl=RoutingArgs.ttl.value,
        )

    def log_retry(self, kwargs: dict, e: Exception) -> dict:
        """
        When a retry or fallback happens, log the details of the just failed model call - similar to Sentry breadcrumbing
        """
        try:
            # Log failed model as the previous model
            previous_model = {
                "exception_type": type(e).__name__,
                "exception_string": str(e),
            }
            for (
                k,
                v,
            ) in (
                kwargs.items()
            ):  # log everything in kwargs except the old previous_models value - prevent nesting
                if k not in ["metadata", "messages", "original_function"]:
                    previous_model[k] = v
                elif k == "metadata" and isinstance(v, dict):
                    previous_model["metadata"] = {}  # type: ignore
                    for metadata_k, metadata_v in kwargs["metadata"].items():
                        if metadata_k != "previous_models":
                            previous_model[k][metadata_k] = metadata_v  # type: ignore

            # check current size of self.previous_models, if it's larger than 3, remove the first element
            if len(self.previous_models) > 3:
                self.previous_models.pop(0)

            self.previous_models.append(previous_model)
            kwargs["metadata"]["previous_models"] = self.previous_models
            return kwargs
        except Exception as e:
            raise e

    def _update_usage(
        self, deployment_id: str, parent_otel_span: Optional[Span]
    ) -> int:
        """
        Update deployment rpm for that minute

        Returns:
        - int: request count
        """
        rpm_key = deployment_id

        request_count = self.cache.get_cache(
            key=rpm_key, parent_otel_span=parent_otel_span, local_only=True
        )
        if request_count is None:
            request_count = 1
            self.cache.set_cache(
                key=rpm_key, value=request_count, local_only=True, ttl=60
            )  # only store for 60s
        else:
            request_count += 1
            self.cache.set_cache(
                key=rpm_key, value=request_count, local_only=True
            )  # don't change existing ttl

        return request_count

    def _has_default_fallbacks(self) -> bool:
        if self.fallbacks is None:
            return False
        for fallback in self.fallbacks:
            if isinstance(fallback, dict):
                if "*" in fallback:
                    return True
        return False

    def _should_raise_content_policy_error(
        self, model: str, response: ModelResponse, kwargs: dict
    ) -> bool:
        """
        Determines if a content policy error should be raised.

        Only raised if a fallback is available.

        Else, original response is returned.
        """
        if response.choices and len(response.choices) > 0:
            if response.choices[0].finish_reason != "content_filter":
                return False

        content_policy_fallbacks = kwargs.get(
            "content_policy_fallbacks", self.content_policy_fallbacks
        )

        ### ONLY RAISE ERROR IF CP FALLBACK AVAILABLE ###
        if content_policy_fallbacks is not None:
            fallback_model_group = None
            for item in content_policy_fallbacks:  # [{"gpt-3.5-turbo": ["gpt-4"]}]
                if list(item.keys())[0] == model:
                    fallback_model_group = item[model]
                    break

            if fallback_model_group is not None:
                return True
        elif self._has_default_fallbacks():  # default fallbacks set
            return True

        verbose_router_logger.info(
            "Content Policy Error occurred. No available fallbacks. Returning original response. model={}, content_policy_fallbacks={}".format(
                model, content_policy_fallbacks
            )
        )
        return False

    def _get_healthy_deployments(self, model: str, parent_otel_span: Optional[Span]):
        _all_deployments: list = []
        try:
            _, _all_deployments = self._common_checks_available_deployment(  # type: ignore
                model=model,
            )
            if isinstance(_all_deployments, dict):
                return []
        except Exception:
            pass

        unhealthy_deployments = _get_cooldown_deployments(
            litellm_router_instance=self, parent_otel_span=parent_otel_span
        )
        healthy_deployments: list = []
        for deployment in _all_deployments:
            if deployment["model_info"]["id"] in unhealthy_deployments:
                continue
            else:
                healthy_deployments.append(deployment)

        return healthy_deployments, _all_deployments

    async def _async_get_healthy_deployments(
        self, model: str, parent_otel_span: Optional[Span]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Returns Tuple of:
        - Tuple[List[Dict], List[Dict]]:
            1. healthy_deployments: list of healthy deployments
            2. all_deployments: list of all deployments
        """
        _all_deployments: list = []
        try:
            _, _all_deployments = self._common_checks_available_deployment(  # type: ignore
                model=model,
            )
            if isinstance(_all_deployments, dict):
                return [], _all_deployments
        except Exception:
            pass

        unhealthy_deployments = await _async_get_cooldown_deployments(
            litellm_router_instance=self, parent_otel_span=parent_otel_span
        )
        healthy_deployments: list = []
        for deployment in _all_deployments:
            if deployment["model_info"]["id"] in unhealthy_deployments:
                continue
            else:
                healthy_deployments.append(deployment)
        return healthy_deployments, _all_deployments

    def routing_strategy_pre_call_checks(self, deployment: dict):
        """
        Mimics 'async_routing_strategy_pre_call_checks'

        Ensures consistent update rpm implementation for 'usage-based-routing-v2'

        Returns:
        - None

        Raises:
        - Rate Limit Exception - If the deployment is over it's tpm/rpm limits
        """
        for _callback in litellm.callbacks:
            if isinstance(_callback, CustomLogger):
                _callback.pre_call_check(deployment)

    async def async_routing_strategy_pre_call_checks(
        self,
        deployment: dict,
        parent_otel_span: Optional[Span],
        logging_obj: Optional[LiteLLMLogging] = None,
    ):
        """
        For usage-based-routing-v2, enables running rpm checks before the call is made, inside the semaphore.

        -> makes the calls concurrency-safe, when rpm limits are set for a deployment

        Returns:
        - None

        Raises:
        - Rate Limit Exception - If the deployment is over it's tpm/rpm limits
        """
        for _callback in litellm.callbacks:
            if isinstance(_callback, CustomLogger):
                try:
                    await _callback.async_pre_call_check(deployment, parent_otel_span)
                except litellm.RateLimitError as e:
                    ## LOG FAILURE EVENT
                    if logging_obj is not None:
                        asyncio.create_task(
                            logging_obj.async_failure_handler(
                                exception=e,
                                traceback_exception=traceback.format_exc(),
                                end_time=time.time(),
                            )
                        )
                        ## LOGGING
                        threading.Thread(
                            target=logging_obj.failure_handler,
                            args=(e, traceback.format_exc()),
                        ).start()  # log response
                    _set_cooldown_deployments(
                        litellm_router_instance=self,
                        exception_status=e.status_code,
                        original_exception=e,
                        deployment=deployment["model_info"]["id"],
                        time_to_cooldown=self.cooldown_time,
                    )
                    raise e
                except Exception as e:
                    ## LOG FAILURE EVENT
                    if logging_obj is not None:
                        asyncio.create_task(
                            logging_obj.async_failure_handler(
                                exception=e,
                                traceback_exception=traceback.format_exc(),
                                end_time=time.time(),
                            )
                        )
                        ## LOGGING
                        threading.Thread(
                            target=logging_obj.failure_handler,
                            args=(e, traceback.format_exc()),
                        ).start()  # log response
                    raise e

    async def async_callback_filter_deployments(
        self,
        model: str,
        healthy_deployments: List[dict],
        messages: Optional[List[AllMessageValues]],
        parent_otel_span: Optional[Span],
        request_kwargs: Optional[dict] = None,
        logging_obj: Optional[LiteLLMLogging] = None,
    ):
        """
        For usage-based-routing-v2, enables running rpm checks before the call is made, inside the semaphore.

        -> makes the calls concurrency-safe, when rpm limits are set for a deployment

        Returns:
        - None

        Raises:
        - Rate Limit Exception - If the deployment is over it's tpm/rpm limits
        """
        returned_healthy_deployments = healthy_deployments
        for _callback in litellm.callbacks:
            if isinstance(_callback, CustomLogger):
                try:
                    returned_healthy_deployments = (
                        await _callback.async_filter_deployments(
                            model=model,
                            healthy_deployments=returned_healthy_deployments,
                            messages=messages,
                            request_kwargs=request_kwargs,
                            parent_otel_span=parent_otel_span,
                        )
                    )
                except Exception as e:
                    ## LOG FAILURE EVENT
                    if logging_obj is not None:
                        asyncio.create_task(
                            logging_obj.async_failure_handler(
                                exception=e,
                                traceback_exception=traceback.format_exc(),
                                end_time=time.time(),
                            )
                        )
                        ## LOGGING
                        threading.Thread(
                            target=logging_obj.failure_handler,
                            args=(e, traceback.format_exc()),
                        ).start()  # log response
                    raise e
        return returned_healthy_deployments

    def _generate_model_id(self, model_group: str, litellm_params: dict):
        """
        Helper function to consistently generate the same id for a deployment

        - create a string from all the litellm params
        - hash
        - use hash as id
        """
        concat_str = model_group
        for k, v in litellm_params.items():
            if isinstance(k, str):
                concat_str += k
            elif isinstance(k, dict):
                concat_str += json.dumps(k)
            else:
                concat_str += str(k)

            if isinstance(v, str):
                concat_str += v
            elif isinstance(v, dict):
                concat_str += json.dumps(v)
            else:
                concat_str += str(v)

        hash_object = hashlib.sha256(concat_str.encode())

        return hash_object.hexdigest()

    def _create_deployment(
        self,
        deployment_info: dict,
        _model_name: str,
        _litellm_params: dict,
        _model_info: dict,
    ) -> Optional[Deployment]:
        """
        Create a deployment object and add it to the model list

        If the deployment is not active for the current environment, it is ignored

        Returns:
        - Deployment: The deployment object
        - None: If the deployment is not active for the current environment (if 'supported_environments' is set in litellm_params)
        """
        try:
            deployment = Deployment(
                **deployment_info,
                model_name=_model_name,
                litellm_params=LiteLLM_Params(**_litellm_params),
                model_info=_model_info,
            )
            for field in CustomPricingLiteLLMParams.model_fields.keys():
                if deployment.litellm_params.get(field) is not None:
                    _model_info[field] = deployment.litellm_params[field]

            ## REGISTER MODEL INFO IN LITELLM MODEL COST MAP
            model_id = deployment.model_info.id
            if model_id is not None:
                litellm.register_model(
                    model_cost={
                        model_id: _model_info,
                    }
                )

            ## OLD MODEL REGISTRATION ## Kept to prevent breaking changes
            _model_name = deployment.litellm_params.model
            if deployment.litellm_params.custom_llm_provider is not None:
                _model_name = (
                    deployment.litellm_params.custom_llm_provider + "/" + _model_name
                )

            litellm.register_model(
                model_cost={
                    _model_name: _model_info,
                }
            )

            ## Check if LLM Deployment is allowed for this deployment
            if (
                self.deployment_is_active_for_environment(deployment=deployment)
                is not True
            ):
                verbose_router_logger.warning(
                    f"Ignoring deployment {deployment.model_name} as it is not active for environment {deployment.model_info['supported_environments']}"
                )
                return None

            deployment = self._add_deployment(deployment=deployment)

            model = deployment.to_json(exclude_none=True)

            self.model_list.append(model)
            return deployment
        except Exception as e:
            if self.ignore_invalid_deployments:
                verbose_router_logger.exception(
                    f"Error creating deployment: {e}, ignoring and continuing with other deployments."
                )
                return None
            else:
                raise e

    def deployment_is_active_for_environment(self, deployment: Deployment) -> bool:
        """
        Function to check if a llm deployment is active for a given environment. Allows using the same config.yaml across multople environments

        Requires `LITELLM_ENVIRONMENT` to be set in .env. Valid values for environment:
            - development
            - staging
            - production

        Raises:
        - ValueError: If LITELLM_ENVIRONMENT is not set in .env or not one of the valid values
        - ValueError: If supported_environments is not set in model_info or not one of the valid values
        """
        if (
            deployment.model_info is None
            or "supported_environments" not in deployment.model_info
            or deployment.model_info["supported_environments"] is None
        ):
            return True
        litellm_environment = get_secret_str(secret_name="LITELLM_ENVIRONMENT")
        if litellm_environment is None:
            raise ValueError(
                "Set 'supported_environments' for model but not 'LITELLM_ENVIRONMENT' set in .env"
            )

        if litellm_environment not in VALID_LITELLM_ENVIRONMENTS:
            raise ValueError(
                f"LITELLM_ENVIRONMENT must be one of {VALID_LITELLM_ENVIRONMENTS}. but set as: {litellm_environment}"
            )

        for _env in deployment.model_info["supported_environments"]:
            if _env not in VALID_LITELLM_ENVIRONMENTS:
                raise ValueError(
                    f"supported_environments must be one of {VALID_LITELLM_ENVIRONMENTS}. but set as: {_env} for deployment: {deployment}"
                )

        if litellm_environment in deployment.model_info["supported_environments"]:
            return True
        return False

    def set_model_list(self, model_list: list):
        original_model_list = copy.deepcopy(model_list)
        self.model_list = []
        # we add api_base/api_key each model so load balancing between azure/gpt on api_base1 and api_base2 works

        for model in original_model_list:
            _model_name = model.pop("model_name")
            _litellm_params = model.pop("litellm_params")
            ## check if litellm params in os.environ
            if isinstance(_litellm_params, dict):
                for k, v in _litellm_params.items():
                    if isinstance(v, str) and v.startswith("os.environ/"):
                        _litellm_params[k] = get_secret(v)

            _model_info: dict = model.pop("model_info", {})

            # check if model info has id
            if "id" not in _model_info:
                _id = self._generate_model_id(_model_name, _litellm_params)
                _model_info["id"] = _id

            if _litellm_params.get("organization", None) is not None and isinstance(
                _litellm_params["organization"], list
            ):  # Addresses https://github.com/BerriAI/litellm/issues/3949
                for org in _litellm_params["organization"]:
                    _litellm_params["organization"] = org
                    self._create_deployment(
                        deployment_info=model,
                        _model_name=_model_name,
                        _litellm_params=_litellm_params,
                        _model_info=_model_info,
                    )
            else:
                self._create_deployment(
                    deployment_info=model,
                    _model_name=_model_name,
                    _litellm_params=_litellm_params,
                    _model_info=_model_info,
                )

        verbose_router_logger.debug(
            f"\nInitialized Model List {self.get_model_names()}"
        )
        self.model_names = [m["model_name"] for m in model_list]

    def _add_deployment(self, deployment: Deployment) -> Deployment:
        import os

        #### DEPLOYMENT NAMES INIT ########
        self.deployment_names.append(deployment.litellm_params.model)
        ############ Users can either pass tpm/rpm as a litellm_param or a router param ###########
        # for get_available_deployment, we use the litellm_param["rpm"]
        # in this snippet we also set rpm to be a litellm_param
        if (
            deployment.litellm_params.rpm is None
            and getattr(deployment, "rpm", None) is not None
        ):
            deployment.litellm_params.rpm = getattr(deployment, "rpm")

        if (
            deployment.litellm_params.tpm is None
            and getattr(deployment, "tpm", None) is not None
        ):
            deployment.litellm_params.tpm = getattr(deployment, "tpm")

        #### VALIDATE MODEL ########
        # check if model provider in supported providers
        (
            _model,
            custom_llm_provider,
            dynamic_api_key,
            api_base,
        ) = litellm.get_llm_provider(
            model=deployment.litellm_params.model,
            custom_llm_provider=deployment.litellm_params.get(
                "custom_llm_provider", None
            ),
        )

        # Check if user is trying to use model_name == "*"
        # this is a catch all model for their specific api key
        # if deployment.model_name == "*":
        #     if deployment.litellm_params.model == "*":
        #         # user wants to pass through all requests to litellm.acompletion for unknown deployments
        #         self.router_general_settings.pass_through_all_models = True
        #     else:
        #         self.default_deployment = deployment.to_json(exclude_none=True)
        # Check if user is using provider specific wildcard routing
        # example model_name = "databricks/*" or model_name = "anthropic/*"
        if "*" in deployment.model_name:
            # store this as a regex pattern - all deployments matching this pattern will be sent to this deployment
            # Store deployment.model_name as a regex pattern
            self.pattern_router.add_pattern(
                deployment.model_name, deployment.to_json(exclude_none=True)
            )
            if deployment.model_info.id:
                self.provider_default_deployment_ids.append(deployment.model_info.id)

        # Azure GPT-Vision Enhancements, users can pass os.environ/
        data_sources = deployment.litellm_params.get("dataSources", []) or []

        for data_source in data_sources:
            params = data_source.get("parameters", {})
            for param_key in ["endpoint", "key"]:
                # if endpoint or key set for Azure GPT Vision Enhancements, check if it's an env var
                if param_key in params and params[param_key].startswith("os.environ/"):
                    env_name = params[param_key].replace("os.environ/", "")
                    params[param_key] = os.environ.get(env_name, "")

        # done reading model["litellm_params"]
        if custom_llm_provider not in litellm.provider_list:
            raise Exception(f"Unsupported provider - {custom_llm_provider}")

        # # init OpenAI, Azure clients
        # InitalizeOpenAISDKClient.set_client(
        #     litellm_router_instance=self, model=deployment.to_json(exclude_none=True)
        # )

        self._initialize_deployment_for_pass_through(
            deployment=deployment,
            custom_llm_provider=custom_llm_provider,
            model=deployment.litellm_params.model,
        )

        return deployment

    def _initialize_deployment_for_pass_through(
        self, deployment: Deployment, custom_llm_provider: str, model: str
    ):
        """
        Optional: Initialize deployment for pass-through endpoints if `deployment.litellm_params.use_in_pass_through` is True

        Each provider uses diff .env vars for pass-through endpoints, this helper uses the deployment credentials to set the .env vars for pass-through endpoints
        """
        if deployment.litellm_params.use_in_pass_through is True:
            from litellm.proxy.pass_through_endpoints.llm_passthrough_endpoints import (
                passthrough_endpoint_router,
            )

            if deployment.litellm_params.litellm_credential_name is not None:
                credential_values = CredentialAccessor.get_credential_values(
                    deployment.litellm_params.litellm_credential_name
                )
            else:
                credential_values = {}

            if custom_llm_provider == "vertex_ai":
                vertex_project = (
                    credential_values.get("vertex_project")
                    or deployment.litellm_params.vertex_project
                )
                vertex_location = (
                    credential_values.get("vertex_location")
                    or deployment.litellm_params.vertex_location
                )
                vertex_credentials = (
                    credential_values.get("vertex_credentials")
                    or deployment.litellm_params.vertex_credentials
                )

                if vertex_project is None or vertex_location is None:
                    raise ValueError(
                        "vertex_project, and vertex_location must be set in litellm_params for pass-through endpoints."
                    )
                passthrough_endpoint_router.add_vertex_credentials(
                    project_id=vertex_project,
                    location=vertex_location,
                    vertex_credentials=vertex_credentials,
                )
            else:
                api_base = (
                    credential_values.get("api_base")
                    or deployment.litellm_params.api_base
                )
                api_key = (
                    credential_values.get("api_key")
                    or deployment.litellm_params.api_key
                )
                passthrough_endpoint_router.set_pass_through_credentials(
                    custom_llm_provider=custom_llm_provider,
                    api_base=api_base,
                    api_key=api_key,
                )
            pass
        pass

    def add_deployment(self, deployment: Deployment) -> Optional[Deployment]:
        """
        Parameters:
        - deployment: Deployment - the deployment to be added to the Router

        Returns:
        - The added deployment
        - OR None (if deployment already exists)
        """
        # check if deployment already exists

        if deployment.model_info.id in self.get_model_ids():
            return None

        # add to model list
        _deployment = deployment.to_json(exclude_none=True)
        # initialize client
        self._add_deployment(deployment=deployment)

        # add to model names
        self.model_list.append(_deployment)
        self.model_names.append(deployment.model_name)
        return deployment

    def upsert_deployment(self, deployment: Deployment) -> Optional[Deployment]:
        """
        Add or update deployment
        Parameters:
        - deployment: Deployment - the deployment to be added to the Router

        Returns:
        - The added/updated deployment
        """
        try:
            # check if deployment already exists
            _deployment_model_id = deployment.model_info.id or ""

            _deployment_on_router: Optional[Deployment] = self.get_deployment(
                model_id=_deployment_model_id
            )
            if _deployment_on_router is not None:
                # deployment with this model_id exists on the router
                if deployment.litellm_params == _deployment_on_router.litellm_params:
                    # No need to update
                    return None

                # if there is a new litellm param -> then update the deployment
                # remove the previous deployment
                removal_idx: Optional[int] = None
                for idx, model in enumerate(self.model_list):
                    if model["model_info"]["id"] == deployment.model_info.id:
                        removal_idx = idx

                if removal_idx is not None:
                    self.model_list.pop(removal_idx)

            # if the model_id is not in router
            self.add_deployment(deployment=deployment)
            return deployment
        except Exception as e:
            if self.ignore_invalid_deployments:
                verbose_router_logger.warning(
                    f"Error upserting deployment: {e}, ignoring and continuing with other deployments."
                )
                return None
            else:
                raise e

    def delete_deployment(self, id: str) -> Optional[Deployment]:
        """
        Parameters:
        - id: str - the id of the deployment to be deleted

        Returns:
        - The deleted deployment
        - OR None (if deleted deployment not found)
        """
        deployment_idx = None
        for idx, m in enumerate(self.model_list):
            if m["model_info"]["id"] == id:
                deployment_idx = idx

        try:
            if deployment_idx is not None:
                item = self.model_list.pop(deployment_idx)
                return item
            else:
                return None
        except Exception:
            return None

    def get_deployment(self, model_id: str) -> Optional[Deployment]:
        """
        Returns -> Deployment or None

        Raise Exception -> if model found in invalid format
        """
        for model in self.model_list:
            if "model_info" in model and "id" in model["model_info"]:
                if model_id == model["model_info"]["id"]:
                    if isinstance(model, dict):
                        return Deployment(**model)
                    elif isinstance(model, Deployment):
                        return model
                    else:
                        raise Exception("Model invalid format - {}".format(type(model)))
        return None

    def get_deployment_credentials(self, model_id: str) -> Optional[dict]:
        """
        Returns -> dict of credentials for a given model id
        """
        deployment = self.get_deployment(model_id=model_id)
        if deployment is None:
            return None
        return CredentialLiteLLMParams(
            **deployment.litellm_params.model_dump(exclude_none=True)
        ).model_dump(exclude_none=True)

    def get_deployment_by_model_group_name(
        self, model_group_name: str
    ) -> Optional[Deployment]:
        """
        Returns -> Deployment or None

        Raise Exception -> if model found in invalid format
        """
        for model in self.model_list:
            if model["model_name"] == model_group_name:
                if isinstance(model, dict):
                    return Deployment(**model)
                elif isinstance(model, Deployment):
                    return model
                else:
                    raise Exception("Model Name invalid - {}".format(type(model)))
        return None

    @overload
    def get_router_model_info(
        self, deployment: dict, received_model_name: str, id: None = None
    ) -> ModelMapInfo:
        pass

    @overload
    def get_router_model_info(
        self, deployment: None, received_model_name: str, id: str
    ) -> ModelMapInfo:
        pass

    def get_router_model_info(
        self,
        deployment: Optional[dict],
        received_model_name: str,
        id: Optional[str] = None,
    ) -> ModelMapInfo:
        """
        For a given model id, return the model info (max tokens, input cost, output cost, etc.).

        Augment litellm info with additional params set in `model_info`.

        For azure models, ignore the `model:`. Only set max tokens, cost values if base_model is set.

        Returns
        - ModelInfo - If found -> typed dict with max tokens, input cost, etc.

        Raises:
        - ValueError -> If model is not mapped yet
        """
        if id is not None:
            _deployment = self.get_deployment(model_id=id)
            if _deployment is not None:
                deployment = _deployment.model_dump(exclude_none=True)

        if deployment is None:
            raise ValueError("Deployment not found")

        ## GET BASE MODEL
        base_model = deployment.get("model_info", {}).get("base_model", None)
        if base_model is None:
            base_model = deployment.get("litellm_params", {}).get("base_model", None)

        model = base_model

        ## GET PROVIDER
        _model, custom_llm_provider, _, _ = litellm.get_llm_provider(
            model=deployment.get("litellm_params", {}).get("model", ""),
            litellm_params=LiteLLM_Params(**deployment.get("litellm_params", {})),
        )

        ## SET MODEL TO 'model=' - if base_model is None + not azure
        if custom_llm_provider == "azure" and base_model is None:
            verbose_router_logger.error(
                "Could not identify azure model. Set azure 'base_model' for accurate max tokens, cost tracking, etc.- https://docs.litellm.ai/docs/proxy/cost_tracking#spend-tracking-for-azure-openai-models"
            )
        elif custom_llm_provider != "azure":
            model = _model

            potential_models = self.pattern_router.route(received_model_name)
            if "*" in model and potential_models is not None:  # if wildcard route
                for potential_model in potential_models:
                    try:
                        if potential_model.get("model_info", {}).get(
                            "id"
                        ) == deployment.get("model_info", {}).get("id"):
                            model = potential_model.get("litellm_params", {}).get(
                                "model"
                            )
                            break
                    except Exception:
                        pass

        ## GET LITELLM MODEL INFO - raises exception, if model is not mapped
        if not model.startswith("{}/".format(custom_llm_provider)):
            model_info_name = "{}/{}".format(custom_llm_provider, model)
        else:
            model_info_name = model

        model_info = litellm.get_model_info(model=model_info_name)

        ## CHECK USER SET MODEL INFO
        user_model_info = deployment.get("model_info", {})

        model_info.update(user_model_info)

        return model_info

    def get_model_info(self, id: str) -> Optional[dict]:
        """
        For a given model id, return the model info

        Returns
        - dict: the model in list with 'model_name', 'litellm_params', Optional['model_info']
        - None: could not find deployment in list
        """
        for model in self.model_list:
            if "model_info" in model and "id" in model["model_info"]:
                if id == model["model_info"]["id"]:
                    return model
        return None

    def get_model_group(self, id: str) -> Optional[List]:
        """
        Return list of all models in the same model group as that model id
        """

        model_info = self.get_model_info(id=id)
        if model_info is None:
            return None

        model_name = model_info["model_name"]
        return self.get_model_list(model_name=model_name)

    def get_deployment_model_info(
        self, model_id: str, model_name: str
    ) -> Optional[ModelInfo]:
        """
        For a given model id, return the model info

        1. Check if model_id is in model info
        2. If not, check if litellm model name is in model info
        3. If not, return None
        """
        from litellm.utils import _update_dictionary

        model_info: Optional[ModelInfo] = None
        custom_model_info: Optional[dict] = None
        litellm_model_name_model_info: Optional[ModelInfo] = None

        try:
            custom_model_info = litellm.model_cost.get(model_id)
        except Exception:
            pass

        try:
            litellm_model_name_model_info = litellm.get_model_info(model=model_name)
        except Exception:
            pass

        if custom_model_info is not None and litellm_model_name_model_info is not None:
            model_info = cast(
                ModelInfo,
                _update_dictionary(
                    cast(dict, litellm_model_name_model_info).copy(),
                    custom_model_info,
                ),
            )
        elif litellm_model_name_model_info is not None:
            model_info = litellm_model_name_model_info

        return model_info

    def _set_model_group_info(  # noqa: PLR0915
        self, model_group: str, user_facing_model_group_name: str
    ) -> Optional[ModelGroupInfo]:
        """
        For a given model group name, return the combined model info

        Returns:
        - ModelGroupInfo if able to construct a model group
        - None if error constructing model group info
        """
        model_group_info: Optional[ModelGroupInfo] = None

        total_tpm: Optional[int] = None
        total_rpm: Optional[int] = None
        configurable_clientside_auth_params: CONFIGURABLE_CLIENTSIDE_AUTH_PARAMS = None
        model_list = self.get_model_list(model_name=model_group)
        if model_list is None:
            return None
        for model in model_list:
            is_match = False
            if (
                "model_name" in model and model["model_name"] == model_group
            ):  # exact match
                is_match = True
            elif (
                "model_name" in model
                and self.pattern_router.route(model_group) is not None
            ):  # wildcard model
                is_match = True

            if not is_match:
                continue
            # model in model group found #
            litellm_params = LiteLLM_Params(**model["litellm_params"])  # type: ignore
            # get configurable clientside auth params
            configurable_clientside_auth_params = (
                litellm_params.configurable_clientside_auth_params
            )
            # get model tpm
            _deployment_tpm: Optional[int] = None
            if _deployment_tpm is None:
                _deployment_tpm = model.get("tpm", None)  # type: ignore
            if _deployment_tpm is None:
                _deployment_tpm = model.get("litellm_params", {}).get("tpm", None)  # type: ignore
            if _deployment_tpm is None:
                _deployment_tpm = model.get("model_info", {}).get("tpm", None)  # type: ignore

            # get model rpm
            _deployment_rpm: Optional[int] = None
            if _deployment_rpm is None:
                _deployment_rpm = model.get("rpm", None)  # type: ignore
            if _deployment_rpm is None:
                _deployment_rpm = model.get("litellm_params", {}).get("rpm", None)  # type: ignore
            if _deployment_rpm is None:
                _deployment_rpm = model.get("model_info", {}).get("rpm", None)  # type: ignore

            # get model info
            try:
                model_id = model.get("model_info", {}).get("id", None)
                if model_id is not None:
                    model_info = self.get_deployment_model_info(
                        model_id=model_id, model_name=litellm_params.model
                    )
                else:
                    model_info = None
            except Exception:
                model_info = None

            # get llm provider
            litellm_model, llm_provider = "", ""
            try:
                litellm_model, llm_provider, _, _ = litellm.get_llm_provider(
                    model=litellm_params.model,
                    custom_llm_provider=litellm_params.custom_llm_provider,
                )
            except litellm.exceptions.BadRequestError as e:
                verbose_router_logger.error(
                    "litellm.router.py::get_model_group_info() - {}".format(str(e))
                )

            if model_info is None:
                supported_openai_params = litellm.get_supported_openai_params(
                    model=litellm_model, custom_llm_provider=llm_provider
                )
                if supported_openai_params is None:
                    supported_openai_params = []
                model_info = ModelMapInfo(
                    key=model_group,
                    max_tokens=None,
                    max_input_tokens=None,
                    max_output_tokens=None,
                    input_cost_per_token=0,
                    output_cost_per_token=0,
                    litellm_provider=llm_provider,
                    mode="chat",
                    supported_openai_params=supported_openai_params,
                    supports_system_messages=None,
                )

            if model_group_info is None:
                model_group_info = ModelGroupInfo(  # type: ignore
                    **{
                        "model_group": user_facing_model_group_name,
                        "providers": [llm_provider],
                        **model_info,
                    }
                )
            else:
                # if max_input_tokens > curr
                # if max_output_tokens > curr
                # if input_cost_per_token > curr
                # if output_cost_per_token > curr
                # supports_parallel_function_calling == True
                # supports_vision == True
                # supports_function_calling == True
                if llm_provider not in model_group_info.providers:
                    model_group_info.providers.append(llm_provider)
                if (
                    model_info.get("max_input_tokens", None) is not None
                    and model_info["max_input_tokens"] is not None
                    and (
                        model_group_info.max_input_tokens is None
                        or model_info["max_input_tokens"]
                        > model_group_info.max_input_tokens
                    )
                ):
                    model_group_info.max_input_tokens = model_info["max_input_tokens"]
                if (
                    model_info.get("max_output_tokens", None) is not None
                    and model_info["max_output_tokens"] is not None
                    and (
                        model_group_info.max_output_tokens is None
                        or model_info["max_output_tokens"]
                        > model_group_info.max_output_tokens
                    )
                ):
                    model_group_info.max_output_tokens = model_info["max_output_tokens"]
                if model_info.get("input_cost_per_token", None) is not None and (
                    model_group_info.input_cost_per_token is None
                    or model_info["input_cost_per_token"]
                    > model_group_info.input_cost_per_token
                ):
                    model_group_info.input_cost_per_token = model_info[
                        "input_cost_per_token"
                    ]
                if model_info.get("output_cost_per_token", None) is not None and (
                    model_group_info.output_cost_per_token is None
                    or model_info["output_cost_per_token"]
                    > model_group_info.output_cost_per_token
                ):
                    model_group_info.output_cost_per_token = model_info[
                        "output_cost_per_token"
                    ]
                if (
                    model_info.get("supports_parallel_function_calling", None)
                    is not None
                    and model_info["supports_parallel_function_calling"] is True  # type: ignore
                ):
                    model_group_info.supports_parallel_function_calling = True
                if (
                    model_info.get("supports_vision", None) is not None
                    and model_info["supports_vision"] is True  # type: ignore
                ):
                    model_group_info.supports_vision = True
                if (
                    model_info.get("supports_function_calling", None) is not None
                    and model_info["supports_function_calling"] is True  # type: ignore
                ):
                    model_group_info.supports_function_calling = True
                if (
                    model_info.get("supports_web_search", None) is not None
                    and model_info["supports_web_search"] is True  # type: ignore
                ):
                    model_group_info.supports_web_search = True
                if (
                    model_info.get("supports_url_context", None) is not None
                    and model_info["supports_url_context"] is True  # type: ignore
                ):
                    model_group_info.supports_url_context = True

                if (
                    model_info.get("supports_reasoning", None) is not None
                    and model_info["supports_reasoning"] is True  # type: ignore
                ):
                    model_group_info.supports_reasoning = True
                if (
                    model_info.get("supported_openai_params", None) is not None
                    and model_info["supported_openai_params"] is not None
                ):
                    model_group_info.supported_openai_params = model_info[
                        "supported_openai_params"
                    ]
                if model_info.get("tpm", None) is not None and _deployment_tpm is None:
                    _deployment_tpm = model_info.get("tpm")
                if model_info.get("rpm", None) is not None and _deployment_rpm is None:
                    _deployment_rpm = model_info.get("rpm")

            if _deployment_tpm is not None:
                if total_tpm is None:
                    total_tpm = 0
                total_tpm += _deployment_tpm  # type: ignore

            if _deployment_rpm is not None:
                if total_rpm is None:
                    total_rpm = 0
                total_rpm += _deployment_rpm  # type: ignore
        if model_group_info is not None:
            ## UPDATE WITH TOTAL TPM/RPM FOR MODEL GROUP
            if total_tpm is not None:
                model_group_info.tpm = total_tpm

            if total_rpm is not None:
                model_group_info.rpm = total_rpm

            ## UPDATE WITH CONFIGURABLE CLIENTSIDE AUTH PARAMS FOR MODEL GROUP
            if configurable_clientside_auth_params is not None:
                model_group_info.configurable_clientside_auth_params = (
                    configurable_clientside_auth_params
                )

        return model_group_info

    def get_model_group_info(self, model_group: str) -> Optional[ModelGroupInfo]:
        """
        For a given model group name, return the combined model info

        Returns:
        - ModelGroupInfo if able to construct a model group
        - None if error constructing model group info or hidden model group
        """
        ## Check if model group alias
        if model_group in self.model_group_alias:
            item = self.model_group_alias[model_group]
            if isinstance(item, str):
                _router_model_group = item
            elif isinstance(item, dict):
                if item["hidden"] is True:
                    return None
                else:
                    _router_model_group = item["model"]
            else:
                return None

            return self._set_model_group_info(
                model_group=_router_model_group,
                user_facing_model_group_name=model_group,
            )

        ## Check if actual model
        return self._set_model_group_info(
            model_group=model_group, user_facing_model_group_name=model_group
        )

    async def get_model_group_usage(
        self, model_group: str
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Returns current tpm/rpm usage for model group

        Parameters:
        - model_group: str - the received model name from the user (can be a wildcard route).

        Returns:
        - usage: Tuple[tpm, rpm]
        """
        dt = get_utc_datetime()
        current_minute = dt.strftime(
            "%H-%M"
        )  # use the same timezone regardless of system clock
        tpm_keys: List[str] = []
        rpm_keys: List[str] = []

        model_list = self.get_model_list(model_name=model_group)
        if model_list is None:  # no matching deployments
            return None, None

        for model in model_list:
            id: Optional[str] = model.get("model_info", {}).get("id")  # type: ignore
            litellm_model: Optional[str] = model["litellm_params"].get(
                "model"
            )  # USE THE MODEL SENT TO litellm.completion() - consistent with how global_router cache is written.
            if id is None or litellm_model is None:
                continue
            tpm_keys.append(
                RouterCacheEnum.TPM.value.format(
                    id=id,
                    model=litellm_model,
                    current_minute=current_minute,
                )
            )
            rpm_keys.append(
                RouterCacheEnum.RPM.value.format(
                    id=id,
                    model=litellm_model,
                    current_minute=current_minute,
                )
            )
        combined_tpm_rpm_keys = tpm_keys + rpm_keys

        combined_tpm_rpm_values = await self.cache.async_batch_get_cache(
            keys=combined_tpm_rpm_keys
        )
        if combined_tpm_rpm_values is None:
            return None, None

        tpm_usage_list: Optional[List] = combined_tpm_rpm_values[: len(tpm_keys)]
        rpm_usage_list: Optional[List] = combined_tpm_rpm_values[len(tpm_keys) :]

        ## TPM
        tpm_usage: Optional[int] = None
        if tpm_usage_list is not None:
            for t in tpm_usage_list:
                if isinstance(t, int):
                    if tpm_usage is None:
                        tpm_usage = 0
                    tpm_usage += t
        ## RPM
        rpm_usage: Optional[int] = None
        if rpm_usage_list is not None:
            for t in rpm_usage_list:
                if isinstance(t, int):
                    if rpm_usage is None:
                        rpm_usage = 0
                    rpm_usage += t
        return tpm_usage, rpm_usage

    @lru_cache(maxsize=DEFAULT_MAX_LRU_CACHE_SIZE)
    def _cached_get_model_group_info(
        self, model_group: str
    ) -> Optional[ModelGroupInfo]:
        """
        Cached version of get_model_group_info, uses @lru_cache wrapper

        This is a speed optimization, since set_response_headers makes a call to get_model_group_info on every request
        """
        return self.get_model_group_info(model_group)

    async def get_remaining_model_group_usage(self, model_group: str) -> Dict[str, int]:
        model_group_info = self._cached_get_model_group_info(model_group)

        if model_group_info is not None and model_group_info.tpm is not None:
            tpm_limit = model_group_info.tpm
        else:
            tpm_limit = None

        if model_group_info is not None and model_group_info.rpm is not None:
            rpm_limit = model_group_info.rpm
        else:
            rpm_limit = None

        if tpm_limit is None and rpm_limit is None:
            return {}

        current_tpm, current_rpm = await self.get_model_group_usage(model_group)

        returned_dict = {}
        if tpm_limit is not None:
            returned_dict["x-ratelimit-remaining-tokens"] = tpm_limit - (
                current_tpm or 0
            )
            returned_dict["x-ratelimit-limit-tokens"] = tpm_limit
        if rpm_limit is not None:
            returned_dict["x-ratelimit-remaining-requests"] = rpm_limit - (
                current_rpm or 0
            )
            returned_dict["x-ratelimit-limit-requests"] = rpm_limit

        return returned_dict

    async def set_response_headers(
        self, response: Any, model_group: Optional[str] = None
    ) -> Any:
        """
        Add the most accurate rate limit headers for a given model response.

        ## TODO: add model group rate limit headers
        # - if healthy_deployments > 1, return model group rate limit headers
        # - else return the model's rate limit headers
        """
        if (
            isinstance(response, BaseModel)
            and hasattr(response, "_hidden_params")
            and isinstance(response._hidden_params, dict)  # type: ignore
        ):
            response._hidden_params.setdefault("additional_headers", {})  # type: ignore
            response._hidden_params["additional_headers"][  # type: ignore
                "x-litellm-model-group"
            ] = model_group

            additional_headers = response._hidden_params["additional_headers"]  # type: ignore

            if (
                "x-ratelimit-remaining-tokens" not in additional_headers
                and "x-ratelimit-remaining-requests" not in additional_headers
                and model_group is not None
            ):
                remaining_usage = await self.get_remaining_model_group_usage(
                    model_group
                )

                for header, value in remaining_usage.items():
                    if value is not None:
                        additional_headers[header] = value
        return response

    def get_model_ids(self, model_name: Optional[str] = None) -> List[str]:
        """
        if 'model_name' is none, returns all.

        Returns list of model id's.
        """
        ids = []
        for model in self.model_list:
            if "model_info" in model and "id" in model["model_info"]:
                id = model["model_info"]["id"]
                if model_name is not None and model["model_name"] == model_name:
                    ids.append(id)
                elif model_name is None:
                    ids.append(id)
        return ids

    def map_team_model(self, team_model_name: str, team_id: str) -> Optional[str]:
        """
        Map a team model name to a team-specific model name.

        Returns:
        - team_model_name: str - the team-specific model name
        - None: if no team-specific model name is found
        """
        for model in self.model_list:
            model_team_id = model["model_info"].get("team_id")
            model_team_public_model_name = model["model_info"].get(
                "team_public_model_name"
            )
            if (
                model_team_id == team_id
                and model_team_public_model_name == team_model_name
            ):
                return model["model_name"]
        return None

    def _get_all_deployments(
        self, model_name: str, model_alias: Optional[str] = None
    ) -> List[DeploymentTypedDict]:
        """
        Return all deployments of a model name

        Used for accurate 'get_model_list'.
        """
        returned_models: List[DeploymentTypedDict] = []
        for model in self.model_list:
            if model_name is not None and model["model_name"] == model_name:
                if model_alias is not None:
                    alias_model = copy.deepcopy(model)
                    alias_model["model_name"] = model_alias
                    returned_models.append(alias_model)
                else:
                    returned_models.append(model)

        return returned_models

    def get_model_names(self, team_id: Optional[str] = None) -> List[str]:
        """
        Returns all possible model names for the router, including models defined via model_group_alias.

        If a team_id is provided, only deployments configured with that team_id (i.e. team‐specific models)
        will yield their team public name.
        """
        deployments = self.get_model_list() or []
        model_names = []

        for deployment in deployments:
            model_info = deployment.get("model_info")
            if self._is_team_specific_model(model_info):
                team_model_name = self._get_team_specific_model(
                    deployment=deployment, team_id=team_id
                )
                if team_model_name:
                    model_names.append(team_model_name)
            else:
                model_names.append(deployment.get("model_name", ""))

        return model_names

    def _get_team_specific_model(
        self, deployment: DeploymentTypedDict, team_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the team-specific model name if team_id matches the deployment.

        Args:
            deployment: DeploymentTypedDict - The model deployment
            team_id: Optional[str] - If passed, will return router models set with a `team_id` matching the passed `team_id`.

        Returns:
            str: The `team_public_model_name` if team_id matches
            None: If team_id doesn't match or no team info exists
        """
        model_info: Optional[Dict] = deployment.get("model_info") or {}
        if model_info is None:
            return None
        if team_id == model_info.get("team_id"):
            return model_info.get("team_public_model_name")
        return None

    def _is_team_specific_model(self, model_info: Optional[Dict]) -> bool:
        """
        Check if model info contains team-specific configuration.

        Args:
            model_info: Model information dictionary

        Returns:
            bool: True if model has team-specific configuration
        """
        return bool(model_info and model_info.get("team_id"))

    def get_model_list_from_model_alias(
        self, model_name: Optional[str] = None
    ) -> List[DeploymentTypedDict]:
        """
        Helper function to get model list from model alias.

        Used by `.get_model_list` to get model list from model alias.
        """
        returned_models: List[DeploymentTypedDict] = []
        for model_alias, model_value in self.model_group_alias.items():
            if model_name is not None and model_alias != model_name:
                continue
            if isinstance(model_value, str):
                _router_model_name: str = model_value
            elif isinstance(model_value, dict):
                _model_value = RouterModelGroupAliasItem(**model_value)  # type: ignore
                if _model_value["hidden"] is True:
                    continue
                else:
                    _router_model_name = _model_value["model"]
            else:
                continue

            returned_models.extend(
                self._get_all_deployments(
                    model_name=_router_model_name, model_alias=model_alias
                )
            )

        return returned_models

    def get_model_list(
        self, model_name: Optional[str] = None
    ) -> Optional[List[DeploymentTypedDict]]:
        """
        Includes router model_group_alias'es as well
        """
        if hasattr(self, "model_list"):
            returned_models: List[DeploymentTypedDict] = []

            if model_name is not None:
                returned_models.extend(self._get_all_deployments(model_name=model_name))

            if hasattr(self, "model_group_alias"):
                returned_models.extend(
                    self.get_model_list_from_model_alias(model_name=model_name)
                )

            if len(returned_models) == 0:  # check if wildcard route
                potential_wildcard_models = self.pattern_router.route(model_name)
                if model_name is not None and potential_wildcard_models is not None:
                    for m in potential_wildcard_models:
                        deployment_typed_dict = DeploymentTypedDict(**m)  # type: ignore
                        deployment_typed_dict["model_name"] = model_name
                        returned_models.append(deployment_typed_dict)

            if model_name is None:
                returned_models += self.model_list

                return returned_models

            return returned_models
        return None

    def get_model_access_groups(
        self, model_name: Optional[str] = None, model_access_group: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        If model_name is provided, only return access groups for that model.

        Parameters:
        - model_name: Optional[str] - the received model name from the user (can be a wildcard route). If set, will only return access groups for that model.
        - model_access_group: Optional[str] - the received model access group from the user. If set, will only return models for that access group.
        """
        from collections import defaultdict

        access_groups = defaultdict(list)

        model_list = self.get_model_list(model_name=model_name)
        if model_list:
            for m in model_list:
                _model_info = m.get("model_info")
                if _model_info:
                    for group in _model_info.get("access_groups", []) or []:
                        if model_access_group is not None:
                            if group == model_access_group:
                                model_name = m["model_name"]
                                access_groups[group].append(model_name)
                        else:
                            model_name = m["model_name"]
                            access_groups[group].append(model_name)

        return access_groups

    def _is_model_access_group_for_wildcard_route(
        self, model_access_group: str
    ) -> bool:
        """
        Return True if model access group is a wildcard route
        """
        # GET ACCESS GROUPS
        access_groups = self.get_model_access_groups(
            model_access_group=model_access_group
        )

        if len(access_groups) == 0:
            return False

        models = access_groups.get(model_access_group, [])

        for model in models:
            # CHECK IF MODEL ACCESS GROUP IS A WILDCARD ROUTE
            if self.pattern_router.route(request=model) is not None:
                return True

        return False

    def get_settings(self):
        """
        Get router settings method, returns a dictionary of the settings and their values.
        For example get the set values for routing_strategy_args, routing_strategy, allowed_fails, cooldown_time, num_retries, timeout, max_retries, retry_after
        """
        _all_vars = vars(self)
        _settings_to_return = {}
        vars_to_include = [
            "routing_strategy_args",
            "routing_strategy",
            "allowed_fails",
            "cooldown_time",
            "num_retries",
            "timeout",
            "max_retries",
            "retry_after",
            "fallbacks",
            "context_window_fallbacks",
            "model_group_retry_policy",
        ]

        for var in vars_to_include:
            if var in _all_vars:
                _settings_to_return[var] = _all_vars[var]
            if (
                var == "routing_strategy_args"
                and self.routing_strategy == "latency-based-routing"
            ):
                _settings_to_return[var] = self.lowestlatency_logger.routing_args.json()
        return _settings_to_return

    def update_settings(self, **kwargs):
        """
        Update the router settings.
        """
        # only the following settings are allowed to be configured
        _allowed_settings = [
            "routing_strategy_args",
            "routing_strategy",
            "allowed_fails",
            "cooldown_time",
            "num_retries",
            "timeout",
            "max_retries",
            "retry_after",
            "fallbacks",
            "context_window_fallbacks",
            "model_group_retry_policy",
        ]

        _int_settings = [
            "timeout",
            "num_retries",
            "retry_after",
            "allowed_fails",
            "cooldown_time",
        ]

        _existing_router_settings = self.get_settings()
        for var in kwargs:
            if var in _allowed_settings:
                if var in _int_settings:
                    _casted_value = int(kwargs[var])
                    setattr(self, var, _casted_value)
                else:
                    # only run routing strategy init if it has changed
                    if (
                        var == "routing_strategy"
                        and _existing_router_settings["routing_strategy"] != kwargs[var]
                    ):
                        self.routing_strategy_init(
                            routing_strategy=kwargs[var],
                            routing_strategy_args=kwargs.get(
                                "routing_strategy_args", {}
                            ),
                        )
                    setattr(self, var, kwargs[var])
            else:
                verbose_router_logger.debug("Setting {} is not allowed".format(var))
        verbose_router_logger.debug(f"Updated Router settings: {self.get_settings()}")

    def _get_client(self, deployment, kwargs, client_type=None):
        """
        Returns the appropriate client based on the given deployment, kwargs, and client_type.

        Parameters:
            deployment (dict): The deployment dictionary containing the clients.
            kwargs (dict): The keyword arguments passed to the function.
            client_type (str): The type of client to return.

        Returns:
            The appropriate client based on the given client_type and kwargs.
        """
        model_id = deployment["model_info"]["id"]
        parent_otel_span: Optional[Span] = _get_parent_otel_span_from_kwargs(kwargs)
        if client_type == "max_parallel_requests":
            cache_key = "{}_max_parallel_requests_client".format(model_id)
            client = self.cache.get_cache(
                key=cache_key, local_only=True, parent_otel_span=parent_otel_span
            )
            if client is None:
                InitalizeCachedClient.set_max_parallel_requests_client(
                    litellm_router_instance=self, model=deployment
                )
                client = self.cache.get_cache(
                    key=cache_key, local_only=True, parent_otel_span=parent_otel_span
                )
            return client
        elif client_type == "async":
            if kwargs.get("stream") is True:
                cache_key = f"{model_id}_stream_async_client"
                client = self.cache.get_cache(
                    key=cache_key, local_only=True, parent_otel_span=parent_otel_span
                )
                return client
            else:
                cache_key = f"{model_id}_async_client"
                client = self.cache.get_cache(
                    key=cache_key, local_only=True, parent_otel_span=parent_otel_span
                )
                return client
        else:
            if kwargs.get("stream") is True:
                cache_key = f"{model_id}_stream_client"
                client = self.cache.get_cache(
                    key=cache_key, parent_otel_span=parent_otel_span
                )
                return client
            else:
                cache_key = f"{model_id}_client"
                client = self.cache.get_cache(
                    key=cache_key, parent_otel_span=parent_otel_span
                )
                return client

    def _pre_call_checks(  # noqa: PLR0915
        self,
        model: str,
        healthy_deployments: List,
        messages: List[Dict[str, str]],
        request_kwargs: Optional[dict] = None,
    ):
        """
        Filter out model in model group, if:

        - model context window < message length. For azure openai models, requires 'base_model' is set. - https://docs.litellm.ai/docs/proxy/cost_tracking#spend-tracking-for-azure-openai-models
        - filter models above rpm limits
        - if region given, filter out models not in that region / unknown region
        - [TODO] function call and model doesn't support function calling
        """

        verbose_router_logger.debug(
            f"Starting Pre-call checks for deployments in model={model}"
        )

        _returned_deployments = copy.deepcopy(healthy_deployments)

        invalid_model_indices = []

        try:
            input_tokens = litellm.token_counter(messages=messages)
        except Exception as e:
            verbose_router_logger.error(
                "litellm.router.py::_pre_call_checks: failed to count tokens. Returning initial list of deployments. Got - {}".format(
                    str(e)
                )
            )
            return _returned_deployments

        _context_window_error = False
        _potential_error_str = ""
        _rate_limit_error = False
        parent_otel_span = _get_parent_otel_span_from_kwargs(request_kwargs)

        ## get model group RPM ##
        dt = get_utc_datetime()
        current_minute = dt.strftime("%H-%M")
        rpm_key = f"{model}:rpm:{current_minute}"
        model_group_cache = (
            self.cache.get_cache(
                key=rpm_key, local_only=True, parent_otel_span=parent_otel_span
            )
            or {}
        )  # check the in-memory cache used by lowest_latency and usage-based routing. Only check the local cache.
        for idx, deployment in enumerate(_returned_deployments):
            # see if we have the info for this model
            try:
                base_model = deployment.get("model_info", {}).get("base_model", None)
                if base_model is None:
                    base_model = deployment.get("litellm_params", {}).get(
                        "base_model", None
                    )
                model_info = self.get_router_model_info(
                    deployment=deployment, received_model_name=model
                )
                model = base_model or deployment.get("litellm_params", {}).get(
                    "model", None
                )

                if (
                    isinstance(model_info, dict)
                    and model_info.get("max_input_tokens", None) is not None
                ):
                    if (
                        isinstance(model_info["max_input_tokens"], int)
                        and input_tokens > model_info["max_input_tokens"]
                    ):
                        invalid_model_indices.append(idx)
                        _context_window_error = True
                        _potential_error_str += (
                            "Model={}, Max Input Tokens={}, Got={}".format(
                                model, model_info["max_input_tokens"], input_tokens
                            )
                        )
                        continue
            except Exception as e:
                verbose_router_logger.exception("An error occurs - {}".format(str(e)))

            _litellm_params = deployment.get("litellm_params", {})
            model_id = deployment.get("model_info", {}).get("id", "")
            ## RPM CHECK ##
            ### get local router cache ###
            current_request_cache_local = (
                self.cache.get_cache(
                    key=model_id, local_only=True, parent_otel_span=parent_otel_span
                )
                or 0
            )
            ### get usage based cache ###
            if (
                isinstance(model_group_cache, dict)
                and self.routing_strategy != "usage-based-routing-v2"
            ):
                model_group_cache[model_id] = model_group_cache.get(model_id, 0)

                current_request = max(
                    current_request_cache_local, model_group_cache[model_id]
                )

                if (
                    isinstance(_litellm_params, dict)
                    and _litellm_params.get("rpm", None) is not None
                ):
                    if (
                        isinstance(_litellm_params["rpm"], int)
                        and _litellm_params["rpm"] <= current_request
                    ):
                        invalid_model_indices.append(idx)
                        _rate_limit_error = True
                        continue

            ## REGION CHECK ##
            if (
                request_kwargs is not None
                and request_kwargs.get("allowed_model_region") is not None
            ):
                allowed_model_region = request_kwargs.get("allowed_model_region")

                if allowed_model_region is not None:
                    if not is_region_allowed(
                        litellm_params=LiteLLM_Params(**_litellm_params),
                        allowed_model_region=allowed_model_region,
                    ):
                        invalid_model_indices.append(idx)
                        continue

            ## INVALID PARAMS ## -> catch 'gpt-3.5-turbo-16k' not supporting 'response_format' param
            if request_kwargs is not None and litellm.drop_params is False:
                # get supported params
                model, custom_llm_provider, _, _ = litellm.get_llm_provider(
                    model=model, litellm_params=LiteLLM_Params(**_litellm_params)
                )

                supported_openai_params = litellm.get_supported_openai_params(
                    model=model, custom_llm_provider=custom_llm_provider
                )

                if supported_openai_params is None:
                    continue
                else:
                    # check the non-default openai params in request kwargs
                    non_default_params = litellm.utils.get_non_default_params(
                        passed_params=request_kwargs
                    )
                    special_params = ["response_format"]
                    # check if all params are supported
                    for k, v in non_default_params.items():
                        if k not in supported_openai_params and k in special_params:
                            # if not -> invalid model
                            verbose_router_logger.debug(
                                f"INVALID MODEL INDEX @ REQUEST KWARG FILTERING, k={k}"
                            )
                            invalid_model_indices.append(idx)

        if len(invalid_model_indices) == len(_returned_deployments):
            """
            - no healthy deployments available b/c context window checks or rate limit error

            - First check for rate limit errors (if this is true, it means the model passed the context window check but failed the rate limit check)
            """

            if _rate_limit_error is True:  # allow generic fallback logic to take place
                raise RouterRateLimitErrorBasic(
                    model=model,
                )

            elif _context_window_error is True:
                raise litellm.ContextWindowExceededError(
                    message="litellm._pre_call_checks: Context Window exceeded for given call. No models have context window large enough for this call.\n{}".format(
                        _potential_error_str
                    ),
                    model=model,
                    llm_provider="",
                )
        if len(invalid_model_indices) > 0:
            for idx in reversed(invalid_model_indices):
                _returned_deployments.pop(idx)

        ## ORDER FILTERING ## -> if user set 'order' in deployments, return deployments with lowest order (e.g. order=1 > order=2)
        if len(_returned_deployments) > 0:
            _returned_deployments = litellm.utils._get_order_filtered_deployments(
                _returned_deployments
            )

        return _returned_deployments

    def _get_model_from_alias(self, model: str) -> Optional[str]:
        """
        Get the model from the alias.

        Returns:
        - str, the litellm model name
        - None, if model is not in model group alias
        """
        if model not in self.model_group_alias:
            return None

        _item = self.model_group_alias[model]
        if isinstance(_item, str):
            model = _item
        else:
            model = _item["model"]

        return model

    def _get_deployment_by_litellm_model(self, model: str) -> List:
        """
        Get the deployment by litellm model.
        """
        return [m for m in self.model_list if m["litellm_params"]["model"] == model]

    def _common_checks_available_deployment(
        self,
        model: str,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
        specific_deployment: Optional[bool] = False,
    ) -> Tuple[str, Union[List, Dict]]:
        """
        Common checks for 'get_available_deployment' across sync + async call.

        If 'healthy_deployments' returned is None, this means the user chose a specific deployment

        Returns
        - str, the litellm model name
        - List, if multiple models chosen
        - Dict, if specific model chosen
        """
        # check if aliases set on litellm model alias map
        if specific_deployment is True:
            return model, self._get_deployment_by_litellm_model(model=model)
        elif model in self.get_model_ids():
            deployment = self.get_deployment(model_id=model)
            if deployment is not None:
                deployment_model = deployment.litellm_params.model
                return deployment_model, deployment.model_dump(exclude_none=True)
            raise ValueError(
                f"LiteLLM Router: Trying to call specific deployment, but Model ID :{model} does not exist in \
                    Model ID List: {self.get_model_ids}"
            )

        _model_from_alias = self._get_model_from_alias(model=model)
        if _model_from_alias is not None:
            model = _model_from_alias

        if model not in self.model_names:
            # check if provider/ specific wildcard routing use pattern matching
            pattern_deployments = self.pattern_router.get_deployments_by_pattern(
                model=model,
            )
            if pattern_deployments:
                return model, pattern_deployments

            # check if default deployment is set
            if self.default_deployment is not None:
                updated_deployment = copy.deepcopy(
                    self.default_deployment
                )  # self.default_deployment
                updated_deployment["litellm_params"]["model"] = model
                return model, updated_deployment

        ## get healthy deployments
        ### get all deployments
        healthy_deployments = self._get_all_deployments(model_name=model)

        if len(healthy_deployments) == 0:
            # check if the user sent in a deployment name instead
            healthy_deployments = self._get_deployment_by_litellm_model(model=model)

        verbose_router_logger.debug(
            f"initial list of deployments: {healthy_deployments}"
        )

        if len(healthy_deployments) == 0:
            raise litellm.BadRequestError(
                message="You passed in model={}. There is no 'model_name' with this string ".format(
                    model
                ),
                model=model,
                llm_provider="",
            )

        if litellm.model_alias_map and model in litellm.model_alias_map:
            model = litellm.model_alias_map[
                model
            ]  # update the model to the actual value if an alias has been passed in

        return model, healthy_deployments

    async def async_get_healthy_deployments(
        self,
        model: str,
        request_kwargs: Dict,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
        specific_deployment: Optional[bool] = False,
        parent_otel_span: Optional[Span] = None,
    ) -> Union[List[Dict], Dict]:
        """
        Get the healthy deployments for a model.

        Returns:
        - List[Dict], if multiple models chosen
        *OR*
        - Dict, if specific model chosen
        """
        model, healthy_deployments = self._common_checks_available_deployment(
            model=model,
            messages=messages,
            input=input,
            specific_deployment=specific_deployment,
        )  # type: ignore

        if isinstance(healthy_deployments, dict):
            return healthy_deployments

        cooldown_deployments = await _async_get_cooldown_deployments(
            litellm_router_instance=self, parent_otel_span=parent_otel_span
        )
        verbose_router_logger.debug(
            f"async cooldown deployments: {cooldown_deployments}"
        )
        verbose_router_logger.debug(f"cooldown_deployments: {cooldown_deployments}")
        healthy_deployments = self._filter_cooldown_deployments(
            healthy_deployments=healthy_deployments,
            cooldown_deployments=cooldown_deployments,
        )

        healthy_deployments = await self.async_callback_filter_deployments(
            model=model,
            healthy_deployments=healthy_deployments,
            messages=(
                cast(List[AllMessageValues], messages) if messages is not None else None
            ),
            request_kwargs=request_kwargs,
            parent_otel_span=parent_otel_span,
        )

        if self.enable_pre_call_checks and messages is not None:
            healthy_deployments = self._pre_call_checks(
                model=model,
                healthy_deployments=cast(List[Dict], healthy_deployments),
                messages=messages,
                request_kwargs=request_kwargs,
            )
        # check if user wants to do tag based routing
        healthy_deployments = await get_deployments_for_tag(  # type: ignore
            llm_router_instance=self,
            model=model,
            request_kwargs=request_kwargs,
            healthy_deployments=healthy_deployments,
        )

        if len(healthy_deployments) == 0:
            exception = await async_raise_no_deployment_exception(
                litellm_router_instance=self,
                model=model,
                parent_otel_span=parent_otel_span,
            )
            raise exception

        return healthy_deployments

    async def async_get_available_deployment(
        self,
        model: str,
        request_kwargs: Dict,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
        specific_deployment: Optional[bool] = False,
    ):
        """
        Async implementation of 'get_available_deployments'.

        Allows all cache calls to be made async => 10x perf impact (8rps -> 100 rps).
        """
        if (
            self.routing_strategy != "usage-based-routing-v2"
            and self.routing_strategy != "simple-shuffle"
            and self.routing_strategy != "cost-based-routing"
            and self.routing_strategy != "latency-based-routing"
            and self.routing_strategy != "least-busy"
        ):  # prevent regressions for other routing strategies, that don't have async get available deployments implemented.
            return self.get_available_deployment(
                model=model,
                messages=messages,
                input=input,
                specific_deployment=specific_deployment,
                request_kwargs=request_kwargs,
            )
        try:
            parent_otel_span = _get_parent_otel_span_from_kwargs(request_kwargs)
            healthy_deployments = await self.async_get_healthy_deployments(
                model=model,
                request_kwargs=request_kwargs,
                messages=messages,
                input=input,
                specific_deployment=specific_deployment,
                parent_otel_span=parent_otel_span,
            )
            if isinstance(healthy_deployments, dict):
                return healthy_deployments

            start_time = time.time()
            if (
                self.routing_strategy == "usage-based-routing-v2"
                and self.lowesttpm_logger_v2 is not None
            ):
                deployment = (
                    await self.lowesttpm_logger_v2.async_get_available_deployments(
                        model_group=model,
                        healthy_deployments=healthy_deployments,  # type: ignore
                        messages=messages,
                        input=input,
                    )
                )
            elif (
                self.routing_strategy == "cost-based-routing"
                and self.lowestcost_logger is not None
            ):
                deployment = (
                    await self.lowestcost_logger.async_get_available_deployments(
                        model_group=model,
                        healthy_deployments=healthy_deployments,  # type: ignore
                        messages=messages,
                        input=input,
                    )
                )
            elif (
                self.routing_strategy == "latency-based-routing"
                and self.lowestlatency_logger is not None
            ):
                deployment = (
                    await self.lowestlatency_logger.async_get_available_deployments(
                        model_group=model,
                        healthy_deployments=healthy_deployments,  # type: ignore
                        messages=messages,
                        input=input,
                        request_kwargs=request_kwargs,
                    )
                )
            elif self.routing_strategy == "simple-shuffle":
                return simple_shuffle(
                    llm_router_instance=self,
                    healthy_deployments=healthy_deployments,
                    model=model,
                )
            elif (
                self.routing_strategy == "least-busy"
                and self.leastbusy_logger is not None
            ):
                deployment = (
                    await self.leastbusy_logger.async_get_available_deployments(
                        model_group=model,
                        healthy_deployments=healthy_deployments,  # type: ignore
                    )
                )
            else:
                deployment = None
            if deployment is None:
                exception = await async_raise_no_deployment_exception(
                    litellm_router_instance=self,
                    model=model,
                    parent_otel_span=parent_otel_span,
                )
                raise exception
            verbose_router_logger.info(
                f"get_available_deployment for model: {model}, Selected deployment: {self.print_deployment(deployment)} for model: {model}"
            )

            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.ROUTER,
                    duration=_duration,
                    call_type="<routing_strategy>.async_get_available_deployments",
                    parent_otel_span=parent_otel_span,
                    start_time=start_time,
                    end_time=end_time,
                )
            )

            return deployment
        except Exception as e:
            traceback_exception = traceback.format_exc()
            # if router rejects call -> log to langfuse/otel/etc.
            if request_kwargs is not None:
                logging_obj = request_kwargs.get("litellm_logging_obj", None)

                if logging_obj is not None:
                    ## LOGGING
                    threading.Thread(
                        target=logging_obj.failure_handler,
                        args=(e, traceback_exception),
                    ).start()  # log response
                    # Handle any exceptions that might occur during streaming
                    asyncio.create_task(
                        logging_obj.async_failure_handler(e, traceback_exception)  # type: ignore
                    )
            raise e

    def get_available_deployment(
        self,
        model: str,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
        specific_deployment: Optional[bool] = False,
        request_kwargs: Optional[Dict] = None,
    ):
        """
        Returns the deployment based on routing strategy
        """
        # users need to explicitly call a specific deployment, by setting `specific_deployment = True` as completion()/embedding() kwarg
        # When this was no explicit we had several issues with fallbacks timing out

        model, healthy_deployments = self._common_checks_available_deployment(
            model=model,
            messages=messages,
            input=input,
            specific_deployment=specific_deployment,
        )

        if isinstance(healthy_deployments, dict):
            return healthy_deployments

        parent_otel_span: Optional[Span] = _get_parent_otel_span_from_kwargs(
            request_kwargs
        )
        cooldown_deployments = _get_cooldown_deployments(
            litellm_router_instance=self, parent_otel_span=parent_otel_span
        )
        healthy_deployments = self._filter_cooldown_deployments(
            healthy_deployments=healthy_deployments,
            cooldown_deployments=cooldown_deployments,
        )

        # filter pre-call checks
        if self.enable_pre_call_checks and messages is not None:
            healthy_deployments = self._pre_call_checks(
                model=model,
                healthy_deployments=healthy_deployments,
                messages=messages,
                request_kwargs=request_kwargs,
            )

        if len(healthy_deployments) == 0:
            model_ids = self.get_model_ids(model_name=model)
            _cooldown_time = self.cooldown_cache.get_min_cooldown(
                model_ids=model_ids, parent_otel_span=parent_otel_span
            )
            _cooldown_list = _get_cooldown_deployments(
                litellm_router_instance=self, parent_otel_span=parent_otel_span
            )
            raise RouterRateLimitError(
                model=model,
                cooldown_time=_cooldown_time,
                enable_pre_call_checks=self.enable_pre_call_checks,
                cooldown_list=_cooldown_list,
            )

        if self.routing_strategy == "least-busy" and self.leastbusy_logger is not None:
            deployment = self.leastbusy_logger.get_available_deployments(
                model_group=model, healthy_deployments=healthy_deployments  # type: ignore
            )
        elif self.routing_strategy == "simple-shuffle":
            # if users pass rpm or tpm, we do a random weighted pick - based on rpm/tpm
            ############## Check 'weight' param set for weighted pick #################
            return simple_shuffle(
                llm_router_instance=self,
                healthy_deployments=healthy_deployments,
                model=model,
            )
        elif (
            self.routing_strategy == "latency-based-routing"
            and self.lowestlatency_logger is not None
        ):
            deployment = self.lowestlatency_logger.get_available_deployments(
                model_group=model,
                healthy_deployments=healthy_deployments,  # type: ignore
                request_kwargs=request_kwargs,
            )
        elif (
            self.routing_strategy == "usage-based-routing"
            and self.lowesttpm_logger is not None
        ):
            deployment = self.lowesttpm_logger.get_available_deployments(
                model_group=model,
                healthy_deployments=healthy_deployments,  # type: ignore
                messages=messages,
                input=input,
            )
        elif (
            self.routing_strategy == "usage-based-routing-v2"
            and self.lowesttpm_logger_v2 is not None
        ):
            deployment = self.lowesttpm_logger_v2.get_available_deployments(
                model_group=model,
                healthy_deployments=healthy_deployments,  # type: ignore
                messages=messages,
                input=input,
            )
        else:
            deployment = None

        if deployment is None:
            verbose_router_logger.info(
                f"get_available_deployment for model: {model}, No deployment available"
            )
            model_ids = self.get_model_ids(model_name=model)
            _cooldown_time = self.cooldown_cache.get_min_cooldown(
                model_ids=model_ids, parent_otel_span=parent_otel_span
            )
            _cooldown_list = _get_cooldown_deployments(
                litellm_router_instance=self, parent_otel_span=parent_otel_span
            )
            raise RouterRateLimitError(
                model=model,
                cooldown_time=_cooldown_time,
                enable_pre_call_checks=self.enable_pre_call_checks,
                cooldown_list=_cooldown_list,
            )
        verbose_router_logger.info(
            f"get_available_deployment for model: {model}, Selected deployment: {self.print_deployment(deployment)} for model: {model}"
        )
        return deployment

    def _filter_cooldown_deployments(
        self, healthy_deployments: List[Dict], cooldown_deployments: List[str]
    ) -> List[Dict]:
        """
        Filters out the deployments currently cooling down from the list of healthy deployments

        Args:
            healthy_deployments: List of healthy deployments
            cooldown_deployments: List of model_ids cooling down. cooldown_deployments is a list of model_id's cooling down, cooldown_deployments = ["16700539-b3cd-42f4-b426-6a12a1bb706a", "16700539-b3cd-42f4-b426-7899"]

        Returns:
            List of healthy deployments
        """
        # filter out the deployments currently cooling down
        deployments_to_remove = []
        verbose_router_logger.debug(f"cooldown deployments: {cooldown_deployments}")
        # Find deployments in model_list whose model_id is cooling down
        for deployment in healthy_deployments:
            deployment_id = deployment["model_info"]["id"]
            if deployment_id in cooldown_deployments:
                deployments_to_remove.append(deployment)

        # remove unhealthy deployments from healthy deployments
        for deployment in deployments_to_remove:
            healthy_deployments.remove(deployment)
        return healthy_deployments

    def _track_deployment_metrics(
        self, deployment, parent_otel_span: Optional[Span], response=None
    ):
        """
        Tracks successful requests rpm usage.
        """
        try:
            model_id = deployment.get("model_info", {}).get("id", None)
            if response is None:
                # update self.deployment_stats
                if model_id is not None:
                    self._update_usage(
                        model_id, parent_otel_span
                    )  # update in-memory cache for tracking
        except Exception as e:
            verbose_router_logger.error(f"Error in _track_deployment_metrics: {str(e)}")

    def get_num_retries_from_retry_policy(
        self, exception: Exception, model_group: Optional[str] = None
    ):
        return _get_num_retries_from_retry_policy(
            exception=exception,
            model_group=model_group,
            model_group_retry_policy=self.model_group_retry_policy,
            retry_policy=self.retry_policy,
        )

    def get_allowed_fails_from_policy(self, exception: Exception):
        """
        BadRequestErrorRetries: Optional[int] = None
        AuthenticationErrorRetries: Optional[int] = None
        TimeoutErrorRetries: Optional[int] = None
        RateLimitErrorRetries: Optional[int] = None
        ContentPolicyViolationErrorRetries: Optional[int] = None
        """
        # if we can find the exception then in the retry policy -> return the number of retries
        allowed_fails_policy: Optional[AllowedFailsPolicy] = self.allowed_fails_policy

        if allowed_fails_policy is None:
            return None

        if (
            isinstance(exception, litellm.BadRequestError)
            and allowed_fails_policy.BadRequestErrorAllowedFails is not None
        ):
            return allowed_fails_policy.BadRequestErrorAllowedFails
        if (
            isinstance(exception, litellm.AuthenticationError)
            and allowed_fails_policy.AuthenticationErrorAllowedFails is not None
        ):
            return allowed_fails_policy.AuthenticationErrorAllowedFails
        if (
            isinstance(exception, litellm.Timeout)
            and allowed_fails_policy.TimeoutErrorAllowedFails is not None
        ):
            return allowed_fails_policy.TimeoutErrorAllowedFails
        if (
            isinstance(exception, litellm.RateLimitError)
            and allowed_fails_policy.RateLimitErrorAllowedFails is not None
        ):
            return allowed_fails_policy.RateLimitErrorAllowedFails
        if (
            isinstance(exception, litellm.ContentPolicyViolationError)
            and allowed_fails_policy.ContentPolicyViolationErrorAllowedFails is not None
        ):
            return allowed_fails_policy.ContentPolicyViolationErrorAllowedFails

    def _initialize_alerting(self):
        from litellm.integrations.SlackAlerting.slack_alerting import SlackAlerting

        if self.alerting_config is None:
            return

        router_alerting_config: AlertingConfig = self.alerting_config

        _slack_alerting_logger = SlackAlerting(
            alerting_threshold=router_alerting_config.alerting_threshold,
            alerting=["slack"],
            default_webhook_url=router_alerting_config.webhook_url,
        )

        self.slack_alerting_logger = _slack_alerting_logger

        litellm.logging_callback_manager.add_litellm_callback(_slack_alerting_logger)  # type: ignore
        litellm.logging_callback_manager.add_litellm_success_callback(
            _slack_alerting_logger.response_taking_too_long_callback
        )
        verbose_router_logger.info(
            "\033[94m\nInitialized Alerting for litellm.Router\033[0m\n"
        )

    def set_custom_routing_strategy(
        self, CustomRoutingStrategy: CustomRoutingStrategyBase
    ):
        """
        Sets get_available_deployment and async_get_available_deployment on an instanced of litellm.Router

        Use this to set your custom routing strategy

        Args:
            CustomRoutingStrategy: litellm.router.CustomRoutingStrategyBase
        """

        setattr(
            self,
            "get_available_deployment",
            CustomRoutingStrategy.get_available_deployment,
        )
        setattr(
            self,
            "async_get_available_deployment",
            CustomRoutingStrategy.async_get_available_deployment,
        )

    def flush_cache(self):
        litellm.cache = None
        self.cache.flush_cache()

    def reset(self):
        ## clean up on close
        litellm.success_callback = []
        litellm._async_success_callback = []
        litellm.failure_callback = []
        litellm._async_failure_callback = []
        self.retry_policy = None
        self.flush_cache()

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\otData.py ===
otData = [
    #
    # common
    #
    ("LookupOrder", []),
    (
        "ScriptList",
        [
            ("uint16", "ScriptCount", None, None, "Number of ScriptRecords"),
            (
                "struct",
                "ScriptRecord",
                "ScriptCount",
                0,
                "Array of ScriptRecords -listed alphabetically by ScriptTag",
            ),
        ],
    ),
    (
        "ScriptRecord",
        [
            ("Tag", "ScriptTag", None, None, "4-byte ScriptTag identifier"),
            (
                "Offset",
                "Script",
                None,
                None,
                "Offset to Script table-from beginning of ScriptList",
            ),
        ],
    ),
    (
        "Script",
        [
            (
                "Offset",
                "DefaultLangSys",
                None,
                None,
                "Offset to DefaultLangSys table-from beginning of Script table-may be NULL",
            ),
            (
                "uint16",
                "LangSysCount",
                None,
                None,
                "Number of LangSysRecords for this script-excluding the DefaultLangSys",
            ),
            (
                "struct",
                "LangSysRecord",
                "LangSysCount",
                0,
                "Array of LangSysRecords-listed alphabetically by LangSysTag",
            ),
        ],
    ),
    (
        "LangSysRecord",
        [
            ("Tag", "LangSysTag", None, None, "4-byte LangSysTag identifier"),
            (
                "Offset",
                "LangSys",
                None,
                None,
                "Offset to LangSys table-from beginning of Script table",
            ),
        ],
    ),
    (
        "LangSys",
        [
            (
                "Offset",
                "LookupOrder",
                None,
                None,
                "= NULL (reserved for an offset to a reordering table)",
            ),
            (
                "uint16",
                "ReqFeatureIndex",
                None,
                None,
                "Index of a feature required for this language system- if no required features = 0xFFFF",
            ),
            (
                "uint16",
                "FeatureCount",
                None,
                None,
                "Number of FeatureIndex values for this language system-excludes the required feature",
            ),
            (
                "uint16",
                "FeatureIndex",
                "FeatureCount",
                0,
                "Array of indices into the FeatureList-in arbitrary order",
            ),
        ],
    ),
    (
        "FeatureList",
        [
            (
                "uint16",
                "FeatureCount",
                None,
                None,
                "Number of FeatureRecords in this table",
            ),
            (
                "struct",
                "FeatureRecord",
                "FeatureCount",
                0,
                "Array of FeatureRecords-zero-based (first feature has FeatureIndex = 0)-listed alphabetically by FeatureTag",
            ),
        ],
    ),
    (
        "FeatureRecord",
        [
            ("Tag", "FeatureTag", None, None, "4-byte feature identification tag"),
            (
                "Offset",
                "Feature",
                None,
                None,
                "Offset to Feature table-from beginning of FeatureList",
            ),
        ],
    ),
    (
        "Feature",
        [
            (
                "Offset",
                "FeatureParams",
                None,
                None,
                "= NULL (reserved for offset to FeatureParams)",
            ),
            (
                "uint16",
                "LookupCount",
                None,
                None,
                "Number of LookupList indices for this feature",
            ),
            (
                "uint16",
                "LookupListIndex",
                "LookupCount",
                0,
                "Array of LookupList indices for this feature -zero-based (first lookup is LookupListIndex = 0)",
            ),
        ],
    ),
    ("FeatureParams", []),
    (
        "FeatureParamsSize",
        [
            (
                "DeciPoints",
                "DesignSize",
                None,
                None,
                "The design size in 720/inch units (decipoints).",
            ),
            (
                "uint16",
                "SubfamilyID",
                None,
                None,
                "Serves as an identifier that associates fonts in a subfamily.",
            ),
            ("NameID", "SubfamilyNameID", None, None, "Subfamily NameID."),
            (
                "DeciPoints",
                "RangeStart",
                None,
                None,
                "Small end of recommended usage range (exclusive) in 720/inch units.",
            ),
            (
                "DeciPoints",
                "RangeEnd",
                None,
                None,
                "Large end of recommended usage range (inclusive) in 720/inch units.",
            ),
        ],
    ),
    (
        "FeatureParamsStylisticSet",
        [
            ("uint16", "Version", None, None, "Set to 0."),
            ("NameID", "UINameID", None, None, "UI NameID."),
        ],
    ),
    (
        "FeatureParamsCharacterVariants",
        [
            ("uint16", "Format", None, None, "Set to 0."),
            ("NameID", "FeatUILabelNameID", None, None, "Feature UI label NameID."),
            (
                "NameID",
                "FeatUITooltipTextNameID",
                None,
                None,
                "Feature UI tooltip text NameID.",
            ),
            ("NameID", "SampleTextNameID", None, None, "Sample text NameID."),
            ("uint16", "NumNamedParameters", None, None, "Number of named parameters."),
            (
                "NameID",
                "FirstParamUILabelNameID",
                None,
                None,
                "First NameID of UI feature parameters.",
            ),
            (
                "uint16",
                "CharCount",
                None,
                None,
                "Count of characters this feature provides glyph variants for.",
            ),
            (
                "uint24",
                "Character",
                "CharCount",
                0,
                "Unicode characters for which this feature provides glyph variants.",
            ),
        ],
    ),
    (
        "LookupList",
        [
            ("uint16", "LookupCount", None, None, "Number of lookups in this table"),
            (
                "Offset",
                "Lookup",
                "LookupCount",
                0,
                "Array of offsets to Lookup tables-from beginning of LookupList -zero based (first lookup is Lookup index = 0)",
            ),
        ],
    ),
    (
        "Lookup",
        [
            (
                "uint16",
                "LookupType",
                None,
                None,
                "Different enumerations for GSUB and GPOS",
            ),
            ("LookupFlag", "LookupFlag", None, None, "Lookup qualifiers"),
            (
                "uint16",
                "SubTableCount",
                None,
                None,
                "Number of SubTables for this lookup",
            ),
            (
                "Offset",
                "SubTable",
                "SubTableCount",
                0,
                "Array of offsets to SubTables-from beginning of Lookup table",
            ),
            (
                "uint16",
                "MarkFilteringSet",
                None,
                "LookupFlag & 0x0010",
                "If set, indicates that the lookup table structure is followed by a MarkFilteringSet field. The layout engine skips over all mark glyphs not in the mark filtering set indicated.",
            ),
        ],
    ),
    (
        "CoverageFormat1",
        [
            ("uint16", "CoverageFormat", None, None, "Format identifier-format = 1"),
            ("uint16", "GlyphCount", None, None, "Number of glyphs in the GlyphArray"),
            (
                "GlyphID",
                "GlyphArray",
                "GlyphCount",
                0,
                "Array of GlyphIDs-in numerical order",
            ),
        ],
    ),
    (
        "CoverageFormat2",
        [
            ("uint16", "CoverageFormat", None, None, "Format identifier-format = 2"),
            ("uint16", "RangeCount", None, None, "Number of RangeRecords"),
            (
                "struct",
                "RangeRecord",
                "RangeCount",
                0,
                "Array of glyph ranges-ordered by Start GlyphID",
            ),
        ],
    ),
    (
        "RangeRecord",
        [
            ("GlyphID", "Start", None, None, "First GlyphID in the range"),
            ("GlyphID", "End", None, None, "Last GlyphID in the range"),
            (
                "uint16",
                "StartCoverageIndex",
                None,
                None,
                "Coverage Index of first GlyphID in range",
            ),
        ],
    ),
    (
        "ClassDefFormat1",
        [
            ("uint16", "ClassFormat", None, None, "Format identifier-format = 1"),
            (
                "GlyphID",
                "StartGlyph",
                None,
                None,
                "First GlyphID of the ClassValueArray",
            ),
            ("uint16", "GlyphCount", None, None, "Size of the ClassValueArray"),
            (
                "uint16",
                "ClassValueArray",
                "GlyphCount",
                0,
                "Array of Class Values-one per GlyphID",
            ),
        ],
    ),
    (
        "ClassDefFormat2",
        [
            ("uint16", "ClassFormat", None, None, "Format identifier-format = 2"),
            ("uint16", "ClassRangeCount", None, None, "Number of ClassRangeRecords"),
            (
                "struct",
                "ClassRangeRecord",
                "ClassRangeCount",
                0,
                "Array of ClassRangeRecords-ordered by Start GlyphID",
            ),
        ],
    ),
    (
        "ClassRangeRecord",
        [
            ("GlyphID", "Start", None, None, "First GlyphID in the range"),
            ("GlyphID", "End", None, None, "Last GlyphID in the range"),
            ("uint16", "Class", None, None, "Applied to all glyphs in the range"),
        ],
    ),
    (
        "Device",
        [
            ("uint16", "StartSize", None, None, "Smallest size to correct-in ppem"),
            ("uint16", "EndSize", None, None, "Largest size to correct-in ppem"),
            (
                "uint16",
                "DeltaFormat",
                None,
                None,
                "Format of DeltaValue array data: 1, 2, or 3",
            ),
            (
                "DeltaValue",
                "DeltaValue",
                None,
                "DeltaFormat in (1,2,3)",
                "Array of compressed data",
            ),
        ],
    ),
    #
    # gpos
    #
    (
        "GPOS",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the GPOS table- 0x00010000 or 0x00010001",
            ),
            (
                "Offset",
                "ScriptList",
                None,
                None,
                "Offset to ScriptList table-from beginning of GPOS table",
            ),
            (
                "Offset",
                "FeatureList",
                None,
                None,
                "Offset to FeatureList table-from beginning of GPOS table",
            ),
            (
                "Offset",
                "LookupList",
                None,
                None,
                "Offset to LookupList table-from beginning of GPOS table",
            ),
            (
                "LOffset",
                "FeatureVariations",
                None,
                "Version >= 0x00010001",
                "Offset to FeatureVariations table-from beginning of GPOS table",
            ),
        ],
    ),
    (
        "SinglePosFormat1",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of SinglePos subtable",
            ),
            (
                "uint16",
                "ValueFormat",
                None,
                None,
                "Defines the types of data in the ValueRecord",
            ),
            (
                "ValueRecord",
                "Value",
                None,
                None,
                "Defines positioning value(s)-applied to all glyphs in the Coverage table",
            ),
        ],
    ),
    (
        "SinglePosFormat2",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 2"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of SinglePos subtable",
            ),
            (
                "uint16",
                "ValueFormat",
                None,
                None,
                "Defines the types of data in the ValueRecord",
            ),
            ("uint16", "ValueCount", None, None, "Number of ValueRecords"),
            (
                "ValueRecord",
                "Value",
                "ValueCount",
                0,
                "Array of ValueRecords-positioning values applied to glyphs",
            ),
        ],
    ),
    (
        "PairPosFormat1",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of PairPos subtable-only the first glyph in each pair",
            ),
            (
                "uint16",
                "ValueFormat1",
                None,
                None,
                "Defines the types of data in ValueRecord1-for the first glyph in the pair -may be zero (0)",
            ),
            (
                "uint16",
                "ValueFormat2",
                None,
                None,
                "Defines the types of data in ValueRecord2-for the second glyph in the pair -may be zero (0)",
            ),
            ("uint16", "PairSetCount", None, None, "Number of PairSet tables"),
            (
                "Offset",
                "PairSet",
                "PairSetCount",
                0,
                "Array of offsets to PairSet tables-from beginning of PairPos subtable-ordered by Coverage Index",
            ),
        ],
    ),
    (
        "PairSet",
        [
            ("uint16", "PairValueCount", None, None, "Number of PairValueRecords"),
            (
                "struct",
                "PairValueRecord",
                "PairValueCount",
                0,
                "Array of PairValueRecords-ordered by GlyphID of the second glyph",
            ),
        ],
    ),
    (
        "PairValueRecord",
        [
            (
                "GlyphID",
                "SecondGlyph",
                None,
                None,
                "GlyphID of second glyph in the pair-first glyph is listed in the Coverage table",
            ),
            (
                "ValueRecord",
                "Value1",
                None,
                None,
                "Positioning data for the first glyph in the pair",
            ),
            (
                "ValueRecord",
                "Value2",
                None,
                None,
                "Positioning data for the second glyph in the pair",
            ),
        ],
    ),
    (
        "PairPosFormat2",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 2"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of PairPos subtable-for the first glyph of the pair",
            ),
            (
                "uint16",
                "ValueFormat1",
                None,
                None,
                "ValueRecord definition-for the first glyph of the pair-may be zero (0)",
            ),
            (
                "uint16",
                "ValueFormat2",
                None,
                None,
                "ValueRecord definition-for the second glyph of the pair-may be zero (0)",
            ),
            (
                "Offset",
                "ClassDef1",
                None,
                None,
                "Offset to ClassDef table-from beginning of PairPos subtable-for the first glyph of the pair",
            ),
            (
                "Offset",
                "ClassDef2",
                None,
                None,
                "Offset to ClassDef table-from beginning of PairPos subtable-for the second glyph of the pair",
            ),
            (
                "uint16",
                "Class1Count",
                None,
                None,
                "Number of classes in ClassDef1 table-includes Class0",
            ),
            (
                "uint16",
                "Class2Count",
                None,
                None,
                "Number of classes in ClassDef2 table-includes Class0",
            ),
            (
                "struct",
                "Class1Record",
                "Class1Count",
                0,
                "Array of Class1 records-ordered by Class1",
            ),
        ],
    ),
    (
        "Class1Record",
        [
            (
                "struct",
                "Class2Record",
                "Class2Count",
                0,
                "Array of Class2 records-ordered by Class2",
            ),
        ],
    ),
    (
        "Class2Record",
        [
            (
                "ValueRecord",
                "Value1",
                None,
                None,
                "Positioning for first glyph-empty if ValueFormat1 = 0",
            ),
            (
                "ValueRecord",
                "Value2",
                None,
                None,
                "Positioning for second glyph-empty if ValueFormat2 = 0",
            ),
        ],
    ),
    (
        "CursivePosFormat1",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of CursivePos subtable",
            ),
            ("uint16", "EntryExitCount", None, None, "Number of EntryExit records"),
            (
                "struct",
                "EntryExitRecord",
                "EntryExitCount",
                0,
                "Array of EntryExit records-in Coverage Index order",
            ),
        ],
    ),
    (
        "EntryExitRecord",
        [
            (
                "Offset",
                "EntryAnchor",
                None,
                None,
                "Offset to EntryAnchor table-from beginning of CursivePos subtable-may be NULL",
            ),
            (
                "Offset",
                "ExitAnchor",
                None,
                None,
                "Offset to ExitAnchor table-from beginning of CursivePos subtable-may be NULL",
            ),
        ],
    ),
    (
        "MarkBasePosFormat1",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "MarkCoverage",
                None,
                None,
                "Offset to MarkCoverage table-from beginning of MarkBasePos subtable",
            ),
            (
                "Offset",
                "BaseCoverage",
                None,
                None,
                "Offset to BaseCoverage table-from beginning of MarkBasePos subtable",
            ),
            ("uint16", "ClassCount", None, None, "Number of classes defined for marks"),
            (
                "Offset",
                "MarkArray",
                None,
                None,
                "Offset to MarkArray table-from beginning of MarkBasePos subtable",
            ),
            (
                "Offset",
                "BaseArray",
                None,
                None,
                "Offset to BaseArray table-from beginning of MarkBasePos subtable",
            ),
        ],
    ),
    (
        "BaseArray",
        [
            ("uint16", "BaseCount", None, None, "Number of BaseRecords"),
            (
                "struct",
                "BaseRecord",
                "BaseCount",
                0,
                "Array of BaseRecords-in order of BaseCoverage Index",
            ),
        ],
    ),
    (
        "BaseRecord",
        [
            (
                "Offset",
                "BaseAnchor",
                "ClassCount",
                0,
                "Array of offsets (one per class) to Anchor tables-from beginning of BaseArray table-ordered by class-zero-based",
            ),
        ],
    ),
    (
        "MarkLigPosFormat1",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "MarkCoverage",
                None,
                None,
                "Offset to Mark Coverage table-from beginning of MarkLigPos subtable",
            ),
            (
                "Offset",
                "LigatureCoverage",
                None,
                None,
                "Offset to Ligature Coverage table-from beginning of MarkLigPos subtable",
            ),
            ("uint16", "ClassCount", None, None, "Number of defined mark classes"),
            (
                "Offset",
                "MarkArray",
                None,
                None,
                "Offset to MarkArray table-from beginning of MarkLigPos subtable",
            ),
            (
                "Offset",
                "LigatureArray",
                None,
                None,
                "Offset to LigatureArray table-from beginning of MarkLigPos subtable",
            ),
        ],
    ),
    (
        "LigatureArray",
        [
            (
                "uint16",
                "LigatureCount",
                None,
                None,
                "Number of LigatureAttach table offsets",
            ),
            (
                "Offset",
                "LigatureAttach",
                "LigatureCount",
                0,
                "Array of offsets to LigatureAttach tables-from beginning of LigatureArray table-ordered by LigatureCoverage Index",
            ),
        ],
    ),
    (
        "LigatureAttach",
        [
            (
                "uint16",
                "ComponentCount",
                None,
                None,
                "Number of ComponentRecords in this ligature",
            ),
            (
                "struct",
                "ComponentRecord",
                "ComponentCount",
                0,
                "Array of Component records-ordered in writing direction",
            ),
        ],
    ),
    (
        "ComponentRecord",
        [
            (
                "Offset",
                "LigatureAnchor",
                "ClassCount",
                0,
                "Array of offsets (one per class) to Anchor tables-from beginning of LigatureAttach table-ordered by class-NULL if a component does not have an attachment for a class-zero-based array",
            ),
        ],
    ),
    (
        "MarkMarkPosFormat1",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Mark1Coverage",
                None,
                None,
                "Offset to Combining Mark Coverage table-from beginning of MarkMarkPos subtable",
            ),
            (
                "Offset",
                "Mark2Coverage",
                None,
                None,
                "Offset to Base Mark Coverage table-from beginning of MarkMarkPos subtable",
            ),
            (
                "uint16",
                "ClassCount",
                None,
                None,
                "Number of Combining Mark classes defined",
            ),
            (
                "Offset",
                "Mark1Array",
                None,
                None,
                "Offset to MarkArray table for Mark1-from beginning of MarkMarkPos subtable",
            ),
            (
                "Offset",
                "Mark2Array",
                None,
                None,
                "Offset to Mark2Array table for Mark2-from beginning of MarkMarkPos subtable",
            ),
        ],
    ),
    (
        "Mark2Array",
        [
            ("uint16", "Mark2Count", None, None, "Number of Mark2 records"),
            (
                "struct",
                "Mark2Record",
                "Mark2Count",
                0,
                "Array of Mark2 records-in Coverage order",
            ),
        ],
    ),
    (
        "Mark2Record",
        [
            (
                "Offset",
                "Mark2Anchor",
                "ClassCount",
                0,
                "Array of offsets (one per class) to Anchor tables-from beginning of Mark2Array table-zero-based array",
            ),
        ],
    ),
    (
        "PosLookupRecord",
        [
            (
                "uint16",
                "SequenceIndex",
                None,
                None,
                "Index to input glyph sequence-first glyph = 0",
            ),
            (
                "uint16",
                "LookupListIndex",
                None,
                None,
                "Lookup to apply to that position-zero-based",
            ),
        ],
    ),
    (
        "ContextPosFormat1",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of ContextPos subtable",
            ),
            ("uint16", "PosRuleSetCount", None, None, "Number of PosRuleSet tables"),
            (
                "Offset",
                "PosRuleSet",
                "PosRuleSetCount",
                0,
                "Array of offsets to PosRuleSet tables-from beginning of ContextPos subtable-ordered by Coverage Index",
            ),
        ],
    ),
    (
        "PosRuleSet",
        [
            ("uint16", "PosRuleCount", None, None, "Number of PosRule tables"),
            (
                "Offset",
                "PosRule",
                "PosRuleCount",
                0,
                "Array of offsets to PosRule tables-from beginning of PosRuleSet-ordered by preference",
            ),
        ],
    ),
    (
        "PosRule",
        [
            (
                "uint16",
                "GlyphCount",
                None,
                None,
                "Number of glyphs in the Input glyph sequence",
            ),
            ("uint16", "PosCount", None, None, "Number of PosLookupRecords"),
            (
                "GlyphID",
                "Input",
                "GlyphCount",
                -1,
                "Array of input GlyphIDs-starting with the second glyph",
            ),
            (
                "struct",
                "PosLookupRecord",
                "PosCount",
                0,
                "Array of positioning lookups-in design order",
            ),
        ],
    ),
    (
        "ContextPosFormat2",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 2"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of ContextPos subtable",
            ),
            (
                "Offset",
                "ClassDef",
                None,
                None,
                "Offset to ClassDef table-from beginning of ContextPos subtable",
            ),
            ("uint16", "PosClassSetCount", None, None, "Number of PosClassSet tables"),
            (
                "Offset",
                "PosClassSet",
                "PosClassSetCount",
                0,
                "Array of offsets to PosClassSet tables-from beginning of ContextPos subtable-ordered by class-may be NULL",
            ),
        ],
    ),
    (
        "PosClassSet",
        [
            (
                "uint16",
                "PosClassRuleCount",
                None,
                None,
                "Number of PosClassRule tables",
            ),
            (
                "Offset",
                "PosClassRule",
                "PosClassRuleCount",
                0,
                "Array of offsets to PosClassRule tables-from beginning of PosClassSet-ordered by preference",
            ),
        ],
    ),
    (
        "PosClassRule",
        [
            ("uint16", "GlyphCount", None, None, "Number of glyphs to be matched"),
            ("uint16", "PosCount", None, None, "Number of PosLookupRecords"),
            (
                "uint16",
                "Class",
                "GlyphCount",
                -1,
                "Array of classes-beginning with the second class-to be matched to the input glyph sequence",
            ),
            (
                "struct",
                "PosLookupRecord",
                "PosCount",
                0,
                "Array of positioning lookups-in design order",
            ),
        ],
    ),
    (
        "ContextPosFormat3",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 3"),
            (
                "uint16",
                "GlyphCount",
                None,
                None,
                "Number of glyphs in the input sequence",
            ),
            ("uint16", "PosCount", None, None, "Number of PosLookupRecords"),
            (
                "Offset",
                "Coverage",
                "GlyphCount",
                0,
                "Array of offsets to Coverage tables-from beginning of ContextPos subtable",
            ),
            (
                "struct",
                "PosLookupRecord",
                "PosCount",
                0,
                "Array of positioning lookups-in design order",
            ),
        ],
    ),
    (
        "ChainContextPosFormat1",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of ContextPos subtable",
            ),
            (
                "uint16",
                "ChainPosRuleSetCount",
                None,
                None,
                "Number of ChainPosRuleSet tables",
            ),
            (
                "Offset",
                "ChainPosRuleSet",
                "ChainPosRuleSetCount",
                0,
                "Array of offsets to ChainPosRuleSet tables-from beginning of ContextPos subtable-ordered by Coverage Index",
            ),
        ],
    ),
    (
        "ChainPosRuleSet",
        [
            (
                "uint16",
                "ChainPosRuleCount",
                None,
                None,
                "Number of ChainPosRule tables",
            ),
            (
                "Offset",
                "ChainPosRule",
                "ChainPosRuleCount",
                0,
                "Array of offsets to ChainPosRule tables-from beginning of ChainPosRuleSet-ordered by preference",
            ),
        ],
    ),
    (
        "ChainPosRule",
        [
            (
                "uint16",
                "BacktrackGlyphCount",
                None,
                None,
                "Total number of glyphs in the backtrack sequence (number of glyphs to be matched before the first glyph)",
            ),
            (
                "GlyphID",
                "Backtrack",
                "BacktrackGlyphCount",
                0,
                "Array of backtracking GlyphID's (to be matched before the input sequence)",
            ),
            (
                "uint16",
                "InputGlyphCount",
                None,
                None,
                "Total number of glyphs in the input sequence (includes the first glyph)",
            ),
            (
                "GlyphID",
                "Input",
                "InputGlyphCount",
                -1,
                "Array of input GlyphIDs (start with second glyph)",
            ),
            (
                "uint16",
                "LookAheadGlyphCount",
                None,
                None,
                "Total number of glyphs in the look ahead sequence (number of glyphs to be matched after the input sequence)",
            ),
            (
                "GlyphID",
                "LookAhead",
                "LookAheadGlyphCount",
                0,
                "Array of lookahead GlyphID's (to be matched after the input sequence)",
            ),
            ("uint16", "PosCount", None, None, "Number of PosLookupRecords"),
            (
                "struct",
                "PosLookupRecord",
                "PosCount",
                0,
                "Array of PosLookupRecords (in design order)",
            ),
        ],
    ),
    (
        "ChainContextPosFormat2",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 2"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of ChainContextPos subtable",
            ),
            (
                "Offset",
                "BacktrackClassDef",
                None,
                None,
                "Offset to ClassDef table containing backtrack sequence context-from beginning of ChainContextPos subtable",
            ),
            (
                "Offset",
                "InputClassDef",
                None,
                None,
                "Offset to ClassDef table containing input sequence context-from beginning of ChainContextPos subtable",
            ),
            (
                "Offset",
                "LookAheadClassDef",
                None,
                None,
                "Offset to ClassDef table containing lookahead sequence context-from beginning of ChainContextPos subtable",
            ),
            (
                "uint16",
                "ChainPosClassSetCount",
                None,
                None,
                "Number of ChainPosClassSet tables",
            ),
            (
                "Offset",
                "ChainPosClassSet",
                "ChainPosClassSetCount",
                0,
                "Array of offsets to ChainPosClassSet tables-from beginning of ChainContextPos subtable-ordered by input class-may be NULL",
            ),
        ],
    ),
    (
        "ChainPosClassSet",
        [
            (
                "uint16",
                "ChainPosClassRuleCount",
                None,
                None,
                "Number of ChainPosClassRule tables",
            ),
            (
                "Offset",
                "ChainPosClassRule",
                "ChainPosClassRuleCount",
                0,
                "Array of offsets to ChainPosClassRule tables-from beginning of ChainPosClassSet-ordered by preference",
            ),
        ],
    ),
    (
        "ChainPosClassRule",
        [
            (
                "uint16",
                "BacktrackGlyphCount",
                None,
                None,
                "Total number of glyphs in the backtrack sequence (number of glyphs to be matched before the first glyph)",
            ),
            (
                "uint16",
                "Backtrack",
                "BacktrackGlyphCount",
                0,
                "Array of backtracking classes(to be matched before the input sequence)",
            ),
            (
                "uint16",
                "InputGlyphCount",
                None,
                None,
                "Total number of classes in the input sequence (includes the first class)",
            ),
            (
                "uint16",
                "Input",
                "InputGlyphCount",
                -1,
                "Array of input classes(start with second class; to be matched with the input glyph sequence)",
            ),
            (
                "uint16",
                "LookAheadGlyphCount",
                None,
                None,
                "Total number of classes in the look ahead sequence (number of classes to be matched after the input sequence)",
            ),
            (
                "uint16",
                "LookAhead",
                "LookAheadGlyphCount",
                0,
                "Array of lookahead classes(to be matched after the input sequence)",
            ),
            ("uint16", "PosCount", None, None, "Number of PosLookupRecords"),
            (
                "struct",
                "PosLookupRecord",
                "PosCount",
                0,
                "Array of PosLookupRecords (in design order)",
            ),
        ],
    ),
    (
        "ChainContextPosFormat3",
        [
            ("uint16", "PosFormat", None, None, "Format identifier-format = 3"),
            (
                "uint16",
                "BacktrackGlyphCount",
                None,
                None,
                "Number of glyphs in the backtracking sequence",
            ),
            (
                "Offset",
                "BacktrackCoverage",
                "BacktrackGlyphCount",
                0,
                "Array of offsets to coverage tables in backtracking sequence, in glyph sequence order",
            ),
            (
                "uint16",
                "InputGlyphCount",
                None,
                None,
                "Number of glyphs in input sequence",
            ),
            (
                "Offset",
                "InputCoverage",
                "InputGlyphCount",
                0,
                "Array of offsets to coverage tables in input sequence, in glyph sequence order",
            ),
            (
                "uint16",
                "LookAheadGlyphCount",
                None,
                None,
                "Number of glyphs in lookahead sequence",
            ),
            (
                "Offset",
                "LookAheadCoverage",
                "LookAheadGlyphCount",
                0,
                "Array of offsets to coverage tables in lookahead sequence, in glyph sequence order",
            ),
            ("uint16", "PosCount", None, None, "Number of PosLookupRecords"),
            (
                "struct",
                "PosLookupRecord",
                "PosCount",
                0,
                "Array of PosLookupRecords,in design order",
            ),
        ],
    ),
    (
        "ExtensionPosFormat1",
        [
            ("uint16", "ExtFormat", None, None, "Format identifier. Set to 1."),
            (
                "uint16",
                "ExtensionLookupType",
                None,
                None,
                "Lookup type of subtable referenced by ExtensionOffset (i.e. the extension subtable).",
            ),
            ("LOffset", "ExtSubTable", None, None, "Offset to SubTable"),
        ],
    ),
    # 	('ValueRecord', [
    # 		('int16', 'XPlacement', None, None, 'Horizontal adjustment for placement-in design units'),
    # 		('int16', 'YPlacement', None, None, 'Vertical adjustment for placement-in design units'),
    # 		('int16', 'XAdvance', None, None, 'Horizontal adjustment for advance-in design units (only used for horizontal writing)'),
    # 		('int16', 'YAdvance', None, None, 'Vertical adjustment for advance-in design units (only used for vertical writing)'),
    # 		('Offset', 'XPlaDevice', None, None, 'Offset to Device table for horizontal placement-measured from beginning of PosTable (may be NULL)'),
    # 		('Offset', 'YPlaDevice', None, None, 'Offset to Device table for vertical placement-measured from beginning of PosTable (may be NULL)'),
    # 		('Offset', 'XAdvDevice', None, None, 'Offset to Device table for horizontal advance-measured from beginning of PosTable (may be NULL)'),
    # 		('Offset', 'YAdvDevice', None, None, 'Offset to Device table for vertical advance-measured from beginning of PosTable (may be NULL)'),
    # 	]),
    (
        "AnchorFormat1",
        [
            ("uint16", "AnchorFormat", None, None, "Format identifier-format = 1"),
            ("int16", "XCoordinate", None, None, "Horizontal value-in design units"),
            ("int16", "YCoordinate", None, None, "Vertical value-in design units"),
        ],
    ),
    (
        "AnchorFormat2",
        [
            ("uint16", "AnchorFormat", None, None, "Format identifier-format = 2"),
            ("int16", "XCoordinate", None, None, "Horizontal value-in design units"),
            ("int16", "YCoordinate", None, None, "Vertical value-in design units"),
            ("uint16", "AnchorPoint", None, None, "Index to glyph contour point"),
        ],
    ),
    (
        "AnchorFormat3",
        [
            ("uint16", "AnchorFormat", None, None, "Format identifier-format = 3"),
            ("int16", "XCoordinate", None, None, "Horizontal value-in design units"),
            ("int16", "YCoordinate", None, None, "Vertical value-in design units"),
            (
                "Offset",
                "XDeviceTable",
                None,
                None,
                "Offset to Device table for X coordinate- from beginning of Anchor table (may be NULL)",
            ),
            (
                "Offset",
                "YDeviceTable",
                None,
                None,
                "Offset to Device table for Y coordinate- from beginning of Anchor table (may be NULL)",
            ),
        ],
    ),
    (
        "MarkArray",
        [
            ("uint16", "MarkCount", None, None, "Number of MarkRecords"),
            (
                "struct",
                "MarkRecord",
                "MarkCount",
                0,
                "Array of MarkRecords-in Coverage order",
            ),
        ],
    ),
    (
        "MarkRecord",
        [
            ("uint16", "Class", None, None, "Class defined for this mark"),
            (
                "Offset",
                "MarkAnchor",
                None,
                None,
                "Offset to Anchor table-from beginning of MarkArray table",
            ),
        ],
    ),
    #
    # gsub
    #
    (
        "GSUB",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the GSUB table- 0x00010000 or 0x00010001",
            ),
            (
                "Offset",
                "ScriptList",
                None,
                None,
                "Offset to ScriptList table-from beginning of GSUB table",
            ),
            (
                "Offset",
                "FeatureList",
                None,
                None,
                "Offset to FeatureList table-from beginning of GSUB table",
            ),
            (
                "Offset",
                "LookupList",
                None,
                None,
                "Offset to LookupList table-from beginning of GSUB table",
            ),
            (
                "LOffset",
                "FeatureVariations",
                None,
                "Version >= 0x00010001",
                "Offset to FeatureVariations table-from beginning of GSUB table",
            ),
        ],
    ),
    (
        "SingleSubstFormat1",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of Substitution table",
            ),
            (
                "uint16",
                "DeltaGlyphID",
                None,
                None,
                "Add to original GlyphID modulo 65536 to get substitute GlyphID",
            ),
        ],
    ),
    (
        "SingleSubstFormat2",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 2"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of Substitution table",
            ),
            (
                "uint16",
                "GlyphCount",
                None,
                None,
                "Number of GlyphIDs in the Substitute array",
            ),
            (
                "GlyphID",
                "Substitute",
                "GlyphCount",
                0,
                "Array of substitute GlyphIDs-ordered by Coverage Index",
            ),
        ],
    ),
    (
        "MultipleSubstFormat1",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of Substitution table",
            ),
            (
                "uint16",
                "SequenceCount",
                None,
                None,
                "Number of Sequence table offsets in the Sequence array",
            ),
            (
                "Offset",
                "Sequence",
                "SequenceCount",
                0,
                "Array of offsets to Sequence tables-from beginning of Substitution table-ordered by Coverage Index",
            ),
        ],
    ),
    (
        "Sequence",
        [
            (
                "uint16",
                "GlyphCount",
                None,
                None,
                "Number of GlyphIDs in the Substitute array. This should always be greater than 0.",
            ),
            (
                "GlyphID",
                "Substitute",
                "GlyphCount",
                0,
                "String of GlyphIDs to substitute",
            ),
        ],
    ),
    (
        "AlternateSubstFormat1",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of Substitution table",
            ),
            (
                "uint16",
                "AlternateSetCount",
                None,
                None,
                "Number of AlternateSet tables",
            ),
            (
                "Offset",
                "AlternateSet",
                "AlternateSetCount",
                0,
                "Array of offsets to AlternateSet tables-from beginning of Substitution table-ordered by Coverage Index",
            ),
        ],
    ),
    (
        "AlternateSet",
        [
            (
                "uint16",
                "GlyphCount",
                None,
                None,
                "Number of GlyphIDs in the Alternate array",
            ),
            (
                "GlyphID",
                "Alternate",
                "GlyphCount",
                0,
                "Array of alternate GlyphIDs-in arbitrary order",
            ),
        ],
    ),
    (
        "LigatureSubstFormat1",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of Substitution table",
            ),
            ("uint16", "LigSetCount", None, None, "Number of LigatureSet tables"),
            (
                "Offset",
                "LigatureSet",
                "LigSetCount",
                0,
                "Array of offsets to LigatureSet tables-from beginning of Substitution table-ordered by Coverage Index",
            ),
        ],
    ),
    (
        "LigatureSet",
        [
            ("uint16", "LigatureCount", None, None, "Number of Ligature tables"),
            (
                "Offset",
                "Ligature",
                "LigatureCount",
                0,
                "Array of offsets to Ligature tables-from beginning of LigatureSet table-ordered by preference",
            ),
        ],
    ),
    (
        "Ligature",
        [
            ("GlyphID", "LigGlyph", None, None, "GlyphID of ligature to substitute"),
            ("uint16", "CompCount", None, None, "Number of components in the ligature"),
            (
                "GlyphID",
                "Component",
                "CompCount",
                -1,
                "Array of component GlyphIDs-start with the second component-ordered in writing direction",
            ),
        ],
    ),
    (
        "SubstLookupRecord",
        [
            (
                "uint16",
                "SequenceIndex",
                None,
                None,
                "Index into current glyph sequence-first glyph = 0",
            ),
            (
                "uint16",
                "LookupListIndex",
                None,
                None,
                "Lookup to apply to that position-zero-based",
            ),
        ],
    ),
    (
        "ContextSubstFormat1",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of Substitution table",
            ),
            (
                "uint16",
                "SubRuleSetCount",
                None,
                None,
                "Number of SubRuleSet tables-must equal GlyphCount in Coverage table",
            ),
            (
                "Offset",
                "SubRuleSet",
                "SubRuleSetCount",
                0,
                "Array of offsets to SubRuleSet tables-from beginning of Substitution table-ordered by Coverage Index",
            ),
        ],
    ),
    (
        "SubRuleSet",
        [
            ("uint16", "SubRuleCount", None, None, "Number of SubRule tables"),
            (
                "Offset",
                "SubRule",
                "SubRuleCount",
                0,
                "Array of offsets to SubRule tables-from beginning of SubRuleSet table-ordered by preference",
            ),
        ],
    ),
    (
        "SubRule",
        [
            (
                "uint16",
                "GlyphCount",
                None,
                None,
                "Total number of glyphs in input glyph sequence-includes the first glyph",
            ),
            ("uint16", "SubstCount", None, None, "Number of SubstLookupRecords"),
            (
                "GlyphID",
                "Input",
                "GlyphCount",
                -1,
                "Array of input GlyphIDs-start with second glyph",
            ),
            (
                "struct",
                "SubstLookupRecord",
                "SubstCount",
                0,
                "Array of SubstLookupRecords-in design order",
            ),
        ],
    ),
    (
        "ContextSubstFormat2",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 2"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of Substitution table",
            ),
            (
                "Offset",
                "ClassDef",
                None,
                None,
                "Offset to glyph ClassDef table-from beginning of Substitution table",
            ),
            ("uint16", "SubClassSetCount", None, None, "Number of SubClassSet tables"),
            (
                "Offset",
                "SubClassSet",
                "SubClassSetCount",
                0,
                "Array of offsets to SubClassSet tables-from beginning of Substitution table-ordered by class-may be NULL",
            ),
        ],
    ),
    (
        "SubClassSet",
        [
            (
                "uint16",
                "SubClassRuleCount",
                None,
                None,
                "Number of SubClassRule tables",
            ),
            (
                "Offset",
                "SubClassRule",
                "SubClassRuleCount",
                0,
                "Array of offsets to SubClassRule tables-from beginning of SubClassSet-ordered by preference",
            ),
        ],
    ),
    (
        "SubClassRule",
        [
            (
                "uint16",
                "GlyphCount",
                None,
                None,
                "Total number of classes specified for the context in the rule-includes the first class",
            ),
            ("uint16", "SubstCount", None, None, "Number of SubstLookupRecords"),
            (
                "uint16",
                "Class",
                "GlyphCount",
                -1,
                "Array of classes-beginning with the second class-to be matched to the input glyph class sequence",
            ),
            (
                "struct",
                "SubstLookupRecord",
                "SubstCount",
                0,
                "Array of Substitution lookups-in design order",
            ),
        ],
    ),
    (
        "ContextSubstFormat3",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 3"),
            (
                "uint16",
                "GlyphCount",
                None,
                None,
                "Number of glyphs in the input glyph sequence",
            ),
            ("uint16", "SubstCount", None, None, "Number of SubstLookupRecords"),
            (
                "Offset",
                "Coverage",
                "GlyphCount",
                0,
                "Array of offsets to Coverage table-from beginning of Substitution table-in glyph sequence order",
            ),
            (
                "struct",
                "SubstLookupRecord",
                "SubstCount",
                0,
                "Array of SubstLookupRecords-in design order",
            ),
        ],
    ),
    (
        "ChainContextSubstFormat1",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of Substitution table",
            ),
            (
                "uint16",
                "ChainSubRuleSetCount",
                None,
                None,
                "Number of ChainSubRuleSet tables-must equal GlyphCount in Coverage table",
            ),
            (
                "Offset",
                "ChainSubRuleSet",
                "ChainSubRuleSetCount",
                0,
                "Array of offsets to ChainSubRuleSet tables-from beginning of Substitution table-ordered by Coverage Index",
            ),
        ],
    ),
    (
        "ChainSubRuleSet",
        [
            (
                "uint16",
                "ChainSubRuleCount",
                None,
                None,
                "Number of ChainSubRule tables",
            ),
            (
                "Offset",
                "ChainSubRule",
                "ChainSubRuleCount",
                0,
                "Array of offsets to ChainSubRule tables-from beginning of ChainSubRuleSet table-ordered by preference",
            ),
        ],
    ),
    (
        "ChainSubRule",
        [
            (
                "uint16",
                "BacktrackGlyphCount",
                None,
                None,
                "Total number of glyphs in the backtrack sequence (number of glyphs to be matched before the first glyph)",
            ),
            (
                "GlyphID",
                "Backtrack",
                "BacktrackGlyphCount",
                0,
                "Array of backtracking GlyphID's (to be matched before the input sequence)",
            ),
            (
                "uint16",
                "InputGlyphCount",
                None,
                None,
                "Total number of glyphs in the input sequence (includes the first glyph)",
            ),
            (
                "GlyphID",
                "Input",
                "InputGlyphCount",
                -1,
                "Array of input GlyphIDs (start with second glyph)",
            ),
            (
                "uint16",
                "LookAheadGlyphCount",
                None,
                None,
                "Total number of glyphs in the look ahead sequence (number of glyphs to be matched after the input sequence)",
            ),
            (
                "GlyphID",
                "LookAhead",
                "LookAheadGlyphCount",
                0,
                "Array of lookahead GlyphID's (to be matched after the input sequence)",
            ),
            ("uint16", "SubstCount", None, None, "Number of SubstLookupRecords"),
            (
                "struct",
                "SubstLookupRecord",
                "SubstCount",
                0,
                "Array of SubstLookupRecords (in design order)",
            ),
        ],
    ),
    (
        "ChainContextSubstFormat2",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 2"),
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table-from beginning of Substitution table",
            ),
            (
                "Offset",
                "BacktrackClassDef",
                None,
                None,
                "Offset to glyph ClassDef table containing backtrack sequence data-from beginning of Substitution table",
            ),
            (
                "Offset",
                "InputClassDef",
                None,
                None,
                "Offset to glyph ClassDef table containing input sequence data-from beginning of Substitution table",
            ),
            (
                "Offset",
                "LookAheadClassDef",
                None,
                None,
                "Offset to glyph ClassDef table containing lookahead sequence data-from beginning of Substitution table",
            ),
            (
                "uint16",
                "ChainSubClassSetCount",
                None,
                None,
                "Number of ChainSubClassSet tables",
            ),
            (
                "Offset",
                "ChainSubClassSet",
                "ChainSubClassSetCount",
                0,
                "Array of offsets to ChainSubClassSet tables-from beginning of Substitution table-ordered by input class-may be NULL",
            ),
        ],
    ),
    (
        "ChainSubClassSet",
        [
            (
                "uint16",
                "ChainSubClassRuleCount",
                None,
                None,
                "Number of ChainSubClassRule tables",
            ),
            (
                "Offset",
                "ChainSubClassRule",
                "ChainSubClassRuleCount",
                0,
                "Array of offsets to ChainSubClassRule tables-from beginning of ChainSubClassSet-ordered by preference",
            ),
        ],
    ),
    (
        "ChainSubClassRule",
        [
            (
                "uint16",
                "BacktrackGlyphCount",
                None,
                None,
                "Total number of glyphs in the backtrack sequence (number of glyphs to be matched before the first glyph)",
            ),
            (
                "uint16",
                "Backtrack",
                "BacktrackGlyphCount",
                0,
                "Array of backtracking classes(to be matched before the input sequence)",
            ),
            (
                "uint16",
                "InputGlyphCount",
                None,
                None,
                "Total number of classes in the input sequence (includes the first class)",
            ),
            (
                "uint16",
                "Input",
                "InputGlyphCount",
                -1,
                "Array of input classes(start with second class; to be matched with the input glyph sequence)",
            ),
            (
                "uint16",
                "LookAheadGlyphCount",
                None,
                None,
                "Total number of classes in the look ahead sequence (number of classes to be matched after the input sequence)",
            ),
            (
                "uint16",
                "LookAhead",
                "LookAheadGlyphCount",
                0,
                "Array of lookahead classes(to be matched after the input sequence)",
            ),
            ("uint16", "SubstCount", None, None, "Number of SubstLookupRecords"),
            (
                "struct",
                "SubstLookupRecord",
                "SubstCount",
                0,
                "Array of SubstLookupRecords (in design order)",
            ),
        ],
    ),
    (
        "ChainContextSubstFormat3",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 3"),
            (
                "uint16",
                "BacktrackGlyphCount",
                None,
                None,
                "Number of glyphs in the backtracking sequence",
            ),
            (
                "Offset",
                "BacktrackCoverage",
                "BacktrackGlyphCount",
                0,
                "Array of offsets to coverage tables in backtracking sequence, in glyph sequence order",
            ),
            (
                "uint16",
                "InputGlyphCount",
                None,
                None,
                "Number of glyphs in input sequence",
            ),
            (
                "Offset",
                "InputCoverage",
                "InputGlyphCount",
                0,
                "Array of offsets to coverage tables in input sequence, in glyph sequence order",
            ),
            (
                "uint16",
                "LookAheadGlyphCount",
                None,
                None,
                "Number of glyphs in lookahead sequence",
            ),
            (
                "Offset",
                "LookAheadCoverage",
                "LookAheadGlyphCount",
                0,
                "Array of offsets to coverage tables in lookahead sequence, in glyph sequence order",
            ),
            ("uint16", "SubstCount", None, None, "Number of SubstLookupRecords"),
            (
                "struct",
                "SubstLookupRecord",
                "SubstCount",
                0,
                "Array of SubstLookupRecords, in design order",
            ),
        ],
    ),
    (
        "ExtensionSubstFormat1",
        [
            ("uint16", "ExtFormat", None, None, "Format identifier. Set to 1."),
            (
                "uint16",
                "ExtensionLookupType",
                None,
                None,
                "Lookup type of subtable referenced by ExtensionOffset (i.e. the extension subtable).",
            ),
            (
                "LOffset",
                "ExtSubTable",
                None,
                None,
                "Array of offsets to Lookup tables-from beginning of LookupList -zero based (first lookup is Lookup index = 0)",
            ),
        ],
    ),
    (
        "ReverseChainSingleSubstFormat1",
        [
            ("uint16", "SubstFormat", None, None, "Format identifier-format = 1"),
            (
                "Offset",
                "Coverage",
                None,
                0,
                "Offset to Coverage table - from beginning of Substitution table",
            ),
            (
                "uint16",
                "BacktrackGlyphCount",
                None,
                None,
                "Number of glyphs in the backtracking sequence",
            ),
            (
                "Offset",
                "BacktrackCoverage",
                "BacktrackGlyphCount",
                0,
                "Array of offsets to coverage tables in backtracking sequence, in glyph sequence order",
            ),
            (
                "uint16",
                "LookAheadGlyphCount",
                None,
                None,
                "Number of glyphs in lookahead sequence",
            ),
            (
                "Offset",
                "LookAheadCoverage",
                "LookAheadGlyphCount",
                0,
                "Array of offsets to coverage tables in lookahead sequence, in glyph sequence order",
            ),
            (
                "uint16",
                "GlyphCount",
                None,
                None,
                "Number of GlyphIDs in the Substitute array",
            ),
            (
                "GlyphID",
                "Substitute",
                "GlyphCount",
                0,
                "Array of substitute GlyphIDs-ordered by Coverage index",
            ),
        ],
    ),
    #
    # gdef
    #
    (
        "GDEF",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the GDEF table- 0x00010000, 0x00010002, or 0x00010003",
            ),
            (
                "Offset",
                "GlyphClassDef",
                None,
                None,
                "Offset to class definition table for glyph type-from beginning of GDEF header (may be NULL)",
            ),
            (
                "Offset",
                "AttachList",
                None,
                None,
                "Offset to list of glyphs with attachment points-from beginning of GDEF header (may be NULL)",
            ),
            (
                "Offset",
                "LigCaretList",
                None,
                None,
                "Offset to list of positioning points for ligature carets-from beginning of GDEF header (may be NULL)",
            ),
            (
                "Offset",
                "MarkAttachClassDef",
                None,
                None,
                "Offset to class definition table for mark attachment type-from beginning of GDEF header (may be NULL)",
            ),
            (
                "Offset",
                "MarkGlyphSetsDef",
                None,
                "Version >= 0x00010002",
                "Offset to the table of mark set definitions-from beginning of GDEF header (may be NULL)",
            ),
            (
                "LOffset",
                "VarStore",
                None,
                "Version >= 0x00010003",
                "Offset to variation store (may be NULL)",
            ),
        ],
    ),
    (
        "AttachList",
        [
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table - from beginning of AttachList table",
            ),
            (
                "uint16",
                "GlyphCount",
                None,
                None,
                "Number of glyphs with attachment points",
            ),
            (
                "Offset",
                "AttachPoint",
                "GlyphCount",
                0,
                "Array of offsets to AttachPoint tables-from beginning of AttachList table-in Coverage Index order",
            ),
        ],
    ),
    (
        "AttachPoint",
        [
            (
                "uint16",
                "PointCount",
                None,
                None,
                "Number of attachment points on this glyph",
            ),
            (
                "uint16",
                "PointIndex",
                "PointCount",
                0,
                "Array of contour point indices -in increasing numerical order",
            ),
        ],
    ),
    (
        "LigCaretList",
        [
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table - from beginning of LigCaretList table",
            ),
            ("uint16", "LigGlyphCount", None, None, "Number of ligature glyphs"),
            (
                "Offset",
                "LigGlyph",
                "LigGlyphCount",
                0,
                "Array of offsets to LigGlyph tables-from beginning of LigCaretList table-in Coverage Index order",
            ),
        ],
    ),
    (
        "LigGlyph",
        [
            (
                "uint16",
                "CaretCount",
                None,
                None,
                "Number of CaretValues for this ligature (components - 1)",
            ),
            (
                "Offset",
                "CaretValue",
                "CaretCount",
                0,
                "Array of offsets to CaretValue tables-from beginning of LigGlyph table-in increasing coordinate order",
            ),
        ],
    ),
    (
        "CaretValueFormat1",
        [
            ("uint16", "CaretValueFormat", None, None, "Format identifier-format = 1"),
            ("int16", "Coordinate", None, None, "X or Y value, in design units"),
        ],
    ),
    (
        "CaretValueFormat2",
        [
            ("uint16", "CaretValueFormat", None, None, "Format identifier-format = 2"),
            ("uint16", "CaretValuePoint", None, None, "Contour point index on glyph"),
        ],
    ),
    (
        "CaretValueFormat3",
        [
            ("uint16", "CaretValueFormat", None, None, "Format identifier-format = 3"),
            ("int16", "Coordinate", None, None, "X or Y value, in design units"),
            (
                "Offset",
                "DeviceTable",
                None,
                None,
                "Offset to Device table for X or Y value-from beginning of CaretValue table",
            ),
        ],
    ),
    (
        "MarkGlyphSetsDef",
        [
            ("uint16", "MarkSetTableFormat", None, None, "Format identifier == 1"),
            ("uint16", "MarkSetCount", None, None, "Number of mark sets defined"),
            (
                "LOffset",
                "Coverage",
                "MarkSetCount",
                0,
                "Array of offsets to mark set coverage tables.",
            ),
        ],
    ),
    #
    # base
    #
    (
        "BASE",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the BASE table-initially 0x00010000",
            ),
            (
                "Offset",
                "HorizAxis",
                None,
                None,
                "Offset to horizontal Axis table-from beginning of BASE table-may be NULL",
            ),
            (
                "Offset",
                "VertAxis",
                None,
                None,
                "Offset to vertical Axis table-from beginning of BASE table-may be NULL",
            ),
            (
                "LOffset",
                "VarStore",
                None,
                "Version >= 0x00010001",
                "Offset to variation store (may be NULL)",
            ),
        ],
    ),
    (
        "Axis",
        [
            (
                "Offset",
                "BaseTagList",
                None,
                None,
                "Offset to BaseTagList table-from beginning of Axis table-may be NULL",
            ),
            (
                "Offset",
                "BaseScriptList",
                None,
                None,
                "Offset to BaseScriptList table-from beginning of Axis table",
            ),
        ],
    ),
    (
        "BaseTagList",
        [
            (
                "uint16",
                "BaseTagCount",
                None,
                None,
                "Number of baseline identification tags in this text direction-may be zero (0)",
            ),
            (
                "Tag",
                "BaselineTag",
                "BaseTagCount",
                0,
                "Array of 4-byte baseline identification tags-must be in alphabetical order",
            ),
        ],
    ),
    (
        "BaseScriptList",
        [
            (
                "uint16",
                "BaseScriptCount",
                None,
                None,
                "Number of BaseScriptRecords defined",
            ),
            (
                "struct",
                "BaseScriptRecord",
                "BaseScriptCount",
                0,
                "Array of BaseScriptRecords-in alphabetical order by BaseScriptTag",
            ),
        ],
    ),
    (
        "BaseScriptRecord",
        [
            ("Tag", "BaseScriptTag", None, None, "4-byte script identification tag"),
            (
                "Offset",
                "BaseScript",
                None,
                None,
                "Offset to BaseScript table-from beginning of BaseScriptList",
            ),
        ],
    ),
    (
        "BaseScript",
        [
            (
                "Offset",
                "BaseValues",
                None,
                None,
                "Offset to BaseValues table-from beginning of BaseScript table-may be NULL",
            ),
            (
                "Offset",
                "DefaultMinMax",
                None,
                None,
                "Offset to MinMax table- from beginning of BaseScript table-may be NULL",
            ),
            (
                "uint16",
                "BaseLangSysCount",
                None,
                None,
                "Number of BaseLangSysRecords defined-may be zero (0)",
            ),
            (
                "struct",
                "BaseLangSysRecord",
                "BaseLangSysCount",
                0,
                "Array of BaseLangSysRecords-in alphabetical order by BaseLangSysTag",
            ),
        ],
    ),
    (
        "BaseLangSysRecord",
        [
            (
                "Tag",
                "BaseLangSysTag",
                None,
                None,
                "4-byte language system identification tag",
            ),
            (
                "Offset",
                "MinMax",
                None,
                None,
                "Offset to MinMax table-from beginning of BaseScript table",
            ),
        ],
    ),
    (
        "BaseValues",
        [
            (
                "uint16",
                "DefaultIndex",
                None,
                None,
                "Index number of default baseline for this script-equals index position of baseline tag in BaselineArray of the BaseTagList",
            ),
            (
                "uint16",
                "BaseCoordCount",
                None,
                None,
                "Number of BaseCoord tables defined-should equal BaseTagCount in the BaseTagList",
            ),
            (
                "Offset",
                "BaseCoord",
                "BaseCoordCount",
                0,
                "Array of offsets to BaseCoord-from beginning of BaseValues table-order matches BaselineTag array in the BaseTagList",
            ),
        ],
    ),
    (
        "MinMax",
        [
            (
                "Offset",
                "MinCoord",
                None,
                None,
                "Offset to BaseCoord table-defines minimum extent value-from the beginning of MinMax table-may be NULL",
            ),
            (
                "Offset",
                "MaxCoord",
                None,
                None,
                "Offset to BaseCoord table-defines maximum extent value-from the beginning of MinMax table-may be NULL",
            ),
            (
                "uint16",
                "FeatMinMaxCount",
                None,
                None,
                "Number of FeatMinMaxRecords-may be zero (0)",
            ),
            (
                "struct",
                "FeatMinMaxRecord",
                "FeatMinMaxCount",
                0,
                "Array of FeatMinMaxRecords-in alphabetical order, by FeatureTableTag",
            ),
        ],
    ),
    (
        "FeatMinMaxRecord",
        [
            (
                "Tag",
                "FeatureTableTag",
                None,
                None,
                "4-byte feature identification tag-must match FeatureTag in FeatureList",
            ),
            (
                "Offset",
                "MinCoord",
                None,
                None,
                "Offset to BaseCoord table-defines minimum extent value-from beginning of MinMax table-may be NULL",
            ),
            (
                "Offset",
                "MaxCoord",
                None,
                None,
                "Offset to BaseCoord table-defines maximum extent value-from beginning of MinMax table-may be NULL",
            ),
        ],
    ),
    (
        "BaseCoordFormat1",
        [
            ("uint16", "BaseCoordFormat", None, None, "Format identifier-format = 1"),
            ("int16", "Coordinate", None, None, "X or Y value, in design units"),
        ],
    ),
    (
        "BaseCoordFormat2",
        [
            ("uint16", "BaseCoordFormat", None, None, "Format identifier-format = 2"),
            ("int16", "Coordinate", None, None, "X or Y value, in design units"),
            ("GlyphID", "ReferenceGlyph", None, None, "GlyphID of control glyph"),
            (
                "uint16",
                "BaseCoordPoint",
                None,
                None,
                "Index of contour point on the ReferenceGlyph",
            ),
        ],
    ),
    (
        "BaseCoordFormat3",
        [
            ("uint16", "BaseCoordFormat", None, None, "Format identifier-format = 3"),
            ("int16", "Coordinate", None, None, "X or Y value, in design units"),
            (
                "Offset",
                "DeviceTable",
                None,
                None,
                "Offset to Device table for X or Y value",
            ),
        ],
    ),
    #
    # jstf
    #
    (
        "JSTF",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the JSTF table-initially set to 0x00010000",
            ),
            (
                "uint16",
                "JstfScriptCount",
                None,
                None,
                "Number of JstfScriptRecords in this table",
            ),
            (
                "struct",
                "JstfScriptRecord",
                "JstfScriptCount",
                0,
                "Array of JstfScriptRecords-in alphabetical order, by JstfScriptTag",
            ),
        ],
    ),
    (
        "JstfScriptRecord",
        [
            ("Tag", "JstfScriptTag", None, None, "4-byte JstfScript identification"),
            (
                "Offset",
                "JstfScript",
                None,
                None,
                "Offset to JstfScript table-from beginning of JSTF Header",
            ),
        ],
    ),
    (
        "JstfScript",
        [
            (
                "Offset",
                "ExtenderGlyph",
                None,
                None,
                "Offset to ExtenderGlyph table-from beginning of JstfScript table-may be NULL",
            ),
            (
                "Offset",
                "DefJstfLangSys",
                None,
                None,
                "Offset to Default JstfLangSys table-from beginning of JstfScript table-may be NULL",
            ),
            (
                "uint16",
                "JstfLangSysCount",
                None,
                None,
                "Number of JstfLangSysRecords in this table- may be zero (0)",
            ),
            (
                "struct",
                "JstfLangSysRecord",
                "JstfLangSysCount",
                0,
                "Array of JstfLangSysRecords-in alphabetical order, by JstfLangSysTag",
            ),
        ],
    ),
    (
        "JstfLangSysRecord",
        [
            ("Tag", "JstfLangSysTag", None, None, "4-byte JstfLangSys identifier"),
            (
                "Offset",
                "JstfLangSys",
                None,
                None,
                "Offset to JstfLangSys table-from beginning of JstfScript table",
            ),
        ],
    ),
    (
        "ExtenderGlyph",
        [
            (
                "uint16",
                "GlyphCount",
                None,
                None,
                "Number of Extender Glyphs in this script",
            ),
            (
                "GlyphID",
                "ExtenderGlyph",
                "GlyphCount",
                0,
                "GlyphIDs-in increasing numerical order",
            ),
        ],
    ),
    (
        "JstfLangSys",
        [
            (
                "uint16",
                "JstfPriorityCount",
                None,
                None,
                "Number of JstfPriority tables",
            ),
            (
                "Offset",
                "JstfPriority",
                "JstfPriorityCount",
                0,
                "Array of offsets to JstfPriority tables-from beginning of JstfLangSys table-in priority order",
            ),
        ],
    ),
    (
        "JstfPriority",
        [
            (
                "Offset",
                "ShrinkageEnableGSUB",
                None,
                None,
                "Offset to Shrinkage Enable JstfGSUBModList table-from beginning of JstfPriority table-may be NULL",
            ),
            (
                "Offset",
                "ShrinkageDisableGSUB",
                None,
                None,
                "Offset to Shrinkage Disable JstfGSUBModList table-from beginning of JstfPriority table-may be NULL",
            ),
            (
                "Offset",
                "ShrinkageEnableGPOS",
                None,
                None,
                "Offset to Shrinkage Enable JstfGPOSModList table-from beginning of JstfPriority table-may be NULL",
            ),
            (
                "Offset",
                "ShrinkageDisableGPOS",
                None,
                None,
                "Offset to Shrinkage Disable JstfGPOSModList table-from beginning of JstfPriority table-may be NULL",
            ),
            (
                "Offset",
                "ShrinkageJstfMax",
                None,
                None,
                "Offset to Shrinkage JstfMax table-from beginning of JstfPriority table -may be NULL",
            ),
            (
                "Offset",
                "ExtensionEnableGSUB",
                None,
                None,
                "Offset to Extension Enable JstfGSUBModList table-may be NULL",
            ),
            (
                "Offset",
                "ExtensionDisableGSUB",
                None,
                None,
                "Offset to Extension Disable JstfGSUBModList table-from beginning of JstfPriority table-may be NULL",
            ),
            (
                "Offset",
                "ExtensionEnableGPOS",
                None,
                None,
                "Offset to Extension Enable JstfGSUBModList table-may be NULL",
            ),
            (
                "Offset",
                "ExtensionDisableGPOS",
                None,
                None,
                "Offset to Extension Disable JstfGSUBModList table-from beginning of JstfPriority table-may be NULL",
            ),
            (
                "Offset",
                "ExtensionJstfMax",
                None,
                None,
                "Offset to Extension JstfMax table-from beginning of JstfPriority table -may be NULL",
            ),
        ],
    ),
    (
        "JstfGSUBModList",
        [
            (
                "uint16",
                "LookupCount",
                None,
                None,
                "Number of lookups for this modification",
            ),
            (
                "uint16",
                "GSUBLookupIndex",
                "LookupCount",
                0,
                "Array of LookupIndex identifiers in GSUB-in increasing numerical order",
            ),
        ],
    ),
    (
        "JstfGPOSModList",
        [
            (
                "uint16",
                "LookupCount",
                None,
                None,
                "Number of lookups for this modification",
            ),
            (
                "uint16",
                "GPOSLookupIndex",
                "LookupCount",
                0,
                "Array of LookupIndex identifiers in GPOS-in increasing numerical order",
            ),
        ],
    ),
    (
        "JstfMax",
        [
            (
                "uint16",
                "LookupCount",
                None,
                None,
                "Number of lookup Indices for this modification",
            ),
            (
                "Offset",
                "Lookup",
                "LookupCount",
                0,
                "Array of offsets to GPOS-type lookup tables-from beginning of JstfMax table-in design order",
            ),
        ],
    ),
    #
    # STAT
    #
    (
        "STAT",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the table-initially set to 0x00010000, currently 0x00010002.",
            ),
            (
                "uint16",
                "DesignAxisRecordSize",
                None,
                None,
                "Size in bytes of each design axis record",
            ),
            ("uint16", "DesignAxisCount", None, None, "Number of design axis records"),
            (
                "LOffsetTo(AxisRecordArray)",
                "DesignAxisRecord",
                None,
                None,
                "Offset in bytes from the beginning of the STAT table to the start of the design axes array",
            ),
            ("uint16", "AxisValueCount", None, None, "Number of axis value tables"),
            (
                "LOffsetTo(AxisValueArray)",
                "AxisValueArray",
                None,
                None,
                "Offset in bytes from the beginning of the STAT table to the start of the axes value offset array",
            ),
            (
                "NameID",
                "ElidedFallbackNameID",
                None,
                "Version >= 0x00010001",
                "NameID to use when all style attributes are elided.",
            ),
        ],
    ),
    (
        "AxisRecordArray",
        [
            ("AxisRecord", "Axis", "DesignAxisCount", 0, "Axis records"),
        ],
    ),
    (
        "AxisRecord",
        [
            (
                "Tag",
                "AxisTag",
                None,
                None,
                "A tag identifying the axis of design variation",
            ),
            (
                "NameID",
                "AxisNameID",
                None,
                None,
                'The name ID for entries in the "name" table that provide a display string for this axis',
            ),
            (
                "uint16",
                "AxisOrdering",
                None,
                None,
                "A value that applications can use to determine primary sorting of face names, or for ordering of descriptors when composing family or face names",
            ),
            (
                "uint8",
                "MoreBytes",
                "DesignAxisRecordSize",
                -8,
                "Extra bytes.  Set to empty array.",
            ),
        ],
    ),
    (
        "AxisValueArray",
        [
            ("Offset", "AxisValue", "AxisValueCount", 0, "Axis values"),
        ],
    ),
    (
        "AxisValueFormat1",
        [
            ("uint16", "Format", None, None, "Format, = 1"),
            (
                "uint16",
                "AxisIndex",
                None,
                None,
                "Index into the axis record array identifying the axis of design variation to which the axis value record applies.",
            ),
            ("STATFlags", "Flags", None, None, "Flags."),
            ("NameID", "ValueNameID", None, None, ""),
            ("Fixed", "Value", None, None, ""),
        ],
    ),
    (
        "AxisValueFormat2",
        [
            ("uint16", "Format", None, None, "Format, = 2"),
            (
                "uint16",
                "AxisIndex",
                None,
                None,
                "Index into the axis record array identifying the axis of design variation to which the axis value record applies.",
            ),
            ("STATFlags", "Flags", None, None, "Flags."),
            ("NameID", "ValueNameID", None, None, ""),
            ("Fixed", "NominalValue", None, None, ""),
            ("Fixed", "RangeMinValue", None, None, ""),
            ("Fixed", "RangeMaxValue", None, None, ""),
        ],
    ),
    (
        "AxisValueFormat3",
        [
            ("uint16", "Format", None, None, "Format, = 3"),
            (
                "uint16",
                "AxisIndex",
                None,
                None,
                "Index into the axis record array identifying the axis of design variation to which the axis value record applies.",
            ),
            ("STATFlags", "Flags", None, None, "Flags."),
            ("NameID", "ValueNameID", None, None, ""),
            ("Fixed", "Value", None, None, ""),
            ("Fixed", "LinkedValue", None, None, ""),
        ],
    ),
    (
        "AxisValueFormat4",
        [
            ("uint16", "Format", None, None, "Format, = 4"),
            (
                "uint16",
                "AxisCount",
                None,
                None,
                "The total number of axes contributing to this axis-values combination.",
            ),
            ("STATFlags", "Flags", None, None, "Flags."),
            ("NameID", "ValueNameID", None, None, ""),
            (
                "struct",
                "AxisValueRecord",
                "AxisCount",
                0,
                "Array of AxisValue records that provide the combination of axis values, one for each contributing axis. ",
            ),
        ],
    ),
    (
        "AxisValueRecord",
        [
            (
                "uint16",
                "AxisIndex",
                None,
                None,
                "Index into the axis record array identifying the axis of design variation to which the axis value record applies.",
            ),
            ("Fixed", "Value", None, None, "A numeric value for this attribute value."),
        ],
    ),
    #
    # Variation fonts
    #
    # GSUB/GPOS FeatureVariations
    (
        "FeatureVariations",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the table-initially set to 0x00010000",
            ),
            (
                "uint32",
                "FeatureVariationCount",
                None,
                None,
                "Number of records in the FeatureVariationRecord array",
            ),
            (
                "struct",
                "FeatureVariationRecord",
                "FeatureVariationCount",
                0,
                "Array of FeatureVariationRecord",
            ),
        ],
    ),
    (
        "FeatureVariationRecord",
        [
            (
                "LOffset",
                "ConditionSet",
                None,
                None,
                "Offset to a ConditionSet table, from beginning of the FeatureVariations table.",
            ),
            (
                "LOffset",
                "FeatureTableSubstitution",
                None,
                None,
                "Offset to a FeatureTableSubstitution table, from beginning of the FeatureVariations table",
            ),
        ],
    ),
    (
        "ConditionList",
        [
            (
                "uint32",
                "ConditionCount",
                None,
                None,
                "Number of condition tables in the ConditionTable array",
            ),
            (
                "LOffset",
                "ConditionTable",
                "ConditionCount",
                0,
                "Array of offset to condition tables, from the beginning of the ConditionList table.",
            ),
        ],
    ),
    (
        "ConditionSet",
        [
            (
                "uint16",
                "ConditionCount",
                None,
                None,
                "Number of condition tables in the ConditionTable array",
            ),
            (
                "LOffset",
                "ConditionTable",
                "ConditionCount",
                0,
                "Array of offset to condition tables, from the beginning of the ConditionSet table.",
            ),
        ],
    ),
    (
        "ConditionTableFormat1",
        [
            ("uint16", "Format", None, None, "Format, = 1"),
            (
                "uint16",
                "AxisIndex",
                None,
                None,
                "Index for the variation axis within the fvar table, base 0.",
            ),
            (
                "F2Dot14",
                "FilterRangeMinValue",
                None,
                None,
                "Minimum normalized axis value of the font variation instances that satisfy this condition.",
            ),
            (
                "F2Dot14",
                "FilterRangeMaxValue",
                None,
                None,
                "Maximum value that satisfies this condition.",
            ),
        ],
    ),
    (
        "ConditionTableFormat2",
        [
            ("uint16", "Format", None, None, "Format, = 2"),
            (
                "int16",
                "DefaultValue",
                None,
                None,
                "Value at default instance.",
            ),
            (
                "uint32",
                "VarIdx",
                None,
                None,
                "Variation index to vary the value based on current designspace location.",
            ),
        ],
    ),
    (
        "ConditionTableFormat3",
        [
            ("uint16", "Format", None, None, "Format, = 3"),
            (
                "uint8",
                "ConditionCount",
                None,
                None,
                "Index for the variation axis within the fvar table, base 0.",
            ),
            (
                "Offset24",
                "ConditionTable",
                "ConditionCount",
                0,
                "Array of condition tables for this conjunction (AND) expression.",
            ),
        ],
    ),
    (
        "ConditionTableFormat4",
        [
            ("uint16", "Format", None, None, "Format, = 4"),
            (
                "uint8",
                "ConditionCount",
                None,
                None,
                "Index for the variation axis within the fvar table, base 0.",
            ),
            (
                "Offset24",
                "ConditionTable",
                "ConditionCount",
                0,
                "Array of condition tables for this disjunction (OR) expression.",
            ),
        ],
    ),
    (
        "ConditionTableFormat5",
        [
            ("uint16", "Format", None, None, "Format, = 5"),
            (
                "Offset24",
                "ConditionTable",
                None,
                None,
                "Condition to negate.",
            ),
        ],
    ),
    (
        "FeatureTableSubstitution",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the table-initially set to 0x00010000",
            ),
            (
                "uint16",
                "SubstitutionCount",
                None,
                None,
                "Number of records in the FeatureVariationRecords array",
            ),
            (
                "FeatureTableSubstitutionRecord",
                "SubstitutionRecord",
                "SubstitutionCount",
                0,
                "Array of FeatureTableSubstitutionRecord",
            ),
        ],
    ),
    (
        "FeatureTableSubstitutionRecord",
        [
            ("uint16", "FeatureIndex", None, None, "The feature table index to match."),
            (
                "LOffset",
                "Feature",
                None,
                None,
                "Offset to an alternate feature table, from start of the FeatureTableSubstitution table.",
            ),
        ],
    ),
    # VariationStore
    (
        "VarRegionAxis",
        [
            ("F2Dot14", "StartCoord", None, None, ""),
            ("F2Dot14", "PeakCoord", None, None, ""),
            ("F2Dot14", "EndCoord", None, None, ""),
        ],
    ),
    (
        "VarRegion",
        [
            ("struct", "VarRegionAxis", "RegionAxisCount", 0, ""),
        ],
    ),
    (
        "VarRegionList",
        [
            ("uint16", "RegionAxisCount", None, None, ""),
            ("uint16", "RegionCount", None, None, ""),
            ("VarRegion", "Region", "RegionCount", 0, ""),
        ],
    ),
    (
        "VarData",
        [
            ("uint16", "ItemCount", None, None, ""),
            ("uint16", "NumShorts", None, None, ""),
            ("uint16", "VarRegionCount", None, None, ""),
            ("uint16", "VarRegionIndex", "VarRegionCount", 0, ""),
            ("VarDataValue", "Item", "ItemCount", 0, ""),
        ],
    ),
    (
        "VarStore",
        [
            ("uint16", "Format", None, None, "Set to 1."),
            ("LOffset", "VarRegionList", None, None, ""),
            ("uint16", "VarDataCount", None, None, ""),
            ("LOffset", "VarData", "VarDataCount", 0, ""),
        ],
    ),
    # Variation helpers
    (
        "VarIdxMap",
        [
            ("uint16", "EntryFormat", None, None, ""),  # Automatically computed
            ("uint16", "MappingCount", None, None, ""),  # Automatically computed
            ("VarIdxMapValue", "mapping", "", 0, "Array of compressed data"),
        ],
    ),
    (
        "DeltaSetIndexMapFormat0",
        [
            ("uint8", "Format", None, None, "Format of the DeltaSetIndexMap = 0"),
            ("uint8", "EntryFormat", None, None, ""),  # Automatically computed
            ("uint16", "MappingCount", None, None, ""),  # Automatically computed
            ("VarIdxMapValue", "mapping", "", 0, "Array of compressed data"),
        ],
    ),
    (
        "DeltaSetIndexMapFormat1",
        [
            ("uint8", "Format", None, None, "Format of the DeltaSetIndexMap = 1"),
            ("uint8", "EntryFormat", None, None, ""),  # Automatically computed
            ("uint32", "MappingCount", None, None, ""),  # Automatically computed
            ("VarIdxMapValue", "mapping", "", 0, "Array of compressed data"),
        ],
    ),
    # MultiVariationStore
    (
        "SparseVarRegionAxis",
        [
            ("uint16", "AxisIndex", None, None, ""),
            ("F2Dot14", "StartCoord", None, None, ""),
            ("F2Dot14", "PeakCoord", None, None, ""),
            ("F2Dot14", "EndCoord", None, None, ""),
        ],
    ),
    (
        "SparseVarRegion",
        [
            ("uint16", "SparseRegionCount", None, None, ""),
            ("struct", "SparseVarRegionAxis", "SparseRegionCount", 0, ""),
        ],
    ),
    (
        "SparseVarRegionList",
        [
            ("uint16", "RegionCount", None, None, ""),
            ("LOffsetTo(SparseVarRegion)", "Region", "RegionCount", 0, ""),
        ],
    ),
    (
        "MultiVarData",
        [
            ("uint8", "Format", None, None, "Set to 1."),
            ("uint16", "VarRegionCount", None, None, ""),
            ("uint16", "VarRegionIndex", "VarRegionCount", 0, ""),
            ("TupleList", "Item", "", 0, ""),
        ],
    ),
    (
        "MultiVarStore",
        [
            ("uint16", "Format", None, None, "Set to 1."),
            ("LOffset", "SparseVarRegionList", None, None, ""),
            ("uint16", "MultiVarDataCount", None, None, ""),
            ("LOffset", "MultiVarData", "MultiVarDataCount", 0, ""),
        ],
    ),
    # VariableComposites
    (
        "VARC",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the HVAR table-initially = 0x00010000",
            ),
            ("LOffset", "Coverage", None, None, ""),
            ("LOffset", "MultiVarStore", None, None, "(may be NULL)"),
            ("LOffset", "ConditionList", None, None, "(may be NULL)"),
            ("LOffset", "AxisIndicesList", None, None, "(may be NULL)"),
            ("LOffset", "VarCompositeGlyphs", None, None, ""),
        ],
    ),
    (
        "AxisIndicesList",
        [
            ("TupleList", "Item", "", 0, ""),
        ],
    ),
    (
        "VarCompositeGlyphs",
        [
            ("VarCompositeGlyphList", "VarCompositeGlyph", "", None, ""),
        ],
    ),
    # Glyph advance variations
    (
        "HVAR",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the HVAR table-initially = 0x00010000",
            ),
            ("LOffset", "VarStore", None, None, ""),
            ("LOffsetTo(VarIdxMap)", "AdvWidthMap", None, None, ""),
            ("LOffsetTo(VarIdxMap)", "LsbMap", None, None, ""),
            ("LOffsetTo(VarIdxMap)", "RsbMap", None, None, ""),
        ],
    ),
    (
        "VVAR",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the VVAR table-initially = 0x00010000",
            ),
            ("LOffset", "VarStore", None, None, ""),
            ("LOffsetTo(VarIdxMap)", "AdvHeightMap", None, None, ""),
            ("LOffsetTo(VarIdxMap)", "TsbMap", None, None, ""),
            ("LOffsetTo(VarIdxMap)", "BsbMap", None, None, ""),
            ("LOffsetTo(VarIdxMap)", "VOrgMap", None, None, "Vertical origin mapping."),
        ],
    ),
    # Font-wide metrics variations
    (
        "MetricsValueRecord",
        [
            ("Tag", "ValueTag", None, None, "4-byte font-wide measure identifier"),
            ("uint32", "VarIdx", None, None, "Combined outer-inner variation index"),
            (
                "uint8",
                "MoreBytes",
                "ValueRecordSize",
                -8,
                "Extra bytes.  Set to empty array.",
            ),
        ],
    ),
    (
        "MVAR",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the MVAR table-initially = 0x00010000",
            ),
            ("uint16", "Reserved", None, None, "Set to 0"),
            ("uint16", "ValueRecordSize", None, None, ""),
            ("uint16", "ValueRecordCount", None, None, ""),
            ("Offset", "VarStore", None, None, ""),
            ("MetricsValueRecord", "ValueRecord", "ValueRecordCount", 0, ""),
        ],
    ),
    #
    # math
    #
    (
        "MATH",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the MATH table-initially set to 0x00010000.",
            ),
            (
                "Offset",
                "MathConstants",
                None,
                None,
                "Offset to MathConstants table - from the beginning of MATH table.",
            ),
            (
                "Offset",
                "MathGlyphInfo",
                None,
                None,
                "Offset to MathGlyphInfo table - from the beginning of MATH table.",
            ),
            (
                "Offset",
                "MathVariants",
                None,
                None,
                "Offset to MathVariants table - from the beginning of MATH table.",
            ),
        ],
    ),
    (
        "MathValueRecord",
        [
            ("int16", "Value", None, None, "The X or Y value in design units."),
            (
                "Offset",
                "DeviceTable",
                None,
                None,
                "Offset to the device table - from the beginning of parent table. May be NULL. Suggested format for device table is 1.",
            ),
        ],
    ),
    (
        "MathConstants",
        [
            (
                "int16",
                "ScriptPercentScaleDown",
                None,
                None,
                "Percentage of scaling down for script level 1. Suggested value: 80%.",
            ),
            (
                "int16",
                "ScriptScriptPercentScaleDown",
                None,
                None,
                "Percentage of scaling down for script level 2 (ScriptScript). Suggested value: 60%.",
            ),
            (
                "uint16",
                "DelimitedSubFormulaMinHeight",
                None,
                None,
                "Minimum height required for a delimited expression to be treated as a subformula. Suggested value: normal line height x1.5.",
            ),
            (
                "uint16",
                "DisplayOperatorMinHeight",
                None,
                None,
                "Minimum height of n-ary operators (such as integral and summation) for formulas in display mode.",
            ),
            (
                "MathValueRecord",
                "MathLeading",
                None,
                None,
                "White space to be left between math formulas to ensure proper line spacing. For example, for applications that treat line gap as a part of line ascender, formulas with ink  going above (os2.sTypoAscender + os2.sTypoLineGap - MathLeading) or with ink going below os2.sTypoDescender will result in increasing line height.",
            ),
            ("MathValueRecord", "AxisHeight", None, None, "Axis height of the font."),
            (
                "MathValueRecord",
                "AccentBaseHeight",
                None,
                None,
                "Maximum (ink) height of accent base that does not require raising the accents. Suggested: x-height of the font (os2.sxHeight) plus any possible overshots.",
            ),
            (
                "MathValueRecord",
                "FlattenedAccentBaseHeight",
                None,
                None,
                "Maximum (ink) height of accent base that does not require flattening the accents. Suggested: cap height of the font (os2.sCapHeight).",
            ),
            (
                "MathValueRecord",
                "SubscriptShiftDown",
                None,
                None,
                "The standard shift down applied to subscript elements. Positive for moving in the downward direction. Suggested: os2.ySubscriptYOffset.",
            ),
            (
                "MathValueRecord",
                "SubscriptTopMax",
                None,
                None,
                "Maximum allowed height of the (ink) top of subscripts that does not require moving subscripts further down. Suggested: 4/5 x-height.",
            ),
            (
                "MathValueRecord",
                "SubscriptBaselineDropMin",
                None,
                None,
                "Minimum allowed drop of the baseline of subscripts relative to the (ink) bottom of the base. Checked for bases that are treated as a box or extended shape. Positive for subscript baseline dropped below the base bottom.",
            ),
            (
                "MathValueRecord",
                "SuperscriptShiftUp",
                None,
                None,
                "Standard shift up applied to superscript elements. Suggested: os2.ySuperscriptYOffset.",
            ),
            (
                "MathValueRecord",
                "SuperscriptShiftUpCramped",
                None,
                None,
                "Standard shift of superscripts relative to the base, in cramped style.",
            ),
            (
                "MathValueRecord",
                "SuperscriptBottomMin",
                None,
                None,
                "Minimum allowed height of the (ink) bottom of superscripts that does not require moving subscripts further up. Suggested: 1/4 x-height.",
            ),
            (
                "MathValueRecord",
                "SuperscriptBaselineDropMax",
                None,
                None,
                "Maximum allowed drop of the baseline of superscripts relative to the (ink) top of the base. Checked for bases that are treated as a box or extended shape. Positive for superscript baseline below the base top.",
            ),
            (
                "MathValueRecord",
                "SubSuperscriptGapMin",
                None,
                None,
                "Minimum gap between the superscript and subscript ink. Suggested: 4x default rule thickness.",
            ),
            (
                "MathValueRecord",
                "SuperscriptBottomMaxWithSubscript",
                None,
                None,
                "The maximum level to which the (ink) bottom of superscript can be pushed to increase the gap between superscript and subscript, before subscript starts being moved down. Suggested: 4/5 x-height.",
            ),
            (
                "MathValueRecord",
                "SpaceAfterScript",
                None,
                None,
                "Extra white space to be added after each subscript and superscript. Suggested: 0.5pt for a 12 pt font.",
            ),
            (
                "MathValueRecord",
                "UpperLimitGapMin",
                None,
                None,
                "Minimum gap between the (ink) bottom of the upper limit, and the (ink) top of the base operator.",
            ),
            (
                "MathValueRecord",
                "UpperLimitBaselineRiseMin",
                None,
                None,
                "Minimum distance between baseline of upper limit and (ink) top of the base operator.",
            ),
            (
                "MathValueRecord",
                "LowerLimitGapMin",
                None,
                None,
                "Minimum gap between (ink) top of the lower limit, and (ink) bottom of the base operator.",
            ),
            (
                "MathValueRecord",
                "LowerLimitBaselineDropMin",
                None,
                None,
                "Minimum distance between baseline of the lower limit and (ink) bottom of the base operator.",
            ),
            (
                "MathValueRecord",
                "StackTopShiftUp",
                None,
                None,
                "Standard shift up applied to the top element of a stack.",
            ),
            (
                "MathValueRecord",
                "StackTopDisplayStyleShiftUp",
                None,
                None,
                "Standard shift up applied to the top element of a stack in display style.",
            ),
            (
                "MathValueRecord",
                "StackBottomShiftDown",
                None,
                None,
                "Standard shift down applied to the bottom element of a stack. Positive for moving in the downward direction.",
            ),
            (
                "MathValueRecord",
                "StackBottomDisplayStyleShiftDown",
                None,
                None,
                "Standard shift down applied to the bottom element of a stack in display style. Positive for moving in the downward direction.",
            ),
            (
                "MathValueRecord",
                "StackGapMin",
                None,
                None,
                "Minimum gap between (ink) bottom of the top element of a stack, and the (ink) top of the bottom element. Suggested: 3x default rule thickness.",
            ),
            (
                "MathValueRecord",
                "StackDisplayStyleGapMin",
                None,
                None,
                "Minimum gap between (ink) bottom of the top element of a stack, and the (ink) top of the bottom element in display style. Suggested: 7x default rule thickness.",
            ),
            (
                "MathValueRecord",
                "StretchStackTopShiftUp",
                None,
                None,
                "Standard shift up applied to the top element of the stretch stack.",
            ),
            (
                "MathValueRecord",
                "StretchStackBottomShiftDown",
                None,
                None,
                "Standard shift down applied to the bottom element of the stretch stack. Positive for moving in the downward direction.",
            ),
            (
                "MathValueRecord",
                "StretchStackGapAboveMin",
                None,
                None,
                "Minimum gap between the ink of the stretched element, and the (ink) bottom of the element above. Suggested: UpperLimitGapMin",
            ),
            (
                "MathValueRecord",
                "StretchStackGapBelowMin",
                None,
                None,
                "Minimum gap between the ink of the stretched element, and the (ink) top of the element below. Suggested: LowerLimitGapMin.",
            ),
            (
                "MathValueRecord",
                "FractionNumeratorShiftUp",
                None,
                None,
                "Standard shift up applied to the numerator.",
            ),
            (
                "MathValueRecord",
                "FractionNumeratorDisplayStyleShiftUp",
                None,
                None,
                "Standard shift up applied to the numerator in display style. Suggested: StackTopDisplayStyleShiftUp.",
            ),
            (
                "MathValueRecord",
                "FractionDenominatorShiftDown",
                None,
                None,
                "Standard shift down applied to the denominator. Positive for moving in the downward direction.",
            ),
            (
                "MathValueRecord",
                "FractionDenominatorDisplayStyleShiftDown",
                None,
                None,
                "Standard shift down applied to the denominator in display style. Positive for moving in the downward direction. Suggested: StackBottomDisplayStyleShiftDown.",
            ),
            (
                "MathValueRecord",
                "FractionNumeratorGapMin",
                None,
                None,
                "Minimum tolerated gap between the (ink) bottom of the numerator and the ink of the fraction bar. Suggested: default rule thickness",
            ),
            (
                "MathValueRecord",
                "FractionNumDisplayStyleGapMin",
                None,
                None,
                "Minimum tolerated gap between the (ink) bottom of the numerator and the ink of the fraction bar in display style. Suggested: 3x default rule thickness.",
            ),
            (
                "MathValueRecord",
                "FractionRuleThickness",
                None,
                None,
                "Thickness of the fraction bar. Suggested: default rule thickness.",
            ),
            (
                "MathValueRecord",
                "FractionDenominatorGapMin",
                None,
                None,
                "Minimum tolerated gap between the (ink) top of the denominator and the ink of the fraction bar. Suggested: default rule thickness",
            ),
            (
                "MathValueRecord",
                "FractionDenomDisplayStyleGapMin",
                None,
                None,
                "Minimum tolerated gap between the (ink) top of the denominator and the ink of the fraction bar in display style. Suggested: 3x default rule thickness.",
            ),
            (
                "MathValueRecord",
                "SkewedFractionHorizontalGap",
                None,
                None,
                "Horizontal distance between the top and bottom elements of a skewed fraction.",
            ),
            (
                "MathValueRecord",
                "SkewedFractionVerticalGap",
                None,
                None,
                "Vertical distance between the ink of the top and bottom elements of a skewed fraction.",
            ),
            (
                "MathValueRecord",
                "OverbarVerticalGap",
                None,
                None,
                "Distance between the overbar and the (ink) top of he base. Suggested: 3x default rule thickness.",
            ),
            (
                "MathValueRecord",
                "OverbarRuleThickness",
                None,
                None,
                "Thickness of overbar. Suggested: default rule thickness.",
            ),
            (
                "MathValueRecord",
                "OverbarExtraAscender",
                None,
                None,
                "Extra white space reserved above the overbar. Suggested: default rule thickness.",
            ),
            (
                "MathValueRecord",
                "UnderbarVerticalGap",
                None,
                None,
                "Distance between underbar and (ink) bottom of the base. Suggested: 3x default rule thickness.",
            ),
            (
                "MathValueRecord",
                "UnderbarRuleThickness",
                None,
                None,
                "Thickness of underbar. Suggested: default rule thickness.",
            ),
            (
                "MathValueRecord",
                "UnderbarExtraDescender",
                None,
                None,
                "Extra white space reserved below the underbar. Always positive. Suggested: default rule thickness.",
            ),
            (
                "MathValueRecord",
                "RadicalVerticalGap",
                None,
                None,
                "Space between the (ink) top of the expression and the bar over it. Suggested: 1 1/4 default rule thickness.",
            ),
            (
                "MathValueRecord",
                "RadicalDisplayStyleVerticalGap",
                None,
                None,
                "Space between the (ink) top of the expression and the bar over it. Suggested: default rule thickness + 1/4 x-height.",
            ),
            (
                "MathValueRecord",
                "RadicalRuleThickness",
                None,
                None,
                "Thickness of the radical rule. This is the thickness of the rule in designed or constructed radical signs. Suggested: default rule thickness.",
            ),
            (
                "MathValueRecord",
                "RadicalExtraAscender",
                None,
                None,
                "Extra white space reserved above the radical. Suggested: RadicalRuleThickness.",
            ),
            (
                "MathValueRecord",
                "RadicalKernBeforeDegree",
                None,
                None,
                "Extra horizontal kern before the degree of a radical, if such is present. Suggested: 5/18 of em.",
            ),
            (
                "MathValueRecord",
                "RadicalKernAfterDegree",
                None,
                None,
                "Negative kern after the degree of a radical, if such is present. Suggested: 10/18 of em.",
            ),
            (
                "uint16",
                "RadicalDegreeBottomRaisePercent",
                None,
                None,
                "Height of the bottom of the radical degree, if such is present, in proportion to the ascender of the radical sign. Suggested: 60%.",
            ),
        ],
    ),
    (
        "MathGlyphInfo",
        [
            (
                "Offset",
                "MathItalicsCorrectionInfo",
                None,
                None,
                "Offset to MathItalicsCorrectionInfo table - from the beginning of MathGlyphInfo table.",
            ),
            (
                "Offset",
                "MathTopAccentAttachment",
                None,
                None,
                "Offset to MathTopAccentAttachment table - from the beginning of MathGlyphInfo table.",
            ),
            (
                "Offset",
                "ExtendedShapeCoverage",
                None,
                None,
                "Offset to coverage table for Extended Shape glyphs - from the  beginning of MathGlyphInfo table. When the left or right glyph of a box is an extended shape variant, the (ink) box (and not the default position defined by values in MathConstants table) should be used for vertical positioning purposes. May be NULL.",
            ),
            (
                "Offset",
                "MathKernInfo",
                None,
                None,
                "Offset to MathKernInfo table - from the beginning of MathGlyphInfo table.",
            ),
        ],
    ),
    (
        "MathItalicsCorrectionInfo",
        [
            (
                "Offset",
                "Coverage",
                None,
                None,
                "Offset to Coverage table - from the beginning of MathItalicsCorrectionInfo table.",
            ),
            (
                "uint16",
                "ItalicsCorrectionCount",
                None,
                None,
                "Number of italics correction values. Should coincide with the number of covered glyphs.",
            ),
            (
                "MathValueRecord",
                "ItalicsCorrection",
                "ItalicsCorrectionCount",
                0,
                "Array of MathValueRecords defining italics correction values for each covered glyph.",
            ),
        ],
    ),
    (
        "MathTopAccentAttachment",
        [
            (
                "Offset",
                "TopAccentCoverage",
                None,
                None,
                "Offset to Coverage table - from the beginning of  MathTopAccentAttachment table.",
            ),
            (
                "uint16",
                "TopAccentAttachmentCount",
                None,
                None,
                "Number of top accent attachment point values. Should coincide with the number of covered glyphs",
            ),
            (
                "MathValueRecord",
                "TopAccentAttachment",
                "TopAccentAttachmentCount",
                0,
                "Array of MathValueRecords defining top accent attachment points for each covered glyph",
            ),
        ],
    ),
    (
        "MathKernInfo",
        [
            (
                "Offset",
                "MathKernCoverage",
                None,
                None,
                "Offset to Coverage table - from the beginning of the MathKernInfo table.",
            ),
            ("uint16", "MathKernCount", None, None, "Number of MathKernInfoRecords."),
            (
                "MathKernInfoRecord",
                "MathKernInfoRecords",
                "MathKernCount",
                0,
                "Array of MathKernInfoRecords, per-glyph information for mathematical positioning of subscripts and superscripts.",
            ),
        ],
    ),
    (
        "MathKernInfoRecord",
        [
            (
                "Offset",
                "TopRightMathKern",
                None,
                None,
                "Offset to MathKern table for top right corner - from the beginning of MathKernInfo table. May be NULL.",
            ),
            (
                "Offset",
                "TopLeftMathKern",
                None,
                None,
                "Offset to MathKern table for the top left corner - from the beginning of MathKernInfo table. May be NULL.",
            ),
            (
                "Offset",
                "BottomRightMathKern",
                None,
                None,
                "Offset to MathKern table for bottom right corner - from the beginning of MathKernInfo table. May be NULL.",
            ),
            (
                "Offset",
                "BottomLeftMathKern",
                None,
                None,
                "Offset to MathKern table for bottom left corner - from the beginning of MathKernInfo table. May be NULL.",
            ),
        ],
    ),
    (
        "MathKern",
        [
            (
                "uint16",
                "HeightCount",
                None,
                None,
                "Number of heights on which the kern value changes.",
            ),
            (
                "MathValueRecord",
                "CorrectionHeight",
                "HeightCount",
                0,
                "Array of correction heights at which the kern value changes. Sorted by the height value in design units.",
            ),
            (
                "MathValueRecord",
                "KernValue",
                "HeightCount",
                1,
                "Array of kern values corresponding to heights. First value is the kern value for all heights less or equal than the first height in this table.Last value is the value to be applied for all heights greater than the last height in this table. Negative values are interpreted as move glyphs closer to each other.",
            ),
        ],
    ),
    (
        "MathVariants",
        [
            (
                "uint16",
                "MinConnectorOverlap",
                None,
                None,
                "Minimum overlap of connecting glyphs during glyph construction,  in design units.",
            ),
            (
                "Offset",
                "VertGlyphCoverage",
                None,
                None,
                "Offset to Coverage table - from the beginning of MathVariants table.",
            ),
            (
                "Offset",
                "HorizGlyphCoverage",
                None,
                None,
                "Offset to Coverage table - from the beginning of MathVariants table.",
            ),
            (
                "uint16",
                "VertGlyphCount",
                None,
                None,
                "Number of glyphs for which information is provided for vertically growing variants.",
            ),
            (
                "uint16",
                "HorizGlyphCount",
                None,
                None,
                "Number of glyphs for which information is provided for horizontally growing variants.",
            ),
            (
                "Offset",
                "VertGlyphConstruction",
                "VertGlyphCount",
                0,
                "Array of offsets to MathGlyphConstruction tables - from the beginning of the MathVariants table, for shapes growing in vertical direction.",
            ),
            (
                "Offset",
                "HorizGlyphConstruction",
                "HorizGlyphCount",
                0,
                "Array of offsets to MathGlyphConstruction tables - from the beginning of the MathVariants table, for shapes growing in horizontal direction.",
            ),
        ],
    ),
    (
        "MathGlyphConstruction",
        [
            (
                "Offset",
                "GlyphAssembly",
                None,
                None,
                "Offset to GlyphAssembly table for this shape - from the beginning of MathGlyphConstruction table. May be NULL",
            ),
            (
                "uint16",
                "VariantCount",
                None,
                None,
                "Count of glyph growing variants for this glyph.",
            ),
            (
                "MathGlyphVariantRecord",
                "MathGlyphVariantRecord",
                "VariantCount",
                0,
                "MathGlyphVariantRecords for alternative variants of the glyphs.",
            ),
        ],
    ),
    (
        "MathGlyphVariantRecord",
        [
            ("GlyphID", "VariantGlyph", None, None, "Glyph ID for the variant."),
            (
                "uint16",
                "AdvanceMeasurement",
                None,
                None,
                "Advance width/height, in design units, of the variant, in the direction of requested glyph extension.",
            ),
        ],
    ),
    (
        "GlyphAssembly",
        [
            (
                "MathValueRecord",
                "ItalicsCorrection",
                None,
                None,
                "Italics correction of this GlyphAssembly. Should not depend on the assembly size.",
            ),
            ("uint16", "PartCount", None, None, "Number of parts in this assembly."),
            (
                "GlyphPartRecord",
                "PartRecords",
                "PartCount",
                0,
                "Array of part records, from left to right and bottom to top.",
            ),
        ],
    ),
    (
        "GlyphPartRecord",
        [
            ("GlyphID", "glyph", None, None, "Glyph ID for the part."),
            (
                "uint16",
                "StartConnectorLength",
                None,
                None,
                "Advance width/ height of the straight bar connector material, in design units, is at the beginning of the glyph, in the direction of the extension.",
            ),
            (
                "uint16",
                "EndConnectorLength",
                None,
                None,
                "Advance width/ height of the straight bar connector material, in design units, is at the end of the glyph, in the direction of the extension.",
            ),
            (
                "uint16",
                "FullAdvance",
                None,
                None,
                "Full advance width/height for this part, in the direction of the extension. In design units.",
            ),
            (
                "uint16",
                "PartFlags",
                None,
                None,
                "Part qualifiers. PartFlags enumeration currently uses only one bit: 0x0001 fExtender: If set, the part can be skipped or repeated. 0xFFFE Reserved",
            ),
        ],
    ),
    ##
    ## Apple Advanced Typography (AAT) tables
    ##
    (
        "AATLookupSegment",
        [
            ("uint16", "lastGlyph", None, None, "Last glyph index in this segment."),
            ("uint16", "firstGlyph", None, None, "First glyph index in this segment."),
            (
                "uint16",
                "value",
                None,
                None,
                "A 16-bit offset from the start of the table to the data.",
            ),
        ],
    ),
    #
    # ankr
    #
    (
        "ankr",
        [
            ("struct", "AnchorPoints", None, None, "Anchor points table."),
        ],
    ),
    (
        "AnchorPointsFormat0",
        [
            ("uint16", "Format", None, None, "Format of the anchor points table, = 0."),
            ("uint16", "Flags", None, None, "Flags. Currenty unused, set to zero."),
            (
                "AATLookupWithDataOffset(AnchorGlyphData)",
                "Anchors",
                None,
                None,
                "Table of with anchor overrides for each glyph.",
            ),
        ],
    ),
    (
        "AnchorGlyphData",
        [
            (
                "uint32",
                "AnchorPointCount",
                None,
                None,
                "Number of anchor points for this glyph.",
            ),
            (
                "struct",
                "AnchorPoint",
                "AnchorPointCount",
                0,
                "Individual anchor points.",
            ),
        ],
    ),
    (
        "AnchorPoint",
        [
            ("int16", "XCoordinate", None, None, "X coordinate of this anchor point."),
            ("int16", "YCoordinate", None, None, "Y coordinate of this anchor point."),
        ],
    ),
    #
    # bsln
    #
    (
        "bsln",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version number of the AAT baseline table (0x00010000 for the initial version).",
            ),
            ("struct", "Baseline", None, None, "Baseline table."),
        ],
    ),
    (
        "BaselineFormat0",
        [
            ("uint16", "Format", None, None, "Format of the baseline table, = 0."),
            (
                "uint16",
                "DefaultBaseline",
                None,
                None,
                "Default baseline value for all glyphs. This value can be from 0 through 31.",
            ),
            (
                "uint16",
                "Delta",
                32,
                0,
                "These are the FUnit distance deltas from the font’s natural baseline to the other baselines used in the font. A total of 32 deltas must be assigned.",
            ),
        ],
    ),
    (
        "BaselineFormat1",
        [
            ("uint16", "Format", None, None, "Format of the baseline table, = 1."),
            (
                "uint16",
                "DefaultBaseline",
                None,
                None,
                "Default baseline value for all glyphs. This value can be from 0 through 31.",
            ),
            (
                "uint16",
                "Delta",
                32,
                0,
                "These are the FUnit distance deltas from the font’s natural baseline to the other baselines used in the font. A total of 32 deltas must be assigned.",
            ),
            (
                "AATLookup(uint16)",
                "BaselineValues",
                None,
                None,
                "Lookup table that maps glyphs to their baseline values.",
            ),
        ],
    ),
    (
        "BaselineFormat2",
        [
            ("uint16", "Format", None, None, "Format of the baseline table, = 1."),
            (
                "uint16",
                "DefaultBaseline",
                None,
                None,
                "Default baseline value for all glyphs. This value can be from 0 through 31.",
            ),
            (
                "GlyphID",
                "StandardGlyph",
                None,
                None,
                "Glyph index of the glyph in this font to be used to set the baseline values. This glyph must contain a set of control points (whose numbers are contained in the following field) that determines baseline distances.",
            ),
            (
                "uint16",
                "ControlPoint",
                32,
                0,
                "Array of 32 control point numbers, associated with the standard glyph. A value of 0xFFFF means there is no corresponding control point in the standard glyph.",
            ),
        ],
    ),
    (
        "BaselineFormat3",
        [
            ("uint16", "Format", None, None, "Format of the baseline table, = 1."),
            (
                "uint16",
                "DefaultBaseline",
                None,
                None,
                "Default baseline value for all glyphs. This value can be from 0 through 31.",
            ),
            (
                "GlyphID",
                "StandardGlyph",
                None,
                None,
                "Glyph index of the glyph in this font to be used to set the baseline values. This glyph must contain a set of control points (whose numbers are contained in the following field) that determines baseline distances.",
            ),
            (
                "uint16",
                "ControlPoint",
                32,
                0,
                "Array of 32 control point numbers, associated with the standard glyph. A value of 0xFFFF means there is no corresponding control point in the standard glyph.",
            ),
            (
                "AATLookup(uint16)",
                "BaselineValues",
                None,
                None,
                "Lookup table that maps glyphs to their baseline values.",
            ),
        ],
    ),
    #
    # cidg
    #
    (
        "cidg",
        [
            ("struct", "CIDGlyphMapping", None, None, "CID-to-glyph mapping table."),
        ],
    ),
    (
        "CIDGlyphMappingFormat0",
        [
            (
                "uint16",
                "Format",
                None,
                None,
                "Format of the CID-to-glyph mapping table, = 0.",
            ),
            ("uint16", "DataFormat", None, None, "Currenty unused, set to zero."),
            ("uint32", "StructLength", None, None, "Size of the table in bytes."),
            ("uint16", "Registry", None, None, "The registry ID."),
            (
                "char64",
                "RegistryName",
                None,
                None,
                "The registry name in ASCII; unused bytes should be set to 0.",
            ),
            ("uint16", "Order", None, None, "The order ID."),
            (
                "char64",
                "OrderName",
                None,
                None,
                "The order name in ASCII; unused bytes should be set to 0.",
            ),
            ("uint16", "SupplementVersion", None, None, "The supplement version."),
            (
                "CIDGlyphMap",
                "Mapping",
                None,
                None,
                "A mapping from CIDs to the glyphs in the font, starting with CID 0. If a CID from the identified collection has no glyph in the font, 0xFFFF is used",
            ),
        ],
    ),
    #
    # feat
    #
    (
        "feat",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the feat table-initially set to 0x00010000.",
            ),
            ("FeatureNames", "FeatureNames", None, None, "The feature names."),
        ],
    ),
    (
        "FeatureNames",
        [
            (
                "uint16",
                "FeatureNameCount",
                None,
                None,
                "Number of entries in the feature name array.",
            ),
            ("uint16", "Reserved1", None, None, "Reserved (set to zero)."),
            ("uint32", "Reserved2", None, None, "Reserved (set to zero)."),
            (
                "FeatureName",
                "FeatureName",
                "FeatureNameCount",
                0,
                "The feature name array.",
            ),
        ],
    ),
    (
        "FeatureName",
        [
            ("uint16", "FeatureType", None, None, "Feature type."),
            (
                "uint16",
                "SettingsCount",
                None,
                None,
                "The number of records in the setting name array.",
            ),
            (
                "LOffset",
                "Settings",
                None,
                None,
                "Offset to setting table for this feature.",
            ),
            (
                "uint16",
                "FeatureFlags",
                None,
                None,
                "Single-bit flags associated with the feature type.",
            ),
            (
                "NameID",
                "FeatureNameID",
                None,
                None,
                "The name table index for the feature name.",
            ),
        ],
    ),
    (
        "Settings",
        [
            ("Setting", "Setting", "SettingsCount", 0, "The setting array."),
        ],
    ),
    (
        "Setting",
        [
            ("uint16", "SettingValue", None, None, "The setting."),
            (
                "NameID",
                "SettingNameID",
                None,
                None,
                "The name table index for the setting name.",
            ),
        ],
    ),
    #
    # gcid
    #
    (
        "gcid",
        [
            ("struct", "GlyphCIDMapping", None, None, "Glyph to CID mapping table."),
        ],
    ),
    (
        "GlyphCIDMappingFormat0",
        [
            (
                "uint16",
                "Format",
                None,
                None,
                "Format of the glyph-to-CID mapping table, = 0.",
            ),
            ("uint16", "DataFormat", None, None, "Currenty unused, set to zero."),
            ("uint32", "StructLength", None, None, "Size of the table in bytes."),
            ("uint16", "Registry", None, None, "The registry ID."),
            (
                "char64",
                "RegistryName",
                None,
                None,
                "The registry name in ASCII; unused bytes should be set to 0.",
            ),
            ("uint16", "Order", None, None, "The order ID."),
            (
                "char64",
                "OrderName",
                None,
                None,
                "The order name in ASCII; unused bytes should be set to 0.",
            ),
            ("uint16", "SupplementVersion", None, None, "The supplement version."),
            (
                "GlyphCIDMap",
                "Mapping",
                None,
                None,
                "The CIDs for the glyphs in the font, starting with glyph 0. If a glyph does not correspond to a CID in the identified collection, 0xFFFF is used",
            ),
        ],
    ),
    #
    # lcar
    #
    (
        "lcar",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version number of the ligature caret table (0x00010000 for the initial version).",
            ),
            ("struct", "LigatureCarets", None, None, "Ligature carets table."),
        ],
    ),
    (
        "LigatureCaretsFormat0",
        [
            (
                "uint16",
                "Format",
                None,
                None,
                "Format of the ligature caret table. Format 0 indicates division points are distances in font units, Format 1 indicates division points are indexes of control points.",
            ),
            (
                "AATLookup(LigCaretDistances)",
                "Carets",
                None,
                None,
                "Lookup table associating ligature glyphs with their caret positions, in font unit distances.",
            ),
        ],
    ),
    (
        "LigatureCaretsFormat1",
        [
            (
                "uint16",
                "Format",
                None,
                None,
                "Format of the ligature caret table. Format 0 indicates division points are distances in font units, Format 1 indicates division points are indexes of control points.",
            ),
            (
                "AATLookup(LigCaretPoints)",
                "Carets",
                None,
                None,
                "Lookup table associating ligature glyphs with their caret positions, as control points.",
            ),
        ],
    ),
    (
        "LigCaretDistances",
        [
            ("uint16", "DivsionPointCount", None, None, "Number of division points."),
            (
                "int16",
                "DivisionPoint",
                "DivsionPointCount",
                0,
                "Distance in font units through which a subdivision is made orthogonally to the baseline.",
            ),
        ],
    ),
    (
        "LigCaretPoints",
        [
            ("uint16", "DivsionPointCount", None, None, "Number of division points."),
            (
                "int16",
                "DivisionPoint",
                "DivsionPointCount",
                0,
                "The number of the control point through which a subdivision is made orthogonally to the baseline.",
            ),
        ],
    ),
    #
    # mort
    #
    (
        "mort",
        [
            ("Version", "Version", None, None, "Version of the mort table."),
            (
                "uint32",
                "MorphChainCount",
                None,
                None,
                "Number of metamorphosis chains.",
            ),
            (
                "MortChain",
                "MorphChain",
                "MorphChainCount",
                0,
                "Array of metamorphosis chains.",
            ),
        ],
    ),
    (
        "MortChain",
        [
            (
                "Flags32",
                "DefaultFlags",
                None,
                None,
                "The default specification for subtables.",
            ),
            (
                "uint32",
                "StructLength",
                None,
                None,
                "Total byte count, including this header; must be a multiple of 4.",
            ),
            (
                "uint16",
                "MorphFeatureCount",
                None,
                None,
                "Number of metamorphosis feature entries.",
            ),
            (
                "uint16",
                "MorphSubtableCount",
                None,
                None,
                "The number of subtables in the chain.",
            ),
            (
                "struct",
                "MorphFeature",
                "MorphFeatureCount",
                0,
                "Array of metamorphosis features.",
            ),
            (
                "MortSubtable",
                "MorphSubtable",
                "MorphSubtableCount",
                0,
                "Array of metamorphosis subtables.",
            ),
        ],
    ),
    (
        "MortSubtable",
        [
            (
                "uint16",
                "StructLength",
                None,
                None,
                "Total subtable length, including this header.",
            ),
            (
                "uint8",
                "CoverageFlags",
                None,
                None,
                "Most significant byte of coverage flags.",
            ),
            ("uint8", "MorphType", None, None, "Subtable type."),
            (
                "Flags32",
                "SubFeatureFlags",
                None,
                None,
                "The 32-bit mask identifying which subtable this is (the subtable being executed if the AND of this value and the processed defaultFlags is nonzero).",
            ),
            ("SubStruct", "SubStruct", None, None, "SubTable."),
        ],
    ),
    #
    # morx
    #
    (
        "morx",
        [
            ("uint16", "Version", None, None, "Version of the morx table."),
            ("uint16", "Reserved", None, None, "Reserved (set to zero)."),
            (
                "uint32",
                "MorphChainCount",
                None,
                None,
                "Number of extended metamorphosis chains.",
            ),
            (
                "MorxChain",
                "MorphChain",
                "MorphChainCount",
                0,
                "Array of extended metamorphosis chains.",
            ),
        ],
    ),
    (
        "MorxChain",
        [
            (
                "Flags32",
                "DefaultFlags",
                None,
                None,
                "The default specification for subtables.",
            ),
            (
                "uint32",
                "StructLength",
                None,
                None,
                "Total byte count, including this header; must be a multiple of 4.",
            ),
            (
                "uint32",
                "MorphFeatureCount",
                None,
                None,
                "Number of feature subtable entries.",
            ),
            (
                "uint32",
                "MorphSubtableCount",
                None,
                None,
                "The number of subtables in the chain.",
            ),
            (
                "MorphFeature",
                "MorphFeature",
                "MorphFeatureCount",
                0,
                "Array of metamorphosis features.",
            ),
            (
                "MorxSubtable",
                "MorphSubtable",
                "MorphSubtableCount",
                0,
                "Array of extended metamorphosis subtables.",
            ),
        ],
    ),
    (
        "MorphFeature",
        [
            ("uint16", "FeatureType", None, None, "The type of feature."),
            (
                "uint16",
                "FeatureSetting",
                None,
                None,
                "The feature's setting (aka selector).",
            ),
            (
                "Flags32",
                "EnableFlags",
                None,
                None,
                "Flags for the settings that this feature and setting enables.",
            ),
            (
                "Flags32",
                "DisableFlags",
                None,
                None,
                "Complement of flags for the settings that this feature and setting disable.",
            ),
        ],
    ),
    # Apple TrueType Reference Manual, chapter “The ‘morx’ table”,
    # section “Metamorphosis Subtables”.
    # https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6morx.html
    (
        "MorxSubtable",
        [
            (
                "uint32",
                "StructLength",
                None,
                None,
                "Total subtable length, including this header.",
            ),
            (
                "uint8",
                "CoverageFlags",
                None,
                None,
                "Most significant byte of coverage flags.",
            ),
            ("uint16", "Reserved", None, None, "Unused."),
            ("uint8", "MorphType", None, None, "Subtable type."),
            (
                "Flags32",
                "SubFeatureFlags",
                None,
                None,
                "The 32-bit mask identifying which subtable this is (the subtable being executed if the AND of this value and the processed defaultFlags is nonzero).",
            ),
            ("SubStruct", "SubStruct", None, None, "SubTable."),
        ],
    ),
    (
        "StateHeader",
        [
            (
                "uint32",
                "ClassCount",
                None,
                None,
                "Number of classes, which is the number of 16-bit entry indices in a single line in the state array.",
            ),
            (
                "uint32",
                "MorphClass",
                None,
                None,
                "Offset from the start of this state table header to the start of the class table.",
            ),
            (
                "uint32",
                "StateArrayOffset",
                None,
                None,
                "Offset from the start of this state table header to the start of the state array.",
            ),
            (
                "uint32",
                "EntryTableOffset",
                None,
                None,
                "Offset from the start of this state table header to the start of the entry table.",
            ),
        ],
    ),
    (
        "RearrangementMorph",
        [
            (
                "STXHeader(RearrangementMorphAction)",
                "StateTable",
                None,
                None,
                "Finite-state transducer table for indic rearrangement.",
            ),
        ],
    ),
    (
        "ContextualMorph",
        [
            (
                "STXHeader(ContextualMorphAction)",
                "StateTable",
                None,
                None,
                "Finite-state transducer for contextual glyph substitution.",
            ),
        ],
    ),
    (
        "LigatureMorph",
        [
            (
                "STXHeader(LigatureMorphAction)",
                "StateTable",
                None,
                None,
                "Finite-state transducer for ligature substitution.",
            ),
        ],
    ),
    (
        "NoncontextualMorph",
        [
            (
                "AATLookup(GlyphID)",
                "Substitution",
                None,
                None,
                "The noncontextual glyph substitution table.",
            ),
        ],
    ),
    (
        "InsertionMorph",
        [
            (
                "STXHeader(InsertionMorphAction)",
                "StateTable",
                None,
                None,
                "Finite-state transducer for glyph insertion.",
            ),
        ],
    ),
    (
        "MorphClass",
        [
            (
                "uint16",
                "FirstGlyph",
                None,
                None,
                "Glyph index of the first glyph in the class table.",
            ),
            # ('uint16', 'GlyphCount', None, None, 'Number of glyphs in class table.'),
            # ('uint8', 'GlyphClass', 'GlyphCount', 0, 'The class codes (indexed by glyph index minus firstGlyph). Class codes range from 0 to the value of stateSize minus 1.'),
        ],
    ),
    # If the 'morx' table version is 3 or greater, then the last subtable in the chain is followed by a subtableGlyphCoverageArray, as described below.
    # 		('Offset', 'MarkGlyphSetsDef', None, 'round(Version*0x10000) >= 0x00010002', 'Offset to the table of mark set definitions-from beginning of GDEF header (may be NULL)'),
    #
    # prop
    #
    (
        "prop",
        [
            (
                "Fixed",
                "Version",
                None,
                None,
                "Version number of the AAT glyphs property table. Version 1.0 is the initial table version. Version 2.0, which is recognized by macOS 8.5 and later, adds support for the “attaches on right” bit. Version 3.0, which gets recognized by macOS X and iOS, adds support for the additional directional properties defined in Unicode 3.0.",
            ),
            ("struct", "GlyphProperties", None, None, "Glyph properties."),
        ],
    ),
    (
        "GlyphPropertiesFormat0",
        [
            ("uint16", "Format", None, None, "Format, = 0."),
            (
                "uint16",
                "DefaultProperties",
                None,
                None,
                "Default properties applied to a glyph. Since there is no lookup table in prop format 0, the default properties get applied to every glyph in the font.",
            ),
        ],
    ),
    (
        "GlyphPropertiesFormat1",
        [
            ("uint16", "Format", None, None, "Format, = 1."),
            (
                "uint16",
                "DefaultProperties",
                None,
                None,
                "Default properties applied to a glyph if that glyph is not present in the Properties lookup table.",
            ),
            (
                "AATLookup(uint16)",
                "Properties",
                None,
                None,
                "Lookup data associating glyphs with their properties.",
            ),
        ],
    ),
    #
    # opbd
    #
    (
        "opbd",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version number of the optical bounds table (0x00010000 for the initial version).",
            ),
            ("struct", "OpticalBounds", None, None, "Optical bounds table."),
        ],
    ),
    (
        "OpticalBoundsFormat0",
        [
            (
                "uint16",
                "Format",
                None,
                None,
                "Format of the optical bounds table, = 0.",
            ),
            (
                "AATLookup(OpticalBoundsDeltas)",
                "OpticalBoundsDeltas",
                None,
                None,
                "Lookup table associating glyphs with their optical bounds, given as deltas in font units.",
            ),
        ],
    ),
    (
        "OpticalBoundsFormat1",
        [
            (
                "uint16",
                "Format",
                None,
                None,
                "Format of the optical bounds table, = 1.",
            ),
            (
                "AATLookup(OpticalBoundsPoints)",
                "OpticalBoundsPoints",
                None,
                None,
                "Lookup table associating glyphs with their optical bounds, given as references to control points.",
            ),
        ],
    ),
    (
        "OpticalBoundsDeltas",
        [
            (
                "int16",
                "Left",
                None,
                None,
                "Delta value for the left-side optical edge.",
            ),
            ("int16", "Top", None, None, "Delta value for the top-side optical edge."),
            (
                "int16",
                "Right",
                None,
                None,
                "Delta value for the right-side optical edge.",
            ),
            (
                "int16",
                "Bottom",
                None,
                None,
                "Delta value for the bottom-side optical edge.",
            ),
        ],
    ),
    (
        "OpticalBoundsPoints",
        [
            (
                "int16",
                "Left",
                None,
                None,
                "Control point index for the left-side optical edge, or -1 if this glyph has none.",
            ),
            (
                "int16",
                "Top",
                None,
                None,
                "Control point index for the top-side optical edge, or -1 if this glyph has none.",
            ),
            (
                "int16",
                "Right",
                None,
                None,
                "Control point index for the right-side optical edge, or -1 if this glyph has none.",
            ),
            (
                "int16",
                "Bottom",
                None,
                None,
                "Control point index for the bottom-side optical edge, or -1 if this glyph has none.",
            ),
        ],
    ),
    #
    # TSIC
    #
    (
        "TSIC",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of table initially set to 0x00010000.",
            ),
            ("uint16", "Flags", None, None, "TSIC flags - set to 0"),
            ("uint16", "AxisCount", None, None, "Axis count from fvar"),
            ("uint16", "RecordCount", None, None, "TSIC record count"),
            ("uint16", "Reserved", None, None, "Set to 0"),
            ("Tag", "AxisArray", "AxisCount", 0, "Array of axis tags in fvar order"),
            (
                "LocationRecord",
                "RecordLocations",
                "RecordCount",
                0,
                "Location in variation space of TSIC record",
            ),
            ("TSICRecord", "Record", "RecordCount", 0, "Array of TSIC records"),
        ],
    ),
    (
        "LocationRecord",
        [
            ("F2Dot14", "Axis", "AxisCount", 0, "Axis record"),
        ],
    ),
    (
        "TSICRecord",
        [
            ("uint16", "Flags", None, None, "Record flags - set to 0"),
            ("uint16", "NumCVTEntries", None, None, "Number of CVT number value pairs"),
            ("uint16", "NameLength", None, None, "Length of optional user record name"),
            ("uint16", "NameArray", "NameLength", 0, "Unicode 16 name"),
            ("uint16", "CVTArray", "NumCVTEntries", 0, "CVT number array"),
            ("int16", "CVTValueArray", "NumCVTEntries", 0, "CVT value"),
        ],
    ),
    #
    # COLR
    #
    (
        "COLR",
        [
            ("uint16", "Version", None, None, "Table version number (starts at 0)."),
            (
                "uint16",
                "BaseGlyphRecordCount",
                None,
                None,
                "Number of Base Glyph Records.",
            ),
            (
                "LOffset",
                "BaseGlyphRecordArray",
                None,
                None,
                "Offset (from beginning of COLR table) to Base Glyph records.",
            ),
            (
                "LOffset",
                "LayerRecordArray",
                None,
                None,
                "Offset (from beginning of COLR table) to Layer Records.",
            ),
            ("uint16", "LayerRecordCount", None, None, "Number of Layer Records."),
            (
                "LOffset",
                "BaseGlyphList",
                None,
                "Version >= 1",
                "Offset (from beginning of COLR table) to array of Version-1 Base Glyph records.",
            ),
            (
                "LOffset",
                "LayerList",
                None,
                "Version >= 1",
                "Offset (from beginning of COLR table) to LayerList.",
            ),
            (
                "LOffset",
                "ClipList",
                None,
                "Version >= 1",
                "Offset to ClipList table (may be NULL)",
            ),
            (
                "LOffsetTo(DeltaSetIndexMap)",
                "VarIndexMap",
                None,
                "Version >= 1",
                "Offset to DeltaSetIndexMap table (may be NULL)",
            ),
            (
                "LOffset",
                "VarStore",
                None,
                "Version >= 1",
                "Offset to variation store (may be NULL)",
            ),
        ],
    ),
    (
        "BaseGlyphRecordArray",
        [
            (
                "BaseGlyphRecord",
                "BaseGlyphRecord",
                "BaseGlyphRecordCount",
                0,
                "Base Glyph records.",
            ),
        ],
    ),
    (
        "BaseGlyphRecord",
        [
            (
                "GlyphID",
                "BaseGlyph",
                None,
                None,
                "Glyph ID of reference glyph. This glyph is for reference only and is not rendered for color.",
            ),
            (
                "uint16",
                "FirstLayerIndex",
                None,
                None,
                "Index (from beginning of the Layer Records) to the layer record. There will be numLayers consecutive entries for this base glyph.",
            ),
            (
                "uint16",
                "NumLayers",
                None,
                None,
                "Number of color layers associated with this glyph.",
            ),
        ],
    ),
    (
        "LayerRecordArray",
        [
            ("LayerRecord", "LayerRecord", "LayerRecordCount", 0, "Layer records."),
        ],
    ),
    (
        "LayerRecord",
        [
            (
                "GlyphID",
                "LayerGlyph",
                None,
                None,
                "Glyph ID of layer glyph (must be in z-order from bottom to top).",
            ),
            (
                "uint16",
                "PaletteIndex",
                None,
                None,
                "Index value to use with a selected color palette.",
            ),
        ],
    ),
    (
        "BaseGlyphList",
        [
            (
                "uint32",
                "BaseGlyphCount",
                None,
                None,
                "Number of Version-1 Base Glyph records",
            ),
            (
                "struct",
                "BaseGlyphPaintRecord",
                "BaseGlyphCount",
                0,
                "Array of Version-1 Base Glyph records",
            ),
        ],
    ),
    (
        "BaseGlyphPaintRecord",
        [
            ("GlyphID", "BaseGlyph", None, None, "Glyph ID of reference glyph."),
            (
                "LOffset",
                "Paint",
                None,
                None,
                "Offset (from beginning of BaseGlyphPaintRecord) to Paint, typically a PaintColrLayers.",
            ),
        ],
    ),
    (
        "LayerList",
        [
            ("uint32", "LayerCount", None, None, "Number of Version-1 Layers"),
            (
                "LOffset",
                "Paint",
                "LayerCount",
                0,
                "Array of offsets to Paint tables, from the start of the LayerList table.",
            ),
        ],
    ),
    (
        "ClipListFormat1",
        [
            (
                "uint8",
                "Format",
                None,
                None,
                "Format for ClipList with 16bit glyph IDs: 1",
            ),
            ("uint32", "ClipCount", None, None, "Number of Clip records."),
            (
                "struct",
                "ClipRecord",
                "ClipCount",
                0,
                "Array of Clip records sorted by glyph ID.",
            ),
        ],
    ),
    (
        "ClipRecord",
        [
            ("uint16", "StartGlyphID", None, None, "First glyph ID in the range."),
            ("uint16", "EndGlyphID", None, None, "Last glyph ID in the range."),
            ("Offset24", "ClipBox", None, None, "Offset to a ClipBox table."),
        ],
    ),
    (
        "ClipBoxFormat1",
        [
            (
                "uint8",
                "Format",
                None,
                None,
                "Format for ClipBox without variation: set to 1.",
            ),
            ("int16", "xMin", None, None, "Minimum x of clip box."),
            ("int16", "yMin", None, None, "Minimum y of clip box."),
            ("int16", "xMax", None, None, "Maximum x of clip box."),
            ("int16", "yMax", None, None, "Maximum y of clip box."),
        ],
    ),
    (
        "ClipBoxFormat2",
        [
            ("uint8", "Format", None, None, "Format for variable ClipBox: set to 2."),
            ("int16", "xMin", None, None, "Minimum x of clip box. VarIndexBase + 0."),
            ("int16", "yMin", None, None, "Minimum y of clip box. VarIndexBase + 1."),
            ("int16", "xMax", None, None, "Maximum x of clip box. VarIndexBase + 2."),
            ("int16", "yMax", None, None, "Maximum y of clip box. VarIndexBase + 3."),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # COLRv1 Affine2x3 uses the same column-major order to serialize a 2D
    # Affine Transformation as the one used by fontTools.misc.transform.
    # However, for historical reasons, the labels 'xy' and 'yx' are swapped.
    # Their fundamental meaning is the same though.
    # COLRv1 Affine2x3 follows the names found in FreeType and Cairo.
    # In all case, the second element in the 6-tuple correspond to the
    # y-part of the x basis vector, and the third to the x-part of the y
    # basis vector.
    # See https://github.com/googlefonts/colr-gradients-spec/pull/85
    (
        "Affine2x3",
        [
            ("Fixed", "xx", None, None, "x-part of x basis vector"),
            ("Fixed", "yx", None, None, "y-part of x basis vector"),
            ("Fixed", "xy", None, None, "x-part of y basis vector"),
            ("Fixed", "yy", None, None, "y-part of y basis vector"),
            ("Fixed", "dx", None, None, "Translation in x direction"),
            ("Fixed", "dy", None, None, "Translation in y direction"),
        ],
    ),
    (
        "VarAffine2x3",
        [
            ("Fixed", "xx", None, None, "x-part of x basis vector. VarIndexBase + 0."),
            ("Fixed", "yx", None, None, "y-part of x basis vector. VarIndexBase + 1."),
            ("Fixed", "xy", None, None, "x-part of y basis vector. VarIndexBase + 2."),
            ("Fixed", "yy", None, None, "y-part of y basis vector. VarIndexBase + 3."),
            (
                "Fixed",
                "dx",
                None,
                None,
                "Translation in x direction. VarIndexBase + 4.",
            ),
            (
                "Fixed",
                "dy",
                None,
                None,
                "Translation in y direction. VarIndexBase + 5.",
            ),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    (
        "ColorStop",
        [
            ("F2Dot14", "StopOffset", None, None, ""),
            ("uint16", "PaletteIndex", None, None, "Index for a CPAL palette entry."),
            ("F2Dot14", "Alpha", None, None, "Values outsided [0.,1.] reserved"),
        ],
    ),
    (
        "VarColorStop",
        [
            ("F2Dot14", "StopOffset", None, None, "VarIndexBase + 0."),
            ("uint16", "PaletteIndex", None, None, "Index for a CPAL palette entry."),
            (
                "F2Dot14",
                "Alpha",
                None,
                None,
                "Values outsided [0.,1.] reserved. VarIndexBase + 1.",
            ),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    (
        "ColorLine",
        [
            (
                "ExtendMode",
                "Extend",
                None,
                None,
                "Enum {PAD = 0, REPEAT = 1, REFLECT = 2}",
            ),
            ("uint16", "StopCount", None, None, "Number of Color stops."),
            ("ColorStop", "ColorStop", "StopCount", 0, "Array of Color stops."),
        ],
    ),
    (
        "VarColorLine",
        [
            (
                "ExtendMode",
                "Extend",
                None,
                None,
                "Enum {PAD = 0, REPEAT = 1, REFLECT = 2}",
            ),
            ("uint16", "StopCount", None, None, "Number of Color stops."),
            ("VarColorStop", "ColorStop", "StopCount", 0, "Array of Color stops."),
        ],
    ),
    # PaintColrLayers
    (
        "PaintFormat1",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 1"),
            (
                "uint8",
                "NumLayers",
                None,
                None,
                "Number of offsets to Paint to read from LayerList.",
            ),
            ("uint32", "FirstLayerIndex", None, None, "Index into LayerList."),
        ],
    ),
    # PaintSolid
    (
        "PaintFormat2",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 2"),
            ("uint16", "PaletteIndex", None, None, "Index for a CPAL palette entry."),
            ("F2Dot14", "Alpha", None, None, "Values outsided [0.,1.] reserved"),
        ],
    ),
    # PaintVarSolid
    (
        "PaintFormat3",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 3"),
            ("uint16", "PaletteIndex", None, None, "Index for a CPAL palette entry."),
            (
                "F2Dot14",
                "Alpha",
                None,
                None,
                "Values outsided [0.,1.] reserved. VarIndexBase + 0.",
            ),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintLinearGradient
    (
        "PaintFormat4",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 4"),
            (
                "Offset24",
                "ColorLine",
                None,
                None,
                "Offset (from beginning of PaintLinearGradient table) to ColorLine subtable.",
            ),
            ("int16", "x0", None, None, ""),
            ("int16", "y0", None, None, ""),
            ("int16", "x1", None, None, ""),
            ("int16", "y1", None, None, ""),
            ("int16", "x2", None, None, ""),
            ("int16", "y2", None, None, ""),
        ],
    ),
    # PaintVarLinearGradient
    (
        "PaintFormat5",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 5"),
            (
                "LOffset24To(VarColorLine)",
                "ColorLine",
                None,
                None,
                "Offset (from beginning of PaintVarLinearGradient table) to VarColorLine subtable.",
            ),
            ("int16", "x0", None, None, "VarIndexBase + 0."),
            ("int16", "y0", None, None, "VarIndexBase + 1."),
            ("int16", "x1", None, None, "VarIndexBase + 2."),
            ("int16", "y1", None, None, "VarIndexBase + 3."),
            ("int16", "x2", None, None, "VarIndexBase + 4."),
            ("int16", "y2", None, None, "VarIndexBase + 5."),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintRadialGradient
    (
        "PaintFormat6",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 6"),
            (
                "Offset24",
                "ColorLine",
                None,
                None,
                "Offset (from beginning of PaintRadialGradient table) to ColorLine subtable.",
            ),
            ("int16", "x0", None, None, ""),
            ("int16", "y0", None, None, ""),
            ("uint16", "r0", None, None, ""),
            ("int16", "x1", None, None, ""),
            ("int16", "y1", None, None, ""),
            ("uint16", "r1", None, None, ""),
        ],
    ),
    # PaintVarRadialGradient
    (
        "PaintFormat7",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 7"),
            (
                "LOffset24To(VarColorLine)",
                "ColorLine",
                None,
                None,
                "Offset (from beginning of PaintVarRadialGradient table) to VarColorLine subtable.",
            ),
            ("int16", "x0", None, None, "VarIndexBase + 0."),
            ("int16", "y0", None, None, "VarIndexBase + 1."),
            ("uint16", "r0", None, None, "VarIndexBase + 2."),
            ("int16", "x1", None, None, "VarIndexBase + 3."),
            ("int16", "y1", None, None, "VarIndexBase + 4."),
            ("uint16", "r1", None, None, "VarIndexBase + 5."),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintSweepGradient
    (
        "PaintFormat8",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 8"),
            (
                "Offset24",
                "ColorLine",
                None,
                None,
                "Offset (from beginning of PaintSweepGradient table) to ColorLine subtable.",
            ),
            ("int16", "centerX", None, None, "Center x coordinate."),
            ("int16", "centerY", None, None, "Center y coordinate."),
            (
                "BiasedAngle",
                "startAngle",
                None,
                None,
                "Start of the angular range of the gradient.",
            ),
            (
                "BiasedAngle",
                "endAngle",
                None,
                None,
                "End of the angular range of the gradient.",
            ),
        ],
    ),
    # PaintVarSweepGradient
    (
        "PaintFormat9",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 9"),
            (
                "LOffset24To(VarColorLine)",
                "ColorLine",
                None,
                None,
                "Offset (from beginning of PaintVarSweepGradient table) to VarColorLine subtable.",
            ),
            ("int16", "centerX", None, None, "Center x coordinate. VarIndexBase + 0."),
            ("int16", "centerY", None, None, "Center y coordinate. VarIndexBase + 1."),
            (
                "BiasedAngle",
                "startAngle",
                None,
                None,
                "Start of the angular range of the gradient. VarIndexBase + 2.",
            ),
            (
                "BiasedAngle",
                "endAngle",
                None,
                None,
                "End of the angular range of the gradient. VarIndexBase + 3.",
            ),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintGlyph
    (
        "PaintFormat10",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 10"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintGlyph table) to Paint subtable.",
            ),
            ("GlyphID", "Glyph", None, None, "Glyph ID for the source outline."),
        ],
    ),
    # PaintColrGlyph
    (
        "PaintFormat11",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 11"),
            (
                "GlyphID",
                "Glyph",
                None,
                None,
                "Virtual glyph ID for a BaseGlyphList base glyph.",
            ),
        ],
    ),
    # PaintTransform
    (
        "PaintFormat12",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 12"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintTransform table) to Paint subtable.",
            ),
            (
                "LOffset24To(Affine2x3)",
                "Transform",
                None,
                None,
                "2x3 matrix for 2D affine transformations.",
            ),
        ],
    ),
    # PaintVarTransform
    (
        "PaintFormat13",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 13"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintVarTransform table) to Paint subtable.",
            ),
            (
                "LOffset24To(VarAffine2x3)",
                "Transform",
                None,
                None,
                "2x3 matrix for 2D affine transformations.",
            ),
        ],
    ),
    # PaintTranslate
    (
        "PaintFormat14",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 14"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintTranslate table) to Paint subtable.",
            ),
            ("int16", "dx", None, None, "Translation in x direction."),
            ("int16", "dy", None, None, "Translation in y direction."),
        ],
    ),
    # PaintVarTranslate
    (
        "PaintFormat15",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 15"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintVarTranslate table) to Paint subtable.",
            ),
            (
                "int16",
                "dx",
                None,
                None,
                "Translation in x direction. VarIndexBase + 0.",
            ),
            (
                "int16",
                "dy",
                None,
                None,
                "Translation in y direction. VarIndexBase + 1.",
            ),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintScale
    (
        "PaintFormat16",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 16"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintScale table) to Paint subtable.",
            ),
            ("F2Dot14", "scaleX", None, None, ""),
            ("F2Dot14", "scaleY", None, None, ""),
        ],
    ),
    # PaintVarScale
    (
        "PaintFormat17",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 17"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintVarScale table) to Paint subtable.",
            ),
            ("F2Dot14", "scaleX", None, None, "VarIndexBase + 0."),
            ("F2Dot14", "scaleY", None, None, "VarIndexBase + 1."),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintScaleAroundCenter
    (
        "PaintFormat18",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 18"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintScaleAroundCenter table) to Paint subtable.",
            ),
            ("F2Dot14", "scaleX", None, None, ""),
            ("F2Dot14", "scaleY", None, None, ""),
            ("int16", "centerX", None, None, ""),
            ("int16", "centerY", None, None, ""),
        ],
    ),
    # PaintVarScaleAroundCenter
    (
        "PaintFormat19",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 19"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintVarScaleAroundCenter table) to Paint subtable.",
            ),
            ("F2Dot14", "scaleX", None, None, "VarIndexBase + 0."),
            ("F2Dot14", "scaleY", None, None, "VarIndexBase + 1."),
            ("int16", "centerX", None, None, "VarIndexBase + 2."),
            ("int16", "centerY", None, None, "VarIndexBase + 3."),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintScaleUniform
    (
        "PaintFormat20",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 20"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintScaleUniform table) to Paint subtable.",
            ),
            ("F2Dot14", "scale", None, None, ""),
        ],
    ),
    # PaintVarScaleUniform
    (
        "PaintFormat21",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 21"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintVarScaleUniform table) to Paint subtable.",
            ),
            ("F2Dot14", "scale", None, None, "VarIndexBase + 0."),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintScaleUniformAroundCenter
    (
        "PaintFormat22",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 22"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintScaleUniformAroundCenter table) to Paint subtable.",
            ),
            ("F2Dot14", "scale", None, None, ""),
            ("int16", "centerX", None, None, ""),
            ("int16", "centerY", None, None, ""),
        ],
    ),
    # PaintVarScaleUniformAroundCenter
    (
        "PaintFormat23",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 23"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintVarScaleUniformAroundCenter table) to Paint subtable.",
            ),
            ("F2Dot14", "scale", None, None, "VarIndexBase + 0"),
            ("int16", "centerX", None, None, "VarIndexBase + 1"),
            ("int16", "centerY", None, None, "VarIndexBase + 2"),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintRotate
    (
        "PaintFormat24",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 24"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintRotate table) to Paint subtable.",
            ),
            ("Angle", "angle", None, None, ""),
        ],
    ),
    # PaintVarRotate
    (
        "PaintFormat25",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 25"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintVarRotate table) to Paint subtable.",
            ),
            ("Angle", "angle", None, None, "VarIndexBase + 0."),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintRotateAroundCenter
    (
        "PaintFormat26",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 26"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintRotateAroundCenter table) to Paint subtable.",
            ),
            ("Angle", "angle", None, None, ""),
            ("int16", "centerX", None, None, ""),
            ("int16", "centerY", None, None, ""),
        ],
    ),
    # PaintVarRotateAroundCenter
    (
        "PaintFormat27",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 27"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintVarRotateAroundCenter table) to Paint subtable.",
            ),
            ("Angle", "angle", None, None, "VarIndexBase + 0."),
            ("int16", "centerX", None, None, "VarIndexBase + 1."),
            ("int16", "centerY", None, None, "VarIndexBase + 2."),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintSkew
    (
        "PaintFormat28",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 28"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintSkew table) to Paint subtable.",
            ),
            ("Angle", "xSkewAngle", None, None, ""),
            ("Angle", "ySkewAngle", None, None, ""),
        ],
    ),
    # PaintVarSkew
    (
        "PaintFormat29",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 29"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintVarSkew table) to Paint subtable.",
            ),
            ("Angle", "xSkewAngle", None, None, "VarIndexBase + 0."),
            ("Angle", "ySkewAngle", None, None, "VarIndexBase + 1."),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintSkewAroundCenter
    (
        "PaintFormat30",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 30"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintSkewAroundCenter table) to Paint subtable.",
            ),
            ("Angle", "xSkewAngle", None, None, ""),
            ("Angle", "ySkewAngle", None, None, ""),
            ("int16", "centerX", None, None, ""),
            ("int16", "centerY", None, None, ""),
        ],
    ),
    # PaintVarSkewAroundCenter
    (
        "PaintFormat31",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 31"),
            (
                "Offset24",
                "Paint",
                None,
                None,
                "Offset (from beginning of PaintVarSkewAroundCenter table) to Paint subtable.",
            ),
            ("Angle", "xSkewAngle", None, None, "VarIndexBase + 0."),
            ("Angle", "ySkewAngle", None, None, "VarIndexBase + 1."),
            ("int16", "centerX", None, None, "VarIndexBase + 2."),
            ("int16", "centerY", None, None, "VarIndexBase + 3."),
            (
                "VarIndex",
                "VarIndexBase",
                None,
                None,
                "Base index into DeltaSetIndexMap.",
            ),
        ],
    ),
    # PaintComposite
    (
        "PaintFormat32",
        [
            ("uint8", "PaintFormat", None, None, "Format identifier-format = 32"),
            (
                "LOffset24To(Paint)",
                "SourcePaint",
                None,
                None,
                "Offset (from beginning of PaintComposite table) to source Paint subtable.",
            ),
            (
                "CompositeMode",
                "CompositeMode",
                None,
                None,
                "A CompositeMode enumeration value.",
            ),
            (
                "LOffset24To(Paint)",
                "BackdropPaint",
                None,
                None,
                "Offset (from beginning of PaintComposite table) to backdrop Paint subtable.",
            ),
        ],
    ),
    #
    # avar
    #
    (
        "AxisValueMap",
        [
            (
                "F2Dot14",
                "FromCoordinate",
                None,
                None,
                "A normalized coordinate value obtained using default normalization",
            ),
            (
                "F2Dot14",
                "ToCoordinate",
                None,
                None,
                "The modified, normalized coordinate value",
            ),
        ],
    ),
    (
        "AxisSegmentMap",
        [
            (
                "uint16",
                "PositionMapCount",
                None,
                None,
                "The number of correspondence pairs for this axis",
            ),
            (
                "AxisValueMap",
                "AxisValueMap",
                "PositionMapCount",
                0,
                "The array of axis value map records for this axis",
            ),
        ],
    ),
    (
        "avar",
        [
            (
                "Version",
                "Version",
                None,
                None,
                "Version of the avar table- 0x00010000 or 0x00020000",
            ),
            ("uint16", "Reserved", None, None, "Permanently reserved; set to zero"),
            (
                "uint16",
                "AxisCount",
                None,
                None,
                'The number of variation axes for this font. This must be the same number as axisCount in the "fvar" table',
            ),
            (
                "AxisSegmentMap",
                "AxisSegmentMap",
                "AxisCount",
                0,
                'The segment maps array — one segment map for each axis, in the order of axes specified in the "fvar" table',
            ),
            (
                "LOffsetTo(DeltaSetIndexMap)",
                "VarIdxMap",
                None,
                "Version >= 0x00020000",
                "",
            ),
            ("LOffset", "VarStore", None, "Version >= 0x00020000", ""),
        ],
    ),
]