
# === NexusCore/openenv\Lib\site-packages\pygments\lexers\javascript.py ===
"""
    pygments.lexers.javascript
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for JavaScript and related languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import bygroups, combined, default, do_insertions, include, \
    inherit, Lexer, RegexLexer, this, using, words, line_re
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Other, Generic, Whitespace
from pygments.util import get_bool_opt
import pygments.unistring as uni

__all__ = ['JavascriptLexer', 'KalLexer', 'LiveScriptLexer', 'DartLexer',
           'TypeScriptLexer', 'LassoLexer', 'ObjectiveJLexer',
           'CoffeeScriptLexer', 'MaskLexer', 'EarlGreyLexer', 'JuttleLexer',
           'NodeConsoleLexer']

JS_IDENT_START = ('(?:[$_' + uni.combine('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl') +
                  ']|\\\\u[a-fA-F0-9]{4})')
JS_IDENT_PART = ('(?:[$' + uni.combine('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl',
                                       'Mn', 'Mc', 'Nd', 'Pc') +
                 '\u200c\u200d]|\\\\u[a-fA-F0-9]{4})')
JS_IDENT = JS_IDENT_START + '(?:' + JS_IDENT_PART + ')*'


class JavascriptLexer(RegexLexer):
    """
    For JavaScript source code.
    """

    name = 'JavaScript'
    url = 'https://www.ecma-international.org/publications-and-standards/standards/ecma-262/'
    aliases = ['javascript', 'js']
    filenames = ['*.js', '*.jsm', '*.mjs', '*.cjs']
    mimetypes = ['application/javascript', 'application/x-javascript',
                 'text/x-javascript', 'text/javascript']
    version_added = ''

    flags = re.DOTALL | re.MULTILINE

    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Whitespace),
            (r'<!--', Comment),
            (r'//.*?$', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gimuysd]+\b|\B)', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            default('#pop')
        ],
        'badregex': [
            (r'\n', Whitespace, '#pop')
        ],
        'root': [
            (r'\A#! ?/.*?$', Comment.Hashbang),  # recognized by node.js
            (r'^(?=\s|/|<!--)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),

            # Numeric literals
            (r'0[bB][01]+n?', Number.Bin),
            (r'0[oO]?[0-7]+n?', Number.Oct),  # Browsers support "0o7" and "07" (< ES5) notations
            (r'0[xX][0-9a-fA-F]+n?', Number.Hex),
            (r'[0-9]+n', Number.Integer),  # Javascript BigInt requires an "n" postfix
            # Javascript doesn't have actual integer literals, so every other
            # numeric literal is handled by the regex below (including "normal")
            # integers
            (r'(\.[0-9]+|[0-9]+\.[0-9]*|[0-9]+)([eE][-+]?[0-9]+)?', Number.Float),

            (r'\.\.\.|=>', Punctuation),
            (r'\+\+|--|~|\?\?=?|\?|:|\\(?=\n)|'
             r'(<<|>>>?|==?|!=?|(?:\*\*|\|\||&&|[-<>+*%&|^/]))=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),

            (r'(typeof|instanceof|in|void|delete|new)\b', Operator.Word, 'slashstartsregex'),

            # Match stuff like: constructor
            (r'\b(constructor|from|as)\b', Keyword.Reserved),

            (r'(for|in|while|do|break|return|continue|switch|case|default|if|else|'
             r'throw|try|catch|finally|yield|await|async|this|of|static|export|'
             r'import|debugger|extends|super)\b', Keyword, 'slashstartsregex'),
            (r'(var|let|const|with|function|class)\b', Keyword.Declaration, 'slashstartsregex'),

            (r'(abstract|boolean|byte|char|double|enum|final|float|goto|'
             r'implements|int|interface|long|native|package|private|protected|'
             r'public|short|synchronized|throws|transient|volatile)\b', Keyword.Reserved),
            (r'(true|false|null|NaN|Infinity|undefined)\b', Keyword.Constant),

            (r'(Array|Boolean|Date|BigInt|Function|Math|ArrayBuffer|'
             r'Number|Object|RegExp|String|Promise|Proxy|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'eval|isFinite|isNaN|parseFloat|parseInt|DataView|'
             r'document|window|globalThis|global|Symbol|Intl|'
             r'WeakSet|WeakMap|Set|Map|Reflect|JSON|Atomics|'
             r'Int(?:8|16|32)Array|BigInt64Array|Float32Array|Float64Array|'
             r'Uint8ClampedArray|Uint(?:8|16|32)Array|BigUint64Array)\b', Name.Builtin),

            (r'((?:Eval|Internal|Range|Reference|Syntax|Type|URI)?Error)\b', Name.Exception),

            # Match stuff like: super(argument, list)
            (r'(super)(\s*)(\([\w,?.$\s]+\s*\))',
             bygroups(Keyword, Whitespace), 'slashstartsregex'),
            # Match stuff like: function() {...}
            (r'([a-zA-Z_?.$][\w?.$]*)(?=\(\) \{)', Name.Other, 'slashstartsregex'),

            (JS_IDENT, Name.Other),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r'`', String.Backtick, 'interp'),
            # private identifier
            (r'#[a-zA-Z_]\w*', Name),
        ],
        'interp': [
            (r'`', String.Backtick, '#pop'),
            (r'\\.', String.Backtick),
            (r'\$\{', String.Interpol, 'interp-inside'),
            (r'\$', String.Backtick),
            (r'[^`\\$]+', String.Backtick),
        ],
        'interp-inside': [
            # TODO: should this include single-line comments and allow nesting strings?
            (r'\}', String.Interpol, '#pop'),
            include('root'),
        ],
    }


class TypeScriptLexer(JavascriptLexer):
    """
    For TypeScript source code.
    """

    name = 'TypeScript'
    url = 'https://www.typescriptlang.org/'
    aliases = ['typescript', 'ts']
    filenames = ['*.ts']
    mimetypes = ['application/x-typescript', 'text/x-typescript']
    version_added = '1.6'

    # Higher priority than the TypoScriptLexer, as TypeScript is far more
    # common these days
    priority = 0.5

    tokens = {
        'root': [
            (r'(abstract|implements|private|protected|public|readonly)\b',
                Keyword, 'slashstartsregex'),
            (r'(enum|interface|override)\b', Keyword.Declaration, 'slashstartsregex'),
            (r'\b(declare|type)\b', Keyword.Reserved),
            # Match variable type keywords
            (r'\b(string|boolean|number)\b', Keyword.Type),
            # Match stuff like: module name {...}
            (r'\b(module)(\s*)([\w?.$]+)(\s*)',
             bygroups(Keyword.Reserved, Whitespace, Name.Other, Whitespace), 'slashstartsregex'),
            # Match stuff like: (function: return type)
            (r'([\w?.$]+)(\s*)(:)(\s*)([\w?.$]+)',
             bygroups(Name.Other, Whitespace, Operator, Whitespace, Keyword.Type)),
            # Match stuff like: Decorators
            (r'@' + JS_IDENT, Keyword.Declaration),
            inherit,
            # private identifier
            (r'#[a-zA-Z_]\w*', Name),
        ],
    }


class KalLexer(RegexLexer):
    """
    For Kal source code.
    """

    name = 'Kal'
    url = 'http://rzimmerman.github.io/kal'
    aliases = ['kal']
    filenames = ['*.kal']
    mimetypes = ['text/kal', 'application/kal']
    version_added = '2.0'

    flags = re.DOTALL
    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Whitespace),
            (r'###[^#].*?###', Comment.Multiline),
            (r'(#(?!##[^#]).*?)(\n)', bygroups(Comment.Single, Whitespace)),
        ],
        'functiondef': [
            (r'([$a-zA-Z_][\w$]*)(\s*)', bygroups(Name.Function, Whitespace),
                '#pop'),
            include('commentsandwhitespace'),
        ],
        'classdef': [
            (r'\b(inherits)(\s+)(from)\b',
                bygroups(Keyword, Whitespace, Keyword)),
            (r'([$a-zA-Z_][\w$]*)(?=\s*\n)', Name.Class, '#pop'),
            (r'[$a-zA-Z_][\w$]*\b', Name.Class),
            include('commentsandwhitespace'),
        ],
        'listcomprehension': [
            (r'\]', Punctuation, '#pop'),
            (r'\b(property|value)\b', Keyword),
            include('root'),
        ],
        'waitfor': [
            (r'\n', Whitespace, '#pop'),
            (r'\bfrom\b', Keyword),
            include('root'),
        ],
        'root': [
            include('commentsandwhitespace'),
            (r'/(?! )(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gimuysd]+\b|\B)', String.Regex),
            (r'\?|:|_(?=\n)|==?|!=|-(?!>)|[<>+*/-]=?',
             Operator),
            (r'\b(and|or|isnt|is|not|but|bitwise|mod|\^|xor|exists|'
             r'doesnt\s+exist)\b', Operator.Word),
            (r'(\([^()]+\))?(\s*)(>)',
                bygroups(Name.Function, Whitespace, Punctuation)),
            (r'[{(]', Punctuation),
            (r'\[', Punctuation, 'listcomprehension'),
            (r'[})\].,]', Punctuation),
            (r'\b(function|method|task)\b', Keyword.Declaration, 'functiondef'),
            (r'\bclass\b', Keyword.Declaration, 'classdef'),
            (r'\b(safe(?=\s))?(\s*)(wait(?=\s))(\s+)(for)\b',
                bygroups(Keyword, Whitespace, Keyword, Whitespace,
                    Keyword), 'waitfor'),
            (r'\b(me|this)(\.[$a-zA-Z_][\w.$]*)?\b', Name.Variable.Instance),
            (r'(?<![.$])(run)(\s+)(in)(\s+)(parallel)\b',
                bygroups(Keyword, Whitespace, Keyword, Whitespace, Keyword)),
            (r'(?<![.$])(for)(\s+)(parallel|series)?\b',
                bygroups(Keyword, Whitespace, Keyword)),
            (r'(?<![.$])(except)(\s+)(when)?\b',
                bygroups(Keyword, Whitespace, Keyword)),
            (r'(?<![.$])(fail)(\s+)(with)?\b',
                bygroups(Keyword, Whitespace, Keyword)),
            (r'(?<![.$])(inherits)(\s+)(from)?\b',
                bygroups(Keyword, Whitespace, Keyword)),
            (r'(?<![.$])(for)(\s+)(parallel|series)?\b',
                bygroups(Keyword, Whitespace, Keyword)),
            (words((
                'in', 'of', 'while', 'until', 'break', 'return', 'continue',
                'when', 'if', 'unless', 'else', 'otherwise', 'throw', 'raise',
                'try', 'catch', 'finally', 'new', 'delete', 'typeof',
                'instanceof', 'super'), prefix=r'(?<![.$])', suffix=r'\b'),
                Keyword),
            (words((
                'true', 'false', 'yes', 'no', 'on', 'off', 'null', 'nothing',
                'none', 'NaN', 'Infinity', 'undefined'), prefix=r'(?<![.$])',
                suffix=r'\b'), Keyword.Constant),
            (words((
                'Array', 'Boolean', 'Date', 'Error', 'Function', 'Math',
                'Number', 'Object', 'RegExp', 'String', 'decodeURI',
                'decodeURIComponent', 'encodeURI', 'encodeURIComponent', 'eval',
                'isFinite', 'isNaN', 'isSafeInteger', 'parseFloat', 'parseInt',
                'document', 'window', 'globalThis', 'Symbol', 'print'),
                suffix=r'\b'), Name.Builtin),
            (r'([$a-zA-Z_][\w.$]*)(\s*)(:|[+\-*/]?\=)?\b',
                bygroups(Name.Variable, Whitespace, Operator)),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            ('"""', String, 'tdqs'),
            ("'''", String, 'tsqs'),
            ('"', String, 'dqs'),
            ("'", String, 'sqs'),
        ],
        'strings': [
            (r'[^#\\\'"]+', String),
            # note that all kal strings are multi-line.
            # hashmarks, quotes and backslashes must be parsed one at a time
        ],
        'interpoling_string': [
            (r'\}', String.Interpol, "#pop"),
            include('root')
        ],
        'dqs': [
            (r'"', String, '#pop'),
            (r'\\.|\'', String),  # double-quoted string don't need ' escapes
            (r'#\{', String.Interpol, "interpoling_string"),
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            (r'#|\\.|"', String),  # single quoted strings don't need " escapses
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            (r'\\.|\'|"', String),  # no need to escape quotes in triple-string
            (r'#\{', String.Interpol, "interpoling_string"),
            include('strings'),
        ],
        'tsqs': [
            (r"'''", String, '#pop'),
            (r'#|\\.|\'|"', String),  # no need to escape quotes in triple-strings
            include('strings')
        ],
    }


class LiveScriptLexer(RegexLexer):
    """
    For LiveScript source code.
    """

    name = 'LiveScript'
    url = 'https://livescript.net/'
    aliases = ['livescript', 'live-script']
    filenames = ['*.ls']
    mimetypes = ['text/livescript']
    version_added = '1.6'

    flags = re.DOTALL
    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Whitespace),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'(#.*?)(\n)', bygroups(Comment.Single, Whitespace)),
        ],
        'multilineregex': [
            include('commentsandwhitespace'),
            (r'//([gimuysd]+\b|\B)', String.Regex, '#pop'),
            (r'/', String.Regex),
            (r'[^/#]+', String.Regex)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'//', String.Regex, ('#pop', 'multilineregex')),
            (r'/(?! )(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gimuysd]+\b|\B)', String.Regex, '#pop'),
            (r'/', Operator, '#pop'),
            default('#pop'),
        ],
        'root': [
            (r'\A(?=\s|/)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),
            (r'(?:\([^()]+\))?[ ]*[~-]{1,2}>|'
             r'(?:\(?[^()\n]+\)?)?[ ]*<[~-]{1,2}', Name.Function),
            (r'\+\+|&&|(?<![.$])\b(?:and|x?or|is|isnt|not)\b|\?|:|=|'
             r'\|\||\\(?=\n)|(<<|>>>?|==?|!=?|'
             r'~(?!\~?>)|-(?!\-?>)|<(?!\[)|(?<!\])>|'
             r'[+*`%&|^/])=?',
             Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(?<![.$])(for|own|in|of|while|until|loop|break|'
             r'return|continue|switch|when|then|if|unless|else|'
             r'throw|try|catch|finally|new|delete|typeof|instanceof|super|'
             r'extends|this|class|by|const|var|to|til)\b', Keyword,
             'slashstartsregex'),
            (r'(?<![.$])(true|false|yes|no|on|off|'
             r'null|NaN|Infinity|undefined|void)\b',
             Keyword.Constant),
            (r'(Array|Boolean|Date|Error|Function|Math|'
             r'Number|Object|RegExp|String|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'eval|isFinite|isNaN|parseFloat|parseInt|document|window|'
             r'globalThis|Symbol|Symbol|BigInt)\b', Name.Builtin),
            (r'([$a-zA-Z_][\w.\-:$]*)(\s*)([:=])(\s+)',
                bygroups(Name.Variable, Whitespace, Operator, Whitespace),
                'slashstartsregex'),
            (r'(@[$a-zA-Z_][\w.\-:$]*)(\s*)([:=])(\s+)',
                bygroups(Name.Variable.Instance, Whitespace, Operator,
                    Whitespace),
                'slashstartsregex'),
            (r'@', Name.Other, 'slashstartsregex'),
            (r'@?[$a-zA-Z_][\w-]*', Name.Other, 'slashstartsregex'),
            (r'[0-9]+\.[0-9]+([eE][0-9]+)?[fd]?(?:[a-zA-Z_]+)?', Number.Float),
            (r'[0-9]+(~[0-9a-z]+)?(?:[a-zA-Z_]+)?', Number.Integer),
            ('"""', String, 'tdqs'),
            ("'''", String, 'tsqs'),
            ('"', String, 'dqs'),
            ("'", String, 'sqs'),
            (r'\\\S+', String),
            (r'<\[.*?\]>', String),
        ],
        'strings': [
            (r'[^#\\\'"]+', String),
            # note that all coffee script strings are multi-line.
            # hashmarks, quotes and backslashes must be parsed one at a time
        ],
        'interpoling_string': [
            (r'\}', String.Interpol, "#pop"),
            include('root')
        ],
        'dqs': [
            (r'"', String, '#pop'),
            (r'\\.|\'', String),  # double-quoted string don't need ' escapes
            (r'#\{', String.Interpol, "interpoling_string"),
            (r'#', String),
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            (r'#|\\.|"', String),  # single quoted strings don't need " escapses
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            (r'\\.|\'|"', String),  # no need to escape quotes in triple-string
            (r'#\{', String.Interpol, "interpoling_string"),
            (r'#', String),
            include('strings'),
        ],
        'tsqs': [
            (r"'''", String, '#pop'),
            (r'#|\\.|\'|"', String),  # no need to escape quotes in triple-strings
            include('strings')
        ],
    }


class DartLexer(RegexLexer):
    """
    For Dart source code.
    """

    name = 'Dart'
    url = 'http://dart.dev/'
    aliases = ['dart']
    filenames = ['*.dart']
    mimetypes = ['text/x-dart']
    version_added = '1.5'

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            include('string_literal'),
            (r'#!(.*?)$', Comment.Preproc),
            (r'\b(import|export)\b', Keyword, 'import_decl'),
            (r'\b(library|source|part of|part)\b', Keyword),
            (r'[^\S\n]+', Whitespace),
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'\b(class|extension|mixin)\b(\s+)',
             bygroups(Keyword.Declaration, Whitespace), 'class'),
            (r'\b(as|assert|break|case|catch|const|continue|default|do|else|finally|'
             r'for|if|in|is|new|rethrow|return|super|switch|this|throw|try|while)\b',
             Keyword),
            (r'\b(abstract|async|await|const|covariant|extends|external|factory|final|'
             r'get|implements|late|native|on|operator|required|set|static|sync|typedef|'
             r'var|with|yield)\b', Keyword.Declaration),
            (r'\b(bool|double|dynamic|int|num|Function|Never|Null|Object|String|void)\b',
             Keyword.Type),
            (r'\b(false|null|true)\b', Keyword.Constant),
            (r'[~!%^&*+=|?:<>/-]|as\b', Operator),
            (r'@[a-zA-Z_$]\w*', Name.Decorator),
            (r'[a-zA-Z_$]\w*:', Name.Label),
            (r'[a-zA-Z_$]\w*', Name),
            (r'[(){}\[\],.;]', Punctuation),
            (r'0[xX][0-9a-fA-F]+', Number.Hex),
            # DIGIT+ (‘.’ DIGIT*)? EXPONENT?
            (r'\d+(\.\d*)?([eE][+-]?\d+)?', Number),
            (r'\.\d+([eE][+-]?\d+)?', Number),  # ‘.’ DIGIT+ EXPONENT?
            (r'\n', Whitespace)
            # pseudo-keyword negate intentionally left out
        ],
        'class': [
            (r'[a-zA-Z_$]\w*', Name.Class, '#pop')
        ],
        'import_decl': [
            include('string_literal'),
            (r'\s+', Whitespace),
            (r'\b(as|deferred|show|hide)\b', Keyword),
            (r'[a-zA-Z_$]\w*', Name),
            (r'\,', Punctuation),
            (r'\;', Punctuation, '#pop')
        ],
        'string_literal': [
            # Raw strings.
            (r'r"""([\w\W]*?)"""', String.Double),
            (r"r'''([\w\W]*?)'''", String.Single),
            (r'r"(.*?)"', String.Double),
            (r"r'(.*?)'", String.Single),
            # Normal Strings.
            (r'"""', String.Double, 'string_double_multiline'),
            (r"'''", String.Single, 'string_single_multiline'),
            (r'"', String.Double, 'string_double'),
            (r"'", String.Single, 'string_single')
        ],
        'string_common': [
            (r"\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|u\{[0-9A-Fa-f]*\}|[a-z'\"$\\])",
             String.Escape),
            (r'(\$)([a-zA-Z_]\w*)', bygroups(String.Interpol, Name)),
            (r'(\$\{)(.*?)(\})',
             bygroups(String.Interpol, using(this), String.Interpol))
        ],
        'string_double': [
            (r'"', String.Double, '#pop'),
            (r'[^"$\\\n]+', String.Double),
            include('string_common'),
            (r'\$+', String.Double)
        ],
        'string_double_multiline': [
            (r'"""', String.Double, '#pop'),
            (r'[^"$\\]+', String.Double),
            include('string_common'),
            (r'(\$|\")+', String.Double)
        ],
        'string_single': [
            (r"'", String.Single, '#pop'),
            (r"[^'$\\\n]+", String.Single),
            include('string_common'),
            (r'\$+', String.Single)
        ],
        'string_single_multiline': [
            (r"'''", String.Single, '#pop'),
            (r'[^\'$\\]+', String.Single),
            include('string_common'),
            (r'(\$|\')+', String.Single)
        ]
    }


class LassoLexer(RegexLexer):
    """
    For Lasso source code, covering both Lasso 9
    syntax and LassoScript for Lasso 8.6 and earlier. For Lasso embedded in
    HTML, use the `LassoHtmlLexer`.

    Additional options accepted:

    `builtinshighlighting`
        If given and ``True``, highlight builtin types, traits, methods, and
        members (default: ``True``).
    `requiredelimiters`
        If given and ``True``, only highlight code between delimiters as Lasso
        (default: ``False``).
    """

    name = 'Lasso'
    aliases = ['lasso', 'lassoscript']
    filenames = ['*.lasso', '*.lasso[89]']
    version_added = '1.6'
    alias_filenames = ['*.incl', '*.inc', '*.las']
    mimetypes = ['text/x-lasso']
    url = 'https://www.lassosoft.com'

    flags = re.IGNORECASE | re.DOTALL | re.MULTILINE

    tokens = {
        'root': [
            (r'^#![ \S]+lasso9\b', Comment.Preproc, 'lasso'),
            (r'(?=\[|<)', Other, 'delimiters'),
            (r'\s+', Whitespace),
            default(('delimiters', 'lassofile')),
        ],
        'delimiters': [
            (r'\[no_square_brackets\]', Comment.Preproc, 'nosquarebrackets'),
            (r'\[noprocess\]', Comment.Preproc, 'noprocess'),
            (r'\[', Comment.Preproc, 'squarebrackets'),
            (r'<\?(lasso(script)?|=)', Comment.Preproc, 'anglebrackets'),
            (r'<(!--.*?-->)?', Other),
            (r'[^[<]+', Other),
        ],
        'nosquarebrackets': [
            (r'\[noprocess\]', Comment.Preproc, 'noprocess'),
            (r'\[', Other),
            (r'<\?(lasso(script)?|=)', Comment.Preproc, 'anglebrackets'),
            (r'<(!--.*?-->)?', Other),
            (r'[^[<]+', Other),
        ],
        'noprocess': [
            (r'\[/noprocess\]', Comment.Preproc, '#pop'),
            (r'\[', Other),
            (r'[^[]', Other),
        ],
        'squarebrackets': [
            (r'\]', Comment.Preproc, '#pop'),
            include('lasso'),
        ],
        'anglebrackets': [
            (r'\?>', Comment.Preproc, '#pop'),
            include('lasso'),
        ],
        'lassofile': [
            (r'\]|\?>', Comment.Preproc, '#pop'),
            include('lasso'),
        ],
        'whitespacecomments': [
            (r'\s+', Whitespace),
            (r'(//.*?)(\s*)$', bygroups(Comment.Single, Whitespace)),
            (r'/\*\*!.*?\*/', String.Doc),
            (r'/\*.*?\*/', Comment.Multiline),
        ],
        'lasso': [
            # whitespace/comments
            include('whitespacecomments'),

            # literals
            (r'\d*\.\d+(e[+-]?\d+)?', Number.Float),
            (r'0x[\da-f]+', Number.Hex),
            (r'\d+', Number.Integer),
            (r'(infinity|NaN)\b', Number),
            (r"'", String.Single, 'singlestring'),
            (r'"', String.Double, 'doublestring'),
            (r'`[^`]*`', String.Backtick),

            # names
            (r'\$[a-z_][\w.]*', Name.Variable),
            (r'#([a-z_][\w.]*|\d+\b)', Name.Variable.Instance),
            (r"(\.)(\s*)('[a-z_][\w.]*')",
                bygroups(Name.Builtin.Pseudo, Whitespace, Name.Variable.Class)),
            (r"(self)(\s*)(->)(\s*)('[a-z_][\w.]*')",
                bygroups(Name.Builtin.Pseudo, Whitespace, Operator, Whitespace,
                    Name.Variable.Class)),
            (r'(\.\.?)(\s*)([a-z_][\w.]*(=(?!=))?)',
                bygroups(Name.Builtin.Pseudo, Whitespace, Name.Other.Member)),
            (r'(->\\?|&)(\s*)([a-z_][\w.]*(=(?!=))?)',
                bygroups(Operator, Whitespace, Name.Other.Member)),
            (r'(?<!->)(self|inherited|currentcapture|givenblock)\b',
                Name.Builtin.Pseudo),
            (r'-(?!infinity)[a-z_][\w.]*', Name.Attribute),
            (r'(::)(\s*)([a-z_][\w.]*)',
                bygroups(Punctuation, Whitespace, Name.Label)),
            (r'(error_(code|msg)_\w+|Error_AddError|Error_ColumnRestriction|'
             r'Error_DatabaseConnectionUnavailable|Error_DatabaseTimeout|'
             r'Error_DeleteError|Error_FieldRestriction|Error_FileNotFound|'
             r'Error_InvalidDatabase|Error_InvalidPassword|'
             r'Error_InvalidUsername|Error_ModuleNotFound|'
             r'Error_NoError|Error_NoPermission|Error_OutOfMemory|'
             r'Error_ReqColumnMissing|Error_ReqFieldMissing|'
             r'Error_RequiredColumnMissing|Error_RequiredFieldMissing|'
             r'Error_UpdateError)\b', Name.Exception),

            # definitions
            (r'(define)(\s+)([a-z_][\w.]*)(\s*)(=>)(\s*)(type|trait|thread)\b',
                bygroups(Keyword.Declaration, Whitespace, Name.Class,
                    Whitespace, Operator, Whitespace, Keyword)),
            (r'(define)(\s+)([a-z_][\w.]*)(\s*)(->)(\s*)([a-z_][\w.]*=?|[-+*/%])',
                bygroups(Keyword.Declaration, Whitespace, Name.Class,
                    Whitespace, Operator, Whitespace, Name.Function),
                'signature'),
            (r'(define)(\s+)([a-z_][\w.]*)',
                bygroups(Keyword.Declaration, Whitespace, Name.Function), 'signature'),
            (r'(public|protected|private|provide)(\s+)(([a-z_][\w.]*=?|[-+*/%])'
             r'(?=\s*\())', bygroups(Keyword, Whitespace, Name.Function),
                'signature'),
            (r'(public|protected|private|provide)(\s+)([a-z_][\w.]*)',
                bygroups(Keyword, Whitespace, Name.Function)),

            # keywords
            (r'(true|false|none|minimal|full|all|void)\b', Keyword.Constant),
            (r'(local|var|variable|global|data(?=\s))\b', Keyword.Declaration),
            (r'(array|date|decimal|duration|integer|map|pair|string|tag|xml|'
             r'null|boolean|bytes|keyword|list|locale|queue|set|stack|'
             r'staticarray)\b', Keyword.Type),
            (r'([a-z_][\w.]*)(\s+)(in)\b', bygroups(Name, Whitespace, Keyword)),
            (r'(let|into)(\s+)([a-z_][\w.]*)', bygroups(Keyword, Whitespace, Name)),
            (r'require\b', Keyword, 'requiresection'),
            (r'(/?)(Namespace_Using)\b', bygroups(Punctuation, Keyword.Namespace)),
            (r'(/?)(Cache|Database_Names|Database_SchemaNames|'
             r'Database_TableNames|Define_Tag|Define_Type|Email_Batch|'
             r'Encode_Set|HTML_Comment|Handle|Handle_Error|Header|If|Inline|'
             r'Iterate|LJAX_Target|Link|Link_CurrentAction|Link_CurrentGroup|'
             r'Link_CurrentRecord|Link_Detail|Link_FirstGroup|Link_FirstRecord|'
             r'Link_LastGroup|Link_LastRecord|Link_NextGroup|Link_NextRecord|'
             r'Link_PrevGroup|Link_PrevRecord|Log|Loop|Output_None|Portal|'
             r'Private|Protect|Records|Referer|Referrer|Repeating|ResultSet|'
             r'Rows|Search_Args|Search_Arguments|Select|Sort_Args|'
             r'Sort_Arguments|Thread_Atomic|Value_List|While|Abort|Case|Else|'
             r'Fail_If|Fail_IfNot|Fail|If_Empty|If_False|If_Null|If_True|'
             r'Loop_Abort|Loop_Continue|Loop_Count|Params|Params_Up|Return|'
             r'Return_Value|Run_Children|SOAP_DefineTag|SOAP_LastRequest|'
             r'SOAP_LastResponse|Tag_Name|ascending|average|by|define|'
             r'descending|do|equals|frozen|group|handle_failure|import|in|into|'
             r'join|let|match|max|min|on|order|parent|protected|provide|public|'
             r'require|returnhome|skip|split_thread|sum|take|thread|to|trait|'
             r'type|where|with|yield|yieldhome)\b',
                bygroups(Punctuation, Keyword)),

            # other
            (r',', Punctuation, 'commamember'),
            (r'(and|or|not)\b', Operator.Word),
            (r'([a-z_][\w.]*)(\s*)(::)(\s*)([a-z_][\w.]*)?(\s*=(?!=))',
                bygroups(Name, Whitespace, Punctuation, Whitespace, Name.Label,
                    Operator)),
            (r'(/?)([\w.]+)', bygroups(Punctuation, Name.Other)),
            (r'(=)(n?bw|n?ew|n?cn|lte?|gte?|n?eq|n?rx|ft)\b',
                bygroups(Operator, Operator.Word)),
            (r':=|[-+*/%=<>&|!?\\]+', Operator),
            (r'[{}():;,@^]', Punctuation),
        ],
        'singlestring': [
            (r"'", String.Single, '#pop'),
            (r"[^'\\]+", String.Single),
            include('escape'),
            (r"\\", String.Single),
        ],
        'doublestring': [
            (r'"', String.Double, '#pop'),
            (r'[^"\\]+', String.Double),
            include('escape'),
            (r'\\', String.Double),
        ],
        'escape': [
            (r'\\(U[\da-f]{8}|u[\da-f]{4}|x[\da-f]{1,2}|[0-7]{1,3}|:[^:\n\r]+:|'
             r'[abefnrtv?"\'\\]|$)', String.Escape),
        ],
        'signature': [
            (r'=>', Operator, '#pop'),
            (r'\)', Punctuation, '#pop'),
            (r'[(,]', Punctuation, 'parameter'),
            include('lasso'),
        ],
        'parameter': [
            (r'\)', Punctuation, '#pop'),
            (r'-?[a-z_][\w.]*', Name.Attribute, '#pop'),
            (r'\.\.\.', Name.Builtin.Pseudo),
            include('lasso'),
        ],
        'requiresection': [
            (r'(([a-z_][\w.]*=?|[-+*/%])(?=\s*\())', Name, 'requiresignature'),
            (r'(([a-z_][\w.]*=?|[-+*/%])(?=(\s*::\s*[\w.]+)?\s*,))', Name),
            (r'[a-z_][\w.]*=?|[-+*/%]', Name, '#pop'),
            (r'(::)(\s*)([a-z_][\w.]*)',
                bygroups(Punctuation, Whitespace, Name.Label)),
            (r',', Punctuation),
            include('whitespacecomments'),
        ],
        'requiresignature': [
            (r'(\)(?=(\s*::\s*[\w.]+)?\s*,))', Punctuation, '#pop'),
            (r'\)', Punctuation, '#pop:2'),
            (r'-?[a-z_][\w.]*', Name.Attribute),
            (r'(::)(\s*)([a-z_][\w.]*)',
                bygroups(Punctuation, Whitespace, Name.Label)),
            (r'\.\.\.', Name.Builtin.Pseudo),
            (r'[(,]', Punctuation),
            include('whitespacecomments'),
        ],
        'commamember': [
            (r'(([a-z_][\w.]*=?|[-+*/%])'
             r'(?=\s*(\(([^()]*\([^()]*\))*[^)]*\)\s*)?(::[\w.\s]+)?=>))',
                Name.Function, 'signature'),
            include('whitespacecomments'),
            default('#pop'),
        ],
    }

    def __init__(self, **options):
        self.builtinshighlighting = get_bool_opt(
            options, 'builtinshighlighting', True)
        self.requiredelimiters = get_bool_opt(
            options, 'requiredelimiters', False)

        self._builtins = set()
        self._members = set()
        if self.builtinshighlighting:
            from pygments.lexers._lasso_builtins import BUILTINS, MEMBERS
            for key, value in BUILTINS.items():
                self._builtins.update(value)
            for key, value in MEMBERS.items():
                self._members.update(value)
        RegexLexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        stack = ['root']
        if self.requiredelimiters:
            stack.append('delimiters')
        for index, token, value in \
                RegexLexer.get_tokens_unprocessed(self, text, stack):
            if (token is Name.Other and value.lower() in self._builtins or
                    token is Name.Other.Member and
                    value.lower().rstrip('=') in self._members):
                yield index, Name.Builtin, value
                continue
            yield index, token, value

    def analyse_text(text):
        rv = 0.0
        if 'bin/lasso9' in text:
            rv += 0.8
        if re.search(r'<\?lasso', text, re.I):
            rv += 0.4
        if re.search(r'local\(', text, re.I):
            rv += 0.4
        return rv


class ObjectiveJLexer(RegexLexer):
    """
    For Objective-J source code with preprocessor directives.
    """

    name = 'Objective-J'
    aliases = ['objective-j', 'objectivej', 'obj-j', 'objj']
    filenames = ['*.j']
    mimetypes = ['text/x-objective-j']
    url = 'https://www.cappuccino.dev/learn/objective-j.html'
    version_added = '1.3'

    #: optional Comment or Whitespace
    _ws = r'(?:\s|//[^\n]*\n|/[*](?:[^*]|[*][^/])*[*]/)*'

    flags = re.DOTALL | re.MULTILINE

    tokens = {
        'root': [
            include('whitespace'),

            # function definition
            (r'^(' + _ws + r'[+-]' + _ws + r')([(a-zA-Z_].*?[^(])(' + _ws + r'\{)',
             bygroups(using(this), using(this, state='function_signature'),
                      using(this))),

            # class definition
            (r'(@interface|@implementation)(\s+)', bygroups(Keyword, Whitespace),
             'classname'),
            (r'(@class|@protocol)(\s*)', bygroups(Keyword, Whitespace),
             'forward_classname'),
            (r'(\s*)(@end)(\s*)', bygroups(Whitespace, Keyword, Whitespace)),

            include('statements'),
            ('[{()}]', Punctuation),
            (';', Punctuation),
        ],
        'whitespace': [
            (r'(@import)(\s+)("(?:\\\\|\\"|[^"])*")',
             bygroups(Comment.Preproc, Whitespace, String.Double)),
            (r'(@import)(\s+)(<(?:\\\\|\\>|[^>])*>)',
             bygroups(Comment.Preproc, Whitespace, String.Double)),
            (r'(#(?:include|import))(\s+)("(?:\\\\|\\"|[^"])*")',
             bygroups(Comment.Preproc, Whitespace, String.Double)),
            (r'(#(?:include|import))(\s+)(<(?:\\\\|\\>|[^>])*>)',
             bygroups(Comment.Preproc, Whitespace, String.Double)),

            (r'#if\s+0', Comment.Preproc, 'if0'),
            (r'#', Comment.Preproc, 'macro'),

            (r'\s+', Whitespace),
            (r'(\\)(\n)',
                bygroups(String.Escape, Whitespace)),  # line continuation
            (r'//(\n|(.|\n)*?[^\\]\n)', Comment.Single),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),
            (r'<!--', Comment),
        ],
        'slashstartsregex': [
            include('whitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gim]+\b|\B)', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            default('#pop'),
        ],
        'badregex': [
            (r'\n', Whitespace, '#pop'),
        ],
        'statements': [
            (r'(L|@)?"', String, 'string'),
            (r"(L|@)?'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])'",
             String.Char),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[lL]?', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),
            (r'0x[0-9a-fA-F]+[Ll]?', Number.Hex),
            (r'0[0-7]+[Ll]?', Number.Oct),
            (r'\d+[Ll]?', Number.Integer),

            (r'^(?=\s|/|<!--)', Text, 'slashstartsregex'),

            (r'\+\+|--|~|&&|\?|:|\|\||\\(?=\n)|'
             r'(<<|>>>?|==?|!=?|[-<>+*%&|^/])=?',
             Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),

            (r'(for|in|while|do|break|return|continue|switch|case|default|if|'
             r'else|throw|try|catch|finally|new|delete|typeof|instanceof|void|'
             r'prototype|__proto__)\b', Keyword, 'slashstartsregex'),

            (r'(var|with|function)\b', Keyword.Declaration, 'slashstartsregex'),

            (r'(@selector|@private|@protected|@public|@encode|'
             r'@synchronized|@try|@throw|@catch|@finally|@end|@property|'
             r'@synthesize|@dynamic|@for|@accessors|new)\b', Keyword),

            (r'(int|long|float|short|double|char|unsigned|signed|void|'
             r'id|BOOL|bool|boolean|IBOutlet|IBAction|SEL|@outlet|@action)\b',
             Keyword.Type),

            (r'(self|super)\b', Name.Builtin),

            (r'(TRUE|YES|FALSE|NO|Nil|nil|NULL)\b', Keyword.Constant),
            (r'(true|false|null|NaN|Infinity|undefined)\b', Keyword.Constant),
            (r'(ABS|ASIN|ACOS|ATAN|ATAN2|SIN|COS|TAN|EXP|POW|CEIL|FLOOR|ROUND|'
             r'MIN|MAX|RAND|SQRT|E|LN2|LN10|LOG2E|LOG10E|PI|PI2|PI_2|SQRT1_2|'
             r'SQRT2)\b', Keyword.Constant),

            (r'(Array|Boolean|Date|Error|Function|Math|'
             r'Number|Object|RegExp|String|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'Error|eval|isFinite|isNaN|parseFloat|parseInt|document|this|'
             r'window|globalThis|Symbol)\b', Name.Builtin),

            (r'([$a-zA-Z_]\w*)(' + _ws + r')(?=\()',
             bygroups(Name.Function, using(this))),

            (r'[$a-zA-Z_]\w*', Name),
        ],
        'classname': [
            # interface definition that inherits
            (r'([a-zA-Z_]\w*)(' + _ws + r':' + _ws +
             r')([a-zA-Z_]\w*)?',
             bygroups(Name.Class, using(this), Name.Class), '#pop'),
            # interface definition for a category
            (r'([a-zA-Z_]\w*)(' + _ws + r'\()([a-zA-Z_]\w*)(\))',
             bygroups(Name.Class, using(this), Name.Label, Text), '#pop'),
            # simple interface / implementation
            (r'([a-zA-Z_]\w*)', Name.Class, '#pop'),
        ],
        'forward_classname': [
            (r'([a-zA-Z_]\w*)(\s*)(,)(\s*)',
             bygroups(Name.Class, Whitespace, Text, Whitespace), '#push'),
            (r'([a-zA-Z_]\w*)(\s*)(;?)',
             bygroups(Name.Class, Whitespace, Text), '#pop'),
        ],
        'function_signature': [
            include('whitespace'),

            # start of a selector w/ parameters
            (r'(\(' + _ws + r')'                # open paren
             r'([a-zA-Z_]\w+)'                  # return type
             r'(' + _ws + r'\)' + _ws + r')'    # close paren
             r'([$a-zA-Z_]\w+' + _ws + r':)',   # function name
             bygroups(using(this), Keyword.Type, using(this),
                      Name.Function), 'function_parameters'),

            # no-param function
            (r'(\(' + _ws + r')'                # open paren
             r'([a-zA-Z_]\w+)'                  # return type
             r'(' + _ws + r'\)' + _ws + r')'    # close paren
             r'([$a-zA-Z_]\w+)',                # function name
             bygroups(using(this), Keyword.Type, using(this),
                      Name.Function), "#pop"),

            # no return type given, start of a selector w/ parameters
            (r'([$a-zA-Z_]\w+' + _ws + r':)',   # function name
             bygroups(Name.Function), 'function_parameters'),

            # no return type given, no-param function
            (r'([$a-zA-Z_]\w+)',                # function name
             bygroups(Name.Function), "#pop"),

            default('#pop'),
        ],
        'function_parameters': [
            include('whitespace'),

            # parameters
            (r'(\(' + _ws + ')'                 # open paren
             r'([^)]+)'                        # type
             r'(' + _ws + r'\)' + _ws + r')'    # close paren
             r'([$a-zA-Z_]\w+)',      # param name
             bygroups(using(this), Keyword.Type, using(this), Text)),

            # one piece of a selector name
            (r'([$a-zA-Z_]\w+' + _ws + r':)',   # function name
             Name.Function),

            # smallest possible selector piece
            (r'(:)', Name.Function),

            # var args
            (r'(,' + _ws + r'\.\.\.)', using(this)),

            # param name
            (r'([$a-zA-Z_]\w+)', Text),
        ],
        'expression': [
            (r'([$a-zA-Z_]\w*)(\()', bygroups(Name.Function,
                                              Punctuation)),
            (r'(\))', Punctuation, "#pop"),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|[0-7]{1,3})', String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'(\\)(\n)', bygroups(String.Escape, Whitespace)),  # line continuation
            (r'\\', String),  # stray backslash
        ],
        'macro': [
            (r'[^/\n]+', Comment.Preproc),
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace), '#pop'),
            (r'/', Comment.Preproc),
            (r'(?<=\\)\n', Whitespace),
            (r'\n', Whitespace, '#pop'),
        ],
        'if0': [
            (r'^\s*#if.*?(?<!\\)\n', Comment.Preproc, '#push'),
            (r'^\s*#endif.*?(?<!\\)\n', Comment.Preproc, '#pop'),
            (r'(.*?)(\n)', bygroups(Comment, Whitespace)),
        ]
    }

    def analyse_text(text):
        if re.search(r'^\s*@import\s+[<"]', text, re.MULTILINE):
            # special directive found in most Objective-J files
            return True
        return False


class CoffeeScriptLexer(RegexLexer):
    """
    For CoffeeScript source code.
    """

    name = 'CoffeeScript'
    url = 'http://coffeescript.org'
    aliases = ['coffeescript', 'coffee-script', 'coffee']
    filenames = ['*.coffee']
    mimetypes = ['text/coffeescript']
    version_added = '1.3'

    _operator_re = (
        r'\+\+|~|&&|\band\b|\bor\b|\bis\b|\bisnt\b|\bnot\b|\?|:|'
        r'\|\||\\(?=\n)|'
        r'(<<|>>>?|==?(?!>)|!=?|=(?!>)|-(?!>)|[<>+*`%&|\^/])=?')

    flags = re.DOTALL
    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Whitespace),
            (r'###[^#].*?###', Comment.Multiline),
            (r'(#(?!##[^#]).*?)(\n)', bygroups(Comment.Single, Whitespace)),
        ],
        'multilineregex': [
            (r'[^/#]+', String.Regex),
            (r'///([gimuysd]+\b|\B)', String.Regex, '#pop'),
            (r'#\{', String.Interpol, 'interpoling_string'),
            (r'[/#]', String.Regex),
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'///', String.Regex, ('#pop', 'multilineregex')),
            (r'/(?! )(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gimuysd]+\b|\B)', String.Regex, '#pop'),
            # This isn't really guarding against mishighlighting well-formed
            # code, just the ability to infinite-loop between root and
            # slashstartsregex.
            (r'/', Operator, '#pop'),
            default('#pop'),
        ],
        'root': [
            include('commentsandwhitespace'),
            (r'\A(?=\s|/)', Text, 'slashstartsregex'),
            (_operator_re, Operator, 'slashstartsregex'),
            (r'(?:\([^()]*\))?\s*[=-]>', Name.Function, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(?<![.$])(for|own|in|of|while|until|'
             r'loop|break|return|continue|'
             r'switch|when|then|if|unless|else|'
             r'throw|try|catch|finally|new|delete|typeof|instanceof|super|'
             r'extends|this|class|by)\b', Keyword, 'slashstartsregex'),
            (r'(?<![.$])(true|false|yes|no|on|off|null|'
             r'NaN|Infinity|undefined)\b',
             Keyword.Constant),
            (r'(Array|Boolean|Date|Error|Function|Math|'
             r'Number|Object|RegExp|String|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'eval|isFinite|isNaN|parseFloat|parseInt|document|window|globalThis|Symbol)\b',
             Name.Builtin),
            (r'([$a-zA-Z_][\w.:$]*)(\s*)([:=])(\s+)',
                bygroups(Name.Variable, Whitespace, Operator, Whitespace),
                'slashstartsregex'),
            (r'(@[$a-zA-Z_][\w.:$]*)(\s*)([:=])(\s+)',
                bygroups(Name.Variable.Instance, Whitespace, Operator, Whitespace),
                'slashstartsregex'),
            (r'@', Name.Other, 'slashstartsregex'),
            (r'@?[$a-zA-Z_][\w$]*', Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            ('"""', String, 'tdqs'),
            ("'''", String, 'tsqs'),
            ('"', String, 'dqs'),
            ("'", String, 'sqs'),
        ],
        'strings': [
            (r'[^#\\\'"]+', String),
            # note that all coffee script strings are multi-line.
            # hashmarks, quotes and backslashes must be parsed one at a time
        ],
        'interpoling_string': [
            (r'\}', String.Interpol, "#pop"),
            include('root')
        ],
        'dqs': [
            (r'"', String, '#pop'),
            (r'\\.|\'', String),  # double-quoted string don't need ' escapes
            (r'#\{', String.Interpol, "interpoling_string"),
            (r'#', String),
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            (r'#|\\.|"', String),  # single quoted strings don't need " escapses
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            (r'\\.|\'|"', String),  # no need to escape quotes in triple-string
            (r'#\{', String.Interpol, "interpoling_string"),
            (r'#', String),
            include('strings'),
        ],
        'tsqs': [
            (r"'''", String, '#pop'),
            (r'#|\\.|\'|"', String),  # no need to escape quotes in triple-strings
            include('strings')
        ],
    }


class MaskLexer(RegexLexer):
    """
    For Mask markup.
    """
    name = 'Mask'
    url = 'https://github.com/atmajs/MaskJS'
    aliases = ['mask']
    filenames = ['*.mask']
    mimetypes = ['text/x-mask']
    version_added = '2.0'

    flags = re.MULTILINE | re.IGNORECASE | re.DOTALL
    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'[{};>]', Punctuation),
            (r"'''", String, 'string-trpl-single'),
            (r'"""', String, 'string-trpl-double'),
            (r"'", String, 'string-single'),
            (r'"', String, 'string-double'),
            (r'([\w-]+)', Name.Tag, 'node'),
            (r'([^.#;{>\s]+)', Name.Class, 'node'),
            (r'(#[\w-]+)', Name.Function, 'node'),
            (r'(\.[\w-]+)', Name.Variable.Class, 'node')
        ],
        'string-base': [
            (r'\\.', String.Escape),
            (r'~\[', String.Interpol, 'interpolation'),
            (r'.', String.Single),
        ],
        'string-single': [
            (r"'", String.Single, '#pop'),
            include('string-base')
        ],
        'string-double': [
            (r'"', String.Single, '#pop'),
            include('string-base')
        ],
        'string-trpl-single': [
            (r"'''", String.Single, '#pop'),
            include('string-base')
        ],
        'string-trpl-double': [
            (r'"""', String.Single, '#pop'),
            include('string-base')
        ],
        'interpolation': [
            (r'\]', String.Interpol, '#pop'),
            (r'(\s*)(:)', bygroups(Whitespace, String.Interpol), 'expression'),
            (r'(\s*)(\w+)(:)', bygroups(Whitespace, Name.Other, Punctuation)),
            (r'[^\]]+', String.Interpol)
        ],
        'expression': [
            (r'[^\]]+', using(JavascriptLexer), '#pop')
        ],
        'node': [
            (r'\s+', Whitespace),
            (r'\.', Name.Variable.Class, 'node-class'),
            (r'\#', Name.Function, 'node-id'),
            (r'(style)([ \t]*)(=)',
                bygroups(Name.Attribute, Whitespace, Operator),
                'node-attr-style-value'),
            (r'([\w:-]+)([ \t]*)(=)',
                bygroups(Name.Attribute, Whitespace, Operator),
                'node-attr-value'),
            (r'[\w:-]+', Name.Attribute),
            (r'[>{;]', Punctuation, '#pop')
        ],
        'node-class': [
            (r'[\w-]+', Name.Variable.Class),
            (r'~\[', String.Interpol, 'interpolation'),
            default('#pop')
        ],
        'node-id': [
            (r'[\w-]+', Name.Function),
            (r'~\[', String.Interpol, 'interpolation'),
            default('#pop')
        ],
        'node-attr-value': [
            (r'\s+', Whitespace),
            (r'\w+', Name.Variable, '#pop'),
            (r"'", String, 'string-single-pop2'),
            (r'"', String, 'string-double-pop2'),
            default('#pop')
        ],
        'node-attr-style-value': [
            (r'\s+', Whitespace),
            (r"'", String.Single, 'css-single-end'),
            (r'"', String.Single, 'css-double-end'),
            include('node-attr-value')
        ],
        'css-base': [
            (r'\s+', Whitespace),
            (r";", Punctuation),
            (r"[\w\-]+\s*:", Name.Builtin)
        ],
        'css-single-end': [
            include('css-base'),
            (r"'", String.Single, '#pop:2'),
            (r"[^;']+", Name.Entity)
        ],
        'css-double-end': [
            include('css-base'),
            (r'"', String.Single, '#pop:2'),
            (r'[^;"]+', Name.Entity)
        ],
        'string-single-pop2': [
            (r"'", String.Single, '#pop:2'),
            include('string-base')
        ],
        'string-double-pop2': [
            (r'"', String.Single, '#pop:2'),
            include('string-base')
        ],
    }


class EarlGreyLexer(RegexLexer):
    """
    For Earl-Grey source code.

    .. versionadded: 2.1
    """

    name = 'Earl Grey'
    aliases = ['earl-grey', 'earlgrey', 'eg']
    filenames = ['*.eg']
    mimetypes = ['text/x-earl-grey']
    url = 'https://github.com/breuleux/earl-grey'
    version_added = ''

    tokens = {
        'root': [
            (r'\n', Whitespace),
            include('control'),
            (r'[^\S\n]+', Text),
            (r'(;;.*)(\n)', bygroups(Comment, Whitespace)),
            (r'[\[\]{}:(),;]', Punctuation),
            (r'(\\)(\n)', bygroups(String.Escape, Whitespace)),
            (r'\\', Text),
            include('errors'),
            (words((
                'with', 'where', 'when', 'and', 'not', 'or', 'in',
                'as', 'of', 'is'),
                prefix=r'(?<=\s|\[)', suffix=r'(?![\w$\-])'),
             Operator.Word),
            (r'[*@]?->', Name.Function),
            (r'[+\-*/~^<>%&|?!@#.]*=', Operator.Word),
            (r'\.{2,3}', Operator.Word),  # Range Operator
            (r'([+*/~^<>&|?!]+)|([#\-](?=\s))|@@+(?=\s)|=+', Operator),
            (r'(?<![\w$\-])(var|let)(?:[^\w$])', Keyword.Declaration),
            include('keywords'),
            include('builtins'),
            include('assignment'),
            (r'''(?x)
                (?:()([a-zA-Z$_](?:[\w$\-]*[\w$])?)|
                   (?<=[\s{\[(])(\.)([a-zA-Z$_](?:[\w$\-]*[\w$])?))
                (?=.*%)''',
             bygroups(Punctuation, Name.Tag, Punctuation, Name.Class.Start), 'dbs'),
            (r'[rR]?`', String.Backtick, 'bt'),
            (r'[rR]?```', String.Backtick, 'tbt'),
            (r'(?<=[\s\[{(,;])\.([a-zA-Z$_](?:[\w$\-]*[\w$])?)'
             r'(?=[\s\]}),;])', String.Symbol),
            include('nested'),
            (r'(?:[rR]|[rR]\.[gmi]{1,3})?"', String, combined('stringescape', 'dqs')),
            (r'(?:[rR]|[rR]\.[gmi]{1,3})?\'', String, combined('stringescape', 'sqs')),
            (r'"""', String, combined('stringescape', 'tdqs')),
            include('tuple'),
            include('import_paths'),
            include('name'),
            include('numbers'),
        ],
        'dbs': [
            (r'(\.)([a-zA-Z$_](?:[\w$\-]*[\w$])?)(?=[.\[\s])',
             bygroups(Punctuation, Name.Class.DBS)),
            (r'(\[)([\^#][a-zA-Z$_](?:[\w$\-]*[\w$])?)(\])',
             bygroups(Punctuation, Name.Entity.DBS, Punctuation)),
            (r'\s+', Whitespace),
            (r'%', Operator.DBS, '#pop'),
        ],
        'import_paths': [
            (r'(?<=[\s:;,])(\.{1,3}(?:[\w\-]*/)*)(\w(?:[\w\-]*\w)*)(?=[\s;,])',
             bygroups(Text.Whitespace, Text)),
        ],
        'assignment': [
            (r'(\.)?([a-zA-Z$_](?:[\w$\-]*[\w$])?)'
             r'(?=\s+[+\-*/~^<>%&|?!@#.]*\=\s)',
             bygroups(Punctuation, Name.Variable))
        ],
        'errors': [
            (words(('Error', 'TypeError', 'ReferenceError'),
                   prefix=r'(?<![\w\-$.])', suffix=r'(?![\w\-$.])'),
             Name.Exception),
            (r'''(?x)
                (?<![\w$])
                E\.[\w$](?:[\w$\-]*[\w$])?
                (?:\.[\w$](?:[\w$\-]*[\w$])?)*
                (?=[({\[?!\s])''',
             Name.Exception),
        ],
        'control': [
            (r'''(?x)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)
                (?!\n)\s+
                (?!and|as|each\*|each|in|is|mod|of|or|when|where|with)
                (?=(?:[+\-*/~^<>%&|?!@#.])?[a-zA-Z$_](?:[\w$-]*[\w$])?)''',
             Keyword.Control),
            (r'([a-zA-Z$_](?:[\w$-]*[\w$])?)(?!\n)(\s+)(?=[\'"\d{\[(])',
             bygroups(Keyword.Control, Whitespace)),
            (r'''(?x)
                (?:
                    (?<=[%=])|
                    (?<=[=\-]>)|
                    (?<=with|each|with)|
                    (?<=each\*|where)
                )(\s+)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)(:)''',
             bygroups(Whitespace, Keyword.Control, Punctuation)),
            (r'''(?x)
                (?<![+\-*/~^<>%&|?!@#.])(\s+)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)(:)''',
             bygroups(Whitespace, Keyword.Control, Punctuation)),
        ],
        'nested': [
            (r'''(?x)
                (?<=[\w$\]})])(\.)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)
                (?=\s+with(?:\s|\n))''',
             bygroups(Punctuation, Name.Function)),
            (r'''(?x)
                (?<!\s)(\.)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)
                (?=[}\]).,;:\s])''',
             bygroups(Punctuation, Name.Field)),
            (r'''(?x)
                (?<=[\w$\]})])(\.)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)
                (?=[\[{(:])''',
             bygroups(Punctuation, Name.Function)),
        ],
        'keywords': [
            (words((
                'each', 'each*', 'mod', 'await', 'break', 'chain',
                'continue', 'elif', 'expr-value', 'if', 'match',
                'return', 'yield', 'pass', 'else', 'require', 'var',
                'let', 'async', 'method', 'gen'),
                prefix=r'(?<![\w\-$.])', suffix=r'(?![\w\-$.])'),
             Keyword.Pseudo),
            (words(('this', 'self', '@'),
                   prefix=r'(?<![\w\-$.])', suffix=r'(?![\w\-$])'),
             Keyword.Constant),
            (words((
                'Function', 'Object', 'Array', 'String', 'Number',
                'Boolean', 'ErrorFactory', 'ENode', 'Promise'),
                prefix=r'(?<![\w\-$.])', suffix=r'(?![\w\-$])'),
             Keyword.Type),
        ],
        'builtins': [
            (words((
                'send', 'object', 'keys', 'items', 'enumerate', 'zip',
                'product', 'neighbours', 'predicate', 'equal',
                'nequal', 'contains', 'repr', 'clone', 'range',
                'getChecker', 'get-checker', 'getProperty', 'get-property',
                'getProjector', 'get-projector', 'consume', 'take',
                'promisify', 'spawn', 'constructor'),
                prefix=r'(?<![\w\-#.])', suffix=r'(?![\w\-.])'),
             Name.Builtin),
            (words((
                'true', 'false', 'null', 'undefined'),
                prefix=r'(?<![\w\-$.])', suffix=r'(?![\w\-$.])'),
             Name.Constant),
        ],
        'name': [
            (r'@([a-zA-Z$_](?:[\w$-]*[\w$])?)', Name.Variable.Instance),
            (r'([a-zA-Z$_](?:[\w$-]*[\w$])?)(\+\+|\-\-)?',
             bygroups(Name.Symbol, Operator.Word))
        ],
        'tuple': [
            (r'#[a-zA-Z_][\w\-]*(?=[\s{(,;])', Name.Namespace)
        ],
        'interpoling_string': [
            (r'\}', String.Interpol, '#pop'),
            include('root')
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'strings': [
            (r'[^\\\'"]', String),
            (r'[\'"\\]', String),
            (r'\n', String)  # All strings are multiline in EG
        ],
        'dqs': [
            (r'"', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),
            (r'\{', String.Interpol, 'interpoling_string'),
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            include('strings'),
        ],
        'bt': [
            (r'`', String.Backtick, '#pop'),
            (r'(?<!`)\n', String.Backtick),
            (r'\^=?', String.Escape),
            (r'.+', String.Backtick),
        ],
        'tbt': [
            (r'```', String.Backtick, '#pop'),
            (r'\n', String.Backtick),
            (r'\^=?', String.Escape),
            (r'[^`]+', String.Backtick),
        ],
        'numbers': [
            (r'\d+\.(?!\.)\d*([eE][+-]?[0-9]+)?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+', Number.Float),
            (r'8r[0-7]+', Number.Oct),
            (r'2r[01]+', Number.Bin),
            (r'16r[a-fA-F0-9]+', Number.Hex),
            (r'([3-79]|[12][0-9]|3[0-6])r[a-zA-Z\d]+(\.[a-zA-Z\d]+)?',
             Number.Radix),
            (r'\d+', Number.Integer)
        ],
    }


class JuttleLexer(RegexLexer):
    """
    For Juttle source code.
    """

    name = 'Juttle'
    url = 'http://juttle.github.io/'
    aliases = ['juttle']
    filenames = ['*.juttle']
    mimetypes = ['application/juttle', 'application/x-juttle',
                 'text/x-juttle', 'text/juttle']
    version_added = '2.2'

    flags = re.DOTALL | re.MULTILINE

    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Whitespace),
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'/\*.*?\*/', Comment.Multiline)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gimuysd]+\b|\B)', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            default('#pop')
        ],
        'badregex': [
            (r'\n', Text, '#pop')
        ],
        'root': [
            (r'^(?=\s|/)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),
            (r':\d{2}:\d{2}:\d{2}(\.\d*)?:', String.Moment),
            (r':(now|beginning|end|forever|yesterday|today|tomorrow|'
             r'(\d+(\.\d*)?|\.\d+)(ms|[smhdwMy])?):', String.Moment),
            (r':\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d*)?)?'
             r'(Z|[+-]\d{2}:\d{2}|[+-]\d{4})?:', String.Moment),
            (r':((\d+(\.\d*)?|\.\d+)[ ]+)?(millisecond|second|minute|hour|'
             r'day|week|month|year)[s]?'
             r'(([ ]+and[ ]+(\d+[ ]+)?(millisecond|second|minute|hour|'
             r'day|week|month|year)[s]?)'
             r'|[ ]+(ago|from[ ]+now))*:', String.Moment),
            (r'\+\+|--|~|&&|\?|:|\|\||\\(?=\n)|'
             r'(==?|!=?|[-<>+*%&|^/])=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(import|return|continue|if|else)\b', Keyword, 'slashstartsregex'),
            (r'(var|const|function|reducer|sub|input)\b', Keyword.Declaration,
             'slashstartsregex'),
            (r'(batch|emit|filter|head|join|keep|pace|pass|put|read|reduce|remove|'
             r'sequence|skip|sort|split|tail|unbatch|uniq|view|write)\b',
             Keyword.Reserved),
            (r'(true|false|null|Infinity)\b', Keyword.Constant),
            (r'(Array|Date|Juttle|Math|Number|Object|RegExp|String)\b',
             Name.Builtin),
            (JS_IDENT, Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
        ]

    }


class NodeConsoleLexer(Lexer):
    """
    For parsing within an interactive Node.js REPL, such as:

    .. sourcecode:: nodejsrepl

        > let a = 3
        undefined
        > a
        3
        > let b = '4'
        undefined
        > b
        '4'
        > b == a
        false

    .. versionadded: 2.10
    """
    name = 'Node.js REPL console session'
    aliases = ['nodejsrepl', ]
    mimetypes = ['text/x-nodejsrepl', ]
    url = 'https://nodejs.org'
    version_added = ''

    def get_tokens_unprocessed(self, text):
        jslexer = JavascriptLexer(**self.options)

        curcode = ''
        insertions = []

        for match in line_re.finditer(text):
            line = match.group()
            if line.startswith('> '):
                insertions.append((len(curcode),
                    [(0, Generic.Prompt, line[:1]),
                     (1, Whitespace, line[1:2])]))

                curcode += line[2:]
            elif line.startswith('...'):
                # node does a nested ... thing depending on depth
                code = line.lstrip('.')
                lead = len(line) - len(code)

                insertions.append((len(curcode),
                    [(0, Generic.Prompt, line[:lead])]))

                curcode += code
            else:
                if curcode:
                    yield from do_insertions(insertions,
                        jslexer.get_tokens_unprocessed(curcode))

                    curcode = ''
                    insertions = []

                yield from do_insertions([],
                    jslexer.get_tokens_unprocessed(line))

        if curcode:
            yield from do_insertions(insertions,
                jslexer.get_tokens_unprocessed(curcode))

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\runtime.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Runtime
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class ScriptId(str):
    '''
    Unique script identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> ScriptId:
        return cls(json)

    def __repr__(self):
        return 'ScriptId({})'.format(super().__repr__())


@dataclass
class SerializationOptions:
    '''
    Represents options for serialization. Overrides ``generatePreview`` and ``returnByValue``.
    '''
    serialization: str

    #: Deep serialization depth. Default is full depth. Respected only in ``deep`` serialization mode.
    max_depth: typing.Optional[int] = None

    #: Embedder-specific parameters. For example if connected to V8 in Chrome these control DOM
    #: serialization via ``maxNodeDepth: integer`` and ``includeShadowTree: "none" `` "open" `` "all"``.
    #: Values can be only of type string or integer.
    additional_parameters: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['serialization'] = self.serialization
        if self.max_depth is not None:
            json['maxDepth'] = self.max_depth
        if self.additional_parameters is not None:
            json['additionalParameters'] = self.additional_parameters
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            serialization=str(json['serialization']),
            max_depth=int(json['maxDepth']) if 'maxDepth' in json else None,
            additional_parameters=dict(json['additionalParameters']) if 'additionalParameters' in json else None,
        )


@dataclass
class DeepSerializedValue:
    '''
    Represents deep serialized value.
    '''
    type_: str

    value: typing.Optional[typing.Any] = None

    object_id: typing.Optional[str] = None

    #: Set if value reference met more then once during serialization. In such
    #: case, value is provided only to one of the serialized values. Unique
    #: per value in the scope of one CDP call.
    weak_local_object_reference: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.value is not None:
            json['value'] = self.value
        if self.object_id is not None:
            json['objectId'] = self.object_id
        if self.weak_local_object_reference is not None:
            json['weakLocalObjectReference'] = self.weak_local_object_reference
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            value=json['value'] if 'value' in json else None,
            object_id=str(json['objectId']) if 'objectId' in json else None,
            weak_local_object_reference=int(json['weakLocalObjectReference']) if 'weakLocalObjectReference' in json else None,
        )


class RemoteObjectId(str):
    '''
    Unique object identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RemoteObjectId:
        return cls(json)

    def __repr__(self):
        return 'RemoteObjectId({})'.format(super().__repr__())


class UnserializableValue(str):
    '''
    Primitive value which cannot be JSON-stringified. Includes values ``-0``, ``NaN``, ``Infinity``,
    ``-Infinity``, and bigint literals.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UnserializableValue:
        return cls(json)

    def __repr__(self):
        return 'UnserializableValue({})'.format(super().__repr__())


@dataclass
class RemoteObject:
    '''
    Mirror object referencing original JavaScript object.
    '''
    #: Object type.
    type_: str

    #: Object subtype hint. Specified for ``object`` type values only.
    #: NOTE: If you change anything here, make sure to also update
    #: ``subtype`` in ``ObjectPreview`` and ``PropertyPreview`` below.
    subtype: typing.Optional[str] = None

    #: Object class (constructor) name. Specified for ``object`` type values only.
    class_name: typing.Optional[str] = None

    #: Remote object value in case of primitive values or JSON values (if it was requested).
    value: typing.Optional[typing.Any] = None

    #: Primitive value which can not be JSON-stringified does not have ``value``, but gets this
    #: property.
    unserializable_value: typing.Optional[UnserializableValue] = None

    #: String representation of the object.
    description: typing.Optional[str] = None

    #: Deep serialized value.
    deep_serialized_value: typing.Optional[DeepSerializedValue] = None

    #: Unique object identifier (for non-primitive values).
    object_id: typing.Optional[RemoteObjectId] = None

    #: Preview containing abbreviated property values. Specified for ``object`` type values only.
    preview: typing.Optional[ObjectPreview] = None

    custom_preview: typing.Optional[CustomPreview] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.subtype is not None:
            json['subtype'] = self.subtype
        if self.class_name is not None:
            json['className'] = self.class_name
        if self.value is not None:
            json['value'] = self.value
        if self.unserializable_value is not None:
            json['unserializableValue'] = self.unserializable_value.to_json()
        if self.description is not None:
            json['description'] = self.description
        if self.deep_serialized_value is not None:
            json['deepSerializedValue'] = self.deep_serialized_value.to_json()
        if self.object_id is not None:
            json['objectId'] = self.object_id.to_json()
        if self.preview is not None:
            json['preview'] = self.preview.to_json()
        if self.custom_preview is not None:
            json['customPreview'] = self.custom_preview.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            subtype=str(json['subtype']) if 'subtype' in json else None,
            class_name=str(json['className']) if 'className' in json else None,
            value=json['value'] if 'value' in json else None,
            unserializable_value=UnserializableValue.from_json(json['unserializableValue']) if 'unserializableValue' in json else None,
            description=str(json['description']) if 'description' in json else None,
            deep_serialized_value=DeepSerializedValue.from_json(json['deepSerializedValue']) if 'deepSerializedValue' in json else None,
            object_id=RemoteObjectId.from_json(json['objectId']) if 'objectId' in json else None,
            preview=ObjectPreview.from_json(json['preview']) if 'preview' in json else None,
            custom_preview=CustomPreview.from_json(json['customPreview']) if 'customPreview' in json else None,
        )


@dataclass
class CustomPreview:
    #: The JSON-stringified result of formatter.header(object, config) call.
    #: It contains json ML array that represents RemoteObject.
    header: str

    #: If formatter returns true as a result of formatter.hasBody call then bodyGetterId will
    #: contain RemoteObjectId for the function that returns result of formatter.body(object, config) call.
    #: The result value is json ML array.
    body_getter_id: typing.Optional[RemoteObjectId] = None

    def to_json(self):
        json = dict()
        json['header'] = self.header
        if self.body_getter_id is not None:
            json['bodyGetterId'] = self.body_getter_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            header=str(json['header']),
            body_getter_id=RemoteObjectId.from_json(json['bodyGetterId']) if 'bodyGetterId' in json else None,
        )


@dataclass
class ObjectPreview:
    '''
    Object containing abbreviated remote object value.
    '''
    #: Object type.
    type_: str

    #: True iff some of the properties or entries of the original object did not fit.
    overflow: bool

    #: List of the properties.
    properties: typing.List[PropertyPreview]

    #: Object subtype hint. Specified for ``object`` type values only.
    subtype: typing.Optional[str] = None

    #: String representation of the object.
    description: typing.Optional[str] = None

    #: List of the entries. Specified for ``map`` and ``set`` subtype values only.
    entries: typing.Optional[typing.List[EntryPreview]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['overflow'] = self.overflow
        json['properties'] = [i.to_json() for i in self.properties]
        if self.subtype is not None:
            json['subtype'] = self.subtype
        if self.description is not None:
            json['description'] = self.description
        if self.entries is not None:
            json['entries'] = [i.to_json() for i in self.entries]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            overflow=bool(json['overflow']),
            properties=[PropertyPreview.from_json(i) for i in json['properties']],
            subtype=str(json['subtype']) if 'subtype' in json else None,
            description=str(json['description']) if 'description' in json else None,
            entries=[EntryPreview.from_json(i) for i in json['entries']] if 'entries' in json else None,
        )


@dataclass
class PropertyPreview:
    #: Property name.
    name: str

    #: Object type. Accessor means that the property itself is an accessor property.
    type_: str

    #: User-friendly property value string.
    value: typing.Optional[str] = None

    #: Nested value preview.
    value_preview: typing.Optional[ObjectPreview] = None

    #: Object subtype hint. Specified for ``object`` type values only.
    subtype: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['type'] = self.type_
        if self.value is not None:
            json['value'] = self.value
        if self.value_preview is not None:
            json['valuePreview'] = self.value_preview.to_json()
        if self.subtype is not None:
            json['subtype'] = self.subtype
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            type_=str(json['type']),
            value=str(json['value']) if 'value' in json else None,
            value_preview=ObjectPreview.from_json(json['valuePreview']) if 'valuePreview' in json else None,
            subtype=str(json['subtype']) if 'subtype' in json else None,
        )


@dataclass
class EntryPreview:
    #: Preview of the value.
    value: ObjectPreview

    #: Preview of the key. Specified for map-like collection entries.
    key: typing.Optional[ObjectPreview] = None

    def to_json(self):
        json = dict()
        json['value'] = self.value.to_json()
        if self.key is not None:
            json['key'] = self.key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=ObjectPreview.from_json(json['value']),
            key=ObjectPreview.from_json(json['key']) if 'key' in json else None,
        )


@dataclass
class PropertyDescriptor:
    '''
    Object property descriptor.
    '''
    #: Property name or symbol description.
    name: str

    #: True if the type of this property descriptor may be changed and if the property may be
    #: deleted from the corresponding object.
    configurable: bool

    #: True if this property shows up during enumeration of the properties on the corresponding
    #: object.
    enumerable: bool

    #: The value associated with the property.
    value: typing.Optional[RemoteObject] = None

    #: True if the value associated with the property may be changed (data descriptors only).
    writable: typing.Optional[bool] = None

    #: A function which serves as a getter for the property, or ``undefined`` if there is no getter
    #: (accessor descriptors only).
    get: typing.Optional[RemoteObject] = None

    #: A function which serves as a setter for the property, or ``undefined`` if there is no setter
    #: (accessor descriptors only).
    set_: typing.Optional[RemoteObject] = None

    #: True if the result was thrown during the evaluation.
    was_thrown: typing.Optional[bool] = None

    #: True if the property is owned for the object.
    is_own: typing.Optional[bool] = None

    #: Property symbol object, if the property is of the ``symbol`` type.
    symbol: typing.Optional[RemoteObject] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['configurable'] = self.configurable
        json['enumerable'] = self.enumerable
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.writable is not None:
            json['writable'] = self.writable
        if self.get is not None:
            json['get'] = self.get.to_json()
        if self.set_ is not None:
            json['set'] = self.set_.to_json()
        if self.was_thrown is not None:
            json['wasThrown'] = self.was_thrown
        if self.is_own is not None:
            json['isOwn'] = self.is_own
        if self.symbol is not None:
            json['symbol'] = self.symbol.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            configurable=bool(json['configurable']),
            enumerable=bool(json['enumerable']),
            value=RemoteObject.from_json(json['value']) if 'value' in json else None,
            writable=bool(json['writable']) if 'writable' in json else None,
            get=RemoteObject.from_json(json['get']) if 'get' in json else None,
            set_=RemoteObject.from_json(json['set']) if 'set' in json else None,
            was_thrown=bool(json['wasThrown']) if 'wasThrown' in json else None,
            is_own=bool(json['isOwn']) if 'isOwn' in json else None,
            symbol=RemoteObject.from_json(json['symbol']) if 'symbol' in json else None,
        )


@dataclass
class InternalPropertyDescriptor:
    '''
    Object internal property descriptor. This property isn't normally visible in JavaScript code.
    '''
    #: Conventional property name.
    name: str

    #: The value associated with the property.
    value: typing.Optional[RemoteObject] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        if self.value is not None:
            json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=RemoteObject.from_json(json['value']) if 'value' in json else None,
        )


@dataclass
class PrivatePropertyDescriptor:
    '''
    Object private field descriptor.
    '''
    #: Private property name.
    name: str

    #: The value associated with the private property.
    value: typing.Optional[RemoteObject] = None

    #: A function which serves as a getter for the private property,
    #: or ``undefined`` if there is no getter (accessor descriptors only).
    get: typing.Optional[RemoteObject] = None

    #: A function which serves as a setter for the private property,
    #: or ``undefined`` if there is no setter (accessor descriptors only).
    set_: typing.Optional[RemoteObject] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.get is not None:
            json['get'] = self.get.to_json()
        if self.set_ is not None:
            json['set'] = self.set_.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=RemoteObject.from_json(json['value']) if 'value' in json else None,
            get=RemoteObject.from_json(json['get']) if 'get' in json else None,
            set_=RemoteObject.from_json(json['set']) if 'set' in json else None,
        )


@dataclass
class CallArgument:
    '''
    Represents function call argument. Either remote object id ``objectId``, primitive ``value``,
    unserializable primitive value or neither of (for undefined) them should be specified.
    '''
    #: Primitive value or serializable javascript object.
    value: typing.Optional[typing.Any] = None

    #: Primitive value which can not be JSON-stringified.
    unserializable_value: typing.Optional[UnserializableValue] = None

    #: Remote object handle.
    object_id: typing.Optional[RemoteObjectId] = None

    def to_json(self):
        json = dict()
        if self.value is not None:
            json['value'] = self.value
        if self.unserializable_value is not None:
            json['unserializableValue'] = self.unserializable_value.to_json()
        if self.object_id is not None:
            json['objectId'] = self.object_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=json['value'] if 'value' in json else None,
            unserializable_value=UnserializableValue.from_json(json['unserializableValue']) if 'unserializableValue' in json else None,
            object_id=RemoteObjectId.from_json(json['objectId']) if 'objectId' in json else None,
        )


class ExecutionContextId(int):
    '''
    Id of an execution context.
    '''
    def to_json(self) -> int:
        return self

    @classmethod
    def from_json(cls, json: int) -> ExecutionContextId:
        return cls(json)

    def __repr__(self):
        return 'ExecutionContextId({})'.format(super().__repr__())


@dataclass
class ExecutionContextDescription:
    '''
    Description of an isolated world.
    '''
    #: Unique id of the execution context. It can be used to specify in which execution context
    #: script evaluation should be performed.
    id_: ExecutionContextId

    #: Execution context origin.
    origin: str

    #: Human readable name describing given context.
    name: str

    #: A system-unique execution context identifier. Unlike the id, this is unique across
    #: multiple processes, so can be reliably used to identify specific context while backend
    #: performs a cross-process navigation.
    unique_id: str

    #: Embedder-specific auxiliary data likely matching {isDefault: boolean, type: 'default'``'isolated'``'worker', frameId: string}
    aux_data: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_.to_json()
        json['origin'] = self.origin
        json['name'] = self.name
        json['uniqueId'] = self.unique_id
        if self.aux_data is not None:
            json['auxData'] = self.aux_data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=ExecutionContextId.from_json(json['id']),
            origin=str(json['origin']),
            name=str(json['name']),
            unique_id=str(json['uniqueId']),
            aux_data=dict(json['auxData']) if 'auxData' in json else None,
        )


@dataclass
class ExceptionDetails:
    '''
    Detailed information about exception (or error) that was thrown during script compilation or
    execution.
    '''
    #: Exception id.
    exception_id: int

    #: Exception text, which should be used together with exception object when available.
    text: str

    #: Line number of the exception location (0-based).
    line_number: int

    #: Column number of the exception location (0-based).
    column_number: int

    #: Script ID of the exception location.
    script_id: typing.Optional[ScriptId] = None

    #: URL of the exception location, to be used when the script was not reported.
    url: typing.Optional[str] = None

    #: JavaScript stack trace if available.
    stack_trace: typing.Optional[StackTrace] = None

    #: Exception object if available.
    exception: typing.Optional[RemoteObject] = None

    #: Identifier of the context where exception happened.
    execution_context_id: typing.Optional[ExecutionContextId] = None

    #: Dictionary with entries of meta data that the client associated
    #: with this exception, such as information about associated network
    #: requests, etc.
    exception_meta_data: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['exceptionId'] = self.exception_id
        json['text'] = self.text
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        if self.script_id is not None:
            json['scriptId'] = self.script_id.to_json()
        if self.url is not None:
            json['url'] = self.url
        if self.stack_trace is not None:
            json['stackTrace'] = self.stack_trace.to_json()
        if self.exception is not None:
            json['exception'] = self.exception.to_json()
        if self.execution_context_id is not None:
            json['executionContextId'] = self.execution_context_id.to_json()
        if self.exception_meta_data is not None:
            json['exceptionMetaData'] = self.exception_meta_data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            exception_id=int(json['exceptionId']),
            text=str(json['text']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
            script_id=ScriptId.from_json(json['scriptId']) if 'scriptId' in json else None,
            url=str(json['url']) if 'url' in json else None,
            stack_trace=StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            exception=RemoteObject.from_json(json['exception']) if 'exception' in json else None,
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']) if 'executionContextId' in json else None,
            exception_meta_data=dict(json['exceptionMetaData']) if 'exceptionMetaData' in json else None,
        )


class Timestamp(float):
    '''
    Number of milliseconds since epoch.
    '''
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> Timestamp:
        return cls(json)

    def __repr__(self):
        return 'Timestamp({})'.format(super().__repr__())


class TimeDelta(float):
    '''
    Number of milliseconds.
    '''
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> TimeDelta:
        return cls(json)

    def __repr__(self):
        return 'TimeDelta({})'.format(super().__repr__())


@dataclass
class CallFrame:
    '''
    Stack entry for runtime errors and assertions.
    '''
    #: JavaScript function name.
    function_name: str

    #: JavaScript script id.
    script_id: ScriptId

    #: JavaScript script name or url.
    url: str

    #: JavaScript script line number (0-based).
    line_number: int

    #: JavaScript script column number (0-based).
    column_number: int

    def to_json(self):
        json = dict()
        json['functionName'] = self.function_name
        json['scriptId'] = self.script_id.to_json()
        json['url'] = self.url
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            function_name=str(json['functionName']),
            script_id=ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
        )


@dataclass
class StackTrace:
    '''
    Call frames for assertions or error messages.
    '''
    #: JavaScript function name.
    call_frames: typing.List[CallFrame]

    #: String label of this stack trace. For async traces this may be a name of the function that
    #: initiated the async call.
    description: typing.Optional[str] = None

    #: Asynchronous JavaScript stack trace that preceded this stack, if available.
    parent: typing.Optional[StackTrace] = None

    #: Asynchronous JavaScript stack trace that preceded this stack, if available.
    parent_id: typing.Optional[StackTraceId] = None

    def to_json(self):
        json = dict()
        json['callFrames'] = [i.to_json() for i in self.call_frames]
        if self.description is not None:
            json['description'] = self.description
        if self.parent is not None:
            json['parent'] = self.parent.to_json()
        if self.parent_id is not None:
            json['parentId'] = self.parent_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            call_frames=[CallFrame.from_json(i) for i in json['callFrames']],
            description=str(json['description']) if 'description' in json else None,
            parent=StackTrace.from_json(json['parent']) if 'parent' in json else None,
            parent_id=StackTraceId.from_json(json['parentId']) if 'parentId' in json else None,
        )


class UniqueDebuggerId(str):
    '''
    Unique identifier of current debugger.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UniqueDebuggerId:
        return cls(json)

    def __repr__(self):
        return 'UniqueDebuggerId({})'.format(super().__repr__())


@dataclass
class StackTraceId:
    '''
    If ``debuggerId`` is set stack trace comes from another debugger and can be resolved there. This
    allows to track cross-debugger calls. See ``Runtime.StackTrace`` and ``Debugger.paused`` for usages.
    '''
    id_: str

    debugger_id: typing.Optional[UniqueDebuggerId] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_
        if self.debugger_id is not None:
            json['debuggerId'] = self.debugger_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=str(json['id']),
            debugger_id=UniqueDebuggerId.from_json(json['debuggerId']) if 'debuggerId' in json else None,
        )


def await_promise(
        promise_object_id: RemoteObjectId,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Add handler to promise with given promise object id.

    :param promise_object_id: Identifier of the promise.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object that should be sent by value.
    :param generate_preview: *(Optional)* Whether preview should be generated for the result.
    :returns: A tuple with the following items:

        0. **result** - Promise result. Will contain rejected value if promise was rejected.
        1. **exceptionDetails** - *(Optional)* Exception details if stack strace is available.
    '''
    params: T_JSON_DICT = dict()
    params['promiseObjectId'] = promise_object_id.to_json()
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.awaitPromise',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def call_function_on(
        function_declaration: str,
        object_id: typing.Optional[RemoteObjectId] = None,
        arguments: typing.Optional[typing.List[CallArgument]] = None,
        silent: typing.Optional[bool] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        user_gesture: typing.Optional[bool] = None,
        await_promise: typing.Optional[bool] = None,
        execution_context_id: typing.Optional[ExecutionContextId] = None,
        object_group: typing.Optional[str] = None,
        throw_on_side_effect: typing.Optional[bool] = None,
        unique_context_id: typing.Optional[str] = None,
        serialization_options: typing.Optional[SerializationOptions] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Calls function with given declaration on the given object. Object group of the result is
    inherited from the target object.

    :param function_declaration: Declaration of the function to call.
    :param object_id: *(Optional)* Identifier of the object to call function on. Either objectId or executionContextId should be specified.
    :param arguments: *(Optional)* Call arguments. All call arguments must belong to the same JavaScript world as the target object.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ```setPauseOnException```` state.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object which should be sent by value. Can be overriden by ````serializationOptions````.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the result.
    :param user_gesture: *(Optional)* Whether execution should be treated as initiated by user in the UI.
    :param await_promise: *(Optional)* Whether execution should ````await```` for resulting value and return once awaited promise is resolved.
    :param execution_context_id: *(Optional)* Specifies execution context which global object will be used to call function on. Either executionContextId or objectId should be specified.
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects. If objectGroup is not specified and objectId is, objectGroup will be inherited from object.
    :param throw_on_side_effect: **(EXPERIMENTAL)** *(Optional)* Whether to throw an exception if side effect cannot be ruled out during evaluation.
    :param unique_context_id: **(EXPERIMENTAL)** *(Optional)* An alternative way to specify the execution context to call function on. Compared to contextId that may be reused across processes, this is guaranteed to be system-unique, so it can be used to prevent accidental function call in context different than intended (e.g. as a result of navigation across process boundaries). This is mutually exclusive with ````executionContextId````.
    :param serialization_options: **(EXPERIMENTAL)** *(Optional)* Specifies the result serialization. If provided, overrides ````generatePreview```` and ````returnByValue```.
    :returns: A tuple with the following items:

        0. **result** - Call result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['functionDeclaration'] = function_declaration
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    if arguments is not None:
        params['arguments'] = [i.to_json() for i in arguments]
    if silent is not None:
        params['silent'] = silent
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if user_gesture is not None:
        params['userGesture'] = user_gesture
    if await_promise is not None:
        params['awaitPromise'] = await_promise
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    if throw_on_side_effect is not None:
        params['throwOnSideEffect'] = throw_on_side_effect
    if unique_context_id is not None:
        params['uniqueContextId'] = unique_context_id
    if serialization_options is not None:
        params['serializationOptions'] = serialization_options.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.callFunctionOn',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def compile_script(
        expression: str,
        source_url: str,
        persist_script: bool,
        execution_context_id: typing.Optional[ExecutionContextId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[ScriptId], typing.Optional[ExceptionDetails]]]:
    '''
    Compiles expression.

    :param expression: Expression to compile.
    :param source_url: Source url to be set for the script.
    :param persist_script: Specifies whether the compiled script should be persisted.
    :param execution_context_id: *(Optional)* Specifies in which execution context to perform script run. If the parameter is omitted the evaluation will be performed in the context of the inspected page.
    :returns: A tuple with the following items:

        0. **scriptId** - *(Optional)* Id of the script.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['expression'] = expression
    params['sourceURL'] = source_url
    params['persistScript'] = persist_script
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.compileScript',
        'params': params,
    }
    json = yield cmd_dict
    return (
        ScriptId.from_json(json['scriptId']) if 'scriptId' in json else None,
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables reporting of execution contexts creation.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.disable',
    }
    json = yield cmd_dict


def discard_console_entries() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Discards collected exceptions and console API calls.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.discardConsoleEntries',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables reporting of execution contexts creation by means of ``executionContextCreated`` event.
    When the reporting gets enabled the event will be sent immediately for each existing execution
    context.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.enable',
    }
    json = yield cmd_dict


def evaluate(
        expression: str,
        object_group: typing.Optional[str] = None,
        include_command_line_api: typing.Optional[bool] = None,
        silent: typing.Optional[bool] = None,
        context_id: typing.Optional[ExecutionContextId] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        user_gesture: typing.Optional[bool] = None,
        await_promise: typing.Optional[bool] = None,
        throw_on_side_effect: typing.Optional[bool] = None,
        timeout: typing.Optional[TimeDelta] = None,
        disable_breaks: typing.Optional[bool] = None,
        repl_mode: typing.Optional[bool] = None,
        allow_unsafe_eval_blocked_by_csp: typing.Optional[bool] = None,
        unique_context_id: typing.Optional[str] = None,
        serialization_options: typing.Optional[SerializationOptions] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Evaluates expression on global object.

    :param expression: Expression to evaluate.
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects.
    :param include_command_line_api: *(Optional)* Determines whether Command Line API should be available during the evaluation.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ```setPauseOnException```` state.
    :param context_id: *(Optional)* Specifies in which execution context to perform evaluation. If the parameter is omitted the evaluation will be performed in the context of the inspected page. This is mutually exclusive with ````uniqueContextId````, which offers an alternative way to identify the execution context that is more reliable in a multi-process environment.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object that should be sent by value.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the result.
    :param user_gesture: *(Optional)* Whether execution should be treated as initiated by user in the UI.
    :param await_promise: *(Optional)* Whether execution should ````await```` for resulting value and return once awaited promise is resolved.
    :param throw_on_side_effect: **(EXPERIMENTAL)** *(Optional)* Whether to throw an exception if side effect cannot be ruled out during evaluation. This implies ````disableBreaks```` below.
    :param timeout: **(EXPERIMENTAL)** *(Optional)* Terminate execution after timing out (number of milliseconds).
    :param disable_breaks: **(EXPERIMENTAL)** *(Optional)* Disable breakpoints during execution.
    :param repl_mode: **(EXPERIMENTAL)** *(Optional)* Setting this flag to true enables ````let```` re-declaration and top-level ````await````. Note that ````let```` variables can only be re-declared if they originate from ````replMode```` themselves.
    :param allow_unsafe_eval_blocked_by_csp: **(EXPERIMENTAL)** *(Optional)* The Content Security Policy (CSP) for the target might block 'unsafe-eval' which includes eval(), Function(), setTimeout() and setInterval() when called with non-callable arguments. This flag bypasses CSP for this evaluation and allows unsafe-eval. Defaults to true.
    :param unique_context_id: **(EXPERIMENTAL)** *(Optional)* An alternative way to specify the execution context to evaluate in. Compared to contextId that may be reused across processes, this is guaranteed to be system-unique, so it can be used to prevent accidental evaluation of the expression in context different than intended (e.g. as a result of navigation across process boundaries). This is mutually exclusive with ````contextId````.
    :param serialization_options: **(EXPERIMENTAL)** *(Optional)* Specifies the result serialization. If provided, overrides ````generatePreview```` and ````returnByValue```.
    :returns: A tuple with the following items:

        0. **result** - Evaluation result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['expression'] = expression
    if object_group is not None:
        params['objectGroup'] = object_group
    if include_command_line_api is not None:
        params['includeCommandLineAPI'] = include_command_line_api
    if silent is not None:
        params['silent'] = silent
    if context_id is not None:
        params['contextId'] = context_id.to_json()
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if user_gesture is not None:
        params['userGesture'] = user_gesture
    if await_promise is not None:
        params['awaitPromise'] = await_promise
    if throw_on_side_effect is not None:
        params['throwOnSideEffect'] = throw_on_side_effect
    if timeout is not None:
        params['timeout'] = timeout.to_json()
    if disable_breaks is not None:
        params['disableBreaks'] = disable_breaks
    if repl_mode is not None:
        params['replMode'] = repl_mode
    if allow_unsafe_eval_blocked_by_csp is not None:
        params['allowUnsafeEvalBlockedByCSP'] = allow_unsafe_eval_blocked_by_csp
    if unique_context_id is not None:
        params['uniqueContextId'] = unique_context_id
    if serialization_options is not None:
        params['serializationOptions'] = serialization_options.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.evaluate',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def get_isolate_id() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Returns the isolate id.

    **EXPERIMENTAL**

    :returns: The isolate id.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getIsolateId',
    }
    json = yield cmd_dict
    return str(json['id'])


def get_heap_usage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[float, float, float, float]]:
    '''
    Returns the JavaScript heap usage.
    It is the total usage of the corresponding isolate not scoped to a particular Runtime.

    **EXPERIMENTAL**

    :returns: A tuple with the following items:

        0. **usedSize** - Used JavaScript heap size in bytes.
        1. **totalSize** - Allocated JavaScript heap size in bytes.
        2. **embedderHeapUsedSize** - Used size in bytes in the embedder's garbage-collected heap.
        3. **backingStorageSize** - Size in bytes of backing storage for array buffers and external strings.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getHeapUsage',
    }
    json = yield cmd_dict
    return (
        float(json['usedSize']),
        float(json['totalSize']),
        float(json['embedderHeapUsedSize']),
        float(json['backingStorageSize'])
    )


def get_properties(
        object_id: RemoteObjectId,
        own_properties: typing.Optional[bool] = None,
        accessor_properties_only: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        non_indexed_properties_only: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[PropertyDescriptor], typing.Optional[typing.List[InternalPropertyDescriptor]], typing.Optional[typing.List[PrivatePropertyDescriptor]], typing.Optional[ExceptionDetails]]]:
    '''
    Returns properties of a given object. Object group of the result is inherited from the target
    object.

    :param object_id: Identifier of the object to return properties for.
    :param own_properties: *(Optional)* If true, returns properties belonging only to the element itself, not to its prototype chain.
    :param accessor_properties_only: **(EXPERIMENTAL)** *(Optional)* If true, returns accessor properties (with getter/setter) only; internal properties are not returned either.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the results.
    :param non_indexed_properties_only: **(EXPERIMENTAL)** *(Optional)* If true, returns non-indexed properties only.
    :returns: A tuple with the following items:

        0. **result** - Object properties.
        1. **internalProperties** - *(Optional)* Internal object properties (only of the element itself).
        2. **privateProperties** - *(Optional)* Object private properties.
        3. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if own_properties is not None:
        params['ownProperties'] = own_properties
    if accessor_properties_only is not None:
        params['accessorPropertiesOnly'] = accessor_properties_only
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if non_indexed_properties_only is not None:
        params['nonIndexedPropertiesOnly'] = non_indexed_properties_only
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getProperties',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [PropertyDescriptor.from_json(i) for i in json['result']],
        [InternalPropertyDescriptor.from_json(i) for i in json['internalProperties']] if 'internalProperties' in json else None,
        [PrivatePropertyDescriptor.from_json(i) for i in json['privateProperties']] if 'privateProperties' in json else None,
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def global_lexical_scope_names(
        execution_context_id: typing.Optional[ExecutionContextId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Returns all let, const and class variables from global scope.

    :param execution_context_id: *(Optional)* Specifies in which execution context to lookup global scope variables.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.globalLexicalScopeNames',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['names']]


def query_objects(
        prototype_object_id: RemoteObjectId,
        object_group: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,RemoteObject]:
    '''
    :param prototype_object_id: Identifier of the prototype to return objects for.
    :param object_group: *(Optional)* Symbolic group name that can be used to release the results.
    :returns: Array with objects.
    '''
    params: T_JSON_DICT = dict()
    params['prototypeObjectId'] = prototype_object_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.queryObjects',
        'params': params,
    }
    json = yield cmd_dict
    return RemoteObject.from_json(json['objects'])


def release_object(
        object_id: RemoteObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases remote object with given id.

    :param object_id: Identifier of the object to release.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.releaseObject',
        'params': params,
    }
    json = yield cmd_dict


def release_object_group(
        object_group: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases all remote objects that belong to a given group.

    :param object_group: Symbolic object group name.
    '''
    params: T_JSON_DICT = dict()
    params['objectGroup'] = object_group
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.releaseObjectGroup',
        'params': params,
    }
    json = yield cmd_dict


def run_if_waiting_for_debugger() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Tells inspected instance to run if it was waiting for debugger to attach.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.runIfWaitingForDebugger',
    }
    json = yield cmd_dict


def run_script(
        script_id: ScriptId,
        execution_context_id: typing.Optional[ExecutionContextId] = None,
        object_group: typing.Optional[str] = None,
        silent: typing.Optional[bool] = None,
        include_command_line_api: typing.Optional[bool] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        await_promise: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Runs script with given id in a given context.

    :param script_id: Id of the script to run.
    :param execution_context_id: *(Optional)* Specifies in which execution context to perform script run. If the parameter is omitted the evaluation will be performed in the context of the inspected page.
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ```setPauseOnException```` state.
    :param include_command_line_api: *(Optional)* Determines whether Command Line API should be available during the evaluation.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object which should be sent by value.
    :param generate_preview: *(Optional)* Whether preview should be generated for the result.
    :param await_promise: *(Optional)* Whether execution should ````await``` for resulting value and return once awaited promise is resolved.
    :returns: A tuple with the following items:

        0. **result** - Run result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    if silent is not None:
        params['silent'] = silent
    if include_command_line_api is not None:
        params['includeCommandLineAPI'] = include_command_line_api
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if await_promise is not None:
        params['awaitPromise'] = await_promise
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.runScript',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def set_async_call_stack_depth(
        max_depth: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables or disables async call stacks tracking.

    :param max_depth: Maximum depth of async call stacks. Setting to ```0``` will effectively disable collecting async call stacks (default).
    '''
    params: T_JSON_DICT = dict()
    params['maxDepth'] = max_depth
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.setAsyncCallStackDepth',
        'params': params,
    }
    json = yield cmd_dict


def set_custom_object_formatter_enabled(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param enabled:
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.setCustomObjectFormatterEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_max_call_stack_size_to_capture(
        size: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param size:
    '''
    params: T_JSON_DICT = dict()
    params['size'] = size
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.setMaxCallStackSizeToCapture',
        'params': params,
    }
    json = yield cmd_dict


def terminate_execution() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Terminate current or next JavaScript execution.
    Will cancel the termination when the outer-most script execution ends.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.terminateExecution',
    }
    json = yield cmd_dict


def add_binding(
        name: str,
        execution_context_id: typing.Optional[ExecutionContextId] = None,
        execution_context_name: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    If executionContextId is empty, adds binding with the given name on the
    global objects of all inspected contexts, including those created later,
    bindings survive reloads.
    Binding function takes exactly one argument, this argument should be string,
    in case of any other input, function throws an exception.
    Each binding function call produces Runtime.bindingCalled notification.

    :param name:
    :param execution_context_id: **(EXPERIMENTAL)** *(Optional)* If specified, the binding would only be exposed to the specified execution context. If omitted and ```executionContextName```` is not set, the binding is exposed to all execution contexts of the target. This parameter is mutually exclusive with ````executionContextName````. Deprecated in favor of ````executionContextName```` due to an unclear use case and bugs in implementation (crbug.com/1169639). ````executionContextId```` will be removed in the future.
    :param execution_context_name: *(Optional)* If specified, the binding is exposed to the executionContext with matching name, even for contexts created after the binding is added. See also ````ExecutionContext.name```` and ````worldName```` parameter to ````Page.addScriptToEvaluateOnNewDocument````. This parameter is mutually exclusive with ````executionContextId```.
    '''
    params: T_JSON_DICT = dict()
    params['name'] = name
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    if execution_context_name is not None:
        params['executionContextName'] = execution_context_name
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.addBinding',
        'params': params,
    }
    json = yield cmd_dict


def remove_binding(
        name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    This method does not remove binding function from global object but
    unsubscribes current runtime agent from Runtime.bindingCalled notifications.

    :param name:
    '''
    params: T_JSON_DICT = dict()
    params['name'] = name
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.removeBinding',
        'params': params,
    }
    json = yield cmd_dict


def get_exception_details(
        error_object_id: RemoteObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Optional[ExceptionDetails]]:
    '''
    This method tries to lookup and populate exception details for a
    JavaScript Error object.
    Note that the stackTrace portion of the resulting exceptionDetails will
    only be populated if the Runtime domain was enabled at the time when the
    Error was thrown.

    **EXPERIMENTAL**

    :param error_object_id: The error object for which to resolve the exception details.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['errorObjectId'] = error_object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getExceptionDetails',
        'params': params,
    }
    json = yield cmd_dict
    return ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None


@event_class('Runtime.bindingCalled')
@dataclass
class BindingCalled:
    '''
    **EXPERIMENTAL**

    Notification is issued every time when binding is called.
    '''
    name: str
    payload: str
    #: Identifier of the context where the call was made.
    execution_context_id: ExecutionContextId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BindingCalled:
        return cls(
            name=str(json['name']),
            payload=str(json['payload']),
            execution_context_id=ExecutionContextId.from_json(json['executionContextId'])
        )


@event_class('Runtime.consoleAPICalled')
@dataclass
class ConsoleAPICalled:
    '''
    Issued when console API was called.
    '''
    #: Type of the call.
    type_: str
    #: Call arguments.
    args: typing.List[RemoteObject]
    #: Identifier of the context where the call was made.
    execution_context_id: ExecutionContextId
    #: Call timestamp.
    timestamp: Timestamp
    #: Stack trace captured when the call was made. The async stack chain is automatically reported for
    #: the following call types: ``assert``, ``error``, ``trace``, ``warning``. For other types the async call
    #: chain can be retrieved using ``Debugger.getStackTrace`` and ``stackTrace.parentId`` field.
    stack_trace: typing.Optional[StackTrace]
    #: Console context descriptor for calls on non-default console context (not console.*):
    #: 'anonymous#unique-logger-id' for call on unnamed context, 'name#unique-logger-id' for call
    #: on named context.
    context: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ConsoleAPICalled:
        return cls(
            type_=str(json['type']),
            args=[RemoteObject.from_json(i) for i in json['args']],
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']),
            timestamp=Timestamp.from_json(json['timestamp']),
            stack_trace=StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            context=str(json['context']) if 'context' in json else None
        )


@event_class('Runtime.exceptionRevoked')
@dataclass
class ExceptionRevoked:
    '''
    Issued when unhandled exception was revoked.
    '''
    #: Reason describing why exception was revoked.
    reason: str
    #: The id of revoked exception, as reported in ``exceptionThrown``.
    exception_id: int

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExceptionRevoked:
        return cls(
            reason=str(json['reason']),
            exception_id=int(json['exceptionId'])
        )


@event_class('Runtime.exceptionThrown')
@dataclass
class ExceptionThrown:
    '''
    Issued when exception was thrown and unhandled.
    '''
    #: Timestamp of the exception.
    timestamp: Timestamp
    exception_details: ExceptionDetails

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExceptionThrown:
        return cls(
            timestamp=Timestamp.from_json(json['timestamp']),
            exception_details=ExceptionDetails.from_json(json['exceptionDetails'])
        )


@event_class('Runtime.executionContextCreated')
@dataclass
class ExecutionContextCreated:
    '''
    Issued when new execution context is created.
    '''
    #: A newly created execution context.
    context: ExecutionContextDescription

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExecutionContextCreated:
        return cls(
            context=ExecutionContextDescription.from_json(json['context'])
        )


@event_class('Runtime.executionContextDestroyed')
@dataclass
class ExecutionContextDestroyed:
    '''
    Issued when execution context is destroyed.
    '''
    #: Id of the destroyed context
    execution_context_id: ExecutionContextId
    #: Unique Id of the destroyed context
    execution_context_unique_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExecutionContextDestroyed:
        return cls(
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']),
            execution_context_unique_id=str(json['executionContextUniqueId'])
        )


@event_class('Runtime.executionContextsCleared')
@dataclass
class ExecutionContextsCleared:
    '''
    Issued when all executionContexts were cleared in browser
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExecutionContextsCleared:
        return cls(

        )


@event_class('Runtime.inspectRequested')
@dataclass
class InspectRequested:
    '''
    Issued when object should be inspected (for example, as a result of inspect() command line API
    call).
    '''
    object_: RemoteObject
    hints: dict
    #: Identifier of the context where the call was made.
    execution_context_id: typing.Optional[ExecutionContextId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InspectRequested:
        return cls(
            object_=RemoteObject.from_json(json['object']),
            hints=dict(json['hints']),
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']) if 'executionContextId' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\runtime.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Runtime
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class ScriptId(str):
    '''
    Unique script identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> ScriptId:
        return cls(json)

    def __repr__(self):
        return 'ScriptId({})'.format(super().__repr__())


@dataclass
class SerializationOptions:
    '''
    Represents options for serialization. Overrides ``generatePreview`` and ``returnByValue``.
    '''
    serialization: str

    #: Deep serialization depth. Default is full depth. Respected only in ``deep`` serialization mode.
    max_depth: typing.Optional[int] = None

    #: Embedder-specific parameters. For example if connected to V8 in Chrome these control DOM
    #: serialization via ``maxNodeDepth: integer`` and ``includeShadowTree: "none" `` "open" `` "all"``.
    #: Values can be only of type string or integer.
    additional_parameters: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['serialization'] = self.serialization
        if self.max_depth is not None:
            json['maxDepth'] = self.max_depth
        if self.additional_parameters is not None:
            json['additionalParameters'] = self.additional_parameters
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            serialization=str(json['serialization']),
            max_depth=int(json['maxDepth']) if 'maxDepth' in json else None,
            additional_parameters=dict(json['additionalParameters']) if 'additionalParameters' in json else None,
        )


@dataclass
class DeepSerializedValue:
    '''
    Represents deep serialized value.
    '''
    type_: str

    value: typing.Optional[typing.Any] = None

    object_id: typing.Optional[str] = None

    #: Set if value reference met more then once during serialization. In such
    #: case, value is provided only to one of the serialized values. Unique
    #: per value in the scope of one CDP call.
    weak_local_object_reference: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.value is not None:
            json['value'] = self.value
        if self.object_id is not None:
            json['objectId'] = self.object_id
        if self.weak_local_object_reference is not None:
            json['weakLocalObjectReference'] = self.weak_local_object_reference
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            value=json['value'] if 'value' in json else None,
            object_id=str(json['objectId']) if 'objectId' in json else None,
            weak_local_object_reference=int(json['weakLocalObjectReference']) if 'weakLocalObjectReference' in json else None,
        )


class RemoteObjectId(str):
    '''
    Unique object identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RemoteObjectId:
        return cls(json)

    def __repr__(self):
        return 'RemoteObjectId({})'.format(super().__repr__())


class UnserializableValue(str):
    '''
    Primitive value which cannot be JSON-stringified. Includes values ``-0``, ``NaN``, ``Infinity``,
    ``-Infinity``, and bigint literals.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UnserializableValue:
        return cls(json)

    def __repr__(self):
        return 'UnserializableValue({})'.format(super().__repr__())


@dataclass
class RemoteObject:
    '''
    Mirror object referencing original JavaScript object.
    '''
    #: Object type.
    type_: str

    #: Object subtype hint. Specified for ``object`` type values only.
    #: NOTE: If you change anything here, make sure to also update
    #: ``subtype`` in ``ObjectPreview`` and ``PropertyPreview`` below.
    subtype: typing.Optional[str] = None

    #: Object class (constructor) name. Specified for ``object`` type values only.
    class_name: typing.Optional[str] = None

    #: Remote object value in case of primitive values or JSON values (if it was requested).
    value: typing.Optional[typing.Any] = None

    #: Primitive value which can not be JSON-stringified does not have ``value``, but gets this
    #: property.
    unserializable_value: typing.Optional[UnserializableValue] = None

    #: String representation of the object.
    description: typing.Optional[str] = None

    #: Deep serialized value.
    deep_serialized_value: typing.Optional[DeepSerializedValue] = None

    #: Unique object identifier (for non-primitive values).
    object_id: typing.Optional[RemoteObjectId] = None

    #: Preview containing abbreviated property values. Specified for ``object`` type values only.
    preview: typing.Optional[ObjectPreview] = None

    custom_preview: typing.Optional[CustomPreview] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.subtype is not None:
            json['subtype'] = self.subtype
        if self.class_name is not None:
            json['className'] = self.class_name
        if self.value is not None:
            json['value'] = self.value
        if self.unserializable_value is not None:
            json['unserializableValue'] = self.unserializable_value.to_json()
        if self.description is not None:
            json['description'] = self.description
        if self.deep_serialized_value is not None:
            json['deepSerializedValue'] = self.deep_serialized_value.to_json()
        if self.object_id is not None:
            json['objectId'] = self.object_id.to_json()
        if self.preview is not None:
            json['preview'] = self.preview.to_json()
        if self.custom_preview is not None:
            json['customPreview'] = self.custom_preview.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            subtype=str(json['subtype']) if 'subtype' in json else None,
            class_name=str(json['className']) if 'className' in json else None,
            value=json['value'] if 'value' in json else None,
            unserializable_value=UnserializableValue.from_json(json['unserializableValue']) if 'unserializableValue' in json else None,
            description=str(json['description']) if 'description' in json else None,
            deep_serialized_value=DeepSerializedValue.from_json(json['deepSerializedValue']) if 'deepSerializedValue' in json else None,
            object_id=RemoteObjectId.from_json(json['objectId']) if 'objectId' in json else None,
            preview=ObjectPreview.from_json(json['preview']) if 'preview' in json else None,
            custom_preview=CustomPreview.from_json(json['customPreview']) if 'customPreview' in json else None,
        )


@dataclass
class CustomPreview:
    #: The JSON-stringified result of formatter.header(object, config) call.
    #: It contains json ML array that represents RemoteObject.
    header: str

    #: If formatter returns true as a result of formatter.hasBody call then bodyGetterId will
    #: contain RemoteObjectId for the function that returns result of formatter.body(object, config) call.
    #: The result value is json ML array.
    body_getter_id: typing.Optional[RemoteObjectId] = None

    def to_json(self):
        json = dict()
        json['header'] = self.header
        if self.body_getter_id is not None:
            json['bodyGetterId'] = self.body_getter_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            header=str(json['header']),
            body_getter_id=RemoteObjectId.from_json(json['bodyGetterId']) if 'bodyGetterId' in json else None,
        )


@dataclass
class ObjectPreview:
    '''
    Object containing abbreviated remote object value.
    '''
    #: Object type.
    type_: str

    #: True iff some of the properties or entries of the original object did not fit.
    overflow: bool

    #: List of the properties.
    properties: typing.List[PropertyPreview]

    #: Object subtype hint. Specified for ``object`` type values only.
    subtype: typing.Optional[str] = None

    #: String representation of the object.
    description: typing.Optional[str] = None

    #: List of the entries. Specified for ``map`` and ``set`` subtype values only.
    entries: typing.Optional[typing.List[EntryPreview]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['overflow'] = self.overflow
        json['properties'] = [i.to_json() for i in self.properties]
        if self.subtype is not None:
            json['subtype'] = self.subtype
        if self.description is not None:
            json['description'] = self.description
        if self.entries is not None:
            json['entries'] = [i.to_json() for i in self.entries]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            overflow=bool(json['overflow']),
            properties=[PropertyPreview.from_json(i) for i in json['properties']],
            subtype=str(json['subtype']) if 'subtype' in json else None,
            description=str(json['description']) if 'description' in json else None,
            entries=[EntryPreview.from_json(i) for i in json['entries']] if 'entries' in json else None,
        )


@dataclass
class PropertyPreview:
    #: Property name.
    name: str

    #: Object type. Accessor means that the property itself is an accessor property.
    type_: str

    #: User-friendly property value string.
    value: typing.Optional[str] = None

    #: Nested value preview.
    value_preview: typing.Optional[ObjectPreview] = None

    #: Object subtype hint. Specified for ``object`` type values only.
    subtype: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['type'] = self.type_
        if self.value is not None:
            json['value'] = self.value
        if self.value_preview is not None:
            json['valuePreview'] = self.value_preview.to_json()
        if self.subtype is not None:
            json['subtype'] = self.subtype
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            type_=str(json['type']),
            value=str(json['value']) if 'value' in json else None,
            value_preview=ObjectPreview.from_json(json['valuePreview']) if 'valuePreview' in json else None,
            subtype=str(json['subtype']) if 'subtype' in json else None,
        )


@dataclass
class EntryPreview:
    #: Preview of the value.
    value: ObjectPreview

    #: Preview of the key. Specified for map-like collection entries.
    key: typing.Optional[ObjectPreview] = None

    def to_json(self):
        json = dict()
        json['value'] = self.value.to_json()
        if self.key is not None:
            json['key'] = self.key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=ObjectPreview.from_json(json['value']),
            key=ObjectPreview.from_json(json['key']) if 'key' in json else None,
        )


@dataclass
class PropertyDescriptor:
    '''
    Object property descriptor.
    '''
    #: Property name or symbol description.
    name: str

    #: True if the type of this property descriptor may be changed and if the property may be
    #: deleted from the corresponding object.
    configurable: bool

    #: True if this property shows up during enumeration of the properties on the corresponding
    #: object.
    enumerable: bool

    #: The value associated with the property.
    value: typing.Optional[RemoteObject] = None

    #: True if the value associated with the property may be changed (data descriptors only).
    writable: typing.Optional[bool] = None

    #: A function which serves as a getter for the property, or ``undefined`` if there is no getter
    #: (accessor descriptors only).
    get: typing.Optional[RemoteObject] = None

    #: A function which serves as a setter for the property, or ``undefined`` if there is no setter
    #: (accessor descriptors only).
    set_: typing.Optional[RemoteObject] = None

    #: True if the result was thrown during the evaluation.
    was_thrown: typing.Optional[bool] = None

    #: True if the property is owned for the object.
    is_own: typing.Optional[bool] = None

    #: Property symbol object, if the property is of the ``symbol`` type.
    symbol: typing.Optional[RemoteObject] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['configurable'] = self.configurable
        json['enumerable'] = self.enumerable
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.writable is not None:
            json['writable'] = self.writable
        if self.get is not None:
            json['get'] = self.get.to_json()
        if self.set_ is not None:
            json['set'] = self.set_.to_json()
        if self.was_thrown is not None:
            json['wasThrown'] = self.was_thrown
        if self.is_own is not None:
            json['isOwn'] = self.is_own
        if self.symbol is not None:
            json['symbol'] = self.symbol.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            configurable=bool(json['configurable']),
            enumerable=bool(json['enumerable']),
            value=RemoteObject.from_json(json['value']) if 'value' in json else None,
            writable=bool(json['writable']) if 'writable' in json else None,
            get=RemoteObject.from_json(json['get']) if 'get' in json else None,
            set_=RemoteObject.from_json(json['set']) if 'set' in json else None,
            was_thrown=bool(json['wasThrown']) if 'wasThrown' in json else None,
            is_own=bool(json['isOwn']) if 'isOwn' in json else None,
            symbol=RemoteObject.from_json(json['symbol']) if 'symbol' in json else None,
        )


@dataclass
class InternalPropertyDescriptor:
    '''
    Object internal property descriptor. This property isn't normally visible in JavaScript code.
    '''
    #: Conventional property name.
    name: str

    #: The value associated with the property.
    value: typing.Optional[RemoteObject] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        if self.value is not None:
            json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=RemoteObject.from_json(json['value']) if 'value' in json else None,
        )


@dataclass
class PrivatePropertyDescriptor:
    '''
    Object private field descriptor.
    '''
    #: Private property name.
    name: str

    #: The value associated with the private property.
    value: typing.Optional[RemoteObject] = None

    #: A function which serves as a getter for the private property,
    #: or ``undefined`` if there is no getter (accessor descriptors only).
    get: typing.Optional[RemoteObject] = None

    #: A function which serves as a setter for the private property,
    #: or ``undefined`` if there is no setter (accessor descriptors only).
    set_: typing.Optional[RemoteObject] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.get is not None:
            json['get'] = self.get.to_json()
        if self.set_ is not None:
            json['set'] = self.set_.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=RemoteObject.from_json(json['value']) if 'value' in json else None,
            get=RemoteObject.from_json(json['get']) if 'get' in json else None,
            set_=RemoteObject.from_json(json['set']) if 'set' in json else None,
        )


@dataclass
class CallArgument:
    '''
    Represents function call argument. Either remote object id ``objectId``, primitive ``value``,
    unserializable primitive value or neither of (for undefined) them should be specified.
    '''
    #: Primitive value or serializable javascript object.
    value: typing.Optional[typing.Any] = None

    #: Primitive value which can not be JSON-stringified.
    unserializable_value: typing.Optional[UnserializableValue] = None

    #: Remote object handle.
    object_id: typing.Optional[RemoteObjectId] = None

    def to_json(self):
        json = dict()
        if self.value is not None:
            json['value'] = self.value
        if self.unserializable_value is not None:
            json['unserializableValue'] = self.unserializable_value.to_json()
        if self.object_id is not None:
            json['objectId'] = self.object_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=json['value'] if 'value' in json else None,
            unserializable_value=UnserializableValue.from_json(json['unserializableValue']) if 'unserializableValue' in json else None,
            object_id=RemoteObjectId.from_json(json['objectId']) if 'objectId' in json else None,
        )


class ExecutionContextId(int):
    '''
    Id of an execution context.
    '''
    def to_json(self) -> int:
        return self

    @classmethod
    def from_json(cls, json: int) -> ExecutionContextId:
        return cls(json)

    def __repr__(self):
        return 'ExecutionContextId({})'.format(super().__repr__())


@dataclass
class ExecutionContextDescription:
    '''
    Description of an isolated world.
    '''
    #: Unique id of the execution context. It can be used to specify in which execution context
    #: script evaluation should be performed.
    id_: ExecutionContextId

    #: Execution context origin.
    origin: str

    #: Human readable name describing given context.
    name: str

    #: A system-unique execution context identifier. Unlike the id, this is unique across
    #: multiple processes, so can be reliably used to identify specific context while backend
    #: performs a cross-process navigation.
    unique_id: str

    #: Embedder-specific auxiliary data likely matching {isDefault: boolean, type: 'default'``'isolated'``'worker', frameId: string}
    aux_data: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_.to_json()
        json['origin'] = self.origin
        json['name'] = self.name
        json['uniqueId'] = self.unique_id
        if self.aux_data is not None:
            json['auxData'] = self.aux_data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=ExecutionContextId.from_json(json['id']),
            origin=str(json['origin']),
            name=str(json['name']),
            unique_id=str(json['uniqueId']),
            aux_data=dict(json['auxData']) if 'auxData' in json else None,
        )


@dataclass
class ExceptionDetails:
    '''
    Detailed information about exception (or error) that was thrown during script compilation or
    execution.
    '''
    #: Exception id.
    exception_id: int

    #: Exception text, which should be used together with exception object when available.
    text: str

    #: Line number of the exception location (0-based).
    line_number: int

    #: Column number of the exception location (0-based).
    column_number: int

    #: Script ID of the exception location.
    script_id: typing.Optional[ScriptId] = None

    #: URL of the exception location, to be used when the script was not reported.
    url: typing.Optional[str] = None

    #: JavaScript stack trace if available.
    stack_trace: typing.Optional[StackTrace] = None

    #: Exception object if available.
    exception: typing.Optional[RemoteObject] = None

    #: Identifier of the context where exception happened.
    execution_context_id: typing.Optional[ExecutionContextId] = None

    #: Dictionary with entries of meta data that the client associated
    #: with this exception, such as information about associated network
    #: requests, etc.
    exception_meta_data: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['exceptionId'] = self.exception_id
        json['text'] = self.text
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        if self.script_id is not None:
            json['scriptId'] = self.script_id.to_json()
        if self.url is not None:
            json['url'] = self.url
        if self.stack_trace is not None:
            json['stackTrace'] = self.stack_trace.to_json()
        if self.exception is not None:
            json['exception'] = self.exception.to_json()
        if self.execution_context_id is not None:
            json['executionContextId'] = self.execution_context_id.to_json()
        if self.exception_meta_data is not None:
            json['exceptionMetaData'] = self.exception_meta_data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            exception_id=int(json['exceptionId']),
            text=str(json['text']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
            script_id=ScriptId.from_json(json['scriptId']) if 'scriptId' in json else None,
            url=str(json['url']) if 'url' in json else None,
            stack_trace=StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            exception=RemoteObject.from_json(json['exception']) if 'exception' in json else None,
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']) if 'executionContextId' in json else None,
            exception_meta_data=dict(json['exceptionMetaData']) if 'exceptionMetaData' in json else None,
        )


class Timestamp(float):
    '''
    Number of milliseconds since epoch.
    '''
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> Timestamp:
        return cls(json)

    def __repr__(self):
        return 'Timestamp({})'.format(super().__repr__())


class TimeDelta(float):
    '''
    Number of milliseconds.
    '''
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> TimeDelta:
        return cls(json)

    def __repr__(self):
        return 'TimeDelta({})'.format(super().__repr__())


@dataclass
class CallFrame:
    '''
    Stack entry for runtime errors and assertions.
    '''
    #: JavaScript function name.
    function_name: str

    #: JavaScript script id.
    script_id: ScriptId

    #: JavaScript script name or url.
    url: str

    #: JavaScript script line number (0-based).
    line_number: int

    #: JavaScript script column number (0-based).
    column_number: int

    def to_json(self):
        json = dict()
        json['functionName'] = self.function_name
        json['scriptId'] = self.script_id.to_json()
        json['url'] = self.url
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            function_name=str(json['functionName']),
            script_id=ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
        )


@dataclass
class StackTrace:
    '''
    Call frames for assertions or error messages.
    '''
    #: JavaScript function name.
    call_frames: typing.List[CallFrame]

    #: String label of this stack trace. For async traces this may be a name of the function that
    #: initiated the async call.
    description: typing.Optional[str] = None

    #: Asynchronous JavaScript stack trace that preceded this stack, if available.
    parent: typing.Optional[StackTrace] = None

    #: Asynchronous JavaScript stack trace that preceded this stack, if available.
    parent_id: typing.Optional[StackTraceId] = None

    def to_json(self):
        json = dict()
        json['callFrames'] = [i.to_json() for i in self.call_frames]
        if self.description is not None:
            json['description'] = self.description
        if self.parent is not None:
            json['parent'] = self.parent.to_json()
        if self.parent_id is not None:
            json['parentId'] = self.parent_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            call_frames=[CallFrame.from_json(i) for i in json['callFrames']],
            description=str(json['description']) if 'description' in json else None,
            parent=StackTrace.from_json(json['parent']) if 'parent' in json else None,
            parent_id=StackTraceId.from_json(json['parentId']) if 'parentId' in json else None,
        )


class UniqueDebuggerId(str):
    '''
    Unique identifier of current debugger.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UniqueDebuggerId:
        return cls(json)

    def __repr__(self):
        return 'UniqueDebuggerId({})'.format(super().__repr__())


@dataclass
class StackTraceId:
    '''
    If ``debuggerId`` is set stack trace comes from another debugger and can be resolved there. This
    allows to track cross-debugger calls. See ``Runtime.StackTrace`` and ``Debugger.paused`` for usages.
    '''
    id_: str

    debugger_id: typing.Optional[UniqueDebuggerId] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_
        if self.debugger_id is not None:
            json['debuggerId'] = self.debugger_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=str(json['id']),
            debugger_id=UniqueDebuggerId.from_json(json['debuggerId']) if 'debuggerId' in json else None,
        )


def await_promise(
        promise_object_id: RemoteObjectId,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Add handler to promise with given promise object id.

    :param promise_object_id: Identifier of the promise.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object that should be sent by value.
    :param generate_preview: *(Optional)* Whether preview should be generated for the result.
    :returns: A tuple with the following items:

        0. **result** - Promise result. Will contain rejected value if promise was rejected.
        1. **exceptionDetails** - *(Optional)* Exception details if stack strace is available.
    '''
    params: T_JSON_DICT = dict()
    params['promiseObjectId'] = promise_object_id.to_json()
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.awaitPromise',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def call_function_on(
        function_declaration: str,
        object_id: typing.Optional[RemoteObjectId] = None,
        arguments: typing.Optional[typing.List[CallArgument]] = None,
        silent: typing.Optional[bool] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        user_gesture: typing.Optional[bool] = None,
        await_promise: typing.Optional[bool] = None,
        execution_context_id: typing.Optional[ExecutionContextId] = None,
        object_group: typing.Optional[str] = None,
        throw_on_side_effect: typing.Optional[bool] = None,
        unique_context_id: typing.Optional[str] = None,
        serialization_options: typing.Optional[SerializationOptions] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Calls function with given declaration on the given object. Object group of the result is
    inherited from the target object.

    :param function_declaration: Declaration of the function to call.
    :param object_id: *(Optional)* Identifier of the object to call function on. Either objectId or executionContextId should be specified.
    :param arguments: *(Optional)* Call arguments. All call arguments must belong to the same JavaScript world as the target object.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ```setPauseOnException```` state.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object which should be sent by value. Can be overriden by ````serializationOptions````.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the result.
    :param user_gesture: *(Optional)* Whether execution should be treated as initiated by user in the UI.
    :param await_promise: *(Optional)* Whether execution should ````await```` for resulting value and return once awaited promise is resolved.
    :param execution_context_id: *(Optional)* Specifies execution context which global object will be used to call function on. Either executionContextId or objectId should be specified.
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects. If objectGroup is not specified and objectId is, objectGroup will be inherited from object.
    :param throw_on_side_effect: **(EXPERIMENTAL)** *(Optional)* Whether to throw an exception if side effect cannot be ruled out during evaluation.
    :param unique_context_id: **(EXPERIMENTAL)** *(Optional)* An alternative way to specify the execution context to call function on. Compared to contextId that may be reused across processes, this is guaranteed to be system-unique, so it can be used to prevent accidental function call in context different than intended (e.g. as a result of navigation across process boundaries). This is mutually exclusive with ````executionContextId````.
    :param serialization_options: **(EXPERIMENTAL)** *(Optional)* Specifies the result serialization. If provided, overrides ````generatePreview```` and ````returnByValue```.
    :returns: A tuple with the following items:

        0. **result** - Call result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['functionDeclaration'] = function_declaration
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    if arguments is not None:
        params['arguments'] = [i.to_json() for i in arguments]
    if silent is not None:
        params['silent'] = silent
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if user_gesture is not None:
        params['userGesture'] = user_gesture
    if await_promise is not None:
        params['awaitPromise'] = await_promise
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    if throw_on_side_effect is not None:
        params['throwOnSideEffect'] = throw_on_side_effect
    if unique_context_id is not None:
        params['uniqueContextId'] = unique_context_id
    if serialization_options is not None:
        params['serializationOptions'] = serialization_options.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.callFunctionOn',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def compile_script(
        expression: str,
        source_url: str,
        persist_script: bool,
        execution_context_id: typing.Optional[ExecutionContextId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[ScriptId], typing.Optional[ExceptionDetails]]]:
    '''
    Compiles expression.

    :param expression: Expression to compile.
    :param source_url: Source url to be set for the script.
    :param persist_script: Specifies whether the compiled script should be persisted.
    :param execution_context_id: *(Optional)* Specifies in which execution context to perform script run. If the parameter is omitted the evaluation will be performed in the context of the inspected page.
    :returns: A tuple with the following items:

        0. **scriptId** - *(Optional)* Id of the script.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['expression'] = expression
    params['sourceURL'] = source_url
    params['persistScript'] = persist_script
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.compileScript',
        'params': params,
    }
    json = yield cmd_dict
    return (
        ScriptId.from_json(json['scriptId']) if 'scriptId' in json else None,
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables reporting of execution contexts creation.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.disable',
    }
    json = yield cmd_dict


def discard_console_entries() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Discards collected exceptions and console API calls.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.discardConsoleEntries',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables reporting of execution contexts creation by means of ``executionContextCreated`` event.
    When the reporting gets enabled the event will be sent immediately for each existing execution
    context.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.enable',
    }
    json = yield cmd_dict


def evaluate(
        expression: str,
        object_group: typing.Optional[str] = None,
        include_command_line_api: typing.Optional[bool] = None,
        silent: typing.Optional[bool] = None,
        context_id: typing.Optional[ExecutionContextId] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        user_gesture: typing.Optional[bool] = None,
        await_promise: typing.Optional[bool] = None,
        throw_on_side_effect: typing.Optional[bool] = None,
        timeout: typing.Optional[TimeDelta] = None,
        disable_breaks: typing.Optional[bool] = None,
        repl_mode: typing.Optional[bool] = None,
        allow_unsafe_eval_blocked_by_csp: typing.Optional[bool] = None,
        unique_context_id: typing.Optional[str] = None,
        serialization_options: typing.Optional[SerializationOptions] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Evaluates expression on global object.

    :param expression: Expression to evaluate.
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects.
    :param include_command_line_api: *(Optional)* Determines whether Command Line API should be available during the evaluation.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ```setPauseOnException```` state.
    :param context_id: *(Optional)* Specifies in which execution context to perform evaluation. If the parameter is omitted the evaluation will be performed in the context of the inspected page. This is mutually exclusive with ````uniqueContextId````, which offers an alternative way to identify the execution context that is more reliable in a multi-process environment.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object that should be sent by value.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the result.
    :param user_gesture: *(Optional)* Whether execution should be treated as initiated by user in the UI.
    :param await_promise: *(Optional)* Whether execution should ````await```` for resulting value and return once awaited promise is resolved.
    :param throw_on_side_effect: **(EXPERIMENTAL)** *(Optional)* Whether to throw an exception if side effect cannot be ruled out during evaluation. This implies ````disableBreaks```` below.
    :param timeout: **(EXPERIMENTAL)** *(Optional)* Terminate execution after timing out (number of milliseconds).
    :param disable_breaks: **(EXPERIMENTAL)** *(Optional)* Disable breakpoints during execution.
    :param repl_mode: **(EXPERIMENTAL)** *(Optional)* Setting this flag to true enables ````let```` re-declaration and top-level ````await````. Note that ````let```` variables can only be re-declared if they originate from ````replMode```` themselves.
    :param allow_unsafe_eval_blocked_by_csp: **(EXPERIMENTAL)** *(Optional)* The Content Security Policy (CSP) for the target might block 'unsafe-eval' which includes eval(), Function(), setTimeout() and setInterval() when called with non-callable arguments. This flag bypasses CSP for this evaluation and allows unsafe-eval. Defaults to true.
    :param unique_context_id: **(EXPERIMENTAL)** *(Optional)* An alternative way to specify the execution context to evaluate in. Compared to contextId that may be reused across processes, this is guaranteed to be system-unique, so it can be used to prevent accidental evaluation of the expression in context different than intended (e.g. as a result of navigation across process boundaries). This is mutually exclusive with ````contextId````.
    :param serialization_options: **(EXPERIMENTAL)** *(Optional)* Specifies the result serialization. If provided, overrides ````generatePreview```` and ````returnByValue```.
    :returns: A tuple with the following items:

        0. **result** - Evaluation result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['expression'] = expression
    if object_group is not None:
        params['objectGroup'] = object_group
    if include_command_line_api is not None:
        params['includeCommandLineAPI'] = include_command_line_api
    if silent is not None:
        params['silent'] = silent
    if context_id is not None:
        params['contextId'] = context_id.to_json()
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if user_gesture is not None:
        params['userGesture'] = user_gesture
    if await_promise is not None:
        params['awaitPromise'] = await_promise
    if throw_on_side_effect is not None:
        params['throwOnSideEffect'] = throw_on_side_effect
    if timeout is not None:
        params['timeout'] = timeout.to_json()
    if disable_breaks is not None:
        params['disableBreaks'] = disable_breaks
    if repl_mode is not None:
        params['replMode'] = repl_mode
    if allow_unsafe_eval_blocked_by_csp is not None:
        params['allowUnsafeEvalBlockedByCSP'] = allow_unsafe_eval_blocked_by_csp
    if unique_context_id is not None:
        params['uniqueContextId'] = unique_context_id
    if serialization_options is not None:
        params['serializationOptions'] = serialization_options.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.evaluate',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def get_isolate_id() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Returns the isolate id.

    **EXPERIMENTAL**

    :returns: The isolate id.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getIsolateId',
    }
    json = yield cmd_dict
    return str(json['id'])


def get_heap_usage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[float, float, float, float]]:
    '''
    Returns the JavaScript heap usage.
    It is the total usage of the corresponding isolate not scoped to a particular Runtime.

    **EXPERIMENTAL**

    :returns: A tuple with the following items:

        0. **usedSize** - Used JavaScript heap size in bytes.
        1. **totalSize** - Allocated JavaScript heap size in bytes.
        2. **embedderHeapUsedSize** - Used size in bytes in the embedder's garbage-collected heap.
        3. **backingStorageSize** - Size in bytes of backing storage for array buffers and external strings.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getHeapUsage',
    }
    json = yield cmd_dict
    return (
        float(json['usedSize']),
        float(json['totalSize']),
        float(json['embedderHeapUsedSize']),
        float(json['backingStorageSize'])
    )


def get_properties(
        object_id: RemoteObjectId,
        own_properties: typing.Optional[bool] = None,
        accessor_properties_only: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        non_indexed_properties_only: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[PropertyDescriptor], typing.Optional[typing.List[InternalPropertyDescriptor]], typing.Optional[typing.List[PrivatePropertyDescriptor]], typing.Optional[ExceptionDetails]]]:
    '''
    Returns properties of a given object. Object group of the result is inherited from the target
    object.

    :param object_id: Identifier of the object to return properties for.
    :param own_properties: *(Optional)* If true, returns properties belonging only to the element itself, not to its prototype chain.
    :param accessor_properties_only: **(EXPERIMENTAL)** *(Optional)* If true, returns accessor properties (with getter/setter) only; internal properties are not returned either.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the results.
    :param non_indexed_properties_only: **(EXPERIMENTAL)** *(Optional)* If true, returns non-indexed properties only.
    :returns: A tuple with the following items:

        0. **result** - Object properties.
        1. **internalProperties** - *(Optional)* Internal object properties (only of the element itself).
        2. **privateProperties** - *(Optional)* Object private properties.
        3. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if own_properties is not None:
        params['ownProperties'] = own_properties
    if accessor_properties_only is not None:
        params['accessorPropertiesOnly'] = accessor_properties_only
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if non_indexed_properties_only is not None:
        params['nonIndexedPropertiesOnly'] = non_indexed_properties_only
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getProperties',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [PropertyDescriptor.from_json(i) for i in json['result']],
        [InternalPropertyDescriptor.from_json(i) for i in json['internalProperties']] if 'internalProperties' in json else None,
        [PrivatePropertyDescriptor.from_json(i) for i in json['privateProperties']] if 'privateProperties' in json else None,
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def global_lexical_scope_names(
        execution_context_id: typing.Optional[ExecutionContextId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Returns all let, const and class variables from global scope.

    :param execution_context_id: *(Optional)* Specifies in which execution context to lookup global scope variables.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.globalLexicalScopeNames',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['names']]


def query_objects(
        prototype_object_id: RemoteObjectId,
        object_group: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,RemoteObject]:
    '''
    :param prototype_object_id: Identifier of the prototype to return objects for.
    :param object_group: *(Optional)* Symbolic group name that can be used to release the results.
    :returns: Array with objects.
    '''
    params: T_JSON_DICT = dict()
    params['prototypeObjectId'] = prototype_object_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.queryObjects',
        'params': params,
    }
    json = yield cmd_dict
    return RemoteObject.from_json(json['objects'])


def release_object(
        object_id: RemoteObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases remote object with given id.

    :param object_id: Identifier of the object to release.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.releaseObject',
        'params': params,
    }
    json = yield cmd_dict


def release_object_group(
        object_group: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases all remote objects that belong to a given group.

    :param object_group: Symbolic object group name.
    '''
    params: T_JSON_DICT = dict()
    params['objectGroup'] = object_group
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.releaseObjectGroup',
        'params': params,
    }
    json = yield cmd_dict


def run_if_waiting_for_debugger() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Tells inspected instance to run if it was waiting for debugger to attach.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.runIfWaitingForDebugger',
    }
    json = yield cmd_dict


def run_script(
        script_id: ScriptId,
        execution_context_id: typing.Optional[ExecutionContextId] = None,
        object_group: typing.Optional[str] = None,
        silent: typing.Optional[bool] = None,
        include_command_line_api: typing.Optional[bool] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        await_promise: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Runs script with given id in a given context.

    :param script_id: Id of the script to run.
    :param execution_context_id: *(Optional)* Specifies in which execution context to perform script run. If the parameter is omitted the evaluation will be performed in the context of the inspected page.
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ```setPauseOnException```` state.
    :param include_command_line_api: *(Optional)* Determines whether Command Line API should be available during the evaluation.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object which should be sent by value.
    :param generate_preview: *(Optional)* Whether preview should be generated for the result.
    :param await_promise: *(Optional)* Whether execution should ````await``` for resulting value and return once awaited promise is resolved.
    :returns: A tuple with the following items:

        0. **result** - Run result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    if silent is not None:
        params['silent'] = silent
    if include_command_line_api is not None:
        params['includeCommandLineAPI'] = include_command_line_api
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if await_promise is not None:
        params['awaitPromise'] = await_promise
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.runScript',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def set_async_call_stack_depth(
        max_depth: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables or disables async call stacks tracking.

    :param max_depth: Maximum depth of async call stacks. Setting to ```0``` will effectively disable collecting async call stacks (default).
    '''
    params: T_JSON_DICT = dict()
    params['maxDepth'] = max_depth
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.setAsyncCallStackDepth',
        'params': params,
    }
    json = yield cmd_dict


def set_custom_object_formatter_enabled(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param enabled:
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.setCustomObjectFormatterEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_max_call_stack_size_to_capture(
        size: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param size:
    '''
    params: T_JSON_DICT = dict()
    params['size'] = size
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.setMaxCallStackSizeToCapture',
        'params': params,
    }
    json = yield cmd_dict


def terminate_execution() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Terminate current or next JavaScript execution.
    Will cancel the termination when the outer-most script execution ends.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.terminateExecution',
    }
    json = yield cmd_dict


def add_binding(
        name: str,
        execution_context_id: typing.Optional[ExecutionContextId] = None,
        execution_context_name: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    If executionContextId is empty, adds binding with the given name on the
    global objects of all inspected contexts, including those created later,
    bindings survive reloads.
    Binding function takes exactly one argument, this argument should be string,
    in case of any other input, function throws an exception.
    Each binding function call produces Runtime.bindingCalled notification.

    :param name:
    :param execution_context_id: **(EXPERIMENTAL)** *(Optional)* If specified, the binding would only be exposed to the specified execution context. If omitted and ```executionContextName```` is not set, the binding is exposed to all execution contexts of the target. This parameter is mutually exclusive with ````executionContextName````. Deprecated in favor of ````executionContextName```` due to an unclear use case and bugs in implementation (crbug.com/1169639). ````executionContextId```` will be removed in the future.
    :param execution_context_name: *(Optional)* If specified, the binding is exposed to the executionContext with matching name, even for contexts created after the binding is added. See also ````ExecutionContext.name```` and ````worldName```` parameter to ````Page.addScriptToEvaluateOnNewDocument````. This parameter is mutually exclusive with ````executionContextId```.
    '''
    params: T_JSON_DICT = dict()
    params['name'] = name
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    if execution_context_name is not None:
        params['executionContextName'] = execution_context_name
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.addBinding',
        'params': params,
    }
    json = yield cmd_dict


def remove_binding(
        name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    This method does not remove binding function from global object but
    unsubscribes current runtime agent from Runtime.bindingCalled notifications.

    :param name:
    '''
    params: T_JSON_DICT = dict()
    params['name'] = name
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.removeBinding',
        'params': params,
    }
    json = yield cmd_dict


def get_exception_details(
        error_object_id: RemoteObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Optional[ExceptionDetails]]:
    '''
    This method tries to lookup and populate exception details for a
    JavaScript Error object.
    Note that the stackTrace portion of the resulting exceptionDetails will
    only be populated if the Runtime domain was enabled at the time when the
    Error was thrown.

    **EXPERIMENTAL**

    :param error_object_id: The error object for which to resolve the exception details.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['errorObjectId'] = error_object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getExceptionDetails',
        'params': params,
    }
    json = yield cmd_dict
    return ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None


@event_class('Runtime.bindingCalled')
@dataclass
class BindingCalled:
    '''
    **EXPERIMENTAL**

    Notification is issued every time when binding is called.
    '''
    name: str
    payload: str
    #: Identifier of the context where the call was made.
    execution_context_id: ExecutionContextId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BindingCalled:
        return cls(
            name=str(json['name']),
            payload=str(json['payload']),
            execution_context_id=ExecutionContextId.from_json(json['executionContextId'])
        )


@event_class('Runtime.consoleAPICalled')
@dataclass
class ConsoleAPICalled:
    '''
    Issued when console API was called.
    '''
    #: Type of the call.
    type_: str
    #: Call arguments.
    args: typing.List[RemoteObject]
    #: Identifier of the context where the call was made.
    execution_context_id: ExecutionContextId
    #: Call timestamp.
    timestamp: Timestamp
    #: Stack trace captured when the call was made. The async stack chain is automatically reported for
    #: the following call types: ``assert``, ``error``, ``trace``, ``warning``. For other types the async call
    #: chain can be retrieved using ``Debugger.getStackTrace`` and ``stackTrace.parentId`` field.
    stack_trace: typing.Optional[StackTrace]
    #: Console context descriptor for calls on non-default console context (not console.*):
    #: 'anonymous#unique-logger-id' for call on unnamed context, 'name#unique-logger-id' for call
    #: on named context.
    context: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ConsoleAPICalled:
        return cls(
            type_=str(json['type']),
            args=[RemoteObject.from_json(i) for i in json['args']],
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']),
            timestamp=Timestamp.from_json(json['timestamp']),
            stack_trace=StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            context=str(json['context']) if 'context' in json else None
        )


@event_class('Runtime.exceptionRevoked')
@dataclass
class ExceptionRevoked:
    '''
    Issued when unhandled exception was revoked.
    '''
    #: Reason describing why exception was revoked.
    reason: str
    #: The id of revoked exception, as reported in ``exceptionThrown``.
    exception_id: int

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExceptionRevoked:
        return cls(
            reason=str(json['reason']),
            exception_id=int(json['exceptionId'])
        )


@event_class('Runtime.exceptionThrown')
@dataclass
class ExceptionThrown:
    '''
    Issued when exception was thrown and unhandled.
    '''
    #: Timestamp of the exception.
    timestamp: Timestamp
    exception_details: ExceptionDetails

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExceptionThrown:
        return cls(
            timestamp=Timestamp.from_json(json['timestamp']),
            exception_details=ExceptionDetails.from_json(json['exceptionDetails'])
        )


@event_class('Runtime.executionContextCreated')
@dataclass
class ExecutionContextCreated:
    '''
    Issued when new execution context is created.
    '''
    #: A newly created execution context.
    context: ExecutionContextDescription

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExecutionContextCreated:
        return cls(
            context=ExecutionContextDescription.from_json(json['context'])
        )


@event_class('Runtime.executionContextDestroyed')
@dataclass
class ExecutionContextDestroyed:
    '''
    Issued when execution context is destroyed.
    '''
    #: Id of the destroyed context
    execution_context_id: ExecutionContextId
    #: Unique Id of the destroyed context
    execution_context_unique_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExecutionContextDestroyed:
        return cls(
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']),
            execution_context_unique_id=str(json['executionContextUniqueId'])
        )


@event_class('Runtime.executionContextsCleared')
@dataclass
class ExecutionContextsCleared:
    '''
    Issued when all executionContexts were cleared in browser
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExecutionContextsCleared:
        return cls(

        )


@event_class('Runtime.inspectRequested')
@dataclass
class InspectRequested:
    '''
    Issued when object should be inspected (for example, as a result of inspect() command line API
    call).
    '''
    object_: RemoteObject
    hints: dict
    #: Identifier of the context where the call was made.
    execution_context_id: typing.Optional[ExecutionContextId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InspectRequested:
        return cls(
            object_=RemoteObject.from_json(json['object']),
            hints=dict(json['hints']),
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']) if 'executionContextId' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\runtime.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Runtime
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class ScriptId(str):
    '''
    Unique script identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> ScriptId:
        return cls(json)

    def __repr__(self):
        return 'ScriptId({})'.format(super().__repr__())


@dataclass
class SerializationOptions:
    '''
    Represents options for serialization. Overrides ``generatePreview`` and ``returnByValue``.
    '''
    serialization: str

    #: Deep serialization depth. Default is full depth. Respected only in ``deep`` serialization mode.
    max_depth: typing.Optional[int] = None

    #: Embedder-specific parameters. For example if connected to V8 in Chrome these control DOM
    #: serialization via ``maxNodeDepth: integer`` and ``includeShadowTree: "none" `` "open" `` "all"``.
    #: Values can be only of type string or integer.
    additional_parameters: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['serialization'] = self.serialization
        if self.max_depth is not None:
            json['maxDepth'] = self.max_depth
        if self.additional_parameters is not None:
            json['additionalParameters'] = self.additional_parameters
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            serialization=str(json['serialization']),
            max_depth=int(json['maxDepth']) if 'maxDepth' in json else None,
            additional_parameters=dict(json['additionalParameters']) if 'additionalParameters' in json else None,
        )


@dataclass
class DeepSerializedValue:
    '''
    Represents deep serialized value.
    '''
    type_: str

    value: typing.Optional[typing.Any] = None

    object_id: typing.Optional[str] = None

    #: Set if value reference met more then once during serialization. In such
    #: case, value is provided only to one of the serialized values. Unique
    #: per value in the scope of one CDP call.
    weak_local_object_reference: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.value is not None:
            json['value'] = self.value
        if self.object_id is not None:
            json['objectId'] = self.object_id
        if self.weak_local_object_reference is not None:
            json['weakLocalObjectReference'] = self.weak_local_object_reference
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            value=json['value'] if 'value' in json else None,
            object_id=str(json['objectId']) if 'objectId' in json else None,
            weak_local_object_reference=int(json['weakLocalObjectReference']) if 'weakLocalObjectReference' in json else None,
        )


class RemoteObjectId(str):
    '''
    Unique object identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RemoteObjectId:
        return cls(json)

    def __repr__(self):
        return 'RemoteObjectId({})'.format(super().__repr__())


class UnserializableValue(str):
    '''
    Primitive value which cannot be JSON-stringified. Includes values ``-0``, ``NaN``, ``Infinity``,
    ``-Infinity``, and bigint literals.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UnserializableValue:
        return cls(json)

    def __repr__(self):
        return 'UnserializableValue({})'.format(super().__repr__())


@dataclass
class RemoteObject:
    '''
    Mirror object referencing original JavaScript object.
    '''
    #: Object type.
    type_: str

    #: Object subtype hint. Specified for ``object`` type values only.
    #: NOTE: If you change anything here, make sure to also update
    #: ``subtype`` in ``ObjectPreview`` and ``PropertyPreview`` below.
    subtype: typing.Optional[str] = None

    #: Object class (constructor) name. Specified for ``object`` type values only.
    class_name: typing.Optional[str] = None

    #: Remote object value in case of primitive values or JSON values (if it was requested).
    value: typing.Optional[typing.Any] = None

    #: Primitive value which can not be JSON-stringified does not have ``value``, but gets this
    #: property.
    unserializable_value: typing.Optional[UnserializableValue] = None

    #: String representation of the object.
    description: typing.Optional[str] = None

    #: Deep serialized value.
    deep_serialized_value: typing.Optional[DeepSerializedValue] = None

    #: Unique object identifier (for non-primitive values).
    object_id: typing.Optional[RemoteObjectId] = None

    #: Preview containing abbreviated property values. Specified for ``object`` type values only.
    preview: typing.Optional[ObjectPreview] = None

    custom_preview: typing.Optional[CustomPreview] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.subtype is not None:
            json['subtype'] = self.subtype
        if self.class_name is not None:
            json['className'] = self.class_name
        if self.value is not None:
            json['value'] = self.value
        if self.unserializable_value is not None:
            json['unserializableValue'] = self.unserializable_value.to_json()
        if self.description is not None:
            json['description'] = self.description
        if self.deep_serialized_value is not None:
            json['deepSerializedValue'] = self.deep_serialized_value.to_json()
        if self.object_id is not None:
            json['objectId'] = self.object_id.to_json()
        if self.preview is not None:
            json['preview'] = self.preview.to_json()
        if self.custom_preview is not None:
            json['customPreview'] = self.custom_preview.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            subtype=str(json['subtype']) if 'subtype' in json else None,
            class_name=str(json['className']) if 'className' in json else None,
            value=json['value'] if 'value' in json else None,
            unserializable_value=UnserializableValue.from_json(json['unserializableValue']) if 'unserializableValue' in json else None,
            description=str(json['description']) if 'description' in json else None,
            deep_serialized_value=DeepSerializedValue.from_json(json['deepSerializedValue']) if 'deepSerializedValue' in json else None,
            object_id=RemoteObjectId.from_json(json['objectId']) if 'objectId' in json else None,
            preview=ObjectPreview.from_json(json['preview']) if 'preview' in json else None,
            custom_preview=CustomPreview.from_json(json['customPreview']) if 'customPreview' in json else None,
        )


@dataclass
class CustomPreview:
    #: The JSON-stringified result of formatter.header(object, config) call.
    #: It contains json ML array that represents RemoteObject.
    header: str

    #: If formatter returns true as a result of formatter.hasBody call then bodyGetterId will
    #: contain RemoteObjectId for the function that returns result of formatter.body(object, config) call.
    #: The result value is json ML array.
    body_getter_id: typing.Optional[RemoteObjectId] = None

    def to_json(self):
        json = dict()
        json['header'] = self.header
        if self.body_getter_id is not None:
            json['bodyGetterId'] = self.body_getter_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            header=str(json['header']),
            body_getter_id=RemoteObjectId.from_json(json['bodyGetterId']) if 'bodyGetterId' in json else None,
        )


@dataclass
class ObjectPreview:
    '''
    Object containing abbreviated remote object value.
    '''
    #: Object type.
    type_: str

    #: True iff some of the properties or entries of the original object did not fit.
    overflow: bool

    #: List of the properties.
    properties: typing.List[PropertyPreview]

    #: Object subtype hint. Specified for ``object`` type values only.
    subtype: typing.Optional[str] = None

    #: String representation of the object.
    description: typing.Optional[str] = None

    #: List of the entries. Specified for ``map`` and ``set`` subtype values only.
    entries: typing.Optional[typing.List[EntryPreview]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['overflow'] = self.overflow
        json['properties'] = [i.to_json() for i in self.properties]
        if self.subtype is not None:
            json['subtype'] = self.subtype
        if self.description is not None:
            json['description'] = self.description
        if self.entries is not None:
            json['entries'] = [i.to_json() for i in self.entries]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            overflow=bool(json['overflow']),
            properties=[PropertyPreview.from_json(i) for i in json['properties']],
            subtype=str(json['subtype']) if 'subtype' in json else None,
            description=str(json['description']) if 'description' in json else None,
            entries=[EntryPreview.from_json(i) for i in json['entries']] if 'entries' in json else None,
        )


@dataclass
class PropertyPreview:
    #: Property name.
    name: str

    #: Object type. Accessor means that the property itself is an accessor property.
    type_: str

    #: User-friendly property value string.
    value: typing.Optional[str] = None

    #: Nested value preview.
    value_preview: typing.Optional[ObjectPreview] = None

    #: Object subtype hint. Specified for ``object`` type values only.
    subtype: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['type'] = self.type_
        if self.value is not None:
            json['value'] = self.value
        if self.value_preview is not None:
            json['valuePreview'] = self.value_preview.to_json()
        if self.subtype is not None:
            json['subtype'] = self.subtype
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            type_=str(json['type']),
            value=str(json['value']) if 'value' in json else None,
            value_preview=ObjectPreview.from_json(json['valuePreview']) if 'valuePreview' in json else None,
            subtype=str(json['subtype']) if 'subtype' in json else None,
        )


@dataclass
class EntryPreview:
    #: Preview of the value.
    value: ObjectPreview

    #: Preview of the key. Specified for map-like collection entries.
    key: typing.Optional[ObjectPreview] = None

    def to_json(self):
        json = dict()
        json['value'] = self.value.to_json()
        if self.key is not None:
            json['key'] = self.key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=ObjectPreview.from_json(json['value']),
            key=ObjectPreview.from_json(json['key']) if 'key' in json else None,
        )


@dataclass
class PropertyDescriptor:
    '''
    Object property descriptor.
    '''
    #: Property name or symbol description.
    name: str

    #: True if the type of this property descriptor may be changed and if the property may be
    #: deleted from the corresponding object.
    configurable: bool

    #: True if this property shows up during enumeration of the properties on the corresponding
    #: object.
    enumerable: bool

    #: The value associated with the property.
    value: typing.Optional[RemoteObject] = None

    #: True if the value associated with the property may be changed (data descriptors only).
    writable: typing.Optional[bool] = None

    #: A function which serves as a getter for the property, or ``undefined`` if there is no getter
    #: (accessor descriptors only).
    get: typing.Optional[RemoteObject] = None

    #: A function which serves as a setter for the property, or ``undefined`` if there is no setter
    #: (accessor descriptors only).
    set_: typing.Optional[RemoteObject] = None

    #: True if the result was thrown during the evaluation.
    was_thrown: typing.Optional[bool] = None

    #: True if the property is owned for the object.
    is_own: typing.Optional[bool] = None

    #: Property symbol object, if the property is of the ``symbol`` type.
    symbol: typing.Optional[RemoteObject] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['configurable'] = self.configurable
        json['enumerable'] = self.enumerable
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.writable is not None:
            json['writable'] = self.writable
        if self.get is not None:
            json['get'] = self.get.to_json()
        if self.set_ is not None:
            json['set'] = self.set_.to_json()
        if self.was_thrown is not None:
            json['wasThrown'] = self.was_thrown
        if self.is_own is not None:
            json['isOwn'] = self.is_own
        if self.symbol is not None:
            json['symbol'] = self.symbol.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            configurable=bool(json['configurable']),
            enumerable=bool(json['enumerable']),
            value=RemoteObject.from_json(json['value']) if 'value' in json else None,
            writable=bool(json['writable']) if 'writable' in json else None,
            get=RemoteObject.from_json(json['get']) if 'get' in json else None,
            set_=RemoteObject.from_json(json['set']) if 'set' in json else None,
            was_thrown=bool(json['wasThrown']) if 'wasThrown' in json else None,
            is_own=bool(json['isOwn']) if 'isOwn' in json else None,
            symbol=RemoteObject.from_json(json['symbol']) if 'symbol' in json else None,
        )


@dataclass
class InternalPropertyDescriptor:
    '''
    Object internal property descriptor. This property isn't normally visible in JavaScript code.
    '''
    #: Conventional property name.
    name: str

    #: The value associated with the property.
    value: typing.Optional[RemoteObject] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        if self.value is not None:
            json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=RemoteObject.from_json(json['value']) if 'value' in json else None,
        )


@dataclass
class PrivatePropertyDescriptor:
    '''
    Object private field descriptor.
    '''
    #: Private property name.
    name: str

    #: The value associated with the private property.
    value: typing.Optional[RemoteObject] = None

    #: A function which serves as a getter for the private property,
    #: or ``undefined`` if there is no getter (accessor descriptors only).
    get: typing.Optional[RemoteObject] = None

    #: A function which serves as a setter for the private property,
    #: or ``undefined`` if there is no setter (accessor descriptors only).
    set_: typing.Optional[RemoteObject] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.get is not None:
            json['get'] = self.get.to_json()
        if self.set_ is not None:
            json['set'] = self.set_.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=RemoteObject.from_json(json['value']) if 'value' in json else None,
            get=RemoteObject.from_json(json['get']) if 'get' in json else None,
            set_=RemoteObject.from_json(json['set']) if 'set' in json else None,
        )


@dataclass
class CallArgument:
    '''
    Represents function call argument. Either remote object id ``objectId``, primitive ``value``,
    unserializable primitive value or neither of (for undefined) them should be specified.
    '''
    #: Primitive value or serializable javascript object.
    value: typing.Optional[typing.Any] = None

    #: Primitive value which can not be JSON-stringified.
    unserializable_value: typing.Optional[UnserializableValue] = None

    #: Remote object handle.
    object_id: typing.Optional[RemoteObjectId] = None

    def to_json(self):
        json = dict()
        if self.value is not None:
            json['value'] = self.value
        if self.unserializable_value is not None:
            json['unserializableValue'] = self.unserializable_value.to_json()
        if self.object_id is not None:
            json['objectId'] = self.object_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=json['value'] if 'value' in json else None,
            unserializable_value=UnserializableValue.from_json(json['unserializableValue']) if 'unserializableValue' in json else None,
            object_id=RemoteObjectId.from_json(json['objectId']) if 'objectId' in json else None,
        )


class ExecutionContextId(int):
    '''
    Id of an execution context.
    '''
    def to_json(self) -> int:
        return self

    @classmethod
    def from_json(cls, json: int) -> ExecutionContextId:
        return cls(json)

    def __repr__(self):
        return 'ExecutionContextId({})'.format(super().__repr__())


@dataclass
class ExecutionContextDescription:
    '''
    Description of an isolated world.
    '''
    #: Unique id of the execution context. It can be used to specify in which execution context
    #: script evaluation should be performed.
    id_: ExecutionContextId

    #: Execution context origin.
    origin: str

    #: Human readable name describing given context.
    name: str

    #: A system-unique execution context identifier. Unlike the id, this is unique across
    #: multiple processes, so can be reliably used to identify specific context while backend
    #: performs a cross-process navigation.
    unique_id: str

    #: Embedder-specific auxiliary data likely matching {isDefault: boolean, type: 'default'``'isolated'``'worker', frameId: string}
    aux_data: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_.to_json()
        json['origin'] = self.origin
        json['name'] = self.name
        json['uniqueId'] = self.unique_id
        if self.aux_data is not None:
            json['auxData'] = self.aux_data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=ExecutionContextId.from_json(json['id']),
            origin=str(json['origin']),
            name=str(json['name']),
            unique_id=str(json['uniqueId']),
            aux_data=dict(json['auxData']) if 'auxData' in json else None,
        )


@dataclass
class ExceptionDetails:
    '''
    Detailed information about exception (or error) that was thrown during script compilation or
    execution.
    '''
    #: Exception id.
    exception_id: int

    #: Exception text, which should be used together with exception object when available.
    text: str

    #: Line number of the exception location (0-based).
    line_number: int

    #: Column number of the exception location (0-based).
    column_number: int

    #: Script ID of the exception location.
    script_id: typing.Optional[ScriptId] = None

    #: URL of the exception location, to be used when the script was not reported.
    url: typing.Optional[str] = None

    #: JavaScript stack trace if available.
    stack_trace: typing.Optional[StackTrace] = None

    #: Exception object if available.
    exception: typing.Optional[RemoteObject] = None

    #: Identifier of the context where exception happened.
    execution_context_id: typing.Optional[ExecutionContextId] = None

    #: Dictionary with entries of meta data that the client associated
    #: with this exception, such as information about associated network
    #: requests, etc.
    exception_meta_data: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['exceptionId'] = self.exception_id
        json['text'] = self.text
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        if self.script_id is not None:
            json['scriptId'] = self.script_id.to_json()
        if self.url is not None:
            json['url'] = self.url
        if self.stack_trace is not None:
            json['stackTrace'] = self.stack_trace.to_json()
        if self.exception is not None:
            json['exception'] = self.exception.to_json()
        if self.execution_context_id is not None:
            json['executionContextId'] = self.execution_context_id.to_json()
        if self.exception_meta_data is not None:
            json['exceptionMetaData'] = self.exception_meta_data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            exception_id=int(json['exceptionId']),
            text=str(json['text']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
            script_id=ScriptId.from_json(json['scriptId']) if 'scriptId' in json else None,
            url=str(json['url']) if 'url' in json else None,
            stack_trace=StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            exception=RemoteObject.from_json(json['exception']) if 'exception' in json else None,
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']) if 'executionContextId' in json else None,
            exception_meta_data=dict(json['exceptionMetaData']) if 'exceptionMetaData' in json else None,
        )


class Timestamp(float):
    '''
    Number of milliseconds since epoch.
    '''
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> Timestamp:
        return cls(json)

    def __repr__(self):
        return 'Timestamp({})'.format(super().__repr__())


class TimeDelta(float):
    '''
    Number of milliseconds.
    '''
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> TimeDelta:
        return cls(json)

    def __repr__(self):
        return 'TimeDelta({})'.format(super().__repr__())


@dataclass
class CallFrame:
    '''
    Stack entry for runtime errors and assertions.
    '''
    #: JavaScript function name.
    function_name: str

    #: JavaScript script id.
    script_id: ScriptId

    #: JavaScript script name or url.
    url: str

    #: JavaScript script line number (0-based).
    line_number: int

    #: JavaScript script column number (0-based).
    column_number: int

    def to_json(self):
        json = dict()
        json['functionName'] = self.function_name
        json['scriptId'] = self.script_id.to_json()
        json['url'] = self.url
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            function_name=str(json['functionName']),
            script_id=ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
        )


@dataclass
class StackTrace:
    '''
    Call frames for assertions or error messages.
    '''
    #: JavaScript function name.
    call_frames: typing.List[CallFrame]

    #: String label of this stack trace. For async traces this may be a name of the function that
    #: initiated the async call.
    description: typing.Optional[str] = None

    #: Asynchronous JavaScript stack trace that preceded this stack, if available.
    parent: typing.Optional[StackTrace] = None

    #: Asynchronous JavaScript stack trace that preceded this stack, if available.
    parent_id: typing.Optional[StackTraceId] = None

    def to_json(self):
        json = dict()
        json['callFrames'] = [i.to_json() for i in self.call_frames]
        if self.description is not None:
            json['description'] = self.description
        if self.parent is not None:
            json['parent'] = self.parent.to_json()
        if self.parent_id is not None:
            json['parentId'] = self.parent_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            call_frames=[CallFrame.from_json(i) for i in json['callFrames']],
            description=str(json['description']) if 'description' in json else None,
            parent=StackTrace.from_json(json['parent']) if 'parent' in json else None,
            parent_id=StackTraceId.from_json(json['parentId']) if 'parentId' in json else None,
        )


class UniqueDebuggerId(str):
    '''
    Unique identifier of current debugger.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UniqueDebuggerId:
        return cls(json)

    def __repr__(self):
        return 'UniqueDebuggerId({})'.format(super().__repr__())


@dataclass
class StackTraceId:
    '''
    If ``debuggerId`` is set stack trace comes from another debugger and can be resolved there. This
    allows to track cross-debugger calls. See ``Runtime.StackTrace`` and ``Debugger.paused`` for usages.
    '''
    id_: str

    debugger_id: typing.Optional[UniqueDebuggerId] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_
        if self.debugger_id is not None:
            json['debuggerId'] = self.debugger_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=str(json['id']),
            debugger_id=UniqueDebuggerId.from_json(json['debuggerId']) if 'debuggerId' in json else None,
        )


def await_promise(
        promise_object_id: RemoteObjectId,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Add handler to promise with given promise object id.

    :param promise_object_id: Identifier of the promise.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object that should be sent by value.
    :param generate_preview: *(Optional)* Whether preview should be generated for the result.
    :returns: A tuple with the following items:

        0. **result** - Promise result. Will contain rejected value if promise was rejected.
        1. **exceptionDetails** - *(Optional)* Exception details if stack strace is available.
    '''
    params: T_JSON_DICT = dict()
    params['promiseObjectId'] = promise_object_id.to_json()
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.awaitPromise',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def call_function_on(
        function_declaration: str,
        object_id: typing.Optional[RemoteObjectId] = None,
        arguments: typing.Optional[typing.List[CallArgument]] = None,
        silent: typing.Optional[bool] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        user_gesture: typing.Optional[bool] = None,
        await_promise: typing.Optional[bool] = None,
        execution_context_id: typing.Optional[ExecutionContextId] = None,
        object_group: typing.Optional[str] = None,
        throw_on_side_effect: typing.Optional[bool] = None,
        unique_context_id: typing.Optional[str] = None,
        serialization_options: typing.Optional[SerializationOptions] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Calls function with given declaration on the given object. Object group of the result is
    inherited from the target object.

    :param function_declaration: Declaration of the function to call.
    :param object_id: *(Optional)* Identifier of the object to call function on. Either objectId or executionContextId should be specified.
    :param arguments: *(Optional)* Call arguments. All call arguments must belong to the same JavaScript world as the target object.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ```setPauseOnException```` state.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object which should be sent by value. Can be overriden by ````serializationOptions````.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the result.
    :param user_gesture: *(Optional)* Whether execution should be treated as initiated by user in the UI.
    :param await_promise: *(Optional)* Whether execution should ````await```` for resulting value and return once awaited promise is resolved.
    :param execution_context_id: *(Optional)* Specifies execution context which global object will be used to call function on. Either executionContextId or objectId should be specified.
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects. If objectGroup is not specified and objectId is, objectGroup will be inherited from object.
    :param throw_on_side_effect: **(EXPERIMENTAL)** *(Optional)* Whether to throw an exception if side effect cannot be ruled out during evaluation.
    :param unique_context_id: **(EXPERIMENTAL)** *(Optional)* An alternative way to specify the execution context to call function on. Compared to contextId that may be reused across processes, this is guaranteed to be system-unique, so it can be used to prevent accidental function call in context different than intended (e.g. as a result of navigation across process boundaries). This is mutually exclusive with ````executionContextId````.
    :param serialization_options: **(EXPERIMENTAL)** *(Optional)* Specifies the result serialization. If provided, overrides ````generatePreview```` and ````returnByValue```.
    :returns: A tuple with the following items:

        0. **result** - Call result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['functionDeclaration'] = function_declaration
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    if arguments is not None:
        params['arguments'] = [i.to_json() for i in arguments]
    if silent is not None:
        params['silent'] = silent
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if user_gesture is not None:
        params['userGesture'] = user_gesture
    if await_promise is not None:
        params['awaitPromise'] = await_promise
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    if throw_on_side_effect is not None:
        params['throwOnSideEffect'] = throw_on_side_effect
    if unique_context_id is not None:
        params['uniqueContextId'] = unique_context_id
    if serialization_options is not None:
        params['serializationOptions'] = serialization_options.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.callFunctionOn',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def compile_script(
        expression: str,
        source_url: str,
        persist_script: bool,
        execution_context_id: typing.Optional[ExecutionContextId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[ScriptId], typing.Optional[ExceptionDetails]]]:
    '''
    Compiles expression.

    :param expression: Expression to compile.
    :param source_url: Source url to be set for the script.
    :param persist_script: Specifies whether the compiled script should be persisted.
    :param execution_context_id: *(Optional)* Specifies in which execution context to perform script run. If the parameter is omitted the evaluation will be performed in the context of the inspected page.
    :returns: A tuple with the following items:

        0. **scriptId** - *(Optional)* Id of the script.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['expression'] = expression
    params['sourceURL'] = source_url
    params['persistScript'] = persist_script
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.compileScript',
        'params': params,
    }
    json = yield cmd_dict
    return (
        ScriptId.from_json(json['scriptId']) if 'scriptId' in json else None,
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables reporting of execution contexts creation.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.disable',
    }
    json = yield cmd_dict


def discard_console_entries() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Discards collected exceptions and console API calls.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.discardConsoleEntries',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables reporting of execution contexts creation by means of ``executionContextCreated`` event.
    When the reporting gets enabled the event will be sent immediately for each existing execution
    context.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.enable',
    }
    json = yield cmd_dict


def evaluate(
        expression: str,
        object_group: typing.Optional[str] = None,
        include_command_line_api: typing.Optional[bool] = None,
        silent: typing.Optional[bool] = None,
        context_id: typing.Optional[ExecutionContextId] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        user_gesture: typing.Optional[bool] = None,
        await_promise: typing.Optional[bool] = None,
        throw_on_side_effect: typing.Optional[bool] = None,
        timeout: typing.Optional[TimeDelta] = None,
        disable_breaks: typing.Optional[bool] = None,
        repl_mode: typing.Optional[bool] = None,
        allow_unsafe_eval_blocked_by_csp: typing.Optional[bool] = None,
        unique_context_id: typing.Optional[str] = None,
        serialization_options: typing.Optional[SerializationOptions] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Evaluates expression on global object.

    :param expression: Expression to evaluate.
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects.
    :param include_command_line_api: *(Optional)* Determines whether Command Line API should be available during the evaluation.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ```setPauseOnException```` state.
    :param context_id: *(Optional)* Specifies in which execution context to perform evaluation. If the parameter is omitted the evaluation will be performed in the context of the inspected page. This is mutually exclusive with ````uniqueContextId````, which offers an alternative way to identify the execution context that is more reliable in a multi-process environment.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object that should be sent by value.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the result.
    :param user_gesture: *(Optional)* Whether execution should be treated as initiated by user in the UI.
    :param await_promise: *(Optional)* Whether execution should ````await```` for resulting value and return once awaited promise is resolved.
    :param throw_on_side_effect: **(EXPERIMENTAL)** *(Optional)* Whether to throw an exception if side effect cannot be ruled out during evaluation. This implies ````disableBreaks```` below.
    :param timeout: **(EXPERIMENTAL)** *(Optional)* Terminate execution after timing out (number of milliseconds).
    :param disable_breaks: **(EXPERIMENTAL)** *(Optional)* Disable breakpoints during execution.
    :param repl_mode: **(EXPERIMENTAL)** *(Optional)* Setting this flag to true enables ````let```` re-declaration and top-level ````await````. Note that ````let```` variables can only be re-declared if they originate from ````replMode```` themselves.
    :param allow_unsafe_eval_blocked_by_csp: **(EXPERIMENTAL)** *(Optional)* The Content Security Policy (CSP) for the target might block 'unsafe-eval' which includes eval(), Function(), setTimeout() and setInterval() when called with non-callable arguments. This flag bypasses CSP for this evaluation and allows unsafe-eval. Defaults to true.
    :param unique_context_id: **(EXPERIMENTAL)** *(Optional)* An alternative way to specify the execution context to evaluate in. Compared to contextId that may be reused across processes, this is guaranteed to be system-unique, so it can be used to prevent accidental evaluation of the expression in context different than intended (e.g. as a result of navigation across process boundaries). This is mutually exclusive with ````contextId````.
    :param serialization_options: **(EXPERIMENTAL)** *(Optional)* Specifies the result serialization. If provided, overrides ````generatePreview```` and ````returnByValue```.
    :returns: A tuple with the following items:

        0. **result** - Evaluation result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['expression'] = expression
    if object_group is not None:
        params['objectGroup'] = object_group
    if include_command_line_api is not None:
        params['includeCommandLineAPI'] = include_command_line_api
    if silent is not None:
        params['silent'] = silent
    if context_id is not None:
        params['contextId'] = context_id.to_json()
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if user_gesture is not None:
        params['userGesture'] = user_gesture
    if await_promise is not None:
        params['awaitPromise'] = await_promise
    if throw_on_side_effect is not None:
        params['throwOnSideEffect'] = throw_on_side_effect
    if timeout is not None:
        params['timeout'] = timeout.to_json()
    if disable_breaks is not None:
        params['disableBreaks'] = disable_breaks
    if repl_mode is not None:
        params['replMode'] = repl_mode
    if allow_unsafe_eval_blocked_by_csp is not None:
        params['allowUnsafeEvalBlockedByCSP'] = allow_unsafe_eval_blocked_by_csp
    if unique_context_id is not None:
        params['uniqueContextId'] = unique_context_id
    if serialization_options is not None:
        params['serializationOptions'] = serialization_options.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.evaluate',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def get_isolate_id() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Returns the isolate id.

    **EXPERIMENTAL**

    :returns: The isolate id.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getIsolateId',
    }
    json = yield cmd_dict
    return str(json['id'])


def get_heap_usage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[float, float, float, float]]:
    '''
    Returns the JavaScript heap usage.
    It is the total usage of the corresponding isolate not scoped to a particular Runtime.

    **EXPERIMENTAL**

    :returns: A tuple with the following items:

        0. **usedSize** - Used JavaScript heap size in bytes.
        1. **totalSize** - Allocated JavaScript heap size in bytes.
        2. **embedderHeapUsedSize** - Used size in bytes in the embedder's garbage-collected heap.
        3. **backingStorageSize** - Size in bytes of backing storage for array buffers and external strings.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getHeapUsage',
    }
    json = yield cmd_dict
    return (
        float(json['usedSize']),
        float(json['totalSize']),
        float(json['embedderHeapUsedSize']),
        float(json['backingStorageSize'])
    )


def get_properties(
        object_id: RemoteObjectId,
        own_properties: typing.Optional[bool] = None,
        accessor_properties_only: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        non_indexed_properties_only: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[PropertyDescriptor], typing.Optional[typing.List[InternalPropertyDescriptor]], typing.Optional[typing.List[PrivatePropertyDescriptor]], typing.Optional[ExceptionDetails]]]:
    '''
    Returns properties of a given object. Object group of the result is inherited from the target
    object.

    :param object_id: Identifier of the object to return properties for.
    :param own_properties: *(Optional)* If true, returns properties belonging only to the element itself, not to its prototype chain.
    :param accessor_properties_only: **(EXPERIMENTAL)** *(Optional)* If true, returns accessor properties (with getter/setter) only; internal properties are not returned either.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the results.
    :param non_indexed_properties_only: **(EXPERIMENTAL)** *(Optional)* If true, returns non-indexed properties only.
    :returns: A tuple with the following items:

        0. **result** - Object properties.
        1. **internalProperties** - *(Optional)* Internal object properties (only of the element itself).
        2. **privateProperties** - *(Optional)* Object private properties.
        3. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if own_properties is not None:
        params['ownProperties'] = own_properties
    if accessor_properties_only is not None:
        params['accessorPropertiesOnly'] = accessor_properties_only
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if non_indexed_properties_only is not None:
        params['nonIndexedPropertiesOnly'] = non_indexed_properties_only
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getProperties',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [PropertyDescriptor.from_json(i) for i in json['result']],
        [InternalPropertyDescriptor.from_json(i) for i in json['internalProperties']] if 'internalProperties' in json else None,
        [PrivatePropertyDescriptor.from_json(i) for i in json['privateProperties']] if 'privateProperties' in json else None,
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def global_lexical_scope_names(
        execution_context_id: typing.Optional[ExecutionContextId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Returns all let, const and class variables from global scope.

    :param execution_context_id: *(Optional)* Specifies in which execution context to lookup global scope variables.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.globalLexicalScopeNames',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['names']]


def query_objects(
        prototype_object_id: RemoteObjectId,
        object_group: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,RemoteObject]:
    '''
    :param prototype_object_id: Identifier of the prototype to return objects for.
    :param object_group: *(Optional)* Symbolic group name that can be used to release the results.
    :returns: Array with objects.
    '''
    params: T_JSON_DICT = dict()
    params['prototypeObjectId'] = prototype_object_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.queryObjects',
        'params': params,
    }
    json = yield cmd_dict
    return RemoteObject.from_json(json['objects'])


def release_object(
        object_id: RemoteObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases remote object with given id.

    :param object_id: Identifier of the object to release.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.releaseObject',
        'params': params,
    }
    json = yield cmd_dict


def release_object_group(
        object_group: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases all remote objects that belong to a given group.

    :param object_group: Symbolic object group name.
    '''
    params: T_JSON_DICT = dict()
    params['objectGroup'] = object_group
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.releaseObjectGroup',
        'params': params,
    }
    json = yield cmd_dict


def run_if_waiting_for_debugger() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Tells inspected instance to run if it was waiting for debugger to attach.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.runIfWaitingForDebugger',
    }
    json = yield cmd_dict


def run_script(
        script_id: ScriptId,
        execution_context_id: typing.Optional[ExecutionContextId] = None,
        object_group: typing.Optional[str] = None,
        silent: typing.Optional[bool] = None,
        include_command_line_api: typing.Optional[bool] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        await_promise: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[RemoteObject, typing.Optional[ExceptionDetails]]]:
    '''
    Runs script with given id in a given context.

    :param script_id: Id of the script to run.
    :param execution_context_id: *(Optional)* Specifies in which execution context to perform script run. If the parameter is omitted the evaluation will be performed in the context of the inspected page.
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ```setPauseOnException```` state.
    :param include_command_line_api: *(Optional)* Determines whether Command Line API should be available during the evaluation.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object which should be sent by value.
    :param generate_preview: *(Optional)* Whether preview should be generated for the result.
    :param await_promise: *(Optional)* Whether execution should ````await``` for resulting value and return once awaited promise is resolved.
    :returns: A tuple with the following items:

        0. **result** - Run result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    if silent is not None:
        params['silent'] = silent
    if include_command_line_api is not None:
        params['includeCommandLineAPI'] = include_command_line_api
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if await_promise is not None:
        params['awaitPromise'] = await_promise
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.runScript',
        'params': params,
    }
    json = yield cmd_dict
    return (
        RemoteObject.from_json(json['result']),
        ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def set_async_call_stack_depth(
        max_depth: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables or disables async call stacks tracking.

    :param max_depth: Maximum depth of async call stacks. Setting to ```0``` will effectively disable collecting async call stacks (default).
    '''
    params: T_JSON_DICT = dict()
    params['maxDepth'] = max_depth
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.setAsyncCallStackDepth',
        'params': params,
    }
    json = yield cmd_dict


def set_custom_object_formatter_enabled(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param enabled:
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.setCustomObjectFormatterEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_max_call_stack_size_to_capture(
        size: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param size:
    '''
    params: T_JSON_DICT = dict()
    params['size'] = size
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.setMaxCallStackSizeToCapture',
        'params': params,
    }
    json = yield cmd_dict


def terminate_execution() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Terminate current or next JavaScript execution.
    Will cancel the termination when the outer-most script execution ends.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.terminateExecution',
    }
    json = yield cmd_dict


def add_binding(
        name: str,
        execution_context_id: typing.Optional[ExecutionContextId] = None,
        execution_context_name: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    If executionContextId is empty, adds binding with the given name on the
    global objects of all inspected contexts, including those created later,
    bindings survive reloads.
    Binding function takes exactly one argument, this argument should be string,
    in case of any other input, function throws an exception.
    Each binding function call produces Runtime.bindingCalled notification.

    :param name:
    :param execution_context_id: **(EXPERIMENTAL)** *(Optional)* If specified, the binding would only be exposed to the specified execution context. If omitted and ```executionContextName```` is not set, the binding is exposed to all execution contexts of the target. This parameter is mutually exclusive with ````executionContextName````. Deprecated in favor of ````executionContextName```` due to an unclear use case and bugs in implementation (crbug.com/1169639). ````executionContextId```` will be removed in the future.
    :param execution_context_name: *(Optional)* If specified, the binding is exposed to the executionContext with matching name, even for contexts created after the binding is added. See also ````ExecutionContext.name```` and ````worldName```` parameter to ````Page.addScriptToEvaluateOnNewDocument````. This parameter is mutually exclusive with ````executionContextId```.
    '''
    params: T_JSON_DICT = dict()
    params['name'] = name
    if execution_context_id is not None:
        params['executionContextId'] = execution_context_id.to_json()
    if execution_context_name is not None:
        params['executionContextName'] = execution_context_name
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.addBinding',
        'params': params,
    }
    json = yield cmd_dict


def remove_binding(
        name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    This method does not remove binding function from global object but
    unsubscribes current runtime agent from Runtime.bindingCalled notifications.

    :param name:
    '''
    params: T_JSON_DICT = dict()
    params['name'] = name
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.removeBinding',
        'params': params,
    }
    json = yield cmd_dict


def get_exception_details(
        error_object_id: RemoteObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Optional[ExceptionDetails]]:
    '''
    This method tries to lookup and populate exception details for a
    JavaScript Error object.
    Note that the stackTrace portion of the resulting exceptionDetails will
    only be populated if the Runtime domain was enabled at the time when the
    Error was thrown.

    **EXPERIMENTAL**

    :param error_object_id: The error object for which to resolve the exception details.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['errorObjectId'] = error_object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Runtime.getExceptionDetails',
        'params': params,
    }
    json = yield cmd_dict
    return ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None


@event_class('Runtime.bindingCalled')
@dataclass
class BindingCalled:
    '''
    **EXPERIMENTAL**

    Notification is issued every time when binding is called.
    '''
    name: str
    payload: str
    #: Identifier of the context where the call was made.
    execution_context_id: ExecutionContextId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BindingCalled:
        return cls(
            name=str(json['name']),
            payload=str(json['payload']),
            execution_context_id=ExecutionContextId.from_json(json['executionContextId'])
        )


@event_class('Runtime.consoleAPICalled')
@dataclass
class ConsoleAPICalled:
    '''
    Issued when console API was called.
    '''
    #: Type of the call.
    type_: str
    #: Call arguments.
    args: typing.List[RemoteObject]
    #: Identifier of the context where the call was made.
    execution_context_id: ExecutionContextId
    #: Call timestamp.
    timestamp: Timestamp
    #: Stack trace captured when the call was made. The async stack chain is automatically reported for
    #: the following call types: ``assert``, ``error``, ``trace``, ``warning``. For other types the async call
    #: chain can be retrieved using ``Debugger.getStackTrace`` and ``stackTrace.parentId`` field.
    stack_trace: typing.Optional[StackTrace]
    #: Console context descriptor for calls on non-default console context (not console.*):
    #: 'anonymous#unique-logger-id' for call on unnamed context, 'name#unique-logger-id' for call
    #: on named context.
    context: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ConsoleAPICalled:
        return cls(
            type_=str(json['type']),
            args=[RemoteObject.from_json(i) for i in json['args']],
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']),
            timestamp=Timestamp.from_json(json['timestamp']),
            stack_trace=StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            context=str(json['context']) if 'context' in json else None
        )


@event_class('Runtime.exceptionRevoked')
@dataclass
class ExceptionRevoked:
    '''
    Issued when unhandled exception was revoked.
    '''
    #: Reason describing why exception was revoked.
    reason: str
    #: The id of revoked exception, as reported in ``exceptionThrown``.
    exception_id: int

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExceptionRevoked:
        return cls(
            reason=str(json['reason']),
            exception_id=int(json['exceptionId'])
        )


@event_class('Runtime.exceptionThrown')
@dataclass
class ExceptionThrown:
    '''
    Issued when exception was thrown and unhandled.
    '''
    #: Timestamp of the exception.
    timestamp: Timestamp
    exception_details: ExceptionDetails

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExceptionThrown:
        return cls(
            timestamp=Timestamp.from_json(json['timestamp']),
            exception_details=ExceptionDetails.from_json(json['exceptionDetails'])
        )


@event_class('Runtime.executionContextCreated')
@dataclass
class ExecutionContextCreated:
    '''
    Issued when new execution context is created.
    '''
    #: A newly created execution context.
    context: ExecutionContextDescription

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExecutionContextCreated:
        return cls(
            context=ExecutionContextDescription.from_json(json['context'])
        )


@event_class('Runtime.executionContextDestroyed')
@dataclass
class ExecutionContextDestroyed:
    '''
    Issued when execution context is destroyed.
    '''
    #: Id of the destroyed context
    execution_context_id: ExecutionContextId
    #: Unique Id of the destroyed context
    execution_context_unique_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExecutionContextDestroyed:
        return cls(
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']),
            execution_context_unique_id=str(json['executionContextUniqueId'])
        )


@event_class('Runtime.executionContextsCleared')
@dataclass
class ExecutionContextsCleared:
    '''
    Issued when all executionContexts were cleared in browser
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ExecutionContextsCleared:
        return cls(

        )


@event_class('Runtime.inspectRequested')
@dataclass
class InspectRequested:
    '''
    Issued when object should be inspected (for example, as a result of inspect() command line API
    call).
    '''
    object_: RemoteObject
    hints: dict
    #: Identifier of the context where the call was made.
    execution_context_id: typing.Optional[ExecutionContextId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InspectRequested:
        return cls(
            object_=RemoteObject.from_json(json['object']),
            hints=dict(json['hints']),
            execution_context_id=ExecutionContextId.from_json(json['executionContextId']) if 'executionContextId' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\internal_user_endpoints.py ===
"""
Internal User Management Endpoints


These are members of a Team on LiteLLM

/user/new
/user/update
/user/delete
/user/info
/user/list
"""

import asyncio
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, cast

import fastapi
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.hooks.user_management_event_hooks import UserManagementEventHooks
from litellm.proxy.management_endpoints.common_daily_activity import get_daily_activity
from litellm.proxy.management_endpoints.common_utils import _user_has_admin_view
from litellm.proxy.management_endpoints.key_management_endpoints import (
    generate_key_helper_fn,
    prepare_metadata_fields,
)
from litellm.proxy.management_helpers.utils import management_endpoint_wrapper
from litellm.proxy.utils import handle_exception_on_proxy
from litellm.types.proxy.management_endpoints.common_daily_activity import (
    BreakdownMetrics,
    KeyMetadata,
    KeyMetricWithMetadata,
    LiteLLM_DailyUserSpend,
    MetricWithMetadata,
    SpendAnalyticsPaginatedResponse,
    SpendMetrics,
)
from litellm.types.proxy.management_endpoints.internal_user_endpoints import (
    UserListResponse,
)

if TYPE_CHECKING:
    from litellm.proxy.proxy_server import PrismaClient

router = APIRouter()


def _update_internal_new_user_params(data_json: dict, data: NewUserRequest) -> dict:
    if "user_id" in data_json and data_json["user_id"] is None:
        data_json["user_id"] = str(uuid.uuid4())

    auto_create_key = data_json.pop("auto_create_key", True)

    if auto_create_key is False:
        data_json["table_name"] = (
            "user"  # only create a user, don't create key if 'auto_create_key' set to False
        )

    if litellm.default_internal_user_params:
        for key, value in litellm.default_internal_user_params.items():
            if key == "available_teams":
                continue
            elif key not in data_json or data_json[key] is None:
                data_json[key] = value
            elif (
                key == "models"
                and isinstance(data_json[key], list)
                and len(data_json[key]) == 0
            ):
                data_json[key] = value

    ## INTERNAL USER ROLE ONLY DEFAULT PARAMS ##
    if (
        data.user_role is not None
        and data.user_role == LitellmUserRoles.INTERNAL_USER.value
    ):
        if (
            litellm.max_internal_user_budget is not None
            and data_json.get("max_budget") is None
        ):
            data_json["max_budget"] = litellm.max_internal_user_budget

        if (
            litellm.internal_user_budget_duration is not None
            and data_json.get("budget_duration") is None
        ):
            data_json["budget_duration"] = litellm.internal_user_budget_duration

    data_json.pop("teams", None)  # handled separately
    return data_json


async def _check_duplicate_user_email(
    user_email: Optional[str], prisma_client: Any
) -> None:
    """
    Helper function to check if a user email already exists in the database.

    Args:
        user_email (Optional[str]): Email to check
        prisma_client (Any): Database client instance

    Raises:
        Exception: If database is not connected
        HTTPException: If user with email already exists
    """
    if user_email:
        if prisma_client is None:
            raise Exception("Database not connected")

        existing_user = await prisma_client.db.litellm_usertable.find_first(
            where={"user_email": user_email.strip()}
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=400,
                detail={"error": f"User with email {user_email} already exists"},
            )


async def _add_user_to_organizations(
    user_id: str,
    organizations: List[str],
    prisma_client: "PrismaClient",
    user_api_key_dict: UserAPIKeyAuth,
):
    """
    Add a user to organizations
    """
    from litellm.proxy.management_endpoints.organization_endpoints import (
        organization_member_add,
    )

    tasks = []
    for organization_id in organizations:
        tasks.append(
            organization_member_add(
                data=OrganizationMemberAddRequest(
                    organization_id=organization_id,
                    member=[
                        OrgMember(
                            user_id=user_id,
                            role=LitellmUserRoles.INTERNAL_USER,
                        )
                    ],
                ),
                http_request=Request(
                    scope={"type": "http", "path": "/user/new"},
                ),
                user_api_key_dict=user_api_key_dict,
            )
        )
    await asyncio.gather(*tasks, return_exceptions=True)


async def _add_user_to_team(
    user_id: str,
    team_id: str,
    user_api_key_dict: UserAPIKeyAuth,
    user_email: Optional[str] = None,
    max_budget_in_team: Optional[float] = None,
    user_role: Literal["user", "admin"] = "user",
):
    from litellm.proxy.management_endpoints.team_endpoints import team_member_add

    try:
        await team_member_add(
            data=TeamMemberAddRequest(
                team_id=team_id,
                member=Member(
                    user_id=user_id,
                    role=user_role,
                    user_email=user_email,
                ),
                max_budget_in_team=max_budget_in_team,
            ),
            user_api_key_dict=user_api_key_dict,
        )
    except HTTPException as e:
        if e.status_code == 400 and (
            "already exists" in str(e) or "doesn't exist" in str(e)
        ):
            verbose_proxy_logger.debug(
                "litellm.proxy.management_endpoints.internal_user_endpoints.new_user(): User already exists in team - {}".format(
                    str(e)
                )
            )
        else:
            verbose_proxy_logger.debug(
                "litellm.proxy.management_endpoints.internal_user_endpoints.new_user(): Exception occured - {}".format(
                    str(e)
                )
            )
    except Exception as e:
        if "already exists" in str(e) or "doesn't exist" in str(e):
            verbose_proxy_logger.debug(
                "litellm.proxy.management_endpoints.internal_user_endpoints.new_user(): User already exists in team - {}".format(
                    str(e)
                )
            )
        elif (
            isinstance(e, ProxyException)
            and ProxyErrorTypes.team_member_already_in_team in e.type
        ):
            verbose_proxy_logger.debug(
                "litellm.proxy.management_endpoints.internal_user_endpoints.new_user(): User already exists in team - {}".format(
                    str(e)
                )
            )
        else:
            raise e


def check_if_default_team_set() -> Optional[Union[List[str], List[NewUserRequestTeam]]]:
    if litellm.default_internal_user_params is None:
        return None
    teams = litellm.default_internal_user_params.get("teams")
    if teams is not None:
        if all(isinstance(team, str) for team in teams):
            return teams
        elif all(isinstance(team, dict) for team in teams):
            return [
                NewUserRequestTeam(
                    team_id=team.get("team_id"),
                    max_budget_in_team=team.get("max_budget_in_team"),
                    user_role=team.get("user_role", "user"),
                )
                for team in teams
            ]
        else:
            verbose_proxy_logger.error(
                "Invalid team type in default internal user params: %s",
                teams,
            )
    return None


@router.post(
    "/user/new",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=NewUserResponse,
)
@management_endpoint_wrapper
async def new_user(
    data: NewUserRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Use this to create a new INTERNAL user with a budget.
    Internal Users can access LiteLLM Admin UI to make keys, request access to models.
    This creates a new user and generates a new api key for the new user. The new api key is returned.

    Returns user id, budget + new key.

    Parameters:
    - user_id: Optional[str] - Specify a user id. If not set, a unique id will be generated.
    - user_alias: Optional[str] - A descriptive name for you to know who this user id refers to.
    - teams: Optional[list] - specify a list of team id's a user belongs to.
    - user_email: Optional[str] - Specify a user email.
    - send_invite_email: Optional[bool] - Specify if an invite email should be sent.
    - user_role: Optional[str] - Specify a user role - "proxy_admin", "proxy_admin_viewer", "internal_user", "internal_user_viewer", "team", "customer". Info about each role here: `https://github.com/BerriAI/litellm/litellm/proxy/_types.py#L20`
    - max_budget: Optional[float] - Specify max budget for a given user.
    - budget_duration: Optional[str] - Budget is reset at the end of specified duration. If not set, budget is never reset. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d"), months ("1mo").
    - models: Optional[list] - Model_name's a user is allowed to call. (if empty, key is allowed to call all models). Set to ['no-default-models'] to block all model access. Restricting user to only team-based model access.
    - tpm_limit: Optional[int] - Specify tpm limit for a given user (Tokens per minute)
    - rpm_limit: Optional[int] - Specify rpm limit for a given user (Requests per minute)
    - auto_create_key: bool - Default=True. Flag used for returning a key as part of the /user/new response
    - aliases: Optional[dict] - Model aliases for the user - [Docs](https://litellm.vercel.app/docs/proxy/virtual_keys#model-aliases)
    - config: Optional[dict] - [DEPRECATED PARAM] User-specific config.
    - allowed_cache_controls: Optional[list] - List of allowed cache control values. Example - ["no-cache", "no-store"]. See all values - https://docs.litellm.ai/docs/proxy/caching#turn-on--off-caching-per-request-
    - blocked: Optional[bool] - [Not Implemented Yet] Whether the user is blocked.
    - guardrails: Optional[List[str]] - [Not Implemented Yet] List of active guardrails for the user
    - permissions: Optional[dict] - [Not Implemented Yet] User-specific permissions, eg. turning off pii masking.
    - metadata: Optional[dict] - Metadata for user, store information for user. Example metadata = {"team": "core-infra", "app": "app2", "email": "ishaan@berri.ai" }
    - max_parallel_requests: Optional[int] - Rate limit a user based on the number of parallel requests. Raises 429 error, if user's parallel requests > x.
    - soft_budget: Optional[float] - Get alerts when user crosses given budget, doesn't block requests.
    - model_max_budget: Optional[dict] - Model-specific max budget for user. [Docs](https://docs.litellm.ai/docs/proxy/users#add-model-specific-budgets-to-keys)
    - model_rpm_limit: Optional[float] - Model-specific rpm limit for user. [Docs](https://docs.litellm.ai/docs/proxy/users#add-model-specific-limits-to-keys)
    - model_tpm_limit: Optional[float] - Model-specific tpm limit for user. [Docs](https://docs.litellm.ai/docs/proxy/users#add-model-specific-limits-to-keys)
    - spend: Optional[float] - Amount spent by user. Default is 0. Will be updated by proxy whenever user is used. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d"), months ("1mo").
    - team_id: Optional[str] - [DEPRECATED PARAM] The team id of the user. Default is None. 
    - duration: Optional[str] - Duration for the key auto-created on `/user/new`. Default is None.
    - key_alias: Optional[str] - Alias for the key auto-created on `/user/new`. Default is None.
    - sso_user_id: Optional[str] - The id of the user in the SSO provider.
    - object_permission: Optional[LiteLLM_ObjectPermissionBase] - internal user-specific object permission. Example - {"vector_stores": ["vector_store_1", "vector_store_2"]}. IF null or {} then no object permission.
    - organizations: List[str] - List of organization id's the user is a member of
    Returns:
    - key: (str) The generated api key for the user
    - expires: (datetime) Datetime object for when key expires.
    - user_id: (str) Unique user id - used for tracking spend across multiple keys for same user id.
    - max_budget: (float|None) Max budget for given user.

    Usage Example 

    ```shell
     curl -X POST "http://localhost:4000/user/new" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer sk-1234" \
     -d '{
         "username": "new_user",
         "email": "new_user@example.com"
     }'
    ```
    """
    try:
        from litellm.proxy.proxy_server import _license_check, prisma_client

        if prisma_client is None:
            raise HTTPException(
                status_code=400, detail=CommonProxyErrors.db_not_connected_error.value
            )

        if prisma_client is None:
            raise HTTPException(
                status_code=500,
                detail=CommonProxyErrors.db_not_connected_error.value,
            )
        # Check for duplicate email
        await _check_duplicate_user_email(data.user_email, prisma_client)

        # Check if license is over limit
        total_users = await prisma_client.db.litellm_usertable.count()
        if total_users and _license_check.is_over_limit(total_users=total_users):
            raise HTTPException(
                status_code=403,
                detail="License is over limit. Please contact support@berri.ai to upgrade your license.",
            )

        data_json = data.json()  # type: ignore
        data_json = _update_internal_new_user_params(data_json, data)
        teams = data.teams
        if teams is None:
            teams = check_if_default_team_set()
        organization_ids = cast(
            Optional[List[str]], data_json.pop("organizations", None)
        )

        response = await generate_key_helper_fn(request_type="user", **data_json)
        # Admin UI Logic
        # Add User to Team and Organization
        # if team_id passed add this user to the team
        _team_id = data_json.get("team_id", None)
        if _team_id is not None:
            await _add_user_to_team(
                user_id=cast(str, response.get("user_id")),
                team_id=_team_id,
                user_api_key_dict=user_api_key_dict,
                user_email=data.user_email,
                max_budget_in_team=None,
                user_role="user",
            )
        elif teams is not None:
            tasks = []
            for team in teams:
                max_budget_in_team: Optional[float] = None
                user_role: Literal["user", "admin"] = "user"
                if isinstance(team, str):
                    team_id = team
                elif isinstance(team, NewUserRequestTeam):
                    team_id = team.team_id
                    max_budget_in_team = team.max_budget_in_team
                    user_role = team.user_role
                else:
                    raise ValueError(f"Invalid team type: {type(team)}")

                tasks.append(
                    _add_user_to_team(
                        user_id=cast(str, response.get("user_id")),
                        team_id=team_id,
                        user_email=data.user_email,
                        user_api_key_dict=user_api_key_dict,
                        max_budget_in_team=max_budget_in_team,
                        user_role=user_role,
                    )
                )
            await asyncio.gather(*tasks, return_exceptions=True)

        user_id = cast(Optional[str], response.get("user_id", None))

        if organization_ids is not None and user_id is not None:
            await _add_user_to_organizations(
                user_id=user_id,
                organizations=organization_ids,
                prisma_client=prisma_client,
                user_api_key_dict=user_api_key_dict,
            )

        special_keys = ["token", "token_id"]
        response_dict = {}
        for key, value in response.items():
            if key in NewUserResponse.model_fields.keys() and key not in special_keys:
                response_dict[key] = value

        response_dict["key"] = response.get("token", "")

        new_user_response = NewUserResponse(**response_dict)

        #########################################################
        ########## USER CREATED HOOK ################
        #########################################################
        asyncio.create_task(
            UserManagementEventHooks.async_user_created_hook(
                data=data,
                response=new_user_response,
                user_api_key_dict=user_api_key_dict,
            )
        )
        #########################################################
        ########## END USER CREATED HOOK ################
        #########################################################

        return new_user_response
    except Exception as e:
        verbose_proxy_logger.exception(
            "/user/new: Exception occured - {}".format(str(e))
        )
        raise handle_exception_on_proxy(e)


@router.get(
    "/user/available_roles",
    tags=["Internal User management"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def ui_get_available_role(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Endpoint used by Admin UI to show all available roles to assign a user
    return {
        "proxy_admin": {
            "description": "Proxy Admin role",
            "ui_label": "Admin"
        }
    }
    """

    _data_to_return = {}
    for role in LitellmUserRoles:
        # We only show a subset of roles on UI
        if role in [
            LitellmUserRoles.PROXY_ADMIN,
            LitellmUserRoles.PROXY_ADMIN_VIEW_ONLY,
            LitellmUserRoles.INTERNAL_USER,
            LitellmUserRoles.INTERNAL_USER_VIEW_ONLY,
        ]:
            _data_to_return[role.value] = {
                "description": role.description,
                "ui_label": role.ui_label,
            }
    return _data_to_return


def get_team_from_list(
    team_list: Optional[Union[List[LiteLLM_TeamTable], List[TeamListResponseObject]]],
    team_id: str,
) -> Optional[Union[LiteLLM_TeamTable, LiteLLM_TeamMembership]]:
    if team_list is None:
        return None

    for team in team_list:
        if team.team_id == team_id:
            return team
    return None


def get_user_id_from_request(request: Request) -> Optional[str]:
    """
    Get the user id from the request
    """
    # Get the raw query string and parse it properly to handle + characters
    user_id: Optional[str] = None
    query_string = str(request.url.query)
    if "user_id=" in query_string:
        # Extract the user_id value from the raw query string
        import re
        from urllib.parse import unquote

        match = re.search(r"user_id=([^&]*)", query_string)
        if match:
            # Use unquote instead of unquote_plus to preserve + characters
            raw_user_id = unquote(match.group(1))
            user_id = raw_user_id
    return user_id


@router.get(
    "/user/info",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
    # response_model=UserInfoResponse,
)
@management_endpoint_wrapper
async def user_info(
    request: Request,
    user_id: Optional[str] = fastapi.Query(
        default=None, description="User ID in the request parameters"
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [10/07/2024]
    Note: To get all users (+pagination), use `/user/list` endpoint.


    Use this to get user information. (user row + all user key info)

    Example request
    ```
    curl -X GET 'http://localhost:4000/user/info?user_id=krrish7%40berri.ai' \
    --header 'Authorization: Bearer sk-1234'
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    try:
        # Handle URL encoding properly by getting user_id from the original request
        if (
            user_id is not None and " " in user_id
        ):  # if user_id is not None and contains a space, get the user_id from the request - this is to handle the case where the user_id is encoded in the url
            user_id = get_user_id_from_request(request=request)

        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )
        if (
            user_id is None
            and user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN
        ):
            return await _get_user_info_for_proxy_admin()
        elif user_id is None:
            user_id = user_api_key_dict.user_id
        ## GET USER ROW ##

        if user_id is not None:
            user_info = await prisma_client.get_data(user_id=user_id)
        else:
            user_info = None

        ## GET ALL TEAMS ##
        team_list = []
        team_id_list = []
        from litellm.proxy.management_endpoints.team_endpoints import list_team

        teams_1 = await list_team(
            http_request=Request(
                scope={"type": "http", "path": "/user/info"},
            ),
            user_id=user_id,
            user_api_key_dict=user_api_key_dict,
        )

        if teams_1 is not None and isinstance(teams_1, list):
            team_list = teams_1
            for team in teams_1:
                team_id_list.append(team.team_id)

        teams_2: Optional[Any] = None
        if user_info is not None:
            # *NEW* get all teams in user 'teams' field
            teams_2 = await prisma_client.get_data(
                team_id_list=user_info.teams, table_name="team", query_type="find_all"
            )

            if teams_2 is not None and isinstance(teams_2, list):
                for team in teams_2:
                    if team.team_id not in team_id_list:
                        team_list.append(team)
                        team_id_list.append(team.team_id)

        elif (
            user_api_key_dict.user_id is not None and user_id is None
        ):  # the key querying the endpoint is the one asking for it's teams
            caller_user_info = await prisma_client.get_data(
                user_id=user_api_key_dict.user_id
            )
            # *NEW* get all teams in user 'teams' field
            if caller_user_info is not None:
                teams_2 = await prisma_client.get_data(
                    team_id_list=caller_user_info.teams,
                    table_name="team",
                    query_type="find_all",
                )

            if teams_2 is not None and isinstance(teams_2, list):
                for team in teams_2:
                    if team.team_id not in team_id_list:
                        team_list.append(team)
                        team_id_list.append(team.team_id)

        ## GET ALL KEYS ##
        keys = await prisma_client.get_data(
            user_id=user_id,
            table_name="key",
            query_type="find_all",
        )

        if user_info is None and keys is not None:
            ## make sure we still return a total spend ##
            spend = 0
            for k in keys:
                spend += getattr(k, "spend", 0)
            user_info = {"spend": spend}

        ## REMOVE HASHED TOKEN INFO before returning ##
        returned_keys = _process_keys_for_user_info(keys=keys, all_teams=teams_1)
        team_list.sort(key=lambda x: (getattr(x, "team_alias", "") or ""))
        _user_info = (
            user_info.model_dump() if isinstance(user_info, BaseModel) else user_info
        )
        response_data = UserInfoResponse(
            user_id=user_id, user_info=_user_info, keys=returned_keys, teams=team_list
        )

        return response_data
    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.user_info(): Exception occured - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)


async def _get_user_info_for_proxy_admin():
    """
    Admin UI Endpoint - Returns All Teams and Keys when Proxy Admin is querying

    - get all teams in LiteLLM_TeamTable
    - get all keys in LiteLLM_VerificationToken table

    Why separate helper for proxy admin ?
        - To get Faster UI load times, get all teams and virtual keys in 1 query
    """

    from litellm.proxy.proxy_server import prisma_client

    sql_query = """
        SELECT 
            (SELECT json_agg(t.*) FROM "LiteLLM_TeamTable" t) as teams,
            (SELECT json_agg(k.*) FROM "LiteLLM_VerificationToken" k WHERE k.team_id != 'litellm-dashboard' OR k.team_id IS NULL) as keys
    """
    if prisma_client is None:
        raise Exception(
            "Database not connected. Connect a database to your proxy - https://docs.litellm.ai/docs/simple_proxy#managing-auth---virtual-keys"
        )

    results = await prisma_client.db.query_raw(sql_query)

    verbose_proxy_logger.debug("results_keys: %s", results)

    _keys_in_db: List = results[0]["keys"] or []
    # cast all keys to LiteLLM_VerificationToken
    keys_in_db = []
    for key in _keys_in_db:
        if key.get("models") is None:
            key["models"] = []
        keys_in_db.append(LiteLLM_VerificationToken(**key))

    # cast all teams to LiteLLM_TeamTable
    _teams_in_db: List = results[0]["teams"] or []
    _teams_in_db = [LiteLLM_TeamTable(**team) for team in _teams_in_db]
    _teams_in_db.sort(key=lambda x: (getattr(x, "team_alias", "") or ""))
    returned_keys = _process_keys_for_user_info(keys=keys_in_db, all_teams=_teams_in_db)
    return UserInfoResponse(
        user_id=None,
        user_info=None,
        keys=returned_keys,
        teams=_teams_in_db,
    )


def _process_keys_for_user_info(
    keys: Optional[List[LiteLLM_VerificationToken]],
    all_teams: Optional[Union[List[LiteLLM_TeamTable], List[TeamListResponseObject]]],
):
    from litellm.proxy.proxy_server import general_settings, litellm_master_key_hash

    returned_keys = []
    if keys is None:
        pass
    else:
        for key in keys:
            if (
                key.token == litellm_master_key_hash
                and general_settings.get("disable_master_key_return", False)
                is True  ## [IMPORTANT] used by hosted proxy-ui to prevent sharing master key on ui
            ):
                continue

            try:
                _key: dict = key.model_dump()  # noqa
            except Exception:
                # if using pydantic v1
                _key = key.dict()
            if (
                "team_id" in _key
                and _key["team_id"] is not None
                and _key["team_id"] != "litellm-dashboard"
            ):
                team_info = get_team_from_list(
                    team_list=all_teams, team_id=_key["team_id"]
                )
                if team_info is not None:
                    team_alias = getattr(team_info, "team_alias", None)
                    _key["team_alias"] = team_alias
                else:
                    _key["team_alias"] = None
            else:
                _key["team_alias"] = "None"
            returned_keys.append(_key)
    return returned_keys


def _update_internal_user_params(data_json: dict, data: UpdateUserRequest) -> dict:
    non_default_values = {}
    for k, v in data_json.items():
        if (
            v is not None
            and v
            not in (
                [],
                {},
            )
            and k not in LiteLLM_ManagementEndpoint_MetadataFields
        ):  # models default to [], spend defaults to 0, we should not reset these values
            non_default_values[k] = v

    is_internal_user = False
    if data.user_role == LitellmUserRoles.INTERNAL_USER:
        is_internal_user = True

    if "budget_duration" in non_default_values:
        from litellm.proxy.common_utils.timezone_utils import get_budget_reset_time

        non_default_values["budget_reset_at"] = get_budget_reset_time(
            budget_duration=non_default_values["budget_duration"]
        )

    if "max_budget" not in non_default_values:
        if (
            is_internal_user and litellm.max_internal_user_budget is not None
        ):  # applies internal user limits, if user role updated
            non_default_values["max_budget"] = litellm.max_internal_user_budget

    if (
        "budget_duration" not in non_default_values
    ):  # applies internal user limits, if user role updated
        if is_internal_user and litellm.internal_user_budget_duration is not None:
            non_default_values["budget_duration"] = (
                litellm.internal_user_budget_duration
            )
            from litellm.proxy.common_utils.timezone_utils import get_budget_reset_time

            non_default_values["budget_reset_at"] = get_budget_reset_time(
                budget_duration=non_default_values["budget_duration"]
            )

    return non_default_values


@router.post(
    "/user/update",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def user_update(
    data: UpdateUserRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Example curl 

    ```
    curl --location 'http://0.0.0.0:4000/user/update' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
        "user_id": "test-litellm-user-4",
        "user_role": "proxy_admin_viewer"
    }'
    ```
    
    Parameters:
        - user_id: Optional[str] - Specify a user id. If not set, a unique id will be generated.
        - user_email: Optional[str] - Specify a user email.
        - password: Optional[str] - Specify a user password.
        - user_alias: Optional[str] - A descriptive name for you to know who this user id refers to.
        - teams: Optional[list] - specify a list of team id's a user belongs to.
        - send_invite_email: Optional[bool] - Specify if an invite email should be sent.
        - user_role: Optional[str] - Specify a user role - "proxy_admin", "proxy_admin_viewer", "internal_user", "internal_user_viewer", "team", "customer". Info about each role here: `https://github.com/BerriAI/litellm/litellm/proxy/_types.py#L20`
        - max_budget: Optional[float] - Specify max budget for a given user.
        - budget_duration: Optional[str] - Budget is reset at the end of specified duration. If not set, budget is never reset. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d"), months ("1mo").
        - models: Optional[list] - Model_name's a user is allowed to call. (if empty, key is allowed to call all models)
        - tpm_limit: Optional[int] - Specify tpm limit for a given user (Tokens per minute)
        - rpm_limit: Optional[int] - Specify rpm limit for a given user (Requests per minute)
        - auto_create_key: bool - Default=True. Flag used for returning a key as part of the /user/new response
        - aliases: Optional[dict] - Model aliases for the user - [Docs](https://litellm.vercel.app/docs/proxy/virtual_keys#model-aliases)
        - config: Optional[dict] - [DEPRECATED PARAM] User-specific config.
        - allowed_cache_controls: Optional[list] - List of allowed cache control values. Example - ["no-cache", "no-store"]. See all values - https://docs.litellm.ai/docs/proxy/caching#turn-on--off-caching-per-request-
        - blocked: Optional[bool] - [Not Implemented Yet] Whether the user is blocked.
        - guardrails: Optional[List[str]] - [Not Implemented Yet] List of active guardrails for the user
        - permissions: Optional[dict] - [Not Implemented Yet] User-specific permissions, eg. turning off pii masking.
        - metadata: Optional[dict] - Metadata for user, store information for user. Example metadata = {"team": "core-infra", "app": "app2", "email": "ishaan@berri.ai" }
        - max_parallel_requests: Optional[int] - Rate limit a user based on the number of parallel requests. Raises 429 error, if user's parallel requests > x.
        - soft_budget: Optional[float] - Get alerts when user crosses given budget, doesn't block requests.
        - model_max_budget: Optional[dict] - Model-specific max budget for user. [Docs](https://docs.litellm.ai/docs/proxy/users#add-model-specific-budgets-to-keys)
        - model_rpm_limit: Optional[float] - Model-specific rpm limit for user. [Docs](https://docs.litellm.ai/docs/proxy/users#add-model-specific-limits-to-keys)
        - model_tpm_limit: Optional[float] - Model-specific tpm limit for user. [Docs](https://docs.litellm.ai/docs/proxy/users#add-model-specific-limits-to-keys)
        - spend: Optional[float] - Amount spent by user. Default is 0. Will be updated by proxy whenever user is used. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d"), months ("1mo").
        - team_id: Optional[str] - [DEPRECATED PARAM] The team id of the user. Default is None. 
        - duration: Optional[str] - [NOT IMPLEMENTED].
        - key_alias: Optional[str] - [NOT IMPLEMENTED].
        - object_permission: Optional[LiteLLM_ObjectPermissionBase] - internal user-specific object permission. Example - {"vector_stores": ["vector_store_1", "vector_store_2"]}. IF null or {} then no object permission.
    
    """
    from litellm.proxy.proxy_server import litellm_proxy_admin_name, prisma_client

    try:
        data_json: dict = data.model_dump(exclude_unset=True)
        # get the row from db
        if prisma_client is None:
            raise Exception("Not connected to DB!")

        # get non default values for key
        non_default_values = _update_internal_user_params(
            data_json=data_json, data=data
        )

        existing_user_row: Optional[BaseModel] = None
        if data.user_id is not None:
            existing_user_row = await prisma_client.db.litellm_usertable.find_first(
                where={"user_id": data.user_id}
            )
            if existing_user_row is not None:
                existing_user_row = LiteLLM_UserTable(
                    **existing_user_row.model_dump(exclude_none=True)
                )

        existing_metadata = (
            cast(Dict, getattr(existing_user_row, "metadata", {}) or {})
            if existing_user_row is not None
            else {}
        )

        non_default_values = prepare_metadata_fields(
            data=data,
            non_default_values=non_default_values,
            existing_metadata=existing_metadata or {},
        )

        ## ADD USER, IF NEW ##
        verbose_proxy_logger.debug("/user/update: Received data = %s", data)
        response: Optional[Any] = None
        if data.user_id is not None and len(data.user_id) > 0:
            non_default_values["user_id"] = data.user_id  # type: ignore
            verbose_proxy_logger.debug("In update user, user_id condition block.")
            response = await prisma_client.update_data(
                user_id=data.user_id,
                data=non_default_values,
                table_name="user",
            )
            verbose_proxy_logger.debug(
                f"received response from updating prisma client. response={response}"
            )
        elif data.user_email is not None:
            non_default_values["user_id"] = str(uuid.uuid4())
            non_default_values["user_email"] = data.user_email
            ## user email is not unique acc. to prisma schema -> future improvement
            ### for now: check if it exists in db, if not - insert it
            existing_user_rows = await prisma_client.get_data(
                key_val={"user_email": data.user_email},
                table_name="user",
                query_type="find_all",
            )
            if existing_user_rows is None or (
                isinstance(existing_user_rows, list) and len(existing_user_rows) == 0
            ):
                response = await prisma_client.insert_data(
                    data=non_default_values, table_name="user"
                )
            elif isinstance(existing_user_rows, list) and len(existing_user_rows) > 0:
                for existing_user in existing_user_rows:
                    response = await prisma_client.update_data(
                        user_id=existing_user.user_id,
                        data=non_default_values,
                        table_name="user",
                    )

        if response is not None:  # emit audit log
            try:
                user_row: BaseModel = (
                    await prisma_client.db.litellm_usertable.find_first(
                        where={"user_id": response["user_id"]}
                    )
                )

                user_row_litellm_typed = LiteLLM_UserTable(
                    **user_row.model_dump(exclude_none=True)
                )

                asyncio.create_task(
                    UserManagementEventHooks.create_internal_user_audit_log(
                        user_id=user_row_litellm_typed.user_id,
                        action="updated",
                        litellm_changed_by=user_api_key_dict.user_id,
                        user_api_key_dict=user_api_key_dict,
                        litellm_proxy_admin_name=litellm_proxy_admin_name,
                        before_value=(
                            existing_user_row.model_dump_json(exclude_none=True)
                            if existing_user_row
                            else None
                        ),
                        after_value=user_row_litellm_typed.model_dump_json(
                            exclude_none=True
                        ),
                    )
                )
            except Exception as e:
                verbose_proxy_logger.warning(
                    "Unable to create audit log for user on `/user/update` - {}".format(
                        str(e)
                    )
                )
        return response  # type: ignore
        # update based on remaining passed in values
    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.user_update(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Authentication Error({str(e)})"),
                type=ProxyErrorTypes.auth_error,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Authentication Error, " + str(e),
            type=ProxyErrorTypes.auth_error,
            param=getattr(e, "param", "None"),
            code=status.HTTP_400_BAD_REQUEST,
        )


async def get_user_key_counts(
    prisma_client,
    user_ids: Optional[List[str]] = None,
):
    """
    Helper function to get the count of keys for each user using Prisma's count method.

    Args:
        prisma_client: The Prisma client instance
        user_ids: List of user IDs to get key counts for

    Returns:
        Dictionary mapping user_id to key count
    """
    from litellm.constants import UI_SESSION_TOKEN_TEAM_ID

    if not user_ids or len(user_ids) == 0:
        return {}

    result = {}

    # Get count for each user_id individually
    for user_id in user_ids:
        count = await prisma_client.db.litellm_verificationtoken.count(
            where={
                "user_id": user_id,
                "OR": [
                    {"team_id": None},
                    {"team_id": {"not": UI_SESSION_TOKEN_TEAM_ID}},
                ],
            }
        )
        result[user_id] = count

    return result


def _validate_sort_params(
    sort_by: Optional[str], sort_order: str
) -> Optional[Dict[str, str]]:
    order_by: Dict[str, str] = {}

    if sort_by is None:
        return None
    # Validate sort_by is a valid column
    valid_columns = [
        "user_id",
        "user_email",
        "created_at",
        "spend",
        "user_alias",
        "user_role",
    ]
    if sort_by not in valid_columns:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Invalid sort column. Must be one of: {', '.join(valid_columns)}"
            },
        )

    # Validate sort_order
    if sort_order.lower() not in ["asc", "desc"]:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid sort order. Must be 'asc' or 'desc'"},
        )

    order_by[sort_by] = sort_order.lower()

    return order_by


@router.get(
    "/user/list",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=UserListResponse,
)
async def get_users(
    role: Optional[str] = fastapi.Query(
        default=None, description="Filter users by role"
    ),
    user_ids: Optional[str] = fastapi.Query(
        default=None, description="Get list of users by user_ids"
    ),
    sso_user_ids: Optional[str] = fastapi.Query(
        default=None, description="Get list of users by sso_user_id"
    ),
    user_email: Optional[str] = fastapi.Query(
        default=None, description="Filter users by partial email match"
    ),
    team: Optional[str] = fastapi.Query(
        default=None, description="Filter users by team id"
    ),
    page: int = fastapi.Query(default=1, ge=1, description="Page number"),
    page_size: int = fastapi.Query(
        default=25, ge=1, le=100, description="Number of items per page"
    ),
    sort_by: Optional[str] = fastapi.Query(
        default=None,
        description="Column to sort by (e.g. 'user_id', 'user_email', 'created_at', 'spend')",
    ),
    sort_order: str = fastapi.Query(
        default="asc", description="Sort order ('asc' or 'desc')"
    ),
):
    """
    Get a paginated list of users with filtering and sorting options.

    Parameters:
        role: Optional[str]
            Filter users by role. Can be one of:
            - proxy_admin
            - proxy_admin_viewer
            - internal_user
            - internal_user_viewer
        user_ids: Optional[str]
            Get list of users by user_ids. Comma separated list of user_ids.
        sso_ids: Optional[str]
            Get list of users by sso_ids. Comma separated list of sso_ids.
        user_email: Optional[str]
            Filter users by partial email match
        team: Optional[str]
            Filter users by team id. Will match if user has this team in their teams array.
        page: int
            The page number to return
        page_size: int
            The number of items per page
        sort_by: Optional[str]
            Column to sort by (e.g. 'user_id', 'user_email', 'created_at', 'spend')
        sort_order: Optional[str]
            Sort order ('asc' or 'desc')
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": f"No db connected. prisma client={prisma_client}"},
        )

    # Calculate skip and take for pagination
    skip = (page - 1) * page_size

    # Build where conditions based on provided parameters
    where_conditions: Dict[str, Any] = {}

    if role:
        where_conditions["user_role"] = role  # Exact match instead of contains

    if user_ids and isinstance(user_ids, str):
        user_id_list = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
        where_conditions["user_id"] = {
            "in": user_id_list,
        }

    if user_email is not None and isinstance(user_email, str):
        where_conditions["user_email"] = {
            "contains": user_email,
            "mode": "insensitive",  # Case-insensitive search
        }

    if team is not None and isinstance(team, str):
        where_conditions["teams"] = {
            "has": team  # Array contains for string arrays in Prisma
        }

    if sso_user_ids is not None and isinstance(sso_user_ids, str):
        sso_id_list = [sid.strip() for sid in sso_user_ids.split(",") if sid.strip()]
        where_conditions["sso_user_id"] = {
            "in": sso_id_list,
        }

    ## Filter any none fastapi.Query params - e.g. where_conditions: {'user_email': {'contains': Query(None), 'mode': 'insensitive'}, 'teams': {'has': Query(None)}}
    where_conditions = {k: v for k, v in where_conditions.items() if v is not None}

    # Build order_by conditions

    order_by: Optional[Dict[str, str]] = (
        _validate_sort_params(sort_by, sort_order)
        if sort_by is not None and isinstance(sort_by, str)
        else None
    )

    users = await prisma_client.db.litellm_usertable.find_many(
        where=where_conditions,
        skip=skip,
        take=page_size,
        order=(
            order_by if order_by else {"created_at": "desc"}
        ),  # Default to created_at desc if no sort specified
    )

    # Get total count of user rows
    total_count = await prisma_client.db.litellm_usertable.count(where=where_conditions)

    # Get key count for each user
    if users is not None:
        user_key_counts = await get_user_key_counts(
            prisma_client, [user.user_id for user in users]
        )
    else:
        user_key_counts = {}

    verbose_proxy_logger.debug(f"Total count of users: {total_count}")

    # Calculate total pages
    total_pages = -(-total_count // page_size)  # Ceiling division

    # Prepare response
    user_list: List[LiteLLM_UserTableWithKeyCount] = []
    if users is not None:
        for user in users:
            user_list.append(
                LiteLLM_UserTableWithKeyCount(
                    **user.model_dump(), key_count=user_key_counts.get(user.user_id, 0)
                )
            )
    else:
        user_list = []

    return {
        "users": user_list,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post(
    "/user/delete",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def delete_user(
    data: DeleteUserRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    litellm_changed_by: Optional[str] = Header(
        None,
        description="The litellm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
):
    """
    delete user and associated user keys

    ```
    curl --location 'http://0.0.0.0:4000/user/delete' \

    --header 'Authorization: Bearer sk-1234' \

    --header 'Content-Type: application/json' \

    --data-raw '{
        "user_ids": ["45e3e396-ee08-4a61-a88e-16b3ce7e0849"]
    }'
    ```

    Parameters:
    - user_ids: List[str] - The list of user id's to be deleted.
    """
    from litellm.proxy.proxy_server import (
        create_audit_log_for_update,
        litellm_proxy_admin_name,
        prisma_client,
    )

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    if data.user_ids is None:
        raise HTTPException(status_code=400, detail={"error": "No user id passed in"})

    # check that all teams passed exist
    for user_id in data.user_ids:
        user_row = await prisma_client.db.litellm_usertable.find_unique(
            where={"user_id": user_id}
        )

        if user_row is None:
            raise HTTPException(
                status_code=404,
                detail={"error": f"User not found, passed user_id={user_id}"},
            )
        else:
            # Enterprise Feature - Audit Logging. Enable with litellm.store_audit_logs = True
            # we do this after the first for loop, since first for loop is for validation. we only want this inserted after validation passes
            if litellm.store_audit_logs is True:
                # make an audit log for each team deleted
                _user_row = user_row.json(exclude_none=True)

                asyncio.create_task(
                    create_audit_log_for_update(
                        request_data=LiteLLM_AuditLogs(
                            id=str(uuid.uuid4()),
                            updated_at=datetime.now(timezone.utc),
                            changed_by=litellm_changed_by
                            or user_api_key_dict.user_id
                            or litellm_proxy_admin_name,
                            changed_by_api_key=user_api_key_dict.api_key,
                            table_name=LitellmTableNames.USER_TABLE_NAME,
                            object_id=user_id,
                            action="deleted",
                            updated_values="{}",
                            before_value=_user_row,
                        )
                    )
                )

    # End of Audit logging

    ## DELETE ASSOCIATED KEYS
    await prisma_client.db.litellm_verificationtoken.delete_many(
        where={"user_id": {"in": data.user_ids}}
    )

    ## DELETE ASSOCIATED INVITATION LINKS
    await prisma_client.db.litellm_invitationlink.delete_many(
        where={"user_id": {"in": data.user_ids}}
    )

    ## DELETE ASSOCIATED ORGANIZATION MEMBERSHIPS
    await prisma_client.db.litellm_organizationmembership.delete_many(
        where={"user_id": {"in": data.user_ids}}
    )

    ## DELETE USERS
    deleted_users = await prisma_client.db.litellm_usertable.delete_many(
        where={"user_id": {"in": data.user_ids}}
    )

    return deleted_users


async def add_internal_user_to_organization(
    user_id: str,
    organization_id: str,
    user_role: LitellmUserRoles,
):
    """
    Helper function to add an internal user to an organization

    Adds the user to LiteLLM_OrganizationMembership table

    - Checks if organization_id exists

    Raises:
    - Exception if database not connected
    - Exception if user_id or organization_id not found
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise Exception("Database not connected")

    try:
        # Check if organization_id exists
        organization_row = await prisma_client.db.litellm_organizationtable.find_unique(
            where={"organization_id": organization_id}
        )
        if organization_row is None:
            raise Exception(
                f"Organization not found, passed organization_id={organization_id}"
            )

        # Create a new organization membership entry
        new_membership = await prisma_client.db.litellm_organizationmembership.create(
            data={
                "user_id": user_id,
                "organization_id": organization_id,
                "user_role": user_role,
                # Note: You can also set budget within an organization if needed
            }
        )

        return new_membership
    except Exception as e:
        raise Exception(f"Failed to add user to organization: {str(e)}")


@router.get(
    "/user/filter/ui",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
    responses={
        200: {"model": List[LiteLLM_UserTableFiltered]},
    },
)
async def ui_view_users(
    user_id: Optional[str] = fastapi.Query(
        default=None, description="User ID in the request parameters"
    ),
    user_email: Optional[str] = fastapi.Query(
        default=None, description="User email in the request parameters"
    ),
    page: int = fastapi.Query(
        default=1, description="Page number for pagination", ge=1
    ),
    page_size: int = fastapi.Query(
        default=50, description="Number of items per page", ge=1, le=100
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [PROXY-ADMIN ONLY]Filter users based on partial match of user_id or email with pagination.

    Args:
        user_id (Optional[str]): Partial user ID to search for
        user_email (Optional[str]): Partial email to search for
        page (int): Page number for pagination (starts at 1)
        page_size (int): Number of items per page (max 100)
        user_api_key_dict (UserAPIKeyAuth): User authentication information

    Returns:
        List[LiteLLM_SpendLogs]: Paginated list of matching user records
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    try:
        # Calculate offset for pagination
        skip = (page - 1) * page_size

        # Build where conditions based on provided parameters
        where_conditions = {}

        if user_id:
            where_conditions["user_id"] = {
                "contains": user_id,
                "mode": "insensitive",  # Case-insensitive search
            }

        if user_email:
            where_conditions["user_email"] = {
                "contains": user_email,
                "mode": "insensitive",  # Case-insensitive search
            }

        # Query users with pagination and filters
        users: Optional[List[BaseModel]] = (
            await prisma_client.db.litellm_usertable.find_many(
                where=where_conditions,
                skip=skip,
                take=page_size,
                order={"created_at": "desc"},
            )
        )

        if not users:
            return []

        return [LiteLLM_UserTableFiltered(**user.model_dump()) for user in users]

    except Exception as e:
        verbose_proxy_logger.exception(f"Error searching users: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching users: {str(e)}")


def update_metrics(
    group_metrics: SpendMetrics, record: LiteLLM_DailyUserSpend
) -> SpendMetrics:
    group_metrics.spend += record.spend
    group_metrics.prompt_tokens += record.prompt_tokens
    group_metrics.completion_tokens += record.completion_tokens
    group_metrics.cache_read_input_tokens += record.cache_read_input_tokens
    group_metrics.cache_creation_input_tokens += record.cache_creation_input_tokens
    group_metrics.total_tokens += record.prompt_tokens + record.completion_tokens
    group_metrics.api_requests += record.api_requests
    group_metrics.successful_requests += record.successful_requests
    group_metrics.failed_requests += record.failed_requests
    return group_metrics


def update_breakdown_metrics(
    breakdown: BreakdownMetrics,
    record: LiteLLM_DailyUserSpend,
    model_metadata: Dict[str, Dict[str, Any]],
    provider_metadata: Dict[str, Dict[str, Any]],
    api_key_metadata: Dict[str, Dict[str, Any]],
) -> BreakdownMetrics:
    """Updates breakdown metrics for a single record using the existing update_metrics function"""

    # Update model breakdown
    if record.model not in breakdown.models:
        breakdown.models[record.model] = MetricWithMetadata(
            metrics=SpendMetrics(),
            metadata=model_metadata.get(
                record.model, {}
            ),  # Add any model-specific metadata here
        )
    breakdown.models[record.model].metrics = update_metrics(
        breakdown.models[record.model].metrics, record
    )

    # Update provider breakdown
    provider = record.custom_llm_provider or "unknown"
    if provider not in breakdown.providers:
        breakdown.providers[provider] = MetricWithMetadata(
            metrics=SpendMetrics(),
            metadata=provider_metadata.get(
                provider, {}
            ),  # Add any provider-specific metadata here
        )
    breakdown.providers[provider].metrics = update_metrics(
        breakdown.providers[provider].metrics, record
    )

    # Update api key breakdown
    if record.api_key not in breakdown.api_keys:
        breakdown.api_keys[record.api_key] = KeyMetricWithMetadata(
            metrics=SpendMetrics(),
            metadata=KeyMetadata(
                key_alias=api_key_metadata.get(record.api_key, {}).get(
                    "key_alias", None
                )
            ),  # Add any api_key-specific metadata here
        )
    breakdown.api_keys[record.api_key].metrics = update_metrics(
        breakdown.api_keys[record.api_key].metrics, record
    )

    return breakdown


@router.get(
    "/user/daily/activity",
    tags=["Budget & Spend Tracking", "Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=SpendAnalyticsPaginatedResponse,
)
async def get_user_daily_activity(
    start_date: Optional[str] = fastapi.Query(
        default=None,
        description="Start date in YYYY-MM-DD format",
    ),
    end_date: Optional[str] = fastapi.Query(
        default=None,
        description="End date in YYYY-MM-DD format",
    ),
    model: Optional[str] = fastapi.Query(
        default=None,
        description="Filter by specific model",
    ),
    api_key: Optional[str] = fastapi.Query(
        default=None,
        description="Filter by specific API key",
    ),
    page: int = fastapi.Query(
        default=1, description="Page number for pagination", ge=1
    ),
    page_size: int = fastapi.Query(
        default=50, description="Items per page", ge=1, le=1000
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
) -> SpendAnalyticsPaginatedResponse:
    """
    [BETA] This is a beta endpoint. It will change.

    Meant to optimize querying spend data for analytics for a user.

    Returns:
    (by date)
    - spend
    - prompt_tokens
    - completion_tokens
    - cache_read_input_tokens
    - cache_creation_input_tokens
    - total_tokens
    - api_requests
    - breakdown by model, api_key, provider
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Please provide start_date and end_date"},
        )

    try:
        entity_id: Optional[str] = None
        if not _user_has_admin_view(user_api_key_dict):
            entity_id = user_api_key_dict.user_id

        return await get_daily_activity(
            prisma_client=prisma_client,
            table_name="litellm_dailyuserspend",
            entity_id_field="user_id",
            entity_id=entity_id,
            entity_metadata_field=None,
            start_date=start_date,
            end_date=end_date,
            model=model,
            api_key=api_key,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        verbose_proxy_logger.exception(
            "/spend/daily/analytics: Exception occured - {}".format(str(e))
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to fetch analytics: {str(e)}"},
        )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\modula2.py ===
"""
    pygments.lexers.modula2
    ~~~~~~~~~~~~~~~~~~~~~~~

    Multi-Dialect Lexer for Modula-2.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include
from pygments.util import get_bool_opt, get_list_opt
from pygments.token import Text, Comment, Operator, Keyword, Name, \
    String, Number, Punctuation, Error

__all__ = ['Modula2Lexer']


# Multi-Dialect Modula-2 Lexer
class Modula2Lexer(RegexLexer):
    """
    For Modula-2 source code.

    The Modula-2 lexer supports several dialects.  By default, it operates in
    fallback mode, recognising the *combined* literals, punctuation symbols
    and operators of all supported dialects, and the *combined* reserved words
    and builtins of PIM Modula-2, ISO Modula-2 and Modula-2 R10, while not
    differentiating between library defined identifiers.

    To select a specific dialect, a dialect option may be passed
    or a dialect tag may be embedded into a source file.

    Dialect Options:

    `m2pim`
        Select PIM Modula-2 dialect.
    `m2iso`
        Select ISO Modula-2 dialect.
    `m2r10`
        Select Modula-2 R10 dialect.
    `objm2`
        Select Objective Modula-2 dialect.

    The PIM and ISO dialect options may be qualified with a language extension.

    Language Extensions:

    `+aglet`
        Select Aglet Modula-2 extensions, available with m2iso.
    `+gm2`
        Select GNU Modula-2 extensions, available with m2pim.
    `+p1`
        Select p1 Modula-2 extensions, available with m2iso.
    `+xds`
        Select XDS Modula-2 extensions, available with m2iso.


    Passing a Dialect Option via Unix Commandline Interface

    Dialect options may be passed to the lexer using the `dialect` key.
    Only one such option should be passed. If multiple dialect options are
    passed, the first valid option is used, any subsequent options are ignored.

    Examples:

    `$ pygmentize -O full,dialect=m2iso -f html -o /path/to/output /path/to/input`
        Use ISO dialect to render input to HTML output
    `$ pygmentize -O full,dialect=m2iso+p1 -f rtf -o /path/to/output /path/to/input`
        Use ISO dialect with p1 extensions to render input to RTF output


    Embedding a Dialect Option within a source file

    A dialect option may be embedded in a source file in form of a dialect
    tag, a specially formatted comment that specifies a dialect option.

    Dialect Tag EBNF::

       dialectTag :
           OpeningCommentDelim Prefix dialectOption ClosingCommentDelim ;

       dialectOption :
           'm2pim' | 'm2iso' | 'm2r10' | 'objm2' |
           'm2iso+aglet' | 'm2pim+gm2' | 'm2iso+p1' | 'm2iso+xds' ;

       Prefix : '!' ;

       OpeningCommentDelim : '(*' ;

       ClosingCommentDelim : '*)' ;

    No whitespace is permitted between the tokens of a dialect tag.

    In the event that a source file contains multiple dialect tags, the first
    tag that contains a valid dialect option will be used and any subsequent
    dialect tags will be ignored.  Ideally, a dialect tag should be placed
    at the beginning of a source file.

    An embedded dialect tag overrides a dialect option set via command line.

    Examples:

    ``(*!m2r10*) DEFINITION MODULE Foobar; ...``
        Use Modula2 R10 dialect to render this source file.
    ``(*!m2pim+gm2*) DEFINITION MODULE Bazbam; ...``
        Use PIM dialect with GNU extensions to render this source file.


    Algol Publication Mode:

    In Algol publication mode, source text is rendered for publication of
    algorithms in scientific papers and academic texts, following the format
    of the Revised Algol-60 Language Report.  It is activated by passing
    one of two corresponding styles as an option:

    `algol`
        render reserved words lowercase underline boldface
        and builtins lowercase boldface italic
    `algol_nu`
        render reserved words lowercase boldface (no underlining)
        and builtins lowercase boldface italic

    The lexer automatically performs the required lowercase conversion when
    this mode is activated.

    Example:

    ``$ pygmentize -O full,style=algol -f latex -o /path/to/output /path/to/input``
        Render input file in Algol publication mode to LaTeX output.


    Rendering Mode of First Class ADT Identifiers:

    The rendering of standard library first class ADT identifiers is controlled
    by option flag "treat_stdlib_adts_as_builtins".

    When this option is turned on, standard library ADT identifiers are rendered
    as builtins.  When it is turned off, they are rendered as ordinary library
    identifiers.

    `treat_stdlib_adts_as_builtins` (default: On)

    The option is useful for dialects that support ADTs as first class objects
    and provide ADTs in the standard library that would otherwise be built-in.

    At present, only Modula-2 R10 supports library ADTs as first class objects
    and therefore, no ADT identifiers are defined for any other dialects.

    Example:

    ``$ pygmentize -O full,dialect=m2r10,treat_stdlib_adts_as_builtins=Off ...``
        Render standard library ADTs as ordinary library types.

    .. versionchanged:: 2.1
       Added multi-dialect support.
    """
    name = 'Modula-2'
    url = 'http://www.modula2.org/'
    aliases = ['modula2', 'm2']
    filenames = ['*.def', '*.mod']
    mimetypes = ['text/x-modula2']
    version_added = '1.3'

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'whitespace': [
            (r'\n+', Text),  # blank lines
            (r'\s+', Text),  # whitespace
        ],
        'dialecttags': [
            # PIM Dialect Tag
            (r'\(\*!m2pim\*\)', Comment.Special),
            # ISO Dialect Tag
            (r'\(\*!m2iso\*\)', Comment.Special),
            # M2R10 Dialect Tag
            (r'\(\*!m2r10\*\)', Comment.Special),
            # ObjM2 Dialect Tag
            (r'\(\*!objm2\*\)', Comment.Special),
            # Aglet Extensions Dialect Tag
            (r'\(\*!m2iso\+aglet\*\)', Comment.Special),
            # GNU Extensions Dialect Tag
            (r'\(\*!m2pim\+gm2\*\)', Comment.Special),
            # p1 Extensions Dialect Tag
            (r'\(\*!m2iso\+p1\*\)', Comment.Special),
            # XDS Extensions Dialect Tag
            (r'\(\*!m2iso\+xds\*\)', Comment.Special),
        ],
        'identifiers': [
            (r'([a-zA-Z_$][\w$]*)', Name),
        ],
        'prefixed_number_literals': [
            #
            # Base-2, whole number
            (r'0b[01]+(\'[01]+)*', Number.Bin),
            #
            # Base-16, whole number
            (r'0[ux][0-9A-F]+(\'[0-9A-F]+)*', Number.Hex),
        ],
        'plain_number_literals': [
            #
            # Base-10, real number with exponent
            (r'[0-9]+(\'[0-9]+)*'  # integral part
             r'\.[0-9]+(\'[0-9]+)*'  # fractional part
             r'[eE][+-]?[0-9]+(\'[0-9]+)*',  # exponent
             Number.Float),
            #
            # Base-10, real number without exponent
            (r'[0-9]+(\'[0-9]+)*'  # integral part
             r'\.[0-9]+(\'[0-9]+)*',  # fractional part
             Number.Float),
            #
            # Base-10, whole number
            (r'[0-9]+(\'[0-9]+)*', Number.Integer),
        ],
        'suffixed_number_literals': [
            #
            # Base-8, whole number
            (r'[0-7]+B', Number.Oct),
            #
            # Base-8, character code
            (r'[0-7]+C', Number.Oct),
            #
            # Base-16, number
            (r'[0-9A-F]+H', Number.Hex),
        ],
        'string_literals': [
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
        ],
        'digraph_operators': [
            # Dot Product Operator
            (r'\*\.', Operator),
            # Array Concatenation Operator
            (r'\+>', Operator),  # M2R10 + ObjM2
            # Inequality Operator
            (r'<>', Operator),  # ISO + PIM
            # Less-Or-Equal, Subset
            (r'<=', Operator),
            # Greater-Or-Equal, Superset
            (r'>=', Operator),
            # Identity Operator
            (r'==', Operator),  # M2R10 + ObjM2
            # Type Conversion Operator
            (r'::', Operator),  # M2R10 + ObjM2
            # Assignment Symbol
            (r':=', Operator),
            # Postfix Increment Mutator
            (r'\+\+', Operator),  # M2R10 + ObjM2
            # Postfix Decrement Mutator
            (r'--', Operator),  # M2R10 + ObjM2
        ],
        'unigraph_operators': [
            # Arithmetic Operators
            (r'[+-]', Operator),
            (r'[*/]', Operator),
            # ISO 80000-2 compliant Set Difference Operator
            (r'\\', Operator),  # M2R10 + ObjM2
            # Relational Operators
            (r'[=#<>]', Operator),
            # Dereferencing Operator
            (r'\^', Operator),
            # Dereferencing Operator Synonym
            (r'@', Operator),  # ISO
            # Logical AND Operator Synonym
            (r'&', Operator),  # PIM + ISO
            # Logical NOT Operator Synonym
            (r'~', Operator),  # PIM + ISO
            # Smalltalk Message Prefix
            (r'`', Operator),  # ObjM2
        ],
        'digraph_punctuation': [
            # Range Constructor
            (r'\.\.', Punctuation),
            # Opening Chevron Bracket
            (r'<<', Punctuation),  # M2R10 + ISO
            # Closing Chevron Bracket
            (r'>>', Punctuation),  # M2R10 + ISO
            # Blueprint Punctuation
            (r'->', Punctuation),  # M2R10 + ISO
            # Distinguish |# and # in M2 R10
            (r'\|#', Punctuation),
            # Distinguish ## and # in M2 R10
            (r'##', Punctuation),
            # Distinguish |* and * in M2 R10
            (r'\|\*', Punctuation),
        ],
        'unigraph_punctuation': [
            # Common Punctuation
            (r'[()\[\]{},.:;|]', Punctuation),
            # Case Label Separator Synonym
            (r'!', Punctuation),  # ISO
            # Blueprint Punctuation
            (r'\?', Punctuation),  # M2R10 + ObjM2
        ],
        'comments': [
            # Single Line Comment
            (r'^//.*?\n', Comment.Single),  # M2R10 + ObjM2
            # Block Comment
            (r'\(\*([^$].*?)\*\)', Comment.Multiline),
            # Template Block Comment
            (r'/\*(.*?)\*/', Comment.Multiline),  # M2R10 + ObjM2
        ],
        'pragmas': [
            # ISO Style Pragmas
            (r'<\*.*?\*>', Comment.Preproc),  # ISO, M2R10 + ObjM2
            # Pascal Style Pragmas
            (r'\(\*\$.*?\*\)', Comment.Preproc),  # PIM
        ],
        'root': [
            include('whitespace'),
            include('dialecttags'),
            include('pragmas'),
            include('comments'),
            include('identifiers'),
            include('suffixed_number_literals'),  # PIM + ISO
            include('prefixed_number_literals'),  # M2R10 + ObjM2
            include('plain_number_literals'),
            include('string_literals'),
            include('digraph_punctuation'),
            include('digraph_operators'),
            include('unigraph_punctuation'),
            include('unigraph_operators'),
        ]
    }

#  C o m m o n   D a t a s e t s

    # Common Reserved Words Dataset
    common_reserved_words = (
        # 37 common reserved words
        'AND', 'ARRAY', 'BEGIN', 'BY', 'CASE', 'CONST', 'DEFINITION', 'DIV',
        'DO', 'ELSE', 'ELSIF', 'END', 'EXIT', 'FOR', 'FROM', 'IF',
        'IMPLEMENTATION', 'IMPORT', 'IN', 'LOOP', 'MOD', 'MODULE', 'NOT',
        'OF', 'OR', 'POINTER', 'PROCEDURE', 'RECORD', 'REPEAT', 'RETURN',
        'SET', 'THEN', 'TO', 'TYPE', 'UNTIL', 'VAR', 'WHILE',
    )

    # Common Builtins Dataset
    common_builtins = (
        # 16 common builtins
        'ABS', 'BOOLEAN', 'CARDINAL', 'CHAR', 'CHR', 'FALSE', 'INTEGER',
        'LONGINT', 'LONGREAL', 'MAX', 'MIN', 'NIL', 'ODD', 'ORD', 'REAL',
        'TRUE',
    )

    # Common Pseudo-Module Builtins Dataset
    common_pseudo_builtins = (
        # 4 common pseudo builtins
        'ADDRESS', 'BYTE', 'WORD', 'ADR'
    )

#  P I M   M o d u l a - 2   D a t a s e t s

    # Lexemes to Mark as Error Tokens for PIM Modula-2
    pim_lexemes_to_reject = (
        '!', '`', '@', '$', '%', '?', '\\', '==', '++', '--', '::', '*.',
        '+>', '->', '<<', '>>', '|#', '##',
    )

    # PIM Modula-2 Additional Reserved Words Dataset
    pim_additional_reserved_words = (
        # 3 additional reserved words
        'EXPORT', 'QUALIFIED', 'WITH',
    )

    # PIM Modula-2 Additional Builtins Dataset
    pim_additional_builtins = (
        # 16 additional builtins
        'BITSET', 'CAP', 'DEC', 'DISPOSE', 'EXCL', 'FLOAT', 'HALT', 'HIGH',
        'INC', 'INCL', 'NEW', 'NIL', 'PROC', 'SIZE', 'TRUNC', 'VAL',
    )

    # PIM Modula-2 Additional Pseudo-Module Builtins Dataset
    pim_additional_pseudo_builtins = (
        # 5 additional pseudo builtins
        'SYSTEM', 'PROCESS', 'TSIZE', 'NEWPROCESS', 'TRANSFER',
    )

#  I S O   M o d u l a - 2   D a t a s e t s

    # Lexemes to Mark as Error Tokens for ISO Modula-2
    iso_lexemes_to_reject = (
        '`', '$', '%', '?', '\\', '==', '++', '--', '::', '*.', '+>', '->',
        '<<', '>>', '|#', '##',
    )

    # ISO Modula-2 Additional Reserved Words Dataset
    iso_additional_reserved_words = (
        # 9 additional reserved words (ISO 10514-1)
        'EXCEPT', 'EXPORT', 'FINALLY', 'FORWARD', 'PACKEDSET', 'QUALIFIED',
        'REM', 'RETRY', 'WITH',
        # 10 additional reserved words (ISO 10514-2 & ISO 10514-3)
        'ABSTRACT', 'AS', 'CLASS', 'GUARD', 'INHERIT', 'OVERRIDE', 'READONLY',
        'REVEAL', 'TRACED', 'UNSAFEGUARDED',
    )

    # ISO Modula-2 Additional Builtins Dataset
    iso_additional_builtins = (
        # 26 additional builtins (ISO 10514-1)
        'BITSET', 'CAP', 'CMPLX', 'COMPLEX', 'DEC', 'DISPOSE', 'EXCL', 'FLOAT',
        'HALT', 'HIGH', 'IM', 'INC', 'INCL', 'INT', 'INTERRUPTIBLE',  'LENGTH',
        'LFLOAT', 'LONGCOMPLEX', 'NEW', 'PROC', 'PROTECTION', 'RE', 'SIZE',
        'TRUNC', 'UNINTERRUBTIBLE', 'VAL',
        # 5 additional builtins (ISO 10514-2 & ISO 10514-3)
        'CREATE', 'DESTROY', 'EMPTY', 'ISMEMBER', 'SELF',
    )

    # ISO Modula-2 Additional Pseudo-Module Builtins Dataset
    iso_additional_pseudo_builtins = (
        # 14 additional builtins (SYSTEM)
        'SYSTEM', 'BITSPERLOC', 'LOCSPERBYTE', 'LOCSPERWORD', 'LOC',
        'ADDADR', 'SUBADR', 'DIFADR', 'MAKEADR', 'ADR',
        'ROTATE', 'SHIFT', 'CAST', 'TSIZE',
        # 13 additional builtins (COROUTINES)
        'COROUTINES', 'ATTACH', 'COROUTINE', 'CURRENT', 'DETACH', 'HANDLER',
        'INTERRUPTSOURCE', 'IOTRANSFER', 'IsATTACHED', 'LISTEN',
        'NEWCOROUTINE', 'PROT', 'TRANSFER',
        # 9 additional builtins (EXCEPTIONS)
        'EXCEPTIONS', 'AllocateSource', 'CurrentNumber', 'ExceptionNumber',
        'ExceptionSource', 'GetMessage', 'IsCurrentSource',
        'IsExceptionalExecution', 'RAISE',
        # 3 additional builtins (TERMINATION)
        'TERMINATION', 'IsTerminating', 'HasHalted',
        # 4 additional builtins (M2EXCEPTION)
        'M2EXCEPTION', 'M2Exceptions', 'M2Exception', 'IsM2Exception',
        'indexException', 'rangeException', 'caseSelectException',
        'invalidLocation', 'functionException', 'wholeValueException',
        'wholeDivException', 'realValueException', 'realDivException',
        'complexValueException', 'complexDivException', 'protException',
        'sysException', 'coException', 'exException',
    )

#  M o d u l a - 2   R 1 0   D a t a s e t s

    # Lexemes to Mark as Error Tokens for Modula-2 R10
    m2r10_lexemes_to_reject = (
        '!', '`', '@', '$', '%', '&', '<>',
    )

    # Modula-2 R10 reserved words in addition to the common set
    m2r10_additional_reserved_words = (
        # 12 additional reserved words
        'ALIAS', 'ARGLIST', 'BLUEPRINT', 'COPY', 'GENLIB', 'INDETERMINATE',
        'NEW', 'NONE', 'OPAQUE', 'REFERENTIAL', 'RELEASE', 'RETAIN',
        # 2 additional reserved words with symbolic assembly option
        'ASM', 'REG',
    )

    # Modula-2 R10 builtins in addition to the common set
    m2r10_additional_builtins = (
        # 26 additional builtins
        'CARDINAL', 'COUNT', 'EMPTY', 'EXISTS', 'INSERT', 'LENGTH', 'LONGCARD',
        'OCTET', 'PTR', 'PRED', 'READ', 'READNEW', 'REMOVE', 'RETRIEVE', 'SORT',
        'STORE', 'SUBSET', 'SUCC', 'TLIMIT', 'TMAX', 'TMIN', 'TRUE', 'TSIZE',
        'UNICHAR', 'WRITE', 'WRITEF',
    )

    # Modula-2 R10 Additional Pseudo-Module Builtins Dataset
    m2r10_additional_pseudo_builtins = (
        # 13 additional builtins (TPROPERTIES)
        'TPROPERTIES', 'PROPERTY', 'LITERAL', 'TPROPERTY', 'TLITERAL',
        'TBUILTIN', 'TDYN', 'TREFC', 'TNIL', 'TBASE', 'TPRECISION',
        'TMAXEXP', 'TMINEXP',
        # 4 additional builtins (CONVERSION)
        'CONVERSION', 'TSXFSIZE', 'SXF', 'VAL',
        # 35 additional builtins (UNSAFE)
        'UNSAFE', 'CAST', 'INTRINSIC', 'AVAIL', 'ADD', 'SUB', 'ADDC', 'SUBC',
        'FETCHADD', 'FETCHSUB', 'SHL', 'SHR', 'ASHR', 'ROTL', 'ROTR', 'ROTLC',
        'ROTRC', 'BWNOT', 'BWAND', 'BWOR', 'BWXOR', 'BWNAND', 'BWNOR',
        'SETBIT', 'TESTBIT', 'LSBIT', 'MSBIT', 'CSBITS', 'BAIL', 'HALT',
        'TODO', 'FFI', 'ADDR', 'VARGLIST', 'VARGC',
        # 11 additional builtins (ATOMIC)
        'ATOMIC', 'INTRINSIC', 'AVAIL', 'SWAP', 'CAS', 'INC', 'DEC', 'BWAND',
        'BWNAND', 'BWOR', 'BWXOR',
        # 7 additional builtins (COMPILER)
        'COMPILER', 'DEBUG', 'MODNAME', 'PROCNAME', 'LINENUM', 'DEFAULT',
        'HASH',
        # 5 additional builtins (ASSEMBLER)
        'ASSEMBLER', 'REGISTER', 'SETREG', 'GETREG', 'CODE',
    )

#  O b j e c t i v e   M o d u l a - 2   D a t a s e t s

    # Lexemes to Mark as Error Tokens for Objective Modula-2
    objm2_lexemes_to_reject = (
        '!', '$', '%', '&', '<>',
    )

    # Objective Modula-2 Extensions
    # reserved words in addition to Modula-2 R10
    objm2_additional_reserved_words = (
        # 16 additional reserved words
        'BYCOPY', 'BYREF', 'CLASS', 'CONTINUE', 'CRITICAL', 'INOUT', 'METHOD',
        'ON', 'OPTIONAL', 'OUT', 'PRIVATE', 'PROTECTED', 'PROTOCOL', 'PUBLIC',
        'SUPER', 'TRY',
    )

    # Objective Modula-2 Extensions
    # builtins in addition to Modula-2 R10
    objm2_additional_builtins = (
        # 3 additional builtins
        'OBJECT', 'NO', 'YES',
    )

    # Objective Modula-2 Extensions
    # pseudo-module builtins in addition to Modula-2 R10
    objm2_additional_pseudo_builtins = (
        # None
    )

#  A g l e t   M o d u l a - 2   D a t a s e t s

    # Aglet Extensions
    # reserved words in addition to ISO Modula-2
    aglet_additional_reserved_words = (
        # None
    )

    # Aglet Extensions
    # builtins in addition to ISO Modula-2
    aglet_additional_builtins = (
        # 9 additional builtins
        'BITSET8', 'BITSET16', 'BITSET32', 'CARDINAL8', 'CARDINAL16',
        'CARDINAL32', 'INTEGER8', 'INTEGER16', 'INTEGER32',
    )

    # Aglet Modula-2 Extensions
    # pseudo-module builtins in addition to ISO Modula-2
    aglet_additional_pseudo_builtins = (
        # None
    )

#  G N U   M o d u l a - 2   D a t a s e t s

    # GNU Extensions
    # reserved words in addition to PIM Modula-2
    gm2_additional_reserved_words = (
        # 10 additional reserved words
        'ASM', '__ATTRIBUTE__', '__BUILTIN__', '__COLUMN__', '__DATE__',
        '__FILE__', '__FUNCTION__', '__LINE__', '__MODULE__', 'VOLATILE',
    )

    # GNU Extensions
    # builtins in addition to PIM Modula-2
    gm2_additional_builtins = (
        # 21 additional builtins
        'BITSET8', 'BITSET16', 'BITSET32', 'CARDINAL8', 'CARDINAL16',
        'CARDINAL32', 'CARDINAL64', 'COMPLEX32', 'COMPLEX64', 'COMPLEX96',
        'COMPLEX128', 'INTEGER8', 'INTEGER16', 'INTEGER32', 'INTEGER64',
        'REAL8', 'REAL16', 'REAL32', 'REAL96', 'REAL128', 'THROW',
    )

    # GNU Extensions
    # pseudo-module builtins in addition to PIM Modula-2
    gm2_additional_pseudo_builtins = (
        # None
    )

#  p 1   M o d u l a - 2   D a t a s e t s

    # p1 Extensions
    # reserved words in addition to ISO Modula-2
    p1_additional_reserved_words = (
        # None
    )

    # p1 Extensions
    # builtins in addition to ISO Modula-2
    p1_additional_builtins = (
        # None
    )

    # p1 Modula-2 Extensions
    # pseudo-module builtins in addition to ISO Modula-2
    p1_additional_pseudo_builtins = (
        # 1 additional builtin
        'BCD',
    )

#  X D S   M o d u l a - 2   D a t a s e t s

    # XDS Extensions
    # reserved words in addition to ISO Modula-2
    xds_additional_reserved_words = (
        # 1 additional reserved word
        'SEQ',
    )

    # XDS Extensions
    # builtins in addition to ISO Modula-2
    xds_additional_builtins = (
        # 9 additional builtins
        'ASH', 'ASSERT', 'DIFFADR_TYPE', 'ENTIER', 'INDEX', 'LEN',
        'LONGCARD', 'SHORTCARD', 'SHORTINT',
    )

    # XDS Modula-2 Extensions
    # pseudo-module builtins in addition to ISO Modula-2
    xds_additional_pseudo_builtins = (
        # 22 additional builtins (SYSTEM)
        'PROCESS', 'NEWPROCESS', 'BOOL8', 'BOOL16', 'BOOL32', 'CARD8',
        'CARD16', 'CARD32', 'INT8', 'INT16', 'INT32', 'REF', 'MOVE',
        'FILL', 'GET', 'PUT', 'CC', 'int', 'unsigned', 'size_t', 'void'
        # 3 additional builtins (COMPILER)
        'COMPILER', 'OPTION', 'EQUATION'
    )

#  P I M   S t a n d a r d   L i b r a r y   D a t a s e t s

    # PIM Modula-2 Standard Library Modules Dataset
    pim_stdlib_module_identifiers = (
        'Terminal', 'FileSystem', 'InOut', 'RealInOut', 'MathLib0', 'Storage',
    )

    # PIM Modula-2 Standard Library Types Dataset
    pim_stdlib_type_identifiers = (
        'Flag', 'FlagSet', 'Response', 'Command', 'Lock', 'Permission',
        'MediumType', 'File', 'FileProc', 'DirectoryProc', 'FileCommand',
        'DirectoryCommand',
    )

    # PIM Modula-2 Standard Library Procedures Dataset
    pim_stdlib_proc_identifiers = (
        'Read', 'BusyRead', 'ReadAgain', 'Write', 'WriteString', 'WriteLn',
        'Create', 'Lookup', 'Close', 'Delete', 'Rename', 'SetRead', 'SetWrite',
        'SetModify', 'SetOpen', 'Doio', 'SetPos', 'GetPos', 'Length', 'Reset',
        'Again', 'ReadWord', 'WriteWord', 'ReadChar', 'WriteChar',
        'CreateMedium', 'DeleteMedium', 'AssignName', 'DeassignName',
        'ReadMedium', 'LookupMedium', 'OpenInput', 'OpenOutput', 'CloseInput',
        'CloseOutput', 'ReadString', 'ReadInt', 'ReadCard', 'ReadWrd',
        'WriteInt', 'WriteCard', 'WriteOct', 'WriteHex', 'WriteWrd',
        'ReadReal', 'WriteReal', 'WriteFixPt', 'WriteRealOct', 'sqrt', 'exp',
        'ln', 'sin', 'cos', 'arctan', 'entier', 'ALLOCATE', 'DEALLOCATE',
    )

    # PIM Modula-2 Standard Library Variables Dataset
    pim_stdlib_var_identifiers = (
        'Done', 'termCH', 'in', 'out'
    )

    # PIM Modula-2 Standard Library Constants Dataset
    pim_stdlib_const_identifiers = (
        'EOL',
    )

#  I S O   S t a n d a r d   L i b r a r y   D a t a s e t s

    # ISO Modula-2 Standard Library Modules Dataset
    iso_stdlib_module_identifiers = (
        # TO DO
    )

    # ISO Modula-2 Standard Library Types Dataset
    iso_stdlib_type_identifiers = (
        # TO DO
    )

    # ISO Modula-2 Standard Library Procedures Dataset
    iso_stdlib_proc_identifiers = (
        # TO DO
    )

    # ISO Modula-2 Standard Library Variables Dataset
    iso_stdlib_var_identifiers = (
        # TO DO
    )

    # ISO Modula-2 Standard Library Constants Dataset
    iso_stdlib_const_identifiers = (
        # TO DO
    )

#  M 2   R 1 0   S t a n d a r d   L i b r a r y   D a t a s e t s

    # Modula-2 R10 Standard Library ADTs Dataset
    m2r10_stdlib_adt_identifiers = (
        'BCD', 'LONGBCD', 'BITSET', 'SHORTBITSET', 'LONGBITSET',
        'LONGLONGBITSET', 'COMPLEX', 'LONGCOMPLEX', 'SHORTCARD', 'LONGLONGCARD',
        'SHORTINT', 'LONGLONGINT', 'POSINT', 'SHORTPOSINT', 'LONGPOSINT',
        'LONGLONGPOSINT', 'BITSET8', 'BITSET16', 'BITSET32', 'BITSET64',
        'BITSET128', 'BS8', 'BS16', 'BS32', 'BS64', 'BS128', 'CARDINAL8',
        'CARDINAL16', 'CARDINAL32', 'CARDINAL64', 'CARDINAL128', 'CARD8',
        'CARD16', 'CARD32', 'CARD64', 'CARD128', 'INTEGER8', 'INTEGER16',
        'INTEGER32', 'INTEGER64', 'INTEGER128', 'INT8', 'INT16', 'INT32',
        'INT64', 'INT128', 'STRING', 'UNISTRING',
    )

    # Modula-2 R10 Standard Library Blueprints Dataset
    m2r10_stdlib_blueprint_identifiers = (
        'ProtoRoot', 'ProtoComputational', 'ProtoNumeric', 'ProtoScalar',
        'ProtoNonScalar', 'ProtoCardinal', 'ProtoInteger', 'ProtoReal',
        'ProtoComplex', 'ProtoVector', 'ProtoTuple', 'ProtoCompArray',
        'ProtoCollection', 'ProtoStaticArray', 'ProtoStaticSet',
        'ProtoStaticString', 'ProtoArray', 'ProtoString', 'ProtoSet',
        'ProtoMultiSet', 'ProtoDictionary', 'ProtoMultiDict', 'ProtoExtension',
        'ProtoIO', 'ProtoCardMath', 'ProtoIntMath', 'ProtoRealMath',
    )

    # Modula-2 R10 Standard Library Modules Dataset
    m2r10_stdlib_module_identifiers = (
        'ASCII', 'BooleanIO', 'CharIO', 'UnicharIO', 'OctetIO',
        'CardinalIO', 'LongCardIO', 'IntegerIO', 'LongIntIO', 'RealIO',
        'LongRealIO', 'BCDIO', 'LongBCDIO', 'CardMath', 'LongCardMath',
        'IntMath', 'LongIntMath', 'RealMath', 'LongRealMath', 'BCDMath',
        'LongBCDMath', 'FileIO', 'FileSystem', 'Storage', 'IOSupport',
    )

    # Modula-2 R10 Standard Library Types Dataset
    m2r10_stdlib_type_identifiers = (
        'File', 'Status',
        # TO BE COMPLETED
    )

    # Modula-2 R10 Standard Library Procedures Dataset
    m2r10_stdlib_proc_identifiers = (
        'ALLOCATE', 'DEALLOCATE', 'SIZE',
        # TO BE COMPLETED
    )

    # Modula-2 R10 Standard Library Variables Dataset
    m2r10_stdlib_var_identifiers = (
        'stdIn', 'stdOut', 'stdErr',
    )

    # Modula-2 R10 Standard Library Constants Dataset
    m2r10_stdlib_const_identifiers = (
        'pi', 'tau',
    )

#  D i a l e c t s

    # Dialect modes
    dialects = (
        'unknown',
        'm2pim', 'm2iso', 'm2r10', 'objm2',
        'm2iso+aglet', 'm2pim+gm2', 'm2iso+p1', 'm2iso+xds',
    )

#   D a t a b a s e s

    # Lexemes to Mark as Errors Database
    lexemes_to_reject_db = {
        # Lexemes to reject for unknown dialect
        'unknown': (
            # LEAVE THIS EMPTY
        ),
        # Lexemes to reject for PIM Modula-2
        'm2pim': (
            pim_lexemes_to_reject,
        ),
        # Lexemes to reject for ISO Modula-2
        'm2iso': (
            iso_lexemes_to_reject,
        ),
        # Lexemes to reject for Modula-2 R10
        'm2r10': (
            m2r10_lexemes_to_reject,
        ),
        # Lexemes to reject for Objective Modula-2
        'objm2': (
            objm2_lexemes_to_reject,
        ),
        # Lexemes to reject for Aglet Modula-2
        'm2iso+aglet': (
            iso_lexemes_to_reject,
        ),
        # Lexemes to reject for GNU Modula-2
        'm2pim+gm2': (
            pim_lexemes_to_reject,
        ),
        # Lexemes to reject for p1 Modula-2
        'm2iso+p1': (
            iso_lexemes_to_reject,
        ),
        # Lexemes to reject for XDS Modula-2
        'm2iso+xds': (
            iso_lexemes_to_reject,
        ),
    }

    # Reserved Words Database
    reserved_words_db = {
        # Reserved words for unknown dialect
        'unknown': (
            common_reserved_words,
            pim_additional_reserved_words,
            iso_additional_reserved_words,
            m2r10_additional_reserved_words,
        ),

        # Reserved words for PIM Modula-2
        'm2pim': (
            common_reserved_words,
            pim_additional_reserved_words,
        ),

        # Reserved words for Modula-2 R10
        'm2iso': (
            common_reserved_words,
            iso_additional_reserved_words,
        ),

        # Reserved words for ISO Modula-2
        'm2r10': (
            common_reserved_words,
            m2r10_additional_reserved_words,
        ),

        # Reserved words for Objective Modula-2
        'objm2': (
            common_reserved_words,
            m2r10_additional_reserved_words,
            objm2_additional_reserved_words,
        ),

        # Reserved words for Aglet Modula-2 Extensions
        'm2iso+aglet': (
            common_reserved_words,
            iso_additional_reserved_words,
            aglet_additional_reserved_words,
        ),

        # Reserved words for GNU Modula-2 Extensions
        'm2pim+gm2': (
            common_reserved_words,
            pim_additional_reserved_words,
            gm2_additional_reserved_words,
        ),

        # Reserved words for p1 Modula-2 Extensions
        'm2iso+p1': (
            common_reserved_words,
            iso_additional_reserved_words,
            p1_additional_reserved_words,
        ),

        # Reserved words for XDS Modula-2 Extensions
        'm2iso+xds': (
            common_reserved_words,
            iso_additional_reserved_words,
            xds_additional_reserved_words,
        ),
    }

    # Builtins Database
    builtins_db = {
        # Builtins for unknown dialect
        'unknown': (
            common_builtins,
            pim_additional_builtins,
            iso_additional_builtins,
            m2r10_additional_builtins,
        ),

        # Builtins for PIM Modula-2
        'm2pim': (
            common_builtins,
            pim_additional_builtins,
        ),

        # Builtins for ISO Modula-2
        'm2iso': (
            common_builtins,
            iso_additional_builtins,
        ),

        # Builtins for ISO Modula-2
        'm2r10': (
            common_builtins,
            m2r10_additional_builtins,
        ),

        # Builtins for Objective Modula-2
        'objm2': (
            common_builtins,
            m2r10_additional_builtins,
            objm2_additional_builtins,
        ),

        # Builtins for Aglet Modula-2 Extensions
        'm2iso+aglet': (
            common_builtins,
            iso_additional_builtins,
            aglet_additional_builtins,
        ),

        # Builtins for GNU Modula-2 Extensions
        'm2pim+gm2': (
            common_builtins,
            pim_additional_builtins,
            gm2_additional_builtins,
        ),

        # Builtins for p1 Modula-2 Extensions
        'm2iso+p1': (
            common_builtins,
            iso_additional_builtins,
            p1_additional_builtins,
        ),

        # Builtins for XDS Modula-2 Extensions
        'm2iso+xds': (
            common_builtins,
            iso_additional_builtins,
            xds_additional_builtins,
        ),
    }

    # Pseudo-Module Builtins Database
    pseudo_builtins_db = {
        # Builtins for unknown dialect
        'unknown': (
            common_pseudo_builtins,
            pim_additional_pseudo_builtins,
            iso_additional_pseudo_builtins,
            m2r10_additional_pseudo_builtins,
        ),

        # Builtins for PIM Modula-2
        'm2pim': (
            common_pseudo_builtins,
            pim_additional_pseudo_builtins,
        ),

        # Builtins for ISO Modula-2
        'm2iso': (
            common_pseudo_builtins,
            iso_additional_pseudo_builtins,
        ),

        # Builtins for ISO Modula-2
        'm2r10': (
            common_pseudo_builtins,
            m2r10_additional_pseudo_builtins,
        ),

        # Builtins for Objective Modula-2
        'objm2': (
            common_pseudo_builtins,
            m2r10_additional_pseudo_builtins,
            objm2_additional_pseudo_builtins,
        ),

        # Builtins for Aglet Modula-2 Extensions
        'm2iso+aglet': (
            common_pseudo_builtins,
            iso_additional_pseudo_builtins,
            aglet_additional_pseudo_builtins,
        ),

        # Builtins for GNU Modula-2 Extensions
        'm2pim+gm2': (
            common_pseudo_builtins,
            pim_additional_pseudo_builtins,
            gm2_additional_pseudo_builtins,
        ),

        # Builtins for p1 Modula-2 Extensions
        'm2iso+p1': (
            common_pseudo_builtins,
            iso_additional_pseudo_builtins,
            p1_additional_pseudo_builtins,
        ),

        # Builtins for XDS Modula-2 Extensions
        'm2iso+xds': (
            common_pseudo_builtins,
            iso_additional_pseudo_builtins,
            xds_additional_pseudo_builtins,
        ),
    }

    # Standard Library ADTs Database
    stdlib_adts_db = {
        # Empty entry for unknown dialect
        'unknown': (
            # LEAVE THIS EMPTY
        ),
        # Standard Library ADTs for PIM Modula-2
        'm2pim': (
            # No first class library types
        ),

        # Standard Library ADTs for ISO Modula-2
        'm2iso': (
            # No first class library types
        ),

        # Standard Library ADTs for Modula-2 R10
        'm2r10': (
            m2r10_stdlib_adt_identifiers,
        ),

        # Standard Library ADTs for Objective Modula-2
        'objm2': (
            m2r10_stdlib_adt_identifiers,
        ),

        # Standard Library ADTs for Aglet Modula-2
        'm2iso+aglet': (
            # No first class library types
        ),

        # Standard Library ADTs for GNU Modula-2
        'm2pim+gm2': (
            # No first class library types
        ),

        # Standard Library ADTs for p1 Modula-2
        'm2iso+p1': (
            # No first class library types
        ),

        # Standard Library ADTs for XDS Modula-2
        'm2iso+xds': (
            # No first class library types
        ),
    }

    # Standard Library Modules Database
    stdlib_modules_db = {
        # Empty entry for unknown dialect
        'unknown': (
            # LEAVE THIS EMPTY
        ),
        # Standard Library Modules for PIM Modula-2
        'm2pim': (
            pim_stdlib_module_identifiers,
        ),

        # Standard Library Modules for ISO Modula-2
        'm2iso': (
            iso_stdlib_module_identifiers,
        ),

        # Standard Library Modules for Modula-2 R10
        'm2r10': (
            m2r10_stdlib_blueprint_identifiers,
            m2r10_stdlib_module_identifiers,
            m2r10_stdlib_adt_identifiers,
        ),

        # Standard Library Modules for Objective Modula-2
        'objm2': (
            m2r10_stdlib_blueprint_identifiers,
            m2r10_stdlib_module_identifiers,
        ),

        # Standard Library Modules for Aglet Modula-2
        'm2iso+aglet': (
            iso_stdlib_module_identifiers,
        ),

        # Standard Library Modules for GNU Modula-2
        'm2pim+gm2': (
            pim_stdlib_module_identifiers,
        ),

        # Standard Library Modules for p1 Modula-2
        'm2iso+p1': (
            iso_stdlib_module_identifiers,
        ),

        # Standard Library Modules for XDS Modula-2
        'm2iso+xds': (
            iso_stdlib_module_identifiers,
        ),
    }

    # Standard Library Types Database
    stdlib_types_db = {
        # Empty entry for unknown dialect
        'unknown': (
            # LEAVE THIS EMPTY
        ),
        # Standard Library Types for PIM Modula-2
        'm2pim': (
            pim_stdlib_type_identifiers,
        ),

        # Standard Library Types for ISO Modula-2
        'm2iso': (
            iso_stdlib_type_identifiers,
        ),

        # Standard Library Types for Modula-2 R10
        'm2r10': (
            m2r10_stdlib_type_identifiers,
        ),

        # Standard Library Types for Objective Modula-2
        'objm2': (
            m2r10_stdlib_type_identifiers,
        ),

        # Standard Library Types for Aglet Modula-2
        'm2iso+aglet': (
            iso_stdlib_type_identifiers,
        ),

        # Standard Library Types for GNU Modula-2
        'm2pim+gm2': (
            pim_stdlib_type_identifiers,
        ),

        # Standard Library Types for p1 Modula-2
        'm2iso+p1': (
            iso_stdlib_type_identifiers,
        ),

        # Standard Library Types for XDS Modula-2
        'm2iso+xds': (
            iso_stdlib_type_identifiers,
        ),
    }

    # Standard Library Procedures Database
    stdlib_procedures_db = {
        # Empty entry for unknown dialect
        'unknown': (
            # LEAVE THIS EMPTY
        ),
        # Standard Library Procedures for PIM Modula-2
        'm2pim': (
            pim_stdlib_proc_identifiers,
        ),

        # Standard Library Procedures for ISO Modula-2
        'm2iso': (
            iso_stdlib_proc_identifiers,
        ),

        # Standard Library Procedures for Modula-2 R10
        'm2r10': (
            m2r10_stdlib_proc_identifiers,
        ),

        # Standard Library Procedures for Objective Modula-2
        'objm2': (
            m2r10_stdlib_proc_identifiers,
        ),

        # Standard Library Procedures for Aglet Modula-2
        'm2iso+aglet': (
            iso_stdlib_proc_identifiers,
        ),

        # Standard Library Procedures for GNU Modula-2
        'm2pim+gm2': (
            pim_stdlib_proc_identifiers,
        ),

        # Standard Library Procedures for p1 Modula-2
        'm2iso+p1': (
            iso_stdlib_proc_identifiers,
        ),

        # Standard Library Procedures for XDS Modula-2
        'm2iso+xds': (
            iso_stdlib_proc_identifiers,
        ),
    }

    # Standard Library Variables Database
    stdlib_variables_db = {
        # Empty entry for unknown dialect
        'unknown': (
            # LEAVE THIS EMPTY
        ),
        # Standard Library Variables for PIM Modula-2
        'm2pim': (
            pim_stdlib_var_identifiers,
        ),

        # Standard Library Variables for ISO Modula-2
        'm2iso': (
            iso_stdlib_var_identifiers,
        ),

        # Standard Library Variables for Modula-2 R10
        'm2r10': (
            m2r10_stdlib_var_identifiers,
        ),

        # Standard Library Variables for Objective Modula-2
        'objm2': (
            m2r10_stdlib_var_identifiers,
        ),

        # Standard Library Variables for Aglet Modula-2
        'm2iso+aglet': (
            iso_stdlib_var_identifiers,
        ),

        # Standard Library Variables for GNU Modula-2
        'm2pim+gm2': (
            pim_stdlib_var_identifiers,
        ),

        # Standard Library Variables for p1 Modula-2
        'm2iso+p1': (
            iso_stdlib_var_identifiers,
        ),

        # Standard Library Variables for XDS Modula-2
        'm2iso+xds': (
            iso_stdlib_var_identifiers,
        ),
    }

    # Standard Library Constants Database
    stdlib_constants_db = {
        # Empty entry for unknown dialect
        'unknown': (
            # LEAVE THIS EMPTY
        ),
        # Standard Library Constants for PIM Modula-2
        'm2pim': (
            pim_stdlib_const_identifiers,
        ),

        # Standard Library Constants for ISO Modula-2
        'm2iso': (
            iso_stdlib_const_identifiers,
        ),

        # Standard Library Constants for Modula-2 R10
        'm2r10': (
            m2r10_stdlib_const_identifiers,
        ),

        # Standard Library Constants for Objective Modula-2
        'objm2': (
            m2r10_stdlib_const_identifiers,
        ),

        # Standard Library Constants for Aglet Modula-2
        'm2iso+aglet': (
            iso_stdlib_const_identifiers,
        ),

        # Standard Library Constants for GNU Modula-2
        'm2pim+gm2': (
            pim_stdlib_const_identifiers,
        ),

        # Standard Library Constants for p1 Modula-2
        'm2iso+p1': (
            iso_stdlib_const_identifiers,
        ),

        # Standard Library Constants for XDS Modula-2
        'm2iso+xds': (
            iso_stdlib_const_identifiers,
        ),
    }

#   M e t h o d s

    # initialise a lexer instance
    def __init__(self, **options):
        #
        # check dialect options
        #
        dialects = get_list_opt(options, 'dialect', [])
        #
        for dialect_option in dialects:
            if dialect_option in self.dialects[1:-1]:
                # valid dialect option found
                self.set_dialect(dialect_option)
                break
        #
        # Fallback Mode (DEFAULT)
        else:
            # no valid dialect option
            self.set_dialect('unknown')
        #
        self.dialect_set_by_tag = False
        #
        # check style options
        #
        styles = get_list_opt(options, 'style', [])
        #
        # use lowercase mode for Algol style
        if 'algol' in styles or 'algol_nu' in styles:
            self.algol_publication_mode = True
        else:
            self.algol_publication_mode = False
        #
        # Check option flags
        #
        self.treat_stdlib_adts_as_builtins = get_bool_opt(
            options, 'treat_stdlib_adts_as_builtins', True)
        #
        # call superclass initialiser
        RegexLexer.__init__(self, **options)

    # Set lexer to a specified dialect
    def set_dialect(self, dialect_id):
        #
        # if __debug__:
        #    print 'entered set_dialect with arg: ', dialect_id
        #
        # check dialect name against known dialects
        if dialect_id not in self.dialects:
            dialect = 'unknown'  # default
        else:
            dialect = dialect_id
        #
        # compose lexemes to reject set
        lexemes_to_reject_set = set()
        # add each list of reject lexemes for this dialect
        for list in self.lexemes_to_reject_db[dialect]:
            lexemes_to_reject_set.update(set(list))
        #
        # compose reserved words set
        reswords_set = set()
        # add each list of reserved words for this dialect
        for list in self.reserved_words_db[dialect]:
            reswords_set.update(set(list))
        #
        # compose builtins set
        builtins_set = set()
        # add each list of builtins for this dialect excluding reserved words
        for list in self.builtins_db[dialect]:
            builtins_set.update(set(list).difference(reswords_set))
        #
        # compose pseudo-builtins set
        pseudo_builtins_set = set()
        # add each list of builtins for this dialect excluding reserved words
        for list in self.pseudo_builtins_db[dialect]:
            pseudo_builtins_set.update(set(list).difference(reswords_set))
        #
        # compose ADTs set
        adts_set = set()
        # add each list of ADTs for this dialect excluding reserved words
        for list in self.stdlib_adts_db[dialect]:
            adts_set.update(set(list).difference(reswords_set))
        #
        # compose modules set
        modules_set = set()
        # add each list of builtins for this dialect excluding builtins
        for list in self.stdlib_modules_db[dialect]:
            modules_set.update(set(list).difference(builtins_set))
        #
        # compose types set
        types_set = set()
        # add each list of types for this dialect excluding builtins
        for list in self.stdlib_types_db[dialect]:
            types_set.update(set(list).difference(builtins_set))
        #
        # compose procedures set
        procedures_set = set()
        # add each list of procedures for this dialect excluding builtins
        for list in self.stdlib_procedures_db[dialect]:
            procedures_set.update(set(list).difference(builtins_set))
        #
        # compose variables set
        variables_set = set()
        # add each list of variables for this dialect excluding builtins
        for list in self.stdlib_variables_db[dialect]:
            variables_set.update(set(list).difference(builtins_set))
        #
        # compose constants set
        constants_set = set()
        # add each list of constants for this dialect excluding builtins
        for list in self.stdlib_constants_db[dialect]:
            constants_set.update(set(list).difference(builtins_set))
        #
        # update lexer state
        self.dialect = dialect
        self.lexemes_to_reject = lexemes_to_reject_set
        self.reserved_words = reswords_set
        self.builtins = builtins_set
        self.pseudo_builtins = pseudo_builtins_set
        self.adts = adts_set
        self.modules = modules_set
        self.types = types_set
        self.procedures = procedures_set
        self.variables = variables_set
        self.constants = constants_set
        #
        # if __debug__:
        #    print 'exiting set_dialect'
        #    print ' self.dialect: ', self.dialect
        #    print ' self.lexemes_to_reject: ', self.lexemes_to_reject
        #    print ' self.reserved_words: ', self.reserved_words
        #    print ' self.builtins: ', self.builtins
        #    print ' self.pseudo_builtins: ', self.pseudo_builtins
        #    print ' self.adts: ', self.adts
        #    print ' self.modules: ', self.modules
        #    print ' self.types: ', self.types
        #    print ' self.procedures: ', self.procedures
        #    print ' self.variables: ', self.variables
        #    print ' self.types: ', self.types
        #    print ' self.constants: ', self.constants

    # Extracts a dialect name from a dialect tag comment string  and checks
    # the extracted name against known dialects.  If a match is found,  the
    # matching name is returned, otherwise dialect id 'unknown' is returned
    def get_dialect_from_dialect_tag(self, dialect_tag):
        #
        # if __debug__:
        #    print 'entered get_dialect_from_dialect_tag with arg: ', dialect_tag
        #
        # constants
        left_tag_delim = '(*!'
        right_tag_delim = '*)'
        left_tag_delim_len = len(left_tag_delim)
        right_tag_delim_len = len(right_tag_delim)
        indicator_start = left_tag_delim_len
        indicator_end = -(right_tag_delim_len)
        #
        # check comment string for dialect indicator
        if len(dialect_tag) > (left_tag_delim_len + right_tag_delim_len) \
           and dialect_tag.startswith(left_tag_delim) \
           and dialect_tag.endswith(right_tag_delim):
            #
            # if __debug__:
            #    print 'dialect tag found'
            #
            # extract dialect indicator
            indicator = dialect_tag[indicator_start:indicator_end]
            #
            # if __debug__:
            #    print 'extracted: ', indicator
            #
            # check against known dialects
            for index in range(1, len(self.dialects)):
                #
                # if __debug__:
                #    print 'dialects[', index, ']: ', self.dialects[index]
                #
                if indicator == self.dialects[index]:
                    #
                    # if __debug__:
                    #    print 'matching dialect found'
                    #
                    # indicator matches known dialect
                    return indicator
            else:
                # indicator does not match any dialect
                return 'unknown'  # default
        else:
            # invalid indicator string
            return 'unknown'  # default

    # intercept the token stream, modify token attributes and return them
    def get_tokens_unprocessed(self, text):
        for index, token, value in RegexLexer.get_tokens_unprocessed(self, text):
            #
            # check for dialect tag if dialect has not been set by tag
            if not self.dialect_set_by_tag and token == Comment.Special:
                indicated_dialect = self.get_dialect_from_dialect_tag(value)
                if indicated_dialect != 'unknown':
                    # token is a dialect indicator
                    # reset reserved words and builtins
                    self.set_dialect(indicated_dialect)
                    self.dialect_set_by_tag = True
            #
            # check for reserved words, predefined and stdlib identifiers
            if token is Name:
                if value in self.reserved_words:
                    token = Keyword.Reserved
                    if self.algol_publication_mode:
                        value = value.lower()
                #
                elif value in self.builtins:
                    token = Name.Builtin
                    if self.algol_publication_mode:
                        value = value.lower()
                #
                elif value in self.pseudo_builtins:
                    token = Name.Builtin.Pseudo
                    if self.algol_publication_mode:
                        value = value.lower()
                #
                elif value in self.adts:
                    if not self.treat_stdlib_adts_as_builtins:
                        token = Name.Namespace
                    else:
                        token = Name.Builtin.Pseudo
                        if self.algol_publication_mode:
                            value = value.lower()
                #
                elif value in self.modules:
                    token = Name.Namespace
                #
                elif value in self.types:
                    token = Name.Class
                #
                elif value in self.procedures:
                    token = Name.Function
                #
                elif value in self.variables:
                    token = Name.Variable
                #
                elif value in self.constants:
                    token = Name.Constant
            #
            elif token in Number:
                #
                # mark prefix number literals as error for PIM and ISO dialects
                if self.dialect not in ('unknown', 'm2r10', 'objm2'):
                    if "'" in value or value[0:2] in ('0b', '0x', '0u'):
                        token = Error
                #
                elif self.dialect in ('m2r10', 'objm2'):
                    # mark base-8 number literals as errors for M2 R10 and ObjM2
                    if token is Number.Oct:
                        token = Error
                    # mark suffix base-16 literals as errors for M2 R10 and ObjM2
                    elif token is Number.Hex and 'H' in value:
                        token = Error
                    # mark real numbers with E as errors for M2 R10 and ObjM2
                    elif token is Number.Float and 'E' in value:
                        token = Error
            #
            elif token in Comment:
                #
                # mark single line comment as error for PIM and ISO dialects
                if token is Comment.Single:
                    if self.dialect not in ('unknown', 'm2r10', 'objm2'):
                        token = Error
                #
                if token is Comment.Preproc:
                    # mark ISO pragma as error for PIM dialects
                    if value.startswith('<*') and \
                       self.dialect.startswith('m2pim'):
                        token = Error
                    # mark PIM pragma as comment for other dialects
                    elif value.startswith('(*$') and \
                            self.dialect != 'unknown' and \
                            not self.dialect.startswith('m2pim'):
                        token = Comment.Multiline
            #
            else:  # token is neither Name nor Comment
                #
                # mark lexemes matching the dialect's error token set as errors
                if value in self.lexemes_to_reject:
                    token = Error
                #
                # substitute lexemes when in Algol mode
                if self.algol_publication_mode:
                    if value == '#':
                        value = '≠'
                    elif value == '<=':
                        value = '≤'
                    elif value == '>=':
                        value = '≥'
                    elif value == '==':
                        value = '≡'
                    elif value == '*.':
                        value = '•'

            # return result
            yield index, token, value

    def analyse_text(text):
        """It's Pascal-like, but does not use FUNCTION -- uses PROCEDURE
        instead."""

        # Check if this looks like Pascal, if not, bail out early
        if not ('(*' in text and '*)' in text and ':=' in text):
            return

        result = 0
        # Procedure is in Modula2
        if re.search(r'\bPROCEDURE\b', text):
            result += 0.6

        # FUNCTION is only valid in Pascal, but not in Modula2
        if re.search(r'\bFUNCTION\b', text):
            result = 0.0

        return result

# === NexusCore/openenv\Lib\site-packages\joblib\test\test_memory.py ===
"""
Test the memory module.
"""

# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2009 Gael Varoquaux
# License: BSD Style, 3 clauses.

import datetime
import functools
import gc
import logging
import os
import os.path
import pathlib
import pickle
import shutil
import sys
import textwrap
import time

import pytest

from joblib._store_backends import FileSystemStoreBackend, StoreBackendBase
from joblib.hashing import hash
from joblib.memory import (
    _FUNCTION_HASHES,
    _STORE_BACKENDS,
    JobLibCollisionWarning,
    MemorizedFunc,
    MemorizedResult,
    Memory,
    NotMemorizedFunc,
    NotMemorizedResult,
    _build_func_identifier,
    _store_backend_factory,
    expires_after,
    register_store_backend,
)
from joblib.parallel import Parallel, delayed
from joblib.test.common import np, with_multiprocessing, with_numpy
from joblib.testing import parametrize, raises, warns


###############################################################################
# Module-level variables for the tests
def f(x, y=1):
    """A module-level function for testing purposes."""
    return x**2 + y


###############################################################################
# Helper function for the tests
def check_identity_lazy(func, accumulator, location):
    """Given a function and an accumulator (a list that grows every
    time the function is called), check that the function can be
    decorated by memory to be a lazy identity.
    """
    # Call each function with several arguments, and check that it is
    # evaluated only once per argument.
    memory = Memory(location=location, verbose=0)
    func = memory.cache(func)
    for i in range(3):
        for _ in range(2):
            assert func(i) == i
            assert len(accumulator) == i + 1


def corrupt_single_cache_item(memory):
    (single_cache_item,) = memory.store_backend.get_items()
    output_filename = os.path.join(single_cache_item.path, "output.pkl")
    with open(output_filename, "w") as f:
        f.write("garbage")


def monkeypatch_cached_func_warn(func, monkeypatch_fixture):
    # Need monkeypatch because pytest does not
    # capture stdlib logging output (see
    # https://github.com/pytest-dev/pytest/issues/2079)

    recorded = []

    def append_to_record(item):
        recorded.append(item)

    monkeypatch_fixture.setattr(func, "warn", append_to_record)
    return recorded


###############################################################################
# Tests
def test_memory_integration(tmpdir):
    """Simple test of memory lazy evaluation."""
    accumulator = list()

    # Rmk: this function has the same name than a module-level function,
    # thus it serves as a test to see that both are identified
    # as different.
    def f(arg):
        accumulator.append(1)
        return arg

    check_identity_lazy(f, accumulator, tmpdir.strpath)

    # Now test clearing
    for compress in (False, True):
        for mmap_mode in ("r", None):
            memory = Memory(
                location=tmpdir.strpath,
                verbose=10,
                mmap_mode=mmap_mode,
                compress=compress,
            )
            # First clear the cache directory, to check that our code can
            # handle that
            # NOTE: this line would raise an exception, as the database file is
            # still open; we ignore the error since we want to test what
            # happens if the directory disappears
            shutil.rmtree(tmpdir.strpath, ignore_errors=True)
            g = memory.cache(f)
            g(1)
            g.clear(warn=False)
            current_accumulator = len(accumulator)
            out = g(1)

        assert len(accumulator) == current_accumulator + 1
        # Also, check that Memory.eval works similarly
        assert memory.eval(f, 1) == out
        assert len(accumulator) == current_accumulator + 1

    # Now do a smoke test with a function defined in __main__, as the name
    # mangling rules are more complex
    f.__module__ = "__main__"
    memory = Memory(location=tmpdir.strpath, verbose=0)
    memory.cache(f)(1)


@parametrize("call_before_reducing", [True, False])
def test_parallel_call_cached_function_defined_in_jupyter(tmpdir, call_before_reducing):
    # Calling an interactively defined memory.cache()'d function inside a
    # Parallel call used to clear the existing cache related to the said
    # function (https://github.com/joblib/joblib/issues/1035)

    # This tests checks that this is no longer the case.

    # TODO: test that the cache related to the function cache persists across
    # ipython sessions (provided that no code change were made to the
    # function's source)?

    # The first part of the test makes the necessary low-level calls to emulate
    # the definition of a function in an jupyter notebook cell. Joblib has
    # some custom code to treat functions defined specifically in jupyter
    # notebooks/ipython session -- we want to test this code, which requires
    # the emulation to be rigorous.
    for session_no in [0, 1]:
        ipython_cell_source = """
        def f(x):
            return x
        """

        ipython_cell_id = "<ipython-input-{}-000000000000>".format(session_no)

        my_locals = {}
        exec(
            compile(
                textwrap.dedent(ipython_cell_source),
                filename=ipython_cell_id,
                mode="exec",
            ),
            # TODO when Python 3.11 is the minimum supported version, use
            # locals=my_locals instead of passing globals and locals in the
            # next two lines as positional arguments
            None,
            my_locals,
        )
        f = my_locals["f"]
        f.__module__ = "__main__"

        # Preliminary sanity checks, and tests checking that joblib properly
        # identified f as an interactive function defined in a jupyter notebook
        assert f(1) == 1
        assert f.__code__.co_filename == ipython_cell_id

        memory = Memory(location=tmpdir.strpath, verbose=0)
        cached_f = memory.cache(f)

        assert len(os.listdir(tmpdir / "joblib")) == 1
        f_cache_relative_directory = os.listdir(tmpdir / "joblib")[0]
        assert "ipython-input" in f_cache_relative_directory

        f_cache_directory = tmpdir / "joblib" / f_cache_relative_directory

        if session_no == 0:
            # The cache should be empty as cached_f has not been called yet.
            assert os.listdir(f_cache_directory) == ["f"]
            assert os.listdir(f_cache_directory / "f") == []

            if call_before_reducing:
                cached_f(3)
                # Two files were just created, func_code.py, and a folder
                # containing the information (inputs hash/ouptput) of
                # cached_f(3)
                assert len(os.listdir(f_cache_directory / "f")) == 2

                # Now, testing  #1035: when calling a cached function, joblib
                # used to dynamically inspect the underlying function to
                # extract its source code (to verify it matches the source code
                # of the function as last inspected by joblib) -- however,
                # source code introspection fails for dynamic functions sent to
                # child processes - which would eventually make joblib clear
                # the cache associated to f
                Parallel(n_jobs=2)(delayed(cached_f)(i) for i in [1, 2])
            else:
                # Submit the function to the joblib child processes, although
                # the function has never been called in the parent yet. This
                # triggers a specific code branch inside
                # MemorizedFunc.__reduce__.
                Parallel(n_jobs=2)(delayed(cached_f)(i) for i in [1, 2])
                # Ensure the child process has time to close the file.
                # Wait up to 5 seconds for slow CI runs
                for _ in range(25):
                    if len(os.listdir(f_cache_directory / "f")) == 3:
                        break
                    time.sleep(0.2)  # pragma: no cover
                assert len(os.listdir(f_cache_directory / "f")) == 3

                cached_f(3)

            # Making sure f's cache does not get cleared after the parallel
            # calls, and contains ALL cached functions calls (f(1), f(2), f(3))
            # and 'func_code.py'
            assert len(os.listdir(f_cache_directory / "f")) == 4
        else:
            # For the second session, there should be an already existing cache
            assert len(os.listdir(f_cache_directory / "f")) == 4

            cached_f(3)

            # The previous cache should not be invalidated after calling the
            # function in a new session
            assert len(os.listdir(f_cache_directory / "f")) == 4


def test_no_memory():
    """Test memory with location=None: no memoize"""
    accumulator = list()

    def ff(arg):
        accumulator.append(1)
        return arg

    memory = Memory(location=None, verbose=0)
    gg = memory.cache(ff)
    for _ in range(4):
        current_accumulator = len(accumulator)
        gg(1)
        assert len(accumulator) == current_accumulator + 1


def test_memory_kwarg(tmpdir):
    "Test memory with a function with keyword arguments."
    accumulator = list()

    def g(arg1=None, arg2=1):
        accumulator.append(1)
        return arg1

    check_identity_lazy(g, accumulator, tmpdir.strpath)

    memory = Memory(location=tmpdir.strpath, verbose=0)
    g = memory.cache(g)
    # Smoke test with an explicit keyword argument:
    assert g(arg1=30, arg2=2) == 30


def test_memory_lambda(tmpdir):
    "Test memory with a function with a lambda."
    accumulator = list()

    def helper(x):
        """A helper function to define l as a lambda."""
        accumulator.append(1)
        return x

    check_identity_lazy(lambda x: helper(x), accumulator, tmpdir.strpath)


def test_memory_name_collision(tmpdir):
    "Check that name collisions with functions will raise warnings"
    memory = Memory(location=tmpdir.strpath, verbose=0)

    @memory.cache
    def name_collision(x):
        """A first function called name_collision"""
        return x

    a = name_collision

    @memory.cache
    def name_collision(x):
        """A second function called name_collision"""
        return x

    b = name_collision

    with warns(JobLibCollisionWarning) as warninfo:
        a(1)
        b(1)

    assert len(warninfo) == 1
    assert "collision" in str(warninfo[0].message)


def test_memory_warning_lambda_collisions(tmpdir):
    # Check that multiple use of lambda will raise collisions
    memory = Memory(location=tmpdir.strpath, verbose=0)
    a = memory.cache(lambda x: x)
    b = memory.cache(lambda x: x + 1)

    with warns(JobLibCollisionWarning) as warninfo:
        assert a(0) == 0
        assert b(1) == 2
        assert a(1) == 1

    # In recent Python versions, we can retrieve the code of lambdas,
    # thus nothing is raised
    assert len(warninfo) == 4


def test_memory_warning_collision_detection(tmpdir):
    # Check that collisions impossible to detect will raise appropriate
    # warnings.
    memory = Memory(location=tmpdir.strpath, verbose=0)
    a1 = eval("lambda x: x")
    a1 = memory.cache(a1)
    b1 = eval("lambda x: x+1")
    b1 = memory.cache(b1)

    with warns(JobLibCollisionWarning) as warninfo:
        a1(1)
        b1(1)
        a1(0)

    assert len(warninfo) == 2
    assert "cannot detect" in str(warninfo[0].message).lower()


def test_memory_partial(tmpdir):
    "Test memory with functools.partial."
    accumulator = list()

    def func(x, y):
        """A helper function to define l as a lambda."""
        accumulator.append(1)
        return y

    import functools

    function = functools.partial(func, 1)

    check_identity_lazy(function, accumulator, tmpdir.strpath)


def test_memory_eval(tmpdir):
    "Smoke test memory with a function with a function defined in an eval."
    memory = Memory(location=tmpdir.strpath, verbose=0)

    m = eval("lambda x: x")
    mm = memory.cache(m)

    assert mm(1) == 1


def count_and_append(x=[]):
    """A function with a side effect in its arguments.

    Return the length of its argument and append one element.
    """
    len_x = len(x)
    x.append(None)
    return len_x


def test_argument_change(tmpdir):
    """Check that if a function has a side effect in its arguments, it
    should use the hash of changing arguments.
    """
    memory = Memory(location=tmpdir.strpath, verbose=0)
    func = memory.cache(count_and_append)
    # call the function for the first time, is should cache it with
    # argument x=[]
    assert func() == 0
    # the second time the argument is x=[None], which is not cached
    # yet, so the functions should be called a second time
    assert func() == 1


@with_numpy
@parametrize("mmap_mode", [None, "r"])
def test_memory_numpy(tmpdir, mmap_mode):
    "Test memory with a function with numpy arrays."
    accumulator = list()

    def n(arg=None):
        accumulator.append(1)
        return arg

    memory = Memory(location=tmpdir.strpath, mmap_mode=mmap_mode, verbose=0)
    cached_n = memory.cache(n)

    rnd = np.random.RandomState(0)
    for i in range(3):
        a = rnd.random_sample((10, 10))
        for _ in range(3):
            assert np.all(cached_n(a) == a)
            assert len(accumulator) == i + 1


@with_numpy
def test_memory_numpy_check_mmap_mode(tmpdir, monkeypatch):
    """Check that mmap_mode is respected even at the first call"""

    memory = Memory(location=tmpdir.strpath, mmap_mode="r", verbose=0)

    @memory.cache()
    def twice(a):
        return a * 2

    a = np.ones(3)

    b = twice(a)
    c = twice(a)

    assert isinstance(c, np.memmap)
    assert c.mode == "r"

    assert isinstance(b, np.memmap)
    assert b.mode == "r"

    # Corrupts the file,  Deleting b and c mmaps
    # is necessary to be able edit the file
    del b
    del c
    gc.collect()
    corrupt_single_cache_item(memory)

    # Make sure that corrupting the file causes recomputation and that
    # a warning is issued.
    recorded_warnings = monkeypatch_cached_func_warn(twice, monkeypatch)
    d = twice(a)
    assert len(recorded_warnings) == 1
    exception_msg = "Exception while loading results"
    assert exception_msg in recorded_warnings[0]
    # Asserts that the recomputation returns a mmap
    assert isinstance(d, np.memmap)
    assert d.mode == "r"


def test_memory_exception(tmpdir):
    """Smoketest the exception handling of Memory."""
    memory = Memory(location=tmpdir.strpath, verbose=0)

    class MyException(Exception):
        pass

    @memory.cache
    def h(exc=0):
        if exc:
            raise MyException

    # Call once, to initialise the cache
    h()

    for _ in range(3):
        # Call 3 times, to be sure that the Exception is always raised
        with raises(MyException):
            h(1)


def test_memory_ignore(tmpdir):
    "Test the ignore feature of memory"
    memory = Memory(location=tmpdir.strpath, verbose=0)
    accumulator = list()

    @memory.cache(ignore=["y"])
    def z(x, y=1):
        accumulator.append(1)

    assert z.ignore == ["y"]

    z(0, y=1)
    assert len(accumulator) == 1
    z(0, y=1)
    assert len(accumulator) == 1
    z(0, y=2)
    assert len(accumulator) == 1


def test_memory_ignore_decorated(tmpdir):
    "Test the ignore feature of memory on a decorated function"
    memory = Memory(location=tmpdir.strpath, verbose=0)
    accumulator = list()

    def decorate(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            return f(*args, **kwargs)

        return wrapped

    @memory.cache(ignore=["y"])
    @decorate
    def z(x, y=1):
        accumulator.append(1)

    assert z.ignore == ["y"]

    z(0, y=1)
    assert len(accumulator) == 1
    z(0, y=1)
    assert len(accumulator) == 1
    z(0, y=2)
    assert len(accumulator) == 1


def test_memory_args_as_kwargs(tmpdir):
    """Non-regression test against 0.12.0 changes.

    https://github.com/joblib/joblib/pull/751
    """
    memory = Memory(location=tmpdir.strpath, verbose=0)

    @memory.cache
    def plus_one(a):
        return a + 1

    # It's possible to call a positional arg as a kwarg.
    assert plus_one(1) == 2
    assert plus_one(a=1) == 2

    # However, a positional argument that joblib hadn't seen
    # before would cause a failure if it was passed as a kwarg.
    assert plus_one(a=2) == 3


@parametrize("ignore, verbose, mmap_mode", [(["x"], 100, "r"), ([], 10, None)])
def test_partial_decoration(tmpdir, ignore, verbose, mmap_mode):
    "Check cache may be called with kwargs before decorating"
    memory = Memory(location=tmpdir.strpath, verbose=0)

    @memory.cache(ignore=ignore, verbose=verbose, mmap_mode=mmap_mode)
    def z(x):
        pass

    assert z.ignore == ignore
    assert z._verbose == verbose
    assert z.mmap_mode == mmap_mode


def test_func_dir(tmpdir):
    # Test the creation of the memory cache directory for the function.
    memory = Memory(location=tmpdir.strpath, verbose=0)
    path = __name__.split(".")
    path.append("f")
    path = tmpdir.join("joblib", *path).strpath

    g = memory.cache(f)
    # Test that the function directory is created on demand
    func_id = _build_func_identifier(f)
    location = os.path.join(g.store_backend.location, func_id)
    assert location == path
    assert os.path.exists(path)
    assert memory.location == os.path.dirname(g.store_backend.location)

    # Test that the code is stored.
    # For the following test to be robust to previous execution, we clear
    # the in-memory store
    _FUNCTION_HASHES.clear()
    assert not g._check_previous_func_code()
    assert os.path.exists(os.path.join(path, "func_code.py"))
    assert g._check_previous_func_code()

    # Test the robustness to failure of loading previous results.
    args_id = g._get_args_id(1)
    output_dir = os.path.join(g.store_backend.location, g.func_id, args_id)
    a = g(1)
    assert os.path.exists(output_dir)
    os.remove(os.path.join(output_dir, "output.pkl"))
    assert a == g(1)


def test_persistence(tmpdir):
    # Test the memorized functions can be pickled and restored.
    memory = Memory(location=tmpdir.strpath, verbose=0)
    g = memory.cache(f)
    output = g(1)

    h = pickle.loads(pickle.dumps(g))

    args_id = h._get_args_id(1)
    output_dir = os.path.join(h.store_backend.location, h.func_id, args_id)
    assert os.path.exists(output_dir)
    assert output == h.store_backend.load_item([h.func_id, args_id])
    memory2 = pickle.loads(pickle.dumps(memory))
    assert memory.store_backend.location == memory2.store_backend.location

    # Smoke test that pickling a memory with location=None works
    memory = Memory(location=None, verbose=0)
    pickle.loads(pickle.dumps(memory))
    g = memory.cache(f)
    gp = pickle.loads(pickle.dumps(g))
    gp(1)


@pytest.mark.parametrize("consider_cache_valid", [True, False])
def test_check_call_in_cache(tmpdir, consider_cache_valid):
    for func in (
        MemorizedFunc(
            f, tmpdir.strpath, cache_validation_callback=lambda _: consider_cache_valid
        ),
        Memory(location=tmpdir.strpath, verbose=0).cache(
            f, cache_validation_callback=lambda _: consider_cache_valid
        ),
    ):
        result = func.check_call_in_cache(2)
        assert isinstance(result, bool)
        assert not result
        assert func(2) == 5
        result = func.check_call_in_cache(2)
        assert isinstance(result, bool)
        assert result == consider_cache_valid
        func.clear()

    func = NotMemorizedFunc(f)
    assert not func.check_call_in_cache(2)


def test_call_and_shelve(tmpdir):
    # Test MemorizedFunc outputting a reference to cache.

    for func, Result in zip(
        (
            MemorizedFunc(f, tmpdir.strpath),
            NotMemorizedFunc(f),
            Memory(location=tmpdir.strpath, verbose=0).cache(f),
            Memory(location=None).cache(f),
        ),
        (MemorizedResult, NotMemorizedResult, MemorizedResult, NotMemorizedResult),
    ):
        assert func(2) == 5
        result = func.call_and_shelve(2)
        assert isinstance(result, Result)
        assert result.get() == 5

        result.clear()
        with raises(KeyError):
            result.get()
        result.clear()  # Do nothing if there is no cache.


def test_call_and_shelve_lazily_load_stored_result(tmpdir):
    """Check call_and_shelve only load stored data if needed."""
    test_access_time_file = tmpdir.join("test_access")
    test_access_time_file.write("test_access")
    test_access_time = os.stat(test_access_time_file.strpath).st_atime
    # check file system access time stats resolution is lower than test wait
    # timings.
    time.sleep(0.5)
    assert test_access_time_file.read() == "test_access"

    if test_access_time == os.stat(test_access_time_file.strpath).st_atime:
        # Skip this test when access time cannot be retrieved with enough
        # precision from the file system (e.g. NTFS on windows).
        pytest.skip("filesystem does not support fine-grained access time attribute")

    memory = Memory(location=tmpdir.strpath, verbose=0)
    func = memory.cache(f)
    args_id = func._get_args_id(2)
    result_path = os.path.join(
        memory.store_backend.location, func.func_id, args_id, "output.pkl"
    )
    assert func(2) == 5
    first_access_time = os.stat(result_path).st_atime
    time.sleep(1)

    # Should not access the stored data
    result = func.call_and_shelve(2)
    assert isinstance(result, MemorizedResult)
    assert os.stat(result_path).st_atime == first_access_time
    time.sleep(1)

    # Read the stored data => last access time is greater than first_access
    assert result.get() == 5
    assert os.stat(result_path).st_atime > first_access_time


def test_memorized_pickling(tmpdir):
    for func in (MemorizedFunc(f, tmpdir.strpath), NotMemorizedFunc(f)):
        filename = tmpdir.join("pickling_test.dat").strpath
        result = func.call_and_shelve(2)
        with open(filename, "wb") as fp:
            pickle.dump(result, fp)
        with open(filename, "rb") as fp:
            result2 = pickle.load(fp)
        assert result2.get() == result.get()
        os.remove(filename)


def test_memorized_repr(tmpdir):
    func = MemorizedFunc(f, tmpdir.strpath)
    result = func.call_and_shelve(2)

    func2 = MemorizedFunc(f, tmpdir.strpath)
    result2 = func2.call_and_shelve(2)
    assert result.get() == result2.get()
    assert repr(func) == repr(func2)

    # Smoke test with NotMemorizedFunc
    func = NotMemorizedFunc(f)
    repr(func)
    repr(func.call_and_shelve(2))

    # Smoke test for message output (increase code coverage)
    func = MemorizedFunc(f, tmpdir.strpath, verbose=11, timestamp=time.time())
    result = func.call_and_shelve(11)
    result.get()

    func = MemorizedFunc(f, tmpdir.strpath, verbose=11)
    result = func.call_and_shelve(11)
    result.get()

    func = MemorizedFunc(f, tmpdir.strpath, verbose=5, timestamp=time.time())
    result = func.call_and_shelve(11)
    result.get()

    func = MemorizedFunc(f, tmpdir.strpath, verbose=5)
    result = func.call_and_shelve(11)
    result.get()


def test_memory_file_modification(capsys, tmpdir, monkeypatch):
    # Test that modifying a Python file after loading it does not lead to
    # Recomputation
    dir_name = tmpdir.mkdir("tmp_import").strpath
    filename = os.path.join(dir_name, "tmp_joblib_.py")
    content = "def f(x):\n    print(x)\n    return x\n"
    with open(filename, "w") as module_file:
        module_file.write(content)

    # Load the module:
    monkeypatch.syspath_prepend(dir_name)
    import tmp_joblib_ as tmp

    memory = Memory(location=tmpdir.strpath, verbose=0)
    f = memory.cache(tmp.f)
    # First call f a few times
    f(1)
    f(2)
    f(1)

    # Now modify the module where f is stored without modifying f
    with open(filename, "w") as module_file:
        module_file.write("\n\n" + content)

    # And call f a couple more times
    f(1)
    f(1)

    # Flush the .pyc files
    shutil.rmtree(dir_name)
    os.mkdir(dir_name)
    # Now modify the module where f is stored, modifying f
    content = 'def f(x):\n    print("x=%s" % x)\n    return x\n'
    with open(filename, "w") as module_file:
        module_file.write(content)

    # And call f more times prior to reloading: the cache should not be
    # invalidated at this point as the active function definition has not
    # changed in memory yet.
    f(1)
    f(1)

    # Now reload
    sys.stdout.write("Reloading\n")
    sys.modules.pop("tmp_joblib_")
    import tmp_joblib_ as tmp

    f = memory.cache(tmp.f)

    # And call f more times
    f(1)
    f(1)

    out, err = capsys.readouterr()
    assert out == "1\n2\nReloading\nx=1\n"


def _function_to_cache(a, b):
    # Just a place holder function to be mutated by tests
    pass


def _sum(a, b):
    return a + b


def _product(a, b):
    return a * b


def test_memory_in_memory_function_code_change(tmpdir):
    _function_to_cache.__code__ = _sum.__code__

    memory = Memory(location=tmpdir.strpath, verbose=0)
    f = memory.cache(_function_to_cache)

    assert f(1, 2) == 3
    assert f(1, 2) == 3

    with warns(JobLibCollisionWarning):
        # Check that inline function modification triggers a cache invalidation
        _function_to_cache.__code__ = _product.__code__
        assert f(1, 2) == 2
        assert f(1, 2) == 2


def test_clear_memory_with_none_location():
    memory = Memory(location=None)
    memory.clear()


def func_with_kwonly_args(a, b, *, kw1="kw1", kw2="kw2"):
    return a, b, kw1, kw2


def func_with_signature(a: int, b: float) -> float:
    return a + b


def test_memory_func_with_kwonly_args(tmpdir):
    memory = Memory(location=tmpdir.strpath, verbose=0)
    func_cached = memory.cache(func_with_kwonly_args)

    assert func_cached(1, 2, kw1=3) == (1, 2, 3, "kw2")

    # Making sure that providing a keyword-only argument by
    # position raises an exception
    with raises(ValueError) as excinfo:
        func_cached(1, 2, 3, kw2=4)
    excinfo.match("Keyword-only parameter 'kw1' was passed as positional parameter")

    # Keyword-only parameter passed by position with cached call
    # should still raise ValueError
    func_cached(1, 2, kw1=3, kw2=4)

    with raises(ValueError) as excinfo:
        func_cached(1, 2, 3, kw2=4)
    excinfo.match("Keyword-only parameter 'kw1' was passed as positional parameter")

    # Test 'ignore' parameter
    func_cached = memory.cache(func_with_kwonly_args, ignore=["kw2"])
    assert func_cached(1, 2, kw1=3, kw2=4) == (1, 2, 3, 4)
    assert func_cached(1, 2, kw1=3, kw2="ignored") == (1, 2, 3, 4)


def test_memory_func_with_signature(tmpdir):
    memory = Memory(location=tmpdir.strpath, verbose=0)
    func_cached = memory.cache(func_with_signature)

    assert func_cached(1, 2.0) == 3.0


def _setup_toy_cache(tmpdir, num_inputs=10):
    memory = Memory(location=tmpdir.strpath, verbose=0)

    @memory.cache()
    def get_1000_bytes(arg):
        return "a" * 1000

    inputs = list(range(num_inputs))
    for arg in inputs:
        get_1000_bytes(arg)

    func_id = _build_func_identifier(get_1000_bytes)
    hash_dirnames = [get_1000_bytes._get_args_id(arg) for arg in inputs]

    full_hashdirs = [
        os.path.join(get_1000_bytes.store_backend.location, func_id, dirname)
        for dirname in hash_dirnames
    ]
    return memory, full_hashdirs, get_1000_bytes


def test__get_items(tmpdir):
    memory, expected_hash_dirs, _ = _setup_toy_cache(tmpdir)
    items = memory.store_backend.get_items()
    hash_dirs = [ci.path for ci in items]
    assert set(hash_dirs) == set(expected_hash_dirs)

    def get_files_size(directory):
        full_paths = [os.path.join(directory, fn) for fn in os.listdir(directory)]
        return sum(os.path.getsize(fp) for fp in full_paths)

    expected_hash_cache_sizes = [get_files_size(hash_dir) for hash_dir in hash_dirs]
    hash_cache_sizes = [ci.size for ci in items]
    assert hash_cache_sizes == expected_hash_cache_sizes

    output_filenames = [os.path.join(hash_dir, "output.pkl") for hash_dir in hash_dirs]

    expected_last_accesses = [
        datetime.datetime.fromtimestamp(os.path.getatime(fn)) for fn in output_filenames
    ]
    last_accesses = [ci.last_access for ci in items]
    assert last_accesses == expected_last_accesses


def test__get_items_to_delete(tmpdir):
    # test empty cache
    memory, _, _ = _setup_toy_cache(tmpdir, num_inputs=0)
    items_to_delete = memory.store_backend._get_items_to_delete("1K")
    assert items_to_delete == []

    memory, expected_hash_cachedirs, _ = _setup_toy_cache(tmpdir)
    items = memory.store_backend.get_items()
    # bytes_limit set to keep only one cache item (each hash cache
    # folder is about 1000 bytes + metadata)
    items_to_delete = memory.store_backend._get_items_to_delete("2K")
    nb_hashes = len(expected_hash_cachedirs)
    assert set.issubset(set(items_to_delete), set(items))
    assert len(items_to_delete) == nb_hashes - 1

    # Sanity check bytes_limit=2048 is the same as bytes_limit='2K'
    items_to_delete_2048b = memory.store_backend._get_items_to_delete(2048)
    assert sorted(items_to_delete) == sorted(items_to_delete_2048b)

    # bytes_limit greater than the size of the cache
    items_to_delete_empty = memory.store_backend._get_items_to_delete("1M")
    assert items_to_delete_empty == []

    # All the cache items need to be deleted
    bytes_limit_too_small = 500
    items_to_delete_500b = memory.store_backend._get_items_to_delete(
        bytes_limit_too_small
    )
    assert set(items_to_delete_500b), set(items)

    # Test LRU property: surviving cache items should all have a more
    # recent last_access that the ones that have been deleted
    items_to_delete_6000b = memory.store_backend._get_items_to_delete(6000)
    surviving_items = set(items).difference(items_to_delete_6000b)

    assert max(ci.last_access for ci in items_to_delete_6000b) <= min(
        ci.last_access for ci in surviving_items
    )


def test_memory_reduce_size_bytes_limit(tmpdir):
    memory, _, _ = _setup_toy_cache(tmpdir)
    ref_cache_items = memory.store_backend.get_items()

    # By default memory.bytes_limit is None and reduce_size is a noop
    memory.reduce_size()
    cache_items = memory.store_backend.get_items()
    assert sorted(ref_cache_items) == sorted(cache_items)

    # No cache items deleted if bytes_limit greater than the size of
    # the cache
    memory.reduce_size(bytes_limit="1M")
    cache_items = memory.store_backend.get_items()
    assert sorted(ref_cache_items) == sorted(cache_items)

    # bytes_limit is set so that only two cache items are kept
    memory.reduce_size(bytes_limit="3K")
    cache_items = memory.store_backend.get_items()
    assert set.issubset(set(cache_items), set(ref_cache_items))
    assert len(cache_items) == 2

    # bytes_limit set so that no cache item is kept
    bytes_limit_too_small = 500
    memory.reduce_size(bytes_limit=bytes_limit_too_small)
    cache_items = memory.store_backend.get_items()
    assert cache_items == []


def test_memory_reduce_size_items_limit(tmpdir):
    memory, _, _ = _setup_toy_cache(tmpdir)
    ref_cache_items = memory.store_backend.get_items()

    # By default reduce_size is a noop
    memory.reduce_size()
    cache_items = memory.store_backend.get_items()
    assert sorted(ref_cache_items) == sorted(cache_items)

    # No cache items deleted if items_limit greater than the size of
    # the cache
    memory.reduce_size(items_limit=10)
    cache_items = memory.store_backend.get_items()
    assert sorted(ref_cache_items) == sorted(cache_items)

    # items_limit is set so that only two cache items are kept
    memory.reduce_size(items_limit=2)
    cache_items = memory.store_backend.get_items()
    assert set.issubset(set(cache_items), set(ref_cache_items))
    assert len(cache_items) == 2

    # item_limit set so that no cache item is kept
    memory.reduce_size(items_limit=0)
    cache_items = memory.store_backend.get_items()
    assert cache_items == []


def test_memory_reduce_size_age_limit(tmpdir):
    import datetime
    import time

    memory, _, put_cache = _setup_toy_cache(tmpdir)
    ref_cache_items = memory.store_backend.get_items()

    # By default reduce_size is a noop
    memory.reduce_size()
    cache_items = memory.store_backend.get_items()
    assert sorted(ref_cache_items) == sorted(cache_items)

    # No cache items deleted if age_limit big.
    memory.reduce_size(age_limit=datetime.timedelta(days=1))
    cache_items = memory.store_backend.get_items()
    assert sorted(ref_cache_items) == sorted(cache_items)

    # age_limit is set so that only two cache items are kept
    time.sleep(1)
    put_cache(-1)
    put_cache(-2)
    memory.reduce_size(age_limit=datetime.timedelta(seconds=1))
    cache_items = memory.store_backend.get_items()
    assert not set.issubset(set(cache_items), set(ref_cache_items))
    assert len(cache_items) == 2

    # ensure age_limit is forced to be positive
    with pytest.raises(ValueError, match="has to be a positive"):
        memory.reduce_size(age_limit=datetime.timedelta(seconds=-1))

    # age_limit set so that no cache item is kept
    time.sleep(0.001)  # make sure the age is different
    memory.reduce_size(age_limit=datetime.timedelta(seconds=0))
    cache_items = memory.store_backend.get_items()
    assert cache_items == []


def test_memory_clear(tmpdir):
    memory, _, g = _setup_toy_cache(tmpdir)
    memory.clear()

    assert os.listdir(memory.store_backend.location) == []

    # Check that the cache for functions hash is also reset.
    assert not g._check_previous_func_code(stacklevel=4)


def fast_func_with_complex_output():
    complex_obj = ["a" * 1000] * 1000
    return complex_obj


def fast_func_with_conditional_complex_output(complex_output=True):
    complex_obj = {str(i): i for i in range(int(1e5))}
    return complex_obj if complex_output else "simple output"


@with_multiprocessing
def test_cached_function_race_condition_when_persisting_output(tmpdir, capfd):
    # Test race condition where multiple processes are writing into
    # the same output.pkl. See
    # https://github.com/joblib/joblib/issues/490 for more details.
    memory = Memory(location=tmpdir.strpath)
    func_cached = memory.cache(fast_func_with_complex_output)

    Parallel(n_jobs=2)(delayed(func_cached)() for i in range(3))

    stdout, stderr = capfd.readouterr()

    # Checking both stdout and stderr (ongoing PR #434 may change
    # logging destination) to make sure there is no exception while
    # loading the results
    exception_msg = "Exception while loading results"
    assert exception_msg not in stdout
    assert exception_msg not in stderr


@with_multiprocessing
def test_cached_function_race_condition_when_persisting_output_2(tmpdir, capfd):
    # Test race condition in first attempt at solving
    # https://github.com/joblib/joblib/issues/490. The race condition
    # was due to the delay between seeing the cache directory created
    # (interpreted as the result being cached) and the output.pkl being
    # pickled.
    memory = Memory(location=tmpdir.strpath)
    func_cached = memory.cache(fast_func_with_conditional_complex_output)

    Parallel(n_jobs=2)(
        delayed(func_cached)(True if i % 2 == 0 else False) for i in range(3)
    )

    stdout, stderr = capfd.readouterr()

    # Checking both stdout and stderr (ongoing PR #434 may change
    # logging destination) to make sure there is no exception while
    # loading the results
    exception_msg = "Exception while loading results"
    assert exception_msg not in stdout
    assert exception_msg not in stderr


def test_memory_recomputes_after_an_error_while_loading_results(tmpdir, monkeypatch):
    memory = Memory(location=tmpdir.strpath)

    def func(arg):
        # This makes sure that the timestamp returned by two calls of
        # func are different. This is needed on Windows where
        # time.time resolution may not be accurate enough
        time.sleep(0.01)
        return arg, time.time()

    cached_func = memory.cache(func)
    input_arg = "arg"
    arg, timestamp = cached_func(input_arg)

    # Make sure the function is correctly cached
    assert arg == input_arg

    # Corrupting output.pkl to make sure that an error happens when
    # loading the cached result
    corrupt_single_cache_item(memory)

    # Make sure that corrupting the file causes recomputation and that
    # a warning is issued.
    recorded_warnings = monkeypatch_cached_func_warn(cached_func, monkeypatch)
    recomputed_arg, recomputed_timestamp = cached_func(arg)
    assert len(recorded_warnings) == 1
    exception_msg = "Exception while loading results"
    assert exception_msg in recorded_warnings[0]
    assert recomputed_arg == arg
    assert recomputed_timestamp > timestamp

    # Corrupting output.pkl to make sure that an error happens when
    # loading the cached result
    corrupt_single_cache_item(memory)
    reference = cached_func.call_and_shelve(arg)
    try:
        reference.get()
        raise AssertionError(
            "It normally not possible to load a corrupted MemorizedResult"
        )
    except KeyError as e:
        message = "is corrupted"
        assert message in str(e.args)


class IncompleteStoreBackend(StoreBackendBase):
    """This backend cannot be instantiated and should raise a TypeError."""

    pass


class DummyStoreBackend(StoreBackendBase):
    """A dummy store backend that does nothing."""

    def _open_item(self, *args, **kwargs):
        """Open an item on store."""
        "Does nothing"

    def _item_exists(self, location):
        """Check if an item location exists."""
        "Does nothing"

    def _move_item(self, src, dst):
        """Move an item from src to dst in store."""
        "Does nothing"

    def create_location(self, location):
        """Create location on store."""
        "Does nothing"

    def exists(self, obj):
        """Check if an object exists in the store"""
        return False

    def clear_location(self, obj):
        """Clear object on store"""
        "Does nothing"

    def get_items(self):
        """Returns the whole list of items available in cache."""
        return []

    def configure(self, location, *args, **kwargs):
        """Configure the store"""
        "Does nothing"


@parametrize("invalid_prefix", [None, dict(), list()])
def test_register_invalid_store_backends_key(invalid_prefix):
    # verify the right exceptions are raised when passing a wrong backend key.
    with raises(ValueError) as excinfo:
        register_store_backend(invalid_prefix, None)
    excinfo.match(r"Store backend name should be a string*")


def test_register_invalid_store_backends_object():
    # verify the right exceptions are raised when passing a wrong backend
    # object.
    with raises(ValueError) as excinfo:
        register_store_backend("fs", None)
    excinfo.match(r"Store backend should inherit StoreBackendBase*")


def test_memory_default_store_backend():
    # test an unknown backend falls back into a FileSystemStoreBackend
    with raises(TypeError) as excinfo:
        Memory(location="/tmp/joblib", backend="unknown")
    excinfo.match(r"Unknown location*")


def test_warning_on_unknown_location_type():
    class NonSupportedLocationClass:
        pass

    unsupported_location = NonSupportedLocationClass()

    with warns(UserWarning) as warninfo:
        _store_backend_factory("local", location=unsupported_location)

    expected_mesage = (
        "Instantiating a backend using a "
        "NonSupportedLocationClass as a location is not "
        "supported by joblib"
    )
    assert expected_mesage in str(warninfo[0].message)


def test_instanciate_incomplete_store_backend():
    # Verify that registering an external incomplete store backend raises an
    # exception when one tries to instantiate it.
    backend_name = "isb"
    register_store_backend(backend_name, IncompleteStoreBackend)
    assert (backend_name, IncompleteStoreBackend) in _STORE_BACKENDS.items()
    with raises(TypeError) as excinfo:
        _store_backend_factory(backend_name, "fake_location")
    excinfo.match(
        r"Can't instantiate abstract class IncompleteStoreBackend "
        "(without an implementation for|with) abstract methods*"
    )


def test_dummy_store_backend():
    # Verify that registering an external store backend works.

    backend_name = "dsb"
    register_store_backend(backend_name, DummyStoreBackend)
    assert (backend_name, DummyStoreBackend) in _STORE_BACKENDS.items()

    backend_obj = _store_backend_factory(backend_name, "dummy_location")
    assert isinstance(backend_obj, DummyStoreBackend)


def test_instanciate_store_backend_with_pathlib_path():
    # Instantiate a FileSystemStoreBackend using a pathlib.Path object
    path = pathlib.Path("some_folder")
    backend_obj = _store_backend_factory("local", path)
    try:
        assert backend_obj.location == "some_folder"
    finally:  # remove cache folder after test
        shutil.rmtree("some_folder", ignore_errors=True)


def test_filesystem_store_backend_repr(tmpdir):
    # Verify string representation of a filesystem store backend.

    repr_pattern = 'FileSystemStoreBackend(location="{location}")'
    backend = FileSystemStoreBackend()
    assert backend.location is None

    repr(backend)  # Should not raise an exception

    assert str(backend) == repr_pattern.format(location=None)

    # backend location is passed explicitly via the configure method (called
    # by the internal _store_backend_factory function)
    backend.configure(tmpdir.strpath)

    assert str(backend) == repr_pattern.format(location=tmpdir.strpath)

    repr(backend)  # Should not raise an exception


def test_memory_objects_repr(tmpdir):
    # Verify printable reprs of MemorizedResult, MemorizedFunc and Memory.

    def my_func(a, b):
        return a + b

    memory = Memory(location=tmpdir.strpath, verbose=0)
    memorized_func = memory.cache(my_func)

    memorized_func_repr = "MemorizedFunc(func={func}, location={location})"

    assert str(memorized_func) == memorized_func_repr.format(
        func=my_func, location=memory.store_backend.location
    )

    memorized_result = memorized_func.call_and_shelve(42, 42)

    memorized_result_repr = (
        'MemorizedResult(location="{location}", func="{func}", args_id="{args_id}")'
    )

    assert str(memorized_result) == memorized_result_repr.format(
        location=memory.store_backend.location,
        func=memorized_result.func_id,
        args_id=memorized_result.args_id,
    )

    assert str(memory) == "Memory(location={location})".format(
        location=memory.store_backend.location
    )


def test_memorized_result_pickle(tmpdir):
    # Verify a MemoryResult object can be pickled/depickled. Non regression
    # test introduced following issue
    # https://github.com/joblib/joblib/issues/747

    memory = Memory(location=tmpdir.strpath)

    @memory.cache
    def g(x):
        return x**2

    memorized_result = g.call_and_shelve(4)
    memorized_result_pickle = pickle.dumps(memorized_result)
    memorized_result_loads = pickle.loads(memorized_result_pickle)

    assert (
        memorized_result.store_backend.location
        == memorized_result_loads.store_backend.location
    )
    assert memorized_result.func == memorized_result_loads.func
    assert memorized_result.args_id == memorized_result_loads.args_id
    assert str(memorized_result) == str(memorized_result_loads)


def compare(left, right, ignored_attrs=None):
    if ignored_attrs is None:
        ignored_attrs = []

    left_vars = vars(left)
    right_vars = vars(right)
    assert set(left_vars.keys()) == set(right_vars.keys())
    for attr in left_vars.keys():
        if attr in ignored_attrs:
            continue
        assert left_vars[attr] == right_vars[attr]


@pytest.mark.parametrize(
    "memory_kwargs",
    [
        {"compress": 3, "verbose": 2},
        {"mmap_mode": "r", "verbose": 5, "backend_options": {"parameter": "unused"}},
    ],
)
def test_memory_pickle_dump_load(tmpdir, memory_kwargs):
    memory = Memory(location=tmpdir.strpath, **memory_kwargs)

    memory_reloaded = pickle.loads(pickle.dumps(memory))

    # Compare Memory instance before and after pickle roundtrip
    compare(memory.store_backend, memory_reloaded.store_backend)
    compare(
        memory,
        memory_reloaded,
        ignored_attrs=set(["store_backend", "timestamp", "_func_code_id"]),
    )
    assert hash(memory) == hash(memory_reloaded)

    func_cached = memory.cache(f)

    func_cached_reloaded = pickle.loads(pickle.dumps(func_cached))

    # Compare MemorizedFunc instance before/after pickle roundtrip
    compare(func_cached.store_backend, func_cached_reloaded.store_backend)
    compare(
        func_cached,
        func_cached_reloaded,
        ignored_attrs=set(["store_backend", "timestamp", "_func_code_id"]),
    )
    assert hash(func_cached) == hash(func_cached_reloaded)

    # Compare MemorizedResult instance before/after pickle roundtrip
    memorized_result = func_cached.call_and_shelve(1)
    memorized_result_reloaded = pickle.loads(pickle.dumps(memorized_result))

    compare(memorized_result.store_backend, memorized_result_reloaded.store_backend)
    compare(
        memorized_result,
        memorized_result_reloaded,
        ignored_attrs=set(["store_backend", "timestamp", "_func_code_id"]),
    )
    assert hash(memorized_result) == hash(memorized_result_reloaded)


def test_info_log(tmpdir, caplog):
    caplog.set_level(logging.INFO)
    x = 3

    memory = Memory(location=tmpdir.strpath, verbose=20)

    @memory.cache
    def f(x):
        return x**2

    _ = f(x)
    assert "Querying" in caplog.text
    caplog.clear()

    memory = Memory(location=tmpdir.strpath, verbose=0)

    @memory.cache
    def f(x):
        return x**2

    _ = f(x)
    assert "Querying" not in caplog.text
    caplog.clear()


class TestCacheValidationCallback:
    "Tests on parameter `cache_validation_callback`"

    def foo(self, x, d, delay=None):
        d["run"] = True
        if delay is not None:
            time.sleep(delay)
        return x * 2

    def test_invalid_cache_validation_callback(self, memory):
        "Test invalid values for `cache_validation_callback"
        match = "cache_validation_callback needs to be callable. Got True."
        with pytest.raises(ValueError, match=match):
            memory.cache(cache_validation_callback=True)

    @pytest.mark.parametrize("consider_cache_valid", [True, False])
    def test_constant_cache_validation_callback(self, memory, consider_cache_valid):
        "Test expiry of old results"
        f = memory.cache(
            self.foo,
            cache_validation_callback=lambda _: consider_cache_valid,
            ignore=["d"],
        )

        d1, d2 = {"run": False}, {"run": False}
        assert f(2, d1) == 4
        assert f(2, d2) == 4

        assert d1["run"]
        assert d2["run"] != consider_cache_valid

    def test_memory_only_cache_long_run(self, memory):
        "Test cache validity based on run duration."

        def cache_validation_callback(metadata):
            duration = metadata["duration"]
            if duration > 0.1:
                return True

        f = memory.cache(
            self.foo, cache_validation_callback=cache_validation_callback, ignore=["d"]
        )

        # Short run are not cached
        d1, d2 = {"run": False}, {"run": False}
        assert f(2, d1, delay=0) == 4
        assert f(2, d2, delay=0) == 4
        assert d1["run"]
        assert d2["run"]

        # Longer run are cached
        d1, d2 = {"run": False}, {"run": False}
        assert f(2, d1, delay=0.2) == 4
        assert f(2, d2, delay=0.2) == 4
        assert d1["run"]
        assert not d2["run"]

    def test_memory_expires_after(self, memory):
        "Test expiry of old cached results"

        f = memory.cache(
            self.foo, cache_validation_callback=expires_after(seconds=0.3), ignore=["d"]
        )

        d1, d2, d3 = {"run": False}, {"run": False}, {"run": False}
        assert f(2, d1) == 4
        assert f(2, d2) == 4
        time.sleep(0.5)
        assert f(2, d3) == 4

        assert d1["run"]
        assert not d2["run"]
        assert d3["run"]


class TestMemorizedFunc:
    "Tests for the MemorizedFunc and NotMemorizedFunc classes"

    @staticmethod
    def f(x, counter):
        counter[x] = counter.get(x, 0) + 1
        return counter[x]

    def test_call_method_memorized(self, memory):
        "Test calling the function"

        f = memory.cache(self.f, ignore=["counter"])

        counter = {}
        assert f(2, counter) == 1
        assert f(2, counter) == 1

        x, meta = f.call(2, counter)
        assert x == 2, "f has not been called properly"
        assert isinstance(meta, dict), (
            "Metadata are not returned by MemorizedFunc.call."
        )

    def test_call_method_not_memorized(self, memory):
        "Test calling the function"

        f = NotMemorizedFunc(self.f)

        counter = {}
        assert f(2, counter) == 1
        assert f(2, counter) == 2

        x, meta = f.call(2, counter)
        assert x == 3, "f has not been called properly"
        assert isinstance(meta, dict), (
            "Metadata are not returned by MemorizedFunc.call."
        )


@with_numpy
@parametrize(
    "location",
    [
        "test_cache_dir",
        pathlib.Path("test_cache_dir"),
        pathlib.Path("test_cache_dir").resolve(),
    ],
)
def test_memory_creates_gitignore(location):
    """Test that using the memory object automatically creates a `.gitignore` file
    within the new cache directory."""

    mem = Memory(location)
    arr = np.asarray([[1, 2, 3], [4, 5, 6]])
    costly_operation = mem.cache(np.square)
    costly_operation(arr)

    location = pathlib.Path(location)

    try:
        path_to_gitignore_file = os.path.join(location, ".gitignore")
        gitignore_file_content = "# Created by joblib automatically.\n*\n"
        with open(path_to_gitignore_file) as f:
            assert gitignore_file_content == f.read()

    finally:  # remove cache folder after test
        shutil.rmtree(location, ignore_errors=True)