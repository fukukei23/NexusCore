
# === NexusCore/tools\exports\export_20250803_114325\combined_164.py ===

# === NexusCore/openenv\Lib\site-packages\pycparser\c_lexer.py ===
#------------------------------------------------------------------------------
# pycparser: c_lexer.py
#
# CLexer class: lexer for the C language
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#------------------------------------------------------------------------------
import re

from .ply import lex
from .ply.lex import TOKEN


class CLexer(object):
    """ A lexer for the C language. After building it, set the
        input text with input(), and call token() to get new
        tokens.

        The public attribute filename can be set to an initial
        filename, but the lexer will update it upon #line
        directives.
    """
    def __init__(self, error_func, on_lbrace_func, on_rbrace_func,
                 type_lookup_func):
        """ Create a new Lexer.

            error_func:
                An error function. Will be called with an error
                message, line and column as arguments, in case of
                an error during lexing.

            on_lbrace_func, on_rbrace_func:
                Called when an LBRACE or RBRACE is encountered
                (likely to push/pop type_lookup_func's scope)

            type_lookup_func:
                A type lookup function. Given a string, it must
                return True IFF this string is a name of a type
                that was defined with a typedef earlier.
        """
        self.error_func = error_func
        self.on_lbrace_func = on_lbrace_func
        self.on_rbrace_func = on_rbrace_func
        self.type_lookup_func = type_lookup_func
        self.filename = ''

        # Keeps track of the last token returned from self.token()
        self.last_token = None

        # Allow either "# line" or "# <num>" to support GCC's
        # cpp output
        #
        self.line_pattern = re.compile(r'([ \t]*line\W)|([ \t]*\d+)')
        self.pragma_pattern = re.compile(r'[ \t]*pragma\W')

    def build(self, **kwargs):
        """ Builds the lexer from the specification. Must be
            called after the lexer object is created.

            This method exists separately, because the PLY
            manual warns against calling lex.lex inside
            __init__
        """
        self.lexer = lex.lex(object=self, **kwargs)

    def reset_lineno(self):
        """ Resets the internal line number counter of the lexer.
        """
        self.lexer.lineno = 1

    def input(self, text):
        self.lexer.input(text)

    def token(self):
        self.last_token = self.lexer.token()
        return self.last_token

    def find_tok_column(self, token):
        """ Find the column of the token in its line.
        """
        last_cr = self.lexer.lexdata.rfind('\n', 0, token.lexpos)
        return token.lexpos - last_cr

    ######################--   PRIVATE   --######################

    ##
    ## Internal auxiliary methods
    ##
    def _error(self, msg, token):
        location = self._make_tok_location(token)
        self.error_func(msg, location[0], location[1])
        self.lexer.skip(1)

    def _make_tok_location(self, token):
        return (token.lineno, self.find_tok_column(token))

    ##
    ## Reserved keywords
    ##
    keywords = (
        'AUTO', 'BREAK', 'CASE', 'CHAR', 'CONST',
        'CONTINUE', 'DEFAULT', 'DO', 'DOUBLE', 'ELSE', 'ENUM', 'EXTERN',
        'FLOAT', 'FOR', 'GOTO', 'IF', 'INLINE', 'INT', 'LONG',
        'REGISTER', 'OFFSETOF',
        'RESTRICT', 'RETURN', 'SHORT', 'SIGNED', 'SIZEOF', 'STATIC', 'STRUCT',
        'SWITCH', 'TYPEDEF', 'UNION', 'UNSIGNED', 'VOID',
        'VOLATILE', 'WHILE', '__INT128',
    )

    keywords_new = (
        '_BOOL', '_COMPLEX',
        '_NORETURN', '_THREAD_LOCAL', '_STATIC_ASSERT',
        '_ATOMIC', '_ALIGNOF', '_ALIGNAS',
        '_PRAGMA',
        )

    keyword_map = {}

    for keyword in keywords:
        keyword_map[keyword.lower()] = keyword

    for keyword in keywords_new:
        keyword_map[keyword[:2].upper() + keyword[2:].lower()] = keyword

    ##
    ## All the tokens recognized by the lexer
    ##
    tokens = keywords + keywords_new + (
        # Identifiers
        'ID',

        # Type identifiers (identifiers previously defined as
        # types with typedef)
        'TYPEID',

        # constants
        'INT_CONST_DEC', 'INT_CONST_OCT', 'INT_CONST_HEX', 'INT_CONST_BIN', 'INT_CONST_CHAR',
        'FLOAT_CONST', 'HEX_FLOAT_CONST',
        'CHAR_CONST',
        'WCHAR_CONST',
        'U8CHAR_CONST',
        'U16CHAR_CONST',
        'U32CHAR_CONST',

        # String literals
        'STRING_LITERAL',
        'WSTRING_LITERAL',
        'U8STRING_LITERAL',
        'U16STRING_LITERAL',
        'U32STRING_LITERAL',

        # Operators
        'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
        'OR', 'AND', 'NOT', 'XOR', 'LSHIFT', 'RSHIFT',
        'LOR', 'LAND', 'LNOT',
        'LT', 'LE', 'GT', 'GE', 'EQ', 'NE',

        # Assignment
        'EQUALS', 'TIMESEQUAL', 'DIVEQUAL', 'MODEQUAL',
        'PLUSEQUAL', 'MINUSEQUAL',
        'LSHIFTEQUAL','RSHIFTEQUAL', 'ANDEQUAL', 'XOREQUAL',
        'OREQUAL',

        # Increment/decrement
        'PLUSPLUS', 'MINUSMINUS',

        # Structure dereference (->)
        'ARROW',

        # Conditional operator (?)
        'CONDOP',

        # Delimiters
        'LPAREN', 'RPAREN',         # ( )
        'LBRACKET', 'RBRACKET',     # [ ]
        'LBRACE', 'RBRACE',         # { }
        'COMMA', 'PERIOD',          # . ,
        'SEMI', 'COLON',            # ; :

        # Ellipsis (...)
        'ELLIPSIS',

        # pre-processor
        'PPHASH',       # '#'
        'PPPRAGMA',     # 'pragma'
        'PPPRAGMASTR',
    )

    ##
    ## Regexes for use in tokens
    ##
    ##

    # valid C identifiers (K&R2: A.2.3), plus '$' (supported by some compilers)
    identifier = r'[a-zA-Z_$][0-9a-zA-Z_$]*'

    hex_prefix = '0[xX]'
    hex_digits = '[0-9a-fA-F]+'
    bin_prefix = '0[bB]'
    bin_digits = '[01]+'

    # integer constants (K&R2: A.2.5.1)
    integer_suffix_opt = r'(([uU]ll)|([uU]LL)|(ll[uU]?)|(LL[uU]?)|([uU][lL])|([lL][uU]?)|[uU])?'
    decimal_constant = '(0'+integer_suffix_opt+')|([1-9][0-9]*'+integer_suffix_opt+')'
    octal_constant = '0[0-7]*'+integer_suffix_opt
    hex_constant = hex_prefix+hex_digits+integer_suffix_opt
    bin_constant = bin_prefix+bin_digits+integer_suffix_opt

    bad_octal_constant = '0[0-7]*[89]'

    # character constants (K&R2: A.2.5.2)
    # Note: a-zA-Z and '.-~^_!=&;,' are allowed as escape chars to support #line
    # directives with Windows paths as filenames (..\..\dir\file)
    # For the same reason, decimal_escape allows all digit sequences. We want to
    # parse all correct code, even if it means to sometimes parse incorrect
    # code.
    #
    # The original regexes were taken verbatim from the C syntax definition,
    # and were later modified to avoid worst-case exponential running time.
    #
    #   simple_escape = r"""([a-zA-Z._~!=&\^\-\\?'"])"""
    #   decimal_escape = r"""(\d+)"""
    #   hex_escape = r"""(x[0-9a-fA-F]+)"""
    #   bad_escape = r"""([\\][^a-zA-Z._~^!=&\^\-\\?'"x0-7])"""
    #
    # The following modifications were made to avoid the ambiguity that allowed backtracking:
    # (https://github.com/eliben/pycparser/issues/61)
    #
    # - \x was removed from simple_escape, unless it was not followed by a hex digit, to avoid ambiguity with hex_escape.
    # - hex_escape allows one or more hex characters, but requires that the next character(if any) is not hex
    # - decimal_escape allows one or more decimal characters, but requires that the next character(if any) is not a decimal
    # - bad_escape does not allow any decimals (8-9), to avoid conflicting with the permissive decimal_escape.
    #
    # Without this change, python's `re` module would recursively try parsing each ambiguous escape sequence in multiple ways.
    # e.g. `\123` could be parsed as `\1`+`23`, `\12`+`3`, and `\123`.

    simple_escape = r"""([a-wyzA-Z._~!=&\^\-\\?'"]|x(?![0-9a-fA-F]))"""
    decimal_escape = r"""(\d+)(?!\d)"""
    hex_escape = r"""(x[0-9a-fA-F]+)(?![0-9a-fA-F])"""
    bad_escape = r"""([\\][^a-zA-Z._~^!=&\^\-\\?'"x0-9])"""

    escape_sequence = r"""(\\("""+simple_escape+'|'+decimal_escape+'|'+hex_escape+'))'

    # This complicated regex with lookahead might be slow for strings, so because all of the valid escapes (including \x) allowed
    # 0 or more non-escaped characters after the first character, simple_escape+decimal_escape+hex_escape got simplified to

    escape_sequence_start_in_string = r"""(\\[0-9a-zA-Z._~!=&\^\-\\?'"])"""

    cconst_char = r"""([^'\\\n]|"""+escape_sequence+')'
    char_const = "'"+cconst_char+"'"
    wchar_const = 'L'+char_const
    u8char_const = 'u8'+char_const
    u16char_const = 'u'+char_const
    u32char_const = 'U'+char_const
    multicharacter_constant = "'"+cconst_char+"{2,4}'"
    unmatched_quote = "('"+cconst_char+"*\\n)|('"+cconst_char+"*$)"
    bad_char_const = r"""('"""+cconst_char+"""[^'\n]+')|('')|('"""+bad_escape+r"""[^'\n]*')"""

    # string literals (K&R2: A.2.6)
    string_char = r"""([^"\\\n]|"""+escape_sequence_start_in_string+')'
    string_literal = '"'+string_char+'*"'
    wstring_literal = 'L'+string_literal
    u8string_literal = 'u8'+string_literal
    u16string_literal = 'u'+string_literal
    u32string_literal = 'U'+string_literal
    bad_string_literal = '"'+string_char+'*'+bad_escape+string_char+'*"'

    # floating constants (K&R2: A.2.5.3)
    exponent_part = r"""([eE][-+]?[0-9]+)"""
    fractional_constant = r"""([0-9]*\.[0-9]+)|([0-9]+\.)"""
    floating_constant = '(((('+fractional_constant+')'+exponent_part+'?)|([0-9]+'+exponent_part+'))[FfLl]?)'
    binary_exponent_part = r'''([pP][+-]?[0-9]+)'''
    hex_fractional_constant = '((('+hex_digits+r""")?\."""+hex_digits+')|('+hex_digits+r"""\.))"""
    hex_floating_constant = '('+hex_prefix+'('+hex_digits+'|'+hex_fractional_constant+')'+binary_exponent_part+'[FfLl]?)'

    ##
    ## Lexer states: used for preprocessor \n-terminated directives
    ##
    states = (
        # ppline: preprocessor line directives
        #
        ('ppline', 'exclusive'),

        # pppragma: pragma
        #
        ('pppragma', 'exclusive'),
    )

    def t_PPHASH(self, t):
        r'[ \t]*\#'
        if self.line_pattern.match(t.lexer.lexdata, pos=t.lexer.lexpos):
            t.lexer.begin('ppline')
            self.pp_line = self.pp_filename = None
        elif self.pragma_pattern.match(t.lexer.lexdata, pos=t.lexer.lexpos):
            t.lexer.begin('pppragma')
        else:
            t.type = 'PPHASH'
            return t

    ##
    ## Rules for the ppline state
    ##
    @TOKEN(string_literal)
    def t_ppline_FILENAME(self, t):
        if self.pp_line is None:
            self._error('filename before line number in #line', t)
        else:
            self.pp_filename = t.value.lstrip('"').rstrip('"')

    @TOKEN(decimal_constant)
    def t_ppline_LINE_NUMBER(self, t):
        if self.pp_line is None:
            self.pp_line = t.value
        else:
            # Ignore: GCC's cpp sometimes inserts a numeric flag
            # after the file name
            pass

    def t_ppline_NEWLINE(self, t):
        r'\n'
        if self.pp_line is None:
            self._error('line number missing in #line', t)
        else:
            self.lexer.lineno = int(self.pp_line)

            if self.pp_filename is not None:
                self.filename = self.pp_filename

        t.lexer.begin('INITIAL')

    def t_ppline_PPLINE(self, t):
        r'line'
        pass

    t_ppline_ignore = ' \t'

    def t_ppline_error(self, t):
        self._error('invalid #line directive', t)

    ##
    ## Rules for the pppragma state
    ##
    def t_pppragma_NEWLINE(self, t):
        r'\n'
        t.lexer.lineno += 1
        t.lexer.begin('INITIAL')

    def t_pppragma_PPPRAGMA(self, t):
        r'pragma'
        return t

    t_pppragma_ignore = ' \t'

    def t_pppragma_STR(self, t):
        '.+'
        t.type = 'PPPRAGMASTR'
        return t

    def t_pppragma_error(self, t):
        self._error('invalid #pragma directive', t)

    ##
    ## Rules for the normal state
    ##
    t_ignore = ' \t'

    # Newlines
    def t_NEWLINE(self, t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")

    # Operators
    t_PLUS              = r'\+'
    t_MINUS             = r'-'
    t_TIMES             = r'\*'
    t_DIVIDE            = r'/'
    t_MOD               = r'%'
    t_OR                = r'\|'
    t_AND               = r'&'
    t_NOT               = r'~'
    t_XOR               = r'\^'
    t_LSHIFT            = r'<<'
    t_RSHIFT            = r'>>'
    t_LOR               = r'\|\|'
    t_LAND              = r'&&'
    t_LNOT              = r'!'
    t_LT                = r'<'
    t_GT                = r'>'
    t_LE                = r'<='
    t_GE                = r'>='
    t_EQ                = r'=='
    t_NE                = r'!='

    # Assignment operators
    t_EQUALS            = r'='
    t_TIMESEQUAL        = r'\*='
    t_DIVEQUAL          = r'/='
    t_MODEQUAL          = r'%='
    t_PLUSEQUAL         = r'\+='
    t_MINUSEQUAL        = r'-='
    t_LSHIFTEQUAL       = r'<<='
    t_RSHIFTEQUAL       = r'>>='
    t_ANDEQUAL          = r'&='
    t_OREQUAL           = r'\|='
    t_XOREQUAL          = r'\^='

    # Increment/decrement
    t_PLUSPLUS          = r'\+\+'
    t_MINUSMINUS        = r'--'

    # ->
    t_ARROW             = r'->'

    # ?
    t_CONDOP            = r'\?'

    # Delimiters
    t_LPAREN            = r'\('
    t_RPAREN            = r'\)'
    t_LBRACKET          = r'\['
    t_RBRACKET          = r'\]'
    t_COMMA             = r','
    t_PERIOD            = r'\.'
    t_SEMI              = r';'
    t_COLON             = r':'
    t_ELLIPSIS          = r'\.\.\.'

    # Scope delimiters
    # To see why on_lbrace_func is needed, consider:
    #   typedef char TT;
    #   void foo(int TT) { TT = 10; }
    #   TT x = 5;
    # Outside the function, TT is a typedef, but inside (starting and ending
    # with the braces) it's a parameter.  The trouble begins with yacc's
    # lookahead token.  If we open a new scope in brace_open, then TT has
    # already been read and incorrectly interpreted as TYPEID.  So, we need
    # to open and close scopes from within the lexer.
    # Similar for the TT immediately outside the end of the function.
    #
    @TOKEN(r'\{')
    def t_LBRACE(self, t):
        self.on_lbrace_func()
        return t
    @TOKEN(r'\}')
    def t_RBRACE(self, t):
        self.on_rbrace_func()
        return t

    t_STRING_LITERAL = string_literal

    # The following floating and integer constants are defined as
    # functions to impose a strict order (otherwise, decimal
    # is placed before the others because its regex is longer,
    # and this is bad)
    #
    @TOKEN(floating_constant)
    def t_FLOAT_CONST(self, t):
        return t

    @TOKEN(hex_floating_constant)
    def t_HEX_FLOAT_CONST(self, t):
        return t

    @TOKEN(hex_constant)
    def t_INT_CONST_HEX(self, t):
        return t

    @TOKEN(bin_constant)
    def t_INT_CONST_BIN(self, t):
        return t

    @TOKEN(bad_octal_constant)
    def t_BAD_CONST_OCT(self, t):
        msg = "Invalid octal constant"
        self._error(msg, t)

    @TOKEN(octal_constant)
    def t_INT_CONST_OCT(self, t):
        return t

    @TOKEN(decimal_constant)
    def t_INT_CONST_DEC(self, t):
        return t

    # Must come before bad_char_const, to prevent it from
    # catching valid char constants as invalid
    #
    @TOKEN(multicharacter_constant)
    def t_INT_CONST_CHAR(self, t):
        return t

    @TOKEN(char_const)
    def t_CHAR_CONST(self, t):
        return t

    @TOKEN(wchar_const)
    def t_WCHAR_CONST(self, t):
        return t

    @TOKEN(u8char_const)
    def t_U8CHAR_CONST(self, t):
        return t

    @TOKEN(u16char_const)
    def t_U16CHAR_CONST(self, t):
        return t

    @TOKEN(u32char_const)
    def t_U32CHAR_CONST(self, t):
        return t

    @TOKEN(unmatched_quote)
    def t_UNMATCHED_QUOTE(self, t):
        msg = "Unmatched '"
        self._error(msg, t)

    @TOKEN(bad_char_const)
    def t_BAD_CHAR_CONST(self, t):
        msg = "Invalid char constant %s" % t.value
        self._error(msg, t)

    @TOKEN(wstring_literal)
    def t_WSTRING_LITERAL(self, t):
        return t

    @TOKEN(u8string_literal)
    def t_U8STRING_LITERAL(self, t):
        return t

    @TOKEN(u16string_literal)
    def t_U16STRING_LITERAL(self, t):
        return t

    @TOKEN(u32string_literal)
    def t_U32STRING_LITERAL(self, t):
        return t

    # unmatched string literals are caught by the preprocessor

    @TOKEN(bad_string_literal)
    def t_BAD_STRING_LITERAL(self, t):
        msg = "String contains invalid escape code"
        self._error(msg, t)

    @TOKEN(identifier)
    def t_ID(self, t):
        t.type = self.keyword_map.get(t.value, "ID")
        if t.type == 'ID' and self.type_lookup_func(t.value):
            t.type = "TYPEID"
        return t

    def t_error(self, t):
        msg = 'Illegal character %s' % repr(t.value[0])
        self._error(msg, t)

# === NexusCore/openenv\Lib\site-packages\IPython\core\tbtools.py ===
import functools
import inspect
import pydoc
import sys
import types
import warnings
from types import TracebackType
from typing import Any, Callable, Optional, Tuple

import stack_data
from pygments.token import Token

from IPython import get_ipython
from IPython.core import debugger
from IPython.utils import path as util_path
from IPython.utils import py3compat
from IPython.utils.PyColorize import Theme, TokenStream, theme_table

_sentinel = object()
INDENT_SIZE = 8


@functools.lru_cache
def count_lines_in_py_file(filename: str) -> int:
    """
    Given a filename, returns the number of lines in the file
    if it ends with the extension ".py". Otherwise, returns 0.
    """
    if not filename.endswith(".py"):
        return 0
    else:
        try:
            with open(filename, "r") as file:
                s = sum(1 for line in file)
        except UnicodeError:
            return 0
    return s


def get_line_number_of_frame(frame: types.FrameType) -> int:
    """
    Given a frame object, returns the total number of lines in the file
    containing the frame's code object, or the number of lines in the
    frame's source code if the file is not available.

    Parameters
    ----------
    frame : FrameType
        The frame object whose line number is to be determined.

    Returns
    -------
    int
        The total number of lines in the file containing the frame's
        code object, or the number of lines in the frame's source code
        if the file is not available.
    """
    filename = frame.f_code.co_filename
    if filename is None:
        print("No file....")
        lines, first = inspect.getsourcelines(frame)
        return first + len(lines)
    return count_lines_in_py_file(filename)


def _safe_string(value: Any, what: Any, func: Any = str) -> str:
    # Copied from cpython/Lib/traceback.py
    try:
        return func(value)
    except:
        return f"<{what} {func.__name__}() failed>"


def _format_traceback_lines(
    lines: list[stack_data.Line],
    theme: Theme,
    has_colors: bool,
    lvals_toks: list[TokenStream],
) -> TokenStream:
    """
    Format tracebacks lines with pointing arrow, leading numbers,
    this assumes the stack have been extracted using stackdata.


    Parameters
    ----------
    lines : list[Line]
    """
    numbers_width = INDENT_SIZE - 1
    tokens: TokenStream = []

    for stack_line in lines:
        if stack_line is stack_data.LINE_GAP:
            toks = [(Token.LinenoEm, "   (...)")]
            tokens.extend(toks)
            continue

        lineno = stack_line.lineno
        line = stack_line.render(pygmented=has_colors).rstrip("\n") + "\n"
        if stack_line.is_current:
            # This is the line with the error
            pad = numbers_width - len(str(lineno))
            toks = [
                (Token.LinenoEm, theme.make_arrow(pad)),
                (Token.LinenoEm, str(lineno)),
                (Token, " "),
                (Token, line),
            ]
        else:
            num = "%*s" % (numbers_width, lineno)
            toks = [
                (Token.LinenoEm, str(num)),
                (Token, " "),
                (Token, line),
            ]

        tokens.extend(toks)
        if lvals_toks and stack_line.is_current:
            for lv in lvals_toks:
                tokens.append((Token, " " * INDENT_SIZE))
                tokens.extend(lv)
                tokens.append((Token, "\n"))
            # strip the last newline
            tokens = tokens[:-1]

    return tokens


# some internal-use functions
def text_repr(value: Any) -> str:
    """Hopefully pretty robust repr equivalent."""
    # this is pretty horrible but should always return *something*
    try:
        return pydoc.text.repr(value)  # type: ignore[call-arg]
    except KeyboardInterrupt:
        raise
    except:
        try:
            return repr(value)
        except KeyboardInterrupt:
            raise
        except:
            try:
                # all still in an except block so we catch
                # getattr raising
                name = getattr(value, "__name__", None)
                if name:
                    # ick, recursion
                    return text_repr(name)
                klass = getattr(value, "__class__", None)
                if klass:
                    return "%s instance" % text_repr(klass)
                return "UNRECOVERABLE REPR FAILURE"
            except KeyboardInterrupt:
                raise
            except:
                return "UNRECOVERABLE REPR FAILURE"


def eqrepr(value: Any, repr: Callable[[Any], str] = text_repr) -> str:
    return "=%s" % repr(value)


def nullrepr(value: Any, repr: Callable[[Any], str] = text_repr) -> str:
    return ""


def _tokens_filename(
    em: bool,
    file: str | None,
    *,
    lineno: int | None = None,
) -> TokenStream:
    """
    Format filename lines with custom formatting from caching compiler or `File *.py` by default

    Parameters
    ----------
    em: wether bold or not
    file : str
    """
    Normal = Token.NormalEm if em else Token.Normal
    Filename = Token.FilenameEm if em else Token.Filename
    ipinst = get_ipython()
    if (
        ipinst is not None
        and (data := ipinst.compile.format_code_name(file)) is not None
    ):
        label, name = data
        if lineno is None:
            return [
                (Normal, label),
                (Normal, " "),
                (Filename, name),
            ]
        else:
            return [
                (Normal, label),
                (Normal, " "),
                (Filename, name),
                (Filename, f", line {lineno}"),
            ]
    else:
        name = util_path.compress_user(
            py3compat.cast_unicode(file, util_path.fs_encoding)
        )
        if lineno is None:
            return [
                (Normal, "File "),
                (Filename, name),
            ]
        else:
            return [
                (Normal, "File "),
                (Filename, f"{name}:{lineno}"),
            ]


def _simple_format_traceback_lines(
    lnum: int,
    index: int,
    lines: list[tuple[str, tuple[str, bool]]],
    lvals_toks: list[TokenStream],
    theme: Theme,
) -> TokenStream:
    """
    Format tracebacks lines with pointing arrow, leading numbers

    This should be equivalent to _format_traceback_lines, but does not rely on stackdata
    to format the lines

    This is due to the fact that stackdata may be slow on super long and complex files.

    Parameters
    ==========

    lnum: int
        number of the target line of code.
    index: int
        which line in the list should be highlighted.
    lines: list[string]
    lvals_toks: pairs of token type and str
        Values of local variables, already colored, to inject just after the error line.
    """
    for item in lvals_toks:
        assert isinstance(item, list)
        for subit in item:
            assert isinstance(subit[1], str)

    numbers_width = INDENT_SIZE - 1
    res_toks: TokenStream = []
    for i, (line, (new_line, err)) in enumerate(lines, lnum - index):
        if not err:
            line = new_line

        colored_line = line
        if i == lnum:
            # This is the line with the error
            pad = numbers_width - len(str(i))
            line_toks = [
                (Token.LinenoEm, theme.make_arrow(pad)),
                (Token.LinenoEm, str(lnum)),
                (Token, " "),
                (Token, colored_line),
            ]
        else:
            padding_num = "%*s" % (numbers_width, i)

            line_toks = [
                (Token.LinenoEm, padding_num),
                (Token, " "),
                (Token, colored_line),
            ]
        res_toks.extend(line_toks)

        if lvals_toks and i == lnum:
            for lv in lvals_toks:
                res_toks.extend(lv)
            # res_toks.extend(lvals_toks)
    return res_toks


class FrameInfo:
    """
    Mirror of stack data's FrameInfo, but so that we can bypass highlighting on
    really long frames.
    """

    description: Optional[str]
    filename: Optional[str]
    lineno: int
    # number of context lines to use
    context: Optional[int]
    raw_lines: list[str]
    _sd: stack_data.core.FrameInfo
    frame: Any

    @classmethod
    def _from_stack_data_FrameInfo(
        cls, frame_info: stack_data.core.FrameInfo | stack_data.core.RepeatedFrames
    ) -> "FrameInfo":
        return cls(
            getattr(frame_info, "description", None),
            getattr(frame_info, "filename", None),  # type: ignore[arg-type]
            getattr(frame_info, "lineno", None),  # type: ignore[arg-type]
            getattr(frame_info, "frame", None),
            getattr(frame_info, "code", None),
            sd=frame_info,
            context=None,
        )

    def __init__(
        self,
        description: Optional[str],
        filename: str,
        lineno: int,
        frame: Any,
        code: Optional[types.CodeType],
        *,
        sd: Any = None,
        context: int | None = None,
    ):
        assert isinstance(lineno, (int, type(None))), lineno
        self.description = description
        self.filename = filename
        self.lineno = lineno
        self.frame = frame
        self.code = code
        self._sd = sd
        self.context = context

        # self.lines = []
        if sd is None:
            try:
                # return a list of source lines and a starting line number
                self.raw_lines = inspect.getsourcelines(frame)[0]
            except OSError:
                self.raw_lines = [
                    "'Could not get source, probably due dynamically evaluated source code.'"
                ]

    @property
    def variables_in_executing_piece(self) -> list[Any]:
        if self._sd is not None:
            return self._sd.variables_in_executing_piece  # type:ignore[misc]
        else:
            return []

    @property
    def lines(self) -> list[Any]:
        from executing.executing import NotOneValueFound

        assert self._sd is not None
        try:
            return self._sd.lines  # type: ignore[misc]
        except NotOneValueFound:

            class Dummy:
                lineno = 0
                is_current = False

                def render(self, *, pygmented: bool) -> str:
                    return "<Error retrieving source code with stack_data see ipython/ipython#13598>"

            return [Dummy()]

    @property
    def executing(self) -> Any:
        if self._sd is not None:
            return self._sd.executing
        else:
            return None


class TBTools:
    """Basic tools used by all traceback printer classes."""

    # Number of frames to skip when reporting tracebacks
    tb_offset = 0
    _theme_name: str
    _old_theme_name: str
    call_pdb: bool
    ostream: Any
    debugger_cls: Any
    pdb: Any

    def __init__(
        self,
        color_scheme: Any = _sentinel,
        call_pdb: bool = False,
        ostream: Any = None,
        *,
        debugger_cls: type | None = None,
        theme_name: str = "nocolor",
    ):
        if color_scheme is not _sentinel:
            assert isinstance(color_scheme, str), color_scheme
            warnings.warn(
                "color_scheme is deprecated since IPython 9.0, use theme_name instead, all lowercase",
                DeprecationWarning,
                stacklevel=2,
            )
            theme_name = color_scheme
        if theme_name in ["Linux", "LightBG", "Neutral", "NoColor"]:
            warnings.warn(
                f"Theme names and color schemes are lowercase in IPython 9.0 use {theme_name.lower()} instead",
                DeprecationWarning,
                stacklevel=2,
            )
            theme_name = theme_name.lower()
        # Whether to call the interactive pdb debugger after printing
        # tracebacks or not
        super().__init__()
        self.call_pdb = call_pdb

        # Output stream to write to.  Note that we store the original value in
        # a private attribute and then make the public ostream a property, so
        # that we can delay accessing sys.stdout until runtime.  The way
        # things are written now, the sys.stdout object is dynamically managed
        # so a reference to it should NEVER be stored statically.  This
        # property approach confines this detail to a single location, and all
        # subclasses can simply access self.ostream for writing.
        self._ostream = ostream

        # Create color table
        self.set_theme_name(theme_name)
        self.debugger_cls = debugger_cls or debugger.Pdb

        if call_pdb:
            self.pdb = self.debugger_cls()
        else:
            self.pdb = None

    def _get_ostream(self) -> Any:
        """Output stream that exceptions are written to.

        Valid values are:

        - None: the default, which means that IPython will dynamically resolve
          to sys.stdout.  This ensures compatibility with most tools, including
          Windows (where plain stdout doesn't recognize ANSI escapes).

        - Any object with 'write' and 'flush' attributes.
        """
        return sys.stdout if self._ostream is None else self._ostream

    def _set_ostream(self, val) -> None:  # type:ignore[no-untyped-def]
        assert val is None or (hasattr(val, "write") and hasattr(val, "flush"))
        self._ostream = val

    ostream = property(_get_ostream, _set_ostream)

    @staticmethod
    def _get_chained_exception(exception_value: Any) -> Any:
        cause = getattr(exception_value, "__cause__", None)
        if cause:
            return cause
        if getattr(exception_value, "__suppress_context__", False):
            return None
        return getattr(exception_value, "__context__", None)

    def get_parts_of_chained_exception(
        self, evalue: BaseException | None
    ) -> Optional[Tuple[type, BaseException, TracebackType]]:
        chained_evalue = self._get_chained_exception(evalue)

        if chained_evalue:
            return (
                chained_evalue.__class__,
                chained_evalue,
                chained_evalue.__traceback__,
            )
        return None

    def prepare_chained_exception_message(
        self, cause: BaseException | None
    ) -> list[list[str]]:
        direct_cause = (
            "\nThe above exception was the direct cause of the following exception:\n"
        )
        exception_during_handling = (
            "\nDuring handling of the above exception, another exception occurred:\n"
        )

        if cause:
            message = [[direct_cause]]
        else:
            message = [[exception_during_handling]]
        return message

    @property
    def has_colors(self) -> bool:
        assert self._theme_name == self._theme_name.lower()
        return self._theme_name != "nocolor"

    def set_theme_name(self, name: str) -> None:
        assert name in theme_table
        assert name.lower() == name
        self._theme_name = name
        # Also set colors of debugger
        if hasattr(self, "pdb") and self.pdb is not None:
            self.pdb.set_theme_name(name)

    def set_colors(self, name: str) -> None:
        """Shorthand access to the color table scheme selector method."""

        # todo emit deprecation
        warnings.warn(
            "set_colors is deprecated since IPython 9.0, use set_theme_name instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.set_theme_name(name)

    def color_toggle(self) -> None:
        """Toggle between the currently active color scheme and nocolor."""
        if self._theme_name == "nocolor":
            self._theme_name = self._old_theme_name
        else:
            self._old_theme_name = self._theme_name
            self._theme_name = "nocolor"

    def stb2text(self, stb: list[str]) -> str:
        """Convert a structured traceback (a list) to a string."""
        return "\n".join(stb)

    def text(
        self,
        etype: type,
        value: BaseException | None,
        tb: TracebackType | None,
        tb_offset: Optional[int] = None,
        context: int = 5,
    ) -> str:
        """Return formatted traceback.

        Subclasses may override this if they add extra arguments.
        """
        tb_list = self.structured_traceback(etype, value, tb, tb_offset, context)
        return self.stb2text(tb_list)

    def structured_traceback(
        self,
        etype: type,
        evalue: BaseException | None,
        etb: Optional[TracebackType] = None,
        tb_offset: Optional[int] = None,
        context: int = 5,
    ) -> list[str]:
        """Return a list of traceback frames.

        Must be implemented by each class.
        """
        raise NotImplementedError()

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\preload.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Preload (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import network
from . import page


class RuleSetId(str):
    '''
    Unique id
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RuleSetId:
        return cls(json)

    def __repr__(self):
        return 'RuleSetId({})'.format(super().__repr__())


@dataclass
class RuleSet:
    '''
    Corresponds to SpeculationRuleSet
    '''
    id_: RuleSetId

    #: Identifies a document which the rule set is associated with.
    loader_id: network.LoaderId

    #: Source text of JSON representing the rule set. If it comes from
    #: ``script`` tag, it is the textContent of the node. Note that it is
    #: a JSON for valid case.
    #: 
    #: See also:
    #: - https://wicg.github.io/nav-speculation/speculation-rules.html
    #: - https://github.com/WICG/nav-speculation/blob/main/triggers.md
    source_text: str

    #: A speculation rule set is either added through an inline
    #: ``script`` tag or through an external resource via the
    #: 'Speculation-Rules' HTTP header. For the first case, we include
    #: the BackendNodeId of the relevant ``script`` tag. For the second
    #: case, we include the external URL where the rule set was loaded
    #: from, and also RequestId if Network domain is enabled.
    #: 
    #: See also:
    #: - https://wicg.github.io/nav-speculation/speculation-rules.html#speculation-rules-script
    #: - https://wicg.github.io/nav-speculation/speculation-rules.html#speculation-rules-header
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    url: typing.Optional[str] = None

    request_id: typing.Optional[network.RequestId] = None

    #: Error information
    #: ``errorMessage`` is null iff ``errorType`` is null.
    error_type: typing.Optional[RuleSetErrorType] = None

    #: TODO(https://crbug.com/1425354): Replace this property with structured error.
    error_message: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_.to_json()
        json['loaderId'] = self.loader_id.to_json()
        json['sourceText'] = self.source_text
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        if self.url is not None:
            json['url'] = self.url
        if self.request_id is not None:
            json['requestId'] = self.request_id.to_json()
        if self.error_type is not None:
            json['errorType'] = self.error_type.to_json()
        if self.error_message is not None:
            json['errorMessage'] = self.error_message
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=RuleSetId.from_json(json['id']),
            loader_id=network.LoaderId.from_json(json['loaderId']),
            source_text=str(json['sourceText']),
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
            url=str(json['url']) if 'url' in json else None,
            request_id=network.RequestId.from_json(json['requestId']) if 'requestId' in json else None,
            error_type=RuleSetErrorType.from_json(json['errorType']) if 'errorType' in json else None,
            error_message=str(json['errorMessage']) if 'errorMessage' in json else None,
        )


class RuleSetErrorType(enum.Enum):
    SOURCE_IS_NOT_JSON_OBJECT = "SourceIsNotJsonObject"
    INVALID_RULES_SKIPPED = "InvalidRulesSkipped"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SpeculationAction(enum.Enum):
    '''
    The type of preloading attempted. It corresponds to
    mojom::SpeculationAction (although PrefetchWithSubresources is omitted as it
    isn't being used by clients).
    '''
    PREFETCH = "Prefetch"
    PRERENDER = "Prerender"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SpeculationTargetHint(enum.Enum):
    '''
    Corresponds to mojom::SpeculationTargetHint.
    See https://github.com/WICG/nav-speculation/blob/main/triggers.md#window-name-targeting-hints
    '''
    BLANK = "Blank"
    SELF = "Self"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PreloadingAttemptKey:
    '''
    A key that identifies a preloading attempt.

    The url used is the url specified by the trigger (i.e. the initial URL), and
    not the final url that is navigated to. For example, prerendering allows
    same-origin main frame navigations during the attempt, but the attempt is
    still keyed with the initial URL.
    '''
    loader_id: network.LoaderId

    action: SpeculationAction

    url: str

    target_hint: typing.Optional[SpeculationTargetHint] = None

    def to_json(self):
        json = dict()
        json['loaderId'] = self.loader_id.to_json()
        json['action'] = self.action.to_json()
        json['url'] = self.url
        if self.target_hint is not None:
            json['targetHint'] = self.target_hint.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            loader_id=network.LoaderId.from_json(json['loaderId']),
            action=SpeculationAction.from_json(json['action']),
            url=str(json['url']),
            target_hint=SpeculationTargetHint.from_json(json['targetHint']) if 'targetHint' in json else None,
        )


@dataclass
class PreloadingAttemptSource:
    '''
    Lists sources for a preloading attempt, specifically the ids of rule sets
    that had a speculation rule that triggered the attempt, and the
    BackendNodeIds of <a href> or <area href> elements that triggered the
    attempt (in the case of attempts triggered by a document rule). It is
    possible for multiple rule sets and links to trigger a single attempt.
    '''
    key: PreloadingAttemptKey

    rule_set_ids: typing.List[RuleSetId]

    node_ids: typing.List[dom.BackendNodeId]

    def to_json(self):
        json = dict()
        json['key'] = self.key.to_json()
        json['ruleSetIds'] = [i.to_json() for i in self.rule_set_ids]
        json['nodeIds'] = [i.to_json() for i in self.node_ids]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=PreloadingAttemptKey.from_json(json['key']),
            rule_set_ids=[RuleSetId.from_json(i) for i in json['ruleSetIds']],
            node_ids=[dom.BackendNodeId.from_json(i) for i in json['nodeIds']],
        )


class PreloadPipelineId(str):
    '''
    Chrome manages different types of preloads together using a
    concept of preloading pipeline. For example, if a site uses a
    SpeculationRules for prerender, Chrome first starts a prefetch and
    then upgrades it to prerender.

    CDP events for them are emitted separately but they share
    ``PreloadPipelineId``.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> PreloadPipelineId:
        return cls(json)

    def __repr__(self):
        return 'PreloadPipelineId({})'.format(super().__repr__())


class PrerenderFinalStatus(enum.Enum):
    '''
    List of FinalStatus reasons for Prerender2.
    '''
    ACTIVATED = "Activated"
    DESTROYED = "Destroyed"
    LOW_END_DEVICE = "LowEndDevice"
    INVALID_SCHEME_REDIRECT = "InvalidSchemeRedirect"
    INVALID_SCHEME_NAVIGATION = "InvalidSchemeNavigation"
    NAVIGATION_REQUEST_BLOCKED_BY_CSP = "NavigationRequestBlockedByCsp"
    MAIN_FRAME_NAVIGATION = "MainFrameNavigation"
    MOJO_BINDER_POLICY = "MojoBinderPolicy"
    RENDERER_PROCESS_CRASHED = "RendererProcessCrashed"
    RENDERER_PROCESS_KILLED = "RendererProcessKilled"
    DOWNLOAD = "Download"
    TRIGGER_DESTROYED = "TriggerDestroyed"
    NAVIGATION_NOT_COMMITTED = "NavigationNotCommitted"
    NAVIGATION_BAD_HTTP_STATUS = "NavigationBadHttpStatus"
    CLIENT_CERT_REQUESTED = "ClientCertRequested"
    NAVIGATION_REQUEST_NETWORK_ERROR = "NavigationRequestNetworkError"
    CANCEL_ALL_HOSTS_FOR_TESTING = "CancelAllHostsForTesting"
    DID_FAIL_LOAD = "DidFailLoad"
    STOP = "Stop"
    SSL_CERTIFICATE_ERROR = "SslCertificateError"
    LOGIN_AUTH_REQUESTED = "LoginAuthRequested"
    UA_CHANGE_REQUIRES_RELOAD = "UaChangeRequiresReload"
    BLOCKED_BY_CLIENT = "BlockedByClient"
    AUDIO_OUTPUT_DEVICE_REQUESTED = "AudioOutputDeviceRequested"
    MIXED_CONTENT = "MixedContent"
    TRIGGER_BACKGROUNDED = "TriggerBackgrounded"
    MEMORY_LIMIT_EXCEEDED = "MemoryLimitExceeded"
    DATA_SAVER_ENABLED = "DataSaverEnabled"
    TRIGGER_URL_HAS_EFFECTIVE_URL = "TriggerUrlHasEffectiveUrl"
    ACTIVATED_BEFORE_STARTED = "ActivatedBeforeStarted"
    INACTIVE_PAGE_RESTRICTION = "InactivePageRestriction"
    START_FAILED = "StartFailed"
    TIMEOUT_BACKGROUNDED = "TimeoutBackgrounded"
    CROSS_SITE_REDIRECT_IN_INITIAL_NAVIGATION = "CrossSiteRedirectInInitialNavigation"
    CROSS_SITE_NAVIGATION_IN_INITIAL_NAVIGATION = "CrossSiteNavigationInInitialNavigation"
    SAME_SITE_CROSS_ORIGIN_REDIRECT_NOT_OPT_IN_IN_INITIAL_NAVIGATION = "SameSiteCrossOriginRedirectNotOptInInInitialNavigation"
    SAME_SITE_CROSS_ORIGIN_NAVIGATION_NOT_OPT_IN_IN_INITIAL_NAVIGATION = "SameSiteCrossOriginNavigationNotOptInInInitialNavigation"
    ACTIVATION_NAVIGATION_PARAMETER_MISMATCH = "ActivationNavigationParameterMismatch"
    ACTIVATED_IN_BACKGROUND = "ActivatedInBackground"
    EMBEDDER_HOST_DISALLOWED = "EmbedderHostDisallowed"
    ACTIVATION_NAVIGATION_DESTROYED_BEFORE_SUCCESS = "ActivationNavigationDestroyedBeforeSuccess"
    TAB_CLOSED_BY_USER_GESTURE = "TabClosedByUserGesture"
    TAB_CLOSED_WITHOUT_USER_GESTURE = "TabClosedWithoutUserGesture"
    PRIMARY_MAIN_FRAME_RENDERER_PROCESS_CRASHED = "PrimaryMainFrameRendererProcessCrashed"
    PRIMARY_MAIN_FRAME_RENDERER_PROCESS_KILLED = "PrimaryMainFrameRendererProcessKilled"
    ACTIVATION_FRAME_POLICY_NOT_COMPATIBLE = "ActivationFramePolicyNotCompatible"
    PRELOADING_DISABLED = "PreloadingDisabled"
    BATTERY_SAVER_ENABLED = "BatterySaverEnabled"
    ACTIVATED_DURING_MAIN_FRAME_NAVIGATION = "ActivatedDuringMainFrameNavigation"
    PRELOADING_UNSUPPORTED_BY_WEB_CONTENTS = "PreloadingUnsupportedByWebContents"
    CROSS_SITE_REDIRECT_IN_MAIN_FRAME_NAVIGATION = "CrossSiteRedirectInMainFrameNavigation"
    CROSS_SITE_NAVIGATION_IN_MAIN_FRAME_NAVIGATION = "CrossSiteNavigationInMainFrameNavigation"
    SAME_SITE_CROSS_ORIGIN_REDIRECT_NOT_OPT_IN_IN_MAIN_FRAME_NAVIGATION = "SameSiteCrossOriginRedirectNotOptInInMainFrameNavigation"
    SAME_SITE_CROSS_ORIGIN_NAVIGATION_NOT_OPT_IN_IN_MAIN_FRAME_NAVIGATION = "SameSiteCrossOriginNavigationNotOptInInMainFrameNavigation"
    MEMORY_PRESSURE_ON_TRIGGER = "MemoryPressureOnTrigger"
    MEMORY_PRESSURE_AFTER_TRIGGERED = "MemoryPressureAfterTriggered"
    PRERENDERING_DISABLED_BY_DEV_TOOLS = "PrerenderingDisabledByDevTools"
    SPECULATION_RULE_REMOVED = "SpeculationRuleRemoved"
    ACTIVATED_WITH_AUXILIARY_BROWSING_CONTEXTS = "ActivatedWithAuxiliaryBrowsingContexts"
    MAX_NUM_OF_RUNNING_EAGER_PRERENDERS_EXCEEDED = "MaxNumOfRunningEagerPrerendersExceeded"
    MAX_NUM_OF_RUNNING_NON_EAGER_PRERENDERS_EXCEEDED = "MaxNumOfRunningNonEagerPrerendersExceeded"
    MAX_NUM_OF_RUNNING_EMBEDDER_PRERENDERS_EXCEEDED = "MaxNumOfRunningEmbedderPrerendersExceeded"
    PRERENDERING_URL_HAS_EFFECTIVE_URL = "PrerenderingUrlHasEffectiveUrl"
    REDIRECTED_PRERENDERING_URL_HAS_EFFECTIVE_URL = "RedirectedPrerenderingUrlHasEffectiveUrl"
    ACTIVATION_URL_HAS_EFFECTIVE_URL = "ActivationUrlHasEffectiveUrl"
    JAVA_SCRIPT_INTERFACE_ADDED = "JavaScriptInterfaceAdded"
    JAVA_SCRIPT_INTERFACE_REMOVED = "JavaScriptInterfaceRemoved"
    ALL_PRERENDERING_CANCELED = "AllPrerenderingCanceled"
    WINDOW_CLOSED = "WindowClosed"
    SLOW_NETWORK = "SlowNetwork"
    OTHER_PRERENDERED_PAGE_ACTIVATED = "OtherPrerenderedPageActivated"
    V8_OPTIMIZER_DISABLED = "V8OptimizerDisabled"
    PRERENDER_FAILED_DURING_PREFETCH = "PrerenderFailedDuringPrefetch"
    BROWSING_DATA_REMOVED = "BrowsingDataRemoved"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PreloadingStatus(enum.Enum):
    '''
    Preloading status values, see also PreloadingTriggeringOutcome. This
    status is shared by prefetchStatusUpdated and prerenderStatusUpdated.
    '''
    PENDING = "Pending"
    RUNNING = "Running"
    READY = "Ready"
    SUCCESS = "Success"
    FAILURE = "Failure"
    NOT_SUPPORTED = "NotSupported"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PrefetchStatus(enum.Enum):
    '''
    TODO(https://crbug.com/1384419): revisit the list of PrefetchStatus and
    filter out the ones that aren't necessary to the developers.
    '''
    PREFETCH_ALLOWED = "PrefetchAllowed"
    PREFETCH_FAILED_INELIGIBLE_REDIRECT = "PrefetchFailedIneligibleRedirect"
    PREFETCH_FAILED_INVALID_REDIRECT = "PrefetchFailedInvalidRedirect"
    PREFETCH_FAILED_MIME_NOT_SUPPORTED = "PrefetchFailedMIMENotSupported"
    PREFETCH_FAILED_NET_ERROR = "PrefetchFailedNetError"
    PREFETCH_FAILED_NON2_XX = "PrefetchFailedNon2XX"
    PREFETCH_EVICTED_AFTER_CANDIDATE_REMOVED = "PrefetchEvictedAfterCandidateRemoved"
    PREFETCH_EVICTED_FOR_NEWER_PREFETCH = "PrefetchEvictedForNewerPrefetch"
    PREFETCH_HELDBACK = "PrefetchHeldback"
    PREFETCH_INELIGIBLE_RETRY_AFTER = "PrefetchIneligibleRetryAfter"
    PREFETCH_IS_PRIVACY_DECOY = "PrefetchIsPrivacyDecoy"
    PREFETCH_IS_STALE = "PrefetchIsStale"
    PREFETCH_NOT_ELIGIBLE_BROWSER_CONTEXT_OFF_THE_RECORD = "PrefetchNotEligibleBrowserContextOffTheRecord"
    PREFETCH_NOT_ELIGIBLE_DATA_SAVER_ENABLED = "PrefetchNotEligibleDataSaverEnabled"
    PREFETCH_NOT_ELIGIBLE_EXISTING_PROXY = "PrefetchNotEligibleExistingProxy"
    PREFETCH_NOT_ELIGIBLE_HOST_IS_NON_UNIQUE = "PrefetchNotEligibleHostIsNonUnique"
    PREFETCH_NOT_ELIGIBLE_NON_DEFAULT_STORAGE_PARTITION = "PrefetchNotEligibleNonDefaultStoragePartition"
    PREFETCH_NOT_ELIGIBLE_SAME_SITE_CROSS_ORIGIN_PREFETCH_REQUIRED_PROXY = "PrefetchNotEligibleSameSiteCrossOriginPrefetchRequiredProxy"
    PREFETCH_NOT_ELIGIBLE_SCHEME_IS_NOT_HTTPS = "PrefetchNotEligibleSchemeIsNotHttps"
    PREFETCH_NOT_ELIGIBLE_USER_HAS_COOKIES = "PrefetchNotEligibleUserHasCookies"
    PREFETCH_NOT_ELIGIBLE_USER_HAS_SERVICE_WORKER = "PrefetchNotEligibleUserHasServiceWorker"
    PREFETCH_NOT_ELIGIBLE_BATTERY_SAVER_ENABLED = "PrefetchNotEligibleBatterySaverEnabled"
    PREFETCH_NOT_ELIGIBLE_PRELOADING_DISABLED = "PrefetchNotEligiblePreloadingDisabled"
    PREFETCH_NOT_FINISHED_IN_TIME = "PrefetchNotFinishedInTime"
    PREFETCH_NOT_STARTED = "PrefetchNotStarted"
    PREFETCH_NOT_USED_COOKIES_CHANGED = "PrefetchNotUsedCookiesChanged"
    PREFETCH_PROXY_NOT_AVAILABLE = "PrefetchProxyNotAvailable"
    PREFETCH_RESPONSE_USED = "PrefetchResponseUsed"
    PREFETCH_SUCCESSFUL_BUT_NOT_USED = "PrefetchSuccessfulButNotUsed"
    PREFETCH_NOT_USED_PROBE_FAILED = "PrefetchNotUsedProbeFailed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PrerenderMismatchedHeaders:
    '''
    Information of headers to be displayed when the header mismatch occurred.
    '''
    header_name: str

    initial_value: typing.Optional[str] = None

    activation_value: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['headerName'] = self.header_name
        if self.initial_value is not None:
            json['initialValue'] = self.initial_value
        if self.activation_value is not None:
            json['activationValue'] = self.activation_value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            header_name=str(json['headerName']),
            initial_value=str(json['initialValue']) if 'initialValue' in json else None,
            activation_value=str(json['activationValue']) if 'activationValue' in json else None,
        )


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Preload.enable',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Preload.disable',
    }
    json = yield cmd_dict


@event_class('Preload.ruleSetUpdated')
@dataclass
class RuleSetUpdated:
    '''
    Upsert. Currently, it is only emitted when a rule set added.
    '''
    rule_set: RuleSet

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RuleSetUpdated:
        return cls(
            rule_set=RuleSet.from_json(json['ruleSet'])
        )


@event_class('Preload.ruleSetRemoved')
@dataclass
class RuleSetRemoved:
    id_: RuleSetId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RuleSetRemoved:
        return cls(
            id_=RuleSetId.from_json(json['id'])
        )


@event_class('Preload.preloadEnabledStateUpdated')
@dataclass
class PreloadEnabledStateUpdated:
    '''
    Fired when a preload enabled state is updated.
    '''
    disabled_by_preference: bool
    disabled_by_data_saver: bool
    disabled_by_battery_saver: bool
    disabled_by_holdback_prefetch_speculation_rules: bool
    disabled_by_holdback_prerender_speculation_rules: bool

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PreloadEnabledStateUpdated:
        return cls(
            disabled_by_preference=bool(json['disabledByPreference']),
            disabled_by_data_saver=bool(json['disabledByDataSaver']),
            disabled_by_battery_saver=bool(json['disabledByBatterySaver']),
            disabled_by_holdback_prefetch_speculation_rules=bool(json['disabledByHoldbackPrefetchSpeculationRules']),
            disabled_by_holdback_prerender_speculation_rules=bool(json['disabledByHoldbackPrerenderSpeculationRules'])
        )


@event_class('Preload.prefetchStatusUpdated')
@dataclass
class PrefetchStatusUpdated:
    '''
    Fired when a prefetch attempt is updated.
    '''
    key: PreloadingAttemptKey
    pipeline_id: PreloadPipelineId
    #: The frame id of the frame initiating prefetch.
    initiating_frame_id: page.FrameId
    prefetch_url: str
    status: PreloadingStatus
    prefetch_status: PrefetchStatus
    request_id: network.RequestId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PrefetchStatusUpdated:
        return cls(
            key=PreloadingAttemptKey.from_json(json['key']),
            pipeline_id=PreloadPipelineId.from_json(json['pipelineId']),
            initiating_frame_id=page.FrameId.from_json(json['initiatingFrameId']),
            prefetch_url=str(json['prefetchUrl']),
            status=PreloadingStatus.from_json(json['status']),
            prefetch_status=PrefetchStatus.from_json(json['prefetchStatus']),
            request_id=network.RequestId.from_json(json['requestId'])
        )


@event_class('Preload.prerenderStatusUpdated')
@dataclass
class PrerenderStatusUpdated:
    '''
    Fired when a prerender attempt is updated.
    '''
    key: PreloadingAttemptKey
    pipeline_id: PreloadPipelineId
    status: PreloadingStatus
    prerender_status: typing.Optional[PrerenderFinalStatus]
    #: This is used to give users more information about the name of Mojo interface
    #: that is incompatible with prerender and has caused the cancellation of the attempt.
    disallowed_mojo_interface: typing.Optional[str]
    mismatched_headers: typing.Optional[typing.List[PrerenderMismatchedHeaders]]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PrerenderStatusUpdated:
        return cls(
            key=PreloadingAttemptKey.from_json(json['key']),
            pipeline_id=PreloadPipelineId.from_json(json['pipelineId']),
            status=PreloadingStatus.from_json(json['status']),
            prerender_status=PrerenderFinalStatus.from_json(json['prerenderStatus']) if 'prerenderStatus' in json else None,
            disallowed_mojo_interface=str(json['disallowedMojoInterface']) if 'disallowedMojoInterface' in json else None,
            mismatched_headers=[PrerenderMismatchedHeaders.from_json(i) for i in json['mismatchedHeaders']] if 'mismatchedHeaders' in json else None
        )


@event_class('Preload.preloadingAttemptSourcesUpdated')
@dataclass
class PreloadingAttemptSourcesUpdated:
    '''
    Send a list of sources for all preloading attempts in a document.
    '''
    loader_id: network.LoaderId
    preloading_attempt_sources: typing.List[PreloadingAttemptSource]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PreloadingAttemptSourcesUpdated:
        return cls(
            loader_id=network.LoaderId.from_json(json['loaderId']),
            preloading_attempt_sources=[PreloadingAttemptSource.from_json(i) for i in json['preloadingAttemptSources']]
        )

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\cmd.py ===
"""distutils.cmd

Provides the Command class, the base class for the command classes
in the distutils.command package.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from abc import abstractmethod
from collections.abc import Callable, MutableSequence
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, overload

from . import _modified, archive_util, dir_util, file_util, util
from ._log import log
from .errors import DistutilsOptionError

if TYPE_CHECKING:
    # type-only import because of mutual dependence between these classes
    from distutils.dist import Distribution

    from typing_extensions import TypeVarTuple, Unpack

    _Ts = TypeVarTuple("_Ts")

_StrPathT = TypeVar("_StrPathT", bound="str | os.PathLike[str]")
_BytesPathT = TypeVar("_BytesPathT", bound="bytes | os.PathLike[bytes]")
_CommandT = TypeVar("_CommandT", bound="Command")


class Command:
    """Abstract base class for defining command classes, the "worker bees"
    of the Distutils.  A useful analogy for command classes is to think of
    them as subroutines with local variables called "options".  The options
    are "declared" in 'initialize_options()' and "defined" (given their
    final values, aka "finalized") in 'finalize_options()', both of which
    must be defined by every command class.  The distinction between the
    two is necessary because option values might come from the outside
    world (command line, config file, ...), and any options dependent on
    other options must be computed *after* these outside influences have
    been processed -- hence 'finalize_options()'.  The "body" of the
    subroutine, where it does all its work based on the values of its
    options, is the 'run()' method, which must also be implemented by every
    command class.
    """

    # 'sub_commands' formalizes the notion of a "family" of commands,
    # eg. "install" as the parent with sub-commands "install_lib",
    # "install_headers", etc.  The parent of a family of commands
    # defines 'sub_commands' as a class attribute; it's a list of
    #    (command_name : string, predicate : unbound_method | string | None)
    # tuples, where 'predicate' is a method of the parent command that
    # determines whether the corresponding command is applicable in the
    # current situation.  (Eg. we "install_headers" is only applicable if
    # we have any C header files to install.)  If 'predicate' is None,
    # that command is always applicable.
    #
    # 'sub_commands' is usually defined at the *end* of a class, because
    # predicates can be unbound methods, so they must already have been
    # defined.  The canonical example is the "install" command.
    sub_commands: ClassVar[  # Any to work around variance issues
        list[tuple[str, Callable[[Any], bool] | None]]
    ] = []

    user_options: ClassVar[
        # Specifying both because list is invariant. Avoids mypy override assignment issues
        list[tuple[str, str, str]] | list[tuple[str, str | None, str]]
    ] = []

    # -- Creation/initialization methods -------------------------------

    def __init__(self, dist: Distribution) -> None:
        """Create and initialize a new Command object.  Most importantly,
        invokes the 'initialize_options()' method, which is the real
        initializer and depends on the actual command being
        instantiated.
        """
        # late import because of mutual dependence between these classes
        from distutils.dist import Distribution

        if not isinstance(dist, Distribution):
            raise TypeError("dist must be a Distribution instance")
        if self.__class__ is Command:
            raise RuntimeError("Command is an abstract class")

        self.distribution = dist
        self.initialize_options()

        # Per-command versions of the global flags, so that the user can
        # customize Distutils' behaviour command-by-command and let some
        # commands fall back on the Distribution's behaviour.  None means
        # "not defined, check self.distribution's copy", while 0 or 1 mean
        # false and true (duh).  Note that this means figuring out the real
        # value of each flag is a touch complicated -- hence "self._dry_run"
        # will be handled by __getattr__, below.
        # XXX This needs to be fixed.
        self._dry_run = None

        # verbose is largely ignored, but needs to be set for
        # backwards compatibility (I think)?
        self.verbose = dist.verbose

        # Some commands define a 'self.force' option to ignore file
        # timestamps, but methods defined *here* assume that
        # 'self.force' exists for all commands.  So define it here
        # just to be safe.
        self.force = None

        # The 'help' flag is just used for command-line parsing, so
        # none of that complicated bureaucracy is needed.
        self.help = False

        # 'finalized' records whether or not 'finalize_options()' has been
        # called.  'finalize_options()' itself should not pay attention to
        # this flag: it is the business of 'ensure_finalized()', which
        # always calls 'finalize_options()', to respect/update it.
        self.finalized = False

    # XXX A more explicit way to customize dry_run would be better.
    def __getattr__(self, attr):
        if attr == 'dry_run':
            myval = getattr(self, "_" + attr)
            if myval is None:
                return getattr(self.distribution, attr)
            else:
                return myval
        else:
            raise AttributeError(attr)

    def ensure_finalized(self) -> None:
        if not self.finalized:
            self.finalize_options()
        self.finalized = True

    # Subclasses must define:
    #   initialize_options()
    #     provide default values for all options; may be customized by
    #     setup script, by options from config file(s), or by command-line
    #     options
    #   finalize_options()
    #     decide on the final values for all options; this is called
    #     after all possible intervention from the outside world
    #     (command-line, option file, etc.) has been processed
    #   run()
    #     run the command: do whatever it is we're here to do,
    #     controlled by the command's various option values

    @abstractmethod
    def initialize_options(self) -> None:
        """Set default values for all the options that this command
        supports.  Note that these defaults may be overridden by other
        commands, by the setup script, by config files, or by the
        command-line.  Thus, this is not the place to code dependencies
        between options; generally, 'initialize_options()' implementations
        are just a bunch of "self.foo = None" assignments.

        This method must be implemented by all command classes.
        """
        raise RuntimeError(
            f"abstract method -- subclass {self.__class__} must override"
        )

    @abstractmethod
    def finalize_options(self) -> None:
        """Set final values for all the options that this command supports.
        This is always called as late as possible, ie.  after any option
        assignments from the command-line or from other commands have been
        done.  Thus, this is the place to code option dependencies: if
        'foo' depends on 'bar', then it is safe to set 'foo' from 'bar' as
        long as 'foo' still has the same value it was assigned in
        'initialize_options()'.

        This method must be implemented by all command classes.
        """
        raise RuntimeError(
            f"abstract method -- subclass {self.__class__} must override"
        )

    def dump_options(self, header=None, indent=""):
        from distutils.fancy_getopt import longopt_xlate

        if header is None:
            header = f"command options for '{self.get_command_name()}':"
        self.announce(indent + header, level=logging.INFO)
        indent = indent + "  "
        for option, _, _ in self.user_options:
            option = option.translate(longopt_xlate)
            if option[-1] == "=":
                option = option[:-1]
            value = getattr(self, option)
            self.announce(indent + f"{option} = {value}", level=logging.INFO)

    @abstractmethod
    def run(self) -> None:
        """A command's raison d'etre: carry out the action it exists to
        perform, controlled by the options initialized in
        'initialize_options()', customized by other commands, the setup
        script, the command-line, and config files, and finalized in
        'finalize_options()'.  All terminal output and filesystem
        interaction should be done by 'run()'.

        This method must be implemented by all command classes.
        """
        raise RuntimeError(
            f"abstract method -- subclass {self.__class__} must override"
        )

    def announce(self, msg: object, level: int = logging.DEBUG) -> None:
        log.log(level, msg)

    def debug_print(self, msg: object) -> None:
        """Print 'msg' to stdout if the global DEBUG (taken from the
        DISTUTILS_DEBUG environment variable) flag is true.
        """
        from distutils.debug import DEBUG

        if DEBUG:
            print(msg)
            sys.stdout.flush()

    # -- Option validation methods -------------------------------------
    # (these are very handy in writing the 'finalize_options()' method)
    #
    # NB. the general philosophy here is to ensure that a particular option
    # value meets certain type and value constraints.  If not, we try to
    # force it into conformance (eg. if we expect a list but have a string,
    # split the string on comma and/or whitespace).  If we can't force the
    # option into conformance, raise DistutilsOptionError.  Thus, command
    # classes need do nothing more than (eg.)
    #   self.ensure_string_list('foo')
    # and they can be guaranteed that thereafter, self.foo will be
    # a list of strings.

    def _ensure_stringlike(self, option, what, default=None):
        val = getattr(self, option)
        if val is None:
            setattr(self, option, default)
            return default
        elif not isinstance(val, str):
            raise DistutilsOptionError(f"'{option}' must be a {what} (got `{val}`)")
        return val

    def ensure_string(self, option: str, default: str | None = None) -> None:
        """Ensure that 'option' is a string; if not defined, set it to
        'default'.
        """
        self._ensure_stringlike(option, "string", default)

    def ensure_string_list(self, option: str) -> None:
        r"""Ensure that 'option' is a list of strings.  If 'option' is
        currently a string, we split it either on /,\s*/ or /\s+/, so
        "foo bar baz", "foo,bar,baz", and "foo,   bar baz" all become
        ["foo", "bar", "baz"].
        """
        val = getattr(self, option)
        if val is None:
            return
        elif isinstance(val, str):
            setattr(self, option, re.split(r',\s*|\s+', val))
        else:
            if isinstance(val, list):
                ok = all(isinstance(v, str) for v in val)
            else:
                ok = False
            if not ok:
                raise DistutilsOptionError(
                    f"'{option}' must be a list of strings (got {val!r})"
                )

    def _ensure_tested_string(self, option, tester, what, error_fmt, default=None):
        val = self._ensure_stringlike(option, what, default)
        if val is not None and not tester(val):
            raise DistutilsOptionError(
                ("error in '%s' option: " + error_fmt) % (option, val)
            )

    def ensure_filename(self, option: str) -> None:
        """Ensure that 'option' is the name of an existing file."""
        self._ensure_tested_string(
            option, os.path.isfile, "filename", "'%s' does not exist or is not a file"
        )

    def ensure_dirname(self, option: str) -> None:
        self._ensure_tested_string(
            option,
            os.path.isdir,
            "directory name",
            "'%s' does not exist or is not a directory",
        )

    # -- Convenience methods for commands ------------------------------

    def get_command_name(self) -> str:
        if hasattr(self, 'command_name'):
            return self.command_name
        else:
            return self.__class__.__name__

    def set_undefined_options(
        self, src_cmd: str, *option_pairs: tuple[str, str]
    ) -> None:
        """Set the values of any "undefined" options from corresponding
        option values in some other command object.  "Undefined" here means
        "is None", which is the convention used to indicate that an option
        has not been changed between 'initialize_options()' and
        'finalize_options()'.  Usually called from 'finalize_options()' for
        options that depend on some other command rather than another
        option of the same command.  'src_cmd' is the other command from
        which option values will be taken (a command object will be created
        for it if necessary); the remaining arguments are
        '(src_option,dst_option)' tuples which mean "take the value of
        'src_option' in the 'src_cmd' command object, and copy it to
        'dst_option' in the current command object".
        """
        # Option_pairs: list of (src_option, dst_option) tuples
        src_cmd_obj = self.distribution.get_command_obj(src_cmd)
        src_cmd_obj.ensure_finalized()
        for src_option, dst_option in option_pairs:
            if getattr(self, dst_option) is None:
                setattr(self, dst_option, getattr(src_cmd_obj, src_option))

    # NOTE: Because distutils is private to Setuptools and not all commands are exposed here,
    # not every possible command is enumerated in the signature.
    def get_finalized_command(self, command: str, create: bool = True) -> Command:
        """Wrapper around Distribution's 'get_command_obj()' method: find
        (create if necessary and 'create' is true) the command object for
        'command', call its 'ensure_finalized()' method, and return the
        finalized command object.
        """
        cmd_obj = self.distribution.get_command_obj(command, create)
        cmd_obj.ensure_finalized()
        return cmd_obj

    # XXX rename to 'get_reinitialized_command()'? (should do the
    # same in dist.py, if so)
    @overload
    def reinitialize_command(
        self, command: str, reinit_subcommands: bool = False
    ) -> Command: ...
    @overload
    def reinitialize_command(
        self, command: _CommandT, reinit_subcommands: bool = False
    ) -> _CommandT: ...
    def reinitialize_command(
        self, command: str | Command, reinit_subcommands=False
    ) -> Command:
        return self.distribution.reinitialize_command(command, reinit_subcommands)

    def run_command(self, command: str) -> None:
        """Run some other command: uses the 'run_command()' method of
        Distribution, which creates and finalizes the command object if
        necessary and then invokes its 'run()' method.
        """
        self.distribution.run_command(command)

    def get_sub_commands(self) -> list[str]:
        """Determine the sub-commands that are relevant in the current
        distribution (ie., that need to be run).  This is based on the
        'sub_commands' class attribute: each tuple in that list may include
        a method that we call to determine if the subcommand needs to be
        run for the current distribution.  Return a list of command names.
        """
        commands = []
        for cmd_name, method in self.sub_commands:
            if method is None or method(self):
                commands.append(cmd_name)
        return commands

    # -- External world manipulation -----------------------------------

    def warn(self, msg: object) -> None:
        log.warning("warning: %s: %s\n", self.get_command_name(), msg)

    def execute(
        self,
        func: Callable[[Unpack[_Ts]], object],
        args: tuple[Unpack[_Ts]],
        msg: object = None,
        level: int = 1,
    ) -> None:
        util.execute(func, args, msg, dry_run=self.dry_run)

    def mkpath(self, name: str, mode: int = 0o777) -> None:
        dir_util.mkpath(name, mode, dry_run=self.dry_run)

    @overload
    def copy_file(
        self,
        infile: str | os.PathLike[str],
        outfile: _StrPathT,
        preserve_mode: bool = True,
        preserve_times: bool = True,
        link: str | None = None,
        level: int = 1,
    ) -> tuple[_StrPathT | str, bool]: ...
    @overload
    def copy_file(
        self,
        infile: bytes | os.PathLike[bytes],
        outfile: _BytesPathT,
        preserve_mode: bool = True,
        preserve_times: bool = True,
        link: str | None = None,
        level: int = 1,
    ) -> tuple[_BytesPathT | bytes, bool]: ...
    def copy_file(
        self,
        infile: str | os.PathLike[str] | bytes | os.PathLike[bytes],
        outfile: str | os.PathLike[str] | bytes | os.PathLike[bytes],
        preserve_mode: bool = True,
        preserve_times: bool = True,
        link: str | None = None,
        level: int = 1,
    ) -> tuple[str | os.PathLike[str] | bytes | os.PathLike[bytes], bool]:
        """Copy a file respecting verbose, dry-run and force flags.  (The
        former two default to whatever is in the Distribution object, and
        the latter defaults to false for commands that don't define it.)"""
        return file_util.copy_file(
            infile,
            outfile,
            preserve_mode,
            preserve_times,
            not self.force,
            link,
            dry_run=self.dry_run,
        )

    def copy_tree(
        self,
        infile: str | os.PathLike[str],
        outfile: str,
        preserve_mode: bool = True,
        preserve_times: bool = True,
        preserve_symlinks: bool = False,
        level: int = 1,
    ) -> list[str]:
        """Copy an entire directory tree respecting verbose, dry-run,
        and force flags.
        """
        return dir_util.copy_tree(
            infile,
            outfile,
            preserve_mode,
            preserve_times,
            preserve_symlinks,
            not self.force,
            dry_run=self.dry_run,
        )

    @overload
    def move_file(
        self, src: str | os.PathLike[str], dst: _StrPathT, level: int = 1
    ) -> _StrPathT | str: ...
    @overload
    def move_file(
        self, src: bytes | os.PathLike[bytes], dst: _BytesPathT, level: int = 1
    ) -> _BytesPathT | bytes: ...
    def move_file(
        self,
        src: str | os.PathLike[str] | bytes | os.PathLike[bytes],
        dst: str | os.PathLike[str] | bytes | os.PathLike[bytes],
        level: int = 1,
    ) -> str | os.PathLike[str] | bytes | os.PathLike[bytes]:
        """Move a file respecting dry-run flag."""
        return file_util.move_file(src, dst, dry_run=self.dry_run)

    def spawn(
        self, cmd: MutableSequence[str], search_path: bool = True, level: int = 1
    ) -> None:
        """Spawn an external command respecting dry-run flag."""
        from distutils.spawn import spawn

        spawn(cmd, search_path, dry_run=self.dry_run)

    @overload
    def make_archive(
        self,
        base_name: str,
        format: str,
        root_dir: str | os.PathLike[str] | bytes | os.PathLike[bytes] | None = None,
        base_dir: str | None = None,
        owner: str | None = None,
        group: str | None = None,
    ) -> str: ...
    @overload
    def make_archive(
        self,
        base_name: str | os.PathLike[str],
        format: str,
        root_dir: str | os.PathLike[str] | bytes | os.PathLike[bytes],
        base_dir: str | None = None,
        owner: str | None = None,
        group: str | None = None,
    ) -> str: ...
    def make_archive(
        self,
        base_name: str | os.PathLike[str],
        format: str,
        root_dir: str | os.PathLike[str] | bytes | os.PathLike[bytes] | None = None,
        base_dir: str | None = None,
        owner: str | None = None,
        group: str | None = None,
    ) -> str:
        return archive_util.make_archive(
            base_name,
            format,
            root_dir,
            base_dir,
            dry_run=self.dry_run,
            owner=owner,
            group=group,
        )

    def make_file(
        self,
        infiles: str | list[str] | tuple[str, ...],
        outfile: str | os.PathLike[str] | bytes | os.PathLike[bytes],
        func: Callable[[Unpack[_Ts]], object],
        args: tuple[Unpack[_Ts]],
        exec_msg: object = None,
        skip_msg: object = None,
        level: int = 1,
    ) -> None:
        """Special case of 'execute()' for operations that process one or
        more input files and generate one output file.  Works just like
        'execute()', except the operation is skipped and a different
        message printed if 'outfile' already exists and is newer than all
        files listed in 'infiles'.  If the command defined 'self.force',
        and it is true, then the command is unconditionally run -- does no
        timestamp checks.
        """
        if skip_msg is None:
            skip_msg = f"skipping {outfile} (inputs unchanged)"

        # Allow 'infiles' to be a single string
        if isinstance(infiles, str):
            infiles = (infiles,)
        elif not isinstance(infiles, (list, tuple)):
            raise TypeError("'infiles' must be a string, or a list or tuple of strings")

        if exec_msg is None:
            exec_msg = "generating {} from {}".format(outfile, ', '.join(infiles))

        # If 'outfile' must be regenerated (either because it doesn't
        # exist, is out-of-date, or the 'force' flag is true) then
        # perform the action that presumably regenerates it
        if self.force or _modified.newer_group(infiles, outfile):
            self.execute(func, args, exec_msg, level)
        # Otherwise, print the "skip" message
        else:
            log.debug(skip_msg)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevconsole_code.py ===
"""
A copy of the code module in the standard library with some changes to work with
async evaluation.

Utilities needed to emulate Python's interactive interpreter.
"""

# Inspired by similar code by Jeff Epler and Fredrik Lundh.

import sys
import traceback
import inspect

# START --------------------------- from codeop import CommandCompiler, compile_command
# START --------------------------- from codeop import CommandCompiler, compile_command
# START --------------------------- from codeop import CommandCompiler, compile_command
# START --------------------------- from codeop import CommandCompiler, compile_command
# START --------------------------- from codeop import CommandCompiler, compile_command
r"""Utilities to compile possibly incomplete Python source code.

This module provides two interfaces, broadly similar to the builtin
function compile(), which take program text, a filename and a 'mode'
and:

- Return code object if the command is complete and valid
- Return None if the command is incomplete
- Raise SyntaxError, ValueError or OverflowError if the command is a
  syntax error (OverflowError and ValueError can be produced by
  malformed literals).

Approach:

First, check if the source consists entirely of blank lines and
comments; if so, replace it with 'pass', because the built-in
parser doesn't always do the right thing for these.

Compile three times: as is, with \n, and with \n\n appended.  If it
compiles as is, it's complete.  If it compiles with one \n appended,
we expect more.  If it doesn't compile either way, we compare the
error we get when compiling with \n or \n\n appended.  If the errors
are the same, the code is broken.  But if the errors are different, we
expect more.  Not intuitive; not even guaranteed to hold in future
releases; but this matches the compiler's behavior from Python 1.4
through 2.2, at least.

Caveat:

It is possible (but not likely) that the parser stops parsing with a
successful outcome before reaching the end of the source; in this
case, trailing symbols may be ignored instead of causing an error.
For example, a backslash followed by two newlines may be followed by
arbitrary garbage.  This will be fixed once the API for the parser is
better.

The two interfaces are:

compile_command(source, filename, symbol):

    Compiles a single command in the manner described above.

CommandCompiler():

    Instances of this class have __call__ methods identical in
    signature to compile_command; the difference is that if the
    instance compiles program text containing a __future__ statement,
    the instance 'remembers' and compiles all subsequent program texts
    with the statement in force.

The module also provides another class:

Compile():

    Instances of this class act like the built-in function compile,
    but with 'memory' in the sense described above.
"""

import __future__

_features = [getattr(__future__, fname) for fname in __future__.all_feature_names]

__all__ = ["compile_command", "Compile", "CommandCompiler"]

PyCF_DONT_IMPLY_DEDENT = 0x200  # Matches pythonrun.h


def _maybe_compile(compiler, source, filename, symbol):
    # Check for source consisting of only blank lines and comments
    for line in source.split("\n"):
        line = line.strip()
        if line and line[0] != "#":
            break  # Leave it alone
    else:
        if symbol != "eval":
            source = "pass"  # Replace it with a 'pass' statement

    err = err1 = err2 = None
    code = code1 = code2 = None

    try:
        code = compiler(source, filename, symbol)
    except SyntaxError as err:
        pass

    try:
        code1 = compiler(source + "\n", filename, symbol)
    except SyntaxError as e:
        err1 = e

    try:
        code2 = compiler(source + "\n\n", filename, symbol)
    except SyntaxError as e:
        err2 = e

    try:
        if code:
            return code
        if not code1 and repr(err1) == repr(err2):
            raise err1
    finally:
        err1 = err2 = None


def _compile(source, filename, symbol):
    return compile(source, filename, symbol, PyCF_DONT_IMPLY_DEDENT)


def compile_command(source, filename="<input>", symbol="single"):
    r"""Compile a command and determine whether it is incomplete.

    Arguments:

    source -- the source string; may contain \n characters
    filename -- optional filename from which source was read; default
                "<input>"
    symbol -- optional grammar start symbol; "single" (default) or "eval"

    Return value / exceptions raised:

    - Return a code object if the command is complete and valid
    - Return None if the command is incomplete
    - Raise SyntaxError, ValueError or OverflowError if the command is a
      syntax error (OverflowError and ValueError can be produced by
      malformed literals).
    """
    return _maybe_compile(_compile, source, filename, symbol)


class Compile:
    """Instances of this class behave much like the built-in compile
    function, but if one is used to compile text containing a future
    statement, it "remembers" and compiles all subsequent program texts
    with the statement in force."""

    def __init__(self):
        self.flags = PyCF_DONT_IMPLY_DEDENT

        try:
            from ast import PyCF_ALLOW_TOP_LEVEL_AWAIT

            self.flags |= PyCF_ALLOW_TOP_LEVEL_AWAIT
        except:
            pass

    def __call__(self, source, filename, symbol):
        codeob = compile(source, filename, symbol, self.flags, 1)
        for feature in _features:
            if codeob.co_flags & feature.compiler_flag:
                self.flags |= feature.compiler_flag
        return codeob


class CommandCompiler:
    """Instances of this class have __call__ methods identical in
    signature to compile_command; the difference is that if the
    instance compiles program text containing a __future__ statement,
    the instance 'remembers' and compiles all subsequent program texts
    with the statement in force."""

    def __init__(
        self,
    ):
        self.compiler = Compile()

    def __call__(self, source, filename="<input>", symbol="single"):
        r"""Compile a command and determine whether it is incomplete.

        Arguments:

        source -- the source string; may contain \n characters
        filename -- optional filename from which source was read;
                    default "<input>"
        symbol -- optional grammar start symbol; "single" (default) or
                  "eval"

        Return value / exceptions raised:

        - Return a code object if the command is complete and valid
        - Return None if the command is incomplete
        - Raise SyntaxError, ValueError or OverflowError if the command is a
          syntax error (OverflowError and ValueError can be produced by
          malformed literals).
        """
        return _maybe_compile(self.compiler, source, filename, symbol)


# END --------------------------- from codeop import CommandCompiler, compile_command
# END --------------------------- from codeop import CommandCompiler, compile_command
# END --------------------------- from codeop import CommandCompiler, compile_command
# END --------------------------- from codeop import CommandCompiler, compile_command
# END --------------------------- from codeop import CommandCompiler, compile_command


__all__ = ["InteractiveInterpreter", "InteractiveConsole", "interact", "compile_command"]

from _pydev_bundle._pydev_saved_modules import threading


class _EvalAwaitInNewEventLoop(threading.Thread):
    def __init__(self, compiled, updated_globals, updated_locals):
        threading.Thread.__init__(self)
        self.daemon = True
        self._compiled = compiled
        self._updated_globals = updated_globals
        self._updated_locals = updated_locals

        # Output
        self.evaluated_value = None
        self.exc = None

    async def _async_func(self):
        return await eval(self._compiled, self._updated_locals, self._updated_globals)

    def run(self):
        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.evaluated_value = asyncio.run(self._async_func())
        except:
            self.exc = sys.exc_info()


class InteractiveInterpreter:
    """Base class for InteractiveConsole.

    This class deals with parsing and interpreter state (the user's
    namespace); it doesn't deal with input buffering or prompting or
    input file naming (the filename is always passed in explicitly).

    """

    def __init__(self, locals=None):
        """Constructor.

        The optional 'locals' argument specifies the dictionary in
        which code will be executed; it defaults to a newly created
        dictionary with key "__name__" set to "__console__" and key
        "__doc__" set to None.

        """
        if locals is None:
            locals = {"__name__": "__console__", "__doc__": None}
        self.locals = locals
        self.compile = CommandCompiler()

    def runsource(self, source, filename="<input>", symbol="single"):
        """Compile and run some source in the interpreter.

        Arguments are as for compile_command().

        One of several things can happen:

        1) The input is incorrect; compile_command() raised an
        exception (SyntaxError or OverflowError).  A syntax traceback
        will be printed by calling the showsyntaxerror() method.

        2) The input is incomplete, and more input is required;
        compile_command() returned None.  Nothing happens.

        3) The input is complete; compile_command() returned a code
        object.  The code is executed by calling self.runcode() (which
        also handles run-time exceptions, except for SystemExit).

        The return value is True in case 2, False in the other cases (unless
        an exception is raised).  The return value can be used to
        decide whether to use sys.ps1 or sys.ps2 to prompt the next
        line.

        """
        try:
            code = self.compile(source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            # Case 1
            self.showsyntaxerror(filename)
            return False

        if code is None:
            # Case 2
            return True

        # Case 3
        self.runcode(code)
        return False

    def runcode(self, code):
        """Execute a code object.

        When an exception occurs, self.showtraceback() is called to
        display a traceback.  All exceptions are caught except
        SystemExit, which is reraised.

        A note about KeyboardInterrupt: this exception may occur
        elsewhere in this code, and may not always be caught.  The
        caller should be prepared to deal with it.

        """
        try:
            is_async = False
            if hasattr(inspect, "CO_COROUTINE"):
                is_async = inspect.CO_COROUTINE & code.co_flags == inspect.CO_COROUTINE

            if is_async:
                t = _EvalAwaitInNewEventLoop(code, self.locals, None)
                t.start()
                t.join()

                if t.exc:
                    raise t.exc[1].with_traceback(t.exc[2])

            else:
                exec(code, self.locals)
        except SystemExit:
            raise
        except:
            self.showtraceback()

    def showsyntaxerror(self, filename=None):
        """Display the syntax error that just occurred.

        This doesn't display a stack trace because there isn't one.

        If a filename is given, it is stuffed in the exception instead
        of what was there before (because Python's parser always uses
        "<string>" when reading from a string).

        The output is written by self.write(), below.

        """
        type, value, tb = sys.exc_info()
        sys.last_type = type
        sys.last_value = value
        sys.last_traceback = tb
        if filename and type is SyntaxError:
            # Work hard to stuff the correct filename in the exception
            try:
                msg, (dummy_filename, lineno, offset, line) = value.args
            except ValueError:
                # Not the format we expect; leave it alone
                pass
            else:
                # Stuff in the right filename
                value = SyntaxError(msg, (filename, lineno, offset, line))
                sys.last_value = value
        if sys.excepthook is sys.__excepthook__:
            lines = traceback.format_exception_only(type, value)
            self.write("".join(lines))
        else:
            # If someone has set sys.excepthook, we let that take precedence
            # over self.write
            sys.excepthook(type, value, tb)

    def showtraceback(self):
        """Display the exception that just occurred.

        We remove the first stack item because it is our own code.

        The output is written by self.write(), below.

        """
        sys.last_type, sys.last_value, last_tb = ei = sys.exc_info()
        sys.last_traceback = last_tb
        try:
            lines = traceback.format_exception(ei[0], ei[1], last_tb.tb_next)
            if sys.excepthook is sys.__excepthook__:
                self.write("".join(lines))
            else:
                # If someone has set sys.excepthook, we let that take precedence
                # over self.write
                sys.excepthook(ei[0], ei[1], last_tb)
        finally:
            last_tb = ei = None

    def write(self, data):
        """Write a string.

        The base implementation writes to sys.stderr; a subclass may
        replace this with a different implementation.

        """
        sys.stderr.write(data)


class InteractiveConsole(InteractiveInterpreter):
    """Closely emulate the behavior of the interactive Python interpreter.

    This class builds on InteractiveInterpreter and adds prompting
    using the familiar sys.ps1 and sys.ps2, and input buffering.

    """

    def __init__(self, locals=None, filename="<console>"):
        """Constructor.

        The optional locals argument will be passed to the
        InteractiveInterpreter base class.

        The optional filename argument should specify the (file)name
        of the input stream; it will show up in tracebacks.

        """
        InteractiveInterpreter.__init__(self, locals)
        self.filename = filename
        self.resetbuffer()

    def resetbuffer(self):
        """Reset the input buffer."""
        self.buffer = []

    def interact(self, banner=None, exitmsg=None):
        """Closely emulate the interactive Python console.

        The optional banner argument specifies the banner to print
        before the first interaction; by default it prints a banner
        similar to the one printed by the real Python interpreter,
        followed by the current class name in parentheses (so as not
        to confuse this with the real interpreter -- since it's so
        close!).

        The optional exitmsg argument specifies the exit message
        printed when exiting. Pass the empty string to suppress
        printing an exit message. If exitmsg is not given or None,
        a default message is printed.

        """
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "
        cprt = 'Type "help", "copyright", "credits" or "license" for more information.'
        if banner is None:
            self.write("Python %s on %s\n%s\n(%s)\n" % (sys.version, sys.platform, cprt, self.__class__.__name__))
        elif banner:
            self.write("%s\n" % str(banner))
        more = 0
        while 1:
            try:
                if more:
                    prompt = sys.ps2
                else:
                    prompt = sys.ps1
                try:
                    line = self.raw_input(prompt)
                except EOFError:
                    self.write("\n")
                    break
                else:
                    more = self.push(line)
            except KeyboardInterrupt:
                self.write("\nKeyboardInterrupt\n")
                self.resetbuffer()
                more = 0
        if exitmsg is None:
            self.write("now exiting %s...\n" % self.__class__.__name__)
        elif exitmsg != "":
            self.write("%s\n" % exitmsg)

    def push(self, line):
        """Push a line to the interpreter.

        The line should not have a trailing newline; it may have
        internal newlines.  The line is appended to a buffer and the
        interpreter's runsource() method is called with the
        concatenated contents of the buffer as source.  If this
        indicates that the command was executed or invalid, the buffer
        is reset; otherwise, the command is incomplete, and the buffer
        is left as it was after the line was appended.  The return
        value is 1 if more input is required, 0 if the line was dealt
        with in some way (this is the same as runsource()).

        """
        self.buffer.append(line)
        source = "\n".join(self.buffer)
        more = self.runsource(source, self.filename)
        if not more:
            self.resetbuffer()
        return more

    def raw_input(self, prompt=""):
        """Write a prompt and read a line.

        The returned line does not include the trailing newline.
        When the user enters the EOF key sequence, EOFError is raised.

        The base implementation uses the built-in function
        input(); a subclass may replace this with a different
        implementation.

        """
        return input(prompt)


def interact(banner=None, readfunc=None, local=None, exitmsg=None):
    """Closely emulate the interactive Python interpreter.

    This is a backwards compatible interface to the InteractiveConsole
    class.  When readfunc is not specified, it attempts to import the
    readline module to enable GNU readline if it is available.

    Arguments (all optional, all default to None):

    banner -- passed to InteractiveConsole.interact()
    readfunc -- if not None, replaces InteractiveConsole.raw_input()
    local -- passed to InteractiveInterpreter.__init__()
    exitmsg -- passed to InteractiveConsole.interact()

    """
    console = InteractiveConsole(local)
    if readfunc is not None:
        console.raw_input = readfunc
    else:
        try:
            import readline
        except ImportError:
            pass
    console.interact(banner, exitmsg)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-q", action="store_true", help="don't print version and copyright messages")
    args = parser.parse_args()
    if args.q or sys.flags.quiet:
        banner = ""
    else:
        banner = None
    interact(banner)

# === NexusCore/openenv\Lib\site-packages\nltk\sem\drt_glue_demo.py ===
# Natural Language Toolkit: GUI Demo for Glue Semantics with Discourse
#                           Representation Theory (DRT) as meaning language
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

try:
    from tkinter import Button, Frame, IntVar, Label, Listbox, Menu, Scrollbar, Tk
    from tkinter.font import Font

    from nltk.draw.util import CanvasFrame, ShowText

except ImportError:
    """Ignore ImportError because tkinter might not be available."""

from nltk.parse import MaltParser
from nltk.sem.drt import DrsDrawer, DrtVariableExpression
from nltk.sem.glue import DrtGlue
from nltk.sem.logic import Variable
from nltk.tag import RegexpTagger
from nltk.util import in_idle


class DrtGlueDemo:
    def __init__(self, examples):
        # Set up the main window.
        self._top = Tk()
        self._top.title("DRT Glue Demo")

        # Set up key bindings.
        self._init_bindings()

        # Initialize the fonts.self._error = None
        self._init_fonts(self._top)

        self._examples = examples
        self._readingCache = [None for example in examples]

        # The user can hide the grammar.
        self._show_grammar = IntVar(self._top)
        self._show_grammar.set(1)

        # Set the data to None
        self._curExample = -1
        self._readings = []
        self._drs = None
        self._drsWidget = None
        self._error = None

        self._init_glue()

        # Create the basic frames.
        self._init_menubar(self._top)
        self._init_buttons(self._top)
        self._init_exampleListbox(self._top)
        self._init_readingListbox(self._top)
        self._init_canvas(self._top)

        # Resize callback
        self._canvas.bind("<Configure>", self._configure)

    #########################################
    ##  Initialization Helpers
    #########################################

    def _init_glue(self):
        tagger = RegexpTagger(
            [
                ("^(David|Mary|John)$", "NNP"),
                (
                    "^(walks|sees|eats|chases|believes|gives|sleeps|chases|persuades|tries|seems|leaves)$",
                    "VB",
                ),
                ("^(go|order|vanish|find|approach)$", "VB"),
                ("^(a)$", "ex_quant"),
                ("^(every)$", "univ_quant"),
                ("^(sandwich|man|dog|pizza|unicorn|cat|senator)$", "NN"),
                ("^(big|gray|former)$", "JJ"),
                ("^(him|himself)$", "PRP"),
            ]
        )

        depparser = MaltParser(tagger=tagger)
        self._glue = DrtGlue(depparser=depparser, remove_duplicates=False)

    def _init_fonts(self, root):
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(root)
        self._size.set(self._sysfont.cget("size"))

        self._boldfont = Font(family="helvetica", weight="bold", size=self._size.get())
        self._font = Font(family="helvetica", size=self._size.get())
        if self._size.get() < 0:
            big = self._size.get() - 2
        else:
            big = self._size.get() + 2
        self._bigfont = Font(family="helvetica", weight="bold", size=big)

    def _init_exampleListbox(self, parent):
        self._exampleFrame = listframe = Frame(parent)
        self._exampleFrame.pack(fill="both", side="left", padx=2)
        self._exampleList_label = Label(
            self._exampleFrame, font=self._boldfont, text="Examples"
        )
        self._exampleList_label.pack()
        self._exampleList = Listbox(
            self._exampleFrame,
            selectmode="single",
            relief="groove",
            background="white",
            foreground="#909090",
            font=self._font,
            selectforeground="#004040",
            selectbackground="#c0f0c0",
        )

        self._exampleList.pack(side="right", fill="both", expand=1)

        for example in self._examples:
            self._exampleList.insert("end", ("  %s" % example))
        self._exampleList.config(height=min(len(self._examples), 25), width=40)

        # Add a scrollbar if there are more than 25 examples.
        if len(self._examples) > 25:
            listscroll = Scrollbar(self._exampleFrame, orient="vertical")
            self._exampleList.config(yscrollcommand=listscroll.set)
            listscroll.config(command=self._exampleList.yview)
            listscroll.pack(side="left", fill="y")

        # If they select a example, apply it.
        self._exampleList.bind("<<ListboxSelect>>", self._exampleList_select)

    def _init_readingListbox(self, parent):
        self._readingFrame = listframe = Frame(parent)
        self._readingFrame.pack(fill="both", side="left", padx=2)
        self._readingList_label = Label(
            self._readingFrame, font=self._boldfont, text="Readings"
        )
        self._readingList_label.pack()
        self._readingList = Listbox(
            self._readingFrame,
            selectmode="single",
            relief="groove",
            background="white",
            foreground="#909090",
            font=self._font,
            selectforeground="#004040",
            selectbackground="#c0f0c0",
        )

        self._readingList.pack(side="right", fill="both", expand=1)

        # Add a scrollbar if there are more than 25 examples.
        listscroll = Scrollbar(self._readingFrame, orient="vertical")
        self._readingList.config(yscrollcommand=listscroll.set)
        listscroll.config(command=self._readingList.yview)
        listscroll.pack(side="right", fill="y")

        self._populate_readingListbox()

    def _populate_readingListbox(self):
        # Populate the listbox with integers
        self._readingList.delete(0, "end")
        for i in range(len(self._readings)):
            self._readingList.insert("end", ("  %s" % (i + 1)))
        self._readingList.config(height=min(len(self._readings), 25), width=5)

        # If they select a example, apply it.
        self._readingList.bind("<<ListboxSelect>>", self._readingList_select)

    def _init_bindings(self):
        # Key bindings are a good thing.
        self._top.bind("<Control-q>", self.destroy)
        self._top.bind("<Control-x>", self.destroy)
        self._top.bind("<Escape>", self.destroy)
        self._top.bind("n", self.next)
        self._top.bind("<space>", self.next)
        self._top.bind("p", self.prev)
        self._top.bind("<BackSpace>", self.prev)

    def _init_buttons(self, parent):
        # Set up the frames.
        self._buttonframe = buttonframe = Frame(parent)
        buttonframe.pack(fill="none", side="bottom", padx=3, pady=2)
        Button(
            buttonframe,
            text="Prev",
            background="#90c0d0",
            foreground="black",
            command=self.prev,
        ).pack(side="left")
        Button(
            buttonframe,
            text="Next",
            background="#90c0d0",
            foreground="black",
            command=self.next,
        ).pack(side="left")

    def _configure(self, event):
        self._autostep = 0
        (x1, y1, x2, y2) = self._cframe.scrollregion()
        y2 = event.height - 6
        self._canvas["scrollregion"] = "%d %d %d %d" % (x1, y1, x2, y2)
        self._redraw()

    def _init_canvas(self, parent):
        self._cframe = CanvasFrame(
            parent,
            background="white",
            # width=525, height=250,
            closeenough=10,
            border=2,
            relief="sunken",
        )
        self._cframe.pack(expand=1, fill="both", side="top", pady=2)
        canvas = self._canvas = self._cframe.canvas()

        # Initially, there's no tree or text
        self._tree = None
        self._textwidgets = []
        self._textline = None

    def _init_menubar(self, parent):
        menubar = Menu(parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="q"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        actionmenu = Menu(menubar, tearoff=0)
        actionmenu.add_command(
            label="Next", underline=0, command=self.next, accelerator="n, Space"
        )
        actionmenu.add_command(
            label="Previous", underline=0, command=self.prev, accelerator="p, Backspace"
        )
        menubar.add_cascade(label="Action", underline=0, menu=actionmenu)

        optionmenu = Menu(menubar, tearoff=0)
        optionmenu.add_checkbutton(
            label="Remove Duplicates",
            underline=0,
            variable=self._glue.remove_duplicates,
            command=self._toggle_remove_duplicates,
            accelerator="r",
        )
        menubar.add_cascade(label="Options", underline=0, menu=optionmenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=12,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=14,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=18,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        parent.config(menu=menubar)

    #########################################
    ##  Main draw procedure
    #########################################

    def _redraw(self):
        canvas = self._canvas

        # Delete the old DRS, widgets, etc.
        if self._drsWidget is not None:
            self._drsWidget.clear()

        if self._drs:
            self._drsWidget = DrsWidget(self._canvas, self._drs)
            self._drsWidget.draw()

        if self._error:
            self._drsWidget = DrsWidget(self._canvas, self._error)
            self._drsWidget.draw()

    #########################################
    ##  Button Callbacks
    #########################################

    def destroy(self, *e):
        self._autostep = 0
        if self._top is None:
            return
        self._top.destroy()
        self._top = None

    def prev(self, *e):
        selection = self._readingList.curselection()
        readingListSize = self._readingList.size()

        # there are readings
        if readingListSize > 0:
            # if one reading is currently selected
            if len(selection) == 1:
                index = int(selection[0])

                # if it's on (or before) the first item
                if index <= 0:
                    self._select_previous_example()
                else:
                    self._readingList_store_selection(index - 1)

            else:
                # select its first reading
                self._readingList_store_selection(readingListSize - 1)

        else:
            self._select_previous_example()

    def _select_previous_example(self):
        # if the current example is not the first example
        if self._curExample > 0:
            self._exampleList_store_selection(self._curExample - 1)
        else:
            # go to the last example
            self._exampleList_store_selection(len(self._examples) - 1)

    def next(self, *e):
        selection = self._readingList.curselection()
        readingListSize = self._readingList.size()

        # if there are readings
        if readingListSize > 0:
            # if one reading is currently selected
            if len(selection) == 1:
                index = int(selection[0])

                # if it's on (or past) the last item
                if index >= (readingListSize - 1):
                    self._select_next_example()
                else:
                    self._readingList_store_selection(index + 1)

            else:
                # select its first reading
                self._readingList_store_selection(0)

        else:
            self._select_next_example()

    def _select_next_example(self):
        # if the current example is not the last example
        if self._curExample < len(self._examples) - 1:
            self._exampleList_store_selection(self._curExample + 1)
        else:
            # go to the first example
            self._exampleList_store_selection(0)

    def about(self, *e):
        ABOUT = (
            "NLTK Discourse Representation Theory (DRT) Glue Semantics Demo\n"
            + "Written by Daniel H. Garrette"
        )
        TITLE = "About: NLTK DRT Glue Demo"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self._top, TITLE, ABOUT)

    def postscript(self, *e):
        self._autostep = 0
        self._cframe.print_to_file()

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._top.mainloop(*args, **kwargs)

    def resize(self, size=None):
        if size is not None:
            self._size.set(size)
        size = self._size.get()
        self._font.configure(size=-(abs(size)))
        self._boldfont.configure(size=-(abs(size)))
        self._sysfont.configure(size=-(abs(size)))
        self._bigfont.configure(size=-(abs(size + 2)))
        self._redraw()

    def _toggle_remove_duplicates(self):
        self._glue.remove_duplicates = not self._glue.remove_duplicates

        self._exampleList.selection_clear(0, "end")
        self._readings = []
        self._populate_readingListbox()
        self._readingCache = [None for ex in self._examples]
        self._curExample = -1
        self._error = None

        self._drs = None
        self._redraw()

    def _exampleList_select(self, event):
        selection = self._exampleList.curselection()
        if len(selection) != 1:
            return
        self._exampleList_store_selection(int(selection[0]))

    def _exampleList_store_selection(self, index):
        self._curExample = index
        example = self._examples[index]

        self._exampleList.selection_clear(0, "end")
        if example:
            cache = self._readingCache[index]
            if cache:
                if isinstance(cache, list):
                    self._readings = cache
                    self._error = None
                else:
                    self._readings = []
                    self._error = cache
            else:
                try:
                    self._readings = self._glue.parse_to_meaning(example)
                    self._error = None
                    self._readingCache[index] = self._readings
                except Exception as e:
                    self._readings = []
                    self._error = DrtVariableExpression(Variable("Error: " + str(e)))
                    self._readingCache[index] = self._error

                    # add a star to the end of the example
                    self._exampleList.delete(index)
                    self._exampleList.insert(index, ("  %s *" % example))
                    self._exampleList.config(
                        height=min(len(self._examples), 25), width=40
                    )

            self._populate_readingListbox()

            self._exampleList.selection_set(index)

            self._drs = None
            self._redraw()

    def _readingList_select(self, event):
        selection = self._readingList.curselection()
        if len(selection) != 1:
            return
        self._readingList_store_selection(int(selection[0]))

    def _readingList_store_selection(self, index):
        reading = self._readings[index]

        self._readingList.selection_clear(0, "end")
        if reading:
            self._readingList.selection_set(index)

            self._drs = reading.simplify().normalize().resolve_anaphora()

            self._redraw()


class DrsWidget:
    def __init__(self, canvas, drs, **attribs):
        self._drs = drs
        self._canvas = canvas
        canvas.font = Font(
            font=canvas.itemcget(canvas.create_text(0, 0, text=""), "font")
        )
        canvas._BUFFER = 3
        self.bbox = (0, 0, 0, 0)

    def draw(self):
        (right, bottom) = DrsDrawer(self._drs, canvas=self._canvas).draw()
        self.bbox = (0, 0, right + 1, bottom + 1)

    def clear(self):
        self._canvas.create_rectangle(self.bbox, fill="white", width="0")


def demo():
    examples = [
        "John walks",
        "David sees Mary",
        "David eats a sandwich",
        "every man chases a dog",
        #                'every man believes a dog yawns',
        #                'John gives David a sandwich',
        "John chases himself",
        #                'John persuades David to order a pizza',
        #                'John tries to go',
        #                'John tries to find a unicorn',
        #                'John seems to vanish',
        #                'a unicorn seems to approach',
        #                'every big cat leaves',
        #                'every gray cat leaves',
        #                'every big gray cat leaves',
        #                'a former senator leaves',
        #                'John likes a cat',
        #                'John likes every cat',
        #                'he walks',
        #                'John walks and he leaves'
    ]
    DrtGlueDemo(examples).mainloop()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\terminal\languages\jupyter_language.py ===
"""
This is NOT jupyter language, this is just python. 
Gotta split this out, generalize it, and move all the python additions to python.py, which imports this
"""

import ast
import logging
import os
import queue
import re
import sys
import threading
import time
import traceback

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm
from jupyter_client import KernelManager

from ..base_language import BaseLanguage

DEBUG_MODE = False

# When running from an executable, ipykernel calls itself infinitely
# This is a workaround to detect it and launch it manually
if "ipykernel_launcher" in sys.argv:
    if sys.path[0] == "":
        del sys.path[0]

    from ipykernel import kernelapp as app

    app.launch_new_instance()
    sys.exit(0)


class JupyterLanguage(BaseLanguage):
    file_extension = "py"
    name = "Python"
    aliases = ["py"]

    def __init__(self, computer):
        self.computer = computer

        self.km = KernelManager(kernel_name="python3")
        self.km.start_kernel()
        self.kc = self.km.client()
        self.kc.start_channels()
        while not self.kc.is_alive():
            time.sleep(0.1)
        time.sleep(0.5)

        self.listener_thread = None
        self.finish_flag = False

        # DISABLED because sometimes this bypasses sending it up to us for some reason!
        # Give it our same matplotlib backend
        # backend = matplotlib.get_backend()

        # Use Agg, which bubbles everything up as an image.
        # Not perfect (I want interactive!) but it works.
        backend = "Agg"

        code = f"""
import matplotlib
matplotlib.use('{backend}')
        """.strip()

        # Use Inline actually, it's better I think
        code = """
%matplotlib inline
import matplotlib.pyplot as plt
""".strip()

        for _ in self.run(code):
            pass

        # DISABLED because it doesn't work??
        # Disable color outputs in the terminal, which don't look good in OI and aren't useful
        # code = """
        # from IPython.core.getipython import get_ipython
        # get_ipython().colors = 'NoColor'
        # """
        # self.run(code)

    def terminate(self):
        self.kc.stop_channels()
        self.km.shutdown_kernel()

    def run(self, code):
        while not self.kc.is_alive():
            time.sleep(0.1)

        self.last_output_time = time.time()
        self.last_output_message_time = time.time()

        ################################################################
        ### OFFICIAL OPEN INTERPRETER GOVERNMENT ISSUE SKILL LIBRARY ###
        ################################################################

        # try:
        #     functions = string_to_python(code)
        # except:
        #     # Non blocking
        #     functions = {}

        # if self.computer.save_skills and functions:
        #     skill_library_path = self.computer.skills.path

        #     if not os.path.exists(skill_library_path):
        #         os.makedirs(skill_library_path)

        #     for filename, function_code in functions.items():
        #         with open(f"{skill_library_path}/{filename}.py", "w") as file:
        #             file.write(function_code)

        self.finish_flag = False
        try:
            try:
                preprocessed_code = self.preprocess_code(code)
            except:
                # Any errors produced here are our fault.
                # Also, for python, you don't need them! It's just for active_line and stuff. Just looks pretty.
                preprocessed_code = code
            message_queue = queue.Queue()
            self._execute_code(preprocessed_code, message_queue)
            yield from self._capture_output(message_queue)
        except GeneratorExit:
            raise  # gotta pass this up!
        except:
            content = traceback.format_exc()
            yield {"type": "console", "format": "output", "content": content}

    def _execute_code(self, code, message_queue):
        def iopub_message_listener():
            max_retries = 100
            while True:
                # If self.finish_flag = True, and we didn't set it (we do below), we need to stop. That's our "stop"
                if self.finish_flag == True:
                    if DEBUG_MODE:
                        print("interrupting kernel!!!!!")
                    self.km.interrupt_kernel()
                    return
                # For async usage
                if (
                    hasattr(self.computer.interpreter, "stop_event")
                    and self.computer.interpreter.stop_event.is_set()
                ):
                    self.km.interrupt_kernel()
                    self.finish_flag = True
                    return
                try:
                    input_patience = int(
                        os.environ.get("INTERPRETER_TERMINAL_INPUT_PATIENCE", 15)
                    )
                    if (
                        time.time() - self.last_output_time > input_patience
                        and time.time() - self.last_output_message_time > input_patience
                    ):
                        self.last_output_message_time = time.time()

                        text = f"{self.computer.interpreter.messages}\n\nThe program above has been running for over 15 seconds. It might require user input. Are there keystrokes that the user should type in, to proceed after the last command?"
                        if time.time() - self.last_output_time > 500:
                            text += f" If you think the process is frozen, or that the user wasn't expect it to run for this long (it has been {time.time() - self.last_output_time} seconds since last output) then say <input>CTRL-C</input>."

                        messages = [
                            {
                                "role": "system",
                                "type": "message",
                                "content": "You are an expert programming assistant. You will help the user determine if they should enter input into the terminal, per the user's requests. If you think the user would want you to type something into stdin, enclose it in <input></input> XML tags, like <input>y</input> to type 'y'.",
                            },
                            {"role": "user", "type": "message", "content": text},
                        ]
                        params = {
                            "messages": messages,
                            "model": self.computer.interpreter.llm.model,
                            "stream": True,
                            "temperature": 0,
                        }
                        if self.computer.interpreter.llm.api_key:
                            params["api_key"] = self.computer.interpreter.llm.api_key

                        response = ""
                        for chunk in litellm.completion(**params):
                            content = chunk.choices[0].delta.content
                            if type(content) == str:
                                response += content

                        # Parse the response for input tags
                        input_match = re.search(r"<input>(.*?)</input>", response)
                        if input_match:
                            user_input = input_match.group(1)
                            # Check if the user input is CTRL-C
                            self.finish_flag = True
                            if user_input.upper() == "CTRL-C":
                                self.finish_flag = True
                            else:
                                self.kc.input(user_input)

                    msg = self.kc.iopub_channel.get_msg(timeout=0.05)
                    self.last_output_time = time.time()
                except queue.Empty:
                    continue
                except Exception as e:
                    max_retries -= 1
                    if max_retries < 0:
                        raise
                    print("Jupyter error, retrying:", str(e))
                    continue

                if DEBUG_MODE:
                    print("-----------" * 10)
                    print("Message received:", msg["content"])
                    print("-----------" * 10)

                if (
                    msg["header"]["msg_type"] == "status"
                    and msg["content"]["execution_state"] == "idle"
                ):
                    # Set finish_flag and return when the kernel becomes idle
                    if DEBUG_MODE:
                        print("from thread: kernel is idle")
                    self.finish_flag = True
                    return

                content = msg["content"]

                if msg["msg_type"] == "stream":
                    line, active_line = self.detect_active_line(content["text"])
                    if active_line:
                        message_queue.put(
                            {
                                "type": "console",
                                "format": "active_line",
                                "content": active_line,
                            }
                        )
                    message_queue.put(
                        {"type": "console", "format": "output", "content": line}
                    )
                elif msg["msg_type"] == "error":
                    content = "\n".join(content["traceback"])
                    # Remove color codes
                    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
                    content = ansi_escape.sub("", content)
                    message_queue.put(
                        {
                            "type": "console",
                            "format": "output",
                            "content": content,
                        }
                    )
                elif msg["msg_type"] in ["display_data", "execute_result"]:
                    data = content["data"]
                    if "image/png" in data:
                        message_queue.put(
                            {
                                "type": "image",
                                "format": "base64.png",
                                "content": data["image/png"],
                            }
                        )
                    elif "image/jpeg" in data:
                        message_queue.put(
                            {
                                "type": "image",
                                "format": "base64.jpeg",
                                "content": data["image/jpeg"],
                            }
                        )
                    elif "text/html" in data:
                        message_queue.put(
                            {
                                "type": "code",
                                "format": "html",
                                "content": data["text/html"],
                            }
                        )
                    elif "text/plain" in data:
                        message_queue.put(
                            {
                                "type": "console",
                                "format": "output",
                                "content": data["text/plain"],
                            }
                        )
                    elif "application/javascript" in data:
                        message_queue.put(
                            {
                                "type": "code",
                                "format": "javascript",
                                "content": data["application/javascript"],
                            }
                        )

        self.listener_thread = threading.Thread(target=iopub_message_listener)
        # self.listener_thread.daemon = True
        self.listener_thread.start()

        if DEBUG_MODE:
            print(
                "thread is on:", self.listener_thread.is_alive(), self.listener_thread
            )

        self.kc.execute(code)

    def detect_active_line(self, line):
        if "##active_line" in line:
            # Split the line by "##active_line" and grab the last element
            last_active_line = line.split("##active_line")[-1]
            # Split the last active line by "##" and grab the first element
            try:
                active_line = int(last_active_line.split("##")[0])
            except:
                active_line = 0
            # Remove all ##active_line{number}##\n
            line = re.sub(r"##active_line\d+##\n", "", line)
            return line, active_line
        return line, None

    def _capture_output(self, message_queue):
        while True:
            time.sleep(0.1)

            # For async usage
            if (
                hasattr(self.computer.interpreter, "stop_event")
                and self.computer.interpreter.stop_event.is_set()
            ):
                self.finish_flag = True
                break

            if self.listener_thread:
                try:
                    output = message_queue.get(timeout=0.1)
                    if DEBUG_MODE:
                        print(output)
                    yield output

                except queue.Empty:
                    if self.finish_flag:
                        time.sleep(0.1)

                        try:
                            output = message_queue.get(timeout=0.1)
                            if DEBUG_MODE:
                                print(output)
                            yield output
                        except queue.Empty:
                            if DEBUG_MODE:
                                print("we're done")
                            break

    def stop(self):
        self.finish_flag = True

    def preprocess_code(self, code):
        return preprocess_python(code)


def preprocess_python(code):
    """
    Add active line markers
    Wrap in a try except
    """

    code = code.strip()

    # Add print commands that tell us what the active line is
    # but don't do this if any line starts with ! or %
    if (
        not any(line.strip().startswith(("!", "%")) for line in code.split("\n"))
        and os.environ.get("INTERPRETER_ACTIVE_LINE_DETECTION", "True").lower()
        == "true"
    ):
        code = add_active_line_prints(code)

    # Wrap in a try except (DISABLED)
    # code = wrap_in_try_except(code)

    # Remove any whitespace lines, as this will break indented blocks
    # (are we sure about this? test this)
    code_lines = code.split("\n")
    code_lines = [c for c in code_lines if c.strip() != ""]
    code = "\n".join(code_lines)

    return code


def add_active_line_prints(code):
    """
    Add print statements indicating line numbers to a python string.
    """
    # Replace newlines and comments with pass statements, so the line numbers are accurate (ast will remove them otherwise)
    code_lines = code.split("\n")
    in_multiline_string = False
    for i in range(len(code_lines)):
        line = code_lines[i]
        if '"""' in line or "'''" in line:
            in_multiline_string = not in_multiline_string
        if not in_multiline_string and (line.strip().startswith("#") or line == ""):
            whitespace = len(line) - len(line.lstrip(" "))
            code_lines[i] = " " * whitespace + "pass"
    processed_code = "\n".join(code_lines)
    try:
        tree = ast.parse(processed_code)
    except:
        # If you can't parse the processed version, try the unprocessed version before giving up
        tree = ast.parse(code)
    transformer = AddLinePrints()
    new_tree = transformer.visit(tree)
    return ast.unparse(new_tree)


class AddLinePrints(ast.NodeTransformer):
    """
    Transformer to insert print statements indicating the line number
    before every executable line in the AST.
    """

    def insert_print_statement(self, line_number):
        """Inserts a print statement for a given line number."""
        return ast.Expr(
            value=ast.Call(
                func=ast.Name(id="print", ctx=ast.Load()),
                args=[ast.Constant(value=f"##active_line{line_number}##")],
                keywords=[],
            )
        )

    def process_body(self, body):
        """Processes a block of statements, adding print calls."""
        new_body = []

        # In case it's not iterable:
        if not isinstance(body, list):
            body = [body]

        for sub_node in body:
            if hasattr(sub_node, "lineno"):
                new_body.append(self.insert_print_statement(sub_node.lineno))
            new_body.append(sub_node)

        return new_body

    def visit(self, node):
        """Overridden visit to transform nodes."""
        new_node = super().visit(node)

        # If node has a body, process it
        if hasattr(new_node, "body"):
            new_node.body = self.process_body(new_node.body)

        # If node has an orelse block (like in for, while, if), process it
        if hasattr(new_node, "orelse") and new_node.orelse:
            new_node.orelse = self.process_body(new_node.orelse)

        # Special case for Try nodes as they have multiple blocks
        if isinstance(new_node, ast.Try):
            for handler in new_node.handlers:
                handler.body = self.process_body(handler.body)
            if new_node.finalbody:
                new_node.finalbody = self.process_body(new_node.finalbody)

        return new_node


def wrap_in_try_except(code):
    # Add import traceback
    code = "import traceback\n" + code

    # Parse the input code into an AST
    parsed_code = ast.parse(code)

    # Wrap the entire code's AST in a single try-except block
    try_except = ast.Try(
        body=parsed_code.body,
        handlers=[
            ast.ExceptHandler(
                type=ast.Name(id="Exception", ctx=ast.Load()),
                name=None,
                body=[
                    ast.Expr(
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id="traceback", ctx=ast.Load()),
                                attr="print_exc",
                                ctx=ast.Load(),
                            ),
                            args=[],
                            keywords=[],
                        )
                    ),
                ],
            )
        ],
        orelse=[],
        finalbody=[],
    )

    # Assign the try-except block as the new body
    parsed_code.body = [try_except]

    # Convert the modified AST back to source code
    return ast.unparse(parsed_code)


def string_to_python(code_as_string):
    parsed_code = ast.parse(code_as_string)

    # Initialize containers for different categories
    import_statements = []
    functions = []
    functions_dict = {}

    # Traverse the AST
    for node in ast.walk(parsed_code):
        # Check for import statements
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            for alias in node.names:
                # Handling the alias in import statements
                if alias.asname:
                    import_statements.append(f"import {alias.name} as {alias.asname}")
                else:
                    import_statements.append(f"import {alias.name}")
        # Check for function definitions
        elif isinstance(node, ast.FunctionDef):
            if node.name.startswith("_"):
                # ignore private functions
                continue
            docstring = ast.get_docstring(node)
            body = node.body
            if docstring:
                body = body[1:]

            code_body = ast.unparse(body[0]).replace("\n", "\n    ")

            func_info = {
                "name": node.name,
                "docstring": docstring,
                "body": code_body,
            }
            functions.append(func_info)

    for func in functions:
        # Consolidating import statements and function definition
        function_content = "\n".join(import_statements) + "\n\n"
        function_content += f"def {func['name']}():\n    \"\"\"{func['docstring']}\"\"\"\n    {func['body']}\n"

        # Adding to dictionary
        functions_dict[func["name"]] = function_content

    return functions_dict

# === NexusCore/openenv\Lib\site-packages\nltk\parse\earleychart.py ===
# Natural Language Toolkit: An Incremental Earley Chart Parser
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
#         Rob Speer <rspeer@mit.edu>
#         Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
#         Jean Mark Gawron <gawron@mail.sdsu.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Data classes and parser implementations for *incremental* chart
parsers, which use dynamic programming to efficiently parse a text.
A "chart parser" derives parse trees for a text by iteratively adding
\"edges\" to a \"chart\".  Each "edge" represents a hypothesis about the tree
structure for a subsequence of the text.  The "chart" is a
\"blackboard\" for composing and combining these hypotheses.

A parser is "incremental", if it guarantees that for all i, j where i < j,
all edges ending at i are built before any edges ending at j.
This is appealing for, say, speech recognizer hypothesis filtering.

The main parser class is ``EarleyChartParser``, which is a top-down
algorithm, originally formulated by Jay Earley (1970).
"""

from time import perf_counter

from nltk.parse.chart import (
    BottomUpPredictCombineRule,
    BottomUpPredictRule,
    CachedTopDownPredictRule,
    Chart,
    ChartParser,
    EdgeI,
    EmptyPredictRule,
    FilteredBottomUpPredictCombineRule,
    FilteredSingleEdgeFundamentalRule,
    LeafEdge,
    LeafInitRule,
    SingleEdgeFundamentalRule,
    TopDownInitRule,
)
from nltk.parse.featurechart import (
    FeatureBottomUpPredictCombineRule,
    FeatureBottomUpPredictRule,
    FeatureChart,
    FeatureChartParser,
    FeatureEmptyPredictRule,
    FeatureSingleEdgeFundamentalRule,
    FeatureTopDownInitRule,
    FeatureTopDownPredictRule,
)

# ////////////////////////////////////////////////////////////
# Incremental Chart
# ////////////////////////////////////////////////////////////


class IncrementalChart(Chart):
    def initialize(self):
        # A sequence of edge lists contained in this chart.
        self._edgelists = tuple([] for x in self._positions())

        # The set of child pointer lists associated with each edge.
        self._edge_to_cpls = {}

        # Indexes mapping attribute values to lists of edges
        # (used by select()).
        self._indexes = {}

    def edges(self):
        return list(self.iteredges())

    def iteredges(self):
        return (edge for edgelist in self._edgelists for edge in edgelist)

    def select(self, end, **restrictions):
        edgelist = self._edgelists[end]

        # If there are no restrictions, then return all edges.
        if restrictions == {}:
            return iter(edgelist)

        # Find the index corresponding to the given restrictions.
        restr_keys = sorted(restrictions.keys())
        restr_keys = tuple(restr_keys)

        # If it doesn't exist, then create it.
        if restr_keys not in self._indexes:
            self._add_index(restr_keys)

        vals = tuple(restrictions[key] for key in restr_keys)
        return iter(self._indexes[restr_keys][end].get(vals, []))

    def _add_index(self, restr_keys):
        # Make sure it's a valid index.
        for key in restr_keys:
            if not hasattr(EdgeI, key):
                raise ValueError("Bad restriction: %s" % key)

        # Create the index.
        index = self._indexes[restr_keys] = tuple({} for x in self._positions())

        # Add all existing edges to the index.
        for end, edgelist in enumerate(self._edgelists):
            this_index = index[end]
            for edge in edgelist:
                vals = tuple(getattr(edge, key)() for key in restr_keys)
                this_index.setdefault(vals, []).append(edge)

    def _register_with_indexes(self, edge):
        end = edge.end()
        for restr_keys, index in self._indexes.items():
            vals = tuple(getattr(edge, key)() for key in restr_keys)
            index[end].setdefault(vals, []).append(edge)

    def _append_edge(self, edge):
        self._edgelists[edge.end()].append(edge)

    def _positions(self):
        return range(self.num_leaves() + 1)


class FeatureIncrementalChart(IncrementalChart, FeatureChart):
    def select(self, end, **restrictions):
        edgelist = self._edgelists[end]

        # If there are no restrictions, then return all edges.
        if restrictions == {}:
            return iter(edgelist)

        # Find the index corresponding to the given restrictions.
        restr_keys = sorted(restrictions.keys())
        restr_keys = tuple(restr_keys)

        # If it doesn't exist, then create it.
        if restr_keys not in self._indexes:
            self._add_index(restr_keys)

        vals = tuple(
            self._get_type_if_possible(restrictions[key]) for key in restr_keys
        )
        return iter(self._indexes[restr_keys][end].get(vals, []))

    def _add_index(self, restr_keys):
        # Make sure it's a valid index.
        for key in restr_keys:
            if not hasattr(EdgeI, key):
                raise ValueError("Bad restriction: %s" % key)

        # Create the index.
        index = self._indexes[restr_keys] = tuple({} for x in self._positions())

        # Add all existing edges to the index.
        for end, edgelist in enumerate(self._edgelists):
            this_index = index[end]
            for edge in edgelist:
                vals = tuple(
                    self._get_type_if_possible(getattr(edge, key)())
                    for key in restr_keys
                )
                this_index.setdefault(vals, []).append(edge)

    def _register_with_indexes(self, edge):
        end = edge.end()
        for restr_keys, index in self._indexes.items():
            vals = tuple(
                self._get_type_if_possible(getattr(edge, key)()) for key in restr_keys
            )
            index[end].setdefault(vals, []).append(edge)


# ////////////////////////////////////////////////////////////
# Incremental CFG Rules
# ////////////////////////////////////////////////////////////


class CompleteFundamentalRule(SingleEdgeFundamentalRule):
    def _apply_incomplete(self, chart, grammar, left_edge):
        end = left_edge.end()
        # When the chart is incremental, we only have to look for
        # empty complete edges here.
        for right_edge in chart.select(
            start=end, end=end, is_complete=True, lhs=left_edge.nextsym()
        ):
            new_edge = left_edge.move_dot_forward(right_edge.end())
            if chart.insert_with_backpointer(new_edge, left_edge, right_edge):
                yield new_edge


class CompleterRule(CompleteFundamentalRule):
    _fundamental_rule = CompleteFundamentalRule()

    def apply(self, chart, grammar, edge):
        if not isinstance(edge, LeafEdge):
            yield from self._fundamental_rule.apply(chart, grammar, edge)


class ScannerRule(CompleteFundamentalRule):
    _fundamental_rule = CompleteFundamentalRule()

    def apply(self, chart, grammar, edge):
        if isinstance(edge, LeafEdge):
            yield from self._fundamental_rule.apply(chart, grammar, edge)


class PredictorRule(CachedTopDownPredictRule):
    pass


class FilteredCompleteFundamentalRule(FilteredSingleEdgeFundamentalRule):
    def apply(self, chart, grammar, edge):
        # Since the Filtered rule only works for grammars without empty productions,
        # we only have to bother with complete edges here.
        if edge.is_complete():
            yield from self._apply_complete(chart, grammar, edge)


# ////////////////////////////////////////////////////////////
# Incremental FCFG Rules
# ////////////////////////////////////////////////////////////


class FeatureCompleteFundamentalRule(FeatureSingleEdgeFundamentalRule):
    def _apply_incomplete(self, chart, grammar, left_edge):
        fr = self._fundamental_rule
        end = left_edge.end()
        # When the chart is incremental, we only have to look for
        # empty complete edges here.
        for right_edge in chart.select(
            start=end, end=end, is_complete=True, lhs=left_edge.nextsym()
        ):
            yield from fr.apply(chart, grammar, left_edge, right_edge)


class FeatureCompleterRule(CompleterRule):
    _fundamental_rule = FeatureCompleteFundamentalRule()


class FeatureScannerRule(ScannerRule):
    _fundamental_rule = FeatureCompleteFundamentalRule()


class FeaturePredictorRule(FeatureTopDownPredictRule):
    pass


# ////////////////////////////////////////////////////////////
# Incremental CFG Chart Parsers
# ////////////////////////////////////////////////////////////

EARLEY_STRATEGY = [
    LeafInitRule(),
    TopDownInitRule(),
    CompleterRule(),
    ScannerRule(),
    PredictorRule(),
]
TD_INCREMENTAL_STRATEGY = [
    LeafInitRule(),
    TopDownInitRule(),
    CachedTopDownPredictRule(),
    CompleteFundamentalRule(),
]
BU_INCREMENTAL_STRATEGY = [
    LeafInitRule(),
    EmptyPredictRule(),
    BottomUpPredictRule(),
    CompleteFundamentalRule(),
]
BU_LC_INCREMENTAL_STRATEGY = [
    LeafInitRule(),
    EmptyPredictRule(),
    BottomUpPredictCombineRule(),
    CompleteFundamentalRule(),
]

LC_INCREMENTAL_STRATEGY = [
    LeafInitRule(),
    FilteredBottomUpPredictCombineRule(),
    FilteredCompleteFundamentalRule(),
]


class IncrementalChartParser(ChartParser):
    """
    An *incremental* chart parser implementing Jay Earley's
    parsing algorithm:

    | For each index end in [0, 1, ..., N]:
    |   For each edge such that edge.end = end:
    |     If edge is incomplete and edge.next is not a part of speech:
    |       Apply PredictorRule to edge
    |     If edge is incomplete and edge.next is a part of speech:
    |       Apply ScannerRule to edge
    |     If edge is complete:
    |       Apply CompleterRule to edge
    | Return any complete parses in the chart
    """

    def __init__(
        self,
        grammar,
        strategy=BU_LC_INCREMENTAL_STRATEGY,
        trace=0,
        trace_chart_width=50,
        chart_class=IncrementalChart,
    ):
        """
        Create a new Earley chart parser, that uses ``grammar`` to
        parse texts.

        :type grammar: CFG
        :param grammar: The grammar used to parse texts.
        :type trace: int
        :param trace: The level of tracing that should be used when
            parsing a text.  ``0`` will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        :type trace_chart_width: int
        :param trace_chart_width: The default total width reserved for
            the chart in trace output.  The remainder of each line will
            be used to display edges.
        :param chart_class: The class that should be used to create
            the charts used by this parser.
        """
        self._grammar = grammar
        self._trace = trace
        self._trace_chart_width = trace_chart_width
        self._chart_class = chart_class

        self._axioms = []
        self._inference_rules = []
        for rule in strategy:
            if rule.NUM_EDGES == 0:
                self._axioms.append(rule)
            elif rule.NUM_EDGES == 1:
                self._inference_rules.append(rule)
            else:
                raise ValueError(
                    "Incremental inference rules must have " "NUM_EDGES == 0 or 1"
                )

    def chart_parse(self, tokens, trace=None):
        if trace is None:
            trace = self._trace
        trace_new_edges = self._trace_new_edges

        tokens = list(tokens)
        self._grammar.check_coverage(tokens)
        chart = self._chart_class(tokens)
        grammar = self._grammar

        # Width, for printing trace edges.
        trace_edge_width = self._trace_chart_width // (chart.num_leaves() + 1)
        if trace:
            print(chart.pretty_format_leaves(trace_edge_width))

        for axiom in self._axioms:
            new_edges = list(axiom.apply(chart, grammar))
            trace_new_edges(chart, axiom, new_edges, trace, trace_edge_width)

        inference_rules = self._inference_rules
        for end in range(chart.num_leaves() + 1):
            if trace > 1:
                print("\n* Processing queue:", end, "\n")
            agenda = list(chart.select(end=end))
            while agenda:
                edge = agenda.pop()
                for rule in inference_rules:
                    new_edges = list(rule.apply(chart, grammar, edge))
                    trace_new_edges(chart, rule, new_edges, trace, trace_edge_width)
                    for new_edge in new_edges:
                        if new_edge.end() == end:
                            agenda.append(new_edge)

        return chart


class EarleyChartParser(IncrementalChartParser):
    def __init__(self, grammar, **parser_args):
        IncrementalChartParser.__init__(self, grammar, EARLEY_STRATEGY, **parser_args)


class IncrementalTopDownChartParser(IncrementalChartParser):
    def __init__(self, grammar, **parser_args):
        IncrementalChartParser.__init__(
            self, grammar, TD_INCREMENTAL_STRATEGY, **parser_args
        )


class IncrementalBottomUpChartParser(IncrementalChartParser):
    def __init__(self, grammar, **parser_args):
        IncrementalChartParser.__init__(
            self, grammar, BU_INCREMENTAL_STRATEGY, **parser_args
        )


class IncrementalBottomUpLeftCornerChartParser(IncrementalChartParser):
    def __init__(self, grammar, **parser_args):
        IncrementalChartParser.__init__(
            self, grammar, BU_LC_INCREMENTAL_STRATEGY, **parser_args
        )


class IncrementalLeftCornerChartParser(IncrementalChartParser):
    def __init__(self, grammar, **parser_args):
        if not grammar.is_nonempty():
            raise ValueError(
                "IncrementalLeftCornerParser only works for grammars "
                "without empty productions."
            )
        IncrementalChartParser.__init__(
            self, grammar, LC_INCREMENTAL_STRATEGY, **parser_args
        )


# ////////////////////////////////////////////////////////////
# Incremental FCFG Chart Parsers
# ////////////////////////////////////////////////////////////

EARLEY_FEATURE_STRATEGY = [
    LeafInitRule(),
    FeatureTopDownInitRule(),
    FeatureCompleterRule(),
    FeatureScannerRule(),
    FeaturePredictorRule(),
]
TD_INCREMENTAL_FEATURE_STRATEGY = [
    LeafInitRule(),
    FeatureTopDownInitRule(),
    FeatureTopDownPredictRule(),
    FeatureCompleteFundamentalRule(),
]
BU_INCREMENTAL_FEATURE_STRATEGY = [
    LeafInitRule(),
    FeatureEmptyPredictRule(),
    FeatureBottomUpPredictRule(),
    FeatureCompleteFundamentalRule(),
]
BU_LC_INCREMENTAL_FEATURE_STRATEGY = [
    LeafInitRule(),
    FeatureEmptyPredictRule(),
    FeatureBottomUpPredictCombineRule(),
    FeatureCompleteFundamentalRule(),
]


class FeatureIncrementalChartParser(IncrementalChartParser, FeatureChartParser):
    def __init__(
        self,
        grammar,
        strategy=BU_LC_INCREMENTAL_FEATURE_STRATEGY,
        trace_chart_width=20,
        chart_class=FeatureIncrementalChart,
        **parser_args
    ):
        IncrementalChartParser.__init__(
            self,
            grammar,
            strategy=strategy,
            trace_chart_width=trace_chart_width,
            chart_class=chart_class,
            **parser_args
        )


class FeatureEarleyChartParser(FeatureIncrementalChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureIncrementalChartParser.__init__(
            self, grammar, EARLEY_FEATURE_STRATEGY, **parser_args
        )


class FeatureIncrementalTopDownChartParser(FeatureIncrementalChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureIncrementalChartParser.__init__(
            self, grammar, TD_INCREMENTAL_FEATURE_STRATEGY, **parser_args
        )


class FeatureIncrementalBottomUpChartParser(FeatureIncrementalChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureIncrementalChartParser.__init__(
            self, grammar, BU_INCREMENTAL_FEATURE_STRATEGY, **parser_args
        )


class FeatureIncrementalBottomUpLeftCornerChartParser(FeatureIncrementalChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureIncrementalChartParser.__init__(
            self, grammar, BU_LC_INCREMENTAL_FEATURE_STRATEGY, **parser_args
        )


# ////////////////////////////////////////////////////////////
# Demonstration
# ////////////////////////////////////////////////////////////


def demo(
    print_times=True,
    print_grammar=False,
    print_trees=True,
    trace=2,
    sent="I saw John with a dog with my cookie",
    numparses=5,
):
    """
    A demonstration of the Earley parsers.
    """
    import sys
    import time

    from nltk.parse.chart import demo_grammar

    # The grammar for ChartParser and SteppingChartParser:
    grammar = demo_grammar()
    if print_grammar:
        print("* Grammar")
        print(grammar)

    # Tokenize the sample sentence.
    print("* Sentence:")
    print(sent)
    tokens = sent.split()
    print(tokens)
    print()

    # Do the parsing.
    earley = EarleyChartParser(grammar, trace=trace)
    t = perf_counter()
    chart = earley.chart_parse(tokens)
    parses = list(chart.parses(grammar.start()))
    t = perf_counter() - t

    # Print results.
    if numparses:
        assert len(parses) == numparses, "Not all parses found"
    if print_trees:
        for tree in parses:
            print(tree)
    else:
        print("Nr trees:", len(parses))
    if print_times:
        print("Time:", t)


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\intpyapp.py ===
# intpyapp.py  - Interactive Python application class
#
import os
import sys
import traceback

import __main__
import commctrl
import win32api
import win32con
import win32ui
from pywin.mfc import afxres, dialog, docview

from . import app, dbgcommands

lastLocateFileName = ".py"  # used in the "File/Locate" dialog...


# todo - _SetupSharedMenu should be moved to a framework class.
def _SetupSharedMenu_(self):
    sharedMenu = self.GetSharedMenu()
    from pywin.framework import toolmenu

    toolmenu.SetToolsMenu(sharedMenu)
    from pywin.framework import help

    help.SetHelpMenuOtherHelp(sharedMenu)


docview.DocTemplate._SetupSharedMenu_ = _SetupSharedMenu_  # type: ignore[method-assign]


class MainFrame(app.MainFrame):
    def OnCreate(self, createStruct):
        self.closing = 0
        if app.MainFrame.OnCreate(self, createStruct) == -1:
            return -1
        style = (
            win32con.WS_CHILD
            | afxres.CBRS_SIZE_DYNAMIC
            | afxres.CBRS_TOP
            | afxres.CBRS_TOOLTIPS
            | afxres.CBRS_FLYBY
        )

        self.EnableDocking(afxres.CBRS_ALIGN_ANY)

        tb = win32ui.CreateToolBar(self, style | win32con.WS_VISIBLE)
        tb.ModifyStyle(0, commctrl.TBSTYLE_FLAT)
        tb.LoadToolBar(win32ui.IDR_MAINFRAME)
        tb.EnableDocking(afxres.CBRS_ALIGN_ANY)
        tb.SetWindowText("Standard")
        self.DockControlBar(tb)
        # Any other packages which use toolbars
        from pywin.debugger.debugger import PrepareControlBars

        PrepareControlBars(self)
        # Note "interact" also uses dockable windows, but they already happen

        # And a "Tools" menu on the main frame.
        menu = self.GetMenu()
        from . import toolmenu

        toolmenu.SetToolsMenu(menu, 2)
        # And fix the "Help" menu on the main frame
        from pywin.framework import help

        help.SetHelpMenuOtherHelp(menu)

    def OnClose(self):
        try:
            import pywin.debugger

            if (
                pywin.debugger.currentDebugger is not None
                and pywin.debugger.currentDebugger.pumping
            ):
                try:
                    pywin.debugger.currentDebugger.close(1)
                except:
                    traceback.print_exc()
                return
        except win32ui.error:
            pass
        self.closing = 1
        self.SaveBarState("ToolbarDefault")
        self.SetActiveView(None)  # Otherwise MFC's OnClose may _not_ prompt for save.

        from pywin.framework import help

        help.FinalizeHelp()

        self.DestroyControlBar(afxres.AFX_IDW_TOOLBAR)
        self.DestroyControlBar(win32ui.ID_VIEW_TOOLBAR_DBG)

        return self._obj_.OnClose()

    def DestroyControlBar(self, id):
        try:
            bar = self.GetControlBar(id)
        except win32ui.error:
            return
        bar.DestroyWindow()

    def OnCommand(self, wparam, lparam):
        # By default, the current MDI child frame will process WM_COMMAND
        # messages before any docked control bars - even if the control bar
        # has focus.  This is a problem for the interactive window when docked.
        # Therefore, we detect the situation of a view having the main frame
        # as its parent, and assume it must be a docked view (which it will in an MDI app)
        try:
            v = (
                self.GetActiveView()
            )  # Raise an exception if none - good - then we want default handling
            # Main frame _does_ have a current view (ie, a docking view) - see if it wants it.
            if v.OnCommand(wparam, lparam):
                return 1
        except (win32ui.error, AttributeError):
            pass
        return self._obj_.OnCommand(wparam, lparam)


class InteractivePythonApp(app.CApp):
    # This works if necessary - just we don't need to override the Run method.
    # 	def Run(self):
    # 		return self._obj_.Run()

    def HookCommands(self):
        app.CApp.HookCommands(self)
        dbgcommands.DebuggerCommandHandler().HookCommands()
        self.HookCommand(self.OnViewBrowse, win32ui.ID_VIEW_BROWSE)
        self.HookCommand(self.OnFileImport, win32ui.ID_FILE_IMPORT)
        self.HookCommand(self.OnFileCheck, win32ui.ID_FILE_CHECK)
        self.HookCommandUpdate(self.OnUpdateFileCheck, win32ui.ID_FILE_CHECK)
        self.HookCommand(self.OnFileRun, win32ui.ID_FILE_RUN)
        self.HookCommand(self.OnFileLocate, win32ui.ID_FILE_LOCATE)
        self.HookCommand(self.OnInteractiveWindow, win32ui.ID_VIEW_INTERACTIVE)
        self.HookCommandUpdate(
            self.OnUpdateInteractiveWindow, win32ui.ID_VIEW_INTERACTIVE
        )
        self.HookCommand(self.OnViewOptions, win32ui.ID_VIEW_OPTIONS)
        self.HookCommand(self.OnHelpIndex, afxres.ID_HELP_INDEX)
        self.HookCommand(self.OnFileSaveAll, win32ui.ID_FILE_SAVE_ALL)
        self.HookCommand(self.OnViewToolbarDbg, win32ui.ID_VIEW_TOOLBAR_DBG)
        self.HookCommandUpdate(self.OnUpdateViewToolbarDbg, win32ui.ID_VIEW_TOOLBAR_DBG)

    def CreateMainFrame(self):
        return MainFrame()

    def MakeExistingDDEConnection(self):
        # Use DDE to connect to an existing instance
        # Return None if no existing instance
        try:
            from . import intpydde
        except ImportError:
            # No dde support!
            return None
        conv = intpydde.CreateConversation(self.ddeServer)
        try:
            conv.ConnectTo("Pythonwin", "System")
            return conv
        except intpydde.error:
            return None

    def InitDDE(self):
        # Do all the magic DDE handling.
        # Returns TRUE if we have pumped the arguments to our
        # remote DDE app, and we should terminate.
        try:
            from . import intpydde
        except ImportError:
            self.ddeServer = None
            intpydde = None
        if intpydde is not None:
            self.ddeServer = intpydde.DDEServer(self)
            self.ddeServer.Create("Pythonwin", intpydde.CBF_FAIL_SELFCONNECTIONS)
            try:
                # If there is an existing instance, pump the arguments to it.
                connection = self.MakeExistingDDEConnection()
                if connection is not None:
                    connection.Exec("self.Activate()")
                    if self.ProcessArgs(sys.argv, connection) is None:
                        return 1
            except:
                # It is too early to 'print' an exception - we
                # don't have stdout setup yet!
                win32ui.DisplayTraceback(
                    sys.exc_info(), " - error in DDE conversation with Pythonwin"
                )
                return 1

    def InitInstance(self):
        # Allow "/nodde" and "/new" to optimize this!
        if (
            "/nodde" not in sys.argv
            and "/new" not in sys.argv
            and "-nodde" not in sys.argv
            and "-new" not in sys.argv
        ):
            if self.InitDDE():
                return 1  # A remote DDE client is doing it for us!
        else:
            self.ddeServer = None

        win32ui.SetRegistryKey(
            f"Python {sys.winver}"
        )  # MFC automatically puts the main frame caption on!
        app.CApp.InitInstance(self)

        # Create the taskbar icon
        win32ui.CreateDebuggerThread()

        # Allow Pythonwin to host OCX controls.
        win32ui.EnableControlContainer()

        # Display the interactive window if the user wants it.
        from . import interact

        interact.CreateInteractiveWindowUserPreference()

        # Load the modules we use internally.
        self.LoadSystemModules()

        # Load additional module the user may want.
        self.LoadUserModules()

        # Load the ToolBar state near the end of the init process, as
        # there may be Toolbar IDs created by the user or other modules.
        # By now all these modules should be loaded, so all the toolbar IDs loaded.
        try:
            self.frame.LoadBarState("ToolbarDefault")
        except win32ui.error:
            # MFC sucks.  It does essentially "GetDlgItem(x)->Something", so if the
            # toolbar with ID x does not exist, MFC crashes!  Pythonwin has a trap for this
            # but I need to investigate more how to prevent it (AFAIK, ensuring all the
            # toolbars are created by now _should_ stop it!)
            pass

        # Finally process the command line arguments.
        try:
            self.ProcessArgs(sys.argv)
        except:
            # too early for printing anything.
            win32ui.DisplayTraceback(
                sys.exc_info(), " - error processing command line args"
            )

    def ExitInstance(self):
        win32ui.DestroyDebuggerThread()
        try:
            from . import interact

            interact.DestroyInteractiveWindow()
        except:
            pass
        if self.ddeServer is not None:
            self.ddeServer.Shutdown()
            self.ddeServer = None
        return app.CApp.ExitInstance(self)

    def Activate(self):
        # Bring to the foreground.  Mainly used when another app starts up, it asks
        # this one to activate itself, then it terminates.
        frame = win32ui.GetMainFrame()
        frame.SetForegroundWindow()
        if frame.GetWindowPlacement()[1] == win32con.SW_SHOWMINIMIZED:
            frame.ShowWindow(win32con.SW_RESTORE)

    def ProcessArgs(self, args, dde=None):
        # If we are going to talk to a remote app via DDE, then
        # activate it!
        if (
            len(args) < 1 or not args[0]
        ):  # argv[0]=='' when started without args, just like Python.exe!
            return

        i = 0
        while i < len(args):
            argType = args[i]
            i += 1
            if argType.startswith("-"):
                # Support dash options. Slash options are misinterpreted by python init
                # as path and not finding usually 'C:\\' ends up in sys.path[0]
                argType = "/" + argType[1:]
            if not argType.startswith("/"):
                argType = win32ui.GetProfileVal(
                    "Python", "Default Arg Type", "/edit"
                ).lower()
                i -= 1  #  arg is /edit's parameter
            par = i < len(args) and args[i] or "MISSING"
            if argType in ("/nodde", "/new", "-nodde", "-new"):
                # Already handled
                pass
            elif argType.startswith("/goto:"):
                gotoline = int(argType[len("/goto:") :])
                if dde:
                    dde.Exec(
                        "from pywin.framework import scriptutils\n"
                        "ed = scriptutils.GetActiveEditControl()\n"
                        "if ed: ed.SetSel(ed.LineIndex(%s - 1))" % gotoline
                    )
                else:
                    from . import scriptutils

                    ed = scriptutils.GetActiveEditControl()
                    if ed:
                        ed.SetSel(ed.LineIndex(gotoline - 1))
            elif argType == "/edit":
                # Load up the default application.
                i += 1
                fname = win32api.GetFullPathName(par)
                if not os.path.isfile(fname):
                    # if we don't catch this, OpenDocumentFile() (actually
                    # PyCDocument.SetPathName() in
                    # pywin.scintilla.document.CScintillaDocument.OnOpenDocument)
                    # segfaults Pythonwin on recent PY3 builds (b228)
                    win32ui.MessageBox(
                        "No such file: {}\n\nCommand Line: {}".format(
                            fname, win32api.GetCommandLine()
                        ),
                        "Open file for edit",
                        win32con.MB_ICONERROR,
                    )
                    continue
                if dde:
                    dde.Exec(f"win32ui.GetApp().OpenDocumentFile({fname!r})")
                else:
                    win32ui.GetApp().OpenDocumentFile(par)
            elif argType == "/rundlg":
                if dde:
                    dde.Exec(
                        "from pywin.framework import scriptutils;scriptutils.RunScript({!r}, {!r}, 1)".format(
                            par, " ".join(args[i + 1 :])
                        )
                    )
                else:
                    from . import scriptutils

                    scriptutils.RunScript(par, " ".join(args[i + 1 :]))
                return
            elif argType == "/run":
                if dde:
                    dde.Exec(
                        "from pywin.framework import scriptutils;scriptutils.RunScript({!r}, {!r}, 0)".format(
                            par, " ".join(args[i + 1 :])
                        )
                    )
                else:
                    from . import scriptutils

                    scriptutils.RunScript(par, " ".join(args[i + 1 :]), 0)
                return
            elif argType == "/app":
                raise RuntimeError(
                    "/app only supported for new instances of Pythonwin.exe"
                )
            elif argType == "/dde":  # Send arbitary command
                if dde is not None:
                    dde.Exec(par)
                else:
                    win32ui.MessageBox(
                        "The /dde command can only be used\r\nwhen Pythonwin is already running"
                    )
                i += 1
            else:
                raise ValueError("Command line argument not recognised: %s" % argType)

    def LoadSystemModules(self):
        self.DoLoadModules("pywin.framework.editor,pywin.framework.stdin")

    def LoadUserModules(self, moduleNames=None):
        # Load the users modules.
        if moduleNames is None:
            default = "pywin.framework.sgrepmdi"
            moduleNames = win32ui.GetProfileVal("Python", "Startup Modules", default)
        self.DoLoadModules(moduleNames)

    def DoLoadModules(self, moduleNames):  # ", sep string of module names.
        if not moduleNames:
            return
        modules = moduleNames.split(",")
        for module in modules:
            try:
                __import__(module)
            except:  # Catch em all, else the app itself dies! 'ImportError:
                traceback.print_exc()
                msg = 'Startup import of user module "%s" failed' % module
                print(msg)
                win32ui.MessageBox(msg)

    #
    # DDE Callback
    #
    def OnDDECommand(self, command):
        try:
            exec(command + "\n")
        except:
            print("ERROR executing DDE command: ", command)
            traceback.print_exc()
            raise

    #
    # General handlers
    #
    def OnViewBrowse(self, id, code):
        "Called when ViewBrowse message is received"
        from pywin.tools import browser

        obName = dialog.GetSimpleInput("Object", "__builtins__", "Browse Python Object")
        if obName is None:
            return
        try:
            browser.Browse(eval(obName, __main__.__dict__, __main__.__dict__))
        except NameError:
            win32ui.MessageBox("This is no object with this name")
        except AttributeError:
            win32ui.MessageBox("The object has no attribute of that name")
        except:
            traceback.print_exc()
            win32ui.MessageBox("This object can not be browsed")

    def OnFileImport(self, id, code):
        "Called when a FileImport message is received. Import the current or specified file"
        from . import scriptutils

        scriptutils.ImportFile()

    def OnFileCheck(self, id, code):
        "Called when a FileCheck message is received. Check the current file."
        from . import scriptutils

        scriptutils.CheckFile()

    def OnUpdateFileCheck(self, cmdui):
        from . import scriptutils

        cmdui.Enable(scriptutils.GetActiveFileName(0) is not None)

    def OnFileRun(self, id, code):
        "Called when a FileRun message is received."
        from . import scriptutils

        showDlg = win32api.GetKeyState(win32con.VK_SHIFT) >= 0
        scriptutils.RunScript(None, None, showDlg)

    def OnFileLocate(self, id, code):
        from . import scriptutils

        global lastLocateFileName  # save the new version away for next time...

        name = dialog.GetSimpleInput(
            "File name", lastLocateFileName, "Locate Python File"
        )
        if name is None:  # Cancelled.
            return
        lastLocateFileName = name
        # if ".py" supplied, rip it off!
        # should also check for .pys and .pyw
        if lastLocateFileName[-3:].lower() == ".py":
            lastLocateFileName = lastLocateFileName[:-3]
        lastLocateFileName = lastLocateFileName.replace(".", "\\")
        newName = scriptutils.LocatePythonFile(lastLocateFileName)
        if newName is None:
            win32ui.MessageBox("The file '%s' can not be located" % lastLocateFileName)
        else:
            win32ui.GetApp().OpenDocumentFile(newName)

    # Display all the "options" property pages we can find
    def OnViewOptions(self, id, code):
        win32ui.InitRichEdit()
        sheet = dialog.PropertySheet("Pythonwin Options")
        # Add property pages we know about that need manual work.
        from pywin.dialogs import ideoptions

        sheet.AddPage(ideoptions.OptionsPropPage())

        from . import toolmenu

        sheet.AddPage(toolmenu.ToolMenuPropPage())

        # Get other dynamic pages from templates.
        pages = []
        for template in self.GetDocTemplateList():
            try:
                # Don't actually call the function with the exception handler.
                getter = template.GetPythonPropertyPages
            except AttributeError:
                # Template does not provide property pages!
                continue
            pages.extend(getter())

        # Debugger template goes at the end
        try:
            from pywin.debugger import configui
        except ImportError:
            configui = None
        if configui is not None:
            pages.append(configui.DebuggerOptionsPropPage())
        # Now simply add the pages, and display the dialog.
        for page in pages:
            sheet.AddPage(page)

        if sheet.DoModal() == win32con.IDOK:
            win32ui.SetStatusText("Applying configuration changes...", 1)
            win32ui.DoWaitCursor(1)
            # Tell every Window in our app that win.ini has changed!
            win32ui.GetMainFrame().SendMessageToDescendants(
                win32con.WM_WININICHANGE, 0, 0
            )
            win32ui.DoWaitCursor(0)

    def OnInteractiveWindow(self, id, code):
        # toggle the existing state.
        from . import interact

        interact.ToggleInteractiveWindow()

    def OnUpdateInteractiveWindow(self, cmdui):
        try:
            interact = sys.modules["pywin.framework.interact"]
            state = interact.IsInteractiveWindowVisible()
        except KeyError:  # Interactive module hasn't ever been imported.
            state = 0
        cmdui.Enable()
        cmdui.SetCheck(state)

    def OnFileSaveAll(self, id, code):
        # Only attempt to save editor documents.
        from pywin.framework.editor import editorTemplate

        num = 0
        for doc in editorTemplate.GetDocumentList():
            if doc.IsModified() and doc.GetPathName():
                num = num = 1
                doc.OnSaveDocument(doc.GetPathName())
        win32ui.SetStatusText("%d documents saved" % num, 1)

    def OnViewToolbarDbg(self, id, code):
        if code == 0:
            return not win32ui.GetMainFrame().OnBarCheck(id)

    def OnUpdateViewToolbarDbg(self, cmdui):
        win32ui.GetMainFrame().OnUpdateControlBarMenu(cmdui)
        cmdui.Enable(1)

    def OnHelpIndex(self, id, code):
        from . import help

        help.SelectAndRunHelpFile()


thisApp = InteractivePythonApp()

# === NexusCore/openenv\Lib\site-packages\click\decorators.py ===
from __future__ import annotations

import inspect
import typing as t
from functools import update_wrapper
from gettext import gettext as _

from .core import Argument
from .core import Command
from .core import Context
from .core import Group
from .core import Option
from .core import Parameter
from .globals import get_current_context
from .utils import echo

if t.TYPE_CHECKING:
    import typing_extensions as te

    P = te.ParamSpec("P")

R = t.TypeVar("R")
T = t.TypeVar("T")
_AnyCallable = t.Callable[..., t.Any]
FC = t.TypeVar("FC", bound="_AnyCallable | Command")


def pass_context(f: t.Callable[te.Concatenate[Context, P], R]) -> t.Callable[P, R]:
    """Marks a callback as wanting to receive the current context
    object as first argument.
    """

    def new_func(*args: P.args, **kwargs: P.kwargs) -> R:
        return f(get_current_context(), *args, **kwargs)

    return update_wrapper(new_func, f)


def pass_obj(f: t.Callable[te.Concatenate[T, P], R]) -> t.Callable[P, R]:
    """Similar to :func:`pass_context`, but only pass the object on the
    context onwards (:attr:`Context.obj`).  This is useful if that object
    represents the state of a nested system.
    """

    def new_func(*args: P.args, **kwargs: P.kwargs) -> R:
        return f(get_current_context().obj, *args, **kwargs)

    return update_wrapper(new_func, f)


def make_pass_decorator(
    object_type: type[T], ensure: bool = False
) -> t.Callable[[t.Callable[te.Concatenate[T, P], R]], t.Callable[P, R]]:
    """Given an object type this creates a decorator that will work
    similar to :func:`pass_obj` but instead of passing the object of the
    current context, it will find the innermost context of type
    :func:`object_type`.

    This generates a decorator that works roughly like this::

        from functools import update_wrapper

        def decorator(f):
            @pass_context
            def new_func(ctx, *args, **kwargs):
                obj = ctx.find_object(object_type)
                return ctx.invoke(f, obj, *args, **kwargs)
            return update_wrapper(new_func, f)
        return decorator

    :param object_type: the type of the object to pass.
    :param ensure: if set to `True`, a new object will be created and
                   remembered on the context if it's not there yet.
    """

    def decorator(f: t.Callable[te.Concatenate[T, P], R]) -> t.Callable[P, R]:
        def new_func(*args: P.args, **kwargs: P.kwargs) -> R:
            ctx = get_current_context()

            obj: T | None
            if ensure:
                obj = ctx.ensure_object(object_type)
            else:
                obj = ctx.find_object(object_type)

            if obj is None:
                raise RuntimeError(
                    "Managed to invoke callback without a context"
                    f" object of type {object_type.__name__!r}"
                    " existing."
                )

            return ctx.invoke(f, obj, *args, **kwargs)

        return update_wrapper(new_func, f)

    return decorator


def pass_meta_key(
    key: str, *, doc_description: str | None = None
) -> t.Callable[[t.Callable[te.Concatenate[T, P], R]], t.Callable[P, R]]:
    """Create a decorator that passes a key from
    :attr:`click.Context.meta` as the first argument to the decorated
    function.

    :param key: Key in ``Context.meta`` to pass.
    :param doc_description: Description of the object being passed,
        inserted into the decorator's docstring. Defaults to "the 'key'
        key from Context.meta".

    .. versionadded:: 8.0
    """

    def decorator(f: t.Callable[te.Concatenate[T, P], R]) -> t.Callable[P, R]:
        def new_func(*args: P.args, **kwargs: P.kwargs) -> R:
            ctx = get_current_context()
            obj = ctx.meta[key]
            return ctx.invoke(f, obj, *args, **kwargs)

        return update_wrapper(new_func, f)

    if doc_description is None:
        doc_description = f"the {key!r} key from :attr:`click.Context.meta`"

    decorator.__doc__ = (
        f"Decorator that passes {doc_description} as the first argument"
        " to the decorated function."
    )
    return decorator


CmdType = t.TypeVar("CmdType", bound=Command)


# variant: no call, directly as decorator for a function.
@t.overload
def command(name: _AnyCallable) -> Command: ...


# variant: with positional name and with positional or keyword cls argument:
# @command(namearg, CommandCls, ...) or @command(namearg, cls=CommandCls, ...)
@t.overload
def command(
    name: str | None,
    cls: type[CmdType],
    **attrs: t.Any,
) -> t.Callable[[_AnyCallable], CmdType]: ...


# variant: name omitted, cls _must_ be a keyword argument, @command(cls=CommandCls, ...)
@t.overload
def command(
    name: None = None,
    *,
    cls: type[CmdType],
    **attrs: t.Any,
) -> t.Callable[[_AnyCallable], CmdType]: ...


# variant: with optional string name, no cls argument provided.
@t.overload
def command(
    name: str | None = ..., cls: None = None, **attrs: t.Any
) -> t.Callable[[_AnyCallable], Command]: ...


def command(
    name: str | _AnyCallable | None = None,
    cls: type[CmdType] | None = None,
    **attrs: t.Any,
) -> Command | t.Callable[[_AnyCallable], Command | CmdType]:
    r"""Creates a new :class:`Command` and uses the decorated function as
    callback.  This will also automatically attach all decorated
    :func:`option`\s and :func:`argument`\s as parameters to the command.

    The name of the command defaults to the name of the function, converted to
    lowercase, with underscores ``_`` replaced by dashes ``-``, and the suffixes
    ``_command``, ``_cmd``, ``_group``, and ``_grp`` are removed. For example,
    ``init_data_command`` becomes ``init-data``.

    All keyword arguments are forwarded to the underlying command class.
    For the ``params`` argument, any decorated params are appended to
    the end of the list.

    Once decorated the function turns into a :class:`Command` instance
    that can be invoked as a command line utility or be attached to a
    command :class:`Group`.

    :param name: The name of the command. Defaults to modifying the function's
        name as described above.
    :param cls: The command class to create. Defaults to :class:`Command`.

    .. versionchanged:: 8.2
        The suffixes ``_command``, ``_cmd``, ``_group``, and ``_grp`` are
        removed when generating the name.

    .. versionchanged:: 8.1
        This decorator can be applied without parentheses.

    .. versionchanged:: 8.1
        The ``params`` argument can be used. Decorated params are
        appended to the end of the list.
    """

    func: t.Callable[[_AnyCallable], t.Any] | None = None

    if callable(name):
        func = name
        name = None
        assert cls is None, "Use 'command(cls=cls)(callable)' to specify a class."
        assert not attrs, "Use 'command(**kwargs)(callable)' to provide arguments."

    if cls is None:
        cls = t.cast("type[CmdType]", Command)

    def decorator(f: _AnyCallable) -> CmdType:
        if isinstance(f, Command):
            raise TypeError("Attempted to convert a callback into a command twice.")

        attr_params = attrs.pop("params", None)
        params = attr_params if attr_params is not None else []

        try:
            decorator_params = f.__click_params__  # type: ignore
        except AttributeError:
            pass
        else:
            del f.__click_params__  # type: ignore
            params.extend(reversed(decorator_params))

        if attrs.get("help") is None:
            attrs["help"] = f.__doc__

        if t.TYPE_CHECKING:
            assert cls is not None
            assert not callable(name)

        if name is not None:
            cmd_name = name
        else:
            cmd_name = f.__name__.lower().replace("_", "-")
            cmd_left, sep, suffix = cmd_name.rpartition("-")

            if sep and suffix in {"command", "cmd", "group", "grp"}:
                cmd_name = cmd_left

        cmd = cls(name=cmd_name, callback=f, params=params, **attrs)
        cmd.__doc__ = f.__doc__
        return cmd

    if func is not None:
        return decorator(func)

    return decorator


GrpType = t.TypeVar("GrpType", bound=Group)


# variant: no call, directly as decorator for a function.
@t.overload
def group(name: _AnyCallable) -> Group: ...


# variant: with positional name and with positional or keyword cls argument:
# @group(namearg, GroupCls, ...) or @group(namearg, cls=GroupCls, ...)
@t.overload
def group(
    name: str | None,
    cls: type[GrpType],
    **attrs: t.Any,
) -> t.Callable[[_AnyCallable], GrpType]: ...


# variant: name omitted, cls _must_ be a keyword argument, @group(cmd=GroupCls, ...)
@t.overload
def group(
    name: None = None,
    *,
    cls: type[GrpType],
    **attrs: t.Any,
) -> t.Callable[[_AnyCallable], GrpType]: ...


# variant: with optional string name, no cls argument provided.
@t.overload
def group(
    name: str | None = ..., cls: None = None, **attrs: t.Any
) -> t.Callable[[_AnyCallable], Group]: ...


def group(
    name: str | _AnyCallable | None = None,
    cls: type[GrpType] | None = None,
    **attrs: t.Any,
) -> Group | t.Callable[[_AnyCallable], Group | GrpType]:
    """Creates a new :class:`Group` with a function as callback.  This
    works otherwise the same as :func:`command` just that the `cls`
    parameter is set to :class:`Group`.

    .. versionchanged:: 8.1
        This decorator can be applied without parentheses.
    """
    if cls is None:
        cls = t.cast("type[GrpType]", Group)

    if callable(name):
        return command(cls=cls, **attrs)(name)

    return command(name, cls, **attrs)


def _param_memo(f: t.Callable[..., t.Any], param: Parameter) -> None:
    if isinstance(f, Command):
        f.params.append(param)
    else:
        if not hasattr(f, "__click_params__"):
            f.__click_params__ = []  # type: ignore

        f.__click_params__.append(param)  # type: ignore


def argument(
    *param_decls: str, cls: type[Argument] | None = None, **attrs: t.Any
) -> t.Callable[[FC], FC]:
    """Attaches an argument to the command.  All positional arguments are
    passed as parameter declarations to :class:`Argument`; all keyword
    arguments are forwarded unchanged (except ``cls``).
    This is equivalent to creating an :class:`Argument` instance manually
    and attaching it to the :attr:`Command.params` list.

    For the default argument class, refer to :class:`Argument` and
    :class:`Parameter` for descriptions of parameters.

    :param cls: the argument class to instantiate.  This defaults to
                :class:`Argument`.
    :param param_decls: Passed as positional arguments to the constructor of
        ``cls``.
    :param attrs: Passed as keyword arguments to the constructor of ``cls``.
    """
    if cls is None:
        cls = Argument

    def decorator(f: FC) -> FC:
        _param_memo(f, cls(param_decls, **attrs))
        return f

    return decorator


def option(
    *param_decls: str, cls: type[Option] | None = None, **attrs: t.Any
) -> t.Callable[[FC], FC]:
    """Attaches an option to the command.  All positional arguments are
    passed as parameter declarations to :class:`Option`; all keyword
    arguments are forwarded unchanged (except ``cls``).
    This is equivalent to creating an :class:`Option` instance manually
    and attaching it to the :attr:`Command.params` list.

    For the default option class, refer to :class:`Option` and
    :class:`Parameter` for descriptions of parameters.

    :param cls: the option class to instantiate.  This defaults to
                :class:`Option`.
    :param param_decls: Passed as positional arguments to the constructor of
        ``cls``.
    :param attrs: Passed as keyword arguments to the constructor of ``cls``.
    """
    if cls is None:
        cls = Option

    def decorator(f: FC) -> FC:
        _param_memo(f, cls(param_decls, **attrs))
        return f

    return decorator


def confirmation_option(*param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]:
    """Add a ``--yes`` option which shows a prompt before continuing if
    not passed. If the prompt is declined, the program will exit.

    :param param_decls: One or more option names. Defaults to the single
        value ``"--yes"``.
    :param kwargs: Extra arguments are passed to :func:`option`.
    """

    def callback(ctx: Context, param: Parameter, value: bool) -> None:
        if not value:
            ctx.abort()

    if not param_decls:
        param_decls = ("--yes",)

    kwargs.setdefault("is_flag", True)
    kwargs.setdefault("callback", callback)
    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("prompt", "Do you want to continue?")
    kwargs.setdefault("help", "Confirm the action without prompting.")
    return option(*param_decls, **kwargs)


def password_option(*param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]:
    """Add a ``--password`` option which prompts for a password, hiding
    input and asking to enter the value again for confirmation.

    :param param_decls: One or more option names. Defaults to the single
        value ``"--password"``.
    :param kwargs: Extra arguments are passed to :func:`option`.
    """
    if not param_decls:
        param_decls = ("--password",)

    kwargs.setdefault("prompt", True)
    kwargs.setdefault("confirmation_prompt", True)
    kwargs.setdefault("hide_input", True)
    return option(*param_decls, **kwargs)


def version_option(
    version: str | None = None,
    *param_decls: str,
    package_name: str | None = None,
    prog_name: str | None = None,
    message: str | None = None,
    **kwargs: t.Any,
) -> t.Callable[[FC], FC]:
    """Add a ``--version`` option which immediately prints the version
    number and exits the program.

    If ``version`` is not provided, Click will try to detect it using
    :func:`importlib.metadata.version` to get the version for the
    ``package_name``.

    If ``package_name`` is not provided, Click will try to detect it by
    inspecting the stack frames. This will be used to detect the
    version, so it must match the name of the installed package.

    :param version: The version number to show. If not provided, Click
        will try to detect it.
    :param param_decls: One or more option names. Defaults to the single
        value ``"--version"``.
    :param package_name: The package name to detect the version from. If
        not provided, Click will try to detect it.
    :param prog_name: The name of the CLI to show in the message. If not
        provided, it will be detected from the command.
    :param message: The message to show. The values ``%(prog)s``,
        ``%(package)s``, and ``%(version)s`` are available. Defaults to
        ``"%(prog)s, version %(version)s"``.
    :param kwargs: Extra arguments are passed to :func:`option`.
    :raise RuntimeError: ``version`` could not be detected.

    .. versionchanged:: 8.0
        Add the ``package_name`` parameter, and the ``%(package)s``
        value for messages.

    .. versionchanged:: 8.0
        Use :mod:`importlib.metadata` instead of ``pkg_resources``. The
        version is detected based on the package name, not the entry
        point name. The Python package name must match the installed
        package name, or be passed with ``package_name=``.
    """
    if message is None:
        message = _("%(prog)s, version %(version)s")

    if version is None and package_name is None:
        frame = inspect.currentframe()
        f_back = frame.f_back if frame is not None else None
        f_globals = f_back.f_globals if f_back is not None else None
        # break reference cycle
        # https://docs.python.org/3/library/inspect.html#the-interpreter-stack
        del frame

        if f_globals is not None:
            package_name = f_globals.get("__name__")

            if package_name == "__main__":
                package_name = f_globals.get("__package__")

            if package_name:
                package_name = package_name.partition(".")[0]

    def callback(ctx: Context, param: Parameter, value: bool) -> None:
        if not value or ctx.resilient_parsing:
            return

        nonlocal prog_name
        nonlocal version

        if prog_name is None:
            prog_name = ctx.find_root().info_name

        if version is None and package_name is not None:
            import importlib.metadata

            try:
                version = importlib.metadata.version(package_name)
            except importlib.metadata.PackageNotFoundError:
                raise RuntimeError(
                    f"{package_name!r} is not installed. Try passing"
                    " 'package_name' instead."
                ) from None

        if version is None:
            raise RuntimeError(
                f"Could not determine the version for {package_name!r} automatically."
            )

        echo(
            message % {"prog": prog_name, "package": package_name, "version": version},
            color=ctx.color,
        )
        ctx.exit()

    if not param_decls:
        param_decls = ("--version",)

    kwargs.setdefault("is_flag", True)
    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("is_eager", True)
    kwargs.setdefault("help", _("Show the version and exit."))
    kwargs["callback"] = callback
    return option(*param_decls, **kwargs)


def help_option(*param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]:
    """Pre-configured ``--help`` option which immediately prints the help page
    and exits the program.

    :param param_decls: One or more option names. Defaults to the single
        value ``"--help"``.
    :param kwargs: Extra arguments are passed to :func:`option`.
    """

    def show_help(ctx: Context, param: Parameter, value: bool) -> None:
        """Callback that print the help page on ``<stdout>`` and exits."""
        if value and not ctx.resilient_parsing:
            echo(ctx.get_help(), color=ctx.color)
            ctx.exit()

    if not param_decls:
        param_decls = ("--help",)

    kwargs.setdefault("is_flag", True)
    kwargs.setdefault("expose_value", False)
    kwargs.setdefault("is_eager", True)
    kwargs.setdefault("help", _("Show this message and exit."))
    kwargs.setdefault("callback", show_help)

    return option(*param_decls, **kwargs)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\robotframework.py ===
"""
    pygments.lexers.robotframework
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for Robot Framework.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

#  Copyright 2012 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import re

from pygments.lexer import Lexer
from pygments.token import Token

__all__ = ['RobotFrameworkLexer']


HEADING = Token.Generic.Heading
SETTING = Token.Keyword.Namespace
IMPORT = Token.Name.Namespace
TC_KW_NAME = Token.Generic.Subheading
KEYWORD = Token.Name.Function
ARGUMENT = Token.String
VARIABLE = Token.Name.Variable
COMMENT = Token.Comment
SEPARATOR = Token.Punctuation
SYNTAX = Token.Punctuation
GHERKIN = Token.Generic.Emph
ERROR = Token.Error


def normalize(string, remove=''):
    string = string.lower()
    for char in remove + ' ':
        if char in string:
            string = string.replace(char, '')
    return string


class RobotFrameworkLexer(Lexer):
    """
    For Robot Framework test data.

    Supports both space and pipe separated plain text formats.
    """
    name = 'RobotFramework'
    url = 'http://robotframework.org'
    aliases = ['robotframework']
    filenames = ['*.robot', '*.resource']
    mimetypes = ['text/x-robotframework']
    version_added = '1.6'

    def __init__(self, **options):
        options['tabsize'] = 2
        options['encoding'] = 'UTF-8'
        Lexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        row_tokenizer = RowTokenizer()
        var_tokenizer = VariableTokenizer()
        index = 0
        for row in text.splitlines():
            for value, token in row_tokenizer.tokenize(row):
                for value, token in var_tokenizer.tokenize(value, token):
                    if value:
                        yield index, token, str(value)
                        index += len(value)


class VariableTokenizer:

    def tokenize(self, string, token):
        var = VariableSplitter(string, identifiers='$@%&')
        if var.start < 0 or token in (COMMENT, ERROR):
            yield string, token
            return
        for value, token in self._tokenize(var, string, token):
            if value:
                yield value, token

    def _tokenize(self, var, string, orig_token):
        before = string[:var.start]
        yield before, orig_token
        yield var.identifier + '{', SYNTAX
        yield from self.tokenize(var.base, VARIABLE)
        yield '}', SYNTAX
        if var.index is not None:
            yield '[', SYNTAX
            yield from self.tokenize(var.index, VARIABLE)
            yield ']', SYNTAX
        yield from self.tokenize(string[var.end:], orig_token)


class RowTokenizer:

    def __init__(self):
        self._table = UnknownTable()
        self._splitter = RowSplitter()
        testcases = TestCaseTable()
        settings = SettingTable(testcases.set_default_template)
        variables = VariableTable()
        keywords = KeywordTable()
        self._tables = {'settings': settings, 'setting': settings,
                        'metadata': settings,
                        'variables': variables, 'variable': variables,
                        'testcases': testcases, 'testcase': testcases,
                        'tasks': testcases, 'task': testcases,
                        'keywords': keywords, 'keyword': keywords,
                        'userkeywords': keywords, 'userkeyword': keywords}

    def tokenize(self, row):
        commented = False
        heading = False
        for index, value in enumerate(self._splitter.split(row)):
            # First value, and every second after that, is a separator.
            index, separator = divmod(index-1, 2)
            if value.startswith('#'):
                commented = True
            elif index == 0 and value.startswith('*'):
                self._table = self._start_table(value)
                heading = True
            yield from self._tokenize(value, index, commented,
                                      separator, heading)
        self._table.end_row()

    def _start_table(self, header):
        name = normalize(header, remove='*')
        return self._tables.get(name, UnknownTable())

    def _tokenize(self, value, index, commented, separator, heading):
        if commented:
            yield value, COMMENT
        elif separator:
            yield value, SEPARATOR
        elif heading:
            yield value, HEADING
        else:
            yield from self._table.tokenize(value, index)


class RowSplitter:
    _space_splitter = re.compile('( {2,})')
    _pipe_splitter = re.compile(r'((?:^| +)\|(?: +|$))')

    def split(self, row):
        splitter = (row.startswith('| ') and self._split_from_pipes
                    or self._split_from_spaces)
        yield from splitter(row)
        yield '\n'

    def _split_from_spaces(self, row):
        yield ''  # Start with (pseudo)separator similarly as with pipes
        yield from self._space_splitter.split(row)

    def _split_from_pipes(self, row):
        _, separator, rest = self._pipe_splitter.split(row, 1)
        yield separator
        while self._pipe_splitter.search(rest):
            cell, separator, rest = self._pipe_splitter.split(rest, 1)
            yield cell
            yield separator
        yield rest


class Tokenizer:
    _tokens = None

    def __init__(self):
        self._index = 0

    def tokenize(self, value):
        values_and_tokens = self._tokenize(value, self._index)
        self._index += 1
        if isinstance(values_and_tokens, type(Token)):
            values_and_tokens = [(value, values_and_tokens)]
        return values_and_tokens

    def _tokenize(self, value, index):
        index = min(index, len(self._tokens) - 1)
        return self._tokens[index]

    def _is_assign(self, value):
        if value.endswith('='):
            value = value[:-1].strip()
        var = VariableSplitter(value, identifiers='$@&')
        return var.start == 0 and var.end == len(value)


class Comment(Tokenizer):
    _tokens = (COMMENT,)


class Setting(Tokenizer):
    _tokens = (SETTING, ARGUMENT)
    _keyword_settings = ('suitesetup', 'suiteprecondition', 'suiteteardown',
                         'suitepostcondition', 'testsetup', 'tasksetup', 'testprecondition',
                         'testteardown','taskteardown', 'testpostcondition', 'testtemplate', 'tasktemplate')
    _import_settings = ('library', 'resource', 'variables')
    _other_settings = ('documentation', 'metadata', 'forcetags', 'defaulttags',
                       'testtimeout','tasktimeout')
    _custom_tokenizer = None

    def __init__(self, template_setter=None):
        Tokenizer.__init__(self)
        self._template_setter = template_setter

    def _tokenize(self, value, index):
        if index == 1 and self._template_setter:
            self._template_setter(value)
        if index == 0:
            normalized = normalize(value)
            if normalized in self._keyword_settings:
                self._custom_tokenizer = KeywordCall(support_assign=False)
            elif normalized in self._import_settings:
                self._custom_tokenizer = ImportSetting()
            elif normalized not in self._other_settings:
                return ERROR
        elif self._custom_tokenizer:
            return self._custom_tokenizer.tokenize(value)
        return Tokenizer._tokenize(self, value, index)


class ImportSetting(Tokenizer):
    _tokens = (IMPORT, ARGUMENT)


class TestCaseSetting(Setting):
    _keyword_settings = ('setup', 'precondition', 'teardown', 'postcondition',
                         'template')
    _import_settings = ()
    _other_settings = ('documentation', 'tags', 'timeout')

    def _tokenize(self, value, index):
        if index == 0:
            type = Setting._tokenize(self, value[1:-1], index)
            return [('[', SYNTAX), (value[1:-1], type), (']', SYNTAX)]
        return Setting._tokenize(self, value, index)


class KeywordSetting(TestCaseSetting):
    _keyword_settings = ('teardown',)
    _other_settings = ('documentation', 'arguments', 'return', 'timeout', 'tags')


class Variable(Tokenizer):
    _tokens = (SYNTAX, ARGUMENT)

    def _tokenize(self, value, index):
        if index == 0 and not self._is_assign(value):
            return ERROR
        return Tokenizer._tokenize(self, value, index)


class KeywordCall(Tokenizer):
    _tokens = (KEYWORD, ARGUMENT)

    def __init__(self, support_assign=True):
        Tokenizer.__init__(self)
        self._keyword_found = not support_assign
        self._assigns = 0

    def _tokenize(self, value, index):
        if not self._keyword_found and self._is_assign(value):
            self._assigns += 1
            return SYNTAX  # VariableTokenizer tokenizes this later.
        if self._keyword_found:
            return Tokenizer._tokenize(self, value, index - self._assigns)
        self._keyword_found = True
        return GherkinTokenizer().tokenize(value, KEYWORD)


class GherkinTokenizer:
    _gherkin_prefix = re.compile('^(Given|When|Then|And|But) ', re.IGNORECASE)

    def tokenize(self, value, token):
        match = self._gherkin_prefix.match(value)
        if not match:
            return [(value, token)]
        end = match.end()
        return [(value[:end], GHERKIN), (value[end:], token)]


class TemplatedKeywordCall(Tokenizer):
    _tokens = (ARGUMENT,)


class ForLoop(Tokenizer):

    def __init__(self):
        Tokenizer.__init__(self)
        self._in_arguments = False

    def _tokenize(self, value, index):
        token = self._in_arguments and ARGUMENT or SYNTAX
        if value.upper() in ('IN', 'IN RANGE'):
            self._in_arguments = True
        return token


class _Table:
    _tokenizer_class = None

    def __init__(self, prev_tokenizer=None):
        self._tokenizer = self._tokenizer_class()
        self._prev_tokenizer = prev_tokenizer
        self._prev_values_on_row = []

    def tokenize(self, value, index):
        if self._continues(value, index):
            self._tokenizer = self._prev_tokenizer
            yield value, SYNTAX
        else:
            yield from self._tokenize(value, index)
        self._prev_values_on_row.append(value)

    def _continues(self, value, index):
        return value == '...' and all(self._is_empty(t)
                                      for t in self._prev_values_on_row)

    def _is_empty(self, value):
        return value in ('', '\\')

    def _tokenize(self, value, index):
        return self._tokenizer.tokenize(value)

    def end_row(self):
        self.__init__(prev_tokenizer=self._tokenizer)


class UnknownTable(_Table):
    _tokenizer_class = Comment

    def _continues(self, value, index):
        return False


class VariableTable(_Table):
    _tokenizer_class = Variable


class SettingTable(_Table):
    _tokenizer_class = Setting

    def __init__(self, template_setter, prev_tokenizer=None):
        _Table.__init__(self, prev_tokenizer)
        self._template_setter = template_setter

    def _tokenize(self, value, index):
        if index == 0 and normalize(value) == 'testtemplate':
            self._tokenizer = Setting(self._template_setter)
        return _Table._tokenize(self, value, index)

    def end_row(self):
        self.__init__(self._template_setter, prev_tokenizer=self._tokenizer)


class TestCaseTable(_Table):
    _setting_class = TestCaseSetting
    _test_template = None
    _default_template = None

    @property
    def _tokenizer_class(self):
        if self._test_template or (self._default_template and
                                   self._test_template is not False):
            return TemplatedKeywordCall
        return KeywordCall

    def _continues(self, value, index):
        return index > 0 and _Table._continues(self, value, index)

    def _tokenize(self, value, index):
        if index == 0:
            if value:
                self._test_template = None
            return GherkinTokenizer().tokenize(value, TC_KW_NAME)
        if index == 1 and self._is_setting(value):
            if self._is_template(value):
                self._test_template = False
                self._tokenizer = self._setting_class(self.set_test_template)
            else:
                self._tokenizer = self._setting_class()
        if index == 1 and self._is_for_loop(value):
            self._tokenizer = ForLoop()
        if index == 1 and self._is_empty(value):
            return [(value, SYNTAX)]
        return _Table._tokenize(self, value, index)

    def _is_setting(self, value):
        return value.startswith('[') and value.endswith(']')

    def _is_template(self, value):
        return normalize(value) == '[template]'

    def _is_for_loop(self, value):
        return value.startswith(':') and normalize(value, remove=':') == 'for'

    def set_test_template(self, template):
        self._test_template = self._is_template_set(template)

    def set_default_template(self, template):
        self._default_template = self._is_template_set(template)

    def _is_template_set(self, template):
        return normalize(template) not in ('', '\\', 'none', '${empty}')


class KeywordTable(TestCaseTable):
    _tokenizer_class = KeywordCall
    _setting_class = KeywordSetting

    def _is_template(self, value):
        return False


# Following code copied directly from Robot Framework 2.7.5.

class VariableSplitter:

    def __init__(self, string, identifiers):
        self.identifier = None
        self.base = None
        self.index = None
        self.start = -1
        self.end = -1
        self._identifiers = identifiers
        self._may_have_internal_variables = False
        try:
            self._split(string)
        except ValueError:
            pass
        else:
            self._finalize()

    def get_replaced_base(self, variables):
        if self._may_have_internal_variables:
            return variables.replace_string(self.base)
        return self.base

    def _finalize(self):
        self.identifier = self._variable_chars[0]
        self.base = ''.join(self._variable_chars[2:-1])
        self.end = self.start + len(self._variable_chars)
        if self._has_list_or_dict_variable_index():
            self.index = ''.join(self._list_and_dict_variable_index_chars[1:-1])
            self.end += len(self._list_and_dict_variable_index_chars)

    def _has_list_or_dict_variable_index(self):
        return self._list_and_dict_variable_index_chars\
        and self._list_and_dict_variable_index_chars[-1] == ']'

    def _split(self, string):
        start_index, max_index = self._find_variable(string)
        self.start = start_index
        self._open_curly = 1
        self._state = self._variable_state
        self._variable_chars = [string[start_index], '{']
        self._list_and_dict_variable_index_chars = []
        self._string = string
        start_index += 2
        for index, char in enumerate(string[start_index:]):
            index += start_index  # Giving start to enumerate only in Py 2.6+
            try:
                self._state(char, index)
            except StopIteration:
                return
            if index  == max_index and not self._scanning_list_variable_index():
                return

    def _scanning_list_variable_index(self):
        return self._state in [self._waiting_list_variable_index_state,
                               self._list_variable_index_state]

    def _find_variable(self, string):
        max_end_index = string.rfind('}')
        if max_end_index == -1:
            raise ValueError('No variable end found')
        if self._is_escaped(string, max_end_index):
            return self._find_variable(string[:max_end_index])
        start_index = self._find_start_index(string, 1, max_end_index)
        if start_index == -1:
            raise ValueError('No variable start found')
        return start_index, max_end_index

    def _find_start_index(self, string, start, end):
        index = string.find('{', start, end) - 1
        if index < 0:
            return -1
        if self._start_index_is_ok(string, index):
            return index
        return self._find_start_index(string, index+2, end)

    def _start_index_is_ok(self, string, index):
        return string[index] in self._identifiers\
        and not self._is_escaped(string, index)

    def _is_escaped(self, string, index):
        escaped = False
        while index > 0 and string[index-1] == '\\':
            index -= 1
            escaped = not escaped
        return escaped

    def _variable_state(self, char, index):
        self._variable_chars.append(char)
        if char == '}' and not self._is_escaped(self._string, index):
            self._open_curly -= 1
            if self._open_curly == 0:
                if not self._is_list_or_dict_variable():
                    raise StopIteration
                self._state = self._waiting_list_variable_index_state
        elif char in self._identifiers:
            self._state = self._internal_variable_start_state

    def _is_list_or_dict_variable(self):
        return self._variable_chars[0] in ('@','&')

    def _internal_variable_start_state(self, char, index):
        self._state = self._variable_state
        if char == '{':
            self._variable_chars.append(char)
            self._open_curly += 1
            self._may_have_internal_variables = True
        else:
            self._variable_state(char, index)

    def _waiting_list_variable_index_state(self, char, index):
        if char != '[':
            raise StopIteration
        self._list_and_dict_variable_index_chars.append(char)
        self._state = self._list_variable_index_state

    def _list_variable_index_state(self, char, index):
        self._list_and_dict_variable_index_chars.append(char)
        if char == ']':
            raise StopIteration

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_trace_dispatch_regular.py ===
from _pydev_bundle.pydev_is_thread_alive import is_thread_alive
from _pydev_bundle.pydev_log import exception as pydev_log_exception
from _pydev_bundle._pydev_saved_modules import threading
from _pydevd_bundle.pydevd_constants import (
    get_current_thread_id,
    NO_FTRACE,
    USE_CUSTOM_SYS_CURRENT_FRAMES_MAP,
    ForkSafeLock,
    PYDEVD_USE_SYS_MONITORING,
)
from pydevd_file_utils import get_abs_path_real_path_and_base_from_frame, NORM_PATHS_AND_BASE_CONTAINER

# fmt: off
# IFDEF CYTHON
# from cpython.object cimport PyObject
# from cpython.ref cimport Py_INCREF, Py_XDECREF
# ELSE
from _pydevd_bundle.pydevd_frame import PyDBFrame, is_unhandled_exception
# ENDIF
# fmt: on

# fmt: off
# IFDEF CYTHON
# cdef dict _global_notify_skipped_step_in
# cython_inline_constant: CMD_STEP_INTO = 107
# cython_inline_constant: CMD_STEP_INTO_MY_CODE = 144
# cython_inline_constant: CMD_STEP_RETURN = 109
# cython_inline_constant: CMD_STEP_RETURN_MY_CODE = 160
# ELSE
# Note: those are now inlined on cython.
CMD_STEP_INTO = 107
CMD_STEP_INTO_MY_CODE = 144
CMD_STEP_RETURN = 109
CMD_STEP_RETURN_MY_CODE = 160
# ENDIF
# fmt: on

# Cache where we should keep that we completely skipped entering some context.
# It needs to be invalidated when:
# - Breakpoints are changed
# It can be used when running regularly (without step over/step in/step return)
global_cache_skips = {}
global_cache_frame_skips = {}

_global_notify_skipped_step_in = False
_global_notify_skipped_step_in_lock = ForkSafeLock()


def notify_skipped_step_in_because_of_filters(py_db, frame):
    global _global_notify_skipped_step_in

    with _global_notify_skipped_step_in_lock:
        if _global_notify_skipped_step_in:
            # Check with lock in place (callers should actually have checked
            # before without the lock in place due to performance).
            return
        _global_notify_skipped_step_in = True
        py_db.notify_skipped_step_in_because_of_filters(frame)


# fmt: off
# IFDEF CYTHON
# cdef class SafeCallWrapper:
#     cdef method_object
#     def __init__(self, method_object):
#         self.method_object = method_object
#     def  __call__(self, *args):
#         #Cannot use 'self' once inside the delegate call since we are borrowing the self reference f_trace field
#         #in the frame, and that reference might get destroyed by set trace on frame and parents
#         cdef PyObject* method_obj = <PyObject*> self.method_object
#         Py_INCREF(<object>method_obj)
#         ret = (<object>method_obj)(*args)
#         Py_XDECREF (method_obj)
#         return SafeCallWrapper(ret) if ret is not None else None
#     def  get_method_object(self):
#         return self.method_object
# ELSE
# ENDIF
# fmt: on


def fix_top_level_trace_and_get_trace_func(py_db, frame):
    # fmt: off
    # IFDEF CYTHON
    # cdef str filename;
    # cdef str name;
    # cdef tuple args;
    # ENDIF
    # fmt: on

    # Note: this is always the first entry-point in the tracing for any thread.
    # After entering here we'll set a new tracing function for this thread
    # where more information is cached (and will also setup the tracing for
    # frames where we should deal with unhandled exceptions).
    thread = None
    # Cache the frame which should be traced to deal with unhandled exceptions.
    # (i.e.: thread entry-points).

    f_unhandled = frame
    # print('called at', f_unhandled.f_code.co_name, f_unhandled.f_code.co_filename, f_unhandled.f_code.co_firstlineno)
    force_only_unhandled_tracer = False
    while f_unhandled is not None:
        # name = splitext(basename(f_unhandled.f_code.co_filename))[0]

        name = f_unhandled.f_code.co_filename
        # basename
        i = name.rfind("/")
        j = name.rfind("\\")
        if j > i:
            i = j
        if i >= 0:
            name = name[i + 1 :]
        # remove ext
        i = name.rfind(".")
        if i >= 0:
            name = name[:i]

        if name == "threading":
            if f_unhandled.f_code.co_name in ("__bootstrap", "_bootstrap"):
                # We need __bootstrap_inner, not __bootstrap.
                return None, False

            elif f_unhandled.f_code.co_name in ("__bootstrap_inner", "_bootstrap_inner"):
                # Note: be careful not to use threading.currentThread to avoid creating a dummy thread.
                t = f_unhandled.f_locals.get("self")
                force_only_unhandled_tracer = True
                if t is not None and isinstance(t, threading.Thread):
                    thread = t
                    break

        elif name == "pydev_monkey":
            if f_unhandled.f_code.co_name == "__call__":
                force_only_unhandled_tracer = True
                break

        elif name == "pydevd":
            if f_unhandled.f_code.co_name in ("run", "main"):
                # We need to get to _exec
                return None, False

            if f_unhandled.f_code.co_name == "_exec":
                force_only_unhandled_tracer = True
                break

        elif name == "pydevd_tracing":
            return None, False

        elif f_unhandled.f_back is None:
            break

        f_unhandled = f_unhandled.f_back

    if thread is None:
        # Important: don't call threadingCurrentThread if we're in the threading module
        # to avoid creating dummy threads.
        if py_db.threading_get_ident is not None:
            thread = py_db.threading_active.get(py_db.threading_get_ident())
            if thread is None:
                return None, False
        else:
            # Jython does not have threading.get_ident().
            thread = py_db.threading_current_thread()

    if getattr(thread, "pydev_do_not_trace", None):
        py_db.disable_tracing()
        return None, False

    try:
        additional_info = thread.additional_info
        if additional_info is None:
            raise AttributeError()
    except:
        additional_info = py_db.set_additional_thread_info(thread)

    # print('enter thread tracer', thread, get_current_thread_id(thread))
    args = (py_db, thread, additional_info, global_cache_skips, global_cache_frame_skips)

    if f_unhandled is not None:
        if f_unhandled.f_back is None and not force_only_unhandled_tracer:
            # Happens when we attach to a running program (cannot reuse instance because it's mutable).
            top_level_thread_tracer = TopLevelThreadTracerNoBackFrame(ThreadTracer(args), args)
            additional_info.top_level_thread_tracer_no_back_frames.append(
                top_level_thread_tracer
            )  # Hack for cython to keep it alive while the thread is alive (just the method in the SetTrace is not enough).
        else:
            top_level_thread_tracer = additional_info.top_level_thread_tracer_unhandled
            if top_level_thread_tracer is None:
                # Stop in some internal place to report about unhandled exceptions
                top_level_thread_tracer = TopLevelThreadTracerOnlyUnhandledExceptions(args)
                additional_info.top_level_thread_tracer_unhandled = top_level_thread_tracer  # Hack for cython to keep it alive while the thread is alive (just the method in the SetTrace is not enough).

        # print(' --> found to trace unhandled', f_unhandled.f_code.co_name, f_unhandled.f_code.co_filename, f_unhandled.f_code.co_firstlineno)
        f_trace = top_level_thread_tracer.get_trace_dispatch_func()
        # fmt: off
        # IFDEF CYTHON
        # f_trace = SafeCallWrapper(f_trace)
        # ENDIF
        # fmt: on
        f_unhandled.f_trace = f_trace

        if frame is f_unhandled:
            return f_trace, False

    thread_tracer = additional_info.thread_tracer
    if thread_tracer is None or thread_tracer._args[0] is not py_db:
        thread_tracer = ThreadTracer(args)
        additional_info.thread_tracer = thread_tracer

    # fmt: off
    # IFDEF CYTHON
    # return SafeCallWrapper(thread_tracer), True
    # ELSE
    return thread_tracer, True
    # ENDIF
    # fmt: on


def trace_dispatch(py_db, frame, event, arg):
    thread_trace_func, apply_to_settrace = py_db.fix_top_level_trace_and_get_trace_func(py_db, frame)
    if thread_trace_func is None:
        return None if event == "call" else NO_FTRACE
    if apply_to_settrace:
        py_db.enable_tracing(thread_trace_func)
    return thread_trace_func(frame, event, arg)


# fmt: off
# IFDEF CYTHON
# cdef class TopLevelThreadTracerOnlyUnhandledExceptions:
#     cdef public tuple _args;
#     def __init__(self, tuple args):
#         self._args = args
# ELSE
class TopLevelThreadTracerOnlyUnhandledExceptions(object):
    def __init__(self, args):
        self._args = args

# ENDIF
# fmt: on

    def trace_unhandled_exceptions(self, frame, event, arg):
        # Note that we ignore the frame as this tracing method should only be put in topmost frames already.
        # print('trace_unhandled_exceptions', event, frame.f_code.co_name, frame.f_code.co_filename, frame.f_code.co_firstlineno)
        if event == "exception" and arg is not None:
            py_db, t, additional_info = self._args[0:3]
            if arg is not None:
                if not additional_info.suspended_at_unhandled:
                    additional_info.suspended_at_unhandled = True

                    py_db.stop_on_unhandled_exception(py_db, t, additional_info, arg)

        # No need to reset frame.f_trace to keep the same trace function.
        return self.trace_unhandled_exceptions

    def get_trace_dispatch_func(self):
        return self.trace_unhandled_exceptions

# fmt: off
# IFDEF CYTHON
# cdef class TopLevelThreadTracerNoBackFrame:
#
#     cdef public object _frame_trace_dispatch;
#     cdef public tuple _args;
#     cdef public object try_except_infos;
#     cdef public object _last_exc_arg;
#     cdef public set _raise_lines;
#     cdef public int _last_raise_line;
#
#     def __init__(self, frame_trace_dispatch, tuple args):
#         self._frame_trace_dispatch = frame_trace_dispatch
#         self._args = args
#         self.try_except_infos = None
#         self._last_exc_arg = None
#         self._raise_lines = set()
#         self._last_raise_line = -1
# ELSE
class TopLevelThreadTracerNoBackFrame(object):
    """
    This tracer is pretty special in that it's dealing with a frame without f_back (i.e.: top frame
    on remote attach or QThread).

    This means that we have to carefully inspect exceptions to discover whether the exception will
    be unhandled or not (if we're dealing with an unhandled exception we need to stop as unhandled,
    otherwise we need to use the regular tracer -- unfortunately the debugger has little info to
    work with in the tracing -- see: https://bugs.python.org/issue34099, so, we inspect bytecode to
    determine if some exception will be traced or not... note that if this is not available -- such
    as on Jython -- we consider any top-level exception to be unnhandled).
    """

    def __init__(self, frame_trace_dispatch, args):
        self._frame_trace_dispatch = frame_trace_dispatch
        self._args = args
        self.try_except_infos = None
        self._last_exc_arg = None
        self._raise_lines = set()
        self._last_raise_line = -1

# ENDIF
# fmt: on

    def trace_dispatch_and_unhandled_exceptions(self, frame, event, arg):
        # DEBUG = 'code_to_debug' in frame.f_code.co_filename
        # if DEBUG: print('trace_dispatch_and_unhandled_exceptions: %s %s %s %s %s %s' % (event, frame.f_code.co_name, frame.f_code.co_filename, frame.f_code.co_firstlineno, self._frame_trace_dispatch, frame.f_lineno))
        frame_trace_dispatch = self._frame_trace_dispatch
        if frame_trace_dispatch is not None:
            self._frame_trace_dispatch = frame_trace_dispatch(frame, event, arg)

        if event == "exception":
            self._last_exc_arg = arg
            self._raise_lines.add(frame.f_lineno)
            self._last_raise_line = frame.f_lineno

        elif event == "return" and self._last_exc_arg is not None:
            # For unhandled exceptions we actually track the return when at the topmost level.
            try:
                py_db, t, additional_info = self._args[0:3]
                if not additional_info.suspended_at_unhandled:  # Note: only check it here, don't set.
                    if is_unhandled_exception(self, py_db, frame, self._last_raise_line, self._raise_lines):
                        py_db.stop_on_unhandled_exception(py_db, t, additional_info, self._last_exc_arg)
            finally:
                # Remove reference to exception after handling it.
                self._last_exc_arg = None

        ret = self.trace_dispatch_and_unhandled_exceptions

        # Need to reset (the call to _frame_trace_dispatch may have changed it).
        # fmt: off
        # IFDEF CYTHON
        # frame.f_trace = SafeCallWrapper(ret)
        # ELSE
        frame.f_trace = ret
        # ENDIF
        # fmt: on
        return ret

    def get_trace_dispatch_func(self):
        return self.trace_dispatch_and_unhandled_exceptions


# fmt: off
# IFDEF CYTHON
# cdef class ThreadTracer:
#     cdef public tuple _args;
#     def __init__(self, tuple args):
#         self._args = args
# ELSE
class ThreadTracer(object):
    def __init__(self, args):
        self._args = args

# ENDIF
# fmt: on

    def __call__(self, frame, event, arg):
        """This is the callback used when we enter some context in the debugger.

        We also decorate the thread we are in with info about the debugging.
        The attributes added are:
            pydev_state
            pydev_step_stop
            pydev_step_cmd
            pydev_notify_kill

        :param PyDB py_db:
            This is the global debugger (this method should actually be added as a method to it).
        """
        # fmt: off
        # IFDEF CYTHON
        # cdef str filename;
        # cdef str base;
        # cdef int pydev_step_cmd;
        # cdef object frame_cache_key;
        # cdef dict cache_skips;
        # cdef bint is_stepping;
        # cdef tuple abs_path_canonical_path_and_base;
        # cdef PyDBAdditionalThreadInfo additional_info;
        # ENDIF
        # fmt: on

        # DEBUG = 'code_to_debug' in frame.f_code.co_filename
        # if DEBUG: print('ENTER: trace_dispatch: %s %s %s %s' % (frame.f_code.co_filename, frame.f_lineno, event, frame.f_code.co_name))
        py_db, t, additional_info, cache_skips, frame_skips_cache = self._args
        if additional_info.is_tracing:
            return None if event == "call" else NO_FTRACE  # we don't wan't to trace code invoked from pydevd_frame.trace_dispatch

        additional_info.is_tracing += 1
        try:
            pydev_step_cmd = additional_info.pydev_step_cmd
            is_stepping = pydev_step_cmd != -1
            if py_db.pydb_disposed:
                return None if event == "call" else NO_FTRACE

            # if thread is not alive, cancel trace_dispatch processing
            if not is_thread_alive(t):
                py_db.notify_thread_not_alive(get_current_thread_id(t))
                return None if event == "call" else NO_FTRACE

            # Note: it's important that the context name is also given because we may hit something once
            # in the global context and another in the local context.
            frame_cache_key = frame.f_code
            if frame_cache_key in cache_skips:
                if not is_stepping:
                    # if DEBUG: print('skipped: trace_dispatch (cache hit)', frame_cache_key, frame.f_lineno, event, frame.f_code.co_name)
                    return None if event == "call" else NO_FTRACE
                else:
                    # When stepping we can't take into account caching based on the breakpoints (only global filtering).
                    if cache_skips.get(frame_cache_key) == 1:
                        if (
                            additional_info.pydev_original_step_cmd in (CMD_STEP_INTO, CMD_STEP_INTO_MY_CODE)
                            and not _global_notify_skipped_step_in
                        ):
                            notify_skipped_step_in_because_of_filters(py_db, frame)

                        back_frame = frame.f_back
                        if back_frame is not None and pydev_step_cmd in (
                            CMD_STEP_INTO,
                            CMD_STEP_INTO_MY_CODE,
                            CMD_STEP_RETURN,
                            CMD_STEP_RETURN_MY_CODE,
                        ):
                            back_frame_cache_key = back_frame.f_code
                            if cache_skips.get(back_frame_cache_key) == 1:
                                # if DEBUG: print('skipped: trace_dispatch (cache hit: 1)', frame_cache_key, frame.f_lineno, event, frame.f_code.co_name)
                                return None if event == "call" else NO_FTRACE
                        else:
                            # if DEBUG: print('skipped: trace_dispatch (cache hit: 2)', frame_cache_key, frame.f_lineno, event, frame.f_code.co_name)
                            return None if event == "call" else NO_FTRACE

            try:
                # Make fast path faster!
                abs_path_canonical_path_and_base = NORM_PATHS_AND_BASE_CONTAINER[frame.f_code.co_filename]
            except:
                abs_path_canonical_path_and_base = get_abs_path_real_path_and_base_from_frame(frame)

            file_type = py_db.get_file_type(
                frame, abs_path_canonical_path_and_base
            )  # we don't want to debug threading or anything related to pydevd

            if file_type is not None:
                if file_type == 1:  # inlining LIB_FILE = 1
                    if not py_db.in_project_scope(frame, abs_path_canonical_path_and_base[0]):
                        # if DEBUG: print('skipped: trace_dispatch (not in scope)', abs_path_canonical_path_and_base[2], frame.f_lineno, event, frame.f_code.co_name, file_type)
                        cache_skips[frame_cache_key] = 1
                        return None if event == "call" else NO_FTRACE
                else:
                    # if DEBUG: print('skipped: trace_dispatch', abs_path_canonical_path_and_base[2], frame.f_lineno, event, frame.f_code.co_name, file_type)
                    cache_skips[frame_cache_key] = 1
                    return None if event == "call" else NO_FTRACE

            if py_db.is_files_filter_enabled:
                if py_db.apply_files_filter(frame, abs_path_canonical_path_and_base[0], False):
                    cache_skips[frame_cache_key] = 1

                    if (
                        is_stepping
                        and additional_info.pydev_original_step_cmd in (CMD_STEP_INTO, CMD_STEP_INTO_MY_CODE)
                        and not _global_notify_skipped_step_in
                    ):
                        notify_skipped_step_in_because_of_filters(py_db, frame)

                    # A little gotcha, sometimes when we're stepping in we have to stop in a
                    # return event showing the back frame as the current frame, so, we need
                    # to check not only the current frame but the back frame too.
                    back_frame = frame.f_back
                    if back_frame is not None and pydev_step_cmd in (
                        CMD_STEP_INTO,
                        CMD_STEP_INTO_MY_CODE,
                        CMD_STEP_RETURN,
                        CMD_STEP_RETURN_MY_CODE,
                    ):
                        if py_db.apply_files_filter(back_frame, back_frame.f_code.co_filename, False):
                            back_frame_cache_key = back_frame.f_code
                            cache_skips[back_frame_cache_key] = 1
                            # if DEBUG: print('skipped: trace_dispatch (filtered out: 1)', frame_cache_key, frame.f_lineno, event, frame.f_code.co_name)
                            return None if event == "call" else NO_FTRACE
                    else:
                        # if DEBUG: print('skipped: trace_dispatch (filtered out: 2)', frame_cache_key, frame.f_lineno, event, frame.f_code.co_name)
                        return None if event == "call" else NO_FTRACE

            # if DEBUG: print('trace_dispatch', filename, frame.f_lineno, event, frame.f_code.co_name, file_type)

            # Just create PyDBFrame directly (removed support for Python versions < 2.5, which required keeping a weak
            # reference to the frame).
            ret = PyDBFrame(
                (
                    py_db,
                    abs_path_canonical_path_and_base,
                    additional_info,
                    t,
                    frame_skips_cache,
                    frame_cache_key,
                )
            ).trace_dispatch(frame, event, arg)
            if ret is None:
                # 1 means skipped because of filters.
                # 2 means skipped because no breakpoints were hit.
                cache_skips[frame_cache_key] = 2
                return None if event == "call" else NO_FTRACE

            # fmt: off
            # IFDEF CYTHON
            # frame.f_trace = SafeCallWrapper(ret)  # Make sure we keep the returned tracer.
            # ELSE
            frame.f_trace = ret  # Make sure we keep the returned tracer.
            # ENDIF
            # fmt: on
            return ret

        except SystemExit:
            return None if event == "call" else NO_FTRACE

        except Exception:
            if py_db.pydb_disposed:
                return None if event == "call" else NO_FTRACE  # Don't log errors when we're shutting down.
            # Log it
            try:
                if pydev_log_exception is not None:
                    # This can actually happen during the interpreter shutdown in Python 2.7
                    pydev_log_exception()
            except:
                # Error logging? We're really in the interpreter shutdown...
                # (https://github.com/fabioz/PyDev.Debugger/issues/8)
                pass
            return None if event == "call" else NO_FTRACE
        finally:
            additional_info.is_tracing -= 1


if USE_CUSTOM_SYS_CURRENT_FRAMES_MAP:
    # This is far from ideal, as we'll leak frames (we'll always have the last created frame, not really
    # the last topmost frame saved -- this should be Ok for our usage, but it may leak frames and things
    # may live longer... as IronPython is garbage-collected, things should live longer anyways, so, it
    # shouldn't be an issue as big as it's in CPython -- it may still be annoying, but this should
    # be a reasonable workaround until IronPython itself is able to provide that functionality).
    #
    # See: https://github.com/IronLanguages/main/issues/1630
    from _pydevd_bundle.pydevd_constants import constructed_tid_to_last_frame

    _original_call = ThreadTracer.__call__

    def __call__(self, frame, event, arg):
        constructed_tid_to_last_frame[self._args[1].ident] = frame
        return _original_call(self, frame, event, arg)

    ThreadTracer.__call__ = __call__

if PYDEVD_USE_SYS_MONITORING:

    def fix_top_level_trace_and_get_trace_func(*args, **kwargs):
        raise RuntimeError("Not used in sys.monitoring mode.")

# === NexusCore/openenv\Lib\site-packages\litellm\types\llms\bedrock.py ===
import json
from typing import Any, List, Literal, Optional, TypedDict, Union

from typing_extensions import (
    TYPE_CHECKING,
    Protocol,
    Required,
    Self,
    TypeGuard,
    get_origin,
    override,
    runtime_checkable,
)

from .openai import ChatCompletionToolCallChunk


class CachePointBlock(TypedDict, total=False):
    type: Literal["default"]


class SystemContentBlock(TypedDict, total=False):
    text: str
    cachePoint: CachePointBlock


class SourceBlock(TypedDict):
    bytes: Optional[str]  # base 64 encoded string


BedrockImageTypes = Literal["png", "jpeg", "gif", "webp"]


class ImageBlock(TypedDict):
    format: Union[BedrockImageTypes, str]
    source: SourceBlock


BedrockVideoTypes = Literal["mp4", "mov", "mkv", "webm", "flv", "mpeg", "mpg", "wmv", "3gp"]


class VideoBlock(TypedDict):
    format: Union[BedrockVideoTypes, str]
    source: SourceBlock


BedrockDocumentTypes = Literal[
    "pdf", "csv", "doc", "docx", "xls", "xlsx", "html", "txt", "md"
]


class DocumentBlock(TypedDict):
    format: Union[BedrockDocumentTypes, str]
    source: SourceBlock
    name: str


class ToolResultContentBlock(TypedDict, total=False):
    image: ImageBlock
    document: DocumentBlock
    json: dict
    text: str


class ToolResultBlock(TypedDict, total=False):
    content: Required[List[ToolResultContentBlock]]
    toolUseId: Required[str]
    status: Literal["success", "error"]


class ToolUseBlock(TypedDict):
    input: dict
    name: str
    toolUseId: str


class BedrockConverseReasoningTextBlock(TypedDict, total=False):
    text: Required[str]
    signature: str


class BedrockConverseReasoningContentBlock(TypedDict, total=False):
    reasoningText: BedrockConverseReasoningTextBlock
    redactedContent: str


class BedrockConverseReasoningContentBlockDelta(TypedDict, total=False):
    signature: str
    redactedContent: str
    text: str


class ContentBlock(TypedDict, total=False):
    text: str
    image: ImageBlock
    video: VideoBlock
    document: DocumentBlock
    toolResult: ToolResultBlock
    toolUse: ToolUseBlock
    cachePoint: CachePointBlock
    reasoningContent: BedrockConverseReasoningContentBlock


class MessageBlock(TypedDict):
    content: List[ContentBlock]
    role: Literal["user", "assistant"]


class ConverseMetricsBlock(TypedDict):
    latencyMs: float  # time in ms


class ConverseResponseOutputBlock(TypedDict):
    message: Optional[MessageBlock]


class ConverseTokenUsageBlock(TypedDict):
    inputTokens: int
    outputTokens: int
    totalTokens: int
    cacheReadInputTokenCount: int
    cacheReadInputTokens: int
    cacheWriteInputTokenCount: int
    cacheWriteInputTokens: int


class ConverseResponseBlock(TypedDict):
    additionalModelResponseFields: dict
    metrics: ConverseMetricsBlock
    output: ConverseResponseOutputBlock
    stopReason: (
        str  # end_turn | tool_use | max_tokens | stop_sequence | content_filtered
    )
    usage: ConverseTokenUsageBlock


class ToolJsonSchemaBlock(TypedDict, total=False):
    type: Literal["object"]
    properties: dict
    required: List[str]


class ToolInputSchemaBlock(TypedDict):
    json: Optional[ToolJsonSchemaBlock]


class ToolSpecBlock(TypedDict, total=False):
    inputSchema: Required[ToolInputSchemaBlock]
    name: Required[str]
    description: str


class ToolBlock(TypedDict, total=False):
    toolSpec: Optional[ToolSpecBlock]
    cachePoint: Optional[CachePointBlock]


class SpecificToolChoiceBlock(TypedDict):
    name: str


class ToolChoiceValuesBlock(TypedDict, total=False):
    any: dict
    auto: dict
    tool: SpecificToolChoiceBlock


class ToolConfigBlock(TypedDict, total=False):
    tools: Required[List[ToolBlock]]
    toolChoice: Union[str, ToolChoiceValuesBlock]


class GuardrailConfigBlock(TypedDict, total=False):
    guardrailIdentifier: str
    guardrailVersion: str
    trace: Literal["enabled", "disabled"]


class InferenceConfig(TypedDict, total=False):
    maxTokens: int
    stopSequences: List[str]
    temperature: float
    topP: float
    topK: int


class ToolBlockDeltaEvent(TypedDict):
    input: str


class ToolUseBlockStartEvent(TypedDict):
    name: str
    toolUseId: str


class ContentBlockStartEvent(TypedDict, total=False):
    toolUse: Optional[ToolUseBlockStartEvent]
    reasoningContent: BedrockConverseReasoningContentBlockDelta


class ContentBlockDeltaEvent(TypedDict, total=False):
    """
    Either 'text' or 'toolUse' will be specified for Converse API streaming response.
    """

    text: str
    toolUse: ToolBlockDeltaEvent
    reasoningContent: BedrockConverseReasoningContentBlockDelta


class PerformanceConfigBlock(TypedDict):
    latency: Literal["optimized", "throughput"]


class CommonRequestObject(
    TypedDict, total=False
):  # common request object across sync + async flows
    additionalModelRequestFields: dict
    additionalModelResponseFieldPaths: List[str]
    inferenceConfig: InferenceConfig
    system: List[SystemContentBlock]
    toolConfig: ToolConfigBlock
    guardrailConfig: Optional[GuardrailConfigBlock]
    performanceConfig: Optional[PerformanceConfigBlock]


class RequestObject(CommonRequestObject, total=False):
    messages: Required[List[MessageBlock]]


class BedrockInvokeNovaRequest(TypedDict, total=False):
    """
    Request object for sending `nova` requests to `/bedrock/invoke/`
    """

    messages: List[MessageBlock]
    inferenceConfig: InferenceConfig
    system: List[SystemContentBlock]
    toolConfig: ToolConfigBlock
    guardrailConfig: Optional[GuardrailConfigBlock]


class GenericStreamingChunk(TypedDict):
    text: Required[str]
    tool_use: Optional[ChatCompletionToolCallChunk]
    is_finished: Required[bool]
    finish_reason: Required[str]
    usage: Optional[ConverseTokenUsageBlock]
    index: int


class Document(TypedDict):
    title: str
    snippet: str


class ServerSentEvent:
    def __init__(
        self,
        *,
        event: Optional[str] = None,
        data: Optional[str] = None,
        id: Optional[str] = None,
        retry: Optional[int] = None,
    ) -> None:
        if data is None:
            data = ""

        self._id = id
        self._data = data
        self._event = event or None
        self._retry = retry

    @property
    def event(self) -> Optional[str]:
        return self._event

    @property
    def id(self) -> Optional[str]:
        return self._id

    @property
    def retry(self) -> Optional[int]:
        return self._retry

    @property
    def data(self) -> str:
        return self._data

    def json(self) -> Any:
        return json.loads(self.data)

    @override
    def __repr__(self) -> str:
        return f"ServerSentEvent(event={self.event}, data={self.data}, id={self.id}, retry={self.retry})"


COHERE_EMBEDDING_INPUT_TYPES = Literal[
    "search_document", "search_query", "classification", "clustering", "image"
]


class CohereEmbeddingRequest(TypedDict, total=False):
    texts: List[str]
    images: List[str]
    input_type: Required[COHERE_EMBEDDING_INPUT_TYPES]
    truncate: Literal["NONE", "START", "END"]
    embedding_types: Literal["float", "int8", "uint8", "binary", "ubinary"]


class CohereEmbeddingRequestWithModel(CohereEmbeddingRequest):
    model: Required[str]


class CohereEmbeddingResponse(TypedDict):
    embeddings: List[List[float]]
    id: str
    response_type: Literal["embedding_floats"]
    texts: List[str]


class AmazonTitanV2EmbeddingRequest(TypedDict):
    inputText: str
    dimensions: int
    normalize: bool


class AmazonTitanV2EmbeddingResponse(TypedDict):
    embedding: List[float]
    inputTextTokenCount: int


class AmazonTitanG1EmbeddingRequest(TypedDict):
    inputText: str


class AmazonTitanG1EmbeddingResponse(TypedDict):
    embedding: List[float]
    inputTextTokenCount: int


class AmazonTitanMultimodalEmbeddingConfig(TypedDict):
    outputEmbeddingLength: Literal[256, 384, 1024]


class AmazonTitanMultimodalEmbeddingRequest(TypedDict, total=False):
    inputText: str
    inputImage: str
    embeddingConfig: AmazonTitanMultimodalEmbeddingConfig


class AmazonTitanMultimodalEmbeddingResponse(TypedDict):
    embedding: List[float]
    inputTextTokenCount: int
    message: str  # Specifies any errors that occur during generation.


AmazonEmbeddingRequest = Union[
    AmazonTitanMultimodalEmbeddingRequest,
    AmazonTitanV2EmbeddingRequest,
    AmazonTitanG1EmbeddingRequest,
]


class AmazonStability3TextToImageRequest(TypedDict, total=False):
    """
    Request for Amazon Stability 3 Text to Image API

    Ref here: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-diffusion-3-text-image.html
    """

    prompt: str
    aspect_ratio: Literal[
        "16:9", "1:1", "21:9", "2:3", "3:2", "4:5", "5:4", "9:16", "9:21"
    ]
    mode: Literal["image-to-image", "text-to-image"]
    output_format: Literal["JPEG", "PNG"]
    seed: int
    negative_prompt: str


class AmazonStability3TextToImageResponse(TypedDict, total=False):
    """
    Response for Amazon Stability 3 Text to Image API

    Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-diffusion-3-text-image.html
    """

    images: List[str]
    seeds: List[str]
    finish_reasons: List[str]


class AmazonNovaCanvasRequestBase(TypedDict, total=False):
    """
    Base class for Amazon Nova Canvas API requests
    """

    pass


class AmazonNovaCanvasImageGenerationConfig(TypedDict, total=False):
    """
    Config for Amazon Nova Canvas Text to Image API

    Ref: https://docs.aws.amazon.com/nova/latest/userguide/image-gen-req-resp-structure.html
    """

    cfgScale: int
    seed: int
    quality: Literal["standard", "premium"]
    width: int
    height: int
    numberOfImages: int


class AmazonNovaCanvasTextToImageParams(TypedDict, total=False):
    """
    Params for Amazon Nova Canvas Text to Image API
    """

    text: str
    negativeText: str
    controlStrength: float
    controlMode: Literal["CANNY_EDIT", "SEGMENTATION"]
    conditionImage: str


class AmazonNovaCanvasTextToImageRequest(
    AmazonNovaCanvasRequestBase, TypedDict, total=False
):
    """
    Request for Amazon Nova Canvas Text to Image API

    Ref: https://docs.aws.amazon.com/nova/latest/userguide/image-gen-req-resp-structure.html
    """

    textToImageParams: AmazonNovaCanvasTextToImageParams
    taskType: Literal["TEXT_IMAGE"]
    imageGenerationConfig: AmazonNovaCanvasImageGenerationConfig


class AmazonNovaCanvasColorGuidedGenerationParams(TypedDict, total=False):
    """
    Params for Amazon Nova Canvas Color Guided Generation API
    """

    colors: List[str]
    referenceImage: str
    text: str
    negativeText: str


class AmazonNovaCanvasColorGuidedRequest(
    AmazonNovaCanvasRequestBase, TypedDict, total=False
):
    """
    Request for Amazon Nova Canvas Color Guided Generation API

    Ref: https://docs.aws.amazon.com/nova/latest/userguide/image-gen-req-resp-structure.html
    """

    taskType: Literal["COLOR_GUIDED_GENERATION"]
    colorGuidedGenerationParams: AmazonNovaCanvasColorGuidedGenerationParams
    imageGenerationConfig: AmazonNovaCanvasImageGenerationConfig


class AmazonNovaCanvasTextToImageResponse(TypedDict, total=False):
    """
    Response for Amazon Nova Canvas Text to Image API

    Ref: https://docs.aws.amazon.com/nova/latest/userguide/image-gen-req-resp-structure.html
    """

    images: List[str]


if TYPE_CHECKING:
    from botocore.awsrequest import AWSPreparedRequest
else:
    AWSPreparedRequest = Any

from pydantic import BaseModel


class BedrockPreparedRequest(TypedDict):
    """
    Internal/Helper class for preparing the request for bedrock image generation
    """

    endpoint_url: str
    prepped: AWSPreparedRequest
    body: bytes
    data: dict


class BedrockRerankTextQuery(TypedDict):
    text: str


class BedrockRerankQuery(TypedDict):
    textQuery: BedrockRerankTextQuery
    type: Literal["TEXT"]


class BedrockRerankModelConfiguration(TypedDict, total=False):
    modelArn: Required[str]
    modelConfiguration: dict


class BedrockRerankBedrockRerankingConfiguration(TypedDict):
    modelConfiguration: BedrockRerankModelConfiguration
    numberOfResults: int


class BedrockRerankConfiguration(TypedDict):
    bedrockRerankingConfiguration: BedrockRerankBedrockRerankingConfiguration
    type: Literal["BEDROCK_RERANKING_MODEL"]


class BedrockRerankTextDocument(TypedDict, total=False):
    text: str


class BedrockRerankInlineDocumentSource(TypedDict, total=False):
    jsonDocument: dict
    textDocument: BedrockRerankTextDocument
    type: Literal["TEXT", "JSON"]


class BedrockRerankSource(TypedDict):
    inlineDocumentSource: BedrockRerankInlineDocumentSource
    type: Literal["INLINE"]


class BedrockRerankRequest(TypedDict):
    """
    Request for Bedrock Rerank API
    """

    queries: List[BedrockRerankQuery]
    rerankingConfiguration: BedrockRerankConfiguration
    sources: List[BedrockRerankSource]


class AmazonDeepSeekR1StreamingResponse(TypedDict):
    generation: str
    generation_token_count: int
    stop_reason: Optional[str]
    prompt_token_count: int

# === NexusCore/openenv\Lib\site-packages\pyasn1\type\namedtype.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import sys

from pyasn1 import error
from pyasn1.type import tag
from pyasn1.type import tagmap

__all__ = ['NamedType', 'OptionalNamedType', 'DefaultedNamedType',
           'NamedTypes']

class NamedType(object):
    """Create named field object for a constructed ASN.1 type.

    The |NamedType| object represents a single name and ASN.1 type of a constructed ASN.1 type.

    |NamedType| objects are immutable and duck-type Python :class:`tuple` objects
    holding *name* and *asn1Object* components.

    Parameters
    ----------
    name: :py:class:`str`
        Field name

    asn1Object:
        ASN.1 type object
    """
    isOptional = False
    isDefaulted = False

    def __init__(self, name, asn1Object, openType=None):
        self.__name = name
        self.__type = asn1Object
        self.__nameAndType = name, asn1Object
        self.__openType = openType

    def __repr__(self):
        representation = '%s=%r' % (self.name, self.asn1Object)

        if self.openType:
            representation += ', open type %r' % self.openType

        return '<%s object, type %s>' % (
            self.__class__.__name__, representation)

    def __eq__(self, other):
        return self.__nameAndType == other

    def __ne__(self, other):
        return self.__nameAndType != other

    def __lt__(self, other):
        return self.__nameAndType < other

    def __le__(self, other):
        return self.__nameAndType <= other

    def __gt__(self, other):
        return self.__nameAndType > other

    def __ge__(self, other):
        return self.__nameAndType >= other

    def __hash__(self):
        return hash(self.__nameAndType)

    def __getitem__(self, idx):
        return self.__nameAndType[idx]

    def __iter__(self):
        return iter(self.__nameAndType)

    @property
    def name(self):
        return self.__name

    @property
    def asn1Object(self):
        return self.__type

    @property
    def openType(self):
        return self.__openType

    # Backward compatibility

    def getName(self):
        return self.name

    def getType(self):
        return self.asn1Object


class OptionalNamedType(NamedType):
    __doc__ = NamedType.__doc__

    isOptional = True


class DefaultedNamedType(NamedType):
    __doc__ = NamedType.__doc__

    isDefaulted = True


class NamedTypes(object):
    """Create a collection of named fields for a constructed ASN.1 type.

    The NamedTypes object represents a collection of named fields of a constructed ASN.1 type.

    *NamedTypes* objects are immutable and duck-type Python :class:`dict` objects
    holding *name* as keys and ASN.1 type object as values.

    Parameters
    ----------
    *namedTypes: :class:`~pyasn1.type.namedtype.NamedType`

    Examples
    --------

    .. code-block:: python

        class Description(Sequence):
            '''
            ASN.1 specification:

            Description ::= SEQUENCE {
                surname    IA5String,
                first-name IA5String OPTIONAL,
                age        INTEGER DEFAULT 40
            }
            '''
            componentType = NamedTypes(
                NamedType('surname', IA5String()),
                OptionalNamedType('first-name', IA5String()),
                DefaultedNamedType('age', Integer(40))
            )

        descr = Description()
        descr['surname'] = 'Smith'
        descr['first-name'] = 'John'
    """
    def __init__(self, *namedTypes, **kwargs):
        self.__namedTypes = namedTypes
        self.__namedTypesLen = len(self.__namedTypes)
        self.__minTagSet = self.__computeMinTagSet()
        self.__nameToPosMap = self.__computeNameToPosMap()
        self.__tagToPosMap = self.__computeTagToPosMap()
        self.__ambiguousTypes = 'terminal' not in kwargs and self.__computeAmbiguousTypes() or {}
        self.__uniqueTagMap = self.__computeTagMaps(unique=True)
        self.__nonUniqueTagMap = self.__computeTagMaps(unique=False)
        self.__hasOptionalOrDefault = any([True for namedType in self.__namedTypes
                                           if namedType.isDefaulted or namedType.isOptional])
        self.__hasOpenTypes = any([True for namedType in self.__namedTypes
                                   if namedType.openType])

        self.__requiredComponents = frozenset(
                [idx for idx, nt in enumerate(self.__namedTypes) if not nt.isOptional and not nt.isDefaulted]
            )
        self.__keys = frozenset([namedType.name for namedType in self.__namedTypes])
        self.__values = tuple([namedType.asn1Object for namedType in self.__namedTypes])
        self.__items = tuple([(namedType.name, namedType.asn1Object) for namedType in self.__namedTypes])

    def __repr__(self):
        representation = ', '.join(['%r' % x for x in self.__namedTypes])
        return '<%s object, types %s>' % (
            self.__class__.__name__, representation)

    def __eq__(self, other):
        return self.__namedTypes == other

    def __ne__(self, other):
        return self.__namedTypes != other

    def __lt__(self, other):
        return self.__namedTypes < other

    def __le__(self, other):
        return self.__namedTypes <= other

    def __gt__(self, other):
        return self.__namedTypes > other

    def __ge__(self, other):
        return self.__namedTypes >= other

    def __hash__(self):
        return hash(self.__namedTypes)

    def __getitem__(self, idx):
        try:
            return self.__namedTypes[idx]

        except TypeError:
            return self.__namedTypes[self.__nameToPosMap[idx]]

    def __contains__(self, key):
        return key in self.__nameToPosMap

    def __iter__(self):
        return (x[0] for x in self.__namedTypes)

    def __bool__(self):
        return self.__namedTypesLen > 0

    def __len__(self):
        return self.__namedTypesLen

    # Python dict protocol

    def values(self):
        return self.__values

    def keys(self):
        return self.__keys

    def items(self):
        return self.__items

    def clone(self):
        return self.__class__(*self.__namedTypes)

    class PostponedError(object):
        def __init__(self, errorMsg):
            self.__errorMsg = errorMsg

        def __getitem__(self, item):
            raise  error.PyAsn1Error(self.__errorMsg)

    def __computeTagToPosMap(self):
        tagToPosMap = {}
        for idx, namedType in enumerate(self.__namedTypes):
            tagMap = namedType.asn1Object.tagMap
            if isinstance(tagMap, NamedTypes.PostponedError):
                return tagMap
            if not tagMap:
                continue
            for _tagSet in tagMap.presentTypes:
                if _tagSet in tagToPosMap:
                    return NamedTypes.PostponedError('Duplicate component tag %s at %s' % (_tagSet, namedType))
                tagToPosMap[_tagSet] = idx

        return tagToPosMap

    def __computeNameToPosMap(self):
        nameToPosMap = {}
        for idx, namedType in enumerate(self.__namedTypes):
            if namedType.name in nameToPosMap:
                return NamedTypes.PostponedError('Duplicate component name %s at %s' % (namedType.name, namedType))
            nameToPosMap[namedType.name] = idx

        return nameToPosMap

    def __computeAmbiguousTypes(self):
        ambiguousTypes = {}
        partialAmbiguousTypes = ()
        for idx, namedType in reversed(tuple(enumerate(self.__namedTypes))):
            if namedType.isOptional or namedType.isDefaulted:
                partialAmbiguousTypes = (namedType,) + partialAmbiguousTypes
            else:
                partialAmbiguousTypes = (namedType,)
            if len(partialAmbiguousTypes) == len(self.__namedTypes):
                ambiguousTypes[idx] = self
            else:
                ambiguousTypes[idx] = NamedTypes(*partialAmbiguousTypes, **dict(terminal=True))
        return ambiguousTypes

    def getTypeByPosition(self, idx):
        """Return ASN.1 type object by its position in fields set.

        Parameters
        ----------
        idx: :py:class:`int`
            Field index

        Returns
        -------
        :
            ASN.1 type

        Raises
        ------
        ~pyasn1.error.PyAsn1Error
            If given position is out of fields range
        """
        try:
            return self.__namedTypes[idx].asn1Object

        except IndexError:
            raise error.PyAsn1Error('Type position out of range')

    def getPositionByType(self, tagSet):
        """Return field position by its ASN.1 type.

        Parameters
        ----------
        tagSet: :class:`~pysnmp.type.tag.TagSet`
            ASN.1 tag set distinguishing one ASN.1 type from others.

        Returns
        -------
        : :py:class:`int`
            ASN.1 type position in fields set

        Raises
        ------
        ~pyasn1.error.PyAsn1Error
            If *tagSet* is not present or ASN.1 types are not unique within callee *NamedTypes*
        """
        try:
            return self.__tagToPosMap[tagSet]

        except KeyError:
            raise error.PyAsn1Error('Type %s not found' % (tagSet,))

    def getNameByPosition(self, idx):
        """Return field name by its position in fields set.

        Parameters
        ----------
        idx: :py:class:`idx`
            Field index

        Returns
        -------
        : :py:class:`str`
            Field name

        Raises
        ------
        ~pyasn1.error.PyAsn1Error
            If given field name is not present in callee *NamedTypes*
        """
        try:
            return self.__namedTypes[idx].name

        except IndexError:
            raise error.PyAsn1Error('Type position out of range')

    def getPositionByName(self, name):
        """Return field position by filed name.

        Parameters
        ----------
        name: :py:class:`str`
            Field name

        Returns
        -------
        : :py:class:`int`
            Field position in fields set

        Raises
        ------
        ~pyasn1.error.PyAsn1Error
            If *name* is not present or not unique within callee *NamedTypes*
        """
        try:
            return self.__nameToPosMap[name]

        except KeyError:
            raise error.PyAsn1Error('Name %s not found' % (name,))

    def getTagMapNearPosition(self, idx):
        """Return ASN.1 types that are allowed at or past given field position.

        Some ASN.1 serialisation allow for skipping optional and defaulted fields.
        Some constructed ASN.1 types allow reordering of the fields. When recovering
        such objects it may be important to know which types can possibly be
        present at any given position in the field sets.

        Parameters
        ----------
        idx: :py:class:`int`
            Field index

        Returns
        -------
        : :class:`~pyasn1.type.tagmap.TagMap`
            Map if ASN.1 types allowed at given field position

        Raises
        ------
        ~pyasn1.error.PyAsn1Error
            If given position is out of fields range
        """
        try:
            return self.__ambiguousTypes[idx].tagMap

        except KeyError:
            raise error.PyAsn1Error('Type position out of range')

    def getPositionNearType(self, tagSet, idx):
        """Return the closest field position where given ASN.1 type is allowed.

        Some ASN.1 serialisation allow for skipping optional and defaulted fields.
        Some constructed ASN.1 types allow reordering of the fields. When recovering
        such objects it may be important to know at which field position, in field set,
        given *tagSet* is allowed at or past *idx* position.

        Parameters
        ----------
        tagSet: :class:`~pyasn1.type.tag.TagSet`
           ASN.1 type which field position to look up

        idx: :py:class:`int`
            Field position at or past which to perform ASN.1 type look up

        Returns
        -------
        : :py:class:`int`
            Field position in fields set

        Raises
        ------
        ~pyasn1.error.PyAsn1Error
            If *tagSet* is not present or not unique within callee *NamedTypes*
            or *idx* is out of fields range
        """
        try:
            return idx + self.__ambiguousTypes[idx].getPositionByType(tagSet)

        except KeyError:
            raise error.PyAsn1Error('Type position out of range')

    def __computeMinTagSet(self):
        minTagSet = None
        for namedType in self.__namedTypes:
            asn1Object = namedType.asn1Object

            try:
                tagSet = asn1Object.minTagSet

            except AttributeError:
                tagSet = asn1Object.tagSet

            if minTagSet is None or tagSet < minTagSet:
                minTagSet = tagSet

        return minTagSet or tag.TagSet()

    @property
    def minTagSet(self):
        """Return the minimal TagSet among ASN.1 type in callee *NamedTypes*.

        Some ASN.1 types/serialisation protocols require ASN.1 types to be
        arranged based on their numerical tag value. The *minTagSet* property
        returns that.

        Returns
        -------
        : :class:`~pyasn1.type.tagset.TagSet`
            Minimal TagSet among ASN.1 types in callee *NamedTypes*
        """
        return self.__minTagSet

    def __computeTagMaps(self, unique):
        presentTypes = {}
        skipTypes = {}
        defaultType = None
        for namedType in self.__namedTypes:
            tagMap = namedType.asn1Object.tagMap
            if isinstance(tagMap, NamedTypes.PostponedError):
                return tagMap
            for tagSet in tagMap:
                if unique and tagSet in presentTypes:
                    return NamedTypes.PostponedError('Non-unique tagSet %s of %s at %s' % (tagSet, namedType, self))
                presentTypes[tagSet] = namedType.asn1Object
            skipTypes.update(tagMap.skipTypes)

            if defaultType is None:
                defaultType = tagMap.defaultType
            elif tagMap.defaultType is not None:
                return NamedTypes.PostponedError('Duplicate default ASN.1 type at %s' % (self,))

        return tagmap.TagMap(presentTypes, skipTypes, defaultType)

    @property
    def tagMap(self):
        """Return a *TagMap* object from tags and types recursively.

        Return a :class:`~pyasn1.type.tagmap.TagMap` object by
        combining tags from *TagMap* objects of children types and
        associating them with their immediate child type.

        Example
        -------
        .. code-block:: python

           OuterType ::= CHOICE {
               innerType INTEGER
           }

        Calling *.tagMap* on *OuterType* will yield a map like this:

        .. code-block:: python

           Integer.tagSet -> Choice
        """
        return self.__nonUniqueTagMap

    @property
    def tagMapUnique(self):
        """Return a *TagMap* object from unique tags and types recursively.

        Return a :class:`~pyasn1.type.tagmap.TagMap` object by
        combining tags from *TagMap* objects of children types and
        associating them with their immediate child type.

        Example
        -------
        .. code-block:: python

           OuterType ::= CHOICE {
               innerType INTEGER
           }

        Calling *.tagMapUnique* on *OuterType* will yield a map like this:

        .. code-block:: python

           Integer.tagSet -> Choice

        Note
        ----

        Duplicate *TagSet* objects found in the tree of children
        types would cause error.
        """
        return self.__uniqueTagMap

    @property
    def hasOptionalOrDefault(self):
        return self.__hasOptionalOrDefault

    @property
    def hasOpenTypes(self):
        return self.__hasOpenTypes

    @property
    def namedTypes(self):
        return tuple(self.__namedTypes)

    @property
    def requiredComponents(self):
        return self.__requiredComponents

# === NexusCore/openenv\Lib\site-packages\nltk\translate\ibm_model.py ===
# Natural Language Toolkit: IBM Model Core
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Tah Wei Hoon <hoon.tw@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Common methods and classes for all IBM models. See ``IBMModel1``,
``IBMModel2``, ``IBMModel3``, ``IBMModel4``, and ``IBMModel5``
for specific implementations.

The IBM models are a series of generative models that learn lexical
translation probabilities, p(target language word|source language word),
given a sentence-aligned parallel corpus.

The models increase in sophistication from model 1 to 5. Typically, the
output of lower models is used to seed the higher models. All models
use the Expectation-Maximization (EM) algorithm to learn various
probability tables.

Words in a sentence are one-indexed. The first word of a sentence has
position 1, not 0. Index 0 is reserved in the source sentence for the
NULL token. The concept of position does not apply to NULL, but it is
indexed at 0 by convention.

Each target word is aligned to exactly one source word or the NULL
token.

References:
Philipp Koehn. 2010. Statistical Machine Translation.
Cambridge University Press, New York.

Peter E Brown, Stephen A. Della Pietra, Vincent J. Della Pietra, and
Robert L. Mercer. 1993. The Mathematics of Statistical Machine
Translation: Parameter Estimation. Computational Linguistics, 19 (2),
263-311.
"""

from bisect import insort_left
from collections import defaultdict
from copy import deepcopy
from math import ceil


def longest_target_sentence_length(sentence_aligned_corpus):
    """
    :param sentence_aligned_corpus: Parallel corpus under consideration
    :type sentence_aligned_corpus: list(AlignedSent)
    :return: Number of words in the longest target language sentence
        of ``sentence_aligned_corpus``
    """
    max_m = 0
    for aligned_sentence in sentence_aligned_corpus:
        m = len(aligned_sentence.words)
        max_m = max(m, max_m)
    return max_m


class IBMModel:
    """
    Abstract base class for all IBM models
    """

    # Avoid division by zero and precision errors by imposing a minimum
    # value for probabilities. Note that this approach is theoretically
    # incorrect, since it may create probabilities that sum to more
    # than 1. In practice, the contribution of probabilities with MIN_PROB
    # is tiny enough that the value of MIN_PROB can be treated as zero.
    MIN_PROB = 1.0e-12  # GIZA++ is more liberal and uses 1.0e-7

    def __init__(self, sentence_aligned_corpus):
        self.init_vocab(sentence_aligned_corpus)
        self.reset_probabilities()

    def reset_probabilities(self):
        self.translation_table = defaultdict(
            lambda: defaultdict(lambda: IBMModel.MIN_PROB)
        )
        """
        dict[str][str]: float. Probability(target word | source word).
        Values accessed as ``translation_table[target_word][source_word]``.
        """

        self.alignment_table = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: IBMModel.MIN_PROB))
            )
        )
        """
        dict[int][int][int][int]: float. Probability(i | j,l,m).
        Values accessed as ``alignment_table[i][j][l][m]``.
        Used in model 2 and hill climbing in models 3 and above
        """

        self.fertility_table = defaultdict(lambda: defaultdict(lambda: self.MIN_PROB))
        """
        dict[int][str]: float. Probability(fertility | source word).
        Values accessed as ``fertility_table[fertility][source_word]``.
        Used in model 3 and higher.
        """

        self.p1 = 0.5
        """
        Probability that a generated word requires another target word
        that is aligned to NULL.
        Used in model 3 and higher.
        """

    def set_uniform_probabilities(self, sentence_aligned_corpus):
        """
        Initialize probability tables to a uniform distribution

        Derived classes should implement this accordingly.
        """
        pass

    def init_vocab(self, sentence_aligned_corpus):
        src_vocab = set()
        trg_vocab = set()
        for aligned_sentence in sentence_aligned_corpus:
            trg_vocab.update(aligned_sentence.words)
            src_vocab.update(aligned_sentence.mots)
        # Add the NULL token
        src_vocab.add(None)

        self.src_vocab = src_vocab
        """
        set(str): All source language words used in training
        """

        self.trg_vocab = trg_vocab
        """
        set(str): All target language words used in training
        """

    def sample(self, sentence_pair):
        """
        Sample the most probable alignments from the entire alignment
        space

        First, determine the best alignment according to IBM Model 2.
        With this initial alignment, use hill climbing to determine the
        best alignment according to a higher IBM Model. Add this
        alignment and its neighbors to the sample set. Repeat this
        process with other initial alignments obtained by pegging an
        alignment point.

        Hill climbing may be stuck in a local maxima, hence the pegging
        and trying out of different alignments.

        :param sentence_pair: Source and target language sentence pair
            to generate a sample of alignments from
        :type sentence_pair: AlignedSent

        :return: A set of best alignments represented by their ``AlignmentInfo``
            and the best alignment of the set for convenience
        :rtype: set(AlignmentInfo), AlignmentInfo
        """
        sampled_alignments = set()
        l = len(sentence_pair.mots)
        m = len(sentence_pair.words)

        # Start from the best model 2 alignment
        initial_alignment = self.best_model2_alignment(sentence_pair)
        potential_alignment = self.hillclimb(initial_alignment)
        sampled_alignments.update(self.neighboring(potential_alignment))
        best_alignment = potential_alignment

        # Start from other model 2 alignments,
        # with the constraint that j is aligned (pegged) to i
        for j in range(1, m + 1):
            for i in range(0, l + 1):
                initial_alignment = self.best_model2_alignment(sentence_pair, j, i)
                potential_alignment = self.hillclimb(initial_alignment, j)
                neighbors = self.neighboring(potential_alignment, j)
                sampled_alignments.update(neighbors)
                if potential_alignment.score > best_alignment.score:
                    best_alignment = potential_alignment

        return sampled_alignments, best_alignment

    def best_model2_alignment(self, sentence_pair, j_pegged=None, i_pegged=0):
        """
        Finds the best alignment according to IBM Model 2

        Used as a starting point for hill climbing in Models 3 and
        above, because it is easier to compute than the best alignments
        in higher models

        :param sentence_pair: Source and target language sentence pair
            to be word-aligned
        :type sentence_pair: AlignedSent

        :param j_pegged: If specified, the alignment point of j_pegged
            will be fixed to i_pegged
        :type j_pegged: int

        :param i_pegged: Alignment point to j_pegged
        :type i_pegged: int
        """
        src_sentence = [None] + sentence_pair.mots
        trg_sentence = ["UNUSED"] + sentence_pair.words  # 1-indexed

        l = len(src_sentence) - 1  # exclude NULL
        m = len(trg_sentence) - 1

        alignment = [0] * (m + 1)  # init all alignments to NULL
        cepts = [[] for i in range(l + 1)]  # init all cepts to empty list

        for j in range(1, m + 1):
            if j == j_pegged:
                # use the pegged alignment instead of searching for best one
                best_i = i_pegged
            else:
                best_i = 0
                max_alignment_prob = IBMModel.MIN_PROB
                t = trg_sentence[j]

                for i in range(0, l + 1):
                    s = src_sentence[i]
                    alignment_prob = (
                        self.translation_table[t][s] * self.alignment_table[i][j][l][m]
                    )

                    if alignment_prob >= max_alignment_prob:
                        max_alignment_prob = alignment_prob
                        best_i = i

            alignment[j] = best_i
            cepts[best_i].append(j)

        return AlignmentInfo(
            tuple(alignment), tuple(src_sentence), tuple(trg_sentence), cepts
        )

    def hillclimb(self, alignment_info, j_pegged=None):
        """
        Starting from the alignment in ``alignment_info``, look at
        neighboring alignments iteratively for the best one

        There is no guarantee that the best alignment in the alignment
        space will be found, because the algorithm might be stuck in a
        local maximum.

        :param j_pegged: If specified, the search will be constrained to
            alignments where ``j_pegged`` remains unchanged
        :type j_pegged: int

        :return: The best alignment found from hill climbing
        :rtype: AlignmentInfo
        """
        alignment = alignment_info  # alias with shorter name
        max_probability = self.prob_t_a_given_s(alignment)

        while True:
            old_alignment = alignment
            for neighbor_alignment in self.neighboring(alignment, j_pegged):
                neighbor_probability = self.prob_t_a_given_s(neighbor_alignment)

                if neighbor_probability > max_probability:
                    alignment = neighbor_alignment
                    max_probability = neighbor_probability

            if alignment == old_alignment:
                # Until there are no better alignments
                break

        alignment.score = max_probability
        return alignment

    def neighboring(self, alignment_info, j_pegged=None):
        """
        Determine the neighbors of ``alignment_info``, obtained by
        moving or swapping one alignment point

        :param j_pegged: If specified, neighbors that have a different
            alignment point from j_pegged will not be considered
        :type j_pegged: int

        :return: A set neighboring alignments represented by their
            ``AlignmentInfo``
        :rtype: set(AlignmentInfo)
        """
        neighbors = set()

        l = len(alignment_info.src_sentence) - 1  # exclude NULL
        m = len(alignment_info.trg_sentence) - 1
        original_alignment = alignment_info.alignment
        original_cepts = alignment_info.cepts

        for j in range(1, m + 1):
            if j != j_pegged:
                # Add alignments that differ by one alignment point
                for i in range(0, l + 1):
                    new_alignment = list(original_alignment)
                    new_cepts = deepcopy(original_cepts)
                    old_i = original_alignment[j]

                    # update alignment
                    new_alignment[j] = i

                    # update cepts
                    insort_left(new_cepts[i], j)
                    new_cepts[old_i].remove(j)

                    new_alignment_info = AlignmentInfo(
                        tuple(new_alignment),
                        alignment_info.src_sentence,
                        alignment_info.trg_sentence,
                        new_cepts,
                    )
                    neighbors.add(new_alignment_info)

        for j in range(1, m + 1):
            if j != j_pegged:
                # Add alignments that have two alignment points swapped
                for other_j in range(1, m + 1):
                    if other_j != j_pegged and other_j != j:
                        new_alignment = list(original_alignment)
                        new_cepts = deepcopy(original_cepts)
                        other_i = original_alignment[other_j]
                        i = original_alignment[j]

                        # update alignments
                        new_alignment[j] = other_i
                        new_alignment[other_j] = i

                        # update cepts
                        new_cepts[other_i].remove(other_j)
                        insort_left(new_cepts[other_i], j)
                        new_cepts[i].remove(j)
                        insort_left(new_cepts[i], other_j)

                        new_alignment_info = AlignmentInfo(
                            tuple(new_alignment),
                            alignment_info.src_sentence,
                            alignment_info.trg_sentence,
                            new_cepts,
                        )
                        neighbors.add(new_alignment_info)

        return neighbors

    def maximize_lexical_translation_probabilities(self, counts):
        for t, src_words in counts.t_given_s.items():
            for s in src_words:
                estimate = counts.t_given_s[t][s] / counts.any_t_given_s[s]
                self.translation_table[t][s] = max(estimate, IBMModel.MIN_PROB)

    def maximize_fertility_probabilities(self, counts):
        for phi, src_words in counts.fertility.items():
            for s in src_words:
                estimate = counts.fertility[phi][s] / counts.fertility_for_any_phi[s]
                self.fertility_table[phi][s] = max(estimate, IBMModel.MIN_PROB)

    def maximize_null_generation_probabilities(self, counts):
        p1_estimate = counts.p1 / (counts.p1 + counts.p0)
        p1_estimate = max(p1_estimate, IBMModel.MIN_PROB)
        # Clip p1 if it is too large, because p0 = 1 - p1 should not be
        # smaller than MIN_PROB
        self.p1 = min(p1_estimate, 1 - IBMModel.MIN_PROB)

    def prob_of_alignments(self, alignments):
        probability = 0
        for alignment_info in alignments:
            probability += self.prob_t_a_given_s(alignment_info)
        return probability

    def prob_t_a_given_s(self, alignment_info):
        """
        Probability of target sentence and an alignment given the
        source sentence

        All required information is assumed to be in ``alignment_info``
        and self.

        Derived classes should override this method
        """
        return 0.0


class AlignmentInfo:
    """
    Helper data object for training IBM Models 3 and up

    Read-only. For a source sentence and its counterpart in the target
    language, this class holds information about the sentence pair's
    alignment, cepts, and fertility.

    Warning: Alignments are one-indexed here, in contrast to
    nltk.translate.Alignment and AlignedSent, which are zero-indexed
    This class is not meant to be used outside of IBM models.
    """

    def __init__(self, alignment, src_sentence, trg_sentence, cepts):
        if not isinstance(alignment, tuple):
            raise TypeError(
                "The alignment must be a tuple because it is used "
                "to uniquely identify AlignmentInfo objects."
            )

        self.alignment = alignment
        """
        tuple(int): Alignment function. ``alignment[j]`` is the position
        in the source sentence that is aligned to the position j in the
        target sentence.
        """

        self.src_sentence = src_sentence
        """
        tuple(str): Source sentence referred to by this object.
        Should include NULL token (None) in index 0.
        """

        self.trg_sentence = trg_sentence
        """
        tuple(str): Target sentence referred to by this object.
        Should have a dummy element in index 0 so that the first word
        starts from index 1.
        """

        self.cepts = cepts
        """
        list(list(int)): The positions of the target words, in
        ascending order, aligned to a source word position. For example,
        cepts[4] = (2, 3, 7) means that words in positions 2, 3 and 7
        of the target sentence are aligned to the word in position 4 of
        the source sentence
        """

        self.score = None
        """
        float: Optional. Probability of alignment, as defined by the
        IBM model that assesses this alignment
        """

    def fertility_of_i(self, i):
        """
        Fertility of word in position ``i`` of the source sentence
        """
        return len(self.cepts[i])

    def is_head_word(self, j):
        """
        :return: Whether the word in position ``j`` of the target
            sentence is a head word
        """
        i = self.alignment[j]
        return self.cepts[i][0] == j

    def center_of_cept(self, i):
        """
        :return: The ceiling of the average positions of the words in
            the tablet of cept ``i``, or 0 if ``i`` is None
        """
        if i is None:
            return 0

        average_position = sum(self.cepts[i]) / len(self.cepts[i])
        return int(ceil(average_position))

    def previous_cept(self, j):
        """
        :return: The previous cept of ``j``, or None if ``j`` belongs to
            the first cept
        """
        i = self.alignment[j]
        if i == 0:
            raise ValueError(
                "Words aligned to NULL cannot have a previous "
                "cept because NULL has no position"
            )
        previous_cept = i - 1
        while previous_cept > 0 and self.fertility_of_i(previous_cept) == 0:
            previous_cept -= 1

        if previous_cept <= 0:
            previous_cept = None
        return previous_cept

    def previous_in_tablet(self, j):
        """
        :return: The position of the previous word that is in the same
            tablet as ``j``, or None if ``j`` is the first word of the
            tablet
        """
        i = self.alignment[j]
        tablet_position = self.cepts[i].index(j)
        if tablet_position == 0:
            return None
        return self.cepts[i][tablet_position - 1]

    def zero_indexed_alignment(self):
        """
        :return: Zero-indexed alignment, suitable for use in external
            ``nltk.translate`` modules like ``nltk.translate.Alignment``
        :rtype: list(tuple)
        """
        zero_indexed_alignment = []
        for j in range(1, len(self.trg_sentence)):
            i = self.alignment[j] - 1
            if i < 0:
                i = None  # alignment to NULL token
            zero_indexed_alignment.append((j - 1, i))
        return zero_indexed_alignment

    def __eq__(self, other):
        return self.alignment == other.alignment

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.alignment)


class Counts:
    """
    Data object to store counts of various parameters during training
    """

    def __init__(self):
        self.t_given_s = defaultdict(lambda: defaultdict(float))
        self.any_t_given_s = defaultdict(float)
        self.p0 = 0.0
        self.p1 = 0.0
        self.fertility = defaultdict(lambda: defaultdict(float))
        self.fertility_for_any_phi = defaultdict(float)

    def update_lexical_translation(self, count, alignment_info, j):
        i = alignment_info.alignment[j]
        t = alignment_info.trg_sentence[j]
        s = alignment_info.src_sentence[i]
        self.t_given_s[t][s] += count
        self.any_t_given_s[s] += count

    def update_null_generation(self, count, alignment_info):
        m = len(alignment_info.trg_sentence) - 1
        fertility_of_null = alignment_info.fertility_of_i(0)
        self.p1 += fertility_of_null * count
        self.p0 += (m - 2 * fertility_of_null) * count

    def update_fertility(self, count, alignment_info):
        for i in range(0, len(alignment_info.src_sentence)):
            s = alignment_info.src_sentence[i]
            phi = alignment_info.fertility_of_i(i)
            self.fertility[phi][s] += count
            self.fertility_for_any_phi[s] += count

# === NexusCore/openenv\Lib\site-packages\setuptools\build_meta.py ===
"""A PEP 517 interface to setuptools

Previously, when a user or a command line tool (let's call it a "frontend")
needed to make a request of setuptools to take a certain action, for
example, generating a list of installation requirements, the frontend
would call "setup.py egg_info" or "setup.py bdist_wheel" on the command line.

PEP 517 defines a different method of interfacing with setuptools. Rather
than calling "setup.py" directly, the frontend should:

  1. Set the current directory to the directory with a setup.py file
  2. Import this module into a safe python interpreter (one in which
     setuptools can potentially set global variables or crash hard).
  3. Call one of the functions defined in PEP 517.

What each function does is defined in PEP 517. However, here is a "casual"
definition of the functions (this definition should not be relied on for
bug reports or API stability):

  - `build_wheel`: build a wheel in the folder and return the basename
  - `get_requires_for_build_wheel`: get the `setup_requires` to build
  - `prepare_metadata_for_build_wheel`: get the `install_requires`
  - `build_sdist`: build an sdist in the folder and return the basename
  - `get_requires_for_build_sdist`: get the `setup_requires` to build

Again, this is not a formal definition! Just a "taste" of the module.
"""

from __future__ import annotations

import contextlib
import io
import os
import shlex
import shutil
import sys
import tempfile
import tokenize
import warnings
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Union

import setuptools

from . import errors
from ._path import StrPath, same_path
from ._reqs import parse_strings
from .warnings import SetuptoolsDeprecationWarning

import distutils
from distutils.util import strtobool

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

__all__ = [
    'get_requires_for_build_sdist',
    'get_requires_for_build_wheel',
    'prepare_metadata_for_build_wheel',
    'build_wheel',
    'build_sdist',
    'get_requires_for_build_editable',
    'prepare_metadata_for_build_editable',
    'build_editable',
    '__legacy__',
    'SetupRequirementsError',
]


class SetupRequirementsError(BaseException):
    def __init__(self, specifiers) -> None:
        self.specifiers = specifiers


class Distribution(setuptools.dist.Distribution):
    def fetch_build_eggs(self, specifiers):
        specifier_list = list(parse_strings(specifiers))

        raise SetupRequirementsError(specifier_list)

    @classmethod
    @contextlib.contextmanager
    def patch(cls):
        """
        Replace
        distutils.dist.Distribution with this class
        for the duration of this context.
        """
        orig = distutils.core.Distribution
        distutils.core.Distribution = cls  # type: ignore[misc] # monkeypatching
        try:
            yield
        finally:
            distutils.core.Distribution = orig  # type: ignore[misc] # monkeypatching


@contextlib.contextmanager
def no_install_setup_requires():
    """Temporarily disable installing setup_requires

    Under PEP 517, the backend reports build dependencies to the frontend,
    and the frontend is responsible for ensuring they're installed.
    So setuptools (acting as a backend) should not try to install them.
    """
    orig = setuptools._install_setup_requires
    setuptools._install_setup_requires = lambda attrs: None
    try:
        yield
    finally:
        setuptools._install_setup_requires = orig


def _get_immediate_subdirectories(a_dir):
    return [
        name for name in os.listdir(a_dir) if os.path.isdir(os.path.join(a_dir, name))
    ]


def _file_with_extension(directory: StrPath, extension: str | tuple[str, ...]):
    matching = (f for f in os.listdir(directory) if f.endswith(extension))
    try:
        (file,) = matching
    except ValueError:
        raise ValueError(
            'No distribution was found. Ensure that `setup.py` '
            'is not empty and that it calls `setup()`.'
        ) from None
    return file


def _open_setup_script(setup_script):
    if not os.path.exists(setup_script):
        # Supply a default setup.py
        return io.StringIO("from setuptools import setup; setup()")

    return tokenize.open(setup_script)


@contextlib.contextmanager
def suppress_known_deprecation():
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', 'setup.py install is deprecated')
        yield


_ConfigSettings: TypeAlias = Union[Mapping[str, Union[str, list[str], None]], None]
"""
Currently the user can run::

    pip install -e . --config-settings key=value
    python -m build -C--key=value -C key=value

- pip will pass both key and value as strings and overwriting repeated keys
  (pypa/pip#11059).
- build will accumulate values associated with repeated keys in a list.
  It will also accept keys with no associated value.
  This means that an option passed by build can be ``str | list[str] | None``.
- PEP 517 specifies that ``config_settings`` is an optional dict.
"""


class _ConfigSettingsTranslator:
    """Translate ``config_settings`` into distutils-style command arguments.
    Only a limited number of options is currently supported.
    """

    # See pypa/setuptools#1928 pypa/setuptools#2491

    def _get_config(self, key: str, config_settings: _ConfigSettings) -> list[str]:
        """
        Get the value of a specific key in ``config_settings`` as a list of strings.

        >>> fn = _ConfigSettingsTranslator()._get_config
        >>> fn("--global-option", None)
        []
        >>> fn("--global-option", {})
        []
        >>> fn("--global-option", {'--global-option': 'foo'})
        ['foo']
        >>> fn("--global-option", {'--global-option': ['foo']})
        ['foo']
        >>> fn("--global-option", {'--global-option': 'foo'})
        ['foo']
        >>> fn("--global-option", {'--global-option': 'foo bar'})
        ['foo', 'bar']
        """
        cfg = config_settings or {}
        opts = cfg.get(key) or []
        return shlex.split(opts) if isinstance(opts, str) else opts

    def _global_args(self, config_settings: _ConfigSettings) -> Iterator[str]:
        """
        Let the user specify ``verbose`` or ``quiet`` + escape hatch via
        ``--global-option``.
        Note: ``-v``, ``-vv``, ``-vvv`` have similar effects in setuptools,
        so we just have to cover the basic scenario ``-v``.

        >>> fn = _ConfigSettingsTranslator()._global_args
        >>> list(fn(None))
        []
        >>> list(fn({"verbose": "False"}))
        ['-q']
        >>> list(fn({"verbose": "1"}))
        ['-v']
        >>> list(fn({"--verbose": None}))
        ['-v']
        >>> list(fn({"verbose": "true", "--global-option": "-q --no-user-cfg"}))
        ['-v', '-q', '--no-user-cfg']
        >>> list(fn({"--quiet": None}))
        ['-q']
        """
        cfg = config_settings or {}
        falsey = {"false", "no", "0", "off"}
        if "verbose" in cfg or "--verbose" in cfg:
            level = str(cfg.get("verbose") or cfg.get("--verbose") or "1")
            yield ("-q" if level.lower() in falsey else "-v")
        if "quiet" in cfg or "--quiet" in cfg:
            level = str(cfg.get("quiet") or cfg.get("--quiet") or "1")
            yield ("-v" if level.lower() in falsey else "-q")

        yield from self._get_config("--global-option", config_settings)

    def __dist_info_args(self, config_settings: _ConfigSettings) -> Iterator[str]:
        """
        The ``dist_info`` command accepts ``tag-date`` and ``tag-build``.

        .. warning::
           We cannot use this yet as it requires the ``sdist`` and ``bdist_wheel``
           commands run in ``build_sdist`` and ``build_wheel`` to reuse the egg-info
           directory created in ``prepare_metadata_for_build_wheel``.

        >>> fn = _ConfigSettingsTranslator()._ConfigSettingsTranslator__dist_info_args
        >>> list(fn(None))
        []
        >>> list(fn({"tag-date": "False"}))
        ['--no-date']
        >>> list(fn({"tag-date": None}))
        ['--no-date']
        >>> list(fn({"tag-date": "true", "tag-build": ".a"}))
        ['--tag-date', '--tag-build', '.a']
        """
        cfg = config_settings or {}
        if "tag-date" in cfg:
            val = strtobool(str(cfg["tag-date"] or "false"))
            yield ("--tag-date" if val else "--no-date")
        if "tag-build" in cfg:
            yield from ["--tag-build", str(cfg["tag-build"])]

    def _editable_args(self, config_settings: _ConfigSettings) -> Iterator[str]:
        """
        The ``editable_wheel`` command accepts ``editable-mode=strict``.

        >>> fn = _ConfigSettingsTranslator()._editable_args
        >>> list(fn(None))
        []
        >>> list(fn({"editable-mode": "strict"}))
        ['--mode', 'strict']
        """
        cfg = config_settings or {}
        mode = cfg.get("editable-mode") or cfg.get("editable_mode")
        if not mode:
            return
        yield from ["--mode", str(mode)]

    def _arbitrary_args(self, config_settings: _ConfigSettings) -> Iterator[str]:
        """
        Users may expect to pass arbitrary lists of arguments to a command
        via "--global-option" (example provided in PEP 517 of a "escape hatch").

        >>> fn = _ConfigSettingsTranslator()._arbitrary_args
        >>> list(fn(None))
        []
        >>> list(fn({}))
        []
        >>> list(fn({'--build-option': 'foo'}))
        ['foo']
        >>> list(fn({'--build-option': ['foo']}))
        ['foo']
        >>> list(fn({'--build-option': 'foo'}))
        ['foo']
        >>> list(fn({'--build-option': 'foo bar'}))
        ['foo', 'bar']
        >>> list(fn({'--global-option': 'foo'}))
        []
        """
        yield from self._get_config("--build-option", config_settings)


class _BuildMetaBackend(_ConfigSettingsTranslator):
    def _get_build_requires(
        self, config_settings: _ConfigSettings, requirements: list[str]
    ):
        sys.argv = [
            *sys.argv[:1],
            *self._global_args(config_settings),
            "egg_info",
        ]
        try:
            with Distribution.patch():
                self.run_setup()
        except SetupRequirementsError as e:
            requirements += e.specifiers

        return requirements

    def run_setup(self, setup_script: str = 'setup.py'):
        # Note that we can reuse our build directory between calls
        # Correctness comes first, then optimization later
        __file__ = os.path.abspath(setup_script)
        __name__ = '__main__'

        with _open_setup_script(__file__) as f:
            code = f.read().replace(r'\r\n', r'\n')

        try:
            exec(code, locals())
        except SystemExit as e:
            if e.code:
                raise
            # We ignore exit code indicating success
            SetuptoolsDeprecationWarning.emit(
                "Running `setup.py` directly as CLI tool is deprecated.",
                "Please avoid using `sys.exit(0)` or similar statements "
                "that don't fit in the paradigm of a configuration file.",
                see_url="https://blog.ganssle.io/articles/2021/10/"
                "setup-py-deprecated.html",
            )

    def get_requires_for_build_wheel(self, config_settings: _ConfigSettings = None):
        return self._get_build_requires(config_settings, requirements=[])

    def get_requires_for_build_sdist(self, config_settings: _ConfigSettings = None):
        return self._get_build_requires(config_settings, requirements=[])

    def _bubble_up_info_directory(
        self, metadata_directory: StrPath, suffix: str
    ) -> str:
        """
        PEP 517 requires that the .dist-info directory be placed in the
        metadata_directory. To comply, we MUST copy the directory to the root.

        Returns the basename of the info directory, e.g. `proj-0.0.0.dist-info`.
        """
        info_dir = self._find_info_directory(metadata_directory, suffix)
        if not same_path(info_dir.parent, metadata_directory):
            shutil.move(str(info_dir), metadata_directory)
            # PEP 517 allow other files and dirs to exist in metadata_directory
        return info_dir.name

    def _find_info_directory(self, metadata_directory: StrPath, suffix: str) -> Path:
        for parent, dirs, _ in os.walk(metadata_directory):
            candidates = [f for f in dirs if f.endswith(suffix)]

            if len(candidates) != 0 or len(dirs) != 1:
                assert len(candidates) == 1, f"Multiple {suffix} directories found"
                return Path(parent, candidates[0])

        msg = f"No {suffix} directory found in {metadata_directory}"
        raise errors.InternalError(msg)

    def prepare_metadata_for_build_wheel(
        self, metadata_directory: StrPath, config_settings: _ConfigSettings = None
    ):
        sys.argv = [
            *sys.argv[:1],
            *self._global_args(config_settings),
            "dist_info",
            "--output-dir",
            str(metadata_directory),
            "--keep-egg-info",
        ]
        with no_install_setup_requires():
            self.run_setup()

        self._bubble_up_info_directory(metadata_directory, ".egg-info")
        return self._bubble_up_info_directory(metadata_directory, ".dist-info")

    def _build_with_temp_dir(
        self,
        setup_command: Iterable[str],
        result_extension: str | tuple[str, ...],
        result_directory: StrPath,
        config_settings: _ConfigSettings,
        arbitrary_args: Iterable[str] = (),
    ):
        result_directory = os.path.abspath(result_directory)

        # Build in a temporary directory, then copy to the target.
        os.makedirs(result_directory, exist_ok=True)

        with tempfile.TemporaryDirectory(
            prefix=".tmp-", dir=result_directory
        ) as tmp_dist_dir:
            sys.argv = [
                *sys.argv[:1],
                *self._global_args(config_settings),
                *setup_command,
                "--dist-dir",
                tmp_dist_dir,
                *arbitrary_args,
            ]
            with no_install_setup_requires():
                self.run_setup()

            result_basename = _file_with_extension(tmp_dist_dir, result_extension)
            result_path = os.path.join(result_directory, result_basename)
            if os.path.exists(result_path):
                # os.rename will fail overwriting on non-Unix.
                os.remove(result_path)
            os.rename(os.path.join(tmp_dist_dir, result_basename), result_path)

        return result_basename

    def build_wheel(
        self,
        wheel_directory: StrPath,
        config_settings: _ConfigSettings = None,
        metadata_directory: StrPath | None = None,
    ):
        def _build(cmd: list[str]):
            with suppress_known_deprecation():
                return self._build_with_temp_dir(
                    cmd,
                    '.whl',
                    wheel_directory,
                    config_settings,
                    self._arbitrary_args(config_settings),
                )

        if metadata_directory is None:
            return _build(['bdist_wheel'])

        try:
            return _build(['bdist_wheel', '--dist-info-dir', str(metadata_directory)])
        except SystemExit as ex:  # pragma: nocover
            # pypa/setuptools#4683
            if "--dist-info-dir not recognized" not in str(ex):
                raise
            _IncompatibleBdistWheel.emit()
            return _build(['bdist_wheel'])

    def build_sdist(
        self, sdist_directory: StrPath, config_settings: _ConfigSettings = None
    ):
        return self._build_with_temp_dir(
            ['sdist', '--formats', 'gztar'], '.tar.gz', sdist_directory, config_settings
        )

    def _get_dist_info_dir(self, metadata_directory: StrPath | None) -> str | None:
        if not metadata_directory:
            return None
        dist_info_candidates = list(Path(metadata_directory).glob("*.dist-info"))
        assert len(dist_info_candidates) <= 1
        return str(dist_info_candidates[0]) if dist_info_candidates else None

    def build_editable(
        self,
        wheel_directory: StrPath,
        config_settings: _ConfigSettings = None,
        metadata_directory: StrPath | None = None,
    ):
        # XXX can or should we hide our editable_wheel command normally?
        info_dir = self._get_dist_info_dir(metadata_directory)
        opts = ["--dist-info-dir", info_dir] if info_dir else []
        cmd = ["editable_wheel", *opts, *self._editable_args(config_settings)]
        with suppress_known_deprecation():
            return self._build_with_temp_dir(
                cmd, ".whl", wheel_directory, config_settings
            )

    def get_requires_for_build_editable(self, config_settings: _ConfigSettings = None):
        return self.get_requires_for_build_wheel(config_settings)

    def prepare_metadata_for_build_editable(
        self, metadata_directory: StrPath, config_settings: _ConfigSettings = None
    ):
        return self.prepare_metadata_for_build_wheel(
            metadata_directory, config_settings
        )


class _BuildMetaLegacyBackend(_BuildMetaBackend):
    """Compatibility backend for setuptools

    This is a version of setuptools.build_meta that endeavors
    to maintain backwards
    compatibility with pre-PEP 517 modes of invocation. It
    exists as a temporary
    bridge between the old packaging mechanism and the new
    packaging mechanism,
    and will eventually be removed.
    """

    def run_setup(self, setup_script: str = 'setup.py'):
        # In order to maintain compatibility with scripts assuming that
        # the setup.py script is in a directory on the PYTHONPATH, inject
        # '' into sys.path. (pypa/setuptools#1642)
        sys_path = list(sys.path)  # Save the original path

        script_dir = os.path.dirname(os.path.abspath(setup_script))
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)

        # Some setup.py scripts (e.g. in pygame and numpy) use sys.argv[0] to
        # get the directory of the source code. They expect it to refer to the
        # setup.py script.
        sys_argv_0 = sys.argv[0]
        sys.argv[0] = setup_script

        try:
            super().run_setup(setup_script=setup_script)
        finally:
            # While PEP 517 frontends should be calling each hook in a fresh
            # subprocess according to the standard (and thus it should not be
            # strictly necessary to restore the old sys.path), we'll restore
            # the original path so that the path manipulation does not persist
            # within the hook after run_setup is called.
            sys.path[:] = sys_path
            sys.argv[0] = sys_argv_0


class _IncompatibleBdistWheel(SetuptoolsDeprecationWarning):
    _SUMMARY = "wheel.bdist_wheel is deprecated, please import it from setuptools"
    _DETAILS = """
    Ensure that any custom bdist_wheel implementation is a subclass of
    setuptools.command.bdist_wheel.bdist_wheel.
    """
    _DUE_DATE = (2025, 10, 15)
    # Initially introduced in 2024/10/15, but maybe too disruptive to be enforced?
    _SEE_URL = "https://github.com/pypa/wheel/pull/631"


# The primary backend
_BACKEND = _BuildMetaBackend()

get_requires_for_build_wheel = _BACKEND.get_requires_for_build_wheel
get_requires_for_build_sdist = _BACKEND.get_requires_for_build_sdist
prepare_metadata_for_build_wheel = _BACKEND.prepare_metadata_for_build_wheel
build_wheel = _BACKEND.build_wheel
build_sdist = _BACKEND.build_sdist
get_requires_for_build_editable = _BACKEND.get_requires_for_build_editable
prepare_metadata_for_build_editable = _BACKEND.prepare_metadata_for_build_editable
build_editable = _BACKEND.build_editable


# The legacy backend
__legacy__ = _BuildMetaLegacyBackend()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\resolvelib\resolvers.py ===
import collections
import itertools
import operator

from .providers import AbstractResolver
from .structs import DirectedGraph, IteratorMapping, build_iter_view

RequirementInformation = collections.namedtuple(
    "RequirementInformation", ["requirement", "parent"]
)


class ResolverException(Exception):
    """A base class for all exceptions raised by this module.

    Exceptions derived by this class should all be handled in this module. Any
    bubbling pass the resolver should be treated as a bug.
    """


class RequirementsConflicted(ResolverException):
    def __init__(self, criterion):
        super(RequirementsConflicted, self).__init__(criterion)
        self.criterion = criterion

    def __str__(self):
        return "Requirements conflict: {}".format(
            ", ".join(repr(r) for r in self.criterion.iter_requirement()),
        )


class InconsistentCandidate(ResolverException):
    def __init__(self, candidate, criterion):
        super(InconsistentCandidate, self).__init__(candidate, criterion)
        self.candidate = candidate
        self.criterion = criterion

    def __str__(self):
        return "Provided candidate {!r} does not satisfy {}".format(
            self.candidate,
            ", ".join(repr(r) for r in self.criterion.iter_requirement()),
        )


class Criterion(object):
    """Representation of possible resolution results of a package.

    This holds three attributes:

    * `information` is a collection of `RequirementInformation` pairs.
      Each pair is a requirement contributing to this criterion, and the
      candidate that provides the requirement.
    * `incompatibilities` is a collection of all known not-to-work candidates
      to exclude from consideration.
    * `candidates` is a collection containing all possible candidates deducted
      from the union of contributing requirements and known incompatibilities.
      It should never be empty, except when the criterion is an attribute of a
      raised `RequirementsConflicted` (in which case it is always empty).

    .. note::
        This class is intended to be externally immutable. **Do not** mutate
        any of its attribute containers.
    """

    def __init__(self, candidates, information, incompatibilities):
        self.candidates = candidates
        self.information = information
        self.incompatibilities = incompatibilities

    def __repr__(self):
        requirements = ", ".join(
            "({!r}, via={!r})".format(req, parent)
            for req, parent in self.information
        )
        return "Criterion({})".format(requirements)

    def iter_requirement(self):
        return (i.requirement for i in self.information)

    def iter_parent(self):
        return (i.parent for i in self.information)


class ResolutionError(ResolverException):
    pass


class ResolutionImpossible(ResolutionError):
    def __init__(self, causes):
        super(ResolutionImpossible, self).__init__(causes)
        # causes is a list of RequirementInformation objects
        self.causes = causes


class ResolutionTooDeep(ResolutionError):
    def __init__(self, round_count):
        super(ResolutionTooDeep, self).__init__(round_count)
        self.round_count = round_count


# Resolution state in a round.
State = collections.namedtuple("State", "mapping criteria backtrack_causes")


class Resolution(object):
    """Stateful resolution object.

    This is designed as a one-off object that holds information to kick start
    the resolution process, and holds the results afterwards.
    """

    def __init__(self, provider, reporter):
        self._p = provider
        self._r = reporter
        self._states = []

    @property
    def state(self):
        try:
            return self._states[-1]
        except IndexError:
            raise AttributeError("state")

    def _push_new_state(self):
        """Push a new state into history.

        This new state will be used to hold resolution results of the next
        coming round.
        """
        base = self._states[-1]
        state = State(
            mapping=base.mapping.copy(),
            criteria=base.criteria.copy(),
            backtrack_causes=base.backtrack_causes[:],
        )
        self._states.append(state)

    def _add_to_criteria(self, criteria, requirement, parent):
        self._r.adding_requirement(requirement=requirement, parent=parent)

        identifier = self._p.identify(requirement_or_candidate=requirement)
        criterion = criteria.get(identifier)
        if criterion:
            incompatibilities = list(criterion.incompatibilities)
        else:
            incompatibilities = []

        matches = self._p.find_matches(
            identifier=identifier,
            requirements=IteratorMapping(
                criteria,
                operator.methodcaller("iter_requirement"),
                {identifier: [requirement]},
            ),
            incompatibilities=IteratorMapping(
                criteria,
                operator.attrgetter("incompatibilities"),
                {identifier: incompatibilities},
            ),
        )

        if criterion:
            information = list(criterion.information)
            information.append(RequirementInformation(requirement, parent))
        else:
            information = [RequirementInformation(requirement, parent)]

        criterion = Criterion(
            candidates=build_iter_view(matches),
            information=information,
            incompatibilities=incompatibilities,
        )
        if not criterion.candidates:
            raise RequirementsConflicted(criterion)
        criteria[identifier] = criterion

    def _remove_information_from_criteria(self, criteria, parents):
        """Remove information from parents of criteria.

        Concretely, removes all values from each criterion's ``information``
        field that have one of ``parents`` as provider of the requirement.

        :param criteria: The criteria to update.
        :param parents: Identifiers for which to remove information from all criteria.
        """
        if not parents:
            return
        for key, criterion in criteria.items():
            criteria[key] = Criterion(
                criterion.candidates,
                [
                    information
                    for information in criterion.information
                    if (
                        information.parent is None
                        or self._p.identify(information.parent) not in parents
                    )
                ],
                criterion.incompatibilities,
            )

    def _get_preference(self, name):
        return self._p.get_preference(
            identifier=name,
            resolutions=self.state.mapping,
            candidates=IteratorMapping(
                self.state.criteria,
                operator.attrgetter("candidates"),
            ),
            information=IteratorMapping(
                self.state.criteria,
                operator.attrgetter("information"),
            ),
            backtrack_causes=self.state.backtrack_causes,
        )

    def _is_current_pin_satisfying(self, name, criterion):
        try:
            current_pin = self.state.mapping[name]
        except KeyError:
            return False
        return all(
            self._p.is_satisfied_by(requirement=r, candidate=current_pin)
            for r in criterion.iter_requirement()
        )

    def _get_updated_criteria(self, candidate):
        criteria = self.state.criteria.copy()
        for requirement in self._p.get_dependencies(candidate=candidate):
            self._add_to_criteria(criteria, requirement, parent=candidate)
        return criteria

    def _attempt_to_pin_criterion(self, name):
        criterion = self.state.criteria[name]

        causes = []
        for candidate in criterion.candidates:
            try:
                criteria = self._get_updated_criteria(candidate)
            except RequirementsConflicted as e:
                self._r.rejecting_candidate(e.criterion, candidate)
                causes.append(e.criterion)
                continue

            # Check the newly-pinned candidate actually works. This should
            # always pass under normal circumstances, but in the case of a
            # faulty provider, we will raise an error to notify the implementer
            # to fix find_matches() and/or is_satisfied_by().
            satisfied = all(
                self._p.is_satisfied_by(requirement=r, candidate=candidate)
                for r in criterion.iter_requirement()
            )
            if not satisfied:
                raise InconsistentCandidate(candidate, criterion)

            self._r.pinning(candidate=candidate)
            self.state.criteria.update(criteria)

            # Put newly-pinned candidate at the end. This is essential because
            # backtracking looks at this mapping to get the last pin.
            self.state.mapping.pop(name, None)
            self.state.mapping[name] = candidate

            return []

        # All candidates tried, nothing works. This criterion is a dead
        # end, signal for backtracking.
        return causes

    def _backjump(self, causes):
        """Perform backjumping.

        When we enter here, the stack is like this::

            [ state Z ]
            [ state Y ]
            [ state X ]
            .... earlier states are irrelevant.

        1. No pins worked for Z, so it does not have a pin.
        2. We want to reset state Y to unpinned, and pin another candidate.
        3. State X holds what state Y was before the pin, but does not
           have the incompatibility information gathered in state Y.

        Each iteration of the loop will:

        1.  Identify Z. The incompatibility is not always caused by the latest
            state. For example, given three requirements A, B and C, with
            dependencies A1, B1 and C1, where A1 and B1 are incompatible: the
            last state might be related to C, so we want to discard the
            previous state.
        2.  Discard Z.
        3.  Discard Y but remember its incompatibility information gathered
            previously, and the failure we're dealing with right now.
        4.  Push a new state Y' based on X, and apply the incompatibility
            information from Y to Y'.
        5a. If this causes Y' to conflict, we need to backtrack again. Make Y'
            the new Z and go back to step 2.
        5b. If the incompatibilities apply cleanly, end backtracking.
        """
        incompatible_reqs = itertools.chain(
            (c.parent for c in causes if c.parent is not None),
            (c.requirement for c in causes),
        )
        incompatible_deps = {self._p.identify(r) for r in incompatible_reqs}
        while len(self._states) >= 3:
            # Remove the state that triggered backtracking.
            del self._states[-1]

            # Ensure to backtrack to a state that caused the incompatibility
            incompatible_state = False
            while not incompatible_state:
                # Retrieve the last candidate pin and known incompatibilities.
                try:
                    broken_state = self._states.pop()
                    name, candidate = broken_state.mapping.popitem()
                except (IndexError, KeyError):
                    raise ResolutionImpossible(causes)
                current_dependencies = {
                    self._p.identify(d)
                    for d in self._p.get_dependencies(candidate)
                }
                incompatible_state = not current_dependencies.isdisjoint(
                    incompatible_deps
                )

            incompatibilities_from_broken = [
                (k, list(v.incompatibilities))
                for k, v in broken_state.criteria.items()
            ]

            # Also mark the newly known incompatibility.
            incompatibilities_from_broken.append((name, [candidate]))

            # Create a new state from the last known-to-work one, and apply
            # the previously gathered incompatibility information.
            def _patch_criteria():
                for k, incompatibilities in incompatibilities_from_broken:
                    if not incompatibilities:
                        continue
                    try:
                        criterion = self.state.criteria[k]
                    except KeyError:
                        continue
                    matches = self._p.find_matches(
                        identifier=k,
                        requirements=IteratorMapping(
                            self.state.criteria,
                            operator.methodcaller("iter_requirement"),
                        ),
                        incompatibilities=IteratorMapping(
                            self.state.criteria,
                            operator.attrgetter("incompatibilities"),
                            {k: incompatibilities},
                        ),
                    )
                    candidates = build_iter_view(matches)
                    if not candidates:
                        return False
                    incompatibilities.extend(criterion.incompatibilities)
                    self.state.criteria[k] = Criterion(
                        candidates=candidates,
                        information=list(criterion.information),
                        incompatibilities=incompatibilities,
                    )
                return True

            self._push_new_state()
            success = _patch_criteria()

            # It works! Let's work on this new state.
            if success:
                return True

            # State does not work after applying known incompatibilities.
            # Try the still previous state.

        # No way to backtrack anymore.
        return False

    def resolve(self, requirements, max_rounds):
        if self._states:
            raise RuntimeError("already resolved")

        self._r.starting()

        # Initialize the root state.
        self._states = [
            State(
                mapping=collections.OrderedDict(),
                criteria={},
                backtrack_causes=[],
            )
        ]
        for r in requirements:
            try:
                self._add_to_criteria(self.state.criteria, r, parent=None)
            except RequirementsConflicted as e:
                raise ResolutionImpossible(e.criterion.information)

        # The root state is saved as a sentinel so the first ever pin can have
        # something to backtrack to if it fails. The root state is basically
        # pinning the virtual "root" package in the graph.
        self._push_new_state()

        for round_index in range(max_rounds):
            self._r.starting_round(index=round_index)

            unsatisfied_names = [
                key
                for key, criterion in self.state.criteria.items()
                if not self._is_current_pin_satisfying(key, criterion)
            ]

            # All criteria are accounted for. Nothing more to pin, we are done!
            if not unsatisfied_names:
                self._r.ending(state=self.state)
                return self.state

            # keep track of satisfied names to calculate diff after pinning
            satisfied_names = set(self.state.criteria.keys()) - set(
                unsatisfied_names
            )

            # Choose the most preferred unpinned criterion to try.
            name = min(unsatisfied_names, key=self._get_preference)
            failure_causes = self._attempt_to_pin_criterion(name)

            if failure_causes:
                causes = [i for c in failure_causes for i in c.information]
                # Backjump if pinning fails. The backjump process puts us in
                # an unpinned state, so we can work on it in the next round.
                self._r.resolving_conflicts(causes=causes)
                success = self._backjump(causes)
                self.state.backtrack_causes[:] = causes

                # Dead ends everywhere. Give up.
                if not success:
                    raise ResolutionImpossible(self.state.backtrack_causes)
            else:
                # discard as information sources any invalidated names
                # (unsatisfied names that were previously satisfied)
                newly_unsatisfied_names = {
                    key
                    for key, criterion in self.state.criteria.items()
                    if key in satisfied_names
                    and not self._is_current_pin_satisfying(key, criterion)
                }
                self._remove_information_from_criteria(
                    self.state.criteria, newly_unsatisfied_names
                )
                # Pinning was successful. Push a new state to do another pin.
                self._push_new_state()

            self._r.ending_round(index=round_index, state=self.state)

        raise ResolutionTooDeep(max_rounds)


def _has_route_to_root(criteria, key, all_keys, connected):
    if key in connected:
        return True
    if key not in criteria:
        return False
    for p in criteria[key].iter_parent():
        try:
            pkey = all_keys[id(p)]
        except KeyError:
            continue
        if pkey in connected:
            connected.add(key)
            return True
        if _has_route_to_root(criteria, pkey, all_keys, connected):
            connected.add(key)
            return True
    return False


Result = collections.namedtuple("Result", "mapping graph criteria")


def _build_result(state):
    mapping = state.mapping
    all_keys = {id(v): k for k, v in mapping.items()}
    all_keys[id(None)] = None

    graph = DirectedGraph()
    graph.add(None)  # Sentinel as root dependencies' parent.

    connected = {None}
    for key, criterion in state.criteria.items():
        if not _has_route_to_root(state.criteria, key, all_keys, connected):
            continue
        if key not in graph:
            graph.add(key)
        for p in criterion.iter_parent():
            try:
                pkey = all_keys[id(p)]
            except KeyError:
                continue
            if pkey not in graph:
                graph.add(pkey)
            graph.connect(pkey, key)

    return Result(
        mapping={k: v for k, v in mapping.items() if k in connected},
        graph=graph,
        criteria=state.criteria,
    )


class Resolver(AbstractResolver):
    """The thing that performs the actual resolution work."""

    base_exception = ResolverException

    def resolve(self, requirements, max_rounds=100):
        """Take a collection of constraints, spit out the resolution result.

        The return value is a representation to the final resolution result. It
        is a tuple subclass with three public members:

        * `mapping`: A dict of resolved candidates. Each key is an identifier
            of a requirement (as returned by the provider's `identify` method),
            and the value is the resolved candidate.
        * `graph`: A `DirectedGraph` instance representing the dependency tree.
            The vertices are keys of `mapping`, and each edge represents *why*
            a particular package is included. A special vertex `None` is
            included to represent parents of user-supplied requirements.
        * `criteria`: A dict of "criteria" that hold detailed information on
            how edges in the graph are derived. Each key is an identifier of a
            requirement, and the value is a `Criterion` instance.

        The following exceptions may be raised if a resolution cannot be found:

        * `ResolutionImpossible`: A resolution cannot be found for the given
            combination of requirements. The `causes` attribute of the
            exception is a list of (requirement, parent), giving the
            requirements that could not be satisfied.
        * `ResolutionTooDeep`: The dependency tree is too deeply nested and
            the resolver gave up. This is usually caused by a circular
            dependency, but you can try to resolve this by increasing the
            `max_rounds` argument.
        """
        resolution = Resolution(self.provider, self.reporter)
        state = resolution.resolve(requirements, max_rounds=max_rounds)
        return _build_result(state)

# === NexusCore/openenv\Lib\site-packages\matplotlib\_layoutgrid.py ===
"""
A layoutgrid is a nrows by ncols set of boxes, meant to be used by
`._constrained_layout`, each box is analogous to a subplotspec element of
a gridspec.

Each box is defined by left[ncols], right[ncols], bottom[nrows] and top[nrows],
and by two editable margins for each side.  The main margin gets its value
set by the size of ticklabels, titles, etc on each Axes that is in the figure.
The outer margin is the padding around the Axes, and space for any
colorbars.

The "inner" widths and heights of these boxes are then constrained to be the
same (relative the values of `width_ratios[ncols]` and `height_ratios[nrows]`).

The layoutgrid is then constrained to be contained within a parent layoutgrid,
its column(s) and row(s) specified when it is created.
"""

import itertools
import kiwisolver as kiwi
import logging
import numpy as np

import matplotlib as mpl
import matplotlib.patches as mpatches
from matplotlib.transforms import Bbox

_log = logging.getLogger(__name__)


class LayoutGrid:
    """
    Analogous to a gridspec, and contained in another LayoutGrid.
    """

    def __init__(self, parent=None, parent_pos=(0, 0),
                 parent_inner=False, name='', ncols=1, nrows=1,
                 h_pad=None, w_pad=None, width_ratios=None,
                 height_ratios=None):
        Variable = kiwi.Variable
        self.parent_pos = parent_pos
        self.parent_inner = parent_inner
        self.name = name + seq_id()
        if isinstance(parent, LayoutGrid):
            self.name = f'{parent.name}.{self.name}'
        self.nrows = nrows
        self.ncols = ncols
        self.height_ratios = np.atleast_1d(height_ratios)
        if height_ratios is None:
            self.height_ratios = np.ones(nrows)
        self.width_ratios = np.atleast_1d(width_ratios)
        if width_ratios is None:
            self.width_ratios = np.ones(ncols)

        sn = self.name + '_'
        if not isinstance(parent, LayoutGrid):
            # parent can be a rect if not a LayoutGrid
            # allows specifying a rectangle to contain the layout.
            self.solver = kiwi.Solver()
        else:
            parent.add_child(self, *parent_pos)
            self.solver = parent.solver
        # keep track of artist associated w/ this layout.  Can be none
        self.artists = np.empty((nrows, ncols), dtype=object)
        self.children = np.empty((nrows, ncols), dtype=object)

        self.margins = {}
        self.margin_vals = {}
        # all the boxes in each column share the same left/right margins:
        for todo in ['left', 'right', 'leftcb', 'rightcb']:
            # track the value so we can change only if a margin is larger
            # than the current value
            self.margin_vals[todo] = np.zeros(ncols)

        sol = self.solver

        self.lefts = [Variable(f'{sn}lefts[{i}]') for i in range(ncols)]
        self.rights = [Variable(f'{sn}rights[{i}]') for i in range(ncols)]
        for todo in ['left', 'right', 'leftcb', 'rightcb']:
            self.margins[todo] = [Variable(f'{sn}margins[{todo}][{i}]')
                                  for i in range(ncols)]
            for i in range(ncols):
                sol.addEditVariable(self.margins[todo][i], 'strong')

        for todo in ['bottom', 'top', 'bottomcb', 'topcb']:
            self.margins[todo] = np.empty((nrows), dtype=object)
            self.margin_vals[todo] = np.zeros(nrows)

        self.bottoms = [Variable(f'{sn}bottoms[{i}]') for i in range(nrows)]
        self.tops = [Variable(f'{sn}tops[{i}]') for i in range(nrows)]
        for todo in ['bottom', 'top', 'bottomcb', 'topcb']:
            self.margins[todo] = [Variable(f'{sn}margins[{todo}][{i}]')
                                  for i in range(nrows)]
            for i in range(nrows):
                sol.addEditVariable(self.margins[todo][i], 'strong')

        # set these margins to zero by default. They will be edited as
        # children are filled.
        self.reset_margins()
        self.add_constraints(parent)

        self.h_pad = h_pad
        self.w_pad = w_pad

    def __repr__(self):
        str = f'LayoutBox: {self.name:25s} {self.nrows}x{self.ncols},\n'
        for i in range(self.nrows):
            for j in range(self.ncols):
                str += f'{i}, {j}: '\
                       f'L{self.lefts[j].value():1.3f}, ' \
                       f'B{self.bottoms[i].value():1.3f}, ' \
                       f'R{self.rights[j].value():1.3f}, ' \
                       f'T{self.tops[i].value():1.3f}, ' \
                       f'ML{self.margins["left"][j].value():1.3f}, ' \
                       f'MR{self.margins["right"][j].value():1.3f}, ' \
                       f'MB{self.margins["bottom"][i].value():1.3f}, ' \
                       f'MT{self.margins["top"][i].value():1.3f}, \n'
        return str

    def reset_margins(self):
        """
        Reset all the margins to zero.  Must do this after changing
        figure size, for instance, because the relative size of the
        axes labels etc changes.
        """
        for todo in ['left', 'right', 'bottom', 'top',
                     'leftcb', 'rightcb', 'bottomcb', 'topcb']:
            self.edit_margins(todo, 0.0)

    def add_constraints(self, parent):
        # define self-consistent constraints
        self.hard_constraints()
        # define relationship with parent layoutgrid:
        self.parent_constraints(parent)
        # define relative widths of the grid cells to each other
        # and stack horizontally and vertically.
        self.grid_constraints()

    def hard_constraints(self):
        """
        These are the redundant constraints, plus ones that make the
        rest of the code easier.
        """
        for i in range(self.ncols):
            hc = [self.rights[i] >= self.lefts[i],
                  (self.rights[i] - self.margins['right'][i] -
                    self.margins['rightcb'][i] >=
                    self.lefts[i] - self.margins['left'][i] -
                    self.margins['leftcb'][i])
                  ]
            for c in hc:
                self.solver.addConstraint(c | 'required')

        for i in range(self.nrows):
            hc = [self.tops[i] >= self.bottoms[i],
                  (self.tops[i] - self.margins['top'][i] -
                    self.margins['topcb'][i] >=
                    self.bottoms[i] - self.margins['bottom'][i] -
                    self.margins['bottomcb'][i])
                  ]
            for c in hc:
                self.solver.addConstraint(c | 'required')

    def add_child(self, child, i=0, j=0):
        # np.ix_ returns the cross product of i and j indices
        self.children[np.ix_(np.atleast_1d(i), np.atleast_1d(j))] = child

    def parent_constraints(self, parent):
        # constraints that are due to the parent...
        # i.e. the first column's left is equal to the
        # parent's left, the last column right equal to the
        # parent's right...
        if not isinstance(parent, LayoutGrid):
            # specify a rectangle in figure coordinates
            hc = [self.lefts[0] == parent[0],
                  self.rights[-1] == parent[0] + parent[2],
                  # top and bottom reversed order...
                  self.tops[0] == parent[1] + parent[3],
                  self.bottoms[-1] == parent[1]]
        else:
            rows, cols = self.parent_pos
            rows = np.atleast_1d(rows)
            cols = np.atleast_1d(cols)

            left = parent.lefts[cols[0]]
            right = parent.rights[cols[-1]]
            top = parent.tops[rows[0]]
            bottom = parent.bottoms[rows[-1]]
            if self.parent_inner:
                # the layout grid is contained inside the inner
                # grid of the parent.
                left += parent.margins['left'][cols[0]]
                left += parent.margins['leftcb'][cols[0]]
                right -= parent.margins['right'][cols[-1]]
                right -= parent.margins['rightcb'][cols[-1]]
                top -= parent.margins['top'][rows[0]]
                top -= parent.margins['topcb'][rows[0]]
                bottom += parent.margins['bottom'][rows[-1]]
                bottom += parent.margins['bottomcb'][rows[-1]]
            hc = [self.lefts[0] == left,
                  self.rights[-1] == right,
                  # from top to bottom
                  self.tops[0] == top,
                  self.bottoms[-1] == bottom]
        for c in hc:
            self.solver.addConstraint(c | 'required')

    def grid_constraints(self):
        # constrain the ratio of the inner part of the grids
        # to be the same (relative to width_ratios)

        # constrain widths:
        w = (self.rights[0] - self.margins['right'][0] -
             self.margins['rightcb'][0])
        w = (w - self.lefts[0] - self.margins['left'][0] -
             self.margins['leftcb'][0])
        w0 = w / self.width_ratios[0]
        # from left to right
        for i in range(1, self.ncols):
            w = (self.rights[i] - self.margins['right'][i] -
                 self.margins['rightcb'][i])
            w = (w - self.lefts[i] - self.margins['left'][i] -
                 self.margins['leftcb'][i])
            c = (w == w0 * self.width_ratios[i])
            self.solver.addConstraint(c | 'strong')
            # constrain the grid cells to be directly next to each other.
            c = (self.rights[i - 1] == self.lefts[i])
            self.solver.addConstraint(c | 'strong')

        # constrain heights:
        h = self.tops[0] - self.margins['top'][0] - self.margins['topcb'][0]
        h = (h - self.bottoms[0] - self.margins['bottom'][0] -
             self.margins['bottomcb'][0])
        h0 = h / self.height_ratios[0]
        # from top to bottom:
        for i in range(1, self.nrows):
            h = (self.tops[i] - self.margins['top'][i] -
                 self.margins['topcb'][i])
            h = (h - self.bottoms[i] - self.margins['bottom'][i] -
                 self.margins['bottomcb'][i])
            c = (h == h0 * self.height_ratios[i])
            self.solver.addConstraint(c | 'strong')
            # constrain the grid cells to be directly above each other.
            c = (self.bottoms[i - 1] == self.tops[i])
            self.solver.addConstraint(c | 'strong')

    # Margin editing:  The margins are variable and meant to
    # contain things of a fixed size like axes labels, tick labels, titles
    # etc
    def edit_margin(self, todo, size, cell):
        """
        Change the size of the margin for one cell.

        Parameters
        ----------
        todo : string (one of 'left', 'right', 'bottom', 'top')
            margin to alter.

        size : float
            Size of the margin.  If it is larger than the existing minimum it
            updates the margin size. Fraction of figure size.

        cell : int
            Cell column or row to edit.
        """
        self.solver.suggestValue(self.margins[todo][cell], size)
        self.margin_vals[todo][cell] = size

    def edit_margin_min(self, todo, size, cell=0):
        """
        Change the minimum size of the margin for one cell.

        Parameters
        ----------
        todo : string (one of 'left', 'right', 'bottom', 'top')
            margin to alter.

        size : float
            Minimum size of the margin .  If it is larger than the
            existing minimum it updates the margin size. Fraction of
            figure size.

        cell : int
            Cell column or row to edit.
        """

        if size > self.margin_vals[todo][cell]:
            self.edit_margin(todo, size, cell)

    def edit_margins(self, todo, size):
        """
        Change the size of all the margin of all the cells in the layout grid.

        Parameters
        ----------
        todo : string (one of 'left', 'right', 'bottom', 'top')
            margin to alter.

        size : float
            Size to set the margins.  Fraction of figure size.
        """

        for i in range(len(self.margin_vals[todo])):
            self.edit_margin(todo, size, i)

    def edit_all_margins_min(self, todo, size):
        """
        Change the minimum size of all the margin of all
        the cells in the layout grid.

        Parameters
        ----------
        todo : {'left', 'right', 'bottom', 'top'}
            The margin to alter.

        size : float
            Minimum size of the margin.  If it is larger than the
            existing minimum it updates the margin size. Fraction of
            figure size.
        """

        for i in range(len(self.margin_vals[todo])):
            self.edit_margin_min(todo, size, i)

    def edit_outer_margin_mins(self, margin, ss):
        """
        Edit all four margin minimums in one statement.

        Parameters
        ----------
        margin : dict
            size of margins in a dict with keys 'left', 'right', 'bottom',
            'top'

        ss : SubplotSpec
            defines the subplotspec these margins should be applied to
        """

        self.edit_margin_min('left', margin['left'], ss.colspan.start)
        self.edit_margin_min('leftcb', margin['leftcb'], ss.colspan.start)
        self.edit_margin_min('right', margin['right'], ss.colspan.stop - 1)
        self.edit_margin_min('rightcb', margin['rightcb'], ss.colspan.stop - 1)
        # rows are from the top down:
        self.edit_margin_min('top', margin['top'], ss.rowspan.start)
        self.edit_margin_min('topcb', margin['topcb'], ss.rowspan.start)
        self.edit_margin_min('bottom', margin['bottom'], ss.rowspan.stop - 1)
        self.edit_margin_min('bottomcb', margin['bottomcb'],
                             ss.rowspan.stop - 1)

    def get_margins(self, todo, col):
        """Return the margin at this position"""
        return self.margin_vals[todo][col]

    def get_outer_bbox(self, rows=0, cols=0):
        """
        Return the outer bounding box of the subplot specs
        given by rows and cols.  rows and cols can be spans.
        """
        rows = np.atleast_1d(rows)
        cols = np.atleast_1d(cols)

        bbox = Bbox.from_extents(
            self.lefts[cols[0]].value(),
            self.bottoms[rows[-1]].value(),
            self.rights[cols[-1]].value(),
            self.tops[rows[0]].value())
        return bbox

    def get_inner_bbox(self, rows=0, cols=0):
        """
        Return the inner bounding box of the subplot specs
        given by rows and cols.  rows and cols can be spans.
        """
        rows = np.atleast_1d(rows)
        cols = np.atleast_1d(cols)

        bbox = Bbox.from_extents(
            (self.lefts[cols[0]].value() +
                self.margins['left'][cols[0]].value() +
                self.margins['leftcb'][cols[0]].value()),
            (self.bottoms[rows[-1]].value() +
                self.margins['bottom'][rows[-1]].value() +
                self.margins['bottomcb'][rows[-1]].value()),
            (self.rights[cols[-1]].value() -
                self.margins['right'][cols[-1]].value() -
                self.margins['rightcb'][cols[-1]].value()),
            (self.tops[rows[0]].value() -
                self.margins['top'][rows[0]].value() -
                self.margins['topcb'][rows[0]].value())
        )
        return bbox

    def get_bbox_for_cb(self, rows=0, cols=0):
        """
        Return the bounding box that includes the
        decorations but, *not* the colorbar...
        """
        rows = np.atleast_1d(rows)
        cols = np.atleast_1d(cols)

        bbox = Bbox.from_extents(
            (self.lefts[cols[0]].value() +
                self.margins['leftcb'][cols[0]].value()),
            (self.bottoms[rows[-1]].value() +
                self.margins['bottomcb'][rows[-1]].value()),
            (self.rights[cols[-1]].value() -
                self.margins['rightcb'][cols[-1]].value()),
            (self.tops[rows[0]].value() -
                self.margins['topcb'][rows[0]].value())
        )
        return bbox

    def get_left_margin_bbox(self, rows=0, cols=0):
        """
        Return the left margin bounding box of the subplot specs
        given by rows and cols.  rows and cols can be spans.
        """
        rows = np.atleast_1d(rows)
        cols = np.atleast_1d(cols)

        bbox = Bbox.from_extents(
            (self.lefts[cols[0]].value() +
                self.margins['leftcb'][cols[0]].value()),
            (self.bottoms[rows[-1]].value()),
            (self.lefts[cols[0]].value() +
                self.margins['leftcb'][cols[0]].value() +
                self.margins['left'][cols[0]].value()),
            (self.tops[rows[0]].value()))
        return bbox

    def get_bottom_margin_bbox(self, rows=0, cols=0):
        """
        Return the left margin bounding box of the subplot specs
        given by rows and cols.  rows and cols can be spans.
        """
        rows = np.atleast_1d(rows)
        cols = np.atleast_1d(cols)

        bbox = Bbox.from_extents(
            (self.lefts[cols[0]].value()),
            (self.bottoms[rows[-1]].value() +
             self.margins['bottomcb'][rows[-1]].value()),
            (self.rights[cols[-1]].value()),
            (self.bottoms[rows[-1]].value() +
                self.margins['bottom'][rows[-1]].value() +
             self.margins['bottomcb'][rows[-1]].value()
             ))
        return bbox

    def get_right_margin_bbox(self, rows=0, cols=0):
        """
        Return the left margin bounding box of the subplot specs
        given by rows and cols.  rows and cols can be spans.
        """
        rows = np.atleast_1d(rows)
        cols = np.atleast_1d(cols)

        bbox = Bbox.from_extents(
            (self.rights[cols[-1]].value() -
                self.margins['right'][cols[-1]].value() -
                self.margins['rightcb'][cols[-1]].value()),
            (self.bottoms[rows[-1]].value()),
            (self.rights[cols[-1]].value() -
                self.margins['rightcb'][cols[-1]].value()),
            (self.tops[rows[0]].value()))
        return bbox

    def get_top_margin_bbox(self, rows=0, cols=0):
        """
        Return the left margin bounding box of the subplot specs
        given by rows and cols.  rows and cols can be spans.
        """
        rows = np.atleast_1d(rows)
        cols = np.atleast_1d(cols)

        bbox = Bbox.from_extents(
            (self.lefts[cols[0]].value()),
            (self.tops[rows[0]].value() -
                self.margins['topcb'][rows[0]].value()),
            (self.rights[cols[-1]].value()),
            (self.tops[rows[0]].value() -
                self.margins['topcb'][rows[0]].value() -
                self.margins['top'][rows[0]].value()))
        return bbox

    def update_variables(self):
        """
        Update the variables for the solver attached to this layoutgrid.
        """
        self.solver.updateVariables()

_layoutboxobjnum = itertools.count()


def seq_id():
    """Generate a short sequential id for layoutbox objects."""
    return '%06d' % next(_layoutboxobjnum)


def plot_children(fig, lg=None, level=0):
    """Simple plotting to show where boxes are."""
    if lg is None:
        _layoutgrids = fig.get_layout_engine().execute(fig)
        lg = _layoutgrids[fig]
    colors = mpl.rcParams["axes.prop_cycle"].by_key()["color"]
    col = colors[level]
    for i in range(lg.nrows):
        for j in range(lg.ncols):
            bb = lg.get_outer_bbox(rows=i, cols=j)
            fig.add_artist(
                mpatches.Rectangle(bb.p0, bb.width, bb.height, linewidth=1,
                                   edgecolor='0.7', facecolor='0.7',
                                   alpha=0.2, transform=fig.transFigure,
                                   zorder=-3))
            bbi = lg.get_inner_bbox(rows=i, cols=j)
            fig.add_artist(
                mpatches.Rectangle(bbi.p0, bbi.width, bbi.height, linewidth=2,
                                   edgecolor=col, facecolor='none',
                                   transform=fig.transFigure, zorder=-2))

            bbi = lg.get_left_margin_bbox(rows=i, cols=j)
            fig.add_artist(
                mpatches.Rectangle(bbi.p0, bbi.width, bbi.height, linewidth=0,
                                   edgecolor='none', alpha=0.2,
                                   facecolor=[0.5, 0.7, 0.5],
                                   transform=fig.transFigure, zorder=-2))
            bbi = lg.get_right_margin_bbox(rows=i, cols=j)
            fig.add_artist(
                mpatches.Rectangle(bbi.p0, bbi.width, bbi.height, linewidth=0,
                                   edgecolor='none', alpha=0.2,
                                   facecolor=[0.7, 0.5, 0.5],
                                   transform=fig.transFigure, zorder=-2))
            bbi = lg.get_bottom_margin_bbox(rows=i, cols=j)
            fig.add_artist(
                mpatches.Rectangle(bbi.p0, bbi.width, bbi.height, linewidth=0,
                                   edgecolor='none', alpha=0.2,
                                   facecolor=[0.5, 0.5, 0.7],
                                   transform=fig.transFigure, zorder=-2))
            bbi = lg.get_top_margin_bbox(rows=i, cols=j)
            fig.add_artist(
                mpatches.Rectangle(bbi.p0, bbi.width, bbi.height, linewidth=0,
                                   edgecolor='none', alpha=0.2,
                                   facecolor=[0.7, 0.2, 0.7],
                                   transform=fig.transFigure, zorder=-2))
    for ch in lg.children.flat:
        if ch is not None:
            plot_children(fig, ch, level=level+1)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\common_request_processing.py ===
import asyncio
import json
import uuid
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Literal,
    Optional,
    Tuple,
    Union,
)

import httpx
import orjson
from fastapi import HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.constants import DD_TRACER_STREAMING_CHUNK_YIELD_RESOURCE
from litellm.litellm_core_utils.dd_tracing import tracer
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.proxy._types import ProxyException, UserAPIKeyAuth
from litellm.proxy.auth.auth_utils import check_response_size_is_safe
from litellm.proxy.common_utils.callback_utils import (
    get_logging_caching_headers,
    get_remaining_tokens_and_requests_from_request_data,
)
from litellm.proxy.route_llm_request import route_request
from litellm.proxy.utils import ProxyLogging
from litellm.router import Router

if TYPE_CHECKING:
    from litellm.proxy.proxy_server import ProxyConfig as _ProxyConfig

    ProxyConfig = _ProxyConfig
else:
    ProxyConfig = Any
from litellm.proxy.litellm_pre_call_utils import add_litellm_data_to_request


async def _parse_event_data_for_error(event_line: Union[str, bytes]) -> Optional[int]:
    """Parses an event line and returns an error code if present, else None."""
    event_line = (
        event_line.decode("utf-8") if isinstance(event_line, bytes) else event_line
    )
    if event_line.startswith("data: "):
        json_str = event_line[len("data: ") :].strip()
        if not json_str or json_str == "[DONE]":  # handle empty data or [DONE] message
            return None
        try:
            data = orjson.loads(json_str)
            if (
                isinstance(data, dict)
                and "error" in data
                and isinstance(data["error"], dict)
            ):
                error_code_raw = data["error"].get("code")
                error_code: Optional[int] = None

                if isinstance(error_code_raw, int):
                    error_code = error_code_raw
                elif isinstance(error_code_raw, str):
                    try:
                        error_code = int(error_code_raw)
                    except ValueError:
                        verbose_proxy_logger.warning(
                            f"Error code is a string but not a valid integer: {error_code_raw}"
                        )
                        # Not a valid integer string, treat as if no valid code was found for this check
                        pass

                # Ensure error_code is a valid HTTP status code
                if error_code is not None and 100 <= error_code <= 599:
                    return error_code
                elif (
                    error_code_raw is not None
                ):  # Log if original code was present but not valid
                    verbose_proxy_logger.warning(
                        f"Error has invalid or non-convertible code: {error_code_raw}"
                    )
        except (orjson.JSONDecodeError, json.JSONDecodeError):
            # not a known error chunk
            pass
    return None


async def create_streaming_response(
    generator: AsyncGenerator[str, None],
    media_type: str,
    headers: dict,
    default_status_code: int = status.HTTP_200_OK,
) -> StreamingResponse:
    """
    Creates a StreamingResponse by inspecting the first chunk for an error code.
    The entire original generator content is streamed, but the HTTP status code
    of the response is set based on the first chunk if it's a recognized error.
    """
    first_chunk_value: Optional[str] = None
    final_status_code = default_status_code

    try:
        first_chunk_value = await generator.__anext__()
        if first_chunk_value is not None:
            error_code_from_chunk = await _parse_event_data_for_error(first_chunk_value)
            if error_code_from_chunk is not None:
                final_status_code = error_code_from_chunk
                verbose_proxy_logger.debug(
                    f"Error detected in first stream chunk. Status code set to: {final_status_code}"
                )

    except StopAsyncIteration:
        # Generator was empty. Default status
        async def empty_gen() -> AsyncGenerator[str, None]:
            if False:
                yield  # type: ignore

        return StreamingResponse(
            empty_gen(),
            media_type=media_type,
            headers=headers,
            status_code=default_status_code,
        )
    except Exception as e:
        # Unexpected error consuming first chunk.
        verbose_proxy_logger.exception(
            f"Error consuming first chunk from generator: {e}"
        )

        # Fallback to a generic error stream
        async def error_gen_message() -> AsyncGenerator[str, None]:
            yield f"data: {json.dumps({'error': {'message': 'Error processing stream start', 'code': status.HTTP_500_INTERNAL_SERVER_ERROR}})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            error_gen_message(),
            media_type=media_type,
            headers=headers,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    async def combined_generator() -> AsyncGenerator[str, None]:
        if first_chunk_value is not None:
            with tracer.trace(DD_TRACER_STREAMING_CHUNK_YIELD_RESOURCE):
                yield first_chunk_value
        async for chunk in generator:
            with tracer.trace(DD_TRACER_STREAMING_CHUNK_YIELD_RESOURCE):
                yield chunk

    return StreamingResponse(
        combined_generator(),
        media_type=media_type,
        headers=headers,
        status_code=final_status_code,
    )


class ProxyBaseLLMRequestProcessing:
    def __init__(self, data: dict):
        self.data = data

    @staticmethod
    def get_custom_headers(
        *,
        user_api_key_dict: UserAPIKeyAuth,
        call_id: Optional[str] = None,
        model_id: Optional[str] = None,
        cache_key: Optional[str] = None,
        api_base: Optional[str] = None,
        version: Optional[str] = None,
        model_region: Optional[str] = None,
        response_cost: Optional[Union[float, str]] = None,
        hidden_params: Optional[dict] = None,
        fastest_response_batch_completion: Optional[bool] = None,
        request_data: Optional[dict] = {},
        timeout: Optional[Union[float, int, httpx.Timeout]] = None,
        **kwargs,
    ) -> dict:
        exclude_values = {"", None, "None"}
        hidden_params = hidden_params or {}
        headers = {
            "x-litellm-call-id": call_id,
            "x-litellm-model-id": model_id,
            "x-litellm-cache-key": cache_key,
            "x-litellm-model-api-base": (
                api_base.split("?")[0] if api_base else None
            ),  # don't include query params, risk of leaking sensitive info
            "x-litellm-version": version,
            "x-litellm-model-region": model_region,
            "x-litellm-response-cost": str(response_cost),
            "x-litellm-key-tpm-limit": str(user_api_key_dict.tpm_limit),
            "x-litellm-key-rpm-limit": str(user_api_key_dict.rpm_limit),
            "x-litellm-key-max-budget": str(user_api_key_dict.max_budget),
            "x-litellm-key-spend": str(user_api_key_dict.spend),
            "x-litellm-response-duration-ms": str(
                hidden_params.get("_response_ms", None)
            ),
            "x-litellm-overhead-duration-ms": str(
                hidden_params.get("litellm_overhead_time_ms", None)
            ),
            "x-litellm-fastest_response_batch_completion": (
                str(fastest_response_batch_completion)
                if fastest_response_batch_completion is not None
                else None
            ),
            "x-litellm-timeout": str(timeout) if timeout is not None else None,
            **{k: str(v) for k, v in kwargs.items()},
        }
        if request_data:
            remaining_tokens_header = (
                get_remaining_tokens_and_requests_from_request_data(request_data)
            )
            headers.update(remaining_tokens_header)

            logging_caching_headers = get_logging_caching_headers(request_data)
            if logging_caching_headers:
                headers.update(logging_caching_headers)

        try:
            return {
                key: str(value)
                for key, value in headers.items()
                if value not in exclude_values
            }
        except Exception as e:
            verbose_proxy_logger.error(f"Error setting custom headers: {e}")
            return {}

    async def common_processing_pre_call_logic(
        self,
        request: Request,
        general_settings: dict,
        user_api_key_dict: UserAPIKeyAuth,
        proxy_logging_obj: ProxyLogging,
        proxy_config: ProxyConfig,
        route_type: Literal[
            "acompletion",
            "aresponses",
            "_arealtime",
            "aget_responses",
            "adelete_responses",
            "acreate_batch",
            "aretrieve_batch",
            "afile_content",
            "atext_completion",
            "acreate_fine_tuning_job",
            "acancel_fine_tuning_job",
            "alist_fine_tuning_jobs",
            "aretrieve_fine_tuning_job",
            "alist_input_items",
            "aimage_edit",
        ],
        version: Optional[str] = None,
        user_model: Optional[str] = None,
        user_temperature: Optional[float] = None,
        user_request_timeout: Optional[float] = None,
        user_max_tokens: Optional[int] = None,
        user_api_base: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[dict, LiteLLMLoggingObj]:
        self.data = await add_litellm_data_to_request(
            data=self.data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        self.data["model"] = (
            general_settings.get("completion_model", None)  # server default
            or user_model  # model name passed via cli args
            or model  # for azure deployments
            or self.data.get("model", None)  # default passed in http request
        )

        # override with user settings, these are params passed via cli
        if user_temperature:
            self.data["temperature"] = user_temperature
        if user_request_timeout:
            self.data["request_timeout"] = user_request_timeout
        if user_max_tokens:
            self.data["max_tokens"] = user_max_tokens
        if user_api_base:
            self.data["api_base"] = user_api_base

        ### MODEL ALIAS MAPPING ###
        # check if model name in model alias map
        # get the actual model name
        if (
            isinstance(self.data["model"], str)
            and self.data["model"] in litellm.model_alias_map
        ):
            self.data["model"] = litellm.model_alias_map[self.data["model"]]

        self.data["litellm_call_id"] = request.headers.get(
            "x-litellm-call-id", str(uuid.uuid4())
        )
        ### CALL HOOKS ### - modify/reject incoming data before calling the model
        self.data = await proxy_logging_obj.pre_call_hook(  # type: ignore
            user_api_key_dict=user_api_key_dict, data=self.data, call_type=route_type  # type: ignore
        )

        ## LOGGING OBJECT ## - initialize logging object for logging success/failure events for call
        ## IMPORTANT Note: - initialize this before running pre-call checks. Ensures we log rejected requests to langfuse.
        logging_obj, self.data = litellm.utils.function_setup(
            original_function=route_type,
            rules_obj=litellm.utils.Rules(),
            start_time=datetime.now(),
            **self.data,
        )

        self.data["litellm_logging_obj"] = logging_obj

        return self.data, logging_obj

    async def base_process_llm_request(
        self,
        request: Request,
        fastapi_response: Response,
        user_api_key_dict: UserAPIKeyAuth,
        route_type: Literal[
            "acompletion",
            "aresponses",
            "_arealtime",
            "aget_responses",
            "adelete_responses",
            "atext_completion",
            "aimage_edit",
            "alist_input_items",
        ],
        proxy_logging_obj: ProxyLogging,
        general_settings: dict,
        proxy_config: ProxyConfig,
        select_data_generator: Callable,
        llm_router: Optional[Router] = None,
        model: Optional[str] = None,
        user_model: Optional[str] = None,
        user_temperature: Optional[float] = None,
        user_request_timeout: Optional[float] = None,
        user_max_tokens: Optional[int] = None,
        user_api_base: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Any:
        """
        Common request processing logic for both chat completions and responses API endpoints
        """
        verbose_proxy_logger.debug(
            "Request received by LiteLLM:\n{}".format(
                json.dumps(self.data, indent=4, default=str)
            ),
        )

        self.data, logging_obj = await self.common_processing_pre_call_logic(
            request=request,
            general_settings=general_settings,
            proxy_logging_obj=proxy_logging_obj,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
            user_model=user_model,
            user_temperature=user_temperature,
            user_request_timeout=user_request_timeout,
            user_max_tokens=user_max_tokens,
            user_api_base=user_api_base,
            model=model,
            route_type=route_type,
        )

        tasks = []
        tasks.append(
            proxy_logging_obj.during_call_hook(
                data=self.data,
                user_api_key_dict=user_api_key_dict,
                call_type=ProxyBaseLLMRequestProcessing._get_pre_call_type(
                    route_type=route_type  # type: ignore
                ),
            )
        )

        ### ROUTE THE REQUEST ###
        # Do not change this - it should be a constant time fetch - ALWAYS
        llm_call = await route_request(
            data=self.data,
            route_type=route_type,
            llm_router=llm_router,
            user_model=user_model,
        )
        tasks.append(llm_call)

        # wait for call to end
        llm_responses = asyncio.gather(
            *tasks
        )  # run the moderation check in parallel to the actual llm api call

        responses = await llm_responses

        response = responses[1]

        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""
        response_cost = hidden_params.get("response_cost", None) or ""
        fastest_response_batch_completion = hidden_params.get(
            "fastest_response_batch_completion", None
        )
        additional_headers: dict = hidden_params.get("additional_headers", {}) or {}

        # Post Call Processing
        if llm_router is not None:
            self.data["deployment"] = llm_router.get_deployment(model_id=model_id)
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=self.data.get("litellm_call_id", ""), status="success"
            )
        )
        if (
            "stream" in self.data and self.data["stream"] is True
        ):  # use generate_responses to stream responses
            custom_headers = ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                call_id=logging_obj.litellm_call_id,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                response_cost=response_cost,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                fastest_response_batch_completion=fastest_response_batch_completion,
                request_data=self.data,
                hidden_params=hidden_params,
                **additional_headers,
            )
            selected_data_generator = select_data_generator(
                response=response,
                user_api_key_dict=user_api_key_dict,
                request_data=self.data,
            )
            return await create_streaming_response(
                generator=selected_data_generator,
                media_type="text/event-stream",
                headers=custom_headers,
            )

        ### CALL HOOKS ### - modify outgoing data
        response = await proxy_logging_obj.post_call_success_hook(
            data=self.data, user_api_key_dict=user_api_key_dict, response=response
        )

        hidden_params = (
            getattr(response, "_hidden_params", {}) or {}
        )  # get any updated response headers
        additional_headers = hidden_params.get("additional_headers", {}) or {}

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                call_id=logging_obj.litellm_call_id,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                response_cost=response_cost,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                fastest_response_batch_completion=fastest_response_batch_completion,
                request_data=self.data,
                hidden_params=hidden_params,
                **additional_headers,
            )
        )
        await check_response_size_is_safe(response=response)

        return response

    async def _handle_llm_api_exception(
        self,
        e: Exception,
        user_api_key_dict: UserAPIKeyAuth,
        proxy_logging_obj: ProxyLogging,
        version: Optional[str] = None,
    ):
        """Raises ProxyException (OpenAI API compatible) if an exception is raised"""
        verbose_proxy_logger.exception(
            f"litellm.proxy.proxy_server._handle_llm_api_exception(): Exception occured - {str(e)}"
        )
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict,
            original_exception=e,
            request_data=self.data,
        )
        litellm_debug_info = getattr(e, "litellm_debug_info", "")
        verbose_proxy_logger.debug(
            "\033[1;31mAn error occurred: %s %s\n\n Debug this by setting `--debug`, e.g. `litellm --model gpt-3.5-turbo --debug`",
            e,
            litellm_debug_info,
        )

        timeout = getattr(
            e, "timeout", None
        )  # returns the timeout set by the wrapper. Used for testing if model-specific timeout are set correctly
        _litellm_logging_obj: Optional[LiteLLMLoggingObj] = self.data.get(
            "litellm_logging_obj", None
        )
        custom_headers = ProxyBaseLLMRequestProcessing.get_custom_headers(
            user_api_key_dict=user_api_key_dict,
            call_id=(
                _litellm_logging_obj.litellm_call_id if _litellm_logging_obj else None
            ),
            version=version,
            response_cost=0,
            model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            request_data=self.data,
            timeout=timeout,
        )
        headers = getattr(e, "headers", {}) or {}
        headers.update(custom_headers)

        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", str(e)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
                headers=headers,
            )
        error_msg = f"{str(e)}"
        raise ProxyException(
            message=getattr(e, "message", error_msg),
            type=getattr(e, "type", "None"),
            param=getattr(e, "param", "None"),
            openai_code=getattr(e, "code", None),
            code=getattr(e, "status_code", 500),
            headers=headers,
        )

    @staticmethod
    def _get_pre_call_type(
        route_type: Literal["acompletion", "aresponses"],
    ) -> Literal["completion", "responses"]:
        if route_type == "acompletion":
            return "completion"
        elif route_type == "aresponses":
            return "responses"