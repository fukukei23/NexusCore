
# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\ie\options.py ===
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
from enum import Enum
from typing import Any, Dict

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.options import ArgOptions


class ElementScrollBehavior(Enum):
    TOP = 0
    BOTTOM = 1


class _IeOptionsDescriptor:
    """_IeOptionsDescriptor is an implementation of Descriptor Protocol:

    : Any look-up or assignment to the below attributes in `Options` class will be intercepted
    by `__get__` and `__set__` method respectively.

    - `browser_attach_timeout`
    - `element_scroll_behavior`
    - `ensure_clean_session`
    - `file_upload_dialog_timeout`
    - `force_create_process_api`
    - `force_shell_windows_api`
    - `full_page_screenshot`
    - `ignore_protected_mode_settings`
    - `ignore_zoom_level`
    - `initial_browser_url`
    - `native_events`
    - `persistent_hover`
    - `require_window_focus`
    - `use_per_process_proxy`
    - `use_legacy_file_upload_dialog_handling`
    - `attach_to_edge_chrome`
    - `edge_executable_path`


    : When an attribute lookup happens,
    Example:
        `self. browser_attach_timeout`
        `__get__` method does a dictionary look up in the dictionary `_options` in `Options` class
        and returns the value of key `browserAttachTimeout`
    : When an attribute assignment happens,
    Example:
        `self.browser_attach_timeout` = 30
        `__set__` method sets/updates the value of the key `browserAttachTimeout` in `_options`
        dictionary in `Options` class.
    """

    def __init__(self, name, expected_type):
        self.name = name
        self.expected_type = expected_type

    def __get__(self, obj, cls):
        return obj._options.get(self.name)

    def __set__(self, obj, value) -> None:
        if not isinstance(value, self.expected_type):
            raise ValueError(f"{self.name} should be of type {self.expected_type.__name__}")

        if self.name == "elementScrollBehavior" and value not in [
            ElementScrollBehavior.TOP,
            ElementScrollBehavior.BOTTOM,
        ]:
            raise ValueError("Element Scroll Behavior out of range.")
        obj._options[self.name] = value


class Options(ArgOptions):
    KEY = "se:ieOptions"
    SWITCHES = "ie.browserCommandLineSwitches"

    BROWSER_ATTACH_TIMEOUT = "browserAttachTimeout"
    ELEMENT_SCROLL_BEHAVIOR = "elementScrollBehavior"
    ENSURE_CLEAN_SESSION = "ie.ensureCleanSession"
    FILE_UPLOAD_DIALOG_TIMEOUT = "ie.fileUploadDialogTimeout"
    FORCE_CREATE_PROCESS_API = "ie.forceCreateProcessApi"
    FORCE_SHELL_WINDOWS_API = "ie.forceShellWindowsApi"
    FULL_PAGE_SCREENSHOT = "ie.enableFullPageScreenshot"
    IGNORE_PROTECTED_MODE_SETTINGS = "ignoreProtectedModeSettings"
    IGNORE_ZOOM_LEVEL = "ignoreZoomSetting"
    INITIAL_BROWSER_URL = "initialBrowserUrl"
    NATIVE_EVENTS = "nativeEvents"
    PERSISTENT_HOVER = "enablePersistentHover"
    REQUIRE_WINDOW_FOCUS = "requireWindowFocus"
    USE_PER_PROCESS_PROXY = "ie.usePerProcessProxy"
    USE_LEGACY_FILE_UPLOAD_DIALOG_HANDLING = "ie.useLegacyFileUploadDialogHandling"
    ATTACH_TO_EDGE_CHROME = "ie.edgechromium"
    EDGE_EXECUTABLE_PATH = "ie.edgepath"
    IGNORE_PROCESS_MATCH = "ie.ignoreprocessmatch"

    # Creating descriptor objects for each of the above IE options
    browser_attach_timeout = _IeOptionsDescriptor(BROWSER_ATTACH_TIMEOUT, int)
    """Gets and Sets `browser_attach_timeout`

    Usage:
    ------
    - Get
        - `self.browser_attach_timeout`
    - Set
        - `self.browser_attach_timeout` = `value`

    Parameters:
    -----------
    `value`: `int` (Timeout) in milliseconds
    """

    element_scroll_behavior = _IeOptionsDescriptor(ELEMENT_SCROLL_BEHAVIOR, Enum)
    """Gets and Sets `element_scroll_behavior`

    Usage:
    ------
    - Get
        - `self.element_scroll_behavior`
    - Set
        - `self.element_scroll_behavior` = `value`

    Parameters:
    -----------
    `value`: `int` either 0 - Top, 1 - Bottom
    """

    ensure_clean_session = _IeOptionsDescriptor(ENSURE_CLEAN_SESSION, bool)
    """Gets and Sets `ensure_clean_session`

    Usage:
    ------
    - Get
        - `self.ensure_clean_session`
    - Set
        - `self.ensure_clean_session` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    file_upload_dialog_timeout = _IeOptionsDescriptor(FILE_UPLOAD_DIALOG_TIMEOUT, int)
    """Gets and Sets `file_upload_dialog_timeout`

    Usage:
    ------
    - Get
        - `self.file_upload_dialog_timeout`
    - Set
        - `self.file_upload_dialog_timeout` = `value`

    Parameters:
    -----------
    `value`: `int` (Timeout) in milliseconds
    """

    force_create_process_api = _IeOptionsDescriptor(FORCE_CREATE_PROCESS_API, bool)
    """Gets and Sets `force_create_process_api`

    Usage:
    ------
    - Get
        - `self.force_create_process_api`
    - Set
        - `self.force_create_process_api` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    force_shell_windows_api = _IeOptionsDescriptor(FORCE_SHELL_WINDOWS_API, bool)
    """Gets and Sets `force_shell_windows_api`

    Usage:
    ------
    - Get
        - `self.force_shell_windows_api`
    - Set
        - `self.force_shell_windows_api` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    full_page_screenshot = _IeOptionsDescriptor(FULL_PAGE_SCREENSHOT, bool)
    """Gets and Sets `full_page_screenshot`

    Usage:
    ------
    - Get
        - `self.full_page_screenshot`
    - Set
        - `self.full_page_screenshot` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    ignore_protected_mode_settings = _IeOptionsDescriptor(IGNORE_PROTECTED_MODE_SETTINGS, bool)
    """Gets and Sets `ignore_protected_mode_settings`

    Usage:
    ------
    - Get
        - `self.ignore_protected_mode_settings`
    - Set
        - `self.ignore_protected_mode_settings` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    ignore_zoom_level = _IeOptionsDescriptor(IGNORE_ZOOM_LEVEL, bool)
    """Gets and Sets `ignore_zoom_level`

    Usage:
    ------
    - Get
        - `self.ignore_zoom_level`
    - Set
        - `self.ignore_zoom_level` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    initial_browser_url = _IeOptionsDescriptor(INITIAL_BROWSER_URL, str)
    """Gets and Sets `initial_browser_url`

    Usage:
    ------
    - Get
        - `self.initial_browser_url`
    - Set
        - `self.initial_browser_url` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    native_events = _IeOptionsDescriptor(NATIVE_EVENTS, bool)
    """Gets and Sets `native_events`

    Usage:
    ------
    - Get
        - `self.native_events`
    - Set
        - `self.native_events` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    persistent_hover = _IeOptionsDescriptor(PERSISTENT_HOVER, bool)
    """Gets and Sets `persistent_hover`

    Usage:
    ------
    - Get
        - `self.persistent_hover`
    - Set
        - `self.persistent_hover` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    require_window_focus = _IeOptionsDescriptor(REQUIRE_WINDOW_FOCUS, bool)
    """Gets and Sets `require_window_focus`

    Usage:
    ------
    - Get
        - `self.require_window_focus`
    - Set
        - `self.require_window_focus` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    use_per_process_proxy = _IeOptionsDescriptor(USE_PER_PROCESS_PROXY, bool)
    """Gets and Sets `use_per_process_proxy`

    Usage:
    ------
    - Get
        - `self.use_per_process_proxy`
    - Set
        - `self.use_per_process_proxy` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    use_legacy_file_upload_dialog_handling = _IeOptionsDescriptor(USE_LEGACY_FILE_UPLOAD_DIALOG_HANDLING, bool)
    """Gets and Sets `use_legacy_file_upload_dialog_handling`

    Usage:
    ------
    - Get
        - `self.use_legacy_file_upload_dialog_handling`
    - Set
        - `self.use_legacy_file_upload_dialog_handling` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    attach_to_edge_chrome = _IeOptionsDescriptor(ATTACH_TO_EDGE_CHROME, bool)
    """Gets and Sets `attach_to_edge_chrome`

    Usage:
    ------
    - Get
        - `self.attach_to_edge_chrome`
    - Set
        - `self.attach_to_edge_chrome` = `value`

    Parameters:
    -----------
    `value`: `bool`
    """

    edge_executable_path = _IeOptionsDescriptor(EDGE_EXECUTABLE_PATH, str)
    """Gets and Sets `edge_executable_path`

    Usage:
    ------
    - Get
        - `self.edge_executable_path`
    - Set
        - `self.edge_executable_path` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    def __init__(self) -> None:
        super().__init__()
        self._options: Dict[str, Any] = {}
        self._additional: Dict[str, Any] = {}

    @property
    def options(self) -> dict:
        """:Returns: A dictionary of browser options."""
        return self._options

    @property
    def additional_options(self) -> dict:
        """:Returns: The additional options."""
        return self._additional

    def add_additional_option(self, name: str, value) -> None:
        """Adds an additional option not yet added as a safe option for IE.

        :Args:
         - name: name of the option to add
         - value: value of the option to add
        """
        self._additional[name] = value

    def to_capabilities(self) -> dict:
        """Marshals the IE options to the correct object."""
        caps = self._caps

        opts = self._options.copy()
        if self._arguments:
            opts[self.SWITCHES] = " ".join(self._arguments)

        if self._additional:
            opts.update(self._additional)

        if opts:
            caps[Options.KEY] = opts
        return caps

    @property
    def default_capabilities(self) -> dict:
        return DesiredCapabilities.INTERNETEXPLORER.copy()

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc5275.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# An Internet Attribute Certificate Profile for Authorization
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc5275.txt
#

from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import opentype
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc3565
from pyasn1_modules import rfc5280
from pyasn1_modules import rfc5652
from pyasn1_modules import rfc5751
from pyasn1_modules import rfc5755

MAX = float('inf')


# Initialize the map for GLAQueryRequests and GLAQueryResponses

glaQueryRRMap = { }


# Imports from RFC 3565

id_aes128_wrap = rfc3565.id_aes128_wrap


# Imports from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier

Certificate = rfc5280.Certificate

GeneralName = rfc5280.GeneralName


# Imports from RFC 5652

CertificateSet = rfc5652.CertificateSet

KEKIdentifier = rfc5652.KEKIdentifier

RecipientInfos = rfc5652.RecipientInfos


# Imports from RFC 5751

SMIMECapability = rfc5751.SMIMECapability


# Imports from RFC 5755

AttributeCertificate = rfc5755.AttributeCertificate


# The GL symmetric key distribution object identifier arc

id_skd = univ.ObjectIdentifier((1, 2, 840, 113549, 1, 9, 16, 8,))


# The GL Use KEK control attribute

id_skd_glUseKEK = id_skd + (1,)


class Certificates(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('pKC',
            Certificate().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('aC',
            univ.SequenceOf(componentType=AttributeCertificate()).subtype(
                subtypeSpec=constraint.ValueSizeConstraint(1, MAX)).subtype(
                    implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('certPath',
            CertificateSet().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class GLInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glName', GeneralName()),
        namedtype.NamedType('glAddress', GeneralName())
    )


class GLOwnerInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glOwnerName', GeneralName()),
        namedtype.NamedType('glOwnerAddress', GeneralName()),
        namedtype.OptionalNamedType('certificates', Certificates())
    )


class GLAdministration(univ.Integer):
    namedValues = namedval.NamedValues(
        ('unmanaged', 0),
        ('managed', 1),
        ('closed', 2)
    )


requested_algorithm = SMIMECapability().subtype(
   implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))
requested_algorithm['capabilityID'] = id_aes128_wrap


class GLKeyAttributes(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.DefaultedNamedType('rekeyControlledByGLO',
            univ.Boolean().subtype(value=0,
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.DefaultedNamedType('recipientsNotMutuallyAware',
            univ.Boolean().subtype(value=1,
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.DefaultedNamedType('duration',
            univ.Integer().subtype(value=0,
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.DefaultedNamedType('generationCounter',
            univ.Integer().subtype(value=2,
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
        namedtype.DefaultedNamedType('requestedAlgorithm', requested_algorithm)
    )


class GLUseKEK(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glInfo', GLInfo()),
        namedtype.NamedType('glOwnerInfo',
            univ.SequenceOf(componentType=GLOwnerInfo()).subtype(
                subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        namedtype.DefaultedNamedType('glAdministration',
            GLAdministration().subtype(value=1)),
        namedtype.OptionalNamedType('glKeyAttributes', GLKeyAttributes())
    )


# The Delete GL control attribute

id_skd_glDelete = id_skd + (2,)


class DeleteGL(GeneralName):
    pass


# The Add GL Member control attribute

id_skd_glAddMember = id_skd + (3,)


class GLMember(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glMemberName', GeneralName()),
        namedtype.OptionalNamedType('glMemberAddress', GeneralName()),
        namedtype.OptionalNamedType('certificates', Certificates())
    )


class GLAddMember(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glName', GeneralName()),
        namedtype.NamedType('glMember', GLMember())
    )


# The Delete GL Member control attribute

id_skd_glDeleteMember = id_skd + (4,)


class GLDeleteMember(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glName', GeneralName()),
        namedtype.NamedType('glMemberToDelete', GeneralName())
    )


# The GL Rekey control attribute

id_skd_glRekey = id_skd + (5,)


class GLNewKeyAttributes(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('rekeyControlledByGLO',
            univ.Boolean().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('recipientsNotMutuallyAware',
            univ.Boolean().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('duration',
            univ.Integer().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.OptionalNamedType('generationCounter',
            univ.Integer().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 3))),
        namedtype.OptionalNamedType('requestedAlgorithm',
            AlgorithmIdentifier().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 4)))
    )


class GLRekey(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glName', GeneralName()),
        namedtype.OptionalNamedType('glAdministration', GLAdministration()),
        namedtype.OptionalNamedType('glNewKeyAttributes', GLNewKeyAttributes()),
        namedtype.OptionalNamedType('glRekeyAllGLKeys', univ.Boolean())
    )


# The Add and Delete GL Owner control attributes

id_skd_glAddOwner = id_skd + (6,)

id_skd_glRemoveOwner = id_skd + (7,)


class GLOwnerAdministration(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glName', GeneralName()),
        namedtype.NamedType('glOwnerInfo', GLOwnerInfo())
    )


# The GL Key Compromise control attribute

id_skd_glKeyCompromise = id_skd + (8,)


class GLKCompromise(GeneralName):
    pass


# The GL Key Refresh control attribute

id_skd_glkRefresh = id_skd + (9,)


class Date(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('start', useful.GeneralizedTime()),
        namedtype.OptionalNamedType('end', useful.GeneralizedTime())
    )


class GLKRefresh(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glName', GeneralName()),
        namedtype.NamedType('dates',
            univ.SequenceOf(componentType=Date()).subtype(
                subtypeSpec=constraint.ValueSizeConstraint(1, MAX)))
    )


# The GLA Query Request control attribute

id_skd_glaQueryRequest = id_skd + (11,)


class GLAQueryRequest(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glaRequestType', univ.ObjectIdentifier()),
        namedtype.NamedType('glaRequestValue', univ.Any(),
            openType=opentype.OpenType('glaRequestType', glaQueryRRMap))
    )


# The GLA Query Response control attribute

id_skd_glaQueryResponse = id_skd + (12,)


class GLAQueryResponse(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glaResponseType', univ.ObjectIdentifier()),
        namedtype.NamedType('glaResponseValue', univ.Any(),
            openType=opentype.OpenType('glaResponseType', glaQueryRRMap))
    )


# The GLA Request/Response (glaRR) arc for glaRequestType/glaResponseType

id_cmc_glaRR = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, 7, 99,))


# The Algorithm Request

id_cmc_gla_skdAlgRequest = id_cmc_glaRR + (1,)


class SKDAlgRequest(univ.Null):
    pass


# The Algorithm Response

id_cmc_gla_skdAlgResponse = id_cmc_glaRR + (2,)

SMIMECapabilities = rfc5751.SMIMECapabilities


# The control attribute to request an updated certificate to the GLA and
# the control attribute to return an updated certificate to the GLA

id_skd_glProvideCert = id_skd + (13,)

id_skd_glManageCert = id_skd + (14,)


class GLManageCert(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glName', GeneralName()),
        namedtype.NamedType('glMember', GLMember())
    )


# The control attribute to distribute the GL shared KEK

id_skd_glKey = id_skd + (15,)


class GLKey(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('glName', GeneralName()),
        namedtype.NamedType('glIdentifier', KEKIdentifier()),
        namedtype.NamedType('glkWrapped', RecipientInfos()),
        namedtype.NamedType('glkAlgorithm', AlgorithmIdentifier()),
        namedtype.NamedType('glkNotBefore', useful.GeneralizedTime()),
        namedtype.NamedType('glkNotAfter', useful.GeneralizedTime())
    )


# The CMC error types

id_cet_skdFailInfo = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, 15, 1,))


class SKDFailInfo(univ.Integer):
    namedValues = namedval.NamedValues(
        ('unspecified', 0),
        ('closedGL', 1),
        ('unsupportedDuration', 2),
        ('noGLACertificate', 3),
        ('invalidCert', 4),
        ('unsupportedAlgorithm', 5),
        ('noGLONameMatch', 6),
        ('invalidGLName', 7),
        ('nameAlreadyInUse', 8),
        ('noSpam', 9),
        ('alreadyAMember', 11),
        ('notAMember', 12),
        ('alreadyAnOwner', 13),
        ('notAnOwner', 14)
    )


# Update the map for GLAQueryRequests and GLAQueryResponses

_glaQueryRRMapUpdate = {
    id_cmc_gla_skdAlgRequest: univ.Null(""),
    id_cmc_gla_skdAlgResponse: SMIMECapabilities(),
}

glaQueryRRMap.update(_glaQueryRRMapUpdate)


# Update the map for CMC control attributes; since CMS Attributes and
# CMC Controls both use 'attrType', one map is used for both

_cmcControlAttributesMapUpdate = {
    id_skd_glUseKEK: GLUseKEK(),
    id_skd_glDelete: DeleteGL(),
    id_skd_glAddMember: GLAddMember(),
    id_skd_glDeleteMember: GLDeleteMember(),
    id_skd_glRekey: GLRekey(),
    id_skd_glAddOwner: GLOwnerAdministration(),
    id_skd_glRemoveOwner: GLOwnerAdministration(),
    id_skd_glKeyCompromise: GLKCompromise(),
    id_skd_glkRefresh: GLKRefresh(),
    id_skd_glaQueryRequest: GLAQueryRequest(),
    id_skd_glaQueryResponse: GLAQueryResponse(),
    id_skd_glProvideCert: GLManageCert(),
    id_skd_glManageCert: GLManageCert(),
    id_skd_glKey: GLKey(),
}

rfc5652.cmsAttributesMap.update(_cmcControlAttributesMapUpdate)

# === NexusCore/openenv\Lib\site-packages\filelock\_api.py ===
from __future__ import annotations

import contextlib
import inspect
import logging
import os
import time
import warnings
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from threading import local
from typing import TYPE_CHECKING, Any, cast
from weakref import WeakValueDictionary

from ._error import Timeout

if TYPE_CHECKING:
    import sys
    from types import TracebackType

    if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
        from typing import Self
    else:  # pragma: no cover (<py311)
        from typing_extensions import Self


_LOGGER = logging.getLogger("filelock")


# This is a helper class which is returned by :meth:`BaseFileLock.acquire` and wraps the lock to make sure __enter__
# is not called twice when entering the with statement. If we would simply return *self*, the lock would be acquired
# again in the *__enter__* method of the BaseFileLock, but not released again automatically. issue #37 (memory leak)
class AcquireReturnProxy:
    """A context-aware object that will release the lock file when exiting."""

    def __init__(self, lock: BaseFileLock) -> None:
        self.lock = lock

    def __enter__(self) -> BaseFileLock:
        return self.lock

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.lock.release()


@dataclass
class FileLockContext:
    """A dataclass which holds the context for a ``BaseFileLock`` object."""

    # The context is held in a separate class to allow optional use of thread local storage via the
    # ThreadLocalFileContext class.

    #: The path to the lock file.
    lock_file: str

    #: The default timeout value.
    timeout: float

    #: The mode for the lock files
    mode: int

    #: Whether the lock should be blocking or not
    blocking: bool

    #: The file descriptor for the *_lock_file* as it is returned by the os.open() function, not None when lock held
    lock_file_fd: int | None = None

    #: The lock counter is used for implementing the nested locking mechanism.
    lock_counter: int = 0  # When the lock is acquired is increased and the lock is only released, when this value is 0


class ThreadLocalFileContext(FileLockContext, local):
    """A thread local version of the ``FileLockContext`` class."""


class FileLockMeta(ABCMeta):
    def __call__(  # noqa: PLR0913
        cls,
        lock_file: str | os.PathLike[str],
        timeout: float = -1,
        mode: int = 0o644,
        thread_local: bool = True,  # noqa: FBT001, FBT002
        *,
        blocking: bool = True,
        is_singleton: bool = False,
        **kwargs: Any,  # capture remaining kwargs for subclasses  # noqa: ANN401
    ) -> BaseFileLock:
        if is_singleton:
            instance = cls._instances.get(str(lock_file))  # type: ignore[attr-defined]
            if instance:
                params_to_check = {
                    "thread_local": (thread_local, instance.is_thread_local()),
                    "timeout": (timeout, instance.timeout),
                    "mode": (mode, instance.mode),
                    "blocking": (blocking, instance.blocking),
                }

                non_matching_params = {
                    name: (passed_param, set_param)
                    for name, (passed_param, set_param) in params_to_check.items()
                    if passed_param != set_param
                }
                if not non_matching_params:
                    return cast("BaseFileLock", instance)

                # parameters do not match; raise error
                msg = "Singleton lock instances cannot be initialized with differing arguments"
                msg += "\nNon-matching arguments: "
                for param_name, (passed_param, set_param) in non_matching_params.items():
                    msg += f"\n\t{param_name} (existing lock has {set_param} but {passed_param} was passed)"
                raise ValueError(msg)

        # Workaround to make `__init__`'s params optional in subclasses
        # E.g. virtualenv changes the signature of the `__init__` method in the `BaseFileLock` class descendant
        # (https://github.com/tox-dev/filelock/pull/340)

        all_params = {
            "timeout": timeout,
            "mode": mode,
            "thread_local": thread_local,
            "blocking": blocking,
            "is_singleton": is_singleton,
            **kwargs,
        }

        present_params = inspect.signature(cls.__init__).parameters  # type: ignore[misc]
        init_params = {key: value for key, value in all_params.items() if key in present_params}

        instance = super().__call__(lock_file, **init_params)

        if is_singleton:
            cls._instances[str(lock_file)] = instance  # type: ignore[attr-defined]

        return cast("BaseFileLock", instance)


class BaseFileLock(contextlib.ContextDecorator, metaclass=FileLockMeta):
    """Abstract base class for a file lock object."""

    _instances: WeakValueDictionary[str, BaseFileLock]

    def __init_subclass__(cls, **kwargs: dict[str, Any]) -> None:
        """Setup unique state for lock subclasses."""
        super().__init_subclass__(**kwargs)
        cls._instances = WeakValueDictionary()

    def __init__(  # noqa: PLR0913
        self,
        lock_file: str | os.PathLike[str],
        timeout: float = -1,
        mode: int = 0o644,
        thread_local: bool = True,  # noqa: FBT001, FBT002
        *,
        blocking: bool = True,
        is_singleton: bool = False,
    ) -> None:
        """
        Create a new lock object.

        :param lock_file: path to the file
        :param timeout: default timeout when acquiring the lock, in seconds. It will be used as fallback value in \
            the acquire method, if no timeout value (``None``) is given. If you want to disable the timeout, set it \
            to a negative value. A timeout of 0 means that there is exactly one attempt to acquire the file lock.
        :param mode: file permissions for the lockfile
        :param thread_local: Whether this object's internal context should be thread local or not. If this is set to \
            ``False`` then the lock will be reentrant across threads.
        :param blocking: whether the lock should be blocking or not
        :param is_singleton: If this is set to ``True`` then only one instance of this class will be created \
            per lock file. This is useful if you want to use the lock object for reentrant locking without needing \
            to pass the same object around.

        """
        self._is_thread_local = thread_local
        self._is_singleton = is_singleton

        # Create the context. Note that external code should not work with the context directly and should instead use
        # properties of this class.
        kwargs: dict[str, Any] = {
            "lock_file": os.fspath(lock_file),
            "timeout": timeout,
            "mode": mode,
            "blocking": blocking,
        }
        self._context: FileLockContext = (ThreadLocalFileContext if thread_local else FileLockContext)(**kwargs)

    def is_thread_local(self) -> bool:
        """:return: a flag indicating if this lock is thread local or not"""
        return self._is_thread_local

    @property
    def is_singleton(self) -> bool:
        """:return: a flag indicating if this lock is singleton or not"""
        return self._is_singleton

    @property
    def lock_file(self) -> str:
        """:return: path to the lock file"""
        return self._context.lock_file

    @property
    def timeout(self) -> float:
        """
        :return: the default timeout value, in seconds

        .. versionadded:: 2.0.0
        """
        return self._context.timeout

    @timeout.setter
    def timeout(self, value: float | str) -> None:
        """
        Change the default timeout value.

        :param value: the new value, in seconds

        """
        self._context.timeout = float(value)

    @property
    def blocking(self) -> bool:
        """:return: whether the locking is blocking or not"""
        return self._context.blocking

    @blocking.setter
    def blocking(self, value: bool) -> None:
        """
        Change the default blocking value.

        :param value: the new value as bool

        """
        self._context.blocking = value

    @property
    def mode(self) -> int:
        """:return: the file permissions for the lockfile"""
        return self._context.mode

    @abstractmethod
    def _acquire(self) -> None:
        """If the file lock could be acquired, self._context.lock_file_fd holds the file descriptor of the lock file."""
        raise NotImplementedError

    @abstractmethod
    def _release(self) -> None:
        """Releases the lock and sets self._context.lock_file_fd to None."""
        raise NotImplementedError

    @property
    def is_locked(self) -> bool:
        """

        :return: A boolean indicating if the lock file is holding the lock currently.

        .. versionchanged:: 2.0.0

            This was previously a method and is now a property.
        """
        return self._context.lock_file_fd is not None

    @property
    def lock_counter(self) -> int:
        """:return: The number of times this lock has been acquired (but not yet released)."""
        return self._context.lock_counter

    def acquire(
        self,
        timeout: float | None = None,
        poll_interval: float = 0.05,
        *,
        poll_intervall: float | None = None,
        blocking: bool | None = None,
    ) -> AcquireReturnProxy:
        """
        Try to acquire the file lock.

        :param timeout: maximum wait time for acquiring the lock, ``None`` means use the default :attr:`~timeout` is and
         if ``timeout < 0``, there is no timeout and this method will block until the lock could be acquired
        :param poll_interval: interval of trying to acquire the lock file
        :param poll_intervall: deprecated, kept for backwards compatibility, use ``poll_interval`` instead
        :param blocking: defaults to True. If False, function will return immediately if it cannot obtain a lock on the
         first attempt. Otherwise, this method will block until the timeout expires or the lock is acquired.
        :raises Timeout: if fails to acquire lock within the timeout period
        :return: a context object that will unlock the file when the context is exited

        .. code-block:: python

            # You can use this method in the context manager (recommended)
            with lock.acquire():
                pass

            # Or use an equivalent try-finally construct:
            lock.acquire()
            try:
                pass
            finally:
                lock.release()

        .. versionchanged:: 2.0.0

            This method returns now a *proxy* object instead of *self*,
            so that it can be used in a with statement without side effects.

        """
        # Use the default timeout, if no timeout is provided.
        if timeout is None:
            timeout = self._context.timeout

        if blocking is None:
            blocking = self._context.blocking

        if poll_intervall is not None:
            msg = "use poll_interval instead of poll_intervall"
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            poll_interval = poll_intervall

        # Increment the number right at the beginning. We can still undo it, if something fails.
        self._context.lock_counter += 1

        lock_id = id(self)
        lock_filename = self.lock_file
        start_time = time.perf_counter()
        try:
            while True:
                if not self.is_locked:
                    _LOGGER.debug("Attempting to acquire lock %s on %s", lock_id, lock_filename)
                    self._acquire()
                if self.is_locked:
                    _LOGGER.debug("Lock %s acquired on %s", lock_id, lock_filename)
                    break
                if blocking is False:
                    _LOGGER.debug("Failed to immediately acquire lock %s on %s", lock_id, lock_filename)
                    raise Timeout(lock_filename)  # noqa: TRY301
                if 0 <= timeout < time.perf_counter() - start_time:
                    _LOGGER.debug("Timeout on acquiring lock %s on %s", lock_id, lock_filename)
                    raise Timeout(lock_filename)  # noqa: TRY301
                msg = "Lock %s not acquired on %s, waiting %s seconds ..."
                _LOGGER.debug(msg, lock_id, lock_filename, poll_interval)
                time.sleep(poll_interval)
        except BaseException:  # Something did go wrong, so decrement the counter.
            self._context.lock_counter = max(0, self._context.lock_counter - 1)
            raise
        return AcquireReturnProxy(lock=self)

    def release(self, force: bool = False) -> None:  # noqa: FBT001, FBT002
        """
        Releases the file lock. Please note, that the lock is only completely released, if the lock counter is 0.
        Also note, that the lock file itself is not automatically deleted.

        :param force: If true, the lock counter is ignored and the lock is released in every case/

        """
        if self.is_locked:
            self._context.lock_counter -= 1

            if self._context.lock_counter == 0 or force:
                lock_id, lock_filename = id(self), self.lock_file

                _LOGGER.debug("Attempting to release lock %s on %s", lock_id, lock_filename)
                self._release()
                self._context.lock_counter = 0
                _LOGGER.debug("Lock %s released on %s", lock_id, lock_filename)

    def __enter__(self) -> Self:
        """
        Acquire the lock.

        :return: the lock object

        """
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Release the lock.

        :param exc_type: the exception type if raised
        :param exc_value: the exception value if raised
        :param traceback: the exception traceback if raised

        """
        self.release()

    def __del__(self) -> None:
        """Called when the lock object is deleted."""
        self.release(force=True)


__all__ = [
    "AcquireReturnProxy",
    "BaseFileLock",
]

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\shell32.py ===
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
Wrapper for shell32.dll in ctypes.
"""

# TODO
# * Add a class wrapper to SHELLEXECUTEINFO
# * More logic into ShellExecuteEx

__revision__ = "$Id$"

from winappdbg.win32.defines import *
from winappdbg.win32.kernel32 import LocalFree

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================

# --- Constants ----------------------------------------------------------------

SEE_MASK_DEFAULT = 0x00000000
SEE_MASK_CLASSNAME = 0x00000001
SEE_MASK_CLASSKEY = 0x00000003
SEE_MASK_IDLIST = 0x00000004
SEE_MASK_INVOKEIDLIST = 0x0000000C
SEE_MASK_ICON = 0x00000010
SEE_MASK_HOTKEY = 0x00000020
SEE_MASK_NOCLOSEPROCESS = 0x00000040
SEE_MASK_CONNECTNETDRV = 0x00000080
SEE_MASK_NOASYNC = 0x00000100
SEE_MASK_DOENVSUBST = 0x00000200
SEE_MASK_FLAG_NO_UI = 0x00000400
SEE_MASK_UNICODE = 0x00004000
SEE_MASK_NO_CONSOLE = 0x00008000
SEE_MASK_ASYNCOK = 0x00100000
SEE_MASK_HMONITOR = 0x00200000
SEE_MASK_NOZONECHECKS = 0x00800000
SEE_MASK_WAITFORINPUTIDLE = 0x02000000
SEE_MASK_FLAG_LOG_USAGE = 0x04000000

SE_ERR_FNF = 2
SE_ERR_PNF = 3
SE_ERR_ACCESSDENIED = 5
SE_ERR_OOM = 8
SE_ERR_DLLNOTFOUND = 32
SE_ERR_SHARE = 26
SE_ERR_ASSOCINCOMPLETE = 27
SE_ERR_DDETIMEOUT = 28
SE_ERR_DDEFAIL = 29
SE_ERR_DDEBUSY = 30
SE_ERR_NOASSOC = 31

SHGFP_TYPE_CURRENT = 0
SHGFP_TYPE_DEFAULT = 1

CSIDL_DESKTOP = 0x0000
CSIDL_INTERNET = 0x0001
CSIDL_PROGRAMS = 0x0002
CSIDL_CONTROLS = 0x0003
CSIDL_PRINTERS = 0x0004
CSIDL_PERSONAL = 0x0005
CSIDL_FAVORITES = 0x0006
CSIDL_STARTUP = 0x0007
CSIDL_RECENT = 0x0008
CSIDL_SENDTO = 0x0009
CSIDL_BITBUCKET = 0x000A
CSIDL_STARTMENU = 0x000B
CSIDL_MYDOCUMENTS = CSIDL_PERSONAL
CSIDL_MYMUSIC = 0x000D
CSIDL_MYVIDEO = 0x000E
CSIDL_DESKTOPDIRECTORY = 0x0010
CSIDL_DRIVES = 0x0011
CSIDL_NETWORK = 0x0012
CSIDL_NETHOOD = 0x0013
CSIDL_FONTS = 0x0014
CSIDL_TEMPLATES = 0x0015
CSIDL_COMMON_STARTMENU = 0x0016
CSIDL_COMMON_PROGRAMS = 0x0017
CSIDL_COMMON_STARTUP = 0x0018
CSIDL_COMMON_DESKTOPDIRECTORY = 0x0019
CSIDL_APPDATA = 0x001A
CSIDL_PRINTHOOD = 0x001B
CSIDL_LOCAL_APPDATA = 0x001C
CSIDL_ALTSTARTUP = 0x001D
CSIDL_COMMON_ALTSTARTUP = 0x001E
CSIDL_COMMON_FAVORITES = 0x001F
CSIDL_INTERNET_CACHE = 0x0020
CSIDL_COOKIES = 0x0021
CSIDL_HISTORY = 0x0022
CSIDL_COMMON_APPDATA = 0x0023
CSIDL_WINDOWS = 0x0024
CSIDL_SYSTEM = 0x0025
CSIDL_PROGRAM_FILES = 0x0026
CSIDL_MYPICTURES = 0x0027
CSIDL_PROFILE = 0x0028
CSIDL_SYSTEMX86 = 0x0029
CSIDL_PROGRAM_FILESX86 = 0x002A
CSIDL_PROGRAM_FILES_COMMON = 0x002B
CSIDL_PROGRAM_FILES_COMMONX86 = 0x002C
CSIDL_COMMON_TEMPLATES = 0x002D
CSIDL_COMMON_DOCUMENTS = 0x002E
CSIDL_COMMON_ADMINTOOLS = 0x002F
CSIDL_ADMINTOOLS = 0x0030
CSIDL_CONNECTIONS = 0x0031
CSIDL_COMMON_MUSIC = 0x0035
CSIDL_COMMON_PICTURES = 0x0036
CSIDL_COMMON_VIDEO = 0x0037
CSIDL_RESOURCES = 0x0038
CSIDL_RESOURCES_LOCALIZED = 0x0039
CSIDL_COMMON_OEM_LINKS = 0x003A
CSIDL_CDBURN_AREA = 0x003B
CSIDL_COMPUTERSNEARME = 0x003D
CSIDL_PROFILES = 0x003E

CSIDL_FOLDER_MASK = 0x00FF

CSIDL_FLAG_PER_USER_INIT = 0x0800
CSIDL_FLAG_NO_ALIAS = 0x1000
CSIDL_FLAG_DONT_VERIFY = 0x4000
CSIDL_FLAG_CREATE = 0x8000

CSIDL_FLAG_MASK = 0xFF00

# --- Structures ---------------------------------------------------------------

# typedef struct _SHELLEXECUTEINFO {
#   DWORD     cbSize;
#   ULONG     fMask;
#   HWND      hwnd;
#   LPCTSTR   lpVerb;
#   LPCTSTR   lpFile;
#   LPCTSTR   lpParameters;
#   LPCTSTR   lpDirectory;
#   int       nShow;
#   HINSTANCE hInstApp;
#   LPVOID    lpIDList;
#   LPCTSTR   lpClass;
#   HKEY      hkeyClass;
#   DWORD     dwHotKey;
#   union {
#     HANDLE hIcon;
#     HANDLE hMonitor;
#   } DUMMYUNIONNAME;
#   HANDLE    hProcess;
# } SHELLEXECUTEINFO, *LPSHELLEXECUTEINFO;


class SHELLEXECUTEINFO(Structure):
    _fields_ = [
        ("cbSize", DWORD),
        ("fMask", ULONG),
        ("hwnd", HWND),
        ("lpVerb", LPSTR),
        ("lpFile", LPSTR),
        ("lpParameters", LPSTR),
        ("lpDirectory", LPSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", HINSTANCE),
        ("lpIDList", LPVOID),
        ("lpClass", LPSTR),
        ("hkeyClass", HKEY),
        ("dwHotKey", DWORD),
        ("hIcon", HANDLE),
        ("hProcess", HANDLE),
    ]

    def __get_hMonitor(self):
        return self.hIcon

    def __set_hMonitor(self, hMonitor):
        self.hIcon = hMonitor

    hMonitor = property(__get_hMonitor, __set_hMonitor)


LPSHELLEXECUTEINFO = POINTER(SHELLEXECUTEINFO)

# --- shell32.dll --------------------------------------------------------------


# LPWSTR *CommandLineToArgvW(
#     LPCWSTR lpCmdLine,
#     int *pNumArgs
# );
def CommandLineToArgvW(lpCmdLine):
    _CommandLineToArgvW = windll.shell32.CommandLineToArgvW
    _CommandLineToArgvW.argtypes = [LPVOID, POINTER(ctypes.c_int)]
    _CommandLineToArgvW.restype = LPVOID

    if not lpCmdLine:
        lpCmdLine = None
    argc = ctypes.c_int(0)
    vptr = ctypes.windll.shell32.CommandLineToArgvW(lpCmdLine, byref(argc))
    if vptr == NULL:
        raise ctypes.WinError()
    argv = vptr
    try:
        argc = argc.value
        if argc <= 0:
            raise ctypes.WinError()
        argv = ctypes.cast(argv, ctypes.POINTER(LPWSTR * argc))
        argv = [argv.contents[i] for i in compat.xrange(0, argc)]
    finally:
        if vptr is not None:
            LocalFree(vptr)
    return argv


def CommandLineToArgvA(lpCmdLine):
    t_ansi = GuessStringType.t_ansi
    t_unicode = GuessStringType.t_unicode
    if isinstance(lpCmdLine, t_ansi):
        cmdline = t_unicode(lpCmdLine)
    else:
        cmdline = lpCmdLine
    return [t_ansi(x) for x in CommandLineToArgvW(cmdline)]


CommandLineToArgv = GuessStringType(CommandLineToArgvA, CommandLineToArgvW)


# HINSTANCE ShellExecute(
#     HWND hwnd,
#     LPCTSTR lpOperation,
#     LPCTSTR lpFile,
#     LPCTSTR lpParameters,
#     LPCTSTR lpDirectory,
#     INT nShowCmd
# );
def ShellExecuteA(hwnd=None, lpOperation=None, lpFile=None, lpParameters=None, lpDirectory=None, nShowCmd=None):
    _ShellExecuteA = windll.shell32.ShellExecuteA
    _ShellExecuteA.argtypes = [HWND, LPSTR, LPSTR, LPSTR, LPSTR, INT]
    _ShellExecuteA.restype = HINSTANCE

    if not nShowCmd:
        nShowCmd = 0
    success = _ShellExecuteA(hwnd, lpOperation, lpFile, lpParameters, lpDirectory, nShowCmd)
    success = ctypes.cast(success, c_int)
    success = success.value
    if not success > 32:  # weird! isn't it?
        raise ctypes.WinError(success)


def ShellExecuteW(hwnd=None, lpOperation=None, lpFile=None, lpParameters=None, lpDirectory=None, nShowCmd=None):
    _ShellExecuteW = windll.shell32.ShellExecuteW
    _ShellExecuteW.argtypes = [HWND, LPWSTR, LPWSTR, LPWSTR, LPWSTR, INT]
    _ShellExecuteW.restype = HINSTANCE

    if not nShowCmd:
        nShowCmd = 0
    success = _ShellExecuteW(hwnd, lpOperation, lpFile, lpParameters, lpDirectory, nShowCmd)
    success = ctypes.cast(success, c_int)
    success = success.value
    if not success > 32:  # weird! isn't it?
        raise ctypes.WinError(success)


ShellExecute = GuessStringType(ShellExecuteA, ShellExecuteW)


# BOOL ShellExecuteEx(
#   __inout  LPSHELLEXECUTEINFO lpExecInfo
# );
def ShellExecuteEx(lpExecInfo):
    if isinstance(lpExecInfo, SHELLEXECUTEINFOA):
        ShellExecuteExA(lpExecInfo)
    elif isinstance(lpExecInfo, SHELLEXECUTEINFOW):
        ShellExecuteExW(lpExecInfo)
    else:
        raise TypeError("Expected SHELLEXECUTEINFOA or SHELLEXECUTEINFOW, got %s instead" % type(lpExecInfo))


def ShellExecuteExA(lpExecInfo):
    _ShellExecuteExA = windll.shell32.ShellExecuteExA
    _ShellExecuteExA.argtypes = [LPSHELLEXECUTEINFOA]
    _ShellExecuteExA.restype = BOOL
    _ShellExecuteExA.errcheck = RaiseIfZero
    _ShellExecuteExA(byref(lpExecInfo))


def ShellExecuteExW(lpExecInfo):
    _ShellExecuteExW = windll.shell32.ShellExecuteExW
    _ShellExecuteExW.argtypes = [LPSHELLEXECUTEINFOW]
    _ShellExecuteExW.restype = BOOL
    _ShellExecuteExW.errcheck = RaiseIfZero
    _ShellExecuteExW(byref(lpExecInfo))


# HINSTANCE FindExecutable(
#   __in      LPCTSTR lpFile,
#   __in_opt  LPCTSTR lpDirectory,
#   __out     LPTSTR lpResult
# );
def FindExecutableA(lpFile, lpDirectory=None):
    _FindExecutableA = windll.shell32.FindExecutableA
    _FindExecutableA.argtypes = [LPSTR, LPSTR, LPSTR]
    _FindExecutableA.restype = HINSTANCE

    lpResult = ctypes.create_string_buffer(MAX_PATH)
    success = _FindExecutableA(lpFile, lpDirectory, lpResult)
    success = ctypes.cast(success, ctypes.c_void_p)
    success = success.value
    if not success > 32:  # weird! isn't it?
        raise ctypes.WinError(success)
    return lpResult.value


def FindExecutableW(lpFile, lpDirectory=None):
    _FindExecutableW = windll.shell32.FindExecutableW
    _FindExecutableW.argtypes = [LPWSTR, LPWSTR, LPWSTR]
    _FindExecutableW.restype = HINSTANCE

    lpResult = ctypes.create_unicode_buffer(MAX_PATH)
    success = _FindExecutableW(lpFile, lpDirectory, lpResult)
    success = ctypes.cast(success, ctypes.c_void_p)
    success = success.value
    if not success > 32:  # weird! isn't it?
        raise ctypes.WinError(success)
    return lpResult.value


FindExecutable = GuessStringType(FindExecutableA, FindExecutableW)


# HRESULT SHGetFolderPath(
#   __in   HWND hwndOwner,
#   __in   int nFolder,
#   __in   HANDLE hToken,
#   __in   DWORD dwFlags,
#   __out  LPTSTR pszPath
# );
def SHGetFolderPathA(nFolder, hToken=None, dwFlags=SHGFP_TYPE_CURRENT):
    _SHGetFolderPathA = windll.shell32.SHGetFolderPathA  # shfolder.dll in older win versions
    _SHGetFolderPathA.argtypes = [HWND, ctypes.c_int, HANDLE, DWORD, LPSTR]
    _SHGetFolderPathA.restype = HRESULT
    _SHGetFolderPathA.errcheck = RaiseIfNotZero  # S_OK == 0

    pszPath = ctypes.create_string_buffer(MAX_PATH + 1)
    _SHGetFolderPathA(None, nFolder, hToken, dwFlags, pszPath)
    return pszPath.value


def SHGetFolderPathW(nFolder, hToken=None, dwFlags=SHGFP_TYPE_CURRENT):
    _SHGetFolderPathW = windll.shell32.SHGetFolderPathW  # shfolder.dll in older win versions
    _SHGetFolderPathW.argtypes = [HWND, ctypes.c_int, HANDLE, DWORD, LPWSTR]
    _SHGetFolderPathW.restype = HRESULT
    _SHGetFolderPathW.errcheck = RaiseIfNotZero  # S_OK == 0

    pszPath = ctypes.create_unicode_buffer(MAX_PATH + 1)
    _SHGetFolderPathW(None, nFolder, hToken, dwFlags, pszPath)
    return pszPath.value


SHGetFolderPath = DefaultStringType(SHGetFolderPathA, SHGetFolderPathW)


# BOOL IsUserAnAdmin(void);
def IsUserAnAdmin():
    # Supposedly, IsUserAnAdmin() is deprecated in Vista.
    # But I tried it on Windows 7 and it works just fine.
    _IsUserAnAdmin = windll.shell32.IsUserAnAdmin
    _IsUserAnAdmin.argtypes = []
    _IsUserAnAdmin.restype = bool
    return _IsUserAnAdmin()


# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai_like\chat\handler.py ===
"""
OpenAI-like chat completion handler

For handling OpenAI-like chat completions, like IBM WatsonX, etc.
"""

import json
from typing import Any, Callable, Optional, Union

import httpx

import litellm
from litellm import LlmProviders
from litellm.llms.bedrock.chat.invoke_handler import MockResponseIterator
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from litellm.llms.databricks.streaming_utils import ModelResponseIterator
from litellm.llms.openai.chat.gpt_transformation import OpenAIGPTConfig
from litellm.llms.openai.openai import OpenAIConfig
from litellm.types.utils import CustomStreamingDecoder, ModelResponse
from litellm.utils import CustomStreamWrapper, ProviderConfigManager

from ..common_utils import OpenAILikeBase, OpenAILikeError
from .transformation import OpenAILikeChatConfig


async def make_call(
    client: Optional[AsyncHTTPHandler],
    api_base: str,
    headers: dict,
    data: str,
    model: str,
    messages: list,
    logging_obj,
    streaming_decoder: Optional[CustomStreamingDecoder] = None,
    fake_stream: bool = False,
):
    if client is None:
        client = litellm.module_level_aclient

    response = await client.post(
        api_base, headers=headers, data=data, stream=not fake_stream
    )

    if streaming_decoder is not None:
        completion_stream: Any = streaming_decoder.aiter_bytes(
            response.aiter_bytes(chunk_size=1024)
        )
    elif fake_stream:
        model_response = ModelResponse(**response.json())
        completion_stream = MockResponseIterator(model_response=model_response)
    else:
        completion_stream = ModelResponseIterator(
            streaming_response=response.aiter_lines(), sync_stream=False
        )
    # LOGGING
    logging_obj.post_call(
        input=messages,
        api_key="",
        original_response=completion_stream,  # Pass the completion stream for logging
        additional_args={"complete_input_dict": data},
    )

    return completion_stream


def make_sync_call(
    client: Optional[HTTPHandler],
    api_base: str,
    headers: dict,
    data: str,
    model: str,
    messages: list,
    logging_obj,
    streaming_decoder: Optional[CustomStreamingDecoder] = None,
    fake_stream: bool = False,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
):
    if client is None:
        client = litellm.module_level_client  # Create a new client if none provided

    response = client.post(
        api_base, headers=headers, data=data, stream=not fake_stream, timeout=timeout
    )

    if response.status_code != 200:
        raise OpenAILikeError(status_code=response.status_code, message=response.read())

    if streaming_decoder is not None:
        completion_stream = streaming_decoder.iter_bytes(
            response.iter_bytes(chunk_size=1024)
        )
    elif fake_stream:
        model_response = ModelResponse(**response.json())
        completion_stream = MockResponseIterator(model_response=model_response)
    else:
        completion_stream = ModelResponseIterator(
            streaming_response=response.iter_lines(), sync_stream=True
        )

    # LOGGING
    logging_obj.post_call(
        input=messages,
        api_key="",
        original_response="first stream response received",
        additional_args={"complete_input_dict": data},
    )

    return completion_stream


class OpenAILikeChatHandler(OpenAILikeBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def acompletion_stream_function(
        self,
        model: str,
        messages: list,
        custom_llm_provider: str,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        api_key,
        logging_obj,
        stream,
        data: dict,
        optional_params=None,
        litellm_params=None,
        logger_fn=None,
        headers={},
        client: Optional[AsyncHTTPHandler] = None,
        streaming_decoder: Optional[CustomStreamingDecoder] = None,
        fake_stream: bool = False,
    ) -> CustomStreamWrapper:
        data["stream"] = True
        completion_stream = await make_call(
            client=client,
            api_base=api_base,
            headers=headers,
            data=json.dumps(data),
            model=model,
            messages=messages,
            logging_obj=logging_obj,
            streaming_decoder=streaming_decoder,
        )
        streamwrapper = CustomStreamWrapper(
            completion_stream=completion_stream,
            model=model,
            custom_llm_provider=custom_llm_provider,
            logging_obj=logging_obj,
        )

        return streamwrapper

    async def acompletion_function(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        custom_llm_provider: str,
        print_verbose: Callable,
        client: Optional[AsyncHTTPHandler],
        encoding,
        api_key,
        logging_obj,
        stream,
        data: dict,
        base_model: Optional[str],
        optional_params: dict,
        litellm_params=None,
        logger_fn=None,
        headers={},
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        json_mode: bool = False,
    ) -> ModelResponse:
        if timeout is None:
            timeout = httpx.Timeout(timeout=600.0, connect=5.0)

        if client is None:
            client = litellm.module_level_aclient

        try:
            response = await client.post(
                api_base, headers=headers, data=json.dumps(data), timeout=timeout
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise OpenAILikeError(
                status_code=e.response.status_code,
                message=e.response.text,
            )
        except httpx.TimeoutException:
            raise OpenAILikeError(status_code=408, message="Timeout error occurred.")
        except Exception as e:
            raise OpenAILikeError(status_code=500, message=str(e))

        return OpenAILikeChatConfig._transform_response(
            model=model,
            response=response,
            model_response=model_response,
            stream=stream,
            logging_obj=logging_obj,
            optional_params=optional_params,
            api_key=api_key,
            data=data,
            messages=messages,
            print_verbose=print_verbose,
            encoding=encoding,
            json_mode=json_mode,
            custom_llm_provider=custom_llm_provider,
            base_model=base_model,
        )

    def completion(
        self,
        *,
        model: str,
        messages: list,
        api_base: str,
        custom_llm_provider: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        api_key: Optional[str],
        logging_obj,
        optional_params: dict,
        acompletion=None,
        litellm_params: dict = {},
        logger_fn=None,
        headers: Optional[dict] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        custom_endpoint: Optional[bool] = None,
        streaming_decoder: Optional[
            CustomStreamingDecoder
        ] = None,  # if openai-compatible api needs custom stream decoder - e.g. sagemaker
        fake_stream: bool = False,
    ):
        custom_endpoint = custom_endpoint or optional_params.pop(
            "custom_endpoint", None
        )
        base_model: Optional[str] = optional_params.pop("base_model", None)
        api_base, headers = self._validate_environment(
            api_base=api_base,
            api_key=api_key,
            endpoint_type="chat_completions",
            custom_endpoint=custom_endpoint,
            headers=headers,
        )

        stream: bool = optional_params.pop("stream", None) or False
        extra_body = optional_params.pop("extra_body", {})
        json_mode = optional_params.pop("json_mode", None)
        optional_params.pop("max_retries", None)
        if not fake_stream:
            optional_params["stream"] = stream

        if messages is not None and custom_llm_provider is not None:
            provider_config = ProviderConfigManager.get_provider_chat_config(
                model=model, provider=LlmProviders(custom_llm_provider)
            )
            if isinstance(provider_config, OpenAIGPTConfig) or isinstance(
                provider_config, OpenAIConfig
            ):
                messages = provider_config._transform_messages(
                    messages=messages, model=model
                )

        data = {
            "model": model,
            "messages": messages,
            **optional_params,
            **extra_body,
        }

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
        if acompletion is True:
            if client is None or not isinstance(client, AsyncHTTPHandler):
                client = None
            if (
                stream is True
            ):  # if function call - fake the streaming (need complete blocks for output parsing in openai format)
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
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    headers=headers,
                    client=client,
                    custom_llm_provider=custom_llm_provider,
                    streaming_decoder=streaming_decoder,
                    fake_stream=fake_stream,
                )
            else:
                return self.acompletion_function(
                    model=model,
                    messages=messages,
                    data=data,
                    api_base=api_base,
                    custom_prompt_dict=custom_prompt_dict,
                    custom_llm_provider=custom_llm_provider,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    encoding=encoding,
                    api_key=api_key,
                    logging_obj=logging_obj,
                    optional_params=optional_params,
                    stream=stream,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    headers=headers,
                    timeout=timeout,
                    base_model=base_model,
                    client=client,
                    json_mode=json_mode,
                )
        else:
            ## COMPLETION CALL
            if stream is True:
                completion_stream = make_sync_call(
                    client=(
                        client
                        if client is not None and isinstance(client, HTTPHandler)
                        else None
                    ),
                    api_base=api_base,
                    headers=headers,
                    data=json.dumps(data),
                    model=model,
                    messages=messages,
                    logging_obj=logging_obj,
                    streaming_decoder=streaming_decoder,
                    fake_stream=fake_stream,
                    timeout=timeout,
                )
                # completion_stream.__iter__()
                return CustomStreamWrapper(
                    completion_stream=completion_stream,
                    model=model,
                    custom_llm_provider=custom_llm_provider,
                    logging_obj=logging_obj,
                )
            else:
                if client is None or not isinstance(client, HTTPHandler):
                    client = HTTPHandler(timeout=timeout)  # type: ignore
                try:
                    response = client.post(
                        url=api_base, headers=headers, data=json.dumps(data)
                    )
                    response.raise_for_status()

                except httpx.HTTPStatusError as e:
                    raise OpenAILikeError(
                        status_code=e.response.status_code,
                        message=e.response.text,
                    )
                except httpx.TimeoutException:
                    raise OpenAILikeError(
                        status_code=408, message="Timeout error occurred."
                    )
                except Exception as e:
                    raise OpenAILikeError(status_code=500, message=str(e))
        return OpenAILikeChatConfig._transform_response(
            model=model,
            response=response,
            model_response=model_response,
            stream=stream,
            logging_obj=logging_obj,
            optional_params=optional_params,
            api_key=api_key,
            data=data,
            messages=messages,
            print_verbose=print_verbose,
            encoding=encoding,
            json_mode=json_mode,
            custom_llm_provider=custom_llm_provider,
            base_model=base_model,
        )

# === NexusCore/openenv\Lib\site-packages\tokenizers\tools\visualizer.py ===
import itertools
import os
import re
from string import Template
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

from tokenizers import Encoding, Tokenizer


dirname = os.path.dirname(__file__)
css_filename = os.path.join(dirname, "visualizer-styles.css")
with open(css_filename) as f:
    css = f.read()


class Annotation:
    start: int
    end: int
    label: int

    def __init__(self, start: int, end: int, label: str):
        self.start = start
        self.end = end
        self.label = label


AnnotationList = List[Annotation]
PartialIntList = List[Optional[int]]


class CharStateKey(NamedTuple):
    token_ix: Optional[int]
    anno_ix: Optional[int]


class CharState:
    char_ix: Optional[int]

    def __init__(self, char_ix):
        self.char_ix = char_ix

        self.anno_ix: Optional[int] = None
        self.tokens: List[int] = []

    @property
    def token_ix(self):
        return self.tokens[0] if len(self.tokens) > 0 else None

    @property
    def is_multitoken(self):
        """
        BPE tokenizers can output more than one token for a char
        """
        return len(self.tokens) > 1

    def partition_key(self) -> CharStateKey:
        return CharStateKey(
            token_ix=self.token_ix,
            anno_ix=self.anno_ix,
        )


class Aligned:
    pass


class EncodingVisualizer:
    """
    Build an EncodingVisualizer

    Args:

         tokenizer (:class:`~tokenizers.Tokenizer`):
            A tokenizer instance

         default_to_notebook (:obj:`bool`):
            Whether to render html output in a notebook by default

         annotation_converter (:obj:`Callable`, `optional`):
            An optional (lambda) function that takes an annotation in any format and returns
            an Annotation object
    """

    unk_token_regex = re.compile("(.{1}\b)?(unk|oov)(\b.{1})?", flags=re.IGNORECASE)

    def __init__(
        self,
        tokenizer: Tokenizer,
        default_to_notebook: bool = True,
        annotation_converter: Optional[Callable[[Any], Annotation]] = None,
    ):
        if default_to_notebook:
            try:
                from IPython.core.display import HTML, display
            except ImportError:
                raise Exception(
                    """We couldn't import IPython utils for html display.
                        Are you running in a notebook?
                        You can also pass `default_to_notebook=False` to get back raw HTML
                    """
                )

        self.tokenizer = tokenizer
        self.default_to_notebook = default_to_notebook
        self.annotation_coverter = annotation_converter
        pass

    def __call__(
        self,
        text: str,
        annotations: AnnotationList = [],
        default_to_notebook: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Build a visualization of the given text

        Args:
            text (:obj:`str`):
                The text to tokenize

            annotations (:obj:`List[Annotation]`, `optional`):
                An optional list of annotations of the text. The can either be an annotation class
                or anything else if you instantiated the visualizer with a converter function

            default_to_notebook (:obj:`bool`, `optional`, defaults to `False`):
                If True, will render the html in a notebook. Otherwise returns an html string.

        Returns:
            The HTML string if default_to_notebook is False, otherwise (default) returns None and
            renders the HTML in the notebook

        """
        final_default_to_notebook = self.default_to_notebook
        if default_to_notebook is not None:
            final_default_to_notebook = default_to_notebook
        if final_default_to_notebook:
            try:
                from IPython.core.display import HTML, display
            except ImportError:
                raise Exception(
                    """We couldn't import IPython utils for html display.
                    Are you running in a notebook?"""
                )
        if self.annotation_coverter is not None:
            annotations = list(map(self.annotation_coverter, annotations))
        encoding = self.tokenizer.encode(text)
        html = EncodingVisualizer.__make_html(text, encoding, annotations)
        if final_default_to_notebook:
            display(HTML(html))
        else:
            return html

    @staticmethod
    def calculate_label_colors(annotations: AnnotationList) -> Dict[str, str]:
        """
        Generates a color palette for all the labels in a given set of annotations

        Args:
          annotations (:obj:`Annotation`):
            A list of annotations

        Returns:
            :obj:`dict`: A dictionary mapping labels to colors in HSL format
        """
        if len(annotations) == 0:
            return {}
        labels = set(map(lambda x: x.label, annotations))
        num_labels = len(labels)
        h_step = int(255 / num_labels)
        if h_step < 20:
            h_step = 20
        s = 32
        l = 64  # noqa: E741
        h = 10
        colors = {}

        for label in sorted(labels):  # sort so we always get the same colors for a given set of labels
            colors[label] = f"hsl({h},{s}%,{l}%"
            h += h_step
        return colors

    @staticmethod
    def consecutive_chars_to_html(
        consecutive_chars_list: List[CharState],
        text: str,
        encoding: Encoding,
    ):
        """
        Converts a list of "consecutive chars" into a single HTML element.
        Chars are consecutive if they fall under the same word, token and annotation.
        The CharState class is a named tuple with a "partition_key" method that makes it easy to
        compare if two chars are consecutive.

        Args:
            consecutive_chars_list (:obj:`List[CharState]`):
                A list of CharStates that have been grouped together

            text (:obj:`str`):
                The original text being processed

            encoding (:class:`~tokenizers.Encoding`):
                The encoding returned from the tokenizer

        Returns:
            :obj:`str`: The HTML span for a set of consecutive chars
        """
        first = consecutive_chars_list[0]
        if first.char_ix is None:
            # its a special token
            stoken = encoding.tokens[first.token_ix]
            # special tokens are represented as empty spans. We use the data attribute and css
            # magic to display it
            return f'<span class="special-token" data-stoken={stoken}></span>'
        # We're not in a special token so this group has a start and end.
        last = consecutive_chars_list[-1]
        start = first.char_ix
        end = last.char_ix + 1
        span_text = text[start:end]
        css_classes = []  # What css classes will we apply on the resulting span
        data_items = {}  # What data attributes will we apply on the result span
        if first.token_ix is not None:
            # We can either be in a token or not (e.g. in white space)
            css_classes.append("token")
            if first.is_multitoken:
                css_classes.append("multi-token")
            if first.token_ix % 2:
                # We use this to color alternating tokens.
                # A token might be split by an annotation that ends in the middle of it, so this
                # lets us visually indicate a consecutive token despite its possible splitting in
                # the html markup
                css_classes.append("odd-token")
            else:
                # Like above, but a different color so we can see the tokens alternate
                css_classes.append("even-token")
            if EncodingVisualizer.unk_token_regex.search(encoding.tokens[first.token_ix]) is not None:
                # This is a special token that is in the text. probably UNK
                css_classes.append("special-token")
                # TODO is this the right name for the data attribute ?
                data_items["stok"] = encoding.tokens[first.token_ix]
        else:
            # In this case we are looking at a group/single char that is not tokenized.
            # e.g. white space
            css_classes.append("non-token")
        css = f'''class="{" ".join(css_classes)}"'''
        data = ""
        for key, val in data_items.items():
            data += f' data-{key}="{val}"'
        return f"<span {css} {data} >{span_text}</span>"

    @staticmethod
    def __make_html(text: str, encoding: Encoding, annotations: AnnotationList) -> str:
        char_states = EncodingVisualizer.__make_char_states(text, encoding, annotations)
        current_consecutive_chars = [char_states[0]]
        prev_anno_ix = char_states[0].anno_ix
        spans = []
        label_colors_dict = EncodingVisualizer.calculate_label_colors(annotations)
        cur_anno_ix = char_states[0].anno_ix
        if cur_anno_ix is not None:
            # If we started in an  annotation make a span for it
            anno = annotations[cur_anno_ix]
            label = anno.label
            color = label_colors_dict[label]
            spans.append(f'<span class="annotation" style="color:{color}" data-label="{label}">')

        for cs in char_states[1:]:
            cur_anno_ix = cs.anno_ix
            if cur_anno_ix != prev_anno_ix:
                # If we've transitioned in or out of an annotation
                spans.append(
                    # Create a span from the current consecutive characters
                    EncodingVisualizer.consecutive_chars_to_html(
                        current_consecutive_chars,
                        text=text,
                        encoding=encoding,
                    )
                )
                current_consecutive_chars = [cs]

                if prev_anno_ix is not None:
                    # if we transitioned out of an annotation close it's span
                    spans.append("</span>")
                if cur_anno_ix is not None:
                    # If we entered a new annotation make a span for it
                    anno = annotations[cur_anno_ix]
                    label = anno.label
                    color = label_colors_dict[label]
                    spans.append(f'<span class="annotation" style="color:{color}" data-label="{label}">')
            prev_anno_ix = cur_anno_ix

            if cs.partition_key() == current_consecutive_chars[0].partition_key():
                # If the current charchter is in the same "group" as the previous one
                current_consecutive_chars.append(cs)
            else:
                # Otherwise we make a span for the previous group
                spans.append(
                    EncodingVisualizer.consecutive_chars_to_html(
                        current_consecutive_chars,
                        text=text,
                        encoding=encoding,
                    )
                )
                # An reset the consecutive_char_list to form a new group
                current_consecutive_chars = [cs]
        # All that's left is to fill out the final span
        # TODO I think there is an edge case here where an annotation's span might not close
        spans.append(
            EncodingVisualizer.consecutive_chars_to_html(
                current_consecutive_chars,
                text=text,
                encoding=encoding,
            )
        )
        res = HTMLBody(spans)  # Send the list of spans to the body of our html
        return res

    @staticmethod
    def __make_anno_map(text: str, annotations: AnnotationList) -> PartialIntList:
        """
        Args:
            text (:obj:`str`):
                The raw text we want to align to

            annotations (:obj:`AnnotationList`):
                A (possibly empty) list of annotations

        Returns:
            A list of  length len(text) whose entry at index i is None if there is no annotation on
            character i or k, the index of the annotation that covers index i where k is with
            respect to the list of annotations
        """
        annotation_map = [None] * len(text)
        for anno_ix, a in enumerate(annotations):
            for i in range(a.start, a.end):
                annotation_map[i] = anno_ix
        return annotation_map

    @staticmethod
    def __make_char_states(text: str, encoding: Encoding, annotations: AnnotationList) -> List[CharState]:
        """
        For each character in the original text, we emit a tuple representing it's "state":

            * which token_ix it corresponds to
            * which word_ix it corresponds to
            * which annotation_ix it corresponds to

        Args:
            text (:obj:`str`):
                The raw text we want to align to

            annotations (:obj:`List[Annotation]`):
                A (possibly empty) list of annotations

            encoding: (:class:`~tokenizers.Encoding`):
                The encoding returned from the tokenizer

        Returns:
            :obj:`List[CharState]`: A list of CharStates, indicating for each char in the text what
            it's state is
        """
        annotation_map = EncodingVisualizer.__make_anno_map(text, annotations)
        # Todo make this a dataclass or named tuple
        char_states: List[CharState] = [CharState(char_ix) for char_ix in range(len(text))]
        for token_ix, token in enumerate(encoding.tokens):
            offsets = encoding.token_to_chars(token_ix)
            if offsets is not None:
                start, end = offsets
                for i in range(start, end):
                    char_states[i].tokens.append(token_ix)
        for char_ix, anno_ix in enumerate(annotation_map):
            char_states[char_ix].anno_ix = anno_ix

        return char_states


def HTMLBody(children: List[str], css_styles=css) -> str:
    """
    Generates the full html with css from a list of html spans

    Args:
        children (:obj:`List[str]`):
            A list of strings, assumed to be html elements

        css_styles (:obj:`str`, `optional`):
            Optional alternative implementation of the css

    Returns:
        :obj:`str`: An HTML string with style markup
    """
    children_text = "".join(children)
    return f"""
    <html>
        <head>
            <style>
                {css_styles}
            </style>
        </head>
        <body>
            <div class="tokenized-text" dir=auto>
            {children_text}
            </div>
        </body>
    </html>
    """

# === NexusCore/openenv\Lib\site-packages\trio\_tools\gen_exports.py ===
#! /usr/bin/env python3
"""
Code generation script for class methods
to be exported as public API
"""
from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING

import attrs

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from typing_extensions import TypeGuard

# keep these imports up to date with conditional imports in test_gen_exports
# isort: split
import astor

PREFIX = "_generated"

HEADER = """# ***********************************************************
# ******* WARNING: AUTOGENERATED! ALL EDITS WILL BE LOST ******
# *************************************************************
from __future__ import annotations

import sys

from ._ki import enable_ki_protection
from ._run import GLOBAL_RUN_CONTEXT
"""

TEMPLATE = """try:
    return{}GLOBAL_RUN_CONTEXT.{}.{}
except AttributeError:
    raise RuntimeError("must be called from async context") from None
"""


@attrs.define
class File:
    path: Path
    modname: str
    platform: str = attrs.field(default="", kw_only=True)
    imports: str = attrs.field(default="", kw_only=True)


def is_function(node: ast.AST) -> TypeGuard[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Check if the AST node is either a function
    or an async function
    """
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))


def is_public(node: ast.AST) -> TypeGuard[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Check if the AST node has a _public decorator"""
    if is_function(node):
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "_public":
                return True
    return False


def get_public_methods(
    tree: ast.AST,
) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return a list of methods marked as public.
    The function walks the given tree and extracts
    all objects that are functions which are marked
    public.
    """
    for node in ast.walk(tree):
        if is_public(node):
            yield node


def create_passthrough_args(funcdef: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Given a function definition, create a string that represents taking all
    the arguments from the function, and passing them through to another
    invocation of the same function.

    Example input: ast.parse("def f(a, *, b): ...")
    Example output: "(a, b=b)"
    """
    call_args = [arg.arg for arg in funcdef.args.args]
    if funcdef.args.vararg:
        call_args.append("*" + funcdef.args.vararg.arg)
    for arg in funcdef.args.kwonlyargs:
        call_args.append(arg.arg + "=" + arg.arg)  # noqa: PERF401  # clarity
    if funcdef.args.kwarg:
        call_args.append("**" + funcdef.args.kwarg.arg)
    return "({})".format(", ".join(call_args))


def run_black(file: File, source: str) -> tuple[bool, str]:
    """Run black on the specified file.

    Returns:
      Tuple of success and result string.
      ex.:
        (False, "Failed to run black!\nerror: cannot format ...")
        (True, "<formatted source>")

    Raises:
      ImportError: If black is not installed.
    """
    # imported to check that `subprocess` calls will succeed
    import black  # noqa: F401

    # Black has an undocumented API, but it doesn't easily allow reading configuration from
    # pyproject.toml, and simultaneously pass in / receive the code as a string.
    # https://github.com/psf/black/issues/779
    result = subprocess.run(
        # "-" as a filename = use stdin, return on stdout.
        [sys.executable, "-m", "black", "--stdin-filename", file.path, "-"],
        input=source,
        capture_output=True,
        encoding="utf8",
    )

    if result.returncode != 0:
        return False, f"Failed to run black!\n{result.stderr}"
    return True, result.stdout


def run_ruff(file: File, source: str) -> tuple[bool, str]:
    """Run ruff on the specified file.

    Returns:
      Tuple of success and result string.
      ex.:
        (False, "Failed to run ruff!\nerror: Failed to parse ...")
        (True, "<formatted source>")

    Raises:
      ImportError: If ruff is not installed.
    """
    # imported to check that `subprocess` calls will succeed
    import ruff  # noqa: F401

    result = subprocess.run(
        # "-" as a filename = use stdin, return on stdout.
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--fix",
            "--unsafe-fixes",
            "--stdin-filename",
            file.path,
            "-",
        ],
        input=source,
        capture_output=True,
        encoding="utf8",
    )

    if result.returncode != 0:
        return False, f"Failed to run ruff!\n{result.stderr}"
    return True, result.stdout


def run_linters(file: File, source: str) -> str:
    """Format the specified file using black and ruff.

    Returns:
      Formatted source code.

    Raises:
      ImportError: If either is not installed.
      SystemExit: If either failed.
    """

    for fn in (run_black, run_ruff):
        success, source = fn(file, source)
        if not success:
            print(source)
            sys.exit(1)

    return source


def gen_public_wrappers_source(file: File) -> str:
    """Scan the given .py file for @_public decorators, and generate wrapper
    functions.

    """
    header = [HEADER]
    header.append(file.imports)
    if file.platform:
        # Simple checks to avoid repeating imports. If this messes up, type checkers/tests will
        # just give errors.
        if "TYPE_CHECKING" not in file.imports:
            header.append("from typing import TYPE_CHECKING\n")
        if "import sys" not in file.imports:  # pragma: no cover
            header.append("import sys\n")
        header.append(
            f'\nassert not TYPE_CHECKING or sys.platform=="{file.platform}"\n',
        )

    generated = ["".join(header)]

    source = astor.code_to_ast.parse_file(file.path)
    method_names = []
    for method in get_public_methods(source):
        # Remove self from arguments
        assert method.args.args[0].arg == "self"
        del method.args.args[0]
        method_names.append(method.name)

        for dec in method.decorator_list:  # pragma: no cover
            if isinstance(dec, ast.Name) and dec.id == "contextmanager":
                is_cm = True
                break
        else:
            is_cm = False

        # Remove decorators
        method.decorator_list = [ast.Name("enable_ki_protection")]

        # Create pass through arguments
        new_args = create_passthrough_args(method)

        # Remove method body without the docstring
        if ast.get_docstring(method) is None:
            del method.body[:]
        else:
            # The first entry is always the docstring
            del method.body[1:]

        # Create the function definition including the body
        func = astor.to_source(method, indent_with=" " * 4)

        if is_cm:  # pragma: no cover
            func = func.replace("->Iterator", "->AbstractContextManager")

        # Create export function body
        template = TEMPLATE.format(
            " await " if isinstance(method, ast.AsyncFunctionDef) else " ",
            file.modname,
            method.name + new_args,
        )

        # Assemble function definition arguments and body
        snippet = func + indent(template, " " * 4)

        # Append the snippet to the corresponding module
        generated.append(snippet)

    method_names.sort()
    # Insert after the header, before function definitions
    generated.insert(1, f"__all__ = {method_names!r}")
    return "\n\n".join(generated)


def matches_disk_files(new_files: dict[str, str]) -> bool:
    for new_path, new_source in new_files.items():
        if not os.path.exists(new_path):
            return False
        old_source = Path(new_path).read_text(encoding="utf-8")
        if old_source != new_source:
            return False
    return True


def process(files: Iterable[File], *, do_test: bool) -> None:
    new_files = {}
    for file in files:
        print("Scanning:", file.path)
        new_source = gen_public_wrappers_source(file)
        new_source = run_linters(file, new_source)
        dirname, basename = os.path.split(file.path)
        new_path = os.path.join(dirname, PREFIX + basename)
        new_files[new_path] = new_source
    matches_disk = matches_disk_files(new_files)
    if do_test:
        if not matches_disk:
            print("Generated sources are outdated. Please regenerate.")
            sys.exit(1)
        else:
            print("Generated sources are up to date.")
    else:
        for new_path, new_source in new_files.items():
            with open(new_path, "w", encoding="utf-8", newline="\n") as fp:
                fp.write(new_source)
        print("Regenerated sources successfully.")
        if not matches_disk:  # TODO: test this branch
            # With pre-commit integration, show that we edited files.
            sys.exit(1)


# This is in fact run in CI, but only in the formatting check job, which
# doesn't collect coverage.
def main() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Generate python code for public api wrappers",
    )
    parser.add_argument(
        "--test",
        "-t",
        action="store_true",
        help="test if code is still up to date",
    )
    parsed_args = parser.parse_args()

    source_root = Path.cwd()
    # Double-check we found the right directory
    assert (source_root / "LICENSE").exists()
    core = source_root / "src/trio/_core"
    to_wrap = [
        File(core / "_run.py", "runner", imports=IMPORTS_RUN),
        File(
            core / "_instrumentation.py",
            "runner.instruments",
            imports=IMPORTS_INSTRUMENT,
        ),
        File(
            core / "_io_windows.py",
            "runner.io_manager",
            platform="win32",
            imports=IMPORTS_WINDOWS,
        ),
        File(
            core / "_io_epoll.py",
            "runner.io_manager",
            platform="linux",
            imports=IMPORTS_EPOLL,
        ),
        File(
            core / "_io_kqueue.py",
            "runner.io_manager",
            platform="darwin",
            imports=IMPORTS_KQUEUE,
        ),
    ]

    process(to_wrap, do_test=parsed_args.test)


IMPORTS_RUN = """\
from collections.abc import Awaitable, Callable
from typing import Any, TYPE_CHECKING

from outcome import Outcome
import contextvars

from ._run import _NO_SEND, RunStatistics, Task
from ._entry_queue import TrioToken
from .._abc import Clock

if TYPE_CHECKING:
    from typing_extensions import Unpack
    from ._run import PosArgT
"""
IMPORTS_INSTRUMENT = """\
from ._instrumentation import Instrument
"""

IMPORTS_EPOLL = """\
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._file_io import _HasFileNo
"""

IMPORTS_KQUEUE = """\
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import select
    from collections.abc import Callable
    from contextlib import AbstractContextManager

    from .. import _core
    from .._file_io import _HasFileNo
    from ._traps import Abort, RaiseCancelT
"""

IMPORTS_WINDOWS = """\
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from typing_extensions import Buffer

    from .._file_io import _HasFileNo
    from ._unbounded_queue import UnboundedQueue
    from ._windows_cffi import Handle, CData
"""


if __name__ == "__main__":  # pragma: no cover
    main()

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\treebank.py ===
# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Michael Heilman <mheilman@cmu.edu> (re-port from http://www.cis.upenn.edu/~treebank/tokenizer.sed)
#         Tom Aarsen <> (modifications)
#
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

r"""

Penn Treebank Tokenizer

The Treebank tokenizer uses regular expressions to tokenize text as in Penn Treebank.
This implementation is a port of the tokenizer sed script written by Robert McIntyre
and available at http://www.cis.upenn.edu/~treebank/tokenizer.sed.
"""

import re
import warnings
from typing import Iterator, List, Tuple

from nltk.tokenize.api import TokenizerI
from nltk.tokenize.destructive import MacIntyreContractions
from nltk.tokenize.util import align_tokens


class TreebankWordTokenizer(TokenizerI):
    r"""
    The Treebank tokenizer uses regular expressions to tokenize text as in Penn Treebank.

    This tokenizer performs the following steps:

    - split standard contractions, e.g. ``don't`` -> ``do n't`` and ``they'll`` -> ``they 'll``
    - treat most punctuation characters as separate tokens
    - split off commas and single quotes, when followed by whitespace
    - separate periods that appear at the end of line

    >>> from nltk.tokenize import TreebankWordTokenizer
    >>> s = '''Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\nThanks.'''
    >>> TreebankWordTokenizer().tokenize(s)
    ['Good', 'muffins', 'cost', '$', '3.88', 'in', 'New', 'York.', 'Please', 'buy', 'me', 'two', 'of', 'them.', 'Thanks', '.']
    >>> s = "They'll save and invest more."
    >>> TreebankWordTokenizer().tokenize(s)
    ['They', "'ll", 'save', 'and', 'invest', 'more', '.']
    >>> s = "hi, my name can't hello,"
    >>> TreebankWordTokenizer().tokenize(s)
    ['hi', ',', 'my', 'name', 'ca', "n't", 'hello', ',']
    """

    # starting quotes
    STARTING_QUOTES = [
        (re.compile(r"^\""), r"``"),
        (re.compile(r"(``)"), r" \1 "),
        (re.compile(r"([ \(\[{<])(\"|\'{2})"), r"\1 `` "),
    ]

    # punctuation
    PUNCTUATION = [
        (re.compile(r"([:,])([^\d])"), r" \1 \2"),
        (re.compile(r"([:,])$"), r" \1 "),
        (re.compile(r"\.\.\."), r" ... "),
        (re.compile(r"[;@#$%&]"), r" \g<0> "),
        (
            re.compile(r'([^\.])(\.)([\]\)}>"\']*)\s*$'),
            r"\1 \2\3 ",
        ),  # Handles the final period.
        (re.compile(r"[?!]"), r" \g<0> "),
        (re.compile(r"([^'])' "), r"\1 ' "),
    ]

    # Pads parentheses
    PARENS_BRACKETS = (re.compile(r"[\]\[\(\)\{\}\<\>]"), r" \g<0> ")

    # Optionally: Convert parentheses, brackets and converts them to PTB symbols.
    CONVERT_PARENTHESES = [
        (re.compile(r"\("), "-LRB-"),
        (re.compile(r"\)"), "-RRB-"),
        (re.compile(r"\["), "-LSB-"),
        (re.compile(r"\]"), "-RSB-"),
        (re.compile(r"\{"), "-LCB-"),
        (re.compile(r"\}"), "-RCB-"),
    ]

    DOUBLE_DASHES = (re.compile(r"--"), r" -- ")

    # ending quotes
    ENDING_QUOTES = [
        (re.compile(r"''"), " '' "),
        (re.compile(r'"'), " '' "),
        (re.compile(r"([^' ])('[sS]|'[mM]|'[dD]|') "), r"\1 \2 "),
        (re.compile(r"([^' ])('ll|'LL|'re|'RE|'ve|'VE|n't|N'T) "), r"\1 \2 "),
    ]

    # List of contractions adapted from Robert MacIntyre's tokenizer.
    _contractions = MacIntyreContractions()
    CONTRACTIONS2 = list(map(re.compile, _contractions.CONTRACTIONS2))
    CONTRACTIONS3 = list(map(re.compile, _contractions.CONTRACTIONS3))

    def tokenize(
        self, text: str, convert_parentheses: bool = False, return_str: bool = False
    ) -> List[str]:
        r"""Return a tokenized copy of `text`.

        >>> from nltk.tokenize import TreebankWordTokenizer
        >>> s = '''Good muffins cost $3.88 (roughly 3,36 euros)\nin New York.  Please buy me\ntwo of them.\nThanks.'''
        >>> TreebankWordTokenizer().tokenize(s) # doctest: +NORMALIZE_WHITESPACE
        ['Good', 'muffins', 'cost', '$', '3.88', '(', 'roughly', '3,36',
        'euros', ')', 'in', 'New', 'York.', 'Please', 'buy', 'me', 'two',
        'of', 'them.', 'Thanks', '.']
        >>> TreebankWordTokenizer().tokenize(s, convert_parentheses=True) # doctest: +NORMALIZE_WHITESPACE
        ['Good', 'muffins', 'cost', '$', '3.88', '-LRB-', 'roughly', '3,36',
        'euros', '-RRB-', 'in', 'New', 'York.', 'Please', 'buy', 'me', 'two',
        'of', 'them.', 'Thanks', '.']

        :param text: A string with a sentence or sentences.
        :type text: str
        :param convert_parentheses: if True, replace parentheses to PTB symbols,
            e.g. `(` to `-LRB-`. Defaults to False.
        :type convert_parentheses: bool, optional
        :param return_str: If True, return tokens as space-separated string,
            defaults to False.
        :type return_str: bool, optional
        :return: List of tokens from `text`.
        :rtype: List[str]
        """
        if return_str is not False:
            warnings.warn(
                "Parameter 'return_str' has been deprecated and should no "
                "longer be used.",
                category=DeprecationWarning,
                stacklevel=2,
            )

        for regexp, substitution in self.STARTING_QUOTES:
            text = regexp.sub(substitution, text)

        for regexp, substitution in self.PUNCTUATION:
            text = regexp.sub(substitution, text)

        # Handles parentheses.
        regexp, substitution = self.PARENS_BRACKETS
        text = regexp.sub(substitution, text)
        # Optionally convert parentheses
        if convert_parentheses:
            for regexp, substitution in self.CONVERT_PARENTHESES:
                text = regexp.sub(substitution, text)

        # Handles double dash.
        regexp, substitution = self.DOUBLE_DASHES
        text = regexp.sub(substitution, text)

        # add extra space to make things easier
        text = " " + text + " "

        for regexp, substitution in self.ENDING_QUOTES:
            text = regexp.sub(substitution, text)

        for regexp in self.CONTRACTIONS2:
            text = regexp.sub(r" \1 \2 ", text)
        for regexp in self.CONTRACTIONS3:
            text = regexp.sub(r" \1 \2 ", text)

        # We are not using CONTRACTIONS4 since
        # they are also commented out in the SED scripts
        # for regexp in self._contractions.CONTRACTIONS4:
        #     text = regexp.sub(r' \1 \2 \3 ', text)

        return text.split()

    def span_tokenize(self, text: str) -> Iterator[Tuple[int, int]]:
        r"""
        Returns the spans of the tokens in ``text``.
        Uses the post-hoc nltk.tokens.align_tokens to return the offset spans.

            >>> from nltk.tokenize import TreebankWordTokenizer
            >>> s = '''Good muffins cost $3.88\nin New (York).  Please (buy) me\ntwo of them.\n(Thanks).'''
            >>> expected = [(0, 4), (5, 12), (13, 17), (18, 19), (19, 23),
            ... (24, 26), (27, 30), (31, 32), (32, 36), (36, 37), (37, 38),
            ... (40, 46), (47, 48), (48, 51), (51, 52), (53, 55), (56, 59),
            ... (60, 62), (63, 68), (69, 70), (70, 76), (76, 77), (77, 78)]
            >>> list(TreebankWordTokenizer().span_tokenize(s)) == expected
            True
            >>> expected = ['Good', 'muffins', 'cost', '$', '3.88', 'in',
            ... 'New', '(', 'York', ')', '.', 'Please', '(', 'buy', ')',
            ... 'me', 'two', 'of', 'them.', '(', 'Thanks', ')', '.']
            >>> [s[start:end] for start, end in TreebankWordTokenizer().span_tokenize(s)] == expected
            True

        :param text: A string with a sentence or sentences.
        :type text: str
        :yield: Tuple[int, int]
        """
        raw_tokens = self.tokenize(text)

        # Convert converted quotes back to original double quotes
        # Do this only if original text contains double quote(s) or double
        # single-quotes (because '' might be transformed to `` if it is
        # treated as starting quotes).
        if ('"' in text) or ("''" in text):
            # Find double quotes and converted quotes
            matched = [m.group() for m in re.finditer(r"``|'{2}|\"", text)]

            # Replace converted quotes back to double quotes
            tokens = [
                matched.pop(0) if tok in ['"', "``", "''"] else tok
                for tok in raw_tokens
            ]
        else:
            tokens = raw_tokens

        yield from align_tokens(tokens, text)


class TreebankWordDetokenizer(TokenizerI):
    r"""
    The Treebank detokenizer uses the reverse regex operations corresponding to
    the Treebank tokenizer's regexes.

    Note:

    - There're additional assumption mades when undoing the padding of ``[;@#$%&]``
      punctuation symbols that isn't presupposed in the TreebankTokenizer.
    - There're additional regexes added in reversing the parentheses tokenization,
       such as the ``r'([\]\)\}\>])\s([:;,.])'``, which removes the additional right
       padding added to the closing parentheses precedding ``[:;,.]``.
    - It's not possible to return the original whitespaces as they were because
      there wasn't explicit records of where `'\n'`, `'\t'` or `'\s'` were removed at
      the text.split() operation.

    >>> from nltk.tokenize.treebank import TreebankWordTokenizer, TreebankWordDetokenizer
    >>> s = '''Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\nThanks.'''
    >>> d = TreebankWordDetokenizer()
    >>> t = TreebankWordTokenizer()
    >>> toks = t.tokenize(s)
    >>> d.detokenize(toks)
    'Good muffins cost $3.88 in New York. Please buy me two of them. Thanks.'

    The MXPOST parentheses substitution can be undone using the ``convert_parentheses``
    parameter:

    >>> s = '''Good muffins cost $3.88\nin New (York).  Please (buy) me\ntwo of them.\n(Thanks).'''
    >>> expected_tokens = ['Good', 'muffins', 'cost', '$', '3.88', 'in',
    ... 'New', '-LRB-', 'York', '-RRB-', '.', 'Please', '-LRB-', 'buy',
    ... '-RRB-', 'me', 'two', 'of', 'them.', '-LRB-', 'Thanks', '-RRB-', '.']
    >>> expected_tokens == t.tokenize(s, convert_parentheses=True)
    True
    >>> expected_detoken = 'Good muffins cost $3.88 in New (York). Please (buy) me two of them. (Thanks).'
    >>> expected_detoken == d.detokenize(t.tokenize(s, convert_parentheses=True), convert_parentheses=True)
    True

    During tokenization it's safe to add more spaces but during detokenization,
    simply undoing the padding doesn't really help.

    - During tokenization, left and right pad is added to ``[!?]``, when
      detokenizing, only left shift the ``[!?]`` is needed.
      Thus ``(re.compile(r'\s([?!])'), r'\g<1>')``.

    - During tokenization ``[:,]`` are left and right padded but when detokenizing,
      only left shift is necessary and we keep right pad after comma/colon
      if the string after is a non-digit.
      Thus ``(re.compile(r'\s([:,])\s([^\d])'), r'\1 \2')``.

    >>> from nltk.tokenize.treebank import TreebankWordDetokenizer
    >>> toks = ['hello', ',', 'i', 'ca', "n't", 'feel', 'my', 'feet', '!', 'Help', '!', '!']
    >>> twd = TreebankWordDetokenizer()
    >>> twd.detokenize(toks)
    "hello, i can't feel my feet! Help!!"

    >>> toks = ['hello', ',', 'i', "can't", 'feel', ';', 'my', 'feet', '!',
    ... 'Help', '!', '!', 'He', 'said', ':', 'Help', ',', 'help', '?', '!']
    >>> twd.detokenize(toks)
    "hello, i can't feel; my feet! Help!! He said: Help, help?!"
    """

    _contractions = MacIntyreContractions()
    CONTRACTIONS2 = [
        re.compile(pattern.replace("(?#X)", r"\s"))
        for pattern in _contractions.CONTRACTIONS2
    ]
    CONTRACTIONS3 = [
        re.compile(pattern.replace("(?#X)", r"\s"))
        for pattern in _contractions.CONTRACTIONS3
    ]

    # ending quotes
    ENDING_QUOTES = [
        (re.compile(r"([^' ])\s('ll|'LL|'re|'RE|'ve|'VE|n't|N'T) "), r"\1\2 "),
        (re.compile(r"([^' ])\s('[sS]|'[mM]|'[dD]|') "), r"\1\2 "),
        (re.compile(r"(\S)\s(\'\')"), r"\1\2"),
        (
            re.compile(r"(\'\')\s([.,:)\]>};%])"),
            r"\1\2",
        ),  # Quotes followed by no-left-padded punctuations.
        (re.compile(r"''"), '"'),
    ]

    # Handles double dashes
    DOUBLE_DASHES = (re.compile(r" -- "), r"--")

    # Optionally: Convert parentheses, brackets and converts them from PTB symbols.
    CONVERT_PARENTHESES = [
        (re.compile("-LRB-"), "("),
        (re.compile("-RRB-"), ")"),
        (re.compile("-LSB-"), "["),
        (re.compile("-RSB-"), "]"),
        (re.compile("-LCB-"), "{"),
        (re.compile("-RCB-"), "}"),
    ]

    # Undo padding on parentheses.
    PARENS_BRACKETS = [
        (re.compile(r"([\[\(\{\<])\s"), r"\g<1>"),
        (re.compile(r"\s([\]\)\}\>])"), r"\g<1>"),
        (re.compile(r"([\]\)\}\>])\s([:;,.])"), r"\1\2"),
    ]

    # punctuation
    PUNCTUATION = [
        (re.compile(r"([^'])\s'\s"), r"\1' "),
        (re.compile(r"\s([?!])"), r"\g<1>"),  # Strip left pad for [?!]
        # (re.compile(r'\s([?!])\s'), r'\g<1>'),
        (re.compile(r'([^\.])\s(\.)([\]\)}>"\']*)\s*$'), r"\1\2\3"),
        # When tokenizing, [;@#$%&] are padded with whitespace regardless of
        # whether there are spaces before or after them.
        # But during detokenization, we need to distinguish between left/right
        # pad, so we split this up.
        (re.compile(r"([#$])\s"), r"\g<1>"),  # Left pad.
        (re.compile(r"\s([;%])"), r"\g<1>"),  # Right pad.
        # (re.compile(r"\s([&*])\s"), r" \g<1> "),  # Unknown pad.
        (re.compile(r"\s\.\.\.\s"), r"..."),
        # (re.compile(r"\s([:,])\s$"), r"\1"),  # .strip() takes care of it.
        (
            re.compile(r"\s([:,])"),
            r"\1",
        ),  # Just remove left padding. Punctuation in numbers won't be padded.
    ]

    # starting quotes
    STARTING_QUOTES = [
        (re.compile(r"([ (\[{<])\s``"), r"\1``"),
        (re.compile(r"(``)\s"), r"\1"),
        (re.compile(r"``"), r'"'),
    ]

    def tokenize(self, tokens: List[str], convert_parentheses: bool = False) -> str:
        """
        Treebank detokenizer, created by undoing the regexes from
        the TreebankWordTokenizer.tokenize.

        :param tokens: A list of strings, i.e. tokenized text.
        :type tokens: List[str]
        :param convert_parentheses: if True, replace PTB symbols with parentheses,
            e.g. `-LRB-` to `(`. Defaults to False.
        :type convert_parentheses: bool, optional
        :return: str
        """
        text = " ".join(tokens)

        # Add extra space to make things easier
        text = " " + text + " "

        # Reverse the contractions regexes.
        # Note: CONTRACTIONS4 are not used in tokenization.
        for regexp in self.CONTRACTIONS3:
            text = regexp.sub(r"\1\2", text)
        for regexp in self.CONTRACTIONS2:
            text = regexp.sub(r"\1\2", text)

        # Reverse the regexes applied for ending quotes.
        for regexp, substitution in self.ENDING_QUOTES:
            text = regexp.sub(substitution, text)

        # Undo the space padding.
        text = text.strip()

        # Reverse the padding on double dashes.
        regexp, substitution = self.DOUBLE_DASHES
        text = regexp.sub(substitution, text)

        if convert_parentheses:
            for regexp, substitution in self.CONVERT_PARENTHESES:
                text = regexp.sub(substitution, text)

        # Reverse the padding regexes applied for parenthesis/brackets.
        for regexp, substitution in self.PARENS_BRACKETS:
            text = regexp.sub(substitution, text)

        # Reverse the regexes applied for punctuations.
        for regexp, substitution in self.PUNCTUATION:
            text = regexp.sub(substitution, text)

        # Reverse the regexes applied for starting quotes.
        for regexp, substitution in self.STARTING_QUOTES:
            text = regexp.sub(substitution, text)

        return text.strip()

    def detokenize(self, tokens: List[str], convert_parentheses: bool = False) -> str:
        """Duck-typing the abstract *tokenize()*."""
        return self.tokenize(tokens, convert_parentheses)

# === NexusCore/openenv\Lib\site-packages\setuptools\config\_validate_pyproject\formats.py ===
"""
The functions in this module are used to validate schemas with the
`format JSON Schema keyword
<https://json-schema.org/understanding-json-schema/reference/string#format>`_.

The correspondence is given by replacing the ``_`` character in the name of the
function with a ``-`` to obtain the format name and vice versa.
"""

import builtins
import logging
import os
import re
import string
import typing
from itertools import chain as _chain

if typing.TYPE_CHECKING:
    from typing_extensions import Literal

_logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------------
# PEP 440

VERSION_PATTERN = r"""
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
"""

VERSION_REGEX = re.compile(r"^\s*" + VERSION_PATTERN + r"\s*$", re.X | re.I)


def pep440(version: str) -> bool:
    """See :ref:`PyPA's version specification <pypa:version-specifiers>`
    (initially introduced in :pep:`440`).
    """
    return VERSION_REGEX.match(version) is not None


# -------------------------------------------------------------------------------------
# PEP 508

PEP508_IDENTIFIER_PATTERN = r"([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])"
PEP508_IDENTIFIER_REGEX = re.compile(f"^{PEP508_IDENTIFIER_PATTERN}$", re.I)


def pep508_identifier(name: str) -> bool:
    """See :ref:`PyPA's name specification <pypa:name-format>`
    (initially introduced in :pep:`508#names`).
    """
    return PEP508_IDENTIFIER_REGEX.match(name) is not None


try:
    try:
        from packaging import requirements as _req
    except ImportError:  # pragma: no cover
        # let's try setuptools vendored version
        from setuptools._vendor.packaging import (  # type: ignore[no-redef]
            requirements as _req,
        )

    def pep508(value: str) -> bool:
        """See :ref:`PyPA's dependency specifiers <pypa:dependency-specifiers>`
        (initially introduced in :pep:`508`).
        """
        try:
            _req.Requirement(value)
            return True
        except _req.InvalidRequirement:
            return False

except ImportError:  # pragma: no cover
    _logger.warning(
        "Could not find an installation of `packaging`. Requirements, dependencies and "
        "versions might not be validated. "
        "To enforce validation, please install `packaging`."
    )

    def pep508(value: str) -> bool:
        return True


def pep508_versionspec(value: str) -> bool:
    """Expression that can be used to specify/lock versions (including ranges)
    See ``versionspec`` in :ref:`PyPA's dependency specifiers
    <pypa:dependency-specifiers>` (initially introduced in :pep:`508`).
    """
    if any(c in value for c in (";", "]", "@")):
        # In PEP 508:
        # conditional markers, extras and URL specs are not included in the
        # versionspec
        return False
    # Let's pretend we have a dependency called `requirement` with the given
    # version spec, then we can reuse the pep508 function for validation:
    return pep508(f"requirement{value}")


# -------------------------------------------------------------------------------------
# PEP 517


def pep517_backend_reference(value: str) -> bool:
    """See PyPA's specification for defining build-backend references
    introduced in :pep:`517#source-trees`.

    This is similar to an entry-point reference (e.g., ``package.module:object``).
    """
    module, _, obj = value.partition(":")
    identifiers = (i.strip() for i in _chain(module.split("."), obj.split(".")))
    return all(python_identifier(i) for i in identifiers if i)


# -------------------------------------------------------------------------------------
# Classifiers - PEP 301


def _download_classifiers() -> str:
    import ssl
    from email.message import Message
    from urllib.request import urlopen

    url = "https://pypi.org/pypi?:action=list_classifiers"
    context = ssl.create_default_context()
    with urlopen(url, context=context) as response:  # noqa: S310 (audit URLs)
        headers = Message()
        headers["content_type"] = response.getheader("content-type", "text/plain")
        return response.read().decode(headers.get_param("charset", "utf-8"))  # type: ignore[no-any-return]


class _TroveClassifier:
    """The ``trove_classifiers`` package is the official way of validating classifiers,
    however this package might not be always available.
    As a workaround we can still download a list from PyPI.
    We also don't want to be over strict about it, so simply skipping silently is an
    option (classifiers will be validated anyway during the upload to PyPI).
    """

    downloaded: typing.Union[None, "Literal[False]", typing.Set[str]]
    """
    None => not cached yet
    False => unavailable
    set => cached values
    """

    def __init__(self) -> None:
        self.downloaded = None
        self._skip_download = False
        self.__name__ = "trove_classifier"  # Emulate a public function

    def _disable_download(self) -> None:
        # This is a private API. Only setuptools has the consent of using it.
        self._skip_download = True

    def __call__(self, value: str) -> bool:
        if self.downloaded is False or self._skip_download is True:
            return True

        if os.getenv("NO_NETWORK") or os.getenv("VALIDATE_PYPROJECT_NO_NETWORK"):
            self.downloaded = False
            msg = (
                "Install ``trove-classifiers`` to ensure proper validation. "
                "Skipping download of classifiers list from PyPI (NO_NETWORK)."
            )
            _logger.debug(msg)
            return True

        if self.downloaded is None:
            msg = (
                "Install ``trove-classifiers`` to ensure proper validation. "
                "Meanwhile a list of classifiers will be downloaded from PyPI."
            )
            _logger.debug(msg)
            try:
                self.downloaded = set(_download_classifiers().splitlines())
            except Exception:
                self.downloaded = False
                _logger.debug("Problem with download, skipping validation")
                return True

        return value in self.downloaded or value.lower().startswith("private ::")


try:
    from trove_classifiers import classifiers as _trove_classifiers

    def trove_classifier(value: str) -> bool:
        """See https://pypi.org/classifiers/"""
        return value in _trove_classifiers or value.lower().startswith("private ::")

except ImportError:  # pragma: no cover
    trove_classifier = _TroveClassifier()


# -------------------------------------------------------------------------------------
# Stub packages - PEP 561


def pep561_stub_name(value: str) -> bool:
    """Name of a directory containing type stubs.
    It must follow the name scheme ``<package>-stubs`` as defined in
    :pep:`561#stub-only-packages`.
    """
    top, *children = value.split(".")
    if not top.endswith("-stubs"):
        return False
    return python_module_name(".".join([top[: -len("-stubs")], *children]))


# -------------------------------------------------------------------------------------
# Non-PEP related


def url(value: str) -> bool:
    """Valid URL (validation uses :obj:`urllib.parse`).
    For maximum compatibility please make sure to include a ``scheme`` prefix
    in your URL (e.g. ``http://``).
    """
    from urllib.parse import urlparse

    try:
        parts = urlparse(value)
        if not parts.scheme:
            _logger.warning(
                "For maximum compatibility please make sure to include a "
                "`scheme` prefix in your URL (e.g. 'http://'). "
                f"Given value: {value}"
            )
            if not (value.startswith("/") or value.startswith("\\") or "@" in value):
                parts = urlparse(f"http://{value}")

        return bool(parts.scheme and parts.netloc)
    except Exception:
        return False


# https://packaging.python.org/specifications/entry-points/
ENTRYPOINT_PATTERN = r"[^\[\s=]([^=]*[^\s=])?"
ENTRYPOINT_REGEX = re.compile(f"^{ENTRYPOINT_PATTERN}$", re.I)
RECOMMEDED_ENTRYPOINT_PATTERN = r"[\w.-]+"
RECOMMEDED_ENTRYPOINT_REGEX = re.compile(f"^{RECOMMEDED_ENTRYPOINT_PATTERN}$", re.I)
ENTRYPOINT_GROUP_PATTERN = r"\w+(\.\w+)*"
ENTRYPOINT_GROUP_REGEX = re.compile(f"^{ENTRYPOINT_GROUP_PATTERN}$", re.I)


def python_identifier(value: str) -> bool:
    """Can be used as identifier in Python.
    (Validation uses :obj:`str.isidentifier`).
    """
    return value.isidentifier()


def python_qualified_identifier(value: str) -> bool:
    """
    Python "dotted identifier", i.e. a sequence of :obj:`python_identifier`
    concatenated with ``"."`` (e.g.: ``package.module.submodule``).
    """
    if value.startswith(".") or value.endswith("."):
        return False
    return all(python_identifier(m) for m in value.split("."))


def python_module_name(value: str) -> bool:
    """Module name that can be used in an ``import``-statement in Python.
    See :obj:`python_qualified_identifier`.
    """
    return python_qualified_identifier(value)


def python_module_name_relaxed(value: str) -> bool:
    """Similar to :obj:`python_module_name`, but relaxed to also accept
    dash characters (``-``) and cover special cases like ``pip-run``.

    It is recommended, however, that beginners avoid dash characters,
    as they require advanced knowledge about Python internals.

    The following are disallowed:

    * names starting/ending in dashes,
    * names ending in ``-stubs`` (potentially collide with :obj:`pep561_stub_name`).
    """
    if value.startswith("-") or value.endswith("-"):
        return False
    if value.endswith("-stubs"):
        return False  # Avoid collision with PEP 561
    return python_module_name(value.replace("-", "_"))


def python_entrypoint_group(value: str) -> bool:
    """See ``Data model > group`` in the :ref:`PyPA's entry-points specification
    <pypa:entry-points>`.
    """
    return ENTRYPOINT_GROUP_REGEX.match(value) is not None


def python_entrypoint_name(value: str) -> bool:
    """See ``Data model > name`` in the :ref:`PyPA's entry-points specification
    <pypa:entry-points>`.
    """
    if not ENTRYPOINT_REGEX.match(value):
        return False
    if not RECOMMEDED_ENTRYPOINT_REGEX.match(value):
        msg = f"Entry point `{value}` does not follow recommended pattern: "
        msg += RECOMMEDED_ENTRYPOINT_PATTERN
        _logger.warning(msg)
    return True


def python_entrypoint_reference(value: str) -> bool:
    """Reference to a Python object using in the format::

        importable.module:object.attr

    See ``Data model >object reference`` in the :ref:`PyPA's entry-points specification
    <pypa:entry-points>`.
    """
    module, _, rest = value.partition(":")
    if "[" in rest:
        obj, _, extras_ = rest.partition("[")
        if extras_.strip()[-1] != "]":
            return False
        extras = (x.strip() for x in extras_.strip(string.whitespace + "[]").split(","))
        if not all(pep508_identifier(e) for e in extras):
            return False
        _logger.warning(f"`{value}` - using extras for entry points is not recommended")
    else:
        obj = rest

    module_parts = module.split(".")
    identifiers = _chain(module_parts, obj.split(".")) if rest else iter(module_parts)
    return all(python_identifier(i.strip()) for i in identifiers)


def uint8(value: builtins.int) -> bool:
    r"""Unsigned 8-bit integer (:math:`0 \leq x < 2^8`)"""
    return 0 <= value < 2**8


def uint16(value: builtins.int) -> bool:
    r"""Unsigned 16-bit integer (:math:`0 \leq x < 2^{16}`)"""
    return 0 <= value < 2**16


def uint(value: builtins.int) -> bool:
    r"""Unsigned 64-bit integer (:math:`0 \leq x < 2^{64}`)"""
    return 0 <= value < 2**64


def int(value: builtins.int) -> bool:
    r"""Signed 64-bit integer (:math:`-2^{63} \leq x < 2^{63}`)"""
    return -(2**63) <= value < 2**63


try:
    from packaging import licenses as _licenses

    def SPDX(value: str) -> bool:
        """See :ref:`PyPA's License-Expression specification
        <pypa:core-metadata-license-expression>` (added in :pep:`639`).
        """
        try:
            _licenses.canonicalize_license_expression(value)
            return True
        except _licenses.InvalidLicenseExpression:
            return False

except ImportError:  # pragma: no cover
    _logger.warning(
        "Could not find an up-to-date installation of `packaging`. "
        "License expressions might not be validated. "
        "To enforce validation, please install `packaging>=24.2`."
    )

    def SPDX(value: str) -> bool:
        return True

# === NexusCore/openenv\Lib\site-packages\win32comext\directsound\test\ds_test.py ===
import os
import struct
import sys
import unittest

import pythoncom
import pywintypes
import win32api
import win32com.directsound.directsound as ds
import win32event
from pywin32_testutil import TestSkipped, find_test_fixture

# next two lines are for for debugging:
# import win32com
# import directsound as ds

WAV_FORMAT_PCM = 1
WAV_HEADER_SIZE = struct.calcsize("<4sl4s4slhhllhh4sl")


def wav_header_unpack(data):
    (
        riff,
        riffsize,
        wave,
        fmt,
        fmtsize,
        format,
        nchannels,
        samplespersecond,
        datarate,
        blockalign,
        bitspersample,
        data,
        datalength,
    ) = struct.unpack("<4sl4s4slhhllhh4sl", data)

    assert riff == b"RIFF", "invalid wav header"

    # fmt chuck is not first chunk, directly followed by data chuck
    # It is nowhere required that they are, it is just very common
    assert (
        fmtsize == 16 and fmt == b"fmt " and data == b"data"
    ), "cannot understand wav header"

    wfx = pywintypes.WAVEFORMATEX()
    wfx.wFormatTag = format
    wfx.nChannels = nchannels
    wfx.nSamplesPerSec = samplespersecond
    wfx.nAvgBytesPerSec = datarate
    wfx.nBlockAlign = blockalign
    wfx.wBitsPerSample = bitspersample

    return wfx, datalength


def wav_header_pack(wfx, datasize):
    return struct.pack(
        "<4sl4s4slhhllhh4sl",
        b"RIFF",
        36 + datasize,
        b"WAVE",
        b"fmt ",
        16,
        wfx.wFormatTag,
        wfx.nChannels,
        wfx.nSamplesPerSec,
        wfx.nAvgBytesPerSec,
        wfx.nBlockAlign,
        wfx.wBitsPerSample,
        b"data",
        datasize,
    )


class WAVEFORMATTest(unittest.TestCase):
    def test_1_Type(self):
        "WAVEFORMATEX type"
        w = pywintypes.WAVEFORMATEX()
        self.assertTrue(isinstance(w, pywintypes.WAVEFORMATEXType))

    def test_2_Attr(self):
        "WAVEFORMATEX attribute access"
        # A wav header for a soundfile from a CD should look like this...
        w = pywintypes.WAVEFORMATEX()
        w.wFormatTag = pywintypes.WAVE_FORMAT_PCM
        w.nChannels = 2
        w.nSamplesPerSec = 44100
        w.nAvgBytesPerSec = 176400
        w.nBlockAlign = 4
        w.wBitsPerSample = 16

        self.assertTrue(w.wFormatTag == 1)
        self.assertTrue(w.nChannels == 2)
        self.assertTrue(w.nSamplesPerSec == 44100)
        self.assertTrue(w.nAvgBytesPerSec == 176400)
        self.assertTrue(w.nBlockAlign == 4)
        self.assertTrue(w.wBitsPerSample == 16)


class DSCAPSTest(unittest.TestCase):
    def test_1_Type(self):
        "DSCAPS type"
        c = ds.DSCAPS()
        self.assertTrue(isinstance(c, ds.DSCAPSType))

    def test_2_Attr(self):
        "DSCAPS attribute access"
        c = ds.DSCAPS()
        c.dwFlags = 1
        c.dwMinSecondarySampleRate = 2
        c.dwMaxSecondarySampleRate = 3
        c.dwPrimaryBuffers = 4
        c.dwMaxHwMixingAllBuffers = 5
        c.dwMaxHwMixingStaticBuffers = 6
        c.dwMaxHwMixingStreamingBuffers = 7
        c.dwFreeHwMixingAllBuffers = 8
        c.dwFreeHwMixingStaticBuffers = 9
        c.dwFreeHwMixingStreamingBuffers = 10
        c.dwMaxHw3DAllBuffers = 11
        c.dwMaxHw3DStaticBuffers = 12
        c.dwMaxHw3DStreamingBuffers = 13
        c.dwFreeHw3DAllBuffers = 14
        c.dwFreeHw3DStaticBuffers = 15
        c.dwFreeHw3DStreamingBuffers = 16
        c.dwTotalHwMemBytes = 17
        c.dwFreeHwMemBytes = 18
        c.dwMaxContigFreeHwMemBytes = 19
        c.dwUnlockTransferRateHwBuffers = 20
        c.dwPlayCpuOverheadSwBuffers = 21

        self.assertTrue(c.dwFlags == 1)
        self.assertTrue(c.dwMinSecondarySampleRate == 2)
        self.assertTrue(c.dwMaxSecondarySampleRate == 3)
        self.assertTrue(c.dwPrimaryBuffers == 4)
        self.assertTrue(c.dwMaxHwMixingAllBuffers == 5)
        self.assertTrue(c.dwMaxHwMixingStaticBuffers == 6)
        self.assertTrue(c.dwMaxHwMixingStreamingBuffers == 7)
        self.assertTrue(c.dwFreeHwMixingAllBuffers == 8)
        self.assertTrue(c.dwFreeHwMixingStaticBuffers == 9)
        self.assertTrue(c.dwFreeHwMixingStreamingBuffers == 10)
        self.assertTrue(c.dwMaxHw3DAllBuffers == 11)
        self.assertTrue(c.dwMaxHw3DStaticBuffers == 12)
        self.assertTrue(c.dwMaxHw3DStreamingBuffers == 13)
        self.assertTrue(c.dwFreeHw3DAllBuffers == 14)
        self.assertTrue(c.dwFreeHw3DStaticBuffers == 15)
        self.assertTrue(c.dwFreeHw3DStreamingBuffers == 16)
        self.assertTrue(c.dwTotalHwMemBytes == 17)
        self.assertTrue(c.dwFreeHwMemBytes == 18)
        self.assertTrue(c.dwMaxContigFreeHwMemBytes == 19)
        self.assertTrue(c.dwUnlockTransferRateHwBuffers == 20)
        self.assertTrue(c.dwPlayCpuOverheadSwBuffers == 21)


class DSBCAPSTest(unittest.TestCase):
    def test_1_Type(self):
        "DSBCAPS type"
        c = ds.DSBCAPS()
        self.assertTrue(isinstance(c, ds.DSBCAPSType))

    def test_2_Attr(self):
        "DSBCAPS attribute access"
        c = ds.DSBCAPS()
        c.dwFlags = 1
        c.dwBufferBytes = 2
        c.dwUnlockTransferRate = 3
        c.dwPlayCpuOverhead = 4

        self.assertTrue(c.dwFlags == 1)
        self.assertTrue(c.dwBufferBytes == 2)
        self.assertTrue(c.dwUnlockTransferRate == 3)
        self.assertTrue(c.dwPlayCpuOverhead == 4)


class DSCCAPSTest(unittest.TestCase):
    def test_1_Type(self):
        "DSCCAPS type"
        c = ds.DSCCAPS()
        self.assertTrue(isinstance(c, ds.DSCCAPSType))

    def test_2_Attr(self):
        "DSCCAPS attribute access"
        c = ds.DSCCAPS()
        c.dwFlags = 1
        c.dwFormats = 2
        c.dwChannels = 4

        self.assertTrue(c.dwFlags == 1)
        self.assertTrue(c.dwFormats == 2)
        self.assertTrue(c.dwChannels == 4)


class DSCBCAPSTest(unittest.TestCase):
    def test_1_Type(self):
        "DSCBCAPS type"
        c = ds.DSCBCAPS()
        self.assertTrue(isinstance(c, ds.DSCBCAPSType))

    def test_2_Attr(self):
        "DSCBCAPS attribute access"
        c = ds.DSCBCAPS()
        c.dwFlags = 1
        c.dwBufferBytes = 2

        self.assertTrue(c.dwFlags == 1)
        self.assertTrue(c.dwBufferBytes == 2)


class DSBUFFERDESCTest(unittest.TestCase):
    def test_1_Type(self):
        "DSBUFFERDESC type"
        c = ds.DSBUFFERDESC()
        self.assertTrue(isinstance(c, ds.DSBUFFERDESCType))

    def test_2_Attr(self):
        "DSBUFFERDESC attribute access"
        c = ds.DSBUFFERDESC()
        c.dwFlags = 1
        c.dwBufferBytes = 2
        c.lpwfxFormat = pywintypes.WAVEFORMATEX()
        c.lpwfxFormat.wFormatTag = pywintypes.WAVE_FORMAT_PCM
        c.lpwfxFormat.nChannels = 2
        c.lpwfxFormat.nSamplesPerSec = 44100
        c.lpwfxFormat.nAvgBytesPerSec = 176400
        c.lpwfxFormat.nBlockAlign = 4
        c.lpwfxFormat.wBitsPerSample = 16

        self.assertTrue(c.dwFlags == 1)
        self.assertTrue(c.dwBufferBytes == 2)
        self.assertTrue(c.lpwfxFormat.wFormatTag == 1)
        self.assertTrue(c.lpwfxFormat.nChannels == 2)
        self.assertTrue(c.lpwfxFormat.nSamplesPerSec == 44100)
        self.assertTrue(c.lpwfxFormat.nAvgBytesPerSec == 176400)
        self.assertTrue(c.lpwfxFormat.nBlockAlign == 4)
        self.assertTrue(c.lpwfxFormat.wBitsPerSample == 16)

    def invalid_format(self, c):
        c.lpwfxFormat = 17

    def test_3_invalid_format(self):
        "DSBUFFERDESC invalid lpwfxFormat assignment"
        c = ds.DSBUFFERDESC()
        self.assertRaises(ValueError, self.invalid_format, c)


class DSCBUFFERDESCTest(unittest.TestCase):
    def test_1_Type(self):
        "DSCBUFFERDESC type"
        c = ds.DSCBUFFERDESC()
        self.assertTrue(isinstance(c, ds.DSCBUFFERDESCType))

    def test_2_Attr(self):
        "DSCBUFFERDESC attribute access"
        c = ds.DSCBUFFERDESC()
        c.dwFlags = 1
        c.dwBufferBytes = 2
        c.lpwfxFormat = pywintypes.WAVEFORMATEX()
        c.lpwfxFormat.wFormatTag = pywintypes.WAVE_FORMAT_PCM
        c.lpwfxFormat.nChannels = 2
        c.lpwfxFormat.nSamplesPerSec = 44100
        c.lpwfxFormat.nAvgBytesPerSec = 176400
        c.lpwfxFormat.nBlockAlign = 4
        c.lpwfxFormat.wBitsPerSample = 16

        self.assertTrue(c.dwFlags == 1)
        self.assertTrue(c.dwBufferBytes == 2)
        self.assertTrue(c.lpwfxFormat.wFormatTag == 1)
        self.assertTrue(c.lpwfxFormat.nChannels == 2)
        self.assertTrue(c.lpwfxFormat.nSamplesPerSec == 44100)
        self.assertTrue(c.lpwfxFormat.nAvgBytesPerSec == 176400)
        self.assertTrue(c.lpwfxFormat.nBlockAlign == 4)
        self.assertTrue(c.lpwfxFormat.wBitsPerSample == 16)

    def invalid_format(self, c):
        c.lpwfxFormat = 17

    def test_3_invalid_format(self):
        "DSCBUFFERDESC invalid lpwfxFormat assignment"
        c = ds.DSCBUFFERDESC()
        self.assertRaises(ValueError, self.invalid_format, c)


class DirectSoundTest(unittest.TestCase):
    # basic tests - mostly just exercise the functions
    def testEnumerate(self):
        """DirectSoundEnumerate() sanity tests"""

        devices = ds.DirectSoundEnumerate()
        # this might fail on machines without a sound card
        self.assertTrue(len(devices))
        # if we have an entry, it must be a tuple of size 3
        self.assertTrue(len(devices[0]) == 3)

    def testCreate(self):
        """DirectSoundCreate()"""
        try:
            d = ds.DirectSoundCreate(None, None)
        except pythoncom.com_error as exc:
            if exc.hresult != ds.DSERR_NODRIVER:
                raise
            raise TestSkipped(exc)

    def testPlay(self):
        """Mesdames et Messieurs, la cour de Devin Dazzle"""
        # relative to 'testall.py' in the win32com test suite.
        extra = os.path.join(
            os.path.dirname(sys.argv[0]), "../../win32comext/directsound/test"
        )

        fname = find_test_fixture("01-Intro.wav", extra)

        with open(fname, "rb") as f:
            hdr = f.read(WAV_HEADER_SIZE)
            wfx, size = wav_header_unpack(hdr)

            try:
                d = ds.DirectSoundCreate(None, None)
            except pythoncom.com_error as exc:
                if exc.hresult != ds.DSERR_NODRIVER:
                    raise
                raise TestSkipped(exc)
            d.SetCooperativeLevel(None, ds.DSSCL_PRIORITY)

            sdesc = ds.DSBUFFERDESC()
            sdesc.dwFlags = ds.DSBCAPS_STICKYFOCUS | ds.DSBCAPS_CTRLPOSITIONNOTIFY
            sdesc.dwBufferBytes = size
            sdesc.lpwfxFormat = wfx

            buffer = d.CreateSoundBuffer(sdesc, None)

            event = win32event.CreateEvent(None, 0, 0, None)
            notify = buffer.QueryInterface(ds.IID_IDirectSoundNotify)

            notify.SetNotificationPositions((ds.DSBPN_OFFSETSTOP, event))

            buffer.Update(0, f.read(size))

            buffer.Play(0)

            win32event.WaitForSingleObject(event, -1)


class DirectSoundCaptureTest(unittest.TestCase):
    # basic tests - mostly just exercise the functions
    def testEnumerate(self):
        """DirectSoundCaptureEnumerate() sanity tests"""

        devices = ds.DirectSoundCaptureEnumerate()
        # this might fail on machines without a sound card
        self.assertTrue(len(devices))
        # if we have an entry, it must be a tuple of size 3
        self.assertTrue(len(devices[0]) == 3)

    def testCreate(self):
        """DirectSoundCreate()"""
        try:
            d = ds.DirectSoundCaptureCreate(None, None)
        except pythoncom.com_error as exc:
            if exc.hresult != ds.DSERR_NODRIVER:
                raise
            raise TestSkipped(exc)

    def testRecord(self):
        try:
            d = ds.DirectSoundCaptureCreate(None, None)
        except pythoncom.com_error as exc:
            if exc.hresult != ds.DSERR_NODRIVER:
                raise
            raise TestSkipped(exc)

        sdesc = ds.DSCBUFFERDESC()
        sdesc.dwBufferBytes = 352800  # 2 seconds
        sdesc.lpwfxFormat = pywintypes.WAVEFORMATEX()
        sdesc.lpwfxFormat.wFormatTag = pywintypes.WAVE_FORMAT_PCM
        sdesc.lpwfxFormat.nChannels = 2
        sdesc.lpwfxFormat.nSamplesPerSec = 44100
        sdesc.lpwfxFormat.nAvgBytesPerSec = 176400
        sdesc.lpwfxFormat.nBlockAlign = 4
        sdesc.lpwfxFormat.wBitsPerSample = 16

        buffer = d.CreateCaptureBuffer(sdesc)

        event = win32event.CreateEvent(None, 0, 0, None)
        notify = buffer.QueryInterface(ds.IID_IDirectSoundNotify)

        notify.SetNotificationPositions((ds.DSBPN_OFFSETSTOP, event))

        buffer.Start(0)

        win32event.WaitForSingleObject(event, -1)
        event.Close()

        data = buffer.Update(0, 352800)
        fname = os.path.join(win32api.GetTempPath(), "test_directsound_record.wav")
        f = open(fname, "wb")
        f.write(wav_header_pack(sdesc.lpwfxFormat, 352800))
        f.write(data)
        f.close()


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\tornado\escape.py ===
#
# Copyright 2009 Facebook
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

"""Escaping/unescaping methods for HTML, JSON, URLs, and others.

Also includes a few other miscellaneous string manipulation functions that
have crept in over time.

Many functions in this module have near-equivalents in the standard library
(the differences mainly relate to handling of bytes and unicode strings,
and were more relevant in Python 2). In new code, the standard library
functions are encouraged instead of this module where applicable. See the
docstrings on each function for details.
"""

import html
import json
import re
import urllib.parse

from tornado.util import unicode_type

import typing
from typing import Union, Any, Optional, Dict, List, Callable


def xhtml_escape(value: Union[str, bytes]) -> str:
    """Escapes a string so it is valid within HTML or XML.

    Escapes the characters ``<``, ``>``, ``"``, ``'``, and ``&``.
    When used in attribute values the escaped strings must be enclosed
    in quotes.

    Equivalent to `html.escape` except that this function always returns
    type `str` while `html.escape` returns `bytes` if its input is `bytes`.

    .. versionchanged:: 3.2

       Added the single quote to the list of escaped characters.

    .. versionchanged:: 6.4

       Now simply wraps `html.escape`. This is equivalent to the old behavior
       except that single quotes are now escaped as ``&#x27;`` instead of
       ``&#39;`` and performance may be different.
    """
    return html.escape(to_unicode(value))


def xhtml_unescape(value: Union[str, bytes]) -> str:
    """Un-escapes an XML-escaped string.

    Equivalent to `html.unescape` except that this function always returns
    type `str` while `html.unescape` returns `bytes` if its input is `bytes`.

    .. versionchanged:: 6.4

       Now simply wraps `html.unescape`. This changes behavior for some inputs
       as required by the HTML 5 specification
       https://html.spec.whatwg.org/multipage/parsing.html#numeric-character-reference-end-state

       Some invalid inputs such as surrogates now raise an error, and numeric
       references to certain ISO-8859-1 characters are now handled correctly.
    """
    return html.unescape(to_unicode(value))


# The fact that json_encode wraps json.dumps is an implementation detail.
# Please see https://github.com/tornadoweb/tornado/pull/706
# before sending a pull request that adds **kwargs to this function.
def json_encode(value: Any) -> str:
    """JSON-encodes the given Python object.

    Equivalent to `json.dumps` with the additional guarantee that the output
    will never contain the character sequence ``</`` which can be problematic
    when JSON is embedded in an HTML ``<script>`` tag.
    """
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the JavaScript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    return json.dumps(value).replace("</", "<\\/")


def json_decode(value: Union[str, bytes]) -> Any:
    """Returns Python objects for the given JSON string.

    Supports both `str` and `bytes` inputs. Equvalent to `json.loads`.
    """
    return json.loads(value)


def squeeze(value: str) -> str:
    """Replace all sequences of whitespace chars with a single space."""
    return re.sub(r"[\x00-\x20]+", " ", value).strip()


def url_escape(value: Union[str, bytes], plus: bool = True) -> str:
    """Returns a URL-encoded version of the given value.

    Equivalent to either `urllib.parse.quote_plus` or `urllib.parse.quote` depending on the ``plus``
    argument.

    If ``plus`` is true (the default), spaces will be represented as ``+`` and slashes will be
    represented as ``%2F``.  This is appropriate for query strings. If ``plus`` is false, spaces
    will be represented as ``%20`` and slashes are left as-is. This is appropriate for the path
    component of a URL. Note that the default of ``plus=True`` is effectively the
    reverse of Python's urllib module.

    .. versionadded:: 3.1
        The ``plus`` argument
    """
    quote = urllib.parse.quote_plus if plus else urllib.parse.quote
    return quote(value)


@typing.overload
def url_unescape(value: Union[str, bytes], encoding: None, plus: bool = True) -> bytes:
    pass


@typing.overload
def url_unescape(
    value: Union[str, bytes], encoding: str = "utf-8", plus: bool = True
) -> str:
    pass


def url_unescape(
    value: Union[str, bytes], encoding: Optional[str] = "utf-8", plus: bool = True
) -> Union[str, bytes]:
    """Decodes the given value from a URL.

    The argument may be either a byte or unicode string.

    If encoding is None, the result will be a byte string and this function is equivalent to
    `urllib.parse.unquote_to_bytes` if ``plus=False``.  Otherwise, the result is a unicode string in
    the specified encoding and this function is equivalent to either `urllib.parse.unquote_plus` or
    `urllib.parse.unquote` except that this function also accepts `bytes` as input.

    If ``plus`` is true (the default), plus signs will be interpreted as spaces (literal plus signs
    must be represented as "%2B").  This is appropriate for query strings and form-encoded values
    but not for the path component of a URL.  Note that this default is the reverse of Python's
    urllib module.

    .. versionadded:: 3.1
       The ``plus`` argument
    """
    if encoding is None:
        if plus:
            # unquote_to_bytes doesn't have a _plus variant
            value = to_basestring(value).replace("+", " ")
        return urllib.parse.unquote_to_bytes(value)
    else:
        unquote = urllib.parse.unquote_plus if plus else urllib.parse.unquote
        return unquote(to_basestring(value), encoding=encoding)


def parse_qs_bytes(
    qs: Union[str, bytes], keep_blank_values: bool = False, strict_parsing: bool = False
) -> Dict[str, List[bytes]]:
    """Parses a query string like urlparse.parse_qs,
    but takes bytes and returns the values as byte strings.

    Keys still become type str (interpreted as latin1 in python3!)
    because it's too painful to keep them as byte strings in
    python3 and in practice they're nearly always ascii anyway.
    """
    # This is gross, but python3 doesn't give us another way.
    # Latin1 is the universal donor of character encodings.
    if isinstance(qs, bytes):
        qs = qs.decode("latin1")
    result = urllib.parse.parse_qs(
        qs, keep_blank_values, strict_parsing, encoding="latin1", errors="strict"
    )
    encoded = {}
    for k, v in result.items():
        encoded[k] = [i.encode("latin1") for i in v]
    return encoded


_UTF8_TYPES = (bytes, type(None))


@typing.overload
def utf8(value: bytes) -> bytes:
    pass


@typing.overload
def utf8(value: str) -> bytes:
    pass


@typing.overload
def utf8(value: None) -> None:
    pass


def utf8(value: Union[None, str, bytes]) -> Optional[bytes]:
    """Converts a string argument to a byte string.

    If the argument is already a byte string or None, it is returned unchanged.
    Otherwise it must be a unicode string and is encoded as utf8.
    """
    if isinstance(value, _UTF8_TYPES):
        return value
    if not isinstance(value, unicode_type):
        raise TypeError("Expected bytes, unicode, or None; got %r" % type(value))
    return value.encode("utf-8")


_TO_UNICODE_TYPES = (unicode_type, type(None))


@typing.overload
def to_unicode(value: str) -> str:
    pass


@typing.overload
def to_unicode(value: bytes) -> str:
    pass


@typing.overload
def to_unicode(value: None) -> None:
    pass


def to_unicode(value: Union[None, str, bytes]) -> Optional[str]:
    """Converts a string argument to a unicode string.

    If the argument is already a unicode string or None, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    if isinstance(value, _TO_UNICODE_TYPES):
        return value
    if not isinstance(value, bytes):
        raise TypeError("Expected bytes, unicode, or None; got %r" % type(value))
    return value.decode("utf-8")


# to_unicode was previously named _unicode not because it was private,
# but to avoid conflicts with the built-in unicode() function/type
_unicode = to_unicode

# When dealing with the standard library across python 2 and 3 it is
# sometimes useful to have a direct conversion to the native string type
native_str = to_unicode
to_basestring = to_unicode


def recursive_unicode(obj: Any) -> Any:
    """Walks a simple data structure, converting byte strings to unicode.

    Supports lists, tuples, and dictionaries.
    """
    if isinstance(obj, dict):
        return {recursive_unicode(k): recursive_unicode(v) for (k, v) in obj.items()}
    elif isinstance(obj, list):
        return list(recursive_unicode(i) for i in obj)
    elif isinstance(obj, tuple):
        return tuple(recursive_unicode(i) for i in obj)
    elif isinstance(obj, bytes):
        return to_unicode(obj)
    else:
        return obj


# I originally used the regex from
# http://daringfireball.net/2010/07/improved_regex_for_matching_urls
# but it gets all exponential on certain patterns (such as too many trailing
# dots), causing the regex matcher to never return.
# This regex should avoid those problems.
# Use to_unicode instead of tornado.util.u - we don't want backslashes getting
# processed as escapes.
_URL_RE = re.compile(
    to_unicode(
        r"""\b((?:([\w-]+):(/{1,3})|www[.])(?:(?:(?:[^\s&()]|&amp;|&quot;)*(?:[^!"#$%&'()*+,.:;<=>?@\[\]^`{|}~\s]))|(?:\((?:[^\s&()]|&amp;|&quot;)*\)))+)"""  # noqa: E501
    )
)


def linkify(
    text: Union[str, bytes],
    shorten: bool = False,
    extra_params: Union[str, Callable[[str], str]] = "",
    require_protocol: bool = False,
    permitted_protocols: List[str] = ["http", "https"],
) -> str:
    """Converts plain text into HTML with links.

    For example: ``linkify("Hello http://tornadoweb.org!")`` would return
    ``Hello <a href="http://tornadoweb.org">http://tornadoweb.org</a>!``

    Parameters:

    * ``shorten``: Long urls will be shortened for display.

    * ``extra_params``: Extra text to include in the link tag, or a callable
      taking the link as an argument and returning the extra text
      e.g. ``linkify(text, extra_params='rel="nofollow" class="external"')``,
      or::

          def extra_params_cb(url):
              if url.startswith("http://example.com"):
                  return 'class="internal"'
              else:
                  return 'class="external" rel="nofollow"'
          linkify(text, extra_params=extra_params_cb)

    * ``require_protocol``: Only linkify urls which include a protocol. If
      this is False, urls such as www.facebook.com will also be linkified.

    * ``permitted_protocols``: List (or set) of protocols which should be
      linkified, e.g. ``linkify(text, permitted_protocols=["http", "ftp",
      "mailto"])``. It is very unsafe to include protocols such as
      ``javascript``.
    """
    if extra_params and not callable(extra_params):
        extra_params = " " + extra_params.strip()

    def make_link(m: typing.Match) -> str:
        url = m.group(1)
        proto = m.group(2)
        if require_protocol and not proto:
            return url  # not protocol, no linkify

        if proto and proto not in permitted_protocols:
            return url  # bad protocol, no linkify

        href = m.group(1)
        if not proto:
            href = "http://" + href  # no proto specified, use http

        if callable(extra_params):
            params = " " + extra_params(href).strip()
        else:
            params = extra_params

        # clip long urls. max_len is just an approximation
        max_len = 30
        if shorten and len(url) > max_len:
            before_clip = url
            if proto:
                proto_len = len(proto) + 1 + len(m.group(3) or "")  # +1 for :
            else:
                proto_len = 0

            parts = url[proto_len:].split("/")
            if len(parts) > 1:
                # Grab the whole host part plus the first bit of the path
                # The path is usually not that interesting once shortened
                # (no more slug, etc), so it really just provides a little
                # extra indication of shortening.
                url = (
                    url[:proto_len]
                    + parts[0]
                    + "/"
                    + parts[1][:8].split("?")[0].split(".")[0]
                )

            if len(url) > max_len * 1.5:  # still too long
                url = url[:max_len]

            if url != before_clip:
                amp = url.rfind("&")
                # avoid splitting html char entities
                if amp > max_len - 5:
                    url = url[:amp]
                url += "..."

                if len(url) >= len(before_clip):
                    url = before_clip
                else:
                    # full url is visible on mouse-over (for those who don't
                    # have a status bar, such as Safari by default)
                    params += ' title="%s"' % href

        return f'<a href="{href}"{params}>{url}</a>'

    # First HTML-escape so that our strings are all safe.
    # The regex is modified to avoid character entites other than &amp; so
    # that we won't pick up &quot;, etc.
    text = _unicode(xhtml_escape(text))
    return _URL_RE.sub(make_link, text)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\guardrails\guardrail_registry.py ===
# litellm/proxy/guardrails/guardrail_registry.py

import importlib
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, cast

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
from litellm.proxy.utils import PrismaClient
from litellm.secret_managers.main import get_secret
from litellm.types.guardrails import (
    Guardrail,
    GuardrailEventHooks,
    LakeraCategoryThresholds,
    LitellmParams,
    SupportedGuardrailIntegrations,
)

from .guardrail_initializers import (
    initialize_aim,
    initialize_aporia,
    initialize_bedrock,
    initialize_guardrails_ai,
    initialize_hide_secrets,
    initialize_lakera,
    initialize_lakera_v2,
    initialize_lasso,
    initialize_pangea,
    initialize_presidio,
)

guardrail_initializer_registry = {
    SupportedGuardrailIntegrations.APORIA.value: initialize_aporia,
    SupportedGuardrailIntegrations.BEDROCK.value: initialize_bedrock,
    SupportedGuardrailIntegrations.LAKERA.value: initialize_lakera,
    SupportedGuardrailIntegrations.LAKERA_V2.value: initialize_lakera_v2,
    SupportedGuardrailIntegrations.AIM.value: initialize_aim,
    SupportedGuardrailIntegrations.PRESIDIO.value: initialize_presidio,
    SupportedGuardrailIntegrations.HIDE_SECRETS.value: initialize_hide_secrets,
    SupportedGuardrailIntegrations.GURDRAILS_AI.value: initialize_guardrails_ai,
    SupportedGuardrailIntegrations.PANGEA.value: initialize_pangea,
    SupportedGuardrailIntegrations.LASSO.value: initialize_lasso,
}


class GuardrailRegistry:
    """
    Registry for guardrails

    Handles adding, removing, and getting guardrails in DB + in memory
    """

    def __init__(self):
        pass

    ###########################################################
    ########### In memory management helpers for guardrails ###########
    ############################################################
    def get_initialized_guardrail_callback(
        self, guardrail_name: str
    ) -> Optional[CustomGuardrail]:
        """
        Returns the initialized guardrail callback for a given guardrail name
        """
        active_guardrails = (
            litellm.logging_callback_manager.get_custom_loggers_for_type(
                callback_type=CustomGuardrail
            )
        )
        for active_guardrail in active_guardrails:
            if isinstance(active_guardrail, CustomGuardrail):
                if active_guardrail.guardrail_name == guardrail_name:
                    return active_guardrail
        return None

    ###########################################################
    ########### DB management helpers for guardrails ###########
    ############################################################
    async def add_guardrail_to_db(
        self, guardrail: Guardrail, prisma_client: PrismaClient
    ):
        """
        Add a guardrail to the database
        """
        try:
            guardrail_name = guardrail.get("guardrail_name")
            litellm_params: str = safe_dumps(dict(guardrail.get("litellm_params", {})))
            guardrail_info: str = safe_dumps(guardrail.get("guardrail_info", {}))

            # Create guardrail in DB
            created_guardrail = await prisma_client.db.litellm_guardrailstable.create(
                data={
                    "guardrail_name": guardrail_name,
                    "litellm_params": litellm_params,
                    "guardrail_info": guardrail_info,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            )

            # Add guardrail_id to the returned guardrail object
            guardrail_dict = dict(guardrail)
            guardrail_dict["guardrail_id"] = created_guardrail.guardrail_id

            return guardrail_dict
        except Exception as e:
            raise Exception(f"Error adding guardrail to DB: {str(e)}")

    async def delete_guardrail_from_db(
        self, guardrail_id: str, prisma_client: PrismaClient
    ):
        """
        Delete a guardrail from the database
        """
        try:
            # Delete from DB
            await prisma_client.db.litellm_guardrailstable.delete(
                where={"guardrail_id": guardrail_id}
            )

            return {"message": f"Guardrail {guardrail_id} deleted successfully"}
        except Exception as e:
            raise Exception(f"Error deleting guardrail from DB: {str(e)}")

    async def update_guardrail_in_db(
        self, guardrail_id: str, guardrail: Guardrail, prisma_client: PrismaClient
    ):
        """
        Update a guardrail in the database
        """
        try:
            guardrail_name = guardrail.get("guardrail_name")
            litellm_params: str = safe_dumps(dict(guardrail.get("litellm_params", {})))
            guardrail_info: str = safe_dumps(guardrail.get("guardrail_info", {}))

            # Update in DB
            updated_guardrail = await prisma_client.db.litellm_guardrailstable.update(
                where={"guardrail_id": guardrail_id},
                data={
                    "guardrail_name": guardrail_name,
                    "litellm_params": litellm_params,
                    "guardrail_info": guardrail_info,
                    "updated_at": datetime.now(timezone.utc),
                },
            )

            # Convert to dict and return
            return dict(updated_guardrail)
        except Exception as e:
            raise Exception(f"Error updating guardrail in DB: {str(e)}")

    @staticmethod
    async def get_all_guardrails_from_db(
        prisma_client: PrismaClient,
    ) -> List[Guardrail]:
        """
        Get all guardrails from the database
        """
        try:
            guardrails_from_db = (
                await prisma_client.db.litellm_guardrailstable.find_many(
                    order={"created_at": "desc"},
                )
            )

            guardrails: List[Guardrail] = []
            for guardrail in guardrails_from_db:
                guardrails.append(Guardrail(**(dict(guardrail))))

            return guardrails
        except Exception as e:
            raise Exception(f"Error getting guardrails from DB: {str(e)}")

    async def get_guardrail_by_id_from_db(
        self, guardrail_id: str, prisma_client: PrismaClient
    ) -> Optional[Guardrail]:
        """
        Get a guardrail by its ID from the database
        """
        try:
            guardrail = await prisma_client.db.litellm_guardrailstable.find_unique(
                where={"guardrail_id": guardrail_id}
            )

            if not guardrail:
                return None

            return Guardrail(**(dict(guardrail)))
        except Exception as e:
            raise Exception(f"Error getting guardrail from DB: {str(e)}")

    async def get_guardrail_by_name_from_db(
        self, guardrail_name: str, prisma_client: PrismaClient
    ) -> Optional[Guardrail]:
        """
        Get a guardrail by its name from the database
        """
        try:
            guardrail = await prisma_client.db.litellm_guardrailstable.find_unique(
                where={"guardrail_name": guardrail_name}
            )

            if not guardrail:
                return None

            return Guardrail(**(dict(guardrail)))
        except Exception as e:
            raise Exception(f"Error getting guardrail from DB: {str(e)}")


class InMemoryGuardrailHandler:
    """
    Class that handles initializing guardrails and adding them to the CallbackManager
    """

    def __init__(self):
        self.IN_MEMORY_GUARDRAILS: Dict[str, Guardrail] = {}
        """
        Guardrail id to Guardrail object mapping
        """

        self.guardrail_id_to_custom_guardrail: Dict[str, Optional[CustomGuardrail]] = {}
        """
        Guardrail id to CustomGuardrail object mapping
        """

    def initialize_guardrail(
        self,
        guardrail: Dict,
        config_file_path: Optional[str] = None,
    ) -> Optional[Guardrail]:
        """
        Initialize a guardrail from a dictionary and add it to the litellm callback manager

        Returns a Guardrail object if the guardrail is initialized successfully
        """
        guardrail_id = guardrail.get("guardrail_id") or str(uuid.uuid4())
        guardrail["guardrail_id"] = guardrail_id
        if guardrail_id in self.IN_MEMORY_GUARDRAILS:
            verbose_proxy_logger.debug(
                "guardrail_id already exists in IN_MEMORY_GUARDRAILS"
            )
            return self.IN_MEMORY_GUARDRAILS[guardrail_id]

        custom_guardrail_callback: Optional[CustomGuardrail] = None
        litellm_params_data = guardrail["litellm_params"]
        verbose_proxy_logger.debug("litellm_params= %s", litellm_params_data)

        litellm_params = LitellmParams(**litellm_params_data)

        if (
            "category_thresholds" in litellm_params_data
            and litellm_params_data["category_thresholds"]
        ):
            lakera_category_thresholds = LakeraCategoryThresholds(
                **litellm_params_data["category_thresholds"]
            )
            litellm_params.category_thresholds = lakera_category_thresholds

        if litellm_params.api_key and litellm_params.api_key.startswith("os.environ/"):
            litellm_params.api_key = str(get_secret(litellm_params.api_key))

        if litellm_params.api_base and litellm_params.api_base.startswith(
            "os.environ/"
        ):
            litellm_params.api_base = str(get_secret(litellm_params.api_base))

        guardrail_type = litellm_params.guardrail
        if guardrail_type is None:
            raise ValueError("guardrail_type is required")

        initializer = guardrail_initializer_registry.get(guardrail_type)

        if initializer:
            custom_guardrail_callback = initializer(litellm_params, guardrail)
        elif isinstance(guardrail_type, str) and "." in guardrail_type:
            custom_guardrail_callback = self.initialize_custom_guardrail(
                guardrail=guardrail,
                guardrail_type=guardrail_type,
                litellm_params=litellm_params,
                config_file_path=config_file_path,
            )
        else:
            raise ValueError(f"Unsupported guardrail: {guardrail_type}")

        parsed_guardrail = Guardrail(
            guardrail_id=guardrail.get("guardrail_id"),
            guardrail_name=guardrail["guardrail_name"],
            litellm_params=litellm_params,
        )

        # store references to the guardrail in memory
        self.IN_MEMORY_GUARDRAILS[guardrail_id] = parsed_guardrail
        self.guardrail_id_to_custom_guardrail[guardrail_id] = custom_guardrail_callback

        return parsed_guardrail

    def initialize_custom_guardrail(
        self,
        guardrail: Dict,
        guardrail_type: str,
        litellm_params: LitellmParams,
        config_file_path: Optional[str] = None,
    ) -> Optional[CustomGuardrail]:
        """
        Initialize a Custom Guardrail from a python file

        This initializes it by adding it to the litellm callback manager
        """
        if not config_file_path:
            raise Exception(
                "GuardrailsAIException - Please pass the config_file_path to initialize_guardrails_v2"
            )

        _file_name, _class_name = guardrail_type.split(".")
        verbose_proxy_logger.debug(
            "Initializing custom guardrail: %s, file_name: %s, class_name: %s",
            guardrail_type,
            _file_name,
            _class_name,
        )

        directory = os.path.dirname(config_file_path)
        module_file_path = os.path.join(directory, _file_name) + ".py"

        spec = importlib.util.spec_from_file_location(_class_name, module_file_path)  # type: ignore
        if not spec:
            raise ImportError(
                f"Could not find a module specification for {module_file_path}"
            )

        module = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(module)  # type: ignore
        _guardrail_class = getattr(module, _class_name)

        mode = litellm_params.mode
        if mode is None:
            raise ValueError(
                f"mode is required for guardrail {guardrail_type} please set mode to one of the following: {', '.join(GuardrailEventHooks)}"
            )

        default_on = litellm_params.default_on
        _guardrail_callback = _guardrail_class(
            guardrail_name=guardrail["guardrail_name"],
            event_hook=mode,
            default_on=default_on,
        )
        litellm.logging_callback_manager.add_litellm_callback(_guardrail_callback)  # type: ignore

        return _guardrail_callback

    def update_in_memory_guardrail(
        self, guardrail_id: str, guardrail: Guardrail
    ) -> None:
        """
        Update a guardrail in memory

        - updates the guardrail in memory
        - updates the guardrail params in litellm.callback_manager
        """
        self.IN_MEMORY_GUARDRAILS[guardrail_id] = guardrail

        custom_guardrail_callback = self.guardrail_id_to_custom_guardrail.get(
            guardrail_id
        )
        if custom_guardrail_callback:
            updated_litellm_params = cast(
                LitellmParams, guardrail.get("litellm_params", {})
            )
            custom_guardrail_callback.update_in_memory_litellm_params(
                litellm_params=updated_litellm_params
            )

    def delete_in_memory_guardrail(self, guardrail_id: str) -> None:
        """
        Delete a guardrail in memory
        """
        self.IN_MEMORY_GUARDRAILS.pop(guardrail_id, None)

    def list_in_memory_guardrails(self) -> List[Guardrail]:
        """
        List all guardrails in memory
        """
        return list(self.IN_MEMORY_GUARDRAILS.values())

    def get_guardrail_by_id(self, guardrail_id: str) -> Optional[Guardrail]:
        """
        Get a guardrail by its ID from memory
        """
        return self.IN_MEMORY_GUARDRAILS.get(guardrail_id)


########################################################
# In Memory Guardrail Handler for LiteLLM Proxy
########################################################
IN_MEMORY_GUARDRAIL_HANDLER = InMemoryGuardrailHandler()
########################################################

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\styles\style.py ===
"""
Tool for creating styles from a dictionary.
"""

from __future__ import annotations

import itertools
import re
from enum import Enum
from typing import Hashable, TypeVar

from prompt_toolkit.cache import SimpleCache

from .base import (
    ANSI_COLOR_NAMES,
    ANSI_COLOR_NAMES_ALIASES,
    DEFAULT_ATTRS,
    Attrs,
    BaseStyle,
)
from .named_colors import NAMED_COLORS

__all__ = [
    "Style",
    "parse_color",
    "Priority",
    "merge_styles",
]

_named_colors_lowercase = {k.lower(): v.lstrip("#") for k, v in NAMED_COLORS.items()}


def parse_color(text: str) -> str:
    """
    Parse/validate color format.

    Like in Pygments, but also support the ANSI color names.
    (These will map to the colors of the 16 color palette.)
    """
    # ANSI color names.
    if text in ANSI_COLOR_NAMES:
        return text
    if text in ANSI_COLOR_NAMES_ALIASES:
        return ANSI_COLOR_NAMES_ALIASES[text]

    # 140 named colors.
    try:
        # Replace by 'hex' value.
        return _named_colors_lowercase[text.lower()]
    except KeyError:
        pass

    # Hex codes.
    if text[0:1] == "#":
        col = text[1:]

        # Keep this for backwards-compatibility (Pygments does it).
        # I don't like the '#' prefix for named colors.
        if col in ANSI_COLOR_NAMES:
            return col
        elif col in ANSI_COLOR_NAMES_ALIASES:
            return ANSI_COLOR_NAMES_ALIASES[col]

        # 6 digit hex color.
        elif len(col) == 6:
            return col

        # 3 digit hex color.
        elif len(col) == 3:
            return col[0] * 2 + col[1] * 2 + col[2] * 2

    # Default.
    elif text in ("", "default"):
        return text

    raise ValueError(f"Wrong color format {text!r}")


# Attributes, when they are not filled in by a style. None means that we take
# the value from the parent.
_EMPTY_ATTRS = Attrs(
    color=None,
    bgcolor=None,
    bold=None,
    underline=None,
    strike=None,
    italic=None,
    blink=None,
    reverse=None,
    hidden=None,
)


def _expand_classname(classname: str) -> list[str]:
    """
    Split a single class name at the `.` operator, and build a list of classes.

    E.g. 'a.b.c' becomes ['a', 'a.b', 'a.b.c']
    """
    result = []
    parts = classname.split(".")

    for i in range(1, len(parts) + 1):
        result.append(".".join(parts[:i]).lower())

    return result


def _parse_style_str(style_str: str) -> Attrs:
    """
    Take a style string, e.g.  'bg:red #88ff00 class:title'
    and return a `Attrs` instance.
    """
    # Start from default Attrs.
    if "noinherit" in style_str:
        attrs = DEFAULT_ATTRS
    else:
        attrs = _EMPTY_ATTRS

    # Now update with the given attributes.
    for part in style_str.split():
        if part == "noinherit":
            pass
        elif part == "bold":
            attrs = attrs._replace(bold=True)
        elif part == "nobold":
            attrs = attrs._replace(bold=False)
        elif part == "italic":
            attrs = attrs._replace(italic=True)
        elif part == "noitalic":
            attrs = attrs._replace(italic=False)
        elif part == "underline":
            attrs = attrs._replace(underline=True)
        elif part == "nounderline":
            attrs = attrs._replace(underline=False)
        elif part == "strike":
            attrs = attrs._replace(strike=True)
        elif part == "nostrike":
            attrs = attrs._replace(strike=False)

        # prompt_toolkit extensions. Not in Pygments.
        elif part == "blink":
            attrs = attrs._replace(blink=True)
        elif part == "noblink":
            attrs = attrs._replace(blink=False)
        elif part == "reverse":
            attrs = attrs._replace(reverse=True)
        elif part == "noreverse":
            attrs = attrs._replace(reverse=False)
        elif part == "hidden":
            attrs = attrs._replace(hidden=True)
        elif part == "nohidden":
            attrs = attrs._replace(hidden=False)

        # Pygments properties that we ignore.
        elif part in ("roman", "sans", "mono"):
            pass
        elif part.startswith("border:"):
            pass

        # Ignore pieces in between square brackets. This is internal stuff.
        # Like '[transparent]' or '[set-cursor-position]'.
        elif part.startswith("[") and part.endswith("]"):
            pass

        # Colors.
        elif part.startswith("bg:"):
            attrs = attrs._replace(bgcolor=parse_color(part[3:]))
        elif part.startswith("fg:"):  # The 'fg:' prefix is optional.
            attrs = attrs._replace(color=parse_color(part[3:]))
        else:
            attrs = attrs._replace(color=parse_color(part))

    return attrs


CLASS_NAMES_RE = re.compile(r"^[a-z0-9.\s_-]*$")  # This one can't contain a comma!


class Priority(Enum):
    """
    The priority of the rules, when a style is created from a dictionary.

    In a `Style`, rules that are defined later will always override previous
    defined rules, however in a dictionary, the key order was arbitrary before
    Python 3.6. This means that the style could change at random between rules.

    We have two options:

    - `DICT_KEY_ORDER`: This means, iterate through the dictionary, and take
       the key/value pairs in order as they come. This is a good option if you
       have Python >3.6. Rules at the end will override rules at the beginning.
    - `MOST_PRECISE`: keys that are defined with most precision will get higher
      priority. (More precise means: more elements.)
    """

    DICT_KEY_ORDER = "KEY_ORDER"
    MOST_PRECISE = "MOST_PRECISE"


# We don't support Python versions older than 3.6 anymore, so we can always
# depend on dictionary ordering. This is the default.
default_priority = Priority.DICT_KEY_ORDER


class Style(BaseStyle):
    """
    Create a ``Style`` instance from a list of style rules.

    The `style_rules` is supposed to be a list of ('classnames', 'style') tuples.
    The classnames are a whitespace separated string of class names and the
    style string is just like a Pygments style definition, but with a few
    additions: it supports 'reverse' and 'blink'.

    Later rules always override previous rules.

    Usage::

        Style([
            ('title', '#ff0000 bold underline'),
            ('something-else', 'reverse'),
            ('class1 class2', 'reverse'),
        ])

    The ``from_dict`` classmethod is similar, but takes a dictionary as input.
    """

    def __init__(self, style_rules: list[tuple[str, str]]) -> None:
        class_names_and_attrs = []

        # Loop through the rules in the order they were defined.
        # Rules that are defined later get priority.
        for class_names, style_str in style_rules:
            assert CLASS_NAMES_RE.match(class_names), repr(class_names)

            # The order of the class names doesn't matter.
            # (But the order of rules does matter.)
            class_names_set = frozenset(class_names.lower().split())
            attrs = _parse_style_str(style_str)

            class_names_and_attrs.append((class_names_set, attrs))

        self._style_rules = style_rules
        self.class_names_and_attrs = class_names_and_attrs

    @property
    def style_rules(self) -> list[tuple[str, str]]:
        return self._style_rules

    @classmethod
    def from_dict(
        cls, style_dict: dict[str, str], priority: Priority = default_priority
    ) -> Style:
        """
        :param style_dict: Style dictionary.
        :param priority: `Priority` value.
        """
        if priority == Priority.MOST_PRECISE:

            def key(item: tuple[str, str]) -> int:
                # Split on '.' and whitespace. Count elements.
                return sum(len(i.split(".")) for i in item[0].split())

            return cls(sorted(style_dict.items(), key=key))
        else:
            return cls(list(style_dict.items()))

    def get_attrs_for_style_str(
        self, style_str: str, default: Attrs = DEFAULT_ATTRS
    ) -> Attrs:
        """
        Get `Attrs` for the given style string.
        """
        list_of_attrs = [default]
        class_names: set[str] = set()

        # Apply default styling.
        for names, attr in self.class_names_and_attrs:
            if not names:
                list_of_attrs.append(attr)

        # Go from left to right through the style string. Things on the right
        # take precedence.
        for part in style_str.split():
            # This part represents a class.
            # Do lookup of this class name in the style definition, as well
            # as all class combinations that we have so far.
            if part.startswith("class:"):
                # Expand all class names (comma separated list).
                new_class_names = []
                for p in part[6:].lower().split(","):
                    new_class_names.extend(_expand_classname(p))

                for new_name in new_class_names:
                    # Build a set of all possible class combinations to be applied.
                    combos = set()
                    combos.add(frozenset([new_name]))

                    for count in range(1, len(class_names) + 1):
                        for c2 in itertools.combinations(class_names, count):
                            combos.add(frozenset(c2 + (new_name,)))

                    # Apply the styles that match these class names.
                    for names, attr in self.class_names_and_attrs:
                        if names in combos:
                            list_of_attrs.append(attr)

                    class_names.add(new_name)

            # Process inline style.
            else:
                inline_attrs = _parse_style_str(part)
                list_of_attrs.append(inline_attrs)

        return _merge_attrs(list_of_attrs)

    def invalidation_hash(self) -> Hashable:
        return id(self.class_names_and_attrs)


_T = TypeVar("_T")


def _merge_attrs(list_of_attrs: list[Attrs]) -> Attrs:
    """
    Take a list of :class:`.Attrs` instances and merge them into one.
    Every `Attr` in the list can override the styling of the previous one. So,
    the last one has highest priority.
    """

    def _or(*values: _T) -> _T:
        "Take first not-None value, starting at the end."
        for v in values[::-1]:
            if v is not None:
                return v
        raise ValueError  # Should not happen, there's always one non-null value.

    return Attrs(
        color=_or("", *[a.color for a in list_of_attrs]),
        bgcolor=_or("", *[a.bgcolor for a in list_of_attrs]),
        bold=_or(False, *[a.bold for a in list_of_attrs]),
        underline=_or(False, *[a.underline for a in list_of_attrs]),
        strike=_or(False, *[a.strike for a in list_of_attrs]),
        italic=_or(False, *[a.italic for a in list_of_attrs]),
        blink=_or(False, *[a.blink for a in list_of_attrs]),
        reverse=_or(False, *[a.reverse for a in list_of_attrs]),
        hidden=_or(False, *[a.hidden for a in list_of_attrs]),
    )


def merge_styles(styles: list[BaseStyle]) -> _MergedStyle:
    """
    Merge multiple `Style` objects.
    """
    styles = [s for s in styles if s is not None]
    return _MergedStyle(styles)


class _MergedStyle(BaseStyle):
    """
    Merge multiple `Style` objects into one.
    This is supposed to ensure consistency: if any of the given styles changes,
    then this style will be updated.
    """

    # NOTE: previously, we used an algorithm where we did not generate the
    #       combined style. Instead this was a proxy that called one style
    #       after the other, passing the outcome of the previous style as the
    #       default for the next one. This did not work, because that way, the
    #       priorities like described in the `Style` class don't work.
    #       'class:aborted' was for instance never displayed in gray, because
    #       the next style specified a default color for any text. (The
    #       explicit styling of class:aborted should have taken priority,
    #       because it was more precise.)
    def __init__(self, styles: list[BaseStyle]) -> None:
        self.styles = styles
        self._style: SimpleCache[Hashable, Style] = SimpleCache(maxsize=1)

    @property
    def _merged_style(self) -> Style:
        "The `Style` object that has the other styles merged together."

        def get() -> Style:
            return Style(self.style_rules)

        return self._style.get(self.invalidation_hash(), get)

    @property
    def style_rules(self) -> list[tuple[str, str]]:
        style_rules = []
        for s in self.styles:
            style_rules.extend(s.style_rules)
        return style_rules

    def get_attrs_for_style_str(
        self, style_str: str, default: Attrs = DEFAULT_ATTRS
    ) -> Attrs:
        return self._merged_style.get_attrs_for_style_str(style_str, default)

    def invalidation_hash(self) -> Hashable:
        return tuple(s.invalidation_hash() for s in self.styles)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\prompt.py ===
from typing import Any, Generic, List, Optional, TextIO, TypeVar, Union, overload

from . import get_console
from .console import Console
from .text import Text, TextType

PromptType = TypeVar("PromptType")
DefaultType = TypeVar("DefaultType")


class PromptError(Exception):
    """Exception base class for prompt related errors."""


class InvalidResponse(PromptError):
    """Exception to indicate a response was invalid. Raise this within process_response() to indicate an error
    and provide an error message.

    Args:
        message (Union[str, Text]): Error message.
    """

    def __init__(self, message: TextType) -> None:
        self.message = message

    def __rich__(self) -> TextType:
        return self.message


class PromptBase(Generic[PromptType]):
    """Ask the user for input until a valid response is received. This is the base class, see one of
    the concrete classes for examples.

    Args:
        prompt (TextType, optional): Prompt text. Defaults to "".
        console (Console, optional): A Console instance or None to use global console. Defaults to None.
        password (bool, optional): Enable password input. Defaults to False.
        choices (List[str], optional): A list of valid choices. Defaults to None.
        case_sensitive (bool, optional): Matching of choices should be case-sensitive. Defaults to True.
        show_default (bool, optional): Show default in prompt. Defaults to True.
        show_choices (bool, optional): Show choices in prompt. Defaults to True.
    """

    response_type: type = str

    validate_error_message = "[prompt.invalid]Please enter a valid value"
    illegal_choice_message = (
        "[prompt.invalid.choice]Please select one of the available options"
    )
    prompt_suffix = ": "

    choices: Optional[List[str]] = None

    def __init__(
        self,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
    ) -> None:
        self.console = console or get_console()
        self.prompt = (
            Text.from_markup(prompt, style="prompt")
            if isinstance(prompt, str)
            else prompt
        )
        self.password = password
        if choices is not None:
            self.choices = choices
        self.case_sensitive = case_sensitive
        self.show_default = show_default
        self.show_choices = show_choices

    @classmethod
    @overload
    def ask(
        cls,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
        default: DefaultType,
        stream: Optional[TextIO] = None,
    ) -> Union[DefaultType, PromptType]:
        ...

    @classmethod
    @overload
    def ask(
        cls,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
        stream: Optional[TextIO] = None,
    ) -> PromptType:
        ...

    @classmethod
    def ask(
        cls,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
        default: Any = ...,
        stream: Optional[TextIO] = None,
    ) -> Any:
        """Shortcut to construct and run a prompt loop and return the result.

        Example:
            >>> filename = Prompt.ask("Enter a filename")

        Args:
            prompt (TextType, optional): Prompt text. Defaults to "".
            console (Console, optional): A Console instance or None to use global console. Defaults to None.
            password (bool, optional): Enable password input. Defaults to False.
            choices (List[str], optional): A list of valid choices. Defaults to None.
            case_sensitive (bool, optional): Matching of choices should be case-sensitive. Defaults to True.
            show_default (bool, optional): Show default in prompt. Defaults to True.
            show_choices (bool, optional): Show choices in prompt. Defaults to True.
            stream (TextIO, optional): Optional text file open for reading to get input. Defaults to None.
        """
        _prompt = cls(
            prompt,
            console=console,
            password=password,
            choices=choices,
            case_sensitive=case_sensitive,
            show_default=show_default,
            show_choices=show_choices,
        )
        return _prompt(default=default, stream=stream)

    def render_default(self, default: DefaultType) -> Text:
        """Turn the supplied default in to a Text instance.

        Args:
            default (DefaultType): Default value.

        Returns:
            Text: Text containing rendering of default value.
        """
        return Text(f"({default})", "prompt.default")

    def make_prompt(self, default: DefaultType) -> Text:
        """Make prompt text.

        Args:
            default (DefaultType): Default value.

        Returns:
            Text: Text to display in prompt.
        """
        prompt = self.prompt.copy()
        prompt.end = ""

        if self.show_choices and self.choices:
            _choices = "/".join(self.choices)
            choices = f"[{_choices}]"
            prompt.append(" ")
            prompt.append(choices, "prompt.choices")

        if (
            default != ...
            and self.show_default
            and isinstance(default, (str, self.response_type))
        ):
            prompt.append(" ")
            _default = self.render_default(default)
            prompt.append(_default)

        prompt.append(self.prompt_suffix)

        return prompt

    @classmethod
    def get_input(
        cls,
        console: Console,
        prompt: TextType,
        password: bool,
        stream: Optional[TextIO] = None,
    ) -> str:
        """Get input from user.

        Args:
            console (Console): Console instance.
            prompt (TextType): Prompt text.
            password (bool): Enable password entry.

        Returns:
            str: String from user.
        """
        return console.input(prompt, password=password, stream=stream)

    def check_choice(self, value: str) -> bool:
        """Check value is in the list of valid choices.

        Args:
            value (str): Value entered by user.

        Returns:
            bool: True if choice was valid, otherwise False.
        """
        assert self.choices is not None
        if self.case_sensitive:
            return value.strip() in self.choices
        return value.strip().lower() in [choice.lower() for choice in self.choices]

    def process_response(self, value: str) -> PromptType:
        """Process response from user, convert to prompt type.

        Args:
            value (str): String typed by user.

        Raises:
            InvalidResponse: If ``value`` is invalid.

        Returns:
            PromptType: The value to be returned from ask method.
        """
        value = value.strip()
        try:
            return_value: PromptType = self.response_type(value)
        except ValueError:
            raise InvalidResponse(self.validate_error_message)

        if self.choices is not None:
            if not self.check_choice(value):
                raise InvalidResponse(self.illegal_choice_message)

            if not self.case_sensitive:
                # return the original choice, not the lower case version
                return_value = self.response_type(
                    self.choices[
                        [choice.lower() for choice in self.choices].index(value.lower())
                    ]
                )
        return return_value

    def on_validate_error(self, value: str, error: InvalidResponse) -> None:
        """Called to handle validation error.

        Args:
            value (str): String entered by user.
            error (InvalidResponse): Exception instance the initiated the error.
        """
        self.console.print(error)

    def pre_prompt(self) -> None:
        """Hook to display something before the prompt."""

    @overload
    def __call__(self, *, stream: Optional[TextIO] = None) -> PromptType:
        ...

    @overload
    def __call__(
        self, *, default: DefaultType, stream: Optional[TextIO] = None
    ) -> Union[PromptType, DefaultType]:
        ...

    def __call__(self, *, default: Any = ..., stream: Optional[TextIO] = None) -> Any:
        """Run the prompt loop.

        Args:
            default (Any, optional): Optional default value.

        Returns:
            PromptType: Processed value.
        """
        while True:
            self.pre_prompt()
            prompt = self.make_prompt(default)
            value = self.get_input(self.console, prompt, self.password, stream=stream)
            if value == "" and default != ...:
                return default
            try:
                return_value = self.process_response(value)
            except InvalidResponse as error:
                self.on_validate_error(value, error)
                continue
            else:
                return return_value


class Prompt(PromptBase[str]):
    """A prompt that returns a str.

    Example:
        >>> name = Prompt.ask("Enter your name")


    """

    response_type = str


class IntPrompt(PromptBase[int]):
    """A prompt that returns an integer.

    Example:
        >>> burrito_count = IntPrompt.ask("How many burritos do you want to order")

    """

    response_type = int
    validate_error_message = "[prompt.invalid]Please enter a valid integer number"


class FloatPrompt(PromptBase[float]):
    """A prompt that returns a float.

    Example:
        >>> temperature = FloatPrompt.ask("Enter desired temperature")

    """

    response_type = float
    validate_error_message = "[prompt.invalid]Please enter a number"


class Confirm(PromptBase[bool]):
    """A yes / no confirmation prompt.

    Example:
        >>> if Confirm.ask("Continue"):
                run_job()

    """

    response_type = bool
    validate_error_message = "[prompt.invalid]Please enter Y or N"
    choices: List[str] = ["y", "n"]

    def render_default(self, default: DefaultType) -> Text:
        """Render the default as (y) or (n) rather than True/False."""
        yes, no = self.choices
        return Text(f"({yes})" if default else f"({no})", style="prompt.default")

    def process_response(self, value: str) -> bool:
        """Convert choices to a bool."""
        value = value.strip().lower()
        if value not in self.choices:
            raise InvalidResponse(self.validate_error_message)
        return value == self.choices[0]


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich import print

    if Confirm.ask("Run [i]prompt[/i] tests?", default=True):
        while True:
            result = IntPrompt.ask(
                ":rocket: Enter a number between [b]1[/b] and [b]10[/b]", default=5
            )
            if result >= 1 and result <= 10:
                break
            print(":pile_of_poo: [prompt.invalid]Number must be between 1 and 10")
        print(f"number={result}")

        while True:
            password = Prompt.ask(
                "Please enter a password [cyan](must be at least 5 characters)",
                password=True,
            )
            if len(password) >= 5:
                break
            print("[prompt.invalid]password too short")
        print(f"password={password!r}")

        fruit = Prompt.ask("Enter a fruit", choices=["apple", "orange", "pear"])
        print(f"fruit={fruit!r}")

        doggie = Prompt.ask(
            "What's the best Dog? (Case INSENSITIVE)",
            choices=["Border Terrier", "Collie", "Labradoodle"],
            case_sensitive=False,
        )
        print(f"doggie={doggie!r}")

    else:
        print("[b]OK :loudly_crying_face:")

# === NexusCore/openenv\Lib\site-packages\rich\prompt.py ===
from typing import Any, Generic, List, Optional, TextIO, TypeVar, Union, overload

from . import get_console
from .console import Console
from .text import Text, TextType

PromptType = TypeVar("PromptType")
DefaultType = TypeVar("DefaultType")


class PromptError(Exception):
    """Exception base class for prompt related errors."""


class InvalidResponse(PromptError):
    """Exception to indicate a response was invalid. Raise this within process_response() to indicate an error
    and provide an error message.

    Args:
        message (Union[str, Text]): Error message.
    """

    def __init__(self, message: TextType) -> None:
        self.message = message

    def __rich__(self) -> TextType:
        return self.message


class PromptBase(Generic[PromptType]):
    """Ask the user for input until a valid response is received. This is the base class, see one of
    the concrete classes for examples.

    Args:
        prompt (TextType, optional): Prompt text. Defaults to "".
        console (Console, optional): A Console instance or None to use global console. Defaults to None.
        password (bool, optional): Enable password input. Defaults to False.
        choices (List[str], optional): A list of valid choices. Defaults to None.
        case_sensitive (bool, optional): Matching of choices should be case-sensitive. Defaults to True.
        show_default (bool, optional): Show default in prompt. Defaults to True.
        show_choices (bool, optional): Show choices in prompt. Defaults to True.
    """

    response_type: type = str

    validate_error_message = "[prompt.invalid]Please enter a valid value"
    illegal_choice_message = (
        "[prompt.invalid.choice]Please select one of the available options"
    )
    prompt_suffix = ": "

    choices: Optional[List[str]] = None

    def __init__(
        self,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
    ) -> None:
        self.console = console or get_console()
        self.prompt = (
            Text.from_markup(prompt, style="prompt")
            if isinstance(prompt, str)
            else prompt
        )
        self.password = password
        if choices is not None:
            self.choices = choices
        self.case_sensitive = case_sensitive
        self.show_default = show_default
        self.show_choices = show_choices

    @classmethod
    @overload
    def ask(
        cls,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
        default: DefaultType,
        stream: Optional[TextIO] = None,
    ) -> Union[DefaultType, PromptType]:
        ...

    @classmethod
    @overload
    def ask(
        cls,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
        stream: Optional[TextIO] = None,
    ) -> PromptType:
        ...

    @classmethod
    def ask(
        cls,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
        default: Any = ...,
        stream: Optional[TextIO] = None,
    ) -> Any:
        """Shortcut to construct and run a prompt loop and return the result.

        Example:
            >>> filename = Prompt.ask("Enter a filename")

        Args:
            prompt (TextType, optional): Prompt text. Defaults to "".
            console (Console, optional): A Console instance or None to use global console. Defaults to None.
            password (bool, optional): Enable password input. Defaults to False.
            choices (List[str], optional): A list of valid choices. Defaults to None.
            case_sensitive (bool, optional): Matching of choices should be case-sensitive. Defaults to True.
            show_default (bool, optional): Show default in prompt. Defaults to True.
            show_choices (bool, optional): Show choices in prompt. Defaults to True.
            stream (TextIO, optional): Optional text file open for reading to get input. Defaults to None.
        """
        _prompt = cls(
            prompt,
            console=console,
            password=password,
            choices=choices,
            case_sensitive=case_sensitive,
            show_default=show_default,
            show_choices=show_choices,
        )
        return _prompt(default=default, stream=stream)

    def render_default(self, default: DefaultType) -> Text:
        """Turn the supplied default in to a Text instance.

        Args:
            default (DefaultType): Default value.

        Returns:
            Text: Text containing rendering of default value.
        """
        return Text(f"({default})", "prompt.default")

    def make_prompt(self, default: DefaultType) -> Text:
        """Make prompt text.

        Args:
            default (DefaultType): Default value.

        Returns:
            Text: Text to display in prompt.
        """
        prompt = self.prompt.copy()
        prompt.end = ""

        if self.show_choices and self.choices:
            _choices = "/".join(self.choices)
            choices = f"[{_choices}]"
            prompt.append(" ")
            prompt.append(choices, "prompt.choices")

        if (
            default != ...
            and self.show_default
            and isinstance(default, (str, self.response_type))
        ):
            prompt.append(" ")
            _default = self.render_default(default)
            prompt.append(_default)

        prompt.append(self.prompt_suffix)

        return prompt

    @classmethod
    def get_input(
        cls,
        console: Console,
        prompt: TextType,
        password: bool,
        stream: Optional[TextIO] = None,
    ) -> str:
        """Get input from user.

        Args:
            console (Console): Console instance.
            prompt (TextType): Prompt text.
            password (bool): Enable password entry.

        Returns:
            str: String from user.
        """
        return console.input(prompt, password=password, stream=stream)

    def check_choice(self, value: str) -> bool:
        """Check value is in the list of valid choices.

        Args:
            value (str): Value entered by user.

        Returns:
            bool: True if choice was valid, otherwise False.
        """
        assert self.choices is not None
        if self.case_sensitive:
            return value.strip() in self.choices
        return value.strip().lower() in [choice.lower() for choice in self.choices]

    def process_response(self, value: str) -> PromptType:
        """Process response from user, convert to prompt type.

        Args:
            value (str): String typed by user.

        Raises:
            InvalidResponse: If ``value`` is invalid.

        Returns:
            PromptType: The value to be returned from ask method.
        """
        value = value.strip()
        try:
            return_value: PromptType = self.response_type(value)
        except ValueError:
            raise InvalidResponse(self.validate_error_message)

        if self.choices is not None:
            if not self.check_choice(value):
                raise InvalidResponse(self.illegal_choice_message)

            if not self.case_sensitive:
                # return the original choice, not the lower case version
                return_value = self.response_type(
                    self.choices[
                        [choice.lower() for choice in self.choices].index(value.lower())
                    ]
                )
        return return_value

    def on_validate_error(self, value: str, error: InvalidResponse) -> None:
        """Called to handle validation error.

        Args:
            value (str): String entered by user.
            error (InvalidResponse): Exception instance the initiated the error.
        """
        self.console.print(error)

    def pre_prompt(self) -> None:
        """Hook to display something before the prompt."""

    @overload
    def __call__(self, *, stream: Optional[TextIO] = None) -> PromptType:
        ...

    @overload
    def __call__(
        self, *, default: DefaultType, stream: Optional[TextIO] = None
    ) -> Union[PromptType, DefaultType]:
        ...

    def __call__(self, *, default: Any = ..., stream: Optional[TextIO] = None) -> Any:
        """Run the prompt loop.

        Args:
            default (Any, optional): Optional default value.

        Returns:
            PromptType: Processed value.
        """
        while True:
            self.pre_prompt()
            prompt = self.make_prompt(default)
            value = self.get_input(self.console, prompt, self.password, stream=stream)
            if value == "" and default != ...:
                return default
            try:
                return_value = self.process_response(value)
            except InvalidResponse as error:
                self.on_validate_error(value, error)
                continue
            else:
                return return_value


class Prompt(PromptBase[str]):
    """A prompt that returns a str.

    Example:
        >>> name = Prompt.ask("Enter your name")


    """

    response_type = str


class IntPrompt(PromptBase[int]):
    """A prompt that returns an integer.

    Example:
        >>> burrito_count = IntPrompt.ask("How many burritos do you want to order")

    """

    response_type = int
    validate_error_message = "[prompt.invalid]Please enter a valid integer number"


class FloatPrompt(PromptBase[float]):
    """A prompt that returns a float.

    Example:
        >>> temperature = FloatPrompt.ask("Enter desired temperature")

    """

    response_type = float
    validate_error_message = "[prompt.invalid]Please enter a number"


class Confirm(PromptBase[bool]):
    """A yes / no confirmation prompt.

    Example:
        >>> if Confirm.ask("Continue"):
                run_job()

    """

    response_type = bool
    validate_error_message = "[prompt.invalid]Please enter Y or N"
    choices: List[str] = ["y", "n"]

    def render_default(self, default: DefaultType) -> Text:
        """Render the default as (y) or (n) rather than True/False."""
        yes, no = self.choices
        return Text(f"({yes})" if default else f"({no})", style="prompt.default")

    def process_response(self, value: str) -> bool:
        """Convert choices to a bool."""
        value = value.strip().lower()
        if value not in self.choices:
            raise InvalidResponse(self.validate_error_message)
        return value == self.choices[0]


if __name__ == "__main__":  # pragma: no cover
    from rich import print

    if Confirm.ask("Run [i]prompt[/i] tests?", default=True):
        while True:
            result = IntPrompt.ask(
                ":rocket: Enter a number between [b]1[/b] and [b]10[/b]", default=5
            )
            if result >= 1 and result <= 10:
                break
            print(":pile_of_poo: [prompt.invalid]Number must be between 1 and 10")
        print(f"number={result}")

        while True:
            password = Prompt.ask(
                "Please enter a password [cyan](must be at least 5 characters)",
                password=True,
            )
            if len(password) >= 5:
                break
            print("[prompt.invalid]password too short")
        print(f"password={password!r}")

        fruit = Prompt.ask("Enter a fruit", choices=["apple", "orange", "pear"])
        print(f"fruit={fruit!r}")

        doggie = Prompt.ask(
            "What's the best Dog? (Case INSENSITIVE)",
            choices=["Border Terrier", "Collie", "Labradoodle"],
            case_sensitive=False,
        )
        print(f"doggie={doggie!r}")

    else:
        print("[b]OK :loudly_crying_face:")

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\azure_storage\azure_storage.py ===
import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from litellm._logging import verbose_logger
from litellm.constants import _DEFAULT_TTL_FOR_HTTPX_CLIENTS, AZURE_STORAGE_MSFT_VERSION
from litellm.integrations.custom_batch_logger import CustomBatchLogger
from litellm.llms.azure.common_utils import get_azure_ad_token_from_entra_id
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.types.utils import StandardLoggingPayload


class AzureBlobStorageLogger(CustomBatchLogger):
    def __init__(
        self,
        **kwargs,
    ):
        try:
            verbose_logger.debug(
                "AzureBlobStorageLogger: in init azure blob storage logger"
            )

            # Env Variables used for Azure Storage Authentication
            self.tenant_id = os.getenv("AZURE_STORAGE_TENANT_ID")
            self.client_id = os.getenv("AZURE_STORAGE_CLIENT_ID")
            self.client_secret = os.getenv("AZURE_STORAGE_CLIENT_SECRET")
            self.azure_storage_account_key: Optional[str] = os.getenv(
                "AZURE_STORAGE_ACCOUNT_KEY"
            )

            # Required Env Variables for Azure Storage
            _azure_storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
            if not _azure_storage_account_name:
                raise ValueError(
                    "Missing required environment variable: AZURE_STORAGE_ACCOUNT_NAME"
                )
            self.azure_storage_account_name: str = _azure_storage_account_name
            _azure_storage_file_system = os.getenv("AZURE_STORAGE_FILE_SYSTEM")
            if not _azure_storage_file_system:
                raise ValueError(
                    "Missing required environment variable: AZURE_STORAGE_FILE_SYSTEM"
                )
            self.azure_storage_file_system: str = _azure_storage_file_system
            self._service_client = None
            # Time that the azure service client expires, in order to reset the connection pool and keep it fresh
            self._service_client_timeout: Optional[float] = None

            # Internal variables used for Token based authentication
            self.azure_auth_token: Optional[str] = (
                None  # the Azure AD token to use for Azure Storage API requests
            )
            self.token_expiry: Optional[datetime] = (
                None  # the expiry time of the currentAzure AD token
            )

            asyncio.create_task(self.periodic_flush())
            self.flush_lock = asyncio.Lock()
            self.log_queue: List[StandardLoggingPayload] = []
            super().__init__(**kwargs, flush_lock=self.flush_lock)
        except Exception as e:
            verbose_logger.exception(
                f"AzureBlobStorageLogger: Got exception on init AzureBlobStorageLogger client {str(e)}"
            )
            raise e

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """
        Async Log success events to Azure Blob Storage

        Raises:
            Raises a NON Blocking verbose_logger.exception if an error occurs
        """
        try:
            self._premium_user_check()
            verbose_logger.debug(
                "AzureBlobStorageLogger: Logging - Enters logging function for model %s",
                kwargs,
            )
            standard_logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object"
            )

            if standard_logging_payload is None:
                raise ValueError("standard_logging_payload is not set")

            self.log_queue.append(standard_logging_payload)

        except Exception as e:
            verbose_logger.exception(f"AzureBlobStorageLogger Layer Error - {str(e)}")
            pass

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        """
        Async Log failure events to Azure Blob Storage

        Raises:
            Raises a NON Blocking verbose_logger.exception if an error occurs
        """
        try:
            self._premium_user_check()
            verbose_logger.debug(
                "AzureBlobStorageLogger: Logging - Enters logging function for model %s",
                kwargs,
            )
            standard_logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object"
            )

            if standard_logging_payload is None:
                raise ValueError("standard_logging_payload is not set")

            self.log_queue.append(standard_logging_payload)
        except Exception as e:
            verbose_logger.exception(f"AzureBlobStorageLogger Layer Error - {str(e)}")
            pass

    async def async_send_batch(self):
        """
        Sends the in memory logs queue to Azure Blob Storage

        Raises:
            Raises a NON Blocking verbose_logger.exception if an error occurs
        """
        try:
            if not self.log_queue:
                verbose_logger.exception("Datadog: log_queue does not exist")
                return

            verbose_logger.debug(
                "AzureBlobStorageLogger - about to flush %s events",
                len(self.log_queue),
            )

            for payload in self.log_queue:
                await self.async_upload_payload_to_azure_blob_storage(payload=payload)

        except Exception as e:
            verbose_logger.exception(
                f"AzureBlobStorageLogger Error sending batch API - {str(e)}"
            )

    async def async_upload_payload_to_azure_blob_storage(
        self, payload: StandardLoggingPayload
    ):
        """
        Uploads the payload to Azure Blob Storage using a 3-step process:
        1. Create file resource
        2. Append data
        3. Flush the data
        """
        try:
            if self.azure_storage_account_key:
                await self.upload_to_azure_data_lake_with_azure_account_key(
                    payload=payload
                )
            else:
                # Get a valid token instead of always requesting a new one
                await self.set_valid_azure_ad_token()
                async_client = get_async_httpx_client(
                    llm_provider=httpxSpecialProvider.LoggingCallback
                )
                json_payload = (
                    json.dumps(payload) + "\n"
                )  # Add newline for each log entry
                payload_bytes = json_payload.encode("utf-8")
                filename = f"{payload.get('id') or str(uuid.uuid4())}.json"
                base_url = f"https://{self.azure_storage_account_name}.dfs.core.windows.net/{self.azure_storage_file_system}/{filename}"

                # Execute the 3-step upload process
                await self._create_file(async_client, base_url)
                await self._append_data(async_client, base_url, json_payload)
                await self._flush_data(async_client, base_url, len(payload_bytes))

                verbose_logger.debug(
                    f"Successfully uploaded log to Azure Blob Storage: {filename}"
                )

        except Exception as e:
            verbose_logger.exception(f"Error uploading to Azure Blob Storage: {str(e)}")
            raise e

    async def _create_file(self, client: AsyncHTTPHandler, base_url: str):
        """Helper method to create the file resource"""
        try:
            verbose_logger.debug(f"Creating file resource at: {base_url}")
            headers = {
                "x-ms-version": AZURE_STORAGE_MSFT_VERSION,
                "Content-Length": "0",
                "Authorization": f"Bearer {self.azure_auth_token}",
            }
            response = await client.put(f"{base_url}?resource=file", headers=headers)
            response.raise_for_status()
            verbose_logger.debug("Successfully created file resource")
        except Exception as e:
            verbose_logger.exception(f"Error creating file resource: {str(e)}")
            raise

    async def _append_data(
        self, client: AsyncHTTPHandler, base_url: str, json_payload: str
    ):
        """Helper method to append data to the file"""
        try:
            verbose_logger.debug(f"Appending data to file: {base_url}")
            headers = {
                "x-ms-version": AZURE_STORAGE_MSFT_VERSION,
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.azure_auth_token}",
            }
            response = await client.patch(
                f"{base_url}?action=append&position=0",
                headers=headers,
                data=json_payload,
            )
            response.raise_for_status()
            verbose_logger.debug("Successfully appended data")
        except Exception as e:
            verbose_logger.exception(f"Error appending data: {str(e)}")
            raise

    async def _flush_data(self, client: AsyncHTTPHandler, base_url: str, position: int):
        """Helper method to flush the data"""
        try:
            verbose_logger.debug(f"Flushing data at position {position}")
            headers = {
                "x-ms-version": AZURE_STORAGE_MSFT_VERSION,
                "Content-Length": "0",
                "Authorization": f"Bearer {self.azure_auth_token}",
            }
            response = await client.patch(
                f"{base_url}?action=flush&position={position}", headers=headers
            )
            response.raise_for_status()
            verbose_logger.debug("Successfully flushed data")
        except Exception as e:
            verbose_logger.exception(f"Error flushing data: {str(e)}")
            raise

    ####### Helper methods to managing Authentication to Azure Storage #######
    ##########################################################################

    async def set_valid_azure_ad_token(self):
        """
        Wrapper to set self.azure_auth_token to a valid Azure AD token, refreshing if necessary

        Refreshes the token when:
        - Token is expired
        - Token is not set
        """
        # Check if token needs refresh
        if self._azure_ad_token_is_expired() or self.azure_auth_token is None:
            verbose_logger.debug("Azure AD token needs refresh")
            self.azure_auth_token = self.get_azure_ad_token_from_azure_storage(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
            # Token typically expires in 1 hour
            self.token_expiry = datetime.now() + timedelta(hours=1)
            verbose_logger.debug(f"New token will expire at {self.token_expiry}")

    def get_azure_ad_token_from_azure_storage(
        self,
        tenant_id: Optional[str],
        client_id: Optional[str],
        client_secret: Optional[str],
    ) -> str:
        """
        Gets Azure AD token to use for Azure Storage API requests
        """
        verbose_logger.debug("Getting Azure AD Token from Azure Storage")
        verbose_logger.debug(
            "tenant_id %s, client_id %s, client_secret %s",
            tenant_id,
            client_id,
            client_secret,
        )
        if tenant_id is None:
            raise ValueError(
                "Missing required environment variable: AZURE_STORAGE_TENANT_ID"
            )
        if client_id is None:
            raise ValueError(
                "Missing required environment variable: AZURE_STORAGE_CLIENT_ID"
            )
        if client_secret is None:
            raise ValueError(
                "Missing required environment variable: AZURE_STORAGE_CLIENT_SECRET"
            )

        token_provider = get_azure_ad_token_from_entra_id(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            scope="https://storage.azure.com/.default",
        )
        token = token_provider()

        verbose_logger.debug("azure auth token %s", token)

        return token

    def _azure_ad_token_is_expired(self):
        """
        Returns True if Azure AD token is expired, False otherwise
        """
        if self.azure_auth_token and self.token_expiry:
            if datetime.now() + timedelta(minutes=5) >= self.token_expiry:
                verbose_logger.debug("Azure AD token is expired. Requesting new token")
                return True
        return False

    def _premium_user_check(self):
        """
        Checks if the user is a premium user, raises an error if not
        """
        from litellm.proxy.proxy_server import CommonProxyErrors, premium_user

        if premium_user is not True:
            raise ValueError(
                f"AzureBlobStorageLogger is only available for premium users. {CommonProxyErrors.not_premium_user}"
            )

    async def get_service_client(self):
        from azure.storage.filedatalake.aio import DataLakeServiceClient

        # expire old clients to recover from connection issues
        if (
            self._service_client_timeout
            and self._service_client
            and self._service_client_timeout > time.time()
        ):
            await self._service_client.close()
            self._service_client = None
        if not self._service_client:
            self._service_client = DataLakeServiceClient(
                account_url=f"https://{self.azure_storage_account_name}.dfs.core.windows.net",
                credential=self.azure_storage_account_key,
            )
            self._service_client_timeout = time.time() + _DEFAULT_TTL_FOR_HTTPX_CLIENTS
        return self._service_client

    async def upload_to_azure_data_lake_with_azure_account_key(
        self, payload: StandardLoggingPayload
    ):
        """
        Uploads the payload to Azure Data Lake using the Azure SDK

        This is used when Azure Storage Account Key is set - Azure Storage Account Key does not work directly with Azure Rest API
        """

        # Create an async service client

        service_client = await self.get_service_client()
        # Get file system client
        file_system_client = service_client.get_file_system_client(
            file_system=self.azure_storage_file_system
        )

        try:
            # Create directory with today's date
            from datetime import datetime

            today = datetime.now().strftime("%Y-%m-%d")
            directory_client = file_system_client.get_directory_client(today)

            # check if the directory exists
            if not await directory_client.exists():
                await directory_client.create_directory()
                verbose_logger.debug(f"Created directory: {today}")

            # Create a file client
            file_name = f"{payload.get('id') or str(uuid.uuid4())}.json"
            file_client = directory_client.get_file_client(file_name)

            # Create the file
            await file_client.create_file()

            # Content to append
            content = json.dumps(payload).encode("utf-8")

            # Append content to the file
            await file_client.append_data(data=content, offset=0, length=len(content))

            # Flush the content to finalize the file
            await file_client.flush_data(position=len(content), offset=0)

            verbose_logger.debug(
                f"Successfully uploaded and wrote to {today}/{file_name}"
            )

        except Exception as e:
            verbose_logger.exception(f"Error occurred: {str(e)}")

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\prompt.py ===
from typing import Any, Generic, List, Optional, TextIO, TypeVar, Union, overload

from . import get_console
from .console import Console
from .text import Text, TextType

PromptType = TypeVar("PromptType")
DefaultType = TypeVar("DefaultType")


class PromptError(Exception):
    """Exception base class for prompt related errors."""


class InvalidResponse(PromptError):
    """Exception to indicate a response was invalid. Raise this within process_response() to indicate an error
    and provide an error message.

    Args:
        message (Union[str, Text]): Error message.
    """

    def __init__(self, message: TextType) -> None:
        self.message = message

    def __rich__(self) -> TextType:
        return self.message


class PromptBase(Generic[PromptType]):
    """Ask the user for input until a valid response is received. This is the base class, see one of
    the concrete classes for examples.

    Args:
        prompt (TextType, optional): Prompt text. Defaults to "".
        console (Console, optional): A Console instance or None to use global console. Defaults to None.
        password (bool, optional): Enable password input. Defaults to False.
        choices (List[str], optional): A list of valid choices. Defaults to None.
        case_sensitive (bool, optional): Matching of choices should be case-sensitive. Defaults to True.
        show_default (bool, optional): Show default in prompt. Defaults to True.
        show_choices (bool, optional): Show choices in prompt. Defaults to True.
    """

    response_type: type = str

    validate_error_message = "[prompt.invalid]Please enter a valid value"
    illegal_choice_message = (
        "[prompt.invalid.choice]Please select one of the available options"
    )
    prompt_suffix = ": "

    choices: Optional[List[str]] = None

    def __init__(
        self,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
    ) -> None:
        self.console = console or get_console()
        self.prompt = (
            Text.from_markup(prompt, style="prompt")
            if isinstance(prompt, str)
            else prompt
        )
        self.password = password
        if choices is not None:
            self.choices = choices
        self.case_sensitive = case_sensitive
        self.show_default = show_default
        self.show_choices = show_choices

    @classmethod
    @overload
    def ask(
        cls,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
        default: DefaultType,
        stream: Optional[TextIO] = None,
    ) -> Union[DefaultType, PromptType]:
        ...

    @classmethod
    @overload
    def ask(
        cls,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
        stream: Optional[TextIO] = None,
    ) -> PromptType:
        ...

    @classmethod
    def ask(
        cls,
        prompt: TextType = "",
        *,
        console: Optional[Console] = None,
        password: bool = False,
        choices: Optional[List[str]] = None,
        case_sensitive: bool = True,
        show_default: bool = True,
        show_choices: bool = True,
        default: Any = ...,
        stream: Optional[TextIO] = None,
    ) -> Any:
        """Shortcut to construct and run a prompt loop and return the result.

        Example:
            >>> filename = Prompt.ask("Enter a filename")

        Args:
            prompt (TextType, optional): Prompt text. Defaults to "".
            console (Console, optional): A Console instance or None to use global console. Defaults to None.
            password (bool, optional): Enable password input. Defaults to False.
            choices (List[str], optional): A list of valid choices. Defaults to None.
            case_sensitive (bool, optional): Matching of choices should be case-sensitive. Defaults to True.
            show_default (bool, optional): Show default in prompt. Defaults to True.
            show_choices (bool, optional): Show choices in prompt. Defaults to True.
            stream (TextIO, optional): Optional text file open for reading to get input. Defaults to None.
        """
        _prompt = cls(
            prompt,
            console=console,
            password=password,
            choices=choices,
            case_sensitive=case_sensitive,
            show_default=show_default,
            show_choices=show_choices,
        )
        return _prompt(default=default, stream=stream)

    def render_default(self, default: DefaultType) -> Text:
        """Turn the supplied default in to a Text instance.

        Args:
            default (DefaultType): Default value.

        Returns:
            Text: Text containing rendering of default value.
        """
        return Text(f"({default})", "prompt.default")

    def make_prompt(self, default: DefaultType) -> Text:
        """Make prompt text.

        Args:
            default (DefaultType): Default value.

        Returns:
            Text: Text to display in prompt.
        """
        prompt = self.prompt.copy()
        prompt.end = ""

        if self.show_choices and self.choices:
            _choices = "/".join(self.choices)
            choices = f"[{_choices}]"
            prompt.append(" ")
            prompt.append(choices, "prompt.choices")

        if (
            default != ...
            and self.show_default
            and isinstance(default, (str, self.response_type))
        ):
            prompt.append(" ")
            _default = self.render_default(default)
            prompt.append(_default)

        prompt.append(self.prompt_suffix)

        return prompt

    @classmethod
    def get_input(
        cls,
        console: Console,
        prompt: TextType,
        password: bool,
        stream: Optional[TextIO] = None,
    ) -> str:
        """Get input from user.

        Args:
            console (Console): Console instance.
            prompt (TextType): Prompt text.
            password (bool): Enable password entry.

        Returns:
            str: String from user.
        """
        return console.input(prompt, password=password, stream=stream)

    def check_choice(self, value: str) -> bool:
        """Check value is in the list of valid choices.

        Args:
            value (str): Value entered by user.

        Returns:
            bool: True if choice was valid, otherwise False.
        """
        assert self.choices is not None
        if self.case_sensitive:
            return value.strip() in self.choices
        return value.strip().lower() in [choice.lower() for choice in self.choices]

    def process_response(self, value: str) -> PromptType:
        """Process response from user, convert to prompt type.

        Args:
            value (str): String typed by user.

        Raises:
            InvalidResponse: If ``value`` is invalid.

        Returns:
            PromptType: The value to be returned from ask method.
        """
        value = value.strip()
        try:
            return_value: PromptType = self.response_type(value)
        except ValueError:
            raise InvalidResponse(self.validate_error_message)

        if self.choices is not None:
            if not self.check_choice(value):
                raise InvalidResponse(self.illegal_choice_message)

            if not self.case_sensitive:
                # return the original choice, not the lower case version
                return_value = self.response_type(
                    self.choices[
                        [choice.lower() for choice in self.choices].index(value.lower())
                    ]
                )
        return return_value

    def on_validate_error(self, value: str, error: InvalidResponse) -> None:
        """Called to handle validation error.

        Args:
            value (str): String entered by user.
            error (InvalidResponse): Exception instance the initiated the error.
        """
        self.console.print(error)

    def pre_prompt(self) -> None:
        """Hook to display something before the prompt."""

    @overload
    def __call__(self, *, stream: Optional[TextIO] = None) -> PromptType:
        ...

    @overload
    def __call__(
        self, *, default: DefaultType, stream: Optional[TextIO] = None
    ) -> Union[PromptType, DefaultType]:
        ...

    def __call__(self, *, default: Any = ..., stream: Optional[TextIO] = None) -> Any:
        """Run the prompt loop.

        Args:
            default (Any, optional): Optional default value.

        Returns:
            PromptType: Processed value.
        """
        while True:
            self.pre_prompt()
            prompt = self.make_prompt(default)
            value = self.get_input(self.console, prompt, self.password, stream=stream)
            if value == "" and default != ...:
                return default
            try:
                return_value = self.process_response(value)
            except InvalidResponse as error:
                self.on_validate_error(value, error)
                continue
            else:
                return return_value


class Prompt(PromptBase[str]):
    """A prompt that returns a str.

    Example:
        >>> name = Prompt.ask("Enter your name")


    """

    response_type = str


class IntPrompt(PromptBase[int]):
    """A prompt that returns an integer.

    Example:
        >>> burrito_count = IntPrompt.ask("How many burritos do you want to order")

    """

    response_type = int
    validate_error_message = "[prompt.invalid]Please enter a valid integer number"


class FloatPrompt(PromptBase[float]):
    """A prompt that returns a float.

    Example:
        >>> temperature = FloatPrompt.ask("Enter desired temperature")

    """

    response_type = float
    validate_error_message = "[prompt.invalid]Please enter a number"


class Confirm(PromptBase[bool]):
    """A yes / no confirmation prompt.

    Example:
        >>> if Confirm.ask("Continue"):
                run_job()

    """

    response_type = bool
    validate_error_message = "[prompt.invalid]Please enter Y or N"
    choices: List[str] = ["y", "n"]

    def render_default(self, default: DefaultType) -> Text:
        """Render the default as (y) or (n) rather than True/False."""
        yes, no = self.choices
        return Text(f"({yes})" if default else f"({no})", style="prompt.default")

    def process_response(self, value: str) -> bool:
        """Convert choices to a bool."""
        value = value.strip().lower()
        if value not in self.choices:
            raise InvalidResponse(self.validate_error_message)
        return value == self.choices[0]


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich import print

    if Confirm.ask("Run [i]prompt[/i] tests?", default=True):
        while True:
            result = IntPrompt.ask(
                ":rocket: Enter a number between [b]1[/b] and [b]10[/b]", default=5
            )
            if result >= 1 and result <= 10:
                break
            print(":pile_of_poo: [prompt.invalid]Number must be between 1 and 10")
        print(f"number={result}")

        while True:
            password = Prompt.ask(
                "Please enter a password [cyan](must be at least 5 characters)",
                password=True,
            )
            if len(password) >= 5:
                break
            print("[prompt.invalid]password too short")
        print(f"password={password!r}")

        fruit = Prompt.ask("Enter a fruit", choices=["apple", "orange", "pear"])
        print(f"fruit={fruit!r}")

        doggie = Prompt.ask(
            "What's the best Dog? (Case INSENSITIVE)",
            choices=["Border Terrier", "Collie", "Labradoodle"],
            case_sensitive=False,
        )
        print(f"doggie={doggie!r}")

    else:
        print("[b]OK :loudly_crying_face:")

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\generics.py ===
import sys
import types
import typing
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    ForwardRef,
    Generic,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from weakref import WeakKeyDictionary, WeakValueDictionary

from typing_extensions import Annotated, Literal as ExtLiteral

from pydantic.v1.class_validators import gather_all_validators
from pydantic.v1.fields import DeferredType
from pydantic.v1.main import BaseModel, create_model
from pydantic.v1.types import JsonWrapper
from pydantic.v1.typing import display_as_type, get_all_type_hints, get_args, get_origin, typing_base
from pydantic.v1.utils import all_identical, lenient_issubclass

if sys.version_info >= (3, 10):
    from typing import _UnionGenericAlias
if sys.version_info >= (3, 8):
    from typing import Literal

GenericModelT = TypeVar('GenericModelT', bound='GenericModel')
TypeVarType = Any  # since mypy doesn't allow the use of TypeVar as a type

CacheKey = Tuple[Type[Any], Any, Tuple[Any, ...]]
Parametrization = Mapping[TypeVarType, Type[Any]]

# weak dictionaries allow the dynamically created parametrized versions of generic models to get collected
# once they are no longer referenced by the caller.
if sys.version_info >= (3, 9):  # Typing for weak dictionaries available at 3.9
    GenericTypesCache = WeakValueDictionary[CacheKey, Type[BaseModel]]
    AssignedParameters = WeakKeyDictionary[Type[BaseModel], Parametrization]
else:
    GenericTypesCache = WeakValueDictionary
    AssignedParameters = WeakKeyDictionary

# _generic_types_cache is a Mapping from __class_getitem__ arguments to the parametrized version of generic models.
# This ensures multiple calls of e.g. A[B] return always the same class.
_generic_types_cache = GenericTypesCache()

# _assigned_parameters is a Mapping from parametrized version of generic models to assigned types of parametrizations
# as captured during construction of the class (not instances).
# E.g., for generic model `Model[A, B]`, when parametrized model `Model[int, str]` is created,
# `Model[int, str]`: {A: int, B: str}` will be stored in `_assigned_parameters`.
# (This information is only otherwise available after creation from the class name string).
_assigned_parameters = AssignedParameters()


class GenericModel(BaseModel):
    __slots__ = ()
    __concrete__: ClassVar[bool] = False

    if TYPE_CHECKING:
        # Putting this in a TYPE_CHECKING block allows us to replace `if Generic not in cls.__bases__` with
        # `not hasattr(cls, "__parameters__")`. This means we don't need to force non-concrete subclasses of
        # `GenericModel` to also inherit from `Generic`, which would require changes to the use of `create_model` below.
        __parameters__: ClassVar[Tuple[TypeVarType, ...]]

    # Setting the return type as Type[Any] instead of Type[BaseModel] prevents PyCharm warnings
    def __class_getitem__(cls: Type[GenericModelT], params: Union[Type[Any], Tuple[Type[Any], ...]]) -> Type[Any]:
        """Instantiates a new class from a generic class `cls` and type variables `params`.

        :param params: Tuple of types the class . Given a generic class
            `Model` with 2 type variables and a concrete model `Model[str, int]`,
            the value `(str, int)` would be passed to `params`.
        :return: New model class inheriting from `cls` with instantiated
            types described by `params`. If no parameters are given, `cls` is
            returned as is.

        """

        def _cache_key(_params: Any) -> CacheKey:
            args = get_args(_params)
            # python returns a list for Callables, which is not hashable
            if len(args) == 2 and isinstance(args[0], list):
                args = (tuple(args[0]), args[1])
            return cls, _params, args

        cached = _generic_types_cache.get(_cache_key(params))
        if cached is not None:
            return cached
        if cls.__concrete__ and Generic not in cls.__bases__:
            raise TypeError('Cannot parameterize a concrete instantiation of a generic model')
        if not isinstance(params, tuple):
            params = (params,)
        if cls is GenericModel and any(isinstance(param, TypeVar) for param in params):
            raise TypeError('Type parameters should be placed on typing.Generic, not GenericModel')
        if not hasattr(cls, '__parameters__'):
            raise TypeError(f'Type {cls.__name__} must inherit from typing.Generic before being parameterized')

        check_parameters_count(cls, params)
        # Build map from generic typevars to passed params
        typevars_map: Dict[TypeVarType, Type[Any]] = dict(zip(cls.__parameters__, params))
        if all_identical(typevars_map.keys(), typevars_map.values()) and typevars_map:
            return cls  # if arguments are equal to parameters it's the same object

        # Create new model with original model as parent inserting fields with DeferredType.
        model_name = cls.__concrete_name__(params)
        validators = gather_all_validators(cls)

        type_hints = get_all_type_hints(cls).items()
        instance_type_hints = {k: v for k, v in type_hints if get_origin(v) is not ClassVar}

        fields = {k: (DeferredType(), cls.__fields__[k].field_info) for k in instance_type_hints if k in cls.__fields__}

        model_module, called_globally = get_caller_frame_info()
        created_model = cast(
            Type[GenericModel],  # casting ensures mypy is aware of the __concrete__ and __parameters__ attributes
            create_model(
                model_name,
                __module__=model_module or cls.__module__,
                __base__=(cls,) + tuple(cls.__parameterized_bases__(typevars_map)),
                __config__=None,
                __validators__=validators,
                __cls_kwargs__=None,
                **fields,
            ),
        )

        _assigned_parameters[created_model] = typevars_map

        if called_globally:  # create global reference and therefore allow pickling
            object_by_reference = None
            reference_name = model_name
            reference_module_globals = sys.modules[created_model.__module__].__dict__
            while object_by_reference is not created_model:
                object_by_reference = reference_module_globals.setdefault(reference_name, created_model)
                reference_name += '_'

        created_model.Config = cls.Config

        # Find any typevars that are still present in the model.
        # If none are left, the model is fully "concrete", otherwise the new
        # class is a generic class as well taking the found typevars as
        # parameters.
        new_params = tuple(
            {param: None for param in iter_contained_typevars(typevars_map.values())}
        )  # use dict as ordered set
        created_model.__concrete__ = not new_params
        if new_params:
            created_model.__parameters__ = new_params

        # Save created model in cache so we don't end up creating duplicate
        # models that should be identical.
        _generic_types_cache[_cache_key(params)] = created_model
        if len(params) == 1:
            _generic_types_cache[_cache_key(params[0])] = created_model

        # Recursively walk class type hints and replace generic typevars
        # with concrete types that were passed.
        _prepare_model_fields(created_model, fields, instance_type_hints, typevars_map)

        return created_model

    @classmethod
    def __concrete_name__(cls: Type[Any], params: Tuple[Type[Any], ...]) -> str:
        """Compute class name for child classes.

        :param params: Tuple of types the class . Given a generic class
            `Model` with 2 type variables and a concrete model `Model[str, int]`,
            the value `(str, int)` would be passed to `params`.
        :return: String representing a the new class where `params` are
            passed to `cls` as type variables.

        This method can be overridden to achieve a custom naming scheme for GenericModels.
        """
        param_names = [display_as_type(param) for param in params]
        params_component = ', '.join(param_names)
        return f'{cls.__name__}[{params_component}]'

    @classmethod
    def __parameterized_bases__(cls, typevars_map: Parametrization) -> Iterator[Type[Any]]:
        """
        Returns unbound bases of cls parameterised to given type variables

        :param typevars_map: Dictionary of type applications for binding subclasses.
            Given a generic class `Model` with 2 type variables [S, T]
            and a concrete model `Model[str, int]`,
            the value `{S: str, T: int}` would be passed to `typevars_map`.
        :return: an iterator of generic sub classes, parameterised by `typevars_map`
            and other assigned parameters of `cls`

        e.g.:
        ```
        class A(GenericModel, Generic[T]):
            ...

        class B(A[V], Generic[V]):
            ...

        assert A[int] in B.__parameterized_bases__({V: int})
        ```
        """

        def build_base_model(
            base_model: Type[GenericModel], mapped_types: Parametrization
        ) -> Iterator[Type[GenericModel]]:
            base_parameters = tuple(mapped_types[param] for param in base_model.__parameters__)
            parameterized_base = base_model.__class_getitem__(base_parameters)
            if parameterized_base is base_model or parameterized_base is cls:
                # Avoid duplication in MRO
                return
            yield parameterized_base

        for base_model in cls.__bases__:
            if not issubclass(base_model, GenericModel):
                # not a class that can be meaningfully parameterized
                continue
            elif not getattr(base_model, '__parameters__', None):
                # base_model is "GenericModel"  (and has no __parameters__)
                # or
                # base_model is already concrete, and will be included transitively via cls.
                continue
            elif cls in _assigned_parameters:
                if base_model in _assigned_parameters:
                    # cls is partially parameterised but not from base_model
                    # e.g. cls = B[S], base_model = A[S]
                    # B[S][int] should subclass A[int],  (and will be transitively via B[int])
                    # but it's not viable to consistently subclass types with arbitrary construction
                    # So don't attempt to include A[S][int]
                    continue
                else:  # base_model not in _assigned_parameters:
                    # cls is partially parameterized, base_model is original generic
                    # e.g.  cls = B[str, T], base_model = B[S, T]
                    # Need to determine the mapping for the base_model parameters
                    mapped_types: Parametrization = {
                        key: typevars_map.get(value, value) for key, value in _assigned_parameters[cls].items()
                    }
                    yield from build_base_model(base_model, mapped_types)
            else:
                # cls is base generic, so base_class has a distinct base
                # can construct the Parameterised base model using typevars_map directly
                yield from build_base_model(base_model, typevars_map)


def replace_types(type_: Any, type_map: Mapping[Any, Any]) -> Any:
    """Return type with all occurrences of `type_map` keys recursively replaced with their values.

    :param type_: Any type, class or generic alias
    :param type_map: Mapping from `TypeVar` instance to concrete types.
    :return: New type representing the basic structure of `type_` with all
        `typevar_map` keys recursively replaced.

    >>> replace_types(Tuple[str, Union[List[str], float]], {str: int})
    Tuple[int, Union[List[int], float]]

    """
    if not type_map:
        return type_

    type_args = get_args(type_)
    origin_type = get_origin(type_)

    if origin_type is Annotated:
        annotated_type, *annotations = type_args
        return Annotated[replace_types(annotated_type, type_map), tuple(annotations)]

    if (origin_type is ExtLiteral) or (sys.version_info >= (3, 8) and origin_type is Literal):
        return type_map.get(type_, type_)
    # Having type args is a good indicator that this is a typing module
    # class instantiation or a generic alias of some sort.
    if type_args:
        resolved_type_args = tuple(replace_types(arg, type_map) for arg in type_args)
        if all_identical(type_args, resolved_type_args):
            # If all arguments are the same, there is no need to modify the
            # type or create a new object at all
            return type_
        if (
            origin_type is not None
            and isinstance(type_, typing_base)
            and not isinstance(origin_type, typing_base)
            and getattr(type_, '_name', None) is not None
        ):
            # In python < 3.9 generic aliases don't exist so any of these like `list`,
            # `type` or `collections.abc.Callable` need to be translated.
            # See: https://www.python.org/dev/peps/pep-0585
            origin_type = getattr(typing, type_._name)
        assert origin_type is not None
        # PEP-604 syntax (Ex.: list | str) is represented with a types.UnionType object that does not have __getitem__.
        # We also cannot use isinstance() since we have to compare types.
        if sys.version_info >= (3, 10) and origin_type is types.UnionType:  # noqa: E721
            return _UnionGenericAlias(origin_type, resolved_type_args)
        return origin_type[resolved_type_args]

    # We handle pydantic generic models separately as they don't have the same
    # semantics as "typing" classes or generic aliases
    if not origin_type and lenient_issubclass(type_, GenericModel) and not type_.__concrete__:
        type_args = type_.__parameters__
        resolved_type_args = tuple(replace_types(t, type_map) for t in type_args)
        if all_identical(type_args, resolved_type_args):
            return type_
        return type_[resolved_type_args]

    # Handle special case for typehints that can have lists as arguments.
    # `typing.Callable[[int, str], int]` is an example for this.
    if isinstance(type_, (List, list)):
        resolved_list = list(replace_types(element, type_map) for element in type_)
        if all_identical(type_, resolved_list):
            return type_
        return resolved_list

    # For JsonWrapperValue, need to handle its inner type to allow correct parsing
    # of generic Json arguments like Json[T]
    if not origin_type and lenient_issubclass(type_, JsonWrapper):
        type_.inner_type = replace_types(type_.inner_type, type_map)
        return type_

    # If all else fails, we try to resolve the type directly and otherwise just
    # return the input with no modifications.
    new_type = type_map.get(type_, type_)
    # Convert string to ForwardRef
    if isinstance(new_type, str):
        return ForwardRef(new_type)
    else:
        return new_type


def check_parameters_count(cls: Type[GenericModel], parameters: Tuple[Any, ...]) -> None:
    actual = len(parameters)
    expected = len(cls.__parameters__)
    if actual != expected:
        description = 'many' if actual > expected else 'few'
        raise TypeError(f'Too {description} parameters for {cls.__name__}; actual {actual}, expected {expected}')


DictValues: Type[Any] = {}.values().__class__


def iter_contained_typevars(v: Any) -> Iterator[TypeVarType]:
    """Recursively iterate through all subtypes and type args of `v` and yield any typevars that are found."""
    if isinstance(v, TypeVar):
        yield v
    elif hasattr(v, '__parameters__') and not get_origin(v) and lenient_issubclass(v, GenericModel):
        yield from v.__parameters__
    elif isinstance(v, (DictValues, list)):
        for var in v:
            yield from iter_contained_typevars(var)
    else:
        args = get_args(v)
        for arg in args:
            yield from iter_contained_typevars(arg)


def get_caller_frame_info() -> Tuple[Optional[str], bool]:
    """
    Used inside a function to check whether it was called globally

    Will only work against non-compiled code, therefore used only in pydantic.generics

    :returns Tuple[module_name, called_globally]
    """
    try:
        previous_caller_frame = sys._getframe(2)
    except ValueError as e:
        raise RuntimeError('This function must be used inside another function') from e
    except AttributeError:  # sys module does not have _getframe function, so there's nothing we can do about it
        return None, False
    frame_globals = previous_caller_frame.f_globals
    return frame_globals.get('__name__'), previous_caller_frame.f_locals is frame_globals


def _prepare_model_fields(
    created_model: Type[GenericModel],
    fields: Mapping[str, Any],
    instance_type_hints: Mapping[str, type],
    typevars_map: Mapping[Any, type],
) -> None:
    """
    Replace DeferredType fields with concrete type hints and prepare them.
    """

    for key, field in created_model.__fields__.items():
        if key not in fields:
            assert field.type_.__class__ is not DeferredType
            # https://github.com/nedbat/coveragepy/issues/198
            continue  # pragma: no cover

        assert field.type_.__class__ is DeferredType, field.type_.__class__

        field_type_hint = instance_type_hints[key]
        concrete_type = replace_types(field_type_hint, typevars_map)
        field.type_ = concrete_type
        field.outer_type_ = concrete_type
        field.prepare()
        created_model.__annotations__[key] = concrete_type

# === NexusCore/openenv\Lib\site-packages\setuptools\command\build_py.py ===
from __future__ import annotations

import fnmatch
import itertools
import os
import stat
import textwrap
from collections.abc import Iterable, Iterator
from functools import partial
from glob import glob
from pathlib import Path

from more_itertools import unique_everseen

from .._path import StrPath, StrPathT
from ..dist import Distribution
from ..warnings import SetuptoolsDeprecationWarning

import distutils.command.build_py as orig
import distutils.errors
from distutils.util import convert_path

_IMPLICIT_DATA_FILES = ('*.pyi', 'py.typed')


def make_writable(target) -> None:
    os.chmod(target, os.stat(target).st_mode | stat.S_IWRITE)


class build_py(orig.build_py):
    """Enhanced 'build_py' command that includes data files with packages

    The data files are specified via a 'package_data' argument to 'setup()'.
    See 'setuptools.dist.Distribution' for more details.

    Also, this version of the 'build_py' command allows you to specify both
    'py_modules' and 'packages' in the same setup operation.
    """

    distribution: Distribution  # override distutils.dist.Distribution with setuptools.dist.Distribution
    editable_mode: bool = False
    existing_egg_info_dir: StrPath | None = None  #: Private API, internal use only.

    def finalize_options(self):
        orig.build_py.finalize_options(self)
        self.package_data = self.distribution.package_data
        self.exclude_package_data = self.distribution.exclude_package_data or {}
        if 'data_files' in self.__dict__:
            del self.__dict__['data_files']

    def copy_file(  # type: ignore[override] # No overload, no bytes support
        self,
        infile: StrPath,
        outfile: StrPathT,
        preserve_mode: bool = True,
        preserve_times: bool = True,
        link: str | None = None,
        level: object = 1,
    ) -> tuple[StrPathT | str, bool]:
        # Overwrite base class to allow using links
        if link:
            infile = str(Path(infile).resolve())
            outfile = str(Path(outfile).resolve())  # type: ignore[assignment] # Re-assigning a str when outfile is StrPath is ok
        return super().copy_file(  # pyright: ignore[reportReturnType] # pypa/distutils#309
            infile, outfile, preserve_mode, preserve_times, link, level
        )

    def run(self) -> None:
        """Build modules, packages, and copy data files to build directory"""
        if not (self.py_modules or self.packages) or self.editable_mode:
            return

        if self.py_modules:
            self.build_modules()

        if self.packages:
            self.build_packages()
            self.build_package_data()

        # Only compile actual .py files, using our base class' idea of what our
        # output files are.
        self.byte_compile(orig.build_py.get_outputs(self, include_bytecode=False))

    def __getattr__(self, attr: str):
        "lazily compute data files"
        if attr == 'data_files':
            self.data_files = self._get_data_files()
            return self.data_files
        return orig.build_py.__getattr__(self, attr)

    def _get_data_files(self):
        """Generate list of '(package,src_dir,build_dir,filenames)' tuples"""
        self.analyze_manifest()
        return list(map(self._get_pkg_data_files, self.packages or ()))

    def get_data_files_without_manifest(self):
        """
        Generate list of ``(package,src_dir,build_dir,filenames)`` tuples,
        but without triggering any attempt to analyze or build the manifest.
        """
        # Prevent eventual errors from unset `manifest_files`
        # (that would otherwise be set by `analyze_manifest`)
        self.__dict__.setdefault('manifest_files', {})
        return list(map(self._get_pkg_data_files, self.packages or ()))

    def _get_pkg_data_files(self, package):
        # Locate package source directory
        src_dir = self.get_package_dir(package)

        # Compute package build directory
        build_dir = os.path.join(*([self.build_lib] + package.split('.')))

        # Strip directory from globbed filenames
        filenames = [
            os.path.relpath(file, src_dir)
            for file in self.find_data_files(package, src_dir)
        ]
        return package, src_dir, build_dir, filenames

    def find_data_files(self, package, src_dir):
        """Return filenames for package's data files in 'src_dir'"""
        patterns = self._get_platform_patterns(
            self.package_data,
            package,
            src_dir,
            extra_patterns=_IMPLICIT_DATA_FILES,
        )
        globs_expanded = map(partial(glob, recursive=True), patterns)
        # flatten the expanded globs into an iterable of matches
        globs_matches = itertools.chain.from_iterable(globs_expanded)
        glob_files = filter(os.path.isfile, globs_matches)
        files = itertools.chain(
            self.manifest_files.get(package, []),
            glob_files,
        )
        return self.exclude_data_files(package, src_dir, files)

    def get_outputs(self, include_bytecode: bool = True) -> list[str]:  # type: ignore[override] # Using a real boolean instead of 0|1
        """See :class:`setuptools.commands.build.SubCommand`"""
        if self.editable_mode:
            return list(self.get_output_mapping().keys())
        return super().get_outputs(include_bytecode)

    def get_output_mapping(self) -> dict[str, str]:
        """See :class:`setuptools.commands.build.SubCommand`"""
        mapping = itertools.chain(
            self._get_package_data_output_mapping(),
            self._get_module_mapping(),
        )
        return dict(sorted(mapping, key=lambda x: x[0]))

    def _get_module_mapping(self) -> Iterator[tuple[str, str]]:
        """Iterate over all modules producing (dest, src) pairs."""
        for package, module, module_file in self.find_all_modules():
            package = package.split('.')
            filename = self.get_module_outfile(self.build_lib, package, module)
            yield (filename, module_file)

    def _get_package_data_output_mapping(self) -> Iterator[tuple[str, str]]:
        """Iterate over package data producing (dest, src) pairs."""
        for package, src_dir, build_dir, filenames in self.data_files:
            for filename in filenames:
                target = os.path.join(build_dir, filename)
                srcfile = os.path.join(src_dir, filename)
                yield (target, srcfile)

    def build_package_data(self) -> None:
        """Copy data files into build directory"""
        for target, srcfile in self._get_package_data_output_mapping():
            self.mkpath(os.path.dirname(target))
            _outf, _copied = self.copy_file(srcfile, target)
            make_writable(target)

    def analyze_manifest(self) -> None:
        self.manifest_files: dict[str, list[str]] = {}
        if not self.distribution.include_package_data:
            return
        src_dirs: dict[str, str] = {}
        for package in self.packages or ():
            # Locate package source directory
            src_dirs[assert_relative(self.get_package_dir(package))] = package

        if (
            self.existing_egg_info_dir
            and Path(self.existing_egg_info_dir, "SOURCES.txt").exists()
        ):
            egg_info_dir = self.existing_egg_info_dir
            manifest = Path(egg_info_dir, "SOURCES.txt")
            files = manifest.read_text(encoding="utf-8").splitlines()
        else:
            self.run_command('egg_info')
            ei_cmd = self.get_finalized_command('egg_info')
            egg_info_dir = ei_cmd.egg_info
            files = ei_cmd.filelist.files

        check = _IncludePackageDataAbuse()
        for path in self._filter_build_files(files, egg_info_dir):
            d, f = os.path.split(assert_relative(path))
            prev = None
            oldf = f
            while d and d != prev and d not in src_dirs:
                prev = d
                d, df = os.path.split(d)
                f = os.path.join(df, f)
            if d in src_dirs:
                if f == oldf:
                    if check.is_module(f):
                        continue  # it's a module, not data
                else:
                    importable = check.importable_subpackage(src_dirs[d], f)
                    if importable:
                        check.warn(importable)
                self.manifest_files.setdefault(src_dirs[d], []).append(path)

    def _filter_build_files(
        self, files: Iterable[str], egg_info: StrPath
    ) -> Iterator[str]:
        """
        ``build_meta`` may try to create egg_info outside of the project directory,
        and this can be problematic for certain plugins (reported in issue #3500).

        Extensions might also include between their sources files created on the
        ``build_lib`` and ``build_temp`` directories.

        This function should filter this case of invalid files out.
        """
        build = self.get_finalized_command("build")
        build_dirs = (egg_info, self.build_lib, build.build_temp, build.build_base)
        norm_dirs = [os.path.normpath(p) for p in build_dirs if p]

        for file in files:
            norm_path = os.path.normpath(file)
            if not os.path.isabs(file) or all(d not in norm_path for d in norm_dirs):
                yield file

    def get_data_files(self) -> None:
        pass  # Lazily compute data files in _get_data_files() function.

    def check_package(self, package, package_dir):
        """Check namespace packages' __init__ for declare_namespace"""
        try:
            return self.packages_checked[package]
        except KeyError:
            pass

        init_py = orig.build_py.check_package(self, package, package_dir)
        self.packages_checked[package] = init_py

        if not init_py or not self.distribution.namespace_packages:
            return init_py

        for pkg in self.distribution.namespace_packages:
            if pkg == package or pkg.startswith(package + '.'):
                break
        else:
            return init_py

        with open(init_py, 'rb') as f:
            contents = f.read()
        if b'declare_namespace' not in contents:
            raise distutils.errors.DistutilsError(
                f"Namespace package problem: {package} is a namespace package, but "
                "its\n__init__.py does not call declare_namespace()! Please "
                'fix it.\n(See the setuptools manual under '
                '"Namespace Packages" for details.)\n"'
            )
        return init_py

    def initialize_options(self):
        self.packages_checked = {}
        orig.build_py.initialize_options(self)
        self.editable_mode = False
        self.existing_egg_info_dir = None

    def get_package_dir(self, package):
        res = orig.build_py.get_package_dir(self, package)
        if self.distribution.src_root is not None:
            return os.path.join(self.distribution.src_root, res)
        return res

    def exclude_data_files(self, package, src_dir, files):
        """Filter filenames for package's data files in 'src_dir'"""
        files = list(files)
        patterns = self._get_platform_patterns(
            self.exclude_package_data,
            package,
            src_dir,
        )
        match_groups = (fnmatch.filter(files, pattern) for pattern in patterns)
        # flatten the groups of matches into an iterable of matches
        matches = itertools.chain.from_iterable(match_groups)
        bad = set(matches)
        keepers = (fn for fn in files if fn not in bad)
        # ditch dupes
        return list(unique_everseen(keepers))

    @staticmethod
    def _get_platform_patterns(spec, package, src_dir, extra_patterns=()):
        """
        yield platform-specific path patterns (suitable for glob
        or fn_match) from a glob-based spec (such as
        self.package_data or self.exclude_package_data)
        matching package in src_dir.
        """
        raw_patterns = itertools.chain(
            extra_patterns,
            spec.get('', []),
            spec.get(package, []),
        )
        return (
            # Each pattern has to be converted to a platform-specific path
            os.path.join(src_dir, convert_path(pattern))
            for pattern in raw_patterns
        )


def assert_relative(path):
    if not os.path.isabs(path):
        return path
    from distutils.errors import DistutilsSetupError

    msg = (
        textwrap.dedent(
            """
        Error: setup script specifies an absolute path:

            %s

        setup() arguments must *always* be /-separated paths relative to the
        setup.py directory, *never* absolute paths.
        """
        ).lstrip()
        % path
    )
    raise DistutilsSetupError(msg)


class _IncludePackageDataAbuse:
    """Inform users that package or module is included as 'data file'"""

    class _Warning(SetuptoolsDeprecationWarning):
        _SUMMARY = """
        Package {importable!r} is absent from the `packages` configuration.
        """

        _DETAILS = """
        ############################
        # Package would be ignored #
        ############################
        Python recognizes {importable!r} as an importable package[^1],
        but it is absent from setuptools' `packages` configuration.

        This leads to an ambiguous overall configuration. If you want to distribute this
        package, please make sure that {importable!r} is explicitly added
        to the `packages` configuration field.

        Alternatively, you can also rely on setuptools' discovery methods
        (for example by using `find_namespace_packages(...)`/`find_namespace:`
        instead of `find_packages(...)`/`find:`).

        You can read more about "package discovery" on setuptools documentation page:

        - https://setuptools.pypa.io/en/latest/userguide/package_discovery.html

        If you don't want {importable!r} to be distributed and are
        already explicitly excluding {importable!r} via
        `find_namespace_packages(...)/find_namespace` or `find_packages(...)/find`,
        you can try to use `exclude_package_data`, or `include-package-data=False` in
        combination with a more fine grained `package-data` configuration.

        You can read more about "package data files" on setuptools documentation page:

        - https://setuptools.pypa.io/en/latest/userguide/datafiles.html


        [^1]: For Python, any directory (with suitable naming) can be imported,
              even if it does not contain any `.py` files.
              On the other hand, currently there is no concept of package data
              directory, all directories are treated like packages.
        """
        # _DUE_DATE: still not defined as this is particularly controversial.
        # Warning initially introduced in May 2022. See issue #3340 for discussion.

    def __init__(self):
        self._already_warned = set()

    def is_module(self, file):
        return file.endswith(".py") and file[: -len(".py")].isidentifier()

    def importable_subpackage(self, parent, file):
        pkg = Path(file).parent
        parts = list(itertools.takewhile(str.isidentifier, pkg.parts))
        if parts:
            return ".".join([parent, *parts])
        return None

    def warn(self, importable):
        if importable not in self._already_warned:
            self._Warning.emit(importable=importable)
            self._already_warned.add(importable)

# === NexusCore/openenv\Lib\site-packages\aiohttp\web_runner.py ===
import asyncio
import signal
import socket
import warnings
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, List, Optional, Set

from yarl import URL

from .typedefs import PathLike
from .web_app import Application
from .web_server import Server

if TYPE_CHECKING:
    from ssl import SSLContext
else:
    try:
        from ssl import SSLContext
    except ImportError:  # pragma: no cover
        SSLContext = object  # type: ignore[misc,assignment]

__all__ = (
    "BaseSite",
    "TCPSite",
    "UnixSite",
    "NamedPipeSite",
    "SockSite",
    "BaseRunner",
    "AppRunner",
    "ServerRunner",
    "GracefulExit",
)


class GracefulExit(SystemExit):
    code = 1


def _raise_graceful_exit() -> None:
    raise GracefulExit()


class BaseSite(ABC):
    __slots__ = ("_runner", "_ssl_context", "_backlog", "_server")

    def __init__(
        self,
        runner: "BaseRunner",
        *,
        shutdown_timeout: float = 60.0,
        ssl_context: Optional[SSLContext] = None,
        backlog: int = 128,
    ) -> None:
        if runner.server is None:
            raise RuntimeError("Call runner.setup() before making a site")
        if shutdown_timeout != 60.0:
            msg = "shutdown_timeout should be set on BaseRunner"
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            runner._shutdown_timeout = shutdown_timeout
        self._runner = runner
        self._ssl_context = ssl_context
        self._backlog = backlog
        self._server: Optional[asyncio.AbstractServer] = None

    @property
    @abstractmethod
    def name(self) -> str:
        pass  # pragma: no cover

    @abstractmethod
    async def start(self) -> None:
        self._runner._reg_site(self)

    async def stop(self) -> None:
        self._runner._check_site(self)
        if self._server is not None:  # Maybe not started yet
            self._server.close()

        self._runner._unreg_site(self)


class TCPSite(BaseSite):
    __slots__ = ("_host", "_port", "_reuse_address", "_reuse_port")

    def __init__(
        self,
        runner: "BaseRunner",
        host: Optional[str] = None,
        port: Optional[int] = None,
        *,
        shutdown_timeout: float = 60.0,
        ssl_context: Optional[SSLContext] = None,
        backlog: int = 128,
        reuse_address: Optional[bool] = None,
        reuse_port: Optional[bool] = None,
    ) -> None:
        super().__init__(
            runner,
            shutdown_timeout=shutdown_timeout,
            ssl_context=ssl_context,
            backlog=backlog,
        )
        self._host = host
        if port is None:
            port = 8443 if self._ssl_context else 8080
        self._port = port
        self._reuse_address = reuse_address
        self._reuse_port = reuse_port

    @property
    def name(self) -> str:
        scheme = "https" if self._ssl_context else "http"
        host = "0.0.0.0" if not self._host else self._host
        return str(URL.build(scheme=scheme, host=host, port=self._port))

    async def start(self) -> None:
        await super().start()
        loop = asyncio.get_event_loop()
        server = self._runner.server
        assert server is not None
        self._server = await loop.create_server(
            server,
            self._host,
            self._port,
            ssl=self._ssl_context,
            backlog=self._backlog,
            reuse_address=self._reuse_address,
            reuse_port=self._reuse_port,
        )


class UnixSite(BaseSite):
    __slots__ = ("_path",)

    def __init__(
        self,
        runner: "BaseRunner",
        path: PathLike,
        *,
        shutdown_timeout: float = 60.0,
        ssl_context: Optional[SSLContext] = None,
        backlog: int = 128,
    ) -> None:
        super().__init__(
            runner,
            shutdown_timeout=shutdown_timeout,
            ssl_context=ssl_context,
            backlog=backlog,
        )
        self._path = path

    @property
    def name(self) -> str:
        scheme = "https" if self._ssl_context else "http"
        return f"{scheme}://unix:{self._path}:"

    async def start(self) -> None:
        await super().start()
        loop = asyncio.get_event_loop()
        server = self._runner.server
        assert server is not None
        self._server = await loop.create_unix_server(
            server,
            self._path,
            ssl=self._ssl_context,
            backlog=self._backlog,
        )


class NamedPipeSite(BaseSite):
    __slots__ = ("_path",)

    def __init__(
        self, runner: "BaseRunner", path: str, *, shutdown_timeout: float = 60.0
    ) -> None:
        loop = asyncio.get_event_loop()
        if not isinstance(
            loop, asyncio.ProactorEventLoop  # type: ignore[attr-defined]
        ):
            raise RuntimeError(
                "Named Pipes only available in proactor loop under windows"
            )
        super().__init__(runner, shutdown_timeout=shutdown_timeout)
        self._path = path

    @property
    def name(self) -> str:
        return self._path

    async def start(self) -> None:
        await super().start()
        loop = asyncio.get_event_loop()
        server = self._runner.server
        assert server is not None
        _server = await loop.start_serving_pipe(  # type: ignore[attr-defined]
            server, self._path
        )
        self._server = _server[0]


class SockSite(BaseSite):
    __slots__ = ("_sock", "_name")

    def __init__(
        self,
        runner: "BaseRunner",
        sock: socket.socket,
        *,
        shutdown_timeout: float = 60.0,
        ssl_context: Optional[SSLContext] = None,
        backlog: int = 128,
    ) -> None:
        super().__init__(
            runner,
            shutdown_timeout=shutdown_timeout,
            ssl_context=ssl_context,
            backlog=backlog,
        )
        self._sock = sock
        scheme = "https" if self._ssl_context else "http"
        if hasattr(socket, "AF_UNIX") and sock.family == socket.AF_UNIX:
            name = f"{scheme}://unix:{sock.getsockname()}:"
        else:
            host, port = sock.getsockname()[:2]
            name = str(URL.build(scheme=scheme, host=host, port=port))
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def start(self) -> None:
        await super().start()
        loop = asyncio.get_event_loop()
        server = self._runner.server
        assert server is not None
        self._server = await loop.create_server(
            server, sock=self._sock, ssl=self._ssl_context, backlog=self._backlog
        )


class BaseRunner(ABC):
    __slots__ = ("_handle_signals", "_kwargs", "_server", "_sites", "_shutdown_timeout")

    def __init__(
        self,
        *,
        handle_signals: bool = False,
        shutdown_timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        self._handle_signals = handle_signals
        self._kwargs = kwargs
        self._server: Optional[Server] = None
        self._sites: List[BaseSite] = []
        self._shutdown_timeout = shutdown_timeout

    @property
    def server(self) -> Optional[Server]:
        return self._server

    @property
    def addresses(self) -> List[Any]:
        ret: List[Any] = []
        for site in self._sites:
            server = site._server
            if server is not None:
                sockets = server.sockets  # type: ignore[attr-defined]
                if sockets is not None:
                    for sock in sockets:
                        ret.append(sock.getsockname())
        return ret

    @property
    def sites(self) -> Set[BaseSite]:
        return set(self._sites)

    async def setup(self) -> None:
        loop = asyncio.get_event_loop()

        if self._handle_signals:
            try:
                loop.add_signal_handler(signal.SIGINT, _raise_graceful_exit)
                loop.add_signal_handler(signal.SIGTERM, _raise_graceful_exit)
            except NotImplementedError:  # pragma: no cover
                # add_signal_handler is not implemented on Windows
                pass

        self._server = await self._make_server()

    @abstractmethod
    async def shutdown(self) -> None:
        """Call any shutdown hooks to help server close gracefully."""

    async def cleanup(self) -> None:
        # The loop over sites is intentional, an exception on gather()
        # leaves self._sites in unpredictable state.
        # The loop guaranties that a site is either deleted on success or
        # still present on failure
        for site in list(self._sites):
            await site.stop()

        if self._server:  # If setup succeeded
            # Yield to event loop to ensure incoming requests prior to stopping the sites
            # have all started to be handled before we proceed to close idle connections.
            await asyncio.sleep(0)
            self._server.pre_shutdown()
            await self.shutdown()
            await self._server.shutdown(self._shutdown_timeout)
        await self._cleanup_server()

        self._server = None
        if self._handle_signals:
            loop = asyncio.get_running_loop()
            try:
                loop.remove_signal_handler(signal.SIGINT)
                loop.remove_signal_handler(signal.SIGTERM)
            except NotImplementedError:  # pragma: no cover
                # remove_signal_handler is not implemented on Windows
                pass

    @abstractmethod
    async def _make_server(self) -> Server:
        pass  # pragma: no cover

    @abstractmethod
    async def _cleanup_server(self) -> None:
        pass  # pragma: no cover

    def _reg_site(self, site: BaseSite) -> None:
        if site in self._sites:
            raise RuntimeError(f"Site {site} is already registered in runner {self}")
        self._sites.append(site)

    def _check_site(self, site: BaseSite) -> None:
        if site not in self._sites:
            raise RuntimeError(f"Site {site} is not registered in runner {self}")

    def _unreg_site(self, site: BaseSite) -> None:
        if site not in self._sites:
            raise RuntimeError(f"Site {site} is not registered in runner {self}")
        self._sites.remove(site)


class ServerRunner(BaseRunner):
    """Low-level web server runner"""

    __slots__ = ("_web_server",)

    def __init__(
        self, web_server: Server, *, handle_signals: bool = False, **kwargs: Any
    ) -> None:
        super().__init__(handle_signals=handle_signals, **kwargs)
        self._web_server = web_server

    async def shutdown(self) -> None:
        pass

    async def _make_server(self) -> Server:
        return self._web_server

    async def _cleanup_server(self) -> None:
        pass


class AppRunner(BaseRunner):
    """Web Application runner"""

    __slots__ = ("_app",)

    def __init__(
        self, app: Application, *, handle_signals: bool = False, **kwargs: Any
    ) -> None:
        super().__init__(handle_signals=handle_signals, **kwargs)
        if not isinstance(app, Application):
            raise TypeError(
                "The first argument should be web.Application "
                "instance, got {!r}".format(app)
            )
        self._app = app

    @property
    def app(self) -> Application:
        return self._app

    async def shutdown(self) -> None:
        await self._app.shutdown()

    async def _make_server(self) -> Server:
        loop = asyncio.get_event_loop()
        self._app._set_loop(loop)
        self._app.on_startup.freeze()
        await self._app.startup()
        self._app.freeze()

        return self._app._make_handler(loop=loop, **self._kwargs)

    async def _cleanup_server(self) -> None:
        await self._app.cleanup()

# === NexusCore/openenv\Lib\site-packages\tqdm\utils.py ===
"""
General helpers required for `tqdm.std`.
"""
import os
import re
import sys
from functools import partial, partialmethod, wraps
from inspect import signature
# TODO consider using wcswidth third-party package for 0-width characters
from unicodedata import east_asian_width
from warnings import warn
from weakref import proxy

_range, _unich, _unicode, _basestring = range, chr, str, str
CUR_OS = sys.platform
IS_WIN = any(CUR_OS.startswith(i) for i in ['win32', 'cygwin'])
IS_NIX = any(CUR_OS.startswith(i) for i in ['aix', 'linux', 'darwin', 'freebsd'])
RE_ANSI = re.compile(r"\x1b\[[;\d]*[A-Za-z]")

try:
    if IS_WIN:
        import colorama
    else:
        raise ImportError
except ImportError:
    colorama = None
else:
    try:
        colorama.init(strip=False)
    except TypeError:
        colorama.init()


def envwrap(prefix, types=None, is_method=False):
    """
    Override parameter defaults via `os.environ[prefix + param_name]`.
    Maps UPPER_CASE env vars map to lower_case param names.
    camelCase isn't supported (because Windows ignores case).

    Precedence (highest first):

    - call (`foo(a=3)`)
    - environ (`FOO_A=2`)
    - signature (`def foo(a=1)`)

    Parameters
    ----------
    prefix  : str
        Env var prefix, e.g. "FOO_"
    types  : dict, optional
        Fallback mappings `{'param_name': type, ...}` if types cannot be
        inferred from function signature.
        Consider using `types=collections.defaultdict(lambda: ast.literal_eval)`.
    is_method  : bool, optional
        Whether to use `functools.partialmethod`. If (default: False) use `functools.partial`.

    Examples
    --------
    ```
    $ cat foo.py
    from tqdm.utils import envwrap
    @envwrap("FOO_")
    def test(a=1, b=2, c=3):
        print(f"received: a={a}, b={b}, c={c}")

    $ FOO_A=42 FOO_C=1337 python -c 'import foo; foo.test(c=99)'
    received: a=42, b=2, c=99
    ```
    """
    if types is None:
        types = {}
    i = len(prefix)
    env_overrides = {k[i:].lower(): v for k, v in os.environ.items() if k.startswith(prefix)}
    part = partialmethod if is_method else partial

    def wrap(func):
        params = signature(func).parameters
        # ignore unknown env vars
        overrides = {k: v for k, v in env_overrides.items() if k in params}
        # infer overrides' `type`s
        for k in overrides:
            param = params[k]
            if param.annotation is not param.empty:  # typehints
                for typ in getattr(param.annotation, '__args__', (param.annotation,)):
                    try:
                        overrides[k] = typ(overrides[k])
                    except Exception:
                        pass
                    else:
                        break
            elif param.default is not None:  # type of default value
                overrides[k] = type(param.default)(overrides[k])
            else:
                try:  # `types` fallback
                    overrides[k] = types[k](overrides[k])
                except KeyError:  # keep unconverted (`str`)
                    pass
        return part(func, **overrides)
    return wrap


class FormatReplace(object):
    """
    >>> a = FormatReplace('something')
    >>> f"{a:5d}"
    'something'
    """  # NOQA: P102
    def __init__(self, replace=''):
        self.replace = replace
        self.format_called = 0

    def __format__(self, _):
        self.format_called += 1
        return self.replace


class Comparable(object):
    """Assumes child has self._comparable attr/@property"""
    def __lt__(self, other):
        return self._comparable < other._comparable

    def __le__(self, other):
        return (self < other) or (self == other)

    def __eq__(self, other):
        return self._comparable == other._comparable

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        return not self <= other

    def __ge__(self, other):
        return not self < other


class ObjectWrapper(object):
    def __getattr__(self, name):
        return getattr(self._wrapped, name)

    def __setattr__(self, name, value):
        return setattr(self._wrapped, name, value)

    def wrapper_getattr(self, name):
        """Actual `self.getattr` rather than self._wrapped.getattr"""
        try:
            return object.__getattr__(self, name)
        except AttributeError:  # py2
            return getattr(self, name)

    def wrapper_setattr(self, name, value):
        """Actual `self.setattr` rather than self._wrapped.setattr"""
        return object.__setattr__(self, name, value)

    def __init__(self, wrapped):
        """
        Thin wrapper around a given object
        """
        self.wrapper_setattr('_wrapped', wrapped)


class SimpleTextIOWrapper(ObjectWrapper):
    """
    Change only `.write()` of the wrapped object by encoding the passed
    value and passing the result to the wrapped object's `.write()` method.
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, wrapped, encoding):
        super().__init__(wrapped)
        self.wrapper_setattr('encoding', encoding)

    def write(self, s):
        """
        Encode `s` and pass to the wrapped object's `.write()` method.
        """
        return self._wrapped.write(s.encode(self.wrapper_getattr('encoding')))

    def __eq__(self, other):
        return self._wrapped == getattr(other, '_wrapped', other)


class DisableOnWriteError(ObjectWrapper):
    """
    Disable the given `tqdm_instance` upon `write()` or `flush()` errors.
    """
    @staticmethod
    def disable_on_exception(tqdm_instance, func):
        """
        Quietly set `tqdm_instance.miniters=inf` if `func` raises `errno=5`.
        """
        tqdm_instance = proxy(tqdm_instance)

        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except OSError as e:
                if e.errno != 5:
                    raise
                try:
                    tqdm_instance.miniters = float('inf')
                except ReferenceError:
                    pass
            except ValueError as e:
                if 'closed' not in str(e):
                    raise
                try:
                    tqdm_instance.miniters = float('inf')
                except ReferenceError:
                    pass
        return inner

    def __init__(self, wrapped, tqdm_instance):
        super().__init__(wrapped)
        if hasattr(wrapped, 'write'):
            self.wrapper_setattr(
                'write', self.disable_on_exception(tqdm_instance, wrapped.write))
        if hasattr(wrapped, 'flush'):
            self.wrapper_setattr(
                'flush', self.disable_on_exception(tqdm_instance, wrapped.flush))

    def __eq__(self, other):
        return self._wrapped == getattr(other, '_wrapped', other)


class CallbackIOWrapper(ObjectWrapper):
    def __init__(self, callback, stream, method="read"):
        """
        Wrap a given `file`-like object's `read()` or `write()` to report
        lengths to the given `callback`
        """
        super().__init__(stream)
        func = getattr(stream, method)
        if method == "write":
            @wraps(func)
            def write(data, *args, **kwargs):
                res = func(data, *args, **kwargs)
                callback(len(data))
                return res
            self.wrapper_setattr('write', write)
        elif method == "read":
            @wraps(func)
            def read(*args, **kwargs):
                data = func(*args, **kwargs)
                callback(len(data))
                return data
            self.wrapper_setattr('read', read)
        else:
            raise KeyError("Can only wrap read/write methods")


def _is_utf(encoding):
    try:
        u'\u2588\u2589'.encode(encoding)
    except UnicodeEncodeError:
        return False
    except Exception:
        try:
            return encoding.lower().startswith('utf-') or ('U8' == encoding)
        except Exception:
            return False
    else:
        return True


def _supports_unicode(fp):
    try:
        return _is_utf(fp.encoding)
    except AttributeError:
        return False


def _is_ascii(s):
    if isinstance(s, str):
        for c in s:
            if ord(c) > 255:
                return False
        return True
    return _supports_unicode(s)


def _screen_shape_wrapper():  # pragma: no cover
    """
    Return a function which returns console dimensions (width, height).
    Supported: linux, osx, windows, cygwin.
    """
    _screen_shape = None
    if IS_WIN:
        _screen_shape = _screen_shape_windows
        if _screen_shape is None:
            _screen_shape = _screen_shape_tput
    if IS_NIX:
        _screen_shape = _screen_shape_linux
    return _screen_shape


def _screen_shape_windows(fp):  # pragma: no cover
    try:
        import struct
        from ctypes import create_string_buffer, windll
        from sys import stdin, stdout

        io_handle = -12  # assume stderr
        if fp == stdin:
            io_handle = -10
        elif fp == stdout:
            io_handle = -11

        h = windll.kernel32.GetStdHandle(io_handle)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            (_bufx, _bufy, _curx, _cury, _wattr, left, top, right, bottom,
             _maxx, _maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            return right - left, bottom - top  # +1
    except Exception:  # nosec
        pass
    return None, None


def _screen_shape_tput(*_):  # pragma: no cover
    """cygwin xterm (windows)"""
    try:
        import shlex
        from subprocess import check_call  # nosec
        return [int(check_call(shlex.split('tput ' + i))) - 1
                for i in ('cols', 'lines')]
    except Exception:  # nosec
        pass
    return None, None


def _screen_shape_linux(fp):  # pragma: no cover

    try:
        from array import array
        from fcntl import ioctl
        from termios import TIOCGWINSZ
    except ImportError:
        return None, None
    else:
        try:
            rows, cols = array('h', ioctl(fp, TIOCGWINSZ, '\0' * 8))[:2]
            return cols, rows
        except Exception:
            try:
                return [int(os.environ[i]) - 1 for i in ("COLUMNS", "LINES")]
            except (KeyError, ValueError):
                return None, None


def _environ_cols_wrapper():  # pragma: no cover
    """
    Return a function which returns console width.
    Supported: linux, osx, windows, cygwin.
    """
    warn("Use `_screen_shape_wrapper()(file)[0]` instead of"
         " `_environ_cols_wrapper()(file)`", DeprecationWarning, stacklevel=2)
    shape = _screen_shape_wrapper()
    if not shape:
        return None

    @wraps(shape)
    def inner(fp):
        return shape(fp)[0]

    return inner


def _term_move_up():  # pragma: no cover
    return '' if (os.name == 'nt') and (colorama is None) else '\x1b[A'


def _text_width(s):
    return sum(2 if east_asian_width(ch) in 'FW' else 1 for ch in str(s))


def disp_len(data):
    """
    Returns the real on-screen length of a string which may contain
    ANSI control codes and wide chars.
    """
    return _text_width(RE_ANSI.sub('', data))


def disp_trim(data, length):
    """
    Trim a string which may contain ANSI control characters.
    """
    if len(data) == disp_len(data):
        return data[:length]

    ansi_present = bool(RE_ANSI.search(data))
    while disp_len(data) > length:  # carefully delete one char at a time
        data = data[:-1]
    if ansi_present and bool(RE_ANSI.search(data)):
        # assume ANSI reset is required
        return data if data.endswith("\033[0m") else data + "\033[0m"
    return data

# === NexusCore/openenv\Lib\site-packages\git\refs\log.py ===
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

__all__ = ["RefLog", "RefLogEntry"]

from mmap import mmap
import os.path as osp
import re
import time as _time

from git.compat import defenc
from git.objects.util import (
    Serializable,
    altz_to_utctz_str,
    parse_date,
)
from git.util import (
    Actor,
    LockedFD,
    LockFile,
    assure_directory_exists,
    bin_to_hex,
    file_contents_ro_filepath,
    to_native_path,
)

# typing ------------------------------------------------------------------

from typing import Iterator, List, Tuple, TYPE_CHECKING, Union

from git.types import PathLike

if TYPE_CHECKING:
    from io import BytesIO

    from git.config import GitConfigParser, SectionConstraint
    from git.refs import SymbolicReference

# ------------------------------------------------------------------------------


class RefLogEntry(Tuple[str, str, Actor, Tuple[int, int], str]):
    """Named tuple allowing easy access to the revlog data fields."""

    _re_hexsha_only = re.compile(r"^[0-9A-Fa-f]{40}$")

    __slots__ = ()

    def __repr__(self) -> str:
        """Representation of ourselves in git reflog format."""
        return self.format()

    def format(self) -> str:
        """:return: A string suitable to be placed in a reflog file."""
        act = self.actor
        time = self.time
        return "{} {} {} <{}> {!s} {}\t{}\n".format(
            self.oldhexsha,
            self.newhexsha,
            act.name,
            act.email,
            time[0],
            altz_to_utctz_str(time[1]),
            self.message,
        )

    @property
    def oldhexsha(self) -> str:
        """The hexsha to the commit the ref pointed to before the change."""
        return self[0]

    @property
    def newhexsha(self) -> str:
        """The hexsha to the commit the ref now points to, after the change."""
        return self[1]

    @property
    def actor(self) -> Actor:
        """Actor instance, providing access."""
        return self[2]

    @property
    def time(self) -> Tuple[int, int]:
        """Time as tuple:

        * [0] = ``int(time)``
        * [1] = ``int(timezone_offset)`` in :attr:`time.altzone` format
        """
        return self[3]

    @property
    def message(self) -> str:
        """Message describing the operation that acted on the reference."""
        return self[4]

    @classmethod
    def new(
        cls,
        oldhexsha: str,
        newhexsha: str,
        actor: Actor,
        time: int,
        tz_offset: int,
        message: str,
    ) -> "RefLogEntry":  # skipcq: PYL-W0621
        """:return: New instance of a :class:`RefLogEntry`"""
        if not isinstance(actor, Actor):
            raise ValueError("Need actor instance, got %s" % actor)
        # END check types
        return RefLogEntry((oldhexsha, newhexsha, actor, (time, tz_offset), message))

    @classmethod
    def from_line(cls, line: bytes) -> "RefLogEntry":
        """:return: New :class:`RefLogEntry` instance from the given revlog line.

        :param line:
            Line bytes without trailing newline

        :raise ValueError:
            If `line` could not be parsed.
        """
        line_str = line.decode(defenc)
        fields = line_str.split("\t", 1)
        if len(fields) == 1:
            info, msg = fields[0], None
        elif len(fields) == 2:
            info, msg = fields
        else:
            raise ValueError("Line must have up to two TAB-separated fields." " Got %s" % repr(line_str))
        # END handle first split

        oldhexsha = info[:40]
        newhexsha = info[41:81]
        for hexsha in (oldhexsha, newhexsha):
            if not cls._re_hexsha_only.match(hexsha):
                raise ValueError("Invalid hexsha: %r" % (hexsha,))
            # END if hexsha re doesn't match
        # END for each hexsha

        email_end = info.find(">", 82)
        if email_end == -1:
            raise ValueError("Missing token: >")
        # END handle missing end brace

        actor = Actor._from_string(info[82 : email_end + 1])
        time, tz_offset = parse_date(info[email_end + 2 :])  # skipcq: PYL-W0621

        return RefLogEntry((oldhexsha, newhexsha, actor, (time, tz_offset), msg))


class RefLog(List[RefLogEntry], Serializable):
    R"""A reflog contains :class:`RefLogEntry`\s, each of which defines a certain state
    of the head in question. Custom query methods allow to retrieve log entries by date
    or by other criteria.

    Reflog entries are ordered. The first added entry is first in the list. The last
    entry, i.e. the last change of the head or reference, is last in the list.
    """

    __slots__ = ("_path",)

    def __new__(cls, filepath: Union[PathLike, None] = None) -> "RefLog":
        inst = super().__new__(cls)
        return inst

    def __init__(self, filepath: Union[PathLike, None] = None) -> None:
        """Initialize this instance with an optional filepath, from which we will
        initialize our data. The path is also used to write changes back using the
        :meth:`write` method."""
        self._path = filepath
        if filepath is not None:
            self._read_from_file()
        # END handle filepath

    def _read_from_file(self) -> None:
        try:
            fmap = file_contents_ro_filepath(self._path, stream=True, allow_mmap=True)
        except OSError:
            # It is possible and allowed that the file doesn't exist!
            return
        # END handle invalid log

        try:
            self._deserialize(fmap)
        finally:
            fmap.close()
        # END handle closing of handle

    # { Interface

    @classmethod
    def from_file(cls, filepath: PathLike) -> "RefLog":
        """
        :return:
            A new :class:`RefLog` instance containing all entries from the reflog at the
            given `filepath`.

        :param filepath:
            Path to reflog.

        :raise ValueError:
            If the file could not be read or was corrupted in some way.
        """
        return cls(filepath)

    @classmethod
    def path(cls, ref: "SymbolicReference") -> str:
        """
        :return:
            String to absolute path at which the reflog of the given ref instance would
            be found. The path is not guaranteed to point to a valid file though.

        :param ref:
            :class:`~git.refs.symbolic.SymbolicReference` instance
        """
        return osp.join(ref.repo.git_dir, "logs", to_native_path(ref.path))

    @classmethod
    def iter_entries(cls, stream: Union[str, "BytesIO", mmap]) -> Iterator[RefLogEntry]:
        """
        :return:
            Iterator yielding :class:`RefLogEntry` instances, one for each line read
            from the given stream.

        :param stream:
            File-like object containing the revlog in its native format or string
            instance pointing to a file to read.
        """
        new_entry = RefLogEntry.from_line
        if isinstance(stream, str):
            # Default args return mmap since Python 3.
            _stream = file_contents_ro_filepath(stream)
            assert isinstance(_stream, mmap)
        else:
            _stream = stream
        # END handle stream type
        while True:
            line = _stream.readline()
            if not line:
                return
            yield new_entry(line.strip())
        # END endless loop

    @classmethod
    def entry_at(cls, filepath: PathLike, index: int) -> "RefLogEntry":
        """
        :return:
            :class:`RefLogEntry` at the given index.

        :param filepath:
            Full path to the index file from which to read the entry.

        :param index:
            Python list compatible index, i.e. it may be negative to specify an entry
            counted from the end of the list.

        :raise IndexError:
            If the entry didn't exist.

        :note:
            This method is faster as it only parses the entry at index, skipping all
            other lines. Nonetheless, the whole file has to be read if the index is
            negative.
        """
        with open(filepath, "rb") as fp:
            if index < 0:
                return RefLogEntry.from_line(fp.readlines()[index].strip())
            # Read until index is reached.

            for i in range(index + 1):
                line = fp.readline()
                if not line:
                    raise IndexError(f"Index file ended at line {i + 1}, before given index was reached")
                # END abort on eof
            # END handle runup

            return RefLogEntry.from_line(line.strip())
        # END handle index

    def to_file(self, filepath: PathLike) -> None:
        """Write the contents of the reflog instance to a file at the given filepath.

        :param filepath:
            Path to file. Parent directories are assumed to exist.
        """
        lfd = LockedFD(filepath)
        assure_directory_exists(filepath, is_file=True)

        fp = lfd.open(write=True, stream=True)
        try:
            self._serialize(fp)
            lfd.commit()
        except BaseException:
            lfd.rollback()
            raise
        # END handle change

    @classmethod
    def append_entry(
        cls,
        config_reader: Union[Actor, "GitConfigParser", "SectionConstraint", None],
        filepath: PathLike,
        oldbinsha: bytes,
        newbinsha: bytes,
        message: str,
        write: bool = True,
    ) -> "RefLogEntry":
        """Append a new log entry to the revlog at filepath.

        :param config_reader:
            Configuration reader of the repository - used to obtain user information.
            May also be an :class:`~git.util.Actor` instance identifying the committer
            directly or ``None``.

        :param filepath:
            Full path to the log file.

        :param oldbinsha:
            Binary sha of the previous commit.

        :param newbinsha:
            Binary sha of the current commit.

        :param message:
            Message describing the change to the reference.

        :param write:
            If ``True``, the changes will be written right away.
            Otherwise the change will not be written.

        :return:
            :class:`RefLogEntry` objects which was appended to the log.

        :note:
            As we are append-only, concurrent access is not a problem as we do not
            interfere with readers.
        """

        if len(oldbinsha) != 20 or len(newbinsha) != 20:
            raise ValueError("Shas need to be given in binary format")
        # END handle sha type
        assure_directory_exists(filepath, is_file=True)
        first_line = message.split("\n")[0]
        if isinstance(config_reader, Actor):
            committer = config_reader  # mypy thinks this is Actor | Gitconfigparser, but why?
        else:
            committer = Actor.committer(config_reader)
        entry = RefLogEntry(
            (
                bin_to_hex(oldbinsha).decode("ascii"),
                bin_to_hex(newbinsha).decode("ascii"),
                committer,
                (int(_time.time()), _time.altzone),
                first_line,
            )
        )

        if write:
            lf = LockFile(filepath)
            lf._obtain_lock_or_raise()
            fd = open(filepath, "ab")
            try:
                fd.write(entry.format().encode(defenc))
            finally:
                fd.close()
                lf._release_lock()
            # END handle write operation
        return entry

    def write(self) -> "RefLog":
        """Write this instance's data to the file we are originating from.

        :return:
            self
        """
        if self._path is None:
            raise ValueError("Instance was not initialized with a path, use to_file(...) instead")
        # END assert path
        self.to_file(self._path)
        return self

    # } END interface

    # { Serializable Interface

    def _serialize(self, stream: "BytesIO") -> "RefLog":
        write = stream.write

        # Write all entries.
        for e in self:
            write(e.format().encode(defenc))
        # END for each entry
        return self

    def _deserialize(self, stream: "BytesIO") -> "RefLog":
        self.extend(self.iter_entries(stream))
        return self

    # } END serializable interface

# === NexusCore/openenv\Lib\site-packages\google\protobuf\message.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

# TODO: We should just make these methods all "pure-virtual" and move
# all implementation out, into reflection.py for now.


"""Contains an abstract base class for protocol messages."""

__author__ = 'robinson@google.com (Will Robinson)'

class Error(Exception):
  """Base error type for this module."""
  pass


class DecodeError(Error):
  """Exception raised when deserializing messages."""
  pass


class EncodeError(Error):
  """Exception raised when serializing messages."""
  pass


class Message(object):

  """Abstract base class for protocol messages.

  Protocol message classes are almost always generated by the protocol
  compiler.  These generated types subclass Message and implement the methods
  shown below.
  """

  # TODO: Link to an HTML document here.

  # TODO: Document that instances of this class will also
  # have an Extensions attribute with __getitem__ and __setitem__.
  # Again, not sure how to best convey this.

  # TODO: Document these fields and methods.

  __slots__ = []

  #: The :class:`google.protobuf.Descriptor`
  # for this message type.
  DESCRIPTOR = None

  def __deepcopy__(self, memo=None):
    clone = type(self)()
    clone.MergeFrom(self)
    return clone

  def __eq__(self, other_msg):
    """Recursively compares two messages by value and structure."""
    raise NotImplementedError

  def __ne__(self, other_msg):
    # Can't just say self != other_msg, since that would infinitely recurse. :)
    return not self == other_msg

  def __hash__(self):
    raise TypeError('unhashable object')

  def __str__(self):
    """Outputs a human-readable representation of the message."""
    raise NotImplementedError

  def __unicode__(self):
    """Outputs a human-readable representation of the message."""
    raise NotImplementedError

  def MergeFrom(self, other_msg):
    """Merges the contents of the specified message into current message.

    This method merges the contents of the specified message into the current
    message. Singular fields that are set in the specified message overwrite
    the corresponding fields in the current message. Repeated fields are
    appended. Singular sub-messages and groups are recursively merged.

    Args:
      other_msg (Message): A message to merge into the current message.
    """
    raise NotImplementedError

  def CopyFrom(self, other_msg):
    """Copies the content of the specified message into the current message.

    The method clears the current message and then merges the specified
    message using MergeFrom.

    Args:
      other_msg (Message): A message to copy into the current one.
    """
    if self is other_msg:
      return
    self.Clear()
    self.MergeFrom(other_msg)

  def Clear(self):
    """Clears all data that was set in the message."""
    raise NotImplementedError

  def SetInParent(self):
    """Mark this as present in the parent.

    This normally happens automatically when you assign a field of a
    sub-message, but sometimes you want to make the sub-message
    present while keeping it empty.  If you find yourself using this,
    you may want to reconsider your design.
    """
    raise NotImplementedError

  def IsInitialized(self):
    """Checks if the message is initialized.

    Returns:
      bool: The method returns True if the message is initialized (i.e. all of
      its required fields are set).
    """
    raise NotImplementedError

  # TODO: MergeFromString() should probably return None and be
  # implemented in terms of a helper that returns the # of bytes read.  Our
  # deserialization routines would use the helper when recursively
  # deserializing, but the end user would almost always just want the no-return
  # MergeFromString().

  def MergeFromString(self, serialized):
    """Merges serialized protocol buffer data into this message.

    When we find a field in `serialized` that is already present
    in this message:

    -   If it's a "repeated" field, we append to the end of our list.
    -   Else, if it's a scalar, we overwrite our field.
    -   Else, (it's a nonrepeated composite), we recursively merge
        into the existing composite.

    Args:
      serialized (bytes): Any object that allows us to call
        ``memoryview(serialized)`` to access a string of bytes using the
        buffer interface.

    Returns:
      int: The number of bytes read from `serialized`.
      For non-group messages, this will always be `len(serialized)`,
      but for messages which are actually groups, this will
      generally be less than `len(serialized)`, since we must
      stop when we reach an ``END_GROUP`` tag.  Note that if
      we *do* stop because of an ``END_GROUP`` tag, the number
      of bytes returned does not include the bytes
      for the ``END_GROUP`` tag information.

    Raises:
      DecodeError: if the input cannot be parsed.
    """
    # TODO: Document handling of unknown fields.
    # TODO: When we switch to a helper, this will return None.
    raise NotImplementedError

  def ParseFromString(self, serialized):
    """Parse serialized protocol buffer data in binary form into this message.

    Like :func:`MergeFromString()`, except we clear the object first.

    Raises:
      message.DecodeError if the input cannot be parsed.
    """
    self.Clear()
    return self.MergeFromString(serialized)

  def SerializeToString(self, **kwargs):
    """Serializes the protocol message to a binary string.

    Keyword Args:
      deterministic (bool): If true, requests deterministic serialization
        of the protobuf, with predictable ordering of map keys.

    Returns:
      A binary string representation of the message if all of the required
      fields in the message are set (i.e. the message is initialized).

    Raises:
      EncodeError: if the message isn't initialized (see :func:`IsInitialized`).
    """
    raise NotImplementedError

  def SerializePartialToString(self, **kwargs):
    """Serializes the protocol message to a binary string.

    This method is similar to SerializeToString but doesn't check if the
    message is initialized.

    Keyword Args:
      deterministic (bool): If true, requests deterministic serialization
        of the protobuf, with predictable ordering of map keys.

    Returns:
      bytes: A serialized representation of the partial message.
    """
    raise NotImplementedError

  # TODO: Decide whether we like these better
  # than auto-generated has_foo() and clear_foo() methods
  # on the instances themselves.  This way is less consistent
  # with C++, but it makes reflection-type access easier and
  # reduces the number of magically autogenerated things.
  #
  # TODO: Be sure to document (and test) exactly
  # which field names are accepted here.  Are we case-sensitive?
  # What do we do with fields that share names with Python keywords
  # like 'lambda' and 'yield'?
  #
  # nnorwitz says:
  # """
  # Typically (in python), an underscore is appended to names that are
  # keywords. So they would become lambda_ or yield_.
  # """
  def ListFields(self):
    """Returns a list of (FieldDescriptor, value) tuples for present fields.

    A message field is non-empty if HasField() would return true. A singular
    primitive field is non-empty if HasField() would return true in proto2 or it
    is non zero in proto3. A repeated field is non-empty if it contains at least
    one element. The fields are ordered by field number.

    Returns:
      list[tuple(FieldDescriptor, value)]: field descriptors and values
      for all fields in the message which are not empty. The values vary by
      field type.
    """
    raise NotImplementedError

  def HasField(self, field_name):
    """Checks if a certain field is set for the message.

    For a oneof group, checks if any field inside is set. Note that if the
    field_name is not defined in the message descriptor, :exc:`ValueError` will
    be raised.

    Args:
      field_name (str): The name of the field to check for presence.

    Returns:
      bool: Whether a value has been set for the named field.

    Raises:
      ValueError: if the `field_name` is not a member of this message.
    """
    raise NotImplementedError

  def ClearField(self, field_name):
    """Clears the contents of a given field.

    Inside a oneof group, clears the field set. If the name neither refers to a
    defined field or oneof group, :exc:`ValueError` is raised.

    Args:
      field_name (str): The name of the field to check for presence.

    Raises:
      ValueError: if the `field_name` is not a member of this message.
    """
    raise NotImplementedError

  def WhichOneof(self, oneof_group):
    """Returns the name of the field that is set inside a oneof group.

    If no field is set, returns None.

    Args:
      oneof_group (str): the name of the oneof group to check.

    Returns:
      str or None: The name of the group that is set, or None.

    Raises:
      ValueError: no group with the given name exists
    """
    raise NotImplementedError

  def HasExtension(self, field_descriptor):
    """Checks if a certain extension is present for this message.

    Extensions are retrieved using the :attr:`Extensions` mapping (if present).

    Args:
      field_descriptor: The field descriptor for the extension to check.

    Returns:
      bool: Whether the extension is present for this message.

    Raises:
      KeyError: if the extension is repeated. Similar to repeated fields,
        there is no separate notion of presence: a "not present" repeated
        extension is an empty list.
    """
    raise NotImplementedError

  def ClearExtension(self, field_descriptor):
    """Clears the contents of a given extension.

    Args:
      field_descriptor: The field descriptor for the extension to clear.
    """
    raise NotImplementedError

  def UnknownFields(self):
    """Returns the UnknownFieldSet.

    Returns:
      UnknownFieldSet: The unknown fields stored in this message.
    """
    raise NotImplementedError

  def DiscardUnknownFields(self):
    """Clears all fields in the :class:`UnknownFieldSet`.

    This operation is recursive for nested message.
    """
    raise NotImplementedError

  def ByteSize(self):
    """Returns the serialized size of this message.

    Recursively calls ByteSize() on all contained messages.

    Returns:
      int: The number of bytes required to serialize this message.
    """
    raise NotImplementedError

  @classmethod
  def FromString(cls, s):
    raise NotImplementedError

# TODO: Remove it in OSS
  @staticmethod
  def RegisterExtension(field_descriptor):
    raise NotImplementedError

  def _SetListener(self, message_listener):
    """Internal method used by the protocol message implementation.
    Clients should not call this directly.

    Sets a listener that this message will call on certain state transitions.

    The purpose of this method is to register back-edges from children to
    parents at runtime, for the purpose of setting "has" bits and
    byte-size-dirty bits in the parent and ancestor objects whenever a child or
    descendant object is modified.

    If the client wants to disconnect this Message from the object tree, she
    explicitly sets callback to None.

    If message_listener is None, unregisters any existing listener.  Otherwise,
    message_listener must implement the MessageListener interface in
    internal/message_listener.py, and we discard any listener registered
    via a previous _SetListener() call.
    """
    raise NotImplementedError

  def __getstate__(self):
    """Support the pickle protocol."""
    return dict(serialized=self.SerializePartialToString())

  def __setstate__(self, state):
    """Support the pickle protocol."""
    self.__init__()
    serialized = state['serialized']
    # On Python 3, using encoding='latin1' is required for unpickling
    # protos pickled by Python 2.
    if not isinstance(serialized, bytes):
      serialized = serialized.encode('latin1')
    self.ParseFromString(serialized)

  def __reduce__(self):
    message_descriptor = self.DESCRIPTOR
    if message_descriptor.containing_type is None:
      return type(self), (), self.__getstate__()
    # the message type must be nested.
    # Python does not pickle nested classes; use the symbol_database on the
    # receiving end.
    container = message_descriptor
    return (_InternalConstructMessage, (container.full_name,),
            self.__getstate__())


def _InternalConstructMessage(full_name):
  """Constructs a nested message."""
  from google.protobuf import symbol_database  # pylint:disable=g-import-not-at-top

  return symbol_database.Default().GetSymbol(full_name)()

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\guardrails\guardrail_hooks\pangea.py ===
# litellm/proxy/guardrails/guardrail_hooks/pangea.py
import os
from typing import Any, Optional, Protocol

from fastapi import HTTPException

from litellm._logging import verbose_proxy_logger
from litellm.caching.dual_cache import DualCache
from litellm.integrations.custom_guardrail import (
    CustomGuardrail,
    log_guardrail_information,
)

from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.proxy._types import UserAPIKeyAuth
from litellm.proxy.common_utils.callback_utils import (
    add_guardrail_to_applied_guardrails_header,
)
from litellm.types.guardrails import GuardrailEventHooks
from litellm.types.utils import LLMResponseTypes, ModelResponse, TextCompletionResponse


class PangeaGuardrailMissingSecrets(Exception):
    """Custom exception for missing Pangea secrets."""

    pass


class _Transformer(Protocol):
    def get_messages(self) -> list[dict]:
        ...

    def update_original_body(self, prompt_messages: list[dict]) -> Any:
        ...


class _TextCompletionRequest:
    def __init__(self, body):
        self.body = body

    def get_messages(self) -> list[dict]:
        return [{"role": "user", "content": self.body["prompt"]}]

    # This mutates the original dict, but we'll still return it anyways
    def update_original_body(self, prompt_messages: list[dict]) -> Any:
        assert len(prompt_messages) == 1
        self.body["prompt"] = prompt_messages[0]["content"]
        return self.body


class _TextCompletionResponse:
    def __init__(self, body):
        self.body = body

    def get_messages(self) -> list[dict]:
        messages = []
        for choice in self.body["choices"]:
            messages.append({"role": "assistant", "content": choice["text"]})

        return messages

    def update_original_body(self, prompt_messages: list[dict]) -> Any:
        assert len(prompt_messages) == len(self.body["choices"])

        for choice, prompt_message in zip(self.body["choices"], prompt_messages):
            choice["text"] = prompt_message["content"]

        return self.body


class _ChatCompletionRequest:
    def __init__(self, body):
        self.body = body

    def get_messages(self) -> list[dict]:
        messages = []

        for message in self.body["messages"]:
            role = message["role"]
            content = message["content"]
            if isinstance(content, str):
                messages.append({"role": role, "content": content})
            if isinstance(content, list):
                for content_part in content:
                    if content_part["type"] == "text":
                        messages.append({"role": role, "content": content_part["text"]})

        return messages

    def update_original_body(self, prompt_messages: list[dict]) -> Any:
        count = 0

        for message in self.body["messages"]:
            content = message["content"]
            if isinstance(content, str):
                message["content"] = prompt_messages[count]["content"]
                count += 1
            if isinstance(content, list):
                for content_part in content:
                    if content_part["type"] == "text":
                        content_part["text"] = prompt_messages[count]["content"]
                        count += 1

        assert len(prompt_messages) == count
        return self.body


class _ChatCompletionResponse:
    def __init__(self, body):
        self.body = body

    def get_messages(self) -> list[dict]:
        messages = []

        for choice in self.body["choices"]:
            messages.append(
                {
                    "role": choice["message"]["role"],
                    "content": choice["message"]["content"],
                }
            )

        return messages

    def update_original_body(self, prompt_messages: list[dict]) -> Any:
        assert len(prompt_messages) == len(self.body["choices"])

        for choice, prompt_message in zip(self.body["choices"], prompt_messages):
            choice["message"]["content"] = prompt_message["content"]

        return self.body


def _get_transformer_for_request(body, call_type) -> Optional[_Transformer]:
    match call_type:
        case "text_completion" | "atext_completion":
            return _TextCompletionRequest(body)
        case "completion" | "acompletion":
            return _ChatCompletionRequest(body)

    return None


def _get_transformer_for_response(body) -> Optional[_Transformer]:
    match body:
        case TextCompletionResponse():
            return _TextCompletionResponse(body)
        case ModelResponse():
            return _ChatCompletionResponse(body)

    return None


class PangeaHandler(CustomGuardrail):
    """
    Pangea AI Guardrail handler to interact with the Pangea AI Guard service.

    This class implements the necessary hooks to call the Pangea AI Guard API
    for input and output scanning based on the configured recipe.
    """

    def __init__(
        self,
        guardrail_name: str,
        pangea_input_recipe: Optional[str] = None,
        pangea_output_recipe: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        **kwargs,
    ):
        """
        Initializes the PangeaHandler.

        Args:
            guardrail_name (str): The name of the guardrail instance.
            pangea_recipe (str): The Pangea recipe key to use for scanning.
            api_key (Optional[str]): The Pangea API key. Reads from PANGEA_API_KEY env var if None.
            api_base (Optional[str]): The Pangea API base URL. Reads from PANGEA_API_BASE env var or uses default if None.
            **kwargs: Additional arguments passed to the CustomGuardrail base class.
        """
        self.async_handler = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.GuardrailCallback
        )
        self.api_key = api_key or os.environ.get("PANGEA_API_KEY")
        if not self.api_key:
            raise PangeaGuardrailMissingSecrets(
                "Pangea API Key not found. Set PANGEA_API_KEY environment variable or pass it in litellm_params."
            )

        # Default Pangea base URL if not provided
        self.api_base = (
            api_base
            or os.environ.get("PANGEA_API_BASE")
            or "https://ai-guard.aws.us.pangea.cloud"
        )
        self.pangea_input_recipe = pangea_input_recipe
        self.pangea_output_recipe = pangea_output_recipe
        self.guardrail_endpoint = f"{self.api_base}/v1/text/guard"

        # Pass relevant kwargs to the parent class
        super().__init__(guardrail_name=guardrail_name, **kwargs)
        verbose_proxy_logger.info(
            f"Initialized Pangea Guardrail: name={guardrail_name}, recipe={pangea_input_recipe}, api_base={self.api_base}"
        )

    async def _call_pangea_guard(self, payload: dict, hook_name: str) -> dict:
        """
        Makes the API call to the Pangea AI Guard endpoint.
        The function itself will raise an error in the case that a response
        should be blocked, but will return a list of redacted messages that the caller
        should act on.

        Args:
            payload (dict): The request payload.
            request_data (dict): Original request data (used for logging/headers).
            hook_name (str): Name of the hook calling this function (for logging).

        Raises:
            HTTPException: If the Pangea API returns a 'blocked: true' response.
            Exception: For other API call failures.

        Returns:
            list[dict]: The original response body
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            verbose_proxy_logger.debug(
                f"Pangea Guardrail ({hook_name}): Calling endpoint {self.guardrail_endpoint} with payload: {payload}"
            )
            response = await self.async_handler.post(
                url=self.guardrail_endpoint, json=payload, headers=headers
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            result = response.json()
            verbose_proxy_logger.debug(
                f"Pangea Guardrail ({hook_name}): Received response: {result}"
            )

            # Check if the request was blocked
            if result.get("result", {}).get("blocked") is True:
                verbose_proxy_logger.warning(
                    f"Pangea Guardrail ({hook_name}): Request blocked. Response: {result}"
                )
                raise HTTPException(
                    status_code=400,  # Bad Request, indicating violation
                    detail={
                        "error": "Violated Pangea guardrail policy",
                        "guardrail_name": self.guardrail_name,
                        "pangea_response": result.get("result"),
                    },
                )
            else:
                verbose_proxy_logger.info(
                    f"Pangea Guardrail ({hook_name}): Request passed. Response: {result.get('result', {}).get('detectors')}"
                )

            return result

        except HTTPException as e:
            # Re-raise HTTPException if it's the one we raised for blocking
            raise e
        except Exception as e:
            verbose_proxy_logger.error(
                f"Pangea Guardrail ({hook_name}): Error calling API: {e}. Response text: {getattr(e, 'response', None) and getattr(e.response, 'text', None)}"  # type: ignore
            )
            # Decide if you want to block by default on error, or allow through
            # Raising an exception here will block the request.
            # To allow through on error, you might just log and return.
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Error communicating with Pangea Guardrail",
                    "guardrail_name": self.guardrail_name,
                    "exception": str(e),
                },
            ) from e

    @log_guardrail_information
    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: str,
    ):
        event_type = GuardrailEventHooks.pre_call
        if self.should_run_guardrail(data=data, event_type=event_type) is not True:
            verbose_proxy_logger.debug(
                f"Pangea Guardrail (async_pre_call_hook): Guardrail is disabled {self.guardrail_name}."
            )
            return data

        transformer = _get_transformer_for_request(data, call_type)
        if not transformer:
            verbose_proxy_logger.warning(
                f"Pangea Guardrail (async_pre_call_hook): Skipping guardrail {self.guardrail_name}"
                f" because we cannot determine type of request: call_type '{call_type}'"
            )
            return

        messages = transformer.get_messages()
        if not messages:
            verbose_proxy_logger.warning(
                f"Pangea Guardrail (async_pre_call_hook): Skipping guardrail {self.guardrail_name}"
                " because messages is empty."
            )
            return

        ai_guard_payload = {
            "debug": False,  # Or make this configurable if needed
            "messages": messages,
        }
        if self.pangea_input_recipe:
            ai_guard_payload["recipe"] = self.pangea_input_recipe

        ai_guard_response = await self._call_pangea_guard(
            ai_guard_payload, "async_pre_call_hook"
        )
        # Add guardrail name to header if passed
        add_guardrail_to_applied_guardrails_header(
            request_data=data, guardrail_name=self.guardrail_name
        )
        prompt_messages = ai_guard_response.get("result", {}).get("prompt_messages", [])

        try:
            return transformer.update_original_body(prompt_messages)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Failed to update original request body",
                    "guardrail_name": self.guardrail_name,
                    "exceptions": str(e),
                },
            ) from e

    @log_guardrail_information
    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        # This union isn't actually correct -- it can get other response types depending on the API called
        response: LLMResponseTypes,
    ):
        """
        Guardrail hook run after a successful LLM call (scans output).

        Args:
            data (dict): The original request data.
            user_api_key_dict (UserAPIKeyAuth): User API key details.
            response (LLMResponseTypes): The response object from the LLM call.
        """
        event_type = GuardrailEventHooks.post_call
        if self.should_run_guardrail(data=data, event_type=event_type) is not True:
            verbose_proxy_logger.debug(
                f"Pangea Guardrail (async_pre_call_hook): Guardrail is disabled {self.guardrail_name}."
            )
            return data

        transformer = _get_transformer_for_response(response)
        if not transformer:
            verbose_proxy_logger.warning(
                f"Pangea Guardrail (async_post_call_success_hook): Skipping guardrail {self.guardrail_name}"
                " because we cannot determine type of request"
            )
            return

        messages = transformer.get_messages()
        verbose_proxy_logger.warning(f"GOT MESSAGES: {messages}")
        ai_guard_payload = {
            "debug": False,  # Or make this configurable if needed
            "messages": messages,
        }
        if self.pangea_output_recipe:
            ai_guard_payload["recipe"] = self.pangea_output_recipe

        ai_guard_response = await self._call_pangea_guard(
            ai_guard_payload, "post_call_success_hook"
        )
        prompt_messages = ai_guard_response.get("result", {}).get("prompt_messages", [])

        try:
            return transformer.update_original_body(prompt_messages)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Failed to update original response body",
                    "guardrail_name": self.guardrail_name,
                    "exceptions": str(e),
                },
            ) from e

# === NexusCore/openenv\Lib\site-packages\nltk\tag\perceptron.py ===
# This module is a port of the Textblob Averaged Perceptron Tagger
# Author: Matthew Honnibal <honnibal+gh@gmail.com>,
#         Long Duong <longdt219@gmail.com> (NLTK port)
# URL: <https://github.com/sloria/textblob-aptagger>
#      <https://www.nltk.org/>
# Copyright 2013 Matthew Honnibal
# NLTK modifications Copyright 2015 The NLTK Project
#
# This module is provided under the terms of the MIT License.

import json
import logging
import random
from collections import defaultdict

from nltk import jsontags
from nltk.data import find, load
from nltk.tag.api import TaggerI

try:
    import numpy as np
except ImportError:
    pass

TRAINED_TAGGER_PATH = "averaged_perceptron_tagger/"

TAGGER_JSONS = {
    "eng": {
        "weights": "averaged_perceptron_tagger_eng.weights.json",
        "tagdict": "averaged_perceptron_tagger_eng.tagdict.json",
        "classes": "averaged_perceptron_tagger_eng.classes.json",
    },
    "rus": {
        "weights": "averaged_perceptron_tagger_rus.weights.json",
        "tagdict": "averaged_perceptron_tagger_rus.tagdict.json",
        "classes": "averaged_perceptron_tagger_rus.classes.json",
    },
    "xxx": {
        "weights": "averaged_perceptron_tagger.xxx.weights.json",
        "tagdict": "averaged_perceptron_tagger.xxx.tagdict.json",
        "classes": "averaged_perceptron_tagger.xxx.classes.json",
    },
}


@jsontags.register_tag
class AveragedPerceptron:
    """An averaged perceptron, as implemented by Matthew Honnibal.

    See more implementation details here:
        https://explosion.ai/blog/part-of-speech-pos-tagger-in-python
    """

    json_tag = "nltk.tag.perceptron.AveragedPerceptron"

    def __init__(self, weights=None):
        # Each feature gets its own weight vector, so weights is a dict-of-dicts
        self.weights = weights if weights else {}
        self.classes = set()
        # The accumulated values, for the averaging. These will be keyed by
        # feature/clas tuples
        self._totals = defaultdict(int)
        # The last time the feature was changed, for the averaging. Also
        # keyed by feature/clas tuples
        # (tstamps is short for timestamps)
        self._tstamps = defaultdict(int)
        # Number of instances seen
        self.i = 0

    def _softmax(self, scores):
        s = np.fromiter(scores.values(), dtype=float)
        exps = np.exp(s)
        return exps / np.sum(exps)

    def predict(self, features, return_conf=False):
        """Dot-product the features and current weights and return the best label."""
        scores = defaultdict(float)
        for feat, value in features.items():
            if feat not in self.weights or value == 0:
                continue
            weights = self.weights[feat]
            for label, weight in weights.items():
                scores[label] += value * weight

        # Do a secondary alphabetic sort, for stability
        best_label = max(self.classes, key=lambda label: (scores[label], label))
        # compute the confidence
        conf = max(self._softmax(scores)) if return_conf == True else None

        return best_label, conf

    def update(self, truth, guess, features):
        """Update the feature weights."""

        def upd_feat(c, f, w, v):
            param = (f, c)
            self._totals[param] += (self.i - self._tstamps[param]) * w
            self._tstamps[param] = self.i
            self.weights[f][c] = w + v

        self.i += 1
        if truth == guess:
            return None
        for f in features:
            weights = self.weights.setdefault(f, {})
            upd_feat(truth, f, weights.get(truth, 0.0), 1.0)
            upd_feat(guess, f, weights.get(guess, 0.0), -1.0)

    def average_weights(self):
        """Average weights from all iterations."""
        for feat, weights in self.weights.items():
            new_feat_weights = {}
            for clas, weight in weights.items():
                param = (feat, clas)
                total = self._totals[param]
                total += (self.i - self._tstamps[param]) * weight
                averaged = round(total / self.i, 3)
                if averaged:
                    new_feat_weights[clas] = averaged
            self.weights[feat] = new_feat_weights

    def save(self, path):
        """Save the model weights as json"""
        with open(path, "w") as fout:
            return json.dump(self.weights, fout)

    def load(self, path):
        """Load the json model weights."""
        with open(path) as fin:
            self.weights = json.load(fin)

    def encode_json_obj(self):
        return self.weights

    @classmethod
    def decode_json_obj(cls, obj):
        return cls(obj)


@jsontags.register_tag
class PerceptronTagger(TaggerI):
    """
    Greedy Averaged Perceptron tagger, as implemented by Matthew Honnibal.
    See more implementation details here:
    https://explosion.ai/blog/part-of-speech-pos-tagger-in-python

    >>> from nltk.tag.perceptron import PerceptronTagger

    Train the model

    >>> tagger = PerceptronTagger(load=False)

    >>> tagger.train([[('today','NN'),('is','VBZ'),('good','JJ'),('day','NN')],
    ... [('yes','NNS'),('it','PRP'),('beautiful','JJ')]])

    >>> tagger.tag(['today','is','a','beautiful','day'])
    [('today', 'NN'), ('is', 'PRP'), ('a', 'PRP'), ('beautiful', 'JJ'), ('day', 'NN')]

    Use the pretrain model (the default constructor)

    >>> pretrain = PerceptronTagger()

    >>> pretrain.tag('The quick brown fox jumps over the lazy dog'.split())
    [('The', 'DT'), ('quick', 'JJ'), ('brown', 'NN'), ('fox', 'NN'), ('jumps', 'VBZ'), ('over', 'IN'), ('the', 'DT'), ('lazy', 'JJ'), ('dog', 'NN')]

    >>> pretrain.tag("The red cat".split())
    [('The', 'DT'), ('red', 'JJ'), ('cat', 'NN')]
    """

    json_tag = "nltk.tag.sequential.PerceptronTagger"

    START = ["-START-", "-START2-"]
    END = ["-END-", "-END2-"]

    def __init__(self, load=True, lang="eng"):
        """
        :param load: Load the json model upon instantiation.
        """
        self.model = AveragedPerceptron()
        self.tagdict = {}
        self.classes = set()
        if load:
            self.load_from_json(lang)

    def tag(self, tokens, return_conf=False, use_tagdict=True):
        """
        Tag tokenized sentences.
        :params tokens: list of word
        :type tokens: list(str)
        """
        prev, prev2 = self.START
        output = []

        context = self.START + [self.normalize(w) for w in tokens] + self.END
        for i, word in enumerate(tokens):
            tag, conf = (
                (self.tagdict.get(word), 1.0) if use_tagdict == True else (None, None)
            )
            if not tag:
                features = self._get_features(i, word, context, prev, prev2)
                tag, conf = self.model.predict(features, return_conf)
            output.append((word, tag, conf) if return_conf == True else (word, tag))

            prev2 = prev
            prev = tag

        return output

    def train(self, sentences, save_loc=None, nr_iter=5):
        """Train a model from sentences, and save it at ``save_loc``. ``nr_iter``
        controls the number of Perceptron training iterations.

        :param sentences: A list or iterator of sentences, where each sentence
            is a list of (words, tags) tuples.
        :param save_loc: If not ``None``, saves a json model in this location.
        :param nr_iter: Number of training iterations.
        """
        # We'd like to allow ``sentences`` to be either a list or an iterator,
        # the latter being especially important for a large training dataset.
        # Because ``self._make_tagdict(sentences)`` runs regardless, we make
        # it populate ``self._sentences`` (a list) with all the sentences.
        # This saves the overheard of just iterating through ``sentences`` to
        # get the list by ``sentences = list(sentences)``.

        self._sentences = list()  # to be populated by self._make_tagdict...
        self._make_tagdict(sentences)
        self.model.classes = self.classes
        for iter_ in range(nr_iter):
            c = 0
            n = 0
            for sentence in self._sentences:
                words, tags = zip(*sentence)

                prev, prev2 = self.START
                context = self.START + [self.normalize(w) for w in words] + self.END
                for i, word in enumerate(words):
                    guess = self.tagdict.get(word)
                    if not guess:
                        feats = self._get_features(i, word, context, prev, prev2)
                        guess, _ = self.model.predict(feats)
                        self.model.update(tags[i], guess, feats)
                    prev2 = prev
                    prev = guess
                    c += guess == tags[i]
                    n += 1
            random.shuffle(self._sentences)
            logging.info(f"Iter {iter_}: {c}/{n}={_pc(c, n)}")

        # We don't need the training sentences anymore, and we don't want to
        # waste space on them when we the trained tagger.
        self._sentences = None

        self.model.average_weights()
        # Save to json files.
        if save_loc is not None:
            self.save_to_json(loc)

    def save_to_json(self, loc, lang="xxx"):
        # TODO:
        assert os.isdir(
            TRAINED_TAGGER_PATH
        ), f"Path set for saving needs to be a directory"

        with open(loc + TAGGER_JSONS[lang]["weights"], "w") as fout:
            json.dump(self.model.weights, fout)
        with open(loc + TAGGER_JSONS[lang]["tagdict"], "w") as fout:
            json.dump(self.tagdict, fout)
        with open(loc + TAGGER_JSONS[lang]["classes"], "w") as fout:
            json.dump(self.classes, fout)

    def load_from_json(self, lang="eng"):
        # Automatically find path to the tagger if location is not specified.
        loc = find(f"taggers/averaged_perceptron_tagger_{lang}/")
        with open(loc + TAGGER_JSONS[lang]["weights"]) as fin:
            self.model.weights = json.load(fin)
        with open(loc + TAGGER_JSONS[lang]["tagdict"]) as fin:
            self.tagdict = json.load(fin)
        with open(loc + TAGGER_JSONS[lang]["classes"]) as fin:
            self.classes = set(json.load(fin))

        self.model.classes = self.classes

    def encode_json_obj(self):
        return self.model.weights, self.tagdict, list(self.classes)

    @classmethod
    def decode_json_obj(cls, obj):
        tagger = cls(load=False)
        tagger.model.weights, tagger.tagdict, tagger.classes = obj
        tagger.classes = set(tagger.classes)
        tagger.model.classes = tagger.classes
        return tagger

    def normalize(self, word):
        """
        Normalization used in pre-processing.
        - All words are lower cased
        - Groups of digits of length 4 are represented as !YEAR;
        - Other digits are represented as !DIGITS

        :rtype: str
        """
        if "-" in word and word[0] != "-":
            return "!HYPHEN"
        if word.isdigit() and len(word) == 4:
            return "!YEAR"
        if word and word[0].isdigit():
            return "!DIGITS"
        return word.lower()

    def _get_features(self, i, word, context, prev, prev2):
        """Map tokens into a feature representation, implemented as a
        {hashable: int} dict. If the features change, a new model must be
        trained.
        """

        def add(name, *args):
            features[" ".join((name,) + tuple(args))] += 1

        i += len(self.START)
        features = defaultdict(int)
        # It's useful to have a constant feature, which acts sort of like a prior
        add("bias")
        add("i suffix", word[-3:])
        add("i pref1", word[0] if word else "")
        add("i-1 tag", prev)
        add("i-2 tag", prev2)
        add("i tag+i-2 tag", prev, prev2)
        add("i word", context[i])
        add("i-1 tag+i word", prev, context[i])
        add("i-1 word", context[i - 1])
        add("i-1 suffix", context[i - 1][-3:])
        add("i-2 word", context[i - 2])
        add("i+1 word", context[i + 1])
        add("i+1 suffix", context[i + 1][-3:])
        add("i+2 word", context[i + 2])
        return features

    def _make_tagdict(self, sentences):
        """
        Make a tag dictionary for single-tag words.
        :param sentences: A list of list of (word, tag) tuples.
        """
        counts = defaultdict(lambda: defaultdict(int))
        for sentence in sentences:
            self._sentences.append(sentence)
            for word, tag in sentence:
                counts[word][tag] += 1
                self.classes.add(tag)
        freq_thresh = 20
        ambiguity_thresh = 0.97
        for word, tag_freqs in counts.items():
            tag, mode = max(tag_freqs.items(), key=lambda item: item[1])
            n = sum(tag_freqs.values())
            # Don't add rare words to the tag dictionary
            # Only add quite unambiguous words
            if n >= freq_thresh and (mode / n) >= ambiguity_thresh:
                self.tagdict[word] = tag


def _pc(n, d):
    return (n / d) * 100


def _load_data_conll_format(filename):
    print("Read from file: ", filename)
    with open(filename, "rb") as fin:
        sentences = []
        sentence = []
        for line in fin.readlines():
            line = line.strip()
            # print line
            if len(line) == 0:
                sentences.append(sentence)
                sentence = []
                continue
            tokens = line.split("\t")
            word = tokens[1]
            tag = tokens[4]
            sentence.append((word, tag))
        return sentences


def _get_pretrain_model():
    # Train and test on English part of ConLL data (WSJ part of Penn Treebank)
    # Train: section 2-11
    # Test : section 23
    tagger = PerceptronTagger()
    training = _load_data_conll_format("english_ptb_train.conll")
    testing = _load_data_conll_format("english_ptb_test.conll")
    print("Size of training and testing (sentence)", len(training), len(testing))
    # Train and save the model
    tagger.train(training, TRAINED_TAGGER_PATH)
    print("Accuracy : ", tagger.accuracy(testing))


if __name__ == "__main__":
    # _get_pretrain_model()
    pass