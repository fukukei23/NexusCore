
# === NexusCore/tools\exports\export_20250803_114325\combined_117.py ===

# === NexusCore/openenv\Lib\site-packages\rich\syntax.py ===
import os.path
import re
import sys
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name, guess_lexer_for_filename
from pygments.style import Style as PygmentsStyle
from pygments.styles import get_style_by_name
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Token,
    Whitespace,
)
from pygments.util import ClassNotFound

from rich.containers import Lines
from rich.padding import Padding, PaddingDimensions

from ._loop import loop_first
from .cells import cell_len
from .color import Color, blend_rgb
from .console import Console, ConsoleOptions, JustifyMethod, RenderResult
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment, Segments
from .style import Style, StyleType
from .text import Text

TokenType = Tuple[str, ...]

WINDOWS = sys.platform == "win32"
DEFAULT_THEME = "monokai"

# The following styles are based on https://github.com/pygments/pygments/blob/master/pygments/formatters/terminal.py
# A few modifications were made

ANSI_LIGHT: Dict[TokenType, Style] = {
    Token: Style(),
    Whitespace: Style(color="white"),
    Comment: Style(dim=True),
    Comment.Preproc: Style(color="cyan"),
    Keyword: Style(color="blue"),
    Keyword.Type: Style(color="cyan"),
    Operator.Word: Style(color="magenta"),
    Name.Builtin: Style(color="cyan"),
    Name.Function: Style(color="green"),
    Name.Namespace: Style(color="cyan", underline=True),
    Name.Class: Style(color="green", underline=True),
    Name.Exception: Style(color="cyan"),
    Name.Decorator: Style(color="magenta", bold=True),
    Name.Variable: Style(color="red"),
    Name.Constant: Style(color="red"),
    Name.Attribute: Style(color="cyan"),
    Name.Tag: Style(color="bright_blue"),
    String: Style(color="yellow"),
    Number: Style(color="blue"),
    Generic.Deleted: Style(color="bright_red"),
    Generic.Inserted: Style(color="green"),
    Generic.Heading: Style(bold=True),
    Generic.Subheading: Style(color="magenta", bold=True),
    Generic.Prompt: Style(bold=True),
    Generic.Error: Style(color="bright_red"),
    Error: Style(color="red", underline=True),
}

ANSI_DARK: Dict[TokenType, Style] = {
    Token: Style(),
    Whitespace: Style(color="bright_black"),
    Comment: Style(dim=True),
    Comment.Preproc: Style(color="bright_cyan"),
    Keyword: Style(color="bright_blue"),
    Keyword.Type: Style(color="bright_cyan"),
    Operator.Word: Style(color="bright_magenta"),
    Name.Builtin: Style(color="bright_cyan"),
    Name.Function: Style(color="bright_green"),
    Name.Namespace: Style(color="bright_cyan", underline=True),
    Name.Class: Style(color="bright_green", underline=True),
    Name.Exception: Style(color="bright_cyan"),
    Name.Decorator: Style(color="bright_magenta", bold=True),
    Name.Variable: Style(color="bright_red"),
    Name.Constant: Style(color="bright_red"),
    Name.Attribute: Style(color="bright_cyan"),
    Name.Tag: Style(color="bright_blue"),
    String: Style(color="yellow"),
    Number: Style(color="bright_blue"),
    Generic.Deleted: Style(color="bright_red"),
    Generic.Inserted: Style(color="bright_green"),
    Generic.Heading: Style(bold=True),
    Generic.Subheading: Style(color="bright_magenta", bold=True),
    Generic.Prompt: Style(bold=True),
    Generic.Error: Style(color="bright_red"),
    Error: Style(color="red", underline=True),
}

RICH_SYNTAX_THEMES = {"ansi_light": ANSI_LIGHT, "ansi_dark": ANSI_DARK}
NUMBERS_COLUMN_DEFAULT_PADDING = 2


class SyntaxTheme(ABC):
    """Base class for a syntax theme."""

    @abstractmethod
    def get_style_for_token(self, token_type: TokenType) -> Style:
        """Get a style for a given Pygments token."""
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def get_background_style(self) -> Style:
        """Get the background color."""
        raise NotImplementedError  # pragma: no cover


class PygmentsSyntaxTheme(SyntaxTheme):
    """Syntax theme that delegates to Pygments theme."""

    def __init__(self, theme: Union[str, Type[PygmentsStyle]]) -> None:
        self._style_cache: Dict[TokenType, Style] = {}
        if isinstance(theme, str):
            try:
                self._pygments_style_class = get_style_by_name(theme)
            except ClassNotFound:
                self._pygments_style_class = get_style_by_name("default")
        else:
            self._pygments_style_class = theme

        self._background_color = self._pygments_style_class.background_color
        self._background_style = Style(bgcolor=self._background_color)

    def get_style_for_token(self, token_type: TokenType) -> Style:
        """Get a style from a Pygments class."""
        try:
            return self._style_cache[token_type]
        except KeyError:
            try:
                pygments_style = self._pygments_style_class.style_for_token(token_type)
            except KeyError:
                style = Style.null()
            else:
                color = pygments_style["color"]
                bgcolor = pygments_style["bgcolor"]
                style = Style(
                    color="#" + color if color else "#000000",
                    bgcolor="#" + bgcolor if bgcolor else self._background_color,
                    bold=pygments_style["bold"],
                    italic=pygments_style["italic"],
                    underline=pygments_style["underline"],
                )
            self._style_cache[token_type] = style
        return style

    def get_background_style(self) -> Style:
        return self._background_style


class ANSISyntaxTheme(SyntaxTheme):
    """Syntax theme to use standard colors."""

    def __init__(self, style_map: Dict[TokenType, Style]) -> None:
        self.style_map = style_map
        self._missing_style = Style.null()
        self._background_style = Style.null()
        self._style_cache: Dict[TokenType, Style] = {}

    def get_style_for_token(self, token_type: TokenType) -> Style:
        """Look up style in the style map."""
        try:
            return self._style_cache[token_type]
        except KeyError:
            # Styles form a hierarchy
            # We need to go from most to least specific
            # e.g. ("foo", "bar", "baz") to ("foo", "bar")  to ("foo",)
            get_style = self.style_map.get
            token = tuple(token_type)
            style = self._missing_style
            while token:
                _style = get_style(token)
                if _style is not None:
                    style = _style
                    break
                token = token[:-1]
            self._style_cache[token_type] = style
            return style

    def get_background_style(self) -> Style:
        return self._background_style


SyntaxPosition = Tuple[int, int]


class _SyntaxHighlightRange(NamedTuple):
    """
    A range to highlight in a Syntax object.
    `start` and `end` are 2-integers tuples, where the first integer is the line number
    (starting from 1) and the second integer is the column index (starting from 0).
    """

    style: StyleType
    start: SyntaxPosition
    end: SyntaxPosition
    style_before: bool = False


class Syntax(JupyterMixin):
    """Construct a Syntax object to render syntax highlighted code.

    Args:
        code (str): Code to highlight.
        lexer (Lexer | str): Lexer to use (see https://pygments.org/docs/lexers/)
        theme (str, optional): Color theme, aka Pygments style (see https://pygments.org/docs/styles/#getting-a-list-of-available-styles). Defaults to "monokai".
        dedent (bool, optional): Enable stripping of initial whitespace. Defaults to False.
        line_numbers (bool, optional): Enable rendering of line numbers. Defaults to False.
        start_line (int, optional): Starting number for line numbers. Defaults to 1.
        line_range (Tuple[int | None, int | None], optional): If given should be a tuple of the start and end line to render.
            A value of None in the tuple indicates the range is open in that direction.
        highlight_lines (Set[int]): A set of line numbers to highlight.
        code_width: Width of code to render (not including line numbers), or ``None`` to use all available width.
        tab_size (int, optional): Size of tabs. Defaults to 4.
        word_wrap (bool, optional): Enable word wrapping.
        background_color (str, optional): Optional background color, or None to use theme color. Defaults to None.
        indent_guides (bool, optional): Show indent guides. Defaults to False.
        padding (PaddingDimensions): Padding to apply around the syntax. Defaults to 0 (no padding).
    """

    _pygments_style_class: Type[PygmentsStyle]
    _theme: SyntaxTheme

    @classmethod
    def get_theme(cls, name: Union[str, SyntaxTheme]) -> SyntaxTheme:
        """Get a syntax theme instance."""
        if isinstance(name, SyntaxTheme):
            return name
        theme: SyntaxTheme
        if name in RICH_SYNTAX_THEMES:
            theme = ANSISyntaxTheme(RICH_SYNTAX_THEMES[name])
        else:
            theme = PygmentsSyntaxTheme(name)
        return theme

    def __init__(
        self,
        code: str,
        lexer: Union[Lexer, str],
        *,
        theme: Union[str, SyntaxTheme] = DEFAULT_THEME,
        dedent: bool = False,
        line_numbers: bool = False,
        start_line: int = 1,
        line_range: Optional[Tuple[Optional[int], Optional[int]]] = None,
        highlight_lines: Optional[Set[int]] = None,
        code_width: Optional[int] = None,
        tab_size: int = 4,
        word_wrap: bool = False,
        background_color: Optional[str] = None,
        indent_guides: bool = False,
        padding: PaddingDimensions = 0,
    ) -> None:
        self.code = code
        self._lexer = lexer
        self.dedent = dedent
        self.line_numbers = line_numbers
        self.start_line = start_line
        self.line_range = line_range
        self.highlight_lines = highlight_lines or set()
        self.code_width = code_width
        self.tab_size = tab_size
        self.word_wrap = word_wrap
        self.background_color = background_color
        self.background_style = (
            Style(bgcolor=background_color) if background_color else Style()
        )
        self.indent_guides = indent_guides
        self.padding = padding

        self._theme = self.get_theme(theme)
        self._stylized_ranges: List[_SyntaxHighlightRange] = []

    @classmethod
    def from_path(
        cls,
        path: str,
        encoding: str = "utf-8",
        lexer: Optional[Union[Lexer, str]] = None,
        theme: Union[str, SyntaxTheme] = DEFAULT_THEME,
        dedent: bool = False,
        line_numbers: bool = False,
        line_range: Optional[Tuple[int, int]] = None,
        start_line: int = 1,
        highlight_lines: Optional[Set[int]] = None,
        code_width: Optional[int] = None,
        tab_size: int = 4,
        word_wrap: bool = False,
        background_color: Optional[str] = None,
        indent_guides: bool = False,
        padding: PaddingDimensions = 0,
    ) -> "Syntax":
        """Construct a Syntax object from a file.

        Args:
            path (str): Path to file to highlight.
            encoding (str): Encoding of file.
            lexer (str | Lexer, optional): Lexer to use. If None, lexer will be auto-detected from path/file content.
            theme (str, optional): Color theme, aka Pygments style (see https://pygments.org/docs/styles/#getting-a-list-of-available-styles). Defaults to "emacs".
            dedent (bool, optional): Enable stripping of initial whitespace. Defaults to True.
            line_numbers (bool, optional): Enable rendering of line numbers. Defaults to False.
            start_line (int, optional): Starting number for line numbers. Defaults to 1.
            line_range (Tuple[int, int], optional): If given should be a tuple of the start and end line to render.
            highlight_lines (Set[int]): A set of line numbers to highlight.
            code_width: Width of code to render (not including line numbers), or ``None`` to use all available width.
            tab_size (int, optional): Size of tabs. Defaults to 4.
            word_wrap (bool, optional): Enable word wrapping of code.
            background_color (str, optional): Optional background color, or None to use theme color. Defaults to None.
            indent_guides (bool, optional): Show indent guides. Defaults to False.
            padding (PaddingDimensions): Padding to apply around the syntax. Defaults to 0 (no padding).

        Returns:
            [Syntax]: A Syntax object that may be printed to the console
        """
        code = Path(path).read_text(encoding=encoding)

        if not lexer:
            lexer = cls.guess_lexer(path, code=code)

        return cls(
            code,
            lexer,
            theme=theme,
            dedent=dedent,
            line_numbers=line_numbers,
            line_range=line_range,
            start_line=start_line,
            highlight_lines=highlight_lines,
            code_width=code_width,
            tab_size=tab_size,
            word_wrap=word_wrap,
            background_color=background_color,
            indent_guides=indent_guides,
            padding=padding,
        )

    @classmethod
    def guess_lexer(cls, path: str, code: Optional[str] = None) -> str:
        """Guess the alias of the Pygments lexer to use based on a path and an optional string of code.
        If code is supplied, it will use a combination of the code and the filename to determine the
        best lexer to use. For example, if the file is ``index.html`` and the file contains Django
        templating syntax, then "html+django" will be returned. If the file is ``index.html``, and no
        templating language is used, the "html" lexer will be used. If no string of code
        is supplied, the lexer will be chosen based on the file extension..

        Args:
             path (AnyStr): The path to the file containing the code you wish to know the lexer for.
             code (str, optional): Optional string of code that will be used as a fallback if no lexer
                is found for the supplied path.

        Returns:
            str: The name of the Pygments lexer that best matches the supplied path/code.
        """
        lexer: Optional[Lexer] = None
        lexer_name = "default"
        if code:
            try:
                lexer = guess_lexer_for_filename(path, code)
            except ClassNotFound:
                pass

        if not lexer:
            try:
                _, ext = os.path.splitext(path)
                if ext:
                    extension = ext.lstrip(".").lower()
                    lexer = get_lexer_by_name(extension)
            except ClassNotFound:
                pass

        if lexer:
            if lexer.aliases:
                lexer_name = lexer.aliases[0]
            else:
                lexer_name = lexer.name

        return lexer_name

    def _get_base_style(self) -> Style:
        """Get the base style."""
        default_style = self._theme.get_background_style() + self.background_style
        return default_style

    def _get_token_color(self, token_type: TokenType) -> Optional[Color]:
        """Get a color (if any) for the given token.

        Args:
            token_type (TokenType): A token type tuple from Pygments.

        Returns:
            Optional[Color]: Color from theme, or None for no color.
        """
        style = self._theme.get_style_for_token(token_type)
        return style.color

    @property
    def lexer(self) -> Optional[Lexer]:
        """The lexer for this syntax, or None if no lexer was found.

        Tries to find the lexer by name if a string was passed to the constructor.
        """

        if isinstance(self._lexer, Lexer):
            return self._lexer
        try:
            return get_lexer_by_name(
                self._lexer,
                stripnl=False,
                ensurenl=True,
                tabsize=self.tab_size,
            )
        except ClassNotFound:
            return None

    @property
    def default_lexer(self) -> Lexer:
        """A Pygments Lexer to use if one is not specified or invalid."""
        return get_lexer_by_name(
            "text",
            stripnl=False,
            ensurenl=True,
            tabsize=self.tab_size,
        )

    def highlight(
        self,
        code: str,
        line_range: Optional[Tuple[Optional[int], Optional[int]]] = None,
    ) -> Text:
        """Highlight code and return a Text instance.

        Args:
            code (str): Code to highlight.
            line_range(Tuple[int, int], optional): Optional line range to highlight.

        Returns:
            Text: A text instance containing highlighted syntax.
        """

        base_style = self._get_base_style()
        justify: JustifyMethod = (
            "default" if base_style.transparent_background else "left"
        )

        text = Text(
            justify=justify,
            style=base_style,
            tab_size=self.tab_size,
            no_wrap=not self.word_wrap,
        )
        _get_theme_style = self._theme.get_style_for_token

        lexer = self.lexer or self.default_lexer

        if lexer is None:
            text.append(code)
        else:
            if line_range:
                # More complicated path to only stylize a portion of the code
                # This speeds up further operations as there are less spans to process
                line_start, line_end = line_range

                def line_tokenize() -> Iterable[Tuple[Any, str]]:
                    """Split tokens to one per line."""
                    assert lexer  # required to make MyPy happy - we know lexer is not None at this point

                    for token_type, token in lexer.get_tokens(code):
                        while token:
                            line_token, new_line, token = token.partition("\n")
                            yield token_type, line_token + new_line

                def tokens_to_spans() -> Iterable[Tuple[str, Optional[Style]]]:
                    """Convert tokens to spans."""
                    tokens = iter(line_tokenize())
                    line_no = 0
                    _line_start = line_start - 1 if line_start else 0

                    # Skip over tokens until line start
                    while line_no < _line_start:
                        try:
                            _token_type, token = next(tokens)
                        except StopIteration:
                            break
                        yield (token, None)
                        if token.endswith("\n"):
                            line_no += 1
                    # Generate spans until line end
                    for token_type, token in tokens:
                        yield (token, _get_theme_style(token_type))
                        if token.endswith("\n"):
                            line_no += 1
                            if line_end and line_no >= line_end:
                                break

                text.append_tokens(tokens_to_spans())

            else:
                text.append_tokens(
                    (token, _get_theme_style(token_type))
                    for token_type, token in lexer.get_tokens(code)
                )
            if self.background_color is not None:
                text.stylize(f"on {self.background_color}")

        if self._stylized_ranges:
            self._apply_stylized_ranges(text)

        return text

    def stylize_range(
        self,
        style: StyleType,
        start: SyntaxPosition,
        end: SyntaxPosition,
        style_before: bool = False,
    ) -> None:
        """
        Adds a custom style on a part of the code, that will be applied to the syntax display when it's rendered.
        Line numbers are 1-based, while column indexes are 0-based.

        Args:
            style (StyleType): The style to apply.
            start (Tuple[int, int]): The start of the range, in the form `[line number, column index]`.
            end (Tuple[int, int]): The end of the range, in the form `[line number, column index]`.
            style_before (bool): Apply the style before any existing styles.
        """
        self._stylized_ranges.append(
            _SyntaxHighlightRange(style, start, end, style_before)
        )

    def _get_line_numbers_color(self, blend: float = 0.3) -> Color:
        background_style = self._theme.get_background_style() + self.background_style
        background_color = background_style.bgcolor
        if background_color is None or background_color.is_system_defined:
            return Color.default()
        foreground_color = self._get_token_color(Token.Text)
        if foreground_color is None or foreground_color.is_system_defined:
            return foreground_color or Color.default()
        new_color = blend_rgb(
            background_color.get_truecolor(),
            foreground_color.get_truecolor(),
            cross_fade=blend,
        )
        return Color.from_triplet(new_color)

    @property
    def _numbers_column_width(self) -> int:
        """Get the number of characters used to render the numbers column."""
        column_width = 0
        if self.line_numbers:
            column_width = (
                len(str(self.start_line + self.code.count("\n")))
                + NUMBERS_COLUMN_DEFAULT_PADDING
            )
        return column_width

    def _get_number_styles(self, console: Console) -> Tuple[Style, Style, Style]:
        """Get background, number, and highlight styles for line numbers."""
        background_style = self._get_base_style()
        if background_style.transparent_background:
            return Style.null(), Style(dim=True), Style.null()
        if console.color_system in ("256", "truecolor"):
            number_style = Style.chain(
                background_style,
                self._theme.get_style_for_token(Token.Text),
                Style(color=self._get_line_numbers_color()),
                self.background_style,
            )
            highlight_number_style = Style.chain(
                background_style,
                self._theme.get_style_for_token(Token.Text),
                Style(bold=True, color=self._get_line_numbers_color(0.9)),
                self.background_style,
            )
        else:
            number_style = background_style + Style(dim=True)
            highlight_number_style = background_style + Style(dim=False)
        return background_style, number_style, highlight_number_style

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        _, right, _, left = Padding.unpack(self.padding)
        padding = left + right
        if self.code_width is not None:
            width = self.code_width + self._numbers_column_width + padding + 1
            return Measurement(self._numbers_column_width, width)
        lines = self.code.splitlines()
        width = (
            self._numbers_column_width
            + padding
            + (max(cell_len(line) for line in lines) if lines else 0)
        )
        if self.line_numbers:
            width += 1
        return Measurement(self._numbers_column_width, width)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        segments = Segments(self._get_syntax(console, options))
        if self.padding:
            yield Padding(segments, style=self._get_base_style(), pad=self.padding)
        else:
            yield segments

    def _get_syntax(
        self,
        console: Console,
        options: ConsoleOptions,
    ) -> Iterable[Segment]:
        """
        Get the Segments for the Syntax object, excluding any vertical/horizontal padding
        """
        transparent_background = self._get_base_style().transparent_background
        code_width = (
            (
                (options.max_width - self._numbers_column_width - 1)
                if self.line_numbers
                else options.max_width
            )
            if self.code_width is None
            else self.code_width
        )

        ends_on_nl, processed_code = self._process_code(self.code)
        text = self.highlight(processed_code, self.line_range)

        if not self.line_numbers and not self.word_wrap and not self.line_range:
            if not ends_on_nl:
                text.remove_suffix("\n")
            # Simple case of just rendering text
            style = (
                self._get_base_style()
                + self._theme.get_style_for_token(Comment)
                + Style(dim=True)
                + self.background_style
            )
            if self.indent_guides and not options.ascii_only:
                text = text.with_indent_guides(self.tab_size, style=style)
                text.overflow = "crop"
            if style.transparent_background:
                yield from console.render(
                    text, options=options.update(width=code_width)
                )
            else:
                syntax_lines = console.render_lines(
                    text,
                    options.update(width=code_width, height=None, justify="left"),
                    style=self.background_style,
                    pad=True,
                    new_lines=True,
                )
                for syntax_line in syntax_lines:
                    yield from syntax_line
            return

        start_line, end_line = self.line_range or (None, None)
        line_offset = 0
        if start_line:
            line_offset = max(0, start_line - 1)
        lines: Union[List[Text], Lines] = text.split("\n", allow_blank=ends_on_nl)
        if self.line_range:
            if line_offset > len(lines):
                return
            lines = lines[line_offset:end_line]

        if self.indent_guides and not options.ascii_only:
            style = (
                self._get_base_style()
                + self._theme.get_style_for_token(Comment)
                + Style(dim=True)
                + self.background_style
            )
            lines = (
                Text("\n")
                .join(lines)
                .with_indent_guides(self.tab_size, style=style + Style(italic=False))
                .split("\n", allow_blank=True)
            )

        numbers_column_width = self._numbers_column_width
        render_options = options.update(width=code_width)

        highlight_line = self.highlight_lines.__contains__
        _Segment = Segment
        new_line = _Segment("\n")

        line_pointer = "> " if options.legacy_windows else "❱ "

        (
            background_style,
            number_style,
            highlight_number_style,
        ) = self._get_number_styles(console)

        for line_no, line in enumerate(lines, self.start_line + line_offset):
            if self.word_wrap:
                wrapped_lines = console.render_lines(
                    line,
                    render_options.update(height=None, justify="left"),
                    style=background_style,
                    pad=not transparent_background,
                )
            else:
                segments = list(line.render(console, end=""))
                if options.no_wrap:
                    wrapped_lines = [segments]
                else:
                    wrapped_lines = [
                        _Segment.adjust_line_length(
                            segments,
                            render_options.max_width,
                            style=background_style,
                            pad=not transparent_background,
                        )
                    ]

            if self.line_numbers:
                wrapped_line_left_pad = _Segment(
                    " " * numbers_column_width + " ", background_style
                )
                for first, wrapped_line in loop_first(wrapped_lines):
                    if first:
                        line_column = str(line_no).rjust(numbers_column_width - 2) + " "
                        if highlight_line(line_no):
                            yield _Segment(line_pointer, Style(color="red"))
                            yield _Segment(line_column, highlight_number_style)
                        else:
                            yield _Segment("  ", highlight_number_style)
                            yield _Segment(line_column, number_style)
                    else:
                        yield wrapped_line_left_pad
                    yield from wrapped_line
                    yield new_line
            else:
                for wrapped_line in wrapped_lines:
                    yield from wrapped_line
                    yield new_line

    def _apply_stylized_ranges(self, text: Text) -> None:
        """
        Apply stylized ranges to a text instance,
        using the given code to determine the right portion to apply the style to.

        Args:
            text (Text): Text instance to apply the style to.
        """
        code = text.plain
        newlines_offsets = [
            # Let's add outer boundaries at each side of the list:
            0,
            # N.B. using "\n" here is much faster than using metacharacters such as "^" or "\Z":
            *[
                match.start() + 1
                for match in re.finditer("\n", code, flags=re.MULTILINE)
            ],
            len(code) + 1,
        ]

        for stylized_range in self._stylized_ranges:
            start = _get_code_index_for_syntax_position(
                newlines_offsets, stylized_range.start
            )
            end = _get_code_index_for_syntax_position(
                newlines_offsets, stylized_range.end
            )
            if start is not None and end is not None:
                if stylized_range.style_before:
                    text.stylize_before(stylized_range.style, start, end)
                else:
                    text.stylize(stylized_range.style, start, end)

    def _process_code(self, code: str) -> Tuple[bool, str]:
        """
        Applies various processing to a raw code string
        (normalises it so it always ends with a line return, dedents it if necessary, etc.)

        Args:
            code (str): The raw code string to process

        Returns:
            Tuple[bool, str]: the boolean indicates whether the raw code ends with a line return,
                while the string is the processed code.
        """
        ends_on_nl = code.endswith("\n")
        processed_code = code if ends_on_nl else code + "\n"
        processed_code = (
            textwrap.dedent(processed_code) if self.dedent else processed_code
        )
        processed_code = processed_code.expandtabs(self.tab_size)
        return ends_on_nl, processed_code


def _get_code_index_for_syntax_position(
    newlines_offsets: Sequence[int], position: SyntaxPosition
) -> Optional[int]:
    """
    Returns the index of the code string for the given positions.

    Args:
        newlines_offsets (Sequence[int]): The offset of each newline character found in the code snippet.
        position (SyntaxPosition): The position to search for.

    Returns:
        Optional[int]: The index of the code string for this position, or `None`
            if the given position's line number is out of range (if it's the column that is out of range
            we silently clamp its value so that it reaches the end of the line)
    """
    lines_count = len(newlines_offsets)

    line_number, column_index = position
    if line_number > lines_count or len(newlines_offsets) < (line_number + 1):
        return None  # `line_number` is out of range
    line_index = line_number - 1
    line_length = newlines_offsets[line_index + 1] - newlines_offsets[line_index] - 1
    # If `column_index` is out of range: let's silently clamp it:
    column_index = min(line_length, column_index)
    return newlines_offsets[line_index] + column_index


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Render syntax to the console with Rich"
    )
    parser.add_argument(
        "path",
        metavar="PATH",
        help="path to file, or - for stdin",
    )
    parser.add_argument(
        "-c",
        "--force-color",
        dest="force_color",
        action="store_true",
        default=None,
        help="force color for non-terminals",
    )
    parser.add_argument(
        "-i",
        "--indent-guides",
        dest="indent_guides",
        action="store_true",
        default=False,
        help="display indent guides",
    )
    parser.add_argument(
        "-l",
        "--line-numbers",
        dest="line_numbers",
        action="store_true",
        help="render line numbers",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        dest="width",
        default=None,
        help="width of output (default will auto-detect)",
    )
    parser.add_argument(
        "-r",
        "--wrap",
        dest="word_wrap",
        action="store_true",
        default=False,
        help="word wrap long lines",
    )
    parser.add_argument(
        "-s",
        "--soft-wrap",
        action="store_true",
        dest="soft_wrap",
        default=False,
        help="enable soft wrapping mode",
    )
    parser.add_argument(
        "-t", "--theme", dest="theme", default="monokai", help="pygments theme"
    )
    parser.add_argument(
        "-b",
        "--background-color",
        dest="background_color",
        default=None,
        help="Override background color",
    )
    parser.add_argument(
        "-x",
        "--lexer",
        default=None,
        dest="lexer_name",
        help="Lexer name",
    )
    parser.add_argument(
        "-p", "--padding", type=int, default=0, dest="padding", help="Padding"
    )
    parser.add_argument(
        "--highlight-line",
        type=int,
        default=None,
        dest="highlight_line",
        help="The line number (not index!) to highlight",
    )
    args = parser.parse_args()

    from rich.console import Console

    console = Console(force_terminal=args.force_color, width=args.width)

    if args.path == "-":
        code = sys.stdin.read()
        syntax = Syntax(
            code=code,
            lexer=args.lexer_name,
            line_numbers=args.line_numbers,
            word_wrap=args.word_wrap,
            theme=args.theme,
            background_color=args.background_color,
            indent_guides=args.indent_guides,
            padding=args.padding,
            highlight_lines={args.highlight_line},
        )
    else:
        syntax = Syntax.from_path(
            args.path,
            lexer=args.lexer_name,
            line_numbers=args.line_numbers,
            word_wrap=args.word_wrap,
            theme=args.theme,
            background_color=args.background_color,
            indent_guides=args.indent_guides,
            padding=args.padding,
            highlight_lines={args.highlight_line},
        )
    console.print(syntax, soft_wrap=args.soft_wrap)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\syntax.py ===
import os.path
import re
import sys
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

from pip._vendor.pygments.lexer import Lexer
from pip._vendor.pygments.lexers import get_lexer_by_name, guess_lexer_for_filename
from pip._vendor.pygments.style import Style as PygmentsStyle
from pip._vendor.pygments.styles import get_style_by_name
from pip._vendor.pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Token,
    Whitespace,
)
from pip._vendor.pygments.util import ClassNotFound

from pip._vendor.rich.containers import Lines
from pip._vendor.rich.padding import Padding, PaddingDimensions

from ._loop import loop_first
from .cells import cell_len
from .color import Color, blend_rgb
from .console import Console, ConsoleOptions, JustifyMethod, RenderResult
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment, Segments
from .style import Style, StyleType
from .text import Text

TokenType = Tuple[str, ...]

WINDOWS = sys.platform == "win32"
DEFAULT_THEME = "monokai"

# The following styles are based on https://github.com/pygments/pygments/blob/master/pygments/formatters/terminal.py
# A few modifications were made

ANSI_LIGHT: Dict[TokenType, Style] = {
    Token: Style(),
    Whitespace: Style(color="white"),
    Comment: Style(dim=True),
    Comment.Preproc: Style(color="cyan"),
    Keyword: Style(color="blue"),
    Keyword.Type: Style(color="cyan"),
    Operator.Word: Style(color="magenta"),
    Name.Builtin: Style(color="cyan"),
    Name.Function: Style(color="green"),
    Name.Namespace: Style(color="cyan", underline=True),
    Name.Class: Style(color="green", underline=True),
    Name.Exception: Style(color="cyan"),
    Name.Decorator: Style(color="magenta", bold=True),
    Name.Variable: Style(color="red"),
    Name.Constant: Style(color="red"),
    Name.Attribute: Style(color="cyan"),
    Name.Tag: Style(color="bright_blue"),
    String: Style(color="yellow"),
    Number: Style(color="blue"),
    Generic.Deleted: Style(color="bright_red"),
    Generic.Inserted: Style(color="green"),
    Generic.Heading: Style(bold=True),
    Generic.Subheading: Style(color="magenta", bold=True),
    Generic.Prompt: Style(bold=True),
    Generic.Error: Style(color="bright_red"),
    Error: Style(color="red", underline=True),
}

ANSI_DARK: Dict[TokenType, Style] = {
    Token: Style(),
    Whitespace: Style(color="bright_black"),
    Comment: Style(dim=True),
    Comment.Preproc: Style(color="bright_cyan"),
    Keyword: Style(color="bright_blue"),
    Keyword.Type: Style(color="bright_cyan"),
    Operator.Word: Style(color="bright_magenta"),
    Name.Builtin: Style(color="bright_cyan"),
    Name.Function: Style(color="bright_green"),
    Name.Namespace: Style(color="bright_cyan", underline=True),
    Name.Class: Style(color="bright_green", underline=True),
    Name.Exception: Style(color="bright_cyan"),
    Name.Decorator: Style(color="bright_magenta", bold=True),
    Name.Variable: Style(color="bright_red"),
    Name.Constant: Style(color="bright_red"),
    Name.Attribute: Style(color="bright_cyan"),
    Name.Tag: Style(color="bright_blue"),
    String: Style(color="yellow"),
    Number: Style(color="bright_blue"),
    Generic.Deleted: Style(color="bright_red"),
    Generic.Inserted: Style(color="bright_green"),
    Generic.Heading: Style(bold=True),
    Generic.Subheading: Style(color="bright_magenta", bold=True),
    Generic.Prompt: Style(bold=True),
    Generic.Error: Style(color="bright_red"),
    Error: Style(color="red", underline=True),
}

RICH_SYNTAX_THEMES = {"ansi_light": ANSI_LIGHT, "ansi_dark": ANSI_DARK}
NUMBERS_COLUMN_DEFAULT_PADDING = 2


class SyntaxTheme(ABC):
    """Base class for a syntax theme."""

    @abstractmethod
    def get_style_for_token(self, token_type: TokenType) -> Style:
        """Get a style for a given Pygments token."""
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def get_background_style(self) -> Style:
        """Get the background color."""
        raise NotImplementedError  # pragma: no cover


class PygmentsSyntaxTheme(SyntaxTheme):
    """Syntax theme that delegates to Pygments theme."""

    def __init__(self, theme: Union[str, Type[PygmentsStyle]]) -> None:
        self._style_cache: Dict[TokenType, Style] = {}
        if isinstance(theme, str):
            try:
                self._pygments_style_class = get_style_by_name(theme)
            except ClassNotFound:
                self._pygments_style_class = get_style_by_name("default")
        else:
            self._pygments_style_class = theme

        self._background_color = self._pygments_style_class.background_color
        self._background_style = Style(bgcolor=self._background_color)

    def get_style_for_token(self, token_type: TokenType) -> Style:
        """Get a style from a Pygments class."""
        try:
            return self._style_cache[token_type]
        except KeyError:
            try:
                pygments_style = self._pygments_style_class.style_for_token(token_type)
            except KeyError:
                style = Style.null()
            else:
                color = pygments_style["color"]
                bgcolor = pygments_style["bgcolor"]
                style = Style(
                    color="#" + color if color else "#000000",
                    bgcolor="#" + bgcolor if bgcolor else self._background_color,
                    bold=pygments_style["bold"],
                    italic=pygments_style["italic"],
                    underline=pygments_style["underline"],
                )
            self._style_cache[token_type] = style
        return style

    def get_background_style(self) -> Style:
        return self._background_style


class ANSISyntaxTheme(SyntaxTheme):
    """Syntax theme to use standard colors."""

    def __init__(self, style_map: Dict[TokenType, Style]) -> None:
        self.style_map = style_map
        self._missing_style = Style.null()
        self._background_style = Style.null()
        self._style_cache: Dict[TokenType, Style] = {}

    def get_style_for_token(self, token_type: TokenType) -> Style:
        """Look up style in the style map."""
        try:
            return self._style_cache[token_type]
        except KeyError:
            # Styles form a hierarchy
            # We need to go from most to least specific
            # e.g. ("foo", "bar", "baz") to ("foo", "bar")  to ("foo",)
            get_style = self.style_map.get
            token = tuple(token_type)
            style = self._missing_style
            while token:
                _style = get_style(token)
                if _style is not None:
                    style = _style
                    break
                token = token[:-1]
            self._style_cache[token_type] = style
            return style

    def get_background_style(self) -> Style:
        return self._background_style


SyntaxPosition = Tuple[int, int]


class _SyntaxHighlightRange(NamedTuple):
    """
    A range to highlight in a Syntax object.
    `start` and `end` are 2-integers tuples, where the first integer is the line number
    (starting from 1) and the second integer is the column index (starting from 0).
    """

    style: StyleType
    start: SyntaxPosition
    end: SyntaxPosition
    style_before: bool = False


class Syntax(JupyterMixin):
    """Construct a Syntax object to render syntax highlighted code.

    Args:
        code (str): Code to highlight.
        lexer (Lexer | str): Lexer to use (see https://pygments.org/docs/lexers/)
        theme (str, optional): Color theme, aka Pygments style (see https://pygments.org/docs/styles/#getting-a-list-of-available-styles). Defaults to "monokai".
        dedent (bool, optional): Enable stripping of initial whitespace. Defaults to False.
        line_numbers (bool, optional): Enable rendering of line numbers. Defaults to False.
        start_line (int, optional): Starting number for line numbers. Defaults to 1.
        line_range (Tuple[int | None, int | None], optional): If given should be a tuple of the start and end line to render.
            A value of None in the tuple indicates the range is open in that direction.
        highlight_lines (Set[int]): A set of line numbers to highlight.
        code_width: Width of code to render (not including line numbers), or ``None`` to use all available width.
        tab_size (int, optional): Size of tabs. Defaults to 4.
        word_wrap (bool, optional): Enable word wrapping.
        background_color (str, optional): Optional background color, or None to use theme color. Defaults to None.
        indent_guides (bool, optional): Show indent guides. Defaults to False.
        padding (PaddingDimensions): Padding to apply around the syntax. Defaults to 0 (no padding).
    """

    _pygments_style_class: Type[PygmentsStyle]
    _theme: SyntaxTheme

    @classmethod
    def get_theme(cls, name: Union[str, SyntaxTheme]) -> SyntaxTheme:
        """Get a syntax theme instance."""
        if isinstance(name, SyntaxTheme):
            return name
        theme: SyntaxTheme
        if name in RICH_SYNTAX_THEMES:
            theme = ANSISyntaxTheme(RICH_SYNTAX_THEMES[name])
        else:
            theme = PygmentsSyntaxTheme(name)
        return theme

    def __init__(
        self,
        code: str,
        lexer: Union[Lexer, str],
        *,
        theme: Union[str, SyntaxTheme] = DEFAULT_THEME,
        dedent: bool = False,
        line_numbers: bool = False,
        start_line: int = 1,
        line_range: Optional[Tuple[Optional[int], Optional[int]]] = None,
        highlight_lines: Optional[Set[int]] = None,
        code_width: Optional[int] = None,
        tab_size: int = 4,
        word_wrap: bool = False,
        background_color: Optional[str] = None,
        indent_guides: bool = False,
        padding: PaddingDimensions = 0,
    ) -> None:
        self.code = code
        self._lexer = lexer
        self.dedent = dedent
        self.line_numbers = line_numbers
        self.start_line = start_line
        self.line_range = line_range
        self.highlight_lines = highlight_lines or set()
        self.code_width = code_width
        self.tab_size = tab_size
        self.word_wrap = word_wrap
        self.background_color = background_color
        self.background_style = (
            Style(bgcolor=background_color) if background_color else Style()
        )
        self.indent_guides = indent_guides
        self.padding = padding

        self._theme = self.get_theme(theme)
        self._stylized_ranges: List[_SyntaxHighlightRange] = []

    @classmethod
    def from_path(
        cls,
        path: str,
        encoding: str = "utf-8",
        lexer: Optional[Union[Lexer, str]] = None,
        theme: Union[str, SyntaxTheme] = DEFAULT_THEME,
        dedent: bool = False,
        line_numbers: bool = False,
        line_range: Optional[Tuple[int, int]] = None,
        start_line: int = 1,
        highlight_lines: Optional[Set[int]] = None,
        code_width: Optional[int] = None,
        tab_size: int = 4,
        word_wrap: bool = False,
        background_color: Optional[str] = None,
        indent_guides: bool = False,
        padding: PaddingDimensions = 0,
    ) -> "Syntax":
        """Construct a Syntax object from a file.

        Args:
            path (str): Path to file to highlight.
            encoding (str): Encoding of file.
            lexer (str | Lexer, optional): Lexer to use. If None, lexer will be auto-detected from path/file content.
            theme (str, optional): Color theme, aka Pygments style (see https://pygments.org/docs/styles/#getting-a-list-of-available-styles). Defaults to "emacs".
            dedent (bool, optional): Enable stripping of initial whitespace. Defaults to True.
            line_numbers (bool, optional): Enable rendering of line numbers. Defaults to False.
            start_line (int, optional): Starting number for line numbers. Defaults to 1.
            line_range (Tuple[int, int], optional): If given should be a tuple of the start and end line to render.
            highlight_lines (Set[int]): A set of line numbers to highlight.
            code_width: Width of code to render (not including line numbers), or ``None`` to use all available width.
            tab_size (int, optional): Size of tabs. Defaults to 4.
            word_wrap (bool, optional): Enable word wrapping of code.
            background_color (str, optional): Optional background color, or None to use theme color. Defaults to None.
            indent_guides (bool, optional): Show indent guides. Defaults to False.
            padding (PaddingDimensions): Padding to apply around the syntax. Defaults to 0 (no padding).

        Returns:
            [Syntax]: A Syntax object that may be printed to the console
        """
        code = Path(path).read_text(encoding=encoding)

        if not lexer:
            lexer = cls.guess_lexer(path, code=code)

        return cls(
            code,
            lexer,
            theme=theme,
            dedent=dedent,
            line_numbers=line_numbers,
            line_range=line_range,
            start_line=start_line,
            highlight_lines=highlight_lines,
            code_width=code_width,
            tab_size=tab_size,
            word_wrap=word_wrap,
            background_color=background_color,
            indent_guides=indent_guides,
            padding=padding,
        )

    @classmethod
    def guess_lexer(cls, path: str, code: Optional[str] = None) -> str:
        """Guess the alias of the Pygments lexer to use based on a path and an optional string of code.
        If code is supplied, it will use a combination of the code and the filename to determine the
        best lexer to use. For example, if the file is ``index.html`` and the file contains Django
        templating syntax, then "html+django" will be returned. If the file is ``index.html``, and no
        templating language is used, the "html" lexer will be used. If no string of code
        is supplied, the lexer will be chosen based on the file extension..

        Args:
             path (AnyStr): The path to the file containing the code you wish to know the lexer for.
             code (str, optional): Optional string of code that will be used as a fallback if no lexer
                is found for the supplied path.

        Returns:
            str: The name of the Pygments lexer that best matches the supplied path/code.
        """
        lexer: Optional[Lexer] = None
        lexer_name = "default"
        if code:
            try:
                lexer = guess_lexer_for_filename(path, code)
            except ClassNotFound:
                pass

        if not lexer:
            try:
                _, ext = os.path.splitext(path)
                if ext:
                    extension = ext.lstrip(".").lower()
                    lexer = get_lexer_by_name(extension)
            except ClassNotFound:
                pass

        if lexer:
            if lexer.aliases:
                lexer_name = lexer.aliases[0]
            else:
                lexer_name = lexer.name

        return lexer_name

    def _get_base_style(self) -> Style:
        """Get the base style."""
        default_style = self._theme.get_background_style() + self.background_style
        return default_style

    def _get_token_color(self, token_type: TokenType) -> Optional[Color]:
        """Get a color (if any) for the given token.

        Args:
            token_type (TokenType): A token type tuple from Pygments.

        Returns:
            Optional[Color]: Color from theme, or None for no color.
        """
        style = self._theme.get_style_for_token(token_type)
        return style.color

    @property
    def lexer(self) -> Optional[Lexer]:
        """The lexer for this syntax, or None if no lexer was found.

        Tries to find the lexer by name if a string was passed to the constructor.
        """

        if isinstance(self._lexer, Lexer):
            return self._lexer
        try:
            return get_lexer_by_name(
                self._lexer,
                stripnl=False,
                ensurenl=True,
                tabsize=self.tab_size,
            )
        except ClassNotFound:
            return None

    @property
    def default_lexer(self) -> Lexer:
        """A Pygments Lexer to use if one is not specified or invalid."""
        return get_lexer_by_name(
            "text",
            stripnl=False,
            ensurenl=True,
            tabsize=self.tab_size,
        )

    def highlight(
        self,
        code: str,
        line_range: Optional[Tuple[Optional[int], Optional[int]]] = None,
    ) -> Text:
        """Highlight code and return a Text instance.

        Args:
            code (str): Code to highlight.
            line_range(Tuple[int, int], optional): Optional line range to highlight.

        Returns:
            Text: A text instance containing highlighted syntax.
        """

        base_style = self._get_base_style()
        justify: JustifyMethod = (
            "default" if base_style.transparent_background else "left"
        )

        text = Text(
            justify=justify,
            style=base_style,
            tab_size=self.tab_size,
            no_wrap=not self.word_wrap,
        )
        _get_theme_style = self._theme.get_style_for_token

        lexer = self.lexer or self.default_lexer

        if lexer is None:
            text.append(code)
        else:
            if line_range:
                # More complicated path to only stylize a portion of the code
                # This speeds up further operations as there are less spans to process
                line_start, line_end = line_range

                def line_tokenize() -> Iterable[Tuple[Any, str]]:
                    """Split tokens to one per line."""
                    assert lexer  # required to make MyPy happy - we know lexer is not None at this point

                    for token_type, token in lexer.get_tokens(code):
                        while token:
                            line_token, new_line, token = token.partition("\n")
                            yield token_type, line_token + new_line

                def tokens_to_spans() -> Iterable[Tuple[str, Optional[Style]]]:
                    """Convert tokens to spans."""
                    tokens = iter(line_tokenize())
                    line_no = 0
                    _line_start = line_start - 1 if line_start else 0

                    # Skip over tokens until line start
                    while line_no < _line_start:
                        try:
                            _token_type, token = next(tokens)
                        except StopIteration:
                            break
                        yield (token, None)
                        if token.endswith("\n"):
                            line_no += 1
                    # Generate spans until line end
                    for token_type, token in tokens:
                        yield (token, _get_theme_style(token_type))
                        if token.endswith("\n"):
                            line_no += 1
                            if line_end and line_no >= line_end:
                                break

                text.append_tokens(tokens_to_spans())

            else:
                text.append_tokens(
                    (token, _get_theme_style(token_type))
                    for token_type, token in lexer.get_tokens(code)
                )
            if self.background_color is not None:
                text.stylize(f"on {self.background_color}")

        if self._stylized_ranges:
            self._apply_stylized_ranges(text)

        return text

    def stylize_range(
        self,
        style: StyleType,
        start: SyntaxPosition,
        end: SyntaxPosition,
        style_before: bool = False,
    ) -> None:
        """
        Adds a custom style on a part of the code, that will be applied to the syntax display when it's rendered.
        Line numbers are 1-based, while column indexes are 0-based.

        Args:
            style (StyleType): The style to apply.
            start (Tuple[int, int]): The start of the range, in the form `[line number, column index]`.
            end (Tuple[int, int]): The end of the range, in the form `[line number, column index]`.
            style_before (bool): Apply the style before any existing styles.
        """
        self._stylized_ranges.append(
            _SyntaxHighlightRange(style, start, end, style_before)
        )

    def _get_line_numbers_color(self, blend: float = 0.3) -> Color:
        background_style = self._theme.get_background_style() + self.background_style
        background_color = background_style.bgcolor
        if background_color is None or background_color.is_system_defined:
            return Color.default()
        foreground_color = self._get_token_color(Token.Text)
        if foreground_color is None or foreground_color.is_system_defined:
            return foreground_color or Color.default()
        new_color = blend_rgb(
            background_color.get_truecolor(),
            foreground_color.get_truecolor(),
            cross_fade=blend,
        )
        return Color.from_triplet(new_color)

    @property
    def _numbers_column_width(self) -> int:
        """Get the number of characters used to render the numbers column."""
        column_width = 0
        if self.line_numbers:
            column_width = (
                len(str(self.start_line + self.code.count("\n")))
                + NUMBERS_COLUMN_DEFAULT_PADDING
            )
        return column_width

    def _get_number_styles(self, console: Console) -> Tuple[Style, Style, Style]:
        """Get background, number, and highlight styles for line numbers."""
        background_style = self._get_base_style()
        if background_style.transparent_background:
            return Style.null(), Style(dim=True), Style.null()
        if console.color_system in ("256", "truecolor"):
            number_style = Style.chain(
                background_style,
                self._theme.get_style_for_token(Token.Text),
                Style(color=self._get_line_numbers_color()),
                self.background_style,
            )
            highlight_number_style = Style.chain(
                background_style,
                self._theme.get_style_for_token(Token.Text),
                Style(bold=True, color=self._get_line_numbers_color(0.9)),
                self.background_style,
            )
        else:
            number_style = background_style + Style(dim=True)
            highlight_number_style = background_style + Style(dim=False)
        return background_style, number_style, highlight_number_style

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        _, right, _, left = Padding.unpack(self.padding)
        padding = left + right
        if self.code_width is not None:
            width = self.code_width + self._numbers_column_width + padding + 1
            return Measurement(self._numbers_column_width, width)
        lines = self.code.splitlines()
        width = (
            self._numbers_column_width
            + padding
            + (max(cell_len(line) for line in lines) if lines else 0)
        )
        if self.line_numbers:
            width += 1
        return Measurement(self._numbers_column_width, width)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        segments = Segments(self._get_syntax(console, options))
        if self.padding:
            yield Padding(segments, style=self._get_base_style(), pad=self.padding)
        else:
            yield segments

    def _get_syntax(
        self,
        console: Console,
        options: ConsoleOptions,
    ) -> Iterable[Segment]:
        """
        Get the Segments for the Syntax object, excluding any vertical/horizontal padding
        """
        transparent_background = self._get_base_style().transparent_background
        code_width = (
            (
                (options.max_width - self._numbers_column_width - 1)
                if self.line_numbers
                else options.max_width
            )
            if self.code_width is None
            else self.code_width
        )

        ends_on_nl, processed_code = self._process_code(self.code)
        text = self.highlight(processed_code, self.line_range)

        if not self.line_numbers and not self.word_wrap and not self.line_range:
            if not ends_on_nl:
                text.remove_suffix("\n")
            # Simple case of just rendering text
            style = (
                self._get_base_style()
                + self._theme.get_style_for_token(Comment)
                + Style(dim=True)
                + self.background_style
            )
            if self.indent_guides and not options.ascii_only:
                text = text.with_indent_guides(self.tab_size, style=style)
                text.overflow = "crop"
            if style.transparent_background:
                yield from console.render(
                    text, options=options.update(width=code_width)
                )
            else:
                syntax_lines = console.render_lines(
                    text,
                    options.update(width=code_width, height=None, justify="left"),
                    style=self.background_style,
                    pad=True,
                    new_lines=True,
                )
                for syntax_line in syntax_lines:
                    yield from syntax_line
            return

        start_line, end_line = self.line_range or (None, None)
        line_offset = 0
        if start_line:
            line_offset = max(0, start_line - 1)
        lines: Union[List[Text], Lines] = text.split("\n", allow_blank=ends_on_nl)
        if self.line_range:
            if line_offset > len(lines):
                return
            lines = lines[line_offset:end_line]

        if self.indent_guides and not options.ascii_only:
            style = (
                self._get_base_style()
                + self._theme.get_style_for_token(Comment)
                + Style(dim=True)
                + self.background_style
            )
            lines = (
                Text("\n")
                .join(lines)
                .with_indent_guides(self.tab_size, style=style + Style(italic=False))
                .split("\n", allow_blank=True)
            )

        numbers_column_width = self._numbers_column_width
        render_options = options.update(width=code_width)

        highlight_line = self.highlight_lines.__contains__
        _Segment = Segment
        new_line = _Segment("\n")

        line_pointer = "> " if options.legacy_windows else "❱ "

        (
            background_style,
            number_style,
            highlight_number_style,
        ) = self._get_number_styles(console)

        for line_no, line in enumerate(lines, self.start_line + line_offset):
            if self.word_wrap:
                wrapped_lines = console.render_lines(
                    line,
                    render_options.update(height=None, justify="left"),
                    style=background_style,
                    pad=not transparent_background,
                )
            else:
                segments = list(line.render(console, end=""))
                if options.no_wrap:
                    wrapped_lines = [segments]
                else:
                    wrapped_lines = [
                        _Segment.adjust_line_length(
                            segments,
                            render_options.max_width,
                            style=background_style,
                            pad=not transparent_background,
                        )
                    ]

            if self.line_numbers:
                wrapped_line_left_pad = _Segment(
                    " " * numbers_column_width + " ", background_style
                )
                for first, wrapped_line in loop_first(wrapped_lines):
                    if first:
                        line_column = str(line_no).rjust(numbers_column_width - 2) + " "
                        if highlight_line(line_no):
                            yield _Segment(line_pointer, Style(color="red"))
                            yield _Segment(line_column, highlight_number_style)
                        else:
                            yield _Segment("  ", highlight_number_style)
                            yield _Segment(line_column, number_style)
                    else:
                        yield wrapped_line_left_pad
                    yield from wrapped_line
                    yield new_line
            else:
                for wrapped_line in wrapped_lines:
                    yield from wrapped_line
                    yield new_line

    def _apply_stylized_ranges(self, text: Text) -> None:
        """
        Apply stylized ranges to a text instance,
        using the given code to determine the right portion to apply the style to.

        Args:
            text (Text): Text instance to apply the style to.
        """
        code = text.plain
        newlines_offsets = [
            # Let's add outer boundaries at each side of the list:
            0,
            # N.B. using "\n" here is much faster than using metacharacters such as "^" or "\Z":
            *[
                match.start() + 1
                for match in re.finditer("\n", code, flags=re.MULTILINE)
            ],
            len(code) + 1,
        ]

        for stylized_range in self._stylized_ranges:
            start = _get_code_index_for_syntax_position(
                newlines_offsets, stylized_range.start
            )
            end = _get_code_index_for_syntax_position(
                newlines_offsets, stylized_range.end
            )
            if start is not None and end is not None:
                if stylized_range.style_before:
                    text.stylize_before(stylized_range.style, start, end)
                else:
                    text.stylize(stylized_range.style, start, end)

    def _process_code(self, code: str) -> Tuple[bool, str]:
        """
        Applies various processing to a raw code string
        (normalises it so it always ends with a line return, dedents it if necessary, etc.)

        Args:
            code (str): The raw code string to process

        Returns:
            Tuple[bool, str]: the boolean indicates whether the raw code ends with a line return,
                while the string is the processed code.
        """
        ends_on_nl = code.endswith("\n")
        processed_code = code if ends_on_nl else code + "\n"
        processed_code = (
            textwrap.dedent(processed_code) if self.dedent else processed_code
        )
        processed_code = processed_code.expandtabs(self.tab_size)
        return ends_on_nl, processed_code


def _get_code_index_for_syntax_position(
    newlines_offsets: Sequence[int], position: SyntaxPosition
) -> Optional[int]:
    """
    Returns the index of the code string for the given positions.

    Args:
        newlines_offsets (Sequence[int]): The offset of each newline character found in the code snippet.
        position (SyntaxPosition): The position to search for.

    Returns:
        Optional[int]: The index of the code string for this position, or `None`
            if the given position's line number is out of range (if it's the column that is out of range
            we silently clamp its value so that it reaches the end of the line)
    """
    lines_count = len(newlines_offsets)

    line_number, column_index = position
    if line_number > lines_count or len(newlines_offsets) < (line_number + 1):
        return None  # `line_number` is out of range
    line_index = line_number - 1
    line_length = newlines_offsets[line_index + 1] - newlines_offsets[line_index] - 1
    # If `column_index` is out of range: let's silently clamp it:
    column_index = min(line_length, column_index)
    return newlines_offsets[line_index] + column_index


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Render syntax to the console with Rich"
    )
    parser.add_argument(
        "path",
        metavar="PATH",
        help="path to file, or - for stdin",
    )
    parser.add_argument(
        "-c",
        "--force-color",
        dest="force_color",
        action="store_true",
        default=None,
        help="force color for non-terminals",
    )
    parser.add_argument(
        "-i",
        "--indent-guides",
        dest="indent_guides",
        action="store_true",
        default=False,
        help="display indent guides",
    )
    parser.add_argument(
        "-l",
        "--line-numbers",
        dest="line_numbers",
        action="store_true",
        help="render line numbers",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        dest="width",
        default=None,
        help="width of output (default will auto-detect)",
    )
    parser.add_argument(
        "-r",
        "--wrap",
        dest="word_wrap",
        action="store_true",
        default=False,
        help="word wrap long lines",
    )
    parser.add_argument(
        "-s",
        "--soft-wrap",
        action="store_true",
        dest="soft_wrap",
        default=False,
        help="enable soft wrapping mode",
    )
    parser.add_argument(
        "-t", "--theme", dest="theme", default="monokai", help="pygments theme"
    )
    parser.add_argument(
        "-b",
        "--background-color",
        dest="background_color",
        default=None,
        help="Override background color",
    )
    parser.add_argument(
        "-x",
        "--lexer",
        default=None,
        dest="lexer_name",
        help="Lexer name",
    )
    parser.add_argument(
        "-p", "--padding", type=int, default=0, dest="padding", help="Padding"
    )
    parser.add_argument(
        "--highlight-line",
        type=int,
        default=None,
        dest="highlight_line",
        help="The line number (not index!) to highlight",
    )
    args = parser.parse_args()

    from pip._vendor.rich.console import Console

    console = Console(force_terminal=args.force_color, width=args.width)

    if args.path == "-":
        code = sys.stdin.read()
        syntax = Syntax(
            code=code,
            lexer=args.lexer_name,
            line_numbers=args.line_numbers,
            word_wrap=args.word_wrap,
            theme=args.theme,
            background_color=args.background_color,
            indent_guides=args.indent_guides,
            padding=args.padding,
            highlight_lines={args.highlight_line},
        )
    else:
        syntax = Syntax.from_path(
            args.path,
            lexer=args.lexer_name,
            line_numbers=args.line_numbers,
            word_wrap=args.word_wrap,
            theme=args.theme,
            background_color=args.background_color,
            indent_guides=args.indent_guides,
            padding=args.padding,
            highlight_lines={args.highlight_line},
        )
    console.print(syntax, soft_wrap=args.soft_wrap)

# === NexusCore/openenv\Lib\site-packages\trio\_ssl.py ===
from __future__ import annotations

import contextlib
import operator as _operator
import ssl as _stdlib_ssl
from enum import Enum as _Enum
from typing import TYPE_CHECKING, Any, ClassVar, Final as TFinal, Generic, TypeVar

import trio

from . import _sync
from ._highlevel_generic import aclose_forcefully
from ._util import ConflictDetector, final
from .abc import Listener, Stream

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from typing_extensions import TypeVarTuple, Unpack

    Ts = TypeVarTuple("Ts")

# General theory of operation:
#
# We implement an API that closely mirrors the stdlib ssl module's blocking
# API, and we do it using the stdlib ssl module's non-blocking in-memory API.
# The stdlib non-blocking in-memory API is barely documented, and acts as a
# thin wrapper around openssl, whose documentation also leaves something to be
# desired. So here's the main things you need to know to understand the code
# in this file:
#
# We use an ssl.SSLObject, which exposes the four main I/O operations:
#
# - do_handshake: performs the initial handshake. Must be called once at the
#   beginning of each connection; is a no-op once it's completed once.
#
# - write: takes some unencrypted data and attempts to send it to the remote
#   peer.

# - read: attempts to decrypt and return some data from the remote peer.
#
# - unwrap: this is weirdly named; maybe it helps to realize that the thing it
#   wraps is called SSL_shutdown. It sends a cryptographically signed message
#   saying "I'm closing this connection now", and then waits to receive the
#   same from the remote peer (unless we already received one, in which case
#   it returns immediately).
#
# All of these operations read and write from some in-memory buffers called
# "BIOs", which are an opaque OpenSSL-specific object that's basically
# semantically equivalent to a Python bytearray. When they want to send some
# bytes to the remote peer, they append them to the outgoing BIO, and when
# they want to receive some bytes from the remote peer, they try to pull them
# out of the incoming BIO. "Sending" always succeeds, because the outgoing BIO
# can always be extended to hold more data. "Receiving" acts sort of like a
# non-blocking socket: it might manage to get some data immediately, or it
# might fail and need to be tried again later. We can also directly add or
# remove data from the BIOs whenever we want.
#
# Now the problem is that while these I/O operations are opaque atomic
# operations from the point of view of us calling them, under the hood they
# might require some arbitrary sequence of sends and receives from the remote
# peer. This is particularly true for do_handshake, which generally requires a
# few round trips, but it's also true for write and read, due to an evil thing
# called "renegotiation".
#
# Renegotiation is the process by which one of the peers might arbitrarily
# decide to redo the handshake at any time. Did I mention it's evil? It's
# pretty evil, and almost universally hated. The HTTP/2 spec forbids the use
# of TLS renegotiation for HTTP/2 connections. TLS 1.3 removes it from the
# protocol entirely. It's impossible to trigger a renegotiation if using
# Python's ssl module. OpenSSL's renegotiation support is pretty buggy [1].
# Nonetheless, it does get used in real life, mostly in two cases:
#
# 1) Normally in TLS 1.2 and below, when the client side of a connection wants
# to present a certificate to prove their identity, that certificate gets sent
# in plaintext. This is bad, because it means that anyone eavesdropping can
# see who's connecting – it's like sending your username in plain text. Not as
# bad as sending your password in plain text, but still, pretty bad. However,
# renegotiations *are* encrypted. So as a workaround, it's not uncommon for
# systems that want to use client certificates to first do an anonymous
# handshake, and then to turn around and do a second handshake (=
# renegotiation) and this time ask for a client cert. Or sometimes this is
# done on a case-by-case basis, e.g. a web server might accept a connection,
# read the request, and then once it sees the page you're asking for it might
# stop and ask you for a certificate.
#
# 2) In principle the same TLS connection can be used for an arbitrarily long
# time, and might transmit arbitrarily large amounts of data. But this creates
# a cryptographic problem: an attacker who has access to arbitrarily large
# amounts of data that's all encrypted using the same key may eventually be
# able to use this to figure out the key. Is this a real practical problem? I
# have no idea, I'm not a cryptographer. In any case, some people worry that
# it's a problem, so their TLS libraries are designed to automatically trigger
# a renegotiation every once in a while on some sort of timer.
#
# The end result is that you might be going along, minding your own business,
# and then *bam*! a wild renegotiation appears! And you just have to cope.
#
# The reason that coping with renegotiations is difficult is that some
# unassuming "read" or "write" call might find itself unable to progress until
# it does a handshake, which remember is a process with multiple round
# trips. So read might have to send data, and write might have to receive
# data, and this might happen multiple times. And some of those attempts might
# fail because there isn't any data yet, and need to be retried. Managing all
# this is pretty complicated.
#
# Here's how openssl (and thus the stdlib ssl module) handle this. All of the
# I/O operations above follow the same rules. When you call one of them:
#
# - it might write some data to the outgoing BIO
# - it might read some data from the incoming BIO
# - it might raise SSLWantReadError if it can't complete without reading more
#   data from the incoming BIO. This is important: the "read" in ReadError
#   refers to reading from the *underlying* stream.
# - (and in principle it might raise SSLWantWriteError too, but that never
#   happens when using memory BIOs, so never mind)
#
# If it doesn't raise an error, then the operation completed successfully
# (though we still need to take any outgoing data out of the memory buffer and
# put it onto the wire). If it *does* raise an error, then we need to retry
# *exactly that method call* later – in particular, if a 'write' failed, we
# need to try again later *with the same data*, because openssl might have
# already committed some of the initial parts of our data to its output even
# though it didn't tell us that, and has remembered that the next time we call
# write it needs to skip the first 1024 bytes or whatever it is. (Well,
# technically, we're actually allowed to call 'write' again with a data buffer
# which is the same as our old one PLUS some extra stuff added onto the end,
# but in Trio that never comes up so never mind.)
#
# There are some people online who claim that once you've gotten a Want*Error
# then the *very next call* you make to openssl *must* be the same as the
# previous one. I'm pretty sure those people are wrong. In particular, it's
# okay to call write, get a WantReadError, and then call read a few times;
# it's just that *the next time you call write*, it has to be with the same
# data.
#
# One final wrinkle: we want our SSLStream to support full-duplex operation,
# i.e. it should be possible for one task to be calling send_all while another
# task is calling receive_some. But renegotiation makes this a big hassle, because
# even if SSLStream's restricts themselves to one task calling send_all and one
# task calling receive_some, those two tasks might end up both wanting to call
# send_all, or both to call receive_some at the same time *on the underlying
# stream*. So we have to do some careful locking to hide this problem from our
# users.
#
# (Renegotiation is evil.)
#
# So our basic strategy is to define a single helper method called "_retry",
# which has generic logic for dealing with SSLWantReadError, pushing data from
# the outgoing BIO to the wire, reading data from the wire to the incoming
# BIO, retrying an I/O call until it works, and synchronizing with other tasks
# that might be calling _retry concurrently. Basically it takes an SSLObject
# non-blocking in-memory method and converts it into a Trio async blocking
# method. _retry is only about 30 lines of code, but all these cases
# multiplied by concurrent calls make it extremely tricky, so there are lots
# of comments down below on the details, and a really extensive test suite in
# test_ssl.py. And now you know *why* it's so tricky, and can probably
# understand how it works.
#
# [1] https://rt.openssl.org/Ticket/Display.html?id=3712

# XX how closely should we match the stdlib API?
# - maybe suppress_ragged_eofs=False is a better default?
# - maybe check crypto folks for advice?
# - this is also interesting: https://bugs.python.org/issue8108#msg102867

# Definitely keep an eye on Cory's TLS API ideas on security-sig etc.

# XX document behavior on cancellation/error (i.e.: all is lost abandon
# stream)
# docs will need to make very clear that this is different from all the other
# cancellations in core Trio


T = TypeVar("T")

################################################################
# SSLStream
################################################################

# Ideally, when the user calls SSLStream.receive_some() with no argument, then
# we should do exactly one call to self.transport_stream.receive_some(),
# decrypt everything we got, and return it. Unfortunately, the way openssl's
# API works, we have to pick how much data we want to allow when we call
# read(), and then it (potentially) triggers a call to
# transport_stream.receive_some(). So at the time we pick the amount of data
# to decrypt, we don't know how much data we've read. As a simple heuristic,
# we record the max amount of data returned by previous calls to
# transport_stream.receive_some(), and we use that for future calls to read().
# But what do we use for the very first call? That's what this constant sets.
#
# Note that the value passed to read() is a limit on the amount of
# *decrypted* data, but we can only see the size of the *encrypted* data
# returned by transport_stream.receive_some(). TLS adds a small amount of
# framing overhead, and TLS compression is rarely used these days because it's
# insecure. So the size of the encrypted data should be a slight over-estimate
# of the size of the decrypted data, which is exactly what we want.
#
# The specific value is not really based on anything; it might be worth tuning
# at some point. But, if you have an TCP connection with the typical 1500 byte
# MTU and an initial window of 10 (see RFC 6928), then the initial burst of
# data will be limited to ~15000 bytes (or a bit less due to IP-level framing
# overhead), so this is chosen to be larger than that.
STARTING_RECEIVE_SIZE: TFinal = 16384


def _is_eof(exc: BaseException | None) -> bool:
    # There appears to be a bug on Python 3.10, where SSLErrors
    # aren't properly translated into SSLEOFErrors.
    # This stringly-typed error check is borrowed from the AnyIO
    # project.
    return isinstance(exc, _stdlib_ssl.SSLEOFError) or (
        "UNEXPECTED_EOF_WHILE_READING" in getattr(exc, "strerror", ())
    )


class NeedHandshakeError(Exception):
    """Some :class:`SSLStream` methods can't return any meaningful data until
    after the handshake. If you call them before the handshake, they raise
    this error.

    """


class _Once:
    __slots__ = ("_afn", "_args", "_done", "started")

    def __init__(
        self,
        afn: Callable[[*Ts], Awaitable[object]],
        *args: Unpack[Ts],
    ) -> None:
        self._afn = afn
        self._args = args
        self.started = False
        self._done = _sync.Event()

    async def ensure(self, *, checkpoint: bool) -> None:
        if not self.started:
            self.started = True
            await self._afn(*self._args)
            self._done.set()
        elif not checkpoint and self._done.is_set():
            return
        else:
            await self._done.wait()

    @property
    def done(self) -> bool:
        return bool(self._done.is_set())


_State = _Enum("_State", ["OK", "BROKEN", "CLOSED"])

# invariant
T_Stream = TypeVar("T_Stream", bound=Stream)


@final
class SSLStream(Stream, Generic[T_Stream]):
    r"""Encrypted communication using SSL/TLS.

    :class:`SSLStream` wraps an arbitrary :class:`~trio.abc.Stream`, and
    allows you to perform encrypted communication over it using the usual
    :class:`~trio.abc.Stream` interface. You pass regular data to
    :meth:`send_all`, then it encrypts it and sends the encrypted data on the
    underlying :class:`~trio.abc.Stream`; :meth:`receive_some` takes encrypted
    data out of the underlying :class:`~trio.abc.Stream` and decrypts it
    before returning it.

    You should read the standard library's :mod:`ssl` documentation carefully
    before attempting to use this class, and probably other general
    documentation on SSL/TLS as well. SSL/TLS is subtle and quick to
    anger. Really. I'm not kidding.

    Args:
      transport_stream (~trio.abc.Stream): The stream used to transport
          encrypted data. Required.

      ssl_context (~ssl.SSLContext): The :class:`~ssl.SSLContext` used for
          this connection. Required. Usually created by calling
          :func:`ssl.create_default_context`.

      server_hostname (str, bytes, or None): The name of the server being
          connected to. Used for `SNI
          <https://en.wikipedia.org/wiki/Server_Name_Indication>`__ and for
          validating the server's certificate (if hostname checking is
          enabled). This is effectively mandatory for clients, and actually
          mandatory if ``ssl_context.check_hostname`` is ``True``.

      server_side (bool): Whether this stream is acting as a client or
          server. Defaults to False, i.e. client mode.

      https_compatible (bool): There are two versions of SSL/TLS commonly
          encountered in the wild: the standard version, and the version used
          for HTTPS (HTTP-over-SSL/TLS).

          Standard-compliant SSL/TLS implementations always send a
          cryptographically signed ``close_notify`` message before closing the
          connection. This is important because if the underlying transport
          were simply closed, then there wouldn't be any way for the other
          side to know whether the connection was intentionally closed by the
          peer that they negotiated a cryptographic connection to, or by some
          `man-in-the-middle
          <https://en.wikipedia.org/wiki/Man-in-the-middle_attack>`__ attacker
          who can't manipulate the cryptographic stream, but can manipulate
          the transport layer (a so-called "truncation attack").

          However, this part of the standard is widely ignored by real-world
          HTTPS implementations, which means that if you want to interoperate
          with them, then you NEED to ignore it too.

          Fortunately this isn't as bad as it sounds, because the HTTP
          protocol already includes its own equivalent of ``close_notify``, so
          doing this again at the SSL/TLS level is redundant. But not all
          protocols do! Therefore, by default Trio implements the safer
          standard-compliant version (``https_compatible=False``). But if
          you're speaking HTTPS or some other protocol where
          ``close_notify``\s are commonly skipped, then you should set
          ``https_compatible=True``; with this setting, Trio will neither
          expect nor send ``close_notify`` messages.

          If you have code that was written to use :class:`ssl.SSLSocket` and
          now you're porting it to Trio, then it may be useful to know that a
          difference between :class:`SSLStream` and :class:`ssl.SSLSocket` is
          that :class:`~ssl.SSLSocket` implements the
          ``https_compatible=True`` behavior by default.

    Attributes:
      transport_stream (trio.abc.Stream): The underlying transport stream
          that was passed to ``__init__``. An example of when this would be
          useful is if you're using :class:`SSLStream` over a
          :class:`~trio.SocketStream` and want to call the
          :class:`~trio.SocketStream`'s :meth:`~trio.SocketStream.setsockopt`
          method.

    Internally, this class is implemented using an instance of
    :class:`ssl.SSLObject`, and all of :class:`~ssl.SSLObject`'s methods and
    attributes are re-exported as methods and attributes on this class.
    However, there is one difference: :class:`~ssl.SSLObject` has several
    methods that return information about the encrypted connection, like
    :meth:`~ssl.SSLSocket.cipher` or
    :meth:`~ssl.SSLSocket.selected_alpn_protocol`. If you call them before the
    handshake, when they can't possibly return useful data, then
    :class:`ssl.SSLObject` returns None, but :class:`trio.SSLStream`
    raises :exc:`NeedHandshakeError`.

    This also means that if you register a SNI callback using
    `~ssl.SSLContext.sni_callback`, then the first argument your callback
    receives will be a :class:`ssl.SSLObject`.

    """

    # Note: any new arguments here should likely also be added to
    # SSLListener.__init__, and maybe the open_ssl_over_tcp_* helpers.
    def __init__(
        self,
        transport_stream: T_Stream,
        ssl_context: _stdlib_ssl.SSLContext,
        *,
        server_hostname: str | bytes | None = None,
        server_side: bool = False,
        https_compatible: bool = False,
    ) -> None:
        self.transport_stream: T_Stream = transport_stream
        self._state = _State.OK
        self._https_compatible = https_compatible
        self._outgoing = _stdlib_ssl.MemoryBIO()
        self._delayed_outgoing: bytes | None = None
        self._incoming = _stdlib_ssl.MemoryBIO()
        self._ssl_object = ssl_context.wrap_bio(
            self._incoming,
            self._outgoing,
            server_side=server_side,
            server_hostname=server_hostname,
        )
        # Tracks whether we've already done the initial handshake
        self._handshook = _Once(self._do_handshake)

        # These are used to synchronize access to self.transport_stream
        self._inner_send_lock = _sync.StrictFIFOLock()
        self._inner_recv_count = 0
        self._inner_recv_lock = _sync.Lock()

        # These are used to make sure that our caller doesn't attempt to make
        # multiple concurrent calls to send_all/wait_send_all_might_not_block
        # or to receive_some.
        self._outer_send_conflict_detector = ConflictDetector(
            "another task is currently sending data on this SSLStream",
        )
        self._outer_recv_conflict_detector = ConflictDetector(
            "another task is currently receiving data on this SSLStream",
        )

        self._estimated_receive_size = STARTING_RECEIVE_SIZE

    _forwarded: ClassVar = {
        "context",
        "server_side",
        "server_hostname",
        "session",
        "session_reused",
        "getpeercert",
        "selected_npn_protocol",
        "cipher",
        "shared_ciphers",
        "compression",
        "pending",
        "get_channel_binding",
        "selected_alpn_protocol",
        "version",
    }

    _after_handshake: ClassVar = {
        "session_reused",
        "getpeercert",
        "selected_npn_protocol",
        "cipher",
        "shared_ciphers",
        "compression",
        "get_channel_binding",
        "selected_alpn_protocol",
        "version",
    }

    def __getattr__(  # type: ignore[explicit-any]
        self,
        name: str,
    ) -> Any:
        if name in self._forwarded:
            if name in self._after_handshake and not self._handshook.done:
                raise NeedHandshakeError(f"call do_handshake() before calling {name!r}")

            return getattr(self._ssl_object, name)
        else:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: object) -> None:
        if name in self._forwarded:
            setattr(self._ssl_object, name, value)
        else:
            super().__setattr__(name, value)

    def __dir__(self) -> list[str]:
        return list(super().__dir__()) + list(self._forwarded)

    def _check_status(self) -> None:
        if self._state is _State.OK:
            return
        elif self._state is _State.BROKEN:
            raise trio.BrokenResourceError
        elif self._state is _State.CLOSED:
            raise trio.ClosedResourceError
        else:  # pragma: no cover
            raise AssertionError()

    # This is probably the single trickiest function in Trio. It has lots of
    # comments, though, just make sure to think carefully if you ever have to
    # touch it. The big comment at the top of this file will help explain
    # too.
    async def _retry(
        self,
        fn: Callable[[*Ts], T],
        *args: Unpack[Ts],
        ignore_want_read: bool = False,
        is_handshake: bool = False,
    ) -> T | None:
        await trio.lowlevel.checkpoint_if_cancelled()
        yielded = False
        finished = False
        while not finished:
            # WARNING: this code needs to be very careful with when it
            # calls 'await'! There might be multiple tasks calling this
            # function at the same time trying to do different operations,
            # so we need to be careful to:
            #
            # 1) interact with the SSLObject, then
            # 2) await on exactly one thing that lets us make forward
            # progress, then
            # 3) loop or exit
            #
            # In particular we don't want to yield while interacting with
            # the SSLObject (because it's shared state, so someone else
            # might come in and mess with it while we're suspended), and
            # we don't want to yield *before* starting the operation that
            # will help us make progress, because then someone else might
            # come in and leapfrog us.

            # Call the SSLObject method, and get its result.
            #
            # NB: despite what the docs say, SSLWantWriteError can't
            # happen – "Writes to memory BIOs will always succeed if
            # memory is available: that is their size can grow
            # indefinitely."
            # https://wiki.openssl.org/index.php/Manual:BIO_s_mem(3)
            want_read = False
            ret = None
            try:
                ret = fn(*args)
            except _stdlib_ssl.SSLWantReadError:
                want_read = True
            except (_stdlib_ssl.SSLError, _stdlib_ssl.CertificateError) as exc:
                self._state = _State.BROKEN
                raise trio.BrokenResourceError from exc
            else:
                finished = True
            if ignore_want_read:
                want_read = False
                finished = True
            to_send = self._outgoing.read()

            # Some versions of SSL_do_handshake have a bug in how they handle
            # the TLS 1.3 handshake on the server side: after the handshake
            # finishes, they automatically send session tickets, even though
            # the client may not be expecting data to arrive at this point and
            # sending it could cause a deadlock or lost data. This applies at
            # least to OpenSSL 1.1.1c and earlier, and the OpenSSL devs
            # currently have no plans to fix it:
            #
            #   https://github.com/openssl/openssl/issues/7948
            #   https://github.com/openssl/openssl/issues/7967
            #
            # The correct behavior is to wait to send session tickets on the
            # first call to SSL_write. (This is what BoringSSL does.) So, we
            # use a heuristic to detect when OpenSSL has tried to send session
            # tickets, and we manually delay sending them until the
            # appropriate moment. For more discussion see:
            #
            #   https://github.com/python-trio/trio/issues/819#issuecomment-517529763
            if (
                is_handshake
                and not want_read
                and self._ssl_object.server_side
                and self._ssl_object.version() == "TLSv1.3"
            ):
                assert self._delayed_outgoing is None
                self._delayed_outgoing = to_send
                to_send = b""

            # Outputs from the above code block are:
            #
            # - to_send: bytestring; if non-empty then we need to send
            #   this data to make forward progress
            #
            # - want_read: True if we need to receive_some some data to make
            #   forward progress
            #
            # - finished: False means that we need to retry the call to
            #   fn(*args) again, after having pushed things forward. True
            #   means we still need to do whatever was said (in particular
            #   send any data in to_send), but once we do then we're
            #   done.
            #
            # - ret: the operation's return value. (Meaningless unless
            #   finished is True.)
            #
            # Invariant: want_read and finished can't both be True at the
            # same time.
            #
            # Now we need to move things forward. There are two things we
            # might have to do, and any given operation might require
            # either, both, or neither to proceed:
            #
            # - send the data in to_send
            #
            # - receive_some some data and put it into the incoming BIO
            #
            # Our strategy is: if there's data to send, send it;
            # *otherwise* if there's data to receive_some, receive_some it.
            #
            # If both need to happen, then we only send. Why? Well, we
            # know that *right now* we have to both send and receive_some
            # before the operation can complete. But as soon as we yield,
            # that information becomes potentially stale – e.g. while
            # we're sending, some other task might go and receive_some the
            # data we need and put it into the incoming BIO. And if it
            # does, then we *definitely don't* want to do a receive_some –
            # there might not be any more data coming, and we'd deadlock!
            # We could do something tricky to keep track of whether a
            # receive_some happens while we're sending, but the case where
            # we have to do both is very unusual (only during a
            # renegotiation), so it's better to keep things simple. So we
            # do just one potentially-blocking operation, then check again
            # for fresh information.
            #
            # And we prioritize sending over receiving because, if there
            # are multiple tasks that want to receive_some, then it
            # doesn't matter what order they go in. But if there are
            # multiple tasks that want to send, then they each have
            # different data, and the data needs to get put onto the wire
            # in the same order that it was retrieved from the outgoing
            # BIO. So if we have data to send, that *needs* to be the
            # *very* *next* *thing* we do, to make sure no-one else sneaks
            # in before us. Or if we can't send immediately because
            # someone else is, then we at least need to get in line
            # immediately.
            if to_send:
                # NOTE: This relies on the lock being strict FIFO fair!
                async with self._inner_send_lock:
                    yielded = True
                    try:
                        if self._delayed_outgoing is not None:
                            to_send = self._delayed_outgoing + to_send
                            self._delayed_outgoing = None
                        await self.transport_stream.send_all(to_send)
                    except:
                        # Some unknown amount of our data got sent, and we
                        # don't know how much. This stream is doomed.
                        self._state = _State.BROKEN
                        raise
            elif want_read:
                # It's possible that someone else is already blocked in
                # transport_stream.receive_some. If so then we want to
                # wait for them to finish, but we don't want to call
                # transport_stream.receive_some again ourselves; we just
                # want to loop around and check if their contribution
                # helped anything. So we make a note of how many times
                # some task has been through here before taking the lock,
                # and if it's changed by the time we get the lock, then we
                # skip calling transport_stream.receive_some and loop
                # around immediately.
                recv_count = self._inner_recv_count
                async with self._inner_recv_lock:
                    yielded = True
                    if recv_count == self._inner_recv_count:
                        data = await self.transport_stream.receive_some()
                        if not data:
                            self._incoming.write_eof()
                        else:
                            self._estimated_receive_size = max(
                                self._estimated_receive_size,
                                len(data),
                            )
                            self._incoming.write(data)
                        self._inner_recv_count += 1
        if not yielded:
            await trio.lowlevel.cancel_shielded_checkpoint()
        return ret

    async def _do_handshake(self) -> None:
        try:
            await self._retry(self._ssl_object.do_handshake, is_handshake=True)
        except:
            self._state = _State.BROKEN
            raise

    async def do_handshake(self) -> None:
        """Ensure that the initial handshake has completed.

        The SSL protocol requires an initial handshake to exchange
        certificates, select cryptographic keys, and so forth, before any
        actual data can be sent or received. You don't have to call this
        method; if you don't, then :class:`SSLStream` will automatically
        perform the handshake as needed, the first time you try to send or
        receive data. But if you want to trigger it manually – for example,
        because you want to look at the peer's certificate before you start
        talking to them – then you can call this method.

        If the initial handshake is already in progress in another task, this
        waits for it to complete and then returns.

        If the initial handshake has already completed, this returns
        immediately without doing anything (except executing a checkpoint).

        .. warning:: If this method is cancelled, then it may leave the
           :class:`SSLStream` in an unusable state. If this happens then any
           future attempt to use the object will raise
           :exc:`trio.BrokenResourceError`.

        """
        self._check_status()
        await self._handshook.ensure(checkpoint=True)

    # Most things work if we don't explicitly force do_handshake to be called
    # before calling receive_some or send_all, because openssl will
    # automatically perform the handshake on the first SSL_{read,write}
    # call. BUT, allowing openssl to do this will disable Python's hostname
    # checking!!! See:
    #   https://bugs.python.org/issue30141
    # So we *definitely* have to make sure that do_handshake is called
    # before doing anything else.
    async def receive_some(self, max_bytes: int | None = None) -> bytes | bytearray:
        """Read some data from the underlying transport, decrypt it, and
        return it.

        See :meth:`trio.abc.ReceiveStream.receive_some` for details.

        .. warning:: If this method is cancelled while the initial handshake
           or a renegotiation are in progress, then it may leave the
           :class:`SSLStream` in an unusable state. If this happens then any
           future attempt to use the object will raise
           :exc:`trio.BrokenResourceError`.

        """
        with self._outer_recv_conflict_detector:
            self._check_status()
            try:
                await self._handshook.ensure(checkpoint=False)
            except trio.BrokenResourceError as exc:
                # For some reason, EOF before handshake sometimes raises
                # SSLSyscallError instead of SSLEOFError (e.g. on my linux
                # laptop, but not on appveyor). Thanks openssl.
                if self._https_compatible and (
                    isinstance(exc.__cause__, _stdlib_ssl.SSLSyscallError)
                    or _is_eof(exc.__cause__)
                ):
                    await trio.lowlevel.checkpoint()
                    return b""
                else:
                    raise
            if max_bytes is None:
                # If we somehow have more data already in our pending buffer
                # than the estimate receive size, bump up our size a bit for
                # this read only.
                max_bytes = max(self._estimated_receive_size, self._incoming.pending)
            else:
                max_bytes = _operator.index(max_bytes)
                if max_bytes < 1:
                    raise ValueError("max_bytes must be >= 1")
            try:
                received = await self._retry(self._ssl_object.read, max_bytes)
                assert received is not None
                return received
            except trio.BrokenResourceError as exc:
                # This isn't quite equivalent to just returning b"" in the
                # first place, because we still end up with self._state set to
                # BROKEN. But that's actually fine, because after getting an
                # EOF on TLS then the only thing you can do is close the
                # stream, and closing doesn't care about the state.

                if self._https_compatible and _is_eof(exc.__cause__):
                    await trio.lowlevel.checkpoint()
                    return b""
                else:
                    raise

    async def send_all(self, data: bytes | bytearray | memoryview) -> None:
        """Encrypt some data and then send it on the underlying transport.

        See :meth:`trio.abc.SendStream.send_all` for details.

        .. warning:: If this method is cancelled, then it may leave the
           :class:`SSLStream` in an unusable state. If this happens then any
           attempt to use the object will raise
           :exc:`trio.BrokenResourceError`.

        """
        with self._outer_send_conflict_detector:
            self._check_status()
            await self._handshook.ensure(checkpoint=False)
            # SSLObject interprets write(b"") as an EOF for some reason, which
            # is not what we want.
            if not data:
                await trio.lowlevel.checkpoint()
                return
            await self._retry(self._ssl_object.write, data)

    async def unwrap(self) -> tuple[Stream, bytes | bytearray]:
        """Cleanly close down the SSL/TLS encryption layer, allowing the
        underlying stream to be used for unencrypted communication.

        You almost certainly don't need this.

        Returns:
          A pair ``(transport_stream, trailing_bytes)``, where
          ``transport_stream`` is the underlying transport stream, and
          ``trailing_bytes`` is a byte string. Since :class:`SSLStream`
          doesn't necessarily know where the end of the encrypted data will
          be, it can happen that it accidentally reads too much from the
          underlying stream. ``trailing_bytes`` contains this extra data; you
          should process it as if it was returned from a call to
          ``transport_stream.receive_some(...)``.

        """
        with self._outer_recv_conflict_detector, self._outer_send_conflict_detector:
            self._check_status()
            await self._handshook.ensure(checkpoint=False)
            await self._retry(self._ssl_object.unwrap)
            transport_stream = self.transport_stream
            self._state = _State.CLOSED
            self.transport_stream = None  # type: ignore[assignment]  # State is CLOSED now, nothing should use
            return (transport_stream, self._incoming.read())

    async def aclose(self) -> None:
        """Gracefully shut down this connection, and close the underlying
        transport.

        If ``https_compatible`` is False (the default), then this attempts to
        first send a ``close_notify`` and then close the underlying stream by
        calling its :meth:`~trio.abc.AsyncResource.aclose` method.

        If ``https_compatible`` is set to True, then this simply closes the
        underlying stream and marks this stream as closed.

        """
        if self._state is _State.CLOSED:
            await trio.lowlevel.checkpoint()
            return
        if self._state is _State.BROKEN or self._https_compatible:
            self._state = _State.CLOSED
            await self.transport_stream.aclose()
            return
        try:
            # https_compatible=False, so we're in spec-compliant mode and have
            # to send close_notify so that the other side gets a cryptographic
            # assurance that we've called aclose. Of course, we can't do
            # anything cryptographic until after we've completed the
            # handshake:
            await self._handshook.ensure(checkpoint=False)
            # Then, we call SSL_shutdown *once*, because we want to send a
            # close_notify but *not* wait for the other side to send back a
            # response. In principle it would be more polite to wait for the
            # other side to reply with their own close_notify. However, if
            # they aren't paying attention (e.g., if they're just sending
            # data and not receiving) then we will never notice our
            # close_notify and we'll be waiting forever. Eventually we'll time
            # out (hopefully), but it's still kind of nasty. And we can't
            # require the other side to always be receiving, because (a)
            # backpressure is kind of important, and (b) I bet there are
            # broken TLS implementations out there that don't receive all the
            # time. (Like e.g. anyone using Python ssl in synchronous mode.)
            #
            # The send-then-immediately-close behavior is explicitly allowed
            # by the TLS specs, so we're ok on that.
            #
            # Subtlety: SSLObject.unwrap will immediately call it a second
            # time, and the second time will raise SSLWantReadError because
            # there hasn't been time for the other side to respond
            # yet. (Unless they spontaneously sent a close_notify before we
            # called this, and it's either already been processed or gets
            # pulled out of the buffer by Python's second call.) So the way to
            # do what we want is to ignore SSLWantReadError on this call.
            #
            # Also, because the other side might have already sent
            # close_notify and closed their connection then it's possible that
            # our attempt to send close_notify will raise
            # BrokenResourceError. This is totally legal, and in fact can happen
            # with two well-behaved Trio programs talking to each other, so we
            # don't want to raise an error. So we suppress BrokenResourceError
            # here. (This is safe, because literally the only thing this call
            # to _retry will do is send the close_notify alert, so that's
            # surely where the error comes from.)
            #
            # FYI in some cases this could also raise SSLSyscallError which I
            # think is because SSL_shutdown is terrible. (Check out that note
            # at the bottom of the man page saying that it sometimes gets
            # raised spuriously.) I haven't seen this since we switched to
            # immediately closing the socket, and I don't know exactly what
            # conditions cause it and how to respond, so for now we're just
            # letting that happen. But if you start seeing it, then hopefully
            # this will give you a little head start on tracking it down,
            # because whoa did this puzzle us at the 2017 PyCon sprints.
            #
            # Also, if someone else is blocked in send/receive, then we aren't
            # going to be able to do a clean shutdown. If that happens, we'll
            # just do an unclean shutdown.
            with contextlib.suppress(trio.BrokenResourceError, trio.BusyResourceError):
                await self._retry(self._ssl_object.unwrap, ignore_want_read=True)
        except:
            # Failure! Kill the stream and move on.
            await aclose_forcefully(self.transport_stream)
            raise
        else:
            # Success! Gracefully close the underlying stream.
            await self.transport_stream.aclose()
        finally:
            self._state = _State.CLOSED

    async def wait_send_all_might_not_block(self) -> None:
        """See :meth:`trio.abc.SendStream.wait_send_all_might_not_block`."""
        # This method's implementation is deceptively simple.
        #
        # First, we take the outer send lock, because of Trio's standard
        # semantics that wait_send_all_might_not_block and send_all
        # conflict.
        with self._outer_send_conflict_detector:
            self._check_status()
            # Then we take the inner send lock. We know that no other tasks
            # are calling self.send_all or self.wait_send_all_might_not_block,
            # because we have the outer_send_lock. But! There might be another
            # task calling self.receive_some -> transport_stream.send_all, in
            # which case if we were to call
            # transport_stream.wait_send_all_might_not_block directly we'd
            # have two tasks doing write-related operations on
            # transport_stream simultaneously, which is not allowed. We
            # *don't* want to raise this conflict to our caller, because it's
            # purely an internal affair – all they did was call
            # wait_send_all_might_not_block and receive_some at the same time,
            # which is totally valid. And waiting for the lock is OK, because
            # a call to send_all certainly wouldn't complete while the other
            # task holds the lock.
            async with self._inner_send_lock:
                # Now we have the lock, which creates another potential
                # problem: what if a call to self.receive_some attempts to do
                # transport_stream.send_all now? It'll have to wait for us to
                # finish! But that's OK, because we release the lock as soon
                # as the underlying stream becomes writable, and the
                # self.receive_some call wasn't going to make any progress
                # until then anyway.
                #
                # Of course, this does mean we might return *before* the
                # stream is logically writable, because immediately after we
                # return self.receive_some might write some data and make it
                # non-writable again. But that's OK too,
                # wait_send_all_might_not_block only guarantees that it
                # doesn't return late.
                await self.transport_stream.wait_send_all_might_not_block()


# this is necessary for Sphinx, see also `_abc.py`
SSLStream.__module__ = SSLStream.__module__.replace("._ssl", "")


@final
class SSLListener(Listener[SSLStream[T_Stream]]):
    """A :class:`~trio.abc.Listener` for SSL/TLS-encrypted servers.

    :class:`SSLListener` wraps around another Listener, and converts
    all incoming connections to encrypted connections by wrapping them
    in a :class:`SSLStream`.

    Args:
      transport_listener (~trio.abc.Listener): The listener whose incoming
          connections will be wrapped in :class:`SSLStream`.

      ssl_context (~ssl.SSLContext): The :class:`~ssl.SSLContext` that will be
          used for incoming connections.

      https_compatible (bool): Passed on to :class:`SSLStream`.

    Attributes:
      transport_listener (trio.abc.Listener): The underlying listener that was
          passed to ``__init__``.

    """

    def __init__(
        self,
        transport_listener: Listener[T_Stream],
        ssl_context: _stdlib_ssl.SSLContext,
        *,
        https_compatible: bool = False,
    ) -> None:
        self.transport_listener = transport_listener
        self._ssl_context = ssl_context
        self._https_compatible = https_compatible

    async def accept(self) -> SSLStream[T_Stream]:
        """Accept the next connection and wrap it in an :class:`SSLStream`.

        See :meth:`trio.abc.Listener.accept` for details.

        """
        transport_stream = await self.transport_listener.accept()
        return SSLStream(
            transport_stream,
            self._ssl_context,
            server_side=True,
            https_compatible=self._https_compatible,
        )

    async def aclose(self) -> None:
        """Close the transport listener."""
        await self.transport_listener.aclose()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\lexer.py ===
"""
    pygments.lexer
    ~~~~~~~~~~~~~~

    Base lexer classes.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import sys
import time

from pip._vendor.pygments.filter import apply_filters, Filter
from pip._vendor.pygments.filters import get_filter_by_name
from pip._vendor.pygments.token import Error, Text, Other, Whitespace, _TokenType
from pip._vendor.pygments.util import get_bool_opt, get_int_opt, get_list_opt, \
    make_analysator, Future, guess_decode
from pip._vendor.pygments.regexopt import regex_opt

__all__ = ['Lexer', 'RegexLexer', 'ExtendedRegexLexer', 'DelegatingLexer',
           'LexerContext', 'include', 'inherit', 'bygroups', 'using', 'this',
           'default', 'words', 'line_re']

line_re = re.compile('.*?\n')

_encoding_map = [(b'\xef\xbb\xbf', 'utf-8'),
                 (b'\xff\xfe\0\0', 'utf-32'),
                 (b'\0\0\xfe\xff', 'utf-32be'),
                 (b'\xff\xfe', 'utf-16'),
                 (b'\xfe\xff', 'utf-16be')]

_default_analyse = staticmethod(lambda x: 0.0)


class LexerMeta(type):
    """
    This metaclass automagically converts ``analyse_text`` methods into
    static methods which always return float values.
    """

    def __new__(mcs, name, bases, d):
        if 'analyse_text' in d:
            d['analyse_text'] = make_analysator(d['analyse_text'])
        return type.__new__(mcs, name, bases, d)


class Lexer(metaclass=LexerMeta):
    """
    Lexer for a specific language.

    See also :doc:`lexerdevelopment`, a high-level guide to writing
    lexers.

    Lexer classes have attributes used for choosing the most appropriate
    lexer based on various criteria.

    .. autoattribute:: name
       :no-value:
    .. autoattribute:: aliases
       :no-value:
    .. autoattribute:: filenames
       :no-value:
    .. autoattribute:: alias_filenames
    .. autoattribute:: mimetypes
       :no-value:
    .. autoattribute:: priority

    Lexers included in Pygments should have two additional attributes:

    .. autoattribute:: url
       :no-value:
    .. autoattribute:: version_added
       :no-value:

    Lexers included in Pygments may have additional attributes:

    .. autoattribute:: _example
       :no-value:

    You can pass options to the constructor. The basic options recognized
    by all lexers and processed by the base `Lexer` class are:

    ``stripnl``
        Strip leading and trailing newlines from the input (default: True).
    ``stripall``
        Strip all leading and trailing whitespace from the input
        (default: False).
    ``ensurenl``
        Make sure that the input ends with a newline (default: True).  This
        is required for some lexers that consume input linewise.

        .. versionadded:: 1.3

    ``tabsize``
        If given and greater than 0, expand tabs in the input (default: 0).
    ``encoding``
        If given, must be an encoding name. This encoding will be used to
        convert the input string to Unicode, if it is not already a Unicode
        string (default: ``'guess'``, which uses a simple UTF-8 / Locale /
        Latin1 detection.  Can also be ``'chardet'`` to use the chardet
        library, if it is installed.
    ``inencoding``
        Overrides the ``encoding`` if given.
    """

    #: Full name of the lexer, in human-readable form
    name = None

    #: A list of short, unique identifiers that can be used to look
    #: up the lexer from a list, e.g., using `get_lexer_by_name()`.
    aliases = []

    #: A list of `fnmatch` patterns that match filenames which contain
    #: content for this lexer. The patterns in this list should be unique among
    #: all lexers.
    filenames = []

    #: A list of `fnmatch` patterns that match filenames which may or may not
    #: contain content for this lexer. This list is used by the
    #: :func:`.guess_lexer_for_filename()` function, to determine which lexers
    #: are then included in guessing the correct one. That means that
    #: e.g. every lexer for HTML and a template language should include
    #: ``\*.html`` in this list.
    alias_filenames = []

    #: A list of MIME types for content that can be lexed with this lexer.
    mimetypes = []

    #: Priority, should multiple lexers match and no content is provided
    priority = 0

    #: URL of the language specification/definition. Used in the Pygments
    #: documentation. Set to an empty string to disable.
    url = None

    #: Version of Pygments in which the lexer was added.
    version_added = None

    #: Example file name. Relative to the ``tests/examplefiles`` directory.
    #: This is used by the documentation generator to show an example.
    _example = None

    def __init__(self, **options):
        """
        This constructor takes arbitrary options as keyword arguments.
        Every subclass must first process its own options and then call
        the `Lexer` constructor, since it processes the basic
        options like `stripnl`.

        An example looks like this:

        .. sourcecode:: python

           def __init__(self, **options):
               self.compress = options.get('compress', '')
               Lexer.__init__(self, **options)

        As these options must all be specifiable as strings (due to the
        command line usage), there are various utility functions
        available to help with that, see `Utilities`_.
        """
        self.options = options
        self.stripnl = get_bool_opt(options, 'stripnl', True)
        self.stripall = get_bool_opt(options, 'stripall', False)
        self.ensurenl = get_bool_opt(options, 'ensurenl', True)
        self.tabsize = get_int_opt(options, 'tabsize', 0)
        self.encoding = options.get('encoding', 'guess')
        self.encoding = options.get('inencoding') or self.encoding
        self.filters = []
        for filter_ in get_list_opt(options, 'filters', ()):
            self.add_filter(filter_)

    def __repr__(self):
        if self.options:
            return f'<pygments.lexers.{self.__class__.__name__} with {self.options!r}>'
        else:
            return f'<pygments.lexers.{self.__class__.__name__}>'

    def add_filter(self, filter_, **options):
        """
        Add a new stream filter to this lexer.
        """
        if not isinstance(filter_, Filter):
            filter_ = get_filter_by_name(filter_, **options)
        self.filters.append(filter_)

    def analyse_text(text):
        """
        A static method which is called for lexer guessing.

        It should analyse the text and return a float in the range
        from ``0.0`` to ``1.0``.  If it returns ``0.0``, the lexer
        will not be selected as the most probable one, if it returns
        ``1.0``, it will be selected immediately.  This is used by
        `guess_lexer`.

        The `LexerMeta` metaclass automatically wraps this function so
        that it works like a static method (no ``self`` or ``cls``
        parameter) and the return value is automatically converted to
        `float`. If the return value is an object that is boolean `False`
        it's the same as if the return values was ``0.0``.
        """

    def _preprocess_lexer_input(self, text):
        """Apply preprocessing such as decoding the input, removing BOM and normalizing newlines."""

        if not isinstance(text, str):
            if self.encoding == 'guess':
                text, _ = guess_decode(text)
            elif self.encoding == 'chardet':
                try:
                    # pip vendoring note: this code is not reachable by pip,
                    # removed import of chardet to make it clear.
                    raise ImportError('chardet is not vendored by pip')
                except ImportError as e:
                    raise ImportError('To enable chardet encoding guessing, '
                                      'please install the chardet library '
                                      'from http://chardet.feedparser.org/') from e
                # check for BOM first
                decoded = None
                for bom, encoding in _encoding_map:
                    if text.startswith(bom):
                        decoded = text[len(bom):].decode(encoding, 'replace')
                        break
                # no BOM found, so use chardet
                if decoded is None:
                    enc = chardet.detect(text[:1024])  # Guess using first 1KB
                    decoded = text.decode(enc.get('encoding') or 'utf-8',
                                          'replace')
                text = decoded
            else:
                text = text.decode(self.encoding)
                if text.startswith('\ufeff'):
                    text = text[len('\ufeff'):]
        else:
            if text.startswith('\ufeff'):
                text = text[len('\ufeff'):]

        # text now *is* a unicode string
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        if self.stripall:
            text = text.strip()
        elif self.stripnl:
            text = text.strip('\n')
        if self.tabsize > 0:
            text = text.expandtabs(self.tabsize)
        if self.ensurenl and not text.endswith('\n'):
            text += '\n'

        return text

    def get_tokens(self, text, unfiltered=False):
        """
        This method is the basic interface of a lexer. It is called by
        the `highlight()` function. It must process the text and return an
        iterable of ``(tokentype, value)`` pairs from `text`.

        Normally, you don't need to override this method. The default
        implementation processes the options recognized by all lexers
        (`stripnl`, `stripall` and so on), and then yields all tokens
        from `get_tokens_unprocessed()`, with the ``index`` dropped.

        If `unfiltered` is set to `True`, the filtering mechanism is
        bypassed even if filters are defined.
        """
        text = self._preprocess_lexer_input(text)

        def streamer():
            for _, t, v in self.get_tokens_unprocessed(text):
                yield t, v
        stream = streamer()
        if not unfiltered:
            stream = apply_filters(stream, self.filters, self)
        return stream

    def get_tokens_unprocessed(self, text):
        """
        This method should process the text and return an iterable of
        ``(index, tokentype, value)`` tuples where ``index`` is the starting
        position of the token within the input text.

        It must be overridden by subclasses. It is recommended to
        implement it as a generator to maximize effectiveness.
        """
        raise NotImplementedError


class DelegatingLexer(Lexer):
    """
    This lexer takes two lexer as arguments. A root lexer and
    a language lexer. First everything is scanned using the language
    lexer, afterwards all ``Other`` tokens are lexed using the root
    lexer.

    The lexers from the ``template`` lexer package use this base lexer.
    """

    def __init__(self, _root_lexer, _language_lexer, _needle=Other, **options):
        self.root_lexer = _root_lexer(**options)
        self.language_lexer = _language_lexer(**options)
        self.needle = _needle
        Lexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        buffered = ''
        insertions = []
        lng_buffer = []
        for i, t, v in self.language_lexer.get_tokens_unprocessed(text):
            if t is self.needle:
                if lng_buffer:
                    insertions.append((len(buffered), lng_buffer))
                    lng_buffer = []
                buffered += v
            else:
                lng_buffer.append((i, t, v))
        if lng_buffer:
            insertions.append((len(buffered), lng_buffer))
        return do_insertions(insertions,
                             self.root_lexer.get_tokens_unprocessed(buffered))


# ------------------------------------------------------------------------------
# RegexLexer and ExtendedRegexLexer
#


class include(str):  # pylint: disable=invalid-name
    """
    Indicates that a state should include rules from another state.
    """
    pass


class _inherit:
    """
    Indicates the a state should inherit from its superclass.
    """
    def __repr__(self):
        return 'inherit'

inherit = _inherit()  # pylint: disable=invalid-name


class combined(tuple):  # pylint: disable=invalid-name
    """
    Indicates a state combined from multiple states.
    """

    def __new__(cls, *args):
        return tuple.__new__(cls, args)

    def __init__(self, *args):
        # tuple.__init__ doesn't do anything
        pass


class _PseudoMatch:
    """
    A pseudo match object constructed from a string.
    """

    def __init__(self, start, text):
        self._text = text
        self._start = start

    def start(self, arg=None):
        return self._start

    def end(self, arg=None):
        return self._start + len(self._text)

    def group(self, arg=None):
        if arg:
            raise IndexError('No such group')
        return self._text

    def groups(self):
        return (self._text,)

    def groupdict(self):
        return {}


def bygroups(*args):
    """
    Callback that yields multiple actions for each group in the match.
    """
    def callback(lexer, match, ctx=None):
        for i, action in enumerate(args):
            if action is None:
                continue
            elif type(action) is _TokenType:
                data = match.group(i + 1)
                if data:
                    yield match.start(i + 1), action, data
            else:
                data = match.group(i + 1)
                if data is not None:
                    if ctx:
                        ctx.pos = match.start(i + 1)
                    for item in action(lexer,
                                       _PseudoMatch(match.start(i + 1), data), ctx):
                        if item:
                            yield item
        if ctx:
            ctx.pos = match.end()
    return callback


class _This:
    """
    Special singleton used for indicating the caller class.
    Used by ``using``.
    """

this = _This()


def using(_other, **kwargs):
    """
    Callback that processes the match with a different lexer.

    The keyword arguments are forwarded to the lexer, except `state` which
    is handled separately.

    `state` specifies the state that the new lexer will start in, and can
    be an enumerable such as ('root', 'inline', 'string') or a simple
    string which is assumed to be on top of the root state.

    Note: For that to work, `_other` must not be an `ExtendedRegexLexer`.
    """
    gt_kwargs = {}
    if 'state' in kwargs:
        s = kwargs.pop('state')
        if isinstance(s, (list, tuple)):
            gt_kwargs['stack'] = s
        else:
            gt_kwargs['stack'] = ('root', s)

    if _other is this:
        def callback(lexer, match, ctx=None):
            # if keyword arguments are given the callback
            # function has to create a new lexer instance
            if kwargs:
                # XXX: cache that somehow
                kwargs.update(lexer.options)
                lx = lexer.__class__(**kwargs)
            else:
                lx = lexer
            s = match.start()
            for i, t, v in lx.get_tokens_unprocessed(match.group(), **gt_kwargs):
                yield i + s, t, v
            if ctx:
                ctx.pos = match.end()
    else:
        def callback(lexer, match, ctx=None):
            # XXX: cache that somehow
            kwargs.update(lexer.options)
            lx = _other(**kwargs)

            s = match.start()
            for i, t, v in lx.get_tokens_unprocessed(match.group(), **gt_kwargs):
                yield i + s, t, v
            if ctx:
                ctx.pos = match.end()
    return callback


class default:
    """
    Indicates a state or state action (e.g. #pop) to apply.
    For example default('#pop') is equivalent to ('', Token, '#pop')
    Note that state tuples may be used as well.

    .. versionadded:: 2.0
    """
    def __init__(self, state):
        self.state = state


class words(Future):
    """
    Indicates a list of literal words that is transformed into an optimized
    regex that matches any of the words.

    .. versionadded:: 2.0
    """
    def __init__(self, words, prefix='', suffix=''):
        self.words = words
        self.prefix = prefix
        self.suffix = suffix

    def get(self):
        return regex_opt(self.words, prefix=self.prefix, suffix=self.suffix)


class RegexLexerMeta(LexerMeta):
    """
    Metaclass for RegexLexer, creates the self._tokens attribute from
    self.tokens on the first instantiation.
    """

    def _process_regex(cls, regex, rflags, state):
        """Preprocess the regular expression component of a token definition."""
        if isinstance(regex, Future):
            regex = regex.get()
        return re.compile(regex, rflags).match

    def _process_token(cls, token):
        """Preprocess the token component of a token definition."""
        assert type(token) is _TokenType or callable(token), \
            f'token type must be simple type or callable, not {token!r}'
        return token

    def _process_new_state(cls, new_state, unprocessed, processed):
        """Preprocess the state transition action of a token definition."""
        if isinstance(new_state, str):
            # an existing state
            if new_state == '#pop':
                return -1
            elif new_state in unprocessed:
                return (new_state,)
            elif new_state == '#push':
                return new_state
            elif new_state[:5] == '#pop:':
                return -int(new_state[5:])
            else:
                assert False, f'unknown new state {new_state!r}'
        elif isinstance(new_state, combined):
            # combine a new state from existing ones
            tmp_state = '_tmp_%d' % cls._tmpname
            cls._tmpname += 1
            itokens = []
            for istate in new_state:
                assert istate != new_state, f'circular state ref {istate!r}'
                itokens.extend(cls._process_state(unprocessed,
                                                  processed, istate))
            processed[tmp_state] = itokens
            return (tmp_state,)
        elif isinstance(new_state, tuple):
            # push more than one state
            for istate in new_state:
                assert (istate in unprocessed or
                        istate in ('#pop', '#push')), \
                    'unknown new state ' + istate
            return new_state
        else:
            assert False, f'unknown new state def {new_state!r}'

    def _process_state(cls, unprocessed, processed, state):
        """Preprocess a single state definition."""
        assert isinstance(state, str), f"wrong state name {state!r}"
        assert state[0] != '#', f"invalid state name {state!r}"
        if state in processed:
            return processed[state]
        tokens = processed[state] = []
        rflags = cls.flags
        for tdef in unprocessed[state]:
            if isinstance(tdef, include):
                # it's a state reference
                assert tdef != state, f"circular state reference {state!r}"
                tokens.extend(cls._process_state(unprocessed, processed,
                                                 str(tdef)))
                continue
            if isinstance(tdef, _inherit):
                # should be processed already, but may not in the case of:
                # 1. the state has no counterpart in any parent
                # 2. the state includes more than one 'inherit'
                continue
            if isinstance(tdef, default):
                new_state = cls._process_new_state(tdef.state, unprocessed, processed)
                tokens.append((re.compile('').match, None, new_state))
                continue

            assert type(tdef) is tuple, f"wrong rule def {tdef!r}"

            try:
                rex = cls._process_regex(tdef[0], rflags, state)
            except Exception as err:
                raise ValueError(f"uncompilable regex {tdef[0]!r} in state {state!r} of {cls!r}: {err}") from err

            token = cls._process_token(tdef[1])

            if len(tdef) == 2:
                new_state = None
            else:
                new_state = cls._process_new_state(tdef[2],
                                                   unprocessed, processed)

            tokens.append((rex, token, new_state))
        return tokens

    def process_tokendef(cls, name, tokendefs=None):
        """Preprocess a dictionary of token definitions."""
        processed = cls._all_tokens[name] = {}
        tokendefs = tokendefs or cls.tokens[name]
        for state in list(tokendefs):
            cls._process_state(tokendefs, processed, state)
        return processed

    def get_tokendefs(cls):
        """
        Merge tokens from superclasses in MRO order, returning a single tokendef
        dictionary.

        Any state that is not defined by a subclass will be inherited
        automatically.  States that *are* defined by subclasses will, by
        default, override that state in the superclass.  If a subclass wishes to
        inherit definitions from a superclass, it can use the special value
        "inherit", which will cause the superclass' state definition to be
        included at that point in the state.
        """
        tokens = {}
        inheritable = {}
        for c in cls.__mro__:
            toks = c.__dict__.get('tokens', {})

            for state, items in toks.items():
                curitems = tokens.get(state)
                if curitems is None:
                    # N.b. because this is assigned by reference, sufficiently
                    # deep hierarchies are processed incrementally (e.g. for
                    # A(B), B(C), C(RegexLexer), B will be premodified so X(B)
                    # will not see any inherits in B).
                    tokens[state] = items
                    try:
                        inherit_ndx = items.index(inherit)
                    except ValueError:
                        continue
                    inheritable[state] = inherit_ndx
                    continue

                inherit_ndx = inheritable.pop(state, None)
                if inherit_ndx is None:
                    continue

                # Replace the "inherit" value with the items
                curitems[inherit_ndx:inherit_ndx+1] = items
                try:
                    # N.b. this is the index in items (that is, the superclass
                    # copy), so offset required when storing below.
                    new_inh_ndx = items.index(inherit)
                except ValueError:
                    pass
                else:
                    inheritable[state] = inherit_ndx + new_inh_ndx

        return tokens

    def __call__(cls, *args, **kwds):
        """Instantiate cls after preprocessing its token definitions."""
        if '_tokens' not in cls.__dict__:
            cls._all_tokens = {}
            cls._tmpname = 0
            if hasattr(cls, 'token_variants') and cls.token_variants:
                # don't process yet
                pass
            else:
                cls._tokens = cls.process_tokendef('', cls.get_tokendefs())

        return type.__call__(cls, *args, **kwds)


class RegexLexer(Lexer, metaclass=RegexLexerMeta):
    """
    Base for simple stateful regular expression-based lexers.
    Simplifies the lexing process so that you need only
    provide a list of states and regular expressions.
    """

    #: Flags for compiling the regular expressions.
    #: Defaults to MULTILINE.
    flags = re.MULTILINE

    #: At all time there is a stack of states. Initially, the stack contains
    #: a single state 'root'. The top of the stack is called "the current state".
    #:
    #: Dict of ``{'state': [(regex, tokentype, new_state), ...], ...}``
    #:
    #: ``new_state`` can be omitted to signify no state transition.
    #: If ``new_state`` is a string, it is pushed on the stack. This ensure
    #: the new current state is ``new_state``.
    #: If ``new_state`` is a tuple of strings, all of those strings are pushed
    #: on the stack and the current state will be the last element of the list.
    #: ``new_state`` can also be ``combined('state1', 'state2', ...)``
    #: to signify a new, anonymous state combined from the rules of two
    #: or more existing ones.
    #: Furthermore, it can be '#pop' to signify going back one step in
    #: the state stack, or '#push' to push the current state on the stack
    #: again. Note that if you push while in a combined state, the combined
    #: state itself is pushed, and not only the state in which the rule is
    #: defined.
    #:
    #: The tuple can also be replaced with ``include('state')``, in which
    #: case the rules from the state named by the string are included in the
    #: current one.
    tokens = {}

    def get_tokens_unprocessed(self, text, stack=('root',)):
        """
        Split ``text`` into (tokentype, text) pairs.

        ``stack`` is the initial stack (default: ``['root']``)
        """
        pos = 0
        tokendefs = self._tokens
        statestack = list(stack)
        statetokens = tokendefs[statestack[-1]]
        while 1:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, pos)
                if m:
                    if action is not None:
                        if type(action) is _TokenType:
                            yield pos, action, m.group()
                        else:
                            yield from action(self, m)
                    pos = m.end()
                    if new_state is not None:
                        # state transition
                        if isinstance(new_state, tuple):
                            for state in new_state:
                                if state == '#pop':
                                    if len(statestack) > 1:
                                        statestack.pop()
                                elif state == '#push':
                                    statestack.append(statestack[-1])
                                else:
                                    statestack.append(state)
                        elif isinstance(new_state, int):
                            # pop, but keep at least one state on the stack
                            # (random code leading to unexpected pops should
                            # not allow exceptions)
                            if abs(new_state) >= len(statestack):
                                del statestack[1:]
                            else:
                                del statestack[new_state:]
                        elif new_state == '#push':
                            statestack.append(statestack[-1])
                        else:
                            assert False, f"wrong state def: {new_state!r}"
                        statetokens = tokendefs[statestack[-1]]
                    break
            else:
                # We are here only if all state tokens have been considered
                # and there was not a match on any of them.
                try:
                    if text[pos] == '\n':
                        # at EOL, reset state to "root"
                        statestack = ['root']
                        statetokens = tokendefs['root']
                        yield pos, Whitespace, '\n'
                        pos += 1
                        continue
                    yield pos, Error, text[pos]
                    pos += 1
                except IndexError:
                    break


class LexerContext:
    """
    A helper object that holds lexer position data.
    """

    def __init__(self, text, pos, stack=None, end=None):
        self.text = text
        self.pos = pos
        self.end = end or len(text)  # end=0 not supported ;-)
        self.stack = stack or ['root']

    def __repr__(self):
        return f'LexerContext({self.text!r}, {self.pos!r}, {self.stack!r})'


class ExtendedRegexLexer(RegexLexer):
    """
    A RegexLexer that uses a context object to store its state.
    """

    def get_tokens_unprocessed(self, text=None, context=None):
        """
        Split ``text`` into (tokentype, text) pairs.
        If ``context`` is given, use this lexer context instead.
        """
        tokendefs = self._tokens
        if not context:
            ctx = LexerContext(text, 0)
            statetokens = tokendefs['root']
        else:
            ctx = context
            statetokens = tokendefs[ctx.stack[-1]]
            text = ctx.text
        while 1:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, ctx.pos, ctx.end)
                if m:
                    if action is not None:
                        if type(action) is _TokenType:
                            yield ctx.pos, action, m.group()
                            ctx.pos = m.end()
                        else:
                            yield from action(self, m, ctx)
                            if not new_state:
                                # altered the state stack?
                                statetokens = tokendefs[ctx.stack[-1]]
                    # CAUTION: callback must set ctx.pos!
                    if new_state is not None:
                        # state transition
                        if isinstance(new_state, tuple):
                            for state in new_state:
                                if state == '#pop':
                                    if len(ctx.stack) > 1:
                                        ctx.stack.pop()
                                elif state == '#push':
                                    ctx.stack.append(ctx.stack[-1])
                                else:
                                    ctx.stack.append(state)
                        elif isinstance(new_state, int):
                            # see RegexLexer for why this check is made
                            if abs(new_state) >= len(ctx.stack):
                                del ctx.stack[1:]
                            else:
                                del ctx.stack[new_state:]
                        elif new_state == '#push':
                            ctx.stack.append(ctx.stack[-1])
                        else:
                            assert False, f"wrong state def: {new_state!r}"
                        statetokens = tokendefs[ctx.stack[-1]]
                    break
            else:
                try:
                    if ctx.pos >= ctx.end:
                        break
                    if text[ctx.pos] == '\n':
                        # at EOL, reset state to "root"
                        ctx.stack = ['root']
                        statetokens = tokendefs['root']
                        yield ctx.pos, Text, '\n'
                        ctx.pos += 1
                        continue
                    yield ctx.pos, Error, text[ctx.pos]
                    ctx.pos += 1
                except IndexError:
                    break


def do_insertions(insertions, tokens):
    """
    Helper for lexers which must combine the results of several
    sublexers.

    ``insertions`` is a list of ``(index, itokens)`` pairs.
    Each ``itokens`` iterable should be inserted at position
    ``index`` into the token stream given by the ``tokens``
    argument.

    The result is a combined token stream.

    TODO: clean up the code here.
    """
    insertions = iter(insertions)
    try:
        index, itokens = next(insertions)
    except StopIteration:
        # no insertions
        yield from tokens
        return

    realpos = None
    insleft = True

    # iterate over the token stream where we want to insert
    # the tokens from the insertion list.
    for i, t, v in tokens:
        # first iteration. store the position of first item
        if realpos is None:
            realpos = i
        oldi = 0
        while insleft and i + len(v) >= index:
            tmpval = v[oldi:index - i]
            if tmpval:
                yield realpos, t, tmpval
                realpos += len(tmpval)
            for it_index, it_token, it_value in itokens:
                yield realpos, it_token, it_value
                realpos += len(it_value)
            oldi = index - i
            try:
                index, itokens = next(insertions)
            except StopIteration:
                insleft = False
                break  # not strictly necessary
        if oldi < len(v):
            yield realpos, t, v[oldi:]
            realpos += len(v) - oldi

    # leftover tokens
    while insleft:
        # no normal tokens, set realpos to zero
        realpos = realpos or 0
        for p, t, v in itokens:
            yield realpos, t, v
            realpos += len(v)
        try:
            index, itokens = next(insertions)
        except StopIteration:
            insleft = False
            break  # not strictly necessary


class ProfilingRegexLexerMeta(RegexLexerMeta):
    """Metaclass for ProfilingRegexLexer, collects regex timing info."""

    def _process_regex(cls, regex, rflags, state):
        if isinstance(regex, words):
            rex = regex_opt(regex.words, prefix=regex.prefix,
                            suffix=regex.suffix)
        else:
            rex = regex
        compiled = re.compile(rex, rflags)

        def match_func(text, pos, endpos=sys.maxsize):
            info = cls._prof_data[-1].setdefault((state, rex), [0, 0.0])
            t0 = time.time()
            res = compiled.match(text, pos, endpos)
            t1 = time.time()
            info[0] += 1
            info[1] += t1 - t0
            return res
        return match_func


class ProfilingRegexLexer(RegexLexer, metaclass=ProfilingRegexLexerMeta):
    """Drop-in replacement for RegexLexer that does profiling of its regexes."""

    _prof_data = []
    _prof_sort_index = 4  # defaults to time per call

    def get_tokens_unprocessed(self, text, stack=('root',)):
        # this needs to be a stack, since using(this) will produce nested calls
        self.__class__._prof_data.append({})
        yield from RegexLexer.get_tokens_unprocessed(self, text, stack)
        rawdata = self.__class__._prof_data.pop()
        data = sorted(((s, repr(r).strip('u\'').replace('\\\\', '\\')[:65],
                        n, 1000 * t, 1000 * t / n)
                       for ((s, r), (n, t)) in rawdata.items()),
                      key=lambda x: x[self._prof_sort_index],
                      reverse=True)
        sum_total = sum(x[3] for x in data)

        print()
        print('Profiling result for %s lexing %d chars in %.3f ms' %
              (self.__class__.__name__, len(text), sum_total))
        print('=' * 110)
        print('%-20s %-64s ncalls  tottime  percall' % ('state', 'regex'))
        print('-' * 110)
        for d in data:
            print('%-20s %-65s %5d %8.4f %8.4f' % d)
        print('=' * 110)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\lexer.py ===
"""
    pygments.lexer
    ~~~~~~~~~~~~~~

    Base lexer classes.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import sys
import time

from pip._vendor.pygments.filter import apply_filters, Filter
from pip._vendor.pygments.filters import get_filter_by_name
from pip._vendor.pygments.token import Error, Text, Other, Whitespace, _TokenType
from pip._vendor.pygments.util import get_bool_opt, get_int_opt, get_list_opt, \
    make_analysator, Future, guess_decode
from pip._vendor.pygments.regexopt import regex_opt

__all__ = ['Lexer', 'RegexLexer', 'ExtendedRegexLexer', 'DelegatingLexer',
           'LexerContext', 'include', 'inherit', 'bygroups', 'using', 'this',
           'default', 'words', 'line_re']

line_re = re.compile('.*?\n')

_encoding_map = [(b'\xef\xbb\xbf', 'utf-8'),
                 (b'\xff\xfe\0\0', 'utf-32'),
                 (b'\0\0\xfe\xff', 'utf-32be'),
                 (b'\xff\xfe', 'utf-16'),
                 (b'\xfe\xff', 'utf-16be')]

_default_analyse = staticmethod(lambda x: 0.0)


class LexerMeta(type):
    """
    This metaclass automagically converts ``analyse_text`` methods into
    static methods which always return float values.
    """

    def __new__(mcs, name, bases, d):
        if 'analyse_text' in d:
            d['analyse_text'] = make_analysator(d['analyse_text'])
        return type.__new__(mcs, name, bases, d)


class Lexer(metaclass=LexerMeta):
    """
    Lexer for a specific language.

    See also :doc:`lexerdevelopment`, a high-level guide to writing
    lexers.

    Lexer classes have attributes used for choosing the most appropriate
    lexer based on various criteria.

    .. autoattribute:: name
       :no-value:
    .. autoattribute:: aliases
       :no-value:
    .. autoattribute:: filenames
       :no-value:
    .. autoattribute:: alias_filenames
    .. autoattribute:: mimetypes
       :no-value:
    .. autoattribute:: priority

    Lexers included in Pygments should have two additional attributes:

    .. autoattribute:: url
       :no-value:
    .. autoattribute:: version_added
       :no-value:

    Lexers included in Pygments may have additional attributes:

    .. autoattribute:: _example
       :no-value:

    You can pass options to the constructor. The basic options recognized
    by all lexers and processed by the base `Lexer` class are:

    ``stripnl``
        Strip leading and trailing newlines from the input (default: True).
    ``stripall``
        Strip all leading and trailing whitespace from the input
        (default: False).
    ``ensurenl``
        Make sure that the input ends with a newline (default: True).  This
        is required for some lexers that consume input linewise.

        .. versionadded:: 1.3

    ``tabsize``
        If given and greater than 0, expand tabs in the input (default: 0).
    ``encoding``
        If given, must be an encoding name. This encoding will be used to
        convert the input string to Unicode, if it is not already a Unicode
        string (default: ``'guess'``, which uses a simple UTF-8 / Locale /
        Latin1 detection.  Can also be ``'chardet'`` to use the chardet
        library, if it is installed.
    ``inencoding``
        Overrides the ``encoding`` if given.
    """

    #: Full name of the lexer, in human-readable form
    name = None

    #: A list of short, unique identifiers that can be used to look
    #: up the lexer from a list, e.g., using `get_lexer_by_name()`.
    aliases = []

    #: A list of `fnmatch` patterns that match filenames which contain
    #: content for this lexer. The patterns in this list should be unique among
    #: all lexers.
    filenames = []

    #: A list of `fnmatch` patterns that match filenames which may or may not
    #: contain content for this lexer. This list is used by the
    #: :func:`.guess_lexer_for_filename()` function, to determine which lexers
    #: are then included in guessing the correct one. That means that
    #: e.g. every lexer for HTML and a template language should include
    #: ``\*.html`` in this list.
    alias_filenames = []

    #: A list of MIME types for content that can be lexed with this lexer.
    mimetypes = []

    #: Priority, should multiple lexers match and no content is provided
    priority = 0

    #: URL of the language specification/definition. Used in the Pygments
    #: documentation. Set to an empty string to disable.
    url = None

    #: Version of Pygments in which the lexer was added.
    version_added = None

    #: Example file name. Relative to the ``tests/examplefiles`` directory.
    #: This is used by the documentation generator to show an example.
    _example = None

    def __init__(self, **options):
        """
        This constructor takes arbitrary options as keyword arguments.
        Every subclass must first process its own options and then call
        the `Lexer` constructor, since it processes the basic
        options like `stripnl`.

        An example looks like this:

        .. sourcecode:: python

           def __init__(self, **options):
               self.compress = options.get('compress', '')
               Lexer.__init__(self, **options)

        As these options must all be specifiable as strings (due to the
        command line usage), there are various utility functions
        available to help with that, see `Utilities`_.
        """
        self.options = options
        self.stripnl = get_bool_opt(options, 'stripnl', True)
        self.stripall = get_bool_opt(options, 'stripall', False)
        self.ensurenl = get_bool_opt(options, 'ensurenl', True)
        self.tabsize = get_int_opt(options, 'tabsize', 0)
        self.encoding = options.get('encoding', 'guess')
        self.encoding = options.get('inencoding') or self.encoding
        self.filters = []
        for filter_ in get_list_opt(options, 'filters', ()):
            self.add_filter(filter_)

    def __repr__(self):
        if self.options:
            return f'<pygments.lexers.{self.__class__.__name__} with {self.options!r}>'
        else:
            return f'<pygments.lexers.{self.__class__.__name__}>'

    def add_filter(self, filter_, **options):
        """
        Add a new stream filter to this lexer.
        """
        if not isinstance(filter_, Filter):
            filter_ = get_filter_by_name(filter_, **options)
        self.filters.append(filter_)

    def analyse_text(text):
        """
        A static method which is called for lexer guessing.

        It should analyse the text and return a float in the range
        from ``0.0`` to ``1.0``.  If it returns ``0.0``, the lexer
        will not be selected as the most probable one, if it returns
        ``1.0``, it will be selected immediately.  This is used by
        `guess_lexer`.

        The `LexerMeta` metaclass automatically wraps this function so
        that it works like a static method (no ``self`` or ``cls``
        parameter) and the return value is automatically converted to
        `float`. If the return value is an object that is boolean `False`
        it's the same as if the return values was ``0.0``.
        """

    def _preprocess_lexer_input(self, text):
        """Apply preprocessing such as decoding the input, removing BOM and normalizing newlines."""

        if not isinstance(text, str):
            if self.encoding == 'guess':
                text, _ = guess_decode(text)
            elif self.encoding == 'chardet':
                try:
                    # pip vendoring note: this code is not reachable by pip,
                    # removed import of chardet to make it clear.
                    raise ImportError('chardet is not vendored by pip')
                except ImportError as e:
                    raise ImportError('To enable chardet encoding guessing, '
                                      'please install the chardet library '
                                      'from http://chardet.feedparser.org/') from e
                # check for BOM first
                decoded = None
                for bom, encoding in _encoding_map:
                    if text.startswith(bom):
                        decoded = text[len(bom):].decode(encoding, 'replace')
                        break
                # no BOM found, so use chardet
                if decoded is None:
                    enc = chardet.detect(text[:1024])  # Guess using first 1KB
                    decoded = text.decode(enc.get('encoding') or 'utf-8',
                                          'replace')
                text = decoded
            else:
                text = text.decode(self.encoding)
                if text.startswith('\ufeff'):
                    text = text[len('\ufeff'):]
        else:
            if text.startswith('\ufeff'):
                text = text[len('\ufeff'):]

        # text now *is* a unicode string
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        if self.stripall:
            text = text.strip()
        elif self.stripnl:
            text = text.strip('\n')
        if self.tabsize > 0:
            text = text.expandtabs(self.tabsize)
        if self.ensurenl and not text.endswith('\n'):
            text += '\n'

        return text

    def get_tokens(self, text, unfiltered=False):
        """
        This method is the basic interface of a lexer. It is called by
        the `highlight()` function. It must process the text and return an
        iterable of ``(tokentype, value)`` pairs from `text`.

        Normally, you don't need to override this method. The default
        implementation processes the options recognized by all lexers
        (`stripnl`, `stripall` and so on), and then yields all tokens
        from `get_tokens_unprocessed()`, with the ``index`` dropped.

        If `unfiltered` is set to `True`, the filtering mechanism is
        bypassed even if filters are defined.
        """
        text = self._preprocess_lexer_input(text)

        def streamer():
            for _, t, v in self.get_tokens_unprocessed(text):
                yield t, v
        stream = streamer()
        if not unfiltered:
            stream = apply_filters(stream, self.filters, self)
        return stream

    def get_tokens_unprocessed(self, text):
        """
        This method should process the text and return an iterable of
        ``(index, tokentype, value)`` tuples where ``index`` is the starting
        position of the token within the input text.

        It must be overridden by subclasses. It is recommended to
        implement it as a generator to maximize effectiveness.
        """
        raise NotImplementedError


class DelegatingLexer(Lexer):
    """
    This lexer takes two lexer as arguments. A root lexer and
    a language lexer. First everything is scanned using the language
    lexer, afterwards all ``Other`` tokens are lexed using the root
    lexer.

    The lexers from the ``template`` lexer package use this base lexer.
    """

    def __init__(self, _root_lexer, _language_lexer, _needle=Other, **options):
        self.root_lexer = _root_lexer(**options)
        self.language_lexer = _language_lexer(**options)
        self.needle = _needle
        Lexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        buffered = ''
        insertions = []
        lng_buffer = []
        for i, t, v in self.language_lexer.get_tokens_unprocessed(text):
            if t is self.needle:
                if lng_buffer:
                    insertions.append((len(buffered), lng_buffer))
                    lng_buffer = []
                buffered += v
            else:
                lng_buffer.append((i, t, v))
        if lng_buffer:
            insertions.append((len(buffered), lng_buffer))
        return do_insertions(insertions,
                             self.root_lexer.get_tokens_unprocessed(buffered))


# ------------------------------------------------------------------------------
# RegexLexer and ExtendedRegexLexer
#


class include(str):  # pylint: disable=invalid-name
    """
    Indicates that a state should include rules from another state.
    """
    pass


class _inherit:
    """
    Indicates the a state should inherit from its superclass.
    """
    def __repr__(self):
        return 'inherit'

inherit = _inherit()  # pylint: disable=invalid-name


class combined(tuple):  # pylint: disable=invalid-name
    """
    Indicates a state combined from multiple states.
    """

    def __new__(cls, *args):
        return tuple.__new__(cls, args)

    def __init__(self, *args):
        # tuple.__init__ doesn't do anything
        pass


class _PseudoMatch:
    """
    A pseudo match object constructed from a string.
    """

    def __init__(self, start, text):
        self._text = text
        self._start = start

    def start(self, arg=None):
        return self._start

    def end(self, arg=None):
        return self._start + len(self._text)

    def group(self, arg=None):
        if arg:
            raise IndexError('No such group')
        return self._text

    def groups(self):
        return (self._text,)

    def groupdict(self):
        return {}


def bygroups(*args):
    """
    Callback that yields multiple actions for each group in the match.
    """
    def callback(lexer, match, ctx=None):
        for i, action in enumerate(args):
            if action is None:
                continue
            elif type(action) is _TokenType:
                data = match.group(i + 1)
                if data:
                    yield match.start(i + 1), action, data
            else:
                data = match.group(i + 1)
                if data is not None:
                    if ctx:
                        ctx.pos = match.start(i + 1)
                    for item in action(lexer,
                                       _PseudoMatch(match.start(i + 1), data), ctx):
                        if item:
                            yield item
        if ctx:
            ctx.pos = match.end()
    return callback


class _This:
    """
    Special singleton used for indicating the caller class.
    Used by ``using``.
    """

this = _This()


def using(_other, **kwargs):
    """
    Callback that processes the match with a different lexer.

    The keyword arguments are forwarded to the lexer, except `state` which
    is handled separately.

    `state` specifies the state that the new lexer will start in, and can
    be an enumerable such as ('root', 'inline', 'string') or a simple
    string which is assumed to be on top of the root state.

    Note: For that to work, `_other` must not be an `ExtendedRegexLexer`.
    """
    gt_kwargs = {}
    if 'state' in kwargs:
        s = kwargs.pop('state')
        if isinstance(s, (list, tuple)):
            gt_kwargs['stack'] = s
        else:
            gt_kwargs['stack'] = ('root', s)

    if _other is this:
        def callback(lexer, match, ctx=None):
            # if keyword arguments are given the callback
            # function has to create a new lexer instance
            if kwargs:
                # XXX: cache that somehow
                kwargs.update(lexer.options)
                lx = lexer.__class__(**kwargs)
            else:
                lx = lexer
            s = match.start()
            for i, t, v in lx.get_tokens_unprocessed(match.group(), **gt_kwargs):
                yield i + s, t, v
            if ctx:
                ctx.pos = match.end()
    else:
        def callback(lexer, match, ctx=None):
            # XXX: cache that somehow
            kwargs.update(lexer.options)
            lx = _other(**kwargs)

            s = match.start()
            for i, t, v in lx.get_tokens_unprocessed(match.group(), **gt_kwargs):
                yield i + s, t, v
            if ctx:
                ctx.pos = match.end()
    return callback


class default:
    """
    Indicates a state or state action (e.g. #pop) to apply.
    For example default('#pop') is equivalent to ('', Token, '#pop')
    Note that state tuples may be used as well.

    .. versionadded:: 2.0
    """
    def __init__(self, state):
        self.state = state


class words(Future):
    """
    Indicates a list of literal words that is transformed into an optimized
    regex that matches any of the words.

    .. versionadded:: 2.0
    """
    def __init__(self, words, prefix='', suffix=''):
        self.words = words
        self.prefix = prefix
        self.suffix = suffix

    def get(self):
        return regex_opt(self.words, prefix=self.prefix, suffix=self.suffix)


class RegexLexerMeta(LexerMeta):
    """
    Metaclass for RegexLexer, creates the self._tokens attribute from
    self.tokens on the first instantiation.
    """

    def _process_regex(cls, regex, rflags, state):
        """Preprocess the regular expression component of a token definition."""
        if isinstance(regex, Future):
            regex = regex.get()
        return re.compile(regex, rflags).match

    def _process_token(cls, token):
        """Preprocess the token component of a token definition."""
        assert type(token) is _TokenType or callable(token), \
            f'token type must be simple type or callable, not {token!r}'
        return token

    def _process_new_state(cls, new_state, unprocessed, processed):
        """Preprocess the state transition action of a token definition."""
        if isinstance(new_state, str):
            # an existing state
            if new_state == '#pop':
                return -1
            elif new_state in unprocessed:
                return (new_state,)
            elif new_state == '#push':
                return new_state
            elif new_state[:5] == '#pop:':
                return -int(new_state[5:])
            else:
                assert False, f'unknown new state {new_state!r}'
        elif isinstance(new_state, combined):
            # combine a new state from existing ones
            tmp_state = '_tmp_%d' % cls._tmpname
            cls._tmpname += 1
            itokens = []
            for istate in new_state:
                assert istate != new_state, f'circular state ref {istate!r}'
                itokens.extend(cls._process_state(unprocessed,
                                                  processed, istate))
            processed[tmp_state] = itokens
            return (tmp_state,)
        elif isinstance(new_state, tuple):
            # push more than one state
            for istate in new_state:
                assert (istate in unprocessed or
                        istate in ('#pop', '#push')), \
                    'unknown new state ' + istate
            return new_state
        else:
            assert False, f'unknown new state def {new_state!r}'

    def _process_state(cls, unprocessed, processed, state):
        """Preprocess a single state definition."""
        assert isinstance(state, str), f"wrong state name {state!r}"
        assert state[0] != '#', f"invalid state name {state!r}"
        if state in processed:
            return processed[state]
        tokens = processed[state] = []
        rflags = cls.flags
        for tdef in unprocessed[state]:
            if isinstance(tdef, include):
                # it's a state reference
                assert tdef != state, f"circular state reference {state!r}"
                tokens.extend(cls._process_state(unprocessed, processed,
                                                 str(tdef)))
                continue
            if isinstance(tdef, _inherit):
                # should be processed already, but may not in the case of:
                # 1. the state has no counterpart in any parent
                # 2. the state includes more than one 'inherit'
                continue
            if isinstance(tdef, default):
                new_state = cls._process_new_state(tdef.state, unprocessed, processed)
                tokens.append((re.compile('').match, None, new_state))
                continue

            assert type(tdef) is tuple, f"wrong rule def {tdef!r}"

            try:
                rex = cls._process_regex(tdef[0], rflags, state)
            except Exception as err:
                raise ValueError(f"uncompilable regex {tdef[0]!r} in state {state!r} of {cls!r}: {err}") from err

            token = cls._process_token(tdef[1])

            if len(tdef) == 2:
                new_state = None
            else:
                new_state = cls._process_new_state(tdef[2],
                                                   unprocessed, processed)

            tokens.append((rex, token, new_state))
        return tokens

    def process_tokendef(cls, name, tokendefs=None):
        """Preprocess a dictionary of token definitions."""
        processed = cls._all_tokens[name] = {}
        tokendefs = tokendefs or cls.tokens[name]
        for state in list(tokendefs):
            cls._process_state(tokendefs, processed, state)
        return processed

    def get_tokendefs(cls):
        """
        Merge tokens from superclasses in MRO order, returning a single tokendef
        dictionary.

        Any state that is not defined by a subclass will be inherited
        automatically.  States that *are* defined by subclasses will, by
        default, override that state in the superclass.  If a subclass wishes to
        inherit definitions from a superclass, it can use the special value
        "inherit", which will cause the superclass' state definition to be
        included at that point in the state.
        """
        tokens = {}
        inheritable = {}
        for c in cls.__mro__:
            toks = c.__dict__.get('tokens', {})

            for state, items in toks.items():
                curitems = tokens.get(state)
                if curitems is None:
                    # N.b. because this is assigned by reference, sufficiently
                    # deep hierarchies are processed incrementally (e.g. for
                    # A(B), B(C), C(RegexLexer), B will be premodified so X(B)
                    # will not see any inherits in B).
                    tokens[state] = items
                    try:
                        inherit_ndx = items.index(inherit)
                    except ValueError:
                        continue
                    inheritable[state] = inherit_ndx
                    continue

                inherit_ndx = inheritable.pop(state, None)
                if inherit_ndx is None:
                    continue

                # Replace the "inherit" value with the items
                curitems[inherit_ndx:inherit_ndx+1] = items
                try:
                    # N.b. this is the index in items (that is, the superclass
                    # copy), so offset required when storing below.
                    new_inh_ndx = items.index(inherit)
                except ValueError:
                    pass
                else:
                    inheritable[state] = inherit_ndx + new_inh_ndx

        return tokens

    def __call__(cls, *args, **kwds):
        """Instantiate cls after preprocessing its token definitions."""
        if '_tokens' not in cls.__dict__:
            cls._all_tokens = {}
            cls._tmpname = 0
            if hasattr(cls, 'token_variants') and cls.token_variants:
                # don't process yet
                pass
            else:
                cls._tokens = cls.process_tokendef('', cls.get_tokendefs())

        return type.__call__(cls, *args, **kwds)


class RegexLexer(Lexer, metaclass=RegexLexerMeta):
    """
    Base for simple stateful regular expression-based lexers.
    Simplifies the lexing process so that you need only
    provide a list of states and regular expressions.
    """

    #: Flags for compiling the regular expressions.
    #: Defaults to MULTILINE.
    flags = re.MULTILINE

    #: At all time there is a stack of states. Initially, the stack contains
    #: a single state 'root'. The top of the stack is called "the current state".
    #:
    #: Dict of ``{'state': [(regex, tokentype, new_state), ...], ...}``
    #:
    #: ``new_state`` can be omitted to signify no state transition.
    #: If ``new_state`` is a string, it is pushed on the stack. This ensure
    #: the new current state is ``new_state``.
    #: If ``new_state`` is a tuple of strings, all of those strings are pushed
    #: on the stack and the current state will be the last element of the list.
    #: ``new_state`` can also be ``combined('state1', 'state2', ...)``
    #: to signify a new, anonymous state combined from the rules of two
    #: or more existing ones.
    #: Furthermore, it can be '#pop' to signify going back one step in
    #: the state stack, or '#push' to push the current state on the stack
    #: again. Note that if you push while in a combined state, the combined
    #: state itself is pushed, and not only the state in which the rule is
    #: defined.
    #:
    #: The tuple can also be replaced with ``include('state')``, in which
    #: case the rules from the state named by the string are included in the
    #: current one.
    tokens = {}

    def get_tokens_unprocessed(self, text, stack=('root',)):
        """
        Split ``text`` into (tokentype, text) pairs.

        ``stack`` is the initial stack (default: ``['root']``)
        """
        pos = 0
        tokendefs = self._tokens
        statestack = list(stack)
        statetokens = tokendefs[statestack[-1]]
        while 1:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, pos)
                if m:
                    if action is not None:
                        if type(action) is _TokenType:
                            yield pos, action, m.group()
                        else:
                            yield from action(self, m)
                    pos = m.end()
                    if new_state is not None:
                        # state transition
                        if isinstance(new_state, tuple):
                            for state in new_state:
                                if state == '#pop':
                                    if len(statestack) > 1:
                                        statestack.pop()
                                elif state == '#push':
                                    statestack.append(statestack[-1])
                                else:
                                    statestack.append(state)
                        elif isinstance(new_state, int):
                            # pop, but keep at least one state on the stack
                            # (random code leading to unexpected pops should
                            # not allow exceptions)
                            if abs(new_state) >= len(statestack):
                                del statestack[1:]
                            else:
                                del statestack[new_state:]
                        elif new_state == '#push':
                            statestack.append(statestack[-1])
                        else:
                            assert False, f"wrong state def: {new_state!r}"
                        statetokens = tokendefs[statestack[-1]]
                    break
            else:
                # We are here only if all state tokens have been considered
                # and there was not a match on any of them.
                try:
                    if text[pos] == '\n':
                        # at EOL, reset state to "root"
                        statestack = ['root']
                        statetokens = tokendefs['root']
                        yield pos, Whitespace, '\n'
                        pos += 1
                        continue
                    yield pos, Error, text[pos]
                    pos += 1
                except IndexError:
                    break


class LexerContext:
    """
    A helper object that holds lexer position data.
    """

    def __init__(self, text, pos, stack=None, end=None):
        self.text = text
        self.pos = pos
        self.end = end or len(text)  # end=0 not supported ;-)
        self.stack = stack or ['root']

    def __repr__(self):
        return f'LexerContext({self.text!r}, {self.pos!r}, {self.stack!r})'


class ExtendedRegexLexer(RegexLexer):
    """
    A RegexLexer that uses a context object to store its state.
    """

    def get_tokens_unprocessed(self, text=None, context=None):
        """
        Split ``text`` into (tokentype, text) pairs.
        If ``context`` is given, use this lexer context instead.
        """
        tokendefs = self._tokens
        if not context:
            ctx = LexerContext(text, 0)
            statetokens = tokendefs['root']
        else:
            ctx = context
            statetokens = tokendefs[ctx.stack[-1]]
            text = ctx.text
        while 1:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, ctx.pos, ctx.end)
                if m:
                    if action is not None:
                        if type(action) is _TokenType:
                            yield ctx.pos, action, m.group()
                            ctx.pos = m.end()
                        else:
                            yield from action(self, m, ctx)
                            if not new_state:
                                # altered the state stack?
                                statetokens = tokendefs[ctx.stack[-1]]
                    # CAUTION: callback must set ctx.pos!
                    if new_state is not None:
                        # state transition
                        if isinstance(new_state, tuple):
                            for state in new_state:
                                if state == '#pop':
                                    if len(ctx.stack) > 1:
                                        ctx.stack.pop()
                                elif state == '#push':
                                    ctx.stack.append(ctx.stack[-1])
                                else:
                                    ctx.stack.append(state)
                        elif isinstance(new_state, int):
                            # see RegexLexer for why this check is made
                            if abs(new_state) >= len(ctx.stack):
                                del ctx.stack[1:]
                            else:
                                del ctx.stack[new_state:]
                        elif new_state == '#push':
                            ctx.stack.append(ctx.stack[-1])
                        else:
                            assert False, f"wrong state def: {new_state!r}"
                        statetokens = tokendefs[ctx.stack[-1]]
                    break
            else:
                try:
                    if ctx.pos >= ctx.end:
                        break
                    if text[ctx.pos] == '\n':
                        # at EOL, reset state to "root"
                        ctx.stack = ['root']
                        statetokens = tokendefs['root']
                        yield ctx.pos, Text, '\n'
                        ctx.pos += 1
                        continue
                    yield ctx.pos, Error, text[ctx.pos]
                    ctx.pos += 1
                except IndexError:
                    break


def do_insertions(insertions, tokens):
    """
    Helper for lexers which must combine the results of several
    sublexers.

    ``insertions`` is a list of ``(index, itokens)`` pairs.
    Each ``itokens`` iterable should be inserted at position
    ``index`` into the token stream given by the ``tokens``
    argument.

    The result is a combined token stream.

    TODO: clean up the code here.
    """
    insertions = iter(insertions)
    try:
        index, itokens = next(insertions)
    except StopIteration:
        # no insertions
        yield from tokens
        return

    realpos = None
    insleft = True

    # iterate over the token stream where we want to insert
    # the tokens from the insertion list.
    for i, t, v in tokens:
        # first iteration. store the position of first item
        if realpos is None:
            realpos = i
        oldi = 0
        while insleft and i + len(v) >= index:
            tmpval = v[oldi:index - i]
            if tmpval:
                yield realpos, t, tmpval
                realpos += len(tmpval)
            for it_index, it_token, it_value in itokens:
                yield realpos, it_token, it_value
                realpos += len(it_value)
            oldi = index - i
            try:
                index, itokens = next(insertions)
            except StopIteration:
                insleft = False
                break  # not strictly necessary
        if oldi < len(v):
            yield realpos, t, v[oldi:]
            realpos += len(v) - oldi

    # leftover tokens
    while insleft:
        # no normal tokens, set realpos to zero
        realpos = realpos or 0
        for p, t, v in itokens:
            yield realpos, t, v
            realpos += len(v)
        try:
            index, itokens = next(insertions)
        except StopIteration:
            insleft = False
            break  # not strictly necessary


class ProfilingRegexLexerMeta(RegexLexerMeta):
    """Metaclass for ProfilingRegexLexer, collects regex timing info."""

    def _process_regex(cls, regex, rflags, state):
        if isinstance(regex, words):
            rex = regex_opt(regex.words, prefix=regex.prefix,
                            suffix=regex.suffix)
        else:
            rex = regex
        compiled = re.compile(rex, rflags)

        def match_func(text, pos, endpos=sys.maxsize):
            info = cls._prof_data[-1].setdefault((state, rex), [0, 0.0])
            t0 = time.time()
            res = compiled.match(text, pos, endpos)
            t1 = time.time()
            info[0] += 1
            info[1] += t1 - t0
            return res
        return match_func


class ProfilingRegexLexer(RegexLexer, metaclass=ProfilingRegexLexerMeta):
    """Drop-in replacement for RegexLexer that does profiling of its regexes."""

    _prof_data = []
    _prof_sort_index = 4  # defaults to time per call

    def get_tokens_unprocessed(self, text, stack=('root',)):
        # this needs to be a stack, since using(this) will produce nested calls
        self.__class__._prof_data.append({})
        yield from RegexLexer.get_tokens_unprocessed(self, text, stack)
        rawdata = self.__class__._prof_data.pop()
        data = sorted(((s, repr(r).strip('u\'').replace('\\\\', '\\')[:65],
                        n, 1000 * t, 1000 * t / n)
                       for ((s, r), (n, t)) in rawdata.items()),
                      key=lambda x: x[self._prof_sort_index],
                      reverse=True)
        sum_total = sum(x[3] for x in data)

        print()
        print('Profiling result for %s lexing %d chars in %.3f ms' %
              (self.__class__.__name__, len(text), sum_total))
        print('=' * 110)
        print('%-20s %-64s ncalls  tottime  percall' % ('state', 'regex'))
        print('-' * 110)
        for d in data:
            print('%-20s %-65s %5d %8.4f %8.4f' % d)
        print('=' * 110)

# === NexusCore/openenv\Lib\site-packages\pygments\lexer.py ===
"""
    pygments.lexer
    ~~~~~~~~~~~~~~

    Base lexer classes.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import sys
import time

from pygments.filter import apply_filters, Filter
from pygments.filters import get_filter_by_name
from pygments.token import Error, Text, Other, Whitespace, _TokenType
from pygments.util import get_bool_opt, get_int_opt, get_list_opt, \
    make_analysator, Future, guess_decode
from pygments.regexopt import regex_opt

__all__ = ['Lexer', 'RegexLexer', 'ExtendedRegexLexer', 'DelegatingLexer',
           'LexerContext', 'include', 'inherit', 'bygroups', 'using', 'this',
           'default', 'words', 'line_re']

line_re = re.compile('.*?\n')

_encoding_map = [(b'\xef\xbb\xbf', 'utf-8'),
                 (b'\xff\xfe\0\0', 'utf-32'),
                 (b'\0\0\xfe\xff', 'utf-32be'),
                 (b'\xff\xfe', 'utf-16'),
                 (b'\xfe\xff', 'utf-16be')]

_default_analyse = staticmethod(lambda x: 0.0)


class LexerMeta(type):
    """
    This metaclass automagically converts ``analyse_text`` methods into
    static methods which always return float values.
    """

    def __new__(mcs, name, bases, d):
        if 'analyse_text' in d:
            d['analyse_text'] = make_analysator(d['analyse_text'])
        return type.__new__(mcs, name, bases, d)


class Lexer(metaclass=LexerMeta):
    """
    Lexer for a specific language.

    See also :doc:`lexerdevelopment`, a high-level guide to writing
    lexers.

    Lexer classes have attributes used for choosing the most appropriate
    lexer based on various criteria.

    .. autoattribute:: name
       :no-value:
    .. autoattribute:: aliases
       :no-value:
    .. autoattribute:: filenames
       :no-value:
    .. autoattribute:: alias_filenames
    .. autoattribute:: mimetypes
       :no-value:
    .. autoattribute:: priority

    Lexers included in Pygments should have two additional attributes:

    .. autoattribute:: url
       :no-value:
    .. autoattribute:: version_added
       :no-value:

    Lexers included in Pygments may have additional attributes:

    .. autoattribute:: _example
       :no-value:

    You can pass options to the constructor. The basic options recognized
    by all lexers and processed by the base `Lexer` class are:

    ``stripnl``
        Strip leading and trailing newlines from the input (default: True).
    ``stripall``
        Strip all leading and trailing whitespace from the input
        (default: False).
    ``ensurenl``
        Make sure that the input ends with a newline (default: True).  This
        is required for some lexers that consume input linewise.

        .. versionadded:: 1.3

    ``tabsize``
        If given and greater than 0, expand tabs in the input (default: 0).
    ``encoding``
        If given, must be an encoding name. This encoding will be used to
        convert the input string to Unicode, if it is not already a Unicode
        string (default: ``'guess'``, which uses a simple UTF-8 / Locale /
        Latin1 detection.  Can also be ``'chardet'`` to use the chardet
        library, if it is installed.
    ``inencoding``
        Overrides the ``encoding`` if given.
    """

    #: Full name of the lexer, in human-readable form
    name = None

    #: A list of short, unique identifiers that can be used to look
    #: up the lexer from a list, e.g., using `get_lexer_by_name()`.
    aliases = []

    #: A list of `fnmatch` patterns that match filenames which contain
    #: content for this lexer. The patterns in this list should be unique among
    #: all lexers.
    filenames = []

    #: A list of `fnmatch` patterns that match filenames which may or may not
    #: contain content for this lexer. This list is used by the
    #: :func:`.guess_lexer_for_filename()` function, to determine which lexers
    #: are then included in guessing the correct one. That means that
    #: e.g. every lexer for HTML and a template language should include
    #: ``\*.html`` in this list.
    alias_filenames = []

    #: A list of MIME types for content that can be lexed with this lexer.
    mimetypes = []

    #: Priority, should multiple lexers match and no content is provided
    priority = 0

    #: URL of the language specification/definition. Used in the Pygments
    #: documentation. Set to an empty string to disable.
    url = None

    #: Version of Pygments in which the lexer was added.
    version_added = None

    #: Example file name. Relative to the ``tests/examplefiles`` directory.
    #: This is used by the documentation generator to show an example.
    _example = None

    def __init__(self, **options):
        """
        This constructor takes arbitrary options as keyword arguments.
        Every subclass must first process its own options and then call
        the `Lexer` constructor, since it processes the basic
        options like `stripnl`.

        An example looks like this:

        .. sourcecode:: python

           def __init__(self, **options):
               self.compress = options.get('compress', '')
               Lexer.__init__(self, **options)

        As these options must all be specifiable as strings (due to the
        command line usage), there are various utility functions
        available to help with that, see `Utilities`_.
        """
        self.options = options
        self.stripnl = get_bool_opt(options, 'stripnl', True)
        self.stripall = get_bool_opt(options, 'stripall', False)
        self.ensurenl = get_bool_opt(options, 'ensurenl', True)
        self.tabsize = get_int_opt(options, 'tabsize', 0)
        self.encoding = options.get('encoding', 'guess')
        self.encoding = options.get('inencoding') or self.encoding
        self.filters = []
        for filter_ in get_list_opt(options, 'filters', ()):
            self.add_filter(filter_)

    def __repr__(self):
        if self.options:
            return f'<pygments.lexers.{self.__class__.__name__} with {self.options!r}>'
        else:
            return f'<pygments.lexers.{self.__class__.__name__}>'

    def add_filter(self, filter_, **options):
        """
        Add a new stream filter to this lexer.
        """
        if not isinstance(filter_, Filter):
            filter_ = get_filter_by_name(filter_, **options)
        self.filters.append(filter_)

    def analyse_text(text):
        """
        A static method which is called for lexer guessing.

        It should analyse the text and return a float in the range
        from ``0.0`` to ``1.0``.  If it returns ``0.0``, the lexer
        will not be selected as the most probable one, if it returns
        ``1.0``, it will be selected immediately.  This is used by
        `guess_lexer`.

        The `LexerMeta` metaclass automatically wraps this function so
        that it works like a static method (no ``self`` or ``cls``
        parameter) and the return value is automatically converted to
        `float`. If the return value is an object that is boolean `False`
        it's the same as if the return values was ``0.0``.
        """

    def _preprocess_lexer_input(self, text):
        """Apply preprocessing such as decoding the input, removing BOM and normalizing newlines."""

        if not isinstance(text, str):
            if self.encoding == 'guess':
                text, _ = guess_decode(text)
            elif self.encoding == 'chardet':
                try:
                    import chardet
                except ImportError as e:
                    raise ImportError('To enable chardet encoding guessing, '
                                      'please install the chardet library '
                                      'from http://chardet.feedparser.org/') from e
                # check for BOM first
                decoded = None
                for bom, encoding in _encoding_map:
                    if text.startswith(bom):
                        decoded = text[len(bom):].decode(encoding, 'replace')
                        break
                # no BOM found, so use chardet
                if decoded is None:
                    enc = chardet.detect(text[:1024])  # Guess using first 1KB
                    decoded = text.decode(enc.get('encoding') or 'utf-8',
                                          'replace')
                text = decoded
            else:
                text = text.decode(self.encoding)
                if text.startswith('\ufeff'):
                    text = text[len('\ufeff'):]
        else:
            if text.startswith('\ufeff'):
                text = text[len('\ufeff'):]

        # text now *is* a unicode string
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        if self.stripall:
            text = text.strip()
        elif self.stripnl:
            text = text.strip('\n')
        if self.tabsize > 0:
            text = text.expandtabs(self.tabsize)
        if self.ensurenl and not text.endswith('\n'):
            text += '\n'

        return text

    def get_tokens(self, text, unfiltered=False):
        """
        This method is the basic interface of a lexer. It is called by
        the `highlight()` function. It must process the text and return an
        iterable of ``(tokentype, value)`` pairs from `text`.

        Normally, you don't need to override this method. The default
        implementation processes the options recognized by all lexers
        (`stripnl`, `stripall` and so on), and then yields all tokens
        from `get_tokens_unprocessed()`, with the ``index`` dropped.

        If `unfiltered` is set to `True`, the filtering mechanism is
        bypassed even if filters are defined.
        """
        text = self._preprocess_lexer_input(text)

        def streamer():
            for _, t, v in self.get_tokens_unprocessed(text):
                yield t, v
        stream = streamer()
        if not unfiltered:
            stream = apply_filters(stream, self.filters, self)
        return stream

    def get_tokens_unprocessed(self, text):
        """
        This method should process the text and return an iterable of
        ``(index, tokentype, value)`` tuples where ``index`` is the starting
        position of the token within the input text.

        It must be overridden by subclasses. It is recommended to
        implement it as a generator to maximize effectiveness.
        """
        raise NotImplementedError


class DelegatingLexer(Lexer):
    """
    This lexer takes two lexer as arguments. A root lexer and
    a language lexer. First everything is scanned using the language
    lexer, afterwards all ``Other`` tokens are lexed using the root
    lexer.

    The lexers from the ``template`` lexer package use this base lexer.
    """

    def __init__(self, _root_lexer, _language_lexer, _needle=Other, **options):
        self.root_lexer = _root_lexer(**options)
        self.language_lexer = _language_lexer(**options)
        self.needle = _needle
        Lexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        buffered = ''
        insertions = []
        lng_buffer = []
        for i, t, v in self.language_lexer.get_tokens_unprocessed(text):
            if t is self.needle:
                if lng_buffer:
                    insertions.append((len(buffered), lng_buffer))
                    lng_buffer = []
                buffered += v
            else:
                lng_buffer.append((i, t, v))
        if lng_buffer:
            insertions.append((len(buffered), lng_buffer))
        return do_insertions(insertions,
                             self.root_lexer.get_tokens_unprocessed(buffered))


# ------------------------------------------------------------------------------
# RegexLexer and ExtendedRegexLexer
#


class include(str):  # pylint: disable=invalid-name
    """
    Indicates that a state should include rules from another state.
    """
    pass


class _inherit:
    """
    Indicates the a state should inherit from its superclass.
    """
    def __repr__(self):
        return 'inherit'

inherit = _inherit()  # pylint: disable=invalid-name


class combined(tuple):  # pylint: disable=invalid-name
    """
    Indicates a state combined from multiple states.
    """

    def __new__(cls, *args):
        return tuple.__new__(cls, args)

    def __init__(self, *args):
        # tuple.__init__ doesn't do anything
        pass


class _PseudoMatch:
    """
    A pseudo match object constructed from a string.
    """

    def __init__(self, start, text):
        self._text = text
        self._start = start

    def start(self, arg=None):
        return self._start

    def end(self, arg=None):
        return self._start + len(self._text)

    def group(self, arg=None):
        if arg:
            raise IndexError('No such group')
        return self._text

    def groups(self):
        return (self._text,)

    def groupdict(self):
        return {}


def bygroups(*args):
    """
    Callback that yields multiple actions for each group in the match.
    """
    def callback(lexer, match, ctx=None):
        for i, action in enumerate(args):
            if action is None:
                continue
            elif type(action) is _TokenType:
                data = match.group(i + 1)
                if data:
                    yield match.start(i + 1), action, data
            else:
                data = match.group(i + 1)
                if data is not None:
                    if ctx:
                        ctx.pos = match.start(i + 1)
                    for item in action(lexer,
                                       _PseudoMatch(match.start(i + 1), data), ctx):
                        if item:
                            yield item
        if ctx:
            ctx.pos = match.end()
    return callback


class _This:
    """
    Special singleton used for indicating the caller class.
    Used by ``using``.
    """

this = _This()


def using(_other, **kwargs):
    """
    Callback that processes the match with a different lexer.

    The keyword arguments are forwarded to the lexer, except `state` which
    is handled separately.

    `state` specifies the state that the new lexer will start in, and can
    be an enumerable such as ('root', 'inline', 'string') or a simple
    string which is assumed to be on top of the root state.

    Note: For that to work, `_other` must not be an `ExtendedRegexLexer`.
    """
    gt_kwargs = {}
    if 'state' in kwargs:
        s = kwargs.pop('state')
        if isinstance(s, (list, tuple)):
            gt_kwargs['stack'] = s
        else:
            gt_kwargs['stack'] = ('root', s)

    if _other is this:
        def callback(lexer, match, ctx=None):
            # if keyword arguments are given the callback
            # function has to create a new lexer instance
            if kwargs:
                # XXX: cache that somehow
                kwargs.update(lexer.options)
                lx = lexer.__class__(**kwargs)
            else:
                lx = lexer
            s = match.start()
            for i, t, v in lx.get_tokens_unprocessed(match.group(), **gt_kwargs):
                yield i + s, t, v
            if ctx:
                ctx.pos = match.end()
    else:
        def callback(lexer, match, ctx=None):
            # XXX: cache that somehow
            kwargs.update(lexer.options)
            lx = _other(**kwargs)

            s = match.start()
            for i, t, v in lx.get_tokens_unprocessed(match.group(), **gt_kwargs):
                yield i + s, t, v
            if ctx:
                ctx.pos = match.end()
    return callback


class default:
    """
    Indicates a state or state action (e.g. #pop) to apply.
    For example default('#pop') is equivalent to ('', Token, '#pop')
    Note that state tuples may be used as well.

    .. versionadded:: 2.0
    """
    def __init__(self, state):
        self.state = state


class words(Future):
    """
    Indicates a list of literal words that is transformed into an optimized
    regex that matches any of the words.

    .. versionadded:: 2.0
    """
    def __init__(self, words, prefix='', suffix=''):
        self.words = words
        self.prefix = prefix
        self.suffix = suffix

    def get(self):
        return regex_opt(self.words, prefix=self.prefix, suffix=self.suffix)


class RegexLexerMeta(LexerMeta):
    """
    Metaclass for RegexLexer, creates the self._tokens attribute from
    self.tokens on the first instantiation.
    """

    def _process_regex(cls, regex, rflags, state):
        """Preprocess the regular expression component of a token definition."""
        if isinstance(regex, Future):
            regex = regex.get()
        return re.compile(regex, rflags).match

    def _process_token(cls, token):
        """Preprocess the token component of a token definition."""
        assert type(token) is _TokenType or callable(token), \
            f'token type must be simple type or callable, not {token!r}'
        return token

    def _process_new_state(cls, new_state, unprocessed, processed):
        """Preprocess the state transition action of a token definition."""
        if isinstance(new_state, str):
            # an existing state
            if new_state == '#pop':
                return -1
            elif new_state in unprocessed:
                return (new_state,)
            elif new_state == '#push':
                return new_state
            elif new_state[:5] == '#pop:':
                return -int(new_state[5:])
            else:
                assert False, f'unknown new state {new_state!r}'
        elif isinstance(new_state, combined):
            # combine a new state from existing ones
            tmp_state = '_tmp_%d' % cls._tmpname
            cls._tmpname += 1
            itokens = []
            for istate in new_state:
                assert istate != new_state, f'circular state ref {istate!r}'
                itokens.extend(cls._process_state(unprocessed,
                                                  processed, istate))
            processed[tmp_state] = itokens
            return (tmp_state,)
        elif isinstance(new_state, tuple):
            # push more than one state
            for istate in new_state:
                assert (istate in unprocessed or
                        istate in ('#pop', '#push')), \
                    'unknown new state ' + istate
            return new_state
        else:
            assert False, f'unknown new state def {new_state!r}'

    def _process_state(cls, unprocessed, processed, state):
        """Preprocess a single state definition."""
        assert isinstance(state, str), f"wrong state name {state!r}"
        assert state[0] != '#', f"invalid state name {state!r}"
        if state in processed:
            return processed[state]
        tokens = processed[state] = []
        rflags = cls.flags
        for tdef in unprocessed[state]:
            if isinstance(tdef, include):
                # it's a state reference
                assert tdef != state, f"circular state reference {state!r}"
                tokens.extend(cls._process_state(unprocessed, processed,
                                                 str(tdef)))
                continue
            if isinstance(tdef, _inherit):
                # should be processed already, but may not in the case of:
                # 1. the state has no counterpart in any parent
                # 2. the state includes more than one 'inherit'
                continue
            if isinstance(tdef, default):
                new_state = cls._process_new_state(tdef.state, unprocessed, processed)
                tokens.append((re.compile('').match, None, new_state))
                continue

            assert type(tdef) is tuple, f"wrong rule def {tdef!r}"

            try:
                rex = cls._process_regex(tdef[0], rflags, state)
            except Exception as err:
                raise ValueError(f"uncompilable regex {tdef[0]!r} in state {state!r} of {cls!r}: {err}") from err

            token = cls._process_token(tdef[1])

            if len(tdef) == 2:
                new_state = None
            else:
                new_state = cls._process_new_state(tdef[2],
                                                   unprocessed, processed)

            tokens.append((rex, token, new_state))
        return tokens

    def process_tokendef(cls, name, tokendefs=None):
        """Preprocess a dictionary of token definitions."""
        processed = cls._all_tokens[name] = {}
        tokendefs = tokendefs or cls.tokens[name]
        for state in list(tokendefs):
            cls._process_state(tokendefs, processed, state)
        return processed

    def get_tokendefs(cls):
        """
        Merge tokens from superclasses in MRO order, returning a single tokendef
        dictionary.

        Any state that is not defined by a subclass will be inherited
        automatically.  States that *are* defined by subclasses will, by
        default, override that state in the superclass.  If a subclass wishes to
        inherit definitions from a superclass, it can use the special value
        "inherit", which will cause the superclass' state definition to be
        included at that point in the state.
        """
        tokens = {}
        inheritable = {}
        for c in cls.__mro__:
            toks = c.__dict__.get('tokens', {})

            for state, items in toks.items():
                curitems = tokens.get(state)
                if curitems is None:
                    # N.b. because this is assigned by reference, sufficiently
                    # deep hierarchies are processed incrementally (e.g. for
                    # A(B), B(C), C(RegexLexer), B will be premodified so X(B)
                    # will not see any inherits in B).
                    tokens[state] = items
                    try:
                        inherit_ndx = items.index(inherit)
                    except ValueError:
                        continue
                    inheritable[state] = inherit_ndx
                    continue

                inherit_ndx = inheritable.pop(state, None)
                if inherit_ndx is None:
                    continue

                # Replace the "inherit" value with the items
                curitems[inherit_ndx:inherit_ndx+1] = items
                try:
                    # N.b. this is the index in items (that is, the superclass
                    # copy), so offset required when storing below.
                    new_inh_ndx = items.index(inherit)
                except ValueError:
                    pass
                else:
                    inheritable[state] = inherit_ndx + new_inh_ndx

        return tokens

    def __call__(cls, *args, **kwds):
        """Instantiate cls after preprocessing its token definitions."""
        if '_tokens' not in cls.__dict__:
            cls._all_tokens = {}
            cls._tmpname = 0
            if hasattr(cls, 'token_variants') and cls.token_variants:
                # don't process yet
                pass
            else:
                cls._tokens = cls.process_tokendef('', cls.get_tokendefs())

        return type.__call__(cls, *args, **kwds)


class RegexLexer(Lexer, metaclass=RegexLexerMeta):
    """
    Base for simple stateful regular expression-based lexers.
    Simplifies the lexing process so that you need only
    provide a list of states and regular expressions.
    """

    #: Flags for compiling the regular expressions.
    #: Defaults to MULTILINE.
    flags = re.MULTILINE

    #: At all time there is a stack of states. Initially, the stack contains
    #: a single state 'root'. The top of the stack is called "the current state".
    #:
    #: Dict of ``{'state': [(regex, tokentype, new_state), ...], ...}``
    #:
    #: ``new_state`` can be omitted to signify no state transition.
    #: If ``new_state`` is a string, it is pushed on the stack. This ensure
    #: the new current state is ``new_state``.
    #: If ``new_state`` is a tuple of strings, all of those strings are pushed
    #: on the stack and the current state will be the last element of the list.
    #: ``new_state`` can also be ``combined('state1', 'state2', ...)``
    #: to signify a new, anonymous state combined from the rules of two
    #: or more existing ones.
    #: Furthermore, it can be '#pop' to signify going back one step in
    #: the state stack, or '#push' to push the current state on the stack
    #: again. Note that if you push while in a combined state, the combined
    #: state itself is pushed, and not only the state in which the rule is
    #: defined.
    #:
    #: The tuple can also be replaced with ``include('state')``, in which
    #: case the rules from the state named by the string are included in the
    #: current one.
    tokens = {}

    def get_tokens_unprocessed(self, text, stack=('root',)):
        """
        Split ``text`` into (tokentype, text) pairs.

        ``stack`` is the initial stack (default: ``['root']``)
        """
        pos = 0
        tokendefs = self._tokens
        statestack = list(stack)
        statetokens = tokendefs[statestack[-1]]
        while 1:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, pos)
                if m:
                    if action is not None:
                        if type(action) is _TokenType:
                            yield pos, action, m.group()
                        else:
                            yield from action(self, m)
                    pos = m.end()
                    if new_state is not None:
                        # state transition
                        if isinstance(new_state, tuple):
                            for state in new_state:
                                if state == '#pop':
                                    if len(statestack) > 1:
                                        statestack.pop()
                                elif state == '#push':
                                    statestack.append(statestack[-1])
                                else:
                                    statestack.append(state)
                        elif isinstance(new_state, int):
                            # pop, but keep at least one state on the stack
                            # (random code leading to unexpected pops should
                            # not allow exceptions)
                            if abs(new_state) >= len(statestack):
                                del statestack[1:]
                            else:
                                del statestack[new_state:]
                        elif new_state == '#push':
                            statestack.append(statestack[-1])
                        else:
                            assert False, f"wrong state def: {new_state!r}"
                        statetokens = tokendefs[statestack[-1]]
                    break
            else:
                # We are here only if all state tokens have been considered
                # and there was not a match on any of them.
                try:
                    if text[pos] == '\n':
                        # at EOL, reset state to "root"
                        statestack = ['root']
                        statetokens = tokendefs['root']
                        yield pos, Whitespace, '\n'
                        pos += 1
                        continue
                    yield pos, Error, text[pos]
                    pos += 1
                except IndexError:
                    break


class LexerContext:
    """
    A helper object that holds lexer position data.
    """

    def __init__(self, text, pos, stack=None, end=None):
        self.text = text
        self.pos = pos
        self.end = end or len(text)  # end=0 not supported ;-)
        self.stack = stack or ['root']

    def __repr__(self):
        return f'LexerContext({self.text!r}, {self.pos!r}, {self.stack!r})'


class ExtendedRegexLexer(RegexLexer):
    """
    A RegexLexer that uses a context object to store its state.
    """

    def get_tokens_unprocessed(self, text=None, context=None):
        """
        Split ``text`` into (tokentype, text) pairs.
        If ``context`` is given, use this lexer context instead.
        """
        tokendefs = self._tokens
        if not context:
            ctx = LexerContext(text, 0)
            statetokens = tokendefs['root']
        else:
            ctx = context
            statetokens = tokendefs[ctx.stack[-1]]
            text = ctx.text
        while 1:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, ctx.pos, ctx.end)
                if m:
                    if action is not None:
                        if type(action) is _TokenType:
                            yield ctx.pos, action, m.group()
                            ctx.pos = m.end()
                        else:
                            yield from action(self, m, ctx)
                            if not new_state:
                                # altered the state stack?
                                statetokens = tokendefs[ctx.stack[-1]]
                    # CAUTION: callback must set ctx.pos!
                    if new_state is not None:
                        # state transition
                        if isinstance(new_state, tuple):
                            for state in new_state:
                                if state == '#pop':
                                    if len(ctx.stack) > 1:
                                        ctx.stack.pop()
                                elif state == '#push':
                                    ctx.stack.append(ctx.stack[-1])
                                else:
                                    ctx.stack.append(state)
                        elif isinstance(new_state, int):
                            # see RegexLexer for why this check is made
                            if abs(new_state) >= len(ctx.stack):
                                del ctx.stack[1:]
                            else:
                                del ctx.stack[new_state:]
                        elif new_state == '#push':
                            ctx.stack.append(ctx.stack[-1])
                        else:
                            assert False, f"wrong state def: {new_state!r}"
                        statetokens = tokendefs[ctx.stack[-1]]
                    break
            else:
                try:
                    if ctx.pos >= ctx.end:
                        break
                    if text[ctx.pos] == '\n':
                        # at EOL, reset state to "root"
                        ctx.stack = ['root']
                        statetokens = tokendefs['root']
                        yield ctx.pos, Text, '\n'
                        ctx.pos += 1
                        continue
                    yield ctx.pos, Error, text[ctx.pos]
                    ctx.pos += 1
                except IndexError:
                    break


def do_insertions(insertions, tokens):
    """
    Helper for lexers which must combine the results of several
    sublexers.

    ``insertions`` is a list of ``(index, itokens)`` pairs.
    Each ``itokens`` iterable should be inserted at position
    ``index`` into the token stream given by the ``tokens``
    argument.

    The result is a combined token stream.

    TODO: clean up the code here.
    """
    insertions = iter(insertions)
    try:
        index, itokens = next(insertions)
    except StopIteration:
        # no insertions
        yield from tokens
        return

    realpos = None
    insleft = True

    # iterate over the token stream where we want to insert
    # the tokens from the insertion list.
    for i, t, v in tokens:
        # first iteration. store the position of first item
        if realpos is None:
            realpos = i
        oldi = 0
        while insleft and i + len(v) >= index:
            tmpval = v[oldi:index - i]
            if tmpval:
                yield realpos, t, tmpval
                realpos += len(tmpval)
            for it_index, it_token, it_value in itokens:
                yield realpos, it_token, it_value
                realpos += len(it_value)
            oldi = index - i
            try:
                index, itokens = next(insertions)
            except StopIteration:
                insleft = False
                break  # not strictly necessary
        if oldi < len(v):
            yield realpos, t, v[oldi:]
            realpos += len(v) - oldi

    # leftover tokens
    while insleft:
        # no normal tokens, set realpos to zero
        realpos = realpos or 0
        for p, t, v in itokens:
            yield realpos, t, v
            realpos += len(v)
        try:
            index, itokens = next(insertions)
        except StopIteration:
            insleft = False
            break  # not strictly necessary


class ProfilingRegexLexerMeta(RegexLexerMeta):
    """Metaclass for ProfilingRegexLexer, collects regex timing info."""

    def _process_regex(cls, regex, rflags, state):
        if isinstance(regex, words):
            rex = regex_opt(regex.words, prefix=regex.prefix,
                            suffix=regex.suffix)
        else:
            rex = regex
        compiled = re.compile(rex, rflags)

        def match_func(text, pos, endpos=sys.maxsize):
            info = cls._prof_data[-1].setdefault((state, rex), [0, 0.0])
            t0 = time.time()
            res = compiled.match(text, pos, endpos)
            t1 = time.time()
            info[0] += 1
            info[1] += t1 - t0
            return res
        return match_func


class ProfilingRegexLexer(RegexLexer, metaclass=ProfilingRegexLexerMeta):
    """Drop-in replacement for RegexLexer that does profiling of its regexes."""

    _prof_data = []
    _prof_sort_index = 4  # defaults to time per call

    def get_tokens_unprocessed(self, text, stack=('root',)):
        # this needs to be a stack, since using(this) will produce nested calls
        self.__class__._prof_data.append({})
        yield from RegexLexer.get_tokens_unprocessed(self, text, stack)
        rawdata = self.__class__._prof_data.pop()
        data = sorted(((s, repr(r).strip('u\'').replace('\\\\', '\\')[:65],
                        n, 1000 * t, 1000 * t / n)
                       for ((s, r), (n, t)) in rawdata.items()),
                      key=lambda x: x[self._prof_sort_index],
                      reverse=True)
        sum_total = sum(x[3] for x in data)

        print()
        print('Profiling result for %s lexing %d chars in %.3f ms' %
              (self.__class__.__name__, len(text), sum_total))
        print('=' * 110)
        print('%-20s %-64s ncalls  tottime  percall' % ('state', 'regex'))
        print('-' * 110)
        for d in data:
            print('%-20s %-65s %5d %8.4f %8.4f' % d)
        print('=' * 110)

# === NexusCore/openenv\Lib\site-packages\tornado\test\websocket_test.py ===
import asyncio
import contextlib
import functools
import socket
import traceback
import typing
import unittest

from tornado.concurrent import Future
from tornado import gen
from tornado.httpclient import HTTPError, HTTPRequest
from tornado.locks import Event
from tornado.log import gen_log, app_log
from tornado.netutil import Resolver
from tornado.simple_httpclient import SimpleAsyncHTTPClient
from tornado.template import DictLoader
from tornado.test.util import abstract_base_test, ignore_deprecation
from tornado.testing import AsyncHTTPTestCase, gen_test, bind_unused_port, ExpectLog
from tornado.web import Application, RequestHandler

try:
    import tornado.websocket  # noqa: F401
    from tornado.util import _websocket_mask_python
except ImportError:
    # The unittest module presents misleading errors on ImportError
    # (it acts as if websocket_test could not be found, hiding the underlying
    # error).  If we get an ImportError here (which could happen due to
    # TORNADO_EXTENSION=1), print some extra information before failing.
    traceback.print_exc()
    raise

from tornado.websocket import (
    WebSocketHandler,
    websocket_connect,
    WebSocketError,
    WebSocketClosedError,
)

try:
    from tornado import speedups
except ImportError:
    speedups = None  # type: ignore


class TestWebSocketHandler(WebSocketHandler):
    """Base class for testing handlers that exposes the on_close event.

    This allows for tests to see the close code and reason on the
    server side.

    """

    def initialize(self, close_future=None, compression_options=None):
        self.close_future = close_future
        self.compression_options = compression_options

    def get_compression_options(self):
        return self.compression_options

    def on_close(self):
        if self.close_future is not None:
            self.close_future.set_result((self.close_code, self.close_reason))


class EchoHandler(TestWebSocketHandler):
    @gen.coroutine
    def on_message(self, message):
        try:
            yield self.write_message(message, isinstance(message, bytes))
        except asyncio.CancelledError:
            pass
        except WebSocketClosedError:
            pass


class ErrorInOnMessageHandler(TestWebSocketHandler):
    def on_message(self, message):
        1 / 0


class HeaderHandler(TestWebSocketHandler):
    def open(self):
        methods_to_test = [
            functools.partial(self.write, "This should not work"),
            functools.partial(self.redirect, "http://localhost/elsewhere"),
            functools.partial(self.set_header, "X-Test", ""),
            functools.partial(self.set_cookie, "Chocolate", "Chip"),
            functools.partial(self.set_status, 503),
            self.flush,
            self.finish,
        ]
        for method in methods_to_test:
            try:
                # In a websocket context, many RequestHandler methods
                # raise RuntimeErrors.
                method()  # type: ignore
                raise Exception("did not get expected exception")
            except RuntimeError:
                pass
        self.write_message(self.request.headers.get("X-Test", ""))


class HeaderEchoHandler(TestWebSocketHandler):
    def set_default_headers(self):
        self.set_header("X-Extra-Response-Header", "Extra-Response-Value")

    def prepare(self):
        for k, v in self.request.headers.get_all():
            if k.lower().startswith("x-test"):
                self.set_header(k, v)


class NonWebSocketHandler(RequestHandler):
    def get(self):
        self.write("ok")


class RedirectHandler(RequestHandler):
    def get(self):
        self.redirect("/echo")


class CloseReasonHandler(TestWebSocketHandler):
    def open(self):
        self.on_close_called = False
        self.close(1001, "goodbye")


class AsyncPrepareHandler(TestWebSocketHandler):
    @gen.coroutine
    def prepare(self):
        yield gen.moment

    def on_message(self, message):
        self.write_message(message)


class PathArgsHandler(TestWebSocketHandler):
    def open(self, arg):
        self.write_message(arg)


class CoroutineOnMessageHandler(TestWebSocketHandler):
    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.sleeping = 0

    @gen.coroutine
    def on_message(self, message):
        if self.sleeping > 0:
            self.write_message("another coroutine is already sleeping")
        self.sleeping += 1
        yield gen.sleep(0.01)
        self.sleeping -= 1
        self.write_message(message)


class RenderMessageHandler(TestWebSocketHandler):
    def on_message(self, message):
        self.write_message(self.render_string("message.html", message=message))


class SubprotocolHandler(TestWebSocketHandler):
    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.select_subprotocol_called = False

    def select_subprotocol(self, subprotocols):
        if self.select_subprotocol_called:
            raise Exception("select_subprotocol called twice")
        self.select_subprotocol_called = True
        if "goodproto" in subprotocols:
            return "goodproto"
        return None

    def open(self):
        if not self.select_subprotocol_called:
            raise Exception("select_subprotocol not called")
        self.write_message("subprotocol=%s" % self.selected_subprotocol)


class OpenCoroutineHandler(TestWebSocketHandler):
    def initialize(self, test, **kwargs):
        super().initialize(**kwargs)
        self.test = test
        self.open_finished = False

    @gen.coroutine
    def open(self):
        yield self.test.message_sent.wait()
        yield gen.sleep(0.010)
        self.open_finished = True

    def on_message(self, message):
        if not self.open_finished:
            raise Exception("on_message called before open finished")
        self.write_message("ok")


class ErrorInOpenHandler(TestWebSocketHandler):
    def open(self):
        raise Exception("boom")


class ErrorInAsyncOpenHandler(TestWebSocketHandler):
    async def open(self):
        await asyncio.sleep(0)
        raise Exception("boom")


class NoDelayHandler(TestWebSocketHandler):
    def open(self):
        self.set_nodelay(True)
        self.write_message("hello")


class WebSocketBaseTestCase(AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()
        self.conns_to_close = []

    def tearDown(self):
        for conn in self.conns_to_close:
            conn.close()
        super().tearDown()

    @gen.coroutine
    def ws_connect(self, path, **kwargs):
        ws = yield websocket_connect(
            "ws://127.0.0.1:%d%s" % (self.get_http_port(), path), **kwargs
        )
        self.conns_to_close.append(ws)
        raise gen.Return(ws)


class WebSocketTest(WebSocketBaseTestCase):
    def get_app(self):
        self.close_future = Future()  # type: Future[None]
        return Application(
            [
                ("/echo", EchoHandler, dict(close_future=self.close_future)),
                ("/non_ws", NonWebSocketHandler),
                ("/redirect", RedirectHandler),
                ("/header", HeaderHandler, dict(close_future=self.close_future)),
                (
                    "/header_echo",
                    HeaderEchoHandler,
                    dict(close_future=self.close_future),
                ),
                (
                    "/close_reason",
                    CloseReasonHandler,
                    dict(close_future=self.close_future),
                ),
                (
                    "/error_in_on_message",
                    ErrorInOnMessageHandler,
                    dict(close_future=self.close_future),
                ),
                (
                    "/async_prepare",
                    AsyncPrepareHandler,
                    dict(close_future=self.close_future),
                ),
                (
                    "/path_args/(.*)",
                    PathArgsHandler,
                    dict(close_future=self.close_future),
                ),
                (
                    "/coroutine",
                    CoroutineOnMessageHandler,
                    dict(close_future=self.close_future),
                ),
                ("/render", RenderMessageHandler, dict(close_future=self.close_future)),
                (
                    "/subprotocol",
                    SubprotocolHandler,
                    dict(close_future=self.close_future),
                ),
                (
                    "/open_coroutine",
                    OpenCoroutineHandler,
                    dict(close_future=self.close_future, test=self),
                ),
                ("/error_in_open", ErrorInOpenHandler),
                ("/error_in_async_open", ErrorInAsyncOpenHandler),
                ("/nodelay", NoDelayHandler),
            ],
            template_loader=DictLoader({"message.html": "<b>{{ message }}</b>"}),
        )

    def get_http_client(self):
        # These tests require HTTP/1; force the use of SimpleAsyncHTTPClient.
        return SimpleAsyncHTTPClient()

    def tearDown(self):
        super().tearDown()
        RequestHandler._template_loaders.clear()

    def test_http_request(self):
        # WS server, HTTP client.
        response = self.fetch("/echo")
        self.assertEqual(response.code, 400)

    def test_missing_websocket_key(self):
        response = self.fetch(
            "/echo",
            headers={
                "Connection": "Upgrade",
                "Upgrade": "WebSocket",
                "Sec-WebSocket-Version": "13",
            },
        )
        self.assertEqual(response.code, 400)

    def test_bad_websocket_version(self):
        response = self.fetch(
            "/echo",
            headers={
                "Connection": "Upgrade",
                "Upgrade": "WebSocket",
                "Sec-WebSocket-Version": "12",
            },
        )
        self.assertEqual(response.code, 426)

    @gen_test
    def test_websocket_gen(self):
        ws = yield self.ws_connect("/echo")
        yield ws.write_message("hello")
        response = yield ws.read_message()
        self.assertEqual(response, "hello")

    def test_websocket_callbacks(self):
        with ignore_deprecation():
            websocket_connect(
                "ws://127.0.0.1:%d/echo" % self.get_http_port(), callback=self.stop
            )
        ws = self.wait().result()
        ws.write_message("hello")
        ws.read_message(self.stop)
        response = self.wait().result()
        self.assertEqual(response, "hello")
        self.close_future.add_done_callback(lambda f: self.stop())
        ws.close()
        self.wait()

    @gen_test
    def test_binary_message(self):
        ws = yield self.ws_connect("/echo")
        ws.write_message(b"hello \xe9", binary=True)
        response = yield ws.read_message()
        self.assertEqual(response, b"hello \xe9")

    @gen_test
    def test_unicode_message(self):
        ws = yield self.ws_connect("/echo")
        ws.write_message("hello \u00e9")
        response = yield ws.read_message()
        self.assertEqual(response, "hello \u00e9")

    @gen_test
    def test_error_in_closed_client_write_message(self):
        ws = yield self.ws_connect("/echo")
        ws.close()
        with self.assertRaises(WebSocketClosedError):
            ws.write_message("hello \u00e9")

    @gen_test
    def test_render_message(self):
        ws = yield self.ws_connect("/render")
        ws.write_message("hello")
        response = yield ws.read_message()
        self.assertEqual(response, "<b>hello</b>")

    @gen_test
    def test_error_in_on_message(self):
        ws = yield self.ws_connect("/error_in_on_message")
        ws.write_message("hello")
        with ExpectLog(app_log, "Uncaught exception"):
            response = yield ws.read_message()
        self.assertIsNone(response)

    @gen_test
    def test_websocket_http_fail(self):
        with self.assertRaises(HTTPError) as cm:
            yield self.ws_connect("/notfound")
        self.assertEqual(cm.exception.code, 404)

    @gen_test
    def test_websocket_http_success(self):
        with self.assertRaises(WebSocketError):
            yield self.ws_connect("/non_ws")

    @gen_test
    def test_websocket_http_redirect(self):
        with self.assertRaises(HTTPError):
            yield self.ws_connect("/redirect")

    @gen_test
    def test_websocket_network_fail(self):
        sock, port = bind_unused_port()
        sock.close()
        with self.assertRaises(IOError):
            with ExpectLog(gen_log, ".*", required=False):
                yield websocket_connect(
                    "ws://127.0.0.1:%d/" % port, connect_timeout=3600
                )

    @gen_test
    def test_websocket_close_buffered_data(self):
        with contextlib.closing(
            (yield websocket_connect("ws://127.0.0.1:%d/echo" % self.get_http_port()))
        ) as ws:
            ws.write_message("hello")
            ws.write_message("world")
            # Close the underlying stream.
            ws.stream.close()

    @gen_test
    def test_websocket_headers(self):
        # Ensure that arbitrary headers can be passed through websocket_connect.
        with contextlib.closing(
            (
                yield websocket_connect(
                    HTTPRequest(
                        "ws://127.0.0.1:%d/header" % self.get_http_port(),
                        headers={"X-Test": "hello"},
                    )
                )
            )
        ) as ws:
            response = yield ws.read_message()
            self.assertEqual(response, "hello")

    @gen_test
    def test_websocket_header_echo(self):
        # Ensure that headers can be returned in the response.
        # Specifically, that arbitrary headers passed through websocket_connect
        # can be returned.
        with contextlib.closing(
            (
                yield websocket_connect(
                    HTTPRequest(
                        "ws://127.0.0.1:%d/header_echo" % self.get_http_port(),
                        headers={"X-Test-Hello": "hello"},
                    )
                )
            )
        ) as ws:
            self.assertEqual(ws.headers.get("X-Test-Hello"), "hello")
            self.assertEqual(
                ws.headers.get("X-Extra-Response-Header"), "Extra-Response-Value"
            )

    @gen_test
    def test_server_close_reason(self):
        ws = yield self.ws_connect("/close_reason")
        msg = yield ws.read_message()
        # A message of None means the other side closed the connection.
        self.assertIs(msg, None)
        self.assertEqual(ws.close_code, 1001)
        self.assertEqual(ws.close_reason, "goodbye")
        # The on_close callback is called no matter which side closed.
        code, reason = yield self.close_future
        # The client echoed the close code it received to the server,
        # so the server's close code (returned via close_future) is
        # the same.
        self.assertEqual(code, 1001)

    @gen_test
    def test_client_close_reason(self):
        ws = yield self.ws_connect("/echo")
        ws.close(1001, "goodbye")
        code, reason = yield self.close_future
        self.assertEqual(code, 1001)
        self.assertEqual(reason, "goodbye")

    @gen_test
    def test_write_after_close(self):
        ws = yield self.ws_connect("/close_reason")
        msg = yield ws.read_message()
        self.assertIs(msg, None)
        with self.assertRaises(WebSocketClosedError):
            ws.write_message("hello")

    @gen_test
    def test_async_prepare(self):
        # Previously, an async prepare method triggered a bug that would
        # result in a timeout on test shutdown (and a memory leak).
        ws = yield self.ws_connect("/async_prepare")
        ws.write_message("hello")
        res = yield ws.read_message()
        self.assertEqual(res, "hello")

    @gen_test
    def test_path_args(self):
        ws = yield self.ws_connect("/path_args/hello")
        res = yield ws.read_message()
        self.assertEqual(res, "hello")

    @gen_test
    def test_coroutine(self):
        ws = yield self.ws_connect("/coroutine")
        # Send both messages immediately, coroutine must process one at a time.
        yield ws.write_message("hello1")
        yield ws.write_message("hello2")
        res = yield ws.read_message()
        self.assertEqual(res, "hello1")
        res = yield ws.read_message()
        self.assertEqual(res, "hello2")

    @gen_test
    def test_check_origin_valid_no_path(self):
        port = self.get_http_port()

        url = "ws://127.0.0.1:%d/echo" % port
        headers = {"Origin": "http://127.0.0.1:%d" % port}

        with contextlib.closing(
            (yield websocket_connect(HTTPRequest(url, headers=headers)))
        ) as ws:
            ws.write_message("hello")
            response = yield ws.read_message()
            self.assertEqual(response, "hello")

    @gen_test
    def test_check_origin_valid_with_path(self):
        port = self.get_http_port()

        url = "ws://127.0.0.1:%d/echo" % port
        headers = {"Origin": "http://127.0.0.1:%d/something" % port}

        with contextlib.closing(
            (yield websocket_connect(HTTPRequest(url, headers=headers)))
        ) as ws:
            ws.write_message("hello")
            response = yield ws.read_message()
            self.assertEqual(response, "hello")

    @gen_test
    def test_check_origin_invalid_partial_url(self):
        port = self.get_http_port()

        url = "ws://127.0.0.1:%d/echo" % port
        headers = {"Origin": "127.0.0.1:%d" % port}

        with self.assertRaises(HTTPError) as cm:
            yield websocket_connect(HTTPRequest(url, headers=headers))
        self.assertEqual(cm.exception.code, 403)

    @gen_test
    def test_check_origin_invalid(self):
        port = self.get_http_port()

        url = "ws://127.0.0.1:%d/echo" % port
        # Host is 127.0.0.1, which should not be accessible from some other
        # domain
        headers = {"Origin": "http://somewhereelse.com"}

        with self.assertRaises(HTTPError) as cm:
            yield websocket_connect(HTTPRequest(url, headers=headers))

        self.assertEqual(cm.exception.code, 403)

    @gen_test
    def test_check_origin_invalid_subdomains(self):
        port = self.get_http_port()

        # CaresResolver may return ipv6-only results for localhost, but our
        # server is only running on ipv4. Test for this edge case and skip
        # the test if it happens.
        addrinfo = yield Resolver().resolve("localhost", port)
        families = {addr[0] for addr in addrinfo}
        if socket.AF_INET not in families:
            self.skipTest("localhost does not resolve to ipv4")
            return

        url = "ws://localhost:%d/echo" % port
        # Subdomains should be disallowed by default.  If we could pass a
        # resolver to websocket_connect we could test sibling domains as well.
        headers = {"Origin": "http://subtenant.localhost"}

        with self.assertRaises(HTTPError) as cm:
            yield websocket_connect(HTTPRequest(url, headers=headers))

        self.assertEqual(cm.exception.code, 403)

    @gen_test
    def test_subprotocols(self):
        ws = yield self.ws_connect(
            "/subprotocol", subprotocols=["badproto", "goodproto"]
        )
        self.assertEqual(ws.selected_subprotocol, "goodproto")
        res = yield ws.read_message()
        self.assertEqual(res, "subprotocol=goodproto")

    @gen_test
    def test_subprotocols_not_offered(self):
        ws = yield self.ws_connect("/subprotocol")
        self.assertIs(ws.selected_subprotocol, None)
        res = yield ws.read_message()
        self.assertEqual(res, "subprotocol=None")

    @gen_test
    def test_open_coroutine(self):
        self.message_sent = Event()
        ws = yield self.ws_connect("/open_coroutine")
        yield ws.write_message("hello")
        self.message_sent.set()
        res = yield ws.read_message()
        self.assertEqual(res, "ok")

    @gen_test
    def test_error_in_open(self):
        with ExpectLog(app_log, "Uncaught exception"):
            ws = yield self.ws_connect("/error_in_open")
            res = yield ws.read_message()
        self.assertIsNone(res)

    @gen_test
    def test_error_in_async_open(self):
        with ExpectLog(app_log, "Uncaught exception"):
            ws = yield self.ws_connect("/error_in_async_open")
            res = yield ws.read_message()
        self.assertIsNone(res)

    @gen_test
    def test_nodelay(self):
        ws = yield self.ws_connect("/nodelay")
        res = yield ws.read_message()
        self.assertEqual(res, "hello")


class NativeCoroutineOnMessageHandler(TestWebSocketHandler):
    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self.sleeping = 0

    async def on_message(self, message):
        if self.sleeping > 0:
            self.write_message("another coroutine is already sleeping")
        self.sleeping += 1
        await gen.sleep(0.01)
        self.sleeping -= 1
        self.write_message(message)


class WebSocketNativeCoroutineTest(WebSocketBaseTestCase):
    def get_app(self):
        return Application([("/native", NativeCoroutineOnMessageHandler)])

    @gen_test
    def test_native_coroutine(self):
        ws = yield self.ws_connect("/native")
        # Send both messages immediately, coroutine must process one at a time.
        yield ws.write_message("hello1")
        yield ws.write_message("hello2")
        res = yield ws.read_message()
        self.assertEqual(res, "hello1")
        res = yield ws.read_message()
        self.assertEqual(res, "hello2")


@abstract_base_test
class CompressionTestMixin(WebSocketBaseTestCase):
    MESSAGE = "Hello world. Testing 123 123"

    def get_app(self):
        class LimitedHandler(TestWebSocketHandler):
            @property
            def max_message_size(self):
                return 1024

            def on_message(self, message):
                self.write_message(str(len(message)))

        return Application(
            [
                (
                    "/echo",
                    EchoHandler,
                    dict(compression_options=self.get_server_compression_options()),
                ),
                (
                    "/limited",
                    LimitedHandler,
                    dict(compression_options=self.get_server_compression_options()),
                ),
            ]
        )

    def get_server_compression_options(self):
        return None

    def get_client_compression_options(self):
        return None

    def verify_wire_bytes(self, bytes_in: int, bytes_out: int) -> None:
        raise NotImplementedError()

    @gen_test
    def test_message_sizes(self):
        ws = yield self.ws_connect(
            "/echo", compression_options=self.get_client_compression_options()
        )
        # Send the same message three times so we can measure the
        # effect of the context_takeover options.
        for i in range(3):
            ws.write_message(self.MESSAGE)
            response = yield ws.read_message()
            self.assertEqual(response, self.MESSAGE)
        self.assertEqual(ws.protocol._message_bytes_out, len(self.MESSAGE) * 3)
        self.assertEqual(ws.protocol._message_bytes_in, len(self.MESSAGE) * 3)
        self.verify_wire_bytes(ws.protocol._wire_bytes_in, ws.protocol._wire_bytes_out)

    @gen_test
    def test_size_limit(self):
        ws = yield self.ws_connect(
            "/limited", compression_options=self.get_client_compression_options()
        )
        # Small messages pass through.
        ws.write_message("a" * 128)
        response = yield ws.read_message()
        self.assertEqual(response, "128")
        # This message is too big after decompression, but it compresses
        # down to a size that will pass the initial checks.
        ws.write_message("a" * 2048)
        response = yield ws.read_message()
        self.assertIsNone(response)


@abstract_base_test
class UncompressedTestMixin(CompressionTestMixin):
    """Specialization of CompressionTestMixin when we expect no compression."""

    def verify_wire_bytes(self, bytes_in, bytes_out):
        # Bytes out includes the 4-byte mask key per message.
        self.assertEqual(bytes_out, 3 * (len(self.MESSAGE) + 6))
        self.assertEqual(bytes_in, 3 * (len(self.MESSAGE) + 2))


class NoCompressionTest(UncompressedTestMixin):
    pass


# If only one side tries to compress, the extension is not negotiated.
class ServerOnlyCompressionTest(UncompressedTestMixin):
    def get_server_compression_options(self):
        return {}


class ClientOnlyCompressionTest(UncompressedTestMixin):
    def get_client_compression_options(self):
        return {}


class DefaultCompressionTest(CompressionTestMixin):
    def get_server_compression_options(self):
        return {}

    def get_client_compression_options(self):
        return {}

    def verify_wire_bytes(self, bytes_in, bytes_out):
        self.assertLess(bytes_out, 3 * (len(self.MESSAGE) + 6))
        self.assertLess(bytes_in, 3 * (len(self.MESSAGE) + 2))
        # Bytes out includes the 4 bytes mask key per message.
        self.assertEqual(bytes_out, bytes_in + 12)


@abstract_base_test
class MaskFunctionMixin(unittest.TestCase):
    # Subclasses should define self.mask(mask, data)
    def mask(self, mask: bytes, data: bytes) -> bytes:
        raise NotImplementedError()

    def test_mask(self: typing.Any):
        self.assertEqual(self.mask(b"abcd", b""), b"")
        self.assertEqual(self.mask(b"abcd", b"b"), b"\x03")
        self.assertEqual(self.mask(b"abcd", b"54321"), b"TVPVP")
        self.assertEqual(self.mask(b"ZXCV", b"98765432"), b"c`t`olpd")
        # Include test cases with \x00 bytes (to ensure that the C
        # extension isn't depending on null-terminated strings) and
        # bytes with the high bit set (to smoke out signedness issues).
        self.assertEqual(
            self.mask(b"\x00\x01\x02\x03", b"\xff\xfb\xfd\xfc\xfe\xfa"),
            b"\xff\xfa\xff\xff\xfe\xfb",
        )
        self.assertEqual(
            self.mask(b"\xff\xfb\xfd\xfc", b"\x00\x01\x02\x03\x04\x05"),
            b"\xff\xfa\xff\xff\xfb\xfe",
        )


class PythonMaskFunctionTest(MaskFunctionMixin):
    def mask(self, mask, data):
        return _websocket_mask_python(mask, data)


@unittest.skipIf(speedups is None, "tornado.speedups module not present")
class CythonMaskFunctionTest(MaskFunctionMixin):
    def mask(self, mask, data):
        return speedups.websocket_mask(mask, data)


class ServerPeriodicPingTest(WebSocketBaseTestCase):
    def get_app(self):
        class PingHandler(TestWebSocketHandler):
            def on_pong(self, data):
                self.write_message("got pong")

        return Application(
            [("/", PingHandler)],
            websocket_ping_interval=0.01,
            websocket_ping_timeout=0,
        )

    @gen_test
    def test_server_ping(self):
        ws = yield self.ws_connect("/")
        for i in range(3):
            response = yield ws.read_message()
            self.assertEqual(response, "got pong")
        # TODO: test that the connection gets closed if ping responses stop.


class ClientPeriodicPingTest(WebSocketBaseTestCase):
    def get_app(self):
        class PingHandler(TestWebSocketHandler):
            def on_ping(self, data):
                self.write_message("got ping")

        return Application([("/", PingHandler)])

    @gen_test
    def test_client_ping(self):
        ws = yield self.ws_connect("/", ping_interval=0.01, ping_timeout=0)
        for i in range(3):
            response = yield ws.read_message()
            self.assertEqual(response, "got ping")
        ws.close()


class ServerPingTimeoutTest(WebSocketBaseTestCase):
    def get_app(self):
        self.handlers: list[WebSocketHandler] = []
        test = self

        class PingHandler(TestWebSocketHandler):
            def initialize(self, close_future=None, compression_options=None):
                self.handlers = test.handlers
                # capture the handler instance so we can interrogate it later
                self.handlers.append(self)
                return super().initialize(
                    close_future=close_future, compression_options=compression_options
                )

        app = Application([("/", PingHandler)])
        return app

    @staticmethod
    def suppress_pong(ws):
        """Suppress the client's "pong" response."""

        def wrapper(fcn):
            def _inner(oppcode: int, data: bytes):
                if oppcode == 0xA:  # NOTE: 0x9=ping, 0xA=pong
                    # prevent pong responses
                    return
                # leave all other responses unchanged
                return fcn(oppcode, data)

            return _inner

        ws.protocol._handle_message = wrapper(ws.protocol._handle_message)

    @gen_test
    def test_client_ping_timeout(self):
        # websocket client
        interval = 0.2
        ws = yield self.ws_connect(
            "/", ping_interval=interval, ping_timeout=interval / 4
        )

        # websocket handler (server side)
        handler = self.handlers[0]

        for _ in range(5):
            # wait for the ping period
            yield gen.sleep(0.2)

            # connection should still be open from the server end
            self.assertIsNone(handler.close_code)
            self.assertIsNone(handler.close_reason)

            # connection should still be open from the client end
            assert ws.protocol.close_code is None

        # suppress the pong response message
        self.suppress_pong(ws)

        # give the server time to register this
        yield gen.sleep(interval * 1.5)

        # connection should be closed from the server side
        self.assertEqual(handler.close_code, 1000)
        self.assertEqual(handler.close_reason, "ping timed out")

        # client should have received a close operation
        self.assertEqual(ws.protocol.close_code, 1000)


class ManualPingTest(WebSocketBaseTestCase):
    def get_app(self):
        class PingHandler(TestWebSocketHandler):
            def on_ping(self, data):
                self.write_message(data, binary=isinstance(data, bytes))

        return Application([("/", PingHandler)])

    @gen_test
    def test_manual_ping(self):
        ws = yield self.ws_connect("/")

        self.assertRaises(ValueError, ws.ping, "a" * 126)

        ws.ping("hello")
        resp = yield ws.read_message()
        # on_ping always sees bytes.
        self.assertEqual(resp, b"hello")

        ws.ping(b"binary hello")
        resp = yield ws.read_message()
        self.assertEqual(resp, b"binary hello")


class MaxMessageSizeTest(WebSocketBaseTestCase):
    def get_app(self):
        return Application([("/", EchoHandler)], websocket_max_message_size=1024)

    @gen_test
    def test_large_message(self):
        ws = yield self.ws_connect("/")

        # Write a message that is allowed.
        msg = "a" * 1024
        ws.write_message(msg)
        resp = yield ws.read_message()
        self.assertEqual(resp, msg)

        # Write a message that is too large.
        ws.write_message(msg + "b")
        resp = yield ws.read_message()
        # A message of None means the other side closed the connection.
        self.assertIs(resp, None)
        self.assertEqual(ws.close_code, 1009)
        self.assertEqual(ws.close_reason, "message too big")
        # TODO: Needs tests of messages split over multiple
        # continuation frames.

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\_extras\_google_auth.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from typing_extensions import ClassVar, override

from ._common import MissingDependencyError
from ..._utils import LazyProxy

if TYPE_CHECKING:
    import google.auth  # type: ignore

    google_auth = google.auth


class GoogleAuthProxy(LazyProxy[Any]):
    should_cache: ClassVar[bool] = True

    @override
    def __load__(self) -> Any:
        try:
            import google.auth  # type: ignore
        except ImportError as err:
            raise MissingDependencyError(extra="vertex", library="google-auth") from err

        return google.auth


if not TYPE_CHECKING:
    google_auth = GoogleAuthProxy()

# === NexusCore/openenv\Lib\site-packages\aiohttp\helpers.py ===
"""Various helper functions"""

import asyncio
import base64
import binascii
import contextlib
import datetime
import enum
import functools
import inspect
import netrc
import os
import platform
import re
import sys
import time
import weakref
from collections import namedtuple
from contextlib import suppress
from email.parser import HeaderParser
from email.utils import parsedate
from math import ceil
from pathlib import Path
from types import MappingProxyType, TracebackType
from typing import (
    Any,
    Callable,
    ContextManager,
    Dict,
    Generator,
    Generic,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    overload,
)
from urllib.parse import quote
from urllib.request import getproxies, proxy_bypass

import attr
from multidict import MultiDict, MultiDictProxy, MultiMapping
from propcache.api import under_cached_property as reify
from yarl import URL

from . import hdrs
from .log import client_logger

if sys.version_info >= (3, 11):
    import asyncio as async_timeout
else:
    import async_timeout

__all__ = ("BasicAuth", "ChainMapProxy", "ETag", "reify")

IS_MACOS = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

PY_310 = sys.version_info >= (3, 10)
PY_311 = sys.version_info >= (3, 11)


_T = TypeVar("_T")
_S = TypeVar("_S")

_SENTINEL = enum.Enum("_SENTINEL", "sentinel")
sentinel = _SENTINEL.sentinel

NO_EXTENSIONS = bool(os.environ.get("AIOHTTP_NO_EXTENSIONS"))

# https://datatracker.ietf.org/doc/html/rfc9112#section-6.3-2.1
EMPTY_BODY_STATUS_CODES = frozenset((204, 304, *range(100, 200)))
# https://datatracker.ietf.org/doc/html/rfc9112#section-6.3-2.1
# https://datatracker.ietf.org/doc/html/rfc9112#section-6.3-2.2
EMPTY_BODY_METHODS = hdrs.METH_HEAD_ALL

DEBUG = sys.flags.dev_mode or (
    not sys.flags.ignore_environment and bool(os.environ.get("PYTHONASYNCIODEBUG"))
)


CHAR = {chr(i) for i in range(0, 128)}
CTL = {chr(i) for i in range(0, 32)} | {
    chr(127),
}
SEPARATORS = {
    "(",
    ")",
    "<",
    ">",
    "@",
    ",",
    ";",
    ":",
    "\\",
    '"',
    "/",
    "[",
    "]",
    "?",
    "=",
    "{",
    "}",
    " ",
    chr(9),
}
TOKEN = CHAR ^ CTL ^ SEPARATORS


class noop:
    def __await__(self) -> Generator[None, None, None]:
        yield


class BasicAuth(namedtuple("BasicAuth", ["login", "password", "encoding"])):
    """Http basic authentication helper."""

    def __new__(
        cls, login: str, password: str = "", encoding: str = "latin1"
    ) -> "BasicAuth":
        if login is None:
            raise ValueError("None is not allowed as login value")

        if password is None:
            raise ValueError("None is not allowed as password value")

        if ":" in login:
            raise ValueError('A ":" is not allowed in login (RFC 1945#section-11.1)')

        return super().__new__(cls, login, password, encoding)

    @classmethod
    def decode(cls, auth_header: str, encoding: str = "latin1") -> "BasicAuth":
        """Create a BasicAuth object from an Authorization HTTP header."""
        try:
            auth_type, encoded_credentials = auth_header.split(" ", 1)
        except ValueError:
            raise ValueError("Could not parse authorization header.")

        if auth_type.lower() != "basic":
            raise ValueError("Unknown authorization method %s" % auth_type)

        try:
            decoded = base64.b64decode(
                encoded_credentials.encode("ascii"), validate=True
            ).decode(encoding)
        except binascii.Error:
            raise ValueError("Invalid base64 encoding.")

        try:
            # RFC 2617 HTTP Authentication
            # https://www.ietf.org/rfc/rfc2617.txt
            # the colon must be present, but the username and password may be
            # otherwise blank.
            username, password = decoded.split(":", 1)
        except ValueError:
            raise ValueError("Invalid credentials.")

        return cls(username, password, encoding=encoding)

    @classmethod
    def from_url(cls, url: URL, *, encoding: str = "latin1") -> Optional["BasicAuth"]:
        """Create BasicAuth from url."""
        if not isinstance(url, URL):
            raise TypeError("url should be yarl.URL instance")
        # Check raw_user and raw_password first as yarl is likely
        # to already have these values parsed from the netloc in the cache.
        if url.raw_user is None and url.raw_password is None:
            return None
        return cls(url.user or "", url.password or "", encoding=encoding)

    def encode(self) -> str:
        """Encode credentials."""
        creds = (f"{self.login}:{self.password}").encode(self.encoding)
        return "Basic %s" % base64.b64encode(creds).decode(self.encoding)


def strip_auth_from_url(url: URL) -> Tuple[URL, Optional[BasicAuth]]:
    """Remove user and password from URL if present and return BasicAuth object."""
    # Check raw_user and raw_password first as yarl is likely
    # to already have these values parsed from the netloc in the cache.
    if url.raw_user is None and url.raw_password is None:
        return url, None
    return url.with_user(None), BasicAuth(url.user or "", url.password or "")


def netrc_from_env() -> Optional[netrc.netrc]:
    """Load netrc from file.

    Attempt to load it from the path specified by the env-var
    NETRC or in the default location in the user's home directory.

    Returns None if it couldn't be found or fails to parse.
    """
    netrc_env = os.environ.get("NETRC")

    if netrc_env is not None:
        netrc_path = Path(netrc_env)
    else:
        try:
            home_dir = Path.home()
        except RuntimeError as e:  # pragma: no cover
            # if pathlib can't resolve home, it may raise a RuntimeError
            client_logger.debug(
                "Could not resolve home directory when "
                "trying to look for .netrc file: %s",
                e,
            )
            return None

        netrc_path = home_dir / ("_netrc" if IS_WINDOWS else ".netrc")

    try:
        return netrc.netrc(str(netrc_path))
    except netrc.NetrcParseError as e:
        client_logger.warning("Could not parse .netrc file: %s", e)
    except OSError as e:
        netrc_exists = False
        with contextlib.suppress(OSError):
            netrc_exists = netrc_path.is_file()
        # we couldn't read the file (doesn't exist, permissions, etc.)
        if netrc_env or netrc_exists:
            # only warn if the environment wanted us to load it,
            # or it appears like the default file does actually exist
            client_logger.warning("Could not read .netrc file: %s", e)

    return None


@attr.s(auto_attribs=True, frozen=True, slots=True)
class ProxyInfo:
    proxy: URL
    proxy_auth: Optional[BasicAuth]


def basicauth_from_netrc(netrc_obj: Optional[netrc.netrc], host: str) -> BasicAuth:
    """
    Return :py:class:`~aiohttp.BasicAuth` credentials for ``host`` from ``netrc_obj``.

    :raises LookupError: if ``netrc_obj`` is :py:data:`None` or if no
            entry is found for the ``host``.
    """
    if netrc_obj is None:
        raise LookupError("No .netrc file found")
    auth_from_netrc = netrc_obj.authenticators(host)

    if auth_from_netrc is None:
        raise LookupError(f"No entry for {host!s} found in the `.netrc` file.")
    login, account, password = auth_from_netrc

    # TODO(PY311): username = login or account
    # Up to python 3.10, account could be None if not specified,
    # and login will be empty string if not specified. From 3.11,
    # login and account will be empty string if not specified.
    username = login if (login or account is None) else account

    # TODO(PY311): Remove this, as password will be empty string
    # if not specified
    if password is None:
        password = ""

    return BasicAuth(username, password)


def proxies_from_env() -> Dict[str, ProxyInfo]:
    proxy_urls = {
        k: URL(v)
        for k, v in getproxies().items()
        if k in ("http", "https", "ws", "wss")
    }
    netrc_obj = netrc_from_env()
    stripped = {k: strip_auth_from_url(v) for k, v in proxy_urls.items()}
    ret = {}
    for proto, val in stripped.items():
        proxy, auth = val
        if proxy.scheme in ("https", "wss"):
            client_logger.warning(
                "%s proxies %s are not supported, ignoring", proxy.scheme.upper(), proxy
            )
            continue
        if netrc_obj and auth is None:
            if proxy.host is not None:
                try:
                    auth = basicauth_from_netrc(netrc_obj, proxy.host)
                except LookupError:
                    auth = None
        ret[proto] = ProxyInfo(proxy, auth)
    return ret


def get_env_proxy_for_url(url: URL) -> Tuple[URL, Optional[BasicAuth]]:
    """Get a permitted proxy for the given URL from the env."""
    if url.host is not None and proxy_bypass(url.host):
        raise LookupError(f"Proxying is disallowed for `{url.host!r}`")

    proxies_in_env = proxies_from_env()
    try:
        proxy_info = proxies_in_env[url.scheme]
    except KeyError:
        raise LookupError(f"No proxies found for `{url!s}` in the env")
    else:
        return proxy_info.proxy, proxy_info.proxy_auth


@attr.s(auto_attribs=True, frozen=True, slots=True)
class MimeType:
    type: str
    subtype: str
    suffix: str
    parameters: "MultiDictProxy[str]"


@functools.lru_cache(maxsize=56)
def parse_mimetype(mimetype: str) -> MimeType:
    """Parses a MIME type into its components.

    mimetype is a MIME type string.

    Returns a MimeType object.

    Example:

    >>> parse_mimetype('text/html; charset=utf-8')
    MimeType(type='text', subtype='html', suffix='',
             parameters={'charset': 'utf-8'})

    """
    if not mimetype:
        return MimeType(
            type="", subtype="", suffix="", parameters=MultiDictProxy(MultiDict())
        )

    parts = mimetype.split(";")
    params: MultiDict[str] = MultiDict()
    for item in parts[1:]:
        if not item:
            continue
        key, _, value = item.partition("=")
        params.add(key.lower().strip(), value.strip(' "'))

    fulltype = parts[0].strip().lower()
    if fulltype == "*":
        fulltype = "*/*"

    mtype, _, stype = fulltype.partition("/")
    stype, _, suffix = stype.partition("+")

    return MimeType(
        type=mtype, subtype=stype, suffix=suffix, parameters=MultiDictProxy(params)
    )


@functools.lru_cache(maxsize=56)
def parse_content_type(raw: str) -> Tuple[str, MappingProxyType[str, str]]:
    """Parse Content-Type header.

    Returns a tuple of the parsed content type and a
    MappingProxyType of parameters.
    """
    msg = HeaderParser().parsestr(f"Content-Type: {raw}")
    content_type = msg.get_content_type()
    params = msg.get_params(())
    content_dict = dict(params[1:])  # First element is content type again
    return content_type, MappingProxyType(content_dict)


def guess_filename(obj: Any, default: Optional[str] = None) -> Optional[str]:
    name = getattr(obj, "name", None)
    if name and isinstance(name, str) and name[0] != "<" and name[-1] != ">":
        return Path(name).name
    return default


not_qtext_re = re.compile(r"[^\041\043-\133\135-\176]")
QCONTENT = {chr(i) for i in range(0x20, 0x7F)} | {"\t"}


def quoted_string(content: str) -> str:
    """Return 7-bit content as quoted-string.

    Format content into a quoted-string as defined in RFC5322 for
    Internet Message Format. Notice that this is not the 8-bit HTTP
    format, but the 7-bit email format. Content must be in usascii or
    a ValueError is raised.
    """
    if not (QCONTENT > set(content)):
        raise ValueError(f"bad content for quoted-string {content!r}")
    return not_qtext_re.sub(lambda x: "\\" + x.group(0), content)


def content_disposition_header(
    disptype: str, quote_fields: bool = True, _charset: str = "utf-8", **params: str
) -> str:
    """Sets ``Content-Disposition`` header for MIME.

    This is the MIME payload Content-Disposition header from RFC 2183
    and RFC 7579 section 4.2, not the HTTP Content-Disposition from
    RFC 6266.

    disptype is a disposition type: inline, attachment, form-data.
    Should be valid extension token (see RFC 2183)

    quote_fields performs value quoting to 7-bit MIME headers
    according to RFC 7578. Set to quote_fields to False if recipient
    can take 8-bit file names and field values.

    _charset specifies the charset to use when quote_fields is True.

    params is a dict with disposition params.
    """
    if not disptype or not (TOKEN > set(disptype)):
        raise ValueError(f"bad content disposition type {disptype!r}")

    value = disptype
    if params:
        lparams = []
        for key, val in params.items():
            if not key or not (TOKEN > set(key)):
                raise ValueError(f"bad content disposition parameter {key!r}={val!r}")
            if quote_fields:
                if key.lower() == "filename":
                    qval = quote(val, "", encoding=_charset)
                    lparams.append((key, '"%s"' % qval))
                else:
                    try:
                        qval = quoted_string(val)
                    except ValueError:
                        qval = "".join(
                            (_charset, "''", quote(val, "", encoding=_charset))
                        )
                        lparams.append((key + "*", qval))
                    else:
                        lparams.append((key, '"%s"' % qval))
            else:
                qval = val.replace("\\", "\\\\").replace('"', '\\"')
                lparams.append((key, '"%s"' % qval))
        sparams = "; ".join("=".join(pair) for pair in lparams)
        value = "; ".join((value, sparams))
    return value


def is_ip_address(host: Optional[str]) -> bool:
    """Check if host looks like an IP Address.

    This check is only meant as a heuristic to ensure that
    a host is not a domain name.
    """
    if not host:
        return False
    # For a host to be an ipv4 address, it must be all numeric.
    # The host must contain a colon to be an IPv6 address.
    return ":" in host or host.replace(".", "").isdigit()


_cached_current_datetime: Optional[int] = None
_cached_formatted_datetime = ""


def rfc822_formatted_time() -> str:
    global _cached_current_datetime
    global _cached_formatted_datetime

    now = int(time.time())
    if now != _cached_current_datetime:
        # Weekday and month names for HTTP date/time formatting;
        # always English!
        # Tuples are constants stored in codeobject!
        _weekdayname = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        _monthname = (
            "",  # Dummy so we can use 1-based month numbers
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        )

        year, month, day, hh, mm, ss, wd, *tail = time.gmtime(now)
        _cached_formatted_datetime = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
            _weekdayname[wd],
            day,
            _monthname[month],
            year,
            hh,
            mm,
            ss,
        )
        _cached_current_datetime = now
    return _cached_formatted_datetime


def _weakref_handle(info: "Tuple[weakref.ref[object], str]") -> None:
    ref, name = info
    ob = ref()
    if ob is not None:
        with suppress(Exception):
            getattr(ob, name)()


def weakref_handle(
    ob: object,
    name: str,
    timeout: float,
    loop: asyncio.AbstractEventLoop,
    timeout_ceil_threshold: float = 5,
) -> Optional[asyncio.TimerHandle]:
    if timeout is not None and timeout > 0:
        when = loop.time() + timeout
        if timeout >= timeout_ceil_threshold:
            when = ceil(when)

        return loop.call_at(when, _weakref_handle, (weakref.ref(ob), name))
    return None


def call_later(
    cb: Callable[[], Any],
    timeout: float,
    loop: asyncio.AbstractEventLoop,
    timeout_ceil_threshold: float = 5,
) -> Optional[asyncio.TimerHandle]:
    if timeout is None or timeout <= 0:
        return None
    now = loop.time()
    when = calculate_timeout_when(now, timeout, timeout_ceil_threshold)
    return loop.call_at(when, cb)


def calculate_timeout_when(
    loop_time: float,
    timeout: float,
    timeout_ceiling_threshold: float,
) -> float:
    """Calculate when to execute a timeout."""
    when = loop_time + timeout
    if timeout > timeout_ceiling_threshold:
        return ceil(when)
    return when


class TimeoutHandle:
    """Timeout handle"""

    __slots__ = ("_timeout", "_loop", "_ceil_threshold", "_callbacks")

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        timeout: Optional[float],
        ceil_threshold: float = 5,
    ) -> None:
        self._timeout = timeout
        self._loop = loop
        self._ceil_threshold = ceil_threshold
        self._callbacks: List[
            Tuple[Callable[..., None], Tuple[Any, ...], Dict[str, Any]]
        ] = []

    def register(
        self, callback: Callable[..., None], *args: Any, **kwargs: Any
    ) -> None:
        self._callbacks.append((callback, args, kwargs))

    def close(self) -> None:
        self._callbacks.clear()

    def start(self) -> Optional[asyncio.TimerHandle]:
        timeout = self._timeout
        if timeout is not None and timeout > 0:
            when = self._loop.time() + timeout
            if timeout >= self._ceil_threshold:
                when = ceil(when)
            return self._loop.call_at(when, self.__call__)
        else:
            return None

    def timer(self) -> "BaseTimerContext":
        if self._timeout is not None and self._timeout > 0:
            timer = TimerContext(self._loop)
            self.register(timer.timeout)
            return timer
        else:
            return TimerNoop()

    def __call__(self) -> None:
        for cb, args, kwargs in self._callbacks:
            with suppress(Exception):
                cb(*args, **kwargs)

        self._callbacks.clear()


class BaseTimerContext(ContextManager["BaseTimerContext"]):

    __slots__ = ()

    def assert_timeout(self) -> None:
        """Raise TimeoutError if timeout has been exceeded."""


class TimerNoop(BaseTimerContext):

    __slots__ = ()

    def __enter__(self) -> BaseTimerContext:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        return


class TimerContext(BaseTimerContext):
    """Low resolution timeout context manager"""

    __slots__ = ("_loop", "_tasks", "_cancelled", "_cancelling")

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._tasks: List[asyncio.Task[Any]] = []
        self._cancelled = False
        self._cancelling = 0

    def assert_timeout(self) -> None:
        """Raise TimeoutError if timer has already been cancelled."""
        if self._cancelled:
            raise asyncio.TimeoutError from None

    def __enter__(self) -> BaseTimerContext:
        task = asyncio.current_task(loop=self._loop)
        if task is None:
            raise RuntimeError("Timeout context manager should be used inside a task")

        if sys.version_info >= (3, 11):
            # Remember if the task was already cancelling
            # so when we __exit__ we can decide if we should
            # raise asyncio.TimeoutError or let the cancellation propagate
            self._cancelling = task.cancelling()

        if self._cancelled:
            raise asyncio.TimeoutError from None

        self._tasks.append(task)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        enter_task: Optional[asyncio.Task[Any]] = None
        if self._tasks:
            enter_task = self._tasks.pop()

        if exc_type is asyncio.CancelledError and self._cancelled:
            assert enter_task is not None
            # The timeout was hit, and the task was cancelled
            # so we need to uncancel the last task that entered the context manager
            # since the cancellation should not leak out of the context manager
            if sys.version_info >= (3, 11):
                # If the task was already cancelling don't raise
                # asyncio.TimeoutError and instead return None
                # to allow the cancellation to propagate
                if enter_task.uncancel() > self._cancelling:
                    return None
            raise asyncio.TimeoutError from exc_val
        return None

    def timeout(self) -> None:
        if not self._cancelled:
            for task in set(self._tasks):
                task.cancel()

            self._cancelled = True


def ceil_timeout(
    delay: Optional[float], ceil_threshold: float = 5
) -> async_timeout.Timeout:
    if delay is None or delay <= 0:
        return async_timeout.timeout(None)

    loop = asyncio.get_running_loop()
    now = loop.time()
    when = now + delay
    if delay > ceil_threshold:
        when = ceil(when)
    return async_timeout.timeout_at(when)


class HeadersMixin:
    """Mixin for handling headers."""

    ATTRS = frozenset(["_content_type", "_content_dict", "_stored_content_type"])

    _headers: MultiMapping[str]
    _content_type: Optional[str] = None
    _content_dict: Optional[Dict[str, str]] = None
    _stored_content_type: Union[str, None, _SENTINEL] = sentinel

    def _parse_content_type(self, raw: Optional[str]) -> None:
        self._stored_content_type = raw
        if raw is None:
            # default value according to RFC 2616
            self._content_type = "application/octet-stream"
            self._content_dict = {}
        else:
            content_type, content_mapping_proxy = parse_content_type(raw)
            self._content_type = content_type
            # _content_dict needs to be mutable so we can update it
            self._content_dict = content_mapping_proxy.copy()

    @property
    def content_type(self) -> str:
        """The value of content part for Content-Type HTTP header."""
        raw = self._headers.get(hdrs.CONTENT_TYPE)
        if self._stored_content_type != raw:
            self._parse_content_type(raw)
        assert self._content_type is not None
        return self._content_type

    @property
    def charset(self) -> Optional[str]:
        """The value of charset part for Content-Type HTTP header."""
        raw = self._headers.get(hdrs.CONTENT_TYPE)
        if self._stored_content_type != raw:
            self._parse_content_type(raw)
        assert self._content_dict is not None
        return self._content_dict.get("charset")

    @property
    def content_length(self) -> Optional[int]:
        """The value of Content-Length HTTP header."""
        content_length = self._headers.get(hdrs.CONTENT_LENGTH)
        return None if content_length is None else int(content_length)


def set_result(fut: "asyncio.Future[_T]", result: _T) -> None:
    if not fut.done():
        fut.set_result(result)


_EXC_SENTINEL = BaseException()


class ErrorableProtocol(Protocol):
    def set_exception(
        self,
        exc: BaseException,
        exc_cause: BaseException = ...,
    ) -> None: ...  # pragma: no cover


def set_exception(
    fut: "asyncio.Future[_T] | ErrorableProtocol",
    exc: BaseException,
    exc_cause: BaseException = _EXC_SENTINEL,
) -> None:
    """Set future exception.

    If the future is marked as complete, this function is a no-op.

    :param exc_cause: An exception that is a direct cause of ``exc``.
                      Only set if provided.
    """
    if asyncio.isfuture(fut) and fut.done():
        return

    exc_is_sentinel = exc_cause is _EXC_SENTINEL
    exc_causes_itself = exc is exc_cause
    if not exc_is_sentinel and not exc_causes_itself:
        exc.__cause__ = exc_cause

    fut.set_exception(exc)


@functools.total_ordering
class AppKey(Generic[_T]):
    """Keys for static typing support in Application."""

    __slots__ = ("_name", "_t", "__orig_class__")

    # This may be set by Python when instantiating with a generic type. We need to
    # support this, in order to support types that are not concrete classes,
    # like Iterable, which can't be passed as the second parameter to __init__.
    __orig_class__: Type[object]

    def __init__(self, name: str, t: Optional[Type[_T]] = None):
        # Prefix with module name to help deduplicate key names.
        frame = inspect.currentframe()
        while frame:
            if frame.f_code.co_name == "<module>":
                module: str = frame.f_globals["__name__"]
                break
            frame = frame.f_back

        self._name = module + "." + name
        self._t = t

    def __lt__(self, other: object) -> bool:
        if isinstance(other, AppKey):
            return self._name < other._name
        return True  # Order AppKey above other types.

    def __repr__(self) -> str:
        t = self._t
        if t is None:
            with suppress(AttributeError):
                # Set to type arg.
                t = get_args(self.__orig_class__)[0]

        if t is None:
            t_repr = "<<Unknown>>"
        elif isinstance(t, type):
            if t.__module__ == "builtins":
                t_repr = t.__qualname__
            else:
                t_repr = f"{t.__module__}.{t.__qualname__}"
        else:
            t_repr = repr(t)
        return f"<AppKey({self._name}, type={t_repr})>"


class ChainMapProxy(Mapping[Union[str, AppKey[Any]], Any]):
    __slots__ = ("_maps",)

    def __init__(self, maps: Iterable[Mapping[Union[str, AppKey[Any]], Any]]) -> None:
        self._maps = tuple(maps)

    def __init_subclass__(cls) -> None:
        raise TypeError(
            "Inheritance class {} from ChainMapProxy "
            "is forbidden".format(cls.__name__)
        )

    @overload  # type: ignore[override]
    def __getitem__(self, key: AppKey[_T]) -> _T: ...

    @overload
    def __getitem__(self, key: str) -> Any: ...

    def __getitem__(self, key: Union[str, AppKey[_T]]) -> Any:
        for mapping in self._maps:
            try:
                return mapping[key]
            except KeyError:
                pass
        raise KeyError(key)

    @overload  # type: ignore[override]
    def get(self, key: AppKey[_T], default: _S) -> Union[_T, _S]: ...

    @overload
    def get(self, key: AppKey[_T], default: None = ...) -> Optional[_T]: ...

    @overload
    def get(self, key: str, default: Any = ...) -> Any: ...

    def get(self, key: Union[str, AppKey[_T]], default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __len__(self) -> int:
        # reuses stored hash values if possible
        return len(set().union(*self._maps))

    def __iter__(self) -> Iterator[Union[str, AppKey[Any]]]:
        d: Dict[Union[str, AppKey[Any]], Any] = {}
        for mapping in reversed(self._maps):
            # reuses stored hash values if possible
            d.update(mapping)
        return iter(d)

    def __contains__(self, key: object) -> bool:
        return any(key in m for m in self._maps)

    def __bool__(self) -> bool:
        return any(self._maps)

    def __repr__(self) -> str:
        content = ", ".join(map(repr, self._maps))
        return f"ChainMapProxy({content})"


# https://tools.ietf.org/html/rfc7232#section-2.3
_ETAGC = r"[!\x23-\x7E\x80-\xff]+"
_ETAGC_RE = re.compile(_ETAGC)
_QUOTED_ETAG = rf'(W/)?"({_ETAGC})"'
QUOTED_ETAG_RE = re.compile(_QUOTED_ETAG)
LIST_QUOTED_ETAG_RE = re.compile(rf"({_QUOTED_ETAG})(?:\s*,\s*|$)|(.)")

ETAG_ANY = "*"


@attr.s(auto_attribs=True, frozen=True, slots=True)
class ETag:
    value: str
    is_weak: bool = False


def validate_etag_value(value: str) -> None:
    if value != ETAG_ANY and not _ETAGC_RE.fullmatch(value):
        raise ValueError(
            f"Value {value!r} is not a valid etag. Maybe it contains '\"'?"
        )


def parse_http_date(date_str: Optional[str]) -> Optional[datetime.datetime]:
    """Process a date string, return a datetime object"""
    if date_str is not None:
        timetuple = parsedate(date_str)
        if timetuple is not None:
            with suppress(ValueError):
                return datetime.datetime(*timetuple[:6], tzinfo=datetime.timezone.utc)
    return None


@functools.lru_cache
def must_be_empty_body(method: str, code: int) -> bool:
    """Check if a request must return an empty body."""
    return (
        code in EMPTY_BODY_STATUS_CODES
        or method in EMPTY_BODY_METHODS
        or (200 <= code < 300 and method in hdrs.METH_CONNECT_ALL)
    )


def should_remove_content_length(method: str, code: int) -> bool:
    """Check if a Content-Length header should be removed.

    This should always be a subset of must_be_empty_body
    """
    # https://www.rfc-editor.org/rfc/rfc9110.html#section-8.6-8
    # https://www.rfc-editor.org/rfc/rfc9110.html#section-15.4.5-4
    return code in EMPTY_BODY_STATUS_CODES or (
        200 <= code < 300 and method in hdrs.METH_CONNECT_ALL
    )

# === NexusCore/openenv\Lib\site-packages\numpy\_core\_internal.py ===
"""
A place for internal code

Some things are more easily handled Python.

"""
import ast
import math
import re
import sys
import warnings

from numpy import _NoValue
from numpy.exceptions import DTypePromotionError

from .multiarray import StringDType, array, dtype, promote_types

try:
    import ctypes
except ImportError:
    ctypes = None

IS_PYPY = sys.implementation.name == 'pypy'

if sys.byteorder == 'little':
    _nbo = '<'
else:
    _nbo = '>'

def _makenames_list(adict, align):
    allfields = []

    for fname, obj in adict.items():
        n = len(obj)
        if not isinstance(obj, tuple) or n not in (2, 3):
            raise ValueError("entry not a 2- or 3- tuple")
        if n > 2 and obj[2] == fname:
            continue
        num = int(obj[1])
        if num < 0:
            raise ValueError("invalid offset.")
        format = dtype(obj[0], align=align)
        if n > 2:
            title = obj[2]
        else:
            title = None
        allfields.append((fname, format, num, title))
    # sort by offsets
    allfields.sort(key=lambda x: x[2])
    names = [x[0] for x in allfields]
    formats = [x[1] for x in allfields]
    offsets = [x[2] for x in allfields]
    titles = [x[3] for x in allfields]

    return names, formats, offsets, titles

# Called in PyArray_DescrConverter function when
#  a dictionary without "names" and "formats"
#  fields is used as a data-type descriptor.
def _usefields(adict, align):
    try:
        names = adict[-1]
    except KeyError:
        names = None
    if names is None:
        names, formats, offsets, titles = _makenames_list(adict, align)
    else:
        formats = []
        offsets = []
        titles = []
        for name in names:
            res = adict[name]
            formats.append(res[0])
            offsets.append(res[1])
            if len(res) > 2:
                titles.append(res[2])
            else:
                titles.append(None)

    return dtype({"names": names,
                  "formats": formats,
                  "offsets": offsets,
                  "titles": titles}, align)


# construct an array_protocol descriptor list
#  from the fields attribute of a descriptor
# This calls itself recursively but should eventually hit
#  a descriptor that has no fields and then return
#  a simple typestring

def _array_descr(descriptor):
    fields = descriptor.fields
    if fields is None:
        subdtype = descriptor.subdtype
        if subdtype is None:
            if descriptor.metadata is None:
                return descriptor.str
            else:
                new = descriptor.metadata.copy()
                if new:
                    return (descriptor.str, new)
                else:
                    return descriptor.str
        else:
            return (_array_descr(subdtype[0]), subdtype[1])

    names = descriptor.names
    ordered_fields = [fields[x] + (x,) for x in names]
    result = []
    offset = 0
    for field in ordered_fields:
        if field[1] > offset:
            num = field[1] - offset
            result.append(('', f'|V{num}'))
            offset += num
        elif field[1] < offset:
            raise ValueError(
                "dtype.descr is not defined for types with overlapping or "
                "out-of-order fields")
        if len(field) > 3:
            name = (field[2], field[3])
        else:
            name = field[2]
        if field[0].subdtype:
            tup = (name, _array_descr(field[0].subdtype[0]),
                   field[0].subdtype[1])
        else:
            tup = (name, _array_descr(field[0]))
        offset += field[0].itemsize
        result.append(tup)

    if descriptor.itemsize > offset:
        num = descriptor.itemsize - offset
        result.append(('', f'|V{num}'))

    return result


# format_re was originally from numarray by J. Todd Miller

format_re = re.compile(r'(?P<order1>[<>|=]?)'
                       r'(?P<repeats> *[(]?[ ,0-9]*[)]? *)'
                       r'(?P<order2>[<>|=]?)'
                       r'(?P<dtype>[A-Za-z0-9.?]*(?:\[[a-zA-Z0-9,.]+\])?)')
sep_re = re.compile(r'\s*,\s*')
space_re = re.compile(r'\s+$')

# astr is a string (perhaps comma separated)

_convorder = {'=': _nbo}

def _commastring(astr):
    startindex = 0
    result = []
    islist = False
    while startindex < len(astr):
        mo = format_re.match(astr, pos=startindex)
        try:
            (order1, repeats, order2, dtype) = mo.groups()
        except (TypeError, AttributeError):
            raise ValueError(
                f'format number {len(result) + 1} of "{astr}" is not recognized'
                ) from None
        startindex = mo.end()
        # Separator or ending padding
        if startindex < len(astr):
            if space_re.match(astr, pos=startindex):
                startindex = len(astr)
            else:
                mo = sep_re.match(astr, pos=startindex)
                if not mo:
                    raise ValueError(
                        'format number %d of "%s" is not recognized' %
                        (len(result) + 1, astr))
                startindex = mo.end()
                islist = True

        if order2 == '':
            order = order1
        elif order1 == '':
            order = order2
        else:
            order1 = _convorder.get(order1, order1)
            order2 = _convorder.get(order2, order2)
            if (order1 != order2):
                raise ValueError(
                    f'inconsistent byte-order specification {order1} and {order2}')
            order = order1

        if order in ('|', '=', _nbo):
            order = ''
        dtype = order + dtype
        if repeats == '':
            newitem = dtype
        else:
            if (repeats[0] == "(" and repeats[-1] == ")"
                    and repeats[1:-1].strip() != ""
                    and "," not in repeats):
                warnings.warn(
                    'Passing in a parenthesized single number for repeats '
                    'is deprecated; pass either a single number or indicate '
                    'a tuple with a comma, like "(2,)".', DeprecationWarning,
                    stacklevel=2)
            newitem = (dtype, ast.literal_eval(repeats))

        result.append(newitem)

    return result if islist else result[0]

class dummy_ctype:

    def __init__(self, cls):
        self._cls = cls

    def __mul__(self, other):
        return self

    def __call__(self, *other):
        return self._cls(other)

    def __eq__(self, other):
        return self._cls == other._cls

    def __ne__(self, other):
        return self._cls != other._cls

def _getintp_ctype():
    val = _getintp_ctype.cache
    if val is not None:
        return val
    if ctypes is None:
        import numpy as np
        val = dummy_ctype(np.intp)
    else:
        char = dtype('n').char
        if char == 'i':
            val = ctypes.c_int
        elif char == 'l':
            val = ctypes.c_long
        elif char == 'q':
            val = ctypes.c_longlong
        else:
            val = ctypes.c_long
    _getintp_ctype.cache = val
    return val


_getintp_ctype.cache = None

# Used for .ctypes attribute of ndarray

class _missing_ctypes:
    def cast(self, num, obj):
        return num.value

    class c_void_p:
        def __init__(self, ptr):
            self.value = ptr


class _ctypes:
    def __init__(self, array, ptr=None):
        self._arr = array

        if ctypes:
            self._ctypes = ctypes
            self._data = self._ctypes.c_void_p(ptr)
        else:
            # fake a pointer-like object that holds onto the reference
            self._ctypes = _missing_ctypes()
            self._data = self._ctypes.c_void_p(ptr)
            self._data._objects = array

        if self._arr.ndim == 0:
            self._zerod = True
        else:
            self._zerod = False

    def data_as(self, obj):
        """
        Return the data pointer cast to a particular c-types object.
        For example, calling ``self._as_parameter_`` is equivalent to
        ``self.data_as(ctypes.c_void_p)``. Perhaps you want to use
        the data as a pointer to a ctypes array of floating-point data:
        ``self.data_as(ctypes.POINTER(ctypes.c_double))``.

        The returned pointer will keep a reference to the array.
        """
        # _ctypes.cast function causes a circular reference of self._data in
        # self._data._objects. Attributes of self._data cannot be released
        # until gc.collect is called. Make a copy of the pointer first then
        # let it hold the array reference. This is a workaround to circumvent
        # the CPython bug https://bugs.python.org/issue12836.
        ptr = self._ctypes.cast(self._data, obj)
        ptr._arr = self._arr
        return ptr

    def shape_as(self, obj):
        """
        Return the shape tuple as an array of some other c-types
        type. For example: ``self.shape_as(ctypes.c_short)``.
        """
        if self._zerod:
            return None
        return (obj * self._arr.ndim)(*self._arr.shape)

    def strides_as(self, obj):
        """
        Return the strides tuple as an array of some other
        c-types type. For example: ``self.strides_as(ctypes.c_longlong)``.
        """
        if self._zerod:
            return None
        return (obj * self._arr.ndim)(*self._arr.strides)

    @property
    def data(self):
        """
        A pointer to the memory area of the array as a Python integer.
        This memory area may contain data that is not aligned, or not in
        correct byte-order. The memory area may not even be writeable.
        The array flags and data-type of this array should be respected
        when passing this attribute to arbitrary C-code to avoid trouble
        that can include Python crashing. User Beware! The value of this
        attribute is exactly the same as:
        ``self._array_interface_['data'][0]``.

        Note that unlike ``data_as``, a reference won't be kept to the array:
        code like ``ctypes.c_void_p((a + b).ctypes.data)`` will result in a
        pointer to a deallocated array, and should be spelt
        ``(a + b).ctypes.data_as(ctypes.c_void_p)``
        """
        return self._data.value

    @property
    def shape(self):
        """
        (c_intp*self.ndim): A ctypes array of length self.ndim where
        the basetype is the C-integer corresponding to ``dtype('p')`` on this
        platform (see `~numpy.ctypeslib.c_intp`). This base-type could be
        `ctypes.c_int`, `ctypes.c_long`, or `ctypes.c_longlong` depending on
        the platform. The ctypes array contains the shape of
        the underlying array.
        """
        return self.shape_as(_getintp_ctype())

    @property
    def strides(self):
        """
        (c_intp*self.ndim): A ctypes array of length self.ndim where
        the basetype is the same as for the shape attribute. This ctypes
        array contains the strides information from the underlying array.
        This strides information is important for showing how many bytes
        must be jumped to get to the next element in the array.
        """
        return self.strides_as(_getintp_ctype())

    @property
    def _as_parameter_(self):
        """
        Overrides the ctypes semi-magic method

        Enables `c_func(some_array.ctypes)`
        """
        return self.data_as(ctypes.c_void_p)

    # Numpy 1.21.0, 2021-05-18

    def get_data(self):
        """Deprecated getter for the `_ctypes.data` property.

        .. deprecated:: 1.21
        """
        warnings.warn('"get_data" is deprecated. Use "data" instead',
                      DeprecationWarning, stacklevel=2)
        return self.data

    def get_shape(self):
        """Deprecated getter for the `_ctypes.shape` property.

        .. deprecated:: 1.21
        """
        warnings.warn('"get_shape" is deprecated. Use "shape" instead',
                      DeprecationWarning, stacklevel=2)
        return self.shape

    def get_strides(self):
        """Deprecated getter for the `_ctypes.strides` property.

        .. deprecated:: 1.21
        """
        warnings.warn('"get_strides" is deprecated. Use "strides" instead',
                      DeprecationWarning, stacklevel=2)
        return self.strides

    def get_as_parameter(self):
        """Deprecated getter for the `_ctypes._as_parameter_` property.

        .. deprecated:: 1.21
        """
        warnings.warn(
            '"get_as_parameter" is deprecated. Use "_as_parameter_" instead',
            DeprecationWarning, stacklevel=2,
        )
        return self._as_parameter_


def _newnames(datatype, order):
    """
    Given a datatype and an order object, return a new names tuple, with the
    order indicated
    """
    oldnames = datatype.names
    nameslist = list(oldnames)
    if isinstance(order, str):
        order = [order]
    seen = set()
    if isinstance(order, (list, tuple)):
        for name in order:
            try:
                nameslist.remove(name)
            except ValueError:
                if name in seen:
                    raise ValueError(f"duplicate field name: {name}") from None
                else:
                    raise ValueError(f"unknown field name: {name}") from None
            seen.add(name)
        return tuple(list(order) + nameslist)
    raise ValueError(f"unsupported order value: {order}")

def _copy_fields(ary):
    """Return copy of structured array with padding between fields removed.

    Parameters
    ----------
    ary : ndarray
       Structured array from which to remove padding bytes

    Returns
    -------
    ary_copy : ndarray
       Copy of ary with padding bytes removed
    """
    dt = ary.dtype
    copy_dtype = {'names': dt.names,
                  'formats': [dt.fields[name][0] for name in dt.names]}
    return array(ary, dtype=copy_dtype, copy=True)

def _promote_fields(dt1, dt2):
    """ Perform type promotion for two structured dtypes.

    Parameters
    ----------
    dt1 : structured dtype
        First dtype.
    dt2 : structured dtype
        Second dtype.

    Returns
    -------
    out : dtype
        The promoted dtype

    Notes
    -----
    If one of the inputs is aligned, the result will be.  The titles of
    both descriptors must match (point to the same field).
    """
    # Both must be structured and have the same names in the same order
    if (dt1.names is None or dt2.names is None) or dt1.names != dt2.names:
        raise DTypePromotionError(
                f"field names `{dt1.names}` and `{dt2.names}` mismatch.")

    # if both are identical, we can (maybe!) just return the same dtype.
    identical = dt1 is dt2
    new_fields = []
    for name in dt1.names:
        field1 = dt1.fields[name]
        field2 = dt2.fields[name]
        new_descr = promote_types(field1[0], field2[0])
        identical = identical and new_descr is field1[0]

        # Check that the titles match (if given):
        if field1[2:] != field2[2:]:
            raise DTypePromotionError(
                    f"field titles of field '{name}' mismatch")
        if len(field1) == 2:
            new_fields.append((name, new_descr))
        else:
            new_fields.append(((field1[2], name), new_descr))

    res = dtype(new_fields, align=dt1.isalignedstruct or dt2.isalignedstruct)

    # Might as well preserve identity (and metadata) if the dtype is identical
    # and the itemsize, offsets are also unmodified.  This could probably be
    # sped up, but also probably just be removed entirely.
    if identical and res.itemsize == dt1.itemsize:
        for name in dt1.names:
            if dt1.fields[name][1] != res.fields[name][1]:
                return res  # the dtype changed.
        return dt1

    return res


def _getfield_is_safe(oldtype, newtype, offset):
    """ Checks safety of getfield for object arrays.

    As in _view_is_safe, we need to check that memory containing objects is not
    reinterpreted as a non-object datatype and vice versa.

    Parameters
    ----------
    oldtype : data-type
        Data type of the original ndarray.
    newtype : data-type
        Data type of the field being accessed by ndarray.getfield
    offset : int
        Offset of the field being accessed by ndarray.getfield

    Raises
    ------
    TypeError
        If the field access is invalid

    """
    if newtype.hasobject or oldtype.hasobject:
        if offset == 0 and newtype == oldtype:
            return
        if oldtype.names is not None:
            for name in oldtype.names:
                if (oldtype.fields[name][1] == offset and
                        oldtype.fields[name][0] == newtype):
                    return
        raise TypeError("Cannot get/set field of an object array")
    return

def _view_is_safe(oldtype, newtype):
    """ Checks safety of a view involving object arrays, for example when
    doing::

        np.zeros(10, dtype=oldtype).view(newtype)

    Parameters
    ----------
    oldtype : data-type
        Data type of original ndarray
    newtype : data-type
        Data type of the view

    Raises
    ------
    TypeError
        If the new type is incompatible with the old type.

    """

    # if the types are equivalent, there is no problem.
    # for example: dtype((np.record, 'i4,i4')) == dtype((np.void, 'i4,i4'))
    if oldtype == newtype:
        return

    if newtype.hasobject or oldtype.hasobject:
        raise TypeError("Cannot change data-type for array of references.")
    return


# Given a string containing a PEP 3118 format specifier,
# construct a NumPy dtype

_pep3118_native_map = {
    '?': '?',
    'c': 'S1',
    'b': 'b',
    'B': 'B',
    'h': 'h',
    'H': 'H',
    'i': 'i',
    'I': 'I',
    'l': 'l',
    'L': 'L',
    'q': 'q',
    'Q': 'Q',
    'e': 'e',
    'f': 'f',
    'd': 'd',
    'g': 'g',
    'Zf': 'F',
    'Zd': 'D',
    'Zg': 'G',
    's': 'S',
    'w': 'U',
    'O': 'O',
    'x': 'V',  # padding
}
_pep3118_native_typechars = ''.join(_pep3118_native_map.keys())

_pep3118_standard_map = {
    '?': '?',
    'c': 'S1',
    'b': 'b',
    'B': 'B',
    'h': 'i2',
    'H': 'u2',
    'i': 'i4',
    'I': 'u4',
    'l': 'i4',
    'L': 'u4',
    'q': 'i8',
    'Q': 'u8',
    'e': 'f2',
    'f': 'f',
    'd': 'd',
    'Zf': 'F',
    'Zd': 'D',
    's': 'S',
    'w': 'U',
    'O': 'O',
    'x': 'V',  # padding
}
_pep3118_standard_typechars = ''.join(_pep3118_standard_map.keys())

_pep3118_unsupported_map = {
    'u': 'UCS-2 strings',
    '&': 'pointers',
    't': 'bitfields',
    'X': 'function pointers',
}

class _Stream:
    def __init__(self, s):
        self.s = s
        self.byteorder = '@'

    def advance(self, n):
        res = self.s[:n]
        self.s = self.s[n:]
        return res

    def consume(self, c):
        if self.s[:len(c)] == c:
            self.advance(len(c))
            return True
        return False

    def consume_until(self, c):
        if callable(c):
            i = 0
            while i < len(self.s) and not c(self.s[i]):
                i = i + 1
            return self.advance(i)
        else:
            i = self.s.index(c)
            res = self.advance(i)
            self.advance(len(c))
            return res

    @property
    def next(self):
        return self.s[0]

    def __bool__(self):
        return bool(self.s)


def _dtype_from_pep3118(spec):
    stream = _Stream(spec)
    dtype, align = __dtype_from_pep3118(stream, is_subdtype=False)
    return dtype

def __dtype_from_pep3118(stream, is_subdtype):
    field_spec = {
        'names': [],
        'formats': [],
        'offsets': [],
        'itemsize': 0
    }
    offset = 0
    common_alignment = 1
    is_padding = False

    # Parse spec
    while stream:
        value = None

        # End of structure, bail out to upper level
        if stream.consume('}'):
            break

        # Sub-arrays (1)
        shape = None
        if stream.consume('('):
            shape = stream.consume_until(')')
            shape = tuple(map(int, shape.split(',')))

        # Byte order
        if stream.next in ('@', '=', '<', '>', '^', '!'):
            byteorder = stream.advance(1)
            if byteorder == '!':
                byteorder = '>'
            stream.byteorder = byteorder

        # Byte order characters also control native vs. standard type sizes
        if stream.byteorder in ('@', '^'):
            type_map = _pep3118_native_map
            type_map_chars = _pep3118_native_typechars
        else:
            type_map = _pep3118_standard_map
            type_map_chars = _pep3118_standard_typechars

        # Item sizes
        itemsize_str = stream.consume_until(lambda c: not c.isdigit())
        if itemsize_str:
            itemsize = int(itemsize_str)
        else:
            itemsize = 1

        # Data types
        is_padding = False

        if stream.consume('T{'):
            value, align = __dtype_from_pep3118(
                stream, is_subdtype=True)
        elif stream.next in type_map_chars:
            if stream.next == 'Z':
                typechar = stream.advance(2)
            else:
                typechar = stream.advance(1)

            is_padding = (typechar == 'x')
            dtypechar = type_map[typechar]
            if dtypechar in 'USV':
                dtypechar += '%d' % itemsize
                itemsize = 1
            numpy_byteorder = {'@': '=', '^': '='}.get(
                stream.byteorder, stream.byteorder)
            value = dtype(numpy_byteorder + dtypechar)
            align = value.alignment
        elif stream.next in _pep3118_unsupported_map:
            desc = _pep3118_unsupported_map[stream.next]
            raise NotImplementedError(
                f"Unrepresentable PEP 3118 data type {stream.next!r} ({desc})")
        else:
            raise ValueError(
                f"Unknown PEP 3118 data type specifier {stream.s!r}"
            )

        #
        # Native alignment may require padding
        #
        # Here we assume that the presence of a '@' character implicitly
        # implies that the start of the array is *already* aligned.
        #
        extra_offset = 0
        if stream.byteorder == '@':
            start_padding = (-offset) % align
            intra_padding = (-value.itemsize) % align

            offset += start_padding

            if intra_padding != 0:
                if itemsize > 1 or (shape is not None and _prod(shape) > 1):
                    # Inject internal padding to the end of the sub-item
                    value = _add_trailing_padding(value, intra_padding)
                else:
                    # We can postpone the injection of internal padding,
                    # as the item appears at most once
                    extra_offset += intra_padding

            # Update common alignment
            common_alignment = _lcm(align, common_alignment)

        # Convert itemsize to sub-array
        if itemsize != 1:
            value = dtype((value, (itemsize,)))

        # Sub-arrays (2)
        if shape is not None:
            value = dtype((value, shape))

        # Field name
        if stream.consume(':'):
            name = stream.consume_until(':')
        else:
            name = None

        if not (is_padding and name is None):
            if name is not None and name in field_spec['names']:
                raise RuntimeError(
                    f"Duplicate field name '{name}' in PEP3118 format"
                )
            field_spec['names'].append(name)
            field_spec['formats'].append(value)
            field_spec['offsets'].append(offset)

        offset += value.itemsize
        offset += extra_offset

        field_spec['itemsize'] = offset

    # extra final padding for aligned types
    if stream.byteorder == '@':
        field_spec['itemsize'] += (-offset) % common_alignment

    # Check if this was a simple 1-item type, and unwrap it
    if (field_spec['names'] == [None]
            and field_spec['offsets'][0] == 0
            and field_spec['itemsize'] == field_spec['formats'][0].itemsize
            and not is_subdtype):
        ret = field_spec['formats'][0]
    else:
        _fix_names(field_spec)
        ret = dtype(field_spec)

    # Finished
    return ret, common_alignment

def _fix_names(field_spec):
    """ Replace names which are None with the next unused f%d name """
    names = field_spec['names']
    for i, name in enumerate(names):
        if name is not None:
            continue

        j = 0
        while True:
            name = f'f{j}'
            if name not in names:
                break
            j = j + 1
        names[i] = name

def _add_trailing_padding(value, padding):
    """Inject the specified number of padding bytes at the end of a dtype"""
    if value.fields is None:
        field_spec = {
            'names': ['f0'],
            'formats': [value],
            'offsets': [0],
            'itemsize': value.itemsize
        }
    else:
        fields = value.fields
        names = value.names
        field_spec = {
            'names': names,
            'formats': [fields[name][0] for name in names],
            'offsets': [fields[name][1] for name in names],
            'itemsize': value.itemsize
        }

    field_spec['itemsize'] += padding
    return dtype(field_spec)

def _prod(a):
    p = 1
    for x in a:
        p *= x
    return p

def _gcd(a, b):
    """Calculate the greatest common divisor of a and b"""
    if not (math.isfinite(a) and math.isfinite(b)):
        raise ValueError('Can only find greatest common divisor of '
                         f'finite arguments, found "{a}" and "{b}"')
    while b:
        a, b = b, a % b
    return a

def _lcm(a, b):
    return a // _gcd(a, b) * b

def array_ufunc_errmsg_formatter(dummy, ufunc, method, *inputs, **kwargs):
    """ Format the error message for when __array_ufunc__ gives up. """
    args_string = ', '.join([f'{arg!r}' for arg in inputs] +
                            [f'{k}={v!r}'
                             for k, v in kwargs.items()])
    args = inputs + kwargs.get('out', ())
    types_string = ', '.join(repr(type(arg).__name__) for arg in args)
    return ('operand type(s) all returned NotImplemented from '
            f'__array_ufunc__({ufunc!r}, {method!r}, {args_string}): {types_string}'
            )


def array_function_errmsg_formatter(public_api, types):
    """ Format the error message for when __array_ufunc__ gives up. """
    func_name = f'{public_api.__module__}.{public_api.__name__}'
    return (f"no implementation found for '{func_name}' on types that implement "
            f'__array_function__: {list(types)}')


def _ufunc_doc_signature_formatter(ufunc):
    """
    Builds a signature string which resembles PEP 457

    This is used to construct the first line of the docstring
    """

    # input arguments are simple
    if ufunc.nin == 1:
        in_args = 'x'
    else:
        in_args = ', '.join(f'x{i + 1}' for i in range(ufunc.nin))

    # output arguments are both keyword or positional
    if ufunc.nout == 0:
        out_args = ', /, out=()'
    elif ufunc.nout == 1:
        out_args = ', /, out=None'
    else:
        out_args = '[, {positional}], / [, out={default}]'.format(
            positional=', '.join(
                f'out{i + 1}' for i in range(ufunc.nout)),
            default=repr((None,) * ufunc.nout)
        )

    # keyword only args depend on whether this is a gufunc
    kwargs = (
        ", casting='same_kind'"
        ", order='K'"
        ", dtype=None"
        ", subok=True"
    )

    # NOTE: gufuncs may or may not support the `axis` parameter
    if ufunc.signature is None:
        kwargs = f", where=True{kwargs}[, signature]"
    else:
        kwargs += "[, signature, axes, axis]"

    # join all the parts together
    return f'{ufunc.__name__}({in_args}{out_args}, *{kwargs})'


def npy_ctypes_check(cls):
    # determine if a class comes from ctypes, in order to work around
    # a bug in the buffer protocol for those objects, bpo-10746
    try:
        # ctypes class are new-style, so have an __mro__. This probably fails
        # for ctypes classes with multiple inheritance.
        if IS_PYPY:
            # (..., _ctypes.basics._CData, Bufferable, object)
            ctype_base = cls.__mro__[-3]
        else:
            # # (..., _ctypes._CData, object)
            ctype_base = cls.__mro__[-2]
        # right now, they're part of the _ctypes module
        return '_ctypes' in ctype_base.__module__
    except Exception:
        return False

# used to handle the _NoValue default argument for na_object
# in the C implementation of the __reduce__ method for stringdtype
def _convert_to_stringdtype_kwargs(coerce, na_object=_NoValue):
    if na_object is _NoValue:
        return StringDType(coerce=coerce)
    return StringDType(coerce=coerce, na_object=na_object)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\ml.py ===
"""
    pygments.lexers.ml
    ~~~~~~~~~~~~~~~~~~

    Lexers for ML family languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, default, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Error

__all__ = ['SMLLexer', 'OcamlLexer', 'OpaLexer', 'ReasonLexer', 'FStarLexer']


class SMLLexer(RegexLexer):
    """
    For the Standard ML language.
    """

    name = 'Standard ML'
    aliases = ['sml']
    filenames = ['*.sml', '*.sig', '*.fun']
    mimetypes = ['text/x-standardml', 'application/x-standardml']
    url = 'https://en.wikipedia.org/wiki/Standard_ML'
    version_added = '1.5'

    alphanumid_reserved = {
        # Core
        'abstype', 'and', 'andalso', 'as', 'case', 'datatype', 'do', 'else',
        'end', 'exception', 'fn', 'fun', 'handle', 'if', 'in', 'infix',
        'infixr', 'let', 'local', 'nonfix', 'of', 'op', 'open', 'orelse',
        'raise', 'rec', 'then', 'type', 'val', 'with', 'withtype', 'while',
        # Modules
        'eqtype', 'functor', 'include', 'sharing', 'sig', 'signature',
        'struct', 'structure', 'where',
    }

    symbolicid_reserved = {
        # Core
        ':', r'\|', '=', '=>', '->', '#',
        # Modules
        ':>',
    }

    nonid_reserved = {'(', ')', '[', ']', '{', '}', ',', ';', '...', '_'}

    alphanumid_re = r"[a-zA-Z][\w']*"
    symbolicid_re = r"[!%&$#+\-/:<=>?@\\~`^|*]+"

    # A character constant is a sequence of the form #s, where s is a string
    # constant denoting a string of size one character. This setup just parses
    # the entire string as either a String.Double or a String.Char (depending
    # on the argument), even if the String.Char is an erroneous
    # multiple-character string.
    def stringy(whatkind):
        return [
            (r'[^"\\]', whatkind),
            (r'\\[\\"abtnvfr]', String.Escape),
            # Control-character notation is used for codes < 32,
            # where \^@ == \000
            (r'\\\^[\x40-\x5e]', String.Escape),
            # Docs say 'decimal digits'
            (r'\\[0-9]{3}', String.Escape),
            (r'\\u[0-9a-fA-F]{4}', String.Escape),
            (r'\\\s+\\', String.Interpol),
            (r'"', whatkind, '#pop'),
        ]

    # Callbacks for distinguishing tokens and reserved words
    def long_id_callback(self, match):
        if match.group(1) in self.alphanumid_reserved:
            token = Error
        else:
            token = Name.Namespace
        yield match.start(1), token, match.group(1)
        yield match.start(2), Punctuation, match.group(2)

    def end_id_callback(self, match):
        if match.group(1) in self.alphanumid_reserved:
            token = Error
        elif match.group(1) in self.symbolicid_reserved:
            token = Error
        else:
            token = Name
        yield match.start(1), token, match.group(1)

    def id_callback(self, match):
        str = match.group(1)
        if str in self.alphanumid_reserved:
            token = Keyword.Reserved
        elif str in self.symbolicid_reserved:
            token = Punctuation
        else:
            token = Name
        yield match.start(1), token, str

    tokens = {
        # Whitespace and comments are (almost) everywhere
        'whitespace': [
            (r'\s+', Text),
            (r'\(\*', Comment.Multiline, 'comment'),
        ],

        'delimiters': [
            # This lexer treats these delimiters specially:
            # Delimiters define scopes, and the scope is how the meaning of
            # the `|' is resolved - is it a case/handle expression, or function
            # definition by cases? (This is not how the Definition works, but
            # it's how MLton behaves, see http://mlton.org/SMLNJDeviations)
            (r'\(|\[|\{', Punctuation, 'main'),
            (r'\)|\]|\}', Punctuation, '#pop'),
            (r'\b(let|if|local)\b(?!\')', Keyword.Reserved, ('main', 'main')),
            (r'\b(struct|sig|while)\b(?!\')', Keyword.Reserved, 'main'),
            (r'\b(do|else|end|in|then)\b(?!\')', Keyword.Reserved, '#pop'),
        ],

        'core': [
            # Punctuation that doesn't overlap symbolic identifiers
            (r'({})'.format('|'.join(re.escape(z) for z in nonid_reserved)),
             Punctuation),

            # Special constants: strings, floats, numbers in decimal and hex
            (r'#"', String.Char, 'char'),
            (r'"', String.Double, 'string'),
            (r'~?0x[0-9a-fA-F]+', Number.Hex),
            (r'0wx[0-9a-fA-F]+', Number.Hex),
            (r'0w\d+', Number.Integer),
            (r'~?\d+\.\d+[eE]~?\d+', Number.Float),
            (r'~?\d+\.\d+', Number.Float),
            (r'~?\d+[eE]~?\d+', Number.Float),
            (r'~?\d+', Number.Integer),

            # Labels
            (r'#\s*[1-9][0-9]*', Name.Label),
            (rf'#\s*({alphanumid_re})', Name.Label),
            (rf'#\s+({symbolicid_re})', Name.Label),
            # Some reserved words trigger a special, local lexer state change
            (r'\b(datatype|abstype)\b(?!\')', Keyword.Reserved, 'dname'),
            (r'\b(exception)\b(?!\')', Keyword.Reserved, 'ename'),
            (r'\b(functor|include|open|signature|structure)\b(?!\')',
             Keyword.Reserved, 'sname'),
            (r'\b(type|eqtype)\b(?!\')', Keyword.Reserved, 'tname'),

            # Regular identifiers, long and otherwise
            (r'\'[\w\']*', Name.Decorator),
            (rf'({alphanumid_re})(\.)', long_id_callback, "dotted"),
            (rf'({alphanumid_re})', id_callback),
            (rf'({symbolicid_re})', id_callback),
        ],
        'dotted': [
            (rf'({alphanumid_re})(\.)', long_id_callback),
            (rf'({alphanumid_re})', end_id_callback, "#pop"),
            (rf'({symbolicid_re})', end_id_callback, "#pop"),
            (r'\s+', Error),
            (r'\S+', Error),
        ],


        # Main parser (prevents errors in files that have scoping errors)
        'root': [
            default('main')
        ],

        # In this scope, I expect '|' to not be followed by a function name,
        # and I expect 'and' to be followed by a binding site
        'main': [
            include('whitespace'),

            # Special behavior of val/and/fun
            (r'\b(val|and)\b(?!\')', Keyword.Reserved, 'vname'),
            (r'\b(fun)\b(?!\')', Keyword.Reserved,
             ('#pop', 'main-fun', 'fname')),

            include('delimiters'),
            include('core'),
            (r'\S+', Error),
        ],

        # In this scope, I expect '|' and 'and' to be followed by a function
        'main-fun': [
            include('whitespace'),

            (r'\s', Text),
            (r'\(\*', Comment.Multiline, 'comment'),

            # Special behavior of val/and/fun
            (r'\b(fun|and)\b(?!\')', Keyword.Reserved, 'fname'),
            (r'\b(val)\b(?!\')', Keyword.Reserved,
             ('#pop', 'main', 'vname')),

            # Special behavior of '|' and '|'-manipulating keywords
            (r'\|', Punctuation, 'fname'),
            (r'\b(case|handle)\b(?!\')', Keyword.Reserved,
             ('#pop', 'main')),

            include('delimiters'),
            include('core'),
            (r'\S+', Error),
        ],

        # Character and string parsers
        'char': stringy(String.Char),
        'string': stringy(String.Double),

        'breakout': [
            (r'(?=\b({})\b(?!\'))'.format('|'.join(alphanumid_reserved)), Text, '#pop'),
        ],

        # Dealing with what comes after module system keywords
        'sname': [
            include('whitespace'),
            include('breakout'),

            (rf'({alphanumid_re})', Name.Namespace),
            default('#pop'),
        ],

        # Dealing with what comes after the 'fun' (or 'and' or '|') keyword
        'fname': [
            include('whitespace'),
            (r'\'[\w\']*', Name.Decorator),
            (r'\(', Punctuation, 'tyvarseq'),

            (rf'({alphanumid_re})', Name.Function, '#pop'),
            (rf'({symbolicid_re})', Name.Function, '#pop'),

            # Ignore interesting function declarations like "fun (x + y) = ..."
            default('#pop'),
        ],

        # Dealing with what comes after the 'val' (or 'and') keyword
        'vname': [
            include('whitespace'),
            (r'\'[\w\']*', Name.Decorator),
            (r'\(', Punctuation, 'tyvarseq'),

            (rf'({alphanumid_re})(\s*)(=(?!{symbolicid_re}))',
             bygroups(Name.Variable, Text, Punctuation), '#pop'),
            (rf'({symbolicid_re})(\s*)(=(?!{symbolicid_re}))',
             bygroups(Name.Variable, Text, Punctuation), '#pop'),
            (rf'({alphanumid_re})', Name.Variable, '#pop'),
            (rf'({symbolicid_re})', Name.Variable, '#pop'),

            # Ignore interesting patterns like 'val (x, y)'
            default('#pop'),
        ],

        # Dealing with what comes after the 'type' (or 'and') keyword
        'tname': [
            include('whitespace'),
            include('breakout'),

            (r'\'[\w\']*', Name.Decorator),
            (r'\(', Punctuation, 'tyvarseq'),
            (rf'=(?!{symbolicid_re})', Punctuation, ('#pop', 'typbind')),

            (rf'({alphanumid_re})', Keyword.Type),
            (rf'({symbolicid_re})', Keyword.Type),
            (r'\S+', Error, '#pop'),
        ],

        # A type binding includes most identifiers
        'typbind': [
            include('whitespace'),

            (r'\b(and)\b(?!\')', Keyword.Reserved, ('#pop', 'tname')),

            include('breakout'),
            include('core'),
            (r'\S+', Error, '#pop'),
        ],

        # Dealing with what comes after the 'datatype' (or 'and') keyword
        'dname': [
            include('whitespace'),
            include('breakout'),

            (r'\'[\w\']*', Name.Decorator),
            (r'\(', Punctuation, 'tyvarseq'),
            (r'(=)(\s*)(datatype)',
             bygroups(Punctuation, Text, Keyword.Reserved), '#pop'),
            (rf'=(?!{symbolicid_re})', Punctuation,
             ('#pop', 'datbind', 'datcon')),

            (rf'({alphanumid_re})', Keyword.Type),
            (rf'({symbolicid_re})', Keyword.Type),
            (r'\S+', Error, '#pop'),
        ],

        # common case - A | B | C of int
        'datbind': [
            include('whitespace'),

            (r'\b(and)\b(?!\')', Keyword.Reserved, ('#pop', 'dname')),
            (r'\b(withtype)\b(?!\')', Keyword.Reserved, ('#pop', 'tname')),
            (r'\b(of)\b(?!\')', Keyword.Reserved),

            (rf'(\|)(\s*)({alphanumid_re})',
             bygroups(Punctuation, Text, Name.Class)),
            (rf'(\|)(\s+)({symbolicid_re})',
             bygroups(Punctuation, Text, Name.Class)),

            include('breakout'),
            include('core'),
            (r'\S+', Error),
        ],

        # Dealing with what comes after an exception
        'ename': [
            include('whitespace'),

            (rf'(and\b)(\s+)({alphanumid_re})',
             bygroups(Keyword.Reserved, Text, Name.Class)),
            (rf'(and\b)(\s*)({symbolicid_re})',
             bygroups(Keyword.Reserved, Text, Name.Class)),
            (r'\b(of)\b(?!\')', Keyword.Reserved),
            (rf'({alphanumid_re})|({symbolicid_re})', Name.Class),

            default('#pop'),
        ],

        'datcon': [
            include('whitespace'),
            (rf'({alphanumid_re})', Name.Class, '#pop'),
            (rf'({symbolicid_re})', Name.Class, '#pop'),
            (r'\S+', Error, '#pop'),
        ],

        # Series of type variables
        'tyvarseq': [
            (r'\s', Text),
            (r'\(\*', Comment.Multiline, 'comment'),

            (r'\'[\w\']*', Name.Decorator),
            (alphanumid_re, Name),
            (r',', Punctuation),
            (r'\)', Punctuation, '#pop'),
            (symbolicid_re, Name),
        ],

        'comment': [
            (r'[^(*)]', Comment.Multiline),
            (r'\(\*', Comment.Multiline, '#push'),
            (r'\*\)', Comment.Multiline, '#pop'),
            (r'[(*)]', Comment.Multiline),
        ],
    }


class OcamlLexer(RegexLexer):
    """
    For the OCaml language.
    """

    name = 'OCaml'
    url = 'https://ocaml.org/'
    aliases = ['ocaml']
    filenames = ['*.ml', '*.mli', '*.mll', '*.mly']
    mimetypes = ['text/x-ocaml']
    version_added = '0.7'

    keywords = (
        'and', 'as', 'assert', 'begin', 'class', 'constraint', 'do', 'done',
        'downto', 'else', 'end', 'exception', 'external', 'false',
        'for', 'fun', 'function', 'functor', 'if', 'in', 'include',
        'inherit', 'initializer', 'lazy', 'let', 'match', 'method',
        'module', 'mutable', 'new', 'object', 'of', 'open', 'private',
        'raise', 'rec', 'sig', 'struct', 'then', 'to', 'true', 'try',
        'type', 'val', 'virtual', 'when', 'while', 'with',
    )
    keyopts = (
        '!=', '#', '&', '&&', r'\(', r'\)', r'\*', r'\+', ',', '-',
        r'-\.', '->', r'\.', r'\.\.', ':', '::', ':=', ':>', ';', ';;', '<',
        '<-', '=', '>', '>]', r'>\}', r'\?', r'\?\?', r'\[', r'\[<', r'\[>',
        r'\[\|', ']', '_', '`', r'\{', r'\{<', r'\|', r'\|]', r'\}', '~'
    )

    operators = r'[!$%&*+\./:<=>?@^|~-]'
    word_operators = ('asr', 'land', 'lor', 'lsl', 'lxor', 'mod', 'or')
    prefix_syms = r'[!?~]'
    infix_syms = r'[=<>@^|&+\*/$%-]'
    primitives = ('unit', 'int', 'float', 'bool', 'string', 'char', 'list', 'array')

    tokens = {
        'escape-sequence': [
            (r'\\[\\"\'ntbr]', String.Escape),
            (r'\\[0-9]{3}', String.Escape),
            (r'\\x[0-9a-fA-F]{2}', String.Escape),
        ],
        'root': [
            (r'\s+', Text),
            (r'false|true|\(\)|\[\]', Name.Builtin.Pseudo),
            (r'\b([A-Z][\w\']*)(?=\s*\.)', Name.Namespace, 'dotted'),
            (r'\b([A-Z][\w\']*)', Name.Class),
            (r'\(\*(?![)])', Comment, 'comment'),
            (r'\b({})\b'.format('|'.join(keywords)), Keyword),
            (r'({})'.format('|'.join(keyopts[::-1])), Operator),
            (rf'({infix_syms}|{prefix_syms})?{operators}', Operator),
            (r'\b({})\b'.format('|'.join(word_operators)), Operator.Word),
            (r'\b({})\b'.format('|'.join(primitives)), Keyword.Type),

            (r"[^\W\d][\w']*", Name),

            (r'-?\d[\d_]*(.[\d_]*)?([eE][+\-]?\d[\d_]*)', Number.Float),
            (r'0[xX][\da-fA-F][\da-fA-F_]*', Number.Hex),
            (r'0[oO][0-7][0-7_]*', Number.Oct),
            (r'0[bB][01][01_]*', Number.Bin),
            (r'\d[\d_]*', Number.Integer),

            (r"'(?:(\\[\\\"'ntbr ])|(\\[0-9]{3})|(\\x[0-9a-fA-F]{2}))'",
             String.Char),
            (r"'.'", String.Char),
            (r"'", Keyword),  # a stray quote is another syntax element

            (r'"', String.Double, 'string'),

            (r'[~?][a-z][\w\']*:', Name.Variable),
        ],
        'comment': [
            (r'[^(*)]+', Comment),
            (r'\(\*', Comment, '#push'),
            (r'\*\)', Comment, '#pop'),
            (r'[(*)]', Comment),
        ],
        'string': [
            (r'[^\\"]+', String.Double),
            include('escape-sequence'),
            (r'\\\n', String.Double),
            (r'"', String.Double, '#pop'),
        ],
        'dotted': [
            (r'\s+', Text),
            (r'\.', Punctuation),
            (r'[A-Z][\w\']*(?=\s*\.)', Name.Namespace),
            (r'[A-Z][\w\']*', Name.Class, '#pop'),
            (r'[a-z_][\w\']*', Name, '#pop'),
            default('#pop'),
        ],
    }


class OpaLexer(RegexLexer):
    """
    Lexer for the Opa language.
    """

    name = 'Opa'
    aliases = ['opa']
    filenames = ['*.opa']
    mimetypes = ['text/x-opa']
    url = 'http://opalang.org'
    version_added = '1.5'

    # most of these aren't strictly keywords
    # but if you color only real keywords, you might just
    # as well not color anything
    keywords = (
        'and', 'as', 'begin', 'case', 'client', 'css', 'database', 'db', 'do',
        'else', 'end', 'external', 'forall', 'function', 'if', 'import',
        'match', 'module', 'or', 'package', 'parser', 'rec', 'server', 'then',
        'type', 'val', 'with', 'xml_parser',
    )

    # matches both stuff and `stuff`
    ident_re = r'(([a-zA-Z_]\w*)|(`[^`]*`))'

    op_re = r'[.=\-<>,@~%/+?*&^!]'
    punc_re = r'[()\[\],;|]'  # '{' and '}' are treated elsewhere
                              # because they are also used for inserts

    tokens = {
        # copied from the caml lexer, should be adapted
        'escape-sequence': [
            (r'\\[\\"\'ntr}]', String.Escape),
            (r'\\[0-9]{3}', String.Escape),
            (r'\\x[0-9a-fA-F]{2}', String.Escape),
        ],

        # factorizing these rules, because they are inserted many times
        'comments': [
            (r'/\*', Comment, 'nested-comment'),
            (r'//.*?$', Comment),
        ],
        'comments-and-spaces': [
            include('comments'),
            (r'\s+', Text),
        ],

        'root': [
            include('comments-and-spaces'),
            # keywords
            (words(keywords, prefix=r'\b', suffix=r'\b'), Keyword),
            # directives
            # we could parse the actual set of directives instead of anything
            # starting with @, but this is troublesome
            # because it needs to be adjusted all the time
            # and assuming we parse only sources that compile, it is useless
            (r'@' + ident_re + r'\b', Name.Builtin.Pseudo),

            # number literals
            (r'-?.[\d]+([eE][+\-]?\d+)', Number.Float),
            (r'-?\d+.\d*([eE][+\-]?\d+)', Number.Float),
            (r'-?\d+[eE][+\-]?\d+', Number.Float),
            (r'0[xX][\da-fA-F]+', Number.Hex),
            (r'0[oO][0-7]+', Number.Oct),
            (r'0[bB][01]+', Number.Bin),
            (r'\d+', Number.Integer),
            # color literals
            (r'#[\da-fA-F]{3,6}', Number.Integer),

            # string literals
            (r'"', String.Double, 'string'),
            # char literal, should be checked because this is the regexp from
            # the caml lexer
            (r"'(?:(\\[\\\"'ntbr ])|(\\[0-9]{3})|(\\x[0-9a-fA-F]{2})|.)'",
             String.Char),

            # this is meant to deal with embedded exprs in strings
            # every time we find a '}' we pop a state so that if we were
            # inside a string, we are back in the string state
            # as a consequence, we must also push a state every time we find a
            # '{' or else we will have errors when parsing {} for instance
            (r'\{', Operator, '#push'),
            (r'\}', Operator, '#pop'),

            # html literals
            # this is a much more strict that the actual parser,
            # since a<b would not be parsed as html
            # but then again, the parser is way too lax, and we can't hope
            # to have something as tolerant
            (r'<(?=[a-zA-Z>])', String.Single, 'html-open-tag'),

            # db path
            # matching the '[_]' in '/a[_]' because it is a part
            # of the syntax of the db path definition
            # unfortunately, i don't know how to match the ']' in
            # /a[1], so this is somewhat inconsistent
            (r'[@?!]?(/\w+)+(\[_\])?', Name.Variable),
            # putting the same color on <- as on db path, since
            # it can be used only to mean Db.write
            (r'<-(?!'+op_re+r')', Name.Variable),

            # 'modules'
            # although modules are not distinguished by their names as in caml
            # the standard library seems to follow the convention that modules
            # only area capitalized
            (r'\b([A-Z]\w*)(?=\.)', Name.Namespace),

            # operators
            # = has a special role because this is the only
            # way to syntactic distinguish binding constructions
            # unfortunately, this colors the equal in {x=2} too
            (r'=(?!'+op_re+r')', Keyword),
            (rf'({op_re})+', Operator),
            (rf'({punc_re})+', Operator),

            # coercions
            (r':', Operator, 'type'),
            # type variables
            # we need this rule because we don't parse specially type
            # definitions so in "type t('a) = ...", "'a" is parsed by 'root'
            ("'"+ident_re, Keyword.Type),

            # id literal, #something, or #{expr}
            (r'#'+ident_re, String.Single),
            (r'#(?=\{)', String.Single),

            # identifiers
            # this avoids to color '2' in 'a2' as an integer
            (ident_re, Text),

            # default, not sure if that is needed or not
            # (r'.', Text),
        ],

        # it is quite painful to have to parse types to know where they end
        # this is the general rule for a type
        # a type is either:
        # * -> ty
        # * type-with-slash
        # * type-with-slash -> ty
        # * type-with-slash (, type-with-slash)+ -> ty
        #
        # the code is pretty funky in here, but this code would roughly
        # translate in caml to:
        # let rec type stream =
        # match stream with
        # | [< "->";  stream >] -> type stream
        # | [< "";  stream >] ->
        #   type_with_slash stream
        #   type_lhs_1 stream;
        # and type_1 stream = ...
        'type': [
            include('comments-and-spaces'),
            (r'->', Keyword.Type),
            default(('#pop', 'type-lhs-1', 'type-with-slash')),
        ],

        # parses all the atomic or closed constructions in the syntax of type
        # expressions: record types, tuple types, type constructors, basic type
        # and type variables
        'type-1': [
            include('comments-and-spaces'),
            (r'\(', Keyword.Type, ('#pop', 'type-tuple')),
            (r'~?\{', Keyword.Type, ('#pop', 'type-record')),
            (ident_re+r'\(', Keyword.Type, ('#pop', 'type-tuple')),
            (ident_re, Keyword.Type, '#pop'),
            ("'"+ident_re, Keyword.Type),
            # this case is not in the syntax but sometimes
            # we think we are parsing types when in fact we are parsing
            # some css, so we just pop the states until we get back into
            # the root state
            default('#pop'),
        ],

        # type-with-slash is either:
        # * type-1
        # * type-1 (/ type-1)+
        'type-with-slash': [
            include('comments-and-spaces'),
            default(('#pop', 'slash-type-1', 'type-1')),
        ],
        'slash-type-1': [
            include('comments-and-spaces'),
            ('/', Keyword.Type, ('#pop', 'type-1')),
            # same remark as above
            default('#pop'),
        ],

        # we go in this state after having parsed a type-with-slash
        # while trying to parse a type
        # and at this point we must determine if we are parsing an arrow
        # type (in which case we must continue parsing) or not (in which
        # case we stop)
        'type-lhs-1': [
            include('comments-and-spaces'),
            (r'->', Keyword.Type, ('#pop', 'type')),
            (r'(?=,)', Keyword.Type, ('#pop', 'type-arrow')),
            default('#pop'),
        ],
        'type-arrow': [
            include('comments-and-spaces'),
            # the look ahead here allows to parse f(x : int, y : float -> truc)
            # correctly
            (r',(?=[^:]*?->)', Keyword.Type, 'type-with-slash'),
            (r'->', Keyword.Type, ('#pop', 'type')),
            # same remark as above
            default('#pop'),
        ],

        # no need to do precise parsing for tuples and records
        # because they are closed constructions, so we can simply
        # find the closing delimiter
        # note that this function would be not work if the source
        # contained identifiers like `{)` (although it could be patched
        # to support it)
        'type-tuple': [
            include('comments-and-spaces'),
            (r'[^()/*]+', Keyword.Type),
            (r'[/*]', Keyword.Type),
            (r'\(', Keyword.Type, '#push'),
            (r'\)', Keyword.Type, '#pop'),
        ],
        'type-record': [
            include('comments-and-spaces'),
            (r'[^{}/*]+', Keyword.Type),
            (r'[/*]', Keyword.Type),
            (r'\{', Keyword.Type, '#push'),
            (r'\}', Keyword.Type, '#pop'),
        ],

        # 'type-tuple': [
        #     include('comments-and-spaces'),
        #     (r'\)', Keyword.Type, '#pop'),
        #     default(('#pop', 'type-tuple-1', 'type-1')),
        # ],
        # 'type-tuple-1': [
        #     include('comments-and-spaces'),
        #     (r',?\s*\)', Keyword.Type, '#pop'), # ,) is a valid end of tuple, in (1,)
        #     (r',', Keyword.Type, 'type-1'),
        # ],
        # 'type-record':[
        #     include('comments-and-spaces'),
        #     (r'\}', Keyword.Type, '#pop'),
        #     (r'~?(?:\w+|`[^`]*`)', Keyword.Type, 'type-record-field-expr'),
        # ],
        # 'type-record-field-expr': [
        #
        # ],

        'nested-comment': [
            (r'[^/*]+', Comment),
            (r'/\*', Comment, '#push'),
            (r'\*/', Comment, '#pop'),
            (r'[/*]', Comment),
        ],

        # the copy pasting between string and single-string
        # is kinda sad. Is there a way to avoid that??
        'string': [
            (r'[^\\"{]+', String.Double),
            (r'"', String.Double, '#pop'),
            (r'\{', Operator, 'root'),
            include('escape-sequence'),
        ],
        'single-string': [
            (r'[^\\\'{]+', String.Double),
            (r'\'', String.Double, '#pop'),
            (r'\{', Operator, 'root'),
            include('escape-sequence'),
        ],

        # all the html stuff
        # can't really reuse some existing html parser
        # because we must be able to parse embedded expressions

        # we are in this state after someone parsed the '<' that
        # started the html literal
        'html-open-tag': [
            (r'[\w\-:]+', String.Single, ('#pop', 'html-attr')),
            (r'>', String.Single, ('#pop', 'html-content')),
        ],

        # we are in this state after someone parsed the '</' that
        # started the end of the closing tag
        'html-end-tag': [
            # this is a star, because </> is allowed
            (r'[\w\-:]*>', String.Single, '#pop'),
        ],

        # we are in this state after having parsed '<ident(:ident)?'
        # we thus parse a possibly empty list of attributes
        'html-attr': [
            (r'\s+', Text),
            (r'[\w\-:]+=', String.Single, 'html-attr-value'),
            (r'/>', String.Single, '#pop'),
            (r'>', String.Single, ('#pop', 'html-content')),
        ],

        'html-attr-value': [
            (r"'", String.Single, ('#pop', 'single-string')),
            (r'"', String.Single, ('#pop', 'string')),
            (r'#'+ident_re, String.Single, '#pop'),
            (r'#(?=\{)', String.Single, ('#pop', 'root')),
            (r'[^"\'{`=<>]+', String.Single, '#pop'),
            (r'\{', Operator, ('#pop', 'root')),  # this is a tail call!
        ],

        # we should probably deal with '\' escapes here
        'html-content': [
            (r'<!--', Comment, 'html-comment'),
            (r'</', String.Single, ('#pop', 'html-end-tag')),
            (r'<', String.Single, 'html-open-tag'),
            (r'\{', Operator, 'root'),
            (r'[^<{]+', String.Single),
        ],

        'html-comment': [
            (r'-->', Comment, '#pop'),
            (r'[^\-]+|-', Comment),
        ],
    }


class ReasonLexer(RegexLexer):
    """
    For the ReasonML language.
    """

    name = 'ReasonML'
    url = 'https://reasonml.github.io/'
    aliases = ['reasonml', 'reason']
    filenames = ['*.re', '*.rei']
    mimetypes = ['text/x-reasonml']
    version_added = '2.6'

    keywords = (
        'as', 'assert', 'begin', 'class', 'constraint', 'do', 'done', 'downto',
        'else', 'end', 'exception', 'external', 'false', 'for', 'fun', 'esfun',
        'function', 'functor', 'if', 'in', 'include', 'inherit', 'initializer', 'lazy',
        'let', 'switch', 'module', 'pub', 'mutable', 'new', 'nonrec', 'object', 'of',
        'open', 'pri', 'rec', 'sig', 'struct', 'then', 'to', 'true', 'try',
        'type', 'val', 'virtual', 'when', 'while', 'with',
    )
    keyopts = (
        '!=', '#', '&', '&&', r'\(', r'\)', r'\*', r'\+', ',', '-',
        r'-\.', '=>', r'\.', r'\.\.', r'\.\.\.', ':', '::', ':=', ':>', ';', ';;', '<',
        '<-', '=', '>', '>]', r'>\}', r'\?', r'\?\?', r'\[', r'\[<', r'\[>',
        r'\[\|', ']', '_', '`', r'\{', r'\{<', r'\|', r'\|\|', r'\|]', r'\}', '~'
    )

    operators = r'[!$%&*+\./:<=>?@^|~-]'
    word_operators = ('and', 'asr', 'land', 'lor', 'lsl', 'lsr', 'lxor', 'mod', 'or')
    prefix_syms = r'[!?~]'
    infix_syms = r'[=<>@^|&+\*/$%-]'
    primitives = ('unit', 'int', 'float', 'bool', 'string', 'char', 'list', 'array')

    tokens = {
        'escape-sequence': [
            (r'\\[\\"\'ntbr]', String.Escape),
            (r'\\[0-9]{3}', String.Escape),
            (r'\\x[0-9a-fA-F]{2}', String.Escape),
        ],
        'root': [
            (r'\s+', Text),
            (r'false|true|\(\)|\[\]', Name.Builtin.Pseudo),
            (r'\b([A-Z][\w\']*)(?=\s*\.)', Name.Namespace, 'dotted'),
            (r'\b([A-Z][\w\']*)', Name.Class),
            (r'//.*?\n', Comment.Single),
            (r'\/\*(?!/)', Comment.Multiline, 'comment'),
            (r'\b({})\b'.format('|'.join(keywords)), Keyword),
            (r'({})'.format('|'.join(keyopts[::-1])), Operator.Word),
            (rf'({infix_syms}|{prefix_syms})?{operators}', Operator),
            (r'\b({})\b'.format('|'.join(word_operators)), Operator.Word),
            (r'\b({})\b'.format('|'.join(primitives)), Keyword.Type),

            (r"[^\W\d][\w']*", Name),

            (r'-?\d[\d_]*(.[\d_]*)?([eE][+\-]?\d[\d_]*)', Number.Float),
            (r'0[xX][\da-fA-F][\da-fA-F_]*', Number.Hex),
            (r'0[oO][0-7][0-7_]*', Number.Oct),
            (r'0[bB][01][01_]*', Number.Bin),
            (r'\d[\d_]*', Number.Integer),

            (r"'(?:(\\[\\\"'ntbr ])|(\\[0-9]{3})|(\\x[0-9a-fA-F]{2}))'",
             String.Char),
            (r"'.'", String.Char),
            (r"'", Keyword),

            (r'"', String.Double, 'string'),

            (r'[~?][a-z][\w\']*:', Name.Variable),
        ],
        'comment': [
            (r'[^/*]+', Comment.Multiline),
            (r'\/\*', Comment.Multiline, '#push'),
            (r'\*\/', Comment.Multiline, '#pop'),
            (r'\*', Comment.Multiline),
        ],
        'string': [
            (r'[^\\"]+', String.Double),
            include('escape-sequence'),
            (r'\\\n', String.Double),
            (r'"', String.Double, '#pop'),
        ],
        'dotted': [
            (r'\s+', Text),
            (r'\.', Punctuation),
            (r'[A-Z][\w\']*(?=\s*\.)', Name.Namespace),
            (r'[A-Z][\w\']*', Name.Class, '#pop'),
            (r'[a-z_][\w\']*', Name, '#pop'),
            default('#pop'),
        ],
    }


class FStarLexer(RegexLexer):
    """
    For the F* language.
    """

    name = 'FStar'
    url = 'https://www.fstar-lang.org/'
    aliases = ['fstar']
    filenames = ['*.fst', '*.fsti']
    mimetypes = ['text/x-fstar']
    version_added = '2.7'

    keywords = (
        'abstract', 'attributes', 'noeq', 'unopteq', 'and'
        'begin', 'by', 'default', 'effect', 'else', 'end', 'ensures',
        'exception', 'exists', 'false', 'forall', 'fun', 'function', 'if',
        'in', 'include', 'inline', 'inline_for_extraction', 'irreducible',
        'logic', 'match', 'module', 'mutable', 'new', 'new_effect', 'noextract',
        'of', 'open', 'opaque', 'private', 'range_of', 'reifiable',
        'reify', 'reflectable', 'requires', 'set_range_of', 'sub_effect',
        'synth', 'then', 'total', 'true', 'try', 'type', 'unfold', 'unfoldable',
        'val', 'when', 'with', 'not'
    )
    decl_keywords = ('let', 'rec')
    assume_keywords = ('assume', 'admit', 'assert', 'calc')
    keyopts = (
        r'~', r'-', r'/\\', r'\\/', r'<:', r'<@', r'\(\|', r'\|\)', r'#', r'u#',
        r'&', r'\(', r'\)', r'\(\)', r',', r'~>', r'->', r'<-', r'<--', r'<==>',
        r'==>', r'\.', r'\?', r'\?\.', r'\.\[', r'\.\(', r'\.\(\|', r'\.\[\|',
        r'\{:pattern', r':', r'::', r':=', r';', r';;', r'=', r'%\[', r'!\{',
        r'\[', r'\[@', r'\[\|', r'\|>', r'\]', r'\|\]', r'\{', r'\|', r'\}', r'\$'
    )

    operators = r'[!$%&*+\./:<=>?@^|~-]'
    prefix_syms = r'[!?~]'
    infix_syms = r'[=<>@^|&+\*/$%-]'
    primitives = ('unit', 'int', 'float', 'bool', 'string', 'char', 'list', 'array')

    tokens = {
        'escape-sequence': [
            (r'\\[\\"\'ntbr]', String.Escape),
            (r'\\[0-9]{3}', String.Escape),
            (r'\\x[0-9a-fA-F]{2}', String.Escape),
        ],
        'root': [
            (r'\s+', Text),
            (r'false|true|False|True|\(\)|\[\]', Name.Builtin.Pseudo),
            (r'\b([A-Z][\w\']*)(?=\s*\.)', Name.Namespace, 'dotted'),
            (r'\b([A-Z][\w\']*)', Name.Class),
            (r'\(\*(?![)])', Comment, 'comment'),
            (r'\/\/.+$', Comment),
            (r'\b({})\b'.format('|'.join(keywords)), Keyword),
            (r'\b({})\b'.format('|'.join(assume_keywords)), Name.Exception),
            (r'\b({})\b'.format('|'.join(decl_keywords)), Keyword.Declaration),
            (r'({})'.format('|'.join(keyopts[::-1])), Operator),
            (rf'({infix_syms}|{prefix_syms})?{operators}', Operator),
            (r'\b({})\b'.format('|'.join(primitives)), Keyword.Type),

            (r"[^\W\d][\w']*", Name),

            (r'-?\d[\d_]*(.[\d_]*)?([eE][+\-]?\d[\d_]*)', Number.Float),
            (r'0[xX][\da-fA-F][\da-fA-F_]*', Number.Hex),
            (r'0[oO][0-7][0-7_]*', Number.Oct),
            (r'0[bB][01][01_]*', Number.Bin),
            (r'\d[\d_]*', Number.Integer),

            (r"'(?:(\\[\\\"'ntbr ])|(\\[0-9]{3})|(\\x[0-9a-fA-F]{2}))'",
             String.Char),
            (r"'.'", String.Char),
            (r"'", Keyword),  # a stray quote is another syntax element
            (r"\`([\w\'.]+)\`", Operator.Word),  # for infix applications
            (r"\`", Keyword),  # for quoting
            (r'"', String.Double, 'string'),

            (r'[~?][a-z][\w\']*:', Name.Variable),
        ],
        'comment': [
            (r'[^(*)]+', Comment),
            (r'\(\*', Comment, '#push'),
            (r'\*\)', Comment, '#pop'),
            (r'[(*)]', Comment),
        ],
        'string': [
            (r'[^\\"]+', String.Double),
            include('escape-sequence'),
            (r'\\\n', String.Double),
            (r'"', String.Double, '#pop'),
        ],
        'dotted': [
            (r'\s+', Text),
            (r'\.', Punctuation),
            (r'[A-Z][\w\']*(?=\s*\.)', Name.Namespace),
            (r'[A-Z][\w\']*', Name.Class, '#pop'),
            (r'[a-z_][\w\']*', Name, '#pop'),
            default('#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\tornado\test\httpclient_test.py ===
import base64
import binascii
from contextlib import closing
import copy
import gzip
import threading
import datetime
from io import BytesIO
import subprocess
import sys
import time
import typing  # noqa: F401
import unicodedata
import unittest

from tornado.escape import utf8, native_str, to_unicode
from tornado import gen
from tornado.httpclient import (
    HTTPRequest,
    HTTPResponse,
    _RequestProxy,
    HTTPError,
    HTTPClient,
)
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.log import gen_log, app_log
from tornado import netutil
from tornado.testing import AsyncHTTPTestCase, bind_unused_port, gen_test, ExpectLog
from tornado.test.util import ignore_deprecation
from tornado.web import Application, RequestHandler, url
from tornado.httputil import format_timestamp, HTTPHeaders


class HelloWorldHandler(RequestHandler):
    def get(self):
        name = self.get_argument("name", "world")
        self.set_header("Content-Type", "text/plain")
        self.finish("Hello %s!" % name)


class PostHandler(RequestHandler):
    def post(self):
        self.finish(
            "Post arg1: %s, arg2: %s"
            % (self.get_argument("arg1"), self.get_argument("arg2"))
        )


class PutHandler(RequestHandler):
    def put(self):
        self.write("Put body: ")
        self.write(self.request.body)


class RedirectHandler(RequestHandler):
    def prepare(self):
        self.write("redirects can have bodies too")
        self.redirect(
            self.get_argument("url"), status=int(self.get_argument("status", "302"))
        )


class RedirectWithoutLocationHandler(RequestHandler):
    def prepare(self):
        # For testing error handling of a redirect with no location header.
        self.set_status(301)
        self.finish()


class ChunkHandler(RequestHandler):
    @gen.coroutine
    def get(self):
        self.write("asdf")
        self.flush()
        # Wait a bit to ensure the chunks are sent and received separately.
        yield gen.sleep(0.01)
        self.write("qwer")


class AuthHandler(RequestHandler):
    def get(self):
        self.finish(self.request.headers["Authorization"])


class CountdownHandler(RequestHandler):
    def get(self, count):
        count = int(count)
        if count > 0:
            self.redirect(self.reverse_url("countdown", count - 1))
        else:
            self.write("Zero")


class EchoPostHandler(RequestHandler):
    def post(self):
        self.write(self.request.body)


class UserAgentHandler(RequestHandler):
    def get(self):
        self.write(self.request.headers.get("User-Agent", "User agent not set"))


class ContentLength304Handler(RequestHandler):
    def get(self):
        self.set_status(304)
        self.set_header("Content-Length", 42)

    def _clear_representation_headers(self):
        # Tornado strips content-length from 304 responses, but here we
        # want to simulate servers that include the headers anyway.
        pass


class PatchHandler(RequestHandler):
    def patch(self):
        "Return the request payload - so we can check it is being kept"
        self.write(self.request.body)


class AllMethodsHandler(RequestHandler):
    SUPPORTED_METHODS = RequestHandler.SUPPORTED_METHODS + ("OTHER",)  # type: ignore

    def method(self):
        assert self.request.method is not None
        self.write(self.request.method)

    get = head = post = put = delete = options = patch = other = method  # type: ignore


class SetHeaderHandler(RequestHandler):
    def get(self):
        # Use get_arguments for keys to get strings, but
        # request.arguments for values to get bytes.
        for k, v in zip(self.get_arguments("k"), self.request.arguments["v"]):
            self.set_header(k, v)


class InvalidGzipHandler(RequestHandler):
    def get(self) -> None:
        # set Content-Encoding manually to avoid automatic gzip encoding
        self.set_header("Content-Type", "text/plain")
        self.set_header("Content-Encoding", "gzip")
        # Triggering the potential bug seems to depend on input length.
        # This length is taken from the bad-response example reported in
        # https://github.com/tornadoweb/tornado/pull/2875 (uncompressed).
        text = "".join(f"Hello World {i}\n" for i in range(9000))[:149051]
        body = gzip.compress(text.encode(), compresslevel=6) + b"\00"
        self.write(body)


class HeaderEncodingHandler(RequestHandler):
    def get(self):
        self.finish(self.request.headers["Foo"].encode("ISO8859-1"))


# These tests end up getting run redundantly: once here with the default
# HTTPClient implementation, and then again in each implementation's own
# test suite.


class HTTPClientCommonTestCase(AsyncHTTPTestCase):
    def get_app(self):
        return Application(
            [
                url("/hello", HelloWorldHandler),
                url("/post", PostHandler),
                url("/put", PutHandler),
                url("/redirect", RedirectHandler),
                url("/redirect_without_location", RedirectWithoutLocationHandler),
                url("/chunk", ChunkHandler),
                url("/auth", AuthHandler),
                url("/countdown/([0-9]+)", CountdownHandler, name="countdown"),
                url("/echopost", EchoPostHandler),
                url("/user_agent", UserAgentHandler),
                url("/304_with_content_length", ContentLength304Handler),
                url("/all_methods", AllMethodsHandler),
                url("/patch", PatchHandler),
                url("/set_header", SetHeaderHandler),
                url("/invalid_gzip", InvalidGzipHandler),
                url("/header-encoding", HeaderEncodingHandler),
            ],
            gzip=True,
        )

    def test_patch_receives_payload(self):
        body = b"some patch data"
        response = self.fetch("/patch", method="PATCH", body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, body)

    def test_hello_world(self):
        response = self.fetch("/hello")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/plain")
        self.assertEqual(response.body, b"Hello world!")
        assert response.request_time is not None
        self.assertEqual(int(response.request_time), 0)

        response = self.fetch("/hello?name=Ben")
        self.assertEqual(response.body, b"Hello Ben!")

    def test_streaming_callback(self):
        # streaming_callback is also tested in test_chunked
        chunks = []  # type: typing.List[bytes]
        response = self.fetch("/hello", streaming_callback=chunks.append)
        # with streaming_callback, data goes to the callback and not response.body
        self.assertEqual(chunks, [b"Hello world!"])
        self.assertFalse(response.body)

    def test_post(self):
        response = self.fetch("/post", method="POST", body="arg1=foo&arg2=bar")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b"Post arg1: foo, arg2: bar")

    def test_chunked(self):
        response = self.fetch("/chunk")
        self.assertEqual(response.body, b"asdfqwer")

        chunks = []  # type: typing.List[bytes]
        response = self.fetch("/chunk", streaming_callback=chunks.append)
        self.assertEqual(chunks, [b"asdf", b"qwer"])
        self.assertFalse(response.body)

    def test_chunked_close(self):
        # test case in which chunks spread read-callback processing
        # over several ioloop iterations, but the connection is already closed.
        sock, port = bind_unused_port()
        with closing(sock):

            @gen.coroutine
            def accept_callback(conn, address):
                # fake an HTTP server using chunked encoding where the final chunks
                # and connection close all happen at once
                stream = IOStream(conn)
                request_data = yield stream.read_until(b"\r\n\r\n")
                if b"HTTP/1." not in request_data:
                    self.skipTest("requires HTTP/1.x")
                yield stream.write(
                    b"""\
HTTP/1.1 200 OK
Transfer-Encoding: chunked

1
1
1
2
0

""".replace(
                        b"\n", b"\r\n"
                    )
                )
                stream.close()

            netutil.add_accept_handler(sock, accept_callback)  # type: ignore
            resp = self.fetch("http://127.0.0.1:%d/" % port)
            resp.rethrow()
            self.assertEqual(resp.body, b"12")
            self.io_loop.remove_handler(sock.fileno())

    def test_basic_auth(self):
        # This test data appears in section 2 of RFC 7617.
        self.assertEqual(
            self.fetch(
                "/auth", auth_username="Aladdin", auth_password="open sesame"
            ).body,
            b"Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==",
        )

    def test_basic_auth_explicit_mode(self):
        self.assertEqual(
            self.fetch(
                "/auth",
                auth_username="Aladdin",
                auth_password="open sesame",
                auth_mode="basic",
            ).body,
            b"Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==",
        )

    def test_basic_auth_unicode(self):
        # This test data appears in section 2.1 of RFC 7617.
        self.assertEqual(
            self.fetch("/auth", auth_username="test", auth_password="123£").body,
            b"Basic dGVzdDoxMjPCow==",
        )

        # The standard mandates NFC. Give it a decomposed username
        # and ensure it is normalized to composed form.
        username = unicodedata.normalize("NFD", "josé")
        self.assertEqual(
            self.fetch("/auth", auth_username=username, auth_password="səcrət").body,
            b"Basic am9zw6k6c8mZY3LJmXQ=",
        )

    def test_unsupported_auth_mode(self):
        # curl and simple clients handle errors a bit differently; the
        # important thing is that they don't fall back to basic auth
        # on an unknown mode.
        with ExpectLog(gen_log, "uncaught exception", required=False):
            with self.assertRaises((ValueError, HTTPError)):  # type: ignore
                self.fetch(
                    "/auth",
                    auth_username="Aladdin",
                    auth_password="open sesame",
                    auth_mode="asdf",
                    raise_error=True,
                )

    def test_follow_redirect(self):
        response = self.fetch("/countdown/2", follow_redirects=False)
        self.assertEqual(302, response.code)
        self.assertTrue(response.headers["Location"].endswith("/countdown/1"))

        response = self.fetch("/countdown/2")
        self.assertEqual(200, response.code)
        self.assertTrue(response.effective_url.endswith("/countdown/0"))
        self.assertEqual(b"Zero", response.body)

    def test_redirect_without_location(self):
        response = self.fetch("/redirect_without_location", follow_redirects=True)
        # If there is no location header, the redirect response should
        # just be returned as-is. (This should arguably raise an
        # error, but libcurl doesn't treat this as an error, so we
        # don't either).
        self.assertEqual(301, response.code)

    def test_redirect_put_with_body(self):
        response = self.fetch(
            "/redirect?url=/put&status=307", method="PUT", body="hello"
        )
        self.assertEqual(response.body, b"Put body: hello")

    def test_redirect_put_without_body(self):
        # This "without body" edge case is similar to what happens with body_producer.
        response = self.fetch(
            "/redirect?url=/put&status=307",
            method="PUT",
            allow_nonstandard_methods=True,
        )
        self.assertEqual(response.body, b"Put body: ")

    def test_method_after_redirect(self):
        # Legacy redirect codes (301, 302) convert POST requests to GET.
        for status in [301, 302, 303]:
            url = "/redirect?url=/all_methods&status=%d" % status
            resp = self.fetch(url, method="POST", body=b"")
            self.assertEqual(b"GET", resp.body)

            # Other methods are left alone, except for 303 redirect, depending on client
            for method in ["GET", "OPTIONS", "PUT", "DELETE"]:
                resp = self.fetch(url, method=method, allow_nonstandard_methods=True)
                if status in [301, 302]:
                    self.assertEqual(utf8(method), resp.body)
                else:
                    self.assertIn(resp.body, [utf8(method), b"GET"])

            # HEAD is different so check it separately.
            resp = self.fetch(url, method="HEAD")
            self.assertEqual(200, resp.code)
            self.assertEqual(b"", resp.body)

        # Newer redirects always preserve the original method.
        for status in [307, 308]:
            url = "/redirect?url=/all_methods&status=307"
            for method in ["GET", "OPTIONS", "POST", "PUT", "DELETE"]:
                resp = self.fetch(url, method=method, allow_nonstandard_methods=True)
                self.assertEqual(method, to_unicode(resp.body))
            resp = self.fetch(url, method="HEAD")
            self.assertEqual(200, resp.code)
            self.assertEqual(b"", resp.body)

    def test_credentials_in_url(self):
        url = self.get_url("/auth").replace("http://", "http://me:secret@")
        response = self.fetch(url)
        self.assertEqual(b"Basic " + base64.b64encode(b"me:secret"), response.body)

    def test_body_encoding(self):
        unicode_body = "\xe9"
        byte_body = binascii.a2b_hex(b"e9")

        # unicode string in body gets converted to utf8
        response = self.fetch(
            "/echopost",
            method="POST",
            body=unicode_body,
            headers={"Content-Type": "application/blah"},
        )
        self.assertEqual(response.headers["Content-Length"], "2")
        self.assertEqual(response.body, utf8(unicode_body))

        # byte strings pass through directly
        response = self.fetch(
            "/echopost",
            method="POST",
            body=byte_body,
            headers={"Content-Type": "application/blah"},
        )
        self.assertEqual(response.headers["Content-Length"], "1")
        self.assertEqual(response.body, byte_body)

        # Mixing unicode in headers and byte string bodies shouldn't
        # break anything
        response = self.fetch(
            "/echopost",
            method="POST",
            body=byte_body,
            headers={"Content-Type": "application/blah"},
            user_agent="foo",
        )
        self.assertEqual(response.headers["Content-Length"], "1")
        self.assertEqual(response.body, byte_body)

    def test_types(self):
        response = self.fetch("/hello")
        self.assertEqual(type(response.body), bytes)
        self.assertEqual(type(response.headers["Content-Type"]), str)
        self.assertEqual(type(response.code), int)
        self.assertEqual(type(response.effective_url), str)

    def test_gzip(self):
        # All the tests in this file should be using gzip, but this test
        # ensures that it is in fact getting compressed, and also tests
        # the httpclient's decompress=False option.
        # Setting Accept-Encoding manually bypasses the client's
        # decompression so we can see the raw data.
        response = self.fetch(
            "/chunk", decompress_response=False, headers={"Accept-Encoding": "gzip"}
        )
        self.assertEqual(response.headers["Content-Encoding"], "gzip")
        self.assertNotEqual(response.body, b"asdfqwer")
        # Our test data gets bigger when gzipped.  Oops.  :)
        # Chunked encoding bypasses the MIN_LENGTH check.
        self.assertEqual(len(response.body), 34)
        f = gzip.GzipFile(mode="r", fileobj=response.buffer)
        self.assertEqual(f.read(), b"asdfqwer")

    def test_invalid_gzip(self):
        # test if client hangs on tricky invalid gzip
        # curl/simple httpclient have different behavior (exception, logging)
        with ExpectLog(
            app_log, "(Uncaught exception|Exception in callback)", required=False
        ):
            try:
                response = self.fetch("/invalid_gzip")
                self.assertEqual(response.code, 200)
                self.assertEqual(response.body[:14], b"Hello World 0\n")
            except HTTPError:
                pass  # acceptable

    def test_header_callback(self):
        first_line = []
        headers = {}
        chunks = []

        def header_callback(header_line):
            if header_line.startswith("HTTP/1.1 101"):
                # Upgrading to HTTP/2
                pass
            elif header_line.startswith("HTTP/"):
                first_line.append(header_line)
            elif header_line != "\r\n":
                k, v = header_line.split(":", 1)
                headers[k.lower()] = v.strip()

        def streaming_callback(chunk):
            # All header callbacks are run before any streaming callbacks,
            # so the header data is available to process the data as it
            # comes in.
            self.assertEqual(headers["content-type"], "text/html; charset=UTF-8")
            chunks.append(chunk)

        self.fetch(
            "/chunk",
            header_callback=header_callback,
            streaming_callback=streaming_callback,
        )
        self.assertEqual(len(first_line), 1, first_line)
        self.assertRegex(first_line[0], "HTTP/[0-9]\\.[0-9] 200.*\r\n")
        self.assertEqual(chunks, [b"asdf", b"qwer"])

    def test_header_callback_to_parse_line(self):
        # Make a request with header_callback and feed the headers to HTTPHeaders.parse_line.
        # (Instead of HTTPHeaders.parse which is used in normal cases). Ensure that the resulting
        # headers are as expected, and in particular do not have trailing whitespace added
        # due to the final CRLF line.
        headers = HTTPHeaders()

        def header_callback(line):
            if line.startswith("HTTP/"):
                # Ignore the first status line
                return
            headers.parse_line(line)

        self.fetch("/hello", header_callback=header_callback)
        for k, v in headers.get_all():
            self.assertTrue(v == v.strip(), (k, v))

    @gen_test
    def test_configure_defaults(self):
        defaults = dict(user_agent="TestDefaultUserAgent", allow_ipv6=False)
        # Construct a new instance of the configured client class
        client = self.http_client.__class__(force_instance=True, defaults=defaults)
        try:
            response = yield client.fetch(self.get_url("/user_agent"))
            self.assertEqual(response.body, b"TestDefaultUserAgent")
        finally:
            client.close()

    def test_header_types(self):
        # Header values may be passed as character or utf8 byte strings,
        # in a plain dictionary or an HTTPHeaders object.
        # Keys must always be the native str type.
        # All combinations should have the same results on the wire.
        for value in ["MyUserAgent", b"MyUserAgent"]:
            for container in [dict, HTTPHeaders]:
                headers = container()
                headers["User-Agent"] = value
                resp = self.fetch("/user_agent", headers=headers)
                self.assertEqual(
                    resp.body,
                    b"MyUserAgent",
                    "response=%r, value=%r, container=%r"
                    % (resp.body, value, container),
                )

    def test_multi_line_headers(self):
        # Multi-line http headers are rare but rfc-allowed
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.2
        sock, port = bind_unused_port()
        with closing(sock):

            @gen.coroutine
            def accept_callback(conn, address):
                stream = IOStream(conn)
                request_data = yield stream.read_until(b"\r\n\r\n")
                if b"HTTP/1." not in request_data:
                    self.skipTest("requires HTTP/1.x")
                yield stream.write(
                    b"""\
HTTP/1.1 200 OK
X-XSS-Protection: 1;
\tmode=block

""".replace(
                        b"\n", b"\r\n"
                    )
                )
                stream.close()

            netutil.add_accept_handler(sock, accept_callback)  # type: ignore
            try:
                resp = self.fetch("http://127.0.0.1:%d/" % port)
                resp.rethrow()
                self.assertEqual(resp.headers["X-XSS-Protection"], "1; mode=block")
            finally:
                self.io_loop.remove_handler(sock.fileno())

    @gen_test
    def test_header_encoding(self):
        response = yield self.http_client.fetch(
            self.get_url("/header-encoding"),
            headers={
                "Foo": "b\xe4r",
            },
        )
        self.assertEqual(response.body, "b\xe4r".encode("ISO8859-1"))

    def test_304_with_content_length(self):
        # According to the spec 304 responses SHOULD NOT include
        # Content-Length or other entity headers, but some servers do it
        # anyway.
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.3.5
        response = self.fetch("/304_with_content_length")
        self.assertEqual(response.code, 304)
        self.assertEqual(response.headers["Content-Length"], "42")

    @gen_test
    def test_future_interface(self):
        response = yield self.http_client.fetch(self.get_url("/hello"))
        self.assertEqual(response.body, b"Hello world!")

    @gen_test
    def test_future_http_error(self):
        with self.assertRaises(HTTPError) as context:
            yield self.http_client.fetch(self.get_url("/notfound"))
        assert context.exception is not None
        assert context.exception.response is not None
        self.assertEqual(context.exception.code, 404)
        self.assertEqual(context.exception.response.code, 404)

    @gen_test
    def test_future_http_error_no_raise(self):
        response = yield self.http_client.fetch(
            self.get_url("/notfound"), raise_error=False
        )
        self.assertEqual(response.code, 404)

    @gen_test
    def test_reuse_request_from_response(self):
        # The response.request attribute should be an HTTPRequest, not
        # a _RequestProxy.
        # This test uses self.http_client.fetch because self.fetch calls
        # self.get_url on the input unconditionally.
        url = self.get_url("/hello")
        response = yield self.http_client.fetch(url)
        self.assertEqual(response.request.url, url)
        self.assertTrue(isinstance(response.request, HTTPRequest))
        response2 = yield self.http_client.fetch(response.request)
        self.assertEqual(response2.body, b"Hello world!")

    @gen_test
    def test_bind_source_ip(self):
        url = self.get_url("/hello")
        request = HTTPRequest(url, network_interface="127.0.0.1")
        response = yield self.http_client.fetch(request)
        self.assertEqual(response.code, 200)

        with self.assertRaises((ValueError, HTTPError)) as context:  # type: ignore
            request = HTTPRequest(url, network_interface="not-interface-or-ip")
            yield self.http_client.fetch(request)
        self.assertIn("not-interface-or-ip", str(context.exception))

    def test_all_methods(self):
        for method in ["GET", "DELETE", "OPTIONS"]:
            response = self.fetch("/all_methods", method=method)
            self.assertEqual(response.body, utf8(method))
        for method in ["POST", "PUT", "PATCH"]:
            response = self.fetch("/all_methods", method=method, body=b"")
            self.assertEqual(response.body, utf8(method))
        response = self.fetch("/all_methods", method="HEAD")
        self.assertEqual(response.body, b"")
        response = self.fetch(
            "/all_methods", method="OTHER", allow_nonstandard_methods=True
        )
        self.assertEqual(response.body, b"OTHER")

    def test_body_sanity_checks(self):
        # These methods require a body.
        for method in ("POST", "PUT", "PATCH"):
            with self.assertRaises(ValueError) as context:
                self.fetch("/all_methods", method=method, raise_error=True)
            self.assertIn("must not be None", str(context.exception))

            resp = self.fetch(
                "/all_methods", method=method, allow_nonstandard_methods=True
            )
            self.assertEqual(resp.code, 200)

        # These methods don't allow a body.
        for method in ("GET", "DELETE", "OPTIONS"):
            with self.assertRaises(ValueError) as context:
                self.fetch(
                    "/all_methods", method=method, body=b"asdf", raise_error=True
                )
            self.assertIn("must be None", str(context.exception))

            # In most cases this can be overridden, but curl_httpclient
            # does not allow body with a GET at all.
            if method != "GET":
                self.fetch(
                    "/all_methods",
                    method=method,
                    body=b"asdf",
                    allow_nonstandard_methods=True,
                    raise_error=True,
                )
                self.assertEqual(resp.code, 200)

    # This test causes odd failures with the combination of
    # curl_httpclient (at least with the version of libcurl available
    # on ubuntu 12.04), TwistedIOLoop, and epoll.  For POST (but not PUT),
    # curl decides the response came back too soon and closes the connection
    # to start again.  It does this *before* telling the socket callback to
    # unregister the FD.  Some IOLoop implementations have special kernel
    # integration to discover this immediately.  Tornado's IOLoops
    # ignore errors on remove_handler to accommodate this behavior, but
    # Twisted's reactor does not.  The removeReader call fails and so
    # do all future removeAll calls (which our tests do at cleanup).
    #
    # def test_post_307(self):
    #    response = self.fetch("/redirect?status=307&url=/post",
    #                          method="POST", body=b"arg1=foo&arg2=bar")
    #    self.assertEqual(response.body, b"Post arg1: foo, arg2: bar")

    def test_put_307(self):
        response = self.fetch(
            "/redirect?status=307&url=/put", method="PUT", body=b"hello"
        )
        response.rethrow()
        self.assertEqual(response.body, b"Put body: hello")

    def test_non_ascii_header(self):
        # Non-ascii headers are sent as latin1.
        response = self.fetch("/set_header?k=foo&v=%E9")
        response.rethrow()
        self.assertEqual(response.headers["Foo"], native_str("\u00e9"))

    def test_response_times(self):
        # A few simple sanity checks of the response time fields to
        # make sure they're using the right basis (between the
        # wall-time and monotonic clocks).
        start_time = time.time()
        response = self.fetch("/hello")
        response.rethrow()
        self.assertIsNotNone(response.request_time)
        assert response.request_time is not None  # for mypy
        self.assertGreaterEqual(response.request_time, 0)
        self.assertLess(response.request_time, 1.0)
        # A very crude check to make sure that start_time is based on
        # wall time and not the monotonic clock.
        self.assertIsNotNone(response.start_time)
        assert response.start_time is not None  # for mypy
        self.assertLess(abs(response.start_time - start_time), 1.0)

        for k, v in response.time_info.items():
            self.assertTrue(0 <= v < 1.0, f"time_info[{k}] out of bounds: {v}")

    def test_zero_timeout(self):
        response = self.fetch("/hello", connect_timeout=0)
        self.assertEqual(response.code, 200)

        response = self.fetch("/hello", request_timeout=0)
        self.assertEqual(response.code, 200)

        response = self.fetch("/hello", connect_timeout=0, request_timeout=0)
        self.assertEqual(response.code, 200)

    @gen_test
    def test_error_after_cancel(self):
        fut = self.http_client.fetch(self.get_url("/404"))
        self.assertTrue(fut.cancel())
        with ExpectLog(app_log, "Exception after Future was cancelled") as el:
            # We can't wait on the cancelled Future any more, so just
            # let the IOLoop run until the exception gets logged (or
            # not, in which case we exit the loop and ExpectLog will
            # raise).
            for i in range(100):
                yield gen.sleep(0.01)
                if el.logged_stack:
                    break

    def test_header_crlf(self):
        # Ensure that the client doesn't allow CRLF injection in headers. RFC 9112 section 2.2
        # prohibits a bare CR specifically and "a recipient MAY recognize a single LF as a line
        # terminator" so we check each character separately as well as the (redundant) CRLF pair.
        for header, name in [
            ("foo\rbar:", "cr"),
            ("foo\nbar:", "lf"),
            ("foo\r\nbar:", "crlf"),
        ]:
            with self.subTest(name=name, position="value"):
                with self.assertRaises(ValueError):
                    self.fetch("/hello", headers={"foo": header})
            with self.subTest(name=name, position="key"):
                with self.assertRaises(ValueError):
                    self.fetch("/hello", headers={header: "foo"})


class RequestProxyTest(unittest.TestCase):
    def test_request_set(self):
        proxy = _RequestProxy(
            HTTPRequest("http://example.com/", user_agent="foo"), dict()
        )
        self.assertEqual(proxy.user_agent, "foo")

    def test_default_set(self):
        proxy = _RequestProxy(
            HTTPRequest("http://example.com/"), dict(network_interface="foo")
        )
        self.assertEqual(proxy.network_interface, "foo")

    def test_both_set(self):
        proxy = _RequestProxy(
            HTTPRequest("http://example.com/", proxy_host="foo"), dict(proxy_host="bar")
        )
        self.assertEqual(proxy.proxy_host, "foo")

    def test_neither_set(self):
        proxy = _RequestProxy(HTTPRequest("http://example.com/"), dict())
        self.assertIsNone(proxy.auth_username)

    def test_bad_attribute(self):
        proxy = _RequestProxy(HTTPRequest("http://example.com/"), dict())
        with self.assertRaises(AttributeError):
            proxy.foo

    def test_defaults_none(self):
        proxy = _RequestProxy(HTTPRequest("http://example.com/"), None)
        self.assertIsNone(proxy.auth_username)


class HTTPResponseTestCase(unittest.TestCase):
    def test_str(self):
        response = HTTPResponse(  # type: ignore
            HTTPRequest("http://example.com"), 200, buffer=BytesIO()
        )
        s = str(response)
        self.assertTrue(s.startswith("HTTPResponse("))
        self.assertIn("code=200", s)


class SyncHTTPClientTest(unittest.TestCase):
    def setUp(self):
        self.server_ioloop = IOLoop(make_current=False)
        event = threading.Event()

        @gen.coroutine
        def init_server():
            sock, self.port = bind_unused_port()
            app = Application([("/", HelloWorldHandler)])
            self.server = HTTPServer(app)
            self.server.add_socket(sock)
            event.set()

        def start():
            self.server_ioloop.run_sync(init_server)
            self.server_ioloop.start()

        self.server_thread = threading.Thread(target=start)
        self.server_thread.start()
        event.wait()

        self.http_client = HTTPClient()

    def tearDown(self):
        def stop_server():
            self.server.stop()
            # Delay the shutdown of the IOLoop by several iterations because
            # the server may still have some cleanup work left when
            # the client finishes with the response (this is noticeable
            # with http/2, which leaves a Future with an unexamined
            # StreamClosedError on the loop).

            @gen.coroutine
            def slow_stop():
                yield self.server.close_all_connections()
                # The number of iterations is difficult to predict. Typically,
                # one is sufficient, although sometimes it needs more.
                for i in range(5):
                    yield
                self.server_ioloop.stop()

            self.server_ioloop.add_callback(slow_stop)

        self.server_ioloop.add_callback(stop_server)
        self.server_thread.join()
        self.http_client.close()
        self.server_ioloop.close(all_fds=True)

    def get_url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def test_sync_client(self):
        response = self.http_client.fetch(self.get_url("/"))
        self.assertEqual(b"Hello world!", response.body)

    def test_sync_client_error(self):
        # Synchronous HTTPClient raises errors directly; no need for
        # response.rethrow()
        with self.assertRaises(HTTPError) as assertion:
            self.http_client.fetch(self.get_url("/notfound"))
        self.assertEqual(assertion.exception.code, 404)


class SyncHTTPClientSubprocessTest(unittest.TestCase):
    def test_destructor_log(self):
        # Regression test for
        # https://github.com/tornadoweb/tornado/issues/2539
        #
        # In the past, the following program would log an
        # "inconsistent AsyncHTTPClient cache" error from a destructor
        # when the process is shutting down. The shutdown process is
        # subtle and I don't fully understand it; the failure does not
        # manifest if that lambda isn't there or is a simpler object
        # like an int (nor does it manifest in the tornado test suite
        # as a whole, which is why we use this subprocess).
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "from tornado.httpclient import HTTPClient; f = lambda: None; c = HTTPClient()",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=15,
        )
        if proc.stdout:
            print("STDOUT:")
            print(to_unicode(proc.stdout))
        if proc.stdout:
            self.fail("subprocess produced unexpected output")


class HTTPRequestTestCase(unittest.TestCase):
    def test_headers(self):
        request = HTTPRequest("http://example.com", headers={"foo": "bar"})
        self.assertEqual(request.headers, {"foo": "bar"})

    def test_headers_setter(self):
        request = HTTPRequest("http://example.com")
        request.headers = {"bar": "baz"}  # type: ignore
        self.assertEqual(request.headers, {"bar": "baz"})

    def test_null_headers_setter(self):
        request = HTTPRequest("http://example.com")
        request.headers = None  # type: ignore
        self.assertEqual(request.headers, {})

    def test_body(self):
        request = HTTPRequest("http://example.com", body="foo")
        self.assertEqual(request.body, utf8("foo"))

    def test_body_setter(self):
        request = HTTPRequest("http://example.com")
        request.body = "foo"  # type: ignore
        self.assertEqual(request.body, utf8("foo"))

    def test_if_modified_since(self):
        http_date = datetime.datetime.now(datetime.timezone.utc)
        request = HTTPRequest("http://example.com", if_modified_since=http_date)
        self.assertEqual(
            request.headers, {"If-Modified-Since": format_timestamp(http_date)}
        )

    def test_if_modified_since_naive_deprecated(self):
        with ignore_deprecation():
            http_date = datetime.datetime.utcnow()
        request = HTTPRequest("http://example.com", if_modified_since=http_date)
        self.assertEqual(
            request.headers, {"If-Modified-Since": format_timestamp(http_date)}
        )


class HTTPErrorTestCase(unittest.TestCase):
    def test_copy(self):
        e = HTTPError(403)
        e2 = copy.copy(e)
        self.assertIsNot(e, e2)
        self.assertEqual(e.code, e2.code)

    def test_plain_error(self):
        e = HTTPError(403)
        self.assertEqual(str(e), "HTTP 403: Forbidden")
        self.assertEqual(repr(e), "HTTP 403: Forbidden")

    def test_error_with_response(self):
        resp = HTTPResponse(HTTPRequest("http://example.com/"), 403)
        with self.assertRaises(HTTPError) as cm:
            resp.rethrow()
        e = cm.exception
        self.assertEqual(str(e), "HTTP 403: Forbidden")
        self.assertEqual(repr(e), "HTTP 403: Forbidden")