
# === NexusCore/myenv\Lib\site-packages\pip\_internal\self_outdated_check.py ===
import datetime
import functools
import hashlib
import json
import logging
import optparse
import os.path
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from pip._vendor.packaging.version import Version
from pip._vendor.packaging.version import parse as parse_version
from pip._vendor.rich.console import Group
from pip._vendor.rich.markup import escape
from pip._vendor.rich.text import Text

from pip._internal.index.collector import LinkCollector
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import get_default_environment
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.network.session import PipSession
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.entrypoints import (
    get_best_invocation_for_this_pip,
    get_best_invocation_for_this_python,
)
from pip._internal.utils.filesystem import adjacent_tmp_file, check_path_owner, replace
from pip._internal.utils.misc import (
    ExternallyManagedEnvironment,
    check_externally_managed,
    ensure_dir,
)

_WEEK = datetime.timedelta(days=7)

logger = logging.getLogger(__name__)


def _get_statefile_name(key: str) -> str:
    key_bytes = key.encode()
    name = hashlib.sha224(key_bytes).hexdigest()
    return name


def _convert_date(isodate: str) -> datetime.datetime:
    """Convert an ISO format string to a date.

    Handles the format 2020-01-22T14:24:01Z (trailing Z)
    which is not supported by older versions of fromisoformat.
    """
    return datetime.datetime.fromisoformat(isodate.replace("Z", "+00:00"))


class SelfCheckState:
    def __init__(self, cache_dir: str) -> None:
        self._state: Dict[str, Any] = {}
        self._statefile_path = None

        # Try to load the existing state
        if cache_dir:
            self._statefile_path = os.path.join(
                cache_dir, "selfcheck", _get_statefile_name(self.key)
            )
            try:
                with open(self._statefile_path, encoding="utf-8") as statefile:
                    self._state = json.load(statefile)
            except (OSError, ValueError, KeyError):
                # Explicitly suppressing exceptions, since we don't want to
                # error out if the cache file is invalid.
                pass

    @property
    def key(self) -> str:
        return sys.prefix

    def get(self, current_time: datetime.datetime) -> Optional[str]:
        """Check if we have a not-outdated version loaded already."""
        if not self._state:
            return None

        if "last_check" not in self._state:
            return None

        if "pypi_version" not in self._state:
            return None

        # Determine if we need to refresh the state
        last_check = _convert_date(self._state["last_check"])
        time_since_last_check = current_time - last_check
        if time_since_last_check > _WEEK:
            return None

        return self._state["pypi_version"]

    def set(self, pypi_version: str, current_time: datetime.datetime) -> None:
        # If we do not have a path to cache in, don't bother saving.
        if not self._statefile_path:
            return

        # Check to make sure that we own the directory
        if not check_path_owner(os.path.dirname(self._statefile_path)):
            return

        # Now that we've ensured the directory is owned by this user, we'll go
        # ahead and make sure that all our directories are created.
        ensure_dir(os.path.dirname(self._statefile_path))

        state = {
            # Include the key so it's easy to tell which pip wrote the
            # file.
            "key": self.key,
            "last_check": current_time.isoformat(),
            "pypi_version": pypi_version,
        }

        text = json.dumps(state, sort_keys=True, separators=(",", ":"))

        with adjacent_tmp_file(self._statefile_path) as f:
            f.write(text.encode())

        try:
            # Since we have a prefix-specific state file, we can just
            # overwrite whatever is there, no need to check.
            replace(f.name, self._statefile_path)
        except OSError:
            # Best effort.
            pass


@dataclass
class UpgradePrompt:
    old: str
    new: str

    def __rich__(self) -> Group:
        if WINDOWS:
            pip_cmd = f"{get_best_invocation_for_this_python()} -m pip"
        else:
            pip_cmd = get_best_invocation_for_this_pip()

        notice = "[bold][[reset][blue]notice[reset][bold]][reset]"
        return Group(
            Text(),
            Text.from_markup(
                f"{notice} A new release of pip is available: "
                f"[red]{self.old}[reset] -> [green]{self.new}[reset]"
            ),
            Text.from_markup(
                f"{notice} To update, run: "
                f"[green]{escape(pip_cmd)} install --upgrade pip"
            ),
        )


def was_installed_by_pip(pkg: str) -> bool:
    """Checks whether pkg was installed by pip

    This is used not to display the upgrade message when pip is in fact
    installed by system package manager, such as dnf on Fedora.
    """
    dist = get_default_environment().get_distribution(pkg)
    return dist is not None and "pip" == dist.installer


def _get_current_remote_pip_version(
    session: PipSession, options: optparse.Values
) -> Optional[str]:
    # Lets use PackageFinder to see what the latest pip version is
    link_collector = LinkCollector.create(
        session,
        options=options,
        suppress_no_index=True,
    )

    # Pass allow_yanked=False so we don't suggest upgrading to a
    # yanked version.
    selection_prefs = SelectionPreferences(
        allow_yanked=False,
        allow_all_prereleases=False,  # Explicitly set to False
    )

    finder = PackageFinder.create(
        link_collector=link_collector,
        selection_prefs=selection_prefs,
    )
    best_candidate = finder.find_best_candidate("pip").best_candidate
    if best_candidate is None:
        return None

    return str(best_candidate.version)


def _self_version_check_logic(
    *,
    state: SelfCheckState,
    current_time: datetime.datetime,
    local_version: Version,
    get_remote_version: Callable[[], Optional[str]],
) -> Optional[UpgradePrompt]:
    remote_version_str = state.get(current_time)
    if remote_version_str is None:
        remote_version_str = get_remote_version()
        if remote_version_str is None:
            logger.debug("No remote pip version found")
            return None
        state.set(remote_version_str, current_time)

    remote_version = parse_version(remote_version_str)
    logger.debug("Remote version of pip: %s", remote_version)
    logger.debug("Local version of pip:  %s", local_version)

    pip_installed_by_pip = was_installed_by_pip("pip")
    logger.debug("Was pip installed by pip? %s", pip_installed_by_pip)
    if not pip_installed_by_pip:
        return None  # Only suggest upgrade if pip is installed by pip.

    local_version_is_older = (
        local_version < remote_version
        and local_version.base_version != remote_version.base_version
    )
    if local_version_is_older:
        return UpgradePrompt(old=str(local_version), new=remote_version_str)

    return None


def pip_self_version_check(session: PipSession, options: optparse.Values) -> None:
    """Check for an update for pip.

    Limit the frequency of checks to once per week. State is stored either in
    the active virtualenv or in the user's USER_CACHE_DIR keyed off the prefix
    of the pip script path.
    """
    installed_dist = get_default_environment().get_distribution("pip")
    if not installed_dist:
        return
    try:
        check_externally_managed()
    except ExternallyManagedEnvironment:
        return

    upgrade_prompt = _self_version_check_logic(
        state=SelfCheckState(cache_dir=options.cache_dir),
        current_time=datetime.datetime.now(datetime.timezone.utc),
        local_version=installed_dist.version,
        get_remote_version=functools.partial(
            _get_current_remote_pip_version, session, options
        ),
    )
    if upgrade_prompt is not None:
        logger.warning("%s", upgrade_prompt, extra={"rich": True})

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_referrers.py ===
import sys
from _pydevd_bundle import pydevd_xml
from os.path import basename
from _pydev_bundle import pydev_log
from urllib.parse import unquote_plus
from _pydevd_bundle.pydevd_constants import IS_PY311_OR_GREATER


# ===================================================================================================
# print_var_node
# ===================================================================================================
def print_var_node(xml_node, stream):
    name = xml_node.getAttribute("name")
    value = xml_node.getAttribute("value")
    val_type = xml_node.getAttribute("type")

    found_as = xml_node.getAttribute("found_as")
    stream.write("Name: ")
    stream.write(unquote_plus(name))
    stream.write(", Value: ")
    stream.write(unquote_plus(value))
    stream.write(", Type: ")
    stream.write(unquote_plus(val_type))
    if found_as:
        stream.write(", Found as: %s" % (unquote_plus(found_as),))
    stream.write("\n")


# ===================================================================================================
# print_referrers
# ===================================================================================================
def print_referrers(obj, stream=None):
    if stream is None:
        stream = sys.stdout
    result = get_referrer_info(obj)
    from xml.dom.minidom import parseString

    dom = parseString(result)

    xml = dom.getElementsByTagName("xml")[0]
    for node in xml.childNodes:
        if node.nodeType == node.TEXT_NODE:
            continue

        if node.localName == "for":
            stream.write("Searching references for: ")
            for child in node.childNodes:
                if child.nodeType == node.TEXT_NODE:
                    continue
                print_var_node(child, stream)

        elif node.localName == "var":
            stream.write("Referrer found: ")
            print_var_node(node, stream)

        else:
            sys.stderr.write("Unhandled node: %s\n" % (node,))

    return result


# ===================================================================================================
# get_referrer_info
# ===================================================================================================
def get_referrer_info(searched_obj):
    DEBUG = 0
    if DEBUG:
        sys.stderr.write("Getting referrers info.\n")
    try:
        try:
            if searched_obj is None:
                ret = ["<xml>\n"]

                ret.append("<for>\n")
                ret.append(
                    pydevd_xml.var_to_xml(
                        searched_obj, "Skipping getting referrers for None", additional_in_xml=' id="%s"' % (id(searched_obj),)
                    )
                )
                ret.append("</for>\n")
                ret.append("</xml>")
                ret = "".join(ret)
                return ret

            obj_id = id(searched_obj)

            try:
                if DEBUG:
                    sys.stderr.write("Getting referrers...\n")
                import gc

                referrers = gc.get_referrers(searched_obj)
            except:
                pydev_log.exception()
                ret = ["<xml>\n"]

                ret.append("<for>\n")
                ret.append(
                    pydevd_xml.var_to_xml(
                        searched_obj, "Exception raised while trying to get_referrers.", additional_in_xml=' id="%s"' % (id(searched_obj),)
                    )
                )
                ret.append("</for>\n")
                ret.append("</xml>")
                ret = "".join(ret)
                return ret

            if DEBUG:
                sys.stderr.write("Found %s referrers.\n" % (len(referrers),))

            curr_frame = sys._getframe()
            frame_type = type(curr_frame)

            # Ignore this frame and any caller frame of this frame

            ignore_frames = {}  # Should be a set, but it's not available on all python versions.
            while curr_frame is not None:
                if basename(curr_frame.f_code.co_filename).startswith("pydev"):
                    ignore_frames[curr_frame] = 1
                curr_frame = curr_frame.f_back

            ret = ["<xml>\n"]

            ret.append("<for>\n")
            if DEBUG:
                sys.stderr.write('Searching Referrers of obj with id="%s"\n' % (obj_id,))

            ret.append(pydevd_xml.var_to_xml(searched_obj, 'Referrers of obj with id="%s"' % (obj_id,)))
            ret.append("</for>\n")

            curr_frame = sys._getframe()
            all_objects = None

            for r in referrers:
                try:
                    if r in ignore_frames:
                        continue  # Skip the references we may add ourselves
                except:
                    pass  # Ok: unhashable type checked...

                if r is referrers:
                    continue

                if r is curr_frame.f_locals:
                    continue

                r_type = type(r)
                r_id = str(id(r))

                representation = str(r_type)

                found_as = ""
                if r_type == frame_type:
                    if DEBUG:
                        sys.stderr.write("Found frame referrer: %r\n" % (r,))
                    for key, val in r.f_locals.items():
                        if val is searched_obj:
                            found_as = key
                            break

                elif r_type == dict:
                    if DEBUG:
                        sys.stderr.write("Found dict referrer: %r\n" % (r,))

                    # Try to check if it's a value in the dict (and under which key it was found)
                    for key, val in r.items():
                        if val is searched_obj:
                            found_as = key
                            if DEBUG:
                                sys.stderr.write("    Found as %r in dict\n" % (found_as,))
                            break

                    # Ok, there's one annoying thing: many times we find it in a dict from an instance,
                    # but with this we don't directly have the class, only the dict, so, to workaround that
                    # we iterate over all reachable objects ad check if one of those has the given dict.
                    if all_objects is None:
                        all_objects = gc.get_objects()

                    for x in all_objects:
                        try:
                            if getattr(x, "__dict__", None) is r:
                                r = x
                                r_type = type(x)
                                r_id = str(id(r))
                                representation = str(r_type)
                                break
                        except:
                            pass  # Just ignore any error here (i.e.: ReferenceError, etc.)

                elif r_type in (tuple, list):
                    if DEBUG:
                        sys.stderr.write("Found tuple referrer: %r\n" % (r,))

                    for i, x in enumerate(r):
                        if x is searched_obj:
                            found_as = "%s[%s]" % (r_type.__name__, i)
                            if DEBUG:
                                sys.stderr.write("    Found as %s in tuple: \n" % (found_as,))
                            break

                elif IS_PY311_OR_GREATER:
                    # Up to Python 3.10, gc.get_referrers for an instance actually returned the
                    # object.__dict__, but on Python 3.11 it returns the actual object, so,
                    # handling is a bit easier (we don't need the workaround from the dict
                    # case to find the actual instance, we just need to find the attribute name).
                    if DEBUG:
                        sys.stderr.write("Found dict referrer: %r\n" % (r,))

                    dct = getattr(r, "__dict__", None)
                    if dct:
                        # Try to check if it's a value in the dict (and under which key it was found)
                        for key, val in dct.items():
                            if val is searched_obj:
                                found_as = key
                                if DEBUG:
                                    sys.stderr.write("    Found as %r in object instance\n" % (found_as,))
                                break

                if found_as:
                    if not isinstance(found_as, str):
                        found_as = str(found_as)
                    found_as = ' found_as="%s"' % (pydevd_xml.make_valid_xml_value(found_as),)

                ret.append(pydevd_xml.var_to_xml(r, representation, additional_in_xml=' id="%s"%s' % (r_id, found_as)))
        finally:
            if DEBUG:
                sys.stderr.write("Done searching for references.\n")

            # If we have any exceptions, don't keep dangling references from this frame to any of our objects.
            all_objects = None
            referrers = None
            searched_obj = None
            r = None
            x = None
            key = None
            val = None
            curr_frame = None
            ignore_frames = None
    except:
        pydev_log.exception()
        ret = ["<xml>\n"]

        ret.append("<for>\n")
        ret.append(pydevd_xml.var_to_xml(searched_obj, "Error getting referrers for:", additional_in_xml=' id="%s"' % (id(searched_obj),)))
        ret.append("</for>\n")
        ret.append("</xml>")
        ret = "".join(ret)
        return ret

    ret.append("</xml>")
    ret = "".join(ret)
    return ret

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\types\safety.py ===
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
    package="google.ai.generativelanguage.v1beta3",
    manifest={
        "HarmCategory",
        "ContentFilter",
        "SafetyFeedback",
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
            Content that is rude, disrepspectful, or
            profane.
        HARM_CATEGORY_VIOLENCE (3):
            Describes scenarios depictng violence against
            an individual or group, or general descriptions
            of gore.
        HARM_CATEGORY_SEXUAL (4):
            Contains references to sexual acts or other
            lewd content.
        HARM_CATEGORY_MEDICAL (5):
            Promotes unchecked medical advice.
        HARM_CATEGORY_DANGEROUS (6):
            Dangerous content that promotes, facilitates,
            or encourages harmful acts.
    """
    HARM_CATEGORY_UNSPECIFIED = 0
    HARM_CATEGORY_DEROGATORY = 1
    HARM_CATEGORY_TOXICITY = 2
    HARM_CATEGORY_VIOLENCE = 3
    HARM_CATEGORY_SEXUAL = 4
    HARM_CATEGORY_MEDICAL = 5
    HARM_CATEGORY_DANGEROUS = 6


class ContentFilter(proto.Message):
    r"""Content filtering metadata associated with processing a
    single request.
    ContentFilter contains a reason and an optional supporting
    string. The reason may be unspecified.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        reason (google.ai.generativelanguage_v1beta3.types.ContentFilter.BlockedReason):
            The reason content was blocked during request
            processing.
        message (str):
            A string that describes the filtering
            behavior in more detail.

            This field is a member of `oneof`_ ``_message``.
    """

    class BlockedReason(proto.Enum):
        r"""A list of reasons why content may have been blocked.

        Values:
            BLOCKED_REASON_UNSPECIFIED (0):
                A blocked reason was not specified.
            SAFETY (1):
                Content was blocked by safety settings.
            OTHER (2):
                Content was blocked, but the reason is
                uncategorized.
        """
        BLOCKED_REASON_UNSPECIFIED = 0
        SAFETY = 1
        OTHER = 2

    reason: BlockedReason = proto.Field(
        proto.ENUM,
        number=1,
        enum=BlockedReason,
    )
    message: str = proto.Field(
        proto.STRING,
        number=2,
        optional=True,
    )


class SafetyFeedback(proto.Message):
    r"""Safety feedback for an entire request.

    This field is populated if content in the input and/or response
    is blocked due to safety settings. SafetyFeedback may not exist
    for every HarmCategory. Each SafetyFeedback will return the
    safety settings used by the request as well as the lowest
    HarmProbability that should be allowed in order to return a
    result.

    Attributes:
        rating (google.ai.generativelanguage_v1beta3.types.SafetyRating):
            Safety rating evaluated from content.
        setting (google.ai.generativelanguage_v1beta3.types.SafetySetting):
            Safety settings applied to the request.
    """

    rating: "SafetyRating" = proto.Field(
        proto.MESSAGE,
        number=1,
        message="SafetyRating",
    )
    setting: "SafetySetting" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="SafetySetting",
    )


class SafetyRating(proto.Message):
    r"""Safety rating for a piece of content.

    The safety rating contains the category of harm and the harm
    probability level in that category for a piece of content.
    Content is classified for safety across a number of harm
    categories and the probability of the harm classification is
    included here.

    Attributes:
        category (google.ai.generativelanguage_v1beta3.types.HarmCategory):
            Required. The category for this rating.
        probability (google.ai.generativelanguage_v1beta3.types.SafetyRating.HarmProbability):
            Required. The probability of harm for this
            content.
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


class SafetySetting(proto.Message):
    r"""Safety setting, affecting the safety-blocking behavior.

    Passing a safety setting for a category changes the allowed
    proability that content is blocked.

    Attributes:
        category (google.ai.generativelanguage_v1beta3.types.HarmCategory):
            Required. The category for this setting.
        threshold (google.ai.generativelanguage_v1beta3.types.SafetySetting.HarmBlockThreshold):
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

# === NexusCore/openenv\Lib\site-packages\litellm\router_strategy\least_busy.py ===
#### What this does ####
#   identifies least busy deployment
#   How is this achieved?
#   - Before each call, have the router print the state of requests {"deployment": "requests_in_flight"}
#   - use litellm.input_callbacks to log when a request is just about to be made to a model - {"deployment-id": traffic}
#   - use litellm.success + failure callbacks to log when a request completed
#   - in get_available_deployment, for a given model group name -> pick based on traffic

import random
from typing import Optional

from litellm.caching.caching import DualCache
from litellm.integrations.custom_logger import CustomLogger


class LeastBusyLoggingHandler(CustomLogger):
    test_flag: bool = False
    logged_success: int = 0
    logged_failure: int = 0

    def __init__(self, router_cache: DualCache, model_list: list):
        self.router_cache = router_cache
        self.mapping_deployment_to_id: dict = {}
        self.model_list = model_list

    def log_pre_api_call(self, model, messages, kwargs):
        """
        Log when a model is being used.

        Caching based on model group.
        """
        try:
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                model_group = kwargs["litellm_params"]["metadata"].get(
                    "model_group", None
                )
                id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                request_count_api_key = f"{model_group}_request_count"
                # update cache
                request_count_dict = (
                    self.router_cache.get_cache(key=request_count_api_key) or {}
                )
                request_count_dict[id] = request_count_dict.get(id, 0) + 1

                self.router_cache.set_cache(
                    key=request_count_api_key, value=request_count_dict
                )
        except Exception:
            pass

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                model_group = kwargs["litellm_params"]["metadata"].get(
                    "model_group", None
                )

                id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                request_count_api_key = f"{model_group}_request_count"
                # decrement count in cache
                request_count_dict = (
                    self.router_cache.get_cache(key=request_count_api_key) or {}
                )
                request_count_value: Optional[int] = request_count_dict.get(id, 0)
                if request_count_value is None:
                    return
                request_count_dict[id] = request_count_value - 1
                self.router_cache.set_cache(
                    key=request_count_api_key, value=request_count_dict
                )

                ### TESTING ###
                if self.test_flag:
                    self.logged_success += 1
        except Exception:
            pass

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        try:
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                model_group = kwargs["litellm_params"]["metadata"].get(
                    "model_group", None
                )
                id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                request_count_api_key = f"{model_group}_request_count"
                # decrement count in cache
                request_count_dict = (
                    self.router_cache.get_cache(key=request_count_api_key) or {}
                )
                request_count_value: Optional[int] = request_count_dict.get(id, 0)
                if request_count_value is None:
                    return
                request_count_dict[id] = request_count_value - 1
                self.router_cache.set_cache(
                    key=request_count_api_key, value=request_count_dict
                )

                ### TESTING ###
                if self.test_flag:
                    self.logged_failure += 1
        except Exception:
            pass

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                model_group = kwargs["litellm_params"]["metadata"].get(
                    "model_group", None
                )

                id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                request_count_api_key = f"{model_group}_request_count"
                # decrement count in cache
                request_count_dict = (
                    await self.router_cache.async_get_cache(key=request_count_api_key)
                    or {}
                )
                request_count_value: Optional[int] = request_count_dict.get(id, 0)
                if request_count_value is None:
                    return
                request_count_dict[id] = request_count_value - 1
                await self.router_cache.async_set_cache(
                    key=request_count_api_key, value=request_count_dict
                )

                ### TESTING ###
                if self.test_flag:
                    self.logged_success += 1
        except Exception:
            pass

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        try:
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                model_group = kwargs["litellm_params"]["metadata"].get(
                    "model_group", None
                )
                id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                request_count_api_key = f"{model_group}_request_count"
                # decrement count in cache
                request_count_dict = (
                    await self.router_cache.async_get_cache(key=request_count_api_key)
                    or {}
                )
                request_count_value: Optional[int] = request_count_dict.get(id, 0)
                if request_count_value is None:
                    return
                request_count_dict[id] = request_count_value - 1
                await self.router_cache.async_set_cache(
                    key=request_count_api_key, value=request_count_dict
                )

                ### TESTING ###
                if self.test_flag:
                    self.logged_failure += 1
        except Exception:
            pass

    def _get_available_deployments(
        self,
        healthy_deployments: list,
        all_deployments: dict,
    ):
        """
        Helper to get deployments using least busy strategy
        """
        for d in healthy_deployments:
            ## if healthy deployment not yet used
            if d["model_info"]["id"] not in all_deployments:
                all_deployments[d["model_info"]["id"]] = 0
        # map deployment to id
        # pick least busy deployment
        min_traffic = float("inf")
        min_deployment = None
        for k, v in all_deployments.items():
            if v < min_traffic:
                min_traffic = v
                min_deployment = k
        if min_deployment is not None:
            ## check if min deployment is a string, if so, cast it to int
            for m in healthy_deployments:
                if m["model_info"]["id"] == min_deployment:
                    return m
            min_deployment = random.choice(healthy_deployments)
        else:
            min_deployment = random.choice(healthy_deployments)
        return min_deployment

    def get_available_deployments(
        self,
        model_group: str,
        healthy_deployments: list,
    ):
        """
        Sync helper to get deployments using least busy strategy
        """
        request_count_api_key = f"{model_group}_request_count"
        all_deployments = self.router_cache.get_cache(key=request_count_api_key) or {}
        return self._get_available_deployments(
            healthy_deployments=healthy_deployments,
            all_deployments=all_deployments,
        )

    async def async_get_available_deployments(
        self, model_group: str, healthy_deployments: list
    ):
        """
        Async helper to get deployments using least busy strategy
        """
        request_count_api_key = f"{model_group}_request_count"
        all_deployments = (
            await self.router_cache.async_get_cache(key=request_count_api_key) or {}
        )
        return self._get_available_deployments(
            healthy_deployments=healthy_deployments,
            all_deployments=all_deployments,
        )

# === NexusCore/openenv\Lib\site-packages\pip\_internal\self_outdated_check.py ===
import datetime
import functools
import hashlib
import json
import logging
import optparse
import os.path
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from pip._vendor.packaging.version import Version
from pip._vendor.packaging.version import parse as parse_version
from pip._vendor.rich.console import Group
from pip._vendor.rich.markup import escape
from pip._vendor.rich.text import Text

from pip._internal.index.collector import LinkCollector
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import get_default_environment
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.network.session import PipSession
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.entrypoints import (
    get_best_invocation_for_this_pip,
    get_best_invocation_for_this_python,
)
from pip._internal.utils.filesystem import adjacent_tmp_file, check_path_owner, replace
from pip._internal.utils.misc import (
    ExternallyManagedEnvironment,
    check_externally_managed,
    ensure_dir,
)

_WEEK = datetime.timedelta(days=7)

logger = logging.getLogger(__name__)


def _get_statefile_name(key: str) -> str:
    key_bytes = key.encode()
    name = hashlib.sha224(key_bytes).hexdigest()
    return name


def _convert_date(isodate: str) -> datetime.datetime:
    """Convert an ISO format string to a date.

    Handles the format 2020-01-22T14:24:01Z (trailing Z)
    which is not supported by older versions of fromisoformat.
    """
    return datetime.datetime.fromisoformat(isodate.replace("Z", "+00:00"))


class SelfCheckState:
    def __init__(self, cache_dir: str) -> None:
        self._state: Dict[str, Any] = {}
        self._statefile_path = None

        # Try to load the existing state
        if cache_dir:
            self._statefile_path = os.path.join(
                cache_dir, "selfcheck", _get_statefile_name(self.key)
            )
            try:
                with open(self._statefile_path, encoding="utf-8") as statefile:
                    self._state = json.load(statefile)
            except (OSError, ValueError, KeyError):
                # Explicitly suppressing exceptions, since we don't want to
                # error out if the cache file is invalid.
                pass

    @property
    def key(self) -> str:
        return sys.prefix

    def get(self, current_time: datetime.datetime) -> Optional[str]:
        """Check if we have a not-outdated version loaded already."""
        if not self._state:
            return None

        if "last_check" not in self._state:
            return None

        if "pypi_version" not in self._state:
            return None

        # Determine if we need to refresh the state
        last_check = _convert_date(self._state["last_check"])
        time_since_last_check = current_time - last_check
        if time_since_last_check > _WEEK:
            return None

        return self._state["pypi_version"]

    def set(self, pypi_version: str, current_time: datetime.datetime) -> None:
        # If we do not have a path to cache in, don't bother saving.
        if not self._statefile_path:
            return

        # Check to make sure that we own the directory
        if not check_path_owner(os.path.dirname(self._statefile_path)):
            return

        # Now that we've ensured the directory is owned by this user, we'll go
        # ahead and make sure that all our directories are created.
        ensure_dir(os.path.dirname(self._statefile_path))

        state = {
            # Include the key so it's easy to tell which pip wrote the
            # file.
            "key": self.key,
            "last_check": current_time.isoformat(),
            "pypi_version": pypi_version,
        }

        text = json.dumps(state, sort_keys=True, separators=(",", ":"))

        with adjacent_tmp_file(self._statefile_path) as f:
            f.write(text.encode())

        try:
            # Since we have a prefix-specific state file, we can just
            # overwrite whatever is there, no need to check.
            replace(f.name, self._statefile_path)
        except OSError:
            # Best effort.
            pass


@dataclass
class UpgradePrompt:
    old: str
    new: str

    def __rich__(self) -> Group:
        if WINDOWS:
            pip_cmd = f"{get_best_invocation_for_this_python()} -m pip"
        else:
            pip_cmd = get_best_invocation_for_this_pip()

        notice = "[bold][[reset][blue]notice[reset][bold]][reset]"
        return Group(
            Text(),
            Text.from_markup(
                f"{notice} A new release of pip is available: "
                f"[red]{self.old}[reset] -> [green]{self.new}[reset]"
            ),
            Text.from_markup(
                f"{notice} To update, run: "
                f"[green]{escape(pip_cmd)} install --upgrade pip"
            ),
        )


def was_installed_by_pip(pkg: str) -> bool:
    """Checks whether pkg was installed by pip

    This is used not to display the upgrade message when pip is in fact
    installed by system package manager, such as dnf on Fedora.
    """
    dist = get_default_environment().get_distribution(pkg)
    return dist is not None and "pip" == dist.installer


def _get_current_remote_pip_version(
    session: PipSession, options: optparse.Values
) -> Optional[str]:
    # Lets use PackageFinder to see what the latest pip version is
    link_collector = LinkCollector.create(
        session,
        options=options,
        suppress_no_index=True,
    )

    # Pass allow_yanked=False so we don't suggest upgrading to a
    # yanked version.
    selection_prefs = SelectionPreferences(
        allow_yanked=False,
        allow_all_prereleases=False,  # Explicitly set to False
    )

    finder = PackageFinder.create(
        link_collector=link_collector,
        selection_prefs=selection_prefs,
    )
    best_candidate = finder.find_best_candidate("pip").best_candidate
    if best_candidate is None:
        return None

    return str(best_candidate.version)


def _self_version_check_logic(
    *,
    state: SelfCheckState,
    current_time: datetime.datetime,
    local_version: Version,
    get_remote_version: Callable[[], Optional[str]],
) -> Optional[UpgradePrompt]:
    remote_version_str = state.get(current_time)
    if remote_version_str is None:
        remote_version_str = get_remote_version()
        if remote_version_str is None:
            logger.debug("No remote pip version found")
            return None
        state.set(remote_version_str, current_time)

    remote_version = parse_version(remote_version_str)
    logger.debug("Remote version of pip: %s", remote_version)
    logger.debug("Local version of pip:  %s", local_version)

    pip_installed_by_pip = was_installed_by_pip("pip")
    logger.debug("Was pip installed by pip? %s", pip_installed_by_pip)
    if not pip_installed_by_pip:
        return None  # Only suggest upgrade if pip is installed by pip.

    local_version_is_older = (
        local_version < remote_version
        and local_version.base_version != remote_version.base_version
    )
    if local_version_is_older:
        return UpgradePrompt(old=str(local_version), new=remote_version_str)

    return None


def pip_self_version_check(session: PipSession, options: optparse.Values) -> None:
    """Check for an update for pip.

    Limit the frequency of checks to once per week. State is stored either in
    the active virtualenv or in the user's USER_CACHE_DIR keyed off the prefix
    of the pip script path.
    """
    installed_dist = get_default_environment().get_distribution("pip")
    if not installed_dist:
        return
    try:
        check_externally_managed()
    except ExternallyManagedEnvironment:
        return

    upgrade_prompt = _self_version_check_logic(
        state=SelfCheckState(cache_dir=options.cache_dir),
        current_time=datetime.datetime.now(datetime.timezone.utc),
        local_version=installed_dist.version,
        get_remote_version=functools.partial(
            _get_current_remote_pip_version, session, options
        ),
    )
    if upgrade_prompt is not None:
        logger.warning("%s", upgrade_prompt, extra={"rich": True})

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\markup.py ===
import re
from ast import literal_eval
from operator import attrgetter
from typing import Callable, Iterable, List, Match, NamedTuple, Optional, Tuple, Union

from ._emoji_replace import _emoji_replace
from .emoji import EmojiVariant
from .errors import MarkupError
from .style import Style
from .text import Span, Text

RE_TAGS = re.compile(
    r"""((\\*)\[([a-z#/@][^[]*?)])""",
    re.VERBOSE,
)

RE_HANDLER = re.compile(r"^([\w.]*?)(\(.*?\))?$")


class Tag(NamedTuple):
    """A tag in console markup."""

    name: str
    """The tag name. e.g. 'bold'."""
    parameters: Optional[str]
    """Any additional parameters after the name."""

    def __str__(self) -> str:
        return (
            self.name if self.parameters is None else f"{self.name} {self.parameters}"
        )

    @property
    def markup(self) -> str:
        """Get the string representation of this tag."""
        return (
            f"[{self.name}]"
            if self.parameters is None
            else f"[{self.name}={self.parameters}]"
        )


_ReStringMatch = Match[str]  # regex match object
_ReSubCallable = Callable[[_ReStringMatch], str]  # Callable invoked by re.sub
_EscapeSubMethod = Callable[[_ReSubCallable, str], str]  # Sub method of a compiled re


def escape(
    markup: str,
    _escape: _EscapeSubMethod = re.compile(r"(\\*)(\[[a-z#/@][^[]*?])").sub,
) -> str:
    """Escapes text so that it won't be interpreted as markup.

    Args:
        markup (str): Content to be inserted in to markup.

    Returns:
        str: Markup with square brackets escaped.
    """

    def escape_backslashes(match: Match[str]) -> str:
        """Called by re.sub replace matches."""
        backslashes, text = match.groups()
        return f"{backslashes}{backslashes}\\{text}"

    markup = _escape(escape_backslashes, markup)
    if markup.endswith("\\") and not markup.endswith("\\\\"):
        return markup + "\\"

    return markup


def _parse(markup: str) -> Iterable[Tuple[int, Optional[str], Optional[Tag]]]:
    """Parse markup in to an iterable of tuples of (position, text, tag).

    Args:
        markup (str): A string containing console markup

    """
    position = 0
    _divmod = divmod
    _Tag = Tag
    for match in RE_TAGS.finditer(markup):
        full_text, escapes, tag_text = match.groups()
        start, end = match.span()
        if start > position:
            yield start, markup[position:start], None
        if escapes:
            backslashes, escaped = _divmod(len(escapes), 2)
            if backslashes:
                # Literal backslashes
                yield start, "\\" * backslashes, None
                start += backslashes * 2
            if escaped:
                # Escape of tag
                yield start, full_text[len(escapes) :], None
                position = end
                continue
        text, equals, parameters = tag_text.partition("=")
        yield start, None, _Tag(text, parameters if equals else None)
        position = end
    if position < len(markup):
        yield position, markup[position:], None


def render(
    markup: str,
    style: Union[str, Style] = "",
    emoji: bool = True,
    emoji_variant: Optional[EmojiVariant] = None,
) -> Text:
    """Render console markup in to a Text instance.

    Args:
        markup (str): A string containing console markup.
        style: (Union[str, Style]): The style to use.
        emoji (bool, optional): Also render emoji code. Defaults to True.
        emoji_variant (str, optional): Optional emoji variant, either "text" or "emoji". Defaults to None.


    Raises:
        MarkupError: If there is a syntax error in the markup.

    Returns:
        Text: A test instance.
    """
    emoji_replace = _emoji_replace
    if "[" not in markup:
        return Text(
            emoji_replace(markup, default_variant=emoji_variant) if emoji else markup,
            style=style,
        )
    text = Text(style=style)
    append = text.append
    normalize = Style.normalize

    style_stack: List[Tuple[int, Tag]] = []
    pop = style_stack.pop

    spans: List[Span] = []
    append_span = spans.append

    _Span = Span
    _Tag = Tag

    def pop_style(style_name: str) -> Tuple[int, Tag]:
        """Pop tag matching given style name."""
        for index, (_, tag) in enumerate(reversed(style_stack), 1):
            if tag.name == style_name:
                return pop(-index)
        raise KeyError(style_name)

    for position, plain_text, tag in _parse(markup):
        if plain_text is not None:
            # Handle open brace escapes, where the brace is not part of a tag.
            plain_text = plain_text.replace("\\[", "[")
            append(emoji_replace(plain_text) if emoji else plain_text)
        elif tag is not None:
            if tag.name.startswith("/"):  # Closing tag
                style_name = tag.name[1:].strip()

                if style_name:  # explicit close
                    style_name = normalize(style_name)
                    try:
                        start, open_tag = pop_style(style_name)
                    except KeyError:
                        raise MarkupError(
                            f"closing tag '{tag.markup}' at position {position} doesn't match any open tag"
                        ) from None
                else:  # implicit close
                    try:
                        start, open_tag = pop()
                    except IndexError:
                        raise MarkupError(
                            f"closing tag '[/]' at position {position} has nothing to close"
                        ) from None

                if open_tag.name.startswith("@"):
                    if open_tag.parameters:
                        handler_name = ""
                        parameters = open_tag.parameters.strip()
                        handler_match = RE_HANDLER.match(parameters)
                        if handler_match is not None:
                            handler_name, match_parameters = handler_match.groups()
                            parameters = (
                                "()" if match_parameters is None else match_parameters
                            )

                        try:
                            meta_params = literal_eval(parameters)
                        except SyntaxError as error:
                            raise MarkupError(
                                f"error parsing {parameters!r} in {open_tag.parameters!r}; {error.msg}"
                            )
                        except Exception as error:
                            raise MarkupError(
                                f"error parsing {open_tag.parameters!r}; {error}"
                            ) from None

                        if handler_name:
                            meta_params = (
                                handler_name,
                                meta_params
                                if isinstance(meta_params, tuple)
                                else (meta_params,),
                            )

                    else:
                        meta_params = ()

                    append_span(
                        _Span(
                            start, len(text), Style(meta={open_tag.name: meta_params})
                        )
                    )
                else:
                    append_span(_Span(start, len(text), str(open_tag)))

            else:  # Opening tag
                normalized_tag = _Tag(normalize(tag.name), tag.parameters)
                style_stack.append((len(text), normalized_tag))

    text_length = len(text)
    while style_stack:
        start, tag = style_stack.pop()
        style = str(tag)
        if style:
            append_span(_Span(start, text_length, style))

    text.spans = sorted(spans[::-1], key=attrgetter("start"))
    return text


if __name__ == "__main__":  # pragma: no cover
    MARKUP = [
        "[red]Hello World[/red]",
        "[magenta]Hello [b]World[/b]",
        "[bold]Bold[italic] bold and italic [/bold]italic[/italic]",
        "Click [link=https://www.willmcgugan.com]here[/link] to visit my Blog",
        ":warning-emoji: [bold red blink] DANGER![/]",
    ]

    from pip._vendor.rich import print
    from pip._vendor.rich.table import Table

    grid = Table("Markup", "Result", padding=(0, 1))

    for markup in MARKUP:
        grid.add_row(Text(markup), markup)

    print(grid)

# === NexusCore/openenv\Lib\site-packages\fsspec\mapping.py ===
import array
import logging
import posixpath
import warnings
from collections.abc import MutableMapping
from functools import cached_property

from fsspec.core import url_to_fs

logger = logging.getLogger("fsspec.mapping")


class FSMap(MutableMapping):
    """Wrap a FileSystem instance as a mutable wrapping.

    The keys of the mapping become files under the given root, and the
    values (which must be bytes) the contents of those files.

    Parameters
    ----------
    root: string
        prefix for all the files
    fs: FileSystem instance
    check: bool (=True)
        performs a touch at the location, to check for write access.

    Examples
    --------
    >>> fs = FileSystem(**parameters)  # doctest: +SKIP
    >>> d = FSMap('my-data/path/', fs)  # doctest: +SKIP
    or, more likely
    >>> d = fs.get_mapper('my-data/path/')

    >>> d['loc1'] = b'Hello World'  # doctest: +SKIP
    >>> list(d.keys())  # doctest: +SKIP
    ['loc1']
    >>> d['loc1']  # doctest: +SKIP
    b'Hello World'
    """

    def __init__(self, root, fs, check=False, create=False, missing_exceptions=None):
        self.fs = fs
        self.root = fs._strip_protocol(root)
        self._root_key_to_str = fs._strip_protocol(posixpath.join(root, "x"))[:-1]
        if missing_exceptions is None:
            missing_exceptions = (
                FileNotFoundError,
                IsADirectoryError,
                NotADirectoryError,
            )
        self.missing_exceptions = missing_exceptions
        self.check = check
        self.create = create
        if create:
            if not self.fs.exists(root):
                self.fs.mkdir(root)
        if check:
            if not self.fs.exists(root):
                raise ValueError(
                    f"Path {root} does not exist. Create "
                    f" with the ``create=True`` keyword"
                )
            self.fs.touch(root + "/a")
            self.fs.rm(root + "/a")

    @cached_property
    def dirfs(self):
        """dirfs instance that can be used with the same keys as the mapper"""
        from .implementations.dirfs import DirFileSystem

        return DirFileSystem(path=self._root_key_to_str, fs=self.fs)

    def clear(self):
        """Remove all keys below root - empties out mapping"""
        logger.info("Clear mapping at %s", self.root)
        try:
            self.fs.rm(self.root, True)
            self.fs.mkdir(self.root)
        except:  # noqa: E722
            pass

    def getitems(self, keys, on_error="raise"):
        """Fetch multiple items from the store

        If the backend is async-able, this might proceed concurrently

        Parameters
        ----------
        keys: list(str)
            They keys to be fetched
        on_error : "raise", "omit", "return"
            If raise, an underlying exception will be raised (converted to KeyError
            if the type is in self.missing_exceptions); if omit, keys with exception
            will simply not be included in the output; if "return", all keys are
            included in the output, but the value will be bytes or an exception
            instance.

        Returns
        -------
        dict(key, bytes|exception)
        """
        keys2 = [self._key_to_str(k) for k in keys]
        oe = on_error if on_error == "raise" else "return"
        try:
            out = self.fs.cat(keys2, on_error=oe)
            if isinstance(out, bytes):
                out = {keys2[0]: out}
        except self.missing_exceptions as e:
            raise KeyError from e
        out = {
            k: (KeyError() if isinstance(v, self.missing_exceptions) else v)
            for k, v in out.items()
        }
        return {
            key: out[k2] if on_error == "raise" else out.get(k2, KeyError(k2))
            for key, k2 in zip(keys, keys2)
            if on_error == "return" or not isinstance(out[k2], BaseException)
        }

    def setitems(self, values_dict):
        """Set the values of multiple items in the store

        Parameters
        ----------
        values_dict: dict(str, bytes)
        """
        values = {self._key_to_str(k): maybe_convert(v) for k, v in values_dict.items()}
        self.fs.pipe(values)

    def delitems(self, keys):
        """Remove multiple keys from the store"""
        self.fs.rm([self._key_to_str(k) for k in keys])

    def _key_to_str(self, key):
        """Generate full path for the key"""
        if not isinstance(key, str):
            # raise TypeError("key must be of type `str`, got `{type(key).__name__}`"
            warnings.warn(
                "from fsspec 2023.5 onward FSMap non-str keys will raise TypeError",
                DeprecationWarning,
            )
            if isinstance(key, list):
                key = tuple(key)
            key = str(key)
        return f"{self._root_key_to_str}{key}".rstrip("/")

    def _str_to_key(self, s):
        """Strip path of to leave key name"""
        return s[len(self.root) :].lstrip("/")

    def __getitem__(self, key, default=None):
        """Retrieve data"""
        k = self._key_to_str(key)
        try:
            result = self.fs.cat(k)
        except self.missing_exceptions as exc:
            if default is not None:
                return default
            raise KeyError(key) from exc
        return result

    def pop(self, key, default=None):
        """Pop data"""
        result = self.__getitem__(key, default)
        try:
            del self[key]
        except KeyError:
            pass
        return result

    def __setitem__(self, key, value):
        """Store value in key"""
        key = self._key_to_str(key)
        self.fs.mkdirs(self.fs._parent(key), exist_ok=True)
        self.fs.pipe_file(key, maybe_convert(value))

    def __iter__(self):
        return (self._str_to_key(x) for x in self.fs.find(self.root))

    def __len__(self):
        return len(self.fs.find(self.root))

    def __delitem__(self, key):
        """Remove key"""
        try:
            self.fs.rm(self._key_to_str(key))
        except Exception as exc:
            raise KeyError from exc

    def __contains__(self, key):
        """Does key exist in mapping?"""
        path = self._key_to_str(key)
        return self.fs.isfile(path)

    def __reduce__(self):
        return FSMap, (self.root, self.fs, False, False, self.missing_exceptions)


def maybe_convert(value):
    if isinstance(value, array.array) or hasattr(value, "__array__"):
        # bytes-like things
        if hasattr(value, "dtype") and value.dtype.kind in "Mm":
            # The buffer interface doesn't support datetime64/timdelta64 numpy
            # arrays
            value = value.view("int64")
        value = bytes(memoryview(value))
    return value


def get_mapper(
    url="",
    check=False,
    create=False,
    missing_exceptions=None,
    alternate_root=None,
    **kwargs,
):
    """Create key-value interface for given URL and options

    The URL will be of the form "protocol://location" and point to the root
    of the mapper required. All keys will be file-names below this location,
    and their values the contents of each key.

    Also accepts compound URLs like zip::s3://bucket/file.zip , see ``fsspec.open``.

    Parameters
    ----------
    url: str
        Root URL of mapping
    check: bool
        Whether to attempt to read from the location before instantiation, to
        check that the mapping does exist
    create: bool
        Whether to make the directory corresponding to the root before
        instantiating
    missing_exceptions: None or tuple
        If given, these exception types will be regarded as missing keys and
        return KeyError when trying to read data. By default, you get
        (FileNotFoundError, IsADirectoryError, NotADirectoryError)
    alternate_root: None or str
        In cases of complex URLs, the parser may fail to pick the correct part
        for the mapper root, so this arg can override

    Returns
    -------
    ``FSMap`` instance, the dict-like key-value store.
    """
    # Removing protocol here - could defer to each open() on the backend
    fs, urlpath = url_to_fs(url, **kwargs)
    root = alternate_root if alternate_root is not None else urlpath
    return FSMap(root, fs, check, create, missing_exceptions=missing_exceptions)

# === NexusCore/openenv\Lib\site-packages\nltk\decorators.py ===
"""
Decorator module by Michele Simionato <michelesimionato@libero.it>
Copyright Michele Simionato, distributed under the terms of the BSD License (see below).
http://www.phyast.pitt.edu/~micheles/python/documentation.html

Included in NLTK for its support of a nice memoization decorator.
"""

__docformat__ = "restructuredtext en"

## The basic trick is to generate the source code for the decorated function
## with the right signature and to evaluate it.
## Uncomment the statement 'print >> sys.stderr, func_src'  in _decorator
## to understand what is going on.

__all__ = ["decorator", "new_wrapper", "getinfo"]

import sys

# Hack to keep NLTK's "tokenize" module from colliding with the "tokenize" in
# the Python standard library.
OLD_SYS_PATH = sys.path[:]
sys.path = [p for p in sys.path if p and "nltk" not in str(p)]
import inspect

sys.path = OLD_SYS_PATH


def __legacysignature(signature):
    """
    For retrocompatibility reasons, we don't use a standard Signature.
    Instead, we use the string generated by this method.
    Basically, from a Signature we create a string and remove the default values.
    """
    listsignature = str(signature)[1:-1].split(",")
    for counter, param in enumerate(listsignature):
        if param.count("=") > 0:
            listsignature[counter] = param[0 : param.index("=")].strip()
        else:
            listsignature[counter] = param.strip()
    return ", ".join(listsignature)


def getinfo(func):
    """
    Returns an info dictionary containing:
    - name (the name of the function : str)
    - argnames (the names of the arguments : list)
    - defaults (the values of the default arguments : tuple)
    - signature (the signature : str)
    - fullsignature (the full signature : Signature)
    - doc (the docstring : str)
    - module (the module name : str)
    - dict (the function __dict__ : str)

    >>> def f(self, x=1, y=2, *args, **kw): pass

    >>> info = getinfo(f)

    >>> info["name"]
    'f'
    >>> info["argnames"]
    ['self', 'x', 'y', 'args', 'kw']

    >>> info["defaults"]
    (1, 2)

    >>> info["signature"]
    'self, x, y, *args, **kw'

    >>> info["fullsignature"]
    <Signature (self, x=1, y=2, *args, **kw)>
    """
    assert inspect.ismethod(func) or inspect.isfunction(func)
    argspec = inspect.getfullargspec(func)
    regargs, varargs, varkwargs = argspec[:3]
    argnames = list(regargs)
    if varargs:
        argnames.append(varargs)
    if varkwargs:
        argnames.append(varkwargs)
    fullsignature = inspect.signature(func)
    # Convert Signature to str
    signature = __legacysignature(fullsignature)

    # pypy compatibility
    if hasattr(func, "__closure__"):
        _closure = func.__closure__
        _globals = func.__globals__
    else:
        _closure = func.func_closure
        _globals = func.func_globals

    return dict(
        name=func.__name__,
        argnames=argnames,
        signature=signature,
        fullsignature=fullsignature,
        defaults=func.__defaults__,
        doc=func.__doc__,
        module=func.__module__,
        dict=func.__dict__,
        globals=_globals,
        closure=_closure,
    )


def update_wrapper(wrapper, model, infodict=None):
    "akin to functools.update_wrapper"
    infodict = infodict or getinfo(model)
    wrapper.__name__ = infodict["name"]
    wrapper.__doc__ = infodict["doc"]
    wrapper.__module__ = infodict["module"]
    wrapper.__dict__.update(infodict["dict"])
    wrapper.__defaults__ = infodict["defaults"]
    wrapper.undecorated = model
    return wrapper


def new_wrapper(wrapper, model):
    """
    An improvement over functools.update_wrapper. The wrapper is a generic
    callable object. It works by generating a copy of the wrapper with the
    right signature and by updating the copy, not the original.
    Moreovoer, 'model' can be a dictionary with keys 'name', 'doc', 'module',
    'dict', 'defaults'.
    """
    if isinstance(model, dict):
        infodict = model
    else:  # assume model is a function
        infodict = getinfo(model)
    assert (
        not "_wrapper_" in infodict["argnames"]
    ), '"_wrapper_" is a reserved argument name!'
    src = "lambda %(signature)s: _wrapper_(%(signature)s)" % infodict
    funcopy = eval(src, dict(_wrapper_=wrapper))
    return update_wrapper(funcopy, model, infodict)


# helper used in decorator_factory
def __call__(self, func):
    return new_wrapper(lambda *a, **k: self.call(func, *a, **k), func)


def decorator_factory(cls):
    """
    Take a class with a ``.caller`` method and return a callable decorator
    object. It works by adding a suitable __call__ method to the class;
    it raises a TypeError if the class already has a nontrivial __call__
    method.
    """
    attrs = set(dir(cls))
    if "__call__" in attrs:
        raise TypeError(
            "You cannot decorate a class with a nontrivial " "__call__ method"
        )
    if "call" not in attrs:
        raise TypeError("You cannot decorate a class without a " ".call method")
    cls.__call__ = __call__
    return cls


def decorator(caller):
    """
    General purpose decorator factory: takes a caller function as
    input and returns a decorator with the same attributes.
    A caller function is any function like this::

     def caller(func, *args, **kw):
         # do something
         return func(*args, **kw)

    Here is an example of usage:

    >>> @decorator
    ... def chatty(f, *args, **kw):
    ...     print("Calling %r" % f.__name__)
    ...     return f(*args, **kw)

    >>> chatty.__name__
    'chatty'

    >>> @chatty
    ... def f(): pass
    ...
    >>> f()
    Calling 'f'

    decorator can also take in input a class with a .caller method; in this
    case it converts the class into a factory of callable decorator objects.
    See the documentation for an example.
    """
    if inspect.isclass(caller):
        return decorator_factory(caller)

    def _decorator(func):  # the real meat is here
        infodict = getinfo(func)
        argnames = infodict["argnames"]
        assert not (
            "_call_" in argnames or "_func_" in argnames
        ), "You cannot use _call_ or _func_ as argument names!"
        src = "lambda %(signature)s: _call_(_func_, %(signature)s)" % infodict
        # import sys; print >> sys.stderr, src # for debugging purposes
        dec_func = eval(src, dict(_func_=func, _call_=caller))
        return update_wrapper(dec_func, func, infodict)

    return update_wrapper(_decorator, caller)


def getattr_(obj, name, default_thunk):
    "Similar to .setdefault in dictionaries."
    try:
        return getattr(obj, name)
    except AttributeError:
        default = default_thunk()
        setattr(obj, name, default)
        return default


@decorator
def memoize(func, *args):
    dic = getattr_(func, "memoize_dic", dict)
    # memoize_dic is created at the first call
    if args in dic:
        return dic[args]
    result = func(*args)
    dic[args] = result
    return result


##########################     LEGALESE    ###############################

##   Redistributions of source code must retain the above copyright
##   notice, this list of conditions and the following disclaimer.
##   Redistributions in bytecode form must reproduce the above copyright
##   notice, this list of conditions and the following disclaimer in
##   the documentation and/or other materials provided with the
##   distribution.

##   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
##   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
##   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
##   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
##   HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
##   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
##   BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
##   OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
##   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
##   TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
##   USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
##   DAMAGE.

# === NexusCore/openenv\Lib\site-packages\rich\markup.py ===
import re
from ast import literal_eval
from operator import attrgetter
from typing import Callable, Iterable, List, Match, NamedTuple, Optional, Tuple, Union

from ._emoji_replace import _emoji_replace
from .emoji import EmojiVariant
from .errors import MarkupError
from .style import Style
from .text import Span, Text

RE_TAGS = re.compile(
    r"""((\\*)\[([a-z#/@][^[]*?)])""",
    re.VERBOSE,
)

RE_HANDLER = re.compile(r"^([\w.]*?)(\(.*?\))?$")


class Tag(NamedTuple):
    """A tag in console markup."""

    name: str
    """The tag name. e.g. 'bold'."""
    parameters: Optional[str]
    """Any additional parameters after the name."""

    def __str__(self) -> str:
        return (
            self.name if self.parameters is None else f"{self.name} {self.parameters}"
        )

    @property
    def markup(self) -> str:
        """Get the string representation of this tag."""
        return (
            f"[{self.name}]"
            if self.parameters is None
            else f"[{self.name}={self.parameters}]"
        )


_ReStringMatch = Match[str]  # regex match object
_ReSubCallable = Callable[[_ReStringMatch], str]  # Callable invoked by re.sub
_EscapeSubMethod = Callable[[_ReSubCallable, str], str]  # Sub method of a compiled re


def escape(
    markup: str,
    _escape: _EscapeSubMethod = re.compile(r"(\\*)(\[[a-z#/@][^[]*?])").sub,
) -> str:
    """Escapes text so that it won't be interpreted as markup.

    Args:
        markup (str): Content to be inserted in to markup.

    Returns:
        str: Markup with square brackets escaped.
    """

    def escape_backslashes(match: Match[str]) -> str:
        """Called by re.sub replace matches."""
        backslashes, text = match.groups()
        return f"{backslashes}{backslashes}\\{text}"

    markup = _escape(escape_backslashes, markup)
    if markup.endswith("\\") and not markup.endswith("\\\\"):
        return markup + "\\"

    return markup


def _parse(markup: str) -> Iterable[Tuple[int, Optional[str], Optional[Tag]]]:
    """Parse markup in to an iterable of tuples of (position, text, tag).

    Args:
        markup (str): A string containing console markup

    """
    position = 0
    _divmod = divmod
    _Tag = Tag
    for match in RE_TAGS.finditer(markup):
        full_text, escapes, tag_text = match.groups()
        start, end = match.span()
        if start > position:
            yield start, markup[position:start], None
        if escapes:
            backslashes, escaped = _divmod(len(escapes), 2)
            if backslashes:
                # Literal backslashes
                yield start, "\\" * backslashes, None
                start += backslashes * 2
            if escaped:
                # Escape of tag
                yield start, full_text[len(escapes) :], None
                position = end
                continue
        text, equals, parameters = tag_text.partition("=")
        yield start, None, _Tag(text, parameters if equals else None)
        position = end
    if position < len(markup):
        yield position, markup[position:], None


def render(
    markup: str,
    style: Union[str, Style] = "",
    emoji: bool = True,
    emoji_variant: Optional[EmojiVariant] = None,
) -> Text:
    """Render console markup in to a Text instance.

    Args:
        markup (str): A string containing console markup.
        style: (Union[str, Style]): The style to use.
        emoji (bool, optional): Also render emoji code. Defaults to True.
        emoji_variant (str, optional): Optional emoji variant, either "text" or "emoji". Defaults to None.


    Raises:
        MarkupError: If there is a syntax error in the markup.

    Returns:
        Text: A test instance.
    """
    emoji_replace = _emoji_replace
    if "[" not in markup:
        return Text(
            emoji_replace(markup, default_variant=emoji_variant) if emoji else markup,
            style=style,
        )
    text = Text(style=style)
    append = text.append
    normalize = Style.normalize

    style_stack: List[Tuple[int, Tag]] = []
    pop = style_stack.pop

    spans: List[Span] = []
    append_span = spans.append

    _Span = Span
    _Tag = Tag

    def pop_style(style_name: str) -> Tuple[int, Tag]:
        """Pop tag matching given style name."""
        for index, (_, tag) in enumerate(reversed(style_stack), 1):
            if tag.name == style_name:
                return pop(-index)
        raise KeyError(style_name)

    for position, plain_text, tag in _parse(markup):
        if plain_text is not None:
            # Handle open brace escapes, where the brace is not part of a tag.
            plain_text = plain_text.replace("\\[", "[")
            append(emoji_replace(plain_text) if emoji else plain_text)
        elif tag is not None:
            if tag.name.startswith("/"):  # Closing tag
                style_name = tag.name[1:].strip()

                if style_name:  # explicit close
                    style_name = normalize(style_name)
                    try:
                        start, open_tag = pop_style(style_name)
                    except KeyError:
                        raise MarkupError(
                            f"closing tag '{tag.markup}' at position {position} doesn't match any open tag"
                        ) from None
                else:  # implicit close
                    try:
                        start, open_tag = pop()
                    except IndexError:
                        raise MarkupError(
                            f"closing tag '[/]' at position {position} has nothing to close"
                        ) from None

                if open_tag.name.startswith("@"):
                    if open_tag.parameters:
                        handler_name = ""
                        parameters = open_tag.parameters.strip()
                        handler_match = RE_HANDLER.match(parameters)
                        if handler_match is not None:
                            handler_name, match_parameters = handler_match.groups()
                            parameters = (
                                "()" if match_parameters is None else match_parameters
                            )

                        try:
                            meta_params = literal_eval(parameters)
                        except SyntaxError as error:
                            raise MarkupError(
                                f"error parsing {parameters!r} in {open_tag.parameters!r}; {error.msg}"
                            )
                        except Exception as error:
                            raise MarkupError(
                                f"error parsing {open_tag.parameters!r}; {error}"
                            ) from None

                        if handler_name:
                            meta_params = (
                                handler_name,
                                meta_params
                                if isinstance(meta_params, tuple)
                                else (meta_params,),
                            )

                    else:
                        meta_params = ()

                    append_span(
                        _Span(
                            start, len(text), Style(meta={open_tag.name: meta_params})
                        )
                    )
                else:
                    append_span(_Span(start, len(text), str(open_tag)))

            else:  # Opening tag
                normalized_tag = _Tag(normalize(tag.name), tag.parameters)
                style_stack.append((len(text), normalized_tag))

    text_length = len(text)
    while style_stack:
        start, tag = style_stack.pop()
        style = str(tag)
        if style:
            append_span(_Span(start, text_length, style))

    text.spans = sorted(spans[::-1], key=attrgetter("start"))
    return text


if __name__ == "__main__":  # pragma: no cover
    MARKUP = [
        "[red]Hello World[/red]",
        "[magenta]Hello [b]World[/b]",
        "[bold]Bold[italic] bold and italic [/bold]italic[/italic]",
        "Click [link=https://www.willmcgugan.com]here[/link] to visit my Blog",
        ":warning-emoji: [bold red blink] DANGER![/]",
    ]

    from rich import print
    from rich.table import Table

    grid = Table("Markup", "Result", padding=(0, 1))

    for markup in MARKUP:
        grid.add_row(Text(markup), markup)

    print(grid)

# === NexusCore/openenv\Lib\site-packages\trio\_highlevel_open_tcp_listeners.py ===
from __future__ import annotations

import errno
import sys
from typing import TYPE_CHECKING

import trio
from trio import TaskStatus

from . import socket as tsocket

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


# Default backlog size:
#
# Having the backlog too low can cause practical problems (a perfectly healthy
# service that starts failing to accept connections if they arrive in a
# burst).
#
# Having it too high doesn't really cause any problems. Like any buffer, you
# want backlog queue to be zero usually, and it won't save you if you're
# getting connection attempts faster than you can call accept() on an ongoing
# basis. But unlike other buffers, this one doesn't really provide any
# backpressure. If a connection gets stuck waiting in the backlog queue, then
# from the peer's point of view the connection succeeded but then their
# send/recv will stall until we get to it, possibly for a long time. OTOH if
# there isn't room in the backlog queue, then their connect stalls, possibly
# for a long time, which is pretty much the same thing.
#
# A large backlog can also use a bit more kernel memory, but this seems fairly
# negligible these days.
#
# So this suggests we should make the backlog as large as possible. This also
# matches what Golang does. However, they do it in a weird way, where they
# have a bunch of code to sniff out the configured upper limit for backlog on
# different operating systems. But on every system, passing in a too-large
# backlog just causes it to be silently truncated to the configured maximum,
# so this is unnecessary -- we can just pass in "infinity" and get the maximum
# that way. (Verified on Windows, Linux, macOS using
# https://github.com/python-trio/trio/wiki/notes-to-self#measure-listen-backlogpy
def _compute_backlog(backlog: int | None) -> int:
    # Many systems (Linux, BSDs, ...) store the backlog in a uint16 and are
    # missing overflow protection, so we apply our own overflow protection.
    # https://github.com/golang/go/issues/5030
    if not isinstance(backlog, int) and backlog is not None:
        raise TypeError(f"backlog must be an int or None, not {backlog!r}")
    if backlog is None:
        return 0xFFFF
    return min(backlog, 0xFFFF)


async def open_tcp_listeners(
    port: int,
    *,
    host: str | bytes | None = None,
    backlog: int | None = None,
) -> list[trio.SocketListener]:
    """Create :class:`SocketListener` objects to listen for TCP connections.

    Args:

      port (int): The port to listen on.

          If you use 0 as your port, then the kernel will automatically pick
          an arbitrary open port. But be careful: if you use this feature when
          binding to multiple IP addresses, then each IP address will get its
          own random port, and the returned listeners will probably be
          listening on different ports. In particular, this will happen if you
          use ``host=None`` – which is the default – because in this case
          :func:`open_tcp_listeners` will bind to both the IPv4 wildcard
          address (``0.0.0.0``) and also the IPv6 wildcard address (``::``).

      host (str, bytes, or None): The local interface to bind to. This is
          passed to :func:`~socket.getaddrinfo` with the ``AI_PASSIVE`` flag
          set.

          If you want to bind to the wildcard address on both IPv4 and IPv6,
          in order to accept connections on all available interfaces, then
          pass ``None``. This is the default.

          If you have a specific interface you want to bind to, pass its IP
          address or hostname here. If a hostname resolves to multiple IP
          addresses, this function will open one listener on each of them.

          If you want to use only IPv4, or only IPv6, but want to accept on
          all interfaces, pass the family-specific wildcard address:
          ``"0.0.0.0"`` for IPv4-only and ``"::"`` for IPv6-only.

      backlog (int or None): The listen backlog to use. If you leave this as
          ``None`` then Trio will pick a good default. (Currently: whatever
          your system has configured as the maximum backlog.)

    Returns:
      list of :class:`SocketListener`

    Raises:
      :class:`TypeError` if invalid arguments.

    """
    # getaddrinfo sometimes allows port=None, sometimes not (depending on
    # whether host=None). And on some systems it treats "" as 0, others it
    # doesn't:
    #   http://klickverbot.at/blog/2012/01/getaddrinfo-edge-case-behavior-on-windows-linux-and-osx/
    if not isinstance(port, int):
        raise TypeError(f"port must be an int not {port!r}")

    computed_backlog = _compute_backlog(backlog)

    addresses = await tsocket.getaddrinfo(
        host,
        port,
        type=tsocket.SOCK_STREAM,
        flags=tsocket.AI_PASSIVE,
    )

    listeners = []
    unsupported_address_families = []
    try:
        for family, type_, proto, _, sockaddr in addresses:
            try:
                sock = tsocket.socket(family, type_, proto)
            except OSError as ex:
                if ex.errno == errno.EAFNOSUPPORT:
                    # If a system only supports IPv4, or only IPv6, it
                    # is still likely that getaddrinfo will return
                    # both an IPv4 and an IPv6 address. As long as at
                    # least one of the returned addresses can be
                    # turned into a socket, we won't complain about a
                    # failure to create the other.
                    unsupported_address_families.append(ex)
                    continue
                else:
                    raise
            try:
                # See https://github.com/python-trio/trio/issues/39
                if sys.platform != "win32":
                    sock.setsockopt(tsocket.SOL_SOCKET, tsocket.SO_REUSEADDR, 1)

                if family == tsocket.AF_INET6:
                    sock.setsockopt(tsocket.IPPROTO_IPV6, tsocket.IPV6_V6ONLY, 1)

                await sock.bind(sockaddr)
                sock.listen(computed_backlog)

                listeners.append(trio.SocketListener(sock))
            except:
                sock.close()
                raise
    except:
        for listener in listeners:
            listener.socket.close()
        raise

    if unsupported_address_families and not listeners:
        msg = (
            "This system doesn't support any of the kinds of "
            "socket that that address could use"
        )
        raise OSError(errno.EAFNOSUPPORT, msg) from ExceptionGroup(
            msg,
            unsupported_address_families,
        )

    return listeners


async def serve_tcp(
    handler: Callable[[trio.SocketStream], Awaitable[object]],
    port: int,
    *,
    host: str | bytes | None = None,
    backlog: int | None = None,
    handler_nursery: trio.Nursery | None = None,
    task_status: TaskStatus[list[trio.SocketListener]] = trio.TASK_STATUS_IGNORED,
) -> None:
    """Listen for incoming TCP connections, and for each one start a task
    running ``handler(stream)``.

    This is a thin convenience wrapper around :func:`open_tcp_listeners` and
    :func:`serve_listeners` – see them for full details.

    .. warning::

       If ``handler`` raises an exception, then this function doesn't do
       anything special to catch it – so by default the exception will
       propagate out and crash your server. If you don't want this, then catch
       exceptions inside your ``handler``, or use a ``handler_nursery`` object
       that responds to exceptions in some other way.

    When used with ``nursery.start`` you get back the newly opened listeners.
    So, for example, if you want to start a server in your test suite and then
    connect to it to check that it's working properly, you can use something
    like::

        from trio import SocketListener, SocketStream
        from trio.testing import open_stream_to_socket_listener

        async with trio.open_nursery() as nursery:
            listeners: list[SocketListener] = await nursery.start(serve_tcp, handler, 0)
            client_stream: SocketStream = await open_stream_to_socket_listener(listeners[0])

            # Then send and receive data on 'client_stream', for example:
            await client_stream.send_all(b"GET / HTTP/1.0\\r\\n\\r\\n")

    This avoids several common pitfalls:

    1. It lets the kernel pick a random open port, so your test suite doesn't
       depend on any particular port being open.

    2. It waits for the server to be accepting connections on that port before
       ``start`` returns, so there's no race condition where the incoming
       connection arrives before the server is ready.

    3. It uses the Listener object to find out which port was picked, so it
       can connect to the right place.

    Args:
      handler: The handler to start for each incoming connection. Passed to
          :func:`serve_listeners`.

      port: The port to listen on. Use 0 to let the kernel pick an open port.
          Passed to :func:`open_tcp_listeners`.

      host (str, bytes, or None): The host interface to listen on; use
          ``None`` to bind to the wildcard address. Passed to
          :func:`open_tcp_listeners`.

      backlog: The listen backlog, or None to have a good default picked.
          Passed to :func:`open_tcp_listeners`.

      handler_nursery: The nursery to start handlers in, or None to use an
          internal nursery. Passed to :func:`serve_listeners`.

      task_status: This function can be used with ``nursery.start``.

    Returns:
      This function only returns when cancelled.

    """
    listeners = await trio.open_tcp_listeners(port, host=host, backlog=backlog)
    await trio.serve_listeners(
        handler,
        listeners,
        handler_nursery=handler_nursery,
        task_status=task_status,
    )

# === NexusCore/openenv\Lib\site-packages\google\oauth2\gdch_credentials.py ===
# Copyright 2022 Google LLC
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

"""Experimental GDCH credentials support.
"""

import datetime

from google.auth import _helpers
from google.auth import _service_account_info
from google.auth import credentials
from google.auth import exceptions
from google.auth import jwt
from google.oauth2 import _client


TOKEN_EXCHANGE_TYPE = "urn:ietf:params:oauth:token-type:token-exchange"
ACCESS_TOKEN_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"
SERVICE_ACCOUNT_TOKEN_TYPE = "urn:k8s:params:oauth:token-type:serviceaccount"
JWT_LIFETIME = datetime.timedelta(seconds=3600)  # 1 hour


class ServiceAccountCredentials(credentials.Credentials):
    """Credentials for GDCH (`Google Distributed Cloud Hosted`_) for service
    account users.

    .. _Google Distributed Cloud Hosted:
        https://cloud.google.com/blog/topics/hybrid-cloud/\
            announcing-google-distributed-cloud-edge-and-hosted

    To create a GDCH service account credential, first create a JSON file of
    the following format::

        {
            "type": "gdch_service_account",
            "format_version": "1",
            "project": "<project name>",
            "private_key_id": "<key id>",
            "private_key": "-----BEGIN EC PRIVATE KEY-----\n<key bytes>\n-----END EC PRIVATE KEY-----\n",
            "name": "<service identity name>",
            "ca_cert_path": "<CA cert path>",
            "token_uri": "https://service-identity.<Domain>/authenticate"
        }

    The "format_version" field stands for the format of the JSON file. For now
    it is always "1". The `private_key_id` and `private_key` is used for signing.
    The `ca_cert_path` is used for token server TLS certificate verification.

    After the JSON file is created, set `GOOGLE_APPLICATION_CREDENTIALS` environment
    variable to the JSON file path, then use the following code to create the
    credential::

        import google.auth

        credential, _ = google.auth.default()
        credential = credential.with_gdch_audience("<the audience>")

    We can also create the credential directly::

        from google.oauth import gdch_credentials

        credential = gdch_credentials.ServiceAccountCredentials.from_service_account_file("<the json file path>")
        credential = credential.with_gdch_audience("<the audience>")

    The token is obtained in the following way. This class first creates a
    self signed JWT. It uses the `name` value as the `iss` and `sub` claim, and
    the `token_uri` as the `aud` claim, and signs the JWT with the `private_key`.
    It then sends the JWT to the `token_uri` to exchange a final token for
    `audience`.
    """

    def __init__(
        self, signer, service_identity_name, project, audience, token_uri, ca_cert_path
    ):
        """
        Args:
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
            service_identity_name (str): The service identity name. It will be
                used as the `iss` and `sub` claim in the self signed JWT.
            project (str): The project.
            audience (str): The audience for the final token.
            token_uri (str): The token server uri.
            ca_cert_path (str): The CA cert path for token server side TLS
                certificate verification. If the token server uses well known
                CA, then this parameter can be `None`.
        """
        super(ServiceAccountCredentials, self).__init__()
        self._signer = signer
        self._service_identity_name = service_identity_name
        self._project = project
        self._audience = audience
        self._token_uri = token_uri
        self._ca_cert_path = ca_cert_path

    def _create_jwt(self):
        now = _helpers.utcnow()
        expiry = now + JWT_LIFETIME
        iss_sub_value = "system:serviceaccount:{}:{}".format(
            self._project, self._service_identity_name
        )

        payload = {
            "iss": iss_sub_value,
            "sub": iss_sub_value,
            "aud": self._token_uri,
            "iat": _helpers.datetime_to_secs(now),
            "exp": _helpers.datetime_to_secs(expiry),
        }

        return _helpers.from_bytes(jwt.encode(self._signer, payload))

    @_helpers.copy_docstring(credentials.Credentials)
    def refresh(self, request):
        import google.auth.transport.requests

        if not isinstance(request, google.auth.transport.requests.Request):
            raise exceptions.RefreshError(
                "For GDCH service account credentials, request must be a google.auth.transport.requests.Request object"
            )

        # Create a self signed JWT, and do token exchange.
        jwt_token = self._create_jwt()
        request_body = {
            "grant_type": TOKEN_EXCHANGE_TYPE,
            "audience": self._audience,
            "requested_token_type": ACCESS_TOKEN_TOKEN_TYPE,
            "subject_token": jwt_token,
            "subject_token_type": SERVICE_ACCOUNT_TOKEN_TYPE,
        }
        response_data = _client._token_endpoint_request(
            request,
            self._token_uri,
            request_body,
            access_token=None,
            use_json=True,
            verify=self._ca_cert_path,
        )

        self.token, _, self.expiry, _ = _client._handle_refresh_grant_response(
            response_data, None
        )

    def with_gdch_audience(self, audience):
        """Create a copy of GDCH credentials with the specified audience.

        Args:
            audience (str): The intended audience for GDCH credentials.
        """
        return self.__class__(
            self._signer,
            self._service_identity_name,
            self._project,
            audience,
            self._token_uri,
            self._ca_cert_path,
        )

    @classmethod
    def _from_signer_and_info(cls, signer, info):
        """Creates a Credentials instance from a signer and service account
        info.

        Args:
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
            info (Mapping[str, str]): The service account info.

        Returns:
            google.oauth2.gdch_credentials.ServiceAccountCredentials: The constructed
                credentials.

        Raises:
            ValueError: If the info is not in the expected format.
        """
        if info["format_version"] != "1":
            raise ValueError("Only format version 1 is supported")

        return cls(
            signer,
            info["name"],  # service_identity_name
            info["project"],
            None,  # audience
            info["token_uri"],
            info.get("ca_cert_path", None),
        )

    @classmethod
    def from_service_account_info(cls, info):
        """Creates a Credentials instance from parsed service account info.

        Args:
            info (Mapping[str, str]): The service account info in Google
                format.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.oauth2.gdch_credentials.ServiceAccountCredentials: The constructed
                credentials.

        Raises:
            ValueError: If the info is not in the expected format.
        """
        signer = _service_account_info.from_dict(
            info,
            require=[
                "format_version",
                "private_key_id",
                "private_key",
                "name",
                "project",
                "token_uri",
            ],
            use_rsa_signer=False,
        )
        return cls._from_signer_and_info(signer, info)

    @classmethod
    def from_service_account_file(cls, filename):
        """Creates a Credentials instance from a service account json file.

        Args:
            filename (str): The path to the service account json file.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.oauth2.gdch_credentials.ServiceAccountCredentials: The constructed
                credentials.
        """
        info, signer = _service_account_info.from_filename(
            filename,
            require=[
                "format_version",
                "private_key_id",
                "private_key",
                "name",
                "project",
                "token_uri",
            ],
            use_rsa_signer=False,
        )
        return cls._from_signer_and_info(signer, info)

# === NexusCore/openenv\Lib\site-packages\nltk\translate\ibm1.py ===
# Natural Language Toolkit: IBM Model 1
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Chin Yee Lee <c.lee32@student.unimelb.edu.au>
#         Hengfeng Li <hengfeng12345@gmail.com>
#         Ruxin Hou <r.hou@student.unimelb.edu.au>
#         Calvin Tanujaya Lim <c.tanujayalim@gmail.com>
# Based on earlier version by:
#         Will Zhang <wilzzha@gmail.com>
#         Guan Gui <ggui@student.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Lexical translation model that ignores word order.

In IBM Model 1, word order is ignored for simplicity. As long as the
word alignments are equivalent, it doesn't matter where the word occurs
in the source or target sentence. Thus, the following three alignments
are equally likely::

    Source: je mange du jambon
    Target: i eat some ham
    Alignment: (0,0) (1,1) (2,2) (3,3)

    Source: je mange du jambon
    Target: some ham eat i
    Alignment: (0,2) (1,3) (2,1) (3,1)

    Source: du jambon je mange
    Target: eat i some ham
    Alignment: (0,3) (1,2) (2,0) (3,1)

Note that an alignment is represented here as
(word_index_in_target, word_index_in_source).

The EM algorithm used in Model 1 is:

:E step: In the training data, count how many times a source language
         word is translated into a target language word, weighted by
         the prior probability of the translation.

:M step: Estimate the new probability of translation based on the
         counts from the Expectation step.

Notations
---------

:i: Position in the source sentence
     Valid values are 0 (for NULL), 1, 2, ..., length of source sentence
:j: Position in the target sentence
     Valid values are 1, 2, ..., length of target sentence
:s: A word in the source language
:t: A word in the target language

References
----------

Philipp Koehn. 2010. Statistical Machine Translation.
Cambridge University Press, New York.

Peter E Brown, Stephen A. Della Pietra, Vincent J. Della Pietra, and
Robert L. Mercer. 1993. The Mathematics of Statistical Machine
Translation: Parameter Estimation. Computational Linguistics, 19 (2),
263-311.
"""

import warnings
from collections import defaultdict

from nltk.translate import AlignedSent, Alignment, IBMModel
from nltk.translate.ibm_model import Counts


class IBMModel1(IBMModel):
    """
    Lexical translation model that ignores word order

    >>> bitext = []
    >>> bitext.append(AlignedSent(['klein', 'ist', 'das', 'haus'], ['the', 'house', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus', 'ist', 'ja', 'groß'], ['the', 'house', 'is', 'big']))
    >>> bitext.append(AlignedSent(['das', 'buch', 'ist', 'ja', 'klein'], ['the', 'book', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus'], ['the', 'house']))
    >>> bitext.append(AlignedSent(['das', 'buch'], ['the', 'book']))
    >>> bitext.append(AlignedSent(['ein', 'buch'], ['a', 'book']))

    >>> ibm1 = IBMModel1(bitext, 5)

    >>> print(round(ibm1.translation_table['buch']['book'], 3))
    0.889
    >>> print(round(ibm1.translation_table['das']['book'], 3))
    0.062
    >>> print(round(ibm1.translation_table['buch'][None], 3))
    0.113
    >>> print(round(ibm1.translation_table['ja'][None], 3))
    0.073

    >>> test_sentence = bitext[2]
    >>> test_sentence.words
    ['das', 'buch', 'ist', 'ja', 'klein']
    >>> test_sentence.mots
    ['the', 'book', 'is', 'small']
    >>> test_sentence.alignment
    Alignment([(0, 0), (1, 1), (2, 2), (3, 2), (4, 3)])

    """

    def __init__(self, sentence_aligned_corpus, iterations, probability_tables=None):
        """
        Train on ``sentence_aligned_corpus`` and create a lexical
        translation model.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        :param sentence_aligned_corpus: Sentence-aligned parallel corpus
        :type sentence_aligned_corpus: list(AlignedSent)

        :param iterations: Number of iterations to run training algorithm
        :type iterations: int

        :param probability_tables: Optional. Use this to pass in custom
            probability values. If not specified, probabilities will be
            set to a uniform distribution, or some other sensible value.
            If specified, the following entry must be present:
            ``translation_table``.
            See ``IBMModel`` for the type and purpose of this table.
        :type probability_tables: dict[str]: object
        """
        super().__init__(sentence_aligned_corpus)

        if probability_tables is None:
            self.set_uniform_probabilities(sentence_aligned_corpus)
        else:
            # Set user-defined probabilities
            self.translation_table = probability_tables["translation_table"]

        for n in range(0, iterations):
            self.train(sentence_aligned_corpus)

        self.align_all(sentence_aligned_corpus)

    def set_uniform_probabilities(self, sentence_aligned_corpus):
        initial_prob = 1 / len(self.trg_vocab)
        if initial_prob < IBMModel.MIN_PROB:
            warnings.warn(
                "Target language vocabulary is too large ("
                + str(len(self.trg_vocab))
                + " words). "
                "Results may be less accurate."
            )

        for t in self.trg_vocab:
            self.translation_table[t] = defaultdict(lambda: initial_prob)

    def train(self, parallel_corpus):
        counts = Counts()
        for aligned_sentence in parallel_corpus:
            trg_sentence = aligned_sentence.words
            src_sentence = [None] + aligned_sentence.mots

            # E step (a): Compute normalization factors to weigh counts
            total_count = self.prob_all_alignments(src_sentence, trg_sentence)

            # E step (b): Collect counts
            for t in trg_sentence:
                for s in src_sentence:
                    count = self.prob_alignment_point(s, t)
                    normalized_count = count / total_count[t]
                    counts.t_given_s[t][s] += normalized_count
                    counts.any_t_given_s[s] += normalized_count

        # M step: Update probabilities with maximum likelihood estimate
        self.maximize_lexical_translation_probabilities(counts)

    def prob_all_alignments(self, src_sentence, trg_sentence):
        """
        Computes the probability of all possible word alignments,
        expressed as a marginal distribution over target words t

        Each entry in the return value represents the contribution to
        the total alignment probability by the target word t.

        To obtain probability(alignment | src_sentence, trg_sentence),
        simply sum the entries in the return value.

        :return: Probability of t for all s in ``src_sentence``
        :rtype: dict(str): float
        """
        alignment_prob_for_t = defaultdict(float)
        for t in trg_sentence:
            for s in src_sentence:
                alignment_prob_for_t[t] += self.prob_alignment_point(s, t)
        return alignment_prob_for_t

    def prob_alignment_point(self, s, t):
        """
        Probability that word ``t`` in the target sentence is aligned to
        word ``s`` in the source sentence
        """
        return self.translation_table[t][s]

    def prob_t_a_given_s(self, alignment_info):
        """
        Probability of target sentence and an alignment given the
        source sentence
        """
        prob = 1.0

        for j, i in enumerate(alignment_info.alignment):
            if j == 0:
                continue  # skip the dummy zeroeth element
            trg_word = alignment_info.trg_sentence[j]
            src_word = alignment_info.src_sentence[i]
            prob *= self.translation_table[trg_word][src_word]

        return max(prob, IBMModel.MIN_PROB)

    def align_all(self, parallel_corpus):
        for sentence_pair in parallel_corpus:
            self.align(sentence_pair)

    def align(self, sentence_pair):
        """
        Determines the best word alignment for one sentence pair from
        the corpus that the model was trained on.

        The best alignment will be set in ``sentence_pair`` when the
        method returns. In contrast with the internal implementation of
        IBM models, the word indices in the ``Alignment`` are zero-
        indexed, not one-indexed.

        :param sentence_pair: A sentence in the source language and its
            counterpart sentence in the target language
        :type sentence_pair: AlignedSent
        """
        best_alignment = []

        for j, trg_word in enumerate(sentence_pair.words):
            # Initialize trg_word to align with the NULL token
            best_prob = max(self.translation_table[trg_word][None], IBMModel.MIN_PROB)
            best_alignment_point = None
            for i, src_word in enumerate(sentence_pair.mots):
                align_prob = self.translation_table[trg_word][src_word]
                if align_prob >= best_prob:  # prefer newer word in case of tie
                    best_prob = align_prob
                    best_alignment_point = i

            best_alignment.append((j, best_alignment_point))

        sentence_pair.alignment = Alignment(best_alignment)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\markup.py ===
import re
from ast import literal_eval
from operator import attrgetter
from typing import Callable, Iterable, List, Match, NamedTuple, Optional, Tuple, Union

from ._emoji_replace import _emoji_replace
from .emoji import EmojiVariant
from .errors import MarkupError
from .style import Style
from .text import Span, Text

RE_TAGS = re.compile(
    r"""((\\*)\[([a-z#/@][^[]*?)])""",
    re.VERBOSE,
)

RE_HANDLER = re.compile(r"^([\w.]*?)(\(.*?\))?$")


class Tag(NamedTuple):
    """A tag in console markup."""

    name: str
    """The tag name. e.g. 'bold'."""
    parameters: Optional[str]
    """Any additional parameters after the name."""

    def __str__(self) -> str:
        return (
            self.name if self.parameters is None else f"{self.name} {self.parameters}"
        )

    @property
    def markup(self) -> str:
        """Get the string representation of this tag."""
        return (
            f"[{self.name}]"
            if self.parameters is None
            else f"[{self.name}={self.parameters}]"
        )


_ReStringMatch = Match[str]  # regex match object
_ReSubCallable = Callable[[_ReStringMatch], str]  # Callable invoked by re.sub
_EscapeSubMethod = Callable[[_ReSubCallable, str], str]  # Sub method of a compiled re


def escape(
    markup: str,
    _escape: _EscapeSubMethod = re.compile(r"(\\*)(\[[a-z#/@][^[]*?])").sub,
) -> str:
    """Escapes text so that it won't be interpreted as markup.

    Args:
        markup (str): Content to be inserted in to markup.

    Returns:
        str: Markup with square brackets escaped.
    """

    def escape_backslashes(match: Match[str]) -> str:
        """Called by re.sub replace matches."""
        backslashes, text = match.groups()
        return f"{backslashes}{backslashes}\\{text}"

    markup = _escape(escape_backslashes, markup)
    if markup.endswith("\\") and not markup.endswith("\\\\"):
        return markup + "\\"

    return markup


def _parse(markup: str) -> Iterable[Tuple[int, Optional[str], Optional[Tag]]]:
    """Parse markup in to an iterable of tuples of (position, text, tag).

    Args:
        markup (str): A string containing console markup

    """
    position = 0
    _divmod = divmod
    _Tag = Tag
    for match in RE_TAGS.finditer(markup):
        full_text, escapes, tag_text = match.groups()
        start, end = match.span()
        if start > position:
            yield start, markup[position:start], None
        if escapes:
            backslashes, escaped = _divmod(len(escapes), 2)
            if backslashes:
                # Literal backslashes
                yield start, "\\" * backslashes, None
                start += backslashes * 2
            if escaped:
                # Escape of tag
                yield start, full_text[len(escapes) :], None
                position = end
                continue
        text, equals, parameters = tag_text.partition("=")
        yield start, None, _Tag(text, parameters if equals else None)
        position = end
    if position < len(markup):
        yield position, markup[position:], None


def render(
    markup: str,
    style: Union[str, Style] = "",
    emoji: bool = True,
    emoji_variant: Optional[EmojiVariant] = None,
) -> Text:
    """Render console markup in to a Text instance.

    Args:
        markup (str): A string containing console markup.
        style: (Union[str, Style]): The style to use.
        emoji (bool, optional): Also render emoji code. Defaults to True.
        emoji_variant (str, optional): Optional emoji variant, either "text" or "emoji". Defaults to None.


    Raises:
        MarkupError: If there is a syntax error in the markup.

    Returns:
        Text: A test instance.
    """
    emoji_replace = _emoji_replace
    if "[" not in markup:
        return Text(
            emoji_replace(markup, default_variant=emoji_variant) if emoji else markup,
            style=style,
        )
    text = Text(style=style)
    append = text.append
    normalize = Style.normalize

    style_stack: List[Tuple[int, Tag]] = []
    pop = style_stack.pop

    spans: List[Span] = []
    append_span = spans.append

    _Span = Span
    _Tag = Tag

    def pop_style(style_name: str) -> Tuple[int, Tag]:
        """Pop tag matching given style name."""
        for index, (_, tag) in enumerate(reversed(style_stack), 1):
            if tag.name == style_name:
                return pop(-index)
        raise KeyError(style_name)

    for position, plain_text, tag in _parse(markup):
        if plain_text is not None:
            # Handle open brace escapes, where the brace is not part of a tag.
            plain_text = plain_text.replace("\\[", "[")
            append(emoji_replace(plain_text) if emoji else plain_text)
        elif tag is not None:
            if tag.name.startswith("/"):  # Closing tag
                style_name = tag.name[1:].strip()

                if style_name:  # explicit close
                    style_name = normalize(style_name)
                    try:
                        start, open_tag = pop_style(style_name)
                    except KeyError:
                        raise MarkupError(
                            f"closing tag '{tag.markup}' at position {position} doesn't match any open tag"
                        ) from None
                else:  # implicit close
                    try:
                        start, open_tag = pop()
                    except IndexError:
                        raise MarkupError(
                            f"closing tag '[/]' at position {position} has nothing to close"
                        ) from None

                if open_tag.name.startswith("@"):
                    if open_tag.parameters:
                        handler_name = ""
                        parameters = open_tag.parameters.strip()
                        handler_match = RE_HANDLER.match(parameters)
                        if handler_match is not None:
                            handler_name, match_parameters = handler_match.groups()
                            parameters = (
                                "()" if match_parameters is None else match_parameters
                            )

                        try:
                            meta_params = literal_eval(parameters)
                        except SyntaxError as error:
                            raise MarkupError(
                                f"error parsing {parameters!r} in {open_tag.parameters!r}; {error.msg}"
                            )
                        except Exception as error:
                            raise MarkupError(
                                f"error parsing {open_tag.parameters!r}; {error}"
                            ) from None

                        if handler_name:
                            meta_params = (
                                handler_name,
                                meta_params
                                if isinstance(meta_params, tuple)
                                else (meta_params,),
                            )

                    else:
                        meta_params = ()

                    append_span(
                        _Span(
                            start, len(text), Style(meta={open_tag.name: meta_params})
                        )
                    )
                else:
                    append_span(_Span(start, len(text), str(open_tag)))

            else:  # Opening tag
                normalized_tag = _Tag(normalize(tag.name), tag.parameters)
                style_stack.append((len(text), normalized_tag))

    text_length = len(text)
    while style_stack:
        start, tag = style_stack.pop()
        style = str(tag)
        if style:
            append_span(_Span(start, text_length, style))

    text.spans = sorted(spans[::-1], key=attrgetter("start"))
    return text


if __name__ == "__main__":  # pragma: no cover
    MARKUP = [
        "[red]Hello World[/red]",
        "[magenta]Hello [b]World[/b]",
        "[bold]Bold[italic] bold and italic [/bold]italic[/italic]",
        "Click [link=https://www.willmcgugan.com]here[/link] to visit my Blog",
        ":warning-emoji: [bold red blink] DANGER![/]",
    ]

    from pip._vendor.rich import print
    from pip._vendor.rich.table import Table

    grid = Table("Markup", "Result", padding=(0, 1))

    for markup in MARKUP:
        grid.add_row(Text(markup), markup)

    print(grid)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\fantom.py ===
"""
    pygments.lexers.fantom
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Fantom language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from string import Template

from pygments.lexer import RegexLexer, include, bygroups, using, \
    this, default, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Literal, Whitespace

__all__ = ['FantomLexer']


class FantomLexer(RegexLexer):
    """
    For Fantom source code.
    """
    name = 'Fantom'
    aliases = ['fan']
    filenames = ['*.fan']
    mimetypes = ['application/x-fantom']
    url = 'https://www.fantom.org'
    version_added = '1.5'

    # often used regexes
    def s(str):
        return Template(str).substitute(
            dict(
                pod=r'[\"\w\.]+',
                eos=r'\n|;',
                id=r'[a-zA-Z_]\w*',
                # all chars which can be part of type definition. Starts with
                # either letter, or [ (maps), or | (funcs)
                type=r'(?:\[|[a-zA-Z_]|\|)[:\w\[\]|\->?]*?',
            )
        )

    tokens = {
        'comments': [
            (r'(?s)/\*.*?\*/', Comment.Multiline),           # Multiline
            (r'//.*?$', Comment.Single),                    # Single line
            # TODO: highlight references in fandocs
            (r'\*\*.*?$', Comment.Special),                 # Fandoc
            (r'#.*$', Comment.Single)                       # Shell-style
        ],
        'literals': [
            (r'\b-?[\d_]+(ns|ms|sec|min|hr|day)', Number),   # Duration
            (r'\b-?[\d_]*\.[\d_]+(ns|ms|sec|min|hr|day)', Number),  # Duration with dot
            (r'\b-?(\d+)?\.\d+(f|F|d|D)?', Number.Float),    # Float/Decimal
            (r'\b-?0x[0-9a-fA-F_]+', Number.Hex),            # Hex
            (r'\b-?[\d_]+', Number.Integer),                 # Int
            (r"'\\.'|'[^\\]'|'\\u[0-9a-f]{4}'", String.Char),  # Char
            (r'"', Punctuation, 'insideStr'),                # Opening quote
            (r'`', Punctuation, 'insideUri'),                # Opening accent
            (r'\b(true|false|null)\b', Keyword.Constant),    # Bool & null
            (r'(?:(\w+)(::))?(\w+)(<\|)(.*?)(\|>)',          # DSL
             bygroups(Name.Namespace, Punctuation, Name.Class,
                      Punctuation, String, Punctuation)),
            (r'(?:(\w+)(::))?(\w+)?(#)(\w+)?',               # Type/slot literal
             bygroups(Name.Namespace, Punctuation, Name.Class,
                      Punctuation, Name.Function)),
            (r'\[,\]', Literal),                             # Empty list
            (s(r'($type)(\[,\])'),                           # Typed empty list
             bygroups(using(this, state='inType'), Literal)),
            (r'\[:\]', Literal),                             # Empty Map
            (s(r'($type)(\[:\])'),
             bygroups(using(this, state='inType'), Literal)),
        ],
        'insideStr': [
            (r'\\\\', String.Escape),                        # Escaped backslash
            (r'\\"', String.Escape),                         # Escaped "
            (r'\\`', String.Escape),                         # Escaped `
            (r'\$\w+', String.Interpol),                     # Subst var
            (r'\$\{.*?\}', String.Interpol),                 # Subst expr
            (r'"', Punctuation, '#pop'),                     # Closing quot
            (r'.', String)                                   # String content
        ],
        'insideUri': [  # TODO: remove copy/paste str/uri
            (r'\\\\', String.Escape),                        # Escaped backslash
            (r'\\"', String.Escape),                         # Escaped "
            (r'\\`', String.Escape),                         # Escaped `
            (r'\$\w+', String.Interpol),                     # Subst var
            (r'\$\{.*?\}', String.Interpol),                 # Subst expr
            (r'`', Punctuation, '#pop'),                     # Closing tick
            (r'.', String.Backtick)                          # URI content
        ],
        'protectionKeywords': [
            (r'\b(public|protected|private|internal)\b', Keyword),
        ],
        'typeKeywords': [
            (r'\b(abstract|final|const|native|facet|enum)\b', Keyword),
        ],
        'methodKeywords': [
            (r'\b(abstract|native|once|override|static|virtual|final)\b',
             Keyword),
        ],
        'fieldKeywords': [
            (r'\b(abstract|const|final|native|override|static|virtual|'
             r'readonly)\b', Keyword)
        ],
        'otherKeywords': [
            (words((
                'try', 'catch', 'throw', 'finally', 'for', 'if', 'else', 'while',
                'as', 'is', 'isnot', 'switch', 'case', 'default', 'continue',
                'break', 'do', 'return', 'get', 'set'), prefix=r'\b', suffix=r'\b'),
             Keyword),
            (r'\b(it|this|super)\b', Name.Builtin.Pseudo),
        ],
        'operators': [
            (r'\+\+|\-\-|\+|\-|\*|/|\|\||&&|<=>|<=|<|>=|>|=|!|\[|\]', Operator)
        ],
        'inType': [
            (r'[\[\]|\->:?]', Punctuation),
            (s(r'$id'), Name.Class),
            default('#pop'),

        ],
        'root': [
            include('comments'),
            include('protectionKeywords'),
            include('typeKeywords'),
            include('methodKeywords'),
            include('fieldKeywords'),
            include('literals'),
            include('otherKeywords'),
            include('operators'),
            (r'using\b', Keyword.Namespace, 'using'),         # Using stmt
            (r'@\w+', Name.Decorator, 'facet'),               # Symbol
            (r'(class|mixin)(\s+)(\w+)', bygroups(Keyword, Whitespace, Name.Class),
             'inheritance'),                                  # Inheritance list

            # Type var := val
            (s(r'($type)([ \t]+)($id)(\s*)(:=)'),
             bygroups(using(this, state='inType'), Whitespace,
                      Name.Variable, Whitespace, Operator)),

            # var := val
            (s(r'($id)(\s*)(:=)'),
             bygroups(Name.Variable, Whitespace, Operator)),

            # .someId( or ->someId( ###
            (s(r'(\.|(?:\->))($id)(\s*)(\()'),
             bygroups(Operator, Name.Function, Whitespace, Punctuation),
             'insideParen'),

            # .someId  or ->someId
            (s(r'(\.|(?:\->))($id)'),
             bygroups(Operator, Name.Function)),

            # new makeXXX (
            (r'(new)(\s+)(make\w*)(\s*)(\()',
             bygroups(Keyword, Whitespace, Name.Function, Whitespace, Punctuation),
             'insideMethodDeclArgs'),

            # Type name (
            (s(r'($type)([ \t]+)'  # Return type and whitespace
               r'($id)(\s*)(\()'),  # method name + open brace
             bygroups(using(this, state='inType'), Whitespace,
                      Name.Function, Whitespace, Punctuation),
             'insideMethodDeclArgs'),

            # ArgType argName,
            (s(r'($type)(\s+)($id)(\s*)(,)'),
             bygroups(using(this, state='inType'), Whitespace, Name.Variable,
                      Whitespace, Punctuation)),

            # ArgType argName)
            # Covered in 'insideParen' state

            # ArgType argName -> ArgType|
            (s(r'($type)(\s+)($id)(\s*)(\->)(\s*)($type)(\|)'),
             bygroups(using(this, state='inType'), Whitespace, Name.Variable,
                      Whitespace, Punctuation, Whitespace, using(this, state='inType'),
                      Punctuation)),

            # ArgType argName|
            (s(r'($type)(\s+)($id)(\s*)(\|)'),
             bygroups(using(this, state='inType'), Whitespace, Name.Variable,
                      Whitespace, Punctuation)),

            # Type var
            (s(r'($type)([ \t]+)($id)'),
             bygroups(using(this, state='inType'), Whitespace,
                      Name.Variable)),

            (r'\(', Punctuation, 'insideParen'),
            (r'\{', Punctuation, 'insideBrace'),
            (r'\s+', Whitespace),
            (r'.', Text)
        ],
        'insideParen': [
            (r'\)', Punctuation, '#pop'),
            include('root'),
        ],
        'insideMethodDeclArgs': [
            (r'\)', Punctuation, '#pop'),
            (s(r'($type)(\s+)($id)(\s*)(\))'),
             bygroups(using(this, state='inType'), Whitespace, Name.Variable,
                      Whitespace, Punctuation), '#pop'),
            include('root'),
        ],
        'insideBrace': [
            (r'\}', Punctuation, '#pop'),
            include('root'),
        ],
        'inheritance': [
            (r'\s+', Whitespace),                                      # Whitespace
            (r':|,', Punctuation),
            (r'(?:(\w+)(::))?(\w+)',
             bygroups(Name.Namespace, Punctuation, Name.Class)),
            (r'\{', Punctuation, '#pop')
        ],
        'using': [
            (r'[ \t]+', Whitespace),  # consume whitespaces
            (r'(\[)(\w+)(\])',
             bygroups(Punctuation, Comment.Special, Punctuation)),  # ffi
            (r'(\")?([\w.]+)(\")?',
             bygroups(Punctuation, Name.Namespace, Punctuation)),  # podname
            (r'::', Punctuation, 'usingClass'),
            default('#pop')
        ],
        'usingClass': [
            (r'[ \t]+', Whitespace),  # consume whitespaces
            (r'(as)(\s+)(\w+)',
             bygroups(Keyword.Declaration, Whitespace, Name.Class), '#pop:2'),
            (r'[\w$]+', Name.Class),
            default('#pop:2')  # jump out to root state
        ],
        'facet': [
            (r'\s+', Whitespace),
            (r'\{', Punctuation, 'facetFields'),
            default('#pop')
        ],
        'facetFields': [
            include('comments'),
            include('literals'),
            include('operators'),
            (r'\s+', Whitespace),
            (r'(\s*)(\w+)(\s*)(=)', bygroups(Whitespace, Name, Whitespace, Operator)),
            (r'\}', Punctuation, '#pop'),
            (r'\s+', Whitespace),
            (r'.', Text)
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\prql.py ===
"""
    pygments.lexers.prql
    ~~~~~~~~~~~~~~~~~~~~

    Lexer for the PRQL query language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, combined, words, include, bygroups
from pygments.token import Comment, Literal, Keyword, Name, Number, Operator, \
    Punctuation, String, Text, Whitespace

__all__ = ['PrqlLexer']


class PrqlLexer(RegexLexer):
    """
    For PRQL source code.

    grammar: https://github.com/PRQL/prql/tree/main/grammars
    """

    name = 'PRQL'
    url = 'https://prql-lang.org/'
    aliases = ['prql']
    filenames = ['*.prql']
    mimetypes = ['application/prql', 'application/x-prql']
    version_added = '2.17'

    builtinTypes = words((
        "bool",
        "int",
        "int8", "int16", "int32", "int64", "int128",
        "float",
        "text",
        "set"), suffix=r'\b')

    def innerstring_rules(ttype):
        return [
            # the new style '{}'.format(...) string formatting
            (r'\{'
             r'((\w+)((\.\w+)|(\[[^\]]+\]))*)?'  # field name
             r'(\:(.?[<>=\^])?[-+ ]?#?0?(\d+)?,?(\.\d+)?[E-GXb-gnosx%]?)?'
             r'\}', String.Interpol),

            (r'[^\\\'"%{\n]+', ttype),
            (r'[\'"\\]', ttype),
            (r'%|(\{{1,2})', ttype)
        ]

    def fstring_rules(ttype):
        return [
            (r'\}', String.Interpol),
            (r'\{', String.Interpol, 'expr-inside-fstring'),
            (r'[^\\\'"{}\n]+', ttype),
            (r'[\'"\\]', ttype),
        ]

    tokens = {
        'root': [

            # Comments
            (r'#!.*', String.Doc),
            (r'#.*', Comment.Single),

            # Whitespace
            (r'\s+', Whitespace),

            # Modules
            (r'^(\s*)(module)(\s*)',
             bygroups(Whitespace, Keyword.Namespace, Whitespace),
             'imports'),

            (builtinTypes, Keyword.Type),

            # Main
            (r'^prql ', Keyword.Reserved),

            ('let', Keyword.Declaration),

            include('keywords'),
            include('expr'),

            # Transforms
            (r'^[A-Za-z_][a-zA-Z0-9_]*', Keyword),
        ],
        'expr': [
            # non-raw f-strings
            ('(f)(""")', bygroups(String.Affix, String.Double),
             combined('fstringescape', 'tdqf')),
            ("(f)(''')", bygroups(String.Affix, String.Single),
             combined('fstringescape', 'tsqf')),
            ('(f)(")', bygroups(String.Affix, String.Double),
             combined('fstringescape', 'dqf')),
            ("(f)(')", bygroups(String.Affix, String.Single),
             combined('fstringescape', 'sqf')),

            # non-raw s-strings
            ('(s)(""")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'tdqf')),
            ("(s)(''')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'tsqf')),
            ('(s)(")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'dqf')),
            ("(s)(')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'sqf')),

            # raw strings
            ('(?i)(r)(""")',
             bygroups(String.Affix, String.Double), 'tdqs'),
            ("(?i)(r)(''')",
             bygroups(String.Affix, String.Single), 'tsqs'),
            ('(?i)(r)(")',
             bygroups(String.Affix, String.Double), 'dqs'),
            ("(?i)(r)(')",
             bygroups(String.Affix, String.Single), 'sqs'),

            # non-raw strings
            ('"""', String.Double, combined('stringescape', 'tdqs')),
            ("'''", String.Single, combined('stringescape', 'tsqs')),
            ('"', String.Double, combined('stringescape', 'dqs')),
            ("'", String.Single, combined('stringescape', 'sqs')),

            # Time and dates
            (r'@\d{4}-\d{2}-\d{2}T\d{2}(:\d{2})?(:\d{2})?(\.\d{1,6})?(Z|[+-]\d{1,2}(:\d{1,2})?)?', Literal.Date),
            (r'@\d{4}-\d{2}-\d{2}', Literal.Date),
            (r'@\d{2}(:\d{2})?(:\d{2})?(\.\d{1,6})?(Z|[+-]\d{1,2}(:\d{1,2})?)?', Literal.Date),

            (r'[^\S\n]+', Text),
            include('numbers'),
            (r'->|=>|==|!=|>=|<=|~=|&&|\|\||\?\?|\/\/', Operator),
            (r'[-~+/*%=<>&^|.@]', Operator),
            (r'[]{}:(),;[]', Punctuation),
            include('functions'),

            # Variable Names
            (r'[A-Za-z_][a-zA-Z0-9_]*', Name.Variable),
        ],
        'numbers': [
            (r'(\d(?:_?\d)*\.(?:\d(?:_?\d)*)?|(?:\d(?:_?\d)*)?\.\d(?:_?\d)*)'
             r'([eE][+-]?\d(?:_?\d)*)?', Number.Float),
            (r'\d(?:_?\d)*[eE][+-]?\d(?:_?\d)*j?', Number.Float),
            (r'0[oO](?:_?[0-7])+', Number.Oct),
            (r'0[bB](?:_?[01])+', Number.Bin),
            (r'0[xX](?:_?[a-fA-F0-9])+', Number.Hex),
            (r'\d(?:_?\d)*', Number.Integer),
        ],
        'fstringescape': [
            include('stringescape'),
        ],
        'bytesescape': [
            (r'\\([\\bfnrt"\']|\n|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'stringescape': [
            (r'\\(N\{.*?\}|u\{[a-fA-F0-9]{1,6}\})', String.Escape),
            include('bytesescape')
        ],
        'fstrings-single': fstring_rules(String.Single),
        'fstrings-double': fstring_rules(String.Double),
        'strings-single': innerstring_rules(String.Single),
        'strings-double': innerstring_rules(String.Double),
        'dqf': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('fstrings-double')
        ],
        'sqf': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('fstrings-single')
        ],
        'dqs': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('strings-double')
        ],
        'sqs': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('strings-single')
        ],
        'tdqf': [
            (r'"""', String.Double, '#pop'),
            include('fstrings-double'),
            (r'\n', String.Double)
        ],
        'tsqf': [
            (r"'''", String.Single, '#pop'),
            include('fstrings-single'),
            (r'\n', String.Single)
        ],
        'tdqs': [
            (r'"""', String.Double, '#pop'),
            include('strings-double'),
            (r'\n', String.Double)
        ],
        'tsqs': [
            (r"'''", String.Single, '#pop'),
            include('strings-single'),
            (r'\n', String.Single)
        ],

        'expr-inside-fstring': [
            (r'[{([]', Punctuation, 'expr-inside-fstring-inner'),
            # without format specifier
            (r'(=\s*)?'         # debug (https://bugs.python.org/issue36817)
             r'\}', String.Interpol, '#pop'),
            # with format specifier
            # we'll catch the remaining '}' in the outer scope
            (r'(=\s*)?'         # debug (https://bugs.python.org/issue36817)
             r':', String.Interpol, '#pop'),
            (r'\s+', Whitespace),  # allow new lines
            include('expr'),
        ],
        'expr-inside-fstring-inner': [
            (r'[{([]', Punctuation, 'expr-inside-fstring-inner'),
            (r'[])}]', Punctuation, '#pop'),
            (r'\s+', Whitespace),  # allow new lines
            include('expr'),
        ],
        'keywords': [
            (words((
                'into', 'case', 'type', 'module', 'internal',
            ), suffix=r'\b'),
                Keyword),
            (words(('true', 'false', 'null'), suffix=r'\b'), Keyword.Constant),
        ],
        'functions': [
            (words((
                "min", "max", "sum", "average", "stddev", "every", "any",
                "concat_array", "count", "lag", "lead", "first", "last",
                "rank", "rank_dense", "row_number", "round", "as", "in",
                "tuple_every", "tuple_map", "tuple_zip", "_eq", "_is_null",
                "from_text", "lower", "upper", "read_parquet", "read_csv"),
                suffix=r'\b'),
             Name.Function),
        ],

        'comment': [
            (r'-(?!\})', Comment.Multiline),
            (r'\{-', Comment.Multiline, 'comment'),
            (r'[^-}]', Comment.Multiline),
            (r'-\}', Comment.Multiline, '#pop'),
        ],

        'imports': [
            (r'\w+(\.\w+)*', Name.Class, '#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\h11\_readers.py ===
# Code to read HTTP data
#
# Strategy: each reader is a callable which takes a ReceiveBuffer object, and
# either:
# 1) consumes some of it and returns an Event
# 2) raises a LocalProtocolError (for consistency -- e.g. we call validate()
#    and it might raise a LocalProtocolError, so simpler just to always use
#    this)
# 3) returns None, meaning "I need more data"
#
# If they have a .read_eof attribute, then this will be called if an EOF is
# received -- but this is optional. Either way, the actual ConnectionClosed
# event will be generated afterwards.
#
# READERS is a dict describing how to pick a reader. It maps states to either:
# - a reader
# - or, for body readers, a dict of per-framing reader factories

import re
from typing import Any, Callable, Dict, Iterable, NoReturn, Optional, Tuple, Type, Union

from ._abnf import chunk_header, header_field, request_line, status_line
from ._events import Data, EndOfMessage, InformationalResponse, Request, Response
from ._receivebuffer import ReceiveBuffer
from ._state import (
    CLIENT,
    CLOSED,
    DONE,
    IDLE,
    MUST_CLOSE,
    SEND_BODY,
    SEND_RESPONSE,
    SERVER,
)
from ._util import LocalProtocolError, RemoteProtocolError, Sentinel, validate

__all__ = ["READERS"]

header_field_re = re.compile(header_field.encode("ascii"))
obs_fold_re = re.compile(rb"[ \t]+")


def _obsolete_line_fold(lines: Iterable[bytes]) -> Iterable[bytes]:
    it = iter(lines)
    last: Optional[bytes] = None
    for line in it:
        match = obs_fold_re.match(line)
        if match:
            if last is None:
                raise LocalProtocolError("continuation line at start of headers")
            if not isinstance(last, bytearray):
                # Cast to a mutable type, avoiding copy on append to ensure O(n) time
                last = bytearray(last)
            last += b" "
            last += line[match.end() :]
        else:
            if last is not None:
                yield last
            last = line
    if last is not None:
        yield last


def _decode_header_lines(
    lines: Iterable[bytes],
) -> Iterable[Tuple[bytes, bytes]]:
    for line in _obsolete_line_fold(lines):
        matches = validate(header_field_re, line, "illegal header line: {!r}", line)
        yield (matches["field_name"], matches["field_value"])


request_line_re = re.compile(request_line.encode("ascii"))


def maybe_read_from_IDLE_client(buf: ReceiveBuffer) -> Optional[Request]:
    lines = buf.maybe_extract_lines()
    if lines is None:
        if buf.is_next_line_obviously_invalid_request_line():
            raise LocalProtocolError("illegal request line")
        return None
    if not lines:
        raise LocalProtocolError("no request line received")
    matches = validate(
        request_line_re, lines[0], "illegal request line: {!r}", lines[0]
    )
    return Request(
        headers=list(_decode_header_lines(lines[1:])), _parsed=True, **matches
    )


status_line_re = re.compile(status_line.encode("ascii"))


def maybe_read_from_SEND_RESPONSE_server(
    buf: ReceiveBuffer,
) -> Union[InformationalResponse, Response, None]:
    lines = buf.maybe_extract_lines()
    if lines is None:
        if buf.is_next_line_obviously_invalid_request_line():
            raise LocalProtocolError("illegal request line")
        return None
    if not lines:
        raise LocalProtocolError("no response line received")
    matches = validate(status_line_re, lines[0], "illegal status line: {!r}", lines[0])
    http_version = (
        b"1.1" if matches["http_version"] is None else matches["http_version"]
    )
    reason = b"" if matches["reason"] is None else matches["reason"]
    status_code = int(matches["status_code"])
    class_: Union[Type[InformationalResponse], Type[Response]] = (
        InformationalResponse if status_code < 200 else Response
    )
    return class_(
        headers=list(_decode_header_lines(lines[1:])),
        _parsed=True,
        status_code=status_code,
        reason=reason,
        http_version=http_version,
    )


class ContentLengthReader:
    def __init__(self, length: int) -> None:
        self._length = length
        self._remaining = length

    def __call__(self, buf: ReceiveBuffer) -> Union[Data, EndOfMessage, None]:
        if self._remaining == 0:
            return EndOfMessage()
        data = buf.maybe_extract_at_most(self._remaining)
        if data is None:
            return None
        self._remaining -= len(data)
        return Data(data=data)

    def read_eof(self) -> NoReturn:
        raise RemoteProtocolError(
            "peer closed connection without sending complete message body "
            "(received {} bytes, expected {})".format(
                self._length - self._remaining, self._length
            )
        )


chunk_header_re = re.compile(chunk_header.encode("ascii"))


class ChunkedReader:
    def __init__(self) -> None:
        self._bytes_in_chunk = 0
        # After reading a chunk, we have to throw away the trailing \r\n.
        # This tracks the bytes that we need to match and throw away.
        self._bytes_to_discard = b""
        self._reading_trailer = False

    def __call__(self, buf: ReceiveBuffer) -> Union[Data, EndOfMessage, None]:
        if self._reading_trailer:
            lines = buf.maybe_extract_lines()
            if lines is None:
                return None
            return EndOfMessage(headers=list(_decode_header_lines(lines)))
        if self._bytes_to_discard:
            data = buf.maybe_extract_at_most(len(self._bytes_to_discard))
            if data is None:
                return None
            if data != self._bytes_to_discard[: len(data)]:
                raise LocalProtocolError(
                    f"malformed chunk footer: {data!r} (expected {self._bytes_to_discard!r})"
                )
            self._bytes_to_discard = self._bytes_to_discard[len(data) :]
            if self._bytes_to_discard:
                return None
            # else, fall through and read some more
        assert self._bytes_to_discard == b""
        if self._bytes_in_chunk == 0:
            # We need to refill our chunk count
            chunk_header = buf.maybe_extract_next_line()
            if chunk_header is None:
                return None
            matches = validate(
                chunk_header_re,
                chunk_header,
                "illegal chunk header: {!r}",
                chunk_header,
            )
            # XX FIXME: we discard chunk extensions. Does anyone care?
            self._bytes_in_chunk = int(matches["chunk_size"], base=16)
            if self._bytes_in_chunk == 0:
                self._reading_trailer = True
                return self(buf)
            chunk_start = True
        else:
            chunk_start = False
        assert self._bytes_in_chunk > 0
        data = buf.maybe_extract_at_most(self._bytes_in_chunk)
        if data is None:
            return None
        self._bytes_in_chunk -= len(data)
        if self._bytes_in_chunk == 0:
            self._bytes_to_discard = b"\r\n"
            chunk_end = True
        else:
            chunk_end = False
        return Data(data=data, chunk_start=chunk_start, chunk_end=chunk_end)

    def read_eof(self) -> NoReturn:
        raise RemoteProtocolError(
            "peer closed connection without sending complete message body "
            "(incomplete chunked read)"
        )


class Http10Reader:
    def __call__(self, buf: ReceiveBuffer) -> Optional[Data]:
        data = buf.maybe_extract_at_most(999999999)
        if data is None:
            return None
        return Data(data=data)

    def read_eof(self) -> EndOfMessage:
        return EndOfMessage()


def expect_nothing(buf: ReceiveBuffer) -> None:
    if buf:
        raise LocalProtocolError("Got data when expecting EOF")
    return None


ReadersType = Dict[
    Union[Type[Sentinel], Tuple[Type[Sentinel], Type[Sentinel]]],
    Union[Callable[..., Any], Dict[str, Callable[..., Any]]],
]

READERS: ReadersType = {
    (CLIENT, IDLE): maybe_read_from_IDLE_client,
    (SERVER, IDLE): maybe_read_from_SEND_RESPONSE_server,
    (SERVER, SEND_RESPONSE): maybe_read_from_SEND_RESPONSE_server,
    (CLIENT, DONE): expect_nothing,
    (CLIENT, MUST_CLOSE): expect_nothing,
    (CLIENT, CLOSED): expect_nothing,
    (SERVER, DONE): expect_nothing,
    (SERVER, MUST_CLOSE): expect_nothing,
    (SERVER, CLOSED): expect_nothing,
    SEND_BODY: {
        "chunked": ChunkedReader,
        "content-length": ContentLengthReader,
        "http/1.0": Http10Reader,
    },
}

# === NexusCore/openenv\Lib\site-packages\joblib\numpy_pickle_compat.py ===
"""Numpy pickle compatibility functions."""

import inspect
import os
import pickle
import zlib
from io import BytesIO

from .numpy_pickle_utils import (
    _ZFILE_PREFIX,
    Unpickler,
    _ensure_native_byte_order,
    _reconstruct,
)


def hex_str(an_int):
    """Convert an int to an hexadecimal string."""
    return "{:#x}".format(an_int)


def asbytes(s):
    if isinstance(s, bytes):
        return s
    return s.encode("latin1")


_MAX_LEN = len(hex_str(2**64))
_CHUNK_SIZE = 64 * 1024


def read_zfile(file_handle):
    """Read the z-file and return the content as a string.

    Z-files are raw data compressed with zlib used internally by joblib
    for persistence. Backward compatibility is not guaranteed. Do not
    use for external purposes.
    """
    file_handle.seek(0)
    header_length = len(_ZFILE_PREFIX) + _MAX_LEN
    length = file_handle.read(header_length)
    length = length[len(_ZFILE_PREFIX) :]
    length = int(length, 16)

    # With python2 and joblib version <= 0.8.4 compressed pickle header is one
    # character wider so we need to ignore an additional space if present.
    # Note: the first byte of the zlib data is guaranteed not to be a
    # space according to
    # https://tools.ietf.org/html/rfc6713#section-2.1
    next_byte = file_handle.read(1)
    if next_byte != b" ":
        # The zlib compressed data has started and we need to go back
        # one byte
        file_handle.seek(header_length)

    # We use the known length of the data to tell Zlib the size of the
    # buffer to allocate.
    data = zlib.decompress(file_handle.read(), 15, length)
    assert len(data) == length, (
        "Incorrect data length while decompressing %s."
        "The file could be corrupted." % file_handle
    )
    return data


def write_zfile(file_handle, data, compress=1):
    """Write the data in the given file as a Z-file.

    Z-files are raw data compressed with zlib used internally by joblib
    for persistence. Backward compatibility is not guaranteed. Do not
    use for external purposes.
    """
    file_handle.write(_ZFILE_PREFIX)
    length = hex_str(len(data))
    # Store the length of the data
    file_handle.write(asbytes(length.ljust(_MAX_LEN)))
    file_handle.write(zlib.compress(asbytes(data), compress))


###############################################################################
# Utility objects for persistence.


class NDArrayWrapper(object):
    """An object to be persisted instead of numpy arrays.

    The only thing this object does, is to carry the filename in which
    the array has been persisted, and the array subclass.
    """

    def __init__(self, filename, subclass, allow_mmap=True):
        """Constructor. Store the useful information for later."""
        self.filename = filename
        self.subclass = subclass
        self.allow_mmap = allow_mmap

    def read(self, unpickler):
        """Reconstruct the array."""
        filename = os.path.join(unpickler._dirname, self.filename)
        # Load the array from the disk
        # use getattr instead of self.allow_mmap to ensure backward compat
        # with NDArrayWrapper instances pickled with joblib < 0.9.0
        allow_mmap = getattr(self, "allow_mmap", True)
        kwargs = {}
        if allow_mmap:
            kwargs["mmap_mode"] = unpickler.mmap_mode
        if "allow_pickle" in inspect.signature(unpickler.np.load).parameters:
            # Required in numpy 1.16.3 and later to acknowledge the security
            # risk.
            kwargs["allow_pickle"] = True
        array = unpickler.np.load(filename, **kwargs)

        # Detect byte order mismatch and swap as needed.
        array = _ensure_native_byte_order(array)

        # Reconstruct subclasses. This does not work with old
        # versions of numpy
        if hasattr(array, "__array_prepare__") and self.subclass not in (
            unpickler.np.ndarray,
            unpickler.np.memmap,
        ):
            # We need to reconstruct another subclass
            new_array = _reconstruct(self.subclass, (0,), "b")
            return new_array.__array_prepare__(array)
        else:
            return array


class ZNDArrayWrapper(NDArrayWrapper):
    """An object to be persisted instead of numpy arrays.

    This object store the Zfile filename in which
    the data array has been persisted, and the meta information to
    retrieve it.
    The reason that we store the raw buffer data of the array and
    the meta information, rather than array representation routine
    (tobytes) is that it enables us to use completely the strided
    model to avoid memory copies (a and a.T store as fast). In
    addition saving the heavy information separately can avoid
    creating large temporary buffers when unpickling data with
    large arrays.
    """

    def __init__(self, filename, init_args, state):
        """Constructor. Store the useful information for later."""
        self.filename = filename
        self.state = state
        self.init_args = init_args

    def read(self, unpickler):
        """Reconstruct the array from the meta-information and the z-file."""
        # Here we a simply reproducing the unpickling mechanism for numpy
        # arrays
        filename = os.path.join(unpickler._dirname, self.filename)
        array = _reconstruct(*self.init_args)
        with open(filename, "rb") as f:
            data = read_zfile(f)
        state = self.state + (data,)
        array.__setstate__(state)
        return array


class ZipNumpyUnpickler(Unpickler):
    """A subclass of the Unpickler to unpickle our numpy pickles."""

    dispatch = Unpickler.dispatch.copy()

    def __init__(self, filename, file_handle, mmap_mode=None):
        """Constructor."""
        self._filename = os.path.basename(filename)
        self._dirname = os.path.dirname(filename)
        self.mmap_mode = mmap_mode
        self.file_handle = self._open_pickle(file_handle)
        Unpickler.__init__(self, self.file_handle)
        try:
            import numpy as np
        except ImportError:
            np = None
        self.np = np

    def _open_pickle(self, file_handle):
        return BytesIO(read_zfile(file_handle))

    def load_build(self):
        """Set the state of a newly created object.

        We capture it to replace our place-holder objects,
        NDArrayWrapper, by the array we are interested in. We
        replace them directly in the stack of pickler.
        """
        Unpickler.load_build(self)
        if isinstance(self.stack[-1], NDArrayWrapper):
            if self.np is None:
                raise ImportError(
                    "Trying to unpickle an ndarray, but numpy didn't import correctly"
                )
            nd_array_wrapper = self.stack.pop()
            array = nd_array_wrapper.read(self)
            self.stack.append(array)

    dispatch[pickle.BUILD[0]] = load_build


def load_compatibility(filename):
    """Reconstruct a Python object from a file persisted with joblib.dump.

    This function ensures the compatibility with joblib old persistence format
    (<= 0.9.3).

    Parameters
    ----------
    filename: string
        The name of the file from which to load the object

    Returns
    -------
    result: any Python object
        The object stored in the file.

    See Also
    --------
    joblib.dump : function to save an object

    Notes
    -----

    This function can load numpy array files saved separately during the
    dump.
    """
    with open(filename, "rb") as file_handle:
        # We are careful to open the file handle early and keep it open to
        # avoid race-conditions on renames. That said, if data is stored in
        # companion files, moving the directory will create a race when
        # joblib tries to access the companion files.
        unpickler = ZipNumpyUnpickler(filename, file_handle=file_handle)
        try:
            obj = unpickler.load()
        except UnicodeDecodeError as exc:
            # More user-friendly error message
            new_exc = ValueError(
                "You may be trying to read with "
                "python 3 a joblib pickle generated with python 2. "
                "This feature is not supported by joblib."
            )
            new_exc.__cause__ = exc
            raise new_exc
        finally:
            if hasattr(unpickler, "file_handle"):
                unpickler.file_handle.close()
        return obj

# === NexusCore/openenv\Lib\site-packages\debugpy\launcher\debuggee.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

import atexit
import ctypes
import os
import signal
import struct
import subprocess
import sys
import threading

from debugpy import launcher
from debugpy.common import log, messaging
from debugpy.launcher import output

if sys.platform == "win32":
    from debugpy.launcher import winapi


process = None
"""subprocess.Popen instance for the debuggee process."""

job_handle = None
"""On Windows, the handle for the job object to which the debuggee is assigned."""

wait_on_exit_predicates = []
"""List of functions that determine whether to pause after debuggee process exits.

Every function is invoked with exit code as the argument. If any of the functions
returns True, the launcher pauses and waits for user input before exiting.
"""


def describe():
    return f"Debuggee[PID={process.pid}]"


def spawn(process_name, cmdline, env, redirect_output):
    log.info(
        "Spawning debuggee process:\n\n"
        "Command line: {0!r}\n\n"
        "Environment variables: {1!r}\n\n",
        cmdline,
        env,
    )

    close_fds = set()
    try:
        if redirect_output:
            # subprocess.PIPE behavior can vary substantially depending on Python version
            # and platform; using our own pipes keeps it simple, predictable, and fast.
            stdout_r, stdout_w = os.pipe()
            stderr_r, stderr_w = os.pipe()
            close_fds |= {stdout_r, stdout_w, stderr_r, stderr_w}
            kwargs = dict(stdout=stdout_w, stderr=stderr_w)
        else:
            kwargs = {}

        if sys.platform != "win32" and sys.implementation.name != 'graalpy':
            # GraalPy does not support running code between fork and exec

            def preexec_fn():
                try:
                    # Start the debuggee in a new process group, so that the launcher can
                    # kill the entire process tree later.
                    os.setpgrp()

                    # Make the new process group the foreground group in its session, so
                    # that it can interact with the terminal. The debuggee will receive
                    # SIGTTOU when tcsetpgrp() is called, and must ignore it.
                    old_handler = signal.signal(signal.SIGTTOU, signal.SIG_IGN)
                    try:
                        tty = os.open("/dev/tty", os.O_RDWR)
                        try:
                            os.tcsetpgrp(tty, os.getpgrp())
                        finally:
                            os.close(tty)
                    finally:
                        signal.signal(signal.SIGTTOU, old_handler)
                except Exception:
                    # Not an error - /dev/tty doesn't work when there's no terminal.
                    log.swallow_exception(
                        "Failed to set up process group", level="info"
                    )

            kwargs.update(preexec_fn=preexec_fn)

        try:
            global process
            process = subprocess.Popen(cmdline, env=env, bufsize=0, **kwargs)
        except Exception as exc:
            raise messaging.MessageHandlingError(
                "Couldn't spawn debuggee: {0}\n\nCommand line:{1!r}".format(
                    exc, cmdline
                )
            )

        log.info("Spawned {0}.", describe())

        if sys.platform == "win32":
            # Assign the debuggee to a new job object, so that the launcher can kill
            # the entire process tree later.
            try:
                global job_handle
                job_handle = winapi.kernel32.CreateJobObjectA(None, None)

                job_info = winapi.JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
                job_info_size = winapi.DWORD(ctypes.sizeof(job_info))
                winapi.kernel32.QueryInformationJobObject(
                    job_handle,
                    winapi.JobObjectExtendedLimitInformation,
                    ctypes.pointer(job_info),
                    job_info_size,
                    ctypes.pointer(job_info_size),
                )

                job_info.BasicLimitInformation.LimitFlags |= (
                    # Ensure that the job will be terminated by the OS once the
                    # launcher exits, even if it doesn't terminate the job explicitly.
                    winapi.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                    |
                    # Allow the debuggee to create its own jobs unrelated to ours.
                    winapi.JOB_OBJECT_LIMIT_BREAKAWAY_OK
                )
                winapi.kernel32.SetInformationJobObject(
                    job_handle,
                    winapi.JobObjectExtendedLimitInformation,
                    ctypes.pointer(job_info),
                    job_info_size,
                )

                process_handle = winapi.kernel32.OpenProcess(
                    winapi.PROCESS_TERMINATE | winapi.PROCESS_SET_QUOTA,
                    False,
                    process.pid,
                )

                winapi.kernel32.AssignProcessToJobObject(job_handle, process_handle)

            except Exception:
                log.swallow_exception("Failed to set up job object", level="warning")

        atexit.register(kill)

        launcher.channel.send_event(
            "process",
            {
                "startMethod": "launch",
                "isLocalProcess": True,
                "systemProcessId": process.pid,
                "name": process_name,
                "pointerSize": struct.calcsize("P") * 8,
            },
        )

        if redirect_output:
            for category, fd, tee in [
                ("stdout", stdout_r, sys.stdout),
                ("stderr", stderr_r, sys.stderr),
            ]:
                output.CaptureOutput(describe(), category, fd, tee)
                close_fds.remove(fd)

        wait_thread = threading.Thread(target=wait_for_exit, name="wait_for_exit()")
        wait_thread.daemon = True
        wait_thread.start()

    finally:
        for fd in close_fds:
            try:
                os.close(fd)
            except Exception:
                log.swallow_exception(level="warning")


def kill():
    if process is None:
        return

    try:
        if process.poll() is None:
            log.info("Killing {0}", describe())
            # Clean up the process tree
            if sys.platform == "win32":
                # On Windows, kill the job object.
                winapi.kernel32.TerminateJobObject(job_handle, 0)
            else:
                # On POSIX, kill the debuggee's process group.
                os.killpg(process.pid, signal.SIGKILL)
    except Exception:
        log.swallow_exception("Failed to kill {0}", describe())


def wait_for_exit():
    try:
        code = process.wait()
        if sys.platform != "win32" and code < 0:
            # On POSIX, if the process was terminated by a signal, Popen will use
            # a negative returncode to indicate that - but the actual exit code of
            # the process is always an unsigned number, and can be determined by
            # taking the lowest 8 bits of that negative returncode.
            code &= 0xFF
    except Exception:
        log.swallow_exception("Couldn't determine process exit code")
        code = -1

    log.info("{0} exited with code {1}", describe(), code)
    output.wait_for_remaining_output()

    # Determine whether we should wait or not before sending "exited", so that any
    # follow-up "terminate" requests don't affect the predicates.
    should_wait = any(pred(code) for pred in wait_on_exit_predicates)

    try:
        launcher.channel.send_event("exited", {"exitCode": code})
    except Exception:
        pass

    if should_wait:
        _wait_for_user_input()

    try:
        launcher.channel.send_event("terminated")
    except Exception:
        pass


def _wait_for_user_input():
    if sys.stdout and sys.stdin and sys.stdin.isatty():
        from debugpy.common import log

        try:
            import msvcrt
        except ImportError:
            can_getch = False
        else:
            can_getch = True

        if can_getch:
            log.debug("msvcrt available - waiting for user input via getch()")
            sys.stdout.write("Press any key to continue . . . ")
            sys.stdout.flush()
            msvcrt.getch()
        else:
            log.debug("msvcrt not available - waiting for user input via read()")
            sys.stdout.write("Press Enter to continue . . . ")
            sys.stdout.flush()
            sys.stdin.read(1)

# === NexusCore/openenv\Lib\site-packages\interpreter\terminal_interface\profiles\defaults\os.py ===
import time

from interpreter import interpreter

interpreter.os = True
interpreter.llm.supports_vision = True

interpreter.llm.model = "gpt-4o"

interpreter.computer.import_computer_api = True

interpreter.llm.supports_functions = True
interpreter.llm.context_window = 110000
interpreter.llm.max_tokens = 4096
interpreter.auto_run = True
interpreter.loop = True
interpreter.sync_computer = True

interpreter.system_message = r"""

You are Open Interpreter, a world-class programmer that can complete any goal by executing code.

When you write code, it will be executed **on the user's machine**. The user has given you **full and complete permission** to execute any code necessary to complete the task.

When a user refers to a filename, they're likely referring to an existing file in the directory you're currently executing code in.

In general, try to make plans with as few steps as possible. As for actually executing code to carry out that plan, **don't try to do everything in one code block.** You should try something, print information about it, then continue from there in tiny, informed steps. You will never get it on the first try, and attempting it in one go will often lead to errors you cant see.

Manually summarize text.

Do not try to write code that attempts the entire task at once, and verify at each step whether or not you're on track.

# Computer

You may use the `computer` Python module to complete tasks:

```python
computer.browser.search(query) # Silently searches Google for the query, returns result. The user's browser is unaffected. (does not open a browser!)
# Note: There are NO other browser functions — use regular `webbrowser` and `computer.display.view()` commands to view/control a real browser.

computer.display.view() # Shows you what's on the screen (primary display by default), returns a `pil_image` `in case you need it (rarely). To get a specific display, use the parameter screen=DISPLAY_NUMBER (0 for primary monitor 1 and above for secondary monitors). **You almost always want to do this first!**
# NOTE: YOU MUST NEVER RUN image.show() AFTER computer.display.view. IT WILL AUTOMATICALLY SHOW YOU THE IMAGE. DO NOT RUN image.show().

computer.keyboard.hotkey(" ", "command") # Opens spotlight (very useful)
computer.keyboard.write("hello")

# Use this to click text:
computer.mouse.click("text onscreen") # This clicks on the UI element with that text. Use this **frequently** and get creative! To click a video, you could pass the *timestamp* (which is usually written on the thumbnail) into this.
# Use this to click an icon, button, or other symbol:
computer.mouse.click(icon="gear icon") # Clicks the icon with that description. Use this very often.

computer.mouse.move("open recent >") # This moves the mouse over the UI element with that text. Many dropdowns will disappear if you click them. You have to hover over items to reveal more.
computer.mouse.click(x=500, y=500) # Use this very, very rarely. It's highly inaccurate

computer.mouse.scroll(-10) # Scrolls down. If you don't find some text on screen that you expected to be there, you probably want to do this
x, y = computer.display.center() # Get your bearings

computer.clipboard.view() # Returns contents of clipboard
computer.os.get_selected_text() # Use frequently. If editing text, the user often wants this

{{
import platform
if platform.system() == 'Darwin':
        print('''
computer.browser.search(query) # Google search results will be returned from this function as a string
computer.files.edit(path_to_file, original_text, replacement_text) # Edit a file
computer.calendar.create_event(title="Meeting", start_date=datetime.datetime.now(), end_date=datetime.datetime.now() + datetime.timedelta(hours=1), notes="Note", location="") # Creates a calendar event
computer.calendar.get_events(start_date=datetime.date.today(), end_date=None) # Get events between dates. If end_date is None, only gets events for start_date
computer.calendar.delete_event(event_title="Meeting", start_date=datetime.datetime) # Delete a specific event with a matching title and start date, you may need to get use get_events() to find the specific event object first
computer.contacts.get_phone_number("John Doe")
computer.contacts.get_email_address("John Doe")
computer.mail.send("john@email.com", "Meeting Reminder", "Reminder that our meeting is at 3pm today.", ["path/to/attachment.pdf", "path/to/attachment2.pdf"]) # Send an email with a optional attachments
computer.mail.get(4, unread=True) # Returns the {number} of unread emails, or all emails if False is passed
computer.mail.unread_count() # Returns the number of unread emails
computer.sms.send("555-123-4567", "Hello from the computer!") # Send a text message. MUST be a phone number, so use computer.contacts.get_phone_number frequently here
''')
}}

```

For rare and complex mouse actions, consider using computer vision libraries on the `computer.display.view()` `pil_image` to produce a list of coordinates for the mouse to move/drag to.

If the user highlighted text in an editor, then asked you to modify it, they probably want you to `keyboard.write` over their version of the text.

Tasks are 100% computer-based. DO NOT simply write long messages to the user to complete tasks. You MUST put your text back into the program they're using to deliver your text!

Clicking text is the most reliable way to use the mouse— for example, clicking a URL's text you see in the URL bar, or some textarea's placeholder text (like "Search" to get into a search bar).

Applescript might be best for some tasks.

If you use `plt.show()`, the resulting image will be sent to you. However, if you use `PIL.Image.show()`, the resulting image will NOT be sent to you.

It is very important to make sure you are focused on the right application and window. Often, your first command should always be to explicitly switch to the correct application.

When searching the web, use query parameters. For example, https://www.amazon.com/s?k=monitor

Try multiple methods before saying the task is impossible. **You can do it!**

# Critical Routine Procedure for Multi-Step Tasks

Include `computer.display.view()` after a 2 second delay at the end of _every_ code block to verify your progress, then answer these questions in extreme detail:

1. Generally, what is happening on-screen?
2. What is the active app?
3. What hotkeys does this app support that might get be closer to my goal?
4. What text areas are active, if any?
5. What text is selected?
6. What options could you take next to get closer to your goal?

{{
# Add window information

try:

    import pywinctl

    active_window = pywinctl.getActiveWindow()

    if active_window:
        app_info = ""

        if "_appName" in active_window.__dict__:
            app_info += (
                "Active Application: " + active_window.__dict__["_appName"]
            )

        if hasattr(active_window, "title"):
            app_info += "\n" + "Active Window Title: " + active_window.title
        elif "_winTitle" in active_window.__dict__:
            app_info += (
                "\n"
                + "Active Window Title:"
                + active_window.__dict__["_winTitle"]
            )

        if app_info != "":
            print(
                "\n\n# Important Information:\n"
                + app_info
                + "\n(If you need to be in another active application to help the user, you need to switch to it.)"
            )

except:
    # Non blocking
    pass
    
}}

""".strip()

# Check if required packages are installed

# THERE IS AN INCONSISTENCY HERE.
# We should be testing if they import WITHIN OI's computer, not here.

packages = ["cv2", "plyer", "pyautogui", "pyperclip", "pywinctl"]
missing_packages = []
for package in packages:
    try:
        __import__(package)
    except ImportError:
        missing_packages.append(package)

if missing_packages:
    interpreter.display_message(
        f"> **Missing Package(s): {', '.join(['`' + p + '`' for p in missing_packages])}**\n\nThese packages are required for OS Control.\n\nInstall them?\n"
    )
    user_input = input("(y/n) > ")
    if user_input.lower() != "y":
        print("\nPlease try to install them manually.\n\n")
        time.sleep(2)
        print("Attempting to start OS control anyway...\n\n")

    else:
        for pip_combo in [
            ["pip", "quotes"],
            ["pip", "no-quotes"],
            ["pip3", "quotes"],
            ["pip", "no-quotes"],
        ]:
            if pip_combo[1] == "quotes":
                command = f'{pip_combo[0]} install "open-interpreter[os]"'
            else:
                command = f"{pip_combo[0]} install open-interpreter[os]"

            interpreter.computer.run("shell", command, display=True)

            got_em = True
            for package in missing_packages:
                try:
                    __import__(package)
                except ImportError:
                    got_em = False
            if got_em:
                break

        missing_packages = []
        for package in packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)

        if missing_packages != []:
            print(
                "\n\nWarning: The following packages could not be installed:",
                ", ".join(missing_packages),
            )
            print("\nPlease try to install them manually.\n\n")
            time.sleep(2)
            print("Attempting to start OS control anyway...\n\n")

interpreter.display_message("> `OS Control` enabled")

# Should we explore other options for ^ these kinds of tags?
# Like:

# from rich import box
# from rich.console import Console
# from rich.panel import Panel
# console = Console()
# print(">\n\n")
# console.print(Panel("[bold italic white on black]OS CONTROL[/bold italic white on black] Enabled", box=box.SQUARE, expand=False), style="white on black")
# print(">\n\n")
# console.print(Panel("[bold italic white on black]OS CONTROL[/bold italic white on black] Enabled", box=box.HEAVY, expand=False), style="white on black")
# print(">\n\n")
# console.print(Panel("[bold italic white on black]OS CONTROL[/bold italic white on black] Enabled", box=box.DOUBLE, expand=False), style="white on black")
# print(">\n\n")
# console.print(Panel("[bold italic white on black]OS CONTROL[/bold italic white on black] Enabled", box=box.SQUARE, expand=False), style="white on black")

if not interpreter.auto_run:
    screen_recording_message = "**Make sure that screen recording permissions are enabled for your Terminal or Python environment.**"
    interpreter.display_message(screen_recording_message)
    print("")

# # FOR TESTING ONLY
# # Install Open Interpreter from GitHub
# for chunk in interpreter.computer.run(
#     "shell",
#     "pip install git+https://github.com/OpenInterpreter/open-interpreter.git",
# ):
#     if chunk.get("format") != "active_line":
#         print(chunk.get("content"))

interpreter.auto_run = True

interpreter.display_message(
    "**Warning:** In this mode, Open Interpreter will not require approval before performing actions. Be ready to close your terminal."
)
print("")  # < - Aesthetic choice

# === NexusCore/openenv\Lib\site-packages\numpy\testing\_private\extbuild.py ===
"""
Build a c-extension module on-the-fly in tests.
See build_and_import_extensions for usage hints

"""

import os
import pathlib
import subprocess
import sys
import sysconfig
import textwrap

__all__ = ['build_and_import_extension', 'compile_extension_module']


def build_and_import_extension(
        modname, functions, *, prologue="", build_dir=None,
        include_dirs=None, more_init=""):
    """
    Build and imports a c-extension module `modname` from a list of function
    fragments `functions`.


    Parameters
    ----------
    functions : list of fragments
        Each fragment is a sequence of func_name, calling convention, snippet.
    prologue : string
        Code to precede the rest, usually extra ``#include`` or ``#define``
        macros.
    build_dir : pathlib.Path
        Where to build the module, usually a temporary directory
    include_dirs : list
        Extra directories to find include files when compiling
    more_init : string
        Code to appear in the module PyMODINIT_FUNC

    Returns
    -------
    out: module
        The module will have been loaded and is ready for use

    Examples
    --------
    >>> functions = [("test_bytes", "METH_O", \"\"\"
        if ( !PyBytesCheck(args)) {
            Py_RETURN_FALSE;
        }
        Py_RETURN_TRUE;
    \"\"\")]
    >>> mod = build_and_import_extension("testme", functions)
    >>> assert not mod.test_bytes('abc')
    >>> assert mod.test_bytes(b'abc')
    """
    if include_dirs is None:
        include_dirs = []
    body = prologue + _make_methods(functions, modname)
    init = """
    PyObject *mod = PyModule_Create(&moduledef);
    #ifdef Py_GIL_DISABLED
    PyUnstable_Module_SetGIL(mod, Py_MOD_GIL_NOT_USED);
    #endif
           """
    if not build_dir:
        build_dir = pathlib.Path('.')
    if more_init:
        init += """#define INITERROR return NULL
                """
        init += more_init
    init += "\nreturn mod;"
    source_string = _make_source(modname, init, body)
    mod_so = compile_extension_module(
        modname, build_dir, include_dirs, source_string)
    import importlib.util
    spec = importlib.util.spec_from_file_location(modname, mod_so)
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
    return foo


def compile_extension_module(
        name, builddir, include_dirs,
        source_string, libraries=None, library_dirs=None):
    """
    Build an extension module and return the filename of the resulting
    native code file.

    Parameters
    ----------
    name : string
        name of the module, possibly including dots if it is a module inside a
        package.
    builddir : pathlib.Path
        Where to build the module, usually a temporary directory
    include_dirs : list
        Extra directories to find include files when compiling
    libraries : list
        Libraries to link into the extension module
    library_dirs: list
        Where to find the libraries, ``-L`` passed to the linker
    """
    modname = name.split('.')[-1]
    dirname = builddir / name
    dirname.mkdir(exist_ok=True)
    cfile = _convert_str_to_file(source_string, dirname)
    include_dirs = include_dirs or []
    libraries = libraries or []
    library_dirs = library_dirs or []

    return _c_compile(
        cfile, outputfilename=dirname / modname,
        include_dirs=include_dirs, libraries=libraries,
        library_dirs=library_dirs,
        )


def _convert_str_to_file(source, dirname):
    """Helper function to create a file ``source.c`` in `dirname` that contains
    the string in `source`. Returns the file name
    """
    filename = dirname / 'source.c'
    with filename.open('w') as f:
        f.write(str(source))
    return filename


def _make_methods(functions, modname):
    """ Turns the name, signature, code in functions into complete functions
    and lists them in a methods_table. Then turns the methods_table into a
    ``PyMethodDef`` structure and returns the resulting code fragment ready
    for compilation
    """
    methods_table = []
    codes = []
    for funcname, flags, code in functions:
        cfuncname = f"{modname}_{funcname}"
        if 'METH_KEYWORDS' in flags:
            signature = '(PyObject *self, PyObject *args, PyObject *kwargs)'
        else:
            signature = '(PyObject *self, PyObject *args)'
        methods_table.append(
            "{\"%s\", (PyCFunction)%s, %s}," % (funcname, cfuncname, flags))
        func_code = f"""
        static PyObject* {cfuncname}{signature}
        {{
        {code}
        }}
        """
        codes.append(func_code)

    body = "\n".join(codes) + """
    static PyMethodDef methods[] = {
    %(methods)s
    { NULL }
    };
    static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "%(modname)s",  /* m_name */
        NULL,           /* m_doc */
        -1,             /* m_size */
        methods,        /* m_methods */
    };
    """ % {'methods': '\n'.join(methods_table), 'modname': modname}
    return body


def _make_source(name, init, body):
    """ Combines the code fragments into source code ready to be compiled
    """
    code = """
    #include <Python.h>

    %(body)s

    PyMODINIT_FUNC
    PyInit_%(name)s(void) {
    %(init)s
    }
    """ % {
        'name': name, 'init': init, 'body': body,
    }
    return code


def _c_compile(cfile, outputfilename, include_dirs, libraries,
               library_dirs):
    link_extra = []
    if sys.platform == 'win32':
        compile_extra = ["/we4013"]
        link_extra.append('/DEBUG')  # generate .pdb file
    elif sys.platform.startswith('linux'):
        compile_extra = [
            "-O0", "-g", "-Werror=implicit-function-declaration", "-fPIC"]
    else:
        compile_extra = []

    return build(
        cfile, outputfilename,
        compile_extra, link_extra,
        include_dirs, libraries, library_dirs)


def build(cfile, outputfilename, compile_extra, link_extra,
          include_dirs, libraries, library_dirs):
    "use meson to build"

    build_dir = cfile.parent / "build"
    os.makedirs(build_dir, exist_ok=True)
    with open(cfile.parent / "meson.build", "wt") as fid:
        link_dirs = ['-L' + d for d in library_dirs]
        fid.write(textwrap.dedent(f"""\
            project('foo', 'c')
            py = import('python').find_installation(pure: false)
            py.extension_module(
                '{outputfilename.parts[-1]}',
                '{cfile.parts[-1]}',
                c_args: {compile_extra},
                link_args: {link_dirs},
                include_directories: {include_dirs},
            )
        """))
    native_file_name = cfile.parent / ".mesonpy-native-file.ini"
    with open(native_file_name, "wt") as fid:
        fid.write(textwrap.dedent(f"""\
            [binaries]
            python = '{sys.executable}'
        """))
    if sys.platform == "win32":
        subprocess.check_call(["meson", "setup",
                               "--buildtype=release",
                               "--vsenv", ".."],
                              cwd=build_dir,
                              )
    else:
        subprocess.check_call(["meson", "setup", "--vsenv",
                               "..", f'--native-file={os.fspath(native_file_name)}'],
                              cwd=build_dir
                              )

    so_name = outputfilename.parts[-1] + get_so_suffix()
    subprocess.check_call(["meson", "compile"], cwd=build_dir)
    os.rename(str(build_dir / so_name), cfile.parent / so_name)
    return cfile.parent / so_name


def get_so_suffix():
    ret = sysconfig.get_config_var('EXT_SUFFIX')
    assert ret
    return ret

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\input\vt100_parser.py ===
"""
Parser for VT100 input stream.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, Generator

from ..key_binding.key_processor import KeyPress
from ..keys import Keys
from .ansi_escape_sequences import ANSI_SEQUENCES

__all__ = [
    "Vt100Parser",
]


# Regex matching any CPR response
# (Note that we use '\Z' instead of '$', because '$' could include a trailing
# newline.)
_cpr_response_re = re.compile("^" + re.escape("\x1b[") + r"\d+;\d+R\Z")

# Mouse events:
# Typical: "Esc[MaB*"  Urxvt: "Esc[96;14;13M" and for Xterm SGR: "Esc[<64;85;12M"
_mouse_event_re = re.compile("^" + re.escape("\x1b[") + r"(<?[\d;]+[mM]|M...)\Z")

# Regex matching any valid prefix of a CPR response.
# (Note that it doesn't contain the last character, the 'R'. The prefix has to
# be shorter.)
_cpr_response_prefix_re = re.compile("^" + re.escape("\x1b[") + r"[\d;]*\Z")

_mouse_event_prefix_re = re.compile("^" + re.escape("\x1b[") + r"(<?[\d;]*|M.{0,2})\Z")


class _Flush:
    """Helper object to indicate flush operation to the parser."""

    pass


class _IsPrefixOfLongerMatchCache(Dict[str, bool]):
    """
    Dictionary that maps input sequences to a boolean indicating whether there is
    any key that start with this characters.
    """

    def __missing__(self, prefix: str) -> bool:
        # (hard coded) If this could be a prefix of a CPR response, return
        # True.
        if _cpr_response_prefix_re.match(prefix) or _mouse_event_prefix_re.match(
            prefix
        ):
            result = True
        else:
            # If this could be a prefix of anything else, also return True.
            result = any(
                v
                for k, v in ANSI_SEQUENCES.items()
                if k.startswith(prefix) and k != prefix
            )

        self[prefix] = result
        return result


_IS_PREFIX_OF_LONGER_MATCH_CACHE = _IsPrefixOfLongerMatchCache()


class Vt100Parser:
    """
    Parser for VT100 input stream.
    Data can be fed through the `feed` method and the given callback will be
    called with KeyPress objects.

    ::

        def callback(key):
            pass
        i = Vt100Parser(callback)
        i.feed('data\x01...')

    :attr feed_key_callback: Function that will be called when a key is parsed.
    """

    # Lookup table of ANSI escape sequences for a VT100 terminal
    # Hint: in order to know what sequences your terminal writes to stdin, run
    #       "od -c" and start typing.
    def __init__(self, feed_key_callback: Callable[[KeyPress], None]) -> None:
        self.feed_key_callback = feed_key_callback
        self.reset()

    def reset(self, request: bool = False) -> None:
        self._in_bracketed_paste = False
        self._start_parser()

    def _start_parser(self) -> None:
        """
        Start the parser coroutine.
        """
        self._input_parser = self._input_parser_generator()
        self._input_parser.send(None)  # type: ignore

    def _get_match(self, prefix: str) -> None | Keys | tuple[Keys, ...]:
        """
        Return the key (or keys) that maps to this prefix.
        """
        # (hard coded) If we match a CPR response, return Keys.CPRResponse.
        # (This one doesn't fit in the ANSI_SEQUENCES, because it contains
        # integer variables.)
        if _cpr_response_re.match(prefix):
            return Keys.CPRResponse

        elif _mouse_event_re.match(prefix):
            return Keys.Vt100MouseEvent

        # Otherwise, use the mappings.
        try:
            return ANSI_SEQUENCES[prefix]
        except KeyError:
            return None

    def _input_parser_generator(self) -> Generator[None, str | _Flush, None]:
        """
        Coroutine (state machine) for the input parser.
        """
        prefix = ""
        retry = False
        flush = False

        while True:
            flush = False

            if retry:
                retry = False
            else:
                # Get next character.
                c = yield

                if isinstance(c, _Flush):
                    flush = True
                else:
                    prefix += c

            # If we have some data, check for matches.
            if prefix:
                is_prefix_of_longer_match = _IS_PREFIX_OF_LONGER_MATCH_CACHE[prefix]
                match = self._get_match(prefix)

                # Exact matches found, call handlers..
                if (flush or not is_prefix_of_longer_match) and match:
                    self._call_handler(match, prefix)
                    prefix = ""

                # No exact match found.
                elif (flush or not is_prefix_of_longer_match) and not match:
                    found = False
                    retry = True

                    # Loop over the input, try the longest match first and
                    # shift.
                    for i in range(len(prefix), 0, -1):
                        match = self._get_match(prefix[:i])
                        if match:
                            self._call_handler(match, prefix[:i])
                            prefix = prefix[i:]
                            found = True

                    if not found:
                        self._call_handler(prefix[0], prefix[0])
                        prefix = prefix[1:]

    def _call_handler(
        self, key: str | Keys | tuple[Keys, ...], insert_text: str
    ) -> None:
        """
        Callback to handler.
        """
        if isinstance(key, tuple):
            # Received ANSI sequence that corresponds with multiple keys
            # (probably alt+something). Handle keys individually, but only pass
            # data payload to first KeyPress (so that we won't insert it
            # multiple times).
            for i, k in enumerate(key):
                self._call_handler(k, insert_text if i == 0 else "")
        else:
            if key == Keys.BracketedPaste:
                self._in_bracketed_paste = True
                self._paste_buffer = ""
            else:
                self.feed_key_callback(KeyPress(key, insert_text))

    def feed(self, data: str) -> None:
        """
        Feed the input stream.

        :param data: Input string (unicode).
        """
        # Handle bracketed paste. (We bypass the parser that matches all other
        # key presses and keep reading input until we see the end mark.)
        # This is much faster then parsing character by character.
        if self._in_bracketed_paste:
            self._paste_buffer += data
            end_mark = "\x1b[201~"

            if end_mark in self._paste_buffer:
                end_index = self._paste_buffer.index(end_mark)

                # Feed content to key bindings.
                paste_content = self._paste_buffer[:end_index]
                self.feed_key_callback(KeyPress(Keys.BracketedPaste, paste_content))

                # Quit bracketed paste mode and handle remaining input.
                self._in_bracketed_paste = False
                remaining = self._paste_buffer[end_index + len(end_mark) :]
                self._paste_buffer = ""

                self.feed(remaining)

        # Handle normal input character by character.
        else:
            for i, c in enumerate(data):
                if self._in_bracketed_paste:
                    # Quit loop and process from this position when the parser
                    # entered bracketed paste.
                    self.feed(data[i:])
                    break
                else:
                    self._input_parser.send(c)

    def flush(self) -> None:
        """
        Flush the buffer of the input stream.

        This will allow us to handle the escape key (or maybe meta) sooner.
        The input received by the escape key is actually the same as the first
        characters of e.g. Arrow-Up, so without knowing what follows the escape
        sequence, we don't know whether escape has been pressed, or whether
        it's something else. This flush function should be called after a
        timeout, and processes everything that's still in the buffer as-is, so
        without assuming any characters will follow.
        """
        self._input_parser.send(_Flush())

    def feed_and_flush(self, data: str) -> None:
        """
        Wrapper around ``feed`` and ``flush``.
        """
        self.feed(data)
        self.flush()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\platformdirs\android.py ===
"""Android."""

from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from typing import TYPE_CHECKING, cast

from .api import PlatformDirsABC


class Android(PlatformDirsABC):
    """
    Follows the guidance `from here <https://android.stackexchange.com/a/216132>`_.

    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`, `version
    <platformdirs.api.PlatformDirsABC.version>`, `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """:return: data directory tied to the user, e.g. ``/data/user/<userid>/<packagename>/files/<AppName>``"""
        return self._append_app_name_and_version(cast(str, _android_folder()), "files")

    @property
    def site_data_dir(self) -> str:
        """:return: data directory shared by users, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_config_dir(self) -> str:
        """
        :return: config directory tied to the user, e.g. \
        ``/data/user/<userid>/<packagename>/shared_prefs/<AppName>``
        """
        return self._append_app_name_and_version(cast(str, _android_folder()), "shared_prefs")

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `user_config_dir`"""
        return self.user_config_dir

    @property
    def user_cache_dir(self) -> str:
        """:return: cache directory tied to the user, e.g.,``/data/user/<userid>/<packagename>/cache/<AppName>``"""
        return self._append_app_name_and_version(cast(str, _android_folder()), "cache")

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, same as `user_cache_dir`"""
        return self.user_cache_dir

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """
        :return: log directory tied to the user, same as `user_cache_dir` if not opinionated else ``log`` in it,
          e.g. ``/data/user/<userid>/<packagename>/cache/<AppName>/log``
        """
        path = self.user_cache_dir
        if self.opinion:
            path = os.path.join(path, "log")  # noqa: PTH118
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user e.g. ``/storage/emulated/0/Documents``"""
        return _android_documents_folder()

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user e.g. ``/storage/emulated/0/Downloads``"""
        return _android_downloads_folder()

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user e.g. ``/storage/emulated/0/Pictures``"""
        return _android_pictures_folder()

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user e.g. ``/storage/emulated/0/DCIM/Camera``"""
        return _android_videos_folder()

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user e.g. ``/storage/emulated/0/Music``"""
        return _android_music_folder()

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user e.g. ``/storage/emulated/0/Desktop``"""
        return "/storage/emulated/0/Desktop"

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, same as `user_cache_dir` if not opinionated else ``tmp`` in it,
          e.g. ``/data/user/<userid>/<packagename>/cache/<AppName>/tmp``
        """
        path = self.user_cache_dir
        if self.opinion:
            path = os.path.join(path, "tmp")  # noqa: PTH118
        return path

    @property
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


@lru_cache(maxsize=1)
def _android_folder() -> str | None:  # noqa: C901
    """:return: base folder for the Android OS or None if it cannot be found"""
    result: str | None = None
    # type checker isn't happy with our "import android", just don't do this when type checking see
    # https://stackoverflow.com/a/61394121
    if not TYPE_CHECKING:
        try:
            # First try to get a path to android app using python4android (if available)...
            from android import mActivity  # noqa: PLC0415

            context = cast("android.content.Context", mActivity.getApplicationContext())  # noqa: F821
            result = context.getFilesDir().getParentFile().getAbsolutePath()
        except Exception:  # noqa: BLE001
            result = None
    if result is None:
        try:
            # ...and fall back to using plain pyjnius, if python4android isn't available or doesn't deliver any useful
            # result...
            from jnius import autoclass  # noqa: PLC0415

            context = autoclass("android.content.Context")
            result = context.getFilesDir().getParentFile().getAbsolutePath()
        except Exception:  # noqa: BLE001
            result = None
    if result is None:
        # and if that fails, too, find an android folder looking at path on the sys.path
        # warning: only works for apps installed under /data, not adopted storage etc.
        pattern = re.compile(r"/data/(data|user/\d+)/(.+)/files")
        for path in sys.path:
            if pattern.match(path):
                result = path.split("/files")[0]
                break
        else:
            result = None
    if result is None:
        # one last try: find an android folder looking at path on the sys.path taking adopted storage paths into
        # account
        pattern = re.compile(r"/mnt/expand/[a-fA-F0-9-]{36}/(data|user/\d+)/(.+)/files")
        for path in sys.path:
            if pattern.match(path):
                result = path.split("/files")[0]
                break
        else:
            result = None
    return result


@lru_cache(maxsize=1)
def _android_documents_folder() -> str:
    """:return: documents folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        documents_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DOCUMENTS).getAbsolutePath()
    except Exception:  # noqa: BLE001
        documents_dir = "/storage/emulated/0/Documents"

    return documents_dir


@lru_cache(maxsize=1)
def _android_downloads_folder() -> str:
    """:return: downloads folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        downloads_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DOWNLOADS).getAbsolutePath()
    except Exception:  # noqa: BLE001
        downloads_dir = "/storage/emulated/0/Downloads"

    return downloads_dir


@lru_cache(maxsize=1)
def _android_pictures_folder() -> str:
    """:return: pictures folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        pictures_dir: str = context.getExternalFilesDir(environment.DIRECTORY_PICTURES).getAbsolutePath()
    except Exception:  # noqa: BLE001
        pictures_dir = "/storage/emulated/0/Pictures"

    return pictures_dir


@lru_cache(maxsize=1)
def _android_videos_folder() -> str:
    """:return: videos folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        videos_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DCIM).getAbsolutePath()
    except Exception:  # noqa: BLE001
        videos_dir = "/storage/emulated/0/DCIM/Camera"

    return videos_dir


@lru_cache(maxsize=1)
def _android_music_folder() -> str:
    """:return: music folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        music_dir: str = context.getExternalFilesDir(environment.DIRECTORY_MUSIC).getAbsolutePath()
    except Exception:  # noqa: BLE001
        music_dir = "/storage/emulated/0/Music"

    return music_dir


__all__ = [
    "Android",
]

# === NexusCore/openenv\Lib\site-packages\PIL\IptcImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# IPTC/NAA file handling
#
# history:
# 1995-10-01 fl   Created
# 1998-03-09 fl   Cleaned up and added to PIL
# 2002-06-18 fl   Added getiptcinfo helper
#
# Copyright (c) Secret Labs AB 1997-2002.
# Copyright (c) Fredrik Lundh 1995.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO
from typing import cast

from . import Image, ImageFile
from ._binary import i16be as i16
from ._binary import i32be as i32
from ._deprecate import deprecate

COMPRESSION = {1: "raw", 5: "jpeg"}


def __getattr__(name: str) -> bytes:
    if name == "PAD":
        deprecate("IptcImagePlugin.PAD", 12)
        return b"\0\0\0\0"
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)


#
# Helpers


def _i(c: bytes) -> int:
    return i32((b"\0\0\0\0" + c)[-4:])


def _i8(c: int | bytes) -> int:
    return c if isinstance(c, int) else c[0]


def i(c: bytes) -> int:
    """.. deprecated:: 10.2.0"""
    deprecate("IptcImagePlugin.i", 12)
    return _i(c)


def dump(c: Sequence[int | bytes]) -> None:
    """.. deprecated:: 10.2.0"""
    deprecate("IptcImagePlugin.dump", 12)
    for i in c:
        print(f"{_i8(i):02x}", end=" ")
    print()


##
# Image plugin for IPTC/NAA datastreams.  To read IPTC/NAA fields
# from TIFF and JPEG files, use the <b>getiptcinfo</b> function.


class IptcImageFile(ImageFile.ImageFile):
    format = "IPTC"
    format_description = "IPTC/NAA"

    def getint(self, key: tuple[int, int]) -> int:
        return _i(self.info[key])

    def field(self) -> tuple[tuple[int, int] | None, int]:
        #
        # get a IPTC field header
        s = self.fp.read(5)
        if not s.strip(b"\x00"):
            return None, 0

        tag = s[1], s[2]

        # syntax
        if s[0] != 0x1C or tag[0] not in [1, 2, 3, 4, 5, 6, 7, 8, 9, 240]:
            msg = "invalid IPTC/NAA file"
            raise SyntaxError(msg)

        # field size
        size = s[3]
        if size > 132:
            msg = "illegal field length in IPTC/NAA file"
            raise OSError(msg)
        elif size == 128:
            size = 0
        elif size > 128:
            size = _i(self.fp.read(size - 128))
        else:
            size = i16(s, 3)

        return tag, size

    def _open(self) -> None:
        # load descriptive fields
        while True:
            offset = self.fp.tell()
            tag, size = self.field()
            if not tag or tag == (8, 10):
                break
            if size:
                tagdata = self.fp.read(size)
            else:
                tagdata = None
            if tag in self.info:
                if isinstance(self.info[tag], list):
                    self.info[tag].append(tagdata)
                else:
                    self.info[tag] = [self.info[tag], tagdata]
            else:
                self.info[tag] = tagdata

        # mode
        layers = self.info[(3, 60)][0]
        component = self.info[(3, 60)][1]
        if (3, 65) in self.info:
            id = self.info[(3, 65)][0] - 1
        else:
            id = 0
        if layers == 1 and not component:
            self._mode = "L"
        elif layers == 3 and component:
            self._mode = "RGB"[id]
        elif layers == 4 and component:
            self._mode = "CMYK"[id]

        # size
        self._size = self.getint((3, 20)), self.getint((3, 30))

        # compression
        try:
            compression = COMPRESSION[self.getint((3, 120))]
        except KeyError as e:
            msg = "Unknown IPTC image compression"
            raise OSError(msg) from e

        # tile
        if tag == (8, 10):
            self.tile = [
                ImageFile._Tile("iptc", (0, 0) + self.size, offset, compression)
            ]

    def load(self) -> Image.core.PixelAccess | None:
        if len(self.tile) != 1 or self.tile[0][0] != "iptc":
            return ImageFile.ImageFile.load(self)

        offset, compression = self.tile[0][2:]

        self.fp.seek(offset)

        # Copy image data to temporary file
        o = BytesIO()
        if compression == "raw":
            # To simplify access to the extracted file,
            # prepend a PPM header
            o.write(b"P5\n%d %d\n255\n" % self.size)
        while True:
            type, size = self.field()
            if type != (8, 10):
                break
            while size > 0:
                s = self.fp.read(min(size, 8192))
                if not s:
                    break
                o.write(s)
                size -= len(s)

        with Image.open(o) as _im:
            _im.load()
            self.im = _im.im
        return None


Image.register_open(IptcImageFile.format, IptcImageFile)

Image.register_extension(IptcImageFile.format, ".iim")


def getiptcinfo(
    im: ImageFile.ImageFile,
) -> dict[tuple[int, int], bytes | list[bytes]] | None:
    """
    Get IPTC information from TIFF, JPEG, or IPTC file.

    :param im: An image containing IPTC data.
    :returns: A dictionary containing IPTC information, or None if
        no IPTC information block was found.
    """
    from . import JpegImagePlugin, TiffImagePlugin

    data = None

    info: dict[tuple[int, int], bytes | list[bytes]] = {}
    if isinstance(im, IptcImageFile):
        # return info dictionary right away
        for k, v in im.info.items():
            if isinstance(k, tuple):
                info[k] = v
        return info

    elif isinstance(im, JpegImagePlugin.JpegImageFile):
        # extract the IPTC/NAA resource
        photoshop = im.info.get("photoshop")
        if photoshop:
            data = photoshop.get(0x0404)

    elif isinstance(im, TiffImagePlugin.TiffImageFile):
        # get raw data from the IPTC/NAA tag (PhotoShop tags the data
        # as 4-byte integers, so we cannot use the get method...)
        try:
            data = im.tag_v2[TiffImagePlugin.IPTC_NAA_CHUNK]
        except KeyError:
            pass

    if data is None:
        return None  # no properties

    # create an IptcImagePlugin object without initializing it
    class FakeImage:
        pass

    fake_im = FakeImage()
    fake_im.__class__ = IptcImageFile  # type: ignore[assignment]
    iptc_im = cast(IptcImageFile, fake_im)

    # parse the IPTC information chunk
    iptc_im.info = {}
    iptc_im.fp = BytesIO(data)

    try:
        iptc_im._open()
    except (IndexError, KeyError):
        pass  # expected failure

    for k, v in iptc_im.info.items():
        if isinstance(k, tuple):
            info[k] = v
    return info

# === NexusCore/openenv\Lib\site-packages\platformdirs\android.py ===
"""Android."""

from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from typing import TYPE_CHECKING, cast

from .api import PlatformDirsABC


class Android(PlatformDirsABC):
    """
    Follows the guidance `from here <https://android.stackexchange.com/a/216132>`_.

    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`, `version
    <platformdirs.api.PlatformDirsABC.version>`, `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """:return: data directory tied to the user, e.g. ``/data/user/<userid>/<packagename>/files/<AppName>``"""
        return self._append_app_name_and_version(cast("str", _android_folder()), "files")

    @property
    def site_data_dir(self) -> str:
        """:return: data directory shared by users, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_config_dir(self) -> str:
        """
        :return: config directory tied to the user, e.g. \
        ``/data/user/<userid>/<packagename>/shared_prefs/<AppName>``
        """
        return self._append_app_name_and_version(cast("str", _android_folder()), "shared_prefs")

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `user_config_dir`"""
        return self.user_config_dir

    @property
    def user_cache_dir(self) -> str:
        """:return: cache directory tied to the user, e.g.,``/data/user/<userid>/<packagename>/cache/<AppName>``"""
        return self._append_app_name_and_version(cast("str", _android_folder()), "cache")

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, same as `user_cache_dir`"""
        return self.user_cache_dir

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """
        :return: log directory tied to the user, same as `user_cache_dir` if not opinionated else ``log`` in it,
          e.g. ``/data/user/<userid>/<packagename>/cache/<AppName>/log``
        """
        path = self.user_cache_dir
        if self.opinion:
            path = os.path.join(path, "log")  # noqa: PTH118
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user e.g. ``/storage/emulated/0/Documents``"""
        return _android_documents_folder()

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user e.g. ``/storage/emulated/0/Downloads``"""
        return _android_downloads_folder()

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user e.g. ``/storage/emulated/0/Pictures``"""
        return _android_pictures_folder()

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user e.g. ``/storage/emulated/0/DCIM/Camera``"""
        return _android_videos_folder()

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user e.g. ``/storage/emulated/0/Music``"""
        return _android_music_folder()

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user e.g. ``/storage/emulated/0/Desktop``"""
        return "/storage/emulated/0/Desktop"

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, same as `user_cache_dir` if not opinionated else ``tmp`` in it,
          e.g. ``/data/user/<userid>/<packagename>/cache/<AppName>/tmp``
        """
        path = self.user_cache_dir
        if self.opinion:
            path = os.path.join(path, "tmp")  # noqa: PTH118
        return path

    @property
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


@lru_cache(maxsize=1)
def _android_folder() -> str | None:  # noqa: C901
    """:return: base folder for the Android OS or None if it cannot be found"""
    result: str | None = None
    # type checker isn't happy with our "import android", just don't do this when type checking see
    # https://stackoverflow.com/a/61394121
    if not TYPE_CHECKING:
        try:
            # First try to get a path to android app using python4android (if available)...
            from android import mActivity  # noqa: PLC0415

            context = cast("android.content.Context", mActivity.getApplicationContext())  # noqa: F821
            result = context.getFilesDir().getParentFile().getAbsolutePath()
        except Exception:  # noqa: BLE001
            result = None
    if result is None:
        try:
            # ...and fall back to using plain pyjnius, if python4android isn't available or doesn't deliver any useful
            # result...
            from jnius import autoclass  # noqa: PLC0415

            context = autoclass("android.content.Context")
            result = context.getFilesDir().getParentFile().getAbsolutePath()
        except Exception:  # noqa: BLE001
            result = None
    if result is None:
        # and if that fails, too, find an android folder looking at path on the sys.path
        # warning: only works for apps installed under /data, not adopted storage etc.
        pattern = re.compile(r"/data/(data|user/\d+)/(.+)/files")
        for path in sys.path:
            if pattern.match(path):
                result = path.split("/files")[0]
                break
        else:
            result = None
    if result is None:
        # one last try: find an android folder looking at path on the sys.path taking adopted storage paths into
        # account
        pattern = re.compile(r"/mnt/expand/[a-fA-F0-9-]{36}/(data|user/\d+)/(.+)/files")
        for path in sys.path:
            if pattern.match(path):
                result = path.split("/files")[0]
                break
        else:
            result = None
    return result


@lru_cache(maxsize=1)
def _android_documents_folder() -> str:
    """:return: documents folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        documents_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DOCUMENTS).getAbsolutePath()
    except Exception:  # noqa: BLE001
        documents_dir = "/storage/emulated/0/Documents"

    return documents_dir


@lru_cache(maxsize=1)
def _android_downloads_folder() -> str:
    """:return: downloads folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        downloads_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DOWNLOADS).getAbsolutePath()
    except Exception:  # noqa: BLE001
        downloads_dir = "/storage/emulated/0/Downloads"

    return downloads_dir


@lru_cache(maxsize=1)
def _android_pictures_folder() -> str:
    """:return: pictures folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        pictures_dir: str = context.getExternalFilesDir(environment.DIRECTORY_PICTURES).getAbsolutePath()
    except Exception:  # noqa: BLE001
        pictures_dir = "/storage/emulated/0/Pictures"

    return pictures_dir


@lru_cache(maxsize=1)
def _android_videos_folder() -> str:
    """:return: videos folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        videos_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DCIM).getAbsolutePath()
    except Exception:  # noqa: BLE001
        videos_dir = "/storage/emulated/0/DCIM/Camera"

    return videos_dir


@lru_cache(maxsize=1)
def _android_music_folder() -> str:
    """:return: music folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        music_dir: str = context.getExternalFilesDir(environment.DIRECTORY_MUSIC).getAbsolutePath()
    except Exception:  # noqa: BLE001
        music_dir = "/storage/emulated/0/Music"

    return music_dir


__all__ = [
    "Android",
]

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\V_D_M_X_.py ===
from . import DefaultTable
from fontTools.misc import sstruct
from fontTools.misc.textTools import safeEval
import struct

VDMX_HeaderFmt = """
	>                 # big endian
	version:     H    # Version number (0 or 1)
	numRecs:     H    # Number of VDMX groups present
	numRatios:   H    # Number of aspect ratio groupings
"""
# the VMDX header is followed by an array of RatRange[numRatios] (i.e. aspect
# ratio ranges);
VDMX_RatRangeFmt = """
	>                 # big endian
	bCharSet:    B    # Character set
	xRatio:      B    # Value to use for x-Ratio
	yStartRatio: B    # Starting y-Ratio value
	yEndRatio:   B    # Ending y-Ratio value
"""
# followed by an array of offset[numRatios] from start of VDMX table to the
# VDMX Group for this ratio range (offsets will be re-calculated on compile);
# followed by an array of Group[numRecs] records;
VDMX_GroupFmt = """
	>                 # big endian
	recs:        H    # Number of height records in this group
	startsz:     B    # Starting yPelHeight
	endsz:       B    # Ending yPelHeight
"""
# followed by an array of vTable[recs] records.
VDMX_vTableFmt = """
	>                 # big endian
	yPelHeight:  H    # yPelHeight to which values apply
	yMax:        h    # Maximum value (in pels) for this yPelHeight
	yMin:        h    # Minimum value (in pels) for this yPelHeight
"""


class table_V_D_M_X_(DefaultTable.DefaultTable):
    """Vertical Device Metrics table

    The ``VDMX`` table records changes to the vertical glyph minima
    and maxima that result from Truetype instructions.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/vdmx
    """

    def decompile(self, data, ttFont):
        pos = 0  # track current position from to start of VDMX table
        dummy, data = sstruct.unpack2(VDMX_HeaderFmt, data, self)
        pos += sstruct.calcsize(VDMX_HeaderFmt)
        self.ratRanges = []
        for i in range(self.numRatios):
            ratio, data = sstruct.unpack2(VDMX_RatRangeFmt, data)
            pos += sstruct.calcsize(VDMX_RatRangeFmt)
            # the mapping between a ratio and a group is defined further below
            ratio["groupIndex"] = None
            self.ratRanges.append(ratio)
        lenOffset = struct.calcsize(">H")
        _offsets = []  # temporarily store offsets to groups
        for i in range(self.numRatios):
            offset = struct.unpack(">H", data[0:lenOffset])[0]
            data = data[lenOffset:]
            pos += lenOffset
            _offsets.append(offset)
        self.groups = []
        for groupIndex in range(self.numRecs):
            # the offset to this group from beginning of the VDMX table
            currOffset = pos
            group, data = sstruct.unpack2(VDMX_GroupFmt, data)
            # the group lenght and bounding sizes are re-calculated on compile
            recs = group.pop("recs")
            startsz = group.pop("startsz")
            endsz = group.pop("endsz")
            pos += sstruct.calcsize(VDMX_GroupFmt)
            for j in range(recs):
                vTable, data = sstruct.unpack2(VDMX_vTableFmt, data)
                vTableLength = sstruct.calcsize(VDMX_vTableFmt)
                pos += vTableLength
                # group is a dict of (yMax, yMin) tuples keyed by yPelHeight
                group[vTable["yPelHeight"]] = (vTable["yMax"], vTable["yMin"])
            # make sure startsz and endsz match the calculated values
            minSize = min(group.keys())
            maxSize = max(group.keys())
            assert (
                startsz == minSize
            ), "startsz (%s) must equal min yPelHeight (%s): group %d" % (
                group.startsz,
                minSize,
                groupIndex,
            )
            assert (
                endsz == maxSize
            ), "endsz (%s) must equal max yPelHeight (%s): group %d" % (
                group.endsz,
                maxSize,
                groupIndex,
            )
            self.groups.append(group)
            # match the defined offsets with the current group's offset
            for offsetIndex, offsetValue in enumerate(_offsets):
                # when numRecs < numRatios there can more than one ratio range
                # sharing the same VDMX group
                if currOffset == offsetValue:
                    # map the group with the ratio range thas has the same
                    # index as the offset to that group (it took me a while..)
                    self.ratRanges[offsetIndex]["groupIndex"] = groupIndex
        # check that all ratio ranges have a group
        for i in range(self.numRatios):
            ratio = self.ratRanges[i]
            if ratio["groupIndex"] is None:
                from fontTools import ttLib

                raise ttLib.TTLibError("no group defined for ratRange %d" % i)

    def _getOffsets(self):
        """
        Calculate offsets to VDMX_Group records.
        For each ratRange return a list of offset values from the beginning of
        the VDMX table to a VDMX_Group.
        """
        lenHeader = sstruct.calcsize(VDMX_HeaderFmt)
        lenRatRange = sstruct.calcsize(VDMX_RatRangeFmt)
        lenOffset = struct.calcsize(">H")
        lenGroupHeader = sstruct.calcsize(VDMX_GroupFmt)
        lenVTable = sstruct.calcsize(VDMX_vTableFmt)
        # offset to the first group
        pos = lenHeader + self.numRatios * lenRatRange + self.numRatios * lenOffset
        groupOffsets = []
        for group in self.groups:
            groupOffsets.append(pos)
            lenGroup = lenGroupHeader + len(group) * lenVTable
            pos += lenGroup  # offset to next group
        offsets = []
        for ratio in self.ratRanges:
            groupIndex = ratio["groupIndex"]
            offsets.append(groupOffsets[groupIndex])
        return offsets

    def compile(self, ttFont):
        if not (self.version == 0 or self.version == 1):
            from fontTools import ttLib

            raise ttLib.TTLibError(
                "unknown format for VDMX table: version %s" % self.version
            )
        data = sstruct.pack(VDMX_HeaderFmt, self)
        for ratio in self.ratRanges:
            data += sstruct.pack(VDMX_RatRangeFmt, ratio)
        # recalculate offsets to VDMX groups
        for offset in self._getOffsets():
            data += struct.pack(">H", offset)
        for group in self.groups:
            recs = len(group)
            startsz = min(group.keys())
            endsz = max(group.keys())
            gHeader = {"recs": recs, "startsz": startsz, "endsz": endsz}
            data += sstruct.pack(VDMX_GroupFmt, gHeader)
            for yPelHeight, (yMax, yMin) in sorted(group.items()):
                vTable = {"yPelHeight": yPelHeight, "yMax": yMax, "yMin": yMin}
                data += sstruct.pack(VDMX_vTableFmt, vTable)
        return data

    def toXML(self, writer, ttFont):
        writer.simpletag("version", value=self.version)
        writer.newline()
        writer.begintag("ratRanges")
        writer.newline()
        for ratio in self.ratRanges:
            groupIndex = ratio["groupIndex"]
            writer.simpletag(
                "ratRange",
                bCharSet=ratio["bCharSet"],
                xRatio=ratio["xRatio"],
                yStartRatio=ratio["yStartRatio"],
                yEndRatio=ratio["yEndRatio"],
                groupIndex=groupIndex,
            )
            writer.newline()
        writer.endtag("ratRanges")
        writer.newline()
        writer.begintag("groups")
        writer.newline()
        for groupIndex in range(self.numRecs):
            group = self.groups[groupIndex]
            recs = len(group)
            startsz = min(group.keys())
            endsz = max(group.keys())
            writer.begintag("group", index=groupIndex)
            writer.newline()
            writer.comment("recs=%d, startsz=%d, endsz=%d" % (recs, startsz, endsz))
            writer.newline()
            for yPelHeight, (yMax, yMin) in sorted(group.items()):
                writer.simpletag(
                    "record",
                    [("yPelHeight", yPelHeight), ("yMax", yMax), ("yMin", yMin)],
                )
                writer.newline()
            writer.endtag("group")
            writer.newline()
        writer.endtag("groups")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "version":
            self.version = safeEval(attrs["value"])
        elif name == "ratRanges":
            if not hasattr(self, "ratRanges"):
                self.ratRanges = []
            for element in content:
                if not isinstance(element, tuple):
                    continue
                name, attrs, content = element
                if name == "ratRange":
                    if not hasattr(self, "numRatios"):
                        self.numRatios = 1
                    else:
                        self.numRatios += 1
                    ratio = {
                        "bCharSet": safeEval(attrs["bCharSet"]),
                        "xRatio": safeEval(attrs["xRatio"]),
                        "yStartRatio": safeEval(attrs["yStartRatio"]),
                        "yEndRatio": safeEval(attrs["yEndRatio"]),
                        "groupIndex": safeEval(attrs["groupIndex"]),
                    }
                    self.ratRanges.append(ratio)
        elif name == "groups":
            if not hasattr(self, "groups"):
                self.groups = []
            for element in content:
                if not isinstance(element, tuple):
                    continue
                name, attrs, content = element
                if name == "group":
                    if not hasattr(self, "numRecs"):
                        self.numRecs = 1
                    else:
                        self.numRecs += 1
                    group = {}
                    for element in content:
                        if not isinstance(element, tuple):
                            continue
                        name, attrs, content = element
                        if name == "record":
                            yPelHeight = safeEval(attrs["yPelHeight"])
                            yMax = safeEval(attrs["yMax"])
                            yMin = safeEval(attrs["yMin"])
                            group[yPelHeight] = (yMax, yMin)
                    self.groups.append(group)

# === NexusCore/openenv\Lib\site-packages\gitdb\test\test_pack.py ===
# Copyright (C) 2010, 2011 Sebastian Thiel (byronimo@gmail.com) and contributors
#
# This module is part of GitDB and is released under
# the New BSD License: https://opensource.org/license/bsd-3-clause/
"""Test everything about packs reading and writing"""
from gitdb.test.lib import (
    TestBase,
    with_rw_directory,
    fixture_path
)

from gitdb.stream import DeltaApplyReader

from gitdb.pack import (
    PackEntity,
    PackIndexFile,
    PackFile
)

from gitdb.base import (
    OInfo,
    OStream,
)

from gitdb.fun import delta_types
from gitdb.exc import UnsupportedOperation
from gitdb.util import to_bin_sha

import pytest

import os
import tempfile


#{ Utilities
def bin_sha_from_filename(filename):
    return to_bin_sha(os.path.splitext(os.path.basename(filename))[0][5:])
#} END utilities


class TestPack(TestBase):

    packindexfile_v1 = (fixture_path('packs/pack-c0438c19fb16422b6bbcce24387b3264416d485b.idx'), 1, 67)
    packindexfile_v2 = (fixture_path('packs/pack-11fdfa9e156ab73caae3b6da867192221f2089c2.idx'), 2, 30)
    packindexfile_v2_3_ascii = (fixture_path('packs/pack-a2bf8e71d8c18879e499335762dd95119d93d9f1.idx'), 2, 42)
    packfile_v2_1 = (fixture_path('packs/pack-c0438c19fb16422b6bbcce24387b3264416d485b.pack'), 2, packindexfile_v1[2])
    packfile_v2_2 = (fixture_path('packs/pack-11fdfa9e156ab73caae3b6da867192221f2089c2.pack'), 2, packindexfile_v2[2])
    packfile_v2_3_ascii = (
        fixture_path('packs/pack-a2bf8e71d8c18879e499335762dd95119d93d9f1.pack'), 2, packindexfile_v2_3_ascii[2])

    def _assert_index_file(self, index, version, size):
        assert index.packfile_checksum() != index.indexfile_checksum()
        assert len(index.packfile_checksum()) == 20
        assert len(index.indexfile_checksum()) == 20
        assert index.version() == version
        assert index.size() == size
        assert len(index.offsets()) == size

        # get all data of all objects
        for oidx in range(index.size()):
            sha = index.sha(oidx)
            assert oidx == index.sha_to_index(sha)

            entry = index.entry(oidx)
            assert len(entry) == 3

            assert entry[0] == index.offset(oidx)
            assert entry[1] == sha
            assert entry[2] == index.crc(oidx)

            # verify partial sha
            for l in (4, 8, 11, 17, 20):
                assert index.partial_sha_to_index(sha[:l], l * 2) == oidx

        # END for each object index in indexfile
        self.assertRaises(ValueError, index.partial_sha_to_index, "\0", 2)

    def _assert_pack_file(self, pack, version, size):
        assert pack.version() == 2
        assert pack.size() == size
        assert len(pack.checksum()) == 20

        num_obj = 0
        for obj in pack.stream_iter():
            num_obj += 1
            info = pack.info(obj.pack_offset)
            stream = pack.stream(obj.pack_offset)

            assert info.pack_offset == stream.pack_offset
            assert info.type_id == stream.type_id
            assert hasattr(stream, 'read')

            # it should be possible to read from both streams
            assert obj.read() == stream.read()

            streams = pack.collect_streams(obj.pack_offset)
            assert streams

            # read the stream
            try:
                dstream = DeltaApplyReader.new(streams)
            except ValueError:
                # ignore these, old git versions use only ref deltas,
                # which we haven't resolved ( as we are without an index )
                # Also ignore non-delta streams
                continue
            # END get deltastream

            # read all
            data = dstream.read()
            assert len(data) == dstream.size

            # test seek
            dstream.seek(0)
            assert dstream.read() == data

            # read chunks
            # NOTE: the current implementation is safe, it basically transfers
            # all calls to the underlying memory map

        # END for each object
        assert num_obj == size

    def test_pack_index(self):
        # check version 1 and 2
        for indexfile, version, size in (self.packindexfile_v1, self.packindexfile_v2):
            index = PackIndexFile(indexfile)
            self._assert_index_file(index, version, size)
        # END run tests

    def test_pack(self):
        # there is this special version 3, but apparently its like 2 ...
        for packfile, version, size in (self.packfile_v2_3_ascii, self.packfile_v2_1, self.packfile_v2_2):
            pack = PackFile(packfile)
            self._assert_pack_file(pack, version, size)
        # END for each pack to test

    @with_rw_directory
    def test_pack_entity(self, rw_dir):
        pack_objs = list()
        for packinfo, indexinfo in ((self.packfile_v2_1, self.packindexfile_v1),
                                    (self.packfile_v2_2, self.packindexfile_v2),
                                    (self.packfile_v2_3_ascii, self.packindexfile_v2_3_ascii)):
            packfile, version, size = packinfo
            indexfile, version, size = indexinfo
            entity = PackEntity(packfile)
            assert entity.pack().path() == packfile
            assert entity.index().path() == indexfile
            pack_objs.extend(entity.stream_iter())

            count = 0
            for info, stream in zip(entity.info_iter(), entity.stream_iter()):
                count += 1
                assert info.binsha == stream.binsha
                assert len(info.binsha) == 20
                assert info.type_id == stream.type_id
                assert info.size == stream.size

                # we return fully resolved items, which is implied by the sha centric access
                assert not info.type_id in delta_types

                # try all calls
                assert len(entity.collect_streams(info.binsha))
                oinfo = entity.info(info.binsha)
                assert isinstance(oinfo, OInfo)
                assert oinfo.binsha is not None
                ostream = entity.stream(info.binsha)
                assert isinstance(ostream, OStream)
                assert ostream.binsha is not None

                # verify the stream
                try:
                    assert entity.is_valid_stream(info.binsha, use_crc=True)
                except UnsupportedOperation:
                    pass
                # END ignore version issues
                assert entity.is_valid_stream(info.binsha, use_crc=False)
            # END for each info, stream tuple
            assert count == size

        # END for each entity

        # pack writing - write all packs into one
        # index path can be None
        pack_path1 = tempfile.mktemp('', "pack1", rw_dir)
        pack_path2 = tempfile.mktemp('', "pack2", rw_dir)
        index_path = tempfile.mktemp('', 'index', rw_dir)
        iteration = 0

        def rewind_streams():
            for obj in pack_objs:
                obj.stream.seek(0)
        # END utility
        for ppath, ipath, num_obj in zip((pack_path1, pack_path2),
                                         (index_path, None),
                                         (len(pack_objs), None)):
            iwrite = None
            if ipath:
                ifile = open(ipath, 'wb')
                iwrite = ifile.write
            # END handle ip

            # make sure we rewind the streams ... we work on the same objects over and over again
            if iteration > 0:
                rewind_streams()
            # END rewind streams
            iteration += 1

            with open(ppath, 'wb') as pfile:
                pack_sha, index_sha = PackEntity.write_pack(pack_objs, pfile.write, iwrite, object_count=num_obj)
            assert os.path.getsize(ppath) > 100

            # verify pack
            pf = PackFile(ppath)
            assert pf.size() == len(pack_objs)
            assert pf.version() == PackFile.pack_version_default
            assert pf.checksum() == pack_sha
            pf.close()

            # verify index
            if ipath is not None:
                ifile.close()
                assert os.path.getsize(ipath) > 100
                idx = PackIndexFile(ipath)
                assert idx.version() == PackIndexFile.index_version_default
                assert idx.packfile_checksum() == pack_sha
                assert idx.indexfile_checksum() == index_sha
                assert idx.size() == len(pack_objs)
                idx.close()
            # END verify files exist
        # END for each packpath, indexpath pair

        # verify the packs thoroughly
        rewind_streams()
        entity = PackEntity.create(pack_objs, rw_dir)
        count = 0
        for info in entity.info_iter():
            count += 1
            for use_crc in range(2):
                assert entity.is_valid_stream(info.binsha, use_crc)
            # END for each crc mode
        # END for each info
        assert count == len(pack_objs)
        entity.close()

    def test_pack_64(self):
        # TODO: hex-edit a pack helping us to verify that we can handle 64 byte offsets
        # of course without really needing such a huge pack
        pytest.skip('not implemented')

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\text_service\transports\base.py ===
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
import abc
from typing import Awaitable, Callable, Dict, Optional, Sequence, Union

import google.api_core
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta import gapic_version as package_version
from google.ai.generativelanguage_v1beta.types import text_service

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class TextServiceTransport(abc.ABC):
    """Abstract transport class for TextService."""

    AUTH_SCOPES = ()

    DEFAULT_HOST: str = "generativelanguage.googleapis.com"

    def __init__(
        self,
        *,
        host: str = DEFAULT_HOST,
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A list of scopes.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
        """

        scopes_kwargs = {"scopes": scopes, "default_scopes": self.AUTH_SCOPES}

        # Save the scopes.
        self._scopes = scopes

        # If no credentials are provided, then determine the appropriate
        # defaults.
        if credentials and credentials_file:
            raise core_exceptions.DuplicateCredentialArgs(
                "'credentials_file' and 'credentials' are mutually exclusive"
            )

        if credentials_file is not None:
            credentials, _ = google.auth.load_credentials_from_file(
                credentials_file, **scopes_kwargs, quota_project_id=quota_project_id
            )
        elif credentials is None:
            credentials, _ = google.auth.default(
                **scopes_kwargs, quota_project_id=quota_project_id
            )
            # Don't apply audience if the credentials file passed from user.
            if hasattr(credentials, "with_gdch_audience"):
                credentials = credentials.with_gdch_audience(
                    api_audience if api_audience else host
                )

        # If the credentials are service account credentials, then always try to use self signed JWT.
        if (
            always_use_jwt_access
            and isinstance(credentials, service_account.Credentials)
            and hasattr(service_account.Credentials, "with_always_use_jwt_access")
        ):
            credentials = credentials.with_always_use_jwt_access(True)

        # Save the credentials.
        self._credentials = credentials

        # Save the hostname. Default to port 443 (HTTPS) if none is specified.
        if ":" not in host:
            host += ":443"
        self._host = host

    @property
    def host(self):
        return self._host

    def _prep_wrapped_messages(self, client_info):
        # Precompute the wrapped methods.
        self._wrapped_methods = {
            self.generate_text: gapic_v1.method.wrap_method(
                self.generate_text,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.embed_text: gapic_v1.method.wrap_method(
                self.embed_text,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.batch_embed_text: gapic_v1.method.wrap_method(
                self.batch_embed_text,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.count_text_tokens: gapic_v1.method.wrap_method(
                self.count_text_tokens,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
        }

    def close(self):
        """Closes resources associated with the transport.

        .. warning::
             Only call this method if the transport is NOT shared
             with other clients - this may cause errors in other clients!
        """
        raise NotImplementedError()

    @property
    def generate_text(
        self,
    ) -> Callable[
        [text_service.GenerateTextRequest],
        Union[
            text_service.GenerateTextResponse,
            Awaitable[text_service.GenerateTextResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def embed_text(
        self,
    ) -> Callable[
        [text_service.EmbedTextRequest],
        Union[
            text_service.EmbedTextResponse, Awaitable[text_service.EmbedTextResponse]
        ],
    ]:
        raise NotImplementedError()

    @property
    def batch_embed_text(
        self,
    ) -> Callable[
        [text_service.BatchEmbedTextRequest],
        Union[
            text_service.BatchEmbedTextResponse,
            Awaitable[text_service.BatchEmbedTextResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def count_text_tokens(
        self,
    ) -> Callable[
        [text_service.CountTextTokensRequest],
        Union[
            text_service.CountTextTokensResponse,
            Awaitable[text_service.CountTextTokensResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("TextServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\types\safety.py ===
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
    package="google.ai.generativelanguage.v1beta2",
    manifest={
        "HarmCategory",
        "ContentFilter",
        "SafetyFeedback",
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
            Content that is rude, disrepspectful, or
            profane.
        HARM_CATEGORY_VIOLENCE (3):
            Describes scenarios depictng violence against
            an individual or group, or general descriptions
            of gore.
        HARM_CATEGORY_SEXUAL (4):
            Contains references to sexual acts or other
            lewd content.
        HARM_CATEGORY_MEDICAL (5):
            Promotes unchecked medical advice.
        HARM_CATEGORY_DANGEROUS (6):
            Dangerous content that promotes, facilitates,
            or encourages harmful acts.
    """
    HARM_CATEGORY_UNSPECIFIED = 0
    HARM_CATEGORY_DEROGATORY = 1
    HARM_CATEGORY_TOXICITY = 2
    HARM_CATEGORY_VIOLENCE = 3
    HARM_CATEGORY_SEXUAL = 4
    HARM_CATEGORY_MEDICAL = 5
    HARM_CATEGORY_DANGEROUS = 6


class ContentFilter(proto.Message):
    r"""Content filtering metadata associated with processing a
    single request.
    ContentFilter contains a reason and an optional supporting
    string. The reason may be unspecified.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        reason (google.ai.generativelanguage_v1beta2.types.ContentFilter.BlockedReason):
            The reason content was blocked during request
            processing.
        message (str):
            A string that describes the filtering
            behavior in more detail.

            This field is a member of `oneof`_ ``_message``.
    """

    class BlockedReason(proto.Enum):
        r"""A list of reasons why content may have been blocked.

        Values:
            BLOCKED_REASON_UNSPECIFIED (0):
                A blocked reason was not specified.
            SAFETY (1):
                Content was blocked by safety settings.
            OTHER (2):
                Content was blocked, but the reason is
                uncategorized.
        """
        BLOCKED_REASON_UNSPECIFIED = 0
        SAFETY = 1
        OTHER = 2

    reason: BlockedReason = proto.Field(
        proto.ENUM,
        number=1,
        enum=BlockedReason,
    )
    message: str = proto.Field(
        proto.STRING,
        number=2,
        optional=True,
    )


class SafetyFeedback(proto.Message):
    r"""Safety feedback for an entire request.

    This field is populated if content in the input and/or response
    is blocked due to safety settings. SafetyFeedback may not exist
    for every HarmCategory. Each SafetyFeedback will return the
    safety settings used by the request as well as the lowest
    HarmProbability that should be allowed in order to return a
    result.

    Attributes:
        rating (google.ai.generativelanguage_v1beta2.types.SafetyRating):
            Safety rating evaluated from content.
        setting (google.ai.generativelanguage_v1beta2.types.SafetySetting):
            Safety settings applied to the request.
    """

    rating: "SafetyRating" = proto.Field(
        proto.MESSAGE,
        number=1,
        message="SafetyRating",
    )
    setting: "SafetySetting" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="SafetySetting",
    )


class SafetyRating(proto.Message):
    r"""Safety rating for a piece of content.

    The safety rating contains the category of harm and the harm
    probability level in that category for a piece of content.
    Content is classified for safety across a number of harm
    categories and the probability of the harm classification is
    included here.

    Attributes:
        category (google.ai.generativelanguage_v1beta2.types.HarmCategory):
            Required. The category for this rating.
        probability (google.ai.generativelanguage_v1beta2.types.SafetyRating.HarmProbability):
            Required. The probability of harm for this
            content.
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


class SafetySetting(proto.Message):
    r"""Safety setting, affecting the safety-blocking behavior.

    Passing a safety setting for a category changes the allowed
    proability that content is blocked.

    Attributes:
        category (google.ai.generativelanguage_v1beta2.types.HarmCategory):
            Required. The category for this setting.
        threshold (google.ai.generativelanguage_v1beta2.types.SafetySetting.HarmBlockThreshold):
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
        """
        HARM_BLOCK_THRESHOLD_UNSPECIFIED = 0
        BLOCK_LOW_AND_ABOVE = 1
        BLOCK_MEDIUM_AND_ABOVE = 2
        BLOCK_ONLY_HIGH = 3

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

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\platformdirs\android.py ===
"""Android."""

from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from typing import TYPE_CHECKING, cast

from .api import PlatformDirsABC


class Android(PlatformDirsABC):
    """
    Follows the guidance `from here <https://android.stackexchange.com/a/216132>`_.

    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`, `version
    <platformdirs.api.PlatformDirsABC.version>`, `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """:return: data directory tied to the user, e.g. ``/data/user/<userid>/<packagename>/files/<AppName>``"""
        return self._append_app_name_and_version(cast(str, _android_folder()), "files")

    @property
    def site_data_dir(self) -> str:
        """:return: data directory shared by users, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_config_dir(self) -> str:
        """
        :return: config directory tied to the user, e.g. \
        ``/data/user/<userid>/<packagename>/shared_prefs/<AppName>``
        """
        return self._append_app_name_and_version(cast(str, _android_folder()), "shared_prefs")

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `user_config_dir`"""
        return self.user_config_dir

    @property
    def user_cache_dir(self) -> str:
        """:return: cache directory tied to the user, e.g.,``/data/user/<userid>/<packagename>/cache/<AppName>``"""
        return self._append_app_name_and_version(cast(str, _android_folder()), "cache")

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, same as `user_cache_dir`"""
        return self.user_cache_dir

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """
        :return: log directory tied to the user, same as `user_cache_dir` if not opinionated else ``log`` in it,
          e.g. ``/data/user/<userid>/<packagename>/cache/<AppName>/log``
        """
        path = self.user_cache_dir
        if self.opinion:
            path = os.path.join(path, "log")  # noqa: PTH118
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user e.g. ``/storage/emulated/0/Documents``"""
        return _android_documents_folder()

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user e.g. ``/storage/emulated/0/Downloads``"""
        return _android_downloads_folder()

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user e.g. ``/storage/emulated/0/Pictures``"""
        return _android_pictures_folder()

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user e.g. ``/storage/emulated/0/DCIM/Camera``"""
        return _android_videos_folder()

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user e.g. ``/storage/emulated/0/Music``"""
        return _android_music_folder()

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user e.g. ``/storage/emulated/0/Desktop``"""
        return "/storage/emulated/0/Desktop"

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, same as `user_cache_dir` if not opinionated else ``tmp`` in it,
          e.g. ``/data/user/<userid>/<packagename>/cache/<AppName>/tmp``
        """
        path = self.user_cache_dir
        if self.opinion:
            path = os.path.join(path, "tmp")  # noqa: PTH118
        return path

    @property
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


@lru_cache(maxsize=1)
def _android_folder() -> str | None:  # noqa: C901
    """:return: base folder for the Android OS or None if it cannot be found"""
    result: str | None = None
    # type checker isn't happy with our "import android", just don't do this when type checking see
    # https://stackoverflow.com/a/61394121
    if not TYPE_CHECKING:
        try:
            # First try to get a path to android app using python4android (if available)...
            from android import mActivity  # noqa: PLC0415

            context = cast("android.content.Context", mActivity.getApplicationContext())  # noqa: F821
            result = context.getFilesDir().getParentFile().getAbsolutePath()
        except Exception:  # noqa: BLE001
            result = None
    if result is None:
        try:
            # ...and fall back to using plain pyjnius, if python4android isn't available or doesn't deliver any useful
            # result...
            from jnius import autoclass  # noqa: PLC0415

            context = autoclass("android.content.Context")
            result = context.getFilesDir().getParentFile().getAbsolutePath()
        except Exception:  # noqa: BLE001
            result = None
    if result is None:
        # and if that fails, too, find an android folder looking at path on the sys.path
        # warning: only works for apps installed under /data, not adopted storage etc.
        pattern = re.compile(r"/data/(data|user/\d+)/(.+)/files")
        for path in sys.path:
            if pattern.match(path):
                result = path.split("/files")[0]
                break
        else:
            result = None
    if result is None:
        # one last try: find an android folder looking at path on the sys.path taking adopted storage paths into
        # account
        pattern = re.compile(r"/mnt/expand/[a-fA-F0-9-]{36}/(data|user/\d+)/(.+)/files")
        for path in sys.path:
            if pattern.match(path):
                result = path.split("/files")[0]
                break
        else:
            result = None
    return result


@lru_cache(maxsize=1)
def _android_documents_folder() -> str:
    """:return: documents folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        documents_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DOCUMENTS).getAbsolutePath()
    except Exception:  # noqa: BLE001
        documents_dir = "/storage/emulated/0/Documents"

    return documents_dir


@lru_cache(maxsize=1)
def _android_downloads_folder() -> str:
    """:return: downloads folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        downloads_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DOWNLOADS).getAbsolutePath()
    except Exception:  # noqa: BLE001
        downloads_dir = "/storage/emulated/0/Downloads"

    return downloads_dir


@lru_cache(maxsize=1)
def _android_pictures_folder() -> str:
    """:return: pictures folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        pictures_dir: str = context.getExternalFilesDir(environment.DIRECTORY_PICTURES).getAbsolutePath()
    except Exception:  # noqa: BLE001
        pictures_dir = "/storage/emulated/0/Pictures"

    return pictures_dir


@lru_cache(maxsize=1)
def _android_videos_folder() -> str:
    """:return: videos folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        videos_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DCIM).getAbsolutePath()
    except Exception:  # noqa: BLE001
        videos_dir = "/storage/emulated/0/DCIM/Camera"

    return videos_dir


@lru_cache(maxsize=1)
def _android_music_folder() -> str:
    """:return: music folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        music_dir: str = context.getExternalFilesDir(environment.DIRECTORY_MUSIC).getAbsolutePath()
    except Exception:  # noqa: BLE001
        music_dir = "/storage/emulated/0/Music"

    return music_dir


__all__ = [
    "Android",
]

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\arturo.py ===
"""
    pygments.lexers.arturo
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Arturo language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups, do_insertions, include, \
    this, using, words
from pygments.token import Comment, Error, Keyword, Name, Number, Operator, \
    Punctuation, String, Text

from pygments.util import ClassNotFound, get_bool_opt

__all__ = ['ArturoLexer']


class ArturoLexer(RegexLexer):
    """
    For Arturo source code.

    See `Arturo's Github <https://github.com/arturo-lang/arturo>`_
    and `Arturo's Website <https://arturo-lang.io/>`_.
    """

    name = 'Arturo'
    aliases = ['arturo', 'art']
    filenames = ['*.art']
    url = 'https://arturo-lang.io/'
    version_added = '2.14'

    def __init__(self, **options):
        self.handle_annotateds = get_bool_opt(options, 'handle_annotateds',
                                              True)
        RegexLexer.__init__(self, **options)

    def handle_annotated_strings(self, match):
        """Adds syntax from another languages inside annotated strings

        match args:
            1:open_string,
            2:exclamation_mark,
            3:lang_name,
            4:space_or_newline,
            5:code,
            6:close_string
        """
        from pygments.lexers import get_lexer_by_name

        # Header's section
        yield match.start(1), String.Double,   match.group(1)
        yield match.start(2), String.Interpol, match.group(2)
        yield match.start(3), String.Interpol, match.group(3)
        yield match.start(4), Text.Whitespace, match.group(4)

        lexer = None
        if self.handle_annotateds:
            try:
                lexer = get_lexer_by_name(match.group(3).strip())
            except ClassNotFound:
                pass
        code = match.group(5)

        if lexer is None:
            yield match.group(5), String, code
        else:
            yield from do_insertions([], lexer.get_tokens_unprocessed(code))

        yield match.start(6), String.Double, match.group(6)

    tokens = {
        'root': [
            (r';.*?$', Comment.Single),
            (r'^((\s#!)|(#!)).*?$', Comment.Hashbang),

            # Constants
            (words(('false', 'true', 'maybe'),      # boolean
                   suffix=r'\b'), Name.Constant),
            (words(('this', 'init'),                # class related keywords
                   prefix=r'\b', suffix=r'\b\??:?'), Name.Builtin.Pseudo),
            (r'`.`', String.Char),                  # character
            (r'\\\w+\b\??:?', Name.Property),       # array index
            (r'#\w+', Name.Constant),               # color
            (r'\b[0-9]+\.[0-9]+', Number.Float),    # float
            (r'\b[0-9]+', Number.Integer),          # integer
            (r'\w+\b\??:', Name.Label),             # label
            # Note: Literals can be labeled too
            (r'\'(?:\w+\b\??:?)', Keyword.Declaration),  # literal
            (r'\:\w+', Keyword.Type),               # type
            # Note: Attributes can be labeled too
            (r'\.\w+\??:?', Name.Attribute),        # attributes

            # Switch structure
            (r'(\()(.*?)(\)\?)',
             bygroups(Punctuation, using(this), Punctuation)),

            # Single Line Strings
            (r'"',   String.Double, 'inside-simple-string'),
            (r'»',   String.Single, 'inside-smart-string'),
            (r'«««', String.Double, 'inside-safe-string'),
            (r'\{\/', String.Single, 'inside-regex-string'),

            # Multi Line Strings
            (r'\{\:', String.Double, 'inside-curly-verb-string'),
            (r'(\{)(\!)(\w+)(\s|\n)([\w\W]*?)(^\})', handle_annotated_strings),
            (r'\{', String.Single, 'inside-curly-string'),
            (r'\-{3,}', String.Single, 'inside-eof-string'),

            include('builtin-functions'),

            # Operators
            (r'[()[\],]', Punctuation),
            (words(('->', '==>', '|', '::', '@', '#',  # sugar syntax
                    '$', '&', '!', '!!', './')), Name.Decorator),
            (words(('<:', ':>', ':<', '>:', '<\\', '<>', '<', '>',
                    'ø', '∞',
                    '+', '-', '*', '~', '=', '^', '%', '/', '//',
                    '==>', '<=>', '<==>',
                    '=>>', '<<=>>', '<<==>>',
                    '-->', '<->', '<-->',
                    '=|', '|=', '-:', ':-',
                    '_', '.', '..', '\\')), Operator),

            (r'\b\w+', Name),
            (r'\s+', Text.Whitespace),
            (r'.+$', Error),
        ],

        'inside-interpol': [
            (r'\|', String.Interpol, '#pop'),
            (r'[^|]+', using(this)),
        ],
        'inside-template': [
            (r'\|\|\>', String.Interpol, '#pop'),
            (r'[^|]+', using(this)),
        ],
        'string-escape': [
            (words(('\\\\', '\\n', '\\t', '\\"')), String.Escape),
        ],

        'inside-simple-string': [
            include('string-escape'),
            (r'\|', String.Interpol, 'inside-interpol'),        # Interpolation
            (r'\<\|\|', String.Interpol, 'inside-template'),    # Templates
            (r'"', String.Double, '#pop'),   # Closing Quote
            (r'[^|"]+', String)              # String Content
        ],
        'inside-smart-string': [
            include('string-escape'),
            (r'\|', String.Interpol, 'inside-interpol'),        # Interpolation
            (r'\<\|\|', String.Interpol, 'inside-template'),    # Templates
            (r'\n', String.Single, '#pop'),  # Closing Quote
            (r'[^|\n]+', String)             # String Content
        ],
        'inside-safe-string': [
            include('string-escape'),
            (r'\|', String.Interpol, 'inside-interpol'),        # Interpolation
            (r'\<\|\|', String.Interpol, 'inside-template'),    # Templates
            (r'»»»', String.Double, '#pop'),    # Closing Quote
            (r'[^|»]+', String)                 # String Content
        ],
        'inside-regex-string': [
            (r'\\[sSwWdDbBZApPxucItnvfr0]+', String.Escape),
            (r'\|', String.Interpol, 'inside-interpol'),        # Interpolation
            (r'\<\|\|', String.Interpol, 'inside-template'),    # Templates
            (r'\/\}', String.Single, '#pop'),  # Closing Quote
            (r'[^|\/]+', String.Regex),        # String Content
        ],
        'inside-curly-verb-string': [
            include('string-escape'),
            (r'\|', String.Interpol, 'inside-interpol'),        # Interpolation
            (r'\<\|\|', String.Interpol, 'inside-template'),    # Templates
            (r'\:\}', String.Double, '#pop'),  # Closing Quote
            (r'[^|<:]+', String),              # String Content
        ],
        'inside-curly-string': [
            include('string-escape'),
            (r'\|', String.Interpol, 'inside-interpol'),        # Interpolation
            (r'\<\|\|', String.Interpol, 'inside-template'),    # Templates
            (r'\}', String.Single, '#pop'),   # Closing Quote
            (r'[^|<}]+', String),             # String Content
        ],
        'inside-eof-string': [
            include('string-escape'),
            (r'\|', String.Interpol, 'inside-interpol'),        # Interpolation
            (r'\<\|\|', String.Interpol, 'inside-template'),    # Templates
            (r'\Z', String.Single, '#pop'),   # Closing Quote
            (r'[^|<]+', String),              # String Content
        ],

        'builtin-functions': [
            (words((
                'all', 'and', 'any', 'ascii', 'attr', 'attribute',
                'attributeLabel', 'binary', 'block' 'char', 'contains',
                'database', 'date', 'dictionary', 'empty', 'equal', 'even',
                'every', 'exists', 'false', 'floatin', 'function', 'greater',
                'greaterOrEqual', 'if', 'in', 'inline', 'integer', 'is',
                'key', 'label', 'leap', 'less', 'lessOrEqual', 'literal',
                'logical', 'lower', 'nand', 'negative', 'nor', 'not',
                'notEqual', 'null', 'numeric', 'odd', 'or', 'path',
                'pathLabel', 'positive', 'prefix', 'prime', 'set', 'some',
                'sorted', 'standalone', 'string', 'subset', 'suffix',
                'superset', 'ymbol', 'true', 'try', 'type', 'unless', 'upper',
                'when', 'whitespace', 'word', 'xnor', 'xor', 'zero',
            ), prefix=r'\b', suffix=r'\b\?'), Name.Builtin),
            (words((
                'abs', 'acos', 'acosh', 'acsec', 'acsech', 'actan', 'actanh',
                'add', 'after', 'alphabet', 'and', 'angle', 'append', 'arg',
                'args', 'arity', 'array', 'as', 'asec', 'asech', 'asin',
                'asinh', 'atan', 'atan2', 'atanh', 'attr', 'attrs', 'average',
                'before', 'benchmark', 'blend', 'break', 'builtins1',
                'builtins2', 'call', 'capitalize', 'case', 'ceil', 'chop',
                'chunk', 'clear', 'close', 'cluster', 'color', 'combine',
                'conj', 'continue', 'copy', 'cos', 'cosh', 'couple', 'csec',
                'csech', 'ctan', 'ctanh', 'cursor', 'darken', 'dec', 'decode',
                'decouple', 'define', 'delete', 'desaturate', 'deviation',
                'dictionary', 'difference', 'digest', 'digits', 'div', 'do',
                'download', 'drop', 'dup', 'e', 'else', 'empty', 'encode',
                'ensure', 'env', 'epsilon', 'escape', 'execute', 'exit', 'exp',
                'extend', 'extract', 'factors', 'false', 'fdiv', 'filter',
                'first', 'flatten', 'floor', 'fold', 'from', 'function',
                'gamma', 'gcd', 'get', 'goto', 'hash', 'help', 'hypot', 'if',
                'in', 'inc', 'indent', 'index', 'infinity', 'info', 'input',
                'insert', 'inspect', 'intersection', 'invert', 'join', 'keys',
                'kurtosis', 'last', 'let', 'levenshtein', 'lighten', 'list',
                'ln', 'log', 'loop', 'lower', 'mail', 'map', 'match', 'max',
                'maybe', 'median', 'min', 'mod', 'module', 'mul', 'nand',
                'neg', 'new', 'nor', 'normalize', 'not', 'now', 'null', 'open',
                'or', 'outdent', 'pad', 'panic', 'path', 'pause',
                'permissions', 'permutate', 'pi', 'pop', 'pow', 'powerset',
                'powmod', 'prefix', 'print', 'prints', 'process', 'product',
                'query', 'random', 'range', 'read', 'relative', 'remove',
                'rename', 'render', 'repeat', 'replace', 'request', 'return',
                'reverse', 'round', 'sample', 'saturate', 'script', 'sec',
                'sech', 'select', 'serve', 'set', 'shl', 'shr', 'shuffle',
                'sin', 'sinh', 'size', 'skewness', 'slice', 'sort', 'split',
                'sqrt', 'squeeze', 'stack', 'strip', 'sub', 'suffix', 'sum',
                'switch', 'symbols', 'symlink', 'sys', 'take', 'tan', 'tanh',
                'terminal', 'to', 'true', 'truncate', 'try', 'type', 'union',
                'unique', 'unless', 'until', 'unzip', 'upper', 'values', 'var',
                'variance', 'volume', 'webview', 'while', 'with', 'wordwrap',
                'write', 'xnor', 'xor', 'zip'
            ), prefix=r'\b', suffix=r'\b'), Name.Builtin)
        ],

    }

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\platformdirs\android.py ===
"""Android."""

from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from typing import TYPE_CHECKING, cast

from .api import PlatformDirsABC


class Android(PlatformDirsABC):
    """
    Follows the guidance `from here <https://android.stackexchange.com/a/216132>`_.

    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`, `version
    <platformdirs.api.PlatformDirsABC.version>`, `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """:return: data directory tied to the user, e.g. ``/data/user/<userid>/<packagename>/files/<AppName>``"""
        return self._append_app_name_and_version(cast(str, _android_folder()), "files")

    @property
    def site_data_dir(self) -> str:
        """:return: data directory shared by users, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_config_dir(self) -> str:
        """
        :return: config directory tied to the user, e.g. \
        ``/data/user/<userid>/<packagename>/shared_prefs/<AppName>``
        """
        return self._append_app_name_and_version(cast(str, _android_folder()), "shared_prefs")

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `user_config_dir`"""
        return self.user_config_dir

    @property
    def user_cache_dir(self) -> str:
        """:return: cache directory tied to the user, e.g.,``/data/user/<userid>/<packagename>/cache/<AppName>``"""
        return self._append_app_name_and_version(cast(str, _android_folder()), "cache")

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, same as `user_cache_dir`"""
        return self.user_cache_dir

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """
        :return: log directory tied to the user, same as `user_cache_dir` if not opinionated else ``log`` in it,
          e.g. ``/data/user/<userid>/<packagename>/cache/<AppName>/log``
        """
        path = self.user_cache_dir
        if self.opinion:
            path = os.path.join(path, "log")  # noqa: PTH118
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user e.g. ``/storage/emulated/0/Documents``"""
        return _android_documents_folder()

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user e.g. ``/storage/emulated/0/Downloads``"""
        return _android_downloads_folder()

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user e.g. ``/storage/emulated/0/Pictures``"""
        return _android_pictures_folder()

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user e.g. ``/storage/emulated/0/DCIM/Camera``"""
        return _android_videos_folder()

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user e.g. ``/storage/emulated/0/Music``"""
        return _android_music_folder()

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user e.g. ``/storage/emulated/0/Desktop``"""
        return "/storage/emulated/0/Desktop"

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, same as `user_cache_dir` if not opinionated else ``tmp`` in it,
          e.g. ``/data/user/<userid>/<packagename>/cache/<AppName>/tmp``
        """
        path = self.user_cache_dir
        if self.opinion:
            path = os.path.join(path, "tmp")  # noqa: PTH118
        return path

    @property
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


@lru_cache(maxsize=1)
def _android_folder() -> str | None:  # noqa: C901, PLR0912
    """:return: base folder for the Android OS or None if it cannot be found"""
    result: str | None = None
    # type checker isn't happy with our "import android", just don't do this when type checking see
    # https://stackoverflow.com/a/61394121
    if not TYPE_CHECKING:
        try:
            # First try to get a path to android app using python4android (if available)...
            from android import mActivity  # noqa: PLC0415

            context = cast("android.content.Context", mActivity.getApplicationContext())  # noqa: F821
            result = context.getFilesDir().getParentFile().getAbsolutePath()
        except Exception:  # noqa: BLE001
            result = None
    if result is None:
        try:
            # ...and fall back to using plain pyjnius, if python4android isn't available or doesn't deliver any useful
            # result...
            from jnius import autoclass  # noqa: PLC0415

            context = autoclass("android.content.Context")
            result = context.getFilesDir().getParentFile().getAbsolutePath()
        except Exception:  # noqa: BLE001
            result = None
    if result is None:
        # and if that fails, too, find an android folder looking at path on the sys.path
        # warning: only works for apps installed under /data, not adopted storage etc.
        pattern = re.compile(r"/data/(data|user/\d+)/(.+)/files")
        for path in sys.path:
            if pattern.match(path):
                result = path.split("/files")[0]
                break
        else:
            result = None
    if result is None:
        # one last try: find an android folder looking at path on the sys.path taking adopted storage paths into
        # account
        pattern = re.compile(r"/mnt/expand/[a-fA-F0-9-]{36}/(data|user/\d+)/(.+)/files")
        for path in sys.path:
            if pattern.match(path):
                result = path.split("/files")[0]
                break
        else:
            result = None
    return result


@lru_cache(maxsize=1)
def _android_documents_folder() -> str:
    """:return: documents folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        documents_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DOCUMENTS).getAbsolutePath()
    except Exception:  # noqa: BLE001
        documents_dir = "/storage/emulated/0/Documents"

    return documents_dir


@lru_cache(maxsize=1)
def _android_downloads_folder() -> str:
    """:return: downloads folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        downloads_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DOWNLOADS).getAbsolutePath()
    except Exception:  # noqa: BLE001
        downloads_dir = "/storage/emulated/0/Downloads"

    return downloads_dir


@lru_cache(maxsize=1)
def _android_pictures_folder() -> str:
    """:return: pictures folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        pictures_dir: str = context.getExternalFilesDir(environment.DIRECTORY_PICTURES).getAbsolutePath()
    except Exception:  # noqa: BLE001
        pictures_dir = "/storage/emulated/0/Pictures"

    return pictures_dir


@lru_cache(maxsize=1)
def _android_videos_folder() -> str:
    """:return: videos folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        videos_dir: str = context.getExternalFilesDir(environment.DIRECTORY_DCIM).getAbsolutePath()
    except Exception:  # noqa: BLE001
        videos_dir = "/storage/emulated/0/DCIM/Camera"

    return videos_dir


@lru_cache(maxsize=1)
def _android_music_folder() -> str:
    """:return: music folder for the Android OS"""
    # Get directories with pyjnius
    try:
        from jnius import autoclass  # noqa: PLC0415

        context = autoclass("android.content.Context")
        environment = autoclass("android.os.Environment")
        music_dir: str = context.getExternalFilesDir(environment.DIRECTORY_MUSIC).getAbsolutePath()
    except Exception:  # noqa: BLE001
        music_dir = "/storage/emulated/0/Music"

    return music_dir


__all__ = [
    "Android",
]

# === NexusCore/evaluation\evalplus\tools\tsr\minimization.py ===
import argparse
import json
import os
import pickle
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from rich.progress import track

from evalplus.data import write_jsonl
from tools.tsr.coverage_init import collect_coverage_info
from tools.tsr.mutation_init import collect_mutation_info
from tools.tsr.sample_init import collect_sample_info
from tools.tsr.utils import get_problems, get_task_ids, to_path


def global_util_init(dataset: str):
    global problems
    global task_ids
    global problem_count
    problems = get_problems(dataset)
    task_ids = get_task_ids(dataset)
    problem_count = len(problems)


###########################
# Greedy Min Set Covering #
###########################


def merge_set_cover(*args) -> Dict[str, List[str]]:
    merged_set_cover = {task_id: [] for task_id in task_ids}
    for set_cover_dict in args:
        for task_id, plus_tests in set_cover_dict.items():
            for plus_test in plus_tests:
                if plus_test not in merged_set_cover[task_id]:
                    merged_set_cover[task_id].append(plus_test)
    return merged_set_cover


def greedy_cover(
    task_id: str, tests: Dict[str, List[Any]], exclude_model: str
) -> Tuple[str, List[str]]:
    q, U = [], set()
    for test_name, test_cover in tests.items():
        cover_set = set()
        for model_path, i_code in test_cover:
            if exclude_model not in model_path:
                cover_set.add((model_path, i_code))
        q.append((test_name, cover_set))
        U = U.union(cover_set)
    # Greedy algorithm for min set cover
    min_cover = []
    while len(U) > 0:
        max_uncover_set, max_test_name = {}, ""
        for test_name, cover_set in q:
            if len(cover_set) > len(max_uncover_set):
                max_uncover_set = cover_set
                max_test_name = test_name
        min_cover.append(max_test_name)
        U = U - max_uncover_set
        qq = []
        for test_name, cover_set in q:
            new_cover_set = U.intersection(cover_set)
            if len(new_cover_set) != 0:
                qq.append((test_name, new_cover_set))
        q = qq
    return task_id, min_cover


def parallel_greedy_cover(
    info_dict: Optional[Dict[str, Dict[str, List[Any]]]],
    exclude_model: str,
    type: str,
    **kwargs,
) -> Dict[str, List[str]]:
    plus_tests = {task_id: [] for task_id in task_ids}

    with ProcessPoolExecutor(max_workers=32) as executor:
        futures = []
        for task_id in task_ids:
            if type == "sample":
                path_task_id = to_path(task_id)
                sample_dir = kwargs["sample_dir"]
                with open(os.path.join(sample_dir, f"{path_task_id}.pkl"), "rb") as f:
                    td = pickle.load(f)
                args = (task_id, td, exclude_model)
            else:
                args = (task_id, info_dict[task_id], exclude_model)
            futures.append(executor.submit(greedy_cover, *args))
        for future in track(as_completed(futures), f"min set cover :: {type}"):
            task_id, min_cover = future.result()
            plus_tests[task_id] = min_cover

    return plus_tests


#####################
# Collect Set Cover #
#####################


def get_coverage_set_cover(
    coverage_dir: str, exclude_model: str, dataset: str
) -> Dict[str, List[str]]:
    coverage_info_dict = collect_coverage_info(coverage_dir, dataset)
    return parallel_greedy_cover(coverage_info_dict, exclude_model, "coverage")


def get_mutation_set_cover(
    mutation_dir: str, exclude_model: str, dataset: str
) -> Dict[str, List[str]]:
    mutation_info_dict = collect_mutation_info(
        os.path.join(mutation_dir, "eval_results.json"), dataset
    )
    return parallel_greedy_cover(mutation_info_dict, exclude_model, "mutation")


def get_sample_set_cover(
    sample_dir: str, sample_eval_dir: str, exclude_model: str, dataset: str
) -> Dict[str, List[str]]:
    collect_sample_info(sample_dir, sample_eval_dir, dataset)
    return parallel_greedy_cover(None, exclude_model, "sample", sample_dir=sample_dir)


#################
# pass@1 greedy #
#################


def compute_avg_test(set_cover_info: Dict[str, List[str]]) -> float:
    sum_tests = sum(
        len(problems[task_id]["base_input"]) + len(set_cover_info[task_id])
        for task_id in task_ids
    )
    return sum_tests / problem_count


def gen_report(set_cover_info: Dict[str, List[str]], sample_eval_dir: str, model: str):
    tsr_dict = {"ntests": compute_avg_test(set_cover_info), "pass@1": 0}
    model_path = os.path.join(sample_eval_dir, f"{model}_temp_0.0", "eval_results.json")
    with open(model_path, "r") as f:
        mdict = json.load(f)
    correct_cnt = 0
    for task_id in task_ids:
        legacy_task_id = task_id
        if legacy_task_id not in mdict["eval"]:
            legacy_task_id = legacy_task_id.replace("/", "_")
        if mdict["eval"][legacy_task_id]["base"][0][0] != "success":
            continue
        correct = True
        for plus_id in set_cover_info[task_id]:
            index = int(plus_id.split("_")[-1])
            if mdict["eval"][legacy_task_id]["plus"][0][1][index] == False:
                correct = False
                break
        if correct:
            correct_cnt += 1
    tsr_dict["pass@1"] = correct_cnt / problem_count
    return tsr_dict


def dump_humaneval_plus_mini(set_cover_info: Dict[str, List[str]], mini_path: str):
    new_problems = []
    for task_id in task_ids:
        otask = problems[task_id]
        task = {
            "task_id": task_id,
            "prompt": otask["prompt"],
            "contract": otask["contract"],
            "canonical_solution": otask["canonical_solution"],
            "entry_point": otask["entry_point"],
            "base_input": otask["base_input"],
            "plus_input": [],
            "atol": otask["atol"],
        }
        for plus_test in set_cover_info[task_id]:
            index = int(plus_test.split("_")[-1])
            task["plus_input"].append(otask["plus_input"][index])
        new_problems.append(deepcopy(task))
    write_jsonl(os.path.join(mini_path, "HumanEvalPlus-Mini.jsonl"), new_problems)


def main(flags):
    coverage_dir = os.path.join(flags.report_dir, "coverage_cache")
    mutation_dir = os.path.join(flags.report_dir, "mutation_cache")
    sample_dir = os.path.join(flags.report_dir, "sample_cache")
    os.makedirs(flags.report_dir, exist_ok=True)

    exclude_model: str = flags.model
    if exclude_model.endswith("b"):  # format: model_name + parameter size
        exclude_model = "".join(exclude_model.split("-")[:-1])

    coverage_set_cover = get_coverage_set_cover(
        coverage_dir, exclude_model, flags.dataset
    )
    mutation_set_cover = get_mutation_set_cover(
        mutation_dir, exclude_model, flags.dataset
    )
    sample_set_cover = get_sample_set_cover(
        sample_dir, flags.sample_eval_dir, exclude_model, flags.dataset
    )
    merged_set_cover = merge_set_cover(
        coverage_set_cover, mutation_set_cover, sample_set_cover
    )

    if flags.model != "ALL":
        final_report = dict()
        # Stage 1: Coverage min set cover
        final_report["coverage"] = gen_report(
            coverage_set_cover, flags.sample_eval_dir, flags.model
        )
        # Stage 2: Mutation min set cover
        final_report["mutation"] = gen_report(
            mutation_set_cover, flags.sample_eval_dir, flags.model
        )
        # Stage 3: Sampling min set cover
        final_report["sample"] = gen_report(
            sample_set_cover, flags.sample_eval_dir, flags.model
        )
        # Stage 4: All
        final_report["full"] = gen_report(
            merged_set_cover, flags.sample_eval_dir, flags.model
        )
        with open(
            os.path.join(flags.report_dir, f"report_{flags.model}.json"), "w"
        ) as f:
            json.dump(final_report, f, indent=4)
    else:
        dump_humaneval_plus_mini(merged_set_cover, flags.mini_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=str, help="Model for testing")
    parser.add_argument("--dataset", type=str, choices=["humaneval", "mbpp"])
    parser.add_argument(
        "--report_dir", type=str, help="Path to JSON report and cache files"
    )
    parser.add_argument(
        "--sample_eval_dir", type=str, help="Path to sample evaluation files"
    )
    parser.add_argument("--mini_path", type=str, help="Path to Mini Dataset")
    args = parser.parse_args()

    global_util_init(args.dataset)
    main(args)

# === NexusCore/openenv\Lib\site-packages\html2image\cli.py ===
""" html2image Command Line Interface
"""

import argparse
import os
from html2image import Html2Image


def size_type(string):
    try:
        width, height = map(int, string.split(','))
        if width <= 0 or height <= 0:
            raise argparse.ArgumentTypeError(
                'Width and height must be positive integers.'
            )
        return width, height
    except ValueError:  # incorrect number of values
        raise argparse.ArgumentTypeError(
            f"Size should be W,H (e.g., 1920,1080), instead got '{string}'"
        )
    except Exception as e:  # unexpected errors
        raise argparse.ArgumentTypeError(f"Invalid size format '{string}': {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate images from HTML/CSS or URLs using the html2image library.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Html2Image instantiation arguments
    group_hti_init = parser.add_argument_group('Html2Image Instance Configuration')
    group_hti_init.add_argument(
        '--output-path', '-o',
        default=os.getcwd(),
        help='Directory to save screenshots.'
    )

    # TODO : this list is duplicated from browser_map in html2image.py
    browser_choices = [
        'chrome', 'chromium', 'google-chrome', 'google-chrome-stable',
        'googlechrome', 'edge', 'chrome-cdp', 'chromium-cdp'
    ]
    group_hti_init.add_argument(
        '--browser',
        default='chrome',
        choices=browser_choices,
        help='Browser to use for screenshots.'
    )
    group_hti_init.add_argument(
        '--browser-executable',
        default=None,
        help='Path to the browser executable. Auto-detected if not provided.'
    )
    group_hti_init.add_argument(
        '--cdp-port',
        type=int,
        default=None,
        help='CDP port for CDP-enabled browsers (e.g., chrome-cdp). Default is library-dependent.'
    )
    group_hti_init.add_argument(
        '--temp-path',
        default=None,
        help="Directory for temporary files. Defaults to system temp directory within an 'html2image' subfolder."
    )
    group_hti_init.add_argument(
        '--keep-temp-files',
        action='store_true',
        help='Do not delete temporary files after screenshot generation.'
    )
    group_hti_init.add_argument(
        '--custom-flags',
        nargs='*', 
        default=[],  # If not provided, defaults are used
        help="Custom flags to pass to the browser (e.g., '--no-sandbox' '--disable-gpu'). If provided, these flags will be used."
    )

    # Screenshot sources arguments
    group_sources = parser.add_argument_group('Screenshot Sources (at least one type is required)')
    group_sources.add_argument(
        '--url', '-U',
        nargs='*', default=[],
        metavar='URL',
        help='URL(s) to screenshot.'
    )
    group_sources.add_argument(
        '--html-file',
        nargs='*', default=[],
        metavar='FILE',
        help='HTML file(s) to screenshot.'
    )
    group_sources.add_argument(
        '--html-string',
        nargs='*', default=[],
        metavar='STRING',
        help='HTML string(s) to screenshot.'
    )
    group_sources.add_argument(
        '--css-file',
        nargs='*', default=[],
        metavar='FILE',
        help='CSS file(s) to load. Used by HTML files or applied with HTML strings.'
    )
    group_sources.add_argument(
        '--css-string',
        nargs='*', default=[],
        metavar='STRING',
        help='CSS string(s) to apply. Combined and used with HTML strings.'
    )
    group_sources.add_argument(
        '--other-file', '-O',
        nargs='*', default=[],
        metavar='FILE',
        help='Other file(s) to screenshot (e.g., SVG).'
    )

    # Screenshot output control arguments
    group_output_ctrl = parser.add_argument_group('Screenshot Output Options')
    group_output_ctrl.add_argument(
        '--save-as', '-S',
        nargs='*', default=None,  # html2image handles default naming if only one source
        metavar='FILENAME',
        help='Filename(s) for the output images. If not provided or fewer names than items, names are auto-generated.'
    )
    group_output_ctrl.add_argument(
        '--size', '-s',
        nargs='*', default=[],
        type=size_type,
        metavar='W,H',
        help="Size(s) for screenshots as W,H. If one W,H pair is given, it applies to all. If multiple, they apply to corresponding screenshots; if fewer pairs than items, the last is repeated. If omitted, (1920,1080) is used."
    )

    # General arguments
    group_general = parser.add_argument_group('General Options')
    group_general.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output from browsers (sets disable_logging=True).'
    )
    group_general.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output, including browser commands if supported by the browser handler.'
    )

    args = parser.parse_args()

    # Prepare Html2Image()
    hti_kwargs = {
        'output_path': args.output_path,
        'browser': args.browser,
        'browser_executable': args.browser_executable,
        'custom_flags': [cf.replace("'", '') for cf in args.custom_flags],
        'disable_logging': args.quiet,
        'temp_path': args.temp_path,
        'keep_temp_files': args.keep_temp_files,
    }

    # Only pass cdp_port if a CDP browser is likely selected and port is given
    if args.cdp_port and 'cdp' in args.browser.lower():
        hti_kwargs['browser_cdp_port'] = args.cdp_port
    elif args.cdp_port:
        print(
            f"Warning: --cdp-port ({args.cdp_port}) was specified, but the selected browser ('{args.browser}') might not be a CDP browser."
        )

    try:
        # Filter out None values so defaults are used for those specific kwargs
        # keep_temp_files and disable_logging are bools, always pass them.
        # custom_flags should be passed even if None, so Html2Image can use its defaults or an empty list.
        active_hti_kwargs = {
            k: v for k, v in hti_kwargs.items()
            if v is not None or k in ['keep_temp_files', 'disable_logging', 'custom_flags']
        }
        hti = Html2Image(**active_hti_kwargs)

    except Exception as e:
        print(f'Error: Could not instantiate Html2Image: {e}')
        exit(1)

    if args.verbose:
        # The `print_command` attribute is specific to ChromiumHeadless.
        # CDP browsers print logs internally.
        if hasattr(hti.browser, 'print_command'):
            hti.browser.print_command = True
            print('Verbose mode: Browser commands will be printed for compatible handlers.')
        else:
            print('Verbose mode enabled. Note: Detailed browser command printing depends on the selected browser handler.')

    has_sources = any([
        args.url, args.html_file, args.html_string, args.other_file
    ])

    # Print help message if no sources were passed
    if not has_sources:
        print('Error: No screenshot sources (URL, HTML file/string, other file) provided.')
        parser.print_usage()
        exit(1)

    # Perform screenshot
    screenshot_kwargs = {
        'url': args.url,
        'html_file': args.html_file,
        'html_str': args.html_string,
        'css_file': args.css_file,
        'css_str': args.css_string,
        'other_file': args.other_file,
        'size': args.size,  # Pass the list of sizes directly from the --size CLI arg
    }

    if args.save_as is not None:
        screenshot_kwargs['save_as'] = args.save_as

    try:
        if args.verbose:
            print('--- Html2Image Instance Configuration ---')
            for k, v in active_hti_kwargs.items():
                print(f'  {k}: {v}')
            print('--- Screenshot Call Arguments ---')
            for k, v in screenshot_kwargs.items():
                if v or k == 'size':  # print if list not empty, or always for size
                    print(f'  {k}: {v}')

        paths = hti.screenshot(**screenshot_kwargs)

        if not args.quiet:
            print(f'Successfully created {len(paths)} image(s):')
            for path in paths:
                print(f'  {path}')

    except FileNotFoundError as e:
        print(f'Error: A required file was not found: {e}')
        exit(1)

    except ValueError as e:  # Can be raised by browser screenshot method for bad size etc.
        print(f'Error: Invalid value encountered: {e}')
        exit(1)

    except Exception as e:
        print(f'An unexpected error occurred during screenshotting: {e}')
        if args.verbose:
            import traceback
            traceback.print_exc()
        exit(1)


if __name__ == '__main__':
    main()

# === NexusCore/openenv\Lib\site-packages\httpx\_config.py ===
from __future__ import annotations

import os
import typing

from ._models import Headers
from ._types import CertTypes, HeaderTypes, TimeoutTypes
from ._urls import URL

if typing.TYPE_CHECKING:
    import ssl  # pragma: no cover

__all__ = ["Limits", "Proxy", "Timeout", "create_ssl_context"]


class UnsetType:
    pass  # pragma: no cover


UNSET = UnsetType()


def create_ssl_context(
    verify: ssl.SSLContext | str | bool = True,
    cert: CertTypes | None = None,
    trust_env: bool = True,
) -> ssl.SSLContext:
    import ssl
    import warnings

    import certifi

    if verify is True:
        if trust_env and os.environ.get("SSL_CERT_FILE"):  # pragma: nocover
            ctx = ssl.create_default_context(cafile=os.environ["SSL_CERT_FILE"])
        elif trust_env and os.environ.get("SSL_CERT_DIR"):  # pragma: nocover
            ctx = ssl.create_default_context(capath=os.environ["SSL_CERT_DIR"])
        else:
            # Default case...
            ctx = ssl.create_default_context(cafile=certifi.where())
    elif verify is False:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    elif isinstance(verify, str):  # pragma: nocover
        message = (
            "`verify=<str>` is deprecated. "
            "Use `verify=ssl.create_default_context(cafile=...)` "
            "or `verify=ssl.create_default_context(capath=...)` instead."
        )
        warnings.warn(message, DeprecationWarning)
        if os.path.isdir(verify):
            return ssl.create_default_context(capath=verify)
        return ssl.create_default_context(cafile=verify)
    else:
        ctx = verify

    if cert:  # pragma: nocover
        message = (
            "`cert=...` is deprecated. Use `verify=<ssl_context>` instead,"
            "with `.load_cert_chain()` to configure the certificate chain."
        )
        warnings.warn(message, DeprecationWarning)
        if isinstance(cert, str):
            ctx.load_cert_chain(cert)
        else:
            ctx.load_cert_chain(*cert)

    return ctx


class Timeout:
    """
    Timeout configuration.

    **Usage**:

    Timeout(None)               # No timeouts.
    Timeout(5.0)                # 5s timeout on all operations.
    Timeout(None, connect=5.0)  # 5s timeout on connect, no other timeouts.
    Timeout(5.0, connect=10.0)  # 10s timeout on connect. 5s timeout elsewhere.
    Timeout(5.0, pool=None)     # No timeout on acquiring connection from pool.
                                # 5s timeout elsewhere.
    """

    def __init__(
        self,
        timeout: TimeoutTypes | UnsetType = UNSET,
        *,
        connect: None | float | UnsetType = UNSET,
        read: None | float | UnsetType = UNSET,
        write: None | float | UnsetType = UNSET,
        pool: None | float | UnsetType = UNSET,
    ) -> None:
        if isinstance(timeout, Timeout):
            # Passed as a single explicit Timeout.
            assert connect is UNSET
            assert read is UNSET
            assert write is UNSET
            assert pool is UNSET
            self.connect = timeout.connect  # type: typing.Optional[float]
            self.read = timeout.read  # type: typing.Optional[float]
            self.write = timeout.write  # type: typing.Optional[float]
            self.pool = timeout.pool  # type: typing.Optional[float]
        elif isinstance(timeout, tuple):
            # Passed as a tuple.
            self.connect = timeout[0]
            self.read = timeout[1]
            self.write = None if len(timeout) < 3 else timeout[2]
            self.pool = None if len(timeout) < 4 else timeout[3]
        elif not (
            isinstance(connect, UnsetType)
            or isinstance(read, UnsetType)
            or isinstance(write, UnsetType)
            or isinstance(pool, UnsetType)
        ):
            self.connect = connect
            self.read = read
            self.write = write
            self.pool = pool
        else:
            if isinstance(timeout, UnsetType):
                raise ValueError(
                    "httpx.Timeout must either include a default, or set all "
                    "four parameters explicitly."
                )
            self.connect = timeout if isinstance(connect, UnsetType) else connect
            self.read = timeout if isinstance(read, UnsetType) else read
            self.write = timeout if isinstance(write, UnsetType) else write
            self.pool = timeout if isinstance(pool, UnsetType) else pool

    def as_dict(self) -> dict[str, float | None]:
        return {
            "connect": self.connect,
            "read": self.read,
            "write": self.write,
            "pool": self.pool,
        }

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.connect == other.connect
            and self.read == other.read
            and self.write == other.write
            and self.pool == other.pool
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        if len({self.connect, self.read, self.write, self.pool}) == 1:
            return f"{class_name}(timeout={self.connect})"
        return (
            f"{class_name}(connect={self.connect}, "
            f"read={self.read}, write={self.write}, pool={self.pool})"
        )


class Limits:
    """
    Configuration for limits to various client behaviors.

    **Parameters:**

    * **max_connections** - The maximum number of concurrent connections that may be
            established.
    * **max_keepalive_connections** - Allow the connection pool to maintain
            keep-alive connections below this point. Should be less than or equal
            to `max_connections`.
    * **keepalive_expiry** - Time limit on idle keep-alive connections in seconds.
    """

    def __init__(
        self,
        *,
        max_connections: int | None = None,
        max_keepalive_connections: int | None = None,
        keepalive_expiry: float | None = 5.0,
    ) -> None:
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.max_connections == other.max_connections
            and self.max_keepalive_connections == other.max_keepalive_connections
            and self.keepalive_expiry == other.keepalive_expiry
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return (
            f"{class_name}(max_connections={self.max_connections}, "
            f"max_keepalive_connections={self.max_keepalive_connections}, "
            f"keepalive_expiry={self.keepalive_expiry})"
        )


class Proxy:
    def __init__(
        self,
        url: URL | str,
        *,
        ssl_context: ssl.SSLContext | None = None,
        auth: tuple[str, str] | None = None,
        headers: HeaderTypes | None = None,
    ) -> None:
        url = URL(url)
        headers = Headers(headers)

        if url.scheme not in ("http", "https", "socks5", "socks5h"):
            raise ValueError(f"Unknown scheme for proxy URL {url!r}")

        if url.username or url.password:
            # Remove any auth credentials from the URL.
            auth = (url.username, url.password)
            url = url.copy_with(username=None, password=None)

        self.url = url
        self.auth = auth
        self.headers = headers
        self.ssl_context = ssl_context

    @property
    def raw_auth(self) -> tuple[bytes, bytes] | None:
        # The proxy authentication as raw bytes.
        return (
            None
            if self.auth is None
            else (self.auth[0].encode("utf-8"), self.auth[1].encode("utf-8"))
        )

    def __repr__(self) -> str:
        # The authentication is represented with the password component masked.
        auth = (self.auth[0], "********") if self.auth else None

        # Build a nice concise representation.
        url_str = f"{str(self.url)!r}"
        auth_str = f", auth={auth!r}" if auth else ""
        headers_str = f", headers={dict(self.headers)!r}" if self.headers else ""
        return f"Proxy({url_str}{auth_str}{headers_str})"


DEFAULT_TIMEOUT_CONFIG = Timeout(timeout=5.0)
DEFAULT_LIMITS = Limits(max_connections=100, max_keepalive_connections=20)
DEFAULT_MAX_REDIRECTS = 20

# === NexusCore/openenv\Lib\site-packages\setuptools\__init__.py ===
"""Extensions to the 'distutils' for large or complex distributions"""
# mypy: disable_error_code=override
# Command.reinitialize_command has an extra **kw param that distutils doesn't have
# Can't disable on the exact line because distutils doesn't exists on Python 3.12
# and mypy isn't aware of distutils_hack, causing distutils.core.Command to be Any,
# and a [unused-ignore] to be raised on 3.12+

from __future__ import annotations

import functools
import os
import sys
from abc import abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING, TypeVar, overload

sys.path.extend(((vendor_path := os.path.join(os.path.dirname(os.path.dirname(__file__)), 'setuptools', '_vendor')) not in sys.path) * [vendor_path])  # fmt: skip
# workaround for #4476
sys.modules.pop('backports', None)

import _distutils_hack.override  # noqa: F401

from . import logging, monkey
from .depends import Require
from .discovery import PackageFinder, PEP420PackageFinder
from .dist import Distribution
from .extension import Extension
from .version import __version__ as __version__
from .warnings import SetuptoolsDeprecationWarning

import distutils.core

__all__ = [
    'setup',
    'Distribution',
    'Command',
    'Extension',
    'Require',
    'SetuptoolsDeprecationWarning',
    'find_packages',
    'find_namespace_packages',
]

_CommandT = TypeVar("_CommandT", bound="_Command")

bootstrap_install_from = None

find_packages = PackageFinder.find
find_namespace_packages = PEP420PackageFinder.find


def _install_setup_requires(attrs):
    # Note: do not use `setuptools.Distribution` directly, as
    # our PEP 517 backend patch `distutils.core.Distribution`.
    class MinimalDistribution(distutils.core.Distribution):
        """
        A minimal version of a distribution for supporting the
        fetch_build_eggs interface.
        """

        def __init__(self, attrs: Mapping[str, object]) -> None:
            _incl = 'dependency_links', 'setup_requires'
            filtered = {k: attrs[k] for k in set(_incl) & set(attrs)}
            super().__init__(filtered)
            # Prevent accidentally triggering discovery with incomplete set of attrs
            self.set_defaults._disable()

        def _get_project_config_files(self, filenames=None):
            """Ignore ``pyproject.toml``, they are not related to setup_requires"""
            try:
                cfg, _toml = super()._split_standard_project_metadata(filenames)
            except Exception:
                return filenames, ()
            return cfg, ()

        def finalize_options(self):
            """
            Disable finalize_options to avoid building the working set.
            Ref #2158.
            """

    dist = MinimalDistribution(attrs)

    # Honor setup.cfg's options.
    dist.parse_config_files(ignore_option_errors=True)
    if dist.setup_requires:
        _fetch_build_eggs(dist)


def _fetch_build_eggs(dist: Distribution):
    try:
        dist.fetch_build_eggs(dist.setup_requires)
    except Exception as ex:
        msg = """
        It is possible a package already installed in your system
        contains an version that is invalid according to PEP 440.
        You can try `pip install --use-pep517` as a workaround for this problem,
        or rely on a new virtual environment.

        If the problem refers to a package that is not installed yet,
        please contact that package's maintainers or distributors.
        """
        if "InvalidVersion" in ex.__class__.__name__:
            if hasattr(ex, "add_note"):
                ex.add_note(msg)  # PEP 678
            else:
                dist.announce(f"\n{msg}\n")
        raise


def setup(**attrs):
    logging.configure()
    # Make sure we have any requirements needed to interpret 'attrs'.
    _install_setup_requires(attrs)
    return distutils.core.setup(**attrs)


setup.__doc__ = distutils.core.setup.__doc__

if TYPE_CHECKING:
    # Work around a mypy issue where type[T] can't be used as a base: https://github.com/python/mypy/issues/10962
    from distutils.core import Command as _Command
else:
    _Command = monkey.get_unpatched(distutils.core.Command)


class Command(_Command):
    """
    Setuptools internal actions are organized using a *command design pattern*.
    This means that each action (or group of closely related actions) executed during
    the build should be implemented as a ``Command`` subclass.

    These commands are abstractions and do not necessarily correspond to a command that
    can (or should) be executed via a terminal, in a CLI fashion (although historically
    they would).

    When creating a new command from scratch, custom defined classes **SHOULD** inherit
    from ``setuptools.Command`` and implement a few mandatory methods.
    Between these mandatory methods, are listed:
    :meth:`initialize_options`, :meth:`finalize_options` and :meth:`run`.

    A useful analogy for command classes is to think of them as subroutines with local
    variables called "options".  The options are "declared" in :meth:`initialize_options`
    and "defined" (given their final values, aka "finalized") in :meth:`finalize_options`,
    both of which must be defined by every command class. The "body" of the subroutine,
    (where it does all the work) is the :meth:`run` method.
    Between :meth:`initialize_options` and :meth:`finalize_options`, ``setuptools`` may set
    the values for options/attributes based on user's input (or circumstance),
    which means that the implementation should be careful to not overwrite values in
    :meth:`finalize_options` unless necessary.

    Please note that other commands (or other parts of setuptools) may also overwrite
    the values of the command's options/attributes multiple times during the build
    process.
    Therefore it is important to consistently implement :meth:`initialize_options` and
    :meth:`finalize_options`. For example, all derived attributes (or attributes that
    depend on the value of other attributes) **SHOULD** be recomputed in
    :meth:`finalize_options`.

    When overwriting existing commands, custom defined classes **MUST** abide by the
    same APIs implemented by the original class. They also **SHOULD** inherit from the
    original class.
    """

    command_consumes_arguments = False
    distribution: Distribution  # override distutils.dist.Distribution with setuptools.dist.Distribution

    def __init__(self, dist: Distribution, **kw) -> None:
        """
        Construct the command for dist, updating
        vars(self) with any keyword parameters.
        """
        super().__init__(dist)
        vars(self).update(kw)

    @overload
    def reinitialize_command(
        self, command: str, reinit_subcommands: bool = False, **kw
    ) -> _Command: ...
    @overload
    def reinitialize_command(
        self, command: _CommandT, reinit_subcommands: bool = False, **kw
    ) -> _CommandT: ...
    def reinitialize_command(
        self, command: str | _Command, reinit_subcommands: bool = False, **kw
    ) -> _Command:
        cmd = _Command.reinitialize_command(self, command, reinit_subcommands)
        vars(cmd).update(kw)
        return cmd  # pyright: ignore[reportReturnType] # pypa/distutils#307

    @abstractmethod
    def initialize_options(self) -> None:
        """
        Set or (reset) all options/attributes/caches used by the command
        to their default values. Note that these values may be overwritten during
        the build.
        """
        raise NotImplementedError

    @abstractmethod
    def finalize_options(self) -> None:
        """
        Set final values for all options/attributes used by the command.
        Most of the time, each option/attribute/cache should only be set if it does not
        have any value yet (e.g. ``if self.attr is None: self.attr = val``).
        """
        raise NotImplementedError

    @abstractmethod
    def run(self) -> None:
        """
        Execute the actions intended by the command.
        (Side effects **SHOULD** only take place when :meth:`run` is executed,
        for example, creating new files or writing to the terminal output).
        """
        raise NotImplementedError


def _find_all_simple(path):
    """
    Find all files under 'path'
    """
    results = (
        os.path.join(base, file)
        for base, dirs, files in os.walk(path, followlinks=True)
        for file in files
    )
    return filter(os.path.isfile, results)


def findall(dir=os.curdir):
    """
    Find all files under 'dir' and return the list of full filenames.
    Unless dir is '.', return full filenames with dir prepended.
    """
    files = _find_all_simple(dir)
    if dir == os.curdir:
        make_rel = functools.partial(os.path.relpath, start=dir)
        files = map(make_rel, files)
    return list(files)


class sic(str):
    """Treat this string as-is (https://en.wikipedia.org/wiki/Sic)"""


# Apply monkey patches
monkey.patch_all()

# === NexusCore/openenv\Lib\site-packages\fontTools\merge\__init__.py ===
# Copyright 2013 Google, Inc. All Rights Reserved.
#
# Google Author(s): Behdad Esfahbod, Roozbeh Pournader

from fontTools import ttLib
import fontTools.merge.base
from fontTools.merge.cmap import (
    computeMegaGlyphOrder,
    computeMegaCmap,
    renameCFFCharStrings,
)
from fontTools.merge.layout import layoutPreMerge, layoutPostMerge
from fontTools.merge.options import Options
import fontTools.merge.tables
from fontTools.misc.loggingTools import Timer
from functools import reduce
import sys
import logging


log = logging.getLogger("fontTools.merge")
timer = Timer(logger=logging.getLogger(__name__ + ".timer"), level=logging.INFO)


class Merger(object):
    """Font merger.

    This class merges multiple files into a single OpenType font, taking into
    account complexities such as OpenType layout (``GSUB``/``GPOS``) tables and
    cross-font metrics (for example ``hhea.ascent`` is set to the maximum value
    across all the fonts).

    If multiple glyphs map to the same Unicode value, and the glyphs are considered
    sufficiently different (that is, they differ in any of paths, widths, or
    height), then subsequent glyphs are renamed and a lookup in the ``locl``
    feature will be created to disambiguate them. For example, if the arguments
    are an Arabic font and a Latin font and both contain a set of parentheses,
    the Latin glyphs will be renamed to ``parenleft.1`` and ``parenright.1``,
    and a lookup will be inserted into the to ``locl`` feature (creating it if
    necessary) under the ``latn`` script to substitute ``parenleft`` with
    ``parenleft.1`` etc.

    Restrictions:

    - All fonts must have the same units per em.
    - If duplicate glyph disambiguation takes place as described above then the
      fonts must have a ``GSUB`` table.

    Attributes:
            options: Currently unused.
    """

    def __init__(self, options=None):
        if not options:
            options = Options()

        self.options = options

    def _openFonts(self, fontfiles):
        fonts = [ttLib.TTFont(fontfile) for fontfile in fontfiles]
        for font, fontfile in zip(fonts, fontfiles):
            font._merger__fontfile = fontfile
            font._merger__name = font["name"].getDebugName(4)
        return fonts

    def merge(self, fontfiles):
        """Merges fonts together.

        Args:
                fontfiles: A list of file names to be merged

        Returns:
                A :class:`fontTools.ttLib.TTFont` object. Call the ``save`` method on
                this to write it out to an OTF file.
        """
        #
        # Settle on a mega glyph order.
        #
        fonts = self._openFonts(fontfiles)
        glyphOrders = [list(font.getGlyphOrder()) for font in fonts]
        computeMegaGlyphOrder(self, glyphOrders)

        # Take first input file sfntVersion
        sfntVersion = fonts[0].sfntVersion

        # Reload fonts and set new glyph names on them.
        fonts = self._openFonts(fontfiles)
        for font, glyphOrder in zip(fonts, glyphOrders):
            font.setGlyphOrder(glyphOrder)
            if "CFF " in font:
                renameCFFCharStrings(self, glyphOrder, font["CFF "])

        cmaps = [font["cmap"] for font in fonts]
        self.duplicateGlyphsPerFont = [{} for _ in fonts]
        computeMegaCmap(self, cmaps)

        mega = ttLib.TTFont(sfntVersion=sfntVersion)
        mega.setGlyphOrder(self.glyphOrder)

        for font in fonts:
            self._preMerge(font)

        self.fonts = fonts

        allTags = reduce(set.union, (list(font.keys()) for font in fonts), set())
        allTags.remove("GlyphOrder")

        for tag in sorted(allTags):
            if tag in self.options.drop_tables:
                continue

            with timer("merge '%s'" % tag):
                tables = [font.get(tag, NotImplemented) for font in fonts]

                log.info("Merging '%s'.", tag)
                clazz = ttLib.getTableClass(tag)
                table = clazz(tag).merge(self, tables)
                # XXX Clean this up and use:  table = mergeObjects(tables)

                if table is not NotImplemented and table is not False:
                    mega[tag] = table
                    log.info("Merged '%s'.", tag)
                else:
                    log.info("Dropped '%s'.", tag)

        del self.duplicateGlyphsPerFont
        del self.fonts

        self._postMerge(mega)

        return mega

    def mergeObjects(self, returnTable, logic, tables):
        # Right now we don't use self at all.  Will use in the future
        # for options and logging.

        allKeys = set.union(
            set(),
            *(vars(table).keys() for table in tables if table is not NotImplemented),
        )
        for key in allKeys:
            log.info(" %s", key)
            try:
                mergeLogic = logic[key]
            except KeyError:
                try:
                    mergeLogic = logic["*"]
                except KeyError:
                    raise Exception(
                        "Don't know how to merge key %s of class %s"
                        % (key, returnTable.__class__.__name__)
                    )
            if mergeLogic is NotImplemented:
                continue
            value = mergeLogic(getattr(table, key, NotImplemented) for table in tables)
            if value is not NotImplemented:
                setattr(returnTable, key, value)

        return returnTable

    def _preMerge(self, font):
        layoutPreMerge(font)

    def _postMerge(self, font):
        layoutPostMerge(font)

        if "OS/2" in font:
            # https://github.com/fonttools/fonttools/issues/2538
            # TODO: Add an option to disable this?
            font["OS/2"].recalcAvgCharWidth(font)


__all__ = ["Options", "Merger", "main"]


@timer("make one with everything (TOTAL TIME)")
def main(args=None):
    """Merge multiple fonts into one"""
    from fontTools import configLogger

    if args is None:
        args = sys.argv[1:]

    options = Options()
    args = options.parse_opts(args)
    fontfiles = []
    if options.input_file:
        with open(options.input_file) as inputfile:
            fontfiles = [
                line.strip()
                for line in inputfile.readlines()
                if not line.lstrip().startswith("#")
            ]
    for g in args:
        fontfiles.append(g)

    if len(fontfiles) < 1:
        print(
            "usage: pyftmerge [font1 ... fontN] [--input-file=filelist.txt] [--output-file=merged.ttf] [--import-file=tables.ttx]",
            file=sys.stderr,
        )
        print(
            "                                   [--drop-tables=tags] [--verbose] [--timing]",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print(" font1 ... fontN              Files to merge.", file=sys.stderr)
        print(
            " --input-file=<filename>      Read files to merge from a text file, each path new line. # Comment lines allowed.",
            file=sys.stderr,
        )
        print(
            " --output-file=<filename>     Specify output file name (default: merged.ttf).",
            file=sys.stderr,
        )
        print(
            " --import-file=<filename>     TTX file to import after merging. This can be used to set metadata.",
            file=sys.stderr,
        )
        print(
            " --drop-tables=<table tags>   Comma separated list of table tags to skip, case sensitive.",
            file=sys.stderr,
        )
        print(
            " --verbose                    Output progress information.",
            file=sys.stderr,
        )
        print(" --timing                     Output progress timing.", file=sys.stderr)
        return 1

    configLogger(level=logging.INFO if options.verbose else logging.WARNING)
    if options.timing:
        timer.logger.setLevel(logging.DEBUG)
    else:
        timer.logger.disabled = True

    merger = Merger(options=options)
    font = merger.merge(fontfiles)

    if options.import_file:
        font.importXML(options.import_file)

    with timer("compile and save font"):
        font.save(options.output_file)


if __name__ == "__main__":
    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\datetime_parse.py ===
"""
Functions to parse datetime objects.

We're using regular expressions rather than time.strptime because:
- They provide both validation and parsing.
- They're more flexible for datetimes.
- The date/datetime/time constructors produce friendlier error messages.

Stolen from https://raw.githubusercontent.com/django/django/main/django/utils/dateparse.py at
9718fa2e8abe430c3526a9278dd976443d4ae3c6

Changed to:
* use standard python datetime types not django.utils.timezone
* raise ValueError when regex doesn't match rather than returning None
* support parsing unix timestamps for dates and datetimes
"""
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, Optional, Type, Union

from pydantic.v1 import errors

date_expr = r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
time_expr = (
    r'(?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    r'(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?$'
)

date_re = re.compile(f'{date_expr}$')
time_re = re.compile(time_expr)
datetime_re = re.compile(f'{date_expr}[T ]{time_expr}')

standard_duration_re = re.compile(
    r'^'
    r'(?:(?P<days>-?\d+) (days?, )?)?'
    r'((?:(?P<hours>-?\d+):)(?=\d+:\d+))?'
    r'(?:(?P<minutes>-?\d+):)?'
    r'(?P<seconds>-?\d+)'
    r'(?:\.(?P<microseconds>\d{1,6})\d{0,6})?'
    r'$'
)

# Support the sections of ISO 8601 date representation that are accepted by timedelta
iso8601_duration_re = re.compile(
    r'^(?P<sign>[-+]?)'
    r'P'
    r'(?:(?P<days>\d+(.\d+)?)D)?'
    r'(?:T'
    r'(?:(?P<hours>\d+(.\d+)?)H)?'
    r'(?:(?P<minutes>\d+(.\d+)?)M)?'
    r'(?:(?P<seconds>\d+(.\d+)?)S)?'
    r')?'
    r'$'
)

EPOCH = datetime(1970, 1, 1)
# if greater than this, the number is in ms, if less than or equal it's in seconds
# (in seconds this is 11th October 2603, in ms it's 20th August 1970)
MS_WATERSHED = int(2e10)
# slightly more than datetime.max in ns - (datetime.max - EPOCH).total_seconds() * 1e9
MAX_NUMBER = int(3e20)
StrBytesIntFloat = Union[str, bytes, int, float]


def get_numeric(value: StrBytesIntFloat, native_expected_type: str) -> Union[None, int, float]:
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except ValueError:
        return None
    except TypeError:
        raise TypeError(f'invalid type; expected {native_expected_type}, string, bytes, int or float')


def from_unix_seconds(seconds: Union[int, float]) -> datetime:
    if seconds > MAX_NUMBER:
        return datetime.max
    elif seconds < -MAX_NUMBER:
        return datetime.min

    while abs(seconds) > MS_WATERSHED:
        seconds /= 1000
    dt = EPOCH + timedelta(seconds=seconds)
    return dt.replace(tzinfo=timezone.utc)


def _parse_timezone(value: Optional[str], error: Type[Exception]) -> Union[None, int, timezone]:
    if value == 'Z':
        return timezone.utc
    elif value is not None:
        offset_mins = int(value[-2:]) if len(value) > 3 else 0
        offset = 60 * int(value[1:3]) + offset_mins
        if value[0] == '-':
            offset = -offset
        try:
            return timezone(timedelta(minutes=offset))
        except ValueError:
            raise error()
    else:
        return None


def parse_date(value: Union[date, StrBytesIntFloat]) -> date:
    """
    Parse a date/int/float/string and return a datetime.date.

    Raise ValueError if the input is well formatted but not a valid date.
    Raise ValueError if the input isn't well formatted.
    """
    if isinstance(value, date):
        if isinstance(value, datetime):
            return value.date()
        else:
            return value

    number = get_numeric(value, 'date')
    if number is not None:
        return from_unix_seconds(number).date()

    if isinstance(value, bytes):
        value = value.decode()

    match = date_re.match(value)  # type: ignore
    if match is None:
        raise errors.DateError()

    kw = {k: int(v) for k, v in match.groupdict().items()}

    try:
        return date(**kw)
    except ValueError:
        raise errors.DateError()


def parse_time(value: Union[time, StrBytesIntFloat]) -> time:
    """
    Parse a time/string and return a datetime.time.

    Raise ValueError if the input is well formatted but not a valid time.
    Raise ValueError if the input isn't well formatted, in particular if it contains an offset.
    """
    if isinstance(value, time):
        return value

    number = get_numeric(value, 'time')
    if number is not None:
        if number >= 86400:
            # doesn't make sense since the time time loop back around to 0
            raise errors.TimeError()
        return (datetime.min + timedelta(seconds=number)).time()

    if isinstance(value, bytes):
        value = value.decode()

    match = time_re.match(value)  # type: ignore
    if match is None:
        raise errors.TimeError()

    kw = match.groupdict()
    if kw['microsecond']:
        kw['microsecond'] = kw['microsecond'].ljust(6, '0')

    tzinfo = _parse_timezone(kw.pop('tzinfo'), errors.TimeError)
    kw_: Dict[str, Union[None, int, timezone]] = {k: int(v) for k, v in kw.items() if v is not None}
    kw_['tzinfo'] = tzinfo

    try:
        return time(**kw_)  # type: ignore
    except ValueError:
        raise errors.TimeError()


def parse_datetime(value: Union[datetime, StrBytesIntFloat]) -> datetime:
    """
    Parse a datetime/int/float/string and return a datetime.datetime.

    This function supports time zone offsets. When the input contains one,
    the output uses a timezone with a fixed offset from UTC.

    Raise ValueError if the input is well formatted but not a valid datetime.
    Raise ValueError if the input isn't well formatted.
    """
    if isinstance(value, datetime):
        return value

    number = get_numeric(value, 'datetime')
    if number is not None:
        return from_unix_seconds(number)

    if isinstance(value, bytes):
        value = value.decode()

    match = datetime_re.match(value)  # type: ignore
    if match is None:
        raise errors.DateTimeError()

    kw = match.groupdict()
    if kw['microsecond']:
        kw['microsecond'] = kw['microsecond'].ljust(6, '0')

    tzinfo = _parse_timezone(kw.pop('tzinfo'), errors.DateTimeError)
    kw_: Dict[str, Union[None, int, timezone]] = {k: int(v) for k, v in kw.items() if v is not None}
    kw_['tzinfo'] = tzinfo

    try:
        return datetime(**kw_)  # type: ignore
    except ValueError:
        raise errors.DateTimeError()


def parse_duration(value: StrBytesIntFloat) -> timedelta:
    """
    Parse a duration int/float/string and return a datetime.timedelta.

    The preferred format for durations in Django is '%d %H:%M:%S.%f'.

    Also supports ISO 8601 representation.
    """
    if isinstance(value, timedelta):
        return value

    if isinstance(value, (int, float)):
        # below code requires a string
        value = f'{value:f}'
    elif isinstance(value, bytes):
        value = value.decode()

    try:
        match = standard_duration_re.match(value) or iso8601_duration_re.match(value)
    except TypeError:
        raise TypeError('invalid type; expected timedelta, string, bytes, int or float')

    if not match:
        raise errors.DurationError()

    kw = match.groupdict()
    sign = -1 if kw.pop('sign', '+') == '-' else 1
    if kw.get('microseconds'):
        kw['microseconds'] = kw['microseconds'].ljust(6, '0')

    if kw.get('seconds') and kw.get('microseconds') and kw['seconds'].startswith('-'):
        kw['microseconds'] = '-' + kw['microseconds']

    kw_ = {k: float(v) for k, v in kw.items() if v is not None}

    return sign * timedelta(**kw_)

# === NexusCore/evaluation\evalplus\evalplus\sanitize.py ===
"""Post-processing LLM-generated Python code implemented using tree-sitter."""

import os
import pathlib
from typing import Dict, Generator, List, Optional, Set, Tuple

from tqdm import tqdm
from tree_sitter import Node
from tree_sitter_languages import get_parser

from evalplus.data import (
    get_human_eval_plus,
    get_mbpp_plus,
    load_solutions,
    write_directory,
    write_jsonl,
)
from evalplus.syncheck import syntax_check

CLASS_TYPE = "class_definition"
FUNCTION_TYPE = "function_definition"
IMPORT_TYPE = ["import_statement", "import_from_statement"]
IDENTIFIER_TYPE = "identifier"
ATTRIBUTE_TYPE = "attribute"
RETURN_TYPE = "return_statement"
EXPRESSION_TYPE = "expression_statement"
ASSIGNMENT_TYPE = "assignment"


def code_extract(text: str) -> str:
    lines = text.split("\n")
    longest_line_pair = (0, 0)
    longest_so_far = 0

    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            current_lines = "\n".join(lines[i : j + 1])
            if syntax_check(current_lines):
                current_length = sum(1 for line in lines[i : j + 1] if line.strip())
                if current_length > longest_so_far:
                    longest_so_far = current_length
                    longest_line_pair = (i, j)

    return "\n".join(lines[longest_line_pair[0] : longest_line_pair[1] + 1])


def get_deps(nodes: List[Tuple[str, Node]]) -> Dict[str, Set[str]]:

    def dfs_get_deps(node: Node, deps: Set[str]) -> None:
        for child in node.children:
            if child.type == IDENTIFIER_TYPE:
                deps.add(child.text.decode("utf8"))
            else:
                dfs_get_deps(child, deps)

    name2deps = {}
    for name, node in nodes:
        deps = set()
        dfs_get_deps(node, deps)
        name2deps[name] = deps
    return name2deps


def get_function_dependency(entrypoint: str, call_graph: Dict[str, str]) -> Set[str]:
    queue = [entrypoint]
    visited = {entrypoint}
    while queue:
        current = queue.pop(0)
        if current not in call_graph:
            continue
        for neighbour in call_graph[current]:
            if not (neighbour in visited):
                visited.add(neighbour)
                queue.append(neighbour)
    return visited


def get_definition_name(node: Node) -> str:
    for child in node.children:
        if child.type == IDENTIFIER_TYPE:
            return child.text.decode("utf8")


def traverse_tree(node: Node) -> Generator[Node, None, None]:
    cursor = node.walk()
    depth = 0

    visited_children = False
    while True:
        if not visited_children:
            yield cursor.node
            if not cursor.goto_first_child():
                depth += 1
                visited_children = True
        elif cursor.goto_next_sibling():
            visited_children = False
        elif not cursor.goto_parent() or depth == 0:
            break
        else:
            depth -= 1


def has_return_statement(node: Node) -> bool:
    traverse_nodes = traverse_tree(node)
    for node in traverse_nodes:
        if node.type == RETURN_TYPE:
            return True
    return False


def sanitize(code: str, entrypoint: Optional[str] = None) -> str:
    code = code_extract(code)
    code_bytes = bytes(code, "utf8")
    parser = get_parser("python")
    tree = parser.parse(code_bytes)
    class_names = set()
    function_names = set()
    variable_names = set()

    root_node = tree.root_node
    import_nodes = []
    definition_nodes = []

    for child in root_node.children:
        if child.type in IMPORT_TYPE:
            import_nodes.append(child)
        elif child.type == CLASS_TYPE:
            name = get_definition_name(child)
            if not (
                name in class_names or name in variable_names or name in function_names
            ):
                definition_nodes.append((name, child))
                class_names.add(name)
        elif child.type == FUNCTION_TYPE:
            name = get_definition_name(child)
            if not (
                name in function_names or name in variable_names or name in class_names
            ) and has_return_statement(child):
                definition_nodes.append((name, child))
                function_names.add(get_definition_name(child))
        elif (
            child.type == EXPRESSION_TYPE and child.children[0].type == ASSIGNMENT_TYPE
        ):
            subchild = child.children[0]
            name = get_definition_name(subchild)
            if not (
                name in variable_names or name in function_names or name in class_names
            ):
                definition_nodes.append((name, subchild))
                variable_names.add(name)

    if entrypoint:
        name2deps = get_deps(definition_nodes)
        reacheable = get_function_dependency(entrypoint, name2deps)

    sanitized_output = b""

    for node in import_nodes:
        sanitized_output += code_bytes[node.start_byte : node.end_byte] + b"\n"

    for pair in definition_nodes:
        name, node = pair
        if entrypoint and not (name in reacheable):
            continue
        sanitized_output += code_bytes[node.start_byte : node.end_byte] + b"\n"
    return sanitized_output[:-1].decode("utf8")


def script(
    samples: str, inplace: bool = False, debug_task: str = None, mbpp_version="default"
):
    # task_id -> entry_point
    entry_point = {}
    # merge two datasets
    dataset = {**get_human_eval_plus(), **get_mbpp_plus(version=mbpp_version)}

    for task_id, problem in dataset.items():
        entry_point[task_id] = problem["entry_point"]

    # make a new folder with "-sanitized" suffix
    is_folder = os.path.isdir(samples)
    target_path = pathlib.Path(samples)
    if not inplace:
        if is_folder:
            new_name = target_path.name + "-sanitized"
        else:
            new_name = target_path.name.replace(".jsonl", "-sanitized.jsonl")
        target_path = target_path.parent / new_name
    target_path = str(target_path)

    nsan = 0
    ntotal = 0

    new_solutions = []

    for solution in tqdm(load_solutions(samples)):
        task_id = solution["task_id"]
        if task_id not in dataset:
            print(
                f"Skiping {task_id} as it does not existing in the latest EvalPlus dataset."
            )
            continue

        function_name = entry_point[task_id] if task_id in entry_point else None
        dbg_identifier = solution["_identifier"]
        if debug_task is not None and task_id != debug_task:
            continue

        ntotal += 1
        if "solution" in solution:
            old_code = solution["solution"]
        else:
            assert "completion" in solution
            old_code = dataset[task_id]["prompt"] + "\n" + solution["completion"]

        new_code = sanitize(code=old_code, entrypoint=function_name)

        # if changed, print the message
        if new_code != old_code:
            msg = "Sanitized: " + dbg_identifier
            if is_folder:
                msg += " -> " + dbg_identifier.replace(samples, target_path)
            print(msg)
            nsan += 1

        new_solutions.append({"task_id": task_id, "solution": new_code})

    if is_folder:
        write_directory(target_path, new_solutions)
    else:
        write_jsonl(target_path, new_solutions)

    if nsan > 0:
        print(f"Sanitized {nsan} out of {ntotal} files.")
    else:
        print(f"All files seems valid -- no files are sanitized.")
    print(f"Check the sanitized files at {target_path}")


def main():
    from fire import Fire

    Fire(script)


if __name__ == "__main__":
    main()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\sphinxext.py ===
"""
    pygments.sphinxext
    ~~~~~~~~~~~~~~~~~~

    Sphinx extension to generate automatic documentation of lexers,
    formatters and filters.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys

from docutils import nodes
from docutils.statemachine import ViewList
from docutils.parsers.rst import Directive
from sphinx.util.nodes import nested_parse_with_titles


MODULEDOC = '''
.. module:: %s

%s
%s
'''

LEXERDOC = '''
.. class:: %s

    :Short names: %s
    :Filenames:   %s
    :MIME types:  %s

    %s

    %s

'''

FMTERDOC = '''
.. class:: %s

    :Short names: %s
    :Filenames: %s

    %s

'''

FILTERDOC = '''
.. class:: %s

    :Name: %s

    %s

'''


class PygmentsDoc(Directive):
    """
    A directive to collect all lexers/formatters/filters and generate
    autoclass directives for them.
    """
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        self.filenames = set()
        if self.arguments[0] == 'lexers':
            out = self.document_lexers()
        elif self.arguments[0] == 'formatters':
            out = self.document_formatters()
        elif self.arguments[0] == 'filters':
            out = self.document_filters()
        elif self.arguments[0] == 'lexers_overview':
            out = self.document_lexers_overview()
        else:
            raise Exception('invalid argument for "pygmentsdoc" directive')
        node = nodes.compound()
        vl = ViewList(out.split('\n'), source='')
        nested_parse_with_titles(self.state, vl, node)
        for fn in self.filenames:
            self.state.document.settings.record_dependencies.add(fn)
        return node.children

    def document_lexers_overview(self):
        """Generate a tabular overview of all lexers.

        The columns are the lexer name, the extensions handled by this lexer
        (or "None"), the aliases and a link to the lexer class."""
        from pip._vendor.pygments.lexers._mapping import LEXERS
        from pip._vendor.pygments.lexers import find_lexer_class
        out = []

        table = []

        def format_link(name, url):
            if url:
                return f'`{name} <{url}>`_'
            return name

        for classname, data in sorted(LEXERS.items(), key=lambda x: x[1][1].lower()):
            lexer_cls = find_lexer_class(data[1])
            extensions = lexer_cls.filenames + lexer_cls.alias_filenames

            table.append({
                'name': format_link(data[1], lexer_cls.url),
                'extensions': ', '.join(extensions).replace('*', '\\*').replace('_', '\\') or 'None',
                'aliases': ', '.join(data[2]),
                'class': f'{data[0]}.{classname}'
            })

        column_names = ['name', 'extensions', 'aliases', 'class']
        column_lengths = [max([len(row[column]) for row in table if row[column]])
                          for column in column_names]

        def write_row(*columns):
            """Format a table row"""
            out = []
            for length, col in zip(column_lengths, columns):
                if col:
                    out.append(col.ljust(length))
                else:
                    out.append(' '*length)

            return ' '.join(out)

        def write_seperator():
            """Write a table separator row"""
            sep = ['='*c for c in column_lengths]
            return write_row(*sep)

        out.append(write_seperator())
        out.append(write_row('Name', 'Extension(s)', 'Short name(s)', 'Lexer class'))
        out.append(write_seperator())
        for row in table:
            out.append(write_row(
                row['name'],
                row['extensions'],
                row['aliases'],
                f':class:`~{row["class"]}`'))
        out.append(write_seperator())

        return '\n'.join(out)

    def document_lexers(self):
        from pip._vendor.pygments.lexers._mapping import LEXERS
        from pip._vendor import pygments
        import inspect
        import pathlib

        out = []
        modules = {}
        moduledocstrings = {}
        for classname, data in sorted(LEXERS.items(), key=lambda x: x[0]):
            module = data[0]
            mod = __import__(module, None, None, [classname])
            self.filenames.add(mod.__file__)
            cls = getattr(mod, classname)
            if not cls.__doc__:
                print(f"Warning: {classname} does not have a docstring.")
            docstring = cls.__doc__
            if isinstance(docstring, bytes):
                docstring = docstring.decode('utf8')

            example_file = getattr(cls, '_example', None)
            if example_file:
                p = pathlib.Path(inspect.getabsfile(pygments)).parent.parent /\
                    'tests' / 'examplefiles' / example_file
                content = p.read_text(encoding='utf-8')
                if not content:
                    raise Exception(
                        f"Empty example file '{example_file}' for lexer "
                        f"{classname}")

                if data[2]:
                    lexer_name = data[2][0]
                    docstring += '\n\n    .. admonition:: Example\n'
                    docstring += f'\n      .. code-block:: {lexer_name}\n\n'
                    for line in content.splitlines():
                        docstring += f'          {line}\n'

            if cls.version_added:
                version_line = f'.. versionadded:: {cls.version_added}'
            else:
                version_line = ''

            modules.setdefault(module, []).append((
                classname,
                ', '.join(data[2]) or 'None',
                ', '.join(data[3]).replace('*', '\\*').replace('_', '\\') or 'None',
                ', '.join(data[4]) or 'None',
                docstring,
                version_line))
            if module not in moduledocstrings:
                moddoc = mod.__doc__
                if isinstance(moddoc, bytes):
                    moddoc = moddoc.decode('utf8')
                moduledocstrings[module] = moddoc

        for module, lexers in sorted(modules.items(), key=lambda x: x[0]):
            if moduledocstrings[module] is None:
                raise Exception(f"Missing docstring for {module}")
            heading = moduledocstrings[module].splitlines()[4].strip().rstrip('.')
            out.append(MODULEDOC % (module, heading, '-'*len(heading)))
            for data in lexers:
                out.append(LEXERDOC % data)

        return ''.join(out)

    def document_formatters(self):
        from pip._vendor.pygments.formatters import FORMATTERS

        out = []
        for classname, data in sorted(FORMATTERS.items(), key=lambda x: x[0]):
            module = data[0]
            mod = __import__(module, None, None, [classname])
            self.filenames.add(mod.__file__)
            cls = getattr(mod, classname)
            docstring = cls.__doc__
            if isinstance(docstring, bytes):
                docstring = docstring.decode('utf8')
            heading = cls.__name__
            out.append(FMTERDOC % (heading, ', '.join(data[2]) or 'None',
                                   ', '.join(data[3]).replace('*', '\\*') or 'None',
                                   docstring))
        return ''.join(out)

    def document_filters(self):
        from pip._vendor.pygments.filters import FILTERS

        out = []
        for name, cls in FILTERS.items():
            self.filenames.add(sys.modules[cls.__module__].__file__)
            docstring = cls.__doc__
            if isinstance(docstring, bytes):
                docstring = docstring.decode('utf8')
            out.append(FILTERDOC % (cls.__name__, name, docstring))
        return ''.join(out)


def setup(app):
    app.add_directive('pygmentsdoc', PygmentsDoc)

# === NexusCore/openenv\Lib\site-packages\numpy\exceptions.py ===
"""
Exceptions and Warnings
=======================

General exceptions used by NumPy.  Note that some exceptions may be module
specific, such as linear algebra errors.

.. versionadded:: NumPy 1.25

    The exceptions module is new in NumPy 1.25.  Older exceptions remain
    available through the main NumPy namespace for compatibility.

.. currentmodule:: numpy.exceptions

Warnings
--------
.. autosummary::
   :toctree: generated/

   ComplexWarning             Given when converting complex to real.
   VisibleDeprecationWarning  Same as a DeprecationWarning, but more visible.
   RankWarning                Issued when the design matrix is rank deficient.

Exceptions
----------
.. autosummary::
   :toctree: generated/

    AxisError          Given when an axis was invalid.
    DTypePromotionError   Given when no common dtype could be found.
    TooHardError       Error specific to `numpy.shares_memory`.

"""


__all__ = [
    "ComplexWarning", "VisibleDeprecationWarning", "ModuleDeprecationWarning",
    "TooHardError", "AxisError", "DTypePromotionError"]


# Disallow reloading this module so as to preserve the identities of the
# classes defined here.
if '_is_loaded' in globals():
    raise RuntimeError('Reloading numpy._globals is not allowed')
_is_loaded = True


class ComplexWarning(RuntimeWarning):
    """
    The warning raised when casting a complex dtype to a real dtype.

    As implemented, casting a complex number to a real discards its imaginary
    part, but this behavior may not be what the user actually wants.

    """
    pass


class ModuleDeprecationWarning(DeprecationWarning):
    """Module deprecation warning.

    .. warning::

        This warning should not be used, since nose testing is not relevant
        anymore.

    The nose tester turns ordinary Deprecation warnings into test failures.
    That makes it hard to deprecate whole modules, because they get
    imported by default. So this is a special Deprecation warning that the
    nose tester will let pass without making tests fail.

    """
    pass


class VisibleDeprecationWarning(UserWarning):
    """Visible deprecation warning.

    By default, python will not show deprecation warnings, so this class
    can be used when a very visible warning is helpful, for example because
    the usage is most likely a user bug.

    """
    pass


class RankWarning(RuntimeWarning):
    """Matrix rank warning.

    Issued by polynomial functions when the design matrix is rank deficient.

    """
    pass


# Exception used in shares_memory()
class TooHardError(RuntimeError):
    """``max_work`` was exceeded.

    This is raised whenever the maximum number of candidate solutions
    to consider specified by the ``max_work`` parameter is exceeded.
    Assigning a finite number to ``max_work`` may have caused the operation
    to fail.

    """
    pass


class AxisError(ValueError, IndexError):
    """Axis supplied was invalid.

    This is raised whenever an ``axis`` parameter is specified that is larger
    than the number of array dimensions.
    For compatibility with code written against older numpy versions, which
    raised a mixture of :exc:`ValueError` and :exc:`IndexError` for this
    situation, this exception subclasses both to ensure that
    ``except ValueError`` and ``except IndexError`` statements continue
    to catch ``AxisError``.

    Parameters
    ----------
    axis : int or str
        The out of bounds axis or a custom exception message.
        If an axis is provided, then `ndim` should be specified as well.
    ndim : int, optional
        The number of array dimensions.
    msg_prefix : str, optional
        A prefix for the exception message.

    Attributes
    ----------
    axis : int, optional
        The out of bounds axis or ``None`` if a custom exception
        message was provided. This should be the axis as passed by
        the user, before any normalization to resolve negative indices.

        .. versionadded:: 1.22
    ndim : int, optional
        The number of array dimensions or ``None`` if a custom exception
        message was provided.

        .. versionadded:: 1.22


    Examples
    --------
    >>> import numpy as np
    >>> array_1d = np.arange(10)
    >>> np.cumsum(array_1d, axis=1)
    Traceback (most recent call last):
      ...
    numpy.exceptions.AxisError: axis 1 is out of bounds for array of dimension 1

    Negative axes are preserved:

    >>> np.cumsum(array_1d, axis=-2)
    Traceback (most recent call last):
      ...
    numpy.exceptions.AxisError: axis -2 is out of bounds for array of dimension 1

    The class constructor generally takes the axis and arrays'
    dimensionality as arguments:

    >>> print(np.exceptions.AxisError(2, 1, msg_prefix='error'))
    error: axis 2 is out of bounds for array of dimension 1

    Alternatively, a custom exception message can be passed:

    >>> print(np.exceptions.AxisError('Custom error message'))
    Custom error message

    """

    __slots__ = ("_msg", "axis", "ndim")

    def __init__(self, axis, ndim=None, msg_prefix=None):
        if ndim is msg_prefix is None:
            # single-argument form: directly set the error message
            self._msg = axis
            self.axis = None
            self.ndim = None
        else:
            self._msg = msg_prefix
            self.axis = axis
            self.ndim = ndim

    def __str__(self):
        axis = self.axis
        ndim = self.ndim

        if axis is ndim is None:
            return self._msg
        else:
            msg = f"axis {axis} is out of bounds for array of dimension {ndim}"
            if self._msg is not None:
                msg = f"{self._msg}: {msg}"
            return msg


class DTypePromotionError(TypeError):
    """Multiple DTypes could not be converted to a common one.

    This exception derives from ``TypeError`` and is raised whenever dtypes
    cannot be converted to a single common one.  This can be because they
    are of a different category/class or incompatible instances of the same
    one (see Examples).

    Notes
    -----
    Many functions will use promotion to find the correct result and
    implementation.  For these functions the error will typically be chained
    with a more specific error indicating that no implementation was found
    for the input dtypes.

    Typically promotion should be considered "invalid" between the dtypes of
    two arrays when `arr1 == arr2` can safely return all ``False`` because the
    dtypes are fundamentally different.

    Examples
    --------
    Datetimes and complex numbers are incompatible classes and cannot be
    promoted:

    >>> import numpy as np
    >>> np.result_type(np.dtype("M8[s]"), np.complex128)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
     ...
    DTypePromotionError: The DType <class 'numpy.dtype[datetime64]'> could not
    be promoted by <class 'numpy.dtype[complex128]'>. This means that no common
    DType exists for the given inputs. For example they cannot be stored in a
    single array unless the dtype is `object`. The full list of DTypes is:
    (<class 'numpy.dtype[datetime64]'>, <class 'numpy.dtype[complex128]'>)

    For example for structured dtypes, the structure can mismatch and the
    same ``DTypePromotionError`` is given when two structured dtypes with
    a mismatch in their number of fields is given:

    >>> dtype1 = np.dtype([("field1", np.float64), ("field2", np.int64)])
    >>> dtype2 = np.dtype([("field1", np.float64)])
    >>> np.promote_types(dtype1, dtype2)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
     ...
    DTypePromotionError: field names `('field1', 'field2')` and `('field1',)`
    mismatch.

    """  # noqa: E501
    pass