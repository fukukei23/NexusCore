
# === NexusCore/tools\exports\export_20250803_114325\combined_203.py ===

# === NexusCore/openenv\Lib\site-packages\markdown_it\common\utils.py ===
"""Utilities for parsing source text
"""
from __future__ import annotations

import re
from typing import Match, TypeVar

from .entities import entities


def charCodeAt(src: str, pos: int) -> int | None:
    """
    Returns the Unicode value of the character at the specified location.

    @param - index The zero-based index of the desired character.
    If there is no character at the specified index, NaN is returned.

    This was added for compatibility with python
    """
    try:
        return ord(src[pos])
    except IndexError:
        return None


def charStrAt(src: str, pos: int) -> str | None:
    """
    Returns the Unicode value of the character at the specified location.

    @param - index The zero-based index of the desired character.
    If there is no character at the specified index, NaN is returned.

    This was added for compatibility with python
    """
    try:
        return src[pos]
    except IndexError:
        return None


_ItemTV = TypeVar("_ItemTV")


def arrayReplaceAt(
    src: list[_ItemTV], pos: int, newElements: list[_ItemTV]
) -> list[_ItemTV]:
    """
    Remove element from array and put another array at those position.
    Useful for some operations with tokens
    """
    return src[:pos] + newElements + src[pos + 1 :]


def isValidEntityCode(c: int) -> bool:
    # broken sequence
    if c >= 0xD800 and c <= 0xDFFF:
        return False
    # never used
    if c >= 0xFDD0 and c <= 0xFDEF:
        return False
    if ((c & 0xFFFF) == 0xFFFF) or ((c & 0xFFFF) == 0xFFFE):
        return False
    # control codes
    if c >= 0x00 and c <= 0x08:
        return False
    if c == 0x0B:
        return False
    if c >= 0x0E and c <= 0x1F:
        return False
    if c >= 0x7F and c <= 0x9F:
        return False
    # out of range
    if c > 0x10FFFF:
        return False
    return True


def fromCodePoint(c: int) -> str:
    """Convert ordinal to unicode.

    Note, in the original Javascript two string characters were required,
    for codepoints larger than `0xFFFF`.
    But Python 3 can represent any unicode codepoint in one character.
    """
    return chr(c)


# UNESCAPE_MD_RE = re.compile(r'\\([!"#$%&\'()*+,\-.\/:;<=>?@[\\\]^_`{|}~])')
# ENTITY_RE_g       = re.compile(r'&([a-z#][a-z0-9]{1,31})', re.IGNORECASE)
UNESCAPE_ALL_RE = re.compile(
    r'\\([!"#$%&\'()*+,\-.\/:;<=>?@[\\\]^_`{|}~])' + "|" + r"&([a-z#][a-z0-9]{1,31});",
    re.IGNORECASE,
)
DIGITAL_ENTITY_BASE10_RE = re.compile(r"#([0-9]{1,8})")
DIGITAL_ENTITY_BASE16_RE = re.compile(r"#x([a-f0-9]{1,8})", re.IGNORECASE)


def replaceEntityPattern(match: str, name: str) -> str:
    """Convert HTML entity patterns,
    see https://spec.commonmark.org/0.30/#entity-references
    """
    if name in entities:
        return entities[name]

    code: None | int = None
    if pat := DIGITAL_ENTITY_BASE10_RE.fullmatch(name):
        code = int(pat.group(1), 10)
    elif pat := DIGITAL_ENTITY_BASE16_RE.fullmatch(name):
        code = int(pat.group(1), 16)

    if code is not None and isValidEntityCode(code):
        return fromCodePoint(code)

    return match


def unescapeAll(string: str) -> str:
    def replacer_func(match: Match[str]) -> str:
        escaped = match.group(1)
        if escaped:
            return escaped
        entity = match.group(2)
        return replaceEntityPattern(match.group(), entity)

    if "\\" not in string and "&" not in string:
        return string
    return UNESCAPE_ALL_RE.sub(replacer_func, string)


ESCAPABLE = r"""\\!"#$%&'()*+,./:;<=>?@\[\]^`{}|_~-"""
ESCAPE_CHAR = re.compile(r"\\([" + ESCAPABLE + r"])")


def stripEscape(string: str) -> str:
    """Strip escape \\ characters"""
    return ESCAPE_CHAR.sub(r"\1", string)


def escapeHtml(raw: str) -> str:
    """Replace special characters "&", "<", ">" and '"' to HTML-safe sequences."""
    # like html.escape, but without escaping single quotes
    raw = raw.replace("&", "&amp;")  # Must be done first!
    raw = raw.replace("<", "&lt;")
    raw = raw.replace(">", "&gt;")
    raw = raw.replace('"', "&quot;")
    return raw


# //////////////////////////////////////////////////////////////////////////////

REGEXP_ESCAPE_RE = re.compile(r"[.?*+^$[\]\\(){}|-]")


def escapeRE(string: str) -> str:
    string = REGEXP_ESCAPE_RE.sub("\\$&", string)
    return string


# //////////////////////////////////////////////////////////////////////////////


def isSpace(code: int | None) -> bool:
    """Check if character code is a whitespace."""
    return code in (0x09, 0x20)


def isStrSpace(ch: str | None) -> bool:
    """Check if character is a whitespace."""
    return ch in ("\t", " ")


MD_WHITESPACE = {
    0x09,  # \t
    0x0A,  # \n
    0x0B,  # \v
    0x0C,  # \f
    0x0D,  # \r
    0x20,  # space
    0xA0,
    0x1680,
    0x202F,
    0x205F,
    0x3000,
}


def isWhiteSpace(code: int) -> bool:
    r"""Zs (unicode class) || [\t\f\v\r\n]"""
    if code >= 0x2000 and code <= 0x200A:
        return True
    return code in MD_WHITESPACE


# //////////////////////////////////////////////////////////////////////////////

UNICODE_PUNCT_RE = re.compile(
    r"[!-#%-\*,-\/:;\?@\[-\]_\{\}\xA1\xA7\xAB\xB6\xB7\xBB\xBF\u037E\u0387\u055A-\u055F\u0589\u058A\u05BE\u05C0\u05C3\u05C6\u05F3\u05F4\u0609\u060A\u060C\u060D\u061B\u061E\u061F\u066A-\u066D\u06D4\u0700-\u070D\u07F7-\u07F9\u0830-\u083E\u085E\u0964\u0965\u0970\u09FD\u0A76\u0AF0\u0C84\u0DF4\u0E4F\u0E5A\u0E5B\u0F04-\u0F12\u0F14\u0F3A-\u0F3D\u0F85\u0FD0-\u0FD4\u0FD9\u0FDA\u104A-\u104F\u10FB\u1360-\u1368\u1400\u166D\u166E\u169B\u169C\u16EB-\u16ED\u1735\u1736\u17D4-\u17D6\u17D8-\u17DA\u1800-\u180A\u1944\u1945\u1A1E\u1A1F\u1AA0-\u1AA6\u1AA8-\u1AAD\u1B5A-\u1B60\u1BFC-\u1BFF\u1C3B-\u1C3F\u1C7E\u1C7F\u1CC0-\u1CC7\u1CD3\u2010-\u2027\u2030-\u2043\u2045-\u2051\u2053-\u205E\u207D\u207E\u208D\u208E\u2308-\u230B\u2329\u232A\u2768-\u2775\u27C5\u27C6\u27E6-\u27EF\u2983-\u2998\u29D8-\u29DB\u29FC\u29FD\u2CF9-\u2CFC\u2CFE\u2CFF\u2D70\u2E00-\u2E2E\u2E30-\u2E4E\u3001-\u3003\u3008-\u3011\u3014-\u301F\u3030\u303D\u30A0\u30FB\uA4FE\uA4FF\uA60D-\uA60F\uA673\uA67E\uA6F2-\uA6F7\uA874-\uA877\uA8CE\uA8CF\uA8F8-\uA8FA\uA8FC\uA92E\uA92F\uA95F\uA9C1-\uA9CD\uA9DE\uA9DF\uAA5C-\uAA5F\uAADE\uAADF\uAAF0\uAAF1\uABEB\uFD3E\uFD3F\uFE10-\uFE19\uFE30-\uFE52\uFE54-\uFE61\uFE63\uFE68\uFE6A\uFE6B\uFF01-\uFF03\uFF05-\uFF0A\uFF0C-\uFF0F\uFF1A\uFF1B\uFF1F\uFF20\uFF3B-\uFF3D\uFF3F\uFF5B\uFF5D\uFF5F-\uFF65]|\uD800[\uDD00-\uDD02\uDF9F\uDFD0]|\uD801\uDD6F|\uD802[\uDC57\uDD1F\uDD3F\uDE50-\uDE58\uDE7F\uDEF0-\uDEF6\uDF39-\uDF3F\uDF99-\uDF9C]|\uD803[\uDF55-\uDF59]|\uD804[\uDC47-\uDC4D\uDCBB\uDCBC\uDCBE-\uDCC1\uDD40-\uDD43\uDD74\uDD75\uDDC5-\uDDC8\uDDCD\uDDDB\uDDDD-\uDDDF\uDE38-\uDE3D\uDEA9]|\uD805[\uDC4B-\uDC4F\uDC5B\uDC5D\uDCC6\uDDC1-\uDDD7\uDE41-\uDE43\uDE60-\uDE6C\uDF3C-\uDF3E]|\uD806[\uDC3B\uDE3F-\uDE46\uDE9A-\uDE9C\uDE9E-\uDEA2]|\uD807[\uDC41-\uDC45\uDC70\uDC71\uDEF7\uDEF8]|\uD809[\uDC70-\uDC74]|\uD81A[\uDE6E\uDE6F\uDEF5\uDF37-\uDF3B\uDF44]|\uD81B[\uDE97-\uDE9A]|\uD82F\uDC9F|\uD836[\uDE87-\uDE8B]|\uD83A[\uDD5E\uDD5F]"  # noqa: E501
)


# Currently without astral characters support.
def isPunctChar(ch: str) -> bool:
    """Check if character is a punctuation character."""
    return UNICODE_PUNCT_RE.search(ch) is not None


MD_ASCII_PUNCT = {
    0x21,  # /* ! */
    0x22,  # /* " */
    0x23,  # /* # */
    0x24,  # /* $ */
    0x25,  # /* % */
    0x26,  # /* & */
    0x27,  # /* ' */
    0x28,  # /* ( */
    0x29,  # /* ) */
    0x2A,  # /* * */
    0x2B,  # /* + */
    0x2C,  # /* , */
    0x2D,  # /* - */
    0x2E,  # /* . */
    0x2F,  # /* / */
    0x3A,  # /* : */
    0x3B,  # /* ; */
    0x3C,  # /* < */
    0x3D,  # /* = */
    0x3E,  # /* > */
    0x3F,  # /* ? */
    0x40,  # /* @ */
    0x5B,  # /* [ */
    0x5C,  # /* \ */
    0x5D,  # /* ] */
    0x5E,  # /* ^ */
    0x5F,  # /* _ */
    0x60,  # /* ` */
    0x7B,  # /* { */
    0x7C,  # /* | */
    0x7D,  # /* } */
    0x7E,  # /* ~ */
}


def isMdAsciiPunct(ch: int) -> bool:
    """Markdown ASCII punctuation characters.

    ::

        !, ", #, $, %, &, ', (, ), *, +, ,, -, ., /, :, ;, <, =, >, ?, @, [, \\, ], ^, _, `, {, |, }, or ~

    See http://spec.commonmark.org/0.15/#ascii-punctuation-character

    Don't confuse with unicode punctuation !!! It lacks some chars in ascii range.

    """  # noqa: E501
    return ch in MD_ASCII_PUNCT


def normalizeReference(string: str) -> str:
    """Helper to unify [reference labels]."""
    # Trim and collapse whitespace
    #
    string = re.sub(r"\s+", " ", string.strip())

    # In node v10 'ẞ'.toLowerCase() === 'Ṿ', which is presumed to be a bug
    # fixed in v12 (couldn't find any details).
    #
    # So treat this one as a special case
    # (remove this when node v10 is no longer supported).
    #
    # if ('ẞ'.toLowerCase() === 'Ṿ') {
    #   str = str.replace(/ẞ/g, 'ß')
    # }

    # .toLowerCase().toUpperCase() should get rid of all differences
    # between letter variants.
    #
    # Simple .toLowerCase() doesn't normalize 125 code points correctly,
    # and .toUpperCase doesn't normalize 6 of them (list of exceptions:
    # İ, ϴ, ẞ, Ω, K, Å - those are already uppercased, but have differently
    # uppercased versions).
    #
    # Here's an example showing how it happens. Lets take greek letter omega:
    # uppercase U+0398 (Θ), U+03f4 (ϴ) and lowercase U+03b8 (θ), U+03d1 (ϑ)
    #
    # Unicode entries:
    # 0398;GREEK CAPITAL LETTER THETA;Lu;0;L;;;;;N;;;;03B8
    # 03B8;GREEK SMALL LETTER THETA;Ll;0;L;;;;;N;;;0398;;0398
    # 03D1;GREEK THETA SYMBOL;Ll;0;L;<compat> 03B8;;;;N;GREEK SMALL LETTER SCRIPT THETA;;0398;;0398
    # 03F4;GREEK CAPITAL THETA SYMBOL;Lu;0;L;<compat> 0398;;;;N;;;;03B8
    #
    # Case-insensitive comparison should treat all of them as equivalent.
    #
    # But .toLowerCase() doesn't change ϑ (it's already lowercase),
    # and .toUpperCase() doesn't change ϴ (already uppercase).
    #
    # Applying first lower then upper case normalizes any character:
    # '\u0398\u03f4\u03b8\u03d1'.toLowerCase().toUpperCase() === '\u0398\u0398\u0398\u0398'
    #
    # Note: this is equivalent to unicode case folding; unicode normalization
    # is a different step that is not required here.
    #
    # Final result should be uppercased, because it's later stored in an object
    # (this avoid a conflict with Object.prototype members,
    # most notably, `__proto__`)
    #
    return string.lower().upper()


LINK_OPEN_RE = re.compile(r"^<a[>\s]", flags=re.IGNORECASE)
LINK_CLOSE_RE = re.compile(r"^</a\s*>", flags=re.IGNORECASE)


def isLinkOpen(string: str) -> bool:
    return bool(LINK_OPEN_RE.search(string))


def isLinkClose(string: str) -> bool:
    return bool(LINK_CLOSE_RE.search(string))

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\panel.py ===
from typing import TYPE_CHECKING, Optional

from .align import AlignMethod
from .box import ROUNDED, Box
from .cells import cell_len
from .jupyter import JupyterMixin
from .measure import Measurement, measure_renderables
from .padding import Padding, PaddingDimensions
from .segment import Segment
from .style import Style, StyleType
from .text import Text, TextType

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderableType, RenderResult


class Panel(JupyterMixin):
    """A console renderable that draws a border around its contents.

    Example:
        >>> console.print(Panel("Hello, World!"))

    Args:
        renderable (RenderableType): A console renderable object.
        box (Box, optional): A Box instance that defines the look of the border (see :ref:`appendix_box`. Defaults to box.ROUNDED.
        title (Optional[TextType], optional): Optional title displayed in panel header. Defaults to None.
        title_align (AlignMethod, optional): Alignment of title. Defaults to "center".
        subtitle (Optional[TextType], optional): Optional subtitle displayed in panel footer. Defaults to None.
        subtitle_align (AlignMethod, optional): Alignment of subtitle. Defaults to "center".
        safe_box (bool, optional): Disable box characters that don't display on windows legacy terminal with *raster* fonts. Defaults to True.
        expand (bool, optional): If True the panel will stretch to fill the console width, otherwise it will be sized to fit the contents. Defaults to True.
        style (str, optional): The style of the panel (border and contents). Defaults to "none".
        border_style (str, optional): The style of the border. Defaults to "none".
        width (Optional[int], optional): Optional width of panel. Defaults to None to auto-detect.
        height (Optional[int], optional): Optional height of panel. Defaults to None to auto-detect.
        padding (Optional[PaddingDimensions]): Optional padding around renderable. Defaults to 0.
        highlight (bool, optional): Enable automatic highlighting of panel title (if str). Defaults to False.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        box: Box = ROUNDED,
        *,
        title: Optional[TextType] = None,
        title_align: AlignMethod = "center",
        subtitle: Optional[TextType] = None,
        subtitle_align: AlignMethod = "center",
        safe_box: Optional[bool] = None,
        expand: bool = True,
        style: StyleType = "none",
        border_style: StyleType = "none",
        width: Optional[int] = None,
        height: Optional[int] = None,
        padding: PaddingDimensions = (0, 1),
        highlight: bool = False,
    ) -> None:
        self.renderable = renderable
        self.box = box
        self.title = title
        self.title_align: AlignMethod = title_align
        self.subtitle = subtitle
        self.subtitle_align = subtitle_align
        self.safe_box = safe_box
        self.expand = expand
        self.style = style
        self.border_style = border_style
        self.width = width
        self.height = height
        self.padding = padding
        self.highlight = highlight

    @classmethod
    def fit(
        cls,
        renderable: "RenderableType",
        box: Box = ROUNDED,
        *,
        title: Optional[TextType] = None,
        title_align: AlignMethod = "center",
        subtitle: Optional[TextType] = None,
        subtitle_align: AlignMethod = "center",
        safe_box: Optional[bool] = None,
        style: StyleType = "none",
        border_style: StyleType = "none",
        width: Optional[int] = None,
        height: Optional[int] = None,
        padding: PaddingDimensions = (0, 1),
        highlight: bool = False,
    ) -> "Panel":
        """An alternative constructor that sets expand=False."""
        return cls(
            renderable,
            box,
            title=title,
            title_align=title_align,
            subtitle=subtitle,
            subtitle_align=subtitle_align,
            safe_box=safe_box,
            style=style,
            border_style=border_style,
            width=width,
            height=height,
            padding=padding,
            highlight=highlight,
            expand=False,
        )

    @property
    def _title(self) -> Optional[Text]:
        if self.title:
            title_text = (
                Text.from_markup(self.title)
                if isinstance(self.title, str)
                else self.title.copy()
            )
            title_text.end = ""
            title_text.plain = title_text.plain.replace("\n", " ")
            title_text.no_wrap = True
            title_text.expand_tabs()
            title_text.pad(1)
            return title_text
        return None

    @property
    def _subtitle(self) -> Optional[Text]:
        if self.subtitle:
            subtitle_text = (
                Text.from_markup(self.subtitle)
                if isinstance(self.subtitle, str)
                else self.subtitle.copy()
            )
            subtitle_text.end = ""
            subtitle_text.plain = subtitle_text.plain.replace("\n", " ")
            subtitle_text.no_wrap = True
            subtitle_text.expand_tabs()
            subtitle_text.pad(1)
            return subtitle_text
        return None

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        _padding = Padding.unpack(self.padding)
        renderable = (
            Padding(self.renderable, _padding) if any(_padding) else self.renderable
        )
        style = console.get_style(self.style)
        partial_border_style = console.get_style(self.border_style)
        border_style = style + partial_border_style
        width = (
            options.max_width
            if self.width is None
            else min(options.max_width, self.width)
        )

        safe_box: bool = console.safe_box if self.safe_box is None else self.safe_box
        box = self.box.substitute(options, safe=safe_box)

        def align_text(
            text: Text, width: int, align: str, character: str, style: Style
        ) -> Text:
            """Gets new aligned text.

            Args:
                text (Text): Title or subtitle text.
                width (int): Desired width.
                align (str): Alignment.
                character (str): Character for alignment.
                style (Style): Border style

            Returns:
                Text: New text instance
            """
            text = text.copy()
            text.truncate(width)
            excess_space = width - cell_len(text.plain)
            if text.style:
                text.stylize(console.get_style(text.style))

            if excess_space:
                if align == "left":
                    return Text.assemble(
                        text,
                        (character * excess_space, style),
                        no_wrap=True,
                        end="",
                    )
                elif align == "center":
                    left = excess_space // 2
                    return Text.assemble(
                        (character * left, style),
                        text,
                        (character * (excess_space - left), style),
                        no_wrap=True,
                        end="",
                    )
                else:
                    return Text.assemble(
                        (character * excess_space, style),
                        text,
                        no_wrap=True,
                        end="",
                    )
            return text

        title_text = self._title
        if title_text is not None:
            title_text.stylize_before(partial_border_style)

        child_width = (
            width - 2
            if self.expand
            else console.measure(
                renderable, options=options.update_width(width - 2)
            ).maximum
        )
        child_height = self.height or options.height or None
        if child_height:
            child_height -= 2
        if title_text is not None:
            child_width = min(
                options.max_width - 2, max(child_width, title_text.cell_len + 2)
            )

        width = child_width + 2
        child_options = options.update(
            width=child_width, height=child_height, highlight=self.highlight
        )
        lines = console.render_lines(renderable, child_options, style=style)

        line_start = Segment(box.mid_left, border_style)
        line_end = Segment(f"{box.mid_right}", border_style)
        new_line = Segment.line()
        if title_text is None or width <= 4:
            yield Segment(box.get_top([width - 2]), border_style)
        else:
            title_text = align_text(
                title_text,
                width - 4,
                self.title_align,
                box.top,
                border_style,
            )
            yield Segment(box.top_left + box.top, border_style)
            yield from console.render(title_text, child_options.update_width(width - 4))
            yield Segment(box.top + box.top_right, border_style)

        yield new_line
        for line in lines:
            yield line_start
            yield from line
            yield line_end
            yield new_line

        subtitle_text = self._subtitle
        if subtitle_text is not None:
            subtitle_text.stylize_before(partial_border_style)

        if subtitle_text is None or width <= 4:
            yield Segment(box.get_bottom([width - 2]), border_style)
        else:
            subtitle_text = align_text(
                subtitle_text,
                width - 4,
                self.subtitle_align,
                box.bottom,
                border_style,
            )
            yield Segment(box.bottom_left + box.bottom, border_style)
            yield from console.render(
                subtitle_text, child_options.update_width(width - 4)
            )
            yield Segment(box.bottom + box.bottom_right, border_style)

        yield new_line

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        _title = self._title
        _, right, _, left = Padding.unpack(self.padding)
        padding = left + right
        renderables = [self.renderable, _title] if _title else [self.renderable]

        if self.width is None:
            width = (
                measure_renderables(
                    console,
                    options.update_width(options.max_width - padding - 2),
                    renderables,
                ).maximum
                + padding
                + 2
            )
        else:
            width = self.width
        return Measurement(width, width)


if __name__ == "__main__":  # pragma: no cover
    from .console import Console

    c = Console()

    from .box import DOUBLE, ROUNDED
    from .padding import Padding

    p = Panel(
        "Hello, World!",
        title="rich.Panel",
        style="white on blue",
        box=DOUBLE,
        padding=1,
    )

    c.print()
    c.print(p)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\prolog.py ===
"""
    pygments.lexers.prolog
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Prolog and Prolog-like languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation

__all__ = ['PrologLexer', 'LogtalkLexer']


class PrologLexer(RegexLexer):
    """
    Lexer for Prolog files.
    """
    name = 'Prolog'
    aliases = ['prolog']
    filenames = ['*.ecl', '*.prolog', '*.pro', '*.pl']
    mimetypes = ['text/x-prolog']
    url = 'https://en.wikipedia.org/wiki/Prolog'
    version_added = ''

    tokens = {
        'root': [
            (r'/\*', Comment.Multiline, 'nested-comment'),
            (r'%.*', Comment.Single),
            # character literal
            (r'0\'.', String.Char),
            (r'0b[01]+', Number.Bin),
            (r'0o[0-7]+', Number.Oct),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            # literal with prepended base
            (r'\d\d?\'[a-zA-Z0-9]+', Number.Integer),
            (r'(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?', Number.Float),
            (r'\d+', Number.Integer),
            (r'[\[\](){}|.,;!]', Punctuation),
            (r':-|-->', Punctuation),
            (r'"(?:\\x[0-9a-fA-F]+\\|\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}|'
             r'\\[0-7]+\\|\\["\\abcefnrstv]|[^\\"])*"', String.Double),
            (r"'(?:''|[^'])*'", String.Atom),  # quoted atom
            # Needs to not be followed by an atom.
            # (r'=(?=\s|[a-zA-Z\[])', Operator),
            (r'is\b', Operator),
            (r'(<|>|=<|>=|==|=:=|=|/|//|\*|\+|-)(?=\s|[a-zA-Z0-9\[])',
             Operator),
            (r'(mod|div|not)\b', Operator),
            (r'_', Keyword),  # The don't-care variable
            (r'([a-z]+)(:)', bygroups(Name.Namespace, Punctuation)),
            (r'([a-z\u00c0-\u1fff\u3040-\ud7ff\ue000-\uffef]'
             r'[\w$\u00c0-\u1fff\u3040-\ud7ff\ue000-\uffef]*)'
             r'(\s*)(:-|-->)',
             bygroups(Name.Function, Text, Operator)),  # function defn
            (r'([a-z\u00c0-\u1fff\u3040-\ud7ff\ue000-\uffef]'
             r'[\w$\u00c0-\u1fff\u3040-\ud7ff\ue000-\uffef]*)'
             r'(\s*)(\()',
             bygroups(Name.Function, Text, Punctuation)),
            (r'[a-z\u00c0-\u1fff\u3040-\ud7ff\ue000-\uffef]'
             r'[\w$\u00c0-\u1fff\u3040-\ud7ff\ue000-\uffef]*',
             String.Atom),  # atom, characters
            # This one includes !
            (r'[#&*+\-./:<=>?@\\^~\u00a1-\u00bf\u2010-\u303f]+',
             String.Atom),  # atom, graphics
            (r'[A-Z_]\w*', Name.Variable),
            (r'\s+|[\u2000-\u200f\ufff0-\ufffe\uffef]', Text),
        ],
        'nested-comment': [
            (r'\*/', Comment.Multiline, '#pop'),
            (r'/\*', Comment.Multiline, '#push'),
            (r'[^*/]+', Comment.Multiline),
            (r'[*/]', Comment.Multiline),
        ],
    }

    def analyse_text(text):
        """Competes with IDL and Visual Prolog on *.pro"""
        if ':-' in text:
            # Visual Prolog also uses :-
            return 0.5
        else:
            return 0


class LogtalkLexer(RegexLexer):
    """
    For Logtalk source code.
    """

    name = 'Logtalk'
    url = 'http://logtalk.org/'
    aliases = ['logtalk']
    filenames = ['*.lgt', '*.logtalk']
    mimetypes = ['text/x-logtalk']
    version_added = '0.10'

    tokens = {
        'root': [
            # Directives
            (r'^\s*:-\s', Punctuation, 'directive'),
            # Comments
            (r'%.*?\n', Comment),
            (r'/\*(.|\n)*?\*/', Comment),
            # Whitespace
            (r'\n', Text),
            (r'\s+', Text),
            # Numbers
            (r"0'[\\]?.", Number),
            (r'0b[01]+', Number.Bin),
            (r'0o[0-7]+', Number.Oct),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'\d+\.?\d*((e|E)(\+|-)?\d+)?', Number),
            # Variables
            (r'([A-Z_][a-zA-Z0-9_]*)', Name.Variable),
            # Event handlers
            (r'(after|before)(?=[(])', Keyword),
            # Message forwarding handler
            (r'forward(?=[(])', Keyword),
            # Execution-context methods
            (r'(context|parameter|this|se(lf|nder))(?=[(])', Keyword),
            # Reflection
            (r'(current_predicate|predicate_property)(?=[(])', Keyword),
            # DCGs and term expansion
            (r'(expand_(goal|term)|(goal|term)_expansion|phrase)(?=[(])', Keyword),
            # Entity
            (r'(abolish|c(reate|urrent))_(object|protocol|category)(?=[(])', Keyword),
            (r'(object|protocol|category)_property(?=[(])', Keyword),
            # Entity relations
            (r'co(mplements_object|nforms_to_protocol)(?=[(])', Keyword),
            (r'extends_(object|protocol|category)(?=[(])', Keyword),
            (r'imp(lements_protocol|orts_category)(?=[(])', Keyword),
            (r'(instantiat|specializ)es_class(?=[(])', Keyword),
            # Events
            (r'(current_event|(abolish|define)_events)(?=[(])', Keyword),
            # Flags
            (r'(create|current|set)_logtalk_flag(?=[(])', Keyword),
            # Compiling, loading, and library paths
            (r'logtalk_(compile|l(ibrary_path|oad|oad_context)|make(_target_action)?)(?=[(])', Keyword),
            (r'\blogtalk_make\b', Keyword),
            # Database
            (r'(clause|retract(all)?)(?=[(])', Keyword),
            (r'a(bolish|ssert(a|z))(?=[(])', Keyword),
            # Control constructs
            (r'(ca(ll|tch)|throw)(?=[(])', Keyword),
            (r'(fa(il|lse)|true|(instantiation|system)_error)\b', Keyword),
            (r'(uninstantiation|type|domain|existence|permission|representation|evaluation|resource|syntax)_error(?=[(])', Keyword),
            # All solutions
            (r'((bag|set)of|f(ind|or)all)(?=[(])', Keyword),
            # Multi-threading predicates
            (r'threaded(_(ca(ll|ncel)|once|ignore|exit|peek|wait|notify))?(?=[(])', Keyword),
            # Engine predicates
            (r'threaded_engine(_(create|destroy|self|next|next_reified|yield|post|fetch))?(?=[(])', Keyword),
            # Term unification
            (r'(subsumes_term|unify_with_occurs_check)(?=[(])', Keyword),
            # Term creation and decomposition
            (r'(functor|arg|copy_term|numbervars|term_variables)(?=[(])', Keyword),
            # Evaluable functors
            (r'(div|rem|m(ax|in|od)|abs|sign)(?=[(])', Keyword),
            (r'float(_(integer|fractional)_part)?(?=[(])', Keyword),
            (r'(floor|t(an|runcate)|round|ceiling)(?=[(])', Keyword),
            # Other arithmetic functors
            (r'(cos|a(cos|sin|tan|tan2)|exp|log|s(in|qrt)|xor)(?=[(])', Keyword),
            # Term testing
            (r'(var|atom(ic)?|integer|float|c(allable|ompound)|n(onvar|umber)|ground|acyclic_term)(?=[(])', Keyword),
            # Term comparison
            (r'compare(?=[(])', Keyword),
            # Stream selection and control
            (r'(curren|se)t_(in|out)put(?=[(])', Keyword),
            (r'(open|close)(?=[(])', Keyword),
            (r'flush_output(?=[(])', Keyword),
            (r'(at_end_of_stream|flush_output)\b', Keyword),
            (r'(stream_property|at_end_of_stream|set_stream_position)(?=[(])', Keyword),
            # Character and byte input/output
            (r'(nl|(get|peek|put)_(byte|c(har|ode)))(?=[(])', Keyword),
            (r'\bnl\b', Keyword),
            # Term input/output
            (r'read(_term)?(?=[(])', Keyword),
            (r'write(q|_(canonical|term))?(?=[(])', Keyword),
            (r'(current_)?op(?=[(])', Keyword),
            (r'(current_)?char_conversion(?=[(])', Keyword),
            # Atomic term processing
            (r'atom_(length|c(hars|o(ncat|des)))(?=[(])', Keyword),
            (r'(char_code|sub_atom)(?=[(])', Keyword),
            (r'number_c(har|ode)s(?=[(])', Keyword),
            # Implementation defined hooks functions
            (r'(se|curren)t_prolog_flag(?=[(])', Keyword),
            (r'\bhalt\b', Keyword),
            (r'halt(?=[(])', Keyword),
            # Message sending operators
            (r'(::|:|\^\^)', Operator),
            # External call
            (r'[{}]', Keyword),
            # Logic and control
            (r'(ignore|once)(?=[(])', Keyword),
            (r'\brepeat\b', Keyword),
            # Sorting
            (r'(key)?sort(?=[(])', Keyword),
            # Bitwise functors
            (r'(>>|<<|/\\|\\\\|\\)', Operator),
            # Predicate aliases
            (r'\bas\b', Operator),
            # Arithmetic evaluation
            (r'\bis\b', Keyword),
            # Arithmetic comparison
            (r'(=:=|=\\=|<|=<|>=|>)', Operator),
            # Term creation and decomposition
            (r'=\.\.', Operator),
            # Term unification
            (r'(=|\\=)', Operator),
            # Term comparison
            (r'(==|\\==|@=<|@<|@>=|@>)', Operator),
            # Evaluable functors
            (r'(//|[-+*/])', Operator),
            (r'\b(e|pi|div|mod|rem)\b', Operator),
            # Other arithmetic functors
            (r'\b\*\*\b', Operator),
            # DCG rules
            (r'-->', Operator),
            # Control constructs
            (r'([!;]|->)', Operator),
            # Logic and control
            (r'\\+', Operator),
            # Mode operators
            (r'[?@]', Operator),
            # Existential quantifier
            (r'\^', Operator),
            # Punctuation
            (r'[()\[\],.|]', Text),
            # Atoms
            (r"[a-z][a-zA-Z0-9_]*", Text),
            (r"'", String, 'quoted_atom'),
            # Double-quoted terms
            (r'"', String, 'double_quoted_term'),
        ],

        'quoted_atom': [
            (r"''", String),
            (r"'", String, '#pop'),
            (r'\\([\\abfnrtv"\']|(x[a-fA-F0-9]+|[0-7]+)\\)', String.Escape),
            (r"[^\\'\n]+", String),
            (r'\\', String),
        ],

        'double_quoted_term': [
            (r'""', String),
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|(x[a-fA-F0-9]+|[0-7]+)\\)', String.Escape),
            (r'[^\\"\n]+', String),
            (r'\\', String),
        ],

        'directive': [
            # Conditional compilation directives
            (r'(el)?if(?=[(])', Keyword, 'root'),
            (r'(e(lse|ndif))(?=[.])', Keyword, 'root'),
            # Entity directives
            (r'(category|object|protocol)(?=[(])', Keyword, 'entityrelations'),
            (r'(end_(category|object|protocol))(?=[.])', Keyword, 'root'),
            # Predicate scope directives
            (r'(public|protected|private)(?=[(])', Keyword, 'root'),
            # Other directives
            (r'e(n(coding|sure_loaded)|xport)(?=[(])', Keyword, 'root'),
            (r'in(clude|itialization|fo)(?=[(])', Keyword, 'root'),
            (r'(built_in|dynamic|synchronized|threaded)(?=[.])', Keyword, 'root'),
            (r'(alias|d(ynamic|iscontiguous)|m(eta_(non_terminal|predicate)|ode|ultifile)|s(et_(logtalk|prolog)_flag|ynchronized))(?=[(])', Keyword, 'root'),
            (r'op(?=[(])', Keyword, 'root'),
            (r'(c(alls|oinductive)|module|reexport|use(s|_module))(?=[(])', Keyword, 'root'),
            (r'[a-z][a-zA-Z0-9_]*(?=[(])', Text, 'root'),
            (r'[a-z][a-zA-Z0-9_]*(?=[.])', Text, 'root'),
        ],

        'entityrelations': [
            (r'(complements|extends|i(nstantiates|mp(lements|orts))|specializes)(?=[(])', Keyword),
            # Numbers
            (r"0'[\\]?.", Number),
            (r'0b[01]+', Number.Bin),
            (r'0o[0-7]+', Number.Oct),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'\d+\.?\d*((e|E)(\+|-)?\d+)?', Number),
            # Variables
            (r'([A-Z_][a-zA-Z0-9_]*)', Name.Variable),
            # Atoms
            (r"[a-z][a-zA-Z0-9_]*", Text),
            (r"'", String, 'quoted_atom'),
            # Double-quoted terms
            (r'"', String, 'double_quoted_term'),
            # End of entity-opening directive
            (r'([)]\.)', Text, 'root'),
            # Scope operator
            (r'(::)', Operator),
            # Punctuation
            (r'[()\[\],.|]', Text),
            # Comments
            (r'%.*?\n', Comment),
            (r'/\*(.|\n)*?\*/', Comment),
            # Whitespace
            (r'\n', Text),
            (r'\s+', Text),
        ]
    }

    def analyse_text(text):
        if ':- object(' in text:
            return 1.0
        elif ':- protocol(' in text:
            return 1.0
        elif ':- category(' in text:
            return 1.0
        elif re.search(r'^:-\s[a-z]', text, re.M):
            return 0.9
        else:
            return 0.0

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\resolvelib\resolver.py ===
import contextlib
import functools
import logging
import os
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, cast

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.resolvelib import BaseReporter, ResolutionImpossible
from pip._vendor.resolvelib import Resolver as RLResolver
from pip._vendor.resolvelib.structs import DirectedGraph

from pip._internal.cache import WheelCache
from pip._internal.index.package_finder import PackageFinder
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.constructors import install_req_extend_extras
from pip._internal.req.req_install import InstallRequirement
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.base import BaseResolver, InstallRequirementProvider
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.reporter import (
    PipDebuggingReporter,
    PipReporter,
)
from pip._internal.utils.packaging import get_requirement

from .base import Candidate, Requirement
from .factory import Factory

if TYPE_CHECKING:
    from pip._vendor.resolvelib.resolvers import Result as RLResult

    Result = RLResult[Requirement, Candidate, str]


logger = logging.getLogger(__name__)


class Resolver(BaseResolver):
    _allowed_strategies = {"eager", "only-if-needed", "to-satisfy-only"}

    def __init__(
        self,
        preparer: RequirementPreparer,
        finder: PackageFinder,
        wheel_cache: Optional[WheelCache],
        make_install_req: InstallRequirementProvider,
        use_user_site: bool,
        ignore_dependencies: bool,
        ignore_installed: bool,
        ignore_requires_python: bool,
        force_reinstall: bool,
        upgrade_strategy: str,
        py_version_info: Optional[Tuple[int, ...]] = None,
    ):
        super().__init__()
        assert upgrade_strategy in self._allowed_strategies

        self.factory = Factory(
            finder=finder,
            preparer=preparer,
            make_install_req=make_install_req,
            wheel_cache=wheel_cache,
            use_user_site=use_user_site,
            force_reinstall=force_reinstall,
            ignore_installed=ignore_installed,
            ignore_requires_python=ignore_requires_python,
            py_version_info=py_version_info,
        )
        self.ignore_dependencies = ignore_dependencies
        self.upgrade_strategy = upgrade_strategy
        self._result: Optional[Result] = None

    def resolve(
        self, root_reqs: List[InstallRequirement], check_supported_wheels: bool
    ) -> RequirementSet:
        collected = self.factory.collect_root_requirements(root_reqs)
        provider = PipProvider(
            factory=self.factory,
            constraints=collected.constraints,
            ignore_dependencies=self.ignore_dependencies,
            upgrade_strategy=self.upgrade_strategy,
            user_requested=collected.user_requested,
        )
        if "PIP_RESOLVER_DEBUG" in os.environ:
            reporter: BaseReporter = PipDebuggingReporter()
        else:
            reporter = PipReporter()
        resolver: RLResolver[Requirement, Candidate, str] = RLResolver(
            provider,
            reporter,
        )

        try:
            limit_how_complex_resolution_can_be = 200000
            result = self._result = resolver.resolve(
                collected.requirements, max_rounds=limit_how_complex_resolution_can_be
            )

        except ResolutionImpossible as e:
            error = self.factory.get_installation_error(
                cast("ResolutionImpossible[Requirement, Candidate]", e),
                collected.constraints,
            )
            raise error from e

        req_set = RequirementSet(check_supported_wheels=check_supported_wheels)
        # process candidates with extras last to ensure their base equivalent is
        # already in the req_set if appropriate.
        # Python's sort is stable so using a binary key function keeps relative order
        # within both subsets.
        for candidate in sorted(
            result.mapping.values(), key=lambda c: c.name != c.project_name
        ):
            ireq = candidate.get_install_requirement()
            if ireq is None:
                if candidate.name != candidate.project_name:
                    # extend existing req's extras
                    with contextlib.suppress(KeyError):
                        req = req_set.get_requirement(candidate.project_name)
                        req_set.add_named_requirement(
                            install_req_extend_extras(
                                req, get_requirement(candidate.name).extras
                            )
                        )
                continue

            # Check if there is already an installation under the same name,
            # and set a flag for later stages to uninstall it, if needed.
            installed_dist = self.factory.get_dist_to_uninstall(candidate)
            if installed_dist is None:
                # There is no existing installation -- nothing to uninstall.
                ireq.should_reinstall = False
            elif self.factory.force_reinstall:
                # The --force-reinstall flag is set -- reinstall.
                ireq.should_reinstall = True
            elif installed_dist.version != candidate.version:
                # The installation is different in version -- reinstall.
                ireq.should_reinstall = True
            elif candidate.is_editable or installed_dist.editable:
                # The incoming distribution is editable, or different in
                # editable-ness to installation -- reinstall.
                ireq.should_reinstall = True
            elif candidate.source_link and candidate.source_link.is_file:
                # The incoming distribution is under file://
                if candidate.source_link.is_wheel:
                    # is a local wheel -- do nothing.
                    logger.info(
                        "%s is already installed with the same version as the "
                        "provided wheel. Use --force-reinstall to force an "
                        "installation of the wheel.",
                        ireq.name,
                    )
                    continue

                # is a local sdist or path -- reinstall
                ireq.should_reinstall = True
            else:
                continue

            link = candidate.source_link
            if link and link.is_yanked:
                # The reason can contain non-ASCII characters, Unicode
                # is required for Python 2.
                msg = (
                    "The candidate selected for download or install is a "
                    "yanked version: {name!r} candidate (version {version} "
                    "at {link})\nReason for being yanked: {reason}"
                ).format(
                    name=candidate.name,
                    version=candidate.version,
                    link=link,
                    reason=link.yanked_reason or "<none given>",
                )
                logger.warning(msg)

            req_set.add_named_requirement(ireq)

        reqs = req_set.all_requirements
        self.factory.preparer.prepare_linked_requirements_more(reqs)
        for req in reqs:
            req.prepared = True
            req.needs_more_preparation = False
        return req_set

    def get_installation_order(
        self, req_set: RequirementSet
    ) -> List[InstallRequirement]:
        """Get order for installation of requirements in RequirementSet.

        The returned list contains a requirement before another that depends on
        it. This helps ensure that the environment is kept consistent as they
        get installed one-by-one.

        The current implementation creates a topological ordering of the
        dependency graph, giving more weight to packages with less
        or no dependencies, while breaking any cycles in the graph at
        arbitrary points. We make no guarantees about where the cycle
        would be broken, other than it *would* be broken.
        """
        assert self._result is not None, "must call resolve() first"

        if not req_set.requirements:
            # Nothing is left to install, so we do not need an order.
            return []

        graph = self._result.graph
        weights = get_topological_weights(graph, set(req_set.requirements.keys()))

        sorted_items = sorted(
            req_set.requirements.items(),
            key=functools.partial(_req_set_item_sorter, weights=weights),
            reverse=True,
        )
        return [ireq for _, ireq in sorted_items]


def get_topological_weights(
    graph: "DirectedGraph[Optional[str]]", requirement_keys: Set[str]
) -> Dict[Optional[str], int]:
    """Assign weights to each node based on how "deep" they are.

    This implementation may change at any point in the future without prior
    notice.

    We first simplify the dependency graph by pruning any leaves and giving them
    the highest weight: a package without any dependencies should be installed
    first. This is done again and again in the same way, giving ever less weight
    to the newly found leaves. The loop stops when no leaves are left: all
    remaining packages have at least one dependency left in the graph.

    Then we continue with the remaining graph, by taking the length for the
    longest path to any node from root, ignoring any paths that contain a single
    node twice (i.e. cycles). This is done through a depth-first search through
    the graph, while keeping track of the path to the node.

    Cycles in the graph result would result in node being revisited while also
    being on its own path. In this case, take no action. This helps ensure we
    don't get stuck in a cycle.

    When assigning weight, the longer path (i.e. larger length) is preferred.

    We are only interested in the weights of packages that are in the
    requirement_keys.
    """
    path: Set[Optional[str]] = set()
    weights: Dict[Optional[str], int] = {}

    def visit(node: Optional[str]) -> None:
        if node in path:
            # We hit a cycle, so we'll break it here.
            return

        # Time to visit the children!
        path.add(node)
        for child in graph.iter_children(node):
            visit(child)
        path.remove(node)

        if node not in requirement_keys:
            return

        last_known_parent_count = weights.get(node, 0)
        weights[node] = max(last_known_parent_count, len(path))

    # Simplify the graph, pruning leaves that have no dependencies.
    # This is needed for large graphs (say over 200 packages) because the
    # `visit` function is exponentially slower then, taking minutes.
    # See https://github.com/pypa/pip/issues/10557
    # We will loop until we explicitly break the loop.
    while True:
        leaves = set()
        for key in graph:
            if key is None:
                continue
            for _child in graph.iter_children(key):
                # This means we have at least one child
                break
            else:
                # No child.
                leaves.add(key)
        if not leaves:
            # We are done simplifying.
            break
        # Calculate the weight for the leaves.
        weight = len(graph) - 1
        for leaf in leaves:
            if leaf not in requirement_keys:
                continue
            weights[leaf] = weight
        # Remove the leaves from the graph, making it simpler.
        for leaf in leaves:
            graph.remove(leaf)

    # Visit the remaining graph.
    # `None` is guaranteed to be the root node by resolvelib.
    visit(None)

    # Sanity check: all requirement keys should be in the weights,
    # and no other keys should be in the weights.
    difference = set(weights.keys()).difference(requirement_keys)
    assert not difference, difference

    return weights


def _req_set_item_sorter(
    item: Tuple[str, InstallRequirement],
    weights: Dict[Optional[str], int],
) -> Tuple[int, str]:
    """Key function used to sort install requirements for installation.

    Based on the "weight" mapping calculated in ``get_installation_order()``.
    The canonical package name is returned as the second member as a tie-
    breaker to ensure the result is predictable, which is useful in tests.
    """
    name = canonicalize_name(item[0])
    return weights[name], name

# === NexusCore/openenv\Lib\site-packages\comm\base_comm.py ===
"""Default classes for Comm and CommManager, for usage in IPython.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import contextlib
import logging
import typing as t
import uuid

from traitlets.utils.importstring import import_item

import comm

if t.TYPE_CHECKING:
    from zmq.eventloop.zmqstream import ZMQStream

logger = logging.getLogger("Comm")

MessageType = t.Dict[str, t.Any]
MaybeDict = t.Optional[t.Dict[str, t.Any]]
BuffersType = t.Optional[t.List[bytes]]
CommCallback = t.Callable[[MessageType], None]
CommTargetCallback = t.Callable[["BaseComm", MessageType], None]


class BaseComm:
    """Class for communicating between a Frontend and a Kernel

    Must be subclassed with a publish_msg method implementation which
    sends comm messages through the iopub channel.
    """

    def __init__(
        self,
        target_name: str = "comm",
        data: MaybeDict = None,
        metadata: MaybeDict = None,
        buffers: BuffersType = None,
        comm_id: str | None = None,
        primary: bool = True,
        target_module: str | None = None,
        topic: bytes | None = None,
        _open_data: MaybeDict = None,
        _close_data: MaybeDict = None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(**kwargs)

        self.comm_id = comm_id if comm_id else uuid.uuid4().hex
        self.primary = primary
        self.target_name = target_name
        self.target_module = target_module
        self.topic = topic if topic else ("comm-%s" % self.comm_id).encode("ascii")

        self._open_data = _open_data if _open_data else {}
        self._close_data = _close_data if _close_data else {}

        self._msg_callback: CommCallback | None = None
        self._close_callback: CommCallback | None = None

        self._closed = True

        if self.primary:
            # I am primary, open my peer.
            self.open(data=data, metadata=metadata, buffers=buffers)
        else:
            self._closed = False

    def publish_msg(
        self,
        msg_type: str,  # noqa: ARG002
        data: MaybeDict = None,  # noqa: ARG002
        metadata: MaybeDict = None,  # noqa: ARG002
        buffers: BuffersType = None,  # noqa: ARG002
        **keys: t.Any,  # noqa: ARG002
    ) -> None:
        msg = "publish_msg Comm method is not implemented"
        raise NotImplementedError(msg)

    def __del__(self) -> None:
        """trigger close on gc"""
        with contextlib.suppress(Exception):
            # any number of things can have gone horribly wrong
            # when called during interpreter teardown
            self.close(deleting=True)

    # publishing messages

    def open(
        self, data: MaybeDict = None, metadata: MaybeDict = None, buffers: BuffersType = None
    ) -> None:
        """Open the frontend-side version of this comm"""

        if data is None:
            data = self._open_data
        comm_manager = comm.get_comm_manager()
        if comm_manager is None:
            msg = "Comms cannot be opened without a comm_manager."  # type:ignore[unreachable]
            raise RuntimeError(msg)

        comm_manager.register_comm(self)
        try:
            self.publish_msg(
                "comm_open",
                data=data,
                metadata=metadata,
                buffers=buffers,
                target_name=self.target_name,
                target_module=self.target_module,
            )
            self._closed = False
        except Exception:
            comm_manager.unregister_comm(self)
            raise

    def close(
        self,
        data: MaybeDict = None,
        metadata: MaybeDict = None,
        buffers: BuffersType = None,
        deleting: bool = False,
    ) -> None:
        """Close the frontend-side version of this comm"""
        if self._closed:
            # only close once
            return
        self._closed = True
        if data is None:
            data = self._close_data
        self.publish_msg(
            "comm_close",
            data=data,
            metadata=metadata,
            buffers=buffers,
        )
        if not deleting:
            # If deleting, the comm can't be registered
            comm.get_comm_manager().unregister_comm(self)

    def send(
        self, data: MaybeDict = None, metadata: MaybeDict = None, buffers: BuffersType = None
    ) -> None:
        """Send a message to the frontend-side version of this comm"""
        self.publish_msg(
            "comm_msg",
            data=data,
            metadata=metadata,
            buffers=buffers,
        )

    # registering callbacks

    def on_close(self, callback: CommCallback | None) -> None:
        """Register a callback for comm_close

        Will be called with the `data` of the close message.

        Call `on_close(None)` to disable an existing callback.
        """
        self._close_callback = callback

    def on_msg(self, callback: CommCallback | None) -> None:
        """Register a callback for comm_msg

        Will be called with the `data` of any comm_msg messages.

        Call `on_msg(None)` to disable an existing callback.
        """
        self._msg_callback = callback

    # handling of incoming messages

    def handle_close(self, msg: MessageType) -> None:
        """Handle a comm_close message"""
        logger.debug("handle_close[%s](%s)", self.comm_id, msg)
        if self._close_callback:
            self._close_callback(msg)

    def handle_msg(self, msg: MessageType) -> None:
        """Handle a comm_msg message"""
        logger.debug("handle_msg[%s](%s)", self.comm_id, msg)
        if self._msg_callback:
            from IPython import get_ipython

            shell = get_ipython()
            if shell:
                shell.events.trigger("pre_execute")
            self._msg_callback(msg)
            if shell:
                shell.events.trigger("post_execute")


class CommManager:
    """Default CommManager singleton implementation for Comms in the Kernel"""

    # Public APIs

    def __init__(self) -> None:
        self.comms: dict[str, BaseComm] = {}
        self.targets: dict[str, CommTargetCallback] = {}

    def register_target(self, target_name: str, f: CommTargetCallback | str) -> None:
        """Register a callable f for a given target name

        f will be called with two arguments when a comm_open message is received with `target`:

        - the Comm instance
        - the `comm_open` message itself.

        f can be a Python callable or an import string for one.
        """
        if isinstance(f, str):
            f = import_item(f)

        self.targets[target_name] = t.cast(CommTargetCallback, f)

    def unregister_target(self, target_name: str, f: CommTargetCallback) -> CommTargetCallback:  # noqa: ARG002
        """Unregister a callable registered with register_target"""
        return self.targets.pop(target_name)

    def register_comm(self, comm: BaseComm) -> str:
        """Register a new comm"""
        comm_id = comm.comm_id
        self.comms[comm_id] = comm
        return comm_id

    def unregister_comm(self, comm: BaseComm) -> None:
        """Unregister a comm, and close its counterpart"""
        # unlike get_comm, this should raise a KeyError
        comm = self.comms.pop(comm.comm_id)

    def get_comm(self, comm_id: str) -> BaseComm | None:
        """Get a comm with a particular id

        Returns the comm if found, otherwise None.

        This will not raise an error,
        it will log messages if the comm cannot be found.
        """
        try:
            return self.comms[comm_id]
        except KeyError:
            logger.warning("No such comm: %s", comm_id)
            if logger.isEnabledFor(logging.DEBUG):
                # don't create the list of keys if debug messages aren't enabled
                logger.debug("Current comms: %s", list(self.comms.keys()))
            return None

    # Message handlers

    def comm_open(self, stream: ZMQStream, ident: str, msg: MessageType) -> None:  # noqa: ARG002
        """Handler for comm_open messages"""
        from comm import create_comm

        content = msg["content"]
        comm_id = content["comm_id"]
        target_name = content["target_name"]
        f = self.targets.get(target_name, None)
        comm = create_comm(
            comm_id=comm_id,
            primary=False,
            target_name=target_name,
        )
        self.register_comm(comm)
        if f is None:
            logger.error("No such comm target registered: %s", target_name)
        else:
            try:
                f(comm, msg)
                return
            except Exception:
                logger.error("Exception opening comm with target: %s", target_name, exc_info=True)

        # Failure.
        try:
            comm.close()
        except Exception:
            logger.error(
                """Could not close comm during `comm_open` failure
                clean-up.  The comm may not have been opened yet.""",
                exc_info=True,
            )

    def comm_msg(self, stream: ZMQStream, ident: str, msg: MessageType) -> None:  # noqa: ARG002
        """Handler for comm_msg messages"""
        content = msg["content"]
        comm_id = content["comm_id"]
        comm = self.get_comm(comm_id)
        if comm is None:
            return

        try:
            comm.handle_msg(msg)
        except Exception:
            logger.error("Exception in comm_msg for %s", comm_id, exc_info=True)

    def comm_close(self, stream: ZMQStream, ident: str, msg: MessageType) -> None:  # noqa: ARG002
        """Handler for comm_close messages"""
        content = msg["content"]
        comm_id = content["comm_id"]
        comm = self.get_comm(comm_id)
        if comm is None:
            return

        self.comms[comm_id]._closed = True
        del self.comms[comm_id]

        try:
            comm.handle_close(msg)
        except Exception:
            logger.error("Exception in comm_close for %s", comm_id, exc_info=True)


__all__ = ["CommManager", "BaseComm"]

# === NexusCore/openenv\Lib\site-packages\googleapiclient\schema.py ===
# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Schema processing for discovery based APIs

Schemas holds an APIs discovery schemas. It can return those schema as
deserialized JSON objects, or pretty print them as prototype objects that
conform to the schema.

For example, given the schema:

 schema = \"\"\"{
   "Foo": {
    "type": "object",
    "properties": {
     "etag": {
      "type": "string",
      "description": "ETag of the collection."
     },
     "kind": {
      "type": "string",
      "description": "Type of the collection ('calendar#acl').",
      "default": "calendar#acl"
     },
     "nextPageToken": {
      "type": "string",
      "description": "Token used to access the next
         page of this result. Omitted if no further results are available."
     }
    }
   }
 }\"\"\"

 s = Schemas(schema)
 print s.prettyPrintByName('Foo')

 Produces the following output:

  {
   "nextPageToken": "A String", # Token used to access the
       # next page of this result. Omitted if no further results are available.
   "kind": "A String", # Type of the collection ('calendar#acl').
   "etag": "A String", # ETag of the collection.
  },

The constructor takes a discovery document in which to look up named schema.
"""
from __future__ import absolute_import

# TODO(jcgregorio) support format, enum, minimum, maximum

__author__ = "jcgregorio@google.com (Joe Gregorio)"


from collections import OrderedDict

from googleapiclient import _helpers as util


class Schemas(object):
    """Schemas for an API."""

    def __init__(self, discovery):
        """Constructor.

        Args:
          discovery: object, Deserialized discovery document from which we pull
            out the named schema.
        """
        self.schemas = discovery.get("schemas", {})

        # Cache of pretty printed schemas.
        self.pretty = {}

    @util.positional(2)
    def _prettyPrintByName(self, name, seen=None, dent=0):
        """Get pretty printed object prototype from the schema name.

        Args:
          name: string, Name of schema in the discovery document.
          seen: list of string, Names of schema already seen. Used to handle
            recursive definitions.

        Returns:
          string, A string that contains a prototype object with
            comments that conforms to the given schema.
        """
        if seen is None:
            seen = []

        if name in seen:
            # Do not fall into an infinite loop over recursive definitions.
            return "# Object with schema name: %s" % name
        seen.append(name)

        if name not in self.pretty:
            self.pretty[name] = _SchemaToStruct(
                self.schemas[name], seen, dent=dent
            ).to_str(self._prettyPrintByName)

        seen.pop()

        return self.pretty[name]

    def prettyPrintByName(self, name):
        """Get pretty printed object prototype from the schema name.

        Args:
          name: string, Name of schema in the discovery document.

        Returns:
          string, A string that contains a prototype object with
            comments that conforms to the given schema.
        """
        # Return with trailing comma and newline removed.
        return self._prettyPrintByName(name, seen=[], dent=0)[:-2]

    @util.positional(2)
    def _prettyPrintSchema(self, schema, seen=None, dent=0):
        """Get pretty printed object prototype of schema.

        Args:
          schema: object, Parsed JSON schema.
          seen: list of string, Names of schema already seen. Used to handle
            recursive definitions.

        Returns:
          string, A string that contains a prototype object with
            comments that conforms to the given schema.
        """
        if seen is None:
            seen = []

        return _SchemaToStruct(schema, seen, dent=dent).to_str(self._prettyPrintByName)

    def prettyPrintSchema(self, schema):
        """Get pretty printed object prototype of schema.

        Args:
          schema: object, Parsed JSON schema.

        Returns:
          string, A string that contains a prototype object with
            comments that conforms to the given schema.
        """
        # Return with trailing comma and newline removed.
        return self._prettyPrintSchema(schema, dent=0)[:-2]

    def get(self, name, default=None):
        """Get deserialized JSON schema from the schema name.

        Args:
          name: string, Schema name.
          default: object, return value if name not found.
        """
        return self.schemas.get(name, default)


class _SchemaToStruct(object):
    """Convert schema to a prototype object."""

    @util.positional(3)
    def __init__(self, schema, seen, dent=0):
        """Constructor.

        Args:
          schema: object, Parsed JSON schema.
          seen: list, List of names of schema already seen while parsing. Used to
            handle recursive definitions.
          dent: int, Initial indentation depth.
        """
        # The result of this parsing kept as list of strings.
        self.value = []

        # The final value of the parsing.
        self.string = None

        # The parsed JSON schema.
        self.schema = schema

        # Indentation level.
        self.dent = dent

        # Method that when called returns a prototype object for the schema with
        # the given name.
        self.from_cache = None

        # List of names of schema already seen while parsing.
        self.seen = seen

    def emit(self, text):
        """Add text as a line to the output.

        Args:
          text: string, Text to output.
        """
        self.value.extend(["  " * self.dent, text, "\n"])

    def emitBegin(self, text):
        """Add text to the output, but with no line terminator.

        Args:
          text: string, Text to output.
        """
        self.value.extend(["  " * self.dent, text])

    def emitEnd(self, text, comment):
        """Add text and comment to the output with line terminator.

        Args:
          text: string, Text to output.
          comment: string, Python comment.
        """
        if comment:
            divider = "\n" + "  " * (self.dent + 2) + "# "
            lines = comment.splitlines()
            lines = [x.rstrip() for x in lines]
            comment = divider.join(lines)
            self.value.extend([text, " # ", comment, "\n"])
        else:
            self.value.extend([text, "\n"])

    def indent(self):
        """Increase indentation level."""
        self.dent += 1

    def undent(self):
        """Decrease indentation level."""
        self.dent -= 1

    def _to_str_impl(self, schema):
        """Prototype object based on the schema, in Python code with comments.

        Args:
          schema: object, Parsed JSON schema file.

        Returns:
          Prototype object based on the schema, in Python code with comments.
        """
        stype = schema.get("type")
        if stype == "object":
            self.emitEnd("{", schema.get("description", ""))
            self.indent()
            if "properties" in schema:
                properties = schema.get("properties", {})
                sorted_properties = OrderedDict(sorted(properties.items()))
                for pname, pschema in sorted_properties.items():
                    self.emitBegin('"%s": ' % pname)
                    self._to_str_impl(pschema)
            elif "additionalProperties" in schema:
                self.emitBegin('"a_key": ')
                self._to_str_impl(schema["additionalProperties"])
            self.undent()
            self.emit("},")
        elif "$ref" in schema:
            schemaName = schema["$ref"]
            description = schema.get("description", "")
            s = self.from_cache(schemaName, seen=self.seen)
            parts = s.splitlines()
            self.emitEnd(parts[0], description)
            for line in parts[1:]:
                self.emit(line.rstrip())
        elif stype == "boolean":
            value = schema.get("default", "True or False")
            self.emitEnd("%s," % str(value), schema.get("description", ""))
        elif stype == "string":
            value = schema.get("default", "A String")
            self.emitEnd('"%s",' % str(value), schema.get("description", ""))
        elif stype == "integer":
            value = schema.get("default", "42")
            self.emitEnd("%s," % str(value), schema.get("description", ""))
        elif stype == "number":
            value = schema.get("default", "3.14")
            self.emitEnd("%s," % str(value), schema.get("description", ""))
        elif stype == "null":
            self.emitEnd("None,", schema.get("description", ""))
        elif stype == "any":
            self.emitEnd('"",', schema.get("description", ""))
        elif stype == "array":
            self.emitEnd("[", schema.get("description"))
            self.indent()
            self.emitBegin("")
            self._to_str_impl(schema["items"])
            self.undent()
            self.emit("],")
        else:
            self.emit("Unknown type! %s" % stype)
            self.emitEnd("", "")

        self.string = "".join(self.value)
        return self.string

    def to_str(self, from_cache):
        """Prototype object based on the schema, in Python code with comments.

        Args:
          from_cache: callable(name, seen), Callable that retrieves an object
             prototype for a schema with the given name. Seen is a list of schema
             names already seen as we recursively descend the schema definition.

        Returns:
          Prototype object based on the schema, in Python code with comments.
          The lines of the code will all be properly indented.
        """
        self.from_cache = from_cache
        return self._to_str_impl(self.schema)

# === NexusCore/openenv\Lib\site-packages\tqdm\notebook.py ===
"""
IPython/Jupyter Notebook progressbar decorator for iterators.
Includes a default `range` iterator printing to `stderr`.

Usage:
>>> from tqdm.notebook import trange, tqdm
>>> for i in trange(10):
...     ...
"""
# import compatibility functions and utilities
import re
import sys
from html import escape
from weakref import proxy

# to inherit from the tqdm class
from .std import tqdm as std_tqdm

if True:  # pragma: no cover
    # import IPython/Jupyter base widget and display utilities
    IPY = 0
    try:  # IPython 4.x
        import ipywidgets
        IPY = 4
    except ImportError:  # IPython 3.x / 2.x
        IPY = 32
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore', message=".*The `IPython.html` package has been deprecated.*")
            try:
                import IPython.html.widgets as ipywidgets  # NOQA: F401
            except ImportError:
                pass

    try:  # IPython 4.x / 3.x
        if IPY == 32:
            from IPython.html.widgets import HTML
            from IPython.html.widgets import FloatProgress as IProgress
            from IPython.html.widgets import HBox
            IPY = 3
        else:
            from ipywidgets import HTML
            from ipywidgets import FloatProgress as IProgress
            from ipywidgets import HBox
    except ImportError:
        try:  # IPython 2.x
            from IPython.html.widgets import HTML
            from IPython.html.widgets import ContainerWidget as HBox
            from IPython.html.widgets import FloatProgressWidget as IProgress
            IPY = 2
        except ImportError:
            IPY = 0
            IProgress = None
            HBox = object

    try:
        from IPython.display import display  # , clear_output
    except ImportError:
        pass

__author__ = {"github.com/": ["lrq3000", "casperdcl", "alexanderkuk"]}
__all__ = ['tqdm_notebook', 'tnrange', 'tqdm', 'trange']
WARN_NOIPYW = ("IProgress not found. Please update jupyter and ipywidgets."
               " See https://ipywidgets.readthedocs.io/en/stable"
               "/user_install.html")


class TqdmHBox(HBox):
    """`ipywidgets.HBox` with a pretty representation"""
    def _json_(self, pretty=None):
        pbar = getattr(self, 'pbar', None)
        if pbar is None:
            return {}
        d = pbar.format_dict
        if pretty is not None:
            d["ascii"] = not pretty
        return d

    def __repr__(self, pretty=False):
        pbar = getattr(self, 'pbar', None)
        if pbar is None:
            return super().__repr__()
        return pbar.format_meter(**self._json_(pretty))

    def _repr_pretty_(self, pp, *_, **__):
        pp.text(self.__repr__(True))


class tqdm_notebook(std_tqdm):
    """
    Experimental IPython/Jupyter Notebook widget using tqdm!
    """
    @staticmethod
    def status_printer(_, total=None, desc=None, ncols=None):
        """
        Manage the printing of an IPython/Jupyter Notebook progress bar widget.
        """
        # Fallback to text bar if there's no total
        # DEPRECATED: replaced with an 'info' style bar
        # if not total:
        #    return super(tqdm_notebook, tqdm_notebook).status_printer(file)

        # fp = file

        # Prepare IPython progress bar
        if IProgress is None:  # #187 #451 #558 #872
            raise ImportError(WARN_NOIPYW)
        if total:
            pbar = IProgress(min=0, max=total)
        else:  # No total? Show info style bar with no progress tqdm status
            pbar = IProgress(min=0, max=1)
            pbar.value = 1
            pbar.bar_style = 'info'
            if ncols is None:
                pbar.layout.width = "20px"

        ltext = HTML()
        rtext = HTML()
        if desc:
            ltext.value = desc
        container = TqdmHBox(children=[ltext, pbar, rtext])
        # Prepare layout
        if ncols is not None:  # use default style of ipywidgets
            # ncols could be 100, "100px", "100%"
            ncols = str(ncols)  # ipywidgets only accepts string
            try:
                if int(ncols) > 0:  # isnumeric and positive
                    ncols += 'px'
            except ValueError:
                pass
            pbar.layout.flex = '2'
            container.layout.width = ncols
            container.layout.display = 'inline-flex'
            container.layout.flex_flow = 'row wrap'

        return container

    def display(self, msg=None, pos=None,
                # additional signals
                close=False, bar_style=None, check_delay=True):
        # Note: contrary to native tqdm, msg='' does NOT clear bar
        # goal is to keep all infos if error happens so user knows
        # at which iteration the loop failed.

        # Clear previous output (really necessary?)
        # clear_output(wait=1)

        if not msg and not close:
            d = self.format_dict
            # remove {bar}
            d['bar_format'] = (d['bar_format'] or "{l_bar}<bar/>{r_bar}").replace(
                "{bar}", "<bar/>")
            msg = self.format_meter(**d)

        ltext, pbar, rtext = self.container.children
        pbar.value = self.n

        if msg:
            msg = msg.replace(' ', u'\u2007')  # fix html space padding
            # html escape special characters (like '&')
            if '<bar/>' in msg:
                left, right = map(escape, re.split(r'\|?<bar/>\|?', msg, maxsplit=1))
            else:
                left, right = '', escape(msg)

            # Update description
            ltext.value = left
            # never clear the bar (signal: msg='')
            if right:
                rtext.value = right

        # Change bar style
        if bar_style:
            # Hack-ish way to avoid the danger bar_style being overridden by
            # success because the bar gets closed after the error...
            if pbar.bar_style != 'danger' or bar_style != 'success':
                pbar.bar_style = bar_style

        # Special signal to close the bar
        if close and pbar.bar_style != 'danger':  # hide only if no error
            try:
                self.container.close()
            except AttributeError:
                self.container.visible = False
            self.container.layout.visibility = 'hidden'  # IPYW>=8

        if check_delay and self.delay > 0 and not self.displayed:
            display(self.container)
            self.displayed = True

    @property
    def colour(self):
        if hasattr(self, 'container'):
            return self.container.children[-2].style.bar_color

    @colour.setter
    def colour(self, bar_color):
        if hasattr(self, 'container'):
            self.container.children[-2].style.bar_color = bar_color

    def __init__(self, *args, **kwargs):
        """
        Supports the usual `tqdm.tqdm` parameters as well as those listed below.

        Parameters
        ----------
        display  : Whether to call `display(self.container)` immediately
            [default: True].
        """
        kwargs = kwargs.copy()
        # Setup default output
        file_kwarg = kwargs.get('file', sys.stderr)
        if file_kwarg is sys.stderr or file_kwarg is None:
            kwargs['file'] = sys.stdout  # avoid the red block in IPython

        # Initialize parent class + avoid printing by using gui=True
        kwargs['gui'] = True
        # convert disable = None to False
        kwargs['disable'] = bool(kwargs.get('disable', False))
        colour = kwargs.pop('colour', None)
        display_here = kwargs.pop('display', True)
        super().__init__(*args, **kwargs)
        if self.disable or not kwargs['gui']:
            self.disp = lambda *_, **__: None
            return

        # Get bar width
        self.ncols = '100%' if self.dynamic_ncols else kwargs.get("ncols", None)

        # Replace with IPython progress bar display (with correct total)
        unit_scale = 1 if self.unit_scale is True else self.unit_scale or 1
        total = self.total * unit_scale if self.total else self.total
        self.container = self.status_printer(self.fp, total, self.desc, self.ncols)
        self.container.pbar = proxy(self)
        self.displayed = False
        if display_here and self.delay <= 0:
            display(self.container)
            self.displayed = True
        self.disp = self.display
        self.colour = colour

        # Print initial bar state
        if not self.disable:
            self.display(check_delay=False)

    def __iter__(self):
        try:
            it = super().__iter__()
            for obj in it:
                # return super(tqdm...) will not catch exception
                yield obj
        # NB: except ... [ as ...] breaks IPython async KeyboardInterrupt
        except:  # NOQA
            self.disp(bar_style='danger')
            raise
        # NB: don't `finally: close()`
        # since this could be a shared bar which the user will `reset()`

    def update(self, n=1):
        try:
            return super().update(n=n)
        # NB: except ... [ as ...] breaks IPython async KeyboardInterrupt
        except:  # NOQA
            # cannot catch KeyboardInterrupt when using manual tqdm
            # as the interrupt will most likely happen on another statement
            self.disp(bar_style='danger')
            raise
        # NB: don't `finally: close()`
        # since this could be a shared bar which the user will `reset()`

    def close(self):
        if self.disable:
            return
        super().close()
        # Try to detect if there was an error or KeyboardInterrupt
        # in manual mode: if n < total, things probably got wrong
        if self.total and self.n < self.total:
            self.disp(bar_style='danger', check_delay=False)
        else:
            if self.leave:
                self.disp(bar_style='success', check_delay=False)
            else:
                self.disp(close=True, check_delay=False)

    def clear(self, *_, **__):
        pass

    def reset(self, total=None):
        """
        Resets to 0 iterations for repeated use.

        Consider combining with `leave=True`.

        Parameters
        ----------
        total  : int or float, optional. Total to use for the new bar.
        """
        if self.disable:
            return super().reset(total=total)
        _, pbar, _ = self.container.children
        pbar.bar_style = ''
        if total is not None:
            pbar.max = total
            if not self.total and self.ncols is None:  # no longer unknown total
                pbar.layout.width = None  # reset width
        return super().reset(total=total)


def tnrange(*args, **kwargs):
    """Shortcut for `tqdm.notebook.tqdm(range(*args), **kwargs)`."""
    return tqdm_notebook(range(*args), **kwargs)


# Aliases
tqdm = tqdm_notebook
trange = tnrange

# === NexusCore/openenv\Lib\site-packages\anyio\streams\memory.py ===
from __future__ import annotations

import warnings
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from types import TracebackType
from typing import Generic, NamedTuple, TypeVar

from .. import (
    BrokenResourceError,
    ClosedResourceError,
    EndOfStream,
    WouldBlock,
)
from .._core._testing import TaskInfo, get_current_task
from ..abc import Event, ObjectReceiveStream, ObjectSendStream
from ..lowlevel import checkpoint

T_Item = TypeVar("T_Item")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)


class MemoryObjectStreamStatistics(NamedTuple):
    current_buffer_used: int  #: number of items stored in the buffer
    #: maximum number of items that can be stored on this stream (or :data:`math.inf`)
    max_buffer_size: float
    open_send_streams: int  #: number of unclosed clones of the send stream
    open_receive_streams: int  #: number of unclosed clones of the receive stream
    #: number of tasks blocked on :meth:`MemoryObjectSendStream.send`
    tasks_waiting_send: int
    #: number of tasks blocked on :meth:`MemoryObjectReceiveStream.receive`
    tasks_waiting_receive: int


@dataclass(eq=False)
class MemoryObjectItemReceiver(Generic[T_Item]):
    task_info: TaskInfo = field(init=False, default_factory=get_current_task)
    item: T_Item = field(init=False)

    def __repr__(self) -> str:
        # When item is not defined, we get following error with default __repr__:
        # AttributeError: 'MemoryObjectItemReceiver' object has no attribute 'item'
        item = getattr(self, "item", None)
        return f"{self.__class__.__name__}(task_info={self.task_info}, item={item!r})"


@dataclass(eq=False)
class MemoryObjectStreamState(Generic[T_Item]):
    max_buffer_size: float = field()
    buffer: deque[T_Item] = field(init=False, default_factory=deque)
    open_send_channels: int = field(init=False, default=0)
    open_receive_channels: int = field(init=False, default=0)
    waiting_receivers: OrderedDict[Event, MemoryObjectItemReceiver[T_Item]] = field(
        init=False, default_factory=OrderedDict
    )
    waiting_senders: OrderedDict[Event, T_Item] = field(
        init=False, default_factory=OrderedDict
    )

    def statistics(self) -> MemoryObjectStreamStatistics:
        return MemoryObjectStreamStatistics(
            len(self.buffer),
            self.max_buffer_size,
            self.open_send_channels,
            self.open_receive_channels,
            len(self.waiting_senders),
            len(self.waiting_receivers),
        )


@dataclass(eq=False)
class MemoryObjectReceiveStream(Generic[T_co], ObjectReceiveStream[T_co]):
    _state: MemoryObjectStreamState[T_co]
    _closed: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self._state.open_receive_channels += 1

    def receive_nowait(self) -> T_co:
        """
        Receive the next item if it can be done without waiting.

        :return: the received item
        :raises ~anyio.ClosedResourceError: if this send stream has been closed
        :raises ~anyio.EndOfStream: if the buffer is empty and this stream has been
            closed from the sending end
        :raises ~anyio.WouldBlock: if there are no items in the buffer and no tasks
            waiting to send

        """
        if self._closed:
            raise ClosedResourceError

        if self._state.waiting_senders:
            # Get the item from the next sender
            send_event, item = self._state.waiting_senders.popitem(last=False)
            self._state.buffer.append(item)
            send_event.set()

        if self._state.buffer:
            return self._state.buffer.popleft()
        elif not self._state.open_send_channels:
            raise EndOfStream

        raise WouldBlock

    async def receive(self) -> T_co:
        await checkpoint()
        try:
            return self.receive_nowait()
        except WouldBlock:
            # Add ourselves in the queue
            receive_event = Event()
            receiver = MemoryObjectItemReceiver[T_co]()
            self._state.waiting_receivers[receive_event] = receiver

            try:
                await receive_event.wait()
            finally:
                self._state.waiting_receivers.pop(receive_event, None)

            try:
                return receiver.item
            except AttributeError:
                raise EndOfStream from None

    def clone(self) -> MemoryObjectReceiveStream[T_co]:
        """
        Create a clone of this receive stream.

        Each clone can be closed separately. Only when all clones have been closed will
        the receiving end of the memory stream be considered closed by the sending ends.

        :return: the cloned stream

        """
        if self._closed:
            raise ClosedResourceError

        return MemoryObjectReceiveStream(_state=self._state)

    def close(self) -> None:
        """
        Close the stream.

        This works the exact same way as :meth:`aclose`, but is provided as a special
        case for the benefit of synchronous callbacks.

        """
        if not self._closed:
            self._closed = True
            self._state.open_receive_channels -= 1
            if self._state.open_receive_channels == 0:
                send_events = list(self._state.waiting_senders.keys())
                for event in send_events:
                    event.set()

    async def aclose(self) -> None:
        self.close()

    def statistics(self) -> MemoryObjectStreamStatistics:
        """
        Return statistics about the current state of this stream.

        .. versionadded:: 3.0
        """
        return self._state.statistics()

    def __enter__(self) -> MemoryObjectReceiveStream[T_co]:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def __del__(self) -> None:
        if not self._closed:
            warnings.warn(
                f"Unclosed <{self.__class__.__name__} at {id(self):x}>",
                ResourceWarning,
                source=self,
            )


@dataclass(eq=False)
class MemoryObjectSendStream(Generic[T_contra], ObjectSendStream[T_contra]):
    _state: MemoryObjectStreamState[T_contra]
    _closed: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self._state.open_send_channels += 1

    def send_nowait(self, item: T_contra) -> None:
        """
        Send an item immediately if it can be done without waiting.

        :param item: the item to send
        :raises ~anyio.ClosedResourceError: if this send stream has been closed
        :raises ~anyio.BrokenResourceError: if the stream has been closed from the
            receiving end
        :raises ~anyio.WouldBlock: if the buffer is full and there are no tasks waiting
            to receive

        """
        if self._closed:
            raise ClosedResourceError
        if not self._state.open_receive_channels:
            raise BrokenResourceError

        while self._state.waiting_receivers:
            receive_event, receiver = self._state.waiting_receivers.popitem(last=False)
            if not receiver.task_info.has_pending_cancellation():
                receiver.item = item
                receive_event.set()
                return

        if len(self._state.buffer) < self._state.max_buffer_size:
            self._state.buffer.append(item)
        else:
            raise WouldBlock

    async def send(self, item: T_contra) -> None:
        """
        Send an item to the stream.

        If the buffer is full, this method blocks until there is again room in the
        buffer or the item can be sent directly to a receiver.

        :param item: the item to send
        :raises ~anyio.ClosedResourceError: if this send stream has been closed
        :raises ~anyio.BrokenResourceError: if the stream has been closed from the
            receiving end

        """
        await checkpoint()
        try:
            self.send_nowait(item)
        except WouldBlock:
            # Wait until there's someone on the receiving end
            send_event = Event()
            self._state.waiting_senders[send_event] = item
            try:
                await send_event.wait()
            except BaseException:
                self._state.waiting_senders.pop(send_event, None)
                raise

            if send_event in self._state.waiting_senders:
                del self._state.waiting_senders[send_event]
                raise BrokenResourceError from None

    def clone(self) -> MemoryObjectSendStream[T_contra]:
        """
        Create a clone of this send stream.

        Each clone can be closed separately. Only when all clones have been closed will
        the sending end of the memory stream be considered closed by the receiving ends.

        :return: the cloned stream

        """
        if self._closed:
            raise ClosedResourceError

        return MemoryObjectSendStream(_state=self._state)

    def close(self) -> None:
        """
        Close the stream.

        This works the exact same way as :meth:`aclose`, but is provided as a special
        case for the benefit of synchronous callbacks.

        """
        if not self._closed:
            self._closed = True
            self._state.open_send_channels -= 1
            if self._state.open_send_channels == 0:
                receive_events = list(self._state.waiting_receivers.keys())
                self._state.waiting_receivers.clear()
                for event in receive_events:
                    event.set()

    async def aclose(self) -> None:
        self.close()

    def statistics(self) -> MemoryObjectStreamStatistics:
        """
        Return statistics about the current state of this stream.

        .. versionadded:: 3.0
        """
        return self._state.statistics()

    def __enter__(self) -> MemoryObjectSendStream[T_contra]:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def __del__(self) -> None:
        if not self._closed:
            warnings.warn(
                f"Unclosed <{self.__class__.__name__} at {id(self):x}>",
                ResourceWarning,
                source=self,
            )

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\literal_ai.py ===
#### What this does ####
# This file contains the LiteralAILogger class which is used to log steps to the LiteralAI observability platform.
import asyncio
import os
import uuid
from typing import List, Optional

import httpx

from litellm._logging import verbose_logger
from litellm.integrations.custom_batch_logger import CustomBatchLogger
from litellm.llms.custom_httpx.http_handler import (
    HTTPHandler,
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.types.utils import StandardLoggingPayload


class LiteralAILogger(CustomBatchLogger):
    def __init__(
        self,
        literalai_api_key=None,
        literalai_api_url="https://cloud.getliteral.ai",
        env=None,
        **kwargs,
    ):
        self.literalai_api_url = os.getenv("LITERAL_API_URL") or literalai_api_url
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": literalai_api_key or os.getenv("LITERAL_API_KEY"),
            "x-client-name": "litellm",
        }
        if env:
            self.headers["x-env"] = env
        self.async_httpx_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.LoggingCallback
        )
        self.sync_http_handler = HTTPHandler()
        batch_size = os.getenv("LITERAL_BATCH_SIZE", None)
        self.flush_lock = asyncio.Lock()
        super().__init__(
            **kwargs,
            flush_lock=self.flush_lock,
            batch_size=int(batch_size) if batch_size else None,
        )

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            verbose_logger.debug(
                "Literal AI Layer Logging - kwargs: %s, response_obj: %s",
                kwargs,
                response_obj,
            )
            data = self._prepare_log_data(kwargs, response_obj, start_time, end_time)
            self.log_queue.append(data)
            verbose_logger.debug(
                "Literal AI logging: queue length %s, batch size %s",
                len(self.log_queue),
                self.batch_size,
            )
            if len(self.log_queue) >= self.batch_size:
                self._send_batch()
        except Exception:
            verbose_logger.exception(
                "Literal AI Layer Error - error logging success event."
            )

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        verbose_logger.info("Literal AI Failure Event Logging!")
        try:
            data = self._prepare_log_data(kwargs, response_obj, start_time, end_time)
            self.log_queue.append(data)
            verbose_logger.debug(
                "Literal AI logging: queue length %s, batch size %s",
                len(self.log_queue),
                self.batch_size,
            )
            if len(self.log_queue) >= self.batch_size:
                self._send_batch()
        except Exception:
            verbose_logger.exception(
                "Literal AI Layer Error - error logging failure event."
            )

    def _send_batch(self):
        if not self.log_queue:
            return

        url = f"{self.literalai_api_url}/api/graphql"
        query = self._steps_query_builder(self.log_queue)
        variables = self._steps_variables_builder(self.log_queue)
        try:
            response = self.sync_http_handler.post(
                url=url,
                json={
                    "query": query,
                    "variables": variables,
                },
                headers=self.headers,
            )

            if response.status_code >= 300:
                verbose_logger.error(
                    f"Literal AI Error: {response.status_code} - {response.text}"
                )
            else:
                verbose_logger.debug(
                    f"Batch of {len(self.log_queue)} runs successfully created"
                )
        except Exception:
            verbose_logger.exception("Literal AI Layer Error")

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            verbose_logger.debug(
                "Literal AI Async Layer Logging - kwargs: %s, response_obj: %s",
                kwargs,
                response_obj,
            )
            data = self._prepare_log_data(kwargs, response_obj, start_time, end_time)
            self.log_queue.append(data)
            verbose_logger.debug(
                "Literal AI logging: queue length %s, batch size %s",
                len(self.log_queue),
                self.batch_size,
            )
            if len(self.log_queue) >= self.batch_size:
                await self.flush_queue()
        except Exception:
            verbose_logger.exception(
                "Literal AI Layer Error - error logging async success event."
            )

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        verbose_logger.info("Literal AI Failure Event Logging!")
        try:
            data = self._prepare_log_data(kwargs, response_obj, start_time, end_time)
            self.log_queue.append(data)
            verbose_logger.debug(
                "Literal AI logging: queue length %s, batch size %s",
                len(self.log_queue),
                self.batch_size,
            )
            if len(self.log_queue) >= self.batch_size:
                await self.flush_queue()
        except Exception:
            verbose_logger.exception(
                "Literal AI Layer Error - error logging async failure event."
            )

    async def async_send_batch(self):
        if not self.log_queue:
            return

        url = f"{self.literalai_api_url}/api/graphql"
        query = self._steps_query_builder(self.log_queue)
        variables = self._steps_variables_builder(self.log_queue)

        try:
            response = await self.async_httpx_client.post(
                url=url,
                json={
                    "query": query,
                    "variables": variables,
                },
                headers=self.headers,
            )
            if response.status_code >= 300:
                verbose_logger.error(
                    f"Literal AI Error: {response.status_code} - {response.text}"
                )
            else:
                verbose_logger.debug(
                    f"Batch of {len(self.log_queue)} runs successfully created"
                )
        except httpx.HTTPStatusError as e:
            verbose_logger.exception(
                f"Literal AI HTTP Error: {e.response.status_code} - {e.response.text}"
            )
        except Exception:
            verbose_logger.exception("Literal AI Layer Error")

    def _prepare_log_data(self, kwargs, response_obj, start_time, end_time) -> dict:
        logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
            "standard_logging_object", None
        )

        if logging_payload is None:
            raise ValueError("standard_logging_object not found in kwargs")
        clean_metadata = logging_payload["metadata"]
        metadata = kwargs.get("litellm_params", {}).get("metadata", {})

        settings = logging_payload["model_parameters"]
        messages = logging_payload["messages"]
        response = logging_payload["response"]
        choices: List = []
        if isinstance(response, dict) and "choices" in response:
            choices = response["choices"]
        message_completion = choices[0]["message"] if choices else None
        prompt_id = None
        variables = None

        if messages and isinstance(messages, list) and isinstance(messages[0], dict):
            for message in messages:
                if literal_prompt := getattr(message, "__literal_prompt__", None):
                    prompt_id = literal_prompt.get("prompt_id")
                    variables = literal_prompt.get("variables")
                    message["uuid"] = literal_prompt.get("uuid")
                    message["templated"] = True

        tools = settings.pop("tools", None)

        step = {
            "id": metadata.get("step_id", str(uuid.uuid4())),
            "error": logging_payload["error_str"],
            "name": kwargs.get("model", ""),
            "threadId": metadata.get("literalai_thread_id", None),
            "parentId": metadata.get("literalai_parent_id", None),
            "rootRunId": metadata.get("literalai_root_run_id", None),
            "input": None,
            "output": None,
            "type": "llm",
            "tags": metadata.get("tags", metadata.get("literalai_tags", None)),
            "startTime": str(start_time),
            "endTime": str(end_time),
            "metadata": clean_metadata,
            "generation": {
                "inputTokenCount": logging_payload["prompt_tokens"],
                "outputTokenCount": logging_payload["completion_tokens"],
                "tokenCount": logging_payload["total_tokens"],
                "promptId": prompt_id,
                "variables": variables,
                "provider": kwargs.get("custom_llm_provider", "litellm"),
                "model": kwargs.get("model", ""),
                "duration": (end_time - start_time).total_seconds(),
                "settings": settings,
                "messages": messages,
                "messageCompletion": message_completion,
                "tools": tools,
            },
        }
        return step

    def _steps_query_variables_builder(self, steps):
        generated = ""
        for id in range(len(steps)):
            generated += f"""$id_{id}: String!
            $threadId_{id}: String
            $rootRunId_{id}: String
            $type_{id}: StepType
            $startTime_{id}: DateTime
            $endTime_{id}: DateTime
            $error_{id}: String
            $input_{id}: Json
            $output_{id}: Json
            $metadata_{id}: Json
            $parentId_{id}: String
            $name_{id}: String
            $tags_{id}: [String!]
            $generation_{id}: GenerationPayloadInput
            $scores_{id}: [ScorePayloadInput!]
            $attachments_{id}: [AttachmentPayloadInput!]
            """
        return generated

    def _steps_ingest_steps_builder(self, steps):
        generated = ""
        for id in range(len(steps)):
            generated += f"""
        step{id}: ingestStep(
            id: $id_{id}
            threadId: $threadId_{id}
            rootRunId: $rootRunId_{id}
            startTime: $startTime_{id}
            endTime: $endTime_{id}
            type: $type_{id}
            error: $error_{id}
            input: $input_{id}
            output: $output_{id}
            metadata: $metadata_{id}
            parentId: $parentId_{id}
            name: $name_{id}
            tags: $tags_{id}
            generation: $generation_{id}
            scores: $scores_{id}
            attachments: $attachments_{id}
        ) {{
            ok
            message
        }}
    """
        return generated

    def _steps_query_builder(self, steps):
        return f"""
        mutation AddStep({self._steps_query_variables_builder(steps)}) {{
        {self._steps_ingest_steps_builder(steps)}
        }}
        """

    def _steps_variables_builder(self, steps):
        def serialize_step(event, id):
            result = {}

            for key, value in event.items():
                # Only keep the keys that are not None to avoid overriding existing values
                if value is not None:
                    result[f"{key}_{id}"] = value

            return result

        variables = {}
        for i in range(len(steps)):
            step = steps[i]
            variables.update(serialize_step(step, i))
        return variables

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\resolvelib\resolver.py ===
import contextlib
import functools
import logging
import os
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, cast

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.resolvelib import BaseReporter, ResolutionImpossible
from pip._vendor.resolvelib import Resolver as RLResolver
from pip._vendor.resolvelib.structs import DirectedGraph

from pip._internal.cache import WheelCache
from pip._internal.index.package_finder import PackageFinder
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.constructors import install_req_extend_extras
from pip._internal.req.req_install import InstallRequirement
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.base import BaseResolver, InstallRequirementProvider
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.reporter import (
    PipDebuggingReporter,
    PipReporter,
)
from pip._internal.utils.packaging import get_requirement

from .base import Candidate, Requirement
from .factory import Factory

if TYPE_CHECKING:
    from pip._vendor.resolvelib.resolvers import Result as RLResult

    Result = RLResult[Requirement, Candidate, str]


logger = logging.getLogger(__name__)


class Resolver(BaseResolver):
    _allowed_strategies = {"eager", "only-if-needed", "to-satisfy-only"}

    def __init__(
        self,
        preparer: RequirementPreparer,
        finder: PackageFinder,
        wheel_cache: Optional[WheelCache],
        make_install_req: InstallRequirementProvider,
        use_user_site: bool,
        ignore_dependencies: bool,
        ignore_installed: bool,
        ignore_requires_python: bool,
        force_reinstall: bool,
        upgrade_strategy: str,
        py_version_info: Optional[Tuple[int, ...]] = None,
    ):
        super().__init__()
        assert upgrade_strategy in self._allowed_strategies

        self.factory = Factory(
            finder=finder,
            preparer=preparer,
            make_install_req=make_install_req,
            wheel_cache=wheel_cache,
            use_user_site=use_user_site,
            force_reinstall=force_reinstall,
            ignore_installed=ignore_installed,
            ignore_requires_python=ignore_requires_python,
            py_version_info=py_version_info,
        )
        self.ignore_dependencies = ignore_dependencies
        self.upgrade_strategy = upgrade_strategy
        self._result: Optional[Result] = None

    def resolve(
        self, root_reqs: List[InstallRequirement], check_supported_wheels: bool
    ) -> RequirementSet:
        collected = self.factory.collect_root_requirements(root_reqs)
        provider = PipProvider(
            factory=self.factory,
            constraints=collected.constraints,
            ignore_dependencies=self.ignore_dependencies,
            upgrade_strategy=self.upgrade_strategy,
            user_requested=collected.user_requested,
        )
        if "PIP_RESOLVER_DEBUG" in os.environ:
            reporter: BaseReporter = PipDebuggingReporter()
        else:
            reporter = PipReporter()
        resolver: RLResolver[Requirement, Candidate, str] = RLResolver(
            provider,
            reporter,
        )

        try:
            limit_how_complex_resolution_can_be = 200000
            result = self._result = resolver.resolve(
                collected.requirements, max_rounds=limit_how_complex_resolution_can_be
            )

        except ResolutionImpossible as e:
            error = self.factory.get_installation_error(
                cast("ResolutionImpossible[Requirement, Candidate]", e),
                collected.constraints,
            )
            raise error from e

        req_set = RequirementSet(check_supported_wheels=check_supported_wheels)
        # process candidates with extras last to ensure their base equivalent is
        # already in the req_set if appropriate.
        # Python's sort is stable so using a binary key function keeps relative order
        # within both subsets.
        for candidate in sorted(
            result.mapping.values(), key=lambda c: c.name != c.project_name
        ):
            ireq = candidate.get_install_requirement()
            if ireq is None:
                if candidate.name != candidate.project_name:
                    # extend existing req's extras
                    with contextlib.suppress(KeyError):
                        req = req_set.get_requirement(candidate.project_name)
                        req_set.add_named_requirement(
                            install_req_extend_extras(
                                req, get_requirement(candidate.name).extras
                            )
                        )
                continue

            # Check if there is already an installation under the same name,
            # and set a flag for later stages to uninstall it, if needed.
            installed_dist = self.factory.get_dist_to_uninstall(candidate)
            if installed_dist is None:
                # There is no existing installation -- nothing to uninstall.
                ireq.should_reinstall = False
            elif self.factory.force_reinstall:
                # The --force-reinstall flag is set -- reinstall.
                ireq.should_reinstall = True
            elif installed_dist.version != candidate.version:
                # The installation is different in version -- reinstall.
                ireq.should_reinstall = True
            elif candidate.is_editable or installed_dist.editable:
                # The incoming distribution is editable, or different in
                # editable-ness to installation -- reinstall.
                ireq.should_reinstall = True
            elif candidate.source_link and candidate.source_link.is_file:
                # The incoming distribution is under file://
                if candidate.source_link.is_wheel:
                    # is a local wheel -- do nothing.
                    logger.info(
                        "%s is already installed with the same version as the "
                        "provided wheel. Use --force-reinstall to force an "
                        "installation of the wheel.",
                        ireq.name,
                    )
                    continue

                # is a local sdist or path -- reinstall
                ireq.should_reinstall = True
            else:
                continue

            link = candidate.source_link
            if link and link.is_yanked:
                # The reason can contain non-ASCII characters, Unicode
                # is required for Python 2.
                msg = (
                    "The candidate selected for download or install is a "
                    "yanked version: {name!r} candidate (version {version} "
                    "at {link})\nReason for being yanked: {reason}"
                ).format(
                    name=candidate.name,
                    version=candidate.version,
                    link=link,
                    reason=link.yanked_reason or "<none given>",
                )
                logger.warning(msg)

            req_set.add_named_requirement(ireq)

        reqs = req_set.all_requirements
        self.factory.preparer.prepare_linked_requirements_more(reqs)
        for req in reqs:
            req.prepared = True
            req.needs_more_preparation = False
        return req_set

    def get_installation_order(
        self, req_set: RequirementSet
    ) -> List[InstallRequirement]:
        """Get order for installation of requirements in RequirementSet.

        The returned list contains a requirement before another that depends on
        it. This helps ensure that the environment is kept consistent as they
        get installed one-by-one.

        The current implementation creates a topological ordering of the
        dependency graph, giving more weight to packages with less
        or no dependencies, while breaking any cycles in the graph at
        arbitrary points. We make no guarantees about where the cycle
        would be broken, other than it *would* be broken.
        """
        assert self._result is not None, "must call resolve() first"

        if not req_set.requirements:
            # Nothing is left to install, so we do not need an order.
            return []

        graph = self._result.graph
        weights = get_topological_weights(graph, set(req_set.requirements.keys()))

        sorted_items = sorted(
            req_set.requirements.items(),
            key=functools.partial(_req_set_item_sorter, weights=weights),
            reverse=True,
        )
        return [ireq for _, ireq in sorted_items]


def get_topological_weights(
    graph: "DirectedGraph[Optional[str]]", requirement_keys: Set[str]
) -> Dict[Optional[str], int]:
    """Assign weights to each node based on how "deep" they are.

    This implementation may change at any point in the future without prior
    notice.

    We first simplify the dependency graph by pruning any leaves and giving them
    the highest weight: a package without any dependencies should be installed
    first. This is done again and again in the same way, giving ever less weight
    to the newly found leaves. The loop stops when no leaves are left: all
    remaining packages have at least one dependency left in the graph.

    Then we continue with the remaining graph, by taking the length for the
    longest path to any node from root, ignoring any paths that contain a single
    node twice (i.e. cycles). This is done through a depth-first search through
    the graph, while keeping track of the path to the node.

    Cycles in the graph result would result in node being revisited while also
    being on its own path. In this case, take no action. This helps ensure we
    don't get stuck in a cycle.

    When assigning weight, the longer path (i.e. larger length) is preferred.

    We are only interested in the weights of packages that are in the
    requirement_keys.
    """
    path: Set[Optional[str]] = set()
    weights: Dict[Optional[str], int] = {}

    def visit(node: Optional[str]) -> None:
        if node in path:
            # We hit a cycle, so we'll break it here.
            return

        # Time to visit the children!
        path.add(node)
        for child in graph.iter_children(node):
            visit(child)
        path.remove(node)

        if node not in requirement_keys:
            return

        last_known_parent_count = weights.get(node, 0)
        weights[node] = max(last_known_parent_count, len(path))

    # Simplify the graph, pruning leaves that have no dependencies.
    # This is needed for large graphs (say over 200 packages) because the
    # `visit` function is exponentially slower then, taking minutes.
    # See https://github.com/pypa/pip/issues/10557
    # We will loop until we explicitly break the loop.
    while True:
        leaves = set()
        for key in graph:
            if key is None:
                continue
            for _child in graph.iter_children(key):
                # This means we have at least one child
                break
            else:
                # No child.
                leaves.add(key)
        if not leaves:
            # We are done simplifying.
            break
        # Calculate the weight for the leaves.
        weight = len(graph) - 1
        for leaf in leaves:
            if leaf not in requirement_keys:
                continue
            weights[leaf] = weight
        # Remove the leaves from the graph, making it simpler.
        for leaf in leaves:
            graph.remove(leaf)

    # Visit the remaining graph.
    # `None` is guaranteed to be the root node by resolvelib.
    visit(None)

    # Sanity check: all requirement keys should be in the weights,
    # and no other keys should be in the weights.
    difference = set(weights.keys()).difference(requirement_keys)
    assert not difference, difference

    return weights


def _req_set_item_sorter(
    item: Tuple[str, InstallRequirement],
    weights: Dict[Optional[str], int],
) -> Tuple[int, str]:
    """Key function used to sort install requirements for installation.

    Based on the "weight" mapping calculated in ``get_installation_order()``.
    The canonical package name is returned as the second member as a tie-
    breaker to ensure the result is predictable, which is useful in tests.
    """
    name = canonicalize_name(item[0])
    return weights[name], name

# === NexusCore/openenv\Lib\site-packages\trio\_core\_parking_lot.py ===
# ParkingLot provides an abstraction for a fair waitqueue with cancellation
# and requeuing support. Inspiration:
#
#    https://webkit.org/blog/6161/locking-in-webkit/
#    https://amanieu.github.io/parking_lot/
#
# which were in turn heavily influenced by
#
#    http://gee.cs.oswego.edu/dl/papers/aqs.pdf
#
# Compared to these, our use of cooperative scheduling allows some
# simplifications (no need for internal locking). On the other hand, the need
# to support Trio's strong cancellation semantics adds some complications
# (tasks need to know where they're queued so they can cancel). Also, in the
# above work, the ParkingLot is a global structure that holds a collection of
# waitqueues keyed by lock address, and which are opportunistically allocated
# and destroyed as contention arises; this allows the worst-case memory usage
# for all waitqueues to be O(#tasks). Here we allocate a separate wait queue
# for each synchronization object, so we're O(#objects + #tasks). This isn't
# *so* bad since compared to our synchronization objects are heavier than
# theirs and our tasks are lighter, so for us #objects is smaller and #tasks
# is larger.
#
# This is in the core because for two reasons. First, it's used by
# UnboundedQueue, and UnboundedQueue is used for a number of things in the
# core. And second, it's responsible for providing fairness to all of our
# high-level synchronization primitives (locks, queues, etc.). For now with
# our FIFO scheduler this is relatively trivial (it's just a FIFO waitqueue),
# but in the future we ever start support task priorities or fair scheduling
#
#    https://github.com/python-trio/trio/issues/32
#
# then all we'll have to do is update this. (Well, full-fledged task
# priorities might also require priority inheritance, which would require more
# work.)
#
# For discussion of data structures to use here, see:
#
#     https://github.com/dabeaz/curio/issues/136
#
# (and also the articles above). Currently we use a SortedDict ordered by a
# global monotonic counter that ensures FIFO ordering. The main advantage of
# this is that it's easy to implement :-). An intrusive doubly-linked list
# would also be a natural approach, so long as we only handle FIFO ordering.
#
# XX: should we switch to the shared global ParkingLot approach?
#
# XX: we should probably add support for "parking tokens" to allow for
# task-fair RWlock (basically: when parking a task needs to be able to mark
# itself as a reader or a writer, and then a task-fair wakeup policy is, wake
# the next task, and if it's a reader than keep waking tasks so long as they
# are readers). Without this I think you can implement write-biased or
# read-biased RWlocks (by using two parking lots and drawing from whichever is
# preferred), but not task-fair -- and task-fair plays much more nicely with
# WFQ. (Consider what happens in the two-lot implementation if you're
# write-biased but all the pending writers are blocked at the scheduler level
# by the WFQ logic...)
# ...alternatively, "phase-fair" RWlocks are pretty interesting:
#    http://www.cs.unc.edu/~anderson/papers/ecrts09b.pdf
# Useful summary:
# https://docs.oracle.com/javase/7/docs/api/java/util/concurrent/locks/ReadWriteLock.html
#
# XX: if we do add WFQ, then we might have to drop the current feature where
# unpark returns the tasks that were unparked. Rationale: suppose that at the
# time we call unpark, the next task is deprioritized... and then, before it
# becomes runnable, a new task parks which *is* runnable. Ideally we should
# immediately wake the new task, and leave the old task on the queue for
# later. But this means we can't commit to which task we are unparking when
# unpark is called.
#
# See: https://github.com/python-trio/trio/issues/53
from __future__ import annotations

import inspect
import math
from collections import OrderedDict
from typing import TYPE_CHECKING

import attrs
import outcome

from .. import _core
from .._util import final

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ._run import Task


GLOBAL_PARKING_LOT_BREAKER: dict[Task, list[ParkingLot]] = {}


def add_parking_lot_breaker(task: Task, lot: ParkingLot) -> None:
    """Register a task as a breaker for a lot. See :meth:`ParkingLot.break_lot`.

    raises:
      trio.BrokenResourceError: if the task has already exited.
    """
    if inspect.getcoroutinestate(task.coro) == inspect.CORO_CLOSED:
        raise _core._exceptions.BrokenResourceError(
            "Attempted to add already exited task as lot breaker.",
        )
    if task not in GLOBAL_PARKING_LOT_BREAKER:
        GLOBAL_PARKING_LOT_BREAKER[task] = [lot]
    else:
        GLOBAL_PARKING_LOT_BREAKER[task].append(lot)


def remove_parking_lot_breaker(task: Task, lot: ParkingLot) -> None:
    """Deregister a task as a breaker for a lot. See :meth:`ParkingLot.break_lot`"""
    try:
        GLOBAL_PARKING_LOT_BREAKER[task].remove(lot)
    except (KeyError, ValueError):
        raise RuntimeError(
            "Attempted to remove task as breaker for a lot it is not registered for",
        ) from None
    if not GLOBAL_PARKING_LOT_BREAKER[task]:
        del GLOBAL_PARKING_LOT_BREAKER[task]


@attrs.frozen
class ParkingLotStatistics:
    """An object containing debugging information for a ParkingLot.

    Currently, the following fields are defined:

    * ``tasks_waiting`` (int): The number of tasks blocked on this lot's
      :meth:`trio.lowlevel.ParkingLot.park` method.

    """

    tasks_waiting: int


@final
@attrs.define(eq=False)
class ParkingLot:
    """A fair wait queue with cancellation and requeuing.

    This class encapsulates the tricky parts of implementing a wait
    queue. It's useful for implementing higher-level synchronization
    primitives like queues and locks.

    In addition to the methods below, you can use ``len(parking_lot)`` to get
    the number of parked tasks, and ``if parking_lot: ...`` to check whether
    there are any parked tasks.

    """

    # {task: None}, we just want a deque where we can quickly delete random
    # items
    _parked: OrderedDict[Task, None] = attrs.field(factory=OrderedDict, init=False)
    broken_by: list[Task] = attrs.field(factory=list, init=False)

    def __len__(self) -> int:
        """Returns the number of parked tasks."""
        return len(self._parked)

    def __bool__(self) -> bool:
        """True if there are parked tasks, False otherwise."""
        return bool(self._parked)

    # XX this currently returns None
    # if we ever add the ability to repark while one's resuming place in
    # line (for false wakeups), then we could have it return a ticket that
    # abstracts the "place in line" concept.
    @_core.enable_ki_protection
    async def park(self) -> None:
        """Park the current task until woken by a call to :meth:`unpark` or
        :meth:`unpark_all`.

        Raises:
          BrokenResourceError: if attempting to park in a broken lot, or the lot
            breaks before we get to unpark.

        """
        if self.broken_by:
            raise _core.BrokenResourceError(
                f"Attempted to park in parking lot broken by {self.broken_by}",
            )
        task = _core.current_task()
        self._parked[task] = None
        task.custom_sleep_data = self

        def abort_fn(_: _core.RaiseCancelT) -> _core.Abort:
            del task.custom_sleep_data._parked[task]
            return _core.Abort.SUCCEEDED

        await _core.wait_task_rescheduled(abort_fn)

    def _pop_several(self, count: int | float) -> Iterator[Task]:  # noqa: PYI041
        if isinstance(count, float):
            if math.isinf(count):
                count = len(self._parked)
            else:
                raise ValueError("Cannot pop a non-integer number of tasks.")
        else:
            count = min(count, len(self._parked))
        for _ in range(count):
            task, _ = self._parked.popitem(last=False)
            yield task

    @_core.enable_ki_protection
    def unpark(self, *, count: int | float = 1) -> list[Task]:  # noqa: PYI041
        """Unpark one or more tasks.

        This wakes up ``count`` tasks that are blocked in :meth:`park`. If
        there are fewer than ``count`` tasks parked, then wakes as many tasks
        are available and then returns successfully.

        Args:
          count (int | math.inf): the number of tasks to unpark.

        """
        tasks = list(self._pop_several(count))
        for task in tasks:
            _core.reschedule(task)
        return tasks

    def unpark_all(self) -> list[Task]:
        """Unpark all parked tasks."""
        return self.unpark(count=len(self))

    @_core.enable_ki_protection
    def repark(
        self,
        new_lot: ParkingLot,
        *,
        count: int | float = 1,  # noqa: PYI041
    ) -> None:
        """Move parked tasks from one :class:`ParkingLot` object to another.

        This dequeues ``count`` tasks from one lot, and requeues them on
        another, preserving order. For example::

           async def parker(lot):
               print("sleeping")
               await lot.park()
               print("woken")

           async def main():
               lot1 = trio.lowlevel.ParkingLot()
               lot2 = trio.lowlevel.ParkingLot()
               async with trio.open_nursery() as nursery:
                   nursery.start_soon(parker, lot1)
                   await trio.testing.wait_all_tasks_blocked()
                   assert len(lot1) == 1
                   assert len(lot2) == 0
                   lot1.repark(lot2)
                   assert len(lot1) == 0
                   assert len(lot2) == 1
                   # This wakes up the task that was originally parked in lot1
                   lot2.unpark()

        If there are fewer than ``count`` tasks parked, then reparks as many
        tasks as are available and then returns successfully.

        Args:
          new_lot (ParkingLot): the parking lot to move tasks to.
          count (int|math.inf): the number of tasks to move.

        """
        if not isinstance(new_lot, ParkingLot):
            raise TypeError("new_lot must be a ParkingLot")
        for task in self._pop_several(count):
            new_lot._parked[task] = None
            task.custom_sleep_data = new_lot

    def repark_all(self, new_lot: ParkingLot) -> None:
        """Move all parked tasks from one :class:`ParkingLot` object to
        another.

        See :meth:`repark` for details.

        """
        return self.repark(new_lot, count=len(self))

    def break_lot(self, task: Task | None = None) -> None:
        """Break this lot, with ``task`` noted as the task that broke it.

        This causes all parked tasks to raise an error, and any
        future tasks attempting to park to error. Unpark & repark become no-ops as the
        parking lot is empty.

        The error raised contains a reference to the task sent as a parameter. The task
        is also saved in the parking lot in the ``broken_by`` attribute.
        """
        if task is None:
            task = _core.current_task()

        # if lot is already broken, just mark this as another breaker and return
        if self.broken_by:
            self.broken_by.append(task)
            return

        self.broken_by.append(task)

        for parked_task in self._parked:
            _core.reschedule(
                parked_task,
                outcome.Error(
                    _core.BrokenResourceError(f"Parking lot broken by {task}"),
                ),
            )
        self._parked.clear()

    def statistics(self) -> ParkingLotStatistics:
        """Return an object containing debugging information.

        Currently the following fields are defined:

        * ``tasks_waiting``: The number of tasks blocked on this lot's
          :meth:`park` method.

        """
        return ParkingLotStatistics(tasks_waiting=len(self._parked))

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_fakenet.py ===
import errno
import re
import socket
import sys

import pytest

import trio
from trio.testing._fake_net import FakeNet

# ENOTCONN gives different messages on different platforms
if sys.platform == "linux":
    ENOTCONN_MSG = r"^\[Errno 107\] (Transport endpoint is|Socket) not connected$"
elif sys.platform == "darwin":
    ENOTCONN_MSG = r"^\[Errno 57\] Socket is not connected$"
else:
    ENOTCONN_MSG = r"^\[Errno 10057\] Unknown error$"


def fn() -> FakeNet:
    fn = FakeNet()
    fn.enable()
    return fn


async def test_basic_udp() -> None:
    fn()
    s1 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)
    s2 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)

    await s1.bind(("127.0.0.1", 0))
    ip, port = s1.getsockname()
    assert ip == "127.0.0.1"
    assert port != 0

    with pytest.raises(
        OSError,
        match=r"^\[\w+ \d+\] Invalid argument$",
    ) as exc:  # Cannot rebind.
        await s1.bind(("192.0.2.1", 0))
    assert exc.value.errno == errno.EINVAL

    # Cannot bind multiple sockets to the same address
    with pytest.raises(
        OSError,
        match=r"^\[\w+ \d+\] (Address (already )?in use|Unknown error)$",
    ) as exc:
        await s2.bind(("127.0.0.1", port))
    assert exc.value.errno == errno.EADDRINUSE

    await s2.sendto(b"xyz", s1.getsockname())
    data, addr = await s1.recvfrom(10)
    assert data == b"xyz"
    assert addr == s2.getsockname()
    await s1.sendto(b"abc", s2.getsockname())
    data, addr = await s2.recvfrom(10)
    assert data == b"abc"
    assert addr == s1.getsockname()


async def test_msg_trunc() -> None:
    fn()
    s1 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)
    s2 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)
    await s1.bind(("127.0.0.1", 0))
    await s2.sendto(b"xyz", s1.getsockname())
    await s1.recvfrom(10)


async def test_recv_methods() -> None:
    """Test all recv methods for codecov"""
    fn()
    s1 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)
    s2 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)

    # receiving on an unbound socket is a bad idea (I think?)
    with pytest.raises(NotImplementedError, match="code will most likely hang"):
        await s2.recv(10)

    await s1.bind(("127.0.0.1", 0))
    ip, port = s1.getsockname()
    assert ip == "127.0.0.1"
    assert port != 0

    # recvfrom
    await s2.sendto(b"abc", s1.getsockname())
    data, addr = await s1.recvfrom(10)
    assert data == b"abc"
    assert addr == s2.getsockname()

    # recv
    await s1.sendto(b"def", s2.getsockname())
    data = await s2.recv(10)
    assert data == b"def"

    # recvfrom_into
    assert await s1.sendto(b"ghi", s2.getsockname()) == 3
    buf = bytearray(10)

    with pytest.raises(NotImplementedError, match=r"^partial recvfrom_into$"):
        (nbytes, addr) = await s2.recvfrom_into(buf, nbytes=2)

    (nbytes, addr) = await s2.recvfrom_into(buf)
    assert nbytes == 3
    assert buf == b"ghi" + b"\x00" * 7
    assert addr == s1.getsockname()

    # recv_into
    assert await s1.sendto(b"jkl", s2.getsockname()) == 3
    buf2 = bytearray(10)
    nbytes = await s2.recv_into(buf2)
    assert nbytes == 3
    assert buf2 == b"jkl" + b"\x00" * 7

    if sys.platform == "linux" and sys.implementation.name == "cpython":
        flags: int = socket.MSG_MORE
    else:
        flags = 1

    # Send seems explicitly non-functional
    with pytest.raises(OSError, match=ENOTCONN_MSG) as exc:
        await s2.send(b"mno")
    assert exc.value.errno == errno.ENOTCONN
    with pytest.raises(
        NotImplementedError, match=r"^FakeNet send flags must be 0, not"
    ):
        await s2.send(b"mno", flags)

    # sendto errors
    # it's successfully used earlier
    with pytest.raises(
        NotImplementedError, match=r"^FakeNet send flags must be 0, not"
    ):
        await s2.sendto(b"mno", flags, s1.getsockname())
    with pytest.raises(TypeError, match=r"wrong number of arguments$"):
        await s2.sendto(b"mno", flags, s1.getsockname(), "extra arg")  # type: ignore[call-overload]


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="functions not in socket on windows",
)
async def test_nonwindows_functionality() -> None:
    # mypy doesn't support a good way of aborting typechecking on different platforms
    if sys.platform != "win32":  # pragma: no branch
        fn()
        s1 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)
        s2 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)
        await s2.bind(("127.0.0.1", 0))

        # sendmsg
        with pytest.raises(OSError, match=ENOTCONN_MSG) as exc:
            await s2.sendmsg([b"mno"])
        assert exc.value.errno == errno.ENOTCONN

        assert await s1.sendmsg([b"jkl"], (), 0, s2.getsockname()) == 3
        (data, ancdata, msg_flags, addr) = await s2.recvmsg(10)
        assert data == b"jkl"
        assert ancdata == []
        assert msg_flags == 0
        assert addr == s1.getsockname()

        # TODO: recvmsg

        # recvmsg_into
        assert await s1.sendto(b"xyzw", s2.getsockname()) == 4
        buf1 = bytearray(2)
        buf2 = bytearray(3)
        ret = await s2.recvmsg_into([buf1, buf2])
        (nbytes, ancdata, msg_flags, addr) = ret
        assert nbytes == 4
        assert buf1 == b"xy"
        assert buf2 == b"zw" + b"\x00"
        assert ancdata == []
        assert msg_flags == 0
        assert addr == s1.getsockname()

        # recvmsg_into with MSG_TRUNC set
        assert await s1.sendto(b"xyzwv", s2.getsockname()) == 5
        buf1 = bytearray(2)
        ret = await s2.recvmsg_into([buf1])
        (nbytes, ancdata, msg_flags, addr) = ret
        assert nbytes == 2
        assert buf1 == b"xy"
        assert ancdata == []
        assert msg_flags == socket.MSG_TRUNC
        assert addr == s1.getsockname()

        with pytest.raises(
            AttributeError,
            match=r"^'FakeSocket' object has no attribute 'share'$",
        ):
            await s1.share(0)  # type: ignore[attr-defined]


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="windows-specific fakesocket testing",
)
async def test_windows_functionality() -> None:
    # mypy doesn't support a good way of aborting typechecking on different platforms
    if sys.platform == "win32":  # pragma: no branch
        fn()
        s1 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)
        s2 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)
        await s1.bind(("127.0.0.1", 0))
        with pytest.raises(
            AttributeError,
            match=r"^'FakeSocket' object has no attribute 'sendmsg'$",
        ):
            await s1.sendmsg([b"jkl"], (), 0, s2.getsockname())  # type: ignore[attr-defined]
        with pytest.raises(
            AttributeError,
            match=r"^'FakeSocket' object has no attribute 'recvmsg'$",
        ):
            s2.recvmsg(0)  # type: ignore[attr-defined]
        with pytest.raises(
            AttributeError,
            match=r"^'FakeSocket' object has no attribute 'recvmsg_into'$",
        ):
            s2.recvmsg_into([])  # type: ignore[attr-defined]
        with pytest.raises(NotImplementedError):
            s1.share(0)


async def test_basic_tcp() -> None:
    fn()
    with pytest.raises(NotImplementedError):
        trio.socket.socket()


async def test_not_implemented_functions() -> None:
    fn()
    s1 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)

    # getsockopt
    with pytest.raises(
        OSError,
        match=r"^FakeNet doesn't implement getsockopt\(\d, \d\)$",
    ):
        s1.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)

    # setsockopt
    with pytest.raises(
        NotImplementedError,
        match=r"^FakeNet always has IPV6_V6ONLY=True$",
    ):
        s1.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, False)
    with pytest.raises(
        OSError,
        match=r"^FakeNet doesn't implement setsockopt\(\d+, \d+, \.\.\.\)$",
    ):
        s1.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, True)
    with pytest.raises(
        OSError,
        match=r"^FakeNet doesn't implement setsockopt\(\d+, \d+, \.\.\.\)$",
    ):
        s1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # set_inheritable
    s1.set_inheritable(False)
    with pytest.raises(
        NotImplementedError,
        match=r"^FakeNet can't make inheritable sockets$",
    ):
        s1.set_inheritable(True)

    # get_inheritable
    assert not s1.get_inheritable()


async def test_getpeername() -> None:
    fn()
    s1 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)
    with pytest.raises(OSError, match=ENOTCONN_MSG) as exc:
        s1.getpeername()
    assert exc.value.errno == errno.ENOTCONN

    await s1.bind(("127.0.0.1", 0))

    with pytest.raises(
        AssertionError,
        match=r"^This method seems to assume that self._binding has a remote UDPEndpoint$",
    ):
        s1.getpeername()


async def test_init() -> None:
    fn()
    with pytest.raises(
        NotImplementedError,
        match=re.escape(
            f"FakeNet doesn't (yet) support type={trio.socket.SOCK_STREAM}",
        ),
    ):
        s1 = trio.socket.socket()

    # getsockname on unbound ipv4 socket
    s1 = trio.socket.socket(type=trio.socket.SOCK_DGRAM)
    assert s1.getsockname() == ("0.0.0.0", 0)

    # getsockname on bound ipv4 socket
    await s1.bind(("0.0.0.0", 0))
    ip, port = s1.getsockname()
    assert ip == "127.0.0.1"
    assert port != 0

    # getsockname on unbound ipv6 socket
    s2 = trio.socket.socket(family=socket.AF_INET6, type=socket.SOCK_DGRAM)
    assert s2.getsockname() == ("::", 0)

    # getsockname on bound ipv6 socket
    await s2.bind(("::", 0))
    ip, port, *_ = s2.getsockname()
    assert ip == "::1"
    assert port != 0
    assert _ == [0, 0]

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\truststore\_api.py ===
import os
import platform
import socket
import ssl
import sys
import typing

import _ssl  # type: ignore[import-not-found]

from ._ssl_constants import (
    _original_SSLContext,
    _original_super_SSLContext,
    _truststore_SSLContext_dunder_class,
    _truststore_SSLContext_super_class,
)

if platform.system() == "Windows":
    from ._windows import _configure_context, _verify_peercerts_impl
elif platform.system() == "Darwin":
    from ._macos import _configure_context, _verify_peercerts_impl
else:
    from ._openssl import _configure_context, _verify_peercerts_impl

if typing.TYPE_CHECKING:
    from pip._vendor.typing_extensions import Buffer

# From typeshed/stdlib/ssl.pyi
_StrOrBytesPath: typing.TypeAlias = str | bytes | os.PathLike[str] | os.PathLike[bytes]
_PasswordType: typing.TypeAlias = str | bytes | typing.Callable[[], str | bytes]


def inject_into_ssl() -> None:
    """Injects the :class:`truststore.SSLContext` into the ``ssl``
    module by replacing :class:`ssl.SSLContext`.
    """
    setattr(ssl, "SSLContext", SSLContext)
    # urllib3 holds on to its own reference of ssl.SSLContext
    # so we need to replace that reference too.
    try:
        import pip._vendor.urllib3.util.ssl_ as urllib3_ssl

        setattr(urllib3_ssl, "SSLContext", SSLContext)
    except ImportError:
        pass


def extract_from_ssl() -> None:
    """Restores the :class:`ssl.SSLContext` class to its original state"""
    setattr(ssl, "SSLContext", _original_SSLContext)
    try:
        import pip._vendor.urllib3.util.ssl_ as urllib3_ssl

        urllib3_ssl.SSLContext = _original_SSLContext  # type: ignore[assignment]
    except ImportError:
        pass


class SSLContext(_truststore_SSLContext_super_class):  # type: ignore[misc]
    """SSLContext API that uses system certificates on all platforms"""

    @property  # type: ignore[misc]
    def __class__(self) -> type:
        # Dirty hack to get around isinstance() checks
        # for ssl.SSLContext instances in aiohttp/trustme
        # when using non-CPython implementations.
        return _truststore_SSLContext_dunder_class or SSLContext

    def __init__(self, protocol: int = None) -> None:  # type: ignore[assignment]
        self._ctx = _original_SSLContext(protocol)

        class TruststoreSSLObject(ssl.SSLObject):
            # This object exists because wrap_bio() doesn't
            # immediately do the handshake so we need to do
            # certificate verifications after SSLObject.do_handshake()

            def do_handshake(self) -> None:
                ret = super().do_handshake()
                _verify_peercerts(self, server_hostname=self.server_hostname)
                return ret

        self._ctx.sslobject_class = TruststoreSSLObject

    def wrap_socket(
        self,
        sock: socket.socket,
        server_side: bool = False,
        do_handshake_on_connect: bool = True,
        suppress_ragged_eofs: bool = True,
        server_hostname: str | None = None,
        session: ssl.SSLSession | None = None,
    ) -> ssl.SSLSocket:
        # Use a context manager here because the
        # inner SSLContext holds on to our state
        # but also does the actual handshake.
        with _configure_context(self._ctx):
            ssl_sock = self._ctx.wrap_socket(
                sock,
                server_side=server_side,
                server_hostname=server_hostname,
                do_handshake_on_connect=do_handshake_on_connect,
                suppress_ragged_eofs=suppress_ragged_eofs,
                session=session,
            )
        try:
            _verify_peercerts(ssl_sock, server_hostname=server_hostname)
        except Exception:
            ssl_sock.close()
            raise
        return ssl_sock

    def wrap_bio(
        self,
        incoming: ssl.MemoryBIO,
        outgoing: ssl.MemoryBIO,
        server_side: bool = False,
        server_hostname: str | None = None,
        session: ssl.SSLSession | None = None,
    ) -> ssl.SSLObject:
        with _configure_context(self._ctx):
            ssl_obj = self._ctx.wrap_bio(
                incoming,
                outgoing,
                server_hostname=server_hostname,
                server_side=server_side,
                session=session,
            )
        return ssl_obj

    def load_verify_locations(
        self,
        cafile: str | bytes | os.PathLike[str] | os.PathLike[bytes] | None = None,
        capath: str | bytes | os.PathLike[str] | os.PathLike[bytes] | None = None,
        cadata: typing.Union[str, "Buffer", None] = None,
    ) -> None:
        return self._ctx.load_verify_locations(
            cafile=cafile, capath=capath, cadata=cadata
        )

    def load_cert_chain(
        self,
        certfile: _StrOrBytesPath,
        keyfile: _StrOrBytesPath | None = None,
        password: _PasswordType | None = None,
    ) -> None:
        return self._ctx.load_cert_chain(
            certfile=certfile, keyfile=keyfile, password=password
        )

    def load_default_certs(
        self, purpose: ssl.Purpose = ssl.Purpose.SERVER_AUTH
    ) -> None:
        return self._ctx.load_default_certs(purpose)

    def set_alpn_protocols(self, alpn_protocols: typing.Iterable[str]) -> None:
        return self._ctx.set_alpn_protocols(alpn_protocols)

    def set_npn_protocols(self, npn_protocols: typing.Iterable[str]) -> None:
        return self._ctx.set_npn_protocols(npn_protocols)

    def set_ciphers(self, __cipherlist: str) -> None:
        return self._ctx.set_ciphers(__cipherlist)

    def get_ciphers(self) -> typing.Any:
        return self._ctx.get_ciphers()

    def session_stats(self) -> dict[str, int]:
        return self._ctx.session_stats()

    def cert_store_stats(self) -> dict[str, int]:
        raise NotImplementedError()

    def set_default_verify_paths(self) -> None:
        self._ctx.set_default_verify_paths()

    @typing.overload
    def get_ca_certs(
        self, binary_form: typing.Literal[False] = ...
    ) -> list[typing.Any]: ...

    @typing.overload
    def get_ca_certs(self, binary_form: typing.Literal[True] = ...) -> list[bytes]: ...

    @typing.overload
    def get_ca_certs(self, binary_form: bool = ...) -> typing.Any: ...

    def get_ca_certs(self, binary_form: bool = False) -> list[typing.Any] | list[bytes]:
        raise NotImplementedError()

    @property
    def check_hostname(self) -> bool:
        return self._ctx.check_hostname

    @check_hostname.setter
    def check_hostname(self, value: bool) -> None:
        self._ctx.check_hostname = value

    @property
    def hostname_checks_common_name(self) -> bool:
        return self._ctx.hostname_checks_common_name

    @hostname_checks_common_name.setter
    def hostname_checks_common_name(self, value: bool) -> None:
        self._ctx.hostname_checks_common_name = value

    @property
    def keylog_filename(self) -> str:
        return self._ctx.keylog_filename

    @keylog_filename.setter
    def keylog_filename(self, value: str) -> None:
        self._ctx.keylog_filename = value

    @property
    def maximum_version(self) -> ssl.TLSVersion:
        return self._ctx.maximum_version

    @maximum_version.setter
    def maximum_version(self, value: ssl.TLSVersion) -> None:
        _original_super_SSLContext.maximum_version.__set__(  # type: ignore[attr-defined]
            self._ctx, value
        )

    @property
    def minimum_version(self) -> ssl.TLSVersion:
        return self._ctx.minimum_version

    @minimum_version.setter
    def minimum_version(self, value: ssl.TLSVersion) -> None:
        _original_super_SSLContext.minimum_version.__set__(  # type: ignore[attr-defined]
            self._ctx, value
        )

    @property
    def options(self) -> ssl.Options:
        return self._ctx.options

    @options.setter
    def options(self, value: ssl.Options) -> None:
        _original_super_SSLContext.options.__set__(  # type: ignore[attr-defined]
            self._ctx, value
        )

    @property
    def post_handshake_auth(self) -> bool:
        return self._ctx.post_handshake_auth

    @post_handshake_auth.setter
    def post_handshake_auth(self, value: bool) -> None:
        self._ctx.post_handshake_auth = value

    @property
    def protocol(self) -> ssl._SSLMethod:
        return self._ctx.protocol

    @property
    def security_level(self) -> int:
        return self._ctx.security_level

    @property
    def verify_flags(self) -> ssl.VerifyFlags:
        return self._ctx.verify_flags

    @verify_flags.setter
    def verify_flags(self, value: ssl.VerifyFlags) -> None:
        _original_super_SSLContext.verify_flags.__set__(  # type: ignore[attr-defined]
            self._ctx, value
        )

    @property
    def verify_mode(self) -> ssl.VerifyMode:
        return self._ctx.verify_mode

    @verify_mode.setter
    def verify_mode(self, value: ssl.VerifyMode) -> None:
        _original_super_SSLContext.verify_mode.__set__(  # type: ignore[attr-defined]
            self._ctx, value
        )


# Python 3.13+ makes get_unverified_chain() a public API that only returns DER
# encoded certificates. We detect whether we need to call public_bytes() for 3.10->3.12
# Pre-3.13 returned None instead of an empty list from get_unverified_chain()
if sys.version_info >= (3, 13):

    def _get_unverified_chain_bytes(sslobj: ssl.SSLObject) -> list[bytes]:
        unverified_chain = sslobj.get_unverified_chain() or ()  # type: ignore[attr-defined]
        return [
            cert if isinstance(cert, bytes) else cert.public_bytes(_ssl.ENCODING_DER)
            for cert in unverified_chain
        ]

else:

    def _get_unverified_chain_bytes(sslobj: ssl.SSLObject) -> list[bytes]:
        unverified_chain = sslobj.get_unverified_chain() or ()  # type: ignore[attr-defined]
        return [cert.public_bytes(_ssl.ENCODING_DER) for cert in unverified_chain]


def _verify_peercerts(
    sock_or_sslobj: ssl.SSLSocket | ssl.SSLObject, server_hostname: str | None
) -> None:
    """
    Verifies the peer certificates from an SSLSocket or SSLObject
    against the certificates in the OS trust store.
    """
    sslobj: ssl.SSLObject = sock_or_sslobj  # type: ignore[assignment]
    try:
        while not hasattr(sslobj, "get_unverified_chain"):
            sslobj = sslobj._sslobj  # type: ignore[attr-defined]
    except AttributeError:
        pass

    cert_bytes = _get_unverified_chain_bytes(sslobj)
    _verify_peercerts_impl(
        sock_or_sslobj.context, cert_bytes, server_hostname=server_hostname
    )

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\__init__.py ===
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
from .cache_service import (
    CreateCachedContentRequest,
    DeleteCachedContentRequest,
    GetCachedContentRequest,
    ListCachedContentsRequest,
    ListCachedContentsResponse,
    UpdateCachedContentRequest,
)
from .cached_content import CachedContent
from .citation import CitationMetadata, CitationSource
from .content import (
    Blob,
    CodeExecution,
    CodeExecutionResult,
    Content,
    ExecutableCode,
    FileData,
    FunctionCall,
    FunctionCallingConfig,
    FunctionDeclaration,
    FunctionResponse,
    GroundingPassage,
    GroundingPassages,
    Part,
    Schema,
    Tool,
    ToolConfig,
    Type,
)
from .discuss_service import (
    CountMessageTokensRequest,
    CountMessageTokensResponse,
    Example,
    GenerateMessageRequest,
    GenerateMessageResponse,
    Message,
    MessagePrompt,
)
from .file import File, VideoMetadata
from .file_service import (
    CreateFileRequest,
    CreateFileResponse,
    DeleteFileRequest,
    GetFileRequest,
    ListFilesRequest,
    ListFilesResponse,
)
from .generative_service import (
    AttributionSourceId,
    BatchEmbedContentsRequest,
    BatchEmbedContentsResponse,
    Candidate,
    ContentEmbedding,
    CountTokensRequest,
    CountTokensResponse,
    EmbedContentRequest,
    EmbedContentResponse,
    GenerateAnswerRequest,
    GenerateAnswerResponse,
    GenerateContentRequest,
    GenerateContentResponse,
    GenerationConfig,
    GroundingAttribution,
    SemanticRetrieverConfig,
    TaskType,
)
from .model import Model
from .model_service import (
    CreateTunedModelMetadata,
    CreateTunedModelRequest,
    DeleteTunedModelRequest,
    GetModelRequest,
    GetTunedModelRequest,
    ListModelsRequest,
    ListModelsResponse,
    ListTunedModelsRequest,
    ListTunedModelsResponse,
    UpdateTunedModelRequest,
)
from .permission import Permission
from .permission_service import (
    CreatePermissionRequest,
    DeletePermissionRequest,
    GetPermissionRequest,
    ListPermissionsRequest,
    ListPermissionsResponse,
    TransferOwnershipRequest,
    TransferOwnershipResponse,
    UpdatePermissionRequest,
)
from .retriever import (
    Chunk,
    ChunkData,
    Condition,
    Corpus,
    CustomMetadata,
    Document,
    MetadataFilter,
    StringList,
)
from .retriever_service import (
    BatchCreateChunksRequest,
    BatchCreateChunksResponse,
    BatchDeleteChunksRequest,
    BatchUpdateChunksRequest,
    BatchUpdateChunksResponse,
    CreateChunkRequest,
    CreateCorpusRequest,
    CreateDocumentRequest,
    DeleteChunkRequest,
    DeleteCorpusRequest,
    DeleteDocumentRequest,
    GetChunkRequest,
    GetCorpusRequest,
    GetDocumentRequest,
    ListChunksRequest,
    ListChunksResponse,
    ListCorporaRequest,
    ListCorporaResponse,
    ListDocumentsRequest,
    ListDocumentsResponse,
    QueryCorpusRequest,
    QueryCorpusResponse,
    QueryDocumentRequest,
    QueryDocumentResponse,
    RelevantChunk,
    UpdateChunkRequest,
    UpdateCorpusRequest,
    UpdateDocumentRequest,
)
from .safety import (
    ContentFilter,
    HarmCategory,
    SafetyFeedback,
    SafetyRating,
    SafetySetting,
)
from .text_service import (
    BatchEmbedTextRequest,
    BatchEmbedTextResponse,
    CountTextTokensRequest,
    CountTextTokensResponse,
    Embedding,
    EmbedTextRequest,
    EmbedTextResponse,
    GenerateTextRequest,
    GenerateTextResponse,
    TextCompletion,
    TextPrompt,
)
from .tuned_model import (
    Dataset,
    Hyperparameters,
    TunedModel,
    TunedModelSource,
    TuningExample,
    TuningExamples,
    TuningSnapshot,
    TuningTask,
)

__all__ = (
    "CreateCachedContentRequest",
    "DeleteCachedContentRequest",
    "GetCachedContentRequest",
    "ListCachedContentsRequest",
    "ListCachedContentsResponse",
    "UpdateCachedContentRequest",
    "CachedContent",
    "CitationMetadata",
    "CitationSource",
    "Blob",
    "CodeExecution",
    "CodeExecutionResult",
    "Content",
    "ExecutableCode",
    "FileData",
    "FunctionCall",
    "FunctionCallingConfig",
    "FunctionDeclaration",
    "FunctionResponse",
    "GroundingPassage",
    "GroundingPassages",
    "Part",
    "Schema",
    "Tool",
    "ToolConfig",
    "Type",
    "CountMessageTokensRequest",
    "CountMessageTokensResponse",
    "Example",
    "GenerateMessageRequest",
    "GenerateMessageResponse",
    "Message",
    "MessagePrompt",
    "File",
    "VideoMetadata",
    "CreateFileRequest",
    "CreateFileResponse",
    "DeleteFileRequest",
    "GetFileRequest",
    "ListFilesRequest",
    "ListFilesResponse",
    "AttributionSourceId",
    "BatchEmbedContentsRequest",
    "BatchEmbedContentsResponse",
    "Candidate",
    "ContentEmbedding",
    "CountTokensRequest",
    "CountTokensResponse",
    "EmbedContentRequest",
    "EmbedContentResponse",
    "GenerateAnswerRequest",
    "GenerateAnswerResponse",
    "GenerateContentRequest",
    "GenerateContentResponse",
    "GenerationConfig",
    "GroundingAttribution",
    "SemanticRetrieverConfig",
    "TaskType",
    "Model",
    "CreateTunedModelMetadata",
    "CreateTunedModelRequest",
    "DeleteTunedModelRequest",
    "GetModelRequest",
    "GetTunedModelRequest",
    "ListModelsRequest",
    "ListModelsResponse",
    "ListTunedModelsRequest",
    "ListTunedModelsResponse",
    "UpdateTunedModelRequest",
    "Permission",
    "CreatePermissionRequest",
    "DeletePermissionRequest",
    "GetPermissionRequest",
    "ListPermissionsRequest",
    "ListPermissionsResponse",
    "TransferOwnershipRequest",
    "TransferOwnershipResponse",
    "UpdatePermissionRequest",
    "Chunk",
    "ChunkData",
    "Condition",
    "Corpus",
    "CustomMetadata",
    "Document",
    "MetadataFilter",
    "StringList",
    "BatchCreateChunksRequest",
    "BatchCreateChunksResponse",
    "BatchDeleteChunksRequest",
    "BatchUpdateChunksRequest",
    "BatchUpdateChunksResponse",
    "CreateChunkRequest",
    "CreateCorpusRequest",
    "CreateDocumentRequest",
    "DeleteChunkRequest",
    "DeleteCorpusRequest",
    "DeleteDocumentRequest",
    "GetChunkRequest",
    "GetCorpusRequest",
    "GetDocumentRequest",
    "ListChunksRequest",
    "ListChunksResponse",
    "ListCorporaRequest",
    "ListCorporaResponse",
    "ListDocumentsRequest",
    "ListDocumentsResponse",
    "QueryCorpusRequest",
    "QueryCorpusResponse",
    "QueryDocumentRequest",
    "QueryDocumentResponse",
    "RelevantChunk",
    "UpdateChunkRequest",
    "UpdateCorpusRequest",
    "UpdateDocumentRequest",
    "ContentFilter",
    "SafetyFeedback",
    "SafetyRating",
    "SafetySetting",
    "HarmCategory",
    "BatchEmbedTextRequest",
    "BatchEmbedTextResponse",
    "CountTextTokensRequest",
    "CountTextTokensResponse",
    "Embedding",
    "EmbedTextRequest",
    "EmbedTextResponse",
    "GenerateTextRequest",
    "GenerateTextResponse",
    "TextCompletion",
    "TextPrompt",
    "Dataset",
    "Hyperparameters",
    "TunedModel",
    "TunedModelSource",
    "TuningExample",
    "TuningExamples",
    "TuningSnapshot",
    "TuningTask",
)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\truststore\_api.py ===
import os
import platform
import socket
import ssl
import sys
import typing

import _ssl  # type: ignore[import-not-found]

from ._ssl_constants import (
    _original_SSLContext,
    _original_super_SSLContext,
    _truststore_SSLContext_dunder_class,
    _truststore_SSLContext_super_class,
)

if platform.system() == "Windows":
    from ._windows import _configure_context, _verify_peercerts_impl
elif platform.system() == "Darwin":
    from ._macos import _configure_context, _verify_peercerts_impl
else:
    from ._openssl import _configure_context, _verify_peercerts_impl

if typing.TYPE_CHECKING:
    from pip._vendor.typing_extensions import Buffer

# From typeshed/stdlib/ssl.pyi
_StrOrBytesPath: typing.TypeAlias = str | bytes | os.PathLike[str] | os.PathLike[bytes]
_PasswordType: typing.TypeAlias = str | bytes | typing.Callable[[], str | bytes]


def inject_into_ssl() -> None:
    """Injects the :class:`truststore.SSLContext` into the ``ssl``
    module by replacing :class:`ssl.SSLContext`.
    """
    setattr(ssl, "SSLContext", SSLContext)
    # urllib3 holds on to its own reference of ssl.SSLContext
    # so we need to replace that reference too.
    try:
        import pip._vendor.urllib3.util.ssl_ as urllib3_ssl

        setattr(urllib3_ssl, "SSLContext", SSLContext)
    except ImportError:
        pass


def extract_from_ssl() -> None:
    """Restores the :class:`ssl.SSLContext` class to its original state"""
    setattr(ssl, "SSLContext", _original_SSLContext)
    try:
        import pip._vendor.urllib3.util.ssl_ as urllib3_ssl

        urllib3_ssl.SSLContext = _original_SSLContext  # type: ignore[assignment]
    except ImportError:
        pass


class SSLContext(_truststore_SSLContext_super_class):  # type: ignore[misc]
    """SSLContext API that uses system certificates on all platforms"""

    @property  # type: ignore[misc]
    def __class__(self) -> type:
        # Dirty hack to get around isinstance() checks
        # for ssl.SSLContext instances in aiohttp/trustme
        # when using non-CPython implementations.
        return _truststore_SSLContext_dunder_class or SSLContext

    def __init__(self, protocol: int = None) -> None:  # type: ignore[assignment]
        self._ctx = _original_SSLContext(protocol)

        class TruststoreSSLObject(ssl.SSLObject):
            # This object exists because wrap_bio() doesn't
            # immediately do the handshake so we need to do
            # certificate verifications after SSLObject.do_handshake()

            def do_handshake(self) -> None:
                ret = super().do_handshake()
                _verify_peercerts(self, server_hostname=self.server_hostname)
                return ret

        self._ctx.sslobject_class = TruststoreSSLObject

    def wrap_socket(
        self,
        sock: socket.socket,
        server_side: bool = False,
        do_handshake_on_connect: bool = True,
        suppress_ragged_eofs: bool = True,
        server_hostname: str | None = None,
        session: ssl.SSLSession | None = None,
    ) -> ssl.SSLSocket:
        # Use a context manager here because the
        # inner SSLContext holds on to our state
        # but also does the actual handshake.
        with _configure_context(self._ctx):
            ssl_sock = self._ctx.wrap_socket(
                sock,
                server_side=server_side,
                server_hostname=server_hostname,
                do_handshake_on_connect=do_handshake_on_connect,
                suppress_ragged_eofs=suppress_ragged_eofs,
                session=session,
            )
        try:
            _verify_peercerts(ssl_sock, server_hostname=server_hostname)
        except Exception:
            ssl_sock.close()
            raise
        return ssl_sock

    def wrap_bio(
        self,
        incoming: ssl.MemoryBIO,
        outgoing: ssl.MemoryBIO,
        server_side: bool = False,
        server_hostname: str | None = None,
        session: ssl.SSLSession | None = None,
    ) -> ssl.SSLObject:
        with _configure_context(self._ctx):
            ssl_obj = self._ctx.wrap_bio(
                incoming,
                outgoing,
                server_hostname=server_hostname,
                server_side=server_side,
                session=session,
            )
        return ssl_obj

    def load_verify_locations(
        self,
        cafile: str | bytes | os.PathLike[str] | os.PathLike[bytes] | None = None,
        capath: str | bytes | os.PathLike[str] | os.PathLike[bytes] | None = None,
        cadata: typing.Union[str, "Buffer", None] = None,
    ) -> None:
        return self._ctx.load_verify_locations(
            cafile=cafile, capath=capath, cadata=cadata
        )

    def load_cert_chain(
        self,
        certfile: _StrOrBytesPath,
        keyfile: _StrOrBytesPath | None = None,
        password: _PasswordType | None = None,
    ) -> None:
        return self._ctx.load_cert_chain(
            certfile=certfile, keyfile=keyfile, password=password
        )

    def load_default_certs(
        self, purpose: ssl.Purpose = ssl.Purpose.SERVER_AUTH
    ) -> None:
        return self._ctx.load_default_certs(purpose)

    def set_alpn_protocols(self, alpn_protocols: typing.Iterable[str]) -> None:
        return self._ctx.set_alpn_protocols(alpn_protocols)

    def set_npn_protocols(self, npn_protocols: typing.Iterable[str]) -> None:
        return self._ctx.set_npn_protocols(npn_protocols)

    def set_ciphers(self, __cipherlist: str) -> None:
        return self._ctx.set_ciphers(__cipherlist)

    def get_ciphers(self) -> typing.Any:
        return self._ctx.get_ciphers()

    def session_stats(self) -> dict[str, int]:
        return self._ctx.session_stats()

    def cert_store_stats(self) -> dict[str, int]:
        raise NotImplementedError()

    def set_default_verify_paths(self) -> None:
        self._ctx.set_default_verify_paths()

    @typing.overload
    def get_ca_certs(
        self, binary_form: typing.Literal[False] = ...
    ) -> list[typing.Any]: ...

    @typing.overload
    def get_ca_certs(self, binary_form: typing.Literal[True] = ...) -> list[bytes]: ...

    @typing.overload
    def get_ca_certs(self, binary_form: bool = ...) -> typing.Any: ...

    def get_ca_certs(self, binary_form: bool = False) -> list[typing.Any] | list[bytes]:
        raise NotImplementedError()

    @property
    def check_hostname(self) -> bool:
        return self._ctx.check_hostname

    @check_hostname.setter
    def check_hostname(self, value: bool) -> None:
        self._ctx.check_hostname = value

    @property
    def hostname_checks_common_name(self) -> bool:
        return self._ctx.hostname_checks_common_name

    @hostname_checks_common_name.setter
    def hostname_checks_common_name(self, value: bool) -> None:
        self._ctx.hostname_checks_common_name = value

    @property
    def keylog_filename(self) -> str:
        return self._ctx.keylog_filename

    @keylog_filename.setter
    def keylog_filename(self, value: str) -> None:
        self._ctx.keylog_filename = value

    @property
    def maximum_version(self) -> ssl.TLSVersion:
        return self._ctx.maximum_version

    @maximum_version.setter
    def maximum_version(self, value: ssl.TLSVersion) -> None:
        _original_super_SSLContext.maximum_version.__set__(  # type: ignore[attr-defined]
            self._ctx, value
        )

    @property
    def minimum_version(self) -> ssl.TLSVersion:
        return self._ctx.minimum_version

    @minimum_version.setter
    def minimum_version(self, value: ssl.TLSVersion) -> None:
        _original_super_SSLContext.minimum_version.__set__(  # type: ignore[attr-defined]
            self._ctx, value
        )

    @property
    def options(self) -> ssl.Options:
        return self._ctx.options

    @options.setter
    def options(self, value: ssl.Options) -> None:
        _original_super_SSLContext.options.__set__(  # type: ignore[attr-defined]
            self._ctx, value
        )

    @property
    def post_handshake_auth(self) -> bool:
        return self._ctx.post_handshake_auth

    @post_handshake_auth.setter
    def post_handshake_auth(self, value: bool) -> None:
        self._ctx.post_handshake_auth = value

    @property
    def protocol(self) -> ssl._SSLMethod:
        return self._ctx.protocol

    @property
    def security_level(self) -> int:
        return self._ctx.security_level

    @property
    def verify_flags(self) -> ssl.VerifyFlags:
        return self._ctx.verify_flags

    @verify_flags.setter
    def verify_flags(self, value: ssl.VerifyFlags) -> None:
        _original_super_SSLContext.verify_flags.__set__(  # type: ignore[attr-defined]
            self._ctx, value
        )

    @property
    def verify_mode(self) -> ssl.VerifyMode:
        return self._ctx.verify_mode

    @verify_mode.setter
    def verify_mode(self, value: ssl.VerifyMode) -> None:
        _original_super_SSLContext.verify_mode.__set__(  # type: ignore[attr-defined]
            self._ctx, value
        )


# Python 3.13+ makes get_unverified_chain() a public API that only returns DER
# encoded certificates. We detect whether we need to call public_bytes() for 3.10->3.12
# Pre-3.13 returned None instead of an empty list from get_unverified_chain()
if sys.version_info >= (3, 13):

    def _get_unverified_chain_bytes(sslobj: ssl.SSLObject) -> list[bytes]:
        unverified_chain = sslobj.get_unverified_chain() or ()  # type: ignore[attr-defined]
        return [
            cert if isinstance(cert, bytes) else cert.public_bytes(_ssl.ENCODING_DER)
            for cert in unverified_chain
        ]

else:

    def _get_unverified_chain_bytes(sslobj: ssl.SSLObject) -> list[bytes]:
        unverified_chain = sslobj.get_unverified_chain() or ()  # type: ignore[attr-defined]
        return [cert.public_bytes(_ssl.ENCODING_DER) for cert in unverified_chain]


def _verify_peercerts(
    sock_or_sslobj: ssl.SSLSocket | ssl.SSLObject, server_hostname: str | None
) -> None:
    """
    Verifies the peer certificates from an SSLSocket or SSLObject
    against the certificates in the OS trust store.
    """
    sslobj: ssl.SSLObject = sock_or_sslobj  # type: ignore[assignment]
    try:
        while not hasattr(sslobj, "get_unverified_chain"):
            sslobj = sslobj._sslobj  # type: ignore[attr-defined]
    except AttributeError:
        pass

    cert_bytes = _get_unverified_chain_bytes(sslobj)
    _verify_peercerts_impl(
        sock_or_sslobj.context, cert_bytes, server_hostname=server_hostname
    )

# === NexusCore/openenv\Lib\site-packages\gitdb\base.py ===
# Copyright (C) 2010, 2011 Sebastian Thiel (byronimo@gmail.com) and contributors
#
# This module is part of GitDB and is released under
# the New BSD License: https://opensource.org/license/bsd-3-clause/
"""Module with basic data structures - they are designed to be lightweight and fast"""
from gitdb.util import bin_to_hex

from gitdb.fun import (
    type_id_to_type_map,
    type_to_type_id_map
)

__all__ = ('OInfo', 'OPackInfo', 'ODeltaPackInfo',
           'OStream', 'OPackStream', 'ODeltaPackStream',
           'IStream', 'InvalidOInfo', 'InvalidOStream')

#{ ODB Bases


class OInfo(tuple):

    """Carries information about an object in an ODB, providing information
    about the binary sha of the object, the type_string as well as the uncompressed size
    in bytes.

    It can be accessed using tuple notation and using attribute access notation::

        assert dbi[0] == dbi.binsha
        assert dbi[1] == dbi.type
        assert dbi[2] == dbi.size

    The type is designed to be as lightweight as possible."""
    __slots__ = tuple()

    def __new__(cls, sha, type, size):
        return tuple.__new__(cls, (sha, type, size))

    def __init__(self, *args):
        tuple.__init__(self)

    #{ Interface
    @property
    def binsha(self):
        """:return: our sha as binary, 20 bytes"""
        return self[0]

    @property
    def hexsha(self):
        """:return: our sha, hex encoded, 40 bytes"""
        return bin_to_hex(self[0])

    @property
    def type(self):
        return self[1]

    @property
    def type_id(self):
        return type_to_type_id_map[self[1]]

    @property
    def size(self):
        return self[2]
    #} END interface


class OPackInfo(tuple):

    """As OInfo, but provides a type_id property to retrieve the numerical type id, and
    does not include a sha.

    Additionally, the pack_offset is the absolute offset into the packfile at which
    all object information is located. The data_offset property points to the absolute
    location in the pack at which that actual data stream can be found."""
    __slots__ = tuple()

    def __new__(cls, packoffset, type, size):
        return tuple.__new__(cls, (packoffset, type, size))

    def __init__(self, *args):
        tuple.__init__(self)

    #{ Interface

    @property
    def pack_offset(self):
        return self[0]

    @property
    def type(self):
        return type_id_to_type_map[self[1]]

    @property
    def type_id(self):
        return self[1]

    @property
    def size(self):
        return self[2]

    #} END interface


class ODeltaPackInfo(OPackInfo):

    """Adds delta specific information,
    Either the 20 byte sha which points to some object in the database,
    or the negative offset from the pack_offset, so that pack_offset - delta_info yields
    the pack offset of the base object"""
    __slots__ = tuple()

    def __new__(cls, packoffset, type, size, delta_info):
        return tuple.__new__(cls, (packoffset, type, size, delta_info))

    #{ Interface
    @property
    def delta_info(self):
        return self[3]
    #} END interface


class OStream(OInfo):

    """Base for object streams retrieved from the database, providing additional
    information about the stream.
    Generally, ODB streams are read-only as objects are immutable"""
    __slots__ = tuple()

    def __new__(cls, sha, type, size, stream, *args, **kwargs):
        """Helps with the initialization of subclasses"""
        return tuple.__new__(cls, (sha, type, size, stream))

    def __init__(self, *args, **kwargs):
        tuple.__init__(self)

    #{ Stream Reader Interface

    def read(self, size=-1):
        return self[3].read(size)

    @property
    def stream(self):
        return self[3]

    #} END stream reader interface


class ODeltaStream(OStream):

    """Uses size info of its stream, delaying reads"""

    def __new__(cls, sha, type, size, stream, *args, **kwargs):
        """Helps with the initialization of subclasses"""
        return tuple.__new__(cls, (sha, type, size, stream))

    #{ Stream Reader Interface

    @property
    def size(self):
        return self[3].size

    #} END stream reader interface


class OPackStream(OPackInfo):

    """Next to pack object information, a stream outputting an undeltified base object
    is provided"""
    __slots__ = tuple()

    def __new__(cls, packoffset, type, size, stream, *args):
        """Helps with the initialization of subclasses"""
        return tuple.__new__(cls, (packoffset, type, size, stream))

    #{ Stream Reader Interface
    def read(self, size=-1):
        return self[3].read(size)

    @property
    def stream(self):
        return self[3]
    #} END stream reader interface


class ODeltaPackStream(ODeltaPackInfo):

    """Provides a stream outputting the uncompressed offset delta information"""
    __slots__ = tuple()

    def __new__(cls, packoffset, type, size, delta_info, stream):
        return tuple.__new__(cls, (packoffset, type, size, delta_info, stream))

    #{ Stream Reader Interface
    def read(self, size=-1):
        return self[4].read(size)

    @property
    def stream(self):
        return self[4]
    #} END stream reader interface


class IStream(list):

    """Represents an input content stream to be fed into the ODB. It is mutable to allow
    the ODB to record information about the operations outcome right in this instance.

    It provides interfaces for the OStream and a StreamReader to allow the instance
    to blend in without prior conversion.

    The only method your content stream must support is 'read'"""
    __slots__ = tuple()

    def __new__(cls, type, size, stream, sha=None):
        return list.__new__(cls, (sha, type, size, stream, None))

    def __init__(self, type, size, stream, sha=None):
        list.__init__(self, (sha, type, size, stream, None))

    #{ Interface
    @property
    def hexsha(self):
        """:return: our sha, hex encoded, 40 bytes"""
        return bin_to_hex(self[0])

    def _error(self):
        """:return: the error that occurred when processing the stream, or None"""
        return self[4]

    def _set_error(self, exc):
        """Set this input stream to the given exc, may be None to reset the error"""
        self[4] = exc

    error = property(_error, _set_error)

    #} END interface

    #{ Stream Reader Interface

    def read(self, size=-1):
        """Implements a simple stream reader interface, passing the read call on
            to our internal stream"""
        return self[3].read(size)

    #} END stream reader interface

    #{  interface

    def _set_binsha(self, binsha):
        self[0] = binsha

    def _binsha(self):
        return self[0]

    binsha = property(_binsha, _set_binsha)

    def _type(self):
        return self[1]

    def _set_type(self, type):
        self[1] = type

    type = property(_type, _set_type)

    def _size(self):
        return self[2]

    def _set_size(self, size):
        self[2] = size

    size = property(_size, _set_size)

    def _stream(self):
        return self[3]

    def _set_stream(self, stream):
        self[3] = stream

    stream = property(_stream, _set_stream)

    #} END odb info interface


class InvalidOInfo(tuple):

    """Carries information about a sha identifying an object which is invalid in
    the queried database. The exception attribute provides more information about
    the cause of the issue"""
    __slots__ = tuple()

    def __new__(cls, sha, exc):
        return tuple.__new__(cls, (sha, exc))

    def __init__(self, sha, exc):
        tuple.__init__(self, (sha, exc))

    @property
    def binsha(self):
        return self[0]

    @property
    def hexsha(self):
        return bin_to_hex(self[0])

    @property
    def error(self):
        """:return: exception instance explaining the failure"""
        return self[1]


class InvalidOStream(InvalidOInfo):

    """Carries information about an invalid ODB stream"""
    __slots__ = tuple()

#} END ODB Bases

# === NexusCore/openenv\Lib\site-packages\googleapiclient\channel.py ===
# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Channel notifications support.

Classes and functions to support channel subscriptions and notifications
on those channels.

Notes:
  - This code is based on experimental APIs and is subject to change.
  - Notification does not do deduplication of notification ids, that's up to
    the receiver.
  - Storing the Channel between calls is up to the caller.


Example setting up a channel:

  # Create a new channel that gets notifications via webhook.
  channel = new_webhook_channel("https://example.com/my_web_hook")

  # Store the channel, keyed by 'channel.id'. Store it before calling the
  # watch method because notifications may start arriving before the watch
  # method returns.
  ...

  resp = service.objects().watchAll(
    bucket="some_bucket_id", body=channel.body()).execute()
  channel.update(resp)

  # Store the channel, keyed by 'channel.id'. Store it after being updated
  # since the resource_id value will now be correct, and that's needed to
  # stop a subscription.
  ...


An example Webhook implementation using webapp2. Note that webapp2 puts
headers in a case insensitive dictionary, as headers aren't guaranteed to
always be upper case.

  id = self.request.headers[X_GOOG_CHANNEL_ID]

  # Retrieve the channel by id.
  channel = ...

  # Parse notification from the headers, including validating the id.
  n = notification_from_headers(channel, self.request.headers)

  # Do app specific stuff with the notification here.
  if n.resource_state == 'sync':
    # Code to handle sync state.
  elif n.resource_state == 'exists':
    # Code to handle the exists state.
  elif n.resource_state == 'not_exists':
    # Code to handle the not exists state.


Example of unsubscribing.

  service.channels().stop(channel.body()).execute()
"""
from __future__ import absolute_import

import datetime
import uuid

from googleapiclient import _helpers as util
from googleapiclient import errors

# The unix time epoch starts at midnight 1970.
EPOCH = datetime.datetime(1970, 1, 1)

# Map the names of the parameters in the JSON channel description to
# the parameter names we use in the Channel class.
CHANNEL_PARAMS = {
    "address": "address",
    "id": "id",
    "expiration": "expiration",
    "params": "params",
    "resourceId": "resource_id",
    "resourceUri": "resource_uri",
    "type": "type",
    "token": "token",
}

X_GOOG_CHANNEL_ID = "X-GOOG-CHANNEL-ID"
X_GOOG_MESSAGE_NUMBER = "X-GOOG-MESSAGE-NUMBER"
X_GOOG_RESOURCE_STATE = "X-GOOG-RESOURCE-STATE"
X_GOOG_RESOURCE_URI = "X-GOOG-RESOURCE-URI"
X_GOOG_RESOURCE_ID = "X-GOOG-RESOURCE-ID"


def _upper_header_keys(headers):
    new_headers = {}
    for k, v in headers.items():
        new_headers[k.upper()] = v
    return new_headers


class Notification(object):
    """A Notification from a Channel.

    Notifications are not usually constructed directly, but are returned
    from functions like notification_from_headers().

    Attributes:
      message_number: int, The unique id number of this notification.
      state: str, The state of the resource being monitored.
      uri: str, The address of the resource being monitored.
      resource_id: str, The unique identifier of the version of the resource at
        this event.
    """

    @util.positional(5)
    def __init__(self, message_number, state, resource_uri, resource_id):
        """Notification constructor.

        Args:
          message_number: int, The unique id number of this notification.
          state: str, The state of the resource being monitored. Can be one
            of "exists", "not_exists", or "sync".
          resource_uri: str, The address of the resource being monitored.
          resource_id: str, The identifier of the watched resource.
        """
        self.message_number = message_number
        self.state = state
        self.resource_uri = resource_uri
        self.resource_id = resource_id


class Channel(object):
    """A Channel for notifications.

    Usually not constructed directly, instead it is returned from helper
    functions like new_webhook_channel().

    Attributes:
      type: str, The type of delivery mechanism used by this channel. For
        example, 'web_hook'.
      id: str, A UUID for the channel.
      token: str, An arbitrary string associated with the channel that
        is delivered to the target address with each event delivered
        over this channel.
      address: str, The address of the receiving entity where events are
        delivered. Specific to the channel type.
      expiration: int, The time, in milliseconds from the epoch, when this
        channel will expire.
      params: dict, A dictionary of string to string, with additional parameters
        controlling delivery channel behavior.
      resource_id: str, An opaque id that identifies the resource that is
        being watched. Stable across different API versions.
      resource_uri: str, The canonicalized ID of the watched resource.
    """

    @util.positional(5)
    def __init__(
        self,
        type,
        id,
        token,
        address,
        expiration=None,
        params=None,
        resource_id="",
        resource_uri="",
    ):
        """Create a new Channel.

        In user code, this Channel constructor will not typically be called
        manually since there are functions for creating channels for each specific
        type with a more customized set of arguments to pass.

        Args:
          type: str, The type of delivery mechanism used by this channel. For
            example, 'web_hook'.
          id: str, A UUID for the channel.
          token: str, An arbitrary string associated with the channel that
            is delivered to the target address with each event delivered
            over this channel.
          address: str,  The address of the receiving entity where events are
            delivered. Specific to the channel type.
          expiration: int, The time, in milliseconds from the epoch, when this
            channel will expire.
          params: dict, A dictionary of string to string, with additional parameters
            controlling delivery channel behavior.
          resource_id: str, An opaque id that identifies the resource that is
            being watched. Stable across different API versions.
          resource_uri: str, The canonicalized ID of the watched resource.
        """
        self.type = type
        self.id = id
        self.token = token
        self.address = address
        self.expiration = expiration
        self.params = params
        self.resource_id = resource_id
        self.resource_uri = resource_uri

    def body(self):
        """Build a body from the Channel.

        Constructs a dictionary that's appropriate for passing into watch()
        methods as the value of body argument.

        Returns:
          A dictionary representation of the channel.
        """
        result = {
            "id": self.id,
            "token": self.token,
            "type": self.type,
            "address": self.address,
        }
        if self.params:
            result["params"] = self.params
        if self.resource_id:
            result["resourceId"] = self.resource_id
        if self.resource_uri:
            result["resourceUri"] = self.resource_uri
        if self.expiration:
            result["expiration"] = self.expiration

        return result

    def update(self, resp):
        """Update a channel with information from the response of watch().

        When a request is sent to watch() a resource, the response returned
        from the watch() request is a dictionary with updated channel information,
        such as the resource_id, which is needed when stopping a subscription.

        Args:
          resp: dict, The response from a watch() method.
        """
        for json_name, param_name in CHANNEL_PARAMS.items():
            value = resp.get(json_name)
            if value is not None:
                setattr(self, param_name, value)


def notification_from_headers(channel, headers):
    """Parse a notification from the webhook request headers, validate
      the notification, and return a Notification object.

    Args:
      channel: Channel, The channel that the notification is associated with.
      headers: dict, A dictionary like object that contains the request headers
        from the webhook HTTP request.

    Returns:
      A Notification object.

    Raises:
      errors.InvalidNotificationError if the notification is invalid.
      ValueError if the X-GOOG-MESSAGE-NUMBER can't be converted to an int.
    """
    headers = _upper_header_keys(headers)
    channel_id = headers[X_GOOG_CHANNEL_ID]
    if channel.id != channel_id:
        raise errors.InvalidNotificationError(
            "Channel id mismatch: %s != %s" % (channel.id, channel_id)
        )
    else:
        message_number = int(headers[X_GOOG_MESSAGE_NUMBER])
        state = headers[X_GOOG_RESOURCE_STATE]
        resource_uri = headers[X_GOOG_RESOURCE_URI]
        resource_id = headers[X_GOOG_RESOURCE_ID]
        return Notification(message_number, state, resource_uri, resource_id)


@util.positional(2)
def new_webhook_channel(url, token=None, expiration=None, params=None):
    """Create a new webhook Channel.

    Args:
      url: str, URL to post notifications to.
      token: str, An arbitrary string associated with the channel that
        is delivered to the target address with each notification delivered
        over this channel.
      expiration: datetime.datetime, A time in the future when the channel
        should expire. Can also be None if the subscription should use the
        default expiration. Note that different services may have different
        limits on how long a subscription lasts. Check the response from the
        watch() method to see the value the service has set for an expiration
        time.
      params: dict, Extra parameters to pass on channel creation. Currently
        not used for webhook channels.
    """
    expiration_ms = 0
    if expiration:
        delta = expiration - EPOCH
        expiration_ms = (
            delta.microseconds / 1000 + (delta.seconds + delta.days * 24 * 3600) * 1000
        )
        if expiration_ms < 0:
            expiration_ms = 0

    return Channel(
        "web_hook",
        str(uuid.uuid4()),
        token,
        url,
        expiration=expiration_ms,
        params=params,
    )

# === NexusCore/openenv\Lib\site-packages\wsproto\extensions.py ===
"""
wsproto/extensions
~~~~~~~~~~~~~~~~~~

WebSocket extensions.
"""

import zlib
from typing import Optional, Tuple, Union

from .frame_protocol import CloseReason, FrameDecoder, FrameProtocol, Opcode, RsvBits


class Extension:
    name: str

    def enabled(self) -> bool:
        return False

    def offer(self) -> Union[bool, str]:
        pass

    def accept(self, offer: str) -> Optional[Union[bool, str]]:
        pass

    def finalize(self, offer: str) -> None:
        pass

    def frame_inbound_header(
        self,
        proto: Union[FrameDecoder, FrameProtocol],
        opcode: Opcode,
        rsv: RsvBits,
        payload_length: int,
    ) -> Union[CloseReason, RsvBits]:
        return RsvBits(False, False, False)

    def frame_inbound_payload_data(
        self, proto: Union[FrameDecoder, FrameProtocol], data: bytes
    ) -> Union[bytes, CloseReason]:
        return data

    def frame_inbound_complete(
        self, proto: Union[FrameDecoder, FrameProtocol], fin: bool
    ) -> Union[bytes, CloseReason, None]:
        pass

    def frame_outbound(
        self,
        proto: Union[FrameDecoder, FrameProtocol],
        opcode: Opcode,
        rsv: RsvBits,
        data: bytes,
        fin: bool,
    ) -> Tuple[RsvBits, bytes]:
        return (rsv, data)


class PerMessageDeflate(Extension):
    name = "permessage-deflate"

    DEFAULT_CLIENT_MAX_WINDOW_BITS = 15
    DEFAULT_SERVER_MAX_WINDOW_BITS = 15

    def __init__(
        self,
        client_no_context_takeover: bool = False,
        client_max_window_bits: Optional[int] = None,
        server_no_context_takeover: bool = False,
        server_max_window_bits: Optional[int] = None,
    ) -> None:
        self.client_no_context_takeover = client_no_context_takeover
        self.server_no_context_takeover = server_no_context_takeover
        self._client_max_window_bits = self.DEFAULT_CLIENT_MAX_WINDOW_BITS
        self._server_max_window_bits = self.DEFAULT_SERVER_MAX_WINDOW_BITS
        if client_max_window_bits is not None:
            self.client_max_window_bits = client_max_window_bits
        if server_max_window_bits is not None:
            self.server_max_window_bits = server_max_window_bits

        self._compressor: Optional[zlib._Compress] = None  # noqa
        self._decompressor: Optional[zlib._Decompress] = None  # noqa
        # This refers to the current frame
        self._inbound_is_compressible: Optional[bool] = None
        # This refers to the ongoing message (which might span multiple
        # frames). Only the first frame in a fragmented message is flagged for
        # compression, so this carries that bit forward.
        self._inbound_compressed: Optional[bool] = None

        self._enabled = False

    @property
    def client_max_window_bits(self) -> int:
        return self._client_max_window_bits

    @client_max_window_bits.setter
    def client_max_window_bits(self, value: int) -> None:
        if value < 9 or value > 15:
            raise ValueError("Window size must be between 9 and 15 inclusive")
        self._client_max_window_bits = value

    @property
    def server_max_window_bits(self) -> int:
        return self._server_max_window_bits

    @server_max_window_bits.setter
    def server_max_window_bits(self, value: int) -> None:
        if value < 9 or value > 15:
            raise ValueError("Window size must be between 9 and 15 inclusive")
        self._server_max_window_bits = value

    def _compressible_opcode(self, opcode: Opcode) -> bool:
        return opcode in (Opcode.TEXT, Opcode.BINARY, Opcode.CONTINUATION)

    def enabled(self) -> bool:
        return self._enabled

    def offer(self) -> Union[bool, str]:
        parameters = [
            "client_max_window_bits=%d" % self.client_max_window_bits,
            "server_max_window_bits=%d" % self.server_max_window_bits,
        ]

        if self.client_no_context_takeover:
            parameters.append("client_no_context_takeover")
        if self.server_no_context_takeover:
            parameters.append("server_no_context_takeover")

        return "; ".join(parameters)

    def finalize(self, offer: str) -> None:
        bits = [b.strip() for b in offer.split(";")]
        for bit in bits[1:]:
            if bit.startswith("client_no_context_takeover"):
                self.client_no_context_takeover = True
            elif bit.startswith("server_no_context_takeover"):
                self.server_no_context_takeover = True
            elif bit.startswith("client_max_window_bits"):
                self.client_max_window_bits = int(bit.split("=", 1)[1].strip())
            elif bit.startswith("server_max_window_bits"):
                self.server_max_window_bits = int(bit.split("=", 1)[1].strip())

        self._enabled = True

    def _parse_params(self, params: str) -> Tuple[Optional[int], Optional[int]]:
        client_max_window_bits = None
        server_max_window_bits = None

        bits = [b.strip() for b in params.split(";")]
        for bit in bits[1:]:
            if bit.startswith("client_no_context_takeover"):
                self.client_no_context_takeover = True
            elif bit.startswith("server_no_context_takeover"):
                self.server_no_context_takeover = True
            elif bit.startswith("client_max_window_bits"):
                if "=" in bit:
                    client_max_window_bits = int(bit.split("=", 1)[1].strip())
                else:
                    client_max_window_bits = self.client_max_window_bits
            elif bit.startswith("server_max_window_bits"):
                if "=" in bit:
                    server_max_window_bits = int(bit.split("=", 1)[1].strip())
                else:
                    server_max_window_bits = self.server_max_window_bits

        return client_max_window_bits, server_max_window_bits

    def accept(self, offer: str) -> Union[bool, None, str]:
        client_max_window_bits, server_max_window_bits = self._parse_params(offer)

        parameters = []

        if self.client_no_context_takeover:
            parameters.append("client_no_context_takeover")
        if self.server_no_context_takeover:
            parameters.append("server_no_context_takeover")
        try:
            if client_max_window_bits is not None:
                parameters.append("client_max_window_bits=%d" % client_max_window_bits)
                self.client_max_window_bits = client_max_window_bits
            if server_max_window_bits is not None:
                parameters.append("server_max_window_bits=%d" % server_max_window_bits)
                self.server_max_window_bits = server_max_window_bits
        except ValueError:
            return None
        else:
            self._enabled = True
            return "; ".join(parameters)

    def frame_inbound_header(
        self,
        proto: Union[FrameDecoder, FrameProtocol],
        opcode: Opcode,
        rsv: RsvBits,
        payload_length: int,
    ) -> Union[CloseReason, RsvBits]:
        if rsv.rsv1 and opcode.iscontrol():
            return CloseReason.PROTOCOL_ERROR
        if rsv.rsv1 and opcode is Opcode.CONTINUATION:
            return CloseReason.PROTOCOL_ERROR

        self._inbound_is_compressible = self._compressible_opcode(opcode)

        if self._inbound_compressed is None:
            self._inbound_compressed = rsv.rsv1
            if self._inbound_compressed:
                assert self._inbound_is_compressible
                if proto.client:
                    bits = self.server_max_window_bits
                else:
                    bits = self.client_max_window_bits
                if self._decompressor is None:
                    self._decompressor = zlib.decompressobj(-int(bits))

        return RsvBits(True, False, False)

    def frame_inbound_payload_data(
        self, proto: Union[FrameDecoder, FrameProtocol], data: bytes
    ) -> Union[bytes, CloseReason]:
        if not self._inbound_compressed or not self._inbound_is_compressible:
            return data
        assert self._decompressor is not None

        try:
            return self._decompressor.decompress(bytes(data))
        except zlib.error:
            return CloseReason.INVALID_FRAME_PAYLOAD_DATA

    def frame_inbound_complete(
        self, proto: Union[FrameDecoder, FrameProtocol], fin: bool
    ) -> Union[bytes, CloseReason, None]:
        if not fin:
            return None
        if not self._inbound_is_compressible:
            self._inbound_compressed = None
            return None
        if not self._inbound_compressed:
            self._inbound_compressed = None
            return None
        assert self._decompressor is not None

        try:
            data = self._decompressor.decompress(b"\x00\x00\xff\xff")
            data += self._decompressor.flush()
        except zlib.error:
            return CloseReason.INVALID_FRAME_PAYLOAD_DATA

        if proto.client:
            no_context_takeover = self.server_no_context_takeover
        else:
            no_context_takeover = self.client_no_context_takeover

        if no_context_takeover:
            self._decompressor = None

        self._inbound_compressed = None

        return data

    def frame_outbound(
        self,
        proto: Union[FrameDecoder, FrameProtocol],
        opcode: Opcode,
        rsv: RsvBits,
        data: bytes,
        fin: bool,
    ) -> Tuple[RsvBits, bytes]:
        if not self._compressible_opcode(opcode):
            return (rsv, data)

        if opcode is not Opcode.CONTINUATION:
            rsv = RsvBits(True, *rsv[1:])

        if self._compressor is None:
            assert opcode is not Opcode.CONTINUATION
            if proto.client:
                bits = self.client_max_window_bits
            else:
                bits = self.server_max_window_bits
            self._compressor = zlib.compressobj(
                zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -int(bits)
            )

        data = self._compressor.compress(bytes(data))

        if fin:
            data += self._compressor.flush(zlib.Z_SYNC_FLUSH)
            data = data[:-4]

            if proto.client:
                no_context_takeover = self.client_no_context_takeover
            else:
                no_context_takeover = self.server_no_context_takeover

            if no_context_takeover:
                self._compressor = None

        return (rsv, data)

    def __repr__(self) -> str:
        descr = ["client_max_window_bits=%d" % self.client_max_window_bits]
        if self.client_no_context_takeover:
            descr.append("client_no_context_takeover")
        descr.append("server_max_window_bits=%d" % self.server_max_window_bits)
        if self.server_no_context_takeover:
            descr.append("server_no_context_takeover")

        return "<{} {}>".format(self.__class__.__name__, "; ".join(descr))


#: SUPPORTED_EXTENSIONS maps all supported extension names to their class.
#: This can be used to iterate all supported extensions of wsproto, instantiate
#: new extensions based on their name, or check if a given extension is
#: supported or not.
SUPPORTED_EXTENSIONS = {PerMessageDeflate.name: PerMessageDeflate}

# === NexusCore/openenv\Lib\site-packages\interpreter\core\llm\run_tool_calling_llm.py ===
import os
import re

from .utils.merge_deltas import merge_deltas
from .utils.parse_partial_json import parse_partial_json

tool_schema = {
    "type": "function",
    "function": {
        "name": "execute",
        "description": "Executes code on the user's machine **in the users local environment** and returns the output",
        "parameters": {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "description": "The programming language (required parameter to the `execute` function)",
                    "enum": [
                        # This will be filled dynamically with the languages OI has access to.
                    ],
                },
                "code": {
                    "type": "string",
                    "description": "The code to execute (required)",
                },
            },
            "required": ["language", "code"],
        },
    },
}


def process_messages(messages):
    processed_messages = []
    last_tool_id = 0

    i = 0
    while i < len(messages):
        message = messages[i]

        if message.get("function_call"):
            last_tool_id += 1
            tool_id = f"toolu_{last_tool_id}"

            # Convert function_call to tool_calls
            function = message.pop("function_call")
            message["tool_calls"] = [
                {"id": tool_id, "type": "function", "function": function}
            ]
            processed_messages.append(message)

            # Process the next message if it's a function response
            if i + 1 < len(messages) and messages[i + 1].get("role") == "function":
                next_message = messages[i + 1].copy()
                next_message["role"] = "tool"
                next_message["tool_call_id"] = tool_id
                processed_messages.append(next_message)
                i += 1  # Skip the next message as we've already processed it
            else:
                # Add an empty tool response if there isn't one
                processed_messages.append(
                    {"role": "tool", "tool_call_id": tool_id, "content": ""}
                )

        elif message.get("role") == "function":
            # This handles orphaned function responses
            last_tool_id += 1
            tool_id = f"toolu_{last_tool_id}"

            # Add a tool call before this orphaned tool response
            processed_messages.append(
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": "execute",
                                "arguments": "# Automated tool call to fetch more output, triggered by the user.",
                            },
                        }
                    ],
                }
            )

            # Process the function response
            message["role"] = "tool"
            message["tool_call_id"] = tool_id
            processed_messages.append(message)

        else:
            # For non-tool-related messages, just add them as is
            processed_messages.append(message)

        i += 1

    return processed_messages


def run_tool_calling_llm(llm, request_params):
    ## Setup

    # Add languages OI has access to
    tool_schema["function"]["parameters"]["properties"]["language"]["enum"] = [
        i.name.lower() for i in llm.interpreter.computer.terminal.languages
    ]
    request_params["tools"] = [tool_schema]

    request_params["messages"] = process_messages(request_params["messages"])

    # # This makes any role: tool have the ID of the last tool call
    # last_tool_id = 0
    # for i, message in enumerate(request_params["messages"]):
    #     if "function_call" in message:
    #         last_tool_id += 1
    #         function = message.pop("function_call")
    #         message["tool_calls"] = [
    #             {
    #                 "id": "toolu_" + str(last_tool_id),
    #                 "type": "function",
    #                 "function": function,
    #             }
    #         ]
    #     if message["role"] == "function":
    #         if i != 0 and request_params["messages"][i - 1]["role"] == "tool":
    #             request_params["messages"][i]["content"] += message["content"]
    #             message = None
    #         else:
    #             message["role"] = "tool"
    #             message["tool_call_id"] = "toolu_" + str(last_tool_id)
    # request_params["messages"] = [m for m in request_params["messages"] if m != None]

    # This adds an empty tool response for any tool call without a tool response
    # new_messages = []
    # for i, message in enumerate(request_params["messages"]):
    #     new_messages.append(message)
    #     if "tool_calls" in message:
    #         tool_call_id = message["tool_calls"][0]["id"]
    #         if not any(
    #             m
    #             for m in request_params["messages"]
    #             if m.get("role") == "tool" and m.get("tool_call_id") == tool_call_id
    #         ):
    #             new_messages.append(
    #                 {"role": "tool", "tool_call_id": tool_call_id, "content": ""}
    #             )
    # request_params["messages"] = new_messages

    # messages = request_params["messages"]
    # for i in range(len(messages)):
    #     if messages[i]["role"] == "user" and isinstance(messages[i]["content"], list):
    #         # Found an image from the user
    #         image_message = messages[i]
    #         j = i + 1
    #         while j < len(messages) and messages[j]["role"] == "tool":
    #             # Move the image down until it's after all the role: tools
    #             j += 1
    #         messages.insert(j, image_message)
    #         del messages[i]
    # request_params["messages"] = messages

    # Add OpenAI's recommended function message
    # request_params["messages"][0][
    #     "content"
    # ] += "\nUse ONLY the function you have been provided with — 'execute(language, code)'."

    ## Convert output to LMC format

    accumulated_deltas = {}
    language = None
    code = ""
    function_call_detected = False
    accumulated_review = ""
    review_category = None
    buffer = ""

    for chunk in llm.completions(**request_params):
        if "choices" not in chunk or len(chunk["choices"]) == 0:
            # This happens sometimes
            continue

        delta = chunk["choices"][0]["delta"]

        # Convert tool call into function call, which we have great parsing logic for below
        if "tool_calls" in delta and delta["tool_calls"]:
            function_call_detected = True

            # import pdb; pdb.set_trace()
            if len(delta["tool_calls"]) > 0 and delta["tool_calls"][0].function:
                delta = {
                    # "id": delta["tool_calls"][0],
                    "function_call": {
                        "name": delta["tool_calls"][0].function.name,
                        "arguments": delta["tool_calls"][0].function.arguments,
                    }
                }

        # Accumulate deltas
        accumulated_deltas = merge_deltas(accumulated_deltas, delta)

        if "content" in delta and delta["content"]:
            if function_call_detected:
                # More content after a code block? This is a code review by a judge layer.

                # print("Code safety review:", delta["content"])

                if review_category == None:
                    accumulated_review += delta["content"]

                    if "<unsafe>" in accumulated_review:
                        review_category = "unsafe"
                    if "<warning>" in accumulated_review:
                        review_category = "warning"
                    if "<safe>" in accumulated_review:
                        review_category = "safe"

                if review_category != None:
                    for tag in [
                        "<safe>",
                        "</safe>",
                        "<warning>",
                        "</warning>",
                        "<unsafe>",
                        "</unsafe>",
                    ]:
                        delta["content"] = delta["content"].replace(tag, "")

                    if re.search("</.*>$", accumulated_review):
                        buffer += delta["content"]
                        continue
                    elif buffer:
                        yield {
                            "type": "review",
                            "format": review_category,
                            "content": buffer + delta["content"],
                        }
                        buffer = ""
                    else:
                        yield {
                            "type": "review",
                            "format": review_category,
                            "content": delta["content"],
                        }
                        buffer = ""

            else:
                yield {"type": "message", "content": delta["content"]}

        if (
            accumulated_deltas.get("function_call")
            and "name" in accumulated_deltas["function_call"]
            and (
                accumulated_deltas["function_call"]["name"] == "python"
                or accumulated_deltas["function_call"]["name"] == "functions"
            )
        ):
            if language is None:
                language = "python"

            # Pull the code string straight out of the "arguments" string
            code_delta = accumulated_deltas["function_call"]["arguments"][len(code) :]
            # Update the code
            code = accumulated_deltas["function_call"]["arguments"]
            # Yield the delta
            if code_delta:
                yield {
                    "type": "code",
                    "format": language,
                    "content": code_delta,
                }

        if (
            accumulated_deltas.get("function_call")
            and "arguments" in accumulated_deltas["function_call"]
            and accumulated_deltas["function_call"]["arguments"]
        ):
            if "arguments" in accumulated_deltas["function_call"]:
                arguments = accumulated_deltas["function_call"]["arguments"]
                arguments = parse_partial_json(arguments)

                if arguments:
                    if (
                        language is None
                        and "language" in arguments
                        and "code"
                        in arguments  # <- This ensures we're *finished* typing language, as opposed to partially done
                        and arguments["language"]
                    ):
                        language = arguments["language"]

                    if language is not None and "code" in arguments:
                        # Calculate the delta (new characters only)
                        code_delta = arguments["code"][len(code) :]
                        # Update the code
                        code = arguments["code"]
                        # Yield the delta
                        if code_delta:
                            yield {
                                "type": "code",
                                "format": language,
                                "content": code_delta,
                            }
                else:
                    if llm.interpreter.verbose:
                        print("Arguments not a dict.")

    if os.getenv("INTERPRETER_REQUIRE_AUTHENTICATION", "False").lower() == "true":
        print("function_call_detected", function_call_detected)
        print("accumulated_review", accumulated_review)
        if function_call_detected and not accumulated_review:
            print("WTF!!!!!!!!!")
            # import pdb
            # pdb.set_trace()
            raise Exception("Judge layer required but did not run.")

# === NexusCore/openenv\Lib\site-packages\IPython\core\profileapp.py ===
# encoding: utf-8
"""
An application for managing IPython profiles.

To be invoked as the `ipython profile` subcommand.

Authors:

* Min RK

"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import os

from traitlets.config.application import Application
from IPython.core.application import (
    BaseIPythonApplication, base_flags
)
from IPython.core.profiledir import ProfileDir
from IPython.utils.importstring import import_item
from IPython.paths import get_ipython_dir, get_ipython_package_dir
from traitlets import Unicode, Bool, Dict, observe

#-----------------------------------------------------------------------------
# Constants
#-----------------------------------------------------------------------------

create_help = """Create an IPython profile by name

Create an ipython profile directory by its name or
profile directory path. Profile directories contain
configuration, log and security related files and are named
using the convention 'profile_<name>'. By default they are
located in your ipython directory. Once created, you will
can edit the configuration files in the profile
directory to configure IPython. Most users will create a
profile directory by name,
`ipython profile create myprofile`, which will put the directory
in `<ipython_dir>/profile_myprofile`.
"""
list_help = """List available IPython profiles

List all available profiles, by profile location, that can
be found in the current working directly or in the ipython
directory. Profile directories are named using the convention
'profile_<profile>'.
"""
profile_help = """Manage IPython profiles

Profile directories contain
configuration, log and security related files and are named
using the convention 'profile_<name>'. By default they are
located in your ipython directory.  You can create profiles
with `ipython profile create <name>`, or see the profiles you
already have with `ipython profile list`

To get started configuring IPython, simply do:

$> ipython profile create

and IPython will create the default profile in <ipython_dir>/profile_default,
where you can edit ipython_config.py to start configuring IPython.

"""

_list_examples = "ipython profile list  # list all profiles"

_create_examples = """
ipython profile create foo         # create profile foo w/ default config files
ipython profile create foo --reset # restage default config files over current
ipython profile create foo --parallel # also stage parallel config files
"""

_main_examples = """
ipython profile create -h  # show the help string for the create subcommand
ipython profile list -h    # show the help string for the list subcommand

ipython locate profile foo # print the path to the directory for profile 'foo'
"""

#-----------------------------------------------------------------------------
# Profile Application Class (for `ipython profile` subcommand)
#-----------------------------------------------------------------------------


def list_profiles_in(path):
    """list profiles in a given root directory"""
    profiles = []

    # for python 3.6+ rewrite to: with os.scandir(path) as dirlist:
    files = os.scandir(path)
    for f in files:
        if f.is_dir() and f.name.startswith('profile_'):
            profiles.append(f.name.split('_', 1)[-1])
    return profiles


def list_bundled_profiles():
    """list profiles that are bundled with IPython."""
    path = os.path.join(get_ipython_package_dir(), u'core', u'profile')
    profiles = []

    # for python 3.6+ rewrite to: with os.scandir(path) as dirlist:
    files =  os.scandir(path)
    for profile in files:
        if profile.is_dir() and profile.name != "__pycache__":
            profiles.append(profile.name)
    return profiles


class ProfileLocate(BaseIPythonApplication):
    description = """print the path to an IPython profile dir"""
    
    def parse_command_line(self, argv=None):
        super(ProfileLocate, self).parse_command_line(argv)
        if self.extra_args:
            self.profile = self.extra_args[0]
    
    def start(self):
        print(self.profile_dir.location)


class ProfileList(Application):
    name = u'ipython-profile'
    description = list_help
    examples = _list_examples

    aliases = Dict({
        'ipython-dir' : 'ProfileList.ipython_dir',
        'log-level' : 'Application.log_level',
    })
    flags = Dict(dict(
        debug = ({'Application' : {'log_level' : 0}},
            "Set Application.log_level to 0, maximizing log output."
        )
    ))

    ipython_dir = Unicode(get_ipython_dir(),
        help="""
        The name of the IPython directory. This directory is used for logging
        configuration (through profiles), history storage, etc. The default
        is usually $HOME/.ipython. This options can also be specified through
        the environment variable IPYTHONDIR.
        """
    ).tag(config=True)


    def _print_profiles(self, profiles):
        """print list of profiles, indented."""
        for profile in profiles:
            print('    %s' % profile)

    def list_profile_dirs(self):
        profiles = list_bundled_profiles()
        if profiles:
            print()
            print("Available profiles in IPython:")
            self._print_profiles(profiles)
            print()
            print("    The first request for a bundled profile will copy it")
            print("    into your IPython directory (%s)," % self.ipython_dir)
            print("    where you can customize it.")
        
        profiles = list_profiles_in(self.ipython_dir)
        if profiles:
            print()
            print("Available profiles in %s:" % self.ipython_dir)
            self._print_profiles(profiles)
        
        profiles = list_profiles_in(os.getcwd())
        if profiles:
            print()
            print(
                "Profiles from CWD have been removed for security reason, see CVE-2022-21699:"
            )

        print()
        print("To use any of the above profiles, start IPython with:")
        print("    ipython --profile=<name>")
        print()

    def start(self):
        self.list_profile_dirs()


create_flags = {}
create_flags.update(base_flags)
# don't include '--init' flag, which implies running profile create in other apps
create_flags.pop('init')
create_flags['reset'] = ({'ProfileCreate': {'overwrite' : True}},
                        "reset config files in this profile to the defaults.")
create_flags['parallel'] = ({'ProfileCreate': {'parallel' : True}},
                        "Include the config files for parallel "
                        "computing apps (ipengine, ipcontroller, etc.)")


class ProfileCreate(BaseIPythonApplication):
    name = u'ipython-profile'
    description = create_help
    examples = _create_examples
    auto_create = Bool(True).tag(config=True)
    def _log_format_default(self):
        return "[%(name)s] %(message)s"

    def _copy_config_files_default(self):
        return True

    parallel = Bool(False,
        help="whether to include parallel computing config files"
    ).tag(config=True)

    @observe('parallel')
    def _parallel_changed(self, change):
        parallel_files = [   'ipcontroller_config.py',
                            'ipengine_config.py',
                            'ipcluster_config.py'
                        ]
        if change['new']:
            for cf in parallel_files:
                self.config_files.append(cf)
        else:
            for cf in parallel_files:
                if cf in self.config_files:
                    self.config_files.remove(cf)

    def parse_command_line(self, argv):
        super(ProfileCreate, self).parse_command_line(argv)
        # accept positional arg as profile name
        if self.extra_args:
            self.profile = self.extra_args[0]

    flags = Dict(create_flags)

    classes = [ProfileDir]
    
    def _import_app(self, app_path):
        """import an app class"""
        app = None
        name = app_path.rsplit('.', 1)[-1]
        try:
            app = import_item(app_path)
        except ImportError:
            self.log.info("Couldn't import %s, config file will be excluded", name)
        except Exception:
            self.log.warning('Unexpected error importing %s', name, exc_info=True)
        return app

    def init_config_files(self):
        super(ProfileCreate, self).init_config_files()
        # use local imports, since these classes may import from here
        from IPython.terminal.ipapp import TerminalIPythonApp
        apps = [TerminalIPythonApp]
        for app_path in (
            'ipykernel.kernelapp.IPKernelApp',
        ):
            app = self._import_app(app_path)
            if app is not None:
                apps.append(app)
        if self.parallel:
            from ipyparallel.apps.ipcontrollerapp import IPControllerApp
            from ipyparallel.apps.ipengineapp import IPEngineApp
            from ipyparallel.apps.ipclusterapp import IPClusterStart
            apps.extend([
                IPControllerApp,
                IPEngineApp,
                IPClusterStart,
            ])
        for App in apps:
            app = App()
            app.config.update(self.config)
            app.log = self.log
            app.overwrite = self.overwrite
            app.copy_config_files=True
            app.ipython_dir=self.ipython_dir
            app.profile_dir=self.profile_dir
            app.init_config_files()

    def stage_default_config_file(self):
        pass


class ProfileApp(Application):
    name = u'ipython profile'
    description = profile_help
    examples = _main_examples

    subcommands = Dict(dict(
        create = (ProfileCreate, ProfileCreate.description.splitlines()[0]),
        list = (ProfileList, ProfileList.description.splitlines()[0]),
        locate = (ProfileLocate, ProfileLocate.description.splitlines()[0]),
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

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\auth\route_checks.py ===
import re
from typing import List, Optional

from fastapi import HTTPException, Request, status

from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import (
    CommonProxyErrors,
    LiteLLM_UserTable,
    LiteLLMRoutes,
    LitellmUserRoles,
    UserAPIKeyAuth,
)

from .auth_checks_organization import _user_is_org_admin


class RouteChecks:
    @staticmethod
    def is_virtual_key_allowed_to_call_route(
        route: str, valid_token: UserAPIKeyAuth
    ) -> bool:
        """
        Raises Exception if Virtual Key is not allowed to call the route
        """

        # Only check if valid_token.allowed_routes is set and is a list with at least one item
        if valid_token.allowed_routes is None:
            return True
        if not isinstance(valid_token.allowed_routes, list):
            return True
        if len(valid_token.allowed_routes) == 0:
            return True

        # explicit check for allowed routes
        if route in valid_token.allowed_routes:
            return True

        # check if wildcard pattern is allowed
        for allowed_route in valid_token.allowed_routes:
            if RouteChecks._route_matches_wildcard_pattern(
                route=route, pattern=allowed_route
            ):
                return True

        raise Exception(
            f"Virtual key is not allowed to call this route. Only allowed to call routes: {valid_token.allowed_routes}. Tried to call route: {route}"
        )

    @staticmethod
    def non_proxy_admin_allowed_routes_check(
        user_obj: Optional[LiteLLM_UserTable],
        _user_role: Optional[LitellmUserRoles],
        route: str,
        request: Request,
        valid_token: UserAPIKeyAuth,
        request_data: dict,
    ):
        """
        Checks if Non Proxy Admin User is allowed to access the route
        """

        # Check user has defined custom admin routes
        RouteChecks.custom_admin_only_route_check(
            route=route,
        )

        if RouteChecks.is_llm_api_route(route=route):
            pass
        elif (
            route in LiteLLMRoutes.info_routes.value
        ):  # check if user allowed to call an info route
            if route == "/key/info":
                # handled by function itself
                pass
            elif route == "/user/info":
                # check if user can access this route
                query_params = request.query_params
                user_id = query_params.get("user_id")
                verbose_proxy_logger.debug(
                    f"user_id: {user_id} & valid_token.user_id: {valid_token.user_id}"
                )
                if user_id and user_id != valid_token.user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="key not allowed to access this user's info. user_id={}, key's user_id={}".format(
                            user_id, valid_token.user_id
                        ),
                    )
            elif route == "/model/info":
                # /model/info just shows models user has access to
                pass
            elif route == "/team/info":
                pass  # handled by function itself
        elif (
            route in LiteLLMRoutes.global_spend_tracking_routes.value
            and getattr(valid_token, "permissions", None) is not None
            and "get_spend_routes" in getattr(valid_token, "permissions", [])
        ):
            pass
        elif _user_role == LitellmUserRoles.PROXY_ADMIN_VIEW_ONLY.value:
            if RouteChecks.is_llm_api_route(route=route):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"user not allowed to access this OpenAI routes, role= {_user_role}",
                )
            if RouteChecks.check_route_access(
                route=route, allowed_routes=LiteLLMRoutes.management_routes.value
            ):
                # the Admin Viewer is only allowed to call /user/update for their own user_id and can only update
                if route == "/user/update":
                    # Check the Request params are valid for PROXY_ADMIN_VIEW_ONLY
                    if request_data is not None and isinstance(request_data, dict):
                        _params_updated = request_data.keys()
                        for param in _params_updated:
                            if param not in ["user_email", "password"]:
                                raise HTTPException(
                                    status_code=status.HTTP_403_FORBIDDEN,
                                    detail=f"user not allowed to access this route, role= {_user_role}. Trying to access: {route} and updating invalid param: {param}. only user_email and password can be updated",
                                )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"user not allowed to access this route, role= {_user_role}. Trying to access: {route}",
                    )

        elif (
            _user_role == LitellmUserRoles.INTERNAL_USER.value
            and RouteChecks.check_route_access(
                route=route, allowed_routes=LiteLLMRoutes.internal_user_routes.value
            )
        ):
            pass
        elif _user_is_org_admin(
            request_data=request_data, user_object=user_obj
        ) and RouteChecks.check_route_access(
            route=route, allowed_routes=LiteLLMRoutes.org_admin_allowed_routes.value
        ):
            pass
        elif (
            _user_role == LitellmUserRoles.INTERNAL_USER_VIEW_ONLY.value
            and RouteChecks.check_route_access(
                route=route,
                allowed_routes=LiteLLMRoutes.internal_user_view_only_routes.value,
            )
        ):
            pass
        elif RouteChecks.check_route_access(
            route=route, allowed_routes=LiteLLMRoutes.self_managed_routes.value
        ):  # routes that manage their own allowed/disallowed logic
            pass
        elif route.startswith("/v1/mcp/"):
            pass  # authN/authZ handled by api itself
        else:
            user_role = "unknown"
            user_id = "unknown"
            if user_obj is not None:
                user_role = user_obj.user_role or "unknown"
                user_id = user_obj.user_id or "unknown"
            raise Exception(
                f"Only proxy admin can be used to generate, delete, update info for new keys/users/teams. Route={route}. Your role={user_role}. Your user_id={user_id}"
            )

    @staticmethod
    def custom_admin_only_route_check(route: str):
        from litellm.proxy.proxy_server import general_settings, premium_user

        if "admin_only_routes" in general_settings:
            if premium_user is not True:
                verbose_proxy_logger.error(
                    f"Trying to use 'admin_only_routes' this is an Enterprise only feature. {CommonProxyErrors.not_premium_user.value}"
                )
                return
            if route in general_settings["admin_only_routes"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"user not allowed to access this route. Route={route} is an admin only route",
                )
        pass

    @staticmethod
    def is_llm_api_route(route: str) -> bool:
        """
        Helper to checks if provided route is an OpenAI route


        Returns:
            - True: if route is an OpenAI route
            - False: if route is not an OpenAI route
        """

        if route in LiteLLMRoutes.openai_routes.value:
            return True

        if route in LiteLLMRoutes.anthropic_routes.value:
            return True

        # fuzzy match routes like "/v1/threads/thread_49EIN5QF32s4mH20M7GFKdlZ"
        # Check for routes with placeholders
        for openai_route in LiteLLMRoutes.openai_routes.value:
            # Replace placeholders with regex pattern
            # placeholders are written as "/threads/{thread_id}"
            if "{" in openai_route:
                if RouteChecks._route_matches_pattern(
                    route=route, pattern=openai_route
                ):
                    return True

        if RouteChecks._is_azure_openai_route(route=route):
            return True

        for _llm_passthrough_route in LiteLLMRoutes.mapped_pass_through_routes.value:
            if _llm_passthrough_route in route:
                return True

        return False

    @staticmethod
    def _is_azure_openai_route(route: str) -> bool:
        """
        Check if route is a route from AzureOpenAI SDK client

        eg.
        route='/openai/deployments/vertex_ai/gemini-1.5-flash/chat/completions'
        """
        # Add support for deployment and engine model paths
        deployment_pattern = r"^/openai/deployments/[^/]+/[^/]+/chat/completions$"
        engine_pattern = r"^/engines/[^/]+/chat/completions$"

        if re.match(deployment_pattern, route) or re.match(engine_pattern, route):
            return True
        return False

    @staticmethod
    def _route_matches_pattern(route: str, pattern: str) -> bool:
        """
        Check if route matches the pattern placed in proxy/_types.py

        Example:
        - pattern: "/threads/{thread_id}"
        - route: "/threads/thread_49EIN5QF32s4mH20M7GFKdlZ"
        - returns: True


        - pattern: "/key/{token_id}/regenerate"
        - route: "/key/regenerate/82akk800000000jjsk"
        - returns: False, pattern is "/key/{token_id}/regenerate"
        """
        pattern = re.sub(r"\{[^}]+\}", r"[^/]+", pattern)
        # Anchor the pattern to match the entire string
        pattern = f"^{pattern}$"
        if re.match(pattern, route):
            return True
        return False

    @staticmethod
    def _route_matches_wildcard_pattern(route: str, pattern: str) -> bool:
        """
        Check if route matches the wildcard pattern

        eg.

        pattern: "/scim/v2/*"
        route: "/scim/v2/Users"
        - returns: True

        pattern: "/scim/v2/*"
        route: "/chat/completions"
        - returns: False


        pattern: "/scim/v2/*"
        route: "/scim/v2/Users/123"
        - returns: True

        """
        if pattern.endswith("*"):
            # Get the prefix (everything before the wildcard)
            prefix = pattern[:-1]
            return route.startswith(prefix)
        else:
            # If there's no wildcard, the pattern and route should match exactly
            return route == pattern

    @staticmethod
    def check_route_access(route: str, allowed_routes: List[str]) -> bool:
        """
        Check if a route has access by checking both exact matches and patterns

        Args:
            route (str): The route to check
            allowed_routes (list): List of allowed routes/patterns

        Returns:
            bool: True if route is allowed, False otherwise
        """
        return route in allowed_routes or any(  # Check exact match
            RouteChecks._route_matches_pattern(route=route, pattern=allowed_route)
            for allowed_route in allowed_routes
        )  # Check pattern match

    @staticmethod
    def _is_assistants_api_request(request: Request) -> bool:
        """
        Returns True if `thread` or `assistant` is in the request path

        Args:
            request (Request): The request object

        Returns:
            bool: True if `thread` or `assistant` is in the request path, False otherwise
        """
        if "thread" in request.url.path or "assistant" in request.url.path:
            return True
        return False

# === NexusCore/openenv\Lib\site-packages\openai\resources\evals\runs\output_items.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing_extensions import Literal

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ....pagination import SyncCursorPage, AsyncCursorPage
from ...._base_client import AsyncPaginator, make_request_options
from ....types.evals.runs import output_item_list_params
from ....types.evals.runs.output_item_list_response import OutputItemListResponse
from ....types.evals.runs.output_item_retrieve_response import OutputItemRetrieveResponse

__all__ = ["OutputItems", "AsyncOutputItems"]


class OutputItems(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> OutputItemsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return OutputItemsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> OutputItemsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return OutputItemsWithStreamingResponse(self)

    def retrieve(
        self,
        output_item_id: str,
        *,
        eval_id: str,
        run_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> OutputItemRetrieveResponse:
        """
        Get an evaluation run output item by ID.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        if not output_item_id:
            raise ValueError(f"Expected a non-empty value for `output_item_id` but received {output_item_id!r}")
        return self._get(
            f"/evals/{eval_id}/runs/{run_id}/output_items/{output_item_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=OutputItemRetrieveResponse,
        )

    def list(
        self,
        run_id: str,
        *,
        eval_id: str,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        status: Literal["fail", "pass"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[OutputItemListResponse]:
        """
        Get a list of output items for an evaluation run.

        Args:
          after: Identifier for the last output item from the previous pagination request.

          limit: Number of output items to retrieve.

          order: Sort order for output items by timestamp. Use `asc` for ascending order or
              `desc` for descending order. Defaults to `asc`.

          status: Filter output items by status. Use `failed` to filter by failed output items or
              `pass` to filter by passed output items.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        return self._get_api_list(
            f"/evals/{eval_id}/runs/{run_id}/output_items",
            page=SyncCursorPage[OutputItemListResponse],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "order": order,
                        "status": status,
                    },
                    output_item_list_params.OutputItemListParams,
                ),
            ),
            model=OutputItemListResponse,
        )


class AsyncOutputItems(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncOutputItemsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncOutputItemsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncOutputItemsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncOutputItemsWithStreamingResponse(self)

    async def retrieve(
        self,
        output_item_id: str,
        *,
        eval_id: str,
        run_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> OutputItemRetrieveResponse:
        """
        Get an evaluation run output item by ID.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        if not output_item_id:
            raise ValueError(f"Expected a non-empty value for `output_item_id` but received {output_item_id!r}")
        return await self._get(
            f"/evals/{eval_id}/runs/{run_id}/output_items/{output_item_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=OutputItemRetrieveResponse,
        )

    def list(
        self,
        run_id: str,
        *,
        eval_id: str,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        status: Literal["fail", "pass"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[OutputItemListResponse, AsyncCursorPage[OutputItemListResponse]]:
        """
        Get a list of output items for an evaluation run.

        Args:
          after: Identifier for the last output item from the previous pagination request.

          limit: Number of output items to retrieve.

          order: Sort order for output items by timestamp. Use `asc` for ascending order or
              `desc` for descending order. Defaults to `asc`.

          status: Filter output items by status. Use `failed` to filter by failed output items or
              `pass` to filter by passed output items.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        return self._get_api_list(
            f"/evals/{eval_id}/runs/{run_id}/output_items",
            page=AsyncCursorPage[OutputItemListResponse],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "order": order,
                        "status": status,
                    },
                    output_item_list_params.OutputItemListParams,
                ),
            ),
            model=OutputItemListResponse,
        )


class OutputItemsWithRawResponse:
    def __init__(self, output_items: OutputItems) -> None:
        self._output_items = output_items

        self.retrieve = _legacy_response.to_raw_response_wrapper(
            output_items.retrieve,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            output_items.list,
        )


class AsyncOutputItemsWithRawResponse:
    def __init__(self, output_items: AsyncOutputItems) -> None:
        self._output_items = output_items

        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            output_items.retrieve,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            output_items.list,
        )


class OutputItemsWithStreamingResponse:
    def __init__(self, output_items: OutputItems) -> None:
        self._output_items = output_items

        self.retrieve = to_streamed_response_wrapper(
            output_items.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            output_items.list,
        )


class AsyncOutputItemsWithStreamingResponse:
    def __init__(self, output_items: AsyncOutputItems) -> None:
        self._output_items = output_items

        self.retrieve = async_to_streamed_response_wrapper(
            output_items.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            output_items.list,
        )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\archetype.py ===
"""
    pygments.lexers.archetype
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for Archetype-related syntaxes, including ODIN, ADL and cADL.

    For uses of this syntax, see the openEHR archetypes <http://www.openEHR.org/ckm>

    Contributed by Thomas Beale <https://github.com/wolandscat>,
    <https://bitbucket.org/thomas_beale>.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, bygroups, using, default
from pygments.token import Text, Comment, Name, Literal, Number, String, \
    Punctuation, Keyword, Operator, Generic, Whitespace

__all__ = ['OdinLexer', 'CadlLexer', 'AdlLexer']


class AtomsLexer(RegexLexer):
    """
    Lexer for Values used in ADL and ODIN.

    .. versionadded:: 2.1
    """

    tokens = {
        # ----- pseudo-states for inclusion -----
        'whitespace': [
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            (r'([ \t]*)(--.*)$', bygroups(Whitespace, Comment)),
        ],
        'archetype_id': [
            (r'([ \t]*)(([a-zA-Z]\w+(\.[a-zA-Z]\w+)*::)?[a-zA-Z]\w+(-[a-zA-Z]\w+){2}'
             r'\.\w+[\w-]*\.v\d+(\.\d+){,2}((-[a-z]+)(\.\d+)?)?)',
             bygroups(Whitespace, Name.Decorator)),
        ],
        'date_constraints': [
            # ISO 8601-based date/time constraints
            (r'[Xx?YyMmDdHhSs\d]{2,4}([:-][Xx?YyMmDdHhSs\d]{2}){2}', Literal.Date),
            # ISO 8601-based duration constraints + optional trailing slash
            (r'(P[YyMmWwDd]+(T[HhMmSs]+)?|PT[HhMmSs]+)/?', Literal.Date),
        ],
        'ordered_values': [
            # ISO 8601 date with optional 'T' ligature
            (r'\d{4}-\d{2}-\d{2}T?', Literal.Date),
            # ISO 8601 time
            (r'\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{4}|Z)?', Literal.Date),
            # ISO 8601 duration
            (r'P((\d*(\.\d+)?[YyMmWwDd]){1,3}(T(\d*(\.\d+)?[HhMmSs]){,3})?|'
             r'T(\d*(\.\d+)?[HhMmSs]){,3})', Literal.Date),
            (r'[+-]?(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+', Number.Float),
            (r'[+-]?\d*\.\d+%?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[+-]?\d+%?', Number.Integer),
        ],
        'values': [
            include('ordered_values'),
            (r'([Tt]rue|[Ff]alse)', Literal),
            (r'"', String, 'string'),
            (r"'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])'", String.Char),
            (r'[a-z][a-z0-9+.-]*:', Literal, 'uri'),
            # term code
            (r'(\[)(\w[\w-]*(?:\([^)\n]+\))?)(::)(\w[\w-]*)(\])',
             bygroups(Punctuation, Name.Decorator, Punctuation, Name.Decorator,
                      Punctuation)),
            (r'\|', Punctuation, 'interval'),
            # list continuation
            (r'\.\.\.', Punctuation),
        ],
        'constraint_values': [
            (r'(\[)(\w[\w-]*(?:\([^)\n]+\))?)(::)',
             bygroups(Punctuation, Name.Decorator, Punctuation), 'adl14_code_constraint'),
            # ADL 1.4 ordinal constraint
            (r'(\d*)(\|)(\[\w[\w-]*::\w[\w-]*\])((?:[,;])?)',
             bygroups(Number, Punctuation, Name.Decorator, Punctuation)),
            include('date_constraints'),
            include('values'),
        ],

        # ----- real states -----
        'string': [
            ('"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|'
             r'u[a-fA-F0-9]{4}|U[a-fA-F0-9]{8}|[0-7]{1,3})', String.Escape),
            # all other characters
            (r'[^\\"]+', String),
            # stray backslash
            (r'\\', String),
        ],
        'uri': [
            # effective URI terminators
            (r'[,>\s]', Punctuation, '#pop'),
            (r'[^>\s,]+', Literal),
        ],
        'interval': [
            (r'\|', Punctuation, '#pop'),
            include('ordered_values'),
            (r'\.\.', Punctuation),
            (r'[<>=] *', Punctuation),
            # handle +/-
            (r'\+/-', Punctuation),
            (r'\s+', Whitespace),
        ],
        'any_code': [
            include('archetype_id'),
            # if it is a code
            (r'[a-z_]\w*[0-9.]+(@[^\]]+)?', Name.Decorator),
            # if it is tuple with attribute names
            (r'[a-z_]\w*', Name.Class),
            # if it is an integer, i.e. Xpath child index
            (r'[0-9]+', Text),
            (r'\|', Punctuation, 'code_rubric'),
            (r'\]', Punctuation, '#pop'),
            # handle use_archetype statement
            (r'(\s*)(,)(\s*)', bygroups(Whitespace, Punctuation, Whitespace)),
        ],
        'code_rubric': [
            (r'\|', Punctuation, '#pop'),
            (r'[^|]+', String),
        ],
        'adl14_code_constraint': [
            (r'\]', Punctuation, '#pop'),
            (r'\|', Punctuation, 'code_rubric'),
            (r'(\w[\w-]*)([;,]?)', bygroups(Name.Decorator, Punctuation)),
            include('whitespace'),
        ],
    }


class OdinLexer(AtomsLexer):
    """
    Lexer for ODIN syntax.
    """
    name = 'ODIN'
    aliases = ['odin']
    filenames = ['*.odin']
    mimetypes = ['text/odin']
    url = 'https://github.com/openEHR/odin'
    version_added = '2.1'

    tokens = {
        'path': [
            (r'>', Punctuation, '#pop'),
            # attribute name
            (r'[a-z_]\w*', Name.Class),
            (r'/', Punctuation),
            (r'\[', Punctuation, 'key'),
            (r'(\s*)(,)(\s*)', bygroups(Whitespace, Punctuation, Whitespace), '#pop'),
            (r'\s+', Whitespace, '#pop'),
        ],
        'key': [
            include('values'),
            (r'\]', Punctuation, '#pop'),
        ],
        'type_cast': [
            (r'\)', Punctuation, '#pop'),
            (r'[^)]+',  Name.Class),
        ],
        'root': [
            include('whitespace'),
            (r'([Tt]rue|[Ff]alse)', Literal),
            include('values'),
            # x-ref path
            (r'/', Punctuation, 'path'),
            # x-ref path starting with key
            (r'\[', Punctuation, 'key'),
            # attribute name
            (r'[a-z_]\w*', Name.Class),
            (r'=', Operator),
            (r'\(', Punctuation, 'type_cast'),
            (r',', Punctuation),
            (r'<', Punctuation),
            (r'>', Punctuation),
            (r';', Punctuation),
        ],
    }


class CadlLexer(AtomsLexer):
    """
    Lexer for cADL syntax.
    """
    name = 'cADL'
    aliases = ['cadl']
    filenames = ['*.cadl']
    url = 'https://specifications.openehr.org/releases/AM/latest/ADL2.html#_cadl_constraint_adl'
    version_added = '2.1'

    tokens = {
        'path': [
            # attribute name
            (r'[a-z_]\w*', Name.Class),
            (r'/', Punctuation),
            (r'\[', Punctuation, 'any_code'),
            (r'\s+', Punctuation, '#pop'),
        ],
        'root': [
            include('whitespace'),
            (r'(cardinality|existence|occurrences|group|include|exclude|'
             r'allow_archetype|use_archetype|use_node)\W', Keyword.Type),
            (r'(and|or|not|there_exists|xor|implies|for_all)\W', Keyword.Type),
            (r'(after|before|closed)\W', Keyword.Type),
            (r'(not)\W', Operator),
            (r'(matches|is_in)\W', Operator),
            # is_in / not is_in char
            ('(\u2208|\u2209)', Operator),
            # there_exists / not there_exists / for_all / and / or
            ('(\u2203|\u2204|\u2200|\u2227|\u2228|\u22BB|\223C)',
             Operator),
            # regex in slot or as string constraint
            (r'(\{)(\s*)(/[^}]+/)(\s*)(\})',
             bygroups(Punctuation, Whitespace, String.Regex, Whitespace, Punctuation)),
            # regex in slot or as string constraint
            (r'(\{)(\s*)(\^[^}]+\^)(\s*)(\})',
             bygroups(Punctuation, Whitespace, String.Regex, Whitespace, Punctuation)),
            (r'/', Punctuation, 'path'),
            # for cardinality etc
            (r'(\{)((?:\d+\.\.)?(?:\d+|\*))'
             r'((?:\s*;\s*(?:ordered|unordered|unique)){,2})(\})',
             bygroups(Punctuation, Number, Number, Punctuation)),
            # [{ is start of a tuple value
            (r'\[\{', Punctuation),
            (r'\}\]', Punctuation),
            (r'\{', Punctuation),
            (r'\}', Punctuation),
            include('constraint_values'),
            # type name
            (r'[A-Z]\w+(<[A-Z]\w+([A-Za-z_<>]*)>)?',  Name.Class),
            # attribute name
            (r'[a-z_]\w*', Name.Class),
            (r'\[', Punctuation, 'any_code'),
            (r'(~|//|\\\\|\+|-|/|\*|\^|!=|=|<=|>=|<|>]?)', Operator),
            (r'\(', Punctuation),
            (r'\)', Punctuation),
            # for lists of values
            (r',', Punctuation),
            (r'"', String, 'string'),
            # for assumed value
            (r';', Punctuation),
        ],
    }


class AdlLexer(AtomsLexer):
    """
    Lexer for ADL syntax.
    """

    name = 'ADL'
    aliases = ['adl']
    filenames = ['*.adl', '*.adls', '*.adlf', '*.adlx']
    url = 'https://specifications.openehr.org/releases/AM/latest/ADL2.html'
    version_added = '2.1'

    tokens = {
        'whitespace': [
            # blank line ends
            (r'\s*\n', Whitespace),
            # comment-only line
            (r'^([ \t]*)(--.*)$', bygroups(Whitespace, Comment)),
        ],
        'odin_section': [
            # repeating the following two rules from the root state enable multi-line
            # strings that start in the first column to be dealt with
            (r'^(language|description|ontology|terminology|annotations|'
             r'component_terminologies|revision_history)([ \t]*\n)',
             bygroups(Generic.Heading, Whitespace)),
            (r'^(definition)([ \t]*\n)', bygroups(Generic.Heading, Whitespace), 'cadl_section'),
            (r'^([ \t]*|[ \t]+.*)\n', using(OdinLexer)),
            (r'^([^"]*")(>[ \t]*\n)', bygroups(String, Punctuation)),
            # template overlay delimiter
            (r'^----------*\n', Text, '#pop'),
            (r'^.*\n', String),
            default('#pop'),
        ],
        'cadl_section': [
            (r'^([ \t]*|[ \t]+.*)\n', using(CadlLexer)),
            default('#pop'),
        ],
        'rules_section': [
            (r'^[ \t]+.*\n', using(CadlLexer)),
            default('#pop'),
        ],
        'metadata': [
            (r'\)', Punctuation, '#pop'),
            (r';', Punctuation),
            (r'([Tt]rue|[Ff]alse)', Literal),
            # numbers and version ids
            (r'\d+(\.\d+)*', Literal),
            # Guids
            (r'(\d|[a-fA-F])+(-(\d|[a-fA-F])+){3,}', Literal),
            (r'\w+', Name.Class),
            (r'"', String, 'string'),
            (r'=', Operator),
            (r'[ \t]+', Whitespace),
            default('#pop'),
        ],
        'root': [
            (r'^(archetype|template_overlay|operational_template|template|'
             r'speciali[sz]e)', Generic.Heading),
            (r'^(language|description|ontology|terminology|annotations|'
             r'component_terminologies|revision_history)[ \t]*\n',
             Generic.Heading, 'odin_section'),
            (r'^(definition)[ \t]*\n', Generic.Heading, 'cadl_section'),
            (r'^(rules)[ \t]*\n', Generic.Heading, 'rules_section'),
            include('archetype_id'),
            (r'([ \t]*)(\()', bygroups(Whitespace, Punctuation), 'metadata'),
            include('whitespace'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\trio\_core\_thread_cache.py ===
from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
import traceback
from functools import partial
from itertools import count
from threading import Lock, Thread
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import outcome

if TYPE_CHECKING:
    from collections.abc import Callable

RetT = TypeVar("RetT")


def _to_os_thread_name(name: str) -> bytes:
    # ctypes handles the trailing \00
    return name.encode("ascii", errors="replace")[:15]


# used to construct the method used to set os thread name, or None, depending on platform.
# called once on import
def get_os_thread_name_func() -> Callable[[int | None, str], None] | None:
    def namefunc(
        setname: Callable[[int, bytes], int],
        ident: int | None,
        name: str,
    ) -> None:
        # Thread.ident is None "if it has not been started". Unclear if that can happen
        # with current usage.
        if ident is not None:  # pragma: no cover
            setname(ident, _to_os_thread_name(name))

    # namefunc on Mac also takes an ident, even if pthread_setname_np doesn't/can't use it
    # so the caller don't need to care about platform.
    def darwin_namefunc(
        setname: Callable[[bytes], int],
        ident: int | None,
        name: str,
    ) -> None:
        # I don't know if Mac can rename threads that hasn't been started, but default
        # to no to be on the safe side.
        if ident is not None:  # pragma: no cover
            setname(_to_os_thread_name(name))

    # find the pthread library
    # this will fail on windows and musl
    libpthread_path = ctypes.util.find_library("pthread")
    if not libpthread_path:
        # musl includes pthread functions directly in libc.so
        # (but note that find_library("c") does not work on musl,
        #  see: https://github.com/python/cpython/issues/65821)
        # so try that library instead
        # if it doesn't exist, CDLL() will fail below
        libpthread_path = "libc.so"

    # Sometimes windows can find the path, but gives a permission error when
    # accessing it. Catching a wider exception in case of more esoteric errors.
    # https://github.com/python-trio/trio/issues/2688
    try:
        libpthread = ctypes.CDLL(libpthread_path)
    except Exception:  # pragma: no cover
        return None

    # get the setname method from it
    # afaik this should never fail
    pthread_setname_np = getattr(libpthread, "pthread_setname_np", None)
    if pthread_setname_np is None:  # pragma: no cover
        return None

    # specify function prototype
    pthread_setname_np.restype = ctypes.c_int

    # on mac OSX pthread_setname_np does not take a thread id,
    # it only lets threads name themselves, which is not a problem for us.
    # Just need to make sure to call it correctly
    if sys.platform == "darwin":
        pthread_setname_np.argtypes = [ctypes.c_char_p]
        return partial(darwin_namefunc, pthread_setname_np)

    # otherwise assume linux parameter conventions. Should also work on *BSD
    pthread_setname_np.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    return partial(namefunc, pthread_setname_np)


# construct os thread name method
set_os_thread_name = get_os_thread_name_func()

# The "thread cache" is a simple unbounded thread pool, i.e., it automatically
# spawns as many threads as needed to handle all the requests its given. Its
# only purpose is to cache worker threads so that they don't have to be
# started from scratch every time we want to delegate some work to a thread.
# It's expected that some higher-level code will track how many threads are in
# use to avoid overwhelming the system (e.g. the limiter= argument to
# trio.to_thread.run_sync).
#
# To maximize sharing, there's only one thread cache per process, even if you
# have multiple calls to trio.run.
#
# Guarantees:
#
# It's safe to call start_thread_soon simultaneously from
# multiple threads.
#
# Idle threads are chosen in LIFO order, i.e. we *don't* spread work evenly
# over all threads. Instead we try to let some threads do most of the work
# while others sit idle as much as possible. Compared to FIFO, this has better
# memory cache behavior, and it makes it easier to detect when we have too
# many threads, so idle ones can exit.
#
# This code assumes that 'dict' has the following properties:
#
# - __setitem__, __delitem__, and popitem are all thread-safe and atomic with
#   respect to each other. This is guaranteed by the GIL.
#
# - popitem returns the most-recently-added item (i.e., __setitem__ + popitem
#   give you a LIFO queue). This relies on dicts being insertion-ordered, like
#   they are in py36+.

# How long a thread will idle waiting for new work before gives up and exits.
# This value is pretty arbitrary; I don't think it matters too much.
IDLE_TIMEOUT = 10  # seconds

name_counter = count()


class WorkerThread(Generic[RetT]):
    __slots__ = ("_default_name", "_job", "_thread", "_thread_cache", "_worker_lock")

    def __init__(self, thread_cache: ThreadCache) -> None:
        self._job: (
            tuple[
                Callable[[], RetT],
                Callable[[outcome.Outcome[RetT]], object],
                str | None,
            ]
            | None
        ) = None
        self._thread_cache = thread_cache
        # This Lock is used in an unconventional way.
        #
        # "Unlocked" means we have a pending job that's been assigned to us;
        # "locked" means that we don't.
        #
        # Initially we have no job, so it starts out in locked state.
        self._worker_lock = Lock()
        self._worker_lock.acquire()
        self._default_name = f"Trio thread {next(name_counter)}"

        self._thread = Thread(target=self._work, name=self._default_name, daemon=True)

        if set_os_thread_name:
            set_os_thread_name(self._thread.ident, self._default_name)
        self._thread.start()

    def _handle_job(self) -> None:
        # Handle job in a separate method to ensure user-created
        # objects are cleaned up in a consistent manner.
        assert self._job is not None
        fn, deliver, name = self._job
        self._job = None

        # set name
        if name is not None:
            self._thread.name = name
            if set_os_thread_name:
                set_os_thread_name(self._thread.ident, name)
        result = outcome.capture(fn)

        # reset name if it was changed
        if name is not None:
            self._thread.name = self._default_name
            if set_os_thread_name:
                set_os_thread_name(self._thread.ident, self._default_name)

        # Tell the cache that we're available to be assigned a new
        # job. We do this *before* calling 'deliver', so that if
        # 'deliver' triggers a new job, it can be assigned to us
        # instead of spawning a new thread.
        self._thread_cache._idle_workers[self] = None
        try:
            deliver(result)
        except BaseException as e:
            print("Exception while delivering result of thread", file=sys.stderr)
            traceback.print_exception(type(e), e, e.__traceback__)

    def _work(self) -> None:
        while True:
            if self._worker_lock.acquire(timeout=IDLE_TIMEOUT):
                # We got a job
                self._handle_job()
            else:
                # Timeout acquiring lock, so we can probably exit. But,
                # there's a race condition: we might be assigned a job *just*
                # as we're about to exit. So we have to check.
                try:
                    del self._thread_cache._idle_workers[self]
                except KeyError:
                    # Someone else removed us from the idle worker queue, so
                    # they must be in the process of assigning us a job - loop
                    # around and wait for it.
                    continue
                else:
                    # We successfully removed ourselves from the idle
                    # worker queue, so no more jobs are incoming; it's safe to
                    # exit.
                    return


class ThreadCache:
    __slots__ = ("_idle_workers",)

    def __init__(self) -> None:
        self._idle_workers: dict[WorkerThread[Any], None] = {}  # type: ignore[explicit-any]

    def start_thread_soon(
        self,
        fn: Callable[[], RetT],
        deliver: Callable[[outcome.Outcome[RetT]], object],
        name: str | None = None,
    ) -> None:
        worker: WorkerThread[RetT]
        try:
            worker, _ = self._idle_workers.popitem()
        except KeyError:
            worker = WorkerThread(self)
        worker._job = (fn, deliver, name)
        worker._worker_lock.release()


THREAD_CACHE = ThreadCache()


def start_thread_soon(
    fn: Callable[[], RetT],
    deliver: Callable[[outcome.Outcome[RetT]], object],
    name: str | None = None,
) -> None:
    """Runs ``deliver(outcome.capture(fn))`` in a worker thread.

    Generally ``fn`` does some blocking work, and ``deliver`` delivers the
    result back to whoever is interested.

    This is a low-level, no-frills interface, very similar to using
    `threading.Thread` to spawn a thread directly. The main difference is
    that this function tries to reuse threads when possible, so it can be
    a bit faster than `threading.Thread`.

    Worker threads have the `~threading.Thread.daemon` flag set, which means
    that if your main thread exits, worker threads will automatically be
    killed. If you want to make sure that your ``fn`` runs to completion, then
    you should make sure that the main thread remains alive until ``deliver``
    is called.

    It is safe to call this function simultaneously from multiple threads.

    Args:

        fn (sync function): Performs arbitrary blocking work.

        deliver (sync function): Takes the `outcome.Outcome` of ``fn``, and
          delivers it. *Must not block.*

    Because worker threads are cached and reused for multiple calls, neither
    function should mutate thread-level state, like `threading.local` objects
    – or if they do, they should be careful to revert their changes before
    returning.

    Note:

        The split between ``fn`` and ``deliver`` serves two purposes. First,
        it's convenient, since most callers need something like this anyway.

        Second, it avoids a small race condition that could cause too many
        threads to be spawned. Consider a program that wants to run several
        jobs sequentially on a thread, so the main thread submits a job, waits
        for it to finish, submits another job, etc. In theory, this program
        should only need one worker thread. But what could happen is:

        1. Worker thread: First job finishes, and calls ``deliver``.

        2. Main thread: receives notification that the job finished, and calls
           ``start_thread_soon``.

        3. Main thread: sees that no worker threads are marked idle, so spawns
           a second worker thread.

        4. Original worker thread: marks itself as idle.

        To avoid this, threads mark themselves as idle *before* calling
        ``deliver``.

        Is this potential extra thread a major problem? Maybe not, but it's
        easy enough to avoid, and we figure that if the user is trying to
        limit how many threads they're using then it's polite to respect that.

    """
    THREAD_CACHE.start_thread_soon(fn, deliver, name)


def clear_worker_threads() -> None:
    # This is OK because the child process does not actually have any
    # worker threads. Additionally, while WorkerThread keeps a strong
    # reference and so would get affected, the only place those are
    # stored is here.
    THREAD_CACHE._idle_workers.clear()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=clear_worker_threads)

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\test_instrumentation.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

import attrs
import pytest

from ... import _abc, _core
from .tutil import check_sequence_matches

if TYPE_CHECKING:
    from collections.abc import Container, Iterable

    from ...lowlevel import Task


@attrs.define(eq=False, slots=False)
class TaskRecorder(_abc.Instrument):
    record: list[tuple[str, Task | None]] = attrs.Factory(list)

    def before_run(self) -> None:
        self.record.append(("before_run", None))

    def task_scheduled(self, task: Task) -> None:
        self.record.append(("schedule", task))

    def before_task_step(self, task: Task) -> None:
        assert task is _core.current_task()
        self.record.append(("before", task))

    def after_task_step(self, task: Task) -> None:
        assert task is _core.current_task()
        self.record.append(("after", task))

    def after_run(self) -> None:
        self.record.append(("after_run", None))

    def filter_tasks(self, tasks: Container[Task]) -> Iterable[tuple[str, Task | None]]:
        for item in self.record:
            if item[0] in ("schedule", "before", "after") and item[1] in tasks:
                yield item
            if item[0] in ("before_run", "after_run"):
                yield item


def test_instruments(recwarn: object) -> None:
    r1 = TaskRecorder()
    r2 = TaskRecorder()
    r3 = TaskRecorder()

    task = None

    # We use a child task for this, because the main task does some extra
    # bookkeeping stuff that can leak into the instrument results, and we
    # don't want to deal with it.
    async def task_fn() -> None:
        nonlocal task
        task = _core.current_task()

        for _ in range(4):
            await _core.checkpoint()
        # replace r2 with r3, to test that we can manipulate them as we go
        _core.remove_instrument(r2)
        with pytest.raises(KeyError):
            _core.remove_instrument(r2)
        # add is idempotent
        _core.add_instrument(r3)
        _core.add_instrument(r3)
        for _ in range(1):
            await _core.checkpoint()

    async def main() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(task_fn)

    _core.run(main, instruments=[r1, r2])

    # It sleeps 5 times, so it runs 6 times.  Note that checkpoint()
    # reschedules the task immediately upon yielding, before the
    # after_task_step event fires.
    expected = (
        [("before_run", None), ("schedule", task)]
        + [("before", task), ("schedule", task), ("after", task)] * 5
        + [("before", task), ("after", task), ("after_run", None)]
    )
    assert r1.record == r2.record + r3.record
    assert task is not None
    assert list(r1.filter_tasks([task])) == expected


def test_instruments_interleave() -> None:
    tasks = {}

    async def two_step1() -> None:
        tasks["t1"] = _core.current_task()
        await _core.checkpoint()

    async def two_step2() -> None:
        tasks["t2"] = _core.current_task()
        await _core.checkpoint()

    async def main() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(two_step1)
            nursery.start_soon(two_step2)

    r = TaskRecorder()
    _core.run(main, instruments=[r])

    expected = [
        ("before_run", None),
        ("schedule", tasks["t1"]),
        ("schedule", tasks["t2"]),
        {
            ("before", tasks["t1"]),
            ("schedule", tasks["t1"]),
            ("after", tasks["t1"]),
            ("before", tasks["t2"]),
            ("schedule", tasks["t2"]),
            ("after", tasks["t2"]),
        },
        {
            ("before", tasks["t1"]),
            ("after", tasks["t1"]),
            ("before", tasks["t2"]),
            ("after", tasks["t2"]),
        },
        ("after_run", None),
    ]
    print(list(r.filter_tasks(tasks.values())))
    check_sequence_matches(list(r.filter_tasks(tasks.values())), expected)


def test_null_instrument() -> None:
    # undefined instrument methods are skipped
    class NullInstrument(_abc.Instrument):
        def something_unrelated(self) -> None:
            pass  # pragma: no cover

    async def main() -> None:
        await _core.checkpoint()

    _core.run(main, instruments=[NullInstrument()])


def test_instrument_before_after_run() -> None:
    record = []

    class BeforeAfterRun(_abc.Instrument):
        def before_run(self) -> None:
            record.append("before_run")

        def after_run(self) -> None:
            record.append("after_run")

    async def main() -> None:
        pass

    _core.run(main, instruments=[BeforeAfterRun()])
    assert record == ["before_run", "after_run"]


def test_instrument_task_spawn_exit() -> None:
    record = []

    class SpawnExitRecorder(_abc.Instrument):
        def task_spawned(self, task: Task) -> None:
            record.append(("spawned", task))

        def task_exited(self, task: Task) -> None:
            record.append(("exited", task))

    async def main() -> Task:
        return _core.current_task()

    main_task = _core.run(main, instruments=[SpawnExitRecorder()])
    assert ("spawned", main_task) in record
    assert ("exited", main_task) in record


# This test also tests having a crash before the initial task is even spawned,
# which is very difficult to handle.
def test_instruments_crash(caplog: pytest.LogCaptureFixture) -> None:
    record = []

    class BrokenInstrument(_abc.Instrument):
        def task_scheduled(self, task: Task) -> NoReturn:
            record.append("scheduled")
            raise ValueError("oops")

        def close(self) -> None:
            # Shouldn't be called -- tests that the instrument disabling logic
            # works right.
            record.append("closed")  # pragma: no cover

    async def main() -> Task:
        record.append("main ran")
        return _core.current_task()

    r = TaskRecorder()
    main_task = _core.run(main, instruments=[r, BrokenInstrument()])
    assert record == ["scheduled", "main ran"]
    # the TaskRecorder kept going throughout, even though the BrokenInstrument
    # was disabled
    assert ("after", main_task) in r.record
    assert ("after_run", None) in r.record
    # And we got a log message
    assert caplog.records[0].exc_info is not None
    exc_type, exc_value, _exc_traceback = caplog.records[0].exc_info
    assert exc_type is ValueError
    assert str(exc_value) == "oops"
    assert "Instrument has been disabled" in caplog.records[0].message


def test_instruments_monkeypatch() -> None:
    class NullInstrument(_abc.Instrument):
        pass

    instrument = NullInstrument()

    async def main() -> None:
        record: list[Task] = []

        # Changing the set of hooks implemented by an instrument after
        # it's installed doesn't make them start being called right away
        instrument.before_task_step = (  # type: ignore[method-assign]
            record.append  # type: ignore[assignment] # append is pos-only
        )

        await _core.checkpoint()
        await _core.checkpoint()
        assert len(record) == 0

        # But if we remove and re-add the instrument, the new hooks are
        # picked up
        _core.remove_instrument(instrument)
        _core.add_instrument(instrument)
        await _core.checkpoint()
        await _core.checkpoint()
        assert record.count(_core.current_task()) == 2

        _core.remove_instrument(instrument)
        await _core.checkpoint()
        await _core.checkpoint()
        assert record.count(_core.current_task()) == 2

    _core.run(main, instruments=[instrument])


def test_instrument_that_raises_on_getattr() -> None:
    class EvilInstrument(_abc.Instrument):
        def task_exited(self, task: Task) -> NoReturn:
            raise AssertionError("this should never happen")  # pragma: no cover

        @property
        def after_run(self) -> NoReturn:
            raise ValueError("oops")

    async def main() -> None:
        with pytest.raises(ValueError, match=r"^oops$"):
            _core.add_instrument(EvilInstrument())

        # Make sure the instrument is fully removed from the per-method lists
        runner = _core.current_task()._runner
        assert "after_run" not in runner.instruments
        assert "task_exited" not in runner.instruments

    _core.run(main)


def test_instrument_call_trio_context() -> None:
    called = set()

    class Instrument(_abc.Instrument):
        pass

    hooks = {
        # not run in task context
        "after_io_wait": (True, False),
        "before_io_wait": (True, False),
        "before_run": (True, False),
        "after_run": (True, False),
        # run in task context
        "before_task_step": (True, True),
        "after_task_step": (True, True),
        "task_exited": (True, True),
        # depends
        "task_scheduled": (True, None),
        "task_spawned": (True, None),
    }
    for hook, val in hooks.items():

        def h(
            self: Instrument,
            *args: object,
            hook: str = hook,
            val: tuple[bool, bool | None] = val,
        ) -> None:
            fail_str = f"failed in {hook}"

            assert _core.in_trio_run() == val[0], fail_str
            if val[1] is not None:
                assert _core.in_trio_task() == val[1], fail_str
            called.add(hook)

        setattr(Instrument, hook, h)

    async def main() -> None:
        await _core.checkpoint()

        async with _core.open_nursery() as nursery:
            nursery.start_soon(_core.checkpoint)

    _core.run(main, instruments=[Instrument()])
    assert called == set(hooks)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\requests\auth.py ===
"""
requests.auth
~~~~~~~~~~~~~

This module contains the authentication handlers for Requests.
"""

import hashlib
import os
import re
import threading
import time
import warnings
from base64 import b64encode

from ._internal_utils import to_native_string
from .compat import basestring, str, urlparse
from .cookies import extract_cookies_to_jar
from .utils import parse_dict_header

CONTENT_TYPE_FORM_URLENCODED = "application/x-www-form-urlencoded"
CONTENT_TYPE_MULTI_PART = "multipart/form-data"


def _basic_auth_str(username, password):
    """Returns a Basic Auth string."""

    # "I want us to put a big-ol' comment on top of it that
    # says that this behaviour is dumb but we need to preserve
    # it because people are relying on it."
    #    - Lukasa
    #
    # These are here solely to maintain backwards compatibility
    # for things like ints. This will be removed in 3.0.0.
    if not isinstance(username, basestring):
        warnings.warn(
            "Non-string usernames will no longer be supported in Requests "
            "3.0.0. Please convert the object you've passed in ({!r}) to "
            "a string or bytes object in the near future to avoid "
            "problems.".format(username),
            category=DeprecationWarning,
        )
        username = str(username)

    if not isinstance(password, basestring):
        warnings.warn(
            "Non-string passwords will no longer be supported in Requests "
            "3.0.0. Please convert the object you've passed in ({!r}) to "
            "a string or bytes object in the near future to avoid "
            "problems.".format(type(password)),
            category=DeprecationWarning,
        )
        password = str(password)
    # -- End Removal --

    if isinstance(username, str):
        username = username.encode("latin1")

    if isinstance(password, str):
        password = password.encode("latin1")

    authstr = "Basic " + to_native_string(
        b64encode(b":".join((username, password))).strip()
    )

    return authstr


class AuthBase:
    """Base class that all auth implementations derive from"""

    def __call__(self, r):
        raise NotImplementedError("Auth hooks must be callable.")


class HTTPBasicAuth(AuthBase):
    """Attaches HTTP Basic Authentication to the given Request object."""

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __eq__(self, other):
        return all(
            [
                self.username == getattr(other, "username", None),
                self.password == getattr(other, "password", None),
            ]
        )

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        r.headers["Authorization"] = _basic_auth_str(self.username, self.password)
        return r


class HTTPProxyAuth(HTTPBasicAuth):
    """Attaches HTTP Proxy Authentication to a given Request object."""

    def __call__(self, r):
        r.headers["Proxy-Authorization"] = _basic_auth_str(self.username, self.password)
        return r


class HTTPDigestAuth(AuthBase):
    """Attaches HTTP Digest Authentication to the given Request object."""

    def __init__(self, username, password):
        self.username = username
        self.password = password
        # Keep state in per-thread local storage
        self._thread_local = threading.local()

    def init_per_thread_state(self):
        # Ensure state is initialized just once per-thread
        if not hasattr(self._thread_local, "init"):
            self._thread_local.init = True
            self._thread_local.last_nonce = ""
            self._thread_local.nonce_count = 0
            self._thread_local.chal = {}
            self._thread_local.pos = None
            self._thread_local.num_401_calls = None

    def build_digest_header(self, method, url):
        """
        :rtype: str
        """

        realm = self._thread_local.chal["realm"]
        nonce = self._thread_local.chal["nonce"]
        qop = self._thread_local.chal.get("qop")
        algorithm = self._thread_local.chal.get("algorithm")
        opaque = self._thread_local.chal.get("opaque")
        hash_utf8 = None

        if algorithm is None:
            _algorithm = "MD5"
        else:
            _algorithm = algorithm.upper()
        # lambdas assume digest modules are imported at the top level
        if _algorithm == "MD5" or _algorithm == "MD5-SESS":

            def md5_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.md5(x).hexdigest()

            hash_utf8 = md5_utf8
        elif _algorithm == "SHA":

            def sha_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha1(x).hexdigest()

            hash_utf8 = sha_utf8
        elif _algorithm == "SHA-256":

            def sha256_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha256(x).hexdigest()

            hash_utf8 = sha256_utf8
        elif _algorithm == "SHA-512":

            def sha512_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha512(x).hexdigest()

            hash_utf8 = sha512_utf8

        KD = lambda s, d: hash_utf8(f"{s}:{d}")  # noqa:E731

        if hash_utf8 is None:
            return None

        # XXX not implemented yet
        entdig = None
        p_parsed = urlparse(url)
        #: path is request-uri defined in RFC 2616 which should not be empty
        path = p_parsed.path or "/"
        if p_parsed.query:
            path += f"?{p_parsed.query}"

        A1 = f"{self.username}:{realm}:{self.password}"
        A2 = f"{method}:{path}"

        HA1 = hash_utf8(A1)
        HA2 = hash_utf8(A2)

        if nonce == self._thread_local.last_nonce:
            self._thread_local.nonce_count += 1
        else:
            self._thread_local.nonce_count = 1
        ncvalue = f"{self._thread_local.nonce_count:08x}"
        s = str(self._thread_local.nonce_count).encode("utf-8")
        s += nonce.encode("utf-8")
        s += time.ctime().encode("utf-8")
        s += os.urandom(8)

        cnonce = hashlib.sha1(s).hexdigest()[:16]
        if _algorithm == "MD5-SESS":
            HA1 = hash_utf8(f"{HA1}:{nonce}:{cnonce}")

        if not qop:
            respdig = KD(HA1, f"{nonce}:{HA2}")
        elif qop == "auth" or "auth" in qop.split(","):
            noncebit = f"{nonce}:{ncvalue}:{cnonce}:auth:{HA2}"
            respdig = KD(HA1, noncebit)
        else:
            # XXX handle auth-int.
            return None

        self._thread_local.last_nonce = nonce

        # XXX should the partial digests be encoded too?
        base = (
            f'username="{self.username}", realm="{realm}", nonce="{nonce}", '
            f'uri="{path}", response="{respdig}"'
        )
        if opaque:
            base += f', opaque="{opaque}"'
        if algorithm:
            base += f', algorithm="{algorithm}"'
        if entdig:
            base += f', digest="{entdig}"'
        if qop:
            base += f', qop="auth", nc={ncvalue}, cnonce="{cnonce}"'

        return f"Digest {base}"

    def handle_redirect(self, r, **kwargs):
        """Reset num_401_calls counter on redirects."""
        if r.is_redirect:
            self._thread_local.num_401_calls = 1

    def handle_401(self, r, **kwargs):
        """
        Takes the given response and tries digest-auth, if needed.

        :rtype: requests.Response
        """

        # If response is not 4xx, do not auth
        # See https://github.com/psf/requests/issues/3772
        if not 400 <= r.status_code < 500:
            self._thread_local.num_401_calls = 1
            return r

        if self._thread_local.pos is not None:
            # Rewind the file position indicator of the body to where
            # it was to resend the request.
            r.request.body.seek(self._thread_local.pos)
        s_auth = r.headers.get("www-authenticate", "")

        if "digest" in s_auth.lower() and self._thread_local.num_401_calls < 2:
            self._thread_local.num_401_calls += 1
            pat = re.compile(r"digest ", flags=re.IGNORECASE)
            self._thread_local.chal = parse_dict_header(pat.sub("", s_auth, count=1))

            # Consume content and release the original connection
            # to allow our new request to reuse the same one.
            r.content
            r.close()
            prep = r.request.copy()
            extract_cookies_to_jar(prep._cookies, r.request, r.raw)
            prep.prepare_cookies(prep._cookies)

            prep.headers["Authorization"] = self.build_digest_header(
                prep.method, prep.url
            )
            _r = r.connection.send(prep, **kwargs)
            _r.history.append(r)
            _r.request = prep

            return _r

        self._thread_local.num_401_calls = 1
        return r

    def __call__(self, r):
        # Initialize per-thread state, if needed
        self.init_per_thread_state()
        # If we have a saved nonce, skip the 401
        if self._thread_local.last_nonce:
            r.headers["Authorization"] = self.build_digest_header(r.method, r.url)
        try:
            self._thread_local.pos = r.body.tell()
        except AttributeError:
            # In the case of HTTPDigestAuth being reused and the body of
            # the previous request was a file-like object, pos has the
            # file position of the previous body. Ensure it's set to
            # None.
            self._thread_local.pos = None
        r.register_hook("response", self.handle_401)
        r.register_hook("response", self.handle_redirect)
        self._thread_local.num_401_calls = 1

        return r

    def __eq__(self, other):
        return all(
            [
                self.username == getattr(other, "username", None),
                self.password == getattr(other, "password", None),
            ]
        )

    def __ne__(self, other):
        return not self == other

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\appengine.py ===
"""
This module provides a pool manager that uses Google App Engine's
`URLFetch Service <https://cloud.google.com/appengine/docs/python/urlfetch>`_.

Example usage::

    from pip._vendor.urllib3 import PoolManager
    from pip._vendor.urllib3.contrib.appengine import AppEngineManager, is_appengine_sandbox

    if is_appengine_sandbox():
        # AppEngineManager uses AppEngine's URLFetch API behind the scenes
        http = AppEngineManager()
    else:
        # PoolManager uses a socket-level API behind the scenes
        http = PoolManager()

    r = http.request('GET', 'https://google.com/')

There are `limitations <https://cloud.google.com/appengine/docs/python/\
urlfetch/#Python_Quotas_and_limits>`_ to the URLFetch service and it may not be
the best choice for your application. There are three options for using
urllib3 on Google App Engine:

1. You can use :class:`AppEngineManager` with URLFetch. URLFetch is
   cost-effective in many circumstances as long as your usage is within the
   limitations.
2. You can use a normal :class:`~urllib3.PoolManager` by enabling sockets.
   Sockets also have `limitations and restrictions
   <https://cloud.google.com/appengine/docs/python/sockets/\
   #limitations-and-restrictions>`_ and have a lower free quota than URLFetch.
   To use sockets, be sure to specify the following in your ``app.yaml``::

        env_variables:
            GAE_USE_SOCKETS_HTTPLIB : 'true'

3. If you are using `App Engine Flexible
<https://cloud.google.com/appengine/docs/flexible/>`_, you can use the standard
:class:`PoolManager` without any configuration or special environment variables.
"""

from __future__ import absolute_import

import io
import logging
import warnings

from ..exceptions import (
    HTTPError,
    HTTPWarning,
    MaxRetryError,
    ProtocolError,
    SSLError,
    TimeoutError,
)
from ..packages.six.moves.urllib.parse import urljoin
from ..request import RequestMethods
from ..response import HTTPResponse
from ..util.retry import Retry
from ..util.timeout import Timeout
from . import _appengine_environ

try:
    from google.appengine.api import urlfetch
except ImportError:
    urlfetch = None


log = logging.getLogger(__name__)


class AppEnginePlatformWarning(HTTPWarning):
    pass


class AppEnginePlatformError(HTTPError):
    pass


class AppEngineManager(RequestMethods):
    """
    Connection manager for Google App Engine sandbox applications.

    This manager uses the URLFetch service directly instead of using the
    emulated httplib, and is subject to URLFetch limitations as described in
    the App Engine documentation `here
    <https://cloud.google.com/appengine/docs/python/urlfetch>`_.

    Notably it will raise an :class:`AppEnginePlatformError` if:
        * URLFetch is not available.
        * If you attempt to use this on App Engine Flexible, as full socket
          support is available.
        * If a request size is more than 10 megabytes.
        * If a response size is more than 32 megabytes.
        * If you use an unsupported request method such as OPTIONS.

    Beyond those cases, it will raise normal urllib3 errors.
    """

    def __init__(
        self,
        headers=None,
        retries=None,
        validate_certificate=True,
        urlfetch_retries=True,
    ):
        if not urlfetch:
            raise AppEnginePlatformError(
                "URLFetch is not available in this environment."
            )

        warnings.warn(
            "urllib3 is using URLFetch on Google App Engine sandbox instead "
            "of sockets. To use sockets directly instead of URLFetch see "
            "https://urllib3.readthedocs.io/en/1.26.x/reference/urllib3.contrib.html.",
            AppEnginePlatformWarning,
        )

        RequestMethods.__init__(self, headers)
        self.validate_certificate = validate_certificate
        self.urlfetch_retries = urlfetch_retries

        self.retries = retries or Retry.DEFAULT

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Return False to re-raise any potential exceptions
        return False

    def urlopen(
        self,
        method,
        url,
        body=None,
        headers=None,
        retries=None,
        redirect=True,
        timeout=Timeout.DEFAULT_TIMEOUT,
        **response_kw
    ):

        retries = self._get_retries(retries, redirect)

        try:
            follow_redirects = redirect and retries.redirect != 0 and retries.total
            response = urlfetch.fetch(
                url,
                payload=body,
                method=method,
                headers=headers or {},
                allow_truncated=False,
                follow_redirects=self.urlfetch_retries and follow_redirects,
                deadline=self._get_absolute_timeout(timeout),
                validate_certificate=self.validate_certificate,
            )
        except urlfetch.DeadlineExceededError as e:
            raise TimeoutError(self, e)

        except urlfetch.InvalidURLError as e:
            if "too large" in str(e):
                raise AppEnginePlatformError(
                    "URLFetch request too large, URLFetch only "
                    "supports requests up to 10mb in size.",
                    e,
                )
            raise ProtocolError(e)

        except urlfetch.DownloadError as e:
            if "Too many redirects" in str(e):
                raise MaxRetryError(self, url, reason=e)
            raise ProtocolError(e)

        except urlfetch.ResponseTooLargeError as e:
            raise AppEnginePlatformError(
                "URLFetch response too large, URLFetch only supports"
                "responses up to 32mb in size.",
                e,
            )

        except urlfetch.SSLCertificateError as e:
            raise SSLError(e)

        except urlfetch.InvalidMethodError as e:
            raise AppEnginePlatformError(
                "URLFetch does not support method: %s" % method, e
            )

        http_response = self._urlfetch_response_to_http_response(
            response, retries=retries, **response_kw
        )

        # Handle redirect?
        redirect_location = redirect and http_response.get_redirect_location()
        if redirect_location:
            # Check for redirect response
            if self.urlfetch_retries and retries.raise_on_redirect:
                raise MaxRetryError(self, url, "too many redirects")
            else:
                if http_response.status == 303:
                    method = "GET"

                try:
                    retries = retries.increment(
                        method, url, response=http_response, _pool=self
                    )
                except MaxRetryError:
                    if retries.raise_on_redirect:
                        raise MaxRetryError(self, url, "too many redirects")
                    return http_response

                retries.sleep_for_retry(http_response)
                log.debug("Redirecting %s -> %s", url, redirect_location)
                redirect_url = urljoin(url, redirect_location)
                return self.urlopen(
                    method,
                    redirect_url,
                    body,
                    headers,
                    retries=retries,
                    redirect=redirect,
                    timeout=timeout,
                    **response_kw
                )

        # Check if we should retry the HTTP response.
        has_retry_after = bool(http_response.headers.get("Retry-After"))
        if retries.is_retry(method, http_response.status, has_retry_after):
            retries = retries.increment(method, url, response=http_response, _pool=self)
            log.debug("Retry: %s", url)
            retries.sleep(http_response)
            return self.urlopen(
                method,
                url,
                body=body,
                headers=headers,
                retries=retries,
                redirect=redirect,
                timeout=timeout,
                **response_kw
            )

        return http_response

    def _urlfetch_response_to_http_response(self, urlfetch_resp, **response_kw):

        if is_prod_appengine():
            # Production GAE handles deflate encoding automatically, but does
            # not remove the encoding header.
            content_encoding = urlfetch_resp.headers.get("content-encoding")

            if content_encoding == "deflate":
                del urlfetch_resp.headers["content-encoding"]

        transfer_encoding = urlfetch_resp.headers.get("transfer-encoding")
        # We have a full response's content,
        # so let's make sure we don't report ourselves as chunked data.
        if transfer_encoding == "chunked":
            encodings = transfer_encoding.split(",")
            encodings.remove("chunked")
            urlfetch_resp.headers["transfer-encoding"] = ",".join(encodings)

        original_response = HTTPResponse(
            # In order for decoding to work, we must present the content as
            # a file-like object.
            body=io.BytesIO(urlfetch_resp.content),
            msg=urlfetch_resp.header_msg,
            headers=urlfetch_resp.headers,
            status=urlfetch_resp.status_code,
            **response_kw
        )

        return HTTPResponse(
            body=io.BytesIO(urlfetch_resp.content),
            headers=urlfetch_resp.headers,
            status=urlfetch_resp.status_code,
            original_response=original_response,
            **response_kw
        )

    def _get_absolute_timeout(self, timeout):
        if timeout is Timeout.DEFAULT_TIMEOUT:
            return None  # Defer to URLFetch's default.
        if isinstance(timeout, Timeout):
            if timeout._read is not None or timeout._connect is not None:
                warnings.warn(
                    "URLFetch does not support granular timeout settings, "
                    "reverting to total or default URLFetch timeout.",
                    AppEnginePlatformWarning,
                )
            return timeout.total
        return timeout

    def _get_retries(self, retries, redirect):
        if not isinstance(retries, Retry):
            retries = Retry.from_int(retries, redirect=redirect, default=self.retries)

        if retries.connect or retries.read or retries.redirect:
            warnings.warn(
                "URLFetch only supports total retries and does not "
                "recognize connect, read, or redirect retry parameters.",
                AppEnginePlatformWarning,
            )

        return retries


# Alias methods from _appengine_environ to maintain public API interface.

is_appengine = _appengine_environ.is_appengine
is_appengine_sandbox = _appengine_environ.is_appengine_sandbox
is_local_appengine = _appengine_environ.is_local_appengine
is_prod_appengine = _appengine_environ.is_prod_appengine
is_prod_appengine_mvms = _appengine_environ.is_prod_appengine_mvms

# === NexusCore/openenv\Lib\site-packages\requests\auth.py ===
"""
requests.auth
~~~~~~~~~~~~~

This module contains the authentication handlers for Requests.
"""

import hashlib
import os
import re
import threading
import time
import warnings
from base64 import b64encode

from ._internal_utils import to_native_string
from .compat import basestring, str, urlparse
from .cookies import extract_cookies_to_jar
from .utils import parse_dict_header

CONTENT_TYPE_FORM_URLENCODED = "application/x-www-form-urlencoded"
CONTENT_TYPE_MULTI_PART = "multipart/form-data"


def _basic_auth_str(username, password):
    """Returns a Basic Auth string."""

    # "I want us to put a big-ol' comment on top of it that
    # says that this behaviour is dumb but we need to preserve
    # it because people are relying on it."
    #    - Lukasa
    #
    # These are here solely to maintain backwards compatibility
    # for things like ints. This will be removed in 3.0.0.
    if not isinstance(username, basestring):
        warnings.warn(
            "Non-string usernames will no longer be supported in Requests "
            "3.0.0. Please convert the object you've passed in ({!r}) to "
            "a string or bytes object in the near future to avoid "
            "problems.".format(username),
            category=DeprecationWarning,
        )
        username = str(username)

    if not isinstance(password, basestring):
        warnings.warn(
            "Non-string passwords will no longer be supported in Requests "
            "3.0.0. Please convert the object you've passed in ({!r}) to "
            "a string or bytes object in the near future to avoid "
            "problems.".format(type(password)),
            category=DeprecationWarning,
        )
        password = str(password)
    # -- End Removal --

    if isinstance(username, str):
        username = username.encode("latin1")

    if isinstance(password, str):
        password = password.encode("latin1")

    authstr = "Basic " + to_native_string(
        b64encode(b":".join((username, password))).strip()
    )

    return authstr


class AuthBase:
    """Base class that all auth implementations derive from"""

    def __call__(self, r):
        raise NotImplementedError("Auth hooks must be callable.")


class HTTPBasicAuth(AuthBase):
    """Attaches HTTP Basic Authentication to the given Request object."""

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __eq__(self, other):
        return all(
            [
                self.username == getattr(other, "username", None),
                self.password == getattr(other, "password", None),
            ]
        )

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        r.headers["Authorization"] = _basic_auth_str(self.username, self.password)
        return r


class HTTPProxyAuth(HTTPBasicAuth):
    """Attaches HTTP Proxy Authentication to a given Request object."""

    def __call__(self, r):
        r.headers["Proxy-Authorization"] = _basic_auth_str(self.username, self.password)
        return r


class HTTPDigestAuth(AuthBase):
    """Attaches HTTP Digest Authentication to the given Request object."""

    def __init__(self, username, password):
        self.username = username
        self.password = password
        # Keep state in per-thread local storage
        self._thread_local = threading.local()

    def init_per_thread_state(self):
        # Ensure state is initialized just once per-thread
        if not hasattr(self._thread_local, "init"):
            self._thread_local.init = True
            self._thread_local.last_nonce = ""
            self._thread_local.nonce_count = 0
            self._thread_local.chal = {}
            self._thread_local.pos = None
            self._thread_local.num_401_calls = None

    def build_digest_header(self, method, url):
        """
        :rtype: str
        """

        realm = self._thread_local.chal["realm"]
        nonce = self._thread_local.chal["nonce"]
        qop = self._thread_local.chal.get("qop")
        algorithm = self._thread_local.chal.get("algorithm")
        opaque = self._thread_local.chal.get("opaque")
        hash_utf8 = None

        if algorithm is None:
            _algorithm = "MD5"
        else:
            _algorithm = algorithm.upper()
        # lambdas assume digest modules are imported at the top level
        if _algorithm == "MD5" or _algorithm == "MD5-SESS":

            def md5_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.md5(x).hexdigest()

            hash_utf8 = md5_utf8
        elif _algorithm == "SHA":

            def sha_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha1(x).hexdigest()

            hash_utf8 = sha_utf8
        elif _algorithm == "SHA-256":

            def sha256_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha256(x).hexdigest()

            hash_utf8 = sha256_utf8
        elif _algorithm == "SHA-512":

            def sha512_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha512(x).hexdigest()

            hash_utf8 = sha512_utf8

        KD = lambda s, d: hash_utf8(f"{s}:{d}")  # noqa:E731

        if hash_utf8 is None:
            return None

        # XXX not implemented yet
        entdig = None
        p_parsed = urlparse(url)
        #: path is request-uri defined in RFC 2616 which should not be empty
        path = p_parsed.path or "/"
        if p_parsed.query:
            path += f"?{p_parsed.query}"

        A1 = f"{self.username}:{realm}:{self.password}"
        A2 = f"{method}:{path}"

        HA1 = hash_utf8(A1)
        HA2 = hash_utf8(A2)

        if nonce == self._thread_local.last_nonce:
            self._thread_local.nonce_count += 1
        else:
            self._thread_local.nonce_count = 1
        ncvalue = f"{self._thread_local.nonce_count:08x}"
        s = str(self._thread_local.nonce_count).encode("utf-8")
        s += nonce.encode("utf-8")
        s += time.ctime().encode("utf-8")
        s += os.urandom(8)

        cnonce = hashlib.sha1(s).hexdigest()[:16]
        if _algorithm == "MD5-SESS":
            HA1 = hash_utf8(f"{HA1}:{nonce}:{cnonce}")

        if not qop:
            respdig = KD(HA1, f"{nonce}:{HA2}")
        elif qop == "auth" or "auth" in qop.split(","):
            noncebit = f"{nonce}:{ncvalue}:{cnonce}:auth:{HA2}"
            respdig = KD(HA1, noncebit)
        else:
            # XXX handle auth-int.
            return None

        self._thread_local.last_nonce = nonce

        # XXX should the partial digests be encoded too?
        base = (
            f'username="{self.username}", realm="{realm}", nonce="{nonce}", '
            f'uri="{path}", response="{respdig}"'
        )
        if opaque:
            base += f', opaque="{opaque}"'
        if algorithm:
            base += f', algorithm="{algorithm}"'
        if entdig:
            base += f', digest="{entdig}"'
        if qop:
            base += f', qop="auth", nc={ncvalue}, cnonce="{cnonce}"'

        return f"Digest {base}"

    def handle_redirect(self, r, **kwargs):
        """Reset num_401_calls counter on redirects."""
        if r.is_redirect:
            self._thread_local.num_401_calls = 1

    def handle_401(self, r, **kwargs):
        """
        Takes the given response and tries digest-auth, if needed.

        :rtype: requests.Response
        """

        # If response is not 4xx, do not auth
        # See https://github.com/psf/requests/issues/3772
        if not 400 <= r.status_code < 500:
            self._thread_local.num_401_calls = 1
            return r

        if self._thread_local.pos is not None:
            # Rewind the file position indicator of the body to where
            # it was to resend the request.
            r.request.body.seek(self._thread_local.pos)
        s_auth = r.headers.get("www-authenticate", "")

        if "digest" in s_auth.lower() and self._thread_local.num_401_calls < 2:
            self._thread_local.num_401_calls += 1
            pat = re.compile(r"digest ", flags=re.IGNORECASE)
            self._thread_local.chal = parse_dict_header(pat.sub("", s_auth, count=1))

            # Consume content and release the original connection
            # to allow our new request to reuse the same one.
            r.content
            r.close()
            prep = r.request.copy()
            extract_cookies_to_jar(prep._cookies, r.request, r.raw)
            prep.prepare_cookies(prep._cookies)

            prep.headers["Authorization"] = self.build_digest_header(
                prep.method, prep.url
            )
            _r = r.connection.send(prep, **kwargs)
            _r.history.append(r)
            _r.request = prep

            return _r

        self._thread_local.num_401_calls = 1
        return r

    def __call__(self, r):
        # Initialize per-thread state, if needed
        self.init_per_thread_state()
        # If we have a saved nonce, skip the 401
        if self._thread_local.last_nonce:
            r.headers["Authorization"] = self.build_digest_header(r.method, r.url)
        try:
            self._thread_local.pos = r.body.tell()
        except AttributeError:
            # In the case of HTTPDigestAuth being reused and the body of
            # the previous request was a file-like object, pos has the
            # file position of the previous body. Ensure it's set to
            # None.
            self._thread_local.pos = None
        r.register_hook("response", self.handle_401)
        r.register_hook("response", self.handle_redirect)
        self._thread_local.num_401_calls = 1

        return r

    def __eq__(self, other):
        return all(
            [
                self.username == getattr(other, "username", None),
                self.password == getattr(other, "password", None),
            ]
        )

    def __ne__(self, other):
        return not self == other

# === NexusCore/openenv\Lib\site-packages\google\generativeai\caching.py ===
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
from __future__ import annotations

import datetime
import textwrap
from typing import Iterable, Optional

from google.generativeai import protos
from google.generativeai.types import caching_types
from google.generativeai.types import content_types
from google.generativeai.client import get_default_cache_client

from google.protobuf import field_mask_pb2

_USER_ROLE = "user"
_MODEL_ROLE = "model"


class CachedContent:
    """Cached content resource."""

    def __init__(self, name):
        """Fetches a `CachedContent` resource.

        Identical to `CachedContent.get`.

        Args:
            name: The resource name referring to the cached content.
        """
        client = get_default_cache_client()

        if "cachedContents/" not in name:
            name = "cachedContents/" + name

        request = protos.GetCachedContentRequest(name=name)
        response = client.get_cached_content(request)
        self._proto = response

    @property
    def name(self) -> str:
        return self._proto.name

    @property
    def model(self) -> str:
        return self._proto.model

    @property
    def display_name(self) -> str:
        return self._proto.display_name

    @property
    def usage_metadata(self) -> protos.CachedContent.UsageMetadata:
        return self._proto.usage_metadata

    @property
    def create_time(self) -> datetime.datetime:
        return self._proto.create_time

    @property
    def update_time(self) -> datetime.datetime:
        return self._proto.update_time

    @property
    def expire_time(self) -> datetime.datetime:
        return self._proto.expire_time

    def __str__(self):
        return textwrap.dedent(
            f"""\
            CachedContent(
                name='{self.name}',
                model='{self.model}',
                display_name='{self.display_name}',
                usage_metadata={'{'}
                    'total_token_count': {self.usage_metadata.total_token_count},
                {'}'},
                create_time={self.create_time},
                update_time={self.update_time},
                expire_time={self.expire_time}
            )"""
        )

    __repr__ = __str__

    @classmethod
    def _from_obj(cls, obj: CachedContent | protos.CachedContent | dict) -> CachedContent:
        """Creates an instance of CachedContent form an object, without calling `get`."""
        self = cls.__new__(cls)
        self._proto = protos.CachedContent()
        self._update(obj)
        return self

    def _update(self, updates):
        """Updates this instance inplace, does not call the API's `update` method"""
        if isinstance(updates, CachedContent):
            updates = updates._proto

        if not isinstance(updates, dict):
            updates = type(updates).to_dict(updates, including_default_value_fields=False)

        for key, value in updates.items():
            setattr(self._proto, key, value)

    @staticmethod
    def _prepare_create_request(
        model: str,
        *,
        display_name: str | None = None,
        system_instruction: Optional[content_types.ContentType] = None,
        contents: Optional[content_types.ContentsType] = None,
        tools: Optional[content_types.FunctionLibraryType] = None,
        tool_config: Optional[content_types.ToolConfigType] = None,
        ttl: Optional[caching_types.TTLTypes] = None,
        expire_time: Optional[caching_types.ExpireTimeTypes] = None,
    ) -> protos.CreateCachedContentRequest:
        """Prepares a CreateCachedContentRequest."""
        if ttl and expire_time:
            raise ValueError(
                "Exclusive arguments: Please provide either `ttl` or `expire_time`, not both."
            )

        if "/" not in model:
            model = "models/" + model

        if display_name and len(display_name) > 128:
            raise ValueError("`display_name` must be no more than 128 unicode characters.")

        if system_instruction:
            system_instruction = content_types.to_content(system_instruction)

        tools_lib = content_types.to_function_library(tools)
        if tools_lib:
            tools_lib = tools_lib.to_proto()

        if tool_config:
            tool_config = content_types.to_tool_config(tool_config)

        if contents:
            contents = content_types.to_contents(contents)
            if not contents[-1].role:
                contents[-1].role = _USER_ROLE

        ttl = caching_types.to_optional_ttl(ttl)
        expire_time = caching_types.to_optional_expire_time(expire_time)

        cached_content = protos.CachedContent(
            model=model,
            display_name=display_name,
            system_instruction=system_instruction,
            contents=contents,
            tools=tools_lib,
            tool_config=tool_config,
            ttl=ttl,
            expire_time=expire_time,
        )

        return protos.CreateCachedContentRequest(cached_content=cached_content)

    @classmethod
    def create(
        cls,
        model: str,
        *,
        display_name: str | None = None,
        system_instruction: Optional[content_types.ContentType] = None,
        contents: Optional[content_types.ContentsType] = None,
        tools: Optional[content_types.FunctionLibraryType] = None,
        tool_config: Optional[content_types.ToolConfigType] = None,
        ttl: Optional[caching_types.TTLTypes] = None,
        expire_time: Optional[caching_types.ExpireTimeTypes] = None,
    ) -> CachedContent:
        """Creates `CachedContent` resource.

        Args:
            model: The name of the `model` to use for cached content creation.
                   Any `CachedContent` resource can be only used with the
                   `model` it was created for.
            display_name: The user-generated meaningful display name
                          of the cached content. `display_name` must be no
                          more than 128 unicode characters.
            system_instruction: Developer set system instruction.
            contents: Contents to cache.
            tools: A list of `Tools` the model may use to generate response.
            tool_config: Config to apply to all tools.
            ttl: TTL for cached resource (in seconds). Defaults to 1 hour.
                 `ttl` and `expire_time` are exclusive arguments.
            expire_time: Expiration time for cached resource.
                         `ttl` and `expire_time` are exclusive arguments.

        Returns:
            `CachedContent` resource with specified name.
        """
        client = get_default_cache_client()

        request = cls._prepare_create_request(
            model=model,
            display_name=display_name,
            system_instruction=system_instruction,
            contents=contents,
            tools=tools,
            tool_config=tool_config,
            ttl=ttl,
            expire_time=expire_time,
        )

        response = client.create_cached_content(request)
        result = CachedContent._from_obj(response)
        return result

    @classmethod
    def get(cls, name: str) -> CachedContent:
        """Fetches required `CachedContent` resource.

        Args:
            name: The resource name referring to the cached content.

        Returns:
            `CachedContent` resource with specified `name`.
        """
        client = get_default_cache_client()

        if "cachedContents/" not in name:
            name = "cachedContents/" + name

        request = protos.GetCachedContentRequest(name=name)
        response = client.get_cached_content(request)
        result = CachedContent._from_obj(response)
        return result

    @classmethod
    def list(cls, page_size: Optional[int] = 1) -> Iterable[CachedContent]:
        """Lists `CachedContent` objects associated with the project.

        Args:
            page_size: The maximum number of permissions to return (per page).
            The service may return fewer `CachedContent` objects.

        Returns:
            A paginated list of `CachedContent` objects.
        """
        client = get_default_cache_client()

        request = protos.ListCachedContentsRequest(page_size=page_size)
        for cached_content in client.list_cached_contents(request):
            cached_content = CachedContent._from_obj(cached_content)
            yield cached_content

    def delete(self) -> None:
        """Deletes `CachedContent` resource."""
        client = get_default_cache_client()

        request = protos.DeleteCachedContentRequest(name=self.name)
        client.delete_cached_content(request)
        return

    def update(
        self,
        *,
        ttl: Optional[caching_types.TTLTypes] = None,
        expire_time: Optional[caching_types.ExpireTimeTypes] = None,
    ) -> None:
        """Updates requested `CachedContent` resource.

        Args:
            ttl: TTL for cached resource (in seconds). Defaults to 1 hour.
                 `ttl` and `expire_time` are exclusive arguments.
            expire_time: Expiration time for cached resource.
                         `ttl` and `expire_time` are exclusive arguments.
        """
        client = get_default_cache_client()

        if ttl and expire_time:
            raise ValueError(
                "Exclusive arguments: Please provide either `ttl` or `expire_time`, not both."
            )

        ttl = caching_types.to_optional_ttl(ttl)
        expire_time = caching_types.to_optional_expire_time(expire_time)

        updates = protos.CachedContent(
            name=self.name,
            ttl=ttl,
            expire_time=expire_time,
        )

        field_mask = field_mask_pb2.FieldMask()

        if ttl:
            field_mask.paths.append("ttl")
        elif expire_time:
            field_mask.paths.append("expire_time")
        else:
            raise ValueError(
                f"Bad update name: Only `ttl`  or `expire_time` can be updated for `CachedContent`."
            )

        request = protos.UpdateCachedContentRequest(cached_content=updates, update_mask=field_mask)
        updated_cc = client.update_cached_content(request)
        self._update(updated_cc)

        return

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\commands\upload.py ===
# coding=utf-8
# Copyright 2023-present, the HuggingFace Inc. team.
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
"""Contains command to upload a repo or file with the CLI.

Usage:
    # Upload file (implicit)
    huggingface-cli upload my-cool-model ./my-cool-model.safetensors

    # Upload file (explicit)
    huggingface-cli upload my-cool-model ./my-cool-model.safetensors  model.safetensors

    # Upload directory (implicit). If `my-cool-model/` is a directory it will be uploaded, otherwise an exception is raised.
    huggingface-cli upload my-cool-model

    # Upload directory (explicit)
    huggingface-cli upload my-cool-model ./models/my-cool-model .

    # Upload filtered directory (example: tensorboard logs except for the last run)
    huggingface-cli upload my-cool-model ./model/training /logs --include "*.tfevents.*" --exclude "*20230905*"

    # Upload with wildcard
    huggingface-cli upload my-cool-model "./model/training/*.safetensors"

    # Upload private dataset
    huggingface-cli upload Wauplin/my-cool-dataset ./data . --repo-type=dataset --private

    # Upload with token
    huggingface-cli upload Wauplin/my-cool-model --token=hf_****

    # Sync local Space with Hub (upload new files, delete removed files)
    huggingface-cli upload Wauplin/space-example --repo-type=space --exclude="/logs/*" --delete="*" --commit-message="Sync local Space with Hub"

    # Schedule commits every 30 minutes
    huggingface-cli upload Wauplin/my-cool-model --every=30
"""

import os
import time
import warnings
from argparse import Namespace, _SubParsersAction
from typing import List, Optional

from huggingface_hub import logging
from huggingface_hub._commit_scheduler import CommitScheduler
from huggingface_hub.commands import BaseHuggingfaceCLICommand
from huggingface_hub.constants import HF_HUB_ENABLE_HF_TRANSFER
from huggingface_hub.errors import RevisionNotFoundError
from huggingface_hub.hf_api import HfApi
from huggingface_hub.utils import disable_progress_bars, enable_progress_bars
from huggingface_hub.utils._runtime import is_xet_available


logger = logging.get_logger(__name__)


class UploadCommand(BaseHuggingfaceCLICommand):
    @staticmethod
    def register_subcommand(parser: _SubParsersAction):
        upload_parser = parser.add_parser("upload", help="Upload a file or a folder to a repo on the Hub")
        upload_parser.add_argument(
            "repo_id", type=str, help="The ID of the repo to upload to (e.g. `username/repo-name`)."
        )
        upload_parser.add_argument(
            "local_path",
            nargs="?",
            help="Local path to the file or folder to upload. Wildcard patterns are supported. Defaults to current directory.",
        )
        upload_parser.add_argument(
            "path_in_repo",
            nargs="?",
            help="Path of the file or folder in the repo. Defaults to the relative path of the file or folder.",
        )
        upload_parser.add_argument(
            "--repo-type",
            choices=["model", "dataset", "space"],
            default="model",
            help="Type of the repo to upload to (e.g. `dataset`).",
        )
        upload_parser.add_argument(
            "--revision",
            type=str,
            help=(
                "An optional Git revision to push to. It can be a branch name or a PR reference. If revision does not"
                " exist and `--create-pr` is not set, a branch will be automatically created."
            ),
        )
        upload_parser.add_argument(
            "--private",
            action="store_true",
            help=(
                "Whether to create a private repo if repo doesn't exist on the Hub. Ignored if the repo already"
                " exists."
            ),
        )
        upload_parser.add_argument("--include", nargs="*", type=str, help="Glob patterns to match files to upload.")
        upload_parser.add_argument(
            "--exclude", nargs="*", type=str, help="Glob patterns to exclude from files to upload."
        )
        upload_parser.add_argument(
            "--delete",
            nargs="*",
            type=str,
            help="Glob patterns for file to be deleted from the repo while committing.",
        )
        upload_parser.add_argument(
            "--commit-message", type=str, help="The summary / title / first line of the generated commit."
        )
        upload_parser.add_argument("--commit-description", type=str, help="The description of the generated commit.")
        upload_parser.add_argument(
            "--create-pr", action="store_true", help="Whether to upload content as a new Pull Request."
        )
        upload_parser.add_argument(
            "--every",
            type=float,
            help="If set, a background job is scheduled to create commits every `every` minutes.",
        )
        upload_parser.add_argument(
            "--token", type=str, help="A User Access Token generated from https://huggingface.co/settings/tokens"
        )
        upload_parser.add_argument(
            "--quiet",
            action="store_true",
            help="If True, progress bars are disabled and only the path to the uploaded files is printed.",
        )
        upload_parser.set_defaults(func=UploadCommand)

    def __init__(self, args: Namespace) -> None:
        self.repo_id: str = args.repo_id
        self.repo_type: Optional[str] = args.repo_type
        self.revision: Optional[str] = args.revision
        self.private: bool = args.private

        self.include: Optional[List[str]] = args.include
        self.exclude: Optional[List[str]] = args.exclude
        self.delete: Optional[List[str]] = args.delete

        self.commit_message: Optional[str] = args.commit_message
        self.commit_description: Optional[str] = args.commit_description
        self.create_pr: bool = args.create_pr
        self.api: HfApi = HfApi(token=args.token, library_name="huggingface-cli")
        self.quiet: bool = args.quiet  # disable warnings and progress bars

        # Check `--every` is valid
        if args.every is not None and args.every <= 0:
            raise ValueError(f"`every` must be a positive value (got '{args.every}')")
        self.every: Optional[float] = args.every

        # Resolve `local_path` and `path_in_repo`
        repo_name: str = args.repo_id.split("/")[-1]  # e.g. "Wauplin/my-cool-model" => "my-cool-model"
        self.local_path: str
        self.path_in_repo: str

        if args.local_path is not None and any(c in args.local_path for c in ["*", "?", "["]):
            if args.include is not None:
                raise ValueError("Cannot set `--include` when passing a `local_path` containing a wildcard.")
            if args.path_in_repo is not None and args.path_in_repo != ".":
                raise ValueError("Cannot set `path_in_repo` when passing a `local_path` containing a wildcard.")
            self.local_path = "."
            self.include = args.local_path
            self.path_in_repo = "."
        elif args.local_path is None and os.path.isfile(repo_name):
            # Implicit case 1: user provided only a repo_id which happen to be a local file as well => upload it with same name
            self.local_path = repo_name
            self.path_in_repo = repo_name
        elif args.local_path is None and os.path.isdir(repo_name):
            # Implicit case 2: user provided only a repo_id which happen to be a local folder as well => upload it at root
            self.local_path = repo_name
            self.path_in_repo = "."
        elif args.local_path is None:
            # Implicit case 3: user provided only a repo_id that does not match a local file or folder
            # => the user must explicitly provide a local_path => raise exception
            raise ValueError(f"'{repo_name}' is not a local file or folder. Please set `local_path` explicitly.")
        elif args.path_in_repo is None and os.path.isfile(args.local_path):
            # Explicit local path to file, no path in repo => upload it at root with same name
            self.local_path = args.local_path
            self.path_in_repo = os.path.basename(args.local_path)
        elif args.path_in_repo is None:
            # Explicit local path to folder, no path in repo => upload at root
            self.local_path = args.local_path
            self.path_in_repo = "."
        else:
            # Finally, if both paths are explicit
            self.local_path = args.local_path
            self.path_in_repo = args.path_in_repo

    def run(self) -> None:
        if self.quiet:
            disable_progress_bars()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                print(self._upload())
            enable_progress_bars()
        else:
            logging.set_verbosity_info()
            print(self._upload())
            logging.set_verbosity_warning()

    def _upload(self) -> str:
        if os.path.isfile(self.local_path):
            if self.include is not None and len(self.include) > 0:
                warnings.warn("Ignoring `--include` since a single file is uploaded.")
            if self.exclude is not None and len(self.exclude) > 0:
                warnings.warn("Ignoring `--exclude` since a single file is uploaded.")
            if self.delete is not None and len(self.delete) > 0:
                warnings.warn("Ignoring `--delete` since a single file is uploaded.")

        if not is_xet_available() and not HF_HUB_ENABLE_HF_TRANSFER:
            logger.info(
                "Consider using `hf_transfer` for faster uploads. This solution comes with some limitations. See"
                " https://huggingface.co/docs/huggingface_hub/hf_transfer for more details."
            )

        # Schedule commits if `every` is set
        if self.every is not None:
            if os.path.isfile(self.local_path):
                # If file => watch entire folder + use allow_patterns
                folder_path = os.path.dirname(self.local_path)
                path_in_repo = (
                    self.path_in_repo[: -len(self.local_path)]  # remove filename from path_in_repo
                    if self.path_in_repo.endswith(self.local_path)
                    else self.path_in_repo
                )
                allow_patterns = [self.local_path]
                ignore_patterns = []
            else:
                folder_path = self.local_path
                path_in_repo = self.path_in_repo
                allow_patterns = self.include or []
                ignore_patterns = self.exclude or []
                if self.delete is not None and len(self.delete) > 0:
                    warnings.warn("Ignoring `--delete` when uploading with scheduled commits.")

            scheduler = CommitScheduler(
                folder_path=folder_path,
                repo_id=self.repo_id,
                repo_type=self.repo_type,
                revision=self.revision,
                allow_patterns=allow_patterns,
                ignore_patterns=ignore_patterns,
                path_in_repo=path_in_repo,
                private=self.private,
                every=self.every,
                hf_api=self.api,
            )
            print(f"Scheduling commits every {self.every} minutes to {scheduler.repo_id}.")
            try:  # Block main thread until KeyboardInterrupt
                while True:
                    time.sleep(100)
            except KeyboardInterrupt:
                scheduler.stop()
                return "Stopped scheduled commits."

        # Otherwise, create repo and proceed with the upload
        if not os.path.isfile(self.local_path) and not os.path.isdir(self.local_path):
            raise FileNotFoundError(f"No such file or directory: '{self.local_path}'.")
        repo_id = self.api.create_repo(
            repo_id=self.repo_id,
            repo_type=self.repo_type,
            exist_ok=True,
            private=self.private,
            space_sdk="gradio" if self.repo_type == "space" else None,
            # ^ We don't want it to fail when uploading to a Space => let's set Gradio by default.
            # ^ I'd rather not add CLI args to set it explicitly as we already have `huggingface-cli repo create` for that.
        ).repo_id

        # Check if branch already exists and if not, create it
        if self.revision is not None and not self.create_pr:
            try:
                self.api.repo_info(repo_id=repo_id, repo_type=self.repo_type, revision=self.revision)
            except RevisionNotFoundError:
                logger.info(f"Branch '{self.revision}' not found. Creating it...")
                self.api.create_branch(repo_id=repo_id, repo_type=self.repo_type, branch=self.revision, exist_ok=True)
                # ^ `exist_ok=True` to avoid race concurrency issues

        # File-based upload
        if os.path.isfile(self.local_path):
            return self.api.upload_file(
                path_or_fileobj=self.local_path,
                path_in_repo=self.path_in_repo,
                repo_id=repo_id,
                repo_type=self.repo_type,
                revision=self.revision,
                commit_message=self.commit_message,
                commit_description=self.commit_description,
                create_pr=self.create_pr,
            )

        # Folder-based upload
        else:
            return self.api.upload_folder(
                folder_path=self.local_path,
                path_in_repo=self.path_in_repo,
                repo_id=repo_id,
                repo_type=self.repo_type,
                revision=self.revision,
                commit_message=self.commit_message,
                commit_description=self.commit_description,
                create_pr=self.create_pr,
                allow_patterns=self.include,
                ignore_patterns=self.exclude,
                delete_patterns=self.delete,
            )

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\realtime\session_update_event.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Union, Optional
from typing_extensions import Literal, TypeAlias

from ...._models import BaseModel

__all__ = [
    "SessionUpdateEvent",
    "Session",
    "SessionClientSecret",
    "SessionClientSecretExpiresAt",
    "SessionInputAudioNoiseReduction",
    "SessionInputAudioTranscription",
    "SessionTool",
    "SessionTracing",
    "SessionTracingTracingConfiguration",
    "SessionTurnDetection",
]


class SessionClientSecretExpiresAt(BaseModel):
    anchor: Optional[Literal["created_at"]] = None
    """The anchor point for the ephemeral token expiration.

    Only `created_at` is currently supported.
    """

    seconds: Optional[int] = None
    """The number of seconds from the anchor point to the expiration.

    Select a value between `10` and `7200`.
    """


class SessionClientSecret(BaseModel):
    expires_at: Optional[SessionClientSecretExpiresAt] = None
    """Configuration for the ephemeral token expiration."""


class SessionInputAudioNoiseReduction(BaseModel):
    type: Optional[Literal["near_field", "far_field"]] = None
    """Type of noise reduction.

    `near_field` is for close-talking microphones such as headphones, `far_field` is
    for far-field microphones such as laptop or conference room microphones.
    """


class SessionInputAudioTranscription(BaseModel):
    language: Optional[str] = None
    """The language of the input audio.

    Supplying the input language in
    [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
    format will improve accuracy and latency.
    """

    model: Optional[str] = None
    """
    The model to use for transcription, current options are `gpt-4o-transcribe`,
    `gpt-4o-mini-transcribe`, and `whisper-1`.
    """

    prompt: Optional[str] = None
    """
    An optional text to guide the model's style or continue a previous audio
    segment. For `whisper-1`, the
    [prompt is a list of keywords](https://platform.openai.com/docs/guides/speech-to-text#prompting).
    For `gpt-4o-transcribe` models, the prompt is a free text string, for example
    "expect words related to technology".
    """


class SessionTool(BaseModel):
    description: Optional[str] = None
    """
    The description of the function, including guidance on when and how to call it,
    and guidance about what to tell the user when calling (if anything).
    """

    name: Optional[str] = None
    """The name of the function."""

    parameters: Optional[object] = None
    """Parameters of the function in JSON Schema."""

    type: Optional[Literal["function"]] = None
    """The type of the tool, i.e. `function`."""


class SessionTracingTracingConfiguration(BaseModel):
    group_id: Optional[str] = None
    """
    The group id to attach to this trace to enable filtering and grouping in the
    traces dashboard.
    """

    metadata: Optional[object] = None
    """
    The arbitrary metadata to attach to this trace to enable filtering in the traces
    dashboard.
    """

    workflow_name: Optional[str] = None
    """The name of the workflow to attach to this trace.

    This is used to name the trace in the traces dashboard.
    """


SessionTracing: TypeAlias = Union[Literal["auto"], SessionTracingTracingConfiguration]


class SessionTurnDetection(BaseModel):
    create_response: Optional[bool] = None
    """
    Whether or not to automatically generate a response when a VAD stop event
    occurs.
    """

    eagerness: Optional[Literal["low", "medium", "high", "auto"]] = None
    """Used only for `semantic_vad` mode.

    The eagerness of the model to respond. `low` will wait longer for the user to
    continue speaking, `high` will respond more quickly. `auto` is the default and
    is equivalent to `medium`.
    """

    interrupt_response: Optional[bool] = None
    """
    Whether or not to automatically interrupt any ongoing response with output to
    the default conversation (i.e. `conversation` of `auto`) when a VAD start event
    occurs.
    """

    prefix_padding_ms: Optional[int] = None
    """Used only for `server_vad` mode.

    Amount of audio to include before the VAD detected speech (in milliseconds).
    Defaults to 300ms.
    """

    silence_duration_ms: Optional[int] = None
    """Used only for `server_vad` mode.

    Duration of silence to detect speech stop (in milliseconds). Defaults to 500ms.
    With shorter values the model will respond more quickly, but may jump in on
    short pauses from the user.
    """

    threshold: Optional[float] = None
    """Used only for `server_vad` mode.

    Activation threshold for VAD (0.0 to 1.0), this defaults to 0.5. A higher
    threshold will require louder audio to activate the model, and thus might
    perform better in noisy environments.
    """

    type: Optional[Literal["server_vad", "semantic_vad"]] = None
    """Type of turn detection."""


class Session(BaseModel):
    client_secret: Optional[SessionClientSecret] = None
    """Configuration options for the generated client secret."""

    input_audio_format: Optional[Literal["pcm16", "g711_ulaw", "g711_alaw"]] = None
    """The format of input audio.

    Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For `pcm16`, input audio must
    be 16-bit PCM at a 24kHz sample rate, single channel (mono), and little-endian
    byte order.
    """

    input_audio_noise_reduction: Optional[SessionInputAudioNoiseReduction] = None
    """Configuration for input audio noise reduction.

    This can be set to `null` to turn off. Noise reduction filters audio added to
    the input audio buffer before it is sent to VAD and the model. Filtering the
    audio can improve VAD and turn detection accuracy (reducing false positives) and
    model performance by improving perception of the input audio.
    """

    input_audio_transcription: Optional[SessionInputAudioTranscription] = None
    """
    Configuration for input audio transcription, defaults to off and can be set to
    `null` to turn off once on. Input audio transcription is not native to the
    model, since the model consumes audio directly. Transcription runs
    asynchronously through
    [the /audio/transcriptions endpoint](https://platform.openai.com/docs/api-reference/audio/createTranscription)
    and should be treated as guidance of input audio content rather than precisely
    what the model heard. The client can optionally set the language and prompt for
    transcription, these offer additional guidance to the transcription service.
    """

    instructions: Optional[str] = None
    """The default system instructions (i.e.

    system message) prepended to model calls. This field allows the client to guide
    the model on desired responses. The model can be instructed on response content
    and format, (e.g. "be extremely succinct", "act friendly", "here are examples of
    good responses") and on audio behavior (e.g. "talk quickly", "inject emotion
    into your voice", "laugh frequently"). The instructions are not guaranteed to be
    followed by the model, but they provide guidance to the model on the desired
    behavior.

    Note that the server sets default instructions which will be used if this field
    is not set and are visible in the `session.created` event at the start of the
    session.
    """

    max_response_output_tokens: Union[int, Literal["inf"], None] = None
    """
    Maximum number of output tokens for a single assistant response, inclusive of
    tool calls. Provide an integer between 1 and 4096 to limit output tokens, or
    `inf` for the maximum available tokens for a given model. Defaults to `inf`.
    """

    modalities: Optional[List[Literal["text", "audio"]]] = None
    """The set of modalities the model can respond with.

    To disable audio, set this to ["text"].
    """

    model: Optional[
        Literal[
            "gpt-4o-realtime-preview",
            "gpt-4o-realtime-preview-2024-10-01",
            "gpt-4o-realtime-preview-2024-12-17",
            "gpt-4o-realtime-preview-2025-06-03",
            "gpt-4o-mini-realtime-preview",
            "gpt-4o-mini-realtime-preview-2024-12-17",
        ]
    ] = None
    """The Realtime model used for this session."""

    output_audio_format: Optional[Literal["pcm16", "g711_ulaw", "g711_alaw"]] = None
    """The format of output audio.

    Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For `pcm16`, output audio is
    sampled at a rate of 24kHz.
    """

    speed: Optional[float] = None
    """The speed of the model's spoken response.

    1.0 is the default speed. 0.25 is the minimum speed. 1.5 is the maximum speed.
    This value can only be changed in between model turns, not while a response is
    in progress.
    """

    temperature: Optional[float] = None
    """Sampling temperature for the model, limited to [0.6, 1.2].

    For audio models a temperature of 0.8 is highly recommended for best
    performance.
    """

    tool_choice: Optional[str] = None
    """How the model chooses tools.

    Options are `auto`, `none`, `required`, or specify a function.
    """

    tools: Optional[List[SessionTool]] = None
    """Tools (functions) available to the model."""

    tracing: Optional[SessionTracing] = None
    """Configuration options for tracing.

    Set to null to disable tracing. Once tracing is enabled for a session, the
    configuration cannot be modified.

    `auto` will create a trace for the session with default values for the workflow
    name, group id, and metadata.
    """

    turn_detection: Optional[SessionTurnDetection] = None
    """Configuration for turn detection, ether Server VAD or Semantic VAD.

    This can be set to `null` to turn off, in which case the client must manually
    trigger model response. Server VAD means that the model will detect the start
    and end of speech based on audio volume and respond at the end of user speech.
    Semantic VAD is more advanced and uses a turn detection model (in conjuction
    with VAD) to semantically estimate whether the user has finished speaking, then
    dynamically sets a timeout based on this probability. For example, if user audio
    trails off with "uhhm", the model will score a low probability of turn end and
    wait longer for the user to continue speaking. This can be useful for more
    natural conversations, but may have a higher latency.
    """

    voice: Union[
        str,
        Literal["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"],
        None,
    ] = None
    """The voice the model uses to respond.

    Voice cannot be changed during the session once the model has responded with
    audio at least once. Current voice options are `alloy`, `ash`, `ballad`,
    `coral`, `echo`, `fable`, `onyx`, `nova`, `sage`, `shimmer`, and `verse`.
    """


class SessionUpdateEvent(BaseModel):
    session: Session
    """Realtime session object configuration."""

    type: Literal["session.update"]
    """The event type, must be `session.update`."""

    event_id: Optional[str] = None
    """Optional client-generated ID used to identify this event."""

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\requests\auth.py ===
"""
requests.auth
~~~~~~~~~~~~~

This module contains the authentication handlers for Requests.
"""

import hashlib
import os
import re
import threading
import time
import warnings
from base64 import b64encode

from ._internal_utils import to_native_string
from .compat import basestring, str, urlparse
from .cookies import extract_cookies_to_jar
from .utils import parse_dict_header

CONTENT_TYPE_FORM_URLENCODED = "application/x-www-form-urlencoded"
CONTENT_TYPE_MULTI_PART = "multipart/form-data"


def _basic_auth_str(username, password):
    """Returns a Basic Auth string."""

    # "I want us to put a big-ol' comment on top of it that
    # says that this behaviour is dumb but we need to preserve
    # it because people are relying on it."
    #    - Lukasa
    #
    # These are here solely to maintain backwards compatibility
    # for things like ints. This will be removed in 3.0.0.
    if not isinstance(username, basestring):
        warnings.warn(
            "Non-string usernames will no longer be supported in Requests "
            "3.0.0. Please convert the object you've passed in ({!r}) to "
            "a string or bytes object in the near future to avoid "
            "problems.".format(username),
            category=DeprecationWarning,
        )
        username = str(username)

    if not isinstance(password, basestring):
        warnings.warn(
            "Non-string passwords will no longer be supported in Requests "
            "3.0.0. Please convert the object you've passed in ({!r}) to "
            "a string or bytes object in the near future to avoid "
            "problems.".format(type(password)),
            category=DeprecationWarning,
        )
        password = str(password)
    # -- End Removal --

    if isinstance(username, str):
        username = username.encode("latin1")

    if isinstance(password, str):
        password = password.encode("latin1")

    authstr = "Basic " + to_native_string(
        b64encode(b":".join((username, password))).strip()
    )

    return authstr


class AuthBase:
    """Base class that all auth implementations derive from"""

    def __call__(self, r):
        raise NotImplementedError("Auth hooks must be callable.")


class HTTPBasicAuth(AuthBase):
    """Attaches HTTP Basic Authentication to the given Request object."""

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __eq__(self, other):
        return all(
            [
                self.username == getattr(other, "username", None),
                self.password == getattr(other, "password", None),
            ]
        )

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        r.headers["Authorization"] = _basic_auth_str(self.username, self.password)
        return r


class HTTPProxyAuth(HTTPBasicAuth):
    """Attaches HTTP Proxy Authentication to a given Request object."""

    def __call__(self, r):
        r.headers["Proxy-Authorization"] = _basic_auth_str(self.username, self.password)
        return r


class HTTPDigestAuth(AuthBase):
    """Attaches HTTP Digest Authentication to the given Request object."""

    def __init__(self, username, password):
        self.username = username
        self.password = password
        # Keep state in per-thread local storage
        self._thread_local = threading.local()

    def init_per_thread_state(self):
        # Ensure state is initialized just once per-thread
        if not hasattr(self._thread_local, "init"):
            self._thread_local.init = True
            self._thread_local.last_nonce = ""
            self._thread_local.nonce_count = 0
            self._thread_local.chal = {}
            self._thread_local.pos = None
            self._thread_local.num_401_calls = None

    def build_digest_header(self, method, url):
        """
        :rtype: str
        """

        realm = self._thread_local.chal["realm"]
        nonce = self._thread_local.chal["nonce"]
        qop = self._thread_local.chal.get("qop")
        algorithm = self._thread_local.chal.get("algorithm")
        opaque = self._thread_local.chal.get("opaque")
        hash_utf8 = None

        if algorithm is None:
            _algorithm = "MD5"
        else:
            _algorithm = algorithm.upper()
        # lambdas assume digest modules are imported at the top level
        if _algorithm == "MD5" or _algorithm == "MD5-SESS":

            def md5_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.md5(x).hexdigest()

            hash_utf8 = md5_utf8
        elif _algorithm == "SHA":

            def sha_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha1(x).hexdigest()

            hash_utf8 = sha_utf8
        elif _algorithm == "SHA-256":

            def sha256_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha256(x).hexdigest()

            hash_utf8 = sha256_utf8
        elif _algorithm == "SHA-512":

            def sha512_utf8(x):
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha512(x).hexdigest()

            hash_utf8 = sha512_utf8

        KD = lambda s, d: hash_utf8(f"{s}:{d}")  # noqa:E731

        if hash_utf8 is None:
            return None

        # XXX not implemented yet
        entdig = None
        p_parsed = urlparse(url)
        #: path is request-uri defined in RFC 2616 which should not be empty
        path = p_parsed.path or "/"
        if p_parsed.query:
            path += f"?{p_parsed.query}"

        A1 = f"{self.username}:{realm}:{self.password}"
        A2 = f"{method}:{path}"

        HA1 = hash_utf8(A1)
        HA2 = hash_utf8(A2)

        if nonce == self._thread_local.last_nonce:
            self._thread_local.nonce_count += 1
        else:
            self._thread_local.nonce_count = 1
        ncvalue = f"{self._thread_local.nonce_count:08x}"
        s = str(self._thread_local.nonce_count).encode("utf-8")
        s += nonce.encode("utf-8")
        s += time.ctime().encode("utf-8")
        s += os.urandom(8)

        cnonce = hashlib.sha1(s).hexdigest()[:16]
        if _algorithm == "MD5-SESS":
            HA1 = hash_utf8(f"{HA1}:{nonce}:{cnonce}")

        if not qop:
            respdig = KD(HA1, f"{nonce}:{HA2}")
        elif qop == "auth" or "auth" in qop.split(","):
            noncebit = f"{nonce}:{ncvalue}:{cnonce}:auth:{HA2}"
            respdig = KD(HA1, noncebit)
        else:
            # XXX handle auth-int.
            return None

        self._thread_local.last_nonce = nonce

        # XXX should the partial digests be encoded too?
        base = (
            f'username="{self.username}", realm="{realm}", nonce="{nonce}", '
            f'uri="{path}", response="{respdig}"'
        )
        if opaque:
            base += f', opaque="{opaque}"'
        if algorithm:
            base += f', algorithm="{algorithm}"'
        if entdig:
            base += f', digest="{entdig}"'
        if qop:
            base += f', qop="auth", nc={ncvalue}, cnonce="{cnonce}"'

        return f"Digest {base}"

    def handle_redirect(self, r, **kwargs):
        """Reset num_401_calls counter on redirects."""
        if r.is_redirect:
            self._thread_local.num_401_calls = 1

    def handle_401(self, r, **kwargs):
        """
        Takes the given response and tries digest-auth, if needed.

        :rtype: requests.Response
        """

        # If response is not 4xx, do not auth
        # See https://github.com/psf/requests/issues/3772
        if not 400 <= r.status_code < 500:
            self._thread_local.num_401_calls = 1
            return r

        if self._thread_local.pos is not None:
            # Rewind the file position indicator of the body to where
            # it was to resend the request.
            r.request.body.seek(self._thread_local.pos)
        s_auth = r.headers.get("www-authenticate", "")

        if "digest" in s_auth.lower() and self._thread_local.num_401_calls < 2:
            self._thread_local.num_401_calls += 1
            pat = re.compile(r"digest ", flags=re.IGNORECASE)
            self._thread_local.chal = parse_dict_header(pat.sub("", s_auth, count=1))

            # Consume content and release the original connection
            # to allow our new request to reuse the same one.
            r.content
            r.close()
            prep = r.request.copy()
            extract_cookies_to_jar(prep._cookies, r.request, r.raw)
            prep.prepare_cookies(prep._cookies)

            prep.headers["Authorization"] = self.build_digest_header(
                prep.method, prep.url
            )
            _r = r.connection.send(prep, **kwargs)
            _r.history.append(r)
            _r.request = prep

            return _r

        self._thread_local.num_401_calls = 1
        return r

    def __call__(self, r):
        # Initialize per-thread state, if needed
        self.init_per_thread_state()
        # If we have a saved nonce, skip the 401
        if self._thread_local.last_nonce:
            r.headers["Authorization"] = self.build_digest_header(r.method, r.url)
        try:
            self._thread_local.pos = r.body.tell()
        except AttributeError:
            # In the case of HTTPDigestAuth being reused and the body of
            # the previous request was a file-like object, pos has the
            # file position of the previous body. Ensure it's set to
            # None.
            self._thread_local.pos = None
        r.register_hook("response", self.handle_401)
        r.register_hook("response", self.handle_redirect)
        self._thread_local.num_401_calls = 1

        return r

    def __eq__(self, other):
        return all(
            [
                self.username == getattr(other, "username", None),
                self.password == getattr(other, "password", None),
            ]
        )

    def __ne__(self, other):
        return not self == other