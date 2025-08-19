
# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\output\win32.py ===
from __future__ import annotations

import sys

assert sys.platform == "win32"

import os
from ctypes import ArgumentError, byref, c_char, c_long, c_uint, c_ulong, pointer
from ctypes.wintypes import DWORD, HANDLE
from typing import Callable, TextIO, TypeVar

from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.data_structures import Size
from prompt_toolkit.styles import ANSI_COLOR_NAMES, Attrs
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.win32_types import (
    CONSOLE_SCREEN_BUFFER_INFO,
    COORD,
    SMALL_RECT,
    STD_INPUT_HANDLE,
    STD_OUTPUT_HANDLE,
)

from ..utils import SPHINX_AUTODOC_RUNNING
from .base import Output
from .color_depth import ColorDepth

# Do not import win32-specific stuff when generating documentation.
# Otherwise RTD would be unable to generate docs for this module.
if not SPHINX_AUTODOC_RUNNING:
    from ctypes import windll


__all__ = [
    "Win32Output",
]


def _coord_byval(coord: COORD) -> c_long:
    """
    Turns a COORD object into a c_long.
    This will cause it to be passed by value instead of by reference. (That is what I think at least.)

    When running ``ptipython`` is run (only with IPython), we often got the following error::

         Error in 'SetConsoleCursorPosition'.
         ArgumentError("argument 2: <class 'TypeError'>: wrong type",)
     argument 2: <class 'TypeError'>: wrong type

    It was solved by turning ``COORD`` parameters into a ``c_long`` like this.

    More info: http://msdn.microsoft.com/en-us/library/windows/desktop/ms686025(v=vs.85).aspx
    """
    return c_long(coord.Y * 0x10000 | coord.X & 0xFFFF)


#: If True: write the output of the renderer also to the following file. This
#: is very useful for debugging. (e.g.: to see that we don't write more bytes
#: than required.)
_DEBUG_RENDER_OUTPUT = False
_DEBUG_RENDER_OUTPUT_FILENAME = r"prompt-toolkit-windows-output.log"


class NoConsoleScreenBufferError(Exception):
    """
    Raised when the application is not running inside a Windows Console, but
    the user tries to instantiate Win32Output.
    """

    def __init__(self) -> None:
        # Are we running in 'xterm' on Windows, like git-bash for instance?
        xterm = "xterm" in os.environ.get("TERM", "")

        if xterm:
            message = (
                "Found {}, while expecting a Windows console. "
                'Maybe try to run this program using "winpty" '
                "or run it in cmd.exe instead. Or otherwise, "
                "in case of Cygwin, use the Python executable "
                "that is compiled for Cygwin.".format(os.environ["TERM"])
            )
        else:
            message = "No Windows console found. Are you running cmd.exe?"
        super().__init__(message)


_T = TypeVar("_T")


class Win32Output(Output):
    """
    I/O abstraction for rendering to Windows consoles.
    (cmd.exe and similar.)
    """

    def __init__(
        self,
        stdout: TextIO,
        use_complete_width: bool = False,
        default_color_depth: ColorDepth | None = None,
    ) -> None:
        self.use_complete_width = use_complete_width
        self.default_color_depth = default_color_depth

        self._buffer: list[str] = []
        self.stdout: TextIO = stdout
        self.hconsole = HANDLE(windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE))

        self._in_alternate_screen = False
        self._hidden = False

        self.color_lookup_table = ColorLookupTable()

        # Remember the default console colors.
        info = self.get_win32_screen_buffer_info()
        self.default_attrs = info.wAttributes if info else 15

        if _DEBUG_RENDER_OUTPUT:
            self.LOG = open(_DEBUG_RENDER_OUTPUT_FILENAME, "ab")

    def fileno(self) -> int:
        "Return file descriptor."
        return self.stdout.fileno()

    def encoding(self) -> str:
        "Return encoding used for stdout."
        return self.stdout.encoding

    def write(self, data: str) -> None:
        if self._hidden:
            data = " " * get_cwidth(data)

        self._buffer.append(data)

    def write_raw(self, data: str) -> None:
        "For win32, there is no difference between write and write_raw."
        self.write(data)

    def get_size(self) -> Size:
        info = self.get_win32_screen_buffer_info()

        # We take the width of the *visible* region as the size. Not the width
        # of the complete screen buffer. (Unless use_complete_width has been
        # set.)
        if self.use_complete_width:
            width = info.dwSize.X
        else:
            width = info.srWindow.Right - info.srWindow.Left

        height = info.srWindow.Bottom - info.srWindow.Top + 1

        # We avoid the right margin, windows will wrap otherwise.
        maxwidth = info.dwSize.X - 1
        width = min(maxwidth, width)

        # Create `Size` object.
        return Size(rows=height, columns=width)

    def _winapi(self, func: Callable[..., _T], *a: object, **kw: object) -> _T:
        """
        Flush and call win API function.
        """
        self.flush()

        if _DEBUG_RENDER_OUTPUT:
            self.LOG.write((f"{func.__name__!r}").encode() + b"\n")
            self.LOG.write(
                b"     " + ", ".join([f"{i!r}" for i in a]).encode("utf-8") + b"\n"
            )
            self.LOG.write(
                b"     "
                + ", ".join([f"{type(i)!r}" for i in a]).encode("utf-8")
                + b"\n"
            )
            self.LOG.flush()

        try:
            return func(*a, **kw)
        except ArgumentError as e:
            if _DEBUG_RENDER_OUTPUT:
                self.LOG.write((f"    Error in {func.__name__!r} {e!r} {e}\n").encode())

            raise

    def get_win32_screen_buffer_info(self) -> CONSOLE_SCREEN_BUFFER_INFO:
        """
        Return Screen buffer info.
        """
        # NOTE: We don't call the `GetConsoleScreenBufferInfo` API through
        #     `self._winapi`. Doing so causes Python to crash on certain 64bit
        #     Python versions. (Reproduced with 64bit Python 2.7.6, on Windows
        #     10). It is not clear why. Possibly, it has to do with passing
        #     these objects as an argument, or through *args.

        # The Python documentation contains the following - possibly related - warning:
        #     ctypes does not support passing unions or structures with
        #     bit-fields to functions by value. While this may work on 32-bit
        #     x86, it's not guaranteed by the library to work in the general
        #     case. Unions and structures with bit-fields should always be
        #     passed to functions by pointer.

        # Also see:
        #    - https://github.com/ipython/ipython/issues/10070
        #    - https://github.com/jonathanslenders/python-prompt-toolkit/issues/406
        #    - https://github.com/jonathanslenders/python-prompt-toolkit/issues/86

        self.flush()
        sbinfo = CONSOLE_SCREEN_BUFFER_INFO()
        success = windll.kernel32.GetConsoleScreenBufferInfo(
            self.hconsole, byref(sbinfo)
        )

        # success = self._winapi(windll.kernel32.GetConsoleScreenBufferInfo,
        #                        self.hconsole, byref(sbinfo))

        if success:
            return sbinfo
        else:
            raise NoConsoleScreenBufferError

    def set_title(self, title: str) -> None:
        """
        Set terminal title.
        """
        self._winapi(windll.kernel32.SetConsoleTitleW, title)

    def clear_title(self) -> None:
        self._winapi(windll.kernel32.SetConsoleTitleW, "")

    def erase_screen(self) -> None:
        start = COORD(0, 0)
        sbinfo = self.get_win32_screen_buffer_info()
        length = sbinfo.dwSize.X * sbinfo.dwSize.Y

        self.cursor_goto(row=0, column=0)
        self._erase(start, length)

    def erase_down(self) -> None:
        sbinfo = self.get_win32_screen_buffer_info()
        size = sbinfo.dwSize

        start = sbinfo.dwCursorPosition
        length = (size.X - size.X) + size.X * (size.Y - sbinfo.dwCursorPosition.Y)

        self._erase(start, length)

    def erase_end_of_line(self) -> None:
        """"""
        sbinfo = self.get_win32_screen_buffer_info()
        start = sbinfo.dwCursorPosition
        length = sbinfo.dwSize.X - sbinfo.dwCursorPosition.X

        self._erase(start, length)

    def _erase(self, start: COORD, length: int) -> None:
        chars_written = c_ulong()

        self._winapi(
            windll.kernel32.FillConsoleOutputCharacterA,
            self.hconsole,
            c_char(b" "),
            DWORD(length),
            _coord_byval(start),
            byref(chars_written),
        )

        # Reset attributes.
        sbinfo = self.get_win32_screen_buffer_info()
        self._winapi(
            windll.kernel32.FillConsoleOutputAttribute,
            self.hconsole,
            sbinfo.wAttributes,
            length,
            _coord_byval(start),
            byref(chars_written),
        )

    def reset_attributes(self) -> None:
        "Reset the console foreground/background color."
        self._winapi(
            windll.kernel32.SetConsoleTextAttribute, self.hconsole, self.default_attrs
        )
        self._hidden = False

    def set_attributes(self, attrs: Attrs, color_depth: ColorDepth) -> None:
        (
            fgcolor,
            bgcolor,
            bold,
            underline,
            strike,
            italic,
            blink,
            reverse,
            hidden,
        ) = attrs
        self._hidden = bool(hidden)

        # Start from the default attributes.
        win_attrs: int = self.default_attrs

        if color_depth != ColorDepth.DEPTH_1_BIT:
            # Override the last four bits: foreground color.
            if fgcolor:
                win_attrs = win_attrs & ~0xF
                win_attrs |= self.color_lookup_table.lookup_fg_color(fgcolor)

            # Override the next four bits: background color.
            if bgcolor:
                win_attrs = win_attrs & ~0xF0
                win_attrs |= self.color_lookup_table.lookup_bg_color(bgcolor)

        # Reverse: swap these four bits groups.
        if reverse:
            win_attrs = (
                (win_attrs & ~0xFF)
                | ((win_attrs & 0xF) << 4)
                | ((win_attrs & 0xF0) >> 4)
            )

        self._winapi(windll.kernel32.SetConsoleTextAttribute, self.hconsole, win_attrs)

    def disable_autowrap(self) -> None:
        # Not supported by Windows.
        pass

    def enable_autowrap(self) -> None:
        # Not supported by Windows.
        pass

    def cursor_goto(self, row: int = 0, column: int = 0) -> None:
        pos = COORD(X=column, Y=row)
        self._winapi(
            windll.kernel32.SetConsoleCursorPosition, self.hconsole, _coord_byval(pos)
        )

    def cursor_up(self, amount: int) -> None:
        sr = self.get_win32_screen_buffer_info().dwCursorPosition
        pos = COORD(X=sr.X, Y=sr.Y - amount)
        self._winapi(
            windll.kernel32.SetConsoleCursorPosition, self.hconsole, _coord_byval(pos)
        )

    def cursor_down(self, amount: int) -> None:
        self.cursor_up(-amount)

    def cursor_forward(self, amount: int) -> None:
        sr = self.get_win32_screen_buffer_info().dwCursorPosition
        #        assert sr.X + amount >= 0, 'Negative cursor position: x=%r amount=%r' % (sr.X, amount)

        pos = COORD(X=max(0, sr.X + amount), Y=sr.Y)
        self._winapi(
            windll.kernel32.SetConsoleCursorPosition, self.hconsole, _coord_byval(pos)
        )

    def cursor_backward(self, amount: int) -> None:
        self.cursor_forward(-amount)

    def flush(self) -> None:
        """
        Write to output stream and flush.
        """
        if not self._buffer:
            # Only flush stdout buffer. (It could be that Python still has
            # something in its buffer. -- We want to be sure to print that in
            # the correct color.)
            self.stdout.flush()
            return

        data = "".join(self._buffer)

        if _DEBUG_RENDER_OUTPUT:
            self.LOG.write((f"{data!r}").encode() + b"\n")
            self.LOG.flush()

        # Print characters one by one. This appears to be the best solution
        # in order to avoid traces of vertical lines when the completion
        # menu disappears.
        for b in data:
            written = DWORD()

            retval = windll.kernel32.WriteConsoleW(
                self.hconsole, b, 1, byref(written), None
            )
            assert retval != 0

        self._buffer = []

    def get_rows_below_cursor_position(self) -> int:
        info = self.get_win32_screen_buffer_info()
        return info.srWindow.Bottom - info.dwCursorPosition.Y + 1

    def scroll_buffer_to_prompt(self) -> None:
        """
        To be called before drawing the prompt. This should scroll the console
        to left, with the cursor at the bottom (if possible).
        """
        # Get current window size
        info = self.get_win32_screen_buffer_info()
        sr = info.srWindow
        cursor_pos = info.dwCursorPosition

        result = SMALL_RECT()

        # Scroll to the left.
        result.Left = 0
        result.Right = sr.Right - sr.Left

        # Scroll vertical
        win_height = sr.Bottom - sr.Top
        if 0 < sr.Bottom - cursor_pos.Y < win_height - 1:
            # no vertical scroll if cursor already on the screen
            result.Bottom = sr.Bottom
        else:
            result.Bottom = max(win_height, cursor_pos.Y)
        result.Top = result.Bottom - win_height

        # Scroll API
        self._winapi(
            windll.kernel32.SetConsoleWindowInfo, self.hconsole, True, byref(result)
        )

    def enter_alternate_screen(self) -> None:
        """
        Go to alternate screen buffer.
        """
        if not self._in_alternate_screen:
            GENERIC_READ = 0x80000000
            GENERIC_WRITE = 0x40000000

            # Create a new console buffer and activate that one.
            handle = HANDLE(
                self._winapi(
                    windll.kernel32.CreateConsoleScreenBuffer,
                    GENERIC_READ | GENERIC_WRITE,
                    DWORD(0),
                    None,
                    DWORD(1),
                    None,
                )
            )

            self._winapi(windll.kernel32.SetConsoleActiveScreenBuffer, handle)
            self.hconsole = handle
            self._in_alternate_screen = True

    def quit_alternate_screen(self) -> None:
        """
        Make stdout again the active buffer.
        """
        if self._in_alternate_screen:
            stdout = HANDLE(
                self._winapi(windll.kernel32.GetStdHandle, STD_OUTPUT_HANDLE)
            )
            self._winapi(windll.kernel32.SetConsoleActiveScreenBuffer, stdout)
            self._winapi(windll.kernel32.CloseHandle, self.hconsole)
            self.hconsole = stdout
            self._in_alternate_screen = False

    def enable_mouse_support(self) -> None:
        ENABLE_MOUSE_INPUT = 0x10

        # This `ENABLE_QUICK_EDIT_MODE` flag needs to be cleared for mouse
        # support to work, but it's possible that it was already cleared
        # before.
        ENABLE_QUICK_EDIT_MODE = 0x0040

        handle = HANDLE(windll.kernel32.GetStdHandle(STD_INPUT_HANDLE))

        original_mode = DWORD()
        self._winapi(windll.kernel32.GetConsoleMode, handle, pointer(original_mode))
        self._winapi(
            windll.kernel32.SetConsoleMode,
            handle,
            (original_mode.value | ENABLE_MOUSE_INPUT) & ~ENABLE_QUICK_EDIT_MODE,
        )

    def disable_mouse_support(self) -> None:
        ENABLE_MOUSE_INPUT = 0x10
        handle = HANDLE(windll.kernel32.GetStdHandle(STD_INPUT_HANDLE))

        original_mode = DWORD()
        self._winapi(windll.kernel32.GetConsoleMode, handle, pointer(original_mode))
        self._winapi(
            windll.kernel32.SetConsoleMode,
            handle,
            original_mode.value & ~ENABLE_MOUSE_INPUT,
        )

    def hide_cursor(self) -> None:
        pass

    def show_cursor(self) -> None:
        pass

    def set_cursor_shape(self, cursor_shape: CursorShape) -> None:
        pass

    def reset_cursor_shape(self) -> None:
        pass

    @classmethod
    def win32_refresh_window(cls) -> None:
        """
        Call win32 API to refresh the whole Window.

        This is sometimes necessary when the application paints background
        for completion menus. When the menu disappears, it leaves traces due
        to a bug in the Windows Console. Sending a repaint request solves it.
        """
        # Get console handle
        handle = HANDLE(windll.kernel32.GetConsoleWindow())

        RDW_INVALIDATE = 0x0001
        windll.user32.RedrawWindow(handle, None, None, c_uint(RDW_INVALIDATE))

    def get_default_color_depth(self) -> ColorDepth:
        """
        Return the default color depth for a windows terminal.

        Contrary to the Vt100 implementation, this doesn't depend on a $TERM
        variable.
        """
        if self.default_color_depth is not None:
            return self.default_color_depth

        return ColorDepth.DEPTH_4_BIT


class FOREGROUND_COLOR:
    BLACK = 0x0000
    BLUE = 0x0001
    GREEN = 0x0002
    CYAN = 0x0003
    RED = 0x0004
    MAGENTA = 0x0005
    YELLOW = 0x0006
    GRAY = 0x0007
    INTENSITY = 0x0008  # Foreground color is intensified.


class BACKGROUND_COLOR:
    BLACK = 0x0000
    BLUE = 0x0010
    GREEN = 0x0020
    CYAN = 0x0030
    RED = 0x0040
    MAGENTA = 0x0050
    YELLOW = 0x0060
    GRAY = 0x0070
    INTENSITY = 0x0080  # Background color is intensified.


def _create_ansi_color_dict(
    color_cls: type[FOREGROUND_COLOR] | type[BACKGROUND_COLOR],
) -> dict[str, int]:
    "Create a table that maps the 16 named ansi colors to their Windows code."
    return {
        "ansidefault": color_cls.BLACK,
        "ansiblack": color_cls.BLACK,
        "ansigray": color_cls.GRAY,
        "ansibrightblack": color_cls.BLACK | color_cls.INTENSITY,
        "ansiwhite": color_cls.GRAY | color_cls.INTENSITY,
        # Low intensity.
        "ansired": color_cls.RED,
        "ansigreen": color_cls.GREEN,
        "ansiyellow": color_cls.YELLOW,
        "ansiblue": color_cls.BLUE,
        "ansimagenta": color_cls.MAGENTA,
        "ansicyan": color_cls.CYAN,
        # High intensity.
        "ansibrightred": color_cls.RED | color_cls.INTENSITY,
        "ansibrightgreen": color_cls.GREEN | color_cls.INTENSITY,
        "ansibrightyellow": color_cls.YELLOW | color_cls.INTENSITY,
        "ansibrightblue": color_cls.BLUE | color_cls.INTENSITY,
        "ansibrightmagenta": color_cls.MAGENTA | color_cls.INTENSITY,
        "ansibrightcyan": color_cls.CYAN | color_cls.INTENSITY,
    }


FG_ANSI_COLORS = _create_ansi_color_dict(FOREGROUND_COLOR)
BG_ANSI_COLORS = _create_ansi_color_dict(BACKGROUND_COLOR)

assert set(FG_ANSI_COLORS) == set(ANSI_COLOR_NAMES)
assert set(BG_ANSI_COLORS) == set(ANSI_COLOR_NAMES)


class ColorLookupTable:
    """
    Inspired by pygments/formatters/terminal256.py
    """

    def __init__(self) -> None:
        self._win32_colors = self._build_color_table()

        # Cache (map color string to foreground and background code).
        self.best_match: dict[str, tuple[int, int]] = {}

    @staticmethod
    def _build_color_table() -> list[tuple[int, int, int, int, int]]:
        """
        Build an RGB-to-256 color conversion table
        """
        FG = FOREGROUND_COLOR
        BG = BACKGROUND_COLOR

        return [
            (0x00, 0x00, 0x00, FG.BLACK, BG.BLACK),
            (0x00, 0x00, 0xAA, FG.BLUE, BG.BLUE),
            (0x00, 0xAA, 0x00, FG.GREEN, BG.GREEN),
            (0x00, 0xAA, 0xAA, FG.CYAN, BG.CYAN),
            (0xAA, 0x00, 0x00, FG.RED, BG.RED),
            (0xAA, 0x00, 0xAA, FG.MAGENTA, BG.MAGENTA),
            (0xAA, 0xAA, 0x00, FG.YELLOW, BG.YELLOW),
            (0x88, 0x88, 0x88, FG.GRAY, BG.GRAY),
            (0x44, 0x44, 0xFF, FG.BLUE | FG.INTENSITY, BG.BLUE | BG.INTENSITY),
            (0x44, 0xFF, 0x44, FG.GREEN | FG.INTENSITY, BG.GREEN | BG.INTENSITY),
            (0x44, 0xFF, 0xFF, FG.CYAN | FG.INTENSITY, BG.CYAN | BG.INTENSITY),
            (0xFF, 0x44, 0x44, FG.RED | FG.INTENSITY, BG.RED | BG.INTENSITY),
            (0xFF, 0x44, 0xFF, FG.MAGENTA | FG.INTENSITY, BG.MAGENTA | BG.INTENSITY),
            (0xFF, 0xFF, 0x44, FG.YELLOW | FG.INTENSITY, BG.YELLOW | BG.INTENSITY),
            (0x44, 0x44, 0x44, FG.BLACK | FG.INTENSITY, BG.BLACK | BG.INTENSITY),
            (0xFF, 0xFF, 0xFF, FG.GRAY | FG.INTENSITY, BG.GRAY | BG.INTENSITY),
        ]

    def _closest_color(self, r: int, g: int, b: int) -> tuple[int, int]:
        distance = 257 * 257 * 3  # "infinity" (>distance from #000000 to #ffffff)
        fg_match = 0
        bg_match = 0

        for r_, g_, b_, fg_, bg_ in self._win32_colors:
            rd = r - r_
            gd = g - g_
            bd = b - b_

            d = rd * rd + gd * gd + bd * bd

            if d < distance:
                fg_match = fg_
                bg_match = bg_
                distance = d
        return fg_match, bg_match

    def _color_indexes(self, color: str) -> tuple[int, int]:
        indexes = self.best_match.get(color, None)
        if indexes is None:
            try:
                rgb = int(str(color), 16)
            except ValueError:
                rgb = 0

            r = (rgb >> 16) & 0xFF
            g = (rgb >> 8) & 0xFF
            b = rgb & 0xFF
            indexes = self._closest_color(r, g, b)
            self.best_match[color] = indexes
        return indexes

    def lookup_fg_color(self, fg_color: str) -> int:
        """
        Return the color for use in the
        `windll.kernel32.SetConsoleTextAttribute` API call.

        :param fg_color: Foreground as text. E.g. 'ffffff' or 'red'
        """
        # Foreground.
        if fg_color in FG_ANSI_COLORS:
            return FG_ANSI_COLORS[fg_color]
        else:
            return self._color_indexes(fg_color)[0]

    def lookup_bg_color(self, bg_color: str) -> int:
        """
        Return the color for use in the
        `windll.kernel32.SetConsoleTextAttribute` API call.

        :param bg_color: Background as text. E.g. 'ffffff' or 'red'
        """
        # Background.
        if bg_color in BG_ANSI_COLORS:
            return BG_ANSI_COLORS[bg_color]
        else:
            return self._color_indexes(bg_color)[1]

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\customer_endpoints.py ===
"""
CUSTOMER MANAGEMENT

All /customer management endpoints 

/customer/new   
/customer/info
/customer/update
/customer/delete
"""

#### END-USER/CUSTOMER MANAGEMENT ####
import traceback
from typing import List, Optional

import fastapi
from fastapi import APIRouter, Depends, HTTPException, Request, status

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth

router = APIRouter()


@router.post(
    "/end_user/block",
    tags=["Customer Management"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
@router.post(
    "/customer/block",
    tags=["Customer Management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def block_user(data: BlockUsers):
    """
    [BETA] Reject calls with this end-user id

    Parameters:
    - user_ids (List[str], required): The unique `user_id`s for the users to block

        (any /chat/completion call with this user={end-user-id} param, will be rejected.)

        ```
        curl -X POST "http://0.0.0.0:8000/user/block"
        -H "Authorization: Bearer sk-1234"
        -d '{
        "user_ids": [<user_id>, ...]
        }'
        ```
    """
    from litellm.proxy.proxy_server import prisma_client

    try:
        records = []
        if prisma_client is not None:
            for id in data.user_ids:
                record = await prisma_client.db.litellm_endusertable.upsert(
                    where={"user_id": id},  # type: ignore
                    data={
                        "create": {"user_id": id, "blocked": True},  # type: ignore
                        "update": {"blocked": True},
                    },
                )
                records.append(record)
        else:
            raise HTTPException(
                status_code=500,
                detail={"error": "Postgres DB Not connected"},
            )

        return {"blocked_users": records}
    except Exception as e:
        verbose_proxy_logger.error(f"An error occurred - {str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post(
    "/end_user/unblock",
    tags=["Customer Management"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
@router.post(
    "/customer/unblock",
    tags=["Customer Management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def unblock_user(data: BlockUsers):
    """
    [BETA] Unblock calls with this user id

    Example
    ```
    curl -X POST "http://0.0.0.0:8000/user/unblock"
    -H "Authorization: Bearer sk-1234"
    -d '{
    "user_ids": [<user_id>, ...]
    }'
    ```
    """
    try:
        from enterprise.enterprise_hooks.blocked_user_list import (
            _ENTERPRISE_BlockedUserList,
        )
    except ImportError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Blocked user check was never set. This call has no effect."
                + CommonProxyErrors.missing_enterprise_package_docker.value
            },
        )

    if (
        not any(isinstance(x, _ENTERPRISE_BlockedUserList) for x in litellm.callbacks)
        or litellm.blocked_user_list is None
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Blocked user check was never set. This call has no effect."
            },
        )

    if isinstance(litellm.blocked_user_list, list):
        for id in data.user_ids:
            litellm.blocked_user_list.remove(id)
    else:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "`blocked_user_list` must be set as a list. Filepaths can't be updated."
            },
        )

    return {"blocked_users": litellm.blocked_user_list}


def new_budget_request(data: NewCustomerRequest) -> Optional[BudgetNewRequest]:
    """
    Return a new budget object if new budget params are passed.
    """
    budget_params = BudgetNewRequest.model_fields.keys()
    budget_kv_pairs = {}

    # Get the actual values from the data object using getattr
    for field_name in budget_params:
        if field_name == "budget_id":
            continue
        value = getattr(data, field_name, None)
        if value is not None:
            budget_kv_pairs[field_name] = value

    if budget_kv_pairs:
        return BudgetNewRequest(**budget_kv_pairs)
    return None


@router.post(
    "/end_user/new",
    tags=["Customer Management"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
@router.post(
    "/customer/new",
    tags=["Customer Management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def new_end_user(
    data: NewCustomerRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Allow creating a new Customer 


    Parameters:
    - user_id: str - The unique identifier for the user.
    - alias: Optional[str] - A human-friendly alias for the user.
    - blocked: bool - Flag to allow or disallow requests for this end-user. Default is False.
    - max_budget: Optional[float] - The maximum budget allocated to the user. Either 'max_budget' or 'budget_id' should be provided, not both.
    - budget_id: Optional[str] - The identifier for an existing budget allocated to the user. Either 'max_budget' or 'budget_id' should be provided, not both.
    - allowed_model_region: Optional[Union[Literal["eu"], Literal["us"]]] - Require all user requests to use models in this specific region.
    - default_model: Optional[str] - If no equivalent model in the allowed region, default all requests to this model.
    - metadata: Optional[dict] = Metadata for customer, store information for customer. Example metadata = {"data_training_opt_out": True}
    - budget_duration: Optional[str] - Budget is reset at the end of specified duration. If not set, budget is never reset. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d").
    - tpm_limit: Optional[int] - [Not Implemented Yet] Specify tpm limit for a given customer (Tokens per minute)
    - rpm_limit: Optional[int] - [Not Implemented Yet] Specify rpm limit for a given customer (Requests per minute)
    - model_max_budget: Optional[dict] - [Not Implemented Yet] Specify max budget for a given model. Example: {"openai/gpt-4o-mini": {"max_budget": 100.0, "budget_duration": "1d"}}
    - max_parallel_requests: Optional[int] - [Not Implemented Yet] Specify max parallel requests for a given customer.
    - soft_budget: Optional[float] - [Not Implemented Yet] Get alerts when customer crosses given budget, doesn't block requests.
    - spend: Optional[float] - Specify initial spend for a given customer.
    - budget_reset_at: Optional[str] - Specify the date and time when the budget should be reset.
    
    
    - Allow specifying allowed regions 
    - Allow specifying default model

    Example curl:
    ```
    curl --location 'http://0.0.0.0:4000/customer/new' \
        --header 'Authorization: Bearer sk-1234' \
        --header 'Content-Type: application/json' \
        --data '{
            "user_id" : "ishaan-jaff-3",
            "allowed_region": "eu",
            "budget_id": "free_tier",
            "default_model": "azure/gpt-3.5-turbo-eu" <- all calls from this user, use this model? 
        }'

        # return end-user object
    ```

    NOTE: This used to be called `/end_user/new`, we will still be maintaining compatibility for /end_user/XXX for these endpoints
    """
    """
    Validation:
        - check if default model exists 
        - create budget object if not already created
    
    - Add user to end user table 

    Return 
    - end-user object
    - currently allowed models 
    """
    from litellm.proxy.proxy_server import (
        litellm_proxy_admin_name,
        llm_router,
        prisma_client,
    )

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )
    try:
        ## VALIDATION ##
        if data.default_model is not None:
            if llm_router is None:
                raise HTTPException(
                    status_code=422,
                    detail={"error": CommonProxyErrors.no_llm_router.value},
                )
            elif data.default_model not in llm_router.get_model_names():
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "Default Model not on proxy. Configure via `/model/new` or config.yaml. Default_model={}, proxy_model_names={}".format(
                            data.default_model, set(llm_router.get_model_names())
                        )
                    },
                )

        new_end_user_obj: Dict = {}

        ## CREATE BUDGET ## if set
        _new_budget = new_budget_request(data)
        if _new_budget is not None:
            try:
                budget_record = await prisma_client.db.litellm_budgettable.create(
                    data={
                        **_new_budget.model_dump(exclude_unset=True),
                        "created_by": user_api_key_dict.user_id or litellm_proxy_admin_name,  # type: ignore
                        "updated_by": user_api_key_dict.user_id
                        or litellm_proxy_admin_name,
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=422, detail={"error": str(e)})

            new_end_user_obj["budget_id"] = budget_record.budget_id
        elif data.budget_id is not None:
            new_end_user_obj["budget_id"] = data.budget_id

        _user_data = data.dict(exclude_none=True)

        for k, v in _user_data.items():
            if k not in BudgetNewRequest.model_fields.keys():
                new_end_user_obj[k] = v

        ## WRITE TO DB ##
        end_user_record = await prisma_client.db.litellm_endusertable.create(
            data=new_end_user_obj,  # type: ignore
            include={"litellm_budget_table": True},
        )

        return end_user_record
    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.management_endpoints.customer_endpoints.new_end_user(): Exception occured - {}".format(
                str(e)
            )
        )
        if "Unique constraint failed on the fields: (`user_id`)" in str(e):
            raise ProxyException(
                message=f"Customer already exists, passed user_id={data.user_id}. Please pass a new user_id.",
                type="bad_request",
                code=400,
                param="user_id",
            )

        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Internal Server Error({str(e)})"),
                type="internal_error",
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Internal Server Error, " + str(e),
            type="internal_error",
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get(
    "/customer/info",
    tags=["Customer Management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=LiteLLM_EndUserTable,
)
@router.get(
    "/end_user/info",
    tags=["Customer Management"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def end_user_info(
    end_user_id: str = fastapi.Query(
        description="End User ID in the request parameters"
    ),
):
    """
    Get information about an end-user. An `end_user` is a customer (external user) of the proxy.

    Parameters:
    - end_user_id (str, required): The unique identifier for the end-user

    Example curl:
    ```
    curl -X GET 'http://localhost:4000/customer/info?end_user_id=test-litellm-user-4' \
        -H 'Authorization: Bearer sk-1234'
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    user_info = await prisma_client.db.litellm_endusertable.find_first(
        where={"user_id": end_user_id}, include={"litellm_budget_table": True}
    )

    if user_info is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "End User Id={} does not exist in db".format(end_user_id)},
        )
    return user_info.model_dump(exclude_none=True)


@router.post(
    "/customer/update",
    tags=["Customer Management"],
    dependencies=[Depends(user_api_key_auth)],
)
@router.post(
    "/end_user/update",
    tags=["Customer Management"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def update_end_user(
    data: UpdateCustomerRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Example curl 

    Parameters:
    - user_id: str
    - alias: Optional[str] = None  # human-friendly alias
    - blocked: bool = False  # allow/disallow requests for this end-user
    - max_budget: Optional[float] = None
    - budget_id: Optional[str] = None  # give either a budget_id or max_budget
    - allowed_model_region: Optional[AllowedModelRegion] = (
        None  # require all user requests to use models in this specific region
    )
    - default_model: Optional[str] = (
        None  # if no equivalent model in allowed region - default all requests to this model
    )

    Example curl:
    ```
    curl --location 'http://0.0.0.0:4000/customer/update' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
        "user_id": "test-litellm-user-4",
        "budget_id": "paid_tier"
    }'

    See below for all params 
    ```
    """

    from litellm.proxy.proxy_server import prisma_client

    try:
        data_json: dict = data.json()
        # get the row from db
        if prisma_client is None:
            raise Exception("Not connected to DB!")

        # get non default values for key
        non_default_values = {}
        for k, v in data_json.items():
            if v is not None and v not in (
                [],
                {},
                0,
            ):  # models default to [], spend defaults to 0, we should not reset these values
                non_default_values[k] = v

        ## Get end user table data ##
        end_user_table_data = await prisma_client.db.litellm_endusertable.find_first(
            where={"user_id": data.user_id}, include={"litellm_budget_table": True}
        )

        if end_user_table_data is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "End User Id={} does not exist in db".format(data.user_id)
                },
            )

        end_user_table_data_typed = LiteLLM_EndUserTable(
            **end_user_table_data.model_dump()
        )

        ## Get budget table data ##
        end_user_budget_table = end_user_table_data_typed.litellm_budget_table

        ## Get all params for budget table ##
        budget_table_data = {}
        update_end_user_table_data = {}
        for k, v in non_default_values.items():
            if k in LiteLLM_BudgetTable.model_fields.keys():
                budget_table_data[k] = v

            if k in LiteLLM_EndUserTable.model_fields.keys():
                update_end_user_table_data[k] = v

        ## Check if budget id is set ##
        if budget_table_data:
            if end_user_budget_table is None:
                ## Create new budget ##
                budget_table_data_record = (
                    await prisma_client.db.litellm_budgettable.create(
                        data=budget_table_data, include={"litellm_endusertable": True}
                    )
                )

                update_end_user_table_data[
                    "budget_id"
                ] = budget_table_data_record.budget_id
            else:
                ## Update existing budget ##
                budget_table_data_record = (
                    await prisma_client.db.litellm_budgettable.update(
                        where={"budget_id": end_user_budget_table.budget_id},
                        data=budget_table_data,
                    )
                )

        ## Update user table, with update params + new budget id (if set) ##
        verbose_proxy_logger.debug("/customer/update: Received data = %s", data)
        if data.user_id is not None and len(data.user_id) > 0:
            update_end_user_table_data["user_id"] = data.user_id  # type: ignore
            verbose_proxy_logger.debug("In update customer, user_id condition block.")
            response = await prisma_client.db.litellm_endusertable.update(
                where={"user_id": data.user_id}, data=update_end_user_table_data, include={"litellm_budget_table": True}  # type: ignore
            )
            if response is None:
                raise ValueError(
                    f"Failed updating customer data. User ID does not exist passed user_id={data.user_id}"
                )
            verbose_proxy_logger.debug(
                f"received response from updating prisma client. response={response}"
            )
            return response
        else:
            raise ValueError(f"user_id is required, passed user_id = {data.user_id}")

        # update based on remaining passed in values

    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.update_end_user(): Exception occured - {}".format(
                str(e)
            )
        )
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Internal Server Error({str(e)})"),
                type="internal_error",
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Internal Server Error, " + str(e),
            type="internal_error",
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    pass


@router.post(
    "/customer/delete",
    tags=["Customer Management"],
    dependencies=[Depends(user_api_key_auth)],
)
@router.post(
    "/end_user/delete",
    tags=["Customer Management"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def delete_end_user(
    data: DeleteCustomerRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Delete multiple end-users.

    Parameters:
    - user_ids (List[str], required): The unique `user_id`s for the users to delete

    Example curl:
    ```
    curl --location 'http://0.0.0.0:4000/customer/delete' \
        --header 'Authorization: Bearer sk-1234' \
        --header 'Content-Type: application/json' \
        --data '{
            "user_ids" :["ishaan-jaff-5"]
    }'

    See below for all params 
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception("Not connected to DB!")

        verbose_proxy_logger.debug("/customer/delete: Received data = %s", data)
        if (
            data.user_ids is not None
            and isinstance(data.user_ids, list)
            and len(data.user_ids) > 0
        ):
            response = await prisma_client.db.litellm_endusertable.delete_many(
                where={"user_id": {"in": data.user_ids}}
            )
            if response is None:
                raise ValueError(
                    f"Failed deleting customer data. User ID does not exist passed user_id={data.user_ids}"
                )
            if response != len(data.user_ids):
                raise ValueError(
                    f"Failed deleting all customer data. User ID does not exist passed user_id={data.user_ids}. Deleted {response} customers, passed {len(data.user_ids)} customers"
                )
            verbose_proxy_logger.debug(
                f"received response from updating prisma client. response={response}"
            )
            return {
                "deleted_customers": response,
                "message": "Successfully deleted customers with ids: "
                + str(data.user_ids),
            }
        else:
            raise ValueError(f"user_id is required, passed user_id = {data.user_ids}")

        # update based on remaining passed in values
    except Exception as e:
        verbose_proxy_logger.error(
            "litellm.proxy.proxy_server.delete_end_user(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Internal Server Error({str(e)})"),
                type="internal_error",
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Internal Server Error, " + str(e),
            type="internal_error",
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    pass


@router.get(
    "/customer/list",
    tags=["Customer Management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=List[LiteLLM_EndUserTable],
)
@router.get(
    "/end_user/list",
    tags=["Customer Management"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def list_end_user(
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [Admin-only] List all available customers

    Example curl:
    ```
    curl --location --request GET 'http://0.0.0.0:4000/customer/list' \
        --header 'Authorization: Bearer sk-1234'
    ```

    """
    from litellm.proxy.proxy_server import prisma_client

    if (
        user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN
        and user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN_VIEW_ONLY
    ):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Admin-only endpoint. Your user role={}".format(
                    user_api_key_dict.user_role
                )
            },
        )

    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    response = await prisma_client.db.litellm_endusertable.find_many(
        include={"litellm_budget_table": True}
    )

    returned_response: List[LiteLLM_EndUserTable] = []
    for item in response:
        returned_response.append(LiteLLM_EndUserTable(**item.model_dump()))
    return returned_response

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\plistlib\__init__.py ===
import collections.abc
import re
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Type,
    Union,
    IO,
)
import warnings
from io import BytesIO
from datetime import datetime
from base64 import b64encode, b64decode
from numbers import Integral
from types import SimpleNamespace
from functools import singledispatch

from fontTools.misc import etree

from fontTools.misc.textTools import tostr


# By default, we
#  - deserialize <data> elements as bytes and
#  - serialize bytes as <data> elements.
# Before, on Python 2, we
#  - deserialized <data> elements as plistlib.Data objects, in order to
#    distinguish them from the built-in str type (which is bytes on python2)
#  - serialized bytes as <string> elements (they must have only contained
#    ASCII characters in this case)
# You can pass use_builtin_types=[True|False] to the load/dump etc. functions
# to enforce a specific treatment.
# NOTE that unicode type always maps to <string> element, and plistlib.Data
# always maps to <data> element, regardless of use_builtin_types.
USE_BUILTIN_TYPES = True

XML_DECLARATION = b"""<?xml version='1.0' encoding='UTF-8'?>"""

PLIST_DOCTYPE = (
    b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
    b'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
)


# Date should conform to a subset of ISO 8601:
# YYYY '-' MM '-' DD 'T' HH ':' MM ':' SS 'Z'
_date_parser = re.compile(
    r"(?P<year>\d\d\d\d)"
    r"(?:-(?P<month>\d\d)"
    r"(?:-(?P<day>\d\d)"
    r"(?:T(?P<hour>\d\d)"
    r"(?::(?P<minute>\d\d)"
    r"(?::(?P<second>\d\d))"
    r"?)?)?)?)?Z",
    re.ASCII,
)


def _date_from_string(s: str) -> datetime:
    order = ("year", "month", "day", "hour", "minute", "second")
    m = _date_parser.match(s)
    if m is None:
        raise ValueError(f"Expected ISO 8601 date string, but got '{s:r}'.")
    gd = m.groupdict()
    lst = []
    for key in order:
        val = gd[key]
        if val is None:
            break
        lst.append(int(val))
    # NOTE: mypy doesn't know that lst is 6 elements long.
    return datetime(*lst)  # type:ignore


def _date_to_string(d: datetime) -> str:
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (
        d.year,
        d.month,
        d.day,
        d.hour,
        d.minute,
        d.second,
    )


class Data:
    """Represents binary data when ``use_builtin_types=False.``

    This class wraps binary data loaded from a plist file when the
    ``use_builtin_types`` argument to the loading function (:py:func:`fromtree`,
    :py:func:`load`, :py:func:`loads`) is false.

    The actual binary data is retrieved using the ``data`` attribute.
    """

    def __init__(self, data: bytes) -> None:
        if not isinstance(data, bytes):
            raise TypeError("Expected bytes, found %s" % type(data).__name__)
        self.data = data

    @classmethod
    def fromBase64(cls, data: Union[bytes, str]) -> "Data":
        return cls(b64decode(data))

    def asBase64(self, maxlinelength: int = 76, indent_level: int = 1) -> bytes:
        return _encode_base64(
            self.data, maxlinelength=maxlinelength, indent_level=indent_level
        )

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.data == other.data
        elif isinstance(other, bytes):
            return self.data == other
        else:
            return NotImplemented

    def __repr__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, repr(self.data))


def _encode_base64(
    data: bytes, maxlinelength: Optional[int] = 76, indent_level: int = 1
) -> bytes:
    data = b64encode(data)
    if data and maxlinelength:
        # split into multiple lines right-justified to 'maxlinelength' chars
        indent = b"\n" + b"  " * indent_level
        max_length = max(16, maxlinelength - len(indent))
        chunks = []
        for i in range(0, len(data), max_length):
            chunks.append(indent)
            chunks.append(data[i : i + max_length])
        chunks.append(indent)
        data = b"".join(chunks)
    return data


# Mypy does not support recursive type aliases as of 0.782, Pylance does.
# https://github.com/python/mypy/issues/731
# https://devblogs.microsoft.com/python/pylance-introduces-five-new-features-that-enable-type-magic-for-python-developers/#1-support-for-recursive-type-aliases
PlistEncodable = Union[
    bool,
    bytes,
    Data,
    datetime,
    float,
    Integral,
    Mapping[str, Any],
    Sequence[Any],
    str,
]


class PlistTarget:
    """Event handler using the ElementTree Target API that can be
    passed to a XMLParser to produce property list objects from XML.
    It is based on the CPython plistlib module's _PlistParser class,
    but does not use the expat parser.

    >>> from fontTools.misc import etree
    >>> parser = etree.XMLParser(target=PlistTarget())
    >>> result = etree.XML(
    ...     "<dict>"
    ...     "    <key>something</key>"
    ...     "    <string>blah</string>"
    ...     "</dict>",
    ...     parser=parser)
    >>> result == {"something": "blah"}
    True

    Links:
    https://github.com/python/cpython/blob/main/Lib/plistlib.py
    http://lxml.de/parsing.html#the-target-parser-interface
    """

    def __init__(
        self,
        use_builtin_types: Optional[bool] = None,
        dict_type: Type[MutableMapping[str, Any]] = dict,
    ) -> None:
        self.stack: List[PlistEncodable] = []
        self.current_key: Optional[str] = None
        self.root: Optional[PlistEncodable] = None
        if use_builtin_types is None:
            self._use_builtin_types = USE_BUILTIN_TYPES
        else:
            if use_builtin_types is False:
                warnings.warn(
                    "Setting use_builtin_types to False is deprecated and will be "
                    "removed soon.",
                    DeprecationWarning,
                )
            self._use_builtin_types = use_builtin_types
        self._dict_type = dict_type

    def start(self, tag: str, attrib: Mapping[str, str]) -> None:
        self._data: List[str] = []
        handler = _TARGET_START_HANDLERS.get(tag)
        if handler is not None:
            handler(self)

    def end(self, tag: str) -> None:
        handler = _TARGET_END_HANDLERS.get(tag)
        if handler is not None:
            handler(self)

    def data(self, data: str) -> None:
        self._data.append(data)

    def close(self) -> PlistEncodable:
        if self.root is None:
            raise ValueError("No root set.")
        return self.root

    # helpers

    def add_object(self, value: PlistEncodable) -> None:
        if self.current_key is not None:
            stack_top = self.stack[-1]
            if not isinstance(stack_top, collections.abc.MutableMapping):
                raise ValueError("unexpected element: %r" % stack_top)
            stack_top[self.current_key] = value
            self.current_key = None
        elif not self.stack:
            # this is the root object
            self.root = value
        else:
            stack_top = self.stack[-1]
            if not isinstance(stack_top, list):
                raise ValueError("unexpected element: %r" % stack_top)
            stack_top.append(value)

    def get_data(self) -> str:
        data = "".join(self._data)
        self._data = []
        return data


# event handlers


def start_dict(self: PlistTarget) -> None:
    d = self._dict_type()
    self.add_object(d)
    self.stack.append(d)


def end_dict(self: PlistTarget) -> None:
    if self.current_key:
        raise ValueError("missing value for key '%s'" % self.current_key)
    self.stack.pop()


def end_key(self: PlistTarget) -> None:
    if self.current_key or not isinstance(self.stack[-1], collections.abc.Mapping):
        raise ValueError("unexpected key")
    self.current_key = self.get_data()


def start_array(self: PlistTarget) -> None:
    a: List[PlistEncodable] = []
    self.add_object(a)
    self.stack.append(a)


def end_array(self: PlistTarget) -> None:
    self.stack.pop()


def end_true(self: PlistTarget) -> None:
    self.add_object(True)


def end_false(self: PlistTarget) -> None:
    self.add_object(False)


def end_integer(self: PlistTarget) -> None:
    self.add_object(int(self.get_data()))


def end_real(self: PlistTarget) -> None:
    self.add_object(float(self.get_data()))


def end_string(self: PlistTarget) -> None:
    self.add_object(self.get_data())


def end_data(self: PlistTarget) -> None:
    if self._use_builtin_types:
        self.add_object(b64decode(self.get_data()))
    else:
        self.add_object(Data.fromBase64(self.get_data()))


def end_date(self: PlistTarget) -> None:
    self.add_object(_date_from_string(self.get_data()))


_TARGET_START_HANDLERS: Dict[str, Callable[[PlistTarget], None]] = {
    "dict": start_dict,
    "array": start_array,
}

_TARGET_END_HANDLERS: Dict[str, Callable[[PlistTarget], None]] = {
    "dict": end_dict,
    "array": end_array,
    "key": end_key,
    "true": end_true,
    "false": end_false,
    "integer": end_integer,
    "real": end_real,
    "string": end_string,
    "data": end_data,
    "date": end_date,
}


# functions to build element tree from plist data


def _string_element(value: str, ctx: SimpleNamespace) -> etree.Element:
    el = etree.Element("string")
    el.text = value
    return el


def _bool_element(value: bool, ctx: SimpleNamespace) -> etree.Element:
    if value:
        return etree.Element("true")
    return etree.Element("false")


def _integer_element(value: int, ctx: SimpleNamespace) -> etree.Element:
    if -1 << 63 <= value < 1 << 64:
        el = etree.Element("integer")
        el.text = "%d" % value
        return el
    raise OverflowError(value)


def _real_element(value: float, ctx: SimpleNamespace) -> etree.Element:
    el = etree.Element("real")
    el.text = repr(value)
    return el


def _dict_element(
    d: Mapping[str, PlistEncodable], ctx: SimpleNamespace
) -> etree.Element:
    el = etree.Element("dict")
    items = d.items()
    if ctx.sort_keys:
        items = sorted(items)  # type: ignore
    ctx.indent_level += 1
    for key, value in items:
        if not isinstance(key, str):
            if ctx.skipkeys:
                continue
            raise TypeError("keys must be strings")
        k = etree.SubElement(el, "key")
        k.text = tostr(key, "utf-8")
        el.append(_make_element(value, ctx))
    ctx.indent_level -= 1
    return el


def _array_element(
    array: Sequence[PlistEncodable], ctx: SimpleNamespace
) -> etree.Element:
    el = etree.Element("array")
    if len(array) == 0:
        return el
    ctx.indent_level += 1
    for value in array:
        el.append(_make_element(value, ctx))
    ctx.indent_level -= 1
    return el


def _date_element(date: datetime, ctx: SimpleNamespace) -> etree.Element:
    el = etree.Element("date")
    el.text = _date_to_string(date)
    return el


def _data_element(data: bytes, ctx: SimpleNamespace) -> etree.Element:
    el = etree.Element("data")
    # NOTE: mypy is confused about whether el.text should be str or bytes.
    el.text = _encode_base64(  # type: ignore
        data,
        maxlinelength=(76 if ctx.pretty_print else None),
        indent_level=ctx.indent_level,
    )
    return el


def _string_or_data_element(raw_bytes: bytes, ctx: SimpleNamespace) -> etree.Element:
    if ctx.use_builtin_types:
        return _data_element(raw_bytes, ctx)
    else:
        try:
            string = raw_bytes.decode(encoding="ascii", errors="strict")
        except UnicodeDecodeError:
            raise ValueError(
                "invalid non-ASCII bytes; use unicode string instead: %r" % raw_bytes
            )
        return _string_element(string, ctx)


# The following is probably not entirely correct. The signature should take `Any`
# and return `NoReturn`. At the time of this writing, neither mypy nor Pyright
# can deal with singledispatch properly and will apply the signature of the base
# function to all others. Being slightly dishonest makes it type-check and return
# usable typing information for the optimistic case.
@singledispatch
def _make_element(value: PlistEncodable, ctx: SimpleNamespace) -> etree.Element:
    raise TypeError("unsupported type: %s" % type(value))


_make_element.register(str)(_string_element)
_make_element.register(bool)(_bool_element)
_make_element.register(Integral)(_integer_element)
_make_element.register(float)(_real_element)
_make_element.register(collections.abc.Mapping)(_dict_element)
_make_element.register(list)(_array_element)
_make_element.register(tuple)(_array_element)
_make_element.register(datetime)(_date_element)
_make_element.register(bytes)(_string_or_data_element)
_make_element.register(bytearray)(_data_element)
_make_element.register(Data)(lambda v, ctx: _data_element(v.data, ctx))


# Public functions to create element tree from plist-compatible python
# data structures and viceversa, for use when (de)serializing GLIF xml.


def totree(
    value: PlistEncodable,
    sort_keys: bool = True,
    skipkeys: bool = False,
    use_builtin_types: Optional[bool] = None,
    pretty_print: bool = True,
    indent_level: int = 1,
) -> etree.Element:
    """Convert a value derived from a plist into an XML tree.

    Args:
        value: Any kind of value to be serialized to XML.
        sort_keys: Whether keys of dictionaries should be sorted.
        skipkeys (bool): Whether to silently skip non-string dictionary
            keys.
        use_builtin_types (bool): If true, byte strings will be
            encoded in Base-64 and wrapped in a ``data`` tag; if
            false, they will be either stored as ASCII strings or an
            exception raised if they cannot be decoded as such. Defaults
            to ``True`` if not present. Deprecated.
        pretty_print (bool): Whether to indent the output.
        indent_level (int): Level of indentation when serializing.

    Returns: an ``etree`` ``Element`` object.

    Raises:
        ``TypeError``
            if non-string dictionary keys are serialized
            and ``skipkeys`` is false.
        ``ValueError``
            if non-ASCII binary data is present
            and `use_builtin_types` is false.
    """
    if use_builtin_types is None:
        use_builtin_types = USE_BUILTIN_TYPES
    else:
        use_builtin_types = use_builtin_types
    context = SimpleNamespace(
        sort_keys=sort_keys,
        skipkeys=skipkeys,
        use_builtin_types=use_builtin_types,
        pretty_print=pretty_print,
        indent_level=indent_level,
    )
    return _make_element(value, context)


def fromtree(
    tree: etree.Element,
    use_builtin_types: Optional[bool] = None,
    dict_type: Type[MutableMapping[str, Any]] = dict,
) -> Any:
    """Convert an XML tree to a plist structure.

    Args:
        tree: An ``etree`` ``Element``.
        use_builtin_types: If True, binary data is deserialized to
            bytes strings. If False, it is wrapped in :py:class:`Data`
            objects. Defaults to True if not provided. Deprecated.
        dict_type: What type to use for dictionaries.

    Returns: An object (usually a dictionary).
    """
    target = PlistTarget(use_builtin_types=use_builtin_types, dict_type=dict_type)
    for action, element in etree.iterwalk(tree, events=("start", "end")):
        if action == "start":
            target.start(element.tag, element.attrib)
        elif action == "end":
            # if there are no children, parse the leaf's data
            if not len(element):
                # always pass str, not None
                target.data(element.text or "")
            target.end(element.tag)
    return target.close()


# python3 plistlib API


def load(
    fp: IO[bytes],
    use_builtin_types: Optional[bool] = None,
    dict_type: Type[MutableMapping[str, Any]] = dict,
) -> Any:
    """Load a plist file into an object.

    Args:
        fp: An opened file.
        use_builtin_types: If True, binary data is deserialized to
            bytes strings. If False, it is wrapped in :py:class:`Data`
            objects. Defaults to True if not provided. Deprecated.
        dict_type: What type to use for dictionaries.

    Returns:
        An object (usually a dictionary) representing the top level of
        the plist file.
    """

    if not hasattr(fp, "read"):
        raise AttributeError("'%s' object has no attribute 'read'" % type(fp).__name__)
    target = PlistTarget(use_builtin_types=use_builtin_types, dict_type=dict_type)
    parser = etree.XMLParser(target=target)
    result = etree.parse(fp, parser=parser)
    # lxml returns the target object directly, while ElementTree wraps
    # it as the root of an ElementTree object
    try:
        return result.getroot()
    except AttributeError:
        return result


def loads(
    value: bytes,
    use_builtin_types: Optional[bool] = None,
    dict_type: Type[MutableMapping[str, Any]] = dict,
) -> Any:
    """Load a plist file from a string into an object.

    Args:
        value: A bytes string containing a plist.
        use_builtin_types: If True, binary data is deserialized to
            bytes strings. If False, it is wrapped in :py:class:`Data`
            objects. Defaults to True if not provided. Deprecated.
        dict_type: What type to use for dictionaries.

    Returns:
        An object (usually a dictionary) representing the top level of
        the plist file.
    """

    fp = BytesIO(value)
    return load(fp, use_builtin_types=use_builtin_types, dict_type=dict_type)


def dump(
    value: PlistEncodable,
    fp: IO[bytes],
    sort_keys: bool = True,
    skipkeys: bool = False,
    use_builtin_types: Optional[bool] = None,
    pretty_print: bool = True,
) -> None:
    """Write a Python object to a plist file.

    Args:
        value: An object to write.
        fp: A file opened for writing.
        sort_keys (bool): Whether keys of dictionaries should be sorted.
        skipkeys (bool): Whether to silently skip non-string dictionary
            keys.
        use_builtin_types (bool): If true, byte strings will be
            encoded in Base-64 and wrapped in a ``data`` tag; if
            false, they will be either stored as ASCII strings or an
            exception raised if they cannot be represented. Defaults
        pretty_print (bool): Whether to indent the output.
        indent_level (int): Level of indentation when serializing.

    Raises:
        ``TypeError``
            if non-string dictionary keys are serialized
            and ``skipkeys`` is false.
        ``ValueError``
            if non-representable binary data is present
            and `use_builtin_types` is false.
    """

    if not hasattr(fp, "write"):
        raise AttributeError("'%s' object has no attribute 'write'" % type(fp).__name__)
    root = etree.Element("plist", version="1.0")
    el = totree(
        value,
        sort_keys=sort_keys,
        skipkeys=skipkeys,
        use_builtin_types=use_builtin_types,
        pretty_print=pretty_print,
    )
    root.append(el)
    tree = etree.ElementTree(root)
    # we write the doctype ourselves instead of using the 'doctype' argument
    # of 'write' method, becuse lxml will force adding a '\n' even when
    # pretty_print is False.
    if pretty_print:
        header = b"\n".join((XML_DECLARATION, PLIST_DOCTYPE, b""))
    else:
        header = XML_DECLARATION + PLIST_DOCTYPE
    fp.write(header)
    tree.write(  # type: ignore
        fp,
        encoding="utf-8",
        pretty_print=pretty_print,
        xml_declaration=False,
    )


def dumps(
    value: PlistEncodable,
    sort_keys: bool = True,
    skipkeys: bool = False,
    use_builtin_types: Optional[bool] = None,
    pretty_print: bool = True,
) -> bytes:
    """Write a Python object to a string in plist format.

    Args:
        value: An object to write.
        sort_keys (bool): Whether keys of dictionaries should be sorted.
        skipkeys (bool): Whether to silently skip non-string dictionary
            keys.
        use_builtin_types (bool): If true, byte strings will be
            encoded in Base-64 and wrapped in a ``data`` tag; if
            false, they will be either stored as strings or an
            exception raised if they cannot be represented. Defaults
        pretty_print (bool): Whether to indent the output.
        indent_level (int): Level of indentation when serializing.

    Returns:
        string: A plist representation of the Python object.

    Raises:
        ``TypeError``
            if non-string dictionary keys are serialized
            and ``skipkeys`` is false.
        ``ValueError``
            if non-representable binary data is present
            and `use_builtin_types` is false.
    """
    fp = BytesIO()
    dump(
        value,
        fp,
        sort_keys=sort_keys,
        skipkeys=skipkeys,
        use_builtin_types=use_builtin_types,
        pretty_print=pretty_print,
    )
    return fp.getvalue()

# === NexusCore/openenv\Lib\site-packages\cffi\vengine_gen.py ===
#
# DEPRECATED: implementation for ffi.verify()
#
import sys, os
import types

from . import model
from .error import VerificationError


class VGenericEngine(object):
    _class_key = 'g'
    _gen_python_module = False

    def __init__(self, verifier):
        self.verifier = verifier
        self.ffi = verifier.ffi
        self.export_symbols = []
        self._struct_pending_verification = {}

    def patch_extension_kwds(self, kwds):
        # add 'export_symbols' to the dictionary.  Note that we add the
        # list before filling it.  When we fill it, it will thus also show
        # up in kwds['export_symbols'].
        kwds.setdefault('export_symbols', self.export_symbols)

    def find_module(self, module_name, path, so_suffixes):
        for so_suffix in so_suffixes:
            basename = module_name + so_suffix
            if path is None:
                path = sys.path
            for dirname in path:
                filename = os.path.join(dirname, basename)
                if os.path.isfile(filename):
                    return filename

    def collect_types(self):
        pass      # not needed in the generic engine

    def _prnt(self, what=''):
        self._f.write(what + '\n')

    def write_source_to_f(self):
        prnt = self._prnt
        # first paste some standard set of lines that are mostly '#include'
        prnt(cffimod_header)
        # then paste the C source given by the user, verbatim.
        prnt(self.verifier.preamble)
        #
        # call generate_gen_xxx_decl(), for every xxx found from
        # ffi._parser._declarations.  This generates all the functions.
        self._generate('decl')
        #
        # on Windows, distutils insists on putting init_cffi_xyz in
        # 'export_symbols', so instead of fighting it, just give up and
        # give it one
        if sys.platform == 'win32':
            if sys.version_info >= (3,):
                prefix = 'PyInit_'
            else:
                prefix = 'init'
            modname = self.verifier.get_module_name()
            prnt("void %s%s(void) { }\n" % (prefix, modname))

    def load_library(self, flags=0):
        # import it with the CFFI backend
        backend = self.ffi._backend
        # needs to make a path that contains '/', on Posix
        filename = os.path.join(os.curdir, self.verifier.modulefilename)
        module = backend.load_library(filename, flags)
        #
        # call loading_gen_struct() to get the struct layout inferred by
        # the C compiler
        self._load(module, 'loading')

        # build the FFILibrary class and instance, this is a module subclass
        # because modules are expected to have usually-constant-attributes and
        # in PyPy this means the JIT is able to treat attributes as constant,
        # which we want.
        class FFILibrary(types.ModuleType):
            _cffi_generic_module = module
            _cffi_ffi = self.ffi
            _cffi_dir = []
            def __dir__(self):
                return FFILibrary._cffi_dir
        library = FFILibrary("")
        #
        # finally, call the loaded_gen_xxx() functions.  This will set
        # up the 'library' object.
        self._load(module, 'loaded', library=library)
        return library

    def _get_declarations(self):
        lst = [(key, tp) for (key, (tp, qual)) in
                                self.ffi._parser._declarations.items()]
        lst.sort()
        return lst

    def _generate(self, step_name):
        for name, tp in self._get_declarations():
            kind, realname = name.split(' ', 1)
            try:
                method = getattr(self, '_generate_gen_%s_%s' % (kind,
                                                                step_name))
            except AttributeError:
                raise VerificationError(
                    "not implemented in verify(): %r" % name)
            try:
                method(tp, realname)
            except Exception as e:
                model.attach_exception_info(e, name)
                raise

    def _load(self, module, step_name, **kwds):
        for name, tp in self._get_declarations():
            kind, realname = name.split(' ', 1)
            method = getattr(self, '_%s_gen_%s' % (step_name, kind))
            try:
                method(tp, realname, module, **kwds)
            except Exception as e:
                model.attach_exception_info(e, name)
                raise

    def _generate_nothing(self, tp, name):
        pass

    def _loaded_noop(self, tp, name, module, **kwds):
        pass

    # ----------
    # typedefs: generates no code so far

    _generate_gen_typedef_decl   = _generate_nothing
    _loading_gen_typedef         = _loaded_noop
    _loaded_gen_typedef          = _loaded_noop

    # ----------
    # function declarations

    def _generate_gen_function_decl(self, tp, name):
        assert isinstance(tp, model.FunctionPtrType)
        if tp.ellipsis:
            # cannot support vararg functions better than this: check for its
            # exact type (including the fixed arguments), and build it as a
            # constant function pointer (no _cffi_f_%s wrapper)
            self._generate_gen_const(False, name, tp)
            return
        prnt = self._prnt
        numargs = len(tp.args)
        argnames = []
        for i, type in enumerate(tp.args):
            indirection = ''
            if isinstance(type, model.StructOrUnion):
                indirection = '*'
            argnames.append('%sx%d' % (indirection, i))
        context = 'argument of %s' % name
        arglist = [type.get_c_name(' %s' % arg, context)
                   for type, arg in zip(tp.args, argnames)]
        tpresult = tp.result
        if isinstance(tpresult, model.StructOrUnion):
            arglist.insert(0, tpresult.get_c_name(' *r', context))
            tpresult = model.void_type
        arglist = ', '.join(arglist) or 'void'
        wrappername = '_cffi_f_%s' % name
        self.export_symbols.append(wrappername)
        if tp.abi:
            abi = tp.abi + ' '
        else:
            abi = ''
        funcdecl = ' %s%s(%s)' % (abi, wrappername, arglist)
        context = 'result of %s' % name
        prnt(tpresult.get_c_name(funcdecl, context))
        prnt('{')
        #
        if isinstance(tp.result, model.StructOrUnion):
            result_code = '*r = '
        elif not isinstance(tp.result, model.VoidType):
            result_code = 'return '
        else:
            result_code = ''
        prnt('  %s%s(%s);' % (result_code, name, ', '.join(argnames)))
        prnt('}')
        prnt()

    _loading_gen_function = _loaded_noop

    def _loaded_gen_function(self, tp, name, module, library):
        assert isinstance(tp, model.FunctionPtrType)
        if tp.ellipsis:
            newfunction = self._load_constant(False, tp, name, module)
        else:
            indirections = []
            base_tp = tp
            if (any(isinstance(typ, model.StructOrUnion) for typ in tp.args)
                    or isinstance(tp.result, model.StructOrUnion)):
                indirect_args = []
                for i, typ in enumerate(tp.args):
                    if isinstance(typ, model.StructOrUnion):
                        typ = model.PointerType(typ)
                        indirections.append((i, typ))
                    indirect_args.append(typ)
                indirect_result = tp.result
                if isinstance(indirect_result, model.StructOrUnion):
                    if indirect_result.fldtypes is None:
                        raise TypeError("'%s' is used as result type, "
                                        "but is opaque" % (
                                            indirect_result._get_c_name(),))
                    indirect_result = model.PointerType(indirect_result)
                    indirect_args.insert(0, indirect_result)
                    indirections.insert(0, ("result", indirect_result))
                    indirect_result = model.void_type
                tp = model.FunctionPtrType(tuple(indirect_args),
                                           indirect_result, tp.ellipsis)
            BFunc = self.ffi._get_cached_btype(tp)
            wrappername = '_cffi_f_%s' % name
            newfunction = module.load_function(BFunc, wrappername)
            for i, typ in indirections:
                newfunction = self._make_struct_wrapper(newfunction, i, typ,
                                                        base_tp)
        setattr(library, name, newfunction)
        type(library)._cffi_dir.append(name)

    def _make_struct_wrapper(self, oldfunc, i, tp, base_tp):
        backend = self.ffi._backend
        BType = self.ffi._get_cached_btype(tp)
        if i == "result":
            ffi = self.ffi
            def newfunc(*args):
                res = ffi.new(BType)
                oldfunc(res, *args)
                return res[0]
        else:
            def newfunc(*args):
                args = args[:i] + (backend.newp(BType, args[i]),) + args[i+1:]
                return oldfunc(*args)
        newfunc._cffi_base_type = base_tp
        return newfunc

    # ----------
    # named structs

    def _generate_gen_struct_decl(self, tp, name):
        assert name == tp.name
        self._generate_struct_or_union_decl(tp, 'struct', name)

    def _loading_gen_struct(self, tp, name, module):
        self._loading_struct_or_union(tp, 'struct', name, module)

    def _loaded_gen_struct(self, tp, name, module, **kwds):
        self._loaded_struct_or_union(tp)

    def _generate_gen_union_decl(self, tp, name):
        assert name == tp.name
        self._generate_struct_or_union_decl(tp, 'union', name)

    def _loading_gen_union(self, tp, name, module):
        self._loading_struct_or_union(tp, 'union', name, module)

    def _loaded_gen_union(self, tp, name, module, **kwds):
        self._loaded_struct_or_union(tp)

    def _generate_struct_or_union_decl(self, tp, prefix, name):
        if tp.fldnames is None:
            return     # nothing to do with opaque structs
        checkfuncname = '_cffi_check_%s_%s' % (prefix, name)
        layoutfuncname = '_cffi_layout_%s_%s' % (prefix, name)
        cname = ('%s %s' % (prefix, name)).strip()
        #
        prnt = self._prnt
        prnt('static void %s(%s *p)' % (checkfuncname, cname))
        prnt('{')
        prnt('  /* only to generate compile-time warnings or errors */')
        prnt('  (void)p;')
        for fname, ftype, fbitsize, fqual in tp.enumfields():
            if (isinstance(ftype, model.PrimitiveType)
                and ftype.is_integer_type()) or fbitsize >= 0:
                # accept all integers, but complain on float or double
                prnt('  (void)((p->%s) << 1);' % fname)
            else:
                # only accept exactly the type declared.
                try:
                    prnt('  { %s = &p->%s; (void)tmp; }' % (
                        ftype.get_c_name('*tmp', 'field %r'%fname, quals=fqual),
                        fname))
                except VerificationError as e:
                    prnt('  /* %s */' % str(e))   # cannot verify it, ignore
        prnt('}')
        self.export_symbols.append(layoutfuncname)
        prnt('intptr_t %s(intptr_t i)' % (layoutfuncname,))
        prnt('{')
        prnt('  struct _cffi_aligncheck { char x; %s y; };' % cname)
        prnt('  static intptr_t nums[] = {')
        prnt('    sizeof(%s),' % cname)
        prnt('    offsetof(struct _cffi_aligncheck, y),')
        for fname, ftype, fbitsize, fqual in tp.enumfields():
            if fbitsize >= 0:
                continue      # xxx ignore fbitsize for now
            prnt('    offsetof(%s, %s),' % (cname, fname))
            if isinstance(ftype, model.ArrayType) and ftype.length is None:
                prnt('    0,  /* %s */' % ftype._get_c_name())
            else:
                prnt('    sizeof(((%s *)0)->%s),' % (cname, fname))
        prnt('    -1')
        prnt('  };')
        prnt('  return nums[i];')
        prnt('  /* the next line is not executed, but compiled */')
        prnt('  %s(0);' % (checkfuncname,))
        prnt('}')
        prnt()

    def _loading_struct_or_union(self, tp, prefix, name, module):
        if tp.fldnames is None:
            return     # nothing to do with opaque structs
        layoutfuncname = '_cffi_layout_%s_%s' % (prefix, name)
        #
        BFunc = self.ffi._typeof_locked("intptr_t(*)(intptr_t)")[0]
        function = module.load_function(BFunc, layoutfuncname)
        layout = []
        num = 0
        while True:
            x = function(num)
            if x < 0: break
            layout.append(x)
            num += 1
        if isinstance(tp, model.StructOrUnion) and tp.partial:
            # use the function()'s sizes and offsets to guide the
            # layout of the struct
            totalsize = layout[0]
            totalalignment = layout[1]
            fieldofs = layout[2::2]
            fieldsize = layout[3::2]
            tp.force_flatten()
            assert len(fieldofs) == len(fieldsize) == len(tp.fldnames)
            tp.fixedlayout = fieldofs, fieldsize, totalsize, totalalignment
        else:
            cname = ('%s %s' % (prefix, name)).strip()
            self._struct_pending_verification[tp] = layout, cname

    def _loaded_struct_or_union(self, tp):
        if tp.fldnames is None:
            return     # nothing to do with opaque structs
        self.ffi._get_cached_btype(tp)   # force 'fixedlayout' to be considered

        if tp in self._struct_pending_verification:
            # check that the layout sizes and offsets match the real ones
            def check(realvalue, expectedvalue, msg):
                if realvalue != expectedvalue:
                    raise VerificationError(
                        "%s (we have %d, but C compiler says %d)"
                        % (msg, expectedvalue, realvalue))
            ffi = self.ffi
            BStruct = ffi._get_cached_btype(tp)
            layout, cname = self._struct_pending_verification.pop(tp)
            check(layout[0], ffi.sizeof(BStruct), "wrong total size")
            check(layout[1], ffi.alignof(BStruct), "wrong total alignment")
            i = 2
            for fname, ftype, fbitsize, fqual in tp.enumfields():
                if fbitsize >= 0:
                    continue        # xxx ignore fbitsize for now
                check(layout[i], ffi.offsetof(BStruct, fname),
                      "wrong offset for field %r" % (fname,))
                if layout[i+1] != 0:
                    BField = ffi._get_cached_btype(ftype)
                    check(layout[i+1], ffi.sizeof(BField),
                          "wrong size for field %r" % (fname,))
                i += 2
            assert i == len(layout)

    # ----------
    # 'anonymous' declarations.  These are produced for anonymous structs
    # or unions; the 'name' is obtained by a typedef.

    def _generate_gen_anonymous_decl(self, tp, name):
        if isinstance(tp, model.EnumType):
            self._generate_gen_enum_decl(tp, name, '')
        else:
            self._generate_struct_or_union_decl(tp, '', name)

    def _loading_gen_anonymous(self, tp, name, module):
        if isinstance(tp, model.EnumType):
            self._loading_gen_enum(tp, name, module, '')
        else:
            self._loading_struct_or_union(tp, '', name, module)

    def _loaded_gen_anonymous(self, tp, name, module, **kwds):
        if isinstance(tp, model.EnumType):
            self._loaded_gen_enum(tp, name, module, **kwds)
        else:
            self._loaded_struct_or_union(tp)

    # ----------
    # constants, likely declared with '#define'

    def _generate_gen_const(self, is_int, name, tp=None, category='const',
                            check_value=None):
        prnt = self._prnt
        funcname = '_cffi_%s_%s' % (category, name)
        self.export_symbols.append(funcname)
        if check_value is not None:
            assert is_int
            assert category == 'const'
            prnt('int %s(char *out_error)' % funcname)
            prnt('{')
            self._check_int_constant_value(name, check_value)
            prnt('  return 0;')
            prnt('}')
        elif is_int:
            assert category == 'const'
            prnt('int %s(long long *out_value)' % funcname)
            prnt('{')
            prnt('  *out_value = (long long)(%s);' % (name,))
            prnt('  return (%s) <= 0;' % (name,))
            prnt('}')
        else:
            assert tp is not None
            assert check_value is None
            if category == 'var':
                ampersand = '&'
            else:
                ampersand = ''
            extra = ''
            if category == 'const' and isinstance(tp, model.StructOrUnion):
                extra = 'const *'
                ampersand = '&'
            prnt(tp.get_c_name(' %s%s(void)' % (extra, funcname), name))
            prnt('{')
            prnt('  return (%s%s);' % (ampersand, name))
            prnt('}')
        prnt()

    def _generate_gen_constant_decl(self, tp, name):
        is_int = isinstance(tp, model.PrimitiveType) and tp.is_integer_type()
        self._generate_gen_const(is_int, name, tp)

    _loading_gen_constant = _loaded_noop

    def _load_constant(self, is_int, tp, name, module, check_value=None):
        funcname = '_cffi_const_%s' % name
        if check_value is not None:
            assert is_int
            self._load_known_int_constant(module, funcname)
            value = check_value
        elif is_int:
            BType = self.ffi._typeof_locked("long long*")[0]
            BFunc = self.ffi._typeof_locked("int(*)(long long*)")[0]
            function = module.load_function(BFunc, funcname)
            p = self.ffi.new(BType)
            negative = function(p)
            value = int(p[0])
            if value < 0 and not negative:
                BLongLong = self.ffi._typeof_locked("long long")[0]
                value += (1 << (8*self.ffi.sizeof(BLongLong)))
        else:
            assert check_value is None
            fntypeextra = '(*)(void)'
            if isinstance(tp, model.StructOrUnion):
                fntypeextra = '*' + fntypeextra
            BFunc = self.ffi._typeof_locked(tp.get_c_name(fntypeextra, name))[0]
            function = module.load_function(BFunc, funcname)
            value = function()
            if isinstance(tp, model.StructOrUnion):
                value = value[0]
        return value

    def _loaded_gen_constant(self, tp, name, module, library):
        is_int = isinstance(tp, model.PrimitiveType) and tp.is_integer_type()
        value = self._load_constant(is_int, tp, name, module)
        setattr(library, name, value)
        type(library)._cffi_dir.append(name)

    # ----------
    # enums

    def _check_int_constant_value(self, name, value):
        prnt = self._prnt
        if value <= 0:
            prnt('  if ((%s) > 0 || (long)(%s) != %dL) {' % (
                name, name, value))
        else:
            prnt('  if ((%s) <= 0 || (unsigned long)(%s) != %dUL) {' % (
                name, name, value))
        prnt('    char buf[64];')
        prnt('    if ((%s) <= 0)' % name)
        prnt('        sprintf(buf, "%%ld", (long)(%s));' % name)
        prnt('    else')
        prnt('        sprintf(buf, "%%lu", (unsigned long)(%s));' %
             name)
        prnt('    sprintf(out_error, "%s has the real value %s, not %s",')
        prnt('            "%s", buf, "%d");' % (name[:100], value))
        prnt('    return -1;')
        prnt('  }')

    def _load_known_int_constant(self, module, funcname):
        BType = self.ffi._typeof_locked("char[]")[0]
        BFunc = self.ffi._typeof_locked("int(*)(char*)")[0]
        function = module.load_function(BFunc, funcname)
        p = self.ffi.new(BType, 256)
        if function(p) < 0:
            error = self.ffi.string(p)
            if sys.version_info >= (3,):
                error = str(error, 'utf-8')
            raise VerificationError(error)

    def _enum_funcname(self, prefix, name):
        # "$enum_$1" => "___D_enum____D_1"
        name = name.replace('$', '___D_')
        return '_cffi_e_%s_%s' % (prefix, name)

    def _generate_gen_enum_decl(self, tp, name, prefix='enum'):
        if tp.partial:
            for enumerator in tp.enumerators:
                self._generate_gen_const(True, enumerator)
            return
        #
        funcname = self._enum_funcname(prefix, name)
        self.export_symbols.append(funcname)
        prnt = self._prnt
        prnt('int %s(char *out_error)' % funcname)
        prnt('{')
        for enumerator, enumvalue in zip(tp.enumerators, tp.enumvalues):
            self._check_int_constant_value(enumerator, enumvalue)
        prnt('  return 0;')
        prnt('}')
        prnt()

    def _loading_gen_enum(self, tp, name, module, prefix='enum'):
        if tp.partial:
            enumvalues = [self._load_constant(True, tp, enumerator, module)
                          for enumerator in tp.enumerators]
            tp.enumvalues = tuple(enumvalues)
            tp.partial_resolved = True
        else:
            funcname = self._enum_funcname(prefix, name)
            self._load_known_int_constant(module, funcname)

    def _loaded_gen_enum(self, tp, name, module, library):
        for enumerator, enumvalue in zip(tp.enumerators, tp.enumvalues):
            setattr(library, enumerator, enumvalue)
            type(library)._cffi_dir.append(enumerator)

    # ----------
    # macros: for now only for integers

    def _generate_gen_macro_decl(self, tp, name):
        if tp == '...':
            check_value = None
        else:
            check_value = tp     # an integer
        self._generate_gen_const(True, name, check_value=check_value)

    _loading_gen_macro = _loaded_noop

    def _loaded_gen_macro(self, tp, name, module, library):
        if tp == '...':
            check_value = None
        else:
            check_value = tp     # an integer
        value = self._load_constant(True, tp, name, module,
                                    check_value=check_value)
        setattr(library, name, value)
        type(library)._cffi_dir.append(name)

    # ----------
    # global variables

    def _generate_gen_variable_decl(self, tp, name):
        if isinstance(tp, model.ArrayType):
            if tp.length_is_unknown():
                prnt = self._prnt
                funcname = '_cffi_sizeof_%s' % (name,)
                self.export_symbols.append(funcname)
                prnt("size_t %s(void)" % funcname)
                prnt("{")
                prnt("  return sizeof(%s);" % (name,))
                prnt("}")
            tp_ptr = model.PointerType(tp.item)
            self._generate_gen_const(False, name, tp_ptr)
        else:
            tp_ptr = model.PointerType(tp)
            self._generate_gen_const(False, name, tp_ptr, category='var')

    _loading_gen_variable = _loaded_noop

    def _loaded_gen_variable(self, tp, name, module, library):
        if isinstance(tp, model.ArrayType):   # int a[5] is "constant" in the
                                              # sense that "a=..." is forbidden
            if tp.length_is_unknown():
                funcname = '_cffi_sizeof_%s' % (name,)
                BFunc = self.ffi._typeof_locked('size_t(*)(void)')[0]
                function = module.load_function(BFunc, funcname)
                size = function()
                BItemType = self.ffi._get_cached_btype(tp.item)
                length, rest = divmod(size, self.ffi.sizeof(BItemType))
                if rest != 0:
                    raise VerificationError(
                        "bad size: %r does not seem to be an array of %s" %
                        (name, tp.item))
                tp = tp.resolve_length(length)
            tp_ptr = model.PointerType(tp.item)
            value = self._load_constant(False, tp_ptr, name, module)
            # 'value' is a <cdata 'type *'> which we have to replace with
            # a <cdata 'type[N]'> if the N is actually known
            if tp.length is not None:
                BArray = self.ffi._get_cached_btype(tp)
                value = self.ffi.cast(BArray, value)
            setattr(library, name, value)
            type(library)._cffi_dir.append(name)
            return
        # remove ptr=<cdata 'int *'> from the library instance, and replace
        # it by a property on the class, which reads/writes into ptr[0].
        funcname = '_cffi_var_%s' % name
        BFunc = self.ffi._typeof_locked(tp.get_c_name('*(*)(void)', name))[0]
        function = module.load_function(BFunc, funcname)
        ptr = function()
        def getter(library):
            return ptr[0]
        def setter(library, value):
            ptr[0] = value
        setattr(type(library), name, property(getter, setter))
        type(library)._cffi_dir.append(name)

cffimod_header = r'''
#include <stdio.h>
#include <stddef.h>
#include <stdarg.h>
#include <errno.h>
#include <sys/types.h>   /* XXX for ssize_t on some platforms */

/* this block of #ifs should be kept exactly identical between
   c/_cffi_backend.c, cffi/vengine_cpy.py, cffi/vengine_gen.py
   and cffi/_cffi_include.h */
#if defined(_MSC_VER)
# include <malloc.h>   /* for alloca() */
# if _MSC_VER < 1600   /* MSVC < 2010 */
   typedef __int8 int8_t;
   typedef __int16 int16_t;
   typedef __int32 int32_t;
   typedef __int64 int64_t;
   typedef unsigned __int8 uint8_t;
   typedef unsigned __int16 uint16_t;
   typedef unsigned __int32 uint32_t;
   typedef unsigned __int64 uint64_t;
   typedef __int8 int_least8_t;
   typedef __int16 int_least16_t;
   typedef __int32 int_least32_t;
   typedef __int64 int_least64_t;
   typedef unsigned __int8 uint_least8_t;
   typedef unsigned __int16 uint_least16_t;
   typedef unsigned __int32 uint_least32_t;
   typedef unsigned __int64 uint_least64_t;
   typedef __int8 int_fast8_t;
   typedef __int16 int_fast16_t;
   typedef __int32 int_fast32_t;
   typedef __int64 int_fast64_t;
   typedef unsigned __int8 uint_fast8_t;
   typedef unsigned __int16 uint_fast16_t;
   typedef unsigned __int32 uint_fast32_t;
   typedef unsigned __int64 uint_fast64_t;
   typedef __int64 intmax_t;
   typedef unsigned __int64 uintmax_t;
# else
#  include <stdint.h>
# endif
# if _MSC_VER < 1800   /* MSVC < 2013 */
#  ifndef __cplusplus
    typedef unsigned char _Bool;
#  endif
# endif
# define _cffi_float_complex_t   _Fcomplex    /* include <complex.h> for it */
# define _cffi_double_complex_t  _Dcomplex    /* include <complex.h> for it */
#else
# include <stdint.h>
# if (defined (__SVR4) && defined (__sun)) || defined(_AIX) || defined(__hpux)
#  include <alloca.h>
# endif
# define _cffi_float_complex_t   float _Complex
# define _cffi_double_complex_t  double _Complex
#endif
'''

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\guardrails\guardrail_hooks\presidio.py ===
# +-----------------------------------------------+
# |                                               |
# |               PII Masking                     |
# |         with Microsoft Presidio               |
# |   https://github.com/BerriAI/litellm/issues/  |
# +-----------------------------------------------+
#
#  Tell us how we can improve! - Krrish & Ishaan


import asyncio
import json
import uuid
from datetime import datetime
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
)

import aiohttp

import litellm  # noqa: E401
from litellm import get_secret
from litellm._logging import verbose_proxy_logger
from litellm.caching.caching import DualCache
from litellm.exceptions import BlockedPiiEntityError
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.proxy._types import UserAPIKeyAuth
from litellm.types.guardrails import (
    GuardrailEventHooks,
    LitellmParams,
    PiiAction,
    PiiEntityType,
    PresidioPerRequestConfig,
)
from litellm.types.proxy.guardrails.guardrail_hooks.presidio import (
    PresidioAnalyzeRequest,
    PresidioAnalyzeResponseItem,
)
from litellm.types.utils import CallTypes as LitellmCallTypes
from litellm.utils import (
    EmbeddingResponse,
    ImageResponse,
    ModelResponse,
    ModelResponseStream,
    StreamingChoices,
)


class _OPTIONAL_PresidioPIIMasking(CustomGuardrail):
    user_api_key_cache = None
    ad_hoc_recognizers = None

    # Class variables or attributes
    def __init__(
        self,
        mock_testing: bool = False,
        mock_redacted_text: Optional[dict] = None,
        presidio_analyzer_api_base: Optional[str] = None,
        presidio_anonymizer_api_base: Optional[str] = None,
        output_parse_pii: Optional[bool] = False,
        presidio_ad_hoc_recognizers: Optional[str] = None,
        logging_only: Optional[bool] = None,
        pii_entities_config: Optional[Dict[PiiEntityType, PiiAction]] = None,
        presidio_language: Optional[str] = None,
        **kwargs,
    ):
        if logging_only is True:
            self.logging_only = True
            kwargs["event_hook"] = GuardrailEventHooks.logging_only
        super().__init__(**kwargs)
        self.pii_tokens: dict = (
            {}
        )  # mapping of PII token to original text - only used with Presidio `replace` operation
        self.mock_redacted_text = mock_redacted_text
        self.output_parse_pii = output_parse_pii or False
        self.pii_entities_config: Dict[PiiEntityType, PiiAction] = (
            pii_entities_config or {}
        )
        self.presidio_language = presidio_language or "en"
        if mock_testing is True:  # for testing purposes only
            return

        ad_hoc_recognizers = presidio_ad_hoc_recognizers
        if ad_hoc_recognizers is not None:
            try:
                with open(ad_hoc_recognizers, "r") as file:
                    self.ad_hoc_recognizers = json.load(file)
            except FileNotFoundError:
                raise Exception(f"File not found. file_path={ad_hoc_recognizers}")
            except json.JSONDecodeError as e:
                raise Exception(
                    f"Error decoding JSON file: {str(e)}, file_path={ad_hoc_recognizers}"
                )
            except Exception as e:
                raise Exception(
                    f"An error occurred: {str(e)}, file_path={ad_hoc_recognizers}"
                )
        self.validate_environment(
            presidio_analyzer_api_base=presidio_analyzer_api_base,
            presidio_anonymizer_api_base=presidio_anonymizer_api_base,
        )

    def validate_environment(
        self,
        presidio_analyzer_api_base: Optional[str] = None,
        presidio_anonymizer_api_base: Optional[str] = None,
    ):
        self.presidio_analyzer_api_base: Optional[
            str
        ] = presidio_analyzer_api_base or get_secret(
            "PRESIDIO_ANALYZER_API_BASE", None
        )  # type: ignore
        self.presidio_anonymizer_api_base: Optional[
            str
        ] = presidio_anonymizer_api_base or litellm.get_secret(
            "PRESIDIO_ANONYMIZER_API_BASE", None
        )  # type: ignore

        if self.presidio_analyzer_api_base is None:
            raise Exception("Missing `PRESIDIO_ANALYZER_API_BASE` from environment")
        if not self.presidio_analyzer_api_base.endswith("/"):
            self.presidio_analyzer_api_base += "/"
        if not (
            self.presidio_analyzer_api_base.startswith("http://")
            or self.presidio_analyzer_api_base.startswith("https://")
        ):
            # add http:// if unset, assume communicating over private network - e.g. render
            self.presidio_analyzer_api_base = (
                "http://" + self.presidio_analyzer_api_base
            )

        if self.presidio_anonymizer_api_base is None:
            raise Exception("Missing `PRESIDIO_ANONYMIZER_API_BASE` from environment")
        if not self.presidio_anonymizer_api_base.endswith("/"):
            self.presidio_anonymizer_api_base += "/"
        if not (
            self.presidio_anonymizer_api_base.startswith("http://")
            or self.presidio_anonymizer_api_base.startswith("https://")
        ):
            # add http:// if unset, assume communicating over private network - e.g. render
            self.presidio_anonymizer_api_base = (
                "http://" + self.presidio_anonymizer_api_base
            )

    def _get_presidio_analyze_request_payload(
        self,
        text: str,
        presidio_config: Optional[PresidioPerRequestConfig],
        request_data: dict,
    ) -> PresidioAnalyzeRequest:
        """
        Construct the payload for the Presidio analyze request

        API Ref: https://microsoft.github.io/presidio/api-docs/api-docs.html#tag/Analyzer/paths/~1analyze/post
        """
        analyze_payload: PresidioAnalyzeRequest = PresidioAnalyzeRequest(
            text=text,
            language=self.presidio_language,
        )
        ##################################################################
        ###### Check if user has configured any params for this guardrail
        ################################################################
        if self.ad_hoc_recognizers is not None:
            analyze_payload["ad_hoc_recognizers"] = self.ad_hoc_recognizers

        if self.pii_entities_config:
            analyze_payload["entities"] = list(self.pii_entities_config.keys())

        ##################################################################
        ######### End of adding config params
        ##################################################################

        # Check if client side request passed any dynamic params
        if presidio_config and presidio_config.language:
            analyze_payload["language"] = presidio_config.language

        casted_analyze_payload: dict = cast(dict, analyze_payload)
        casted_analyze_payload.update(
            self.get_guardrail_dynamic_request_body_params(request_data=request_data)
        )
        return cast(PresidioAnalyzeRequest, casted_analyze_payload)

    async def analyze_text(
        self,
        text: str,
        presidio_config: Optional[PresidioPerRequestConfig],
        request_data: dict,
    ) -> Union[List[PresidioAnalyzeResponseItem], Dict]:
        """
        Send text to the Presidio analyzer endpoint and get analysis results
        """
        try:
            async with aiohttp.ClientSession() as session:
                if self.mock_redacted_text is not None:
                    return self.mock_redacted_text

                # Make the request to /analyze
                analyze_url = f"{self.presidio_analyzer_api_base}analyze"

                analyze_payload: PresidioAnalyzeRequest = (
                    self._get_presidio_analyze_request_payload(
                        text=text,
                        presidio_config=presidio_config,
                        request_data=request_data,
                    )
                )

                verbose_proxy_logger.debug(
                    "Making request to: %s with payload: %s",
                    analyze_url,
                    analyze_payload,
                )

                async with session.post(analyze_url, json=analyze_payload) as response:
                    analyze_results = await response.json()
                    verbose_proxy_logger.debug("analyze_results: %s", analyze_results)
                    final_results = []
                    for item in analyze_results:
                        final_results.append(PresidioAnalyzeResponseItem(**item))
                    return final_results
        except Exception as e:
            raise e

    async def anonymize_text(
        self,
        text: str,
        analyze_results: Any,
        output_parse_pii: bool,
        masked_entity_count: Dict[str, int],
    ) -> str:
        """
        Send analysis results to the Presidio anonymizer endpoint to get redacted text
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Make the request to /anonymize
                anonymize_url = f"{self.presidio_anonymizer_api_base}anonymize"
                verbose_proxy_logger.debug("Making request to: %s", anonymize_url)
                anonymize_payload = {
                    "text": text,
                    "analyzer_results": analyze_results,
                }

                async with session.post(
                    anonymize_url, json=anonymize_payload
                ) as response:
                    redacted_text = await response.json()

                new_text = text
                if redacted_text is not None:
                    verbose_proxy_logger.debug("redacted_text: %s", redacted_text)
                    for item in redacted_text["items"]:
                        start = item["start"]
                        end = item["end"]
                        replacement = item["text"]  # replacement token
                        if item["operator"] == "replace" and output_parse_pii is True:
                            # check if token in dict
                            # if exists, add a uuid to the replacement token for swapping back to the original text in llm response output parsing
                            if replacement in self.pii_tokens:
                                replacement = replacement + str(uuid.uuid4())

                            self.pii_tokens[replacement] = new_text[
                                start:end
                            ]  # get text it'll replace

                        new_text = new_text[:start] + replacement + new_text[end:]
                        entity_type = item.get("entity_type", None)
                        if entity_type is not None:
                            masked_entity_count[entity_type] = (
                                masked_entity_count.get(entity_type, 0) + 1
                            )
                    return redacted_text["text"]
                else:
                    raise Exception(f"Invalid anonymizer response: {redacted_text}")
        except Exception as e:
            raise e

    def raise_exception_if_blocked_entities_detected(
        self, analyze_results: Union[List[PresidioAnalyzeResponseItem], Dict]
    ):
        """
        Raise an exception if blocked entities are detected
        """
        if self.pii_entities_config is None:
            return

        if isinstance(analyze_results, Dict):
            # if mock testing is enabled, analyze_results is a dict
            # we don't need to raise an exception in this case
            return

        for result in analyze_results:
            entity_type = result.get("entity_type")

            if entity_type:
                casted_entity_type: PiiEntityType = cast(PiiEntityType, entity_type)
                if (
                    casted_entity_type in self.pii_entities_config
                    and self.pii_entities_config[casted_entity_type] == PiiAction.BLOCK
                ):
                    raise BlockedPiiEntityError(
                        entity_type=entity_type,
                        guardrail_name=self.guardrail_name,
                    )

    async def check_pii(
        self,
        text: str,
        output_parse_pii: bool,
        presidio_config: Optional[PresidioPerRequestConfig],
        request_data: dict,
    ) -> str:
        """
        Calls Presidio Analyze + Anonymize endpoints for PII Analysis + Masking
        """
        start_time = datetime.now()
        analyze_results: Optional[Union[List[PresidioAnalyzeResponseItem], Dict]] = None
        status: Literal["success", "failure"] = "success"
        masked_entity_count: Dict[str, int] = {}
        exception_str: str = ""
        try:
            if self.mock_redacted_text is not None:
                redacted_text = self.mock_redacted_text
            else:
                # First get analysis results
                analyze_results = await self.analyze_text(
                    text=text,
                    presidio_config=presidio_config,
                    request_data=request_data,
                )
                verbose_proxy_logger.debug("analyze_results: %s", analyze_results)

                ####################################################
                # Blocked Entities check
                ####################################################
                self.raise_exception_if_blocked_entities_detected(
                    analyze_results=analyze_results
                )

                # Then anonymize the text using the analysis results
                return await self.anonymize_text(
                    text=text,
                    analyze_results=analyze_results,
                    output_parse_pii=output_parse_pii,
                    masked_entity_count=masked_entity_count,
                )
            return redacted_text["text"]
        except Exception as e:
            status = "failure"
            exception_str = str(e)
            raise e
        finally:
            ####################################################
            # Create Guardrail Trace for logging on Langfuse, Datadog, etc.
            ####################################################
            guardrail_json_response: Union[Exception, str, dict, List[dict]] = {}
            if status == "success":
                if isinstance(analyze_results, List):
                    guardrail_json_response = [dict(item) for item in analyze_results]
            else:
                guardrail_json_response = exception_str
            self.add_standard_logging_guardrail_information_to_request_data(
                guardrail_json_response=guardrail_json_response,
                request_data=request_data,
                guardrail_status=status,
                start_time=start_time.timestamp(),
                end_time=datetime.now().timestamp(),
                duration=(datetime.now() - start_time).total_seconds(),
                masked_entity_count=masked_entity_count,
            )

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: str,
    ):
        """
        - Check if request turned off pii
            - Check if user allowed to turn off pii (key permissions -> 'allow_pii_controls')

        - Take the request data
        - Call /analyze -> get the results
        - Call /anonymize w/ the analyze results -> get the redacted text

        For multiple messages in /chat/completions, we'll need to call them in parallel.
        """

        try:
            content_safety = data.get("content_safety", None)
            verbose_proxy_logger.debug("content_safety: %s", content_safety)
            presidio_config = self.get_presidio_settings_from_request_data(data)
            if call_type in [
                LitellmCallTypes.completion.value,
                LitellmCallTypes.acompletion.value,
            ]:
                messages = data["messages"]
                tasks = []

                for m in messages:
                    content = m.get("content", None)
                    if content is None:
                        continue
                    if isinstance(content, str):
                        tasks.append(
                            self.check_pii(
                                text=content,
                                output_parse_pii=self.output_parse_pii,
                                presidio_config=presidio_config,
                                request_data=data,
                            )
                        )
                responses = await asyncio.gather(*tasks)
                for index, r in enumerate(responses):
                    content = messages[index].get("content", None)
                    if content is None:
                        continue
                    if isinstance(content, str):
                        messages[index][
                            "content"
                        ] = r  # replace content with redacted string
                verbose_proxy_logger.info(
                    f"Presidio PII Masking: Redacted pii message: {data['messages']}"
                )
                data["messages"] = messages
            else:
                verbose_proxy_logger.debug(
                    f"Not running async_pre_call_hook for call_type={call_type}"
                )
            return data
        except Exception as e:
            raise e

    def logging_hook(
        self, kwargs: dict, result: Any, call_type: str
    ) -> Tuple[dict, Any]:
        from concurrent.futures import ThreadPoolExecutor

        def run_in_new_loop():
            """Run the coroutine in a new event loop within this thread."""
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                return new_loop.run_until_complete(
                    self.async_logging_hook(
                        kwargs=kwargs, result=result, call_type=call_type
                    )
                )
            finally:
                new_loop.close()
                asyncio.set_event_loop(None)

        try:
            # First, try to get the current event loop
            _ = asyncio.get_running_loop()
            # If we're already in an event loop, run in a separate thread
            # to avoid nested event loop issues
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_new_loop)
                return future.result()

        except RuntimeError:
            # No running event loop, we can safely run in this thread
            return run_in_new_loop()

    async def async_logging_hook(
        self, kwargs: dict, result: Any, call_type: str
    ) -> Tuple[dict, Any]:
        """
        Masks the input before logging to langfuse, datadog, etc.
        """
        if (
            call_type == "completion" or call_type == "acompletion"
        ):  # /chat/completions requests
            messages: Optional[List] = kwargs.get("messages", None)
            tasks = []

            if messages is None:
                return kwargs, result

            presidio_config = self.get_presidio_settings_from_request_data(kwargs)

            for m in messages:
                text_str = ""
                content = m.get("content", None)
                if content is None:
                    continue
                if isinstance(content, str):
                    text_str = content
                    tasks.append(
                        self.check_pii(
                            text=text_str,
                            output_parse_pii=False,
                            presidio_config=presidio_config,
                            request_data=kwargs,
                        )
                    )  # need to pass separately b/c presidio has context window limits
            responses = await asyncio.gather(*tasks)
            for index, r in enumerate(responses):
                content = messages[index].get("content", None)
                if content is None:
                    continue
                if isinstance(content, str):
                    messages[index][
                        "content"
                    ] = r  # replace content with redacted string
            verbose_proxy_logger.info(
                f"Presidio PII Masking: Redacted pii message: {messages}"
            )
            kwargs["messages"] = messages

        return kwargs, result

    async def async_post_call_success_hook(  # type: ignore
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        response: Union[ModelResponse, EmbeddingResponse, ImageResponse],
    ):
        """
        Output parse the response object to replace the masked tokens with user sent values
        """
        verbose_proxy_logger.debug(
            f"PII Masking Args: self.output_parse_pii={self.output_parse_pii}; type of response={type(response)}"
        )

        if self.output_parse_pii is False and litellm.output_parse_pii is False:
            return response

        if isinstance(response, ModelResponse) and not isinstance(
            response.choices[0], StreamingChoices
        ):  # /chat/completions requests
            if isinstance(response.choices[0].message.content, str):
                verbose_proxy_logger.debug(
                    f"self.pii_tokens: {self.pii_tokens}; initial response: {response.choices[0].message.content}"
                )
                for key, value in self.pii_tokens.items():
                    response.choices[0].message.content = response.choices[
                        0
                    ].message.content.replace(key, value)
        return response

    async def async_post_call_streaming_iterator_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        response: Any,
        request_data: dict,
    ) -> AsyncGenerator[ModelResponseStream, None]:
        """
        Process streaming response chunks to unmask PII tokens when needed.

        If PII processing is enabled, this collects all chunks, applies PII unmasking,
        and returns a reconstructed stream. Otherwise, it passes through the original stream.
        """
        # If PII unmasking not needed, just pass through the original stream
        if not (self.output_parse_pii and self.pii_tokens):
            async for chunk in response:
                yield chunk
            return

        # Import here to avoid circular imports
        from litellm.llms.base_llm.base_model_iterator import MockResponseIterator
        from litellm.types.utils import Choices, Message

        try:
            # Collect all chunks to process them together
            collected_content = ""
            last_chunk = None

            async for chunk in response:
                last_chunk = chunk

                # Extract content safely with proper attribute checks
                if (
                    hasattr(chunk, "choices")
                    and chunk.choices
                    and hasattr(chunk.choices[0], "delta")
                    and hasattr(chunk.choices[0].delta, "content")
                    and isinstance(chunk.choices[0].delta.content, str)
                ):
                    collected_content += chunk.choices[0].delta.content

            # No need to proceed if we didn't capture a valid chunk
            if not last_chunk:
                async for chunk in response:
                    yield chunk
                return

            # Apply PII unmasking to the complete content
            for token, original_text in self.pii_tokens.items():
                collected_content = collected_content.replace(token, original_text)

            # Reconstruct the response with unmasked content
            mock_response = MockResponseIterator(
                model_response=ModelResponse(
                    id=last_chunk.id,
                    object=last_chunk.object,
                    created=last_chunk.created,
                    model=last_chunk.model,
                    choices=[
                        Choices(
                            message=Message(
                                role="assistant",
                                content=collected_content,
                            ),
                            index=0,
                            finish_reason="stop",
                        )
                    ],
                ),
                json_mode=False,
            )

            # Return the reconstructed stream
            async for chunk in mock_response:
                yield chunk

        except Exception as e:
            verbose_proxy_logger.error(f"Error in PII streaming processing: {str(e)}")
            # Fallback to original stream on error
            async for chunk in response:
                yield chunk

    def get_presidio_settings_from_request_data(
        self, data: dict
    ) -> Optional[PresidioPerRequestConfig]:
        if "metadata" in data:
            _metadata = data.get("metadata", None)
            if _metadata is None:
                return None
            _guardrail_config = _metadata.get("guardrail_config")
            if _guardrail_config:
                _presidio_config = PresidioPerRequestConfig(**_guardrail_config)
                return _presidio_config

        return None

    def print_verbose(self, print_statement):
        try:
            verbose_proxy_logger.debug(print_statement)
            if litellm.set_verbose:
                print(print_statement)  # noqa
        except Exception:
            pass

    async def apply_guardrail(
        self,
        text: str,
        language: Optional[str] = None,
        entities: Optional[List[PiiEntityType]] = None,
    ) -> str:
        """
        UI will call this function to check:
            1. If the connection to the guardrail is working
            2. When Testing the guardrail with some text, this function will be called with the input text and returns a text after applying the guardrail
        """
        text = await self.check_pii(
            text=text,
            output_parse_pii=self.output_parse_pii,
            presidio_config=None,
            request_data={},
        )
        return text

    def update_in_memory_litellm_params(self, litellm_params: LitellmParams) -> None:
        """
        Update the guardrails litellm params in memory
        """
        if litellm_params.pii_entities_config:
            self.pii_entities_config = litellm_params.pii_entities_config

# === NexusCore/openenv\Lib\site-packages\websocket\_app.py ===
import inspect
import selectors
import socket
import threading
import time
from typing import Any, Callable, Optional, Union

from . import _logging
from ._abnf import ABNF
from ._core import WebSocket, getdefaulttimeout
from ._exceptions import (
    WebSocketConnectionClosedException,
    WebSocketException,
    WebSocketTimeoutException,
)
from ._ssl_compat import SSLEOFError
from ._url import parse_url

"""
_app.py
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

__all__ = ["WebSocketApp"]

RECONNECT = 0


def setReconnect(reconnectInterval: int) -> None:
    global RECONNECT
    RECONNECT = reconnectInterval


class DispatcherBase:
    """
    DispatcherBase
    """

    def __init__(self, app: Any, ping_timeout: Union[float, int, None]) -> None:
        self.app = app
        self.ping_timeout = ping_timeout

    def timeout(self, seconds: Union[float, int, None], callback: Callable) -> None:
        time.sleep(seconds)
        callback()

    def reconnect(self, seconds: int, reconnector: Callable) -> None:
        try:
            _logging.info(
                f"reconnect() - retrying in {seconds} seconds [{len(inspect.stack())} frames in stack]"
            )
            time.sleep(seconds)
            reconnector(reconnecting=True)
        except KeyboardInterrupt as e:
            _logging.info(f"User exited {e}")
            raise e


class Dispatcher(DispatcherBase):
    """
    Dispatcher
    """

    def read(
        self,
        sock: socket.socket,
        read_callback: Callable,
        check_callback: Callable,
    ) -> None:
        sel = selectors.DefaultSelector()
        sel.register(self.app.sock.sock, selectors.EVENT_READ)
        try:
            while self.app.keep_running:
                if sel.select(self.ping_timeout):
                    if not read_callback():
                        break
                check_callback()
        finally:
            sel.close()


class SSLDispatcher(DispatcherBase):
    """
    SSLDispatcher
    """

    def read(
        self,
        sock: socket.socket,
        read_callback: Callable,
        check_callback: Callable,
    ) -> None:
        sock = self.app.sock.sock
        sel = selectors.DefaultSelector()
        sel.register(sock, selectors.EVENT_READ)
        try:
            while self.app.keep_running:
                if self.select(sock, sel):
                    if not read_callback():
                        break
                check_callback()
        finally:
            sel.close()

    def select(self, sock, sel: selectors.DefaultSelector):
        sock = self.app.sock.sock
        if sock.pending():
            return [
                sock,
            ]

        r = sel.select(self.ping_timeout)

        if len(r) > 0:
            return r[0][0]


class WrappedDispatcher:
    """
    WrappedDispatcher
    """

    def __init__(self, app, ping_timeout: Union[float, int, None], dispatcher) -> None:
        self.app = app
        self.ping_timeout = ping_timeout
        self.dispatcher = dispatcher
        dispatcher.signal(2, dispatcher.abort)  # keyboard interrupt

    def read(
        self,
        sock: socket.socket,
        read_callback: Callable,
        check_callback: Callable,
    ) -> None:
        self.dispatcher.read(sock, read_callback)
        self.ping_timeout and self.timeout(self.ping_timeout, check_callback)

    def timeout(self, seconds: float, callback: Callable) -> None:
        self.dispatcher.timeout(seconds, callback)

    def reconnect(self, seconds: int, reconnector: Callable) -> None:
        self.timeout(seconds, reconnector)


class WebSocketApp:
    """
    Higher level of APIs are provided. The interface is like JavaScript WebSocket object.
    """

    def __init__(
        self,
        url: str,
        header: Union[list, dict, Callable, None] = None,
        on_open: Optional[Callable[[WebSocket], None]] = None,
        on_reconnect: Optional[Callable[[WebSocket], None]] = None,
        on_message: Optional[Callable[[WebSocket, Any], None]] = None,
        on_error: Optional[Callable[[WebSocket, Any], None]] = None,
        on_close: Optional[Callable[[WebSocket, Any, Any], None]] = None,
        on_ping: Optional[Callable] = None,
        on_pong: Optional[Callable] = None,
        on_cont_message: Optional[Callable] = None,
        keep_running: bool = True,
        get_mask_key: Optional[Callable] = None,
        cookie: Optional[str] = None,
        subprotocols: Optional[list] = None,
        on_data: Optional[Callable] = None,
        socket: Optional[socket.socket] = None,
    ) -> None:
        """
        WebSocketApp initialization

        Parameters
        ----------
        url: str
            Websocket url.
        header: list or dict or Callable
            Custom header for websocket handshake.
            If the parameter is a callable object, it is called just before the connection attempt.
            The returned dict or list is used as custom header value.
            This could be useful in order to properly setup timestamp dependent headers.
        on_open: function
            Callback object which is called at opening websocket.
            on_open has one argument.
            The 1st argument is this class object.
        on_reconnect: function
            Callback object which is called at reconnecting websocket.
            on_reconnect has one argument.
            The 1st argument is this class object.
        on_message: function
            Callback object which is called when received data.
            on_message has 2 arguments.
            The 1st argument is this class object.
            The 2nd argument is utf-8 data received from the server.
        on_error: function
            Callback object which is called when we get error.
            on_error has 2 arguments.
            The 1st argument is this class object.
            The 2nd argument is exception object.
        on_close: function
            Callback object which is called when connection is closed.
            on_close has 3 arguments.
            The 1st argument is this class object.
            The 2nd argument is close_status_code.
            The 3rd argument is close_msg.
        on_cont_message: function
            Callback object which is called when a continuation
            frame is received.
            on_cont_message has 3 arguments.
            The 1st argument is this class object.
            The 2nd argument is utf-8 string which we get from the server.
            The 3rd argument is continue flag. if 0, the data continue
            to next frame data
        on_data: function
            Callback object which is called when a message received.
            This is called before on_message or on_cont_message,
            and then on_message or on_cont_message is called.
            on_data has 4 argument.
            The 1st argument is this class object.
            The 2nd argument is utf-8 string which we get from the server.
            The 3rd argument is data type. ABNF.OPCODE_TEXT or ABNF.OPCODE_BINARY will be came.
            The 4th argument is continue flag. If 0, the data continue
        keep_running: bool
            This parameter is obsolete and ignored.
        get_mask_key: function
            A callable function to get new mask keys, see the
            WebSocket.set_mask_key's docstring for more information.
        cookie: str
            Cookie value.
        subprotocols: list
            List of available sub protocols. Default is None.
        socket: socket
            Pre-initialized stream socket.
        """
        self.url = url
        self.header = header if header is not None else []
        self.cookie = cookie

        self.on_open = on_open
        self.on_reconnect = on_reconnect
        self.on_message = on_message
        self.on_data = on_data
        self.on_error = on_error
        self.on_close = on_close
        self.on_ping = on_ping
        self.on_pong = on_pong
        self.on_cont_message = on_cont_message
        self.keep_running = False
        self.get_mask_key = get_mask_key
        self.sock: Optional[WebSocket] = None
        self.last_ping_tm = float(0)
        self.last_pong_tm = float(0)
        self.ping_thread: Optional[threading.Thread] = None
        self.stop_ping: Optional[threading.Event] = None
        self.ping_interval = float(0)
        self.ping_timeout: Union[float, int, None] = None
        self.ping_payload = ""
        self.subprotocols = subprotocols
        self.prepared_socket = socket
        self.has_errored = False
        self.has_done_teardown = False
        self.has_done_teardown_lock = threading.Lock()

    def send(self, data: Union[bytes, str], opcode: int = ABNF.OPCODE_TEXT) -> None:
        """
        send message

        Parameters
        ----------
        data: str
            Message to send. If you set opcode to OPCODE_TEXT,
            data must be utf-8 string or unicode.
        opcode: int
            Operation code of data. Default is OPCODE_TEXT.
        """

        if not self.sock or self.sock.send(data, opcode) == 0:
            raise WebSocketConnectionClosedException("Connection is already closed.")

    def send_text(self, text_data: str) -> None:
        """
        Sends UTF-8 encoded text.
        """
        if not self.sock or self.sock.send(text_data, ABNF.OPCODE_TEXT) == 0:
            raise WebSocketConnectionClosedException("Connection is already closed.")

    def send_bytes(self, data: Union[bytes, bytearray]) -> None:
        """
        Sends a sequence of bytes.
        """
        if not self.sock or self.sock.send(data, ABNF.OPCODE_BINARY) == 0:
            raise WebSocketConnectionClosedException("Connection is already closed.")

    def close(self, **kwargs) -> None:
        """
        Close websocket connection.
        """
        self.keep_running = False
        if self.sock:
            self.sock.close(**kwargs)
            self.sock = None

    def _start_ping_thread(self) -> None:
        self.last_ping_tm = self.last_pong_tm = float(0)
        self.stop_ping = threading.Event()
        self.ping_thread = threading.Thread(target=self._send_ping)
        self.ping_thread.daemon = True
        self.ping_thread.start()

    def _stop_ping_thread(self) -> None:
        if self.stop_ping:
            self.stop_ping.set()
        if self.ping_thread and self.ping_thread.is_alive():
            self.ping_thread.join(3)
        self.last_ping_tm = self.last_pong_tm = float(0)

    def _send_ping(self) -> None:
        if self.stop_ping.wait(self.ping_interval) or self.keep_running is False:
            return
        while not self.stop_ping.wait(self.ping_interval) and self.keep_running is True:
            if self.sock:
                self.last_ping_tm = time.time()
                try:
                    _logging.debug("Sending ping")
                    self.sock.ping(self.ping_payload)
                except Exception as e:
                    _logging.debug(f"Failed to send ping: {e}")

    def run_forever(
        self,
        sockopt: tuple = None,
        sslopt: dict = None,
        ping_interval: Union[float, int] = 0,
        ping_timeout: Union[float, int, None] = None,
        ping_payload: str = "",
        http_proxy_host: str = None,
        http_proxy_port: Union[int, str] = None,
        http_no_proxy: list = None,
        http_proxy_auth: tuple = None,
        http_proxy_timeout: Optional[float] = None,
        skip_utf8_validation: bool = False,
        host: str = None,
        origin: str = None,
        dispatcher=None,
        suppress_origin: bool = False,
        proxy_type: str = None,
        reconnect: int = None,
    ) -> bool:
        """
        Run event loop for WebSocket framework.

        This loop is an infinite loop and is alive while websocket is available.

        Parameters
        ----------
        sockopt: tuple
            Values for socket.setsockopt.
            sockopt must be tuple
            and each element is argument of sock.setsockopt.
        sslopt: dict
            Optional dict object for ssl socket option.
        ping_interval: int or float
            Automatically send "ping" command
            every specified period (in seconds).
            If set to 0, no ping is sent periodically.
        ping_timeout: int or float
            Timeout (in seconds) if the pong message is not received.
        ping_payload: str
            Payload message to send with each ping.
        http_proxy_host: str
            HTTP proxy host name.
        http_proxy_port: int or str
            HTTP proxy port. If not set, set to 80.
        http_no_proxy: list
            Whitelisted host names that don't use the proxy.
        http_proxy_timeout: int or float
            HTTP proxy timeout, default is 60 sec as per python-socks.
        http_proxy_auth: tuple
            HTTP proxy auth information. tuple of username and password. Default is None.
        skip_utf8_validation: bool
            skip utf8 validation.
        host: str
            update host header.
        origin: str
            update origin header.
        dispatcher: Dispatcher object
            customize reading data from socket.
        suppress_origin: bool
            suppress outputting origin header.
        proxy_type: str
            type of proxy from: http, socks4, socks4a, socks5, socks5h
        reconnect: int
            delay interval when reconnecting

        Returns
        -------
        teardown: bool
            False if the `WebSocketApp` is closed or caught KeyboardInterrupt,
            True if any other exception was raised during a loop.
        """

        if reconnect is None:
            reconnect = RECONNECT

        if ping_timeout is not None and ping_timeout <= 0:
            raise WebSocketException("Ensure ping_timeout > 0")
        if ping_interval is not None and ping_interval < 0:
            raise WebSocketException("Ensure ping_interval >= 0")
        if ping_timeout and ping_interval and ping_interval <= ping_timeout:
            raise WebSocketException("Ensure ping_interval > ping_timeout")
        if not sockopt:
            sockopt = ()
        if not sslopt:
            sslopt = {}
        if self.sock:
            raise WebSocketException("socket is already opened")

        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.ping_payload = ping_payload
        self.has_done_teardown = False
        self.keep_running = True

        def teardown(close_frame: ABNF = None):
            """
            Tears down the connection.

            Parameters
            ----------
            close_frame: ABNF frame
                If close_frame is set, the on_close handler is invoked
                with the statusCode and reason from the provided frame.
            """

            # teardown() is called in many code paths to ensure resources are cleaned up and on_close is fired.
            # To ensure the work is only done once, we use this bool and lock.
            with self.has_done_teardown_lock:
                if self.has_done_teardown:
                    return
                self.has_done_teardown = True

            self._stop_ping_thread()
            self.keep_running = False
            if self.sock:
                self.sock.close()
            close_status_code, close_reason = self._get_close_args(
                close_frame if close_frame else None
            )
            self.sock = None

            # Finally call the callback AFTER all teardown is complete
            self._callback(self.on_close, close_status_code, close_reason)

        def setSock(reconnecting: bool = False) -> None:
            if reconnecting and self.sock:
                self.sock.shutdown()

            self.sock = WebSocket(
                self.get_mask_key,
                sockopt=sockopt,
                sslopt=sslopt,
                fire_cont_frame=self.on_cont_message is not None,
                skip_utf8_validation=skip_utf8_validation,
                enable_multithread=True,
            )

            self.sock.settimeout(getdefaulttimeout())
            try:
                header = self.header() if callable(self.header) else self.header

                self.sock.connect(
                    self.url,
                    header=header,
                    cookie=self.cookie,
                    http_proxy_host=http_proxy_host,
                    http_proxy_port=http_proxy_port,
                    http_no_proxy=http_no_proxy,
                    http_proxy_auth=http_proxy_auth,
                    http_proxy_timeout=http_proxy_timeout,
                    subprotocols=self.subprotocols,
                    host=host,
                    origin=origin,
                    suppress_origin=suppress_origin,
                    proxy_type=proxy_type,
                    socket=self.prepared_socket,
                )

                _logging.info("Websocket connected")

                if self.ping_interval:
                    self._start_ping_thread()

                if reconnecting and self.on_reconnect:
                    self._callback(self.on_reconnect)
                else:
                    self._callback(self.on_open)

                dispatcher.read(self.sock.sock, read, check)
            except (
                WebSocketConnectionClosedException,
                ConnectionRefusedError,
                KeyboardInterrupt,
                SystemExit,
                Exception,
            ) as e:
                handleDisconnect(e, reconnecting)

        def read() -> bool:
            if not self.keep_running:
                return teardown()

            try:
                op_code, frame = self.sock.recv_data_frame(True)
            except (
                WebSocketConnectionClosedException,
                KeyboardInterrupt,
                SSLEOFError,
            ) as e:
                if custom_dispatcher:
                    return handleDisconnect(e, bool(reconnect))
                else:
                    raise e

            if op_code == ABNF.OPCODE_CLOSE:
                return teardown(frame)
            elif op_code == ABNF.OPCODE_PING:
                self._callback(self.on_ping, frame.data)
            elif op_code == ABNF.OPCODE_PONG:
                self.last_pong_tm = time.time()
                self._callback(self.on_pong, frame.data)
            elif op_code == ABNF.OPCODE_CONT and self.on_cont_message:
                self._callback(self.on_data, frame.data, frame.opcode, frame.fin)
                self._callback(self.on_cont_message, frame.data, frame.fin)
            else:
                data = frame.data
                if op_code == ABNF.OPCODE_TEXT and not skip_utf8_validation:
                    data = data.decode("utf-8")
                self._callback(self.on_data, data, frame.opcode, True)
                self._callback(self.on_message, data)

            return True

        def check() -> bool:
            if self.ping_timeout:
                has_timeout_expired = (
                    time.time() - self.last_ping_tm > self.ping_timeout
                )
                has_pong_not_arrived_after_last_ping = (
                    self.last_pong_tm - self.last_ping_tm < 0
                )
                has_pong_arrived_too_late = (
                    self.last_pong_tm - self.last_ping_tm > self.ping_timeout
                )

                if (
                    self.last_ping_tm
                    and has_timeout_expired
                    and (
                        has_pong_not_arrived_after_last_ping
                        or has_pong_arrived_too_late
                    )
                ):
                    raise WebSocketTimeoutException("ping/pong timed out")
            return True

        def handleDisconnect(
            e: Union[
                WebSocketConnectionClosedException,
                ConnectionRefusedError,
                KeyboardInterrupt,
                SystemExit,
                Exception,
            ],
            reconnecting: bool = False,
        ) -> bool:
            self.has_errored = True
            self._stop_ping_thread()
            if not reconnecting:
                self._callback(self.on_error, e)

            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                teardown()
                # Propagate further
                raise

            if reconnect:
                _logging.info(f"{e} - reconnect")
                if custom_dispatcher:
                    _logging.debug(
                        f"Calling custom dispatcher reconnect [{len(inspect.stack())} frames in stack]"
                    )
                    dispatcher.reconnect(reconnect, setSock)
            else:
                _logging.error(f"{e} - goodbye")
                teardown()

        custom_dispatcher = bool(dispatcher)
        dispatcher = self.create_dispatcher(
            ping_timeout, dispatcher, parse_url(self.url)[3]
        )

        try:
            setSock()
            if not custom_dispatcher and reconnect:
                while self.keep_running:
                    _logging.debug(
                        f"Calling dispatcher reconnect [{len(inspect.stack())} frames in stack]"
                    )
                    dispatcher.reconnect(reconnect, setSock)
        except (KeyboardInterrupt, Exception) as e:
            _logging.info(f"tearing down on exception {e}")
            teardown()
        finally:
            if not custom_dispatcher:
                # Ensure teardown was called before returning from run_forever
                teardown()

        return self.has_errored

    def create_dispatcher(
        self,
        ping_timeout: Union[float, int, None],
        dispatcher: Optional[DispatcherBase] = None,
        is_ssl: bool = False,
    ) -> Union[Dispatcher, SSLDispatcher, WrappedDispatcher]:
        if dispatcher:  # If custom dispatcher is set, use WrappedDispatcher
            return WrappedDispatcher(self, ping_timeout, dispatcher)
        timeout = ping_timeout or 10
        if is_ssl:
            return SSLDispatcher(self, timeout)
        return Dispatcher(self, timeout)

    def _get_close_args(self, close_frame: ABNF) -> list:
        """
        _get_close_args extracts the close code and reason from the close body
        if it exists (RFC6455 says WebSocket Connection Close Code is optional)
        """
        # Need to catch the case where close_frame is None
        # Otherwise the following if statement causes an error
        if not self.on_close or not close_frame:
            return [None, None]

        # Extract close frame status code
        if close_frame.data and len(close_frame.data) >= 2:
            close_status_code = 256 * int(close_frame.data[0]) + int(
                close_frame.data[1]
            )
            reason = close_frame.data[2:]
            if isinstance(reason, bytes):
                reason = reason.decode("utf-8")
            return [close_status_code, reason]
        else:
            # Most likely reached this because len(close_frame_data.data) < 2
            return [None, None]

    def _callback(self, callback, *args) -> None:
        if callback:
            try:
                callback(self, *args)

            except Exception as e:
                _logging.error(f"error from callback {callback}: {e}")
                if self.on_error:
                    self.on_error(self, e)

# === NexusCore/openenv\Lib\site-packages\jedi\inference\names.py ===
from abc import abstractmethod
from inspect import Parameter
from typing import Optional, Tuple

from parso.tree import search_ancestor

from jedi.parser_utils import find_statement_documentation, clean_scope_docstring
from jedi.inference.utils import unite
from jedi.inference.base_value import ValueSet, NO_VALUES
from jedi.inference.cache import inference_state_method_cache
from jedi.inference import docstrings
from jedi.cache import memoize_method
from jedi.inference.helpers import deep_ast_copy, infer_call_of_leaf
from jedi.plugins import plugin_manager


def _merge_name_docs(names):
    doc = ''
    for name in names:
        if doc:
            # In case we have multiple values, just return all of them
            # separated by a few dashes.
            doc += '\n' + '-' * 30 + '\n'
        doc += name.py__doc__()
    return doc


class AbstractNameDefinition:
    start_pos: Optional[Tuple[int, int]] = None
    string_name: str
    parent_context = None
    tree_name = None
    is_value_name = True
    """
    Used for the Jedi API to know if it's a keyword or an actual name.
    """

    @abstractmethod
    def infer(self):
        raise NotImplementedError

    @abstractmethod
    def goto(self):
        # Typically names are already definitions and therefore a goto on that
        # name will always result on itself.
        return {self}

    def get_qualified_names(self, include_module_names=False):
        qualified_names = self._get_qualified_names()
        if qualified_names is None or not include_module_names:
            return qualified_names

        module_names = self.get_root_context().string_names
        if module_names is None:
            return None
        return module_names + qualified_names

    def _get_qualified_names(self):
        # By default, a name has no qualified names.
        return None

    def get_root_context(self):
        return self.parent_context.get_root_context()

    def get_public_name(self):
        return self.string_name

    def __repr__(self):
        if self.start_pos is None:
            return '<%s: string_name=%s>' % (self.__class__.__name__, self.string_name)
        return '<%s: string_name=%s start_pos=%s>' % (self.__class__.__name__,
                                                      self.string_name, self.start_pos)

    def is_import(self):
        return False

    def py__doc__(self):
        return ''

    @property
    def api_type(self):
        return self.parent_context.api_type

    def get_defining_qualified_value(self):
        """
        Returns either None or the value that is public and qualified. Won't
        return a function, because a name in a function is never public.
        """
        return None


class AbstractArbitraryName(AbstractNameDefinition):
    """
    When you e.g. want to complete dicts keys, you probably want to complete
    string literals, which is not really a name, but for Jedi we use this
    concept of Name for completions as well.
    """
    is_value_name = False

    def __init__(self, inference_state, string):
        self.inference_state = inference_state
        self.string_name = string
        self.parent_context = inference_state.builtins_module

    def infer(self):
        return NO_VALUES


class AbstractTreeName(AbstractNameDefinition):
    def __init__(self, parent_context, tree_name):
        self.parent_context = parent_context
        self.tree_name = tree_name

    def get_qualified_names(self, include_module_names=False):
        import_node = search_ancestor(self.tree_name, 'import_name', 'import_from')
        # For import nodes we cannot just have names, because it's very unclear
        # how they would look like. For now we just ignore them in most cases.
        # In case of level == 1, it works always, because it's like a submodule
        # lookup.
        if import_node is not None and not (import_node.level == 1
                                            and self.get_root_context().get_value().is_package()):
            # TODO improve the situation for when level is present.
            if include_module_names and not import_node.level:
                return tuple(n.value for n in import_node.get_path_for_name(self.tree_name))
            else:
                return None

        return super().get_qualified_names(include_module_names)

    def _get_qualified_names(self):
        parent_names = self.parent_context.get_qualified_names()
        if parent_names is None:
            return None
        return parent_names + (self.tree_name.value,)

    def get_defining_qualified_value(self):
        if self.is_import():
            raise NotImplementedError("Shouldn't really happen, please report")
        elif self.parent_context:
            return self.parent_context.get_value()  # Might be None
        return None

    def goto(self):
        context = self.parent_context
        name = self.tree_name
        definition = name.get_definition(import_name_always=True)
        if definition is not None:
            type_ = definition.type
            if type_ == 'expr_stmt':
                # Only take the parent, because if it's more complicated than just
                # a name it's something you can "goto" again.
                is_simple_name = name.parent.type not in ('power', 'trailer')
                if is_simple_name:
                    return [self]
            elif type_ in ('import_from', 'import_name'):
                from jedi.inference.imports import goto_import
                module_names = goto_import(context, name)
                return module_names
            else:
                return [self]
        else:
            from jedi.inference.imports import follow_error_node_imports_if_possible
            values = follow_error_node_imports_if_possible(context, name)
            if values is not None:
                return [value.name for value in values]

        par = name.parent
        node_type = par.type
        if node_type == 'argument' and par.children[1] == '=' and par.children[0] == name:
            # Named param goto.
            trailer = par.parent
            if trailer.type == 'arglist':
                trailer = trailer.parent
            if trailer.type != 'classdef':
                if trailer.type == 'decorator':
                    value_set = context.infer_node(trailer.children[1])
                else:
                    i = trailer.parent.children.index(trailer)
                    to_infer = trailer.parent.children[:i]
                    if to_infer[0] == 'await':
                        to_infer.pop(0)
                    value_set = context.infer_node(to_infer[0])
                    from jedi.inference.syntax_tree import infer_trailer
                    for trailer in to_infer[1:]:
                        value_set = infer_trailer(context, value_set, trailer)
                param_names = []
                for value in value_set:
                    for signature in value.get_signatures():
                        for param_name in signature.get_param_names():
                            if param_name.string_name == name.value:
                                param_names.append(param_name)
                return param_names
        elif node_type == 'dotted_name':  # Is a decorator.
            index = par.children.index(name)
            if index > 0:
                new_dotted = deep_ast_copy(par)
                new_dotted.children[index - 1:] = []
                values = context.infer_node(new_dotted)
                return unite(
                    value.goto(name, name_context=context)
                    for value in values
                )

        if node_type == 'trailer' and par.children[0] == '.':
            values = infer_call_of_leaf(context, name, cut_own_trailer=True)
            return values.goto(name, name_context=context)
        else:
            stmt = search_ancestor(
                name, 'expr_stmt', 'lambdef'
            ) or name
            if stmt.type == 'lambdef':
                stmt = name
            return context.goto(name, position=stmt.start_pos)

    def is_import(self):
        imp = search_ancestor(self.tree_name, 'import_from', 'import_name')
        return imp is not None

    @property
    def string_name(self):
        return self.tree_name.value

    @property
    def start_pos(self):
        return self.tree_name.start_pos


class ValueNameMixin:
    def infer(self):
        return ValueSet([self._value])

    def py__doc__(self):
        doc = self._value.py__doc__()
        if not doc and self._value.is_stub():
            from jedi.inference.gradual.conversion import convert_names
            names = convert_names([self], prefer_stub_to_compiled=False)
            if self not in names:
                return _merge_name_docs(names)
        return doc

    def _get_qualified_names(self):
        return self._value.get_qualified_names()

    def get_root_context(self):
        if self.parent_context is None:  # A module
            return self._value.as_context()
        return super().get_root_context()

    def get_defining_qualified_value(self):
        context = self.parent_context
        if context is not None and (context.is_module() or context.is_class()):
            return self.parent_context.get_value()  # Might be None
        return None

    @property
    def api_type(self):
        return self._value.api_type


class ValueName(ValueNameMixin, AbstractTreeName):
    def __init__(self, value, tree_name):
        super().__init__(value.parent_context, tree_name)
        self._value = value

    def goto(self):
        return ValueSet([self._value.name])


class TreeNameDefinition(AbstractTreeName):
    _API_TYPES = dict(
        import_name='module',
        import_from='module',
        funcdef='function',
        param='param',
        classdef='class',
    )

    def infer(self):
        # Refactor this, should probably be here.
        from jedi.inference.syntax_tree import tree_name_to_values
        return tree_name_to_values(
            self.parent_context.inference_state,
            self.parent_context,
            self.tree_name
        )

    @property
    def api_type(self):
        definition = self.tree_name.get_definition(import_name_always=True)
        if definition is None:
            return 'statement'
        return self._API_TYPES.get(definition.type, 'statement')

    def assignment_indexes(self):
        """
        Returns an array of tuple(int, node) of the indexes that are used in
        tuple assignments.

        For example if the name is ``y`` in the following code::

            x, (y, z) = 2, ''

        would result in ``[(1, xyz_node), (0, yz_node)]``.

        When searching for b in the case ``a, *b, c = [...]`` it will return::

            [(slice(1, -1), abc_node)]
        """
        indexes = []
        is_star_expr = False
        node = self.tree_name.parent
        compare = self.tree_name
        while node is not None:
            if node.type in ('testlist', 'testlist_comp', 'testlist_star_expr', 'exprlist'):
                for i, child in enumerate(node.children):
                    if child == compare:
                        index = int(i / 2)
                        if is_star_expr:
                            from_end = int((len(node.children) - i) / 2)
                            index = slice(index, -from_end)
                        indexes.insert(0, (index, node))
                        break
                else:
                    raise LookupError("Couldn't find the assignment.")
                is_star_expr = False
            elif node.type == 'star_expr':
                is_star_expr = True
            elif node.type in ('expr_stmt', 'sync_comp_for'):
                break

            compare = node
            node = node.parent
        return indexes

    @property
    def inference_state(self):
        # Used by the cache function below
        return self.parent_context.inference_state

    @inference_state_method_cache(default='')
    def py__doc__(self):
        api_type = self.api_type
        if api_type in ('function', 'class', 'property'):
            if self.parent_context.get_root_context().is_stub():
                from jedi.inference.gradual.conversion import convert_names
                names = convert_names([self], prefer_stub_to_compiled=False)
                if self not in names:
                    return _merge_name_docs(names)

            # Make sure the names are not TreeNameDefinitions anymore.
            return clean_scope_docstring(self.tree_name.get_definition())

        if api_type == 'module':
            names = self.goto()
            if self not in names:
                return _merge_name_docs(names)

        if api_type == 'statement' and self.tree_name.is_definition():
            return find_statement_documentation(self.tree_name.get_definition())
        return ''


class _ParamMixin:
    def maybe_positional_argument(self, include_star=True):
        options = [Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD]
        if include_star:
            options.append(Parameter.VAR_POSITIONAL)
        return self.get_kind() in options

    def maybe_keyword_argument(self, include_stars=True):
        options = [Parameter.KEYWORD_ONLY, Parameter.POSITIONAL_OR_KEYWORD]
        if include_stars:
            options.append(Parameter.VAR_KEYWORD)
        return self.get_kind() in options

    def _kind_string(self):
        kind = self.get_kind()
        if kind == Parameter.VAR_POSITIONAL:  # *args
            return '*'
        if kind == Parameter.VAR_KEYWORD:  # **kwargs
            return '**'
        return ''

    def get_qualified_names(self, include_module_names=False):
        return None


class ParamNameInterface(_ParamMixin):
    api_type = 'param'

    def get_kind(self):
        raise NotImplementedError

    def to_string(self):
        raise NotImplementedError

    def get_executed_param_name(self):
        """
        For dealing with type inference and working around the graph, we
        sometimes want to have the param name of the execution. This feels a
        bit strange and we might have to refactor at some point.

        For now however it exists to avoid infering params when we don't really
        need them (e.g. when we can just instead use annotations.
        """
        return None

    @property
    def star_count(self):
        kind = self.get_kind()
        if kind == Parameter.VAR_POSITIONAL:
            return 1
        if kind == Parameter.VAR_KEYWORD:
            return 2
        return 0

    def infer_default(self):
        return NO_VALUES


class BaseTreeParamName(ParamNameInterface, AbstractTreeName):
    annotation_node = None
    default_node = None

    def to_string(self):
        output = self._kind_string() + self.get_public_name()
        annotation = self.annotation_node
        default = self.default_node
        if annotation is not None:
            output += ': ' + annotation.get_code(include_prefix=False)
        if default is not None:
            output += '=' + default.get_code(include_prefix=False)
        return output

    def get_public_name(self):
        name = self.string_name
        if name.startswith('__'):
            # Params starting with __ are an equivalent to positional only
            # variables in typeshed.
            name = name[2:]
        return name

    def goto(self, **kwargs):
        return [self]


class _ActualTreeParamName(BaseTreeParamName):
    def __init__(self, function_value, tree_name):
        super().__init__(
            function_value.get_default_param_context(), tree_name)
        self.function_value = function_value

    def _get_param_node(self):
        return search_ancestor(self.tree_name, 'param')

    @property
    def annotation_node(self):
        return self._get_param_node().annotation

    def infer_annotation(self, execute_annotation=True, ignore_stars=False):
        from jedi.inference.gradual.annotation import infer_param
        values = infer_param(
            self.function_value, self._get_param_node(),
            ignore_stars=ignore_stars)
        if execute_annotation:
            values = values.execute_annotation()
        return values

    def infer_default(self):
        node = self.default_node
        if node is None:
            return NO_VALUES
        return self.parent_context.infer_node(node)

    @property
    def default_node(self):
        return self._get_param_node().default

    def get_kind(self):
        tree_param = self._get_param_node()
        if tree_param.star_count == 1:  # *args
            return Parameter.VAR_POSITIONAL
        if tree_param.star_count == 2:  # **kwargs
            return Parameter.VAR_KEYWORD

        # Params starting with __ are an equivalent to positional only
        # variables in typeshed.
        if tree_param.name.value.startswith('__'):
            return Parameter.POSITIONAL_ONLY

        parent = tree_param.parent
        param_appeared = False
        for p in parent.children:
            if param_appeared:
                if p == '/':
                    return Parameter.POSITIONAL_ONLY
            else:
                if p == '*':
                    return Parameter.KEYWORD_ONLY
                if p.type == 'param':
                    if p.star_count:
                        return Parameter.KEYWORD_ONLY
                    if p == tree_param:
                        param_appeared = True
        return Parameter.POSITIONAL_OR_KEYWORD

    def infer(self):
        values = self.infer_annotation()
        if values:
            return values

        doc_params = docstrings.infer_param(self.function_value, self._get_param_node())
        return doc_params


class AnonymousParamName(_ActualTreeParamName):
    @plugin_manager.decorate(name='goto_anonymous_param')
    def goto(self):
        return super().goto()

    @plugin_manager.decorate(name='infer_anonymous_param')
    def infer(self):
        values = super().infer()
        if values:
            return values
        from jedi.inference.dynamic_params import dynamic_param_lookup
        param = self._get_param_node()
        values = dynamic_param_lookup(self.function_value, param.position_index)
        if values:
            return values

        if param.star_count == 1:
            from jedi.inference.value.iterable import FakeTuple
            value = FakeTuple(self.function_value.inference_state, [])
        elif param.star_count == 2:
            from jedi.inference.value.iterable import FakeDict
            value = FakeDict(self.function_value.inference_state, {})
        elif param.default is None:
            return NO_VALUES
        else:
            return self.function_value.parent_context.infer_node(param.default)
        return ValueSet({value})


class ParamName(_ActualTreeParamName):
    def __init__(self, function_value, tree_name, arguments):
        super().__init__(function_value, tree_name)
        self.arguments = arguments

    def infer(self):
        values = super().infer()
        if values:
            return values

        return self.get_executed_param_name().infer()

    def get_executed_param_name(self):
        from jedi.inference.param import get_executed_param_names
        params_names = get_executed_param_names(self.function_value, self.arguments)
        return params_names[self._get_param_node().position_index]


class ParamNameWrapper(_ParamMixin):
    def __init__(self, param_name):
        self._wrapped_param_name = param_name

    def __getattr__(self, name):
        return getattr(self._wrapped_param_name, name)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self._wrapped_param_name)


class ImportName(AbstractNameDefinition):
    start_pos = (1, 0)
    _level = 0

    def __init__(self, parent_context, string_name):
        self._from_module_context = parent_context
        self.string_name = string_name

    def get_qualified_names(self, include_module_names=False):
        if include_module_names:
            if self._level:
                assert self._level == 1, "Everything else is not supported for now"
                module_names = self._from_module_context.string_names
                if module_names is None:
                    return module_names
                return module_names + (self.string_name,)
            return (self.string_name,)
        return ()

    @property
    def parent_context(self):
        m = self._from_module_context
        import_values = self.infer()
        if not import_values:
            return m
        # It's almost always possible to find the import or to not find it. The
        # importing returns only one value, pretty much always.
        return next(iter(import_values)).as_context()

    @memoize_method
    def infer(self):
        from jedi.inference.imports import Importer
        m = self._from_module_context
        return Importer(m.inference_state, [self.string_name], m, level=self._level).follow()

    def goto(self):
        return [m.name for m in self.infer()]

    @property
    def api_type(self):
        return 'module'

    def py__doc__(self):
        return _merge_name_docs(self.goto())


class SubModuleName(ImportName):
    _level = 1


class NameWrapper:
    def __init__(self, wrapped_name):
        self._wrapped_name = wrapped_name

    def __getattr__(self, name):
        return getattr(self._wrapped_name, name)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._wrapped_name)


class StubNameMixin:
    def py__doc__(self):
        from jedi.inference.gradual.conversion import convert_names
        # Stubs are not complicated and we can just follow simple statements
        # that have an equals in them, because they typically make something
        # else public. See e.g. stubs for `requests`.
        names = [self]
        if self.api_type == 'statement' and '=' in self.tree_name.get_definition().children:
            names = [v.name for v in self.infer()]

        names = convert_names(names, prefer_stub_to_compiled=False)
        if self in names:
            return super().py__doc__()
        else:
            # We have signatures ourselves in stubs, so don't use signatures
            # from the implementation.
            return _merge_name_docs(names)


# From here on down we make looking up the sys.version_info fast.
class StubName(StubNameMixin, TreeNameDefinition):
    def infer(self):
        inferred = super().infer()
        if self.string_name == 'version_info' and self.get_root_context().py__name__() == 'sys':
            from jedi.inference.gradual.stub_value import VersionInfo
            return ValueSet(VersionInfo(c) for c in inferred)
        return inferred


class ModuleName(ValueNameMixin, AbstractNameDefinition):
    start_pos = 1, 0

    def __init__(self, value, name):
        self._value = value
        self._name = name

    @property
    def string_name(self):
        return self._name


class StubModuleName(StubNameMixin, ModuleName):
    pass

# === NexusCore/openenv\Lib\site-packages\win32com\server\register.py ===
"""Utilities for registering objects.

This module contains utility functions to register Python objects as
valid COM Servers.  The RegisterServer function provides all information
necessary to allow the COM framework to respond to a request for a COM object,
construct the necessary Python object, and dispatch COM events.

"""

import os
import sys

import pythoncom
import win32api
import win32con
import winerror

CATID_PythonCOMServer = "{B3EF80D0-68E2-11D0-A689-00C04FD658FF}"


def _set_subkeys(keyName, valueDict, base=win32con.HKEY_CLASSES_ROOT):
    hkey = win32api.RegCreateKey(base, keyName)
    try:
        for key, value in valueDict.items():
            win32api.RegSetValueEx(hkey, key, None, win32con.REG_SZ, value)
    finally:
        win32api.RegCloseKey(hkey)


def _set_string(path, value, base=win32con.HKEY_CLASSES_ROOT):
    "Set a string value in the registry."

    win32api.RegSetValue(base, path, win32con.REG_SZ, value)


def _get_string(path, base=win32con.HKEY_CLASSES_ROOT):
    "Get a string value from the registry."

    try:
        return win32api.RegQueryValue(base, path)
    except win32api.error:
        return None


def _remove_key(path, base=win32con.HKEY_CLASSES_ROOT):
    "Remove a string from the registry."

    try:
        win32api.RegDeleteKey(base, path)
    except win32api.error as xxx_todo_changeme1:
        (code, fn, msg) = xxx_todo_changeme1.args
        if code != winerror.ERROR_FILE_NOT_FOUND:
            raise win32api.error(code, fn, msg)


def recurse_delete_key(path, base=win32con.HKEY_CLASSES_ROOT):
    """Recursively delete registry keys.

    This is needed since you can't blast a key when subkeys exist.
    """
    try:
        h = win32api.RegOpenKey(base, path)
    except win32api.error as xxx_todo_changeme2:
        (code, fn, msg) = xxx_todo_changeme2.args
        if code != winerror.ERROR_FILE_NOT_FOUND:
            raise win32api.error(code, fn, msg)
    else:
        # parent key found and opened successfully. do some work, making sure
        # to always close the thing (error or no).
        try:
            # remove all of the subkeys
            while 1:
                try:
                    subkeyname = win32api.RegEnumKey(h, 0)
                except win32api.error as xxx_todo_changeme:
                    (code, fn, msg) = xxx_todo_changeme.args
                    if code != winerror.ERROR_NO_MORE_ITEMS:
                        raise win32api.error(code, fn, msg)
                    break
                recurse_delete_key(path + "\\" + subkeyname, base)

            # remove the parent key
            _remove_key(path, base)
        finally:
            win32api.RegCloseKey(h)


def _cat_registrar():
    return pythoncom.CoCreateInstance(
        pythoncom.CLSID_StdComponentCategoriesMgr,
        None,
        pythoncom.CLSCTX_INPROC_SERVER,
        pythoncom.IID_ICatRegister,
    )


def _find_localserver_exe(mustfind):
    if sys.platform != "win32":
        return sys.executable
    if os.path.splitext(os.path.basename(pythoncom.__file__))[0].endswith("_d"):
        exeBaseName = "pythonw_d.exe"
    else:
        exeBaseName = "pythonw.exe"
    # First see if in the same directory as this .EXE
    exeName = os.path.join(os.path.split(sys.executable)[0], exeBaseName)
    if not os.path.exists(exeName):
        # See if in our sys.prefix directory
        exeName = os.path.join(sys.prefix, exeBaseName)
    if not os.path.exists(exeName):
        # See if in our sys.prefix/pcbuild directory (for developers)
        if "64 bit" in sys.version:
            exeName = os.path.join(sys.prefix, "PCbuild", "amd64", exeBaseName)
        else:
            exeName = os.path.join(sys.prefix, "PCbuild", exeBaseName)
    if not os.path.exists(exeName):
        # See if the registry has some info.
        try:
            key = "SOFTWARE\\Python\\PythonCore\\%s\\InstallPath" % sys.winver
            path = win32api.RegQueryValue(win32con.HKEY_LOCAL_MACHINE, key)
            exeName = os.path.join(path, exeBaseName)
        except (AttributeError, win32api.error):
            pass
    if not os.path.exists(exeName):
        if mustfind:
            raise RuntimeError("Can not locate the program '%s'" % exeBaseName)
        return None
    return exeName


def _find_localserver_module():
    import win32com.server

    path = next(iter(win32com.server.__path__))
    baseName = "localserver"
    pyfile = os.path.join(path, baseName + ".py")
    try:
        os.stat(pyfile)
    except OSError:
        # See if we have a compiled extension
        if __debug__:
            ext = ".pyc"
        else:
            ext = ".pyo"
        pyfile = os.path.join(path, baseName + ext)
        try:
            os.stat(pyfile)
        except OSError:
            raise RuntimeError(
                "Can not locate the Python module 'win32com.server.%s'" % baseName
            )
    return pyfile


def RegisterServer(
    clsid,
    pythonInstString=None,
    desc=None,
    progID=None,
    verProgID=None,
    defIcon=None,
    threadingModel="both",
    policy=None,
    catids=[],
    other={},
    addPyComCat=None,
    dispatcher=None,
    clsctx=None,
    addnPath=None,
):
    """Registers a Python object as a COM Server.  This enters almost all necessary
    information in the system registry, allowing COM to use the object.

    clsid -- The (unique) CLSID of the server.
    pythonInstString -- A string holding the instance name that will be created
                  whenever COM requests a new object.
    desc -- The description of the COM object.
    progID -- The user name of this object (eg, Word.Document)
    verProgId -- The user name of this version's implementation (eg Word.6.Document)
    defIcon -- The default icon for the object.
    threadingModel -- The threading model this object supports.
    policy -- The policy to use when creating this object.
    catids -- A list of category ID's this object belongs in.
    other -- A dictionary of extra items to be registered.
    addPyComCat -- A flag indicating if the object should be added to the list
             of Python servers installed on the machine.  If None (the default)
             then it will be registered when running from python source, but
             not registered if running in a frozen environment.
    dispatcher -- The dispatcher to use when creating this object.
    clsctx -- One of the CLSCTX_* constants.
    addnPath -- An additional path the COM framework will add to sys.path
                before attempting to create the object.
    """

    ### backwards-compat check
    ### Certain policies do not require a "class name", just the policy itself.
    if not pythonInstString and not policy:
        raise TypeError(
            "You must specify either the Python Class or Python Policy which implement the COM object."
        )

    keyNameRoot = "CLSID\\%s" % str(clsid)
    _set_string(keyNameRoot, desc)

    # Also register as an "Application" so DCOM etc all see us.
    _set_string("AppID\\%s" % clsid, progID)
    # Depending on contexts requested, register the specified server type.
    # Set default clsctx.
    if not clsctx:
        clsctx = pythoncom.CLSCTX_INPROC_SERVER | pythoncom.CLSCTX_LOCAL_SERVER
    # And if we are frozen, ignore the ones that don't make sense in this
    # context.
    if pythoncom.frozen:
        assert (
            sys.frozen
        ), "pythoncom is frozen, but sys.frozen is not set - don't know the context!"
        if sys.frozen == "dll":
            clsctx &= pythoncom.CLSCTX_INPROC_SERVER
        else:
            clsctx &= pythoncom.CLSCTX_LOCAL_SERVER
    # Now setup based on the clsctx left over.
    if clsctx & pythoncom.CLSCTX_INPROC_SERVER:
        # get the module to use for registration.
        # nod to Gordon's installer - if sys.frozen and sys.frozendllhandle
        # exist, then we are being registered via a DLL - use this DLL as the
        # file name.
        if pythoncom.frozen:
            if hasattr(sys, "frozendllhandle"):
                dllName = win32api.GetModuleFileName(sys.frozendllhandle)
            else:
                raise RuntimeError(
                    "We appear to have a frozen DLL, but I don't know the DLL to use"
                )
        else:
            # Normal case - running from .py file, so register pythoncom's DLL.
            # Although now we prefer a 'loader' DLL if it exists to avoid some
            # manifest issues (the 'loader' DLL has a manifest, but pythoncom does not)
            pythoncom_dir = os.path.dirname(pythoncom.__file__)
            suffix = (
                "_d"
                if os.path.splitext(os.path.basename(pythoncom.__file__))[0].endswith(
                    "_d"
                )
                else ""
            )
            # Always register with the full path to the DLLs.
            loadername = os.path.join(
                pythoncom_dir,
                "pythoncomloader%d%d%s.dll"
                % (sys.version_info.major, sys.version_info.minor, suffix),
            )
            dllName = loadername if os.path.isfile(loadername) else pythoncom.__file__

        _set_subkeys(
            keyNameRoot + "\\InprocServer32",
            {
                None: dllName,
                "ThreadingModel": threadingModel,
            },
        )
    else:  # Remove any old InProcServer32 registrations
        _remove_key(keyNameRoot + "\\InprocServer32")

    if clsctx & pythoncom.CLSCTX_LOCAL_SERVER:
        if pythoncom.frozen:
            # If we are frozen, we write "{exe} /Automate", just
            # like "normal" .EXEs do
            exeName = win32api.GetShortPathName(sys.executable)
            command = f"{exeName} /Automate"
        else:
            # Running from .py sources - we need to write
            # 'python.exe win32com\server\localserver.py {clsid}"
            exeName = _find_localserver_exe(1)
            exeName = win32api.GetShortPathName(exeName)
            pyfile = _find_localserver_module()
            command = f'{exeName} "{pyfile}" {clsid}'
        _set_string(keyNameRoot + "\\LocalServer32", command)
    else:  # Remove any old LocalServer32 registrations
        _remove_key(keyNameRoot + "\\LocalServer32")

    if pythonInstString:
        _set_string(keyNameRoot + "\\PythonCOM", pythonInstString)
    else:
        _remove_key(keyNameRoot + "\\PythonCOM")
    if policy:
        _set_string(keyNameRoot + "\\PythonCOMPolicy", policy)
    else:
        _remove_key(keyNameRoot + "\\PythonCOMPolicy")

    if dispatcher:
        _set_string(keyNameRoot + "\\PythonCOMDispatcher", dispatcher)
    else:
        _remove_key(keyNameRoot + "\\PythonCOMDispatcher")

    if defIcon:
        _set_string(keyNameRoot + "\\DefaultIcon", defIcon)
    else:
        _remove_key(keyNameRoot + "\\DefaultIcon")

    if addnPath:
        _set_string(keyNameRoot + "\\PythonCOMPath", addnPath)
    else:
        _remove_key(keyNameRoot + "\\PythonCOMPath")

    if addPyComCat is None:
        addPyComCat = pythoncom.frozen == 0
    if addPyComCat:
        catids = catids + [CATID_PythonCOMServer]

    # Set up the implemented categories
    if catids:
        regCat = _cat_registrar()
        regCat.RegisterClassImplCategories(clsid, catids)

    # set up any other reg values they might have
    if other:
        for key, value in other.items():
            _set_string(keyNameRoot + "\\" + key, value)

    if progID:
        # set the progID as the most specific that was given to us
        if verProgID:
            _set_string(keyNameRoot + "\\ProgID", verProgID)
        else:
            _set_string(keyNameRoot + "\\ProgID", progID)

        # Set up the root entries - version independent.
        if desc:
            _set_string(progID, desc)
        _set_string(progID + "\\CLSID", str(clsid))

        # Set up the root entries - version dependent.
        if verProgID:
            # point from independent to the current version
            _set_string(progID + "\\CurVer", verProgID)

            # point to the version-independent one
            _set_string(keyNameRoot + "\\VersionIndependentProgID", progID)

            # set up the versioned progID
            if desc:
                _set_string(verProgID, desc)
            _set_string(verProgID + "\\CLSID", str(clsid))


def GetUnregisterServerKeys(clsid, progID=None, verProgID=None, customKeys=None):
    """Given a server, return a list of of ("key", root), which are keys recursively
    and uncondtionally deleted at unregister or uninstall time.
    """
    # remove the main CLSID registration
    ret = [("CLSID\\%s" % str(clsid), win32con.HKEY_CLASSES_ROOT)]
    # remove the versioned ProgID registration
    if verProgID:
        ret.append((verProgID, win32con.HKEY_CLASSES_ROOT))
    # blow away the independent ProgID. we can't leave it since we just
    # torched the class.
    ### could potentially check the CLSID... ?
    if progID:
        ret.append((progID, win32con.HKEY_CLASSES_ROOT))
    # The DCOM config tool may write settings to the AppID key for our CLSID
    ret.append(("AppID\\%s" % str(clsid), win32con.HKEY_CLASSES_ROOT))
    # Any custom keys?
    if customKeys:
        ret.extend(customKeys)

    return ret


def UnregisterServer(clsid, progID=None, verProgID=None, customKeys=None):
    """Unregisters a Python COM server."""

    for args in GetUnregisterServerKeys(clsid, progID, verProgID, customKeys):
        recurse_delete_key(*args)

    ### it might be nice at some point to "roll back" the independent ProgID
    ### to an earlier version if one exists, and just blowing away the
    ### specified version of the ProgID (and its corresponding CLSID)
    ### another time, though...

    ### NOTE: ATL simply blows away the above three keys without the
    ### potential checks that I describe.  Assuming that defines the
    ### "standard" then we have no additional changes necessary.


def GetRegisteredServerOption(clsid, optionName):
    """Given a CLSID for a server and option name, return the option value"""
    keyNameRoot = f"CLSID\\{clsid}\\{optionName}"
    return _get_string(keyNameRoot)


def _get(ob, attr, default=None):
    try:
        return getattr(ob, attr)
    except AttributeError:
        pass
    # look down sub-classes
    try:
        bases = ob.__bases__
    except AttributeError:
        # ob is not a class - no probs.
        return default
    for base in bases:
        val = _get(base, attr, None)
        if val is not None:
            return val
    return default


def RegisterClasses(*classes, **flags):
    quiet = "quiet" in flags and flags["quiet"]
    debugging = "debug" in flags and flags["debug"]
    for cls in classes:
        clsid = cls._reg_clsid_
        progID = _get(cls, "_reg_progid_")
        desc = _get(cls, "_reg_desc_", progID)
        spec = _get(cls, "_reg_class_spec_")
        verProgID = _get(cls, "_reg_verprogid_")
        defIcon = _get(cls, "_reg_icon_")
        threadingModel = _get(cls, "_reg_threading_", "both")
        catids = _get(cls, "_reg_catids_", [])
        options = _get(cls, "_reg_options_", {})
        policySpec = _get(cls, "_reg_policy_spec_")
        clsctx = _get(cls, "_reg_clsctx_")
        tlb_filename = _get(cls, "_reg_typelib_filename_")
        # default to being a COM category only when not frozen.
        addPyComCat = not _get(cls, "_reg_disable_pycomcat_", pythoncom.frozen != 0)
        addnPath = None
        if debugging:
            # If the class has a debugging dispatcher specified, use it, otherwise
            # use our default dispatcher.
            dispatcherSpec = _get(cls, "_reg_debug_dispatcher_spec_")
            if dispatcherSpec is None:
                dispatcherSpec = "win32com.server.dispatcher.DefaultDebugDispatcher"
            # And remember the debugging flag as servers may wish to use it at runtime.
            debuggingDesc = "(for debugging)"
            options["Debugging"] = "1"
        else:
            dispatcherSpec = _get(cls, "_reg_dispatcher_spec_")
            debuggingDesc = ""
            options["Debugging"] = "0"

        if spec is None:
            moduleName = cls.__module__
            if moduleName == "__main__":
                # Use argv[0] to determine the module name.
                try:
                    # Use the win32api to find the case-sensitive name
                    moduleName = os.path.splitext(
                        win32api.FindFiles(sys.argv[0])[0][8]
                    )[0]
                except (IndexError, win32api.error):
                    # Can't find the script file - the user must explicitly set the _reg_... attribute.
                    raise TypeError(
                        "Can't locate the script hosting the COM object - please set _reg_class_spec_ in your object"
                    )

            spec = moduleName + "." + cls.__name__
            # Frozen apps don't need their directory on sys.path
            if not pythoncom.frozen:
                scriptDir = os.path.split(sys.argv[0])[0]
                if not scriptDir:
                    scriptDir = "."
                addnPath = win32api.GetFullPathName(scriptDir)

        RegisterServer(
            clsid,
            spec,
            desc,
            progID,
            verProgID,
            defIcon,
            threadingModel,
            policySpec,
            catids,
            options,
            addPyComCat,
            dispatcherSpec,
            clsctx,
            addnPath,
        )
        if not quiet:
            print("Registered:", progID or spec, debuggingDesc)
        # Register the typelibrary
        if tlb_filename:
            tlb_filename = os.path.abspath(tlb_filename)
            typelib = pythoncom.LoadTypeLib(tlb_filename)
            pythoncom.RegisterTypeLib(typelib, tlb_filename)
            if not quiet:
                print("Registered type library:", tlb_filename)
    extra = flags.get("finalize_register")
    if extra:
        extra()


def UnregisterClasses(*classes, **flags):
    quiet = "quiet" in flags and flags["quiet"]
    for cls in classes:
        clsid = cls._reg_clsid_
        progID = _get(cls, "_reg_progid_")
        verProgID = _get(cls, "_reg_verprogid_")
        customKeys = _get(cls, "_reg_remove_keys_")
        unregister_typelib = _get(cls, "_reg_typelib_filename_") is not None

        UnregisterServer(clsid, progID, verProgID, customKeys)
        if not quiet:
            print("Unregistered:", progID or str(clsid))
        if unregister_typelib:
            tlb_guid = _get(cls, "_typelib_guid_")
            if tlb_guid is None:
                # I guess I could load the typelib, but they need the GUID anyway.
                print("Have typelib filename, but no GUID - can't unregister")
            else:
                major, minor = _get(cls, "_typelib_version_", (1, 0))
                lcid = _get(cls, "_typelib_lcid_", 0)
                try:
                    pythoncom.UnRegisterTypeLib(tlb_guid, major, minor, lcid)
                    if not quiet:
                        print("Unregistered type library")
                except pythoncom.com_error:
                    pass

    extra = flags.get("finalize_unregister")
    if extra:
        extra()


# Unregister info is for installers or external uninstallers.
# The WISE installer, for example firstly registers the COM server,
# then queries for the Unregister info, appending it to its
# install log.  Uninstalling the package will uninstall the server.
def UnregisterInfoClasses(*classes, **flags):
    ret = []
    for cls in classes:
        clsid = cls._reg_clsid_
        progID = _get(cls, "_reg_progid_")
        verProgID = _get(cls, "_reg_verprogid_")
        customKeys = _get(cls, "_reg_remove_keys_")

        ret.extend(GetUnregisterServerKeys(clsid, progID, verProgID, customKeys))
    return ret


# Attempt to 're-execute' our current process with elevation.
def ReExecuteElevated(flags):
    import tempfile

    import win32console
    import win32event  # we've already checked we are running XP above
    import win32process
    from win32com.shell import shellcon
    from win32com.shell.shell import ShellExecuteEx

    if not flags["quiet"]:
        print("Requesting elevation and retrying...")
    new_params = " ".join(['"' + a + '"' for a in sys.argv])
    # If we aren't already in unattended mode, we want our sub-process to
    # be.
    if not flags["unattended"]:
        new_params += " --unattended"
    # specifying the parent means the dialog is centered over our window,
    # which is a good usability clue.
    # hwnd is unlikely on the command-line, but flags may come from elsewhere
    try:
        hwnd = flags.get("hwnd", win32console.GetConsoleWindow())
    except win32console.error:
        hwnd = 0
    # Redirect output so we give the user some clue what went wrong.  This
    # also means we need to use COMSPEC.  However, the "current directory"
    # appears to end up ignored - so we execute things via a temp batch file.
    tempbase = tempfile.mktemp("pycomserverreg")
    outfile = tempbase + ".out"
    batfile = tempbase + ".bat"

    # If registering from pythonwin, need to run python console instead since
    #  pythonwin will just open script for editting
    current_exe = os.path.split(sys.executable)[1].lower()
    exe_to_run = None
    if current_exe == "pythonwin.exe":
        exe_to_run = os.path.join(sys.prefix, "python.exe")
    elif current_exe == "pythonwin_d.exe":
        exe_to_run = os.path.join(sys.prefix, "python_d.exe")
    if not exe_to_run or not os.path.exists(exe_to_run):
        exe_to_run = sys.executable

    try:
        batf = open(batfile, "w")
        try:
            cwd = os.getcwd()
            print("@echo off", file=batf)
            # nothing is 'inherited' by the elevated process, including the
            # environment.  I wonder if we need to set more?
            print("set PYTHONPATH=%s" % os.environ.get("PYTHONPATH", ""), file=batf)
            # may be on a different drive - select that before attempting to CD.
            print(os.path.splitdrive(cwd)[0], file=batf)
            print('cd "%s"' % os.getcwd(), file=batf)
            print(
                '{} {} > "{}" 2>&1'.format(
                    win32api.GetShortPathName(exe_to_run), new_params, outfile
                ),
                file=batf,
            )
        finally:
            batf.close()
        executable = os.environ.get("COMSPEC", "cmd.exe")
        rc = ShellExecuteEx(
            hwnd=hwnd,
            fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
            lpVerb="runas",
            lpFile=executable,
            lpParameters='/C "%s"' % batfile,
            nShow=win32con.SW_SHOW,
        )
        hproc = rc["hProcess"]
        win32event.WaitForSingleObject(hproc, win32event.INFINITE)
        exit_code = win32process.GetExitCodeProcess(hproc)
        outf = open(outfile)
        try:
            output = outf.read()
        finally:
            outf.close()

        if exit_code:
            # Even if quiet you get to see this message.
            print("Error: registration failed (exit code %s)." % exit_code)
        # if we are quiet then the output if likely to already be nearly
        # empty, so always print it.
        print(output, end=" ")
    finally:
        for f in (outfile, batfile):
            try:
                os.unlink(f)
            except OSError as exc:
                print(f"Failed to remove tempfile '{f}': {exc}")


def UseCommandLine(*classes, **flags):
    unregisterInfo = "--unregister_info" in sys.argv
    unregister = "--unregister" in sys.argv
    flags["quiet"] = flags.get("quiet", 0) or "--quiet" in sys.argv
    flags["debug"] = flags.get("debug", 0) or "--debug" in sys.argv
    flags["unattended"] = flags.get("unattended", 0) or "--unattended" in sys.argv
    if unregisterInfo:
        return UnregisterInfoClasses(*classes, **flags)
    try:
        if unregister:
            UnregisterClasses(*classes, **flags)
        else:
            RegisterClasses(*classes, **flags)
    except win32api.error as exc:
        # If we are on xp+ and have "access denied", retry using
        # ShellExecuteEx with 'runas' verb to force elevation (vista) and/or
        # admin login dialog (vista/xp)
        if (
            flags["unattended"]
            or exc.winerror != winerror.ERROR_ACCESS_DENIED
            or sys.getwindowsversion()[0] < 5
        ):
            raise
        ReExecuteElevated(flags)


def RegisterPyComCategory():
    """Register the Python COM Server component category."""
    regCat = _cat_registrar()
    regCat.RegisterCategories([(CATID_PythonCOMServer, 0x0409, "Python COM Server")])


if not pythoncom.frozen:
    try:
        win32api.RegQueryValue(
            win32con.HKEY_CLASSES_ROOT,
            "Component Categories\\%s" % CATID_PythonCOMServer,
        )
    except win32api.error:
        try:
            RegisterPyComCategory()
        except pythoncom.error:  # Error with the COM category manager - oh well.
            pass

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\docking\DockingBar.py ===
# DockingBar.py

# Ported directly (comments and all) from the samples at www.codeguru.com

# WARNING: Use at your own risk, as this interface is highly likely to change.
# Currently we support only one child per DockingBar.  Later we need to add
# support for multiple children.

import struct

import win32api
import win32con
import win32ui
from pywin.mfc import afxres, window

clrBtnHilight = win32api.GetSysColor(win32con.COLOR_BTNHILIGHT)
clrBtnShadow = win32api.GetSysColor(win32con.COLOR_BTNSHADOW)


def CenterPoint(rect):
    width = rect[2] - rect[0]
    height = rect[3] - rect[1]
    return rect[0] + width // 2, rect[1] + height // 2


def OffsetRect(rect, point):
    (x, y) = point
    return rect[0] + x, rect[1] + y, rect[2] + x, rect[3] + y


def DeflateRect(rect, point):
    (x, y) = point
    return rect[0] + x, rect[1] + y, rect[2] - x, rect[3] - y


def PtInRect(rect, pt):
    return rect[0] <= pt[0] < rect[2] and rect[1] <= pt[1] < rect[3]


class DockingBar(window.Wnd):
    def __init__(self, obj=None):
        if obj is None:
            obj = win32ui.CreateControlBar()
        window.Wnd.__init__(self, obj)
        self.dialog = None
        self.nDockBarID = 0
        self.sizeMin = 32, 32
        self.sizeHorz = 200, 200
        self.sizeVert = 200, 200
        self.sizeFloat = 200, 200
        self.bTracking = 0
        self.bInRecalcNC = 0
        self.cxEdge = 6
        self.cxBorder = 3
        self.cxGripper = 20
        self.brushBkgd = win32ui.CreateBrush()
        self.brushBkgd.CreateSolidBrush(win32api.GetSysColor(win32con.COLOR_BTNFACE))

        # Support for diagonal resizing
        self.cyBorder = 3
        self.cCaptionSize = win32api.GetSystemMetrics(win32con.SM_CYSMCAPTION)
        self.cMinWidth = win32api.GetSystemMetrics(win32con.SM_CXMIN)
        self.cMinHeight = win32api.GetSystemMetrics(win32con.SM_CYMIN)
        self.rectUndock = (0, 0, 0, 0)

    def OnUpdateCmdUI(self, target, bDisableIfNoHndler):
        return self.UpdateDialogControls(target, bDisableIfNoHndler)

    def CreateWindow(
        self,
        parent,
        childCreator,
        title,
        id,
        style=win32con.WS_CHILD | win32con.WS_VISIBLE | afxres.CBRS_LEFT,
        childCreatorArgs=(),
    ):
        assert not (
            (style & afxres.CBRS_SIZE_FIXED) and (style & afxres.CBRS_SIZE_DYNAMIC)
        ), "Invalid style"
        self.rectClose = self.rectBorder = self.rectGripper = self.rectTracker = (
            0,
            0,
            0,
            0,
        )

        # save the style
        self._obj_.dwStyle = style & afxres.CBRS_ALL

        cursor = win32api.LoadCursor(0, win32con.IDC_ARROW)
        wndClass = win32ui.RegisterWndClass(
            win32con.CS_DBLCLKS, cursor, self.brushBkgd.GetSafeHandle(), 0
        )

        self._obj_.CreateWindow(wndClass, title, style, (0, 0, 0, 0), parent, id)

        # Create the child dialog
        self.dialog = childCreator(*(self,) + childCreatorArgs)

        # use the dialog dimensions as default base dimensions
        assert self.dialog.IsWindow(), (
            "The childCreator function %s did not create a window!" % childCreator
        )
        rect = self.dialog.GetWindowRect()
        self.sizeHorz = self.sizeVert = self.sizeFloat = (
            rect[2] - rect[0],
            rect[3] - rect[1],
        )

        self.sizeHorz = self.sizeHorz[0], self.sizeHorz[1] + self.cxEdge + self.cxBorder
        self.sizeVert = self.sizeVert[0] + self.cxEdge + self.cxBorder, self.sizeVert[1]
        self.HookMessages()

    def CalcFixedLayout(self, bStretch, bHorz):
        rectTop = self.dockSite.GetControlBar(
            afxres.AFX_IDW_DOCKBAR_TOP
        ).GetWindowRect()
        rectLeft = self.dockSite.GetControlBar(
            afxres.AFX_IDW_DOCKBAR_LEFT
        ).GetWindowRect()
        if bStretch:
            nHorzDockBarWidth = 32767
            nVertDockBarHeight = 32767
        else:
            nHorzDockBarWidth = rectTop[2] - rectTop[0] + 4
            nVertDockBarHeight = rectLeft[3] - rectLeft[1] + 4

        if self.IsFloating():
            return self.sizeFloat
        if bHorz:
            return nHorzDockBarWidth, self.sizeHorz[1]
        return self.sizeVert[0], nVertDockBarHeight

    def CalcDynamicLayout(self, length, mode):
        # Support for diagonal sizing.
        if self.IsFloating():
            self.GetParent().GetParent().ModifyStyle(win32ui.MFS_4THICKFRAME, 0)
        if mode & (win32ui.LM_HORZDOCK | win32ui.LM_VERTDOCK):
            flags = (
                win32con.SWP_NOSIZE
                | win32con.SWP_NOMOVE
                | win32con.SWP_NOZORDER
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_FRAMECHANGED
            )
            self.SetWindowPos(
                0,
                (
                    0,
                    0,
                    0,
                    0,
                ),
                flags,
            )
            self.dockSite.RecalcLayout()
            return self._obj_.CalcDynamicLayout(length, mode)

        if mode & win32ui.LM_MRUWIDTH:
            return self.sizeFloat
        if mode & win32ui.LM_COMMIT:
            self.sizeFloat = length, self.sizeFloat[1]
            return self.sizeFloat
        # More diagonal sizing.
        if self.IsFloating():
            dc = self.dockContext
            pt = win32api.GetCursorPos()
            windowRect = self.GetParent().GetParent().GetWindowRect()

            hittest = dc.nHitTest
            if hittest == win32con.HTTOPLEFT:
                cx = max(windowRect[2] - pt[0], self.cMinWidth) - self.cxBorder
                cy = max(windowRect[3] - self.cCaptionSize - pt[1], self.cMinHeight) - 1
                self.sizeFloat = cx, cy

                top = (
                    min(pt[1], windowRect[3] - self.cCaptionSize - self.cMinHeight)
                    - self.cyBorder
                )
                left = min(pt[0], windowRect[2] - self.cMinWidth) - 1
                dc.rectFrameDragHorz = (
                    left,
                    top,
                    dc.rectFrameDragHorz[2],
                    dc.rectFrameDragHorz[3],
                )
                return self.sizeFloat
            if hittest == win32con.HTTOPRIGHT:
                cx = max(pt[0] - windowRect[0], self.cMinWidth)
                cy = max(windowRect[3] - self.cCaptionSize - pt[1], self.cMinHeight) - 1
                self.sizeFloat = cx, cy

                top = (
                    min(pt[1], windowRect[3] - self.cCaptionSize - self.cMinHeight)
                    - self.cyBorder
                )
                dc.rectFrameDragHorz = (
                    dc.rectFrameDragHorz[0],
                    top,
                    dc.rectFrameDragHorz[2],
                    dc.rectFrameDragHorz[3],
                )
                return self.sizeFloat

            if hittest == win32con.HTBOTTOMLEFT:
                cx = max(windowRect[2] - pt[0], self.cMinWidth) - self.cxBorder
                cy = max(pt[1] - windowRect[1] - self.cCaptionSize, self.cMinHeight)
                self.sizeFloat = cx, cy

                left = min(pt[0], windowRect[2] - self.cMinWidth) - 1
                dc.rectFrameDragHorz = (
                    left,
                    dc.rectFrameDragHorz[1],
                    dc.rectFrameDragHorz[2],
                    dc.rectFrameDragHorz[3],
                )
                return self.sizeFloat

            if hittest == win32con.HTBOTTOMRIGHT:
                cx = max(pt[0] - windowRect[0], self.cMinWidth)
                cy = max(pt[1] - windowRect[1] - self.cCaptionSize, self.cMinHeight)
                self.sizeFloat = cx, cy
                return self.sizeFloat

        if mode & win32ui.LM_LENGTHY:
            self.sizeFloat = self.sizeFloat[0], max(self.sizeMin[1], length)
            return self.sizeFloat
        else:
            return max(self.sizeMin[0], length), self.sizeFloat[1]

    def OnWindowPosChanged(self, msg):
        if self.GetSafeHwnd() == 0 or self.dialog is None:
            return 0
        lparam = msg[3]
        """ LPARAM used with WM_WINDOWPOSCHANGED:
            typedef struct {
                HWND hwnd;
                HWND hwndInsertAfter;
                int x;
                int y;
                int cx;
                int cy;
                UINT flags;} WINDOWPOS;
        """
        format = "PPiiiii"
        bytes = win32ui.GetBytes(lparam, struct.calcsize(format))
        hwnd, hwndAfter, x, y, cx, cy, flags = struct.unpack(format, bytes)

        if self.bInRecalcNC:
            rc = self.GetClientRect()
            self.dialog.MoveWindow(rc)
            return 0
        # Find on which side are we docked
        nDockBarID = self.GetParent().GetDlgCtrlID()
        # Return if dropped at same location
        # no docking side change and no size change
        if (
            (nDockBarID == self.nDockBarID)
            and (flags & win32con.SWP_NOSIZE)
            and (
                (self._obj_.dwStyle & afxres.CBRS_BORDER_ANY) != afxres.CBRS_BORDER_ANY
            )
        ):
            return
        self.nDockBarID = nDockBarID

        # Force recalc the non-client area
        self.bInRecalcNC = 1
        try:
            swpflags = (
                win32con.SWP_NOSIZE
                | win32con.SWP_NOMOVE
                | win32con.SWP_NOZORDER
                | win32con.SWP_FRAMECHANGED
            )
            self.SetWindowPos(0, (0, 0, 0, 0), swpflags)
        finally:
            self.bInRecalcNC = 0
        return 0

    # This is a virtual and not a message hook.
    def OnSetCursor(self, window, nHitTest, wMouseMsg):
        if nHitTest != win32con.HTSIZE or self.bTracking:
            return self._obj_.OnSetCursor(window, nHitTest, wMouseMsg)

        if self.IsHorz():
            win32api.SetCursor(win32api.LoadCursor(0, win32con.IDC_SIZENS))
        else:
            win32api.SetCursor(win32api.LoadCursor(0, win32con.IDC_SIZEWE))
        return 1

    # Mouse Handling
    def OnLButtonUp(self, msg):
        if not self.bTracking:
            return 1  # pass it on.
        self.StopTracking(1)
        return 0  # Don't pass on

    def OnLButtonDown(self, msg):
        # UINT nFlags, CPoint point)
        # only start dragging if clicked in "void" space
        if self.dockBar is not None:
            # start the drag
            pt = msg[5]
            pt = self.ClientToScreen(pt)
            self.dockContext.StartDrag(pt)
            return 0
        return 1

    def OnNcLButtonDown(self, msg):
        if self.bTracking:
            return 0
        nHitTest = wparam = msg[2]
        pt = msg[5]

        if nHitTest == win32con.HTSYSMENU and not self.IsFloating():
            self.GetDockingFrame().ShowControlBar(self, 0, 0)
        elif nHitTest == win32con.HTMINBUTTON and not self.IsFloating():
            self.dockContext.ToggleDocking()
        elif (
            nHitTest == win32con.HTCAPTION
            and not self.IsFloating()
            and self.dockBar is not None
        ):
            self.dockContext.StartDrag(pt)
        elif nHitTest == win32con.HTSIZE and not self.IsFloating():
            self.StartTracking()
        else:
            return 1
        return 0

    def OnLButtonDblClk(self, msg):
        # only toggle docking if clicked in "void" space
        if self.dockBar is not None:
            # toggle docking
            self.dockContext.ToggleDocking()
            return 0
        return 1

    def OnNcLButtonDblClk(self, msg):
        nHitTest = wparam = msg[2]
        # UINT nHitTest, CPoint point)
        if self.dockBar is not None and nHitTest == win32con.HTCAPTION:
            # toggle docking
            self.dockContext.ToggleDocking()
            return 0
        return 1

    def OnMouseMove(self, msg):
        flags = wparam = msg[2]
        lparam = msg[3]
        if self.IsFloating() or not self.bTracking:
            return 1

        # Convert unsigned 16 bit to signed 32 bit.
        x = win32api.LOWORD(lparam)
        if x & 32768:
            x |= -65536
        y = win32api.HIWORD(lparam)
        if y & 32768:
            y |= -65536
        pt = x, y
        cpt = CenterPoint(self.rectTracker)
        pt = self.ClientToWnd(pt)
        if self.IsHorz():
            if cpt[1] != pt[1]:
                self.OnInvertTracker(self.rectTracker)
                self.rectTracker = OffsetRect(self.rectTracker, (0, pt[1] - cpt[1]))
                self.OnInvertTracker(self.rectTracker)
        else:
            if cpt[0] != pt[0]:
                self.OnInvertTracker(self.rectTracker)
                self.rectTracker = OffsetRect(self.rectTracker, (pt[0] - cpt[0], 0))
                self.OnInvertTracker(self.rectTracker)

        return 0  # Don't pass it on.

    # 	def OnBarStyleChange(self, old, new):

    def OnNcCalcSize(self, bCalcValid, size_info):
        (rc0, rc1, rc2, pos) = size_info
        self.rectBorder = self.GetWindowRect()
        self.rectBorder = OffsetRect(
            self.rectBorder, (-self.rectBorder[0], -self.rectBorder[1])
        )

        dwBorderStyle = self._obj_.dwStyle | afxres.CBRS_BORDER_ANY

        if self.nDockBarID == afxres.AFX_IDW_DOCKBAR_TOP:
            dwBorderStyle &= ~afxres.CBRS_BORDER_BOTTOM
            rc0.left += self.cxGripper
            rc0.bottom -= self.cxEdge
            rc0.top += self.cxBorder
            rc0.right -= self.cxBorder
            self.rectBorder = (
                self.rectBorder[0],
                self.rectBorder[3] - self.cxEdge,
                self.rectBorder[2],
                self.rectBorder[3],
            )
        elif self.nDockBarID == afxres.AFX_IDW_DOCKBAR_BOTTOM:
            dwBorderStyle &= ~afxres.CBRS_BORDER_TOP
            rc0.left += self.cxGripper
            rc0.top += self.cxEdge
            rc0.bottom -= self.cxBorder
            rc0.right -= self.cxBorder
            self.rectBorder = (
                self.rectBorder[0],
                self.rectBorder[1],
                self.rectBorder[2],
                self.rectBorder[1] + self.cxEdge,
            )
        elif self.nDockBarID == afxres.AFX_IDW_DOCKBAR_LEFT:
            dwBorderStyle &= ~afxres.CBRS_BORDER_RIGHT
            rc0.right -= self.cxEdge
            rc0.left += self.cxBorder
            rc0.bottom -= self.cxBorder
            rc0.top += self.cxGripper
            self.rectBorder = (
                self.rectBorder[2] - self.cxEdge,
                self.rectBorder[1],
                self.rectBorder[2],
                self.rectBorder[3],
            )
        elif self.nDockBarID == afxres.AFX_IDW_DOCKBAR_RIGHT:
            dwBorderStyle &= ~afxres.CBRS_BORDER_LEFT
            rc0.left += self.cxEdge
            rc0.right -= self.cxBorder
            rc0.bottom -= self.cxBorder
            rc0.top += self.cxGripper
            self.rectBorder = (
                self.rectBorder[0],
                self.rectBorder[1],
                self.rectBorder[0] + self.cxEdge,
                self.rectBorder[3],
            )
        else:
            self.rectBorder = 0, 0, 0, 0

        self.SetBarStyle(dwBorderStyle)
        return 0

    def OnNcPaint(self, msg):
        self.EraseNonClient()
        dc = self.GetWindowDC()
        ctl = win32api.GetSysColor(win32con.COLOR_BTNHIGHLIGHT)
        cbr = win32api.GetSysColor(win32con.COLOR_BTNSHADOW)
        dc.Draw3dRect(self.rectBorder, ctl, cbr)

        self.DrawGripper(dc)

        rect = self.GetClientRect()
        self.InvalidateRect(rect, 1)
        return 0

    def OnNcHitTest(self, pt):  # A virtual, not a hooked message.
        if self.IsFloating():
            return 1

        ptOrig = pt
        rect = self.GetWindowRect()
        pt = pt[0] - rect[0], pt[1] - rect[1]

        if PtInRect(self.rectClose, pt):
            return win32con.HTSYSMENU
        elif PtInRect(self.rectUndock, pt):
            return win32con.HTMINBUTTON
        elif PtInRect(self.rectGripper, pt):
            return win32con.HTCAPTION
        elif PtInRect(self.rectBorder, pt):
            return win32con.HTSIZE
        else:
            return self._obj_.OnNcHitTest(ptOrig)

    def StartTracking(self):
        self.SetCapture()

        # make sure no updates are pending
        self.RedrawWindow(None, None, win32con.RDW_ALLCHILDREN | win32con.RDW_UPDATENOW)
        self.dockSite.LockWindowUpdate()

        self.ptOld = CenterPoint(self.rectBorder)
        self.bTracking = 1

        self.rectTracker = self.rectBorder
        if not self.IsHorz():
            l, t, r, b = self.rectTracker
            b -= 4
            self.rectTracker = l, t, r, b

        self.OnInvertTracker(self.rectTracker)

    def OnCaptureChanged(self, msg):
        hwnd = lparam = msg[3]
        if self.bTracking and hwnd != self.GetSafeHwnd():
            self.StopTracking(0)  # cancel tracking
        return 1

    def StopTracking(self, bAccept):
        self.OnInvertTracker(self.rectTracker)
        self.dockSite.UnlockWindowUpdate()
        self.bTracking = 0
        self.ReleaseCapture()
        if not bAccept:
            return

        rcc = self.dockSite.GetWindowRect()
        if self.IsHorz():
            newsize = self.sizeHorz[1]
            maxsize = newsize + (rcc[3] - rcc[1])
            minsize = self.sizeMin[1]
        else:
            newsize = self.sizeVert[0]
            maxsize = newsize + (rcc[2] - rcc[0])
            minsize = self.sizeMin[0]

        pt = CenterPoint(self.rectTracker)
        if self.nDockBarID == afxres.AFX_IDW_DOCKBAR_TOP:
            newsize += pt[1] - self.ptOld[1]
        elif self.nDockBarID == afxres.AFX_IDW_DOCKBAR_BOTTOM:
            newsize += -pt[1] + self.ptOld[1]
        elif self.nDockBarID == afxres.AFX_IDW_DOCKBAR_LEFT:
            newsize += pt[0] - self.ptOld[0]
        elif self.nDockBarID == afxres.AFX_IDW_DOCKBAR_RIGHT:
            newsize += -pt[0] + self.ptOld[0]
        newsize = max(minsize, min(maxsize, newsize))
        if self.IsHorz():
            self.sizeHorz = self.sizeHorz[0], newsize
        else:
            self.sizeVert = newsize, self.sizeVert[1]
        self.dockSite.RecalcLayout()
        return 0

    def OnInvertTracker(self, rect):
        assert rect[2] - rect[0] > 0 and rect[3] - rect[1] > 0, "rect is empty"
        assert self.bTracking
        rcc = self.GetWindowRect()
        rcf = self.dockSite.GetWindowRect()

        rect = OffsetRect(rect, (rcc[0] - rcf[0], rcc[1] - rcf[1]))
        rect = DeflateRect(rect, (1, 1))

        flags = win32con.DCX_WINDOW | win32con.DCX_CACHE | win32con.DCX_LOCKWINDOWUPDATE
        dc = self.dockSite.GetDCEx(None, flags)
        try:
            brush = win32ui.GetHalftoneBrush()
            oldBrush = dc.SelectObject(brush)

            dc.PatBlt(
                (rect[0], rect[1]),
                (rect[2] - rect[0], rect[3] - rect[1]),
                win32con.PATINVERT,
            )
            dc.SelectObject(oldBrush)
        finally:
            self.dockSite.ReleaseDC(dc)

    def IsHorz(self):
        return (
            self.nDockBarID == afxres.AFX_IDW_DOCKBAR_TOP
            or self.nDockBarID == afxres.AFX_IDW_DOCKBAR_BOTTOM
        )

    def ClientToWnd(self, pt):
        x, y = pt
        if self.nDockBarID == afxres.AFX_IDW_DOCKBAR_BOTTOM:
            y += self.cxEdge
        elif self.nDockBarID == afxres.AFX_IDW_DOCKBAR_RIGHT:
            x += self.cxEdge
        return x, y

    def DrawGripper(self, dc):
        # no gripper if floating
        if self._obj_.dwStyle & afxres.CBRS_FLOATING:
            return

        # -==HACK==-
        # in order to calculate the client area properly after docking,
        # the client area must be recalculated twice (I have no idea why)
        self.dockSite.RecalcLayout()
        # -==END HACK==-

        gripper = self.GetWindowRect()
        gripper = self.ScreenToClient(gripper)
        gripper = OffsetRect(gripper, (-gripper[0], -gripper[1]))
        gl, gt, gr, gb = gripper

        if self._obj_.dwStyle & afxres.CBRS_ORIENT_HORZ:
            # gripper at left
            self.rectGripper = gl, gt + 40, gl + 20, gb
            # draw close box
            self.rectClose = gl + 7, gt + 10, gl + 19, gt + 22
            dc.DrawFrameControl(
                self.rectClose, win32con.DFC_CAPTION, win32con.DFCS_CAPTIONCLOSE
            )
            # draw docking toggle box
            self.rectUndock = OffsetRect(self.rectClose, (0, 13))
            dc.DrawFrameControl(
                self.rectUndock, win32con.DFC_CAPTION, win32con.DFCS_CAPTIONMAX
            )

            gt += 38
            gb -= 10
            gl += 10
            gr = gl + 3
            gripper = gl, gt, gr, gb
            dc.Draw3dRect(gripper, clrBtnHilight, clrBtnShadow)
            dc.Draw3dRect(OffsetRect(gripper, (4, 0)), clrBtnHilight, clrBtnShadow)
        else:
            # gripper at top
            self.rectGripper = gl, gt, gr - 40, gt + 20
            # draw close box
            self.rectClose = gr - 21, gt + 7, gr - 10, gt + 18
            dc.DrawFrameControl(
                self.rectClose, win32con.DFC_CAPTION, win32con.DFCS_CAPTIONCLOSE
            )
            #  draw docking toggle box
            self.rectUndock = OffsetRect(self.rectClose, (-13, 0))
            dc.DrawFrameControl(
                self.rectUndock, win32con.DFC_CAPTION, win32con.DFCS_CAPTIONMAX
            )
            gr -= 38
            gl += 10
            gt += 10
            gb = gt + 3

            gripper = gl, gt, gr, gb
            dc.Draw3dRect(gripper, clrBtnHilight, clrBtnShadow)
            dc.Draw3dRect(OffsetRect(gripper, (0, 4)), clrBtnHilight, clrBtnShadow)

    def HookMessages(self):
        self.HookMessage(self.OnLButtonUp, win32con.WM_LBUTTONUP)
        self.HookMessage(self.OnLButtonDown, win32con.WM_LBUTTONDOWN)
        self.HookMessage(self.OnLButtonDblClk, win32con.WM_LBUTTONDBLCLK)
        self.HookMessage(self.OnNcLButtonDown, win32con.WM_NCLBUTTONDOWN)
        self.HookMessage(self.OnNcLButtonDblClk, win32con.WM_NCLBUTTONDBLCLK)
        self.HookMessage(self.OnMouseMove, win32con.WM_MOUSEMOVE)
        self.HookMessage(self.OnNcPaint, win32con.WM_NCPAINT)
        self.HookMessage(self.OnCaptureChanged, win32con.WM_CAPTURECHANGED)
        self.HookMessage(self.OnWindowPosChanged, win32con.WM_WINDOWPOSCHANGED)


# 		self.HookMessage(self.OnSize, win32con.WM_SIZE)


def EditCreator(parent):
    d = win32ui.CreateEdit()
    es = (
        win32con.WS_CHILD
        | win32con.WS_VISIBLE
        | win32con.WS_BORDER
        | win32con.ES_MULTILINE
        | win32con.ES_WANTRETURN
    )
    d.CreateWindow(es, (0, 0, 150, 150), parent, 1000)
    return d


def test():
    bar = DockingBar()
    creator = EditCreator
    bar.CreateWindow(win32ui.GetMainFrame(), creator, "Coolbar Demo", 0xFFFFF)
    # 	win32ui.GetMainFrame().ShowControlBar(bar, 1, 0)
    bar.SetBarStyle(
        bar.GetBarStyle()
        | afxres.CBRS_TOOLTIPS
        | afxres.CBRS_FLYBY
        | afxres.CBRS_SIZE_DYNAMIC
    )
    bar.EnableDocking(afxres.CBRS_ALIGN_ANY)
    win32ui.GetMainFrame().DockControlBar(bar, afxres.AFX_IDW_DOCKBAR_BOTTOM)


if __name__ == "__main__":
    test()

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\basic.py ===
"""Implementation of basic magic functions."""


from logging import error
import io
import os
from pprint import pformat
import sys
from warnings import warn

from traitlets.utils.importstring import import_item
from IPython.core import magic_arguments, page
from IPython.core.error import UsageError
from IPython.core.magic import Magics, magics_class, line_magic, magic_escapes
from IPython.utils.text import format_screen, dedent, indent
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils.ipstruct import Struct


class MagicsDisplay:
    def __init__(self, magics_manager, ignore=None):
        self.ignore = ignore if ignore else []
        self.magics_manager = magics_manager

    def _lsmagic(self):
        """The main implementation of the %lsmagic"""
        mesc = magic_escapes['line']
        cesc = magic_escapes['cell']
        mman = self.magics_manager
        magics = mman.lsmagic()
        out = ['Available line magics:',
               mesc + ('  '+mesc).join(sorted([m for m,v in magics['line'].items() if (v not in self.ignore)])),
               '',
               'Available cell magics:',
               cesc + ('  '+cesc).join(sorted([m for m,v in magics['cell'].items() if (v not in self.ignore)])),
               '',
               mman.auto_status()]
        return '\n'.join(out)

    def _repr_pretty_(self, p, cycle):
        p.text(self._lsmagic())

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self._lsmagic()

    def _jsonable(self):
        """turn magics dict into jsonable dict of the same structure

        replaces object instances with their class names as strings
        """
        magic_dict = {}
        mman = self.magics_manager
        magics = mman.lsmagic()
        for key, subdict in magics.items():
            d = {}
            magic_dict[key] = d
            for name, obj in subdict.items():
                try:
                    classname = obj.__self__.__class__.__name__
                except AttributeError:
                    classname = 'Other'

                d[name] = classname
        return magic_dict

    def _repr_json_(self):
        return self._jsonable()


@magics_class
class BasicMagics(Magics):
    """Magics that provide central IPython functionality.

    These are various magics that don't fit into specific categories but that
    are all part of the base 'IPython experience'."""

    @skip_doctest
    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        '-l', '--line', action='store_true',
        help="""Create a line magic alias."""
    )
    @magic_arguments.argument(
        '-c', '--cell', action='store_true',
        help="""Create a cell magic alias."""
    )
    @magic_arguments.argument(
        'name',
        help="""Name of the magic to be created."""
    )
    @magic_arguments.argument(
        'target',
        help="""Name of the existing line or cell magic."""
    )
    @magic_arguments.argument(
        '-p', '--params', default=None,
        help="""Parameters passed to the magic function."""
    )
    @line_magic
    def alias_magic(self, line=''):
        """Create an alias for an existing line or cell magic.

        Examples
        --------
        ::

          In [1]: %alias_magic t timeit
          Created `%t` as an alias for `%timeit`.
          Created `%%t` as an alias for `%%timeit`.

          In [2]: %t -n1 pass
          107 ns ± 43.6 ns per loop (mean ± std. dev. of 7 runs, 1 loop each)

          In [3]: %%t -n1
             ...: pass
             ...:
          107 ns ± 58.3 ns per loop (mean ± std. dev. of 7 runs, 1 loop each)

          In [4]: %alias_magic --cell whereami pwd
          UsageError: Cell magic function `%%pwd` not found.
          In [5]: %alias_magic --line whereami pwd
          Created `%whereami` as an alias for `%pwd`.

          In [6]: %whereami
          Out[6]: '/home/testuser'

          In [7]: %alias_magic h history -p "-l 30" --line
          Created `%h` as an alias for `%history -l 30`.
        """

        args = magic_arguments.parse_argstring(self.alias_magic, line)
        shell = self.shell
        mman = self.shell.magics_manager
        escs = ''.join(magic_escapes.values())

        target = args.target.lstrip(escs)
        name = args.name.lstrip(escs)

        params = args.params
        if (params and
                ((params.startswith('"') and params.endswith('"'))
                or (params.startswith("'") and params.endswith("'")))):
            params = params[1:-1]

        # Find the requested magics.
        m_line = shell.find_magic(target, 'line')
        m_cell = shell.find_magic(target, 'cell')
        if args.line and m_line is None:
            raise UsageError('Line magic function `%s%s` not found.' %
                             (magic_escapes['line'], target))
        if args.cell and m_cell is None:
            raise UsageError('Cell magic function `%s%s` not found.' %
                             (magic_escapes['cell'], target))

        # If --line and --cell are not specified, default to the ones
        # that are available.
        if not args.line and not args.cell:
            if not m_line and not m_cell:
                raise UsageError(
                    'No line or cell magic with name `%s` found.' % target
                )
            args.line = bool(m_line)
            args.cell = bool(m_cell)

        params_str = "" if params is None else " " + params

        if args.line:
            mman.register_alias(name, target, 'line', params)
            print('Created `%s%s` as an alias for `%s%s%s`.' % (
                magic_escapes['line'], name,
                magic_escapes['line'], target, params_str))

        if args.cell:
            mman.register_alias(name, target, 'cell', params)
            print('Created `%s%s` as an alias for `%s%s%s`.' % (
                magic_escapes['cell'], name,
                magic_escapes['cell'], target, params_str))

    @line_magic
    def lsmagic(self, parameter_s=''):
        """List currently available magic functions."""
        return MagicsDisplay(self.shell.magics_manager, ignore=[])

    def _magic_docs(self, brief=False, rest=False):
        """Return docstrings from magic functions."""
        mman = self.shell.magics_manager
        docs = mman.lsmagic_docs(brief, missing='No documentation')

        if rest:
            format_string = '**%s%s**::\n\n%s\n\n'
        else:
            format_string = '%s%s:\n%s\n'

        return ''.join(
            [format_string % (magic_escapes['line'], fname,
                              indent(dedent(fndoc)))
             for fname, fndoc in sorted(docs['line'].items())]
            +
            [format_string % (magic_escapes['cell'], fname,
                              indent(dedent(fndoc)))
             for fname, fndoc in sorted(docs['cell'].items())]
        )

    @line_magic
    def magic(self, parameter_s=''):
        """Print information about the magic function system.

        Supported formats: -latex, -brief, -rest
        """

        mode = ''
        try:
            mode = parameter_s.split()[0][1:]
        except IndexError:
            pass

        brief = (mode == 'brief')
        rest = (mode == 'rest')
        magic_docs = self._magic_docs(brief, rest)

        if mode == 'latex':
            print(self.format_latex(magic_docs))
            return
        else:
            magic_docs = format_screen(magic_docs)

        out = ["""
IPython's 'magic' functions
===========================

The magic function system provides a series of functions which allow you to
control the behavior of IPython itself, plus a lot of system-type
features. There are two kinds of magics, line-oriented and cell-oriented.

Line magics are prefixed with the % character and work much like OS
command-line calls: they get as an argument the rest of the line, where
arguments are passed without parentheses or quotes.  For example, this will
time the given statement::

        %timeit range(1000)

Cell magics are prefixed with a double %%, and they are functions that get as
an argument not only the rest of the line, but also the lines below it in a
separate argument.  These magics are called with two arguments: the rest of the
call line and the body of the cell, consisting of the lines below the first.
For example::

        %%timeit x = numpy.random.randn((100, 100))
        numpy.linalg.svd(x)

will time the execution of the numpy svd routine, running the assignment of x
as part of the setup phase, which is not timed.

In a line-oriented client (the terminal or Qt console IPython), starting a new
input with %% will automatically enter cell mode, and IPython will continue
reading input until a blank line is given.  In the notebook, simply type the
whole cell as one entity, but keep in mind that the %% escape can only be at
the very start of the cell.

NOTE: If you have 'automagic' enabled (via the command line option or with the
%automagic function), you don't need to type in the % explicitly for line
magics; cell magics always require an explicit '%%' escape.  By default,
IPython ships with automagic on, so you should only rarely need the % escape.

Example: typing '%cd mydir' (without the quotes) changes your working directory
to 'mydir', if it exists.

For a list of the available magic functions, use %lsmagic. For a description
of any of them, type %magic_name?, e.g. '%cd?'.

Currently the magic system has the following functions:""",
       magic_docs,
       "Summary of magic functions (from %slsmagic):" % magic_escapes['line'],
       str(self.lsmagic()),
       ]
        page.page('\n'.join(out))


    @line_magic
    def page(self, parameter_s=''):
        """Pretty print the object and display it through a pager.

        %page [options] OBJECT

        If no object is given, use _ (last output).

        Options:

          -r: page str(object), don't pretty-print it."""

        # After a function contributed by Olivier Aubert, slightly modified.

        # Process options/args
        opts, args = self.parse_options(parameter_s, 'r')
        raw = 'r' in opts

        oname = args and args or '_'
        info = self.shell._ofind(oname)
        if info.found:
            if raw:
                txt = str(info.obj)
            else:
                txt = pformat(info.obj)
            page.page(txt)
        else:
            print('Object `%s` not found' % oname)

    @line_magic
    def pprint(self, parameter_s=''):
        """Toggle pretty printing on/off."""
        ptformatter = self.shell.display_formatter.formatters['text/plain']
        ptformatter.pprint = bool(1 - ptformatter.pprint)
        print('Pretty printing has been turned',
              ['OFF','ON'][ptformatter.pprint])

    @line_magic
    def colors(self, parameter_s=''):
        """Switch color scheme/theme globally for IPython

        Examples
        --------
        To get a plain black and white terminal::

          %colors nocolor
        """


        new_theme = parameter_s.strip()
        if not new_theme:
            from IPython.utils.PyColorize import theme_table

            raise UsageError(
                "%colors: you must specify a color theme. See '%colors?'."
                f" Available themes: {list(theme_table.keys())}"
            )

        self.shell.colors = new_theme

    @line_magic
    def xmode(self, parameter_s=''):
        """Switch modes for the exception handlers.

        Valid modes: Plain, Context, Verbose, and Minimal.

        If called without arguments, acts as a toggle.

        When in verbose mode the value `--show` (and `--hide`)
        will respectively show (or hide) frames with ``__tracebackhide__ =
        True`` value set.
        """

        def xmode_switch_err(name):
            warn('Error changing %s exception modes.\n%s' %
                 (name,sys.exc_info()[1]))

        shell = self.shell
        if parameter_s.strip() == "--show":
            shell.InteractiveTB.skip_hidden = False
            return
        if parameter_s.strip() == "--hide":
            shell.InteractiveTB.skip_hidden = True
            return

        new_mode = parameter_s.strip().capitalize()
        try:
            shell.InteractiveTB.set_mode(mode=new_mode)
            print('Exception reporting mode:',shell.InteractiveTB.mode)
        except:
            raise
            xmode_switch_err('user')

    @line_magic
    def quickref(self, arg):
        """ Show a quick reference sheet """
        from IPython.core.usage import quick_reference
        qr = quick_reference + self._magic_docs(brief=True)
        page.page(qr)

    @line_magic
    def doctest_mode(self, parameter_s=''):
        """Toggle doctest mode on and off.

        This mode is intended to make IPython behave as much as possible like a
        plain Python shell, from the perspective of how its prompts, exceptions
        and output look.  This makes it easy to copy and paste parts of a
        session into doctests.  It does so by:

        - Changing the prompts to the classic ``>>>`` ones.
        - Changing the exception reporting mode to 'Plain'.
        - Disabling pretty-printing of output.

        Note that IPython also supports the pasting of code snippets that have
        leading '>>>' and '...' prompts in them.  This means that you can paste
        doctests from files or docstrings (even if they have leading
        whitespace), and the code will execute correctly.  You can then use
        '%history -t' to see the translated history; this will give you the
        input after removal of all the leading prompts and whitespace, which
        can be pasted back into an editor.

        With these features, you can switch into this mode easily whenever you
        need to do testing and changes to doctests, without having to leave
        your existing IPython session.
        """

        # Shorthands
        shell = self.shell
        meta = shell.meta
        disp_formatter = self.shell.display_formatter
        ptformatter = disp_formatter.formatters['text/plain']
        # dstore is a data store kept in the instance metadata bag to track any
        # changes we make, so we can undo them later.
        dstore = meta.setdefault('doctest_mode',Struct())
        save_dstore = dstore.setdefault

        # save a few values we'll need to recover later
        mode = save_dstore('mode',False)
        save_dstore('rc_pprint',ptformatter.pprint)
        save_dstore('xmode',shell.InteractiveTB.mode)
        save_dstore('rc_separate_out',shell.separate_out)
        save_dstore('rc_separate_out2',shell.separate_out2)
        save_dstore('rc_separate_in',shell.separate_in)
        save_dstore('rc_active_types',disp_formatter.active_types)

        if not mode:
            # turn on

            # Prompt separators like plain python
            shell.separate_in = ''
            shell.separate_out = ''
            shell.separate_out2 = ''


            ptformatter.pprint = False
            disp_formatter.active_types = ['text/plain']

            shell.run_line_magic("xmode", "Plain")
        else:
            # turn off
            shell.separate_in = dstore.rc_separate_in

            shell.separate_out = dstore.rc_separate_out
            shell.separate_out2 = dstore.rc_separate_out2

            ptformatter.pprint = dstore.rc_pprint
            disp_formatter.active_types = dstore.rc_active_types

            shell.run_line_magic("xmode", dstore.xmode)

        # mode here is the state before we switch; switch_doctest_mode takes
        # the mode we're switching to.
        shell.switch_doctest_mode(not mode)

        # Store new mode and inform
        dstore.mode = bool(not mode)
        mode_label = ['OFF','ON'][dstore.mode]
        print('Doctest mode is:', mode_label)

    @line_magic
    def gui(self, parameter_s=''):
        """Enable or disable IPython GUI event loop integration.

        %gui [GUINAME]

        This magic replaces IPython's threaded shells that were activated
        using the (pylab/wthread/etc.) command line flags.  GUI toolkits
        can now be enabled at runtime and keyboard
        interrupts should work without any problems.  The following toolkits
        are supported:  wxPython, PyQt4, PyGTK, Tk and Cocoa (OSX)::

            %gui wx      # enable wxPython event loop integration
            %gui qt      # enable PyQt/PySide event loop integration
                         # with the latest version available.
            %gui qt6     # enable PyQt6/PySide6 event loop integration
            %gui qt5     # enable PyQt5/PySide2 event loop integration
            %gui gtk     # enable PyGTK event loop integration
            %gui gtk3    # enable Gtk3 event loop integration
            %gui gtk4    # enable Gtk4 event loop integration
            %gui tk      # enable Tk event loop integration
            %gui osx     # enable Cocoa event loop integration
                         # (requires %matplotlib 1.1)
            %gui         # disable all event loop integration

        WARNING:  after any of these has been called you can simply create
        an application object, but DO NOT start the event loop yourself, as
        we have already handled that.
        """
        opts, arg = self.parse_options(parameter_s, '')
        if arg=='': arg = None
        try:
            return self.shell.enable_gui(arg)
        except Exception as e:
            # print simple error message, rather than traceback if we can't
            # hook up the GUI
            error(str(e))

    @skip_doctest
    @line_magic
    def precision(self, s=''):
        """Set floating point precision for pretty printing.

        Can set either integer precision or a format string.

        If numpy has been imported and precision is an int,
        numpy display precision will also be set, via ``numpy.set_printoptions``.

        If no argument is given, defaults will be restored.

        Examples
        --------
        ::

            In [1]: from math import pi

            In [2]: %precision 3
            Out[2]: '%.3f'

            In [3]: pi
            Out[3]: 3.142

            In [4]: %precision %i
            Out[4]: '%i'

            In [5]: pi
            Out[5]: 3

            In [6]: %precision %e
            Out[6]: '%e'

            In [7]: pi**10
            Out[7]: 9.364805e+04

            In [8]: %precision
            Out[8]: '%r'

            In [9]: pi**10
            Out[9]: 93648.047476082982
        """
        ptformatter = self.shell.display_formatter.formatters['text/plain']
        ptformatter.float_precision = s
        return ptformatter.float_format

    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        'filename', type=str,
        help='Notebook name or filename'
    )
    @line_magic
    def notebook(self, s):
        """Export and convert IPython notebooks.

        This function can export the current IPython history to a notebook file.
        For example, to export the history to "foo.ipynb" do "%notebook foo.ipynb".
        """
        args = magic_arguments.parse_argstring(self.notebook, s)
        outfname = os.path.expanduser(args.filename)

        from nbformat import write, v4

        cells = []
        hist = list(self.shell.history_manager.get_range())
        outputs = self.shell.history_manager.outputs
        exceptions = self.shell.history_manager.exceptions

        if(len(hist)<=1):
            raise ValueError('History is empty, cannot export')
        for session, execution_count, source in hist[:-1]:
            cell = v4.new_code_cell(execution_count=execution_count, source=source)
            for output in outputs[execution_count]:
                for mime_type, data in output.bundle.items():
                    if output.output_type == "out_stream":
                        cell.outputs.append(v4.new_output("stream", text=[data]))
                    elif output.output_type == "err_stream":
                        err_output = v4.new_output("stream", text=[data])
                        err_output.name = "stderr"
                        cell.outputs.append(err_output)
                    elif output.output_type == "execute_result":
                        cell.outputs.append(
                            v4.new_output(
                                "execute_result",
                                data={mime_type: data},
                                execution_count=execution_count,
                            )
                        )
                    elif output.output_type == "display_data":
                        cell.outputs.append(
                            v4.new_output(
                                "display_data",
                                data={mime_type: data},
                            )
                        )
                    else:
                        raise ValueError(f"Unknown output type: {output.output_type}")

            # Check if this execution_count is in exceptions (current session)
            if execution_count in exceptions:
                cell.outputs.append(
                    v4.new_output("error", **exceptions[execution_count])
                )
            cells.append(cell)

        nb = v4.new_notebook(cells=cells)
        with io.open(outfname, "w", encoding="utf-8") as f:
            write(nb, f, version=4)

@magics_class
class AsyncMagics(BasicMagics):

    @line_magic
    def autoawait(self, parameter_s):
        """
        Allow to change the status of the autoawait option.

        This allow you to set a specific asynchronous code runner.

        If no value is passed, print the currently used asynchronous integration
        and whether it is activated.

        It can take a number of value evaluated in the following order:

        - False/false/off deactivate autoawait integration
        - True/true/on activate autoawait integration using configured default
          loop
        - asyncio/curio/trio activate autoawait integration and use integration
          with said library.

        - `sync` turn on the pseudo-sync integration (mostly used for
          `IPython.embed()` which does not run IPython with a real eventloop and
          deactivate running asynchronous code. Turning on Asynchronous code with
          the pseudo sync loop is undefined behavior and may lead IPython to crash.

        If the passed parameter does not match any of the above and is a python
        identifier, get said object from user namespace and set it as the
        runner, and activate autoawait.

        If the object is a fully qualified object name, attempt to import it and
        set it as the runner, and activate autoawait.

        The exact behavior of autoawait is experimental and subject to change
        across version of IPython and Python.
        """

        param = parameter_s.strip()
        d = {True: "on", False: "off"}

        if not param:
            print("IPython autoawait is `{}`, and set to use `{}`".format(
                d[self.shell.autoawait],
                self.shell.loop_runner
            ))
            return None

        if param.lower() in ('false', 'off'):
            self.shell.autoawait = False
            return None
        if param.lower() in ('true', 'on'):
            self.shell.autoawait = True
            return None

        if param in self.shell.loop_runner_map:
            self.shell.loop_runner, self.shell.autoawait = self.shell.loop_runner_map[param]
            return None

        if param in self.shell.user_ns :
            self.shell.loop_runner = self.shell.user_ns[param]
            self.shell.autoawait = True
            return None

        runner = import_item(param)

        self.shell.loop_runner = runner
        self.shell.autoawait = True

# === NexusCore/openenv\Lib\site-packages\nltk\parse\featurechart.py ===
# Natural Language Toolkit: Chart Parser for Feature-Based Grammars
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Rob Speer <rspeer@mit.edu>
#         Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Extension of chart parsing implementation to handle grammars with
feature structures as nodes.
"""
from time import perf_counter

from nltk.featstruct import TYPE, FeatStruct, find_variables, unify
from nltk.grammar import (
    CFG,
    FeatStructNonterminal,
    Nonterminal,
    Production,
    is_nonterminal,
    is_terminal,
)
from nltk.parse.chart import (
    BottomUpPredictCombineRule,
    BottomUpPredictRule,
    CachedTopDownPredictRule,
    Chart,
    ChartParser,
    EdgeI,
    EmptyPredictRule,
    FundamentalRule,
    LeafInitRule,
    SingleEdgeFundamentalRule,
    TopDownInitRule,
    TreeEdge,
)
from nltk.sem import logic
from nltk.tree import Tree

# ////////////////////////////////////////////////////////////
# Tree Edge
# ////////////////////////////////////////////////////////////


class FeatureTreeEdge(TreeEdge):
    """
    A specialized tree edge that allows shared variable bindings
    between nonterminals on the left-hand side and right-hand side.

    Each ``FeatureTreeEdge`` contains a set of ``bindings``, i.e., a
    dictionary mapping from variables to values.  If the edge is not
    complete, then these bindings are simply stored.  However, if the
    edge is complete, then the constructor applies these bindings to
    every nonterminal in the edge whose symbol implements the
    interface ``SubstituteBindingsI``.
    """

    def __init__(self, span, lhs, rhs, dot=0, bindings=None):
        """
        Construct a new edge.  If the edge is incomplete (i.e., if
        ``dot<len(rhs)``), then store the bindings as-is.  If the edge
        is complete (i.e., if ``dot==len(rhs)``), then apply the
        bindings to all nonterminals in ``lhs`` and ``rhs``, and then
        clear the bindings.  See ``TreeEdge`` for a description of
        the other arguments.
        """
        if bindings is None:
            bindings = {}

        # If the edge is complete, then substitute in the bindings,
        # and then throw them away.  (If we didn't throw them away, we
        # might think that 2 complete edges are different just because
        # they have different bindings, even though all bindings have
        # already been applied.)
        if dot == len(rhs) and bindings:
            lhs = self._bind(lhs, bindings)
            rhs = [self._bind(elt, bindings) for elt in rhs]
            bindings = {}

        # Initialize the edge.
        TreeEdge.__init__(self, span, lhs, rhs, dot)
        self._bindings = bindings
        self._comparison_key = (self._comparison_key, tuple(sorted(bindings.items())))

    @staticmethod
    def from_production(production, index):
        """
        :return: A new ``TreeEdge`` formed from the given production.
            The new edge's left-hand side and right-hand side will
            be taken from ``production``; its span will be
            ``(index,index)``; and its dot position will be ``0``.
        :rtype: TreeEdge
        """
        return FeatureTreeEdge(
            span=(index, index), lhs=production.lhs(), rhs=production.rhs(), dot=0
        )

    def move_dot_forward(self, new_end, bindings=None):
        """
        :return: A new ``FeatureTreeEdge`` formed from this edge.
            The new edge's dot position is increased by ``1``,
            and its end index will be replaced by ``new_end``.
        :rtype: FeatureTreeEdge
        :param new_end: The new end index.
        :type new_end: int
        :param bindings: Bindings for the new edge.
        :type bindings: dict
        """
        return FeatureTreeEdge(
            span=(self._span[0], new_end),
            lhs=self._lhs,
            rhs=self._rhs,
            dot=self._dot + 1,
            bindings=bindings,
        )

    def _bind(self, nt, bindings):
        if not isinstance(nt, FeatStructNonterminal):
            return nt
        return nt.substitute_bindings(bindings)

    def next_with_bindings(self):
        return self._bind(self.nextsym(), self._bindings)

    def bindings(self):
        """
        Return a copy of this edge's bindings dictionary.
        """
        return self._bindings.copy()

    def variables(self):
        """
        :return: The set of variables used by this edge.
        :rtype: set(Variable)
        """
        return find_variables(
            [self._lhs]
            + list(self._rhs)
            + list(self._bindings.keys())
            + list(self._bindings.values()),
            fs_class=FeatStruct,
        )

    def __str__(self):
        if self.is_complete():
            return super().__str__()
        else:
            bindings = "{%s}" % ", ".join(
                "%s: %r" % item for item in sorted(self._bindings.items())
            )
            return f"{super().__str__()} {bindings}"


# ////////////////////////////////////////////////////////////
# A specialized Chart for feature grammars
# ////////////////////////////////////////////////////////////

# TODO: subsumes check when adding new edges


class FeatureChart(Chart):
    """
    A Chart for feature grammars.
    :see: ``Chart`` for more information.
    """

    def select(self, **restrictions):
        """
        Returns an iterator over the edges in this chart.
        See ``Chart.select`` for more information about the
        ``restrictions`` on the edges.
        """
        # If there are no restrictions, then return all edges.
        if restrictions == {}:
            return iter(self._edges)

        # Find the index corresponding to the given restrictions.
        restr_keys = sorted(restrictions.keys())
        restr_keys = tuple(restr_keys)

        # If it doesn't exist, then create it.
        if restr_keys not in self._indexes:
            self._add_index(restr_keys)

        vals = tuple(
            self._get_type_if_possible(restrictions[key]) for key in restr_keys
        )
        return iter(self._indexes[restr_keys].get(vals, []))

    def _add_index(self, restr_keys):
        """
        A helper function for ``select``, which creates a new index for
        a given set of attributes (aka restriction keys).
        """
        # Make sure it's a valid index.
        for key in restr_keys:
            if not hasattr(EdgeI, key):
                raise ValueError("Bad restriction: %s" % key)

        # Create the index.
        index = self._indexes[restr_keys] = {}

        # Add all existing edges to the index.
        for edge in self._edges:
            vals = tuple(
                self._get_type_if_possible(getattr(edge, key)()) for key in restr_keys
            )
            index.setdefault(vals, []).append(edge)

    def _register_with_indexes(self, edge):
        """
        A helper function for ``insert``, which registers the new
        edge with all existing indexes.
        """
        for restr_keys, index in self._indexes.items():
            vals = tuple(
                self._get_type_if_possible(getattr(edge, key)()) for key in restr_keys
            )
            index.setdefault(vals, []).append(edge)

    def _get_type_if_possible(self, item):
        """
        Helper function which returns the ``TYPE`` feature of the ``item``,
        if it exists, otherwise it returns the ``item`` itself
        """
        if isinstance(item, dict) and TYPE in item:
            return item[TYPE]
        else:
            return item

    def parses(self, start, tree_class=Tree):
        for edge in self.select(start=0, end=self._num_leaves):
            if (
                (isinstance(edge, FeatureTreeEdge))
                and (edge.lhs()[TYPE] == start[TYPE])
                and (unify(edge.lhs(), start, rename_vars=True))
            ):
                yield from self.trees(edge, complete=True, tree_class=tree_class)


# ////////////////////////////////////////////////////////////
# Fundamental Rule
# ////////////////////////////////////////////////////////////


class FeatureFundamentalRule(FundamentalRule):
    r"""
    A specialized version of the fundamental rule that operates on
    nonterminals whose symbols are ``FeatStructNonterminal``s.  Rather
    than simply comparing the nonterminals for equality, they are
    unified.  Variable bindings from these unifications are collected
    and stored in the chart using a ``FeatureTreeEdge``.  When a
    complete edge is generated, these bindings are applied to all
    nonterminals in the edge.

    The fundamental rule states that:

    - ``[A -> alpha \* B1 beta][i:j]``
    - ``[B2 -> gamma \*][j:k]``

    licenses the edge:

    - ``[A -> alpha B3 \* beta][i:j]``

    assuming that B1 and B2 can be unified to generate B3.
    """

    def apply(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (
            left_edge.end() == right_edge.start()
            and left_edge.is_incomplete()
            and right_edge.is_complete()
            and isinstance(left_edge, FeatureTreeEdge)
        ):
            return
        found = right_edge.lhs()
        nextsym = left_edge.nextsym()
        if isinstance(right_edge, FeatureTreeEdge):
            if not is_nonterminal(nextsym):
                return
            if left_edge.nextsym()[TYPE] != right_edge.lhs()[TYPE]:
                return
            # Create a copy of the bindings.
            bindings = left_edge.bindings()
            # We rename vars here, because we don't want variables
            # from the two different productions to match.
            found = found.rename_variables(used_vars=left_edge.variables())
            # Unify B1 (left_edge.nextsym) with B2 (right_edge.lhs) to
            # generate B3 (result).
            result = unify(nextsym, found, bindings, rename_vars=False)
            if result is None:
                return
        else:
            if nextsym != found:
                return
            # Create a copy of the bindings.
            bindings = left_edge.bindings()

        # Construct the new edge.
        new_edge = left_edge.move_dot_forward(right_edge.end(), bindings)

        # Add it to the chart, with appropriate child pointers.
        if chart.insert_with_backpointer(new_edge, left_edge, right_edge):
            yield new_edge


class FeatureSingleEdgeFundamentalRule(SingleEdgeFundamentalRule):
    """
    A specialized version of the completer / single edge fundamental rule
    that operates on nonterminals whose symbols are ``FeatStructNonterminal``.
    Rather than simply comparing the nonterminals for equality, they are
    unified.
    """

    _fundamental_rule = FeatureFundamentalRule()

    def _apply_complete(self, chart, grammar, right_edge):
        fr = self._fundamental_rule
        for left_edge in chart.select(
            end=right_edge.start(), is_complete=False, nextsym=right_edge.lhs()
        ):
            yield from fr.apply(chart, grammar, left_edge, right_edge)

    def _apply_incomplete(self, chart, grammar, left_edge):
        fr = self._fundamental_rule
        for right_edge in chart.select(
            start=left_edge.end(), is_complete=True, lhs=left_edge.nextsym()
        ):
            yield from fr.apply(chart, grammar, left_edge, right_edge)


# ////////////////////////////////////////////////////////////
# Top-Down Prediction
# ////////////////////////////////////////////////////////////


class FeatureTopDownInitRule(TopDownInitRule):
    def apply(self, chart, grammar):
        for prod in grammar.productions(lhs=grammar.start()):
            new_edge = FeatureTreeEdge.from_production(prod, 0)
            if chart.insert(new_edge, ()):
                yield new_edge


class FeatureTopDownPredictRule(CachedTopDownPredictRule):
    r"""
    A specialized version of the (cached) top down predict rule that operates
    on nonterminals whose symbols are ``FeatStructNonterminal``.  Rather
    than simply comparing the nonterminals for equality, they are
    unified.

    The top down expand rule states that:

    - ``[A -> alpha \* B1 beta][i:j]``

    licenses the edge:

    - ``[B2 -> \* gamma][j:j]``

    for each grammar production ``B2 -> gamma``, assuming that B1
    and B2 can be unified.
    """

    def apply(self, chart, grammar, edge):
        if edge.is_complete():
            return
        nextsym, index = edge.nextsym(), edge.end()
        if not is_nonterminal(nextsym):
            return

        # If we've already applied this rule to an edge with the same
        # next & end, and the chart & grammar have not changed, then
        # just return (no new edges to add).
        nextsym_with_bindings = edge.next_with_bindings()
        done = self._done.get((nextsym_with_bindings, index), (None, None))
        if done[0] is chart and done[1] is grammar:
            return

        for prod in grammar.productions(lhs=nextsym):
            # If the left corner in the predicted production is
            # leaf, it must match with the input.
            if prod.rhs():
                first = prod.rhs()[0]
                if is_terminal(first):
                    if index >= chart.num_leaves():
                        continue
                    if first != chart.leaf(index):
                        continue

            # We rename vars here, because we don't want variables
            # from the two different productions to match.
            if unify(prod.lhs(), nextsym_with_bindings, rename_vars=True):
                new_edge = FeatureTreeEdge.from_production(prod, edge.end())
                if chart.insert(new_edge, ()):
                    yield new_edge

        # Record the fact that we've applied this rule.
        self._done[nextsym_with_bindings, index] = (chart, grammar)


# ////////////////////////////////////////////////////////////
# Bottom-Up Prediction
# ////////////////////////////////////////////////////////////


class FeatureBottomUpPredictRule(BottomUpPredictRule):
    def apply(self, chart, grammar, edge):
        if edge.is_incomplete():
            return
        for prod in grammar.productions(rhs=edge.lhs()):
            if isinstance(edge, FeatureTreeEdge):
                _next = prod.rhs()[0]
                if not is_nonterminal(_next):
                    continue

            new_edge = FeatureTreeEdge.from_production(prod, edge.start())
            if chart.insert(new_edge, ()):
                yield new_edge


class FeatureBottomUpPredictCombineRule(BottomUpPredictCombineRule):
    def apply(self, chart, grammar, edge):
        if edge.is_incomplete():
            return
        found = edge.lhs()
        for prod in grammar.productions(rhs=found):
            bindings = {}
            if isinstance(edge, FeatureTreeEdge):
                _next = prod.rhs()[0]
                if not is_nonterminal(_next):
                    continue

                # We rename vars here, because we don't want variables
                # from the two different productions to match.
                used_vars = find_variables(
                    (prod.lhs(),) + prod.rhs(), fs_class=FeatStruct
                )
                found = found.rename_variables(used_vars=used_vars)

                result = unify(_next, found, bindings, rename_vars=False)
                if result is None:
                    continue

            new_edge = FeatureTreeEdge.from_production(
                prod, edge.start()
            ).move_dot_forward(edge.end(), bindings)
            if chart.insert(new_edge, (edge,)):
                yield new_edge


class FeatureEmptyPredictRule(EmptyPredictRule):
    def apply(self, chart, grammar):
        for prod in grammar.productions(empty=True):
            for index in range(chart.num_leaves() + 1):
                new_edge = FeatureTreeEdge.from_production(prod, index)
                if chart.insert(new_edge, ()):
                    yield new_edge


# ////////////////////////////////////////////////////////////
# Feature Chart Parser
# ////////////////////////////////////////////////////////////

TD_FEATURE_STRATEGY = [
    LeafInitRule(),
    FeatureTopDownInitRule(),
    FeatureTopDownPredictRule(),
    FeatureSingleEdgeFundamentalRule(),
]
BU_FEATURE_STRATEGY = [
    LeafInitRule(),
    FeatureEmptyPredictRule(),
    FeatureBottomUpPredictRule(),
    FeatureSingleEdgeFundamentalRule(),
]
BU_LC_FEATURE_STRATEGY = [
    LeafInitRule(),
    FeatureEmptyPredictRule(),
    FeatureBottomUpPredictCombineRule(),
    FeatureSingleEdgeFundamentalRule(),
]


class FeatureChartParser(ChartParser):
    def __init__(
        self,
        grammar,
        strategy=BU_LC_FEATURE_STRATEGY,
        trace_chart_width=20,
        chart_class=FeatureChart,
        **parser_args,
    ):
        ChartParser.__init__(
            self,
            grammar,
            strategy=strategy,
            trace_chart_width=trace_chart_width,
            chart_class=chart_class,
            **parser_args,
        )


class FeatureTopDownChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(self, grammar, TD_FEATURE_STRATEGY, **parser_args)


class FeatureBottomUpChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(self, grammar, BU_FEATURE_STRATEGY, **parser_args)


class FeatureBottomUpLeftCornerChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(
            self, grammar, BU_LC_FEATURE_STRATEGY, **parser_args
        )


# ////////////////////////////////////////////////////////////
# Instantiate Variable Chart
# ////////////////////////////////////////////////////////////


class InstantiateVarsChart(FeatureChart):
    """
    A specialized chart that 'instantiates' variables whose names
    start with '@', by replacing them with unique new variables.
    In particular, whenever a complete edge is added to the chart, any
    variables in the edge's ``lhs`` whose names start with '@' will be
    replaced by unique new ``Variable``.
    """

    def __init__(self, tokens):
        FeatureChart.__init__(self, tokens)

    def initialize(self):
        self._instantiated = set()
        FeatureChart.initialize(self)

    def insert(self, edge, child_pointer_list):
        if edge in self._instantiated:
            return False
        self.instantiate_edge(edge)
        return FeatureChart.insert(self, edge, child_pointer_list)

    def instantiate_edge(self, edge):
        """
        If the edge is a ``FeatureTreeEdge``, and it is complete,
        then instantiate all variables whose names start with '@',
        by replacing them with unique new variables.

        Note that instantiation is done in-place, since the
        parsing algorithms might already hold a reference to
        the edge for future use.
        """
        # If the edge is a leaf, or is not complete, or is
        # already in the chart, then just return it as-is.
        if not isinstance(edge, FeatureTreeEdge):
            return
        if not edge.is_complete():
            return
        if edge in self._edge_to_cpls:
            return

        # Get a list of variables that need to be instantiated.
        # If there are none, then return as-is.
        inst_vars = self.inst_vars(edge)
        if not inst_vars:
            return

        # Instantiate the edge!
        self._instantiated.add(edge)
        edge._lhs = edge.lhs().substitute_bindings(inst_vars)

    def inst_vars(self, edge):
        return {
            var: logic.unique_variable()
            for var in edge.lhs().variables()
            if var.name.startswith("@")
        }


# ////////////////////////////////////////////////////////////
# Demo
# ////////////////////////////////////////////////////////////


def demo_grammar():
    from nltk.grammar import FeatureGrammar

    return FeatureGrammar.fromstring(
        """
S  -> NP VP
PP -> Prep NP
NP -> NP PP
VP -> VP PP
VP -> Verb NP
VP -> Verb
NP -> Det[pl=?x] Noun[pl=?x]
NP -> "John"
NP -> "I"
Det -> "the"
Det -> "my"
Det[-pl] -> "a"
Noun[-pl] -> "dog"
Noun[-pl] -> "cookie"
Verb -> "ate"
Verb -> "saw"
Prep -> "with"
Prep -> "under"
"""
    )


def demo(
    print_times=True,
    print_grammar=True,
    print_trees=True,
    print_sentence=True,
    trace=1,
    parser=FeatureChartParser,
    sent="I saw John with a dog with my cookie",
):
    import sys
    import time

    print()
    grammar = demo_grammar()
    if print_grammar:
        print(grammar)
        print()
    print("*", parser.__name__)
    if print_sentence:
        print("Sentence:", sent)
    tokens = sent.split()
    t = perf_counter()
    cp = parser(grammar, trace=trace)
    chart = cp.chart_parse(tokens)
    trees = list(chart.parses(grammar.start()))
    if print_times:
        print("Time: %s" % (perf_counter() - t))
    if print_trees:
        for tree in trees:
            print(tree)
    else:
        print("Nr trees:", len(trees))


def run_profile():
    import profile

    profile.run("for i in range(1): demo()", "/tmp/profile.out")
    import pstats

    p = pstats.Stats("/tmp/profile.out")
    p.strip_dirs().sort_stats("time", "cum").print_stats(60)
    p.strip_dirs().sort_stats("cum", "time").print_stats(60)


if __name__ == "__main__":
    from nltk.data import load

    demo()
    print()
    grammar = load("grammars/book_grammars/feat0.fcfg")
    cp = FeatureChartParser(grammar, trace=2)
    sent = "Kim likes children"
    tokens = sent.split()
    trees = cp.parse(tokens)
    for tree in trees:
        print(tree)

# === NexusCore/openenv\Lib\site-packages\wsproto\frame_protocol.py ===
"""
wsproto/frame_protocol
~~~~~~~~~~~~~~~~~~~~~~

WebSocket frame protocol implementation.
"""

import os
import struct
from codecs import getincrementaldecoder, IncrementalDecoder
from enum import IntEnum
from typing import Generator, List, NamedTuple, Optional, Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .extensions import Extension  # pragma: no cover


_XOR_TABLE = [bytes(a ^ b for a in range(256)) for b in range(256)]


class XorMaskerSimple:
    def __init__(self, masking_key: bytes) -> None:
        self._masking_key = masking_key

    def process(self, data: bytes) -> bytes:
        if data:
            data_array = bytearray(data)
            a, b, c, d = (_XOR_TABLE[n] for n in self._masking_key)
            data_array[::4] = data_array[::4].translate(a)
            data_array[1::4] = data_array[1::4].translate(b)
            data_array[2::4] = data_array[2::4].translate(c)
            data_array[3::4] = data_array[3::4].translate(d)

            # Rotate the masking key so that the next usage continues
            # with the next key element, rather than restarting.
            key_rotation = len(data) % 4
            self._masking_key = (
                self._masking_key[key_rotation:] + self._masking_key[:key_rotation]
            )

            return bytes(data_array)
        return data


class XorMaskerNull:
    def process(self, data: bytes) -> bytes:
        return data


# RFC6455, Section 5.2 - Base Framing Protocol

# Payload length constants
PAYLOAD_LENGTH_TWO_BYTE = 126
PAYLOAD_LENGTH_EIGHT_BYTE = 127
MAX_PAYLOAD_NORMAL = 125
MAX_PAYLOAD_TWO_BYTE = 2**16 - 1
MAX_PAYLOAD_EIGHT_BYTE = 2**64 - 1
MAX_FRAME_PAYLOAD = MAX_PAYLOAD_EIGHT_BYTE

# MASK and PAYLOAD LEN are packed into a byte
MASK_MASK = 0x80
PAYLOAD_LEN_MASK = 0x7F

# FIN, RSV[123] and OPCODE are packed into a single byte
FIN_MASK = 0x80
RSV1_MASK = 0x40
RSV2_MASK = 0x20
RSV3_MASK = 0x10
OPCODE_MASK = 0x0F


class Opcode(IntEnum):
    """
    RFC 6455, Section 5.2 - Base Framing Protocol
    """

    #: Continuation frame
    CONTINUATION = 0x0

    #: Text message
    TEXT = 0x1

    #: Binary message
    BINARY = 0x2

    #: Close frame
    CLOSE = 0x8

    #: Ping frame
    PING = 0x9

    #: Pong frame
    PONG = 0xA

    def iscontrol(self) -> bool:
        return bool(self & 0x08)


class CloseReason(IntEnum):
    """
    RFC 6455, Section 7.4.1 - Defined Status Codes
    """

    #: indicates a normal closure, meaning that the purpose for
    #: which the connection was established has been fulfilled.
    NORMAL_CLOSURE = 1000

    #: indicates that an endpoint is "going away", such as a server
    #: going down or a browser having navigated away from a page.
    GOING_AWAY = 1001

    #: indicates that an endpoint is terminating the connection due
    #: to a protocol error.
    PROTOCOL_ERROR = 1002

    #: indicates that an endpoint is terminating the connection
    #: because it has received a type of data it cannot accept (e.g., an
    #: endpoint that understands only text data MAY send this if it
    #: receives a binary message).
    UNSUPPORTED_DATA = 1003

    #: Reserved.  The specific meaning might be defined in the future.
    # DON'T DEFINE THIS: RESERVED_1004 = 1004

    #: is a reserved value and MUST NOT be set as a status code in a
    #: Close control frame by an endpoint.  It is designated for use in
    #: applications expecting a status code to indicate that no status
    #: code was actually present.
    NO_STATUS_RCVD = 1005

    #: is a reserved value and MUST NOT be set as a status code in a
    #: Close control frame by an endpoint.  It is designated for use in
    #: applications expecting a status code to indicate that the
    #: connection was closed abnormally, e.g., without sending or
    #: receiving a Close control frame.
    ABNORMAL_CLOSURE = 1006

    #: indicates that an endpoint is terminating the connection
    #: because it has received data within a message that was not
    #: consistent with the type of the message (e.g., non-UTF-8 [RFC3629]
    #: data within a text message).
    INVALID_FRAME_PAYLOAD_DATA = 1007

    #: indicates that an endpoint is terminating the connection
    #: because it has received a message that violates its policy.  This
    #: is a generic status code that can be returned when there is no
    #: other more suitable status code (e.g., 1003 or 1009) or if there
    #: is a need to hide specific details about the policy.
    POLICY_VIOLATION = 1008

    #: indicates that an endpoint is terminating the connection
    #: because it has received a message that is too big for it to
    #: process.
    MESSAGE_TOO_BIG = 1009

    #: indicates that an endpoint (client) is terminating the
    #: connection because it has expected the server to negotiate one or
    #: more extension, but the server didn't return them in the response
    #: message of the WebSocket handshake.  The list of extensions that
    #: are needed SHOULD appear in the /reason/ part of the Close frame.
    #: Note that this status code is not used by the server, because it
    #: can fail the WebSocket handshake instead.
    MANDATORY_EXT = 1010

    #: indicates that a server is terminating the connection because
    #: it encountered an unexpected condition that prevented it from
    #: fulfilling the request.
    INTERNAL_ERROR = 1011

    #: Server/service is restarting
    #: (not part of RFC6455)
    SERVICE_RESTART = 1012

    #: Temporary server condition forced blocking client's request
    #: (not part of RFC6455)
    TRY_AGAIN_LATER = 1013

    #: is a reserved value and MUST NOT be set as a status code in a
    #: Close control frame by an endpoint.  It is designated for use in
    #: applications expecting a status code to indicate that the
    #: connection was closed due to a failure to perform a TLS handshake
    #: (e.g., the server certificate can't be verified).
    TLS_HANDSHAKE_FAILED = 1015


# RFC 6455, Section 7.4.1 - Defined Status Codes
LOCAL_ONLY_CLOSE_REASONS = (
    CloseReason.NO_STATUS_RCVD,
    CloseReason.ABNORMAL_CLOSURE,
    CloseReason.TLS_HANDSHAKE_FAILED,
)


# RFC 6455, Section 7.4.2 - Status Code Ranges
MIN_CLOSE_REASON = 1000
MIN_PROTOCOL_CLOSE_REASON = 1000
MAX_PROTOCOL_CLOSE_REASON = 2999
MIN_LIBRARY_CLOSE_REASON = 3000
MAX_LIBRARY_CLOSE_REASON = 3999
MIN_PRIVATE_CLOSE_REASON = 4000
MAX_PRIVATE_CLOSE_REASON = 4999
MAX_CLOSE_REASON = 4999


NULL_MASK = struct.pack("!I", 0)


class ParseFailed(Exception):
    def __init__(
        self, msg: str, code: CloseReason = CloseReason.PROTOCOL_ERROR
    ) -> None:
        super().__init__(msg)
        self.code = code


class RsvBits(NamedTuple):
    rsv1: bool
    rsv2: bool
    rsv3: bool


class Header(NamedTuple):
    fin: bool
    rsv: RsvBits
    opcode: Opcode
    payload_len: int
    masking_key: Optional[bytes]


class Frame(NamedTuple):
    opcode: Opcode
    payload: Union[bytes, str, Tuple[int, str]]
    frame_finished: bool
    message_finished: bool


def _truncate_utf8(data: bytes, nbytes: int) -> bytes:
    if len(data) <= nbytes:
        return data

    # Truncate
    data = data[:nbytes]
    # But we might have cut a codepoint in half, in which case we want to
    # discard the partial character so the data is at least
    # well-formed. This is a little inefficient since it processes the
    # whole message twice when in theory we could just peek at the last
    # few characters, but since this is only used for close messages (max
    # length = 125 bytes) it really doesn't matter.
    data = data.decode("utf-8", errors="ignore").encode("utf-8")
    return data


class Buffer:
    def __init__(self, initial_bytes: Optional[bytes] = None) -> None:
        self.buffer = bytearray()
        self.bytes_used = 0
        if initial_bytes:
            self.feed(initial_bytes)

    def feed(self, new_bytes: bytes) -> None:
        self.buffer += new_bytes

    def consume_at_most(self, nbytes: int) -> bytes:
        if not nbytes:
            return bytearray()

        data = self.buffer[self.bytes_used : self.bytes_used + nbytes]
        self.bytes_used += len(data)
        return data

    def consume_exactly(self, nbytes: int) -> Optional[bytes]:
        if len(self.buffer) - self.bytes_used < nbytes:
            return None

        return self.consume_at_most(nbytes)

    def commit(self) -> None:
        # In CPython 3.4+, del[:n] is amortized O(n), *not* quadratic
        del self.buffer[: self.bytes_used]
        self.bytes_used = 0

    def rollback(self) -> None:
        self.bytes_used = 0

    def __len__(self) -> int:
        return len(self.buffer)


class MessageDecoder:
    def __init__(self) -> None:
        self.opcode: Optional[Opcode] = None
        self.decoder: Optional[IncrementalDecoder] = None

    def process_frame(self, frame: Frame) -> Frame:
        assert not frame.opcode.iscontrol()

        if self.opcode is None:
            if frame.opcode is Opcode.CONTINUATION:
                raise ParseFailed("unexpected CONTINUATION")
            self.opcode = frame.opcode
        elif frame.opcode is not Opcode.CONTINUATION:
            raise ParseFailed("expected CONTINUATION, got %r" % frame.opcode)

        if frame.opcode is Opcode.TEXT:
            self.decoder = getincrementaldecoder("utf-8")()

        finished = frame.frame_finished and frame.message_finished

        if self.decoder is None:
            data = frame.payload
        else:
            assert isinstance(frame.payload, (bytes, bytearray))
            try:
                data = self.decoder.decode(frame.payload, finished)
            except UnicodeDecodeError as exc:
                raise ParseFailed(str(exc), CloseReason.INVALID_FRAME_PAYLOAD_DATA)

        frame = Frame(self.opcode, data, frame.frame_finished, finished)

        if finished:
            self.opcode = None
            self.decoder = None

        return frame


class FrameDecoder:
    def __init__(
        self, client: bool, extensions: Optional[List["Extension"]] = None
    ) -> None:
        self.client = client
        self.extensions = extensions or []

        self.buffer = Buffer()

        self.header: Optional[Header] = None
        self.effective_opcode: Optional[Opcode] = None
        self.masker: Union[None, XorMaskerNull, XorMaskerSimple] = None
        self.payload_required = 0
        self.payload_consumed = 0

    def receive_bytes(self, data: bytes) -> None:
        self.buffer.feed(data)

    def process_buffer(self) -> Optional[Frame]:
        if not self.header:
            if not self.parse_header():
                return None
        # parse_header() sets these.
        assert self.header is not None
        assert self.masker is not None
        assert self.effective_opcode is not None

        if len(self.buffer) < self.payload_required:
            return None

        payload_remaining = self.header.payload_len - self.payload_consumed
        payload = self.buffer.consume_at_most(payload_remaining)
        if not payload and self.header.payload_len > 0:
            return None
        self.buffer.commit()

        self.payload_consumed += len(payload)
        finished = self.payload_consumed == self.header.payload_len

        payload = self.masker.process(payload)

        for extension in self.extensions:
            payload_ = extension.frame_inbound_payload_data(self, payload)
            if isinstance(payload_, CloseReason):
                raise ParseFailed("error in extension", payload_)
            payload = payload_

        if finished:
            final = bytearray()
            for extension in self.extensions:
                result = extension.frame_inbound_complete(self, self.header.fin)
                if isinstance(result, CloseReason):
                    raise ParseFailed("error in extension", result)
                if result is not None:
                    final += result
            payload += final

        frame = Frame(self.effective_opcode, payload, finished, self.header.fin)

        if finished:
            self.header = None
            self.effective_opcode = None
            self.masker = None
        else:
            self.effective_opcode = Opcode.CONTINUATION

        return frame

    def parse_header(self) -> bool:
        data = self.buffer.consume_exactly(2)
        if data is None:
            self.buffer.rollback()
            return False

        fin = bool(data[0] & FIN_MASK)
        rsv = RsvBits(
            bool(data[0] & RSV1_MASK),
            bool(data[0] & RSV2_MASK),
            bool(data[0] & RSV3_MASK),
        )
        opcode = data[0] & OPCODE_MASK
        try:
            opcode = Opcode(opcode)
        except ValueError:
            raise ParseFailed(f"Invalid opcode {opcode:#x}")

        if opcode.iscontrol() and not fin:
            raise ParseFailed("Invalid attempt to fragment control frame")

        has_mask = bool(data[1] & MASK_MASK)
        payload_len_short = data[1] & PAYLOAD_LEN_MASK
        payload_len = self.parse_extended_payload_length(opcode, payload_len_short)
        if payload_len is None:
            self.buffer.rollback()
            return False

        self.extension_processing(opcode, rsv, payload_len)

        if has_mask and self.client:
            raise ParseFailed("client received unexpected masked frame")
        if not has_mask and not self.client:
            raise ParseFailed("server received unexpected unmasked frame")
        if has_mask:
            masking_key = self.buffer.consume_exactly(4)
            if masking_key is None:
                self.buffer.rollback()
                return False
            self.masker = XorMaskerSimple(masking_key)
        else:
            self.masker = XorMaskerNull()

        self.buffer.commit()
        self.header = Header(fin, rsv, opcode, payload_len, None)
        self.effective_opcode = self.header.opcode
        if self.header.opcode.iscontrol():
            self.payload_required = payload_len
        else:
            self.payload_required = 0
        self.payload_consumed = 0
        return True

    def parse_extended_payload_length(
        self, opcode: Opcode, payload_len: int
    ) -> Optional[int]:
        if opcode.iscontrol() and payload_len > MAX_PAYLOAD_NORMAL:
            raise ParseFailed("Control frame with payload len > 125")
        if payload_len == PAYLOAD_LENGTH_TWO_BYTE:
            data = self.buffer.consume_exactly(2)
            if data is None:
                return None
            (payload_len,) = struct.unpack("!H", data)
            if payload_len <= MAX_PAYLOAD_NORMAL:
                raise ParseFailed(
                    "Payload length used 2 bytes when 1 would have sufficed"
                )
        elif payload_len == PAYLOAD_LENGTH_EIGHT_BYTE:
            data = self.buffer.consume_exactly(8)
            if data is None:
                return None
            (payload_len,) = struct.unpack("!Q", data)
            if payload_len <= MAX_PAYLOAD_TWO_BYTE:
                raise ParseFailed(
                    "Payload length used 8 bytes when 2 would have sufficed"
                )
            if payload_len >> 63:
                # I'm not sure why this is illegal, but that's what the RFC
                # says, so...
                raise ParseFailed("8-byte payload length with non-zero MSB")

        return payload_len

    def extension_processing(
        self, opcode: Opcode, rsv: RsvBits, payload_len: int
    ) -> None:
        rsv_used = [False, False, False]
        for extension in self.extensions:
            result = extension.frame_inbound_header(self, opcode, rsv, payload_len)
            if isinstance(result, CloseReason):
                raise ParseFailed("error in extension", result)
            for bit, used in enumerate(result):
                if used:
                    rsv_used[bit] = True
        for expected, found in zip(rsv_used, rsv):
            if found and not expected:
                raise ParseFailed("Reserved bit set unexpectedly")


class FrameProtocol:
    def __init__(self, client: bool, extensions: List["Extension"]) -> None:
        self.client = client
        self.extensions = [ext for ext in extensions if ext.enabled()]

        # Global state
        self._frame_decoder = FrameDecoder(self.client, self.extensions)
        self._message_decoder = MessageDecoder()
        self._parse_more = self._parse_more_gen()

        self._outbound_opcode: Optional[Opcode] = None

    def _process_close(self, frame: Frame) -> Frame:
        data = frame.payload
        assert isinstance(data, (bytes, bytearray))

        if not data:
            # "If this Close control frame contains no status code, _The
            # WebSocket Connection Close Code_ is considered to be 1005"
            data = (CloseReason.NO_STATUS_RCVD, "")
        elif len(data) == 1:
            raise ParseFailed("CLOSE with 1 byte payload")
        else:
            (code,) = struct.unpack("!H", data[:2])
            if code < MIN_CLOSE_REASON or code > MAX_CLOSE_REASON:
                raise ParseFailed("CLOSE with invalid code")
            try:
                code = CloseReason(code)
            except ValueError:
                pass
            if code in LOCAL_ONLY_CLOSE_REASONS:
                raise ParseFailed("remote CLOSE with local-only reason")
            if not isinstance(code, CloseReason) and code <= MAX_PROTOCOL_CLOSE_REASON:
                raise ParseFailed("CLOSE with unknown reserved code")
            try:
                reason = data[2:].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ParseFailed(
                    "Error decoding CLOSE reason: " + str(exc),
                    CloseReason.INVALID_FRAME_PAYLOAD_DATA,
                )
            data = (code, reason)

        return Frame(frame.opcode, data, frame.frame_finished, frame.message_finished)

    def _parse_more_gen(self) -> Generator[Optional[Frame], None, None]:
        # Consume as much as we can from self._buffer, yielding events, and
        # then yield None when we need more data. Or raise ParseFailed.

        # XX FIXME this should probably be refactored so that we never see
        # disabled extensions in the first place...
        self.extensions = [ext for ext in self.extensions if ext.enabled()]
        closed = False

        while not closed:
            frame = self._frame_decoder.process_buffer()

            if frame is not None:
                if not frame.opcode.iscontrol():
                    frame = self._message_decoder.process_frame(frame)
                elif frame.opcode == Opcode.CLOSE:
                    frame = self._process_close(frame)
                    closed = True

            yield frame

    def receive_bytes(self, data: bytes) -> None:
        self._frame_decoder.receive_bytes(data)

    def received_frames(self) -> Generator[Frame, None, None]:
        for event in self._parse_more:
            if event is None:
                break
            else:
                yield event

    def close(self, code: Optional[int] = None, reason: Optional[str] = None) -> bytes:
        payload = bytearray()
        if code is CloseReason.NO_STATUS_RCVD:
            code = None
        if code is None and reason:
            raise TypeError("cannot specify a reason without a code")
        if code in LOCAL_ONLY_CLOSE_REASONS:
            code = CloseReason.NORMAL_CLOSURE
        if code is not None:
            payload += bytearray(struct.pack("!H", code))
            if reason is not None:
                payload += _truncate_utf8(
                    reason.encode("utf-8"), MAX_PAYLOAD_NORMAL - 2
                )

        return self._serialize_frame(Opcode.CLOSE, payload)

    def ping(self, payload: bytes = b"") -> bytes:
        return self._serialize_frame(Opcode.PING, payload)

    def pong(self, payload: bytes = b"") -> bytes:
        return self._serialize_frame(Opcode.PONG, payload)

    def send_data(
        self, payload: Union[bytes, bytearray, str] = b"", fin: bool = True
    ) -> bytes:
        if isinstance(payload, (bytes, bytearray, memoryview)):
            opcode = Opcode.BINARY
        elif isinstance(payload, str):
            opcode = Opcode.TEXT
            payload = payload.encode("utf-8")
        else:
            raise ValueError("Must provide bytes or text")

        if self._outbound_opcode is None:
            self._outbound_opcode = opcode
        elif self._outbound_opcode is not opcode:
            raise TypeError("Data type mismatch inside message")
        else:
            opcode = Opcode.CONTINUATION

        if fin:
            self._outbound_opcode = None

        return self._serialize_frame(opcode, payload, fin)

    def _make_fin_rsv_opcode(self, fin: bool, rsv: RsvBits, opcode: Opcode) -> int:
        fin_bits = int(fin) << 7
        rsv_bits = (int(rsv.rsv1) << 6) + (int(rsv.rsv2) << 5) + (int(rsv.rsv3) << 4)
        opcode_bits = int(opcode)

        return fin_bits | rsv_bits | opcode_bits

    def _serialize_frame(
        self, opcode: Opcode, payload: bytes = b"", fin: bool = True
    ) -> bytes:
        rsv = RsvBits(False, False, False)
        for extension in reversed(self.extensions):
            rsv, payload = extension.frame_outbound(self, opcode, rsv, payload, fin)

        fin_rsv_opcode = self._make_fin_rsv_opcode(fin, rsv, opcode)

        payload_length = len(payload)
        quad_payload = False
        if payload_length <= MAX_PAYLOAD_NORMAL:
            first_payload = payload_length
            second_payload = None
        elif payload_length <= MAX_PAYLOAD_TWO_BYTE:
            first_payload = PAYLOAD_LENGTH_TWO_BYTE
            second_payload = payload_length
        else:
            first_payload = PAYLOAD_LENGTH_EIGHT_BYTE
            second_payload = payload_length
            quad_payload = True

        if self.client:
            first_payload |= 1 << 7

        header = bytearray([fin_rsv_opcode, first_payload])
        if second_payload is not None:
            if opcode.iscontrol():
                raise ValueError("payload too long for control frame")
            if quad_payload:
                header += bytearray(struct.pack("!Q", second_payload))
            else:
                header += bytearray(struct.pack("!H", second_payload))

        if self.client:
            # "The masking key is a 32-bit value chosen at random by the
            # client.  When preparing a masked frame, the client MUST pick a
            # fresh masking key from the set of allowed 32-bit values.  The
            # masking key needs to be unpredictable; thus, the masking key
            # MUST be derived from a strong source of entropy, and the masking
            # key for a given frame MUST NOT make it simple for a server/proxy
            # to predict the masking key for a subsequent frame.  The
            # unpredictability of the masking key is essential to prevent
            # authors of malicious applications from selecting the bytes that
            # appear on the wire."
            #   -- https://tools.ietf.org/html/rfc6455#section-5.3
            masking_key = os.urandom(4)
            masker = XorMaskerSimple(masking_key)
            return header + masking_key + masker.process(payload)

        return header + payload

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\token_counter.py ===
# What is this?
## Helper utilities for token counting
import base64
import io
import struct
from typing import Callable, List, Literal, Optional, Tuple, Union, cast

import tiktoken

import litellm
from litellm import verbose_logger
from litellm.constants import (
    DEFAULT_IMAGE_HEIGHT,
    DEFAULT_IMAGE_TOKEN_COUNT,
    DEFAULT_IMAGE_WIDTH,
    MAX_LONG_SIDE_FOR_IMAGE_HIGH_RES,
    MAX_SHORT_SIDE_FOR_IMAGE_HIGH_RES,
    MAX_TILE_HEIGHT,
    MAX_TILE_WIDTH,
)
from litellm.litellm_core_utils.default_encoding import encoding as default_encoding
from litellm.llms.custom_httpx.http_handler import _get_httpx_client
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionNamedToolChoiceParam,
    ChatCompletionToolParam,
    OpenAIMessageContent,
)
from litellm.types.utils import Message, SelectTokenizerResponse


def get_modified_max_tokens(
    model: str,
    base_model: str,
    messages: Optional[List[AllMessageValues]],
    user_max_tokens: Optional[int],
    buffer_perc: Optional[float],
    buffer_num: Optional[float],
) -> Optional[int]:
    """
    Params:

    Returns the user's max output tokens, adjusted for:
    - the size of input - for models where input + output can't exceed X
    - model max output tokens - for models where there is a separate output token limit
    """
    try:
        if user_max_tokens is None:
            return None

        ## MODEL INFO
        _model_info = litellm.get_model_info(model=model)

        max_output_tokens = litellm.get_max_tokens(
            model=base_model
        )  # assume min context window is 4k tokens

        ## UNKNOWN MAX OUTPUT TOKENS - return user defined amount
        if max_output_tokens is None:
            return user_max_tokens

        input_tokens = litellm.token_counter(model=base_model, messages=messages)

        # token buffer
        if buffer_perc is None:
            buffer_perc = 0.1
        if buffer_num is None:
            buffer_num = 10
        token_buffer = max(
            buffer_perc * input_tokens, buffer_num
        )  # give at least a 10 token buffer. token counting can be imprecise.

        input_tokens += int(token_buffer)
        verbose_logger.debug(
            f"max_output_tokens: {max_output_tokens}, user_max_tokens: {user_max_tokens}"
        )
        ## CASE 1: model input + output can't exceed X - happens when max input = max output, e.g. gpt-3.5-turbo
        if _model_info["max_input_tokens"] == max_output_tokens:
            verbose_logger.debug(
                f"input_tokens: {input_tokens}, max_output_tokens: {max_output_tokens}"
            )
            if input_tokens > max_output_tokens:
                pass  # allow call to fail normally - don't set max_tokens to negative.
            elif (
                user_max_tokens + input_tokens > max_output_tokens
            ):  # we can still modify to keep it positive but below the limit
                verbose_logger.debug(
                    f"MODIFYING MAX TOKENS - user_max_tokens={user_max_tokens}, input_tokens={input_tokens}, max_output_tokens={max_output_tokens}"
                )
                user_max_tokens = int(max_output_tokens - input_tokens)
        ## CASE 2: user_max_tokens> model max output tokens
        elif user_max_tokens > max_output_tokens:
            user_max_tokens = max_output_tokens

        verbose_logger.debug(
            f"litellm.litellm_core_utils.token_counter.py::get_modified_max_tokens() - user_max_tokens: {user_max_tokens}"
        )

        return user_max_tokens
    except Exception as e:
        verbose_logger.error(
            "litellm.litellm_core_utils.token_counter.py::get_modified_max_tokens() - Error while checking max token limit: {}\nmodel={}, base_model={}".format(
                str(e), model, base_model
            )
        )
        return user_max_tokens


def resize_image_high_res(
    width: int,
    height: int,
) -> Tuple[int, int]:
    # Maximum dimensions for high res mode
    max_short_side = MAX_SHORT_SIDE_FOR_IMAGE_HIGH_RES
    max_long_side = MAX_LONG_SIDE_FOR_IMAGE_HIGH_RES

    # Return early if no resizing is needed
    if (
        width <= MAX_SHORT_SIDE_FOR_IMAGE_HIGH_RES
        and height <= MAX_SHORT_SIDE_FOR_IMAGE_HIGH_RES
    ):
        return width, height

    # Determine the longer and shorter sides
    longer_side = max(width, height)
    shorter_side = min(width, height)

    # Calculate the aspect ratio
    aspect_ratio = longer_side / shorter_side

    # Resize based on the short side being 768px
    if width <= height:  # Portrait or square
        resized_width = max_short_side
        resized_height = int(resized_width * aspect_ratio)
        # if the long side exceeds the limit after resizing, adjust both sides accordingly
        if resized_height > max_long_side:
            resized_height = max_long_side
            resized_width = int(resized_height / aspect_ratio)
    else:  # Landscape
        resized_height = max_short_side
        resized_width = int(resized_height * aspect_ratio)
        # if the long side exceeds the limit after resizing, adjust both sides accordingly
        if resized_width > max_long_side:
            resized_width = max_long_side
            resized_height = int(resized_width / aspect_ratio)

    return resized_width, resized_height


# Test the function with the given example
def calculate_tiles_needed(
    resized_width,
    resized_height,
    tile_width=MAX_TILE_WIDTH,
    tile_height=MAX_TILE_HEIGHT,
):
    tiles_across = (resized_width + tile_width - 1) // tile_width
    tiles_down = (resized_height + tile_height - 1) // tile_height
    total_tiles = tiles_across * tiles_down
    return total_tiles


def get_image_type(image_data: bytes) -> Union[str, None]:
    """take an image (really only the first ~100 bytes max are needed)
    and return 'png' 'gif' 'jpeg' 'webp' 'heic' or None. method added to
    allow deprecation of imghdr in 3.13"""

    if image_data[0:8] == b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a":
        return "png"

    if image_data[0:4] == b"GIF8" and image_data[5:6] == b"a":
        return "gif"

    if image_data[0:3] == b"\xff\xd8\xff":
        return "jpeg"

    if image_data[4:8] == b"ftyp":
        return "heic"

    if image_data[0:4] == b"RIFF" and image_data[8:12] == b"WEBP":
        return "webp"

    return None


def get_image_dimensions(
    data: str,
) -> Tuple[int, int]:
    """
    Async Function to get the dimensions of an image from a URL or base64 encoded string.

    Args:
        data (str): The URL or base64 encoded string of the image.

    Returns:
        Tuple[int, int]: The width and height of the image.
    """
    img_data = None
    try:
        # Try to open as URL
        client = _get_httpx_client()
        response = client.get(data)
        img_data = response.read()
    except Exception:
        # If not URL, assume it's base64
        _header, encoded = data.split(",", 1)
        img_data = base64.b64decode(encoded)

    img_type = get_image_type(img_data)

    if img_type == "png":
        w, h = struct.unpack(">LL", img_data[16:24])
        return w, h
    elif img_type == "gif":
        w, h = struct.unpack("<HH", img_data[6:10])
        return w, h
    elif img_type == "jpeg":
        with io.BytesIO(img_data) as fhandle:
            fhandle.seek(0)
            size = 2
            ftype = 0
            while not 0xC0 <= ftype <= 0xCF or ftype in (0xC4, 0xC8, 0xCC):
                fhandle.seek(size, 1)
                byte = fhandle.read(1)
                while ord(byte) == 0xFF:
                    byte = fhandle.read(1)
                ftype = ord(byte)
                size = struct.unpack(">H", fhandle.read(2))[0] - 2
            fhandle.seek(1, 1)
            h, w = struct.unpack(">HH", fhandle.read(4))
        return w, h
    elif img_type == "webp":
        # For WebP, the dimensions are stored at different offsets depending on the format
        # Check for VP8X (extended format)
        if img_data[12:16] == b"VP8X":
            w = struct.unpack("<I", img_data[24:27] + b"\x00")[0] + 1
            h = struct.unpack("<I", img_data[27:30] + b"\x00")[0] + 1
            return w, h
        # Check for VP8 (lossy format)
        elif img_data[12:16] == b"VP8 ":
            w = struct.unpack("<H", img_data[26:28])[0] & 0x3FFF
            h = struct.unpack("<H", img_data[28:30])[0] & 0x3FFF
            return w, h
        # Check for VP8L (lossless format)
        elif img_data[12:16] == b"VP8L":
            bits = struct.unpack("<I", img_data[21:25])[0]
            w = (bits & 0x3FFF) + 1
            h = ((bits >> 14) & 0x3FFF) + 1
            return w, h

    # return sensible default image dimensions if unable to get dimensions
    return DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT


def calculate_img_tokens(
    data,
    mode: Literal["low", "high", "auto"] = "auto",
    base_tokens: int = 85,  # openai default - https://openai.com/pricing
    use_default_image_token_count: bool = False,
):
    """
    Calculate the number of tokens for an image.

    Args:
        data (str): The URL or base64 encoded string of the image.
        mode (Literal["low", "high", "auto"]): The mode to use for calculating the number of tokens.
        base_tokens (int): The base number of tokens for an image.
        use_default_image_token_count (bool): When True, will NOT make a GET request to the image URL and instead return the default image dimensions.

    Returns:
        int: The number of tokens for the image.
    """
    if use_default_image_token_count:
        verbose_logger.debug(
            "Using default image token count: {}".format(DEFAULT_IMAGE_TOKEN_COUNT)
        )
        return DEFAULT_IMAGE_TOKEN_COUNT
    if mode == "low" or mode == "auto":
        return base_tokens
    elif mode == "high":
        # Run the async function using the helper
        width, height = get_image_dimensions(
            data=data,
        )
        resized_width, resized_height = resize_image_high_res(
            width=width, height=height
        )
        tiles_needed_high_res = calculate_tiles_needed(
            resized_width=resized_width, resized_height=resized_height
        )
        tile_tokens = (base_tokens * 2) * tiles_needed_high_res
        total_tokens = base_tokens + tile_tokens
        return total_tokens


TokenCounterFunction = Callable[[str], int]
"""
Type for a function that counts tokens in a string.
"""


class _MessageCountParams:
    """
    A class to hold the parameters for counting tokens in messages.
    """

    def __init__(
        self,
        model: str,
        custom_tokenizer: Optional[Union[dict, SelectTokenizerResponse]],
    ):
        from litellm.utils import print_verbose

        actual_model = _fix_model_name(model)
        if actual_model == "gpt-3.5-turbo-0301":
            self.tokens_per_message = (
                4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
            )
            self.tokens_per_name = -1  # if there's a name, the role is omitted
        elif actual_model in litellm.open_ai_chat_completion_models:
            self.tokens_per_message = 3
            self.tokens_per_name = 1
        elif actual_model in litellm.azure_llms:
            self.tokens_per_message = 3
            self.tokens_per_name = 1
        else:
            print_verbose(
                f"Warning: unknown model {model}. Using default token params."
            )
            self.tokens_per_message = 3
            self.tokens_per_name = 1
        self.count_function = _get_count_function(model, custom_tokenizer)


def token_counter(
    model="",
    custom_tokenizer: Optional[Union[dict, SelectTokenizerResponse]] = None,
    text: Optional[Union[str, List[str]]] = None,
    messages: Optional[List[Union[AllMessageValues, Message]]] = None,
    count_response_tokens: Optional[bool] = False,
    tools: Optional[List[ChatCompletionToolParam]] = None,
    tool_choice: Optional[ChatCompletionNamedToolChoiceParam] = None,
    use_default_image_token_count: Optional[bool] = False,
    default_token_count: Optional[int] = None,
) -> int:
    """
    Count the number of tokens in a given text using a specified model.

    Args:
    model (str): The name of the model to use for tokenization. Default is an empty string.
    custom_tokenizer (Optional[dict]): A custom tokenizer created with the `create_pretrained_tokenizer` or `create_tokenizer` method. Must be a dictionary with a string value for `type` and Tokenizer for `tokenizer`. Default is None.
    text (str): The raw text string to be passed to the model. Default is None.
    messages (Optional[List[AllMessageValues]]): Alternative to passing in text. A list of dictionaries representing messages with "role" and "content" keys. Default is None.
    count_response_tokens (Optional[bool]): set to True to indicate we are processing a stream response.
    tools (Optional[List[ChatCompletionToolParam]]): The available tools. Default is None.
    tool_choice (Optional[ChatCompletionNamedToolChoiceParam]): The tool choice. Default is None.
    use_default_image_token_count (Optional[bool]): When True, will NOT make a GET request to the image URL and instead return the default image dimensions. Default is False.
    default_token_count (Optional[int]): The default number of tokens to return for a message block, if an error occurs. Default is None.

    Returns:
    int: The number of tokens in the text.
    """
    from litellm.utils import convert_list_message_to_dict

    #########################################################
    # Flag to disable token counter
    # We've gotten reports of this consuming CPU cycles,
    # exposing this flag to allow users to disable
    # it to confirm if this is indeed the issue
    #########################################################
    if litellm.disable_token_counter is True:
        return 0

    verbose_logger.debug(
        f"messages in token_counter: {messages}, text in token_counter: {text}"
    )
    if text is not None and messages is not None:
        raise ValueError("text and messages cannot both be set")
    if use_default_image_token_count is None:
        use_default_image_token_count = False

    if text is not None:
        if tools or tool_choice:
            raise ValueError("tools or tool_choice cannot be set if using text")
        if isinstance(text, List):
            text_to_count = "".join(t for t in text if isinstance(t, str))
        elif isinstance(text, str):
            text_to_count = text
        count_function = _get_count_function(model, custom_tokenizer)
        num_tokens = count_function(text_to_count)

    elif messages is not None:
        new_messages = cast(
            List[AllMessageValues], convert_list_message_to_dict(messages)
        )
        params = _MessageCountParams(model, custom_tokenizer)
        num_tokens = _count_messages(
            params, new_messages, use_default_image_token_count, default_token_count
        )
        if count_response_tokens is False:
            includes_system_message = any(
                [message.get("role", None) == "system" for message in new_messages]
            )
            num_tokens += _count_extra(
                params.count_function, tools, tool_choice, includes_system_message
            )

    else:
        raise ValueError("Either text or messages must be provided")

    return num_tokens


def _count_messages(
    params: _MessageCountParams,
    messages: List[AllMessageValues],
    use_default_image_token_count: bool,
    default_token_count: Optional[int],
) -> int:
    """
    Count the number of tokens in a list of messages.

    Args:
        params (_MessageCountParams): The parameters for counting tokens.
        messages (List[AllMessageValues]): The list of messages to count tokens in.
        use_default_image_token_count (bool): When True, will NOT make a GET request to the image URL and instead return the default image dimensions.
        default_token_count (Optional[int]): The default number of tokens to return for a message block, if an error occurs.
    """
    num_tokens = 0
    if len(messages) == 0:
        return num_tokens
    for message in messages:
        num_tokens += params.tokens_per_message
        for key, value in message.items():
            if value is None:
                pass
            elif key == "tool_calls":
                if isinstance(value, List):
                    for tool_call in value:
                        if "function" in tool_call:
                            function_arguments = tool_call["function"].get(
                                "arguments", []
                            )
                            num_tokens += params.count_function(str(function_arguments))
                        else:
                            raise ValueError(
                                f"Unsupported tool call {tool_call} must contain a function key"
                            )
                else:
                    raise ValueError(
                        f"Unsupported type {type(value)} for key tool_calls in message {message}"
                    )
            elif isinstance(value, str):
                num_tokens += params.count_function(value)
                if key == "name":
                    num_tokens += params.tokens_per_name
            elif key == "content" and isinstance(value, List):
                num_tokens += _count_content_list(
                    params.count_function,
                    value,
                    use_default_image_token_count,
                    default_token_count,
                )
            else:
                raise ValueError(
                    f"Unsupported type {type(value)} for key {key} in message {message}"
                )
    return num_tokens


def _count_extra(
    count_function: TokenCounterFunction,
    tools: Optional[List[ChatCompletionToolParam]],
    tool_choice: Optional[ChatCompletionNamedToolChoiceParam],
    includes_system_message: bool,
) -> int:
    """Count extra tokens for function definitions and tool choices.
    Args:
        count_function (TokenCounterFunction): The function to count tokens.
        tools (Optional[List[ChatCompletionToolParam]]): The available tools.
        tool_choice (Optional[ChatCompletionNamedToolChoiceParam]): The tool choice.
        includes_system_message (bool): Whether the messages include a system message.
    """

    num_tokens = 3  # every reply is primed with <|start|>assistant<|message|>

    if tools:
        num_tokens += count_function(_format_function_definitions(tools))
        num_tokens += 9  # Additional tokens for function definition of tools
    # If there's a system message and tools are present, subtract four tokens
    if tools and includes_system_message:
        num_tokens -= 4
    # If tool_choice is 'none', add one token.
    # If it's an object, add 4 + the number of tokens in the function name.
    # If it's undefined or 'auto', don't add anything.
    if tool_choice == "none":
        num_tokens += 1
    elif isinstance(tool_choice, dict):
        num_tokens += 7
        num_tokens += count_function(str(tool_choice["function"]["name"]))

    return num_tokens


def _get_count_function(
    model: Optional[str],
    custom_tokenizer: Optional[Union[dict, SelectTokenizerResponse]] = None,
) -> TokenCounterFunction:
    """
    Get the function to count tokens based on the model and custom tokenizer."""
    from litellm.utils import _select_tokenizer, print_verbose

    if model is not None or custom_tokenizer is not None:
        tokenizer_json = custom_tokenizer or _select_tokenizer(model)  # type: ignore
        if tokenizer_json["type"] == "huggingface_tokenizer":

            def count_tokens(text: str) -> int:
                enc = tokenizer_json["tokenizer"].encode(text)
                return len(enc.ids)

        elif tokenizer_json["type"] == "openai_tokenizer":
            model_to_use = _fix_model_name(model)  # type: ignore
            try:
                if "gpt-4o" in model_to_use:
                    encoding = tiktoken.get_encoding("o200k_base")
                else:
                    encoding = tiktoken.encoding_for_model(model_to_use)
            except KeyError:
                print_verbose("Warning: model not found. Using cl100k_base encoding.")
                encoding = tiktoken.get_encoding("cl100k_base")

            def count_tokens(text: str) -> int:
                return len(encoding.encode(text))

        else:
            raise ValueError("Unsupported tokenizer type")
    else:

        def count_tokens(text: str) -> int:
            return len(default_encoding.encode(text, disallowed_special=()))

    return count_tokens


def _fix_model_name(model: str) -> str:
    """We normalize some model names to others"""
    if model in litellm.azure_llms:
        # azure llms use gpt-35-turbo instead of gpt-3.5-turbo 🙃
        return model.replace("-35", "-3.5")
    elif model in litellm.open_ai_chat_completion_models:
        return model  # type: ignore
    else:
        return "gpt-3.5-turbo"


def _count_content_list(
    count_function: TokenCounterFunction,
    content_list: OpenAIMessageContent,
    use_default_image_token_count: bool,
    default_token_count: Optional[int],
) -> int:
    """
    Get the number of tokens from a list of content.
    """
    try:
        num_tokens = 0
        for c in content_list:
            if isinstance(c, str):
                num_tokens += count_function(c)
            elif c["type"] == "text":
                num_tokens += count_function(c["text"])
            elif c["type"] == "image_url":
                if isinstance(c["image_url"], dict):
                    image_url_dict = c["image_url"]
                    detail = image_url_dict.get("detail", "auto")
                    if detail not in ["low", "high", "auto"]:
                        raise ValueError(
                            f"Invalid detail value: {detail}. Expected 'low', 'high', or 'auto'."
                        )
                    url = image_url_dict.get("url")
                    num_tokens += calculate_img_tokens(
                        data=url,
                        mode=detail,  # type: ignore
                        use_default_image_token_count=use_default_image_token_count,
                    )
                elif isinstance(c["image_url"], str):
                    image_url_str = c["image_url"]
                    num_tokens += calculate_img_tokens(
                        data=image_url_str,
                        mode="auto",
                        use_default_image_token_count=use_default_image_token_count,
                    )
                else:
                    raise ValueError(
                        f"Invalid image_url type: {type(c['image_url'])}. Expected str or dict."
                    )
            else:
                raise ValueError(
                    f"Invalid content type: {type(c)}. Expected str or dict."
                )
        return num_tokens
    except Exception as e:
        if default_token_count is not None:
            return default_token_count
        raise ValueError(
            f"Error getting number of tokens from content list: {e}, default_token_count={default_token_count}"
        )


def _format_function_definitions(tools):
    """Formats tool definitions in the format that OpenAI appears to use.
    Based on https://github.com/forestwanglin/openai-java/blob/main/jtokkit/src/main/java/xyz/felh/openai/jtokkit/utils/TikTokenUtils.java
    """
    lines = []
    lines.append("namespace functions {")
    lines.append("")
    for tool in tools:
        function = tool.get("function")
        if function_description := function.get("description"):
            lines.append(f"// {function_description}")
        function_name = function.get("name")
        parameters = function.get("parameters", {})
        properties = parameters.get("properties")
        if properties and properties.keys():
            lines.append(f"type {function_name} = (_: {{")
            lines.append(_format_object_parameters(parameters, 0))
            lines.append("}) => any;")
        else:
            lines.append(f"type {function_name} = () => any;")
        lines.append("")
    lines.append("} // namespace functions")
    return "\n".join(lines)


def _format_object_parameters(parameters, indent):
    properties = parameters.get("properties")
    if not properties:
        return ""
    required_params = parameters.get("required", [])
    lines = []
    for key, props in properties.items():
        description = props.get("description")
        if description:
            lines.append(f"// {description}")
        question = "?"
        if required_params and key in required_params:
            question = ""
        lines.append(f"{key}{question}: {_format_type(props, indent)},")
    return "\n".join([" " * max(0, indent) + line for line in lines])


def _format_type(props, indent):
    type = props.get("type")
    if type == "string":
        if "enum" in props:
            return " | ".join([f'"{item}"' for item in props["enum"]])
        return "string"
    elif type == "array":
        # items is required, OpenAI throws an error if it's missing
        return f"{_format_type(props['items'], indent)}[]"
    elif type == "object":
        return f"{{\n{_format_object_parameters(props, indent + 2)}\n}}"
    elif type in ["integer", "number"]:
        if "enum" in props:
            return " | ".join([f'"{item}"' for item in props["enum"]])
        return "number"
    elif type == "boolean":
        return "boolean"
    elif type == "null":
        return "null"
    else:
        # This is a guess, as an empty string doesn't yield the expected token count
        return "any"

# === NexusCore/openenv\Lib\site-packages\openai\lib\streaming\chat\_types.py ===
from __future__ import annotations

from typing_extensions import TypeAlias

from ....types.chat import ParsedChoice, ParsedChatCompletion, ParsedChatCompletionMessage

ParsedChatCompletionSnapshot: TypeAlias = ParsedChatCompletion[object]
"""Snapshot type representing an in-progress accumulation of
a `ParsedChatCompletion` object.
"""

ParsedChatCompletionMessageSnapshot: TypeAlias = ParsedChatCompletionMessage[object]
"""Snapshot type representing an in-progress accumulation of
a `ParsedChatCompletionMessage` object.

If the content has been fully accumulated, the `.parsed` content will be
the `response_format` instance, otherwise it'll be the raw JSON parsed version.
"""

ParsedChoiceSnapshot: TypeAlias = ParsedChoice[object]

# === NexusCore/openenv\Lib\site-packages\tornado\netutil.py ===
#
# Copyright 2011 Facebook
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

"""Miscellaneous network utility code."""

import asyncio
import concurrent.futures
import errno
import os
import sys
import socket
import ssl
import stat

from tornado.concurrent import dummy_executor, run_on_executor
from tornado.ioloop import IOLoop
from tornado.util import Configurable, errno_from_exception

from typing import List, Callable, Any, Type, Dict, Union, Tuple, Awaitable, Optional

# Note that the naming of ssl.Purpose is confusing; the purpose
# of a context is to authenticate the opposite side of the connection.
_client_ssl_defaults = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
_server_ssl_defaults = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
if hasattr(ssl, "OP_NO_COMPRESSION"):
    # See netutil.ssl_options_to_context
    _client_ssl_defaults.options |= ssl.OP_NO_COMPRESSION
    _server_ssl_defaults.options |= ssl.OP_NO_COMPRESSION

# ThreadedResolver runs getaddrinfo on a thread. If the hostname is unicode,
# getaddrinfo attempts to import encodings.idna. If this is done at
# module-import time, the import lock is already held by the main thread,
# leading to deadlock. Avoid it by caching the idna encoder on the main
# thread now.
"foo".encode("idna")

# For undiagnosed reasons, 'latin1' codec may also need to be preloaded.
"foo".encode("latin1")

# Default backlog used when calling sock.listen()
_DEFAULT_BACKLOG = 128


def bind_sockets(
    port: int,
    address: Optional[str] = None,
    family: socket.AddressFamily = socket.AF_UNSPEC,
    backlog: int = _DEFAULT_BACKLOG,
    flags: Optional[int] = None,
    reuse_port: bool = False,
) -> List[socket.socket]:
    """Creates listening sockets bound to the given port and address.

    Returns a list of socket objects (multiple sockets are returned if
    the given address maps to multiple IP addresses, which is most common
    for mixed IPv4 and IPv6 use).

    Address may be either an IP address or hostname.  If it's a hostname,
    the server will listen on all IP addresses associated with the
    name.  Address may be an empty string or None to listen on all
    available interfaces.  Family may be set to either `socket.AF_INET`
    or `socket.AF_INET6` to restrict to IPv4 or IPv6 addresses, otherwise
    both will be used if available.

    The ``backlog`` argument has the same meaning as for
    `socket.listen() <socket.socket.listen>`.

    ``flags`` is a bitmask of AI_* flags to `~socket.getaddrinfo`, like
    ``socket.AI_PASSIVE | socket.AI_NUMERICHOST``.

    ``reuse_port`` option sets ``SO_REUSEPORT`` option for every socket
    in the list. If your platform doesn't support this option ValueError will
    be raised.
    """
    if reuse_port and not hasattr(socket, "SO_REUSEPORT"):
        raise ValueError("the platform doesn't support SO_REUSEPORT")

    sockets = []
    if address == "":
        address = None
    if not socket.has_ipv6 and family == socket.AF_UNSPEC:
        # Python can be compiled with --disable-ipv6, which causes
        # operations on AF_INET6 sockets to fail, but does not
        # automatically exclude those results from getaddrinfo
        # results.
        # http://bugs.python.org/issue16208
        family = socket.AF_INET
    if flags is None:
        flags = socket.AI_PASSIVE
    bound_port = None
    unique_addresses = set()  # type: set
    for res in sorted(
        socket.getaddrinfo(address, port, family, socket.SOCK_STREAM, 0, flags),
        key=lambda x: x[0],
    ):
        if res in unique_addresses:
            continue

        unique_addresses.add(res)

        af, socktype, proto, canonname, sockaddr = res
        if (
            sys.platform == "darwin"
            and address == "localhost"
            and af == socket.AF_INET6
            and sockaddr[3] != 0  # type: ignore
        ):
            # Mac OS X includes a link-local address fe80::1%lo0 in the
            # getaddrinfo results for 'localhost'.  However, the firewall
            # doesn't understand that this is a local address and will
            # prompt for access (often repeatedly, due to an apparent
            # bug in its ability to remember granting access to an
            # application). Skip these addresses.
            continue
        try:
            sock = socket.socket(af, socktype, proto)
        except OSError as e:
            if errno_from_exception(e) == errno.EAFNOSUPPORT:
                continue
            raise
        if os.name != "nt":
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except OSError as e:
                if errno_from_exception(e) != errno.ENOPROTOOPT:
                    # Hurd doesn't support SO_REUSEADDR.
                    raise
        if reuse_port:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        if af == socket.AF_INET6:
            # On linux, ipv6 sockets accept ipv4 too by default,
            # but this makes it impossible to bind to both
            # 0.0.0.0 in ipv4 and :: in ipv6.  On other systems,
            # separate sockets *must* be used to listen for both ipv4
            # and ipv6.  For consistency, always disable ipv4 on our
            # ipv6 sockets and use a separate ipv4 socket when needed.
            #
            # Python 2.x on windows doesn't have IPPROTO_IPV6.
            if hasattr(socket, "IPPROTO_IPV6"):
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)

        # automatic port allocation with port=None
        # should bind on the same port on IPv4 and IPv6
        host, requested_port = sockaddr[:2]
        if requested_port == 0 and bound_port is not None:
            sockaddr = tuple([host, bound_port] + list(sockaddr[2:]))

        sock.setblocking(False)
        try:
            sock.bind(sockaddr)
        except OSError as e:
            if (
                errno_from_exception(e) == errno.EADDRNOTAVAIL
                and address == "localhost"
                and sockaddr[0] == "::1"
            ):
                # On some systems (most notably docker with default
                # configurations), ipv6 is partially disabled:
                # socket.has_ipv6 is true, we can create AF_INET6
                # sockets, and getaddrinfo("localhost", ...,
                # AF_PASSIVE) resolves to ::1, but we get an error
                # when binding.
                #
                # Swallow the error, but only for this specific case.
                # If EADDRNOTAVAIL occurs in other situations, it
                # might be a real problem like a typo in a
                # configuration.
                sock.close()
                continue
            else:
                raise
        bound_port = sock.getsockname()[1]
        sock.listen(backlog)
        sockets.append(sock)
    return sockets


if hasattr(socket, "AF_UNIX"):

    def bind_unix_socket(
        file: str, mode: int = 0o600, backlog: int = _DEFAULT_BACKLOG
    ) -> socket.socket:
        """Creates a listening unix socket.

        If a socket with the given name already exists, it will be deleted.
        If any other file with that name exists, an exception will be
        raised.

        Returns a socket object (not a list of socket objects like
        `bind_sockets`)
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except OSError as e:
            if errno_from_exception(e) != errno.ENOPROTOOPT:
                # Hurd doesn't support SO_REUSEADDR
                raise
        sock.setblocking(False)
        # File names comprising of an initial null-byte denote an abstract
        # namespace, on Linux, and therefore are not subject to file system
        # orientated processing.
        if not file.startswith("\0"):
            try:
                st = os.stat(file)
            except FileNotFoundError:
                pass
            else:
                if stat.S_ISSOCK(st.st_mode):
                    os.remove(file)
                else:
                    raise ValueError("File %s exists and is not a socket", file)
            sock.bind(file)
            os.chmod(file, mode)
        else:
            sock.bind(file)
        sock.listen(backlog)
        return sock


def add_accept_handler(
    sock: socket.socket, callback: Callable[[socket.socket, Any], None]
) -> Callable[[], None]:
    """Adds an `.IOLoop` event handler to accept new connections on ``sock``.

    When a connection is accepted, ``callback(connection, address)`` will
    be run (``connection`` is a socket object, and ``address`` is the
    address of the other end of the connection).  Note that this signature
    is different from the ``callback(fd, events)`` signature used for
    `.IOLoop` handlers.

    A callable is returned which, when called, will remove the `.IOLoop`
    event handler and stop processing further incoming connections.

    .. versionchanged:: 5.0
       The ``io_loop`` argument (deprecated since version 4.1) has been removed.

    .. versionchanged:: 5.0
       A callable is returned (``None`` was returned before).
    """
    io_loop = IOLoop.current()
    removed = [False]

    def accept_handler(fd: socket.socket, events: int) -> None:
        # More connections may come in while we're handling callbacks;
        # to prevent starvation of other tasks we must limit the number
        # of connections we accept at a time.  Ideally we would accept
        # up to the number of connections that were waiting when we
        # entered this method, but this information is not available
        # (and rearranging this method to call accept() as many times
        # as possible before running any callbacks would have adverse
        # effects on load balancing in multiprocess configurations).
        # Instead, we use the (default) listen backlog as a rough
        # heuristic for the number of connections we can reasonably
        # accept at once.
        for i in range(_DEFAULT_BACKLOG):
            if removed[0]:
                # The socket was probably closed
                return
            try:
                connection, address = sock.accept()
            except BlockingIOError:
                # EWOULDBLOCK indicates we have accepted every
                # connection that is available.
                return
            except ConnectionAbortedError:
                # ECONNABORTED indicates that there was a connection
                # but it was closed while still in the accept queue.
                # (observed on FreeBSD).
                continue
            callback(connection, address)

    def remove_handler() -> None:
        io_loop.remove_handler(sock)
        removed[0] = True

    io_loop.add_handler(sock, accept_handler, IOLoop.READ)
    return remove_handler


def is_valid_ip(ip: str) -> bool:
    """Returns ``True`` if the given string is a well-formed IP address.

    Supports IPv4 and IPv6.
    """
    if not ip or "\x00" in ip:
        # getaddrinfo resolves empty strings to localhost, and truncates
        # on zero bytes.
        return False
    try:
        res = socket.getaddrinfo(
            ip, 0, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_NUMERICHOST
        )
        return bool(res)
    except socket.gaierror as e:
        if e.args[0] == socket.EAI_NONAME:
            return False
        raise
    except UnicodeError:
        # `socket.getaddrinfo` will raise a UnicodeError from the
        # `idna` decoder if the input is longer than 63 characters,
        # even for socket.AI_NUMERICHOST.  See
        # https://bugs.python.org/issue32958 for discussion
        return False
    return True


class Resolver(Configurable):
    """Configurable asynchronous DNS resolver interface.

    By default, a blocking implementation is used (which simply calls
    `socket.getaddrinfo`).  An alternative implementation can be
    chosen with the `Resolver.configure <.Configurable.configure>`
    class method::

        Resolver.configure('tornado.netutil.ThreadedResolver')

    The implementations of this interface included with Tornado are

    * `tornado.netutil.DefaultLoopResolver`
    * `tornado.netutil.DefaultExecutorResolver` (deprecated)
    * `tornado.netutil.BlockingResolver` (deprecated)
    * `tornado.netutil.ThreadedResolver` (deprecated)
    * `tornado.netutil.OverrideResolver`
    * `tornado.platform.caresresolver.CaresResolver` (deprecated)

    .. versionchanged:: 5.0
       The default implementation has changed from `BlockingResolver` to
       `DefaultExecutorResolver`.

    .. versionchanged:: 6.2
       The default implementation has changed from `DefaultExecutorResolver` to
       `DefaultLoopResolver`.
    """

    @classmethod
    def configurable_base(cls) -> Type["Resolver"]:
        return Resolver

    @classmethod
    def configurable_default(cls) -> Type["Resolver"]:
        return DefaultLoopResolver

    def resolve(
        self, host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
    ) -> Awaitable[List[Tuple[int, Any]]]:
        """Resolves an address.

        The ``host`` argument is a string which may be a hostname or a
        literal IP address.

        Returns a `.Future` whose result is a list of (family,
        address) pairs, where address is a tuple suitable to pass to
        `socket.connect <socket.socket.connect>` (i.e. a ``(host,
        port)`` pair for IPv4; additional fields may be present for
        IPv6). If a ``callback`` is passed, it will be run with the
        result as an argument when it is complete.

        :raises IOError: if the address cannot be resolved.

        .. versionchanged:: 4.4
           Standardized all implementations to raise `IOError`.

        .. versionchanged:: 6.0 The ``callback`` argument was removed.
           Use the returned awaitable object instead.

        """
        raise NotImplementedError()

    def close(self) -> None:
        """Closes the `Resolver`, freeing any resources used.

        .. versionadded:: 3.1

        """
        pass


def _resolve_addr(
    host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
) -> List[Tuple[int, Any]]:
    # On Solaris, getaddrinfo fails if the given port is not found
    # in /etc/services and no socket type is given, so we must pass
    # one here.  The socket type used here doesn't seem to actually
    # matter (we discard the one we get back in the results),
    # so the addresses we return should still be usable with SOCK_DGRAM.
    addrinfo = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)
    results = []
    for fam, socktype, proto, canonname, address in addrinfo:
        results.append((fam, address))
    return results  # type: ignore


class DefaultExecutorResolver(Resolver):
    """Resolver implementation using `.IOLoop.run_in_executor`.

    .. versionadded:: 5.0

    .. deprecated:: 6.2

       Use `DefaultLoopResolver` instead.
    """

    async def resolve(
        self, host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
    ) -> List[Tuple[int, Any]]:
        result = await IOLoop.current().run_in_executor(
            None, _resolve_addr, host, port, family
        )
        return result


class DefaultLoopResolver(Resolver):
    """Resolver implementation using `asyncio.loop.getaddrinfo`."""

    async def resolve(
        self, host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
    ) -> List[Tuple[int, Any]]:
        # On Solaris, getaddrinfo fails if the given port is not found
        # in /etc/services and no socket type is given, so we must pass
        # one here.  The socket type used here doesn't seem to actually
        # matter (we discard the one we get back in the results),
        # so the addresses we return should still be usable with SOCK_DGRAM.
        return [
            (fam, address)
            for fam, _, _, _, address in await asyncio.get_running_loop().getaddrinfo(
                host, port, family=family, type=socket.SOCK_STREAM
            )
        ]


class ExecutorResolver(Resolver):
    """Resolver implementation using a `concurrent.futures.Executor`.

    Use this instead of `ThreadedResolver` when you require additional
    control over the executor being used.

    The executor will be shut down when the resolver is closed unless
    ``close_resolver=False``; use this if you want to reuse the same
    executor elsewhere.

    .. versionchanged:: 5.0
       The ``io_loop`` argument (deprecated since version 4.1) has been removed.

    .. deprecated:: 5.0
       The default `Resolver` now uses `asyncio.loop.getaddrinfo`;
       use that instead of this class.
    """

    def initialize(
        self,
        executor: Optional[concurrent.futures.Executor] = None,
        close_executor: bool = True,
    ) -> None:
        if executor is not None:
            self.executor = executor
            self.close_executor = close_executor
        else:
            self.executor = dummy_executor
            self.close_executor = False

    def close(self) -> None:
        if self.close_executor:
            self.executor.shutdown()
        self.executor = None  # type: ignore

    @run_on_executor
    def resolve(
        self, host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
    ) -> List[Tuple[int, Any]]:
        return _resolve_addr(host, port, family)


class BlockingResolver(ExecutorResolver):
    """Default `Resolver` implementation, using `socket.getaddrinfo`.

    The `.IOLoop` will be blocked during the resolution, although the
    callback will not be run until the next `.IOLoop` iteration.

    .. deprecated:: 5.0
       The default `Resolver` now uses `.IOLoop.run_in_executor`; use that instead
       of this class.
    """

    def initialize(self) -> None:  # type: ignore
        super().initialize()


class ThreadedResolver(ExecutorResolver):
    """Multithreaded non-blocking `Resolver` implementation.

    The thread pool size can be configured with::

        Resolver.configure('tornado.netutil.ThreadedResolver',
                           num_threads=10)

    .. versionchanged:: 3.1
       All ``ThreadedResolvers`` share a single thread pool, whose
       size is set by the first one to be created.

    .. deprecated:: 5.0
       The default `Resolver` now uses `.IOLoop.run_in_executor`; use that instead
       of this class.
    """

    _threadpool = None  # type: ignore
    _threadpool_pid = None  # type: int

    def initialize(self, num_threads: int = 10) -> None:  # type: ignore
        threadpool = ThreadedResolver._create_threadpool(num_threads)
        super().initialize(executor=threadpool, close_executor=False)

    @classmethod
    def _create_threadpool(
        cls, num_threads: int
    ) -> concurrent.futures.ThreadPoolExecutor:
        pid = os.getpid()
        if cls._threadpool_pid != pid:
            # Threads cannot survive after a fork, so if our pid isn't what it
            # was when we created the pool then delete it.
            cls._threadpool = None
        if cls._threadpool is None:
            cls._threadpool = concurrent.futures.ThreadPoolExecutor(num_threads)
            cls._threadpool_pid = pid
        return cls._threadpool


class OverrideResolver(Resolver):
    """Wraps a resolver with a mapping of overrides.

    This can be used to make local DNS changes (e.g. for testing)
    without modifying system-wide settings.

    The mapping can be in three formats::

        {
            # Hostname to host or ip
            "example.com": "127.0.1.1",

            # Host+port to host+port
            ("login.example.com", 443): ("localhost", 1443),

            # Host+port+address family to host+port
            ("login.example.com", 443, socket.AF_INET6): ("::1", 1443),
        }

    .. versionchanged:: 5.0
       Added support for host-port-family triplets.
    """

    def initialize(self, resolver: Resolver, mapping: dict) -> None:
        self.resolver = resolver
        self.mapping = mapping

    def close(self) -> None:
        self.resolver.close()

    def resolve(
        self, host: str, port: int, family: socket.AddressFamily = socket.AF_UNSPEC
    ) -> Awaitable[List[Tuple[int, Any]]]:
        if (host, port, family) in self.mapping:
            host, port = self.mapping[(host, port, family)]
        elif (host, port) in self.mapping:
            host, port = self.mapping[(host, port)]
        elif host in self.mapping:
            host = self.mapping[host]
        return self.resolver.resolve(host, port, family)


# These are the keyword arguments to ssl.wrap_socket that must be translated
# to their SSLContext equivalents (the other arguments are still passed
# to SSLContext.wrap_socket).
_SSL_CONTEXT_KEYWORDS = frozenset(
    ["ssl_version", "certfile", "keyfile", "cert_reqs", "ca_certs", "ciphers"]
)


def ssl_options_to_context(
    ssl_options: Union[Dict[str, Any], ssl.SSLContext],
    server_side: Optional[bool] = None,
) -> ssl.SSLContext:
    """Try to convert an ``ssl_options`` dictionary to an
    `~ssl.SSLContext` object.

    The ``ssl_options`` argument may be either an `ssl.SSLContext` object or a dictionary containing
    keywords to be passed to ``ssl.SSLContext.wrap_socket``.  This function converts the dict form
    to its `~ssl.SSLContext` equivalent, and may be used when a component which accepts both forms
    needs to upgrade to the `~ssl.SSLContext` version to use features like SNI or ALPN.

    .. versionchanged:: 6.2

       Added server_side argument. Omitting this argument will result in a DeprecationWarning on
       Python 3.10.

    """
    if isinstance(ssl_options, ssl.SSLContext):
        return ssl_options
    assert isinstance(ssl_options, dict)
    assert all(k in _SSL_CONTEXT_KEYWORDS for k in ssl_options), ssl_options
    # TODO: Now that we have the server_side argument, can we switch to
    # create_default_context or would that change behavior?
    default_version = ssl.PROTOCOL_TLS
    if server_side:
        default_version = ssl.PROTOCOL_TLS_SERVER
    elif server_side is not None:
        default_version = ssl.PROTOCOL_TLS_CLIENT
    context = ssl.SSLContext(ssl_options.get("ssl_version", default_version))
    if "certfile" in ssl_options:
        context.load_cert_chain(
            ssl_options["certfile"], ssl_options.get("keyfile", None)
        )
    if "cert_reqs" in ssl_options:
        if ssl_options["cert_reqs"] == ssl.CERT_NONE:
            # This may have been set automatically by PROTOCOL_TLS_CLIENT but is
            # incompatible with CERT_NONE so we must manually clear it.
            context.check_hostname = False
        context.verify_mode = ssl_options["cert_reqs"]
    if "ca_certs" in ssl_options:
        context.load_verify_locations(ssl_options["ca_certs"])
    if "ciphers" in ssl_options:
        context.set_ciphers(ssl_options["ciphers"])
    if hasattr(ssl, "OP_NO_COMPRESSION"):
        # Disable TLS compression to avoid CRIME and related attacks.
        # This constant depends on openssl version 1.0.
        # TODO: Do we need to do this ourselves or can we trust
        # the defaults?
        context.options |= ssl.OP_NO_COMPRESSION
    return context


def ssl_wrap_socket(
    socket: socket.socket,
    ssl_options: Union[Dict[str, Any], ssl.SSLContext],
    server_hostname: Optional[str] = None,
    server_side: Optional[bool] = None,
    **kwargs: Any,
) -> ssl.SSLSocket:
    """Returns an ``ssl.SSLSocket`` wrapping the given socket.

    ``ssl_options`` may be either an `ssl.SSLContext` object or a
    dictionary (as accepted by `ssl_options_to_context`).  Additional
    keyword arguments are passed to `ssl.SSLContext.wrap_socket`.

    .. versionchanged:: 6.2

       Added server_side argument. Omitting this argument will
       result in a DeprecationWarning on Python 3.10.
    """
    context = ssl_options_to_context(ssl_options, server_side=server_side)
    if server_side is None:
        server_side = False
    assert ssl.HAS_SNI
    # TODO: add a unittest for hostname validation (python added server-side SNI support in 3.4)
    # In the meantime it can be manually tested with
    # python3 -m tornado.httpclient https://sni.velox.ch
    return context.wrap_socket(
        socket, server_hostname=server_hostname, server_side=server_side, **kwargs
    )

# === NexusCore/openenv\Lib\site-packages\google\api_core\exceptions.py ===
# Copyright 2014 Google LLC
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

"""Exceptions raised by Google API core & clients.

This module provides base classes for all errors raised by libraries based
on :mod:`google.api_core`, including both HTTP and gRPC clients.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import http.client
from typing import Optional, Dict
from typing import Union
import warnings

from google.rpc import error_details_pb2


def _warn_could_not_import_grpcio_status():
    warnings.warn(
        "Please install grpcio-status to obtain helpful grpc error messages.",
        ImportWarning,
    )  # pragma: NO COVER


try:
    import grpc

    try:
        from grpc_status import rpc_status
    except ImportError:  # pragma: NO COVER
        _warn_could_not_import_grpcio_status()
        rpc_status = None
except ImportError:  # pragma: NO COVER
    grpc = None

# Lookup tables for mapping exceptions from HTTP and gRPC transports.
# Populated by _GoogleAPICallErrorMeta
_HTTP_CODE_TO_EXCEPTION: Dict[int, Exception] = {}
_GRPC_CODE_TO_EXCEPTION: Dict[int, Exception] = {}

# Additional lookup table to map integer status codes to grpc status code
# grpc does not currently support initializing enums from ints
# i.e., grpc.StatusCode(5) raises an error
_INT_TO_GRPC_CODE = {}
if grpc is not None:  # pragma: no branch
    for x in grpc.StatusCode:
        _INT_TO_GRPC_CODE[x.value[0]] = x


class GoogleAPIError(Exception):
    """Base class for all exceptions raised by Google API Clients."""

    pass


class DuplicateCredentialArgs(GoogleAPIError):
    """Raised when multiple credentials are passed."""

    pass


class RetryError(GoogleAPIError):
    """Raised when a function has exhausted all of its available retries.

    Args:
        message (str): The exception message.
        cause (Exception): The last exception raised when retrying the
            function.
    """

    def __init__(self, message, cause):
        super(RetryError, self).__init__(message)
        self.message = message
        self._cause = cause

    @property
    def cause(self):
        """The last exception raised when retrying the function."""
        return self._cause

    def __str__(self):
        return "{}, last exception: {}".format(self.message, self.cause)


class _GoogleAPICallErrorMeta(type):
    """Metaclass for registering GoogleAPICallError subclasses."""

    def __new__(mcs, name, bases, class_dict):
        cls = type.__new__(mcs, name, bases, class_dict)
        if cls.code is not None:
            _HTTP_CODE_TO_EXCEPTION.setdefault(cls.code, cls)
        if cls.grpc_status_code is not None:
            _GRPC_CODE_TO_EXCEPTION.setdefault(cls.grpc_status_code, cls)
        return cls


class GoogleAPICallError(GoogleAPIError, metaclass=_GoogleAPICallErrorMeta):
    """Base class for exceptions raised by calling API methods.

    Args:
        message (str): The exception message.
        errors (Sequence[Any]): An optional list of error details.
        details (Sequence[Any]): An optional list of objects defined in google.rpc.error_details.
        response (Union[requests.Request, grpc.Call]): The response or
            gRPC call metadata.
        error_info (Union[error_details_pb2.ErrorInfo, None]): An optional object containing error info
            (google.rpc.error_details.ErrorInfo).
    """

    code: Union[int, None] = None
    """Optional[int]: The HTTP status code associated with this error.

    This may be ``None`` if the exception does not have a direct mapping
    to an HTTP error.

    See http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
    """

    grpc_status_code = None
    """Optional[grpc.StatusCode]: The gRPC status code associated with this
    error.

    This may be ``None`` if the exception does not match up to a gRPC error.
    """

    def __init__(self, message, errors=(), details=(), response=None, error_info=None):
        super(GoogleAPICallError, self).__init__(message)
        self.message = message
        """str: The exception message."""
        self._errors = errors
        self._details = details
        self._response = response
        self._error_info = error_info

    def __str__(self):
        error_msg = "{} {}".format(self.code, self.message)
        if self.details:
            error_msg = "{} {}".format(error_msg, self.details)
        # Note: This else condition can be removed once proposal A from
        # b/284179390 is implemented.
        else:
            if self.errors:
                errors = [
                    f"{error.code}: {error.message}"
                    for error in self.errors
                    if hasattr(error, "code") and hasattr(error, "message")
                ]
                if errors:
                    error_msg = "{} {}".format(error_msg, "\n".join(errors))
        return error_msg

    @property
    def reason(self):
        """The reason of the error.

        Reference:
            https://github.com/googleapis/googleapis/blob/master/google/rpc/error_details.proto#L112

        Returns:
            Union[str, None]: An optional string containing reason of the error.
        """
        return self._error_info.reason if self._error_info else None

    @property
    def domain(self):
        """The logical grouping to which the "reason" belongs.

        Reference:
            https://github.com/googleapis/googleapis/blob/master/google/rpc/error_details.proto#L112

        Returns:
            Union[str, None]: An optional string containing a logical grouping to which the "reason" belongs.
        """
        return self._error_info.domain if self._error_info else None

    @property
    def metadata(self):
        """Additional structured details about this error.

        Reference:
            https://github.com/googleapis/googleapis/blob/master/google/rpc/error_details.proto#L112

        Returns:
            Union[Dict[str, str], None]: An optional object containing structured details about the error.
        """
        return self._error_info.metadata if self._error_info else None

    @property
    def errors(self):
        """Detailed error information.

        Returns:
            Sequence[Any]: A list of additional error details.
        """
        return list(self._errors)

    @property
    def details(self):
        """Information contained in google.rpc.status.details.

        Reference:
            https://github.com/googleapis/googleapis/blob/master/google/rpc/status.proto
            https://github.com/googleapis/googleapis/blob/master/google/rpc/error_details.proto

        Returns:
            Sequence[Any]: A list of structured objects from error_details.proto
        """
        return list(self._details)

    @property
    def response(self):
        """Optional[Union[requests.Request, grpc.Call]]: The response or
        gRPC call metadata."""
        return self._response


class Redirection(GoogleAPICallError):
    """Base class for for all redirection (HTTP 3xx) responses."""


class MovedPermanently(Redirection):
    """Exception mapping a ``301 Moved Permanently`` response."""

    code = http.client.MOVED_PERMANENTLY


class NotModified(Redirection):
    """Exception mapping a ``304 Not Modified`` response."""

    code = http.client.NOT_MODIFIED


class TemporaryRedirect(Redirection):
    """Exception mapping a ``307 Temporary Redirect`` response."""

    code = http.client.TEMPORARY_REDIRECT


class ResumeIncomplete(Redirection):
    """Exception mapping a ``308 Resume Incomplete`` response.

    .. note:: :attr:`http.client.PERMANENT_REDIRECT` is ``308``, but Google
        APIs differ in their use of this status code.
    """

    code = 308


class ClientError(GoogleAPICallError):
    """Base class for all client error (HTTP 4xx) responses."""


class BadRequest(ClientError):
    """Exception mapping a ``400 Bad Request`` response."""

    code = http.client.BAD_REQUEST


class InvalidArgument(BadRequest):
    """Exception mapping a :attr:`grpc.StatusCode.INVALID_ARGUMENT` error."""

    grpc_status_code = grpc.StatusCode.INVALID_ARGUMENT if grpc is not None else None


class FailedPrecondition(BadRequest):
    """Exception mapping a :attr:`grpc.StatusCode.FAILED_PRECONDITION`
    error."""

    grpc_status_code = grpc.StatusCode.FAILED_PRECONDITION if grpc is not None else None


class OutOfRange(BadRequest):
    """Exception mapping a :attr:`grpc.StatusCode.OUT_OF_RANGE` error."""

    grpc_status_code = grpc.StatusCode.OUT_OF_RANGE if grpc is not None else None


class Unauthorized(ClientError):
    """Exception mapping a ``401 Unauthorized`` response."""

    code = http.client.UNAUTHORIZED


class Unauthenticated(Unauthorized):
    """Exception mapping a :attr:`grpc.StatusCode.UNAUTHENTICATED` error."""

    grpc_status_code = grpc.StatusCode.UNAUTHENTICATED if grpc is not None else None


class Forbidden(ClientError):
    """Exception mapping a ``403 Forbidden`` response."""

    code = http.client.FORBIDDEN


class PermissionDenied(Forbidden):
    """Exception mapping a :attr:`grpc.StatusCode.PERMISSION_DENIED` error."""

    grpc_status_code = grpc.StatusCode.PERMISSION_DENIED if grpc is not None else None


class NotFound(ClientError):
    """Exception mapping a ``404 Not Found`` response or a
    :attr:`grpc.StatusCode.NOT_FOUND` error."""

    code = http.client.NOT_FOUND
    grpc_status_code = grpc.StatusCode.NOT_FOUND if grpc is not None else None


class MethodNotAllowed(ClientError):
    """Exception mapping a ``405 Method Not Allowed`` response."""

    code = http.client.METHOD_NOT_ALLOWED


class Conflict(ClientError):
    """Exception mapping a ``409 Conflict`` response."""

    code = http.client.CONFLICT


class AlreadyExists(Conflict):
    """Exception mapping a :attr:`grpc.StatusCode.ALREADY_EXISTS` error."""

    grpc_status_code = grpc.StatusCode.ALREADY_EXISTS if grpc is not None else None


class Aborted(Conflict):
    """Exception mapping a :attr:`grpc.StatusCode.ABORTED` error."""

    grpc_status_code = grpc.StatusCode.ABORTED if grpc is not None else None


class LengthRequired(ClientError):
    """Exception mapping a ``411 Length Required`` response."""

    code = http.client.LENGTH_REQUIRED


class PreconditionFailed(ClientError):
    """Exception mapping a ``412 Precondition Failed`` response."""

    code = http.client.PRECONDITION_FAILED


class RequestRangeNotSatisfiable(ClientError):
    """Exception mapping a ``416 Request Range Not Satisfiable`` response."""

    code = http.client.REQUESTED_RANGE_NOT_SATISFIABLE


class TooManyRequests(ClientError):
    """Exception mapping a ``429 Too Many Requests`` response."""

    code = http.client.TOO_MANY_REQUESTS


class ResourceExhausted(TooManyRequests):
    """Exception mapping a :attr:`grpc.StatusCode.RESOURCE_EXHAUSTED` error."""

    grpc_status_code = grpc.StatusCode.RESOURCE_EXHAUSTED if grpc is not None else None


class Cancelled(ClientError):
    """Exception mapping a :attr:`grpc.StatusCode.CANCELLED` error."""

    # This maps to HTTP status code 499. See
    # https://github.com/googleapis/googleapis/blob/master/google/rpc/code.proto
    code = 499
    grpc_status_code = grpc.StatusCode.CANCELLED if grpc is not None else None


class ServerError(GoogleAPICallError):
    """Base for 5xx responses."""


class InternalServerError(ServerError):
    """Exception mapping a ``500 Internal Server Error`` response. or a
    :attr:`grpc.StatusCode.INTERNAL` error."""

    code = http.client.INTERNAL_SERVER_ERROR
    grpc_status_code = grpc.StatusCode.INTERNAL if grpc is not None else None


class Unknown(ServerError):
    """Exception mapping a :attr:`grpc.StatusCode.UNKNOWN` error."""

    grpc_status_code = grpc.StatusCode.UNKNOWN if grpc is not None else None


class DataLoss(ServerError):
    """Exception mapping a :attr:`grpc.StatusCode.DATA_LOSS` error."""

    grpc_status_code = grpc.StatusCode.DATA_LOSS if grpc is not None else None


class MethodNotImplemented(ServerError):
    """Exception mapping a ``501 Not Implemented`` response or a
    :attr:`grpc.StatusCode.UNIMPLEMENTED` error."""

    code = http.client.NOT_IMPLEMENTED
    grpc_status_code = grpc.StatusCode.UNIMPLEMENTED if grpc is not None else None


class BadGateway(ServerError):
    """Exception mapping a ``502 Bad Gateway`` response."""

    code = http.client.BAD_GATEWAY


class ServiceUnavailable(ServerError):
    """Exception mapping a ``503 Service Unavailable`` response or a
    :attr:`grpc.StatusCode.UNAVAILABLE` error."""

    code = http.client.SERVICE_UNAVAILABLE
    grpc_status_code = grpc.StatusCode.UNAVAILABLE if grpc is not None else None


class GatewayTimeout(ServerError):
    """Exception mapping a ``504 Gateway Timeout`` response."""

    code = http.client.GATEWAY_TIMEOUT


class DeadlineExceeded(GatewayTimeout):
    """Exception mapping a :attr:`grpc.StatusCode.DEADLINE_EXCEEDED` error."""

    grpc_status_code = grpc.StatusCode.DEADLINE_EXCEEDED if grpc is not None else None


class AsyncRestUnsupportedParameterError(NotImplementedError):
    """Raised when an unsupported parameter is configured against async rest transport."""

    pass


def exception_class_for_http_status(status_code):
    """Return the exception class for a specific HTTP status code.

    Args:
        status_code (int): The HTTP status code.

    Returns:
        :func:`type`: the appropriate subclass of :class:`GoogleAPICallError`.
    """
    return _HTTP_CODE_TO_EXCEPTION.get(status_code, GoogleAPICallError)


def from_http_status(status_code, message, **kwargs):
    """Create a :class:`GoogleAPICallError` from an HTTP status code.

    Args:
        status_code (int): The HTTP status code.
        message (str): The exception message.
        kwargs: Additional arguments passed to the :class:`GoogleAPICallError`
            constructor.

    Returns:
        GoogleAPICallError: An instance of the appropriate subclass of
            :class:`GoogleAPICallError`.
    """
    error_class = exception_class_for_http_status(status_code)
    error = error_class(message, **kwargs)

    if error.code is None:
        error.code = status_code

    return error


def _format_rest_error_message(error, method, url):
    method = method.upper() if method else None
    message = "{method} {url}: {error}".format(
        method=method,
        url=url,
        error=error,
    )
    return message


# NOTE: We're moving away from `from_http_status` because it expects an aiohttp response compared
# to `format_http_response_error` which expects a more abstract response from google.auth and is
# compatible with both sync and async response types.
# TODO(https://github.com/googleapis/python-api-core/issues/691): Add type hint for response.
def format_http_response_error(
    response, method: str, url: str, payload: Optional[Dict] = None
):
    """Create a :class:`GoogleAPICallError` from a google auth rest response.

    Args:
        response Union[google.auth.transport.Response, google.auth.aio.transport.Response]: The HTTP response.
        method Optional(str): The HTTP request method.
        url Optional(str): The HTTP request url.
        payload Optional(dict): The HTTP response payload. If not passed in, it is read from response for a response type of google.auth.transport.Response.

    Returns:
        GoogleAPICallError: An instance of the appropriate subclass of
            :class:`GoogleAPICallError`, with the message and errors populated
            from the response.
    """
    payload = {} if not payload else payload
    error_message = payload.get("error", {}).get("message", "unknown error")
    errors = payload.get("error", {}).get("errors", ())
    # In JSON, details are already formatted in developer-friendly way.
    details = payload.get("error", {}).get("details", ())
    error_info_list = list(
        filter(
            lambda detail: detail.get("@type", "")
            == "type.googleapis.com/google.rpc.ErrorInfo",
            details,
        )
    )
    error_info = error_info_list[0] if error_info_list else None
    message = _format_rest_error_message(error_message, method, url)

    exception = from_http_status(
        response.status_code,
        message,
        errors=errors,
        details=details,
        response=response,
        error_info=error_info,
    )
    return exception


def from_http_response(response):
    """Create a :class:`GoogleAPICallError` from a :class:`requests.Response`.

    Args:
        response (requests.Response): The HTTP response.

    Returns:
        GoogleAPICallError: An instance of the appropriate subclass of
            :class:`GoogleAPICallError`, with the message and errors populated
            from the response.
    """
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": {"message": response.text or "unknown error"}}
    return format_http_response_error(
        response, response.request.method, response.request.url, payload
    )


def exception_class_for_grpc_status(status_code):
    """Return the exception class for a specific :class:`grpc.StatusCode`.

    Args:
        status_code (grpc.StatusCode): The gRPC status code.

    Returns:
        :func:`type`: the appropriate subclass of :class:`GoogleAPICallError`.
    """
    return _GRPC_CODE_TO_EXCEPTION.get(status_code, GoogleAPICallError)


def from_grpc_status(status_code, message, **kwargs):
    """Create a :class:`GoogleAPICallError` from a :class:`grpc.StatusCode`.

    Args:
        status_code (Union[grpc.StatusCode, int]): The gRPC status code.
        message (str): The exception message.
        kwargs: Additional arguments passed to the :class:`GoogleAPICallError`
            constructor.

    Returns:
        GoogleAPICallError: An instance of the appropriate subclass of
            :class:`GoogleAPICallError`.
    """

    if isinstance(status_code, int):
        status_code = _INT_TO_GRPC_CODE.get(status_code, status_code)

    error_class = exception_class_for_grpc_status(status_code)
    error = error_class(message, **kwargs)

    if error.grpc_status_code is None:
        error.grpc_status_code = status_code

    return error


def _is_informative_grpc_error(rpc_exc):
    return hasattr(rpc_exc, "code") and hasattr(rpc_exc, "details")


def _parse_grpc_error_details(rpc_exc):
    if not rpc_status:  # pragma: NO COVER
        _warn_could_not_import_grpcio_status()
        return [], None
    try:
        status = rpc_status.from_call(rpc_exc)
    except NotImplementedError:  # workaround
        return [], None

    if not status:
        return [], None

    possible_errors = [
        error_details_pb2.BadRequest,
        error_details_pb2.PreconditionFailure,
        error_details_pb2.QuotaFailure,
        error_details_pb2.ErrorInfo,
        error_details_pb2.RetryInfo,
        error_details_pb2.ResourceInfo,
        error_details_pb2.RequestInfo,
        error_details_pb2.DebugInfo,
        error_details_pb2.Help,
        error_details_pb2.LocalizedMessage,
    ]
    error_info = None
    error_details = []
    for detail in status.details:
        matched_detail_cls = list(
            filter(lambda x: detail.Is(x.DESCRIPTOR), possible_errors)
        )
        # If nothing matched, use detail directly.
        if len(matched_detail_cls) == 0:
            info = detail
        else:
            info = matched_detail_cls[0]()
            detail.Unpack(info)
        error_details.append(info)
        if isinstance(info, error_details_pb2.ErrorInfo):
            error_info = info
    return error_details, error_info


def from_grpc_error(rpc_exc):
    """Create a :class:`GoogleAPICallError` from a :class:`grpc.RpcError`.

    Args:
        rpc_exc (grpc.RpcError): The gRPC error.

    Returns:
        GoogleAPICallError: An instance of the appropriate subclass of
            :class:`GoogleAPICallError`.
    """
    # NOTE(lidiz) All gRPC error shares the parent class grpc.RpcError.
    # However, check for grpc.RpcError breaks backward compatibility.
    if (
        grpc is not None and isinstance(rpc_exc, grpc.Call)
    ) or _is_informative_grpc_error(rpc_exc):
        details, err_info = _parse_grpc_error_details(rpc_exc)
        return from_grpc_status(
            rpc_exc.code(),
            rpc_exc.details(),
            errors=(rpc_exc,),
            details=details,
            response=rpc_exc,
            error_info=err_info,
        )
    else:
        return GoogleAPICallError(str(rpc_exc), errors=(rpc_exc,), response=rpc_exc)