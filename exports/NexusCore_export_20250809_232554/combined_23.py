
# === NexusCore/src\nexuscore\code_interpreter\BaseCodeInterpreter.py ===
import os
import sys
import re

prj_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(prj_root_path)


from nexuscore.utils.const import *

class BaseCodeInterpreter:
    def __init__(self):
        self.dialog = [
            {
                "role": "system",
                "content": CODE_INTERPRETER_SYSTEM_PROMPT,
            },
        ]

    @staticmethod
    def extract_code_blocks(text: str):
        pattern = r"```(?:python\n)?(.*?)```"  # Match optional 'python\n' but don't capture it
        code_blocks = re.findall(pattern, text, re.DOTALL)
        return [block.strip() for block in code_blocks]

    def execute_code_and_return_output(self, code_str: str, nb):
        _, _ = nb.add_and_run(GUARD_CODE)
        outputs, error_flag = nb.add_and_run(code_str)
        return outputs, error_flag

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\code_interpreter\BaseCodeInterpreter.py ===
import os
import sys
import re

prj_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(prj_root_path)


from utils.const import *

class BaseCodeInterpreter:
    def __init__(self):
        self.dialog = [
            {
                "role": "system",
                "content": CODE_INTERPRETER_SYSTEM_PROMPT,
            },
        ]

    @staticmethod
    def extract_code_blocks(text: str):
        pattern = r"```(?:python\n)?(.*?)```"  # Match optional 'python\n' but don't capture it
        code_blocks = re.findall(pattern, text, re.DOTALL)
        return [block.strip() for block in code_blocks]

    def execute_code_and_return_output(self, code_str: str, nb):
        _, _ = nb.add_and_run(GUARD_CODE)
        outputs, error_flag = nb.add_and_run(code_str)
        return outputs, error_flag

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\code_interpreter\BaseCodeInterpreter.py ===
import os
import sys
import re

prj_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(prj_root_path)


from utils.const import *

class BaseCodeInterpreter:
    def __init__(self):
        self.dialog = [
            {
                "role": "system",
                "content": CODE_INTERPRETER_SYSTEM_PROMPT,
            },
        ]

    @staticmethod
    def extract_code_blocks(text: str):
        pattern = r"```(?:python\n)?(.*?)```"  # Match optional 'python\n' but don't capture it
        code_blocks = re.findall(pattern, text, re.DOTALL)
        return [block.strip() for block in code_blocks]

    def execute_code_and_return_output(self, code_str: str, nb):
        _, _ = nb.add_and_run(GUARD_CODE)
        outputs, error_flag = nb.add_and_run(code_str)
        return outputs, error_flag

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32gui_struct.py ===
# This is a work in progress - see Demos/win32gui_menu.py

# win32gui_struct.py - helpers for working with various win32gui structures.
# As win32gui is "light-weight", it does not define objects for all possible
# win32 structures - in general, "buffer" objects are passed around - it is
# the callers responsibility to pack the buffer in the correct format.
#
# This module defines some helpers for the commonly used structures.
#
# In general, each structure has 3 functions:
#
# buffer, extras = PackSTRUCTURE(items, ...)
# item, ... = UnpackSTRUCTURE(buffer)
# buffer, extras = EmtpySTRUCTURE(...)
#
# 'extras' is always items that must be held along with the buffer, as the
# buffer refers to these object's memory.
# For structures that support a 'mask', this mask is hidden from the user - if
# 'None' is passed, the mask flag will not be set, or on return, None will
# be returned for the value if the mask is not set.
#
# NOTE: I considered making these structures look like real classes, and
# support 'attributes' etc - however, ctypes already has a good structure
# mechanism - I think it makes more sense to support ctype structures
# at the win32gui level, then there will be no need for this module at all.
# XXX - the above makes sense in terms of what is built and passed to
# win32gui (ie, the Pack* functions) - but doesn't make as much sense for
# the Unpack* functions, where the aim is user convenience.

import array
import struct
import sys
from collections import namedtuple

import commctrl
import pywintypes
import win32con
import win32gui


def _MakeResult(names_str, values):
    names = names_str.split()
    # TODO: Dynamic namedtuple. This could be made static, also exposing the types
    nt = namedtuple(names[0], names[1:])  # noqa: PYI024
    return nt(*values)


is64bit = "64 bit" in sys.version
_nmhdr_fmt = "PPi"
if is64bit:
    # When the item past the NMHDR gets aligned (eg, when it is a struct)
    # we need this many bytes padding.
    _nmhdr_align_padding = "xxxx"
else:
    _nmhdr_align_padding = ""


# Encode a string suitable for passing in a win32gui related structure
def _make_text_buffer(text):
    if not isinstance(text, str):
        raise TypeError("MENUITEMINFO text must be unicode")
    data = (text + "\0").encode("utf-16le")
    return array.array("b", data)


# make an 'empty' buffer, ready for filling with cch characters.
def _make_empty_text_buffer(cch):
    return _make_text_buffer("\0" * cch)


# Generic WM_NOTIFY unpacking
def UnpackWMNOTIFY(lparam):
    format = "PPi"
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    return _MakeResult("WMNOTIFY hwndFrom idFrom code", struct.unpack(format, buf))


def UnpackNMITEMACTIVATE(lparam):
    format = _nmhdr_fmt + _nmhdr_align_padding
    if is64bit:
        # the struct module doesn't handle this correctly as some of the items
        # are actually structs in structs, which get individually aligned.
        format += "iiiiiiixxxxP"
    else:
        format += "iiiiiiiP"
    buf = win32gui.PyMakeBuffer(struct.calcsize(format), lparam)
    return _MakeResult(
        "NMITEMACTIVATE hwndFrom idFrom code iItem iSubItem uNewState uOldState uChanged actionx actiony lParam",
        struct.unpack(format, buf),
    )


# MENUITEMINFO struct
# https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-menuiteminfow
# We use the struct module to pack and unpack strings as MENUITEMINFO
# structures.  We also have special handling for the 'fMask' item in that
# structure to avoid the caller needing to explicitly check validity
# (None is used if the mask excludes/should exclude the value)
_menuiteminfo_fmt = "5i5PiP"


def PackMENUITEMINFO(
    fType=None,
    fState=None,
    wID=None,
    hSubMenu=None,
    hbmpChecked=None,
    hbmpUnchecked=None,
    dwItemData=None,
    text=None,
    hbmpItem=None,
    dwTypeData=None,
):
    # 'extras' are objects the caller must keep a reference to (as their
    # memory is used) for the lifetime of the INFO item.
    extras = []
    # ack - dwItemData and dwTypeData were confused for a while...
    assert (
        dwItemData is None or dwTypeData is None
    ), "sorry - these were confused - you probably want dwItemData"
    # if we are a long way past 209, then we can nuke the above...
    if dwTypeData is not None:
        import warnings

        warnings.warn("PackMENUITEMINFO: please use dwItemData instead of dwTypeData")
    if dwItemData is None:
        dwItemData = dwTypeData or 0

    fMask = 0
    if fType is None:
        fType = 0
    else:
        fMask |= win32con.MIIM_FTYPE
    if fState is None:
        fState = 0
    else:
        fMask |= win32con.MIIM_STATE
    if wID is None:
        wID = 0
    else:
        fMask |= win32con.MIIM_ID
    if hSubMenu is None:
        hSubMenu = 0
    else:
        fMask |= win32con.MIIM_SUBMENU
    if hbmpChecked is None:
        assert hbmpUnchecked is None, "neither or both checkmark bmps must be given"
        hbmpChecked = hbmpUnchecked = 0
    else:
        assert hbmpUnchecked is not None, "neither or both checkmark bmps must be given"
        fMask |= win32con.MIIM_CHECKMARKS
    if dwItemData is None:
        dwItemData = 0
    else:
        fMask |= win32con.MIIM_DATA
    if hbmpItem is None:
        hbmpItem = 0
    else:
        fMask |= win32con.MIIM_BITMAP
    if text is not None:
        fMask |= win32con.MIIM_STRING
        str_buf = _make_text_buffer(text)
        cch = len(text)
        # We are taking address of strbuf - it must not die until windows
        # has finished with our structure.
        lptext = str_buf.buffer_info()[0]
        extras.append(str_buf)
    else:
        lptext = 0
        cch = 0
    # Create the struct.
    # 'P' format does not accept PyHANDLE's !
    item = struct.pack(
        _menuiteminfo_fmt,
        struct.calcsize(_menuiteminfo_fmt),  # cbSize
        fMask,
        fType,
        fState,
        wID,
        int(hSubMenu),
        int(hbmpChecked),
        int(hbmpUnchecked),
        dwItemData,
        lptext,
        cch,
        int(hbmpItem),
    )
    # Now copy the string to a writable buffer, so that the result
    # could be passed to a 'Get' function
    return array.array("b", item), extras


def UnpackMENUITEMINFO(s):
    (
        cb,
        fMask,
        fType,
        fState,
        wID,
        hSubMenu,
        hbmpChecked,
        hbmpUnchecked,
        dwItemData,
        lptext,
        cch,
        hbmpItem,
    ) = struct.unpack(_menuiteminfo_fmt, s)
    assert cb == len(s)
    if fMask & win32con.MIIM_FTYPE == 0:
        fType = None
    if fMask & win32con.MIIM_STATE == 0:
        fState = None
    if fMask & win32con.MIIM_ID == 0:
        wID = None
    if fMask & win32con.MIIM_SUBMENU == 0:
        hSubMenu = None
    if fMask & win32con.MIIM_CHECKMARKS == 0:
        hbmpChecked = hbmpUnchecked = None
    if fMask & win32con.MIIM_DATA == 0:
        dwItemData = None
    if fMask & win32con.MIIM_BITMAP == 0:
        hbmpItem = None
    if fMask & win32con.MIIM_STRING:
        text = win32gui.PyGetString(lptext, cch)
    else:
        text = None
    return _MakeResult(
        "MENUITEMINFO fType fState wID hSubMenu hbmpChecked "
        "hbmpUnchecked dwItemData text hbmpItem",
        (
            fType,
            fState,
            wID,
            hSubMenu,
            hbmpChecked,
            hbmpUnchecked,
            dwItemData,
            text,
            hbmpItem,
        ),
    )


def EmptyMENUITEMINFO(mask=None, text_buf_size=512):
    # text_buf_size is number of *characters* - not necessarily no of bytes.
    extra = []
    if mask is None:
        mask = (
            win32con.MIIM_BITMAP
            | win32con.MIIM_CHECKMARKS
            | win32con.MIIM_DATA
            | win32con.MIIM_FTYPE
            | win32con.MIIM_ID
            | win32con.MIIM_STATE
            | win32con.MIIM_STRING
            | win32con.MIIM_SUBMENU
        )
        # Note: No MIIM_TYPE - this screws win2k/98.

    if mask & win32con.MIIM_STRING:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0

    # Now copy the string to a writable buffer, so that the result
    # could be passed to a 'Get' function
    buf = struct.pack(
        _menuiteminfo_fmt,
        struct.calcsize(_menuiteminfo_fmt),  # cbSize
        mask,
        0,  # fType,
        0,  # fState,
        0,  # wID,
        0,  # hSubMenu,
        0,  # hbmpChecked,
        0,  # hbmpUnchecked,
        0,  # dwItemData,
        text_addr,
        text_buf_size,
        0,  # hbmpItem
    )
    return array.array("b", buf), extra


# MENUINFO struct
_menuinfo_fmt = "iiiiPiP"


def PackMENUINFO(
    dwStyle=None,
    cyMax=None,
    hbrBack=None,
    dwContextHelpID=None,
    dwMenuData=None,
    fMask=0,
):
    if dwStyle is None:
        dwStyle = 0
    else:
        fMask |= win32con.MIM_STYLE
    if cyMax is None:
        cyMax = 0
    else:
        fMask |= win32con.MIM_MAXHEIGHT
    if hbrBack is None:
        hbrBack = 0
    else:
        fMask |= win32con.MIM_BACKGROUND
    if dwContextHelpID is None:
        dwContextHelpID = 0
    else:
        fMask |= win32con.MIM_HELPID
    if dwMenuData is None:
        dwMenuData = 0
    else:
        fMask |= win32con.MIM_MENUDATA
    # Create the struct.
    item = struct.pack(
        _menuinfo_fmt,
        struct.calcsize(_menuinfo_fmt),  # cbSize
        fMask,
        dwStyle,
        cyMax,
        hbrBack,
        dwContextHelpID,
        dwMenuData,
    )
    return array.array("b", item)


def UnpackMENUINFO(s):
    (cb, fMask, dwStyle, cyMax, hbrBack, dwContextHelpID, dwMenuData) = struct.unpack(
        _menuinfo_fmt, s
    )
    assert cb == len(s)
    if fMask & win32con.MIM_STYLE == 0:
        dwStyle = None
    if fMask & win32con.MIM_MAXHEIGHT == 0:
        cyMax = None
    if fMask & win32con.MIM_BACKGROUND == 0:
        hbrBack = None
    if fMask & win32con.MIM_HELPID == 0:
        dwContextHelpID = None
    if fMask & win32con.MIM_MENUDATA == 0:
        dwMenuData = None
    return _MakeResult(
        "MENUINFO dwStyle cyMax hbrBack dwContextHelpID dwMenuData",
        (dwStyle, cyMax, hbrBack, dwContextHelpID, dwMenuData),
    )


def EmptyMENUINFO(mask=None):
    if mask is None:
        mask = (
            win32con.MIM_STYLE
            | win32con.MIM_MAXHEIGHT
            | win32con.MIM_BACKGROUND
            | win32con.MIM_HELPID
            | win32con.MIM_MENUDATA
        )

    buf = struct.pack(
        _menuinfo_fmt,
        struct.calcsize(_menuinfo_fmt),  # cbSize
        mask,
        0,  # dwStyle
        0,  # cyMax
        0,  # hbrBack,
        0,  # dwContextHelpID,
        0,  # dwMenuData,
    )
    return array.array("b", buf)


##########################################################################
#
# Tree View structure support - TVITEM, TVINSERTSTRUCT and TVDISPINFO
#
##########################################################################

# XXX - Note that the following implementation of TreeView structures is ripped
# XXX - from the SpamBayes project.  It may not quite work correctly yet - I
# XXX - intend checking them later - but having them is better than not at all!

_tvitem_fmt = "iPiiPiiiiP"


# Helpers for the ugly win32 structure packing/unpacking
# XXX - Note that functions using _GetMaskAndVal run 3x faster if they are
# 'inlined' into the function - see PackLVITEM.  If the profiler points at
# _GetMaskAndVal(), you should nuke it (patches welcome once they have been
# tested)
def _GetMaskAndVal(val, default, mask, flag):
    if val is None:
        return mask, default
    else:
        if flag is not None:
            mask |= flag
        return mask, val


def PackTVINSERTSTRUCT(parent, insertAfter, tvitem):
    tvitem_buf, extra = PackTVITEM(*tvitem)
    tvitem_buf = tvitem_buf.tobytes()
    format = "PP%ds" % len(tvitem_buf)
    return struct.pack(format, parent, insertAfter, tvitem_buf), extra


def PackTVITEM(hitem, state, stateMask, text, image, selimage, citems, param):
    extra = []  # objects we must keep references to
    mask = 0
    mask, hitem = _GetMaskAndVal(hitem, 0, mask, commctrl.TVIF_HANDLE)
    mask, state = _GetMaskAndVal(state, 0, mask, commctrl.TVIF_STATE)
    if not mask & commctrl.TVIF_STATE:
        stateMask = 0
    mask, text = _GetMaskAndVal(text, None, mask, commctrl.TVIF_TEXT)
    mask, image = _GetMaskAndVal(image, 0, mask, commctrl.TVIF_IMAGE)
    mask, selimage = _GetMaskAndVal(selimage, 0, mask, commctrl.TVIF_SELECTEDIMAGE)
    mask, citems = _GetMaskAndVal(citems, 0, mask, commctrl.TVIF_CHILDREN)
    mask, param = _GetMaskAndVal(param, 0, mask, commctrl.TVIF_PARAM)
    if text is None:
        text_addr = text_len = 0
    else:
        text_buffer = _make_text_buffer(text)
        text_len = len(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    buf = struct.pack(
        _tvitem_fmt,
        mask,
        hitem,
        state,
        stateMask,
        text_addr,
        text_len,  # text
        image,
        selimage,
        citems,
        param,
    )
    return array.array("b", buf), extra


# Make a new buffer suitable for querying hitem's attributes.
def EmptyTVITEM(hitem, mask=None, text_buf_size=512):
    extra = []  # objects we must keep references to
    if mask is None:
        mask = (
            commctrl.TVIF_HANDLE
            | commctrl.TVIF_STATE
            | commctrl.TVIF_TEXT
            | commctrl.TVIF_IMAGE
            | commctrl.TVIF_SELECTEDIMAGE
            | commctrl.TVIF_CHILDREN
            | commctrl.TVIF_PARAM
        )
    if mask & commctrl.TVIF_TEXT:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0
    buf = struct.pack(
        _tvitem_fmt, mask, hitem, 0, 0, text_addr, text_buf_size, 0, 0, 0, 0
    )
    return array.array("b", buf), extra


def UnpackTVITEM(buffer):
    (
        item_mask,
        item_hItem,
        item_state,
        item_stateMask,
        item_textptr,
        item_cchText,
        item_image,
        item_selimage,
        item_cChildren,
        item_param,
    ) = struct.unpack(_tvitem_fmt, buffer)
    # ensure only items listed by the mask are valid (except we assume the
    # handle is always valid - some notifications (eg, TVN_ENDLABELEDIT) set a
    # mask that doesn't include the handle, but the docs explicity say it is.)
    if not (item_mask & commctrl.TVIF_TEXT):
        item_textptr = item_cchText = None
    if not (item_mask & commctrl.TVIF_CHILDREN):
        item_cChildren = None
    if not (item_mask & commctrl.TVIF_IMAGE):
        item_image = None
    if not (item_mask & commctrl.TVIF_PARAM):
        item_param = None
    if not (item_mask & commctrl.TVIF_SELECTEDIMAGE):
        item_selimage = None
    if not (item_mask & commctrl.TVIF_STATE):
        item_state = item_stateMask = None

    if item_textptr:
        text = win32gui.PyGetString(item_textptr)
    else:
        text = None
    return _MakeResult(
        "TVITEM item_hItem item_state item_stateMask "
        "text item_image item_selimage item_cChildren item_param",
        (
            item_hItem,
            item_state,
            item_stateMask,
            text,
            item_image,
            item_selimage,
            item_cChildren,
            item_param,
        ),
    )


# Unpack the lparm from a "TVNOTIFY" message
def UnpackTVNOTIFY(lparam):
    item_size = struct.calcsize(_tvitem_fmt)
    format = _nmhdr_fmt + _nmhdr_align_padding
    if is64bit:
        format += "ixxxx"
    else:
        format += "i"
    format += "%ds%ds" % (item_size, item_size)
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    hwndFrom, id, code, action, buf_old, buf_new = struct.unpack(format, buf)
    item_old = UnpackTVITEM(buf_old)
    item_new = UnpackTVITEM(buf_new)
    return _MakeResult(
        "TVNOTIFY hwndFrom id code action item_old item_new",
        (hwndFrom, id, code, action, item_old, item_new),
    )


def UnpackTVDISPINFO(lparam):
    item_size = struct.calcsize(_tvitem_fmt)
    format = "PPi%ds" % (item_size,)
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    hwndFrom, id, code, buf_item = struct.unpack(format, buf)
    item = UnpackTVITEM(buf_item)
    return _MakeResult("TVDISPINFO hwndFrom id code item", (hwndFrom, id, code, item))


#
# List view items
_lvitem_fmt = "iiiiiPiiPi"


def PackLVITEM(
    item=None,
    subItem=None,
    state=None,
    stateMask=None,
    text=None,
    image=None,
    param=None,
    indent=None,
):
    extra = []  # objects we must keep references to
    mask = 0
    # _GetMaskAndVal adds quite a bit of overhead to this function.
    if item is None:
        item = 0  # No mask for item
    if subItem is None:
        subItem = 0  # No mask for sibItem
    if state is None:
        state = 0
        stateMask = 0
    else:
        mask |= commctrl.LVIF_STATE
        if stateMask is None:
            stateMask = state

    if image is None:
        image = 0
    else:
        mask |= commctrl.LVIF_IMAGE
    if param is None:
        param = 0
    else:
        mask |= commctrl.LVIF_PARAM
    if indent is None:
        indent = 0
    else:
        mask |= commctrl.LVIF_INDENT

    if text is None:
        text_addr = text_len = 0
    else:
        mask |= commctrl.LVIF_TEXT
        text_buffer = _make_text_buffer(text)
        text_len = len(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    buf = struct.pack(
        _lvitem_fmt,
        mask,
        item,
        subItem,
        state,
        stateMask,
        text_addr,
        text_len,  # text
        image,
        param,
        indent,
    )
    return array.array("b", buf), extra


def UnpackLVITEM(buffer):
    (
        item_mask,
        item_item,
        item_subItem,
        item_state,
        item_stateMask,
        item_textptr,
        item_cchText,
        item_image,
        item_param,
        item_indent,
    ) = struct.unpack(_lvitem_fmt, buffer)
    # ensure only items listed by the mask are valid
    if not (item_mask & commctrl.LVIF_TEXT):
        item_textptr = item_cchText = None
    if not (item_mask & commctrl.LVIF_IMAGE):
        item_image = None
    if not (item_mask & commctrl.LVIF_PARAM):
        item_param = None
    if not (item_mask & commctrl.LVIF_INDENT):
        item_indent = None
    if not (item_mask & commctrl.LVIF_STATE):
        item_state = item_stateMask = None

    if item_textptr:
        text = win32gui.PyGetString(item_textptr)
    else:
        text = None
    return _MakeResult(
        "LVITEM item_item item_subItem item_state "
        "item_stateMask text item_image item_param item_indent",
        (
            item_item,
            item_subItem,
            item_state,
            item_stateMask,
            text,
            item_image,
            item_param,
            item_indent,
        ),
    )


# Unpack an "LVNOTIFY" message
def UnpackLVDISPINFO(lparam):
    item_size = struct.calcsize(_lvitem_fmt)
    format = _nmhdr_fmt + _nmhdr_align_padding + ("%ds" % (item_size,))
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    hwndFrom, id, code, buf_item = struct.unpack(format, buf)
    item = UnpackLVITEM(buf_item)
    return _MakeResult("LVDISPINFO hwndFrom id code item", (hwndFrom, id, code, item))


def UnpackLVNOTIFY(lparam):
    format = _nmhdr_fmt + _nmhdr_align_padding + "7i"
    if is64bit:
        format += "xxxx"  # point needs padding.
    format += "P"
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    (
        hwndFrom,
        id,
        code,
        item,
        subitem,
        newstate,
        oldstate,
        changed,
        pt_x,
        pt_y,
        lparam,
    ) = struct.unpack(format, buf)
    return _MakeResult(
        "UnpackLVNOTIFY hwndFrom id code item subitem "
        "newstate oldstate changed pt lparam",
        (
            hwndFrom,
            id,
            code,
            item,
            subitem,
            newstate,
            oldstate,
            changed,
            (pt_x, pt_y),
            lparam,
        ),
    )


# Make a new buffer suitable for querying an items attributes.
def EmptyLVITEM(item, subitem, mask=None, text_buf_size=512):
    extra = []  # objects we must keep references to
    if mask is None:
        mask = (
            commctrl.LVIF_IMAGE
            | commctrl.LVIF_INDENT
            | commctrl.LVIF_TEXT
            | commctrl.LVIF_PARAM
            | commctrl.LVIF_STATE
        )
    if mask & commctrl.LVIF_TEXT:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0
    buf = struct.pack(
        _lvitem_fmt,
        mask,
        item,
        subitem,
        0,
        0,
        text_addr,
        text_buf_size,  # text
        0,
        0,
        0,
    )
    return array.array("b", buf), extra


# List view column structure
_lvcolumn_fmt = "iiiPiiii"


def PackLVCOLUMN(fmt=None, cx=None, text=None, subItem=None, image=None, order=None):
    extra = []  # objects we must keep references to
    mask = 0
    mask, fmt = _GetMaskAndVal(fmt, 0, mask, commctrl.LVCF_FMT)
    mask, cx = _GetMaskAndVal(cx, 0, mask, commctrl.LVCF_WIDTH)
    mask, text = _GetMaskAndVal(text, None, mask, commctrl.LVCF_TEXT)
    mask, subItem = _GetMaskAndVal(subItem, 0, mask, commctrl.LVCF_SUBITEM)
    mask, image = _GetMaskAndVal(image, 0, mask, commctrl.LVCF_IMAGE)
    mask, order = _GetMaskAndVal(order, 0, mask, commctrl.LVCF_ORDER)
    if text is None:
        text_addr = text_len = 0
    else:
        text_buffer = _make_text_buffer(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
        text_len = len(text)
    buf = struct.pack(
        _lvcolumn_fmt, mask, fmt, cx, text_addr, text_len, subItem, image, order
    )
    return array.array("b", buf), extra


def UnpackLVCOLUMN(lparam):
    mask, fmt, cx, text_addr, text_size, subItem, image, order = struct.unpack(
        _lvcolumn_fmt, lparam
    )
    # ensure only items listed by the mask are valid
    if not (mask & commctrl.LVCF_FMT):
        fmt = None
    if not (mask & commctrl.LVCF_WIDTH):
        cx = None
    if not (mask & commctrl.LVCF_TEXT):
        text_addr = text_size = None
    if not (mask & commctrl.LVCF_SUBITEM):
        subItem = None
    if not (mask & commctrl.LVCF_IMAGE):
        image = None
    if not (mask & commctrl.LVCF_ORDER):
        order = None
    if text_addr:
        text = win32gui.PyGetString(text_addr)
    else:
        text = None
    return _MakeResult(
        "LVCOLUMN fmt cx text subItem image order",
        (fmt, cx, text, subItem, image, order),
    )


# Make a new buffer suitable for querying an items attributes.
def EmptyLVCOLUMN(mask=None, text_buf_size=512):
    extra = []  # objects we must keep references to
    if mask is None:
        mask = (
            commctrl.LVCF_FMT
            | commctrl.LVCF_WIDTH
            | commctrl.LVCF_TEXT
            | commctrl.LVCF_SUBITEM
            | commctrl.LVCF_IMAGE
            | commctrl.LVCF_ORDER
        )
    if mask & commctrl.LVCF_TEXT:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0
    buf = struct.pack(_lvcolumn_fmt, mask, 0, 0, text_addr, text_buf_size, 0, 0, 0)
    return array.array("b", buf), extra


# List view hit-test.
def PackLVHITTEST(pt):
    format = "iiiii"
    buf = struct.pack(format, pt[0], pt[1], 0, 0, 0)
    return array.array("b", buf), None


def UnpackLVHITTEST(buf):
    format = "iiiii"
    x, y, flags, item, subitem = struct.unpack(format, buf)
    return _MakeResult(
        "LVHITTEST pt flags item subitem", ((x, y), flags, item, subitem)
    )


def PackHDITEM(
    cxy=None, text=None, hbm=None, fmt=None, param=None, image=None, order=None
):
    extra = []  # objects we must keep references to
    mask = 0
    mask, cxy = _GetMaskAndVal(cxy, 0, mask, commctrl.HDI_HEIGHT)
    mask, text = _GetMaskAndVal(text, None, mask, commctrl.LVCF_TEXT)
    mask, hbm = _GetMaskAndVal(hbm, 0, mask, commctrl.HDI_BITMAP)
    mask, fmt = _GetMaskAndVal(fmt, 0, mask, commctrl.HDI_FORMAT)
    mask, param = _GetMaskAndVal(param, 0, mask, commctrl.HDI_LPARAM)
    mask, image = _GetMaskAndVal(image, 0, mask, commctrl.HDI_IMAGE)
    mask, order = _GetMaskAndVal(order, 0, mask, commctrl.HDI_ORDER)

    if text is None:
        text_addr = text_len = 0
    else:
        text_buffer = _make_text_buffer(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
        text_len = len(text)

    format = "iiPPiiPiiii"
    buf = struct.pack(
        format, mask, cxy, text_addr, hbm, text_len, fmt, param, image, order, 0, 0
    )
    return array.array("b", buf), extra


# Device notification stuff


# Generic function for packing a DEV_BROADCAST_* structure - generally used
# by the other PackDEV_BROADCAST_* functions in this module.
def PackDEV_BROADCAST(devicetype, rest_fmt, rest_data, extra_data=b""):
    # It seems a requirement is 4 byte alignment, even for the 'BYTE data[1]'
    # field (eg, that would make DEV_BROADCAST_HANDLE 41 bytes, but we must
    # be 44.
    extra_data += b"\0" * (4 - len(extra_data) % 4)
    format = "iii" + rest_fmt
    full_size = struct.calcsize(format) + len(extra_data)
    data = (full_size, devicetype, 0) + rest_data
    return struct.pack(format, *data) + extra_data


def PackDEV_BROADCAST_HANDLE(
    handle,
    hdevnotify=0,
    guid=b"\0" * 16,
    name_offset=0,
    data=b"\0",
):
    return PackDEV_BROADCAST(
        win32con.DBT_DEVTYP_HANDLE,
        "PP16sl",
        (int(handle), int(hdevnotify), bytes(memoryview(guid)), name_offset),
        data,
    )


def PackDEV_BROADCAST_VOLUME(unitmask, flags):
    return PackDEV_BROADCAST(win32con.DBT_DEVTYP_VOLUME, "II", (unitmask, flags))


def PackDEV_BROADCAST_DEVICEINTERFACE(classguid, name=""):
    if not isinstance(name, str):
        raise TypeError("Must provide unicode for the name")
    name = name.encode("utf-16le")

    # 16 bytes for the IID followed by \0 term'd string.
    rest_fmt = "16s%ds" % len(name)
    # bytes(memoryview(iid)) hoops necessary to get the raw IID bytes.
    rest_data = (bytes(memoryview(pywintypes.IID(classguid))), name)
    return PackDEV_BROADCAST(win32con.DBT_DEVTYP_DEVICEINTERFACE, rest_fmt, rest_data)


# An object returned by UnpackDEV_BROADCAST.
class DEV_BROADCAST_INFO:
    def __init__(self, devicetype, **kw):
        self.devicetype = devicetype
        self.__dict__.update(kw)

    def __str__(self):
        return "DEV_BROADCAST_INFO:" + str(self.__dict__)


# Support for unpacking the 'lparam'
def UnpackDEV_BROADCAST(lparam):
    if lparam == 0:
        return None
    hdr_format = "iii"
    hdr_size = struct.calcsize(hdr_format)
    hdr_buf = win32gui.PyGetMemory(lparam, hdr_size)
    size, devtype, reserved = struct.unpack("iii", hdr_buf)
    # Due to x64 alignment issues, we need to use the full format string over
    # the entire buffer.  ie, on x64:
    # calcsize('iiiP') != calcsize('iii')+calcsize('P')
    buf = win32gui.PyGetMemory(lparam, size)

    extra = x = {}
    if devtype == win32con.DBT_DEVTYP_HANDLE:
        # 2 handles, a GUID, a LONG and possibly an array following...
        fmt = hdr_format + "PP16sl"
        (
            _,
            _,
            _,
            x["handle"],
            x["hdevnotify"],
            guid_bytes,
            x["nameoffset"],
        ) = struct.unpack(fmt, buf[: struct.calcsize(fmt)])
        x["eventguid"] = pywintypes.IID(guid_bytes, True)
    elif devtype == win32con.DBT_DEVTYP_DEVICEINTERFACE:
        fmt = hdr_format + "16s"
        _, _, _, guid_bytes = struct.unpack(fmt, buf[: struct.calcsize(fmt)])
        x["classguid"] = pywintypes.IID(guid_bytes, True)
        x["name"] = win32gui.PyGetString(lparam + struct.calcsize(fmt))
    elif devtype == win32con.DBT_DEVTYP_VOLUME:
        # int mask and flags
        fmt = hdr_format + "II"
        _, _, _, x["unitmask"], x["flags"] = struct.unpack(
            fmt, buf[: struct.calcsize(fmt)]
        )
    elif devtype == win32con.DBT_DEVTYP_PORT:
        x["name"] = win32gui.PyGetString(lparam + struct.calcsize(hdr_format))
    else:
        raise NotImplementedError("unknown device type %d" % (devtype,))
    return DEV_BROADCAST_INFO(devtype, **extra)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\win32gui_struct.py ===
# This is a work in progress - see Demos/win32gui_menu.py

# win32gui_struct.py - helpers for working with various win32gui structures.
# As win32gui is "light-weight", it does not define objects for all possible
# win32 structures - in general, "buffer" objects are passed around - it is
# the callers responsibility to pack the buffer in the correct format.
#
# This module defines some helpers for the commonly used structures.
#
# In general, each structure has 3 functions:
#
# buffer, extras = PackSTRUCTURE(items, ...)
# item, ... = UnpackSTRUCTURE(buffer)
# buffer, extras = EmtpySTRUCTURE(...)
#
# 'extras' is always items that must be held along with the buffer, as the
# buffer refers to these object's memory.
# For structures that support a 'mask', this mask is hidden from the user - if
# 'None' is passed, the mask flag will not be set, or on return, None will
# be returned for the value if the mask is not set.
#
# NOTE: I considered making these structures look like real classes, and
# support 'attributes' etc - however, ctypes already has a good structure
# mechanism - I think it makes more sense to support ctype structures
# at the win32gui level, then there will be no need for this module at all.
# XXX - the above makes sense in terms of what is built and passed to
# win32gui (ie, the Pack* functions) - but doesn't make as much sense for
# the Unpack* functions, where the aim is user convenience.

import array
import struct
import sys
from collections import namedtuple

import commctrl
import pywintypes
import win32con
import win32gui


def _MakeResult(names_str, values):
    names = names_str.split()
    # TODO: Dynamic namedtuple. This could be made static, also exposing the types
    nt = namedtuple(names[0], names[1:])  # noqa: PYI024
    return nt(*values)


is64bit = "64 bit" in sys.version
_nmhdr_fmt = "PPi"
if is64bit:
    # When the item past the NMHDR gets aligned (eg, when it is a struct)
    # we need this many bytes padding.
    _nmhdr_align_padding = "xxxx"
else:
    _nmhdr_align_padding = ""


# Encode a string suitable for passing in a win32gui related structure
def _make_text_buffer(text):
    if not isinstance(text, str):
        raise TypeError("MENUITEMINFO text must be unicode")
    data = (text + "\0").encode("utf-16le")
    return array.array("b", data)


# make an 'empty' buffer, ready for filling with cch characters.
def _make_empty_text_buffer(cch):
    return _make_text_buffer("\0" * cch)


# Generic WM_NOTIFY unpacking
def UnpackWMNOTIFY(lparam):
    format = "PPi"
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    return _MakeResult("WMNOTIFY hwndFrom idFrom code", struct.unpack(format, buf))


def UnpackNMITEMACTIVATE(lparam):
    format = _nmhdr_fmt + _nmhdr_align_padding
    if is64bit:
        # the struct module doesn't handle this correctly as some of the items
        # are actually structs in structs, which get individually aligned.
        format += "iiiiiiixxxxP"
    else:
        format += "iiiiiiiP"
    buf = win32gui.PyMakeBuffer(struct.calcsize(format), lparam)
    return _MakeResult(
        "NMITEMACTIVATE hwndFrom idFrom code iItem iSubItem uNewState uOldState uChanged actionx actiony lParam",
        struct.unpack(format, buf),
    )


# MENUITEMINFO struct
# https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-menuiteminfow
# We use the struct module to pack and unpack strings as MENUITEMINFO
# structures.  We also have special handling for the 'fMask' item in that
# structure to avoid the caller needing to explicitly check validity
# (None is used if the mask excludes/should exclude the value)
_menuiteminfo_fmt = "5i5PiP"


def PackMENUITEMINFO(
    fType=None,
    fState=None,
    wID=None,
    hSubMenu=None,
    hbmpChecked=None,
    hbmpUnchecked=None,
    dwItemData=None,
    text=None,
    hbmpItem=None,
    dwTypeData=None,
):
    # 'extras' are objects the caller must keep a reference to (as their
    # memory is used) for the lifetime of the INFO item.
    extras = []
    # ack - dwItemData and dwTypeData were confused for a while...
    assert (
        dwItemData is None or dwTypeData is None
    ), "sorry - these were confused - you probably want dwItemData"
    # if we are a long way past 209, then we can nuke the above...
    if dwTypeData is not None:
        import warnings

        warnings.warn("PackMENUITEMINFO: please use dwItemData instead of dwTypeData")
    if dwItemData is None:
        dwItemData = dwTypeData or 0

    fMask = 0
    if fType is None:
        fType = 0
    else:
        fMask |= win32con.MIIM_FTYPE
    if fState is None:
        fState = 0
    else:
        fMask |= win32con.MIIM_STATE
    if wID is None:
        wID = 0
    else:
        fMask |= win32con.MIIM_ID
    if hSubMenu is None:
        hSubMenu = 0
    else:
        fMask |= win32con.MIIM_SUBMENU
    if hbmpChecked is None:
        assert hbmpUnchecked is None, "neither or both checkmark bmps must be given"
        hbmpChecked = hbmpUnchecked = 0
    else:
        assert hbmpUnchecked is not None, "neither or both checkmark bmps must be given"
        fMask |= win32con.MIIM_CHECKMARKS
    if dwItemData is None:
        dwItemData = 0
    else:
        fMask |= win32con.MIIM_DATA
    if hbmpItem is None:
        hbmpItem = 0
    else:
        fMask |= win32con.MIIM_BITMAP
    if text is not None:
        fMask |= win32con.MIIM_STRING
        str_buf = _make_text_buffer(text)
        cch = len(text)
        # We are taking address of strbuf - it must not die until windows
        # has finished with our structure.
        lptext = str_buf.buffer_info()[0]
        extras.append(str_buf)
    else:
        lptext = 0
        cch = 0
    # Create the struct.
    # 'P' format does not accept PyHANDLE's !
    item = struct.pack(
        _menuiteminfo_fmt,
        struct.calcsize(_menuiteminfo_fmt),  # cbSize
        fMask,
        fType,
        fState,
        wID,
        int(hSubMenu),
        int(hbmpChecked),
        int(hbmpUnchecked),
        dwItemData,
        lptext,
        cch,
        int(hbmpItem),
    )
    # Now copy the string to a writable buffer, so that the result
    # could be passed to a 'Get' function
    return array.array("b", item), extras


def UnpackMENUITEMINFO(s):
    (
        cb,
        fMask,
        fType,
        fState,
        wID,
        hSubMenu,
        hbmpChecked,
        hbmpUnchecked,
        dwItemData,
        lptext,
        cch,
        hbmpItem,
    ) = struct.unpack(_menuiteminfo_fmt, s)
    assert cb == len(s)
    if fMask & win32con.MIIM_FTYPE == 0:
        fType = None
    if fMask & win32con.MIIM_STATE == 0:
        fState = None
    if fMask & win32con.MIIM_ID == 0:
        wID = None
    if fMask & win32con.MIIM_SUBMENU == 0:
        hSubMenu = None
    if fMask & win32con.MIIM_CHECKMARKS == 0:
        hbmpChecked = hbmpUnchecked = None
    if fMask & win32con.MIIM_DATA == 0:
        dwItemData = None
    if fMask & win32con.MIIM_BITMAP == 0:
        hbmpItem = None
    if fMask & win32con.MIIM_STRING:
        text = win32gui.PyGetString(lptext, cch)
    else:
        text = None
    return _MakeResult(
        "MENUITEMINFO fType fState wID hSubMenu hbmpChecked "
        "hbmpUnchecked dwItemData text hbmpItem",
        (
            fType,
            fState,
            wID,
            hSubMenu,
            hbmpChecked,
            hbmpUnchecked,
            dwItemData,
            text,
            hbmpItem,
        ),
    )


def EmptyMENUITEMINFO(mask=None, text_buf_size=512):
    # text_buf_size is number of *characters* - not necessarily no of bytes.
    extra = []
    if mask is None:
        mask = (
            win32con.MIIM_BITMAP
            | win32con.MIIM_CHECKMARKS
            | win32con.MIIM_DATA
            | win32con.MIIM_FTYPE
            | win32con.MIIM_ID
            | win32con.MIIM_STATE
            | win32con.MIIM_STRING
            | win32con.MIIM_SUBMENU
        )
        # Note: No MIIM_TYPE - this screws win2k/98.

    if mask & win32con.MIIM_STRING:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0

    # Now copy the string to a writable buffer, so that the result
    # could be passed to a 'Get' function
    buf = struct.pack(
        _menuiteminfo_fmt,
        struct.calcsize(_menuiteminfo_fmt),  # cbSize
        mask,
        0,  # fType,
        0,  # fState,
        0,  # wID,
        0,  # hSubMenu,
        0,  # hbmpChecked,
        0,  # hbmpUnchecked,
        0,  # dwItemData,
        text_addr,
        text_buf_size,
        0,  # hbmpItem
    )
    return array.array("b", buf), extra


# MENUINFO struct
_menuinfo_fmt = "iiiiPiP"


def PackMENUINFO(
    dwStyle=None,
    cyMax=None,
    hbrBack=None,
    dwContextHelpID=None,
    dwMenuData=None,
    fMask=0,
):
    if dwStyle is None:
        dwStyle = 0
    else:
        fMask |= win32con.MIM_STYLE
    if cyMax is None:
        cyMax = 0
    else:
        fMask |= win32con.MIM_MAXHEIGHT
    if hbrBack is None:
        hbrBack = 0
    else:
        fMask |= win32con.MIM_BACKGROUND
    if dwContextHelpID is None:
        dwContextHelpID = 0
    else:
        fMask |= win32con.MIM_HELPID
    if dwMenuData is None:
        dwMenuData = 0
    else:
        fMask |= win32con.MIM_MENUDATA
    # Create the struct.
    item = struct.pack(
        _menuinfo_fmt,
        struct.calcsize(_menuinfo_fmt),  # cbSize
        fMask,
        dwStyle,
        cyMax,
        hbrBack,
        dwContextHelpID,
        dwMenuData,
    )
    return array.array("b", item)


def UnpackMENUINFO(s):
    (cb, fMask, dwStyle, cyMax, hbrBack, dwContextHelpID, dwMenuData) = struct.unpack(
        _menuinfo_fmt, s
    )
    assert cb == len(s)
    if fMask & win32con.MIM_STYLE == 0:
        dwStyle = None
    if fMask & win32con.MIM_MAXHEIGHT == 0:
        cyMax = None
    if fMask & win32con.MIM_BACKGROUND == 0:
        hbrBack = None
    if fMask & win32con.MIM_HELPID == 0:
        dwContextHelpID = None
    if fMask & win32con.MIM_MENUDATA == 0:
        dwMenuData = None
    return _MakeResult(
        "MENUINFO dwStyle cyMax hbrBack dwContextHelpID dwMenuData",
        (dwStyle, cyMax, hbrBack, dwContextHelpID, dwMenuData),
    )


def EmptyMENUINFO(mask=None):
    if mask is None:
        mask = (
            win32con.MIM_STYLE
            | win32con.MIM_MAXHEIGHT
            | win32con.MIM_BACKGROUND
            | win32con.MIM_HELPID
            | win32con.MIM_MENUDATA
        )

    buf = struct.pack(
        _menuinfo_fmt,
        struct.calcsize(_menuinfo_fmt),  # cbSize
        mask,
        0,  # dwStyle
        0,  # cyMax
        0,  # hbrBack,
        0,  # dwContextHelpID,
        0,  # dwMenuData,
    )
    return array.array("b", buf)


##########################################################################
#
# Tree View structure support - TVITEM, TVINSERTSTRUCT and TVDISPINFO
#
##########################################################################

# XXX - Note that the following implementation of TreeView structures is ripped
# XXX - from the SpamBayes project.  It may not quite work correctly yet - I
# XXX - intend checking them later - but having them is better than not at all!

_tvitem_fmt = "iPiiPiiiiP"


# Helpers for the ugly win32 structure packing/unpacking
# XXX - Note that functions using _GetMaskAndVal run 3x faster if they are
# 'inlined' into the function - see PackLVITEM.  If the profiler points at
# _GetMaskAndVal(), you should nuke it (patches welcome once they have been
# tested)
def _GetMaskAndVal(val, default, mask, flag):
    if val is None:
        return mask, default
    else:
        if flag is not None:
            mask |= flag
        return mask, val


def PackTVINSERTSTRUCT(parent, insertAfter, tvitem):
    tvitem_buf, extra = PackTVITEM(*tvitem)
    tvitem_buf = tvitem_buf.tobytes()
    format = "PP%ds" % len(tvitem_buf)
    return struct.pack(format, parent, insertAfter, tvitem_buf), extra


def PackTVITEM(hitem, state, stateMask, text, image, selimage, citems, param):
    extra = []  # objects we must keep references to
    mask = 0
    mask, hitem = _GetMaskAndVal(hitem, 0, mask, commctrl.TVIF_HANDLE)
    mask, state = _GetMaskAndVal(state, 0, mask, commctrl.TVIF_STATE)
    if not mask & commctrl.TVIF_STATE:
        stateMask = 0
    mask, text = _GetMaskAndVal(text, None, mask, commctrl.TVIF_TEXT)
    mask, image = _GetMaskAndVal(image, 0, mask, commctrl.TVIF_IMAGE)
    mask, selimage = _GetMaskAndVal(selimage, 0, mask, commctrl.TVIF_SELECTEDIMAGE)
    mask, citems = _GetMaskAndVal(citems, 0, mask, commctrl.TVIF_CHILDREN)
    mask, param = _GetMaskAndVal(param, 0, mask, commctrl.TVIF_PARAM)
    if text is None:
        text_addr = text_len = 0
    else:
        text_buffer = _make_text_buffer(text)
        text_len = len(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    buf = struct.pack(
        _tvitem_fmt,
        mask,
        hitem,
        state,
        stateMask,
        text_addr,
        text_len,  # text
        image,
        selimage,
        citems,
        param,
    )
    return array.array("b", buf), extra


# Make a new buffer suitable for querying hitem's attributes.
def EmptyTVITEM(hitem, mask=None, text_buf_size=512):
    extra = []  # objects we must keep references to
    if mask is None:
        mask = (
            commctrl.TVIF_HANDLE
            | commctrl.TVIF_STATE
            | commctrl.TVIF_TEXT
            | commctrl.TVIF_IMAGE
            | commctrl.TVIF_SELECTEDIMAGE
            | commctrl.TVIF_CHILDREN
            | commctrl.TVIF_PARAM
        )
    if mask & commctrl.TVIF_TEXT:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0
    buf = struct.pack(
        _tvitem_fmt, mask, hitem, 0, 0, text_addr, text_buf_size, 0, 0, 0, 0
    )
    return array.array("b", buf), extra


def UnpackTVITEM(buffer):
    (
        item_mask,
        item_hItem,
        item_state,
        item_stateMask,
        item_textptr,
        item_cchText,
        item_image,
        item_selimage,
        item_cChildren,
        item_param,
    ) = struct.unpack(_tvitem_fmt, buffer)
    # ensure only items listed by the mask are valid (except we assume the
    # handle is always valid - some notifications (eg, TVN_ENDLABELEDIT) set a
    # mask that doesn't include the handle, but the docs explicity say it is.)
    if not (item_mask & commctrl.TVIF_TEXT):
        item_textptr = item_cchText = None
    if not (item_mask & commctrl.TVIF_CHILDREN):
        item_cChildren = None
    if not (item_mask & commctrl.TVIF_IMAGE):
        item_image = None
    if not (item_mask & commctrl.TVIF_PARAM):
        item_param = None
    if not (item_mask & commctrl.TVIF_SELECTEDIMAGE):
        item_selimage = None
    if not (item_mask & commctrl.TVIF_STATE):
        item_state = item_stateMask = None

    if item_textptr:
        text = win32gui.PyGetString(item_textptr)
    else:
        text = None
    return _MakeResult(
        "TVITEM item_hItem item_state item_stateMask "
        "text item_image item_selimage item_cChildren item_param",
        (
            item_hItem,
            item_state,
            item_stateMask,
            text,
            item_image,
            item_selimage,
            item_cChildren,
            item_param,
        ),
    )


# Unpack the lparm from a "TVNOTIFY" message
def UnpackTVNOTIFY(lparam):
    item_size = struct.calcsize(_tvitem_fmt)
    format = _nmhdr_fmt + _nmhdr_align_padding
    if is64bit:
        format += "ixxxx"
    else:
        format += "i"
    format += "%ds%ds" % (item_size, item_size)
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    hwndFrom, id, code, action, buf_old, buf_new = struct.unpack(format, buf)
    item_old = UnpackTVITEM(buf_old)
    item_new = UnpackTVITEM(buf_new)
    return _MakeResult(
        "TVNOTIFY hwndFrom id code action item_old item_new",
        (hwndFrom, id, code, action, item_old, item_new),
    )


def UnpackTVDISPINFO(lparam):
    item_size = struct.calcsize(_tvitem_fmt)
    format = "PPi%ds" % (item_size,)
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    hwndFrom, id, code, buf_item = struct.unpack(format, buf)
    item = UnpackTVITEM(buf_item)
    return _MakeResult("TVDISPINFO hwndFrom id code item", (hwndFrom, id, code, item))


#
# List view items
_lvitem_fmt = "iiiiiPiiPi"


def PackLVITEM(
    item=None,
    subItem=None,
    state=None,
    stateMask=None,
    text=None,
    image=None,
    param=None,
    indent=None,
):
    extra = []  # objects we must keep references to
    mask = 0
    # _GetMaskAndVal adds quite a bit of overhead to this function.
    if item is None:
        item = 0  # No mask for item
    if subItem is None:
        subItem = 0  # No mask for sibItem
    if state is None:
        state = 0
        stateMask = 0
    else:
        mask |= commctrl.LVIF_STATE
        if stateMask is None:
            stateMask = state

    if image is None:
        image = 0
    else:
        mask |= commctrl.LVIF_IMAGE
    if param is None:
        param = 0
    else:
        mask |= commctrl.LVIF_PARAM
    if indent is None:
        indent = 0
    else:
        mask |= commctrl.LVIF_INDENT

    if text is None:
        text_addr = text_len = 0
    else:
        mask |= commctrl.LVIF_TEXT
        text_buffer = _make_text_buffer(text)
        text_len = len(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    buf = struct.pack(
        _lvitem_fmt,
        mask,
        item,
        subItem,
        state,
        stateMask,
        text_addr,
        text_len,  # text
        image,
        param,
        indent,
    )
    return array.array("b", buf), extra


def UnpackLVITEM(buffer):
    (
        item_mask,
        item_item,
        item_subItem,
        item_state,
        item_stateMask,
        item_textptr,
        item_cchText,
        item_image,
        item_param,
        item_indent,
    ) = struct.unpack(_lvitem_fmt, buffer)
    # ensure only items listed by the mask are valid
    if not (item_mask & commctrl.LVIF_TEXT):
        item_textptr = item_cchText = None
    if not (item_mask & commctrl.LVIF_IMAGE):
        item_image = None
    if not (item_mask & commctrl.LVIF_PARAM):
        item_param = None
    if not (item_mask & commctrl.LVIF_INDENT):
        item_indent = None
    if not (item_mask & commctrl.LVIF_STATE):
        item_state = item_stateMask = None

    if item_textptr:
        text = win32gui.PyGetString(item_textptr)
    else:
        text = None
    return _MakeResult(
        "LVITEM item_item item_subItem item_state "
        "item_stateMask text item_image item_param item_indent",
        (
            item_item,
            item_subItem,
            item_state,
            item_stateMask,
            text,
            item_image,
            item_param,
            item_indent,
        ),
    )


# Unpack an "LVNOTIFY" message
def UnpackLVDISPINFO(lparam):
    item_size = struct.calcsize(_lvitem_fmt)
    format = _nmhdr_fmt + _nmhdr_align_padding + ("%ds" % (item_size,))
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    hwndFrom, id, code, buf_item = struct.unpack(format, buf)
    item = UnpackLVITEM(buf_item)
    return _MakeResult("LVDISPINFO hwndFrom id code item", (hwndFrom, id, code, item))


def UnpackLVNOTIFY(lparam):
    format = _nmhdr_fmt + _nmhdr_align_padding + "7i"
    if is64bit:
        format += "xxxx"  # point needs padding.
    format += "P"
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    (
        hwndFrom,
        id,
        code,
        item,
        subitem,
        newstate,
        oldstate,
        changed,
        pt_x,
        pt_y,
        lparam,
    ) = struct.unpack(format, buf)
    return _MakeResult(
        "UnpackLVNOTIFY hwndFrom id code item subitem "
        "newstate oldstate changed pt lparam",
        (
            hwndFrom,
            id,
            code,
            item,
            subitem,
            newstate,
            oldstate,
            changed,
            (pt_x, pt_y),
            lparam,
        ),
    )


# Make a new buffer suitable for querying an items attributes.
def EmptyLVITEM(item, subitem, mask=None, text_buf_size=512):
    extra = []  # objects we must keep references to
    if mask is None:
        mask = (
            commctrl.LVIF_IMAGE
            | commctrl.LVIF_INDENT
            | commctrl.LVIF_TEXT
            | commctrl.LVIF_PARAM
            | commctrl.LVIF_STATE
        )
    if mask & commctrl.LVIF_TEXT:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0
    buf = struct.pack(
        _lvitem_fmt,
        mask,
        item,
        subitem,
        0,
        0,
        text_addr,
        text_buf_size,  # text
        0,
        0,
        0,
    )
    return array.array("b", buf), extra


# List view column structure
_lvcolumn_fmt = "iiiPiiii"


def PackLVCOLUMN(fmt=None, cx=None, text=None, subItem=None, image=None, order=None):
    extra = []  # objects we must keep references to
    mask = 0
    mask, fmt = _GetMaskAndVal(fmt, 0, mask, commctrl.LVCF_FMT)
    mask, cx = _GetMaskAndVal(cx, 0, mask, commctrl.LVCF_WIDTH)
    mask, text = _GetMaskAndVal(text, None, mask, commctrl.LVCF_TEXT)
    mask, subItem = _GetMaskAndVal(subItem, 0, mask, commctrl.LVCF_SUBITEM)
    mask, image = _GetMaskAndVal(image, 0, mask, commctrl.LVCF_IMAGE)
    mask, order = _GetMaskAndVal(order, 0, mask, commctrl.LVCF_ORDER)
    if text is None:
        text_addr = text_len = 0
    else:
        text_buffer = _make_text_buffer(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
        text_len = len(text)
    buf = struct.pack(
        _lvcolumn_fmt, mask, fmt, cx, text_addr, text_len, subItem, image, order
    )
    return array.array("b", buf), extra


def UnpackLVCOLUMN(lparam):
    mask, fmt, cx, text_addr, text_size, subItem, image, order = struct.unpack(
        _lvcolumn_fmt, lparam
    )
    # ensure only items listed by the mask are valid
    if not (mask & commctrl.LVCF_FMT):
        fmt = None
    if not (mask & commctrl.LVCF_WIDTH):
        cx = None
    if not (mask & commctrl.LVCF_TEXT):
        text_addr = text_size = None
    if not (mask & commctrl.LVCF_SUBITEM):
        subItem = None
    if not (mask & commctrl.LVCF_IMAGE):
        image = None
    if not (mask & commctrl.LVCF_ORDER):
        order = None
    if text_addr:
        text = win32gui.PyGetString(text_addr)
    else:
        text = None
    return _MakeResult(
        "LVCOLUMN fmt cx text subItem image order",
        (fmt, cx, text, subItem, image, order),
    )


# Make a new buffer suitable for querying an items attributes.
def EmptyLVCOLUMN(mask=None, text_buf_size=512):
    extra = []  # objects we must keep references to
    if mask is None:
        mask = (
            commctrl.LVCF_FMT
            | commctrl.LVCF_WIDTH
            | commctrl.LVCF_TEXT
            | commctrl.LVCF_SUBITEM
            | commctrl.LVCF_IMAGE
            | commctrl.LVCF_ORDER
        )
    if mask & commctrl.LVCF_TEXT:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0
    buf = struct.pack(_lvcolumn_fmt, mask, 0, 0, text_addr, text_buf_size, 0, 0, 0)
    return array.array("b", buf), extra


# List view hit-test.
def PackLVHITTEST(pt):
    format = "iiiii"
    buf = struct.pack(format, pt[0], pt[1], 0, 0, 0)
    return array.array("b", buf), None


def UnpackLVHITTEST(buf):
    format = "iiiii"
    x, y, flags, item, subitem = struct.unpack(format, buf)
    return _MakeResult(
        "LVHITTEST pt flags item subitem", ((x, y), flags, item, subitem)
    )


def PackHDITEM(
    cxy=None, text=None, hbm=None, fmt=None, param=None, image=None, order=None
):
    extra = []  # objects we must keep references to
    mask = 0
    mask, cxy = _GetMaskAndVal(cxy, 0, mask, commctrl.HDI_HEIGHT)
    mask, text = _GetMaskAndVal(text, None, mask, commctrl.LVCF_TEXT)
    mask, hbm = _GetMaskAndVal(hbm, 0, mask, commctrl.HDI_BITMAP)
    mask, fmt = _GetMaskAndVal(fmt, 0, mask, commctrl.HDI_FORMAT)
    mask, param = _GetMaskAndVal(param, 0, mask, commctrl.HDI_LPARAM)
    mask, image = _GetMaskAndVal(image, 0, mask, commctrl.HDI_IMAGE)
    mask, order = _GetMaskAndVal(order, 0, mask, commctrl.HDI_ORDER)

    if text is None:
        text_addr = text_len = 0
    else:
        text_buffer = _make_text_buffer(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
        text_len = len(text)

    format = "iiPPiiPiiii"
    buf = struct.pack(
        format, mask, cxy, text_addr, hbm, text_len, fmt, param, image, order, 0, 0
    )
    return array.array("b", buf), extra


# Device notification stuff


# Generic function for packing a DEV_BROADCAST_* structure - generally used
# by the other PackDEV_BROADCAST_* functions in this module.
def PackDEV_BROADCAST(devicetype, rest_fmt, rest_data, extra_data=b""):
    # It seems a requirement is 4 byte alignment, even for the 'BYTE data[1]'
    # field (eg, that would make DEV_BROADCAST_HANDLE 41 bytes, but we must
    # be 44.
    extra_data += b"\0" * (4 - len(extra_data) % 4)
    format = "iii" + rest_fmt
    full_size = struct.calcsize(format) + len(extra_data)
    data = (full_size, devicetype, 0) + rest_data
    return struct.pack(format, *data) + extra_data


def PackDEV_BROADCAST_HANDLE(
    handle,
    hdevnotify=0,
    guid=b"\0" * 16,
    name_offset=0,
    data=b"\0",
):
    return PackDEV_BROADCAST(
        win32con.DBT_DEVTYP_HANDLE,
        "PP16sl",
        (int(handle), int(hdevnotify), bytes(memoryview(guid)), name_offset),
        data,
    )


def PackDEV_BROADCAST_VOLUME(unitmask, flags):
    return PackDEV_BROADCAST(win32con.DBT_DEVTYP_VOLUME, "II", (unitmask, flags))


def PackDEV_BROADCAST_DEVICEINTERFACE(classguid, name=""):
    if not isinstance(name, str):
        raise TypeError("Must provide unicode for the name")
    name = name.encode("utf-16le")

    # 16 bytes for the IID followed by \0 term'd string.
    rest_fmt = "16s%ds" % len(name)
    # bytes(memoryview(iid)) hoops necessary to get the raw IID bytes.
    rest_data = (bytes(memoryview(pywintypes.IID(classguid))), name)
    return PackDEV_BROADCAST(win32con.DBT_DEVTYP_DEVICEINTERFACE, rest_fmt, rest_data)


# An object returned by UnpackDEV_BROADCAST.
class DEV_BROADCAST_INFO:
    def __init__(self, devicetype, **kw):
        self.devicetype = devicetype
        self.__dict__.update(kw)

    def __str__(self):
        return "DEV_BROADCAST_INFO:" + str(self.__dict__)


# Support for unpacking the 'lparam'
def UnpackDEV_BROADCAST(lparam):
    if lparam == 0:
        return None
    hdr_format = "iii"
    hdr_size = struct.calcsize(hdr_format)
    hdr_buf = win32gui.PyGetMemory(lparam, hdr_size)
    size, devtype, reserved = struct.unpack("iii", hdr_buf)
    # Due to x64 alignment issues, we need to use the full format string over
    # the entire buffer.  ie, on x64:
    # calcsize('iiiP') != calcsize('iii')+calcsize('P')
    buf = win32gui.PyGetMemory(lparam, size)

    extra = x = {}
    if devtype == win32con.DBT_DEVTYP_HANDLE:
        # 2 handles, a GUID, a LONG and possibly an array following...
        fmt = hdr_format + "PP16sl"
        (
            _,
            _,
            _,
            x["handle"],
            x["hdevnotify"],
            guid_bytes,
            x["nameoffset"],
        ) = struct.unpack(fmt, buf[: struct.calcsize(fmt)])
        x["eventguid"] = pywintypes.IID(guid_bytes, True)
    elif devtype == win32con.DBT_DEVTYP_DEVICEINTERFACE:
        fmt = hdr_format + "16s"
        _, _, _, guid_bytes = struct.unpack(fmt, buf[: struct.calcsize(fmt)])
        x["classguid"] = pywintypes.IID(guid_bytes, True)
        x["name"] = win32gui.PyGetString(lparam + struct.calcsize(fmt))
    elif devtype == win32con.DBT_DEVTYP_VOLUME:
        # int mask and flags
        fmt = hdr_format + "II"
        _, _, _, x["unitmask"], x["flags"] = struct.unpack(
            fmt, buf[: struct.calcsize(fmt)]
        )
    elif devtype == win32con.DBT_DEVTYP_PORT:
        x["name"] = win32gui.PyGetString(lparam + struct.calcsize(hdr_format))
    else:
        raise NotImplementedError("unknown device type %d" % (devtype,))
    return DEV_BROADCAST_INFO(devtype, **extra)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\win32gui_struct.py ===
# This is a work in progress - see Demos/win32gui_menu.py

# win32gui_struct.py - helpers for working with various win32gui structures.
# As win32gui is "light-weight", it does not define objects for all possible
# win32 structures - in general, "buffer" objects are passed around - it is
# the callers responsibility to pack the buffer in the correct format.
#
# This module defines some helpers for the commonly used structures.
#
# In general, each structure has 3 functions:
#
# buffer, extras = PackSTRUCTURE(items, ...)
# item, ... = UnpackSTRUCTURE(buffer)
# buffer, extras = EmtpySTRUCTURE(...)
#
# 'extras' is always items that must be held along with the buffer, as the
# buffer refers to these object's memory.
# For structures that support a 'mask', this mask is hidden from the user - if
# 'None' is passed, the mask flag will not be set, or on return, None will
# be returned for the value if the mask is not set.
#
# NOTE: I considered making these structures look like real classes, and
# support 'attributes' etc - however, ctypes already has a good structure
# mechanism - I think it makes more sense to support ctype structures
# at the win32gui level, then there will be no need for this module at all.
# XXX - the above makes sense in terms of what is built and passed to
# win32gui (ie, the Pack* functions) - but doesn't make as much sense for
# the Unpack* functions, where the aim is user convenience.

import array
import struct
import sys
from collections import namedtuple

import commctrl
import pywintypes
import win32con
import win32gui


def _MakeResult(names_str, values):
    names = names_str.split()
    # TODO: Dynamic namedtuple. This could be made static, also exposing the types
    nt = namedtuple(names[0], names[1:])  # noqa: PYI024
    return nt(*values)


is64bit = "64 bit" in sys.version
_nmhdr_fmt = "PPi"
if is64bit:
    # When the item past the NMHDR gets aligned (eg, when it is a struct)
    # we need this many bytes padding.
    _nmhdr_align_padding = "xxxx"
else:
    _nmhdr_align_padding = ""


# Encode a string suitable for passing in a win32gui related structure
def _make_text_buffer(text):
    if not isinstance(text, str):
        raise TypeError("MENUITEMINFO text must be unicode")
    data = (text + "\0").encode("utf-16le")
    return array.array("b", data)


# make an 'empty' buffer, ready for filling with cch characters.
def _make_empty_text_buffer(cch):
    return _make_text_buffer("\0" * cch)


# Generic WM_NOTIFY unpacking
def UnpackWMNOTIFY(lparam):
    format = "PPi"
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    return _MakeResult("WMNOTIFY hwndFrom idFrom code", struct.unpack(format, buf))


def UnpackNMITEMACTIVATE(lparam):
    format = _nmhdr_fmt + _nmhdr_align_padding
    if is64bit:
        # the struct module doesn't handle this correctly as some of the items
        # are actually structs in structs, which get individually aligned.
        format += "iiiiiiixxxxP"
    else:
        format += "iiiiiiiP"
    buf = win32gui.PyMakeBuffer(struct.calcsize(format), lparam)
    return _MakeResult(
        "NMITEMACTIVATE hwndFrom idFrom code iItem iSubItem uNewState uOldState uChanged actionx actiony lParam",
        struct.unpack(format, buf),
    )


# MENUITEMINFO struct
# https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-menuiteminfow
# We use the struct module to pack and unpack strings as MENUITEMINFO
# structures.  We also have special handling for the 'fMask' item in that
# structure to avoid the caller needing to explicitly check validity
# (None is used if the mask excludes/should exclude the value)
_menuiteminfo_fmt = "5i5PiP"


def PackMENUITEMINFO(
    fType=None,
    fState=None,
    wID=None,
    hSubMenu=None,
    hbmpChecked=None,
    hbmpUnchecked=None,
    dwItemData=None,
    text=None,
    hbmpItem=None,
    dwTypeData=None,
):
    # 'extras' are objects the caller must keep a reference to (as their
    # memory is used) for the lifetime of the INFO item.
    extras = []
    # ack - dwItemData and dwTypeData were confused for a while...
    assert (
        dwItemData is None or dwTypeData is None
    ), "sorry - these were confused - you probably want dwItemData"
    # if we are a long way past 209, then we can nuke the above...
    if dwTypeData is not None:
        import warnings

        warnings.warn("PackMENUITEMINFO: please use dwItemData instead of dwTypeData")
    if dwItemData is None:
        dwItemData = dwTypeData or 0

    fMask = 0
    if fType is None:
        fType = 0
    else:
        fMask |= win32con.MIIM_FTYPE
    if fState is None:
        fState = 0
    else:
        fMask |= win32con.MIIM_STATE
    if wID is None:
        wID = 0
    else:
        fMask |= win32con.MIIM_ID
    if hSubMenu is None:
        hSubMenu = 0
    else:
        fMask |= win32con.MIIM_SUBMENU
    if hbmpChecked is None:
        assert hbmpUnchecked is None, "neither or both checkmark bmps must be given"
        hbmpChecked = hbmpUnchecked = 0
    else:
        assert hbmpUnchecked is not None, "neither or both checkmark bmps must be given"
        fMask |= win32con.MIIM_CHECKMARKS
    if dwItemData is None:
        dwItemData = 0
    else:
        fMask |= win32con.MIIM_DATA
    if hbmpItem is None:
        hbmpItem = 0
    else:
        fMask |= win32con.MIIM_BITMAP
    if text is not None:
        fMask |= win32con.MIIM_STRING
        str_buf = _make_text_buffer(text)
        cch = len(text)
        # We are taking address of strbuf - it must not die until windows
        # has finished with our structure.
        lptext = str_buf.buffer_info()[0]
        extras.append(str_buf)
    else:
        lptext = 0
        cch = 0
    # Create the struct.
    # 'P' format does not accept PyHANDLE's !
    item = struct.pack(
        _menuiteminfo_fmt,
        struct.calcsize(_menuiteminfo_fmt),  # cbSize
        fMask,
        fType,
        fState,
        wID,
        int(hSubMenu),
        int(hbmpChecked),
        int(hbmpUnchecked),
        dwItemData,
        lptext,
        cch,
        int(hbmpItem),
    )
    # Now copy the string to a writable buffer, so that the result
    # could be passed to a 'Get' function
    return array.array("b", item), extras


def UnpackMENUITEMINFO(s):
    (
        cb,
        fMask,
        fType,
        fState,
        wID,
        hSubMenu,
        hbmpChecked,
        hbmpUnchecked,
        dwItemData,
        lptext,
        cch,
        hbmpItem,
    ) = struct.unpack(_menuiteminfo_fmt, s)
    assert cb == len(s)
    if fMask & win32con.MIIM_FTYPE == 0:
        fType = None
    if fMask & win32con.MIIM_STATE == 0:
        fState = None
    if fMask & win32con.MIIM_ID == 0:
        wID = None
    if fMask & win32con.MIIM_SUBMENU == 0:
        hSubMenu = None
    if fMask & win32con.MIIM_CHECKMARKS == 0:
        hbmpChecked = hbmpUnchecked = None
    if fMask & win32con.MIIM_DATA == 0:
        dwItemData = None
    if fMask & win32con.MIIM_BITMAP == 0:
        hbmpItem = None
    if fMask & win32con.MIIM_STRING:
        text = win32gui.PyGetString(lptext, cch)
    else:
        text = None
    return _MakeResult(
        "MENUITEMINFO fType fState wID hSubMenu hbmpChecked "
        "hbmpUnchecked dwItemData text hbmpItem",
        (
            fType,
            fState,
            wID,
            hSubMenu,
            hbmpChecked,
            hbmpUnchecked,
            dwItemData,
            text,
            hbmpItem,
        ),
    )


def EmptyMENUITEMINFO(mask=None, text_buf_size=512):
    # text_buf_size is number of *characters* - not necessarily no of bytes.
    extra = []
    if mask is None:
        mask = (
            win32con.MIIM_BITMAP
            | win32con.MIIM_CHECKMARKS
            | win32con.MIIM_DATA
            | win32con.MIIM_FTYPE
            | win32con.MIIM_ID
            | win32con.MIIM_STATE
            | win32con.MIIM_STRING
            | win32con.MIIM_SUBMENU
        )
        # Note: No MIIM_TYPE - this screws win2k/98.

    if mask & win32con.MIIM_STRING:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0

    # Now copy the string to a writable buffer, so that the result
    # could be passed to a 'Get' function
    buf = struct.pack(
        _menuiteminfo_fmt,
        struct.calcsize(_menuiteminfo_fmt),  # cbSize
        mask,
        0,  # fType,
        0,  # fState,
        0,  # wID,
        0,  # hSubMenu,
        0,  # hbmpChecked,
        0,  # hbmpUnchecked,
        0,  # dwItemData,
        text_addr,
        text_buf_size,
        0,  # hbmpItem
    )
    return array.array("b", buf), extra


# MENUINFO struct
_menuinfo_fmt = "iiiiPiP"


def PackMENUINFO(
    dwStyle=None,
    cyMax=None,
    hbrBack=None,
    dwContextHelpID=None,
    dwMenuData=None,
    fMask=0,
):
    if dwStyle is None:
        dwStyle = 0
    else:
        fMask |= win32con.MIM_STYLE
    if cyMax is None:
        cyMax = 0
    else:
        fMask |= win32con.MIM_MAXHEIGHT
    if hbrBack is None:
        hbrBack = 0
    else:
        fMask |= win32con.MIM_BACKGROUND
    if dwContextHelpID is None:
        dwContextHelpID = 0
    else:
        fMask |= win32con.MIM_HELPID
    if dwMenuData is None:
        dwMenuData = 0
    else:
        fMask |= win32con.MIM_MENUDATA
    # Create the struct.
    item = struct.pack(
        _menuinfo_fmt,
        struct.calcsize(_menuinfo_fmt),  # cbSize
        fMask,
        dwStyle,
        cyMax,
        hbrBack,
        dwContextHelpID,
        dwMenuData,
    )
    return array.array("b", item)


def UnpackMENUINFO(s):
    (cb, fMask, dwStyle, cyMax, hbrBack, dwContextHelpID, dwMenuData) = struct.unpack(
        _menuinfo_fmt, s
    )
    assert cb == len(s)
    if fMask & win32con.MIM_STYLE == 0:
        dwStyle = None
    if fMask & win32con.MIM_MAXHEIGHT == 0:
        cyMax = None
    if fMask & win32con.MIM_BACKGROUND == 0:
        hbrBack = None
    if fMask & win32con.MIM_HELPID == 0:
        dwContextHelpID = None
    if fMask & win32con.MIM_MENUDATA == 0:
        dwMenuData = None
    return _MakeResult(
        "MENUINFO dwStyle cyMax hbrBack dwContextHelpID dwMenuData",
        (dwStyle, cyMax, hbrBack, dwContextHelpID, dwMenuData),
    )


def EmptyMENUINFO(mask=None):
    if mask is None:
        mask = (
            win32con.MIM_STYLE
            | win32con.MIM_MAXHEIGHT
            | win32con.MIM_BACKGROUND
            | win32con.MIM_HELPID
            | win32con.MIM_MENUDATA
        )

    buf = struct.pack(
        _menuinfo_fmt,
        struct.calcsize(_menuinfo_fmt),  # cbSize
        mask,
        0,  # dwStyle
        0,  # cyMax
        0,  # hbrBack,
        0,  # dwContextHelpID,
        0,  # dwMenuData,
    )
    return array.array("b", buf)


##########################################################################
#
# Tree View structure support - TVITEM, TVINSERTSTRUCT and TVDISPINFO
#
##########################################################################

# XXX - Note that the following implementation of TreeView structures is ripped
# XXX - from the SpamBayes project.  It may not quite work correctly yet - I
# XXX - intend checking them later - but having them is better than not at all!

_tvitem_fmt = "iPiiPiiiiP"


# Helpers for the ugly win32 structure packing/unpacking
# XXX - Note that functions using _GetMaskAndVal run 3x faster if they are
# 'inlined' into the function - see PackLVITEM.  If the profiler points at
# _GetMaskAndVal(), you should nuke it (patches welcome once they have been
# tested)
def _GetMaskAndVal(val, default, mask, flag):
    if val is None:
        return mask, default
    else:
        if flag is not None:
            mask |= flag
        return mask, val


def PackTVINSERTSTRUCT(parent, insertAfter, tvitem):
    tvitem_buf, extra = PackTVITEM(*tvitem)
    tvitem_buf = tvitem_buf.tobytes()
    format = "PP%ds" % len(tvitem_buf)
    return struct.pack(format, parent, insertAfter, tvitem_buf), extra


def PackTVITEM(hitem, state, stateMask, text, image, selimage, citems, param):
    extra = []  # objects we must keep references to
    mask = 0
    mask, hitem = _GetMaskAndVal(hitem, 0, mask, commctrl.TVIF_HANDLE)
    mask, state = _GetMaskAndVal(state, 0, mask, commctrl.TVIF_STATE)
    if not mask & commctrl.TVIF_STATE:
        stateMask = 0
    mask, text = _GetMaskAndVal(text, None, mask, commctrl.TVIF_TEXT)
    mask, image = _GetMaskAndVal(image, 0, mask, commctrl.TVIF_IMAGE)
    mask, selimage = _GetMaskAndVal(selimage, 0, mask, commctrl.TVIF_SELECTEDIMAGE)
    mask, citems = _GetMaskAndVal(citems, 0, mask, commctrl.TVIF_CHILDREN)
    mask, param = _GetMaskAndVal(param, 0, mask, commctrl.TVIF_PARAM)
    if text is None:
        text_addr = text_len = 0
    else:
        text_buffer = _make_text_buffer(text)
        text_len = len(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    buf = struct.pack(
        _tvitem_fmt,
        mask,
        hitem,
        state,
        stateMask,
        text_addr,
        text_len,  # text
        image,
        selimage,
        citems,
        param,
    )
    return array.array("b", buf), extra


# Make a new buffer suitable for querying hitem's attributes.
def EmptyTVITEM(hitem, mask=None, text_buf_size=512):
    extra = []  # objects we must keep references to
    if mask is None:
        mask = (
            commctrl.TVIF_HANDLE
            | commctrl.TVIF_STATE
            | commctrl.TVIF_TEXT
            | commctrl.TVIF_IMAGE
            | commctrl.TVIF_SELECTEDIMAGE
            | commctrl.TVIF_CHILDREN
            | commctrl.TVIF_PARAM
        )
    if mask & commctrl.TVIF_TEXT:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0
    buf = struct.pack(
        _tvitem_fmt, mask, hitem, 0, 0, text_addr, text_buf_size, 0, 0, 0, 0
    )
    return array.array("b", buf), extra


def UnpackTVITEM(buffer):
    (
        item_mask,
        item_hItem,
        item_state,
        item_stateMask,
        item_textptr,
        item_cchText,
        item_image,
        item_selimage,
        item_cChildren,
        item_param,
    ) = struct.unpack(_tvitem_fmt, buffer)
    # ensure only items listed by the mask are valid (except we assume the
    # handle is always valid - some notifications (eg, TVN_ENDLABELEDIT) set a
    # mask that doesn't include the handle, but the docs explicity say it is.)
    if not (item_mask & commctrl.TVIF_TEXT):
        item_textptr = item_cchText = None
    if not (item_mask & commctrl.TVIF_CHILDREN):
        item_cChildren = None
    if not (item_mask & commctrl.TVIF_IMAGE):
        item_image = None
    if not (item_mask & commctrl.TVIF_PARAM):
        item_param = None
    if not (item_mask & commctrl.TVIF_SELECTEDIMAGE):
        item_selimage = None
    if not (item_mask & commctrl.TVIF_STATE):
        item_state = item_stateMask = None

    if item_textptr:
        text = win32gui.PyGetString(item_textptr)
    else:
        text = None
    return _MakeResult(
        "TVITEM item_hItem item_state item_stateMask "
        "text item_image item_selimage item_cChildren item_param",
        (
            item_hItem,
            item_state,
            item_stateMask,
            text,
            item_image,
            item_selimage,
            item_cChildren,
            item_param,
        ),
    )


# Unpack the lparm from a "TVNOTIFY" message
def UnpackTVNOTIFY(lparam):
    item_size = struct.calcsize(_tvitem_fmt)
    format = _nmhdr_fmt + _nmhdr_align_padding
    if is64bit:
        format += "ixxxx"
    else:
        format += "i"
    format += "%ds%ds" % (item_size, item_size)
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    hwndFrom, id, code, action, buf_old, buf_new = struct.unpack(format, buf)
    item_old = UnpackTVITEM(buf_old)
    item_new = UnpackTVITEM(buf_new)
    return _MakeResult(
        "TVNOTIFY hwndFrom id code action item_old item_new",
        (hwndFrom, id, code, action, item_old, item_new),
    )


def UnpackTVDISPINFO(lparam):
    item_size = struct.calcsize(_tvitem_fmt)
    format = "PPi%ds" % (item_size,)
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    hwndFrom, id, code, buf_item = struct.unpack(format, buf)
    item = UnpackTVITEM(buf_item)
    return _MakeResult("TVDISPINFO hwndFrom id code item", (hwndFrom, id, code, item))


#
# List view items
_lvitem_fmt = "iiiiiPiiPi"


def PackLVITEM(
    item=None,
    subItem=None,
    state=None,
    stateMask=None,
    text=None,
    image=None,
    param=None,
    indent=None,
):
    extra = []  # objects we must keep references to
    mask = 0
    # _GetMaskAndVal adds quite a bit of overhead to this function.
    if item is None:
        item = 0  # No mask for item
    if subItem is None:
        subItem = 0  # No mask for sibItem
    if state is None:
        state = 0
        stateMask = 0
    else:
        mask |= commctrl.LVIF_STATE
        if stateMask is None:
            stateMask = state

    if image is None:
        image = 0
    else:
        mask |= commctrl.LVIF_IMAGE
    if param is None:
        param = 0
    else:
        mask |= commctrl.LVIF_PARAM
    if indent is None:
        indent = 0
    else:
        mask |= commctrl.LVIF_INDENT

    if text is None:
        text_addr = text_len = 0
    else:
        mask |= commctrl.LVIF_TEXT
        text_buffer = _make_text_buffer(text)
        text_len = len(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    buf = struct.pack(
        _lvitem_fmt,
        mask,
        item,
        subItem,
        state,
        stateMask,
        text_addr,
        text_len,  # text
        image,
        param,
        indent,
    )
    return array.array("b", buf), extra


def UnpackLVITEM(buffer):
    (
        item_mask,
        item_item,
        item_subItem,
        item_state,
        item_stateMask,
        item_textptr,
        item_cchText,
        item_image,
        item_param,
        item_indent,
    ) = struct.unpack(_lvitem_fmt, buffer)
    # ensure only items listed by the mask are valid
    if not (item_mask & commctrl.LVIF_TEXT):
        item_textptr = item_cchText = None
    if not (item_mask & commctrl.LVIF_IMAGE):
        item_image = None
    if not (item_mask & commctrl.LVIF_PARAM):
        item_param = None
    if not (item_mask & commctrl.LVIF_INDENT):
        item_indent = None
    if not (item_mask & commctrl.LVIF_STATE):
        item_state = item_stateMask = None

    if item_textptr:
        text = win32gui.PyGetString(item_textptr)
    else:
        text = None
    return _MakeResult(
        "LVITEM item_item item_subItem item_state "
        "item_stateMask text item_image item_param item_indent",
        (
            item_item,
            item_subItem,
            item_state,
            item_stateMask,
            text,
            item_image,
            item_param,
            item_indent,
        ),
    )


# Unpack an "LVNOTIFY" message
def UnpackLVDISPINFO(lparam):
    item_size = struct.calcsize(_lvitem_fmt)
    format = _nmhdr_fmt + _nmhdr_align_padding + ("%ds" % (item_size,))
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    hwndFrom, id, code, buf_item = struct.unpack(format, buf)
    item = UnpackLVITEM(buf_item)
    return _MakeResult("LVDISPINFO hwndFrom id code item", (hwndFrom, id, code, item))


def UnpackLVNOTIFY(lparam):
    format = _nmhdr_fmt + _nmhdr_align_padding + "7i"
    if is64bit:
        format += "xxxx"  # point needs padding.
    format += "P"
    buf = win32gui.PyGetMemory(lparam, struct.calcsize(format))
    (
        hwndFrom,
        id,
        code,
        item,
        subitem,
        newstate,
        oldstate,
        changed,
        pt_x,
        pt_y,
        lparam,
    ) = struct.unpack(format, buf)
    return _MakeResult(
        "UnpackLVNOTIFY hwndFrom id code item subitem "
        "newstate oldstate changed pt lparam",
        (
            hwndFrom,
            id,
            code,
            item,
            subitem,
            newstate,
            oldstate,
            changed,
            (pt_x, pt_y),
            lparam,
        ),
    )


# Make a new buffer suitable for querying an items attributes.
def EmptyLVITEM(item, subitem, mask=None, text_buf_size=512):
    extra = []  # objects we must keep references to
    if mask is None:
        mask = (
            commctrl.LVIF_IMAGE
            | commctrl.LVIF_INDENT
            | commctrl.LVIF_TEXT
            | commctrl.LVIF_PARAM
            | commctrl.LVIF_STATE
        )
    if mask & commctrl.LVIF_TEXT:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0
    buf = struct.pack(
        _lvitem_fmt,
        mask,
        item,
        subitem,
        0,
        0,
        text_addr,
        text_buf_size,  # text
        0,
        0,
        0,
    )
    return array.array("b", buf), extra


# List view column structure
_lvcolumn_fmt = "iiiPiiii"


def PackLVCOLUMN(fmt=None, cx=None, text=None, subItem=None, image=None, order=None):
    extra = []  # objects we must keep references to
    mask = 0
    mask, fmt = _GetMaskAndVal(fmt, 0, mask, commctrl.LVCF_FMT)
    mask, cx = _GetMaskAndVal(cx, 0, mask, commctrl.LVCF_WIDTH)
    mask, text = _GetMaskAndVal(text, None, mask, commctrl.LVCF_TEXT)
    mask, subItem = _GetMaskAndVal(subItem, 0, mask, commctrl.LVCF_SUBITEM)
    mask, image = _GetMaskAndVal(image, 0, mask, commctrl.LVCF_IMAGE)
    mask, order = _GetMaskAndVal(order, 0, mask, commctrl.LVCF_ORDER)
    if text is None:
        text_addr = text_len = 0
    else:
        text_buffer = _make_text_buffer(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
        text_len = len(text)
    buf = struct.pack(
        _lvcolumn_fmt, mask, fmt, cx, text_addr, text_len, subItem, image, order
    )
    return array.array("b", buf), extra


def UnpackLVCOLUMN(lparam):
    mask, fmt, cx, text_addr, text_size, subItem, image, order = struct.unpack(
        _lvcolumn_fmt, lparam
    )
    # ensure only items listed by the mask are valid
    if not (mask & commctrl.LVCF_FMT):
        fmt = None
    if not (mask & commctrl.LVCF_WIDTH):
        cx = None
    if not (mask & commctrl.LVCF_TEXT):
        text_addr = text_size = None
    if not (mask & commctrl.LVCF_SUBITEM):
        subItem = None
    if not (mask & commctrl.LVCF_IMAGE):
        image = None
    if not (mask & commctrl.LVCF_ORDER):
        order = None
    if text_addr:
        text = win32gui.PyGetString(text_addr)
    else:
        text = None
    return _MakeResult(
        "LVCOLUMN fmt cx text subItem image order",
        (fmt, cx, text, subItem, image, order),
    )


# Make a new buffer suitable for querying an items attributes.
def EmptyLVCOLUMN(mask=None, text_buf_size=512):
    extra = []  # objects we must keep references to
    if mask is None:
        mask = (
            commctrl.LVCF_FMT
            | commctrl.LVCF_WIDTH
            | commctrl.LVCF_TEXT
            | commctrl.LVCF_SUBITEM
            | commctrl.LVCF_IMAGE
            | commctrl.LVCF_ORDER
        )
    if mask & commctrl.LVCF_TEXT:
        text_buffer = _make_empty_text_buffer(text_buf_size)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
    else:
        text_addr = text_buf_size = 0
    buf = struct.pack(_lvcolumn_fmt, mask, 0, 0, text_addr, text_buf_size, 0, 0, 0)
    return array.array("b", buf), extra


# List view hit-test.
def PackLVHITTEST(pt):
    format = "iiiii"
    buf = struct.pack(format, pt[0], pt[1], 0, 0, 0)
    return array.array("b", buf), None


def UnpackLVHITTEST(buf):
    format = "iiiii"
    x, y, flags, item, subitem = struct.unpack(format, buf)
    return _MakeResult(
        "LVHITTEST pt flags item subitem", ((x, y), flags, item, subitem)
    )


def PackHDITEM(
    cxy=None, text=None, hbm=None, fmt=None, param=None, image=None, order=None
):
    extra = []  # objects we must keep references to
    mask = 0
    mask, cxy = _GetMaskAndVal(cxy, 0, mask, commctrl.HDI_HEIGHT)
    mask, text = _GetMaskAndVal(text, None, mask, commctrl.LVCF_TEXT)
    mask, hbm = _GetMaskAndVal(hbm, 0, mask, commctrl.HDI_BITMAP)
    mask, fmt = _GetMaskAndVal(fmt, 0, mask, commctrl.HDI_FORMAT)
    mask, param = _GetMaskAndVal(param, 0, mask, commctrl.HDI_LPARAM)
    mask, image = _GetMaskAndVal(image, 0, mask, commctrl.HDI_IMAGE)
    mask, order = _GetMaskAndVal(order, 0, mask, commctrl.HDI_ORDER)

    if text is None:
        text_addr = text_len = 0
    else:
        text_buffer = _make_text_buffer(text)
        extra.append(text_buffer)
        text_addr, _ = text_buffer.buffer_info()
        text_len = len(text)

    format = "iiPPiiPiiii"
    buf = struct.pack(
        format, mask, cxy, text_addr, hbm, text_len, fmt, param, image, order, 0, 0
    )
    return array.array("b", buf), extra


# Device notification stuff


# Generic function for packing a DEV_BROADCAST_* structure - generally used
# by the other PackDEV_BROADCAST_* functions in this module.
def PackDEV_BROADCAST(devicetype, rest_fmt, rest_data, extra_data=b""):
    # It seems a requirement is 4 byte alignment, even for the 'BYTE data[1]'
    # field (eg, that would make DEV_BROADCAST_HANDLE 41 bytes, but we must
    # be 44.
    extra_data += b"\0" * (4 - len(extra_data) % 4)
    format = "iii" + rest_fmt
    full_size = struct.calcsize(format) + len(extra_data)
    data = (full_size, devicetype, 0) + rest_data
    return struct.pack(format, *data) + extra_data


def PackDEV_BROADCAST_HANDLE(
    handle,
    hdevnotify=0,
    guid=b"\0" * 16,
    name_offset=0,
    data=b"\0",
):
    return PackDEV_BROADCAST(
        win32con.DBT_DEVTYP_HANDLE,
        "PP16sl",
        (int(handle), int(hdevnotify), bytes(memoryview(guid)), name_offset),
        data,
    )


def PackDEV_BROADCAST_VOLUME(unitmask, flags):
    return PackDEV_BROADCAST(win32con.DBT_DEVTYP_VOLUME, "II", (unitmask, flags))


def PackDEV_BROADCAST_DEVICEINTERFACE(classguid, name=""):
    if not isinstance(name, str):
        raise TypeError("Must provide unicode for the name")
    name = name.encode("utf-16le")

    # 16 bytes for the IID followed by \0 term'd string.
    rest_fmt = "16s%ds" % len(name)
    # bytes(memoryview(iid)) hoops necessary to get the raw IID bytes.
    rest_data = (bytes(memoryview(pywintypes.IID(classguid))), name)
    return PackDEV_BROADCAST(win32con.DBT_DEVTYP_DEVICEINTERFACE, rest_fmt, rest_data)


# An object returned by UnpackDEV_BROADCAST.
class DEV_BROADCAST_INFO:
    def __init__(self, devicetype, **kw):
        self.devicetype = devicetype
        self.__dict__.update(kw)

    def __str__(self):
        return "DEV_BROADCAST_INFO:" + str(self.__dict__)


# Support for unpacking the 'lparam'
def UnpackDEV_BROADCAST(lparam):
    if lparam == 0:
        return None
    hdr_format = "iii"
    hdr_size = struct.calcsize(hdr_format)
    hdr_buf = win32gui.PyGetMemory(lparam, hdr_size)
    size, devtype, reserved = struct.unpack("iii", hdr_buf)
    # Due to x64 alignment issues, we need to use the full format string over
    # the entire buffer.  ie, on x64:
    # calcsize('iiiP') != calcsize('iii')+calcsize('P')
    buf = win32gui.PyGetMemory(lparam, size)

    extra = x = {}
    if devtype == win32con.DBT_DEVTYP_HANDLE:
        # 2 handles, a GUID, a LONG and possibly an array following...
        fmt = hdr_format + "PP16sl"
        (
            _,
            _,
            _,
            x["handle"],
            x["hdevnotify"],
            guid_bytes,
            x["nameoffset"],
        ) = struct.unpack(fmt, buf[: struct.calcsize(fmt)])
        x["eventguid"] = pywintypes.IID(guid_bytes, True)
    elif devtype == win32con.DBT_DEVTYP_DEVICEINTERFACE:
        fmt = hdr_format + "16s"
        _, _, _, guid_bytes = struct.unpack(fmt, buf[: struct.calcsize(fmt)])
        x["classguid"] = pywintypes.IID(guid_bytes, True)
        x["name"] = win32gui.PyGetString(lparam + struct.calcsize(fmt))
    elif devtype == win32con.DBT_DEVTYP_VOLUME:
        # int mask and flags
        fmt = hdr_format + "II"
        _, _, _, x["unitmask"], x["flags"] = struct.unpack(
            fmt, buf[: struct.calcsize(fmt)]
        )
    elif devtype == win32con.DBT_DEVTYP_PORT:
        x["name"] = win32gui.PyGetString(lparam + struct.calcsize(hdr_format))
    else:
        raise NotImplementedError("unknown device type %d" % (devtype,))
    return DEV_BROADCAST_INFO(devtype, **extra)

# === NexusCore/openenv\Lib\site-packages\win32\lib\mmsystem.py ===
import win32api

# Generated by h2py from d:/msdev/include/mmsystem.h
MAXPNAMELEN = 32
MAXERRORLENGTH = 256
MAX_JOYSTICKOEMVXDNAME = 260
MM_MICROSOFT = 1
MM_MIDI_MAPPER = 1
MM_WAVE_MAPPER = 2
MM_SNDBLST_MIDIOUT = 3
MM_SNDBLST_MIDIIN = 4
MM_SNDBLST_SYNTH = 5
MM_SNDBLST_WAVEOUT = 6
MM_SNDBLST_WAVEIN = 7
MM_ADLIB = 9
MM_MPU401_MIDIOUT = 10
MM_MPU401_MIDIIN = 11
MM_PC_JOYSTICK = 12
TIME_MS = 0x0001
TIME_SAMPLES = 0x0002
TIME_BYTES = 0x0004
TIME_SMPTE = 0x0008
TIME_MIDI = 0x0010
TIME_TICKS = 0x0020
MM_JOY1MOVE = 0x3A0
MM_JOY2MOVE = 0x3A1
MM_JOY1ZMOVE = 0x3A2
MM_JOY2ZMOVE = 0x3A3
MM_JOY1BUTTONDOWN = 0x3B5
MM_JOY2BUTTONDOWN = 0x3B6
MM_JOY1BUTTONUP = 0x3B7
MM_JOY2BUTTONUP = 0x3B8
MM_MCINOTIFY = 0x3B9
MM_WOM_OPEN = 0x3BB
MM_WOM_CLOSE = 0x3BC
MM_WOM_DONE = 0x3BD
MM_WIM_OPEN = 0x3BE
MM_WIM_CLOSE = 0x3BF
MM_WIM_DATA = 0x3C0
MM_MIM_OPEN = 0x3C1
MM_MIM_CLOSE = 0x3C2
MM_MIM_DATA = 0x3C3
MM_MIM_LONGDATA = 0x3C4
MM_MIM_ERROR = 0x3C5
MM_MIM_LONGERROR = 0x3C6
MM_MOM_OPEN = 0x3C7
MM_MOM_CLOSE = 0x3C8
MM_MOM_DONE = 0x3C9
MM_STREAM_OPEN = 0x3D4
MM_STREAM_CLOSE = 0x3D5
MM_STREAM_DONE = 0x3D6
MM_STREAM_ERROR = 0x3D7
MM_MOM_POSITIONCB = 0x3CA
MM_MIM_MOREDATA = 0x3CC
MM_MIXM_LINE_CHANGE = 0x3D0
MM_MIXM_CONTROL_CHANGE = 0x3D1
MMSYSERR_BASE = 0
WAVERR_BASE = 32
MIDIERR_BASE = 64
TIMERR_BASE = 96
JOYERR_BASE = 160
MCIERR_BASE = 256
MIXERR_BASE = 1024
MCI_STRING_OFFSET = 512
MCI_VD_OFFSET = 1024
MCI_CD_OFFSET = 1088
MCI_WAVE_OFFSET = 1152
MCI_SEQ_OFFSET = 1216
MMSYSERR_NOERROR = 0
MMSYSERR_ERROR = MMSYSERR_BASE + 1
MMSYSERR_BADDEVICEID = MMSYSERR_BASE + 2
MMSYSERR_NOTENABLED = MMSYSERR_BASE + 3
MMSYSERR_ALLOCATED = MMSYSERR_BASE + 4
MMSYSERR_INVALHANDLE = MMSYSERR_BASE + 5
MMSYSERR_NODRIVER = MMSYSERR_BASE + 6
MMSYSERR_NOMEM = MMSYSERR_BASE + 7
MMSYSERR_NOTSUPPORTED = MMSYSERR_BASE + 8
MMSYSERR_BADERRNUM = MMSYSERR_BASE + 9
MMSYSERR_INVALFLAG = MMSYSERR_BASE + 10
MMSYSERR_INVALPARAM = MMSYSERR_BASE + 11
MMSYSERR_HANDLEBUSY = MMSYSERR_BASE + 12
MMSYSERR_INVALIDALIAS = MMSYSERR_BASE + 13
MMSYSERR_BADDB = MMSYSERR_BASE + 14
MMSYSERR_KEYNOTFOUND = MMSYSERR_BASE + 15
MMSYSERR_READERROR = MMSYSERR_BASE + 16
MMSYSERR_WRITEERROR = MMSYSERR_BASE + 17
MMSYSERR_DELETEERROR = MMSYSERR_BASE + 18
MMSYSERR_VALNOTFOUND = MMSYSERR_BASE + 19
MMSYSERR_NODRIVERCB = MMSYSERR_BASE + 20
MMSYSERR_LASTERROR = MMSYSERR_BASE + 20
DRV_LOAD = 0x0001
DRV_ENABLE = 0x0002
DRV_OPEN = 0x0003
DRV_CLOSE = 0x0004
DRV_DISABLE = 0x0005
DRV_FREE = 0x0006
DRV_CONFIGURE = 0x0007
DRV_QUERYCONFIGURE = 0x0008
DRV_INSTALL = 0x0009
DRV_REMOVE = 0x000A
DRV_EXITSESSION = 0x000B
DRV_POWER = 0x000F
DRV_RESERVED = 0x0800
DRV_USER = 0x4000
DRVCNF_CANCEL = 0x0000
DRVCNF_OK = 0x0001
DRVCNF_RESTART = 0x0002
DRV_CANCEL = DRVCNF_CANCEL
DRV_OK = DRVCNF_OK
DRV_RESTART = DRVCNF_RESTART
DRV_MCI_FIRST = DRV_RESERVED
DRV_MCI_LAST = DRV_RESERVED + 0xFFF
CALLBACK_TYPEMASK = 0x00070000
CALLBACK_NULL = 0x00000000
CALLBACK_WINDOW = 0x00010000
CALLBACK_TASK = 0x00020000
CALLBACK_FUNCTION = 0x00030000
CALLBACK_THREAD = CALLBACK_TASK
CALLBACK_EVENT = 0x00050000
SND_SYNC = 0x0000
SND_ASYNC = 0x0001
SND_NODEFAULT = 0x0002
SND_MEMORY = 0x0004
SND_LOOP = 0x0008
SND_NOSTOP = 0x0010
SND_NOWAIT = 0x00002000
SND_ALIAS = 0x00010000
SND_ALIAS_ID = 0x00110000
SND_FILENAME = 0x00020000
SND_RESOURCE = 0x00040004
SND_PURGE = 0x0040
SND_APPLICATION = 0x0080
SND_ALIAS_START = 0
WAVERR_BADFORMAT = WAVERR_BASE + 0
WAVERR_STILLPLAYING = WAVERR_BASE + 1
WAVERR_UNPREPARED = WAVERR_BASE + 2
WAVERR_SYNC = WAVERR_BASE + 3
WAVERR_LASTERROR = WAVERR_BASE + 3
WOM_OPEN = MM_WOM_OPEN
WOM_CLOSE = MM_WOM_CLOSE
WOM_DONE = MM_WOM_DONE
WIM_OPEN = MM_WIM_OPEN
WIM_CLOSE = MM_WIM_CLOSE
WIM_DATA = MM_WIM_DATA
WAVE_MAPPER = -1  # 0xFFFFFFFF
WAVE_FORMAT_QUERY = 0x0001
WAVE_ALLOWSYNC = 0x0002
WAVE_MAPPED = 0x0004
WAVE_FORMAT_DIRECT = 0x0008
WAVE_FORMAT_DIRECT_QUERY = WAVE_FORMAT_QUERY | WAVE_FORMAT_DIRECT
WHDR_DONE = 0x00000001
WHDR_PREPARED = 0x00000002
WHDR_BEGINLOOP = 0x00000004
WHDR_ENDLOOP = 0x00000008
WHDR_INQUEUE = 0x00000010
WAVECAPS_PITCH = 0x0001
WAVECAPS_PLAYBACKRATE = 0x0002
WAVECAPS_VOLUME = 0x0004
WAVECAPS_LRVOLUME = 0x0008
WAVECAPS_SYNC = 0x0010
WAVECAPS_SAMPLEACCURATE = 0x0020
WAVECAPS_DIRECTSOUND = 0x0040
WAVE_INVALIDFORMAT = 0x00000000
WAVE_FORMAT_1M08 = 0x00000001
WAVE_FORMAT_1S08 = 0x00000002
WAVE_FORMAT_1M16 = 0x00000004
WAVE_FORMAT_1S16 = 0x00000008
WAVE_FORMAT_2M08 = 0x00000010
WAVE_FORMAT_2S08 = 0x00000020
WAVE_FORMAT_2M16 = 0x00000040
WAVE_FORMAT_2S16 = 0x00000080
WAVE_FORMAT_4M08 = 0x00000100
WAVE_FORMAT_4S08 = 0x00000200
WAVE_FORMAT_4M16 = 0x00000400
WAVE_FORMAT_4S16 = 0x00000800
WAVE_FORMAT_PCM = 1
WAVE_FORMAT_IEEE_FLOAT = 3
MIDIERR_UNPREPARED = MIDIERR_BASE + 0
MIDIERR_STILLPLAYING = MIDIERR_BASE + 1
MIDIERR_NOMAP = MIDIERR_BASE + 2
MIDIERR_NOTREADY = MIDIERR_BASE + 3
MIDIERR_NODEVICE = MIDIERR_BASE + 4
MIDIERR_INVALIDSETUP = MIDIERR_BASE + 5
MIDIERR_BADOPENMODE = MIDIERR_BASE + 6
MIDIERR_DONT_CONTINUE = MIDIERR_BASE + 7
MIDIERR_LASTERROR = MIDIERR_BASE + 7
MIDIPATCHSIZE = 128
MIM_OPEN = MM_MIM_OPEN
MIM_CLOSE = MM_MIM_CLOSE
MIM_DATA = MM_MIM_DATA
MIM_LONGDATA = MM_MIM_LONGDATA
MIM_ERROR = MM_MIM_ERROR
MIM_LONGERROR = MM_MIM_LONGERROR
MOM_OPEN = MM_MOM_OPEN
MOM_CLOSE = MM_MOM_CLOSE
MOM_DONE = MM_MOM_DONE
MIM_MOREDATA = MM_MIM_MOREDATA
MOM_POSITIONCB = MM_MOM_POSITIONCB
MIDI_IO_STATUS = 0x00000020
MIDI_CACHE_ALL = 1
MIDI_CACHE_BESTFIT = 2
MIDI_CACHE_QUERY = 3
MIDI_UNCACHE = 4
MOD_MIDIPORT = 1
MOD_SYNTH = 2
MOD_SQSYNTH = 3
MOD_FMSYNTH = 4
MOD_MAPPER = 5
MIDICAPS_VOLUME = 0x0001
MIDICAPS_LRVOLUME = 0x0002
MIDICAPS_CACHE = 0x0004
MIDICAPS_STREAM = 0x0008
MHDR_DONE = 0x00000001
MHDR_PREPARED = 0x00000002
MHDR_INQUEUE = 0x00000004
MHDR_ISSTRM = 0x00000008
MEVT_F_SHORT = 0x00000000
MEVT_F_LONG = -2147483648  # 0x80000000
MEVT_F_CALLBACK = 0x40000000


def MEVT_EVENTTYPE(x):
    return (x >> 24) & 0xFF


def MEVT_EVENTPARM(x):
    return x & 0x00FFFFFF


MIDISTRM_ERROR = -2
MIDIPROP_SET = -2147483648  # 0x80000000
MIDIPROP_GET = 0x40000000
MIDIPROP_TIMEDIV = 0x00000001
MIDIPROP_TEMPO = 0x00000002
AUXCAPS_CDAUDIO = 1
AUXCAPS_AUXIN = 2
AUXCAPS_VOLUME = 0x0001
AUXCAPS_LRVOLUME = 0x0002
MIXER_SHORT_NAME_CHARS = 16
MIXER_LONG_NAME_CHARS = 64
MIXERR_INVALLINE = MIXERR_BASE + 0
MIXERR_INVALCONTROL = MIXERR_BASE + 1
MIXERR_INVALVALUE = MIXERR_BASE + 2
MIXERR_LASTERROR = MIXERR_BASE + 2
MIXER_OBJECTF_HANDLE = -2147483648  # 0x80000000
MIXER_OBJECTF_MIXER = 0x00000000
MIXER_OBJECTF_HMIXER = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_MIXER
MIXER_OBJECTF_WAVEOUT = 0x10000000
MIXER_OBJECTF_HWAVEOUT = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_WAVEOUT
MIXER_OBJECTF_WAVEIN = 0x20000000
MIXER_OBJECTF_HWAVEIN = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_WAVEIN
MIXER_OBJECTF_MIDIOUT = 0x30000000
MIXER_OBJECTF_HMIDIOUT = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_MIDIOUT
MIXER_OBJECTF_MIDIIN = 0x40000000
MIXER_OBJECTF_HMIDIIN = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_MIDIIN
MIXER_OBJECTF_AUX = 0x50000000
MIXERLINE_LINEF_ACTIVE = 0x00000001
MIXERLINE_LINEF_DISCONNECTED = 0x00008000
MIXERLINE_LINEF_SOURCE = -2147483648  # 0x80000000
MIXERLINE_COMPONENTTYPE_DST_FIRST = 0x00000000
MIXERLINE_COMPONENTTYPE_DST_UNDEFINED = MIXERLINE_COMPONENTTYPE_DST_FIRST + 0
MIXERLINE_COMPONENTTYPE_DST_DIGITAL = MIXERLINE_COMPONENTTYPE_DST_FIRST + 1
MIXERLINE_COMPONENTTYPE_DST_LINE = MIXERLINE_COMPONENTTYPE_DST_FIRST + 2
MIXERLINE_COMPONENTTYPE_DST_MONITOR = MIXERLINE_COMPONENTTYPE_DST_FIRST + 3
MIXERLINE_COMPONENTTYPE_DST_SPEAKERS = MIXERLINE_COMPONENTTYPE_DST_FIRST + 4
MIXERLINE_COMPONENTTYPE_DST_HEADPHONES = MIXERLINE_COMPONENTTYPE_DST_FIRST + 5
MIXERLINE_COMPONENTTYPE_DST_TELEPHONE = MIXERLINE_COMPONENTTYPE_DST_FIRST + 6
MIXERLINE_COMPONENTTYPE_DST_WAVEIN = MIXERLINE_COMPONENTTYPE_DST_FIRST + 7
MIXERLINE_COMPONENTTYPE_DST_VOICEIN = MIXERLINE_COMPONENTTYPE_DST_FIRST + 8
MIXERLINE_COMPONENTTYPE_DST_LAST = MIXERLINE_COMPONENTTYPE_DST_FIRST + 8
MIXERLINE_COMPONENTTYPE_SRC_FIRST = 0x00001000
MIXERLINE_COMPONENTTYPE_SRC_UNDEFINED = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 0
MIXERLINE_COMPONENTTYPE_SRC_DIGITAL = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 1
MIXERLINE_COMPONENTTYPE_SRC_LINE = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 2
MIXERLINE_COMPONENTTYPE_SRC_MICROPHONE = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 3
MIXERLINE_COMPONENTTYPE_SRC_SYNTHESIZER = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 4
MIXERLINE_COMPONENTTYPE_SRC_COMPACTDISC = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 5
MIXERLINE_COMPONENTTYPE_SRC_TELEPHONE = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 6
MIXERLINE_COMPONENTTYPE_SRC_PCSPEAKER = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 7
MIXERLINE_COMPONENTTYPE_SRC_WAVEOUT = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 8
MIXERLINE_COMPONENTTYPE_SRC_AUXILIARY = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 9
MIXERLINE_COMPONENTTYPE_SRC_ANALOG = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 10
MIXERLINE_COMPONENTTYPE_SRC_LAST = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 10
MIXERLINE_TARGETTYPE_UNDEFINED = 0
MIXERLINE_TARGETTYPE_WAVEOUT = 1
MIXERLINE_TARGETTYPE_WAVEIN = 2
MIXERLINE_TARGETTYPE_MIDIOUT = 3
MIXERLINE_TARGETTYPE_MIDIIN = 4
MIXERLINE_TARGETTYPE_AUX = 5
MIXER_GETLINEINFOF_DESTINATION = 0x00000000
MIXER_GETLINEINFOF_SOURCE = 0x00000001
MIXER_GETLINEINFOF_LINEID = 0x00000002
MIXER_GETLINEINFOF_COMPONENTTYPE = 0x00000003
MIXER_GETLINEINFOF_TARGETTYPE = 0x00000004
MIXER_GETLINEINFOF_QUERYMASK = 0x0000000F
MIXERCONTROL_CONTROLF_UNIFORM = 0x00000001
MIXERCONTROL_CONTROLF_MULTIPLE = 0x00000002
MIXERCONTROL_CONTROLF_DISABLED = -2147483648  # 0x80000000
MIXERCONTROL_CT_CLASS_MASK = -268435456  # 0xF0000000
MIXERCONTROL_CT_CLASS_CUSTOM = 0x00000000
MIXERCONTROL_CT_CLASS_METER = 0x10000000
MIXERCONTROL_CT_CLASS_SWITCH = 0x20000000
MIXERCONTROL_CT_CLASS_NUMBER = 0x30000000
MIXERCONTROL_CT_CLASS_SLIDER = 0x40000000
MIXERCONTROL_CT_CLASS_FADER = 0x50000000
MIXERCONTROL_CT_CLASS_TIME = 0x60000000
MIXERCONTROL_CT_CLASS_LIST = 0x70000000
MIXERCONTROL_CT_SUBCLASS_MASK = 0x0F000000
MIXERCONTROL_CT_SC_SWITCH_BOOLEAN = 0x00000000
MIXERCONTROL_CT_SC_SWITCH_BUTTON = 0x01000000
MIXERCONTROL_CT_SC_METER_POLLED = 0x00000000
MIXERCONTROL_CT_SC_TIME_MICROSECS = 0x00000000
MIXERCONTROL_CT_SC_TIME_MILLISECS = 0x01000000
MIXERCONTROL_CT_SC_LIST_SINGLE = 0x00000000
MIXERCONTROL_CT_SC_LIST_MULTIPLE = 0x01000000
MIXERCONTROL_CT_UNITS_MASK = 0x00FF0000
MIXERCONTROL_CT_UNITS_CUSTOM = 0x00000000
MIXERCONTROL_CT_UNITS_BOOLEAN = 0x00010000
MIXERCONTROL_CT_UNITS_SIGNED = 0x00020000
MIXERCONTROL_CT_UNITS_UNSIGNED = 0x00030000
MIXERCONTROL_CT_UNITS_DECIBELS = 0x00040000
MIXERCONTROL_CT_UNITS_PERCENT = 0x00050000
MIXERCONTROL_CONTROLTYPE_CUSTOM = (
    MIXERCONTROL_CT_CLASS_CUSTOM | MIXERCONTROL_CT_UNITS_CUSTOM
)
MIXERCONTROL_CONTROLTYPE_BOOLEANMETER = (
    MIXERCONTROL_CT_CLASS_METER
    | MIXERCONTROL_CT_SC_METER_POLLED
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_SIGNEDMETER = (
    MIXERCONTROL_CT_CLASS_METER
    | MIXERCONTROL_CT_SC_METER_POLLED
    | MIXERCONTROL_CT_UNITS_SIGNED
)
MIXERCONTROL_CONTROLTYPE_PEAKMETER = MIXERCONTROL_CONTROLTYPE_SIGNEDMETER + 1
MIXERCONTROL_CONTROLTYPE_UNSIGNEDMETER = (
    MIXERCONTROL_CT_CLASS_METER
    | MIXERCONTROL_CT_SC_METER_POLLED
    | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_BOOLEAN = (
    MIXERCONTROL_CT_CLASS_SWITCH
    | MIXERCONTROL_CT_SC_SWITCH_BOOLEAN
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_ONOFF = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 1
MIXERCONTROL_CONTROLTYPE_MUTE = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 2
MIXERCONTROL_CONTROLTYPE_MONO = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 3
MIXERCONTROL_CONTROLTYPE_LOUDNESS = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 4
MIXERCONTROL_CONTROLTYPE_STEREOENH = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 5
MIXERCONTROL_CONTROLTYPE_BUTTON = (
    MIXERCONTROL_CT_CLASS_SWITCH
    | MIXERCONTROL_CT_SC_SWITCH_BUTTON
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_DECIBELS = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_DECIBELS
)
MIXERCONTROL_CONTROLTYPE_SIGNED = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_SIGNED
)
MIXERCONTROL_CONTROLTYPE_UNSIGNED = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_PERCENT = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_PERCENT
)
MIXERCONTROL_CONTROLTYPE_SLIDER = (
    MIXERCONTROL_CT_CLASS_SLIDER | MIXERCONTROL_CT_UNITS_SIGNED
)
MIXERCONTROL_CONTROLTYPE_PAN = MIXERCONTROL_CONTROLTYPE_SLIDER + 1
MIXERCONTROL_CONTROLTYPE_QSOUNDPAN = MIXERCONTROL_CONTROLTYPE_SLIDER + 2
MIXERCONTROL_CONTROLTYPE_FADER = (
    MIXERCONTROL_CT_CLASS_FADER | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_VOLUME = MIXERCONTROL_CONTROLTYPE_FADER + 1
MIXERCONTROL_CONTROLTYPE_BASS = MIXERCONTROL_CONTROLTYPE_FADER + 2
MIXERCONTROL_CONTROLTYPE_TREBLE = MIXERCONTROL_CONTROLTYPE_FADER + 3
MIXERCONTROL_CONTROLTYPE_EQUALIZER = MIXERCONTROL_CONTROLTYPE_FADER + 4
MIXERCONTROL_CONTROLTYPE_SINGLESELECT = (
    MIXERCONTROL_CT_CLASS_LIST
    | MIXERCONTROL_CT_SC_LIST_SINGLE
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_MUX = MIXERCONTROL_CONTROLTYPE_SINGLESELECT + 1
MIXERCONTROL_CONTROLTYPE_MULTIPLESELECT = (
    MIXERCONTROL_CT_CLASS_LIST
    | MIXERCONTROL_CT_SC_LIST_MULTIPLE
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_MIXER = MIXERCONTROL_CONTROLTYPE_MULTIPLESELECT + 1
MIXERCONTROL_CONTROLTYPE_MICROTIME = (
    MIXERCONTROL_CT_CLASS_TIME
    | MIXERCONTROL_CT_SC_TIME_MICROSECS
    | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_MILLITIME = (
    MIXERCONTROL_CT_CLASS_TIME
    | MIXERCONTROL_CT_SC_TIME_MILLISECS
    | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXER_GETLINECONTROLSF_ALL = 0x00000000
MIXER_GETLINECONTROLSF_ONEBYID = 0x00000001
MIXER_GETLINECONTROLSF_ONEBYTYPE = 0x00000002
MIXER_GETLINECONTROLSF_QUERYMASK = 0x0000000F
MIXER_GETCONTROLDETAILSF_VALUE = 0x00000000
MIXER_GETCONTROLDETAILSF_LISTTEXT = 0x00000001
MIXER_GETCONTROLDETAILSF_QUERYMASK = 0x0000000F
MIXER_SETCONTROLDETAILSF_VALUE = 0x00000000
MIXER_SETCONTROLDETAILSF_CUSTOM = 0x00000001
MIXER_SETCONTROLDETAILSF_QUERYMASK = 0x0000000F
TIMERR_NOERROR = 0
TIMERR_NOCANDO = TIMERR_BASE + 1
TIMERR_STRUCT = TIMERR_BASE + 33
TIME_ONESHOT = 0x0000
TIME_PERIODIC = 0x0001
TIME_CALLBACK_FUNCTION = 0x0000
TIME_CALLBACK_EVENT_SET = 0x0010
TIME_CALLBACK_EVENT_PULSE = 0x0020
JOYERR_NOERROR = 0
JOYERR_PARMS = JOYERR_BASE + 5
JOYERR_NOCANDO = JOYERR_BASE + 6
JOYERR_UNPLUGGED = JOYERR_BASE + 7
JOY_BUTTON1 = 0x0001
JOY_BUTTON2 = 0x0002
JOY_BUTTON3 = 0x0004
JOY_BUTTON4 = 0x0008
JOY_BUTTON1CHG = 0x0100
JOY_BUTTON2CHG = 0x0200
JOY_BUTTON3CHG = 0x0400
JOY_BUTTON4CHG = 0x0800
JOY_BUTTON5 = 0x00000010
JOY_BUTTON6 = 0x00000020
JOY_BUTTON7 = 0x00000040
JOY_BUTTON8 = 0x00000080
JOY_BUTTON9 = 0x00000100
JOY_BUTTON10 = 0x00000200
JOY_BUTTON11 = 0x00000400
JOY_BUTTON12 = 0x00000800
JOY_BUTTON13 = 0x00001000
JOY_BUTTON14 = 0x00002000
JOY_BUTTON15 = 0x00004000
JOY_BUTTON16 = 0x00008000
JOY_BUTTON17 = 0x00010000
JOY_BUTTON18 = 0x00020000
JOY_BUTTON19 = 0x00040000
JOY_BUTTON20 = 0x00080000
JOY_BUTTON21 = 0x00100000
JOY_BUTTON22 = 0x00200000
JOY_BUTTON23 = 0x00400000
JOY_BUTTON24 = 0x00800000
JOY_BUTTON25 = 0x01000000
JOY_BUTTON26 = 0x02000000
JOY_BUTTON27 = 0x04000000
JOY_BUTTON28 = 0x08000000
JOY_BUTTON29 = 0x10000000
JOY_BUTTON30 = 0x20000000
JOY_BUTTON31 = 0x40000000
JOY_BUTTON32 = -2147483648  # 0x80000000
JOY_POVFORWARD = 0
JOY_POVRIGHT = 9000
JOY_POVBACKWARD = 18000
JOY_POVLEFT = 27000
JOY_RETURNX = 0x00000001
JOY_RETURNY = 0x00000002
JOY_RETURNZ = 0x00000004
JOY_RETURNR = 0x00000008
JOY_RETURNU = 0x00000010
JOY_RETURNV = 0x00000020
JOY_RETURNPOV = 0x00000040
JOY_RETURNBUTTONS = 0x00000080
JOY_RETURNRAWDATA = 0x00000100
JOY_RETURNPOVCTS = 0x00000200
JOY_RETURNCENTERED = 0x00000400
JOY_USEDEADZONE = 0x00000800
JOY_RETURNALL = (
    JOY_RETURNX
    | JOY_RETURNY
    | JOY_RETURNZ
    | JOY_RETURNR
    | JOY_RETURNU
    | JOY_RETURNV
    | JOY_RETURNPOV
    | JOY_RETURNBUTTONS
)
JOY_CAL_READALWAYS = 0x00010000
JOY_CAL_READXYONLY = 0x00020000
JOY_CAL_READ3 = 0x00040000
JOY_CAL_READ4 = 0x00080000
JOY_CAL_READXONLY = 0x00100000
JOY_CAL_READYONLY = 0x00200000
JOY_CAL_READ5 = 0x00400000
JOY_CAL_READ6 = 0x00800000
JOY_CAL_READZONLY = 0x01000000
JOY_CAL_READRONLY = 0x02000000
JOY_CAL_READUONLY = 0x04000000
JOY_CAL_READVONLY = 0x08000000
JOYSTICKID1 = 0
JOYSTICKID2 = 1
JOYCAPS_HASZ = 0x0001
JOYCAPS_HASR = 0x0002
JOYCAPS_HASU = 0x0004
JOYCAPS_HASV = 0x0008
JOYCAPS_HASPOV = 0x0010
JOYCAPS_POV4DIR = 0x0020
JOYCAPS_POVCTS = 0x0040
MMIOERR_BASE = 256
MMIOERR_FILENOTFOUND = MMIOERR_BASE + 1
MMIOERR_OUTOFMEMORY = MMIOERR_BASE + 2
MMIOERR_CANNOTOPEN = MMIOERR_BASE + 3
MMIOERR_CANNOTCLOSE = MMIOERR_BASE + 4
MMIOERR_CANNOTREAD = MMIOERR_BASE + 5
MMIOERR_CANNOTWRITE = MMIOERR_BASE + 6
MMIOERR_CANNOTSEEK = MMIOERR_BASE + 7
MMIOERR_CANNOTEXPAND = MMIOERR_BASE + 8
MMIOERR_CHUNKNOTFOUND = MMIOERR_BASE + 9
MMIOERR_UNBUFFERED = MMIOERR_BASE + 10
MMIOERR_PATHNOTFOUND = MMIOERR_BASE + 11
MMIOERR_ACCESSDENIED = MMIOERR_BASE + 12
MMIOERR_SHARINGVIOLATION = MMIOERR_BASE + 13
MMIOERR_NETWORKERROR = MMIOERR_BASE + 14
MMIOERR_TOOMANYOPENFILES = MMIOERR_BASE + 15
MMIOERR_INVALIDFILE = MMIOERR_BASE + 16
CFSEPCHAR = ord("+")
MMIO_RWMODE = 0x00000003
MMIO_SHAREMODE = 0x00000070
MMIO_CREATE = 0x00001000
MMIO_PARSE = 0x00000100
MMIO_DELETE = 0x00000200
MMIO_EXIST = 0x00004000
MMIO_ALLOCBUF = 0x00010000
MMIO_GETTEMP = 0x00020000
MMIO_DIRTY = 0x10000000
MMIO_READ = 0x00000000
MMIO_WRITE = 0x00000001
MMIO_READWRITE = 0x00000002
MMIO_COMPAT = 0x00000000
MMIO_EXCLUSIVE = 0x00000010
MMIO_DENYWRITE = 0x00000020
MMIO_DENYREAD = 0x00000030
MMIO_DENYNONE = 0x00000040
MMIO_FHOPEN = 0x0010
MMIO_EMPTYBUF = 0x0010
MMIO_TOUPPER = 0x0010
MMIO_INSTALLPROC = 0x00010000
MMIO_GLOBALPROC = 0x10000000
MMIO_REMOVEPROC = 0x00020000
MMIO_UNICODEPROC = 0x01000000
MMIO_FINDPROC = 0x00040000
MMIO_FINDCHUNK = 0x0010
MMIO_FINDRIFF = 0x0020
MMIO_FINDLIST = 0x0040
MMIO_CREATERIFF = 0x0020
MMIO_CREATELIST = 0x0040
MMIOM_READ = MMIO_READ
MMIOM_WRITE = MMIO_WRITE
MMIOM_SEEK = 2
MMIOM_OPEN = 3
MMIOM_CLOSE = 4
MMIOM_WRITEFLUSH = 5
MMIOM_RENAME = 6
MMIOM_USER = 0x8000
SEEK_SET = 0
SEEK_CUR = 1
SEEK_END = 2
MMIO_DEFAULTBUFFER = 8192
MCIERR_INVALID_DEVICE_ID = MCIERR_BASE + 1
MCIERR_UNRECOGNIZED_KEYWORD = MCIERR_BASE + 3
MCIERR_UNRECOGNIZED_COMMAND = MCIERR_BASE + 5
MCIERR_HARDWARE = MCIERR_BASE + 6
MCIERR_INVALID_DEVICE_NAME = MCIERR_BASE + 7
MCIERR_OUT_OF_MEMORY = MCIERR_BASE + 8
MCIERR_DEVICE_OPEN = MCIERR_BASE + 9
MCIERR_CANNOT_LOAD_DRIVER = MCIERR_BASE + 10
MCIERR_MISSING_COMMAND_STRING = MCIERR_BASE + 11
MCIERR_PARAM_OVERFLOW = MCIERR_BASE + 12
MCIERR_MISSING_STRING_ARGUMENT = MCIERR_BASE + 13
MCIERR_BAD_INTEGER = MCIERR_BASE + 14
MCIERR_PARSER_INTERNAL = MCIERR_BASE + 15
MCIERR_DRIVER_INTERNAL = MCIERR_BASE + 16
MCIERR_MISSING_PARAMETER = MCIERR_BASE + 17
MCIERR_UNSUPPORTED_FUNCTION = MCIERR_BASE + 18
MCIERR_FILE_NOT_FOUND = MCIERR_BASE + 19
MCIERR_DEVICE_NOT_READY = MCIERR_BASE + 20
MCIERR_INTERNAL = MCIERR_BASE + 21
MCIERR_DRIVER = MCIERR_BASE + 22
MCIERR_CANNOT_USE_ALL = MCIERR_BASE + 23
MCIERR_MULTIPLE = MCIERR_BASE + 24
MCIERR_EXTENSION_NOT_FOUND = MCIERR_BASE + 25
MCIERR_OUTOFRANGE = MCIERR_BASE + 26
MCIERR_FLAGS_NOT_COMPATIBLE = MCIERR_BASE + 28
MCIERR_FILE_NOT_SAVED = MCIERR_BASE + 30
MCIERR_DEVICE_TYPE_REQUIRED = MCIERR_BASE + 31
MCIERR_DEVICE_LOCKED = MCIERR_BASE + 32
MCIERR_DUPLICATE_ALIAS = MCIERR_BASE + 33
MCIERR_BAD_CONSTANT = MCIERR_BASE + 34
MCIERR_MUST_USE_SHAREABLE = MCIERR_BASE + 35
MCIERR_MISSING_DEVICE_NAME = MCIERR_BASE + 36
MCIERR_BAD_TIME_FORMAT = MCIERR_BASE + 37
MCIERR_NO_CLOSING_QUOTE = MCIERR_BASE + 38
MCIERR_DUPLICATE_FLAGS = MCIERR_BASE + 39
MCIERR_INVALID_FILE = MCIERR_BASE + 40
MCIERR_NULL_PARAMETER_BLOCK = MCIERR_BASE + 41
MCIERR_UNNAMED_RESOURCE = MCIERR_BASE + 42
MCIERR_NEW_REQUIRES_ALIAS = MCIERR_BASE + 43
MCIERR_NOTIFY_ON_AUTO_OPEN = MCIERR_BASE + 44
MCIERR_NO_ELEMENT_ALLOWED = MCIERR_BASE + 45
MCIERR_NONAPPLICABLE_FUNCTION = MCIERR_BASE + 46
MCIERR_ILLEGAL_FOR_AUTO_OPEN = MCIERR_BASE + 47
MCIERR_FILENAME_REQUIRED = MCIERR_BASE + 48
MCIERR_EXTRA_CHARACTERS = MCIERR_BASE + 49
MCIERR_DEVICE_NOT_INSTALLED = MCIERR_BASE + 50
MCIERR_GET_CD = MCIERR_BASE + 51
MCIERR_SET_CD = MCIERR_BASE + 52
MCIERR_SET_DRIVE = MCIERR_BASE + 53
MCIERR_DEVICE_LENGTH = MCIERR_BASE + 54
MCIERR_DEVICE_ORD_LENGTH = MCIERR_BASE + 55
MCIERR_NO_INTEGER = MCIERR_BASE + 56
MCIERR_WAVE_OUTPUTSINUSE = MCIERR_BASE + 64
MCIERR_WAVE_SETOUTPUTINUSE = MCIERR_BASE + 65
MCIERR_WAVE_INPUTSINUSE = MCIERR_BASE + 66
MCIERR_WAVE_SETINPUTINUSE = MCIERR_BASE + 67
MCIERR_WAVE_OUTPUTUNSPECIFIED = MCIERR_BASE + 68
MCIERR_WAVE_INPUTUNSPECIFIED = MCIERR_BASE + 69
MCIERR_WAVE_OUTPUTSUNSUITABLE = MCIERR_BASE + 70
MCIERR_WAVE_SETOUTPUTUNSUITABLE = MCIERR_BASE + 71
MCIERR_WAVE_INPUTSUNSUITABLE = MCIERR_BASE + 72
MCIERR_WAVE_SETINPUTUNSUITABLE = MCIERR_BASE + 73
MCIERR_SEQ_DIV_INCOMPATIBLE = MCIERR_BASE + 80
MCIERR_SEQ_PORT_INUSE = MCIERR_BASE + 81
MCIERR_SEQ_PORT_NONEXISTENT = MCIERR_BASE + 82
MCIERR_SEQ_PORT_MAPNODEVICE = MCIERR_BASE + 83
MCIERR_SEQ_PORT_MISCERROR = MCIERR_BASE + 84
MCIERR_SEQ_TIMER = MCIERR_BASE + 85
MCIERR_SEQ_PORTUNSPECIFIED = MCIERR_BASE + 86
MCIERR_SEQ_NOMIDIPRESENT = MCIERR_BASE + 87
MCIERR_NO_WINDOW = MCIERR_BASE + 90
MCIERR_CREATEWINDOW = MCIERR_BASE + 91
MCIERR_FILE_READ = MCIERR_BASE + 92
MCIERR_FILE_WRITE = MCIERR_BASE + 93
MCIERR_NO_IDENTITY = MCIERR_BASE + 94
MCIERR_CUSTOM_DRIVER_BASE = MCIERR_BASE + 256
MCI_FIRST = DRV_MCI_FIRST
MCI_OPEN = 0x0803
MCI_CLOSE = 0x0804
MCI_ESCAPE = 0x0805
MCI_PLAY = 0x0806
MCI_SEEK = 0x0807
MCI_STOP = 0x0808
MCI_PAUSE = 0x0809
MCI_INFO = 0x080A
MCI_GETDEVCAPS = 0x080B
MCI_SPIN = 0x080C
MCI_SET = 0x080D
MCI_STEP = 0x080E
MCI_RECORD = 0x080F
MCI_SYSINFO = 0x0810
MCI_BREAK = 0x0811
MCI_SAVE = 0x0813
MCI_STATUS = 0x0814
MCI_CUE = 0x0830
MCI_REALIZE = 0x0840
MCI_WINDOW = 0x0841
MCI_PUT = 0x0842
MCI_WHERE = 0x0843
MCI_FREEZE = 0x0844
MCI_UNFREEZE = 0x0845
MCI_LOAD = 0x0850
MCI_CUT = 0x0851
MCI_COPY = 0x0852
MCI_PASTE = 0x0853
MCI_UPDATE = 0x0854
MCI_RESUME = 0x0855
MCI_DELETE = 0x0856
MCI_USER_MESSAGES = DRV_MCI_FIRST + 0x400
MCI_LAST = 0x0FFF
MCI_DEVTYPE_VCR = 513
MCI_DEVTYPE_VIDEODISC = 514
MCI_DEVTYPE_OVERLAY = 515
MCI_DEVTYPE_CD_AUDIO = 516
MCI_DEVTYPE_DAT = 517
MCI_DEVTYPE_SCANNER = 518
MCI_DEVTYPE_ANIMATION = 519
MCI_DEVTYPE_DIGITAL_VIDEO = 520
MCI_DEVTYPE_OTHER = 521
MCI_DEVTYPE_WAVEFORM_AUDIO = 522
MCI_DEVTYPE_SEQUENCER = 523
MCI_DEVTYPE_FIRST = MCI_DEVTYPE_VCR
MCI_DEVTYPE_LAST = MCI_DEVTYPE_SEQUENCER
MCI_DEVTYPE_FIRST_USER = 0x1000
MCI_MODE_NOT_READY = MCI_STRING_OFFSET + 12
MCI_MODE_STOP = MCI_STRING_OFFSET + 13
MCI_MODE_PLAY = MCI_STRING_OFFSET + 14
MCI_MODE_RECORD = MCI_STRING_OFFSET + 15
MCI_MODE_SEEK = MCI_STRING_OFFSET + 16
MCI_MODE_PAUSE = MCI_STRING_OFFSET + 17
MCI_MODE_OPEN = MCI_STRING_OFFSET + 18
MCI_FORMAT_MILLISECONDS = 0
MCI_FORMAT_HMS = 1
MCI_FORMAT_MSF = 2
MCI_FORMAT_FRAMES = 3
MCI_FORMAT_SMPTE_24 = 4
MCI_FORMAT_SMPTE_25 = 5
MCI_FORMAT_SMPTE_30 = 6
MCI_FORMAT_SMPTE_30DROP = 7
MCI_FORMAT_BYTES = 8
MCI_FORMAT_SAMPLES = 9
MCI_FORMAT_TMSF = 10


def MCI_MSF_MINUTE(msf):
    return msf


def MCI_MSF_SECOND(msf):
    return msf >> 8


def MCI_MSF_FRAME(msf):
    return msf >> 16


def MCI_TMSF_TRACK(tmsf):
    return tmsf


def MCI_TMSF_MINUTE(tmsf):
    return tmsf >> 8


def MCI_TMSF_SECOND(tmsf):
    return tmsf >> 16


def MCI_TMSF_FRAME(tmsf):
    return tmsf >> 24


def MCI_HMS_HOUR(hms):
    return hms


def MCI_HMS_MINUTE(hms):
    return hms >> 8


def MCI_HMS_SECOND(hms):
    return hms >> 16


MCI_NOTIFY_SUCCESSFUL = 0x0001
MCI_NOTIFY_SUPERSEDED = 0x0002
MCI_NOTIFY_ABORTED = 0x0004
MCI_NOTIFY_FAILURE = 0x0008
MCI_NOTIFY = 0x00000001
MCI_WAIT = 0x00000002
MCI_FROM = 0x00000004
MCI_TO = 0x00000008
MCI_TRACK = 0x00000010
MCI_OPEN_SHAREABLE = 0x00000100
MCI_OPEN_ELEMENT = 0x00000200
MCI_OPEN_ALIAS = 0x00000400
MCI_OPEN_ELEMENT_ID = 0x00000800
MCI_OPEN_TYPE_ID = 0x00001000
MCI_OPEN_TYPE = 0x00002000
MCI_SEEK_TO_START = 0x00000100
MCI_SEEK_TO_END = 0x00000200
MCI_STATUS_ITEM = 0x00000100
MCI_STATUS_START = 0x00000200
MCI_STATUS_LENGTH = 0x00000001
MCI_STATUS_POSITION = 0x00000002
MCI_STATUS_NUMBER_OF_TRACKS = 0x00000003
MCI_STATUS_MODE = 0x00000004
MCI_STATUS_MEDIA_PRESENT = 0x00000005
MCI_STATUS_TIME_FORMAT = 0x00000006
MCI_STATUS_READY = 0x00000007
MCI_STATUS_CURRENT_TRACK = 0x00000008
MCI_INFO_PRODUCT = 0x00000100
MCI_INFO_FILE = 0x00000200
MCI_INFO_MEDIA_UPC = 0x00000400
MCI_INFO_MEDIA_IDENTITY = 0x00000800
MCI_INFO_NAME = 0x00001000
MCI_INFO_COPYRIGHT = 0x00002000
MCI_GETDEVCAPS_ITEM = 0x00000100
MCI_GETDEVCAPS_CAN_RECORD = 0x00000001
MCI_GETDEVCAPS_HAS_AUDIO = 0x00000002
MCI_GETDEVCAPS_HAS_VIDEO = 0x00000003
MCI_GETDEVCAPS_DEVICE_TYPE = 0x00000004
MCI_GETDEVCAPS_USES_FILES = 0x00000005
MCI_GETDEVCAPS_COMPOUND_DEVICE = 0x00000006
MCI_GETDEVCAPS_CAN_EJECT = 0x00000007
MCI_GETDEVCAPS_CAN_PLAY = 0x00000008
MCI_GETDEVCAPS_CAN_SAVE = 0x00000009
MCI_SYSINFO_QUANTITY = 0x00000100
MCI_SYSINFO_OPEN = 0x00000200
MCI_SYSINFO_NAME = 0x00000400
MCI_SYSINFO_INSTALLNAME = 0x00000800
MCI_SET_DOOR_OPEN = 0x00000100
MCI_SET_DOOR_CLOSED = 0x00000200
MCI_SET_TIME_FORMAT = 0x00000400
MCI_SET_AUDIO = 0x00000800
MCI_SET_VIDEO = 0x00001000
MCI_SET_ON = 0x00002000
MCI_SET_OFF = 0x00004000
MCI_SET_AUDIO_ALL = 0x00000000
MCI_SET_AUDIO_LEFT = 0x00000001
MCI_SET_AUDIO_RIGHT = 0x00000002
MCI_BREAK_KEY = 0x00000100
MCI_BREAK_HWND = 0x00000200
MCI_BREAK_OFF = 0x00000400
MCI_RECORD_INSERT = 0x00000100
MCI_RECORD_OVERWRITE = 0x00000200
MCI_SAVE_FILE = 0x00000100
MCI_LOAD_FILE = 0x00000100
MCI_VD_MODE_PARK = MCI_VD_OFFSET + 1
MCI_VD_MEDIA_CLV = MCI_VD_OFFSET + 2
MCI_VD_MEDIA_CAV = MCI_VD_OFFSET + 3
MCI_VD_MEDIA_OTHER = MCI_VD_OFFSET + 4
MCI_VD_FORMAT_TRACK = 0x4001
MCI_VD_PLAY_REVERSE = 0x00010000
MCI_VD_PLAY_FAST = 0x00020000
MCI_VD_PLAY_SPEED = 0x00040000
MCI_VD_PLAY_SCAN = 0x00080000
MCI_VD_PLAY_SLOW = 0x00100000
MCI_VD_SEEK_REVERSE = 0x00010000
MCI_VD_STATUS_SPEED = 0x00004002
MCI_VD_STATUS_FORWARD = 0x00004003
MCI_VD_STATUS_MEDIA_TYPE = 0x00004004
MCI_VD_STATUS_SIDE = 0x00004005
MCI_VD_STATUS_DISC_SIZE = 0x00004006
MCI_VD_GETDEVCAPS_CLV = 0x00010000
MCI_VD_GETDEVCAPS_CAV = 0x00020000
MCI_VD_SPIN_UP = 0x00010000
MCI_VD_SPIN_DOWN = 0x00020000
MCI_VD_GETDEVCAPS_CAN_REVERSE = 0x00004002
MCI_VD_GETDEVCAPS_FAST_RATE = 0x00004003
MCI_VD_GETDEVCAPS_SLOW_RATE = 0x00004004
MCI_VD_GETDEVCAPS_NORMAL_RATE = 0x00004005
MCI_VD_STEP_FRAMES = 0x00010000
MCI_VD_STEP_REVERSE = 0x00020000
MCI_VD_ESCAPE_STRING = 0x00000100
MCI_CDA_STATUS_TYPE_TRACK = 0x00004001
MCI_CDA_TRACK_AUDIO = MCI_CD_OFFSET + 0
MCI_CDA_TRACK_OTHER = MCI_CD_OFFSET + 1
MCI_WAVE_PCM = MCI_WAVE_OFFSET + 0
MCI_WAVE_MAPPER = MCI_WAVE_OFFSET + 1
MCI_WAVE_OPEN_BUFFER = 0x00010000
MCI_WAVE_SET_FORMATTAG = 0x00010000
MCI_WAVE_SET_CHANNELS = 0x00020000
MCI_WAVE_SET_SAMPLESPERSEC = 0x00040000
MCI_WAVE_SET_AVGBYTESPERSEC = 0x00080000
MCI_WAVE_SET_BLOCKALIGN = 0x00100000
MCI_WAVE_SET_BITSPERSAMPLE = 0x00200000
MCI_WAVE_INPUT = 0x00400000
MCI_WAVE_OUTPUT = 0x00800000
MCI_WAVE_STATUS_FORMATTAG = 0x00004001
MCI_WAVE_STATUS_CHANNELS = 0x00004002
MCI_WAVE_STATUS_SAMPLESPERSEC = 0x00004003
MCI_WAVE_STATUS_AVGBYTESPERSEC = 0x00004004
MCI_WAVE_STATUS_BLOCKALIGN = 0x00004005
MCI_WAVE_STATUS_BITSPERSAMPLE = 0x00004006
MCI_WAVE_STATUS_LEVEL = 0x00004007
MCI_WAVE_SET_ANYINPUT = 0x04000000
MCI_WAVE_SET_ANYOUTPUT = 0x08000000
MCI_WAVE_GETDEVCAPS_INPUTS = 0x00004001
MCI_WAVE_GETDEVCAPS_OUTPUTS = 0x00004002
MCI_SEQ_DIV_PPQN = 0 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_24 = 1 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_25 = 2 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_30DROP = 3 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_30 = 4 + MCI_SEQ_OFFSET
MCI_SEQ_FORMAT_SONGPTR = 0x4001
MCI_SEQ_FILE = 0x4002
MCI_SEQ_MIDI = 0x4003
MCI_SEQ_SMPTE = 0x4004
MCI_SEQ_NONE = 65533
MCI_SEQ_MAPPER = 65535
MCI_SEQ_STATUS_TEMPO = 0x00004002
MCI_SEQ_STATUS_PORT = 0x00004003
MCI_SEQ_STATUS_SLAVE = 0x00004007
MCI_SEQ_STATUS_MASTER = 0x00004008
MCI_SEQ_STATUS_OFFSET = 0x00004009
MCI_SEQ_STATUS_DIVTYPE = 0x0000400A
MCI_SEQ_STATUS_NAME = 0x0000400B
MCI_SEQ_STATUS_COPYRIGHT = 0x0000400C
MCI_SEQ_SET_TEMPO = 0x00010000
MCI_SEQ_SET_PORT = 0x00020000
MCI_SEQ_SET_SLAVE = 0x00040000
MCI_SEQ_SET_MASTER = 0x00080000
MCI_SEQ_SET_OFFSET = 0x01000000
MCI_ANIM_OPEN_WS = 0x00010000
MCI_ANIM_OPEN_PARENT = 0x00020000
MCI_ANIM_OPEN_NOSTATIC = 0x00040000
MCI_ANIM_PLAY_SPEED = 0x00010000
MCI_ANIM_PLAY_REVERSE = 0x00020000
MCI_ANIM_PLAY_FAST = 0x00040000
MCI_ANIM_PLAY_SLOW = 0x00080000
MCI_ANIM_PLAY_SCAN = 0x00100000
MCI_ANIM_STEP_REVERSE = 0x00010000
MCI_ANIM_STEP_FRAMES = 0x00020000
MCI_ANIM_STATUS_SPEED = 0x00004001
MCI_ANIM_STATUS_FORWARD = 0x00004002
MCI_ANIM_STATUS_HWND = 0x00004003
MCI_ANIM_STATUS_HPAL = 0x00004004
MCI_ANIM_STATUS_STRETCH = 0x00004005
MCI_ANIM_INFO_TEXT = 0x00010000
MCI_ANIM_GETDEVCAPS_CAN_REVERSE = 0x00004001
MCI_ANIM_GETDEVCAPS_FAST_RATE = 0x00004002
MCI_ANIM_GETDEVCAPS_SLOW_RATE = 0x00004003
MCI_ANIM_GETDEVCAPS_NORMAL_RATE = 0x00004004
MCI_ANIM_GETDEVCAPS_PALETTES = 0x00004006
MCI_ANIM_GETDEVCAPS_CAN_STRETCH = 0x00004007
MCI_ANIM_GETDEVCAPS_MAX_WINDOWS = 0x00004008
MCI_ANIM_REALIZE_NORM = 0x00010000
MCI_ANIM_REALIZE_BKGD = 0x00020000
MCI_ANIM_WINDOW_HWND = 0x00010000
MCI_ANIM_WINDOW_STATE = 0x00040000
MCI_ANIM_WINDOW_TEXT = 0x00080000
MCI_ANIM_WINDOW_ENABLE_STRETCH = 0x00100000
MCI_ANIM_WINDOW_DISABLE_STRETCH = 0x00200000
MCI_ANIM_WINDOW_DEFAULT = 0x00000000
MCI_ANIM_RECT = 0x00010000
MCI_ANIM_PUT_SOURCE = 0x00020000
MCI_ANIM_PUT_DESTINATION = 0x00040000
MCI_ANIM_WHERE_SOURCE = 0x00020000
MCI_ANIM_WHERE_DESTINATION = 0x00040000
MCI_ANIM_UPDATE_HDC = 0x00020000
MCI_OVLY_OPEN_WS = 0x00010000
MCI_OVLY_OPEN_PARENT = 0x00020000
MCI_OVLY_STATUS_HWND = 0x00004001
MCI_OVLY_STATUS_STRETCH = 0x00004002
MCI_OVLY_INFO_TEXT = 0x00010000
MCI_OVLY_GETDEVCAPS_CAN_STRETCH = 0x00004001
MCI_OVLY_GETDEVCAPS_CAN_FREEZE = 0x00004002
MCI_OVLY_GETDEVCAPS_MAX_WINDOWS = 0x00004003
MCI_OVLY_WINDOW_HWND = 0x00010000
MCI_OVLY_WINDOW_STATE = 0x00040000
MCI_OVLY_WINDOW_TEXT = 0x00080000
MCI_OVLY_WINDOW_ENABLE_STRETCH = 0x00100000
MCI_OVLY_WINDOW_DISABLE_STRETCH = 0x00200000
MCI_OVLY_WINDOW_DEFAULT = 0x00000000
MCI_OVLY_RECT = 0x00010000
MCI_OVLY_PUT_SOURCE = 0x00020000
MCI_OVLY_PUT_DESTINATION = 0x00040000
MCI_OVLY_PUT_FRAME = 0x00080000
MCI_OVLY_PUT_VIDEO = 0x00100000
MCI_OVLY_WHERE_SOURCE = 0x00020000
MCI_OVLY_WHERE_DESTINATION = 0x00040000
MCI_OVLY_WHERE_FRAME = 0x00080000
MCI_OVLY_WHERE_VIDEO = 0x00100000
SELECTDIB = 41


def DIBINDEX(n):
    return win32api.MAKELONG(n, 0x10FF)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\mmsystem.py ===
import win32api

# Generated by h2py from d:/msdev/include/mmsystem.h
MAXPNAMELEN = 32
MAXERRORLENGTH = 256
MAX_JOYSTICKOEMVXDNAME = 260
MM_MICROSOFT = 1
MM_MIDI_MAPPER = 1
MM_WAVE_MAPPER = 2
MM_SNDBLST_MIDIOUT = 3
MM_SNDBLST_MIDIIN = 4
MM_SNDBLST_SYNTH = 5
MM_SNDBLST_WAVEOUT = 6
MM_SNDBLST_WAVEIN = 7
MM_ADLIB = 9
MM_MPU401_MIDIOUT = 10
MM_MPU401_MIDIIN = 11
MM_PC_JOYSTICK = 12
TIME_MS = 0x0001
TIME_SAMPLES = 0x0002
TIME_BYTES = 0x0004
TIME_SMPTE = 0x0008
TIME_MIDI = 0x0010
TIME_TICKS = 0x0020
MM_JOY1MOVE = 0x3A0
MM_JOY2MOVE = 0x3A1
MM_JOY1ZMOVE = 0x3A2
MM_JOY2ZMOVE = 0x3A3
MM_JOY1BUTTONDOWN = 0x3B5
MM_JOY2BUTTONDOWN = 0x3B6
MM_JOY1BUTTONUP = 0x3B7
MM_JOY2BUTTONUP = 0x3B8
MM_MCINOTIFY = 0x3B9
MM_WOM_OPEN = 0x3BB
MM_WOM_CLOSE = 0x3BC
MM_WOM_DONE = 0x3BD
MM_WIM_OPEN = 0x3BE
MM_WIM_CLOSE = 0x3BF
MM_WIM_DATA = 0x3C0
MM_MIM_OPEN = 0x3C1
MM_MIM_CLOSE = 0x3C2
MM_MIM_DATA = 0x3C3
MM_MIM_LONGDATA = 0x3C4
MM_MIM_ERROR = 0x3C5
MM_MIM_LONGERROR = 0x3C6
MM_MOM_OPEN = 0x3C7
MM_MOM_CLOSE = 0x3C8
MM_MOM_DONE = 0x3C9
MM_STREAM_OPEN = 0x3D4
MM_STREAM_CLOSE = 0x3D5
MM_STREAM_DONE = 0x3D6
MM_STREAM_ERROR = 0x3D7
MM_MOM_POSITIONCB = 0x3CA
MM_MIM_MOREDATA = 0x3CC
MM_MIXM_LINE_CHANGE = 0x3D0
MM_MIXM_CONTROL_CHANGE = 0x3D1
MMSYSERR_BASE = 0
WAVERR_BASE = 32
MIDIERR_BASE = 64
TIMERR_BASE = 96
JOYERR_BASE = 160
MCIERR_BASE = 256
MIXERR_BASE = 1024
MCI_STRING_OFFSET = 512
MCI_VD_OFFSET = 1024
MCI_CD_OFFSET = 1088
MCI_WAVE_OFFSET = 1152
MCI_SEQ_OFFSET = 1216
MMSYSERR_NOERROR = 0
MMSYSERR_ERROR = MMSYSERR_BASE + 1
MMSYSERR_BADDEVICEID = MMSYSERR_BASE + 2
MMSYSERR_NOTENABLED = MMSYSERR_BASE + 3
MMSYSERR_ALLOCATED = MMSYSERR_BASE + 4
MMSYSERR_INVALHANDLE = MMSYSERR_BASE + 5
MMSYSERR_NODRIVER = MMSYSERR_BASE + 6
MMSYSERR_NOMEM = MMSYSERR_BASE + 7
MMSYSERR_NOTSUPPORTED = MMSYSERR_BASE + 8
MMSYSERR_BADERRNUM = MMSYSERR_BASE + 9
MMSYSERR_INVALFLAG = MMSYSERR_BASE + 10
MMSYSERR_INVALPARAM = MMSYSERR_BASE + 11
MMSYSERR_HANDLEBUSY = MMSYSERR_BASE + 12
MMSYSERR_INVALIDALIAS = MMSYSERR_BASE + 13
MMSYSERR_BADDB = MMSYSERR_BASE + 14
MMSYSERR_KEYNOTFOUND = MMSYSERR_BASE + 15
MMSYSERR_READERROR = MMSYSERR_BASE + 16
MMSYSERR_WRITEERROR = MMSYSERR_BASE + 17
MMSYSERR_DELETEERROR = MMSYSERR_BASE + 18
MMSYSERR_VALNOTFOUND = MMSYSERR_BASE + 19
MMSYSERR_NODRIVERCB = MMSYSERR_BASE + 20
MMSYSERR_LASTERROR = MMSYSERR_BASE + 20
DRV_LOAD = 0x0001
DRV_ENABLE = 0x0002
DRV_OPEN = 0x0003
DRV_CLOSE = 0x0004
DRV_DISABLE = 0x0005
DRV_FREE = 0x0006
DRV_CONFIGURE = 0x0007
DRV_QUERYCONFIGURE = 0x0008
DRV_INSTALL = 0x0009
DRV_REMOVE = 0x000A
DRV_EXITSESSION = 0x000B
DRV_POWER = 0x000F
DRV_RESERVED = 0x0800
DRV_USER = 0x4000
DRVCNF_CANCEL = 0x0000
DRVCNF_OK = 0x0001
DRVCNF_RESTART = 0x0002
DRV_CANCEL = DRVCNF_CANCEL
DRV_OK = DRVCNF_OK
DRV_RESTART = DRVCNF_RESTART
DRV_MCI_FIRST = DRV_RESERVED
DRV_MCI_LAST = DRV_RESERVED + 0xFFF
CALLBACK_TYPEMASK = 0x00070000
CALLBACK_NULL = 0x00000000
CALLBACK_WINDOW = 0x00010000
CALLBACK_TASK = 0x00020000
CALLBACK_FUNCTION = 0x00030000
CALLBACK_THREAD = CALLBACK_TASK
CALLBACK_EVENT = 0x00050000
SND_SYNC = 0x0000
SND_ASYNC = 0x0001
SND_NODEFAULT = 0x0002
SND_MEMORY = 0x0004
SND_LOOP = 0x0008
SND_NOSTOP = 0x0010
SND_NOWAIT = 0x00002000
SND_ALIAS = 0x00010000
SND_ALIAS_ID = 0x00110000
SND_FILENAME = 0x00020000
SND_RESOURCE = 0x00040004
SND_PURGE = 0x0040
SND_APPLICATION = 0x0080
SND_ALIAS_START = 0
WAVERR_BADFORMAT = WAVERR_BASE + 0
WAVERR_STILLPLAYING = WAVERR_BASE + 1
WAVERR_UNPREPARED = WAVERR_BASE + 2
WAVERR_SYNC = WAVERR_BASE + 3
WAVERR_LASTERROR = WAVERR_BASE + 3
WOM_OPEN = MM_WOM_OPEN
WOM_CLOSE = MM_WOM_CLOSE
WOM_DONE = MM_WOM_DONE
WIM_OPEN = MM_WIM_OPEN
WIM_CLOSE = MM_WIM_CLOSE
WIM_DATA = MM_WIM_DATA
WAVE_MAPPER = -1  # 0xFFFFFFFF
WAVE_FORMAT_QUERY = 0x0001
WAVE_ALLOWSYNC = 0x0002
WAVE_MAPPED = 0x0004
WAVE_FORMAT_DIRECT = 0x0008
WAVE_FORMAT_DIRECT_QUERY = WAVE_FORMAT_QUERY | WAVE_FORMAT_DIRECT
WHDR_DONE = 0x00000001
WHDR_PREPARED = 0x00000002
WHDR_BEGINLOOP = 0x00000004
WHDR_ENDLOOP = 0x00000008
WHDR_INQUEUE = 0x00000010
WAVECAPS_PITCH = 0x0001
WAVECAPS_PLAYBACKRATE = 0x0002
WAVECAPS_VOLUME = 0x0004
WAVECAPS_LRVOLUME = 0x0008
WAVECAPS_SYNC = 0x0010
WAVECAPS_SAMPLEACCURATE = 0x0020
WAVECAPS_DIRECTSOUND = 0x0040
WAVE_INVALIDFORMAT = 0x00000000
WAVE_FORMAT_1M08 = 0x00000001
WAVE_FORMAT_1S08 = 0x00000002
WAVE_FORMAT_1M16 = 0x00000004
WAVE_FORMAT_1S16 = 0x00000008
WAVE_FORMAT_2M08 = 0x00000010
WAVE_FORMAT_2S08 = 0x00000020
WAVE_FORMAT_2M16 = 0x00000040
WAVE_FORMAT_2S16 = 0x00000080
WAVE_FORMAT_4M08 = 0x00000100
WAVE_FORMAT_4S08 = 0x00000200
WAVE_FORMAT_4M16 = 0x00000400
WAVE_FORMAT_4S16 = 0x00000800
WAVE_FORMAT_PCM = 1
WAVE_FORMAT_IEEE_FLOAT = 3
MIDIERR_UNPREPARED = MIDIERR_BASE + 0
MIDIERR_STILLPLAYING = MIDIERR_BASE + 1
MIDIERR_NOMAP = MIDIERR_BASE + 2
MIDIERR_NOTREADY = MIDIERR_BASE + 3
MIDIERR_NODEVICE = MIDIERR_BASE + 4
MIDIERR_INVALIDSETUP = MIDIERR_BASE + 5
MIDIERR_BADOPENMODE = MIDIERR_BASE + 6
MIDIERR_DONT_CONTINUE = MIDIERR_BASE + 7
MIDIERR_LASTERROR = MIDIERR_BASE + 7
MIDIPATCHSIZE = 128
MIM_OPEN = MM_MIM_OPEN
MIM_CLOSE = MM_MIM_CLOSE
MIM_DATA = MM_MIM_DATA
MIM_LONGDATA = MM_MIM_LONGDATA
MIM_ERROR = MM_MIM_ERROR
MIM_LONGERROR = MM_MIM_LONGERROR
MOM_OPEN = MM_MOM_OPEN
MOM_CLOSE = MM_MOM_CLOSE
MOM_DONE = MM_MOM_DONE
MIM_MOREDATA = MM_MIM_MOREDATA
MOM_POSITIONCB = MM_MOM_POSITIONCB
MIDI_IO_STATUS = 0x00000020
MIDI_CACHE_ALL = 1
MIDI_CACHE_BESTFIT = 2
MIDI_CACHE_QUERY = 3
MIDI_UNCACHE = 4
MOD_MIDIPORT = 1
MOD_SYNTH = 2
MOD_SQSYNTH = 3
MOD_FMSYNTH = 4
MOD_MAPPER = 5
MIDICAPS_VOLUME = 0x0001
MIDICAPS_LRVOLUME = 0x0002
MIDICAPS_CACHE = 0x0004
MIDICAPS_STREAM = 0x0008
MHDR_DONE = 0x00000001
MHDR_PREPARED = 0x00000002
MHDR_INQUEUE = 0x00000004
MHDR_ISSTRM = 0x00000008
MEVT_F_SHORT = 0x00000000
MEVT_F_LONG = -2147483648  # 0x80000000
MEVT_F_CALLBACK = 0x40000000


def MEVT_EVENTTYPE(x):
    return (x >> 24) & 0xFF


def MEVT_EVENTPARM(x):
    return x & 0x00FFFFFF


MIDISTRM_ERROR = -2
MIDIPROP_SET = -2147483648  # 0x80000000
MIDIPROP_GET = 0x40000000
MIDIPROP_TIMEDIV = 0x00000001
MIDIPROP_TEMPO = 0x00000002
AUXCAPS_CDAUDIO = 1
AUXCAPS_AUXIN = 2
AUXCAPS_VOLUME = 0x0001
AUXCAPS_LRVOLUME = 0x0002
MIXER_SHORT_NAME_CHARS = 16
MIXER_LONG_NAME_CHARS = 64
MIXERR_INVALLINE = MIXERR_BASE + 0
MIXERR_INVALCONTROL = MIXERR_BASE + 1
MIXERR_INVALVALUE = MIXERR_BASE + 2
MIXERR_LASTERROR = MIXERR_BASE + 2
MIXER_OBJECTF_HANDLE = -2147483648  # 0x80000000
MIXER_OBJECTF_MIXER = 0x00000000
MIXER_OBJECTF_HMIXER = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_MIXER
MIXER_OBJECTF_WAVEOUT = 0x10000000
MIXER_OBJECTF_HWAVEOUT = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_WAVEOUT
MIXER_OBJECTF_WAVEIN = 0x20000000
MIXER_OBJECTF_HWAVEIN = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_WAVEIN
MIXER_OBJECTF_MIDIOUT = 0x30000000
MIXER_OBJECTF_HMIDIOUT = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_MIDIOUT
MIXER_OBJECTF_MIDIIN = 0x40000000
MIXER_OBJECTF_HMIDIIN = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_MIDIIN
MIXER_OBJECTF_AUX = 0x50000000
MIXERLINE_LINEF_ACTIVE = 0x00000001
MIXERLINE_LINEF_DISCONNECTED = 0x00008000
MIXERLINE_LINEF_SOURCE = -2147483648  # 0x80000000
MIXERLINE_COMPONENTTYPE_DST_FIRST = 0x00000000
MIXERLINE_COMPONENTTYPE_DST_UNDEFINED = MIXERLINE_COMPONENTTYPE_DST_FIRST + 0
MIXERLINE_COMPONENTTYPE_DST_DIGITAL = MIXERLINE_COMPONENTTYPE_DST_FIRST + 1
MIXERLINE_COMPONENTTYPE_DST_LINE = MIXERLINE_COMPONENTTYPE_DST_FIRST + 2
MIXERLINE_COMPONENTTYPE_DST_MONITOR = MIXERLINE_COMPONENTTYPE_DST_FIRST + 3
MIXERLINE_COMPONENTTYPE_DST_SPEAKERS = MIXERLINE_COMPONENTTYPE_DST_FIRST + 4
MIXERLINE_COMPONENTTYPE_DST_HEADPHONES = MIXERLINE_COMPONENTTYPE_DST_FIRST + 5
MIXERLINE_COMPONENTTYPE_DST_TELEPHONE = MIXERLINE_COMPONENTTYPE_DST_FIRST + 6
MIXERLINE_COMPONENTTYPE_DST_WAVEIN = MIXERLINE_COMPONENTTYPE_DST_FIRST + 7
MIXERLINE_COMPONENTTYPE_DST_VOICEIN = MIXERLINE_COMPONENTTYPE_DST_FIRST + 8
MIXERLINE_COMPONENTTYPE_DST_LAST = MIXERLINE_COMPONENTTYPE_DST_FIRST + 8
MIXERLINE_COMPONENTTYPE_SRC_FIRST = 0x00001000
MIXERLINE_COMPONENTTYPE_SRC_UNDEFINED = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 0
MIXERLINE_COMPONENTTYPE_SRC_DIGITAL = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 1
MIXERLINE_COMPONENTTYPE_SRC_LINE = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 2
MIXERLINE_COMPONENTTYPE_SRC_MICROPHONE = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 3
MIXERLINE_COMPONENTTYPE_SRC_SYNTHESIZER = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 4
MIXERLINE_COMPONENTTYPE_SRC_COMPACTDISC = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 5
MIXERLINE_COMPONENTTYPE_SRC_TELEPHONE = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 6
MIXERLINE_COMPONENTTYPE_SRC_PCSPEAKER = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 7
MIXERLINE_COMPONENTTYPE_SRC_WAVEOUT = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 8
MIXERLINE_COMPONENTTYPE_SRC_AUXILIARY = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 9
MIXERLINE_COMPONENTTYPE_SRC_ANALOG = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 10
MIXERLINE_COMPONENTTYPE_SRC_LAST = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 10
MIXERLINE_TARGETTYPE_UNDEFINED = 0
MIXERLINE_TARGETTYPE_WAVEOUT = 1
MIXERLINE_TARGETTYPE_WAVEIN = 2
MIXERLINE_TARGETTYPE_MIDIOUT = 3
MIXERLINE_TARGETTYPE_MIDIIN = 4
MIXERLINE_TARGETTYPE_AUX = 5
MIXER_GETLINEINFOF_DESTINATION = 0x00000000
MIXER_GETLINEINFOF_SOURCE = 0x00000001
MIXER_GETLINEINFOF_LINEID = 0x00000002
MIXER_GETLINEINFOF_COMPONENTTYPE = 0x00000003
MIXER_GETLINEINFOF_TARGETTYPE = 0x00000004
MIXER_GETLINEINFOF_QUERYMASK = 0x0000000F
MIXERCONTROL_CONTROLF_UNIFORM = 0x00000001
MIXERCONTROL_CONTROLF_MULTIPLE = 0x00000002
MIXERCONTROL_CONTROLF_DISABLED = -2147483648  # 0x80000000
MIXERCONTROL_CT_CLASS_MASK = -268435456  # 0xF0000000
MIXERCONTROL_CT_CLASS_CUSTOM = 0x00000000
MIXERCONTROL_CT_CLASS_METER = 0x10000000
MIXERCONTROL_CT_CLASS_SWITCH = 0x20000000
MIXERCONTROL_CT_CLASS_NUMBER = 0x30000000
MIXERCONTROL_CT_CLASS_SLIDER = 0x40000000
MIXERCONTROL_CT_CLASS_FADER = 0x50000000
MIXERCONTROL_CT_CLASS_TIME = 0x60000000
MIXERCONTROL_CT_CLASS_LIST = 0x70000000
MIXERCONTROL_CT_SUBCLASS_MASK = 0x0F000000
MIXERCONTROL_CT_SC_SWITCH_BOOLEAN = 0x00000000
MIXERCONTROL_CT_SC_SWITCH_BUTTON = 0x01000000
MIXERCONTROL_CT_SC_METER_POLLED = 0x00000000
MIXERCONTROL_CT_SC_TIME_MICROSECS = 0x00000000
MIXERCONTROL_CT_SC_TIME_MILLISECS = 0x01000000
MIXERCONTROL_CT_SC_LIST_SINGLE = 0x00000000
MIXERCONTROL_CT_SC_LIST_MULTIPLE = 0x01000000
MIXERCONTROL_CT_UNITS_MASK = 0x00FF0000
MIXERCONTROL_CT_UNITS_CUSTOM = 0x00000000
MIXERCONTROL_CT_UNITS_BOOLEAN = 0x00010000
MIXERCONTROL_CT_UNITS_SIGNED = 0x00020000
MIXERCONTROL_CT_UNITS_UNSIGNED = 0x00030000
MIXERCONTROL_CT_UNITS_DECIBELS = 0x00040000
MIXERCONTROL_CT_UNITS_PERCENT = 0x00050000
MIXERCONTROL_CONTROLTYPE_CUSTOM = (
    MIXERCONTROL_CT_CLASS_CUSTOM | MIXERCONTROL_CT_UNITS_CUSTOM
)
MIXERCONTROL_CONTROLTYPE_BOOLEANMETER = (
    MIXERCONTROL_CT_CLASS_METER
    | MIXERCONTROL_CT_SC_METER_POLLED
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_SIGNEDMETER = (
    MIXERCONTROL_CT_CLASS_METER
    | MIXERCONTROL_CT_SC_METER_POLLED
    | MIXERCONTROL_CT_UNITS_SIGNED
)
MIXERCONTROL_CONTROLTYPE_PEAKMETER = MIXERCONTROL_CONTROLTYPE_SIGNEDMETER + 1
MIXERCONTROL_CONTROLTYPE_UNSIGNEDMETER = (
    MIXERCONTROL_CT_CLASS_METER
    | MIXERCONTROL_CT_SC_METER_POLLED
    | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_BOOLEAN = (
    MIXERCONTROL_CT_CLASS_SWITCH
    | MIXERCONTROL_CT_SC_SWITCH_BOOLEAN
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_ONOFF = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 1
MIXERCONTROL_CONTROLTYPE_MUTE = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 2
MIXERCONTROL_CONTROLTYPE_MONO = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 3
MIXERCONTROL_CONTROLTYPE_LOUDNESS = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 4
MIXERCONTROL_CONTROLTYPE_STEREOENH = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 5
MIXERCONTROL_CONTROLTYPE_BUTTON = (
    MIXERCONTROL_CT_CLASS_SWITCH
    | MIXERCONTROL_CT_SC_SWITCH_BUTTON
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_DECIBELS = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_DECIBELS
)
MIXERCONTROL_CONTROLTYPE_SIGNED = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_SIGNED
)
MIXERCONTROL_CONTROLTYPE_UNSIGNED = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_PERCENT = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_PERCENT
)
MIXERCONTROL_CONTROLTYPE_SLIDER = (
    MIXERCONTROL_CT_CLASS_SLIDER | MIXERCONTROL_CT_UNITS_SIGNED
)
MIXERCONTROL_CONTROLTYPE_PAN = MIXERCONTROL_CONTROLTYPE_SLIDER + 1
MIXERCONTROL_CONTROLTYPE_QSOUNDPAN = MIXERCONTROL_CONTROLTYPE_SLIDER + 2
MIXERCONTROL_CONTROLTYPE_FADER = (
    MIXERCONTROL_CT_CLASS_FADER | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_VOLUME = MIXERCONTROL_CONTROLTYPE_FADER + 1
MIXERCONTROL_CONTROLTYPE_BASS = MIXERCONTROL_CONTROLTYPE_FADER + 2
MIXERCONTROL_CONTROLTYPE_TREBLE = MIXERCONTROL_CONTROLTYPE_FADER + 3
MIXERCONTROL_CONTROLTYPE_EQUALIZER = MIXERCONTROL_CONTROLTYPE_FADER + 4
MIXERCONTROL_CONTROLTYPE_SINGLESELECT = (
    MIXERCONTROL_CT_CLASS_LIST
    | MIXERCONTROL_CT_SC_LIST_SINGLE
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_MUX = MIXERCONTROL_CONTROLTYPE_SINGLESELECT + 1
MIXERCONTROL_CONTROLTYPE_MULTIPLESELECT = (
    MIXERCONTROL_CT_CLASS_LIST
    | MIXERCONTROL_CT_SC_LIST_MULTIPLE
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_MIXER = MIXERCONTROL_CONTROLTYPE_MULTIPLESELECT + 1
MIXERCONTROL_CONTROLTYPE_MICROTIME = (
    MIXERCONTROL_CT_CLASS_TIME
    | MIXERCONTROL_CT_SC_TIME_MICROSECS
    | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_MILLITIME = (
    MIXERCONTROL_CT_CLASS_TIME
    | MIXERCONTROL_CT_SC_TIME_MILLISECS
    | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXER_GETLINECONTROLSF_ALL = 0x00000000
MIXER_GETLINECONTROLSF_ONEBYID = 0x00000001
MIXER_GETLINECONTROLSF_ONEBYTYPE = 0x00000002
MIXER_GETLINECONTROLSF_QUERYMASK = 0x0000000F
MIXER_GETCONTROLDETAILSF_VALUE = 0x00000000
MIXER_GETCONTROLDETAILSF_LISTTEXT = 0x00000001
MIXER_GETCONTROLDETAILSF_QUERYMASK = 0x0000000F
MIXER_SETCONTROLDETAILSF_VALUE = 0x00000000
MIXER_SETCONTROLDETAILSF_CUSTOM = 0x00000001
MIXER_SETCONTROLDETAILSF_QUERYMASK = 0x0000000F
TIMERR_NOERROR = 0
TIMERR_NOCANDO = TIMERR_BASE + 1
TIMERR_STRUCT = TIMERR_BASE + 33
TIME_ONESHOT = 0x0000
TIME_PERIODIC = 0x0001
TIME_CALLBACK_FUNCTION = 0x0000
TIME_CALLBACK_EVENT_SET = 0x0010
TIME_CALLBACK_EVENT_PULSE = 0x0020
JOYERR_NOERROR = 0
JOYERR_PARMS = JOYERR_BASE + 5
JOYERR_NOCANDO = JOYERR_BASE + 6
JOYERR_UNPLUGGED = JOYERR_BASE + 7
JOY_BUTTON1 = 0x0001
JOY_BUTTON2 = 0x0002
JOY_BUTTON3 = 0x0004
JOY_BUTTON4 = 0x0008
JOY_BUTTON1CHG = 0x0100
JOY_BUTTON2CHG = 0x0200
JOY_BUTTON3CHG = 0x0400
JOY_BUTTON4CHG = 0x0800
JOY_BUTTON5 = 0x00000010
JOY_BUTTON6 = 0x00000020
JOY_BUTTON7 = 0x00000040
JOY_BUTTON8 = 0x00000080
JOY_BUTTON9 = 0x00000100
JOY_BUTTON10 = 0x00000200
JOY_BUTTON11 = 0x00000400
JOY_BUTTON12 = 0x00000800
JOY_BUTTON13 = 0x00001000
JOY_BUTTON14 = 0x00002000
JOY_BUTTON15 = 0x00004000
JOY_BUTTON16 = 0x00008000
JOY_BUTTON17 = 0x00010000
JOY_BUTTON18 = 0x00020000
JOY_BUTTON19 = 0x00040000
JOY_BUTTON20 = 0x00080000
JOY_BUTTON21 = 0x00100000
JOY_BUTTON22 = 0x00200000
JOY_BUTTON23 = 0x00400000
JOY_BUTTON24 = 0x00800000
JOY_BUTTON25 = 0x01000000
JOY_BUTTON26 = 0x02000000
JOY_BUTTON27 = 0x04000000
JOY_BUTTON28 = 0x08000000
JOY_BUTTON29 = 0x10000000
JOY_BUTTON30 = 0x20000000
JOY_BUTTON31 = 0x40000000
JOY_BUTTON32 = -2147483648  # 0x80000000
JOY_POVFORWARD = 0
JOY_POVRIGHT = 9000
JOY_POVBACKWARD = 18000
JOY_POVLEFT = 27000
JOY_RETURNX = 0x00000001
JOY_RETURNY = 0x00000002
JOY_RETURNZ = 0x00000004
JOY_RETURNR = 0x00000008
JOY_RETURNU = 0x00000010
JOY_RETURNV = 0x00000020
JOY_RETURNPOV = 0x00000040
JOY_RETURNBUTTONS = 0x00000080
JOY_RETURNRAWDATA = 0x00000100
JOY_RETURNPOVCTS = 0x00000200
JOY_RETURNCENTERED = 0x00000400
JOY_USEDEADZONE = 0x00000800
JOY_RETURNALL = (
    JOY_RETURNX
    | JOY_RETURNY
    | JOY_RETURNZ
    | JOY_RETURNR
    | JOY_RETURNU
    | JOY_RETURNV
    | JOY_RETURNPOV
    | JOY_RETURNBUTTONS
)
JOY_CAL_READALWAYS = 0x00010000
JOY_CAL_READXYONLY = 0x00020000
JOY_CAL_READ3 = 0x00040000
JOY_CAL_READ4 = 0x00080000
JOY_CAL_READXONLY = 0x00100000
JOY_CAL_READYONLY = 0x00200000
JOY_CAL_READ5 = 0x00400000
JOY_CAL_READ6 = 0x00800000
JOY_CAL_READZONLY = 0x01000000
JOY_CAL_READRONLY = 0x02000000
JOY_CAL_READUONLY = 0x04000000
JOY_CAL_READVONLY = 0x08000000
JOYSTICKID1 = 0
JOYSTICKID2 = 1
JOYCAPS_HASZ = 0x0001
JOYCAPS_HASR = 0x0002
JOYCAPS_HASU = 0x0004
JOYCAPS_HASV = 0x0008
JOYCAPS_HASPOV = 0x0010
JOYCAPS_POV4DIR = 0x0020
JOYCAPS_POVCTS = 0x0040
MMIOERR_BASE = 256
MMIOERR_FILENOTFOUND = MMIOERR_BASE + 1
MMIOERR_OUTOFMEMORY = MMIOERR_BASE + 2
MMIOERR_CANNOTOPEN = MMIOERR_BASE + 3
MMIOERR_CANNOTCLOSE = MMIOERR_BASE + 4
MMIOERR_CANNOTREAD = MMIOERR_BASE + 5
MMIOERR_CANNOTWRITE = MMIOERR_BASE + 6
MMIOERR_CANNOTSEEK = MMIOERR_BASE + 7
MMIOERR_CANNOTEXPAND = MMIOERR_BASE + 8
MMIOERR_CHUNKNOTFOUND = MMIOERR_BASE + 9
MMIOERR_UNBUFFERED = MMIOERR_BASE + 10
MMIOERR_PATHNOTFOUND = MMIOERR_BASE + 11
MMIOERR_ACCESSDENIED = MMIOERR_BASE + 12
MMIOERR_SHARINGVIOLATION = MMIOERR_BASE + 13
MMIOERR_NETWORKERROR = MMIOERR_BASE + 14
MMIOERR_TOOMANYOPENFILES = MMIOERR_BASE + 15
MMIOERR_INVALIDFILE = MMIOERR_BASE + 16
CFSEPCHAR = ord("+")
MMIO_RWMODE = 0x00000003
MMIO_SHAREMODE = 0x00000070
MMIO_CREATE = 0x00001000
MMIO_PARSE = 0x00000100
MMIO_DELETE = 0x00000200
MMIO_EXIST = 0x00004000
MMIO_ALLOCBUF = 0x00010000
MMIO_GETTEMP = 0x00020000
MMIO_DIRTY = 0x10000000
MMIO_READ = 0x00000000
MMIO_WRITE = 0x00000001
MMIO_READWRITE = 0x00000002
MMIO_COMPAT = 0x00000000
MMIO_EXCLUSIVE = 0x00000010
MMIO_DENYWRITE = 0x00000020
MMIO_DENYREAD = 0x00000030
MMIO_DENYNONE = 0x00000040
MMIO_FHOPEN = 0x0010
MMIO_EMPTYBUF = 0x0010
MMIO_TOUPPER = 0x0010
MMIO_INSTALLPROC = 0x00010000
MMIO_GLOBALPROC = 0x10000000
MMIO_REMOVEPROC = 0x00020000
MMIO_UNICODEPROC = 0x01000000
MMIO_FINDPROC = 0x00040000
MMIO_FINDCHUNK = 0x0010
MMIO_FINDRIFF = 0x0020
MMIO_FINDLIST = 0x0040
MMIO_CREATERIFF = 0x0020
MMIO_CREATELIST = 0x0040
MMIOM_READ = MMIO_READ
MMIOM_WRITE = MMIO_WRITE
MMIOM_SEEK = 2
MMIOM_OPEN = 3
MMIOM_CLOSE = 4
MMIOM_WRITEFLUSH = 5
MMIOM_RENAME = 6
MMIOM_USER = 0x8000
SEEK_SET = 0
SEEK_CUR = 1
SEEK_END = 2
MMIO_DEFAULTBUFFER = 8192
MCIERR_INVALID_DEVICE_ID = MCIERR_BASE + 1
MCIERR_UNRECOGNIZED_KEYWORD = MCIERR_BASE + 3
MCIERR_UNRECOGNIZED_COMMAND = MCIERR_BASE + 5
MCIERR_HARDWARE = MCIERR_BASE + 6
MCIERR_INVALID_DEVICE_NAME = MCIERR_BASE + 7
MCIERR_OUT_OF_MEMORY = MCIERR_BASE + 8
MCIERR_DEVICE_OPEN = MCIERR_BASE + 9
MCIERR_CANNOT_LOAD_DRIVER = MCIERR_BASE + 10
MCIERR_MISSING_COMMAND_STRING = MCIERR_BASE + 11
MCIERR_PARAM_OVERFLOW = MCIERR_BASE + 12
MCIERR_MISSING_STRING_ARGUMENT = MCIERR_BASE + 13
MCIERR_BAD_INTEGER = MCIERR_BASE + 14
MCIERR_PARSER_INTERNAL = MCIERR_BASE + 15
MCIERR_DRIVER_INTERNAL = MCIERR_BASE + 16
MCIERR_MISSING_PARAMETER = MCIERR_BASE + 17
MCIERR_UNSUPPORTED_FUNCTION = MCIERR_BASE + 18
MCIERR_FILE_NOT_FOUND = MCIERR_BASE + 19
MCIERR_DEVICE_NOT_READY = MCIERR_BASE + 20
MCIERR_INTERNAL = MCIERR_BASE + 21
MCIERR_DRIVER = MCIERR_BASE + 22
MCIERR_CANNOT_USE_ALL = MCIERR_BASE + 23
MCIERR_MULTIPLE = MCIERR_BASE + 24
MCIERR_EXTENSION_NOT_FOUND = MCIERR_BASE + 25
MCIERR_OUTOFRANGE = MCIERR_BASE + 26
MCIERR_FLAGS_NOT_COMPATIBLE = MCIERR_BASE + 28
MCIERR_FILE_NOT_SAVED = MCIERR_BASE + 30
MCIERR_DEVICE_TYPE_REQUIRED = MCIERR_BASE + 31
MCIERR_DEVICE_LOCKED = MCIERR_BASE + 32
MCIERR_DUPLICATE_ALIAS = MCIERR_BASE + 33
MCIERR_BAD_CONSTANT = MCIERR_BASE + 34
MCIERR_MUST_USE_SHAREABLE = MCIERR_BASE + 35
MCIERR_MISSING_DEVICE_NAME = MCIERR_BASE + 36
MCIERR_BAD_TIME_FORMAT = MCIERR_BASE + 37
MCIERR_NO_CLOSING_QUOTE = MCIERR_BASE + 38
MCIERR_DUPLICATE_FLAGS = MCIERR_BASE + 39
MCIERR_INVALID_FILE = MCIERR_BASE + 40
MCIERR_NULL_PARAMETER_BLOCK = MCIERR_BASE + 41
MCIERR_UNNAMED_RESOURCE = MCIERR_BASE + 42
MCIERR_NEW_REQUIRES_ALIAS = MCIERR_BASE + 43
MCIERR_NOTIFY_ON_AUTO_OPEN = MCIERR_BASE + 44
MCIERR_NO_ELEMENT_ALLOWED = MCIERR_BASE + 45
MCIERR_NONAPPLICABLE_FUNCTION = MCIERR_BASE + 46
MCIERR_ILLEGAL_FOR_AUTO_OPEN = MCIERR_BASE + 47
MCIERR_FILENAME_REQUIRED = MCIERR_BASE + 48
MCIERR_EXTRA_CHARACTERS = MCIERR_BASE + 49
MCIERR_DEVICE_NOT_INSTALLED = MCIERR_BASE + 50
MCIERR_GET_CD = MCIERR_BASE + 51
MCIERR_SET_CD = MCIERR_BASE + 52
MCIERR_SET_DRIVE = MCIERR_BASE + 53
MCIERR_DEVICE_LENGTH = MCIERR_BASE + 54
MCIERR_DEVICE_ORD_LENGTH = MCIERR_BASE + 55
MCIERR_NO_INTEGER = MCIERR_BASE + 56
MCIERR_WAVE_OUTPUTSINUSE = MCIERR_BASE + 64
MCIERR_WAVE_SETOUTPUTINUSE = MCIERR_BASE + 65
MCIERR_WAVE_INPUTSINUSE = MCIERR_BASE + 66
MCIERR_WAVE_SETINPUTINUSE = MCIERR_BASE + 67
MCIERR_WAVE_OUTPUTUNSPECIFIED = MCIERR_BASE + 68
MCIERR_WAVE_INPUTUNSPECIFIED = MCIERR_BASE + 69
MCIERR_WAVE_OUTPUTSUNSUITABLE = MCIERR_BASE + 70
MCIERR_WAVE_SETOUTPUTUNSUITABLE = MCIERR_BASE + 71
MCIERR_WAVE_INPUTSUNSUITABLE = MCIERR_BASE + 72
MCIERR_WAVE_SETINPUTUNSUITABLE = MCIERR_BASE + 73
MCIERR_SEQ_DIV_INCOMPATIBLE = MCIERR_BASE + 80
MCIERR_SEQ_PORT_INUSE = MCIERR_BASE + 81
MCIERR_SEQ_PORT_NONEXISTENT = MCIERR_BASE + 82
MCIERR_SEQ_PORT_MAPNODEVICE = MCIERR_BASE + 83
MCIERR_SEQ_PORT_MISCERROR = MCIERR_BASE + 84
MCIERR_SEQ_TIMER = MCIERR_BASE + 85
MCIERR_SEQ_PORTUNSPECIFIED = MCIERR_BASE + 86
MCIERR_SEQ_NOMIDIPRESENT = MCIERR_BASE + 87
MCIERR_NO_WINDOW = MCIERR_BASE + 90
MCIERR_CREATEWINDOW = MCIERR_BASE + 91
MCIERR_FILE_READ = MCIERR_BASE + 92
MCIERR_FILE_WRITE = MCIERR_BASE + 93
MCIERR_NO_IDENTITY = MCIERR_BASE + 94
MCIERR_CUSTOM_DRIVER_BASE = MCIERR_BASE + 256
MCI_FIRST = DRV_MCI_FIRST
MCI_OPEN = 0x0803
MCI_CLOSE = 0x0804
MCI_ESCAPE = 0x0805
MCI_PLAY = 0x0806
MCI_SEEK = 0x0807
MCI_STOP = 0x0808
MCI_PAUSE = 0x0809
MCI_INFO = 0x080A
MCI_GETDEVCAPS = 0x080B
MCI_SPIN = 0x080C
MCI_SET = 0x080D
MCI_STEP = 0x080E
MCI_RECORD = 0x080F
MCI_SYSINFO = 0x0810
MCI_BREAK = 0x0811
MCI_SAVE = 0x0813
MCI_STATUS = 0x0814
MCI_CUE = 0x0830
MCI_REALIZE = 0x0840
MCI_WINDOW = 0x0841
MCI_PUT = 0x0842
MCI_WHERE = 0x0843
MCI_FREEZE = 0x0844
MCI_UNFREEZE = 0x0845
MCI_LOAD = 0x0850
MCI_CUT = 0x0851
MCI_COPY = 0x0852
MCI_PASTE = 0x0853
MCI_UPDATE = 0x0854
MCI_RESUME = 0x0855
MCI_DELETE = 0x0856
MCI_USER_MESSAGES = DRV_MCI_FIRST + 0x400
MCI_LAST = 0x0FFF
MCI_DEVTYPE_VCR = 513
MCI_DEVTYPE_VIDEODISC = 514
MCI_DEVTYPE_OVERLAY = 515
MCI_DEVTYPE_CD_AUDIO = 516
MCI_DEVTYPE_DAT = 517
MCI_DEVTYPE_SCANNER = 518
MCI_DEVTYPE_ANIMATION = 519
MCI_DEVTYPE_DIGITAL_VIDEO = 520
MCI_DEVTYPE_OTHER = 521
MCI_DEVTYPE_WAVEFORM_AUDIO = 522
MCI_DEVTYPE_SEQUENCER = 523
MCI_DEVTYPE_FIRST = MCI_DEVTYPE_VCR
MCI_DEVTYPE_LAST = MCI_DEVTYPE_SEQUENCER
MCI_DEVTYPE_FIRST_USER = 0x1000
MCI_MODE_NOT_READY = MCI_STRING_OFFSET + 12
MCI_MODE_STOP = MCI_STRING_OFFSET + 13
MCI_MODE_PLAY = MCI_STRING_OFFSET + 14
MCI_MODE_RECORD = MCI_STRING_OFFSET + 15
MCI_MODE_SEEK = MCI_STRING_OFFSET + 16
MCI_MODE_PAUSE = MCI_STRING_OFFSET + 17
MCI_MODE_OPEN = MCI_STRING_OFFSET + 18
MCI_FORMAT_MILLISECONDS = 0
MCI_FORMAT_HMS = 1
MCI_FORMAT_MSF = 2
MCI_FORMAT_FRAMES = 3
MCI_FORMAT_SMPTE_24 = 4
MCI_FORMAT_SMPTE_25 = 5
MCI_FORMAT_SMPTE_30 = 6
MCI_FORMAT_SMPTE_30DROP = 7
MCI_FORMAT_BYTES = 8
MCI_FORMAT_SAMPLES = 9
MCI_FORMAT_TMSF = 10


def MCI_MSF_MINUTE(msf):
    return msf


def MCI_MSF_SECOND(msf):
    return msf >> 8


def MCI_MSF_FRAME(msf):
    return msf >> 16


def MCI_TMSF_TRACK(tmsf):
    return tmsf


def MCI_TMSF_MINUTE(tmsf):
    return tmsf >> 8


def MCI_TMSF_SECOND(tmsf):
    return tmsf >> 16


def MCI_TMSF_FRAME(tmsf):
    return tmsf >> 24


def MCI_HMS_HOUR(hms):
    return hms


def MCI_HMS_MINUTE(hms):
    return hms >> 8


def MCI_HMS_SECOND(hms):
    return hms >> 16


MCI_NOTIFY_SUCCESSFUL = 0x0001
MCI_NOTIFY_SUPERSEDED = 0x0002
MCI_NOTIFY_ABORTED = 0x0004
MCI_NOTIFY_FAILURE = 0x0008
MCI_NOTIFY = 0x00000001
MCI_WAIT = 0x00000002
MCI_FROM = 0x00000004
MCI_TO = 0x00000008
MCI_TRACK = 0x00000010
MCI_OPEN_SHAREABLE = 0x00000100
MCI_OPEN_ELEMENT = 0x00000200
MCI_OPEN_ALIAS = 0x00000400
MCI_OPEN_ELEMENT_ID = 0x00000800
MCI_OPEN_TYPE_ID = 0x00001000
MCI_OPEN_TYPE = 0x00002000
MCI_SEEK_TO_START = 0x00000100
MCI_SEEK_TO_END = 0x00000200
MCI_STATUS_ITEM = 0x00000100
MCI_STATUS_START = 0x00000200
MCI_STATUS_LENGTH = 0x00000001
MCI_STATUS_POSITION = 0x00000002
MCI_STATUS_NUMBER_OF_TRACKS = 0x00000003
MCI_STATUS_MODE = 0x00000004
MCI_STATUS_MEDIA_PRESENT = 0x00000005
MCI_STATUS_TIME_FORMAT = 0x00000006
MCI_STATUS_READY = 0x00000007
MCI_STATUS_CURRENT_TRACK = 0x00000008
MCI_INFO_PRODUCT = 0x00000100
MCI_INFO_FILE = 0x00000200
MCI_INFO_MEDIA_UPC = 0x00000400
MCI_INFO_MEDIA_IDENTITY = 0x00000800
MCI_INFO_NAME = 0x00001000
MCI_INFO_COPYRIGHT = 0x00002000
MCI_GETDEVCAPS_ITEM = 0x00000100
MCI_GETDEVCAPS_CAN_RECORD = 0x00000001
MCI_GETDEVCAPS_HAS_AUDIO = 0x00000002
MCI_GETDEVCAPS_HAS_VIDEO = 0x00000003
MCI_GETDEVCAPS_DEVICE_TYPE = 0x00000004
MCI_GETDEVCAPS_USES_FILES = 0x00000005
MCI_GETDEVCAPS_COMPOUND_DEVICE = 0x00000006
MCI_GETDEVCAPS_CAN_EJECT = 0x00000007
MCI_GETDEVCAPS_CAN_PLAY = 0x00000008
MCI_GETDEVCAPS_CAN_SAVE = 0x00000009
MCI_SYSINFO_QUANTITY = 0x00000100
MCI_SYSINFO_OPEN = 0x00000200
MCI_SYSINFO_NAME = 0x00000400
MCI_SYSINFO_INSTALLNAME = 0x00000800
MCI_SET_DOOR_OPEN = 0x00000100
MCI_SET_DOOR_CLOSED = 0x00000200
MCI_SET_TIME_FORMAT = 0x00000400
MCI_SET_AUDIO = 0x00000800
MCI_SET_VIDEO = 0x00001000
MCI_SET_ON = 0x00002000
MCI_SET_OFF = 0x00004000
MCI_SET_AUDIO_ALL = 0x00000000
MCI_SET_AUDIO_LEFT = 0x00000001
MCI_SET_AUDIO_RIGHT = 0x00000002
MCI_BREAK_KEY = 0x00000100
MCI_BREAK_HWND = 0x00000200
MCI_BREAK_OFF = 0x00000400
MCI_RECORD_INSERT = 0x00000100
MCI_RECORD_OVERWRITE = 0x00000200
MCI_SAVE_FILE = 0x00000100
MCI_LOAD_FILE = 0x00000100
MCI_VD_MODE_PARK = MCI_VD_OFFSET + 1
MCI_VD_MEDIA_CLV = MCI_VD_OFFSET + 2
MCI_VD_MEDIA_CAV = MCI_VD_OFFSET + 3
MCI_VD_MEDIA_OTHER = MCI_VD_OFFSET + 4
MCI_VD_FORMAT_TRACK = 0x4001
MCI_VD_PLAY_REVERSE = 0x00010000
MCI_VD_PLAY_FAST = 0x00020000
MCI_VD_PLAY_SPEED = 0x00040000
MCI_VD_PLAY_SCAN = 0x00080000
MCI_VD_PLAY_SLOW = 0x00100000
MCI_VD_SEEK_REVERSE = 0x00010000
MCI_VD_STATUS_SPEED = 0x00004002
MCI_VD_STATUS_FORWARD = 0x00004003
MCI_VD_STATUS_MEDIA_TYPE = 0x00004004
MCI_VD_STATUS_SIDE = 0x00004005
MCI_VD_STATUS_DISC_SIZE = 0x00004006
MCI_VD_GETDEVCAPS_CLV = 0x00010000
MCI_VD_GETDEVCAPS_CAV = 0x00020000
MCI_VD_SPIN_UP = 0x00010000
MCI_VD_SPIN_DOWN = 0x00020000
MCI_VD_GETDEVCAPS_CAN_REVERSE = 0x00004002
MCI_VD_GETDEVCAPS_FAST_RATE = 0x00004003
MCI_VD_GETDEVCAPS_SLOW_RATE = 0x00004004
MCI_VD_GETDEVCAPS_NORMAL_RATE = 0x00004005
MCI_VD_STEP_FRAMES = 0x00010000
MCI_VD_STEP_REVERSE = 0x00020000
MCI_VD_ESCAPE_STRING = 0x00000100
MCI_CDA_STATUS_TYPE_TRACK = 0x00004001
MCI_CDA_TRACK_AUDIO = MCI_CD_OFFSET + 0
MCI_CDA_TRACK_OTHER = MCI_CD_OFFSET + 1
MCI_WAVE_PCM = MCI_WAVE_OFFSET + 0
MCI_WAVE_MAPPER = MCI_WAVE_OFFSET + 1
MCI_WAVE_OPEN_BUFFER = 0x00010000
MCI_WAVE_SET_FORMATTAG = 0x00010000
MCI_WAVE_SET_CHANNELS = 0x00020000
MCI_WAVE_SET_SAMPLESPERSEC = 0x00040000
MCI_WAVE_SET_AVGBYTESPERSEC = 0x00080000
MCI_WAVE_SET_BLOCKALIGN = 0x00100000
MCI_WAVE_SET_BITSPERSAMPLE = 0x00200000
MCI_WAVE_INPUT = 0x00400000
MCI_WAVE_OUTPUT = 0x00800000
MCI_WAVE_STATUS_FORMATTAG = 0x00004001
MCI_WAVE_STATUS_CHANNELS = 0x00004002
MCI_WAVE_STATUS_SAMPLESPERSEC = 0x00004003
MCI_WAVE_STATUS_AVGBYTESPERSEC = 0x00004004
MCI_WAVE_STATUS_BLOCKALIGN = 0x00004005
MCI_WAVE_STATUS_BITSPERSAMPLE = 0x00004006
MCI_WAVE_STATUS_LEVEL = 0x00004007
MCI_WAVE_SET_ANYINPUT = 0x04000000
MCI_WAVE_SET_ANYOUTPUT = 0x08000000
MCI_WAVE_GETDEVCAPS_INPUTS = 0x00004001
MCI_WAVE_GETDEVCAPS_OUTPUTS = 0x00004002
MCI_SEQ_DIV_PPQN = 0 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_24 = 1 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_25 = 2 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_30DROP = 3 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_30 = 4 + MCI_SEQ_OFFSET
MCI_SEQ_FORMAT_SONGPTR = 0x4001
MCI_SEQ_FILE = 0x4002
MCI_SEQ_MIDI = 0x4003
MCI_SEQ_SMPTE = 0x4004
MCI_SEQ_NONE = 65533
MCI_SEQ_MAPPER = 65535
MCI_SEQ_STATUS_TEMPO = 0x00004002
MCI_SEQ_STATUS_PORT = 0x00004003
MCI_SEQ_STATUS_SLAVE = 0x00004007
MCI_SEQ_STATUS_MASTER = 0x00004008
MCI_SEQ_STATUS_OFFSET = 0x00004009
MCI_SEQ_STATUS_DIVTYPE = 0x0000400A
MCI_SEQ_STATUS_NAME = 0x0000400B
MCI_SEQ_STATUS_COPYRIGHT = 0x0000400C
MCI_SEQ_SET_TEMPO = 0x00010000
MCI_SEQ_SET_PORT = 0x00020000
MCI_SEQ_SET_SLAVE = 0x00040000
MCI_SEQ_SET_MASTER = 0x00080000
MCI_SEQ_SET_OFFSET = 0x01000000
MCI_ANIM_OPEN_WS = 0x00010000
MCI_ANIM_OPEN_PARENT = 0x00020000
MCI_ANIM_OPEN_NOSTATIC = 0x00040000
MCI_ANIM_PLAY_SPEED = 0x00010000
MCI_ANIM_PLAY_REVERSE = 0x00020000
MCI_ANIM_PLAY_FAST = 0x00040000
MCI_ANIM_PLAY_SLOW = 0x00080000
MCI_ANIM_PLAY_SCAN = 0x00100000
MCI_ANIM_STEP_REVERSE = 0x00010000
MCI_ANIM_STEP_FRAMES = 0x00020000
MCI_ANIM_STATUS_SPEED = 0x00004001
MCI_ANIM_STATUS_FORWARD = 0x00004002
MCI_ANIM_STATUS_HWND = 0x00004003
MCI_ANIM_STATUS_HPAL = 0x00004004
MCI_ANIM_STATUS_STRETCH = 0x00004005
MCI_ANIM_INFO_TEXT = 0x00010000
MCI_ANIM_GETDEVCAPS_CAN_REVERSE = 0x00004001
MCI_ANIM_GETDEVCAPS_FAST_RATE = 0x00004002
MCI_ANIM_GETDEVCAPS_SLOW_RATE = 0x00004003
MCI_ANIM_GETDEVCAPS_NORMAL_RATE = 0x00004004
MCI_ANIM_GETDEVCAPS_PALETTES = 0x00004006
MCI_ANIM_GETDEVCAPS_CAN_STRETCH = 0x00004007
MCI_ANIM_GETDEVCAPS_MAX_WINDOWS = 0x00004008
MCI_ANIM_REALIZE_NORM = 0x00010000
MCI_ANIM_REALIZE_BKGD = 0x00020000
MCI_ANIM_WINDOW_HWND = 0x00010000
MCI_ANIM_WINDOW_STATE = 0x00040000
MCI_ANIM_WINDOW_TEXT = 0x00080000
MCI_ANIM_WINDOW_ENABLE_STRETCH = 0x00100000
MCI_ANIM_WINDOW_DISABLE_STRETCH = 0x00200000
MCI_ANIM_WINDOW_DEFAULT = 0x00000000
MCI_ANIM_RECT = 0x00010000
MCI_ANIM_PUT_SOURCE = 0x00020000
MCI_ANIM_PUT_DESTINATION = 0x00040000
MCI_ANIM_WHERE_SOURCE = 0x00020000
MCI_ANIM_WHERE_DESTINATION = 0x00040000
MCI_ANIM_UPDATE_HDC = 0x00020000
MCI_OVLY_OPEN_WS = 0x00010000
MCI_OVLY_OPEN_PARENT = 0x00020000
MCI_OVLY_STATUS_HWND = 0x00004001
MCI_OVLY_STATUS_STRETCH = 0x00004002
MCI_OVLY_INFO_TEXT = 0x00010000
MCI_OVLY_GETDEVCAPS_CAN_STRETCH = 0x00004001
MCI_OVLY_GETDEVCAPS_CAN_FREEZE = 0x00004002
MCI_OVLY_GETDEVCAPS_MAX_WINDOWS = 0x00004003
MCI_OVLY_WINDOW_HWND = 0x00010000
MCI_OVLY_WINDOW_STATE = 0x00040000
MCI_OVLY_WINDOW_TEXT = 0x00080000
MCI_OVLY_WINDOW_ENABLE_STRETCH = 0x00100000
MCI_OVLY_WINDOW_DISABLE_STRETCH = 0x00200000
MCI_OVLY_WINDOW_DEFAULT = 0x00000000
MCI_OVLY_RECT = 0x00010000
MCI_OVLY_PUT_SOURCE = 0x00020000
MCI_OVLY_PUT_DESTINATION = 0x00040000
MCI_OVLY_PUT_FRAME = 0x00080000
MCI_OVLY_PUT_VIDEO = 0x00100000
MCI_OVLY_WHERE_SOURCE = 0x00020000
MCI_OVLY_WHERE_DESTINATION = 0x00040000
MCI_OVLY_WHERE_FRAME = 0x00080000
MCI_OVLY_WHERE_VIDEO = 0x00100000
SELECTDIB = 41


def DIBINDEX(n):
    return win32api.MAKELONG(n, 0x10FF)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\mmsystem.py ===
import win32api

# Generated by h2py from d:/msdev/include/mmsystem.h
MAXPNAMELEN = 32
MAXERRORLENGTH = 256
MAX_JOYSTICKOEMVXDNAME = 260
MM_MICROSOFT = 1
MM_MIDI_MAPPER = 1
MM_WAVE_MAPPER = 2
MM_SNDBLST_MIDIOUT = 3
MM_SNDBLST_MIDIIN = 4
MM_SNDBLST_SYNTH = 5
MM_SNDBLST_WAVEOUT = 6
MM_SNDBLST_WAVEIN = 7
MM_ADLIB = 9
MM_MPU401_MIDIOUT = 10
MM_MPU401_MIDIIN = 11
MM_PC_JOYSTICK = 12
TIME_MS = 0x0001
TIME_SAMPLES = 0x0002
TIME_BYTES = 0x0004
TIME_SMPTE = 0x0008
TIME_MIDI = 0x0010
TIME_TICKS = 0x0020
MM_JOY1MOVE = 0x3A0
MM_JOY2MOVE = 0x3A1
MM_JOY1ZMOVE = 0x3A2
MM_JOY2ZMOVE = 0x3A3
MM_JOY1BUTTONDOWN = 0x3B5
MM_JOY2BUTTONDOWN = 0x3B6
MM_JOY1BUTTONUP = 0x3B7
MM_JOY2BUTTONUP = 0x3B8
MM_MCINOTIFY = 0x3B9
MM_WOM_OPEN = 0x3BB
MM_WOM_CLOSE = 0x3BC
MM_WOM_DONE = 0x3BD
MM_WIM_OPEN = 0x3BE
MM_WIM_CLOSE = 0x3BF
MM_WIM_DATA = 0x3C0
MM_MIM_OPEN = 0x3C1
MM_MIM_CLOSE = 0x3C2
MM_MIM_DATA = 0x3C3
MM_MIM_LONGDATA = 0x3C4
MM_MIM_ERROR = 0x3C5
MM_MIM_LONGERROR = 0x3C6
MM_MOM_OPEN = 0x3C7
MM_MOM_CLOSE = 0x3C8
MM_MOM_DONE = 0x3C9
MM_STREAM_OPEN = 0x3D4
MM_STREAM_CLOSE = 0x3D5
MM_STREAM_DONE = 0x3D6
MM_STREAM_ERROR = 0x3D7
MM_MOM_POSITIONCB = 0x3CA
MM_MIM_MOREDATA = 0x3CC
MM_MIXM_LINE_CHANGE = 0x3D0
MM_MIXM_CONTROL_CHANGE = 0x3D1
MMSYSERR_BASE = 0
WAVERR_BASE = 32
MIDIERR_BASE = 64
TIMERR_BASE = 96
JOYERR_BASE = 160
MCIERR_BASE = 256
MIXERR_BASE = 1024
MCI_STRING_OFFSET = 512
MCI_VD_OFFSET = 1024
MCI_CD_OFFSET = 1088
MCI_WAVE_OFFSET = 1152
MCI_SEQ_OFFSET = 1216
MMSYSERR_NOERROR = 0
MMSYSERR_ERROR = MMSYSERR_BASE + 1
MMSYSERR_BADDEVICEID = MMSYSERR_BASE + 2
MMSYSERR_NOTENABLED = MMSYSERR_BASE + 3
MMSYSERR_ALLOCATED = MMSYSERR_BASE + 4
MMSYSERR_INVALHANDLE = MMSYSERR_BASE + 5
MMSYSERR_NODRIVER = MMSYSERR_BASE + 6
MMSYSERR_NOMEM = MMSYSERR_BASE + 7
MMSYSERR_NOTSUPPORTED = MMSYSERR_BASE + 8
MMSYSERR_BADERRNUM = MMSYSERR_BASE + 9
MMSYSERR_INVALFLAG = MMSYSERR_BASE + 10
MMSYSERR_INVALPARAM = MMSYSERR_BASE + 11
MMSYSERR_HANDLEBUSY = MMSYSERR_BASE + 12
MMSYSERR_INVALIDALIAS = MMSYSERR_BASE + 13
MMSYSERR_BADDB = MMSYSERR_BASE + 14
MMSYSERR_KEYNOTFOUND = MMSYSERR_BASE + 15
MMSYSERR_READERROR = MMSYSERR_BASE + 16
MMSYSERR_WRITEERROR = MMSYSERR_BASE + 17
MMSYSERR_DELETEERROR = MMSYSERR_BASE + 18
MMSYSERR_VALNOTFOUND = MMSYSERR_BASE + 19
MMSYSERR_NODRIVERCB = MMSYSERR_BASE + 20
MMSYSERR_LASTERROR = MMSYSERR_BASE + 20
DRV_LOAD = 0x0001
DRV_ENABLE = 0x0002
DRV_OPEN = 0x0003
DRV_CLOSE = 0x0004
DRV_DISABLE = 0x0005
DRV_FREE = 0x0006
DRV_CONFIGURE = 0x0007
DRV_QUERYCONFIGURE = 0x0008
DRV_INSTALL = 0x0009
DRV_REMOVE = 0x000A
DRV_EXITSESSION = 0x000B
DRV_POWER = 0x000F
DRV_RESERVED = 0x0800
DRV_USER = 0x4000
DRVCNF_CANCEL = 0x0000
DRVCNF_OK = 0x0001
DRVCNF_RESTART = 0x0002
DRV_CANCEL = DRVCNF_CANCEL
DRV_OK = DRVCNF_OK
DRV_RESTART = DRVCNF_RESTART
DRV_MCI_FIRST = DRV_RESERVED
DRV_MCI_LAST = DRV_RESERVED + 0xFFF
CALLBACK_TYPEMASK = 0x00070000
CALLBACK_NULL = 0x00000000
CALLBACK_WINDOW = 0x00010000
CALLBACK_TASK = 0x00020000
CALLBACK_FUNCTION = 0x00030000
CALLBACK_THREAD = CALLBACK_TASK
CALLBACK_EVENT = 0x00050000
SND_SYNC = 0x0000
SND_ASYNC = 0x0001
SND_NODEFAULT = 0x0002
SND_MEMORY = 0x0004
SND_LOOP = 0x0008
SND_NOSTOP = 0x0010
SND_NOWAIT = 0x00002000
SND_ALIAS = 0x00010000
SND_ALIAS_ID = 0x00110000
SND_FILENAME = 0x00020000
SND_RESOURCE = 0x00040004
SND_PURGE = 0x0040
SND_APPLICATION = 0x0080
SND_ALIAS_START = 0
WAVERR_BADFORMAT = WAVERR_BASE + 0
WAVERR_STILLPLAYING = WAVERR_BASE + 1
WAVERR_UNPREPARED = WAVERR_BASE + 2
WAVERR_SYNC = WAVERR_BASE + 3
WAVERR_LASTERROR = WAVERR_BASE + 3
WOM_OPEN = MM_WOM_OPEN
WOM_CLOSE = MM_WOM_CLOSE
WOM_DONE = MM_WOM_DONE
WIM_OPEN = MM_WIM_OPEN
WIM_CLOSE = MM_WIM_CLOSE
WIM_DATA = MM_WIM_DATA
WAVE_MAPPER = -1  # 0xFFFFFFFF
WAVE_FORMAT_QUERY = 0x0001
WAVE_ALLOWSYNC = 0x0002
WAVE_MAPPED = 0x0004
WAVE_FORMAT_DIRECT = 0x0008
WAVE_FORMAT_DIRECT_QUERY = WAVE_FORMAT_QUERY | WAVE_FORMAT_DIRECT
WHDR_DONE = 0x00000001
WHDR_PREPARED = 0x00000002
WHDR_BEGINLOOP = 0x00000004
WHDR_ENDLOOP = 0x00000008
WHDR_INQUEUE = 0x00000010
WAVECAPS_PITCH = 0x0001
WAVECAPS_PLAYBACKRATE = 0x0002
WAVECAPS_VOLUME = 0x0004
WAVECAPS_LRVOLUME = 0x0008
WAVECAPS_SYNC = 0x0010
WAVECAPS_SAMPLEACCURATE = 0x0020
WAVECAPS_DIRECTSOUND = 0x0040
WAVE_INVALIDFORMAT = 0x00000000
WAVE_FORMAT_1M08 = 0x00000001
WAVE_FORMAT_1S08 = 0x00000002
WAVE_FORMAT_1M16 = 0x00000004
WAVE_FORMAT_1S16 = 0x00000008
WAVE_FORMAT_2M08 = 0x00000010
WAVE_FORMAT_2S08 = 0x00000020
WAVE_FORMAT_2M16 = 0x00000040
WAVE_FORMAT_2S16 = 0x00000080
WAVE_FORMAT_4M08 = 0x00000100
WAVE_FORMAT_4S08 = 0x00000200
WAVE_FORMAT_4M16 = 0x00000400
WAVE_FORMAT_4S16 = 0x00000800
WAVE_FORMAT_PCM = 1
WAVE_FORMAT_IEEE_FLOAT = 3
MIDIERR_UNPREPARED = MIDIERR_BASE + 0
MIDIERR_STILLPLAYING = MIDIERR_BASE + 1
MIDIERR_NOMAP = MIDIERR_BASE + 2
MIDIERR_NOTREADY = MIDIERR_BASE + 3
MIDIERR_NODEVICE = MIDIERR_BASE + 4
MIDIERR_INVALIDSETUP = MIDIERR_BASE + 5
MIDIERR_BADOPENMODE = MIDIERR_BASE + 6
MIDIERR_DONT_CONTINUE = MIDIERR_BASE + 7
MIDIERR_LASTERROR = MIDIERR_BASE + 7
MIDIPATCHSIZE = 128
MIM_OPEN = MM_MIM_OPEN
MIM_CLOSE = MM_MIM_CLOSE
MIM_DATA = MM_MIM_DATA
MIM_LONGDATA = MM_MIM_LONGDATA
MIM_ERROR = MM_MIM_ERROR
MIM_LONGERROR = MM_MIM_LONGERROR
MOM_OPEN = MM_MOM_OPEN
MOM_CLOSE = MM_MOM_CLOSE
MOM_DONE = MM_MOM_DONE
MIM_MOREDATA = MM_MIM_MOREDATA
MOM_POSITIONCB = MM_MOM_POSITIONCB
MIDI_IO_STATUS = 0x00000020
MIDI_CACHE_ALL = 1
MIDI_CACHE_BESTFIT = 2
MIDI_CACHE_QUERY = 3
MIDI_UNCACHE = 4
MOD_MIDIPORT = 1
MOD_SYNTH = 2
MOD_SQSYNTH = 3
MOD_FMSYNTH = 4
MOD_MAPPER = 5
MIDICAPS_VOLUME = 0x0001
MIDICAPS_LRVOLUME = 0x0002
MIDICAPS_CACHE = 0x0004
MIDICAPS_STREAM = 0x0008
MHDR_DONE = 0x00000001
MHDR_PREPARED = 0x00000002
MHDR_INQUEUE = 0x00000004
MHDR_ISSTRM = 0x00000008
MEVT_F_SHORT = 0x00000000
MEVT_F_LONG = -2147483648  # 0x80000000
MEVT_F_CALLBACK = 0x40000000


def MEVT_EVENTTYPE(x):
    return (x >> 24) & 0xFF


def MEVT_EVENTPARM(x):
    return x & 0x00FFFFFF


MIDISTRM_ERROR = -2
MIDIPROP_SET = -2147483648  # 0x80000000
MIDIPROP_GET = 0x40000000
MIDIPROP_TIMEDIV = 0x00000001
MIDIPROP_TEMPO = 0x00000002
AUXCAPS_CDAUDIO = 1
AUXCAPS_AUXIN = 2
AUXCAPS_VOLUME = 0x0001
AUXCAPS_LRVOLUME = 0x0002
MIXER_SHORT_NAME_CHARS = 16
MIXER_LONG_NAME_CHARS = 64
MIXERR_INVALLINE = MIXERR_BASE + 0
MIXERR_INVALCONTROL = MIXERR_BASE + 1
MIXERR_INVALVALUE = MIXERR_BASE + 2
MIXERR_LASTERROR = MIXERR_BASE + 2
MIXER_OBJECTF_HANDLE = -2147483648  # 0x80000000
MIXER_OBJECTF_MIXER = 0x00000000
MIXER_OBJECTF_HMIXER = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_MIXER
MIXER_OBJECTF_WAVEOUT = 0x10000000
MIXER_OBJECTF_HWAVEOUT = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_WAVEOUT
MIXER_OBJECTF_WAVEIN = 0x20000000
MIXER_OBJECTF_HWAVEIN = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_WAVEIN
MIXER_OBJECTF_MIDIOUT = 0x30000000
MIXER_OBJECTF_HMIDIOUT = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_MIDIOUT
MIXER_OBJECTF_MIDIIN = 0x40000000
MIXER_OBJECTF_HMIDIIN = MIXER_OBJECTF_HANDLE | MIXER_OBJECTF_MIDIIN
MIXER_OBJECTF_AUX = 0x50000000
MIXERLINE_LINEF_ACTIVE = 0x00000001
MIXERLINE_LINEF_DISCONNECTED = 0x00008000
MIXERLINE_LINEF_SOURCE = -2147483648  # 0x80000000
MIXERLINE_COMPONENTTYPE_DST_FIRST = 0x00000000
MIXERLINE_COMPONENTTYPE_DST_UNDEFINED = MIXERLINE_COMPONENTTYPE_DST_FIRST + 0
MIXERLINE_COMPONENTTYPE_DST_DIGITAL = MIXERLINE_COMPONENTTYPE_DST_FIRST + 1
MIXERLINE_COMPONENTTYPE_DST_LINE = MIXERLINE_COMPONENTTYPE_DST_FIRST + 2
MIXERLINE_COMPONENTTYPE_DST_MONITOR = MIXERLINE_COMPONENTTYPE_DST_FIRST + 3
MIXERLINE_COMPONENTTYPE_DST_SPEAKERS = MIXERLINE_COMPONENTTYPE_DST_FIRST + 4
MIXERLINE_COMPONENTTYPE_DST_HEADPHONES = MIXERLINE_COMPONENTTYPE_DST_FIRST + 5
MIXERLINE_COMPONENTTYPE_DST_TELEPHONE = MIXERLINE_COMPONENTTYPE_DST_FIRST + 6
MIXERLINE_COMPONENTTYPE_DST_WAVEIN = MIXERLINE_COMPONENTTYPE_DST_FIRST + 7
MIXERLINE_COMPONENTTYPE_DST_VOICEIN = MIXERLINE_COMPONENTTYPE_DST_FIRST + 8
MIXERLINE_COMPONENTTYPE_DST_LAST = MIXERLINE_COMPONENTTYPE_DST_FIRST + 8
MIXERLINE_COMPONENTTYPE_SRC_FIRST = 0x00001000
MIXERLINE_COMPONENTTYPE_SRC_UNDEFINED = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 0
MIXERLINE_COMPONENTTYPE_SRC_DIGITAL = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 1
MIXERLINE_COMPONENTTYPE_SRC_LINE = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 2
MIXERLINE_COMPONENTTYPE_SRC_MICROPHONE = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 3
MIXERLINE_COMPONENTTYPE_SRC_SYNTHESIZER = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 4
MIXERLINE_COMPONENTTYPE_SRC_COMPACTDISC = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 5
MIXERLINE_COMPONENTTYPE_SRC_TELEPHONE = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 6
MIXERLINE_COMPONENTTYPE_SRC_PCSPEAKER = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 7
MIXERLINE_COMPONENTTYPE_SRC_WAVEOUT = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 8
MIXERLINE_COMPONENTTYPE_SRC_AUXILIARY = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 9
MIXERLINE_COMPONENTTYPE_SRC_ANALOG = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 10
MIXERLINE_COMPONENTTYPE_SRC_LAST = MIXERLINE_COMPONENTTYPE_SRC_FIRST + 10
MIXERLINE_TARGETTYPE_UNDEFINED = 0
MIXERLINE_TARGETTYPE_WAVEOUT = 1
MIXERLINE_TARGETTYPE_WAVEIN = 2
MIXERLINE_TARGETTYPE_MIDIOUT = 3
MIXERLINE_TARGETTYPE_MIDIIN = 4
MIXERLINE_TARGETTYPE_AUX = 5
MIXER_GETLINEINFOF_DESTINATION = 0x00000000
MIXER_GETLINEINFOF_SOURCE = 0x00000001
MIXER_GETLINEINFOF_LINEID = 0x00000002
MIXER_GETLINEINFOF_COMPONENTTYPE = 0x00000003
MIXER_GETLINEINFOF_TARGETTYPE = 0x00000004
MIXER_GETLINEINFOF_QUERYMASK = 0x0000000F
MIXERCONTROL_CONTROLF_UNIFORM = 0x00000001
MIXERCONTROL_CONTROLF_MULTIPLE = 0x00000002
MIXERCONTROL_CONTROLF_DISABLED = -2147483648  # 0x80000000
MIXERCONTROL_CT_CLASS_MASK = -268435456  # 0xF0000000
MIXERCONTROL_CT_CLASS_CUSTOM = 0x00000000
MIXERCONTROL_CT_CLASS_METER = 0x10000000
MIXERCONTROL_CT_CLASS_SWITCH = 0x20000000
MIXERCONTROL_CT_CLASS_NUMBER = 0x30000000
MIXERCONTROL_CT_CLASS_SLIDER = 0x40000000
MIXERCONTROL_CT_CLASS_FADER = 0x50000000
MIXERCONTROL_CT_CLASS_TIME = 0x60000000
MIXERCONTROL_CT_CLASS_LIST = 0x70000000
MIXERCONTROL_CT_SUBCLASS_MASK = 0x0F000000
MIXERCONTROL_CT_SC_SWITCH_BOOLEAN = 0x00000000
MIXERCONTROL_CT_SC_SWITCH_BUTTON = 0x01000000
MIXERCONTROL_CT_SC_METER_POLLED = 0x00000000
MIXERCONTROL_CT_SC_TIME_MICROSECS = 0x00000000
MIXERCONTROL_CT_SC_TIME_MILLISECS = 0x01000000
MIXERCONTROL_CT_SC_LIST_SINGLE = 0x00000000
MIXERCONTROL_CT_SC_LIST_MULTIPLE = 0x01000000
MIXERCONTROL_CT_UNITS_MASK = 0x00FF0000
MIXERCONTROL_CT_UNITS_CUSTOM = 0x00000000
MIXERCONTROL_CT_UNITS_BOOLEAN = 0x00010000
MIXERCONTROL_CT_UNITS_SIGNED = 0x00020000
MIXERCONTROL_CT_UNITS_UNSIGNED = 0x00030000
MIXERCONTROL_CT_UNITS_DECIBELS = 0x00040000
MIXERCONTROL_CT_UNITS_PERCENT = 0x00050000
MIXERCONTROL_CONTROLTYPE_CUSTOM = (
    MIXERCONTROL_CT_CLASS_CUSTOM | MIXERCONTROL_CT_UNITS_CUSTOM
)
MIXERCONTROL_CONTROLTYPE_BOOLEANMETER = (
    MIXERCONTROL_CT_CLASS_METER
    | MIXERCONTROL_CT_SC_METER_POLLED
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_SIGNEDMETER = (
    MIXERCONTROL_CT_CLASS_METER
    | MIXERCONTROL_CT_SC_METER_POLLED
    | MIXERCONTROL_CT_UNITS_SIGNED
)
MIXERCONTROL_CONTROLTYPE_PEAKMETER = MIXERCONTROL_CONTROLTYPE_SIGNEDMETER + 1
MIXERCONTROL_CONTROLTYPE_UNSIGNEDMETER = (
    MIXERCONTROL_CT_CLASS_METER
    | MIXERCONTROL_CT_SC_METER_POLLED
    | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_BOOLEAN = (
    MIXERCONTROL_CT_CLASS_SWITCH
    | MIXERCONTROL_CT_SC_SWITCH_BOOLEAN
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_ONOFF = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 1
MIXERCONTROL_CONTROLTYPE_MUTE = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 2
MIXERCONTROL_CONTROLTYPE_MONO = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 3
MIXERCONTROL_CONTROLTYPE_LOUDNESS = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 4
MIXERCONTROL_CONTROLTYPE_STEREOENH = MIXERCONTROL_CONTROLTYPE_BOOLEAN + 5
MIXERCONTROL_CONTROLTYPE_BUTTON = (
    MIXERCONTROL_CT_CLASS_SWITCH
    | MIXERCONTROL_CT_SC_SWITCH_BUTTON
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_DECIBELS = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_DECIBELS
)
MIXERCONTROL_CONTROLTYPE_SIGNED = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_SIGNED
)
MIXERCONTROL_CONTROLTYPE_UNSIGNED = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_PERCENT = (
    MIXERCONTROL_CT_CLASS_NUMBER | MIXERCONTROL_CT_UNITS_PERCENT
)
MIXERCONTROL_CONTROLTYPE_SLIDER = (
    MIXERCONTROL_CT_CLASS_SLIDER | MIXERCONTROL_CT_UNITS_SIGNED
)
MIXERCONTROL_CONTROLTYPE_PAN = MIXERCONTROL_CONTROLTYPE_SLIDER + 1
MIXERCONTROL_CONTROLTYPE_QSOUNDPAN = MIXERCONTROL_CONTROLTYPE_SLIDER + 2
MIXERCONTROL_CONTROLTYPE_FADER = (
    MIXERCONTROL_CT_CLASS_FADER | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_VOLUME = MIXERCONTROL_CONTROLTYPE_FADER + 1
MIXERCONTROL_CONTROLTYPE_BASS = MIXERCONTROL_CONTROLTYPE_FADER + 2
MIXERCONTROL_CONTROLTYPE_TREBLE = MIXERCONTROL_CONTROLTYPE_FADER + 3
MIXERCONTROL_CONTROLTYPE_EQUALIZER = MIXERCONTROL_CONTROLTYPE_FADER + 4
MIXERCONTROL_CONTROLTYPE_SINGLESELECT = (
    MIXERCONTROL_CT_CLASS_LIST
    | MIXERCONTROL_CT_SC_LIST_SINGLE
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_MUX = MIXERCONTROL_CONTROLTYPE_SINGLESELECT + 1
MIXERCONTROL_CONTROLTYPE_MULTIPLESELECT = (
    MIXERCONTROL_CT_CLASS_LIST
    | MIXERCONTROL_CT_SC_LIST_MULTIPLE
    | MIXERCONTROL_CT_UNITS_BOOLEAN
)
MIXERCONTROL_CONTROLTYPE_MIXER = MIXERCONTROL_CONTROLTYPE_MULTIPLESELECT + 1
MIXERCONTROL_CONTROLTYPE_MICROTIME = (
    MIXERCONTROL_CT_CLASS_TIME
    | MIXERCONTROL_CT_SC_TIME_MICROSECS
    | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXERCONTROL_CONTROLTYPE_MILLITIME = (
    MIXERCONTROL_CT_CLASS_TIME
    | MIXERCONTROL_CT_SC_TIME_MILLISECS
    | MIXERCONTROL_CT_UNITS_UNSIGNED
)
MIXER_GETLINECONTROLSF_ALL = 0x00000000
MIXER_GETLINECONTROLSF_ONEBYID = 0x00000001
MIXER_GETLINECONTROLSF_ONEBYTYPE = 0x00000002
MIXER_GETLINECONTROLSF_QUERYMASK = 0x0000000F
MIXER_GETCONTROLDETAILSF_VALUE = 0x00000000
MIXER_GETCONTROLDETAILSF_LISTTEXT = 0x00000001
MIXER_GETCONTROLDETAILSF_QUERYMASK = 0x0000000F
MIXER_SETCONTROLDETAILSF_VALUE = 0x00000000
MIXER_SETCONTROLDETAILSF_CUSTOM = 0x00000001
MIXER_SETCONTROLDETAILSF_QUERYMASK = 0x0000000F
TIMERR_NOERROR = 0
TIMERR_NOCANDO = TIMERR_BASE + 1
TIMERR_STRUCT = TIMERR_BASE + 33
TIME_ONESHOT = 0x0000
TIME_PERIODIC = 0x0001
TIME_CALLBACK_FUNCTION = 0x0000
TIME_CALLBACK_EVENT_SET = 0x0010
TIME_CALLBACK_EVENT_PULSE = 0x0020
JOYERR_NOERROR = 0
JOYERR_PARMS = JOYERR_BASE + 5
JOYERR_NOCANDO = JOYERR_BASE + 6
JOYERR_UNPLUGGED = JOYERR_BASE + 7
JOY_BUTTON1 = 0x0001
JOY_BUTTON2 = 0x0002
JOY_BUTTON3 = 0x0004
JOY_BUTTON4 = 0x0008
JOY_BUTTON1CHG = 0x0100
JOY_BUTTON2CHG = 0x0200
JOY_BUTTON3CHG = 0x0400
JOY_BUTTON4CHG = 0x0800
JOY_BUTTON5 = 0x00000010
JOY_BUTTON6 = 0x00000020
JOY_BUTTON7 = 0x00000040
JOY_BUTTON8 = 0x00000080
JOY_BUTTON9 = 0x00000100
JOY_BUTTON10 = 0x00000200
JOY_BUTTON11 = 0x00000400
JOY_BUTTON12 = 0x00000800
JOY_BUTTON13 = 0x00001000
JOY_BUTTON14 = 0x00002000
JOY_BUTTON15 = 0x00004000
JOY_BUTTON16 = 0x00008000
JOY_BUTTON17 = 0x00010000
JOY_BUTTON18 = 0x00020000
JOY_BUTTON19 = 0x00040000
JOY_BUTTON20 = 0x00080000
JOY_BUTTON21 = 0x00100000
JOY_BUTTON22 = 0x00200000
JOY_BUTTON23 = 0x00400000
JOY_BUTTON24 = 0x00800000
JOY_BUTTON25 = 0x01000000
JOY_BUTTON26 = 0x02000000
JOY_BUTTON27 = 0x04000000
JOY_BUTTON28 = 0x08000000
JOY_BUTTON29 = 0x10000000
JOY_BUTTON30 = 0x20000000
JOY_BUTTON31 = 0x40000000
JOY_BUTTON32 = -2147483648  # 0x80000000
JOY_POVFORWARD = 0
JOY_POVRIGHT = 9000
JOY_POVBACKWARD = 18000
JOY_POVLEFT = 27000
JOY_RETURNX = 0x00000001
JOY_RETURNY = 0x00000002
JOY_RETURNZ = 0x00000004
JOY_RETURNR = 0x00000008
JOY_RETURNU = 0x00000010
JOY_RETURNV = 0x00000020
JOY_RETURNPOV = 0x00000040
JOY_RETURNBUTTONS = 0x00000080
JOY_RETURNRAWDATA = 0x00000100
JOY_RETURNPOVCTS = 0x00000200
JOY_RETURNCENTERED = 0x00000400
JOY_USEDEADZONE = 0x00000800
JOY_RETURNALL = (
    JOY_RETURNX
    | JOY_RETURNY
    | JOY_RETURNZ
    | JOY_RETURNR
    | JOY_RETURNU
    | JOY_RETURNV
    | JOY_RETURNPOV
    | JOY_RETURNBUTTONS
)
JOY_CAL_READALWAYS = 0x00010000
JOY_CAL_READXYONLY = 0x00020000
JOY_CAL_READ3 = 0x00040000
JOY_CAL_READ4 = 0x00080000
JOY_CAL_READXONLY = 0x00100000
JOY_CAL_READYONLY = 0x00200000
JOY_CAL_READ5 = 0x00400000
JOY_CAL_READ6 = 0x00800000
JOY_CAL_READZONLY = 0x01000000
JOY_CAL_READRONLY = 0x02000000
JOY_CAL_READUONLY = 0x04000000
JOY_CAL_READVONLY = 0x08000000
JOYSTICKID1 = 0
JOYSTICKID2 = 1
JOYCAPS_HASZ = 0x0001
JOYCAPS_HASR = 0x0002
JOYCAPS_HASU = 0x0004
JOYCAPS_HASV = 0x0008
JOYCAPS_HASPOV = 0x0010
JOYCAPS_POV4DIR = 0x0020
JOYCAPS_POVCTS = 0x0040
MMIOERR_BASE = 256
MMIOERR_FILENOTFOUND = MMIOERR_BASE + 1
MMIOERR_OUTOFMEMORY = MMIOERR_BASE + 2
MMIOERR_CANNOTOPEN = MMIOERR_BASE + 3
MMIOERR_CANNOTCLOSE = MMIOERR_BASE + 4
MMIOERR_CANNOTREAD = MMIOERR_BASE + 5
MMIOERR_CANNOTWRITE = MMIOERR_BASE + 6
MMIOERR_CANNOTSEEK = MMIOERR_BASE + 7
MMIOERR_CANNOTEXPAND = MMIOERR_BASE + 8
MMIOERR_CHUNKNOTFOUND = MMIOERR_BASE + 9
MMIOERR_UNBUFFERED = MMIOERR_BASE + 10
MMIOERR_PATHNOTFOUND = MMIOERR_BASE + 11
MMIOERR_ACCESSDENIED = MMIOERR_BASE + 12
MMIOERR_SHARINGVIOLATION = MMIOERR_BASE + 13
MMIOERR_NETWORKERROR = MMIOERR_BASE + 14
MMIOERR_TOOMANYOPENFILES = MMIOERR_BASE + 15
MMIOERR_INVALIDFILE = MMIOERR_BASE + 16
CFSEPCHAR = ord("+")
MMIO_RWMODE = 0x00000003
MMIO_SHAREMODE = 0x00000070
MMIO_CREATE = 0x00001000
MMIO_PARSE = 0x00000100
MMIO_DELETE = 0x00000200
MMIO_EXIST = 0x00004000
MMIO_ALLOCBUF = 0x00010000
MMIO_GETTEMP = 0x00020000
MMIO_DIRTY = 0x10000000
MMIO_READ = 0x00000000
MMIO_WRITE = 0x00000001
MMIO_READWRITE = 0x00000002
MMIO_COMPAT = 0x00000000
MMIO_EXCLUSIVE = 0x00000010
MMIO_DENYWRITE = 0x00000020
MMIO_DENYREAD = 0x00000030
MMIO_DENYNONE = 0x00000040
MMIO_FHOPEN = 0x0010
MMIO_EMPTYBUF = 0x0010
MMIO_TOUPPER = 0x0010
MMIO_INSTALLPROC = 0x00010000
MMIO_GLOBALPROC = 0x10000000
MMIO_REMOVEPROC = 0x00020000
MMIO_UNICODEPROC = 0x01000000
MMIO_FINDPROC = 0x00040000
MMIO_FINDCHUNK = 0x0010
MMIO_FINDRIFF = 0x0020
MMIO_FINDLIST = 0x0040
MMIO_CREATERIFF = 0x0020
MMIO_CREATELIST = 0x0040
MMIOM_READ = MMIO_READ
MMIOM_WRITE = MMIO_WRITE
MMIOM_SEEK = 2
MMIOM_OPEN = 3
MMIOM_CLOSE = 4
MMIOM_WRITEFLUSH = 5
MMIOM_RENAME = 6
MMIOM_USER = 0x8000
SEEK_SET = 0
SEEK_CUR = 1
SEEK_END = 2
MMIO_DEFAULTBUFFER = 8192
MCIERR_INVALID_DEVICE_ID = MCIERR_BASE + 1
MCIERR_UNRECOGNIZED_KEYWORD = MCIERR_BASE + 3
MCIERR_UNRECOGNIZED_COMMAND = MCIERR_BASE + 5
MCIERR_HARDWARE = MCIERR_BASE + 6
MCIERR_INVALID_DEVICE_NAME = MCIERR_BASE + 7
MCIERR_OUT_OF_MEMORY = MCIERR_BASE + 8
MCIERR_DEVICE_OPEN = MCIERR_BASE + 9
MCIERR_CANNOT_LOAD_DRIVER = MCIERR_BASE + 10
MCIERR_MISSING_COMMAND_STRING = MCIERR_BASE + 11
MCIERR_PARAM_OVERFLOW = MCIERR_BASE + 12
MCIERR_MISSING_STRING_ARGUMENT = MCIERR_BASE + 13
MCIERR_BAD_INTEGER = MCIERR_BASE + 14
MCIERR_PARSER_INTERNAL = MCIERR_BASE + 15
MCIERR_DRIVER_INTERNAL = MCIERR_BASE + 16
MCIERR_MISSING_PARAMETER = MCIERR_BASE + 17
MCIERR_UNSUPPORTED_FUNCTION = MCIERR_BASE + 18
MCIERR_FILE_NOT_FOUND = MCIERR_BASE + 19
MCIERR_DEVICE_NOT_READY = MCIERR_BASE + 20
MCIERR_INTERNAL = MCIERR_BASE + 21
MCIERR_DRIVER = MCIERR_BASE + 22
MCIERR_CANNOT_USE_ALL = MCIERR_BASE + 23
MCIERR_MULTIPLE = MCIERR_BASE + 24
MCIERR_EXTENSION_NOT_FOUND = MCIERR_BASE + 25
MCIERR_OUTOFRANGE = MCIERR_BASE + 26
MCIERR_FLAGS_NOT_COMPATIBLE = MCIERR_BASE + 28
MCIERR_FILE_NOT_SAVED = MCIERR_BASE + 30
MCIERR_DEVICE_TYPE_REQUIRED = MCIERR_BASE + 31
MCIERR_DEVICE_LOCKED = MCIERR_BASE + 32
MCIERR_DUPLICATE_ALIAS = MCIERR_BASE + 33
MCIERR_BAD_CONSTANT = MCIERR_BASE + 34
MCIERR_MUST_USE_SHAREABLE = MCIERR_BASE + 35
MCIERR_MISSING_DEVICE_NAME = MCIERR_BASE + 36
MCIERR_BAD_TIME_FORMAT = MCIERR_BASE + 37
MCIERR_NO_CLOSING_QUOTE = MCIERR_BASE + 38
MCIERR_DUPLICATE_FLAGS = MCIERR_BASE + 39
MCIERR_INVALID_FILE = MCIERR_BASE + 40
MCIERR_NULL_PARAMETER_BLOCK = MCIERR_BASE + 41
MCIERR_UNNAMED_RESOURCE = MCIERR_BASE + 42
MCIERR_NEW_REQUIRES_ALIAS = MCIERR_BASE + 43
MCIERR_NOTIFY_ON_AUTO_OPEN = MCIERR_BASE + 44
MCIERR_NO_ELEMENT_ALLOWED = MCIERR_BASE + 45
MCIERR_NONAPPLICABLE_FUNCTION = MCIERR_BASE + 46
MCIERR_ILLEGAL_FOR_AUTO_OPEN = MCIERR_BASE + 47
MCIERR_FILENAME_REQUIRED = MCIERR_BASE + 48
MCIERR_EXTRA_CHARACTERS = MCIERR_BASE + 49
MCIERR_DEVICE_NOT_INSTALLED = MCIERR_BASE + 50
MCIERR_GET_CD = MCIERR_BASE + 51
MCIERR_SET_CD = MCIERR_BASE + 52
MCIERR_SET_DRIVE = MCIERR_BASE + 53
MCIERR_DEVICE_LENGTH = MCIERR_BASE + 54
MCIERR_DEVICE_ORD_LENGTH = MCIERR_BASE + 55
MCIERR_NO_INTEGER = MCIERR_BASE + 56
MCIERR_WAVE_OUTPUTSINUSE = MCIERR_BASE + 64
MCIERR_WAVE_SETOUTPUTINUSE = MCIERR_BASE + 65
MCIERR_WAVE_INPUTSINUSE = MCIERR_BASE + 66
MCIERR_WAVE_SETINPUTINUSE = MCIERR_BASE + 67
MCIERR_WAVE_OUTPUTUNSPECIFIED = MCIERR_BASE + 68
MCIERR_WAVE_INPUTUNSPECIFIED = MCIERR_BASE + 69
MCIERR_WAVE_OUTPUTSUNSUITABLE = MCIERR_BASE + 70
MCIERR_WAVE_SETOUTPUTUNSUITABLE = MCIERR_BASE + 71
MCIERR_WAVE_INPUTSUNSUITABLE = MCIERR_BASE + 72
MCIERR_WAVE_SETINPUTUNSUITABLE = MCIERR_BASE + 73
MCIERR_SEQ_DIV_INCOMPATIBLE = MCIERR_BASE + 80
MCIERR_SEQ_PORT_INUSE = MCIERR_BASE + 81
MCIERR_SEQ_PORT_NONEXISTENT = MCIERR_BASE + 82
MCIERR_SEQ_PORT_MAPNODEVICE = MCIERR_BASE + 83
MCIERR_SEQ_PORT_MISCERROR = MCIERR_BASE + 84
MCIERR_SEQ_TIMER = MCIERR_BASE + 85
MCIERR_SEQ_PORTUNSPECIFIED = MCIERR_BASE + 86
MCIERR_SEQ_NOMIDIPRESENT = MCIERR_BASE + 87
MCIERR_NO_WINDOW = MCIERR_BASE + 90
MCIERR_CREATEWINDOW = MCIERR_BASE + 91
MCIERR_FILE_READ = MCIERR_BASE + 92
MCIERR_FILE_WRITE = MCIERR_BASE + 93
MCIERR_NO_IDENTITY = MCIERR_BASE + 94
MCIERR_CUSTOM_DRIVER_BASE = MCIERR_BASE + 256
MCI_FIRST = DRV_MCI_FIRST
MCI_OPEN = 0x0803
MCI_CLOSE = 0x0804
MCI_ESCAPE = 0x0805
MCI_PLAY = 0x0806
MCI_SEEK = 0x0807
MCI_STOP = 0x0808
MCI_PAUSE = 0x0809
MCI_INFO = 0x080A
MCI_GETDEVCAPS = 0x080B
MCI_SPIN = 0x080C
MCI_SET = 0x080D
MCI_STEP = 0x080E
MCI_RECORD = 0x080F
MCI_SYSINFO = 0x0810
MCI_BREAK = 0x0811
MCI_SAVE = 0x0813
MCI_STATUS = 0x0814
MCI_CUE = 0x0830
MCI_REALIZE = 0x0840
MCI_WINDOW = 0x0841
MCI_PUT = 0x0842
MCI_WHERE = 0x0843
MCI_FREEZE = 0x0844
MCI_UNFREEZE = 0x0845
MCI_LOAD = 0x0850
MCI_CUT = 0x0851
MCI_COPY = 0x0852
MCI_PASTE = 0x0853
MCI_UPDATE = 0x0854
MCI_RESUME = 0x0855
MCI_DELETE = 0x0856
MCI_USER_MESSAGES = DRV_MCI_FIRST + 0x400
MCI_LAST = 0x0FFF
MCI_DEVTYPE_VCR = 513
MCI_DEVTYPE_VIDEODISC = 514
MCI_DEVTYPE_OVERLAY = 515
MCI_DEVTYPE_CD_AUDIO = 516
MCI_DEVTYPE_DAT = 517
MCI_DEVTYPE_SCANNER = 518
MCI_DEVTYPE_ANIMATION = 519
MCI_DEVTYPE_DIGITAL_VIDEO = 520
MCI_DEVTYPE_OTHER = 521
MCI_DEVTYPE_WAVEFORM_AUDIO = 522
MCI_DEVTYPE_SEQUENCER = 523
MCI_DEVTYPE_FIRST = MCI_DEVTYPE_VCR
MCI_DEVTYPE_LAST = MCI_DEVTYPE_SEQUENCER
MCI_DEVTYPE_FIRST_USER = 0x1000
MCI_MODE_NOT_READY = MCI_STRING_OFFSET + 12
MCI_MODE_STOP = MCI_STRING_OFFSET + 13
MCI_MODE_PLAY = MCI_STRING_OFFSET + 14
MCI_MODE_RECORD = MCI_STRING_OFFSET + 15
MCI_MODE_SEEK = MCI_STRING_OFFSET + 16
MCI_MODE_PAUSE = MCI_STRING_OFFSET + 17
MCI_MODE_OPEN = MCI_STRING_OFFSET + 18
MCI_FORMAT_MILLISECONDS = 0
MCI_FORMAT_HMS = 1
MCI_FORMAT_MSF = 2
MCI_FORMAT_FRAMES = 3
MCI_FORMAT_SMPTE_24 = 4
MCI_FORMAT_SMPTE_25 = 5
MCI_FORMAT_SMPTE_30 = 6
MCI_FORMAT_SMPTE_30DROP = 7
MCI_FORMAT_BYTES = 8
MCI_FORMAT_SAMPLES = 9
MCI_FORMAT_TMSF = 10


def MCI_MSF_MINUTE(msf):
    return msf


def MCI_MSF_SECOND(msf):
    return msf >> 8


def MCI_MSF_FRAME(msf):
    return msf >> 16


def MCI_TMSF_TRACK(tmsf):
    return tmsf


def MCI_TMSF_MINUTE(tmsf):
    return tmsf >> 8


def MCI_TMSF_SECOND(tmsf):
    return tmsf >> 16


def MCI_TMSF_FRAME(tmsf):
    return tmsf >> 24


def MCI_HMS_HOUR(hms):
    return hms


def MCI_HMS_MINUTE(hms):
    return hms >> 8


def MCI_HMS_SECOND(hms):
    return hms >> 16


MCI_NOTIFY_SUCCESSFUL = 0x0001
MCI_NOTIFY_SUPERSEDED = 0x0002
MCI_NOTIFY_ABORTED = 0x0004
MCI_NOTIFY_FAILURE = 0x0008
MCI_NOTIFY = 0x00000001
MCI_WAIT = 0x00000002
MCI_FROM = 0x00000004
MCI_TO = 0x00000008
MCI_TRACK = 0x00000010
MCI_OPEN_SHAREABLE = 0x00000100
MCI_OPEN_ELEMENT = 0x00000200
MCI_OPEN_ALIAS = 0x00000400
MCI_OPEN_ELEMENT_ID = 0x00000800
MCI_OPEN_TYPE_ID = 0x00001000
MCI_OPEN_TYPE = 0x00002000
MCI_SEEK_TO_START = 0x00000100
MCI_SEEK_TO_END = 0x00000200
MCI_STATUS_ITEM = 0x00000100
MCI_STATUS_START = 0x00000200
MCI_STATUS_LENGTH = 0x00000001
MCI_STATUS_POSITION = 0x00000002
MCI_STATUS_NUMBER_OF_TRACKS = 0x00000003
MCI_STATUS_MODE = 0x00000004
MCI_STATUS_MEDIA_PRESENT = 0x00000005
MCI_STATUS_TIME_FORMAT = 0x00000006
MCI_STATUS_READY = 0x00000007
MCI_STATUS_CURRENT_TRACK = 0x00000008
MCI_INFO_PRODUCT = 0x00000100
MCI_INFO_FILE = 0x00000200
MCI_INFO_MEDIA_UPC = 0x00000400
MCI_INFO_MEDIA_IDENTITY = 0x00000800
MCI_INFO_NAME = 0x00001000
MCI_INFO_COPYRIGHT = 0x00002000
MCI_GETDEVCAPS_ITEM = 0x00000100
MCI_GETDEVCAPS_CAN_RECORD = 0x00000001
MCI_GETDEVCAPS_HAS_AUDIO = 0x00000002
MCI_GETDEVCAPS_HAS_VIDEO = 0x00000003
MCI_GETDEVCAPS_DEVICE_TYPE = 0x00000004
MCI_GETDEVCAPS_USES_FILES = 0x00000005
MCI_GETDEVCAPS_COMPOUND_DEVICE = 0x00000006
MCI_GETDEVCAPS_CAN_EJECT = 0x00000007
MCI_GETDEVCAPS_CAN_PLAY = 0x00000008
MCI_GETDEVCAPS_CAN_SAVE = 0x00000009
MCI_SYSINFO_QUANTITY = 0x00000100
MCI_SYSINFO_OPEN = 0x00000200
MCI_SYSINFO_NAME = 0x00000400
MCI_SYSINFO_INSTALLNAME = 0x00000800
MCI_SET_DOOR_OPEN = 0x00000100
MCI_SET_DOOR_CLOSED = 0x00000200
MCI_SET_TIME_FORMAT = 0x00000400
MCI_SET_AUDIO = 0x00000800
MCI_SET_VIDEO = 0x00001000
MCI_SET_ON = 0x00002000
MCI_SET_OFF = 0x00004000
MCI_SET_AUDIO_ALL = 0x00000000
MCI_SET_AUDIO_LEFT = 0x00000001
MCI_SET_AUDIO_RIGHT = 0x00000002
MCI_BREAK_KEY = 0x00000100
MCI_BREAK_HWND = 0x00000200
MCI_BREAK_OFF = 0x00000400
MCI_RECORD_INSERT = 0x00000100
MCI_RECORD_OVERWRITE = 0x00000200
MCI_SAVE_FILE = 0x00000100
MCI_LOAD_FILE = 0x00000100
MCI_VD_MODE_PARK = MCI_VD_OFFSET + 1
MCI_VD_MEDIA_CLV = MCI_VD_OFFSET + 2
MCI_VD_MEDIA_CAV = MCI_VD_OFFSET + 3
MCI_VD_MEDIA_OTHER = MCI_VD_OFFSET + 4
MCI_VD_FORMAT_TRACK = 0x4001
MCI_VD_PLAY_REVERSE = 0x00010000
MCI_VD_PLAY_FAST = 0x00020000
MCI_VD_PLAY_SPEED = 0x00040000
MCI_VD_PLAY_SCAN = 0x00080000
MCI_VD_PLAY_SLOW = 0x00100000
MCI_VD_SEEK_REVERSE = 0x00010000
MCI_VD_STATUS_SPEED = 0x00004002
MCI_VD_STATUS_FORWARD = 0x00004003
MCI_VD_STATUS_MEDIA_TYPE = 0x00004004
MCI_VD_STATUS_SIDE = 0x00004005
MCI_VD_STATUS_DISC_SIZE = 0x00004006
MCI_VD_GETDEVCAPS_CLV = 0x00010000
MCI_VD_GETDEVCAPS_CAV = 0x00020000
MCI_VD_SPIN_UP = 0x00010000
MCI_VD_SPIN_DOWN = 0x00020000
MCI_VD_GETDEVCAPS_CAN_REVERSE = 0x00004002
MCI_VD_GETDEVCAPS_FAST_RATE = 0x00004003
MCI_VD_GETDEVCAPS_SLOW_RATE = 0x00004004
MCI_VD_GETDEVCAPS_NORMAL_RATE = 0x00004005
MCI_VD_STEP_FRAMES = 0x00010000
MCI_VD_STEP_REVERSE = 0x00020000
MCI_VD_ESCAPE_STRING = 0x00000100
MCI_CDA_STATUS_TYPE_TRACK = 0x00004001
MCI_CDA_TRACK_AUDIO = MCI_CD_OFFSET + 0
MCI_CDA_TRACK_OTHER = MCI_CD_OFFSET + 1
MCI_WAVE_PCM = MCI_WAVE_OFFSET + 0
MCI_WAVE_MAPPER = MCI_WAVE_OFFSET + 1
MCI_WAVE_OPEN_BUFFER = 0x00010000
MCI_WAVE_SET_FORMATTAG = 0x00010000
MCI_WAVE_SET_CHANNELS = 0x00020000
MCI_WAVE_SET_SAMPLESPERSEC = 0x00040000
MCI_WAVE_SET_AVGBYTESPERSEC = 0x00080000
MCI_WAVE_SET_BLOCKALIGN = 0x00100000
MCI_WAVE_SET_BITSPERSAMPLE = 0x00200000
MCI_WAVE_INPUT = 0x00400000
MCI_WAVE_OUTPUT = 0x00800000
MCI_WAVE_STATUS_FORMATTAG = 0x00004001
MCI_WAVE_STATUS_CHANNELS = 0x00004002
MCI_WAVE_STATUS_SAMPLESPERSEC = 0x00004003
MCI_WAVE_STATUS_AVGBYTESPERSEC = 0x00004004
MCI_WAVE_STATUS_BLOCKALIGN = 0x00004005
MCI_WAVE_STATUS_BITSPERSAMPLE = 0x00004006
MCI_WAVE_STATUS_LEVEL = 0x00004007
MCI_WAVE_SET_ANYINPUT = 0x04000000
MCI_WAVE_SET_ANYOUTPUT = 0x08000000
MCI_WAVE_GETDEVCAPS_INPUTS = 0x00004001
MCI_WAVE_GETDEVCAPS_OUTPUTS = 0x00004002
MCI_SEQ_DIV_PPQN = 0 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_24 = 1 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_25 = 2 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_30DROP = 3 + MCI_SEQ_OFFSET
MCI_SEQ_DIV_SMPTE_30 = 4 + MCI_SEQ_OFFSET
MCI_SEQ_FORMAT_SONGPTR = 0x4001
MCI_SEQ_FILE = 0x4002
MCI_SEQ_MIDI = 0x4003
MCI_SEQ_SMPTE = 0x4004
MCI_SEQ_NONE = 65533
MCI_SEQ_MAPPER = 65535
MCI_SEQ_STATUS_TEMPO = 0x00004002
MCI_SEQ_STATUS_PORT = 0x00004003
MCI_SEQ_STATUS_SLAVE = 0x00004007
MCI_SEQ_STATUS_MASTER = 0x00004008
MCI_SEQ_STATUS_OFFSET = 0x00004009
MCI_SEQ_STATUS_DIVTYPE = 0x0000400A
MCI_SEQ_STATUS_NAME = 0x0000400B
MCI_SEQ_STATUS_COPYRIGHT = 0x0000400C
MCI_SEQ_SET_TEMPO = 0x00010000
MCI_SEQ_SET_PORT = 0x00020000
MCI_SEQ_SET_SLAVE = 0x00040000
MCI_SEQ_SET_MASTER = 0x00080000
MCI_SEQ_SET_OFFSET = 0x01000000
MCI_ANIM_OPEN_WS = 0x00010000
MCI_ANIM_OPEN_PARENT = 0x00020000
MCI_ANIM_OPEN_NOSTATIC = 0x00040000
MCI_ANIM_PLAY_SPEED = 0x00010000
MCI_ANIM_PLAY_REVERSE = 0x00020000
MCI_ANIM_PLAY_FAST = 0x00040000
MCI_ANIM_PLAY_SLOW = 0x00080000
MCI_ANIM_PLAY_SCAN = 0x00100000
MCI_ANIM_STEP_REVERSE = 0x00010000
MCI_ANIM_STEP_FRAMES = 0x00020000
MCI_ANIM_STATUS_SPEED = 0x00004001
MCI_ANIM_STATUS_FORWARD = 0x00004002
MCI_ANIM_STATUS_HWND = 0x00004003
MCI_ANIM_STATUS_HPAL = 0x00004004
MCI_ANIM_STATUS_STRETCH = 0x00004005
MCI_ANIM_INFO_TEXT = 0x00010000
MCI_ANIM_GETDEVCAPS_CAN_REVERSE = 0x00004001
MCI_ANIM_GETDEVCAPS_FAST_RATE = 0x00004002
MCI_ANIM_GETDEVCAPS_SLOW_RATE = 0x00004003
MCI_ANIM_GETDEVCAPS_NORMAL_RATE = 0x00004004
MCI_ANIM_GETDEVCAPS_PALETTES = 0x00004006
MCI_ANIM_GETDEVCAPS_CAN_STRETCH = 0x00004007
MCI_ANIM_GETDEVCAPS_MAX_WINDOWS = 0x00004008
MCI_ANIM_REALIZE_NORM = 0x00010000
MCI_ANIM_REALIZE_BKGD = 0x00020000
MCI_ANIM_WINDOW_HWND = 0x00010000
MCI_ANIM_WINDOW_STATE = 0x00040000
MCI_ANIM_WINDOW_TEXT = 0x00080000
MCI_ANIM_WINDOW_ENABLE_STRETCH = 0x00100000
MCI_ANIM_WINDOW_DISABLE_STRETCH = 0x00200000
MCI_ANIM_WINDOW_DEFAULT = 0x00000000
MCI_ANIM_RECT = 0x00010000
MCI_ANIM_PUT_SOURCE = 0x00020000
MCI_ANIM_PUT_DESTINATION = 0x00040000
MCI_ANIM_WHERE_SOURCE = 0x00020000
MCI_ANIM_WHERE_DESTINATION = 0x00040000
MCI_ANIM_UPDATE_HDC = 0x00020000
MCI_OVLY_OPEN_WS = 0x00010000
MCI_OVLY_OPEN_PARENT = 0x00020000
MCI_OVLY_STATUS_HWND = 0x00004001
MCI_OVLY_STATUS_STRETCH = 0x00004002
MCI_OVLY_INFO_TEXT = 0x00010000
MCI_OVLY_GETDEVCAPS_CAN_STRETCH = 0x00004001
MCI_OVLY_GETDEVCAPS_CAN_FREEZE = 0x00004002
MCI_OVLY_GETDEVCAPS_MAX_WINDOWS = 0x00004003
MCI_OVLY_WINDOW_HWND = 0x00010000
MCI_OVLY_WINDOW_STATE = 0x00040000
MCI_OVLY_WINDOW_TEXT = 0x00080000
MCI_OVLY_WINDOW_ENABLE_STRETCH = 0x00100000
MCI_OVLY_WINDOW_DISABLE_STRETCH = 0x00200000
MCI_OVLY_WINDOW_DEFAULT = 0x00000000
MCI_OVLY_RECT = 0x00010000
MCI_OVLY_PUT_SOURCE = 0x00020000
MCI_OVLY_PUT_DESTINATION = 0x00040000
MCI_OVLY_PUT_FRAME = 0x00080000
MCI_OVLY_PUT_VIDEO = 0x00100000
MCI_OVLY_WHERE_SOURCE = 0x00020000
MCI_OVLY_WHERE_DESTINATION = 0x00040000
MCI_OVLY_WHERE_FRAME = 0x00080000
MCI_OVLY_WHERE_VIDEO = 0x00100000
SELECTDIB = 41


def DIBINDEX(n):
    return win32api.MAKELONG(n, 0x10FF)

# === NexusCore/openenv\Lib\site-packages\IPython\lib\pretty.py ===
"""
Python advanced pretty printer.  This pretty printer is intended to
replace the old `pprint` python module which does not allow developers
to provide their own pretty print callbacks.

This module is based on ruby's `prettyprint.rb` library by `Tanaka Akira`.


Example Usage
-------------

To directly print the representation of an object use `pprint`::

    from pretty import pprint
    pprint(complex_object)

To get a string of the output use `pretty`::

    from pretty import pretty
    string = pretty(complex_object)


Extending
---------

The pretty library allows developers to add pretty printing rules for their
own objects.  This process is straightforward.  All you have to do is to
add a `_repr_pretty_` method to your object and call the methods on the
pretty printer passed::

    class MyObject(object):

        def _repr_pretty_(self, p, cycle):
            ...

Here's an example for a class with a simple constructor::

    class MySimpleObject:

        def __init__(self, a, b, *, c=None):
            self.a = a
            self.b = b
            self.c = c

        def _repr_pretty_(self, p, cycle):
            ctor = CallExpression.factory(self.__class__.__name__)
            if self.c is None:
                p.pretty(ctor(a, b))
            else:
                p.pretty(ctor(a, b, c=c))

Here is an example implementation of a `_repr_pretty_` method for a list
subclass::

    class MyList(list):

        def _repr_pretty_(self, p, cycle):
            if cycle:
                p.text('MyList(...)')
            else:
                with p.group(8, 'MyList([', '])'):
                    for idx, item in enumerate(self):
                        if idx:
                            p.text(',')
                            p.breakable()
                        p.pretty(item)

The `cycle` parameter is `True` if pretty detected a cycle.  You *have* to
react to that or the result is an infinite loop.  `p.text()` just adds
non breaking text to the output, `p.breakable()` either adds a whitespace
or breaks here.  If you pass it an argument it's used instead of the
default space.  `p.pretty` prettyprints another object using the pretty print
method.

The first parameter to the `group` function specifies the extra indentation
of the next line.  In this example the next item will either be on the same
line (if the items are short enough) or aligned with the right edge of the
opening bracket of `MyList`.

If you just want to indent something you can use the group function
without open / close parameters.  You can also use this code::

    with p.indent(2):
        ...

Inheritance diagram:

.. inheritance-diagram:: IPython.lib.pretty
   :parts: 3

:copyright: 2007 by Armin Ronacher.
            Portions (c) 2009 by Robert Kern.
:license: BSD License.
"""

from contextlib import contextmanager
import datetime
import os
import re
import sys
import types
from collections import deque
from inspect import signature
from io import StringIO
from warnings import warn

from IPython.utils.decorators import undoc
from IPython.utils.py3compat import PYPY

from typing import Dict

__all__ = ['pretty', 'pprint', 'PrettyPrinter', 'RepresentationPrinter',
    'for_type', 'for_type_by_name', 'RawText', 'RawStringLiteral', 'CallExpression']


MAX_SEQ_LENGTH = 1000
_re_pattern_type = type(re.compile(''))

def _safe_getattr(obj, attr, default=None):
    """Safe version of getattr.

    Same as getattr, but will return ``default`` on any Exception,
    rather than raising.
    """
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default

def _sorted_for_pprint(items):
    """
    Sort the given items for pretty printing. Since some predictable
    sorting is better than no sorting at all, we sort on the string
    representation if normal sorting fails.
    """
    items = list(items)
    try:
        return sorted(items)
    except Exception:
        try:
            return sorted(items, key=str)
        except Exception:
            return items

def pretty(obj, verbose=False, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
    """
    Pretty print the object's representation.
    """
    stream = StringIO()
    printer = RepresentationPrinter(stream, verbose, max_width, newline, max_seq_length=max_seq_length)
    printer.pretty(obj)
    printer.flush()
    return stream.getvalue()


def pprint(obj, verbose=False, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
    """
    Like `pretty` but print to stdout.
    """
    printer = RepresentationPrinter(sys.stdout, verbose, max_width, newline, max_seq_length=max_seq_length)
    printer.pretty(obj)
    printer.flush()
    sys.stdout.write(newline)
    sys.stdout.flush()

class _PrettyPrinterBase:

    @contextmanager
    def indent(self, indent):
        """with statement support for indenting/dedenting."""
        self.indentation += indent
        try:
            yield
        finally:
            self.indentation -= indent

    @contextmanager
    def group(self, indent=0, open='', close=''):
        """like begin_group / end_group but for the with statement."""
        self.begin_group(indent, open)
        try:
            yield
        finally:
            self.end_group(indent, close)

class PrettyPrinter(_PrettyPrinterBase):
    """
    Baseclass for the `RepresentationPrinter` prettyprinter that is used to
    generate pretty reprs of objects.  Contrary to the `RepresentationPrinter`
    this printer knows nothing about the default pprinters or the `_repr_pretty_`
    callback method.
    """

    def __init__(self, output, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
        self.output = output
        self.max_width = max_width
        self.newline = newline
        self.max_seq_length = max_seq_length
        self.output_width = 0
        self.buffer_width = 0
        self.buffer = deque()

        root_group = Group(0)
        self.group_stack = [root_group]
        self.group_queue = GroupQueue(root_group)
        self.indentation = 0

    def _break_one_group(self, group):
        while group.breakables:
            x = self.buffer.popleft()
            self.output_width = x.output(self.output, self.output_width)
            self.buffer_width -= x.width
        while self.buffer and isinstance(self.buffer[0], Text):
            x = self.buffer.popleft()
            self.output_width = x.output(self.output, self.output_width)
            self.buffer_width -= x.width

    def _break_outer_groups(self):
        while self.max_width < self.output_width + self.buffer_width:
            group = self.group_queue.deq()
            if not group:
                return
            self._break_one_group(group)

    def text(self, obj):
        """Add literal text to the output."""
        width = len(obj)
        if self.buffer:
            text = self.buffer[-1]
            if not isinstance(text, Text):
                text = Text()
                self.buffer.append(text)
            text.add(obj, width)
            self.buffer_width += width
            self._break_outer_groups()
        else:
            self.output.write(obj)
            self.output_width += width

    def breakable(self, sep=' '):
        """
        Add a breakable separator to the output.  This does not mean that it
        will automatically break here.  If no breaking on this position takes
        place the `sep` is inserted which default to one space.
        """
        width = len(sep)
        group = self.group_stack[-1]
        if group.want_break:
            self.flush()
            self.output.write(self.newline)
            self.output.write(' ' * self.indentation)
            self.output_width = self.indentation
            self.buffer_width = 0
        else:
            self.buffer.append(Breakable(sep, width, self))
            self.buffer_width += width
            self._break_outer_groups()

    def break_(self):
        """
        Explicitly insert a newline into the output, maintaining correct indentation.
        """
        group = self.group_queue.deq()
        if group:
            self._break_one_group(group)
        self.flush()
        self.output.write(self.newline)
        self.output.write(' ' * self.indentation)
        self.output_width = self.indentation
        self.buffer_width = 0


    def begin_group(self, indent=0, open=''):
        """
        Begin a group.
        The first parameter specifies the indentation for the next line (usually
        the width of the opening text), the second the opening text.  All
        parameters are optional.
        """
        if open:
            self.text(open)
        group = Group(self.group_stack[-1].depth + 1)
        self.group_stack.append(group)
        self.group_queue.enq(group)
        self.indentation += indent

    def _enumerate(self, seq):
        """like enumerate, but with an upper limit on the number of items"""
        for idx, x in enumerate(seq):
            if self.max_seq_length and idx >= self.max_seq_length:
                self.text(',')
                self.breakable()
                self.text('...')
                return
            yield idx, x

    def end_group(self, dedent=0, close=''):
        """End a group. See `begin_group` for more details."""
        self.indentation -= dedent
        group = self.group_stack.pop()
        if not group.breakables:
            self.group_queue.remove(group)
        if close:
            self.text(close)

    def flush(self):
        """Flush data that is left in the buffer."""
        for data in self.buffer:
            self.output_width += data.output(self.output, self.output_width)
        self.buffer.clear()
        self.buffer_width = 0


def _get_mro(obj_class):
    """ Get a reasonable method resolution order of a class and its superclasses
    for both old-style and new-style classes.
    """
    if not hasattr(obj_class, '__mro__'):
        # Old-style class. Mix in object to make a fake new-style class.
        try:
            obj_class = type(obj_class.__name__, (obj_class, object), {})
        except TypeError:
            # Old-style extension type that does not descend from object.
            # FIXME: try to construct a more thorough MRO.
            mro = [obj_class]
        else:
            mro = obj_class.__mro__[1:-1]
    else:
        mro = obj_class.__mro__
    return mro


class RepresentationPrinter(PrettyPrinter):
    """
    Special pretty printer that has a `pretty` method that calls the pretty
    printer for a python object.

    This class stores processing data on `self` so you must *never* use
    this class in a threaded environment.  Always lock it or reinstanciate
    it.

    Instances also have a verbose flag callbacks can access to control their
    output.  For example the default instance repr prints all attributes and
    methods that are not prefixed by an underscore if the printer is in
    verbose mode.
    """

    def __init__(self, output, verbose=False, max_width=79, newline='\n',
        singleton_pprinters=None, type_pprinters=None, deferred_pprinters=None,
        max_seq_length=MAX_SEQ_LENGTH):

        PrettyPrinter.__init__(self, output, max_width, newline, max_seq_length=max_seq_length)
        self.verbose = verbose
        self.stack = []
        if singleton_pprinters is None:
            singleton_pprinters = _singleton_pprinters.copy()
        self.singleton_pprinters = singleton_pprinters
        if type_pprinters is None:
            type_pprinters = _type_pprinters.copy()
        self.type_pprinters = type_pprinters
        if deferred_pprinters is None:
            deferred_pprinters = _deferred_type_pprinters.copy()
        self.deferred_pprinters = deferred_pprinters

    def pretty(self, obj):
        """Pretty print the given object."""
        obj_id = id(obj)
        cycle = obj_id in self.stack
        self.stack.append(obj_id)
        self.begin_group()
        try:
            obj_class = _safe_getattr(obj, '__class__', None) or type(obj)
            # First try to find registered singleton printers for the type.
            try:
                printer = self.singleton_pprinters[obj_id]
            except (TypeError, KeyError):
                pass
            else:
                return printer(obj, self, cycle)
            # Next walk the mro and check for either:
            #   1) a registered printer
            #   2) a _repr_pretty_ method
            for cls in _get_mro(obj_class):
                if cls in self.type_pprinters:
                    # printer registered in self.type_pprinters
                    return self.type_pprinters[cls](obj, self, cycle)
                else:
                    # deferred printer
                    printer = self._in_deferred_types(cls)
                    if printer is not None:
                        return printer(obj, self, cycle)
                    else:
                        # Finally look for special method names.
                        # Some objects automatically create any requested
                        # attribute. Try to ignore most of them by checking for
                        # callability.
                        if '_repr_pretty_' in cls.__dict__:
                            meth = cls._repr_pretty_
                            if callable(meth):
                                return meth(obj, self, cycle)
                        if (
                            cls is not object
                            # check if cls defines __repr__
                            and "__repr__" in cls.__dict__
                            # check if __repr__ is callable.
                            # Note: we need to test getattr(cls, '__repr__')
                            #   instead of cls.__dict__['__repr__']
                            #   in order to work with descriptors like partialmethod,
                            and callable(_safe_getattr(cls, "__repr__", None))
                        ):
                            return _repr_pprint(obj, self, cycle)

            return _default_pprint(obj, self, cycle)
        finally:
            self.end_group()
            self.stack.pop()

    def _in_deferred_types(self, cls):
        """
        Check if the given class is specified in the deferred type registry.

        Returns the printer from the registry if it exists, and None if the
        class is not in the registry. Successful matches will be moved to the
        regular type registry for future use.
        """
        mod = _safe_getattr(cls, '__module__', None)
        name = _safe_getattr(cls, '__name__', None)
        key = (mod, name)
        printer = None
        if key in self.deferred_pprinters:
            # Move the printer over to the regular registry.
            printer = self.deferred_pprinters.pop(key)
            self.type_pprinters[cls] = printer
        return printer


class Printable:

    def output(self, stream, output_width):
        return output_width


class Text(Printable):

    def __init__(self):
        self.objs = []
        self.width = 0

    def output(self, stream, output_width):
        for obj in self.objs:
            stream.write(obj)
        return output_width + self.width

    def add(self, obj, width):
        self.objs.append(obj)
        self.width += width


class Breakable(Printable):

    def __init__(self, seq, width, pretty):
        self.obj = seq
        self.width = width
        self.pretty = pretty
        self.indentation = pretty.indentation
        self.group = pretty.group_stack[-1]
        self.group.breakables.append(self)

    def output(self, stream, output_width):
        self.group.breakables.popleft()
        if self.group.want_break:
            stream.write(self.pretty.newline)
            stream.write(' ' * self.indentation)
            return self.indentation
        if not self.group.breakables:
            self.pretty.group_queue.remove(self.group)
        stream.write(self.obj)
        return output_width + self.width


class Group(Printable):

    def __init__(self, depth):
        self.depth = depth
        self.breakables = deque()
        self.want_break = False


class GroupQueue:

    def __init__(self, *groups):
        self.queue = []
        for group in groups:
            self.enq(group)

    def enq(self, group):
        depth = group.depth
        while depth > len(self.queue) - 1:
            self.queue.append([])
        self.queue[depth].append(group)

    def deq(self):
        for stack in self.queue:
            for idx, group in enumerate(reversed(stack)):
                if group.breakables:
                    del stack[idx]
                    group.want_break = True
                    return group
            for group in stack:
                group.want_break = True
            del stack[:]

    def remove(self, group):
        try:
            self.queue[group.depth].remove(group)
        except ValueError:
            pass


class RawText:
    """ Object such that ``p.pretty(RawText(value))`` is the same as ``p.text(value)``.

    An example usage of this would be to show a list as binary numbers, using
    ``p.pretty([RawText(bin(i)) for i in integers])``.
    """
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        p.text(self.value)


class CallExpression:
    """ Object which emits a line-wrapped call expression in the form `__name(*args, **kwargs)` """
    def __init__(__self, __name, *args, **kwargs):
        # dunders are to avoid clashes with kwargs, as python's name managing
        # will kick in.
        self = __self
        self.name = __name
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def factory(cls, name):
        def inner(*args, **kwargs):
            return cls(name, *args, **kwargs)
        return inner

    def _repr_pretty_(self, p, cycle):
        # dunders are to avoid clashes with kwargs, as python's name managing
        # will kick in.

        started = False
        def new_item():
            nonlocal started
            if started:
                p.text(",")
                p.breakable()
            started = True

        prefix = self.name + "("
        with p.group(len(prefix), prefix, ")"):
            for arg in self.args:
                new_item()
                p.pretty(arg)
            for arg_name, arg in self.kwargs.items():
                new_item()
                arg_prefix = arg_name + "="
                with p.group(len(arg_prefix), arg_prefix):
                    p.pretty(arg)


class RawStringLiteral:
    """ Wrapper that shows a string with a `r` prefix """
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        base_repr = repr(self.value)
        if base_repr[:1] in 'uU':
            base_repr = base_repr[1:]
            prefix = 'ur'
        else:
            prefix = 'r'
        base_repr = prefix + base_repr.replace('\\\\', '\\')
        p.text(base_repr)


def _default_pprint(obj, p, cycle):
    """
    The default print function.  Used if an object does not provide one and
    it's none of the builtin objects.
    """
    klass = _safe_getattr(obj, '__class__', None) or type(obj)
    if _safe_getattr(klass, '__repr__', None) is not object.__repr__:
        # A user-provided repr. Find newlines and replace them with p.break_()
        _repr_pprint(obj, p, cycle)
        return
    p.begin_group(1, '<')
    p.pretty(klass)
    p.text(' at 0x%x' % id(obj))
    if cycle:
        p.text(' ...')
    elif p.verbose:
        first = True
        for key in dir(obj):
            if not key.startswith('_'):
                try:
                    value = getattr(obj, key)
                except AttributeError:
                    continue
                if isinstance(value, types.MethodType):
                    continue
                if not first:
                    p.text(',')
                p.breakable()
                p.text(key)
                p.text('=')
                step = len(key) + 1
                p.indentation += step
                p.pretty(value)
                p.indentation -= step
                first = False
    p.end_group(1, '>')


def _seq_pprinter_factory(start, end):
    """
    Factory that returns a pprint function useful for sequences.  Used by
    the default pprint for tuples and lists.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text(start + '...' + end)
        step = len(start)
        p.begin_group(step, start)
        for idx, x in p._enumerate(obj):
            if idx:
                p.text(',')
                p.breakable()
            p.pretty(x)
        if len(obj) == 1 and isinstance(obj, tuple):
            # Special case for 1-item tuples.
            p.text(',')
        p.end_group(step, end)
    return inner


def _set_pprinter_factory(start, end):
    """
    Factory that returns a pprint function useful for sets and frozensets.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text(start + '...' + end)
        if len(obj) == 0:
            # Special case.
            p.text(type(obj).__name__ + '()')
        else:
            step = len(start)
            p.begin_group(step, start)
            # Like dictionary keys, we will try to sort the items if there aren't too many
            if not (p.max_seq_length and len(obj) >= p.max_seq_length):
                items = _sorted_for_pprint(obj)
            else:
                items = obj
            for idx, x in p._enumerate(items):
                if idx:
                    p.text(',')
                    p.breakable()
                p.pretty(x)
            p.end_group(step, end)
    return inner


def _dict_pprinter_factory(start, end):
    """
    Factory that returns a pprint function used by the default pprint of
    dicts and dict proxies.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text('{...}')
        step = len(start)
        p.begin_group(step, start)
        keys = obj.keys()
        for idx, key in p._enumerate(keys):
            if idx:
                p.text(',')
                p.breakable()
            p.pretty(key)
            p.text(': ')
            p.pretty(obj[key])
        p.end_group(step, end)
    return inner


def _super_pprint(obj, p, cycle):
    """The pprint for the super type."""
    p.begin_group(8, '<super: ')
    p.pretty(obj.__thisclass__)
    p.text(',')
    p.breakable()
    if PYPY: # In PyPy, super() objects don't have __self__ attributes
        dself = obj.__repr__.__self__
        p.pretty(None if dself is obj else dself)
    else:
        p.pretty(obj.__self__)
    p.end_group(8, '>')



class _ReFlags:
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        done_one = False
        for flag in (
            "IGNORECASE",
            "LOCALE",
            "MULTILINE",
            "DOTALL",
            "UNICODE",
            "VERBOSE",
            "DEBUG",
        ):
            if self.value & getattr(re, flag):
                if done_one:
                    p.text('|')
                p.text('re.' + flag)
                done_one = True


def _re_pattern_pprint(obj, p, cycle):
    """The pprint function for regular expression patterns."""
    re_compile = CallExpression.factory('re.compile')
    if obj.flags:
        p.pretty(re_compile(RawStringLiteral(obj.pattern), _ReFlags(obj.flags)))
    else:
        p.pretty(re_compile(RawStringLiteral(obj.pattern)))


def _types_simplenamespace_pprint(obj, p, cycle):
    """The pprint function for types.SimpleNamespace."""
    namespace = CallExpression.factory('namespace')
    if cycle:
        p.pretty(namespace(RawText("...")))
    else:
        p.pretty(namespace(**obj.__dict__))


def _type_pprint(obj, p, cycle):
    """The pprint for classes and types."""
    # Heap allocated types might not have the module attribute,
    # and others may set it to None.

    # Checks for a __repr__ override in the metaclass. Can't compare the
    # type(obj).__repr__ directly because in PyPy the representation function
    # inherited from type isn't the same type.__repr__
    if [m for m in _get_mro(type(obj)) if "__repr__" in vars(m)][:1] != [type]:
        _repr_pprint(obj, p, cycle)
        return

    mod = _safe_getattr(obj, '__module__', None)
    try:
        name = obj.__qualname__
        if not isinstance(name, str):
            # This can happen if the type implements __qualname__ as a property
            # or other descriptor in Python 2.
            raise Exception("Try __name__")
    except Exception:
        name = obj.__name__
        if not isinstance(name, str):
            name = '<unknown type>'

    if mod in (None, '__builtin__', 'builtins', 'exceptions'):
        p.text(name)
    else:
        p.text(mod + '.' + name)


def _repr_pprint(obj, p, cycle):
    """A pprint that just redirects to the normal repr function."""
    # Find newlines and replace them with p.break_()
    output = repr(obj)
    lines = output.splitlines()
    with p.group():
        for idx, output_line in enumerate(lines):
            if idx:
                p.break_()
            p.text(output_line)


def _function_pprint(obj, p, cycle):
    """Base pprint for all functions and builtin functions."""
    name = _safe_getattr(obj, '__qualname__', obj.__name__)
    mod = obj.__module__
    if mod and mod not in ('__builtin__', 'builtins', 'exceptions'):
        name = mod + '.' + name
    try:
       func_def = name + str(signature(obj))
    except ValueError:
       func_def = name
    p.text('<function %s>' % func_def)


def _exception_pprint(obj, p, cycle):
    """Base pprint for all exceptions."""
    name = getattr(obj.__class__, '__qualname__', obj.__class__.__name__)
    if obj.__class__.__module__ not in ('exceptions', 'builtins'):
        name = '%s.%s' % (obj.__class__.__module__, name)

    p.pretty(CallExpression(name, *getattr(obj, 'args', ())))


#: the exception base
_exception_base: type
try:
    _exception_base = BaseException
except NameError:
    _exception_base = Exception


#: printers for builtin types
_type_pprinters = {
    int:                        _repr_pprint,
    float:                      _repr_pprint,
    str:                        _repr_pprint,
    tuple:                      _seq_pprinter_factory('(', ')'),
    list:                       _seq_pprinter_factory('[', ']'),
    dict:                       _dict_pprinter_factory('{', '}'),
    set:                        _set_pprinter_factory('{', '}'),
    frozenset:                  _set_pprinter_factory('frozenset({', '})'),
    super:                      _super_pprint,
    _re_pattern_type:           _re_pattern_pprint,
    type:                       _type_pprint,
    types.FunctionType:         _function_pprint,
    types.BuiltinFunctionType:  _function_pprint,
    types.MethodType:           _repr_pprint,
    types.SimpleNamespace:      _types_simplenamespace_pprint,
    datetime.datetime:          _repr_pprint,
    datetime.timedelta:         _repr_pprint,
    _exception_base:            _exception_pprint
}

# render os.environ like a dict
_env_type = type(os.environ)
# future-proof in case os.environ becomes a plain dict?
if _env_type is not dict:
    _type_pprinters[_env_type] = _dict_pprinter_factory('environ{', '}')

_type_pprinters[types.MappingProxyType] = _dict_pprinter_factory("mappingproxy({", "})")
_type_pprinters[slice] = _repr_pprint

_type_pprinters[range] = _repr_pprint
_type_pprinters[bytes] = _repr_pprint

#: printers for types specified by name
_deferred_type_pprinters: Dict = {}


def for_type(typ, func):
    """
    Add a pretty printer for a given type.
    """
    oldfunc = _type_pprinters.get(typ, None)
    if func is not None:
        # To support easy restoration of old pprinters, we need to ignore Nones.
        _type_pprinters[typ] = func
    return oldfunc

def for_type_by_name(type_module, type_name, func):
    """
    Add a pretty printer for a type specified by the module and name of a type
    rather than the type object itself.
    """
    key = (type_module, type_name)
    oldfunc = _deferred_type_pprinters.get(key, None)
    if func is not None:
        # To support easy restoration of old pprinters, we need to ignore Nones.
        _deferred_type_pprinters[key] = func
    return oldfunc


#: printers for the default singletons
_singleton_pprinters = dict.fromkeys(map(id, [None, True, False, Ellipsis,
                                      NotImplemented]), _repr_pprint)


def _defaultdict_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    else:
        p.pretty(cls_ctor(obj.default_factory, dict(obj)))

def _ordereddict_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif len(obj):
        p.pretty(cls_ctor(list(obj.items())))
    else:
        p.pretty(cls_ctor())

def _deque_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif obj.maxlen is not None:
        p.pretty(cls_ctor(list(obj), maxlen=obj.maxlen))
    else:
        p.pretty(cls_ctor(list(obj)))

def _counter_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif len(obj):
        p.pretty(cls_ctor(dict(obj.most_common())))
    else:
        p.pretty(cls_ctor())


def _userlist_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    else:
        p.pretty(cls_ctor(obj.data))


for_type_by_name('collections', 'defaultdict', _defaultdict_pprint)
for_type_by_name('collections', 'OrderedDict', _ordereddict_pprint)
for_type_by_name('collections', 'deque', _deque_pprint)
for_type_by_name('collections', 'Counter', _counter_pprint)
for_type_by_name("collections", "UserList", _userlist_pprint)

if __name__ == '__main__':
    from random import randrange

    class Foo:
        def __init__(self):
            self.foo = 1
            self.bar = re.compile(r'\s+')
            self.blub = dict.fromkeys(range(30), randrange(1, 40))
            self.hehe = 23424.234234
            self.list = ["blub", "blah", self]

        def get_foo(self):
            print("foo")

    pprint(Foo(), verbose=True)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\lib\pretty.py ===
"""
Python advanced pretty printer.  This pretty printer is intended to
replace the old `pprint` python module which does not allow developers
to provide their own pretty print callbacks.

This module is based on ruby's `prettyprint.rb` library by `Tanaka Akira`.


Example Usage
-------------

To directly print the representation of an object use `pprint`::

    from pretty import pprint
    pprint(complex_object)

To get a string of the output use `pretty`::

    from pretty import pretty
    string = pretty(complex_object)


Extending
---------

The pretty library allows developers to add pretty printing rules for their
own objects.  This process is straightforward.  All you have to do is to
add a `_repr_pretty_` method to your object and call the methods on the
pretty printer passed::

    class MyObject(object):

        def _repr_pretty_(self, p, cycle):
            ...

Here's an example for a class with a simple constructor::

    class MySimpleObject:

        def __init__(self, a, b, *, c=None):
            self.a = a
            self.b = b
            self.c = c

        def _repr_pretty_(self, p, cycle):
            ctor = CallExpression.factory(self.__class__.__name__)
            if self.c is None:
                p.pretty(ctor(a, b))
            else:
                p.pretty(ctor(a, b, c=c))

Here is an example implementation of a `_repr_pretty_` method for a list
subclass::

    class MyList(list):

        def _repr_pretty_(self, p, cycle):
            if cycle:
                p.text('MyList(...)')
            else:
                with p.group(8, 'MyList([', '])'):
                    for idx, item in enumerate(self):
                        if idx:
                            p.text(',')
                            p.breakable()
                        p.pretty(item)

The `cycle` parameter is `True` if pretty detected a cycle.  You *have* to
react to that or the result is an infinite loop.  `p.text()` just adds
non breaking text to the output, `p.breakable()` either adds a whitespace
or breaks here.  If you pass it an argument it's used instead of the
default space.  `p.pretty` prettyprints another object using the pretty print
method.

The first parameter to the `group` function specifies the extra indentation
of the next line.  In this example the next item will either be on the same
line (if the items are short enough) or aligned with the right edge of the
opening bracket of `MyList`.

If you just want to indent something you can use the group function
without open / close parameters.  You can also use this code::

    with p.indent(2):
        ...

Inheritance diagram:

.. inheritance-diagram:: IPython.lib.pretty
   :parts: 3

:copyright: 2007 by Armin Ronacher.
            Portions (c) 2009 by Robert Kern.
:license: BSD License.
"""

from contextlib import contextmanager
import datetime
import os
import re
import sys
import types
from collections import deque
from inspect import signature
from io import StringIO
from warnings import warn

from IPython.utils.decorators import undoc
from IPython.utils.py3compat import PYPY

from typing import Dict

__all__ = ['pretty', 'pprint', 'PrettyPrinter', 'RepresentationPrinter',
    'for_type', 'for_type_by_name', 'RawText', 'RawStringLiteral', 'CallExpression']


MAX_SEQ_LENGTH = 1000
_re_pattern_type = type(re.compile(''))

def _safe_getattr(obj, attr, default=None):
    """Safe version of getattr.

    Same as getattr, but will return ``default`` on any Exception,
    rather than raising.
    """
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default

def _sorted_for_pprint(items):
    """
    Sort the given items for pretty printing. Since some predictable
    sorting is better than no sorting at all, we sort on the string
    representation if normal sorting fails.
    """
    items = list(items)
    try:
        return sorted(items)
    except Exception:
        try:
            return sorted(items, key=str)
        except Exception:
            return items

def pretty(obj, verbose=False, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
    """
    Pretty print the object's representation.
    """
    stream = StringIO()
    printer = RepresentationPrinter(stream, verbose, max_width, newline, max_seq_length=max_seq_length)
    printer.pretty(obj)
    printer.flush()
    return stream.getvalue()


def pprint(obj, verbose=False, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
    """
    Like `pretty` but print to stdout.
    """
    printer = RepresentationPrinter(sys.stdout, verbose, max_width, newline, max_seq_length=max_seq_length)
    printer.pretty(obj)
    printer.flush()
    sys.stdout.write(newline)
    sys.stdout.flush()

class _PrettyPrinterBase:

    @contextmanager
    def indent(self, indent):
        """with statement support for indenting/dedenting."""
        self.indentation += indent
        try:
            yield
        finally:
            self.indentation -= indent

    @contextmanager
    def group(self, indent=0, open='', close=''):
        """like begin_group / end_group but for the with statement."""
        self.begin_group(indent, open)
        try:
            yield
        finally:
            self.end_group(indent, close)

class PrettyPrinter(_PrettyPrinterBase):
    """
    Baseclass for the `RepresentationPrinter` prettyprinter that is used to
    generate pretty reprs of objects.  Contrary to the `RepresentationPrinter`
    this printer knows nothing about the default pprinters or the `_repr_pretty_`
    callback method.
    """

    def __init__(self, output, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
        self.output = output
        self.max_width = max_width
        self.newline = newline
        self.max_seq_length = max_seq_length
        self.output_width = 0
        self.buffer_width = 0
        self.buffer = deque()

        root_group = Group(0)
        self.group_stack = [root_group]
        self.group_queue = GroupQueue(root_group)
        self.indentation = 0

    def _break_one_group(self, group):
        while group.breakables:
            x = self.buffer.popleft()
            self.output_width = x.output(self.output, self.output_width)
            self.buffer_width -= x.width
        while self.buffer and isinstance(self.buffer[0], Text):
            x = self.buffer.popleft()
            self.output_width = x.output(self.output, self.output_width)
            self.buffer_width -= x.width

    def _break_outer_groups(self):
        while self.max_width < self.output_width + self.buffer_width:
            group = self.group_queue.deq()
            if not group:
                return
            self._break_one_group(group)

    def text(self, obj):
        """Add literal text to the output."""
        width = len(obj)
        if self.buffer:
            text = self.buffer[-1]
            if not isinstance(text, Text):
                text = Text()
                self.buffer.append(text)
            text.add(obj, width)
            self.buffer_width += width
            self._break_outer_groups()
        else:
            self.output.write(obj)
            self.output_width += width

    def breakable(self, sep=' '):
        """
        Add a breakable separator to the output.  This does not mean that it
        will automatically break here.  If no breaking on this position takes
        place the `sep` is inserted which default to one space.
        """
        width = len(sep)
        group = self.group_stack[-1]
        if group.want_break:
            self.flush()
            self.output.write(self.newline)
            self.output.write(' ' * self.indentation)
            self.output_width = self.indentation
            self.buffer_width = 0
        else:
            self.buffer.append(Breakable(sep, width, self))
            self.buffer_width += width
            self._break_outer_groups()

    def break_(self):
        """
        Explicitly insert a newline into the output, maintaining correct indentation.
        """
        group = self.group_queue.deq()
        if group:
            self._break_one_group(group)
        self.flush()
        self.output.write(self.newline)
        self.output.write(' ' * self.indentation)
        self.output_width = self.indentation
        self.buffer_width = 0


    def begin_group(self, indent=0, open=''):
        """
        Begin a group.
        The first parameter specifies the indentation for the next line (usually
        the width of the opening text), the second the opening text.  All
        parameters are optional.
        """
        if open:
            self.text(open)
        group = Group(self.group_stack[-1].depth + 1)
        self.group_stack.append(group)
        self.group_queue.enq(group)
        self.indentation += indent

    def _enumerate(self, seq):
        """like enumerate, but with an upper limit on the number of items"""
        for idx, x in enumerate(seq):
            if self.max_seq_length and idx >= self.max_seq_length:
                self.text(',')
                self.breakable()
                self.text('...')
                return
            yield idx, x

    def end_group(self, dedent=0, close=''):
        """End a group. See `begin_group` for more details."""
        self.indentation -= dedent
        group = self.group_stack.pop()
        if not group.breakables:
            self.group_queue.remove(group)
        if close:
            self.text(close)

    def flush(self):
        """Flush data that is left in the buffer."""
        for data in self.buffer:
            self.output_width += data.output(self.output, self.output_width)
        self.buffer.clear()
        self.buffer_width = 0


def _get_mro(obj_class):
    """ Get a reasonable method resolution order of a class and its superclasses
    for both old-style and new-style classes.
    """
    if not hasattr(obj_class, '__mro__'):
        # Old-style class. Mix in object to make a fake new-style class.
        try:
            obj_class = type(obj_class.__name__, (obj_class, object), {})
        except TypeError:
            # Old-style extension type that does not descend from object.
            # FIXME: try to construct a more thorough MRO.
            mro = [obj_class]
        else:
            mro = obj_class.__mro__[1:-1]
    else:
        mro = obj_class.__mro__
    return mro


class RepresentationPrinter(PrettyPrinter):
    """
    Special pretty printer that has a `pretty` method that calls the pretty
    printer for a python object.

    This class stores processing data on `self` so you must *never* use
    this class in a threaded environment.  Always lock it or reinstanciate
    it.

    Instances also have a verbose flag callbacks can access to control their
    output.  For example the default instance repr prints all attributes and
    methods that are not prefixed by an underscore if the printer is in
    verbose mode.
    """

    def __init__(self, output, verbose=False, max_width=79, newline='\n',
        singleton_pprinters=None, type_pprinters=None, deferred_pprinters=None,
        max_seq_length=MAX_SEQ_LENGTH):

        PrettyPrinter.__init__(self, output, max_width, newline, max_seq_length=max_seq_length)
        self.verbose = verbose
        self.stack = []
        if singleton_pprinters is None:
            singleton_pprinters = _singleton_pprinters.copy()
        self.singleton_pprinters = singleton_pprinters
        if type_pprinters is None:
            type_pprinters = _type_pprinters.copy()
        self.type_pprinters = type_pprinters
        if deferred_pprinters is None:
            deferred_pprinters = _deferred_type_pprinters.copy()
        self.deferred_pprinters = deferred_pprinters

    def pretty(self, obj):
        """Pretty print the given object."""
        obj_id = id(obj)
        cycle = obj_id in self.stack
        self.stack.append(obj_id)
        self.begin_group()
        try:
            obj_class = _safe_getattr(obj, '__class__', None) or type(obj)
            # First try to find registered singleton printers for the type.
            try:
                printer = self.singleton_pprinters[obj_id]
            except (TypeError, KeyError):
                pass
            else:
                return printer(obj, self, cycle)
            # Next walk the mro and check for either:
            #   1) a registered printer
            #   2) a _repr_pretty_ method
            for cls in _get_mro(obj_class):
                if cls in self.type_pprinters:
                    # printer registered in self.type_pprinters
                    return self.type_pprinters[cls](obj, self, cycle)
                else:
                    # deferred printer
                    printer = self._in_deferred_types(cls)
                    if printer is not None:
                        return printer(obj, self, cycle)
                    else:
                        # Finally look for special method names.
                        # Some objects automatically create any requested
                        # attribute. Try to ignore most of them by checking for
                        # callability.
                        if '_repr_pretty_' in cls.__dict__:
                            meth = cls._repr_pretty_
                            if callable(meth):
                                return meth(obj, self, cycle)
                        if (
                            cls is not object
                            # check if cls defines __repr__
                            and "__repr__" in cls.__dict__
                            # check if __repr__ is callable.
                            # Note: we need to test getattr(cls, '__repr__')
                            #   instead of cls.__dict__['__repr__']
                            #   in order to work with descriptors like partialmethod,
                            and callable(_safe_getattr(cls, "__repr__", None))
                        ):
                            return _repr_pprint(obj, self, cycle)

            return _default_pprint(obj, self, cycle)
        finally:
            self.end_group()
            self.stack.pop()

    def _in_deferred_types(self, cls):
        """
        Check if the given class is specified in the deferred type registry.

        Returns the printer from the registry if it exists, and None if the
        class is not in the registry. Successful matches will be moved to the
        regular type registry for future use.
        """
        mod = _safe_getattr(cls, '__module__', None)
        name = _safe_getattr(cls, '__name__', None)
        key = (mod, name)
        printer = None
        if key in self.deferred_pprinters:
            # Move the printer over to the regular registry.
            printer = self.deferred_pprinters.pop(key)
            self.type_pprinters[cls] = printer
        return printer


class Printable:

    def output(self, stream, output_width):
        return output_width


class Text(Printable):

    def __init__(self):
        self.objs = []
        self.width = 0

    def output(self, stream, output_width):
        for obj in self.objs:
            stream.write(obj)
        return output_width + self.width

    def add(self, obj, width):
        self.objs.append(obj)
        self.width += width


class Breakable(Printable):

    def __init__(self, seq, width, pretty):
        self.obj = seq
        self.width = width
        self.pretty = pretty
        self.indentation = pretty.indentation
        self.group = pretty.group_stack[-1]
        self.group.breakables.append(self)

    def output(self, stream, output_width):
        self.group.breakables.popleft()
        if self.group.want_break:
            stream.write(self.pretty.newline)
            stream.write(' ' * self.indentation)
            return self.indentation
        if not self.group.breakables:
            self.pretty.group_queue.remove(self.group)
        stream.write(self.obj)
        return output_width + self.width


class Group(Printable):

    def __init__(self, depth):
        self.depth = depth
        self.breakables = deque()
        self.want_break = False


class GroupQueue:

    def __init__(self, *groups):
        self.queue = []
        for group in groups:
            self.enq(group)

    def enq(self, group):
        depth = group.depth
        while depth > len(self.queue) - 1:
            self.queue.append([])
        self.queue[depth].append(group)

    def deq(self):
        for stack in self.queue:
            for idx, group in enumerate(reversed(stack)):
                if group.breakables:
                    del stack[idx]
                    group.want_break = True
                    return group
            for group in stack:
                group.want_break = True
            del stack[:]

    def remove(self, group):
        try:
            self.queue[group.depth].remove(group)
        except ValueError:
            pass


class RawText:
    """ Object such that ``p.pretty(RawText(value))`` is the same as ``p.text(value)``.

    An example usage of this would be to show a list as binary numbers, using
    ``p.pretty([RawText(bin(i)) for i in integers])``.
    """
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        p.text(self.value)


class CallExpression:
    """ Object which emits a line-wrapped call expression in the form `__name(*args, **kwargs)` """
    def __init__(__self, __name, *args, **kwargs):
        # dunders are to avoid clashes with kwargs, as python's name managing
        # will kick in.
        self = __self
        self.name = __name
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def factory(cls, name):
        def inner(*args, **kwargs):
            return cls(name, *args, **kwargs)
        return inner

    def _repr_pretty_(self, p, cycle):
        # dunders are to avoid clashes with kwargs, as python's name managing
        # will kick in.

        started = False
        def new_item():
            nonlocal started
            if started:
                p.text(",")
                p.breakable()
            started = True

        prefix = self.name + "("
        with p.group(len(prefix), prefix, ")"):
            for arg in self.args:
                new_item()
                p.pretty(arg)
            for arg_name, arg in self.kwargs.items():
                new_item()
                arg_prefix = arg_name + "="
                with p.group(len(arg_prefix), arg_prefix):
                    p.pretty(arg)


class RawStringLiteral:
    """ Wrapper that shows a string with a `r` prefix """
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        base_repr = repr(self.value)
        if base_repr[:1] in 'uU':
            base_repr = base_repr[1:]
            prefix = 'ur'
        else:
            prefix = 'r'
        base_repr = prefix + base_repr.replace('\\\\', '\\')
        p.text(base_repr)


def _default_pprint(obj, p, cycle):
    """
    The default print function.  Used if an object does not provide one and
    it's none of the builtin objects.
    """
    klass = _safe_getattr(obj, '__class__', None) or type(obj)
    if _safe_getattr(klass, '__repr__', None) is not object.__repr__:
        # A user-provided repr. Find newlines and replace them with p.break_()
        _repr_pprint(obj, p, cycle)
        return
    p.begin_group(1, '<')
    p.pretty(klass)
    p.text(' at 0x%x' % id(obj))
    if cycle:
        p.text(' ...')
    elif p.verbose:
        first = True
        for key in dir(obj):
            if not key.startswith('_'):
                try:
                    value = getattr(obj, key)
                except AttributeError:
                    continue
                if isinstance(value, types.MethodType):
                    continue
                if not first:
                    p.text(',')
                p.breakable()
                p.text(key)
                p.text('=')
                step = len(key) + 1
                p.indentation += step
                p.pretty(value)
                p.indentation -= step
                first = False
    p.end_group(1, '>')


def _seq_pprinter_factory(start, end):
    """
    Factory that returns a pprint function useful for sequences.  Used by
    the default pprint for tuples and lists.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text(start + '...' + end)
        step = len(start)
        p.begin_group(step, start)
        for idx, x in p._enumerate(obj):
            if idx:
                p.text(',')
                p.breakable()
            p.pretty(x)
        if len(obj) == 1 and isinstance(obj, tuple):
            # Special case for 1-item tuples.
            p.text(',')
        p.end_group(step, end)
    return inner


def _set_pprinter_factory(start, end):
    """
    Factory that returns a pprint function useful for sets and frozensets.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text(start + '...' + end)
        if len(obj) == 0:
            # Special case.
            p.text(type(obj).__name__ + '()')
        else:
            step = len(start)
            p.begin_group(step, start)
            # Like dictionary keys, we will try to sort the items if there aren't too many
            if not (p.max_seq_length and len(obj) >= p.max_seq_length):
                items = _sorted_for_pprint(obj)
            else:
                items = obj
            for idx, x in p._enumerate(items):
                if idx:
                    p.text(',')
                    p.breakable()
                p.pretty(x)
            p.end_group(step, end)
    return inner


def _dict_pprinter_factory(start, end):
    """
    Factory that returns a pprint function used by the default pprint of
    dicts and dict proxies.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text('{...}')
        step = len(start)
        p.begin_group(step, start)
        keys = obj.keys()
        for idx, key in p._enumerate(keys):
            if idx:
                p.text(',')
                p.breakable()
            p.pretty(key)
            p.text(': ')
            p.pretty(obj[key])
        p.end_group(step, end)
    return inner


def _super_pprint(obj, p, cycle):
    """The pprint for the super type."""
    p.begin_group(8, '<super: ')
    p.pretty(obj.__thisclass__)
    p.text(',')
    p.breakable()
    if PYPY: # In PyPy, super() objects don't have __self__ attributes
        dself = obj.__repr__.__self__
        p.pretty(None if dself is obj else dself)
    else:
        p.pretty(obj.__self__)
    p.end_group(8, '>')



class _ReFlags:
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        done_one = False
        for flag in (
            "IGNORECASE",
            "LOCALE",
            "MULTILINE",
            "DOTALL",
            "UNICODE",
            "VERBOSE",
            "DEBUG",
        ):
            if self.value & getattr(re, flag):
                if done_one:
                    p.text('|')
                p.text('re.' + flag)
                done_one = True


def _re_pattern_pprint(obj, p, cycle):
    """The pprint function for regular expression patterns."""
    re_compile = CallExpression.factory('re.compile')
    if obj.flags:
        p.pretty(re_compile(RawStringLiteral(obj.pattern), _ReFlags(obj.flags)))
    else:
        p.pretty(re_compile(RawStringLiteral(obj.pattern)))


def _types_simplenamespace_pprint(obj, p, cycle):
    """The pprint function for types.SimpleNamespace."""
    namespace = CallExpression.factory('namespace')
    if cycle:
        p.pretty(namespace(RawText("...")))
    else:
        p.pretty(namespace(**obj.__dict__))


def _type_pprint(obj, p, cycle):
    """The pprint for classes and types."""
    # Heap allocated types might not have the module attribute,
    # and others may set it to None.

    # Checks for a __repr__ override in the metaclass. Can't compare the
    # type(obj).__repr__ directly because in PyPy the representation function
    # inherited from type isn't the same type.__repr__
    if [m for m in _get_mro(type(obj)) if "__repr__" in vars(m)][:1] != [type]:
        _repr_pprint(obj, p, cycle)
        return

    mod = _safe_getattr(obj, '__module__', None)
    try:
        name = obj.__qualname__
        if not isinstance(name, str):
            # This can happen if the type implements __qualname__ as a property
            # or other descriptor in Python 2.
            raise Exception("Try __name__")
    except Exception:
        name = obj.__name__
        if not isinstance(name, str):
            name = '<unknown type>'

    if mod in (None, '__builtin__', 'builtins', 'exceptions'):
        p.text(name)
    else:
        p.text(mod + '.' + name)


def _repr_pprint(obj, p, cycle):
    """A pprint that just redirects to the normal repr function."""
    # Find newlines and replace them with p.break_()
    output = repr(obj)
    lines = output.splitlines()
    with p.group():
        for idx, output_line in enumerate(lines):
            if idx:
                p.break_()
            p.text(output_line)


def _function_pprint(obj, p, cycle):
    """Base pprint for all functions and builtin functions."""
    name = _safe_getattr(obj, '__qualname__', obj.__name__)
    mod = obj.__module__
    if mod and mod not in ('__builtin__', 'builtins', 'exceptions'):
        name = mod + '.' + name
    try:
       func_def = name + str(signature(obj))
    except ValueError:
       func_def = name
    p.text('<function %s>' % func_def)


def _exception_pprint(obj, p, cycle):
    """Base pprint for all exceptions."""
    name = getattr(obj.__class__, '__qualname__', obj.__class__.__name__)
    if obj.__class__.__module__ not in ('exceptions', 'builtins'):
        name = '%s.%s' % (obj.__class__.__module__, name)

    p.pretty(CallExpression(name, *getattr(obj, 'args', ())))


#: the exception base
_exception_base: type
try:
    _exception_base = BaseException
except NameError:
    _exception_base = Exception


#: printers for builtin types
_type_pprinters = {
    int:                        _repr_pprint,
    float:                      _repr_pprint,
    str:                        _repr_pprint,
    tuple:                      _seq_pprinter_factory('(', ')'),
    list:                       _seq_pprinter_factory('[', ']'),
    dict:                       _dict_pprinter_factory('{', '}'),
    set:                        _set_pprinter_factory('{', '}'),
    frozenset:                  _set_pprinter_factory('frozenset({', '})'),
    super:                      _super_pprint,
    _re_pattern_type:           _re_pattern_pprint,
    type:                       _type_pprint,
    types.FunctionType:         _function_pprint,
    types.BuiltinFunctionType:  _function_pprint,
    types.MethodType:           _repr_pprint,
    types.SimpleNamespace:      _types_simplenamespace_pprint,
    datetime.datetime:          _repr_pprint,
    datetime.timedelta:         _repr_pprint,
    _exception_base:            _exception_pprint
}

# render os.environ like a dict
_env_type = type(os.environ)
# future-proof in case os.environ becomes a plain dict?
if _env_type is not dict:
    _type_pprinters[_env_type] = _dict_pprinter_factory('environ{', '}')

_type_pprinters[types.MappingProxyType] = _dict_pprinter_factory("mappingproxy({", "})")
_type_pprinters[slice] = _repr_pprint

_type_pprinters[range] = _repr_pprint
_type_pprinters[bytes] = _repr_pprint

#: printers for types specified by name
_deferred_type_pprinters: Dict = {}


def for_type(typ, func):
    """
    Add a pretty printer for a given type.
    """
    oldfunc = _type_pprinters.get(typ, None)
    if func is not None:
        # To support easy restoration of old pprinters, we need to ignore Nones.
        _type_pprinters[typ] = func
    return oldfunc

def for_type_by_name(type_module, type_name, func):
    """
    Add a pretty printer for a type specified by the module and name of a type
    rather than the type object itself.
    """
    key = (type_module, type_name)
    oldfunc = _deferred_type_pprinters.get(key, None)
    if func is not None:
        # To support easy restoration of old pprinters, we need to ignore Nones.
        _deferred_type_pprinters[key] = func
    return oldfunc


#: printers for the default singletons
_singleton_pprinters = dict.fromkeys(map(id, [None, True, False, Ellipsis,
                                      NotImplemented]), _repr_pprint)


def _defaultdict_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    else:
        p.pretty(cls_ctor(obj.default_factory, dict(obj)))

def _ordereddict_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif len(obj):
        p.pretty(cls_ctor(list(obj.items())))
    else:
        p.pretty(cls_ctor())

def _deque_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif obj.maxlen is not None:
        p.pretty(cls_ctor(list(obj), maxlen=obj.maxlen))
    else:
        p.pretty(cls_ctor(list(obj)))

def _counter_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif len(obj):
        p.pretty(cls_ctor(dict(obj.most_common())))
    else:
        p.pretty(cls_ctor())


def _userlist_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    else:
        p.pretty(cls_ctor(obj.data))


for_type_by_name('collections', 'defaultdict', _defaultdict_pprint)
for_type_by_name('collections', 'OrderedDict', _ordereddict_pprint)
for_type_by_name('collections', 'deque', _deque_pprint)
for_type_by_name('collections', 'Counter', _counter_pprint)
for_type_by_name("collections", "UserList", _userlist_pprint)

if __name__ == '__main__':
    from random import randrange

    class Foo:
        def __init__(self):
            self.foo = 1
            self.bar = re.compile(r'\s+')
            self.blub = dict.fromkeys(range(30), randrange(1, 40))
            self.hehe = 23424.234234
            self.list = ["blub", "blah", self]

        def get_foo(self):
            print("foo")

    pprint(Foo(), verbose=True)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\IPython\lib\pretty.py ===
"""
Python advanced pretty printer.  This pretty printer is intended to
replace the old `pprint` python module which does not allow developers
to provide their own pretty print callbacks.

This module is based on ruby's `prettyprint.rb` library by `Tanaka Akira`.


Example Usage
-------------

To directly print the representation of an object use `pprint`::

    from pretty import pprint
    pprint(complex_object)

To get a string of the output use `pretty`::

    from pretty import pretty
    string = pretty(complex_object)


Extending
---------

The pretty library allows developers to add pretty printing rules for their
own objects.  This process is straightforward.  All you have to do is to
add a `_repr_pretty_` method to your object and call the methods on the
pretty printer passed::

    class MyObject(object):

        def _repr_pretty_(self, p, cycle):
            ...

Here's an example for a class with a simple constructor::

    class MySimpleObject:

        def __init__(self, a, b, *, c=None):
            self.a = a
            self.b = b
            self.c = c

        def _repr_pretty_(self, p, cycle):
            ctor = CallExpression.factory(self.__class__.__name__)
            if self.c is None:
                p.pretty(ctor(a, b))
            else:
                p.pretty(ctor(a, b, c=c))

Here is an example implementation of a `_repr_pretty_` method for a list
subclass::

    class MyList(list):

        def _repr_pretty_(self, p, cycle):
            if cycle:
                p.text('MyList(...)')
            else:
                with p.group(8, 'MyList([', '])'):
                    for idx, item in enumerate(self):
                        if idx:
                            p.text(',')
                            p.breakable()
                        p.pretty(item)

The `cycle` parameter is `True` if pretty detected a cycle.  You *have* to
react to that or the result is an infinite loop.  `p.text()` just adds
non breaking text to the output, `p.breakable()` either adds a whitespace
or breaks here.  If you pass it an argument it's used instead of the
default space.  `p.pretty` prettyprints another object using the pretty print
method.

The first parameter to the `group` function specifies the extra indentation
of the next line.  In this example the next item will either be on the same
line (if the items are short enough) or aligned with the right edge of the
opening bracket of `MyList`.

If you just want to indent something you can use the group function
without open / close parameters.  You can also use this code::

    with p.indent(2):
        ...

Inheritance diagram:

.. inheritance-diagram:: IPython.lib.pretty
   :parts: 3

:copyright: 2007 by Armin Ronacher.
            Portions (c) 2009 by Robert Kern.
:license: BSD License.
"""

from contextlib import contextmanager
import datetime
import os
import re
import sys
import types
from collections import deque
from inspect import signature
from io import StringIO
from warnings import warn

from IPython.utils.decorators import undoc
from IPython.utils.py3compat import PYPY

from typing import Dict

__all__ = ['pretty', 'pprint', 'PrettyPrinter', 'RepresentationPrinter',
    'for_type', 'for_type_by_name', 'RawText', 'RawStringLiteral', 'CallExpression']


MAX_SEQ_LENGTH = 1000
_re_pattern_type = type(re.compile(''))

def _safe_getattr(obj, attr, default=None):
    """Safe version of getattr.

    Same as getattr, but will return ``default`` on any Exception,
    rather than raising.
    """
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default

def _sorted_for_pprint(items):
    """
    Sort the given items for pretty printing. Since some predictable
    sorting is better than no sorting at all, we sort on the string
    representation if normal sorting fails.
    """
    items = list(items)
    try:
        return sorted(items)
    except Exception:
        try:
            return sorted(items, key=str)
        except Exception:
            return items

def pretty(obj, verbose=False, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
    """
    Pretty print the object's representation.
    """
    stream = StringIO()
    printer = RepresentationPrinter(stream, verbose, max_width, newline, max_seq_length=max_seq_length)
    printer.pretty(obj)
    printer.flush()
    return stream.getvalue()


def pprint(obj, verbose=False, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
    """
    Like `pretty` but print to stdout.
    """
    printer = RepresentationPrinter(sys.stdout, verbose, max_width, newline, max_seq_length=max_seq_length)
    printer.pretty(obj)
    printer.flush()
    sys.stdout.write(newline)
    sys.stdout.flush()

class _PrettyPrinterBase:

    @contextmanager
    def indent(self, indent):
        """with statement support for indenting/dedenting."""
        self.indentation += indent
        try:
            yield
        finally:
            self.indentation -= indent

    @contextmanager
    def group(self, indent=0, open='', close=''):
        """like begin_group / end_group but for the with statement."""
        self.begin_group(indent, open)
        try:
            yield
        finally:
            self.end_group(indent, close)

class PrettyPrinter(_PrettyPrinterBase):
    """
    Baseclass for the `RepresentationPrinter` prettyprinter that is used to
    generate pretty reprs of objects.  Contrary to the `RepresentationPrinter`
    this printer knows nothing about the default pprinters or the `_repr_pretty_`
    callback method.
    """

    def __init__(self, output, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
        self.output = output
        self.max_width = max_width
        self.newline = newline
        self.max_seq_length = max_seq_length
        self.output_width = 0
        self.buffer_width = 0
        self.buffer = deque()

        root_group = Group(0)
        self.group_stack = [root_group]
        self.group_queue = GroupQueue(root_group)
        self.indentation = 0

    def _break_one_group(self, group):
        while group.breakables:
            x = self.buffer.popleft()
            self.output_width = x.output(self.output, self.output_width)
            self.buffer_width -= x.width
        while self.buffer and isinstance(self.buffer[0], Text):
            x = self.buffer.popleft()
            self.output_width = x.output(self.output, self.output_width)
            self.buffer_width -= x.width

    def _break_outer_groups(self):
        while self.max_width < self.output_width + self.buffer_width:
            group = self.group_queue.deq()
            if not group:
                return
            self._break_one_group(group)

    def text(self, obj):
        """Add literal text to the output."""
        width = len(obj)
        if self.buffer:
            text = self.buffer[-1]
            if not isinstance(text, Text):
                text = Text()
                self.buffer.append(text)
            text.add(obj, width)
            self.buffer_width += width
            self._break_outer_groups()
        else:
            self.output.write(obj)
            self.output_width += width

    def breakable(self, sep=' '):
        """
        Add a breakable separator to the output.  This does not mean that it
        will automatically break here.  If no breaking on this position takes
        place the `sep` is inserted which default to one space.
        """
        width = len(sep)
        group = self.group_stack[-1]
        if group.want_break:
            self.flush()
            self.output.write(self.newline)
            self.output.write(' ' * self.indentation)
            self.output_width = self.indentation
            self.buffer_width = 0
        else:
            self.buffer.append(Breakable(sep, width, self))
            self.buffer_width += width
            self._break_outer_groups()

    def break_(self):
        """
        Explicitly insert a newline into the output, maintaining correct indentation.
        """
        group = self.group_queue.deq()
        if group:
            self._break_one_group(group)
        self.flush()
        self.output.write(self.newline)
        self.output.write(' ' * self.indentation)
        self.output_width = self.indentation
        self.buffer_width = 0


    def begin_group(self, indent=0, open=''):
        """
        Begin a group.
        The first parameter specifies the indentation for the next line (usually
        the width of the opening text), the second the opening text.  All
        parameters are optional.
        """
        if open:
            self.text(open)
        group = Group(self.group_stack[-1].depth + 1)
        self.group_stack.append(group)
        self.group_queue.enq(group)
        self.indentation += indent

    def _enumerate(self, seq):
        """like enumerate, but with an upper limit on the number of items"""
        for idx, x in enumerate(seq):
            if self.max_seq_length and idx >= self.max_seq_length:
                self.text(',')
                self.breakable()
                self.text('...')
                return
            yield idx, x

    def end_group(self, dedent=0, close=''):
        """End a group. See `begin_group` for more details."""
        self.indentation -= dedent
        group = self.group_stack.pop()
        if not group.breakables:
            self.group_queue.remove(group)
        if close:
            self.text(close)

    def flush(self):
        """Flush data that is left in the buffer."""
        for data in self.buffer:
            self.output_width += data.output(self.output, self.output_width)
        self.buffer.clear()
        self.buffer_width = 0


def _get_mro(obj_class):
    """ Get a reasonable method resolution order of a class and its superclasses
    for both old-style and new-style classes.
    """
    if not hasattr(obj_class, '__mro__'):
        # Old-style class. Mix in object to make a fake new-style class.
        try:
            obj_class = type(obj_class.__name__, (obj_class, object), {})
        except TypeError:
            # Old-style extension type that does not descend from object.
            # FIXME: try to construct a more thorough MRO.
            mro = [obj_class]
        else:
            mro = obj_class.__mro__[1:-1]
    else:
        mro = obj_class.__mro__
    return mro


class RepresentationPrinter(PrettyPrinter):
    """
    Special pretty printer that has a `pretty` method that calls the pretty
    printer for a python object.

    This class stores processing data on `self` so you must *never* use
    this class in a threaded environment.  Always lock it or reinstanciate
    it.

    Instances also have a verbose flag callbacks can access to control their
    output.  For example the default instance repr prints all attributes and
    methods that are not prefixed by an underscore if the printer is in
    verbose mode.
    """

    def __init__(self, output, verbose=False, max_width=79, newline='\n',
        singleton_pprinters=None, type_pprinters=None, deferred_pprinters=None,
        max_seq_length=MAX_SEQ_LENGTH):

        PrettyPrinter.__init__(self, output, max_width, newline, max_seq_length=max_seq_length)
        self.verbose = verbose
        self.stack = []
        if singleton_pprinters is None:
            singleton_pprinters = _singleton_pprinters.copy()
        self.singleton_pprinters = singleton_pprinters
        if type_pprinters is None:
            type_pprinters = _type_pprinters.copy()
        self.type_pprinters = type_pprinters
        if deferred_pprinters is None:
            deferred_pprinters = _deferred_type_pprinters.copy()
        self.deferred_pprinters = deferred_pprinters

    def pretty(self, obj):
        """Pretty print the given object."""
        obj_id = id(obj)
        cycle = obj_id in self.stack
        self.stack.append(obj_id)
        self.begin_group()
        try:
            obj_class = _safe_getattr(obj, '__class__', None) or type(obj)
            # First try to find registered singleton printers for the type.
            try:
                printer = self.singleton_pprinters[obj_id]
            except (TypeError, KeyError):
                pass
            else:
                return printer(obj, self, cycle)
            # Next walk the mro and check for either:
            #   1) a registered printer
            #   2) a _repr_pretty_ method
            for cls in _get_mro(obj_class):
                if cls in self.type_pprinters:
                    # printer registered in self.type_pprinters
                    return self.type_pprinters[cls](obj, self, cycle)
                else:
                    # deferred printer
                    printer = self._in_deferred_types(cls)
                    if printer is not None:
                        return printer(obj, self, cycle)
                    else:
                        # Finally look for special method names.
                        # Some objects automatically create any requested
                        # attribute. Try to ignore most of them by checking for
                        # callability.
                        if '_repr_pretty_' in cls.__dict__:
                            meth = cls._repr_pretty_
                            if callable(meth):
                                return meth(obj, self, cycle)
                        if (
                            cls is not object
                            # check if cls defines __repr__
                            and "__repr__" in cls.__dict__
                            # check if __repr__ is callable.
                            # Note: we need to test getattr(cls, '__repr__')
                            #   instead of cls.__dict__['__repr__']
                            #   in order to work with descriptors like partialmethod,
                            and callable(_safe_getattr(cls, "__repr__", None))
                        ):
                            return _repr_pprint(obj, self, cycle)

            return _default_pprint(obj, self, cycle)
        finally:
            self.end_group()
            self.stack.pop()

    def _in_deferred_types(self, cls):
        """
        Check if the given class is specified in the deferred type registry.

        Returns the printer from the registry if it exists, and None if the
        class is not in the registry. Successful matches will be moved to the
        regular type registry for future use.
        """
        mod = _safe_getattr(cls, '__module__', None)
        name = _safe_getattr(cls, '__name__', None)
        key = (mod, name)
        printer = None
        if key in self.deferred_pprinters:
            # Move the printer over to the regular registry.
            printer = self.deferred_pprinters.pop(key)
            self.type_pprinters[cls] = printer
        return printer


class Printable:

    def output(self, stream, output_width):
        return output_width


class Text(Printable):

    def __init__(self):
        self.objs = []
        self.width = 0

    def output(self, stream, output_width):
        for obj in self.objs:
            stream.write(obj)
        return output_width + self.width

    def add(self, obj, width):
        self.objs.append(obj)
        self.width += width


class Breakable(Printable):

    def __init__(self, seq, width, pretty):
        self.obj = seq
        self.width = width
        self.pretty = pretty
        self.indentation = pretty.indentation
        self.group = pretty.group_stack[-1]
        self.group.breakables.append(self)

    def output(self, stream, output_width):
        self.group.breakables.popleft()
        if self.group.want_break:
            stream.write(self.pretty.newline)
            stream.write(' ' * self.indentation)
            return self.indentation
        if not self.group.breakables:
            self.pretty.group_queue.remove(self.group)
        stream.write(self.obj)
        return output_width + self.width


class Group(Printable):

    def __init__(self, depth):
        self.depth = depth
        self.breakables = deque()
        self.want_break = False


class GroupQueue:

    def __init__(self, *groups):
        self.queue = []
        for group in groups:
            self.enq(group)

    def enq(self, group):
        depth = group.depth
        while depth > len(self.queue) - 1:
            self.queue.append([])
        self.queue[depth].append(group)

    def deq(self):
        for stack in self.queue:
            for idx, group in enumerate(reversed(stack)):
                if group.breakables:
                    del stack[idx]
                    group.want_break = True
                    return group
            for group in stack:
                group.want_break = True
            del stack[:]

    def remove(self, group):
        try:
            self.queue[group.depth].remove(group)
        except ValueError:
            pass


class RawText:
    """ Object such that ``p.pretty(RawText(value))`` is the same as ``p.text(value)``.

    An example usage of this would be to show a list as binary numbers, using
    ``p.pretty([RawText(bin(i)) for i in integers])``.
    """
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        p.text(self.value)


class CallExpression:
    """ Object which emits a line-wrapped call expression in the form `__name(*args, **kwargs)` """
    def __init__(__self, __name, *args, **kwargs):
        # dunders are to avoid clashes with kwargs, as python's name managing
        # will kick in.
        self = __self
        self.name = __name
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def factory(cls, name):
        def inner(*args, **kwargs):
            return cls(name, *args, **kwargs)
        return inner

    def _repr_pretty_(self, p, cycle):
        # dunders are to avoid clashes with kwargs, as python's name managing
        # will kick in.

        started = False
        def new_item():
            nonlocal started
            if started:
                p.text(",")
                p.breakable()
            started = True

        prefix = self.name + "("
        with p.group(len(prefix), prefix, ")"):
            for arg in self.args:
                new_item()
                p.pretty(arg)
            for arg_name, arg in self.kwargs.items():
                new_item()
                arg_prefix = arg_name + "="
                with p.group(len(arg_prefix), arg_prefix):
                    p.pretty(arg)


class RawStringLiteral:
    """ Wrapper that shows a string with a `r` prefix """
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        base_repr = repr(self.value)
        if base_repr[:1] in 'uU':
            base_repr = base_repr[1:]
            prefix = 'ur'
        else:
            prefix = 'r'
        base_repr = prefix + base_repr.replace('\\\\', '\\')
        p.text(base_repr)


def _default_pprint(obj, p, cycle):
    """
    The default print function.  Used if an object does not provide one and
    it's none of the builtin objects.
    """
    klass = _safe_getattr(obj, '__class__', None) or type(obj)
    if _safe_getattr(klass, '__repr__', None) is not object.__repr__:
        # A user-provided repr. Find newlines and replace them with p.break_()
        _repr_pprint(obj, p, cycle)
        return
    p.begin_group(1, '<')
    p.pretty(klass)
    p.text(' at 0x%x' % id(obj))
    if cycle:
        p.text(' ...')
    elif p.verbose:
        first = True
        for key in dir(obj):
            if not key.startswith('_'):
                try:
                    value = getattr(obj, key)
                except AttributeError:
                    continue
                if isinstance(value, types.MethodType):
                    continue
                if not first:
                    p.text(',')
                p.breakable()
                p.text(key)
                p.text('=')
                step = len(key) + 1
                p.indentation += step
                p.pretty(value)
                p.indentation -= step
                first = False
    p.end_group(1, '>')


def _seq_pprinter_factory(start, end):
    """
    Factory that returns a pprint function useful for sequences.  Used by
    the default pprint for tuples and lists.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text(start + '...' + end)
        step = len(start)
        p.begin_group(step, start)
        for idx, x in p._enumerate(obj):
            if idx:
                p.text(',')
                p.breakable()
            p.pretty(x)
        if len(obj) == 1 and isinstance(obj, tuple):
            # Special case for 1-item tuples.
            p.text(',')
        p.end_group(step, end)
    return inner


def _set_pprinter_factory(start, end):
    """
    Factory that returns a pprint function useful for sets and frozensets.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text(start + '...' + end)
        if len(obj) == 0:
            # Special case.
            p.text(type(obj).__name__ + '()')
        else:
            step = len(start)
            p.begin_group(step, start)
            # Like dictionary keys, we will try to sort the items if there aren't too many
            if not (p.max_seq_length and len(obj) >= p.max_seq_length):
                items = _sorted_for_pprint(obj)
            else:
                items = obj
            for idx, x in p._enumerate(items):
                if idx:
                    p.text(',')
                    p.breakable()
                p.pretty(x)
            p.end_group(step, end)
    return inner


def _dict_pprinter_factory(start, end):
    """
    Factory that returns a pprint function used by the default pprint of
    dicts and dict proxies.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text('{...}')
        step = len(start)
        p.begin_group(step, start)
        keys = obj.keys()
        for idx, key in p._enumerate(keys):
            if idx:
                p.text(',')
                p.breakable()
            p.pretty(key)
            p.text(': ')
            p.pretty(obj[key])
        p.end_group(step, end)
    return inner


def _super_pprint(obj, p, cycle):
    """The pprint for the super type."""
    p.begin_group(8, '<super: ')
    p.pretty(obj.__thisclass__)
    p.text(',')
    p.breakable()
    if PYPY: # In PyPy, super() objects don't have __self__ attributes
        dself = obj.__repr__.__self__
        p.pretty(None if dself is obj else dself)
    else:
        p.pretty(obj.__self__)
    p.end_group(8, '>')



class _ReFlags:
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        done_one = False
        for flag in (
            "IGNORECASE",
            "LOCALE",
            "MULTILINE",
            "DOTALL",
            "UNICODE",
            "VERBOSE",
            "DEBUG",
        ):
            if self.value & getattr(re, flag):
                if done_one:
                    p.text('|')
                p.text('re.' + flag)
                done_one = True


def _re_pattern_pprint(obj, p, cycle):
    """The pprint function for regular expression patterns."""
    re_compile = CallExpression.factory('re.compile')
    if obj.flags:
        p.pretty(re_compile(RawStringLiteral(obj.pattern), _ReFlags(obj.flags)))
    else:
        p.pretty(re_compile(RawStringLiteral(obj.pattern)))


def _types_simplenamespace_pprint(obj, p, cycle):
    """The pprint function for types.SimpleNamespace."""
    namespace = CallExpression.factory('namespace')
    if cycle:
        p.pretty(namespace(RawText("...")))
    else:
        p.pretty(namespace(**obj.__dict__))


def _type_pprint(obj, p, cycle):
    """The pprint for classes and types."""
    # Heap allocated types might not have the module attribute,
    # and others may set it to None.

    # Checks for a __repr__ override in the metaclass. Can't compare the
    # type(obj).__repr__ directly because in PyPy the representation function
    # inherited from type isn't the same type.__repr__
    if [m for m in _get_mro(type(obj)) if "__repr__" in vars(m)][:1] != [type]:
        _repr_pprint(obj, p, cycle)
        return

    mod = _safe_getattr(obj, '__module__', None)
    try:
        name = obj.__qualname__
        if not isinstance(name, str):
            # This can happen if the type implements __qualname__ as a property
            # or other descriptor in Python 2.
            raise Exception("Try __name__")
    except Exception:
        name = obj.__name__
        if not isinstance(name, str):
            name = '<unknown type>'

    if mod in (None, '__builtin__', 'builtins', 'exceptions'):
        p.text(name)
    else:
        p.text(mod + '.' + name)


def _repr_pprint(obj, p, cycle):
    """A pprint that just redirects to the normal repr function."""
    # Find newlines and replace them with p.break_()
    output = repr(obj)
    lines = output.splitlines()
    with p.group():
        for idx, output_line in enumerate(lines):
            if idx:
                p.break_()
            p.text(output_line)


def _function_pprint(obj, p, cycle):
    """Base pprint for all functions and builtin functions."""
    name = _safe_getattr(obj, '__qualname__', obj.__name__)
    mod = obj.__module__
    if mod and mod not in ('__builtin__', 'builtins', 'exceptions'):
        name = mod + '.' + name
    try:
       func_def = name + str(signature(obj))
    except ValueError:
       func_def = name
    p.text('<function %s>' % func_def)


def _exception_pprint(obj, p, cycle):
    """Base pprint for all exceptions."""
    name = getattr(obj.__class__, '__qualname__', obj.__class__.__name__)
    if obj.__class__.__module__ not in ('exceptions', 'builtins'):
        name = '%s.%s' % (obj.__class__.__module__, name)

    p.pretty(CallExpression(name, *getattr(obj, 'args', ())))


#: the exception base
_exception_base: type
try:
    _exception_base = BaseException
except NameError:
    _exception_base = Exception


#: printers for builtin types
_type_pprinters = {
    int:                        _repr_pprint,
    float:                      _repr_pprint,
    str:                        _repr_pprint,
    tuple:                      _seq_pprinter_factory('(', ')'),
    list:                       _seq_pprinter_factory('[', ']'),
    dict:                       _dict_pprinter_factory('{', '}'),
    set:                        _set_pprinter_factory('{', '}'),
    frozenset:                  _set_pprinter_factory('frozenset({', '})'),
    super:                      _super_pprint,
    _re_pattern_type:           _re_pattern_pprint,
    type:                       _type_pprint,
    types.FunctionType:         _function_pprint,
    types.BuiltinFunctionType:  _function_pprint,
    types.MethodType:           _repr_pprint,
    types.SimpleNamespace:      _types_simplenamespace_pprint,
    datetime.datetime:          _repr_pprint,
    datetime.timedelta:         _repr_pprint,
    _exception_base:            _exception_pprint
}

# render os.environ like a dict
_env_type = type(os.environ)
# future-proof in case os.environ becomes a plain dict?
if _env_type is not dict:
    _type_pprinters[_env_type] = _dict_pprinter_factory('environ{', '}')

_type_pprinters[types.MappingProxyType] = _dict_pprinter_factory("mappingproxy({", "})")
_type_pprinters[slice] = _repr_pprint

_type_pprinters[range] = _repr_pprint
_type_pprinters[bytes] = _repr_pprint

#: printers for types specified by name
_deferred_type_pprinters: Dict = {}


def for_type(typ, func):
    """
    Add a pretty printer for a given type.
    """
    oldfunc = _type_pprinters.get(typ, None)
    if func is not None:
        # To support easy restoration of old pprinters, we need to ignore Nones.
        _type_pprinters[typ] = func
    return oldfunc

def for_type_by_name(type_module, type_name, func):
    """
    Add a pretty printer for a type specified by the module and name of a type
    rather than the type object itself.
    """
    key = (type_module, type_name)
    oldfunc = _deferred_type_pprinters.get(key, None)
    if func is not None:
        # To support easy restoration of old pprinters, we need to ignore Nones.
        _deferred_type_pprinters[key] = func
    return oldfunc


#: printers for the default singletons
_singleton_pprinters = dict.fromkeys(map(id, [None, True, False, Ellipsis,
                                      NotImplemented]), _repr_pprint)


def _defaultdict_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    else:
        p.pretty(cls_ctor(obj.default_factory, dict(obj)))

def _ordereddict_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif len(obj):
        p.pretty(cls_ctor(list(obj.items())))
    else:
        p.pretty(cls_ctor())

def _deque_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif obj.maxlen is not None:
        p.pretty(cls_ctor(list(obj), maxlen=obj.maxlen))
    else:
        p.pretty(cls_ctor(list(obj)))

def _counter_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif len(obj):
        p.pretty(cls_ctor(dict(obj.most_common())))
    else:
        p.pretty(cls_ctor())


def _userlist_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    else:
        p.pretty(cls_ctor(obj.data))


for_type_by_name('collections', 'defaultdict', _defaultdict_pprint)
for_type_by_name('collections', 'OrderedDict', _ordereddict_pprint)
for_type_by_name('collections', 'deque', _deque_pprint)
for_type_by_name('collections', 'Counter', _counter_pprint)
for_type_by_name("collections", "UserList", _userlist_pprint)

if __name__ == '__main__':
    from random import randrange

    class Foo:
        def __init__(self):
            self.foo = 1
            self.bar = re.compile(r'\s+')
            self.blub = dict.fromkeys(range(30), randrange(1, 40))
            self.hehe = 23424.234234
            self.list = ["blub", "blah", self]

        def get_foo(self):
            print("foo")

    pprint(Foo(), verbose=True)

# === NexusCore/src\dev_tools\test_openai_connection.py ===
# test_openai_connection.py
import os
from openai import OpenAI
from dotenv import load_dotenv

# .env から APIキーを読み込み
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ .env に OPENAI_API_KEY が定義されていません。")
    exit(1)

client = OpenAI(api_key=api_key)

# GPT-4 に簡単な質問を送信して動作確認
try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": "こんにちは！APIは正常に動いていますか？"}
        ]
    )
    print("✅ 接続成功！レスポンス：\n")
    print(response.choices[0].message.content)

except Exception as e:
    print(f"❌ エラーが発生しました：{e}")

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\dev_tools\test_openai_connection.py ===
# test_openai_connection.py
import os
from openai import OpenAI
from dotenv import load_dotenv

# .env から APIキーを読み込み
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ .env に OPENAI_API_KEY が定義されていません。")
    exit(1)

client = OpenAI(api_key=api_key)

# GPT-4 に簡単な質問を送信して動作確認
try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": "こんにちは！APIは正常に動いていますか？"}
        ]
    )
    print("✅ 接続成功！レスポンス：\n")
    print(response.choices[0].message.content)

except Exception as e:
    print(f"❌ エラーが発生しました：{e}")

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\dev_tools\test_openai_connection.py ===
# test_openai_connection.py
import os
from openai import OpenAI
from dotenv import load_dotenv

# .env から APIキーを読み込み
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ .env に OPENAI_API_KEY が定義されていません。")
    exit(1)

client = OpenAI(api_key=api_key)

# GPT-4 に簡単な質問を送信して動作確認
try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": "こんにちは！APIは正常に動いていますか？"}
        ]
    )
    print("✅ 接続成功！レスポンス：\n")
    print(response.choices[0].message.content)

except Exception as e:
    print(f"❌ エラーが発生しました：{e}")

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_iotools.py ===
"""A collection of functions designed to help I/O with ascii files.

"""
__docformat__ = "restructuredtext en"

import itertools

import numpy as np
import numpy._core.numeric as nx
from numpy._utils import asbytes, asunicode


def _decode_line(line, encoding=None):
    """Decode bytes from binary input streams.

    Defaults to decoding from 'latin1'.

    Parameters
    ----------
    line : str or bytes
         Line to be decoded.
    encoding : str
         Encoding used to decode `line`.

    Returns
    -------
    decoded_line : str

    """
    if type(line) is bytes:
        if encoding is None:
            encoding = "latin1"
        line = line.decode(encoding)

    return line


def _is_string_like(obj):
    """
    Check whether obj behaves like a string.
    """
    try:
        obj + ''
    except (TypeError, ValueError):
        return False
    return True


def _is_bytes_like(obj):
    """
    Check whether obj behaves like a bytes object.
    """
    try:
        obj + b''
    except (TypeError, ValueError):
        return False
    return True


def has_nested_fields(ndtype):
    """
    Returns whether one or several fields of a dtype are nested.

    Parameters
    ----------
    ndtype : dtype
        Data-type of a structured array.

    Raises
    ------
    AttributeError
        If `ndtype` does not have a `names` attribute.

    Examples
    --------
    >>> import numpy as np
    >>> dt = np.dtype([('name', 'S4'), ('x', float), ('y', float)])
    >>> np.lib._iotools.has_nested_fields(dt)
    False

    """
    return any(ndtype[name].names is not None for name in ndtype.names or ())


def flatten_dtype(ndtype, flatten_base=False):
    """
    Unpack a structured data-type by collapsing nested fields and/or fields
    with a shape.

    Note that the field names are lost.

    Parameters
    ----------
    ndtype : dtype
        The datatype to collapse
    flatten_base : bool, optional
       If True, transform a field with a shape into several fields. Default is
       False.

    Examples
    --------
    >>> import numpy as np
    >>> dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
    ...                ('block', int, (2, 3))])
    >>> np.lib._iotools.flatten_dtype(dt)
    [dtype('S4'), dtype('float64'), dtype('float64'), dtype('int64')]
    >>> np.lib._iotools.flatten_dtype(dt, flatten_base=True)
    [dtype('S4'),
     dtype('float64'),
     dtype('float64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64')]

    """
    names = ndtype.names
    if names is None:
        if flatten_base:
            return [ndtype.base] * int(np.prod(ndtype.shape))
        return [ndtype.base]
    else:
        types = []
        for field in names:
            info = ndtype.fields[field]
            flat_dt = flatten_dtype(info[0], flatten_base)
            types.extend(flat_dt)
        return types


class LineSplitter:
    """
    Object to split a string at a given delimiter or at given places.

    Parameters
    ----------
    delimiter : str, int, or sequence of ints, optional
        If a string, character used to delimit consecutive fields.
        If an integer or a sequence of integers, width(s) of each field.
    comments : str, optional
        Character used to mark the beginning of a comment. Default is '#'.
    autostrip : bool, optional
        Whether to strip each individual field. Default is True.

    """

    def autostrip(self, method):
        """
        Wrapper to strip each member of the output of `method`.

        Parameters
        ----------
        method : function
            Function that takes a single argument and returns a sequence of
            strings.

        Returns
        -------
        wrapped : function
            The result of wrapping `method`. `wrapped` takes a single input
            argument and returns a list of strings that are stripped of
            white-space.

        """
        return lambda input: [_.strip() for _ in method(input)]

    def __init__(self, delimiter=None, comments='#', autostrip=True,
                 encoding=None):
        delimiter = _decode_line(delimiter)
        comments = _decode_line(comments)

        self.comments = comments

        # Delimiter is a character
        if (delimiter is None) or isinstance(delimiter, str):
            delimiter = delimiter or None
            _handyman = self._delimited_splitter
        # Delimiter is a list of field widths
        elif hasattr(delimiter, '__iter__'):
            _handyman = self._variablewidth_splitter
            idx = np.cumsum([0] + list(delimiter))
            delimiter = [slice(i, j) for (i, j) in itertools.pairwise(idx)]
        # Delimiter is a single integer
        elif int(delimiter):
            (_handyman, delimiter) = (
                    self._fixedwidth_splitter, int(delimiter))
        else:
            (_handyman, delimiter) = (self._delimited_splitter, None)
        self.delimiter = delimiter
        if autostrip:
            self._handyman = self.autostrip(_handyman)
        else:
            self._handyman = _handyman
        self.encoding = encoding

    def _delimited_splitter(self, line):
        """Chop off comments, strip, and split at delimiter. """
        if self.comments is not None:
            line = line.split(self.comments)[0]
        line = line.strip(" \r\n")
        if not line:
            return []
        return line.split(self.delimiter)

    def _fixedwidth_splitter(self, line):
        if self.comments is not None:
            line = line.split(self.comments)[0]
        line = line.strip("\r\n")
        if not line:
            return []
        fixed = self.delimiter
        slices = [slice(i, i + fixed) for i in range(0, len(line), fixed)]
        return [line[s] for s in slices]

    def _variablewidth_splitter(self, line):
        if self.comments is not None:
            line = line.split(self.comments)[0]
        if not line:
            return []
        slices = self.delimiter
        return [line[s] for s in slices]

    def __call__(self, line):
        return self._handyman(_decode_line(line, self.encoding))


class NameValidator:
    """
    Object to validate a list of strings to use as field names.

    The strings are stripped of any non alphanumeric character, and spaces
    are replaced by '_'. During instantiation, the user can define a list
    of names to exclude, as well as a list of invalid characters. Names in
    the exclusion list are appended a '_' character.

    Once an instance has been created, it can be called with a list of
    names, and a list of valid names will be created.  The `__call__`
    method accepts an optional keyword "default" that sets the default name
    in case of ambiguity. By default this is 'f', so that names will
    default to `f0`, `f1`, etc.

    Parameters
    ----------
    excludelist : sequence, optional
        A list of names to exclude. This list is appended to the default
        list ['return', 'file', 'print']. Excluded names are appended an
        underscore: for example, `file` becomes `file_` if supplied.
    deletechars : str, optional
        A string combining invalid characters that must be deleted from the
        names.
    case_sensitive : {True, False, 'upper', 'lower'}, optional
        * If True, field names are case-sensitive.
        * If False or 'upper', field names are converted to upper case.
        * If 'lower', field names are converted to lower case.

        The default value is True.
    replace_space : '_', optional
        Character(s) used in replacement of white spaces.

    Notes
    -----
    Calling an instance of `NameValidator` is the same as calling its
    method `validate`.

    Examples
    --------
    >>> import numpy as np
    >>> validator = np.lib._iotools.NameValidator()
    >>> validator(['file', 'field2', 'with space', 'CaSe'])
    ('file_', 'field2', 'with_space', 'CaSe')

    >>> validator = np.lib._iotools.NameValidator(excludelist=['excl'],
    ...                                           deletechars='q',
    ...                                           case_sensitive=False)
    >>> validator(['excl', 'field2', 'no_q', 'with space', 'CaSe'])
    ('EXCL', 'FIELD2', 'NO_Q', 'WITH_SPACE', 'CASE')

    """

    defaultexcludelist = 'return', 'file', 'print'
    defaultdeletechars = frozenset(r"""~!@#$%^&*()-=+~\|]}[{';: /?.>,<""")

    def __init__(self, excludelist=None, deletechars=None,
                 case_sensitive=None, replace_space='_'):
        # Process the exclusion list ..
        if excludelist is None:
            excludelist = []
        excludelist.extend(self.defaultexcludelist)
        self.excludelist = excludelist
        # Process the list of characters to delete
        if deletechars is None:
            delete = set(self.defaultdeletechars)
        else:
            delete = set(deletechars)
        delete.add('"')
        self.deletechars = delete
        # Process the case option .....
        if (case_sensitive is None) or (case_sensitive is True):
            self.case_converter = lambda x: x
        elif (case_sensitive is False) or case_sensitive.startswith('u'):
            self.case_converter = lambda x: x.upper()
        elif case_sensitive.startswith('l'):
            self.case_converter = lambda x: x.lower()
        else:
            msg = f'unrecognized case_sensitive value {case_sensitive}.'
            raise ValueError(msg)

        self.replace_space = replace_space

    def validate(self, names, defaultfmt="f%i", nbfields=None):
        """
        Validate a list of strings as field names for a structured array.

        Parameters
        ----------
        names : sequence of str
            Strings to be validated.
        defaultfmt : str, optional
            Default format string, used if validating a given string
            reduces its length to zero.
        nbfields : integer, optional
            Final number of validated names, used to expand or shrink the
            initial list of names.

        Returns
        -------
        validatednames : list of str
            The list of validated field names.

        Notes
        -----
        A `NameValidator` instance can be called directly, which is the
        same as calling `validate`. For examples, see `NameValidator`.

        """
        # Initial checks ..............
        if (names is None):
            if (nbfields is None):
                return None
            names = []
        if isinstance(names, str):
            names = [names, ]
        if nbfields is not None:
            nbnames = len(names)
            if (nbnames < nbfields):
                names = list(names) + [''] * (nbfields - nbnames)
            elif (nbnames > nbfields):
                names = names[:nbfields]
        # Set some shortcuts ...........
        deletechars = self.deletechars
        excludelist = self.excludelist
        case_converter = self.case_converter
        replace_space = self.replace_space
        # Initializes some variables ...
        validatednames = []
        seen = {}
        nbempty = 0

        for item in names:
            item = case_converter(item).strip()
            if replace_space:
                item = item.replace(' ', replace_space)
            item = ''.join([c for c in item if c not in deletechars])
            if item == '':
                item = defaultfmt % nbempty
                while item in names:
                    nbempty += 1
                    item = defaultfmt % nbempty
                nbempty += 1
            elif item in excludelist:
                item += '_'
            cnt = seen.get(item, 0)
            if cnt > 0:
                validatednames.append(item + '_%d' % cnt)
            else:
                validatednames.append(item)
            seen[item] = cnt + 1
        return tuple(validatednames)

    def __call__(self, names, defaultfmt="f%i", nbfields=None):
        return self.validate(names, defaultfmt=defaultfmt, nbfields=nbfields)


def str2bool(value):
    """
    Tries to transform a string supposed to represent a boolean to a boolean.

    Parameters
    ----------
    value : str
        The string that is transformed to a boolean.

    Returns
    -------
    boolval : bool
        The boolean representation of `value`.

    Raises
    ------
    ValueError
        If the string is not 'True' or 'False' (case independent)

    Examples
    --------
    >>> import numpy as np
    >>> np.lib._iotools.str2bool('TRUE')
    True
    >>> np.lib._iotools.str2bool('false')
    False

    """
    value = value.upper()
    if value == 'TRUE':
        return True
    elif value == 'FALSE':
        return False
    else:
        raise ValueError("Invalid boolean")


class ConverterError(Exception):
    """
    Exception raised when an error occurs in a converter for string values.

    """
    pass


class ConverterLockError(ConverterError):
    """
    Exception raised when an attempt is made to upgrade a locked converter.

    """
    pass


class ConversionWarning(UserWarning):
    """
    Warning issued when a string converter has a problem.

    Notes
    -----
    In `genfromtxt` a `ConversionWarning` is issued if raising exceptions
    is explicitly suppressed with the "invalid_raise" keyword.

    """
    pass


class StringConverter:
    """
    Factory class for function transforming a string into another object
    (int, float).

    After initialization, an instance can be called to transform a string
    into another object. If the string is recognized as representing a
    missing value, a default value is returned.

    Attributes
    ----------
    func : function
        Function used for the conversion.
    default : any
        Default value to return when the input corresponds to a missing
        value.
    type : type
        Type of the output.
    _status : int
        Integer representing the order of the conversion.
    _mapper : sequence of tuples
        Sequence of tuples (dtype, function, default value) to evaluate in
        order.
    _locked : bool
        Holds `locked` parameter.

    Parameters
    ----------
    dtype_or_func : {None, dtype, function}, optional
        If a `dtype`, specifies the input data type, used to define a basic
        function and a default value for missing data. For example, when
        `dtype` is float, the `func` attribute is set to `float` and the
        default value to `np.nan`.  If a function, this function is used to
        convert a string to another object. In this case, it is recommended
        to give an associated default value as input.
    default : any, optional
        Value to return by default, that is, when the string to be
        converted is flagged as missing. If not given, `StringConverter`
        tries to supply a reasonable default value.
    missing_values : {None, sequence of str}, optional
        ``None`` or sequence of strings indicating a missing value. If ``None``
        then missing values are indicated by empty entries. The default is
        ``None``.
    locked : bool, optional
        Whether the StringConverter should be locked to prevent automatic
        upgrade or not. Default is False.

    """
    _mapper = [(nx.bool, str2bool, False),
               (nx.int_, int, -1),]

    # On 32-bit systems, we need to make sure that we explicitly include
    # nx.int64 since ns.int_ is nx.int32.
    if nx.dtype(nx.int_).itemsize < nx.dtype(nx.int64).itemsize:
        _mapper.append((nx.int64, int, -1))

    _mapper.extend([(nx.float64, float, nx.nan),
                    (nx.complex128, complex, nx.nan + 0j),
                    (nx.longdouble, nx.longdouble, nx.nan),
                    # If a non-default dtype is passed, fall back to generic
                    # ones (should only be used for the converter)
                    (nx.integer, int, -1),
                    (nx.floating, float, nx.nan),
                    (nx.complexfloating, complex, nx.nan + 0j),
                    # Last, try with the string types (must be last, because
                    # `_mapper[-1]` is used as default in some cases)
                    (nx.str_, asunicode, '???'),
                    (nx.bytes_, asbytes, '???'),
                    ])

    @classmethod
    def _getdtype(cls, val):
        """Returns the dtype of the input variable."""
        return np.array(val).dtype

    @classmethod
    def _getsubdtype(cls, val):
        """Returns the type of the dtype of the input variable."""
        return np.array(val).dtype.type

    @classmethod
    def _dtypeortype(cls, dtype):
        """Returns dtype for datetime64 and type of dtype otherwise."""

        # This is a bit annoying. We want to return the "general" type in most
        # cases (ie. "string" rather than "S10"), but we want to return the
        # specific type for datetime64 (ie. "datetime64[us]" rather than
        # "datetime64").
        if dtype.type == np.datetime64:
            return dtype
        return dtype.type

    @classmethod
    def upgrade_mapper(cls, func, default=None):
        """
        Upgrade the mapper of a StringConverter by adding a new function and
        its corresponding default.

        The input function (or sequence of functions) and its associated
        default value (if any) is inserted in penultimate position of the
        mapper.  The corresponding type is estimated from the dtype of the
        default value.

        Parameters
        ----------
        func : var
            Function, or sequence of functions

        Examples
        --------
        >>> import dateutil.parser
        >>> import datetime
        >>> dateparser = dateutil.parser.parse
        >>> defaultdate = datetime.date(2000, 1, 1)
        >>> StringConverter.upgrade_mapper(dateparser, default=defaultdate)
        """
        # Func is a single functions
        if callable(func):
            cls._mapper.insert(-1, (cls._getsubdtype(default), func, default))
            return
        elif hasattr(func, '__iter__'):
            if isinstance(func[0], (tuple, list)):
                for _ in func:
                    cls._mapper.insert(-1, _)
                return
            if default is None:
                default = [None] * len(func)
            else:
                default = list(default)
                default.append([None] * (len(func) - len(default)))
            for fct, dft in zip(func, default):
                cls._mapper.insert(-1, (cls._getsubdtype(dft), fct, dft))

    @classmethod
    def _find_map_entry(cls, dtype):
        # if a converter for the specific dtype is available use that
        for i, (deftype, func, default_def) in enumerate(cls._mapper):
            if dtype.type == deftype:
                return i, (deftype, func, default_def)

        # otherwise find an inexact match
        for i, (deftype, func, default_def) in enumerate(cls._mapper):
            if np.issubdtype(dtype.type, deftype):
                return i, (deftype, func, default_def)

        raise LookupError

    def __init__(self, dtype_or_func=None, default=None, missing_values=None,
                 locked=False):
        # Defines a lock for upgrade
        self._locked = bool(locked)
        # No input dtype: minimal initialization
        if dtype_or_func is None:
            self.func = str2bool
            self._status = 0
            self.default = default or False
            dtype = np.dtype('bool')
        else:
            # Is the input a np.dtype ?
            try:
                self.func = None
                dtype = np.dtype(dtype_or_func)
            except TypeError:
                # dtype_or_func must be a function, then
                if not callable(dtype_or_func):
                    errmsg = ("The input argument `dtype` is neither a"
                              " function nor a dtype (got '%s' instead)")
                    raise TypeError(errmsg % type(dtype_or_func))
                # Set the function
                self.func = dtype_or_func
                # If we don't have a default, try to guess it or set it to
                # None
                if default is None:
                    try:
                        default = self.func('0')
                    except ValueError:
                        default = None
                dtype = self._getdtype(default)

            # find the best match in our mapper
            try:
                self._status, (_, func, default_def) = self._find_map_entry(dtype)
            except LookupError:
                # no match
                self.default = default
                _, func, _ = self._mapper[-1]
                self._status = 0
            else:
                # use the found default only if we did not already have one
                if default is None:
                    self.default = default_def
                else:
                    self.default = default

            # If the input was a dtype, set the function to the last we saw
            if self.func is None:
                self.func = func

            # If the status is 1 (int), change the function to
            # something more robust.
            if self.func == self._mapper[1][1]:
                if issubclass(dtype.type, np.uint64):
                    self.func = np.uint64
                elif issubclass(dtype.type, np.int64):
                    self.func = np.int64
                else:
                    self.func = lambda x: int(float(x))
        # Store the list of strings corresponding to missing values.
        if missing_values is None:
            self.missing_values = {''}
        else:
            if isinstance(missing_values, str):
                missing_values = missing_values.split(",")
            self.missing_values = set(list(missing_values) + [''])

        self._callingfunction = self._strict_call
        self.type = self._dtypeortype(dtype)
        self._checked = False
        self._initial_default = default

    def _loose_call(self, value):
        try:
            return self.func(value)
        except ValueError:
            return self.default

    def _strict_call(self, value):
        try:

            # We check if we can convert the value using the current function
            new_value = self.func(value)

            # In addition to having to check whether func can convert the
            # value, we also have to make sure that we don't get overflow
            # errors for integers.
            if self.func is int:
                try:
                    np.array(value, dtype=self.type)
                except OverflowError:
                    raise ValueError

            # We're still here so we can now return the new value
            return new_value

        except ValueError:
            if value.strip() in self.missing_values:
                if not self._status:
                    self._checked = False
                return self.default
            raise ValueError(f"Cannot convert string '{value}'")

    def __call__(self, value):
        return self._callingfunction(value)

    def _do_upgrade(self):
        # Raise an exception if we locked the converter...
        if self._locked:
            errmsg = "Converter is locked and cannot be upgraded"
            raise ConverterLockError(errmsg)
        _statusmax = len(self._mapper)
        # Complains if we try to upgrade by the maximum
        _status = self._status
        if _status == _statusmax:
            errmsg = "Could not find a valid conversion function"
            raise ConverterError(errmsg)
        elif _status < _statusmax - 1:
            _status += 1
        self.type, self.func, default = self._mapper[_status]
        self._status = _status
        if self._initial_default is not None:
            self.default = self._initial_default
        else:
            self.default = default

    def upgrade(self, value):
        """
        Find the best converter for a given string, and return the result.

        The supplied string `value` is converted by testing different
        converters in order. First the `func` method of the
        `StringConverter` instance is tried, if this fails other available
        converters are tried.  The order in which these other converters
        are tried is determined by the `_status` attribute of the instance.

        Parameters
        ----------
        value : str
            The string to convert.

        Returns
        -------
        out : any
            The result of converting `value` with the appropriate converter.

        """
        self._checked = True
        try:
            return self._strict_call(value)
        except ValueError:
            self._do_upgrade()
            return self.upgrade(value)

    def iterupgrade(self, value):
        self._checked = True
        if not hasattr(value, '__iter__'):
            value = (value,)
        _strict_call = self._strict_call
        try:
            for _m in value:
                _strict_call(_m)
        except ValueError:
            self._do_upgrade()
            self.iterupgrade(value)

    def update(self, func, default=None, testing_value=None,
               missing_values='', locked=False):
        """
        Set StringConverter attributes directly.

        Parameters
        ----------
        func : function
            Conversion function.
        default : any, optional
            Value to return by default, that is, when the string to be
            converted is flagged as missing. If not given,
            `StringConverter` tries to supply a reasonable default value.
        testing_value : str, optional
            A string representing a standard input value of the converter.
            This string is used to help defining a reasonable default
            value.
        missing_values : {sequence of str, None}, optional
            Sequence of strings indicating a missing value. If ``None``, then
            the existing `missing_values` are cleared. The default is ``''``.
        locked : bool, optional
            Whether the StringConverter should be locked to prevent
            automatic upgrade or not. Default is False.

        Notes
        -----
        `update` takes the same parameters as the constructor of
        `StringConverter`, except that `func` does not accept a `dtype`
        whereas `dtype_or_func` in the constructor does.

        """
        self.func = func
        self._locked = locked

        # Don't reset the default to None if we can avoid it
        if default is not None:
            self.default = default
            self.type = self._dtypeortype(self._getdtype(default))
        else:
            try:
                tester = func(testing_value or '1')
            except (TypeError, ValueError):
                tester = None
            self.type = self._dtypeortype(self._getdtype(tester))

        # Add the missing values to the existing set or clear it.
        if missing_values is None:
            # Clear all missing values even though the ctor initializes it to
            # set(['']) when the argument is None.
            self.missing_values = set()
        else:
            if not np.iterable(missing_values):
                missing_values = [missing_values]
            if not all(isinstance(v, str) for v in missing_values):
                raise TypeError("missing_values must be strings or unicode")
            self.missing_values.update(missing_values)


def easy_dtype(ndtype, names=None, defaultfmt="f%i", **validationargs):
    """
    Convenience function to create a `np.dtype` object.

    The function processes the input `dtype` and matches it with the given
    names.

    Parameters
    ----------
    ndtype : var
        Definition of the dtype. Can be any string or dictionary recognized
        by the `np.dtype` function, or a sequence of types.
    names : str or sequence, optional
        Sequence of strings to use as field names for a structured dtype.
        For convenience, `names` can be a string of a comma-separated list
        of names.
    defaultfmt : str, optional
        Format string used to define missing names, such as ``"f%i"``
        (default) or ``"fields_%02i"``.
    validationargs : optional
        A series of optional arguments used to initialize a
        `NameValidator`.

    Examples
    --------
    >>> import numpy as np
    >>> np.lib._iotools.easy_dtype(float)
    dtype('float64')
    >>> np.lib._iotools.easy_dtype("i4, f8")
    dtype([('f0', '<i4'), ('f1', '<f8')])
    >>> np.lib._iotools.easy_dtype("i4, f8", defaultfmt="field_%03i")
    dtype([('field_000', '<i4'), ('field_001', '<f8')])

    >>> np.lib._iotools.easy_dtype((int, float, float), names="a,b,c")
    dtype([('a', '<i8'), ('b', '<f8'), ('c', '<f8')])
    >>> np.lib._iotools.easy_dtype(float, names="a,b,c")
    dtype([('a', '<f8'), ('b', '<f8'), ('c', '<f8')])

    """
    try:
        ndtype = np.dtype(ndtype)
    except TypeError:
        validate = NameValidator(**validationargs)
        nbfields = len(ndtype)
        if names is None:
            names = [''] * len(ndtype)
        elif isinstance(names, str):
            names = names.split(",")
        names = validate(names, nbfields=nbfields, defaultfmt=defaultfmt)
        ndtype = np.dtype({"formats": ndtype, "names": names})
    else:
        # Explicit names
        if names is not None:
            validate = NameValidator(**validationargs)
            if isinstance(names, str):
                names = names.split(",")
            # Simple dtype: repeat to match the nb of names
            if ndtype.names is None:
                formats = tuple([ndtype.type] * len(names))
                names = validate(names, defaultfmt=defaultfmt)
                ndtype = np.dtype(list(zip(names, formats)))
            # Structured dtype: just validate the names as needed
            else:
                ndtype.names = validate(names, nbfields=len(ndtype.names),
                                        defaultfmt=defaultfmt)
        # No implicit names
        elif ndtype.names is not None:
            validate = NameValidator(**validationargs)
            # Default initial names : should we change the format ?
            numbered_names = tuple(f"f{i}" for i in range(len(ndtype.names)))
            if ((ndtype.names == numbered_names) and (defaultfmt != "f%i")):
                ndtype.names = validate([''] * len(ndtype.names),
                                        defaultfmt=defaultfmt)
            # Explicit initial names : just validate
            else:
                ndtype.names = validate(ndtype.names, defaultfmt=defaultfmt)
    return ndtype

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_iotools.py ===
"""A collection of functions designed to help I/O with ascii files.

"""
__docformat__ = "restructuredtext en"

import itertools

import numpy as np
import numpy._core.numeric as nx
from numpy._utils import asbytes, asunicode


def _decode_line(line, encoding=None):
    """Decode bytes from binary input streams.

    Defaults to decoding from 'latin1'.

    Parameters
    ----------
    line : str or bytes
         Line to be decoded.
    encoding : str
         Encoding used to decode `line`.

    Returns
    -------
    decoded_line : str

    """
    if type(line) is bytes:
        if encoding is None:
            encoding = "latin1"
        line = line.decode(encoding)

    return line


def _is_string_like(obj):
    """
    Check whether obj behaves like a string.
    """
    try:
        obj + ''
    except (TypeError, ValueError):
        return False
    return True


def _is_bytes_like(obj):
    """
    Check whether obj behaves like a bytes object.
    """
    try:
        obj + b''
    except (TypeError, ValueError):
        return False
    return True


def has_nested_fields(ndtype):
    """
    Returns whether one or several fields of a dtype are nested.

    Parameters
    ----------
    ndtype : dtype
        Data-type of a structured array.

    Raises
    ------
    AttributeError
        If `ndtype` does not have a `names` attribute.

    Examples
    --------
    >>> import numpy as np
    >>> dt = np.dtype([('name', 'S4'), ('x', float), ('y', float)])
    >>> np.lib._iotools.has_nested_fields(dt)
    False

    """
    return any(ndtype[name].names is not None for name in ndtype.names or ())


def flatten_dtype(ndtype, flatten_base=False):
    """
    Unpack a structured data-type by collapsing nested fields and/or fields
    with a shape.

    Note that the field names are lost.

    Parameters
    ----------
    ndtype : dtype
        The datatype to collapse
    flatten_base : bool, optional
       If True, transform a field with a shape into several fields. Default is
       False.

    Examples
    --------
    >>> import numpy as np
    >>> dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
    ...                ('block', int, (2, 3))])
    >>> np.lib._iotools.flatten_dtype(dt)
    [dtype('S4'), dtype('float64'), dtype('float64'), dtype('int64')]
    >>> np.lib._iotools.flatten_dtype(dt, flatten_base=True)
    [dtype('S4'),
     dtype('float64'),
     dtype('float64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64')]

    """
    names = ndtype.names
    if names is None:
        if flatten_base:
            return [ndtype.base] * int(np.prod(ndtype.shape))
        return [ndtype.base]
    else:
        types = []
        for field in names:
            info = ndtype.fields[field]
            flat_dt = flatten_dtype(info[0], flatten_base)
            types.extend(flat_dt)
        return types


class LineSplitter:
    """
    Object to split a string at a given delimiter or at given places.

    Parameters
    ----------
    delimiter : str, int, or sequence of ints, optional
        If a string, character used to delimit consecutive fields.
        If an integer or a sequence of integers, width(s) of each field.
    comments : str, optional
        Character used to mark the beginning of a comment. Default is '#'.
    autostrip : bool, optional
        Whether to strip each individual field. Default is True.

    """

    def autostrip(self, method):
        """
        Wrapper to strip each member of the output of `method`.

        Parameters
        ----------
        method : function
            Function that takes a single argument and returns a sequence of
            strings.

        Returns
        -------
        wrapped : function
            The result of wrapping `method`. `wrapped` takes a single input
            argument and returns a list of strings that are stripped of
            white-space.

        """
        return lambda input: [_.strip() for _ in method(input)]

    def __init__(self, delimiter=None, comments='#', autostrip=True,
                 encoding=None):
        delimiter = _decode_line(delimiter)
        comments = _decode_line(comments)

        self.comments = comments

        # Delimiter is a character
        if (delimiter is None) or isinstance(delimiter, str):
            delimiter = delimiter or None
            _handyman = self._delimited_splitter
        # Delimiter is a list of field widths
        elif hasattr(delimiter, '__iter__'):
            _handyman = self._variablewidth_splitter
            idx = np.cumsum([0] + list(delimiter))
            delimiter = [slice(i, j) for (i, j) in itertools.pairwise(idx)]
        # Delimiter is a single integer
        elif int(delimiter):
            (_handyman, delimiter) = (
                    self._fixedwidth_splitter, int(delimiter))
        else:
            (_handyman, delimiter) = (self._delimited_splitter, None)
        self.delimiter = delimiter
        if autostrip:
            self._handyman = self.autostrip(_handyman)
        else:
            self._handyman = _handyman
        self.encoding = encoding

    def _delimited_splitter(self, line):
        """Chop off comments, strip, and split at delimiter. """
        if self.comments is not None:
            line = line.split(self.comments)[0]
        line = line.strip(" \r\n")
        if not line:
            return []
        return line.split(self.delimiter)

    def _fixedwidth_splitter(self, line):
        if self.comments is not None:
            line = line.split(self.comments)[0]
        line = line.strip("\r\n")
        if not line:
            return []
        fixed = self.delimiter
        slices = [slice(i, i + fixed) for i in range(0, len(line), fixed)]
        return [line[s] for s in slices]

    def _variablewidth_splitter(self, line):
        if self.comments is not None:
            line = line.split(self.comments)[0]
        if not line:
            return []
        slices = self.delimiter
        return [line[s] for s in slices]

    def __call__(self, line):
        return self._handyman(_decode_line(line, self.encoding))


class NameValidator:
    """
    Object to validate a list of strings to use as field names.

    The strings are stripped of any non alphanumeric character, and spaces
    are replaced by '_'. During instantiation, the user can define a list
    of names to exclude, as well as a list of invalid characters. Names in
    the exclusion list are appended a '_' character.

    Once an instance has been created, it can be called with a list of
    names, and a list of valid names will be created.  The `__call__`
    method accepts an optional keyword "default" that sets the default name
    in case of ambiguity. By default this is 'f', so that names will
    default to `f0`, `f1`, etc.

    Parameters
    ----------
    excludelist : sequence, optional
        A list of names to exclude. This list is appended to the default
        list ['return', 'file', 'print']. Excluded names are appended an
        underscore: for example, `file` becomes `file_` if supplied.
    deletechars : str, optional
        A string combining invalid characters that must be deleted from the
        names.
    case_sensitive : {True, False, 'upper', 'lower'}, optional
        * If True, field names are case-sensitive.
        * If False or 'upper', field names are converted to upper case.
        * If 'lower', field names are converted to lower case.

        The default value is True.
    replace_space : '_', optional
        Character(s) used in replacement of white spaces.

    Notes
    -----
    Calling an instance of `NameValidator` is the same as calling its
    method `validate`.

    Examples
    --------
    >>> import numpy as np
    >>> validator = np.lib._iotools.NameValidator()
    >>> validator(['file', 'field2', 'with space', 'CaSe'])
    ('file_', 'field2', 'with_space', 'CaSe')

    >>> validator = np.lib._iotools.NameValidator(excludelist=['excl'],
    ...                                           deletechars='q',
    ...                                           case_sensitive=False)
    >>> validator(['excl', 'field2', 'no_q', 'with space', 'CaSe'])
    ('EXCL', 'FIELD2', 'NO_Q', 'WITH_SPACE', 'CASE')

    """

    defaultexcludelist = 'return', 'file', 'print'
    defaultdeletechars = frozenset(r"""~!@#$%^&*()-=+~\|]}[{';: /?.>,<""")

    def __init__(self, excludelist=None, deletechars=None,
                 case_sensitive=None, replace_space='_'):
        # Process the exclusion list ..
        if excludelist is None:
            excludelist = []
        excludelist.extend(self.defaultexcludelist)
        self.excludelist = excludelist
        # Process the list of characters to delete
        if deletechars is None:
            delete = set(self.defaultdeletechars)
        else:
            delete = set(deletechars)
        delete.add('"')
        self.deletechars = delete
        # Process the case option .....
        if (case_sensitive is None) or (case_sensitive is True):
            self.case_converter = lambda x: x
        elif (case_sensitive is False) or case_sensitive.startswith('u'):
            self.case_converter = lambda x: x.upper()
        elif case_sensitive.startswith('l'):
            self.case_converter = lambda x: x.lower()
        else:
            msg = f'unrecognized case_sensitive value {case_sensitive}.'
            raise ValueError(msg)

        self.replace_space = replace_space

    def validate(self, names, defaultfmt="f%i", nbfields=None):
        """
        Validate a list of strings as field names for a structured array.

        Parameters
        ----------
        names : sequence of str
            Strings to be validated.
        defaultfmt : str, optional
            Default format string, used if validating a given string
            reduces its length to zero.
        nbfields : integer, optional
            Final number of validated names, used to expand or shrink the
            initial list of names.

        Returns
        -------
        validatednames : list of str
            The list of validated field names.

        Notes
        -----
        A `NameValidator` instance can be called directly, which is the
        same as calling `validate`. For examples, see `NameValidator`.

        """
        # Initial checks ..............
        if (names is None):
            if (nbfields is None):
                return None
            names = []
        if isinstance(names, str):
            names = [names, ]
        if nbfields is not None:
            nbnames = len(names)
            if (nbnames < nbfields):
                names = list(names) + [''] * (nbfields - nbnames)
            elif (nbnames > nbfields):
                names = names[:nbfields]
        # Set some shortcuts ...........
        deletechars = self.deletechars
        excludelist = self.excludelist
        case_converter = self.case_converter
        replace_space = self.replace_space
        # Initializes some variables ...
        validatednames = []
        seen = {}
        nbempty = 0

        for item in names:
            item = case_converter(item).strip()
            if replace_space:
                item = item.replace(' ', replace_space)
            item = ''.join([c for c in item if c not in deletechars])
            if item == '':
                item = defaultfmt % nbempty
                while item in names:
                    nbempty += 1
                    item = defaultfmt % nbempty
                nbempty += 1
            elif item in excludelist:
                item += '_'
            cnt = seen.get(item, 0)
            if cnt > 0:
                validatednames.append(item + '_%d' % cnt)
            else:
                validatednames.append(item)
            seen[item] = cnt + 1
        return tuple(validatednames)

    def __call__(self, names, defaultfmt="f%i", nbfields=None):
        return self.validate(names, defaultfmt=defaultfmt, nbfields=nbfields)


def str2bool(value):
    """
    Tries to transform a string supposed to represent a boolean to a boolean.

    Parameters
    ----------
    value : str
        The string that is transformed to a boolean.

    Returns
    -------
    boolval : bool
        The boolean representation of `value`.

    Raises
    ------
    ValueError
        If the string is not 'True' or 'False' (case independent)

    Examples
    --------
    >>> import numpy as np
    >>> np.lib._iotools.str2bool('TRUE')
    True
    >>> np.lib._iotools.str2bool('false')
    False

    """
    value = value.upper()
    if value == 'TRUE':
        return True
    elif value == 'FALSE':
        return False
    else:
        raise ValueError("Invalid boolean")


class ConverterError(Exception):
    """
    Exception raised when an error occurs in a converter for string values.

    """
    pass


class ConverterLockError(ConverterError):
    """
    Exception raised when an attempt is made to upgrade a locked converter.

    """
    pass


class ConversionWarning(UserWarning):
    """
    Warning issued when a string converter has a problem.

    Notes
    -----
    In `genfromtxt` a `ConversionWarning` is issued if raising exceptions
    is explicitly suppressed with the "invalid_raise" keyword.

    """
    pass


class StringConverter:
    """
    Factory class for function transforming a string into another object
    (int, float).

    After initialization, an instance can be called to transform a string
    into another object. If the string is recognized as representing a
    missing value, a default value is returned.

    Attributes
    ----------
    func : function
        Function used for the conversion.
    default : any
        Default value to return when the input corresponds to a missing
        value.
    type : type
        Type of the output.
    _status : int
        Integer representing the order of the conversion.
    _mapper : sequence of tuples
        Sequence of tuples (dtype, function, default value) to evaluate in
        order.
    _locked : bool
        Holds `locked` parameter.

    Parameters
    ----------
    dtype_or_func : {None, dtype, function}, optional
        If a `dtype`, specifies the input data type, used to define a basic
        function and a default value for missing data. For example, when
        `dtype` is float, the `func` attribute is set to `float` and the
        default value to `np.nan`.  If a function, this function is used to
        convert a string to another object. In this case, it is recommended
        to give an associated default value as input.
    default : any, optional
        Value to return by default, that is, when the string to be
        converted is flagged as missing. If not given, `StringConverter`
        tries to supply a reasonable default value.
    missing_values : {None, sequence of str}, optional
        ``None`` or sequence of strings indicating a missing value. If ``None``
        then missing values are indicated by empty entries. The default is
        ``None``.
    locked : bool, optional
        Whether the StringConverter should be locked to prevent automatic
        upgrade or not. Default is False.

    """
    _mapper = [(nx.bool, str2bool, False),
               (nx.int_, int, -1),]

    # On 32-bit systems, we need to make sure that we explicitly include
    # nx.int64 since ns.int_ is nx.int32.
    if nx.dtype(nx.int_).itemsize < nx.dtype(nx.int64).itemsize:
        _mapper.append((nx.int64, int, -1))

    _mapper.extend([(nx.float64, float, nx.nan),
                    (nx.complex128, complex, nx.nan + 0j),
                    (nx.longdouble, nx.longdouble, nx.nan),
                    # If a non-default dtype is passed, fall back to generic
                    # ones (should only be used for the converter)
                    (nx.integer, int, -1),
                    (nx.floating, float, nx.nan),
                    (nx.complexfloating, complex, nx.nan + 0j),
                    # Last, try with the string types (must be last, because
                    # `_mapper[-1]` is used as default in some cases)
                    (nx.str_, asunicode, '???'),
                    (nx.bytes_, asbytes, '???'),
                    ])

    @classmethod
    def _getdtype(cls, val):
        """Returns the dtype of the input variable."""
        return np.array(val).dtype

    @classmethod
    def _getsubdtype(cls, val):
        """Returns the type of the dtype of the input variable."""
        return np.array(val).dtype.type

    @classmethod
    def _dtypeortype(cls, dtype):
        """Returns dtype for datetime64 and type of dtype otherwise."""

        # This is a bit annoying. We want to return the "general" type in most
        # cases (ie. "string" rather than "S10"), but we want to return the
        # specific type for datetime64 (ie. "datetime64[us]" rather than
        # "datetime64").
        if dtype.type == np.datetime64:
            return dtype
        return dtype.type

    @classmethod
    def upgrade_mapper(cls, func, default=None):
        """
        Upgrade the mapper of a StringConverter by adding a new function and
        its corresponding default.

        The input function (or sequence of functions) and its associated
        default value (if any) is inserted in penultimate position of the
        mapper.  The corresponding type is estimated from the dtype of the
        default value.

        Parameters
        ----------
        func : var
            Function, or sequence of functions

        Examples
        --------
        >>> import dateutil.parser
        >>> import datetime
        >>> dateparser = dateutil.parser.parse
        >>> defaultdate = datetime.date(2000, 1, 1)
        >>> StringConverter.upgrade_mapper(dateparser, default=defaultdate)
        """
        # Func is a single functions
        if callable(func):
            cls._mapper.insert(-1, (cls._getsubdtype(default), func, default))
            return
        elif hasattr(func, '__iter__'):
            if isinstance(func[0], (tuple, list)):
                for _ in func:
                    cls._mapper.insert(-1, _)
                return
            if default is None:
                default = [None] * len(func)
            else:
                default = list(default)
                default.append([None] * (len(func) - len(default)))
            for fct, dft in zip(func, default):
                cls._mapper.insert(-1, (cls._getsubdtype(dft), fct, dft))

    @classmethod
    def _find_map_entry(cls, dtype):
        # if a converter for the specific dtype is available use that
        for i, (deftype, func, default_def) in enumerate(cls._mapper):
            if dtype.type == deftype:
                return i, (deftype, func, default_def)

        # otherwise find an inexact match
        for i, (deftype, func, default_def) in enumerate(cls._mapper):
            if np.issubdtype(dtype.type, deftype):
                return i, (deftype, func, default_def)

        raise LookupError

    def __init__(self, dtype_or_func=None, default=None, missing_values=None,
                 locked=False):
        # Defines a lock for upgrade
        self._locked = bool(locked)
        # No input dtype: minimal initialization
        if dtype_or_func is None:
            self.func = str2bool
            self._status = 0
            self.default = default or False
            dtype = np.dtype('bool')
        else:
            # Is the input a np.dtype ?
            try:
                self.func = None
                dtype = np.dtype(dtype_or_func)
            except TypeError:
                # dtype_or_func must be a function, then
                if not callable(dtype_or_func):
                    errmsg = ("The input argument `dtype` is neither a"
                              " function nor a dtype (got '%s' instead)")
                    raise TypeError(errmsg % type(dtype_or_func))
                # Set the function
                self.func = dtype_or_func
                # If we don't have a default, try to guess it or set it to
                # None
                if default is None:
                    try:
                        default = self.func('0')
                    except ValueError:
                        default = None
                dtype = self._getdtype(default)

            # find the best match in our mapper
            try:
                self._status, (_, func, default_def) = self._find_map_entry(dtype)
            except LookupError:
                # no match
                self.default = default
                _, func, _ = self._mapper[-1]
                self._status = 0
            else:
                # use the found default only if we did not already have one
                if default is None:
                    self.default = default_def
                else:
                    self.default = default

            # If the input was a dtype, set the function to the last we saw
            if self.func is None:
                self.func = func

            # If the status is 1 (int), change the function to
            # something more robust.
            if self.func == self._mapper[1][1]:
                if issubclass(dtype.type, np.uint64):
                    self.func = np.uint64
                elif issubclass(dtype.type, np.int64):
                    self.func = np.int64
                else:
                    self.func = lambda x: int(float(x))
        # Store the list of strings corresponding to missing values.
        if missing_values is None:
            self.missing_values = {''}
        else:
            if isinstance(missing_values, str):
                missing_values = missing_values.split(",")
            self.missing_values = set(list(missing_values) + [''])

        self._callingfunction = self._strict_call
        self.type = self._dtypeortype(dtype)
        self._checked = False
        self._initial_default = default

    def _loose_call(self, value):
        try:
            return self.func(value)
        except ValueError:
            return self.default

    def _strict_call(self, value):
        try:

            # We check if we can convert the value using the current function
            new_value = self.func(value)

            # In addition to having to check whether func can convert the
            # value, we also have to make sure that we don't get overflow
            # errors for integers.
            if self.func is int:
                try:
                    np.array(value, dtype=self.type)
                except OverflowError:
                    raise ValueError

            # We're still here so we can now return the new value
            return new_value

        except ValueError:
            if value.strip() in self.missing_values:
                if not self._status:
                    self._checked = False
                return self.default
            raise ValueError(f"Cannot convert string '{value}'")

    def __call__(self, value):
        return self._callingfunction(value)

    def _do_upgrade(self):
        # Raise an exception if we locked the converter...
        if self._locked:
            errmsg = "Converter is locked and cannot be upgraded"
            raise ConverterLockError(errmsg)
        _statusmax = len(self._mapper)
        # Complains if we try to upgrade by the maximum
        _status = self._status
        if _status == _statusmax:
            errmsg = "Could not find a valid conversion function"
            raise ConverterError(errmsg)
        elif _status < _statusmax - 1:
            _status += 1
        self.type, self.func, default = self._mapper[_status]
        self._status = _status
        if self._initial_default is not None:
            self.default = self._initial_default
        else:
            self.default = default

    def upgrade(self, value):
        """
        Find the best converter for a given string, and return the result.

        The supplied string `value` is converted by testing different
        converters in order. First the `func` method of the
        `StringConverter` instance is tried, if this fails other available
        converters are tried.  The order in which these other converters
        are tried is determined by the `_status` attribute of the instance.

        Parameters
        ----------
        value : str
            The string to convert.

        Returns
        -------
        out : any
            The result of converting `value` with the appropriate converter.

        """
        self._checked = True
        try:
            return self._strict_call(value)
        except ValueError:
            self._do_upgrade()
            return self.upgrade(value)

    def iterupgrade(self, value):
        self._checked = True
        if not hasattr(value, '__iter__'):
            value = (value,)
        _strict_call = self._strict_call
        try:
            for _m in value:
                _strict_call(_m)
        except ValueError:
            self._do_upgrade()
            self.iterupgrade(value)

    def update(self, func, default=None, testing_value=None,
               missing_values='', locked=False):
        """
        Set StringConverter attributes directly.

        Parameters
        ----------
        func : function
            Conversion function.
        default : any, optional
            Value to return by default, that is, when the string to be
            converted is flagged as missing. If not given,
            `StringConverter` tries to supply a reasonable default value.
        testing_value : str, optional
            A string representing a standard input value of the converter.
            This string is used to help defining a reasonable default
            value.
        missing_values : {sequence of str, None}, optional
            Sequence of strings indicating a missing value. If ``None``, then
            the existing `missing_values` are cleared. The default is ``''``.
        locked : bool, optional
            Whether the StringConverter should be locked to prevent
            automatic upgrade or not. Default is False.

        Notes
        -----
        `update` takes the same parameters as the constructor of
        `StringConverter`, except that `func` does not accept a `dtype`
        whereas `dtype_or_func` in the constructor does.

        """
        self.func = func
        self._locked = locked

        # Don't reset the default to None if we can avoid it
        if default is not None:
            self.default = default
            self.type = self._dtypeortype(self._getdtype(default))
        else:
            try:
                tester = func(testing_value or '1')
            except (TypeError, ValueError):
                tester = None
            self.type = self._dtypeortype(self._getdtype(tester))

        # Add the missing values to the existing set or clear it.
        if missing_values is None:
            # Clear all missing values even though the ctor initializes it to
            # set(['']) when the argument is None.
            self.missing_values = set()
        else:
            if not np.iterable(missing_values):
                missing_values = [missing_values]
            if not all(isinstance(v, str) for v in missing_values):
                raise TypeError("missing_values must be strings or unicode")
            self.missing_values.update(missing_values)


def easy_dtype(ndtype, names=None, defaultfmt="f%i", **validationargs):
    """
    Convenience function to create a `np.dtype` object.

    The function processes the input `dtype` and matches it with the given
    names.

    Parameters
    ----------
    ndtype : var
        Definition of the dtype. Can be any string or dictionary recognized
        by the `np.dtype` function, or a sequence of types.
    names : str or sequence, optional
        Sequence of strings to use as field names for a structured dtype.
        For convenience, `names` can be a string of a comma-separated list
        of names.
    defaultfmt : str, optional
        Format string used to define missing names, such as ``"f%i"``
        (default) or ``"fields_%02i"``.
    validationargs : optional
        A series of optional arguments used to initialize a
        `NameValidator`.

    Examples
    --------
    >>> import numpy as np
    >>> np.lib._iotools.easy_dtype(float)
    dtype('float64')
    >>> np.lib._iotools.easy_dtype("i4, f8")
    dtype([('f0', '<i4'), ('f1', '<f8')])
    >>> np.lib._iotools.easy_dtype("i4, f8", defaultfmt="field_%03i")
    dtype([('field_000', '<i4'), ('field_001', '<f8')])

    >>> np.lib._iotools.easy_dtype((int, float, float), names="a,b,c")
    dtype([('a', '<i8'), ('b', '<f8'), ('c', '<f8')])
    >>> np.lib._iotools.easy_dtype(float, names="a,b,c")
    dtype([('a', '<f8'), ('b', '<f8'), ('c', '<f8')])

    """
    try:
        ndtype = np.dtype(ndtype)
    except TypeError:
        validate = NameValidator(**validationargs)
        nbfields = len(ndtype)
        if names is None:
            names = [''] * len(ndtype)
        elif isinstance(names, str):
            names = names.split(",")
        names = validate(names, nbfields=nbfields, defaultfmt=defaultfmt)
        ndtype = np.dtype({"formats": ndtype, "names": names})
    else:
        # Explicit names
        if names is not None:
            validate = NameValidator(**validationargs)
            if isinstance(names, str):
                names = names.split(",")
            # Simple dtype: repeat to match the nb of names
            if ndtype.names is None:
                formats = tuple([ndtype.type] * len(names))
                names = validate(names, defaultfmt=defaultfmt)
                ndtype = np.dtype(list(zip(names, formats)))
            # Structured dtype: just validate the names as needed
            else:
                ndtype.names = validate(names, nbfields=len(ndtype.names),
                                        defaultfmt=defaultfmt)
        # No implicit names
        elif ndtype.names is not None:
            validate = NameValidator(**validationargs)
            # Default initial names : should we change the format ?
            numbered_names = tuple(f"f{i}" for i in range(len(ndtype.names)))
            if ((ndtype.names == numbered_names) and (defaultfmt != "f%i")):
                ndtype.names = validate([''] * len(ndtype.names),
                                        defaultfmt=defaultfmt)
            # Explicit initial names : just validate
            else:
                ndtype.names = validate(ndtype.names, defaultfmt=defaultfmt)
    return ndtype