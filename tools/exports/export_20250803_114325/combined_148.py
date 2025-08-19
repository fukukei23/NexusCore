
# === NexusCore/openenv\Lib\site-packages\litellm\router_strategy\lowest_tpm_rpm_v2.py ===
#### What this does ####
#   identifies lowest tpm deployment
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import httpx

import litellm
from litellm import token_counter
from litellm._logging import verbose_logger, verbose_router_logger
from litellm.caching.caching import DualCache
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.core_helpers import _get_parent_otel_span_from_kwargs
from litellm.types.router import RouterErrors
from litellm.types.utils import LiteLLMPydanticObjectBase, StandardLoggingPayload
from litellm.utils import get_utc_datetime, print_verbose

from .base_routing_strategy import BaseRoutingStrategy

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = Union[_Span, Any]
else:
    Span = Any


class RoutingArgs(LiteLLMPydanticObjectBase):
    ttl: int = 1 * 60  # 1min (RPM/TPM expire key)


class LowestTPMLoggingHandler_v2(BaseRoutingStrategy, CustomLogger):
    """
    Updated version of TPM/RPM Logging.

    Meant to work across instances.

    Caches individual models, not model_groups

    Uses batch get (redis.mget)

    Increments tpm/rpm limit using redis.incr
    """

    test_flag: bool = False
    logged_success: int = 0
    logged_failure: int = 0
    default_cache_time_seconds: int = 1 * 60 * 60  # 1 hour

    def __init__(
        self, router_cache: DualCache, model_list: list, routing_args: dict = {}
    ):
        self.router_cache = router_cache
        self.model_list = model_list
        self.routing_args = RoutingArgs(**routing_args)
        BaseRoutingStrategy.__init__(
            self,
            dual_cache=router_cache,
            should_batch_redis_writes=True,
            default_sync_interval=0.1,
        )

    def pre_call_check(self, deployment: Dict) -> Optional[Dict]:
        """
        Pre-call check + update model rpm

        Returns - deployment

        Raises - RateLimitError if deployment over defined RPM limit
        """
        try:
            # ------------
            # Setup values
            # ------------

            dt = get_utc_datetime()
            current_minute = dt.strftime("%H-%M")
            model_id = deployment.get("model_info", {}).get("id")
            deployment_name = deployment.get("litellm_params", {}).get("model")
            rpm_key = f"{model_id}:{deployment_name}:rpm:{current_minute}"

            local_result = self.router_cache.get_cache(
                key=rpm_key, local_only=True
            )  # check local result first

            deployment_rpm = None
            if deployment_rpm is None:
                deployment_rpm = deployment.get("rpm")
            if deployment_rpm is None:
                deployment_rpm = deployment.get("litellm_params", {}).get("rpm")
            if deployment_rpm is None:
                deployment_rpm = deployment.get("model_info", {}).get("rpm")
            if deployment_rpm is None:
                deployment_rpm = float("inf")

            if local_result is not None and local_result >= deployment_rpm:
                raise litellm.RateLimitError(
                    message="Deployment over defined rpm limit={}. current usage={}".format(
                        deployment_rpm, local_result
                    ),
                    llm_provider="",
                    model=deployment.get("litellm_params", {}).get("model"),
                    response=httpx.Response(
                        status_code=429,
                        content="{} rpm limit={}. current usage={}. id={}, model_group={}. Get the model info by calling 'router.get_model_info(id)".format(
                            RouterErrors.user_defined_ratelimit_error.value,
                            deployment_rpm,
                            local_result,
                            model_id,
                            deployment.get("model_name", ""),
                        ),
                        request=httpx.Request(method="tpm_rpm_limits", url="https://github.com/BerriAI/litellm"),  # type: ignore
                    ),
                )
            else:
                # if local result below limit, check redis ## prevent unnecessary redis checks

                result = self.router_cache.increment_cache(
                    key=rpm_key, value=1, ttl=self.routing_args.ttl
                )
                if result is not None and result > deployment_rpm:
                    raise litellm.RateLimitError(
                        message="Deployment over defined rpm limit={}. current usage={}".format(
                            deployment_rpm, result
                        ),
                        llm_provider="",
                        model=deployment.get("litellm_params", {}).get("model"),
                        response=httpx.Response(
                            status_code=429,
                            content="{} rpm limit={}. current usage={}".format(
                                RouterErrors.user_defined_ratelimit_error.value,
                                deployment_rpm,
                                result,
                            ),
                            request=httpx.Request(method="tpm_rpm_limits", url="https://github.com/BerriAI/litellm"),  # type: ignore
                        ),
                    )
            return deployment
        except Exception as e:
            if isinstance(e, litellm.RateLimitError):
                raise e
            return deployment  # don't fail calls if eg. redis fails to connect

    async def async_pre_call_check(
        self, deployment: Dict, parent_otel_span: Optional[Span]
    ) -> Optional[Dict]:
        """
        Pre-call check + update model rpm
        - Used inside semaphore
        - raise rate limit error if deployment over limit

        Why? solves concurrency issue - https://github.com/BerriAI/litellm/issues/2994

        Returns - deployment

        Raises - RateLimitError if deployment over defined RPM limit
        """
        try:
            # ------------
            # Setup values
            # ------------
            dt = get_utc_datetime()
            current_minute = dt.strftime("%H-%M")
            model_id = deployment.get("model_info", {}).get("id")
            deployment_name = deployment.get("litellm_params", {}).get("model")

            rpm_key = f"{model_id}:{deployment_name}:rpm:{current_minute}"
            local_result = await self.router_cache.async_get_cache(
                key=rpm_key, local_only=True
            )  # check local result first

            deployment_rpm = None
            if deployment_rpm is None:
                deployment_rpm = deployment.get("rpm")
            if deployment_rpm is None:
                deployment_rpm = deployment.get("litellm_params", {}).get("rpm")
            if deployment_rpm is None:
                deployment_rpm = deployment.get("model_info", {}).get("rpm")
            if deployment_rpm is None:
                deployment_rpm = float("inf")
            if local_result is not None and local_result >= deployment_rpm:
                raise litellm.RateLimitError(
                    message="Deployment over defined rpm limit={}. current usage={}".format(
                        deployment_rpm, local_result
                    ),
                    llm_provider="",
                    model=deployment.get("litellm_params", {}).get("model"),
                    response=httpx.Response(
                        status_code=429,
                        content="{} rpm limit={}. current usage={}".format(
                            RouterErrors.user_defined_ratelimit_error.value,
                            deployment_rpm,
                            local_result,
                        ),
                        headers={"retry-after": str(60)},  # type: ignore
                        request=httpx.Request(method="tpm_rpm_limits", url="https://github.com/BerriAI/litellm"),  # type: ignore
                    ),
                    num_retries=deployment.get("num_retries"),
                )
            else:
                # if local result below limit, check redis ## prevent unnecessary redis checks
                result = await self._increment_value_in_current_window(
                    key=rpm_key, value=1, ttl=self.routing_args.ttl
                )
                if result is not None and result > deployment_rpm:
                    raise litellm.RateLimitError(
                        message="Deployment over defined rpm limit={}. current usage={}".format(
                            deployment_rpm, result
                        ),
                        llm_provider="",
                        model=deployment.get("litellm_params", {}).get("model"),
                        response=httpx.Response(
                            status_code=429,
                            content="{} rpm limit={}. current usage={}".format(
                                RouterErrors.user_defined_ratelimit_error.value,
                                deployment_rpm,
                                result,
                            ),
                            headers={"retry-after": str(60)},  # type: ignore
                            request=httpx.Request(method="tpm_rpm_limits", url="https://github.com/BerriAI/litellm"),  # type: ignore
                        ),
                        num_retries=deployment.get("num_retries"),
                    )
            return deployment
        except Exception as e:
            if isinstance(e, litellm.RateLimitError):
                raise e
            return deployment  # don't fail calls if eg. redis fails to connect

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            """
            Update TPM/RPM usage on success
            """
            standard_logging_object: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object"
            )
            if standard_logging_object is None:
                raise ValueError("standard_logging_object not passed in.")
            model_group = standard_logging_object.get("model_group")
            model = standard_logging_object["hidden_params"].get("litellm_model_name")
            id = standard_logging_object.get("model_id")
            if model_group is None or id is None or model is None:
                return
            elif isinstance(id, int):
                id = str(id)

            total_tokens = standard_logging_object.get("total_tokens")

            # ------------
            # Setup values
            # ------------
            dt = get_utc_datetime()
            current_minute = dt.strftime(
                "%H-%M"
            )  # use the same timezone regardless of system clock

            tpm_key = f"{id}:{model}:tpm:{current_minute}"
            # ------------
            # Update usage
            # ------------
            # update cache

            ## TPM
            self.router_cache.increment_cache(
                key=tpm_key, value=total_tokens, ttl=self.routing_args.ttl
            )
            ### TESTING ###
            if self.test_flag:
                self.logged_success += 1
        except Exception as e:
            verbose_logger.exception(
                "litellm.proxy.hooks.lowest_tpm_rpm_v2.py::log_success_event(): Exception occured - {}".format(
                    str(e)
                )
            )
            pass

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            """
            Update TPM usage on success
            """
            standard_logging_object: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object"
            )
            if standard_logging_object is None:
                raise ValueError("standard_logging_object not passed in.")
            model_group = standard_logging_object.get("model_group")
            model = standard_logging_object["hidden_params"]["litellm_model_name"]
            id = standard_logging_object.get("model_id")
            if model_group is None or id is None:
                return
            elif isinstance(id, int):
                id = str(id)
            total_tokens = standard_logging_object.get("total_tokens")
            # ------------
            # Setup values
            # ------------
            dt = get_utc_datetime()
            current_minute = dt.strftime(
                "%H-%M"
            )  # use the same timezone regardless of system clock

            tpm_key = f"{id}:{model}:tpm:{current_minute}"
            # ------------
            # Update usage
            # ------------
            # update cache
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
            ## TPM
            await self.router_cache.async_increment_cache(
                key=tpm_key,
                value=total_tokens,
                ttl=self.routing_args.ttl,
                parent_otel_span=parent_otel_span,
            )

            ### TESTING ###
            if self.test_flag:
                self.logged_success += 1
        except Exception as e:
            verbose_logger.exception(
                "litellm.proxy.hooks.lowest_tpm_rpm_v2.py::async_log_success_event(): Exception occured - {}".format(
                    str(e)
                )
            )
            pass

    def _return_potential_deployments(
        self,
        healthy_deployments: List[Dict],
        all_deployments: Dict,
        input_tokens: int,
        rpm_dict: Dict,
    ):
        lowest_tpm = float("inf")
        potential_deployments = []  # if multiple deployments have the same low value
        for item, item_tpm in all_deployments.items():
            ## get the item from model list
            _deployment = None
            item = item.split(":")[0]
            for m in healthy_deployments:
                if item == m["model_info"]["id"]:
                    _deployment = m
            if _deployment is None:
                continue  # skip to next one
            elif item_tpm is None:
                continue  # skip if unhealthy deployment

            _deployment_tpm = None
            if _deployment_tpm is None:
                _deployment_tpm = _deployment.get("tpm")
            if _deployment_tpm is None:
                _deployment_tpm = _deployment.get("litellm_params", {}).get("tpm")
            if _deployment_tpm is None:
                _deployment_tpm = _deployment.get("model_info", {}).get("tpm")
            if _deployment_tpm is None:
                _deployment_tpm = float("inf")

            _deployment_rpm = None
            if _deployment_rpm is None:
                _deployment_rpm = _deployment.get("rpm")
            if _deployment_rpm is None:
                _deployment_rpm = _deployment.get("litellm_params", {}).get("rpm")
            if _deployment_rpm is None:
                _deployment_rpm = _deployment.get("model_info", {}).get("rpm")
            if _deployment_rpm is None:
                _deployment_rpm = float("inf")
            if item_tpm + input_tokens > _deployment_tpm:
                continue
            elif (
                (rpm_dict is not None and item in rpm_dict)
                and rpm_dict[item] is not None
                and (rpm_dict[item] + 1 >= _deployment_rpm)
            ):
                continue
            elif item_tpm == lowest_tpm:
                potential_deployments.append(_deployment)
            elif item_tpm < lowest_tpm:
                lowest_tpm = item_tpm
                potential_deployments = [_deployment]
        return potential_deployments

    def _common_checks_available_deployment(  # noqa: PLR0915
        self,
        model_group: str,
        healthy_deployments: list,
        tpm_keys: list,
        tpm_values: Optional[list],
        rpm_keys: list,
        rpm_values: Optional[list],
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
    ) -> Optional[dict]:
        """
        Common checks for get available deployment, across sync + async implementations
        """

        if tpm_values is None or rpm_values is None:
            return None

        tpm_dict = {}  # {model_id: 1, ..}
        for idx, key in enumerate(tpm_keys):
            tpm_dict[tpm_keys[idx].split(":")[0]] = tpm_values[idx]

        rpm_dict = {}  # {model_id: 1, ..}
        for idx, key in enumerate(rpm_keys):
            rpm_dict[rpm_keys[idx].split(":")[0]] = rpm_values[idx]

        try:
            input_tokens = token_counter(messages=messages, text=input)
        except Exception:
            input_tokens = 0
        verbose_router_logger.debug(f"input_tokens={input_tokens}")
        # -----------------------
        # Find lowest used model
        # ----------------------

        if tpm_dict is None:  # base case - none of the deployments have been used
            # initialize a tpm dict with {model_id: 0}
            tpm_dict = {}
            for deployment in healthy_deployments:
                tpm_dict[deployment["model_info"]["id"]] = 0
        else:
            for d in healthy_deployments:
                ## if healthy deployment not yet used
                tpm_key = d["model_info"]["id"]
                if tpm_key not in tpm_dict or tpm_dict[tpm_key] is None:
                    tpm_dict[tpm_key] = 0

        all_deployments = tpm_dict
        potential_deployments = self._return_potential_deployments(
            healthy_deployments=healthy_deployments,
            all_deployments=all_deployments,
            input_tokens=input_tokens,
            rpm_dict=rpm_dict,
        )
        print_verbose("returning picked lowest tpm/rpm deployment.")

        if len(potential_deployments) > 0:
            return random.choice(potential_deployments)
        else:
            return None

    async def async_get_available_deployments(
        self,
        model_group: str,
        healthy_deployments: list,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
    ):
        """
        Async implementation of get deployments.

        Reduces time to retrieve the tpm/rpm values from cache
        """
        # get list of potential deployments
        verbose_router_logger.debug(
            f"get_available_deployments - Usage Based. model_group: {model_group}, healthy_deployments: {healthy_deployments}"
        )

        dt = get_utc_datetime()
        current_minute = dt.strftime("%H-%M")

        tpm_keys = []
        rpm_keys = []
        for m in healthy_deployments:
            if isinstance(m, dict):
                id = m.get("model_info", {}).get(
                    "id"
                )  # a deployment should always have an 'id'. this is set in router.py
                deployment_name = m.get("litellm_params", {}).get("model")
                tpm_key = "{}:{}:tpm:{}".format(id, deployment_name, current_minute)
                rpm_key = "{}:{}:rpm:{}".format(id, deployment_name, current_minute)

                tpm_keys.append(tpm_key)
                rpm_keys.append(rpm_key)

        combined_tpm_rpm_keys = tpm_keys + rpm_keys

        combined_tpm_rpm_values = await self.router_cache.async_batch_get_cache(
            keys=combined_tpm_rpm_keys
        )  # [1, 2, None, ..]

        if combined_tpm_rpm_values is not None:
            tpm_values = combined_tpm_rpm_values[: len(tpm_keys)]
            rpm_values = combined_tpm_rpm_values[len(tpm_keys) :]
        else:
            tpm_values = None
            rpm_values = None

        deployment = self._common_checks_available_deployment(
            model_group=model_group,
            healthy_deployments=healthy_deployments,
            tpm_keys=tpm_keys,
            tpm_values=tpm_values,
            rpm_keys=rpm_keys,
            rpm_values=rpm_values,
            messages=messages,
            input=input,
        )

        try:
            assert deployment is not None
            return deployment
        except Exception:
            ### GET THE DICT OF TPM / RPM + LIMITS PER DEPLOYMENT ###
            deployment_dict = {}
            for index, _deployment in enumerate(healthy_deployments):
                if isinstance(_deployment, dict):
                    id = _deployment.get("model_info", {}).get("id")
                    ### GET DEPLOYMENT TPM LIMIT ###
                    _deployment_tpm = None
                    if _deployment_tpm is None:
                        _deployment_tpm = _deployment.get("tpm", None)
                    if _deployment_tpm is None:
                        _deployment_tpm = _deployment.get("litellm_params", {}).get(
                            "tpm", None
                        )
                    if _deployment_tpm is None:
                        _deployment_tpm = _deployment.get("model_info", {}).get(
                            "tpm", None
                        )
                    if _deployment_tpm is None:
                        _deployment_tpm = float("inf")

                    ### GET CURRENT TPM ###
                    current_tpm = tpm_values[index] if tpm_values else 0

                    ### GET DEPLOYMENT TPM LIMIT ###
                    _deployment_rpm = None
                    if _deployment_rpm is None:
                        _deployment_rpm = _deployment.get("rpm", None)
                    if _deployment_rpm is None:
                        _deployment_rpm = _deployment.get("litellm_params", {}).get(
                            "rpm", None
                        )
                    if _deployment_rpm is None:
                        _deployment_rpm = _deployment.get("model_info", {}).get(
                            "rpm", None
                        )
                    if _deployment_rpm is None:
                        _deployment_rpm = float("inf")

                    ### GET CURRENT RPM ###
                    current_rpm = rpm_values[index] if rpm_values else 0

                    deployment_dict[id] = {
                        "current_tpm": current_tpm,
                        "tpm_limit": _deployment_tpm,
                        "current_rpm": current_rpm,
                        "rpm_limit": _deployment_rpm,
                    }
            raise litellm.RateLimitError(
                message=f"{RouterErrors.no_deployments_available.value}. Passed model={model_group}. Deployments={deployment_dict}",
                llm_provider="",
                model=model_group,
                response=httpx.Response(
                    status_code=429,
                    content="",
                    headers={"retry-after": str(60)},  # type: ignore
                    request=httpx.Request(method="tpm_rpm_limits", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
            )

    def get_available_deployments(
        self,
        model_group: str,
        healthy_deployments: list,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
        parent_otel_span: Optional[Span] = None,
    ):
        """
        Returns a deployment with the lowest TPM/RPM usage.
        """
        # get list of potential deployments
        verbose_router_logger.debug(
            f"get_available_deployments - Usage Based. model_group: {model_group}, healthy_deployments: {healthy_deployments}"
        )

        dt = get_utc_datetime()
        current_minute = dt.strftime("%H-%M")
        tpm_keys = []
        rpm_keys = []
        for m in healthy_deployments:
            if isinstance(m, dict):
                id = m.get("model_info", {}).get(
                    "id"
                )  # a deployment should always have an 'id'. this is set in router.py
                deployment_name = m.get("litellm_params", {}).get("model")
                tpm_key = "{}:{}:tpm:{}".format(id, deployment_name, current_minute)
                rpm_key = "{}:{}:rpm:{}".format(id, deployment_name, current_minute)

                tpm_keys.append(tpm_key)
                rpm_keys.append(rpm_key)

        tpm_values = self.router_cache.batch_get_cache(
            keys=tpm_keys, parent_otel_span=parent_otel_span
        )  # [1, 2, None, ..]
        rpm_values = self.router_cache.batch_get_cache(
            keys=rpm_keys, parent_otel_span=parent_otel_span
        )  # [1, 2, None, ..]

        deployment = self._common_checks_available_deployment(
            model_group=model_group,
            healthy_deployments=healthy_deployments,
            tpm_keys=tpm_keys,
            tpm_values=tpm_values,
            rpm_keys=rpm_keys,
            rpm_values=rpm_values,
            messages=messages,
            input=input,
        )

        try:
            assert deployment is not None
            return deployment
        except Exception:
            ### GET THE DICT OF TPM / RPM + LIMITS PER DEPLOYMENT ###
            deployment_dict = {}
            for index, _deployment in enumerate(healthy_deployments):
                if isinstance(_deployment, dict):
                    id = _deployment.get("model_info", {}).get("id")
                    ### GET DEPLOYMENT TPM LIMIT ###
                    _deployment_tpm = None
                    if _deployment_tpm is None:
                        _deployment_tpm = _deployment.get("tpm", None)
                    if _deployment_tpm is None:
                        _deployment_tpm = _deployment.get("litellm_params", {}).get(
                            "tpm", None
                        )
                    if _deployment_tpm is None:
                        _deployment_tpm = _deployment.get("model_info", {}).get(
                            "tpm", None
                        )
                    if _deployment_tpm is None:
                        _deployment_tpm = float("inf")

                    ### GET CURRENT TPM ###
                    current_tpm = tpm_values[index] if tpm_values else 0

                    ### GET DEPLOYMENT TPM LIMIT ###
                    _deployment_rpm = None
                    if _deployment_rpm is None:
                        _deployment_rpm = _deployment.get("rpm", None)
                    if _deployment_rpm is None:
                        _deployment_rpm = _deployment.get("litellm_params", {}).get(
                            "rpm", None
                        )
                    if _deployment_rpm is None:
                        _deployment_rpm = _deployment.get("model_info", {}).get(
                            "rpm", None
                        )
                    if _deployment_rpm is None:
                        _deployment_rpm = float("inf")

                    ### GET CURRENT RPM ###
                    current_rpm = rpm_values[index] if rpm_values else 0

                    deployment_dict[id] = {
                        "current_tpm": current_tpm,
                        "tpm_limit": _deployment_tpm,
                        "current_rpm": current_rpm,
                        "rpm_limit": _deployment_rpm,
                    }
            raise ValueError(
                f"{RouterErrors.no_deployments_available.value}. Passed model={model_group}. Deployments={deployment_dict}"
            )

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\key_binding\key_bindings.py ===
"""
Key bindings registry.

A `KeyBindings` object is a container that holds a list of key bindings. It has a
very efficient internal data structure for checking which key bindings apply
for a pressed key.

Typical usage::

    kb = KeyBindings()

    @kb.add(Keys.ControlX, Keys.ControlC, filter=INSERT)
    def handler(event):
        # Handle ControlX-ControlC key sequence.
        pass

It is also possible to combine multiple KeyBindings objects. We do this in the
default key bindings. There are some KeyBindings objects that contain the Emacs
bindings, while others contain the Vi bindings. They are merged together using
`merge_key_bindings`.

We also have a `ConditionalKeyBindings` object that can enable/disable a group of
key bindings at once.


It is also possible to add a filter to a function, before a key binding has
been assigned, through the `key_binding` decorator.::

    # First define a key handler with the `filter`.
    @key_binding(filter=condition)
    def my_key_binding(event):
        ...

    # Later, add it to the key bindings.
    kb.add(Keys.A, my_key_binding)
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod, abstractproperty
from inspect import isawaitable
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Hashable,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.filters import FilterOrBool, Never, to_filter
from prompt_toolkit.keys import KEY_ALIASES, Keys

if TYPE_CHECKING:
    # Avoid circular imports.
    from .key_processor import KeyPressEvent

    # The only two return values for a mouse handler (and key bindings) are
    # `None` and `NotImplemented`. For the type checker it's best to annotate
    # this as `object`. (The consumer never expects a more specific instance:
    # checking for NotImplemented can be done using `is NotImplemented`.)
    NotImplementedOrNone = object
    # Other non-working options are:
    # * Optional[Literal[NotImplemented]]
    #      --> Doesn't work, Literal can't take an Any.
    # * None
    #      --> Doesn't work. We can't assign the result of a function that
    #          returns `None` to a variable.
    # * Any
    #      --> Works, but too broad.


__all__ = [
    "NotImplementedOrNone",
    "Binding",
    "KeyBindingsBase",
    "KeyBindings",
    "ConditionalKeyBindings",
    "merge_key_bindings",
    "DynamicKeyBindings",
    "GlobalOnlyKeyBindings",
]

# Key bindings can be regular functions or coroutines.
# In both cases, if they return `NotImplemented`, the UI won't be invalidated.
# This is mainly used in case of mouse move events, to prevent excessive
# repainting during mouse move events.
KeyHandlerCallable = Callable[
    ["KeyPressEvent"],
    Union["NotImplementedOrNone", Coroutine[Any, Any, "NotImplementedOrNone"]],
]


class Binding:
    """
    Key binding: (key sequence + handler + filter).
    (Immutable binding class.)

    :param record_in_macro: When True, don't record this key binding when a
        macro is recorded.
    """

    def __init__(
        self,
        keys: tuple[Keys | str, ...],
        handler: KeyHandlerCallable,
        filter: FilterOrBool = True,
        eager: FilterOrBool = False,
        is_global: FilterOrBool = False,
        save_before: Callable[[KeyPressEvent], bool] = (lambda e: True),
        record_in_macro: FilterOrBool = True,
    ) -> None:
        self.keys = keys
        self.handler = handler
        self.filter = to_filter(filter)
        self.eager = to_filter(eager)
        self.is_global = to_filter(is_global)
        self.save_before = save_before
        self.record_in_macro = to_filter(record_in_macro)

    def call(self, event: KeyPressEvent) -> None:
        result = self.handler(event)

        # If the handler is a coroutine, create an asyncio task.
        if isawaitable(result):
            awaitable = cast(Coroutine[Any, Any, "NotImplementedOrNone"], result)

            async def bg_task() -> None:
                result = await awaitable
                if result != NotImplemented:
                    event.app.invalidate()

            event.app.create_background_task(bg_task())

        elif result != NotImplemented:
            event.app.invalidate()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(keys={self.keys!r}, handler={self.handler!r})"
        )


# Sequence of keys presses.
KeysTuple = Tuple[Union[Keys, str], ...]


class KeyBindingsBase(metaclass=ABCMeta):
    """
    Interface for a KeyBindings.
    """

    @abstractproperty
    def _version(self) -> Hashable:
        """
        For cache invalidation. - This should increase every time that
        something changes.
        """
        return 0

    @abstractmethod
    def get_bindings_for_keys(self, keys: KeysTuple) -> list[Binding]:
        """
        Return a list of key bindings that can handle these keys.
        (This return also inactive bindings, so the `filter` still has to be
        called, for checking it.)

        :param keys: tuple of keys.
        """
        return []

    @abstractmethod
    def get_bindings_starting_with_keys(self, keys: KeysTuple) -> list[Binding]:
        """
        Return a list of key bindings that handle a key sequence starting with
        `keys`. (It does only return bindings for which the sequences are
        longer than `keys`. And like `get_bindings_for_keys`, it also includes
        inactive bindings.)

        :param keys: tuple of keys.
        """
        return []

    @abstractproperty
    def bindings(self) -> list[Binding]:
        """
        List of `Binding` objects.
        (These need to be exposed, so that `KeyBindings` objects can be merged
        together.)
        """
        return []

    # `add` and `remove` don't have to be part of this interface.


T = TypeVar("T", bound=Union[KeyHandlerCallable, Binding])


class KeyBindings(KeyBindingsBase):
    """
    A container for a set of key bindings.

    Example usage::

        kb = KeyBindings()

        @kb.add('c-t')
        def _(event):
            print('Control-T pressed')

        @kb.add('c-a', 'c-b')
        def _(event):
            print('Control-A pressed, followed by Control-B')

        @kb.add('c-x', filter=is_searching)
        def _(event):
            print('Control-X pressed')  # Works only if we are searching.

    """

    def __init__(self) -> None:
        self._bindings: list[Binding] = []
        self._get_bindings_for_keys_cache: SimpleCache[KeysTuple, list[Binding]] = (
            SimpleCache(maxsize=10000)
        )
        self._get_bindings_starting_with_keys_cache: SimpleCache[
            KeysTuple, list[Binding]
        ] = SimpleCache(maxsize=1000)
        self.__version = 0  # For cache invalidation.

    def _clear_cache(self) -> None:
        self.__version += 1
        self._get_bindings_for_keys_cache.clear()
        self._get_bindings_starting_with_keys_cache.clear()

    @property
    def bindings(self) -> list[Binding]:
        return self._bindings

    @property
    def _version(self) -> Hashable:
        return self.__version

    def add(
        self,
        *keys: Keys | str,
        filter: FilterOrBool = True,
        eager: FilterOrBool = False,
        is_global: FilterOrBool = False,
        save_before: Callable[[KeyPressEvent], bool] = (lambda e: True),
        record_in_macro: FilterOrBool = True,
    ) -> Callable[[T], T]:
        """
        Decorator for adding a key bindings.

        :param filter: :class:`~prompt_toolkit.filters.Filter` to determine
            when this key binding is active.
        :param eager: :class:`~prompt_toolkit.filters.Filter` or `bool`.
            When True, ignore potential longer matches when this key binding is
            hit. E.g. when there is an active eager key binding for Ctrl-X,
            execute the handler immediately and ignore the key binding for
            Ctrl-X Ctrl-E of which it is a prefix.
        :param is_global: When this key bindings is added to a `Container` or
            `Control`, make it a global (always active) binding.
        :param save_before: Callable that takes an `Event` and returns True if
            we should save the current buffer, before handling the event.
            (That's the default.)
        :param record_in_macro: Record these key bindings when a macro is
            being recorded. (True by default.)
        """
        assert keys

        keys = tuple(_parse_key(k) for k in keys)

        if isinstance(filter, Never):
            # When a filter is Never, it will always stay disabled, so in that
            # case don't bother putting it in the key bindings. It will slow
            # down every key press otherwise.
            def decorator(func: T) -> T:
                return func

        else:

            def decorator(func: T) -> T:
                if isinstance(func, Binding):
                    # We're adding an existing Binding object.
                    self.bindings.append(
                        Binding(
                            keys,
                            func.handler,
                            filter=func.filter & to_filter(filter),
                            eager=to_filter(eager) | func.eager,
                            is_global=to_filter(is_global) | func.is_global,
                            save_before=func.save_before,
                            record_in_macro=func.record_in_macro,
                        )
                    )
                else:
                    self.bindings.append(
                        Binding(
                            keys,
                            cast(KeyHandlerCallable, func),
                            filter=filter,
                            eager=eager,
                            is_global=is_global,
                            save_before=save_before,
                            record_in_macro=record_in_macro,
                        )
                    )
                self._clear_cache()

                return func

        return decorator

    def remove(self, *args: Keys | str | KeyHandlerCallable) -> None:
        """
        Remove a key binding.

        This expects either a function that was given to `add` method as
        parameter or a sequence of key bindings.

        Raises `ValueError` when no bindings was found.

        Usage::

            remove(handler)  # Pass handler.
            remove('c-x', 'c-a')  # Or pass the key bindings.
        """
        found = False

        if callable(args[0]):
            assert len(args) == 1
            function = args[0]

            # Remove the given function.
            for b in self.bindings:
                if b.handler == function:
                    self.bindings.remove(b)
                    found = True

        else:
            assert len(args) > 0
            args = cast(Tuple[Union[Keys, str]], args)

            # Remove this sequence of key bindings.
            keys = tuple(_parse_key(k) for k in args)

            for b in self.bindings:
                if b.keys == keys:
                    self.bindings.remove(b)
                    found = True

        if found:
            self._clear_cache()
        else:
            # No key binding found for this function. Raise ValueError.
            raise ValueError(f"Binding not found: {function!r}")

    # For backwards-compatibility.
    add_binding = add
    remove_binding = remove

    def get_bindings_for_keys(self, keys: KeysTuple) -> list[Binding]:
        """
        Return a list of key bindings that can handle this key.
        (This return also inactive bindings, so the `filter` still has to be
        called, for checking it.)

        :param keys: tuple of keys.
        """

        def get() -> list[Binding]:
            result: list[tuple[int, Binding]] = []

            for b in self.bindings:
                if len(keys) == len(b.keys):
                    match = True
                    any_count = 0

                    for i, j in zip(b.keys, keys):
                        if i != j and i != Keys.Any:
                            match = False
                            break

                        if i == Keys.Any:
                            any_count += 1

                    if match:
                        result.append((any_count, b))

            # Place bindings that have more 'Any' occurrences in them at the end.
            result = sorted(result, key=lambda item: -item[0])

            return [item[1] for item in result]

        return self._get_bindings_for_keys_cache.get(keys, get)

    def get_bindings_starting_with_keys(self, keys: KeysTuple) -> list[Binding]:
        """
        Return a list of key bindings that handle a key sequence starting with
        `keys`. (It does only return bindings for which the sequences are
        longer than `keys`. And like `get_bindings_for_keys`, it also includes
        inactive bindings.)

        :param keys: tuple of keys.
        """

        def get() -> list[Binding]:
            result = []
            for b in self.bindings:
                if len(keys) < len(b.keys):
                    match = True
                    for i, j in zip(b.keys, keys):
                        if i != j and i != Keys.Any:
                            match = False
                            break
                    if match:
                        result.append(b)
            return result

        return self._get_bindings_starting_with_keys_cache.get(keys, get)


def _parse_key(key: Keys | str) -> str | Keys:
    """
    Replace key by alias and verify whether it's a valid one.
    """
    # Already a parse key? -> Return it.
    if isinstance(key, Keys):
        return key

    # Lookup aliases.
    key = KEY_ALIASES.get(key, key)

    # Replace 'space' by ' '
    if key == "space":
        key = " "

    # Return as `Key` object when it's a special key.
    try:
        return Keys(key)
    except ValueError:
        pass

    # Final validation.
    if len(key) != 1:
        raise ValueError(f"Invalid key: {key}")

    return key


def key_binding(
    filter: FilterOrBool = True,
    eager: FilterOrBool = False,
    is_global: FilterOrBool = False,
    save_before: Callable[[KeyPressEvent], bool] = (lambda event: True),
    record_in_macro: FilterOrBool = True,
) -> Callable[[KeyHandlerCallable], Binding]:
    """
    Decorator that turn a function into a `Binding` object. This can be added
    to a `KeyBindings` object when a key binding is assigned.
    """
    assert save_before is None or callable(save_before)

    filter = to_filter(filter)
    eager = to_filter(eager)
    is_global = to_filter(is_global)
    save_before = save_before
    record_in_macro = to_filter(record_in_macro)
    keys = ()

    def decorator(function: KeyHandlerCallable) -> Binding:
        return Binding(
            keys,
            function,
            filter=filter,
            eager=eager,
            is_global=is_global,
            save_before=save_before,
            record_in_macro=record_in_macro,
        )

    return decorator


class _Proxy(KeyBindingsBase):
    """
    Common part for ConditionalKeyBindings and _MergedKeyBindings.
    """

    def __init__(self) -> None:
        # `KeyBindings` to be synchronized with all the others.
        self._bindings2: KeyBindingsBase = KeyBindings()
        self._last_version: Hashable = ()

    def _update_cache(self) -> None:
        """
        If `self._last_version` is outdated, then this should update
        the version and `self._bindings2`.
        """
        raise NotImplementedError

    # Proxy methods to self._bindings2.

    @property
    def bindings(self) -> list[Binding]:
        self._update_cache()
        return self._bindings2.bindings

    @property
    def _version(self) -> Hashable:
        self._update_cache()
        return self._last_version

    def get_bindings_for_keys(self, keys: KeysTuple) -> list[Binding]:
        self._update_cache()
        return self._bindings2.get_bindings_for_keys(keys)

    def get_bindings_starting_with_keys(self, keys: KeysTuple) -> list[Binding]:
        self._update_cache()
        return self._bindings2.get_bindings_starting_with_keys(keys)


class ConditionalKeyBindings(_Proxy):
    """
    Wraps around a `KeyBindings`. Disable/enable all the key bindings according to
    the given (additional) filter.::

        @Condition
        def setting_is_true():
            return True  # or False

        registry = ConditionalKeyBindings(key_bindings, setting_is_true)

    When new key bindings are added to this object. They are also
    enable/disabled according to the given `filter`.

    :param registries: List of :class:`.KeyBindings` objects.
    :param filter: :class:`~prompt_toolkit.filters.Filter` object.
    """

    def __init__(
        self, key_bindings: KeyBindingsBase, filter: FilterOrBool = True
    ) -> None:
        _Proxy.__init__(self)

        self.key_bindings = key_bindings
        self.filter = to_filter(filter)

    def _update_cache(self) -> None:
        "If the original key bindings was changed. Update our copy version."
        expected_version = self.key_bindings._version

        if self._last_version != expected_version:
            bindings2 = KeyBindings()

            # Copy all bindings from `self.key_bindings`, adding our condition.
            for b in self.key_bindings.bindings:
                bindings2.bindings.append(
                    Binding(
                        keys=b.keys,
                        handler=b.handler,
                        filter=self.filter & b.filter,
                        eager=b.eager,
                        is_global=b.is_global,
                        save_before=b.save_before,
                        record_in_macro=b.record_in_macro,
                    )
                )

            self._bindings2 = bindings2
            self._last_version = expected_version


class _MergedKeyBindings(_Proxy):
    """
    Merge multiple registries of key bindings into one.

    This class acts as a proxy to multiple :class:`.KeyBindings` objects, but
    behaves as if this is just one bigger :class:`.KeyBindings`.

    :param registries: List of :class:`.KeyBindings` objects.
    """

    def __init__(self, registries: Sequence[KeyBindingsBase]) -> None:
        _Proxy.__init__(self)
        self.registries = registries

    def _update_cache(self) -> None:
        """
        If one of the original registries was changed. Update our merged
        version.
        """
        expected_version = tuple(r._version for r in self.registries)

        if self._last_version != expected_version:
            bindings2 = KeyBindings()

            for reg in self.registries:
                bindings2.bindings.extend(reg.bindings)

            self._bindings2 = bindings2
            self._last_version = expected_version


def merge_key_bindings(bindings: Sequence[KeyBindingsBase]) -> _MergedKeyBindings:
    """
    Merge multiple :class:`.Keybinding` objects together.

    Usage::

        bindings = merge_key_bindings([bindings1, bindings2, ...])
    """
    return _MergedKeyBindings(bindings)


class DynamicKeyBindings(_Proxy):
    """
    KeyBindings class that can dynamically returns any KeyBindings.

    :param get_key_bindings: Callable that returns a :class:`.KeyBindings` instance.
    """

    def __init__(self, get_key_bindings: Callable[[], KeyBindingsBase | None]) -> None:
        self.get_key_bindings = get_key_bindings
        self.__version = 0
        self._last_child_version = None
        self._dummy = KeyBindings()  # Empty key bindings.

    def _update_cache(self) -> None:
        key_bindings = self.get_key_bindings() or self._dummy
        assert isinstance(key_bindings, KeyBindingsBase)
        version = id(key_bindings), key_bindings._version

        self._bindings2 = key_bindings
        self._last_version = version


class GlobalOnlyKeyBindings(_Proxy):
    """
    Wrapper around a :class:`.KeyBindings` object that only exposes the global
    key bindings.
    """

    def __init__(self, key_bindings: KeyBindingsBase) -> None:
        _Proxy.__init__(self)
        self.key_bindings = key_bindings

    def _update_cache(self) -> None:
        """
        If one of the original registries was changed. Update our merged
        version.
        """
        expected_version = self.key_bindings._version

        if self._last_version != expected_version:
            bindings2 = KeyBindings()

            for b in self.key_bindings.bindings:
                if b.is_global():
                    bindings2.bindings.append(b)

            self._bindings2 = bindings2
            self._last_version = expected_version

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\html.py ===
"""
    pygments.lexers.html
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for HTML, XML and related markup.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, ExtendedRegexLexer, include, bygroups, \
    default, using, inherit, this
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Punctuation, Whitespace
from pygments.util import looks_like_xml, html_doctype_matches

from pygments.lexers.javascript import JavascriptLexer
from pygments.lexers.jvm import ScalaLexer
from pygments.lexers.css import CssLexer, _indentation, _starts_block
from pygments.lexers.ruby import RubyLexer

__all__ = ['HtmlLexer', 'DtdLexer', 'XmlLexer', 'XsltLexer', 'HamlLexer',
           'ScamlLexer', 'PugLexer', 'VueLexer', 'UrlEncodedLexer']


class HtmlLexer(RegexLexer):
    """
    For HTML 4 and XHTML 1 markup. Nested JavaScript and CSS is highlighted
    by the appropriate lexer.
    """

    name = 'HTML'
    url = 'https://html.spec.whatwg.org/'
    aliases = ['html']
    filenames = ['*.html', '*.htm', '*.xhtml', '*.xslt']
    mimetypes = ['text/html', 'application/xhtml+xml']
    version_added = ''

    flags = re.IGNORECASE | re.DOTALL
    tokens = {
        'root': [
            ('[^<&]+', Text),
            (r'&\S*?;', Name.Entity),
            (r'\<\!\[CDATA\[.*?\]\]\>', Comment.Preproc),
            (r'<!--.*?-->', Comment.Multiline),
            (r'<\?.*?\?>', Comment.Preproc),
            ('<![^>]*>', Comment.Preproc),
            (r'(<)(\s*)(script)(\s*)',
             bygroups(Punctuation, Text, Name.Tag, Text),
             ('script-content', 'tag')),
            (r'(<)(\s*)(style)(\s*)',
             bygroups(Punctuation, Text, Name.Tag, Text),
             ('style-content', 'tag')),
            # note: this allows tag names not used in HTML like <x:with-dash>,
            # this is to support yet-unknown template engines and the like
            (r'(<)(\s*)([\w:.-]+)',
             bygroups(Punctuation, Text, Name.Tag), 'tag'),
            (r'(<)(\s*)(/)(\s*)([\w:.-]+)(\s*)(>)',
             bygroups(Punctuation, Text, Punctuation, Text, Name.Tag, Text,
                      Punctuation)),
        ],
        'tag': [
            (r'\s+', Text),
            (r'([\w:-]+\s*)(=)(\s*)', bygroups(Name.Attribute, Operator, Text),
             'attr'),
            (r'[\w:-]+', Name.Attribute),
            (r'(/?)(\s*)(>)', bygroups(Punctuation, Text, Punctuation), '#pop'),
        ],
        'script-content': [
            (r'(<)(\s*)(/)(\s*)(script)(\s*)(>)',
             bygroups(Punctuation, Text, Punctuation, Text, Name.Tag, Text,
                      Punctuation), '#pop'),
            (r'.+?(?=<\s*/\s*script\s*>)', using(JavascriptLexer)),
            # fallback cases for when there is no closing script tag
            # first look for newline and then go back into root state
            # if that fails just read the rest of the file
            # this is similar to the error handling logic in lexer.py
            (r'.+?\n', using(JavascriptLexer), '#pop'),
            (r'.+', using(JavascriptLexer), '#pop'),
        ],
        'style-content': [
            (r'(<)(\s*)(/)(\s*)(style)(\s*)(>)',
             bygroups(Punctuation, Text, Punctuation, Text, Name.Tag, Text,
                      Punctuation),'#pop'),
            (r'.+?(?=<\s*/\s*style\s*>)', using(CssLexer)),
            # fallback cases for when there is no closing style tag
            # first look for newline and then go back into root state
            # if that fails just read the rest of the file
            # this is similar to the error handling logic in lexer.py
            (r'.+?\n', using(CssLexer), '#pop'),
            (r'.+', using(CssLexer), '#pop'),
        ],
        'attr': [
            ('".*?"', String, '#pop'),
            ("'.*?'", String, '#pop'),
            (r'[^\s>]+', String, '#pop'),
        ],
    }

    def analyse_text(text):
        if html_doctype_matches(text):
            return 0.5


class DtdLexer(RegexLexer):
    """
    A lexer for DTDs (Document Type Definitions).
    """

    flags = re.MULTILINE | re.DOTALL

    name = 'DTD'
    aliases = ['dtd']
    filenames = ['*.dtd']
    mimetypes = ['application/xml-dtd']
    url = 'https://en.wikipedia.org/wiki/Document_type_definition'
    version_added = '1.5'

    tokens = {
        'root': [
            include('common'),

            (r'(<!ELEMENT)(\s+)(\S+)',
                bygroups(Keyword, Text, Name.Tag), 'element'),
            (r'(<!ATTLIST)(\s+)(\S+)',
                bygroups(Keyword, Text, Name.Tag), 'attlist'),
            (r'(<!ENTITY)(\s+)(\S+)',
                bygroups(Keyword, Text, Name.Entity), 'entity'),
            (r'(<!NOTATION)(\s+)(\S+)',
                bygroups(Keyword, Text, Name.Tag), 'notation'),
            (r'(<!\[)([^\[\s]+)(\s*)(\[)',  # conditional sections
                bygroups(Keyword, Name.Entity, Text, Keyword)),

            (r'(<!DOCTYPE)(\s+)([^>\s]+)',
                bygroups(Keyword, Text, Name.Tag)),
            (r'PUBLIC|SYSTEM', Keyword.Constant),
            (r'[\[\]>]', Keyword),
        ],

        'common': [
            (r'\s+', Text),
            (r'(%|&)[^;]*;', Name.Entity),
            ('<!--', Comment, 'comment'),
            (r'[(|)*,?+]', Operator),
            (r'"[^"]*"', String.Double),
            (r'\'[^\']*\'', String.Single),
        ],

        'comment': [
            ('[^-]+', Comment),
            ('-->', Comment, '#pop'),
            ('-', Comment),
        ],

        'element': [
            include('common'),
            (r'EMPTY|ANY|#PCDATA', Keyword.Constant),
            (r'[^>\s|()?+*,]+', Name.Tag),
            (r'>', Keyword, '#pop'),
        ],

        'attlist': [
            include('common'),
            (r'CDATA|IDREFS|IDREF|ID|NMTOKENS|NMTOKEN|ENTITIES|ENTITY|NOTATION',
             Keyword.Constant),
            (r'#REQUIRED|#IMPLIED|#FIXED', Keyword.Constant),
            (r'xml:space|xml:lang', Keyword.Reserved),
            (r'[^>\s|()?+*,]+', Name.Attribute),
            (r'>', Keyword, '#pop'),
        ],

        'entity': [
            include('common'),
            (r'SYSTEM|PUBLIC|NDATA', Keyword.Constant),
            (r'[^>\s|()?+*,]+', Name.Entity),
            (r'>', Keyword, '#pop'),
        ],

        'notation': [
            include('common'),
            (r'SYSTEM|PUBLIC', Keyword.Constant),
            (r'[^>\s|()?+*,]+', Name.Attribute),
            (r'>', Keyword, '#pop'),
        ],
    }

    def analyse_text(text):
        if not looks_like_xml(text) and \
           ('<!ELEMENT' in text or '<!ATTLIST' in text or '<!ENTITY' in text):
            return 0.8


class XmlLexer(RegexLexer):
    """
    Generic lexer for XML (eXtensible Markup Language).
    """

    flags = re.MULTILINE | re.DOTALL

    name = 'XML'
    aliases = ['xml']
    filenames = ['*.xml', '*.xsl', '*.rss', '*.xslt', '*.xsd',
                 '*.wsdl', '*.wsf']
    mimetypes = ['text/xml', 'application/xml', 'image/svg+xml',
                 'application/rss+xml', 'application/atom+xml']
    url = 'https://www.w3.org/XML'
    version_added = ''

    tokens = {
        'root': [
            (r'[^<&\s]+', Text),
            (r'[^<&\S]+', Whitespace),
            (r'&\S*?;', Name.Entity),
            (r'\<\!\[CDATA\[.*?\]\]\>', Comment.Preproc),
            (r'<!--.*?-->', Comment.Multiline),
            (r'<\?.*?\?>', Comment.Preproc),
            ('<![^>]*>', Comment.Preproc),
            (r'<\s*[\w:.-]+', Name.Tag, 'tag'),
            (r'<\s*/\s*[\w:.-]+\s*>', Name.Tag),
        ],
        'tag': [
            (r'\s+', Whitespace),
            (r'[\w.:-]+\s*=', Name.Attribute, 'attr'),
            (r'/?\s*>', Name.Tag, '#pop'),
        ],
        'attr': [
            (r'\s+', Whitespace),
            ('".*?"', String, '#pop'),
            ("'.*?'", String, '#pop'),
            (r'[^\s>]+', String, '#pop'),
        ],
    }

    def analyse_text(text):
        if looks_like_xml(text):
            return 0.45  # less than HTML


class XsltLexer(XmlLexer):
    """
    A lexer for XSLT.
    """

    name = 'XSLT'
    aliases = ['xslt']
    filenames = ['*.xsl', '*.xslt', '*.xpl']  # xpl is XProc
    mimetypes = ['application/xsl+xml', 'application/xslt+xml']
    url = 'https://www.w3.org/TR/xslt-30'
    version_added = '0.10'

    EXTRA_KEYWORDS = {
        'apply-imports', 'apply-templates', 'attribute',
        'attribute-set', 'call-template', 'choose', 'comment',
        'copy', 'copy-of', 'decimal-format', 'element', 'fallback',
        'for-each', 'if', 'import', 'include', 'key', 'message',
        'namespace-alias', 'number', 'otherwise', 'output', 'param',
        'preserve-space', 'processing-instruction', 'sort',
        'strip-space', 'stylesheet', 'template', 'text', 'transform',
        'value-of', 'variable', 'when', 'with-param'
    }

    def get_tokens_unprocessed(self, text):
        for index, token, value in XmlLexer.get_tokens_unprocessed(self, text):
            m = re.match('</?xsl:([^>]*)/?>?', value)

            if token is Name.Tag and m and m.group(1) in self.EXTRA_KEYWORDS:
                yield index, Keyword, value
            else:
                yield index, token, value

    def analyse_text(text):
        if looks_like_xml(text) and '<xsl' in text:
            return 0.8


class HamlLexer(ExtendedRegexLexer):
    """
    For Haml markup.
    """

    name = 'Haml'
    aliases = ['haml']
    filenames = ['*.haml']
    mimetypes = ['text/x-haml']
    url = 'https://haml.info'
    version_added = '1.3'

    flags = re.IGNORECASE
    # Haml can include " |\n" anywhere,
    # which is ignored and used to wrap long lines.
    # To accommodate this, use this custom faux dot instead.
    _dot = r'(?: \|\n(?=.* \|)|.)'

    # In certain places, a comma at the end of the line
    # allows line wrapping as well.
    _comma_dot = r'(?:,\s*\n|' + _dot + ')'
    tokens = {
        'root': [
            (r'[ \t]*\n', Text),
            (r'[ \t]*', _indentation),
        ],

        'css': [
            (r'\.[\w:-]+', Name.Class, 'tag'),
            (r'\#[\w:-]+', Name.Function, 'tag'),
        ],

        'eval-or-plain': [
            (r'[&!]?==', Punctuation, 'plain'),
            (r'([&!]?[=~])(' + _comma_dot + r'*\n)',
             bygroups(Punctuation, using(RubyLexer)),
             'root'),
            default('plain'),
        ],

        'content': [
            include('css'),
            (r'%[\w:-]+', Name.Tag, 'tag'),
            (r'!!!' + _dot + r'*\n', Name.Namespace, '#pop'),
            (r'(/)(\[' + _dot + r'*?\])(' + _dot + r'*\n)',
             bygroups(Comment, Comment.Special, Comment),
             '#pop'),
            (r'/' + _dot + r'*\n', _starts_block(Comment, 'html-comment-block'),
             '#pop'),
            (r'-#' + _dot + r'*\n', _starts_block(Comment.Preproc,
                                                  'haml-comment-block'), '#pop'),
            (r'(-)(' + _comma_dot + r'*\n)',
             bygroups(Punctuation, using(RubyLexer)),
             '#pop'),
            (r':' + _dot + r'*\n', _starts_block(Name.Decorator, 'filter-block'),
             '#pop'),
            include('eval-or-plain'),
        ],

        'tag': [
            include('css'),
            (r'\{(,\n|' + _dot + r')*?\}', using(RubyLexer)),
            (r'\[' + _dot + r'*?\]', using(RubyLexer)),
            (r'\(', Text, 'html-attributes'),
            (r'/[ \t]*\n', Punctuation, '#pop:2'),
            (r'[<>]{1,2}(?=[ \t=])', Punctuation),
            include('eval-or-plain'),
        ],

        'plain': [
            (r'([^#\n]|#[^{\n]|(\\\\)*\\#\{)+', Text),
            (r'(#\{)(' + _dot + r'*?)(\})',
             bygroups(String.Interpol, using(RubyLexer), String.Interpol)),
            (r'\n', Text, 'root'),
        ],

        'html-attributes': [
            (r'\s+', Text),
            (r'[\w:-]+[ \t]*=', Name.Attribute, 'html-attribute-value'),
            (r'[\w:-]+', Name.Attribute),
            (r'\)', Text, '#pop'),
        ],

        'html-attribute-value': [
            (r'[ \t]+', Text),
            (r'\w+', Name.Variable, '#pop'),
            (r'@\w+', Name.Variable.Instance, '#pop'),
            (r'\$\w+', Name.Variable.Global, '#pop'),
            (r"'(\\\\|\\[^\\]|[^'\\\n])*'", String, '#pop'),
            (r'"(\\\\|\\[^\\]|[^"\\\n])*"', String, '#pop'),
        ],

        'html-comment-block': [
            (_dot + '+', Comment),
            (r'\n', Text, 'root'),
        ],

        'haml-comment-block': [
            (_dot + '+', Comment.Preproc),
            (r'\n', Text, 'root'),
        ],

        'filter-block': [
            (r'([^#\n]|#[^{\n]|(\\\\)*\\#\{)+', Name.Decorator),
            (r'(#\{)(' + _dot + r'*?)(\})',
             bygroups(String.Interpol, using(RubyLexer), String.Interpol)),
            (r'\n', Text, 'root'),
        ],
    }


class ScamlLexer(ExtendedRegexLexer):
    """
    For Scaml markup.  Scaml is Haml for Scala.
    """

    name = 'Scaml'
    aliases = ['scaml']
    filenames = ['*.scaml']
    mimetypes = ['text/x-scaml']
    url = 'https://scalate.github.io/scalate/'
    version_added = '1.4'

    flags = re.IGNORECASE
    # Scaml does not yet support the " |\n" notation to
    # wrap long lines.  Once it does, use the custom faux
    # dot instead.
    # _dot = r'(?: \|\n(?=.* \|)|.)'
    _dot = r'.'

    tokens = {
        'root': [
            (r'[ \t]*\n', Text),
            (r'[ \t]*', _indentation),
        ],

        'css': [
            (r'\.[\w:-]+', Name.Class, 'tag'),
            (r'\#[\w:-]+', Name.Function, 'tag'),
        ],

        'eval-or-plain': [
            (r'[&!]?==', Punctuation, 'plain'),
            (r'([&!]?[=~])(' + _dot + r'*\n)',
             bygroups(Punctuation, using(ScalaLexer)),
             'root'),
            default('plain'),
        ],

        'content': [
            include('css'),
            (r'%[\w:-]+', Name.Tag, 'tag'),
            (r'!!!' + _dot + r'*\n', Name.Namespace, '#pop'),
            (r'(/)(\[' + _dot + r'*?\])(' + _dot + r'*\n)',
             bygroups(Comment, Comment.Special, Comment),
             '#pop'),
            (r'/' + _dot + r'*\n', _starts_block(Comment, 'html-comment-block'),
             '#pop'),
            (r'-#' + _dot + r'*\n', _starts_block(Comment.Preproc,
                                                  'scaml-comment-block'), '#pop'),
            (r'(-@\s*)(import)?(' + _dot + r'*\n)',
             bygroups(Punctuation, Keyword, using(ScalaLexer)),
             '#pop'),
            (r'(-)(' + _dot + r'*\n)',
             bygroups(Punctuation, using(ScalaLexer)),
             '#pop'),
            (r':' + _dot + r'*\n', _starts_block(Name.Decorator, 'filter-block'),
             '#pop'),
            include('eval-or-plain'),
        ],

        'tag': [
            include('css'),
            (r'\{(,\n|' + _dot + r')*?\}', using(ScalaLexer)),
            (r'\[' + _dot + r'*?\]', using(ScalaLexer)),
            (r'\(', Text, 'html-attributes'),
            (r'/[ \t]*\n', Punctuation, '#pop:2'),
            (r'[<>]{1,2}(?=[ \t=])', Punctuation),
            include('eval-or-plain'),
        ],

        'plain': [
            (r'([^#\n]|#[^{\n]|(\\\\)*\\#\{)+', Text),
            (r'(#\{)(' + _dot + r'*?)(\})',
             bygroups(String.Interpol, using(ScalaLexer), String.Interpol)),
            (r'\n', Text, 'root'),
        ],

        'html-attributes': [
            (r'\s+', Text),
            (r'[\w:-]+[ \t]*=', Name.Attribute, 'html-attribute-value'),
            (r'[\w:-]+', Name.Attribute),
            (r'\)', Text, '#pop'),
        ],

        'html-attribute-value': [
            (r'[ \t]+', Text),
            (r'\w+', Name.Variable, '#pop'),
            (r'@\w+', Name.Variable.Instance, '#pop'),
            (r'\$\w+', Name.Variable.Global, '#pop'),
            (r"'(\\\\|\\[^\\]|[^'\\\n])*'", String, '#pop'),
            (r'"(\\\\|\\[^\\]|[^"\\\n])*"', String, '#pop'),
        ],

        'html-comment-block': [
            (_dot + '+', Comment),
            (r'\n', Text, 'root'),
        ],

        'scaml-comment-block': [
            (_dot + '+', Comment.Preproc),
            (r'\n', Text, 'root'),
        ],

        'filter-block': [
            (r'([^#\n]|#[^{\n]|(\\\\)*\\#\{)+', Name.Decorator),
            (r'(#\{)(' + _dot + r'*?)(\})',
             bygroups(String.Interpol, using(ScalaLexer), String.Interpol)),
            (r'\n', Text, 'root'),
        ],
    }


class PugLexer(ExtendedRegexLexer):
    """
    For Pug markup.
    Pug is a variant of Scaml, see:
    http://scalate.fusesource.org/documentation/scaml-reference.html
    """

    name = 'Pug'
    aliases = ['pug', 'jade']
    filenames = ['*.pug', '*.jade']
    mimetypes = ['text/x-pug', 'text/x-jade']
    url = 'https://pugjs.org'
    version_added = '1.4'

    flags = re.IGNORECASE
    _dot = r'.'

    tokens = {
        'root': [
            (r'[ \t]*\n', Text),
            (r'[ \t]*', _indentation),
        ],

        'css': [
            (r'\.[\w:-]+', Name.Class, 'tag'),
            (r'\#[\w:-]+', Name.Function, 'tag'),
        ],

        'eval-or-plain': [
            (r'[&!]?==', Punctuation, 'plain'),
            (r'([&!]?[=~])(' + _dot + r'*\n)',
             bygroups(Punctuation, using(ScalaLexer)),  'root'),
            default('plain'),
        ],

        'content': [
            include('css'),
            (r'!!!' + _dot + r'*\n', Name.Namespace, '#pop'),
            (r'(/)(\[' + _dot + r'*?\])(' + _dot + r'*\n)',
             bygroups(Comment, Comment.Special, Comment),
             '#pop'),
            (r'/' + _dot + r'*\n', _starts_block(Comment, 'html-comment-block'),
             '#pop'),
            (r'-#' + _dot + r'*\n', _starts_block(Comment.Preproc,
                                                  'scaml-comment-block'), '#pop'),
            (r'(-@\s*)(import)?(' + _dot + r'*\n)',
             bygroups(Punctuation, Keyword, using(ScalaLexer)),
             '#pop'),
            (r'(-)(' + _dot + r'*\n)',
             bygroups(Punctuation, using(ScalaLexer)),
             '#pop'),
            (r':' + _dot + r'*\n', _starts_block(Name.Decorator, 'filter-block'),
             '#pop'),
            (r'[\w:-]+', Name.Tag, 'tag'),
            (r'\|', Text, 'eval-or-plain'),
        ],

        'tag': [
            include('css'),
            (r'\{(,\n|' + _dot + r')*?\}', using(ScalaLexer)),
            (r'\[' + _dot + r'*?\]', using(ScalaLexer)),
            (r'\(', Text, 'html-attributes'),
            (r'/[ \t]*\n', Punctuation, '#pop:2'),
            (r'[<>]{1,2}(?=[ \t=])', Punctuation),
            include('eval-or-plain'),
        ],

        'plain': [
            (r'([^#\n]|#[^{\n]|(\\\\)*\\#\{)+', Text),
            (r'(#\{)(' + _dot + r'*?)(\})',
             bygroups(String.Interpol, using(ScalaLexer), String.Interpol)),
            (r'\n', Text, 'root'),
        ],

        'html-attributes': [
            (r'\s+', Text),
            (r'[\w:-]+[ \t]*=', Name.Attribute, 'html-attribute-value'),
            (r'[\w:-]+', Name.Attribute),
            (r'\)', Text, '#pop'),
        ],

        'html-attribute-value': [
            (r'[ \t]+', Text),
            (r'\w+', Name.Variable, '#pop'),
            (r'@\w+', Name.Variable.Instance, '#pop'),
            (r'\$\w+', Name.Variable.Global, '#pop'),
            (r"'(\\\\|\\[^\\]|[^'\\\n])*'", String, '#pop'),
            (r'"(\\\\|\\[^\\]|[^"\\\n])*"', String, '#pop'),
        ],

        'html-comment-block': [
            (_dot + '+', Comment),
            (r'\n', Text, 'root'),
        ],

        'scaml-comment-block': [
            (_dot + '+', Comment.Preproc),
            (r'\n', Text, 'root'),
        ],

        'filter-block': [
            (r'([^#\n]|#[^{\n]|(\\\\)*\\#\{)+', Name.Decorator),
            (r'(#\{)(' + _dot + r'*?)(\})',
             bygroups(String.Interpol, using(ScalaLexer), String.Interpol)),
            (r'\n', Text, 'root'),
        ],
    }
JadeLexer = PugLexer  # compat


class UrlEncodedLexer(RegexLexer):
    """
    Lexer for urlencoded data
    """

    name = 'urlencoded'
    aliases = ['urlencoded']
    mimetypes = ['application/x-www-form-urlencoded']
    url = 'https://en.wikipedia.org/wiki/Percent-encoding'
    version_added = '2.16'

    tokens = {
        'root': [
            ('([^&=]*)(=)([^=&]*)(&?)', bygroups(Name.Tag, Operator, String, Punctuation)),
        ],
    }
    

class VueLexer(HtmlLexer):
    """
    For Vue Single-File Component.
    """

    name = 'Vue'
    url = 'https://vuejs.org/api/sfc-spec.html'
    aliases = ['vue']
    filenames = ['*.vue']
    mimetypes = []
    version_added = '2.19'

    flags = re.IGNORECASE | re.DOTALL
    tokens = {
        'root': [
            (r'(\{\{)(.*?)(\}\})', bygroups(Comment.Preproc,
             using(JavascriptLexer), Comment.Preproc)),
            ('[^<&{]+', Text),
            inherit,
        ],
        'tag': [
            (r'\s+', Text),
            (r'((?:[@:]|v-)(?:[.\w:-]|\[[^\]]*?\])+\s*)(=)(\s*)',
             bygroups(using(this, state=['name']), Operator, Text),
             'attr-directive'),
            (r'([\w:-]+\s*)(=)(\s*)', bygroups(Name.Attribute, Operator, Text),
             'attr'),
            (r'[\w:-]+', Name.Attribute),
            (r'(/?)(\s*)(>)', bygroups(Punctuation, Text, Punctuation), '#pop'),
        ],
        'name': [
            (r'[\w-]+', Name.Attribute),
            (r'[:@.]', Punctuation),
            (r'(\[)([^\]]*?)(\])', bygroups(Comment.Preproc,
             using(JavascriptLexer), Comment.Preproc)),
        ],
        'attr-directive': [
            (r'(["\'])(.*?)(\1)', bygroups(String,
             using(JavascriptLexer), String), '#pop'),
            (r'[^\s>]+', using(JavascriptLexer), '#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\tornado\test\httputil_test.py ===
from tornado.httputil import (
    url_concat,
    parse_multipart_form_data,
    HTTPHeaders,
    format_timestamp,
    HTTPServerRequest,
    parse_request_start_line,
    parse_cookie,
    qs_to_qsl,
    HTTPInputError,
    HTTPFile,
)
from tornado.escape import utf8, native_str
from tornado.log import gen_log
from tornado.test.util import ignore_deprecation

import copy
import datetime
import logging
import pickle
import time
import urllib.parse
import unittest

from typing import Tuple, Dict, List


def form_data_args() -> Tuple[Dict[str, List[bytes]], Dict[str, List[HTTPFile]]]:
    """Return two empty dicts suitable for use with parse_multipart_form_data.

    mypy insists on type annotations for dict literals, so this lets us avoid
    the verbose types throughout this test.
    """
    return {}, {}


class TestUrlConcat(unittest.TestCase):
    def test_url_concat_no_query_params(self):
        url = url_concat("https://localhost/path", [("y", "y"), ("z", "z")])
        self.assertEqual(url, "https://localhost/path?y=y&z=z")

    def test_url_concat_encode_args(self):
        url = url_concat("https://localhost/path", [("y", "/y"), ("z", "z")])
        self.assertEqual(url, "https://localhost/path?y=%2Fy&z=z")

    def test_url_concat_trailing_q(self):
        url = url_concat("https://localhost/path?", [("y", "y"), ("z", "z")])
        self.assertEqual(url, "https://localhost/path?y=y&z=z")

    def test_url_concat_q_with_no_trailing_amp(self):
        url = url_concat("https://localhost/path?x", [("y", "y"), ("z", "z")])
        self.assertEqual(url, "https://localhost/path?x=&y=y&z=z")

    def test_url_concat_trailing_amp(self):
        url = url_concat("https://localhost/path?x&", [("y", "y"), ("z", "z")])
        self.assertEqual(url, "https://localhost/path?x=&y=y&z=z")

    def test_url_concat_mult_params(self):
        url = url_concat("https://localhost/path?a=1&b=2", [("y", "y"), ("z", "z")])
        self.assertEqual(url, "https://localhost/path?a=1&b=2&y=y&z=z")

    def test_url_concat_no_params(self):
        url = url_concat("https://localhost/path?r=1&t=2", [])
        self.assertEqual(url, "https://localhost/path?r=1&t=2")

    def test_url_concat_none_params(self):
        url = url_concat("https://localhost/path?r=1&t=2", None)
        self.assertEqual(url, "https://localhost/path?r=1&t=2")

    def test_url_concat_with_frag(self):
        url = url_concat("https://localhost/path#tab", [("y", "y")])
        self.assertEqual(url, "https://localhost/path?y=y#tab")

    def test_url_concat_multi_same_params(self):
        url = url_concat("https://localhost/path", [("y", "y1"), ("y", "y2")])
        self.assertEqual(url, "https://localhost/path?y=y1&y=y2")

    def test_url_concat_multi_same_query_params(self):
        url = url_concat("https://localhost/path?r=1&r=2", [("y", "y")])
        self.assertEqual(url, "https://localhost/path?r=1&r=2&y=y")

    def test_url_concat_dict_params(self):
        url = url_concat("https://localhost/path", dict(y="y"))
        self.assertEqual(url, "https://localhost/path?y=y")


class QsParseTest(unittest.TestCase):
    def test_parsing(self):
        qsstring = "a=1&b=2&a=3"
        qs = urllib.parse.parse_qs(qsstring)
        qsl = list(qs_to_qsl(qs))
        self.assertIn(("a", "1"), qsl)
        self.assertIn(("a", "3"), qsl)
        self.assertIn(("b", "2"), qsl)


class MultipartFormDataTest(unittest.TestCase):
    def test_file_upload(self):
        data = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
--1234--""".replace(
            b"\n", b"\r\n"
        )
        args, files = form_data_args()
        parse_multipart_form_data(b"1234", data, args, files)
        file = files["files"][0]
        self.assertEqual(file["filename"], "ab.txt")
        self.assertEqual(file["body"], b"Foo")

    def test_unquoted_names(self):
        # quotes are optional unless special characters are present
        data = b"""\
--1234
Content-Disposition: form-data; name=files; filename=ab.txt

Foo
--1234--""".replace(
            b"\n", b"\r\n"
        )
        args, files = form_data_args()
        parse_multipart_form_data(b"1234", data, args, files)
        file = files["files"][0]
        self.assertEqual(file["filename"], "ab.txt")
        self.assertEqual(file["body"], b"Foo")

    def test_special_filenames(self):
        filenames = [
            "a;b.txt",
            'a"b.txt',
            'a";b.txt',
            'a;"b.txt',
            'a";";.txt',
            'a\\"b.txt',
            "a\\b.txt",
        ]
        for filename in filenames:
            logging.debug("trying filename %r", filename)
            str_data = """\
--1234
Content-Disposition: form-data; name="files"; filename="%s"

Foo
--1234--""" % filename.replace(
                "\\", "\\\\"
            ).replace(
                '"', '\\"'
            )
            data = utf8(str_data.replace("\n", "\r\n"))
            args, files = form_data_args()
            parse_multipart_form_data(b"1234", data, args, files)
            file = files["files"][0]
            self.assertEqual(file["filename"], filename)
            self.assertEqual(file["body"], b"Foo")

    def test_non_ascii_filename_rfc5987(self):
        data = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"; filename*=UTF-8''%C3%A1b.txt

Foo
--1234--""".replace(
            b"\n", b"\r\n"
        )
        args, files = form_data_args()
        parse_multipart_form_data(b"1234", data, args, files)
        file = files["files"][0]
        self.assertEqual(file["filename"], "áb.txt")
        self.assertEqual(file["body"], b"Foo")

    def test_non_ascii_filename_raw(self):
        data = """\
--1234
Content-Disposition: form-data; name="files"; filename="测试.txt"

Foo
--1234--""".encode(
            "utf-8"
        ).replace(
            b"\n", b"\r\n"
        )
        args, files = form_data_args()
        parse_multipart_form_data(b"1234", data, args, files)
        file = files["files"][0]
        self.assertEqual(file["filename"], "测试.txt")
        self.assertEqual(file["body"], b"Foo")

    def test_boundary_starts_and_ends_with_quotes(self):
        data = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
--1234--""".replace(
            b"\n", b"\r\n"
        )
        args, files = form_data_args()
        parse_multipart_form_data(b'"1234"', data, args, files)
        file = files["files"][0]
        self.assertEqual(file["filename"], "ab.txt")
        self.assertEqual(file["body"], b"Foo")

    def test_missing_headers(self):
        data = b"""\
--1234

Foo
--1234--""".replace(
            b"\n", b"\r\n"
        )
        args, files = form_data_args()
        with self.assertRaises(
            HTTPInputError, msg="multipart/form-data missing headers"
        ):
            parse_multipart_form_data(b"1234", data, args, files)
        self.assertEqual(files, {})

    def test_invalid_content_disposition(self):
        data = b"""\
--1234
Content-Disposition: invalid; name="files"; filename="ab.txt"

Foo
--1234--""".replace(
            b"\n", b"\r\n"
        )
        args, files = form_data_args()
        with self.assertRaises(HTTPInputError, msg="Invalid multipart/form-data"):
            parse_multipart_form_data(b"1234", data, args, files)
        self.assertEqual(files, {})

    def test_line_does_not_end_with_correct_line_break(self):
        data = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo--1234--""".replace(
            b"\n", b"\r\n"
        )
        args, files = form_data_args()
        with self.assertRaises(HTTPInputError, msg="Invalid multipart/form-data"):
            parse_multipart_form_data(b"1234", data, args, files)
        self.assertEqual(files, {})

    def test_content_disposition_header_without_name_parameter(self):
        data = b"""\
--1234
Content-Disposition: form-data; filename="ab.txt"

Foo
--1234--""".replace(
            b"\n", b"\r\n"
        )
        args, files = form_data_args()
        with self.assertRaises(
            HTTPInputError, msg="multipart/form-data value missing name"
        ):
            parse_multipart_form_data(b"1234", data, args, files)
        self.assertEqual(files, {})

    def test_data_after_final_boundary(self):
        # The spec requires that data after the final boundary be ignored.
        # http://www.w3.org/Protocols/rfc1341/7_2_Multipart.html
        # In practice, some libraries include an extra CRLF after the boundary.
        data = b"""\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
--1234--
""".replace(
            b"\n", b"\r\n"
        )
        args, files = form_data_args()
        parse_multipart_form_data(b"1234", data, args, files)
        file = files["files"][0]
        self.assertEqual(file["filename"], "ab.txt")
        self.assertEqual(file["body"], b"Foo")


class HTTPHeadersTest(unittest.TestCase):
    def test_multi_line(self):
        # Lines beginning with whitespace are appended to the previous line
        # with any leading whitespace replaced by a single space.
        # Note that while multi-line headers are a part of the HTTP spec,
        # their use is strongly discouraged.
        data = """\
Foo: bar
 baz
Asdf: qwer
\tzxcv
Foo: even
     more
     lines
""".replace(
            "\n", "\r\n"
        )
        headers = HTTPHeaders.parse(data)
        self.assertEqual(headers["asdf"], "qwer zxcv")
        self.assertEqual(headers.get_list("asdf"), ["qwer zxcv"])
        self.assertEqual(headers["Foo"], "bar baz,even more lines")
        self.assertEqual(headers.get_list("foo"), ["bar baz", "even more lines"])
        self.assertEqual(
            sorted(list(headers.get_all())),
            [("Asdf", "qwer zxcv"), ("Foo", "bar baz"), ("Foo", "even more lines")],
        )

    def test_continuation(self):
        data = "Foo: bar\r\n\tasdf"
        headers = HTTPHeaders.parse(data)
        self.assertEqual(headers["Foo"], "bar asdf")

        # If the first line starts with whitespace, it's a
        # continuation line with nothing to continue, so reject it
        # (with a proper error).
        data = " Foo: bar"
        self.assertRaises(HTTPInputError, HTTPHeaders.parse, data)

        # \f (formfeed) is whitespace according to str.isspace, but
        # not according to the HTTP spec.
        data = "Foo: bar\r\n\fasdf"
        self.assertRaises(HTTPInputError, HTTPHeaders.parse, data)

    def test_forbidden_ascii_characters(self):
        # Control characters and ASCII whitespace other than space, tab, and CRLF are not allowed in
        # headers.
        for c in range(0xFF):
            data = f"Foo: bar{chr(c)}baz\r\n"
            if c == 0x09 or (c >= 0x20 and c != 0x7F):
                headers = HTTPHeaders.parse(data)
                self.assertEqual(headers["Foo"], f"bar{chr(c)}baz")
            else:
                self.assertRaises(HTTPInputError, HTTPHeaders.parse, data)

    def test_unicode_newlines(self):
        # Ensure that only \r\n is recognized as a header separator, and not
        # the other newline-like unicode characters.
        # Characters that are likely to be problematic can be found in
        # http://unicode.org/standard/reports/tr13/tr13-5.html
        # and cpython's unicodeobject.c (which defines the implementation
        # of unicode_type.splitlines(), and uses a different list than TR13).
        newlines = [
            # The following ascii characters are sometimes treated as newline-like,
            # but they're disallowed in HTTP headers. This test covers unicode
            # characters that are permitted in headers (under the obs-text rule).
            # "\u001b",  # VERTICAL TAB
            # "\u001c",  # FILE SEPARATOR
            # "\u001d",  # GROUP SEPARATOR
            # "\u001e",  # RECORD SEPARATOR
            "\u0085",  # NEXT LINE
            "\u2028",  # LINE SEPARATOR
            "\u2029",  # PARAGRAPH SEPARATOR
        ]
        for newline in newlines:
            # Try the utf8 and latin1 representations of each newline
            for encoding in ["utf8", "latin1"]:
                try:
                    try:
                        encoded = newline.encode(encoding)
                    except UnicodeEncodeError:
                        # Some chars cannot be represented in latin1
                        continue
                    data = b"Cookie: foo=" + encoded + b"bar"
                    # parse() wants a native_str, so decode through latin1
                    # in the same way the real parser does.
                    headers = HTTPHeaders.parse(native_str(data.decode("latin1")))
                    expected = [
                        (
                            "Cookie",
                            "foo=" + native_str(encoded.decode("latin1")) + "bar",
                        )
                    ]
                    self.assertEqual(expected, list(headers.get_all()))
                except Exception:
                    gen_log.warning("failed while trying %r in %s", newline, encoding)
                    raise

    def test_unicode_whitespace(self):
        # Only tabs and spaces are to be stripped according to the HTTP standard.
        # Other unicode whitespace is to be left as-is. In the context of headers,
        # this specifically means the whitespace characters falling within the
        # latin1 charset.
        whitespace = [
            (" ", True),  # SPACE
            ("\t", True),  # TAB
            ("\u00a0", False),  # NON-BREAKING SPACE
            ("\u0085", False),  # NEXT LINE
        ]
        for c, stripped in whitespace:
            headers = HTTPHeaders.parse("Transfer-Encoding: %schunked" % c)
            if stripped:
                expected = [("Transfer-Encoding", "chunked")]
            else:
                expected = [("Transfer-Encoding", "%schunked" % c)]
            self.assertEqual(expected, list(headers.get_all()))

    def test_optional_cr(self):
        # Bare CR is  not a valid line separator
        with self.assertRaises(HTTPInputError):
            HTTPHeaders.parse("CRLF: crlf\r\nLF: lf\nCR: cr\rMore: more\r\n")

        # Both CRLF and LF should be accepted as separators. CR should not be
        # part of the data when followed by LF.
        headers = HTTPHeaders.parse("CRLF: crlf\r\nLF: lf\nMore: more\r\n")
        self.assertEqual(
            sorted(headers.get_all()),
            [("Crlf", "crlf"), ("Lf", "lf"), ("More", "more")],
        )

    def test_copy(self):
        all_pairs = [("A", "1"), ("A", "2"), ("B", "c")]
        h1 = HTTPHeaders()
        for k, v in all_pairs:
            h1.add(k, v)
        h2 = h1.copy()
        h3 = copy.copy(h1)
        h4 = copy.deepcopy(h1)
        for headers in [h1, h2, h3, h4]:
            # All the copies are identical, no matter how they were
            # constructed.
            self.assertEqual(list(sorted(headers.get_all())), all_pairs)
        for headers in [h2, h3, h4]:
            # Neither the dict or its member lists are reused.
            self.assertIsNot(headers, h1)
            self.assertIsNot(headers.get_list("A"), h1.get_list("A"))

    def test_pickle_roundtrip(self):
        headers = HTTPHeaders()
        headers.add("Set-Cookie", "a=b")
        headers.add("Set-Cookie", "c=d")
        headers.add("Content-Type", "text/html")
        pickled = pickle.dumps(headers)
        unpickled = pickle.loads(pickled)
        self.assertEqual(sorted(headers.get_all()), sorted(unpickled.get_all()))
        self.assertEqual(sorted(headers.items()), sorted(unpickled.items()))

    def test_setdefault(self):
        headers = HTTPHeaders()
        headers["foo"] = "bar"
        # If a value is present, setdefault returns it without changes.
        self.assertEqual(headers.setdefault("foo", "baz"), "bar")
        self.assertEqual(headers["foo"], "bar")
        # If a value is not present, setdefault sets it for future use.
        self.assertEqual(headers.setdefault("quux", "xyzzy"), "xyzzy")
        self.assertEqual(headers["quux"], "xyzzy")
        self.assertEqual(sorted(headers.get_all()), [("Foo", "bar"), ("Quux", "xyzzy")])

    def test_string(self):
        headers = HTTPHeaders()
        headers.add("Foo", "1")
        headers.add("Foo", "2")
        headers.add("Foo", "3")
        headers2 = HTTPHeaders.parse(str(headers))
        self.assertEqual(headers, headers2)

    def test_invalid_header_names(self):
        invalid_names = [
            "",
            "foo bar",
            "foo\tbar",
            "foo\nbar",
            "foo\x00bar",
            "foo ",
            " foo",
            "é",
        ]
        for name in invalid_names:
            headers = HTTPHeaders()
            with self.assertRaises(HTTPInputError):
                headers.add(name, "bar")


class FormatTimestampTest(unittest.TestCase):
    # Make sure that all the input types are supported.
    TIMESTAMP = 1359312200.503611
    EXPECTED = "Sun, 27 Jan 2013 18:43:20 GMT"

    def check(self, value):
        self.assertEqual(format_timestamp(value), self.EXPECTED)

    def test_unix_time_float(self):
        self.check(self.TIMESTAMP)

    def test_unix_time_int(self):
        self.check(int(self.TIMESTAMP))

    def test_struct_time(self):
        self.check(time.gmtime(self.TIMESTAMP))

    def test_time_tuple(self):
        tup = tuple(time.gmtime(self.TIMESTAMP))
        self.assertEqual(9, len(tup))
        self.check(tup)

    def test_utc_naive_datetime(self):
        self.check(
            datetime.datetime.fromtimestamp(
                self.TIMESTAMP, datetime.timezone.utc
            ).replace(tzinfo=None)
        )

    def test_utc_naive_datetime_deprecated(self):
        with ignore_deprecation():
            self.check(datetime.datetime.utcfromtimestamp(self.TIMESTAMP))

    def test_utc_aware_datetime(self):
        self.check(
            datetime.datetime.fromtimestamp(self.TIMESTAMP, datetime.timezone.utc)
        )

    def test_other_aware_datetime(self):
        # Other timezones are ignored; the timezone is always printed as GMT
        self.check(
            datetime.datetime.fromtimestamp(
                self.TIMESTAMP, datetime.timezone(datetime.timedelta(hours=-4))
            )
        )


# HTTPServerRequest is mainly tested incidentally to the server itself,
# but this tests the parts of the class that can be tested in isolation.
class HTTPServerRequestTest(unittest.TestCase):
    def test_default_constructor(self):
        # All parameters are formally optional, but uri is required
        # (and has been for some time).  This test ensures that no
        # more required parameters slip in.
        HTTPServerRequest(uri="/")

    def test_body_is_a_byte_string(self):
        request = HTTPServerRequest(uri="/")
        self.assertIsInstance(request.body, bytes)

    def test_repr_does_not_contain_headers(self):
        request = HTTPServerRequest(
            uri="/", headers=HTTPHeaders({"Canary": ["Coal Mine"]})
        )
        self.assertNotIn("Canary", repr(request))


class ParseRequestStartLineTest(unittest.TestCase):
    METHOD = "GET"
    PATH = "/foo"
    VERSION = "HTTP/1.1"

    def test_parse_request_start_line(self):
        start_line = " ".join([self.METHOD, self.PATH, self.VERSION])
        parsed_start_line = parse_request_start_line(start_line)
        self.assertEqual(parsed_start_line.method, self.METHOD)
        self.assertEqual(parsed_start_line.path, self.PATH)
        self.assertEqual(parsed_start_line.version, self.VERSION)


class ParseCookieTest(unittest.TestCase):
    # These tests copied from Django:
    # https://github.com/django/django/pull/6277/commits/da810901ada1cae9fc1f018f879f11a7fb467b28
    def test_python_cookies(self):
        """
        Test cases copied from Python's Lib/test/test_http_cookies.py
        """
        self.assertEqual(
            parse_cookie("chips=ahoy; vienna=finger"),
            {"chips": "ahoy", "vienna": "finger"},
        )
        # Here parse_cookie() differs from Python's cookie parsing in that it
        # treats all semicolons as delimiters, even within quotes.
        self.assertEqual(
            parse_cookie('keebler="E=mc2; L=\\"Loves\\"; fudge=\\012;"'),
            {"keebler": '"E=mc2', "L": '\\"Loves\\"', "fudge": "\\012", "": '"'},
        )
        # Illegal cookies that have an '=' char in an unquoted value.
        self.assertEqual(parse_cookie("keebler=E=mc2"), {"keebler": "E=mc2"})
        # Cookies with ':' character in their name.
        self.assertEqual(
            parse_cookie("key:term=value:term"), {"key:term": "value:term"}
        )
        # Cookies with '[' and ']'.
        self.assertEqual(
            parse_cookie("a=b; c=[; d=r; f=h"), {"a": "b", "c": "[", "d": "r", "f": "h"}
        )

    def test_cookie_edgecases(self):
        # Cookies that RFC6265 allows.
        self.assertEqual(
            parse_cookie("a=b; Domain=example.com"), {"a": "b", "Domain": "example.com"}
        )
        # parse_cookie() has historically kept only the last cookie with the
        # same name.
        self.assertEqual(parse_cookie("a=b; h=i; a=c"), {"a": "c", "h": "i"})

    def test_invalid_cookies(self):
        """
        Cookie strings that go against RFC6265 but browsers will send if set
        via document.cookie.
        """
        # Chunks without an equals sign appear as unnamed values per
        # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
        self.assertIn(
            "django_language",
            parse_cookie("abc=def; unnamed; django_language=en").keys(),
        )
        # Even a double quote may be an unamed value.
        self.assertEqual(parse_cookie('a=b; "; c=d'), {"a": "b", "": '"', "c": "d"})
        # Spaces in names and values, and an equals sign in values.
        self.assertEqual(
            parse_cookie("a b c=d e = f; gh=i"), {"a b c": "d e = f", "gh": "i"}
        )
        # More characters the spec forbids.
        self.assertEqual(
            parse_cookie('a   b,c<>@:/[]?{}=d  "  =e,f g'),
            {"a   b,c<>@:/[]?{}": 'd  "  =e,f g'},
        )
        # Unicode characters. The spec only allows ASCII.
        self.assertEqual(
            parse_cookie("saint=André Bessette"),
            {"saint": native_str("André Bessette")},
        )
        # Browsers don't send extra whitespace or semicolons in Cookie headers,
        # but parse_cookie() should parse whitespace the same way
        # document.cookie parses whitespace.
        self.assertEqual(
            parse_cookie("  =  b  ;  ;  =  ;   c  =  ;  "), {"": "b", "c": ""}
        )

    def test_unquote(self):
        # Copied from
        # https://github.com/python/cpython/blob/dc7a2b6522ec7af41282bc34f405bee9b306d611/Lib/test/test_http_cookies.py#L62
        cases = [
            (r'a="b=\""', 'b="'),
            (r'a="b=\\"', "b=\\"),
            (r'a="b=\="', "b=="),
            (r'a="b=\n"', "b=n"),
            (r'a="b=\042"', 'b="'),
            (r'a="b=\134"', "b=\\"),
            (r'a="b=\377"', "b=\xff"),
            (r'a="b=\400"', "b=400"),
            (r'a="b=\42"', "b=42"),
            (r'a="b=\\042"', "b=\\042"),
            (r'a="b=\\134"', "b=\\134"),
            (r'a="b=\\\""', 'b=\\"'),
            (r'a="b=\\\042"', 'b=\\"'),
            (r'a="b=\134\""', 'b=\\"'),
            (r'a="b=\134\042"', 'b=\\"'),
        ]
        for encoded, decoded in cases:
            with self.subTest(encoded):
                c = parse_cookie(encoded)
                self.assertEqual(c["a"], decoded)

    def test_unquote_large(self):
        # Adapted from
        # https://github.com/python/cpython/blob/dc7a2b6522ec7af41282bc34f405bee9b306d611/Lib/test/test_http_cookies.py#L87
        # Modified from that test because we handle semicolons differently from the stdlib.
        #
        # This is a performance regression test: prior to improvements in Tornado 6.4.2, this test
        # would take over a minute with n= 100k. Now it runs in tens of milliseconds.
        n = 100000
        for encoded in r"\\", r"\134":
            with self.subTest(encoded):
                start = time.time()
                data = 'a="b=' + encoded * n + '"'
                value = parse_cookie(data)["a"]
                end = time.time()
                self.assertEqual(value[:3], "b=\\")
                self.assertEqual(value[-3:], "\\\\\\")
                self.assertEqual(len(value), n + 2)

                # Very loose performance check to avoid false positives
                self.assertLess(end - start, 1, "Test took too long")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\cmdline.py ===
"""
    pygments.cmdline
    ~~~~~~~~~~~~~~~~

    Command line interface.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import os
import sys
import shutil
import argparse
from textwrap import dedent

from pip._vendor.pygments import __version__, highlight
from pip._vendor.pygments.util import ClassNotFound, OptionError, docstring_headline, \
    guess_decode, guess_decode_from_terminal, terminal_encoding, \
    UnclosingTextIOWrapper
from pip._vendor.pygments.lexers import get_all_lexers, get_lexer_by_name, guess_lexer, \
    load_lexer_from_file, get_lexer_for_filename, find_lexer_class_for_filename
from pip._vendor.pygments.lexers.special import TextLexer
from pip._vendor.pygments.formatters.latex import LatexEmbeddedLexer, LatexFormatter
from pip._vendor.pygments.formatters import get_all_formatters, get_formatter_by_name, \
    load_formatter_from_file, get_formatter_for_filename, find_formatter_class
from pip._vendor.pygments.formatters.terminal import TerminalFormatter
from pip._vendor.pygments.formatters.terminal256 import Terminal256Formatter, TerminalTrueColorFormatter
from pip._vendor.pygments.filters import get_all_filters, find_filter_class
from pip._vendor.pygments.styles import get_all_styles, get_style_by_name


def _parse_options(o_strs):
    opts = {}
    if not o_strs:
        return opts
    for o_str in o_strs:
        if not o_str.strip():
            continue
        o_args = o_str.split(',')
        for o_arg in o_args:
            o_arg = o_arg.strip()
            try:
                o_key, o_val = o_arg.split('=', 1)
                o_key = o_key.strip()
                o_val = o_val.strip()
            except ValueError:
                opts[o_arg] = True
            else:
                opts[o_key] = o_val
    return opts


def _parse_filters(f_strs):
    filters = []
    if not f_strs:
        return filters
    for f_str in f_strs:
        if ':' in f_str:
            fname, fopts = f_str.split(':', 1)
            filters.append((fname, _parse_options([fopts])))
        else:
            filters.append((f_str, {}))
    return filters


def _print_help(what, name):
    try:
        if what == 'lexer':
            cls = get_lexer_by_name(name)
            print(f"Help on the {cls.name} lexer:")
            print(dedent(cls.__doc__))
        elif what == 'formatter':
            cls = find_formatter_class(name)
            print(f"Help on the {cls.name} formatter:")
            print(dedent(cls.__doc__))
        elif what == 'filter':
            cls = find_filter_class(name)
            print(f"Help on the {name} filter:")
            print(dedent(cls.__doc__))
        return 0
    except (AttributeError, ValueError):
        print(f"{what} not found!", file=sys.stderr)
        return 1


def _print_list(what):
    if what == 'lexer':
        print()
        print("Lexers:")
        print("~~~~~~~")

        info = []
        for fullname, names, exts, _ in get_all_lexers():
            tup = (', '.join(names)+':', fullname,
                   exts and '(filenames ' + ', '.join(exts) + ')' or '')
            info.append(tup)
        info.sort()
        for i in info:
            print(('* {}\n    {} {}').format(*i))

    elif what == 'formatter':
        print()
        print("Formatters:")
        print("~~~~~~~~~~~")

        info = []
        for cls in get_all_formatters():
            doc = docstring_headline(cls)
            tup = (', '.join(cls.aliases) + ':', doc, cls.filenames and
                   '(filenames ' + ', '.join(cls.filenames) + ')' or '')
            info.append(tup)
        info.sort()
        for i in info:
            print(('* {}\n    {} {}').format(*i))

    elif what == 'filter':
        print()
        print("Filters:")
        print("~~~~~~~~")

        for name in get_all_filters():
            cls = find_filter_class(name)
            print("* " + name + ':')
            print(f"    {docstring_headline(cls)}")

    elif what == 'style':
        print()
        print("Styles:")
        print("~~~~~~~")

        for name in get_all_styles():
            cls = get_style_by_name(name)
            print("* " + name + ':')
            print(f"    {docstring_headline(cls)}")


def _print_list_as_json(requested_items):
    import json
    result = {}
    if 'lexer' in requested_items:
        info = {}
        for fullname, names, filenames, mimetypes in get_all_lexers():
            info[fullname] = {
                'aliases': names,
                'filenames': filenames,
                'mimetypes': mimetypes
            }
        result['lexers'] = info

    if 'formatter' in requested_items:
        info = {}
        for cls in get_all_formatters():
            doc = docstring_headline(cls)
            info[cls.name] = {
                'aliases': cls.aliases,
                'filenames': cls.filenames,
                'doc': doc
            }
        result['formatters'] = info

    if 'filter' in requested_items:
        info = {}
        for name in get_all_filters():
            cls = find_filter_class(name)
            info[name] = {
                'doc': docstring_headline(cls)
            }
        result['filters'] = info

    if 'style' in requested_items:
        info = {}
        for name in get_all_styles():
            cls = get_style_by_name(name)
            info[name] = {
                'doc': docstring_headline(cls)
            }
        result['styles'] = info

    json.dump(result, sys.stdout)

def main_inner(parser, argns):
    if argns.help:
        parser.print_help()
        return 0

    if argns.V:
        print(f'Pygments version {__version__}, (c) 2006-2024 by Georg Brandl, Matthäus '
              'Chajdas and contributors.')
        return 0

    def is_only_option(opt):
        return not any(v for (k, v) in vars(argns).items() if k != opt)

    # handle ``pygmentize -L``
    if argns.L is not None:
        arg_set = set()
        for k, v in vars(argns).items():
            if v:
                arg_set.add(k)

        arg_set.discard('L')
        arg_set.discard('json')

        if arg_set:
            parser.print_help(sys.stderr)
            return 2

        # print version
        if not argns.json:
            main(['', '-V'])
        allowed_types = {'lexer', 'formatter', 'filter', 'style'}
        largs = [arg.rstrip('s') for arg in argns.L]
        if any(arg not in allowed_types for arg in largs):
            parser.print_help(sys.stderr)
            return 0
        if not largs:
            largs = allowed_types
        if not argns.json:
            for arg in largs:
                _print_list(arg)
        else:
            _print_list_as_json(largs)
        return 0

    # handle ``pygmentize -H``
    if argns.H:
        if not is_only_option('H'):
            parser.print_help(sys.stderr)
            return 2
        what, name = argns.H
        if what not in ('lexer', 'formatter', 'filter'):
            parser.print_help(sys.stderr)
            return 2
        return _print_help(what, name)

    # parse -O options
    parsed_opts = _parse_options(argns.O or [])

    # parse -P options
    for p_opt in argns.P or []:
        try:
            name, value = p_opt.split('=', 1)
        except ValueError:
            parsed_opts[p_opt] = True
        else:
            parsed_opts[name] = value

    # encodings
    inencoding = parsed_opts.get('inencoding', parsed_opts.get('encoding'))
    outencoding = parsed_opts.get('outencoding', parsed_opts.get('encoding'))

    # handle ``pygmentize -N``
    if argns.N:
        lexer = find_lexer_class_for_filename(argns.N)
        if lexer is None:
            lexer = TextLexer

        print(lexer.aliases[0])
        return 0

    # handle ``pygmentize -C``
    if argns.C:
        inp = sys.stdin.buffer.read()
        try:
            lexer = guess_lexer(inp, inencoding=inencoding)
        except ClassNotFound:
            lexer = TextLexer

        print(lexer.aliases[0])
        return 0

    # handle ``pygmentize -S``
    S_opt = argns.S
    a_opt = argns.a
    if S_opt is not None:
        f_opt = argns.f
        if not f_opt:
            parser.print_help(sys.stderr)
            return 2
        if argns.l or argns.INPUTFILE:
            parser.print_help(sys.stderr)
            return 2

        try:
            parsed_opts['style'] = S_opt
            fmter = get_formatter_by_name(f_opt, **parsed_opts)
        except ClassNotFound as err:
            print(err, file=sys.stderr)
            return 1

        print(fmter.get_style_defs(a_opt or ''))
        return 0

    # if no -S is given, -a is not allowed
    if argns.a is not None:
        parser.print_help(sys.stderr)
        return 2

    # parse -F options
    F_opts = _parse_filters(argns.F or [])

    # -x: allow custom (eXternal) lexers and formatters
    allow_custom_lexer_formatter = bool(argns.x)

    # select lexer
    lexer = None

    # given by name?
    lexername = argns.l
    if lexername:
        # custom lexer, located relative to user's cwd
        if allow_custom_lexer_formatter and '.py' in lexername:
            try:
                filename = None
                name = None
                if ':' in lexername:
                    filename, name = lexername.rsplit(':', 1)

                    if '.py' in name:
                        # This can happen on Windows: If the lexername is
                        # C:\lexer.py -- return to normal load path in that case
                        name = None

                if filename and name:
                    lexer = load_lexer_from_file(filename, name,
                                                 **parsed_opts)
                else:
                    lexer = load_lexer_from_file(lexername, **parsed_opts)
            except ClassNotFound as err:
                print('Error:', err, file=sys.stderr)
                return 1
        else:
            try:
                lexer = get_lexer_by_name(lexername, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1

    # read input code
    code = None

    if argns.INPUTFILE:
        if argns.s:
            print('Error: -s option not usable when input file specified',
                  file=sys.stderr)
            return 2

        infn = argns.INPUTFILE
        try:
            with open(infn, 'rb') as infp:
                code = infp.read()
        except Exception as err:
            print('Error: cannot read infile:', err, file=sys.stderr)
            return 1
        if not inencoding:
            code, inencoding = guess_decode(code)

        # do we have to guess the lexer?
        if not lexer:
            try:
                lexer = get_lexer_for_filename(infn, code, **parsed_opts)
            except ClassNotFound as err:
                if argns.g:
                    try:
                        lexer = guess_lexer(code, **parsed_opts)
                    except ClassNotFound:
                        lexer = TextLexer(**parsed_opts)
                else:
                    print('Error:', err, file=sys.stderr)
                    return 1
            except OptionError as err:
                print('Error:', err, file=sys.stderr)
                return 1

    elif not argns.s:  # treat stdin as full file (-s support is later)
        # read code from terminal, always in binary mode since we want to
        # decode ourselves and be tolerant with it
        code = sys.stdin.buffer.read()  # use .buffer to get a binary stream
        if not inencoding:
            code, inencoding = guess_decode_from_terminal(code, sys.stdin)
            # else the lexer will do the decoding
        if not lexer:
            try:
                lexer = guess_lexer(code, **parsed_opts)
            except ClassNotFound:
                lexer = TextLexer(**parsed_opts)

    else:  # -s option needs a lexer with -l
        if not lexer:
            print('Error: when using -s a lexer has to be selected with -l',
                  file=sys.stderr)
            return 2

    # process filters
    for fname, fopts in F_opts:
        try:
            lexer.add_filter(fname, **fopts)
        except ClassNotFound as err:
            print('Error:', err, file=sys.stderr)
            return 1

    # select formatter
    outfn = argns.o
    fmter = argns.f
    if fmter:
        # custom formatter, located relative to user's cwd
        if allow_custom_lexer_formatter and '.py' in fmter:
            try:
                filename = None
                name = None
                if ':' in fmter:
                    # Same logic as above for custom lexer
                    filename, name = fmter.rsplit(':', 1)

                    if '.py' in name:
                        name = None

                if filename and name:
                    fmter = load_formatter_from_file(filename, name,
                                                     **parsed_opts)
                else:
                    fmter = load_formatter_from_file(fmter, **parsed_opts)
            except ClassNotFound as err:
                print('Error:', err, file=sys.stderr)
                return 1
        else:
            try:
                fmter = get_formatter_by_name(fmter, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1

    if outfn:
        if not fmter:
            try:
                fmter = get_formatter_for_filename(outfn, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1
        try:
            outfile = open(outfn, 'wb')
        except Exception as err:
            print('Error: cannot open outfile:', err, file=sys.stderr)
            return 1
    else:
        if not fmter:
            if os.environ.get('COLORTERM','') in ('truecolor', '24bit'):
                fmter = TerminalTrueColorFormatter(**parsed_opts)
            elif '256' in os.environ.get('TERM', ''):
                fmter = Terminal256Formatter(**parsed_opts)
            else:
                fmter = TerminalFormatter(**parsed_opts)
        outfile = sys.stdout.buffer

    # determine output encoding if not explicitly selected
    if not outencoding:
        if outfn:
            # output file? use lexer encoding for now (can still be None)
            fmter.encoding = inencoding
        else:
            # else use terminal encoding
            fmter.encoding = terminal_encoding(sys.stdout)

    # provide coloring under Windows, if possible
    if not outfn and sys.platform in ('win32', 'cygwin') and \
       fmter.name in ('Terminal', 'Terminal256'):  # pragma: no cover
        # unfortunately colorama doesn't support binary streams on Py3
        outfile = UnclosingTextIOWrapper(outfile, encoding=fmter.encoding)
        fmter.encoding = None
        try:
            import colorama.initialise
        except ImportError:
            pass
        else:
            outfile = colorama.initialise.wrap_stream(
                outfile, convert=None, strip=None, autoreset=False, wrap=True)

    # When using the LaTeX formatter and the option `escapeinside` is
    # specified, we need a special lexer which collects escaped text
    # before running the chosen language lexer.
    escapeinside = parsed_opts.get('escapeinside', '')
    if len(escapeinside) == 2 and isinstance(fmter, LatexFormatter):
        left = escapeinside[0]
        right = escapeinside[1]
        lexer = LatexEmbeddedLexer(left, right, lexer)

    # ... and do it!
    if not argns.s:
        # process whole input as per normal...
        try:
            highlight(code, lexer, fmter, outfile)
        finally:
            if outfn:
                outfile.close()
        return 0
    else:
        # line by line processing of stdin (eg: for 'tail -f')...
        try:
            while 1:
                line = sys.stdin.buffer.readline()
                if not line:
                    break
                if not inencoding:
                    line = guess_decode_from_terminal(line, sys.stdin)[0]
                highlight(line, lexer, fmter, outfile)
                if hasattr(outfile, 'flush'):
                    outfile.flush()
            return 0
        except KeyboardInterrupt:  # pragma: no cover
            return 0
        finally:
            if outfn:
                outfile.close()


class HelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog, indent_increment=2, max_help_position=16, width=None):
        if width is None:
            try:
                width = shutil.get_terminal_size().columns - 2
            except Exception:
                pass
        argparse.HelpFormatter.__init__(self, prog, indent_increment,
                                        max_help_position, width)


def main(args=sys.argv):
    """
    Main command line entry point.
    """
    desc = "Highlight an input file and write the result to an output file."
    parser = argparse.ArgumentParser(description=desc, add_help=False,
                                     formatter_class=HelpFormatter)

    operation = parser.add_argument_group('Main operation')
    lexersel = operation.add_mutually_exclusive_group()
    lexersel.add_argument(
        '-l', metavar='LEXER',
        help='Specify the lexer to use.  (Query names with -L.)  If not '
        'given and -g is not present, the lexer is guessed from the filename.')
    lexersel.add_argument(
        '-g', action='store_true',
        help='Guess the lexer from the file contents, or pass through '
        'as plain text if nothing can be guessed.')
    operation.add_argument(
        '-F', metavar='FILTER[:options]', action='append',
        help='Add a filter to the token stream.  (Query names with -L.) '
        'Filter options are given after a colon if necessary.')
    operation.add_argument(
        '-f', metavar='FORMATTER',
        help='Specify the formatter to use.  (Query names with -L.) '
        'If not given, the formatter is guessed from the output filename, '
        'and defaults to the terminal formatter if the output is to the '
        'terminal or an unknown file extension.')
    operation.add_argument(
        '-O', metavar='OPTION=value[,OPTION=value,...]', action='append',
        help='Give options to the lexer and formatter as a comma-separated '
        'list of key-value pairs. '
        'Example: `-O bg=light,python=cool`.')
    operation.add_argument(
        '-P', metavar='OPTION=value', action='append',
        help='Give a single option to the lexer and formatter - with this '
        'you can pass options whose value contains commas and equal signs. '
        'Example: `-P "heading=Pygments, the Python highlighter"`.')
    operation.add_argument(
        '-o', metavar='OUTPUTFILE',
        help='Where to write the output.  Defaults to standard output.')

    operation.add_argument(
        'INPUTFILE', nargs='?',
        help='Where to read the input.  Defaults to standard input.')

    flags = parser.add_argument_group('Operation flags')
    flags.add_argument(
        '-v', action='store_true',
        help='Print a detailed traceback on unhandled exceptions, which '
        'is useful for debugging and bug reports.')
    flags.add_argument(
        '-s', action='store_true',
        help='Process lines one at a time until EOF, rather than waiting to '
        'process the entire file.  This only works for stdin, only for lexers '
        'with no line-spanning constructs, and is intended for streaming '
        'input such as you get from `tail -f`. '
        'Example usage: `tail -f sql.log | pygmentize -s -l sql`.')
    flags.add_argument(
        '-x', action='store_true',
        help='Allow custom lexers and formatters to be loaded from a .py file '
        'relative to the current working directory. For example, '
        '`-l ./customlexer.py -x`. By default, this option expects a file '
        'with a class named CustomLexer or CustomFormatter; you can also '
        'specify your own class name with a colon (`-l ./lexer.py:MyLexer`). '
        'Users should be very careful not to use this option with untrusted '
        'files, because it will import and run them.')
    flags.add_argument('--json', help='Output as JSON. This can '
        'be only used in conjunction with -L.',
        default=False,
        action='store_true')

    special_modes_group = parser.add_argument_group(
        'Special modes - do not do any highlighting')
    special_modes = special_modes_group.add_mutually_exclusive_group()
    special_modes.add_argument(
        '-S', metavar='STYLE -f formatter',
        help='Print style definitions for STYLE for a formatter '
        'given with -f. The argument given by -a is formatter '
        'dependent.')
    special_modes.add_argument(
        '-L', nargs='*', metavar='WHAT',
        help='List lexers, formatters, styles or filters -- '
        'give additional arguments for the thing(s) you want to list '
        '(e.g. "styles"), or omit them to list everything.')
    special_modes.add_argument(
        '-N', metavar='FILENAME',
        help='Guess and print out a lexer name based solely on the given '
        'filename. Does not take input or highlight anything. If no specific '
        'lexer can be determined, "text" is printed.')
    special_modes.add_argument(
        '-C', action='store_true',
        help='Like -N, but print out a lexer name based solely on '
        'a given content from standard input.')
    special_modes.add_argument(
        '-H', action='store', nargs=2, metavar=('NAME', 'TYPE'),
        help='Print detailed help for the object <name> of type <type>, '
        'where <type> is one of "lexer", "formatter" or "filter".')
    special_modes.add_argument(
        '-V', action='store_true',
        help='Print the package version.')
    special_modes.add_argument(
        '-h', '--help', action='store_true',
        help='Print this help.')
    special_modes_group.add_argument(
        '-a', metavar='ARG',
        help='Formatter-specific additional argument for the -S (print '
        'style sheet) mode.')

    argns = parser.parse_args(args[1:])

    try:
        return main_inner(parser, argns)
    except BrokenPipeError:
        # someone closed our stdout, e.g. by quitting a pager.
        return 0
    except Exception:
        if argns.v:
            print(file=sys.stderr)
            print('*' * 65, file=sys.stderr)
            print('An unhandled exception occurred while highlighting.',
                  file=sys.stderr)
            print('Please report the whole traceback to the issue tracker at',
                  file=sys.stderr)
            print('<https://github.com/pygments/pygments/issues>.',
                  file=sys.stderr)
            print('*' * 65, file=sys.stderr)
            print(file=sys.stderr)
            raise
        import traceback
        info = traceback.format_exception(*sys.exc_info())
        msg = info[-1].strip()
        if len(info) >= 3:
            # extract relevant file and position info
            msg += '\n   (f{})'.format(info[-2].split('\n')[0].strip()[1:])
        print(file=sys.stderr)
        print('*** Error while highlighting:', file=sys.stderr)
        print(msg, file=sys.stderr)
        print('*** If this is a bug you want to report, please rerun with -v.',
              file=sys.stderr)
        return 1

# === NexusCore/openenv\Lib\site-packages\charset_normalizer\api.py ===
from __future__ import annotations

import logging
from os import PathLike
from typing import BinaryIO

from .cd import (
    coherence_ratio,
    encoding_languages,
    mb_encoding_languages,
    merge_coherence_ratios,
)
from .constant import IANA_SUPPORTED, TOO_BIG_SEQUENCE, TOO_SMALL_SEQUENCE, TRACE
from .md import mess_ratio
from .models import CharsetMatch, CharsetMatches
from .utils import (
    any_specified_encoding,
    cut_sequence_chunks,
    iana_name,
    identify_sig_or_bom,
    is_cp_similar,
    is_multi_byte_encoding,
    should_strip_sig_or_bom,
)

logger = logging.getLogger("charset_normalizer")
explain_handler = logging.StreamHandler()
explain_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
)


def from_bytes(
    sequences: bytes | bytearray,
    steps: int = 5,
    chunk_size: int = 512,
    threshold: float = 0.2,
    cp_isolation: list[str] | None = None,
    cp_exclusion: list[str] | None = None,
    preemptive_behaviour: bool = True,
    explain: bool = False,
    language_threshold: float = 0.1,
    enable_fallback: bool = True,
) -> CharsetMatches:
    """
    Given a raw bytes sequence, return the best possibles charset usable to render str objects.
    If there is no results, it is a strong indicator that the source is binary/not text.
    By default, the process will extract 5 blocks of 512o each to assess the mess and coherence of a given sequence.
    And will give up a particular code page after 20% of measured mess. Those criteria are customizable at will.

    The preemptive behavior DOES NOT replace the traditional detection workflow, it prioritize a particular code page
    but never take it for granted. Can improve the performance.

    You may want to focus your attention to some code page or/and not others, use cp_isolation and cp_exclusion for that
    purpose.

    This function will strip the SIG in the payload/sequence every time except on UTF-16, UTF-32.
    By default the library does not setup any handler other than the NullHandler, if you choose to set the 'explain'
    toggle to True it will alter the logger configuration to add a StreamHandler that is suitable for debugging.
    Custom logging format and handler can be set manually.
    """

    if not isinstance(sequences, (bytearray, bytes)):
        raise TypeError(
            "Expected object of type bytes or bytearray, got: {}".format(
                type(sequences)
            )
        )

    if explain:
        previous_logger_level: int = logger.level
        logger.addHandler(explain_handler)
        logger.setLevel(TRACE)

    length: int = len(sequences)

    if length == 0:
        logger.debug("Encoding detection on empty bytes, assuming utf_8 intention.")
        if explain:  # Defensive: ensure exit path clean handler
            logger.removeHandler(explain_handler)
            logger.setLevel(previous_logger_level or logging.WARNING)
        return CharsetMatches([CharsetMatch(sequences, "utf_8", 0.0, False, [], "")])

    if cp_isolation is not None:
        logger.log(
            TRACE,
            "cp_isolation is set. use this flag for debugging purpose. "
            "limited list of encoding allowed : %s.",
            ", ".join(cp_isolation),
        )
        cp_isolation = [iana_name(cp, False) for cp in cp_isolation]
    else:
        cp_isolation = []

    if cp_exclusion is not None:
        logger.log(
            TRACE,
            "cp_exclusion is set. use this flag for debugging purpose. "
            "limited list of encoding excluded : %s.",
            ", ".join(cp_exclusion),
        )
        cp_exclusion = [iana_name(cp, False) for cp in cp_exclusion]
    else:
        cp_exclusion = []

    if length <= (chunk_size * steps):
        logger.log(
            TRACE,
            "override steps (%i) and chunk_size (%i) as content does not fit (%i byte(s) given) parameters.",
            steps,
            chunk_size,
            length,
        )
        steps = 1
        chunk_size = length

    if steps > 1 and length / steps < chunk_size:
        chunk_size = int(length / steps)

    is_too_small_sequence: bool = len(sequences) < TOO_SMALL_SEQUENCE
    is_too_large_sequence: bool = len(sequences) >= TOO_BIG_SEQUENCE

    if is_too_small_sequence:
        logger.log(
            TRACE,
            "Trying to detect encoding from a tiny portion of ({}) byte(s).".format(
                length
            ),
        )
    elif is_too_large_sequence:
        logger.log(
            TRACE,
            "Using lazy str decoding because the payload is quite large, ({}) byte(s).".format(
                length
            ),
        )

    prioritized_encodings: list[str] = []

    specified_encoding: str | None = (
        any_specified_encoding(sequences) if preemptive_behaviour else None
    )

    if specified_encoding is not None:
        prioritized_encodings.append(specified_encoding)
        logger.log(
            TRACE,
            "Detected declarative mark in sequence. Priority +1 given for %s.",
            specified_encoding,
        )

    tested: set[str] = set()
    tested_but_hard_failure: list[str] = []
    tested_but_soft_failure: list[str] = []

    fallback_ascii: CharsetMatch | None = None
    fallback_u8: CharsetMatch | None = None
    fallback_specified: CharsetMatch | None = None

    results: CharsetMatches = CharsetMatches()

    early_stop_results: CharsetMatches = CharsetMatches()

    sig_encoding, sig_payload = identify_sig_or_bom(sequences)

    if sig_encoding is not None:
        prioritized_encodings.append(sig_encoding)
        logger.log(
            TRACE,
            "Detected a SIG or BOM mark on first %i byte(s). Priority +1 given for %s.",
            len(sig_payload),
            sig_encoding,
        )

    prioritized_encodings.append("ascii")

    if "utf_8" not in prioritized_encodings:
        prioritized_encodings.append("utf_8")

    for encoding_iana in prioritized_encodings + IANA_SUPPORTED:
        if cp_isolation and encoding_iana not in cp_isolation:
            continue

        if cp_exclusion and encoding_iana in cp_exclusion:
            continue

        if encoding_iana in tested:
            continue

        tested.add(encoding_iana)

        decoded_payload: str | None = None
        bom_or_sig_available: bool = sig_encoding == encoding_iana
        strip_sig_or_bom: bool = bom_or_sig_available and should_strip_sig_or_bom(
            encoding_iana
        )

        if encoding_iana in {"utf_16", "utf_32"} and not bom_or_sig_available:
            logger.log(
                TRACE,
                "Encoding %s won't be tested as-is because it require a BOM. Will try some sub-encoder LE/BE.",
                encoding_iana,
            )
            continue
        if encoding_iana in {"utf_7"} and not bom_or_sig_available:
            logger.log(
                TRACE,
                "Encoding %s won't be tested as-is because detection is unreliable without BOM/SIG.",
                encoding_iana,
            )
            continue

        try:
            is_multi_byte_decoder: bool = is_multi_byte_encoding(encoding_iana)
        except (ModuleNotFoundError, ImportError):
            logger.log(
                TRACE,
                "Encoding %s does not provide an IncrementalDecoder",
                encoding_iana,
            )
            continue

        try:
            if is_too_large_sequence and is_multi_byte_decoder is False:
                str(
                    (
                        sequences[: int(50e4)]
                        if strip_sig_or_bom is False
                        else sequences[len(sig_payload) : int(50e4)]
                    ),
                    encoding=encoding_iana,
                )
            else:
                decoded_payload = str(
                    (
                        sequences
                        if strip_sig_or_bom is False
                        else sequences[len(sig_payload) :]
                    ),
                    encoding=encoding_iana,
                )
        except (UnicodeDecodeError, LookupError) as e:
            if not isinstance(e, LookupError):
                logger.log(
                    TRACE,
                    "Code page %s does not fit given bytes sequence at ALL. %s",
                    encoding_iana,
                    str(e),
                )
            tested_but_hard_failure.append(encoding_iana)
            continue

        similar_soft_failure_test: bool = False

        for encoding_soft_failed in tested_but_soft_failure:
            if is_cp_similar(encoding_iana, encoding_soft_failed):
                similar_soft_failure_test = True
                break

        if similar_soft_failure_test:
            logger.log(
                TRACE,
                "%s is deemed too similar to code page %s and was consider unsuited already. Continuing!",
                encoding_iana,
                encoding_soft_failed,
            )
            continue

        r_ = range(
            0 if not bom_or_sig_available else len(sig_payload),
            length,
            int(length / steps),
        )

        multi_byte_bonus: bool = (
            is_multi_byte_decoder
            and decoded_payload is not None
            and len(decoded_payload) < length
        )

        if multi_byte_bonus:
            logger.log(
                TRACE,
                "Code page %s is a multi byte encoding table and it appear that at least one character "
                "was encoded using n-bytes.",
                encoding_iana,
            )

        max_chunk_gave_up: int = int(len(r_) / 4)

        max_chunk_gave_up = max(max_chunk_gave_up, 2)
        early_stop_count: int = 0
        lazy_str_hard_failure = False

        md_chunks: list[str] = []
        md_ratios = []

        try:
            for chunk in cut_sequence_chunks(
                sequences,
                encoding_iana,
                r_,
                chunk_size,
                bom_or_sig_available,
                strip_sig_or_bom,
                sig_payload,
                is_multi_byte_decoder,
                decoded_payload,
            ):
                md_chunks.append(chunk)

                md_ratios.append(
                    mess_ratio(
                        chunk,
                        threshold,
                        explain is True and 1 <= len(cp_isolation) <= 2,
                    )
                )

                if md_ratios[-1] >= threshold:
                    early_stop_count += 1

                if (early_stop_count >= max_chunk_gave_up) or (
                    bom_or_sig_available and strip_sig_or_bom is False
                ):
                    break
        except (
            UnicodeDecodeError
        ) as e:  # Lazy str loading may have missed something there
            logger.log(
                TRACE,
                "LazyStr Loading: After MD chunk decode, code page %s does not fit given bytes sequence at ALL. %s",
                encoding_iana,
                str(e),
            )
            early_stop_count = max_chunk_gave_up
            lazy_str_hard_failure = True

        # We might want to check the sequence again with the whole content
        # Only if initial MD tests passes
        if (
            not lazy_str_hard_failure
            and is_too_large_sequence
            and not is_multi_byte_decoder
        ):
            try:
                sequences[int(50e3) :].decode(encoding_iana, errors="strict")
            except UnicodeDecodeError as e:
                logger.log(
                    TRACE,
                    "LazyStr Loading: After final lookup, code page %s does not fit given bytes sequence at ALL. %s",
                    encoding_iana,
                    str(e),
                )
                tested_but_hard_failure.append(encoding_iana)
                continue

        mean_mess_ratio: float = sum(md_ratios) / len(md_ratios) if md_ratios else 0.0
        if mean_mess_ratio >= threshold or early_stop_count >= max_chunk_gave_up:
            tested_but_soft_failure.append(encoding_iana)
            logger.log(
                TRACE,
                "%s was excluded because of initial chaos probing. Gave up %i time(s). "
                "Computed mean chaos is %f %%.",
                encoding_iana,
                early_stop_count,
                round(mean_mess_ratio * 100, ndigits=3),
            )
            # Preparing those fallbacks in case we got nothing.
            if (
                enable_fallback
                and encoding_iana in ["ascii", "utf_8", specified_encoding]
                and not lazy_str_hard_failure
            ):
                fallback_entry = CharsetMatch(
                    sequences,
                    encoding_iana,
                    threshold,
                    False,
                    [],
                    decoded_payload,
                    preemptive_declaration=specified_encoding,
                )
                if encoding_iana == specified_encoding:
                    fallback_specified = fallback_entry
                elif encoding_iana == "ascii":
                    fallback_ascii = fallback_entry
                else:
                    fallback_u8 = fallback_entry
            continue

        logger.log(
            TRACE,
            "%s passed initial chaos probing. Mean measured chaos is %f %%",
            encoding_iana,
            round(mean_mess_ratio * 100, ndigits=3),
        )

        if not is_multi_byte_decoder:
            target_languages: list[str] = encoding_languages(encoding_iana)
        else:
            target_languages = mb_encoding_languages(encoding_iana)

        if target_languages:
            logger.log(
                TRACE,
                "{} should target any language(s) of {}".format(
                    encoding_iana, str(target_languages)
                ),
            )

        cd_ratios = []

        # We shall skip the CD when its about ASCII
        # Most of the time its not relevant to run "language-detection" on it.
        if encoding_iana != "ascii":
            for chunk in md_chunks:
                chunk_languages = coherence_ratio(
                    chunk,
                    language_threshold,
                    ",".join(target_languages) if target_languages else None,
                )

                cd_ratios.append(chunk_languages)

        cd_ratios_merged = merge_coherence_ratios(cd_ratios)

        if cd_ratios_merged:
            logger.log(
                TRACE,
                "We detected language {} using {}".format(
                    cd_ratios_merged, encoding_iana
                ),
            )

        current_match = CharsetMatch(
            sequences,
            encoding_iana,
            mean_mess_ratio,
            bom_or_sig_available,
            cd_ratios_merged,
            (
                decoded_payload
                if (
                    is_too_large_sequence is False
                    or encoding_iana in [specified_encoding, "ascii", "utf_8"]
                )
                else None
            ),
            preemptive_declaration=specified_encoding,
        )

        results.append(current_match)

        if (
            encoding_iana in [specified_encoding, "ascii", "utf_8"]
            and mean_mess_ratio < 0.1
        ):
            # If md says nothing to worry about, then... stop immediately!
            if mean_mess_ratio == 0.0:
                logger.debug(
                    "Encoding detection: %s is most likely the one.",
                    current_match.encoding,
                )
                if explain:  # Defensive: ensure exit path clean handler
                    logger.removeHandler(explain_handler)
                    logger.setLevel(previous_logger_level)
                return CharsetMatches([current_match])

            early_stop_results.append(current_match)

        if (
            len(early_stop_results)
            and (specified_encoding is None or specified_encoding in tested)
            and "ascii" in tested
            and "utf_8" in tested
        ):
            probable_result: CharsetMatch = early_stop_results.best()  # type: ignore[assignment]
            logger.debug(
                "Encoding detection: %s is most likely the one.",
                probable_result.encoding,
            )
            if explain:  # Defensive: ensure exit path clean handler
                logger.removeHandler(explain_handler)
                logger.setLevel(previous_logger_level)

            return CharsetMatches([probable_result])

        if encoding_iana == sig_encoding:
            logger.debug(
                "Encoding detection: %s is most likely the one as we detected a BOM or SIG within "
                "the beginning of the sequence.",
                encoding_iana,
            )
            if explain:  # Defensive: ensure exit path clean handler
                logger.removeHandler(explain_handler)
                logger.setLevel(previous_logger_level)
            return CharsetMatches([results[encoding_iana]])

    if len(results) == 0:
        if fallback_u8 or fallback_ascii or fallback_specified:
            logger.log(
                TRACE,
                "Nothing got out of the detection process. Using ASCII/UTF-8/Specified fallback.",
            )

        if fallback_specified:
            logger.debug(
                "Encoding detection: %s will be used as a fallback match",
                fallback_specified.encoding,
            )
            results.append(fallback_specified)
        elif (
            (fallback_u8 and fallback_ascii is None)
            or (
                fallback_u8
                and fallback_ascii
                and fallback_u8.fingerprint != fallback_ascii.fingerprint
            )
            or (fallback_u8 is not None)
        ):
            logger.debug("Encoding detection: utf_8 will be used as a fallback match")
            results.append(fallback_u8)
        elif fallback_ascii:
            logger.debug("Encoding detection: ascii will be used as a fallback match")
            results.append(fallback_ascii)

    if results:
        logger.debug(
            "Encoding detection: Found %s as plausible (best-candidate) for content. With %i alternatives.",
            results.best().encoding,  # type: ignore
            len(results) - 1,
        )
    else:
        logger.debug("Encoding detection: Unable to determine any suitable charset.")

    if explain:
        logger.removeHandler(explain_handler)
        logger.setLevel(previous_logger_level)

    return results


def from_fp(
    fp: BinaryIO,
    steps: int = 5,
    chunk_size: int = 512,
    threshold: float = 0.20,
    cp_isolation: list[str] | None = None,
    cp_exclusion: list[str] | None = None,
    preemptive_behaviour: bool = True,
    explain: bool = False,
    language_threshold: float = 0.1,
    enable_fallback: bool = True,
) -> CharsetMatches:
    """
    Same thing than the function from_bytes but using a file pointer that is already ready.
    Will not close the file pointer.
    """
    return from_bytes(
        fp.read(),
        steps,
        chunk_size,
        threshold,
        cp_isolation,
        cp_exclusion,
        preemptive_behaviour,
        explain,
        language_threshold,
        enable_fallback,
    )


def from_path(
    path: str | bytes | PathLike,  # type: ignore[type-arg]
    steps: int = 5,
    chunk_size: int = 512,
    threshold: float = 0.20,
    cp_isolation: list[str] | None = None,
    cp_exclusion: list[str] | None = None,
    preemptive_behaviour: bool = True,
    explain: bool = False,
    language_threshold: float = 0.1,
    enable_fallback: bool = True,
) -> CharsetMatches:
    """
    Same thing than the function from_bytes but with one extra step. Opening and reading given file path in binary mode.
    Can raise IOError.
    """
    with open(path, "rb") as fp:
        return from_fp(
            fp,
            steps,
            chunk_size,
            threshold,
            cp_isolation,
            cp_exclusion,
            preemptive_behaviour,
            explain,
            language_threshold,
            enable_fallback,
        )


def is_binary(
    fp_or_path_or_payload: PathLike | str | BinaryIO | bytes,  # type: ignore[type-arg]
    steps: int = 5,
    chunk_size: int = 512,
    threshold: float = 0.20,
    cp_isolation: list[str] | None = None,
    cp_exclusion: list[str] | None = None,
    preemptive_behaviour: bool = True,
    explain: bool = False,
    language_threshold: float = 0.1,
    enable_fallback: bool = False,
) -> bool:
    """
    Detect if the given input (file, bytes, or path) points to a binary file. aka. not a string.
    Based on the same main heuristic algorithms and default kwargs at the sole exception that fallbacks match
    are disabled to be stricter around ASCII-compatible but unlikely to be a string.
    """
    if isinstance(fp_or_path_or_payload, (str, PathLike)):
        guesses = from_path(
            fp_or_path_or_payload,
            steps=steps,
            chunk_size=chunk_size,
            threshold=threshold,
            cp_isolation=cp_isolation,
            cp_exclusion=cp_exclusion,
            preemptive_behaviour=preemptive_behaviour,
            explain=explain,
            language_threshold=language_threshold,
            enable_fallback=enable_fallback,
        )
    elif isinstance(
        fp_or_path_or_payload,
        (
            bytes,
            bytearray,
        ),
    ):
        guesses = from_bytes(
            fp_or_path_or_payload,
            steps=steps,
            chunk_size=chunk_size,
            threshold=threshold,
            cp_isolation=cp_isolation,
            cp_exclusion=cp_exclusion,
            preemptive_behaviour=preemptive_behaviour,
            explain=explain,
            language_threshold=language_threshold,
            enable_fallback=enable_fallback,
        )
    else:
        guesses = from_fp(
            fp_or_path_or_payload,
            steps=steps,
            chunk_size=chunk_size,
            threshold=threshold,
            cp_isolation=cp_isolation,
            cp_exclusion=cp_exclusion,
            preemptive_behaviour=preemptive_behaviour,
            explain=explain,
            language_threshold=language_threshold,
            enable_fallback=enable_fallback,
        )

    return not guesses

# === NexusCore/openenv\Lib\site-packages\pygments\cmdline.py ===
"""
    pygments.cmdline
    ~~~~~~~~~~~~~~~~

    Command line interface.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import os
import sys
import shutil
import argparse
from textwrap import dedent

from pygments import __version__, highlight
from pygments.util import ClassNotFound, OptionError, docstring_headline, \
    guess_decode, guess_decode_from_terminal, terminal_encoding, \
    UnclosingTextIOWrapper
from pygments.lexers import get_all_lexers, get_lexer_by_name, guess_lexer, \
    load_lexer_from_file, get_lexer_for_filename, find_lexer_class_for_filename
from pygments.lexers.special import TextLexer
from pygments.formatters.latex import LatexEmbeddedLexer, LatexFormatter
from pygments.formatters import get_all_formatters, get_formatter_by_name, \
    load_formatter_from_file, get_formatter_for_filename, find_formatter_class
from pygments.formatters.terminal import TerminalFormatter
from pygments.formatters.terminal256 import Terminal256Formatter, TerminalTrueColorFormatter
from pygments.filters import get_all_filters, find_filter_class
from pygments.styles import get_all_styles, get_style_by_name


def _parse_options(o_strs):
    opts = {}
    if not o_strs:
        return opts
    for o_str in o_strs:
        if not o_str.strip():
            continue
        o_args = o_str.split(',')
        for o_arg in o_args:
            o_arg = o_arg.strip()
            try:
                o_key, o_val = o_arg.split('=', 1)
                o_key = o_key.strip()
                o_val = o_val.strip()
            except ValueError:
                opts[o_arg] = True
            else:
                opts[o_key] = o_val
    return opts


def _parse_filters(f_strs):
    filters = []
    if not f_strs:
        return filters
    for f_str in f_strs:
        if ':' in f_str:
            fname, fopts = f_str.split(':', 1)
            filters.append((fname, _parse_options([fopts])))
        else:
            filters.append((f_str, {}))
    return filters


def _print_help(what, name):
    try:
        if what == 'lexer':
            cls = get_lexer_by_name(name)
            print(f"Help on the {cls.name} lexer:")
            print(dedent(cls.__doc__))
        elif what == 'formatter':
            cls = find_formatter_class(name)
            print(f"Help on the {cls.name} formatter:")
            print(dedent(cls.__doc__))
        elif what == 'filter':
            cls = find_filter_class(name)
            print(f"Help on the {name} filter:")
            print(dedent(cls.__doc__))
        return 0
    except (AttributeError, ValueError):
        print(f"{what} not found!", file=sys.stderr)
        return 1


def _print_list(what):
    if what == 'lexer':
        print()
        print("Lexers:")
        print("~~~~~~~")

        info = []
        for fullname, names, exts, _ in get_all_lexers():
            tup = (', '.join(names)+':', fullname,
                   exts and '(filenames ' + ', '.join(exts) + ')' or '')
            info.append(tup)
        info.sort()
        for i in info:
            print(('* {}\n    {} {}').format(*i))

    elif what == 'formatter':
        print()
        print("Formatters:")
        print("~~~~~~~~~~~")

        info = []
        for cls in get_all_formatters():
            doc = docstring_headline(cls)
            tup = (', '.join(cls.aliases) + ':', doc, cls.filenames and
                   '(filenames ' + ', '.join(cls.filenames) + ')' or '')
            info.append(tup)
        info.sort()
        for i in info:
            print(('* {}\n    {} {}').format(*i))

    elif what == 'filter':
        print()
        print("Filters:")
        print("~~~~~~~~")

        for name in get_all_filters():
            cls = find_filter_class(name)
            print("* " + name + ':')
            print(f"    {docstring_headline(cls)}")

    elif what == 'style':
        print()
        print("Styles:")
        print("~~~~~~~")

        for name in get_all_styles():
            cls = get_style_by_name(name)
            print("* " + name + ':')
            print(f"    {docstring_headline(cls)}")


def _print_list_as_json(requested_items):
    import json
    result = {}
    if 'lexer' in requested_items:
        info = {}
        for fullname, names, filenames, mimetypes in get_all_lexers():
            info[fullname] = {
                'aliases': names,
                'filenames': filenames,
                'mimetypes': mimetypes
            }
        result['lexers'] = info

    if 'formatter' in requested_items:
        info = {}
        for cls in get_all_formatters():
            doc = docstring_headline(cls)
            info[cls.name] = {
                'aliases': cls.aliases,
                'filenames': cls.filenames,
                'doc': doc
            }
        result['formatters'] = info

    if 'filter' in requested_items:
        info = {}
        for name in get_all_filters():
            cls = find_filter_class(name)
            info[name] = {
                'doc': docstring_headline(cls)
            }
        result['filters'] = info

    if 'style' in requested_items:
        info = {}
        for name in get_all_styles():
            cls = get_style_by_name(name)
            info[name] = {
                'doc': docstring_headline(cls)
            }
        result['styles'] = info

    json.dump(result, sys.stdout)

def main_inner(parser, argns):
    if argns.help:
        parser.print_help()
        return 0

    if argns.V:
        print(f'Pygments version {__version__}, (c) 2006-2024 by Georg Brandl, Matthäus '
              'Chajdas and contributors.')
        return 0

    def is_only_option(opt):
        return not any(v for (k, v) in vars(argns).items() if k != opt)

    # handle ``pygmentize -L``
    if argns.L is not None:
        arg_set = set()
        for k, v in vars(argns).items():
            if v:
                arg_set.add(k)

        arg_set.discard('L')
        arg_set.discard('json')

        if arg_set:
            parser.print_help(sys.stderr)
            return 2

        # print version
        if not argns.json:
            main(['', '-V'])
        allowed_types = {'lexer', 'formatter', 'filter', 'style'}
        largs = [arg.rstrip('s') for arg in argns.L]
        if any(arg not in allowed_types for arg in largs):
            parser.print_help(sys.stderr)
            return 0
        if not largs:
            largs = allowed_types
        if not argns.json:
            for arg in largs:
                _print_list(arg)
        else:
            _print_list_as_json(largs)
        return 0

    # handle ``pygmentize -H``
    if argns.H:
        if not is_only_option('H'):
            parser.print_help(sys.stderr)
            return 2
        what, name = argns.H
        if what not in ('lexer', 'formatter', 'filter'):
            parser.print_help(sys.stderr)
            return 2
        return _print_help(what, name)

    # parse -O options
    parsed_opts = _parse_options(argns.O or [])

    # parse -P options
    for p_opt in argns.P or []:
        try:
            name, value = p_opt.split('=', 1)
        except ValueError:
            parsed_opts[p_opt] = True
        else:
            parsed_opts[name] = value

    # encodings
    inencoding = parsed_opts.get('inencoding', parsed_opts.get('encoding'))
    outencoding = parsed_opts.get('outencoding', parsed_opts.get('encoding'))

    # handle ``pygmentize -N``
    if argns.N:
        lexer = find_lexer_class_for_filename(argns.N)
        if lexer is None:
            lexer = TextLexer

        print(lexer.aliases[0])
        return 0

    # handle ``pygmentize -C``
    if argns.C:
        inp = sys.stdin.buffer.read()
        try:
            lexer = guess_lexer(inp, inencoding=inencoding)
        except ClassNotFound:
            lexer = TextLexer

        print(lexer.aliases[0])
        return 0

    # handle ``pygmentize -S``
    S_opt = argns.S
    a_opt = argns.a
    if S_opt is not None:
        f_opt = argns.f
        if not f_opt:
            parser.print_help(sys.stderr)
            return 2
        if argns.l or argns.INPUTFILE:
            parser.print_help(sys.stderr)
            return 2

        try:
            parsed_opts['style'] = S_opt
            fmter = get_formatter_by_name(f_opt, **parsed_opts)
        except ClassNotFound as err:
            print(err, file=sys.stderr)
            return 1

        print(fmter.get_style_defs(a_opt or ''))
        return 0

    # if no -S is given, -a is not allowed
    if argns.a is not None:
        parser.print_help(sys.stderr)
        return 2

    # parse -F options
    F_opts = _parse_filters(argns.F or [])

    # -x: allow custom (eXternal) lexers and formatters
    allow_custom_lexer_formatter = bool(argns.x)

    # select lexer
    lexer = None

    # given by name?
    lexername = argns.l
    if lexername:
        # custom lexer, located relative to user's cwd
        if allow_custom_lexer_formatter and '.py' in lexername:
            try:
                filename = None
                name = None
                if ':' in lexername:
                    filename, name = lexername.rsplit(':', 1)

                    if '.py' in name:
                        # This can happen on Windows: If the lexername is
                        # C:\lexer.py -- return to normal load path in that case
                        name = None

                if filename and name:
                    lexer = load_lexer_from_file(filename, name,
                                                 **parsed_opts)
                else:
                    lexer = load_lexer_from_file(lexername, **parsed_opts)
            except ClassNotFound as err:
                print('Error:', err, file=sys.stderr)
                return 1
        else:
            try:
                lexer = get_lexer_by_name(lexername, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1

    # read input code
    code = None

    if argns.INPUTFILE:
        if argns.s:
            print('Error: -s option not usable when input file specified',
                  file=sys.stderr)
            return 2

        infn = argns.INPUTFILE
        try:
            with open(infn, 'rb') as infp:
                code = infp.read()
        except Exception as err:
            print('Error: cannot read infile:', err, file=sys.stderr)
            return 1
        if not inencoding:
            code, inencoding = guess_decode(code)

        # do we have to guess the lexer?
        if not lexer:
            try:
                lexer = get_lexer_for_filename(infn, code, **parsed_opts)
            except ClassNotFound as err:
                if argns.g:
                    try:
                        lexer = guess_lexer(code, **parsed_opts)
                    except ClassNotFound:
                        lexer = TextLexer(**parsed_opts)
                else:
                    print('Error:', err, file=sys.stderr)
                    return 1
            except OptionError as err:
                print('Error:', err, file=sys.stderr)
                return 1

    elif not argns.s:  # treat stdin as full file (-s support is later)
        # read code from terminal, always in binary mode since we want to
        # decode ourselves and be tolerant with it
        code = sys.stdin.buffer.read()  # use .buffer to get a binary stream
        if not inencoding:
            code, inencoding = guess_decode_from_terminal(code, sys.stdin)
            # else the lexer will do the decoding
        if not lexer:
            try:
                lexer = guess_lexer(code, **parsed_opts)
            except ClassNotFound:
                lexer = TextLexer(**parsed_opts)

    else:  # -s option needs a lexer with -l
        if not lexer:
            print('Error: when using -s a lexer has to be selected with -l',
                  file=sys.stderr)
            return 2

    # process filters
    for fname, fopts in F_opts:
        try:
            lexer.add_filter(fname, **fopts)
        except ClassNotFound as err:
            print('Error:', err, file=sys.stderr)
            return 1

    # select formatter
    outfn = argns.o
    fmter = argns.f
    if fmter:
        # custom formatter, located relative to user's cwd
        if allow_custom_lexer_formatter and '.py' in fmter:
            try:
                filename = None
                name = None
                if ':' in fmter:
                    # Same logic as above for custom lexer
                    filename, name = fmter.rsplit(':', 1)

                    if '.py' in name:
                        name = None

                if filename and name:
                    fmter = load_formatter_from_file(filename, name,
                                                     **parsed_opts)
                else:
                    fmter = load_formatter_from_file(fmter, **parsed_opts)
            except ClassNotFound as err:
                print('Error:', err, file=sys.stderr)
                return 1
        else:
            try:
                fmter = get_formatter_by_name(fmter, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1

    if outfn:
        if not fmter:
            try:
                fmter = get_formatter_for_filename(outfn, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1
        try:
            outfile = open(outfn, 'wb')
        except Exception as err:
            print('Error: cannot open outfile:', err, file=sys.stderr)
            return 1
    else:
        if not fmter:
            if os.environ.get('COLORTERM','') in ('truecolor', '24bit'):
                fmter = TerminalTrueColorFormatter(**parsed_opts)
            elif '256' in os.environ.get('TERM', ''):
                fmter = Terminal256Formatter(**parsed_opts)
            else:
                fmter = TerminalFormatter(**parsed_opts)
        outfile = sys.stdout.buffer

    # determine output encoding if not explicitly selected
    if not outencoding:
        if outfn:
            # output file? use lexer encoding for now (can still be None)
            fmter.encoding = inencoding
        else:
            # else use terminal encoding
            fmter.encoding = terminal_encoding(sys.stdout)

    # provide coloring under Windows, if possible
    if not outfn and sys.platform in ('win32', 'cygwin') and \
       fmter.name in ('Terminal', 'Terminal256'):  # pragma: no cover
        # unfortunately colorama doesn't support binary streams on Py3
        outfile = UnclosingTextIOWrapper(outfile, encoding=fmter.encoding)
        fmter.encoding = None
        try:
            import colorama.initialise
        except ImportError:
            pass
        else:
            outfile = colorama.initialise.wrap_stream(
                outfile, convert=None, strip=None, autoreset=False, wrap=True)

    # When using the LaTeX formatter and the option `escapeinside` is
    # specified, we need a special lexer which collects escaped text
    # before running the chosen language lexer.
    escapeinside = parsed_opts.get('escapeinside', '')
    if len(escapeinside) == 2 and isinstance(fmter, LatexFormatter):
        left = escapeinside[0]
        right = escapeinside[1]
        lexer = LatexEmbeddedLexer(left, right, lexer)

    # ... and do it!
    if not argns.s:
        # process whole input as per normal...
        try:
            highlight(code, lexer, fmter, outfile)
        finally:
            if outfn:
                outfile.close()
        return 0
    else:
        # line by line processing of stdin (eg: for 'tail -f')...
        try:
            while 1:
                line = sys.stdin.buffer.readline()
                if not line:
                    break
                if not inencoding:
                    line = guess_decode_from_terminal(line, sys.stdin)[0]
                highlight(line, lexer, fmter, outfile)
                if hasattr(outfile, 'flush'):
                    outfile.flush()
            return 0
        except KeyboardInterrupt:  # pragma: no cover
            return 0
        finally:
            if outfn:
                outfile.close()


class HelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog, indent_increment=2, max_help_position=16, width=None):
        if width is None:
            try:
                width = shutil.get_terminal_size().columns - 2
            except Exception:
                pass
        argparse.HelpFormatter.__init__(self, prog, indent_increment,
                                        max_help_position, width)


def main(args=sys.argv):
    """
    Main command line entry point.
    """
    desc = "Highlight an input file and write the result to an output file."
    parser = argparse.ArgumentParser(description=desc, add_help=False,
                                     formatter_class=HelpFormatter)

    operation = parser.add_argument_group('Main operation')
    lexersel = operation.add_mutually_exclusive_group()
    lexersel.add_argument(
        '-l', metavar='LEXER',
        help='Specify the lexer to use.  (Query names with -L.)  If not '
        'given and -g is not present, the lexer is guessed from the filename.')
    lexersel.add_argument(
        '-g', action='store_true',
        help='Guess the lexer from the file contents, or pass through '
        'as plain text if nothing can be guessed.')
    operation.add_argument(
        '-F', metavar='FILTER[:options]', action='append',
        help='Add a filter to the token stream.  (Query names with -L.) '
        'Filter options are given after a colon if necessary.')
    operation.add_argument(
        '-f', metavar='FORMATTER',
        help='Specify the formatter to use.  (Query names with -L.) '
        'If not given, the formatter is guessed from the output filename, '
        'and defaults to the terminal formatter if the output is to the '
        'terminal or an unknown file extension.')
    operation.add_argument(
        '-O', metavar='OPTION=value[,OPTION=value,...]', action='append',
        help='Give options to the lexer and formatter as a comma-separated '
        'list of key-value pairs. '
        'Example: `-O bg=light,python=cool`.')
    operation.add_argument(
        '-P', metavar='OPTION=value', action='append',
        help='Give a single option to the lexer and formatter - with this '
        'you can pass options whose value contains commas and equal signs. '
        'Example: `-P "heading=Pygments, the Python highlighter"`.')
    operation.add_argument(
        '-o', metavar='OUTPUTFILE',
        help='Where to write the output.  Defaults to standard output.')

    operation.add_argument(
        'INPUTFILE', nargs='?',
        help='Where to read the input.  Defaults to standard input.')

    flags = parser.add_argument_group('Operation flags')
    flags.add_argument(
        '-v', action='store_true',
        help='Print a detailed traceback on unhandled exceptions, which '
        'is useful for debugging and bug reports.')
    flags.add_argument(
        '-s', action='store_true',
        help='Process lines one at a time until EOF, rather than waiting to '
        'process the entire file.  This only works for stdin, only for lexers '
        'with no line-spanning constructs, and is intended for streaming '
        'input such as you get from `tail -f`. '
        'Example usage: `tail -f sql.log | pygmentize -s -l sql`.')
    flags.add_argument(
        '-x', action='store_true',
        help='Allow custom lexers and formatters to be loaded from a .py file '
        'relative to the current working directory. For example, '
        '`-l ./customlexer.py -x`. By default, this option expects a file '
        'with a class named CustomLexer or CustomFormatter; you can also '
        'specify your own class name with a colon (`-l ./lexer.py:MyLexer`). '
        'Users should be very careful not to use this option with untrusted '
        'files, because it will import and run them.')
    flags.add_argument('--json', help='Output as JSON. This can '
        'be only used in conjunction with -L.',
        default=False,
        action='store_true')

    special_modes_group = parser.add_argument_group(
        'Special modes - do not do any highlighting')
    special_modes = special_modes_group.add_mutually_exclusive_group()
    special_modes.add_argument(
        '-S', metavar='STYLE -f formatter',
        help='Print style definitions for STYLE for a formatter '
        'given with -f. The argument given by -a is formatter '
        'dependent.')
    special_modes.add_argument(
        '-L', nargs='*', metavar='WHAT',
        help='List lexers, formatters, styles or filters -- '
        'give additional arguments for the thing(s) you want to list '
        '(e.g. "styles"), or omit them to list everything.')
    special_modes.add_argument(
        '-N', metavar='FILENAME',
        help='Guess and print out a lexer name based solely on the given '
        'filename. Does not take input or highlight anything. If no specific '
        'lexer can be determined, "text" is printed.')
    special_modes.add_argument(
        '-C', action='store_true',
        help='Like -N, but print out a lexer name based solely on '
        'a given content from standard input.')
    special_modes.add_argument(
        '-H', action='store', nargs=2, metavar=('NAME', 'TYPE'),
        help='Print detailed help for the object <name> of type <type>, '
        'where <type> is one of "lexer", "formatter" or "filter".')
    special_modes.add_argument(
        '-V', action='store_true',
        help='Print the package version.')
    special_modes.add_argument(
        '-h', '--help', action='store_true',
        help='Print this help.')
    special_modes_group.add_argument(
        '-a', metavar='ARG',
        help='Formatter-specific additional argument for the -S (print '
        'style sheet) mode.')

    argns = parser.parse_args(args[1:])

    try:
        return main_inner(parser, argns)
    except BrokenPipeError:
        # someone closed our stdout, e.g. by quitting a pager.
        return 0
    except Exception:
        if argns.v:
            print(file=sys.stderr)
            print('*' * 65, file=sys.stderr)
            print('An unhandled exception occurred while highlighting.',
                  file=sys.stderr)
            print('Please report the whole traceback to the issue tracker at',
                  file=sys.stderr)
            print('<https://github.com/pygments/pygments/issues>.',
                  file=sys.stderr)
            print('*' * 65, file=sys.stderr)
            print(file=sys.stderr)
            raise
        import traceback
        info = traceback.format_exception(*sys.exc_info())
        msg = info[-1].strip()
        if len(info) >= 3:
            # extract relevant file and position info
            msg += '\n   (f{})'.format(info[-2].split('\n')[0].strip()[1:])
        print(file=sys.stderr)
        print('*** Error while highlighting:', file=sys.stderr)
        print(msg, file=sys.stderr)
        print('*** If this is a bug you want to report, please rerun with -v.',
              file=sys.stderr)
        return 1

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\cmdline.py ===
"""
    pygments.cmdline
    ~~~~~~~~~~~~~~~~

    Command line interface.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import os
import sys
import shutil
import argparse
from textwrap import dedent

from pip._vendor.pygments import __version__, highlight
from pip._vendor.pygments.util import ClassNotFound, OptionError, docstring_headline, \
    guess_decode, guess_decode_from_terminal, terminal_encoding, \
    UnclosingTextIOWrapper
from pip._vendor.pygments.lexers import get_all_lexers, get_lexer_by_name, guess_lexer, \
    load_lexer_from_file, get_lexer_for_filename, find_lexer_class_for_filename
from pip._vendor.pygments.lexers.special import TextLexer
from pip._vendor.pygments.formatters.latex import LatexEmbeddedLexer, LatexFormatter
from pip._vendor.pygments.formatters import get_all_formatters, get_formatter_by_name, \
    load_formatter_from_file, get_formatter_for_filename, find_formatter_class
from pip._vendor.pygments.formatters.terminal import TerminalFormatter
from pip._vendor.pygments.formatters.terminal256 import Terminal256Formatter, TerminalTrueColorFormatter
from pip._vendor.pygments.filters import get_all_filters, find_filter_class
from pip._vendor.pygments.styles import get_all_styles, get_style_by_name


def _parse_options(o_strs):
    opts = {}
    if not o_strs:
        return opts
    for o_str in o_strs:
        if not o_str.strip():
            continue
        o_args = o_str.split(',')
        for o_arg in o_args:
            o_arg = o_arg.strip()
            try:
                o_key, o_val = o_arg.split('=', 1)
                o_key = o_key.strip()
                o_val = o_val.strip()
            except ValueError:
                opts[o_arg] = True
            else:
                opts[o_key] = o_val
    return opts


def _parse_filters(f_strs):
    filters = []
    if not f_strs:
        return filters
    for f_str in f_strs:
        if ':' in f_str:
            fname, fopts = f_str.split(':', 1)
            filters.append((fname, _parse_options([fopts])))
        else:
            filters.append((f_str, {}))
    return filters


def _print_help(what, name):
    try:
        if what == 'lexer':
            cls = get_lexer_by_name(name)
            print(f"Help on the {cls.name} lexer:")
            print(dedent(cls.__doc__))
        elif what == 'formatter':
            cls = find_formatter_class(name)
            print(f"Help on the {cls.name} formatter:")
            print(dedent(cls.__doc__))
        elif what == 'filter':
            cls = find_filter_class(name)
            print(f"Help on the {name} filter:")
            print(dedent(cls.__doc__))
        return 0
    except (AttributeError, ValueError):
        print(f"{what} not found!", file=sys.stderr)
        return 1


def _print_list(what):
    if what == 'lexer':
        print()
        print("Lexers:")
        print("~~~~~~~")

        info = []
        for fullname, names, exts, _ in get_all_lexers():
            tup = (', '.join(names)+':', fullname,
                   exts and '(filenames ' + ', '.join(exts) + ')' or '')
            info.append(tup)
        info.sort()
        for i in info:
            print(('* {}\n    {} {}').format(*i))

    elif what == 'formatter':
        print()
        print("Formatters:")
        print("~~~~~~~~~~~")

        info = []
        for cls in get_all_formatters():
            doc = docstring_headline(cls)
            tup = (', '.join(cls.aliases) + ':', doc, cls.filenames and
                   '(filenames ' + ', '.join(cls.filenames) + ')' or '')
            info.append(tup)
        info.sort()
        for i in info:
            print(('* {}\n    {} {}').format(*i))

    elif what == 'filter':
        print()
        print("Filters:")
        print("~~~~~~~~")

        for name in get_all_filters():
            cls = find_filter_class(name)
            print("* " + name + ':')
            print(f"    {docstring_headline(cls)}")

    elif what == 'style':
        print()
        print("Styles:")
        print("~~~~~~~")

        for name in get_all_styles():
            cls = get_style_by_name(name)
            print("* " + name + ':')
            print(f"    {docstring_headline(cls)}")


def _print_list_as_json(requested_items):
    import json
    result = {}
    if 'lexer' in requested_items:
        info = {}
        for fullname, names, filenames, mimetypes in get_all_lexers():
            info[fullname] = {
                'aliases': names,
                'filenames': filenames,
                'mimetypes': mimetypes
            }
        result['lexers'] = info

    if 'formatter' in requested_items:
        info = {}
        for cls in get_all_formatters():
            doc = docstring_headline(cls)
            info[cls.name] = {
                'aliases': cls.aliases,
                'filenames': cls.filenames,
                'doc': doc
            }
        result['formatters'] = info

    if 'filter' in requested_items:
        info = {}
        for name in get_all_filters():
            cls = find_filter_class(name)
            info[name] = {
                'doc': docstring_headline(cls)
            }
        result['filters'] = info

    if 'style' in requested_items:
        info = {}
        for name in get_all_styles():
            cls = get_style_by_name(name)
            info[name] = {
                'doc': docstring_headline(cls)
            }
        result['styles'] = info

    json.dump(result, sys.stdout)

def main_inner(parser, argns):
    if argns.help:
        parser.print_help()
        return 0

    if argns.V:
        print(f'Pygments version {__version__}, (c) 2006-2024 by Georg Brandl, Matthäus '
              'Chajdas and contributors.')
        return 0

    def is_only_option(opt):
        return not any(v for (k, v) in vars(argns).items() if k != opt)

    # handle ``pygmentize -L``
    if argns.L is not None:
        arg_set = set()
        for k, v in vars(argns).items():
            if v:
                arg_set.add(k)

        arg_set.discard('L')
        arg_set.discard('json')

        if arg_set:
            parser.print_help(sys.stderr)
            return 2

        # print version
        if not argns.json:
            main(['', '-V'])
        allowed_types = {'lexer', 'formatter', 'filter', 'style'}
        largs = [arg.rstrip('s') for arg in argns.L]
        if any(arg not in allowed_types for arg in largs):
            parser.print_help(sys.stderr)
            return 0
        if not largs:
            largs = allowed_types
        if not argns.json:
            for arg in largs:
                _print_list(arg)
        else:
            _print_list_as_json(largs)
        return 0

    # handle ``pygmentize -H``
    if argns.H:
        if not is_only_option('H'):
            parser.print_help(sys.stderr)
            return 2
        what, name = argns.H
        if what not in ('lexer', 'formatter', 'filter'):
            parser.print_help(sys.stderr)
            return 2
        return _print_help(what, name)

    # parse -O options
    parsed_opts = _parse_options(argns.O or [])

    # parse -P options
    for p_opt in argns.P or []:
        try:
            name, value = p_opt.split('=', 1)
        except ValueError:
            parsed_opts[p_opt] = True
        else:
            parsed_opts[name] = value

    # encodings
    inencoding = parsed_opts.get('inencoding', parsed_opts.get('encoding'))
    outencoding = parsed_opts.get('outencoding', parsed_opts.get('encoding'))

    # handle ``pygmentize -N``
    if argns.N:
        lexer = find_lexer_class_for_filename(argns.N)
        if lexer is None:
            lexer = TextLexer

        print(lexer.aliases[0])
        return 0

    # handle ``pygmentize -C``
    if argns.C:
        inp = sys.stdin.buffer.read()
        try:
            lexer = guess_lexer(inp, inencoding=inencoding)
        except ClassNotFound:
            lexer = TextLexer

        print(lexer.aliases[0])
        return 0

    # handle ``pygmentize -S``
    S_opt = argns.S
    a_opt = argns.a
    if S_opt is not None:
        f_opt = argns.f
        if not f_opt:
            parser.print_help(sys.stderr)
            return 2
        if argns.l or argns.INPUTFILE:
            parser.print_help(sys.stderr)
            return 2

        try:
            parsed_opts['style'] = S_opt
            fmter = get_formatter_by_name(f_opt, **parsed_opts)
        except ClassNotFound as err:
            print(err, file=sys.stderr)
            return 1

        print(fmter.get_style_defs(a_opt or ''))
        return 0

    # if no -S is given, -a is not allowed
    if argns.a is not None:
        parser.print_help(sys.stderr)
        return 2

    # parse -F options
    F_opts = _parse_filters(argns.F or [])

    # -x: allow custom (eXternal) lexers and formatters
    allow_custom_lexer_formatter = bool(argns.x)

    # select lexer
    lexer = None

    # given by name?
    lexername = argns.l
    if lexername:
        # custom lexer, located relative to user's cwd
        if allow_custom_lexer_formatter and '.py' in lexername:
            try:
                filename = None
                name = None
                if ':' in lexername:
                    filename, name = lexername.rsplit(':', 1)

                    if '.py' in name:
                        # This can happen on Windows: If the lexername is
                        # C:\lexer.py -- return to normal load path in that case
                        name = None

                if filename and name:
                    lexer = load_lexer_from_file(filename, name,
                                                 **parsed_opts)
                else:
                    lexer = load_lexer_from_file(lexername, **parsed_opts)
            except ClassNotFound as err:
                print('Error:', err, file=sys.stderr)
                return 1
        else:
            try:
                lexer = get_lexer_by_name(lexername, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1

    # read input code
    code = None

    if argns.INPUTFILE:
        if argns.s:
            print('Error: -s option not usable when input file specified',
                  file=sys.stderr)
            return 2

        infn = argns.INPUTFILE
        try:
            with open(infn, 'rb') as infp:
                code = infp.read()
        except Exception as err:
            print('Error: cannot read infile:', err, file=sys.stderr)
            return 1
        if not inencoding:
            code, inencoding = guess_decode(code)

        # do we have to guess the lexer?
        if not lexer:
            try:
                lexer = get_lexer_for_filename(infn, code, **parsed_opts)
            except ClassNotFound as err:
                if argns.g:
                    try:
                        lexer = guess_lexer(code, **parsed_opts)
                    except ClassNotFound:
                        lexer = TextLexer(**parsed_opts)
                else:
                    print('Error:', err, file=sys.stderr)
                    return 1
            except OptionError as err:
                print('Error:', err, file=sys.stderr)
                return 1

    elif not argns.s:  # treat stdin as full file (-s support is later)
        # read code from terminal, always in binary mode since we want to
        # decode ourselves and be tolerant with it
        code = sys.stdin.buffer.read()  # use .buffer to get a binary stream
        if not inencoding:
            code, inencoding = guess_decode_from_terminal(code, sys.stdin)
            # else the lexer will do the decoding
        if not lexer:
            try:
                lexer = guess_lexer(code, **parsed_opts)
            except ClassNotFound:
                lexer = TextLexer(**parsed_opts)

    else:  # -s option needs a lexer with -l
        if not lexer:
            print('Error: when using -s a lexer has to be selected with -l',
                  file=sys.stderr)
            return 2

    # process filters
    for fname, fopts in F_opts:
        try:
            lexer.add_filter(fname, **fopts)
        except ClassNotFound as err:
            print('Error:', err, file=sys.stderr)
            return 1

    # select formatter
    outfn = argns.o
    fmter = argns.f
    if fmter:
        # custom formatter, located relative to user's cwd
        if allow_custom_lexer_formatter and '.py' in fmter:
            try:
                filename = None
                name = None
                if ':' in fmter:
                    # Same logic as above for custom lexer
                    filename, name = fmter.rsplit(':', 1)

                    if '.py' in name:
                        name = None

                if filename and name:
                    fmter = load_formatter_from_file(filename, name,
                                                     **parsed_opts)
                else:
                    fmter = load_formatter_from_file(fmter, **parsed_opts)
            except ClassNotFound as err:
                print('Error:', err, file=sys.stderr)
                return 1
        else:
            try:
                fmter = get_formatter_by_name(fmter, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1

    if outfn:
        if not fmter:
            try:
                fmter = get_formatter_for_filename(outfn, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1
        try:
            outfile = open(outfn, 'wb')
        except Exception as err:
            print('Error: cannot open outfile:', err, file=sys.stderr)
            return 1
    else:
        if not fmter:
            if os.environ.get('COLORTERM','') in ('truecolor', '24bit'):
                fmter = TerminalTrueColorFormatter(**parsed_opts)
            elif '256' in os.environ.get('TERM', ''):
                fmter = Terminal256Formatter(**parsed_opts)
            else:
                fmter = TerminalFormatter(**parsed_opts)
        outfile = sys.stdout.buffer

    # determine output encoding if not explicitly selected
    if not outencoding:
        if outfn:
            # output file? use lexer encoding for now (can still be None)
            fmter.encoding = inencoding
        else:
            # else use terminal encoding
            fmter.encoding = terminal_encoding(sys.stdout)

    # provide coloring under Windows, if possible
    if not outfn and sys.platform in ('win32', 'cygwin') and \
       fmter.name in ('Terminal', 'Terminal256'):  # pragma: no cover
        # unfortunately colorama doesn't support binary streams on Py3
        outfile = UnclosingTextIOWrapper(outfile, encoding=fmter.encoding)
        fmter.encoding = None
        try:
            import colorama.initialise
        except ImportError:
            pass
        else:
            outfile = colorama.initialise.wrap_stream(
                outfile, convert=None, strip=None, autoreset=False, wrap=True)

    # When using the LaTeX formatter and the option `escapeinside` is
    # specified, we need a special lexer which collects escaped text
    # before running the chosen language lexer.
    escapeinside = parsed_opts.get('escapeinside', '')
    if len(escapeinside) == 2 and isinstance(fmter, LatexFormatter):
        left = escapeinside[0]
        right = escapeinside[1]
        lexer = LatexEmbeddedLexer(left, right, lexer)

    # ... and do it!
    if not argns.s:
        # process whole input as per normal...
        try:
            highlight(code, lexer, fmter, outfile)
        finally:
            if outfn:
                outfile.close()
        return 0
    else:
        # line by line processing of stdin (eg: for 'tail -f')...
        try:
            while 1:
                line = sys.stdin.buffer.readline()
                if not line:
                    break
                if not inencoding:
                    line = guess_decode_from_terminal(line, sys.stdin)[0]
                highlight(line, lexer, fmter, outfile)
                if hasattr(outfile, 'flush'):
                    outfile.flush()
            return 0
        except KeyboardInterrupt:  # pragma: no cover
            return 0
        finally:
            if outfn:
                outfile.close()


class HelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog, indent_increment=2, max_help_position=16, width=None):
        if width is None:
            try:
                width = shutil.get_terminal_size().columns - 2
            except Exception:
                pass
        argparse.HelpFormatter.__init__(self, prog, indent_increment,
                                        max_help_position, width)


def main(args=sys.argv):
    """
    Main command line entry point.
    """
    desc = "Highlight an input file and write the result to an output file."
    parser = argparse.ArgumentParser(description=desc, add_help=False,
                                     formatter_class=HelpFormatter)

    operation = parser.add_argument_group('Main operation')
    lexersel = operation.add_mutually_exclusive_group()
    lexersel.add_argument(
        '-l', metavar='LEXER',
        help='Specify the lexer to use.  (Query names with -L.)  If not '
        'given and -g is not present, the lexer is guessed from the filename.')
    lexersel.add_argument(
        '-g', action='store_true',
        help='Guess the lexer from the file contents, or pass through '
        'as plain text if nothing can be guessed.')
    operation.add_argument(
        '-F', metavar='FILTER[:options]', action='append',
        help='Add a filter to the token stream.  (Query names with -L.) '
        'Filter options are given after a colon if necessary.')
    operation.add_argument(
        '-f', metavar='FORMATTER',
        help='Specify the formatter to use.  (Query names with -L.) '
        'If not given, the formatter is guessed from the output filename, '
        'and defaults to the terminal formatter if the output is to the '
        'terminal or an unknown file extension.')
    operation.add_argument(
        '-O', metavar='OPTION=value[,OPTION=value,...]', action='append',
        help='Give options to the lexer and formatter as a comma-separated '
        'list of key-value pairs. '
        'Example: `-O bg=light,python=cool`.')
    operation.add_argument(
        '-P', metavar='OPTION=value', action='append',
        help='Give a single option to the lexer and formatter - with this '
        'you can pass options whose value contains commas and equal signs. '
        'Example: `-P "heading=Pygments, the Python highlighter"`.')
    operation.add_argument(
        '-o', metavar='OUTPUTFILE',
        help='Where to write the output.  Defaults to standard output.')

    operation.add_argument(
        'INPUTFILE', nargs='?',
        help='Where to read the input.  Defaults to standard input.')

    flags = parser.add_argument_group('Operation flags')
    flags.add_argument(
        '-v', action='store_true',
        help='Print a detailed traceback on unhandled exceptions, which '
        'is useful for debugging and bug reports.')
    flags.add_argument(
        '-s', action='store_true',
        help='Process lines one at a time until EOF, rather than waiting to '
        'process the entire file.  This only works for stdin, only for lexers '
        'with no line-spanning constructs, and is intended for streaming '
        'input such as you get from `tail -f`. '
        'Example usage: `tail -f sql.log | pygmentize -s -l sql`.')
    flags.add_argument(
        '-x', action='store_true',
        help='Allow custom lexers and formatters to be loaded from a .py file '
        'relative to the current working directory. For example, '
        '`-l ./customlexer.py -x`. By default, this option expects a file '
        'with a class named CustomLexer or CustomFormatter; you can also '
        'specify your own class name with a colon (`-l ./lexer.py:MyLexer`). '
        'Users should be very careful not to use this option with untrusted '
        'files, because it will import and run them.')
    flags.add_argument('--json', help='Output as JSON. This can '
        'be only used in conjunction with -L.',
        default=False,
        action='store_true')

    special_modes_group = parser.add_argument_group(
        'Special modes - do not do any highlighting')
    special_modes = special_modes_group.add_mutually_exclusive_group()
    special_modes.add_argument(
        '-S', metavar='STYLE -f formatter',
        help='Print style definitions for STYLE for a formatter '
        'given with -f. The argument given by -a is formatter '
        'dependent.')
    special_modes.add_argument(
        '-L', nargs='*', metavar='WHAT',
        help='List lexers, formatters, styles or filters -- '
        'give additional arguments for the thing(s) you want to list '
        '(e.g. "styles"), or omit them to list everything.')
    special_modes.add_argument(
        '-N', metavar='FILENAME',
        help='Guess and print out a lexer name based solely on the given '
        'filename. Does not take input or highlight anything. If no specific '
        'lexer can be determined, "text" is printed.')
    special_modes.add_argument(
        '-C', action='store_true',
        help='Like -N, but print out a lexer name based solely on '
        'a given content from standard input.')
    special_modes.add_argument(
        '-H', action='store', nargs=2, metavar=('NAME', 'TYPE'),
        help='Print detailed help for the object <name> of type <type>, '
        'where <type> is one of "lexer", "formatter" or "filter".')
    special_modes.add_argument(
        '-V', action='store_true',
        help='Print the package version.')
    special_modes.add_argument(
        '-h', '--help', action='store_true',
        help='Print this help.')
    special_modes_group.add_argument(
        '-a', metavar='ARG',
        help='Formatter-specific additional argument for the -S (print '
        'style sheet) mode.')

    argns = parser.parse_args(args[1:])

    try:
        return main_inner(parser, argns)
    except BrokenPipeError:
        # someone closed our stdout, e.g. by quitting a pager.
        return 0
    except Exception:
        if argns.v:
            print(file=sys.stderr)
            print('*' * 65, file=sys.stderr)
            print('An unhandled exception occurred while highlighting.',
                  file=sys.stderr)
            print('Please report the whole traceback to the issue tracker at',
                  file=sys.stderr)
            print('<https://github.com/pygments/pygments/issues>.',
                  file=sys.stderr)
            print('*' * 65, file=sys.stderr)
            print(file=sys.stderr)
            raise
        import traceback
        info = traceback.format_exception(*sys.exc_info())
        msg = info[-1].strip()
        if len(info) >= 3:
            # extract relevant file and position info
            msg += '\n   (f{})'.format(info[-2].split('\n')[0].strip()[1:])
        print(file=sys.stderr)
        print('*** Error while highlighting:', file=sys.stderr)
        print(msg, file=sys.stderr)
        print('*** If this is a bug you want to report, please rerun with -v.',
              file=sys.stderr)
        return 1

# === NexusCore/openenv\Lib\site-packages\pydantic\experimental\pipeline.py ===
"""Experimental pipeline API functionality. Be careful with this API, it's subject to change."""

from __future__ import annotations

import datetime
import operator
import re
import sys
from collections import deque
from collections.abc import Container
from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property, partial
from re import Pattern
from typing import TYPE_CHECKING, Annotated, Any, Callable, Generic, Protocol, TypeVar, Union, overload

import annotated_types

if TYPE_CHECKING:
    from pydantic_core import core_schema as cs

    from pydantic import GetCoreSchemaHandler

from pydantic._internal._internal_dataclass import slots_true as _slots_true

if sys.version_info < (3, 10):
    EllipsisType = type(Ellipsis)
else:
    from types import EllipsisType

__all__ = ['validate_as', 'validate_as_deferred', 'transform']

_slots_frozen = {**_slots_true, 'frozen': True}


@dataclass(**_slots_frozen)
class _ValidateAs:
    tp: type[Any]
    strict: bool = False


@dataclass
class _ValidateAsDefer:
    func: Callable[[], type[Any]]

    @cached_property
    def tp(self) -> type[Any]:
        return self.func()


@dataclass(**_slots_frozen)
class _Transform:
    func: Callable[[Any], Any]


@dataclass(**_slots_frozen)
class _PipelineOr:
    left: _Pipeline[Any, Any]
    right: _Pipeline[Any, Any]


@dataclass(**_slots_frozen)
class _PipelineAnd:
    left: _Pipeline[Any, Any]
    right: _Pipeline[Any, Any]


@dataclass(**_slots_frozen)
class _Eq:
    value: Any


@dataclass(**_slots_frozen)
class _NotEq:
    value: Any


@dataclass(**_slots_frozen)
class _In:
    values: Container[Any]


@dataclass(**_slots_frozen)
class _NotIn:
    values: Container[Any]


_ConstraintAnnotation = Union[
    annotated_types.Le,
    annotated_types.Ge,
    annotated_types.Lt,
    annotated_types.Gt,
    annotated_types.Len,
    annotated_types.MultipleOf,
    annotated_types.Timezone,
    annotated_types.Interval,
    annotated_types.Predicate,
    # common predicates not included in annotated_types
    _Eq,
    _NotEq,
    _In,
    _NotIn,
    # regular expressions
    Pattern[str],
]


@dataclass(**_slots_frozen)
class _Constraint:
    constraint: _ConstraintAnnotation


_Step = Union[_ValidateAs, _ValidateAsDefer, _Transform, _PipelineOr, _PipelineAnd, _Constraint]

_InT = TypeVar('_InT')
_OutT = TypeVar('_OutT')
_NewOutT = TypeVar('_NewOutT')


class _FieldTypeMarker:
    pass


# TODO: ultimately, make this public, see https://github.com/pydantic/pydantic/pull/9459#discussion_r1628197626
# Also, make this frozen eventually, but that doesn't work right now because of the generic base
# Which attempts to modify __orig_base__ and such.
# We could go with a manual freeze, but that seems overkill for now.
@dataclass(**_slots_true)
class _Pipeline(Generic[_InT, _OutT]):
    """Abstract representation of a chain of validation, transformation, and parsing steps."""

    _steps: tuple[_Step, ...]

    def transform(
        self,
        func: Callable[[_OutT], _NewOutT],
    ) -> _Pipeline[_InT, _NewOutT]:
        """Transform the output of the previous step.

        If used as the first step in a pipeline, the type of the field is used.
        That is, the transformation is applied to after the value is parsed to the field's type.
        """
        return _Pipeline[_InT, _NewOutT](self._steps + (_Transform(func),))

    @overload
    def validate_as(self, tp: type[_NewOutT], *, strict: bool = ...) -> _Pipeline[_InT, _NewOutT]: ...

    @overload
    def validate_as(self, tp: EllipsisType, *, strict: bool = ...) -> _Pipeline[_InT, Any]:  # type: ignore
        ...

    def validate_as(self, tp: type[_NewOutT] | EllipsisType, *, strict: bool = False) -> _Pipeline[_InT, Any]:  # type: ignore
        """Validate / parse the input into a new type.

        If no type is provided, the type of the field is used.

        Types are parsed in Pydantic's `lax` mode by default,
        but you can enable `strict` mode by passing `strict=True`.
        """
        if isinstance(tp, EllipsisType):
            return _Pipeline[_InT, Any](self._steps + (_ValidateAs(_FieldTypeMarker, strict=strict),))
        return _Pipeline[_InT, _NewOutT](self._steps + (_ValidateAs(tp, strict=strict),))

    def validate_as_deferred(self, func: Callable[[], type[_NewOutT]]) -> _Pipeline[_InT, _NewOutT]:
        """Parse the input into a new type, deferring resolution of the type until the current class
        is fully defined.

        This is useful when you need to reference the class in it's own type annotations.
        """
        return _Pipeline[_InT, _NewOutT](self._steps + (_ValidateAsDefer(func),))

    # constraints
    @overload
    def constrain(self: _Pipeline[_InT, _NewOutGe], constraint: annotated_types.Ge) -> _Pipeline[_InT, _NewOutGe]: ...

    @overload
    def constrain(self: _Pipeline[_InT, _NewOutGt], constraint: annotated_types.Gt) -> _Pipeline[_InT, _NewOutGt]: ...

    @overload
    def constrain(self: _Pipeline[_InT, _NewOutLe], constraint: annotated_types.Le) -> _Pipeline[_InT, _NewOutLe]: ...

    @overload
    def constrain(self: _Pipeline[_InT, _NewOutLt], constraint: annotated_types.Lt) -> _Pipeline[_InT, _NewOutLt]: ...

    @overload
    def constrain(
        self: _Pipeline[_InT, _NewOutLen], constraint: annotated_types.Len
    ) -> _Pipeline[_InT, _NewOutLen]: ...

    @overload
    def constrain(
        self: _Pipeline[_InT, _NewOutT], constraint: annotated_types.MultipleOf
    ) -> _Pipeline[_InT, _NewOutT]: ...

    @overload
    def constrain(
        self: _Pipeline[_InT, _NewOutDatetime], constraint: annotated_types.Timezone
    ) -> _Pipeline[_InT, _NewOutDatetime]: ...

    @overload
    def constrain(self: _Pipeline[_InT, _OutT], constraint: annotated_types.Predicate) -> _Pipeline[_InT, _OutT]: ...

    @overload
    def constrain(
        self: _Pipeline[_InT, _NewOutInterval], constraint: annotated_types.Interval
    ) -> _Pipeline[_InT, _NewOutInterval]: ...

    @overload
    def constrain(self: _Pipeline[_InT, _OutT], constraint: _Eq) -> _Pipeline[_InT, _OutT]: ...

    @overload
    def constrain(self: _Pipeline[_InT, _OutT], constraint: _NotEq) -> _Pipeline[_InT, _OutT]: ...

    @overload
    def constrain(self: _Pipeline[_InT, _OutT], constraint: _In) -> _Pipeline[_InT, _OutT]: ...

    @overload
    def constrain(self: _Pipeline[_InT, _OutT], constraint: _NotIn) -> _Pipeline[_InT, _OutT]: ...

    @overload
    def constrain(self: _Pipeline[_InT, _NewOutT], constraint: Pattern[str]) -> _Pipeline[_InT, _NewOutT]: ...

    def constrain(self, constraint: _ConstraintAnnotation) -> Any:
        """Constrain a value to meet a certain condition.

        We support most conditions from `annotated_types`, as well as regular expressions.

        Most of the time you'll be calling a shortcut method like `gt`, `lt`, `len`, etc
        so you don't need to call this directly.
        """
        return _Pipeline[_InT, _OutT](self._steps + (_Constraint(constraint),))

    def predicate(self: _Pipeline[_InT, _NewOutT], func: Callable[[_NewOutT], bool]) -> _Pipeline[_InT, _NewOutT]:
        """Constrain a value to meet a certain predicate."""
        return self.constrain(annotated_types.Predicate(func))

    def gt(self: _Pipeline[_InT, _NewOutGt], gt: _NewOutGt) -> _Pipeline[_InT, _NewOutGt]:
        """Constrain a value to be greater than a certain value."""
        return self.constrain(annotated_types.Gt(gt))

    def lt(self: _Pipeline[_InT, _NewOutLt], lt: _NewOutLt) -> _Pipeline[_InT, _NewOutLt]:
        """Constrain a value to be less than a certain value."""
        return self.constrain(annotated_types.Lt(lt))

    def ge(self: _Pipeline[_InT, _NewOutGe], ge: _NewOutGe) -> _Pipeline[_InT, _NewOutGe]:
        """Constrain a value to be greater than or equal to a certain value."""
        return self.constrain(annotated_types.Ge(ge))

    def le(self: _Pipeline[_InT, _NewOutLe], le: _NewOutLe) -> _Pipeline[_InT, _NewOutLe]:
        """Constrain a value to be less than or equal to a certain value."""
        return self.constrain(annotated_types.Le(le))

    def len(self: _Pipeline[_InT, _NewOutLen], min_len: int, max_len: int | None = None) -> _Pipeline[_InT, _NewOutLen]:
        """Constrain a value to have a certain length."""
        return self.constrain(annotated_types.Len(min_len, max_len))

    @overload
    def multiple_of(self: _Pipeline[_InT, _NewOutDiv], multiple_of: _NewOutDiv) -> _Pipeline[_InT, _NewOutDiv]: ...

    @overload
    def multiple_of(self: _Pipeline[_InT, _NewOutMod], multiple_of: _NewOutMod) -> _Pipeline[_InT, _NewOutMod]: ...

    def multiple_of(self: _Pipeline[_InT, Any], multiple_of: Any) -> _Pipeline[_InT, Any]:
        """Constrain a value to be a multiple of a certain number."""
        return self.constrain(annotated_types.MultipleOf(multiple_of))

    def eq(self: _Pipeline[_InT, _OutT], value: _OutT) -> _Pipeline[_InT, _OutT]:
        """Constrain a value to be equal to a certain value."""
        return self.constrain(_Eq(value))

    def not_eq(self: _Pipeline[_InT, _OutT], value: _OutT) -> _Pipeline[_InT, _OutT]:
        """Constrain a value to not be equal to a certain value."""
        return self.constrain(_NotEq(value))

    def in_(self: _Pipeline[_InT, _OutT], values: Container[_OutT]) -> _Pipeline[_InT, _OutT]:
        """Constrain a value to be in a certain set."""
        return self.constrain(_In(values))

    def not_in(self: _Pipeline[_InT, _OutT], values: Container[_OutT]) -> _Pipeline[_InT, _OutT]:
        """Constrain a value to not be in a certain set."""
        return self.constrain(_NotIn(values))

    # timezone methods
    def datetime_tz_naive(self: _Pipeline[_InT, datetime.datetime]) -> _Pipeline[_InT, datetime.datetime]:
        return self.constrain(annotated_types.Timezone(None))

    def datetime_tz_aware(self: _Pipeline[_InT, datetime.datetime]) -> _Pipeline[_InT, datetime.datetime]:
        return self.constrain(annotated_types.Timezone(...))

    def datetime_tz(
        self: _Pipeline[_InT, datetime.datetime], tz: datetime.tzinfo
    ) -> _Pipeline[_InT, datetime.datetime]:
        return self.constrain(annotated_types.Timezone(tz))  # type: ignore

    def datetime_with_tz(
        self: _Pipeline[_InT, datetime.datetime], tz: datetime.tzinfo | None
    ) -> _Pipeline[_InT, datetime.datetime]:
        return self.transform(partial(datetime.datetime.replace, tzinfo=tz))

    # string methods
    def str_lower(self: _Pipeline[_InT, str]) -> _Pipeline[_InT, str]:
        return self.transform(str.lower)

    def str_upper(self: _Pipeline[_InT, str]) -> _Pipeline[_InT, str]:
        return self.transform(str.upper)

    def str_title(self: _Pipeline[_InT, str]) -> _Pipeline[_InT, str]:
        return self.transform(str.title)

    def str_strip(self: _Pipeline[_InT, str]) -> _Pipeline[_InT, str]:
        return self.transform(str.strip)

    def str_pattern(self: _Pipeline[_InT, str], pattern: str) -> _Pipeline[_InT, str]:
        return self.constrain(re.compile(pattern))

    def str_contains(self: _Pipeline[_InT, str], substring: str) -> _Pipeline[_InT, str]:
        return self.predicate(lambda v: substring in v)

    def str_starts_with(self: _Pipeline[_InT, str], prefix: str) -> _Pipeline[_InT, str]:
        return self.predicate(lambda v: v.startswith(prefix))

    def str_ends_with(self: _Pipeline[_InT, str], suffix: str) -> _Pipeline[_InT, str]:
        return self.predicate(lambda v: v.endswith(suffix))

    # operators
    def otherwise(self, other: _Pipeline[_OtherIn, _OtherOut]) -> _Pipeline[_InT | _OtherIn, _OutT | _OtherOut]:
        """Combine two validation chains, returning the result of the first chain if it succeeds, and the second chain if it fails."""
        return _Pipeline((_PipelineOr(self, other),))

    __or__ = otherwise

    def then(self, other: _Pipeline[_OutT, _OtherOut]) -> _Pipeline[_InT, _OtherOut]:
        """Pipe the result of one validation chain into another."""
        return _Pipeline((_PipelineAnd(self, other),))

    __and__ = then

    def __get_pydantic_core_schema__(self, source_type: Any, handler: GetCoreSchemaHandler) -> cs.CoreSchema:
        from pydantic_core import core_schema as cs

        queue = deque(self._steps)

        s = None

        while queue:
            step = queue.popleft()
            s = _apply_step(step, s, handler, source_type)

        s = s or cs.any_schema()
        return s

    def __supports_type__(self, _: _OutT) -> bool:
        raise NotImplementedError


validate_as = _Pipeline[Any, Any](()).validate_as
validate_as_deferred = _Pipeline[Any, Any](()).validate_as_deferred
transform = _Pipeline[Any, Any]((_ValidateAs(_FieldTypeMarker),)).transform


def _check_func(
    func: Callable[[Any], bool], predicate_err: str | Callable[[], str], s: cs.CoreSchema | None
) -> cs.CoreSchema:
    from pydantic_core import core_schema as cs

    def handler(v: Any) -> Any:
        if func(v):
            return v
        raise ValueError(f'Expected {predicate_err if isinstance(predicate_err, str) else predicate_err()}')

    if s is None:
        return cs.no_info_plain_validator_function(handler)
    else:
        return cs.no_info_after_validator_function(handler, s)


def _apply_step(step: _Step, s: cs.CoreSchema | None, handler: GetCoreSchemaHandler, source_type: Any) -> cs.CoreSchema:
    from pydantic_core import core_schema as cs

    if isinstance(step, _ValidateAs):
        s = _apply_parse(s, step.tp, step.strict, handler, source_type)
    elif isinstance(step, _ValidateAsDefer):
        s = _apply_parse(s, step.tp, False, handler, source_type)
    elif isinstance(step, _Transform):
        s = _apply_transform(s, step.func, handler)
    elif isinstance(step, _Constraint):
        s = _apply_constraint(s, step.constraint)
    elif isinstance(step, _PipelineOr):
        s = cs.union_schema([handler(step.left), handler(step.right)])
    else:
        assert isinstance(step, _PipelineAnd)
        s = cs.chain_schema([handler(step.left), handler(step.right)])
    return s


def _apply_parse(
    s: cs.CoreSchema | None,
    tp: type[Any],
    strict: bool,
    handler: GetCoreSchemaHandler,
    source_type: Any,
) -> cs.CoreSchema:
    from pydantic_core import core_schema as cs

    from pydantic import Strict

    if tp is _FieldTypeMarker:
        return cs.chain_schema([s, handler(source_type)]) if s else handler(source_type)

    if strict:
        tp = Annotated[tp, Strict()]  # type: ignore

    if s and s['type'] == 'any':
        return handler(tp)
    else:
        return cs.chain_schema([s, handler(tp)]) if s else handler(tp)


def _apply_transform(
    s: cs.CoreSchema | None, func: Callable[[Any], Any], handler: GetCoreSchemaHandler
) -> cs.CoreSchema:
    from pydantic_core import core_schema as cs

    if s is None:
        return cs.no_info_plain_validator_function(func)

    if s['type'] == 'str':
        if func is str.strip:
            s = s.copy()
            s['strip_whitespace'] = True
            return s
        elif func is str.lower:
            s = s.copy()
            s['to_lower'] = True
            return s
        elif func is str.upper:
            s = s.copy()
            s['to_upper'] = True
            return s

    return cs.no_info_after_validator_function(func, s)


def _apply_constraint(  # noqa: C901
    s: cs.CoreSchema | None, constraint: _ConstraintAnnotation
) -> cs.CoreSchema:
    """Apply a single constraint to a schema."""
    if isinstance(constraint, annotated_types.Gt):
        gt = constraint.gt
        if s and s['type'] in {'int', 'float', 'decimal'}:
            s = s.copy()
            if s['type'] == 'int' and isinstance(gt, int):
                s['gt'] = gt
            elif s['type'] == 'float' and isinstance(gt, float):
                s['gt'] = gt
            elif s['type'] == 'decimal' and isinstance(gt, Decimal):
                s['gt'] = gt
        else:

            def check_gt(v: Any) -> bool:
                return v > gt

            s = _check_func(check_gt, f'> {gt}', s)
    elif isinstance(constraint, annotated_types.Ge):
        ge = constraint.ge
        if s and s['type'] in {'int', 'float', 'decimal'}:
            s = s.copy()
            if s['type'] == 'int' and isinstance(ge, int):
                s['ge'] = ge
            elif s['type'] == 'float' and isinstance(ge, float):
                s['ge'] = ge
            elif s['type'] == 'decimal' and isinstance(ge, Decimal):
                s['ge'] = ge

        def check_ge(v: Any) -> bool:
            return v >= ge

        s = _check_func(check_ge, f'>= {ge}', s)
    elif isinstance(constraint, annotated_types.Lt):
        lt = constraint.lt
        if s and s['type'] in {'int', 'float', 'decimal'}:
            s = s.copy()
            if s['type'] == 'int' and isinstance(lt, int):
                s['lt'] = lt
            elif s['type'] == 'float' and isinstance(lt, float):
                s['lt'] = lt
            elif s['type'] == 'decimal' and isinstance(lt, Decimal):
                s['lt'] = lt

        def check_lt(v: Any) -> bool:
            return v < lt

        s = _check_func(check_lt, f'< {lt}', s)
    elif isinstance(constraint, annotated_types.Le):
        le = constraint.le
        if s and s['type'] in {'int', 'float', 'decimal'}:
            s = s.copy()
            if s['type'] == 'int' and isinstance(le, int):
                s['le'] = le
            elif s['type'] == 'float' and isinstance(le, float):
                s['le'] = le
            elif s['type'] == 'decimal' and isinstance(le, Decimal):
                s['le'] = le

        def check_le(v: Any) -> bool:
            return v <= le

        s = _check_func(check_le, f'<= {le}', s)
    elif isinstance(constraint, annotated_types.Len):
        min_len = constraint.min_length
        max_len = constraint.max_length

        if s and s['type'] in {'str', 'list', 'tuple', 'set', 'frozenset', 'dict'}:
            assert (
                s['type'] == 'str'
                or s['type'] == 'list'
                or s['type'] == 'tuple'
                or s['type'] == 'set'
                or s['type'] == 'dict'
                or s['type'] == 'frozenset'
            )
            s = s.copy()
            if min_len != 0:
                s['min_length'] = min_len
            if max_len is not None:
                s['max_length'] = max_len

        def check_len(v: Any) -> bool:
            if max_len is not None:
                return (min_len <= len(v)) and (len(v) <= max_len)
            return min_len <= len(v)

        s = _check_func(check_len, f'length >= {min_len} and length <= {max_len}', s)
    elif isinstance(constraint, annotated_types.MultipleOf):
        multiple_of = constraint.multiple_of
        if s and s['type'] in {'int', 'float', 'decimal'}:
            s = s.copy()
            if s['type'] == 'int' and isinstance(multiple_of, int):
                s['multiple_of'] = multiple_of
            elif s['type'] == 'float' and isinstance(multiple_of, float):
                s['multiple_of'] = multiple_of
            elif s['type'] == 'decimal' and isinstance(multiple_of, Decimal):
                s['multiple_of'] = multiple_of

        def check_multiple_of(v: Any) -> bool:
            return v % multiple_of == 0

        s = _check_func(check_multiple_of, f'% {multiple_of} == 0', s)
    elif isinstance(constraint, annotated_types.Timezone):
        tz = constraint.tz

        if tz is ...:
            if s and s['type'] == 'datetime':
                s = s.copy()
                s['tz_constraint'] = 'aware'
            else:

                def check_tz_aware(v: object) -> bool:
                    assert isinstance(v, datetime.datetime)
                    return v.tzinfo is not None

                s = _check_func(check_tz_aware, 'timezone aware', s)
        elif tz is None:
            if s and s['type'] == 'datetime':
                s = s.copy()
                s['tz_constraint'] = 'naive'
            else:

                def check_tz_naive(v: object) -> bool:
                    assert isinstance(v, datetime.datetime)
                    return v.tzinfo is None

                s = _check_func(check_tz_naive, 'timezone naive', s)
        else:
            raise NotImplementedError('Constraining to a specific timezone is not yet supported')
    elif isinstance(constraint, annotated_types.Interval):
        if constraint.ge:
            s = _apply_constraint(s, annotated_types.Ge(constraint.ge))
        if constraint.gt:
            s = _apply_constraint(s, annotated_types.Gt(constraint.gt))
        if constraint.le:
            s = _apply_constraint(s, annotated_types.Le(constraint.le))
        if constraint.lt:
            s = _apply_constraint(s, annotated_types.Lt(constraint.lt))
        assert s is not None
    elif isinstance(constraint, annotated_types.Predicate):
        func = constraint.func

        if func.__name__ == '<lambda>':
            # attempt to extract the source code for a lambda function
            # to use as the function name in error messages
            # TODO: is there a better way? should we just not do this?
            import inspect

            try:
                source = inspect.getsource(func).strip()
                source = source.removesuffix(')')
                lambda_source_code = '`' + ''.join(''.join(source.split('lambda ')[1:]).split(':')[1:]).strip() + '`'
            except OSError:
                # stringified annotations
                lambda_source_code = 'lambda'

            s = _check_func(func, lambda_source_code, s)
        else:
            s = _check_func(func, func.__name__, s)
    elif isinstance(constraint, _NotEq):
        value = constraint.value

        def check_not_eq(v: Any) -> bool:
            return operator.__ne__(v, value)

        s = _check_func(check_not_eq, f'!= {value}', s)
    elif isinstance(constraint, _Eq):
        value = constraint.value

        def check_eq(v: Any) -> bool:
            return operator.__eq__(v, value)

        s = _check_func(check_eq, f'== {value}', s)
    elif isinstance(constraint, _In):
        values = constraint.values

        def check_in(v: Any) -> bool:
            return operator.__contains__(values, v)

        s = _check_func(check_in, f'in {values}', s)
    elif isinstance(constraint, _NotIn):
        values = constraint.values

        def check_not_in(v: Any) -> bool:
            return operator.__not__(operator.__contains__(values, v))

        s = _check_func(check_not_in, f'not in {values}', s)
    else:
        assert isinstance(constraint, Pattern)
        if s and s['type'] == 'str':
            s = s.copy()
            s['pattern'] = constraint.pattern
        else:

            def check_pattern(v: object) -> bool:
                assert isinstance(v, str)
                return constraint.match(v) is not None

            s = _check_func(check_pattern, f'~ {constraint.pattern}', s)
    return s


class _SupportsRange(annotated_types.SupportsLe, annotated_types.SupportsGe, Protocol):
    pass


class _SupportsLen(Protocol):
    def __len__(self) -> int: ...


_NewOutGt = TypeVar('_NewOutGt', bound=annotated_types.SupportsGt)
_NewOutGe = TypeVar('_NewOutGe', bound=annotated_types.SupportsGe)
_NewOutLt = TypeVar('_NewOutLt', bound=annotated_types.SupportsLt)
_NewOutLe = TypeVar('_NewOutLe', bound=annotated_types.SupportsLe)
_NewOutLen = TypeVar('_NewOutLen', bound=_SupportsLen)
_NewOutDiv = TypeVar('_NewOutDiv', bound=annotated_types.SupportsDiv)
_NewOutMod = TypeVar('_NewOutMod', bound=annotated_types.SupportsMod)
_NewOutDatetime = TypeVar('_NewOutDatetime', bound=datetime.datetime)
_NewOutInterval = TypeVar('_NewOutInterval', bound=_SupportsRange)
_OtherIn = TypeVar('_OtherIn')
_OtherOut = TypeVar('_OtherOut')

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\types\generative_service.py ===
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

from google.ai.generativelanguage_v1.types import citation
from google.ai.generativelanguage_v1.types import content as gag_content
from google.ai.generativelanguage_v1.types import safety

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1",
    manifest={
        "TaskType",
        "GenerateContentRequest",
        "GenerationConfig",
        "GenerateContentResponse",
        "Candidate",
        "EmbedContentRequest",
        "ContentEmbedding",
        "EmbedContentResponse",
        "BatchEmbedContentsRequest",
        "BatchEmbedContentsResponse",
        "CountTokensRequest",
        "CountTokensResponse",
    },
)


class TaskType(proto.Enum):
    r"""Type of task for which the embedding will be used.

    Values:
        TASK_TYPE_UNSPECIFIED (0):
            Unset value, which will default to one of the
            other enum values.
        RETRIEVAL_QUERY (1):
            Specifies the given text is a query in a
            search/retrieval setting.
        RETRIEVAL_DOCUMENT (2):
            Specifies the given text is a document from
            the corpus being searched.
        SEMANTIC_SIMILARITY (3):
            Specifies the given text will be used for
            STS.
        CLASSIFICATION (4):
            Specifies that the given text will be
            classified.
        CLUSTERING (5):
            Specifies that the embeddings will be used
            for clustering.
        QUESTION_ANSWERING (6):
            Specifies that the given text will be used
            for question answering.
        FACT_VERIFICATION (7):
            Specifies that the given text will be used
            for fact verification.
    """
    TASK_TYPE_UNSPECIFIED = 0
    RETRIEVAL_QUERY = 1
    RETRIEVAL_DOCUMENT = 2
    SEMANTIC_SIMILARITY = 3
    CLASSIFICATION = 4
    CLUSTERING = 5
    QUESTION_ANSWERING = 6
    FACT_VERIFICATION = 7


class GenerateContentRequest(proto.Message):
    r"""Request to generate a completion from the model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The name of the ``Model`` to use for generating
            the completion.

            Format: ``name=models/{model}``.
        contents (MutableSequence[google.ai.generativelanguage_v1.types.Content]):
            Required. The content of the current
            conversation with the model.
            For single-turn queries, this is a single
            instance. For multi-turn queries, this is a
            repeated field that contains conversation
            history + latest request.
        safety_settings (MutableSequence[google.ai.generativelanguage_v1.types.SafetySetting]):
            Optional. A list of unique ``SafetySetting`` instances for
            blocking unsafe content.

            This will be enforced on the
            ``GenerateContentRequest.contents`` and
            ``GenerateContentResponse.candidates``. There should not be
            more than one setting for each ``SafetyCategory`` type. The
            API will block any contents and responses that fail to meet
            the thresholds set by these settings. This list overrides
            the default settings for each ``SafetyCategory`` specified
            in the safety_settings. If there is no ``SafetySetting`` for
            a given ``SafetyCategory`` provided in the list, the API
            will use the default safety setting for that category. Harm
            categories HARM_CATEGORY_HATE_SPEECH,
            HARM_CATEGORY_SEXUALLY_EXPLICIT,
            HARM_CATEGORY_DANGEROUS_CONTENT, HARM_CATEGORY_HARASSMENT
            are supported.
        generation_config (google.ai.generativelanguage_v1.types.GenerationConfig):
            Optional. Configuration options for model
            generation and outputs.

            This field is a member of `oneof`_ ``_generation_config``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    contents: MutableSequence[gag_content.Content] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )
    safety_settings: MutableSequence[safety.SafetySetting] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message=safety.SafetySetting,
    )
    generation_config: "GenerationConfig" = proto.Field(
        proto.MESSAGE,
        number=4,
        optional=True,
        message="GenerationConfig",
    )


class GenerationConfig(proto.Message):
    r"""Configuration options for model generation and outputs. Not
    all parameters may be configurable for every model.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        candidate_count (int):
            Optional. Number of generated responses to
            return.
            Currently, this value can only be set to 1. If
            unset, this will default to 1.

            This field is a member of `oneof`_ ``_candidate_count``.
        stop_sequences (MutableSequence[str]):
            Optional. The set of character sequences (up
            to 5) that will stop output generation. If
            specified, the API will stop at the first
            appearance of a stop sequence. The stop sequence
            will not be included as part of the response.
        max_output_tokens (int):
            Optional. The maximum number of tokens to include in a
            candidate.

            Note: The default value varies by model, see the
            ``Model.output_token_limit`` attribute of the ``Model``
            returned from the ``getModel`` function.

            This field is a member of `oneof`_ ``_max_output_tokens``.
        temperature (float):
            Optional. Controls the randomness of the output.

            Note: The default value varies by model, see the
            ``Model.temperature`` attribute of the ``Model`` returned
            from the ``getModel`` function.

            Values can range from [0.0, 2.0].

            This field is a member of `oneof`_ ``_temperature``.
        top_p (float):
            Optional. The maximum cumulative probability of tokens to
            consider when sampling.

            The model uses combined Top-k and nucleus sampling.

            Tokens are sorted based on their assigned probabilities so
            that only the most likely tokens are considered. Top-k
            sampling directly limits the maximum number of tokens to
            consider, while Nucleus sampling limits number of tokens
            based on the cumulative probability.

            Note: The default value varies by model, see the
            ``Model.top_p`` attribute of the ``Model`` returned from the
            ``getModel`` function.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            Optional. The maximum number of tokens to consider when
            sampling.

            Models use nucleus sampling or combined Top-k and nucleus
            sampling. Top-k sampling considers the set of ``top_k`` most
            probable tokens. Models running with nucleus sampling don't
            allow top_k setting.

            Note: The default value varies by model, see the
            ``Model.top_k`` attribute of the ``Model`` returned from the
            ``getModel`` function. Empty ``top_k`` field in ``Model``
            indicates the model doesn't apply top-k sampling and doesn't
            allow setting ``top_k`` on requests.

            This field is a member of `oneof`_ ``_top_k``.
    """

    candidate_count: int = proto.Field(
        proto.INT32,
        number=1,
        optional=True,
    )
    stop_sequences: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=2,
    )
    max_output_tokens: int = proto.Field(
        proto.INT32,
        number=4,
        optional=True,
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=5,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=6,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=7,
        optional=True,
    )


class GenerateContentResponse(proto.Message):
    r"""Response from the model supporting multiple candidates.

    Note on safety ratings and content filtering. They are reported for
    both prompt in ``GenerateContentResponse.prompt_feedback`` and for
    each candidate in ``finish_reason`` and in ``safety_ratings``. The
    API contract is that:

    -  either all requested candidates are returned or no candidates at
       all
    -  no candidates are returned only if there was something wrong with
       the prompt (see ``prompt_feedback``)
    -  feedback on each candidate is reported on ``finish_reason`` and
       ``safety_ratings``.

    Attributes:
        candidates (MutableSequence[google.ai.generativelanguage_v1.types.Candidate]):
            Candidate responses from the model.
        prompt_feedback (google.ai.generativelanguage_v1.types.GenerateContentResponse.PromptFeedback):
            Returns the prompt's feedback related to the
            content filters.
        usage_metadata (google.ai.generativelanguage_v1.types.GenerateContentResponse.UsageMetadata):
            Output only. Metadata on the generation
            requests' token usage.
    """

    class PromptFeedback(proto.Message):
        r"""A set of the feedback metadata the prompt specified in
        ``GenerateContentRequest.content``.

        Attributes:
            block_reason (google.ai.generativelanguage_v1.types.GenerateContentResponse.PromptFeedback.BlockReason):
                Optional. If set, the prompt was blocked and
                no candidates are returned. Rephrase your
                prompt.
            safety_ratings (MutableSequence[google.ai.generativelanguage_v1.types.SafetyRating]):
                Ratings for safety of the prompt.
                There is at most one rating per category.
        """

        class BlockReason(proto.Enum):
            r"""Specifies what was the reason why prompt was blocked.

            Values:
                BLOCK_REASON_UNSPECIFIED (0):
                    Default value. This value is unused.
                SAFETY (1):
                    Prompt was blocked due to safety reasons. You can inspect
                    ``safety_ratings`` to understand which safety category
                    blocked it.
                OTHER (2):
                    Prompt was blocked due to unknown reaasons.
            """
            BLOCK_REASON_UNSPECIFIED = 0
            SAFETY = 1
            OTHER = 2

        block_reason: "GenerateContentResponse.PromptFeedback.BlockReason" = (
            proto.Field(
                proto.ENUM,
                number=1,
                enum="GenerateContentResponse.PromptFeedback.BlockReason",
            )
        )
        safety_ratings: MutableSequence[safety.SafetyRating] = proto.RepeatedField(
            proto.MESSAGE,
            number=2,
            message=safety.SafetyRating,
        )

    class UsageMetadata(proto.Message):
        r"""Metadata on the generation request's token usage.

        Attributes:
            prompt_token_count (int):
                Number of tokens in the prompt.
            candidates_token_count (int):
                Total number of tokens across the generated
                candidates.
            total_token_count (int):
                Total token count for the generation request
                (prompt + candidates).
        """

        prompt_token_count: int = proto.Field(
            proto.INT32,
            number=1,
        )
        candidates_token_count: int = proto.Field(
            proto.INT32,
            number=2,
        )
        total_token_count: int = proto.Field(
            proto.INT32,
            number=3,
        )

    candidates: MutableSequence["Candidate"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="Candidate",
    )
    prompt_feedback: PromptFeedback = proto.Field(
        proto.MESSAGE,
        number=2,
        message=PromptFeedback,
    )
    usage_metadata: UsageMetadata = proto.Field(
        proto.MESSAGE,
        number=3,
        message=UsageMetadata,
    )


class Candidate(proto.Message):
    r"""A response candidate generated from the model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        index (int):
            Output only. Index of the candidate in the
            list of candidates.

            This field is a member of `oneof`_ ``_index``.
        content (google.ai.generativelanguage_v1.types.Content):
            Output only. Generated content returned from
            the model.
        finish_reason (google.ai.generativelanguage_v1.types.Candidate.FinishReason):
            Optional. Output only. The reason why the
            model stopped generating tokens.
            If empty, the model has not stopped generating
            the tokens.
        safety_ratings (MutableSequence[google.ai.generativelanguage_v1.types.SafetyRating]):
            List of ratings for the safety of a response
            candidate.
            There is at most one rating per category.
        citation_metadata (google.ai.generativelanguage_v1.types.CitationMetadata):
            Output only. Citation information for model-generated
            candidate.

            This field may be populated with recitation information for
            any text included in the ``content``. These are passages
            that are "recited" from copyrighted material in the
            foundational LLM's training data.
        token_count (int):
            Output only. Token count for this candidate.
    """

    class FinishReason(proto.Enum):
        r"""Defines the reason why the model stopped generating tokens.

        Values:
            FINISH_REASON_UNSPECIFIED (0):
                Default value. This value is unused.
            STOP (1):
                Natural stop point of the model or provided
                stop sequence.
            MAX_TOKENS (2):
                The maximum number of tokens as specified in
                the request was reached.
            SAFETY (3):
                The candidate content was flagged for safety
                reasons.
            RECITATION (4):
                The candidate content was flagged for
                recitation reasons.
            OTHER (5):
                Unknown reason.
        """
        FINISH_REASON_UNSPECIFIED = 0
        STOP = 1
        MAX_TOKENS = 2
        SAFETY = 3
        RECITATION = 4
        OTHER = 5

    index: int = proto.Field(
        proto.INT32,
        number=3,
        optional=True,
    )
    content: gag_content.Content = proto.Field(
        proto.MESSAGE,
        number=1,
        message=gag_content.Content,
    )
    finish_reason: FinishReason = proto.Field(
        proto.ENUM,
        number=2,
        enum=FinishReason,
    )
    safety_ratings: MutableSequence[safety.SafetyRating] = proto.RepeatedField(
        proto.MESSAGE,
        number=5,
        message=safety.SafetyRating,
    )
    citation_metadata: citation.CitationMetadata = proto.Field(
        proto.MESSAGE,
        number=6,
        message=citation.CitationMetadata,
    )
    token_count: int = proto.Field(
        proto.INT32,
        number=7,
    )


class EmbedContentRequest(proto.Message):
    r"""Request containing the ``Content`` for the model to embed.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        content (google.ai.generativelanguage_v1.types.Content):
            Required. The content to embed. Only the ``parts.text``
            fields will be counted.
        task_type (google.ai.generativelanguage_v1.types.TaskType):
            Optional. Optional task type for which the embeddings will
            be used. Can only be set for ``models/embedding-001``.

            This field is a member of `oneof`_ ``_task_type``.
        title (str):
            Optional. An optional title for the text. Only applicable
            when TaskType is ``RETRIEVAL_DOCUMENT``.

            Note: Specifying a ``title`` for ``RETRIEVAL_DOCUMENT``
            provides better quality embeddings for retrieval.

            This field is a member of `oneof`_ ``_title``.
        output_dimensionality (int):
            Optional. Optional reduced dimension for the output
            embedding. If set, excessive values in the output embedding
            are truncated from the end. Supported by newer models since
            2024, and the earlier model (``models/embedding-001``)
            cannot specify this value.

            This field is a member of `oneof`_ ``_output_dimensionality``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    content: gag_content.Content = proto.Field(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )
    task_type: "TaskType" = proto.Field(
        proto.ENUM,
        number=3,
        optional=True,
        enum="TaskType",
    )
    title: str = proto.Field(
        proto.STRING,
        number=4,
        optional=True,
    )
    output_dimensionality: int = proto.Field(
        proto.INT32,
        number=5,
        optional=True,
    )


class ContentEmbedding(proto.Message):
    r"""A list of floats representing an embedding.

    Attributes:
        values (MutableSequence[float]):
            The embedding values.
    """

    values: MutableSequence[float] = proto.RepeatedField(
        proto.FLOAT,
        number=1,
    )


class EmbedContentResponse(proto.Message):
    r"""The response to an ``EmbedContentRequest``.

    Attributes:
        embedding (google.ai.generativelanguage_v1.types.ContentEmbedding):
            Output only. The embedding generated from the
            input content.
    """

    embedding: "ContentEmbedding" = proto.Field(
        proto.MESSAGE,
        number=1,
        message="ContentEmbedding",
    )


class BatchEmbedContentsRequest(proto.Message):
    r"""Batch request to get embeddings from the model for a list of
    prompts.

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        requests (MutableSequence[google.ai.generativelanguage_v1.types.EmbedContentRequest]):
            Required. Embed requests for the batch. The model in each of
            these requests must match the model specified
            ``BatchEmbedContentsRequest.model``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    requests: MutableSequence["EmbedContentRequest"] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message="EmbedContentRequest",
    )


class BatchEmbedContentsResponse(proto.Message):
    r"""The response to a ``BatchEmbedContentsRequest``.

    Attributes:
        embeddings (MutableSequence[google.ai.generativelanguage_v1.types.ContentEmbedding]):
            Output only. The embeddings for each request,
            in the same order as provided in the batch
            request.
    """

    embeddings: MutableSequence["ContentEmbedding"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="ContentEmbedding",
    )


class CountTokensRequest(proto.Message):
    r"""Counts the number of tokens in the ``prompt`` sent to a model.

    Models may tokenize text differently, so each model may return a
    different ``token_count``.

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        contents (MutableSequence[google.ai.generativelanguage_v1.types.Content]):
            Optional. The input given to the model as a prompt. This
            field is ignored when ``generate_content_request`` is set.
        generate_content_request (google.ai.generativelanguage_v1.types.GenerateContentRequest):
            Optional. The overall input given to the
            model. CountTokens will count prompt, function
            calling, etc.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    contents: MutableSequence[gag_content.Content] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )
    generate_content_request: "GenerateContentRequest" = proto.Field(
        proto.MESSAGE,
        number=3,
        message="GenerateContentRequest",
    )


class CountTokensResponse(proto.Message):
    r"""A response from ``CountTokens``.

    It returns the model's ``token_count`` for the ``prompt``.

    Attributes:
        total_tokens (int):
            The number of tokens that the ``model`` tokenizes the
            ``prompt`` into.

            Always non-negative.
    """

    total_tokens: int = proto.Field(
        proto.INT32,
        number=1,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_qlik_builtins.py ===
"""
    pygments.lexers._qlik_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Qlik builtins.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# operators
#   see https://help.qlik.com/en-US/sense/August2021/Subsystems/Hub/Content/Sense_Hub/Scripting/Operators/operators.htm
OPERATORS_LIST = {
    "words": [
        # Bit operators
        "bitnot",
        "bitand",
        "bitor",
        "bitxor",
        # Logical operators
        "and",
        "or",
        "not",
        "xor",
        # Relational operators
        "precedes",
        "follows",
        # String operators
        "like",
    ],
    "symbols": [
        # Bit operators
        ">>",
        "<<",
        # Logical operators
        # Numeric operators
        "+",
        "-",
        "/",
        "*",
        # Relational operators
        "<",
        "<=",
        ">",
        ">=",
        "=",
        "<>",
        # String operators
        "&",
    ],
}

# SCRIPT STATEMENTS
#   see https://help.qlik.com/en-US/sense/August2021/Subsystems/Hub/Content/Sense_Hub/Scripting/
STATEMENT_LIST = [
    # control statements
    "for",
    "each",
    "in",
    "next",
    "do",
    "while",
    "until",
    "unless",
    "loop",
    "return",
    "switch",
    "case",
    "default",
    "if",
    "else",
    "endif",
    "then",
    "end",
    "exit",
    "script",
    "switch",
    # prefixes
    "Add",
    "Buffer",
    "Concatenate",
    "Crosstable",
    "First",
    "Generic",
    "Hierarchy",
    "HierarchyBelongsTo",
    "Inner",
    "IntervalMatch",
    "Join",
    "Keep",
    "Left",
    "Mapping",
    "Merge",
    "NoConcatenate",
    "Outer",
    "Partial reload",
    "Replace",
    "Right",
    "Sample",
    "Semantic",
    "Unless",
    "When",
    # regular statements
    "Alias",  # alias ... as ...
    "as",
    "AutoNumber",
    "Binary",
    "Comment field",  # comment fields ... using ...
    "Comment fields",  # comment field ... with ...
    "using",
    "with",
    "Comment table",  # comment table ... with ...
    "Comment tables",  # comment tables ... using ...
    "Connect",
    "ODBC",  # ODBC CONNECT TO ...
    "OLEBD",  # OLEDB CONNECT TO ...
    "CUSTOM",  # CUSTOM CONNECT TO ...
    "LIB",  # LIB CONNECT TO ...
    "Declare",
    "Derive",
    "From",
    "explicit",
    "implicit",
    "Direct Query",
    "dimension",
    "measure",
    "Directory",
    "Disconnect",
    "Drop field",
    "Drop fields",
    "Drop table",
    "Drop tables",
    "Execute",
    "FlushLog",
    "Force",
    "capitalization",
    "case upper",
    "case lower",
    "case mixed",
    "Load",
    "distinct",
    "from",
    "inline",
    "resident",
    "from_field",
    "autogenerate",
    "extension",
    "where",
    "group by",
    "order by",
    "asc",
    "desc",
    "Let",
    "Loosen Table",
    "Map",
    "NullAsNull",
    "NullAsValue",
    "Qualify",
    "Rem",
    "Rename field",
    "Rename fields",
    "Rename table",
    "Rename tables",
    "Search",
    "include",
    "exclude",
    "Section",
    "access",
    "application",
    "Select",
    "Set",
    "Sleep",
    "SQL",
    "SQLColumns",
    "SQLTables",
    "SQLTypes",
    "Star",
    "Store",
    "Tag",
    "Trace",
    "Unmap",
    "Unqualify",
    "Untag",
    # Qualifiers
    "total",
]

# Script functions
#    see https://help.qlik.com/en-US/sense/August2021/Subsystems/Hub/Content/Sense_Hub/Scripting/functions-in-scripts-chart-expressions.htm
SCRIPT_FUNCTIONS = [
    # Basic aggregation functions in the data load script
    "FirstSortedValue",
    "Max",
    "Min",
    "Mode",
    "Only",
    "Sum",
    # Counter aggregation functions in the data load script
    "Count",
    "MissingCount",
    "NullCount",
    "NumericCount",
    "TextCount",
    # Financial aggregation functions in the data load script
    "IRR",
    "XIRR",
    "NPV",
    "XNPV",
    # Statistical aggregation functions in the data load script
    "Avg",
    "Correl",
    "Fractile",
    "FractileExc",
    "Kurtosis",
    "LINEST_B" "LINEST_df",
    "LINEST_f",
    "LINEST_m",
    "LINEST_r2",
    "LINEST_seb",
    "LINEST_sem",
    "LINEST_sey",
    "LINEST_ssreg",
    "Linest_ssresid",
    "Median",
    "Skew",
    "Stdev",
    "Sterr",
    "STEYX",
    # Statistical test functions
    "Chi2Test_chi2",
    "Chi2Test_df",
    "Chi2Test_p",
    # Two independent samples t-tests
    "ttest_conf",
    "ttest_df",
    "ttest_dif",
    "ttest_lower",
    "ttest_sig",
    "ttest_sterr",
    "ttest_t",
    "ttest_upper",
    # Two independent weighted samples t-tests
    "ttestw_conf",
    "ttestw_df",
    "ttestw_dif",
    "ttestw_lower",
    "ttestw_sig",
    "ttestw_sterr",
    "ttestw_t",
    "ttestw_upper",
    # One sample t-tests
    "ttest1_conf",
    "ttest1_df",
    "ttest1_dif",
    "ttest1_lower",
    "ttest1_sig",
    "ttest1_sterr",
    "ttest1_t",
    "ttest1_upper",
    # One weighted sample t-tests
    "ttest1w_conf",
    "ttest1w_df",
    "ttest1w_dif",
    "ttest1w_lower",
    "ttest1w_sig",
    "ttest1w_sterr",
    "ttest1w_t",
    "ttest1w_upper",
    # One column format functions
    "ztest_conf",
    "ztest_dif",
    "ztest_sig",
    "ztest_sterr",
    "ztest_z",
    "ztest_lower",
    "ztest_upper",
    # Weighted two-column format functions
    "ztestw_conf",
    "ztestw_dif",
    "ztestw_lower",
    "ztestw_sig",
    "ztestw_sterr",
    "ztestw_upper",
    "ztestw_z",
    # String aggregation functions in the data load script
    "Concat",
    "FirstValue",
    "LastValue",
    "MaxString",
    "MinString",
    # Synthetic dimension functions
    "ValueList",
    "ValueLoop",
    # Color functions
    "ARGB",
    "HSL",
    "RGB",
    "Color",
    "Colormix1",
    "Colormix2",
    "SysColor",
    "ColorMapHue",
    "ColorMapJet",
    "black",
    "blue",
    "brown",
    "cyan",
    "darkgray",
    "green",
    "lightblue",
    "lightcyan",
    "lightgray",
    "lightgreen",
    "lightmagenta",
    "lightred",
    "magenta",
    "red",
    "white",
    "yellow",
    # Conditional functions
    "alt",
    "class",
    "coalesce",
    "if",
    "match",
    "mixmatch",
    "pick",
    "wildmatch",
    # Counter functions
    "autonumber",
    "autonumberhash128",
    "autonumberhash256",
    "IterNo",
    "RecNo",
    "RowNo",
    # Integer expressions of time
    "second",
    "minute",
    "hour",
    "day",
    "week",
    "month",
    "year",
    "weekyear",
    "weekday",
    # Timestamp functions
    "now",
    "today",
    "LocalTime",
    # Make functions
    "makedate",
    "makeweekdate",
    "maketime",
    # Other date functions
    "AddMonths",
    "AddYears",
    "yeartodate",
    # Timezone functions
    "timezone",
    "GMT",
    "UTC",
    "daylightsaving",
    "converttolocaltime",
    # Set time functions
    "setdateyear",
    "setdateyearmonth",
    # In... functions
    "inyear",
    "inyeartodate",
    "inquarter",
    "inquartertodate",
    "inmonth",
    "inmonthtodate",
    "inmonths",
    "inmonthstodate",
    "inweek",
    "inweektodate",
    "inlunarweek",
    "inlunarweektodate",
    "inday",
    "indaytotime",
    # Start ... end functions
    "yearstart",
    "yearend",
    "yearname",
    "quarterstart",
    "quarterend",
    "quartername",
    "monthstart",
    "monthend",
    "monthname",
    "monthsstart",
    "monthsend",
    "monthsname",
    "weekstart",
    "weekend",
    "weekname",
    "lunarweekstart",
    "lunarweekend",
    "lunarweekname",
    "daystart",
    "dayend",
    "dayname",
    # Day numbering functions
    "age",
    "networkdays",
    "firstworkdate",
    "lastworkdate",
    "daynumberofyear",
    "daynumberofquarter",
    # Exponential and logarithmic
    "exp",
    "log",
    "log10",
    "pow",
    "sqr",
    "sqrt",
    # Count functions
    "GetAlternativeCount",
    "GetExcludedCount",
    "GetNotSelectedCount",
    "GetPossibleCount",
    "GetSelectedCount",
    # Field and selection functions
    "GetCurrentSelections",
    "GetFieldSelections",
    "GetObjectDimension",
    "GetObjectField",
    "GetObjectMeasure",
    # File functions
    "Attribute",
    "ConnectString",
    "FileBaseName",
    "FileDir",
    "FileExtension",
    "FileName",
    "FilePath",
    "FileSize",
    "FileTime",
    "GetFolderPath",
    "QvdCreateTime",
    "QvdFieldName",
    "QvdNoOfFields",
    "QvdNoOfRecords",
    "QvdTableName",
    # Financial functions
    "FV",
    "nPer",
    "Pmt",
    "PV",
    "Rate",
    # Formatting functions
    "ApplyCodepage",
    "Date",
    "Dual",
    "Interval",
    "Money",
    "Num",
    "Time",
    "Timestamp",
    # General numeric functions
    "bitcount",
    "div",
    "fabs",
    "fact",
    "frac",
    "sign",
    # Combination and permutation functions
    "combin",
    "permut",
    # Modulo functions
    "fmod",
    "mod",
    # Parity functions
    "even",
    "odd",
    # Rounding functions
    "ceil",
    "floor",
    "round",
    # Geospatial functions
    "GeoAggrGeometry",
    "GeoBoundingBox",
    "GeoCountVertex",
    "GeoInvProjectGeometry",
    "GeoProjectGeometry",
    "GeoReduceGeometry",
    "GeoGetBoundingBox",
    "GeoGetPolygonCenter",
    "GeoMakePoint",
    "GeoProject",
    # Interpretation functions
    "Date#",
    "Interval#",
    "Money#",
    "Num#",
    "Text",
    "Time#",
    "Timestamp#",
    # Field functions
    "FieldIndex",
    "FieldValue",
    "FieldValueCount",
    # Inter-record functions in the data load script
    "Exists",
    "LookUp",
    "Peek",
    "Previous",
    # Logical functions
    "IsNum",
    "IsText",
    # Mapping functions
    "ApplyMap",
    "MapSubstring",
    # Mathematical functions
    "e",
    "false",
    "pi",
    "rand",
    "true",
    # NULL functions
    "EmptyIsNull",
    "IsNull",
    "Null",
    # Basic range functions
    "RangeMax",
    "RangeMaxString",
    "RangeMin",
    "RangeMinString",
    "RangeMode",
    "RangeOnly",
    "RangeSum",
    # Counter range functions
    "RangeCount",
    "RangeMissingCount",
    "RangeNullCount",
    "RangeNumericCount",
    "RangeTextCount",
    # Statistical range functions
    "RangeAvg",
    "RangeCorrel",
    "RangeFractile",
    "RangeKurtosis",
    "RangeSkew",
    "RangeStdev",
    # Financial range functions
    "RangeIRR",
    "RangeNPV",
    "RangeXIRR",
    "RangeXNPV",
    # Statistical distribution
    "CHIDIST",
    "CHIINV",
    "NORMDIST",
    "NORMINV",
    "TDIST",
    "TINV",
    "FDIST",
    "FINV",
    # String functions
    "Capitalize",
    "Chr",
    "Evaluate",
    "FindOneOf",
    "Hash128",
    "Hash160",
    "Hash256",
    "Index",
    "KeepChar",
    "Left",
    "Len",
    "LevenshteinDist",
    "Lower",
    "LTrim",
    "Mid",
    "Ord",
    "PurgeChar",
    "Repeat",
    "Replace",
    "Right",
    "RTrim",
    "SubField",
    "SubStringCount",
    "TextBetween",
    "Trim",
    "Upper",
    # System functions
    "Author",
    "ClientPlatform",
    "ComputerName",
    "DocumentName",
    "DocumentPath",
    "DocumentTitle",
    "EngineVersion",
    "GetCollationLocale",
    "GetObjectField",
    "GetRegistryString",
    "IsPartialReload",
    "OSUser",
    "ProductVersion",
    "ReloadTime",
    "StateName",
    # Table functions
    "FieldName",
    "FieldNumber",
    "NoOfFields",
    "NoOfRows",
    "NoOfTables",
    "TableName",
    "TableNumber",
]

# System variables and constants
# see https://help.qlik.com/en-US/sense/August2021/Subsystems/Hub/Content/Sense_Hub/Scripting/work-with-variables-in-data-load-editor.htm
CONSTANT_LIST = [
    # System Variables
    "floppy",
    "cd",
    "include",
    "must_include",
    "hideprefix",
    "hidesuffix",
    "qvpath",
    "qvroot",
    "QvWorkPath",
    "QvWorkRoot",
    "StripComments",
    "Verbatim",
    "OpenUrlTimeout",
    "WinPath",
    "WinRoot",
    "CollationLocale",
    "CreateSearchIndexOnReload",
    # value handling variables
    "NullDisplay",
    "NullInterpret",
    "NullValue",
    "OtherSymbol",
    # Currency formatting
    "MoneyDecimalSep",
    "MoneyFormat",
    "MoneyThousandSep",
    # Number formatting
    "DecimalSep",
    "ThousandSep",
    "NumericalAbbreviation",
    # Time formatting
    "DateFormat",
    "TimeFormat",
    "TimestampFormat",
    "MonthNames",
    "LongMonthNames",
    "DayNames",
    "LongDayNames",
    "FirstWeekDay",
    "BrokenWeeks",
    "ReferenceDay",
    "FirstMonthOfYear",
    # Error variables
    "errormode",
    "scripterror",
    "scripterrorcount",
    "scripterrorlist",
    # Other
    "null",
]

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\cb_rules.py ===
"""
Build call-back mechanism for f2py2e.

Copyright 1999 -- 2011 Pearu Peterson all rights reserved.
Copyright 2011 -- present NumPy Developers.
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
"""
from . import __version__, cfuncs
from .auxfuncs import (
    applyrules,
    debugcapi,
    dictappend,
    errmess,
    getargs,
    hasnote,
    isarray,
    iscomplex,
    iscomplexarray,
    iscomplexfunction,
    isfunction,
    isintent_c,
    isintent_hide,
    isintent_in,
    isintent_inout,
    isintent_nothide,
    isintent_out,
    isoptional,
    isrequired,
    isscalar,
    isstring,
    isstringfunction,
    issubroutine,
    l_and,
    l_not,
    l_or,
    outmess,
    replace,
    stripcomma,
    throw_error,
)

f2py_version = __version__.version


################## Rules for callback function ##############

cb_routine_rules = {
    'cbtypedefs': 'typedef #rctype#(*#name#_typedef)(#optargs_td##args_td##strarglens_td##noargs#);',
    'body': """
#begintitle#
typedef struct {
    PyObject *capi;
    PyTupleObject *args_capi;
    int nofargs;
    jmp_buf jmpbuf;
} #name#_t;

#if defined(F2PY_THREAD_LOCAL_DECL) && !defined(F2PY_USE_PYTHON_TLS)

static F2PY_THREAD_LOCAL_DECL #name#_t *_active_#name# = NULL;

static #name#_t *swap_active_#name#(#name#_t *ptr) {
    #name#_t *prev = _active_#name#;
    _active_#name# = ptr;
    return prev;
}

static #name#_t *get_active_#name#(void) {
    return _active_#name#;
}

#else

static #name#_t *swap_active_#name#(#name#_t *ptr) {
    char *key = "__f2py_cb_#name#";
    return (#name#_t *)F2PySwapThreadLocalCallbackPtr(key, ptr);
}

static #name#_t *get_active_#name#(void) {
    char *key = "__f2py_cb_#name#";
    return (#name#_t *)F2PyGetThreadLocalCallbackPtr(key);
}

#endif

/*typedef #rctype#(*#name#_typedef)(#optargs_td##args_td##strarglens_td##noargs#);*/
#static# #rctype# #callbackname# (#optargs##args##strarglens##noargs#) {
    #name#_t cb_local = { NULL, NULL, 0 };
    #name#_t *cb = NULL;
    PyTupleObject *capi_arglist = NULL;
    PyObject *capi_return = NULL;
    PyObject *capi_tmp = NULL;
    PyObject *capi_arglist_list = NULL;
    int capi_j,capi_i = 0;
    int capi_longjmp_ok = 1;
#decl#
#ifdef F2PY_REPORT_ATEXIT
f2py_cb_start_clock();
#endif
    cb = get_active_#name#();
    if (cb == NULL) {
        capi_longjmp_ok = 0;
        cb = &cb_local;
    }
    capi_arglist = cb->args_capi;
    CFUNCSMESS(\"cb:Call-back function #name# (maxnofargs=#maxnofargs#(-#nofoptargs#))\\n\");
    CFUNCSMESSPY(\"cb:#name#_capi=\",cb->capi);
    if (cb->capi==NULL) {
        capi_longjmp_ok = 0;
        cb->capi = PyObject_GetAttrString(#modulename#_module,\"#argname#\");
        CFUNCSMESSPY(\"cb:#name#_capi=\",cb->capi);
    }
    if (cb->capi==NULL) {
        PyErr_SetString(#modulename#_error,\"cb: Callback #argname# not defined (as an argument or module #modulename# attribute).\\n\");
        goto capi_fail;
    }
    if (F2PyCapsule_Check(cb->capi)) {
    #name#_typedef #name#_cptr;
    #name#_cptr = F2PyCapsule_AsVoidPtr(cb->capi);
    #returncptr#(*#name#_cptr)(#optargs_nm##args_nm##strarglens_nm#);
    #return#
    }
    if (capi_arglist==NULL) {
        capi_longjmp_ok = 0;
        capi_tmp = PyObject_GetAttrString(#modulename#_module,\"#argname#_extra_args\");
        if (capi_tmp) {
            capi_arglist = (PyTupleObject *)PySequence_Tuple(capi_tmp);
            Py_DECREF(capi_tmp);
            if (capi_arglist==NULL) {
                PyErr_SetString(#modulename#_error,\"Failed to convert #modulename#.#argname#_extra_args to tuple.\\n\");
                goto capi_fail;
            }
        } else {
            PyErr_Clear();
            capi_arglist = (PyTupleObject *)Py_BuildValue(\"()\");
        }
    }
    if (capi_arglist == NULL) {
        PyErr_SetString(#modulename#_error,\"Callback #argname# argument list is not set.\\n\");
        goto capi_fail;
    }
#setdims#
#ifdef PYPY_VERSION
#define CAPI_ARGLIST_SETITEM(idx, value) PyList_SetItem((PyObject *)capi_arglist_list, idx, value)
    capi_arglist_list = PySequence_List((PyObject *)capi_arglist);
    if (capi_arglist_list == NULL) goto capi_fail;
#else
#define CAPI_ARGLIST_SETITEM(idx, value) PyTuple_SetItem((PyObject *)capi_arglist, idx, value)
#endif
#pyobjfrom#
#undef CAPI_ARGLIST_SETITEM
#ifdef PYPY_VERSION
    CFUNCSMESSPY(\"cb:capi_arglist=\",capi_arglist_list);
#else
    CFUNCSMESSPY(\"cb:capi_arglist=\",capi_arglist);
#endif
    CFUNCSMESS(\"cb:Call-back calling Python function #argname#.\\n\");
#ifdef F2PY_REPORT_ATEXIT
f2py_cb_start_call_clock();
#endif
#ifdef PYPY_VERSION
    capi_return = PyObject_CallObject(cb->capi,(PyObject *)capi_arglist_list);
    Py_DECREF(capi_arglist_list);
    capi_arglist_list = NULL;
#else
    capi_return = PyObject_CallObject(cb->capi,(PyObject *)capi_arglist);
#endif
#ifdef F2PY_REPORT_ATEXIT
f2py_cb_stop_call_clock();
#endif
    CFUNCSMESSPY(\"cb:capi_return=\",capi_return);
    if (capi_return == NULL) {
        fprintf(stderr,\"capi_return is NULL\\n\");
        goto capi_fail;
    }
    if (capi_return == Py_None) {
        Py_DECREF(capi_return);
        capi_return = Py_BuildValue(\"()\");
    }
    else if (!PyTuple_Check(capi_return)) {
        capi_return = Py_BuildValue(\"(N)\",capi_return);
    }
    capi_j = PyTuple_Size(capi_return);
    capi_i = 0;
#frompyobj#
    CFUNCSMESS(\"cb:#name#:successful\\n\");
    Py_DECREF(capi_return);
#ifdef F2PY_REPORT_ATEXIT
f2py_cb_stop_clock();
#endif
    goto capi_return_pt;
capi_fail:
    fprintf(stderr,\"Call-back #name# failed.\\n\");
    Py_XDECREF(capi_return);
    Py_XDECREF(capi_arglist_list);
    if (capi_longjmp_ok) {
        longjmp(cb->jmpbuf,-1);
    }
capi_return_pt:
    ;
#return#
}
#endtitle#
""",
    'need': ['setjmp.h', 'CFUNCSMESS', 'F2PY_THREAD_LOCAL_DECL'],
    'maxnofargs': '#maxnofargs#',
    'nofoptargs': '#nofoptargs#',
    'docstr': """\
    def #argname#(#docsignature#): return #docreturn#\\n\\
#docstrsigns#""",
    'latexdocstr': """
{{}\\verb@def #argname#(#latexdocsignature#): return #docreturn#@{}}
#routnote#

#latexdocstrsigns#""",
    'docstrshort': 'def #argname#(#docsignature#): return #docreturn#'
}
cb_rout_rules = [
    {  # Init
        'separatorsfor': {'decl': '\n',
                          'args': ',', 'optargs': '', 'pyobjfrom': '\n', 'freemem': '\n',
                          'args_td': ',', 'optargs_td': '',
                          'args_nm': ',', 'optargs_nm': '',
                          'frompyobj': '\n', 'setdims': '\n',
                          'docstrsigns': '\\n"\n"',
                          'latexdocstrsigns': '\n',
                          'latexdocstrreq': '\n', 'latexdocstropt': '\n',
                          'latexdocstrout': '\n', 'latexdocstrcbs': '\n',
                          },
        'decl': '/*decl*/', 'pyobjfrom': '/*pyobjfrom*/', 'frompyobj': '/*frompyobj*/',
        'args': [], 'optargs': '', 'return': '', 'strarglens': '', 'freemem': '/*freemem*/',
        'args_td': [], 'optargs_td': '', 'strarglens_td': '',
        'args_nm': [], 'optargs_nm': '', 'strarglens_nm': '',
        'noargs': '',
        'setdims': '/*setdims*/',
        'docstrsigns': '', 'latexdocstrsigns': '',
        'docstrreq': '    Required arguments:',
        'docstropt': '    Optional arguments:',
        'docstrout': '    Return objects:',
        'docstrcbs': '    Call-back functions:',
        'docreturn': '', 'docsign': '', 'docsignopt': '',
        'latexdocstrreq': '\\noindent Required arguments:',
        'latexdocstropt': '\\noindent Optional arguments:',
        'latexdocstrout': '\\noindent Return objects:',
        'latexdocstrcbs': '\\noindent Call-back functions:',
        'routnote': {hasnote: '--- #note#', l_not(hasnote): ''},
    }, {  # Function
        'decl': '    #ctype# return_value = 0;',
        'frompyobj': [
            {debugcapi: '    CFUNCSMESS("cb:Getting return_value->");'},
            '''\
    if (capi_j>capi_i) {
        GETSCALARFROMPYTUPLE(capi_return,capi_i++,&return_value,#ctype#,
          "#ctype#_from_pyobj failed in converting return_value of"
          " call-back function #name# to C #ctype#\\n");
    } else {
        fprintf(stderr,"Warning: call-back function #name# did not provide"
                       " return value (index=%d, type=#ctype#)\\n",capi_i);
    }''',
            {debugcapi:
             '    fprintf(stderr,"#showvalueformat#.\\n",return_value);'}
        ],
        'need': ['#ctype#_from_pyobj', {debugcapi: 'CFUNCSMESS'}, 'GETSCALARFROMPYTUPLE'],
        'return': '    return return_value;',
        '_check': l_and(isfunction, l_not(isstringfunction), l_not(iscomplexfunction))
    },
    {  # String function
        'pyobjfrom': {debugcapi: '    fprintf(stderr,"debug-capi:cb:#name#:%d:\\n",return_value_len);'},
        'args': '#ctype# return_value,int return_value_len',
        'args_nm': 'return_value,&return_value_len',
        'args_td': '#ctype# ,int',
        'frompyobj': [
            {debugcapi: '    CFUNCSMESS("cb:Getting return_value->\\"");'},
            """\
    if (capi_j>capi_i) {
        GETSTRFROMPYTUPLE(capi_return,capi_i++,return_value,return_value_len);
    } else {
        fprintf(stderr,"Warning: call-back function #name# did not provide"
                       " return value (index=%d, type=#ctype#)\\n",capi_i);
    }""",
            {debugcapi:
             '    fprintf(stderr,"#showvalueformat#\\".\\n",return_value);'}
        ],
        'need': ['#ctype#_from_pyobj', {debugcapi: 'CFUNCSMESS'},
                 'string.h', 'GETSTRFROMPYTUPLE'],
        'return': 'return;',
        '_check': isstringfunction
    },
    {  # Complex function
        'optargs': """
#ifndef F2PY_CB_RETURNCOMPLEX
#ctype# *return_value
#endif
""",
        'optargs_nm': """
#ifndef F2PY_CB_RETURNCOMPLEX
return_value
#endif
""",
        'optargs_td': """
#ifndef F2PY_CB_RETURNCOMPLEX
#ctype# *
#endif
""",
        'decl': """
#ifdef F2PY_CB_RETURNCOMPLEX
    #ctype# return_value = {0, 0};
#endif
""",
        'frompyobj': [
            {debugcapi: '    CFUNCSMESS("cb:Getting return_value->");'},
            """\
    if (capi_j>capi_i) {
#ifdef F2PY_CB_RETURNCOMPLEX
        GETSCALARFROMPYTUPLE(capi_return,capi_i++,&return_value,#ctype#,
          \"#ctype#_from_pyobj failed in converting return_value of call-back\"
          \" function #name# to C #ctype#\\n\");
#else
        GETSCALARFROMPYTUPLE(capi_return,capi_i++,return_value,#ctype#,
          \"#ctype#_from_pyobj failed in converting return_value of call-back\"
          \" function #name# to C #ctype#\\n\");
#endif
    } else {
        fprintf(stderr,
                \"Warning: call-back function #name# did not provide\"
                \" return value (index=%d, type=#ctype#)\\n\",capi_i);
    }""",
            {debugcapi: """\
#ifdef F2PY_CB_RETURNCOMPLEX
    fprintf(stderr,\"#showvalueformat#.\\n\",(return_value).r,(return_value).i);
#else
    fprintf(stderr,\"#showvalueformat#.\\n\",(*return_value).r,(*return_value).i);
#endif
"""}
        ],
        'return': """
#ifdef F2PY_CB_RETURNCOMPLEX
    return return_value;
#else
    return;
#endif
""",
        'need': ['#ctype#_from_pyobj', {debugcapi: 'CFUNCSMESS'},
                 'string.h', 'GETSCALARFROMPYTUPLE', '#ctype#'],
        '_check': iscomplexfunction
    },
    {'docstrout': '        #pydocsignout#',
     'latexdocstrout': ['\\item[]{{}\\verb@#pydocsignout#@{}}',
                        {hasnote: '--- #note#'}],
     'docreturn': '#rname#,',
     '_check': isfunction},
    {'_check': issubroutine, 'return': 'return;'}
]

cb_arg_rules = [
    {  # Doc
        'docstropt': {l_and(isoptional, isintent_nothide): '        #pydocsign#'},
        'docstrreq': {l_and(isrequired, isintent_nothide): '        #pydocsign#'},
        'docstrout': {isintent_out: '        #pydocsignout#'},
        'latexdocstropt': {l_and(isoptional, isintent_nothide): ['\\item[]{{}\\verb@#pydocsign#@{}}',
                                                                 {hasnote: '--- #note#'}]},
        'latexdocstrreq': {l_and(isrequired, isintent_nothide): ['\\item[]{{}\\verb@#pydocsign#@{}}',
                                                                 {hasnote: '--- #note#'}]},
        'latexdocstrout': {isintent_out: ['\\item[]{{}\\verb@#pydocsignout#@{}}',
                                          {l_and(hasnote, isintent_hide): '--- #note#',
                                           l_and(hasnote, isintent_nothide): '--- See above.'}]},
        'docsign': {l_and(isrequired, isintent_nothide): '#varname#,'},
        'docsignopt': {l_and(isoptional, isintent_nothide): '#varname#,'},
        'depend': ''
    },
    {
        'args': {
            l_and(isscalar, isintent_c): '#ctype# #varname_i#',
            l_and(isscalar, l_not(isintent_c)): '#ctype# *#varname_i#_cb_capi',
            isarray: '#ctype# *#varname_i#',
            isstring: '#ctype# #varname_i#'
        },
        'args_nm': {
            l_and(isscalar, isintent_c): '#varname_i#',
            l_and(isscalar, l_not(isintent_c)): '#varname_i#_cb_capi',
            isarray: '#varname_i#',
            isstring: '#varname_i#'
        },
        'args_td': {
            l_and(isscalar, isintent_c): '#ctype#',
            l_and(isscalar, l_not(isintent_c)): '#ctype# *',
            isarray: '#ctype# *',
            isstring: '#ctype#'
        },
        'need': {l_or(isscalar, isarray, isstring): '#ctype#'},
        # untested with multiple args
        'strarglens': {isstring: ',int #varname_i#_cb_len'},
        'strarglens_td': {isstring: ',int'},  # untested with multiple args
        # untested with multiple args
        'strarglens_nm': {isstring: ',#varname_i#_cb_len'},
    },
    {  # Scalars
        'decl': {l_not(isintent_c): '    #ctype# #varname_i#=(*#varname_i#_cb_capi);'},
        'error': {l_and(isintent_c, isintent_out,
                        throw_error('intent(c,out) is forbidden for callback scalar arguments')):
                  ''},
        'frompyobj': [{debugcapi: '    CFUNCSMESS("cb:Getting #varname#->");'},
                      {isintent_out:
                       '    if (capi_j>capi_i)\n        GETSCALARFROMPYTUPLE(capi_return,capi_i++,#varname_i#_cb_capi,#ctype#,"#ctype#_from_pyobj failed in converting argument #varname# of call-back function #name# to C #ctype#\\n");'},
                      {l_and(debugcapi, l_and(l_not(iscomplex), isintent_c)):
                          '    fprintf(stderr,"#showvalueformat#.\\n",#varname_i#);'},
                      {l_and(debugcapi, l_and(l_not(iscomplex), l_not(isintent_c))):
                          '    fprintf(stderr,"#showvalueformat#.\\n",*#varname_i#_cb_capi);'},
                      {l_and(debugcapi, l_and(iscomplex, isintent_c)):
                          '    fprintf(stderr,"#showvalueformat#.\\n",(#varname_i#).r,(#varname_i#).i);'},
                      {l_and(debugcapi, l_and(iscomplex, l_not(isintent_c))):
                          '    fprintf(stderr,"#showvalueformat#.\\n",(*#varname_i#_cb_capi).r,(*#varname_i#_cb_capi).i);'},
                      ],
        'need': [{isintent_out: ['#ctype#_from_pyobj', 'GETSCALARFROMPYTUPLE']},
                 {debugcapi: 'CFUNCSMESS'}],
        '_check': isscalar
    }, {
        'pyobjfrom': [{isintent_in: """\
    if (cb->nofargs>capi_i)
        if (CAPI_ARGLIST_SETITEM(capi_i++,pyobj_from_#ctype#1(#varname_i#)))
            goto capi_fail;"""},
                      {isintent_inout: """\
    if (cb->nofargs>capi_i)
        if (CAPI_ARGLIST_SETITEM(capi_i++,pyarr_from_p_#ctype#1(#varname_i#_cb_capi)))
            goto capi_fail;"""}],
        'need': [{isintent_in: 'pyobj_from_#ctype#1'},
                 {isintent_inout: 'pyarr_from_p_#ctype#1'},
                 {iscomplex: '#ctype#'}],
        '_check': l_and(isscalar, isintent_nothide),
        '_optional': ''
    }, {  # String
        'frompyobj': [{debugcapi: '    CFUNCSMESS("cb:Getting #varname#->\\"");'},
                      """    if (capi_j>capi_i)
        GETSTRFROMPYTUPLE(capi_return,capi_i++,#varname_i#,#varname_i#_cb_len);""",
                      {debugcapi:
                       '    fprintf(stderr,"#showvalueformat#\\":%d:.\\n",#varname_i#,#varname_i#_cb_len);'},
                      ],
        'need': ['#ctype#', 'GETSTRFROMPYTUPLE',
                 {debugcapi: 'CFUNCSMESS'}, 'string.h'],
        '_check': l_and(isstring, isintent_out)
    }, {
        'pyobjfrom': [
            {debugcapi:
             ('    fprintf(stderr,"debug-capi:cb:#varname#=#showvalueformat#:'
              '%d:\\n",#varname_i#,#varname_i#_cb_len);')},
            {isintent_in: """\
    if (cb->nofargs>capi_i)
        if (CAPI_ARGLIST_SETITEM(capi_i++,pyobj_from_#ctype#1size(#varname_i#,#varname_i#_cb_len)))
            goto capi_fail;"""},
                      {isintent_inout: """\
    if (cb->nofargs>capi_i) {
        int #varname_i#_cb_dims[] = {#varname_i#_cb_len};
        if (CAPI_ARGLIST_SETITEM(capi_i++,pyarr_from_p_#ctype#1(#varname_i#,#varname_i#_cb_dims)))
            goto capi_fail;
    }"""}],
        'need': [{isintent_in: 'pyobj_from_#ctype#1size'},
                 {isintent_inout: 'pyarr_from_p_#ctype#1'}],
        '_check': l_and(isstring, isintent_nothide),
        '_optional': ''
    },
    # Array ...
    {
        'decl': '    npy_intp #varname_i#_Dims[#rank#] = {#rank*[-1]#};',
        'setdims': '    #cbsetdims#;',
        '_check': isarray,
        '_depend': ''
    },
    {
        'pyobjfrom': [{debugcapi: '    fprintf(stderr,"debug-capi:cb:#varname#\\n");'},
                      {isintent_c: """\
    if (cb->nofargs>capi_i) {
        /* tmp_arr will be inserted to capi_arglist_list that will be
           destroyed when leaving callback function wrapper together
           with tmp_arr. */
        PyArrayObject *tmp_arr = (PyArrayObject *)PyArray_New(&PyArray_Type,
          #rank#,#varname_i#_Dims,#atype#,NULL,(char*)#varname_i#,#elsize#,
          NPY_ARRAY_CARRAY,NULL);
""",
                       l_not(isintent_c): """\
    if (cb->nofargs>capi_i) {
        /* tmp_arr will be inserted to capi_arglist_list that will be
           destroyed when leaving callback function wrapper together
           with tmp_arr. */
        PyArrayObject *tmp_arr = (PyArrayObject *)PyArray_New(&PyArray_Type,
          #rank#,#varname_i#_Dims,#atype#,NULL,(char*)#varname_i#,#elsize#,
          NPY_ARRAY_FARRAY,NULL);
""",
                       },
                      """
        if (tmp_arr==NULL)
            goto capi_fail;
        if (CAPI_ARGLIST_SETITEM(capi_i++,(PyObject *)tmp_arr))
            goto capi_fail;
}"""],
        '_check': l_and(isarray, isintent_nothide, l_or(isintent_in, isintent_inout)),
        '_optional': '',
    }, {
        'frompyobj': [{debugcapi: '    CFUNCSMESS("cb:Getting #varname#->");'},
                      """    if (capi_j>capi_i) {
        PyArrayObject *rv_cb_arr = NULL;
        if ((capi_tmp = PyTuple_GetItem(capi_return,capi_i++))==NULL) goto capi_fail;
        rv_cb_arr =  array_from_pyobj(#atype#,#varname_i#_Dims,#rank#,F2PY_INTENT_IN""",
                      {isintent_c: '|F2PY_INTENT_C'},
                      """,capi_tmp);
        if (rv_cb_arr == NULL) {
            fprintf(stderr,\"rv_cb_arr is NULL\\n\");
            goto capi_fail;
        }
        MEMCOPY(#varname_i#,PyArray_DATA(rv_cb_arr),PyArray_NBYTES(rv_cb_arr));
        if (capi_tmp != (PyObject *)rv_cb_arr) {
            Py_DECREF(rv_cb_arr);
        }
    }""",
                      {debugcapi: '    fprintf(stderr,"<-.\\n");'},
                      ],
        'need': ['MEMCOPY', {iscomplexarray: '#ctype#'}],
        '_check': l_and(isarray, isintent_out)
    }, {
        'docreturn': '#varname#,',
        '_check': isintent_out
    }
]

################## Build call-back module #############
cb_map = {}


def buildcallbacks(m):
    cb_map[m['name']] = []
    for bi in m['body']:
        if bi['block'] == 'interface':
            for b in bi['body']:
                if b:
                    buildcallback(b, m['name'])
                else:
                    errmess(f"warning: empty body for {m['name']}\n")


def buildcallback(rout, um):
    from . import capi_maps

    outmess(f"    Constructing call-back function \"cb_{rout['name']}_in_{um}\"\n")
    args, depargs = getargs(rout)
    capi_maps.depargs = depargs
    var = rout['vars']
    vrd = capi_maps.cb_routsign2map(rout, um)
    rd = dictappend({}, vrd)
    cb_map[um].append([rout['name'], rd['name']])
    for r in cb_rout_rules:
        if ('_check' in r and r['_check'](rout)) or ('_check' not in r):
            ar = applyrules(r, vrd, rout)
            rd = dictappend(rd, ar)
    savevrd = {}
    for i, a in enumerate(args):
        vrd = capi_maps.cb_sign2map(a, var[a], index=i)
        savevrd[a] = vrd
        for r in cb_arg_rules:
            if '_depend' in r:
                continue
            if '_optional' in r and isoptional(var[a]):
                continue
            if ('_check' in r and r['_check'](var[a])) or ('_check' not in r):
                ar = applyrules(r, vrd, var[a])
                rd = dictappend(rd, ar)
                if '_break' in r:
                    break
    for a in args:
        vrd = savevrd[a]
        for r in cb_arg_rules:
            if '_depend' in r:
                continue
            if ('_optional' not in r) or ('_optional' in r and isrequired(var[a])):
                continue
            if ('_check' in r and r['_check'](var[a])) or ('_check' not in r):
                ar = applyrules(r, vrd, var[a])
                rd = dictappend(rd, ar)
                if '_break' in r:
                    break
    for a in depargs:
        vrd = savevrd[a]
        for r in cb_arg_rules:
            if '_depend' not in r:
                continue
            if '_optional' in r:
                continue
            if ('_check' in r and r['_check'](var[a])) or ('_check' not in r):
                ar = applyrules(r, vrd, var[a])
                rd = dictappend(rd, ar)
                if '_break' in r:
                    break
    if 'args' in rd and 'optargs' in rd:
        if isinstance(rd['optargs'], list):
            rd['optargs'] = rd['optargs'] + ["""
#ifndef F2PY_CB_RETURNCOMPLEX
,
#endif
"""]
            rd['optargs_nm'] = rd['optargs_nm'] + ["""
#ifndef F2PY_CB_RETURNCOMPLEX
,
#endif
"""]
            rd['optargs_td'] = rd['optargs_td'] + ["""
#ifndef F2PY_CB_RETURNCOMPLEX
,
#endif
"""]
    if isinstance(rd['docreturn'], list):
        rd['docreturn'] = stripcomma(
            replace('#docreturn#', {'docreturn': rd['docreturn']}))
    optargs = stripcomma(replace('#docsignopt#',
                                 {'docsignopt': rd['docsignopt']}
                                 ))
    if optargs == '':
        rd['docsignature'] = stripcomma(
            replace('#docsign#', {'docsign': rd['docsign']}))
    else:
        rd['docsignature'] = replace('#docsign#[#docsignopt#]',
                                     {'docsign': rd['docsign'],
                                      'docsignopt': optargs,
                                      })
    rd['latexdocsignature'] = rd['docsignature'].replace('_', '\\_')
    rd['latexdocsignature'] = rd['latexdocsignature'].replace(',', ', ')
    rd['docstrsigns'] = []
    rd['latexdocstrsigns'] = []
    for k in ['docstrreq', 'docstropt', 'docstrout', 'docstrcbs']:
        if k in rd and isinstance(rd[k], list):
            rd['docstrsigns'] = rd['docstrsigns'] + rd[k]
        k = 'latex' + k
        if k in rd and isinstance(rd[k], list):
            rd['latexdocstrsigns'] = rd['latexdocstrsigns'] + rd[k][0:1] +\
                ['\\begin{description}'] + rd[k][1:] +\
                ['\\end{description}']
    if 'args' not in rd:
        rd['args'] = ''
        rd['args_td'] = ''
        rd['args_nm'] = ''
    if not (rd.get('args') or rd.get('optargs') or rd.get('strarglens')):
        rd['noargs'] = 'void'

    ar = applyrules(cb_routine_rules, rd)
    cfuncs.callbacks[rd['name']] = ar['body']
    if isinstance(ar['need'], str):
        ar['need'] = [ar['need']]

    if 'need' in rd:
        for t in cfuncs.typedefs.keys():
            if t in rd['need']:
                ar['need'].append(t)

    cfuncs.typedefs_generated[rd['name'] + '_typedef'] = ar['cbtypedefs']
    ar['need'].append(rd['name'] + '_typedef')
    cfuncs.needs[rd['name']] = ar['need']

    capi_maps.lcb2_map[rd['name']] = {'maxnofargs': ar['maxnofargs'],
                                      'nofoptargs': ar['nofoptargs'],
                                      'docstr': ar['docstr'],
                                      'latexdocstr': ar['latexdocstr'],
                                      'argname': rd['argname']
                                      }
    outmess(f"      {ar['docstrshort']}\n")
################## Build call-back function #############

# === NexusCore/openenv\Lib\site-packages\fontTools\colorLib\builder.py ===
"""
colorLib.builder: Build COLR/CPAL tables from scratch

"""

import collections
import copy
import enum
from functools import partial
from math import ceil, log
from typing import (
    Any,
    Dict,
    Generator,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from fontTools.misc.arrayTools import intRect
from fontTools.misc.fixedTools import fixedToFloat
from fontTools.misc.treeTools import build_n_ary_tree
from fontTools.ttLib.tables import C_O_L_R_
from fontTools.ttLib.tables import C_P_A_L_
from fontTools.ttLib.tables import _n_a_m_e
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables.otTables import ExtendMode, CompositeMode
from .errors import ColorLibError
from .geometry import round_start_circle_stable_containment
from .table_builder import BuildCallback, TableBuilder


# TODO move type aliases to colorLib.types?
T = TypeVar("T")
_Kwargs = Mapping[str, Any]
_PaintInput = Union[int, _Kwargs, ot.Paint, Tuple[str, "_PaintInput"]]
_PaintInputList = Sequence[_PaintInput]
_ColorGlyphsDict = Dict[str, Union[_PaintInputList, _PaintInput]]
_ColorGlyphsV0Dict = Dict[str, Sequence[Tuple[str, int]]]
_ClipBoxInput = Union[
    Tuple[int, int, int, int, int],  # format 1, variable
    Tuple[int, int, int, int],  # format 0, non-variable
    ot.ClipBox,
]


MAX_PAINT_COLR_LAYER_COUNT = 255
_DEFAULT_ALPHA = 1.0
_MAX_REUSE_LEN = 32


def _beforeBuildPaintRadialGradient(paint, source):
    x0 = source["x0"]
    y0 = source["y0"]
    r0 = source["r0"]
    x1 = source["x1"]
    y1 = source["y1"]
    r1 = source["r1"]

    # TODO apparently no builder_test confirms this works (?)

    # avoid abrupt change after rounding when c0 is near c1's perimeter
    c = round_start_circle_stable_containment((x0, y0), r0, (x1, y1), r1)
    x0, y0 = c.centre
    r0 = c.radius

    # update source to ensure paint is built with corrected values
    source["x0"] = x0
    source["y0"] = y0
    source["r0"] = r0
    source["x1"] = x1
    source["y1"] = y1
    source["r1"] = r1

    return paint, source


def _defaultColorStop():
    colorStop = ot.ColorStop()
    colorStop.Alpha = _DEFAULT_ALPHA
    return colorStop


def _defaultVarColorStop():
    colorStop = ot.VarColorStop()
    colorStop.Alpha = _DEFAULT_ALPHA
    return colorStop


def _defaultColorLine():
    colorLine = ot.ColorLine()
    colorLine.Extend = ExtendMode.PAD
    return colorLine


def _defaultVarColorLine():
    colorLine = ot.VarColorLine()
    colorLine.Extend = ExtendMode.PAD
    return colorLine


def _defaultPaintSolid():
    paint = ot.Paint()
    paint.Alpha = _DEFAULT_ALPHA
    return paint


def _buildPaintCallbacks():
    return {
        (
            BuildCallback.BEFORE_BUILD,
            ot.Paint,
            ot.PaintFormat.PaintRadialGradient,
        ): _beforeBuildPaintRadialGradient,
        (
            BuildCallback.BEFORE_BUILD,
            ot.Paint,
            ot.PaintFormat.PaintVarRadialGradient,
        ): _beforeBuildPaintRadialGradient,
        (BuildCallback.CREATE_DEFAULT, ot.ColorStop): _defaultColorStop,
        (BuildCallback.CREATE_DEFAULT, ot.VarColorStop): _defaultVarColorStop,
        (BuildCallback.CREATE_DEFAULT, ot.ColorLine): _defaultColorLine,
        (BuildCallback.CREATE_DEFAULT, ot.VarColorLine): _defaultVarColorLine,
        (
            BuildCallback.CREATE_DEFAULT,
            ot.Paint,
            ot.PaintFormat.PaintSolid,
        ): _defaultPaintSolid,
        (
            BuildCallback.CREATE_DEFAULT,
            ot.Paint,
            ot.PaintFormat.PaintVarSolid,
        ): _defaultPaintSolid,
    }


def populateCOLRv0(
    table: ot.COLR,
    colorGlyphsV0: _ColorGlyphsV0Dict,
    glyphMap: Optional[Mapping[str, int]] = None,
):
    """Build v0 color layers and add to existing COLR table.

    Args:
        table: a raw ``otTables.COLR()`` object (not ttLib's ``table_C_O_L_R_``).
        colorGlyphsV0: map of base glyph names to lists of (layer glyph names,
            color palette index) tuples. Can be empty.
        glyphMap: a map from glyph names to glyph indices, as returned from
            ``TTFont.getReverseGlyphMap()``, to optionally sort base records by GID.
    """
    if glyphMap is not None:
        colorGlyphItems = sorted(
            colorGlyphsV0.items(), key=lambda item: glyphMap[item[0]]
        )
    else:
        colorGlyphItems = colorGlyphsV0.items()
    baseGlyphRecords = []
    layerRecords = []
    for baseGlyph, layers in colorGlyphItems:
        baseRec = ot.BaseGlyphRecord()
        baseRec.BaseGlyph = baseGlyph
        baseRec.FirstLayerIndex = len(layerRecords)
        baseRec.NumLayers = len(layers)
        baseGlyphRecords.append(baseRec)

        for layerGlyph, paletteIndex in layers:
            layerRec = ot.LayerRecord()
            layerRec.LayerGlyph = layerGlyph
            layerRec.PaletteIndex = paletteIndex
            layerRecords.append(layerRec)

    table.BaseGlyphRecordArray = table.LayerRecordArray = None
    if baseGlyphRecords:
        table.BaseGlyphRecordArray = ot.BaseGlyphRecordArray()
        table.BaseGlyphRecordArray.BaseGlyphRecord = baseGlyphRecords
    if layerRecords:
        table.LayerRecordArray = ot.LayerRecordArray()
        table.LayerRecordArray.LayerRecord = layerRecords
    table.BaseGlyphRecordCount = len(baseGlyphRecords)
    table.LayerRecordCount = len(layerRecords)


def buildCOLR(
    colorGlyphs: _ColorGlyphsDict,
    version: Optional[int] = None,
    *,
    glyphMap: Optional[Mapping[str, int]] = None,
    varStore: Optional[ot.VarStore] = None,
    varIndexMap: Optional[ot.DeltaSetIndexMap] = None,
    clipBoxes: Optional[Dict[str, _ClipBoxInput]] = None,
    allowLayerReuse: bool = True,
) -> C_O_L_R_.table_C_O_L_R_:
    """Build COLR table from color layers mapping.

    Args:

        colorGlyphs: map of base glyph name to, either list of (layer glyph name,
            color palette index) tuples for COLRv0; or a single ``Paint`` (dict) or
            list of ``Paint`` for COLRv1.
        version: the version of COLR table. If None, the version is determined
            by the presence of COLRv1 paints or variation data (varStore), which
            require version 1; otherwise, if all base glyphs use only simple color
            layers, version 0 is used.
        glyphMap: a map from glyph names to glyph indices, as returned from
            TTFont.getReverseGlyphMap(), to optionally sort base records by GID.
        varStore: Optional ItemVarationStore for deltas associated with v1 layer.
        varIndexMap: Optional DeltaSetIndexMap for deltas associated with v1 layer.
        clipBoxes: Optional map of base glyph name to clip box 4- or 5-tuples:
            (xMin, yMin, xMax, yMax) or (xMin, yMin, xMax, yMax, varIndexBase).

    Returns:
        A new COLR table.
    """
    self = C_O_L_R_.table_C_O_L_R_()

    if varStore is not None and version == 0:
        raise ValueError("Can't add VarStore to COLRv0")

    if version in (None, 0) and not varStore:
        # split color glyphs into v0 and v1 and encode separately
        colorGlyphsV0, colorGlyphsV1 = _split_color_glyphs_by_version(colorGlyphs)
        if version == 0 and colorGlyphsV1:
            raise ValueError("Can't encode COLRv1 glyphs in COLRv0")
    else:
        # unless explicitly requested for v1 or have variations, in which case
        # we encode all color glyph as v1
        colorGlyphsV0, colorGlyphsV1 = {}, colorGlyphs

    colr = ot.COLR()

    populateCOLRv0(colr, colorGlyphsV0, glyphMap)

    colr.LayerList, colr.BaseGlyphList = buildColrV1(
        colorGlyphsV1,
        glyphMap,
        allowLayerReuse=allowLayerReuse,
    )

    if version is None:
        version = 1 if (varStore or colorGlyphsV1) else 0
    elif version not in (0, 1):
        raise NotImplementedError(version)
    self.version = colr.Version = version

    if version == 0:
        self.ColorLayers = self._decompileColorLayersV0(colr)
    else:
        colr.ClipList = buildClipList(clipBoxes) if clipBoxes else None
        colr.VarIndexMap = varIndexMap
        colr.VarStore = varStore
        self.table = colr

    return self


def buildClipList(clipBoxes: Dict[str, _ClipBoxInput]) -> ot.ClipList:
    clipList = ot.ClipList()
    clipList.Format = 1
    clipList.clips = {name: buildClipBox(box) for name, box in clipBoxes.items()}
    return clipList


def buildClipBox(clipBox: _ClipBoxInput) -> ot.ClipBox:
    if isinstance(clipBox, ot.ClipBox):
        return clipBox
    n = len(clipBox)
    clip = ot.ClipBox()
    if n not in (4, 5):
        raise ValueError(f"Invalid ClipBox: expected 4 or 5 values, found {n}")
    clip.xMin, clip.yMin, clip.xMax, clip.yMax = intRect(clipBox[:4])
    clip.Format = int(n == 5) + 1
    if n == 5:
        clip.VarIndexBase = int(clipBox[4])
    return clip


class ColorPaletteType(enum.IntFlag):
    USABLE_WITH_LIGHT_BACKGROUND = 0x0001
    USABLE_WITH_DARK_BACKGROUND = 0x0002

    @classmethod
    def _missing_(cls, value):
        # enforce reserved bits
        if isinstance(value, int) and (value < 0 or value & 0xFFFC != 0):
            raise ValueError(f"{value} is not a valid {cls.__name__}")
        return super()._missing_(value)


# None, 'abc' or {'en': 'abc', 'de': 'xyz'}
_OptionalLocalizedString = Union[None, str, Dict[str, str]]


def buildPaletteLabels(
    labels: Iterable[_OptionalLocalizedString], nameTable: _n_a_m_e.table__n_a_m_e
) -> List[Optional[int]]:
    return [
        (
            nameTable.addMultilingualName(l, mac=False)
            if isinstance(l, dict)
            else (
                C_P_A_L_.table_C_P_A_L_.NO_NAME_ID
                if l is None
                else nameTable.addMultilingualName({"en": l}, mac=False)
            )
        )
        for l in labels
    ]


def buildCPAL(
    palettes: Sequence[Sequence[Tuple[float, float, float, float]]],
    paletteTypes: Optional[Sequence[ColorPaletteType]] = None,
    paletteLabels: Optional[Sequence[_OptionalLocalizedString]] = None,
    paletteEntryLabels: Optional[Sequence[_OptionalLocalizedString]] = None,
    nameTable: Optional[_n_a_m_e.table__n_a_m_e] = None,
) -> C_P_A_L_.table_C_P_A_L_:
    """Build CPAL table from list of color palettes.

    Args:
        palettes: list of lists of colors encoded as tuples of (R, G, B, A) floats
            in the range [0..1].
        paletteTypes: optional list of ColorPaletteType, one for each palette.
        paletteLabels: optional list of palette labels. Each lable can be either:
            None (no label), a string (for for default English labels), or a
            localized string (as a dict keyed with BCP47 language codes).
        paletteEntryLabels: optional list of palette entry labels, one for each
            palette entry (see paletteLabels).
        nameTable: optional name table where to store palette and palette entry
            labels. Required if either paletteLabels or paletteEntryLabels is set.

    Return:
        A new CPAL v0 or v1 table, if custom palette types or labels are specified.
    """
    if len({len(p) for p in palettes}) != 1:
        raise ColorLibError("color palettes have different lengths")

    if (paletteLabels or paletteEntryLabels) and not nameTable:
        raise TypeError(
            "nameTable is required if palette or palette entries have labels"
        )

    cpal = C_P_A_L_.table_C_P_A_L_()
    cpal.numPaletteEntries = len(palettes[0])

    cpal.palettes = []
    for i, palette in enumerate(palettes):
        colors = []
        for j, color in enumerate(palette):
            if not isinstance(color, tuple) or len(color) != 4:
                raise ColorLibError(
                    f"In palette[{i}][{j}]: expected (R, G, B, A) tuple, got {color!r}"
                )
            if any(v > 1 or v < 0 for v in color):
                raise ColorLibError(
                    f"palette[{i}][{j}] has invalid out-of-range [0..1] color: {color!r}"
                )
            # input colors are RGBA, CPAL encodes them as BGRA
            red, green, blue, alpha = color
            colors.append(
                C_P_A_L_.Color(*(round(v * 255) for v in (blue, green, red, alpha)))
            )
        cpal.palettes.append(colors)

    if any(v is not None for v in (paletteTypes, paletteLabels, paletteEntryLabels)):
        cpal.version = 1

        if paletteTypes is not None:
            if len(paletteTypes) != len(palettes):
                raise ColorLibError(
                    f"Expected {len(palettes)} paletteTypes, got {len(paletteTypes)}"
                )
            cpal.paletteTypes = [ColorPaletteType(t).value for t in paletteTypes]
        else:
            cpal.paletteTypes = [C_P_A_L_.table_C_P_A_L_.DEFAULT_PALETTE_TYPE] * len(
                palettes
            )

        if paletteLabels is not None:
            if len(paletteLabels) != len(palettes):
                raise ColorLibError(
                    f"Expected {len(palettes)} paletteLabels, got {len(paletteLabels)}"
                )
            cpal.paletteLabels = buildPaletteLabels(paletteLabels, nameTable)
        else:
            cpal.paletteLabels = [C_P_A_L_.table_C_P_A_L_.NO_NAME_ID] * len(palettes)

        if paletteEntryLabels is not None:
            if len(paletteEntryLabels) != cpal.numPaletteEntries:
                raise ColorLibError(
                    f"Expected {cpal.numPaletteEntries} paletteEntryLabels, "
                    f"got {len(paletteEntryLabels)}"
                )
            cpal.paletteEntryLabels = buildPaletteLabels(paletteEntryLabels, nameTable)
        else:
            cpal.paletteEntryLabels = [
                C_P_A_L_.table_C_P_A_L_.NO_NAME_ID
            ] * cpal.numPaletteEntries
    else:
        cpal.version = 0

    return cpal


# COLR v1 tables
# See draft proposal at: https://github.com/googlefonts/colr-gradients-spec


def _is_colrv0_layer(layer: Any) -> bool:
    # Consider as COLRv0 layer any sequence of length 2 (be it tuple or list) in which
    # the first element is a str (the layerGlyph) and the second element is an int
    # (CPAL paletteIndex).
    # https://github.com/googlefonts/ufo2ft/issues/426
    try:
        layerGlyph, paletteIndex = layer
    except (TypeError, ValueError):
        return False
    else:
        return isinstance(layerGlyph, str) and isinstance(paletteIndex, int)


def _split_color_glyphs_by_version(
    colorGlyphs: _ColorGlyphsDict,
) -> Tuple[_ColorGlyphsV0Dict, _ColorGlyphsDict]:
    colorGlyphsV0 = {}
    colorGlyphsV1 = {}
    for baseGlyph, layers in colorGlyphs.items():
        if all(_is_colrv0_layer(l) for l in layers):
            colorGlyphsV0[baseGlyph] = layers
        else:
            colorGlyphsV1[baseGlyph] = layers

    # sanity check
    assert set(colorGlyphs) == (set(colorGlyphsV0) | set(colorGlyphsV1))

    return colorGlyphsV0, colorGlyphsV1


def _reuse_ranges(num_layers: int) -> Generator[Tuple[int, int], None, None]:
    # TODO feels like something itertools might have already
    for lbound in range(num_layers):
        # Reuse of very large #s of layers is relatively unlikely
        # +2: we want sequences of at least 2
        # otData handles single-record duplication
        for ubound in range(
            lbound + 2, min(num_layers + 1, lbound + 2 + _MAX_REUSE_LEN)
        ):
            yield (lbound, ubound)


class LayerReuseCache:
    reusePool: Mapping[Tuple[Any, ...], int]
    tuples: Mapping[int, Tuple[Any, ...]]
    keepAlive: List[ot.Paint]  # we need id to remain valid

    def __init__(self):
        self.reusePool = {}
        self.tuples = {}
        self.keepAlive = []

    def _paint_tuple(self, paint: ot.Paint):
        # start simple, who even cares about cyclic graphs or interesting field types
        def _tuple_safe(value):
            if isinstance(value, enum.Enum):
                return value
            elif hasattr(value, "__dict__"):
                return tuple(
                    (k, _tuple_safe(v)) for k, v in sorted(value.__dict__.items())
                )
            elif isinstance(value, collections.abc.MutableSequence):
                return tuple(_tuple_safe(e) for e in value)
            return value

        # Cache the tuples for individual Paint instead of the whole sequence
        # because the seq could be a transient slice
        result = self.tuples.get(id(paint), None)
        if result is None:
            result = _tuple_safe(paint)
            self.tuples[id(paint)] = result
            self.keepAlive.append(paint)
        return result

    def _as_tuple(self, paints: Sequence[ot.Paint]) -> Tuple[Any, ...]:
        return tuple(self._paint_tuple(p) for p in paints)

    def try_reuse(self, layers: List[ot.Paint]) -> List[ot.Paint]:
        found_reuse = True
        while found_reuse:
            found_reuse = False

            ranges = sorted(
                _reuse_ranges(len(layers)),
                key=lambda t: (t[1] - t[0], t[1], t[0]),
                reverse=True,
            )
            for lbound, ubound in ranges:
                reuse_lbound = self.reusePool.get(
                    self._as_tuple(layers[lbound:ubound]), -1
                )
                if reuse_lbound == -1:
                    continue
                new_slice = ot.Paint()
                new_slice.Format = int(ot.PaintFormat.PaintColrLayers)
                new_slice.NumLayers = ubound - lbound
                new_slice.FirstLayerIndex = reuse_lbound
                layers = layers[:lbound] + [new_slice] + layers[ubound:]
                found_reuse = True
                break
        return layers

    def add(self, layers: List[ot.Paint], first_layer_index: int):
        for lbound, ubound in _reuse_ranges(len(layers)):
            self.reusePool[self._as_tuple(layers[lbound:ubound])] = (
                lbound + first_layer_index
            )


class LayerListBuilder:
    layers: List[ot.Paint]
    cache: LayerReuseCache
    allowLayerReuse: bool

    def __init__(self, *, allowLayerReuse=True):
        self.layers = []
        if allowLayerReuse:
            self.cache = LayerReuseCache()
        else:
            self.cache = None

        # We need to intercept construction of PaintColrLayers
        callbacks = _buildPaintCallbacks()
        callbacks[
            (
                BuildCallback.BEFORE_BUILD,
                ot.Paint,
                ot.PaintFormat.PaintColrLayers,
            )
        ] = self._beforeBuildPaintColrLayers
        self.tableBuilder = TableBuilder(callbacks)

    # COLR layers is unusual in that it modifies shared state
    # so we need a callback into an object
    def _beforeBuildPaintColrLayers(self, dest, source):
        # Sketchy gymnastics: a sequence input will have dropped it's layers
        # into NumLayers; get it back
        if isinstance(source.get("NumLayers", None), collections.abc.Sequence):
            layers = source["NumLayers"]
        else:
            layers = source["Layers"]

        # Convert maps seqs or whatever into typed objects
        layers = [self.buildPaint(l) for l in layers]

        # No reason to have a colr layers with just one entry
        if len(layers) == 1:
            return layers[0], {}

        if self.cache is not None:
            # Look for reuse, with preference to longer sequences
            # This may make the layer list smaller
            layers = self.cache.try_reuse(layers)

        # The layer list is now final; if it's too big we need to tree it
        is_tree = len(layers) > MAX_PAINT_COLR_LAYER_COUNT
        layers = build_n_ary_tree(layers, n=MAX_PAINT_COLR_LAYER_COUNT)

        # We now have a tree of sequences with Paint leaves.
        # Convert the sequences into PaintColrLayers.
        def listToColrLayers(layer):
            if isinstance(layer, collections.abc.Sequence):
                return self.buildPaint(
                    {
                        "Format": ot.PaintFormat.PaintColrLayers,
                        "Layers": [listToColrLayers(l) for l in layer],
                    }
                )
            return layer

        layers = [listToColrLayers(l) for l in layers]

        # No reason to have a colr layers with just one entry
        if len(layers) == 1:
            return layers[0], {}

        paint = ot.Paint()
        paint.Format = int(ot.PaintFormat.PaintColrLayers)
        paint.NumLayers = len(layers)
        paint.FirstLayerIndex = len(self.layers)
        self.layers.extend(layers)

        # Register our parts for reuse provided we aren't a tree
        # If we are a tree the leaves registered for reuse and that will suffice
        if self.cache is not None and not is_tree:
            self.cache.add(layers, paint.FirstLayerIndex)

        # we've fully built dest; empty source prevents generalized build from kicking in
        return paint, {}

    def buildPaint(self, paint: _PaintInput) -> ot.Paint:
        return self.tableBuilder.build(ot.Paint, paint)

    def build(self) -> Optional[ot.LayerList]:
        if not self.layers:
            return None
        layers = ot.LayerList()
        layers.LayerCount = len(self.layers)
        layers.Paint = self.layers
        return layers


def buildBaseGlyphPaintRecord(
    baseGlyph: str, layerBuilder: LayerListBuilder, paint: _PaintInput
) -> ot.BaseGlyphList:
    self = ot.BaseGlyphPaintRecord()
    self.BaseGlyph = baseGlyph
    self.Paint = layerBuilder.buildPaint(paint)
    return self


def _format_glyph_errors(errors: Mapping[str, Exception]) -> str:
    lines = []
    for baseGlyph, error in sorted(errors.items()):
        lines.append(f"    {baseGlyph} => {type(error).__name__}: {error}")
    return "\n".join(lines)


def buildColrV1(
    colorGlyphs: _ColorGlyphsDict,
    glyphMap: Optional[Mapping[str, int]] = None,
    *,
    allowLayerReuse: bool = True,
) -> Tuple[Optional[ot.LayerList], ot.BaseGlyphList]:
    if glyphMap is not None:
        colorGlyphItems = sorted(
            colorGlyphs.items(), key=lambda item: glyphMap[item[0]]
        )
    else:
        colorGlyphItems = colorGlyphs.items()

    errors = {}
    baseGlyphs = []
    layerBuilder = LayerListBuilder(allowLayerReuse=allowLayerReuse)
    for baseGlyph, paint in colorGlyphItems:
        try:
            baseGlyphs.append(buildBaseGlyphPaintRecord(baseGlyph, layerBuilder, paint))

        except (ColorLibError, OverflowError, ValueError, TypeError) as e:
            errors[baseGlyph] = e

    if errors:
        failed_glyphs = _format_glyph_errors(errors)
        exc = ColorLibError(f"Failed to build BaseGlyphList:\n{failed_glyphs}")
        exc.errors = errors
        raise exc from next(iter(errors.values()))

    layers = layerBuilder.build()
    glyphs = ot.BaseGlyphList()
    glyphs.BaseGlyphCount = len(baseGlyphs)
    glyphs.BaseGlyphPaintRecord = baseGlyphs
    return (layers, glyphs)

# === NexusCore/openenv\Lib\site-packages\fontTools\voltLib\parser.py ===
import fontTools.voltLib.ast as ast
from fontTools.voltLib.lexer import Lexer
from fontTools.voltLib.error import VoltLibError
from io import open

PARSE_FUNCS = {
    "DEF_GLYPH": "parse_def_glyph_",
    "DEF_GROUP": "parse_def_group_",
    "DEF_SCRIPT": "parse_def_script_",
    "DEF_LOOKUP": "parse_def_lookup_",
    "DEF_ANCHOR": "parse_def_anchor_",
    "GRID_PPEM": "parse_ppem_",
    "PRESENTATION_PPEM": "parse_ppem_",
    "PPOSITIONING_PPEM": "parse_ppem_",
    "COMPILER_USEEXTENSIONLOOKUPS": "parse_noarg_option_",
    "COMPILER_USEPAIRPOSFORMAT2": "parse_noarg_option_",
    "CMAP_FORMAT": "parse_cmap_format",
    "DO_NOT_TOUCH_CMAP": "parse_noarg_option_",
}


class Parser(object):
    def __init__(self, path):
        self.doc_ = ast.VoltFile()
        self.glyphs_ = OrderedSymbolTable()
        self.groups_ = SymbolTable()
        self.anchors_ = {}  # dictionary of SymbolTable() keyed by glyph
        self.scripts_ = SymbolTable()
        self.langs_ = SymbolTable()
        self.lookups_ = SymbolTable()
        self.next_token_type_, self.next_token_ = (None, None)
        self.next_token_location_ = None
        self.make_lexer_(path)
        self.advance_lexer_()

    def make_lexer_(self, file_or_path):
        if hasattr(file_or_path, "read"):
            filename = getattr(file_or_path, "name", None)
            data = file_or_path.read()
        else:
            filename = file_or_path
            with open(file_or_path, "r") as f:
                data = f.read()
        self.lexer_ = Lexer(data, filename)

    def parse(self):
        statements = self.doc_.statements
        while self.next_token_type_ is not None:
            self.advance_lexer_()
            if self.cur_token_ in PARSE_FUNCS.keys():
                func = getattr(self, PARSE_FUNCS[self.cur_token_])
                statements.append(func())
            elif self.is_cur_keyword_("END"):
                break
            else:
                raise VoltLibError(
                    "Expected " + ", ".join(sorted(PARSE_FUNCS.keys())),
                    self.cur_token_location_,
                )
        return self.doc_

    def parse_def_glyph_(self):
        assert self.is_cur_keyword_("DEF_GLYPH")
        location = self.cur_token_location_
        name = self.expect_string_()
        self.expect_keyword_("ID")
        gid = self.expect_number_()
        if gid < 0:
            raise VoltLibError("Invalid glyph ID", self.cur_token_location_)
        gunicode = None
        if self.next_token_ == "UNICODE":
            self.expect_keyword_("UNICODE")
            gunicode = [self.expect_number_()]
            if gunicode[0] < 0:
                raise VoltLibError("Invalid glyph UNICODE", self.cur_token_location_)
        elif self.next_token_ == "UNICODEVALUES":
            self.expect_keyword_("UNICODEVALUES")
            gunicode = self.parse_unicode_values_()
        gtype = None
        if self.next_token_ == "TYPE":
            self.expect_keyword_("TYPE")
            gtype = self.expect_name_()
            assert gtype in ("BASE", "LIGATURE", "MARK", "COMPONENT")
        components = None
        if self.next_token_ == "COMPONENTS":
            self.expect_keyword_("COMPONENTS")
            components = self.expect_number_()
        self.expect_keyword_("END_GLYPH")
        if self.glyphs_.resolve(name) is not None:
            raise VoltLibError(
                'Glyph "%s" (gid %i) already defined' % (name, gid), location
            )
        def_glyph = ast.GlyphDefinition(
            name, gid, gunicode, gtype, components, location=location
        )
        self.glyphs_.define(name, def_glyph)
        return def_glyph

    def parse_def_group_(self):
        assert self.is_cur_keyword_("DEF_GROUP")
        location = self.cur_token_location_
        name = self.expect_string_()
        enum = None
        if self.next_token_ == "ENUM":
            enum = self.parse_enum_()
        self.expect_keyword_("END_GROUP")
        if self.groups_.resolve(name) is not None:
            raise VoltLibError(
                'Glyph group "%s" already defined, '
                "group names are case insensitive" % name,
                location,
            )
        def_group = ast.GroupDefinition(name, enum, location=location)
        self.groups_.define(name, def_group)
        return def_group

    def parse_def_script_(self):
        assert self.is_cur_keyword_("DEF_SCRIPT")
        location = self.cur_token_location_
        name = None
        if self.next_token_ == "NAME":
            self.expect_keyword_("NAME")
            name = self.expect_string_()
        self.expect_keyword_("TAG")
        tag = self.expect_string_()
        if self.scripts_.resolve(tag) is not None:
            raise VoltLibError(
                'Script "%s" already defined, '
                "script tags are case insensitive" % tag,
                location,
            )
        self.langs_.enter_scope()
        langs = []
        while self.next_token_ != "END_SCRIPT":
            self.advance_lexer_()
            lang = self.parse_langsys_()
            self.expect_keyword_("END_LANGSYS")
            if self.langs_.resolve(lang.tag) is not None:
                raise VoltLibError(
                    'Language "%s" already defined in script "%s", '
                    "language tags are case insensitive" % (lang.tag, tag),
                    location,
                )
            self.langs_.define(lang.tag, lang)
            langs.append(lang)
        self.expect_keyword_("END_SCRIPT")
        self.langs_.exit_scope()
        def_script = ast.ScriptDefinition(name, tag, langs, location=location)
        self.scripts_.define(tag, def_script)
        return def_script

    def parse_langsys_(self):
        assert self.is_cur_keyword_("DEF_LANGSYS")
        location = self.cur_token_location_
        name = None
        if self.next_token_ == "NAME":
            self.expect_keyword_("NAME")
            name = self.expect_string_()
        self.expect_keyword_("TAG")
        tag = self.expect_string_()
        features = []
        while self.next_token_ != "END_LANGSYS":
            self.advance_lexer_()
            feature = self.parse_feature_()
            self.expect_keyword_("END_FEATURE")
            features.append(feature)
        def_langsys = ast.LangSysDefinition(name, tag, features, location=location)
        return def_langsys

    def parse_feature_(self):
        assert self.is_cur_keyword_("DEF_FEATURE")
        location = self.cur_token_location_
        self.expect_keyword_("NAME")
        name = self.expect_string_()
        self.expect_keyword_("TAG")
        tag = self.expect_string_()
        lookups = []
        while self.next_token_ != "END_FEATURE":
            # self.advance_lexer_()
            self.expect_keyword_("LOOKUP")
            lookup = self.expect_string_()
            lookups.append(lookup)
        feature = ast.FeatureDefinition(name, tag, lookups, location=location)
        return feature

    def parse_def_lookup_(self):
        assert self.is_cur_keyword_("DEF_LOOKUP")
        location = self.cur_token_location_
        name = self.expect_string_()
        if not name[0].isalpha():
            raise VoltLibError(
                'Lookup name "%s" must start with a letter' % name, location
            )
        if self.lookups_.resolve(name) is not None:
            raise VoltLibError(
                'Lookup "%s" already defined, '
                "lookup names are case insensitive" % name,
                location,
            )
        process_base = True
        if self.next_token_ == "PROCESS_BASE":
            self.advance_lexer_()
        elif self.next_token_ == "SKIP_BASE":
            self.advance_lexer_()
            process_base = False
        process_marks = True
        mark_glyph_set = None
        if self.next_token_ == "PROCESS_MARKS":
            self.advance_lexer_()
            if self.next_token_ == "MARK_GLYPH_SET":
                self.advance_lexer_()
                mark_glyph_set = self.expect_string_()
            elif self.next_token_ == "ALL":
                self.advance_lexer_()
            elif self.next_token_ == "NONE":
                self.advance_lexer_()
                process_marks = False
            elif self.next_token_type_ == Lexer.STRING:
                process_marks = self.expect_string_()
            else:
                raise VoltLibError(
                    "Expected ALL, NONE, MARK_GLYPH_SET or an ID. "
                    "Got %s" % (self.next_token_type_),
                    location,
                )
        elif self.next_token_ == "SKIP_MARKS":
            self.advance_lexer_()
            process_marks = False
        direction = None
        if self.next_token_ == "DIRECTION":
            self.expect_keyword_("DIRECTION")
            direction = self.expect_name_()
            assert direction in ("LTR", "RTL")
        reversal = None
        if self.next_token_ == "REVERSAL":
            self.expect_keyword_("REVERSAL")
            reversal = True
        comments = None
        if self.next_token_ == "COMMENTS":
            self.expect_keyword_("COMMENTS")
            comments = self.expect_string_().replace(r"\n", "\n")
        context = []
        while self.next_token_ in ("EXCEPT_CONTEXT", "IN_CONTEXT"):
            context = self.parse_context_()
        as_pos_or_sub = self.expect_name_()
        sub = None
        pos = None
        if as_pos_or_sub == "AS_SUBSTITUTION":
            sub = self.parse_substitution_(reversal)
        elif as_pos_or_sub == "AS_POSITION":
            pos = self.parse_position_()
        else:
            raise VoltLibError(
                "Expected AS_SUBSTITUTION or AS_POSITION. " "Got %s" % (as_pos_or_sub),
                location,
            )
        def_lookup = ast.LookupDefinition(
            name,
            process_base,
            process_marks,
            mark_glyph_set,
            direction,
            reversal,
            comments,
            context,
            sub,
            pos,
            location=location,
        )
        self.lookups_.define(name, def_lookup)
        return def_lookup

    def parse_context_(self):
        location = self.cur_token_location_
        contexts = []
        while self.next_token_ in ("EXCEPT_CONTEXT", "IN_CONTEXT"):
            side = None
            coverage = None
            ex_or_in = self.expect_name_()
            # side_contexts = [] # XXX
            if self.next_token_ != "END_CONTEXT":
                left = []
                right = []
                while self.next_token_ in ("LEFT", "RIGHT"):
                    side = self.expect_name_()
                    coverage = self.parse_coverage_()
                    if side == "LEFT":
                        left.append(coverage)
                    else:
                        right.append(coverage)
                self.expect_keyword_("END_CONTEXT")
                context = ast.ContextDefinition(
                    ex_or_in, left, right, location=location
                )
                contexts.append(context)
            else:
                self.expect_keyword_("END_CONTEXT")
        return contexts

    def parse_substitution_(self, reversal):
        assert self.is_cur_keyword_("AS_SUBSTITUTION")
        location = self.cur_token_location_
        src = []
        dest = []
        if self.next_token_ != "SUB":
            raise VoltLibError("Expected SUB", location)
        while self.next_token_ == "SUB":
            self.expect_keyword_("SUB")
            src.append(self.parse_coverage_())
            self.expect_keyword_("WITH")
            dest.append(self.parse_coverage_())
            self.expect_keyword_("END_SUB")
        self.expect_keyword_("END_SUBSTITUTION")
        max_src = max([len(cov) for cov in src])
        max_dest = max([len(cov) for cov in dest])

        # many to many or mixed is invalid
        if max_src > 1 and max_dest > 1:
            raise VoltLibError("Invalid substitution type", location)

        mapping = dict(zip(tuple(src), tuple(dest)))
        if max_src == 1 and max_dest == 1:
            # Alternate substitutions are represented by adding multiple
            # substitutions for the same glyph, so we detect that here
            glyphs = [x.glyphSet() for cov in src for x in cov]  # flatten src
            if len(set(glyphs)) != len(glyphs):  # src has duplicates
                sub = ast.SubstitutionAlternateDefinition(mapping, location=location)
            else:
                if reversal:
                    # Reversal is valid only for single glyph substitutions
                    # and VOLT ignores it otherwise.
                    sub = ast.SubstitutionReverseChainingSingleDefinition(
                        mapping, location=location
                    )
                else:
                    sub = ast.SubstitutionSingleDefinition(mapping, location=location)
        elif max_src == 1 and max_dest > 1:
            sub = ast.SubstitutionMultipleDefinition(mapping, location=location)
        elif max_src > 1 and max_dest == 1:
            sub = ast.SubstitutionLigatureDefinition(mapping, location=location)
        return sub

    def parse_position_(self):
        assert self.is_cur_keyword_("AS_POSITION")
        location = self.cur_token_location_
        pos_type = self.expect_name_()
        if pos_type not in ("ATTACH", "ATTACH_CURSIVE", "ADJUST_PAIR", "ADJUST_SINGLE"):
            raise VoltLibError(
                "Expected ATTACH, ATTACH_CURSIVE, ADJUST_PAIR, ADJUST_SINGLE", location
            )
        if pos_type == "ATTACH":
            position = self.parse_attach_()
        elif pos_type == "ATTACH_CURSIVE":
            position = self.parse_attach_cursive_()
        elif pos_type == "ADJUST_PAIR":
            position = self.parse_adjust_pair_()
        elif pos_type == "ADJUST_SINGLE":
            position = self.parse_adjust_single_()
        self.expect_keyword_("END_POSITION")
        return position

    def parse_attach_(self):
        assert self.is_cur_keyword_("ATTACH")
        location = self.cur_token_location_
        coverage = self.parse_coverage_()
        coverage_to = []
        self.expect_keyword_("TO")
        while self.next_token_ != "END_ATTACH":
            cov = self.parse_coverage_()
            self.expect_keyword_("AT")
            self.expect_keyword_("ANCHOR")
            anchor_name = self.expect_string_()
            coverage_to.append((cov, anchor_name))
        self.expect_keyword_("END_ATTACH")
        position = ast.PositionAttachDefinition(
            coverage, coverage_to, location=location
        )
        return position

    def parse_attach_cursive_(self):
        assert self.is_cur_keyword_("ATTACH_CURSIVE")
        location = self.cur_token_location_
        coverages_exit = []
        coverages_enter = []
        while self.next_token_ != "ENTER":
            self.expect_keyword_("EXIT")
            coverages_exit.append(self.parse_coverage_())
        while self.next_token_ != "END_ATTACH":
            self.expect_keyword_("ENTER")
            coverages_enter.append(self.parse_coverage_())
        self.expect_keyword_("END_ATTACH")
        position = ast.PositionAttachCursiveDefinition(
            coverages_exit, coverages_enter, location=location
        )
        return position

    def parse_adjust_pair_(self):
        assert self.is_cur_keyword_("ADJUST_PAIR")
        location = self.cur_token_location_
        coverages_1 = []
        coverages_2 = []
        adjust_pair = {}
        while self.next_token_ == "FIRST":
            self.advance_lexer_()
            coverage_1 = self.parse_coverage_()
            coverages_1.append(coverage_1)
        while self.next_token_ == "SECOND":
            self.advance_lexer_()
            coverage_2 = self.parse_coverage_()
            coverages_2.append(coverage_2)
        while self.next_token_ != "END_ADJUST":
            id_1 = self.expect_number_()
            id_2 = self.expect_number_()
            self.expect_keyword_("BY")
            pos_1 = self.parse_pos_()
            pos_2 = self.parse_pos_()
            adjust_pair[(id_1, id_2)] = (pos_1, pos_2)
        self.expect_keyword_("END_ADJUST")
        position = ast.PositionAdjustPairDefinition(
            coverages_1, coverages_2, adjust_pair, location=location
        )
        return position

    def parse_adjust_single_(self):
        assert self.is_cur_keyword_("ADJUST_SINGLE")
        location = self.cur_token_location_
        adjust_single = []
        while self.next_token_ != "END_ADJUST":
            coverages = self.parse_coverage_()
            self.expect_keyword_("BY")
            pos = self.parse_pos_()
            adjust_single.append((coverages, pos))
        self.expect_keyword_("END_ADJUST")
        position = ast.PositionAdjustSingleDefinition(adjust_single, location=location)
        return position

    def parse_def_anchor_(self):
        assert self.is_cur_keyword_("DEF_ANCHOR")
        location = self.cur_token_location_
        name = self.expect_string_()
        self.expect_keyword_("ON")
        gid = self.expect_number_()
        self.expect_keyword_("GLYPH")
        glyph_name = self.expect_name_()
        self.expect_keyword_("COMPONENT")
        component = self.expect_number_()
        # check for duplicate anchor names on this glyph
        if glyph_name in self.anchors_:
            anchor = self.anchors_[glyph_name].resolve(name)
            if anchor is not None and anchor.component == component:
                raise VoltLibError(
                    'Anchor "%s" already defined, '
                    "anchor names are case insensitive" % name,
                    location,
                )
        if self.next_token_ == "LOCKED":
            locked = True
            self.advance_lexer_()
        else:
            locked = False
        self.expect_keyword_("AT")
        pos = self.parse_pos_()
        self.expect_keyword_("END_ANCHOR")
        anchor = ast.AnchorDefinition(
            name, gid, glyph_name, component, locked, pos, location=location
        )
        if glyph_name not in self.anchors_:
            self.anchors_[glyph_name] = SymbolTable()
        self.anchors_[glyph_name].define(name, anchor)
        return anchor

    def parse_adjust_by_(self):
        self.advance_lexer_()
        assert self.is_cur_keyword_("ADJUST_BY")
        adjustment = self.expect_number_()
        self.expect_keyword_("AT")
        size = self.expect_number_()
        return adjustment, size

    def parse_pos_(self):
        # VOLT syntax doesn't seem to take device Y advance
        self.advance_lexer_()
        location = self.cur_token_location_
        assert self.is_cur_keyword_("POS"), location
        adv = None
        dx = None
        dy = None
        adv_adjust_by = {}
        dx_adjust_by = {}
        dy_adjust_by = {}
        if self.next_token_ == "ADV":
            self.advance_lexer_()
            adv = self.expect_number_()
            while self.next_token_ == "ADJUST_BY":
                adjustment, size = self.parse_adjust_by_()
                adv_adjust_by[size] = adjustment
        if self.next_token_ == "DX":
            self.advance_lexer_()
            dx = self.expect_number_()
            while self.next_token_ == "ADJUST_BY":
                adjustment, size = self.parse_adjust_by_()
                dx_adjust_by[size] = adjustment
        if self.next_token_ == "DY":
            self.advance_lexer_()
            dy = self.expect_number_()
            while self.next_token_ == "ADJUST_BY":
                adjustment, size = self.parse_adjust_by_()
                dy_adjust_by[size] = adjustment
        self.expect_keyword_("END_POS")
        return ast.Pos(adv, dx, dy, adv_adjust_by, dx_adjust_by, dy_adjust_by)

    def parse_unicode_values_(self):
        location = self.cur_token_location_
        try:
            unicode_values = self.expect_string_().split(",")
            unicode_values = [int(uni[2:], 16) for uni in unicode_values if uni != ""]
        except ValueError as err:
            raise VoltLibError(str(err), location)
        return unicode_values if unicode_values != [] else None

    def parse_enum_(self):
        self.expect_keyword_("ENUM")
        location = self.cur_token_location_
        enum = ast.Enum(self.parse_coverage_(), location=location)
        self.expect_keyword_("END_ENUM")
        return enum

    def parse_coverage_(self):
        coverage = []
        location = self.cur_token_location_
        while self.next_token_ in ("GLYPH", "GROUP", "RANGE", "ENUM"):
            if self.next_token_ == "ENUM":
                enum = self.parse_enum_()
                coverage.append(enum)
            elif self.next_token_ == "GLYPH":
                self.expect_keyword_("GLYPH")
                name = self.expect_string_()
                coverage.append(ast.GlyphName(name, location=location))
            elif self.next_token_ == "GROUP":
                self.expect_keyword_("GROUP")
                name = self.expect_string_()
                coverage.append(ast.GroupName(name, self, location=location))
            elif self.next_token_ == "RANGE":
                self.expect_keyword_("RANGE")
                start = self.expect_string_()
                self.expect_keyword_("TO")
                end = self.expect_string_()
                coverage.append(ast.Range(start, end, self, location=location))
        return tuple(coverage)

    def resolve_group(self, group_name):
        return self.groups_.resolve(group_name)

    def glyph_range(self, start, end):
        return self.glyphs_.range(start, end)

    def parse_ppem_(self):
        location = self.cur_token_location_
        ppem_name = self.cur_token_
        value = self.expect_number_()
        setting = ast.SettingDefinition(ppem_name, value, location=location)
        return setting

    def parse_noarg_option_(self):
        location = self.cur_token_location_
        name = self.cur_token_
        value = True
        setting = ast.SettingDefinition(name, value, location=location)
        return setting

    def parse_cmap_format(self):
        location = self.cur_token_location_
        name = self.cur_token_
        value = (self.expect_number_(), self.expect_number_(), self.expect_number_())
        setting = ast.SettingDefinition(name, value, location=location)
        return setting

    def is_cur_keyword_(self, k):
        return (self.cur_token_type_ is Lexer.NAME) and (self.cur_token_ == k)

    def expect_string_(self):
        self.advance_lexer_()
        if self.cur_token_type_ is not Lexer.STRING:
            raise VoltLibError("Expected a string", self.cur_token_location_)
        return self.cur_token_

    def expect_keyword_(self, keyword):
        self.advance_lexer_()
        if self.cur_token_type_ is Lexer.NAME and self.cur_token_ == keyword:
            return self.cur_token_
        raise VoltLibError('Expected "%s"' % keyword, self.cur_token_location_)

    def expect_name_(self):
        self.advance_lexer_()
        if self.cur_token_type_ is Lexer.NAME:
            return self.cur_token_
        raise VoltLibError("Expected a name", self.cur_token_location_)

    def expect_number_(self):
        self.advance_lexer_()
        if self.cur_token_type_ is not Lexer.NUMBER:
            raise VoltLibError("Expected a number", self.cur_token_location_)
        return self.cur_token_

    def advance_lexer_(self):
        self.cur_token_type_, self.cur_token_, self.cur_token_location_ = (
            self.next_token_type_,
            self.next_token_,
            self.next_token_location_,
        )
        try:
            if self.is_cur_keyword_("END"):
                raise StopIteration
            (
                self.next_token_type_,
                self.next_token_,
                self.next_token_location_,
            ) = self.lexer_.next()
        except StopIteration:
            self.next_token_type_, self.next_token_ = (None, None)


class SymbolTable(object):
    def __init__(self):
        self.scopes_ = [{}]

    def enter_scope(self):
        self.scopes_.append({})

    def exit_scope(self):
        self.scopes_.pop()

    def define(self, name, item):
        self.scopes_[-1][name] = item

    def resolve(self, name, case_insensitive=True):
        for scope in reversed(self.scopes_):
            item = scope.get(name)
            if item:
                return item
        if case_insensitive:
            for key in scope:
                if key.lower() == name.lower():
                    return scope[key]
        return None


class OrderedSymbolTable(SymbolTable):
    def __init__(self):
        self.scopes_ = [{}]

    def enter_scope(self):
        self.scopes_.append({})

    def resolve(self, name, case_insensitive=False):
        SymbolTable.resolve(self, name, case_insensitive=case_insensitive)

    def range(self, start, end):
        for scope in reversed(self.scopes_):
            if start in scope and end in scope:
                start_idx = list(scope.keys()).index(start)
                end_idx = list(scope.keys()).index(end)
                return list(scope.keys())[start_idx : end_idx + 1]
        return None

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\get_llm_provider_logic.py ===
from typing import Optional, Tuple

import httpx

import litellm
from litellm.constants import REPLICATE_MODEL_NAME_WITH_ID_LENGTH
from litellm.secret_managers.main import get_secret, get_secret_str

from ..types.router import LiteLLM_Params


def _is_non_openai_azure_model(model: str) -> bool:
    try:
        model_name = model.split("/", 1)[1]
        if (
            model_name in litellm.cohere_chat_models
            or f"mistral/{model_name}" in litellm.mistral_chat_models
        ):
            return True
    except Exception:
        return False
    return False


def handle_cohere_chat_model_custom_llm_provider(
    model: str, custom_llm_provider: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    if user sets model = "cohere/command-r" -> use custom_llm_provider = "cohere_chat"

    Args:
        model:
        custom_llm_provider:

    Returns:
        model, custom_llm_provider
    """

    if custom_llm_provider:
        if custom_llm_provider == "cohere" and model in litellm.cohere_chat_models:
            return model, "cohere_chat"

    if "/" in model:
        _custom_llm_provider, _model = model.split("/", 1)
        if (
            _custom_llm_provider
            and _custom_llm_provider == "cohere"
            and _model in litellm.cohere_chat_models
        ):
            return _model, "cohere_chat"

    return model, custom_llm_provider


def handle_anthropic_text_model_custom_llm_provider(
    model: str, custom_llm_provider: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    if user sets model = "anthropic/claude-2" -> use custom_llm_provider = "anthropic_text"

    Args:
        model:
        custom_llm_provider:

    Returns:
        model, custom_llm_provider
    """

    if custom_llm_provider:
        if (
            custom_llm_provider == "anthropic"
            and litellm.AnthropicTextConfig._is_anthropic_text_model(model)
        ):
            return model, "anthropic_text"

    if "/" in model:
        _custom_llm_provider, _model = model.split("/", 1)
        if (
            _custom_llm_provider
            and _custom_llm_provider == "anthropic"
            and litellm.AnthropicTextConfig._is_anthropic_text_model(_model)
        ):
            return _model, "anthropic_text"

    return model, custom_llm_provider


def get_llm_provider(  # noqa: PLR0915
    model: str,
    custom_llm_provider: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    litellm_params: Optional[LiteLLM_Params] = None,
) -> Tuple[str, str, Optional[str], Optional[str]]:
    """
    Returns the provider for a given model name - e.g. 'azure/chatgpt-v-2' -> 'azure'

    For router -> Can also give the whole litellm param dict -> this function will extract the relevant details

    Raises Error - if unable to map model to a provider

    Return model, custom_llm_provider, dynamic_api_key, api_base
    """
    try:
        if litellm.LiteLLMProxyChatConfig._should_use_litellm_proxy_by_default(
            litellm_params=litellm_params
        ):
            return litellm.LiteLLMProxyChatConfig.litellm_proxy_get_custom_llm_provider_info(
                model=model, api_base=api_base, api_key=api_key
            )

        ## IF LITELLM PARAMS GIVEN ##
        if litellm_params:
            assert (
                custom_llm_provider is None and api_base is None and api_key is None
            ), "Either pass in litellm_params or the custom_llm_provider/api_base/api_key. Otherwise, these values will be overriden."
            custom_llm_provider = litellm_params.custom_llm_provider
            api_base = litellm_params.api_base
            api_key = litellm_params.api_key

        dynamic_api_key = None
        # check if llm provider provided
        # AZURE AI-Studio Logic - Azure AI Studio supports AZURE/Cohere
        # If User passes azure/command-r-plus -> we should send it to cohere_chat/command-r-plus
        if model.split("/", 1)[0] == "azure":
            if _is_non_openai_azure_model(model):
                custom_llm_provider = "openai"
                return model, custom_llm_provider, dynamic_api_key, api_base

        ### Handle cases when custom_llm_provider is set to cohere/command-r-plus but it should use cohere_chat route
        model, custom_llm_provider = handle_cohere_chat_model_custom_llm_provider(
            model, custom_llm_provider
        )

        model, custom_llm_provider = handle_anthropic_text_model_custom_llm_provider(
            model, custom_llm_provider
        )

        if custom_llm_provider and (
            model.split("/")[0] != custom_llm_provider
        ):  # handle scenario where model="azure/*" and custom_llm_provider="azure"
            model = custom_llm_provider + "/" + model

        if api_key and api_key.startswith("os.environ/"):
            dynamic_api_key = get_secret_str(api_key)
        # check if llm provider part of model name

        if (
            model.split("/", 1)[0] in litellm.provider_list
            and model.split("/", 1)[0] not in litellm.model_list_set
            and len(model.split("/"))
            > 1  # handle edge case where user passes in `litellm --model mistral` https://github.com/BerriAI/litellm/issues/1351
        ):
            return _get_openai_compatible_provider_info(
                model=model,
                api_base=api_base,
                api_key=api_key,
                dynamic_api_key=dynamic_api_key,
            )
        elif model.split("/", 1)[0] in litellm.provider_list:
            custom_llm_provider = model.split("/", 1)[0]
            model = model.split("/", 1)[1]
            if api_base is not None and not isinstance(api_base, str):
                raise Exception(
                    "api base needs to be a string. api_base={}".format(api_base)
                )
            if dynamic_api_key is not None and not isinstance(dynamic_api_key, str):
                raise Exception(
                    "dynamic_api_key needs to be a string. dynamic_api_key={}".format(
                        dynamic_api_key
                    )
                )
            return model, custom_llm_provider, dynamic_api_key, api_base
        # check if api base is a known openai compatible endpoint
        if api_base:
            for endpoint in litellm.openai_compatible_endpoints:
                if endpoint in api_base:
                    if endpoint == "api.perplexity.ai":
                        custom_llm_provider = "perplexity"
                        dynamic_api_key = get_secret_str("PERPLEXITYAI_API_KEY")
                    elif endpoint == "api.endpoints.anyscale.com/v1":
                        custom_llm_provider = "anyscale"
                        dynamic_api_key = get_secret_str("ANYSCALE_API_KEY")
                    elif endpoint == "api.deepinfra.com/v1/openai":
                        custom_llm_provider = "deepinfra"
                        dynamic_api_key = get_secret_str("DEEPINFRA_API_KEY")
                    elif endpoint == "api.mistral.ai/v1":
                        custom_llm_provider = "mistral"
                        dynamic_api_key = get_secret_str("MISTRAL_API_KEY")
                    elif endpoint == "api.groq.com/openai/v1":
                        custom_llm_provider = "groq"
                        dynamic_api_key = get_secret_str("GROQ_API_KEY")
                    elif endpoint == "https://integrate.api.nvidia.com/v1":
                        custom_llm_provider = "nvidia_nim"
                        dynamic_api_key = get_secret_str("NVIDIA_NIM_API_KEY")
                    elif endpoint == "https://api.cerebras.ai/v1":
                        custom_llm_provider = "cerebras"
                        dynamic_api_key = get_secret_str("CEREBRAS_API_KEY")
                    elif endpoint == "https://api.sambanova.ai/v1":
                        custom_llm_provider = "sambanova"
                        dynamic_api_key = get_secret_str("SAMBANOVA_API_KEY")
                    elif endpoint == "https://api.ai21.com/studio/v1":
                        custom_llm_provider = "ai21_chat"
                        dynamic_api_key = get_secret_str("AI21_API_KEY")
                    elif endpoint == "https://codestral.mistral.ai/v1":
                        custom_llm_provider = "codestral"
                        dynamic_api_key = get_secret_str("CODESTRAL_API_KEY")
                    elif endpoint == "https://codestral.mistral.ai/v1":
                        custom_llm_provider = "text-completion-codestral"
                        dynamic_api_key = get_secret_str("CODESTRAL_API_KEY")
                    elif endpoint == "app.empower.dev/api/v1":
                        custom_llm_provider = "empower"
                        dynamic_api_key = get_secret_str("EMPOWER_API_KEY")
                    elif endpoint == "api.deepseek.com/v1":
                        custom_llm_provider = "deepseek"
                        dynamic_api_key = get_secret_str("DEEPSEEK_API_KEY")
                    elif endpoint == "https://api.friendli.ai/serverless/v1":
                        custom_llm_provider = "friendliai"
                        dynamic_api_key = get_secret_str(
                            "FRIENDLIAI_API_KEY"
                        ) or get_secret("FRIENDLI_TOKEN")
                    elif endpoint == "api.galadriel.com/v1":
                        custom_llm_provider = "galadriel"
                        dynamic_api_key = get_secret_str("GALADRIEL_API_KEY")
                    elif endpoint == "https://api.llama.com/compat/v1":
                        custom_llm_provider = "meta_llama"
                        dynamic_api_key = api_key or get_secret_str("LLAMA_API_KEY")
                    elif endpoint == "https://api.featherless.ai/v1":
                        custom_llm_provider = "featherless_ai"
                        dynamic_api_key = get_secret_str("FEATHERLESS_AI_API_KEY")
                    elif endpoint == litellm.NscaleConfig.API_BASE_URL:
                        custom_llm_provider = "nscale"
                        dynamic_api_key = litellm.NscaleConfig.get_api_key()

                    if api_base is not None and not isinstance(api_base, str):
                        raise Exception(
                            "api base needs to be a string. api_base={}".format(
                                api_base
                            )
                        )
                    if dynamic_api_key is not None and not isinstance(
                        dynamic_api_key, str
                    ):
                        raise Exception(
                            "dynamic_api_key needs to be a string. dynamic_api_key={}".format(
                                dynamic_api_key
                            )
                        )
                    return model, custom_llm_provider, dynamic_api_key, api_base  # type: ignore

        # check if model in known model provider list  -> for huggingface models, raise exception as they don't have a fixed provider (can be togetherai, anyscale, baseten, runpod, et.)
        ## openai - chatcompletion + text completion
        if (
            model in litellm.open_ai_chat_completion_models
            or "ft:gpt-3.5-turbo" in model
            or "ft:gpt-4" in model  # catches ft:gpt-4-0613, ft:gpt-4o
            or model in litellm.openai_image_generation_models
        ):
            custom_llm_provider = "openai"
        elif model in litellm.open_ai_text_completion_models:
            custom_llm_provider = "text-completion-openai"
        ## anthropic
        elif model in litellm.anthropic_models:
            if litellm.AnthropicTextConfig._is_anthropic_text_model(model):
                custom_llm_provider = "anthropic_text"
            else:
                custom_llm_provider = "anthropic"
        ## cohere
        elif model in litellm.cohere_models or model in litellm.cohere_embedding_models:
            custom_llm_provider = "cohere"
        ## cohere chat models
        elif model in litellm.cohere_chat_models:
            custom_llm_provider = "cohere_chat"
        ## replicate
        elif model in litellm.replicate_models or (
            ":" in model and len(model) > REPLICATE_MODEL_NAME_WITH_ID_LENGTH
        ):
            model_parts = model.split(":")
            if (
                len(model_parts) > 1
                and len(model_parts[1]) == REPLICATE_MODEL_NAME_WITH_ID_LENGTH
            ):  ## checks if model name has a 64 digit code - e.g. "meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3"
                custom_llm_provider = "replicate"
            elif model in litellm.replicate_models:
                custom_llm_provider = "replicate"
        ## openrouter
        elif model in litellm.openrouter_models:
            custom_llm_provider = "openrouter"
        ## maritalk
        elif model in litellm.maritalk_models:
            custom_llm_provider = "maritalk"
        ## vertex - text + chat + language (gemini) models
        elif (
            model in litellm.vertex_chat_models
            or model in litellm.vertex_code_chat_models
            or model in litellm.vertex_text_models
            or model in litellm.vertex_code_text_models
            or model in litellm.vertex_language_models
            or model in litellm.vertex_embedding_models
            or model in litellm.vertex_vision_models
            or model in litellm.vertex_ai_image_models
        ):
            custom_llm_provider = "vertex_ai"
        ## ai21
        elif model in litellm.ai21_chat_models or model in litellm.ai21_models:
            custom_llm_provider = "ai21_chat"
            api_base = (
                api_base
                or get_secret("AI21_API_BASE")
                or "https://api.ai21.com/studio/v1"
            )  # type: ignore
            dynamic_api_key = api_key or get_secret("AI21_API_KEY")
        ## aleph_alpha
        elif model in litellm.aleph_alpha_models:
            custom_llm_provider = "aleph_alpha"
        ## baseten
        elif model in litellm.baseten_models:
            custom_llm_provider = "baseten"
        ## nlp_cloud
        elif model in litellm.nlp_cloud_models:
            custom_llm_provider = "nlp_cloud"
        ## petals
        elif model in litellm.petals_models:
            custom_llm_provider = "petals"
        ## bedrock
        elif (
            model in litellm.bedrock_models
            or model in litellm.bedrock_embedding_models
            or model in litellm.bedrock_converse_models
        ):
            custom_llm_provider = "bedrock"
        elif model in litellm.watsonx_models:
            custom_llm_provider = "watsonx"
        # openai embeddings
        elif model in litellm.open_ai_embedding_models:
            custom_llm_provider = "openai"
        elif model in litellm.empower_models:
            custom_llm_provider = "empower"
        elif model == "*":
            custom_llm_provider = "openai"
        if not custom_llm_provider:
            if litellm.suppress_debug_info is False:
                print()  # noqa
                print(  # noqa
                    "\033[1;31mProvider List: https://docs.litellm.ai/docs/providers\033[0m"  # noqa
                )  # noqa
                print()  # noqa
            error_str = f"LLM Provider NOT provided. Pass in the LLM provider you are trying to call. You passed model={model}\n Pass model as E.g. For 'Huggingface' inference endpoints pass in `completion(model='huggingface/starcoder',..)` Learn more: https://docs.litellm.ai/docs/providers"
            # maps to openai.NotFoundError, this is raised when openai does not recognize the llm
            raise litellm.exceptions.BadRequestError(  # type: ignore
                message=error_str,
                model=model,
                response=httpx.Response(
                    status_code=400,
                    content=error_str,
                    request=httpx.Request(method="completion", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
                llm_provider="",
            )
        if api_base is not None and not isinstance(api_base, str):
            raise Exception(
                "api base needs to be a string. api_base={}".format(api_base)
            )
        if dynamic_api_key is not None and not isinstance(dynamic_api_key, str):
            raise Exception(
                "dynamic_api_key needs to be a string. dynamic_api_key={}".format(
                    dynamic_api_key
                )
            )
        return model, custom_llm_provider, dynamic_api_key, api_base
    except Exception as e:
        if isinstance(e, litellm.exceptions.BadRequestError):
            raise e
        else:
            error_str = (
                f"GetLLMProvider Exception - {str(e)}\n\noriginal model: {model}"
            )
            raise litellm.exceptions.BadRequestError(  # type: ignore
                message=f"GetLLMProvider Exception - {str(e)}\n\noriginal model: {model}",
                model=model,
                response=httpx.Response(
                    status_code=400,
                    content=error_str,
                    request=httpx.Request(method="completion", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
                llm_provider="",
            )


def _get_openai_compatible_provider_info(  # noqa: PLR0915
    model: str,
    api_base: Optional[str],
    api_key: Optional[str],
    dynamic_api_key: Optional[str],
) -> Tuple[str, str, Optional[str], Optional[str]]:
    """
    Returns:
        Tuple[str, str, Optional[str], Optional[str]]:
            model: str
            custom_llm_provider: str
            dynamic_api_key: Optional[str]
            api_base: Optional[str]
    """

    custom_llm_provider = model.split("/", 1)[0]
    model = model.split("/", 1)[1]

    if custom_llm_provider == "perplexity":
        # perplexity is openai compatible, we just need to set this to custom_openai and have the api_base be https://api.perplexity.ai
        (
            api_base,
            dynamic_api_key,
        ) = litellm.PerplexityChatConfig()._get_openai_compatible_provider_info(
            api_base, api_key
        )
    elif custom_llm_provider == "aiohttp_openai":
        return model, "aiohttp_openai", api_key, api_base
    elif custom_llm_provider == "anyscale":
        # anyscale is openai compatible, we just need to set this to custom_openai and have the api_base be https://api.endpoints.anyscale.com/v1
        api_base = api_base or get_secret_str("ANYSCALE_API_BASE") or "https://api.endpoints.anyscale.com/v1"  # type: ignore
        dynamic_api_key = api_key or get_secret_str("ANYSCALE_API_KEY")
    elif custom_llm_provider == "deepinfra":
        (
            api_base,
            dynamic_api_key,
        ) = litellm.DeepInfraConfig()._get_openai_compatible_provider_info(
            api_base, api_key
        )
    elif custom_llm_provider == "empower":
        api_base = (
            api_base
            or get_secret("EMPOWER_API_BASE")
            or "https://app.empower.dev/api/v1"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("EMPOWER_API_KEY")
    elif custom_llm_provider == "groq":
        (
            api_base,
            dynamic_api_key,
        ) = litellm.GroqChatConfig()._get_openai_compatible_provider_info(
            api_base, api_key
        )
    elif custom_llm_provider == "nvidia_nim":
        # nvidia_nim is openai compatible, we just need to set this to custom_openai and have the api_base be https://api.endpoints.anyscale.com/v1
        api_base = (
            api_base
            or get_secret("NVIDIA_NIM_API_BASE")
            or "https://integrate.api.nvidia.com/v1"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("NVIDIA_NIM_API_KEY")
    elif custom_llm_provider == "cerebras":
        api_base = (
            api_base or get_secret("CEREBRAS_API_BASE") or "https://api.cerebras.ai/v1"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("CEREBRAS_API_KEY")
    elif custom_llm_provider == "sambanova":
        api_base = (
            api_base
            or get_secret("SAMBANOVA_API_BASE")
            or "https://api.sambanova.ai/v1"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("SAMBANOVA_API_KEY")
    elif custom_llm_provider == "meta_llama":
        api_base = (
            api_base
            or get_secret("LLAMA_API_BASE")
            or "https://api.llama.com/compat/v1"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("LLAMA_API_KEY")
    elif custom_llm_provider == "nebius":
        api_base = (
            api_base
            or get_secret("NEBIUS_API_BASE")
            or "https://api.studio.nebius.ai/v1"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("NEBIUS_API_KEY")
    elif (custom_llm_provider == "ai21_chat") or (
        custom_llm_provider == "ai21" and model in litellm.ai21_chat_models
    ):
        api_base = (
            api_base or get_secret("AI21_API_BASE") or "https://api.ai21.com/studio/v1"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("AI21_API_KEY")
        custom_llm_provider = "ai21_chat"
    elif custom_llm_provider == "volcengine":
        # volcengine is openai compatible, we just need to set this to custom_openai and have the api_base be https://api.endpoints.anyscale.com/v1
        api_base = (
            api_base
            or get_secret("VOLCENGINE_API_BASE")
            or "https://ark.cn-beijing.volces.com/api/v3"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("VOLCENGINE_API_KEY")
    elif custom_llm_provider == "codestral":
        # codestral is openai compatible, we just need to set this to custom_openai and have the api_base be https://codestral.mistral.ai/v1
        api_base = (
            api_base
            or get_secret("CODESTRAL_API_BASE")
            or "https://codestral.mistral.ai/v1"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("CODESTRAL_API_KEY")
    elif custom_llm_provider == "hosted_vllm":
        # vllm is openai compatible, we just need to set this to custom_openai
        (
            api_base,
            dynamic_api_key,
        ) = litellm.HostedVLLMChatConfig()._get_openai_compatible_provider_info(
            api_base, api_key
        )
    elif custom_llm_provider == "llamafile":
        # llamafile is OpenAI compatible.
        (
            api_base,
            dynamic_api_key,
        ) = litellm.LlamafileChatConfig()._get_openai_compatible_provider_info(
            api_base, api_key
        )
    elif custom_llm_provider == "datarobot":
        # DataRobot is OpenAI compatible.
        (
            api_base,
            dynamic_api_key
        ) = litellm.DataRobotConfig()._get_openai_compatible_provider_info(
            api_base, api_key
        )
    elif custom_llm_provider == "lm_studio":
        # lm_studio is openai compatible, we just need to set this to custom_openai
        (
            api_base,
            dynamic_api_key,
        ) = litellm.LMStudioChatConfig()._get_openai_compatible_provider_info(
            api_base, api_key
        )
    elif custom_llm_provider == "deepseek":
        # deepseek is openai compatible, we just need to set this to custom_openai and have the api_base be https://api.deepseek.com/v1
        api_base = (
            api_base
            or get_secret("DEEPSEEK_API_BASE")
            or "https://api.deepseek.com/beta"
        )  # type: ignore

        dynamic_api_key = api_key or get_secret_str("DEEPSEEK_API_KEY")
    elif custom_llm_provider == "fireworks_ai":
        # fireworks is openai compatible, we just need to set this to custom_openai and have the api_base be https://api.fireworks.ai/inference/v1
        (
            api_base,
            dynamic_api_key,
        ) = litellm.FireworksAIConfig()._get_openai_compatible_provider_info(
            api_base=api_base, api_key=api_key
        )
    elif custom_llm_provider == "azure_ai":
        (
            api_base,
            dynamic_api_key,
            custom_llm_provider,
        ) = litellm.AzureAIStudioConfig()._get_openai_compatible_provider_info(
            model, api_base, api_key, custom_llm_provider
        )
    elif custom_llm_provider == "github":
        api_base = (
            api_base
            or get_secret_str("GITHUB_API_BASE")
            or "https://models.inference.ai.azure.com"  # This is github's default base url
        )
        dynamic_api_key = api_key or get_secret_str("GITHUB_API_KEY")
    elif custom_llm_provider == "litellm_proxy":
        (
            api_base,
            dynamic_api_key,
        ) = litellm.LiteLLMProxyChatConfig()._get_openai_compatible_provider_info(
            api_base=api_base, api_key=api_key
        )

    elif custom_llm_provider == "mistral":
        (
            api_base,
            dynamic_api_key,
        ) = litellm.MistralConfig()._get_openai_compatible_provider_info(
            api_base, api_key
        )
    elif custom_llm_provider == "jina_ai":
        (
            custom_llm_provider,
            api_base,
            dynamic_api_key,
        ) = litellm.JinaAIEmbeddingConfig()._get_openai_compatible_provider_info(
            api_base, api_key
        )
    elif custom_llm_provider == "xai":
        (
            api_base,
            dynamic_api_key,
        ) = litellm.XAIChatConfig()._get_openai_compatible_provider_info(
            api_base, api_key
        )
    elif custom_llm_provider == "together_ai":
        api_base = (
            api_base
            or get_secret_str("TOGETHER_AI_API_BASE")
            or "https://api.together.xyz/v1"
        )  # type: ignore
        dynamic_api_key = api_key or (
            get_secret_str("TOGETHER_API_KEY")
            or get_secret_str("TOGETHER_AI_API_KEY")
            or get_secret_str("TOGETHERAI_API_KEY")
            or get_secret_str("TOGETHER_AI_TOKEN")
        )
    elif custom_llm_provider == "friendliai":
        api_base = (
            api_base
            or get_secret("FRIENDLI_API_BASE")
            or "https://api.friendli.ai/serverless/v1"
        )  # type: ignore
        dynamic_api_key = (
            api_key
            or get_secret_str("FRIENDLIAI_API_KEY")
            or get_secret_str("FRIENDLI_TOKEN")
        )
    elif custom_llm_provider == "galadriel":
        api_base = (
            api_base
            or get_secret("GALADRIEL_API_BASE")
            or "https://api.galadriel.com/v1"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("GALADRIEL_API_KEY")
    elif custom_llm_provider == "novita":
        api_base = (
            api_base
            or get_secret("NOVITA_API_BASE")
            or "https://api.novita.ai/v3/openai"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("NOVITA_API_KEY")
    elif custom_llm_provider == "snowflake":
        api_base = (
            api_base
            or get_secret_str("SNOWFLAKE_API_BASE")
            or f"https://{get_secret('SNOWFLAKE_ACCOUNT_ID')}.snowflakecomputing.com/api/v2/cortex/inference:complete"
        )  # type: ignore
        dynamic_api_key = api_key or get_secret_str("SNOWFLAKE_JWT")
    elif custom_llm_provider == "featherless_ai":
        (
            api_base,
            dynamic_api_key,
        ) = litellm.FeatherlessAIConfig()._get_openai_compatible_provider_info(
            api_base, api_key
        )
    elif custom_llm_provider == "nscale":
        (
            api_base,
            dynamic_api_key,
        ) = litellm.NscaleConfig()._get_openai_compatible_provider_info(
            api_base=api_base, api_key=api_key
        )

    if api_base is not None and not isinstance(api_base, str):
        raise Exception("api base needs to be a string. api_base={}".format(api_base))
    if dynamic_api_key is not None and not isinstance(dynamic_api_key, str):
        raise Exception(
            "dynamic_api_key needs to be a string. dynamic_api_key={}".format(
                dynamic_api_key
            )
        )
    if dynamic_api_key is None and api_key is not None:
        dynamic_api_key = api_key
    return model, custom_llm_provider, dynamic_api_key, api_base