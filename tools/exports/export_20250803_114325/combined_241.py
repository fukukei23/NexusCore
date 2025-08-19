
# === NexusCore/openenv\Lib\site-packages\win32\Demos\eventLogDemo.py ===
import win32api  # To translate NT Sids to account names.
import win32con
import win32evtlog
import win32evtlogutil
import win32security


def ReadLog(computer, logType="Application", dumpEachRecord=0):
    # read the entire log back.
    h = win32evtlog.OpenEventLog(computer, logType)
    numRecords = win32evtlog.GetNumberOfEventLogRecords(h)
    # print(f"There are {numRecords} records")

    num = 0
    while 1:
        objects = win32evtlog.ReadEventLog(
            h,
            win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ,
            0,
        )
        if not objects:
            break
        for object in objects:
            # get it for testing purposes, but don't print it.
            msg = win32evtlogutil.SafeFormatMessage(object, logType)
            if object.Sid is not None:
                try:
                    domain, user, typ = win32security.LookupAccountSid(
                        computer, object.Sid
                    )
                    sidDesc = f"{domain}/{user}"
                except win32security.error:
                    sidDesc = str(object.Sid)
                user_desc = f"Event associated with user {sidDesc}"
            else:
                user_desc = None
            if dumpEachRecord:
                print(
                    "Event record from {!r} generated at {}".format(
                        object.SourceName, object.TimeGenerated.Format()
                    )
                )
                if user_desc:
                    print(user_desc)
                try:
                    print(msg)
                except UnicodeError:
                    print("(unicode error printing message: repr() follows...)")
                    print(repr(msg))

        num += len(objects)

    if numRecords == num:
        print("Successfully read all", numRecords, "records")
    else:
        print(
            "Couldn't get all records - reported %d, but found %d" % (numRecords, num)
        )
        print(
            "(Note that some other app may have written records while we were running!)"
        )
    win32evtlog.CloseEventLog(h)


def usage():
    print("Writes an event to the event log.")
    print("-w : Don't write any test records.")
    print("-r : Don't read the event log")
    print("-c : computerName : Process the log on the specified computer")
    print("-v : Verbose")
    print("-t : LogType - Use the specified log - default = 'Application'")


def test():
    # check if running on Windows NT, if not, display notice and terminate
    if win32api.GetVersion() & 0x80000000:
        print("This sample only runs on NT")
        return

    import getopt
    import sys

    opts, args = getopt.getopt(sys.argv[1:], "rwh?c:t:v")
    computer = None
    do_read = do_write = 1

    logType = "Application"
    verbose = 0

    if len(args) > 0:
        print("Invalid args")
        usage()
        return 1
    for opt, val in opts:
        if opt == "-t":
            logType = val
        if opt == "-c":
            computer = val
        if opt in ["-h", "-?"]:
            usage()
            return
        if opt == "-r":
            do_read = 0
        if opt == "-w":
            do_write = 0
        if opt == "-v":
            verbose += 1
    if do_write:
        ph = win32api.GetCurrentProcess()
        th = win32security.OpenProcessToken(ph, win32con.TOKEN_READ)
        my_sid = win32security.GetTokenInformation(th, win32security.TokenUser)[0]

        win32evtlogutil.ReportEvent(
            logType,
            2,
            strings=["The message text for event 2", "Another insert"],
            data=b"Raw\0Data",
            sid=my_sid,
        )
        win32evtlogutil.ReportEvent(
            logType,
            1,
            eventType=win32evtlog.EVENTLOG_WARNING_TYPE,
            strings=["A warning", "An even more dire warning"],
            data=b"Raw\0Data",
            sid=my_sid,
        )
        win32evtlogutil.ReportEvent(
            logType,
            1,
            eventType=win32evtlog.EVENTLOG_INFORMATION_TYPE,
            strings=["An info", "Too much info"],
            data=b"Raw\0Data",
            sid=my_sid,
        )
        print("Successfully wrote 3 records to the log")

    if do_read:
        ReadLog(computer, logType, verbose > 0)


if __name__ == "__main__":
    test()

# === NexusCore/openenv\Lib\site-packages\win32comext\shell\demos\explorer_browser.py ===
# A sample of using Vista's IExplorerBrowser interfaces...
# Currently doesn't quite work:
# * CPU sits at 100% while running.

import sys

import pythoncom
import win32api
import win32con
import win32gui
from win32com.server.util import unwrap, wrap
from win32com.shell import shell, shellcon

# event handler for the browser.
IExplorerBrowserEvents_Methods = """OnNavigationComplete OnNavigationFailed
                                    OnNavigationPending OnViewCreated""".split()


class EventHandler:
    _com_interfaces_ = [shell.IID_IExplorerBrowserEvents]
    _public_methods_ = IExplorerBrowserEvents_Methods

    def OnNavigationComplete(self, pidl):
        print("OnNavComplete", pidl)

    def OnNavigationFailed(self, pidl):
        print("OnNavigationFailed", pidl)

    def OnNavigationPending(self, pidl):
        print("OnNavigationPending", pidl)

    def OnViewCreated(self, view):
        print("OnViewCreated", view)
        # And if our demo view has been registered, it may well
        # be that view!
        try:
            pyview = unwrap(view)
            print("and look - it's a Python implemented view!", pyview)
        except ValueError:
            pass


class MainWindow:
    def __init__(self):
        message_map = {
            win32con.WM_DESTROY: self.OnDestroy,
            win32con.WM_COMMAND: self.OnCommand,
            win32con.WM_SIZE: self.OnSize,
        }
        # Register the Window class.
        wc = win32gui.WNDCLASS()
        hinst = wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "test_explorer_browser"
        wc.lpfnWndProc = message_map  # could also specify a wndproc.
        classAtom = win32gui.RegisterClass(wc)
        # Create the Window.
        style = win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE
        self.hwnd = win32gui.CreateWindow(
            classAtom,
            "Python IExplorerBrowser demo",
            style,
            0,
            0,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            0,
            0,
            hinst,
            None,
        )
        eb = pythoncom.CoCreateInstance(
            shellcon.CLSID_ExplorerBrowser,
            None,
            pythoncom.CLSCTX_ALL,
            shell.IID_IExplorerBrowser,
        )
        # as per MSDN docs, hook up events early
        self.event_cookie = eb.Advise(wrap(EventHandler()))

        eb.SetOptions(shellcon.EBO_SHOWFRAMES)
        rect = win32gui.GetClientRect(self.hwnd)
        # Set the flags such that the folders autoarrange and non web view is presented
        flags = (shellcon.FVM_LIST, shellcon.FWF_AUTOARRANGE | shellcon.FWF_NOWEBVIEW)
        eb.Initialize(self.hwnd, rect, (0, shellcon.FVM_DETAILS))
        if len(sys.argv) == 2:
            # If an arg was specified, ask the desktop parse it.
            # You can pass anything explorer accepts as its '/e' argument -
            # eg, "::{guid}\::{guid}" etc.
            # "::{20D04FE0-3AEA-1069-A2D8-08002B30309D}" is "My Computer"
            pidl = shell.SHGetDesktopFolder().ParseDisplayName(0, None, sys.argv[1])[1]
        else:
            # And start browsing at the root of the namespace.
            pidl = []
        eb.BrowseToIDList(pidl, shellcon.SBSP_ABSOLUTE)
        # and for some reason the "Folder" view in the navigator pane doesn't
        # magically synchronize itself - so let's do that ourself.
        # Get the tree control.
        sp = eb.QueryInterface(pythoncom.IID_IServiceProvider)
        try:
            tree = sp.QueryService(
                shell.IID_INameSpaceTreeControl, shell.IID_INameSpaceTreeControl
            )
        except pythoncom.com_error as exc:
            # this should really only fail if no "nav" frame exists...
            print(
                "Strange - failed to get the tree control even though "
                "we asked for a EBO_SHOWFRAMES"
            )
            print(exc)
        else:
            # get the IShellItem for the selection.
            si = shell.SHCreateItemFromIDList(pidl, shell.IID_IShellItem)
            # set it to selected.
            tree.SetItemState(si, shellcon.NSTCIS_SELECTED, shellcon.NSTCIS_SELECTED)

        # eb.FillFromObject(None, shellcon.EBF_NODROPTARGET);
        # eb.SetEmptyText("No known folders yet...");
        self.eb = eb

    def OnCommand(self, hwnd, msg, wparam, lparam):
        pass

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        print("tearing down ExplorerBrowser...")
        self.eb.Unadvise(self.event_cookie)
        self.eb.Destroy()
        self.eb = None
        print("shutting down app...")
        win32gui.PostQuitMessage(0)

    def OnSize(self, hwnd, msg, wparam, lparam):
        x = win32api.LOWORD(lparam)
        y = win32api.HIWORD(lparam)
        self.eb.SetRect(None, (0, 0, x, y))


def main():
    w = MainWindow()
    win32gui.PumpMessages()


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc3161.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Time-Stamp Protocol (TSP)
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc3161.txt
#

from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc4210
from pyasn1_modules import rfc5280
from pyasn1_modules import rfc5652


Extensions = rfc5280.Extensions

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier

GeneralName = rfc5280.GeneralName

ContentInfo = rfc5652.ContentInfo

PKIFreeText = rfc4210.PKIFreeText


id_ct_TSTInfo = univ.ObjectIdentifier('1.2.840.113549.1.9.16.1.4')


class Accuracy(univ.Sequence):
    pass

Accuracy.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('seconds', univ.Integer()),
    namedtype.OptionalNamedType('millis', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(1, 999)).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('micros', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(1, 999)).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class MessageImprint(univ.Sequence):
    pass

MessageImprint.componentType = namedtype.NamedTypes(
    namedtype.NamedType('hashAlgorithm', AlgorithmIdentifier()),
    namedtype.NamedType('hashedMessage', univ.OctetString())
)


class PKIFailureInfo(univ.BitString):
    pass

PKIFailureInfo.namedValues = namedval.NamedValues(
    ('badAlg', 0),
    ('badRequest', 2),
    ('badDataFormat', 5),
    ('timeNotAvailable', 14),
    ('unacceptedPolicy', 15),
    ('unacceptedExtension', 16),
    ('addInfoNotAvailable', 17),
    ('systemFailure', 25)
)


class PKIStatus(univ.Integer):
    pass

PKIStatus.namedValues = namedval.NamedValues(
    ('granted', 0),
    ('grantedWithMods', 1),
    ('rejection', 2),
    ('waiting', 3),
    ('revocationWarning', 4),
    ('revocationNotification', 5)
)


class PKIStatusInfo(univ.Sequence):
    pass

PKIStatusInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('status', PKIStatus()),
    namedtype.OptionalNamedType('statusString', PKIFreeText()),
    namedtype.OptionalNamedType('failInfo', PKIFailureInfo())
)


class TSAPolicyId(univ.ObjectIdentifier):
    pass


class TSTInfo(univ.Sequence):
    pass

TSTInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', univ.Integer(namedValues=namedval.NamedValues(('v1', 1)))),
    namedtype.NamedType('policy', TSAPolicyId()),
    namedtype.NamedType('messageImprint', MessageImprint()),
    namedtype.NamedType('serialNumber', univ.Integer()),
    namedtype.NamedType('genTime', useful.GeneralizedTime()),
    namedtype.OptionalNamedType('accuracy', Accuracy()),
    namedtype.DefaultedNamedType('ordering', univ.Boolean().subtype(value=0)),
    namedtype.OptionalNamedType('nonce', univ.Integer()),
    namedtype.OptionalNamedType('tsa', GeneralName().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('extensions', Extensions().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class TimeStampReq(univ.Sequence):
    pass

TimeStampReq.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', univ.Integer(namedValues=namedval.NamedValues(('v1', 1)))),
    namedtype.NamedType('messageImprint', MessageImprint()),
    namedtype.OptionalNamedType('reqPolicy', TSAPolicyId()),
    namedtype.OptionalNamedType('nonce', univ.Integer()),
    namedtype.DefaultedNamedType('certReq', univ.Boolean().subtype(value=0)),
    namedtype.OptionalNamedType('extensions', Extensions().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class TimeStampToken(ContentInfo):
    pass


class TimeStampResp(univ.Sequence):
    pass

TimeStampResp.componentType = namedtype.NamedTypes(
    namedtype.NamedType('status', PKIStatusInfo()),
    namedtype.OptionalNamedType('timeStampToken', TimeStampToken())
)

# === NexusCore/openenv\Lib\site-packages\win32com\storagecon.py ===
"""Constants related to IStorage and related interfaces

This file was generated by h2py from d:\\msdev\\include\\objbase.h
then hand edited, a few extra constants added, etc.
"""

STGC_DEFAULT = 0
STGC_OVERWRITE = 1
STGC_ONLYIFCURRENT = 2
STGC_DANGEROUSLYCOMMITMERELYTODISKCACHE = 4
STGC_CONSOLIDATE = 8

STGTY_STORAGE = 1
STGTY_STREAM = 2
STGTY_LOCKBYTES = 3
STGTY_PROPERTY = 4
STREAM_SEEK_SET = 0
STREAM_SEEK_CUR = 1
STREAM_SEEK_END = 2

LOCK_WRITE = 1
LOCK_EXCLUSIVE = 2
LOCK_ONLYONCE = 4

# Generated as from here.

CWCSTORAGENAME = 32
STGM_DIRECT = 0x00000000
STGM_TRANSACTED = 0x00010000
STGM_SIMPLE = 0x08000000
STGM_READ = 0x00000000
STGM_WRITE = 0x00000001
STGM_READWRITE = 0x00000002
STGM_SHARE_DENY_NONE = 0x00000040
STGM_SHARE_DENY_READ = 0x00000030
STGM_SHARE_DENY_WRITE = 0x00000020
STGM_SHARE_EXCLUSIVE = 0x00000010
STGM_PRIORITY = 0x00040000
STGM_DELETEONRELEASE = 0x04000000
STGM_NOSCRATCH = 0x00100000
STGM_CREATE = 0x00001000
STGM_CONVERT = 0x00020000
STGM_FAILIFTHERE = 0x00000000
STGM_NOSNAPSHOT = 0x00200000
ASYNC_MODE_COMPATIBILITY = 0x00000001
ASYNC_MODE_DEFAULT = 0x00000000
STGTY_REPEAT = 0x00000100
STG_TOEND = 0xFFFFFFFF
STG_LAYOUT_SEQUENTIAL = 0x00000000
STG_LAYOUT_INTERLEAVED = 0x00000001

## access rights used with COM server ACL's
COM_RIGHTS_EXECUTE = 1
COM_RIGHTS_EXECUTE_LOCAL = 2
COM_RIGHTS_EXECUTE_REMOTE = 4
COM_RIGHTS_ACTIVATE_LOCAL = 8
COM_RIGHTS_ACTIVATE_REMOTE = 16

STGFMT_DOCUMENT = 0
STGFMT_STORAGE = 0
STGFMT_NATIVE = 1
STGFMT_FILE = 3
STGFMT_ANY = 4
STGFMT_DOCFILE = 5

PID_DICTIONARY = 0
PID_CODEPAGE = 1
PID_FIRST_USABLE = 2
PID_FIRST_NAME_DEFAULT = 4095

PID_LOCALE = -2147483648
PID_MODIFY_TIME = -2147483647
PID_SECURITY = -2147483646
PID_BEHAVIOR = -2147483645
PID_ILLEGAL = -1
PID_MIN_READONLY = -2147483648
PID_MAX_READONLY = -1073741825

## DiscardableInformation
PIDDI_THUMBNAIL = 0x00000002

## SummaryInformation
PIDSI_TITLE = 2
PIDSI_SUBJECT = 3
PIDSI_AUTHOR = 4
PIDSI_KEYWORDS = 5
PIDSI_COMMENTS = 6
PIDSI_TEMPLATE = 7
PIDSI_LASTAUTHOR = 8
PIDSI_REVNUMBER = 9
PIDSI_EDITTIME = 10
PIDSI_LASTPRINTED = 11
PIDSI_CREATE_DTM = 12
PIDSI_LASTSAVE_DTM = 13
PIDSI_PAGECOUNT = 14
PIDSI_WORDCOUNT = 15
PIDSI_CHARCOUNT = 16
PIDSI_THUMBNAIL = 17
PIDSI_APPNAME = 18
PIDSI_DOC_SECURITY = 19

## DocSummaryInformation
PIDDSI_CATEGORY = 2
PIDDSI_PRESFORMAT = 3
PIDDSI_BYTECOUNT = 4
PIDDSI_LINECOUNT = 5
PIDDSI_PARCOUNT = 6
PIDDSI_SLIDECOUNT = 7
PIDDSI_NOTECOUNT = 8
PIDDSI_HIDDENCOUNT = 9
PIDDSI_MMCLIPCOUNT = 10
PIDDSI_SCALE = 11
PIDDSI_HEADINGPAIR = 12
PIDDSI_DOCPARTS = 13
PIDDSI_MANAGER = 14
PIDDSI_COMPANY = 15
PIDDSI_LINKSDIRTY = 16


## MediaFileSummaryInfo
PIDMSI_EDITOR = 2
PIDMSI_SUPPLIER = 3
PIDMSI_SOURCE = 4
PIDMSI_SEQUENCE_NO = 5
PIDMSI_PROJECT = 6
PIDMSI_STATUS = 7
PIDMSI_OWNER = 8
PIDMSI_RATING = 9
PIDMSI_PRODUCTION = 10
PIDMSI_COPYRIGHT = 11

## PROPSETFLAG enum
PROPSETFLAG_DEFAULT = 0
PROPSETFLAG_NONSIMPLE = 1
PROPSETFLAG_ANSI = 2
PROPSETFLAG_UNBUFFERED = 4
PROPSETFLAG_CASE_SENSITIVE = 8

## STGMOVE enum
STGMOVE_MOVE = 0
STGMOVE_COPY = 1
STGMOVE_SHALLOWCOPY = 2

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\visitor.py ===
"""Generic visitor pattern implementation for Python objects."""

import enum


class Visitor(object):
    defaultStop = False

    @classmethod
    def _register(celf, clazzes_attrs):
        assert celf != Visitor, "Subclass Visitor instead."
        if "_visitors" not in celf.__dict__:
            celf._visitors = {}

        def wrapper(method):
            assert method.__name__ == "visit"
            for clazzes, attrs in clazzes_attrs:
                if type(clazzes) != tuple:
                    clazzes = (clazzes,)
                if type(attrs) == str:
                    attrs = (attrs,)
                for clazz in clazzes:
                    _visitors = celf._visitors.setdefault(clazz, {})
                    for attr in attrs:
                        assert attr not in _visitors, (
                            "Oops, class '%s' has visitor function for '%s' defined already."
                            % (clazz.__name__, attr)
                        )
                        _visitors[attr] = method
            return None

        return wrapper

    @classmethod
    def register(celf, clazzes):
        if type(clazzes) != tuple:
            clazzes = (clazzes,)
        return celf._register([(clazzes, (None,))])

    @classmethod
    def register_attr(celf, clazzes, attrs):
        clazzes_attrs = []
        if type(clazzes) != tuple:
            clazzes = (clazzes,)
        if type(attrs) == str:
            attrs = (attrs,)
        for clazz in clazzes:
            clazzes_attrs.append((clazz, attrs))
        return celf._register(clazzes_attrs)

    @classmethod
    def register_attrs(celf, clazzes_attrs):
        return celf._register(clazzes_attrs)

    @classmethod
    def _visitorsFor(celf, thing, _default={}):
        typ = type(thing)

        for celf in celf.mro():
            _visitors = getattr(celf, "_visitors", None)
            if _visitors is None:
                break

            for base in typ.mro():
                m = celf._visitors.get(base, None)
                if m is not None:
                    return m

        return _default

    def visitObject(self, obj, *args, **kwargs):
        """Called to visit an object. This function loops over all non-private
        attributes of the objects and calls any user-registered (via
        @register_attr() or @register_attrs()) visit() functions.

        If there is no user-registered visit function, of if there is and it
        returns True, or it returns None (or doesn't return anything) and
        visitor.defaultStop is False (default), then the visitor will proceed
        to call self.visitAttr()"""

        keys = sorted(vars(obj).keys())
        _visitors = self._visitorsFor(obj)
        defaultVisitor = _visitors.get("*", None)
        for key in keys:
            if key[0] == "_":
                continue
            value = getattr(obj, key)
            visitorFunc = _visitors.get(key, defaultVisitor)
            if visitorFunc is not None:
                ret = visitorFunc(self, obj, key, value, *args, **kwargs)
                if ret == False or (ret is None and self.defaultStop):
                    continue
            self.visitAttr(obj, key, value, *args, **kwargs)

    def visitAttr(self, obj, attr, value, *args, **kwargs):
        """Called to visit an attribute of an object."""
        self.visit(value, *args, **kwargs)

    def visitList(self, obj, *args, **kwargs):
        """Called to visit any value that is a list."""
        for value in obj:
            self.visit(value, *args, **kwargs)

    def visitDict(self, obj, *args, **kwargs):
        """Called to visit any value that is a dictionary."""
        for value in obj.values():
            self.visit(value, *args, **kwargs)

    def visitLeaf(self, obj, *args, **kwargs):
        """Called to visit any value that is not an object, list,
        or dictionary."""
        pass

    def visit(self, obj, *args, **kwargs):
        """This is the main entry to the visitor. The visitor will visit object
        obj.

        The visitor will first determine if there is a registered (via
        @register()) visit function for the type of object. If there is, it
        will be called, and (visitor, obj, *args, **kwargs) will be passed to
        the user visit function.

        If there is no user-registered visit function, of if there is and it
        returns True, or it returns None (or doesn't return anything) and
        visitor.defaultStop is False (default), then the visitor will proceed
        to dispatch to one of self.visitObject(), self.visitList(),
        self.visitDict(), or self.visitLeaf() (any of which can be overriden in
        a subclass)."""

        visitorFunc = self._visitorsFor(obj).get(None, None)
        if visitorFunc is not None:
            ret = visitorFunc(self, obj, *args, **kwargs)
            if ret == False or (ret is None and self.defaultStop):
                return
        if hasattr(obj, "__dict__") and not isinstance(obj, enum.Enum):
            self.visitObject(obj, *args, **kwargs)
        elif isinstance(obj, list):
            self.visitList(obj, *args, **kwargs)
        elif isinstance(obj, dict):
            self.visitDict(obj, *args, **kwargs)
        else:
            self.visitLeaf(obj, *args, **kwargs)

# === NexusCore/openenv\Lib\site-packages\litellm\images\utils.py ===
from io import BufferedReader, BytesIO
from typing import Any, Dict, cast, get_type_hints

import litellm
from litellm.litellm_core_utils.token_counter import get_image_type
from litellm.llms.base_llm.image_edit.transformation import BaseImageEditConfig
from litellm.types.files import FILE_MIME_TYPES, FileType
from litellm.types.images.main import ImageEditOptionalRequestParams


class ImageEditRequestUtils:
    @staticmethod
    def get_optional_params_image_edit(
        model: str,
        image_edit_provider_config: BaseImageEditConfig,
        image_edit_optional_params: ImageEditOptionalRequestParams,
    ) -> Dict:
        """
        Get optional parameters for the image edit API.

        Args:
            params: Dictionary of all parameters
            model: The model name
            image_edit_provider_config: The provider configuration for image edit API

        Returns:
            A dictionary of supported parameters for the image edit API
        """
        # Remove None values and internal parameters

        # Get supported parameters for the model
        supported_params = image_edit_provider_config.get_supported_openai_params(model)

        # Check for unsupported parameters
        unsupported_params = [
            param
            for param in image_edit_optional_params
            if param not in supported_params
        ]

        if unsupported_params:
            raise litellm.UnsupportedParamsError(
                model=model,
                message=f"The following parameters are not supported for model {model}: {', '.join(unsupported_params)}",
            )

        # Map parameters to provider-specific format
        mapped_params = image_edit_provider_config.map_openai_params(
            image_edit_optional_params=image_edit_optional_params,
            model=model,
            drop_params=litellm.drop_params,
        )

        return mapped_params

    @staticmethod
    def get_requested_image_edit_optional_param(
        params: Dict[str, Any],
    ) -> ImageEditOptionalRequestParams:
        """
        Filter parameters to only include those defined in ImageEditOptionalRequestParams.

        Args:
            params: Dictionary of parameters to filter

        Returns:
            ImageEditOptionalRequestParams instance with only the valid parameters
        """
        valid_keys = get_type_hints(ImageEditOptionalRequestParams).keys()
        filtered_params = {
            k: v for k, v in params.items() if k in valid_keys and v is not None
        }

        return cast(ImageEditOptionalRequestParams, filtered_params)

    @staticmethod
    def get_image_content_type(image_data: Any) -> str:
        """
        Detect the content type of image data using existing LiteLLM utils.

        Args:
            image_data: Can be BytesIO, bytes, BufferedReader, or other file-like objects

        Returns:
            The MIME type string (e.g., "image/png", "image/jpeg")
        """
        try:
            # Extract bytes for content type detection
            if isinstance(image_data, BytesIO):
                # Save current position
                current_pos = image_data.tell()
                image_data.seek(0)
                bytes_data = image_data.read(
                    100
                )  # First 100 bytes are enough for detection
                # Restore position
                image_data.seek(current_pos)
            elif isinstance(image_data, BufferedReader):
                # Save current position
                current_pos = image_data.tell()
                image_data.seek(0)
                bytes_data = image_data.read(100)
                # Restore position
                image_data.seek(current_pos)
            elif isinstance(image_data, bytes):
                bytes_data = image_data[:100]
            else:
                # For other types, try to read if possible
                if hasattr(image_data, "read"):
                    current_pos = getattr(image_data, "tell", lambda: 0)()
                    if hasattr(image_data, "seek"):
                        image_data.seek(0)
                    bytes_data = image_data.read(100)
                    if hasattr(image_data, "seek"):
                        image_data.seek(current_pos)
                else:
                    return FILE_MIME_TYPES[FileType.PNG]  # Default fallback

            # Use the existing get_image_type function to detect image type
            image_type_str = get_image_type(bytes_data)

            if image_type_str is None:
                return FILE_MIME_TYPES[FileType.PNG]  # Default if detection fails

            # Map detected type string to FileType enum and get MIME type
            type_mapping = {
                "png": FileType.PNG,
                "jpeg": FileType.JPEG,
                "gif": FileType.GIF,
                "webp": FileType.WEBP,
                "heic": FileType.HEIC,
            }

            file_type = type_mapping.get(image_type_str)
            if file_type is None:
                return FILE_MIME_TYPES[FileType.PNG]  # Default to PNG if unknown

            return FILE_MIME_TYPES[file_type]

        except Exception:
            # If anything goes wrong, default to PNG
            return FILE_MIME_TYPES[FileType.PNG]

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\db\log_db_metrics.py ===
"""
Handles logging DB success/failure to ServiceLogger()

ServiceLogger() then sends DB logs to Prometheus, OTEL, Datadog etc
"""

import asyncio
from datetime import datetime
from functools import wraps
from typing import Callable, Dict, Tuple

from litellm._service_logger import ServiceTypes
from litellm.litellm_core_utils.core_helpers import (
    _get_parent_otel_span_from_kwargs,
    get_litellm_metadata_from_kwargs,
)


def log_db_metrics(func):
    """
    Decorator to log the duration of a DB related function to ServiceLogger()

    Handles logging DB success/failure to ServiceLogger(), which logs to Prometheus, OTEL, Datadog

    When logging Failure it checks if the Exception is a PrismaError, httpx.ConnectError or httpx.TimeoutException and then logs that as a DB Service Failure

    Args:
        func: The function to be decorated

    Returns:
        Result from the decorated function

    Raises:
        Exception: If the decorated function raises an exception
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time: datetime = datetime.now()

        try:
            result = await func(*args, **kwargs)
            end_time: datetime = datetime.now()
            from litellm.proxy.proxy_server import proxy_logging_obj

            if "PROXY" not in func.__name__:
                asyncio.create_task(
                    proxy_logging_obj.service_logging_obj.async_service_success_hook(
                        service=ServiceTypes.DB,
                        call_type=func.__name__,
                        parent_otel_span=kwargs.get("parent_otel_span", None),
                        duration=(end_time - start_time).total_seconds(),
                        start_time=start_time,
                        end_time=end_time,
                        event_metadata={
                            "function_name": func.__name__,
                            "function_kwargs": kwargs,
                            "function_args": args,
                        },
                    )
                )
            elif (
                # in litellm custom callbacks kwargs is passed as arg[0]
                # https://docs.litellm.ai/docs/observability/custom_callback#callback-functions
                args is not None
                and len(args) > 1
                and isinstance(args[1], dict)
            ):
                passed_kwargs = args[1]
                parent_otel_span = _get_parent_otel_span_from_kwargs(
                    kwargs=passed_kwargs
                )
                if parent_otel_span is not None:
                    metadata = get_litellm_metadata_from_kwargs(kwargs=passed_kwargs)

                    asyncio.create_task(
                        proxy_logging_obj.service_logging_obj.async_service_success_hook(
                            service=ServiceTypes.BATCH_WRITE_TO_DB,
                            call_type=func.__name__,
                            parent_otel_span=parent_otel_span,
                            duration=0.0,
                            start_time=start_time,
                            end_time=end_time,
                            event_metadata=metadata,
                        )
                    )
            # end of logging to otel
            return result
        except Exception as e:
            end_time: datetime = datetime.now()
            await _handle_logging_db_exception(
                e=e,
                func=func,
                kwargs=kwargs,
                args=args,
                start_time=start_time,
                end_time=end_time,
            )
            raise e

    return wrapper


def _is_exception_related_to_db(e: Exception) -> bool:
    """
    Returns True if the exception is related to the DB
    """

    import httpx
    from prisma.errors import PrismaError

    return isinstance(e, (PrismaError, httpx.ConnectError, httpx.TimeoutException))


async def _handle_logging_db_exception(
    e: Exception,
    func: Callable,
    kwargs: Dict,
    args: Tuple,
    start_time: datetime,
    end_time: datetime,
) -> None:
    from litellm.proxy.proxy_server import proxy_logging_obj

    # don't log this as a DB Service Failure, if the DB did not raise an exception
    if _is_exception_related_to_db(e) is not True:
        return

    await proxy_logging_obj.service_logging_obj.async_service_failure_hook(
        error=e,
        service=ServiceTypes.DB,
        call_type=func.__name__,
        parent_otel_span=kwargs.get("parent_otel_span"),
        duration=(end_time - start_time).total_seconds(),
        start_time=start_time,
        end_time=end_time,
        event_metadata={
            "function_name": func.__name__,
            "function_kwargs": kwargs,
            "function_args": args,
        },
    )

# === NexusCore/openenv\Lib\site-packages\nltk\tag\hunpos.py ===
# Natural Language Toolkit: Interface to the HunPos POS-tagger
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
#         Dávid Márk Nemeskey <nemeskeyd@gmail.com> (modifications)
#         Attila Zséder <zseder@gmail.com> (modifications)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for interfacing with the HunPos open-source POS-tagger.
"""

import os
from subprocess import PIPE, Popen

from nltk.internals import find_binary, find_file
from nltk.tag.api import TaggerI

_hunpos_url = "https://code.google.com/p/hunpos/"

_hunpos_charset = "ISO-8859-1"
"""The default encoding used by hunpos: ISO-8859-1."""


class HunposTagger(TaggerI):
    """
    A class for pos tagging with HunPos. The input is the paths to:
     - a model trained on training data
     - (optionally) the path to the hunpos-tag binary
     - (optionally) the encoding of the training data (default: ISO-8859-1)

    Check whether the required "hunpos-tag" binary is available:

        >>> from nltk.test.setup_fixt import check_binary
        >>> check_binary('hunpos-tag')

    Example:
        >>> from nltk.tag import HunposTagger
        >>> ht = HunposTagger('en_wsj.model')
        >>> ht.tag('What is the airspeed of an unladen swallow ?'.split())
        [('What', 'WP'), ('is', 'VBZ'), ('the', 'DT'), ('airspeed', 'NN'), ('of', 'IN'), ('an', 'DT'), ('unladen', 'NN'), ('swallow', 'VB'), ('?', '.')]
        >>> ht.close()

    This class communicates with the hunpos-tag binary via pipes. When the
    tagger object is no longer needed, the close() method should be called to
    free system resources. The class supports the context manager interface; if
    used in a with statement, the close() method is invoked automatically:

        >>> with HunposTagger('en_wsj.model') as ht:
        ...     ht.tag('What is the airspeed of an unladen swallow ?'.split())
        ...
        [('What', 'WP'), ('is', 'VBZ'), ('the', 'DT'), ('airspeed', 'NN'), ('of', 'IN'), ('an', 'DT'), ('unladen', 'NN'), ('swallow', 'VB'), ('?', '.')]
    """

    def __init__(
        self, path_to_model, path_to_bin=None, encoding=_hunpos_charset, verbose=False
    ):
        """
        Starts the hunpos-tag executable and establishes a connection with it.

        :param path_to_model: The model file.
        :param path_to_bin: The hunpos-tag binary.
        :param encoding: The encoding used by the model. Unicode tokens
            passed to the tag() and tag_sents() methods are converted to
            this charset when they are sent to hunpos-tag.
            The default is ISO-8859-1 (Latin-1).

            This parameter is ignored for str tokens, which are sent as-is.
            The caller must ensure that tokens are encoded in the right charset.
        """
        self._closed = True
        hunpos_paths = [
            ".",
            "/usr/bin",
            "/usr/local/bin",
            "/opt/local/bin",
            "/Applications/bin",
            "~/bin",
            "~/Applications/bin",
        ]
        hunpos_paths = list(map(os.path.expanduser, hunpos_paths))

        self._hunpos_bin = find_binary(
            "hunpos-tag",
            path_to_bin,
            env_vars=("HUNPOS_TAGGER",),
            searchpath=hunpos_paths,
            url=_hunpos_url,
            verbose=verbose,
        )

        self._hunpos_model = find_file(
            path_to_model, env_vars=("HUNPOS_TAGGER",), verbose=verbose
        )
        self._encoding = encoding
        self._hunpos = Popen(
            [self._hunpos_bin, self._hunpos_model],
            shell=False,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )
        self._closed = False

    def __del__(self):
        self.close()

    def close(self):
        """Closes the pipe to the hunpos executable."""
        if not self._closed:
            self._hunpos.communicate()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def tag(self, tokens):
        """Tags a single sentence: a list of words.
        The tokens should not contain any newline characters.
        """
        for token in tokens:
            assert "\n" not in token, "Tokens should not contain newlines"
            if isinstance(token, str):
                token = token.encode(self._encoding)
            self._hunpos.stdin.write(token + b"\n")
        # We write a final empty line to tell hunpos that the sentence is finished:
        self._hunpos.stdin.write(b"\n")
        self._hunpos.stdin.flush()

        tagged_tokens = []
        for token in tokens:
            tagged = self._hunpos.stdout.readline().strip().split(b"\t")
            tag = tagged[1] if len(tagged) > 1 else None
            tagged_tokens.append((token, tag))
        # We have to read (and dismiss) the final empty line:
        self._hunpos.stdout.readline()

        return tagged_tokens

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_impl_to_api_mapping.py ===
# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import inspect
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from playwright._impl._errors import Error
from playwright._impl._map import Map

API_ATTR = "_pw_api_instance_"
IMPL_ATTR = "_pw_impl_instance_"


class ImplWrapper:
    def __init__(self, impl_obj: Any) -> None:
        self._impl_obj = impl_obj

    def __repr__(self) -> str:
        return self._impl_obj.__repr__()


class ImplToApiMapping:
    def __init__(self) -> None:
        self._mapping: Dict[type, type] = {}

    def register(self, impl_class: type, api_class: type) -> None:
        self._mapping[impl_class] = api_class

    def from_maybe_impl(
        self, obj: Any, visited: Optional[Map[Any, Union[List, Dict]]] = None
    ) -> Any:
        # Python does share default arguments between calls, so we need to
        # create a new map if it is not provided.
        if not visited:
            visited = Map()
        if not obj:
            return obj
        if isinstance(obj, dict):
            if obj in visited:
                return visited[obj]
            o: Dict = {}
            visited[obj] = o
            for name, value in obj.items():
                o[name] = self.from_maybe_impl(value, visited)
            return o
        if isinstance(obj, list):
            if obj in visited:
                return visited[obj]
            a: List = []
            visited[obj] = a
            for item in obj:
                a.append(self.from_maybe_impl(item, visited))
            return a
        api_class = self._mapping.get(type(obj))
        if api_class:
            api_instance = getattr(obj, API_ATTR, None)
            if not api_instance:
                api_instance = api_class(obj)
                setattr(obj, API_ATTR, api_instance)
            return api_instance
        else:
            return obj

    def from_impl(self, obj: Any) -> Any:
        assert obj
        result = self.from_maybe_impl(obj)
        assert result
        return result

    def from_impl_nullable(self, obj: Any = None) -> Optional[Any]:
        return self.from_impl(obj) if obj else None

    def from_impl_list(self, items: Sequence[Any]) -> List[Any]:
        return list(map(lambda a: self.from_impl(a), items))

    def from_impl_dict(self, map: Dict[str, Any]) -> Dict[str, Any]:
        return {name: self.from_impl(value) for name, value in map.items()}

    def to_impl(
        self, obj: Any, visited: Optional[Map[Any, Union[List, Dict]]] = None
    ) -> Any:
        if visited is None:
            visited = Map()
        try:
            if not obj:
                return obj
            if isinstance(obj, dict):
                if obj in visited:
                    return visited[obj]
                o: Dict = {}
                visited[obj] = o
                for name, value in obj.items():
                    o[name] = self.to_impl(value, visited)
                return o
            if isinstance(obj, list):
                if obj in visited:
                    return visited[obj]
                a: List = []
                visited[obj] = a
                for item in obj:
                    a.append(self.to_impl(item, visited))
                return a
            if isinstance(obj, ImplWrapper):
                return obj._impl_obj
            return obj
        except RecursionError:
            raise Error("Maximum argument depth exceeded")

    def wrap_handler(self, handler: Callable[..., Any]) -> Callable[..., None]:
        def wrapper_func(*args: Any) -> Any:
            arg_count = len(inspect.signature(handler).parameters)
            return handler(
                *list(map(lambda a: self.from_maybe_impl(a), args))[:arg_count]
            )

        if inspect.ismethod(handler):
            wrapper = getattr(handler.__self__, IMPL_ATTR + handler.__name__, None)
            if not wrapper:
                wrapper = wrapper_func
                setattr(
                    handler.__self__,
                    IMPL_ATTR + handler.__name__,
                    wrapper,
                )
            return wrapper

        wrapper = getattr(handler, IMPL_ATTR, None)
        if not wrapper:
            wrapper = wrapper_func
            setattr(handler, IMPL_ATTR, wrapper)
        return wrapper

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\timeouts.py ===
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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypedDict

    class JSONTimeouts(TypedDict, total=False):
        implicit: int
        pageLoad: int
        script: int

else:
    from typing import Dict

    JSONTimeouts = Dict[str, int]


class _TimeoutsDescriptor:
    """Get or set the value of the attributes listed below.

    _implicit_wait _page_load _script

    This does not set the value on the remote end.
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls) -> float:
        return getattr(obj, self.name) / 1000

    def __set__(self, obj, value) -> None:
        converted_value = getattr(obj, "_convert")(value)
        setattr(obj, self.name, converted_value)


class Timeouts:
    def __init__(self, implicit_wait: float = 0, page_load: float = 0, script: float = 0) -> None:
        """Create a new Timeouts object.

        This implements https://w3c.github.io/webdriver/#timeouts.

        :Args:
         - implicit_wait - Either an int or a float. Set how many
            seconds to wait when searching for elements before
            throwing an error.
         - page_load - Either an int or a float. Set how many seconds
            to wait for a page load to complete before throwing
            an error.
         - script - Either an int or a float. Set how many seconds to
            wait for an asynchronous script to finish execution
            before throwing an error.
        """

        self._implicit_wait = self._convert(implicit_wait)
        self._page_load = self._convert(page_load)
        self._script = self._convert(script)

    # Creating descriptor objects
    implicit_wait = _TimeoutsDescriptor("_implicit_wait")
    """Get or set how many seconds to wait when searching for elements.

    This does not set the value on the remote end.

    Usage:
    ------
    - Get
        - `self.implicit_wait`
    - Set
        - `self.implicit_wait` = `value`

    Parameters:
    -----------
    `value`: `float`
    """

    page_load = _TimeoutsDescriptor("_page_load")
    """Get or set how many seconds to wait for the page to load.

    This does not set the value on the remote end.

    Usage:
    ------
    - Get
        - `self.page_load`
    - Set
        - `self.page_load` = `value`

    Parameters:
    -----------
    `value`: `float`
    """

    script = _TimeoutsDescriptor("_script")
    """Get or set how many seconds to wait for an asynchronous script to finish
    execution.

    This does not set the value on the remote end.

    Usage:
    ------
    - Get
        - `self.script`
    - Set
        - `self.script` = `value`

    Parameters:
    -----------
    `value`: `float`
    """

    def _convert(self, timeout: float) -> int:
        if isinstance(timeout, (int, float)):
            return int(float(timeout) * 1000)
        raise TypeError("Timeouts can only be an int or a float")

    def _to_json(self) -> JSONTimeouts:
        timeouts: JSONTimeouts = {}
        if self._implicit_wait:
            timeouts["implicit"] = self._implicit_wait
        if self._page_load:
            timeouts["pageLoad"] = self._page_load
        if self._script:
            timeouts["script"] = self._script

        return timeouts

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\autocommand\autoasync.py ===
# Copyright 2014-2015 Nathan West
#
# This file is part of autocommand.
#
# autocommand is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# autocommand is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with autocommand.  If not, see <http://www.gnu.org/licenses/>.

from asyncio import get_event_loop, iscoroutine
from functools import wraps
from inspect import signature


async def _run_forever_coro(coro, args, kwargs, loop):
    '''
    This helper function launches an async main function that was tagged with
    forever=True. There are two possibilities:

    - The function is a normal function, which handles initializing the event
      loop, which is then run forever
    - The function is a coroutine, which needs to be scheduled in the event
      loop, which is then run forever
      - There is also the possibility that the function is a normal function
        wrapping a coroutine function

    The function is therefore called unconditionally and scheduled in the event
    loop if the return value is a coroutine object.

    The reason this is a separate function is to make absolutely sure that all
    the objects created are garbage collected after all is said and done; we
    do this to ensure that any exceptions raised in the tasks are collected
    ASAP.
    '''

    # Personal note: I consider this an antipattern, as it relies on the use of
    # unowned resources. The setup function dumps some stuff into the event
    # loop where it just whirls in the ether without a well defined owner or
    # lifetime. For this reason, there's a good chance I'll remove the
    # forever=True feature from autoasync at some point in the future.
    thing = coro(*args, **kwargs)
    if iscoroutine(thing):
        await thing


def autoasync(coro=None, *, loop=None, forever=False, pass_loop=False):
    '''
    Convert an asyncio coroutine into a function which, when called, is
    evaluted in an event loop, and the return value returned. This is intented
    to make it easy to write entry points into asyncio coroutines, which
    otherwise need to be explictly evaluted with an event loop's
    run_until_complete.

    If `loop` is given, it is used as the event loop to run the coro in. If it
    is None (the default), the loop is retreived using asyncio.get_event_loop.
    This call is defered until the decorated function is called, so that
    callers can install custom event loops or event loop policies after
    @autoasync is applied.

    If `forever` is True, the loop is run forever after the decorated coroutine
    is finished. Use this for servers created with asyncio.start_server and the
    like.

    If `pass_loop` is True, the event loop object is passed into the coroutine
    as the `loop` kwarg when the wrapper function is called. In this case, the
    wrapper function's __signature__ is updated to remove this parameter, so
    that autoparse can still be used on it without generating a parameter for
    `loop`.

    This coroutine can be called with ( @autoasync(...) ) or without
    ( @autoasync ) arguments.

    Examples:

    @autoasync
    def get_file(host, port):
        reader, writer = yield from asyncio.open_connection(host, port)
        data = reader.read()
        sys.stdout.write(data.decode())

    get_file(host, port)

    @autoasync(forever=True, pass_loop=True)
    def server(host, port, loop):
        yield_from loop.create_server(Proto, host, port)

    server('localhost', 8899)

    '''
    if coro is None:
        return lambda c: autoasync(
            c, loop=loop,
            forever=forever,
            pass_loop=pass_loop)

    # The old and new signatures are required to correctly bind the loop
    # parameter in 100% of cases, even if it's a positional parameter.
    # NOTE: A future release will probably require the loop parameter to be
    # a kwonly parameter.
    if pass_loop:
        old_sig = signature(coro)
        new_sig = old_sig.replace(parameters=(
            param for name, param in old_sig.parameters.items()
            if name != "loop"))

    @wraps(coro)
    def autoasync_wrapper(*args, **kwargs):
        # Defer the call to get_event_loop so that, if a custom policy is
        # installed after the autoasync decorator, it is respected at call time
        local_loop = get_event_loop() if loop is None else loop

        # Inject the 'loop' argument. We have to use this signature binding to
        # ensure it's injected in the correct place (positional, keyword, etc)
        if pass_loop:
            bound_args = old_sig.bind_partial()
            bound_args.arguments.update(
                loop=local_loop,
                **new_sig.bind(*args, **kwargs).arguments)
            args, kwargs = bound_args.args, bound_args.kwargs

        if forever:
            local_loop.create_task(_run_forever_coro(
                coro, args, kwargs, local_loop
            ))
            local_loop.run_forever()
        else:
            return local_loop.run_until_complete(coro(*args, **kwargs))

    # Attach the updated signature. This allows 'pass_loop' to be used with
    # autoparse
    if pass_loop:
        autoasync_wrapper.__signature__ = new_sig

    return autoasync_wrapper

# === NexusCore/openenv\Lib\site-packages\win32com\test\testGIT.py ===
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

import _thread
import traceback

import pythoncom
import win32api
import win32com.client
import win32event


def TestInterp(interp):
    assert interp.Eval("1+1") == 2, "The interpreter returned the wrong result."
    try:
        interp.Eval(1 + 1)
        raise AssertionError("The interpreter did not raise an exception")
    except pythoncom.com_error as details:
        import winerror

        assert (
            details[0] == winerror.DISP_E_TYPEMISMATCH
        ), "The interpreter exception was not winerror.DISP_E_TYPEMISMATCH."


def TestInterpInThread(stopEvent, cookie):
    try:
        DoTestInterpInThread(cookie)
    finally:
        win32event.SetEvent(stopEvent)


def CreateGIT():
    return pythoncom.CoCreateInstance(
        pythoncom.CLSID_StdGlobalInterfaceTable,
        None,
        pythoncom.CLSCTX_INPROC,
        pythoncom.IID_IGlobalInterfaceTable,
    )


def DoTestInterpInThread(cookie):
    try:
        pythoncom.CoInitialize()
        myThread = win32api.GetCurrentThreadId()
        GIT = CreateGIT()

        interp = GIT.GetInterfaceFromGlobal(cookie, pythoncom.IID_IDispatch)
        interp = win32com.client.Dispatch(interp)

        TestInterp(interp)
        interp.Exec("import win32api")
        print(
            "The test thread id is %d, Python.Interpreter's thread ID is %d"
            % (myThread, interp.Eval("win32api.GetCurrentThreadId()"))
        )
        interp = None
        pythoncom.CoUninitialize()
    except:
        traceback.print_exc()


def BeginThreadsSimpleMarshal(numThreads, cookie):
    """Creates multiple threads using simple (but slower) marshalling.

    Single interpreter object, but a new stream is created per thread.

    Returns the handles the threads will set when complete.
    """
    ret = []
    for i in range(numThreads):
        hEvent = win32event.CreateEvent(None, 0, 0, None)
        _thread.start_new(TestInterpInThread, (hEvent, cookie))
        ret.append(hEvent)
    return ret


def test(fn):
    print("The main thread is %d" % (win32api.GetCurrentThreadId()))
    GIT = CreateGIT()
    interp = win32com.client.Dispatch("Python.Interpreter")
    cookie = GIT.RegisterInterfaceInGlobal(interp._oleobj_, pythoncom.IID_IDispatch)

    events = fn(4, cookie)
    numFinished = 0
    while 1:
        try:
            rc = win32event.MsgWaitForMultipleObjects(
                events, 0, 2000, win32event.QS_ALLINPUT
            )
            if rc >= win32event.WAIT_OBJECT_0 and rc < win32event.WAIT_OBJECT_0 + len(
                events
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
    GIT.RevokeInterfaceFromGlobal(cookie)
    del interp
    del GIT


if __name__ == "__main__":
    test(BeginThreadsSimpleMarshal)
    win32api.Sleep(500)
    # Doing CoUninit here stop pythoncom.dll hanging when DLLMain shuts-down the process
    pythoncom.CoUninitialize()
    if pythoncom._GetInterfaceCount() != 0 or pythoncom._GetGatewayCount() != 0:
        print(
            "Done with interfaces=%d, gateways=%d"
            % (pythoncom._GetInterfaceCount(), pythoncom._GetGatewayCount())
        )
    else:
        print("Done.")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\padding.py ===
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from .console import (
        Console,
        ConsoleOptions,
        RenderableType,
        RenderResult,
    )

from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style

PaddingDimensions = Union[int, Tuple[int], Tuple[int, int], Tuple[int, int, int, int]]


class Padding(JupyterMixin):
    """Draw space around content.

    Example:
        >>> print(Padding("Hello", (2, 4), style="on blue"))

    Args:
        renderable (RenderableType): String or other renderable.
        pad (Union[int, Tuple[int]]): Padding for top, right, bottom, and left borders.
            May be specified with 1, 2, or 4 integers (CSS style).
        style (Union[str, Style], optional): Style for padding characters. Defaults to "none".
        expand (bool, optional): Expand padding to fit available width. Defaults to True.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        pad: "PaddingDimensions" = (0, 0, 0, 0),
        *,
        style: Union[str, Style] = "none",
        expand: bool = True,
    ):
        self.renderable = renderable
        self.top, self.right, self.bottom, self.left = self.unpack(pad)
        self.style = style
        self.expand = expand

    @classmethod
    def indent(cls, renderable: "RenderableType", level: int) -> "Padding":
        """Make padding instance to render an indent.

        Args:
            renderable (RenderableType): String or other renderable.
            level (int): Number of characters to indent.

        Returns:
            Padding: A Padding instance.
        """

        return Padding(renderable, pad=(0, 0, 0, level), expand=False)

    @staticmethod
    def unpack(pad: "PaddingDimensions") -> Tuple[int, int, int, int]:
        """Unpack padding specified in CSS style."""
        if isinstance(pad, int):
            return (pad, pad, pad, pad)
        if len(pad) == 1:
            _pad = pad[0]
            return (_pad, _pad, _pad, _pad)
        if len(pad) == 2:
            pad_top, pad_right = pad
            return (pad_top, pad_right, pad_top, pad_right)
        if len(pad) == 4:
            top, right, bottom, left = pad
            return (top, right, bottom, left)
        raise ValueError(f"1, 2 or 4 integers required for padding; {len(pad)} given")

    def __repr__(self) -> str:
        return f"Padding({self.renderable!r}, ({self.top},{self.right},{self.bottom},{self.left}))"

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        style = console.get_style(self.style)
        if self.expand:
            width = options.max_width
        else:
            width = min(
                Measurement.get(console, options, self.renderable).maximum
                + self.left
                + self.right,
                options.max_width,
            )
        render_options = options.update_width(width - self.left - self.right)
        if render_options.height is not None:
            render_options = render_options.update_height(
                height=render_options.height - self.top - self.bottom
            )
        lines = console.render_lines(
            self.renderable, render_options, style=style, pad=True
        )
        _Segment = Segment

        left = _Segment(" " * self.left, style) if self.left else None
        right = (
            [_Segment(f'{" " * self.right}', style), _Segment.line()]
            if self.right
            else [_Segment.line()]
        )
        blank_line: Optional[List[Segment]] = None
        if self.top:
            blank_line = [_Segment(f'{" " * width}\n', style)]
            yield from blank_line * self.top
        if left:
            for line in lines:
                yield left
                yield from line
                yield from right
        else:
            for line in lines:
                yield from line
                yield from right
        if self.bottom:
            blank_line = blank_line or [_Segment(f'{" " * width}\n', style)]
            yield from blank_line * self.bottom

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        max_width = options.max_width
        extra_width = self.left + self.right
        if max_width - extra_width < 1:
            return Measurement(max_width, max_width)
        measure_min, measure_max = Measurement.get(console, options, self.renderable)
        measurement = Measurement(measure_min + extra_width, measure_max + extra_width)
        measurement = measurement.with_maximum(max_width)
        return measurement


if __name__ == "__main__":  #  pragma: no cover
    from pip._vendor.rich import print

    print(Padding("Hello, World", (2, 4), style="on blue"))

# === NexusCore/openenv\Lib\site-packages\httpcore\__init__.py ===
from ._api import request, stream
from ._async import (
    AsyncConnectionInterface,
    AsyncConnectionPool,
    AsyncHTTP2Connection,
    AsyncHTTP11Connection,
    AsyncHTTPConnection,
    AsyncHTTPProxy,
    AsyncSOCKSProxy,
)
from ._backends.base import (
    SOCKET_OPTION,
    AsyncNetworkBackend,
    AsyncNetworkStream,
    NetworkBackend,
    NetworkStream,
)
from ._backends.mock import AsyncMockBackend, AsyncMockStream, MockBackend, MockStream
from ._backends.sync import SyncBackend
from ._exceptions import (
    ConnectError,
    ConnectionNotAvailable,
    ConnectTimeout,
    LocalProtocolError,
    NetworkError,
    PoolTimeout,
    ProtocolError,
    ProxyError,
    ReadError,
    ReadTimeout,
    RemoteProtocolError,
    TimeoutException,
    UnsupportedProtocol,
    WriteError,
    WriteTimeout,
)
from ._models import URL, Origin, Proxy, Request, Response
from ._ssl import default_ssl_context
from ._sync import (
    ConnectionInterface,
    ConnectionPool,
    HTTP2Connection,
    HTTP11Connection,
    HTTPConnection,
    HTTPProxy,
    SOCKSProxy,
)

# The 'httpcore.AnyIOBackend' class is conditional on 'anyio' being installed.
try:
    from ._backends.anyio import AnyIOBackend
except ImportError:  # pragma: nocover

    class AnyIOBackend:  # type: ignore
        def __init__(self, *args, **kwargs):  # type: ignore
            msg = (
                "Attempted to use 'httpcore.AnyIOBackend' but 'anyio' is not installed."
            )
            raise RuntimeError(msg)


# The 'httpcore.TrioBackend' class is conditional on 'trio' being installed.
try:
    from ._backends.trio import TrioBackend
except ImportError:  # pragma: nocover

    class TrioBackend:  # type: ignore
        def __init__(self, *args, **kwargs):  # type: ignore
            msg = "Attempted to use 'httpcore.TrioBackend' but 'trio' is not installed."
            raise RuntimeError(msg)


__all__ = [
    # top-level requests
    "request",
    "stream",
    # models
    "Origin",
    "URL",
    "Request",
    "Response",
    "Proxy",
    # async
    "AsyncHTTPConnection",
    "AsyncConnectionPool",
    "AsyncHTTPProxy",
    "AsyncHTTP11Connection",
    "AsyncHTTP2Connection",
    "AsyncConnectionInterface",
    "AsyncSOCKSProxy",
    # sync
    "HTTPConnection",
    "ConnectionPool",
    "HTTPProxy",
    "HTTP11Connection",
    "HTTP2Connection",
    "ConnectionInterface",
    "SOCKSProxy",
    # network backends, implementations
    "SyncBackend",
    "AnyIOBackend",
    "TrioBackend",
    # network backends, mock implementations
    "AsyncMockBackend",
    "AsyncMockStream",
    "MockBackend",
    "MockStream",
    # network backends, interface
    "AsyncNetworkStream",
    "AsyncNetworkBackend",
    "NetworkStream",
    "NetworkBackend",
    # util
    "default_ssl_context",
    "SOCKET_OPTION",
    # exceptions
    "ConnectionNotAvailable",
    "ProxyError",
    "ProtocolError",
    "LocalProtocolError",
    "RemoteProtocolError",
    "UnsupportedProtocol",
    "TimeoutException",
    "PoolTimeout",
    "ConnectTimeout",
    "ReadTimeout",
    "WriteTimeout",
    "NetworkError",
    "ConnectError",
    "ReadError",
    "WriteError",
]

__version__ = "1.0.9"


__locals = locals()
for __name in __all__:
    # Exclude SOCKET_OPTION, it causes AttributeError on Python 3.14
    if not __name.startswith(("__", "SOCKET_OPTION")):
        setattr(__locals[__name], "__module__", "httpcore")  # noqa

# === NexusCore/openenv\Lib\site-packages\matplotlib\container.py ===
from matplotlib import cbook
from matplotlib.artist import Artist


class Container(tuple):
    """
    Base class for containers.

    Containers are classes that collect semantically related Artists such as
    the bars of a bar plot.
    """

    def __repr__(self):
        return f"<{type(self).__name__} object of {len(self)} artists>"

    def __new__(cls, *args, **kwargs):
        return tuple.__new__(cls, args[0])

    def __init__(self, kl, label=None):
        self._callbacks = cbook.CallbackRegistry(signals=["pchanged"])
        self._remove_method = None
        self._label = str(label) if label is not None else None

    def remove(self):
        for c in cbook.flatten(
                self, scalarp=lambda x: isinstance(x, Artist)):
            if c is not None:
                c.remove()
        if self._remove_method:
            self._remove_method(self)

    def get_children(self):
        return [child for child in cbook.flatten(self) if child is not None]

    get_label = Artist.get_label
    set_label = Artist.set_label
    add_callback = Artist.add_callback
    remove_callback = Artist.remove_callback
    pchanged = Artist.pchanged


class BarContainer(Container):
    """
    Container for the artists of bar plots (e.g. created by `.Axes.bar`).

    The container can be treated as a tuple of the *patches* themselves.
    Additionally, you can access these and further parameters by the
    attributes.

    Attributes
    ----------
    patches : list of :class:`~matplotlib.patches.Rectangle`
        The artists of the bars.

    errorbar : None or :class:`~matplotlib.container.ErrorbarContainer`
        A container for the error bar artists if error bars are present.
        *None* otherwise.

    datavalues : None or array-like
        The underlying data values corresponding to the bars.

    orientation : {'vertical', 'horizontal'}, default: None
        If 'vertical', the bars are assumed to be vertical.
        If 'horizontal', the bars are assumed to be horizontal.

    """

    def __init__(self, patches, errorbar=None, *, datavalues=None,
                 orientation=None, **kwargs):
        self.patches = patches
        self.errorbar = errorbar
        self.datavalues = datavalues
        self.orientation = orientation
        super().__init__(patches, **kwargs)


class ErrorbarContainer(Container):
    """
    Container for the artists of error bars (e.g. created by `.Axes.errorbar`).

    The container can be treated as the *lines* tuple itself.
    Additionally, you can access these and further parameters by the
    attributes.

    Attributes
    ----------
    lines : tuple
        Tuple of ``(data_line, caplines, barlinecols)``.

        - data_line : A `~matplotlib.lines.Line2D` instance of x, y plot markers
          and/or line.
        - caplines : A tuple of `~matplotlib.lines.Line2D` instances of the error
          bar caps.
        - barlinecols : A tuple of `~matplotlib.collections.LineCollection` with the
          horizontal and vertical error ranges.

    has_xerr, has_yerr : bool
        ``True`` if the errorbar has x/y errors.

    """

    def __init__(self, lines, has_xerr=False, has_yerr=False, **kwargs):
        self.lines = lines
        self.has_xerr = has_xerr
        self.has_yerr = has_yerr
        super().__init__(lines, **kwargs)


class StemContainer(Container):
    """
    Container for the artists created in a :meth:`.Axes.stem` plot.

    The container can be treated like a namedtuple ``(markerline, stemlines,
    baseline)``.

    Attributes
    ----------
    markerline : `~matplotlib.lines.Line2D`
        The artist of the markers at the stem heads.

    stemlines : `~matplotlib.collections.LineCollection`
        The artists of the vertical lines for all stems.

    baseline : `~matplotlib.lines.Line2D`
        The artist of the horizontal baseline.
    """
    def __init__(self, markerline_stemlines_baseline, **kwargs):
        """
        Parameters
        ----------
        markerline_stemlines_baseline : tuple
            Tuple of ``(markerline, stemlines, baseline)``.
            ``markerline`` contains the `.Line2D` of the markers,
            ``stemlines`` is a `.LineCollection` of the main lines,
            ``baseline`` is the `.Line2D` of the baseline.
        """
        markerline, stemlines, baseline = markerline_stemlines_baseline
        self.markerline = markerline
        self.stemlines = stemlines
        self.baseline = baseline
        super().__init__(markerline_stemlines_baseline, **kwargs)

# === NexusCore/openenv\Lib\site-packages\matplotlib\_docstring.py ===
import inspect

from . import _api


def kwarg_doc(text):
    """
    Decorator for defining the kwdoc documentation of artist properties.

    This decorator can be applied to artist property setter methods.
    The given text is stored in a private attribute ``_kwarg_doc`` on
    the method.  It is used to overwrite auto-generated documentation
    in the *kwdoc list* for artists. The kwdoc list is used to document
    ``**kwargs`` when they are properties of an artist. See e.g. the
    ``**kwargs`` section in `.Axes.text`.

    The text should contain the supported types, as well as the default
    value if applicable, e.g.:

        @_docstring.kwarg_doc("bool, default: :rc:`text.usetex`")
        def set_usetex(self, usetex):

    See Also
    --------
    matplotlib.artist.kwdoc

    """
    def decorator(func):
        func._kwarg_doc = text
        return func
    return decorator


class Substitution:
    """
    A decorator that performs %-substitution on an object's docstring.

    This decorator should be robust even if ``obj.__doc__`` is None (for
    example, if -OO was passed to the interpreter).

    Usage: construct a docstring.Substitution with a sequence or dictionary
    suitable for performing substitution; then decorate a suitable function
    with the constructed object, e.g.::

        sub_author_name = Substitution(author='Jason')

        @sub_author_name
        def some_function(x):
            "%(author)s wrote this function"

        # note that some_function.__doc__ is now "Jason wrote this function"

    One can also use positional arguments::

        sub_first_last_names = Substitution('Edgar Allen', 'Poe')

        @sub_first_last_names
        def some_function(x):
            "%s %s wrote the Raven"
    """
    def __init__(self, *args, **kwargs):
        if args and kwargs:
            raise TypeError("Only positional or keyword args are allowed")
        self.params = args or kwargs

    def __call__(self, func):
        if func.__doc__:
            func.__doc__ = inspect.cleandoc(func.__doc__) % self.params
        return func


class _ArtistKwdocLoader(dict):
    def __missing__(self, key):
        if not key.endswith(":kwdoc"):
            raise KeyError(key)
        name = key[:-len(":kwdoc")]
        from matplotlib.artist import Artist, kwdoc
        try:
            cls, = (cls for cls in _api.recursive_subclasses(Artist)
                    if cls.__name__ == name)
        except ValueError as e:
            raise KeyError(key) from e
        return self.setdefault(key, kwdoc(cls))


class _ArtistPropertiesSubstitution:
    """
    A class to substitute formatted placeholders in docstrings.

    This is realized in a single instance ``_docstring.interpd``.

    Use `~._ArtistPropertiesSubstition.register` to define placeholders and
    their substitution, e.g. ``_docstring.interpd.register(name="some value")``.

    Use this as a decorator to apply the substitution::

        @_docstring.interpd
        def some_func():
            '''Replace %(name)s.'''

    Decorating a class triggers substitution both on the class docstring and
    on the class' ``__init__`` docstring (which is a commonly required
    pattern for Artist subclasses).

    Substitutions of the form ``%(classname:kwdoc)s`` (ending with the
    literal ":kwdoc" suffix) trigger lookup of an Artist subclass with the
    given *classname*, and are substituted with the `.kwdoc` of that class.
    """

    def __init__(self):
        self.params = _ArtistKwdocLoader()

    def register(self, **kwargs):
        """
        Register substitutions.

        ``_docstring.interpd.register(name="some value")`` makes "name" available
        as a named parameter that will be replaced by "some value".
        """
        self.params.update(**kwargs)

    def __call__(self, obj):
        if obj.__doc__:
            obj.__doc__ = inspect.cleandoc(obj.__doc__) % self.params
        if isinstance(obj, type) and obj.__init__ != object.__init__:
            self(obj.__init__)
        return obj


def copy(source):
    """Copy a docstring from another source function (if present)."""
    def do_copy(target):
        if source.__doc__:
            target.__doc__ = source.__doc__
        return target
    return do_copy


# Create a decorator that will house the various docstring snippets reused
# throughout Matplotlib.
interpd = _ArtistPropertiesSubstitution()

# === NexusCore/openenv\Lib\site-packages\openai\_module_client.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import TYPE_CHECKING
from typing_extensions import override

if TYPE_CHECKING:
    from .resources.files import Files
    from .resources.images import Images
    from .resources.models import Models
    from .resources.batches import Batches
    from .resources.beta.beta import Beta
    from .resources.chat.chat import Chat
    from .resources.embeddings import Embeddings
    from .resources.audio.audio import Audio
    from .resources.completions import Completions
    from .resources.evals.evals import Evals
    from .resources.moderations import Moderations
    from .resources.uploads.uploads import Uploads
    from .resources.responses.responses import Responses
    from .resources.containers.containers import Containers
    from .resources.fine_tuning.fine_tuning import FineTuning
    from .resources.vector_stores.vector_stores import VectorStores

from . import _load_client
from ._utils import LazyProxy


class ChatProxy(LazyProxy["Chat"]):
    @override
    def __load__(self) -> Chat:
        return _load_client().chat


class BetaProxy(LazyProxy["Beta"]):
    @override
    def __load__(self) -> Beta:
        return _load_client().beta


class FilesProxy(LazyProxy["Files"]):
    @override
    def __load__(self) -> Files:
        return _load_client().files


class AudioProxy(LazyProxy["Audio"]):
    @override
    def __load__(self) -> Audio:
        return _load_client().audio


class EvalsProxy(LazyProxy["Evals"]):
    @override
    def __load__(self) -> Evals:
        return _load_client().evals


class ImagesProxy(LazyProxy["Images"]):
    @override
    def __load__(self) -> Images:
        return _load_client().images


class ModelsProxy(LazyProxy["Models"]):
    @override
    def __load__(self) -> Models:
        return _load_client().models


class BatchesProxy(LazyProxy["Batches"]):
    @override
    def __load__(self) -> Batches:
        return _load_client().batches


class UploadsProxy(LazyProxy["Uploads"]):
    @override
    def __load__(self) -> Uploads:
        return _load_client().uploads


class ResponsesProxy(LazyProxy["Responses"]):
    @override
    def __load__(self) -> Responses:
        return _load_client().responses


class EmbeddingsProxy(LazyProxy["Embeddings"]):
    @override
    def __load__(self) -> Embeddings:
        return _load_client().embeddings


class ContainersProxy(LazyProxy["Containers"]):
    @override
    def __load__(self) -> Containers:
        return _load_client().containers


class CompletionsProxy(LazyProxy["Completions"]):
    @override
    def __load__(self) -> Completions:
        return _load_client().completions


class ModerationsProxy(LazyProxy["Moderations"]):
    @override
    def __load__(self) -> Moderations:
        return _load_client().moderations


class FineTuningProxy(LazyProxy["FineTuning"]):
    @override
    def __load__(self) -> FineTuning:
        return _load_client().fine_tuning


class VectorStoresProxy(LazyProxy["VectorStores"]):
    @override
    def __load__(self) -> VectorStores:
        return _load_client().vector_stores


chat: Chat = ChatProxy().__as_proxied__()
beta: Beta = BetaProxy().__as_proxied__()
files: Files = FilesProxy().__as_proxied__()
audio: Audio = AudioProxy().__as_proxied__()
evals: Evals = EvalsProxy().__as_proxied__()
images: Images = ImagesProxy().__as_proxied__()
models: Models = ModelsProxy().__as_proxied__()
batches: Batches = BatchesProxy().__as_proxied__()
uploads: Uploads = UploadsProxy().__as_proxied__()
responses: Responses = ResponsesProxy().__as_proxied__()
embeddings: Embeddings = EmbeddingsProxy().__as_proxied__()
containers: Containers = ContainersProxy().__as_proxied__()
completions: Completions = CompletionsProxy().__as_proxied__()
moderations: Moderations = ModerationsProxy().__as_proxied__()
fine_tuning: FineTuning = FineTuningProxy().__as_proxied__()
vector_stores: VectorStores = VectorStoresProxy().__as_proxied__()

# === NexusCore/openenv\Lib\site-packages\rich\padding.py ===
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from .console import (
        Console,
        ConsoleOptions,
        RenderableType,
        RenderResult,
    )

from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style

PaddingDimensions = Union[int, Tuple[int], Tuple[int, int], Tuple[int, int, int, int]]


class Padding(JupyterMixin):
    """Draw space around content.

    Example:
        >>> print(Padding("Hello", (2, 4), style="on blue"))

    Args:
        renderable (RenderableType): String or other renderable.
        pad (Union[int, Tuple[int]]): Padding for top, right, bottom, and left borders.
            May be specified with 1, 2, or 4 integers (CSS style).
        style (Union[str, Style], optional): Style for padding characters. Defaults to "none".
        expand (bool, optional): Expand padding to fit available width. Defaults to True.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        pad: "PaddingDimensions" = (0, 0, 0, 0),
        *,
        style: Union[str, Style] = "none",
        expand: bool = True,
    ):
        self.renderable = renderable
        self.top, self.right, self.bottom, self.left = self.unpack(pad)
        self.style = style
        self.expand = expand

    @classmethod
    def indent(cls, renderable: "RenderableType", level: int) -> "Padding":
        """Make padding instance to render an indent.

        Args:
            renderable (RenderableType): String or other renderable.
            level (int): Number of characters to indent.

        Returns:
            Padding: A Padding instance.
        """

        return Padding(renderable, pad=(0, 0, 0, level), expand=False)

    @staticmethod
    def unpack(pad: "PaddingDimensions") -> Tuple[int, int, int, int]:
        """Unpack padding specified in CSS style."""
        if isinstance(pad, int):
            return (pad, pad, pad, pad)
        if len(pad) == 1:
            _pad = pad[0]
            return (_pad, _pad, _pad, _pad)
        if len(pad) == 2:
            pad_top, pad_right = pad
            return (pad_top, pad_right, pad_top, pad_right)
        if len(pad) == 4:
            top, right, bottom, left = pad
            return (top, right, bottom, left)
        raise ValueError(f"1, 2 or 4 integers required for padding; {len(pad)} given")

    def __repr__(self) -> str:
        return f"Padding({self.renderable!r}, ({self.top},{self.right},{self.bottom},{self.left}))"

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        style = console.get_style(self.style)
        if self.expand:
            width = options.max_width
        else:
            width = min(
                Measurement.get(console, options, self.renderable).maximum
                + self.left
                + self.right,
                options.max_width,
            )
        render_options = options.update_width(width - self.left - self.right)
        if render_options.height is not None:
            render_options = render_options.update_height(
                height=render_options.height - self.top - self.bottom
            )
        lines = console.render_lines(
            self.renderable, render_options, style=style, pad=True
        )
        _Segment = Segment

        left = _Segment(" " * self.left, style) if self.left else None
        right = (
            [_Segment(f'{" " * self.right}', style), _Segment.line()]
            if self.right
            else [_Segment.line()]
        )
        blank_line: Optional[List[Segment]] = None
        if self.top:
            blank_line = [_Segment(f'{" " * width}\n', style)]
            yield from blank_line * self.top
        if left:
            for line in lines:
                yield left
                yield from line
                yield from right
        else:
            for line in lines:
                yield from line
                yield from right
        if self.bottom:
            blank_line = blank_line or [_Segment(f'{" " * width}\n', style)]
            yield from blank_line * self.bottom

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        max_width = options.max_width
        extra_width = self.left + self.right
        if max_width - extra_width < 1:
            return Measurement(max_width, max_width)
        measure_min, measure_max = Measurement.get(console, options, self.renderable)
        measurement = Measurement(measure_min + extra_width, measure_max + extra_width)
        measurement = measurement.with_maximum(max_width)
        return measurement


if __name__ == "__main__":  #  pragma: no cover
    from rich import print

    print(Padding("Hello, World", (2, 4), style="on blue"))

# === NexusCore/openenv\Lib\site-packages\anyio\streams\stapled.py ===
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from ..abc import (
    ByteReceiveStream,
    ByteSendStream,
    ByteStream,
    Listener,
    ObjectReceiveStream,
    ObjectSendStream,
    ObjectStream,
    TaskGroup,
)

T_Item = TypeVar("T_Item")
T_Stream = TypeVar("T_Stream")


@dataclass(eq=False)
class StapledByteStream(ByteStream):
    """
    Combines two byte streams into a single, bidirectional byte stream.

    Extra attributes will be provided from both streams, with the receive stream
    providing the values in case of a conflict.

    :param ByteSendStream send_stream: the sending byte stream
    :param ByteReceiveStream receive_stream: the receiving byte stream
    """

    send_stream: ByteSendStream
    receive_stream: ByteReceiveStream

    async def receive(self, max_bytes: int = 65536) -> bytes:
        return await self.receive_stream.receive(max_bytes)

    async def send(self, item: bytes) -> None:
        await self.send_stream.send(item)

    async def send_eof(self) -> None:
        await self.send_stream.aclose()

    async def aclose(self) -> None:
        await self.send_stream.aclose()
        await self.receive_stream.aclose()

    @property
    def extra_attributes(self) -> Mapping[Any, Callable[[], Any]]:
        return {
            **self.send_stream.extra_attributes,
            **self.receive_stream.extra_attributes,
        }


@dataclass(eq=False)
class StapledObjectStream(Generic[T_Item], ObjectStream[T_Item]):
    """
    Combines two object streams into a single, bidirectional object stream.

    Extra attributes will be provided from both streams, with the receive stream
    providing the values in case of a conflict.

    :param ObjectSendStream send_stream: the sending object stream
    :param ObjectReceiveStream receive_stream: the receiving object stream
    """

    send_stream: ObjectSendStream[T_Item]
    receive_stream: ObjectReceiveStream[T_Item]

    async def receive(self) -> T_Item:
        return await self.receive_stream.receive()

    async def send(self, item: T_Item) -> None:
        await self.send_stream.send(item)

    async def send_eof(self) -> None:
        await self.send_stream.aclose()

    async def aclose(self) -> None:
        await self.send_stream.aclose()
        await self.receive_stream.aclose()

    @property
    def extra_attributes(self) -> Mapping[Any, Callable[[], Any]]:
        return {
            **self.send_stream.extra_attributes,
            **self.receive_stream.extra_attributes,
        }


@dataclass(eq=False)
class MultiListener(Generic[T_Stream], Listener[T_Stream]):
    """
    Combines multiple listeners into one, serving connections from all of them at once.

    Any MultiListeners in the given collection of listeners will have their listeners
    moved into this one.

    Extra attributes are provided from each listener, with each successive listener
    overriding any conflicting attributes from the previous one.

    :param listeners: listeners to serve
    :type listeners: Sequence[Listener[T_Stream]]
    """

    listeners: Sequence[Listener[T_Stream]]

    def __post_init__(self) -> None:
        listeners: list[Listener[T_Stream]] = []
        for listener in self.listeners:
            if isinstance(listener, MultiListener):
                listeners.extend(listener.listeners)
                del listener.listeners[:]  # type: ignore[attr-defined]
            else:
                listeners.append(listener)

        self.listeners = listeners

    async def serve(
        self, handler: Callable[[T_Stream], Any], task_group: TaskGroup | None = None
    ) -> None:
        from .. import create_task_group

        async with create_task_group() as tg:
            for listener in self.listeners:
                tg.start_soon(listener.serve, handler, task_group)

    async def aclose(self) -> None:
        for listener in self.listeners:
            await listener.aclose()

    @property
    def extra_attributes(self) -> Mapping[Any, Callable[[], Any]]:
        attributes: dict = {}
        for listener in self.listeners:
            attributes.update(listener.extra_attributes)

        return attributes

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_runfiles\pydev_runfiles_unittest.py ===
import unittest as python_unittest
from _pydev_runfiles import pydev_runfiles_xml_rpc
import time
from _pydevd_bundle import pydevd_io
import traceback
from _pydevd_bundle.pydevd_constants import *  # @UnusedWildImport
from io import StringIO


# =======================================================================================================================
# PydevTextTestRunner
# =======================================================================================================================
class PydevTextTestRunner(python_unittest.TextTestRunner):
    def _makeResult(self):
        return PydevTestResult(self.stream, self.descriptions, self.verbosity)


_PythonTextTestResult = python_unittest.TextTestRunner()._makeResult().__class__


# =======================================================================================================================
# PydevTestResult
# =======================================================================================================================
class PydevTestResult(_PythonTextTestResult):
    def addSubTest(self, test, subtest, err):
        """Called at the end of a subtest.
        'err' is None if the subtest ended successfully, otherwise it's a
        tuple of values as returned by sys.exc_info().
        """
        _PythonTextTestResult.addSubTest(self, test, subtest, err)
        if err is not None:
            subdesc = subtest._subDescription()
            error = (test, self._exc_info_to_string(err, test))
            self._reportErrors([error], [], "", "%s %s" % (self.get_test_name(test), subdesc))

    def startTest(self, test):
        _PythonTextTestResult.startTest(self, test)
        self.buf = pydevd_io.start_redirect(keep_original_redirection=True, std="both")
        self.start_time = time.time()
        self._current_errors_stack = []
        self._current_failures_stack = []

        try:
            test_name = test.__class__.__name__ + "." + test._testMethodName
        except AttributeError:
            # Support for jython 2.1 (__testMethodName is pseudo-private in the test case)
            test_name = test.__class__.__name__ + "." + test._TestCase__testMethodName

        pydev_runfiles_xml_rpc.notifyStartTest(test.__pydev_pyfile__, test_name)

    def get_test_name(self, test):
        try:
            try:
                test_name = test.__class__.__name__ + "." + test._testMethodName
            except AttributeError:
                # Support for jython 2.1 (__testMethodName is pseudo-private in the test case)
                try:
                    test_name = test.__class__.__name__ + "." + test._TestCase__testMethodName
                # Support for class/module exceptions (test is instance of _ErrorHolder)
                except:
                    test_name = test.description.split()[1][1:-1] + " <" + test.description.split()[0] + ">"
        except:
            traceback.print_exc()
            return "<unable to get test name>"
        return test_name

    def stopTest(self, test):
        end_time = time.time()
        pydevd_io.end_redirect(std="both")

        _PythonTextTestResult.stopTest(self, test)

        captured_output = self.buf.getvalue()
        del self.buf
        error_contents = ""
        test_name = self.get_test_name(test)

        diff_time = "%.2f" % (end_time - self.start_time)

        skipped = False
        outcome = getattr(test, "_outcome", None)
        if outcome is not None:
            skipped = bool(getattr(outcome, "skipped", None))

        if skipped:
            pydev_runfiles_xml_rpc.notifyTest("skip", captured_output, error_contents, test.__pydev_pyfile__, test_name, diff_time)
        elif not self._current_errors_stack and not self._current_failures_stack:
            pydev_runfiles_xml_rpc.notifyTest("ok", captured_output, error_contents, test.__pydev_pyfile__, test_name, diff_time)
        else:
            self._reportErrors(self._current_errors_stack, self._current_failures_stack, captured_output, test_name)

    def _reportErrors(self, errors, failures, captured_output, test_name, diff_time=""):
        error_contents = []
        for test, s in errors + failures:
            if type(s) == type((1,)):  # If it's a tuple (for jython 2.1)
                sio = StringIO()
                traceback.print_exception(s[0], s[1], s[2], file=sio)
                s = sio.getvalue()
            error_contents.append(s)

        sep = "\n" + self.separator1
        error_contents = sep.join(error_contents)

        if errors and not failures:
            try:
                pydev_runfiles_xml_rpc.notifyTest("error", captured_output, error_contents, test.__pydev_pyfile__, test_name, diff_time)
            except:
                file_start = error_contents.find('File "')
                file_end = error_contents.find('", ', file_start)
                if file_start != -1 and file_end != -1:
                    file = error_contents[file_start + 6 : file_end]
                else:
                    file = "<unable to get file>"
                pydev_runfiles_xml_rpc.notifyTest("error", captured_output, error_contents, file, test_name, diff_time)

        elif failures and not errors:
            pydev_runfiles_xml_rpc.notifyTest("fail", captured_output, error_contents, test.__pydev_pyfile__, test_name, diff_time)

        else:  # Ok, we got both, errors and failures. Let's mark it as an error in the end.
            pydev_runfiles_xml_rpc.notifyTest("error", captured_output, error_contents, test.__pydev_pyfile__, test_name, diff_time)

    def addError(self, test, err):
        _PythonTextTestResult.addError(self, test, err)
        # Support for class/module exceptions (test is instance of _ErrorHolder)
        if not hasattr(self, "_current_errors_stack") or test.__class__.__name__ == "_ErrorHolder":
            # Not in start...end, so, report error now (i.e.: django pre/post-setup)
            self._reportErrors([self.errors[-1]], [], "", self.get_test_name(test))
        else:
            self._current_errors_stack.append(self.errors[-1])

    def addFailure(self, test, err):
        _PythonTextTestResult.addFailure(self, test, err)
        if not hasattr(self, "_current_failures_stack"):
            # Not in start...end, so, report error now (i.e.: django pre/post-setup)
            self._reportErrors([], [self.failures[-1]], "", self.get_test_name(test))
        else:
            self._current_failures_stack.append(self.failures[-1])


class PydevTestSuite(python_unittest.TestSuite):
    pass

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\permission.py ===
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
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "Permission",
    },
)


class Permission(proto.Message):
    r"""Permission resource grants user, group or the rest of the
    world access to the PaLM API resource (e.g. a tuned model,
    corpus).

    A role is a collection of permitted operations that allows users
    to perform specific actions on PaLM API resources. To make them
    available to users, groups, or service accounts, you assign
    roles. When you assign a role, you grant permissions that the
    role contains.

    There are three concentric roles. Each role is a superset of the
    previous role's permitted operations:

    - reader can use the resource (e.g. tuned model, corpus) for
      inference
    - writer has reader's permissions and additionally can edit and
      share
    - owner has writer's permissions and additionally can delete


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        name (str):
            Output only. Identifier. The permission name. A unique name
            will be generated on create. Examples:
            tunedModels/{tuned_model}/permissions/{permission}
            corpora/{corpus}/permissions/{permission} Output only.
        grantee_type (google.ai.generativelanguage_v1beta.types.Permission.GranteeType):
            Optional. Immutable. The type of the grantee.

            This field is a member of `oneof`_ ``_grantee_type``.
        email_address (str):
            Optional. Immutable. The email address of the
            user of group which this permission refers.
            Field is not set when permission's grantee type
            is EVERYONE.

            This field is a member of `oneof`_ ``_email_address``.
        role (google.ai.generativelanguage_v1beta.types.Permission.Role):
            Required. The role granted by this
            permission.

            This field is a member of `oneof`_ ``_role``.
    """

    class GranteeType(proto.Enum):
        r"""Defines types of the grantee of this permission.

        Values:
            GRANTEE_TYPE_UNSPECIFIED (0):
                The default value. This value is unused.
            USER (1):
                Represents a user. When set, you must provide email_address
                for the user.
            GROUP (2):
                Represents a group. When set, you must provide email_address
                for the group.
            EVERYONE (3):
                Represents access to everyone. No extra
                information is required.
        """
        GRANTEE_TYPE_UNSPECIFIED = 0
        USER = 1
        GROUP = 2
        EVERYONE = 3

    class Role(proto.Enum):
        r"""Defines the role granted by this permission.

        Values:
            ROLE_UNSPECIFIED (0):
                The default value. This value is unused.
            OWNER (1):
                Owner can use, update, share and delete the
                resource.
            WRITER (2):
                Writer can use, update and share the
                resource.
            READER (3):
                Reader can use the resource.
        """
        ROLE_UNSPECIFIED = 0
        OWNER = 1
        WRITER = 2
        READER = 3

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    grantee_type: GranteeType = proto.Field(
        proto.ENUM,
        number=2,
        optional=True,
        enum=GranteeType,
    )
    email_address: str = proto.Field(
        proto.STRING,
        number=3,
        optional=True,
    )
    role: Role = proto.Field(
        proto.ENUM,
        number=4,
        optional=True,
        enum=Role,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\utils\_paths.py ===
# coding=utf-8
# Copyright 2022-present, the HuggingFace Inc. team.
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
"""Contains utilities to handle paths in Huggingface Hub."""

from fnmatch import fnmatch
from pathlib import Path
from typing import Callable, Generator, Iterable, List, Optional, TypeVar, Union


T = TypeVar("T")

# Always ignore `.git` and `.cache/huggingface` folders in commits
DEFAULT_IGNORE_PATTERNS = [
    ".git",
    ".git/*",
    "*/.git",
    "**/.git/**",
    ".cache/huggingface",
    ".cache/huggingface/*",
    "*/.cache/huggingface",
    "**/.cache/huggingface/**",
]
# Forbidden to commit these folders
FORBIDDEN_FOLDERS = [".git", ".cache"]


def filter_repo_objects(
    items: Iterable[T],
    *,
    allow_patterns: Optional[Union[List[str], str]] = None,
    ignore_patterns: Optional[Union[List[str], str]] = None,
    key: Optional[Callable[[T], str]] = None,
) -> Generator[T, None, None]:
    """Filter repo objects based on an allowlist and a denylist.

    Input must be a list of paths (`str` or `Path`) or a list of arbitrary objects.
    In the later case, `key` must be provided and specifies a function of one argument
    that is used to extract a path from each element in iterable.

    Patterns are Unix shell-style wildcards which are NOT regular expressions. See
    https://docs.python.org/3/library/fnmatch.html for more details.

    Args:
        items (`Iterable`):
            List of items to filter.
        allow_patterns (`str` or `List[str]`, *optional*):
            Patterns constituting the allowlist. If provided, item paths must match at
            least one pattern from the allowlist.
        ignore_patterns (`str` or `List[str]`, *optional*):
            Patterns constituting the denylist. If provided, item paths must not match
            any patterns from the denylist.
        key (`Callable[[T], str]`, *optional*):
            Single-argument function to extract a path from each item. If not provided,
            the `items` must already be `str` or `Path`.

    Returns:
        Filtered list of objects, as a generator.

    Raises:
        :class:`ValueError`:
            If `key` is not provided and items are not `str` or `Path`.

    Example usage with paths:
    ```python
    >>> # Filter only PDFs that are not hidden.
    >>> list(filter_repo_objects(
    ...     ["aaa.PDF", "bbb.jpg", ".ccc.pdf", ".ddd.png"],
    ...     allow_patterns=["*.pdf"],
    ...     ignore_patterns=[".*"],
    ... ))
    ["aaa.pdf"]
    ```

    Example usage with objects:
    ```python
    >>> list(filter_repo_objects(
    ... [
    ...     CommitOperationAdd(path_or_fileobj="/tmp/aaa.pdf", path_in_repo="aaa.pdf")
    ...     CommitOperationAdd(path_or_fileobj="/tmp/bbb.jpg", path_in_repo="bbb.jpg")
    ...     CommitOperationAdd(path_or_fileobj="/tmp/.ccc.pdf", path_in_repo=".ccc.pdf")
    ...     CommitOperationAdd(path_or_fileobj="/tmp/.ddd.png", path_in_repo=".ddd.png")
    ... ],
    ... allow_patterns=["*.pdf"],
    ... ignore_patterns=[".*"],
    ... key=lambda x: x.repo_in_path
    ... ))
    [CommitOperationAdd(path_or_fileobj="/tmp/aaa.pdf", path_in_repo="aaa.pdf")]
    ```
    """
    if isinstance(allow_patterns, str):
        allow_patterns = [allow_patterns]

    if isinstance(ignore_patterns, str):
        ignore_patterns = [ignore_patterns]

    if allow_patterns is not None:
        allow_patterns = [_add_wildcard_to_directories(p) for p in allow_patterns]
    if ignore_patterns is not None:
        ignore_patterns = [_add_wildcard_to_directories(p) for p in ignore_patterns]

    if key is None:

        def _identity(item: T) -> str:
            if isinstance(item, str):
                return item
            if isinstance(item, Path):
                return str(item)
            raise ValueError(f"Please provide `key` argument in `filter_repo_objects`: `{item}` is not a string.")

        key = _identity  # Items must be `str` or `Path`, otherwise raise ValueError

    for item in items:
        path = key(item)

        # Skip if there's an allowlist and path doesn't match any
        if allow_patterns is not None and not any(fnmatch(path, r) for r in allow_patterns):
            continue

        # Skip if there's a denylist and path matches any
        if ignore_patterns is not None and any(fnmatch(path, r) for r in ignore_patterns):
            continue

        yield item


def _add_wildcard_to_directories(pattern: str) -> str:
    if pattern[-1] == "/":
        return pattern + "*"
    return pattern

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\prompts.py ===
"""Terminal input and output prompts."""

from pygments.token import Token
import sys

from IPython.core.displayhook import DisplayHook

from prompt_toolkit.formatted_text import fragment_list_width, PygmentsTokens
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.enums import EditingMode


class Prompts:
    def __init__(self, shell):
        self.shell = shell

    def vi_mode(self):
        if (getattr(self.shell.pt_app, 'editing_mode', None) == EditingMode.VI
                and self.shell.prompt_includes_vi_mode):
            mode = str(self.shell.pt_app.app.vi_state.input_mode)
            if mode.startswith('InputMode.'):
                mode = mode[10:13].lower()
            elif mode.startswith('vi-'):
                mode = mode[3:6]
            return '['+mode+'] '
        return ''

    def current_line(self) -> int:
        if self.shell.pt_app is not None:
            return self.shell.pt_app.default_buffer.document.cursor_position_row or 0
        return 0

    def in_prompt_tokens(self):
        return [
            (Token.Prompt.Mode, self.vi_mode()),
            (
                Token.Prompt.LineNumber,
                self.shell.prompt_line_number_format.format(
                    line=1, rel_line=-self.current_line()
                ),
            ),
            (Token.Prompt, "In ["),
            (Token.PromptNum, str(self.shell.execution_count)),
            (Token.Prompt, ']: '),
        ]

    def _width(self):
        return fragment_list_width(self.in_prompt_tokens())

    def continuation_prompt_tokens(
        self,
        width: int | None = None,
        *,
        lineno: int | None = None,
        wrap_count: int | None = None,
    ):
        if width is None:
            width = self._width()
        line = lineno + 1 if lineno is not None else 0
        if wrap_count:
            return [
                (
                    Token.Prompt.Wrap,
                    # (" " * (width - 2)) + "\N{HORIZONTAL ELLIPSIS} ",
                    (" " * (width - 2)) + "\N{VERTICAL ELLIPSIS} ",
                ),
            ]
        prefix = " " * len(
            self.vi_mode()
        ) + self.shell.prompt_line_number_format.format(
            line=line, rel_line=line - self.current_line() - 1
        )
        return [
            (
                getattr(Token.Prompt.Continuation, f"L{lineno}"),
                prefix + (" " * (width - len(prefix) - 5)) + "...:",
            ),
            (Token.Prompt.Padding, " "),
        ]

    def rewrite_prompt_tokens(self):
        width = self._width()
        return [
            (Token.Prompt, ('-' * (width - 2)) + '> '),
        ]

    def out_prompt_tokens(self):
        return [
            (Token.OutPrompt, 'Out['),
            (Token.OutPromptNum, str(self.shell.execution_count)),
            (Token.OutPrompt, ']: '),
        ]

class ClassicPrompts(Prompts):
    def in_prompt_tokens(self):
        return [
            (Token.Prompt, '>>> '),
        ]

    def continuation_prompt_tokens(self, width=None):
        return [(Token.Prompt.Continuation, "... ")]

    def rewrite_prompt_tokens(self):
        return []

    def out_prompt_tokens(self):
        return []

class RichPromptDisplayHook(DisplayHook):
    """Subclass of base display hook using coloured prompt"""
    def write_output_prompt(self):
        sys.stdout.write(self.shell.separate_out)
        # If we're not displaying a prompt, it effectively ends with a newline,
        # because the output will be left-aligned.
        self.prompt_end_newline = True

        if self.do_full_cache:
            tokens = self.shell.prompts.out_prompt_tokens()
            prompt_txt = "".join(s for _, s in tokens)
            if prompt_txt and not prompt_txt.endswith("\n"):
                # Ask for a newline before multiline output
                self.prompt_end_newline = False

            if self.shell.pt_app:
                print_formatted_text(PygmentsTokens(tokens),
                    style=self.shell.pt_app.app.style, end='',
                )
            else:
                sys.stdout.write(prompt_txt)

    def write_format_data(self, format_dict, md_dict=None) -> None:
        assert self.shell is not None
        if self.shell.mime_renderers:

            for mime, handler in self.shell.mime_renderers.items():
                if mime in format_dict:
                    handler(format_dict[mime], None)
                    return
                
        super().write_format_data(format_dict, md_dict)


# === NexusCore/openenv\Lib\site-packages\IPython\extensions\deduperreload\deduperreload_patching.py ===
from __future__ import annotations
import ctypes
import sys
from typing import Any

NOT_FOUND: object = object()
_MAX_FIELD_SEARCH_OFFSET = 50

if sys.maxsize > 2**32:
    WORD_TYPE: type[ctypes.c_int32] | type[ctypes.c_int64] = ctypes.c_int64
    WORD_N_BYTES = 8
else:
    WORD_TYPE = ctypes.c_int32
    WORD_N_BYTES = 4


class DeduperReloaderPatchingMixin:
    @staticmethod
    def infer_field_offset(
        obj: object,
        field: str,
    ) -> int:
        field_value = getattr(obj, field, NOT_FOUND)
        if field_value is NOT_FOUND:
            return -1
        obj_addr = ctypes.c_void_p.from_buffer(ctypes.py_object(obj)).value
        field_addr = ctypes.c_void_p.from_buffer(ctypes.py_object(field_value)).value
        if obj_addr is None or field_addr is None:
            return -1
        ret = -1
        for offset in range(1, _MAX_FIELD_SEARCH_OFFSET):
            if (
                ctypes.cast(
                    obj_addr + WORD_N_BYTES * offset, ctypes.POINTER(WORD_TYPE)
                ).contents.value
                == field_addr
            ):
                ret = offset
                break
        return ret

    @classmethod
    def try_write_readonly_attr(
        cls,
        obj: object,
        field: str,
        new_value: object,
        offset: int | None = None,
    ) -> None:
        prev_value = getattr(obj, field, NOT_FOUND)
        if prev_value is NOT_FOUND:
            return
        if offset is None:
            offset = cls.infer_field_offset(obj, field)
        if offset == -1:
            return
        obj_addr = ctypes.c_void_p.from_buffer(ctypes.py_object(obj)).value
        new_value_addr = ctypes.c_void_p.from_buffer(ctypes.py_object(new_value)).value
        if obj_addr is None or new_value_addr is None:
            return
        if prev_value is not None:
            ctypes.pythonapi.Py_DecRef(ctypes.py_object(prev_value))
        if new_value is not None:
            ctypes.pythonapi.Py_IncRef(ctypes.py_object(new_value))
        ctypes.cast(
            obj_addr + WORD_N_BYTES * offset, ctypes.POINTER(WORD_TYPE)
        ).contents.value = new_value_addr

    @classmethod
    def try_patch_readonly_attr(
        cls,
        old: object,
        new: object,
        field: str,
        new_is_value: bool = False,
        offset: int = -1,
    ) -> None:

        old_value = getattr(old, field, NOT_FOUND)
        new_value = new if new_is_value else getattr(new, field, NOT_FOUND)
        if old_value is NOT_FOUND or new_value is NOT_FOUND:
            return
        elif old_value is new_value:
            return
        elif old_value is not None and offset < 0:
            offset = cls.infer_field_offset(old, field)
        elif offset < 0:
            assert not new_is_value
            assert new_value is not None
            offset = cls.infer_field_offset(new, field)
        cls.try_write_readonly_attr(old, field, new_value, offset=offset)

    @classmethod
    def try_patch_attr(
        cls,
        old: object,
        new: object,
        field: str,
        new_is_value: bool = False,
        offset: int = -1,
    ) -> None:
        try:
            setattr(old, field, new if new_is_value else getattr(new, field))
        except (AttributeError, TypeError, ValueError):
            cls.try_patch_readonly_attr(old, new, field, new_is_value, offset)

    @classmethod
    def patch_function(
        cls, to_patch_to: Any, to_patch_from: Any, is_method: bool
    ) -> None:
        new_freevars = []
        new_closure = []
        for i, v in enumerate(to_patch_to.__code__.co_freevars):
            if v not in to_patch_from.__code__.co_freevars or v == "__class__":
                new_freevars.append(v)
                new_closure.append(to_patch_to.__closure__[i])
        for i, v in enumerate(to_patch_from.__code__.co_freevars):
            if v not in new_freevars:
                new_freevars.append(v)
                new_closure.append(to_patch_from.__closure__[i])
        code_with_new_freevars = to_patch_from.__code__.replace(
            co_freevars=tuple(new_freevars)
        )
        # lambdas may complain if there is more than one freevar
        cls.try_patch_attr(
            to_patch_to, code_with_new_freevars, "__code__", new_is_value=True
        )
        offset = -1
        if to_patch_to.__closure__ is None and to_patch_from.__closure__ is not None:
            offset = cls.infer_field_offset(to_patch_from, "__closure__")
        cls.try_patch_readonly_attr(
            to_patch_to,
            tuple(new_closure) or None,
            "__closure__",
            new_is_value=True,
            offset=offset,
        )
        for attr in ("__defaults__", "__kwdefaults__", "__doc__", "__dict__"):
            cls.try_patch_attr(to_patch_to, to_patch_from, attr)
        if is_method:
            cls.try_patch_readonly_attr(to_patch_to, to_patch_from, "__self__")

# === NexusCore/openenv\Lib\site-packages\litellm\llms\infinity\embedding\transformation.py ===
from typing import List, Optional, Union

import httpx

from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.llms.base_llm.embedding.transformation import BaseEmbeddingConfig
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllEmbeddingInputValues, AllMessageValues
from litellm.types.utils import EmbeddingResponse, Usage

from ..common_utils import InfinityError


class InfinityEmbeddingConfig(BaseEmbeddingConfig):
    """
    Reference: https://infinity.modal.michaelfeil.eu/docs
    """

    def __init__(self) -> None:
        pass

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        if api_base is None:
            raise ValueError("api_base is required for Infinity embeddings")
        # Remove trailing slashes and ensure clean base URL
        api_base = api_base.rstrip("/")
        if not api_base.endswith("/embeddings"):
            api_base = f"{api_base}/embeddings"
        return api_base

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
        if api_key is None:
            api_key = get_secret_str("INFINITY_API_KEY")

        default_headers = {
            "Authorization": f"Bearer {api_key}",
            "accept": "application/json",
            "Content-Type": "application/json",
        }

        # If 'Authorization' is provided in headers, it overrides the default.
        if "Authorization" in headers:
            default_headers["Authorization"] = headers["Authorization"]

        # Merge other headers, overriding any default ones except Authorization
        return {**default_headers, **headers}

    def get_supported_openai_params(self, model: str) -> list:
        return [
            "encoding_format",
            "modality",
            "dimensions",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        """
        Map OpenAI params to Infinity params

        Reference: https://infinity.modal.michaelfeil.eu/docs
        """
        if "encoding_format" in non_default_params:
            optional_params["encoding_format"] = non_default_params["encoding_format"]
        if "modality" in non_default_params:
            optional_params["modality"] = non_default_params["modality"]
        if "dimensions" in non_default_params:
            optional_params["output_dimension"] = non_default_params["dimensions"]
        return optional_params

    def transform_embedding_request(
        self,
        model: str,
        input: AllEmbeddingInputValues,
        optional_params: dict,
        headers: dict,
    ) -> dict:
        return {
            "input": input,
            "model": model,
            **optional_params,
        }

    def transform_embedding_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: EmbeddingResponse,
        logging_obj: LiteLLMLoggingObj,
        api_key: Optional[str] = None,
        request_data: dict = {},
        optional_params: dict = {},
        litellm_params: dict = {},
    ) -> EmbeddingResponse:
        try:
            raw_response_json = raw_response.json()
        except Exception:
            raise InfinityError(
                message=raw_response.text, status_code=raw_response.status_code
            )

        # model_response.usage
        model_response.model = raw_response_json.get("model")
        model_response.data = raw_response_json.get("data")
        model_response.object = raw_response_json.get("object")

        usage = Usage(
            prompt_tokens=raw_response_json.get("usage", {}).get("prompt_tokens", 0),
            total_tokens=raw_response_json.get("usage", {}).get("total_tokens", 0),
        )
        model_response.usage = usage
        return model_response

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return InfinityError(
            message=error_message, status_code=status_code, headers=headers
        )

# === NexusCore/openenv\Lib\site-packages\litellm\types\integrations\rag\bedrock_knowledgebase.py ===
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union


class BedrockKBLocation(TypedDict, total=False):
    """Location information for a retrieved document."""

    type: str
    s3Location: Optional[dict]
    webLocation: Optional[dict]
    kendraDocumentLocation: Optional[dict]
    salesforceLocation: Optional[dict]
    sharePointLocation: Optional[dict]
    confluenceLocation: Optional[dict]
    customDocumentLocation: Optional[dict]
    sqlLocation: Optional[dict]


class BedrockKBRowValue(TypedDict):
    """Row value in a retrieved document."""

    columnName: str
    columnValue: str
    type: str


class BedrockKBContent(TypedDict, total=False):
    """Content of a retrieved document."""

    type: str
    text: Optional[str]
    byteContent: Optional[str]
    row: Optional[List[BedrockKBRowValue]]


class BedrockKBRetrievalResult(TypedDict, total=False):
    """Individual result from a knowledge base retrieval."""

    content: Optional[BedrockKBContent]
    location: Optional[BedrockKBLocation]
    score: Optional[float]
    metadata: Optional[Dict[str, Any]]


class BedrockKBResponse(TypedDict, total=False):
    """Response from a Bedrock Knowledge Base retrieval request."""

    guardrailAction: Optional[Literal["INTERVENED", "NONE"]]
    nextToken: Optional[str]
    retrievalResults: Optional[List[BedrockKBRetrievalResult]]


################ Bedrock Knowledge Base Request Types #################
#########################################################################
#########################################################################


class BedrockKBMetadataAttribute(TypedDict, total=False):
    """Metadata attribute configuration for implicit filtering."""

    description: Optional[str]
    key: Optional[str]
    type: Optional[str]


class BedrockKBImplicitFilterConfiguration(TypedDict, total=False):
    """Configuration for implicit filtering."""

    metadataAttributes: Optional[List[BedrockKBMetadataAttribute]]
    modelArn: Optional[str]


class BedrockKBSelectiveModeConfiguration(TypedDict, total=False):
    """Configuration for selective mode in reranking."""

    pass  # This can be expanded based on actual requirements


class BedrockKBMetadataConfiguration(TypedDict, total=False):
    """Metadata configuration for reranking."""

    selectionMode: Optional[str]
    selectiveModeConfiguration: Optional[BedrockKBSelectiveModeConfiguration]


class BedrockKBModelConfiguration(TypedDict, total=False):
    """Model configuration for reranking."""

    additionalModelRequestFields: Optional[Dict[str, Any]]
    modelArn: Optional[str]


class BedrockKBRerankingConfiguration(TypedDict, total=False):
    """Configuration for reranking in vector search."""

    bedrockRerankingConfiguration: Optional[
        Dict[str, Any]
    ]  # This could be further typed if needed
    type: Optional[str]


class BedrockKBVectorSearchConfiguration(TypedDict, total=False):
    """Configuration for vector search."""

    filter: Optional[Dict[str, Any]]
    implicitFilterConfiguration: Optional[BedrockKBImplicitFilterConfiguration]
    numberOfResults: Optional[int]
    overrideSearchType: Optional[str]
    rerankingConfiguration: Optional[BedrockKBRerankingConfiguration]


class BedrockKBRetrievalConfiguration(TypedDict, total=False):
    """Configuration for retrieval."""

    vectorSearchConfiguration: Optional[BedrockKBVectorSearchConfiguration]


class BedrockKBRetrievalQuery(TypedDict, total=False):
    """Query structure for retrieval."""

    text: Optional[str]


class BedrockKBGuardrailConfiguration(TypedDict, total=False):
    """Configuration for guardrails."""

    guardrailId: Optional[str]
    guardrailVersion: Optional[str]


class BedrockKBRequest(TypedDict, total=False):
    """Complete request structure for Bedrock Knowledge Base retrieval."""

    guardrailConfiguration: Optional[BedrockKBGuardrailConfiguration]
    nextToken: Optional[str]
    retrievalConfiguration: Optional[BedrockKBRetrievalConfiguration]
    retrievalQuery: BedrockKBRetrievalQuery


#########################################################################
#########################################################################
#########################################################################

# === NexusCore/openenv\Lib\site-packages\nltk\lm\models.py ===
# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
#         Manu Joseph <manujosephv@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Language Models"""

from nltk.lm.api import LanguageModel, Smoothing
from nltk.lm.smoothing import AbsoluteDiscounting, KneserNey, WittenBell


class MLE(LanguageModel):
    """Class for providing MLE ngram model scores.

    Inherits initialization from BaseNgramModel.
    """

    def unmasked_score(self, word, context=None):
        """Returns the MLE score for a word given a context.

        Args:
        - word is expected to be a string
        - context is expected to be something reasonably convertible to a tuple
        """
        return self.context_counts(context).freq(word)


class Lidstone(LanguageModel):
    """Provides Lidstone-smoothed scores.

    In addition to initialization arguments from BaseNgramModel also requires
    a number by which to increase the counts, gamma.
    """

    def __init__(self, gamma, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gamma = gamma

    def unmasked_score(self, word, context=None):
        """Add-one smoothing: Lidstone or Laplace.

        To see what kind, look at `gamma` attribute on the class.

        """
        counts = self.context_counts(context)
        word_count = counts[word]
        norm_count = counts.N()
        return (word_count + self.gamma) / (norm_count + len(self.vocab) * self.gamma)


class Laplace(Lidstone):
    """Implements Laplace (add one) smoothing.

    Initialization identical to BaseNgramModel because gamma is always 1.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(1, *args, **kwargs)


class StupidBackoff(LanguageModel):
    """Provides StupidBackoff scores.

    In addition to initialization arguments from BaseNgramModel also requires
    a parameter alpha with which we scale the lower order probabilities.
    Note that this is not a true probability distribution as scores for ngrams
    of the same order do not sum up to unity.
    """

    def __init__(self, alpha=0.4, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alpha = alpha

    def unmasked_score(self, word, context=None):
        if not context:
            # Base recursion
            return self.counts.unigrams.freq(word)
        counts = self.context_counts(context)
        word_count = counts[word]
        norm_count = counts.N()
        if word_count > 0:
            return word_count / norm_count
        else:
            return self.alpha * self.unmasked_score(word, context[1:])


class InterpolatedLanguageModel(LanguageModel):
    """Logic common to all interpolated language models.

    The idea to abstract this comes from Chen & Goodman 1995.
    Do not instantiate this class directly!
    """

    def __init__(self, smoothing_cls, order, **kwargs):
        params = kwargs.pop("params", {})
        super().__init__(order, **kwargs)
        self.estimator = smoothing_cls(self.vocab, self.counts, **params)

    def unmasked_score(self, word, context=None):
        if not context:
            # The base recursion case: no context, we only have a unigram.
            return self.estimator.unigram_score(word)
        if not self.counts[context]:
            # It can also happen that we have no data for this context.
            # In that case we defer to the lower-order ngram.
            # This is the same as setting alpha to 0 and gamma to 1.
            alpha, gamma = 0, 1
        else:
            alpha, gamma = self.estimator.alpha_gamma(word, context)
        return alpha + gamma * self.unmasked_score(word, context[1:])


class WittenBellInterpolated(InterpolatedLanguageModel):
    """Interpolated version of Witten-Bell smoothing."""

    def __init__(self, order, **kwargs):
        super().__init__(WittenBell, order, **kwargs)


class AbsoluteDiscountingInterpolated(InterpolatedLanguageModel):
    """Interpolated version of smoothing with absolute discount."""

    def __init__(self, order, discount=0.75, **kwargs):
        super().__init__(
            AbsoluteDiscounting, order, params={"discount": discount}, **kwargs
        )


class KneserNeyInterpolated(InterpolatedLanguageModel):
    """Interpolated version of Kneser-Ney smoothing."""

    def __init__(self, order, discount=0.1, **kwargs):
        if not (0 <= discount <= 1):
            raise ValueError(
                "Discount must be between 0 and 1 for probabilities to sum to unity."
            )
        super().__init__(
            KneserNey, order, params={"discount": discount, "order": order}, **kwargs
        )

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\padding.py ===
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from .console import (
        Console,
        ConsoleOptions,
        RenderableType,
        RenderResult,
    )

from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style

PaddingDimensions = Union[int, Tuple[int], Tuple[int, int], Tuple[int, int, int, int]]


class Padding(JupyterMixin):
    """Draw space around content.

    Example:
        >>> print(Padding("Hello", (2, 4), style="on blue"))

    Args:
        renderable (RenderableType): String or other renderable.
        pad (Union[int, Tuple[int]]): Padding for top, right, bottom, and left borders.
            May be specified with 1, 2, or 4 integers (CSS style).
        style (Union[str, Style], optional): Style for padding characters. Defaults to "none".
        expand (bool, optional): Expand padding to fit available width. Defaults to True.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        pad: "PaddingDimensions" = (0, 0, 0, 0),
        *,
        style: Union[str, Style] = "none",
        expand: bool = True,
    ):
        self.renderable = renderable
        self.top, self.right, self.bottom, self.left = self.unpack(pad)
        self.style = style
        self.expand = expand

    @classmethod
    def indent(cls, renderable: "RenderableType", level: int) -> "Padding":
        """Make padding instance to render an indent.

        Args:
            renderable (RenderableType): String or other renderable.
            level (int): Number of characters to indent.

        Returns:
            Padding: A Padding instance.
        """

        return Padding(renderable, pad=(0, 0, 0, level), expand=False)

    @staticmethod
    def unpack(pad: "PaddingDimensions") -> Tuple[int, int, int, int]:
        """Unpack padding specified in CSS style."""
        if isinstance(pad, int):
            return (pad, pad, pad, pad)
        if len(pad) == 1:
            _pad = pad[0]
            return (_pad, _pad, _pad, _pad)
        if len(pad) == 2:
            pad_top, pad_right = pad
            return (pad_top, pad_right, pad_top, pad_right)
        if len(pad) == 4:
            top, right, bottom, left = pad
            return (top, right, bottom, left)
        raise ValueError(f"1, 2 or 4 integers required for padding; {len(pad)} given")

    def __repr__(self) -> str:
        return f"Padding({self.renderable!r}, ({self.top},{self.right},{self.bottom},{self.left}))"

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        style = console.get_style(self.style)
        if self.expand:
            width = options.max_width
        else:
            width = min(
                Measurement.get(console, options, self.renderable).maximum
                + self.left
                + self.right,
                options.max_width,
            )
        render_options = options.update_width(width - self.left - self.right)
        if render_options.height is not None:
            render_options = render_options.update_height(
                height=render_options.height - self.top - self.bottom
            )
        lines = console.render_lines(
            self.renderable, render_options, style=style, pad=True
        )
        _Segment = Segment

        left = _Segment(" " * self.left, style) if self.left else None
        right = (
            [_Segment(f'{" " * self.right}', style), _Segment.line()]
            if self.right
            else [_Segment.line()]
        )
        blank_line: Optional[List[Segment]] = None
        if self.top:
            blank_line = [_Segment(f'{" " * width}\n', style)]
            yield from blank_line * self.top
        if left:
            for line in lines:
                yield left
                yield from line
                yield from right
        else:
            for line in lines:
                yield from line
                yield from right
        if self.bottom:
            blank_line = blank_line or [_Segment(f'{" " * width}\n', style)]
            yield from blank_line * self.bottom

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        max_width = options.max_width
        extra_width = self.left + self.right
        if max_width - extra_width < 1:
            return Measurement(max_width, max_width)
        measure_min, measure_max = Measurement.get(console, options, self.renderable)
        measurement = Measurement(measure_min + extra_width, measure_max + extra_width)
        measurement = measurement.with_maximum(max_width)
        return measurement


if __name__ == "__main__":  #  pragma: no cover
    from pip._vendor.rich import print

    print(Padding("Hello, World", (2, 4), style="on blue"))

# === NexusCore/openenv\Lib\site-packages\pydantic\deprecated\json.py ===
import datetime
import warnings
from collections import deque
from decimal import Decimal
from enum import Enum
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from pathlib import Path
from re import Pattern
from types import GeneratorType
from typing import TYPE_CHECKING, Any, Callable, Union
from uuid import UUID

from typing_extensions import deprecated

from .._internal._import_utils import import_cached_base_model
from ..color import Color
from ..networks import NameEmail
from ..types import SecretBytes, SecretStr
from ..warnings import PydanticDeprecatedSince20

if not TYPE_CHECKING:
    # See PyCharm issues https://youtrack.jetbrains.com/issue/PY-21915
    # and https://youtrack.jetbrains.com/issue/PY-51428
    DeprecationWarning = PydanticDeprecatedSince20

__all__ = 'pydantic_encoder', 'custom_pydantic_encoder', 'timedelta_isoformat'


def isoformat(o: Union[datetime.date, datetime.time]) -> str:
    return o.isoformat()


def decimal_encoder(dec_value: Decimal) -> Union[int, float]:
    """Encodes a Decimal as int of there's no exponent, otherwise float.

    This is useful when we use ConstrainedDecimal to represent Numeric(x,0)
    where a integer (but not int typed) is used. Encoding this as a float
    results in failed round-tripping between encode and parse.
    Our Id type is a prime example of this.

    >>> decimal_encoder(Decimal("1.0"))
    1.0

    >>> decimal_encoder(Decimal("1"))
    1
    """
    exponent = dec_value.as_tuple().exponent
    if isinstance(exponent, int) and exponent >= 0:
        return int(dec_value)
    else:
        return float(dec_value)


ENCODERS_BY_TYPE: dict[type[Any], Callable[[Any], Any]] = {
    bytes: lambda o: o.decode(),
    Color: str,
    datetime.date: isoformat,
    datetime.datetime: isoformat,
    datetime.time: isoformat,
    datetime.timedelta: lambda td: td.total_seconds(),
    Decimal: decimal_encoder,
    Enum: lambda o: o.value,
    frozenset: list,
    deque: list,
    GeneratorType: list,
    IPv4Address: str,
    IPv4Interface: str,
    IPv4Network: str,
    IPv6Address: str,
    IPv6Interface: str,
    IPv6Network: str,
    NameEmail: str,
    Path: str,
    Pattern: lambda o: o.pattern,
    SecretBytes: str,
    SecretStr: str,
    set: list,
    UUID: str,
}


@deprecated(
    '`pydantic_encoder` is deprecated, use `pydantic_core.to_jsonable_python` instead.',
    category=None,
)
def pydantic_encoder(obj: Any) -> Any:
    warnings.warn(
        '`pydantic_encoder` is deprecated, use `pydantic_core.to_jsonable_python` instead.',
        category=PydanticDeprecatedSince20,
        stacklevel=2,
    )
    from dataclasses import asdict, is_dataclass

    BaseModel = import_cached_base_model()

    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif is_dataclass(obj):
        return asdict(obj)  # type: ignore

    # Check the class type and its superclasses for a matching encoder
    for base in obj.__class__.__mro__[:-1]:
        try:
            encoder = ENCODERS_BY_TYPE[base]
        except KeyError:
            continue
        return encoder(obj)
    else:  # We have exited the for loop without finding a suitable encoder
        raise TypeError(f"Object of type '{obj.__class__.__name__}' is not JSON serializable")


# TODO: Add a suggested migration path once there is a way to use custom encoders
@deprecated(
    '`custom_pydantic_encoder` is deprecated, use `BaseModel.model_dump` instead.',
    category=None,
)
def custom_pydantic_encoder(type_encoders: dict[Any, Callable[[type[Any]], Any]], obj: Any) -> Any:
    warnings.warn(
        '`custom_pydantic_encoder` is deprecated, use `BaseModel.model_dump` instead.',
        category=PydanticDeprecatedSince20,
        stacklevel=2,
    )
    # Check the class type and its superclasses for a matching encoder
    for base in obj.__class__.__mro__[:-1]:
        try:
            encoder = type_encoders[base]
        except KeyError:
            continue

        return encoder(obj)
    else:  # We have exited the for loop without finding a suitable encoder
        return pydantic_encoder(obj)


@deprecated('`timedelta_isoformat` is deprecated.', category=None)
def timedelta_isoformat(td: datetime.timedelta) -> str:
    """ISO 8601 encoding for Python timedelta object."""
    warnings.warn('`timedelta_isoformat` is deprecated.', category=PydanticDeprecatedSince20, stacklevel=2)
    minutes, seconds = divmod(td.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{"-" if td.days < 0 else ""}P{abs(td.days)}DT{hours:d}H{minutes:d}M{seconds:d}.{td.microseconds:06d}S'

# === NexusCore/openenv\Lib\site-packages\setuptools\command\setopt.py ===
import configparser
import os

from .. import Command
from ..unicode_utils import _cfg_read_utf8_with_fallback

import distutils
from distutils import log
from distutils.errors import DistutilsOptionError
from distutils.util import convert_path

__all__ = ['config_file', 'edit_config', 'option_base', 'setopt']


def config_file(kind="local"):
    """Get the filename of the distutils, local, global, or per-user config

    `kind` must be one of "local", "global", or "user"
    """
    if kind == 'local':
        return 'setup.cfg'
    if kind == 'global':
        return os.path.join(os.path.dirname(distutils.__file__), 'distutils.cfg')
    if kind == 'user':
        dot = os.name == 'posix' and '.' or ''
        return os.path.expanduser(convert_path(f"~/{dot}pydistutils.cfg"))
    raise ValueError("config_file() type must be 'local', 'global', or 'user'", kind)


def edit_config(filename, settings, dry_run=False):
    """Edit a configuration file to include `settings`

    `settings` is a dictionary of dictionaries or ``None`` values, keyed by
    command/section name.  A ``None`` value means to delete the entire section,
    while a dictionary lists settings to be changed or deleted in that section.
    A setting of ``None`` means to delete that setting.
    """
    log.debug("Reading configuration from %s", filename)
    opts = configparser.RawConfigParser()
    opts.optionxform = lambda optionstr: optionstr  # type: ignore[method-assign] # overriding method
    _cfg_read_utf8_with_fallback(opts, filename)

    for section, options in settings.items():
        if options is None:
            log.info("Deleting section [%s] from %s", section, filename)
            opts.remove_section(section)
        else:
            if not opts.has_section(section):
                log.debug("Adding new section [%s] to %s", section, filename)
                opts.add_section(section)
            for option, value in options.items():
                if value is None:
                    log.debug("Deleting %s.%s from %s", section, option, filename)
                    opts.remove_option(section, option)
                    if not opts.options(section):
                        log.info(
                            "Deleting empty [%s] section from %s", section, filename
                        )
                        opts.remove_section(section)
                else:
                    log.debug(
                        "Setting %s.%s to %r in %s", section, option, value, filename
                    )
                    opts.set(section, option, value)

    log.info("Writing %s", filename)
    if not dry_run:
        with open(filename, 'w', encoding="utf-8") as f:
            opts.write(f)


class option_base(Command):
    """Abstract base class for commands that mess with config files"""

    user_options = [
        ('global-config', 'g', "save options to the site-wide distutils.cfg file"),
        ('user-config', 'u', "save options to the current user's pydistutils.cfg file"),
        ('filename=', 'f', "configuration file to use (default=setup.cfg)"),
    ]

    boolean_options = [
        'global-config',
        'user-config',
    ]

    def initialize_options(self):
        self.global_config = None
        self.user_config = None
        self.filename = None

    def finalize_options(self):
        filenames = []
        if self.global_config:
            filenames.append(config_file('global'))
        if self.user_config:
            filenames.append(config_file('user'))
        if self.filename is not None:
            filenames.append(self.filename)
        if not filenames:
            filenames.append(config_file('local'))
        if len(filenames) > 1:
            raise DistutilsOptionError(
                "Must specify only one configuration file option", filenames
            )
        (self.filename,) = filenames


class setopt(option_base):
    """Save command-line options to a file"""

    description = "set an option in setup.cfg or another config file"

    user_options = [
        ('command=', 'c', 'command to set an option for'),
        ('option=', 'o', 'option to set'),
        ('set-value=', 's', 'value of the option'),
        ('remove', 'r', 'remove (unset) the value'),
    ] + option_base.user_options

    boolean_options = option_base.boolean_options + ['remove']

    def initialize_options(self):
        option_base.initialize_options(self)
        self.command = None
        self.option = None
        self.set_value = None
        self.remove = None

    def finalize_options(self) -> None:
        option_base.finalize_options(self)
        if self.command is None or self.option is None:
            raise DistutilsOptionError("Must specify --command *and* --option")
        if self.set_value is None and not self.remove:
            raise DistutilsOptionError("Must specify --set-value or --remove")

    def run(self) -> None:
        edit_config(
            self.filename,
            {self.command: {self.option.replace('-', '_'): self.set_value}},
            self.dry_run,
        )

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\command\bdist_dumb.py ===
"""distutils.command.bdist_dumb

Implements the Distutils 'bdist_dumb' command (create a "dumb" built
distribution -- i.e., just an archive to be unpacked under $prefix or
$exec_prefix)."""

import os
from distutils._log import log
from typing import ClassVar

from ..core import Command
from ..dir_util import ensure_relative, remove_tree
from ..errors import DistutilsPlatformError
from ..sysconfig import get_python_version
from ..util import get_platform


class bdist_dumb(Command):
    description = "create a \"dumb\" built distribution"

    user_options = [
        ('bdist-dir=', 'd', "temporary directory for creating the distribution"),
        (
            'plat-name=',
            'p',
            "platform name to embed in generated filenames "
            f"[default: {get_platform()}]",
        ),
        (
            'format=',
            'f',
            "archive format to create (tar, gztar, bztar, xztar, ztar, zip)",
        ),
        (
            'keep-temp',
            'k',
            "keep the pseudo-installation tree around after creating the distribution archive",
        ),
        ('dist-dir=', 'd', "directory to put final built distributions in"),
        ('skip-build', None, "skip rebuilding everything (for testing/debugging)"),
        (
            'relative',
            None,
            "build the archive using relative paths [default: false]",
        ),
        (
            'owner=',
            'u',
            "Owner name used when creating a tar file [default: current user]",
        ),
        (
            'group=',
            'g',
            "Group name used when creating a tar file [default: current group]",
        ),
    ]

    boolean_options: ClassVar[list[str]] = ['keep-temp', 'skip-build', 'relative']

    default_format = {'posix': 'gztar', 'nt': 'zip'}

    def initialize_options(self):
        self.bdist_dir = None
        self.plat_name = None
        self.format = None
        self.keep_temp = False
        self.dist_dir = None
        self.skip_build = None
        self.relative = False
        self.owner = None
        self.group = None

    def finalize_options(self):
        if self.bdist_dir is None:
            bdist_base = self.get_finalized_command('bdist').bdist_base
            self.bdist_dir = os.path.join(bdist_base, 'dumb')

        if self.format is None:
            try:
                self.format = self.default_format[os.name]
            except KeyError:
                raise DistutilsPlatformError(
                    "don't know how to create dumb built distributions "
                    f"on platform {os.name}"
                )

        self.set_undefined_options(
            'bdist',
            ('dist_dir', 'dist_dir'),
            ('plat_name', 'plat_name'),
            ('skip_build', 'skip_build'),
        )

    def run(self):
        if not self.skip_build:
            self.run_command('build')

        install = self.reinitialize_command('install', reinit_subcommands=True)
        install.root = self.bdist_dir
        install.skip_build = self.skip_build
        install.warn_dir = False

        log.info("installing to %s", self.bdist_dir)
        self.run_command('install')

        # And make an archive relative to the root of the
        # pseudo-installation tree.
        archive_basename = f"{self.distribution.get_fullname()}.{self.plat_name}"

        pseudoinstall_root = os.path.join(self.dist_dir, archive_basename)
        if not self.relative:
            archive_root = self.bdist_dir
        else:
            if self.distribution.has_ext_modules() and (
                install.install_base != install.install_platbase
            ):
                raise DistutilsPlatformError(
                    "can't make a dumb built distribution where "
                    f"base and platbase are different ({install.install_base!r}, {install.install_platbase!r})"
                )
            else:
                archive_root = os.path.join(
                    self.bdist_dir, ensure_relative(install.install_base)
                )

        # Make the archive
        filename = self.make_archive(
            pseudoinstall_root,
            self.format,
            root_dir=archive_root,
            owner=self.owner,
            group=self.group,
        )
        if self.distribution.has_ext_modules():
            pyversion = get_python_version()
        else:
            pyversion = 'any'
        self.distribution.dist_files.append(('bdist_dumb', pyversion, filename))

        if not self.keep_temp:
            remove_tree(self.bdist_dir, dry_run=self.dry_run)

# === NexusCore/openenv\Lib\site-packages\trio\_tests\type_tests\path.py ===
"""Path wrapping is quite complex, ensure all methods are understood as wrapped correctly."""

import io
import os
import pathlib
import sys
from typing import IO, Any, BinaryIO

import trio
from trio._file_io import AsyncIOWrapper
from typing_extensions import assert_type


def operator_checks(text: str, tpath: trio.Path, ppath: pathlib.Path) -> None:
    """Verify operators produce the right results."""
    assert_type(tpath / ppath, trio.Path)
    assert_type(tpath / tpath, trio.Path)
    assert_type(tpath / text, trio.Path)
    assert_type(text / tpath, trio.Path)

    assert_type(tpath > tpath, bool)
    assert_type(tpath >= tpath, bool)
    assert_type(tpath < tpath, bool)
    assert_type(tpath <= tpath, bool)

    assert_type(tpath > ppath, bool)
    assert_type(tpath >= ppath, bool)
    assert_type(tpath < ppath, bool)
    assert_type(tpath <= ppath, bool)

    assert_type(ppath > tpath, bool)
    assert_type(ppath >= tpath, bool)
    assert_type(ppath < tpath, bool)
    assert_type(ppath <= tpath, bool)


def sync_attrs(path: trio.Path) -> None:
    assert_type(path.parts, tuple[str, ...])
    assert_type(path.drive, str)
    assert_type(path.root, str)
    assert_type(path.anchor, str)
    assert_type(path.parents[3], trio.Path)
    assert_type(path.parent, trio.Path)
    assert_type(path.name, str)
    assert_type(path.suffix, str)
    assert_type(path.suffixes, list[str])
    assert_type(path.stem, str)
    assert_type(path.as_posix(), str)
    assert_type(path.as_uri(), str)
    assert_type(path.is_absolute(), bool)
    assert_type(path.is_relative_to(path), bool)
    assert_type(path.is_reserved(), bool)
    assert_type(path.joinpath(path, "folder"), trio.Path)
    assert_type(path.match("*.py"), bool)
    assert_type(path.relative_to("/usr"), trio.Path)
    if sys.version_info >= (3, 12):
        assert_type(path.relative_to("/", walk_up=True), trio.Path)
    assert_type(path.with_name("filename.txt"), trio.Path)
    assert_type(path.with_stem("readme"), trio.Path)
    assert_type(path.with_suffix(".log"), trio.Path)


async def async_attrs(path: trio.Path) -> None:
    assert_type(await trio.Path.cwd(), trio.Path)
    assert_type(await trio.Path.home(), trio.Path)
    assert_type(await path.stat(), os.stat_result)
    assert_type(await path.chmod(0o777), None)
    assert_type(await path.exists(), bool)
    assert_type(await path.expanduser(), trio.Path)
    for result in await path.glob("*.py"):
        assert_type(result, trio.Path)
    if sys.platform != "win32":
        assert_type(await path.group(), str)
    assert_type(await path.is_dir(), bool)
    assert_type(await path.is_file(), bool)
    if sys.version_info >= (3, 12):
        assert_type(await path.is_junction(), bool)
    if sys.platform != "win32":
        assert_type(await path.is_mount(), bool)
    assert_type(await path.is_symlink(), bool)
    assert_type(await path.is_socket(), bool)
    assert_type(await path.is_fifo(), bool)
    assert_type(await path.is_block_device(), bool)
    assert_type(await path.is_char_device(), bool)
    for child_iter in await path.iterdir():
        assert_type(child_iter, trio.Path)
    # TODO: Path.walk() in 3.12
    assert_type(await path.lchmod(0o111), None)
    assert_type(await path.lstat(), os.stat_result)
    assert_type(await path.mkdir(mode=0o777, parents=True, exist_ok=False), None)
    # Open done separately.
    if sys.platform != "win32":
        assert_type(await path.owner(), str)
    assert_type(await path.read_bytes(), bytes)
    assert_type(await path.read_text(encoding="utf16", errors="replace"), str)
    assert_type(await path.readlink(), trio.Path)
    assert_type(await path.rename("another"), trio.Path)
    assert_type(await path.replace(path), trio.Path)
    assert_type(await path.resolve(), trio.Path)
    for child_glob in await path.glob("*.py"):
        assert_type(child_glob, trio.Path)
    for child_rglob in await path.rglob("*.py"):
        assert_type(child_rglob, trio.Path)
    assert_type(await path.rmdir(), None)
    assert_type(await path.samefile("something_else"), bool)
    assert_type(await path.symlink_to("somewhere"), None)
    if sys.version_info >= (3, 10):
        assert_type(await path.hardlink_to("elsewhere"), None)
    assert_type(await path.touch(), None)
    assert_type(await path.unlink(missing_ok=True), None)
    assert_type(await path.write_bytes(b"123"), int)
    assert_type(
        await path.write_text("hello", encoding="utf32le", errors="ignore"),
        int,
    )


async def open_results(path: trio.Path, some_int: int, some_str: str) -> None:
    # Check the overloads.
    assert_type(await path.open(), AsyncIOWrapper[io.TextIOWrapper])
    assert_type(await path.open("r"), AsyncIOWrapper[io.TextIOWrapper])
    assert_type(await path.open("r+"), AsyncIOWrapper[io.TextIOWrapper])
    assert_type(await path.open("w"), AsyncIOWrapper[io.TextIOWrapper])
    assert_type(await path.open("rb", buffering=0), AsyncIOWrapper[io.FileIO])
    assert_type(await path.open("rb+"), AsyncIOWrapper[io.BufferedRandom])
    assert_type(await path.open("wb"), AsyncIOWrapper[io.BufferedWriter])
    assert_type(await path.open("rb"), AsyncIOWrapper[io.BufferedReader])
    assert_type(await path.open("rb", buffering=some_int), AsyncIOWrapper[BinaryIO])
    assert_type(await path.open(some_str), AsyncIOWrapper[IO[Any]])

    # Check they produce the right types.
    file_bin = await path.open("rb+")
    assert_type(await file_bin.read(), bytes)
    assert_type(await file_bin.write(b"test"), int)
    assert_type(await file_bin.seek(32), int)

    file_text = await path.open("r+t")
    assert_type(await file_text.read(), str)
    assert_type(await file_text.write("test"), int)
    # TODO: report mypy bug: equiv to https://github.com/microsoft/pyright/issues/6833
    assert_type(await file_text.readlines(), list[str])

# === NexusCore/openenv\Lib\site-packages\ipykernel\connect.py ===
"""Connection file-related utilities for the kernel
"""
# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import json
import sys
from subprocess import PIPE, Popen
from typing import TYPE_CHECKING, Any

import jupyter_client
from jupyter_client import write_connection_file

if TYPE_CHECKING:
    from ipykernel.kernelapp import IPKernelApp


def get_connection_file(app: IPKernelApp | None = None) -> str:
    """Return the path to the connection file of an app

    Parameters
    ----------
    app : IPKernelApp instance [optional]
        If unspecified, the currently running app will be used
    """
    from traitlets.utils import filefind

    if app is None:
        from ipykernel.kernelapp import IPKernelApp

        if not IPKernelApp.initialized():
            msg = "app not specified, and not in a running Kernel"
            raise RuntimeError(msg)

        app = IPKernelApp.instance()
    return filefind(app.connection_file, [".", app.connection_dir])


def _find_connection_file(connection_file):
    """Return the absolute path for a connection file

    - If nothing specified, return current Kernel's connection file
    - Otherwise, call jupyter_client.find_connection_file
    """
    if connection_file is None:
        # get connection file from current kernel
        return get_connection_file()
    return jupyter_client.find_connection_file(connection_file)


def get_connection_info(
    connection_file: str | None = None, unpack: bool = False
) -> str | dict[str, Any]:
    """Return the connection information for the current Kernel.

    Parameters
    ----------
    connection_file : str [optional]
        The connection file to be used. Can be given by absolute path, or
        IPython will search in the security directory.
        If run from IPython,

        If unspecified, the connection file for the currently running
        IPython Kernel will be used, which is only allowed from inside a kernel.

    unpack : bool [default: False]
        if True, return the unpacked dict, otherwise just the string contents
        of the file.

    Returns
    -------
    The connection dictionary of the current kernel, as string or dict,
    depending on `unpack`.
    """
    cf = _find_connection_file(connection_file)

    with open(cf) as f:
        info_str = f.read()

    if unpack:
        info = json.loads(info_str)
        # ensure key is bytes:
        info["key"] = info.get("key", "").encode()
        return info  # type:ignore[no-any-return]

    return info_str


def connect_qtconsole(
    connection_file: str | None = None, argv: list[str] | None = None
) -> Popen[Any]:
    """Connect a qtconsole to the current kernel.

    This is useful for connecting a second qtconsole to a kernel, or to a
    local notebook.

    Parameters
    ----------
    connection_file : str [optional]
        The connection file to be used. Can be given by absolute path, or
        IPython will search in the security directory.
        If run from IPython,

        If unspecified, the connection file for the currently running
        IPython Kernel will be used, which is only allowed from inside a kernel.

    argv : list [optional]
        Any extra args to be passed to the console.

    Returns
    -------
    :class:`subprocess.Popen` instance running the qtconsole frontend
    """
    argv = [] if argv is None else argv

    cf = _find_connection_file(connection_file)

    cmd = ";".join(["from qtconsole import qtconsoleapp", "qtconsoleapp.main()"])

    kwargs: dict[str, Any] = {}
    # Launch the Qt console in a separate session & process group, so
    # interrupting the kernel doesn't kill it.
    kwargs["start_new_session"] = True

    return Popen(
        [sys.executable, "-c", cmd, "--existing", cf, *argv],
        stdout=PIPE,
        stderr=PIPE,
        close_fds=(sys.platform != "win32"),
        **kwargs,
    )


__all__ = [
    "write_connection_file",
    "get_connection_file",
    "get_connection_info",
    "connect_qtconsole",
]

# === NexusCore/openenv\Lib\site-packages\matplotlib\mathtext.py ===
r"""
A module for parsing a subset of the TeX math syntax and rendering it to a
Matplotlib backend.

For a tutorial of its usage, see :ref:`mathtext`.  This
document is primarily concerned with implementation details.

The module uses pyparsing_ to parse the TeX expression.

.. _pyparsing: https://pypi.org/project/pyparsing/

The Bakoma distribution of the TeX Computer Modern fonts, and STIX
fonts are supported.  There is experimental support for using
arbitrary fonts, but results may vary without proper tweaking and
metrics for those fonts.
"""

import functools
import logging

import matplotlib as mpl
from matplotlib import _api, _mathtext
from matplotlib.ft2font import LoadFlags
from matplotlib.font_manager import FontProperties
from ._mathtext import (  # noqa: F401, reexported API
    RasterParse, VectorParse, get_unicode_index)

_log = logging.getLogger(__name__)


get_unicode_index.__module__ = __name__

##############################################################################
# MAIN


class MathTextParser:
    _parser = None
    _font_type_mapping = {
        'cm':          _mathtext.BakomaFonts,
        'dejavuserif': _mathtext.DejaVuSerifFonts,
        'dejavusans':  _mathtext.DejaVuSansFonts,
        'stix':        _mathtext.StixFonts,
        'stixsans':    _mathtext.StixSansFonts,
        'custom':      _mathtext.UnicodeFonts,
    }

    def __init__(self, output):
        """
        Create a MathTextParser for the given backend *output*.

        Parameters
        ----------
        output : {"path", "agg"}
            Whether to return a `VectorParse` ("path") or a
            `RasterParse` ("agg", or its synonym "macosx").
        """
        self._output_type = _api.check_getitem(
            {"path": "vector", "agg": "raster", "macosx": "raster"},
            output=output.lower())

    def parse(self, s, dpi=72, prop=None, *, antialiased=None):
        """
        Parse the given math expression *s* at the given *dpi*.  If *prop* is
        provided, it is a `.FontProperties` object specifying the "default"
        font to use in the math expression, used for all non-math text.

        The results are cached, so multiple calls to `parse`
        with the same expression should be fast.

        Depending on the *output* type, this returns either a `VectorParse` or
        a `RasterParse`.
        """
        # lru_cache can't decorate parse() directly because prop is
        # mutable, so we key the cache using an internal copy (see
        # Text._get_text_metrics_with_cache for a similar case); likewise,
        # we need to check the mutable state of the text.antialiased and
        # text.hinting rcParams.
        prop = prop.copy() if prop is not None else None
        antialiased = mpl._val_or_rc(antialiased, 'text.antialiased')
        from matplotlib.backends import backend_agg
        load_glyph_flags = {
            "vector": LoadFlags.NO_HINTING,
            "raster": backend_agg.get_hinting_flag(),
        }[self._output_type]
        return self._parse_cached(s, dpi, prop, antialiased, load_glyph_flags)

    @functools.lru_cache(50)
    def _parse_cached(self, s, dpi, prop, antialiased, load_glyph_flags):
        if prop is None:
            prop = FontProperties()
        fontset_class = _api.check_getitem(
            self._font_type_mapping, fontset=prop.get_math_fontfamily())
        fontset = fontset_class(prop, load_glyph_flags)
        fontsize = prop.get_size_in_points()

        if self._parser is None:  # Cache the parser globally.
            self.__class__._parser = _mathtext.Parser()

        box = self._parser.parse(s, fontset, fontsize, dpi)
        output = _mathtext.ship(box)
        if self._output_type == "vector":
            return output.to_vector()
        elif self._output_type == "raster":
            return output.to_raster(antialiased=antialiased)


def math_to_image(s, filename_or_obj, prop=None, dpi=None, format=None,
                  *, color=None):
    """
    Given a math expression, renders it in a closely-clipped bounding
    box to an image file.

    Parameters
    ----------
    s : str
        A math expression.  The math portion must be enclosed in dollar signs.
    filename_or_obj : str or path-like or file-like
        Where to write the image data.
    prop : `.FontProperties`, optional
        The size and style of the text.
    dpi : float, optional
        The output dpi.  If not set, the dpi is determined as for
        `.Figure.savefig`.
    format : str, optional
        The output format, e.g., 'svg', 'pdf', 'ps' or 'png'.  If not set, the
        format is determined as for `.Figure.savefig`.
    color : str, optional
        Foreground color, defaults to :rc:`text.color`.
    """
    from matplotlib import figure

    parser = MathTextParser('path')
    width, height, depth, _, _ = parser.parse(s, dpi=72, prop=prop)

    fig = figure.Figure(figsize=(width / 72.0, height / 72.0))
    fig.text(0, depth/height, s, fontproperties=prop, color=color)
    fig.savefig(filename_or_obj, dpi=dpi, format=format)

    return depth

# === NexusCore/openenv\Lib\site-packages\pure_eval\my_getattr_static.py ===
import types

from pure_eval.utils import of_type, CannotEval

_sentinel = object()


def _static_getmro(klass):
    return type.__dict__['__mro__'].__get__(klass)


def _check_instance(obj, attr):
    instance_dict = {}
    try:
        instance_dict = object.__getattribute__(obj, "__dict__")
    except AttributeError:
        pass
    return dict.get(instance_dict, attr, _sentinel)


def _check_class(klass, attr):
    for entry in _static_getmro(klass):
        if _shadowed_dict(type(entry)) is _sentinel:
            try:
                return entry.__dict__[attr]
            except KeyError:
                pass
        else:
            break
    return _sentinel


def _is_type(obj):
    try:
        _static_getmro(obj)
    except TypeError:
        return False
    return True


def _shadowed_dict(klass):
    dict_attr = type.__dict__["__dict__"]
    for entry in _static_getmro(klass):
        try:
            class_dict = dict_attr.__get__(entry)["__dict__"]
        except KeyError:
            pass
        else:
            if not (type(class_dict) is types.GetSetDescriptorType and
                    class_dict.__name__ == "__dict__" and
                    class_dict.__objclass__ is entry):
                return class_dict
    return _sentinel


def getattr_static(obj, attr):
    """Retrieve attributes without triggering dynamic lookup via the
       descriptor protocol,  __getattr__ or __getattribute__.

       Note: this function may not be able to retrieve all attributes
       that getattr can fetch (like dynamically created attributes)
       and may find attributes that getattr can't (like descriptors
       that raise AttributeError). It can also return descriptor objects
       instead of instance members in some cases. See the
       documentation for details.
    """
    instance_result = _sentinel
    if not _is_type(obj):
        klass = type(obj)
        dict_attr = _shadowed_dict(klass)
        if (dict_attr is _sentinel or
                type(dict_attr) is types.MemberDescriptorType):
            instance_result = _check_instance(obj, attr)
        else:
            raise CannotEval
    else:
        klass = obj

    klass_result = _check_class(klass, attr)

    if instance_result is not _sentinel and klass_result is not _sentinel:
        if _check_class(type(klass_result), "__get__") is not _sentinel and (
            _check_class(type(klass_result), "__set__") is not _sentinel
            or _check_class(type(klass_result), "__delete__") is not _sentinel
        ):
            return _resolve_descriptor(klass_result, obj, klass)

    if instance_result is not _sentinel:
        return instance_result
    if klass_result is not _sentinel:
        get = _check_class(type(klass_result), '__get__')
        if get is _sentinel:
            return klass_result
        else:
            if obj is klass:
                instance = None
            else:
                instance = obj
            return _resolve_descriptor(klass_result, instance, klass)

    if obj is klass:
        # for types we check the metaclass too
        for entry in _static_getmro(type(klass)):
            if _shadowed_dict(type(entry)) is _sentinel:
                try:
                    result = entry.__dict__[attr]
                    get = _check_class(type(result), '__get__')
                    if get is not _sentinel:
                        raise CannotEval
                    return result
                except KeyError:
                    pass
    raise CannotEval


class _foo:
    __slots__ = ['foo']
    method = lambda: 0


slot_descriptor = _foo.foo
wrapper_descriptor = str.__dict__['__add__']
method_descriptor = str.__dict__['startswith']
user_method_descriptor = _foo.__dict__['method']

safe_descriptors_raw = [
    slot_descriptor,
    wrapper_descriptor,
    method_descriptor,
    user_method_descriptor,
]

safe_descriptor_types = list(map(type, safe_descriptors_raw))


def _resolve_descriptor(d, instance, owner):
    try:
        return type(of_type(d, *safe_descriptor_types)).__get__(d, instance, owner)
    except AttributeError as e:
        raise CannotEval from e

# === NexusCore/openenv\Lib\site-packages\git\objects\tag.py ===
# Copyright (C) 2008, 2009 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

"""Provides an :class:`~git.objects.base.Object`-based type for annotated tags.

This defines the :class:`TagObject` class, which represents annotated tags.
For lightweight tags, see the :mod:`git.refs.tag` module.
"""

__all__ = ["TagObject"]

import sys

from git.compat import defenc
from git.util import Actor, hex_to_bin

from . import base
from .util import get_object_type_by_name, parse_actor_and_date

# typing ----------------------------------------------

from typing import List, TYPE_CHECKING, Union

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

if TYPE_CHECKING:
    from git.repo import Repo

    from .blob import Blob
    from .commit import Commit
    from .tree import Tree

# ---------------------------------------------------


class TagObject(base.Object):
    """Annotated (i.e. non-lightweight) tag carrying additional information about an
    object we are pointing to.

    See :manpage:`gitglossary(7)` on "tag object":
    https://git-scm.com/docs/gitglossary#def_tag_object
    """

    type: Literal["tag"] = "tag"

    __slots__ = (
        "object",
        "tag",
        "tagger",
        "tagged_date",
        "tagger_tz_offset",
        "message",
    )

    def __init__(
        self,
        repo: "Repo",
        binsha: bytes,
        object: Union[None, base.Object] = None,
        tag: Union[None, str] = None,
        tagger: Union[None, Actor] = None,
        tagged_date: Union[int, None] = None,
        tagger_tz_offset: Union[int, None] = None,
        message: Union[str, None] = None,
    ) -> None:  # @ReservedAssignment
        """Initialize a tag object with additional data.

        :param repo:
            Repository this object is located in.

        :param binsha:
            20 byte SHA1.

        :param object:
            :class:`~git.objects.base.Object` instance of object we are pointing to.

        :param tag:
            Name of this tag.

        :param tagger:
            :class:`~git.util.Actor` identifying the tagger.

        :param tagged_date: int_seconds_since_epoch
            The DateTime of the tag creation.
            Use :func:`time.gmtime` to convert it into a different format.

        :param tagger_tz_offset: int_seconds_west_of_utc
            The timezone that the `tagged_date` is in, in a format similar to
            :attr:`time.altzone`.
        """
        super().__init__(repo, binsha)
        if object is not None:
            self.object: Union["Commit", "Blob", "Tree", "TagObject"] = object
        if tag is not None:
            self.tag = tag
        if tagger is not None:
            self.tagger = tagger
        if tagged_date is not None:
            self.tagged_date = tagged_date
        if tagger_tz_offset is not None:
            self.tagger_tz_offset = tagger_tz_offset
        if message is not None:
            self.message = message

    def _set_cache_(self, attr: str) -> None:
        """Cache all our attributes at once."""
        if attr in TagObject.__slots__:
            ostream = self.repo.odb.stream(self.binsha)
            lines: List[str] = ostream.read().decode(defenc, "replace").splitlines()

            _obj, hexsha = lines[0].split(" ")
            _type_token, type_name = lines[1].split(" ")
            object_type = get_object_type_by_name(type_name.encode("ascii"))
            self.object = object_type(self.repo, hex_to_bin(hexsha))

            self.tag = lines[2][4:]  # tag <tag name>

            if len(lines) > 3:
                tagger_info = lines[3]  # tagger <actor> <date>
                (
                    self.tagger,
                    self.tagged_date,
                    self.tagger_tz_offset,
                ) = parse_actor_and_date(tagger_info)

            # Line 4 empty - it could mark the beginning of the next header.
            # In case there really is no message, it would not exist.
            # Otherwise a newline separates header from message.
            if len(lines) > 5:
                self.message = "\n".join(lines[5:])
            else:
                self.message = ""
        # END check our attributes
        else:
            super()._set_cache_(attr)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\types\permission.py ===
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
        "Permission",
    },
)


class Permission(proto.Message):
    r"""Permission resource grants user, group or the rest of the
    world access to the PaLM API resource (e.g. a tuned model,
    file).

    A role is a collection of permitted operations that allows users
    to perform specific actions on PaLM API resources. To make them
    available to users, groups, or service accounts, you assign
    roles. When you assign a role, you grant permissions that the
    role contains.

    There are three concentric roles. Each role is a superset of the
    previous role's permitted operations:

    - reader can use the resource (e.g. tuned model) for inference
    - writer has reader's permissions and additionally can edit and
      share
    - owner has writer's permissions and additionally can delete


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        name (str):
            Output only. The permission name. A unique name will be
            generated on create. Example:
            tunedModels/{tuned_model}permssions/{permission} Output
            only.
        grantee_type (google.ai.generativelanguage_v1beta3.types.Permission.GranteeType):
            Required. Immutable. The type of the grantee.

            This field is a member of `oneof`_ ``_grantee_type``.
        email_address (str):
            Optional. Immutable. The email address of the
            user of group which this permission refers.
            Field is not set when permission's grantee type
            is EVERYONE.

            This field is a member of `oneof`_ ``_email_address``.
        role (google.ai.generativelanguage_v1beta3.types.Permission.Role):
            Required. The role granted by this
            permission.

            This field is a member of `oneof`_ ``_role``.
    """

    class GranteeType(proto.Enum):
        r"""Defines types of the grantee of this permission.

        Values:
            GRANTEE_TYPE_UNSPECIFIED (0):
                The default value. This value is unused.
            USER (1):
                Represents a user. When set, you must provide email_address
                for the user.
            GROUP (2):
                Represents a group. When set, you must provide email_address
                for the group.
            EVERYONE (3):
                Represents access to everyone. No extra
                information is required.
        """
        GRANTEE_TYPE_UNSPECIFIED = 0
        USER = 1
        GROUP = 2
        EVERYONE = 3

    class Role(proto.Enum):
        r"""Defines the role granted by this permission.

        Values:
            ROLE_UNSPECIFIED (0):
                The default value. This value is unused.
            OWNER (1):
                Owner can use, update, share and delete the
                resource.
            WRITER (2):
                Writer can use, update and share the
                resource.
            READER (3):
                Reader can use the resource.
        """
        ROLE_UNSPECIFIED = 0
        OWNER = 1
        WRITER = 2
        READER = 3

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    grantee_type: GranteeType = proto.Field(
        proto.ENUM,
        number=2,
        optional=True,
        enum=GranteeType,
    )
    email_address: str = proto.Field(
        proto.STRING,
        number=3,
        optional=True,
    )
    role: Role = proto.Field(
        proto.ENUM,
        number=4,
        optional=True,
        enum=Role,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\google\protobuf\internal\api_implementation.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Determine which implementation of the protobuf API is used in this process.
"""

import importlib
import os
import sys
import warnings


def _ApiVersionToImplementationType(api_version):
  if api_version == 2:
    return 'cpp'
  if api_version == 1:
    raise ValueError('api_version=1 is no longer supported.')
  if api_version == 0:
    return 'python'
  return None


_implementation_type = None
try:
  # pylint: disable=g-import-not-at-top
  from google.protobuf.internal import _api_implementation
  # The compile-time constants in the _api_implementation module can be used to
  # switch to a certain implementation of the Python API at build time.
  _implementation_type = _ApiVersionToImplementationType(
      _api_implementation.api_version)
except ImportError:
  pass  # Unspecified by compiler flags.


def _CanImport(mod_name):
  try:
    mod = importlib.import_module(mod_name)
    # Work around a known issue in the classic bootstrap .par import hook.
    if not mod:
      raise ImportError(mod_name + ' import succeeded but was None')
    return True
  except ImportError:
    return False


if _implementation_type is None:
  if _CanImport('google._upb._message'):
    _implementation_type = 'upb'
  elif _CanImport('google.protobuf.pyext._message'):
    _implementation_type = 'cpp'
  else:
    _implementation_type = 'python'


# This environment variable can be used to switch to a certain implementation
# of the Python API, overriding the compile-time constants in the
# _api_implementation module. Right now only 'python', 'cpp' and 'upb' are
# valid values. Any other value will raise error.
_implementation_type = os.getenv('PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION',
                                 _implementation_type)

if _implementation_type not in ('python', 'cpp', 'upb'):
  raise ValueError('PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION {0} is not '
                   'supported. Please set to \'python\', \'cpp\' or '
                   '\'upb\'.'.format(_implementation_type))

if 'PyPy' in sys.version and _implementation_type == 'cpp':
  warnings.warn('PyPy does not work yet with cpp protocol buffers. '
                'Falling back to the python implementation.')
  _implementation_type = 'python'

_c_module = None

if _implementation_type == 'cpp':
  try:
    # pylint: disable=g-import-not-at-top
    from google.protobuf.pyext import _message
    sys.modules['google3.net.proto2.python.internal.cpp._message'] = _message
    _c_module = _message
    del _message
  except ImportError:
    # TODO: fail back to python
    warnings.warn(
        'Selected implementation cpp is not available.')
    pass

if _implementation_type == 'upb':
  try:
    # pylint: disable=g-import-not-at-top
    from google._upb import _message
    _c_module = _message
    del _message
  except ImportError:
    warnings.warn('Selected implementation upb is not available. '
                  'Falling back to the python implementation.')
    _implementation_type = 'python'
    pass

# Detect if serialization should be deterministic by default
try:
  # The presence of this module in a build allows the proto implementation to
  # be upgraded merely via build deps.
  #
  # NOTE: Merely importing this automatically enables deterministic proto
  # serialization for C++ code, but we still need to export it as a boolean so
  # that we can do the same for `_implementation_type == 'python'`.
  #
  # NOTE2: It is possible for C++ code to enable deterministic serialization by
  # default _without_ affecting Python code, if the C++ implementation is not in
  # use by this module.  That is intended behavior, so we don't actually expose
  # this boolean outside of this module.
  #
  # pylint: disable=g-import-not-at-top,unused-import
  from google.protobuf import enable_deterministic_proto_serialization
  _python_deterministic_proto_serialization = True
except ImportError:
  _python_deterministic_proto_serialization = False


# Usage of this function is discouraged. Clients shouldn't care which
# implementation of the API is in use. Note that there is no guarantee
# that differences between APIs will be maintained.
# Please don't use this function if possible.
def Type():
  return _implementation_type


# See comment on 'Type' above.
# TODO: Remove the API, it returns a constant. b/228102101
def Version():
  return 2


# For internal use only
def IsPythonDefaultSerializationDeterministic():
  return _python_deterministic_proto_serialization

# === NexusCore/openenv\Lib\site-packages\inquirer\render\console\_checkbox.py ===
from readchar import key

from inquirer import errors
from inquirer.render.console._other import GLOBAL_OTHER_CHOICE
from inquirer.render.console.base import MAX_OPTIONS_DISPLAYED_AT_ONCE
from inquirer.render.console.base import BaseConsoleRender
from inquirer.render.console.base import half_options


class Checkbox(BaseConsoleRender):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.locked = self.question.locked or []
        self.selection = [k for (k, v) in enumerate(self.question.choices) if v in self.default_choices()]
        self.current = 0

    def get_hint(self):
        try:
            hint = self.question.hints[self.question.choices[self.current]]
            return hint or ""
        except KeyError:
            return ""

    def default_choices(self):
        default = self.question.default or []
        return default + self.locked

    @property
    def is_long(self):
        choices = self.question.choices or []
        return len(choices) >= MAX_OPTIONS_DISPLAYED_AT_ONCE

    def get_options(self):
        choices = self.question.choices or []
        if self.is_long:
            cmin = 0
            cmax = MAX_OPTIONS_DISPLAYED_AT_ONCE

            if half_options < self.current < len(choices) - half_options:
                cmin += self.current - half_options
                cmax += self.current - half_options
            elif self.current >= len(choices) - half_options:
                cmin += len(choices) - MAX_OPTIONS_DISPLAYED_AT_ONCE
                cmax += len(choices)

            cchoices = choices[cmin:cmax]
        else:
            cchoices = choices

        ending_milestone = max(len(choices) - half_options, half_options + 1)
        is_in_beginning = self.current <= half_options
        is_in_middle = half_options < self.current < ending_milestone
        is_in_end = self.current >= ending_milestone
        for index, choice in enumerate(cchoices):
            if (
                (is_in_middle and self.current - half_options + index in self.selection)
                or (is_in_beginning and index in self.selection)
                or (is_in_end and index + max(len(choices) - MAX_OPTIONS_DISPLAYED_AT_ONCE, 0) in self.selection)
            ):  # noqa
                symbol = self.theme.Checkbox.selected_icon
                color = self.theme.Checkbox.selected_color
            else:
                symbol = self.theme.Checkbox.unselected_icon
                color = self.theme.Checkbox.unselected_color

            selector = " "
            end_index = ending_milestone + index - half_options - 1
            if (
                (is_in_middle and index == half_options)
                or (is_in_beginning and index == self.current)
                or (is_in_end and end_index == self.current)
            ):
                selector = self.theme.Checkbox.selection_icon
                color = self.theme.Checkbox.selection_color

            if choice in self.locked:
                color = self.theme.Checkbox.locked_option_color

            if choice == GLOBAL_OTHER_CHOICE:
                symbol = "+"

            yield choice, selector + " " + symbol, color

    def process_input(self, pressed):
        question = self.question
        is_current_choice_locked = question.choices[self.current] in self.locked
        if pressed == key.UP:
            if question.carousel and self.current == 0:
                self.current = len(question.choices) - 1
            else:
                self.current = max(0, self.current - 1)
            return
        elif pressed == key.DOWN:
            if question.carousel and self.current == len(question.choices) - 1:
                self.current = 0
            else:
                self.current = min(len(self.question.choices) - 1, self.current + 1)
            return
        elif pressed == key.SPACE:
            if self.question.choices[self.current] == GLOBAL_OTHER_CHOICE:
                self.other_input()
            elif self.current in self.selection:
                if not is_current_choice_locked:
                    self.selection.remove(self.current)
            else:
                self.selection.append(self.current)
        elif pressed == key.LEFT:
            if self.current in self.selection:
                if not is_current_choice_locked:
                    self.selection.remove(self.current)
        elif pressed == key.RIGHT:
            if self.current not in self.selection:
                self.selection.append(self.current)
        elif pressed == key.CTRL_A:
            self.selection = [i for i in range(len(self.question.choices))]
        elif pressed == key.CTRL_R:
            self.selection = []
        elif pressed == key.CTRL_I:
            self.selection = [i for i in range(len(self.question.choices)) if i not in self.selection]
        elif pressed == key.ENTER:
            result = []
            for x in self.selection:
                value = self.question.choices[x]
                result.append(getattr(value, "value", value))
            raise errors.EndOfInput(result)
        elif pressed == key.CTRL_C:
            raise KeyboardInterrupt()

    def other_input(self):
        other = super().other_input()

        # Clear the print that inquirer.text made
        print(self.terminal.move_up + self.terminal.clear_eol, end="")

        if not other:
            return

        index = self.question.add_choice(other)
        if index not in self.selection:
            self.selection.append(index)

# === NexusCore/openenv\Lib\site-packages\interpreter\core\utils\system_debug_info.py ===
import platform
import subprocess

import pkg_resources
import psutil
import toml


def get_python_version():
    return platform.python_version()


def get_pip_version():
    try:
        pip_version = subprocess.check_output(["pip", "--version"]).decode().split()[1]
    except Exception as e:
        pip_version = str(e)
    return pip_version


def get_oi_version():
    try:
        oi_version_cmd = subprocess.check_output(
            ["interpreter", "--version"], text=True
        )
    except Exception as e:
        oi_version_cmd = str(e)
    oi_version_pkg = pkg_resources.get_distribution("open-interpreter").version
    oi_version = oi_version_cmd, oi_version_pkg
    return oi_version


def get_os_version():
    return platform.platform()


def get_cpu_info():
    return platform.processor()


def get_ram_info():
    vm = psutil.virtual_memory()
    used_ram_gb = vm.used / (1024**3)
    free_ram_gb = vm.free / (1024**3)
    total_ram_gb = vm.total / (1024**3)
    return f"{total_ram_gb:.2f} GB, used: {used_ram_gb:.2f}, free: {free_ram_gb:.2f}"


def get_package_mismatches(file_path="pyproject.toml"):
    with open(file_path, "r") as file:
        pyproject = toml.load(file)
    dependencies = pyproject["tool"]["poetry"]["dependencies"]
    dev_dependencies = pyproject["tool"]["poetry"]["group"]["dev"]["dependencies"]
    dependencies.update(dev_dependencies)

    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}

    mismatches = []
    for package, version_info in dependencies.items():
        if isinstance(version_info, dict):
            version_info = version_info["version"]
        installed_version = installed_packages.get(package)
        if installed_version and version_info.startswith("^"):
            expected_version = version_info[1:]
            if not installed_version.startswith(expected_version):
                mismatches.append(
                    f"\t  {package}: Mismatch, pyproject.toml={expected_version}, pip={installed_version}"
                )
        else:
            mismatches.append(f"\t  {package}: Not found in pip list")

    return "\n" + "\n".join(mismatches)


def interpreter_info(interpreter):
    try:
        if interpreter.offline and interpreter.llm.api_base:
            try:
                curl = subprocess.check_output(f"curl {interpreter.llm.api_base}")
            except Exception as e:
                curl = str(e)
        else:
            curl = "Not local"

        messages_to_display = []
        for message in interpreter.messages:
            message = str(message.copy())
            try:
                if len(message) > 2000:
                    message = message[:1000]
            except Exception as e:
                print(str(e), "for message:", message)
            messages_to_display.append(message)

        return f"""

        # Interpreter Info
        
        Vision: {interpreter.llm.supports_vision}
        Model: {interpreter.llm.model}
        Function calling: {interpreter.llm.supports_functions}
        Context window: {interpreter.llm.context_window}
        Max tokens: {interpreter.llm.max_tokens}
        Computer API: {interpreter.computer.import_computer_api}

        Auto run: {interpreter.auto_run}
        API base: {interpreter.llm.api_base}
        Offline: {interpreter.offline}

        Curl output: {curl}

        # Messages

        System Message: {interpreter.system_message}

        """ + "\n\n".join(
            [str(m) for m in messages_to_display]
        )
    except:
        return "Error, couldn't get interpreter info"


def system_info(interpreter):
    oi_version = get_oi_version()
    print(
        f"""
        Python Version: {get_python_version()}
        Pip Version: {get_pip_version()}
        Open-interpreter Version: cmd: {oi_version[0]}, pkg: {oi_version[1]}
        OS Version and Architecture: {get_os_version()}
        CPU Info: {get_cpu_info()}
        RAM Info: {get_ram_info()}
        {interpreter_info(interpreter)}
    """
    )

    # Removed the following, as it causes `FileNotFoundError: [Errno 2] No such file or directory: 'pyproject.toml'`` on prod
    # (i think it works on dev, but on prod the pyproject.toml will not be in the cwd. might not be accessible at all)
    # Package Version Mismatches:
    # {get_package_mismatches()}

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\config.py ===
"""Implementation of configuration-related magic functions.
"""
#-----------------------------------------------------------------------------
#  Copyright (c) 2012 The IPython Development Team.
#
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
import re

# Our own packages
from IPython.core.error import UsageError
from IPython.core.magic import Magics, magics_class, line_magic
from logging import error

#-----------------------------------------------------------------------------
# Magic implementation classes
#-----------------------------------------------------------------------------

reg = re.compile(r'^\w+\.\w+$')
@magics_class
class ConfigMagics(Magics):

    def __init__(self, shell):
        super(ConfigMagics, self).__init__(shell)
        self.configurables = []

    @line_magic
    def config(self, s):
        """configure IPython

            %config Class[.trait=value]

        This magic exposes most of the IPython config system. Any
        Configurable class should be able to be configured with the simple
        line::

            %config Class.trait=value

        Where `value` will be resolved in the user's namespace, if it is an
        expression or variable name.

        Examples
        --------

        To see what classes are available for config, pass no arguments::

            In [1]: %config
            Available objects for config:
                AliasManager
                DisplayFormatter
                HistoryManager
                IPCompleter
                LoggingMagics
                MagicsManager
                OSMagics
                PrefilterManager
                ScriptMagics
                TerminalInteractiveShell

        To view what is configurable on a given class, just pass the class
        name::

            In [2]: %config LoggingMagics
            LoggingMagics(Magics) options
            ---------------------------
            LoggingMagics.quiet=<Bool>
                Suppress output of log state when logging is enabled
                Current: False

        but the real use is in setting values::

            In [3]: %config LoggingMagics.quiet = True

        and these values are read from the user_ns if they are variables::

            In [4]: feeling_quiet=False

            In [5]: %config LoggingMagics.quiet = feeling_quiet

        """
        from traitlets.config.loader import Config
        # some IPython objects are Configurable, but do not yet have
        # any configurable traits.  Exclude them from the effects of
        # this magic, as their presence is just noise:
        configurables = sorted(set([ c for c in self.shell.configurables
                                     if c.__class__.class_traits(config=True)
                                     ]), key=lambda x: x.__class__.__name__)
        classnames = [ c.__class__.__name__ for c in configurables ]

        line = s.strip()
        if not line:
            # print available configurable names
            print("Available objects for config:")
            for name in classnames:
                print("   ", name)
            return
        elif line in classnames:
            # `%config TerminalInteractiveShell` will print trait info for
            # TerminalInteractiveShell
            c = configurables[classnames.index(line)]
            cls = c.__class__
            help = cls.class_get_help(c)
            # strip leading '--' from cl-args:
            help = re.sub(re.compile(r'^--', re.MULTILINE), '', help)
            print(help)
            return
        elif reg.match(line):
            cls, attr = line.split('.')
            return getattr(configurables[classnames.index(cls)],attr)
        elif '=' not in line:
            msg = "Invalid config statement: %r, "\
                  "should be `Class.trait = value`."
            
            ll = line.lower()
            for classname in classnames:
                if ll == classname.lower():
                    msg = msg + '\nDid you mean %s (note the case)?' % classname
                    break

            raise UsageError( msg % line)

        # otherwise, assume we are setting configurables.
        # leave quotes on args when splitting, because we want
        # unquoted args to eval in user_ns
        cfg = Config()
        exec("cfg."+line, self.shell.user_ns, locals())

        for configurable in configurables:
            try:
                configurable.update_config(cfg)
            except Exception as e:
                error(e)

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\pt_inputhooks\glut.py ===
"""GLUT Input hook for interactive use with prompt_toolkit
"""


# GLUT is quite an old library and it is difficult to ensure proper
# integration within IPython since original GLUT does not allow to handle
# events one by one. Instead, it requires for the mainloop to be entered
# and never returned (there is not even a function to exit he
# mainloop). Fortunately, there are alternatives such as freeglut
# (available for linux and windows) and the OSX implementation gives
# access to a glutCheckLoop() function that blocks itself until a new
# event is received. This means we have to setup the idle callback to
# ensure we got at least one event that will unblock the function.
#
# Furthermore, it is not possible to install these handlers without a window
# being first created. We choose to make this window invisible. This means that
# display mode options are set at this level and user won't be able to change
# them later without modifying the code. This should probably be made available
# via IPython options system.

import sys
import time
import signal
import OpenGL.GLUT as glut
import OpenGL.platform as platform
from timeit import default_timer as clock

# Frame per second : 60
# Should probably be an IPython option
glut_fps = 60

# Display mode : double buffeed + rgba + depth
# Should probably be an IPython option
glut_display_mode = (glut.GLUT_DOUBLE |
                     glut.GLUT_RGBA   |
                     glut.GLUT_DEPTH)

glutMainLoopEvent = None
if sys.platform == 'darwin':
    try:
        glutCheckLoop = platform.createBaseFunction(
            'glutCheckLoop', dll=platform.GLUT, resultType=None,
            argTypes=[],
            doc='glutCheckLoop(  ) -> None',
            argNames=(),
            )
    except AttributeError as e:
        raise RuntimeError(
            '''Your glut implementation does not allow interactive sessions. '''
            '''Consider installing freeglut.''') from e
    glutMainLoopEvent = glutCheckLoop
elif glut.HAVE_FREEGLUT:
    glutMainLoopEvent = glut.glutMainLoopEvent
else:
    raise RuntimeError(
        '''Your glut implementation does not allow interactive sessions. '''
        '''Consider installing freeglut.''')


def glut_display():
    # Dummy display function
    pass

def glut_idle():
    # Dummy idle function
    pass

def glut_close():
    # Close function only hides the current window
    glut.glutHideWindow()
    glutMainLoopEvent()

def glut_int_handler(signum, frame):
    # Catch sigint and print the defaultipyt   message
    signal.signal(signal.SIGINT, signal.default_int_handler)
    print('\nKeyboardInterrupt')
    # Need to reprint the prompt at this stage

# Initialisation code
glut.glutInit( sys.argv )
glut.glutInitDisplayMode( glut_display_mode )
# This is specific to freeglut
if bool(glut.glutSetOption):
    glut.glutSetOption( glut.GLUT_ACTION_ON_WINDOW_CLOSE,
                        glut.GLUT_ACTION_GLUTMAINLOOP_RETURNS )
glut.glutCreateWindow( b'ipython' )
glut.glutReshapeWindow( 1, 1 )
glut.glutHideWindow( )
glut.glutWMCloseFunc( glut_close )
glut.glutDisplayFunc( glut_display )
glut.glutIdleFunc( glut_idle )


def inputhook(context):
    """Run the pyglet event loop by processing pending events only.

    This keeps processing pending events until stdin is ready.  After
    processing all pending events, a call to time.sleep is inserted.  This is
    needed, otherwise, CPU usage is at 100%.  This sleep time should be tuned
    though for best performance.
    """
    # We need to protect against a user pressing Control-C when IPython is
    # idle and this is running. We trap KeyboardInterrupt and pass.

    signal.signal(signal.SIGINT, glut_int_handler)

    try:
        t = clock()

        # Make sure the default window is set after a window has been closed
        if glut.glutGetWindow() == 0:
            glut.glutSetWindow( 1 )
            glutMainLoopEvent()
            return 0

        while not context.input_is_ready():
            glutMainLoopEvent()
            # We need to sleep at this point to keep the idle CPU load
            # low.  However, if sleep to long, GUI response is poor.  As
            # a compromise, we watch how often GUI events are being processed
            # and switch between a short and long sleep time.  Here are some
            # stats useful in helping to tune this.
            # time    CPU load
            # 0.001   13%
            # 0.005   3%
            # 0.01    1.5%
            # 0.05    0.5%
            used_time = clock() - t
            if used_time > 10.0:
                # print('Sleep for 1 s')  # dbg
                time.sleep(1.0)
            elif used_time > 0.1:
                # Few GUI events coming in, so we can sleep longer
                # print('Sleep for 0.05 s')  # dbg
                time.sleep(0.05)
            else:
                # Many GUI events coming in, so sleep only very little
                time.sleep(0.001)
    except KeyboardInterrupt:
        pass

# === NexusCore/openenv\Lib\site-packages\nltk\chat\suntsu.py ===
# Natural Language Toolkit: Sun Tsu-Bot
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Sam Huston 2007
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Tsu bot responds to all queries with a Sun Tsu sayings

Quoted from Sun Tsu's The Art of War
Translated by LIONEL GILES, M.A. 1910
Hosted by the Gutenberg Project
https://www.gutenberg.org/
"""

from nltk.chat.util import Chat, reflections

pairs = (
    (r"quit", ("Good-bye.", "Plan well", "May victory be your future")),
    (
        r"[^\?]*\?",
        (
            "Please consider whether you can answer your own question.",
            "Ask me no questions!",
        ),
    ),
    (
        r"[0-9]+(.*)",
        (
            "It is the rule in war, if our forces are ten to the enemy's one, to surround him; if five to one, to attack him; if twice as numerous, to divide our army into two.",
            "There are five essentials for victory",
        ),
    ),
    (
        r"[A-Ca-c](.*)",
        (
            "The art of war is of vital importance to the State.",
            "All warfare is based on deception.",
            "If your opponent is secure at all points, be prepared for him. If he is in superior strength, evade him.",
            "If the campaign is protracted, the resources of the State will not be equal to the strain.",
            "Attack him where he is unprepared, appear where you are not expected.",
            "There is no instance of a country having benefited from prolonged warfare.",
        ),
    ),
    (
        r"[D-Fd-f](.*)",
        (
            "The skillful soldier does not raise a second levy, neither are his supply-wagons loaded more than twice.",
            "Bring war material with you from home, but forage on the enemy.",
            "In war, then, let your great object be victory, not lengthy campaigns.",
            "To fight and conquer in all your battles is not supreme excellence; supreme excellence consists in breaking the enemy's resistance without fighting.",
        ),
    ),
    (
        r"[G-Ig-i](.*)",
        (
            "Heaven signifies night and day, cold and heat, times and seasons.",
            "It is the rule in war, if our forces are ten to the enemy's one, to surround him; if five to one, to attack him; if twice as numerous, to divide our army into two.",
            "The good fighters of old first put themselves beyond the possibility of defeat, and then waited for an opportunity of defeating the enemy.",
            "One may know how to conquer without being able to do it.",
        ),
    ),
    (
        r"[J-Lj-l](.*)",
        (
            "There are three ways in which a ruler can bring misfortune upon his army.",
            "By commanding the army to advance or to retreat, being ignorant of the fact that it cannot obey. This is called hobbling the army.",
            "By attempting to govern an army in the same way as he administers a kingdom, being ignorant of the conditions which obtain in an army. This causes restlessness in the soldier's minds.",
            "By employing the officers of his army without discrimination, through ignorance of the military principle of adaptation to circumstances. This shakes the confidence of the soldiers.",
            "There are five essentials for victory",
            "He will win who knows when to fight and when not to fight.",
            "He will win who knows how to handle both superior and inferior forces.",
            "He will win whose army is animated by the same spirit throughout all its ranks.",
            "He will win who, prepared himself, waits to take the enemy unprepared.",
            "He will win who has military capacity and is not interfered with by the sovereign.",
        ),
    ),
    (
        r"[M-Om-o](.*)",
        (
            "If you know the enemy and know yourself, you need not fear the result of a hundred battles.",
            "If you know yourself but not the enemy, for every victory gained you will also suffer a defeat.",
            "If you know neither the enemy nor yourself, you will succumb in every battle.",
            "The control of a large force is the same principle as the control of a few men: it is merely a question of dividing up their numbers.",
        ),
    ),
    (
        r"[P-Rp-r](.*)",
        (
            "Security against defeat implies defensive tactics; ability to defeat the enemy means taking the offensive.",
            "Standing on the defensive indicates insufficient strength; attacking, a superabundance of strength.",
            "He wins his battles by making no mistakes. Making no mistakes is what establishes the certainty of victory, for it means conquering an enemy that is already defeated.",
            "A victorious army opposed to a routed one, is as a pound's weight placed in the scale against a single grain.",
            "The onrush of a conquering force is like the bursting of pent-up waters into a chasm a thousand fathoms deep.",
        ),
    ),
    (
        r"[S-Us-u](.*)",
        (
            "What the ancients called a clever fighter is one who not only wins, but excels in winning with ease.",
            "Hence his victories bring him neither reputation for wisdom nor credit for courage.",
            "Hence the skillful fighter puts himself into a position which makes defeat impossible, and does not miss the moment for defeating the enemy.",
            "In war the victorious strategist only seeks battle after the victory has been won, whereas he who is destined to defeat first fights and afterwards looks for victory.",
            "There are not more than five musical notes, yet the combinations of these five give rise to more melodies than can ever be heard.",
            "Appear at points which the enemy must hasten to defend; march swiftly to places where you are not expected.",
        ),
    ),
    (
        r"[V-Zv-z](.*)",
        (
            "It is a matter of life and death, a road either to safety or to ruin.",
            "Hold out baits to entice the enemy. Feign disorder, and crush him.",
            "All men can see the tactics whereby I conquer, but what none can see is the strategy out of which victory is evolved.",
            "Do not repeat the tactics which have gained you one victory, but let your methods be regulated by the infinite variety of circumstances.",
            "So in war, the way is to avoid what is strong and to strike at what is weak.",
            "Just as water retains no constant shape, so in warfare there are no constant conditions.",
        ),
    ),
    (r"(.*)", ("Your statement insults me.", "")),
)

suntsu_chatbot = Chat(pairs, reflections)


def suntsu_chat():
    print("Talk to the program by typing in plain English, using normal upper-")
    print('and lower-case letters and punctuation.  Enter "quit" when done.')
    print("=" * 72)
    print("You seek enlightenment?")

    suntsu_chatbot.converse()


def demo():
    suntsu_chat()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\sexpr.py ===
# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Yoav Goldberg <yoavg@cs.bgu.ac.il>
#         Steven Bird <stevenbird1@gmail.com> (minor edits)
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

"""
S-Expression Tokenizer

``SExprTokenizer`` is used to find parenthesized expressions in a
string.  In particular, it divides a string into a sequence of
substrings that are either parenthesized expressions (including any
nested parenthesized expressions), or other whitespace-separated
tokens.

    >>> from nltk.tokenize import SExprTokenizer
    >>> SExprTokenizer().tokenize('(a b (c d)) e f (g)')
    ['(a b (c d))', 'e', 'f', '(g)']

By default, `SExprTokenizer` will raise a ``ValueError`` exception if
used to tokenize an expression with non-matching parentheses:

    >>> SExprTokenizer().tokenize('c) d) e (f (g')
    Traceback (most recent call last):
      ...
    ValueError: Un-matched close paren at char 1

The ``strict`` argument can be set to False to allow for
non-matching parentheses.  Any unmatched close parentheses will be
listed as their own s-expression; and the last partial sexpr with
unmatched open parentheses will be listed as its own sexpr:

    >>> SExprTokenizer(strict=False).tokenize('c) d) e (f (g')
    ['c', ')', 'd', ')', 'e', '(f (g']

The characters used for open and close parentheses may be customized
using the ``parens`` argument to the `SExprTokenizer` constructor:

    >>> SExprTokenizer(parens='{}').tokenize('{a b {c d}} e f {g}')
    ['{a b {c d}}', 'e', 'f', '{g}']

The s-expression tokenizer is also available as a function:

    >>> from nltk.tokenize import sexpr_tokenize
    >>> sexpr_tokenize('(a b (c d)) e f (g)')
    ['(a b (c d))', 'e', 'f', '(g)']

"""

import re

from nltk.tokenize.api import TokenizerI


class SExprTokenizer(TokenizerI):
    """
    A tokenizer that divides strings into s-expressions.
    An s-expresion can be either:

      - a parenthesized expression, including any nested parenthesized
        expressions, or
      - a sequence of non-whitespace non-parenthesis characters.

    For example, the string ``(a (b c)) d e (f)`` consists of four
    s-expressions: ``(a (b c))``, ``d``, ``e``, and ``(f)``.

    By default, the characters ``(`` and ``)`` are treated as open and
    close parentheses, but alternative strings may be specified.

    :param parens: A two-element sequence specifying the open and close parentheses
        that should be used to find sexprs.  This will typically be either a
        two-character string, or a list of two strings.
    :type parens: str or list
    :param strict: If true, then raise an exception when tokenizing an ill-formed sexpr.
    """

    def __init__(self, parens="()", strict=True):
        if len(parens) != 2:
            raise ValueError("parens must contain exactly two strings")
        self._strict = strict
        self._open_paren = parens[0]
        self._close_paren = parens[1]
        self._paren_regexp = re.compile(
            f"{re.escape(parens[0])}|{re.escape(parens[1])}"
        )

    def tokenize(self, text):
        """
        Return a list of s-expressions extracted from *text*.
        For example:

            >>> SExprTokenizer().tokenize('(a b (c d)) e f (g)')
            ['(a b (c d))', 'e', 'f', '(g)']

        All parentheses are assumed to mark s-expressions.
        (No special processing is done to exclude parentheses that occur
        inside strings, or following backslash characters.)

        If the given expression contains non-matching parentheses,
        then the behavior of the tokenizer depends on the ``strict``
        parameter to the constructor.  If ``strict`` is ``True``, then
        raise a ``ValueError``.  If ``strict`` is ``False``, then any
        unmatched close parentheses will be listed as their own
        s-expression; and the last partial s-expression with unmatched open
        parentheses will be listed as its own s-expression:

            >>> SExprTokenizer(strict=False).tokenize('c) d) e (f (g')
            ['c', ')', 'd', ')', 'e', '(f (g']

        :param text: the string to be tokenized
        :type text: str or iter(str)
        :rtype: iter(str)
        """
        result = []
        pos = 0
        depth = 0
        for m in self._paren_regexp.finditer(text):
            paren = m.group()
            if depth == 0:
                result += text[pos : m.start()].split()
                pos = m.start()
            if paren == self._open_paren:
                depth += 1
            if paren == self._close_paren:
                if self._strict and depth == 0:
                    raise ValueError("Un-matched close paren at char %d" % m.start())
                depth = max(0, depth - 1)
                if depth == 0:
                    result.append(text[pos : m.end()])
                    pos = m.end()
        if self._strict and depth > 0:
            raise ValueError("Un-matched open paren at char %d" % pos)
        if pos < len(text):
            result.append(text[pos:])
        return result


sexpr_tokenize = SExprTokenizer().tokenize

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_tracing.py ===
# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pathlib
from typing import Dict, Optional, Union, cast

from playwright._impl._api_structures import TracingGroupLocation
from playwright._impl._artifact import Artifact
from playwright._impl._connection import ChannelOwner, from_nullable_channel
from playwright._impl._helper import locals_to_params


class Tracing(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.mark_as_internal_type()
        self._include_sources: bool = False
        self._stacks_id: Optional[str] = None
        self._is_tracing: bool = False
        self._traces_dir: Optional[str] = None

    async def start(
        self,
        name: str = None,
        title: str = None,
        snapshots: bool = None,
        screenshots: bool = None,
        sources: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        self._include_sources = bool(sources)

        await self._channel.send("tracingStart", params)
        trace_name = await self._channel.send(
            "tracingStartChunk", {"title": title, "name": name}
        )
        await self._start_collecting_stacks(trace_name)

    async def start_chunk(self, title: str = None, name: str = None) -> None:
        params = locals_to_params(locals())
        trace_name = await self._channel.send("tracingStartChunk", params)
        await self._start_collecting_stacks(trace_name)

    async def _start_collecting_stacks(self, trace_name: str) -> None:
        if not self._is_tracing:
            self._is_tracing = True
            self._connection.set_is_tracing(True)
        self._stacks_id = await self._connection.local_utils.tracing_started(
            self._traces_dir, trace_name
        )

    async def stop_chunk(self, path: Union[pathlib.Path, str] = None) -> None:
        await self._do_stop_chunk(path)

    async def stop(self, path: Union[pathlib.Path, str] = None) -> None:
        await self._do_stop_chunk(path)
        await self._channel.send("tracingStop")

    async def _do_stop_chunk(self, file_path: Union[pathlib.Path, str] = None) -> None:
        self._reset_stack_counter()

        if not file_path:
            # Not interested in any artifacts
            await self._channel.send("tracingStopChunk", {"mode": "discard"})
            if self._stacks_id:
                await self._connection.local_utils.trace_discarded(self._stacks_id)
            return

        is_local = not self._connection.is_remote

        if is_local:
            result = await self._channel.send_return_as_dict(
                "tracingStopChunk", {"mode": "entries"}
            )
            await self._connection.local_utils.zip(
                {
                    "zipFile": str(file_path),
                    "entries": result["entries"],
                    "stacksId": self._stacks_id,
                    "mode": "write",
                    "includeSources": self._include_sources,
                }
            )
            return

        result = await self._channel.send_return_as_dict(
            "tracingStopChunk",
            {
                "mode": "archive",
            },
        )

        artifact = cast(
            Optional[Artifact],
            from_nullable_channel(result.get("artifact")),
        )

        # The artifact may be missing if the browser closed while stopping tracing.
        if not artifact:
            if self._stacks_id:
                await self._connection.local_utils.trace_discarded(self._stacks_id)
            return

        # Save trace to the final local file.
        await artifact.save_as(file_path)
        await artifact.delete()

        await self._connection.local_utils.zip(
            {
                "zipFile": str(file_path),
                "entries": [],
                "stacksId": self._stacks_id,
                "mode": "append",
                "includeSources": self._include_sources,
            }
        )

    def _reset_stack_counter(self) -> None:
        if self._is_tracing:
            self._is_tracing = False
            self._connection.set_is_tracing(False)

    async def group(self, name: str, location: TracingGroupLocation = None) -> None:
        await self._channel.send("tracingGroup", locals_to_params(locals()))

    async def group_end(self) -> None:
        await self._channel.send("tracingGroupEnd")

# === NexusCore/openenv\Lib\site-packages\pydantic\plugin\_schema_validator.py ===
"""Pluggable schema validator for pydantic."""

from __future__ import annotations

import functools
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Callable, Literal, TypeVar

from pydantic_core import CoreConfig, CoreSchema, SchemaValidator, ValidationError
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from . import BaseValidateHandlerProtocol, PydanticPluginProtocol, SchemaKind, SchemaTypePath


P = ParamSpec('P')
R = TypeVar('R')
Event = Literal['on_validate_python', 'on_validate_json', 'on_validate_strings']
events: list[Event] = list(Event.__args__)  # type: ignore


def create_schema_validator(
    schema: CoreSchema,
    schema_type: Any,
    schema_type_module: str,
    schema_type_name: str,
    schema_kind: SchemaKind,
    config: CoreConfig | None = None,
    plugin_settings: dict[str, Any] | None = None,
) -> SchemaValidator | PluggableSchemaValidator:
    """Create a `SchemaValidator` or `PluggableSchemaValidator` if plugins are installed.

    Returns:
        If plugins are installed then return `PluggableSchemaValidator`, otherwise return `SchemaValidator`.
    """
    from . import SchemaTypePath
    from ._loader import get_plugins

    plugins = get_plugins()
    if plugins:
        return PluggableSchemaValidator(
            schema,
            schema_type,
            SchemaTypePath(schema_type_module, schema_type_name),
            schema_kind,
            config,
            plugins,
            plugin_settings or {},
        )
    else:
        return SchemaValidator(schema, config)


class PluggableSchemaValidator:
    """Pluggable schema validator."""

    __slots__ = '_schema_validator', 'validate_json', 'validate_python', 'validate_strings'

    def __init__(
        self,
        schema: CoreSchema,
        schema_type: Any,
        schema_type_path: SchemaTypePath,
        schema_kind: SchemaKind,
        config: CoreConfig | None,
        plugins: Iterable[PydanticPluginProtocol],
        plugin_settings: dict[str, Any],
    ) -> None:
        self._schema_validator = SchemaValidator(schema, config)

        python_event_handlers: list[BaseValidateHandlerProtocol] = []
        json_event_handlers: list[BaseValidateHandlerProtocol] = []
        strings_event_handlers: list[BaseValidateHandlerProtocol] = []
        for plugin in plugins:
            try:
                p, j, s = plugin.new_schema_validator(
                    schema, schema_type, schema_type_path, schema_kind, config, plugin_settings
                )
            except TypeError as e:  # pragma: no cover
                raise TypeError(f'Error using plugin `{plugin.__module__}:{plugin.__class__.__name__}`: {e}') from e
            if p is not None:
                python_event_handlers.append(p)
            if j is not None:
                json_event_handlers.append(j)
            if s is not None:
                strings_event_handlers.append(s)

        self.validate_python = build_wrapper(self._schema_validator.validate_python, python_event_handlers)
        self.validate_json = build_wrapper(self._schema_validator.validate_json, json_event_handlers)
        self.validate_strings = build_wrapper(self._schema_validator.validate_strings, strings_event_handlers)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._schema_validator, name)


def build_wrapper(func: Callable[P, R], event_handlers: list[BaseValidateHandlerProtocol]) -> Callable[P, R]:
    if not event_handlers:
        return func
    else:
        on_enters = tuple(h.on_enter for h in event_handlers if filter_handlers(h, 'on_enter'))
        on_successes = tuple(h.on_success for h in event_handlers if filter_handlers(h, 'on_success'))
        on_errors = tuple(h.on_error for h in event_handlers if filter_handlers(h, 'on_error'))
        on_exceptions = tuple(h.on_exception for h in event_handlers if filter_handlers(h, 'on_exception'))

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for on_enter_handler in on_enters:
                on_enter_handler(*args, **kwargs)

            try:
                result = func(*args, **kwargs)
            except ValidationError as error:
                for on_error_handler in on_errors:
                    on_error_handler(error)
                raise
            except Exception as exception:
                for on_exception_handler in on_exceptions:
                    on_exception_handler(exception)
                raise
            else:
                for on_success_handler in on_successes:
                    on_success_handler(result)
                return result

        return wrapper


def filter_handlers(handler_cls: BaseValidateHandlerProtocol, method_name: str) -> bool:
    """Filter out handler methods which are not implemented by the plugin directly - e.g. are missing
    or are inherited from the protocol.
    """
    handler = getattr(handler_cls, method_name, None)
    if handler is None:
        return False
    elif handler.__module__ == 'pydantic.plugin':
        # this is the original handler, from the protocol due to runtime inheritance
        # we don't want to call it
        return False
    else:
        return True

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_validate_call.py ===
from __future__ import annotations as _annotations

import functools
import inspect
from collections.abc import Awaitable
from functools import partial
from typing import Any, Callable

import pydantic_core

from ..config import ConfigDict
from ..plugin._schema_validator import create_schema_validator
from ._config import ConfigWrapper
from ._generate_schema import GenerateSchema, ValidateCallSupportedTypes
from ._namespace_utils import MappingNamespace, NsResolver, ns_for_function


def extract_function_name(func: ValidateCallSupportedTypes) -> str:
    """Extract the name of a `ValidateCallSupportedTypes` object."""
    return f'partial({func.func.__name__})' if isinstance(func, functools.partial) else func.__name__


def extract_function_qualname(func: ValidateCallSupportedTypes) -> str:
    """Extract the qualname of a `ValidateCallSupportedTypes` object."""
    return f'partial({func.func.__qualname__})' if isinstance(func, functools.partial) else func.__qualname__


def update_wrapper_attributes(wrapped: ValidateCallSupportedTypes, wrapper: Callable[..., Any]):
    """Update the `wrapper` function with the attributes of the `wrapped` function. Return the updated function."""
    if inspect.iscoroutinefunction(wrapped):

        @functools.wraps(wrapped)
        async def wrapper_function(*args, **kwargs):  # type: ignore
            return await wrapper(*args, **kwargs)
    else:

        @functools.wraps(wrapped)
        def wrapper_function(*args, **kwargs):
            return wrapper(*args, **kwargs)

    # We need to manually update this because `partial` object has no `__name__` and `__qualname__`.
    wrapper_function.__name__ = extract_function_name(wrapped)
    wrapper_function.__qualname__ = extract_function_qualname(wrapped)
    wrapper_function.raw_function = wrapped  # type: ignore

    return wrapper_function


class ValidateCallWrapper:
    """This is a wrapper around a function that validates the arguments passed to it, and optionally the return value."""

    __slots__ = (
        'function',
        'validate_return',
        'schema_type',
        'module',
        'qualname',
        'ns_resolver',
        'config_wrapper',
        '__pydantic_complete__',
        '__pydantic_validator__',
        '__return_pydantic_validator__',
    )

    def __init__(
        self,
        function: ValidateCallSupportedTypes,
        config: ConfigDict | None,
        validate_return: bool,
        parent_namespace: MappingNamespace | None,
    ) -> None:
        self.function = function
        self.validate_return = validate_return
        if isinstance(function, partial):
            self.schema_type = function.func
            self.module = function.func.__module__
        else:
            self.schema_type = function
            self.module = function.__module__
        self.qualname = extract_function_qualname(function)

        self.ns_resolver = NsResolver(
            namespaces_tuple=ns_for_function(self.schema_type, parent_namespace=parent_namespace)
        )
        self.config_wrapper = ConfigWrapper(config)
        if not self.config_wrapper.defer_build:
            self._create_validators()
        else:
            self.__pydantic_complete__ = False

    def _create_validators(self) -> None:
        gen_schema = GenerateSchema(self.config_wrapper, self.ns_resolver)
        schema = gen_schema.clean_schema(gen_schema.generate_schema(self.function))
        core_config = self.config_wrapper.core_config(title=self.qualname)

        self.__pydantic_validator__ = create_schema_validator(
            schema,
            self.schema_type,
            self.module,
            self.qualname,
            'validate_call',
            core_config,
            self.config_wrapper.plugin_settings,
        )
        if self.validate_return:
            signature = inspect.signature(self.function)
            return_type = signature.return_annotation if signature.return_annotation is not signature.empty else Any
            gen_schema = GenerateSchema(self.config_wrapper, self.ns_resolver)
            schema = gen_schema.clean_schema(gen_schema.generate_schema(return_type))
            validator = create_schema_validator(
                schema,
                self.schema_type,
                self.module,
                self.qualname,
                'validate_call',
                core_config,
                self.config_wrapper.plugin_settings,
            )
            if inspect.iscoroutinefunction(self.function):

                async def return_val_wrapper(aw: Awaitable[Any]) -> None:
                    return validator.validate_python(await aw)

                self.__return_pydantic_validator__ = return_val_wrapper
            else:
                self.__return_pydantic_validator__ = validator.validate_python
        else:
            self.__return_pydantic_validator__ = None

        self.__pydantic_complete__ = True

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if not self.__pydantic_complete__:
            self._create_validators()

        res = self.__pydantic_validator__.validate_python(pydantic_core.ArgsKwargs(args, kwargs))
        if self.__return_pydantic_validator__:
            return self.__return_pydantic_validator__(res)
        else:
            return res

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\thingsdb.py ===
"""
    pygments.lexers.thingsdb
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for the ThingsDB language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, bygroups
from pygments.token import Comment, Keyword, Name, Number, String, Text, \
    Operator, Punctuation, Whitespace

__all__ = ['ThingsDBLexer']


class ThingsDBLexer(RegexLexer):
    """
    Lexer for the ThingsDB programming language.
    """
    name = 'ThingsDB'
    aliases = ['ti', 'thingsdb']
    filenames = ['*.ti']
    url = 'https://www.thingsdb.net'
    version_added = '2.9'

    tokens = {
        'root': [
            include('expression'),
        ],
        'expression': [
            include('comments'),
            include('whitespace'),

            # numbers
            (r'[-+]?0b[01]+', Number.Bin),
            (r'[-+]?0o[0-8]+', Number.Oct),
            (r'([-+]?0x[0-9a-fA-F]+)', Number.Hex),
            (r'[-+]?[0-9]+', Number.Integer),
            (r'[-+]?((inf|nan)([^0-9A-Za-z_]|$)|[0-9]*\.[0-9]+(e[+-][0-9]+)?)',
             Number.Float),

            # strings
            (r'(?:"(?:[^"]*)")+', String.Double),
            (r"(?:'(?:[^']*)')+", String.Single),
            (r"(?:`(?:[^`]*)`)+", String.Backtick),

            # literals
            (r'(true|false|nil)\b', Keyword.Constant),

            # name constants
            (r'(FULL|USER|GRANT|CHANGE|JOIN|RUN|QUERY|'
             r'DEBUG|INFO|WARNING|ERROR|CRITICAL|'
             r'NO_IDS|INT_MIN|INT_MAX)\b', Name.Constant),

            # regular expressions
            (r'(/[^/\\]*(?:\\.[^/\\]*)*/i?)', String.Regex),

            # name, assignments and functions
            include('names'),

            (r'[(){}\[\],;]', Punctuation),
            (r'[+\-*/%&|<>^!~@=:?]', Operator),
        ],
        'names': [
            (r'(\.)'
             r'(first|last|then|else|load|at|again_in|again_at|err|cancel|'
             r'closure|set_closure|args|set_args|owner|set_owner|equals|copy|'
             r'dup|assign|week|weekday|yday|zone|len|call|doc|emit|extract|'
             r'choice|code|format|msg|each|every|extend|extend_unique|filter|'
             r'find|flat|find_index|has|index_of|count|sum|is_unique|unique|'
             r'join|map|map_id|map_wrap|map_type|vmap|move|pop|push|fill|'
             r'remove|replace|restrict|restriction|shift|sort|splice|to|add|'
             r'one|clear|contains|ends_with|name|lower|replace|reverse|'
             r'starts_with|split|test|trim|trim_left|trim_right|upper|del|ren|'
             r'to_type|to_thing|get|id|keys|reduce|set|some|value|values|wrap|'
             r'unshift|unwrap|search)'
             r'(\()',
             bygroups(Name.Function, Name.Function, Punctuation), 'arguments'),
            (r'(alt_raise|assert|base64_encode|base64_decode|bool|bytes|'
             r'closure|datetime|deep|future|is_future|del_enum|del_type|room|'
             r'is_room|task|tasks|is_task|is_email|is_url|is_tel|is_time_zone|'
             r'timeit|enum|enum_info|enum_map|enums_info|err|regex|is_regex|'
             r'change_id|float|has_enum|has_type|int|is_array|is_ascii|'
             r'is_float|is_bool|is_bytes|is_closure|is_datetime|is_enum|'
             r'is_err|is_mpdata|is_inf|is_int|is_list|is_nan|is_nil|is_raw|'
             r'is_set|is_str|is_thing|is_timeval|is_tuple|is_utf8|json_dump|'
             r'json_load|list|log|import|export|root|mod_enum|mod_type|new|'
             r'new_type|now|raise|rand|range|randint|randstr|refs|rename_enum|'
             r'set|set_enum|set_type|str|thing|timeval|try|type|type_assert|'
             r'type_count|type_info|types_info|nse|wse|backup_info|'
             r'backups_info|backups_ok|counters|del_backup|has_backup|'
             r'new_backup|node_info|nodes_info|reset_counters|restart_module|'
             r'set_log_level|shutdown|has_module|del_module|module_info|'
             r'modules_info|new_module|deploy_module|rename_module|'
             r'refresh_module|set_module_conf|set_module_scope|'
             r'collections_info|del_collection|del_expired|del_node|del_token|'
             r'del_user|grant|has_collection|has_node|has_token|has_user|'
             r'new_collection|new_node|new_token|new_user|rename_collection|'
             r'rename_user|restore|revoke|set_password|set_time_zone|'
             r'set_default_deep|time_zones_info|user_info|users_info|'
             r'del_procedure|has_procedure|new_procedure|mod_procedure|'
             r'procedure_doc|procedure_info|procedures_info|rename_procedure|'
             r'run|assert_err|auth_err|bad_data_err|cancelled_err|'
             r'rename_type|forbidden_err|lookup_err|max_quota_err|node_err|'
             r'num_arguments_err|operation_err|overflow_err|syntax_err|'
             r'collection_info|type_err|value_err|zero_div_err)'
             r'(\()',
             bygroups(Name.Function, Punctuation),
             'arguments'),
            (r'(\.[A-Za-z_][0-9A-Za-z_]*)'
             r'(\s*)(=)',
             bygroups(Name.Attribute, Text, Operator)),
            (r'\.[A-Za-z_][0-9A-Za-z_]*', Name.Attribute),
            (r'([A-Za-z_][0-9A-Za-z_]*)(\s*)(=)',
             bygroups(Name.Variable, Text, Operator)),
            (r'[A-Za-z_][0-9A-Za-z_]*', Name.Variable),
        ],
        'whitespace': [
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
        ],
        'comments': [
            (r'//(.*?)\n', Comment.Single),
            (r'/\*', Comment.Multiline, 'comment'),
        ],
        'comment': [
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ],
        'arguments': [
            include('expression'),
            (',', Punctuation),
            (r'\(', Punctuation, '#push'),
            (r'\)', Punctuation, '#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\vyper.py ===
"""
    pygments.lexers.vyper
    ~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Vyper Smart Contract language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups, words
from pygments.token import (Comment, String, Name, Keyword, Number,
                            Operator, Punctuation, Text, Whitespace)

__all__ = ['VyperLexer']


class VyperLexer(RegexLexer):
    """For the Vyper smart contract language.
    """
    name = 'Vyper'
    aliases = ['vyper']
    filenames = ['*.vy']
    url = "https://vyper.readthedocs.io"
    version_added = '2.17'

    tokens = {
        'root': [
            # Whitespace
            (r'\s+', Whitespace),

            # Line continuations
            (r'(\\)(\n|\r\n|\r)', bygroups(Text, Whitespace)),

            # Comments - inline and multiline
            (r'#.*$', Comment.Single),
            (r'\"\"\"', Comment.Multiline, 'multiline-comment'),

            # Strings - single and double
            (r"'", String.Single, 'single-string'),
            (r'"', String.Double, 'double-string'),

            # Functions (working)
            (r'(def)(\s+)([a-zA-Z_][a-zA-Z0-9_]*)',
             bygroups(Keyword, Whitespace, Name.Function)),

            # Event and Struct
            (r'(event|struct|interface|log)(\s+)([a-zA-Z_][a-zA-Z0-9_]*)',
             bygroups(Keyword, Whitespace, Name.Class)),

            # Imports
            (r'(from)(\s+)(vyper\.\w+)(\s+)(import)(\s+)(\w+)',
             bygroups(Keyword, Whitespace, Name.Namespace, Whitespace,
                      Keyword, Whitespace, Name.Class)),

            # Numeric Literals
            (r'\b0x[0-9a-fA-F]+\b', Number.Hex),
            (r'\b(\d{1,3}(?:_\d{3})*|\d+)\b', Number.Integer),
            (r'\b\d+\.\d*\b', Number.Float),

            # Keywords
            (words(('def', 'event', 'pass', 'return', 'for', 'while', 'if', 'elif',
                    'else', 'assert', 'raise', 'import', 'in', 'struct', 'implements',
                    'interface', 'from', 'indexed', 'log', 'extcall', 'staticcall'),
                   prefix=r'\b', suffix=r'\b'), Keyword),

            # Visibility and State Mutability
            (words(('public', 'private', 'view', 'pure', 'constant',
                    'immutable', 'nonpayable'), prefix=r'\b', suffix=r'\b'),
             Keyword.Declaration),

            # Built-in Functions
            (words(('bitwise_and', 'bitwise_not', 'bitwise_or', 'bitwise_xor', 'shift',
                    'create_minimal_proxy_to', 'create_copy_of', 'create_from_blueprint',
                    'ecadd', 'ecmul', 'ecrecover', 'keccak256', 'sha256', 'concat', 'convert',
                    'uint2str', 'extract32', 'slice', 'abs', 'ceil', 'floor', 'max', 'max_value',
                    'min', 'min_value', 'pow_mod256', 'sqrt', 'isqrt', 'uint256_addmod',
                    'uint256_mulmod', 'unsafe_add', 'unsafe_sub', 'unsafe_mul', 'unsafe_div',
                    'as_wei_value', 'blockhash', 'empty', 'len', 'method_id', '_abi_encode',
                    '_abi_decode', 'print', 'range'), prefix=r'\b', suffix=r'\b'),
             Name.Builtin),

            # Built-in Variables and Attributes
            (words(('msg.sender', 'msg.value', 'block.timestamp', 'block.number', 'msg.gas'),
                   prefix=r'\b', suffix=r'\b'),
             Name.Builtin.Pseudo),

            (words(('uint', 'uint8', 'uint16', 'uint32', 'uint64', 'uint128', 'uint256',
                    'int', 'int8', 'int16', 'int32', 'int64', 'int128', 'int256', 'bool',
                    'decimal', 'bytes', 'bytes1', 'bytes2', 'bytes3', 'bytes4', 'bytes5',
                    'bytes6', 'bytes7', 'bytes8', 'bytes9', 'bytes10', 'bytes11',
                    'bytes12', 'bytes13', 'bytes14', 'bytes15', 'bytes16', 'bytes17',
                    'bytes18', 'bytes19', 'bytes20', 'bytes21', 'bytes22', 'bytes23',
                    'bytes24', 'bytes25', 'bytes26', 'bytes27', 'bytes28', 'bytes29',
                    'bytes30', 'bytes31', 'bytes32', 'string', 'String', 'address',
                    'enum', 'struct'), prefix=r'\b', suffix=r'\b'),
             Keyword.Type),

            # indexed keywords
            (r'\b(indexed)\b(\s*)(\()(\s*)(\w+)(\s*)(\))',
             bygroups(Keyword, Whitespace, Punctuation, Whitespace,
                      Keyword.Type, Punctuation)),

            # Operators and Punctuation
            (r'(\+|\-|\*|\/|<=?|>=?|==|!=|=|\||&|%)', Operator),
            (r'[.,:;()\[\]{}]', Punctuation),

            # Other variable names and types
            (r'@[\w.]+', Name.Decorator),
            (r'__\w+__', Name.Magic),  # Matches double underscores followed by word characters
            (r'EMPTY_BYTES32', Name.Constant),
            (r'\bERC20\b', Name.Class),
            (r'\bself\b', Name.Attribute),

            (r'Bytes\[\d+\]', Keyword.Type),

            # Generic names and variables
            (r'\b[a-zA-Z_]\w*\b:', Name.Variable),
            (r'\b[a-zA-Z_]\w*\b', Name),

        ],

        'multiline-comment': [
            (r'\"\"\"', Comment.Multiline, '#pop'),
            (r'[^"]+', Comment.Multiline),
            (r'\"', Comment.Multiline)
        ],

        'single-string': [
            (r"[^\\']+", String.Single),
            (r"'", String.Single, '#pop'),
            (r'\\.', String.Escape),
        ],

        'double-string': [
            (r'[^\\"]+', String.Double),
            (r'"', String.Double, '#pop'),
            (r'\\.', String.Escape),
        ]
    }

# === NexusCore/openenv\Lib\site-packages\trio\_tests\tools\test_mypy_annotate.py ===
from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING

import pytest

from trio._tools.mypy_annotate import Result, export, main, process_line

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("", None),
        ("a regular line\n", None),
        (
            "package\\filename.py:42:8: note: Some info\n",
            Result(
                kind="notice",
                filename="package\\filename.py",
                start_line=42,
                start_col=8,
                end_line=None,
                end_col=None,
                message=" Some info",
            ),
        ),
        (
            "package/filename.py:42:1:46:3: error: Type error here [code]\n",
            Result(
                kind="error",
                filename="package/filename.py",
                start_line=42,
                start_col=1,
                end_line=46,
                end_col=3,
                message=" Type error here [code]",
            ),
        ),
        (
            "package/module.py:87: warn: Bad code\n",
            Result(
                kind="warning",
                filename="package/module.py",
                start_line=87,
                message=" Bad code",
            ),
        ),
    ],
    ids=["blank", "normal", "note-wcol", "error-wend", "warn-lineonly"],
)
def test_processing(src: str, expected: Result | None) -> None:
    result = process_line(src)
    assert result == expected


def test_export(capsys: pytest.CaptureFixture[str]) -> None:
    results = {
        Result(
            kind="notice",
            filename="package\\filename.py",
            start_line=42,
            start_col=8,
            end_line=None,
            end_col=None,
            message=" Some info",
        ): ["Windows", "Mac"],
        Result(
            kind="error",
            filename="package/filename.py",
            start_line=42,
            start_col=1,
            end_line=46,
            end_col=3,
            message=" Type error here [code]",
        ): ["Linux", "Mac"],
        Result(
            kind="warning",
            filename="package/module.py",
            start_line=87,
            message=" Bad code",
        ): ["Linux"],
    }
    export(results)
    std = capsys.readouterr()
    assert std.err == ""
    assert std.out == (
        "::notice file=package\\filename.py,line=42,col=8,"
        "title=Mypy-Windows+Mac::package\\filename.py:(42:8): Some info"
        "\n"
        "::error file=package/filename.py,line=42,col=1,endLine=46,endColumn=3,"
        "title=Mypy-Linux+Mac::package/filename.py:(42:1 - 46:3): Type error here [code]"
        "\n"
        "::warning file=package/module.py,line=87,"
        "title=Mypy-Linux::package/module.py:87: Bad code\n"
    )


def test_endtoend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import trio._tools.mypy_annotate as mypy_annotate

    inp_text = """\
Mypy begun
trio/core.py:15: error: Bad types here [misc]
trio/package/module.py:48:4:56:18: warn: Missing annotations  [no-untyped-def]
Found 3 errors in 29 files
"""
    result_file = tmp_path / "dump.dat"
    assert not result_file.exists()
    with monkeypatch.context():
        monkeypatch.setattr(sys, "stdin", io.StringIO(inp_text))

        mypy_annotate.main(
            ["--dumpfile", str(result_file), "--platform", "SomePlatform"],
        )

    std = capsys.readouterr()
    assert std.err == ""
    assert std.out == inp_text  # Echos the original.

    assert result_file.exists()

    main(["--dumpfile", str(result_file)])

    std = capsys.readouterr()
    assert std.err == ""
    assert std.out == (
        "::error file=trio/core.py,line=15,title=Mypy-SomePlatform::trio/core.py:15: Bad types here [misc]\n"
        "::warning file=trio/package/module.py,line=48,col=4,endLine=56,endColumn=18,"
        "title=Mypy-SomePlatform::trio/package/module.py:(48:4 - 56:18): Missing "
        "annotations  [no-untyped-def]\n"
    )

# === NexusCore/openenv\Lib\site-packages\win32com\test\testIterators.py ===
# Some raw iter tests.  Some "high-level" iterator tests can be found in
# testvb.py and testOutlook.py
import sys
import unittest

import pythoncom
import win32com.server.util
import win32com.test.util
from win32com.client import Dispatch
from win32com.client.gencache import EnsureDispatch


class _BaseTestCase(win32com.test.util.TestCase):
    def test_enumvariant_vb(self):
        ob, iter = self.iter_factory()
        got = []
        for v in iter:
            got.append(v)
        self.assertEqual(got, self.expected_data)

    def test_yield(self):
        ob, i = self.iter_factory()
        got = []
        for v in iter(i):
            got.append(v)
        self.assertEqual(got, self.expected_data)

    def _do_test_nonenum(self, object):
        try:
            for i in object:
                pass
            self.fail("Could iterate over a non-iterable object")
        except TypeError:
            pass  # this is expected.
        self.assertRaises(TypeError, iter, object)
        self.assertRaises(AttributeError, getattr, object, "next")

    def test_nonenum_wrapper(self):
        # Check our raw PyIDispatch
        ob = self.object._oleobj_
        try:
            for i in ob:
                pass
            self.fail("Could iterate over a non-iterable object")
        except TypeError:
            pass  # this is expected.
        self.assertRaises(TypeError, iter, ob)
        self.assertRaises(AttributeError, getattr, ob, "next")

        # And our Dispatch wrapper
        ob = self.object
        try:
            for i in ob:
                pass
            self.fail("Could iterate over a non-iterable object")
        except TypeError:
            pass  # this is expected.
        # Note that as our object may be dynamic, we *do* have a __getitem__
        # method, meaning we *can* call iter() on the object.  In this case
        # actual iteration is what fails.
        # So either the 'iter(); will raise a type error, or an attempt to
        # fetch it
        try:
            next(iter(ob))
            self.fail("Expected a TypeError fetching this iterator")
        except TypeError:
            pass
        # And it should never have a 'next' method
        self.assertRaises(AttributeError, getattr, ob, "next")


class VBTestCase(_BaseTestCase):
    def setUp(self):
        def factory():
            # Our VB test harness exposes a property with IEnumVariant.
            ob = self.object.EnumerableCollectionProperty
            for i in self.expected_data:
                ob.Add(i)
            # Get the raw IEnumVARIANT.
            invkind = pythoncom.DISPATCH_METHOD | pythoncom.DISPATCH_PROPERTYGET
            iter = ob._oleobj_.InvokeTypes(
                pythoncom.DISPID_NEWENUM, 0, invkind, (13, 10), ()
            )
            return ob, iter.QueryInterface(pythoncom.IID_IEnumVARIANT)

        # We *need* generated dispatch semantics, so dynamic __getitem__ etc
        # don't get in the way of our tests.
        self.object = EnsureDispatch("PyCOMVBTest.Tester")
        self.expected_data = [1, "Two", "3"]
        self.iter_factory = factory

    def tearDown(self):
        self.object = None


# Test our client semantics, but using a wrapped Python list object.
# This has the effect of re-using our client specific tests, but in this
# case is exercising the server side.
class SomeObject:
    _public_methods_ = ["GetCollection"]

    def __init__(self, data):
        self.data = data

    def GetCollection(self):
        return win32com.server.util.NewCollection(self.data)


class WrappedPythonCOMServerTestCase(_BaseTestCase):
    def setUp(self):
        def factory():
            ob = self.object.GetCollection()
            flags = pythoncom.DISPATCH_METHOD | pythoncom.DISPATCH_PROPERTYGET
            enum = ob._oleobj_.Invoke(pythoncom.DISPID_NEWENUM, 0, flags, 1)
            return ob, enum.QueryInterface(pythoncom.IID_IEnumVARIANT)

        self.expected_data = [1, "Two", 3]
        sv = win32com.server.util.wrap(SomeObject(self.expected_data))
        self.object = Dispatch(sv)
        self.iter_factory = factory

    def tearDown(self):
        self.object = None


def suite():
    # We don't want our base class run
    suite = unittest.TestSuite()
    for item in globals().values():
        if (
            isinstance(item, type)
            and issubclass(item, unittest.TestCase)
            and item != _BaseTestCase
        ):
            suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(item))
    return suite


if __name__ == "__main__":
    unittest.main(argv=sys.argv + ["suite"])

# === NexusCore/openenv\Lib\site-packages\zmq\auth\certs.py ===
"""0MQ authentication related functions and classes."""

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.

import datetime
import glob
import os
from typing import Dict, Optional, Tuple, Union

import zmq

_cert_secret_banner = """#   ****  Generated on {0} by pyzmq  ****
#   ZeroMQ CURVE **Secret** Certificate
#   DO NOT PROVIDE THIS FILE TO OTHER USERS nor change its permissions.

"""


_cert_public_banner = """#   ****  Generated on {0} by pyzmq  ****
#   ZeroMQ CURVE Public Certificate
#   Exchange securely, or use a secure mechanism to verify the contents
#   of this file after exchange. Store public certificates in your home
#   directory, in the .curve subdirectory.

"""


def _write_key_file(
    key_filename: Union[str, os.PathLike],
    banner: str,
    public_key: Union[str, bytes],
    secret_key: Optional[Union[str, bytes]] = None,
    metadata: Optional[Dict[str, str]] = None,
    encoding: str = 'utf-8',
) -> None:
    """Create a certificate file"""
    if isinstance(public_key, bytes):
        public_key = public_key.decode(encoding)
    if isinstance(secret_key, bytes):
        secret_key = secret_key.decode(encoding)
    with open(key_filename, 'w', encoding='utf8') as f:
        f.write(banner.format(datetime.datetime.now()))

        f.write('metadata\n')
        if metadata:
            for k, v in metadata.items():
                if isinstance(k, bytes):
                    k = k.decode(encoding)
                if isinstance(v, bytes):
                    v = v.decode(encoding)
                f.write(f"    {k} = {v}\n")

        f.write('curve\n')
        f.write(f"    public-key = \"{public_key}\"\n")

        if secret_key:
            f.write(f"    secret-key = \"{secret_key}\"\n")


def create_certificates(
    key_dir: Union[str, os.PathLike],
    name: str,
    metadata: Optional[Dict[str, str]] = None,
) -> Tuple[str, str]:
    """Create zmq certificates.

    Returns the file paths to the public and secret certificate files.
    """
    public_key, secret_key = zmq.curve_keypair()
    base_filename = os.path.join(key_dir, name)
    secret_key_file = f"{base_filename}.key_secret"
    public_key_file = f"{base_filename}.key"
    now = datetime.datetime.now()

    _write_key_file(public_key_file, _cert_public_banner.format(now), public_key)

    _write_key_file(
        secret_key_file,
        _cert_secret_banner.format(now),
        public_key,
        secret_key=secret_key,
        metadata=metadata,
    )

    return public_key_file, secret_key_file


def load_certificate(
    filename: Union[str, os.PathLike],
) -> Tuple[bytes, Optional[bytes]]:
    """Load public and secret key from a zmq certificate.

    Returns (public_key, secret_key)

    If the certificate file only contains the public key,
    secret_key will be None.

    If there is no public key found in the file, ValueError will be raised.
    """
    public_key = None
    secret_key = None
    if not os.path.exists(filename):
        raise OSError(f"Invalid certificate file: {filename}")

    with open(filename, 'rb') as f:
        for line in f:
            line = line.strip()
            if line.startswith(b'#'):
                continue
            if line.startswith(b'public-key'):
                public_key = line.split(b"=", 1)[1].strip(b' \t\'"')
            if line.startswith(b'secret-key'):
                secret_key = line.split(b"=", 1)[1].strip(b' \t\'"')
            if public_key and secret_key:
                break

    if public_key is None:
        raise ValueError(f"No public key found in {filename}")

    return public_key, secret_key


def load_certificates(directory: Union[str, os.PathLike] = '.') -> Dict[bytes, bool]:
    """Load public keys from all certificates in a directory"""
    certs = {}
    if not os.path.isdir(directory):
        raise OSError(f"Invalid certificate directory: {directory}")
    # Follow czmq pattern of public keys stored in *.key files.
    glob_string = os.path.join(directory, "*.key")

    cert_files = glob.glob(glob_string)
    for cert_file in cert_files:
        public_key, _ = load_certificate(cert_file)
        if public_key:
            certs[public_key] = True
    return certs


__all__ = ['create_certificates', 'load_certificate', 'load_certificates']

# === NexusCore/myenv\Lib\site-packages\pip\_internal\commands\index.py ===
import logging
from optparse import Values
from typing import Any, Iterable, List, Optional

from pip._vendor.packaging.version import Version

from pip._internal.cli import cmdoptions
from pip._internal.cli.req_command import IndexGroupCommand
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.commands.search import print_dist_installation_info
from pip._internal.exceptions import CommandError, DistributionNotFound, PipError
from pip._internal.index.collector import LinkCollector
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.models.target_python import TargetPython
from pip._internal.network.session import PipSession
from pip._internal.utils.misc import write_output

logger = logging.getLogger(__name__)


class IndexCommand(IndexGroupCommand):
    """
    Inspect information available from package indexes.
    """

    ignore_require_venv = True
    usage = """
        %prog versions <package>
    """

    def add_options(self) -> None:
        cmdoptions.add_target_python_options(self.cmd_opts)

        self.cmd_opts.add_option(cmdoptions.ignore_requires_python())
        self.cmd_opts.add_option(cmdoptions.pre())
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        handlers = {
            "versions": self.get_available_package_versions,
        }

        logger.warning(
            "pip index is currently an experimental command. "
            "It may be removed/changed in a future release "
            "without prior warning."
        )

        # Determine action
        if not args or args[0] not in handlers:
            logger.error(
                "Need an action (%s) to perform.",
                ", ".join(sorted(handlers)),
            )
            return ERROR

        action = args[0]

        # Error handling happens here, not in the action-handlers.
        try:
            handlers[action](options, args[1:])
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        return SUCCESS

    def _build_package_finder(
        self,
        options: Values,
        session: PipSession,
        target_python: Optional[TargetPython] = None,
        ignore_requires_python: Optional[bool] = None,
    ) -> PackageFinder:
        """
        Create a package finder appropriate to the index command.
        """
        link_collector = LinkCollector.create(session, options=options)

        # Pass allow_yanked=False to ignore yanked versions.
        selection_prefs = SelectionPreferences(
            allow_yanked=False,
            allow_all_prereleases=options.pre,
            ignore_requires_python=ignore_requires_python,
        )

        return PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=selection_prefs,
            target_python=target_python,
        )

    def get_available_package_versions(self, options: Values, args: List[Any]) -> None:
        if len(args) != 1:
            raise CommandError("You need to specify exactly one argument")

        target_python = cmdoptions.make_target_python(options)
        query = args[0]

        with self._build_session(options) as session:
            finder = self._build_package_finder(
                options=options,
                session=session,
                target_python=target_python,
                ignore_requires_python=options.ignore_requires_python,
            )

            versions: Iterable[Version] = (
                candidate.version for candidate in finder.find_all_candidates(query)
            )

            if not options.pre:
                # Remove prereleases
                versions = (
                    version for version in versions if not version.is_prerelease
                )
            versions = set(versions)

            if not versions:
                raise DistributionNotFound(
                    f"No matching distribution found for {query}"
                )

            formatted_versions = [str(ver) for ver in sorted(versions, reverse=True)]
            latest = formatted_versions[0]

        write_output(f"{query} ({latest})")
        write_output("Available versions: {}".format(", ".join(formatted_versions)))
        print_dist_installation_info(query, latest)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\resolvelib\base.py ===
from dataclasses import dataclass
from typing import FrozenSet, Iterable, Optional, Tuple

from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import NormalizedName
from pip._vendor.packaging.version import Version

from pip._internal.models.link import Link, links_equivalent
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.hashes import Hashes

CandidateLookup = Tuple[Optional["Candidate"], Optional[InstallRequirement]]


def format_name(project: NormalizedName, extras: FrozenSet[NormalizedName]) -> str:
    if not extras:
        return project
    extras_expr = ",".join(sorted(extras))
    return f"{project}[{extras_expr}]"


@dataclass(frozen=True)
class Constraint:
    specifier: SpecifierSet
    hashes: Hashes
    links: FrozenSet[Link]

    @classmethod
    def empty(cls) -> "Constraint":
        return Constraint(SpecifierSet(), Hashes(), frozenset())

    @classmethod
    def from_ireq(cls, ireq: InstallRequirement) -> "Constraint":
        links = frozenset([ireq.link]) if ireq.link else frozenset()
        return Constraint(ireq.specifier, ireq.hashes(trust_internet=False), links)

    def __bool__(self) -> bool:
        return bool(self.specifier) or bool(self.hashes) or bool(self.links)

    def __and__(self, other: InstallRequirement) -> "Constraint":
        if not isinstance(other, InstallRequirement):
            return NotImplemented
        specifier = self.specifier & other.specifier
        hashes = self.hashes & other.hashes(trust_internet=False)
        links = self.links
        if other.link:
            links = links.union([other.link])
        return Constraint(specifier, hashes, links)

    def is_satisfied_by(self, candidate: "Candidate") -> bool:
        # Reject if there are any mismatched URL constraints on this package.
        if self.links and not all(_match_link(link, candidate) for link in self.links):
            return False
        # We can safely always allow prereleases here since PackageFinder
        # already implements the prerelease logic, and would have filtered out
        # prerelease candidates if the user does not expect them.
        return self.specifier.contains(candidate.version, prereleases=True)


class Requirement:
    @property
    def project_name(self) -> NormalizedName:
        """The "project name" of a requirement.

        This is different from ``name`` if this requirement contains extras,
        in which case ``name`` would contain the ``[...]`` part, while this
        refers to the name of the project.
        """
        raise NotImplementedError("Subclass should override")

    @property
    def name(self) -> str:
        """The name identifying this requirement in the resolver.

        This is different from ``project_name`` if this requirement contains
        extras, where ``project_name`` would not contain the ``[...]`` part.
        """
        raise NotImplementedError("Subclass should override")

    def is_satisfied_by(self, candidate: "Candidate") -> bool:
        return False

    def get_candidate_lookup(self) -> CandidateLookup:
        raise NotImplementedError("Subclass should override")

    def format_for_error(self) -> str:
        raise NotImplementedError("Subclass should override")


def _match_link(link: Link, candidate: "Candidate") -> bool:
    if candidate.source_link:
        return links_equivalent(link, candidate.source_link)
    return False


class Candidate:
    @property
    def project_name(self) -> NormalizedName:
        """The "project name" of the candidate.

        This is different from ``name`` if this candidate contains extras,
        in which case ``name`` would contain the ``[...]`` part, while this
        refers to the name of the project.
        """
        raise NotImplementedError("Override in subclass")

    @property
    def name(self) -> str:
        """The name identifying this candidate in the resolver.

        This is different from ``project_name`` if this candidate contains
        extras, where ``project_name`` would not contain the ``[...]`` part.
        """
        raise NotImplementedError("Override in subclass")

    @property
    def version(self) -> Version:
        raise NotImplementedError("Override in subclass")

    @property
    def is_installed(self) -> bool:
        raise NotImplementedError("Override in subclass")

    @property
    def is_editable(self) -> bool:
        raise NotImplementedError("Override in subclass")

    @property
    def source_link(self) -> Optional[Link]:
        raise NotImplementedError("Override in subclass")

    def iter_dependencies(self, with_requires: bool) -> Iterable[Optional[Requirement]]:
        raise NotImplementedError("Override in subclass")

    def get_install_requirement(self) -> Optional[InstallRequirement]:
        raise NotImplementedError("Override in subclass")

    def format_for_error(self) -> str:
        raise NotImplementedError("Subclass should override")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\json.py ===
from pathlib import Path
from json import loads, dumps
from typing import Any, Callable, Optional, Union

from .text import Text
from .highlighter import JSONHighlighter, NullHighlighter


class JSON:
    """A renderable which pretty prints JSON.

    Args:
        json (str): JSON encoded data.
        indent (Union[None, int, str], optional): Number of characters to indent by. Defaults to 2.
        highlight (bool, optional): Enable highlighting. Defaults to True.
        skip_keys (bool, optional): Skip keys not of a basic type. Defaults to False.
        ensure_ascii (bool, optional): Escape all non-ascii characters. Defaults to False.
        check_circular (bool, optional): Check for circular references. Defaults to True.
        allow_nan (bool, optional): Allow NaN and Infinity values. Defaults to True.
        default (Callable, optional): A callable that converts values that can not be encoded
            in to something that can be JSON encoded. Defaults to None.
        sort_keys (bool, optional): Sort dictionary keys. Defaults to False.
    """

    def __init__(
        self,
        json: str,
        indent: Union[None, int, str] = 2,
        highlight: bool = True,
        skip_keys: bool = False,
        ensure_ascii: bool = False,
        check_circular: bool = True,
        allow_nan: bool = True,
        default: Optional[Callable[[Any], Any]] = None,
        sort_keys: bool = False,
    ) -> None:
        data = loads(json)
        json = dumps(
            data,
            indent=indent,
            skipkeys=skip_keys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            default=default,
            sort_keys=sort_keys,
        )
        highlighter = JSONHighlighter() if highlight else NullHighlighter()
        self.text = highlighter(json)
        self.text.no_wrap = True
        self.text.overflow = None

    @classmethod
    def from_data(
        cls,
        data: Any,
        indent: Union[None, int, str] = 2,
        highlight: bool = True,
        skip_keys: bool = False,
        ensure_ascii: bool = False,
        check_circular: bool = True,
        allow_nan: bool = True,
        default: Optional[Callable[[Any], Any]] = None,
        sort_keys: bool = False,
    ) -> "JSON":
        """Encodes a JSON object from arbitrary data.

        Args:
            data (Any): An object that may be encoded in to JSON
            indent (Union[None, int, str], optional): Number of characters to indent by. Defaults to 2.
            highlight (bool, optional): Enable highlighting. Defaults to True.
            default (Callable, optional): Optional callable which will be called for objects that cannot be serialized. Defaults to None.
            skip_keys (bool, optional): Skip keys not of a basic type. Defaults to False.
            ensure_ascii (bool, optional): Escape all non-ascii characters. Defaults to False.
            check_circular (bool, optional): Check for circular references. Defaults to True.
            allow_nan (bool, optional): Allow NaN and Infinity values. Defaults to True.
            default (Callable, optional): A callable that converts values that can not be encoded
                in to something that can be JSON encoded. Defaults to None.
            sort_keys (bool, optional): Sort dictionary keys. Defaults to False.

        Returns:
            JSON: New JSON object from the given data.
        """
        json_instance: "JSON" = cls.__new__(cls)
        json = dumps(
            data,
            indent=indent,
            skipkeys=skip_keys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            default=default,
            sort_keys=sort_keys,
        )
        highlighter = JSONHighlighter() if highlight else NullHighlighter()
        json_instance.text = highlighter(json)
        json_instance.text.no_wrap = True
        json_instance.text.overflow = None
        return json_instance

    def __rich__(self) -> Text:
        return self.text


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Pretty print json")
    parser.add_argument(
        "path",
        metavar="PATH",
        help="path to file, or - for stdin",
    )
    parser.add_argument(
        "-i",
        "--indent",
        metavar="SPACES",
        type=int,
        help="Number of spaces in an indent",
        default=2,
    )
    args = parser.parse_args()

    from pip._vendor.rich.console import Console

    console = Console()
    error_console = Console(stderr=True)

    try:
        if args.path == "-":
            json_data = sys.stdin.read()
        else:
            json_data = Path(args.path).read_text()
    except Exception as error:
        error_console.print(f"Unable to read {args.path!r}; {error}")
        sys.exit(-1)

    console.print(JSON(json_data, indent=args.indent), soft_wrap=True)

# === NexusCore/openenv\Lib\site-packages\rich\json.py ===
from pathlib import Path
from json import loads, dumps
from typing import Any, Callable, Optional, Union

from .text import Text
from .highlighter import JSONHighlighter, NullHighlighter


class JSON:
    """A renderable which pretty prints JSON.

    Args:
        json (str): JSON encoded data.
        indent (Union[None, int, str], optional): Number of characters to indent by. Defaults to 2.
        highlight (bool, optional): Enable highlighting. Defaults to True.
        skip_keys (bool, optional): Skip keys not of a basic type. Defaults to False.
        ensure_ascii (bool, optional): Escape all non-ascii characters. Defaults to False.
        check_circular (bool, optional): Check for circular references. Defaults to True.
        allow_nan (bool, optional): Allow NaN and Infinity values. Defaults to True.
        default (Callable, optional): A callable that converts values that can not be encoded
            in to something that can be JSON encoded. Defaults to None.
        sort_keys (bool, optional): Sort dictionary keys. Defaults to False.
    """

    def __init__(
        self,
        json: str,
        indent: Union[None, int, str] = 2,
        highlight: bool = True,
        skip_keys: bool = False,
        ensure_ascii: bool = False,
        check_circular: bool = True,
        allow_nan: bool = True,
        default: Optional[Callable[[Any], Any]] = None,
        sort_keys: bool = False,
    ) -> None:
        data = loads(json)
        json = dumps(
            data,
            indent=indent,
            skipkeys=skip_keys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            default=default,
            sort_keys=sort_keys,
        )
        highlighter = JSONHighlighter() if highlight else NullHighlighter()
        self.text = highlighter(json)
        self.text.no_wrap = True
        self.text.overflow = None

    @classmethod
    def from_data(
        cls,
        data: Any,
        indent: Union[None, int, str] = 2,
        highlight: bool = True,
        skip_keys: bool = False,
        ensure_ascii: bool = False,
        check_circular: bool = True,
        allow_nan: bool = True,
        default: Optional[Callable[[Any], Any]] = None,
        sort_keys: bool = False,
    ) -> "JSON":
        """Encodes a JSON object from arbitrary data.

        Args:
            data (Any): An object that may be encoded in to JSON
            indent (Union[None, int, str], optional): Number of characters to indent by. Defaults to 2.
            highlight (bool, optional): Enable highlighting. Defaults to True.
            default (Callable, optional): Optional callable which will be called for objects that cannot be serialized. Defaults to None.
            skip_keys (bool, optional): Skip keys not of a basic type. Defaults to False.
            ensure_ascii (bool, optional): Escape all non-ascii characters. Defaults to False.
            check_circular (bool, optional): Check for circular references. Defaults to True.
            allow_nan (bool, optional): Allow NaN and Infinity values. Defaults to True.
            default (Callable, optional): A callable that converts values that can not be encoded
                in to something that can be JSON encoded. Defaults to None.
            sort_keys (bool, optional): Sort dictionary keys. Defaults to False.

        Returns:
            JSON: New JSON object from the given data.
        """
        json_instance: "JSON" = cls.__new__(cls)
        json = dumps(
            data,
            indent=indent,
            skipkeys=skip_keys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            default=default,
            sort_keys=sort_keys,
        )
        highlighter = JSONHighlighter() if highlight else NullHighlighter()
        json_instance.text = highlighter(json)
        json_instance.text.no_wrap = True
        json_instance.text.overflow = None
        return json_instance

    def __rich__(self) -> Text:
        return self.text


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Pretty print json")
    parser.add_argument(
        "path",
        metavar="PATH",
        help="path to file, or - for stdin",
    )
    parser.add_argument(
        "-i",
        "--indent",
        metavar="SPACES",
        type=int,
        help="Number of spaces in an indent",
        default=2,
    )
    args = parser.parse_args()

    from rich.console import Console

    console = Console()
    error_console = Console(stderr=True)

    try:
        if args.path == "-":
            json_data = sys.stdin.read()
        else:
            json_data = Path(args.path).read_text()
    except Exception as error:
        error_console.print(f"Unable to read {args.path!r}; {error}")
        sys.exit(-1)

    console.print(JSON(json_data, indent=args.indent), soft_wrap=True)

# === NexusCore/openenv\Lib\site-packages\yaml\composer.py ===

__all__ = ['Composer', 'ComposerError']

from .error import MarkedYAMLError
from .events import *
from .nodes import *

class ComposerError(MarkedYAMLError):
    pass

class Composer:

    def __init__(self):
        self.anchors = {}

    def check_node(self):
        # Drop the STREAM-START event.
        if self.check_event(StreamStartEvent):
            self.get_event()

        # If there are more documents available?
        return not self.check_event(StreamEndEvent)

    def get_node(self):
        # Get the root node of the next document.
        if not self.check_event(StreamEndEvent):
            return self.compose_document()

    def get_single_node(self):
        # Drop the STREAM-START event.
        self.get_event()

        # Compose a document if the stream is not empty.
        document = None
        if not self.check_event(StreamEndEvent):
            document = self.compose_document()

        # Ensure that the stream contains no more documents.
        if not self.check_event(StreamEndEvent):
            event = self.get_event()
            raise ComposerError("expected a single document in the stream",
                    document.start_mark, "but found another document",
                    event.start_mark)

        # Drop the STREAM-END event.
        self.get_event()

        return document

    def compose_document(self):
        # Drop the DOCUMENT-START event.
        self.get_event()

        # Compose the root node.
        node = self.compose_node(None, None)

        # Drop the DOCUMENT-END event.
        self.get_event()

        self.anchors = {}
        return node

    def compose_node(self, parent, index):
        if self.check_event(AliasEvent):
            event = self.get_event()
            anchor = event.anchor
            if anchor not in self.anchors:
                raise ComposerError(None, None, "found undefined alias %r"
                        % anchor, event.start_mark)
            return self.anchors[anchor]
        event = self.peek_event()
        anchor = event.anchor
        if anchor is not None:
            if anchor in self.anchors:
                raise ComposerError("found duplicate anchor %r; first occurrence"
                        % anchor, self.anchors[anchor].start_mark,
                        "second occurrence", event.start_mark)
        self.descend_resolver(parent, index)
        if self.check_event(ScalarEvent):
            node = self.compose_scalar_node(anchor)
        elif self.check_event(SequenceStartEvent):
            node = self.compose_sequence_node(anchor)
        elif self.check_event(MappingStartEvent):
            node = self.compose_mapping_node(anchor)
        self.ascend_resolver()
        return node

    def compose_scalar_node(self, anchor):
        event = self.get_event()
        tag = event.tag
        if tag is None or tag == '!':
            tag = self.resolve(ScalarNode, event.value, event.implicit)
        node = ScalarNode(tag, event.value,
                event.start_mark, event.end_mark, style=event.style)
        if anchor is not None:
            self.anchors[anchor] = node
        return node

    def compose_sequence_node(self, anchor):
        start_event = self.get_event()
        tag = start_event.tag
        if tag is None or tag == '!':
            tag = self.resolve(SequenceNode, None, start_event.implicit)
        node = SequenceNode(tag, [],
                start_event.start_mark, None,
                flow_style=start_event.flow_style)
        if anchor is not None:
            self.anchors[anchor] = node
        index = 0
        while not self.check_event(SequenceEndEvent):
            node.value.append(self.compose_node(node, index))
            index += 1
        end_event = self.get_event()
        node.end_mark = end_event.end_mark
        return node

    def compose_mapping_node(self, anchor):
        start_event = self.get_event()
        tag = start_event.tag
        if tag is None or tag == '!':
            tag = self.resolve(MappingNode, None, start_event.implicit)
        node = MappingNode(tag, [],
                start_event.start_mark, None,
                flow_style=start_event.flow_style)
        if anchor is not None:
            self.anchors[anchor] = node
        while not self.check_event(MappingEndEvent):
            #key_event = self.peek_event()
            item_key = self.compose_node(node, None)
            #if item_key in node.value:
            #    raise ComposerError("while composing a mapping", start_event.start_mark,
            #            "found duplicate key", key_event.start_mark)
            item_value = self.compose_node(node, item_key)
            #node.value[item_key] = item_value
            node.value.append((item_key, item_value))
        end_event = self.get_event()
        node.end_mark = end_event.end_mark
        return node


# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_v_h_e_a.py ===
from fontTools.misc import sstruct
from fontTools.misc.textTools import safeEval
from fontTools.misc.fixedTools import (
    ensureVersionIsLong as fi2ve,
    versionToFixed as ve2fi,
)
from . import DefaultTable
import math


vheaFormat = """
		>	# big endian
		tableVersion:		L
		ascent:			h
		descent:		h
		lineGap:		h
		advanceHeightMax:	H
		minTopSideBearing:	h
		minBottomSideBearing:	h
		yMaxExtent:		h
		caretSlopeRise:		h
		caretSlopeRun:		h
		caretOffset:		h
		reserved1:		h
		reserved2:		h
		reserved3:		h
		reserved4:		h
		metricDataFormat:	h
		numberOfVMetrics:	H
"""


class table__v_h_e_a(DefaultTable.DefaultTable):
    """Vertical Header table

    The ``vhea`` table contains information needed during vertical
    text layout.

    .. note::
       This converter class is kept in sync with the :class:`._h_h_e_a.table__h_h_e_a`
       table constructor.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/vhea
    """

    # Note: Keep in sync with table__h_h_e_a

    dependencies = ["vmtx", "glyf", "CFF ", "CFF2"]

    def decompile(self, data, ttFont):
        sstruct.unpack(vheaFormat, data, self)

    def compile(self, ttFont):
        if ttFont.recalcBBoxes and (
            ttFont.isLoaded("glyf")
            or ttFont.isLoaded("CFF ")
            or ttFont.isLoaded("CFF2")
        ):
            self.recalc(ttFont)
        self.tableVersion = fi2ve(self.tableVersion)
        return sstruct.pack(vheaFormat, self)

    def recalc(self, ttFont):
        if "vmtx" not in ttFont:
            return

        vmtxTable = ttFont["vmtx"]
        self.advanceHeightMax = max(adv for adv, _ in vmtxTable.metrics.values())

        boundsHeightDict = {}
        if "glyf" in ttFont:
            glyfTable = ttFont["glyf"]
            for name in ttFont.getGlyphOrder():
                g = glyfTable[name]
                if g.numberOfContours == 0:
                    continue
                if g.numberOfContours < 0 and not hasattr(g, "yMax"):
                    # Composite glyph without extents set.
                    # Calculate those.
                    g.recalcBounds(glyfTable)
                boundsHeightDict[name] = g.yMax - g.yMin
        elif "CFF " in ttFont or "CFF2" in ttFont:
            if "CFF " in ttFont:
                topDict = ttFont["CFF "].cff.topDictIndex[0]
            else:
                topDict = ttFont["CFF2"].cff.topDictIndex[0]
            charStrings = topDict.CharStrings
            for name in ttFont.getGlyphOrder():
                cs = charStrings[name]
                bounds = cs.calcBounds(charStrings)
                if bounds is not None:
                    boundsHeightDict[name] = int(
                        math.ceil(bounds[3]) - math.floor(bounds[1])
                    )

        if boundsHeightDict:
            minTopSideBearing = float("inf")
            minBottomSideBearing = float("inf")
            yMaxExtent = -float("inf")
            for name, boundsHeight in boundsHeightDict.items():
                advanceHeight, tsb = vmtxTable[name]
                bsb = advanceHeight - tsb - boundsHeight
                extent = tsb + boundsHeight
                minTopSideBearing = min(minTopSideBearing, tsb)
                minBottomSideBearing = min(minBottomSideBearing, bsb)
                yMaxExtent = max(yMaxExtent, extent)
            self.minTopSideBearing = minTopSideBearing
            self.minBottomSideBearing = minBottomSideBearing
            self.yMaxExtent = yMaxExtent

        else:  # No glyph has outlines.
            self.minTopSideBearing = 0
            self.minBottomSideBearing = 0
            self.yMaxExtent = 0

    def toXML(self, writer, ttFont):
        formatstring, names, fixes = sstruct.getformat(vheaFormat)
        for name in names:
            value = getattr(self, name)
            if name == "tableVersion":
                value = fi2ve(value)
                value = "0x%08x" % value
            writer.simpletag(name, value=value)
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "tableVersion":
            setattr(self, name, ve2fi(attrs["value"]))
            return
        setattr(self, name, safeEval(attrs["value"]))

    # reserved0 is caretOffset for legacy reasons
    @property
    def reserved0(self):
        return self.caretOffset

    @reserved0.setter
    def reserved0(self, value):
        self.caretOffset = value

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\pt_inputhooks\__init__.py ===
import importlib
import os
from typing import Tuple, Callable

aliases = {
    'qt4': 'qt',
    'gtk2': 'gtk',
}

backends = [
    "qt",
    "qt5",
    "qt6",
    "gtk",
    "gtk2",
    "gtk3",
    "gtk4",
    "tk",
    "wx",
    "pyglet",
    "glut",
    "osx",
    "asyncio",
]

registered = {}

def register(name, inputhook):
    """Register the function *inputhook* as an event loop integration."""
    registered[name] = inputhook


class UnknownBackend(KeyError):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return ("No event loop integration for {!r}. "
                "Supported event loops are: {}").format(self.name,
                                    ', '.join(backends + sorted(registered)))


def set_qt_api(gui):
    """Sets the `QT_API` environment variable if it isn't already set."""

    qt_api = os.environ.get("QT_API", None)

    from IPython.external.qt_loaders import (
        QT_API_PYQT,
        QT_API_PYQT5,
        QT_API_PYQT6,
        QT_API_PYSIDE,
        QT_API_PYSIDE2,
        QT_API_PYSIDE6,
        QT_API_PYQTv1,
        loaded_api,
    )

    loaded = loaded_api()

    qt_env2gui = {
        QT_API_PYSIDE: "qt4",
        QT_API_PYQTv1: "qt4",
        QT_API_PYQT: "qt4",
        QT_API_PYSIDE2: "qt5",
        QT_API_PYQT5: "qt5",
        QT_API_PYSIDE6: "qt6",
        QT_API_PYQT6: "qt6",
    }
    if loaded is not None and gui != "qt":
        if qt_env2gui[loaded] != gui:
            print(
                f"Cannot switch Qt versions for this session; will use {qt_env2gui[loaded]}."
            )
            return qt_env2gui[loaded]

    if qt_api is not None and gui != "qt":
        if qt_env2gui[qt_api] != gui:
            print(
                f'Request for "{gui}" will be ignored because `QT_API` '
                f'environment variable is set to "{qt_api}"'
            )
            return qt_env2gui[qt_api]
    else:
        if gui == "qt5":
            try:
                import PyQt5  # noqa

                os.environ["QT_API"] = "pyqt5"
            except ImportError:
                try:
                    import PySide2  # noqa

                    os.environ["QT_API"] = "pyside2"
                except ImportError:
                    os.environ["QT_API"] = "pyqt5"
        elif gui == "qt6":
            try:
                import PyQt6  # noqa

                os.environ["QT_API"] = "pyqt6"
            except ImportError:
                try:
                    import PySide6  # noqa

                    os.environ["QT_API"] = "pyside6"
                except ImportError:
                    os.environ["QT_API"] = "pyqt6"
        elif gui == "qt":
            # Don't set QT_API; let IPython logic choose the version.
            if "QT_API" in os.environ.keys():
                del os.environ["QT_API"]
        else:
            print(f'Unrecognized Qt version: {gui}. Should be "qt5", "qt6", or "qt".')
            return

        # Import it now so we can figure out which version it is.
        from IPython.external.qt_for_kernel import QT_API

        return qt_env2gui[QT_API]


def get_inputhook_name_and_func(gui: str) -> Tuple[str, Callable]:
    if gui in registered:
        return gui, registered[gui]

    if gui not in backends:
        raise UnknownBackend(gui)

    if gui in aliases:
        return get_inputhook_name_and_func(aliases[gui])

    gui_mod = gui
    if gui.startswith("qt"):
        gui = set_qt_api(gui)
        gui_mod = "qt"

    mod = importlib.import_module("IPython.terminal.pt_inputhooks." + gui_mod)
    return gui, mod.inputhook

# === NexusCore/openenv\Lib\site-packages\litellm\anthropic_interface\messages\__init__.py ===
"""
Interface for Anthropic's messages API

Use this to call LLMs in Anthropic /messages Request/Response format

This is an __init__.py file to allow the following interface

- litellm.messages.acreate
- litellm.messages.create

"""

from typing import Any, AsyncIterator, Coroutine, Dict, List, Optional, Union

from litellm.llms.anthropic.experimental_pass_through.messages.handler import (
    anthropic_messages as _async_anthropic_messages,
)
from litellm.llms.anthropic.experimental_pass_through.messages.handler import (
    anthropic_messages_handler as _sync_anthropic_messages,
)
from litellm.types.llms.anthropic_messages.anthropic_response import (
    AnthropicMessagesResponse,
)


async def acreate(
    max_tokens: int,
    messages: List[Dict],
    model: str,
    metadata: Optional[Dict] = None,
    stop_sequences: Optional[List[str]] = None,
    stream: Optional[bool] = False,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    thinking: Optional[Dict] = None,
    tool_choice: Optional[Dict] = None,
    tools: Optional[List[Dict]] = None,
    top_k: Optional[int] = None,
    top_p: Optional[float] = None,
    **kwargs
) -> Union[AnthropicMessagesResponse, AsyncIterator]:
    """
    Async wrapper for Anthropic's messages API

    Args:
        max_tokens (int): Maximum tokens to generate (required)
        messages (List[Dict]): List of message objects with role and content (required)
        model (str): Model name to use (required)
        metadata (Dict, optional): Request metadata
        stop_sequences (List[str], optional): Custom stop sequences
        stream (bool, optional): Whether to stream the response
        system (str, optional): System prompt
        temperature (float, optional): Sampling temperature (0.0 to 1.0)
        thinking (Dict, optional): Extended thinking configuration
        tool_choice (Dict, optional): Tool choice configuration
        tools (List[Dict], optional): List of tool definitions
        top_k (int, optional): Top K sampling parameter
        top_p (float, optional): Nucleus sampling parameter
        **kwargs: Additional arguments

    Returns:
        Dict: Response from the API
    """
    return await _async_anthropic_messages(
        max_tokens=max_tokens,
        messages=messages,
        model=model,
        metadata=metadata,
        stop_sequences=stop_sequences,
        stream=stream,
        system=system,
        temperature=temperature,
        thinking=thinking,
        tool_choice=tool_choice,
        tools=tools,
        top_k=top_k,
        top_p=top_p,
        **kwargs,
    )


def create(
    max_tokens: int,
    messages: List[Dict],
    model: str,
    metadata: Optional[Dict] = None,
    stop_sequences: Optional[List[str]] = None,
    stream: Optional[bool] = False,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    thinking: Optional[Dict] = None,
    tool_choice: Optional[Dict] = None,
    tools: Optional[List[Dict]] = None,
    top_k: Optional[int] = None,
    top_p: Optional[float] = None,
    **kwargs
) -> Union[
    AnthropicMessagesResponse,
    AsyncIterator[Any],
    Coroutine[Any, Any, Union[AnthropicMessagesResponse, AsyncIterator[Any]]],
]:
    """
    Async wrapper for Anthropic's messages API

    Args:
        max_tokens (int): Maximum tokens to generate (required)
        messages (List[Dict]): List of message objects with role and content (required)
        model (str): Model name to use (required)
        metadata (Dict, optional): Request metadata
        stop_sequences (List[str], optional): Custom stop sequences
        stream (bool, optional): Whether to stream the response
        system (str, optional): System prompt
        temperature (float, optional): Sampling temperature (0.0 to 1.0)
        thinking (Dict, optional): Extended thinking configuration
        tool_choice (Dict, optional): Tool choice configuration
        tools (List[Dict], optional): List of tool definitions
        top_k (int, optional): Top K sampling parameter
        top_p (float, optional): Nucleus sampling parameter
        **kwargs: Additional arguments

    Returns:
        Dict: Response from the API
    """
    return _sync_anthropic_messages(
        max_tokens=max_tokens,
        messages=messages,
        model=model,
        metadata=metadata,
        stop_sequences=stop_sequences,
        stream=stream,
        system=system,
        temperature=temperature,
        thinking=thinking,
        tool_choice=tool_choice,
        tools=tools,
        top_k=top_k,
        top_p=top_p,
        **kwargs,
    )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\hosted_vllm\chat\transformation.py ===
"""
Translate from OpenAI's `/v1/chat/completions` to VLLM's `/v1/chat/completions`
"""

from typing import Any, Coroutine, List, Literal, Optional, Tuple, Union, cast, overload

from litellm.litellm_core_utils.prompt_templates.common_utils import (
    _get_image_mime_type_from_url,
)
from litellm.litellm_core_utils.prompt_templates.factory import _parse_mime_type
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionFileObject,
    ChatCompletionVideoObject,
    ChatCompletionVideoUrlObject,
)

from ....utils import _remove_additional_properties, _remove_strict_from_schema
from ...openai.chat.gpt_transformation import OpenAIGPTConfig


class HostedVLLMChatConfig(OpenAIGPTConfig):
    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        _tools = non_default_params.pop("tools", None)
        if _tools is not None:
            # remove 'additionalProperties' from tools
            _tools = _remove_additional_properties(_tools)
            # remove 'strict' from tools
            _tools = _remove_strict_from_schema(_tools)
        if _tools is not None:
            non_default_params["tools"] = _tools
        return super().map_openai_params(
            non_default_params, optional_params, model, drop_params
        )

    def _get_openai_compatible_provider_info(
        self, api_base: Optional[str], api_key: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        api_base = api_base or get_secret_str("HOSTED_VLLM_API_BASE")  # type: ignore
        dynamic_api_key = (
            api_key or get_secret_str("HOSTED_VLLM_API_KEY") or "fake-api-key"
        )  # vllm does not require an api key
        return api_base, dynamic_api_key

    def _is_video_file(self, content_item: ChatCompletionFileObject) -> bool:
        """
        Check if the file is a video

        - format: video/<extension>
        - file_data: base64 encoded video data
        - file_id: infer mp4 from extension
        """
        file = content_item.get("file", {})
        format = file.get("format")
        file_data = file.get("file_data")
        file_id = file.get("file_id")
        if content_item.get("type") != "file":
            return False
        if format and format.startswith("video/"):
            return True
        elif file_data:
            mime_type = _parse_mime_type(file_data)
            if mime_type and mime_type.startswith("video/"):
                return True
        elif file_id:
            mime_type = _get_image_mime_type_from_url(file_id)
            if mime_type and mime_type.startswith("video/"):
                return True
        return False

    def _convert_file_to_video_url(
        self, content_item: ChatCompletionFileObject
    ) -> ChatCompletionVideoObject:
        file = content_item.get("file", {})
        file_id = file.get("file_id")
        file_data = file.get("file_data")

        if file_id:
            return ChatCompletionVideoObject(
                type="video_url", video_url=ChatCompletionVideoUrlObject(url=file_id)
            )
        elif file_data:
            return ChatCompletionVideoObject(
                type="video_url", video_url=ChatCompletionVideoUrlObject(url=file_data)
            )
        raise ValueError("file_id or file_data is required")

    @overload
    def _transform_messages(
        self, messages: List[AllMessageValues], model: str, is_async: Literal[True]
    ) -> Coroutine[Any, Any, List[AllMessageValues]]:
        ...

    @overload
    def _transform_messages(
        self,
        messages: List[AllMessageValues],
        model: str,
        is_async: Literal[False] = False,
    ) -> List[AllMessageValues]:
        ...

    def _transform_messages(
        self, messages: List[AllMessageValues], model: str, is_async: bool = False
    ) -> Union[List[AllMessageValues], Coroutine[Any, Any, List[AllMessageValues]]]:
        """
        Support translating video files from file_id or file_data to video_url
        """
        for message in messages:
            if message["role"] == "user":
                message_content = message.get("content")
                if message_content and isinstance(message_content, list):
                    replaced_content_items: List[
                        Tuple[int, ChatCompletionFileObject]
                    ] = []
                    for idx, content_item in enumerate(message_content):
                        if content_item.get("type") == "file":
                            content_item = cast(ChatCompletionFileObject, content_item)
                            if self._is_video_file(content_item):
                                replaced_content_items.append((idx, content_item))
                    for idx, content_item in replaced_content_items:
                        message_content[idx] = self._convert_file_to_video_url(
                            content_item
                        )
        if is_async:
            return super()._transform_messages(
                messages, model, is_async=cast(Literal[True], True)
            )
        else:
            return super()._transform_messages(
                messages, model, is_async=cast(Literal[False], False)
            )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\vertex_ai_endpoints\langfuse_endpoints.py ===
"""
What is this? 

Logging Pass-Through Endpoints
"""

"""
1. Create pass-through endpoints for any LITELLM_BASE_URL/langfuse/<endpoint> map to LANGFUSE_BASE_URL/<endpoint>
"""

import base64
import os
from base64 import b64encode
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Response

import litellm
from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.litellm_pre_call_utils import _get_dynamic_logging_metadata
from litellm.proxy.pass_through_endpoints.pass_through_endpoints import (
    create_pass_through_route,
)

router = APIRouter()
default_vertex_config = None


def create_request_copy(request: Request):
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "cookies": request.cookies,
        "query_params": dict(request.query_params),
    }


@router.api_route(
    "/langfuse/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Langfuse Pass-through", "pass-through"],
)
async def langfuse_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
):
    """
    Call Langfuse via LiteLLM proxy. Works with Langfuse SDK.

    [Docs](https://docs.litellm.ai/docs/pass_through/langfuse)
    """
    from litellm.proxy.proxy_server import proxy_config

    ## CHECK FOR LITELLM API KEY IN THE QUERY PARAMS - ?..key=LITELLM_API_KEY
    api_key = request.headers.get("Authorization") or ""

    ## decrypt base64 hash
    api_key = api_key.replace("Basic ", "")

    decoded_bytes = base64.b64decode(api_key)
    decoded_str = decoded_bytes.decode("utf-8")
    api_key = decoded_str.split(":")[1]  # assume api key is passed in as secret key

    user_api_key_dict = await user_api_key_auth(
        request=request, api_key="Bearer {}".format(api_key)
    )

    callback_settings_obj: Optional[
        TeamCallbackMetadata
    ] = _get_dynamic_logging_metadata(
        user_api_key_dict=user_api_key_dict, proxy_config=proxy_config
    )

    dynamic_langfuse_public_key: Optional[str] = None
    dynamic_langfuse_secret_key: Optional[str] = None
    dynamic_langfuse_host: Optional[str] = None
    if (
        callback_settings_obj is not None
        and callback_settings_obj.callback_vars is not None
    ):
        for k, v in callback_settings_obj.callback_vars.items():
            if k == "langfuse_public_key":
                dynamic_langfuse_public_key = v
            elif k == "langfuse_secret_key":
                dynamic_langfuse_secret_key = v
            elif k == "langfuse_host":
                dynamic_langfuse_host = v

    base_target_url: str = (
        dynamic_langfuse_host
        or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        or "https://cloud.langfuse.com"
    )
    if not (
        base_target_url.startswith("http://") or base_target_url.startswith("https://")
    ):
        # add http:// if unset, assume communicating over private network - e.g. render
        base_target_url = "http://" + base_target_url

    encoded_endpoint = httpx.URL(endpoint).path

    # Ensure endpoint starts with '/' for proper URL construction
    if not encoded_endpoint.startswith("/"):
        encoded_endpoint = "/" + encoded_endpoint

    # Construct the full target URL using httpx
    base_url = httpx.URL(base_target_url)
    updated_url = base_url.copy_with(path=encoded_endpoint)

    # Add or update query parameters
    langfuse_public_key = dynamic_langfuse_public_key or litellm.utils.get_secret(
        secret_name="LANGFUSE_PUBLIC_KEY"
    )
    langfuse_secret_key = dynamic_langfuse_secret_key or litellm.utils.get_secret(
        secret_name="LANGFUSE_SECRET_KEY"
    )

    langfuse_combined_key = "Basic " + b64encode(
        f"{langfuse_public_key}:{langfuse_secret_key}".encode("utf-8")
    ).decode("ascii")

    ## CREATE PASS-THROUGH
    endpoint_func = create_pass_through_route(
        endpoint=endpoint,
        target=str(updated_url),
        custom_headers={"Authorization": langfuse_combined_key},
    )  # dynamically construct pass-through endpoint based on incoming path
    received_value = await endpoint_func(
        request,
        fastapi_response,
        user_api_key_dict,
        query_params=dict(request.query_params),  # type: ignore
    )

    return received_value

# === NexusCore/openenv\Lib\site-packages\nltk\misc\wordfinder.py ===
# Natural Language Toolkit: Word Finder
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

# Simplified from PHP version by Robert Klein <brathna@gmail.com>
# http://fswordfinder.sourceforge.net/

import random


# reverse a word with probability 0.5
def revword(word):
    if random.randint(1, 2) == 1:
        return word[::-1]
    return word


# try to insert word at position x,y; direction encoded in xf,yf
def step(word, x, xf, y, yf, grid):
    for i in range(len(word)):
        if grid[xf(i)][yf(i)] != "" and grid[xf(i)][yf(i)] != word[i]:
            return False
    for i in range(len(word)):
        grid[xf(i)][yf(i)] = word[i]
    return True


# try to insert word at position x,y, in direction dir
def check(word, dir, x, y, grid, rows, cols):
    if dir == 1:
        if x - len(word) < 0 or y - len(word) < 0:
            return False
        return step(word, x, lambda i: x - i, y, lambda i: y - i, grid)
    elif dir == 2:
        if x - len(word) < 0:
            return False
        return step(word, x, lambda i: x - i, y, lambda i: y, grid)
    elif dir == 3:
        if x - len(word) < 0 or y + (len(word) - 1) >= cols:
            return False
        return step(word, x, lambda i: x - i, y, lambda i: y + i, grid)
    elif dir == 4:
        if y - len(word) < 0:
            return False
        return step(word, x, lambda i: x, y, lambda i: y - i, grid)


def wordfinder(words, rows=20, cols=20, attempts=50, alph="ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    """
    Attempt to arrange words into a letter-grid with the specified
    number of rows and columns.  Try each word in several positions
    and directions, until it can be fitted into the grid, or the
    maximum number of allowable attempts is exceeded.  Returns a tuple
    consisting of the grid and the words that were successfully
    placed.

    :param words: the list of words to be put into the grid
    :type words: list
    :param rows: the number of rows in the grid
    :type rows: int
    :param cols: the number of columns in the grid
    :type cols: int
    :param attempts: the number of times to attempt placing a word
    :type attempts: int
    :param alph: the alphabet, to be used for filling blank cells
    :type alph: list
    :rtype: tuple
    """

    # place longer words first
    words = sorted(words, key=len, reverse=True)

    grid = []  # the letter grid
    used = []  # the words we used

    # initialize the grid
    for i in range(rows):
        grid.append([""] * cols)

    # try to place each word
    for word in words:
        word = word.strip().upper()  # normalize
        save = word  # keep a record of the word
        word = revword(word)
        for attempt in range(attempts):
            r = random.randint(0, len(word))
            dir = random.choice([1, 2, 3, 4])
            x = random.randint(0, rows)
            y = random.randint(0, cols)
            if dir == 1:
                x += r
                y += r
            elif dir == 2:
                x += r
            elif dir == 3:
                x += r
                y -= r
            elif dir == 4:
                y += r
            if 0 <= x < rows and 0 <= y < cols:
                if check(word, dir, x, y, grid, rows, cols):
                    #                   used.append((save, dir, x, y, word))
                    used.append(save)
                    break

    # Fill up the remaining spaces
    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == "":
                grid[i][j] = random.choice(alph)

    return grid, used


def word_finder():
    from nltk.corpus import words

    wordlist = words.words()
    random.shuffle(wordlist)
    wordlist = wordlist[:200]
    wordlist = [w for w in wordlist if 3 <= len(w) <= 12]
    grid, used = wordfinder(wordlist)

    print("Word Finder\n")
    for i in range(len(grid)):
        for j in range(len(grid[i])):
            print(grid[i][j], end=" ")
        print()
    print()

    for i in range(len(used)):
        print("%d:" % (i + 1), used[i])


if __name__ == "__main__":
    word_finder()

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\simple.py ===
# Natural Language Toolkit: Simple Tokenizers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

r"""
Simple Tokenizers

These tokenizers divide strings into substrings using the string
``split()`` method.
When tokenizing using a particular delimiter string, use
the string ``split()`` method directly, as this is more efficient.

The simple tokenizers are *not* available as separate functions;
instead, you should just use the string ``split()`` method directly:

    >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks."
    >>> s.split() # doctest: +NORMALIZE_WHITESPACE
    ['Good', 'muffins', 'cost', '$3.88', 'in', 'New', 'York.',
    'Please', 'buy', 'me', 'two', 'of', 'them.', 'Thanks.']
    >>> s.split(' ') # doctest: +NORMALIZE_WHITESPACE
    ['Good', 'muffins', 'cost', '$3.88\nin', 'New', 'York.', '',
    'Please', 'buy', 'me\ntwo', 'of', 'them.\n\nThanks.']
    >>> s.split('\n') # doctest: +NORMALIZE_WHITESPACE
    ['Good muffins cost $3.88', 'in New York.  Please buy me',
    'two of them.', '', 'Thanks.']

The simple tokenizers are mainly useful because they follow the
standard ``TokenizerI`` interface, and so can be used with any code
that expects a tokenizer.  For example, these tokenizers can be used
to specify the tokenization conventions when building a `CorpusReader`.

"""

from nltk.tokenize.api import StringTokenizer, TokenizerI
from nltk.tokenize.util import regexp_span_tokenize, string_span_tokenize


class SpaceTokenizer(StringTokenizer):
    r"""Tokenize a string using the space character as a delimiter,
    which is the same as ``s.split(' ')``.

        >>> from nltk.tokenize import SpaceTokenizer
        >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks."
        >>> SpaceTokenizer().tokenize(s) # doctest: +NORMALIZE_WHITESPACE
        ['Good', 'muffins', 'cost', '$3.88\nin', 'New', 'York.', '',
        'Please', 'buy', 'me\ntwo', 'of', 'them.\n\nThanks.']
    """

    _string = " "


class TabTokenizer(StringTokenizer):
    r"""Tokenize a string use the tab character as a delimiter,
    the same as ``s.split('\t')``.

        >>> from nltk.tokenize import TabTokenizer
        >>> TabTokenizer().tokenize('a\tb c\n\t d')
        ['a', 'b c\n', ' d']
    """

    _string = "\t"


class CharTokenizer(StringTokenizer):
    """Tokenize a string into individual characters.  If this functionality
    is ever required directly, use ``for char in string``.
    """

    _string = None

    def tokenize(self, s):
        return list(s)

    def span_tokenize(self, s):
        yield from enumerate(range(1, len(s) + 1))


class LineTokenizer(TokenizerI):
    r"""Tokenize a string into its lines, optionally discarding blank lines.
    This is similar to ``s.split('\n')``.

        >>> from nltk.tokenize import LineTokenizer
        >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks."
        >>> LineTokenizer(blanklines='keep').tokenize(s) # doctest: +NORMALIZE_WHITESPACE
        ['Good muffins cost $3.88', 'in New York.  Please buy me',
        'two of them.', '', 'Thanks.']
        >>> # same as [l for l in s.split('\n') if l.strip()]:
        >>> LineTokenizer(blanklines='discard').tokenize(s) # doctest: +NORMALIZE_WHITESPACE
        ['Good muffins cost $3.88', 'in New York.  Please buy me',
        'two of them.', 'Thanks.']

    :param blanklines: Indicates how blank lines should be handled.  Valid values are:

        - ``discard``: strip blank lines out of the token list before returning it.
           A line is considered blank if it contains only whitespace characters.
        - ``keep``: leave all blank lines in the token list.
        - ``discard-eof``: if the string ends with a newline, then do not generate
           a corresponding token ``''`` after that newline.
    """

    def __init__(self, blanklines="discard"):
        valid_blanklines = ("discard", "keep", "discard-eof")
        if blanklines not in valid_blanklines:
            raise ValueError(
                "Blank lines must be one of: %s" % " ".join(valid_blanklines)
            )

        self._blanklines = blanklines

    def tokenize(self, s):
        lines = s.splitlines()
        # If requested, strip off blank lines.
        if self._blanklines == "discard":
            lines = [l for l in lines if l.rstrip()]
        elif self._blanklines == "discard-eof":
            if lines and not lines[-1].strip():
                lines.pop()
        return lines

    # discard-eof not implemented
    def span_tokenize(self, s):
        if self._blanklines == "keep":
            yield from string_span_tokenize(s, r"\n")
        else:
            yield from regexp_span_tokenize(s, r"\n(\s+\n)*")


######################################################################
# { Tokenization Functions
######################################################################
# XXX: it is stated in module docs that there is no function versions


def line_tokenize(text, blanklines="discard"):
    return LineTokenizer(blanklines).tokenize(text)

# === NexusCore/openenv\Lib\site-packages\openai\cli\_api\image.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from argparse import ArgumentParser

from .._utils import get_client, print_model
from ..._types import NOT_GIVEN, NotGiven, NotGivenOr
from .._models import BaseModel
from .._progress import BufferReader

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def register(subparser: _SubParsersAction[ArgumentParser]) -> None:
    sub = subparser.add_parser("images.generate")
    sub.add_argument("-m", "--model", type=str)
    sub.add_argument("-p", "--prompt", type=str, required=True)
    sub.add_argument("-n", "--num-images", type=int, default=1)
    sub.add_argument("-s", "--size", type=str, default="1024x1024", help="Size of the output image")
    sub.add_argument("--response-format", type=str, default="url")
    sub.set_defaults(func=CLIImage.create, args_model=CLIImageCreateArgs)

    sub = subparser.add_parser("images.edit")
    sub.add_argument("-m", "--model", type=str)
    sub.add_argument("-p", "--prompt", type=str, required=True)
    sub.add_argument("-n", "--num-images", type=int, default=1)
    sub.add_argument(
        "-I",
        "--image",
        type=str,
        required=True,
        help="Image to modify. Should be a local path and a PNG encoded image.",
    )
    sub.add_argument("-s", "--size", type=str, default="1024x1024", help="Size of the output image")
    sub.add_argument("--response-format", type=str, default="url")
    sub.add_argument(
        "-M",
        "--mask",
        type=str,
        required=False,
        help="Path to a mask image. It should be the same size as the image you're editing and a RGBA PNG image. The Alpha channel acts as the mask.",
    )
    sub.set_defaults(func=CLIImage.edit, args_model=CLIImageEditArgs)

    sub = subparser.add_parser("images.create_variation")
    sub.add_argument("-m", "--model", type=str)
    sub.add_argument("-n", "--num-images", type=int, default=1)
    sub.add_argument(
        "-I",
        "--image",
        type=str,
        required=True,
        help="Image to modify. Should be a local path and a PNG encoded image.",
    )
    sub.add_argument("-s", "--size", type=str, default="1024x1024", help="Size of the output image")
    sub.add_argument("--response-format", type=str, default="url")
    sub.set_defaults(func=CLIImage.create_variation, args_model=CLIImageCreateVariationArgs)


class CLIImageCreateArgs(BaseModel):
    prompt: str
    num_images: int
    size: str
    response_format: str
    model: NotGivenOr[str] = NOT_GIVEN


class CLIImageCreateVariationArgs(BaseModel):
    image: str
    num_images: int
    size: str
    response_format: str
    model: NotGivenOr[str] = NOT_GIVEN


class CLIImageEditArgs(BaseModel):
    image: str
    num_images: int
    size: str
    response_format: str
    prompt: str
    mask: NotGivenOr[str] = NOT_GIVEN
    model: NotGivenOr[str] = NOT_GIVEN


class CLIImage:
    @staticmethod
    def create(args: CLIImageCreateArgs) -> None:
        image = get_client().images.generate(
            model=args.model,
            prompt=args.prompt,
            n=args.num_images,
            # casts required because the API is typed for enums
            # but we don't want to validate that here for forwards-compat
            size=cast(Any, args.size),
            response_format=cast(Any, args.response_format),
        )
        print_model(image)

    @staticmethod
    def create_variation(args: CLIImageCreateVariationArgs) -> None:
        with open(args.image, "rb") as file_reader:
            buffer_reader = BufferReader(file_reader.read(), desc="Upload progress")

        image = get_client().images.create_variation(
            model=args.model,
            image=("image", buffer_reader),
            n=args.num_images,
            # casts required because the API is typed for enums
            # but we don't want to validate that here for forwards-compat
            size=cast(Any, args.size),
            response_format=cast(Any, args.response_format),
        )
        print_model(image)

    @staticmethod
    def edit(args: CLIImageEditArgs) -> None:
        with open(args.image, "rb") as file_reader:
            buffer_reader = BufferReader(file_reader.read(), desc="Image upload progress")

        if isinstance(args.mask, NotGiven):
            mask: NotGivenOr[BufferReader] = NOT_GIVEN
        else:
            with open(args.mask, "rb") as file_reader:
                mask = BufferReader(file_reader.read(), desc="Mask progress")

        image = get_client().images.edit(
            model=args.model,
            prompt=args.prompt,
            image=("image", buffer_reader),
            n=args.num_images,
            mask=("mask", mask) if not isinstance(mask, NotGiven) else mask,
            # casts required because the API is typed for enums
            # but we don't want to validate that here for forwards-compat
            size=cast(Any, args.size),
            response_format=cast(Any, args.response_format),
        )
        print_model(image)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\commands\index.py ===
import logging
from optparse import Values
from typing import Any, Iterable, List, Optional

from pip._vendor.packaging.version import Version

from pip._internal.cli import cmdoptions
from pip._internal.cli.req_command import IndexGroupCommand
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.commands.search import print_dist_installation_info
from pip._internal.exceptions import CommandError, DistributionNotFound, PipError
from pip._internal.index.collector import LinkCollector
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.models.target_python import TargetPython
from pip._internal.network.session import PipSession
from pip._internal.utils.misc import write_output

logger = logging.getLogger(__name__)


class IndexCommand(IndexGroupCommand):
    """
    Inspect information available from package indexes.
    """

    ignore_require_venv = True
    usage = """
        %prog versions <package>
    """

    def add_options(self) -> None:
        cmdoptions.add_target_python_options(self.cmd_opts)

        self.cmd_opts.add_option(cmdoptions.ignore_requires_python())
        self.cmd_opts.add_option(cmdoptions.pre())
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        handlers = {
            "versions": self.get_available_package_versions,
        }

        logger.warning(
            "pip index is currently an experimental command. "
            "It may be removed/changed in a future release "
            "without prior warning."
        )

        # Determine action
        if not args or args[0] not in handlers:
            logger.error(
                "Need an action (%s) to perform.",
                ", ".join(sorted(handlers)),
            )
            return ERROR

        action = args[0]

        # Error handling happens here, not in the action-handlers.
        try:
            handlers[action](options, args[1:])
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        return SUCCESS

    def _build_package_finder(
        self,
        options: Values,
        session: PipSession,
        target_python: Optional[TargetPython] = None,
        ignore_requires_python: Optional[bool] = None,
    ) -> PackageFinder:
        """
        Create a package finder appropriate to the index command.
        """
        link_collector = LinkCollector.create(session, options=options)

        # Pass allow_yanked=False to ignore yanked versions.
        selection_prefs = SelectionPreferences(
            allow_yanked=False,
            allow_all_prereleases=options.pre,
            ignore_requires_python=ignore_requires_python,
        )

        return PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=selection_prefs,
            target_python=target_python,
        )

    def get_available_package_versions(self, options: Values, args: List[Any]) -> None:
        if len(args) != 1:
            raise CommandError("You need to specify exactly one argument")

        target_python = cmdoptions.make_target_python(options)
        query = args[0]

        with self._build_session(options) as session:
            finder = self._build_package_finder(
                options=options,
                session=session,
                target_python=target_python,
                ignore_requires_python=options.ignore_requires_python,
            )

            versions: Iterable[Version] = (
                candidate.version for candidate in finder.find_all_candidates(query)
            )

            if not options.pre:
                # Remove prereleases
                versions = (
                    version for version in versions if not version.is_prerelease
                )
            versions = set(versions)

            if not versions:
                raise DistributionNotFound(
                    f"No matching distribution found for {query}"
                )

            formatted_versions = [str(ver) for ver in sorted(versions, reverse=True)]
            latest = formatted_versions[0]

        write_output(f"{query} ({latest})")
        write_output("Available versions: {}".format(", ".join(formatted_versions)))
        print_dist_installation_info(query, latest)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\resolvelib\base.py ===
from dataclasses import dataclass
from typing import FrozenSet, Iterable, Optional, Tuple

from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import NormalizedName
from pip._vendor.packaging.version import Version

from pip._internal.models.link import Link, links_equivalent
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.hashes import Hashes

CandidateLookup = Tuple[Optional["Candidate"], Optional[InstallRequirement]]


def format_name(project: NormalizedName, extras: FrozenSet[NormalizedName]) -> str:
    if not extras:
        return project
    extras_expr = ",".join(sorted(extras))
    return f"{project}[{extras_expr}]"


@dataclass(frozen=True)
class Constraint:
    specifier: SpecifierSet
    hashes: Hashes
    links: FrozenSet[Link]

    @classmethod
    def empty(cls) -> "Constraint":
        return Constraint(SpecifierSet(), Hashes(), frozenset())

    @classmethod
    def from_ireq(cls, ireq: InstallRequirement) -> "Constraint":
        links = frozenset([ireq.link]) if ireq.link else frozenset()
        return Constraint(ireq.specifier, ireq.hashes(trust_internet=False), links)

    def __bool__(self) -> bool:
        return bool(self.specifier) or bool(self.hashes) or bool(self.links)

    def __and__(self, other: InstallRequirement) -> "Constraint":
        if not isinstance(other, InstallRequirement):
            return NotImplemented
        specifier = self.specifier & other.specifier
        hashes = self.hashes & other.hashes(trust_internet=False)
        links = self.links
        if other.link:
            links = links.union([other.link])
        return Constraint(specifier, hashes, links)

    def is_satisfied_by(self, candidate: "Candidate") -> bool:
        # Reject if there are any mismatched URL constraints on this package.
        if self.links and not all(_match_link(link, candidate) for link in self.links):
            return False
        # We can safely always allow prereleases here since PackageFinder
        # already implements the prerelease logic, and would have filtered out
        # prerelease candidates if the user does not expect them.
        return self.specifier.contains(candidate.version, prereleases=True)


class Requirement:
    @property
    def project_name(self) -> NormalizedName:
        """The "project name" of a requirement.

        This is different from ``name`` if this requirement contains extras,
        in which case ``name`` would contain the ``[...]`` part, while this
        refers to the name of the project.
        """
        raise NotImplementedError("Subclass should override")

    @property
    def name(self) -> str:
        """The name identifying this requirement in the resolver.

        This is different from ``project_name`` if this requirement contains
        extras, where ``project_name`` would not contain the ``[...]`` part.
        """
        raise NotImplementedError("Subclass should override")

    def is_satisfied_by(self, candidate: "Candidate") -> bool:
        return False

    def get_candidate_lookup(self) -> CandidateLookup:
        raise NotImplementedError("Subclass should override")

    def format_for_error(self) -> str:
        raise NotImplementedError("Subclass should override")


def _match_link(link: Link, candidate: "Candidate") -> bool:
    if candidate.source_link:
        return links_equivalent(link, candidate.source_link)
    return False


class Candidate:
    @property
    def project_name(self) -> NormalizedName:
        """The "project name" of the candidate.

        This is different from ``name`` if this candidate contains extras,
        in which case ``name`` would contain the ``[...]`` part, while this
        refers to the name of the project.
        """
        raise NotImplementedError("Override in subclass")

    @property
    def name(self) -> str:
        """The name identifying this candidate in the resolver.

        This is different from ``project_name`` if this candidate contains
        extras, where ``project_name`` would not contain the ``[...]`` part.
        """
        raise NotImplementedError("Override in subclass")

    @property
    def version(self) -> Version:
        raise NotImplementedError("Override in subclass")

    @property
    def is_installed(self) -> bool:
        raise NotImplementedError("Override in subclass")

    @property
    def is_editable(self) -> bool:
        raise NotImplementedError("Override in subclass")

    @property
    def source_link(self) -> Optional[Link]:
        raise NotImplementedError("Override in subclass")

    def iter_dependencies(self, with_requires: bool) -> Iterable[Optional[Requirement]]:
        raise NotImplementedError("Override in subclass")

    def get_install_requirement(self) -> Optional[InstallRequirement]:
        raise NotImplementedError("Override in subclass")

    def format_for_error(self) -> str:
        raise NotImplementedError("Subclass should override")

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\json.py ===
from pathlib import Path
from json import loads, dumps
from typing import Any, Callable, Optional, Union

from .text import Text
from .highlighter import JSONHighlighter, NullHighlighter


class JSON:
    """A renderable which pretty prints JSON.

    Args:
        json (str): JSON encoded data.
        indent (Union[None, int, str], optional): Number of characters to indent by. Defaults to 2.
        highlight (bool, optional): Enable highlighting. Defaults to True.
        skip_keys (bool, optional): Skip keys not of a basic type. Defaults to False.
        ensure_ascii (bool, optional): Escape all non-ascii characters. Defaults to False.
        check_circular (bool, optional): Check for circular references. Defaults to True.
        allow_nan (bool, optional): Allow NaN and Infinity values. Defaults to True.
        default (Callable, optional): A callable that converts values that can not be encoded
            in to something that can be JSON encoded. Defaults to None.
        sort_keys (bool, optional): Sort dictionary keys. Defaults to False.
    """

    def __init__(
        self,
        json: str,
        indent: Union[None, int, str] = 2,
        highlight: bool = True,
        skip_keys: bool = False,
        ensure_ascii: bool = False,
        check_circular: bool = True,
        allow_nan: bool = True,
        default: Optional[Callable[[Any], Any]] = None,
        sort_keys: bool = False,
    ) -> None:
        data = loads(json)
        json = dumps(
            data,
            indent=indent,
            skipkeys=skip_keys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            default=default,
            sort_keys=sort_keys,
        )
        highlighter = JSONHighlighter() if highlight else NullHighlighter()
        self.text = highlighter(json)
        self.text.no_wrap = True
        self.text.overflow = None

    @classmethod
    def from_data(
        cls,
        data: Any,
        indent: Union[None, int, str] = 2,
        highlight: bool = True,
        skip_keys: bool = False,
        ensure_ascii: bool = False,
        check_circular: bool = True,
        allow_nan: bool = True,
        default: Optional[Callable[[Any], Any]] = None,
        sort_keys: bool = False,
    ) -> "JSON":
        """Encodes a JSON object from arbitrary data.

        Args:
            data (Any): An object that may be encoded in to JSON
            indent (Union[None, int, str], optional): Number of characters to indent by. Defaults to 2.
            highlight (bool, optional): Enable highlighting. Defaults to True.
            default (Callable, optional): Optional callable which will be called for objects that cannot be serialized. Defaults to None.
            skip_keys (bool, optional): Skip keys not of a basic type. Defaults to False.
            ensure_ascii (bool, optional): Escape all non-ascii characters. Defaults to False.
            check_circular (bool, optional): Check for circular references. Defaults to True.
            allow_nan (bool, optional): Allow NaN and Infinity values. Defaults to True.
            default (Callable, optional): A callable that converts values that can not be encoded
                in to something that can be JSON encoded. Defaults to None.
            sort_keys (bool, optional): Sort dictionary keys. Defaults to False.

        Returns:
            JSON: New JSON object from the given data.
        """
        json_instance: "JSON" = cls.__new__(cls)
        json = dumps(
            data,
            indent=indent,
            skipkeys=skip_keys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            default=default,
            sort_keys=sort_keys,
        )
        highlighter = JSONHighlighter() if highlight else NullHighlighter()
        json_instance.text = highlighter(json)
        json_instance.text.no_wrap = True
        json_instance.text.overflow = None
        return json_instance

    def __rich__(self) -> Text:
        return self.text


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Pretty print json")
    parser.add_argument(
        "path",
        metavar="PATH",
        help="path to file, or - for stdin",
    )
    parser.add_argument(
        "-i",
        "--indent",
        metavar="SPACES",
        type=int,
        help="Number of spaces in an indent",
        default=2,
    )
    args = parser.parse_args()

    from pip._vendor.rich.console import Console

    console = Console()
    error_console = Console(stderr=True)

    try:
        if args.path == "-":
            json_data = sys.stdin.read()
        else:
            json_data = Path(args.path).read_text()
    except Exception as error:
        error_console.print(f"Unable to read {args.path!r}; {error}")
        sys.exit(-1)

    console.print(JSON(json_data, indent=args.indent), soft_wrap=True)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\chapel.py ===
"""
    pygments.lexers.chapel
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Chapel language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

__all__ = ['ChapelLexer']


class ChapelLexer(RegexLexer):
    """
    For Chapel source.
    """
    name = 'Chapel'
    url = 'https://chapel-lang.org/'
    filenames = ['*.chpl']
    aliases = ['chapel', 'chpl']
    version_added = '2.0'
    # mimetypes = ['text/x-chapel']

    known_types = ('bool', 'bytes', 'complex', 'imag', 'int', 'locale',
                   'nothing', 'opaque', 'range', 'real', 'string', 'uint',
                   'void')

    type_modifiers_par = ('atomic', 'single', 'sync')
    type_modifiers_mem = ('borrowed', 'owned', 'shared', 'unmanaged')
    type_modifiers = (*type_modifiers_par, *type_modifiers_mem)

    declarations = ('config', 'const', 'in', 'inout', 'out', 'param', 'ref',
                    'type', 'var')

    constants = ('false', 'nil', 'none', 'true')

    other_keywords = ('align', 'as',
                      'begin', 'break', 'by',
                      'catch', 'cobegin', 'coforall', 'continue',
                      'defer', 'delete', 'dmapped', 'do', 'domain',
                      'else', 'enum', 'except', 'export', 'extern',
                      'for', 'forall', 'foreach', 'forwarding',
                      'if', 'implements', 'import', 'index', 'init', 'inline',
                      'label', 'lambda', 'let', 'lifetime', 'local',
                      'new', 'noinit',
                      'on', 'only', 'otherwise', 'override',
                      'pragma', 'primitive', 'private', 'prototype', 'public',
                      'reduce', 'require', 'return',
                      'scan', 'select', 'serial', 'sparse', 'subdomain',
                      'then', 'this', 'throw', 'throws', 'try',
                      'use',
                      'when', 'where', 'while', 'with',
                      'yield',
                      'zip')

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            (r'\\\n', Text),

            (r'//(.*?)\n', Comment.Single),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),

            (words(declarations, suffix=r'\b'), Keyword.Declaration),
            (words(constants, suffix=r'\b'), Keyword.Constant),
            (words(known_types, suffix=r'\b'), Keyword.Type),
            (words((*type_modifiers, *other_keywords), suffix=r'\b'), Keyword),

            (r'@', Keyword, 'attributename'),
            (r'(iter)(\s+)', bygroups(Keyword, Whitespace), 'procname'),
            (r'(proc)(\s+)', bygroups(Keyword, Whitespace), 'procname'),
            (r'(operator)(\s+)', bygroups(Keyword, Whitespace), 'procname'),
            (r'(class|interface|module|record|union)(\s+)', bygroups(Keyword, Whitespace),
             'classname'),

            # imaginary integers
            (r'\d+i', Number),
            (r'\d+\.\d*([Ee][-+]\d+)?i', Number),
            (r'\.\d+([Ee][-+]\d+)?i', Number),
            (r'\d+[Ee][-+]\d+i', Number),

            # reals cannot end with a period due to lexical ambiguity with
            # .. operator. See reference for rationale.
            (r'(\d*\.\d+)([eE][+-]?[0-9]+)?i?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+i?', Number.Float),

            # integer literals
            # -- binary
            (r'0[bB][01]+', Number.Bin),
            # -- hex
            (r'0[xX][0-9a-fA-F]+', Number.Hex),
            # -- octal
            (r'0[oO][0-7]+', Number.Oct),
            # -- decimal
            (r'[0-9]+', Number.Integer),

            # strings
            (r'"(\\\\|\\"|[^"])*"', String),
            (r"'(\\\\|\\'|[^'])*'", String),

            # tokens
            (r'(=|\+=|-=|\*=|/=|\*\*=|%=|&=|\|=|\^=|&&=|\|\|=|<<=|>>=|'
             r'<=>|<~>|\.\.|by|#|\.\.\.|'
             r'&&|\|\||!|&|\||\^|~|<<|>>|'
             r'==|!=|<=|>=|<|>|'
             r'[+\-*/%]|\*\*)', Operator),
            (r'[:;,.?()\[\]{}]', Punctuation),

            # identifiers
            (r'[a-zA-Z_][\w$]*', Name.Other),
        ],
        'classname': [
            (r'[a-zA-Z_][\w$]*', Name.Class, '#pop'),
        ],
        'procname': [
            (r'([a-zA-Z_][.\w$]*|'  # regular function name, including secondary
             r'\~[a-zA-Z_][.\w$]*|'  # support for legacy destructors
             r'[+*/!~%<>=&^|\-:]{1,2})',  # operators
             Name.Function, '#pop'),

            # allow `proc (atomic T).foo`
            (r'\(', Punctuation, "receivertype"),
            (r'\)+\.', Punctuation),
        ],
        'receivertype': [
            (words(type_modifiers, suffix=r'\b'), Keyword),
            (words(known_types, suffix=r'\b'), Keyword.Type),
            (r'[^()]*', Name.Other, '#pop'),
        ],
        'attributename': [
            (r'[a-zA-Z_][.\w$]*', Name.Decorator, '#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\meson.py ===
"""
    pygments.lexers.meson
    ~~~~~~~~~~~~~~~~~~~~~

    Pygments lexer for the Meson build system

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, words, include
from pygments.token import Comment, Name, Number, Punctuation, Operator, \
    Keyword, String, Whitespace

__all__ = ['MesonLexer']


class MesonLexer(RegexLexer):
    """Meson language lexer.

    The grammar definition use to transcribe the syntax was retrieved from
    https://mesonbuild.com/Syntax.html#grammar for version 0.58.
    Some of those definitions are improperly transcribed, so the Meson++
    implementation was also checked: https://github.com/dcbaker/meson-plus-plus.
    """

    # TODO String interpolation @VARNAME@ inner matches
    # TODO keyword_arg: value inner matches

    name = 'Meson'
    url = 'https://mesonbuild.com/'
    aliases = ['meson', 'meson.build']
    filenames = ['meson.build', 'meson_options.txt']
    mimetypes = ['text/x-meson']
    version_added = '2.10'

    tokens = {
        'root': [
            (r'#.*?$', Comment),
            (r"'''.*'''", String.Single),
            (r'[1-9][0-9]*', Number.Integer),
            (r'0o[0-7]+', Number.Oct),
            (r'0x[a-fA-F0-9]+', Number.Hex),
            include('string'),
            include('keywords'),
            include('expr'),
            (r'[a-zA-Z_][a-zA-Z_0-9]*', Name),
            (r'\s+', Whitespace),
        ],
        'string': [
            (r"[']{3}([']{0,2}([^\\']|\\(.|\n)))*[']{3}", String),
            (r"'.*?(?<!\\)(\\\\)*?'", String),
        ],
        'keywords': [
            (words((
                'if',
                'elif',
                'else',
                'endif',
                'foreach',
                'endforeach',
                'break',
                'continue',
            ),
                   suffix=r'\b'), Keyword),
        ],
        'expr': [
            (r'(in|and|or|not)\b', Operator.Word),
            (r'(\*=|/=|%=|\+]=|-=|==|!=|\+|-|=)', Operator),
            (r'[\[\]{}:().,?]', Punctuation),
            (words(('true', 'false'), suffix=r'\b'), Keyword.Constant),
            include('builtins'),
            (words((
                'meson',
                'build_machine',
                'host_machine',
                'target_machine',
            ),
                   suffix=r'\b'), Name.Variable.Magic),
        ],
        'builtins': [
            # This list was extracted from the v0.58 reference manual
            (words((
                'add_global_arguments',
                'add_global_link_arguments',
                'add_languages',
                'add_project_arguments',
                'add_project_link_arguments',
                'add_test_setup',
                'assert',
                'benchmark',
                'both_libraries',
                'build_target',
                'configuration_data',
                'configure_file',
                'custom_target',
                'declare_dependency',
                'dependency',
                'disabler',
                'environment',
                'error',
                'executable',
                'files',
                'find_library',
                'find_program',
                'generator',
                'get_option',
                'get_variable',
                'include_directories',
                'install_data',
                'install_headers',
                'install_man',
                'install_subdir',
                'is_disabler',
                'is_variable',
                'jar',
                'join_paths',
                'library',
                'message',
                'project',
                'range',
                'run_command',
                'set_variable',
                'shared_library',
                'shared_module',
                'static_library',
                'subdir',
                'subdir_done',
                'subproject',
                'summary',
                'test',
                'vcs_tag',
                'warning',
            ),
                   prefix=r'(?<!\.)',
                   suffix=r'\b'), Name.Builtin),
            (r'(?<!\.)import\b', Name.Namespace),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\selenium_manager.py ===
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
import json
import logging
import os
import platform
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import List, Optional

from selenium.common import WebDriverException

logger = logging.getLogger(__name__)


class SeleniumManager:
    """Wrapper for getting information from the Selenium Manager binaries.

    This implementation is still in beta, and may change.
    """

    def binary_paths(self, args: List) -> dict:
        """Determines the locations of the requested assets.

        :Args:
         - args: the commands to send to the selenium manager binary.
        :Returns: dictionary of assets and their path
        """

        args = [str(self._get_binary())] + args
        if logger.getEffectiveLevel() == logging.DEBUG:
            args.append("--debug")
        args.append("--language-binding")
        args.append("python")
        args.append("--output")
        args.append("json")

        return self._run(args)

    @staticmethod
    def _get_binary() -> Path:
        """Determines the path of the correct Selenium Manager binary.

        :Returns: The Selenium Manager executable location

        :Raises: WebDriverException if the platform is unsupported
        """

        compiled_path = Path(__file__).parent.joinpath("selenium-manager")
        exe = sysconfig.get_config_var("EXE")
        if exe is not None:
            compiled_path = compiled_path.with_suffix(exe)

        path: Optional[Path] = None

        if (env_path := os.getenv("SE_MANAGER_PATH")) is not None:
            logger.debug("Selenium Manager set by env SE_MANAGER_PATH to: %s", env_path)
            path = Path(env_path)
        elif compiled_path.exists():
            path = compiled_path
        else:
            allowed = {
                ("darwin", "any"): "macos/selenium-manager",
                ("win32", "any"): "windows/selenium-manager.exe",
                ("cygwin", "any"): "windows/selenium-manager.exe",
                ("linux", "x86_64"): "linux/selenium-manager",
                ("freebsd", "x86_64"): "linux/selenium-manager",
                ("openbsd", "x86_64"): "linux/selenium-manager",
            }

            arch = platform.machine() if sys.platform in ("linux", "freebsd", "openbsd") else "any"
            if sys.platform in ["freebsd", "openbsd"]:
                logger.warning("Selenium Manager binary may not be compatible with %s; verify settings", sys.platform)

            location = allowed.get((sys.platform, arch))
            if location is None:
                raise WebDriverException(f"Unsupported platform/architecture combination: {sys.platform}/{arch}")

            path = Path(__file__).parent.joinpath(location)

        if path is None or not path.is_file():
            raise WebDriverException(f"Unable to obtain working Selenium Manager binary; {path}")

        logger.debug("Selenium Manager binary found at: %s", path)

        return path

    @staticmethod
    def _run(args: List[str]) -> dict:
        """Executes the Selenium Manager Binary.

        :Args:
         - args: the components of the command being executed.
        :Returns: The log string containing the driver location.
        """
        command = " ".join(args)
        logger.debug("Executing process: %s", command)
        try:
            if sys.platform == "win32":
                completed_proc = subprocess.run(args, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                completed_proc = subprocess.run(args, capture_output=True)
            stdout = completed_proc.stdout.decode("utf-8").rstrip("\n")
            stderr = completed_proc.stderr.decode("utf-8").rstrip("\n")
            output = json.loads(stdout) if stdout != "" else {"logs": [], "result": {}}
        except Exception as err:
            raise WebDriverException(f"Unsuccessful command executed: {command}") from err

        SeleniumManager._process_logs(output["logs"])
        result = output["result"]
        if completed_proc.returncode:
            raise WebDriverException(
                f"Unsuccessful command executed: {command}; code: {completed_proc.returncode}\n{result}\n{stderr}"
            )
        return result

    @staticmethod
    def _process_logs(log_items: List[dict]):
        for item in log_items:
            if item["level"] == "WARN":
                logger.warning(item["message"])
            elif item["level"] in ["DEBUG", "INFO"]:
                logger.debug(item["message"])