
# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\input\ansi_escape_sequences.py ===
"""
Mappings from VT100 (ANSI) escape sequences to the corresponding prompt_toolkit
keys.

We are not using the terminfo/termcap databases to detect the ANSI escape
sequences for the input. Instead, we recognize 99% of the most common
sequences. This works well, because in practice, every modern terminal is
mostly Xterm compatible.

Some useful docs:
- Mintty: https://github.com/mintty/mintty/blob/master/wiki/Keycodes.md
"""

from __future__ import annotations

from ..keys import Keys

__all__ = [
    "ANSI_SEQUENCES",
    "REVERSE_ANSI_SEQUENCES",
]

# Mapping of vt100 escape codes to Keys.
ANSI_SEQUENCES: dict[str, Keys | tuple[Keys, ...]] = {
    # Control keys.
    "\x00": Keys.ControlAt,  # Control-At (Also for Ctrl-Space)
    "\x01": Keys.ControlA,  # Control-A (home)
    "\x02": Keys.ControlB,  # Control-B (emacs cursor left)
    "\x03": Keys.ControlC,  # Control-C (interrupt)
    "\x04": Keys.ControlD,  # Control-D (exit)
    "\x05": Keys.ControlE,  # Control-E (end)
    "\x06": Keys.ControlF,  # Control-F (cursor forward)
    "\x07": Keys.ControlG,  # Control-G
    "\x08": Keys.ControlH,  # Control-H (8) (Identical to '\b')
    "\x09": Keys.ControlI,  # Control-I (9) (Identical to '\t')
    "\x0a": Keys.ControlJ,  # Control-J (10) (Identical to '\n')
    "\x0b": Keys.ControlK,  # Control-K (delete until end of line; vertical tab)
    "\x0c": Keys.ControlL,  # Control-L (clear; form feed)
    "\x0d": Keys.ControlM,  # Control-M (13) (Identical to '\r')
    "\x0e": Keys.ControlN,  # Control-N (14) (history forward)
    "\x0f": Keys.ControlO,  # Control-O (15)
    "\x10": Keys.ControlP,  # Control-P (16) (history back)
    "\x11": Keys.ControlQ,  # Control-Q
    "\x12": Keys.ControlR,  # Control-R (18) (reverse search)
    "\x13": Keys.ControlS,  # Control-S (19) (forward search)
    "\x14": Keys.ControlT,  # Control-T
    "\x15": Keys.ControlU,  # Control-U
    "\x16": Keys.ControlV,  # Control-V
    "\x17": Keys.ControlW,  # Control-W
    "\x18": Keys.ControlX,  # Control-X
    "\x19": Keys.ControlY,  # Control-Y (25)
    "\x1a": Keys.ControlZ,  # Control-Z
    "\x1b": Keys.Escape,  # Also Control-[
    "\x9b": Keys.ShiftEscape,
    "\x1c": Keys.ControlBackslash,  # Both Control-\ (also Ctrl-| )
    "\x1d": Keys.ControlSquareClose,  # Control-]
    "\x1e": Keys.ControlCircumflex,  # Control-^
    "\x1f": Keys.ControlUnderscore,  # Control-underscore (Also for Ctrl-hyphen.)
    # ASCII Delete (0x7f)
    # Vt220 (and Linux terminal) send this when pressing backspace. We map this
    # to ControlH, because that will make it easier to create key bindings that
    # work everywhere, with the trade-off that it's no longer possible to
    # handle backspace and control-h individually for the few terminals that
    # support it. (Most terminals send ControlH when backspace is pressed.)
    # See: http://www.ibb.net/~anne/keyboard.html
    "\x7f": Keys.ControlH,
    # --
    # Various
    "\x1b[1~": Keys.Home,  # tmux
    "\x1b[2~": Keys.Insert,
    "\x1b[3~": Keys.Delete,
    "\x1b[4~": Keys.End,  # tmux
    "\x1b[5~": Keys.PageUp,
    "\x1b[6~": Keys.PageDown,
    "\x1b[7~": Keys.Home,  # xrvt
    "\x1b[8~": Keys.End,  # xrvt
    "\x1b[Z": Keys.BackTab,  # shift + tab
    "\x1b\x09": Keys.BackTab,  # Linux console
    "\x1b[~": Keys.BackTab,  # Windows console
    # --
    # Function keys.
    "\x1bOP": Keys.F1,
    "\x1bOQ": Keys.F2,
    "\x1bOR": Keys.F3,
    "\x1bOS": Keys.F4,
    "\x1b[[A": Keys.F1,  # Linux console.
    "\x1b[[B": Keys.F2,  # Linux console.
    "\x1b[[C": Keys.F3,  # Linux console.
    "\x1b[[D": Keys.F4,  # Linux console.
    "\x1b[[E": Keys.F5,  # Linux console.
    "\x1b[11~": Keys.F1,  # rxvt-unicode
    "\x1b[12~": Keys.F2,  # rxvt-unicode
    "\x1b[13~": Keys.F3,  # rxvt-unicode
    "\x1b[14~": Keys.F4,  # rxvt-unicode
    "\x1b[15~": Keys.F5,
    "\x1b[17~": Keys.F6,
    "\x1b[18~": Keys.F7,
    "\x1b[19~": Keys.F8,
    "\x1b[20~": Keys.F9,
    "\x1b[21~": Keys.F10,
    "\x1b[23~": Keys.F11,
    "\x1b[24~": Keys.F12,
    "\x1b[25~": Keys.F13,
    "\x1b[26~": Keys.F14,
    "\x1b[28~": Keys.F15,
    "\x1b[29~": Keys.F16,
    "\x1b[31~": Keys.F17,
    "\x1b[32~": Keys.F18,
    "\x1b[33~": Keys.F19,
    "\x1b[34~": Keys.F20,
    # Xterm
    "\x1b[1;2P": Keys.F13,
    "\x1b[1;2Q": Keys.F14,
    # '\x1b[1;2R': Keys.F15,  # Conflicts with CPR response.
    "\x1b[1;2S": Keys.F16,
    "\x1b[15;2~": Keys.F17,
    "\x1b[17;2~": Keys.F18,
    "\x1b[18;2~": Keys.F19,
    "\x1b[19;2~": Keys.F20,
    "\x1b[20;2~": Keys.F21,
    "\x1b[21;2~": Keys.F22,
    "\x1b[23;2~": Keys.F23,
    "\x1b[24;2~": Keys.F24,
    # --
    # CSI 27 disambiguated modified "other" keys (xterm)
    # Ref: https://invisible-island.net/xterm/modified-keys.html
    # These are currently unsupported, so just re-map some common ones to the
    # unmodified versions
    "\x1b[27;2;13~": Keys.ControlM,  # Shift + Enter
    "\x1b[27;5;13~": Keys.ControlM,  # Ctrl + Enter
    "\x1b[27;6;13~": Keys.ControlM,  # Ctrl + Shift + Enter
    # --
    # Control + function keys.
    "\x1b[1;5P": Keys.ControlF1,
    "\x1b[1;5Q": Keys.ControlF2,
    # "\x1b[1;5R": Keys.ControlF3,  # Conflicts with CPR response.
    "\x1b[1;5S": Keys.ControlF4,
    "\x1b[15;5~": Keys.ControlF5,
    "\x1b[17;5~": Keys.ControlF6,
    "\x1b[18;5~": Keys.ControlF7,
    "\x1b[19;5~": Keys.ControlF8,
    "\x1b[20;5~": Keys.ControlF9,
    "\x1b[21;5~": Keys.ControlF10,
    "\x1b[23;5~": Keys.ControlF11,
    "\x1b[24;5~": Keys.ControlF12,
    "\x1b[1;6P": Keys.ControlF13,
    "\x1b[1;6Q": Keys.ControlF14,
    # "\x1b[1;6R": Keys.ControlF15,  # Conflicts with CPR response.
    "\x1b[1;6S": Keys.ControlF16,
    "\x1b[15;6~": Keys.ControlF17,
    "\x1b[17;6~": Keys.ControlF18,
    "\x1b[18;6~": Keys.ControlF19,
    "\x1b[19;6~": Keys.ControlF20,
    "\x1b[20;6~": Keys.ControlF21,
    "\x1b[21;6~": Keys.ControlF22,
    "\x1b[23;6~": Keys.ControlF23,
    "\x1b[24;6~": Keys.ControlF24,
    # --
    # Tmux (Win32 subsystem) sends the following scroll events.
    "\x1b[62~": Keys.ScrollUp,
    "\x1b[63~": Keys.ScrollDown,
    "\x1b[200~": Keys.BracketedPaste,  # Start of bracketed paste.
    # --
    # Sequences generated by numpad 5. Not sure what it means. (It doesn't
    # appear in 'infocmp'. Just ignore.
    "\x1b[E": Keys.Ignore,  # Xterm.
    "\x1b[G": Keys.Ignore,  # Linux console.
    # --
    # Meta/control/escape + pageup/pagedown/insert/delete.
    "\x1b[3;2~": Keys.ShiftDelete,  # xterm, gnome-terminal.
    "\x1b[5;2~": Keys.ShiftPageUp,
    "\x1b[6;2~": Keys.ShiftPageDown,
    "\x1b[2;3~": (Keys.Escape, Keys.Insert),
    "\x1b[3;3~": (Keys.Escape, Keys.Delete),
    "\x1b[5;3~": (Keys.Escape, Keys.PageUp),
    "\x1b[6;3~": (Keys.Escape, Keys.PageDown),
    "\x1b[2;4~": (Keys.Escape, Keys.ShiftInsert),
    "\x1b[3;4~": (Keys.Escape, Keys.ShiftDelete),
    "\x1b[5;4~": (Keys.Escape, Keys.ShiftPageUp),
    "\x1b[6;4~": (Keys.Escape, Keys.ShiftPageDown),
    "\x1b[3;5~": Keys.ControlDelete,  # xterm, gnome-terminal.
    "\x1b[5;5~": Keys.ControlPageUp,
    "\x1b[6;5~": Keys.ControlPageDown,
    "\x1b[3;6~": Keys.ControlShiftDelete,
    "\x1b[5;6~": Keys.ControlShiftPageUp,
    "\x1b[6;6~": Keys.ControlShiftPageDown,
    "\x1b[2;7~": (Keys.Escape, Keys.ControlInsert),
    "\x1b[5;7~": (Keys.Escape, Keys.ControlPageDown),
    "\x1b[6;7~": (Keys.Escape, Keys.ControlPageDown),
    "\x1b[2;8~": (Keys.Escape, Keys.ControlShiftInsert),
    "\x1b[5;8~": (Keys.Escape, Keys.ControlShiftPageDown),
    "\x1b[6;8~": (Keys.Escape, Keys.ControlShiftPageDown),
    # --
    # Arrows.
    # (Normal cursor mode).
    "\x1b[A": Keys.Up,
    "\x1b[B": Keys.Down,
    "\x1b[C": Keys.Right,
    "\x1b[D": Keys.Left,
    "\x1b[H": Keys.Home,
    "\x1b[F": Keys.End,
    # Tmux sends following keystrokes when control+arrow is pressed, but for
    # Emacs ansi-term sends the same sequences for normal arrow keys. Consider
    # it a normal arrow press, because that's more important.
    # (Application cursor mode).
    "\x1bOA": Keys.Up,
    "\x1bOB": Keys.Down,
    "\x1bOC": Keys.Right,
    "\x1bOD": Keys.Left,
    "\x1bOF": Keys.End,
    "\x1bOH": Keys.Home,
    # Shift + arrows.
    "\x1b[1;2A": Keys.ShiftUp,
    "\x1b[1;2B": Keys.ShiftDown,
    "\x1b[1;2C": Keys.ShiftRight,
    "\x1b[1;2D": Keys.ShiftLeft,
    "\x1b[1;2F": Keys.ShiftEnd,
    "\x1b[1;2H": Keys.ShiftHome,
    # Meta + arrow keys. Several terminals handle this differently.
    # The following sequences are for xterm and gnome-terminal.
    #     (Iterm sends ESC followed by the normal arrow_up/down/left/right
    #     sequences, and the OSX Terminal sends ESCb and ESCf for "alt
    #     arrow_left" and "alt arrow_right." We don't handle these
    #     explicitly, in here, because would could not distinguish between
    #     pressing ESC (to go to Vi navigation mode), followed by just the
    #     'b' or 'f' key. These combinations are handled in
    #     the input processor.)
    "\x1b[1;3A": (Keys.Escape, Keys.Up),
    "\x1b[1;3B": (Keys.Escape, Keys.Down),
    "\x1b[1;3C": (Keys.Escape, Keys.Right),
    "\x1b[1;3D": (Keys.Escape, Keys.Left),
    "\x1b[1;3F": (Keys.Escape, Keys.End),
    "\x1b[1;3H": (Keys.Escape, Keys.Home),
    # Alt+shift+number.
    "\x1b[1;4A": (Keys.Escape, Keys.ShiftDown),
    "\x1b[1;4B": (Keys.Escape, Keys.ShiftUp),
    "\x1b[1;4C": (Keys.Escape, Keys.ShiftRight),
    "\x1b[1;4D": (Keys.Escape, Keys.ShiftLeft),
    "\x1b[1;4F": (Keys.Escape, Keys.ShiftEnd),
    "\x1b[1;4H": (Keys.Escape, Keys.ShiftHome),
    # Control + arrows.
    "\x1b[1;5A": Keys.ControlUp,  # Cursor Mode
    "\x1b[1;5B": Keys.ControlDown,  # Cursor Mode
    "\x1b[1;5C": Keys.ControlRight,  # Cursor Mode
    "\x1b[1;5D": Keys.ControlLeft,  # Cursor Mode
    "\x1b[1;5F": Keys.ControlEnd,
    "\x1b[1;5H": Keys.ControlHome,
    # Tmux sends following keystrokes when control+arrow is pressed, but for
    # Emacs ansi-term sends the same sequences for normal arrow keys. Consider
    # it a normal arrow press, because that's more important.
    "\x1b[5A": Keys.ControlUp,
    "\x1b[5B": Keys.ControlDown,
    "\x1b[5C": Keys.ControlRight,
    "\x1b[5D": Keys.ControlLeft,
    "\x1bOc": Keys.ControlRight,  # rxvt
    "\x1bOd": Keys.ControlLeft,  # rxvt
    # Control + shift + arrows.
    "\x1b[1;6A": Keys.ControlShiftDown,
    "\x1b[1;6B": Keys.ControlShiftUp,
    "\x1b[1;6C": Keys.ControlShiftRight,
    "\x1b[1;6D": Keys.ControlShiftLeft,
    "\x1b[1;6F": Keys.ControlShiftEnd,
    "\x1b[1;6H": Keys.ControlShiftHome,
    # Control + Meta + arrows.
    "\x1b[1;7A": (Keys.Escape, Keys.ControlDown),
    "\x1b[1;7B": (Keys.Escape, Keys.ControlUp),
    "\x1b[1;7C": (Keys.Escape, Keys.ControlRight),
    "\x1b[1;7D": (Keys.Escape, Keys.ControlLeft),
    "\x1b[1;7F": (Keys.Escape, Keys.ControlEnd),
    "\x1b[1;7H": (Keys.Escape, Keys.ControlHome),
    # Meta + Shift + arrows.
    "\x1b[1;8A": (Keys.Escape, Keys.ControlShiftDown),
    "\x1b[1;8B": (Keys.Escape, Keys.ControlShiftUp),
    "\x1b[1;8C": (Keys.Escape, Keys.ControlShiftRight),
    "\x1b[1;8D": (Keys.Escape, Keys.ControlShiftLeft),
    "\x1b[1;8F": (Keys.Escape, Keys.ControlShiftEnd),
    "\x1b[1;8H": (Keys.Escape, Keys.ControlShiftHome),
    # Meta + arrow on (some?) Macs when using iTerm defaults (see issue #483).
    "\x1b[1;9A": (Keys.Escape, Keys.Up),
    "\x1b[1;9B": (Keys.Escape, Keys.Down),
    "\x1b[1;9C": (Keys.Escape, Keys.Right),
    "\x1b[1;9D": (Keys.Escape, Keys.Left),
    # --
    # Control/shift/meta + number in mintty.
    # (c-2 will actually send c-@ and c-6 will send c-^.)
    "\x1b[1;5p": Keys.Control0,
    "\x1b[1;5q": Keys.Control1,
    "\x1b[1;5r": Keys.Control2,
    "\x1b[1;5s": Keys.Control3,
    "\x1b[1;5t": Keys.Control4,
    "\x1b[1;5u": Keys.Control5,
    "\x1b[1;5v": Keys.Control6,
    "\x1b[1;5w": Keys.Control7,
    "\x1b[1;5x": Keys.Control8,
    "\x1b[1;5y": Keys.Control9,
    "\x1b[1;6p": Keys.ControlShift0,
    "\x1b[1;6q": Keys.ControlShift1,
    "\x1b[1;6r": Keys.ControlShift2,
    "\x1b[1;6s": Keys.ControlShift3,
    "\x1b[1;6t": Keys.ControlShift4,
    "\x1b[1;6u": Keys.ControlShift5,
    "\x1b[1;6v": Keys.ControlShift6,
    "\x1b[1;6w": Keys.ControlShift7,
    "\x1b[1;6x": Keys.ControlShift8,
    "\x1b[1;6y": Keys.ControlShift9,
    "\x1b[1;7p": (Keys.Escape, Keys.Control0),
    "\x1b[1;7q": (Keys.Escape, Keys.Control1),
    "\x1b[1;7r": (Keys.Escape, Keys.Control2),
    "\x1b[1;7s": (Keys.Escape, Keys.Control3),
    "\x1b[1;7t": (Keys.Escape, Keys.Control4),
    "\x1b[1;7u": (Keys.Escape, Keys.Control5),
    "\x1b[1;7v": (Keys.Escape, Keys.Control6),
    "\x1b[1;7w": (Keys.Escape, Keys.Control7),
    "\x1b[1;7x": (Keys.Escape, Keys.Control8),
    "\x1b[1;7y": (Keys.Escape, Keys.Control9),
    "\x1b[1;8p": (Keys.Escape, Keys.ControlShift0),
    "\x1b[1;8q": (Keys.Escape, Keys.ControlShift1),
    "\x1b[1;8r": (Keys.Escape, Keys.ControlShift2),
    "\x1b[1;8s": (Keys.Escape, Keys.ControlShift3),
    "\x1b[1;8t": (Keys.Escape, Keys.ControlShift4),
    "\x1b[1;8u": (Keys.Escape, Keys.ControlShift5),
    "\x1b[1;8v": (Keys.Escape, Keys.ControlShift6),
    "\x1b[1;8w": (Keys.Escape, Keys.ControlShift7),
    "\x1b[1;8x": (Keys.Escape, Keys.ControlShift8),
    "\x1b[1;8y": (Keys.Escape, Keys.ControlShift9),
}


def _get_reverse_ansi_sequences() -> dict[Keys, str]:
    """
    Create a dictionary that maps prompt_toolkit keys back to the VT100 escape
    sequences.
    """
    result: dict[Keys, str] = {}

    for sequence, key in ANSI_SEQUENCES.items():
        if not isinstance(key, tuple):
            if key not in result:
                result[key] = sequence

    return result


REVERSE_ANSI_SEQUENCES = _get_reverse_ansi_sequences()

# === NexusCore/openenv\Lib\site-packages\tornado\log.py ===
#
# Copyright 2012 Facebook
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
"""Logging support for Tornado.

Tornado uses three logger streams:

* ``tornado.access``: Per-request logging for Tornado's HTTP servers (and
  potentially other servers in the future)
* ``tornado.application``: Logging of errors from application code (i.e.
  uncaught exceptions from callbacks)
* ``tornado.general``: General-purpose logging, including any errors
  or warnings from Tornado itself.

These streams may be configured independently using the standard library's
`logging` module.  For example, you may wish to send ``tornado.access`` logs
to a separate file for analysis.
"""
import logging
import logging.handlers
import sys

from tornado.escape import _unicode
from tornado.util import unicode_type, basestring_type

try:
    import colorama  # type: ignore
except ImportError:
    colorama = None

try:
    import curses
except ImportError:
    curses = None  # type: ignore

from typing import Dict, Any, cast, Optional

# Logger objects for internal tornado use
access_log = logging.getLogger("tornado.access")
app_log = logging.getLogger("tornado.application")
gen_log = logging.getLogger("tornado.general")


def _stderr_supports_color() -> bool:
    try:
        if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
            if curses:
                curses.setupterm()
                if curses.tigetnum("colors") > 0:
                    return True
            elif colorama:
                if sys.stderr is getattr(
                    colorama.initialise, "wrapped_stderr", object()
                ):
                    return True
    except Exception:
        # Very broad exception handling because it's always better to
        # fall back to non-colored logs than to break at startup.
        pass
    return False


def _safe_unicode(s: Any) -> str:
    try:
        return _unicode(s)
    except UnicodeDecodeError:
        return repr(s)


class LogFormatter(logging.Formatter):
    """Log formatter used in Tornado.

    Key features of this formatter are:

    * Color support when logging to a terminal that supports it.
    * Timestamps on every log line.
    * Robust against str/bytes encoding problems.

    This formatter is enabled automatically by
    `tornado.options.parse_command_line` or `tornado.options.parse_config_file`
    (unless ``--logging=none`` is used).

    Color support on Windows versions that do not support ANSI color codes is
    enabled by use of the colorama__ library. Applications that wish to use
    this must first initialize colorama with a call to ``colorama.init``.
    See the colorama documentation for details.

    __ https://pypi.python.org/pypi/colorama

    .. versionchanged:: 4.5
       Added support for ``colorama``. Changed the constructor
       signature to be compatible with `logging.config.dictConfig`.
    """

    DEFAULT_FORMAT = "%(color)s[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d]%(end_color)s %(message)s"  # noqa: E501
    DEFAULT_DATE_FORMAT = "%y%m%d %H:%M:%S"
    DEFAULT_COLORS = {
        logging.DEBUG: 4,  # Blue
        logging.INFO: 2,  # Green
        logging.WARNING: 3,  # Yellow
        logging.ERROR: 1,  # Red
        logging.CRITICAL: 5,  # Magenta
    }

    def __init__(
        self,
        fmt: str = DEFAULT_FORMAT,
        datefmt: str = DEFAULT_DATE_FORMAT,
        style: str = "%",
        color: bool = True,
        colors: Dict[int, int] = DEFAULT_COLORS,
    ) -> None:
        r"""
        :arg bool color: Enables color support.
        :arg str fmt: Log message format.
          It will be applied to the attributes dict of log records. The
          text between ``%(color)s`` and ``%(end_color)s`` will be colored
          depending on the level if color support is on.
        :arg dict colors: color mappings from logging level to terminal color
          code
        :arg str datefmt: Datetime format.
          Used for formatting ``(asctime)`` placeholder in ``prefix_fmt``.

        .. versionchanged:: 3.2

           Added ``fmt`` and ``datefmt`` arguments.
        """
        logging.Formatter.__init__(self, datefmt=datefmt)
        self._fmt = fmt

        self._colors = {}  # type: Dict[int, str]
        if color and _stderr_supports_color():
            if curses is not None:
                fg_color = curses.tigetstr("setaf") or curses.tigetstr("setf") or b""

                for levelno, code in colors.items():
                    # Convert the terminal control characters from
                    # bytes to unicode strings for easier use with the
                    # logging module.
                    self._colors[levelno] = unicode_type(
                        curses.tparm(fg_color, code), "ascii"
                    )
                normal = curses.tigetstr("sgr0")
                if normal is not None:
                    self._normal = unicode_type(normal, "ascii")
                else:
                    self._normal = ""
            else:
                # If curses is not present (currently we'll only get here for
                # colorama on windows), assume hard-coded ANSI color codes.
                for levelno, code in colors.items():
                    self._colors[levelno] = "\033[2;3%dm" % code
                self._normal = "\033[0m"
        else:
            self._normal = ""

    def format(self, record: Any) -> str:
        try:
            message = record.getMessage()
            assert isinstance(message, basestring_type)  # guaranteed by logging
            # Encoding notes:  The logging module prefers to work with character
            # strings, but only enforces that log messages are instances of
            # basestring.  In python 2, non-ascii bytestrings will make
            # their way through the logging framework until they blow up with
            # an unhelpful decoding error (with this formatter it happens
            # when we attach the prefix, but there are other opportunities for
            # exceptions further along in the framework).
            #
            # If a byte string makes it this far, convert it to unicode to
            # ensure it will make it out to the logs.  Use repr() as a fallback
            # to ensure that all byte strings can be converted successfully,
            # but don't do it by default so we don't add extra quotes to ascii
            # bytestrings.  This is a bit of a hacky place to do this, but
            # it's worth it since the encoding errors that would otherwise
            # result are so useless (and tornado is fond of using utf8-encoded
            # byte strings wherever possible).
            record.message = _safe_unicode(message)
        except Exception as e:
            record.message = f"Bad message ({e!r}): {record.__dict__!r}"

        record.asctime = self.formatTime(record, cast(str, self.datefmt))

        if record.levelno in self._colors:
            record.color = self._colors[record.levelno]
            record.end_color = self._normal
        else:
            record.color = record.end_color = ""

        formatted = self._fmt % record.__dict__

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            # exc_text contains multiple lines.  We need to _safe_unicode
            # each line separately so that non-utf8 bytes don't cause
            # all the newlines to turn into '\n'.
            lines = [formatted.rstrip()]
            lines.extend(_safe_unicode(ln) for ln in record.exc_text.split("\n"))
            formatted = "\n".join(lines)
        return formatted.replace("\n", "\n    ")


def enable_pretty_logging(
    options: Any = None, logger: Optional[logging.Logger] = None
) -> None:
    """Turns on formatted logging output as configured.

    This is called automatically by `tornado.options.parse_command_line`
    and `tornado.options.parse_config_file`.
    """
    if options is None:
        import tornado.options

        options = tornado.options.options
    if options.logging is None or options.logging.lower() == "none":
        return
    if logger is None:
        logger = logging.getLogger()
    logger.setLevel(getattr(logging, options.logging.upper()))
    if options.log_file_prefix:
        rotate_mode = options.log_rotate_mode
        if rotate_mode == "size":
            channel = logging.handlers.RotatingFileHandler(
                filename=options.log_file_prefix,
                maxBytes=options.log_file_max_size,
                backupCount=options.log_file_num_backups,
                encoding="utf-8",
            )  # type: logging.Handler
        elif rotate_mode == "time":
            channel = logging.handlers.TimedRotatingFileHandler(
                filename=options.log_file_prefix,
                when=options.log_rotate_when,
                interval=options.log_rotate_interval,
                backupCount=options.log_file_num_backups,
                encoding="utf-8",
            )
        else:
            error_message = (
                "The value of log_rotate_mode option should be "
                + '"size" or "time", not "%s".' % rotate_mode
            )
            raise ValueError(error_message)
        channel.setFormatter(LogFormatter(color=False))
        logger.addHandler(channel)

    if options.log_to_stderr or (options.log_to_stderr is None and not logger.handlers):
        # Set up color if we are in a tty and curses is installed
        channel = logging.StreamHandler()
        channel.setFormatter(LogFormatter())
        logger.addHandler(channel)


def define_logging_options(options: Any = None) -> None:
    """Add logging-related flags to ``options``.

    These options are present automatically on the default options instance;
    this method is only necessary if you have created your own `.OptionParser`.

    .. versionadded:: 4.2
        This function existed in prior versions but was broken and undocumented until 4.2.
    """
    if options is None:
        # late import to prevent cycle
        import tornado.options

        options = tornado.options.options
    options.define(
        "logging",
        default="info",
        help=(
            "Set the Python log level. If 'none', tornado won't touch the "
            "logging configuration."
        ),
        metavar="debug|info|warning|error|none",
    )
    options.define(
        "log_to_stderr",
        type=bool,
        default=None,
        help=(
            "Send log output to stderr (colorized if possible). "
            "By default use stderr if --log_file_prefix is not set and "
            "no other logging is configured."
        ),
    )
    options.define(
        "log_file_prefix",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Path prefix for log files. "
            "Note that if you are running multiple tornado processes, "
            "log_file_prefix must be different for each of them (e.g. "
            "include the port number)"
        ),
    )
    options.define(
        "log_file_max_size",
        type=int,
        default=100 * 1000 * 1000,
        help="max size of log files before rollover",
    )
    options.define(
        "log_file_num_backups", type=int, default=10, help="number of log files to keep"
    )

    options.define(
        "log_rotate_when",
        type=str,
        default="midnight",
        help=(
            "specify the type of TimedRotatingFileHandler interval "
            "other options:('S', 'M', 'H', 'D', 'W0'-'W6')"
        ),
    )
    options.define(
        "log_rotate_interval",
        type=int,
        default=1,
        help="The interval value of timed rotating",
    )

    options.define(
        "log_rotate_mode",
        type=str,
        default="size",
        help="The mode of rotating files(time or size)",
    )

    options.add_parse_callback(lambda: enable_pretty_logging(options))

# === NexusCore/openenv\Lib\site-packages\google\api_core\grpc_helpers_async.py ===
# Copyright 2020 Google LLC
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

"""AsyncIO helpers for :mod:`grpc` supporting 3.7+.

Please combine more detailed docstring in grpc_helpers.py to use following
functions. This module is implementing the same surface with AsyncIO semantics.
"""

import asyncio
import functools

from typing import AsyncGenerator, Generic, Iterator, Optional, TypeVar

import grpc
from grpc import aio

from google.api_core import exceptions, grpc_helpers

# denotes the proto response type for grpc calls
P = TypeVar("P")

# NOTE(lidiz) Alternatively, we can hack "__getattribute__" to perform
# automatic patching for us. But that means the overhead of creating an
# extra Python function spreads to every single send and receive.


class _WrappedCall(aio.Call):
    def __init__(self):
        self._call = None

    def with_call(self, call):
        """Supplies the call object separately to keep __init__ clean."""
        self._call = call
        return self

    async def initial_metadata(self):
        return await self._call.initial_metadata()

    async def trailing_metadata(self):
        return await self._call.trailing_metadata()

    async def code(self):
        return await self._call.code()

    async def details(self):
        return await self._call.details()

    def cancelled(self):
        return self._call.cancelled()

    def done(self):
        return self._call.done()

    def time_remaining(self):
        return self._call.time_remaining()

    def cancel(self):
        return self._call.cancel()

    def add_done_callback(self, callback):
        self._call.add_done_callback(callback)

    async def wait_for_connection(self):
        try:
            await self._call.wait_for_connection()
        except grpc.RpcError as rpc_error:
            raise exceptions.from_grpc_error(rpc_error) from rpc_error


class _WrappedUnaryResponseMixin(Generic[P], _WrappedCall):
    def __await__(self) -> Iterator[P]:
        try:
            response = yield from self._call.__await__()
            return response
        except grpc.RpcError as rpc_error:
            raise exceptions.from_grpc_error(rpc_error) from rpc_error


class _WrappedStreamResponseMixin(Generic[P], _WrappedCall):
    def __init__(self):
        self._wrapped_async_generator = None

    async def read(self) -> P:
        try:
            return await self._call.read()
        except grpc.RpcError as rpc_error:
            raise exceptions.from_grpc_error(rpc_error) from rpc_error

    async def _wrapped_aiter(self) -> AsyncGenerator[P, None]:
        try:
            # NOTE(lidiz) coverage doesn't understand the exception raised from
            # __anext__ method. It is covered by test case:
            #     test_wrap_stream_errors_aiter_non_rpc_error
            async for response in self._call:  # pragma: no branch
                yield response
        except grpc.RpcError as rpc_error:
            raise exceptions.from_grpc_error(rpc_error) from rpc_error

    def __aiter__(self) -> AsyncGenerator[P, None]:
        if not self._wrapped_async_generator:
            self._wrapped_async_generator = self._wrapped_aiter()
        return self._wrapped_async_generator


class _WrappedStreamRequestMixin(_WrappedCall):
    async def write(self, request):
        try:
            await self._call.write(request)
        except grpc.RpcError as rpc_error:
            raise exceptions.from_grpc_error(rpc_error) from rpc_error

    async def done_writing(self):
        try:
            await self._call.done_writing()
        except grpc.RpcError as rpc_error:
            raise exceptions.from_grpc_error(rpc_error) from rpc_error


# NOTE(lidiz) Implementing each individual class separately, so we don't
# expose any API that should not be seen. E.g., __aiter__ in unary-unary
# RPC, or __await__ in stream-stream RPC.
class _WrappedUnaryUnaryCall(_WrappedUnaryResponseMixin[P], aio.UnaryUnaryCall):
    """Wrapped UnaryUnaryCall to map exceptions."""


class _WrappedUnaryStreamCall(_WrappedStreamResponseMixin[P], aio.UnaryStreamCall):
    """Wrapped UnaryStreamCall to map exceptions."""


class _WrappedStreamUnaryCall(
    _WrappedUnaryResponseMixin[P], _WrappedStreamRequestMixin, aio.StreamUnaryCall
):
    """Wrapped StreamUnaryCall to map exceptions."""


class _WrappedStreamStreamCall(
    _WrappedStreamRequestMixin, _WrappedStreamResponseMixin[P], aio.StreamStreamCall
):
    """Wrapped StreamStreamCall to map exceptions."""


# public type alias denoting the return type of async streaming gapic calls
GrpcAsyncStream = _WrappedStreamResponseMixin
# public type alias denoting the return type of unary gapic calls
AwaitableGrpcCall = _WrappedUnaryResponseMixin


def _wrap_unary_errors(callable_):
    """Map errors for Unary-Unary async callables."""

    @functools.wraps(callable_)
    def error_remapped_callable(*args, **kwargs):
        call = callable_(*args, **kwargs)
        return _WrappedUnaryUnaryCall().with_call(call)

    return error_remapped_callable


def _wrap_stream_errors(callable_, wrapper_type):
    """Map errors for streaming RPC async callables."""

    @functools.wraps(callable_)
    async def error_remapped_callable(*args, **kwargs):
        call = callable_(*args, **kwargs)
        call = wrapper_type().with_call(call)
        await call.wait_for_connection()
        return call

    return error_remapped_callable


def wrap_errors(callable_):
    """Wrap a gRPC async callable and map :class:`grpc.RpcErrors` to
    friendly error classes.

    Errors raised by the gRPC callable are mapped to the appropriate
    :class:`google.api_core.exceptions.GoogleAPICallError` subclasses. The
    original `grpc.RpcError` (which is usually also a `grpc.Call`) is
    available from the ``response`` property on the mapped exception. This
    is useful for extracting metadata from the original error.

    Args:
        callable_ (Callable): A gRPC callable.

    Returns: Callable: The wrapped gRPC callable.
    """
    grpc_helpers._patch_callable_name(callable_)

    if isinstance(callable_, aio.UnaryStreamMultiCallable):
        return _wrap_stream_errors(callable_, _WrappedUnaryStreamCall)
    elif isinstance(callable_, aio.StreamUnaryMultiCallable):
        return _wrap_stream_errors(callable_, _WrappedStreamUnaryCall)
    elif isinstance(callable_, aio.StreamStreamMultiCallable):
        return _wrap_stream_errors(callable_, _WrappedStreamStreamCall)
    else:
        return _wrap_unary_errors(callable_)


def create_channel(
    target,
    credentials=None,
    scopes=None,
    ssl_credentials=None,
    credentials_file=None,
    quota_project_id=None,
    default_scopes=None,
    default_host=None,
    compression=None,
    attempt_direct_path: Optional[bool] = False,
    **kwargs
):
    """Create an AsyncIO secure channel with credentials.

    Args:
        target (str): The target service address in the format 'hostname:port'.
        credentials (google.auth.credentials.Credentials): The credentials. If
            not specified, then this function will attempt to ascertain the
            credentials from the environment using :func:`google.auth.default`.
        scopes (Sequence[str]): A optional list of scopes needed for this
            service. These are only used when credentials are not specified and
            are passed to :func:`google.auth.default`.
        ssl_credentials (grpc.ChannelCredentials): Optional SSL channel
            credentials. This can be used to specify different certificates.
        credentials_file (str): A file with credentials that can be loaded with
            :func:`google.auth.load_credentials_from_file`. This argument is
            mutually exclusive with credentials.

            .. warning::
                Important: If you accept a credential configuration (credential JSON/File/Stream)
                from an external source for authentication to Google Cloud Platform, you must
                validate it before providing it to any Google API or client library. Providing an
                unvalidated credential configuration to Google APIs or libraries can compromise
                the security of your systems and data. For more information, refer to
                `Validate credential configurations from external sources`_.

            .. _Validate credential configurations from external sources:

            https://cloud.google.com/docs/authentication/external/externally-sourced-credentials
        quota_project_id (str): An optional project to use for billing and quota.
        default_scopes (Sequence[str]): Default scopes passed by a Google client
            library. Use 'scopes' for user-defined scopes.
        default_host (str): The default endpoint. e.g., "pubsub.googleapis.com".
        compression (grpc.Compression): An optional value indicating the
            compression method to be used over the lifetime of the channel.
        attempt_direct_path (Optional[bool]): If set, Direct Path will be attempted
            when the request is made. Direct Path is only available within a Google
            Compute Engine (GCE) environment and provides a proxyless connection
            which increases the available throughput, reduces latency, and increases
            reliability. Note:

            - This argument should only be set in a GCE environment and for Services
              that are known to support Direct Path.
            - If this argument is set outside of GCE, then this request will fail
              unless the back-end service happens to have configured fall-back to DNS.
            - If the request causes a `ServiceUnavailable` response, it is recommended
              that the client repeat the request with `attempt_direct_path` set to
              `False` as the Service may not support Direct Path.
            - Using `ssl_credentials` with `attempt_direct_path` set to `True` will
              result in `ValueError` as this combination  is not yet supported.

        kwargs: Additional key-word args passed to :func:`aio.secure_channel`.

    Returns:
        aio.Channel: The created channel.

    Raises:
        google.api_core.DuplicateCredentialArgs: If both a credentials object and credentials_file are passed.
        ValueError: If `ssl_credentials` is set and `attempt_direct_path` is set to `True`.
    """

    # If `ssl_credentials` is set and `attempt_direct_path` is set to `True`,
    # raise ValueError as this is not yet supported.
    # See https://github.com/googleapis/python-api-core/issues/590
    if ssl_credentials and attempt_direct_path:
        raise ValueError("Using ssl_credentials with Direct Path is not supported")

    composite_credentials = grpc_helpers._create_composite_credentials(
        credentials=credentials,
        credentials_file=credentials_file,
        scopes=scopes,
        default_scopes=default_scopes,
        ssl_credentials=ssl_credentials,
        quota_project_id=quota_project_id,
        default_host=default_host,
    )

    if attempt_direct_path:
        target = grpc_helpers._modify_target_for_direct_path(target)

    return aio.secure_channel(
        target, composite_credentials, compression=compression, **kwargs
    )


class FakeUnaryUnaryCall(_WrappedUnaryUnaryCall):
    """Fake implementation for unary-unary RPCs.

    It is a dummy object for response message. Supply the intended response
    upon the initialization, and the coroutine will return the exact response
    message.
    """

    def __init__(self, response=object()):
        self.response = response
        self._future = asyncio.get_event_loop().create_future()
        self._future.set_result(self.response)

    def __await__(self):
        response = yield from self._future.__await__()
        return response


class FakeStreamUnaryCall(_WrappedStreamUnaryCall):
    """Fake implementation for stream-unary RPCs.

    It is a dummy object for response message. Supply the intended response
    upon the initialization, and the coroutine will return the exact response
    message.
    """

    def __init__(self, response=object()):
        self.response = response
        self._future = asyncio.get_event_loop().create_future()
        self._future.set_result(self.response)

    def __await__(self):
        response = yield from self._future.__await__()
        return response

    async def wait_for_connection(self):
        pass

# === NexusCore/openenv\Lib\site-packages\google\auth\transport\grpc.py ===
# Copyright 2016 Google LLC
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

"""Authorization support for gRPC."""

from __future__ import absolute_import

import logging
import os

from google.auth import environment_vars
from google.auth import exceptions
from google.auth.transport import _mtls_helper
from google.oauth2 import service_account

try:
    import grpc  # type: ignore
except ImportError as caught_exc:  # pragma: NO COVER
    raise ImportError(
        "gRPC is not installed from please install the grpcio package to use the gRPC transport."
    ) from caught_exc

_LOGGER = logging.getLogger(__name__)


class AuthMetadataPlugin(grpc.AuthMetadataPlugin):
    """A `gRPC AuthMetadataPlugin`_ that inserts the credentials into each
    request.

    .. _gRPC AuthMetadataPlugin:
        http://www.grpc.io/grpc/python/grpc.html#grpc.AuthMetadataPlugin

    Args:
        credentials (google.auth.credentials.Credentials): The credentials to
            add to requests.
        request (google.auth.transport.Request): A HTTP transport request
            object used to refresh credentials as needed.
        default_host (Optional[str]): A host like "pubsub.googleapis.com".
            This is used when a self-signed JWT is created from service
            account credentials.
    """

    def __init__(self, credentials, request, default_host=None):
        # pylint: disable=no-value-for-parameter
        # pylint doesn't realize that the super method takes no arguments
        # because this class is the same name as the superclass.
        super(AuthMetadataPlugin, self).__init__()
        self._credentials = credentials
        self._request = request
        self._default_host = default_host

    def _get_authorization_headers(self, context):
        """Gets the authorization headers for a request.

        Returns:
            Sequence[Tuple[str, str]]: A list of request headers (key, value)
                to add to the request.
        """
        headers = {}

        # https://google.aip.dev/auth/4111
        # Attempt to use self-signed JWTs when a service account is used.
        # A default host must be explicitly provided since it cannot always
        # be determined from the context.service_url.
        if isinstance(self._credentials, service_account.Credentials):
            self._credentials._create_self_signed_jwt(
                "https://{}/".format(self._default_host) if self._default_host else None
            )

        self._credentials.before_request(
            self._request, context.method_name, context.service_url, headers
        )

        return list(headers.items())

    def __call__(self, context, callback):
        """Passes authorization metadata into the given callback.

        Args:
            context (grpc.AuthMetadataContext): The RPC context.
            callback (grpc.AuthMetadataPluginCallback): The callback that will
                be invoked to pass in the authorization metadata.
        """
        callback(self._get_authorization_headers(context), None)


def secure_authorized_channel(
    credentials,
    request,
    target,
    ssl_credentials=None,
    client_cert_callback=None,
    **kwargs
):
    """Creates a secure authorized gRPC channel.

    This creates a channel with SSL and :class:`AuthMetadataPlugin`. This
    channel can be used to create a stub that can make authorized requests.
    Users can configure client certificate or rely on device certificates to
    establish a mutual TLS channel, if the `GOOGLE_API_USE_CLIENT_CERTIFICATE`
    variable is explicitly set to `true`.

    Example::

        import google.auth
        import google.auth.transport.grpc
        import google.auth.transport.requests
        from google.cloud.speech.v1 import cloud_speech_pb2

        # Get credentials.
        credentials, _ = google.auth.default()

        # Get an HTTP request function to refresh credentials.
        request = google.auth.transport.requests.Request()

        # Create a channel.
        channel = google.auth.transport.grpc.secure_authorized_channel(
            credentials, regular_endpoint, request,
            ssl_credentials=grpc.ssl_channel_credentials())

        # Use the channel to create a stub.
        cloud_speech.create_Speech_stub(channel)

    Usage:

    There are actually a couple of options to create a channel, depending on if
    you want to create a regular or mutual TLS channel.

    First let's list the endpoints (regular vs mutual TLS) to choose from::

        regular_endpoint = 'speech.googleapis.com:443'
        mtls_endpoint = 'speech.mtls.googleapis.com:443'

    Option 1: create a regular (non-mutual) TLS channel by explicitly setting
    the ssl_credentials::

        regular_ssl_credentials = grpc.ssl_channel_credentials()

        channel = google.auth.transport.grpc.secure_authorized_channel(
            credentials, regular_endpoint, request,
            ssl_credentials=regular_ssl_credentials)

    Option 2: create a mutual TLS channel by calling a callback which returns
    the client side certificate and the key (Note that
    `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable must be explicitly
    set to `true`)::

        def my_client_cert_callback():
            code_to_load_client_cert_and_key()
            if loaded:
                return (pem_cert_bytes, pem_key_bytes)
            raise MyClientCertFailureException()

        try:
            channel = google.auth.transport.grpc.secure_authorized_channel(
                credentials, mtls_endpoint, request,
                client_cert_callback=my_client_cert_callback)
        except MyClientCertFailureException:
            # handle the exception

    Option 3: use application default SSL credentials. It searches and uses
    the command in a context aware metadata file, which is available on devices
    with endpoint verification support (Note that
    `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable must be explicitly
    set to `true`).
    See https://cloud.google.com/endpoint-verification/docs/overview::

        try:
            default_ssl_credentials = SslCredentials()
        except:
            # Exception can be raised if the context aware metadata is malformed.
            # See :class:`SslCredentials` for the possible exceptions.

        # Choose the endpoint based on the SSL credentials type.
        if default_ssl_credentials.is_mtls:
            endpoint_to_use = mtls_endpoint
        else:
            endpoint_to_use = regular_endpoint
        channel = google.auth.transport.grpc.secure_authorized_channel(
            credentials, endpoint_to_use, request,
            ssl_credentials=default_ssl_credentials)

    Option 4: not setting ssl_credentials and client_cert_callback. For devices
    without endpoint verification support or `GOOGLE_API_USE_CLIENT_CERTIFICATE`
    environment variable is not `true`, a regular TLS channel is created;
    otherwise, a mutual TLS channel is created, however, the call should be
    wrapped in a try/except block in case of malformed context aware metadata.

    The following code uses regular_endpoint, it works the same no matter the
    created channle is regular or mutual TLS. Regular endpoint ignores client
    certificate and key::

        channel = google.auth.transport.grpc.secure_authorized_channel(
            credentials, regular_endpoint, request)

    The following code uses mtls_endpoint, if the created channle is regular,
    and API mtls_endpoint is confgured to require client SSL credentials, API
    calls using this channel will be rejected::

        channel = google.auth.transport.grpc.secure_authorized_channel(
            credentials, mtls_endpoint, request)

    Args:
        credentials (google.auth.credentials.Credentials): The credentials to
            add to requests.
        request (google.auth.transport.Request): A HTTP transport request
            object used to refresh credentials as needed. Even though gRPC
            is a separate transport, there's no way to refresh the credentials
            without using a standard http transport.
        target (str): The host and port of the service.
        ssl_credentials (grpc.ChannelCredentials): Optional SSL channel
            credentials. This can be used to specify different certificates.
            This argument is mutually exclusive with client_cert_callback;
            providing both will raise an exception.
            If ssl_credentials and client_cert_callback are None, application
            default SSL credentials are used if `GOOGLE_API_USE_CLIENT_CERTIFICATE`
            environment variable is explicitly set to `true`, otherwise one way TLS
            SSL credentials are used.
        client_cert_callback (Callable[[], (bytes, bytes)]): Optional
            callback function to obtain client certicate and key for mutual TLS
            connection. This argument is mutually exclusive with
            ssl_credentials; providing both will raise an exception.
            This argument does nothing unless `GOOGLE_API_USE_CLIENT_CERTIFICATE`
            environment variable is explicitly set to `true`.
        kwargs: Additional arguments to pass to :func:`grpc.secure_channel`.

    Returns:
        grpc.Channel: The created gRPC channel.

    Raises:
        google.auth.exceptions.MutualTLSChannelError: If mutual TLS channel
            creation failed for any reason.
    """
    # Create the metadata plugin for inserting the authorization header.
    metadata_plugin = AuthMetadataPlugin(credentials, request)

    # Create a set of grpc.CallCredentials using the metadata plugin.
    google_auth_credentials = grpc.metadata_call_credentials(metadata_plugin)

    if ssl_credentials and client_cert_callback:
        raise exceptions.MalformedError(
            "Received both ssl_credentials and client_cert_callback; "
            "these are mutually exclusive."
        )

    # If SSL credentials are not explicitly set, try client_cert_callback and ADC.
    if not ssl_credentials:
        use_client_cert = os.getenv(
            environment_vars.GOOGLE_API_USE_CLIENT_CERTIFICATE, "false"
        )
        if use_client_cert == "true" and client_cert_callback:
            # Use the callback if provided.
            cert, key = client_cert_callback()
            ssl_credentials = grpc.ssl_channel_credentials(
                certificate_chain=cert, private_key=key
            )
        elif use_client_cert == "true":
            # Use application default SSL credentials.
            adc_ssl_credentils = SslCredentials()
            ssl_credentials = adc_ssl_credentils.ssl_credentials
        else:
            ssl_credentials = grpc.ssl_channel_credentials()

    # Combine the ssl credentials and the authorization credentials.
    composite_credentials = grpc.composite_channel_credentials(
        ssl_credentials, google_auth_credentials
    )

    return grpc.secure_channel(target, composite_credentials, **kwargs)


class SslCredentials:
    """Class for application default SSL credentials.

    The behavior is controlled by `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment
    variable whose default value is `false`. Client certificate will not be used
    unless the environment variable is explicitly set to `true`. See
    https://google.aip.dev/auth/4114

    If the environment variable is `true`, then for devices with endpoint verification
    support, a device certificate will be automatically loaded and mutual TLS will
    be established.
    See https://cloud.google.com/endpoint-verification/docs/overview.
    """

    def __init__(self):
        use_client_cert = os.getenv(
            environment_vars.GOOGLE_API_USE_CLIENT_CERTIFICATE, "false"
        )
        if use_client_cert != "true":
            self._is_mtls = False
        else:
            # Load client SSL credentials.
            metadata_path = _mtls_helper._check_config_path(
                _mtls_helper.CONTEXT_AWARE_METADATA_PATH
            )
            self._is_mtls = metadata_path is not None

    @property
    def ssl_credentials(self):
        """Get the created SSL channel credentials.

        For devices with endpoint verification support, if the device certificate
        loading has any problems, corresponding exceptions will be raised. For
        a device without endpoint verification support, no exceptions will be
        raised.

        Returns:
            grpc.ChannelCredentials: The created grpc channel credentials.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS channel
                creation failed for any reason.
        """
        if self._is_mtls:
            try:
                _, cert, key, _ = _mtls_helper.get_client_ssl_credentials()
                self._ssl_credentials = grpc.ssl_channel_credentials(
                    certificate_chain=cert, private_key=key
                )
            except exceptions.ClientCertError as caught_exc:
                new_exc = exceptions.MutualTLSChannelError(caught_exc)
                raise new_exc from caught_exc
        else:
            self._ssl_credentials = grpc.ssl_channel_credentials()

        return self._ssl_credentials

    @property
    def is_mtls(self):
        """Indicates if the created SSL channel credentials is mutual TLS."""
        return self._is_mtls

# === NexusCore/openenv\Lib\site-packages\filelock\asyncio.py ===
"""An asyncio-based implementation of the file lock."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from dataclasses import dataclass
from threading import local
from typing import TYPE_CHECKING, Any, Callable, NoReturn, cast

from ._api import BaseFileLock, FileLockContext, FileLockMeta
from ._error import Timeout
from ._soft import SoftFileLock
from ._unix import UnixFileLock
from ._windows import WindowsFileLock

if TYPE_CHECKING:
    import sys
    from concurrent import futures
    from types import TracebackType

    if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
        from typing import Self
    else:  # pragma: no cover (<py311)
        from typing_extensions import Self


_LOGGER = logging.getLogger("filelock")


@dataclass
class AsyncFileLockContext(FileLockContext):
    """A dataclass which holds the context for a ``BaseAsyncFileLock`` object."""

    #: Whether run in executor
    run_in_executor: bool = True

    #: The executor
    executor: futures.Executor | None = None

    #: The loop
    loop: asyncio.AbstractEventLoop | None = None


class AsyncThreadLocalFileContext(AsyncFileLockContext, local):
    """A thread local version of the ``FileLockContext`` class."""


class AsyncAcquireReturnProxy:
    """A context-aware object that will release the lock file when exiting."""

    def __init__(self, lock: BaseAsyncFileLock) -> None:  # noqa: D107
        self.lock = lock

    async def __aenter__(self) -> BaseAsyncFileLock:  # noqa: D105
        return self.lock

    async def __aexit__(  # noqa: D105
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.lock.release()


class AsyncFileLockMeta(FileLockMeta):
    def __call__(  # type: ignore[override] # noqa: PLR0913
        cls,  # noqa: N805
        lock_file: str | os.PathLike[str],
        timeout: float = -1,
        mode: int = 0o644,
        thread_local: bool = False,  # noqa: FBT001, FBT002
        *,
        blocking: bool = True,
        is_singleton: bool = False,
        loop: asyncio.AbstractEventLoop | None = None,
        run_in_executor: bool = True,
        executor: futures.Executor | None = None,
    ) -> BaseAsyncFileLock:
        if thread_local and run_in_executor:
            msg = "run_in_executor is not supported when thread_local is True"
            raise ValueError(msg)
        instance = super().__call__(
            lock_file=lock_file,
            timeout=timeout,
            mode=mode,
            thread_local=thread_local,
            blocking=blocking,
            is_singleton=is_singleton,
            loop=loop,
            run_in_executor=run_in_executor,
            executor=executor,
        )
        return cast("BaseAsyncFileLock", instance)


class BaseAsyncFileLock(BaseFileLock, metaclass=AsyncFileLockMeta):
    """Base class for asynchronous file locks."""

    def __init__(  # noqa: PLR0913
        self,
        lock_file: str | os.PathLike[str],
        timeout: float = -1,
        mode: int = 0o644,
        thread_local: bool = False,  # noqa: FBT001, FBT002
        *,
        blocking: bool = True,
        is_singleton: bool = False,
        loop: asyncio.AbstractEventLoop | None = None,
        run_in_executor: bool = True,
        executor: futures.Executor | None = None,
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
        :param loop: The event loop to use. If not specified, the running event loop will be used.
        :param run_in_executor: If this is set to ``True`` then the lock will be acquired in an executor.
        :param executor: The executor to use. If not specified, the default executor will be used.

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
            "loop": loop,
            "run_in_executor": run_in_executor,
            "executor": executor,
        }
        self._context: AsyncFileLockContext = (AsyncThreadLocalFileContext if thread_local else AsyncFileLockContext)(
            **kwargs
        )

    @property
    def run_in_executor(self) -> bool:
        """::return: whether run in executor."""
        return self._context.run_in_executor

    @property
    def executor(self) -> futures.Executor | None:
        """::return: the executor."""
        return self._context.executor

    @executor.setter
    def executor(self, value: futures.Executor | None) -> None:  # pragma: no cover
        """
        Change the executor.

        :param value: the new executor or ``None``
        :type value: futures.Executor | None

        """
        self._context.executor = value

    @property
    def loop(self) -> asyncio.AbstractEventLoop | None:
        """::return: the event loop."""
        return self._context.loop

    async def acquire(  # type: ignore[override]
        self,
        timeout: float | None = None,
        poll_interval: float = 0.05,
        *,
        blocking: bool | None = None,
    ) -> AsyncAcquireReturnProxy:
        """
        Try to acquire the file lock.

        :param timeout: maximum wait time for acquiring the lock, ``None`` means use the default
            :attr:`~BaseFileLock.timeout` is and if ``timeout < 0``, there is no timeout and
            this method will block until the lock could be acquired
        :param poll_interval: interval of trying to acquire the lock file
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

        """
        # Use the default timeout, if no timeout is provided.
        if timeout is None:
            timeout = self._context.timeout

        if blocking is None:
            blocking = self._context.blocking

        # Increment the number right at the beginning. We can still undo it, if something fails.
        self._context.lock_counter += 1

        lock_id = id(self)
        lock_filename = self.lock_file
        start_time = time.perf_counter()
        try:
            while True:
                if not self.is_locked:
                    _LOGGER.debug("Attempting to acquire lock %s on %s", lock_id, lock_filename)
                    await self._run_internal_method(self._acquire)
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
                await asyncio.sleep(poll_interval)
        except BaseException:  # Something did go wrong, so decrement the counter.
            self._context.lock_counter = max(0, self._context.lock_counter - 1)
            raise
        return AsyncAcquireReturnProxy(lock=self)

    async def release(self, force: bool = False) -> None:  # type: ignore[override]  # noqa: FBT001, FBT002
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
                await self._run_internal_method(self._release)
                self._context.lock_counter = 0
                _LOGGER.debug("Lock %s released on %s", lock_id, lock_filename)

    async def _run_internal_method(self, method: Callable[[], Any]) -> None:
        if asyncio.iscoroutinefunction(method):
            await method()
        elif self.run_in_executor:
            loop = self.loop or asyncio.get_running_loop()
            await loop.run_in_executor(self.executor, method)
        else:
            method()

    def __enter__(self) -> NoReturn:
        """
        Replace old __enter__ method to avoid using it.

        NOTE: DO NOT USE `with` FOR ASYNCIO LOCKS, USE `async with` INSTEAD.

        :return: none
        :rtype: NoReturn
        """
        msg = "Do not use `with` for asyncio locks, use `async with` instead."
        raise NotImplementedError(msg)

    async def __aenter__(self) -> Self:
        """
        Acquire the lock.

        :return: the lock object

        """
        await self.acquire()
        return self

    async def __aexit__(
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
        await self.release()

    def __del__(self) -> None:
        """Called when the lock object is deleted."""
        with contextlib.suppress(RuntimeError):
            loop = self.loop or asyncio.get_running_loop()
            if not loop.is_running():  # pragma: no cover
                loop.run_until_complete(self.release(force=True))
            else:
                loop.create_task(self.release(force=True))


class AsyncSoftFileLock(SoftFileLock, BaseAsyncFileLock):
    """Simply watches the existence of the lock file."""


class AsyncUnixFileLock(UnixFileLock, BaseAsyncFileLock):
    """Uses the :func:`fcntl.flock` to hard lock the lock file on unix systems."""


class AsyncWindowsFileLock(WindowsFileLock, BaseAsyncFileLock):
    """Uses the :func:`msvcrt.locking` to hard lock the lock file on windows systems."""


__all__ = [
    "AsyncAcquireReturnProxy",
    "AsyncSoftFileLock",
    "AsyncUnixFileLock",
    "AsyncWindowsFileLock",
    "BaseAsyncFileLock",
]

# === NexusCore/openenv\Lib\site-packages\nltk\stem\lancaster.py ===
# Natural Language Toolkit: Stemmers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Tomcavage <stomcava@law.upenn.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A word stemmer based on the Lancaster (Paice/Husk) stemming algorithm.
Paice, Chris D. "Another Stemmer." ACM SIGIR Forum 24.3 (1990): 56-61.
"""
import re

from nltk.stem.api import StemmerI


class LancasterStemmer(StemmerI):
    """
    Lancaster Stemmer

        >>> from nltk.stem.lancaster import LancasterStemmer
        >>> st = LancasterStemmer()
        >>> st.stem('maximum')     # Remove "-um" when word is intact
        'maxim'
        >>> st.stem('presumably')  # Don't remove "-um" when word is not intact
        'presum'
        >>> st.stem('multiply')    # No action taken if word ends with "-ply"
        'multiply'
        >>> st.stem('provision')   # Replace "-sion" with "-j" to trigger "j" set of rules
        'provid'
        >>> st.stem('owed')        # Word starting with vowel must contain at least 2 letters
        'ow'
        >>> st.stem('ear')         # ditto
        'ear'
        >>> st.stem('saying')      # Words starting with consonant must contain at least 3
        'say'
        >>> st.stem('crying')      #     letters and one of those letters must be a vowel
        'cry'
        >>> st.stem('string')      # ditto
        'string'
        >>> st.stem('meant')       # ditto
        'meant'
        >>> st.stem('cement')      # ditto
        'cem'
        >>> st_pre = LancasterStemmer(strip_prefix_flag=True)
        >>> st_pre.stem('kilometer') # Test Prefix
        'met'
        >>> st_custom = LancasterStemmer(rule_tuple=("ssen4>", "s1t."))
        >>> st_custom.stem("ness") # Change s to t
        'nest'
    """

    # The rule list is static since it doesn't change between instances
    default_rule_tuple = (
        "ai*2.",  # -ia > -   if intact
        "a*1.",  # -a > -    if intact
        "bb1.",  # -bb > -b
        "city3s.",  # -ytic > -ys
        "ci2>",  # -ic > -
        "cn1t>",  # -nc > -nt
        "dd1.",  # -dd > -d
        "dei3y>",  # -ied > -y
        "deec2ss.",  # -ceed >", -cess
        "dee1.",  # -eed > -ee
        "de2>",  # -ed > -
        "dooh4>",  # -hood > -
        "e1>",  # -e > -
        "feil1v.",  # -lief > -liev
        "fi2>",  # -if > -
        "gni3>",  # -ing > -
        "gai3y.",  # -iag > -y
        "ga2>",  # -ag > -
        "gg1.",  # -gg > -g
        "ht*2.",  # -th > -   if intact
        "hsiug5ct.",  # -guish > -ct
        "hsi3>",  # -ish > -
        "i*1.",  # -i > -    if intact
        "i1y>",  # -i > -y
        "ji1d.",  # -ij > -id   --  see nois4j> & vis3j>
        "juf1s.",  # -fuj > -fus
        "ju1d.",  # -uj > -ud
        "jo1d.",  # -oj > -od
        "jeh1r.",  # -hej > -her
        "jrev1t.",  # -verj > -vert
        "jsim2t.",  # -misj > -mit
        "jn1d.",  # -nj > -nd
        "j1s.",  # -j > -s
        "lbaifi6.",  # -ifiabl > -
        "lbai4y.",  # -iabl > -y
        "lba3>",  # -abl > -
        "lbi3.",  # -ibl > -
        "lib2l>",  # -bil > -bl
        "lc1.",  # -cl > c
        "lufi4y.",  # -iful > -y
        "luf3>",  # -ful > -
        "lu2.",  # -ul > -
        "lai3>",  # -ial > -
        "lau3>",  # -ual > -
        "la2>",  # -al > -
        "ll1.",  # -ll > -l
        "mui3.",  # -ium > -
        "mu*2.",  # -um > -   if intact
        "msi3>",  # -ism > -
        "mm1.",  # -mm > -m
        "nois4j>",  # -sion > -j
        "noix4ct.",  # -xion > -ct
        "noi3>",  # -ion > -
        "nai3>",  # -ian > -
        "na2>",  # -an > -
        "nee0.",  # protect  -een
        "ne2>",  # -en > -
        "nn1.",  # -nn > -n
        "pihs4>",  # -ship > -
        "pp1.",  # -pp > -p
        "re2>",  # -er > -
        "rae0.",  # protect  -ear
        "ra2.",  # -ar > -
        "ro2>",  # -or > -
        "ru2>",  # -ur > -
        "rr1.",  # -rr > -r
        "rt1>",  # -tr > -t
        "rei3y>",  # -ier > -y
        "sei3y>",  # -ies > -y
        "sis2.",  # -sis > -s
        "si2>",  # -is > -
        "ssen4>",  # -ness > -
        "ss0.",  # protect  -ss
        "suo3>",  # -ous > -
        "su*2.",  # -us > -   if intact
        "s*1>",  # -s > -    if intact
        "s0.",  # -s > -s
        "tacilp4y.",  # -plicat > -ply
        "ta2>",  # -at > -
        "tnem4>",  # -ment > -
        "tne3>",  # -ent > -
        "tna3>",  # -ant > -
        "tpir2b.",  # -ript > -rib
        "tpro2b.",  # -orpt > -orb
        "tcud1.",  # -duct > -duc
        "tpmus2.",  # -sumpt > -sum
        "tpec2iv.",  # -cept > -ceiv
        "tulo2v.",  # -olut > -olv
        "tsis0.",  # protect  -sist
        "tsi3>",  # -ist > -
        "tt1.",  # -tt > -t
        "uqi3.",  # -iqu > -
        "ugo1.",  # -ogu > -og
        "vis3j>",  # -siv > -j
        "vie0.",  # protect  -eiv
        "vi2>",  # -iv > -
        "ylb1>",  # -bly > -bl
        "yli3y>",  # -ily > -y
        "ylp0.",  # protect  -ply
        "yl2>",  # -ly > -
        "ygo1.",  # -ogy > -og
        "yhp1.",  # -phy > -ph
        "ymo1.",  # -omy > -om
        "ypo1.",  # -opy > -op
        "yti3>",  # -ity > -
        "yte3>",  # -ety > -
        "ytl2.",  # -lty > -l
        "yrtsi5.",  # -istry > -
        "yra3>",  # -ary > -
        "yro3>",  # -ory > -
        "yfi3.",  # -ify > -
        "ycn2t>",  # -ncy > -nt
        "yca3>",  # -acy > -
        "zi2>",  # -iz > -
        "zy1s.",  # -yz > -ys
    )

    def __init__(self, rule_tuple=None, strip_prefix_flag=False):
        """Create an instance of the Lancaster stemmer."""
        # Setup an empty rule dictionary - this will be filled in later
        self.rule_dictionary = {}
        # Check if a user wants to strip prefix
        self._strip_prefix = strip_prefix_flag
        # Check if a user wants to use his/her own rule tuples.
        self._rule_tuple = rule_tuple if rule_tuple else self.default_rule_tuple

    def parseRules(self, rule_tuple=None):
        """Validate the set of rules used in this stemmer.

        If this function is called as an individual method, without using stem
        method, rule_tuple argument will be compiled into self.rule_dictionary.
        If this function is called within stem, self._rule_tuple will be used.

        """
        # If there is no argument for the function, use class' own rule tuple.
        rule_tuple = rule_tuple if rule_tuple else self._rule_tuple
        valid_rule = re.compile(r"^[a-z]+\*?\d[a-z]*[>\.]?$")
        # Empty any old rules from the rule set before adding new ones
        self.rule_dictionary = {}

        for rule in rule_tuple:
            if not valid_rule.match(rule):
                raise ValueError(f"The rule {rule} is invalid")
            first_letter = rule[0:1]
            if first_letter in self.rule_dictionary:
                self.rule_dictionary[first_letter].append(rule)
            else:
                self.rule_dictionary[first_letter] = [rule]

    def stem(self, word):
        """Stem a word using the Lancaster stemmer."""
        # Lower-case the word, since all the rules are lower-cased
        word = word.lower()
        word = self.__stripPrefix(word) if self._strip_prefix else word

        # Save a copy of the original word
        intact_word = word

        # If rule dictionary is empty, parse rule tuple.
        if not self.rule_dictionary:
            self.parseRules()

        return self.__doStemming(word, intact_word)

    def __doStemming(self, word, intact_word):
        """Perform the actual word stemming"""

        valid_rule = re.compile(r"^([a-z]+)(\*?)(\d)([a-z]*)([>\.]?)$")

        proceed = True

        while proceed:
            # Find the position of the last letter of the word to be stemmed
            last_letter_position = self.__getLastLetter(word)

            # Only stem the word if it has a last letter and a rule matching that last letter
            if (
                last_letter_position < 0
                or word[last_letter_position] not in self.rule_dictionary
            ):
                proceed = False

            else:
                rule_was_applied = False

                # Go through each rule that matches the word's final letter
                for rule in self.rule_dictionary[word[last_letter_position]]:
                    rule_match = valid_rule.match(rule)
                    if rule_match:
                        (
                            ending_string,
                            intact_flag,
                            remove_total,
                            append_string,
                            cont_flag,
                        ) = rule_match.groups()

                        # Convert the number of chars to remove when stemming
                        # from a string to an integer
                        remove_total = int(remove_total)

                        # Proceed if word's ending matches rule's word ending
                        if word.endswith(ending_string[::-1]):
                            if intact_flag:
                                if word == intact_word and self.__isAcceptable(
                                    word, remove_total
                                ):
                                    word = self.__applyRule(
                                        word, remove_total, append_string
                                    )
                                    rule_was_applied = True
                                    if cont_flag == ".":
                                        proceed = False
                                    break
                            elif self.__isAcceptable(word, remove_total):
                                word = self.__applyRule(
                                    word, remove_total, append_string
                                )
                                rule_was_applied = True
                                if cont_flag == ".":
                                    proceed = False
                                break
                # If no rules apply, the word doesn't need any more stemming
                if rule_was_applied == False:
                    proceed = False
        return word

    def __getLastLetter(self, word):
        """Get the zero-based index of the last alphabetic character in this string"""
        last_letter = -1
        for position in range(len(word)):
            if word[position].isalpha():
                last_letter = position
            else:
                break
        return last_letter

    def __isAcceptable(self, word, remove_total):
        """Determine if the word is acceptable for stemming."""
        word_is_acceptable = False
        # If the word starts with a vowel, it must be at least 2
        # characters long to be stemmed
        if word[0] in "aeiouy":
            if len(word) - remove_total >= 2:
                word_is_acceptable = True
        # If the word starts with a consonant, it must be at least 3
        # characters long (including one vowel) to be stemmed
        elif len(word) - remove_total >= 3:
            if word[1] in "aeiouy":
                word_is_acceptable = True
            elif word[2] in "aeiouy":
                word_is_acceptable = True
        return word_is_acceptable

    def __applyRule(self, word, remove_total, append_string):
        """Apply the stemming rule to the word"""
        # Remove letters from the end of the word
        new_word_length = len(word) - remove_total
        word = word[0:new_word_length]

        # And add new letters to the end of the truncated word
        if append_string:
            word += append_string
        return word

    def __stripPrefix(self, word):
        """Remove prefix from a word.

        This function originally taken from Whoosh.

        """
        for prefix in (
            "kilo",
            "micro",
            "milli",
            "intra",
            "ultra",
            "mega",
            "nano",
            "pico",
            "pseudo",
        ):
            if word.startswith(prefix):
                return word[len(prefix) :]
        return word

    def __repr__(self):
        return "<LancasterStemmer>"

# === NexusCore/openenv\Lib\site-packages\jupyter_client\kernelspecapp.py ===
"""Apps for managing kernel specs."""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import errno
import json
import os.path
import sys
import typing as t

from jupyter_core.application import JupyterApp, base_aliases, base_flags
from traitlets import Bool, Dict, Instance, List, Unicode
from traitlets.config.application import Application

from . import __version__
from .kernelspec import KernelSpecManager
from .provisioning.factory import KernelProvisionerFactory


class ListKernelSpecs(JupyterApp):
    """An app to list kernel specs."""

    version = __version__
    description = """List installed kernel specifications."""
    kernel_spec_manager = Instance(KernelSpecManager)
    json_output = Bool(
        False,
        help="output spec name and location as machine-readable json.",
        config=True,
    )

    flags = {
        "json": (
            {"ListKernelSpecs": {"json_output": True}},
            "output spec name and location as machine-readable json.",
        ),
        "debug": base_flags["debug"],
    }

    def _kernel_spec_manager_default(self) -> KernelSpecManager:
        return KernelSpecManager(parent=self, data_dir=self.data_dir)

    def start(self) -> dict[str, t.Any] | None:  # type:ignore[override]
        """Start the application."""
        paths = self.kernel_spec_manager.find_kernel_specs()
        specs = self.kernel_spec_manager.get_all_specs()
        if not self.json_output:
            if not specs:
                print("No kernels available")
                return None
            # pad to width of longest kernel name
            name_len = len(sorted(paths, key=lambda name: len(name))[-1])

            def path_key(item: t.Any) -> t.Any:
                """sort key function for Jupyter path priority"""
                path = item[1]
                for idx, prefix in enumerate(self.jupyter_path):
                    if path.startswith(prefix):
                        return (idx, path)
                # not in jupyter path, artificially added to the front
                return (-1, path)

            print("Available kernels:")
            for kernelname, path in sorted(paths.items(), key=path_key):
                print(f"  {kernelname.ljust(name_len)}    {path}")
        else:
            print(json.dumps({"kernelspecs": specs}, indent=2))
        return specs


class InstallKernelSpec(JupyterApp):
    """An app to install a kernel spec."""

    version = __version__
    description = """Install a kernel specification directory.

    Given a SOURCE DIRECTORY containing a kernel spec,
    jupyter will copy that directory into one of the Jupyter kernel directories.
    The default is to install kernelspecs for all users.
    `--user` can be specified to install a kernel only for the current user.
    """
    examples = """
    jupyter kernelspec install /path/to/my_kernel --user
    """
    usage = "jupyter kernelspec install SOURCE_DIR [--options]"
    kernel_spec_manager = Instance(KernelSpecManager)

    def _kernel_spec_manager_default(self) -> KernelSpecManager:
        return KernelSpecManager(data_dir=self.data_dir)

    sourcedir = Unicode()
    kernel_name = Unicode("", config=True, help="Install the kernel spec with this name")

    def _kernel_name_default(self) -> str:
        return os.path.basename(self.sourcedir)

    user = Bool(
        False,
        config=True,
        help="""
        Try to install the kernel spec to the per-user directory instead of
        the system or environment directory.
        """,
    )
    prefix = Unicode(
        "",
        config=True,
        help="""Specify a prefix to install to, e.g. an env.
        The kernelspec will be installed in PREFIX/share/jupyter/kernels/
        """,
    )
    replace = Bool(False, config=True, help="Replace any existing kernel spec with this name.")

    aliases = {
        "name": "InstallKernelSpec.kernel_name",
        "prefix": "InstallKernelSpec.prefix",
    }
    aliases.update(base_aliases)

    flags = {
        "user": (
            {"InstallKernelSpec": {"user": True}},
            "Install to the per-user kernel registry",
        ),
        "replace": (
            {"InstallKernelSpec": {"replace": True}},
            "Replace any existing kernel spec with this name.",
        ),
        "sys-prefix": (
            {"InstallKernelSpec": {"prefix": sys.prefix}},
            "Install to Python's sys.prefix. Useful in conda/virtual environments.",
        ),
        "debug": base_flags["debug"],
    }

    def parse_command_line(self, argv: None | list[str]) -> None:  # type:ignore[override]
        """Parse the command line args."""
        super().parse_command_line(argv)
        # accept positional arg as profile name
        if self.extra_args:
            self.sourcedir = self.extra_args[0]
        else:
            print("No source directory specified.", file=sys.stderr)
            self.exit(1)

    def start(self) -> None:
        """Start the application."""
        if self.user and self.prefix:
            self.exit("Can't specify both user and prefix. Please choose one or the other.")
        try:
            self.kernel_spec_manager.install_kernel_spec(
                self.sourcedir,
                kernel_name=self.kernel_name,
                user=self.user,
                prefix=self.prefix,
                replace=self.replace,
            )
        except OSError as e:
            if e.errno == errno.EACCES:
                print(e, file=sys.stderr)
                if not self.user:
                    print("Perhaps you want to install with `sudo` or `--user`?", file=sys.stderr)
                self.exit(1)
            elif e.errno == errno.EEXIST:
                print(f"A kernel spec is already present at {e.filename}", file=sys.stderr)
                self.exit(1)
            raise


class RemoveKernelSpec(JupyterApp):
    """An app to remove a kernel spec."""

    version = __version__
    description = """Remove one or more Jupyter kernelspecs by name."""
    examples = """jupyter kernelspec remove python2 [my_kernel ...]"""

    force = Bool(False, config=True, help="""Force removal, don't prompt for confirmation.""")
    spec_names = List(Unicode())

    kernel_spec_manager = Instance(KernelSpecManager)

    def _kernel_spec_manager_default(self) -> KernelSpecManager:
        return KernelSpecManager(data_dir=self.data_dir, parent=self)

    flags = {
        "f": ({"RemoveKernelSpec": {"force": True}}, force.help),
    }
    flags.update(JupyterApp.flags)

    def parse_command_line(self, argv: list[str] | None) -> None:  # type:ignore[override]
        """Parse the command line args."""
        super().parse_command_line(argv)
        # accept positional arg as profile name
        if self.extra_args:
            self.spec_names = sorted(set(self.extra_args))  # remove duplicates
        else:
            self.exit("No kernelspec specified.")

    def start(self) -> None:
        """Start the application."""
        self.kernel_spec_manager.ensure_native_kernel = False
        spec_paths = self.kernel_spec_manager.find_kernel_specs()
        missing = set(self.spec_names).difference(set(spec_paths))
        if missing:
            self.exit("Couldn't find kernel spec(s): %s" % ", ".join(missing))

        if not (self.force or self.answer_yes):
            print("Kernel specs to remove:")
            for name in self.spec_names:
                path = spec_paths.get(name, name)
                print(f"  {name.ljust(20)}\t{path.ljust(20)}")
            answer = input("Remove %i kernel specs [y/N]: " % len(self.spec_names))
            if not answer.lower().startswith("y"):
                return

        for kernel_name in self.spec_names:
            try:
                path = self.kernel_spec_manager.remove_kernel_spec(kernel_name)
            except OSError as e:
                if e.errno == errno.EACCES:
                    print(e, file=sys.stderr)
                    print("Perhaps you want sudo?", file=sys.stderr)
                    self.exit(1)
                else:
                    raise
            print(f"Removed {path}")


class InstallNativeKernelSpec(JupyterApp):
    """An app to install the native kernel spec."""

    version = __version__
    description = """[DEPRECATED] Install the IPython kernel spec directory for this Python."""
    kernel_spec_manager = Instance(KernelSpecManager)

    def _kernel_spec_manager_default(self) -> KernelSpecManager:  # pragma: no cover
        return KernelSpecManager(data_dir=self.data_dir)

    user = Bool(
        False,
        config=True,
        help="""
        Try to install the kernel spec to the per-user directory instead of
        the system or environment directory.
        """,
    )

    flags = {
        "user": (
            {"InstallNativeKernelSpec": {"user": True}},
            "Install to the per-user kernel registry",
        ),
        "debug": base_flags["debug"],
    }

    def start(self) -> None:  # pragma: no cover
        """Start the application."""
        self.log.warning(
            "`jupyter kernelspec install-self` is DEPRECATED as of 4.0."
            " You probably want `ipython kernel install` to install the IPython kernelspec."
        )
        try:
            from ipykernel import kernelspec
        except ModuleNotFoundError:
            print("ipykernel not available, can't install its spec.", file=sys.stderr)
            self.exit(1)
        try:
            kernelspec.install(self.kernel_spec_manager, user=self.user)
        except OSError as e:
            if e.errno == errno.EACCES:
                print(e, file=sys.stderr)
                if not self.user:
                    print(
                        "Perhaps you want to install with `sudo` or `--user`?",
                        file=sys.stderr,
                    )
                self.exit(1)
            self.exit(e)  # type:ignore[arg-type]


class ListProvisioners(JupyterApp):
    """An app to list provisioners."""

    version = __version__
    description = """List available provisioners for use in kernel specifications."""

    def start(self) -> None:
        """Start the application."""
        kfp = KernelProvisionerFactory.instance(parent=self)
        print("Available kernel provisioners:")
        provisioners = kfp.get_provisioner_entries()

        # pad to width of longest kernel name
        name_len = len(sorted(provisioners, key=lambda name: len(name))[-1])

        for name in sorted(provisioners):
            print(f"  {name.ljust(name_len)}    {provisioners[name]}")


class KernelSpecApp(Application):
    """An app to manage kernel specs."""

    version = __version__
    name = "jupyter kernelspec"
    description = """Manage Jupyter kernel specifications."""

    subcommands = Dict(
        {
            "list": (ListKernelSpecs, ListKernelSpecs.description.splitlines()[0]),
            "install": (
                InstallKernelSpec,
                InstallKernelSpec.description.splitlines()[0],
            ),
            "uninstall": (RemoveKernelSpec, "Alias for remove"),
            "remove": (RemoveKernelSpec, RemoveKernelSpec.description.splitlines()[0]),
            "install-self": (
                InstallNativeKernelSpec,
                InstallNativeKernelSpec.description.splitlines()[0],
            ),
            "provisioners": (ListProvisioners, ListProvisioners.description.splitlines()[0]),
        }
    )

    aliases = {}
    flags = {}

    def start(self) -> None:
        """Start the application."""
        if self.subapp is None:
            print("No subcommand specified. Must specify one of: %s" % list(self.subcommands))
            print()
            self.print_description()
            self.print_subcommands()
            self.exit(1)
        else:
            return self.subapp.start()


if __name__ == "__main__":
    KernelSpecApp.launch_instance()

# === NexusCore/openenv\Lib\site-packages\urllib3\fields.py ===
from __future__ import annotations

import email.utils
import mimetypes
import typing

_TYPE_FIELD_VALUE = typing.Union[str, bytes]
_TYPE_FIELD_VALUE_TUPLE = typing.Union[
    _TYPE_FIELD_VALUE,
    tuple[str, _TYPE_FIELD_VALUE],
    tuple[str, _TYPE_FIELD_VALUE, str],
]


def guess_content_type(
    filename: str | None, default: str = "application/octet-stream"
) -> str:
    """
    Guess the "Content-Type" of a file.

    :param filename:
        The filename to guess the "Content-Type" of using :mod:`mimetypes`.
    :param default:
        If no "Content-Type" can be guessed, default to `default`.
    """
    if filename:
        return mimetypes.guess_type(filename)[0] or default
    return default


def format_header_param_rfc2231(name: str, value: _TYPE_FIELD_VALUE) -> str:
    """
    Helper function to format and quote a single header parameter using the
    strategy defined in RFC 2231.

    Particularly useful for header parameters which might contain
    non-ASCII values, like file names. This follows
    `RFC 2388 Section 4.4 <https://tools.ietf.org/html/rfc2388#section-4.4>`_.

    :param name:
        The name of the parameter, a string expected to be ASCII only.
    :param value:
        The value of the parameter, provided as ``bytes`` or `str``.
    :returns:
        An RFC-2231-formatted unicode string.

    .. deprecated:: 2.0.0
        Will be removed in urllib3 v2.1.0. This is not valid for
        ``multipart/form-data`` header parameters.
    """
    import warnings

    warnings.warn(
        "'format_header_param_rfc2231' is deprecated and will be "
        "removed in urllib3 v2.1.0. This is not valid for "
        "multipart/form-data header parameters.",
        DeprecationWarning,
        stacklevel=2,
    )

    if isinstance(value, bytes):
        value = value.decode("utf-8")

    if not any(ch in value for ch in '"\\\r\n'):
        result = f'{name}="{value}"'
        try:
            result.encode("ascii")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        else:
            return result

    value = email.utils.encode_rfc2231(value, "utf-8")
    value = f"{name}*={value}"

    return value


def format_multipart_header_param(name: str, value: _TYPE_FIELD_VALUE) -> str:
    """
    Format and quote a single multipart header parameter.

    This follows the `WHATWG HTML Standard`_ as of 2021/06/10, matching
    the behavior of current browser and curl versions. Values are
    assumed to be UTF-8. The ``\\n``, ``\\r``, and ``"`` characters are
    percent encoded.

    .. _WHATWG HTML Standard:
        https://html.spec.whatwg.org/multipage/
        form-control-infrastructure.html#multipart-form-data

    :param name:
        The name of the parameter, an ASCII-only ``str``.
    :param value:
        The value of the parameter, a ``str`` or UTF-8 encoded
        ``bytes``.
    :returns:
        A string ``name="value"`` with the escaped value.

    .. versionchanged:: 2.0.0
        Matches the WHATWG HTML Standard as of 2021/06/10. Control
        characters are no longer percent encoded.

    .. versionchanged:: 2.0.0
        Renamed from ``format_header_param_html5`` and
        ``format_header_param``. The old names will be removed in
        urllib3 v2.1.0.
    """
    if isinstance(value, bytes):
        value = value.decode("utf-8")

    # percent encode \n \r "
    value = value.translate({10: "%0A", 13: "%0D", 34: "%22"})
    return f'{name}="{value}"'


def format_header_param_html5(name: str, value: _TYPE_FIELD_VALUE) -> str:
    """
    .. deprecated:: 2.0.0
        Renamed to :func:`format_multipart_header_param`. Will be
        removed in urllib3 v2.1.0.
    """
    import warnings

    warnings.warn(
        "'format_header_param_html5' has been renamed to "
        "'format_multipart_header_param'. The old name will be "
        "removed in urllib3 v2.1.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    return format_multipart_header_param(name, value)


def format_header_param(name: str, value: _TYPE_FIELD_VALUE) -> str:
    """
    .. deprecated:: 2.0.0
        Renamed to :func:`format_multipart_header_param`. Will be
        removed in urllib3 v2.1.0.
    """
    import warnings

    warnings.warn(
        "'format_header_param' has been renamed to "
        "'format_multipart_header_param'. The old name will be "
        "removed in urllib3 v2.1.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    return format_multipart_header_param(name, value)


class RequestField:
    """
    A data container for request body parameters.

    :param name:
        The name of this request field. Must be unicode.
    :param data:
        The data/value body.
    :param filename:
        An optional filename of the request field. Must be unicode.
    :param headers:
        An optional dict-like object of headers to initially use for the field.

    .. versionchanged:: 2.0.0
        The ``header_formatter`` parameter is deprecated and will
        be removed in urllib3 v2.1.0.
    """

    def __init__(
        self,
        name: str,
        data: _TYPE_FIELD_VALUE,
        filename: str | None = None,
        headers: typing.Mapping[str, str] | None = None,
        header_formatter: typing.Callable[[str, _TYPE_FIELD_VALUE], str] | None = None,
    ):
        self._name = name
        self._filename = filename
        self.data = data
        self.headers: dict[str, str | None] = {}
        if headers:
            self.headers = dict(headers)

        if header_formatter is not None:
            import warnings

            warnings.warn(
                "The 'header_formatter' parameter is deprecated and "
                "will be removed in urllib3 v2.1.0.",
                DeprecationWarning,
                stacklevel=2,
            )
            self.header_formatter = header_formatter
        else:
            self.header_formatter = format_multipart_header_param

    @classmethod
    def from_tuples(
        cls,
        fieldname: str,
        value: _TYPE_FIELD_VALUE_TUPLE,
        header_formatter: typing.Callable[[str, _TYPE_FIELD_VALUE], str] | None = None,
    ) -> RequestField:
        """
        A :class:`~urllib3.fields.RequestField` factory from old-style tuple parameters.

        Supports constructing :class:`~urllib3.fields.RequestField` from
        parameter of key/value strings AND key/filetuple. A filetuple is a
        (filename, data, MIME type) tuple where the MIME type is optional.
        For example::

            'foo': 'bar',
            'fakefile': ('foofile.txt', 'contents of foofile'),
            'realfile': ('barfile.txt', open('realfile').read()),
            'typedfile': ('bazfile.bin', open('bazfile').read(), 'image/jpeg'),
            'nonamefile': 'contents of nonamefile field',

        Field names and filenames must be unicode.
        """
        filename: str | None
        content_type: str | None
        data: _TYPE_FIELD_VALUE

        if isinstance(value, tuple):
            if len(value) == 3:
                filename, data, content_type = value
            else:
                filename, data = value
                content_type = guess_content_type(filename)
        else:
            filename = None
            content_type = None
            data = value

        request_param = cls(
            fieldname, data, filename=filename, header_formatter=header_formatter
        )
        request_param.make_multipart(content_type=content_type)

        return request_param

    def _render_part(self, name: str, value: _TYPE_FIELD_VALUE) -> str:
        """
        Override this method to change how each multipart header
        parameter is formatted. By default, this calls
        :func:`format_multipart_header_param`.

        :param name:
            The name of the parameter, an ASCII-only ``str``.
        :param value:
            The value of the parameter, a ``str`` or UTF-8 encoded
            ``bytes``.

        :meta public:
        """
        return self.header_formatter(name, value)

    def _render_parts(
        self,
        header_parts: (
            dict[str, _TYPE_FIELD_VALUE | None]
            | typing.Sequence[tuple[str, _TYPE_FIELD_VALUE | None]]
        ),
    ) -> str:
        """
        Helper function to format and quote a single header.

        Useful for single headers that are composed of multiple items. E.g.,
        'Content-Disposition' fields.

        :param header_parts:
            A sequence of (k, v) tuples or a :class:`dict` of (k, v) to format
            as `k1="v1"; k2="v2"; ...`.
        """
        iterable: typing.Iterable[tuple[str, _TYPE_FIELD_VALUE | None]]

        parts = []
        if isinstance(header_parts, dict):
            iterable = header_parts.items()
        else:
            iterable = header_parts

        for name, value in iterable:
            if value is not None:
                parts.append(self._render_part(name, value))

        return "; ".join(parts)

    def render_headers(self) -> str:
        """
        Renders the headers for this request field.
        """
        lines = []

        sort_keys = ["Content-Disposition", "Content-Type", "Content-Location"]
        for sort_key in sort_keys:
            if self.headers.get(sort_key, False):
                lines.append(f"{sort_key}: {self.headers[sort_key]}")

        for header_name, header_value in self.headers.items():
            if header_name not in sort_keys:
                if header_value:
                    lines.append(f"{header_name}: {header_value}")

        lines.append("\r\n")
        return "\r\n".join(lines)

    def make_multipart(
        self,
        content_disposition: str | None = None,
        content_type: str | None = None,
        content_location: str | None = None,
    ) -> None:
        """
        Makes this request field into a multipart request field.

        This method overrides "Content-Disposition", "Content-Type" and
        "Content-Location" headers to the request parameter.

        :param content_disposition:
            The 'Content-Disposition' of the request body. Defaults to 'form-data'
        :param content_type:
            The 'Content-Type' of the request body.
        :param content_location:
            The 'Content-Location' of the request body.

        """
        content_disposition = (content_disposition or "form-data") + "; ".join(
            [
                "",
                self._render_parts(
                    (("name", self._name), ("filename", self._filename))
                ),
            ]
        )

        self.headers["Content-Disposition"] = content_disposition
        self.headers["Content-Type"] = content_type
        self.headers["Content-Location"] = content_location

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\discuss_service\transports\grpc_asyncio.py ===
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
from typing import Awaitable, Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, grpc_helpers_async
from google.api_core import retry_async as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta.types import discuss_service

from .base import DEFAULT_CLIENT_INFO, DiscussServiceTransport
from .grpc import DiscussServiceGrpcTransport


class DiscussServiceGrpcAsyncIOTransport(DiscussServiceTransport):
    """gRPC AsyncIO backend transport for DiscussService.

    An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _grpc_channel: aio.Channel
    _stubs: Dict[str, Callable] = {}

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> aio.Channel:
        """Create and return a gRPC AsyncIO channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            aio.Channel: A gRPC AsyncIO channel object.
        """

        return grpc_helpers_async.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[aio.Channel, Callable[..., aio.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
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
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            channel (Optional[Union[aio.Channel, Callable[..., aio.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, aio.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None
        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @property
    def grpc_channel(self) -> aio.Channel:
        """Create the channel designed to connect to this service.

        This property caches on the instance; repeated calls return
        the same channel.
        """
        # Return the channel from cache.
        return self._grpc_channel

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        Awaitable[discuss_service.GenerateMessageResponse],
    ]:
        r"""Return a callable for the generate message method over gRPC.

        Generates a response from the model given an input
        ``MessagePrompt``.

        Returns:
            Callable[[~.GenerateMessageRequest],
                    Awaitable[~.GenerateMessageResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_message" not in self._stubs:
            self._stubs["generate_message"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.DiscussService/GenerateMessage",
                request_serializer=discuss_service.GenerateMessageRequest.serialize,
                response_deserializer=discuss_service.GenerateMessageResponse.deserialize,
            )
        return self._stubs["generate_message"]

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        Awaitable[discuss_service.CountMessageTokensResponse],
    ]:
        r"""Return a callable for the count message tokens method over gRPC.

        Runs a model's tokenizer on a string and returns the
        token count.

        Returns:
            Callable[[~.CountMessageTokensRequest],
                    Awaitable[~.CountMessageTokensResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_message_tokens" not in self._stubs:
            self._stubs["count_message_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.DiscussService/CountMessageTokens",
                request_serializer=discuss_service.CountMessageTokensRequest.serialize,
                response_deserializer=discuss_service.CountMessageTokensResponse.deserialize,
            )
        return self._stubs["count_message_tokens"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.generate_message: gapic_v1.method_async.wrap_method(
                self.generate_message,
                default_retry=retries.AsyncRetry(
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
            self.count_message_tokens: gapic_v1.method_async.wrap_method(
                self.count_message_tokens,
                default_retry=retries.AsyncRetry(
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
        return self.grpc_channel.close()


__all__ = ("DiscussServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\httpcore\_async\socks_proxy.py ===
from __future__ import annotations

import logging
import ssl

import socksio

from .._backends.auto import AutoBackend
from .._backends.base import AsyncNetworkBackend, AsyncNetworkStream
from .._exceptions import ConnectionNotAvailable, ProxyError
from .._models import URL, Origin, Request, Response, enforce_bytes, enforce_url
from .._ssl import default_ssl_context
from .._synchronization import AsyncLock
from .._trace import Trace
from .connection_pool import AsyncConnectionPool
from .http11 import AsyncHTTP11Connection
from .interfaces import AsyncConnectionInterface

logger = logging.getLogger("httpcore.socks")


AUTH_METHODS = {
    b"\x00": "NO AUTHENTICATION REQUIRED",
    b"\x01": "GSSAPI",
    b"\x02": "USERNAME/PASSWORD",
    b"\xff": "NO ACCEPTABLE METHODS",
}

REPLY_CODES = {
    b"\x00": "Succeeded",
    b"\x01": "General SOCKS server failure",
    b"\x02": "Connection not allowed by ruleset",
    b"\x03": "Network unreachable",
    b"\x04": "Host unreachable",
    b"\x05": "Connection refused",
    b"\x06": "TTL expired",
    b"\x07": "Command not supported",
    b"\x08": "Address type not supported",
}


async def _init_socks5_connection(
    stream: AsyncNetworkStream,
    *,
    host: bytes,
    port: int,
    auth: tuple[bytes, bytes] | None = None,
) -> None:
    conn = socksio.socks5.SOCKS5Connection()

    # Auth method request
    auth_method = (
        socksio.socks5.SOCKS5AuthMethod.NO_AUTH_REQUIRED
        if auth is None
        else socksio.socks5.SOCKS5AuthMethod.USERNAME_PASSWORD
    )
    conn.send(socksio.socks5.SOCKS5AuthMethodsRequest([auth_method]))
    outgoing_bytes = conn.data_to_send()
    await stream.write(outgoing_bytes)

    # Auth method response
    incoming_bytes = await stream.read(max_bytes=4096)
    response = conn.receive_data(incoming_bytes)
    assert isinstance(response, socksio.socks5.SOCKS5AuthReply)
    if response.method != auth_method:
        requested = AUTH_METHODS.get(auth_method, "UNKNOWN")
        responded = AUTH_METHODS.get(response.method, "UNKNOWN")
        raise ProxyError(
            f"Requested {requested} from proxy server, but got {responded}."
        )

    if response.method == socksio.socks5.SOCKS5AuthMethod.USERNAME_PASSWORD:
        # Username/password request
        assert auth is not None
        username, password = auth
        conn.send(socksio.socks5.SOCKS5UsernamePasswordRequest(username, password))
        outgoing_bytes = conn.data_to_send()
        await stream.write(outgoing_bytes)

        # Username/password response
        incoming_bytes = await stream.read(max_bytes=4096)
        response = conn.receive_data(incoming_bytes)
        assert isinstance(response, socksio.socks5.SOCKS5UsernamePasswordReply)
        if not response.success:
            raise ProxyError("Invalid username/password")

    # Connect request
    conn.send(
        socksio.socks5.SOCKS5CommandRequest.from_address(
            socksio.socks5.SOCKS5Command.CONNECT, (host, port)
        )
    )
    outgoing_bytes = conn.data_to_send()
    await stream.write(outgoing_bytes)

    # Connect response
    incoming_bytes = await stream.read(max_bytes=4096)
    response = conn.receive_data(incoming_bytes)
    assert isinstance(response, socksio.socks5.SOCKS5Reply)
    if response.reply_code != socksio.socks5.SOCKS5ReplyCode.SUCCEEDED:
        reply_code = REPLY_CODES.get(response.reply_code, "UNKOWN")
        raise ProxyError(f"Proxy Server could not connect: {reply_code}.")


class AsyncSOCKSProxy(AsyncConnectionPool):  # pragma: nocover
    """
    A connection pool that sends requests via an HTTP proxy.
    """

    def __init__(
        self,
        proxy_url: URL | bytes | str,
        proxy_auth: tuple[bytes | str, bytes | str] | None = None,
        ssl_context: ssl.SSLContext | None = None,
        max_connections: int | None = 10,
        max_keepalive_connections: int | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        retries: int = 0,
        network_backend: AsyncNetworkBackend | None = None,
    ) -> None:
        """
        A connection pool for making HTTP requests.

        Parameters:
            proxy_url: The URL to use when connecting to the proxy server.
                For example `"http://127.0.0.1:8080/"`.
            ssl_context: An SSL context to use for verifying connections.
                If not specified, the default `httpcore.default_ssl_context()`
                will be used.
            max_connections: The maximum number of concurrent HTTP connections that
                the pool should allow. Any attempt to send a request on a pool that
                would exceed this amount will block until a connection is available.
            max_keepalive_connections: The maximum number of idle HTTP connections
                that will be maintained in the pool.
            keepalive_expiry: The duration in seconds that an idle HTTP connection
                may be maintained for before being expired from the pool.
            http1: A boolean indicating if HTTP/1.1 requests should be supported
                by the connection pool. Defaults to True.
            http2: A boolean indicating if HTTP/2 requests should be supported by
                the connection pool. Defaults to False.
            retries: The maximum number of retries when trying to establish
                a connection.
            local_address: Local address to connect from. Can also be used to
                connect using a particular address family. Using
                `local_address="0.0.0.0"` will connect using an `AF_INET` address
                (IPv4), while using `local_address="::"` will connect using an
                `AF_INET6` address (IPv6).
            uds: Path to a Unix Domain Socket to use instead of TCP sockets.
            network_backend: A backend instance to use for handling network I/O.
        """
        super().__init__(
            ssl_context=ssl_context,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            http1=http1,
            http2=http2,
            network_backend=network_backend,
            retries=retries,
        )
        self._ssl_context = ssl_context
        self._proxy_url = enforce_url(proxy_url, name="proxy_url")
        if proxy_auth is not None:
            username, password = proxy_auth
            username_bytes = enforce_bytes(username, name="proxy_auth")
            password_bytes = enforce_bytes(password, name="proxy_auth")
            self._proxy_auth: tuple[bytes, bytes] | None = (
                username_bytes,
                password_bytes,
            )
        else:
            self._proxy_auth = None

    def create_connection(self, origin: Origin) -> AsyncConnectionInterface:
        return AsyncSocks5Connection(
            proxy_origin=self._proxy_url.origin,
            remote_origin=origin,
            proxy_auth=self._proxy_auth,
            ssl_context=self._ssl_context,
            keepalive_expiry=self._keepalive_expiry,
            http1=self._http1,
            http2=self._http2,
            network_backend=self._network_backend,
        )


class AsyncSocks5Connection(AsyncConnectionInterface):
    def __init__(
        self,
        proxy_origin: Origin,
        remote_origin: Origin,
        proxy_auth: tuple[bytes, bytes] | None = None,
        ssl_context: ssl.SSLContext | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        network_backend: AsyncNetworkBackend | None = None,
    ) -> None:
        self._proxy_origin = proxy_origin
        self._remote_origin = remote_origin
        self._proxy_auth = proxy_auth
        self._ssl_context = ssl_context
        self._keepalive_expiry = keepalive_expiry
        self._http1 = http1
        self._http2 = http2

        self._network_backend: AsyncNetworkBackend = (
            AutoBackend() if network_backend is None else network_backend
        )
        self._connect_lock = AsyncLock()
        self._connection: AsyncConnectionInterface | None = None
        self._connect_failed = False

    async def handle_async_request(self, request: Request) -> Response:
        timeouts = request.extensions.get("timeout", {})
        sni_hostname = request.extensions.get("sni_hostname", None)
        timeout = timeouts.get("connect", None)

        async with self._connect_lock:
            if self._connection is None:
                try:
                    # Connect to the proxy
                    kwargs = {
                        "host": self._proxy_origin.host.decode("ascii"),
                        "port": self._proxy_origin.port,
                        "timeout": timeout,
                    }
                    async with Trace("connect_tcp", logger, request, kwargs) as trace:
                        stream = await self._network_backend.connect_tcp(**kwargs)
                        trace.return_value = stream

                    # Connect to the remote host using socks5
                    kwargs = {
                        "stream": stream,
                        "host": self._remote_origin.host.decode("ascii"),
                        "port": self._remote_origin.port,
                        "auth": self._proxy_auth,
                    }
                    async with Trace(
                        "setup_socks5_connection", logger, request, kwargs
                    ) as trace:
                        await _init_socks5_connection(**kwargs)
                        trace.return_value = stream

                    # Upgrade the stream to SSL
                    if self._remote_origin.scheme == b"https":
                        ssl_context = (
                            default_ssl_context()
                            if self._ssl_context is None
                            else self._ssl_context
                        )
                        alpn_protocols = (
                            ["http/1.1", "h2"] if self._http2 else ["http/1.1"]
                        )
                        ssl_context.set_alpn_protocols(alpn_protocols)

                        kwargs = {
                            "ssl_context": ssl_context,
                            "server_hostname": sni_hostname
                            or self._remote_origin.host.decode("ascii"),
                            "timeout": timeout,
                        }
                        async with Trace("start_tls", logger, request, kwargs) as trace:
                            stream = await stream.start_tls(**kwargs)
                            trace.return_value = stream

                    # Determine if we should be using HTTP/1.1 or HTTP/2
                    ssl_object = stream.get_extra_info("ssl_object")
                    http2_negotiated = (
                        ssl_object is not None
                        and ssl_object.selected_alpn_protocol() == "h2"
                    )

                    # Create the HTTP/1.1 or HTTP/2 connection
                    if http2_negotiated or (
                        self._http2 and not self._http1
                    ):  # pragma: nocover
                        from .http2 import AsyncHTTP2Connection

                        self._connection = AsyncHTTP2Connection(
                            origin=self._remote_origin,
                            stream=stream,
                            keepalive_expiry=self._keepalive_expiry,
                        )
                    else:
                        self._connection = AsyncHTTP11Connection(
                            origin=self._remote_origin,
                            stream=stream,
                            keepalive_expiry=self._keepalive_expiry,
                        )
                except Exception as exc:
                    self._connect_failed = True
                    raise exc
            elif not self._connection.is_available():  # pragma: nocover
                raise ConnectionNotAvailable()

        return await self._connection.handle_async_request(request)

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._remote_origin

    async def aclose(self) -> None:
        if self._connection is not None:
            await self._connection.aclose()

    def is_available(self) -> bool:
        if self._connection is None:  # pragma: nocover
            # If HTTP/2 support is enabled, and the resulting connection could
            # end up as HTTP/2 then we should indicate the connection as being
            # available to service multiple requests.
            return (
                self._http2
                and (self._remote_origin.scheme == b"https" or not self._http1)
                and not self._connect_failed
            )
        return self._connection.is_available()

    def has_expired(self) -> bool:
        if self._connection is None:  # pragma: nocover
            return self._connect_failed
        return self._connection.has_expired()

    def is_idle(self) -> bool:
        if self._connection is None:  # pragma: nocover
            return self._connect_failed
        return self._connection.is_idle()

    def is_closed(self) -> bool:
        if self._connection is None:  # pragma: nocover
            return self._connect_failed
        return self._connection.is_closed()

    def info(self) -> str:
        if self._connection is None:  # pragma: nocover
            return "CONNECTION FAILED" if self._connect_failed else "CONNECTING"
        return self._connection.info()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{self.info()}]>"

# === NexusCore/openenv\Lib\site-packages\httpcore\_sync\socks_proxy.py ===
from __future__ import annotations

import logging
import ssl

import socksio

from .._backends.sync import SyncBackend
from .._backends.base import NetworkBackend, NetworkStream
from .._exceptions import ConnectionNotAvailable, ProxyError
from .._models import URL, Origin, Request, Response, enforce_bytes, enforce_url
from .._ssl import default_ssl_context
from .._synchronization import Lock
from .._trace import Trace
from .connection_pool import ConnectionPool
from .http11 import HTTP11Connection
from .interfaces import ConnectionInterface

logger = logging.getLogger("httpcore.socks")


AUTH_METHODS = {
    b"\x00": "NO AUTHENTICATION REQUIRED",
    b"\x01": "GSSAPI",
    b"\x02": "USERNAME/PASSWORD",
    b"\xff": "NO ACCEPTABLE METHODS",
}

REPLY_CODES = {
    b"\x00": "Succeeded",
    b"\x01": "General SOCKS server failure",
    b"\x02": "Connection not allowed by ruleset",
    b"\x03": "Network unreachable",
    b"\x04": "Host unreachable",
    b"\x05": "Connection refused",
    b"\x06": "TTL expired",
    b"\x07": "Command not supported",
    b"\x08": "Address type not supported",
}


def _init_socks5_connection(
    stream: NetworkStream,
    *,
    host: bytes,
    port: int,
    auth: tuple[bytes, bytes] | None = None,
) -> None:
    conn = socksio.socks5.SOCKS5Connection()

    # Auth method request
    auth_method = (
        socksio.socks5.SOCKS5AuthMethod.NO_AUTH_REQUIRED
        if auth is None
        else socksio.socks5.SOCKS5AuthMethod.USERNAME_PASSWORD
    )
    conn.send(socksio.socks5.SOCKS5AuthMethodsRequest([auth_method]))
    outgoing_bytes = conn.data_to_send()
    stream.write(outgoing_bytes)

    # Auth method response
    incoming_bytes = stream.read(max_bytes=4096)
    response = conn.receive_data(incoming_bytes)
    assert isinstance(response, socksio.socks5.SOCKS5AuthReply)
    if response.method != auth_method:
        requested = AUTH_METHODS.get(auth_method, "UNKNOWN")
        responded = AUTH_METHODS.get(response.method, "UNKNOWN")
        raise ProxyError(
            f"Requested {requested} from proxy server, but got {responded}."
        )

    if response.method == socksio.socks5.SOCKS5AuthMethod.USERNAME_PASSWORD:
        # Username/password request
        assert auth is not None
        username, password = auth
        conn.send(socksio.socks5.SOCKS5UsernamePasswordRequest(username, password))
        outgoing_bytes = conn.data_to_send()
        stream.write(outgoing_bytes)

        # Username/password response
        incoming_bytes = stream.read(max_bytes=4096)
        response = conn.receive_data(incoming_bytes)
        assert isinstance(response, socksio.socks5.SOCKS5UsernamePasswordReply)
        if not response.success:
            raise ProxyError("Invalid username/password")

    # Connect request
    conn.send(
        socksio.socks5.SOCKS5CommandRequest.from_address(
            socksio.socks5.SOCKS5Command.CONNECT, (host, port)
        )
    )
    outgoing_bytes = conn.data_to_send()
    stream.write(outgoing_bytes)

    # Connect response
    incoming_bytes = stream.read(max_bytes=4096)
    response = conn.receive_data(incoming_bytes)
    assert isinstance(response, socksio.socks5.SOCKS5Reply)
    if response.reply_code != socksio.socks5.SOCKS5ReplyCode.SUCCEEDED:
        reply_code = REPLY_CODES.get(response.reply_code, "UNKOWN")
        raise ProxyError(f"Proxy Server could not connect: {reply_code}.")


class SOCKSProxy(ConnectionPool):  # pragma: nocover
    """
    A connection pool that sends requests via an HTTP proxy.
    """

    def __init__(
        self,
        proxy_url: URL | bytes | str,
        proxy_auth: tuple[bytes | str, bytes | str] | None = None,
        ssl_context: ssl.SSLContext | None = None,
        max_connections: int | None = 10,
        max_keepalive_connections: int | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        retries: int = 0,
        network_backend: NetworkBackend | None = None,
    ) -> None:
        """
        A connection pool for making HTTP requests.

        Parameters:
            proxy_url: The URL to use when connecting to the proxy server.
                For example `"http://127.0.0.1:8080/"`.
            ssl_context: An SSL context to use for verifying connections.
                If not specified, the default `httpcore.default_ssl_context()`
                will be used.
            max_connections: The maximum number of concurrent HTTP connections that
                the pool should allow. Any attempt to send a request on a pool that
                would exceed this amount will block until a connection is available.
            max_keepalive_connections: The maximum number of idle HTTP connections
                that will be maintained in the pool.
            keepalive_expiry: The duration in seconds that an idle HTTP connection
                may be maintained for before being expired from the pool.
            http1: A boolean indicating if HTTP/1.1 requests should be supported
                by the connection pool. Defaults to True.
            http2: A boolean indicating if HTTP/2 requests should be supported by
                the connection pool. Defaults to False.
            retries: The maximum number of retries when trying to establish
                a connection.
            local_address: Local address to connect from. Can also be used to
                connect using a particular address family. Using
                `local_address="0.0.0.0"` will connect using an `AF_INET` address
                (IPv4), while using `local_address="::"` will connect using an
                `AF_INET6` address (IPv6).
            uds: Path to a Unix Domain Socket to use instead of TCP sockets.
            network_backend: A backend instance to use for handling network I/O.
        """
        super().__init__(
            ssl_context=ssl_context,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            http1=http1,
            http2=http2,
            network_backend=network_backend,
            retries=retries,
        )
        self._ssl_context = ssl_context
        self._proxy_url = enforce_url(proxy_url, name="proxy_url")
        if proxy_auth is not None:
            username, password = proxy_auth
            username_bytes = enforce_bytes(username, name="proxy_auth")
            password_bytes = enforce_bytes(password, name="proxy_auth")
            self._proxy_auth: tuple[bytes, bytes] | None = (
                username_bytes,
                password_bytes,
            )
        else:
            self._proxy_auth = None

    def create_connection(self, origin: Origin) -> ConnectionInterface:
        return Socks5Connection(
            proxy_origin=self._proxy_url.origin,
            remote_origin=origin,
            proxy_auth=self._proxy_auth,
            ssl_context=self._ssl_context,
            keepalive_expiry=self._keepalive_expiry,
            http1=self._http1,
            http2=self._http2,
            network_backend=self._network_backend,
        )


class Socks5Connection(ConnectionInterface):
    def __init__(
        self,
        proxy_origin: Origin,
        remote_origin: Origin,
        proxy_auth: tuple[bytes, bytes] | None = None,
        ssl_context: ssl.SSLContext | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        network_backend: NetworkBackend | None = None,
    ) -> None:
        self._proxy_origin = proxy_origin
        self._remote_origin = remote_origin
        self._proxy_auth = proxy_auth
        self._ssl_context = ssl_context
        self._keepalive_expiry = keepalive_expiry
        self._http1 = http1
        self._http2 = http2

        self._network_backend: NetworkBackend = (
            SyncBackend() if network_backend is None else network_backend
        )
        self._connect_lock = Lock()
        self._connection: ConnectionInterface | None = None
        self._connect_failed = False

    def handle_request(self, request: Request) -> Response:
        timeouts = request.extensions.get("timeout", {})
        sni_hostname = request.extensions.get("sni_hostname", None)
        timeout = timeouts.get("connect", None)

        with self._connect_lock:
            if self._connection is None:
                try:
                    # Connect to the proxy
                    kwargs = {
                        "host": self._proxy_origin.host.decode("ascii"),
                        "port": self._proxy_origin.port,
                        "timeout": timeout,
                    }
                    with Trace("connect_tcp", logger, request, kwargs) as trace:
                        stream = self._network_backend.connect_tcp(**kwargs)
                        trace.return_value = stream

                    # Connect to the remote host using socks5
                    kwargs = {
                        "stream": stream,
                        "host": self._remote_origin.host.decode("ascii"),
                        "port": self._remote_origin.port,
                        "auth": self._proxy_auth,
                    }
                    with Trace(
                        "setup_socks5_connection", logger, request, kwargs
                    ) as trace:
                        _init_socks5_connection(**kwargs)
                        trace.return_value = stream

                    # Upgrade the stream to SSL
                    if self._remote_origin.scheme == b"https":
                        ssl_context = (
                            default_ssl_context()
                            if self._ssl_context is None
                            else self._ssl_context
                        )
                        alpn_protocols = (
                            ["http/1.1", "h2"] if self._http2 else ["http/1.1"]
                        )
                        ssl_context.set_alpn_protocols(alpn_protocols)

                        kwargs = {
                            "ssl_context": ssl_context,
                            "server_hostname": sni_hostname
                            or self._remote_origin.host.decode("ascii"),
                            "timeout": timeout,
                        }
                        with Trace("start_tls", logger, request, kwargs) as trace:
                            stream = stream.start_tls(**kwargs)
                            trace.return_value = stream

                    # Determine if we should be using HTTP/1.1 or HTTP/2
                    ssl_object = stream.get_extra_info("ssl_object")
                    http2_negotiated = (
                        ssl_object is not None
                        and ssl_object.selected_alpn_protocol() == "h2"
                    )

                    # Create the HTTP/1.1 or HTTP/2 connection
                    if http2_negotiated or (
                        self._http2 and not self._http1
                    ):  # pragma: nocover
                        from .http2 import HTTP2Connection

                        self._connection = HTTP2Connection(
                            origin=self._remote_origin,
                            stream=stream,
                            keepalive_expiry=self._keepalive_expiry,
                        )
                    else:
                        self._connection = HTTP11Connection(
                            origin=self._remote_origin,
                            stream=stream,
                            keepalive_expiry=self._keepalive_expiry,
                        )
                except Exception as exc:
                    self._connect_failed = True
                    raise exc
            elif not self._connection.is_available():  # pragma: nocover
                raise ConnectionNotAvailable()

        return self._connection.handle_request(request)

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._remote_origin

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()

    def is_available(self) -> bool:
        if self._connection is None:  # pragma: nocover
            # If HTTP/2 support is enabled, and the resulting connection could
            # end up as HTTP/2 then we should indicate the connection as being
            # available to service multiple requests.
            return (
                self._http2
                and (self._remote_origin.scheme == b"https" or not self._http1)
                and not self._connect_failed
            )
        return self._connection.is_available()

    def has_expired(self) -> bool:
        if self._connection is None:  # pragma: nocover
            return self._connect_failed
        return self._connection.has_expired()

    def is_idle(self) -> bool:
        if self._connection is None:  # pragma: nocover
            return self._connect_failed
        return self._connection.is_idle()

    def is_closed(self) -> bool:
        if self._connection is None:  # pragma: nocover
            return self._connect_failed
        return self._connection.is_closed()

    def info(self) -> str:
        if self._connection is None:  # pragma: nocover
            return "CONNECTION FAILED" if self._connect_failed else "CONNECTING"
        return self._connection.info()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{self.info()}]>"

# === NexusCore/openenv\Lib\site-packages\IPython\core\usage.py ===
# -*- coding: utf-8 -*-
"""Usage information for the main IPython applications.
"""
#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#  Copyright (C) 2001-2007 Fernando Perez. <fperez@colorado.edu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import sys
from IPython.core import release

cl_usage = """\
=========
 IPython
=========

Tools for Interactive Computing in Python
=========================================

    A Python shell with automatic history (input and output), dynamic object
    introspection, easier configuration, command completion, access to the
    system shell and more.  IPython can also be embedded in running programs.


Usage

    ipython [subcommand] [options] [-c cmd | -m mod | file] [--] [arg] ...

    If invoked with no options, it executes the file and exits, passing the
    remaining arguments to the script, just as if you had specified the same
    command with python. You may need to specify `--` before args to be passed
    to the script, to prevent IPython from attempting to parse them. If you
    specify the option `-i` before the filename, it will enter an interactive
    IPython session after running the script, rather than exiting. Files ending
    in .py will be treated as normal Python, but files ending in .ipy can
    contain special IPython syntax (magic commands, shell expansions, etc.).

    Almost all configuration in IPython is available via the command-line. Do
    `ipython --help-all` to see all available options.  For persistent
    configuration, look into your `ipython_config.py` configuration file for
    details.

    This file is typically installed in the `IPYTHONDIR` directory, and there
    is a separate configuration directory for each profile. The default profile
    directory will be located in $IPYTHONDIR/profile_default. IPYTHONDIR
    defaults to to `$HOME/.ipython`.  For Windows users, $HOME resolves to
    C:\\Users\\YourUserName in most instances.

    To initialize a profile with the default configuration file, do::

      $> ipython profile create

    and start editing `IPYTHONDIR/profile_default/ipython_config.py`

    In IPython's documentation, we will refer to this directory as
    `IPYTHONDIR`, you can change its default location by creating an
    environment variable with this name and setting it to the desired path.

    For more information, see the manual available in HTML and PDF in your
    installation, or online at https://ipython.org/documentation.html.
"""

interactive_usage = """
IPython -- An enhanced Interactive Python
=========================================

IPython offers a fully compatible replacement for the standard Python
interpreter, with convenient shell features, special commands, command
history mechanism and output results caching.

At your system command line, type 'ipython -h' to see the command line
options available. This document only describes interactive features.

GETTING HELP
------------

Within IPython you have various way to access help:

  ?         -> Introduction and overview of IPython's features (this screen).
  object?   -> Details about 'object'.
  object??  -> More detailed, verbose information about 'object'.
  %quickref -> Quick reference of all IPython specific syntax and magics.
  help      -> Access Python's own help system.

If you are in terminal IPython you can quit this screen by pressing `q`.


MAIN FEATURES
-------------

* Access to the standard Python help with object docstrings and the Python
  manuals. Simply type 'help' (no quotes) to invoke it.

* Magic commands: type %magic for information on the magic subsystem.

* System command aliases, via the %alias command or the configuration file(s).

* Dynamic object information:

  Typing ?word or word? prints detailed information about an object. Certain
  long strings (code, etc.) get snipped in the center for brevity.

  Typing ??word or word?? gives access to the full information without
  snipping long strings. Strings that are longer than the screen are printed
  through the less pager.

  The ?/?? system gives access to the full source code for any object (if
  available), shows function prototypes and other useful information.

  If you just want to see an object's docstring, type '%pdoc object' (without
  quotes, and without % if you have automagic on).

* Tab completion in the local namespace:

  At any time, hitting tab will complete any available python commands or
  variable names, and show you a list of the possible completions if there's
  no unambiguous one. It will also complete filenames in the current directory.

* Search previous command history in multiple ways:

  - Start typing, and then use arrow keys up/down or (Ctrl-p/Ctrl-n) to search
    through the history items that match what you've typed so far.

  - Hit Ctrl-r: opens a search prompt. Begin typing and the system searches
    your history for lines that match what you've typed so far, completing as
    much as it can.

  - %hist: search history by index.

* Persistent command history across sessions.

* Logging of input with the ability to save and restore a working session.

* System shell with !. Typing !ls will run 'ls' in the current directory.

* The reload command does a 'deep' reload of a module: changes made to the
  module since you imported will actually be available without having to exit.

* Verbose and colored exception traceback printouts. See the magic xmode and
  xcolor functions for details (just type %magic).

* Input caching system:

  IPython offers numbered prompts (In/Out) with input and output caching. All
  input is saved and can be retrieved as variables (besides the usual arrow
  key recall).

  The following GLOBAL variables always exist (so don't overwrite them!):
  _i: stores previous input.
  _ii: next previous.
  _iii: next-next previous.
  _ih : a list of all input _ih[n] is the input from line n.

  Additionally, global variables named _i<n> are dynamically created (<n>
  being the prompt counter), such that _i<n> == _ih[<n>]

  For example, what you typed at prompt 14 is available as _i14 and _ih[14].

  You can create macros which contain multiple input lines from this history,
  for later re-execution, with the %macro function.

  The history function %hist allows you to see any part of your input history
  by printing a range of the _i variables. Note that inputs which contain
  magic functions (%) appear in the history with a prepended comment. This is
  because they aren't really valid Python code, so you can't exec them.

* Output caching system:

  For output that is returned from actions, a system similar to the input
  cache exists but using _ instead of _i. Only actions that produce a result
  (NOT assignments, for example) are cached. If you are familiar with
  Mathematica, IPython's _ variables behave exactly like Mathematica's %
  variables.

  The following GLOBAL variables always exist (so don't overwrite them!):
  _ (one underscore): previous output.
  __ (two underscores): next previous.
  ___ (three underscores): next-next previous.

  Global variables named _<n> are dynamically created (<n> being the prompt
  counter), such that the result of output <n> is always available as _<n>.

  Finally, a global dictionary named _oh exists with entries for all lines
  which generated output.

* Directory history:

  Your history of visited directories is kept in the global list _dh, and the
  magic %cd command can be used to go to any entry in that list.

* Auto-parentheses and auto-quotes (adapted from Nathan Gray's LazyPython)

  1. Auto-parentheses
        
     Callable objects (i.e. functions, methods, etc) can be invoked like
     this (notice the commas between the arguments)::
       
         In [1]: callable_ob arg1, arg2, arg3
       
     and the input will be translated to this::
       
         callable_ob(arg1, arg2, arg3)
       
     This feature is off by default (in rare cases it can produce
     undesirable side-effects), but you can activate it at the command-line
     by starting IPython with `--autocall 1`, set it permanently in your
     configuration file, or turn on at runtime with `%autocall 1`.

     You can force auto-parentheses by using '/' as the first character
     of a line.  For example::
       
          In [1]: /globals             # becomes 'globals()'
       
     Note that the '/' MUST be the first character on the line!  This
     won't work::
       
          In [2]: print /globals    # syntax error

     In most cases the automatic algorithm should work, so you should
     rarely need to explicitly invoke /. One notable exception is if you
     are trying to call a function with a list of tuples as arguments (the
     parenthesis will confuse IPython)::
       
          In [1]: zip (1,2,3),(4,5,6)  # won't work
       
     but this will work::
       
          In [2]: /zip (1,2,3),(4,5,6)
          ------> zip ((1,2,3),(4,5,6))
          Out[2]= [(1, 4), (2, 5), (3, 6)]

     IPython tells you that it has altered your command line by
     displaying the new command line preceded by -->.  e.g.::
       
          In [18]: callable list
          -------> callable (list)

  2. Auto-Quoting
    
     You can force auto-quoting of a function's arguments by using ',' as
     the first character of a line.  For example::
       
          In [1]: ,my_function /home/me   # becomes my_function("/home/me")

     If you use ';' instead, the whole argument is quoted as a single
     string (while ',' splits on whitespace)::
       
          In [2]: ,my_function a b c   # becomes my_function("a","b","c")
          In [3]: ;my_function a b c   # becomes my_function("a b c")

     Note that the ',' MUST be the first character on the line!  This
     won't work::
       
          In [4]: x = ,my_function /home/me    # syntax error
"""

interactive_usage_min =  """\
An enhanced console for Python.
Some of its features are:
- Tab completion in the local namespace.
- Logging of input, see command-line options.
- System shell escape via ! , eg !ls.
- Magic commands, starting with a % (like %ls, %pwd, %cd, etc.)
- Keeps track of locally defined variables via %who, %whos.
- Show object information with a ? eg ?x or x? (use ?? for more info).
"""

quick_reference = r"""
IPython -- An enhanced Interactive Python - Quick Reference Card
================================================================

obj?, obj??      : Get help, or more help for object (also works as
                   ?obj, ??obj).
?foo.*abc*       : List names in 'foo' containing 'abc' in them.
%magic           : Information about IPython's 'magic' % functions.

Magic functions are prefixed by % or %%, and typically take their arguments
without parentheses, quotes or even commas for convenience.  Line magics take a
single % and cell magics are prefixed with two %%.

Example magic function calls:

%alias d ls -F   : 'd' is now an alias for 'ls -F'
alias d ls -F    : Works if 'alias' not a python name
alist = %alias   : Get list of aliases to 'alist'
cd /usr/share    : Obvious. cd -<tab> to choose from visited dirs.
%cd??            : See help AND source for magic %cd
%timeit x=10     : time the 'x=10' statement with high precision.
%%timeit x=2**100
x**100           : time 'x**100' with a setup of 'x=2**100'; setup code is not
                   counted.  This is an example of a cell magic.

System commands:

!cp a.txt b/     : System command escape, calls os.system()
cp a.txt b/      : after %rehashx, most system commands work without !
cp ${f}.txt $bar : Variable expansion in magics and system commands
files = !ls /usr : Capture system command output
files.s, files.l, files.n: "a b c", ['a','b','c'], 'a\nb\nc'

History:

_i, _ii, _iii    : Previous, next previous, next next previous input
_i4, _ih[2:5]    : Input history line 4, lines 2-4
exec(_i81)       : Execute input history line #81 again
%rep 81          : Edit input history line #81
_, __, ___       : previous, next previous, next next previous output
_dh              : Directory history
_oh              : Output history
%hist            : Command history of current session.
%hist -g foo     : Search command history of (almost) all sessions for 'foo'.
%hist -g         : Command history of (almost) all sessions.
%hist 1/2-8      : Command history containing lines 2-8 of session 1.
%hist 1/ ~2/     : Command history of session 1 and 2 sessions before current.
%hist ~8/1-~6/5  : Command history from line 1 of 8 sessions ago to
                   line 5 of 6 sessions ago.
%edit 0/         : Open editor to execute code with history of current session.

Autocall:

f 1,2            : f(1,2)  # Off by default, enable with %autocall magic.
/f 1,2           : f(1,2) (forced autoparen)
,f 1 2           : f("1","2")
;f 1 2           : f("1 2")

Remember: TAB completion works in many contexts, not just file names
or python names.

The following magic functions are currently available:

"""

default_banner_parts = ["Python %s\n"%sys.version.split("\n")[0],
    "Type 'copyright', 'credits' or 'license' for more information\n" ,
    "IPython {version} -- An enhanced Interactive Python. Type '?' for help.\n".format(version=release.version),
]

default_banner = ''.join(default_banner_parts)

# === NexusCore/evaluation\evalplus\evalplus\gen\type_mut.py ===
import copy
import random
import string
import time
from typing import Any, Dict, List, Set, Tuple

from multipledispatch import dispatch

from evalplus.gen.mut_gen import MutateGen
from evalplus.gen.util import trusted_check_exec

MAX_MULTI_STEP_SIZE = 5
MUTATE_BOUND_SIZE = 8

NoneType = type(None)


# decorator to use ingredients
class use_ingredient:
    def __init__(self, prob: float):
        assert 0 <= prob <= 0.95
        self.prob = prob

    def __call__(obj, func):
        def wrapper(self, seed_input):
            if random.random() < obj.prob and self.ingredients[type(seed_input)]:
                return random.choice(list(self.ingredients[type(seed_input)]))
            else:
                return func(self, seed_input)

        return wrapper


class TypedMutGen(MutateGen):
    def __init__(self, inputs: List, signature: str, contract_code: str):
        super().__init__(inputs, signature, contract_code)
        self.timeout = 60 * 60  # 1 hour
        self.ingredients = {
            int: set(),
            float: set(),
            str: set(),
            complex: set(),
        }
        for x in inputs:
            self.fetch_ingredient(x)

    def seed_selection(self):
        # random for now.
        return random.choice(self.seed_pool)

    def mutate(self, seed_input: Any) -> List:
        new_input = copy.deepcopy(seed_input)

        patience = MUTATE_BOUND_SIZE
        while new_input == seed_input or patience == 0:
            new_input = self.typed_mutate(new_input)
            patience -= 1

        return new_input

    #########################
    # Type-aware generation #
    #########################
    @dispatch(NoneType)
    def typed_gen(self, _):
        return None

    @dispatch(int)
    def typed_gen(self, _):
        @use_ingredient(0.5)
        def _impl(*_):
            return random.randint(-100, 100)

        return _impl(self, _)

    @dispatch(float)
    def typed_gen(self, _):
        @use_ingredient(0.5)
        def _impl(*_):
            return random.uniform(-100, 100)

        return _impl(self, _)

    @dispatch(bool)
    def typed_gen(self, _):
        return random.choice([True, False])

    @dispatch(str)
    def typed_gen(self, _):
        @use_ingredient(0.5)
        def _impl(*_):
            return "".join(
                random.choice(string.ascii_letters)
                for _ in range(random.randint(0, 10))
            )

        return _impl(self, _)

    def any_gen(self):
        # weighted choose
        choice = random.choices(
            [
                True,
                1,
                1.1,
                "str",
                [],  # list
                tuple(),  # tuple
                dict(),  # dict
                None,  # None
            ],
            [0.2, 0.2, 0.2, 0.2, 0.05, 0.05, 0.05, 0.05],
        )[0]
        return self.typed_gen(choice)

    @dispatch(list)
    def typed_gen(self, _):
        ret = []
        size = random.randint(0, 10)
        if random.randint(0, 4) == 0:  # heterogeneous
            for _ in range(size):
                ret.append(self.any_gen())
        else:  # homogeneous
            t = random.choice([bool(), int(), float(), str()])
            for _ in range(size):
                ret.append(self.typed_gen(t))
        return ret

    @dispatch(tuple)
    def typed_gen(self, _):
        return tuple(self.typed_gen([]))

    # NOTE: disable set for now as Steven is too weak in Python (/s)
    # @dispatch(set)
    # def typed_gen(self, _):
    #     return set(self.typed_gen([]))

    @dispatch(dict)
    def typed_gen(self, _):
        ret = dict()
        values = self.typed_gen([])
        # NOTE: Assumption: nobody uses dict with heterogeneous keys
        # NOTE: Assumption: nobody uses dict with boolean keys
        key_type = random.choice([int(), float(), str()])
        for v in values:
            ret[self.typed_gen(key_type)] = self.typed_gen(v)
        return ret

    ########################
    # Type-aware mutation  #
    ########################
    # Simple primitives
    @dispatch(int)
    def typed_mutate(self, seed_input: int):
        @use_ingredient(0.5)
        def _impl(_, seed_input: int):
            return seed_input + random.randint(-1, 1)

        return _impl(self, seed_input)

    @dispatch(float)
    def typed_mutate(self, seed_input: float):
        @use_ingredient(0.5)
        def _impl(_, seed_input: float):
            if random.randint(0, 1):
                return seed_input + random.uniform(-1, 1)
            return seed_input * (1 + random.uniform(-0.5, 0.5))

        return _impl(self, seed_input)

    @dispatch(complex)
    def typed_mutate(self, seed_input: complex):
        @use_ingredient(0.5)
        def _impl(_, seed_input: complex):
            imag = seed_input.imag + random.uniform(-1, 1)
            return complex(0, imag)

        return _impl(self, seed_input)

    @dispatch(bool)
    def typed_mutate(self, seed_input: bool):
        return random.choice([True, False])

    @dispatch(NoneType)
    def typed_mutate(self, seed_input: NoneType):
        return None

    # List-like
    @dispatch(list)
    def typed_mutate(self, seed_input: List):
        if len(seed_input) == 0:
            return self.typed_gen([])

        choice = random.randint(0, 3)
        idx = random.randint(0, len(seed_input) - 1)
        if choice == 0:  # remove one element
            seed_input.pop(random.randint(0, len(seed_input) - 1))
        elif choice == 1 and len(seed_input) > 0:  # add one mutated element
            seed_input.insert(
                random.randint(0, len(seed_input) - 1),
                self.typed_mutate(seed_input[idx]),
            )
        elif choice == 2 and len(seed_input) > 0:  # repeat one element
            seed_input.append(seed_input[idx])
        else:  # inplace element change
            seed_input[idx] = self.typed_mutate(seed_input[idx])
        return seed_input

    @dispatch(tuple)
    def typed_mutate(self, seed_input: Tuple):
        return tuple(self.typed_mutate(list(seed_input)))

    # String
    @dispatch(str)
    def typed_mutate(self, seed_input: str):
        @use_ingredient(0.4)
        def _impl(_, seed_input: str):
            choice = random.randint(0, 2) if seed_input else 0
            if choice == 0 and self.ingredients[str]:  # insert an ingredient
                idx = random.randint(0, len(seed_input))
                return (
                    seed_input[:idx]
                    + random.choice(list(self.ingredients[str]))
                    + seed_input[idx:]
                )
            # other choices assume len(seed_input) > 0
            elif choice == 1:  # replace a substring with empty or mutated string
                start = random.randint(0, len(seed_input) - 1)
                end = random.randint(start + 1, len(seed_input))
                mid = (
                    ""
                    if random.randint(0, 1)
                    else self.typed_mutate(seed_input[start:end])
                )
                return seed_input[:start] + mid + seed_input[end:]
            elif choice == 2:  # repeat one element
                idx = random.randint(0, len(seed_input) - 1)
                return (
                    seed_input[:idx]
                    + seed_input[random.randint(0, len(seed_input) - 1)]
                    + seed_input[idx:]
                )

            # random char
            return self.typed_gen(str())

        return _impl(self, seed_input)

    # Set
    @dispatch(set)
    def typed_mutate(self, seed_input: Set):
        return set(self.typed_mutate(list(seed_input)))

    # Dict
    @dispatch(dict)
    def typed_mutate(self, seed_input: Dict):
        if len(seed_input) == 0:
            return self.typed_gen(dict())

        choice = random.randint(0, 2)
        if choice == 0:  # remove a kv
            del seed_input[random.choice(list(seed_input.keys()))]
        elif choice == 1:  # add a kv
            k = self.typed_mutate(random.choice(list(seed_input.keys())))
            v = self.typed_mutate(random.choice(list(seed_input.values())))
            seed_input[k] = v
        elif choice == 2:  # inplace value change
            k0, v0 = random.choice(list(seed_input.items()))
            seed_input[k0] = self.typed_mutate(v0)
        return seed_input

    ############################################
    # Fetching ingredients to self.ingredients #
    ############################################
    def fetch_ingredient(self, seed_input):
        self.typed_fetch(seed_input)

    @dispatch(int)
    def typed_fetch(self, seed_input: int):
        self.ingredients[int].add(seed_input)

    @dispatch(float)
    def typed_fetch(self, seed_input: float):
        self.ingredients[float].add(seed_input)

    @dispatch(complex)
    def typed_fetch(self, seed_input: complex):
        self.ingredients[complex].add(seed_input)

    @dispatch(str)
    def typed_fetch(self, seed_input: str):
        self.ingredients[str].add(seed_input)
        for token in seed_input.strip().split():
            self.ingredients[str].add(token)

    # List-like
    def _fetch_list_like(self, seed_input):
        for x in seed_input:
            if self.typed_fetch.dispatch(type(x)):
                self.fetch_ingredient(x)

    @dispatch(list)
    def typed_fetch(self, seed_input: List):
        self._fetch_list_like(seed_input)

    @dispatch(tuple)
    def typed_fetch(self, seed_input: Tuple):
        self._fetch_list_like(seed_input)

    # NOTE: disable set for now as Steven is too weak in Python (/s)
    # @dispatch(set)
    # def typed_fetch(self, seed_input: Set):
    #     self._fetch_list_like(seed_input)

    # Dict
    @dispatch(dict)
    def typed_fetch(self, seed_input: Dict):
        self._fetch_list_like(seed_input.keys())
        self._fetch_list_like(seed_input.values())

    def generate(self, num: int):
        start = time.time()
        num_generated = 1
        while len(self.new_inputs) < num and time.time() - start < self.timeout:
            if num_generated % 1000 == 0:
                print(
                    f"generated {num_generated} already with {len(self.new_inputs)} new inputs ... "
                )
            new_input = self.seed_selection()
            # Multi-step instead of single-step
            for _ in range(random.randint(1, MAX_MULTI_STEP_SIZE)):
                new_input = self.mutate(new_input)
            num_generated += 1
            if hash(str(new_input)) not in self.seed_hash:
                if trusted_check_exec(self.contract, [new_input], self.entry_point):
                    self.typed_fetch(new_input)
                    self.seed_pool.append(new_input)
                    self.new_inputs.append(new_input)
                self.seed_hash.add(hash(str(new_input)))
        return self.new_inputs[:num]

# === NexusCore/openenv\Lib\site-packages\google\longrunning\operations_pb2_grpc.py ===
# Copyright 2020 Google LLC
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

# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!

"""Client and server classes corresponding to protobuf-defined services."""
from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2
import grpc

from google.longrunning import (
    operations_proto_pb2 as google_dot_longrunning_dot_operations__pb2,
)


class OperationsStub(object):
    """Manages long-running operations with an API service.

    When an API method normally takes long time to complete, it can be designed
    to return [Operation][google.longrunning.Operation] to the client, and the client can use this
    interface to receive the real response asynchronously by polling the
    operation resource, or pass the operation resource to another API (such as
    Google Cloud Pub/Sub API) to receive the response.  Any API service that
    returns long-running operations should implement the `Operations` interface
    so developers can have a consistent client experience.
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.ListOperations = channel.unary_unary(
            "/google.longrunning.Operations/ListOperations",
            request_serializer=google_dot_longrunning_dot_operations__pb2.ListOperationsRequest.SerializeToString,
            response_deserializer=google_dot_longrunning_dot_operations__pb2.ListOperationsResponse.FromString,
        )
        self.GetOperation = channel.unary_unary(
            "/google.longrunning.Operations/GetOperation",
            request_serializer=google_dot_longrunning_dot_operations__pb2.GetOperationRequest.SerializeToString,
            response_deserializer=google_dot_longrunning_dot_operations__pb2.Operation.FromString,
        )
        self.DeleteOperation = channel.unary_unary(
            "/google.longrunning.Operations/DeleteOperation",
            request_serializer=google_dot_longrunning_dot_operations__pb2.DeleteOperationRequest.SerializeToString,
            response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
        )
        self.CancelOperation = channel.unary_unary(
            "/google.longrunning.Operations/CancelOperation",
            request_serializer=google_dot_longrunning_dot_operations__pb2.CancelOperationRequest.SerializeToString,
            response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
        )
        self.WaitOperation = channel.unary_unary(
            "/google.longrunning.Operations/WaitOperation",
            request_serializer=google_dot_longrunning_dot_operations__pb2.WaitOperationRequest.SerializeToString,
            response_deserializer=google_dot_longrunning_dot_operations__pb2.Operation.FromString,
        )


class OperationsServicer(object):
    """Manages long-running operations with an API service.

    When an API method normally takes long time to complete, it can be designed
    to return [Operation][google.longrunning.Operation] to the client, and the client can use this
    interface to receive the real response asynchronously by polling the
    operation resource, or pass the operation resource to another API (such as
    Google Cloud Pub/Sub API) to receive the response.  Any API service that
    returns long-running operations should implement the `Operations` interface
    so developers can have a consistent client experience.
    """

    def ListOperations(self, request, context):
        """Lists operations that match the specified filter in the request. If the
        server doesn't support this method, it returns `UNIMPLEMENTED`.

        NOTE: the `name` binding allows API services to override the binding
        to use different resource name schemes, such as `users/*/operations`. To
        override the binding, API services can add a binding such as
        `"/v1/{name=users/*}/operations"` to their service configuration.
        For backwards compatibility, the default name includes the operations
        collection id, however overriding users must ensure the name binding
        is the parent resource, without the operations collection id.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def GetOperation(self, request, context):
        """Gets the latest state of a long-running operation.  Clients can use this
        method to poll the operation result at intervals as recommended by the API
        service.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def DeleteOperation(self, request, context):
        """Deletes a long-running operation. This method indicates that the client is
        no longer interested in the operation result. It does not cancel the
        operation. If the server doesn't support this method, it returns
        `google.rpc.Code.UNIMPLEMENTED`.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def CancelOperation(self, request, context):
        """Starts asynchronous cancellation on a long-running operation.  The server
        makes a best effort to cancel the operation, but success is not
        guaranteed.  If the server doesn't support this method, it returns
        `google.rpc.Code.UNIMPLEMENTED`.  Clients can use
        [Operations.GetOperation][google.longrunning.Operations.GetOperation] or
        other methods to check whether the cancellation succeeded or whether the
        operation completed despite cancellation. On successful cancellation,
        the operation is not deleted; instead, it becomes an operation with
        an [Operation.error][google.longrunning.Operation.error] value with a [google.rpc.Status.code][google.rpc.Status.code] of 1,
        corresponding to `Code.CANCELLED`.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def WaitOperation(self, request, context):
        """Waits until the specified long-running operation is done or reaches at most
        a specified timeout, returning the latest state.  If the operation is
        already done, the latest state is immediately returned.  If the timeout
        specified is greater than the default HTTP/RPC timeout, the HTTP/RPC
        timeout is used.  If the server does not support this method, it returns
        `google.rpc.Code.UNIMPLEMENTED`.
        Note that this method is on a best-effort basis.  It may return the latest
        state before the specified timeout (including immediately), meaning even an
        immediate response is no guarantee that the operation is done.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")


def add_OperationsServicer_to_server(servicer, server):
    rpc_method_handlers = {
        "ListOperations": grpc.unary_unary_rpc_method_handler(
            servicer.ListOperations,
            request_deserializer=google_dot_longrunning_dot_operations__pb2.ListOperationsRequest.FromString,
            response_serializer=google_dot_longrunning_dot_operations__pb2.ListOperationsResponse.SerializeToString,
        ),
        "GetOperation": grpc.unary_unary_rpc_method_handler(
            servicer.GetOperation,
            request_deserializer=google_dot_longrunning_dot_operations__pb2.GetOperationRequest.FromString,
            response_serializer=google_dot_longrunning_dot_operations__pb2.Operation.SerializeToString,
        ),
        "DeleteOperation": grpc.unary_unary_rpc_method_handler(
            servicer.DeleteOperation,
            request_deserializer=google_dot_longrunning_dot_operations__pb2.DeleteOperationRequest.FromString,
            response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        ),
        "CancelOperation": grpc.unary_unary_rpc_method_handler(
            servicer.CancelOperation,
            request_deserializer=google_dot_longrunning_dot_operations__pb2.CancelOperationRequest.FromString,
            response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        ),
        "WaitOperation": grpc.unary_unary_rpc_method_handler(
            servicer.WaitOperation,
            request_deserializer=google_dot_longrunning_dot_operations__pb2.WaitOperationRequest.FromString,
            response_serializer=google_dot_longrunning_dot_operations__pb2.Operation.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "google.longrunning.Operations", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))


# This class is part of an EXPERIMENTAL API.
class Operations(object):
    """Manages long-running operations with an API service.

    When an API method normally takes long time to complete, it can be designed
    to return [Operation][google.longrunning.Operation] to the client, and the client can use this
    interface to receive the real response asynchronously by polling the
    operation resource, or pass the operation resource to another API (such as
    Google Cloud Pub/Sub API) to receive the response.  Any API service that
    returns long-running operations should implement the `Operations` interface
    so developers can have a consistent client experience.
    """

    @staticmethod
    def ListOperations(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/google.longrunning.Operations/ListOperations",
            google_dot_longrunning_dot_operations__pb2.ListOperationsRequest.SerializeToString,
            google_dot_longrunning_dot_operations__pb2.ListOperationsResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )

    @staticmethod
    def GetOperation(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/google.longrunning.Operations/GetOperation",
            google_dot_longrunning_dot_operations__pb2.GetOperationRequest.SerializeToString,
            google_dot_longrunning_dot_operations__pb2.Operation.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )

    @staticmethod
    def DeleteOperation(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/google.longrunning.Operations/DeleteOperation",
            google_dot_longrunning_dot_operations__pb2.DeleteOperationRequest.SerializeToString,
            google_dot_protobuf_dot_empty__pb2.Empty.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )

    @staticmethod
    def CancelOperation(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/google.longrunning.Operations/CancelOperation",
            google_dot_longrunning_dot_operations__pb2.CancelOperationRequest.SerializeToString,
            google_dot_protobuf_dot_empty__pb2.Empty.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )

    @staticmethod
    def WaitOperation(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/google.longrunning.Operations/WaitOperation",
            google_dot_longrunning_dot_operations__pb2.WaitOperationRequest.SerializeToString,
            google_dot_longrunning_dot_operations__pb2.Operation.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\discuss_service\transports\grpc_asyncio.py ===
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
from typing import Awaitable, Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, grpc_helpers_async
from google.api_core import retry_async as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta2.types import discuss_service

from .base import DEFAULT_CLIENT_INFO, DiscussServiceTransport
from .grpc import DiscussServiceGrpcTransport


class DiscussServiceGrpcAsyncIOTransport(DiscussServiceTransport):
    """gRPC AsyncIO backend transport for DiscussService.

    An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _grpc_channel: aio.Channel
    _stubs: Dict[str, Callable] = {}

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> aio.Channel:
        """Create and return a gRPC AsyncIO channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            aio.Channel: A gRPC AsyncIO channel object.
        """

        return grpc_helpers_async.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[aio.Channel, Callable[..., aio.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
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
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            channel (Optional[Union[aio.Channel, Callable[..., aio.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, aio.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None
        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @property
    def grpc_channel(self) -> aio.Channel:
        """Create the channel designed to connect to this service.

        This property caches on the instance; repeated calls return
        the same channel.
        """
        # Return the channel from cache.
        return self._grpc_channel

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        Awaitable[discuss_service.GenerateMessageResponse],
    ]:
        r"""Return a callable for the generate message method over gRPC.

        Generates a response from the model given an input
        ``MessagePrompt``.

        Returns:
            Callable[[~.GenerateMessageRequest],
                    Awaitable[~.GenerateMessageResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_message" not in self._stubs:
            self._stubs["generate_message"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta2.DiscussService/GenerateMessage",
                request_serializer=discuss_service.GenerateMessageRequest.serialize,
                response_deserializer=discuss_service.GenerateMessageResponse.deserialize,
            )
        return self._stubs["generate_message"]

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        Awaitable[discuss_service.CountMessageTokensResponse],
    ]:
        r"""Return a callable for the count message tokens method over gRPC.

        Runs a model's tokenizer on a string and returns the
        token count.

        Returns:
            Callable[[~.CountMessageTokensRequest],
                    Awaitable[~.CountMessageTokensResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_message_tokens" not in self._stubs:
            self._stubs["count_message_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta2.DiscussService/CountMessageTokens",
                request_serializer=discuss_service.CountMessageTokensRequest.serialize,
                response_deserializer=discuss_service.CountMessageTokensResponse.deserialize,
            )
        return self._stubs["count_message_tokens"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.generate_message: gapic_v1.method_async.wrap_method(
                self.generate_message,
                default_retry=retries.AsyncRetry(
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
            self.count_message_tokens: gapic_v1.method_async.wrap_method(
                self.count_message_tokens,
                default_retry=retries.AsyncRetry(
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
        return self.grpc_channel.close()


__all__ = ("DiscussServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\nltk\ccg\combinator.py ===
# Natural Language Toolkit: Combinatory Categorial Grammar
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
CCG Combinators
"""

from abc import ABCMeta, abstractmethod

from nltk.ccg.api import FunctionalCategory


class UndirectedBinaryCombinator(metaclass=ABCMeta):
    """
    Abstract class for representing a binary combinator.
    Merely defines functions for checking if the function and argument
    are able to be combined, and what the resulting category is.

    Note that as no assumptions are made as to direction, the unrestricted
    combinators can perform all backward, forward and crossed variations
    of the combinators; these restrictions must be added in the rule
    class.
    """

    @abstractmethod
    def can_combine(self, function, argument):
        pass

    @abstractmethod
    def combine(self, function, argument):
        pass


class DirectedBinaryCombinator(metaclass=ABCMeta):
    """
    Wrapper for the undirected binary combinator.
    It takes left and right categories, and decides which is to be
    the function, and which the argument.
    It then decides whether or not they can be combined.
    """

    @abstractmethod
    def can_combine(self, left, right):
        pass

    @abstractmethod
    def combine(self, left, right):
        pass


class ForwardCombinator(DirectedBinaryCombinator):
    """
    Class representing combinators where the primary functor is on the left.

    Takes an undirected combinator, and a predicate which adds constraints
    restricting the cases in which it may apply.
    """

    def __init__(self, combinator, predicate, suffix=""):
        self._combinator = combinator
        self._predicate = predicate
        self._suffix = suffix

    def can_combine(self, left, right):
        return self._combinator.can_combine(left, right) and self._predicate(
            left, right
        )

    def combine(self, left, right):
        yield from self._combinator.combine(left, right)

    def __str__(self):
        return f">{self._combinator}{self._suffix}"


class BackwardCombinator(DirectedBinaryCombinator):
    """
    The backward equivalent of the ForwardCombinator class.
    """

    def __init__(self, combinator, predicate, suffix=""):
        self._combinator = combinator
        self._predicate = predicate
        self._suffix = suffix

    def can_combine(self, left, right):
        return self._combinator.can_combine(right, left) and self._predicate(
            left, right
        )

    def combine(self, left, right):
        yield from self._combinator.combine(right, left)

    def __str__(self):
        return f"<{self._combinator}{self._suffix}"


class UndirectedFunctionApplication(UndirectedBinaryCombinator):
    """
    Class representing function application.
    Implements rules of the form:
    X/Y Y -> X (>)
    And the corresponding backwards application rule
    """

    def can_combine(self, function, argument):
        if not function.is_function():
            return False

        return not function.arg().can_unify(argument) is None

    def combine(self, function, argument):
        if not function.is_function():
            return

        subs = function.arg().can_unify(argument)
        if subs is None:
            return

        yield function.res().substitute(subs)

    def __str__(self):
        return ""


# Predicates for function application.


# Ensures the left functor takes an argument on the right
def forwardOnly(left, right):
    return left.dir().is_forward()


# Ensures the right functor takes an argument on the left
def backwardOnly(left, right):
    return right.dir().is_backward()


# Application combinator instances
ForwardApplication = ForwardCombinator(UndirectedFunctionApplication(), forwardOnly)
BackwardApplication = BackwardCombinator(UndirectedFunctionApplication(), backwardOnly)


class UndirectedComposition(UndirectedBinaryCombinator):
    """
    Functional composition (harmonic) combinator.
    Implements rules of the form
    X/Y Y/Z -> X/Z (B>)
    And the corresponding backwards and crossed variations.
    """

    def can_combine(self, function, argument):
        # Can only combine two functions, and both functions must
        # allow composition.
        if not (function.is_function() and argument.is_function()):
            return False
        if function.dir().can_compose() and argument.dir().can_compose():
            return not function.arg().can_unify(argument.res()) is None
        return False

    def combine(self, function, argument):
        if not (function.is_function() and argument.is_function()):
            return
        if function.dir().can_compose() and argument.dir().can_compose():
            subs = function.arg().can_unify(argument.res())
            if subs is not None:
                yield FunctionalCategory(
                    function.res().substitute(subs),
                    argument.arg().substitute(subs),
                    argument.dir(),
                )

    def __str__(self):
        return "B"


# Predicates for restricting application of straight composition.
def bothForward(left, right):
    return left.dir().is_forward() and right.dir().is_forward()


def bothBackward(left, right):
    return left.dir().is_backward() and right.dir().is_backward()


# Predicates for crossed composition
def crossedDirs(left, right):
    return left.dir().is_forward() and right.dir().is_backward()


def backwardBxConstraint(left, right):
    # The functors must be crossed inwards
    if not crossedDirs(left, right):
        return False
    # Permuting combinators must be allowed
    if not left.dir().can_cross() and right.dir().can_cross():
        return False
    # The resulting argument category is restricted to be primitive
    return left.arg().is_primitive()


# Straight composition combinators
ForwardComposition = ForwardCombinator(UndirectedComposition(), forwardOnly)
BackwardComposition = BackwardCombinator(UndirectedComposition(), backwardOnly)

# Backward crossed composition
BackwardBx = BackwardCombinator(
    UndirectedComposition(), backwardBxConstraint, suffix="x"
)


class UndirectedSubstitution(UndirectedBinaryCombinator):
    r"""
    Substitution (permutation) combinator.
    Implements rules of the form
    Y/Z (X\Y)/Z -> X/Z (<Sx)
    And other variations.
    """

    def can_combine(self, function, argument):
        if function.is_primitive() or argument.is_primitive():
            return False

        # These could potentially be moved to the predicates, as the
        # constraints may not be general to all languages.
        if function.res().is_primitive():
            return False
        if not function.arg().is_primitive():
            return False

        if not (function.dir().can_compose() and argument.dir().can_compose()):
            return False
        return (function.res().arg() == argument.res()) and (
            function.arg() == argument.arg()
        )

    def combine(self, function, argument):
        if self.can_combine(function, argument):
            yield FunctionalCategory(
                function.res().res(), argument.arg(), argument.dir()
            )

    def __str__(self):
        return "S"


# Predicate for forward substitution
def forwardSConstraint(left, right):
    if not bothForward(left, right):
        return False
    return left.res().dir().is_forward() and left.arg().is_primitive()


# Predicate for backward crossed substitution
def backwardSxConstraint(left, right):
    if not left.dir().can_cross() and right.dir().can_cross():
        return False
    if not bothForward(left, right):
        return False
    return right.res().dir().is_backward() and right.arg().is_primitive()


# Instances of substitution combinators
ForwardSubstitution = ForwardCombinator(UndirectedSubstitution(), forwardSConstraint)
BackwardSx = BackwardCombinator(UndirectedSubstitution(), backwardSxConstraint, "x")


# Retrieves the left-most functional category.
# ie, (N\N)/(S/NP) => N\N
def innermostFunction(categ):
    while categ.res().is_function():
        categ = categ.res()
    return categ


class UndirectedTypeRaise(UndirectedBinaryCombinator):
    """
    Undirected combinator for type raising.
    """

    def can_combine(self, function, arg):
        # The argument must be a function.
        # The restriction that arg.res() must be a function
        # merely reduces redundant type-raising; if arg.res() is
        # primitive, we have:
        # X Y\X =>(<T) Y/(Y\X) Y\X =>(>) Y
        # which is equivalent to
        # X Y\X =>(<) Y
        if not (arg.is_function() and arg.res().is_function()):
            return False

        arg = innermostFunction(arg)

        # left, arg_categ are undefined!
        subs = left.can_unify(arg_categ.arg())
        if subs is not None:
            return True
        return False

    def combine(self, function, arg):
        if not (
            function.is_primitive() and arg.is_function() and arg.res().is_function()
        ):
            return

        # Type-raising matches only the innermost application.
        arg = innermostFunction(arg)

        subs = function.can_unify(arg.arg())
        if subs is not None:
            xcat = arg.res().substitute(subs)
            yield FunctionalCategory(
                xcat, FunctionalCategory(xcat, function, arg.dir()), -(arg.dir())
            )

    def __str__(self):
        return "T"


# Predicates for type-raising
# The direction of the innermost category must be towards
# the primary functor.
# The restriction that the variable must be primitive is not
# common to all versions of CCGs; some authors have other restrictions.
def forwardTConstraint(left, right):
    arg = innermostFunction(right)
    return arg.dir().is_backward() and arg.res().is_primitive()


def backwardTConstraint(left, right):
    arg = innermostFunction(left)
    return arg.dir().is_forward() and arg.res().is_primitive()


# Instances of type-raising combinators
ForwardT = ForwardCombinator(UndirectedTypeRaise(), forwardTConstraint)
BackwardT = BackwardCombinator(UndirectedTypeRaise(), backwardTConstraint)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\bidi\network.py ===
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

from selenium.webdriver.common.bidi.common import command_builder


class NetworkEvent:
    """Represents a network event."""

    def __init__(self, event_class, **kwargs):
        self.event_class = event_class
        self.params = kwargs

    @classmethod
    def from_json(cls, json):
        return cls(event_class=json.get("event_class"), **json)


class Network:
    EVENTS = {
        "before_request": "network.beforeRequestSent",
        "response_started": "network.responseStarted",
        "response_completed": "network.responseCompleted",
        "auth_required": "network.authRequired",
        "fetch_error": "network.fetchError",
        "continue_request": "network.continueRequest",
        "continue_auth": "network.continueWithAuth",
    }

    PHASES = {
        "before_request": "beforeRequestSent",
        "response_started": "responseStarted",
        "auth_required": "authRequired",
    }

    def __init__(self, conn):
        self.conn = conn
        self.intercepts = []
        self.callbacks = {}
        self.subscriptions = {}

    def _add_intercept(self, phases=[], contexts=None, url_patterns=None):
        """Add an intercept to the network.

        Parameters:
        ----------
            phases (list, optional): A list of phases to intercept.
                Default is empty list.
            contexts (list, optional): A list of contexts to intercept.
                Default is None.
            url_patterns (list, optional): A list of URL patterns to intercept.
                Default is None.

        Returns:
        -------
            str : intercept id
        """
        params = {}
        if contexts is not None:
            params["contexts"] = contexts
        if url_patterns is not None:
            params["urlPatterns"] = url_patterns
        if len(phases) > 0:
            params["phases"] = phases
        else:
            params["phases"] = ["beforeRequestSent"]
        cmd = command_builder("network.addIntercept", params)

        result = self.conn.execute(cmd)
        self.intercepts.append(result["intercept"])
        return result

    def _remove_intercept(self, intercept=None):
        """Remove a specific intercept, or all intercepts.

        Parameters:
        ----------
            intercept (str, optional): The intercept to remove.
                Default is None.

        Raises:
        ------
            Exception: If intercept is not found.

        Notes:
        -----
            If intercept is None, all intercepts will be removed.
        """
        if intercept is None:
            intercepts_to_remove = self.intercepts.copy()  # create a copy before iterating
            for intercept_id in intercepts_to_remove:  # remove all intercepts
                self.conn.execute(command_builder("network.removeIntercept", {"intercept": intercept_id}))
                self.intercepts.remove(intercept_id)
        else:
            try:
                self.conn.execute(command_builder("network.removeIntercept", {"intercept": intercept}))
                self.intercepts.remove(intercept)
            except Exception as e:
                raise Exception(f"Exception: {e}")

    def _on_request(self, event_name, callback):
        """Set a callback function to subscribe to a network event.

        Parameters:
        ----------
            event_name (str): The event to subscribe to.
            callback (function): The callback function to execute on event.
                Takes Request object as argument.

        Returns:
        -------
            int : callback id
        """

        event = NetworkEvent(event_name)

        def _callback(event_data):
            request = Request(
                network=self,
                request_id=event_data.params["request"].get("request", None),
                body_size=event_data.params["request"].get("bodySize", None),
                cookies=event_data.params["request"].get("cookies", None),
                resource_type=event_data.params["request"].get("goog:resourceType", None),
                headers=event_data.params["request"].get("headers", None),
                headers_size=event_data.params["request"].get("headersSize", None),
                timings=event_data.params["request"].get("timings", None),
                url=event_data.params["request"].get("url", None),
            )
            callback(request)

        callback_id = self.conn.add_callback(event, _callback)

        if event_name in self.callbacks:
            self.callbacks[event_name].append(callback_id)
        else:
            self.callbacks[event_name] = [callback_id]

        return callback_id

    def add_request_handler(self, event, callback, url_patterns=None, contexts=None):
        """Add a request handler to the network.

        Parameters:
        ----------
            event (str): The event to subscribe to.
            url_patterns (list, optional): A list of URL patterns to intercept.
                Default is None.
            contexts (list, optional): A list of contexts to intercept.
                Default is None.
            callback (function): The callback function to execute on request interception
                Takes Request object as argument.

        Returns:
        -------
            int : callback id
        """

        try:
            event_name = self.EVENTS[event]
            phase_name = self.PHASES[event]
        except KeyError:
            raise Exception(f"Event {event} not found")

        result = self._add_intercept(phases=[phase_name], url_patterns=url_patterns, contexts=contexts)
        callback_id = self._on_request(event_name, callback)

        if event_name in self.subscriptions:
            self.subscriptions[event_name].append(callback_id)
        else:
            params = {}
            params["events"] = [event_name]
            self.conn.execute(command_builder("session.subscribe", params))
            self.subscriptions[event_name] = [callback_id]

        self.callbacks[callback_id] = result["intercept"]
        return callback_id

    def remove_request_handler(self, event, callback_id):
        """Remove a request handler from the network.

        Parameters:
        ----------
            event_name (str): The event to unsubscribe from.
            callback_id (int): The callback id to remove.
        """
        try:
            event_name = self.EVENTS[event]
        except KeyError:
            raise Exception(f"Event {event} not found")

        net_event = NetworkEvent(event_name)

        self.conn.remove_callback(net_event, callback_id)
        self._remove_intercept(self.callbacks[callback_id])
        del self.callbacks[callback_id]
        self.subscriptions[event_name].remove(callback_id)
        if len(self.subscriptions[event_name]) == 0:
            params = {}
            params["events"] = [event_name]
            self.conn.execute(command_builder("session.unsubscribe", params))
            del self.subscriptions[event_name]

    def clear_request_handlers(self):
        """Clear all request handlers from the network."""

        for event_name in self.subscriptions:
            net_event = NetworkEvent(event_name)
            for callback_id in self.subscriptions[event_name]:
                self.conn.remove_callback(net_event, callback_id)
                self._remove_intercept(self.callbacks[callback_id])
                del self.callbacks[callback_id]
            params = {}
            params["events"] = [event_name]
            self.conn.execute(command_builder("session.unsubscribe", params))
        self.subscriptions = {}

    def add_auth_handler(self, username, password):
        """Add an authentication handler to the network.

        Parameters:
        ----------
            username (str): The username to authenticate with.
            password (str): The password to authenticate with.

        Returns:
        -------
            int : callback id
        """
        event = "auth_required"

        def _callback(request):
            request._continue_with_auth(username, password)

        return self.add_request_handler(event, _callback)

    def remove_auth_handler(self, callback_id):
        """Remove an authentication handler from the network.

        Parameters:
        ----------
            callback_id (int): The callback id to remove.
        """
        event = "auth_required"
        self.remove_request_handler(event, callback_id)


class Request:
    """Represents an intercepted network request."""

    def __init__(
        self,
        network: Network,
        request_id,
        body_size=None,
        cookies=None,
        resource_type=None,
        headers=None,
        headers_size=None,
        method=None,
        timings=None,
        url=None,
    ):
        self.network = network
        self.request_id = request_id
        self.body_size = body_size
        self.cookies = cookies
        self.resource_type = resource_type
        self.headers = headers
        self.headers_size = headers_size
        self.method = method
        self.timings = timings
        self.url = url

    def fail_request(self):
        """Fail this request."""

        if not self.request_id:
            raise ValueError("Request not found.")

        params = {"request": self.request_id}
        self.network.conn.execute(command_builder("network.failRequest", params))

    def continue_request(self, body=None, method=None, headers=None, cookies=None, url=None):
        """Continue after intercepting this request."""

        if not self.request_id:
            raise ValueError("Request not found.")

        params = {"request": self.request_id}
        if body is not None:
            params["body"] = body
        if method is not None:
            params["method"] = method
        if headers is not None:
            params["headers"] = headers
        if cookies is not None:
            params["cookies"] = cookies
        if url is not None:
            params["url"] = url

        self.network.conn.execute(command_builder("network.continueRequest", params))

    def _continue_with_auth(self, username=None, password=None):
        """Continue with authentication.

        Parameters:
        ----------
            request (Request): The request to continue with.
            username (str): The username to authenticate with.
            password (str): The password to authenticate with.

        Notes:
        -----
            If username or password is None, it attempts auth with no credentials
        """

        params = {}
        params["request"] = self.request_id

        if not username or not password:  # no credentials is valid option
            params["action"] = "default"
        else:
            params["action"] = "provideCredentials"
            params["credentials"] = {"type": "password", "username": username, "password": password}

        self.network.conn.execute(command_builder("network.continueWithAuth", params))

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\compilers\C\cygwin.py ===
"""distutils.cygwinccompiler

Provides the CygwinCCompiler class, a subclass of UnixCCompiler that
handles the Cygwin port of the GNU C compiler to Windows.  It also contains
the Mingw32CCompiler class which handles the mingw32 port of GCC (same as
cygwin in no-cygwin mode).
"""

import copy
import os
import pathlib
import shlex
import sys
import warnings
from subprocess import check_output

from ...errors import (
    DistutilsExecError,
    DistutilsPlatformError,
)
from ...file_util import write_file
from ...sysconfig import get_config_vars
from ...version import LooseVersion, suppress_known_deprecation
from . import unix
from .errors import (
    CompileError,
    Error,
)


def get_msvcr():
    """No longer needed, but kept for backward compatibility."""
    return []


_runtime_library_dirs_msg = (
    "Unable to set runtime library search path on Windows, "
    "usually indicated by `runtime_library_dirs` parameter to Extension"
)


class Compiler(unix.Compiler):
    """Handles the Cygwin port of the GNU C compiler to Windows."""

    compiler_type = 'cygwin'
    obj_extension = ".o"
    static_lib_extension = ".a"
    shared_lib_extension = ".dll.a"
    dylib_lib_extension = ".dll"
    static_lib_format = "lib%s%s"
    shared_lib_format = "lib%s%s"
    dylib_lib_format = "cyg%s%s"
    exe_extension = ".exe"

    def __init__(self, verbose=False, dry_run=False, force=False):
        super().__init__(verbose, dry_run, force)

        status, details = check_config_h()
        self.debug_print(f"Python's GCC status: {status} (details: {details})")
        if status is not CONFIG_H_OK:
            self.warn(
                "Python's pyconfig.h doesn't seem to support your compiler. "
                f"Reason: {details}. "
                "Compiling may fail because of undefined preprocessor macros."
            )

        self.cc, self.cxx = get_config_vars('CC', 'CXX')

        # Override 'CC' and 'CXX' environment variables for
        # building using MINGW compiler for MSVC python.
        self.cc = os.environ.get('CC', self.cc or 'gcc')
        self.cxx = os.environ.get('CXX', self.cxx or 'g++')

        self.linker_dll = self.cc
        self.linker_dll_cxx = self.cxx
        shared_option = "-shared"

        self.set_executables(
            compiler=f'{self.cc} -mcygwin -O -Wall',
            compiler_so=f'{self.cc} -mcygwin -mdll -O -Wall',
            compiler_cxx=f'{self.cxx} -mcygwin -O -Wall',
            compiler_so_cxx=f'{self.cxx} -mcygwin -mdll -O -Wall',
            linker_exe=f'{self.cc} -mcygwin',
            linker_so=f'{self.linker_dll} -mcygwin {shared_option}',
            linker_exe_cxx=f'{self.cxx} -mcygwin',
            linker_so_cxx=f'{self.linker_dll_cxx} -mcygwin {shared_option}',
        )

        self.dll_libraries = get_msvcr()

    @property
    def gcc_version(self):
        # Older numpy depended on this existing to check for ancient
        # gcc versions. This doesn't make much sense with clang etc so
        # just hardcode to something recent.
        # https://github.com/numpy/numpy/pull/20333
        warnings.warn(
            "gcc_version attribute of CygwinCCompiler is deprecated. "
            "Instead of returning actual gcc version a fixed value 11.2.0 is returned.",
            DeprecationWarning,
            stacklevel=2,
        )
        with suppress_known_deprecation():
            return LooseVersion("11.2.0")

    def _compile(self, obj, src, ext, cc_args, extra_postargs, pp_opts):
        """Compiles the source by spawning GCC and windres if needed."""
        if ext in ('.rc', '.res'):
            # gcc needs '.res' and '.rc' compiled to object files !!!
            try:
                self.spawn(["windres", "-i", src, "-o", obj])
            except DistutilsExecError as msg:
                raise CompileError(msg)
        else:  # for other files use the C-compiler
            try:
                if self.detect_language(src) == 'c++':
                    self.spawn(
                        self.compiler_so_cxx
                        + cc_args
                        + [src, '-o', obj]
                        + extra_postargs
                    )
                else:
                    self.spawn(
                        self.compiler_so + cc_args + [src, '-o', obj] + extra_postargs
                    )
            except DistutilsExecError as msg:
                raise CompileError(msg)

    def link(
        self,
        target_desc,
        objects,
        output_filename,
        output_dir=None,
        libraries=None,
        library_dirs=None,
        runtime_library_dirs=None,
        export_symbols=None,
        debug=False,
        extra_preargs=None,
        extra_postargs=None,
        build_temp=None,
        target_lang=None,
    ):
        """Link the objects."""
        # use separate copies, so we can modify the lists
        extra_preargs = copy.copy(extra_preargs or [])
        libraries = copy.copy(libraries or [])
        objects = copy.copy(objects or [])

        if runtime_library_dirs:
            self.warn(_runtime_library_dirs_msg)

        # Additional libraries
        libraries.extend(self.dll_libraries)

        # handle export symbols by creating a def-file
        # with executables this only works with gcc/ld as linker
        if (export_symbols is not None) and (
            target_desc != self.EXECUTABLE or self.linker_dll == "gcc"
        ):
            # (The linker doesn't do anything if output is up-to-date.
            # So it would probably better to check if we really need this,
            # but for this we had to insert some unchanged parts of
            # UnixCCompiler, and this is not what we want.)

            # we want to put some files in the same directory as the
            # object files are, build_temp doesn't help much
            # where are the object files
            temp_dir = os.path.dirname(objects[0])
            # name of dll to give the helper files the same base name
            (dll_name, dll_extension) = os.path.splitext(
                os.path.basename(output_filename)
            )

            # generate the filenames for these files
            def_file = os.path.join(temp_dir, dll_name + ".def")

            # Generate .def file
            contents = [f"LIBRARY {os.path.basename(output_filename)}", "EXPORTS"]
            contents.extend(export_symbols)
            self.execute(write_file, (def_file, contents), f"writing {def_file}")

            # next add options for def-file

            # for gcc/ld the def-file is specified as any object files
            objects.append(def_file)

        # end: if ((export_symbols is not None) and
        #        (target_desc != self.EXECUTABLE or self.linker_dll == "gcc")):

        # who wants symbols and a many times larger output file
        # should explicitly switch the debug mode on
        # otherwise we let ld strip the output file
        # (On my machine: 10KiB < stripped_file < ??100KiB
        #   unstripped_file = stripped_file + XXX KiB
        #  ( XXX=254 for a typical python extension))
        if not debug:
            extra_preargs.append("-s")

        super().link(
            target_desc,
            objects,
            output_filename,
            output_dir,
            libraries,
            library_dirs,
            runtime_library_dirs,
            None,  # export_symbols, we do this in our def-file
            debug,
            extra_preargs,
            extra_postargs,
            build_temp,
            target_lang,
        )

    def runtime_library_dir_option(self, dir):
        # cygwin doesn't support rpath. While in theory we could error
        # out like MSVC does, code might expect it to work like on Unix, so
        # just warn and hope for the best.
        self.warn(_runtime_library_dirs_msg)
        return []

    # -- Miscellaneous methods -----------------------------------------

    def _make_out_path(self, output_dir, strip_dir, src_name):
        # use normcase to make sure '.rc' is really '.rc' and not '.RC'
        norm_src_name = os.path.normcase(src_name)
        return super()._make_out_path(output_dir, strip_dir, norm_src_name)

    @property
    def out_extensions(self):
        """
        Add support for rc and res files.
        """
        return {
            **super().out_extensions,
            **{ext: ext + self.obj_extension for ext in ('.res', '.rc')},
        }


# the same as cygwin plus some additional parameters
class MinGW32Compiler(Compiler):
    """Handles the Mingw32 port of the GNU C compiler to Windows."""

    compiler_type = 'mingw32'

    def __init__(self, verbose=False, dry_run=False, force=False):
        super().__init__(verbose, dry_run, force)

        shared_option = "-shared"

        if is_cygwincc(self.cc):
            raise Error('Cygwin gcc cannot be used with --compiler=mingw32')

        self.set_executables(
            compiler=f'{self.cc} -O -Wall',
            compiler_so=f'{self.cc} -shared -O -Wall',
            compiler_so_cxx=f'{self.cxx} -shared -O -Wall',
            compiler_cxx=f'{self.cxx} -O -Wall',
            linker_exe=f'{self.cc}',
            linker_so=f'{self.linker_dll} {shared_option}',
            linker_exe_cxx=f'{self.cxx}',
            linker_so_cxx=f'{self.linker_dll_cxx} {shared_option}',
        )

    def runtime_library_dir_option(self, dir):
        raise DistutilsPlatformError(_runtime_library_dirs_msg)


# Because these compilers aren't configured in Python's pyconfig.h file by
# default, we should at least warn the user if he is using an unmodified
# version.

CONFIG_H_OK = "ok"
CONFIG_H_NOTOK = "not ok"
CONFIG_H_UNCERTAIN = "uncertain"


def check_config_h():
    """Check if the current Python installation appears amenable to building
    extensions with GCC.

    Returns a tuple (status, details), where 'status' is one of the following
    constants:

    - CONFIG_H_OK: all is well, go ahead and compile
    - CONFIG_H_NOTOK: doesn't look good
    - CONFIG_H_UNCERTAIN: not sure -- unable to read pyconfig.h

    'details' is a human-readable string explaining the situation.

    Note there are two ways to conclude "OK": either 'sys.version' contains
    the string "GCC" (implying that this Python was built with GCC), or the
    installed "pyconfig.h" contains the string "__GNUC__".
    """

    # XXX since this function also checks sys.version, it's not strictly a
    # "pyconfig.h" check -- should probably be renamed...

    from distutils import sysconfig

    # if sys.version contains GCC then python was compiled with GCC, and the
    # pyconfig.h file should be OK
    if "GCC" in sys.version:
        return CONFIG_H_OK, "sys.version mentions 'GCC'"

    # Clang would also work
    if "Clang" in sys.version:
        return CONFIG_H_OK, "sys.version mentions 'Clang'"

    # let's see if __GNUC__ is mentioned in python.h
    fn = sysconfig.get_config_h_filename()
    try:
        config_h = pathlib.Path(fn).read_text(encoding='utf-8')
    except OSError as exc:
        return (CONFIG_H_UNCERTAIN, f"couldn't read '{fn}': {exc.strerror}")
    else:
        substring = '__GNUC__'
        if substring in config_h:
            code = CONFIG_H_OK
            mention_inflected = 'mentions'
        else:
            code = CONFIG_H_NOTOK
            mention_inflected = 'does not mention'
        return code, f"{fn!r} {mention_inflected} {substring!r}"


def is_cygwincc(cc):
    """Try to determine if the compiler that would be used is from cygwin."""
    out_string = check_output(shlex.split(cc) + ['-dumpmachine'])
    return out_string.strip().endswith(b'cygwin')


get_versions = None
"""
A stand-in for the previous get_versions() function to prevent failures
when monkeypatched. See pypa/setuptools#2969.
"""

# === NexusCore/openenv\Lib\site-packages\tornado\test\testing_test.py ===
from tornado import gen, ioloop
from tornado.httpserver import HTTPServer
from tornado.locks import Event
from tornado.testing import AsyncHTTPTestCase, AsyncTestCase, bind_unused_port, gen_test
from tornado.web import Application
import asyncio
import contextlib
import gc
import os
import platform
import sys
import traceback
import unittest
import warnings


@contextlib.contextmanager
def set_environ(name, value):
    old_value = os.environ.get(name)
    os.environ[name] = value

    try:
        yield
    finally:
        if old_value is None:
            del os.environ[name]
        else:
            os.environ[name] = old_value


class AsyncTestCaseTest(AsyncTestCase):
    def test_wait_timeout(self):
        time = self.io_loop.time

        # Accept default 5-second timeout, no error
        self.io_loop.add_timeout(time() + 0.01, self.stop)
        self.wait()

        # Timeout passed to wait()
        self.io_loop.add_timeout(time() + 1, self.stop)
        with self.assertRaises(self.failureException):
            self.wait(timeout=0.01)

        # Timeout set with environment variable
        self.io_loop.add_timeout(time() + 1, self.stop)
        with set_environ("ASYNC_TEST_TIMEOUT", "0.01"):
            with self.assertRaises(self.failureException):
                self.wait()

    def test_subsequent_wait_calls(self):
        """
        This test makes sure that a second call to wait()
        clears the first timeout.
        """
        # The first wait ends with time left on the clock
        self.io_loop.add_timeout(self.io_loop.time() + 0.00, self.stop)
        self.wait(timeout=0.1)
        # The second wait has enough time for itself but would fail if the
        # first wait's deadline were still in effect.
        self.io_loop.add_timeout(self.io_loop.time() + 0.2, self.stop)
        self.wait(timeout=0.4)


class LeakTest(AsyncTestCase):
    def tearDown(self):
        super().tearDown()
        # Trigger a gc to make warnings more deterministic.
        gc.collect()

    def test_leaked_coroutine(self):
        # This test verifies that "leaked" coroutines are shut down
        # without triggering warnings like "task was destroyed but it
        # is pending". If this test were to fail, it would fail
        # because runtests.py detected unexpected output to stderr.
        event = Event()

        async def callback():
            try:
                await event.wait()
            except asyncio.CancelledError:
                pass

        self.io_loop.add_callback(callback)
        self.io_loop.add_callback(self.stop)
        self.wait()


class AsyncHTTPTestCaseTest(AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()
        # Bind a second port.
        sock, port = bind_unused_port()
        app = Application()
        server = HTTPServer(app, **self.get_httpserver_options())
        server.add_socket(sock)
        self.second_port = port
        self.second_server = server

    def get_app(self):
        return Application()

    def test_fetch_segment(self):
        path = "/path"
        response = self.fetch(path)
        self.assertEqual(response.request.url, self.get_url(path))

    def test_fetch_full_http_url(self):
        # Ensure that self.fetch() recognizes absolute urls and does
        # not transform them into references to our main test server.
        path = "http://127.0.0.1:%d/path" % self.second_port

        response = self.fetch(path)
        self.assertEqual(response.request.url, path)

    def tearDown(self):
        self.second_server.stop()
        super().tearDown()


class AsyncTestCaseReturnAssertionsTest(unittest.TestCase):
    # These tests verify that tests that return non-None values (without being decorated with
    # @gen_test) raise errors instead of incorrectly succeeding. These tests should be removed or
    # updated when the _callTestMethod method is removed from AsyncTestCase (the same checks will
    # still happen, but they'll be performed in the stdlib as DeprecationWarnings)
    def test_undecorated_generator(self):
        class Test(AsyncTestCase):
            def test_gen(self):
                yield

        test = Test("test_gen")
        result = unittest.TestResult()
        test.run(result)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("should be decorated", result.errors[0][1])

    @unittest.skipIf(
        platform.python_implementation() == "PyPy",
        "pypy destructor warnings cannot be silenced",
    )
    @unittest.skipIf(
        # This check actually exists in 3.11 but it changed in 3.12 in a way that breaks
        # this test.
        sys.version_info >= (3, 12),
        "py312 has its own check for test case returns",
    )
    def test_undecorated_coroutine(self):
        class Test(AsyncTestCase):
            async def test_coro(self):
                pass

        test = Test("test_coro")
        result = unittest.TestResult()

        # Silence "RuntimeWarning: coroutine 'test_coro' was never awaited".
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            test.run(result)

        self.assertEqual(len(result.errors), 1)
        self.assertIn("should be decorated", result.errors[0][1])

    def test_undecorated_generator_with_skip(self):
        class Test(AsyncTestCase):
            @unittest.skip("don't run this")
            def test_gen(self):
                yield

        test = Test("test_gen")
        result = unittest.TestResult()
        test.run(result)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.skipped), 1)

    def test_other_return(self):
        class Test(AsyncTestCase):
            def test_other_return(self):
                return 42

        test = Test("test_other_return")
        result = unittest.TestResult()
        test.run(result)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Return value from test method ignored", result.errors[0][1])


class SetUpTearDownTest(unittest.TestCase):
    def test_set_up_tear_down(self):
        """
        This test makes sure that AsyncTestCase calls super methods for
        setUp and tearDown.

        InheritBoth is a subclass of both AsyncTestCase and
        SetUpTearDown, with the ordering so that the super of
        AsyncTestCase will be SetUpTearDown.
        """
        events = []
        result = unittest.TestResult()

        class SetUpTearDown(unittest.TestCase):
            def setUp(self):
                events.append("setUp")

            def tearDown(self):
                events.append("tearDown")

        class InheritBoth(AsyncTestCase, SetUpTearDown):
            def test(self):
                events.append("test")

        InheritBoth("test").run(result)
        expected = ["setUp", "test", "tearDown"]
        self.assertEqual(expected, events)


class AsyncHTTPTestCaseSetUpTearDownTest(unittest.TestCase):
    def test_tear_down_releases_app_and_http_server(self):
        result = unittest.TestResult()

        class SetUpTearDown(AsyncHTTPTestCase):
            def get_app(self):
                return Application()

            def test(self):
                self.assertTrue(hasattr(self, "_app"))
                self.assertTrue(hasattr(self, "http_server"))

        test = SetUpTearDown("test")
        test.run(result)
        self.assertFalse(hasattr(test, "_app"))
        self.assertFalse(hasattr(test, "http_server"))


class GenTest(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.finished = False

    def tearDown(self):
        self.assertTrue(self.finished)
        super().tearDown()

    @gen_test
    def test_sync(self):
        self.finished = True

    @gen_test
    def test_async(self):
        yield gen.moment
        self.finished = True

    def test_timeout(self):
        # Set a short timeout and exceed it.
        @gen_test(timeout=0.1)
        def test(self):
            yield gen.sleep(1)

        # This can't use assertRaises because we need to inspect the
        # exc_info triple (and not just the exception object)
        try:
            test(self)
            self.fail("did not get expected exception")
        except ioloop.TimeoutError:
            # The stack trace should blame the add_timeout line, not just
            # unrelated IOLoop/testing internals.
            self.assertIn("gen.sleep(1)", traceback.format_exc())

        self.finished = True

    def test_no_timeout(self):
        # A test that does not exceed its timeout should succeed.
        @gen_test(timeout=1)
        def test(self):
            yield gen.sleep(0.1)

        test(self)
        self.finished = True

    def test_timeout_environment_variable(self):
        @gen_test(timeout=0.5)
        def test_long_timeout(self):
            yield gen.sleep(0.25)

        # Uses provided timeout of 0.5 seconds, doesn't time out.
        with set_environ("ASYNC_TEST_TIMEOUT", "0.1"):
            test_long_timeout(self)

        self.finished = True

    def test_no_timeout_environment_variable(self):
        @gen_test(timeout=0.01)
        def test_short_timeout(self):
            yield gen.sleep(1)

        # Uses environment-variable timeout of 0.1, times out.
        with set_environ("ASYNC_TEST_TIMEOUT", "0.1"):
            with self.assertRaises(ioloop.TimeoutError):
                test_short_timeout(self)

        self.finished = True

    def test_with_method_args(self):
        @gen_test
        def test_with_args(self, *args):
            self.assertEqual(args, ("test",))
            yield gen.moment

        test_with_args(self, "test")
        self.finished = True

    def test_with_method_kwargs(self):
        @gen_test
        def test_with_kwargs(self, **kwargs):
            self.assertDictEqual(kwargs, {"test": "test"})
            yield gen.moment

        test_with_kwargs(self, test="test")
        self.finished = True

    def test_native_coroutine(self):
        @gen_test
        async def test(self):
            self.finished = True

        test(self)

    def test_native_coroutine_timeout(self):
        # Set a short timeout and exceed it.
        @gen_test(timeout=0.1)
        async def test(self):
            await gen.sleep(1)

        try:
            test(self)
            self.fail("did not get expected exception")
        except ioloop.TimeoutError:
            self.finished = True


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\win32comext\adsi\adsicon.py ===
ADS_ATTR_CLEAR = 1
ADS_ATTR_UPDATE = 2
ADS_ATTR_APPEND = 3
ADS_ATTR_DELETE = 4
ADS_EXT_MINEXTDISPID = 1
ADS_EXT_MAXEXTDISPID = 16777215
ADS_EXT_INITCREDENTIALS = 1
ADS_EXT_INITIALIZE_COMPLETE = 2

ADS_SEARCHPREF_ASYNCHRONOUS = 0
ADS_SEARCHPREF_DEREF_ALIASES = 1
ADS_SEARCHPREF_SIZE_LIMIT = 2
ADS_SEARCHPREF_TIME_LIMIT = 3
ADS_SEARCHPREF_ATTRIBTYPES_ONLY = 4
ADS_SEARCHPREF_SEARCH_SCOPE = 5
ADS_SEARCHPREF_TIMEOUT = 6
ADS_SEARCHPREF_PAGESIZE = 7
ADS_SEARCHPREF_PAGED_TIME_LIMIT = 8
ADS_SEARCHPREF_CHASE_REFERRALS = 9
ADS_SEARCHPREF_SORT_ON = 10
ADS_SEARCHPREF_CACHE_RESULTS = 11
ADS_SEARCHPREF_DIRSYNC = 12
ADS_SEARCHPREF_TOMBSTONE = 13

ADS_SCOPE_BASE = 0
ADS_SCOPE_ONELEVEL = 1
ADS_SCOPE_SUBTREE = 2

ADS_SECURE_AUTHENTICATION = 0x1
ADS_USE_ENCRYPTION = 0x2
ADS_USE_SSL = 0x2
ADS_READONLY_SERVER = 0x4
ADS_PROMPT_CREDENTIALS = 0x8
ADS_NO_AUTHENTICATION = 0x10
ADS_FAST_BIND = 0x20
ADS_USE_SIGNING = 0x40
ADS_USE_SEALING = 0x80
ADS_USE_DELEGATION = 0x100
ADS_SERVER_BIND = 0x200

ADSTYPE_INVALID = 0
ADSTYPE_DN_STRING = ADSTYPE_INVALID + 1
ADSTYPE_CASE_EXACT_STRING = ADSTYPE_DN_STRING + 1
ADSTYPE_CASE_IGNORE_STRING = ADSTYPE_CASE_EXACT_STRING + 1
ADSTYPE_PRINTABLE_STRING = ADSTYPE_CASE_IGNORE_STRING + 1
ADSTYPE_NUMERIC_STRING = ADSTYPE_PRINTABLE_STRING + 1
ADSTYPE_BOOLEAN = ADSTYPE_NUMERIC_STRING + 1
ADSTYPE_INTEGER = ADSTYPE_BOOLEAN + 1
ADSTYPE_OCTET_STRING = ADSTYPE_INTEGER + 1
ADSTYPE_UTC_TIME = ADSTYPE_OCTET_STRING + 1
ADSTYPE_LARGE_INTEGER = ADSTYPE_UTC_TIME + 1
ADSTYPE_PROV_SPECIFIC = ADSTYPE_LARGE_INTEGER + 1
ADSTYPE_OBJECT_CLASS = ADSTYPE_PROV_SPECIFIC + 1
ADSTYPE_CASEIGNORE_LIST = ADSTYPE_OBJECT_CLASS + 1
ADSTYPE_OCTET_LIST = ADSTYPE_CASEIGNORE_LIST + 1
ADSTYPE_PATH = ADSTYPE_OCTET_LIST + 1
ADSTYPE_POSTALADDRESS = ADSTYPE_PATH + 1
ADSTYPE_TIMESTAMP = ADSTYPE_POSTALADDRESS + 1
ADSTYPE_BACKLINK = ADSTYPE_TIMESTAMP + 1
ADSTYPE_TYPEDNAME = ADSTYPE_BACKLINK + 1
ADSTYPE_HOLD = ADSTYPE_TYPEDNAME + 1
ADSTYPE_NETADDRESS = ADSTYPE_HOLD + 1
ADSTYPE_REPLICAPOINTER = ADSTYPE_NETADDRESS + 1
ADSTYPE_FAXNUMBER = ADSTYPE_REPLICAPOINTER + 1
ADSTYPE_EMAIL = ADSTYPE_FAXNUMBER + 1
ADSTYPE_NT_SECURITY_DESCRIPTOR = ADSTYPE_EMAIL + 1
ADSTYPE_UNKNOWN = ADSTYPE_NT_SECURITY_DESCRIPTOR + 1
ADSTYPE_DN_WITH_BINARY = ADSTYPE_UNKNOWN + 1
ADSTYPE_DN_WITH_STRING = ADSTYPE_DN_WITH_BINARY + 1

ADS_PROPERTY_CLEAR = 1
ADS_PROPERTY_UPDATE = 2
ADS_PROPERTY_APPEND = 3
ADS_PROPERTY_DELETE = 4
ADS_SYSTEMFLAG_DISALLOW_DELETE = -2147483648
ADS_SYSTEMFLAG_CONFIG_ALLOW_RENAME = 0x40000000
ADS_SYSTEMFLAG_CONFIG_ALLOW_MOVE = 0x20000000
ADS_SYSTEMFLAG_CONFIG_ALLOW_LIMITED_MOVE = 0x10000000
ADS_SYSTEMFLAG_DOMAIN_DISALLOW_RENAME = -2147483648
ADS_SYSTEMFLAG_DOMAIN_DISALLOW_MOVE = 0x4000000
ADS_SYSTEMFLAG_CR_NTDS_NC = 0x1
ADS_SYSTEMFLAG_CR_NTDS_DOMAIN = 0x2
ADS_SYSTEMFLAG_ATTR_NOT_REPLICATED = 0x1
ADS_SYSTEMFLAG_ATTR_IS_CONSTRUCTED = 0x4
ADS_GROUP_TYPE_GLOBAL_GROUP = 0x2
ADS_GROUP_TYPE_DOMAIN_LOCAL_GROUP = 0x4
ADS_GROUP_TYPE_LOCAL_GROUP = 0x4
ADS_GROUP_TYPE_UNIVERSAL_GROUP = 0x8
ADS_GROUP_TYPE_SECURITY_ENABLED = -2147483648
ADS_UF_SCRIPT = 0x1
ADS_UF_ACCOUNTDISABLE = 0x2
ADS_UF_HOMEDIR_REQUIRED = 0x8
ADS_UF_LOCKOUT = 0x10
ADS_UF_PASSWD_NOTREQD = 0x20
ADS_UF_PASSWD_CANT_CHANGE = 0x40
ADS_UF_ENCRYPTED_TEXT_PASSWORD_ALLOWED = 0x80
ADS_UF_TEMP_DUPLICATE_ACCOUNT = 0x100
ADS_UF_NORMAL_ACCOUNT = 0x200
ADS_UF_INTERDOMAIN_TRUST_ACCOUNT = 0x800
ADS_UF_WORKSTATION_TRUST_ACCOUNT = 0x1000
ADS_UF_SERVER_TRUST_ACCOUNT = 0x2000
ADS_UF_DONT_EXPIRE_PASSWD = 0x10000
ADS_UF_MNS_LOGON_ACCOUNT = 0x20000
ADS_UF_SMARTCARD_REQUIRED = 0x40000
ADS_UF_TRUSTED_FOR_DELEGATION = 0x80000
ADS_UF_NOT_DELEGATED = 0x100000
ADS_UF_USE_DES_KEY_ONLY = 0x200000
ADS_UF_DONT_REQUIRE_PREAUTH = 0x400000
ADS_UF_PASSWORD_EXPIRED = 0x800000
ADS_UF_TRUSTED_TO_AUTHENTICATE_FOR_DELEGATION = 0x1000000
ADS_RIGHT_DELETE = 0x10000
ADS_RIGHT_READ_CONTROL = 0x20000
ADS_RIGHT_WRITE_DAC = 0x40000
ADS_RIGHT_WRITE_OWNER = 0x80000
ADS_RIGHT_SYNCHRONIZE = 0x100000
ADS_RIGHT_ACCESS_SYSTEM_SECURITY = 0x1000000
ADS_RIGHT_GENERIC_READ = -2147483648
ADS_RIGHT_GENERIC_WRITE = 0x40000000
ADS_RIGHT_GENERIC_EXECUTE = 0x20000000
ADS_RIGHT_GENERIC_ALL = 0x10000000
ADS_RIGHT_DS_CREATE_CHILD = 0x1
ADS_RIGHT_DS_DELETE_CHILD = 0x2
ADS_RIGHT_ACTRL_DS_LIST = 0x4
ADS_RIGHT_DS_SELF = 0x8
ADS_RIGHT_DS_READ_PROP = 0x10
ADS_RIGHT_DS_WRITE_PROP = 0x20
ADS_RIGHT_DS_DELETE_TREE = 0x40
ADS_RIGHT_DS_LIST_OBJECT = 0x80
ADS_RIGHT_DS_CONTROL_ACCESS = 0x100
ADS_ACETYPE_ACCESS_ALLOWED = 0
ADS_ACETYPE_ACCESS_DENIED = 0x1
ADS_ACETYPE_SYSTEM_AUDIT = 0x2
ADS_ACETYPE_ACCESS_ALLOWED_OBJECT = 0x5
ADS_ACETYPE_ACCESS_DENIED_OBJECT = 0x6
ADS_ACETYPE_SYSTEM_AUDIT_OBJECT = 0x7
ADS_ACETYPE_SYSTEM_ALARM_OBJECT = 0x8
ADS_ACETYPE_ACCESS_ALLOWED_CALLBACK = 0x9
ADS_ACETYPE_ACCESS_DENIED_CALLBACK = 0xA
ADS_ACETYPE_ACCESS_ALLOWED_CALLBACK_OBJECT = 0xB
ADS_ACETYPE_ACCESS_DENIED_CALLBACK_OBJECT = 0xC
ADS_ACETYPE_SYSTEM_AUDIT_CALLBACK = 0xD
ADS_ACETYPE_SYSTEM_ALARM_CALLBACK = 0xE
ADS_ACETYPE_SYSTEM_AUDIT_CALLBACK_OBJECT = 0xF
ADS_ACETYPE_SYSTEM_ALARM_CALLBACK_OBJECT = 0x10
ADS_ACEFLAG_INHERIT_ACE = 0x2
ADS_ACEFLAG_NO_PROPAGATE_INHERIT_ACE = 0x4
ADS_ACEFLAG_INHERIT_ONLY_ACE = 0x8
ADS_ACEFLAG_INHERITED_ACE = 0x10
ADS_ACEFLAG_VALID_INHERIT_FLAGS = 0x1F
ADS_ACEFLAG_SUCCESSFUL_ACCESS = 0x40
ADS_ACEFLAG_FAILED_ACCESS = 0x80
ADS_FLAG_OBJECT_TYPE_PRESENT = 0x1
ADS_FLAG_INHERITED_OBJECT_TYPE_PRESENT = 0x2
ADS_SD_CONTROL_SE_OWNER_DEFAULTED = 0x1
ADS_SD_CONTROL_SE_GROUP_DEFAULTED = 0x2
ADS_SD_CONTROL_SE_DACL_PRESENT = 0x4
ADS_SD_CONTROL_SE_DACL_DEFAULTED = 0x8
ADS_SD_CONTROL_SE_SACL_PRESENT = 0x10
ADS_SD_CONTROL_SE_SACL_DEFAULTED = 0x20
ADS_SD_CONTROL_SE_DACL_AUTO_INHERIT_REQ = 0x100
ADS_SD_CONTROL_SE_SACL_AUTO_INHERIT_REQ = 0x200
ADS_SD_CONTROL_SE_DACL_AUTO_INHERITED = 0x400
ADS_SD_CONTROL_SE_SACL_AUTO_INHERITED = 0x800
ADS_SD_CONTROL_SE_DACL_PROTECTED = 0x1000
ADS_SD_CONTROL_SE_SACL_PROTECTED = 0x2000
ADS_SD_CONTROL_SE_SELF_RELATIVE = 0x8000
ADS_SD_REVISION_DS = 4
ADS_NAME_TYPE_1779 = 1
ADS_NAME_TYPE_CANONICAL = 2
ADS_NAME_TYPE_NT4 = 3
ADS_NAME_TYPE_DISPLAY = 4
ADS_NAME_TYPE_DOMAIN_SIMPLE = 5
ADS_NAME_TYPE_ENTERPRISE_SIMPLE = 6
ADS_NAME_TYPE_GUID = 7
ADS_NAME_TYPE_UNKNOWN = 8
ADS_NAME_TYPE_USER_PRINCIPAL_NAME = 9
ADS_NAME_TYPE_CANONICAL_EX = 10
ADS_NAME_TYPE_SERVICE_PRINCIPAL_NAME = 11
ADS_NAME_TYPE_SID_OR_SID_HISTORY_NAME = 12
ADS_NAME_INITTYPE_DOMAIN = 1
ADS_NAME_INITTYPE_SERVER = 2
ADS_NAME_INITTYPE_GC = 3
ADS_OPTION_SERVERNAME = 0
ADS_OPTION_REFERRALS = ADS_OPTION_SERVERNAME + 1
ADS_OPTION_PAGE_SIZE = ADS_OPTION_REFERRALS + 1
ADS_OPTION_SECURITY_MASK = ADS_OPTION_PAGE_SIZE + 1
ADS_OPTION_MUTUAL_AUTH_STATUS = ADS_OPTION_SECURITY_MASK + 1
ADS_OPTION_QUOTA = ADS_OPTION_MUTUAL_AUTH_STATUS + 1
ADS_OPTION_PASSWORD_PORTNUMBER = ADS_OPTION_QUOTA + 1
ADS_OPTION_PASSWORD_METHOD = ADS_OPTION_PASSWORD_PORTNUMBER + 1
ADS_SECURITY_INFO_OWNER = 0x1
ADS_SECURITY_INFO_GROUP = 0x2
ADS_SECURITY_INFO_DACL = 0x4
ADS_SECURITY_INFO_SACL = 0x8
ADS_SETTYPE_FULL = 1
ADS_SETTYPE_PROVIDER = 2
ADS_SETTYPE_SERVER = 3
ADS_SETTYPE_DN = 4
ADS_FORMAT_WINDOWS = 1
ADS_FORMAT_WINDOWS_NO_SERVER = 2
ADS_FORMAT_WINDOWS_DN = 3
ADS_FORMAT_WINDOWS_PARENT = 4
ADS_FORMAT_X500 = 5
ADS_FORMAT_X500_NO_SERVER = 6
ADS_FORMAT_X500_DN = 7
ADS_FORMAT_X500_PARENT = 8
ADS_FORMAT_SERVER = 9
ADS_FORMAT_PROVIDER = 10
ADS_FORMAT_LEAF = 11
ADS_DISPLAY_FULL = 1
ADS_DISPLAY_VALUE_ONLY = 2
ADS_ESCAPEDMODE_DEFAULT = 1
ADS_ESCAPEDMODE_ON = 2
ADS_ESCAPEDMODE_OFF = 3
ADS_ESCAPEDMODE_OFF_EX = 4
ADS_PATH_FILE = 1
ADS_PATH_FILESHARE = 2
ADS_PATH_REGISTRY = 3
ADS_SD_FORMAT_IID = 1
ADS_SD_FORMAT_RAW = 2
ADS_SD_FORMAT_HEXSTRING = 3


# Generated by h2py from AdsErr.h
def _HRESULT_TYPEDEF_(_sc):
    return _sc


E_ADS_BAD_PATHNAME = _HRESULT_TYPEDEF_(-2147463168)
E_ADS_INVALID_DOMAIN_OBJECT = _HRESULT_TYPEDEF_(-2147463167)
E_ADS_INVALID_USER_OBJECT = _HRESULT_TYPEDEF_(-2147463166)
E_ADS_INVALID_COMPUTER_OBJECT = _HRESULT_TYPEDEF_(-2147463165)
E_ADS_UNKNOWN_OBJECT = _HRESULT_TYPEDEF_(-2147463164)
E_ADS_PROPERTY_NOT_SET = _HRESULT_TYPEDEF_(-2147463163)
E_ADS_PROPERTY_NOT_SUPPORTED = _HRESULT_TYPEDEF_(-2147463162)
E_ADS_PROPERTY_INVALID = _HRESULT_TYPEDEF_(-2147463161)
E_ADS_BAD_PARAMETER = _HRESULT_TYPEDEF_(-2147463160)
E_ADS_OBJECT_UNBOUND = _HRESULT_TYPEDEF_(-2147463159)
E_ADS_PROPERTY_NOT_MODIFIED = _HRESULT_TYPEDEF_(-2147463158)
E_ADS_PROPERTY_MODIFIED = _HRESULT_TYPEDEF_(-2147463157)
E_ADS_CANT_CONVERT_DATATYPE = _HRESULT_TYPEDEF_(-2147463156)
E_ADS_PROPERTY_NOT_FOUND = _HRESULT_TYPEDEF_(-2147463155)
E_ADS_OBJECT_EXISTS = _HRESULT_TYPEDEF_(-2147463154)
E_ADS_SCHEMA_VIOLATION = _HRESULT_TYPEDEF_(-2147463153)
E_ADS_COLUMN_NOT_SET = _HRESULT_TYPEDEF_(-2147463152)
S_ADS_ERRORSOCCURRED = _HRESULT_TYPEDEF_(0x00005011)
S_ADS_NOMORE_ROWS = _HRESULT_TYPEDEF_(0x00005012)
S_ADS_NOMORE_COLUMNS = _HRESULT_TYPEDEF_(0x00005013)
E_ADS_INVALID_FILTER = _HRESULT_TYPEDEF_(-2147463148)

# ADS_DEREFENUM enum
ADS_DEREF_NEVER = 0
ADS_DEREF_SEARCHING = 1
ADS_DEREF_FINDING = 2
ADS_DEREF_ALWAYS = 3

# ADS_PREFERENCES_ENUM
ADSIPROP_ASYNCHRONOUS = 0
ADSIPROP_DEREF_ALIASES = 0x1
ADSIPROP_SIZE_LIMIT = 0x2
ADSIPROP_TIME_LIMIT = 0x3
ADSIPROP_ATTRIBTYPES_ONLY = 0x4
ADSIPROP_SEARCH_SCOPE = 0x5
ADSIPROP_TIMEOUT = 0x6
ADSIPROP_PAGESIZE = 0x7
ADSIPROP_PAGED_TIME_LIMIT = 0x8
ADSIPROP_CHASE_REFERRALS = 0x9
ADSIPROP_SORT_ON = 0xA
ADSIPROP_CACHE_RESULTS = 0xB
ADSIPROP_ADSIFLAG = 0xC

# ADSI_DIALECT_ENUM
ADSI_DIALECT_LDAP = 0
ADSI_DIALECT_SQL = 0x1

# ADS_CHASE_REFERRALS_ENUM
ADS_CHASE_REFERRALS_NEVER = 0
ADS_CHASE_REFERRALS_SUBORDINATE = 0x20
ADS_CHASE_REFERRALS_EXTERNAL = 0x40
ADS_CHASE_REFERRALS_ALWAYS = (
    ADS_CHASE_REFERRALS_SUBORDINATE | ADS_CHASE_REFERRALS_EXTERNAL
)

# Generated by h2py from ObjSel.h
DSOP_SCOPE_TYPE_TARGET_COMPUTER = 0x00000001
DSOP_SCOPE_TYPE_UPLEVEL_JOINED_DOMAIN = 0x00000002
DSOP_SCOPE_TYPE_DOWNLEVEL_JOINED_DOMAIN = 0x00000004
DSOP_SCOPE_TYPE_ENTERPRISE_DOMAIN = 0x00000008
DSOP_SCOPE_TYPE_GLOBAL_CATALOG = 0x00000010
DSOP_SCOPE_TYPE_EXTERNAL_UPLEVEL_DOMAIN = 0x00000020
DSOP_SCOPE_TYPE_EXTERNAL_DOWNLEVEL_DOMAIN = 0x00000040
DSOP_SCOPE_TYPE_WORKGROUP = 0x00000080
DSOP_SCOPE_TYPE_USER_ENTERED_UPLEVEL_SCOPE = 0x00000100
DSOP_SCOPE_TYPE_USER_ENTERED_DOWNLEVEL_SCOPE = 0x00000200
DSOP_SCOPE_FLAG_STARTING_SCOPE = 0x00000001
DSOP_SCOPE_FLAG_WANT_PROVIDER_WINNT = 0x00000002
DSOP_SCOPE_FLAG_WANT_PROVIDER_LDAP = 0x00000004
DSOP_SCOPE_FLAG_WANT_PROVIDER_GC = 0x00000008
DSOP_SCOPE_FLAG_WANT_SID_PATH = 0x00000010
DSOP_SCOPE_FLAG_WANT_DOWNLEVEL_BUILTIN_PATH = 0x00000020
DSOP_SCOPE_FLAG_DEFAULT_FILTER_USERS = 0x00000040
DSOP_SCOPE_FLAG_DEFAULT_FILTER_GROUPS = 0x00000080
DSOP_SCOPE_FLAG_DEFAULT_FILTER_COMPUTERS = 0x00000100
DSOP_SCOPE_FLAG_DEFAULT_FILTER_CONTACTS = 0x00000200
DSOP_FILTER_INCLUDE_ADVANCED_VIEW = 0x00000001
DSOP_FILTER_USERS = 0x00000002
DSOP_FILTER_BUILTIN_GROUPS = 0x00000004
DSOP_FILTER_WELL_KNOWN_PRINCIPALS = 0x00000008
DSOP_FILTER_UNIVERSAL_GROUPS_DL = 0x00000010
DSOP_FILTER_UNIVERSAL_GROUPS_SE = 0x00000020
DSOP_FILTER_GLOBAL_GROUPS_DL = 0x00000040
DSOP_FILTER_GLOBAL_GROUPS_SE = 0x00000080
DSOP_FILTER_DOMAIN_LOCAL_GROUPS_DL = 0x00000100
DSOP_FILTER_DOMAIN_LOCAL_GROUPS_SE = 0x00000200
DSOP_FILTER_CONTACTS = 0x00000400
DSOP_FILTER_COMPUTERS = 0x00000800
DSOP_DOWNLEVEL_FILTER_USERS = -2147483647
DSOP_DOWNLEVEL_FILTER_LOCAL_GROUPS = -2147483646
DSOP_DOWNLEVEL_FILTER_GLOBAL_GROUPS = -2147483644
DSOP_DOWNLEVEL_FILTER_COMPUTERS = -2147483640
DSOP_DOWNLEVEL_FILTER_WORLD = -2147483632
DSOP_DOWNLEVEL_FILTER_AUTHENTICATED_USER = -2147483616
DSOP_DOWNLEVEL_FILTER_ANONYMOUS = -2147483584
DSOP_DOWNLEVEL_FILTER_BATCH = -2147483520
DSOP_DOWNLEVEL_FILTER_CREATOR_OWNER = -2147483392
DSOP_DOWNLEVEL_FILTER_CREATOR_GROUP = -2147483136
DSOP_DOWNLEVEL_FILTER_DIALUP = -2147482624
DSOP_DOWNLEVEL_FILTER_INTERACTIVE = -2147481600
DSOP_DOWNLEVEL_FILTER_NETWORK = -2147479552
DSOP_DOWNLEVEL_FILTER_SERVICE = -2147475456
DSOP_DOWNLEVEL_FILTER_SYSTEM = -2147467264
DSOP_DOWNLEVEL_FILTER_EXCLUDE_BUILTIN_GROUPS = -2147450880
DSOP_DOWNLEVEL_FILTER_TERMINAL_SERVER = -2147418112
DSOP_DOWNLEVEL_FILTER_ALL_WELLKNOWN_SIDS = -2147352576
DSOP_DOWNLEVEL_FILTER_LOCAL_SERVICE = -2147221504
DSOP_DOWNLEVEL_FILTER_NETWORK_SERVICE = -2146959360
DSOP_DOWNLEVEL_FILTER_REMOTE_LOGON = -2146435072
DSOP_FLAG_MULTISELECT = 0x00000001
DSOP_FLAG_SKIP_TARGET_COMPUTER_DC_CHECK = 0x00000002
CFSTR_DSOP_DS_SELECTION_LIST = "CFSTR_DSOP_DS_SELECTION_LIST"

# === NexusCore/openenv\Lib\site-packages\contourpy\util\bokeh_renderer.py ===
from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

from bokeh.io import export_png, export_svg, show
from bokeh.io.export import get_screenshot_as_png
from bokeh.layouts import gridplot
from bokeh.models.annotations.labels import Label
from bokeh.palettes import Category10
from bokeh.plotting import figure
import numpy as np

from contourpy.enum_util import as_fill_type, as_line_type
from contourpy.util.bokeh_util import filled_to_bokeh, lines_to_bokeh
from contourpy.util.renderer import Renderer

if TYPE_CHECKING:
    from bokeh.core.enums import OutputBackendType
    from bokeh.models import GridPlot
    from bokeh.palettes import Palette
    from numpy.typing import ArrayLike
    from selenium.webdriver.remote.webdriver import WebDriver

    from contourpy import FillType, LineType
    from contourpy._contourpy import FillReturn, LineReturn


class BokehRenderer(Renderer):
    """Utility renderer using Bokeh to render a grid of plots over the same (x, y) range.

    Args:
        nrows (int, optional): Number of rows of plots, default ``1``.
        ncols (int, optional): Number of columns of plots, default ``1``.
        figsize (tuple(float, float), optional): Figure size in inches (assuming 100 dpi), default
            ``(9, 9)``.
        show_frame (bool, optional): Whether to show frame and axes ticks, default ``True``.
        want_svg (bool, optional): Whether output is required in SVG format or not, default
            ``False``.

    Warning:
        :class:`~.BokehRenderer`, unlike :class:`~.MplRenderer`, needs to be told in advance if
        output to SVG format will be required later, otherwise it will assume PNG output.
    """
    _figures: list[figure]
    _layout: GridPlot
    _palette: Palette
    _want_svg: bool

    def __init__(
        self,
        nrows: int = 1,
        ncols: int = 1,
        figsize: tuple[float, float] = (9, 9),
        show_frame: bool = True,
        want_svg: bool = False,
    ) -> None:
        self._want_svg = want_svg
        self._palette = Category10[10]

        total_size = 100*np.asarray(figsize, dtype=int)  # Assuming 100 dpi.

        nfigures = nrows*ncols
        self._figures = []
        backend: OutputBackendType = "svg" if self._want_svg else "canvas"
        for _ in range(nfigures):
            fig = figure(output_backend=backend)
            fig.xgrid.visible = False  # type: ignore[attr-defined]
            fig.ygrid.visible = False  # type: ignore[attr-defined]
            self._figures.append(fig)
            if not show_frame:
                fig.outline_line_color = None
                fig.axis.visible = False  # type: ignore[attr-defined]

        self._layout = gridplot(
            self._figures, ncols=ncols, toolbar_location=None,  # type: ignore[arg-type]
            width=total_size[0] // ncols, height=total_size[1] // nrows)

    def _convert_color(self, color: str) -> str:
        if isinstance(color, str) and color[0] == "C":
            index = int(color[1:])
            color = self._palette[index]
        return color

    def _get_figure(self, ax: figure | int) -> figure:
        if isinstance(ax, int):
            ax = self._figures[ax]
        return ax

    def filled(
        self,
        filled: FillReturn,
        fill_type: FillType | str,
        ax: figure | int = 0,
        color: str = "C0",
        alpha: float = 0.7,
    ) -> None:
        """Plot filled contours on a single plot.

        Args:
            filled (sequence of arrays): Filled contour data as returned by
                :meth:`~.ContourGenerator.filled`.
            fill_type (FillType or str): Type of :meth:`~.ContourGenerator.filled` data as returned
                by :attr:`~.ContourGenerator.fill_type`, or a string equivalent.
            ax (int or Bokeh Figure, optional): Which plot to use, default ``0``.
            color (str, optional): Color to plot with. May be a string color or the letter ``"C"``
                followed by an integer in the range ``"C0"`` to ``"C9"`` to use a color from the
                ``Category10`` palette. Default ``"C0"``.
            alpha (float, optional): Opacity to plot with, default ``0.7``.
        """
        fill_type = as_fill_type(fill_type)
        fig = self._get_figure(ax)
        color = self._convert_color(color)
        xs, ys = filled_to_bokeh(filled, fill_type)
        if len(xs) > 0:
            fig.multi_polygons(xs=[xs], ys=[ys], color=color, fill_alpha=alpha, line_width=0)  # type: ignore[arg-type]

    def grid(
        self,
        x: ArrayLike,
        y: ArrayLike,
        ax: figure | int = 0,
        color: str = "black",
        alpha: float = 0.1,
        point_color: str | None = None,
        quad_as_tri_alpha: float = 0,
    ) -> None:
        """Plot quad grid lines on a single plot.

        Args:
            x (array-like of shape (ny, nx) or (nx,)): The x-coordinates of the grid points.
            y (array-like of shape (ny, nx) or (ny,)): The y-coordinates of the grid points.
            ax (int or Bokeh Figure, optional): Which plot to use, default ``0``.
            color (str, optional): Color to plot grid lines, default ``"black"``.
            alpha (float, optional): Opacity to plot lines with, default ``0.1``.
            point_color (str, optional): Color to plot grid points or ``None`` if grid points
                should not be plotted, default ``None``.
            quad_as_tri_alpha (float, optional): Opacity to plot ``quad_as_tri`` grid, default
                ``0``.

        Colors may be a string color or the letter ``"C"`` followed by an integer in the range
        ``"C0"`` to ``"C9"`` to use a color from the ``Category10`` palette.

        Warning:
            ``quad_as_tri_alpha > 0`` plots all quads as though they are unmasked.
        """
        fig = self._get_figure(ax)
        x, y = self._grid_as_2d(x, y)
        xs = list(x) + list(x.T)
        ys = list(y) + list(y.T)
        kwargs = {"line_color": color, "alpha": alpha}
        fig.multi_line(xs, ys, **kwargs)
        if quad_as_tri_alpha > 0:
            # Assumes no quad mask.
            xmid = (0.25*(x[:-1, :-1] + x[1:, :-1] + x[:-1, 1:] + x[1:, 1:])).ravel()
            ymid = (0.25*(y[:-1, :-1] + y[1:, :-1] + y[:-1, 1:] + y[1:, 1:])).ravel()
            fig.multi_line(
                list(np.stack((x[:-1, :-1].ravel(), xmid, x[1:, 1:].ravel()), axis=1)),
                list(np.stack((y[:-1, :-1].ravel(), ymid, y[1:, 1:].ravel()), axis=1)),
                **kwargs)
            fig.multi_line(
                list(np.stack((x[:-1, 1:].ravel(), xmid, x[1:, :-1].ravel()), axis=1)),
                list(np.stack((y[:-1, 1:].ravel(), ymid, y[1:, :-1].ravel()), axis=1)),
                **kwargs)
        if point_color is not None:
            fig.scatter(
                x=x.ravel(), y=y.ravel(), fill_color=color, line_color=None, alpha=alpha,
                marker="circle", size=8)

    def lines(
        self,
        lines: LineReturn,
        line_type: LineType | str,
        ax: figure | int = 0,
        color: str = "C0",
        alpha: float = 1.0,
        linewidth: float = 1,
    ) -> None:
        """Plot contour lines on a single plot.

        Args:
            lines (sequence of arrays): Contour line data as returned by
                :meth:`~.ContourGenerator.lines`.
            line_type (LineType or str): Type of :meth:`~.ContourGenerator.lines` data as returned
                by :attr:`~.ContourGenerator.line_type`, or a string equivalent.
            ax (int or Bokeh Figure, optional): Which plot to use, default ``0``.
            color (str, optional): Color to plot lines. May be a string color or the letter ``"C"``
                followed by an integer in the range ``"C0"`` to ``"C9"`` to use a color from the
                ``Category10`` palette. Default ``"C0"``.
            alpha (float, optional): Opacity to plot lines with, default ``1.0``.
            linewidth (float, optional): Width of lines, default ``1``.

        Note:
            Assumes all lines are open line strips not closed line loops.
        """
        line_type = as_line_type(line_type)
        fig = self._get_figure(ax)
        color = self._convert_color(color)
        xs, ys = lines_to_bokeh(lines, line_type)
        if xs is not None:
            assert ys is not None
            fig.line(xs, ys, line_color=color, line_alpha=alpha, line_width=linewidth)

    def mask(
        self,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike | np.ma.MaskedArray[Any, Any],
        ax: figure | int = 0,
        color: str = "black",
    ) -> None:
        """Plot masked out grid points as circles on a single plot.

        Args:
            x (array-like of shape (ny, nx) or (nx,)): The x-coordinates of the grid points.
            y (array-like of shape (ny, nx) or (ny,)): The y-coordinates of the grid points.
            z (masked array of shape (ny, nx): z-values.
            ax (int or Bokeh Figure, optional): Which plot to use, default ``0``.
            color (str, optional): Circle color, default ``"black"``.
        """
        mask = np.ma.getmask(z)  # type: ignore[no-untyped-call]
        if mask is np.ma.nomask:
            return
        fig = self._get_figure(ax)
        color = self._convert_color(color)
        x, y = self._grid_as_2d(x, y)
        fig.scatter(x[mask], y[mask], fill_color=color, marker="circle", size=10)

    def save(
        self,
        filename: str,
        transparent: bool = False,
        *,
        webdriver: WebDriver | None = None,
    ) -> None:
        """Save plots to SVG or PNG file.

        Args:
            filename (str): Filename to save to.
            transparent (bool, optional): Whether background should be transparent, default
                ``False``.
            webdriver (WebDriver, optional): Selenium WebDriver instance to use to create the image.

                .. versionadded:: 1.1.1

        Warning:
            To output to SVG file, ``want_svg=True`` must have been passed to the constructor.
        """
        if transparent:
            for fig in self._figures:
                fig.background_fill_color = None
                fig.border_fill_color = None

        if self._want_svg:
            export_svg(self._layout, filename=filename, webdriver=webdriver)
        else:
            export_png(self._layout, filename=filename, webdriver=webdriver)

    def save_to_buffer(self, *, webdriver: WebDriver | None = None) -> io.BytesIO:
        """Save plots to an ``io.BytesIO`` buffer.

        Args:
            webdriver (WebDriver, optional): Selenium WebDriver instance to use to create the image.

                .. versionadded:: 1.1.1

        Return:
            BytesIO: PNG image buffer.
        """
        image = get_screenshot_as_png(self._layout, driver=webdriver)
        buffer = io.BytesIO()
        image.save(buffer, "png")
        return buffer

    def show(self) -> None:
        """Show plots in web browser, in usual Bokeh manner.
        """
        show(self._layout)

    def title(self, title: str, ax: figure | int = 0, color: str | None = None) -> None:
        """Set the title of a single plot.

        Args:
            title (str): Title text.
            ax (int or Bokeh Figure, optional): Which plot to set the title of, default ``0``.
            color (str, optional): Color to set title. May be a string color or the letter ``"C"``
                followed by an integer in the range ``"C0"`` to ``"C9"`` to use a color from the
                ``Category10`` palette. Default ``None`` which is ``black``.
        """
        fig = self._get_figure(ax)
        fig.title = title
        fig.title.align = "center"  # type: ignore[attr-defined]
        if color is not None:
            fig.title.text_color = self._convert_color(color)  # type: ignore[attr-defined]

    def z_values(
        self,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike,
        ax: figure | int = 0,
        color: str = "green",
        fmt: str = ".1f",
        quad_as_tri: bool = False,
    ) -> None:
        """Show ``z`` values on a single plot.

        Args:
            x (array-like of shape (ny, nx) or (nx,)): The x-coordinates of the grid points.
            y (array-like of shape (ny, nx) or (ny,)): The y-coordinates of the grid points.
            z (array-like of shape (ny, nx): z-values.
            ax (int or Bokeh Figure, optional): Which plot to use, default ``0``.
            color (str, optional): Color of added text. May be a string color or the letter ``"C"``
                followed by an integer in the range ``"C0"`` to ``"C9"`` to use a color from the
                ``Category10`` palette. Default ``"green"``.
            fmt (str, optional): Format to display z-values, default ``".1f"``.
            quad_as_tri (bool, optional): Whether to show z-values at the ``quad_as_tri`` centres
                of quads.

        Warning:
            ``quad_as_tri=True`` shows z-values for all quads, even if masked.
        """
        fig = self._get_figure(ax)
        color = self._convert_color(color)
        x, y = self._grid_as_2d(x, y)
        z = np.asarray(z)
        ny, nx = z.shape
        kwargs = {"text_color": color, "text_align": "center", "text_baseline": "middle"}
        for j in range(ny):
            for i in range(nx):
                label = Label(x=x[j, i], y=y[j, i], text=f"{z[j, i]:{fmt}}", **kwargs)  # type: ignore[arg-type]
                fig.add_layout(label)
        if quad_as_tri:
            for j in range(ny-1):
                for i in range(nx-1):
                    xx = np.mean(x[j:j+2, i:i+2])
                    yy = np.mean(y[j:j+2, i:i+2])
                    zz = np.mean(z[j:j+2, i:i+2])
                    fig.add_layout(Label(x=xx, y=yy, text=f"{zz:{fmt}}", **kwargs))  # type: ignore[arg-type]

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_runpy.py ===
"""
Vendored copy of runpy from the standard library.

It's vendored so that we can properly ignore it when used to start user code
while still making it possible for the user to debug runpy itself.

runpy.py - locating and running Python code using the module namespace

Provides support for locating and running Python scripts using the Python
module namespace instead of the native filesystem.

This allows Python code to play nicely with non-filesystem based PEP 302
importers when locating support scripts as well as when importing modules.
"""
# Written by Nick Coghlan <ncoghlan at gmail.com>
#    to implement PEP 338 (Executing Modules as Scripts)

import sys
import importlib.machinery  # importlib first so we can test #15386 via -m
import importlib.util
import io
import types
import os

__all__ = [
    "run_module",
    "run_path",
]


# Note: fabioz: Don't use pkgutil (when handling caught exceptions we could end up
# showing exceptions in pkgutil.get_imported (specifically the KeyError), so,
# create a copy of the function we need to properly ignore this exception when
# running the program.
def pkgutil_get_importer(path_item):
    """Retrieve a finder for the given path item

    The returned finder is cached in sys.path_importer_cache
    if it was newly created by a path hook.

    The cache (or part of it) can be cleared manually if a
    rescan of sys.path_hooks is necessary.
    """
    try:
        importer = sys.path_importer_cache[path_item]
    except KeyError:
        for path_hook in sys.path_hooks:
            try:
                importer = path_hook(path_item)
                sys.path_importer_cache.setdefault(path_item, importer)
                break
            except ImportError:
                pass
        else:
            importer = None
    return importer


class _TempModule(object):
    """Temporarily replace a module in sys.modules with an empty namespace"""

    def __init__(self, mod_name):
        self.mod_name = mod_name
        self.module = types.ModuleType(mod_name)
        self._saved_module = []

    def __enter__(self):
        mod_name = self.mod_name
        try:
            self._saved_module.append(sys.modules[mod_name])
        except KeyError:
            pass
        sys.modules[mod_name] = self.module
        return self

    def __exit__(self, *args):
        if self._saved_module:
            sys.modules[self.mod_name] = self._saved_module[0]
        else:
            del sys.modules[self.mod_name]
        self._saved_module = []


class _ModifiedArgv0(object):
    def __init__(self, value):
        self.value = value
        self._saved_value = self._sentinel = object()

    def __enter__(self):
        if self._saved_value is not self._sentinel:
            raise RuntimeError("Already preserving saved value")
        self._saved_value = sys.argv[0]
        sys.argv[0] = self.value

    def __exit__(self, *args):
        self.value = self._sentinel
        sys.argv[0] = self._saved_value


# TODO: Replace these helpers with importlib._bootstrap_external functions.
def _run_code(code, run_globals, init_globals=None, mod_name=None, mod_spec=None, pkg_name=None, script_name=None):
    """Helper to run code in nominated namespace"""
    if init_globals is not None:
        run_globals.update(init_globals)
    if mod_spec is None:
        loader = None
        fname = script_name
        cached = None
    else:
        loader = mod_spec.loader
        fname = mod_spec.origin
        cached = mod_spec.cached
        if pkg_name is None:
            pkg_name = mod_spec.parent
    run_globals.update(
        __name__=mod_name, __file__=fname, __cached__=cached, __doc__=None, __loader__=loader, __package__=pkg_name, __spec__=mod_spec
    )
    exec(code, run_globals)
    return run_globals


def _run_module_code(code, init_globals=None, mod_name=None, mod_spec=None, pkg_name=None, script_name=None):
    """Helper to run code in new namespace with sys modified"""
    fname = script_name if mod_spec is None else mod_spec.origin
    with _TempModule(mod_name) as temp_module, _ModifiedArgv0(fname):
        mod_globals = temp_module.module.__dict__
        _run_code(code, mod_globals, init_globals, mod_name, mod_spec, pkg_name, script_name)
    # Copy the globals of the temporary module, as they
    # may be cleared when the temporary module goes away
    return mod_globals.copy()


# Helper to get the full name, spec and code for a module
def _get_module_details(mod_name, error=ImportError):
    if mod_name.startswith("."):
        raise error("Relative module names not supported")
    pkg_name, _, _ = mod_name.rpartition(".")
    if pkg_name:
        # Try importing the parent to avoid catching initialization errors
        try:
            __import__(pkg_name)
        except ImportError as e:
            # If the parent or higher ancestor package is missing, let the
            # error be raised by find_spec() below and then be caught. But do
            # not allow other errors to be caught.
            if e.name is None or (e.name != pkg_name and not pkg_name.startswith(e.name + ".")):
                raise
        # Warn if the module has already been imported under its normal name
        existing = sys.modules.get(mod_name)
        if existing is not None and not hasattr(existing, "__path__"):
            from warnings import warn

            msg = (
                "{mod_name!r} found in sys.modules after import of "
                "package {pkg_name!r}, but prior to execution of "
                "{mod_name!r}; this may result in unpredictable "
                "behaviour".format(mod_name=mod_name, pkg_name=pkg_name)
            )
            warn(RuntimeWarning(msg))

    try:
        spec = importlib.util.find_spec(mod_name)
    except (ImportError, AttributeError, TypeError, ValueError) as ex:
        # This hack fixes an impedance mismatch between pkgutil and
        # importlib, where the latter raises other errors for cases where
        # pkgutil previously raised ImportError
        msg = "Error while finding module specification for {!r} ({}: {})"
        if mod_name.endswith(".py"):
            msg += f". Try using '{mod_name[:-3]}' instead of " f"'{mod_name}' as the module name."
        raise error(msg.format(mod_name, type(ex).__name__, ex)) from ex
    if spec is None:
        raise error("No module named %s" % mod_name)
    if spec.submodule_search_locations is not None:
        if mod_name == "__main__" or mod_name.endswith(".__main__"):
            raise error("Cannot use package as __main__ module")
        try:
            pkg_main_name = mod_name + ".__main__"
            return _get_module_details(pkg_main_name, error)
        except error as e:
            if mod_name not in sys.modules:
                raise  # No module loaded; being a package is irrelevant
            raise error(("%s; %r is a package and cannot " + "be directly executed") % (e, mod_name))
    loader = spec.loader
    if loader is None:
        raise error("%r is a namespace package and cannot be executed" % mod_name)
    try:
        code = loader.get_code(mod_name)
    except ImportError as e:
        raise error(format(e)) from e
    if code is None:
        raise error("No code object available for %s" % mod_name)
    return mod_name, spec, code


class _Error(Exception):
    """Error that _run_module_as_main() should report without a traceback"""


# XXX ncoghlan: Should this be documented and made public?
# (Current thoughts: don't repeat the mistake that lead to its
# creation when run_module() no longer met the needs of
# mainmodule.c, but couldn't be changed because it was public)
def _run_module_as_main(mod_name, alter_argv=True):
    """Runs the designated module in the __main__ namespace

    Note that the executed module will have full access to the
    __main__ namespace. If this is not desirable, the run_module()
    function should be used to run the module code in a fresh namespace.

    At the very least, these variables in __main__ will be overwritten:
        __name__
        __file__
        __cached__
        __loader__
        __package__
    """
    try:
        if alter_argv or mod_name != "__main__":  # i.e. -m switch
            mod_name, mod_spec, code = _get_module_details(mod_name, _Error)
        else:  # i.e. directory or zipfile execution
            mod_name, mod_spec, code = _get_main_module_details(_Error)
    except _Error as exc:
        msg = "%s: %s" % (sys.executable, exc)
        sys.exit(msg)
    main_globals = sys.modules["__main__"].__dict__
    if alter_argv:
        sys.argv[0] = mod_spec.origin
    return _run_code(code, main_globals, None, "__main__", mod_spec)


def run_module(mod_name, init_globals=None, run_name=None, alter_sys=False):
    """Execute a module's code without importing it

    Returns the resulting top level namespace dictionary
    """
    mod_name, mod_spec, code = _get_module_details(mod_name)
    if run_name is None:
        run_name = mod_name
    if alter_sys:
        return _run_module_code(code, init_globals, run_name, mod_spec)
    else:
        # Leave the sys module alone
        return _run_code(code, {}, init_globals, run_name, mod_spec)


def _get_main_module_details(error=ImportError):
    # Helper that gives a nicer error message when attempting to
    # execute a zipfile or directory by invoking __main__.py
    # Also moves the standard __main__ out of the way so that the
    # preexisting __loader__ entry doesn't cause issues
    main_name = "__main__"
    saved_main = sys.modules[main_name]
    del sys.modules[main_name]
    try:
        return _get_module_details(main_name)
    except ImportError as exc:
        if main_name in str(exc):
            raise error("can't find %r module in %r" % (main_name, sys.path[0])) from exc
        raise
    finally:
        sys.modules[main_name] = saved_main


try:
    io_open_code = io.open_code
except AttributeError:
    # Compatibility with Python 3.6/3.7
    import tokenize

    io_open_code = tokenize.open


def _get_code_from_file(run_name, fname):
    # Check for a compiled file first
    from pkgutil import read_code

    decoded_path = os.path.abspath(os.fsdecode(fname))
    with io_open_code(decoded_path) as f:
        code = read_code(f)
    if code is None:
        # That didn't work, so try it as normal source code
        with io_open_code(decoded_path) as f:
            code = compile(f.read(), fname, "exec")
    return code, fname


def run_path(path_name, init_globals=None, run_name=None):
    """Execute code located at the specified filesystem location

    Returns the resulting top level namespace dictionary

    The file path may refer directly to a Python script (i.e.
    one that could be directly executed with execfile) or else
    it may refer to a zipfile or directory containing a top
    level __main__.py script.
    """
    if run_name is None:
        run_name = "<run_path>"
    pkg_name = run_name.rpartition(".")[0]
    importer = pkgutil_get_importer(path_name)
    # Trying to avoid importing imp so as to not consume the deprecation warning.
    is_NullImporter = False
    if type(importer).__module__ == "imp":
        if type(importer).__name__ == "NullImporter":
            is_NullImporter = True
    if isinstance(importer, type(None)) or is_NullImporter:
        # Not a valid sys.path entry, so run the code directly
        # execfile() doesn't help as we want to allow compiled files
        code, fname = _get_code_from_file(run_name, path_name)
        return _run_module_code(code, init_globals, run_name, pkg_name=pkg_name, script_name=fname)
    else:
        # Finder is defined for path, so add it to
        # the start of sys.path
        sys.path.insert(0, path_name)
        try:
            # Here's where things are a little different from the run_module
            # case. There, we only had to replace the module in sys while the
            # code was running and doing so was somewhat optional. Here, we
            # have no choice and we have to remove it even while we read the
            # code. If we don't do this, a __loader__ attribute in the
            # existing __main__ module may prevent location of the new module.
            mod_name, mod_spec, code = _get_main_module_details()
            with _TempModule(run_name) as temp_module, _ModifiedArgv0(path_name):
                mod_globals = temp_module.module.__dict__
                return _run_code(code, mod_globals, init_globals, run_name, mod_spec, pkg_name).copy()
        finally:
            try:
                sys.path.remove(path_name)
            except ValueError:
                pass


if __name__ == "__main__":
    # Run the module specified as the next command line argument
    if len(sys.argv) < 2:
        print("No module specified for execution", file=sys.stderr)
    else:
        del sys.argv[0]  # Make the requested module sys.argv[0]
        _run_module_as_main(sys.argv[0])

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\formatters\terminal256.py ===
"""
    pygments.formatters.terminal256
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for 256-color terminal output with ANSI sequences.

    RGB-to-XTERM color conversion routines adapted from xterm256-conv
    tool (http://frexx.de/xterm-256-notes/data/xterm256-conv2.tar.bz2)
    by Wolfgang Frisch.

    Formatter version 1.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# TODO:
#  - Options to map style's bold/underline/italic/border attributes
#    to some ANSI attrbutes (something like 'italic=underline')
#  - An option to output "style RGB to xterm RGB/index" conversion table
#  - An option to indicate that we are running in "reverse background"
#    xterm. This means that default colors are white-on-black, not
#    black-on-while, so colors like "white background" need to be converted
#    to "white background, black foreground", etc...

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.console import codes
from pip._vendor.pygments.style import ansicolors


__all__ = ['Terminal256Formatter', 'TerminalTrueColorFormatter']


class EscapeSequence:
    def __init__(self, fg=None, bg=None, bold=False, underline=False, italic=False):
        self.fg = fg
        self.bg = bg
        self.bold = bold
        self.underline = underline
        self.italic = italic

    def escape(self, attrs):
        if len(attrs):
            return "\x1b[" + ";".join(attrs) + "m"
        return ""

    def color_string(self):
        attrs = []
        if self.fg is not None:
            if self.fg in ansicolors:
                esc = codes[self.fg.replace('ansi','')]
                if ';01m' in esc:
                    self.bold = True
                # extract fg color code.
                attrs.append(esc[2:4])
            else:
                attrs.extend(("38", "5", "%i" % self.fg))
        if self.bg is not None:
            if self.bg in ansicolors:
                esc = codes[self.bg.replace('ansi','')]
                # extract fg color code, add 10 for bg.
                attrs.append(str(int(esc[2:4])+10))
            else:
                attrs.extend(("48", "5", "%i" % self.bg))
        if self.bold:
            attrs.append("01")
        if self.underline:
            attrs.append("04")
        if self.italic:
            attrs.append("03")
        return self.escape(attrs)

    def true_color_string(self):
        attrs = []
        if self.fg:
            attrs.extend(("38", "2", str(self.fg[0]), str(self.fg[1]), str(self.fg[2])))
        if self.bg:
            attrs.extend(("48", "2", str(self.bg[0]), str(self.bg[1]), str(self.bg[2])))
        if self.bold:
            attrs.append("01")
        if self.underline:
            attrs.append("04")
        if self.italic:
            attrs.append("03")
        return self.escape(attrs)

    def reset_string(self):
        attrs = []
        if self.fg is not None:
            attrs.append("39")
        if self.bg is not None:
            attrs.append("49")
        if self.bold or self.underline or self.italic:
            attrs.append("00")
        return self.escape(attrs)


class Terminal256Formatter(Formatter):
    """
    Format tokens with ANSI color sequences, for output in a 256-color
    terminal or console.  Like in `TerminalFormatter` color sequences
    are terminated at newlines, so that paging the output works correctly.

    The formatter takes colors from a style defined by the `style` option
    and converts them to nearest ANSI 256-color escape sequences. Bold and
    underline attributes from the style are preserved (and displayed).

    .. versionadded:: 0.9

    .. versionchanged:: 2.2
       If the used style defines foreground colors in the form ``#ansi*``, then
       `Terminal256Formatter` will map these to non extended foreground color.
       See :ref:`AnsiTerminalStyle` for more information.

    .. versionchanged:: 2.4
       The ANSI color names have been updated with names that are easier to
       understand and align with colornames of other projects and terminals.
       See :ref:`this table <new-ansi-color-names>` for more information.


    Options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `linenos`
        Set to ``True`` to have line numbers on the terminal output as well
        (default: ``False`` = no line numbers).
    """
    name = 'Terminal256'
    aliases = ['terminal256', 'console256', '256']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)

        self.xterm_colors = []
        self.best_match = {}
        self.style_string = {}

        self.usebold = 'nobold' not in options
        self.useunderline = 'nounderline' not in options
        self.useitalic = 'noitalic' not in options

        self._build_color_table()  # build an RGB-to-256 color conversion table
        self._setup_styles()  # convert selected style's colors to term. colors

        self.linenos = options.get('linenos', False)
        self._lineno = 0

    def _build_color_table(self):
        # colors 0..15: 16 basic colors

        self.xterm_colors.append((0x00, 0x00, 0x00))  # 0
        self.xterm_colors.append((0xcd, 0x00, 0x00))  # 1
        self.xterm_colors.append((0x00, 0xcd, 0x00))  # 2
        self.xterm_colors.append((0xcd, 0xcd, 0x00))  # 3
        self.xterm_colors.append((0x00, 0x00, 0xee))  # 4
        self.xterm_colors.append((0xcd, 0x00, 0xcd))  # 5
        self.xterm_colors.append((0x00, 0xcd, 0xcd))  # 6
        self.xterm_colors.append((0xe5, 0xe5, 0xe5))  # 7
        self.xterm_colors.append((0x7f, 0x7f, 0x7f))  # 8
        self.xterm_colors.append((0xff, 0x00, 0x00))  # 9
        self.xterm_colors.append((0x00, 0xff, 0x00))  # 10
        self.xterm_colors.append((0xff, 0xff, 0x00))  # 11
        self.xterm_colors.append((0x5c, 0x5c, 0xff))  # 12
        self.xterm_colors.append((0xff, 0x00, 0xff))  # 13
        self.xterm_colors.append((0x00, 0xff, 0xff))  # 14
        self.xterm_colors.append((0xff, 0xff, 0xff))  # 15

        # colors 16..232: the 6x6x6 color cube

        valuerange = (0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff)

        for i in range(217):
            r = valuerange[(i // 36) % 6]
            g = valuerange[(i // 6) % 6]
            b = valuerange[i % 6]
            self.xterm_colors.append((r, g, b))

        # colors 233..253: grayscale

        for i in range(1, 22):
            v = 8 + i * 10
            self.xterm_colors.append((v, v, v))

    def _closest_color(self, r, g, b):
        distance = 257*257*3  # "infinity" (>distance from #000000 to #ffffff)
        match = 0

        for i in range(0, 254):
            values = self.xterm_colors[i]

            rd = r - values[0]
            gd = g - values[1]
            bd = b - values[2]
            d = rd*rd + gd*gd + bd*bd

            if d < distance:
                match = i
                distance = d
        return match

    def _color_index(self, color):
        index = self.best_match.get(color, None)
        if color in ansicolors:
            # strip the `ansi/#ansi` part and look up code
            index = color
            self.best_match[color] = index
        if index is None:
            try:
                rgb = int(str(color), 16)
            except ValueError:
                rgb = 0

            r = (rgb >> 16) & 0xff
            g = (rgb >> 8) & 0xff
            b = rgb & 0xff
            index = self._closest_color(r, g, b)
            self.best_match[color] = index
        return index

    def _setup_styles(self):
        for ttype, ndef in self.style:
            escape = EscapeSequence()
            # get foreground from ansicolor if set
            if ndef['ansicolor']:
                escape.fg = self._color_index(ndef['ansicolor'])
            elif ndef['color']:
                escape.fg = self._color_index(ndef['color'])
            if ndef['bgansicolor']:
                escape.bg = self._color_index(ndef['bgansicolor'])
            elif ndef['bgcolor']:
                escape.bg = self._color_index(ndef['bgcolor'])
            if self.usebold and ndef['bold']:
                escape.bold = True
            if self.useunderline and ndef['underline']:
                escape.underline = True
            if self.useitalic and ndef['italic']:
                escape.italic = True
            self.style_string[str(ttype)] = (escape.color_string(),
                                             escape.reset_string())

    def _write_lineno(self, outfile):
        self._lineno += 1
        outfile.write("%s%04d: " % (self._lineno != 1 and '\n' or '', self._lineno))

    def format(self, tokensource, outfile):
        return Formatter.format(self, tokensource, outfile)

    def format_unencoded(self, tokensource, outfile):
        if self.linenos:
            self._write_lineno(outfile)

        for ttype, value in tokensource:
            not_found = True
            while ttype and not_found:
                try:
                    # outfile.write( "<" + str(ttype) + ">" )
                    on, off = self.style_string[str(ttype)]

                    # Like TerminalFormatter, add "reset colors" escape sequence
                    # on newline.
                    spl = value.split('\n')
                    for line in spl[:-1]:
                        if line:
                            outfile.write(on + line + off)
                        if self.linenos:
                            self._write_lineno(outfile)
                        else:
                            outfile.write('\n')

                    if spl[-1]:
                        outfile.write(on + spl[-1] + off)

                    not_found = False
                    # outfile.write( '#' + str(ttype) + '#' )

                except KeyError:
                    # ottype = ttype
                    ttype = ttype.parent
                    # outfile.write( '!' + str(ottype) + '->' + str(ttype) + '!' )

            if not_found:
                outfile.write(value)

        if self.linenos:
            outfile.write("\n")



class TerminalTrueColorFormatter(Terminal256Formatter):
    r"""
    Format tokens with ANSI color sequences, for output in a true-color
    terminal or console.  Like in `TerminalFormatter` color sequences
    are terminated at newlines, so that paging the output works correctly.

    .. versionadded:: 2.1

    Options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).
    """
    name = 'TerminalTrueColor'
    aliases = ['terminal16m', 'console16m', '16m']
    filenames = []

    def _build_color_table(self):
        pass

    def _color_tuple(self, color):
        try:
            rgb = int(str(color), 16)
        except ValueError:
            return None
        r = (rgb >> 16) & 0xff
        g = (rgb >> 8) & 0xff
        b = rgb & 0xff
        return (r, g, b)

    def _setup_styles(self):
        for ttype, ndef in self.style:
            escape = EscapeSequence()
            if ndef['color']:
                escape.fg = self._color_tuple(ndef['color'])
            if ndef['bgcolor']:
                escape.bg = self._color_tuple(ndef['bgcolor'])
            if self.usebold and ndef['bold']:
                escape.bold = True
            if self.useunderline and ndef['underline']:
                escape.underline = True
            if self.useitalic and ndef['italic']:
                escape.italic = True
            self.style_string[str(ttype)] = (escape.true_color_string(),
                                             escape.reset_string())

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\_snapshot_download.py ===
import os
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Type, Union

import requests
from tqdm.auto import tqdm as base_tqdm
from tqdm.contrib.concurrent import thread_map

from . import constants
from .errors import (
    GatedRepoError,
    HfHubHTTPError,
    LocalEntryNotFoundError,
    RepositoryNotFoundError,
    RevisionNotFoundError,
)
from .file_download import REGEX_COMMIT_HASH, hf_hub_download, repo_folder_name
from .hf_api import DatasetInfo, HfApi, ModelInfo, RepoFile, SpaceInfo
from .utils import OfflineModeIsEnabled, filter_repo_objects, logging, validate_hf_hub_args
from .utils import tqdm as hf_tqdm


logger = logging.get_logger(__name__)

VERY_LARGE_REPO_THRESHOLD = 50000  # After this limit, we don't consider `repo_info.siblings` to be reliable enough


@validate_hf_hub_args
def snapshot_download(
    repo_id: str,
    *,
    repo_type: Optional[str] = None,
    revision: Optional[str] = None,
    cache_dir: Union[str, Path, None] = None,
    local_dir: Union[str, Path, None] = None,
    library_name: Optional[str] = None,
    library_version: Optional[str] = None,
    user_agent: Optional[Union[Dict, str]] = None,
    proxies: Optional[Dict] = None,
    etag_timeout: float = constants.DEFAULT_ETAG_TIMEOUT,
    force_download: bool = False,
    token: Optional[Union[bool, str]] = None,
    local_files_only: bool = False,
    allow_patterns: Optional[Union[List[str], str]] = None,
    ignore_patterns: Optional[Union[List[str], str]] = None,
    max_workers: int = 8,
    tqdm_class: Optional[Type[base_tqdm]] = None,
    headers: Optional[Dict[str, str]] = None,
    endpoint: Optional[str] = None,
    # Deprecated args
    local_dir_use_symlinks: Union[bool, Literal["auto"]] = "auto",
    resume_download: Optional[bool] = None,
) -> str:
    """Download repo files.

    Download a whole snapshot of a repo's files at the specified revision. This is useful when you want all files from
    a repo, because you don't know which ones you will need a priori. All files are nested inside a folder in order
    to keep their actual filename relative to that folder. You can also filter which files to download using
    `allow_patterns` and `ignore_patterns`.

    If `local_dir` is provided, the file structure from the repo will be replicated in this location. When using this
    option, the `cache_dir` will not be used and a `.cache/huggingface/` folder will be created at the root of `local_dir`
    to store some metadata related to the downloaded files. While this mechanism is not as robust as the main
    cache-system, it's optimized for regularly pulling the latest version of a repository.

    An alternative would be to clone the repo but this requires git and git-lfs to be installed and properly
    configured. It is also not possible to filter which files to download when cloning a repository using git.

    Args:
        repo_id (`str`):
            A user or an organization name and a repo name separated by a `/`.
        repo_type (`str`, *optional*):
            Set to `"dataset"` or `"space"` if downloading from a dataset or space,
            `None` or `"model"` if downloading from a model. Default is `None`.
        revision (`str`, *optional*):
            An optional Git revision id which can be a branch name, a tag, or a
            commit hash.
        cache_dir (`str`, `Path`, *optional*):
            Path to the folder where cached files are stored.
        local_dir (`str` or `Path`, *optional*):
            If provided, the downloaded files will be placed under this directory.
        library_name (`str`, *optional*):
            The name of the library to which the object corresponds.
        library_version (`str`, *optional*):
            The version of the library.
        user_agent (`str`, `dict`, *optional*):
            The user-agent info in the form of a dictionary or a string.
        proxies (`dict`, *optional*):
            Dictionary mapping protocol to the URL of the proxy passed to
            `requests.request`.
        etag_timeout (`float`, *optional*, defaults to `10`):
            When fetching ETag, how many seconds to wait for the server to send
            data before giving up which is passed to `requests.request`.
        force_download (`bool`, *optional*, defaults to `False`):
            Whether the file should be downloaded even if it already exists in the local cache.
        token (`str`, `bool`, *optional*):
            A token to be used for the download.
                - If `True`, the token is read from the HuggingFace config
                  folder.
                - If a string, it's used as the authentication token.
        headers (`dict`, *optional*):
            Additional headers to include in the request. Those headers take precedence over the others.
        local_files_only (`bool`, *optional*, defaults to `False`):
            If `True`, avoid downloading the file and return the path to the
            local cached file if it exists.
        allow_patterns (`List[str]` or `str`, *optional*):
            If provided, only files matching at least one pattern are downloaded.
        ignore_patterns (`List[str]` or `str`, *optional*):
            If provided, files matching any of the patterns are not downloaded.
        max_workers (`int`, *optional*):
            Number of concurrent threads to download files (1 thread = 1 file download).
            Defaults to 8.
        tqdm_class (`tqdm`, *optional*):
            If provided, overwrites the default behavior for the progress bar. Passed
            argument must inherit from `tqdm.auto.tqdm` or at least mimic its behavior.
            Note that the `tqdm_class` is not passed to each individual download.
            Defaults to the custom HF progress bar that can be disabled by setting
            `HF_HUB_DISABLE_PROGRESS_BARS` environment variable.

    Returns:
        `str`: folder path of the repo snapshot.

    Raises:
        [`~utils.RepositoryNotFoundError`]
            If the repository to download from cannot be found. This may be because it doesn't exist,
            or because it is set to `private` and you do not have access.
        [`~utils.RevisionNotFoundError`]
            If the revision to download from cannot be found.
        [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
            If `token=True` and the token cannot be found.
        [`OSError`](https://docs.python.org/3/library/exceptions.html#OSError) if
            ETag cannot be determined.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            if some parameter value is invalid.
    """
    if cache_dir is None:
        cache_dir = constants.HF_HUB_CACHE
    if revision is None:
        revision = constants.DEFAULT_REVISION
    if isinstance(cache_dir, Path):
        cache_dir = str(cache_dir)

    if repo_type is None:
        repo_type = "model"
    if repo_type not in constants.REPO_TYPES:
        raise ValueError(f"Invalid repo type: {repo_type}. Accepted repo types are: {str(constants.REPO_TYPES)}")

    storage_folder = os.path.join(cache_dir, repo_folder_name(repo_id=repo_id, repo_type=repo_type))

    api = HfApi(
        library_name=library_name,
        library_version=library_version,
        user_agent=user_agent,
        endpoint=endpoint,
        headers=headers,
        token=token,
    )

    repo_info: Union[ModelInfo, DatasetInfo, SpaceInfo, None] = None
    api_call_error: Optional[Exception] = None
    if not local_files_only:
        # try/except logic to handle different errors => taken from `hf_hub_download`
        try:
            # if we have internet connection we want to list files to download
            repo_info = api.repo_info(repo_id=repo_id, repo_type=repo_type, revision=revision)
        except (requests.exceptions.SSLError, requests.exceptions.ProxyError):
            # Actually raise for those subclasses of ConnectionError
            raise
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            OfflineModeIsEnabled,
        ) as error:
            # Internet connection is down
            # => will try to use local files only
            api_call_error = error
            pass
        except RevisionNotFoundError:
            # The repo was found but the revision doesn't exist on the Hub (never existed or got deleted)
            raise
        except requests.HTTPError as error:
            # Multiple reasons for an http error:
            # - Repository is private and invalid/missing token sent
            # - Repository is gated and invalid/missing token sent
            # - Hub is down (error 500 or 504)
            # => let's switch to 'local_files_only=True' to check if the files are already cached.
            #    (if it's not the case, the error will be re-raised)
            api_call_error = error
            pass

    # At this stage, if `repo_info` is None it means either:
    # - internet connection is down
    # - internet connection is deactivated (local_files_only=True or HF_HUB_OFFLINE=True)
    # - repo is private/gated and invalid/missing token sent
    # - Hub is down
    # => let's look if we can find the appropriate folder in the cache:
    #    - if the specified revision is a commit hash, look inside "snapshots".
    #    - f the specified revision is a branch or tag, look inside "refs".
    # => if local_dir is not None, we will return the path to the local folder if it exists.
    if repo_info is None:
        # Try to get which commit hash corresponds to the specified revision
        commit_hash = None
        if REGEX_COMMIT_HASH.match(revision):
            commit_hash = revision
        else:
            ref_path = os.path.join(storage_folder, "refs", revision)
            if os.path.exists(ref_path):
                # retrieve commit_hash from refs file
                with open(ref_path) as f:
                    commit_hash = f.read()

        # Try to locate snapshot folder for this commit hash
        if commit_hash is not None and local_dir is None:
            snapshot_folder = os.path.join(storage_folder, "snapshots", commit_hash)
            if os.path.exists(snapshot_folder):
                # Snapshot folder exists => let's return it
                # (but we can't check if all the files are actually there)
                return snapshot_folder

        # If local_dir is not None, return it if it exists and is not empty
        if local_dir is not None:
            local_dir = Path(local_dir)
            if local_dir.is_dir() and any(local_dir.iterdir()):
                logger.warning(
                    f"Returning existing local_dir `{local_dir}` as remote repo cannot be accessed in `snapshot_download` ({api_call_error})."
                )
                return str(local_dir.resolve())
        # If we couldn't find the appropriate folder on disk, raise an error.
        if local_files_only:
            raise LocalEntryNotFoundError(
                "Cannot find an appropriate cached snapshot folder for the specified revision on the local disk and "
                "outgoing traffic has been disabled. To enable repo look-ups and downloads online, pass "
                "'local_files_only=False' as input."
            )
        elif isinstance(api_call_error, OfflineModeIsEnabled):
            raise LocalEntryNotFoundError(
                "Cannot find an appropriate cached snapshot folder for the specified revision on the local disk and "
                "outgoing traffic has been disabled. To enable repo look-ups and downloads online, set "
                "'HF_HUB_OFFLINE=0' as environment variable."
            ) from api_call_error
        elif isinstance(api_call_error, (RepositoryNotFoundError, GatedRepoError)) or (
            isinstance(api_call_error, HfHubHTTPError) and api_call_error.response.status_code == 401
        ):
            # Repo not found, gated, or specific authentication error => let's raise the actual error
            raise api_call_error
        else:
            # Otherwise: most likely a connection issue or Hub downtime => let's warn the user
            raise LocalEntryNotFoundError(
                "An error happened while trying to locate the files on the Hub and we cannot find the appropriate"
                " snapshot folder for the specified revision on the local disk. Please check your internet connection"
                " and try again."
            ) from api_call_error

    # At this stage, internet connection is up and running
    # => let's download the files!
    assert repo_info.sha is not None, "Repo info returned from server must have a revision sha."
    assert repo_info.siblings is not None, "Repo info returned from server must have a siblings list."

    # Corner case: on very large repos, the siblings list in `repo_info` might not contain all files.
    # In that case, we need to use the `list_repo_tree` method to prevent caching issues.
    repo_files: Iterable[str] = [f.rfilename for f in repo_info.siblings]
    has_many_files = len(repo_info.siblings) > VERY_LARGE_REPO_THRESHOLD
    if has_many_files:
        logger.info("The repo has more than 50,000 files. Using `list_repo_tree` to ensure all files are listed.")
        repo_files = (
            f.rfilename
            for f in api.list_repo_tree(repo_id=repo_id, recursive=True, revision=revision, repo_type=repo_type)
            if isinstance(f, RepoFile)
        )

    filtered_repo_files: Iterable[str] = filter_repo_objects(
        items=repo_files,
        allow_patterns=allow_patterns,
        ignore_patterns=ignore_patterns,
    )

    if not has_many_files:
        filtered_repo_files = list(filtered_repo_files)
        tqdm_desc = f"Fetching {len(filtered_repo_files)} files"
    else:
        tqdm_desc = "Fetching ... files"

    commit_hash = repo_info.sha
    snapshot_folder = os.path.join(storage_folder, "snapshots", commit_hash)
    # if passed revision is not identical to commit_hash
    # then revision has to be a branch name or tag name.
    # In that case store a ref.
    if revision != commit_hash:
        ref_path = os.path.join(storage_folder, "refs", revision)
        try:
            os.makedirs(os.path.dirname(ref_path), exist_ok=True)
            with open(ref_path, "w") as f:
                f.write(commit_hash)
        except OSError as e:
            logger.warning(f"Ignored error while writing commit hash to {ref_path}: {e}.")

    # we pass the commit_hash to hf_hub_download
    # so no network call happens if we already
    # have the file locally.
    def _inner_hf_hub_download(repo_file: str):
        return hf_hub_download(
            repo_id,
            filename=repo_file,
            repo_type=repo_type,
            revision=commit_hash,
            endpoint=endpoint,
            cache_dir=cache_dir,
            local_dir=local_dir,
            local_dir_use_symlinks=local_dir_use_symlinks,
            library_name=library_name,
            library_version=library_version,
            user_agent=user_agent,
            proxies=proxies,
            etag_timeout=etag_timeout,
            resume_download=resume_download,
            force_download=force_download,
            token=token,
            headers=headers,
        )

    if constants.HF_HUB_ENABLE_HF_TRANSFER:
        # when using hf_transfer we don't want extra parallelism
        # from the one hf_transfer provides
        for file in filtered_repo_files:
            _inner_hf_hub_download(file)
    else:
        thread_map(
            _inner_hf_hub_download,
            filtered_repo_files,
            desc=tqdm_desc,
            max_workers=max_workers,
            # User can use its own tqdm class or the default one from `huggingface_hub.utils`
            tqdm_class=tqdm_class or hf_tqdm,
        )

    if local_dir is not None:
        return str(os.path.realpath(local_dir))
    return snapshot_folder

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_filtering.py ===
import fnmatch
import glob
import os.path
import sys

from _pydev_bundle import pydev_log
import pydevd_file_utils
import json
from collections import namedtuple
from _pydev_bundle._pydev_saved_modules import threading
from pydevd_file_utils import normcase
from _pydevd_bundle.pydevd_constants import USER_CODE_BASENAMES_STARTING_WITH, LIBRARY_CODE_BASENAMES_STARTING_WITH, IS_PYPY, IS_WINDOWS
from _pydevd_bundle import pydevd_constants
from _pydevd_bundle.pydevd_constants import is_true_in_env

ExcludeFilter = namedtuple("ExcludeFilter", "name, exclude, is_path")


def _convert_to_str_and_clear_empty(roots):
    new_roots = []
    for root in roots:
        assert isinstance(root, str), "%s not str (found: %s)" % (root, type(root))
        if root:
            new_roots.append(root)
    return new_roots


def _check_matches(patterns, paths):
    if not patterns and not paths:
        # Matched to the end.
        return True

    if (not patterns and paths) or (patterns and not paths):
        return False

    pattern = normcase(patterns[0])
    path = normcase(paths[0])

    if not glob.has_magic(pattern):
        if pattern != path:
            return False

    elif pattern == "**":
        if len(patterns) == 1:
            return True  # if ** is the last one it matches anything to the right.

        for i in range(len(paths)):
            # Recursively check the remaining patterns as the
            # current pattern could match any number of paths.
            if _check_matches(patterns[1:], paths[i:]):
                return True

    elif not fnmatch.fnmatch(path, pattern):
        # Current part doesn't match.
        return False

    return _check_matches(patterns[1:], paths[1:])


def glob_matches_path(path, pattern, sep=os.sep, altsep=os.altsep):
    if altsep:
        pattern = pattern.replace(altsep, sep)
        path = path.replace(altsep, sep)

    drive = ""
    if len(path) > 1 and path[1] == ":":
        drive, path = path[0], path[2:]

    if drive and len(pattern) > 1:
        if pattern[1] == ":":
            if drive.lower() != pattern[0].lower():
                return False
            pattern = pattern[2:]

    patterns = pattern.split(sep)
    paths = path.split(sep)
    if paths:
        if paths[0] == "":
            paths = paths[1:]
    if patterns:
        if patterns[0] == "":
            patterns = patterns[1:]

    return _check_matches(patterns, paths)


class FilesFiltering(object):
    """
    Note: calls at FilesFiltering are uncached.

    The actual API used should be through PyDB.
    """

    def __init__(self):
        self._exclude_filters = []
        self._project_roots = []
        self._library_roots = []

        # Filter out libraries?
        self._use_libraries_filter = False
        self.require_module = False  # True if some exclude filter filters by the module.

        self.set_use_libraries_filter(is_true_in_env("PYDEVD_FILTER_LIBRARIES"))

        project_roots = os.getenv("IDE_PROJECT_ROOTS", None)
        if project_roots is not None:
            project_roots = project_roots.split(os.pathsep)
        else:
            project_roots = []
        self.set_project_roots(project_roots)

        library_roots = os.getenv("LIBRARY_ROOTS", None)
        if library_roots is not None:
            library_roots = library_roots.split(os.pathsep)
        else:
            library_roots = self._get_default_library_roots()
        self.set_library_roots(library_roots)

        # Stepping filters.
        pydevd_filters = os.getenv("PYDEVD_FILTERS", "")
        # To filter out it's something as: {'**/not_my_code/**': True}
        if pydevd_filters:
            pydev_log.debug("PYDEVD_FILTERS %s", (pydevd_filters,))
            if pydevd_filters.startswith("{"):
                # dict(glob_pattern (str) -> exclude(True or False))
                exclude_filters = []
                for key, val in json.loads(pydevd_filters).items():
                    exclude_filters.append(ExcludeFilter(key, val, True))
                self._exclude_filters = exclude_filters
            else:
                # A ';' separated list of strings with globs for the
                # list of excludes.
                filters = pydevd_filters.split(";")
                new_filters = []
                for new_filter in filters:
                    if new_filter.strip():
                        new_filters.append(ExcludeFilter(new_filter.strip(), True, True))
                self._exclude_filters = new_filters

    @classmethod
    def _get_default_library_roots(cls):
        pydev_log.debug("Collecting default library roots.")
        # Provide sensible defaults if not in env vars.
        import site

        roots = []

        try:
            import sysconfig  # Python 2.7 onwards only.
        except ImportError:
            pass
        else:
            for path_name in set(("stdlib", "platstdlib", "purelib", "platlib")) & set(sysconfig.get_path_names()):
                roots.append(sysconfig.get_path(path_name))

        # Make sure we always get at least the standard library location (based on the `os` and
        # `threading` modules -- it's a bit weird that it may be different on the ci, but it happens).
        roots.append(os.path.dirname(os.__file__))
        roots.append(os.path.dirname(threading.__file__))
        if IS_PYPY:
            # On PyPy 3.6 (7.3.1) it wrongly says that sysconfig.get_path('stdlib') is
            # <install>/lib-pypy when the installed version is <install>/lib_pypy.
            try:
                import _pypy_wait
            except ImportError:
                pydev_log.debug("Unable to import _pypy_wait on PyPy when collecting default library roots.")
            else:
                pypy_lib_dir = os.path.dirname(_pypy_wait.__file__)
                pydev_log.debug("Adding %s to default library roots.", pypy_lib_dir)
                roots.append(pypy_lib_dir)

        if hasattr(site, "getusersitepackages"):
            site_paths = site.getusersitepackages()
            if isinstance(site_paths, (list, tuple)):
                for site_path in site_paths:
                    roots.append(site_path)
            else:
                roots.append(site_paths)

        if hasattr(site, "getsitepackages"):
            site_paths = site.getsitepackages()
            if isinstance(site_paths, (list, tuple)):
                for site_path in site_paths:
                    roots.append(site_path)
            else:
                roots.append(site_paths)

        for path in sys.path:
            if os.path.exists(path) and os.path.basename(path) in ("site-packages", "pip-global"):
                roots.append(path)

        # On WASM some of the roots may not exist, filter those out.
        roots = [path for path in roots if path is not None]
        roots.extend([os.path.realpath(path) for path in roots])

        return sorted(set(roots))

    def _fix_roots(self, roots):
        roots = _convert_to_str_and_clear_empty(roots)
        new_roots = []
        for root in roots:
            path = self._absolute_normalized_path(root)
            if pydevd_constants.IS_WINDOWS:
                new_roots.append(path + "\\")
            else:
                new_roots.append(path + "/")
        return new_roots

    def _absolute_normalized_path(self, filename):
        """
        Provides a version of the filename that's absolute and normalized.
        """
        return normcase(pydevd_file_utils.absolute_path(filename))

    def set_project_roots(self, project_roots):
        self._project_roots = self._fix_roots(project_roots)
        pydev_log.debug("IDE_PROJECT_ROOTS %s\n" % project_roots)

    def _get_project_roots(self):
        return self._project_roots

    def set_library_roots(self, roots):
        self._library_roots = self._fix_roots(roots)
        pydev_log.debug("LIBRARY_ROOTS %s\n" % roots)

    def _get_library_roots(self):
        return self._library_roots

    def in_project_roots(self, received_filename):
        """
        Note: don't call directly. Use PyDb.in_project_scope (there's no caching here and it doesn't
        handle all possibilities for knowing whether a project is actually in the scope, it
        just handles the heuristics based on the absolute_normalized_filename without the actual frame).
        """
        DEBUG = False

        if received_filename.startswith(USER_CODE_BASENAMES_STARTING_WITH):
            if DEBUG:
                pydev_log.debug(
                    "In in_project_roots - user basenames - starts with %s (%s)", received_filename, USER_CODE_BASENAMES_STARTING_WITH
                )
            return True

        if received_filename.startswith(LIBRARY_CODE_BASENAMES_STARTING_WITH):
            if DEBUG:
                pydev_log.debug(
                    "Not in in_project_roots - library basenames - starts with %s (%s)",
                    received_filename,
                    LIBRARY_CODE_BASENAMES_STARTING_WITH,
                )
            return False

        project_roots = self._get_project_roots()  # roots are absolute/normalized.

        absolute_normalized_filename = self._absolute_normalized_path(received_filename)
        absolute_normalized_filename_as_dir = absolute_normalized_filename + ("\\" if IS_WINDOWS else "/")

        found_in_project = []
        for root in project_roots:
            if root and (absolute_normalized_filename.startswith(root) or root == absolute_normalized_filename_as_dir):
                if DEBUG:
                    pydev_log.debug("In project: %s (%s)", absolute_normalized_filename, root)
                found_in_project.append(root)

        found_in_library = []
        library_roots = self._get_library_roots()
        for root in library_roots:
            if root and (absolute_normalized_filename.startswith(root) or root == absolute_normalized_filename_as_dir):
                found_in_library.append(root)
                if DEBUG:
                    pydev_log.debug("In library: %s (%s)", absolute_normalized_filename, root)
            else:
                if DEBUG:
                    pydev_log.debug("Not in library: %s (%s)", absolute_normalized_filename, root)

        if not project_roots:
            # If we have no project roots configured, consider it being in the project
            # roots if it's not found in site-packages (because we have defaults for those
            # and not the other way around).
            in_project = not found_in_library
            if DEBUG:
                pydev_log.debug("Final in project (no project roots): %s (%s)", absolute_normalized_filename, in_project)

        else:
            in_project = False
            if found_in_project:
                if not found_in_library:
                    if DEBUG:
                        pydev_log.debug("Final in project (in_project and not found_in_library): %s (True)", absolute_normalized_filename)
                    in_project = True
                else:
                    # Found in both, let's see which one has the bigger path matched.
                    if max(len(x) for x in found_in_project) > max(len(x) for x in found_in_library):
                        in_project = True
                    if DEBUG:
                        pydev_log.debug("Final in project (found in both): %s (%s)", absolute_normalized_filename, in_project)

        return in_project

    def use_libraries_filter(self):
        """
        Should we debug only what's inside project folders?
        """
        return self._use_libraries_filter

    def set_use_libraries_filter(self, use):
        pydev_log.debug("pydevd: Use libraries filter: %s\n" % use)
        self._use_libraries_filter = use

    def use_exclude_filters(self):
        # Enabled if we have any filters registered.
        return len(self._exclude_filters) > 0

    def exclude_by_filter(self, absolute_filename, module_name):
        """
        :return: True if it should be excluded, False if it should be included and None
            if no rule matched the given file.
        """
        for exclude_filter in self._exclude_filters:  # : :type exclude_filter: ExcludeFilter
            if exclude_filter.is_path:
                if glob_matches_path(absolute_filename, exclude_filter.name):
                    return exclude_filter.exclude
            else:
                # Module filter.
                if exclude_filter.name == module_name or module_name.startswith(exclude_filter.name + "."):
                    return exclude_filter.exclude
        return None

    def set_exclude_filters(self, exclude_filters):
        """
        :param list(ExcludeFilter) exclude_filters:
        """
        self._exclude_filters = exclude_filters
        self.require_module = False
        for exclude_filter in exclude_filters:
            if not exclude_filter.is_path:
                self.require_module = True
                break

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\text_service\transports\grpc_asyncio.py ===
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
from typing import Awaitable, Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, grpc_helpers_async
from google.api_core import retry_async as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta2.types import text_service

from .base import DEFAULT_CLIENT_INFO, TextServiceTransport
from .grpc import TextServiceGrpcTransport


class TextServiceGrpcAsyncIOTransport(TextServiceTransport):
    """gRPC AsyncIO backend transport for TextService.

    API for using Generative Language Models (GLMs) trained to
    generate text.
    Also known as Large Language Models (LLM)s, these generate text
    given an input prompt from the user.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _grpc_channel: aio.Channel
    _stubs: Dict[str, Callable] = {}

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> aio.Channel:
        """Create and return a gRPC AsyncIO channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            aio.Channel: A gRPC AsyncIO channel object.
        """

        return grpc_helpers_async.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[aio.Channel, Callable[..., aio.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
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
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            channel (Optional[Union[aio.Channel, Callable[..., aio.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, aio.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None
        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @property
    def grpc_channel(self) -> aio.Channel:
        """Create the channel designed to connect to this service.

        This property caches on the instance; repeated calls return
        the same channel.
        """
        # Return the channel from cache.
        return self._grpc_channel

    @property
    def generate_text(
        self,
    ) -> Callable[
        [text_service.GenerateTextRequest], Awaitable[text_service.GenerateTextResponse]
    ]:
        r"""Return a callable for the generate text method over gRPC.

        Generates a response from the model given an input
        message.

        Returns:
            Callable[[~.GenerateTextRequest],
                    Awaitable[~.GenerateTextResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_text" not in self._stubs:
            self._stubs["generate_text"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta2.TextService/GenerateText",
                request_serializer=text_service.GenerateTextRequest.serialize,
                response_deserializer=text_service.GenerateTextResponse.deserialize,
            )
        return self._stubs["generate_text"]

    @property
    def embed_text(
        self,
    ) -> Callable[
        [text_service.EmbedTextRequest], Awaitable[text_service.EmbedTextResponse]
    ]:
        r"""Return a callable for the embed text method over gRPC.

        Generates an embedding from the model given an input
        message.

        Returns:
            Callable[[~.EmbedTextRequest],
                    Awaitable[~.EmbedTextResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "embed_text" not in self._stubs:
            self._stubs["embed_text"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta2.TextService/EmbedText",
                request_serializer=text_service.EmbedTextRequest.serialize,
                response_deserializer=text_service.EmbedTextResponse.deserialize,
            )
        return self._stubs["embed_text"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.generate_text: gapic_v1.method_async.wrap_method(
                self.generate_text,
                default_retry=retries.AsyncRetry(
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
            self.embed_text: gapic_v1.method_async.wrap_method(
                self.embed_text,
                default_retry=retries.AsyncRetry(
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
        return self.grpc_channel.close()


__all__ = ("TextServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\history.py ===
"""Implementation of magic functions related to History.
"""
#-----------------------------------------------------------------------------
#  Copyright (c) 2012, IPython Development Team.
#
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
import os
import sys
from io import open as io_open
import fnmatch

# Our own packages
from IPython.core.error import StdinNotImplementedError
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.core.magic_arguments import (argument, magic_arguments,
                                          parse_argstring)
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils import io

#-----------------------------------------------------------------------------
# Magics class implementation
#-----------------------------------------------------------------------------


_unspecified = object()


@magics_class
class HistoryMagics(Magics):

    @magic_arguments()
    @argument(
        '-n', dest='print_nums', action='store_true', default=False,
        help="""
        print line numbers for each input.
        This feature is only available if numbered prompts are in use.
        """)
    @argument(
        '-o', dest='get_output', action='store_true', default=False,
        help="also print outputs for each input.")
    @argument(
        '-p', dest='pyprompts', action='store_true', default=False,
        help="""
        print classic '>>>' python prompts before each input.
        This is useful for making documentation, and in conjunction
        with -o, for producing doctest-ready output.
        """)
    @argument(
        '-t', dest='raw', action='store_false', default=True,
        help="""
        print the 'translated' history, as IPython understands it.
        IPython filters your input and converts it all into valid Python
        source before executing it (things like magics or aliases are turned
        into function calls, for example). With this option, you'll see the
        native history instead of the user-entered version: '%%cd /' will be
        seen as 'get_ipython().run_line_magic("cd", "/")' instead of '%%cd /'.
        """)
    @argument(
        '-f', dest='filename',
        help="""
        FILENAME: instead of printing the output to the screen, redirect
        it to the given file.  The file is always overwritten, though *when
        it can*, IPython asks for confirmation first. In particular, running
        the command 'history -f FILENAME' from the IPython Notebook
        interface will replace FILENAME even if it already exists *without*
        confirmation.
        """)
    @argument(
        '-g', dest='pattern', nargs='*', default=None,
        help="""
        treat the arg as a glob pattern to search for in (full) history.
        This includes the saved history (almost all commands ever written).
        The pattern may contain '?' to match one unknown character and '*'
        to match any number of unknown characters. Use '%%hist -g' to show
        full saved history (may be very long).
        """)
    @argument(
        '-l', dest='limit', type=int, nargs='?', default=_unspecified,
        help="""
        get the last n lines from all sessions. Specify n as a single
        arg, or the default is the last 10 lines.
        """)
    @argument(
        '-u', dest='unique', action='store_true',
        help="""
        when searching history using `-g`, show only unique history.
        """)
    @argument('range', nargs='*')
    @skip_doctest
    @line_magic
    def history(self, parameter_s = ''):
        """Print input history (_i<n> variables), with most recent last.

        By default, input history is printed without line numbers so it can be
        directly pasted into an editor. Use -n to show them.

        By default, all input history from the current session is displayed.
        Ranges of history can be indicated using the syntax:

        ``4``
            Line 4, current session
        ``4-6``
            Lines 4-6, current session
        ``243/1-5``
            Lines 1-5, session 243
        ``~2/7``
            Line 7, session 2 before current
        ``~8/1-~6/5``
            From the first line of 8 sessions ago, to the fifth line of 6
            sessions ago.

        Multiple ranges can be entered, separated by spaces

        The same syntax is used by %macro, %save, %edit, %rerun

        Examples
        --------
        ::

          In [6]: %history -n 4-6
          4:a = 12
          5:print(a**2)
          6:%history -n 4-6

        """

        args = parse_argstring(self.history, parameter_s)

        # For brevity
        history_manager = self.shell.history_manager

        def _format_lineno(session, line):
            """Helper function to format line numbers properly."""
            if session in (0, history_manager.session_number):
                return str(line)
            return "%s/%s" % (session, line)

        # Check if output to specific file was requested.
        outfname = args.filename
        if not outfname:
            outfile = sys.stdout  # default
            # We don't want to close stdout at the end!
            close_at_end = False
        else:
            outfname = os.path.expanduser(outfname)
            if os.path.exists(outfname):
                try:
                    ans = io.ask_yes_no("File %r exists. Overwrite?" % outfname)
                except StdinNotImplementedError:
                    ans = True
                if not ans:
                    print('Aborting.')
                    return
                print("Overwriting file.")
            outfile = io_open(outfname, 'w', encoding='utf-8')
            close_at_end = True

        print_nums = args.print_nums
        get_output = args.get_output
        pyprompts = args.pyprompts
        raw = args.raw

        pattern = None
        limit = None if args.limit is _unspecified else args.limit

        range_pattern = False
        if args.pattern is not None and not args.range:
            if args.pattern:
                pattern = "*" + " ".join(args.pattern) + "*"
            else:
                pattern = "*"
            hist = history_manager.search(pattern, raw=raw, output=get_output,
                                          n=limit, unique=args.unique)
            print_nums = True
        elif args.limit is not _unspecified:
            n = 10 if limit is None else limit
            hist = history_manager.get_tail(n, raw=raw, output=get_output)
        else:
            if args.pattern:
                range_pattern = "*" + " ".join(args.pattern) + "*"
                print_nums = True
            hist = history_manager.get_range_by_str(
                " ".join(args.range), raw, get_output
            )

        # We could be displaying the entire history, so let's not try to pull
        # it into a list in memory. Anything that needs more space will just
        # misalign.
        width = 4

        for session, lineno, inline in hist:
            # Print user history with tabs expanded to 4 spaces.  The GUI
            # clients use hard tabs for easier usability in auto-indented code,
            # but we want to produce PEP-8 compliant history for safe pasting
            # into an editor.
            if get_output:
                inline, output = inline
            if range_pattern:
                if not fnmatch.fnmatch(inline, range_pattern):
                    continue
            inline = inline.expandtabs(4).rstrip()

            multiline = "\n" in inline
            line_sep = '\n' if multiline else ' '
            if print_nums:
                print(u'%s:%s' % (_format_lineno(session, lineno).rjust(width),
                        line_sep),  file=outfile, end=u'')
            if pyprompts:
                print(u">>> ", end=u"", file=outfile)
                if multiline:
                    inline = "\n... ".join(inline.splitlines()) + "\n..."
            print(inline, file=outfile)
            if get_output and output:
                print(output, file=outfile)

        if close_at_end:
            outfile.close()

    @line_magic
    def recall(self, arg):
        r"""Repeat a command, or get command to input line for editing.

        %recall and %rep are equivalent.

        - %recall (no arguments):

        Place a string version of last computation result (stored in the
        special '_' variable) to the next input prompt. Allows you to create
        elaborate command lines without using copy-paste::

             In[1]: l = ["hei", "vaan"]
             In[2]: "".join(l)
            Out[2]: heivaan
             In[3]: %recall
             In[4]: heivaan_ <== cursor blinking

        %recall 45

        Place history line 45 on the next input prompt. Use %hist to find
        out the number.

        %recall 1-4

        Combine the specified lines into one cell, and place it on the next
        input prompt. See %history for the slice syntax.

        %recall foo+bar

        If foo+bar can be evaluated in the user namespace, the result is
        placed at the next input prompt. Otherwise, the history is searched
        for lines which contain that substring, and the most recent one is
        placed at the next input prompt.
        """
        if not arg:                 # Last output
            self.shell.set_next_input(str(self.shell.user_ns["_"]))
            return
                                    # Get history range
        histlines = self.shell.history_manager.get_range_by_str(arg)
        cmd = "\n".join(x[2] for x in histlines)
        if cmd:
            self.shell.set_next_input(cmd.rstrip())
            return

        try:                        # Variable in user namespace
            cmd = str(eval(arg, self.shell.user_ns))
        except Exception:           # Search for term in history
            histlines = self.shell.history_manager.search("*"+arg+"*")
            for h in reversed([x[2] for x in histlines]):
                if 'recall' in h or 'rep' in h:
                    continue
                self.shell.set_next_input(h.rstrip())
                return
        else:
            self.shell.set_next_input(cmd.rstrip())
            return
        print("Couldn't evaluate or find in history:", arg)

    @line_magic
    def rerun(self, parameter_s=''):
        """Re-run previous input

        By default, you can specify ranges of input history to be repeated
        (as with %history). With no arguments, it will repeat the last line.

        Options:

          -l <n> : Repeat the last n lines of input, not including the
          current command.

          -g foo : Repeat the most recent line which contains foo
        """
        opts, args = self.parse_options(parameter_s, 'l:g:', mode='string')
        if "l" in opts:         # Last n lines
            try:
                n = int(opts["l"])
            except ValueError:
                print("Number of lines must be an integer")
                return

            if n == 0:
                print("Requested 0 last lines - nothing to run")
                return
            elif n < 0:
                print("Number of lines to rerun cannot be negative")
                return

            hist = self.shell.history_manager.get_tail(n)
        elif "g" in opts:       # Search
            p = "*"+opts['g']+"*"
            hist = list(self.shell.history_manager.search(p))
            for l in reversed(hist):
                if "rerun" not in l[2]:
                    hist = [l]     # The last match which isn't a %rerun
                    break
            else:
                hist = []          # No matches except %rerun
        elif args:              # Specify history ranges
            hist = self.shell.history_manager.get_range_by_str(args)
        else:                   # Last line
            hist = self.shell.history_manager.get_tail(1)
        hist = [x[2] for x in hist]
        if not hist:
            print("No lines in history match specification")
            return
        histlines = "\n".join(hist)
        print("=== Executing: ===")
        print(histlines)
        print("=== Output: ===")
        self.shell.run_cell("\n".join(hist), store_history=False)

# === NexusCore/openenv\Lib\site-packages\joblib\test\test_func_inspect.py ===
"""
Test the func_inspect module.
"""

# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2009 Gael Varoquaux
# License: BSD Style, 3 clauses.

import functools

from joblib.func_inspect import (
    _clean_win_chars,
    filter_args,
    format_signature,
    get_func_code,
    get_func_name,
)
from joblib.memory import Memory
from joblib.test.common import with_numpy
from joblib.testing import fixture, parametrize, raises


###############################################################################
# Module-level functions and fixture, for tests
def f(x, y=0):
    pass


def g(x):
    pass


def h(x, y=0, *args, **kwargs):
    pass


def i(x=1):
    pass


def j(x, y, **kwargs):
    pass


def k(*args, **kwargs):
    pass


def m1(x, *, y):
    pass


def m2(x, *, y, z=3):
    pass


@fixture(scope="module")
def cached_func(tmpdir_factory):
    # Create a Memory object to test decorated functions.
    # We should be careful not to call the decorated functions, so that
    # cache directories are not created in the temp dir.
    cachedir = tmpdir_factory.mktemp("joblib_test_func_inspect")
    mem = Memory(cachedir.strpath)

    @mem.cache
    def cached_func_inner(x):
        return x

    return cached_func_inner


class Klass(object):
    def f(self, x):
        return x


###############################################################################
# Tests


@parametrize(
    "func,args,filtered_args",
    [
        (f, [[], (1,)], {"x": 1, "y": 0}),
        (f, [["x"], (1,)], {"y": 0}),
        (f, [["y"], (0,)], {"x": 0}),
        (f, [["y"], (0,), {"y": 1}], {"x": 0}),
        (f, [["x", "y"], (0,)], {}),
        (f, [[], (0,), {"y": 1}], {"x": 0, "y": 1}),
        (f, [["y"], (), {"x": 2, "y": 1}], {"x": 2}),
        (g, [[], (), {"x": 1}], {"x": 1}),
        (i, [[], (2,)], {"x": 2}),
    ],
)
def test_filter_args(func, args, filtered_args):
    assert filter_args(func, *args) == filtered_args


def test_filter_args_method():
    obj = Klass()
    assert filter_args(obj.f, [], (1,)) == {"x": 1, "self": obj}


@parametrize(
    "func,args,filtered_args",
    [
        (h, [[], (1,)], {"x": 1, "y": 0, "*": [], "**": {}}),
        (h, [[], (1, 2, 3, 4)], {"x": 1, "y": 2, "*": [3, 4], "**": {}}),
        (h, [[], (1, 25), {"ee": 2}], {"x": 1, "y": 25, "*": [], "**": {"ee": 2}}),
        (h, [["*"], (1, 2, 25), {"ee": 2}], {"x": 1, "y": 2, "**": {"ee": 2}}),
    ],
)
def test_filter_varargs(func, args, filtered_args):
    assert filter_args(func, *args) == filtered_args


test_filter_kwargs_extra_params = [
    (m1, [[], (1,), {"y": 2}], {"x": 1, "y": 2}),
    (m2, [[], (1,), {"y": 2}], {"x": 1, "y": 2, "z": 3}),
]


@parametrize(
    "func,args,filtered_args",
    [
        (k, [[], (1, 2), {"ee": 2}], {"*": [1, 2], "**": {"ee": 2}}),
        (k, [[], (3, 4)], {"*": [3, 4], "**": {}}),
    ]
    + test_filter_kwargs_extra_params,
)
def test_filter_kwargs(func, args, filtered_args):
    assert filter_args(func, *args) == filtered_args


def test_filter_args_2():
    assert filter_args(j, [], (1, 2), {"ee": 2}) == {"x": 1, "y": 2, "**": {"ee": 2}}

    ff = functools.partial(f, 1)
    # filter_args has to special-case partial
    assert filter_args(ff, [], (1,)) == {"*": [1], "**": {}}
    assert filter_args(ff, ["y"], (1,)) == {"*": [1], "**": {}}


@parametrize("func,funcname", [(f, "f"), (g, "g"), (cached_func, "cached_func")])
def test_func_name(func, funcname):
    # Check that we are not confused by decoration
    # here testcase 'cached_func' is the function itself
    assert get_func_name(func)[1] == funcname


def test_func_name_on_inner_func(cached_func):
    # Check that we are not confused by decoration
    # here testcase 'cached_func' is the 'cached_func_inner' function
    # returned by 'cached_func' fixture
    assert get_func_name(cached_func)[1] == "cached_func_inner"


def test_func_name_collision_on_inner_func():
    # Check that two functions defining and caching an inner function
    # with the same do not cause (module, name) collision
    def f():
        def inner_func():
            return  # pragma: no cover

        return get_func_name(inner_func)

    def g():
        def inner_func():
            return  # pragma: no cover

        return get_func_name(inner_func)

    module, name = f()
    other_module, other_name = g()

    assert name == other_name
    assert module != other_module


def test_func_inspect_errors():
    # Check that func_inspect is robust and will work on weird objects
    assert get_func_name("a".lower)[-1] == "lower"
    assert get_func_code("a".lower)[1:] == (None, -1)
    ff = lambda x: x  # noqa: E731
    assert get_func_name(ff, win_characters=False)[-1] == "<lambda>"
    assert get_func_code(ff)[1] == __file__.replace(".pyc", ".py")
    # Simulate a function defined in __main__
    ff.__module__ = "__main__"
    assert get_func_name(ff, win_characters=False)[-1] == "<lambda>"
    assert get_func_code(ff)[1] == __file__.replace(".pyc", ".py")


def func_with_kwonly_args(a, b, *, kw1="kw1", kw2="kw2"):
    pass


def func_with_signature(a: int, b: int) -> None:
    pass


def test_filter_args_edge_cases():
    assert filter_args(func_with_kwonly_args, [], (1, 2), {"kw1": 3, "kw2": 4}) == {
        "a": 1,
        "b": 2,
        "kw1": 3,
        "kw2": 4,
    }

    # filter_args doesn't care about keyword-only arguments so you
    # can pass 'kw1' into *args without any problem
    with raises(ValueError) as excinfo:
        filter_args(func_with_kwonly_args, [], (1, 2, 3), {"kw2": 2})
    excinfo.match("Keyword-only parameter 'kw1' was passed as positional parameter")

    assert filter_args(
        func_with_kwonly_args, ["b", "kw2"], (1, 2), {"kw1": 3, "kw2": 4}
    ) == {"a": 1, "kw1": 3}

    assert filter_args(func_with_signature, ["b"], (1, 2)) == {"a": 1}


def test_bound_methods():
    """Make sure that calling the same method on two different instances
    of the same class does resolv to different signatures.
    """
    a = Klass()
    b = Klass()
    assert filter_args(a.f, [], (1,)) != filter_args(b.f, [], (1,))


@parametrize(
    "exception,regex,func,args",
    [
        (
            ValueError,
            "ignore_lst must be a list of parameters to ignore",
            f,
            ["bar", (None,)],
        ),
        (
            ValueError,
            r"Ignore list: argument \'(.*)\' is not defined",
            g,
            [["bar"], (None,)],
        ),
        (ValueError, "Wrong number of arguments", h, [[]]),
    ],
)
def test_filter_args_error_msg(exception, regex, func, args):
    """Make sure that filter_args returns decent error messages, for the
    sake of the user.
    """
    with raises(exception) as excinfo:
        filter_args(func, *args)
    excinfo.match(regex)


def test_filter_args_no_kwargs_mutation():
    """None-regression test against 0.12.0 changes.

    https://github.com/joblib/joblib/pull/75

    Make sure filter args doesn't mutate the kwargs dict that gets passed in.
    """
    kwargs = {"x": 0}
    filter_args(g, [], [], kwargs)
    assert kwargs == {"x": 0}


def test_clean_win_chars():
    string = r"C:\foo\bar\main.py"
    mangled_string = _clean_win_chars(string)
    for char in ("\\", ":", "<", ">", "!"):
        assert char not in mangled_string


@parametrize(
    "func,args,kwargs,sgn_expected",
    [
        (g, [list(range(5))], {}, "g([0, 1, 2, 3, 4])"),
        (k, [1, 2, (3, 4)], {"y": True}, "k(1, 2, (3, 4), y=True)"),
    ],
)
def test_format_signature(func, args, kwargs, sgn_expected):
    # Test signature formatting.
    path, sgn_result = format_signature(func, *args, **kwargs)
    assert sgn_result == sgn_expected


def test_format_signature_long_arguments():
    shortening_threshold = 1500
    # shortening gets it down to 700 characters but there is the name
    # of the function in the signature and a few additional things
    # like dots for the ellipsis
    shortening_target = 700 + 10

    arg = "a" * shortening_threshold
    _, signature = format_signature(h, arg)
    assert len(signature) < shortening_target

    nb_args = 5
    args = [arg for _ in range(nb_args)]
    _, signature = format_signature(h, *args)
    assert len(signature) < shortening_target * nb_args

    kwargs = {str(i): arg for i, arg in enumerate(args)}
    _, signature = format_signature(h, **kwargs)
    assert len(signature) < shortening_target * nb_args

    _, signature = format_signature(h, *args, **kwargs)
    assert len(signature) < shortening_target * 2 * nb_args


@with_numpy
def test_format_signature_numpy():
    """Test the format signature formatting with numpy."""


def test_special_source_encoding():
    from joblib.test.test_func_inspect_special_encoding import big5_f

    func_code, source_file, first_line = get_func_code(big5_f)
    assert first_line == 5
    assert "def big5_f():" in func_code
    assert "test_func_inspect_special_encoding" in source_file


def _get_code():
    from joblib.test.test_func_inspect_special_encoding import big5_f

    return get_func_code(big5_f)[0]


def test_func_code_consistency():
    from joblib.parallel import Parallel, delayed

    codes = Parallel(n_jobs=2)(delayed(_get_code)() for _ in range(5))
    assert len(set(codes)) == 1

# === NexusCore/openenv\Lib\site-packages\nltk\ccg\lexicon.py ===
# Natural Language Toolkit: Combinatory Categorial Grammar
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
CCG Lexicons
"""

import re
from collections import defaultdict

from nltk.ccg.api import CCGVar, Direction, FunctionalCategory, PrimitiveCategory
from nltk.internals import deprecated
from nltk.sem.logic import Expression

# ------------
# Regular expressions used for parsing components of the lexicon
# ------------

# Parses a primitive category and subscripts
PRIM_RE = re.compile(r"""([A-Za-z]+)(\[[A-Za-z,]+\])?""")

# Separates the next primitive category from the remainder of the
# string
NEXTPRIM_RE = re.compile(r"""([A-Za-z]+(?:\[[A-Za-z,]+\])?)(.*)""")

# Separates the next application operator from the remainder
APP_RE = re.compile(r"""([\\/])([.,]?)([.,]?)(.*)""")

# Parses the definition of the right-hand side (rhs) of either a word or a family
LEX_RE = re.compile(r"""([\S_]+)\s*(::|[-=]+>)\s*(.+)""", re.UNICODE)

# Parses the right hand side that contains category and maybe semantic predicate
RHS_RE = re.compile(r"""([^{}]*[^ {}])\s*(\{[^}]+\})?""", re.UNICODE)

# Parses the semantic predicate
SEMANTICS_RE = re.compile(r"""\{([^}]+)\}""", re.UNICODE)

# Strips comments from a line
COMMENTS_RE = re.compile("""([^#]*)(?:#.*)?""")


class Token:
    """
    Class representing a token.

    token => category {semantics}
    e.g. eat => S\\var[pl]/var {\\x y.eat(x,y)}

    * `token` (string)
    * `categ` (string)
    * `semantics` (Expression)
    """

    def __init__(self, token, categ, semantics=None):
        self._token = token
        self._categ = categ
        self._semantics = semantics

    def categ(self):
        return self._categ

    def semantics(self):
        return self._semantics

    def __str__(self):
        semantics_str = ""
        if self._semantics is not None:
            semantics_str = " {" + str(self._semantics) + "}"
        return "" + str(self._categ) + semantics_str

    def __cmp__(self, other):
        if not isinstance(other, Token):
            return -1
        return cmp((self._categ, self._semantics), other.categ(), other.semantics())


class CCGLexicon:
    """
    Class representing a lexicon for CCG grammars.

    * `primitives`: The list of primitive categories for the lexicon
    * `families`: Families of categories
    * `entries`: A mapping of words to possible categories
    """

    def __init__(self, start, primitives, families, entries):
        self._start = PrimitiveCategory(start)
        self._primitives = primitives
        self._families = families
        self._entries = entries

    def categories(self, word):
        """
        Returns all the possible categories for a word
        """
        return self._entries[word]

    def start(self):
        """
        Return the target category for the parser
        """
        return self._start

    def __str__(self):
        """
        String representation of the lexicon. Used for debugging.
        """
        string = ""
        first = True
        for ident in sorted(self._entries):
            if not first:
                string = string + "\n"
            string = string + ident + " => "

            first = True
            for cat in self._entries[ident]:
                if not first:
                    string = string + " | "
                else:
                    first = False
                string = string + "%s" % cat
        return string


# -----------
# Parsing lexicons
# -----------


def matchBrackets(string):
    """
    Separate the contents matching the first set of brackets from the rest of
    the input.
    """
    rest = string[1:]
    inside = "("

    while rest != "" and not rest.startswith(")"):
        if rest.startswith("("):
            (part, rest) = matchBrackets(rest)
            inside = inside + part
        else:
            inside = inside + rest[0]
            rest = rest[1:]
    if rest.startswith(")"):
        return (inside + ")", rest[1:])
    raise AssertionError("Unmatched bracket in string '" + string + "'")


def nextCategory(string):
    """
    Separate the string for the next portion of the category from the rest
    of the string
    """
    if string.startswith("("):
        return matchBrackets(string)
    return NEXTPRIM_RE.match(string).groups()


def parseApplication(app):
    """
    Parse an application operator
    """
    return Direction(app[0], app[1:])


def parseSubscripts(subscr):
    """
    Parse the subscripts for a primitive category
    """
    if subscr:
        return subscr[1:-1].split(",")
    return []


def parsePrimitiveCategory(chunks, primitives, families, var):
    """
    Parse a primitive category

    If the primitive is the special category 'var', replace it with the
    correct `CCGVar`.
    """
    if chunks[0] == "var":
        if chunks[1] is None:
            if var is None:
                var = CCGVar()
            return (var, var)

    catstr = chunks[0]
    if catstr in families:
        (cat, cvar) = families[catstr]
        if var is None:
            var = cvar
        else:
            cat = cat.substitute([(cvar, var)])
        return (cat, var)

    if catstr in primitives:
        subscrs = parseSubscripts(chunks[1])
        return (PrimitiveCategory(catstr, subscrs), var)
    raise AssertionError(
        "String '" + catstr + "' is neither a family nor primitive category."
    )


def augParseCategory(line, primitives, families, var=None):
    """
    Parse a string representing a category, and returns a tuple with
    (possibly) the CCG variable for the category
    """
    (cat_string, rest) = nextCategory(line)

    if cat_string.startswith("("):
        (res, var) = augParseCategory(cat_string[1:-1], primitives, families, var)

    else:
        (res, var) = parsePrimitiveCategory(
            PRIM_RE.match(cat_string).groups(), primitives, families, var
        )

    while rest != "":
        app = APP_RE.match(rest).groups()
        direction = parseApplication(app[0:3])
        rest = app[3]

        (cat_string, rest) = nextCategory(rest)
        if cat_string.startswith("("):
            (arg, var) = augParseCategory(cat_string[1:-1], primitives, families, var)
        else:
            (arg, var) = parsePrimitiveCategory(
                PRIM_RE.match(cat_string).groups(), primitives, families, var
            )
        res = FunctionalCategory(res, arg, direction)

    return (res, var)


def fromstring(lex_str, include_semantics=False):
    """
    Convert string representation into a lexicon for CCGs.
    """
    CCGVar.reset_id()
    primitives = []
    families = {}
    entries = defaultdict(list)
    for line in lex_str.splitlines():
        # Strip comments and leading/trailing whitespace.
        line = COMMENTS_RE.match(line).groups()[0].strip()
        if line == "":
            continue

        if line.startswith(":-"):
            # A line of primitive categories.
            # The first one is the target category
            # ie, :- S, N, NP, VP
            primitives = primitives + [
                prim.strip() for prim in line[2:].strip().split(",")
            ]
        else:
            # Either a family definition, or a word definition
            (ident, sep, rhs) = LEX_RE.match(line).groups()
            (catstr, semantics_str) = RHS_RE.match(rhs).groups()
            (cat, var) = augParseCategory(catstr, primitives, families)

            if sep == "::":
                # Family definition
                # ie, Det :: NP/N
                families[ident] = (cat, var)
            else:
                semantics = None
                if include_semantics is True:
                    if semantics_str is None:
                        raise AssertionError(
                            line
                            + " must contain semantics because include_semantics is set to True"
                        )
                    else:
                        semantics = Expression.fromstring(
                            SEMANTICS_RE.match(semantics_str).groups()[0]
                        )
                # Word definition
                # ie, which => (N\N)/(S/NP)
                entries[ident].append(Token(ident, cat, semantics))
    return CCGLexicon(primitives[0], primitives, families, entries)


@deprecated("Use fromstring() instead.")
def parseLexicon(lex_str):
    return fromstring(lex_str)


openccg_tinytiny = fromstring(
    """
    # Rather minimal lexicon based on the openccg `tinytiny' grammar.
    # Only incorporates a subset of the morphological subcategories, however.
    :- S,NP,N                    # Primitive categories
    Det :: NP/N                  # Determiners
    Pro :: NP
    IntransVsg :: S\\NP[sg]    # Tensed intransitive verbs (singular)
    IntransVpl :: S\\NP[pl]    # Plural
    TransVsg :: S\\NP[sg]/NP   # Tensed transitive verbs (singular)
    TransVpl :: S\\NP[pl]/NP   # Plural

    the => NP[sg]/N[sg]
    the => NP[pl]/N[pl]

    I => Pro
    me => Pro
    we => Pro
    us => Pro

    book => N[sg]
    books => N[pl]

    peach => N[sg]
    peaches => N[pl]

    policeman => N[sg]
    policemen => N[pl]

    boy => N[sg]
    boys => N[pl]

    sleep => IntransVsg
    sleep => IntransVpl

    eat => IntransVpl
    eat => TransVpl
    eats => IntransVsg
    eats => TransVsg

    see => TransVpl
    sees => TransVsg
    """
)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\formatters\terminal256.py ===
"""
    pygments.formatters.terminal256
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for 256-color terminal output with ANSI sequences.

    RGB-to-XTERM color conversion routines adapted from xterm256-conv
    tool (http://frexx.de/xterm-256-notes/data/xterm256-conv2.tar.bz2)
    by Wolfgang Frisch.

    Formatter version 1.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# TODO:
#  - Options to map style's bold/underline/italic/border attributes
#    to some ANSI attrbutes (something like 'italic=underline')
#  - An option to output "style RGB to xterm RGB/index" conversion table
#  - An option to indicate that we are running in "reverse background"
#    xterm. This means that default colors are white-on-black, not
#    black-on-while, so colors like "white background" need to be converted
#    to "white background, black foreground", etc...

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.console import codes
from pip._vendor.pygments.style import ansicolors


__all__ = ['Terminal256Formatter', 'TerminalTrueColorFormatter']


class EscapeSequence:
    def __init__(self, fg=None, bg=None, bold=False, underline=False, italic=False):
        self.fg = fg
        self.bg = bg
        self.bold = bold
        self.underline = underline
        self.italic = italic

    def escape(self, attrs):
        if len(attrs):
            return "\x1b[" + ";".join(attrs) + "m"
        return ""

    def color_string(self):
        attrs = []
        if self.fg is not None:
            if self.fg in ansicolors:
                esc = codes[self.fg.replace('ansi','')]
                if ';01m' in esc:
                    self.bold = True
                # extract fg color code.
                attrs.append(esc[2:4])
            else:
                attrs.extend(("38", "5", "%i" % self.fg))
        if self.bg is not None:
            if self.bg in ansicolors:
                esc = codes[self.bg.replace('ansi','')]
                # extract fg color code, add 10 for bg.
                attrs.append(str(int(esc[2:4])+10))
            else:
                attrs.extend(("48", "5", "%i" % self.bg))
        if self.bold:
            attrs.append("01")
        if self.underline:
            attrs.append("04")
        if self.italic:
            attrs.append("03")
        return self.escape(attrs)

    def true_color_string(self):
        attrs = []
        if self.fg:
            attrs.extend(("38", "2", str(self.fg[0]), str(self.fg[1]), str(self.fg[2])))
        if self.bg:
            attrs.extend(("48", "2", str(self.bg[0]), str(self.bg[1]), str(self.bg[2])))
        if self.bold:
            attrs.append("01")
        if self.underline:
            attrs.append("04")
        if self.italic:
            attrs.append("03")
        return self.escape(attrs)

    def reset_string(self):
        attrs = []
        if self.fg is not None:
            attrs.append("39")
        if self.bg is not None:
            attrs.append("49")
        if self.bold or self.underline or self.italic:
            attrs.append("00")
        return self.escape(attrs)


class Terminal256Formatter(Formatter):
    """
    Format tokens with ANSI color sequences, for output in a 256-color
    terminal or console.  Like in `TerminalFormatter` color sequences
    are terminated at newlines, so that paging the output works correctly.

    The formatter takes colors from a style defined by the `style` option
    and converts them to nearest ANSI 256-color escape sequences. Bold and
    underline attributes from the style are preserved (and displayed).

    .. versionadded:: 0.9

    .. versionchanged:: 2.2
       If the used style defines foreground colors in the form ``#ansi*``, then
       `Terminal256Formatter` will map these to non extended foreground color.
       See :ref:`AnsiTerminalStyle` for more information.

    .. versionchanged:: 2.4
       The ANSI color names have been updated with names that are easier to
       understand and align with colornames of other projects and terminals.
       See :ref:`this table <new-ansi-color-names>` for more information.


    Options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `linenos`
        Set to ``True`` to have line numbers on the terminal output as well
        (default: ``False`` = no line numbers).
    """
    name = 'Terminal256'
    aliases = ['terminal256', 'console256', '256']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)

        self.xterm_colors = []
        self.best_match = {}
        self.style_string = {}

        self.usebold = 'nobold' not in options
        self.useunderline = 'nounderline' not in options
        self.useitalic = 'noitalic' not in options

        self._build_color_table()  # build an RGB-to-256 color conversion table
        self._setup_styles()  # convert selected style's colors to term. colors

        self.linenos = options.get('linenos', False)
        self._lineno = 0

    def _build_color_table(self):
        # colors 0..15: 16 basic colors

        self.xterm_colors.append((0x00, 0x00, 0x00))  # 0
        self.xterm_colors.append((0xcd, 0x00, 0x00))  # 1
        self.xterm_colors.append((0x00, 0xcd, 0x00))  # 2
        self.xterm_colors.append((0xcd, 0xcd, 0x00))  # 3
        self.xterm_colors.append((0x00, 0x00, 0xee))  # 4
        self.xterm_colors.append((0xcd, 0x00, 0xcd))  # 5
        self.xterm_colors.append((0x00, 0xcd, 0xcd))  # 6
        self.xterm_colors.append((0xe5, 0xe5, 0xe5))  # 7
        self.xterm_colors.append((0x7f, 0x7f, 0x7f))  # 8
        self.xterm_colors.append((0xff, 0x00, 0x00))  # 9
        self.xterm_colors.append((0x00, 0xff, 0x00))  # 10
        self.xterm_colors.append((0xff, 0xff, 0x00))  # 11
        self.xterm_colors.append((0x5c, 0x5c, 0xff))  # 12
        self.xterm_colors.append((0xff, 0x00, 0xff))  # 13
        self.xterm_colors.append((0x00, 0xff, 0xff))  # 14
        self.xterm_colors.append((0xff, 0xff, 0xff))  # 15

        # colors 16..232: the 6x6x6 color cube

        valuerange = (0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff)

        for i in range(217):
            r = valuerange[(i // 36) % 6]
            g = valuerange[(i // 6) % 6]
            b = valuerange[i % 6]
            self.xterm_colors.append((r, g, b))

        # colors 233..253: grayscale

        for i in range(1, 22):
            v = 8 + i * 10
            self.xterm_colors.append((v, v, v))

    def _closest_color(self, r, g, b):
        distance = 257*257*3  # "infinity" (>distance from #000000 to #ffffff)
        match = 0

        for i in range(0, 254):
            values = self.xterm_colors[i]

            rd = r - values[0]
            gd = g - values[1]
            bd = b - values[2]
            d = rd*rd + gd*gd + bd*bd

            if d < distance:
                match = i
                distance = d
        return match

    def _color_index(self, color):
        index = self.best_match.get(color, None)
        if color in ansicolors:
            # strip the `ansi/#ansi` part and look up code
            index = color
            self.best_match[color] = index
        if index is None:
            try:
                rgb = int(str(color), 16)
            except ValueError:
                rgb = 0

            r = (rgb >> 16) & 0xff
            g = (rgb >> 8) & 0xff
            b = rgb & 0xff
            index = self._closest_color(r, g, b)
            self.best_match[color] = index
        return index

    def _setup_styles(self):
        for ttype, ndef in self.style:
            escape = EscapeSequence()
            # get foreground from ansicolor if set
            if ndef['ansicolor']:
                escape.fg = self._color_index(ndef['ansicolor'])
            elif ndef['color']:
                escape.fg = self._color_index(ndef['color'])
            if ndef['bgansicolor']:
                escape.bg = self._color_index(ndef['bgansicolor'])
            elif ndef['bgcolor']:
                escape.bg = self._color_index(ndef['bgcolor'])
            if self.usebold and ndef['bold']:
                escape.bold = True
            if self.useunderline and ndef['underline']:
                escape.underline = True
            if self.useitalic and ndef['italic']:
                escape.italic = True
            self.style_string[str(ttype)] = (escape.color_string(),
                                             escape.reset_string())

    def _write_lineno(self, outfile):
        self._lineno += 1
        outfile.write("%s%04d: " % (self._lineno != 1 and '\n' or '', self._lineno))

    def format(self, tokensource, outfile):
        return Formatter.format(self, tokensource, outfile)

    def format_unencoded(self, tokensource, outfile):
        if self.linenos:
            self._write_lineno(outfile)

        for ttype, value in tokensource:
            not_found = True
            while ttype and not_found:
                try:
                    # outfile.write( "<" + str(ttype) + ">" )
                    on, off = self.style_string[str(ttype)]

                    # Like TerminalFormatter, add "reset colors" escape sequence
                    # on newline.
                    spl = value.split('\n')
                    for line in spl[:-1]:
                        if line:
                            outfile.write(on + line + off)
                        if self.linenos:
                            self._write_lineno(outfile)
                        else:
                            outfile.write('\n')

                    if spl[-1]:
                        outfile.write(on + spl[-1] + off)

                    not_found = False
                    # outfile.write( '#' + str(ttype) + '#' )

                except KeyError:
                    # ottype = ttype
                    ttype = ttype.parent
                    # outfile.write( '!' + str(ottype) + '->' + str(ttype) + '!' )

            if not_found:
                outfile.write(value)

        if self.linenos:
            outfile.write("\n")



class TerminalTrueColorFormatter(Terminal256Formatter):
    r"""
    Format tokens with ANSI color sequences, for output in a true-color
    terminal or console.  Like in `TerminalFormatter` color sequences
    are terminated at newlines, so that paging the output works correctly.

    .. versionadded:: 2.1

    Options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).
    """
    name = 'TerminalTrueColor'
    aliases = ['terminal16m', 'console16m', '16m']
    filenames = []

    def _build_color_table(self):
        pass

    def _color_tuple(self, color):
        try:
            rgb = int(str(color), 16)
        except ValueError:
            return None
        r = (rgb >> 16) & 0xff
        g = (rgb >> 8) & 0xff
        b = rgb & 0xff
        return (r, g, b)

    def _setup_styles(self):
        for ttype, ndef in self.style:
            escape = EscapeSequence()
            if ndef['color']:
                escape.fg = self._color_tuple(ndef['color'])
            if ndef['bgcolor']:
                escape.bg = self._color_tuple(ndef['bgcolor'])
            if self.usebold and ndef['bold']:
                escape.bold = True
            if self.useunderline and ndef['underline']:
                escape.underline = True
            if self.useitalic and ndef['italic']:
                escape.italic = True
            self.style_string[str(ttype)] = (escape.true_color_string(),
                                             escape.reset_string())