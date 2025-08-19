
# === NexusCore/tools\exports\export_20250803_114325\combined_150.py ===

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\basic.py ===
"""
    pygments.lexers.basic
    ~~~~~~~~~~~~~~~~~~~~~

    Lexers for BASIC like languages (other than VB.net).

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups, default, words, include
from pygments.token import Comment, Error, Keyword, Name, Number, \
    Punctuation, Operator, String, Text, Whitespace
from pygments.lexers import _vbscript_builtins


__all__ = ['BlitzBasicLexer', 'BlitzMaxLexer', 'MonkeyLexer', 'CbmBasicV2Lexer',
           'QBasicLexer', 'VBScriptLexer', 'BBCBasicLexer']


class BlitzMaxLexer(RegexLexer):
    """
    For BlitzMax source code.
    """

    name = 'BlitzMax'
    url = 'http://blitzbasic.com'
    aliases = ['blitzmax', 'bmax']
    filenames = ['*.bmx']
    mimetypes = ['text/x-bmx']
    version_added = '1.4'

    bmax_vopwords = r'\b(Shl|Shr|Sar|Mod)\b'
    bmax_sktypes = r'@{1,2}|[!#$%]'
    bmax_lktypes = r'\b(Int|Byte|Short|Float|Double|Long)\b'
    bmax_name = r'[a-z_]\w*'
    bmax_var = (rf'({bmax_name})(?:(?:([ \t]*)({bmax_sktypes})|([ \t]*:[ \t]*\b(?:Shl|Shr|Sar|Mod)\b)'
                rf'|([ \t]*)(:)([ \t]*)(?:{bmax_lktypes}|({bmax_name})))(?:([ \t]*)(Ptr))?)')
    bmax_func = bmax_var + r'?((?:[ \t]|\.\.\n)*)([(])'

    flags = re.MULTILINE | re.IGNORECASE
    tokens = {
        'root': [
            # Text
            (r'\s+', Whitespace),
            (r'(\.\.)(\n)', bygroups(Text, Whitespace)),  # Line continuation
            # Comments
            (r"'.*?\n", Comment.Single),
            (r'([ \t]*)\bRem\n(\n|.)*?\s*\bEnd([ \t]*)Rem', Comment.Multiline),
            # Data types
            ('"', String.Double, 'string'),
            # Numbers
            (r'[0-9]+\.[0-9]*(?!\.)', Number.Float),
            (r'\.[0-9]*(?!\.)', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r'\$[0-9a-f]+', Number.Hex),
            (r'\%[10]+', Number.Bin),
            # Other
            (rf'(?:(?:(:)?([ \t]*)(:?{bmax_vopwords}|([+\-*/&|~]))|Or|And|Not|[=<>^]))', Operator),
            (r'[(),.:\[\]]', Punctuation),
            (r'(?:#[\w \t]*)', Name.Label),
            (r'(?:\?[\w \t]*)', Comment.Preproc),
            # Identifiers
            (rf'\b(New)\b([ \t]?)([(]?)({bmax_name})',
             bygroups(Keyword.Reserved, Whitespace, Punctuation, Name.Class)),
            (rf'\b(Import|Framework|Module)([ \t]+)({bmax_name}\.{bmax_name})',
             bygroups(Keyword.Reserved, Whitespace, Keyword.Namespace)),
            (bmax_func, bygroups(Name.Function, Whitespace, Keyword.Type,
                                 Operator, Whitespace, Punctuation, Whitespace,
                                 Keyword.Type, Name.Class, Whitespace,
                                 Keyword.Type, Whitespace, Punctuation)),
            (bmax_var, bygroups(Name.Variable, Whitespace, Keyword.Type, Operator,
                                Whitespace, Punctuation, Whitespace, Keyword.Type,
                                Name.Class, Whitespace, Keyword.Type)),
            (rf'\b(Type|Extends)([ \t]+)({bmax_name})',
             bygroups(Keyword.Reserved, Whitespace, Name.Class)),
            # Keywords
            (r'\b(Ptr)\b', Keyword.Type),
            (r'\b(Pi|True|False|Null|Self|Super)\b', Keyword.Constant),
            (r'\b(Local|Global|Const|Field)\b', Keyword.Declaration),
            (words((
                'TNullMethodException', 'TNullFunctionException',
                'TNullObjectException', 'TArrayBoundsException',
                'TRuntimeException'), prefix=r'\b', suffix=r'\b'), Name.Exception),
            (words((
                'Strict', 'SuperStrict', 'Module', 'ModuleInfo',
                'End', 'Return', 'Continue', 'Exit', 'Public', 'Private',
                'Var', 'VarPtr', 'Chr', 'Len', 'Asc', 'SizeOf', 'Sgn', 'Abs', 'Min', 'Max',
                'New', 'Release', 'Delete', 'Incbin', 'IncbinPtr', 'IncbinLen',
                'Framework', 'Include', 'Import', 'Extern', 'EndExtern',
                'Function', 'EndFunction', 'Type', 'EndType', 'Extends', 'Method', 'EndMethod',
                'Abstract', 'Final', 'If', 'Then', 'Else', 'ElseIf', 'EndIf',
                'For', 'To', 'Next', 'Step', 'EachIn', 'While', 'Wend', 'EndWhile',
                'Repeat', 'Until', 'Forever', 'Select', 'Case', 'Default', 'EndSelect',
                'Try', 'Catch', 'EndTry', 'Throw', 'Assert', 'Goto', 'DefData', 'ReadData',
                'RestoreData'), prefix=r'\b', suffix=r'\b'),
             Keyword.Reserved),
            # Final resolve (for variable names and such)
            (rf'({bmax_name})', Name.Variable),
        ],
        'string': [
            (r'""', String.Double),
            (r'"C?', String.Double, '#pop'),
            (r'[^"]+', String.Double),
        ],
    }


class BlitzBasicLexer(RegexLexer):
    """
    For BlitzBasic source code.
    """

    name = 'BlitzBasic'
    url = 'http://blitzbasic.com'
    aliases = ['blitzbasic', 'b3d', 'bplus']
    filenames = ['*.bb', '*.decls']
    mimetypes = ['text/x-bb']
    version_added = '2.0'

    bb_sktypes = r'@{1,2}|[#$%]'
    bb_name = r'[a-z]\w*'
    bb_var = (rf'({bb_name})(?:([ \t]*)({bb_sktypes})|([ \t]*)([.])([ \t]*)(?:({bb_name})))?')

    flags = re.MULTILINE | re.IGNORECASE
    tokens = {
        'root': [
            # Text
            (r'\s+', Whitespace),
            # Comments
            (r";.*?\n", Comment.Single),
            # Data types
            ('"', String.Double, 'string'),
            # Numbers
            (r'[0-9]+\.[0-9]*(?!\.)', Number.Float),
            (r'\.[0-9]+(?!\.)', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r'\$[0-9a-f]+', Number.Hex),
            (r'\%[10]+', Number.Bin),
            # Other
            (words(('Shl', 'Shr', 'Sar', 'Mod', 'Or', 'And', 'Not',
                    'Abs', 'Sgn', 'Handle', 'Int', 'Float', 'Str',
                    'First', 'Last', 'Before', 'After'),
                   prefix=r'\b', suffix=r'\b'),
             Operator),
            (r'([+\-*/~=<>^])', Operator),
            (r'[(),:\[\]\\]', Punctuation),
            (rf'\.([ \t]*)({bb_name})', Name.Label),
            # Identifiers
            (rf'\b(New)\b([ \t]+)({bb_name})',
             bygroups(Keyword.Reserved, Whitespace, Name.Class)),
            (rf'\b(Gosub|Goto)\b([ \t]+)({bb_name})',
             bygroups(Keyword.Reserved, Whitespace, Name.Label)),
            (rf'\b(Object)\b([ \t]*)([.])([ \t]*)({bb_name})\b',
             bygroups(Operator, Whitespace, Punctuation, Whitespace, Name.Class)),
            (rf'\b{bb_var}\b([ \t]*)(\()',
             bygroups(Name.Function, Whitespace, Keyword.Type, Whitespace, Punctuation,
                      Whitespace, Name.Class, Whitespace, Punctuation)),
            (rf'\b(Function)\b([ \t]+){bb_var}',
             bygroups(Keyword.Reserved, Whitespace, Name.Function, Whitespace, Keyword.Type,
                      Whitespace, Punctuation, Whitespace, Name.Class)),
            (rf'\b(Type)([ \t]+)({bb_name})',
             bygroups(Keyword.Reserved, Whitespace, Name.Class)),
            # Keywords
            (r'\b(Pi|True|False|Null)\b', Keyword.Constant),
            (r'\b(Local|Global|Const|Field|Dim)\b', Keyword.Declaration),
            (words((
                'End', 'Return', 'Exit', 'Chr', 'Len', 'Asc', 'New', 'Delete', 'Insert',
                'Include', 'Function', 'Type', 'If', 'Then', 'Else', 'ElseIf', 'EndIf',
                'For', 'To', 'Next', 'Step', 'Each', 'While', 'Wend',
                'Repeat', 'Until', 'Forever', 'Select', 'Case', 'Default',
                'Goto', 'Gosub', 'Data', 'Read', 'Restore'), prefix=r'\b', suffix=r'\b'),
             Keyword.Reserved),
            # Final resolve (for variable names and such)
            # (r'(%s)' % (bb_name), Name.Variable),
            (bb_var, bygroups(Name.Variable, Whitespace, Keyword.Type,
                              Whitespace, Punctuation, Whitespace, Name.Class)),
        ],
        'string': [
            (r'""', String.Double),
            (r'"C?', String.Double, '#pop'),
            (r'[^"\n]+', String.Double),
        ],
    }


class MonkeyLexer(RegexLexer):
    """
    For Monkey source code.
    """

    name = 'Monkey'
    aliases = ['monkey']
    filenames = ['*.monkey']
    mimetypes = ['text/x-monkey']
    url = 'https://blitzresearch.itch.io/monkeyx'
    version_added = '1.6'

    name_variable = r'[a-z_]\w*'
    name_function = r'[A-Z]\w*'
    name_constant = r'[A-Z_][A-Z0-9_]*'
    name_class = r'[A-Z]\w*'
    name_module = r'[a-z0-9_]*'

    keyword_type = r'(?:Int|Float|String|Bool|Object|Array|Void)'
    # ? == Bool // % == Int // # == Float // $ == String
    keyword_type_special = r'[?%#$]'

    flags = re.MULTILINE

    tokens = {
        'root': [
            # Text
            (r'\s+', Whitespace),
            # Comments
            (r"'.*", Comment),
            (r'(?i)^#rem\b', Comment.Multiline, 'comment'),
            # preprocessor directives
            (r'(?i)^(?:#If|#ElseIf|#Else|#EndIf|#End|#Print|#Error)\b', Comment.Preproc),
            # preprocessor variable (any line starting with '#' that is not a directive)
            (r'^#', Comment.Preproc, 'variables'),
            # String
            ('"', String.Double, 'string'),
            # Numbers
            (r'[0-9]+\.[0-9]*(?!\.)', Number.Float),
            (r'\.[0-9]+(?!\.)', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r'\$[0-9a-fA-Z]+', Number.Hex),
            (r'\%[10]+', Number.Bin),
            # Native data types
            (rf'\b{keyword_type}\b', Keyword.Type),
            # Exception handling
            (r'(?i)\b(?:Try|Catch|Throw)\b', Keyword.Reserved),
            (r'Throwable', Name.Exception),
            # Builtins
            (r'(?i)\b(?:Null|True|False)\b', Name.Builtin),
            (r'(?i)\b(?:Self|Super)\b', Name.Builtin.Pseudo),
            (r'\b(?:HOST|LANG|TARGET|CONFIG)\b', Name.Constant),
            # Keywords
            (r'(?i)^(Import)(\s+)(.*)(\n)',
             bygroups(Keyword.Namespace, Whitespace, Name.Namespace, Whitespace)),
            (r'(?i)^Strict\b.*\n', Keyword.Reserved),
            (r'(?i)(Const|Local|Global|Field)(\s+)',
             bygroups(Keyword.Declaration, Whitespace), 'variables'),
            (r'(?i)(New|Class|Interface|Extends|Implements)(\s+)',
             bygroups(Keyword.Reserved, Whitespace), 'classname'),
            (r'(?i)(Function|Method)(\s+)',
             bygroups(Keyword.Reserved, Whitespace), 'funcname'),
            (r'(?i)(?:End|Return|Public|Private|Extern|Property|'
             r'Final|Abstract)\b', Keyword.Reserved),
            # Flow Control stuff
            (r'(?i)(?:If|Then|Else|ElseIf|EndIf|'
             r'Select|Case|Default|'
             r'While|Wend|'
             r'Repeat|Until|Forever|'
             r'For|To|Until|Step|EachIn|Next|'
             r'Exit|Continue)(?=\s)', Keyword.Reserved),
            # not used yet
            (r'(?i)\b(?:Module|Inline)\b', Keyword.Reserved),
            # Array
            (r'[\[\]]', Punctuation),
            # Other
            (r'<=|>=|<>|\*=|/=|\+=|-=|&=|~=|\|=|[-&*/^+=<>|~]', Operator),
            (r'(?i)(?:Not|Mod|Shl|Shr|And|Or)', Operator.Word),
            (r'[(){}!#,.:]', Punctuation),
            # catch the rest
            (rf'{name_constant}\b', Name.Constant),
            (rf'{name_function}\b', Name.Function),
            (rf'{name_variable}\b', Name.Variable),
        ],
        'funcname': [
            (rf'(?i){name_function}\b', Name.Function),
            (r':', Punctuation, 'classname'),
            (r'\s+', Whitespace),
            (r'\(', Punctuation, 'variables'),
            (r'\)', Punctuation, '#pop')
        ],
        'classname': [
            (rf'{name_module}\.', Name.Namespace),
            (rf'{keyword_type}\b', Keyword.Type),
            (rf'{name_class}\b', Name.Class),
            # array (of given size)
            (r'(\[)(\s*)(\d*)(\s*)(\])',
             bygroups(Punctuation, Whitespace, Number.Integer, Whitespace, Punctuation)),
            # generics
            (r'\s+(?!<)', Whitespace, '#pop'),
            (r'<', Punctuation, '#push'),
            (r'>', Punctuation, '#pop'),
            (r'\n', Whitespace, '#pop'),
            default('#pop')
        ],
        'variables': [
            (rf'{name_constant}\b', Name.Constant),
            (rf'{name_variable}\b', Name.Variable),
            (rf'{keyword_type_special}', Keyword.Type),
            (r'\s+', Whitespace),
            (r':', Punctuation, 'classname'),
            (r',', Punctuation, '#push'),
            default('#pop')
        ],
        'string': [
            (r'[^"~]+', String.Double),
            (r'~q|~n|~r|~t|~z|~~', String.Escape),
            (r'"', String.Double, '#pop'),
        ],
        'comment': [
            (r'(?i)^#rem.*?', Comment.Multiline, "#push"),
            (r'(?i)^#end.*?', Comment.Multiline, "#pop"),
            (r'\n', Comment.Multiline),
            (r'.+', Comment.Multiline),
        ],
    }


class CbmBasicV2Lexer(RegexLexer):
    """
    For CBM BASIC V2 sources.
    """
    name = 'CBM BASIC V2'
    aliases = ['cbmbas']
    filenames = ['*.bas']
    url = 'https://en.wikipedia.org/wiki/Commodore_BASIC'
    version_added = '1.6'

    flags = re.IGNORECASE

    tokens = {
        'root': [
            (r'rem.*\n', Comment.Single),
            (r'\s+', Whitespace),
            (r'new|run|end|for|to|next|step|go(to|sub)?|on|return|stop|cont'
             r'|if|then|input#?|read|wait|load|save|verify|poke|sys|print#?'
             r'|list|clr|cmd|open|close|get#?', Keyword.Reserved),
            (r'data|restore|dim|let|def|fn', Keyword.Declaration),
            (r'tab|spc|sgn|int|abs|usr|fre|pos|sqr|rnd|log|exp|cos|sin|tan|atn'
             r'|peek|len|val|asc|(str|chr|left|right|mid)\$', Name.Builtin),
            (r'[-+*/^<>=]', Operator),
            (r'not|and|or', Operator.Word),
            (r'"[^"\n]*.', String),
            (r'\d+|[-+]?\d*\.\d*(e[-+]?\d+)?', Number.Float),
            (r'[(),:;]', Punctuation),
            (r'\w+[$%]?', Name),
        ]
    }

    def analyse_text(text):
        # if it starts with a line number, it shouldn't be a "modern" Basic
        # like VB.net
        if re.match(r'^\d+', text):
            return 0.2


class QBasicLexer(RegexLexer):
    """
    For QBasic source code.
    """

    name = 'QBasic'
    aliases = ['qbasic', 'basic']
    filenames = ['*.BAS', '*.bas']
    mimetypes = ['text/basic']
    url = 'https://en.wikipedia.org/wiki/QBasic'
    version_added = '2.0'

    declarations = ('DATA', 'LET')

    functions = (
        'ABS', 'ASC', 'ATN', 'CDBL', 'CHR$', 'CINT', 'CLNG',
        'COMMAND$', 'COS', 'CSNG', 'CSRLIN', 'CVD', 'CVDMBF', 'CVI',
        'CVL', 'CVS', 'CVSMBF', 'DATE$', 'ENVIRON$', 'EOF', 'ERDEV',
        'ERDEV$', 'ERL', 'ERR', 'EXP', 'FILEATTR', 'FIX', 'FRE',
        'FREEFILE', 'HEX$', 'INKEY$', 'INP', 'INPUT$', 'INSTR', 'INT',
        'IOCTL$', 'LBOUND', 'LCASE$', 'LEFT$', 'LEN', 'LOC', 'LOF',
        'LOG', 'LPOS', 'LTRIM$', 'MID$', 'MKD$', 'MKDMBF$', 'MKI$',
        'MKL$', 'MKS$', 'MKSMBF$', 'OCT$', 'PEEK', 'PEN', 'PLAY',
        'PMAP', 'POINT', 'POS', 'RIGHT$', 'RND', 'RTRIM$', 'SADD',
        'SCREEN', 'SEEK', 'SETMEM', 'SGN', 'SIN', 'SPACE$', 'SPC',
        'SQR', 'STICK', 'STR$', 'STRIG', 'STRING$', 'TAB', 'TAN',
        'TIME$', 'TIMER', 'UBOUND', 'UCASE$', 'VAL', 'VARPTR',
        'VARPTR$', 'VARSEG'
    )

    metacommands = ('$DYNAMIC', '$INCLUDE', '$STATIC')

    operators = ('AND', 'EQV', 'IMP', 'NOT', 'OR', 'XOR')

    statements = (
        'BEEP', 'BLOAD', 'BSAVE', 'CALL', 'CALL ABSOLUTE',
        'CALL INTERRUPT', 'CALLS', 'CHAIN', 'CHDIR', 'CIRCLE', 'CLEAR',
        'CLOSE', 'CLS', 'COLOR', 'COM', 'COMMON', 'CONST', 'DATA',
        'DATE$', 'DECLARE', 'DEF FN', 'DEF SEG', 'DEFDBL', 'DEFINT',
        'DEFLNG', 'DEFSNG', 'DEFSTR', 'DEF', 'DIM', 'DO', 'LOOP',
        'DRAW', 'END', 'ENVIRON', 'ERASE', 'ERROR', 'EXIT', 'FIELD',
        'FILES', 'FOR', 'NEXT', 'FUNCTION', 'GET', 'GOSUB', 'GOTO',
        'IF', 'THEN', 'INPUT', 'INPUT #', 'IOCTL', 'KEY', 'KEY',
        'KILL', 'LET', 'LINE', 'LINE INPUT', 'LINE INPUT #', 'LOCATE',
        'LOCK', 'UNLOCK', 'LPRINT', 'LSET', 'MID$', 'MKDIR', 'NAME',
        'ON COM', 'ON ERROR', 'ON KEY', 'ON PEN', 'ON PLAY',
        'ON STRIG', 'ON TIMER', 'ON UEVENT', 'ON', 'OPEN', 'OPEN COM',
        'OPTION BASE', 'OUT', 'PAINT', 'PALETTE', 'PCOPY', 'PEN',
        'PLAY', 'POKE', 'PRESET', 'PRINT', 'PRINT #', 'PRINT USING',
        'PSET', 'PUT', 'PUT', 'RANDOMIZE', 'READ', 'REDIM', 'REM',
        'RESET', 'RESTORE', 'RESUME', 'RETURN', 'RMDIR', 'RSET', 'RUN',
        'SCREEN', 'SEEK', 'SELECT CASE', 'SHARED', 'SHELL', 'SLEEP',
        'SOUND', 'STATIC', 'STOP', 'STRIG', 'SUB', 'SWAP', 'SYSTEM',
        'TIME$', 'TIMER', 'TROFF', 'TRON', 'TYPE', 'UEVENT', 'UNLOCK',
        'VIEW', 'WAIT', 'WHILE', 'WEND', 'WIDTH', 'WINDOW', 'WRITE'
    )

    keywords = (
        'ACCESS', 'ALIAS', 'ANY', 'APPEND', 'AS', 'BASE', 'BINARY',
        'BYVAL', 'CASE', 'CDECL', 'DOUBLE', 'ELSE', 'ELSEIF', 'ENDIF',
        'INTEGER', 'IS', 'LIST', 'LOCAL', 'LONG', 'LOOP', 'MOD',
        'NEXT', 'OFF', 'ON', 'OUTPUT', 'RANDOM', 'SIGNAL', 'SINGLE',
        'STEP', 'STRING', 'THEN', 'TO', 'UNTIL', 'USING', 'WEND'
    )

    tokens = {
        'root': [
            (r'\n+', Text),
            (r'\s+', Text.Whitespace),
            (r'^(\s*)(\d*)(\s*)(REM .*)$',
             bygroups(Text.Whitespace, Name.Label, Text.Whitespace,
                      Comment.Single)),
            (r'^(\s*)(\d+)(\s*)',
             bygroups(Text.Whitespace, Name.Label, Text.Whitespace)),
            (r'(?=[\s]*)(\w+)(?=[\s]*=)', Name.Variable.Global),
            (r'(?=[^"]*)\'.*$', Comment.Single),
            (r'"[^\n"]*"', String.Double),
            (r'(END)(\s+)(FUNCTION|IF|SELECT|SUB)',
             bygroups(Keyword.Reserved, Text.Whitespace, Keyword.Reserved)),
            (r'(DECLARE)(\s+)([A-Z]+)(\s+)(\S+)',
             bygroups(Keyword.Declaration, Text.Whitespace, Name.Variable,
                      Text.Whitespace, Name)),
            (r'(DIM)(\s+)(SHARED)(\s+)([^\s(]+)',
             bygroups(Keyword.Declaration, Text.Whitespace, Name.Variable,
                      Text.Whitespace, Name.Variable.Global)),
            (r'(DIM)(\s+)([^\s(]+)',
             bygroups(Keyword.Declaration, Text.Whitespace, Name.Variable.Global)),
            (r'^(\s*)([a-zA-Z_]+)(\s*)(\=)',
             bygroups(Text.Whitespace, Name.Variable.Global, Text.Whitespace,
                      Operator)),
            (r'(GOTO|GOSUB)(\s+)(\w+\:?)',
             bygroups(Keyword.Reserved, Text.Whitespace, Name.Label)),
            (r'(SUB)(\s+)(\w+\:?)',
             bygroups(Keyword.Reserved, Text.Whitespace, Name.Label)),
            include('declarations'),
            include('functions'),
            include('metacommands'),
            include('operators'),
            include('statements'),
            include('keywords'),
            (r'[a-zA-Z_]\w*[$@#&!]', Name.Variable.Global),
            (r'[a-zA-Z_]\w*\:', Name.Label),
            (r'\-?\d*\.\d+[@|#]?', Number.Float),
            (r'\-?\d+[@|#]', Number.Float),
            (r'\-?\d+#?', Number.Integer.Long),
            (r'\-?\d+#?', Number.Integer),
            (r'!=|==|:=|\.=|<<|>>|[-~+/\\*%=<>&^|?:!.]', Operator),
            (r'[\[\]{}(),;]', Punctuation),
            (r'[\w]+', Name.Variable.Global),
        ],
        # can't use regular \b because of X$()
        # XXX: use words() here
        'declarations': [
            (r'\b({})(?=\(|\b)'.format('|'.join(map(re.escape, declarations))),
             Keyword.Declaration),
        ],
        'functions': [
            (r'\b({})(?=\(|\b)'.format('|'.join(map(re.escape, functions))),
             Keyword.Reserved),
        ],
        'metacommands': [
            (r'\b({})(?=\(|\b)'.format('|'.join(map(re.escape, metacommands))),
             Keyword.Constant),
        ],
        'operators': [
            (r'\b({})(?=\(|\b)'.format('|'.join(map(re.escape, operators))), Operator.Word),
        ],
        'statements': [
            (r'\b({})\b'.format('|'.join(map(re.escape, statements))),
             Keyword.Reserved),
        ],
        'keywords': [
            (r'\b({})\b'.format('|'.join(keywords)), Keyword),
        ],
    }

    def analyse_text(text):
        if '$DYNAMIC' in text or '$STATIC' in text:
            return 0.9


class VBScriptLexer(RegexLexer):
    """
    VBScript is scripting language that is modeled on Visual Basic.
    """
    name = 'VBScript'
    aliases = ['vbscript']
    filenames = ['*.vbs', '*.VBS']
    url = 'https://learn.microsoft.com/en-us/previous-versions/t0aew7h6(v=vs.85)'
    version_added = '2.4'

    flags = re.IGNORECASE

    tokens = {
        'root': [
            (r"'[^\n]*", Comment.Single),
            (r'\s+', Whitespace),
            ('"', String.Double, 'string'),
            ('&h[0-9a-f]+', Number.Hex),
            # Float variant 1, for example: 1., 1.e2, 1.2e3
            (r'[0-9]+\.[0-9]*(e[+-]?[0-9]+)?', Number.Float),
            (r'\.[0-9]+(e[+-]?[0-9]+)?', Number.Float),  # Float variant 2, for example: .1, .1e2
            (r'[0-9]+e[+-]?[0-9]+', Number.Float),  # Float variant 3, for example: 123e45
            (r'[0-9]+', Number.Integer),
            ('#.+#', String),  # date or time value
            (r'(dim)(\s+)([a-z_][a-z0-9_]*)',
             bygroups(Keyword.Declaration, Whitespace, Name.Variable), 'dim_more'),
            (r'(function|sub)(\s+)([a-z_][a-z0-9_]*)',
             bygroups(Keyword.Declaration, Whitespace, Name.Function)),
            (r'(class)(\s+)([a-z_][a-z0-9_]*)',
             bygroups(Keyword.Declaration, Whitespace, Name.Class)),
            (r'(const)(\s+)([a-z_][a-z0-9_]*)',
             bygroups(Keyword.Declaration, Whitespace, Name.Constant)),
            (r'(end)(\s+)(class|function|if|property|sub|with)',
             bygroups(Keyword, Whitespace, Keyword)),
            (r'(on)(\s+)(error)(\s+)(goto)(\s+)(0)',
             bygroups(Keyword, Whitespace, Keyword, Whitespace, Keyword, Whitespace, Number.Integer)),
            (r'(on)(\s+)(error)(\s+)(resume)(\s+)(next)',
             bygroups(Keyword, Whitespace, Keyword, Whitespace, Keyword, Whitespace, Keyword)),
            (r'(option)(\s+)(explicit)', bygroups(Keyword, Whitespace, Keyword)),
            (r'(property)(\s+)(get|let|set)(\s+)([a-z_][a-z0-9_]*)',
             bygroups(Keyword.Declaration, Whitespace, Keyword.Declaration, Whitespace, Name.Property)),
            (r'rem\s.*[^\n]*', Comment.Single),
            (words(_vbscript_builtins.KEYWORDS, suffix=r'\b'), Keyword),
            (words(_vbscript_builtins.OPERATORS), Operator),
            (words(_vbscript_builtins.OPERATOR_WORDS, suffix=r'\b'), Operator.Word),
            (words(_vbscript_builtins.BUILTIN_CONSTANTS, suffix=r'\b'), Name.Constant),
            (words(_vbscript_builtins.BUILTIN_FUNCTIONS, suffix=r'\b'), Name.Builtin),
            (words(_vbscript_builtins.BUILTIN_VARIABLES, suffix=r'\b'), Name.Builtin),
            (r'[a-z_][a-z0-9_]*', Name),
            (r'\b_\n', Operator),
            (words(r'(),.:'), Punctuation),
            (r'.+(\n)?', Error)
        ],
        'dim_more': [
            (r'(\s*)(,)(\s*)([a-z_][a-z0-9]*)',
             bygroups(Whitespace, Punctuation, Whitespace, Name.Variable)),
            default('#pop'),
        ],
        'string': [
            (r'[^"\n]+', String.Double),
            (r'\"\"', String.Double),
            (r'"', String.Double, '#pop'),
            (r'\n', Error, '#pop'),  # Unterminated string
        ],
    }


class BBCBasicLexer(RegexLexer):
    """
    BBC Basic was supplied on the BBC Micro, and later Acorn RISC OS.
    It is also used by BBC Basic For Windows.
    """
    base_keywords = ['OTHERWISE', 'AND', 'DIV', 'EOR', 'MOD', 'OR', 'ERROR',
                     'LINE', 'OFF', 'STEP', 'SPC', 'TAB', 'ELSE', 'THEN',
                     'OPENIN', 'PTR', 'PAGE', 'TIME', 'LOMEM', 'HIMEM', 'ABS',
                     'ACS', 'ADVAL', 'ASC', 'ASN', 'ATN', 'BGET', 'COS', 'COUNT',
                     'DEG', 'ERL', 'ERR', 'EVAL', 'EXP', 'EXT', 'FALSE', 'FN',
                     'GET', 'INKEY', 'INSTR', 'INT', 'LEN', 'LN', 'LOG', 'NOT',
                     'OPENUP', 'OPENOUT', 'PI', 'POINT', 'POS', 'RAD', 'RND',
                     'SGN', 'SIN', 'SQR', 'TAN', 'TO', 'TRUE', 'USR', 'VAL',
                     'VPOS', 'CHR$', 'GET$', 'INKEY$', 'LEFT$', 'MID$',
                     'RIGHT$', 'STR$', 'STRING$', 'EOF', 'PTR', 'PAGE', 'TIME',
                     'LOMEM', 'HIMEM', 'SOUND', 'BPUT', 'CALL', 'CHAIN', 'CLEAR',
                     'CLOSE', 'CLG', 'CLS', 'DATA', 'DEF', 'DIM', 'DRAW', 'END',
                     'ENDPROC', 'ENVELOPE', 'FOR', 'GOSUB', 'GOTO', 'GCOL', 'IF',
                     'INPUT', 'LET', 'LOCAL', 'MODE', 'MOVE', 'NEXT', 'ON',
                     'VDU', 'PLOT', 'PRINT', 'PROC', 'READ', 'REM', 'REPEAT',
                     'REPORT', 'RESTORE', 'RETURN', 'RUN', 'STOP', 'COLOUR',
                     'TRACE', 'UNTIL', 'WIDTH', 'OSCLI']

    basic5_keywords = ['WHEN', 'OF', 'ENDCASE', 'ENDIF', 'ENDWHILE', 'CASE',
                       'CIRCLE', 'FILL', 'ORIGIN', 'POINT', 'RECTANGLE', 'SWAP',
                       'WHILE', 'WAIT', 'MOUSE', 'QUIT', 'SYS', 'INSTALL',
                       'LIBRARY', 'TINT', 'ELLIPSE', 'BEATS', 'TEMPO', 'VOICES',
                       'VOICE', 'STEREO', 'OVERLAY', 'APPEND', 'AUTO', 'CRUNCH',
                       'DELETE', 'EDIT', 'HELP', 'LIST', 'LOAD', 'LVAR', 'NEW',
                       'OLD', 'RENUMBER', 'SAVE', 'TEXTLOAD', 'TEXTSAVE',
                       'TWIN', 'TWINO', 'INSTALL', 'SUM', 'BEAT']


    name = 'BBC Basic'
    aliases = ['bbcbasic']
    filenames = ['*.bbc']
    url = 'https://www.bbcbasic.co.uk/bbcbasic.html'
    version_added = '2.4'

    tokens = {
        'root': [
            (r"[0-9]+", Name.Label),
            (r"(\*)([^\n]*)",
             bygroups(Keyword.Pseudo, Comment.Special)),
            default('code'),
        ],

        'code': [
            (r"(REM)([^\n]*)",
             bygroups(Keyword.Declaration, Comment.Single)),
            (r'\n', Whitespace, 'root'),
            (r'\s+', Whitespace),
            (r':', Comment.Preproc),

            # Some special cases to make functions come out nicer
            (r'(DEF)(\s*)(FN|PROC)([A-Za-z_@][\w@]*)',
             bygroups(Keyword.Declaration, Whitespace,
                      Keyword.Declaration, Name.Function)),
            (r'(FN|PROC)([A-Za-z_@][\w@]*)',
             bygroups(Keyword, Name.Function)),

            (r'(GOTO|GOSUB|THEN|RESTORE)(\s*)(\d+)',
             bygroups(Keyword, Whitespace, Name.Label)),

            (r'(TRUE|FALSE)', Keyword.Constant),
            (r'(PAGE|LOMEM|HIMEM|TIME|WIDTH|ERL|ERR|REPORT\$|POS|VPOS|VOICES)',
             Keyword.Pseudo),

            (words(base_keywords), Keyword),
            (words(basic5_keywords), Keyword),

            ('"', String.Double, 'string'),

            ('%[01]{1,32}', Number.Bin),
            ('&[0-9a-f]{1,8}', Number.Hex),

            (r'[+-]?[0-9]+\.[0-9]*(E[+-]?[0-9]+)?', Number.Float),
            (r'[+-]?\.[0-9]+(E[+-]?[0-9]+)?', Number.Float),
            (r'[+-]?[0-9]+E[+-]?[0-9]+', Number.Float),
            (r'[+-]?\d+', Number.Integer),

            (r'([A-Za-z_@][\w@]*[%$]?)', Name.Variable),
            (r'([+\-]=|[$!|?+\-*/%^=><();]|>=|<=|<>|<<|>>|>>>|,)', Operator),
        ],
        'string': [
            (r'[^"\n]+', String.Double),
            (r'"', String.Double, '#pop'),
            (r'\n', Error, 'root'),  # Unterminated string
        ],
    }

    def analyse_text(text):
        if text.startswith('10REM >') or text.startswith('REM >'):
            return 0.9

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_sync.py ===
from __future__ import annotations

import re
import weakref
from typing import TYPE_CHECKING, Callable, Union

import pytest

from trio.testing import Matcher, RaisesGroup

from .. import _core
from .._core._parking_lot import GLOBAL_PARKING_LOT_BREAKER
from .._sync import *
from .._timeouts import sleep_forever
from ..testing import assert_checkpoints, wait_all_tasks_blocked

if TYPE_CHECKING:
    from typing_extensions import TypeAlias


async def test_Event() -> None:
    e = Event()
    assert not e.is_set()
    assert e.statistics().tasks_waiting == 0

    e.set()
    assert e.is_set()
    with assert_checkpoints():
        await e.wait()

    e = Event()

    record = []

    async def child() -> None:
        record.append("sleeping")
        await e.wait()
        record.append("woken")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(child)
        nursery.start_soon(child)
        await wait_all_tasks_blocked()
        assert record == ["sleeping", "sleeping"]
        assert e.statistics().tasks_waiting == 2
        e.set()
        await wait_all_tasks_blocked()
        assert record == ["sleeping", "sleeping", "woken", "woken"]


async def test_CapacityLimiter() -> None:
    with pytest.raises(TypeError):
        CapacityLimiter(1.0)
    with pytest.raises(ValueError, match=r"^total_tokens must be >= 1$"):
        CapacityLimiter(-1)
    c = CapacityLimiter(2)
    repr(c)  # smoke test
    assert c.total_tokens == 2
    assert c.borrowed_tokens == 0
    assert c.available_tokens == 2
    with pytest.raises(RuntimeError):
        c.release()
    assert c.borrowed_tokens == 0
    c.acquire_nowait()
    assert c.borrowed_tokens == 1
    assert c.available_tokens == 1

    stats = c.statistics()
    assert stats.borrowed_tokens == 1
    assert stats.total_tokens == 2
    assert stats.borrowers == [_core.current_task()]
    assert stats.tasks_waiting == 0

    # Can't re-acquire when we already have it
    with pytest.raises(RuntimeError):
        c.acquire_nowait()
    assert c.borrowed_tokens == 1
    with pytest.raises(RuntimeError):
        await c.acquire()
    assert c.borrowed_tokens == 1

    # We can acquire on behalf of someone else though
    with assert_checkpoints():
        await c.acquire_on_behalf_of("someone")

    # But then we've run out of capacity
    assert c.borrowed_tokens == 2
    with pytest.raises(_core.WouldBlock):
        c.acquire_on_behalf_of_nowait("third party")

    assert set(c.statistics().borrowers) == {_core.current_task(), "someone"}

    # Until we release one
    c.release_on_behalf_of(_core.current_task())
    assert c.statistics().borrowers == ["someone"]

    c.release_on_behalf_of("someone")
    assert c.borrowed_tokens == 0
    with assert_checkpoints():
        async with c:
            assert c.borrowed_tokens == 1

    async with _core.open_nursery() as nursery:
        await c.acquire_on_behalf_of("value 1")
        await c.acquire_on_behalf_of("value 2")
        nursery.start_soon(c.acquire_on_behalf_of, "value 3")
        await wait_all_tasks_blocked()
        assert c.borrowed_tokens == 2
        assert c.statistics().tasks_waiting == 1
        c.release_on_behalf_of("value 2")
        # Fairness:
        assert c.borrowed_tokens == 2
        with pytest.raises(_core.WouldBlock):
            c.acquire_nowait()

    c.release_on_behalf_of("value 3")
    c.release_on_behalf_of("value 1")


async def test_CapacityLimiter_inf() -> None:
    from math import inf

    c = CapacityLimiter(inf)
    repr(c)  # smoke test
    assert c.total_tokens == inf
    assert c.borrowed_tokens == 0
    assert c.available_tokens == inf
    with pytest.raises(RuntimeError):
        c.release()
    assert c.borrowed_tokens == 0
    c.acquire_nowait()
    assert c.borrowed_tokens == 1
    assert c.available_tokens == inf


async def test_CapacityLimiter_change_total_tokens() -> None:
    c = CapacityLimiter(2)

    with pytest.raises(TypeError):
        c.total_tokens = 1.0

    with pytest.raises(ValueError, match=r"^total_tokens must be >= 1$"):
        c.total_tokens = 0

    with pytest.raises(ValueError, match=r"^total_tokens must be >= 1$"):
        c.total_tokens = -10

    assert c.total_tokens == 2

    async with _core.open_nursery() as nursery:
        for i in range(5):
            nursery.start_soon(c.acquire_on_behalf_of, i)
            await wait_all_tasks_blocked()
        assert set(c.statistics().borrowers) == {0, 1}
        assert c.statistics().tasks_waiting == 3
        c.total_tokens += 2
        assert set(c.statistics().borrowers) == {0, 1, 2, 3}
        assert c.statistics().tasks_waiting == 1
        c.total_tokens -= 3
        assert c.borrowed_tokens == 4
        assert c.total_tokens == 1
        c.release_on_behalf_of(0)
        c.release_on_behalf_of(1)
        c.release_on_behalf_of(2)
        assert set(c.statistics().borrowers) == {3}
        assert c.statistics().tasks_waiting == 1
        c.release_on_behalf_of(3)
        assert set(c.statistics().borrowers) == {4}
        assert c.statistics().tasks_waiting == 0


# regression test for issue #548
async def test_CapacityLimiter_memleak_548() -> None:
    limiter = CapacityLimiter(total_tokens=1)
    await limiter.acquire()

    async with _core.open_nursery() as n:
        n.start_soon(limiter.acquire)
        await wait_all_tasks_blocked()  # give it a chance to run the task
        n.cancel_scope.cancel()

    # if this is 1, the acquire call (despite being killed) is still there in the task, and will
    # leak memory all the while the limiter is active
    assert len(limiter._pending_borrowers) == 0


async def test_Semaphore() -> None:
    with pytest.raises(TypeError):
        Semaphore(1.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=r"^initial value must be >= 0$"):
        Semaphore(-1)
    s = Semaphore(1)
    repr(s)  # smoke test
    assert s.value == 1
    assert s.max_value is None
    s.release()
    assert s.value == 2
    assert s.statistics().tasks_waiting == 0
    s.acquire_nowait()
    assert s.value == 1
    with assert_checkpoints():
        await s.acquire()
    assert s.value == 0
    with pytest.raises(_core.WouldBlock):
        s.acquire_nowait()

    s.release()
    assert s.value == 1
    with assert_checkpoints():
        async with s:
            assert s.value == 0
    assert s.value == 1
    s.acquire_nowait()

    record = []

    async def do_acquire(s: Semaphore) -> None:
        record.append("started")
        await s.acquire()
        record.append("finished")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(do_acquire, s)
        await wait_all_tasks_blocked()
        assert record == ["started"]
        assert s.value == 0
        s.release()
        # Fairness:
        assert s.value == 0
        with pytest.raises(_core.WouldBlock):
            s.acquire_nowait()
    assert record == ["started", "finished"]


def test_Semaphore_bounded() -> None:
    with pytest.raises(TypeError):
        Semaphore(1, max_value=1.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=r"^max_values must be >= initial_value$"):
        Semaphore(2, max_value=1)
    bs = Semaphore(1, max_value=1)
    assert bs.max_value == 1
    repr(bs)  # smoke test
    with pytest.raises(ValueError, match=r"^semaphore released too many times$"):
        bs.release()
    assert bs.value == 1
    bs.acquire_nowait()
    assert bs.value == 0
    bs.release()
    assert bs.value == 1


@pytest.mark.parametrize("lockcls", [Lock, StrictFIFOLock], ids=lambda fn: fn.__name__)
async def test_Lock_and_StrictFIFOLock(
    lockcls: type[Lock | StrictFIFOLock],
) -> None:
    l = lockcls()  # noqa
    assert not l.locked()

    # make sure locks can be weakref'ed (gh-331)
    r = weakref.ref(l)
    assert r() is l

    repr(l)  # smoke test
    # make sure repr uses the right name for subclasses
    assert lockcls.__name__ in repr(l)
    with assert_checkpoints():
        async with l:
            assert l.locked()
            repr(l)  # smoke test (repr branches on locked/unlocked)
    assert not l.locked()
    l.acquire_nowait()
    assert l.locked()
    l.release()
    assert not l.locked()
    with assert_checkpoints():
        await l.acquire()
    assert l.locked()
    l.release()
    assert not l.locked()

    l.acquire_nowait()
    with pytest.raises(RuntimeError):
        # Error out if we already own the lock
        l.acquire_nowait()
    l.release()
    with pytest.raises(RuntimeError):
        # Error out if we don't own the lock
        l.release()

    holder_task = None

    async def holder() -> None:
        nonlocal holder_task
        holder_task = _core.current_task()
        async with l:
            await sleep_forever()

    async with _core.open_nursery() as nursery:
        assert not l.locked()
        nursery.start_soon(holder)
        await wait_all_tasks_blocked()
        assert l.locked()
        # WouldBlock if someone else holds the lock
        with pytest.raises(_core.WouldBlock):
            l.acquire_nowait()
        # Can't release a lock someone else holds
        with pytest.raises(RuntimeError):
            l.release()

        statistics = l.statistics()
        print(statistics)
        assert statistics.locked
        assert statistics.owner is holder_task
        assert statistics.tasks_waiting == 0

        nursery.start_soon(holder)
        await wait_all_tasks_blocked()
        statistics = l.statistics()
        print(statistics)
        assert statistics.tasks_waiting == 1

        nursery.cancel_scope.cancel()

    statistics = l.statistics()
    assert not statistics.locked
    assert statistics.owner is None
    assert statistics.tasks_waiting == 0


async def test_Condition() -> None:
    with pytest.raises(TypeError):
        Condition(Semaphore(1))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Condition(StrictFIFOLock)  # type: ignore[arg-type]
    l = Lock()  # noqa
    c = Condition(l)
    assert not l.locked()
    assert not c.locked()
    with assert_checkpoints():
        await c.acquire()
    assert l.locked()
    assert c.locked()

    c = Condition()
    assert not c.locked()
    c.acquire_nowait()
    assert c.locked()
    with pytest.raises(RuntimeError):
        c.acquire_nowait()
    c.release()

    with pytest.raises(RuntimeError):
        # Can't wait without holding the lock
        await c.wait()
    with pytest.raises(RuntimeError):
        # Can't notify without holding the lock
        c.notify()
    with pytest.raises(RuntimeError):
        # Can't notify without holding the lock
        c.notify_all()

    finished_waiters = set()

    async def waiter(i: int) -> None:
        async with c:
            await c.wait()
        finished_waiters.add(i)

    async with _core.open_nursery() as nursery:
        for i in range(3):
            nursery.start_soon(waiter, i)
            await wait_all_tasks_blocked()
        async with c:
            c.notify()
        assert c.locked()
        await wait_all_tasks_blocked()
        assert finished_waiters == {0}
        async with c:
            c.notify_all()
        await wait_all_tasks_blocked()
        assert finished_waiters == {0, 1, 2}

    finished_waiters = set()
    async with _core.open_nursery() as nursery:
        for i in range(3):
            nursery.start_soon(waiter, i)
            await wait_all_tasks_blocked()
        async with c:
            c.notify(2)
            statistics = c.statistics()
            print(statistics)
            assert statistics.tasks_waiting == 1
            assert statistics.lock_statistics.tasks_waiting == 2
        # exiting the context manager hands off the lock to the first task
        assert c.statistics().lock_statistics.tasks_waiting == 1

        await wait_all_tasks_blocked()
        assert finished_waiters == {0, 1}

        async with c:
            c.notify_all()

    # After being cancelled still hold the lock (!)
    # (Note that c.__aexit__ checks that we hold the lock as well)
    with _core.CancelScope() as scope:
        async with c:
            scope.cancel()
            try:
                await c.wait()
            finally:
                assert c.locked()


from .._channel import open_memory_channel
from .._sync import AsyncContextManagerMixin

# Three ways of implementing a Lock in terms of a channel. Used to let us put
# the channel through the generic lock tests.


class ChannelLock1(AsyncContextManagerMixin):
    def __init__(self, capacity: int) -> None:
        self.s, self.r = open_memory_channel[None](capacity)
        for _ in range(capacity - 1):
            self.s.send_nowait(None)

    def acquire_nowait(self) -> None:
        self.s.send_nowait(None)

    async def acquire(self) -> None:
        await self.s.send(None)

    def release(self) -> None:
        self.r.receive_nowait()


class ChannelLock2(AsyncContextManagerMixin):
    def __init__(self) -> None:
        self.s, self.r = open_memory_channel[None](10)
        self.s.send_nowait(None)

    def acquire_nowait(self) -> None:
        self.r.receive_nowait()

    async def acquire(self) -> None:
        await self.r.receive()

    def release(self) -> None:
        self.s.send_nowait(None)


class ChannelLock3(AsyncContextManagerMixin):
    def __init__(self) -> None:
        self.s, self.r = open_memory_channel[None](0)
        # self.acquired is true when one task acquires the lock and
        # only becomes false when it's released and no tasks are
        # waiting to acquire.
        self.acquired = False

    def acquire_nowait(self) -> None:
        assert not self.acquired
        self.acquired = True

    async def acquire(self) -> None:
        if self.acquired:
            await self.s.send(None)
        else:
            self.acquired = True
            await _core.checkpoint()

    def release(self) -> None:
        try:
            self.r.receive_nowait()
        except _core.WouldBlock:
            assert self.acquired
            self.acquired = False


lock_factories = [
    lambda: CapacityLimiter(1),
    lambda: Semaphore(1),
    Lock,
    StrictFIFOLock,
    lambda: ChannelLock1(10),
    lambda: ChannelLock1(1),
    ChannelLock2,
    ChannelLock3,
]
lock_factory_names = [
    "CapacityLimiter(1)",
    "Semaphore(1)",
    "Lock",
    "StrictFIFOLock",
    "ChannelLock1(10)",
    "ChannelLock1(1)",
    "ChannelLock2",
    "ChannelLock3",
]

generic_lock_test = pytest.mark.parametrize(
    "lock_factory",
    lock_factories,
    ids=lock_factory_names,
)

LockLike: TypeAlias = Union[
    CapacityLimiter,
    Semaphore,
    Lock,
    StrictFIFOLock,
    ChannelLock1,
    ChannelLock2,
    ChannelLock3,
]
LockFactory: TypeAlias = Callable[[], LockLike]


# Spawn a bunch of workers that take a lock and then yield; make sure that
# only one worker is ever in the critical section at a time.
@generic_lock_test
async def test_generic_lock_exclusion(lock_factory: LockFactory) -> None:
    LOOPS = 10
    WORKERS = 5
    in_critical_section = False
    acquires = 0

    async def worker(lock_like: LockLike) -> None:
        nonlocal in_critical_section, acquires
        for _ in range(LOOPS):
            async with lock_like:
                acquires += 1
                assert not in_critical_section
                in_critical_section = True
                await _core.checkpoint()
                await _core.checkpoint()
                assert in_critical_section
                in_critical_section = False

    async with _core.open_nursery() as nursery:
        lock_like = lock_factory()
        for _ in range(WORKERS):
            nursery.start_soon(worker, lock_like)
    assert not in_critical_section
    assert acquires == LOOPS * WORKERS


# Several workers queue on the same lock; make sure they each get it, in
# order.
@generic_lock_test
async def test_generic_lock_fifo_fairness(lock_factory: LockFactory) -> None:
    initial_order = []
    record = []
    LOOPS = 5

    async def loopy(name: int, lock_like: LockLike) -> None:
        # Record the order each task was initially scheduled in
        initial_order.append(name)
        for _ in range(LOOPS):
            async with lock_like:
                record.append(name)

    lock_like = lock_factory()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(loopy, 1, lock_like)
        nursery.start_soon(loopy, 2, lock_like)
        nursery.start_soon(loopy, 3, lock_like)
    # The first three could be in any order due to scheduling randomness,
    # but after that they should repeat in the same order
    for i in range(LOOPS):
        assert record[3 * i : 3 * (i + 1)] == initial_order


@generic_lock_test
async def test_generic_lock_acquire_nowait_blocks_acquire(
    lock_factory: LockFactory,
) -> None:
    lock_like = lock_factory()

    record = []

    async def lock_taker() -> None:
        record.append("started")
        async with lock_like:
            pass
        record.append("finished")

    async with _core.open_nursery() as nursery:
        lock_like.acquire_nowait()
        nursery.start_soon(lock_taker)
        await wait_all_tasks_blocked()
        assert record == ["started"]
        lock_like.release()


async def test_lock_acquire_unowned_lock() -> None:
    """Test that trying to acquire a lock whose owner has exited raises an error.
    see https://github.com/python-trio/trio/issues/3035
    """
    assert not GLOBAL_PARKING_LOT_BREAKER
    lock = trio.Lock()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(lock.acquire)
    owner_str = re.escape(str(lock._lot.broken_by[0]))
    with pytest.raises(
        trio.BrokenResourceError,
        match=f"^Owner of this lock exited without releasing: {owner_str}$",
    ):
        await lock.acquire()
    assert not GLOBAL_PARKING_LOT_BREAKER


async def test_lock_multiple_acquire() -> None:
    """Test for error if awaiting on a lock whose owner exits without releasing.
    see https://github.com/python-trio/trio/issues/3035"""
    assert not GLOBAL_PARKING_LOT_BREAKER
    lock = trio.Lock()
    with RaisesGroup(
        Matcher(
            trio.BrokenResourceError,
            match="^Owner of this lock exited without releasing: ",
        ),
    ):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(lock.acquire)
            nursery.start_soon(lock.acquire)
    assert not GLOBAL_PARKING_LOT_BREAKER


async def test_lock_handover() -> None:
    assert not GLOBAL_PARKING_LOT_BREAKER
    child_task: Task | None = None
    lock = trio.Lock()

    # this task acquires the lock
    lock.acquire_nowait()
    assert {
        _core.current_task(): [
            lock._lot,
        ],
    } == GLOBAL_PARKING_LOT_BREAKER

    async with trio.open_nursery() as nursery:
        nursery.start_soon(lock.acquire)
        await wait_all_tasks_blocked()

        # hand over the lock to the child task
        lock.release()

        # check values, and get the identifier out of the dict for later check
        assert len(GLOBAL_PARKING_LOT_BREAKER) == 1
        child_task = next(iter(GLOBAL_PARKING_LOT_BREAKER))
        assert GLOBAL_PARKING_LOT_BREAKER[child_task] == [lock._lot]

    assert lock._lot.broken_by == [child_task]
    assert not GLOBAL_PARKING_LOT_BREAKER

# === NexusCore/openenv\Lib\site-packages\google\auth\impersonated_credentials.py ===
# Copyright 2018 Google Inc.
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

"""Google Cloud Impersonated credentials.

This module provides authentication for applications where local credentials
impersonates a remote service account using `IAM Credentials API`_.

This class can be used to impersonate a service account as long as the original
Credential object has the "Service Account Token Creator" role on the target
service account.

    .. _IAM Credentials API:
        https://cloud.google.com/iam/credentials/reference/rest/
"""

import base64
import copy
from datetime import datetime
import http.client as http_client
import json

from google.auth import _exponential_backoff
from google.auth import _helpers
from google.auth import credentials
from google.auth import exceptions
from google.auth import iam
from google.auth import jwt
from google.auth import metrics
from google.oauth2 import _client


_REFRESH_ERROR = "Unable to acquire impersonated credentials"

_DEFAULT_TOKEN_LIFETIME_SECS = 3600  # 1 hour in seconds

_GOOGLE_OAUTH2_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

_SOURCE_CREDENTIAL_AUTHORIZED_USER_TYPE = "authorized_user"
_SOURCE_CREDENTIAL_SERVICE_ACCOUNT_TYPE = "service_account"
_SOURCE_CREDENTIAL_EXTERNAL_ACCOUNT_AUTHORIZED_USER_TYPE = (
    "external_account_authorized_user"
)


def _make_iam_token_request(
    request,
    principal,
    headers,
    body,
    universe_domain=credentials.DEFAULT_UNIVERSE_DOMAIN,
    iam_endpoint_override=None,
):
    """Makes a request to the Google Cloud IAM service for an access token.
    Args:
        request (Request): The Request object to use.
        principal (str): The principal to request an access token for.
        headers (Mapping[str, str]): Map of headers to transmit.
        body (Mapping[str, str]): JSON Payload body for the iamcredentials
            API call.
        iam_endpoint_override (Optiona[str]): The full IAM endpoint override
            with the target_principal embedded. This is useful when supporting
            impersonation with regional endpoints.

    Raises:
        google.auth.exceptions.TransportError: Raised if there is an underlying
            HTTP connection error
        google.auth.exceptions.RefreshError: Raised if the impersonated
            credentials are not available.  Common reasons are
            `iamcredentials.googleapis.com` is not enabled or the
            `Service Account Token Creator` is not assigned
    """
    iam_endpoint = iam_endpoint_override or iam._IAM_ENDPOINT.replace(
        credentials.DEFAULT_UNIVERSE_DOMAIN, universe_domain
    ).format(principal)

    body = json.dumps(body).encode("utf-8")

    response = request(url=iam_endpoint, method="POST", headers=headers, body=body)

    # support both string and bytes type response.data
    response_body = (
        response.data.decode("utf-8")
        if hasattr(response.data, "decode")
        else response.data
    )

    if response.status != http_client.OK:
        raise exceptions.RefreshError(_REFRESH_ERROR, response_body)

    try:
        token_response = json.loads(response_body)
        token = token_response["accessToken"]
        expiry = datetime.strptime(token_response["expireTime"], "%Y-%m-%dT%H:%M:%SZ")

        return token, expiry

    except (KeyError, ValueError) as caught_exc:
        new_exc = exceptions.RefreshError(
            "{}: No access token or invalid expiration in response.".format(
                _REFRESH_ERROR
            ),
            response_body,
        )
        raise new_exc from caught_exc


class Credentials(
    credentials.Scoped, credentials.CredentialsWithQuotaProject, credentials.Signing
):
    """This module defines impersonated credentials which are essentially
    impersonated identities.

    Impersonated Credentials allows credentials issued to a user or
    service account to impersonate another. The target service account must
    grant the originating credential principal the
    `Service Account Token Creator`_ IAM role:

    For more information about Token Creator IAM role and
    IAMCredentials API, see
    `Creating Short-Lived Service Account Credentials`_.

    .. _Service Account Token Creator:
        https://cloud.google.com/iam/docs/service-accounts#the_service_account_token_creator_role

    .. _Creating Short-Lived Service Account Credentials:
        https://cloud.google.com/iam/docs/creating-short-lived-service-account-credentials

    Usage:

    First grant source_credentials the `Service Account Token Creator`
    role on the target account to impersonate.   In this example, the
    service account represented by svc_account.json has the
    token creator role on
    `impersonated-account@_project_.iam.gserviceaccount.com`.

    Enable the IAMCredentials API on the source project:
    `gcloud services enable iamcredentials.googleapis.com`.

    Initialize a source credential which does not have access to
    list bucket::

        from google.oauth2 import service_account

        target_scopes = [
            'https://www.googleapis.com/auth/devstorage.read_only']

        source_credentials = (
            service_account.Credentials.from_service_account_file(
                '/path/to/svc_account.json',
                scopes=target_scopes))

    Now use the source credentials to acquire credentials to impersonate
    another service account::

        from google.auth import impersonated_credentials

        target_credentials = impersonated_credentials.Credentials(
          source_credentials=source_credentials,
          target_principal='impersonated-account@_project_.iam.gserviceaccount.com',
          target_scopes = target_scopes,
          lifetime=500)

    Resource access is granted::

        client = storage.Client(credentials=target_credentials)
        buckets = client.list_buckets(project='your_project')
        for bucket in buckets:
          print(bucket.name)
    """

    def __init__(
        self,
        source_credentials,
        target_principal,
        target_scopes,
        delegates=None,
        subject=None,
        lifetime=_DEFAULT_TOKEN_LIFETIME_SECS,
        quota_project_id=None,
        iam_endpoint_override=None,
    ):
        """
        Args:
            source_credentials (google.auth.Credentials): The source credential
                used as to acquire the impersonated credentials.
            target_principal (str): The service account to impersonate.
            target_scopes (Sequence[str]): Scopes to request during the
                authorization grant.
            delegates (Sequence[str]): The chained list of delegates required
                to grant the final access_token.  If set, the sequence of
                identities must have "Service Account Token Creator" capability
                granted to the prceeding identity.  For example, if set to
                [serviceAccountB, serviceAccountC], the source_credential
                must have the Token Creator role on serviceAccountB.
                serviceAccountB must have the Token Creator on
                serviceAccountC.
                Finally, C must have Token Creator on target_principal.
                If left unset, source_credential must have that role on
                target_principal.
            lifetime (int): Number of seconds the delegated credential should
                be valid for (upto 3600).
            quota_project_id (Optional[str]): The project ID used for quota and billing.
                This project may be different from the project used to
                create the credentials.
            iam_endpoint_override (Optional[str]): The full IAM endpoint override
                with the target_principal embedded. This is useful when supporting
                impersonation with regional endpoints.
            subject (Optional[str]): sub field of a JWT. This field should only be set
                if you wish to impersonate as a user. This feature is useful when
                using domain wide delegation.
        """

        super(Credentials, self).__init__()

        self._source_credentials = copy.copy(source_credentials)
        # Service account source credentials must have the _IAM_SCOPE
        # added to refresh correctly. User credentials cannot have
        # their original scopes modified.
        if isinstance(self._source_credentials, credentials.Scoped):
            self._source_credentials = self._source_credentials.with_scopes(
                iam._IAM_SCOPE
            )
            # If the source credential is service account and self signed jwt
            # is needed, we need to create a jwt credential inside it
            if (
                hasattr(self._source_credentials, "_create_self_signed_jwt")
                and self._source_credentials._always_use_jwt_access
            ):
                self._source_credentials._create_self_signed_jwt(None)

        self._universe_domain = source_credentials.universe_domain
        self._target_principal = target_principal
        self._target_scopes = target_scopes
        self._delegates = delegates
        self._subject = subject
        self._lifetime = lifetime or _DEFAULT_TOKEN_LIFETIME_SECS
        self.token = None
        self.expiry = _helpers.utcnow()
        self._quota_project_id = quota_project_id
        self._iam_endpoint_override = iam_endpoint_override
        self._cred_file_path = None

    def _metric_header_for_usage(self):
        return metrics.CRED_TYPE_SA_IMPERSONATE

    @_helpers.copy_docstring(credentials.Credentials)
    def refresh(self, request):
        self._update_token(request)

    def _update_token(self, request):
        """Updates credentials with a new access_token representing
        the impersonated account.

        Args:
            request (google.auth.transport.requests.Request): Request object
                to use for refreshing credentials.
        """

        # Refresh our source credentials if it is not valid.
        if (
            self._source_credentials.token_state == credentials.TokenState.STALE
            or self._source_credentials.token_state == credentials.TokenState.INVALID
        ):
            self._source_credentials.refresh(request)

        body = {
            "delegates": self._delegates,
            "scope": self._target_scopes,
            "lifetime": str(self._lifetime) + "s",
        }

        headers = {
            "Content-Type": "application/json",
            metrics.API_CLIENT_HEADER: metrics.token_request_access_token_impersonate(),
        }

        # Apply the source credentials authentication info.
        self._source_credentials.apply(headers)

        #  If a subject is specified a domain-wide delegation auth-flow is initiated
        #  to impersonate as the provided subject (user).
        if self._subject:
            if self.universe_domain != credentials.DEFAULT_UNIVERSE_DOMAIN:
                raise exceptions.GoogleAuthError(
                    "Domain-wide delegation is not supported in universes other "
                    + "than googleapis.com"
                )

            now = _helpers.utcnow()
            payload = {
                "iss": self._target_principal,
                "scope": _helpers.scopes_to_string(self._target_scopes or ()),
                "sub": self._subject,
                "aud": _GOOGLE_OAUTH2_TOKEN_ENDPOINT,
                "iat": _helpers.datetime_to_secs(now),
                "exp": _helpers.datetime_to_secs(now) + _DEFAULT_TOKEN_LIFETIME_SECS,
            }

            assertion = _sign_jwt_request(
                request=request,
                principal=self._target_principal,
                headers=headers,
                payload=payload,
                delegates=self._delegates,
            )

            self.token, self.expiry, _ = _client.jwt_grant(
                request, _GOOGLE_OAUTH2_TOKEN_ENDPOINT, assertion
            )

            return

        self.token, self.expiry = _make_iam_token_request(
            request=request,
            principal=self._target_principal,
            headers=headers,
            body=body,
            universe_domain=self.universe_domain,
            iam_endpoint_override=self._iam_endpoint_override,
        )

    def sign_bytes(self, message):
        from google.auth.transport.requests import AuthorizedSession

        iam_sign_endpoint = iam._IAM_SIGN_ENDPOINT.replace(
            credentials.DEFAULT_UNIVERSE_DOMAIN, self.universe_domain
        ).format(self._target_principal)

        body = {
            "payload": base64.b64encode(message).decode("utf-8"),
            "delegates": self._delegates,
        }

        headers = {"Content-Type": "application/json"}

        authed_session = AuthorizedSession(self._source_credentials)

        try:
            retries = _exponential_backoff.ExponentialBackoff()
            for _ in retries:
                response = authed_session.post(
                    url=iam_sign_endpoint, headers=headers, json=body
                )
                if response.status_code in iam.IAM_RETRY_CODES:
                    continue
                if response.status_code != http_client.OK:
                    raise exceptions.TransportError(
                        "Error calling sign_bytes: {}".format(response.json())
                    )

                return base64.b64decode(response.json()["signedBlob"])
        finally:
            authed_session.close()
        raise exceptions.TransportError("exhausted signBlob endpoint retries")

    @property
    def signer_email(self):
        return self._target_principal

    @property
    def service_account_email(self):
        return self._target_principal

    @property
    def signer(self):
        return self

    @property
    def requires_scopes(self):
        return not self._target_scopes

    @_helpers.copy_docstring(credentials.Credentials)
    def get_cred_info(self):
        if self._cred_file_path:
            return {
                "credential_source": self._cred_file_path,
                "credential_type": "impersonated credentials",
                "principal": self._target_principal,
            }
        return None

    def _make_copy(self):
        cred = self.__class__(
            self._source_credentials,
            target_principal=self._target_principal,
            target_scopes=self._target_scopes,
            delegates=self._delegates,
            lifetime=self._lifetime,
            quota_project_id=self._quota_project_id,
            iam_endpoint_override=self._iam_endpoint_override,
        )
        cred._cred_file_path = self._cred_file_path
        return cred

    @_helpers.copy_docstring(credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):
        cred = self._make_copy()
        cred._quota_project_id = quota_project_id
        return cred

    @_helpers.copy_docstring(credentials.Scoped)
    def with_scopes(self, scopes, default_scopes=None):
        cred = self._make_copy()
        cred._target_scopes = scopes or default_scopes
        return cred

    @classmethod
    def from_impersonated_service_account_info(cls, info, scopes=None):
        """Creates a Credentials instance from parsed impersonated service account credentials info.

        Args:
            info (Mapping[str, str]): The impersonated service account credentials info in Google
                format.
            scopes (Sequence[str]): Optional list of scopes to include in the
                credentials.

        Returns:
            google.oauth2.credentials.Credentials: The constructed
                credentials.

        Raises:
            InvalidType: If the info["source_credentials"] are not a supported impersonation type
            InvalidValue: If the info["service_account_impersonation_url"] is not in the expected format.
            ValueError: If the info is not in the expected format.
        """

        source_credentials_info = info.get("source_credentials")
        source_credentials_type = source_credentials_info.get("type")
        if source_credentials_type == _SOURCE_CREDENTIAL_AUTHORIZED_USER_TYPE:
            from google.oauth2 import credentials

            source_credentials = credentials.Credentials.from_authorized_user_info(
                source_credentials_info
            )
        elif source_credentials_type == _SOURCE_CREDENTIAL_SERVICE_ACCOUNT_TYPE:
            from google.oauth2 import service_account

            source_credentials = service_account.Credentials.from_service_account_info(
                source_credentials_info
            )
        elif (
            source_credentials_type
            == _SOURCE_CREDENTIAL_EXTERNAL_ACCOUNT_AUTHORIZED_USER_TYPE
        ):
            from google.auth import external_account_authorized_user

            source_credentials = external_account_authorized_user.Credentials.from_info(
                source_credentials_info
            )
        else:
            raise exceptions.InvalidType(
                "source credential of type {} is not supported.".format(
                    source_credentials_type
                )
            )

        impersonation_url = info.get("service_account_impersonation_url")
        start_index = impersonation_url.rfind("/")
        end_index = impersonation_url.find(":generateAccessToken")
        if start_index == -1 or end_index == -1 or start_index > end_index:
            raise exceptions.InvalidValue(
                "Cannot extract target principal from {}".format(impersonation_url)
            )
        target_principal = impersonation_url[start_index + 1 : end_index]
        delegates = info.get("delegates")
        quota_project_id = info.get("quota_project_id")

        return cls(
            source_credentials,
            target_principal,
            scopes,
            delegates,
            quota_project_id=quota_project_id,
        )


class IDTokenCredentials(credentials.CredentialsWithQuotaProject):
    """Open ID Connect ID Token-based service account credentials.

    """

    def __init__(
        self,
        target_credentials,
        target_audience=None,
        include_email=False,
        quota_project_id=None,
    ):
        """
        Args:
            target_credentials (google.auth.Credentials): The target
                credential used as to acquire the id tokens for.
            target_audience (string): Audience to issue the token for.
            include_email (bool): Include email in IdToken
            quota_project_id (Optional[str]):  The project ID used for
                quota and billing.
        """
        super(IDTokenCredentials, self).__init__()

        if not isinstance(target_credentials, Credentials):
            raise exceptions.GoogleAuthError(
                "Provided Credential must be " "impersonated_credentials"
            )
        self._target_credentials = target_credentials
        self._target_audience = target_audience
        self._include_email = include_email
        self._quota_project_id = quota_project_id

    def from_credentials(self, target_credentials, target_audience=None):
        return self.__class__(
            target_credentials=target_credentials,
            target_audience=target_audience,
            include_email=self._include_email,
            quota_project_id=self._quota_project_id,
        )

    def with_target_audience(self, target_audience):
        return self.__class__(
            target_credentials=self._target_credentials,
            target_audience=target_audience,
            include_email=self._include_email,
            quota_project_id=self._quota_project_id,
        )

    def with_include_email(self, include_email):
        return self.__class__(
            target_credentials=self._target_credentials,
            target_audience=self._target_audience,
            include_email=include_email,
            quota_project_id=self._quota_project_id,
        )

    @_helpers.copy_docstring(credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):
        return self.__class__(
            target_credentials=self._target_credentials,
            target_audience=self._target_audience,
            include_email=self._include_email,
            quota_project_id=quota_project_id,
        )

    @_helpers.copy_docstring(credentials.Credentials)
    def refresh(self, request):
        from google.auth.transport.requests import AuthorizedSession

        iam_sign_endpoint = iam._IAM_IDTOKEN_ENDPOINT.replace(
            credentials.DEFAULT_UNIVERSE_DOMAIN,
            self._target_credentials.universe_domain,
        ).format(self._target_credentials.signer_email)

        body = {
            "audience": self._target_audience,
            "delegates": self._target_credentials._delegates,
            "includeEmail": self._include_email,
        }

        headers = {
            "Content-Type": "application/json",
            metrics.API_CLIENT_HEADER: metrics.token_request_id_token_impersonate(),
        }

        authed_session = AuthorizedSession(
            self._target_credentials._source_credentials, auth_request=request
        )

        try:
            response = authed_session.post(
                url=iam_sign_endpoint,
                headers=headers,
                data=json.dumps(body).encode("utf-8"),
            )
        finally:
            authed_session.close()

        if response.status_code != http_client.OK:
            raise exceptions.RefreshError(
                "Error getting ID token: {}".format(response.json())
            )

        id_token = response.json()["token"]
        self.token = id_token
        self.expiry = datetime.utcfromtimestamp(
            jwt.decode(id_token, verify=False)["exp"]
        )


def _sign_jwt_request(request, principal, headers, payload, delegates=[]):
    """Makes a request to the Google Cloud IAM service to sign a JWT using a
    service account's system-managed private key.
    Args:
        request (Request): The Request object to use.
        principal (str): The principal to request an access token for.
        headers (Mapping[str, str]): Map of headers to transmit.
        payload (Mapping[str, str]): The JWT payload to sign. Must be a
            serialized JSON object that contains a JWT Claims Set.
        delegates (Sequence[str]): The chained list of delegates required
            to grant the final access_token.  If set, the sequence of
            identities must have "Service Account Token Creator" capability
            granted to the prceeding identity.  For example, if set to
            [serviceAccountB, serviceAccountC], the source_credential
            must have the Token Creator role on serviceAccountB.
            serviceAccountB must have the Token Creator on
            serviceAccountC.
            Finally, C must have Token Creator on target_principal.
            If left unset, source_credential must have that role on
            target_principal.

    Raises:
        google.auth.exceptions.TransportError: Raised if there is an underlying
            HTTP connection error
        google.auth.exceptions.RefreshError: Raised if the impersonated
            credentials are not available.  Common reasons are
            `iamcredentials.googleapis.com` is not enabled or the
            `Service Account Token Creator` is not assigned
    """
    iam_endpoint = iam._IAM_SIGNJWT_ENDPOINT.format(principal)

    body = {"delegates": delegates, "payload": json.dumps(payload)}
    body = json.dumps(body).encode("utf-8")

    response = request(url=iam_endpoint, method="POST", headers=headers, body=body)

    # support both string and bytes type response.data
    response_body = (
        response.data.decode("utf-8")
        if hasattr(response.data, "decode")
        else response.data
    )

    if response.status != http_client.OK:
        raise exceptions.RefreshError(_REFRESH_ERROR, response_body)

    try:
        jwt_response = json.loads(response_body)
        signed_jwt = jwt_response["signedJwt"]
        return signed_jwt

    except (KeyError, ValueError) as caught_exc:
        new_exc = exceptions.RefreshError(
            "{}: No signed JWT in response.".format(_REFRESH_ERROR), response_body
        )
        raise new_exc from caught_exc

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\remote\webelement.py ===
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
from __future__ import annotations

import os
import pkgutil
import warnings
import zipfile
from abc import ABCMeta
from base64 import b64decode, encodebytes
from hashlib import md5 as md5_hash
from io import BytesIO
from typing import List

from selenium.common.exceptions import JavascriptException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.utils import keys_to_typing

from .command import Command
from .shadowroot import ShadowRoot

# TODO: When moving to supporting python 3.9 as the minimum version we can
# use built in importlib_resources.files.
getAttribute_js = None
isDisplayed_js = None


def _load_js():
    global getAttribute_js
    global isDisplayed_js
    _pkg = ".".join(__name__.split(".")[:-1])
    getAttribute_js = pkgutil.get_data(_pkg, "getAttribute.js").decode("utf8")
    isDisplayed_js = pkgutil.get_data(_pkg, "isDisplayed.js").decode("utf8")


class BaseWebElement(metaclass=ABCMeta):
    """Abstract Base Class for WebElement.

    ABC's will allow custom types to be registered as a WebElement to
    pass type checks.
    """

    pass


class WebElement(BaseWebElement):
    """Represents a DOM element.

    Generally, all interesting operations that interact with a document will be
    performed through this interface.

    All method calls will do a freshness check to ensure that the element
    reference is still valid.  This essentially determines whether the
    element is still attached to the DOM.  If this test fails, then an
    ``StaleElementReferenceException`` is thrown, and all future calls to this
    instance will fail.
    """

    def __init__(self, parent, id_) -> None:
        self._parent = parent
        self._id = id_

    def __repr__(self):
        return f'<{type(self).__module__}.{type(self).__name__} (session="{self.session_id}", element="{self._id}")>'

    @property
    def session_id(self) -> str:
        return self._parent.session_id

    @property
    def tag_name(self) -> str:
        """This element's ``tagName`` property.

        Returns:
        --------
        str : The tag name of the element.

        Example:
        --------
        >>> element = driver.find_element(By.ID, "foo")
        """
        return self._execute(Command.GET_ELEMENT_TAG_NAME)["value"]

    @property
    def text(self) -> str:
        """The text of the element.

        Returns:
        --------
        str : The text of the element.

        Example:
        --------
        >>> element = driver.find_element(By.ID, "foo")
        >>> print(element.text)
        """
        return self._execute(Command.GET_ELEMENT_TEXT)["value"]

    def click(self) -> None:
        """Clicks the element.

        Example:
        --------
        >>> element = driver.find_element(By.ID, "foo")
        >>> element.click()
        """
        self._execute(Command.CLICK_ELEMENT)

    def submit(self) -> None:
        """Submits a form.

        Example:
        --------
        >>> form = driver.find_element(By.NAME, "login")
        >>> form.submit()
        """
        script = (
            "/* submitForm */var form = arguments[0];\n"
            'while (form.nodeName != "FORM" && form.parentNode) {\n'
            "  form = form.parentNode;\n"
            "}\n"
            "if (!form) { throw Error('Unable to find containing form element'); }\n"
            "if (!form.ownerDocument) { throw Error('Unable to find owning document'); }\n"
            "var e = form.ownerDocument.createEvent('Event');\n"
            "e.initEvent('submit', true, true);\n"
            "if (form.dispatchEvent(e)) { HTMLFormElement.prototype.submit.call(form) }\n"
        )

        try:
            self._parent.execute_script(script, self)
        except JavascriptException as exc:
            raise WebDriverException("To submit an element, it must be nested inside a form element") from exc

    def clear(self) -> None:
        """Clears the text if it's a text entry element.

        Example:
        --------
        >>> text_field = driver.find_element(By.NAME, "username")
        >>> text_field.clear()
        """
        self._execute(Command.CLEAR_ELEMENT)

    def get_property(self, name) -> str | bool | WebElement | dict:
        """Gets the given property of the element.

        Parameters:
        -----------
        name : str
            - Name of the property to retrieve.

        Returns:
        -------
        str | bool | WebElement | dict : The value of the property.

        Example:
        -------
        >>> text_length = target_element.get_property("text_length")
        """
        try:
            return self._execute(Command.GET_ELEMENT_PROPERTY, {"name": name})["value"]
        except WebDriverException:
            # if we hit an end point that doesn't understand getElementProperty lets fake it
            return self.parent.execute_script("return arguments[0][arguments[1]]", self, name)

    def get_dom_attribute(self, name) -> str:
        """Gets the given attribute of the element. Unlike
        :func:`~selenium.webdriver.remote.BaseWebElement.get_attribute`, this
        method only returns attributes declared in the element's HTML markup.

        Parameters:
        -----------
        name : str
            - Name of the attribute to retrieve.

        Returns:
        -------
        str : The value of the attribute.

        Example:
        -------
        >>> text_length = target_element.get_dom_attribute("class")
        """
        return self._execute(Command.GET_ELEMENT_ATTRIBUTE, {"name": name})["value"]

    def get_attribute(self, name) -> str | None:
        """Gets the given attribute or property of the element.

        This method will first try to return the value of a property with the
        given name. If a property with that name doesn't exist, it returns the
        value of the attribute with the same name. If there's no attribute with
        that name, ``None`` is returned.

        Values which are considered truthy, that is equals "true" or "false",
        are returned as booleans.  All other non-``None`` values are returned
        as strings.  For attributes or properties which do not exist, ``None``
        is returned.

        To obtain the exact value of the attribute or property,
        use :func:`~selenium.webdriver.remote.BaseWebElement.get_dom_attribute` or
        :func:`~selenium.webdriver.remote.BaseWebElement.get_property` methods respectively.

        Parameters:
        -----------
        name : str
            - Name of the attribute/property to retrieve.

        Returns:
        -------
        str | bool | None : The value of the attribute/property.

        Example:
        --------
        >>> # Check if the "active" CSS class is applied to an element.
        >>> is_active = "active" in target_element.get_attribute("class")
        """
        if getAttribute_js is None:
            _load_js()
        attribute_value = self.parent.execute_script(
            f"/* getAttribute */return ({getAttribute_js}).apply(null, arguments);", self, name
        )
        return attribute_value

    def is_selected(self) -> bool:
        """Returns whether the element is selected.

        Example:
        --------
        >>> is_selected = element.is_selected()

        Notes:
        ------
            - This method is generally used on checkboxes, options in a select
            and radio buttons.
        """
        return self._execute(Command.IS_ELEMENT_SELECTED)["value"]

    def is_enabled(self) -> bool:
        """Returns whether the element is enabled.

        Example:
        --------
        >>> is_enabled = element.is_enabled()
        """
        return self._execute(Command.IS_ELEMENT_ENABLED)["value"]

    def send_keys(self, *value: str) -> None:
        """Simulates typing into the element.

        Parameters:
        -----------
        value : str
            - A string for typing, or setting form fields.  For setting
            file inputs, this could be a local file path.

        Notes:
        ------
            - Use this to send simple key events or to fill out form fields
            - This can also be used to set file inputs.

        Examples:
        --------
        To send a simple key event::
        >>> form_textfield = driver.find_element(By.NAME, "username")
        >>> form_textfield.send_keys("admin")

        or to set a file input field::
        >>> file_input = driver.find_element(By.NAME, "profilePic")
        >>> file_input.send_keys("path/to/profilepic.gif")
        >>> # Generally it's better to wrap the file path in one of the methods
        >>> # in os.path to return the actual path to support cross OS testing.
        >>> # file_input.send_keys(os.path.abspath("path/to/profilepic.gif"))
        >>> # When using Cygwin, the path need to be provided in Windows format.
        >>> # file_input.send_keys(f"C:/cygwin{os.path.abspath('path/to/profilepic.gif').replace('/', '\\')}")
        """
        # transfer file to another machine only if remote driver is used
        # the same behaviour as for java binding
        if self.parent._is_remote:
            local_files = list(
                map(
                    lambda keys_to_send: self.parent.file_detector.is_local_file(str(keys_to_send)),
                    "".join(map(str, value)).split("\n"),
                )
            )
            if None not in local_files:
                remote_files = []
                for file in local_files:
                    remote_files.append(self._upload(file))
                value = tuple("\n".join(remote_files))

        self._execute(
            Command.SEND_KEYS_TO_ELEMENT, {"text": "".join(keys_to_typing(value)), "value": keys_to_typing(value)}
        )

    @property
    def shadow_root(self) -> ShadowRoot:
        """Returns a shadow root of the element if there is one or an error.
        Only works from Chromium 96, Firefox 96, and Safari 16.4 onwards.

        Returns:
        -------
        ShadowRoot : object

        Raises:
        -------
        NoSuchShadowRoot - if no shadow root was attached to element

        Example:
        --------
        >>> try:
        ...     shadow_root = element.shadow_root
        >>> except NoSuchShadowRoot:
        ...     print("No shadow root attached to element")
        """
        return self._execute(Command.GET_SHADOW_ROOT)["value"]

    # RenderedWebElement Items
    def is_displayed(self) -> bool:
        """Whether the element is visible to a user.

        Example:
        --------
        >>> is_displayed = element.is_displayed()
        """
        # Only go into this conditional for browsers that don't use the atom themselves
        if isDisplayed_js is None:
            _load_js()
        return self.parent.execute_script(f"/* isDisplayed */return ({isDisplayed_js}).apply(null, arguments);", self)

    @property
    def location_once_scrolled_into_view(self) -> dict:
        """THIS PROPERTY MAY CHANGE WITHOUT WARNING. Use this to discover where
        on the screen an element is so that we can click it. This method should
        cause the element to be scrolled into view.

        Returns:
        --------
        dict: the top lefthand corner location on the screen, or zero
            coordinates if the element is not visible.

        Example:
        --------
        >>> loc = element.location_once_scrolled_into_view
        """
        old_loc = self._execute(
            Command.W3C_EXECUTE_SCRIPT,
            {
                "script": "arguments[0].scrollIntoView(true); return arguments[0].getBoundingClientRect()",
                "args": [self],
            },
        )["value"]
        return {"x": round(old_loc["x"]), "y": round(old_loc["y"])}

    @property
    def size(self) -> dict:
        """The size of the element.

        Returns:
        --------
        dict: The width and height of the element.

        Example:
        --------
        >>> size = element.size
        """
        size = self._execute(Command.GET_ELEMENT_RECT)["value"]
        new_size = {"height": size["height"], "width": size["width"]}
        return new_size

    def value_of_css_property(self, property_name) -> str:
        """The value of a CSS property.

        Parameters:
        -----------
        property_name : str
            - The name of the CSS property to get the value of.

        Returns:
        --------
        str : The value of the CSS property.

        Example:
        --------
        >>> value = element.value_of_css_property("color")
        """
        return self._execute(Command.GET_ELEMENT_VALUE_OF_CSS_PROPERTY, {"propertyName": property_name})["value"]

    @property
    def location(self) -> dict:
        """The location of the element in the renderable canvas.

        Returns:
        --------
        dict: The x and y coordinates of the element.

        Example:
        --------
        >>> loc = element.location
        """
        old_loc = self._execute(Command.GET_ELEMENT_RECT)["value"]
        new_loc = {"x": round(old_loc["x"]), "y": round(old_loc["y"])}
        return new_loc

    @property
    def rect(self) -> dict:
        """A dictionary with the size and location of the element.

        Returns:
        --------
        dict: The size and location of the element.

        Example:
        --------
        >>> rect = element.rect
        """
        return self._execute(Command.GET_ELEMENT_RECT)["value"]

    @property
    def aria_role(self) -> str:
        """Returns the ARIA role of the current web element.

        Returns:
        --------
        str : The ARIA role of the element.

        Example:
        --------
        >>> role = element.aria_role
        """
        return self._execute(Command.GET_ELEMENT_ARIA_ROLE)["value"]

    @property
    def accessible_name(self) -> str:
        """Returns the ARIA Level of the current webelement.

        Returns:
        --------
        str : The ARIA Level of the element.

        Example:
        --------
        >>> name = element.accessible_name
        """
        return self._execute(Command.GET_ELEMENT_ARIA_LABEL)["value"]

    @property
    def screenshot_as_base64(self) -> str:
        """Gets the screenshot of the current element as a base64 encoded
        string.

        Returns:
        --------
        str : The screenshot of the element as a base64 encoded string.

        Example:
        --------
        >>> img_b64 = element.screenshot_as_base64
        """
        return self._execute(Command.ELEMENT_SCREENSHOT)["value"]

    @property
    def screenshot_as_png(self) -> bytes:
        """Gets the screenshot of the current element as a binary data.

        Returns:
        --------
        bytes : The screenshot of the element as binary data.

        Example:
        --------
        >>> element_png = element.screenshot_as_png
        """
        return b64decode(self.screenshot_as_base64.encode("ascii"))

    def screenshot(self, filename) -> bool:
        """Saves a screenshot of the current element to a PNG image file.
        Returns False if there is any IOError, else returns True. Use full
        paths in your filename.

        Returns:
        --------
        bool : True if the screenshot was saved successfully, False otherwise.

        Parameters:
        -----------
        filename : str
            The full path you wish to save your screenshot to. This
            should end with a `.png` extension.

        Element:
        --------
        >>> element.screenshot("/Screenshots/foo.png")
        """
        if not filename.lower().endswith(".png"):
            warnings.warn(
                "name used for saved screenshot does not match file type. It should end with a `.png` extension",
                UserWarning,
            )
        png = self.screenshot_as_png
        try:
            with open(filename, "wb") as f:
                f.write(png)
        except OSError:
            return False
        finally:
            del png
        return True

    @property
    def parent(self):
        """Internal reference to the WebDriver instance this element was found
        from.

        Example:
        --------
        >>> element = driver.find_element(By.ID, "foo")
        >>> parent_element = element.parent
        """
        return self._parent

    @property
    def id(self) -> str:
        """Internal ID used by selenium.

        This is mainly for internal use. Simple use cases such as checking if 2
        webelements refer to the same element, can be done using ``==``::

        Example:
        --------
        >>> if element1 == element2:
        ...     print("These 2 are equal")
        """
        return self._id

    def __eq__(self, element):
        return hasattr(element, "id") and self._id == element.id

    def __ne__(self, element):
        return not self.__eq__(element)

    # Private Methods
    def _execute(self, command, params=None):
        """Executes a command against the underlying HTML element.

        Parameters:
        -----------
        command : any
            The name of the command to _execute as a string.

        params : dict
            A dictionary of named Parameters to send with the command.

        Returns:
        -------
          The command's JSON response loaded into a dictionary object.
        """
        if not params:
            params = {}
        params["id"] = self._id
        return self._parent.execute(command, params)

    def find_element(self, by=By.ID, value=None) -> WebElement:
        """Find an element given a By strategy and locator.

        Parameters:
        -----------
        by : selenium.webdriver.common.by.By
            The locating strategy to use. Default is `By.ID`. Supported values include:
            - By.ID: Locate by element ID.
            - By.NAME: Locate by the `name` attribute.
            - By.XPATH: Locate by an XPath expression.
            - By.CSS_SELECTOR: Locate by a CSS selector.
            - By.CLASS_NAME: Locate by the `class` attribute.
            - By.TAG_NAME: Locate by the tag name (e.g., "input", "button").
            - By.LINK_TEXT: Locate a link element by its exact text.
            - By.PARTIAL_LINK_TEXT: Locate a link element by partial text match.
            - RelativeBy: Locate elements relative to a specified root element.

        Example:
        --------
        element = driver.find_element(By.ID, 'foo')

        Returns:
        -------
        WebElement
            The first matching `WebElement` found on the page.
        """
        by, value = self._parent.locator_converter.convert(by, value)
        return self._execute(Command.FIND_CHILD_ELEMENT, {"using": by, "value": value})["value"]

    def find_elements(self, by=By.ID, value=None) -> List[WebElement]:
        """Find elements given a By strategy and locator.

        Parameters:
        -----------
        by : selenium.webdriver.common.by.By
            The locating strategy to use. Default is `By.ID`. Supported values include:
            - By.ID: Locate by element ID.
            - By.NAME: Locate by the `name` attribute.
            - By.XPATH: Locate by an XPath expression.
            - By.CSS_SELECTOR: Locate by a CSS selector.
            - By.CLASS_NAME: Locate by the `class` attribute.
            - By.TAG_NAME: Locate by the tag name (e.g., "input", "button").
            - By.LINK_TEXT: Locate a link element by its exact text.
            - By.PARTIAL_LINK_TEXT: Locate a link element by partial text match.
            - RelativeBy: Locate elements relative to a specified root element.

        Example:
        --------
        >>> element = driver.find_elements(By.ID, "foo")

        Returns:
        -------
        List[WebElement]
            list of `WebElements` matching locator strategy found on the page.
        """
        by, value = self._parent.locator_converter.convert(by, value)
        return self._execute(Command.FIND_CHILD_ELEMENTS, {"using": by, "value": value})["value"]

    def __hash__(self) -> int:
        return int(md5_hash(self._id.encode("utf-8")).hexdigest(), 16)

    def _upload(self, filename):
        fp = BytesIO()
        zipped = zipfile.ZipFile(fp, "w", zipfile.ZIP_DEFLATED)
        zipped.write(filename, os.path.split(filename)[1])
        zipped.close()
        content = encodebytes(fp.getvalue())
        if not isinstance(content, str):
            content = content.decode("utf-8")
        try:
            return self._execute(Command.UPLOAD_FILE, {"file": content})["value"]
        except WebDriverException as e:
            if "Unrecognized command: POST" in str(e):
                return filename
            if "Command not found: POST " in str(e):
                return filename
            if '{"status":405,"value":["GET","HEAD","DELETE"]}' in str(e):
                return filename
            raise

# === NexusCore/openenv\Lib\site-packages\yaspin\core.py ===
# :copyright: (c) 2021 by Pavlo Dmytrenko.
# :license: MIT, see LICENSE for more details.

"""
yaspin.yaspin
~~~~~~~~~~~~~

A lightweight terminal spinner.
"""
from __future__ import annotations

import functools
import itertools
import shutil
import signal
import sys
import threading
import time
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Final,
    Generator,
    Iterator,
    Optional,
    Protocol,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    runtime_checkable,
)

from termcolor import ATTRIBUTES, COLORS, HIGHLIGHTS, colored

from .constants import SPINNER_ATTRS

if TYPE_CHECKING:
    from types import FrameType, TracebackType

    SignalHandlers = Union[Callable[[int, Optional[FrameType]], Any], int, None]

Fn = TypeVar("Fn", bound=Callable[..., Any])

ENCODING: Final[str] = "utf-8"


def to_unicode(text_type: Union[str, bytes], encoding: str = ENCODING) -> str:
    if isinstance(text_type, bytes):
        return text_type.decode(encoding)
    return text_type


@dataclass
class Spinner:
    frames: str
    interval: int


default_spinner = Spinner("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", 80)


@runtime_checkable
class SignalHandlerProtocol(Protocol):
    def __call__(self, signum: int, frame: Any, spinner: Yaspin) -> None: ...


def default_handler(signum: int, frame: Any, spinner: Yaspin) -> None:  # pylint: disable=unused-argument
    """Signal handler, used to gracefully shut down the ``spinner`` instance
    when specified signal is received by the process running the ``spinner``.

    ``signum`` and ``frame`` are mandatory arguments. Check ``signal.signal``
    function for more details.
    """
    spinner.fail()
    spinner.stop()
    sys.exit(0)


def fancy_handler(signum: int, frame: Any, spinner: Yaspin) -> None:  # pylint: disable=unused-argument
    """Signal handler, used to gracefully shut down the ``spinner`` instance
    when specified signal is received by the process running the ``spinner``.

    ``signum`` and ``frame`` are mandatory arguments. Check ``signal.signal``
    function for more details.
    """
    spinner.red.fail("✘")
    spinner.stop()
    sys.exit(0)


class Yaspin:  # pylint: disable=too-many-instance-attributes
    """Implements a context manager that spawns a thread
    to write spinner frames into a tty (stdout) during
    context execution.
    """

    # When Python finds its output attached to a terminal,
    # it sets the sys.stdout.encoding attribute to the terminal's encoding.
    # The print statement's handler will automatically encode unicode
    # arguments into bytes.
    def __init__(  # pylint: disable=too-many-arguments
        self,
        spinner: Spinner = default_spinner,
        text: str = "",
        color: Optional[str] = None,
        on_color: Optional[str] = None,
        attrs: Optional[Sequence[str]] = None,
        reversal: bool = False,
        side: str = "left",
        sigmap: Optional[dict[signal.Signals, SignalHandlers]] = None,
        timer: bool = False,
        ellipsis: str = "",
    ) -> None:
        # Spinner
        self._spinner = self._set_spinner(spinner)
        self._frames = self._set_frames(self._spinner, reversal)
        self._interval = self._set_interval(self._spinner)
        self._cycle = self._set_cycle(self._frames)

        # Color Specification
        self._color = self._set_color(color) if color else color
        self._on_color = self._set_on_color(on_color) if on_color else on_color
        self._attrs = self._set_attrs(attrs) if attrs else set()
        self._color_func = self._compose_color_func()

        # Other
        self._text = text
        self._side = self._set_side(side)
        self._reversal = reversal
        self._timer = timer
        self._ellipsis = ellipsis
        self._terminal_width: int = shutil.get_terminal_size().columns
        self._start_time: Optional[float] = None
        self._stop_time: Optional[float] = None

        # Helper flags
        self._stop_spin: Optional[threading.Event] = None
        self._hide_spin: Optional[threading.Event] = None
        self._spin_thread: Optional[threading.Thread] = None
        self._last_frame: Optional[str] = None
        self._stdout_lock = threading.Lock()
        self._hidden_level = 0
        self._cur_line_len = 0

        # Signals
        self._sigmap = sigmap if sigmap else {}
        # Maps signals to their default handlers in order to reset
        # custom handlers set by ``sigmap`` at the cleanup phase.
        self._dfl_sigmap: dict[signal.Signals, SignalHandlers] = {}

    # Dunders
    #
    def __repr__(self) -> str:
        return f"<Yaspin frames={self._frames!s}>"

    def __enter__(self) -> Yaspin:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self._spin_thread is None:
            raise RuntimeError("spin thread is None")
        # Avoid stop() execution for the 2nd time
        if self._spin_thread.is_alive():
            self.stop()

    def __call__(self, fn: Fn) -> Fn:
        @functools.wraps(fn)
        def inner(*args: Any, **kwargs: Any) -> Fn:
            with self:
                return fn(*args, **kwargs)

        return cast(Fn, inner)

    def __getattr__(self, name: str) -> Yaspin:
        # CLI spinners
        if name in SPINNER_ATTRS:
            from .spinners import Spinners  # pylint: disable=import-outside-toplevel

            sp = getattr(Spinners, name)
            self.spinner = sp
        # Color Attributes: "color", "on_color", "attrs"
        elif name in set(key for d in [ATTRIBUTES, COLORS, HIGHLIGHTS] for key in d):
            # Call appropriate property setters;
            # _color_func is updated automatically by setters.
            if name in ATTRIBUTES:
                self.attrs = [name]  # calls property setter
            if name in COLORS:
                setattr(self, "color", name)  # calls property setter
            if name in HIGHLIGHTS:
                setattr(self, "on_color", name)  # calls property setter
        # Side: "left" or "right"
        elif name in ("left", "right"):
            self.side = name  # calls property setter
        # Common error for unsupported attributes
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute: '{name}'")
        return self

    # Properties
    #
    @property
    def spinner(self) -> Spinner:
        return self._spinner

    @spinner.setter
    def spinner(self, sp: Spinner) -> None:
        self._spinner = self._set_spinner(sp)
        self._frames = self._set_frames(self._spinner, self._reversal)
        self._interval = self._set_interval(self._spinner)
        self._cycle = self._set_cycle(self._frames)

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, txt: str) -> None:
        self._text = txt

    @property
    def color(self) -> Optional[str]:
        return self._color

    @color.setter
    def color(self, value: str) -> None:
        self._color = self._set_color(value) if value else value
        self._color_func = self._compose_color_func()  # update

    @property
    def on_color(self) -> Optional[str]:
        return self._on_color

    @on_color.setter
    def on_color(self, value: str) -> None:
        self._on_color = self._set_on_color(value) if value else value
        self._color_func = self._compose_color_func()  # update

    @property
    def attrs(self) -> Sequence[str]:
        return list(self._attrs)

    @attrs.setter
    def attrs(self, value: Sequence[str]) -> None:
        new_attrs = self._set_attrs(value) if value else set()
        self._attrs = self._attrs.union(new_attrs)
        self._color_func = self._compose_color_func()  # update

    @property
    def side(self) -> str:
        return self._side

    @side.setter
    def side(self, value: str) -> None:
        self._side = self._set_side(value)

    @property
    def ellipsis(self) -> str:
        return self._ellipsis

    @ellipsis.setter
    def ellipsis(self, value: str) -> None:
        self._ellipsis = value

    @property
    def reversal(self) -> bool:
        return self._reversal

    @reversal.setter
    def reversal(self, value: bool) -> None:
        self._reversal = value
        self._frames = self._set_frames(self._spinner, self._reversal)
        self._cycle = self._set_cycle(self._frames)

    @property
    def elapsed_time(self) -> float:
        if self._start_time is None:
            return 0
        if self._stop_time is None:
            return time.time() - self._start_time
        return self._stop_time - self._start_time

    # Public
    #
    def start(self) -> None:
        if self._sigmap:
            self._register_signal_handlers()

        self._hide_cursor()
        self._start_time = time.time()
        # Reset value to properly calculate subsequent spinner starts (if any)
        self._stop_time = None
        self._stop_spin = threading.Event()
        self._hide_spin = threading.Event()
        self._spin_thread = threading.Thread(target=self._spin)
        try:
            self._spin_thread.start()
        finally:
            # Ensure cursor is not hidden if any failure occurs that prevents
            # getting it back
            self._show_cursor()

    def stop(self) -> None:
        self._stop_time = time.time()

        if self._dfl_sigmap:
            # Reset registered signal handlers to default ones
            self._reset_signal_handlers()

        if self._spin_thread is not None:
            if self._stop_spin is None:
                raise RuntimeError("stop_spin event is None")
            self._stop_spin.set()
            self._spin_thread.join()

        self._clear_line()
        self._show_cursor()

    def hide(self) -> None:
        """Hide the spinner to allow for custom writing to the terminal."""
        thr_is_alive = self._spin_thread and self._spin_thread.is_alive()
        if self._hide_spin is None:
            raise RuntimeError("hide_spin is None")

        if thr_is_alive and not self._hide_spin.is_set():
            with self._stdout_lock:
                # set the hidden spinner flag
                self._hide_spin.set()
                self._clear_line()

                # flush the stdout buffer so the current line
                # can be rewritten to
                sys.stdout.flush()

    @contextmanager
    def hidden(self) -> Generator[None, None, None]:
        """Hide the spinner within a block, can be nested"""
        if self._hidden_level == 0:
            self.hide()
        self._hidden_level += 1
        try:
            yield
        finally:
            self._hidden_level -= 1
            if self._hidden_level == 0:
                self.show()

    def show(self) -> None:
        """Show the hidden spinner."""
        thr_is_alive = self._spin_thread and self._spin_thread.is_alive()
        if self._hide_spin is None:
            raise RuntimeError("hide_spin is None")

        if thr_is_alive and self._hide_spin.is_set():
            with self._stdout_lock:
                # clear the hidden spinner flag
                self._hide_spin.clear()
                # clear the current line so the spinner is not appended to it
                self._clear_line()

    def write(self, text: str) -> None:
        """Write text in the terminal without breaking the spinner."""
        # similar to tqdm.write()
        # https://pypi.python.org/pypi/tqdm#writing-messages
        with self._stdout_lock:
            self._clear_line()
            if isinstance(text, (str, bytes)):
                _text = to_unicode(text)
            else:
                _text = str(text)
            sys.stdout.write(f"{_text}\n")
            self._cur_line_len = 0

    def ok(self, text: str = "OK") -> None:
        """Set Ok (success) finalizer to a spinner."""
        _text = text if text else "OK"
        self._freeze(_text)

    def fail(self, text: str = "FAIL") -> None:
        """Set fail finalizer to a spinner."""
        _text = text if text else "FAIL"
        self._freeze(_text)

    # Protected
    #
    @staticmethod
    def _warn_color_disabled() -> None:
        warnings.warn(
            "color, on_color and attrs are not supported when running in jupyter",
            stacklevel=3,
        )

    def _freeze(self, final_text: str) -> None:
        """Stop spinner, compose last frame and 'freeze' it."""
        text = to_unicode(final_text)
        self._last_frame = self._compose_out(text, mode="last")

        # Should be stopped here, otherwise prints after
        # self._freeze call will mess up the spinner
        self.stop()
        with self._stdout_lock:
            if self._last_frame is None:
                raise RuntimeError("last_frame is None")
            sys.stdout.write(self._last_frame)
            self._cur_line_len = 0

    def _spin(self) -> None:
        if self._stop_spin is None:
            raise RuntimeError("stop_spin is None")

        while not self._stop_spin.is_set():
            if self._hide_spin is not None and self._hide_spin.is_set():
                # Wait a bit to avoid wasting cycles
                time.sleep(self._interval)
                continue

            # Compose output
            spin_phase = next(self._cycle)
            out = self._compose_out(spin_phase)

            # Write
            with self._stdout_lock:
                self._clear_line()
                sys.stdout.write(out)
                sys.stdout.flush()
                self._cur_line_len = max(self._cur_line_len, len(out))

            # Wait
            self._stop_spin.wait(self._interval)

    def _compose_color_func(self) -> Optional[Callable[..., str]]:
        if self.is_jupyter():
            # ANSI Color Control Sequences are problematic in Jupyter
            return None

        return functools.partial(
            colored,
            color=self._color,
            on_color=self._on_color,
            attrs=list(self._attrs),
        )

    def _compose_out(self, frame: str, mode: Optional[str] = None) -> str:
        text = str(self._text)

        # Timer
        if self._timer:
            sec, fsec = divmod(round(100 * self.elapsed_time), 100)
            timer = " ({}.{:02.0f})".format(  # pylint: disable=consider-using-f-string
                timedelta(seconds=sec), fsec
            )
        else:
            timer = ""

        # Truncate
        max_text_len = self._get_max_text_length(len(frame), len(timer))
        if max_text_len < 1:
            raise ValueError(
                f"Terminal size {self._terminal_width} is too small to display spinner with the given settings."
            )
        text = text[:max_text_len] + self._ellipsis if len(text) > max_text_len else text

        # Colors
        if self._color_func is not None:
            frame = self._color_func(frame)

        # Position
        if self._side == "right":
            frame, text = text, frame

        # Mode
        if mode is None:
            out = f"\r{frame} {text}{timer}"
        else:
            out = f"{frame} {text}{timer}\n"

        return out

    def _get_max_text_length(self, frame_width: int, timer_width: int) -> int:
        ellipsis_width = len(self._ellipsis)
        # There is always a space between frame and text
        frame_width += 1

        return self._terminal_width - frame_width - timer_width - ellipsis_width

    def _register_signal_handlers(self) -> None:
        # SIGKILL cannot be caught or ignored, and the receiving
        # process cannot perform any clean-up upon receiving this
        # signal.
        if signal.SIGKILL in self._sigmap:
            raise ValueError(
                "Trying to set handler for SIGKILL signal. "
                "SIGKILL cannot be caught or ignored in POSIX systems."
            )
        for sig, sig_handler in self._sigmap.items():
            # A handler for a particular signal, once set, remains
            # installed until it is explicitly reset. Store default
            # signal handlers for subsequent reset at cleanup phase.
            dfl_handler = signal.getsignal(sig)
            self._dfl_sigmap[sig] = dfl_handler

            # ``signal.SIG_DFL`` and ``signal.SIG_IGN`` are also valid
            # signal handlers and are not callables.
            if callable(sig_handler) and isinstance(sig_handler, SignalHandlerProtocol):
                # ``signal.signal`` accepts handler function which is
                # called with two arguments: signal number and the
                # interrupted stack frame. ``functools.partial`` solves
                # the problem of passing spinner instance into the handler
                # function.
                sig_handler = functools.partial(sig_handler, spinner=self)

            signal.signal(sig, sig_handler)

    def _reset_signal_handlers(self) -> None:
        for sig, sig_handler in self._dfl_sigmap.items():
            signal.signal(sig, sig_handler)

    # Static
    #
    @staticmethod
    def is_jupyter() -> bool:
        return not sys.stdout.isatty()

    @staticmethod
    def _set_color(value: str) -> str:
        if Yaspin.is_jupyter():
            Yaspin._warn_color_disabled()

        if value not in COLORS:
            raise ValueError(
                "'{0}': unsupported color value. Use one of the: {1}".format(  # pylint: disable=consider-using-f-string
                    value, ", ".join(COLORS.keys())
                )
            )
        return value

    @staticmethod
    def _set_on_color(value: str) -> str:
        if Yaspin.is_jupyter():
            Yaspin._warn_color_disabled()

        if value not in HIGHLIGHTS:
            raise ValueError(
                "'{0}': unsupported on_color value. "  # pylint: disable=consider-using-f-string
                "Use one of the: {1}".format(value, ", ".join(HIGHLIGHTS.keys()))
            )
        return value

    @staticmethod
    def _set_attrs(attrs: Sequence[str]) -> set[str]:
        if Yaspin.is_jupyter():
            Yaspin._warn_color_disabled()

        for attr in attrs:
            if attr not in ATTRIBUTES:
                raise ValueError(
                    "'{0}': unsupported attribute value. "  # pylint: disable=consider-using-f-string
                    "Use one of the: {1}".format(attr, ", ".join(ATTRIBUTES.keys()))
                )
        return set(attrs)

    @staticmethod
    def _set_spinner(spinner: Spinner) -> Spinner:
        if hasattr(spinner, "frames") and hasattr(spinner, "interval"):
            if not spinner.frames or not spinner.interval:
                sp = default_spinner
            else:
                sp = spinner
        else:
            sp = default_spinner

        return sp

    @staticmethod
    def _set_side(side: str) -> str:
        if side not in ("left", "right"):
            raise ValueError("'{0}': unsupported side value. Use either 'left' or 'right'.")
        return side

    @staticmethod
    def _set_frames(spinner: Spinner, reversal: bool) -> Union[str, Sequence[str]]:
        uframes = None  # unicode frames
        uframes_seq = None  # sequence of unicode frames

        if isinstance(spinner.frames, str):
            uframes = spinner.frames

        # TODO (pavdmyt): support any type that implements iterable
        if isinstance(spinner.frames, (list, tuple)):
            # Empty ``spinner.frames`` is handled by ``Yaspin._set_spinner``
            if spinner.frames and isinstance(spinner.frames[0], bytes):
                uframes_seq = [to_unicode(frame) for frame in spinner.frames]
            else:
                uframes_seq = spinner.frames

        _frames = uframes or uframes_seq
        if not _frames:
            # Empty ``spinner.frames`` is handled by ``Yaspin._set_spinner``.
            # This code is very unlikely to be executed. However, it's still
            # here to be on a safe side.
            raise ValueError(f"{spinner!r}: no frames found in spinner")

        # Builtin ``reversed`` returns reverse iterator,
        # which adds unnecessary difficulty for returning
        # unicode value;
        # Hence using [::-1] syntax
        frames = _frames[::-1] if reversal else _frames

        return frames

    @staticmethod
    def _set_interval(spinner: Spinner) -> float:
        # Milliseconds to Seconds
        return spinner.interval * 0.001

    @staticmethod
    def _set_cycle(frames: Union[str, Sequence[str]]) -> Iterator[str]:
        return itertools.cycle(frames)

    @staticmethod
    def _hide_cursor() -> None:
        if sys.stdout.isatty():
            # ANSI Control Sequence DECTCEM 1 does not work in Jupyter
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

    @staticmethod
    def _show_cursor() -> None:
        if sys.stdout.isatty():
            # ANSI Control Sequence DECTCEM 2 does not work in Jupyter
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    def _clear_line(self) -> None:
        if sys.stdout.isatty():
            # ANSI Control Sequence EL does not work in Jupyter
            sys.stdout.write("\r\033[K")
        else:
            fill = " " * self._cur_line_len
            sys.stdout.write(f"\r{fill}\r")

# === NexusCore/openenv\Lib\site-packages\nltk\inference\discourse.py ===
# Natural Language Toolkit: Discourse Processing
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Dan Garrette <dhgarrette@gmail.com>
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

r"""
Module for incrementally developing simple discourses, and checking for semantic ambiguity,
consistency and informativeness.

Many of the ideas are based on the CURT family of programs of Blackburn and Bos
(see http://homepages.inf.ed.ac.uk/jbos/comsem/book1.html).

Consistency checking is carried out  by using the ``mace`` module to call the Mace4 model builder.
Informativeness checking is carried out with a call to ``Prover.prove()`` from
the ``inference``  module.

``DiscourseTester`` is a constructor for discourses.
The basic data structure is a list of sentences, stored as ``self._sentences``. Each sentence in the list
is assigned a "sentence ID" (``sid``) of the form ``s``\ *i*. For example::

    s0: A boxer walks
    s1: Every boxer chases a girl

Each sentence can be ambiguous between a number of readings, each of which receives a
"reading ID" (``rid``) of the form ``s``\ *i* -``r``\ *j*. For example::

    s0 readings:

    s0-r1: some x.(boxer(x) & walk(x))
    s0-r0: some x.(boxerdog(x) & walk(x))

A "thread" is a list of readings, represented as a list of ``rid``\ s.
Each thread receives a "thread ID" (``tid``) of the form ``d``\ *i*.
For example::

    d0: ['s0-r0', 's1-r0']

The set of all threads for a discourse is the Cartesian product of all the readings of the sequences of sentences.
(This is not intended to scale beyond very short discourses!) The method ``readings(filter=True)`` will only show
those threads which are consistent (taking into account any background assumptions).
"""

import os
from abc import ABCMeta, abstractmethod
from functools import reduce
from operator import add, and_

from nltk.data import show_cfg
from nltk.inference.mace import MaceCommand
from nltk.inference.prover9 import Prover9Command
from nltk.parse import load_parser
from nltk.parse.malt import MaltParser
from nltk.sem.drt import AnaphoraResolutionException, resolve_anaphora
from nltk.sem.glue import DrtGlue
from nltk.sem.logic import Expression
from nltk.tag import RegexpTagger


class ReadingCommand(metaclass=ABCMeta):
    @abstractmethod
    def parse_to_readings(self, sentence):
        """
        :param sentence: the sentence to read
        :type sentence: str
        """

    def process_thread(self, sentence_readings):
        """
        This method should be used to handle dependencies between readings such
        as resolving anaphora.

        :param sentence_readings: readings to process
        :type sentence_readings: list(Expression)
        :return: the list of readings after processing
        :rtype: list(Expression)
        """
        return sentence_readings

    @abstractmethod
    def combine_readings(self, readings):
        """
        :param readings: readings to combine
        :type readings: list(Expression)
        :return: one combined reading
        :rtype: Expression
        """

    @abstractmethod
    def to_fol(self, expression):
        """
        Convert this expression into a First-Order Logic expression.

        :param expression: an expression
        :type expression: Expression
        :return: a FOL version of the input expression
        :rtype: Expression
        """


class CfgReadingCommand(ReadingCommand):
    def __init__(self, gramfile=None):
        """
        :param gramfile: name of file where grammar can be loaded
        :type gramfile: str
        """
        self._gramfile = (
            gramfile if gramfile else "grammars/book_grammars/discourse.fcfg"
        )
        self._parser = load_parser(self._gramfile)

    def parse_to_readings(self, sentence):
        """:see: ReadingCommand.parse_to_readings()"""
        from nltk.sem import root_semrep

        tokens = sentence.split()
        trees = self._parser.parse(tokens)
        return [root_semrep(tree) for tree in trees]

    def combine_readings(self, readings):
        """:see: ReadingCommand.combine_readings()"""
        return reduce(and_, readings)

    def to_fol(self, expression):
        """:see: ReadingCommand.to_fol()"""
        return expression


class DrtGlueReadingCommand(ReadingCommand):
    def __init__(self, semtype_file=None, remove_duplicates=False, depparser=None):
        """
        :param semtype_file: name of file where grammar can be loaded
        :param remove_duplicates: should duplicates be removed?
        :param depparser: the dependency parser
        """
        if semtype_file is None:
            semtype_file = os.path.join(
                "grammars", "sample_grammars", "drt_glue.semtype"
            )
        self._glue = DrtGlue(
            semtype_file=semtype_file,
            remove_duplicates=remove_duplicates,
            depparser=depparser,
        )

    def parse_to_readings(self, sentence):
        """:see: ReadingCommand.parse_to_readings()"""
        return self._glue.parse_to_meaning(sentence)

    def process_thread(self, sentence_readings):
        """:see: ReadingCommand.process_thread()"""
        try:
            return [self.combine_readings(sentence_readings)]
        except AnaphoraResolutionException:
            return []

    def combine_readings(self, readings):
        """:see: ReadingCommand.combine_readings()"""
        thread_reading = reduce(add, readings)
        return resolve_anaphora(thread_reading.simplify())

    def to_fol(self, expression):
        """:see: ReadingCommand.to_fol()"""
        return expression.fol()


class DiscourseTester:
    """
    Check properties of an ongoing discourse.
    """

    def __init__(self, input, reading_command=None, background=None):
        """
        Initialize a ``DiscourseTester``.

        :param input: the discourse sentences
        :type input: list of str
        :param background: Formulas which express background assumptions
        :type background: list(Expression)
        """
        self._input = input
        self._sentences = {"s%s" % i: sent for i, sent in enumerate(input)}
        self._models = None
        self._readings = {}
        self._reading_command = (
            reading_command if reading_command else CfgReadingCommand()
        )
        self._threads = {}
        self._filtered_threads = {}
        if background is not None:
            from nltk.sem.logic import Expression

            for e in background:
                assert isinstance(e, Expression)
            self._background = background
        else:
            self._background = []

    ###############################
    # Sentences
    ###############################

    def sentences(self):
        """
        Display the list of sentences in the current discourse.
        """
        for id in sorted(self._sentences):
            print(f"{id}: {self._sentences[id]}")

    def add_sentence(self, sentence, informchk=False, consistchk=False):
        """
        Add a sentence to the current discourse.

        Updates ``self._input`` and ``self._sentences``.
        :param sentence: An input sentence
        :type sentence: str
        :param informchk: if ``True``, check that the result of adding the sentence is thread-informative. Updates ``self._readings``.
        :param consistchk: if ``True``, check that the result of adding the sentence is thread-consistent. Updates ``self._readings``.

        """
        # check whether the new sentence is informative (i.e. not entailed by the previous discourse)
        if informchk:
            self.readings(verbose=False)
            for tid in sorted(self._threads):
                assumptions = [reading for (rid, reading) in self.expand_threads(tid)]
                assumptions += self._background
                for sent_reading in self._get_readings(sentence):
                    tp = Prover9Command(goal=sent_reading, assumptions=assumptions)
                    if tp.prove():
                        print(
                            "Sentence '%s' under reading '%s':"
                            % (sentence, str(sent_reading))
                        )
                        print("Not informative relative to thread '%s'" % tid)

        self._input.append(sentence)
        self._sentences = {"s%s" % i: sent for i, sent in enumerate(self._input)}
        # check whether adding the new sentence to the discourse preserves consistency (i.e. a model can be found for the combined set of
        # of assumptions
        if consistchk:
            self.readings(verbose=False)
            self.models(show=False)

    def retract_sentence(self, sentence, verbose=True):
        """
        Remove a sentence from the current discourse.

        Updates ``self._input``, ``self._sentences`` and ``self._readings``.
        :param sentence: An input sentence
        :type sentence: str
        :param verbose: If ``True``,  report on the updated list of sentences.
        """
        try:
            self._input.remove(sentence)
        except ValueError:
            print(
                "Retraction failed. The sentence '%s' is not part of the current discourse:"
                % sentence
            )
            self.sentences()
            return None
        self._sentences = {"s%s" % i: sent for i, sent in enumerate(self._input)}
        self.readings(verbose=False)
        if verbose:
            print("Current sentences are ")
            self.sentences()

    def grammar(self):
        """
        Print out the grammar in use for parsing input sentences
        """
        show_cfg(self._reading_command._gramfile)

    ###############################
    # Readings and Threads
    ###############################

    def _get_readings(self, sentence):
        """
        Build a list of semantic readings for a sentence.

        :rtype: list(Expression)
        """
        return self._reading_command.parse_to_readings(sentence)

    def _construct_readings(self):
        """
        Use ``self._sentences`` to construct a value for ``self._readings``.
        """
        # re-initialize self._readings in case we have retracted a sentence
        self._readings = {}
        for sid in sorted(self._sentences):
            sentence = self._sentences[sid]
            readings = self._get_readings(sentence)
            self._readings[sid] = {
                f"{sid}-r{rid}": reading.simplify()
                for rid, reading in enumerate(sorted(readings, key=str))
            }

    def _construct_threads(self):
        """
        Use ``self._readings`` to construct a value for ``self._threads``
        and use the model builder to construct a value for ``self._filtered_threads``
        """
        thread_list = [[]]
        for sid in sorted(self._readings):
            thread_list = self.multiply(thread_list, sorted(self._readings[sid]))
        self._threads = {"d%s" % tid: thread for tid, thread in enumerate(thread_list)}
        # re-initialize the filtered threads
        self._filtered_threads = {}
        # keep the same ids, but only include threads which get models
        consistency_checked = self._check_consistency(self._threads)
        for tid, thread in self._threads.items():
            if (tid, True) in consistency_checked:
                self._filtered_threads[tid] = thread

    def _show_readings(self, sentence=None):
        """
        Print out the readings for  the discourse (or a single sentence).
        """
        if sentence is not None:
            print("The sentence '%s' has these readings:" % sentence)
            for r in [str(reading) for reading in (self._get_readings(sentence))]:
                print("    %s" % r)
        else:
            for sid in sorted(self._readings):
                print()
                print("%s readings:" % sid)
                print()  #'-' * 30
                for rid in sorted(self._readings[sid]):
                    lf = self._readings[sid][rid]
                    print(f"{rid}: {lf.normalize()}")

    def _show_threads(self, filter=False, show_thread_readings=False):
        """
        Print out the value of ``self._threads`` or ``self._filtered_hreads``
        """
        threads = self._filtered_threads if filter else self._threads
        for tid in sorted(threads):
            if show_thread_readings:
                readings = [
                    self._readings[rid.split("-")[0]][rid] for rid in self._threads[tid]
                ]
                try:
                    thread_reading = (
                        ": %s"
                        % self._reading_command.combine_readings(readings).normalize()
                    )
                except Exception as e:
                    thread_reading = ": INVALID: %s" % e.__class__.__name__
            else:
                thread_reading = ""

            print("%s:" % tid, self._threads[tid], thread_reading)

    def readings(
        self,
        sentence=None,
        threaded=False,
        verbose=True,
        filter=False,
        show_thread_readings=False,
    ):
        """
        Construct and show the readings of the discourse (or of a single sentence).

        :param sentence: test just this sentence
        :type sentence: str
        :param threaded: if ``True``, print out each thread ID and the corresponding thread.
        :param filter: if ``True``, only print out consistent thread IDs and threads.
        """
        self._construct_readings()
        self._construct_threads()

        # if we are filtering or showing thread readings, show threads
        if filter or show_thread_readings:
            threaded = True

        if verbose:
            if not threaded:
                self._show_readings(sentence=sentence)
            else:
                self._show_threads(
                    filter=filter, show_thread_readings=show_thread_readings
                )

    def expand_threads(self, thread_id, threads=None):
        """
        Given a thread ID, find the list of ``logic.Expression`` objects corresponding to the reading IDs in that thread.

        :param thread_id: thread ID
        :type thread_id: str
        :param threads: a mapping from thread IDs to lists of reading IDs
        :type threads: dict
        :return: A list of pairs ``(rid, reading)`` where reading is the ``logic.Expression`` associated with a reading ID
        :rtype: list of tuple
        """
        if threads is None:
            threads = self._threads
        return [
            (rid, self._readings[sid][rid])
            for rid in threads[thread_id]
            for sid in rid.split("-")[:1]
        ]

    ###############################
    # Models and Background
    ###############################

    def _check_consistency(self, threads, show=False, verbose=False):
        results = []
        for tid in sorted(threads):
            assumptions = [
                reading for (rid, reading) in self.expand_threads(tid, threads=threads)
            ]
            assumptions = list(
                map(
                    self._reading_command.to_fol,
                    self._reading_command.process_thread(assumptions),
                )
            )
            if assumptions:
                assumptions += self._background
                # if Mace4 finds a model, it always seems to find it quickly
                mb = MaceCommand(None, assumptions, max_models=20)
                modelfound = mb.build_model()
            else:
                modelfound = False
            results.append((tid, modelfound))
            if show:
                spacer(80)
                print("Model for Discourse Thread %s" % tid)
                spacer(80)
                if verbose:
                    for a in assumptions:
                        print(a)
                    spacer(80)
                if modelfound:
                    print(mb.model(format="cooked"))
                else:
                    print("No model found!\n")
        return results

    def models(self, thread_id=None, show=True, verbose=False):
        """
        Call Mace4 to build a model for each current discourse thread.

        :param thread_id: thread ID
        :type thread_id: str
        :param show: If ``True``, display the model that has been found.
        """
        self._construct_readings()
        self._construct_threads()
        threads = {thread_id: self._threads[thread_id]} if thread_id else self._threads

        for tid, modelfound in self._check_consistency(
            threads, show=show, verbose=verbose
        ):
            idlist = [rid for rid in threads[tid]]

            if not modelfound:
                print(f"Inconsistent discourse: {tid} {idlist}:")
                for rid, reading in self.expand_threads(tid):
                    print(f"    {rid}: {reading.normalize()}")
                print()
            else:
                print(f"Consistent discourse: {tid} {idlist}:")
                for rid, reading in self.expand_threads(tid):
                    print(f"    {rid}: {reading.normalize()}")
                print()

    def add_background(self, background, verbose=False):
        """
        Add a list of background assumptions for reasoning about the discourse.

        When called,  this method also updates the discourse model's set of readings and threads.
        :param background: Formulas which contain background information
        :type background: list(Expression)
        """
        from nltk.sem.logic import Expression

        for count, e in enumerate(background):
            assert isinstance(e, Expression)
            if verbose:
                print("Adding assumption %s to background" % count)
            self._background.append(e)

        # update the state
        self._construct_readings()
        self._construct_threads()

    def background(self):
        """
        Show the current background assumptions.
        """
        for e in self._background:
            print(str(e))

    ###############################
    # Misc
    ###############################

    @staticmethod
    def multiply(discourse, readings):
        """
        Multiply every thread in ``discourse`` by every reading in ``readings``.

        Given discourse = [['A'], ['B']], readings = ['a', 'b', 'c'] , returns
        [['A', 'a'], ['A', 'b'], ['A', 'c'], ['B', 'a'], ['B', 'b'], ['B', 'c']]

        :param discourse: the current list of readings
        :type discourse: list of lists
        :param readings: an additional list of readings
        :type readings: list(Expression)
        :rtype: A list of lists
        """
        result = []
        for sublist in discourse:
            for r in readings:
                new = []
                new += sublist
                new.append(r)
                result.append(new)
        return result


def load_fol(s):
    """
    Temporarily duplicated from ``nltk.sem.util``.
    Convert a  file of first order formulas into a list of ``Expression`` objects.

    :param s: the contents of the file
    :type s: str
    :return: a list of parsed formulas.
    :rtype: list(Expression)
    """
    statements = []
    for linenum, line in enumerate(s.splitlines()):
        line = line.strip()
        if line.startswith("#") or line == "":
            continue
        try:
            statements.append(Expression.fromstring(line))
        except Exception as e:
            raise ValueError(f"Unable to parse line {linenum}: {line}") from e
    return statements


###############################
# Demo
###############################
def discourse_demo(reading_command=None):
    """
    Illustrate the various methods of ``DiscourseTester``
    """
    dt = DiscourseTester(
        ["A boxer walks", "Every boxer chases a girl"], reading_command
    )
    dt.models()
    print()
    # dt.grammar()
    print()
    dt.sentences()
    print()
    dt.readings()
    print()
    dt.readings(threaded=True)
    print()
    dt.models("d1")
    dt.add_sentence("John is a boxer")
    print()
    dt.sentences()
    print()
    dt.readings(threaded=True)
    print()
    dt = DiscourseTester(
        ["A student dances", "Every student is a person"], reading_command
    )
    print()
    dt.add_sentence("No person dances", consistchk=True)
    print()
    dt.readings()
    print()
    dt.retract_sentence("No person dances", verbose=True)
    print()
    dt.models()
    print()
    dt.readings("A person dances")
    print()
    dt.add_sentence("A person dances", informchk=True)
    dt = DiscourseTester(
        ["Vincent is a boxer", "Fido is a boxer", "Vincent is married", "Fido barks"],
        reading_command,
    )
    dt.readings(filter=True)
    import nltk.data

    background_file = os.path.join("grammars", "book_grammars", "background.fol")
    background = nltk.data.load(background_file)

    print()
    dt.add_background(background, verbose=False)
    dt.background()
    print()
    dt.readings(filter=True)
    print()
    dt.models()


def drt_discourse_demo(reading_command=None):
    """
    Illustrate the various methods of ``DiscourseTester``
    """
    dt = DiscourseTester(["every dog chases a boy", "he runs"], reading_command)
    dt.models()
    print()
    dt.sentences()
    print()
    dt.readings()
    print()
    dt.readings(show_thread_readings=True)
    print()
    dt.readings(filter=True, show_thread_readings=True)


def spacer(num=30):
    print("-" * num)


def demo():
    discourse_demo()

    tagger = RegexpTagger(
        [
            ("^(chases|runs)$", "VB"),
            ("^(a)$", "ex_quant"),
            ("^(every)$", "univ_quant"),
            ("^(dog|boy)$", "NN"),
            ("^(he)$", "PRP"),
        ]
    )
    depparser = MaltParser(tagger=tagger)
    drt_discourse_demo(
        DrtGlueReadingCommand(remove_duplicates=False, depparser=depparser)
    )


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\IPython\utils\text.py ===
"""
Utilities for working with strings and text.

Inheritance diagram:

.. inheritance-diagram:: IPython.utils.text
   :parts: 3
"""

import os
import re
import string
import sys
import textwrap
import warnings
from string import Formatter
from pathlib import Path

from typing import (
    List,
    Dict,
    Tuple,
    Optional,
    cast,
    Sequence,
    Mapping,
    Any,
    Union,
    Callable,
    Iterator,
    TypeVar,
)

if sys.version_info < (3, 12):
    from typing_extensions import Self
else:
    from typing import Self


class LSString(str):
    """String derivative with a special access attributes.

    These are normal strings, but with the special attributes:

        .l (or .list) : value as list (split on newlines).
        .n (or .nlstr): original value (the string itself).
        .s (or .spstr): value as whitespace-separated string.
        .p (or .paths): list of path objects (requires path.py package)

    Any values which require transformations are computed only once and
    cached.

    Such strings are very useful to efficiently interact with the shell, which
    typically only understands whitespace-separated options for commands."""

    __list: List[str]
    __spstr: str
    __paths: List[Path]

    def get_list(self) -> List[str]:
        try:
            return self.__list
        except AttributeError:
            self.__list = self.split('\n')
            return self.__list

    l = list = property(get_list)

    def get_spstr(self) -> str:
        try:
            return self.__spstr
        except AttributeError:
            self.__spstr = self.replace('\n',' ')
            return self.__spstr

    s = spstr = property(get_spstr)

    def get_nlstr(self) -> Self:
        return self

    n = nlstr = property(get_nlstr)

    def get_paths(self) -> List[Path]:
        try:
            return self.__paths
        except AttributeError:
            self.__paths = [Path(p) for p in self.split('\n') if os.path.exists(p)]
            return self.__paths

    p = paths = property(get_paths)

# FIXME: We need to reimplement type specific displayhook and then add this
# back as a custom printer. This should also be moved outside utils into the
# core.

# def print_lsstring(arg):
#     """ Prettier (non-repr-like) and more informative printer for LSString """
#     print("LSString (.p, .n, .l, .s available). Value:")
#     print(arg)
#
#
# print_lsstring = result_display.register(LSString)(print_lsstring)


class SList(list):
    """List derivative with a special access attributes.

    These are normal lists, but with the special attributes:

    * .l (or .list) : value as list (the list itself).
    * .n (or .nlstr): value as a string, joined on newlines.
    * .s (or .spstr): value as a string, joined on spaces.
    * .p (or .paths): list of path objects (requires path.py package)

    Any values which require transformations are computed only once and
    cached."""

    __spstr: str
    __nlstr: str
    __paths: List[Path]

    def get_list(self) -> Self:
        return self

    l = list = property(get_list)

    def get_spstr(self) -> str:
        try:
            return self.__spstr
        except AttributeError:
            self.__spstr = ' '.join(self)
            return self.__spstr

    s = spstr = property(get_spstr)

    def get_nlstr(self) -> str:
        try:
            return self.__nlstr
        except AttributeError:
            self.__nlstr = '\n'.join(self)
            return self.__nlstr

    n = nlstr = property(get_nlstr)

    def get_paths(self) -> List[Path]:
        try:
            return self.__paths
        except AttributeError:
            self.__paths = [Path(p) for p in self if os.path.exists(p)]
            return self.__paths

    p = paths = property(get_paths)

    def grep(
        self,
        pattern: Union[str, Callable[[Any], re.Match[str] | None]],
        prune: bool = False,
        field: Optional[int] = None,
    ) -> Self:
        """Return all strings matching 'pattern' (a regex or callable)

        This is case-insensitive. If prune is true, return all items
        NOT matching the pattern.

        If field is specified, the match must occur in the specified
        whitespace-separated field.

        Examples::

            a.grep( lambda x: x.startswith('C') )
            a.grep('Cha.*log', prune=1)
            a.grep('chm', field=-1)
        """

        def match_target(s: str) -> str:
            if field is None:
                return s
            parts = s.split()
            try:
                tgt = parts[field]
                return tgt
            except IndexError:
                return ""

        if isinstance(pattern, str):
            pred = lambda x : re.search(pattern, x, re.IGNORECASE)
        else:
            pred = pattern
        if not prune:
            return type(self)([el for el in self if pred(match_target(el))])
        else:
            return type(self)([el for el in self if not pred(match_target(el))])

    def fields(self, *fields: List[str]) -> List[List[str]]:
        """Collect whitespace-separated fields from string list

        Allows quick awk-like usage of string lists.

        Example data (in var a, created by 'a = !ls -l')::

            -rwxrwxrwx  1 ville None      18 Dec 14  2006 ChangeLog
            drwxrwxrwx+ 6 ville None       0 Oct 24 18:05 IPython

        * ``a.fields(0)`` is ``['-rwxrwxrwx', 'drwxrwxrwx+']``
        * ``a.fields(1,0)`` is ``['1 -rwxrwxrwx', '6 drwxrwxrwx+']``
          (note the joining by space).
        * ``a.fields(-1)`` is ``['ChangeLog', 'IPython']``

        IndexErrors are ignored.

        Without args, fields() just split()'s the strings.
        """
        if len(fields) == 0:
            return [el.split() for el in self]

        res = SList()
        for el in [f.split() for f in self]:
            lineparts = []

            for fd in fields:
                try:
                    lineparts.append(el[fd])
                except IndexError:
                    pass
            if lineparts:
                res.append(" ".join(lineparts))

        return res

    def sort(  # type:ignore[override]
        self,
        field: Optional[List[str]] = None,
        nums: bool = False,
    ) -> Self:
        """sort by specified fields (see fields())

        Example::

            a.sort(1, nums = True)

        Sorts a by second field, in numerical order (so that 21 > 3)

        """

        #decorate, sort, undecorate
        if field is not None:
            dsu = [[SList([line]).fields(field),  line] for line in self]
        else:
            dsu = [[line,  line] for line in self]
        if nums:
            for i in range(len(dsu)):
                numstr = "".join([ch for ch in dsu[i][0] if ch.isdigit()])
                try:
                    n = int(numstr)
                except ValueError:
                    n = 0
                dsu[i][0] = n


        dsu.sort()
        return type(self)([t[1] for t in dsu])


def indent(instr: str, nspaces: int = 4, ntabs: int = 0, flatten: bool = False) -> str:
    """Indent a string a given number of spaces or tabstops.

    indent(str, nspaces=4, ntabs=0) -> indent str by ntabs+nspaces.

    Parameters
    ----------
    instr : basestring
        The string to be indented.
    nspaces : int (default: 4)
        The number of spaces to be indented.
    ntabs : int (default: 0)
        The number of tabs to be indented.
    flatten : bool (default: False)
        Whether to scrub existing indentation.  If True, all lines will be
        aligned to the same indentation.  If False, existing indentation will
        be strictly increased.

    Returns
    -------
    str : string indented by ntabs and nspaces.

    """
    ind = "\t" * ntabs + " " * nspaces
    if flatten:
        pat = re.compile(r'^\s*', re.MULTILINE)
    else:
        pat = re.compile(r'^', re.MULTILINE)
    outstr = re.sub(pat, ind, instr)
    if outstr.endswith(os.linesep+ind):
        return outstr[:-len(ind)]
    else:
        return outstr


def list_strings(arg: Union[str, List[str]]) -> List[str]:
    """Always return a list of strings, given a string or list of strings
    as input.

    Examples
    --------
    ::

        In [7]: list_strings('A single string')
        Out[7]: ['A single string']

        In [8]: list_strings(['A single string in a list'])
        Out[8]: ['A single string in a list']

        In [9]: list_strings(['A','list','of','strings'])
        Out[9]: ['A', 'list', 'of', 'strings']
    """

    if isinstance(arg, str):
        return [arg]
    else:
        return arg


def marquee(txt: str = "", width: int = 78, mark: str = "*") -> str:
    """Return the input string centered in a 'marquee'.

    Examples
    --------
    ::

        In [16]: marquee('A test',40)
        Out[16]: '**************** A test ****************'

        In [17]: marquee('A test',40,'-')
        Out[17]: '---------------- A test ----------------'

        In [18]: marquee('A test',40,' ')
        Out[18]: '                 A test                 '

    """
    if not txt:
        return (mark*width)[:width]
    nmark = (width-len(txt)-2)//len(mark)//2
    if nmark < 0: nmark =0
    marks = mark*nmark
    return '%s %s %s' % (marks,txt,marks)


def format_screen(strng: str) -> str:
    """Format a string for screen printing.

    This removes some latex-type format codes."""
    # Paragraph continue
    par_re = re.compile(r'\\$',re.MULTILINE)
    strng = par_re.sub('',strng)
    return strng


def dedent(text: str) -> str:
    """Equivalent of textwrap.dedent that ignores unindented first line.

    This means it will still dedent strings like:
    '''foo
    is a bar
    '''

    For use in wrap_paragraphs.
    """

    if text.startswith('\n'):
        # text starts with blank line, don't ignore the first line
        return textwrap.dedent(text)

    # split first line
    splits = text.split('\n',1)
    if len(splits) == 1:
        # only one line
        return textwrap.dedent(text)

    first, rest = splits
    # dedent everything but the first line
    rest = textwrap.dedent(rest)
    return '\n'.join([first, rest])


def strip_email_quotes(text: str) -> str:
    """Strip leading email quotation characters ('>').

    Removes any combination of leading '>' interspersed with whitespace that
    appears *identically* in all lines of the input text.

    Parameters
    ----------
    text : str

    Examples
    --------

    Simple uses::

        In [2]: strip_email_quotes('> > text')
        Out[2]: 'text'

        In [3]: strip_email_quotes('> > text\\n> > more')
        Out[3]: 'text\\nmore'

    Note how only the common prefix that appears in all lines is stripped::

        In [4]: strip_email_quotes('> > text\\n> > more\\n> more...')
        Out[4]: '> text\\n> more\\nmore...'

    So if any line has no quote marks ('>'), then none are stripped from any
    of them ::

        In [5]: strip_email_quotes('> > text\\n> > more\\nlast different')
        Out[5]: '> > text\\n> > more\\nlast different'
    """
    lines = text.splitlines()
    strip_len = 0

    for characters in zip(*lines):
        # Check if all characters in this position are the same
        if len(set(characters)) > 1:
            break
        prefix_char = characters[0]

        if prefix_char in string.whitespace or prefix_char == ">":
            strip_len += 1
        else:
            break

    text = "\n".join([ln[strip_len:] for ln in lines])
    return text


class EvalFormatter(Formatter):
    """A String Formatter that allows evaluation of simple expressions.

    Note that this version interprets a `:`  as specifying a format string (as per
    standard string formatting), so if slicing is required, you must explicitly
    create a slice.

    This is to be used in templating cases, such as the parallel batch
    script templates, where simple arithmetic on arguments is useful.

    Examples
    --------
    ::

        In [1]: f = EvalFormatter()
        In [2]: f.format('{n//4}', n=8)
        Out[2]: '2'

        In [3]: f.format("{greeting[slice(2,4)]}", greeting="Hello")
        Out[3]: 'll'
    """

    def get_field(self, name: str, args: Any, kwargs: Any) -> Tuple[Any, str]:
        v = eval(name, kwargs)
        return v, name

#XXX: As of Python 3.4, the format string parsing no longer splits on a colon
# inside [], so EvalFormatter can handle slicing. Once we only support 3.4 and
# above, it should be possible to remove FullEvalFormatter.

class FullEvalFormatter(Formatter):
    """A String Formatter that allows evaluation of simple expressions.
    
    Any time a format key is not found in the kwargs,
    it will be tried as an expression in the kwargs namespace.
    
    Note that this version allows slicing using [1:2], so you cannot specify
    a format string. Use :class:`EvalFormatter` to permit format strings.
    
    Examples
    --------
    ::

        In [1]: f = FullEvalFormatter()
        In [2]: f.format('{n//4}', n=8)
        Out[2]: '2'

        In [3]: f.format('{list(range(5))[2:4]}')
        Out[3]: '[2, 3]'

        In [4]: f.format('{3*2}')
        Out[4]: '6'
    """
    # copied from Formatter._vformat with minor changes to allow eval
    # and replace the format_spec code with slicing
    def vformat(
        self, format_string: str, args: Sequence[Any], kwargs: Mapping[str, Any]
    ) -> str:
        result = []
        conversion: Optional[str]
        for literal_text, field_name, format_spec, conversion in self.parse(
            format_string
        ):
            # output the literal text
            if literal_text:
                result.append(literal_text)

            # if there's a field, output it
            if field_name is not None:
                # this is some markup, find the object and do
                # the formatting

                if format_spec:
                    # override format spec, to allow slicing:
                    field_name = ':'.join([field_name, format_spec])

                # eval the contents of the field for the object
                # to be formatted
                obj = eval(field_name, dict(kwargs))

                # do any conversion on the resulting object
                # type issue in typeshed, fined in https://github.com/python/typeshed/pull/11377
                obj = self.convert_field(obj, conversion)  # type: ignore[arg-type]

                # format the object and append to the result
                result.append(self.format_field(obj, ''))

        return ''.join(result)


class DollarFormatter(FullEvalFormatter):
    """Formatter allowing Itpl style $foo replacement, for names and attribute
    access only. Standard {foo} replacement also works, and allows full
    evaluation of its arguments.

    Examples
    --------
    ::

        In [1]: f = DollarFormatter()
        In [2]: f.format('{n//4}', n=8)
        Out[2]: '2'

        In [3]: f.format('23 * 76 is $result', result=23*76)
        Out[3]: '23 * 76 is 1748'

        In [4]: f.format('$a or {b}', a=1, b=2)
        Out[4]: '1 or 2'
    """

    _dollar_pattern_ignore_single_quote = re.compile(
        r"(.*?)\$(\$?[\w\.]+)(?=([^']*'[^']*')*[^']*$)"
    )

    def parse(self, fmt_string: str) -> Iterator[Tuple[Any, Any, Any, Any]]:  # type: ignore[explicit-override]
        for literal_txt, field_name, format_spec, conversion in Formatter.parse(
            self, fmt_string
        ):
            # Find $foo patterns in the literal text.
            continue_from = 0
            txt = ""
            for m in self._dollar_pattern_ignore_single_quote.finditer(literal_txt):
                new_txt, new_field = m.group(1,2)
                # $$foo --> $foo
                if new_field.startswith("$"):
                    txt += new_txt + new_field
                else:
                    yield (txt + new_txt, new_field, "", None)
                    txt = ""
                continue_from = m.end()
            
            # Re-yield the {foo} style pattern
            yield (txt + literal_txt[continue_from:], field_name, format_spec, conversion)

    def __repr__(self) -> str:
        return "<DollarFormatter>"

#-----------------------------------------------------------------------------
# Utils to columnize a list of string
#-----------------------------------------------------------------------------


def _col_chunks(
    l: List[int], max_rows: int, row_first: bool = False
) -> Iterator[List[int]]:
    """Yield successive max_rows-sized column chunks from l."""
    if row_first:
        ncols = (len(l) // max_rows) + (len(l) % max_rows > 0)
        for i in range(ncols):
            yield [l[j] for j in range(i, len(l), ncols)]
    else:
        for i in range(0, len(l), max_rows):
            yield l[i:(i + max_rows)]


def _find_optimal(
    rlist: List[int], row_first: bool, separator_size: int, displaywidth: int
) -> Dict[str, Any]:
    """Calculate optimal info to columnize a list of string"""
    for max_rows in range(1, len(rlist) + 1):
        col_widths = list(map(max, _col_chunks(rlist, max_rows, row_first)))
        sumlength = sum(col_widths)
        ncols = len(col_widths)
        if sumlength + separator_size * (ncols - 1) <= displaywidth:
            break
    return {'num_columns': ncols,
            'optimal_separator_width': (displaywidth - sumlength) // (ncols - 1) if (ncols - 1) else 0,
            'max_rows': max_rows,
            'column_widths': col_widths
            }


T = TypeVar("T")


def _get_or_default(mylist: List[T], i: int, default: T) -> T:
    """return list item number, or default if don't exist"""
    if i >= len(mylist):
        return default
    else :
        return mylist[i]


def get_text_list(
    list_: List[str], last_sep: str = " and ", sep: str = ", ", wrap_item_with: str = ""
) -> str:
    """
    Return a string with a natural enumeration of items

    >>> get_text_list(['a', 'b', 'c', 'd'])
    'a, b, c and d'
    >>> get_text_list(['a', 'b', 'c'], ' or ')
    'a, b or c'
    >>> get_text_list(['a', 'b', 'c'], ', ')
    'a, b, c'
    >>> get_text_list(['a', 'b'], ' or ')
    'a or b'
    >>> get_text_list(['a'])
    'a'
    >>> get_text_list([])
    ''
    >>> get_text_list(['a', 'b'], wrap_item_with="`")
    '`a` and `b`'
    >>> get_text_list(['a', 'b', 'c', 'd'], " = ", sep=" + ")
    'a + b + c = d'
    """
    if len(list_) == 0:
        return ''
    if wrap_item_with:
        list_ = ['%s%s%s' % (wrap_item_with, item, wrap_item_with) for
                 item in list_]
    if len(list_) == 1:
        return list_[0]
    return '%s%s%s' % (
        sep.join(i for i in list_[:-1]),
        last_sep, list_[-1])

# === NexusCore/openenv\Lib\site-packages\fontTools\t1Lib\__init__.py ===
"""fontTools.t1Lib.py -- Tools for PostScript Type 1 fonts.

Functions for reading and writing raw Type 1 data:

read(path)
	reads any Type 1 font file, returns the raw data and a type indicator:
	'LWFN', 'PFB' or 'OTHER', depending on the format of the file pointed
	to by 'path'.
	Raises an error when the file does not contain valid Type 1 data.

write(path, data, kind='OTHER', dohex=False)
	writes raw Type 1 data to the file pointed to by 'path'.
	'kind' can be one of 'LWFN', 'PFB' or 'OTHER'; it defaults to 'OTHER'.
	'dohex' is a flag which determines whether the eexec encrypted
	part should be written as hexadecimal or binary, but only if kind
	is 'OTHER'.
"""

import fontTools
from fontTools.misc import eexec
from fontTools.misc.macCreatorType import getMacCreatorAndType
from fontTools.misc.textTools import bytechr, byteord, bytesjoin, tobytes
from fontTools.misc.psOperators import (
    _type1_pre_eexec_order,
    _type1_fontinfo_order,
    _type1_post_eexec_order,
)
from fontTools.encodings.StandardEncoding import StandardEncoding
import os
import re

__author__ = "jvr"
__version__ = "1.0b3"
DEBUG = 0


try:
    try:
        from Carbon import Res
    except ImportError:
        import Res  # MacPython < 2.2
except ImportError:
    haveMacSupport = 0
else:
    haveMacSupport = 1


class T1Error(Exception):
    pass


class T1Font(object):
    """Type 1 font class.

    Uses a minimal interpeter that supports just about enough PS to parse
    Type 1 fonts.
    """

    def __init__(self, path, encoding="ascii", kind=None):
        if kind is None:
            self.data, _ = read(path)
        elif kind == "LWFN":
            self.data = readLWFN(path)
        elif kind == "PFB":
            self.data = readPFB(path)
        elif kind == "OTHER":
            self.data = readOther(path)
        else:
            raise ValueError(kind)
        self.encoding = encoding

    def saveAs(self, path, type, dohex=False):
        write(path, self.getData(), type, dohex)

    def getData(self):
        if not hasattr(self, "data"):
            self.data = self.createData()
        return self.data

    def getGlyphSet(self):
        """Return a generic GlyphSet, which is a dict-like object
        mapping glyph names to glyph objects. The returned glyph objects
        have a .draw() method that supports the Pen protocol, and will
        have an attribute named 'width', but only *after* the .draw() method
        has been called.

        In the case of Type 1, the GlyphSet is simply the CharStrings dict.
        """
        return self["CharStrings"]

    def __getitem__(self, key):
        if not hasattr(self, "font"):
            self.parse()
        return self.font[key]

    def parse(self):
        from fontTools.misc import psLib
        from fontTools.misc import psCharStrings

        self.font = psLib.suckfont(self.data, self.encoding)
        charStrings = self.font["CharStrings"]
        lenIV = self.font["Private"].get("lenIV", 4)
        assert lenIV >= 0
        subrs = self.font["Private"]["Subrs"]
        for glyphName, charString in charStrings.items():
            charString, R = eexec.decrypt(charString, 4330)
            charStrings[glyphName] = psCharStrings.T1CharString(
                charString[lenIV:], subrs=subrs
            )
        for i in range(len(subrs)):
            charString, R = eexec.decrypt(subrs[i], 4330)
            subrs[i] = psCharStrings.T1CharString(charString[lenIV:], subrs=subrs)
        del self.data

    def createData(self):
        sf = self.font

        eexec_began = False
        eexec_dict = {}
        lines = []
        lines.extend(
            [
                self._tobytes(f"%!FontType1-1.1: {sf['FontName']}"),
                self._tobytes(f"%t1Font: ({fontTools.version})"),
                self._tobytes(f"%%BeginResource: font {sf['FontName']}"),
            ]
        )
        # follow t1write.c:writeRegNameKeyedFont
        size = 3  # Headroom for new key addition
        size += 1  # FontMatrix is always counted
        size += 1 + 1  # Private, CharStings
        for key in font_dictionary_keys:
            size += int(key in sf)
        lines.append(self._tobytes(f"{size} dict dup begin"))

        for key, value in sf.items():
            if eexec_began:
                eexec_dict[key] = value
                continue

            if key == "FontInfo":
                fi = sf["FontInfo"]
                # follow t1write.c:writeFontInfoDict
                size = 3  # Headroom for new key addition
                for subkey in FontInfo_dictionary_keys:
                    size += int(subkey in fi)
                lines.append(self._tobytes(f"/FontInfo {size} dict dup begin"))

                for subkey, subvalue in fi.items():
                    lines.extend(self._make_lines(subkey, subvalue))
                lines.append(b"end def")
            elif key in _type1_post_eexec_order:  # usually 'Private'
                eexec_dict[key] = value
                eexec_began = True
            else:
                lines.extend(self._make_lines(key, value))
        lines.append(b"end")
        eexec_portion = self.encode_eexec(eexec_dict)
        lines.append(bytesjoin([b"currentfile eexec ", eexec_portion]))

        for _ in range(8):
            lines.append(self._tobytes("0" * 64))
        lines.extend([b"cleartomark", b"%%EndResource", b"%%EOF"])

        data = bytesjoin(lines, "\n")
        return data

    def encode_eexec(self, eexec_dict):
        lines = []

        # '-|', '|-', '|'
        RD_key, ND_key, NP_key = None, None, None
        lenIV = 4
        subrs = std_subrs

        # Ensure we look at Private first, because we need RD_key, ND_key, NP_key and lenIV
        sortedItems = sorted(eexec_dict.items(), key=lambda item: item[0] != "Private")

        for key, value in sortedItems:
            if key == "Private":
                pr = eexec_dict["Private"]
                # follow t1write.c:writePrivateDict
                size = 3  # for RD, ND, NP
                for subkey in Private_dictionary_keys:
                    size += int(subkey in pr)
                lines.append(b"dup /Private")
                lines.append(self._tobytes(f"{size} dict dup begin"))
                for subkey, subvalue in pr.items():
                    if not RD_key and subvalue == RD_value:
                        RD_key = subkey
                    elif not ND_key and subvalue in ND_values:
                        ND_key = subkey
                    elif not NP_key and subvalue in PD_values:
                        NP_key = subkey

                    if subkey == "lenIV":
                        lenIV = subvalue

                    if subkey == "OtherSubrs":
                        # XXX: assert that no flex hint is used
                        lines.append(self._tobytes(hintothers))
                    elif subkey == "Subrs":
                        for subr_bin in subvalue:
                            subr_bin.compile()
                        subrs = [subr_bin.bytecode for subr_bin in subvalue]
                        lines.append(f"/Subrs {len(subrs)} array".encode("ascii"))
                        for i, subr_bin in enumerate(subrs):
                            encrypted_subr, R = eexec.encrypt(
                                bytesjoin([char_IV[:lenIV], subr_bin]), 4330
                            )
                            lines.append(
                                bytesjoin(
                                    [
                                        self._tobytes(
                                            f"dup {i} {len(encrypted_subr)} {RD_key} "
                                        ),
                                        encrypted_subr,
                                        self._tobytes(f" {NP_key}"),
                                    ]
                                )
                            )
                        lines.append(b"def")

                        lines.append(b"put")
                    else:
                        lines.extend(self._make_lines(subkey, subvalue))
            elif key == "CharStrings":
                lines.append(b"dup /CharStrings")
                lines.append(
                    self._tobytes(f"{len(eexec_dict['CharStrings'])} dict dup begin")
                )
                for glyph_name, char_bin in eexec_dict["CharStrings"].items():
                    char_bin.compile()
                    encrypted_char, R = eexec.encrypt(
                        bytesjoin([char_IV[:lenIV], char_bin.bytecode]), 4330
                    )
                    lines.append(
                        bytesjoin(
                            [
                                self._tobytes(
                                    f"/{glyph_name} {len(encrypted_char)} {RD_key} "
                                ),
                                encrypted_char,
                                self._tobytes(f" {ND_key}"),
                            ]
                        )
                    )
                lines.append(b"end put")
            else:
                lines.extend(self._make_lines(key, value))

        lines.extend(
            [
                b"end",
                b"dup /FontName get exch definefont pop",
                b"mark",
                b"currentfile closefile\n",
            ]
        )

        eexec_portion = bytesjoin(lines, "\n")
        encrypted_eexec, R = eexec.encrypt(bytesjoin([eexec_IV, eexec_portion]), 55665)

        return encrypted_eexec

    def _make_lines(self, key, value):
        if key == "FontName":
            return [self._tobytes(f"/{key} /{value} def")]
        if key in ["isFixedPitch", "ForceBold", "RndStemUp"]:
            return [self._tobytes(f"/{key} {'true' if value else 'false'} def")]
        elif key == "Encoding":
            if value == StandardEncoding:
                return [self._tobytes(f"/{key} StandardEncoding def")]
            else:
                # follow fontTools.misc.psOperators._type1_Encoding_repr
                lines = []
                lines.append(b"/Encoding 256 array")
                lines.append(b"0 1 255 {1 index exch /.notdef put} for")
                for i in range(256):
                    name = value[i]
                    if name != ".notdef":
                        lines.append(self._tobytes(f"dup {i} /{name} put"))
                lines.append(b"def")
                return lines
        if isinstance(value, str):
            return [self._tobytes(f"/{key} ({value}) def")]
        elif isinstance(value, bool):
            return [self._tobytes(f"/{key} {'true' if value else 'false'} def")]
        elif isinstance(value, list):
            return [self._tobytes(f"/{key} [{' '.join(str(v) for v in value)}] def")]
        elif isinstance(value, tuple):
            return [self._tobytes(f"/{key} {{{' '.join(str(v) for v in value)}}} def")]
        else:
            return [self._tobytes(f"/{key} {value} def")]

    def _tobytes(self, s, errors="strict"):
        return tobytes(s, self.encoding, errors)


# low level T1 data read and write functions


def read(path, onlyHeader=False):
    """reads any Type 1 font file, returns raw data"""
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    creator, typ = getMacCreatorAndType(path)
    if typ == "LWFN":
        return readLWFN(path, onlyHeader), "LWFN"
    if ext == ".pfb":
        return readPFB(path, onlyHeader), "PFB"
    else:
        return readOther(path), "OTHER"


def write(path, data, kind="OTHER", dohex=False):
    assertType1(data)
    kind = kind.upper()
    try:
        os.remove(path)
    except os.error:
        pass
    err = 1
    try:
        if kind == "LWFN":
            writeLWFN(path, data)
        elif kind == "PFB":
            writePFB(path, data)
        else:
            writeOther(path, data, dohex)
        err = 0
    finally:
        if err and not DEBUG:
            try:
                os.remove(path)
            except os.error:
                pass


# -- internal --

LWFNCHUNKSIZE = 2000
HEXLINELENGTH = 80


def readLWFN(path, onlyHeader=False):
    """reads an LWFN font file, returns raw data"""
    from fontTools.misc.macRes import ResourceReader

    reader = ResourceReader(path)
    try:
        data = []
        for res in reader.get("POST", []):
            code = byteord(res.data[0])
            if byteord(res.data[1]) != 0:
                raise T1Error("corrupt LWFN file")
            if code in [1, 2]:
                if onlyHeader and code == 2:
                    break
                data.append(res.data[2:])
            elif code in [3, 5]:
                break
            elif code == 4:
                with open(path, "rb") as f:
                    data.append(f.read())
            elif code == 0:
                pass  # comment, ignore
            else:
                raise T1Error("bad chunk code: " + repr(code))
    finally:
        reader.close()
    data = bytesjoin(data)
    assertType1(data)
    return data


def readPFB(path, onlyHeader=False):
    """reads a PFB font file, returns raw data"""
    data = []
    with open(path, "rb") as f:
        while True:
            if f.read(1) != bytechr(128):
                raise T1Error("corrupt PFB file")
            code = byteord(f.read(1))
            if code in [1, 2]:
                chunklen = stringToLong(f.read(4))
                chunk = f.read(chunklen)
                assert len(chunk) == chunklen
                data.append(chunk)
            elif code == 3:
                break
            else:
                raise T1Error("bad chunk code: " + repr(code))
            if onlyHeader:
                break
    data = bytesjoin(data)
    assertType1(data)
    return data


def readOther(path):
    """reads any (font) file, returns raw data"""
    with open(path, "rb") as f:
        data = f.read()
    assertType1(data)
    chunks = findEncryptedChunks(data)
    data = []
    for isEncrypted, chunk in chunks:
        if isEncrypted and isHex(chunk[:4]):
            data.append(deHexString(chunk))
        else:
            data.append(chunk)
    return bytesjoin(data)


# file writing tools


def writeLWFN(path, data):
    # Res.FSpCreateResFile was deprecated in OS X 10.5
    Res.FSpCreateResFile(path, "just", "LWFN", 0)
    resRef = Res.FSOpenResFile(path, 2)  # write-only
    try:
        Res.UseResFile(resRef)
        resID = 501
        chunks = findEncryptedChunks(data)
        for isEncrypted, chunk in chunks:
            if isEncrypted:
                code = 2
            else:
                code = 1
            while chunk:
                res = Res.Resource(bytechr(code) + "\0" + chunk[: LWFNCHUNKSIZE - 2])
                res.AddResource("POST", resID, "")
                chunk = chunk[LWFNCHUNKSIZE - 2 :]
                resID = resID + 1
        res = Res.Resource(bytechr(5) + "\0")
        res.AddResource("POST", resID, "")
    finally:
        Res.CloseResFile(resRef)


def writePFB(path, data):
    chunks = findEncryptedChunks(data)
    with open(path, "wb") as f:
        for isEncrypted, chunk in chunks:
            if isEncrypted:
                code = 2
            else:
                code = 1
            f.write(bytechr(128) + bytechr(code))
            f.write(longToString(len(chunk)))
            f.write(chunk)
        f.write(bytechr(128) + bytechr(3))


def writeOther(path, data, dohex=False):
    chunks = findEncryptedChunks(data)
    with open(path, "wb") as f:
        hexlinelen = HEXLINELENGTH // 2
        for isEncrypted, chunk in chunks:
            if isEncrypted:
                code = 2
            else:
                code = 1
            if code == 2 and dohex:
                while chunk:
                    f.write(eexec.hexString(chunk[:hexlinelen]))
                    f.write(b"\r")
                    chunk = chunk[hexlinelen:]
            else:
                f.write(chunk)


# decryption tools

EEXECBEGIN = b"currentfile eexec"
# The spec allows for 512 ASCII zeros interrupted by arbitrary whitespace to
# follow eexec
EEXECEND = re.compile(b"(0[ \t\r\n]*){512}", flags=re.M)
EEXECINTERNALEND = b"currentfile closefile"
EEXECBEGINMARKER = b"%-- eexec start\r"
EEXECENDMARKER = b"%-- eexec end\r"

_ishexRE = re.compile(b"[0-9A-Fa-f]*$")


def isHex(text):
    return _ishexRE.match(text) is not None


def decryptType1(data):
    chunks = findEncryptedChunks(data)
    data = []
    for isEncrypted, chunk in chunks:
        if isEncrypted:
            if isHex(chunk[:4]):
                chunk = deHexString(chunk)
            decrypted, R = eexec.decrypt(chunk, 55665)
            decrypted = decrypted[4:]
            if (
                decrypted[-len(EEXECINTERNALEND) - 1 : -1] != EEXECINTERNALEND
                and decrypted[-len(EEXECINTERNALEND) - 2 : -2] != EEXECINTERNALEND
            ):
                raise T1Error("invalid end of eexec part")
            decrypted = decrypted[: -len(EEXECINTERNALEND) - 2] + b"\r"
            data.append(EEXECBEGINMARKER + decrypted + EEXECENDMARKER)
        else:
            if chunk[-len(EEXECBEGIN) - 1 : -1] == EEXECBEGIN:
                data.append(chunk[: -len(EEXECBEGIN) - 1])
            else:
                data.append(chunk)
    return bytesjoin(data)


def findEncryptedChunks(data):
    chunks = []
    while True:
        eBegin = data.find(EEXECBEGIN)
        if eBegin < 0:
            break
        eBegin = eBegin + len(EEXECBEGIN) + 1
        endMatch = EEXECEND.search(data, eBegin)
        if endMatch is None:
            raise T1Error("can't find end of eexec part")
        eEnd = endMatch.start()
        cypherText = data[eBegin : eEnd + 2]
        if isHex(cypherText[:4]):
            cypherText = deHexString(cypherText)
        plainText, R = eexec.decrypt(cypherText, 55665)
        eEndLocal = plainText.find(EEXECINTERNALEND)
        if eEndLocal < 0:
            raise T1Error("can't find end of eexec part")
        chunks.append((0, data[:eBegin]))
        chunks.append((1, cypherText[: eEndLocal + len(EEXECINTERNALEND) + 1]))
        data = data[eEnd:]
    chunks.append((0, data))
    return chunks


def deHexString(hexstring):
    return eexec.deHexString(bytesjoin(hexstring.split()))


# Type 1 assertion

_fontType1RE = re.compile(rb"/FontType\s+1\s+def")


def assertType1(data):
    for head in [b"%!PS-AdobeFont", b"%!FontType1"]:
        if data[: len(head)] == head:
            break
    else:
        raise T1Error("not a PostScript font")
    if not _fontType1RE.search(data):
        raise T1Error("not a Type 1 font")
    if data.find(b"currentfile eexec") < 0:
        raise T1Error("not an encrypted Type 1 font")
    # XXX what else?
    return data


# pfb helpers


def longToString(long):
    s = b""
    for i in range(4):
        s += bytechr((long & (0xFF << (i * 8))) >> i * 8)
    return s


def stringToLong(s):
    if len(s) != 4:
        raise ValueError("string must be 4 bytes long")
    l = 0
    for i in range(4):
        l += byteord(s[i]) << (i * 8)
    return l


# PS stream helpers

font_dictionary_keys = list(_type1_pre_eexec_order)
# t1write.c:writeRegNameKeyedFont
# always counts following keys
font_dictionary_keys.remove("FontMatrix")

FontInfo_dictionary_keys = list(_type1_fontinfo_order)
# extend because AFDKO tx may use following keys
FontInfo_dictionary_keys.extend(
    [
        "FSType",
        "Copyright",
    ]
)

Private_dictionary_keys = [
    # We don't know what names will be actually used.
    # "RD",
    # "ND",
    # "NP",
    "Subrs",
    "OtherSubrs",
    "UniqueID",
    "BlueValues",
    "OtherBlues",
    "FamilyBlues",
    "FamilyOtherBlues",
    "BlueScale",
    "BlueShift",
    "BlueFuzz",
    "StdHW",
    "StdVW",
    "StemSnapH",
    "StemSnapV",
    "ForceBold",
    "LanguageGroup",
    "password",
    "lenIV",
    "MinFeature",
    "RndStemUp",
]

# t1write_hintothers.h
hintothers = """/OtherSubrs[{}{}{}{systemdict/internaldict known not{pop 3}{1183615869
systemdict/internaldict get exec dup/startlock known{/startlock get exec}{dup
/strtlck known{/strtlck get exec}{pop 3}ifelse}ifelse}ifelse}executeonly]def"""
# t1write.c:saveStdSubrs
std_subrs = [
    # 3 0 callother pop pop setcurrentpoint return
    b"\x8e\x8b\x0c\x10\x0c\x11\x0c\x11\x0c\x21\x0b",
    # 0 1 callother return
    b"\x8b\x8c\x0c\x10\x0b",
    # 0 2 callother return
    b"\x8b\x8d\x0c\x10\x0b",
    # return
    b"\x0b",
    # 3 1 3 callother pop callsubr return
    b"\x8e\x8c\x8e\x0c\x10\x0c\x11\x0a\x0b",
]
# follow t1write.c:writeRegNameKeyedFont
eexec_IV = b"cccc"
char_IV = b"\x0c\x0c\x0c\x0c"
RD_value = ("string", "currentfile", "exch", "readstring", "pop")
ND_values = [("def",), ("noaccess", "def")]
PD_values = [("put",), ("noaccess", "put")]

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_stan_builtins.py ===
"""
    pygments.lexers._stan_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This file contains the names of functions for Stan used by
    ``pygments.lexers.math.StanLexer. This is for Stan language version 2.29.0.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

KEYWORDS = (
    'break',
    'continue',
    'else',
    'for',
    'if',
    'in',
    'print',
    'reject',
    'return',
    'while',
)

TYPES = (
    'cholesky_factor_corr',
    'cholesky_factor_cov',
    'corr_matrix',
    'cov_matrix',
    'int',
    'matrix',
    'ordered',
    'positive_ordered',
    'real',
    'row_vector',
    'simplex',
    'unit_vector',
    'vector',
    'void',
    'array',
    'complex'
)

FUNCTIONS = (
    'abs',
    'acos',
    'acosh',
    'add_diag',
    'algebra_solver',
    'algebra_solver_newton',
    'append_array',
    'append_col',
    'append_row',
    'arg',
    'asin',
    'asinh',
    'atan',
    'atan2',
    'atanh',
    'bernoulli_cdf',
    'bernoulli_lccdf',
    'bernoulli_lcdf',
    'bernoulli_logit_glm_lpmf',
    'bernoulli_logit_glm_lupmf',
    'bernoulli_logit_glm_rng',
    'bernoulli_logit_lpmf',
    'bernoulli_logit_lupmf',
    'bernoulli_logit_rng',
    'bernoulli_lpmf',
    'bernoulli_lupmf',
    'bernoulli_rng',
    'bessel_first_kind',
    'bessel_second_kind',
    'beta',
    'beta_binomial_cdf',
    'beta_binomial_lccdf',
    'beta_binomial_lcdf',
    'beta_binomial_lpmf',
    'beta_binomial_lupmf',
    'beta_binomial_rng',
    'beta_cdf',
    'beta_lccdf',
    'beta_lcdf',
    'beta_lpdf',
    'beta_lupdf',
    'beta_proportion_lccdf',
    'beta_proportion_lcdf',
    'beta_proportion_rng',
    'beta_rng',
    'binary_log_loss',
    'binomial_cdf',
    'binomial_coefficient_log',
    'binomial_lccdf',
    'binomial_lcdf',
    'binomial_logit_lpmf',
    'binomial_logit_lupmf',
    'binomial_lpmf',
    'binomial_lupmf',
    'binomial_rng',
    'block',
    'categorical_logit_glm_lpmf',
    'categorical_logit_glm_lupmf',
    'categorical_logit_lpmf',
    'categorical_logit_lupmf',
    'categorical_logit_rng',
    'categorical_lpmf',
    'categorical_lupmf',
    'categorical_rng',
    'cauchy_cdf',
    'cauchy_lccdf',
    'cauchy_lcdf',
    'cauchy_lpdf',
    'cauchy_lupdf',
    'cauchy_rng',
    'cbrt',
    'ceil',
    'chi_square_cdf',
    'chi_square_lccdf',
    'chi_square_lcdf',
    'chi_square_lpdf',
    'chi_square_lupdf',
    'chi_square_rng',
    'chol2inv',
    'cholesky_decompose',
    'choose',
    'col',
    'cols',
    'columns_dot_product',
    'columns_dot_self',
    'conj',
    'cos',
    'cosh',
    'cov_exp_quad',
    'crossprod',
    'csr_extract_u',
    'csr_extract_v',
    'csr_extract_w',
    'csr_matrix_times_vector',
    'csr_to_dense_matrix',
    'cumulative_sum',
    'dae',
    'dae_tol',
    'determinant',
    'diag_matrix',
    'diag_post_multiply',
    'diag_pre_multiply',
    'diagonal',
    'digamma',
    'dims',
    'dirichlet_lpdf',
    'dirichlet_lupdf',
    'dirichlet_rng',
    'discrete_range_cdf',
    'discrete_range_lccdf',
    'discrete_range_lcdf',
    'discrete_range_lpmf',
    'discrete_range_lupmf',
    'discrete_range_rng',
    'distance',
    'dot_product',
    'dot_self',
    'double_exponential_cdf',
    'double_exponential_lccdf',
    'double_exponential_lcdf',
    'double_exponential_lpdf',
    'double_exponential_lupdf',
    'double_exponential_rng',
    'e',
    'eigenvalues_sym',
    'eigenvectors_sym',
    'erf',
    'erfc',
    'exp',
    'exp2',
    'exp_mod_normal_cdf',
    'exp_mod_normal_lccdf',
    'exp_mod_normal_lcdf',
    'exp_mod_normal_lpdf',
    'exp_mod_normal_lupdf',
    'exp_mod_normal_rng',
    'expm1',
    'exponential_cdf',
    'exponential_lccdf',
    'exponential_lcdf',
    'exponential_lpdf',
    'exponential_lupdf',
    'exponential_rng',
    'fabs',
    'falling_factorial',
    'fdim',
    'floor',
    'fma',
    'fmax',
    'fmin',
    'fmod',
    'frechet_cdf',
    'frechet_lccdf',
    'frechet_lcdf',
    'frechet_lpdf',
    'frechet_lupdf',
    'frechet_rng',
    'gamma_cdf',
    'gamma_lccdf',
    'gamma_lcdf',
    'gamma_lpdf',
    'gamma_lupdf',
    'gamma_p',
    'gamma_q',
    'gamma_rng',
    'gaussian_dlm_obs_lpdf',
    'gaussian_dlm_obs_lupdf',
    'generalized_inverse',
    'get_imag',
    'get_lp',
    'get_real',
    'gumbel_cdf',
    'gumbel_lccdf',
    'gumbel_lcdf',
    'gumbel_lpdf',
    'gumbel_lupdf',
    'gumbel_rng',
    'head',
    'hmm_hidden_state_prob',
    'hmm_latent_rng',
    'hmm_marginal',
    'hypergeometric_lpmf',
    'hypergeometric_lupmf',
    'hypergeometric_rng',
    'hypot',
    'identity_matrix',
    'inc_beta',
    'int_step',
    'integrate_1d',
    'integrate_ode',
    'integrate_ode_adams',
    'integrate_ode_bdf',
    'integrate_ode_rk45',
    'inv',
    'inv_chi_square_cdf',
    'inv_chi_square_lccdf',
    'inv_chi_square_lcdf',
    'inv_chi_square_lpdf',
    'inv_chi_square_lupdf',
    'inv_chi_square_rng',
    'inv_cloglog',
    'inv_erfc',
    'inv_gamma_cdf',
    'inv_gamma_lccdf',
    'inv_gamma_lcdf',
    'inv_gamma_lpdf',
    'inv_gamma_lupdf',
    'inv_gamma_rng',
    'inv_logit',
    'inv_Phi',
    'inv_sqrt',
    'inv_square',
    'inv_wishart_lpdf',
    'inv_wishart_lupdf',
    'inv_wishart_rng',
    'inverse',
    'inverse_spd',
    'is_inf',
    'is_nan',
    'lambert_w0',
    'lambert_wm1',
    'lbeta',
    'lchoose',
    'ldexp',
    'lgamma',
    'linspaced_array',
    'linspaced_int_array',
    'linspaced_row_vector',
    'linspaced_vector',
    'lkj_corr_cholesky_lpdf',
    'lkj_corr_cholesky_lupdf',
    'lkj_corr_cholesky_rng',
    'lkj_corr_lpdf',
    'lkj_corr_lupdf',
    'lkj_corr_rng',
    'lmgamma',
    'lmultiply',
    'log',
    'log10',
    'log1m',
    'log1m_exp',
    'log1m_inv_logit',
    'log1p',
    'log1p_exp',
    'log2',
    'log_determinant',
    'log_diff_exp',
    'log_falling_factorial',
    'log_inv_logit',
    'log_inv_logit_diff',
    'log_mix',
    'log_modified_bessel_first_kind',
    'log_rising_factorial',
    'log_softmax',
    'log_sum_exp',
    'logistic_cdf',
    'logistic_lccdf',
    'logistic_lcdf',
    'logistic_lpdf',
    'logistic_lupdf',
    'logistic_rng',
    'logit',
    'loglogistic_cdf',
    'loglogistic_lpdf',
    'loglogistic_rng',
    'lognormal_cdf',
    'lognormal_lccdf',
    'lognormal_lcdf',
    'lognormal_lpdf',
    'lognormal_lupdf',
    'lognormal_rng',
    'machine_precision',
    'map_rect',
    'matrix_exp',
    'matrix_exp_multiply',
    'matrix_power',
    'max',
    'mdivide_left_spd',
    'mdivide_left_tri_low',
    'mdivide_right_spd',
    'mdivide_right_tri_low',
    'mean',
    'min',
    'modified_bessel_first_kind',
    'modified_bessel_second_kind',
    'multi_gp_cholesky_lpdf',
    'multi_gp_cholesky_lupdf',
    'multi_gp_lpdf',
    'multi_gp_lupdf',
    'multi_normal_cholesky_lpdf',
    'multi_normal_cholesky_lupdf',
    'multi_normal_cholesky_rng',
    'multi_normal_lpdf',
    'multi_normal_lupdf',
    'multi_normal_prec_lpdf',
    'multi_normal_prec_lupdf',
    'multi_normal_rng',
    'multi_student_t_lpdf',
    'multi_student_t_lupdf',
    'multi_student_t_rng',
    'multinomial_logit_lpmf',
    'multinomial_logit_lupmf',
    'multinomial_logit_rng',
    'multinomial_lpmf',
    'multinomial_lupmf',
    'multinomial_rng',
    'multiply_log',
    'multiply_lower_tri_self_transpose',
    'neg_binomial_2_cdf',
    'neg_binomial_2_lccdf',
    'neg_binomial_2_lcdf',
    'neg_binomial_2_log_glm_lpmf',
    'neg_binomial_2_log_glm_lupmf',
    'neg_binomial_2_log_lpmf',
    'neg_binomial_2_log_lupmf',
    'neg_binomial_2_log_rng',
    'neg_binomial_2_lpmf',
    'neg_binomial_2_lupmf',
    'neg_binomial_2_rng',
    'neg_binomial_cdf',
    'neg_binomial_lccdf',
    'neg_binomial_lcdf',
    'neg_binomial_lpmf',
    'neg_binomial_lupmf',
    'neg_binomial_rng',
    'negative_infinity',
    'norm',
    'normal_cdf',
    'normal_id_glm_lpdf',
    'normal_id_glm_lupdf',
    'normal_lccdf',
    'normal_lcdf',
    'normal_lpdf',
    'normal_lupdf',
    'normal_rng',
    'not_a_number',
    'num_elements',
    'ode_adams',
    'ode_adams_tol',
    'ode_adjoint_tol_ctl',
    'ode_bdf',
    'ode_bdf_tol',
    'ode_ckrk',
    'ode_ckrk_tol',
    'ode_rk45',
    'ode_rk45_tol',
    'one_hot_array',
    'one_hot_int_array',
    'one_hot_row_vector',
    'one_hot_vector',
    'ones_array',
    'ones_int_array',
    'ones_row_vector',
    'ones_vector',
    'ordered_logistic_glm_lpmf',
    'ordered_logistic_glm_lupmf',
    'ordered_logistic_lpmf',
    'ordered_logistic_lupmf',
    'ordered_logistic_rng',
    'ordered_probit_lpmf',
    'ordered_probit_lupmf',
    'ordered_probit_rng',
    'owens_t',
    'pareto_cdf',
    'pareto_lccdf',
    'pareto_lcdf',
    'pareto_lpdf',
    'pareto_lupdf',
    'pareto_rng',
    'pareto_type_2_cdf',
    'pareto_type_2_lccdf',
    'pareto_type_2_lcdf',
    'pareto_type_2_lpdf',
    'pareto_type_2_lupdf',
    'pareto_type_2_rng',
    'Phi',
    'Phi_approx',
    'pi',
    'poisson_cdf',
    'poisson_lccdf',
    'poisson_lcdf',
    'poisson_log_glm_lpmf',
    'poisson_log_glm_lupmf',
    'poisson_log_lpmf',
    'poisson_log_lupmf',
    'poisson_log_rng',
    'poisson_lpmf',
    'poisson_lupmf',
    'poisson_rng',
    'polar',
    'positive_infinity',
    'pow',
    'print',
    'prod',
    'proj',
    'qr_Q',
    'qr_R',
    'qr_thin_Q',
    'qr_thin_R',
    'quad_form',
    'quad_form_diag',
    'quad_form_sym',
    'quantile',
    'rank',
    'rayleigh_cdf',
    'rayleigh_lccdf',
    'rayleigh_lcdf',
    'rayleigh_lpdf',
    'rayleigh_lupdf',
    'rayleigh_rng',
    'reduce_sum',
    'reject',
    'rep_array',
    'rep_matrix',
    'rep_row_vector',
    'rep_vector',
    'reverse',
    'rising_factorial',
    'round',
    'row',
    'rows',
    'rows_dot_product',
    'rows_dot_self',
    'scale_matrix_exp_multiply',
    'scaled_inv_chi_square_cdf',
    'scaled_inv_chi_square_lccdf',
    'scaled_inv_chi_square_lcdf',
    'scaled_inv_chi_square_lpdf',
    'scaled_inv_chi_square_lupdf',
    'scaled_inv_chi_square_rng',
    'sd',
    'segment',
    'sin',
    'singular_values',
    'sinh',
    'size',
    'skew_double_exponential_cdf',
    'skew_double_exponential_lccdf',
    'skew_double_exponential_lcdf',
    'skew_double_exponential_lpdf',
    'skew_double_exponential_lupdf',
    'skew_double_exponential_rng',
    'skew_normal_cdf',
    'skew_normal_lccdf',
    'skew_normal_lcdf',
    'skew_normal_lpdf',
    'skew_normal_lupdf',
    'skew_normal_rng',
    'softmax',
    'sort_asc',
    'sort_desc',
    'sort_indices_asc',
    'sort_indices_desc',
    'sqrt',
    'sqrt2',
    'square',
    'squared_distance',
    'std_normal_cdf',
    'std_normal_lccdf',
    'std_normal_lcdf',
    'std_normal_lpdf',
    'std_normal_lupdf',
    'std_normal_rng',
    'step',
    'student_t_cdf',
    'student_t_lccdf',
    'student_t_lcdf',
    'student_t_lpdf',
    'student_t_lupdf',
    'student_t_rng',
    'sub_col',
    'sub_row',
    'sum',
    'svd_U',
    'svd_V',
    'symmetrize_from_lower_tri',
    'tail',
    'tan',
    'tanh',
    'target',
    'tcrossprod',
    'tgamma',
    'to_array_1d',
    'to_array_2d',
    'to_complex',
    'to_matrix',
    'to_row_vector',
    'to_vector',
    'trace',
    'trace_gen_quad_form',
    'trace_quad_form',
    'trigamma',
    'trunc',
    'uniform_cdf',
    'uniform_lccdf',
    'uniform_lcdf',
    'uniform_lpdf',
    'uniform_lupdf',
    'uniform_rng',
    'uniform_simplex',
    'variance',
    'von_mises_cdf',
    'von_mises_lccdf',
    'von_mises_lcdf',
    'von_mises_lpdf',
    'von_mises_lupdf',
    'von_mises_rng',
    'weibull_cdf',
    'weibull_lccdf',
    'weibull_lcdf',
    'weibull_lpdf',
    'weibull_lupdf',
    'weibull_rng',
    'wiener_lpdf',
    'wiener_lupdf',
    'wishart_lpdf',
    'wishart_lupdf',
    'wishart_rng',
    'zeros_array',
    'zeros_int_array',
    'zeros_row_vector'
)

DISTRIBUTIONS = (
    'bernoulli',
    'bernoulli_logit',
    'bernoulli_logit_glm',
    'beta',
    'beta_binomial',
    'binomial',
    'binomial_logit',
    'categorical',
    'categorical_logit',
    'categorical_logit_glm',
    'cauchy',
    'chi_square',
    'dirichlet',
    'discrete_range',
    'double_exponential',
    'exp_mod_normal',
    'exponential',
    'frechet',
    'gamma',
    'gaussian_dlm_obs',
    'gumbel',
    'hypergeometric',
    'inv_chi_square',
    'inv_gamma',
    'inv_wishart',
    'lkj_corr',
    'lkj_corr_cholesky',
    'logistic',
    'loglogistic',
    'lognormal',
    'multi_gp',
    'multi_gp_cholesky',
    'multi_normal',
    'multi_normal_cholesky',
    'multi_normal_prec',
    'multi_student_t',
    'multinomial',
    'multinomial_logit',
    'neg_binomial',
    'neg_binomial_2',
    'neg_binomial_2_log',
    'neg_binomial_2_log_glm',
    'normal',
    'normal_id_glm',
    'ordered_logistic',
    'ordered_logistic_glm',
    'ordered_probit',
    'pareto',
    'pareto_type_2',
    'poisson',
    'poisson_log',
    'poisson_log_glm',
    'rayleigh',
    'scaled_inv_chi_square',
    'skew_double_exponential',
    'skew_normal',
    'std_normal',
    'student_t',
    'uniform',
    'von_mises',
    'weibull',
    'wiener',
    'wishart',
)

RESERVED = (
    'repeat',
    'until',
    'then',
    'true',
    'false',
    'var',
    'struct',
    'typedef',
    'export',
    'auto',
    'extern',
    'var',
    'static',
)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\accessibility.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Accessibility (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import page
from . import runtime


class AXNodeId(str):
    '''
    Unique accessibility node identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> AXNodeId:
        return cls(json)

    def __repr__(self):
        return 'AXNodeId({})'.format(super().__repr__())


class AXValueType(enum.Enum):
    '''
    Enum of possible property types.
    '''
    BOOLEAN = "boolean"
    TRISTATE = "tristate"
    BOOLEAN_OR_UNDEFINED = "booleanOrUndefined"
    IDREF = "idref"
    IDREF_LIST = "idrefList"
    INTEGER = "integer"
    NODE = "node"
    NODE_LIST = "nodeList"
    NUMBER = "number"
    STRING = "string"
    COMPUTED_STRING = "computedString"
    TOKEN = "token"
    TOKEN_LIST = "tokenList"
    DOM_RELATION = "domRelation"
    ROLE = "role"
    INTERNAL_ROLE = "internalRole"
    VALUE_UNDEFINED = "valueUndefined"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AXValueSourceType(enum.Enum):
    '''
    Enum of possible property sources.
    '''
    ATTRIBUTE = "attribute"
    IMPLICIT = "implicit"
    STYLE = "style"
    CONTENTS = "contents"
    PLACEHOLDER = "placeholder"
    RELATED_ELEMENT = "relatedElement"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AXValueNativeSourceType(enum.Enum):
    '''
    Enum of possible native property sources (as a subtype of a particular AXValueSourceType).
    '''
    DESCRIPTION = "description"
    FIGCAPTION = "figcaption"
    LABEL = "label"
    LABELFOR = "labelfor"
    LABELWRAPPED = "labelwrapped"
    LEGEND = "legend"
    RUBYANNOTATION = "rubyannotation"
    TABLECAPTION = "tablecaption"
    TITLE = "title"
    OTHER = "other"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AXValueSource:
    '''
    A single source for a computed AX property.
    '''
    #: What type of source this is.
    type_: AXValueSourceType

    #: The value of this property source.
    value: typing.Optional[AXValue] = None

    #: The name of the relevant attribute, if any.
    attribute: typing.Optional[str] = None

    #: The value of the relevant attribute, if any.
    attribute_value: typing.Optional[AXValue] = None

    #: Whether this source is superseded by a higher priority source.
    superseded: typing.Optional[bool] = None

    #: The native markup source for this value, e.g. a ``<label>`` element.
    native_source: typing.Optional[AXValueNativeSourceType] = None

    #: The value, such as a node or node list, of the native source.
    native_source_value: typing.Optional[AXValue] = None

    #: Whether the value for this property is invalid.
    invalid: typing.Optional[bool] = None

    #: Reason for the value being invalid, if it is.
    invalid_reason: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_.to_json()
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.attribute is not None:
            json['attribute'] = self.attribute
        if self.attribute_value is not None:
            json['attributeValue'] = self.attribute_value.to_json()
        if self.superseded is not None:
            json['superseded'] = self.superseded
        if self.native_source is not None:
            json['nativeSource'] = self.native_source.to_json()
        if self.native_source_value is not None:
            json['nativeSourceValue'] = self.native_source_value.to_json()
        if self.invalid is not None:
            json['invalid'] = self.invalid
        if self.invalid_reason is not None:
            json['invalidReason'] = self.invalid_reason
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=AXValueSourceType.from_json(json['type']),
            value=AXValue.from_json(json['value']) if 'value' in json else None,
            attribute=str(json['attribute']) if 'attribute' in json else None,
            attribute_value=AXValue.from_json(json['attributeValue']) if 'attributeValue' in json else None,
            superseded=bool(json['superseded']) if 'superseded' in json else None,
            native_source=AXValueNativeSourceType.from_json(json['nativeSource']) if 'nativeSource' in json else None,
            native_source_value=AXValue.from_json(json['nativeSourceValue']) if 'nativeSourceValue' in json else None,
            invalid=bool(json['invalid']) if 'invalid' in json else None,
            invalid_reason=str(json['invalidReason']) if 'invalidReason' in json else None,
        )


@dataclass
class AXRelatedNode:
    #: The BackendNodeId of the related DOM node.
    backend_dom_node_id: dom.BackendNodeId

    #: The IDRef value provided, if any.
    idref: typing.Optional[str] = None

    #: The text alternative of this node in the current context.
    text: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['backendDOMNodeId'] = self.backend_dom_node_id.to_json()
        if self.idref is not None:
            json['idref'] = self.idref
        if self.text is not None:
            json['text'] = self.text
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            backend_dom_node_id=dom.BackendNodeId.from_json(json['backendDOMNodeId']),
            idref=str(json['idref']) if 'idref' in json else None,
            text=str(json['text']) if 'text' in json else None,
        )


@dataclass
class AXProperty:
    #: The name of this property.
    name: AXPropertyName

    #: The value of this property.
    value: AXValue

    def to_json(self):
        json = dict()
        json['name'] = self.name.to_json()
        json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=AXPropertyName.from_json(json['name']),
            value=AXValue.from_json(json['value']),
        )


@dataclass
class AXValue:
    '''
    A single computed AX property.
    '''
    #: The type of this value.
    type_: AXValueType

    #: The computed value of this property.
    value: typing.Optional[typing.Any] = None

    #: One or more related nodes, if applicable.
    related_nodes: typing.Optional[typing.List[AXRelatedNode]] = None

    #: The sources which contributed to the computation of this property.
    sources: typing.Optional[typing.List[AXValueSource]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_.to_json()
        if self.value is not None:
            json['value'] = self.value
        if self.related_nodes is not None:
            json['relatedNodes'] = [i.to_json() for i in self.related_nodes]
        if self.sources is not None:
            json['sources'] = [i.to_json() for i in self.sources]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=AXValueType.from_json(json['type']),
            value=json['value'] if 'value' in json else None,
            related_nodes=[AXRelatedNode.from_json(i) for i in json['relatedNodes']] if 'relatedNodes' in json else None,
            sources=[AXValueSource.from_json(i) for i in json['sources']] if 'sources' in json else None,
        )


class AXPropertyName(enum.Enum):
    '''
    Values of AXProperty name:
    - from 'busy' to 'roledescription': states which apply to every AX node
    - from 'live' to 'root': attributes which apply to nodes in live regions
    - from 'autocomplete' to 'valuetext': attributes which apply to widgets
    - from 'checked' to 'selected': states which apply to widgets
    - from 'activedescendant' to 'owns' - relationships between elements other than parent/child/sibling.
    '''
    ACTIONS = "actions"
    BUSY = "busy"
    DISABLED = "disabled"
    EDITABLE = "editable"
    FOCUSABLE = "focusable"
    FOCUSED = "focused"
    HIDDEN = "hidden"
    HIDDEN_ROOT = "hiddenRoot"
    INVALID = "invalid"
    KEYSHORTCUTS = "keyshortcuts"
    SETTABLE = "settable"
    ROLEDESCRIPTION = "roledescription"
    LIVE = "live"
    ATOMIC = "atomic"
    RELEVANT = "relevant"
    ROOT = "root"
    AUTOCOMPLETE = "autocomplete"
    HAS_POPUP = "hasPopup"
    LEVEL = "level"
    MULTISELECTABLE = "multiselectable"
    ORIENTATION = "orientation"
    MULTILINE = "multiline"
    READONLY = "readonly"
    REQUIRED = "required"
    VALUEMIN = "valuemin"
    VALUEMAX = "valuemax"
    VALUETEXT = "valuetext"
    CHECKED = "checked"
    EXPANDED = "expanded"
    MODAL = "modal"
    PRESSED = "pressed"
    SELECTED = "selected"
    ACTIVEDESCENDANT = "activedescendant"
    CONTROLS = "controls"
    DESCRIBEDBY = "describedby"
    DETAILS = "details"
    ERRORMESSAGE = "errormessage"
    FLOWTO = "flowto"
    LABELLEDBY = "labelledby"
    OWNS = "owns"
    URL = "url"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AXNode:
    '''
    A node in the accessibility tree.
    '''
    #: Unique identifier for this node.
    node_id: AXNodeId

    #: Whether this node is ignored for accessibility
    ignored: bool

    #: Collection of reasons why this node is hidden.
    ignored_reasons: typing.Optional[typing.List[AXProperty]] = None

    #: This ``Node``'s role, whether explicit or implicit.
    role: typing.Optional[AXValue] = None

    #: This ``Node``'s Chrome raw role.
    chrome_role: typing.Optional[AXValue] = None

    #: The accessible name for this ``Node``.
    name: typing.Optional[AXValue] = None

    #: The accessible description for this ``Node``.
    description: typing.Optional[AXValue] = None

    #: The value for this ``Node``.
    value: typing.Optional[AXValue] = None

    #: All other properties
    properties: typing.Optional[typing.List[AXProperty]] = None

    #: ID for this node's parent.
    parent_id: typing.Optional[AXNodeId] = None

    #: IDs for each of this node's child nodes.
    child_ids: typing.Optional[typing.List[AXNodeId]] = None

    #: The backend ID for the associated DOM node, if any.
    backend_dom_node_id: typing.Optional[dom.BackendNodeId] = None

    #: The frame ID for the frame associated with this nodes document.
    frame_id: typing.Optional[page.FrameId] = None

    def to_json(self):
        json = dict()
        json['nodeId'] = self.node_id.to_json()
        json['ignored'] = self.ignored
        if self.ignored_reasons is not None:
            json['ignoredReasons'] = [i.to_json() for i in self.ignored_reasons]
        if self.role is not None:
            json['role'] = self.role.to_json()
        if self.chrome_role is not None:
            json['chromeRole'] = self.chrome_role.to_json()
        if self.name is not None:
            json['name'] = self.name.to_json()
        if self.description is not None:
            json['description'] = self.description.to_json()
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.properties is not None:
            json['properties'] = [i.to_json() for i in self.properties]
        if self.parent_id is not None:
            json['parentId'] = self.parent_id.to_json()
        if self.child_ids is not None:
            json['childIds'] = [i.to_json() for i in self.child_ids]
        if self.backend_dom_node_id is not None:
            json['backendDOMNodeId'] = self.backend_dom_node_id.to_json()
        if self.frame_id is not None:
            json['frameId'] = self.frame_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            node_id=AXNodeId.from_json(json['nodeId']),
            ignored=bool(json['ignored']),
            ignored_reasons=[AXProperty.from_json(i) for i in json['ignoredReasons']] if 'ignoredReasons' in json else None,
            role=AXValue.from_json(json['role']) if 'role' in json else None,
            chrome_role=AXValue.from_json(json['chromeRole']) if 'chromeRole' in json else None,
            name=AXValue.from_json(json['name']) if 'name' in json else None,
            description=AXValue.from_json(json['description']) if 'description' in json else None,
            value=AXValue.from_json(json['value']) if 'value' in json else None,
            properties=[AXProperty.from_json(i) for i in json['properties']] if 'properties' in json else None,
            parent_id=AXNodeId.from_json(json['parentId']) if 'parentId' in json else None,
            child_ids=[AXNodeId.from_json(i) for i in json['childIds']] if 'childIds' in json else None,
            backend_dom_node_id=dom.BackendNodeId.from_json(json['backendDOMNodeId']) if 'backendDOMNodeId' in json else None,
            frame_id=page.FrameId.from_json(json['frameId']) if 'frameId' in json else None,
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables the accessibility domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables the accessibility domain which causes ``AXNodeId``'s to remain consistent between method calls.
    This turns on accessibility for the page, which can impact performance until accessibility is disabled.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.enable',
    }
    json = yield cmd_dict


def get_partial_ax_tree(
        node_id: typing.Optional[dom.NodeId] = None,
        backend_node_id: typing.Optional[dom.BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None,
        fetch_relatives: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches the accessibility node and partial accessibility tree for this DOM node, if it exists.

    **EXPERIMENTAL**

    :param node_id: *(Optional)* Identifier of the node to get the partial accessibility tree for.
    :param backend_node_id: *(Optional)* Identifier of the backend node to get the partial accessibility tree for.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper to get the partial accessibility tree for.
    :param fetch_relatives: *(Optional)* Whether to fetch this node's ancestors, siblings and children. Defaults to true.
    :returns: The ``Accessibility.AXNode`` for this DOM node, if it exists, plus its ancestors, siblings and children, if requested.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    if fetch_relatives is not None:
        params['fetchRelatives'] = fetch_relatives
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getPartialAXTree',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def get_full_ax_tree(
        depth: typing.Optional[int] = None,
        frame_id: typing.Optional[page.FrameId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches the entire accessibility tree for the root Document

    **EXPERIMENTAL**

    :param depth: *(Optional)* The maximum depth at which descendants of the root node should be retrieved. If omitted, the full tree is returned.
    :param frame_id: *(Optional)* The frame for whose document the AX tree should be retrieved. If omitted, the root frame is used.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if depth is not None:
        params['depth'] = depth
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getFullAXTree',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def get_root_ax_node(
        frame_id: typing.Optional[page.FrameId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,AXNode]:
    '''
    Fetches the root node.
    Requires ``enable()`` to have been called previously.

    **EXPERIMENTAL**

    :param frame_id: *(Optional)* The frame in whose document the node resides. If omitted, the root frame is used.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getRootAXNode',
        'params': params,
    }
    json = yield cmd_dict
    return AXNode.from_json(json['node'])


def get_ax_node_and_ancestors(
        node_id: typing.Optional[dom.NodeId] = None,
        backend_node_id: typing.Optional[dom.BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches a node and all ancestors up to and including the root.
    Requires ``enable()`` to have been called previously.

    **EXPERIMENTAL**

    :param node_id: *(Optional)* Identifier of the node to get.
    :param backend_node_id: *(Optional)* Identifier of the backend node to get.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper to get.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getAXNodeAndAncestors',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def get_child_ax_nodes(
        id_: AXNodeId,
        frame_id: typing.Optional[page.FrameId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches a particular accessibility node by AXNodeId.
    Requires ``enable()`` to have been called previously.

    **EXPERIMENTAL**

    :param id_:
    :param frame_id: *(Optional)* The frame in whose document the node resides. If omitted, the root frame is used.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_.to_json()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getChildAXNodes',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def query_ax_tree(
        node_id: typing.Optional[dom.NodeId] = None,
        backend_node_id: typing.Optional[dom.BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None,
        accessible_name: typing.Optional[str] = None,
        role: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Query a DOM node's accessibility subtree for accessible name and role.
    This command computes the name and role for all nodes in the subtree, including those that are
    ignored for accessibility, and returns those that match the specified name and role. If no DOM
    node is specified, or the DOM node does not exist, the command returns an error. If neither
    ``accessibleName`` or ``role`` is specified, it returns all the accessibility nodes in the subtree.

    **EXPERIMENTAL**

    :param node_id: *(Optional)* Identifier of the node for the root to query.
    :param backend_node_id: *(Optional)* Identifier of the backend node for the root to query.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper for the root to query.
    :param accessible_name: *(Optional)* Find nodes with this computed name.
    :param role: *(Optional)* Find nodes with this computed role.
    :returns: A list of ``Accessibility.AXNode`` matching the specified attributes, including nodes that are ignored for accessibility.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    if accessible_name is not None:
        params['accessibleName'] = accessible_name
    if role is not None:
        params['role'] = role
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.queryAXTree',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


@event_class('Accessibility.loadComplete')
@dataclass
class LoadComplete:
    '''
    **EXPERIMENTAL**

    The loadComplete event mirrors the load complete event sent by the browser to assistive
    technology when the web page has finished loading.
    '''
    #: New document root node.
    root: AXNode

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LoadComplete:
        return cls(
            root=AXNode.from_json(json['root'])
        )


@event_class('Accessibility.nodesUpdated')
@dataclass
class NodesUpdated:
    '''
    **EXPERIMENTAL**

    The nodesUpdated event is sent every time a previously requested node has changed the in tree.
    '''
    #: Updated node data.
    nodes: typing.List[AXNode]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> NodesUpdated:
        return cls(
            nodes=[AXNode.from_json(i) for i in json['nodes']]
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\accessibility.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Accessibility (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import page
from . import runtime


class AXNodeId(str):
    '''
    Unique accessibility node identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> AXNodeId:
        return cls(json)

    def __repr__(self):
        return 'AXNodeId({})'.format(super().__repr__())


class AXValueType(enum.Enum):
    '''
    Enum of possible property types.
    '''
    BOOLEAN = "boolean"
    TRISTATE = "tristate"
    BOOLEAN_OR_UNDEFINED = "booleanOrUndefined"
    IDREF = "idref"
    IDREF_LIST = "idrefList"
    INTEGER = "integer"
    NODE = "node"
    NODE_LIST = "nodeList"
    NUMBER = "number"
    STRING = "string"
    COMPUTED_STRING = "computedString"
    TOKEN = "token"
    TOKEN_LIST = "tokenList"
    DOM_RELATION = "domRelation"
    ROLE = "role"
    INTERNAL_ROLE = "internalRole"
    VALUE_UNDEFINED = "valueUndefined"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AXValueSourceType(enum.Enum):
    '''
    Enum of possible property sources.
    '''
    ATTRIBUTE = "attribute"
    IMPLICIT = "implicit"
    STYLE = "style"
    CONTENTS = "contents"
    PLACEHOLDER = "placeholder"
    RELATED_ELEMENT = "relatedElement"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AXValueNativeSourceType(enum.Enum):
    '''
    Enum of possible native property sources (as a subtype of a particular AXValueSourceType).
    '''
    DESCRIPTION = "description"
    FIGCAPTION = "figcaption"
    LABEL = "label"
    LABELFOR = "labelfor"
    LABELWRAPPED = "labelwrapped"
    LEGEND = "legend"
    RUBYANNOTATION = "rubyannotation"
    TABLECAPTION = "tablecaption"
    TITLE = "title"
    OTHER = "other"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AXValueSource:
    '''
    A single source for a computed AX property.
    '''
    #: What type of source this is.
    type_: AXValueSourceType

    #: The value of this property source.
    value: typing.Optional[AXValue] = None

    #: The name of the relevant attribute, if any.
    attribute: typing.Optional[str] = None

    #: The value of the relevant attribute, if any.
    attribute_value: typing.Optional[AXValue] = None

    #: Whether this source is superseded by a higher priority source.
    superseded: typing.Optional[bool] = None

    #: The native markup source for this value, e.g. a ``<label>`` element.
    native_source: typing.Optional[AXValueNativeSourceType] = None

    #: The value, such as a node or node list, of the native source.
    native_source_value: typing.Optional[AXValue] = None

    #: Whether the value for this property is invalid.
    invalid: typing.Optional[bool] = None

    #: Reason for the value being invalid, if it is.
    invalid_reason: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_.to_json()
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.attribute is not None:
            json['attribute'] = self.attribute
        if self.attribute_value is not None:
            json['attributeValue'] = self.attribute_value.to_json()
        if self.superseded is not None:
            json['superseded'] = self.superseded
        if self.native_source is not None:
            json['nativeSource'] = self.native_source.to_json()
        if self.native_source_value is not None:
            json['nativeSourceValue'] = self.native_source_value.to_json()
        if self.invalid is not None:
            json['invalid'] = self.invalid
        if self.invalid_reason is not None:
            json['invalidReason'] = self.invalid_reason
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=AXValueSourceType.from_json(json['type']),
            value=AXValue.from_json(json['value']) if 'value' in json else None,
            attribute=str(json['attribute']) if 'attribute' in json else None,
            attribute_value=AXValue.from_json(json['attributeValue']) if 'attributeValue' in json else None,
            superseded=bool(json['superseded']) if 'superseded' in json else None,
            native_source=AXValueNativeSourceType.from_json(json['nativeSource']) if 'nativeSource' in json else None,
            native_source_value=AXValue.from_json(json['nativeSourceValue']) if 'nativeSourceValue' in json else None,
            invalid=bool(json['invalid']) if 'invalid' in json else None,
            invalid_reason=str(json['invalidReason']) if 'invalidReason' in json else None,
        )


@dataclass
class AXRelatedNode:
    #: The BackendNodeId of the related DOM node.
    backend_dom_node_id: dom.BackendNodeId

    #: The IDRef value provided, if any.
    idref: typing.Optional[str] = None

    #: The text alternative of this node in the current context.
    text: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['backendDOMNodeId'] = self.backend_dom_node_id.to_json()
        if self.idref is not None:
            json['idref'] = self.idref
        if self.text is not None:
            json['text'] = self.text
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            backend_dom_node_id=dom.BackendNodeId.from_json(json['backendDOMNodeId']),
            idref=str(json['idref']) if 'idref' in json else None,
            text=str(json['text']) if 'text' in json else None,
        )


@dataclass
class AXProperty:
    #: The name of this property.
    name: AXPropertyName

    #: The value of this property.
    value: AXValue

    def to_json(self):
        json = dict()
        json['name'] = self.name.to_json()
        json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=AXPropertyName.from_json(json['name']),
            value=AXValue.from_json(json['value']),
        )


@dataclass
class AXValue:
    '''
    A single computed AX property.
    '''
    #: The type of this value.
    type_: AXValueType

    #: The computed value of this property.
    value: typing.Optional[typing.Any] = None

    #: One or more related nodes, if applicable.
    related_nodes: typing.Optional[typing.List[AXRelatedNode]] = None

    #: The sources which contributed to the computation of this property.
    sources: typing.Optional[typing.List[AXValueSource]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_.to_json()
        if self.value is not None:
            json['value'] = self.value
        if self.related_nodes is not None:
            json['relatedNodes'] = [i.to_json() for i in self.related_nodes]
        if self.sources is not None:
            json['sources'] = [i.to_json() for i in self.sources]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=AXValueType.from_json(json['type']),
            value=json['value'] if 'value' in json else None,
            related_nodes=[AXRelatedNode.from_json(i) for i in json['relatedNodes']] if 'relatedNodes' in json else None,
            sources=[AXValueSource.from_json(i) for i in json['sources']] if 'sources' in json else None,
        )


class AXPropertyName(enum.Enum):
    '''
    Values of AXProperty name:
    - from 'busy' to 'roledescription': states which apply to every AX node
    - from 'live' to 'root': attributes which apply to nodes in live regions
    - from 'autocomplete' to 'valuetext': attributes which apply to widgets
    - from 'checked' to 'selected': states which apply to widgets
    - from 'activedescendant' to 'owns' - relationships between elements other than parent/child/sibling.
    '''
    ACTIONS = "actions"
    BUSY = "busy"
    DISABLED = "disabled"
    EDITABLE = "editable"
    FOCUSABLE = "focusable"
    FOCUSED = "focused"
    HIDDEN = "hidden"
    HIDDEN_ROOT = "hiddenRoot"
    INVALID = "invalid"
    KEYSHORTCUTS = "keyshortcuts"
    SETTABLE = "settable"
    ROLEDESCRIPTION = "roledescription"
    LIVE = "live"
    ATOMIC = "atomic"
    RELEVANT = "relevant"
    ROOT = "root"
    AUTOCOMPLETE = "autocomplete"
    HAS_POPUP = "hasPopup"
    LEVEL = "level"
    MULTISELECTABLE = "multiselectable"
    ORIENTATION = "orientation"
    MULTILINE = "multiline"
    READONLY = "readonly"
    REQUIRED = "required"
    VALUEMIN = "valuemin"
    VALUEMAX = "valuemax"
    VALUETEXT = "valuetext"
    CHECKED = "checked"
    EXPANDED = "expanded"
    MODAL = "modal"
    PRESSED = "pressed"
    SELECTED = "selected"
    ACTIVEDESCENDANT = "activedescendant"
    CONTROLS = "controls"
    DESCRIBEDBY = "describedby"
    DETAILS = "details"
    ERRORMESSAGE = "errormessage"
    FLOWTO = "flowto"
    LABELLEDBY = "labelledby"
    OWNS = "owns"
    URL = "url"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AXNode:
    '''
    A node in the accessibility tree.
    '''
    #: Unique identifier for this node.
    node_id: AXNodeId

    #: Whether this node is ignored for accessibility
    ignored: bool

    #: Collection of reasons why this node is hidden.
    ignored_reasons: typing.Optional[typing.List[AXProperty]] = None

    #: This ``Node``'s role, whether explicit or implicit.
    role: typing.Optional[AXValue] = None

    #: This ``Node``'s Chrome raw role.
    chrome_role: typing.Optional[AXValue] = None

    #: The accessible name for this ``Node``.
    name: typing.Optional[AXValue] = None

    #: The accessible description for this ``Node``.
    description: typing.Optional[AXValue] = None

    #: The value for this ``Node``.
    value: typing.Optional[AXValue] = None

    #: All other properties
    properties: typing.Optional[typing.List[AXProperty]] = None

    #: ID for this node's parent.
    parent_id: typing.Optional[AXNodeId] = None

    #: IDs for each of this node's child nodes.
    child_ids: typing.Optional[typing.List[AXNodeId]] = None

    #: The backend ID for the associated DOM node, if any.
    backend_dom_node_id: typing.Optional[dom.BackendNodeId] = None

    #: The frame ID for the frame associated with this nodes document.
    frame_id: typing.Optional[page.FrameId] = None

    def to_json(self):
        json = dict()
        json['nodeId'] = self.node_id.to_json()
        json['ignored'] = self.ignored
        if self.ignored_reasons is not None:
            json['ignoredReasons'] = [i.to_json() for i in self.ignored_reasons]
        if self.role is not None:
            json['role'] = self.role.to_json()
        if self.chrome_role is not None:
            json['chromeRole'] = self.chrome_role.to_json()
        if self.name is not None:
            json['name'] = self.name.to_json()
        if self.description is not None:
            json['description'] = self.description.to_json()
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.properties is not None:
            json['properties'] = [i.to_json() for i in self.properties]
        if self.parent_id is not None:
            json['parentId'] = self.parent_id.to_json()
        if self.child_ids is not None:
            json['childIds'] = [i.to_json() for i in self.child_ids]
        if self.backend_dom_node_id is not None:
            json['backendDOMNodeId'] = self.backend_dom_node_id.to_json()
        if self.frame_id is not None:
            json['frameId'] = self.frame_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            node_id=AXNodeId.from_json(json['nodeId']),
            ignored=bool(json['ignored']),
            ignored_reasons=[AXProperty.from_json(i) for i in json['ignoredReasons']] if 'ignoredReasons' in json else None,
            role=AXValue.from_json(json['role']) if 'role' in json else None,
            chrome_role=AXValue.from_json(json['chromeRole']) if 'chromeRole' in json else None,
            name=AXValue.from_json(json['name']) if 'name' in json else None,
            description=AXValue.from_json(json['description']) if 'description' in json else None,
            value=AXValue.from_json(json['value']) if 'value' in json else None,
            properties=[AXProperty.from_json(i) for i in json['properties']] if 'properties' in json else None,
            parent_id=AXNodeId.from_json(json['parentId']) if 'parentId' in json else None,
            child_ids=[AXNodeId.from_json(i) for i in json['childIds']] if 'childIds' in json else None,
            backend_dom_node_id=dom.BackendNodeId.from_json(json['backendDOMNodeId']) if 'backendDOMNodeId' in json else None,
            frame_id=page.FrameId.from_json(json['frameId']) if 'frameId' in json else None,
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables the accessibility domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables the accessibility domain which causes ``AXNodeId``'s to remain consistent between method calls.
    This turns on accessibility for the page, which can impact performance until accessibility is disabled.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.enable',
    }
    json = yield cmd_dict


def get_partial_ax_tree(
        node_id: typing.Optional[dom.NodeId] = None,
        backend_node_id: typing.Optional[dom.BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None,
        fetch_relatives: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches the accessibility node and partial accessibility tree for this DOM node, if it exists.

    **EXPERIMENTAL**

    :param node_id: *(Optional)* Identifier of the node to get the partial accessibility tree for.
    :param backend_node_id: *(Optional)* Identifier of the backend node to get the partial accessibility tree for.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper to get the partial accessibility tree for.
    :param fetch_relatives: *(Optional)* Whether to fetch this node's ancestors, siblings and children. Defaults to true.
    :returns: The ``Accessibility.AXNode`` for this DOM node, if it exists, plus its ancestors, siblings and children, if requested.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    if fetch_relatives is not None:
        params['fetchRelatives'] = fetch_relatives
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getPartialAXTree',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def get_full_ax_tree(
        depth: typing.Optional[int] = None,
        frame_id: typing.Optional[page.FrameId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches the entire accessibility tree for the root Document

    **EXPERIMENTAL**

    :param depth: *(Optional)* The maximum depth at which descendants of the root node should be retrieved. If omitted, the full tree is returned.
    :param frame_id: *(Optional)* The frame for whose document the AX tree should be retrieved. If omitted, the root frame is used.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if depth is not None:
        params['depth'] = depth
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getFullAXTree',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def get_root_ax_node(
        frame_id: typing.Optional[page.FrameId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,AXNode]:
    '''
    Fetches the root node.
    Requires ``enable()`` to have been called previously.

    **EXPERIMENTAL**

    :param frame_id: *(Optional)* The frame in whose document the node resides. If omitted, the root frame is used.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getRootAXNode',
        'params': params,
    }
    json = yield cmd_dict
    return AXNode.from_json(json['node'])


def get_ax_node_and_ancestors(
        node_id: typing.Optional[dom.NodeId] = None,
        backend_node_id: typing.Optional[dom.BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches a node and all ancestors up to and including the root.
    Requires ``enable()`` to have been called previously.

    **EXPERIMENTAL**

    :param node_id: *(Optional)* Identifier of the node to get.
    :param backend_node_id: *(Optional)* Identifier of the backend node to get.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper to get.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getAXNodeAndAncestors',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def get_child_ax_nodes(
        id_: AXNodeId,
        frame_id: typing.Optional[page.FrameId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches a particular accessibility node by AXNodeId.
    Requires ``enable()`` to have been called previously.

    **EXPERIMENTAL**

    :param id_:
    :param frame_id: *(Optional)* The frame in whose document the node resides. If omitted, the root frame is used.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_.to_json()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getChildAXNodes',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def query_ax_tree(
        node_id: typing.Optional[dom.NodeId] = None,
        backend_node_id: typing.Optional[dom.BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None,
        accessible_name: typing.Optional[str] = None,
        role: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Query a DOM node's accessibility subtree for accessible name and role.
    This command computes the name and role for all nodes in the subtree, including those that are
    ignored for accessibility, and returns those that match the specified name and role. If no DOM
    node is specified, or the DOM node does not exist, the command returns an error. If neither
    ``accessibleName`` or ``role`` is specified, it returns all the accessibility nodes in the subtree.

    **EXPERIMENTAL**

    :param node_id: *(Optional)* Identifier of the node for the root to query.
    :param backend_node_id: *(Optional)* Identifier of the backend node for the root to query.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper for the root to query.
    :param accessible_name: *(Optional)* Find nodes with this computed name.
    :param role: *(Optional)* Find nodes with this computed role.
    :returns: A list of ``Accessibility.AXNode`` matching the specified attributes, including nodes that are ignored for accessibility.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    if accessible_name is not None:
        params['accessibleName'] = accessible_name
    if role is not None:
        params['role'] = role
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.queryAXTree',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


@event_class('Accessibility.loadComplete')
@dataclass
class LoadComplete:
    '''
    **EXPERIMENTAL**

    The loadComplete event mirrors the load complete event sent by the browser to assistive
    technology when the web page has finished loading.
    '''
    #: New document root node.
    root: AXNode

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LoadComplete:
        return cls(
            root=AXNode.from_json(json['root'])
        )


@event_class('Accessibility.nodesUpdated')
@dataclass
class NodesUpdated:
    '''
    **EXPERIMENTAL**

    The nodesUpdated event is sent every time a previously requested node has changed the in tree.
    '''
    #: Updated node data.
    nodes: typing.List[AXNode]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> NodesUpdated:
        return cls(
            nodes=[AXNode.from_json(i) for i in json['nodes']]
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\accessibility.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Accessibility (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import page
from . import runtime


class AXNodeId(str):
    '''
    Unique accessibility node identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> AXNodeId:
        return cls(json)

    def __repr__(self):
        return 'AXNodeId({})'.format(super().__repr__())


class AXValueType(enum.Enum):
    '''
    Enum of possible property types.
    '''
    BOOLEAN = "boolean"
    TRISTATE = "tristate"
    BOOLEAN_OR_UNDEFINED = "booleanOrUndefined"
    IDREF = "idref"
    IDREF_LIST = "idrefList"
    INTEGER = "integer"
    NODE = "node"
    NODE_LIST = "nodeList"
    NUMBER = "number"
    STRING = "string"
    COMPUTED_STRING = "computedString"
    TOKEN = "token"
    TOKEN_LIST = "tokenList"
    DOM_RELATION = "domRelation"
    ROLE = "role"
    INTERNAL_ROLE = "internalRole"
    VALUE_UNDEFINED = "valueUndefined"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AXValueSourceType(enum.Enum):
    '''
    Enum of possible property sources.
    '''
    ATTRIBUTE = "attribute"
    IMPLICIT = "implicit"
    STYLE = "style"
    CONTENTS = "contents"
    PLACEHOLDER = "placeholder"
    RELATED_ELEMENT = "relatedElement"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AXValueNativeSourceType(enum.Enum):
    '''
    Enum of possible native property sources (as a subtype of a particular AXValueSourceType).
    '''
    DESCRIPTION = "description"
    FIGCAPTION = "figcaption"
    LABEL = "label"
    LABELFOR = "labelfor"
    LABELWRAPPED = "labelwrapped"
    LEGEND = "legend"
    RUBYANNOTATION = "rubyannotation"
    TABLECAPTION = "tablecaption"
    TITLE = "title"
    OTHER = "other"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AXValueSource:
    '''
    A single source for a computed AX property.
    '''
    #: What type of source this is.
    type_: AXValueSourceType

    #: The value of this property source.
    value: typing.Optional[AXValue] = None

    #: The name of the relevant attribute, if any.
    attribute: typing.Optional[str] = None

    #: The value of the relevant attribute, if any.
    attribute_value: typing.Optional[AXValue] = None

    #: Whether this source is superseded by a higher priority source.
    superseded: typing.Optional[bool] = None

    #: The native markup source for this value, e.g. a ``<label>`` element.
    native_source: typing.Optional[AXValueNativeSourceType] = None

    #: The value, such as a node or node list, of the native source.
    native_source_value: typing.Optional[AXValue] = None

    #: Whether the value for this property is invalid.
    invalid: typing.Optional[bool] = None

    #: Reason for the value being invalid, if it is.
    invalid_reason: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_.to_json()
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.attribute is not None:
            json['attribute'] = self.attribute
        if self.attribute_value is not None:
            json['attributeValue'] = self.attribute_value.to_json()
        if self.superseded is not None:
            json['superseded'] = self.superseded
        if self.native_source is not None:
            json['nativeSource'] = self.native_source.to_json()
        if self.native_source_value is not None:
            json['nativeSourceValue'] = self.native_source_value.to_json()
        if self.invalid is not None:
            json['invalid'] = self.invalid
        if self.invalid_reason is not None:
            json['invalidReason'] = self.invalid_reason
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=AXValueSourceType.from_json(json['type']),
            value=AXValue.from_json(json['value']) if 'value' in json else None,
            attribute=str(json['attribute']) if 'attribute' in json else None,
            attribute_value=AXValue.from_json(json['attributeValue']) if 'attributeValue' in json else None,
            superseded=bool(json['superseded']) if 'superseded' in json else None,
            native_source=AXValueNativeSourceType.from_json(json['nativeSource']) if 'nativeSource' in json else None,
            native_source_value=AXValue.from_json(json['nativeSourceValue']) if 'nativeSourceValue' in json else None,
            invalid=bool(json['invalid']) if 'invalid' in json else None,
            invalid_reason=str(json['invalidReason']) if 'invalidReason' in json else None,
        )


@dataclass
class AXRelatedNode:
    #: The BackendNodeId of the related DOM node.
    backend_dom_node_id: dom.BackendNodeId

    #: The IDRef value provided, if any.
    idref: typing.Optional[str] = None

    #: The text alternative of this node in the current context.
    text: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['backendDOMNodeId'] = self.backend_dom_node_id.to_json()
        if self.idref is not None:
            json['idref'] = self.idref
        if self.text is not None:
            json['text'] = self.text
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            backend_dom_node_id=dom.BackendNodeId.from_json(json['backendDOMNodeId']),
            idref=str(json['idref']) if 'idref' in json else None,
            text=str(json['text']) if 'text' in json else None,
        )


@dataclass
class AXProperty:
    #: The name of this property.
    name: AXPropertyName

    #: The value of this property.
    value: AXValue

    def to_json(self):
        json = dict()
        json['name'] = self.name.to_json()
        json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=AXPropertyName.from_json(json['name']),
            value=AXValue.from_json(json['value']),
        )


@dataclass
class AXValue:
    '''
    A single computed AX property.
    '''
    #: The type of this value.
    type_: AXValueType

    #: The computed value of this property.
    value: typing.Optional[typing.Any] = None

    #: One or more related nodes, if applicable.
    related_nodes: typing.Optional[typing.List[AXRelatedNode]] = None

    #: The sources which contributed to the computation of this property.
    sources: typing.Optional[typing.List[AXValueSource]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_.to_json()
        if self.value is not None:
            json['value'] = self.value
        if self.related_nodes is not None:
            json['relatedNodes'] = [i.to_json() for i in self.related_nodes]
        if self.sources is not None:
            json['sources'] = [i.to_json() for i in self.sources]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=AXValueType.from_json(json['type']),
            value=json['value'] if 'value' in json else None,
            related_nodes=[AXRelatedNode.from_json(i) for i in json['relatedNodes']] if 'relatedNodes' in json else None,
            sources=[AXValueSource.from_json(i) for i in json['sources']] if 'sources' in json else None,
        )


class AXPropertyName(enum.Enum):
    '''
    Values of AXProperty name:
    - from 'busy' to 'roledescription': states which apply to every AX node
    - from 'live' to 'root': attributes which apply to nodes in live regions
    - from 'autocomplete' to 'valuetext': attributes which apply to widgets
    - from 'checked' to 'selected': states which apply to widgets
    - from 'activedescendant' to 'owns' - relationships between elements other than parent/child/sibling.
    '''
    ACTIONS = "actions"
    BUSY = "busy"
    DISABLED = "disabled"
    EDITABLE = "editable"
    FOCUSABLE = "focusable"
    FOCUSED = "focused"
    HIDDEN = "hidden"
    HIDDEN_ROOT = "hiddenRoot"
    INVALID = "invalid"
    KEYSHORTCUTS = "keyshortcuts"
    SETTABLE = "settable"
    ROLEDESCRIPTION = "roledescription"
    LIVE = "live"
    ATOMIC = "atomic"
    RELEVANT = "relevant"
    ROOT = "root"
    AUTOCOMPLETE = "autocomplete"
    HAS_POPUP = "hasPopup"
    LEVEL = "level"
    MULTISELECTABLE = "multiselectable"
    ORIENTATION = "orientation"
    MULTILINE = "multiline"
    READONLY = "readonly"
    REQUIRED = "required"
    VALUEMIN = "valuemin"
    VALUEMAX = "valuemax"
    VALUETEXT = "valuetext"
    CHECKED = "checked"
    EXPANDED = "expanded"
    MODAL = "modal"
    PRESSED = "pressed"
    SELECTED = "selected"
    ACTIVEDESCENDANT = "activedescendant"
    CONTROLS = "controls"
    DESCRIBEDBY = "describedby"
    DETAILS = "details"
    ERRORMESSAGE = "errormessage"
    FLOWTO = "flowto"
    LABELLEDBY = "labelledby"
    OWNS = "owns"
    URL = "url"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AXNode:
    '''
    A node in the accessibility tree.
    '''
    #: Unique identifier for this node.
    node_id: AXNodeId

    #: Whether this node is ignored for accessibility
    ignored: bool

    #: Collection of reasons why this node is hidden.
    ignored_reasons: typing.Optional[typing.List[AXProperty]] = None

    #: This ``Node``'s role, whether explicit or implicit.
    role: typing.Optional[AXValue] = None

    #: This ``Node``'s Chrome raw role.
    chrome_role: typing.Optional[AXValue] = None

    #: The accessible name for this ``Node``.
    name: typing.Optional[AXValue] = None

    #: The accessible description for this ``Node``.
    description: typing.Optional[AXValue] = None

    #: The value for this ``Node``.
    value: typing.Optional[AXValue] = None

    #: All other properties
    properties: typing.Optional[typing.List[AXProperty]] = None

    #: ID for this node's parent.
    parent_id: typing.Optional[AXNodeId] = None

    #: IDs for each of this node's child nodes.
    child_ids: typing.Optional[typing.List[AXNodeId]] = None

    #: The backend ID for the associated DOM node, if any.
    backend_dom_node_id: typing.Optional[dom.BackendNodeId] = None

    #: The frame ID for the frame associated with this nodes document.
    frame_id: typing.Optional[page.FrameId] = None

    def to_json(self):
        json = dict()
        json['nodeId'] = self.node_id.to_json()
        json['ignored'] = self.ignored
        if self.ignored_reasons is not None:
            json['ignoredReasons'] = [i.to_json() for i in self.ignored_reasons]
        if self.role is not None:
            json['role'] = self.role.to_json()
        if self.chrome_role is not None:
            json['chromeRole'] = self.chrome_role.to_json()
        if self.name is not None:
            json['name'] = self.name.to_json()
        if self.description is not None:
            json['description'] = self.description.to_json()
        if self.value is not None:
            json['value'] = self.value.to_json()
        if self.properties is not None:
            json['properties'] = [i.to_json() for i in self.properties]
        if self.parent_id is not None:
            json['parentId'] = self.parent_id.to_json()
        if self.child_ids is not None:
            json['childIds'] = [i.to_json() for i in self.child_ids]
        if self.backend_dom_node_id is not None:
            json['backendDOMNodeId'] = self.backend_dom_node_id.to_json()
        if self.frame_id is not None:
            json['frameId'] = self.frame_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            node_id=AXNodeId.from_json(json['nodeId']),
            ignored=bool(json['ignored']),
            ignored_reasons=[AXProperty.from_json(i) for i in json['ignoredReasons']] if 'ignoredReasons' in json else None,
            role=AXValue.from_json(json['role']) if 'role' in json else None,
            chrome_role=AXValue.from_json(json['chromeRole']) if 'chromeRole' in json else None,
            name=AXValue.from_json(json['name']) if 'name' in json else None,
            description=AXValue.from_json(json['description']) if 'description' in json else None,
            value=AXValue.from_json(json['value']) if 'value' in json else None,
            properties=[AXProperty.from_json(i) for i in json['properties']] if 'properties' in json else None,
            parent_id=AXNodeId.from_json(json['parentId']) if 'parentId' in json else None,
            child_ids=[AXNodeId.from_json(i) for i in json['childIds']] if 'childIds' in json else None,
            backend_dom_node_id=dom.BackendNodeId.from_json(json['backendDOMNodeId']) if 'backendDOMNodeId' in json else None,
            frame_id=page.FrameId.from_json(json['frameId']) if 'frameId' in json else None,
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables the accessibility domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables the accessibility domain which causes ``AXNodeId``'s to remain consistent between method calls.
    This turns on accessibility for the page, which can impact performance until accessibility is disabled.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.enable',
    }
    json = yield cmd_dict


def get_partial_ax_tree(
        node_id: typing.Optional[dom.NodeId] = None,
        backend_node_id: typing.Optional[dom.BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None,
        fetch_relatives: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches the accessibility node and partial accessibility tree for this DOM node, if it exists.

    **EXPERIMENTAL**

    :param node_id: *(Optional)* Identifier of the node to get the partial accessibility tree for.
    :param backend_node_id: *(Optional)* Identifier of the backend node to get the partial accessibility tree for.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper to get the partial accessibility tree for.
    :param fetch_relatives: *(Optional)* Whether to fetch this node's ancestors, siblings and children. Defaults to true.
    :returns: The ``Accessibility.AXNode`` for this DOM node, if it exists, plus its ancestors, siblings and children, if requested.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    if fetch_relatives is not None:
        params['fetchRelatives'] = fetch_relatives
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getPartialAXTree',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def get_full_ax_tree(
        depth: typing.Optional[int] = None,
        frame_id: typing.Optional[page.FrameId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches the entire accessibility tree for the root Document

    **EXPERIMENTAL**

    :param depth: *(Optional)* The maximum depth at which descendants of the root node should be retrieved. If omitted, the full tree is returned.
    :param frame_id: *(Optional)* The frame for whose document the AX tree should be retrieved. If omitted, the root frame is used.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if depth is not None:
        params['depth'] = depth
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getFullAXTree',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def get_root_ax_node(
        frame_id: typing.Optional[page.FrameId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,AXNode]:
    '''
    Fetches the root node.
    Requires ``enable()`` to have been called previously.

    **EXPERIMENTAL**

    :param frame_id: *(Optional)* The frame in whose document the node resides. If omitted, the root frame is used.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getRootAXNode',
        'params': params,
    }
    json = yield cmd_dict
    return AXNode.from_json(json['node'])


def get_ax_node_and_ancestors(
        node_id: typing.Optional[dom.NodeId] = None,
        backend_node_id: typing.Optional[dom.BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches a node and all ancestors up to and including the root.
    Requires ``enable()`` to have been called previously.

    **EXPERIMENTAL**

    :param node_id: *(Optional)* Identifier of the node to get.
    :param backend_node_id: *(Optional)* Identifier of the backend node to get.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper to get.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getAXNodeAndAncestors',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def get_child_ax_nodes(
        id_: AXNodeId,
        frame_id: typing.Optional[page.FrameId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Fetches a particular accessibility node by AXNodeId.
    Requires ``enable()`` to have been called previously.

    **EXPERIMENTAL**

    :param id_:
    :param frame_id: *(Optional)* The frame in whose document the node resides. If omitted, the root frame is used.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_.to_json()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.getChildAXNodes',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


def query_ax_tree(
        node_id: typing.Optional[dom.NodeId] = None,
        backend_node_id: typing.Optional[dom.BackendNodeId] = None,
        object_id: typing.Optional[runtime.RemoteObjectId] = None,
        accessible_name: typing.Optional[str] = None,
        role: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AXNode]]:
    '''
    Query a DOM node's accessibility subtree for accessible name and role.
    This command computes the name and role for all nodes in the subtree, including those that are
    ignored for accessibility, and returns those that match the specified name and role. If no DOM
    node is specified, or the DOM node does not exist, the command returns an error. If neither
    ``accessibleName`` or ``role`` is specified, it returns all the accessibility nodes in the subtree.

    **EXPERIMENTAL**

    :param node_id: *(Optional)* Identifier of the node for the root to query.
    :param backend_node_id: *(Optional)* Identifier of the backend node for the root to query.
    :param object_id: *(Optional)* JavaScript object id of the node wrapper for the root to query.
    :param accessible_name: *(Optional)* Find nodes with this computed name.
    :param role: *(Optional)* Find nodes with this computed role.
    :returns: A list of ``Accessibility.AXNode`` matching the specified attributes, including nodes that are ignored for accessibility.
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    if backend_node_id is not None:
        params['backendNodeId'] = backend_node_id.to_json()
    if object_id is not None:
        params['objectId'] = object_id.to_json()
    if accessible_name is not None:
        params['accessibleName'] = accessible_name
    if role is not None:
        params['role'] = role
    cmd_dict: T_JSON_DICT = {
        'method': 'Accessibility.queryAXTree',
        'params': params,
    }
    json = yield cmd_dict
    return [AXNode.from_json(i) for i in json['nodes']]


@event_class('Accessibility.loadComplete')
@dataclass
class LoadComplete:
    '''
    **EXPERIMENTAL**

    The loadComplete event mirrors the load complete event sent by the browser to assistive
    technology when the web page has finished loading.
    '''
    #: New document root node.
    root: AXNode

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LoadComplete:
        return cls(
            root=AXNode.from_json(json['root'])
        )


@event_class('Accessibility.nodesUpdated')
@dataclass
class NodesUpdated:
    '''
    **EXPERIMENTAL**

    The nodesUpdated event is sent every time a previously requested node has changed the in tree.
    '''
    #: Updated node data.
    nodes: typing.List[AXNode]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> NodesUpdated:
        return cls(
            nodes=[AXNode.from_json(i) for i in json['nodes']]
        )

# === NexusCore/openenv\Lib\site-packages\websocket\_core.py ===
import socket
import struct
import threading
import time
from typing import Optional, Union

# websocket modules
from ._abnf import ABNF, STATUS_NORMAL, continuous_frame, frame_buffer
from ._exceptions import WebSocketProtocolException, WebSocketConnectionClosedException
from ._handshake import SUPPORTED_REDIRECT_STATUSES, handshake
from ._http import connect, proxy_info
from ._logging import debug, error, trace, isEnabledForError, isEnabledForTrace
from ._socket import getdefaulttimeout, recv, send, sock_opt
from ._ssl_compat import ssl
from ._utils import NoLock

"""
_core.py
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

__all__ = ["WebSocket", "create_connection"]


class WebSocket:
    """
    Low level WebSocket interface.

    This class is based on the WebSocket protocol `draft-hixie-thewebsocketprotocol-76 <http://tools.ietf.org/html/draft-hixie-thewebsocketprotocol-76>`_

    We can connect to the websocket server and send/receive data.
    The following example is an echo client.

    >>> import websocket
    >>> ws = websocket.WebSocket()
    >>> ws.connect("ws://echo.websocket.events")
    >>> ws.recv()
    'echo.websocket.events sponsored by Lob.com'
    >>> ws.send("Hello, Server")
    19
    >>> ws.recv()
    'Hello, Server'
    >>> ws.close()

    Parameters
    ----------
    get_mask_key: func
        A callable function to get new mask keys, see the
        WebSocket.set_mask_key's docstring for more information.
    sockopt: tuple
        Values for socket.setsockopt.
        sockopt must be tuple and each element is argument of sock.setsockopt.
    sslopt: dict
        Optional dict object for ssl socket options. See FAQ for details.
    fire_cont_frame: bool
        Fire recv event for each cont frame. Default is False.
    enable_multithread: bool
        If set to True, lock send method.
    skip_utf8_validation: bool
        Skip utf8 validation.
    """

    def __init__(
        self,
        get_mask_key=None,
        sockopt=None,
        sslopt=None,
        fire_cont_frame: bool = False,
        enable_multithread: bool = True,
        skip_utf8_validation: bool = False,
        **_,
    ):
        """
        Initialize WebSocket object.

        Parameters
        ----------
        sslopt: dict
            Optional dict object for ssl socket options. See FAQ for details.
        """
        self.sock_opt = sock_opt(sockopt, sslopt)
        self.handshake_response = None
        self.sock: Optional[socket.socket] = None

        self.connected = False
        self.get_mask_key = get_mask_key
        # These buffer over the build-up of a single frame.
        self.frame_buffer = frame_buffer(self._recv, skip_utf8_validation)
        self.cont_frame = continuous_frame(fire_cont_frame, skip_utf8_validation)

        if enable_multithread:
            self.lock = threading.Lock()
            self.readlock = threading.Lock()
        else:
            self.lock = NoLock()
            self.readlock = NoLock()

    def __iter__(self):
        """
        Allow iteration over websocket, implying sequential `recv` executions.
        """
        while True:
            yield self.recv()

    def __next__(self):
        return self.recv()

    def next(self):
        return self.__next__()

    def fileno(self):
        return self.sock.fileno()

    def set_mask_key(self, func):
        """
        Set function to create mask key. You can customize mask key generator.
        Mainly, this is for testing purpose.

        Parameters
        ----------
        func: func
            callable object. the func takes 1 argument as integer.
            The argument means length of mask key.
            This func must return string(byte array),
            which length is argument specified.
        """
        self.get_mask_key = func

    def gettimeout(self) -> Union[float, int, None]:
        """
        Get the websocket timeout (in seconds) as an int or float

        Returns
        ----------
        timeout: int or float
             returns timeout value (in seconds). This value could be either float/integer.
        """
        return self.sock_opt.timeout

    def settimeout(self, timeout: Union[float, int, None]):
        """
        Set the timeout to the websocket.

        Parameters
        ----------
        timeout: int or float
            timeout time (in seconds). This value could be either float/integer.
        """
        self.sock_opt.timeout = timeout
        if self.sock:
            self.sock.settimeout(timeout)

    timeout = property(gettimeout, settimeout)

    def getsubprotocol(self):
        """
        Get subprotocol
        """
        if self.handshake_response:
            return self.handshake_response.subprotocol
        else:
            return None

    subprotocol = property(getsubprotocol)

    def getstatus(self):
        """
        Get handshake status
        """
        if self.handshake_response:
            return self.handshake_response.status
        else:
            return None

    status = property(getstatus)

    def getheaders(self):
        """
        Get handshake response header
        """
        if self.handshake_response:
            return self.handshake_response.headers
        else:
            return None

    def is_ssl(self):
        try:
            return isinstance(self.sock, ssl.SSLSocket)
        except:
            return False

    headers = property(getheaders)

    def connect(self, url, **options):
        """
        Connect to url. url is websocket url scheme.
        ie. ws://host:port/resource
        You can customize using 'options'.
        If you set "header" list object, you can set your own custom header.

        >>> ws = WebSocket()
        >>> ws.connect("ws://echo.websocket.events",
                ...     header=["User-Agent: MyProgram",
                ...             "x-custom: header"])

        Parameters
        ----------
        header: list or dict
            Custom http header list or dict.
        cookie: str
            Cookie value.
        origin: str
            Custom origin url.
        connection: str
            Custom connection header value.
            Default value "Upgrade" set in _handshake.py
        suppress_origin: bool
            Suppress outputting origin header.
        host: str
            Custom host header string.
        timeout: int or float
            Socket timeout time. This value is an integer or float.
            If you set None for this value, it means "use default_timeout value"
        http_proxy_host: str
            HTTP proxy host name.
        http_proxy_port: str or int
            HTTP proxy port. Default is 80.
        http_no_proxy: list
            Whitelisted host names that don't use the proxy.
        http_proxy_auth: tuple
            HTTP proxy auth information. Tuple of username and password. Default is None.
        http_proxy_timeout: int or float
            HTTP proxy timeout, default is 60 sec as per python-socks.
        redirect_limit: int
            Number of redirects to follow.
        subprotocols: list
            List of available subprotocols. Default is None.
        socket: socket
            Pre-initialized stream socket.
        """
        self.sock_opt.timeout = options.get("timeout", self.sock_opt.timeout)
        self.sock, addrs = connect(
            url, self.sock_opt, proxy_info(**options), options.pop("socket", None)
        )

        try:
            self.handshake_response = handshake(self.sock, url, *addrs, **options)
            for _ in range(options.pop("redirect_limit", 3)):
                if self.handshake_response.status in SUPPORTED_REDIRECT_STATUSES:
                    url = self.handshake_response.headers["location"]
                    self.sock.close()
                    self.sock, addrs = connect(
                        url,
                        self.sock_opt,
                        proxy_info(**options),
                        options.pop("socket", None),
                    )
                    self.handshake_response = handshake(
                        self.sock, url, *addrs, **options
                    )
            self.connected = True
        except:
            if self.sock:
                self.sock.close()
                self.sock = None
            raise

    def send(self, payload: Union[bytes, str], opcode: int = ABNF.OPCODE_TEXT) -> int:
        """
        Send the data as string.

        Parameters
        ----------
        payload: str
            Payload must be utf-8 string or unicode,
            If the opcode is OPCODE_TEXT.
            Otherwise, it must be string(byte array).
        opcode: int
            Operation code (opcode) to send.
        """

        frame = ABNF.create_frame(payload, opcode)
        return self.send_frame(frame)

    def send_text(self, text_data: str) -> int:
        """
        Sends UTF-8 encoded text.
        """
        return self.send(text_data, ABNF.OPCODE_TEXT)

    def send_bytes(self, data: Union[bytes, bytearray]) -> int:
        """
        Sends a sequence of bytes.
        """
        return self.send(data, ABNF.OPCODE_BINARY)

    def send_frame(self, frame) -> int:
        """
        Send the data frame.

        >>> ws = create_connection("ws://echo.websocket.events")
        >>> frame = ABNF.create_frame("Hello", ABNF.OPCODE_TEXT)
        >>> ws.send_frame(frame)
        >>> cont_frame = ABNF.create_frame("My name is ", ABNF.OPCODE_CONT, 0)
        >>> ws.send_frame(frame)
        >>> cont_frame = ABNF.create_frame("Foo Bar", ABNF.OPCODE_CONT, 1)
        >>> ws.send_frame(frame)

        Parameters
        ----------
        frame: ABNF frame
            frame data created by ABNF.create_frame
        """
        if self.get_mask_key:
            frame.get_mask_key = self.get_mask_key
        data = frame.format()
        length = len(data)
        if isEnabledForTrace():
            trace(f"++Sent raw: {repr(data)}")
            trace(f"++Sent decoded: {frame.__str__()}")
        with self.lock:
            while data:
                l = self._send(data)
                data = data[l:]

        return length

    def send_binary(self, payload: bytes) -> int:
        """
        Send a binary message (OPCODE_BINARY).

        Parameters
        ----------
        payload: bytes
            payload of message to send.
        """
        return self.send(payload, ABNF.OPCODE_BINARY)

    def ping(self, payload: Union[str, bytes] = ""):
        """
        Send ping data.

        Parameters
        ----------
        payload: str
            data payload to send server.
        """
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        self.send(payload, ABNF.OPCODE_PING)

    def pong(self, payload: Union[str, bytes] = ""):
        """
        Send pong data.

        Parameters
        ----------
        payload: str
            data payload to send server.
        """
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        self.send(payload, ABNF.OPCODE_PONG)

    def recv(self) -> Union[str, bytes]:
        """
        Receive string data(byte array) from the server.

        Returns
        ----------
        data: string (byte array) value.
        """
        with self.readlock:
            opcode, data = self.recv_data()
        if opcode == ABNF.OPCODE_TEXT:
            data_received: Union[bytes, str] = data
            if isinstance(data_received, bytes):
                return data_received.decode("utf-8")
            elif isinstance(data_received, str):
                return data_received
        elif opcode == ABNF.OPCODE_BINARY:
            data_binary: bytes = data
            return data_binary
        else:
            return ""

    def recv_data(self, control_frame: bool = False) -> tuple:
        """
        Receive data with operation code.

        Parameters
        ----------
        control_frame: bool
            a boolean flag indicating whether to return control frame
            data, defaults to False

        Returns
        -------
        opcode, frame.data: tuple
            tuple of operation code and string(byte array) value.
        """
        opcode, frame = self.recv_data_frame(control_frame)
        return opcode, frame.data

    def recv_data_frame(self, control_frame: bool = False) -> tuple:
        """
        Receive data with operation code.

        If a valid ping message is received, a pong response is sent.

        Parameters
        ----------
        control_frame: bool
            a boolean flag indicating whether to return control frame
            data, defaults to False

        Returns
        -------
        frame.opcode, frame: tuple
            tuple of operation code and string(byte array) value.
        """
        while True:
            frame = self.recv_frame()
            if isEnabledForTrace():
                trace(f"++Rcv raw: {repr(frame.format())}")
                trace(f"++Rcv decoded: {frame.__str__()}")
            if not frame:
                # handle error:
                # 'NoneType' object has no attribute 'opcode'
                raise WebSocketProtocolException(f"Not a valid frame {frame}")
            elif frame.opcode in (
                ABNF.OPCODE_TEXT,
                ABNF.OPCODE_BINARY,
                ABNF.OPCODE_CONT,
            ):
                self.cont_frame.validate(frame)
                self.cont_frame.add(frame)

                if self.cont_frame.is_fire(frame):
                    return self.cont_frame.extract(frame)

            elif frame.opcode == ABNF.OPCODE_CLOSE:
                self.send_close()
                return frame.opcode, frame
            elif frame.opcode == ABNF.OPCODE_PING:
                if len(frame.data) < 126:
                    self.pong(frame.data)
                else:
                    raise WebSocketProtocolException("Ping message is too long")
                if control_frame:
                    return frame.opcode, frame
            elif frame.opcode == ABNF.OPCODE_PONG:
                if control_frame:
                    return frame.opcode, frame

    def recv_frame(self):
        """
        Receive data as frame from server.

        Returns
        -------
        self.frame_buffer.recv_frame(): ABNF frame object
        """
        return self.frame_buffer.recv_frame()

    def send_close(self, status: int = STATUS_NORMAL, reason: bytes = b""):
        """
        Send close data to the server.

        Parameters
        ----------
        status: int
            Status code to send. See STATUS_XXX.
        reason: str or bytes
            The reason to close. This must be string or UTF-8 bytes.
        """
        if status < 0 or status >= ABNF.LENGTH_16:
            raise ValueError("code is invalid range")
        self.connected = False
        self.send(struct.pack("!H", status) + reason, ABNF.OPCODE_CLOSE)

    def close(self, status: int = STATUS_NORMAL, reason: bytes = b"", timeout: int = 3):
        """
        Close Websocket object

        Parameters
        ----------
        status: int
            Status code to send. See VALID_CLOSE_STATUS in ABNF.
        reason: bytes
            The reason to close in UTF-8.
        timeout: int or float
            Timeout until receive a close frame.
            If None, it will wait forever until receive a close frame.
        """
        if not self.connected:
            return
        if status < 0 or status >= ABNF.LENGTH_16:
            raise ValueError("code is invalid range")

        try:
            self.connected = False
            self.send(struct.pack("!H", status) + reason, ABNF.OPCODE_CLOSE)
            sock_timeout = self.sock.gettimeout()
            self.sock.settimeout(timeout)
            start_time = time.time()
            while timeout is None or time.time() - start_time < timeout:
                try:
                    frame = self.recv_frame()
                    if frame.opcode != ABNF.OPCODE_CLOSE:
                        continue
                    if isEnabledForError():
                        recv_status = struct.unpack("!H", frame.data[0:2])[0]
                        if recv_status >= 3000 and recv_status <= 4999:
                            debug(f"close status: {repr(recv_status)}")
                        elif recv_status != STATUS_NORMAL:
                            error(f"close status: {repr(recv_status)}")
                    break
                except:
                    break
            self.sock.settimeout(sock_timeout)
            self.sock.shutdown(socket.SHUT_RDWR)
        except:
            pass

        self.shutdown()

    def abort(self):
        """
        Low-level asynchronous abort, wakes up other threads that are waiting in recv_*
        """
        if self.connected:
            self.sock.shutdown(socket.SHUT_RDWR)

    def shutdown(self):
        """
        close socket, immediately.
        """
        if self.sock:
            self.sock.close()
            self.sock = None
            self.connected = False

    def _send(self, data: Union[str, bytes]):
        return send(self.sock, data)

    def _recv(self, bufsize):
        try:
            return recv(self.sock, bufsize)
        except WebSocketConnectionClosedException:
            if self.sock:
                self.sock.close()
            self.sock = None
            self.connected = False
            raise


def create_connection(url: str, timeout=None, class_=WebSocket, **options):
    """
    Connect to url and return websocket object.

    Connect to url and return the WebSocket object.
    Passing optional timeout parameter will set the timeout on the socket.
    If no timeout is supplied,
    the global default timeout setting returned by getdefaulttimeout() is used.
    You can customize using 'options'.
    If you set "header" list object, you can set your own custom header.

    >>> conn = create_connection("ws://echo.websocket.events",
         ...     header=["User-Agent: MyProgram",
         ...             "x-custom: header"])

    Parameters
    ----------
    class_: class
        class to instantiate when creating the connection. It has to implement
        settimeout and connect. It's __init__ should be compatible with
        WebSocket.__init__, i.e. accept all of it's kwargs.
    header: list or dict
        custom http header list or dict.
    cookie: str
        Cookie value.
    origin: str
        custom origin url.
    suppress_origin: bool
        suppress outputting origin header.
    host: str
        custom host header string.
    timeout: int or float
        socket timeout time. This value could be either float/integer.
        If set to None, it uses the default_timeout value.
    http_proxy_host: str
        HTTP proxy host name.
    http_proxy_port: str or int
        HTTP proxy port. If not set, set to 80.
    http_no_proxy: list
        Whitelisted host names that don't use the proxy.
    http_proxy_auth: tuple
        HTTP proxy auth information. tuple of username and password. Default is None.
    http_proxy_timeout: int or float
        HTTP proxy timeout, default is 60 sec as per python-socks.
    enable_multithread: bool
        Enable lock for multithread.
    redirect_limit: int
        Number of redirects to follow.
    sockopt: tuple
        Values for socket.setsockopt.
        sockopt must be a tuple and each element is an argument of sock.setsockopt.
    sslopt: dict
        Optional dict object for ssl socket options. See FAQ for details.
    subprotocols: list
        List of available subprotocols. Default is None.
    skip_utf8_validation: bool
        Skip utf8 validation.
    socket: socket
        Pre-initialized stream socket.
    """
    sockopt = options.pop("sockopt", [])
    sslopt = options.pop("sslopt", {})
    fire_cont_frame = options.pop("fire_cont_frame", False)
    enable_multithread = options.pop("enable_multithread", True)
    skip_utf8_validation = options.pop("skip_utf8_validation", False)
    websock = class_(
        sockopt=sockopt,
        sslopt=sslopt,
        fire_cont_frame=fire_cont_frame,
        enable_multithread=enable_multithread,
        skip_utf8_validation=skip_utf8_validation,
        **options,
    )
    websock.settimeout(timeout if timeout is not None else getdefaulttimeout())
    websock.connect(url, **options)
    return websock

# === NexusCore/openenv\Lib\site-packages\jedi\inference\value\iterable.py ===
"""
Contains all classes and functions to deal with lists, dicts, generators and
iterators in general.
"""
from jedi.inference import compiled
from jedi.inference import analysis
from jedi.inference.lazy_value import LazyKnownValue, LazyKnownValues, \
    LazyTreeValue
from jedi.inference.helpers import get_int_or_none, is_string, \
    reraise_getitem_errors, SimpleGetItemNotFound
from jedi.inference.utils import safe_property, to_list
from jedi.inference.cache import inference_state_method_cache
from jedi.inference.filters import LazyAttributeOverwrite, publish_method
from jedi.inference.base_value import ValueSet, Value, NO_VALUES, \
    ContextualizedNode, iterate_values, sentinel, \
    LazyValueWrapper
from jedi.parser_utils import get_sync_comp_fors
from jedi.inference.context import CompForContext
from jedi.inference.value.dynamic_arrays import check_array_additions


class IterableMixin:
    def py__next__(self, contextualized_node=None):
        return self.py__iter__(contextualized_node)

    def py__stop_iteration_returns(self):
        return ValueSet([compiled.builtin_from_name(self.inference_state, 'None')])

    # At the moment, safe values are simple values like "foo", 1 and not
    # lists/dicts. Therefore as a small speed optimization we can just do the
    # default instead of resolving the lazy wrapped values, that are just
    # doing this in the end as well.
    # This mostly speeds up patterns like `sys.version_info >= (3, 0)` in
    # typeshed.
    get_safe_value = Value.get_safe_value


class GeneratorBase(LazyAttributeOverwrite, IterableMixin):
    array_type = None

    def _get_wrapped_value(self):
        instance, = self._get_cls().execute_annotation()
        return instance

    def _get_cls(self):
        generator, = self.inference_state.typing_module.py__getattribute__('Generator')
        return generator

    def py__bool__(self):
        return True

    @publish_method('__iter__')
    def _iter(self, arguments):
        return ValueSet([self])

    @publish_method('send')
    @publish_method('__next__')
    def _next(self, arguments):
        return ValueSet.from_sets(lazy_value.infer() for lazy_value in self.py__iter__())

    def py__stop_iteration_returns(self):
        return ValueSet([compiled.builtin_from_name(self.inference_state, 'None')])

    @property
    def name(self):
        return compiled.CompiledValueName(self, 'Generator')

    def get_annotated_class_object(self):
        from jedi.inference.gradual.generics import TupleGenericManager
        gen_values = self.merge_types_of_iterate().py__class__()
        gm = TupleGenericManager((gen_values, NO_VALUES, NO_VALUES))
        return self._get_cls().with_generics(gm)


class Generator(GeneratorBase):
    """Handling of `yield` functions."""
    def __init__(self, inference_state, func_execution_context):
        super().__init__(inference_state)
        self._func_execution_context = func_execution_context

    def py__iter__(self, contextualized_node=None):
        iterators = self._func_execution_context.infer_annotations()
        if iterators:
            return iterators.iterate(contextualized_node)
        return self._func_execution_context.get_yield_lazy_values()

    def py__stop_iteration_returns(self):
        return self._func_execution_context.get_return_values()

    def __repr__(self):
        return "<%s of %s>" % (type(self).__name__, self._func_execution_context)


def comprehension_from_atom(inference_state, value, atom):
    bracket = atom.children[0]
    test_list_comp = atom.children[1]

    if bracket == '{':
        if atom.children[1].children[1] == ':':
            sync_comp_for = test_list_comp.children[3]
            if sync_comp_for.type == 'comp_for':
                sync_comp_for = sync_comp_for.children[1]

            return DictComprehension(
                inference_state,
                value,
                sync_comp_for_node=sync_comp_for,
                key_node=test_list_comp.children[0],
                value_node=test_list_comp.children[2],
            )
        else:
            cls = SetComprehension
    elif bracket == '(':
        cls = GeneratorComprehension
    elif bracket == '[':
        cls = ListComprehension

    sync_comp_for = test_list_comp.children[1]
    if sync_comp_for.type == 'comp_for':
        sync_comp_for = sync_comp_for.children[1]

    return cls(
        inference_state,
        defining_context=value,
        sync_comp_for_node=sync_comp_for,
        entry_node=test_list_comp.children[0],
    )


class ComprehensionMixin:
    @inference_state_method_cache()
    def _get_comp_for_context(self, parent_context, comp_for):
        return CompForContext(parent_context, comp_for)

    def _nested(self, comp_fors, parent_context=None):
        comp_for = comp_fors[0]

        is_async = comp_for.parent.type == 'comp_for'

        input_node = comp_for.children[3]
        parent_context = parent_context or self._defining_context
        input_types = parent_context.infer_node(input_node)

        cn = ContextualizedNode(parent_context, input_node)
        iterated = input_types.iterate(cn, is_async=is_async)
        exprlist = comp_for.children[1]
        for i, lazy_value in enumerate(iterated):
            types = lazy_value.infer()
            dct = unpack_tuple_to_dict(parent_context, types, exprlist)
            context = self._get_comp_for_context(
                parent_context,
                comp_for,
            )
            with context.predefine_names(comp_for, dct):
                try:
                    yield from self._nested(comp_fors[1:], context)
                except IndexError:
                    iterated = context.infer_node(self._entry_node)
                    if self.array_type == 'dict':
                        yield iterated, context.infer_node(self._value_node)
                    else:
                        yield iterated

    @inference_state_method_cache(default=[])
    @to_list
    def _iterate(self):
        comp_fors = tuple(get_sync_comp_fors(self._sync_comp_for_node))
        yield from self._nested(comp_fors)

    def py__iter__(self, contextualized_node=None):
        for set_ in self._iterate():
            yield LazyKnownValues(set_)

    def __repr__(self):
        return "<%s of %s>" % (type(self).__name__, self._sync_comp_for_node)


class _DictMixin:
    def _get_generics(self):
        return tuple(c_set.py__class__() for c_set in self.get_mapping_item_values())


class Sequence(LazyAttributeOverwrite, IterableMixin):
    api_type = 'instance'

    @property
    def name(self):
        return compiled.CompiledValueName(self, self.array_type)

    def _get_generics(self):
        return (self.merge_types_of_iterate().py__class__(),)

    @inference_state_method_cache(default=())
    def _cached_generics(self):
        return self._get_generics()

    def _get_wrapped_value(self):
        from jedi.inference.gradual.base import GenericClass
        from jedi.inference.gradual.generics import TupleGenericManager
        klass = compiled.builtin_from_name(self.inference_state, self.array_type)
        c, = GenericClass(
            klass,
            TupleGenericManager(self._cached_generics())
        ).execute_annotation()
        return c

    def py__bool__(self):
        return None  # We don't know the length, because of appends.

    @safe_property
    def parent(self):
        return self.inference_state.builtins_module

    def py__getitem__(self, index_value_set, contextualized_node):
        if self.array_type == 'dict':
            return self._dict_values()
        return iterate_values(ValueSet([self]))


class _BaseComprehension(ComprehensionMixin):
    def __init__(self, inference_state, defining_context, sync_comp_for_node, entry_node):
        assert sync_comp_for_node.type == 'sync_comp_for'
        super().__init__(inference_state)
        self._defining_context = defining_context
        self._sync_comp_for_node = sync_comp_for_node
        self._entry_node = entry_node


class ListComprehension(_BaseComprehension, Sequence):
    array_type = 'list'

    def py__simple_getitem__(self, index):
        if isinstance(index, slice):
            return ValueSet([self])

        all_types = list(self.py__iter__())
        with reraise_getitem_errors(IndexError, TypeError):
            lazy_value = all_types[index]
        return lazy_value.infer()


class SetComprehension(_BaseComprehension, Sequence):
    array_type = 'set'


class GeneratorComprehension(_BaseComprehension, GeneratorBase):
    pass


class _DictKeyMixin:
    # TODO merge with _DictMixin?
    def get_mapping_item_values(self):
        return self._dict_keys(), self._dict_values()

    def get_key_values(self):
        # TODO merge with _dict_keys?
        return self._dict_keys()


class DictComprehension(ComprehensionMixin, Sequence, _DictKeyMixin):
    array_type = 'dict'

    def __init__(self, inference_state, defining_context, sync_comp_for_node, key_node, value_node):
        assert sync_comp_for_node.type == 'sync_comp_for'
        super().__init__(inference_state)
        self._defining_context = defining_context
        self._sync_comp_for_node = sync_comp_for_node
        self._entry_node = key_node
        self._value_node = value_node

    def py__iter__(self, contextualized_node=None):
        for keys, values in self._iterate():
            yield LazyKnownValues(keys)

    def py__simple_getitem__(self, index):
        for keys, values in self._iterate():
            for k in keys:
                # Be careful in the future if refactoring, index could be a
                # slice object.
                if k.get_safe_value(default=object()) == index:
                    return values
        raise SimpleGetItemNotFound()

    def _dict_keys(self):
        return ValueSet.from_sets(keys for keys, values in self._iterate())

    def _dict_values(self):
        return ValueSet.from_sets(values for keys, values in self._iterate())

    @publish_method('values')
    def _imitate_values(self, arguments):
        lazy_value = LazyKnownValues(self._dict_values())
        return ValueSet([FakeList(self.inference_state, [lazy_value])])

    @publish_method('items')
    def _imitate_items(self, arguments):
        lazy_values = [
            LazyKnownValue(
                FakeTuple(
                    self.inference_state,
                    [LazyKnownValues(key),
                     LazyKnownValues(value)]
                )
            )
            for key, value in self._iterate()
        ]

        return ValueSet([FakeList(self.inference_state, lazy_values)])

    def exact_key_items(self):
        # NOTE: A smarter thing can probably done here to achieve better
        # completions, but at least like this jedi doesn't crash
        return []


class SequenceLiteralValue(Sequence):
    _TUPLE_LIKE = 'testlist_star_expr', 'testlist', 'subscriptlist'
    mapping = {'(': 'tuple',
               '[': 'list',
               '{': 'set'}

    def __init__(self, inference_state, defining_context, atom):
        super().__init__(inference_state)
        self.atom = atom
        self._defining_context = defining_context

        if self.atom.type in self._TUPLE_LIKE:
            self.array_type = 'tuple'
        else:
            self.array_type = SequenceLiteralValue.mapping[atom.children[0]]
            """The builtin name of the array (list, set, tuple or dict)."""

    def _get_generics(self):
        if self.array_type == 'tuple':
            return tuple(x.infer().py__class__() for x in self.py__iter__())
        return super()._get_generics()

    def py__simple_getitem__(self, index):
        """Here the index is an int/str. Raises IndexError/KeyError."""
        if isinstance(index, slice):
            return ValueSet([self])
        else:
            with reraise_getitem_errors(TypeError, KeyError, IndexError):
                node = self.get_tree_entries()[index]
            if node == ':' or node.type == 'subscript':
                return NO_VALUES
            return self._defining_context.infer_node(node)

    def py__iter__(self, contextualized_node=None):
        """
        While values returns the possible values for any array field, this
        function returns the value for a certain index.
        """
        for node in self.get_tree_entries():
            if node == ':' or node.type == 'subscript':
                # TODO this should probably use at least part of the code
                #      of infer_subscript_list.
                yield LazyKnownValue(Slice(self._defining_context, None, None, None))
            else:
                yield LazyTreeValue(self._defining_context, node)
        yield from check_array_additions(self._defining_context, self)

    def py__len__(self):
        # This function is not really used often. It's more of a try.
        return len(self.get_tree_entries())

    def get_tree_entries(self):
        c = self.atom.children

        if self.atom.type in self._TUPLE_LIKE:
            return c[::2]

        array_node = c[1]
        if array_node in (']', '}', ')'):
            return []  # Direct closing bracket, doesn't contain items.

        if array_node.type == 'testlist_comp':
            # filter out (for now) pep 448 single-star unpacking
            return [value for value in array_node.children[::2]
                    if value.type != "star_expr"]
        elif array_node.type == 'dictorsetmaker':
            kv = []
            iterator = iter(array_node.children)
            for key in iterator:
                if key == "**":
                    # dict with pep 448 double-star unpacking
                    # for now ignoring the values imported by **
                    next(iterator)
                    next(iterator, None)  # Possible comma.
                else:
                    op = next(iterator, None)
                    if op is None or op == ',':
                        if key.type == "star_expr":
                            # pep 448 single-star unpacking
                            # for now ignoring values imported by *
                            pass
                        else:
                            kv.append(key)  # A set.
                    else:
                        assert op == ':'  # A dict.
                        kv.append((key, next(iterator)))
                        next(iterator, None)  # Possible comma.
            return kv
        else:
            if array_node.type == "star_expr":
                # pep 448 single-star unpacking
                # for now ignoring values imported by *
                return []
            else:
                return [array_node]

    def __repr__(self):
        return "<%s of %s>" % (self.__class__.__name__, self.atom)


class DictLiteralValue(_DictMixin, SequenceLiteralValue, _DictKeyMixin):
    array_type = 'dict'

    def __init__(self, inference_state, defining_context, atom):
        # Intentionally don't call the super class. This is definitely a sign
        # that the architecture is bad and we should refactor.
        Sequence.__init__(self, inference_state)
        self._defining_context = defining_context
        self.atom = atom

    def py__simple_getitem__(self, index):
        """Here the index is an int/str. Raises IndexError/KeyError."""
        compiled_value_index = compiled.create_simple_object(self.inference_state, index)
        for key, value in self.get_tree_entries():
            for k in self._defining_context.infer_node(key):
                for key_v in k.execute_operation(compiled_value_index, '=='):
                    if key_v.get_safe_value():
                        return self._defining_context.infer_node(value)
        raise SimpleGetItemNotFound('No key found in dictionary %s.' % self)

    def py__iter__(self, contextualized_node=None):
        """
        While values returns the possible values for any array field, this
        function returns the value for a certain index.
        """
        # Get keys.
        types = NO_VALUES
        for k, _ in self.get_tree_entries():
            types |= self._defining_context.infer_node(k)
        # We don't know which dict index comes first, therefore always
        # yield all the types.
        for _ in types:
            yield LazyKnownValues(types)

    @publish_method('values')
    def _imitate_values(self, arguments):
        lazy_value = LazyKnownValues(self._dict_values())
        return ValueSet([FakeList(self.inference_state, [lazy_value])])

    @publish_method('items')
    def _imitate_items(self, arguments):
        lazy_values = [
            LazyKnownValue(FakeTuple(
                self.inference_state,
                (LazyTreeValue(self._defining_context, key_node),
                 LazyTreeValue(self._defining_context, value_node))
            )) for key_node, value_node in self.get_tree_entries()
        ]

        return ValueSet([FakeList(self.inference_state, lazy_values)])

    def exact_key_items(self):
        """
        Returns a generator of tuples like dict.items(), where the key is
        resolved (as a string) and the values are still lazy values.
        """
        for key_node, value in self.get_tree_entries():
            for key in self._defining_context.infer_node(key_node):
                if is_string(key):
                    yield key.get_safe_value(), LazyTreeValue(self._defining_context, value)

    def _dict_values(self):
        return ValueSet.from_sets(
            self._defining_context.infer_node(v)
            for k, v in self.get_tree_entries()
        )

    def _dict_keys(self):
        return ValueSet.from_sets(
            self._defining_context.infer_node(k)
            for k, v in self.get_tree_entries()
        )


class _FakeSequence(Sequence):
    def __init__(self, inference_state, lazy_value_list):
        """
        type should be one of "tuple", "list"
        """
        super().__init__(inference_state)
        self._lazy_value_list = lazy_value_list

    def py__simple_getitem__(self, index):
        if isinstance(index, slice):
            return ValueSet([self])

        with reraise_getitem_errors(IndexError, TypeError):
            lazy_value = self._lazy_value_list[index]
        return lazy_value.infer()

    def py__iter__(self, contextualized_node=None):
        return self._lazy_value_list

    def py__bool__(self):
        return bool(len(self._lazy_value_list))

    def __repr__(self):
        return "<%s of %s>" % (type(self).__name__, self._lazy_value_list)


class FakeTuple(_FakeSequence):
    array_type = 'tuple'


class FakeList(_FakeSequence):
    array_type = 'tuple'


class FakeDict(_DictMixin, Sequence, _DictKeyMixin):
    array_type = 'dict'

    def __init__(self, inference_state, dct):
        super().__init__(inference_state)
        self._dct = dct

    def py__iter__(self, contextualized_node=None):
        for key in self._dct:
            yield LazyKnownValue(compiled.create_simple_object(self.inference_state, key))

    def py__simple_getitem__(self, index):
        with reraise_getitem_errors(KeyError, TypeError):
            lazy_value = self._dct[index]
        return lazy_value.infer()

    @publish_method('values')
    def _values(self, arguments):
        return ValueSet([FakeTuple(
            self.inference_state,
            [LazyKnownValues(self._dict_values())]
        )])

    def _dict_values(self):
        return ValueSet.from_sets(lazy_value.infer() for lazy_value in self._dct.values())

    def _dict_keys(self):
        return ValueSet.from_sets(lazy_value.infer() for lazy_value in self.py__iter__())

    def exact_key_items(self):
        return self._dct.items()

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self._dct)


class MergedArray(Sequence):
    def __init__(self, inference_state, arrays):
        super().__init__(inference_state)
        self.array_type = arrays[-1].array_type
        self._arrays = arrays

    def py__iter__(self, contextualized_node=None):
        for array in self._arrays:
            yield from array.py__iter__()

    def py__simple_getitem__(self, index):
        return ValueSet.from_sets(lazy_value.infer() for lazy_value in self.py__iter__())


def unpack_tuple_to_dict(context, types, exprlist):
    """
    Unpacking tuple assignments in for statements and expr_stmts.
    """
    if exprlist.type == 'name':
        return {exprlist.value: types}
    elif exprlist.type == 'atom' and exprlist.children[0] in ('(', '['):
        return unpack_tuple_to_dict(context, types, exprlist.children[1])
    elif exprlist.type in ('testlist', 'testlist_comp', 'exprlist',
                           'testlist_star_expr'):
        dct = {}
        parts = iter(exprlist.children[::2])
        n = 0
        for lazy_value in types.iterate(ContextualizedNode(context, exprlist)):
            n += 1
            try:
                part = next(parts)
            except StopIteration:
                analysis.add(context, 'value-error-too-many-values', part,
                             message="ValueError: too many values to unpack (expected %s)" % n)
            else:
                dct.update(unpack_tuple_to_dict(context, lazy_value.infer(), part))
        has_parts = next(parts, None)
        if types and has_parts is not None:
            analysis.add(context, 'value-error-too-few-values', has_parts,
                         message="ValueError: need more than %s values to unpack" % n)
        return dct
    elif exprlist.type == 'power' or exprlist.type == 'atom_expr':
        # Something like ``arr[x], var = ...``.
        # This is something that is not yet supported, would also be difficult
        # to write into a dict.
        return {}
    elif exprlist.type == 'star_expr':  # `a, *b, c = x` type unpackings
        # Currently we're not supporting them.
        return {}
    raise NotImplementedError


class Slice(LazyValueWrapper):
    def __init__(self, python_context, start, stop, step):
        self.inference_state = python_context.inference_state
        self._context = python_context
        # All of them are either a Precedence or None.
        self._start = start
        self._stop = stop
        self._step = step

    def _get_wrapped_value(self):
        value = compiled.builtin_from_name(self._context.inference_state, 'slice')
        slice_value, = value.execute_with_values()
        return slice_value

    def get_safe_value(self, default=sentinel):
        """
        Imitate CompiledValue.obj behavior and return a ``builtin.slice()``
        object.
        """
        def get(element):
            if element is None:
                return None

            result = self._context.infer_node(element)
            if len(result) != 1:
                # For simplicity, we want slices to be clear defined with just
                # one type.  Otherwise we will return an empty slice object.
                raise IndexError

            value, = result
            return get_int_or_none(value)

        try:
            return slice(get(self._start), get(self._stop), get(self._step))
        except IndexError:
            return slice(None, None, None)

# === NexusCore/openenv\Lib\site-packages\google\api_core\grpc_helpers.py ===
# Copyright 2017 Google LLC
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

"""Helpers for :mod:`grpc`."""
from typing import Generic, Iterator, Optional, TypeVar

import collections
import functools
import warnings

import grpc

from google.api_core import exceptions
import google.auth
import google.auth.credentials
import google.auth.transport.grpc
import google.auth.transport.requests
import google.protobuf

PROTOBUF_VERSION = google.protobuf.__version__

# The grpcio-gcp package only has support for protobuf < 4
if PROTOBUF_VERSION[0:2] == "3.":  # pragma: NO COVER
    try:
        import grpc_gcp

        warnings.warn(
            """Support for grpcio-gcp is deprecated. This feature will be
            removed from `google-api-core` after January 1, 2024. If you need to
            continue to use this feature, please pin to a specific version of
            `google-api-core`.""",
            DeprecationWarning,
        )
        HAS_GRPC_GCP = True
    except ImportError:
        HAS_GRPC_GCP = False
else:
    HAS_GRPC_GCP = False


# The list of gRPC Callable interfaces that return iterators.
_STREAM_WRAP_CLASSES = (grpc.UnaryStreamMultiCallable, grpc.StreamStreamMultiCallable)

# denotes the proto response type for grpc calls
P = TypeVar("P")


def _patch_callable_name(callable_):
    """Fix-up gRPC callable attributes.

    gRPC callable lack the ``__name__`` attribute which causes
    :func:`functools.wraps` to error. This adds the attribute if needed.
    """
    if not hasattr(callable_, "__name__"):
        callable_.__name__ = callable_.__class__.__name__


def _wrap_unary_errors(callable_):
    """Map errors for Unary-Unary and Stream-Unary gRPC callables."""
    _patch_callable_name(callable_)

    @functools.wraps(callable_)
    def error_remapped_callable(*args, **kwargs):
        try:
            return callable_(*args, **kwargs)
        except grpc.RpcError as exc:
            raise exceptions.from_grpc_error(exc) from exc

    return error_remapped_callable


class _StreamingResponseIterator(Generic[P], grpc.Call):
    def __init__(self, wrapped, prefetch_first_result=True):
        self._wrapped = wrapped

        # This iterator is used in a retry context, and returned outside after init.
        # gRPC will not throw an exception until the stream is consumed, so we need
        # to retrieve the first result, in order to fail, in order to trigger a retry.
        try:
            if prefetch_first_result:
                self._stored_first_result = next(self._wrapped)
        except TypeError:
            # It is possible the wrapped method isn't an iterable (a grpc.Call
            # for instance). If this happens don't store the first result.
            pass
        except StopIteration:
            # ignore stop iteration at this time. This should be handled outside of retry.
            pass

    def __iter__(self) -> Iterator[P]:
        """This iterator is also an iterable that returns itself."""
        return self

    def __next__(self) -> P:
        """Get the next response from the stream.

        Returns:
            protobuf.Message: A single response from the stream.
        """
        try:
            if hasattr(self, "_stored_first_result"):
                result = self._stored_first_result
                del self._stored_first_result
                return result
            return next(self._wrapped)
        except grpc.RpcError as exc:
            # If the stream has already returned data, we cannot recover here.
            raise exceptions.from_grpc_error(exc) from exc

    # grpc.Call & grpc.RpcContext interface

    def add_callback(self, callback):
        return self._wrapped.add_callback(callback)

    def cancel(self):
        return self._wrapped.cancel()

    def code(self):
        return self._wrapped.code()

    def details(self):
        return self._wrapped.details()

    def initial_metadata(self):
        return self._wrapped.initial_metadata()

    def is_active(self):
        return self._wrapped.is_active()

    def time_remaining(self):
        return self._wrapped.time_remaining()

    def trailing_metadata(self):
        return self._wrapped.trailing_metadata()


# public type alias denoting the return type of streaming gapic calls
GrpcStream = _StreamingResponseIterator[P]


def _wrap_stream_errors(callable_):
    """Wrap errors for Unary-Stream and Stream-Stream gRPC callables.

    The callables that return iterators require a bit more logic to re-map
    errors when iterating. This wraps both the initial invocation and the
    iterator of the return value to re-map errors.
    """
    _patch_callable_name(callable_)

    @functools.wraps(callable_)
    def error_remapped_callable(*args, **kwargs):
        try:
            result = callable_(*args, **kwargs)
            # Auto-fetching the first result causes PubSub client's streaming pull
            # to hang when re-opening the stream, thus we need examine the hacky
            # hidden flag to see if pre-fetching is disabled.
            # https://github.com/googleapis/python-pubsub/issues/93#issuecomment-630762257
            prefetch_first = getattr(callable_, "_prefetch_first_result_", True)
            return _StreamingResponseIterator(
                result, prefetch_first_result=prefetch_first
            )
        except grpc.RpcError as exc:
            raise exceptions.from_grpc_error(exc) from exc

    return error_remapped_callable


def wrap_errors(callable_):
    """Wrap a gRPC callable and map :class:`grpc.RpcErrors` to friendly error
    classes.

    Errors raised by the gRPC callable are mapped to the appropriate
    :class:`google.api_core.exceptions.GoogleAPICallError` subclasses.
    The original `grpc.RpcError` (which is usually also a `grpc.Call`) is
    available from the ``response`` property on the mapped exception. This
    is useful for extracting metadata from the original error.

    Args:
        callable_ (Callable): A gRPC callable.

    Returns:
        Callable: The wrapped gRPC callable.
    """
    if isinstance(callable_, _STREAM_WRAP_CLASSES):
        return _wrap_stream_errors(callable_)
    else:
        return _wrap_unary_errors(callable_)


def _create_composite_credentials(
    credentials=None,
    credentials_file=None,
    default_scopes=None,
    scopes=None,
    ssl_credentials=None,
    quota_project_id=None,
    default_host=None,
):
    """Create the composite credentials for secure channels.

    Args:
        credentials (google.auth.credentials.Credentials): The credentials. If
            not specified, then this function will attempt to ascertain the
            credentials from the environment using :func:`google.auth.default`.
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
        default_scopes (Sequence[str]): A optional list of scopes needed for this
            service. These are only used when credentials are not specified and
            are passed to :func:`google.auth.default`.
        scopes (Sequence[str]): A optional list of scopes needed for this
            service. These are only used when credentials are not specified and
            are passed to :func:`google.auth.default`.
        ssl_credentials (grpc.ChannelCredentials): Optional SSL channel
            credentials. This can be used to specify different certificates.
        quota_project_id (str): An optional project to use for billing and quota.
        default_host (str): The default endpoint. e.g., "pubsub.googleapis.com".

    Returns:
        grpc.ChannelCredentials: The composed channel credentials object.

    Raises:
        google.api_core.DuplicateCredentialArgs: If both a credentials object and credentials_file are passed.
    """
    if credentials and credentials_file:
        raise exceptions.DuplicateCredentialArgs(
            "'credentials' and 'credentials_file' are mutually exclusive."
        )

    if credentials_file:
        credentials, _ = google.auth.load_credentials_from_file(
            credentials_file, scopes=scopes, default_scopes=default_scopes
        )
    elif credentials:
        credentials = google.auth.credentials.with_scopes_if_required(
            credentials, scopes=scopes, default_scopes=default_scopes
        )
    else:
        credentials, _ = google.auth.default(
            scopes=scopes, default_scopes=default_scopes
        )

    if quota_project_id and isinstance(
        credentials, google.auth.credentials.CredentialsWithQuotaProject
    ):
        credentials = credentials.with_quota_project(quota_project_id)

    request = google.auth.transport.requests.Request()

    # Create the metadata plugin for inserting the authorization header.
    metadata_plugin = google.auth.transport.grpc.AuthMetadataPlugin(
        credentials,
        request,
        default_host=default_host,
    )

    # Create a set of grpc.CallCredentials using the metadata plugin.
    google_auth_credentials = grpc.metadata_call_credentials(metadata_plugin)

    # if `ssl_credentials` is set, use `grpc.composite_channel_credentials` instead of
    # `grpc.compute_engine_channel_credentials` as the former supports passing
    # `ssl_credentials` via `channel_credentials` which is needed for mTLS.
    if ssl_credentials:
        # Combine the ssl credentials and the authorization credentials.
        # See https://grpc.github.io/grpc/python/grpc.html#grpc.composite_channel_credentials
        return grpc.composite_channel_credentials(
            ssl_credentials, google_auth_credentials
        )
    else:
        # Use grpc.compute_engine_channel_credentials in order to support Direct Path.
        # See https://grpc.github.io/grpc/python/grpc.html#grpc.compute_engine_channel_credentials
        # TODO(https://github.com/googleapis/python-api-core/issues/598):
        # Although `grpc.compute_engine_channel_credentials` returns channel credentials
        # outside of a Google Compute Engine environment (GCE), we should determine if
        # there is a way to reliably detect a GCE environment so that
        # `grpc.compute_engine_channel_credentials` is not called outside of GCE.
        return grpc.compute_engine_channel_credentials(google_auth_credentials)


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
    **kwargs,
):
    """Create a secure channel with credentials.

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

        kwargs: Additional key-word args passed to
            :func:`grpc_gcp.secure_channel` or :func:`grpc.secure_channel`.
            Note: `grpc_gcp` is only supported in environments with protobuf < 4.0.0.

    Returns:
        grpc.Channel: The created channel.

    Raises:
        google.api_core.DuplicateCredentialArgs: If both a credentials object and credentials_file are passed.
        ValueError: If `ssl_credentials` is set and `attempt_direct_path` is set to `True`.
    """

    # If `ssl_credentials` is set and `attempt_direct_path` is set to `True`,
    # raise ValueError as this is not yet supported.
    # See https://github.com/googleapis/python-api-core/issues/590
    if ssl_credentials and attempt_direct_path:
        raise ValueError("Using ssl_credentials with Direct Path is not supported")

    composite_credentials = _create_composite_credentials(
        credentials=credentials,
        credentials_file=credentials_file,
        default_scopes=default_scopes,
        scopes=scopes,
        ssl_credentials=ssl_credentials,
        quota_project_id=quota_project_id,
        default_host=default_host,
    )

    # Note that grpcio-gcp is deprecated
    if HAS_GRPC_GCP:  # pragma: NO COVER
        if compression is not None and compression != grpc.Compression.NoCompression:
            warnings.warn(
                "The `compression` argument is ignored for grpc_gcp.secure_channel creation.",
                DeprecationWarning,
            )
        if attempt_direct_path:
            warnings.warn(
                """The `attempt_direct_path` argument is ignored for grpc_gcp.secure_channel creation.""",
                DeprecationWarning,
            )
        return grpc_gcp.secure_channel(target, composite_credentials, **kwargs)

    if attempt_direct_path:
        target = _modify_target_for_direct_path(target)

    return grpc.secure_channel(
        target, composite_credentials, compression=compression, **kwargs
    )


def _modify_target_for_direct_path(target: str) -> str:
    """
    Given a target, return a modified version which is compatible with Direct Path.

    Args:
        target (str): The target service address in the format 'hostname[:port]' or
            'dns://hostname[:port]'.

    Returns:
        target (str): The target service address which is converted into a format compatible with Direct Path.
            If the target contains `dns:///` or does not contain `:///`, the target will be converted in
            a format compatible with Direct Path; otherwise the original target will be returned as the
            original target may already denote Direct Path.
    """

    # A DNS prefix may be included with the target to indicate the endpoint is living in the Internet,
    # outside of Google Cloud Platform.
    dns_prefix = "dns:///"
    # Remove "dns:///" if `attempt_direct_path` is set to True as
    # the Direct Path prefix `google-c2p:///` will be used instead.
    target = target.replace(dns_prefix, "")

    direct_path_separator = ":///"
    if direct_path_separator not in target:
        target_without_port = target.split(":")[0]
        # Modify the target to use Direct Path by adding the `google-c2p:///` prefix
        target = f"google-c2p{direct_path_separator}{target_without_port}"
    return target


_MethodCall = collections.namedtuple(
    "_MethodCall", ("request", "timeout", "metadata", "credentials", "compression")
)

_ChannelRequest = collections.namedtuple("_ChannelRequest", ("method", "request"))


class _CallableStub(object):
    """Stub for the grpc.*MultiCallable interfaces."""

    def __init__(self, method, channel):
        self._method = method
        self._channel = channel
        self.response = None
        """Union[protobuf.Message, Callable[protobuf.Message], exception]:
        The response to give when invoking this callable. If this is a
        callable, it will be invoked with the request protobuf. If it's an
        exception, the exception will be raised when this is invoked.
        """
        self.responses = None
        """Iterator[
            Union[protobuf.Message, Callable[protobuf.Message], exception]]:
        An iterator of responses. If specified, self.response will be populated
        on each invocation by calling ``next(self.responses)``."""
        self.requests = []
        """List[protobuf.Message]: All requests sent to this callable."""
        self.calls = []
        """List[Tuple]: All invocations of this callable. Each tuple is the
        request, timeout, metadata, compression, and credentials."""

    def __call__(
        self, request, timeout=None, metadata=None, credentials=None, compression=None
    ):
        self._channel.requests.append(_ChannelRequest(self._method, request))
        self.calls.append(
            _MethodCall(request, timeout, metadata, credentials, compression)
        )
        self.requests.append(request)

        response = self.response
        if self.responses is not None:
            if response is None:
                response = next(self.responses)
            else:
                raise ValueError(
                    "{method}.response and {method}.responses are mutually "
                    "exclusive.".format(method=self._method)
                )

        if callable(response):
            return response(request)

        if isinstance(response, Exception):
            raise response

        if response is not None:
            return response

        raise ValueError('Method stub for "{}" has no response.'.format(self._method))


def _simplify_method_name(method):
    """Simplifies a gRPC method name.

    When gRPC invokes the channel to create a callable, it gives a full
    method name like "/google.pubsub.v1.Publisher/CreateTopic". This
    returns just the name of the method, in this case "CreateTopic".

    Args:
        method (str): The name of the method.

    Returns:
        str: The simplified name of the method.
    """
    return method.rsplit("/", 1).pop()


class ChannelStub(grpc.Channel):
    """A testing stub for the grpc.Channel interface.

    This can be used to test any client that eventually uses a gRPC channel
    to communicate. By passing in a channel stub, you can configure which
    responses are returned and track which requests are made.

    For example:

    .. code-block:: python

        channel_stub = grpc_helpers.ChannelStub()
        client = FooClient(channel=channel_stub)

        channel_stub.GetFoo.response = foo_pb2.Foo(name='bar')

        foo = client.get_foo(labels=['baz'])

        assert foo.name == 'bar'
        assert channel_stub.GetFoo.requests[0].labels = ['baz']

    Each method on the stub can be accessed and configured on the channel.
    Here's some examples of various configurations:

    .. code-block:: python

        # Return a basic response:

        channel_stub.GetFoo.response = foo_pb2.Foo(name='bar')
        assert client.get_foo().name == 'bar'

        # Raise an exception:
        channel_stub.GetFoo.response = NotFound('...')

        with pytest.raises(NotFound):
            client.get_foo()

        # Use a sequence of responses:
        channel_stub.GetFoo.responses = iter([
            foo_pb2.Foo(name='bar'),
            foo_pb2.Foo(name='baz'),
        ])

        assert client.get_foo().name == 'bar'
        assert client.get_foo().name == 'baz'

        # Use a callable

        def on_get_foo(request):
            return foo_pb2.Foo(name='bar' + request.id)

        channel_stub.GetFoo.response = on_get_foo

        assert client.get_foo(id='123').name == 'bar123'
    """

    def __init__(self, responses=[]):
        self.requests = []
        """Sequence[Tuple[str, protobuf.Message]]: A list of all requests made
        on this channel in order. The tuple is of method name, request
        message."""
        self._method_stubs = {}

    def _stub_for_method(self, method):
        method = _simplify_method_name(method)
        self._method_stubs[method] = _CallableStub(method, self)
        return self._method_stubs[method]

    def __getattr__(self, key):
        try:
            return self._method_stubs[key]
        except KeyError:
            raise AttributeError

    def unary_unary(
        self,
        method,
        request_serializer=None,
        response_deserializer=None,
        _registered_method=False,
    ):
        """grpc.Channel.unary_unary implementation."""
        return self._stub_for_method(method)

    def unary_stream(
        self,
        method,
        request_serializer=None,
        response_deserializer=None,
        _registered_method=False,
    ):
        """grpc.Channel.unary_stream implementation."""
        return self._stub_for_method(method)

    def stream_unary(
        self,
        method,
        request_serializer=None,
        response_deserializer=None,
        _registered_method=False,
    ):
        """grpc.Channel.stream_unary implementation."""
        return self._stub_for_method(method)

    def stream_stream(
        self,
        method,
        request_serializer=None,
        response_deserializer=None,
        _registered_method=False,
    ):
        """grpc.Channel.stream_stream implementation."""
        return self._stub_for_method(method)

    def subscribe(self, callback, try_to_connect=False):
        """grpc.Channel.subscribe implementation."""
        pass

    def unsubscribe(self, callback):
        """grpc.Channel.unsubscribe implementation."""
        pass

    def close(self):
        """grpc.Channel.close implementation."""
        pass

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\errors.py ===
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Sequence, Set, Tuple, Type, Union

from pydantic.v1.typing import display_as_type

if TYPE_CHECKING:
    from pydantic.v1.typing import DictStrAny

# explicitly state exports to avoid "from pydantic.v1.errors import *" also importing Decimal, Path etc.
__all__ = (
    'PydanticTypeError',
    'PydanticValueError',
    'ConfigError',
    'MissingError',
    'ExtraError',
    'NoneIsNotAllowedError',
    'NoneIsAllowedError',
    'WrongConstantError',
    'NotNoneError',
    'BoolError',
    'BytesError',
    'DictError',
    'EmailError',
    'UrlError',
    'UrlSchemeError',
    'UrlSchemePermittedError',
    'UrlUserInfoError',
    'UrlHostError',
    'UrlHostTldError',
    'UrlPortError',
    'UrlExtraError',
    'EnumError',
    'IntEnumError',
    'EnumMemberError',
    'IntegerError',
    'FloatError',
    'PathError',
    'PathNotExistsError',
    'PathNotAFileError',
    'PathNotADirectoryError',
    'PyObjectError',
    'SequenceError',
    'ListError',
    'SetError',
    'FrozenSetError',
    'TupleError',
    'TupleLengthError',
    'ListMinLengthError',
    'ListMaxLengthError',
    'ListUniqueItemsError',
    'SetMinLengthError',
    'SetMaxLengthError',
    'FrozenSetMinLengthError',
    'FrozenSetMaxLengthError',
    'AnyStrMinLengthError',
    'AnyStrMaxLengthError',
    'StrError',
    'StrRegexError',
    'NumberNotGtError',
    'NumberNotGeError',
    'NumberNotLtError',
    'NumberNotLeError',
    'NumberNotMultipleError',
    'DecimalError',
    'DecimalIsNotFiniteError',
    'DecimalMaxDigitsError',
    'DecimalMaxPlacesError',
    'DecimalWholeDigitsError',
    'DateTimeError',
    'DateError',
    'DateNotInThePastError',
    'DateNotInTheFutureError',
    'TimeError',
    'DurationError',
    'HashableError',
    'UUIDError',
    'UUIDVersionError',
    'ArbitraryTypeError',
    'ClassError',
    'SubclassError',
    'JsonError',
    'JsonTypeError',
    'PatternError',
    'DataclassTypeError',
    'CallableError',
    'IPvAnyAddressError',
    'IPvAnyInterfaceError',
    'IPvAnyNetworkError',
    'IPv4AddressError',
    'IPv6AddressError',
    'IPv4NetworkError',
    'IPv6NetworkError',
    'IPv4InterfaceError',
    'IPv6InterfaceError',
    'ColorError',
    'StrictBoolError',
    'NotDigitError',
    'LuhnValidationError',
    'InvalidLengthForBrand',
    'InvalidByteSize',
    'InvalidByteSizeUnit',
    'MissingDiscriminator',
    'InvalidDiscriminator',
)


def cls_kwargs(cls: Type['PydanticErrorMixin'], ctx: 'DictStrAny') -> 'PydanticErrorMixin':
    """
    For built-in exceptions like ValueError or TypeError, we need to implement
    __reduce__ to override the default behaviour (instead of __getstate__/__setstate__)
    By default pickle protocol 2 calls `cls.__new__(cls, *args)`.
    Since we only use kwargs, we need a little constructor to change that.
    Note: the callable can't be a lambda as pickle looks in the namespace to find it
    """
    return cls(**ctx)


class PydanticErrorMixin:
    code: str
    msg_template: str

    def __init__(self, **ctx: Any) -> None:
        self.__dict__ = ctx

    def __str__(self) -> str:
        return self.msg_template.format(**self.__dict__)

    def __reduce__(self) -> Tuple[Callable[..., 'PydanticErrorMixin'], Tuple[Type['PydanticErrorMixin'], 'DictStrAny']]:
        return cls_kwargs, (self.__class__, self.__dict__)


class PydanticTypeError(PydanticErrorMixin, TypeError):
    pass


class PydanticValueError(PydanticErrorMixin, ValueError):
    pass


class ConfigError(RuntimeError):
    pass


class MissingError(PydanticValueError):
    msg_template = 'field required'


class ExtraError(PydanticValueError):
    msg_template = 'extra fields not permitted'


class NoneIsNotAllowedError(PydanticTypeError):
    code = 'none.not_allowed'
    msg_template = 'none is not an allowed value'


class NoneIsAllowedError(PydanticTypeError):
    code = 'none.allowed'
    msg_template = 'value is not none'


class WrongConstantError(PydanticValueError):
    code = 'const'

    def __str__(self) -> str:
        permitted = ', '.join(repr(v) for v in self.permitted)  # type: ignore
        return f'unexpected value; permitted: {permitted}'


class NotNoneError(PydanticTypeError):
    code = 'not_none'
    msg_template = 'value is not None'


class BoolError(PydanticTypeError):
    msg_template = 'value could not be parsed to a boolean'


class BytesError(PydanticTypeError):
    msg_template = 'byte type expected'


class DictError(PydanticTypeError):
    msg_template = 'value is not a valid dict'


class EmailError(PydanticValueError):
    msg_template = 'value is not a valid email address'


class UrlError(PydanticValueError):
    code = 'url'


class UrlSchemeError(UrlError):
    code = 'url.scheme'
    msg_template = 'invalid or missing URL scheme'


class UrlSchemePermittedError(UrlError):
    code = 'url.scheme'
    msg_template = 'URL scheme not permitted'

    def __init__(self, allowed_schemes: Set[str]):
        super().__init__(allowed_schemes=allowed_schemes)


class UrlUserInfoError(UrlError):
    code = 'url.userinfo'
    msg_template = 'userinfo required in URL but missing'


class UrlHostError(UrlError):
    code = 'url.host'
    msg_template = 'URL host invalid'


class UrlHostTldError(UrlError):
    code = 'url.host'
    msg_template = 'URL host invalid, top level domain required'


class UrlPortError(UrlError):
    code = 'url.port'
    msg_template = 'URL port invalid, port cannot exceed 65535'


class UrlExtraError(UrlError):
    code = 'url.extra'
    msg_template = 'URL invalid, extra characters found after valid URL: {extra!r}'


class EnumMemberError(PydanticTypeError):
    code = 'enum'

    def __str__(self) -> str:
        permitted = ', '.join(repr(v.value) for v in self.enum_values)  # type: ignore
        return f'value is not a valid enumeration member; permitted: {permitted}'


class IntegerError(PydanticTypeError):
    msg_template = 'value is not a valid integer'


class FloatError(PydanticTypeError):
    msg_template = 'value is not a valid float'


class PathError(PydanticTypeError):
    msg_template = 'value is not a valid path'


class _PathValueError(PydanticValueError):
    def __init__(self, *, path: Path) -> None:
        super().__init__(path=str(path))


class PathNotExistsError(_PathValueError):
    code = 'path.not_exists'
    msg_template = 'file or directory at path "{path}" does not exist'


class PathNotAFileError(_PathValueError):
    code = 'path.not_a_file'
    msg_template = 'path "{path}" does not point to a file'


class PathNotADirectoryError(_PathValueError):
    code = 'path.not_a_directory'
    msg_template = 'path "{path}" does not point to a directory'


class PyObjectError(PydanticTypeError):
    msg_template = 'ensure this value contains valid import path or valid callable: {error_message}'


class SequenceError(PydanticTypeError):
    msg_template = 'value is not a valid sequence'


class IterableError(PydanticTypeError):
    msg_template = 'value is not a valid iterable'


class ListError(PydanticTypeError):
    msg_template = 'value is not a valid list'


class SetError(PydanticTypeError):
    msg_template = 'value is not a valid set'


class FrozenSetError(PydanticTypeError):
    msg_template = 'value is not a valid frozenset'


class DequeError(PydanticTypeError):
    msg_template = 'value is not a valid deque'


class TupleError(PydanticTypeError):
    msg_template = 'value is not a valid tuple'


class TupleLengthError(PydanticValueError):
    code = 'tuple.length'
    msg_template = 'wrong tuple length {actual_length}, expected {expected_length}'

    def __init__(self, *, actual_length: int, expected_length: int) -> None:
        super().__init__(actual_length=actual_length, expected_length=expected_length)


class ListMinLengthError(PydanticValueError):
    code = 'list.min_items'
    msg_template = 'ensure this value has at least {limit_value} items'

    def __init__(self, *, limit_value: int) -> None:
        super().__init__(limit_value=limit_value)


class ListMaxLengthError(PydanticValueError):
    code = 'list.max_items'
    msg_template = 'ensure this value has at most {limit_value} items'

    def __init__(self, *, limit_value: int) -> None:
        super().__init__(limit_value=limit_value)


class ListUniqueItemsError(PydanticValueError):
    code = 'list.unique_items'
    msg_template = 'the list has duplicated items'


class SetMinLengthError(PydanticValueError):
    code = 'set.min_items'
    msg_template = 'ensure this value has at least {limit_value} items'

    def __init__(self, *, limit_value: int) -> None:
        super().__init__(limit_value=limit_value)


class SetMaxLengthError(PydanticValueError):
    code = 'set.max_items'
    msg_template = 'ensure this value has at most {limit_value} items'

    def __init__(self, *, limit_value: int) -> None:
        super().__init__(limit_value=limit_value)


class FrozenSetMinLengthError(PydanticValueError):
    code = 'frozenset.min_items'
    msg_template = 'ensure this value has at least {limit_value} items'

    def __init__(self, *, limit_value: int) -> None:
        super().__init__(limit_value=limit_value)


class FrozenSetMaxLengthError(PydanticValueError):
    code = 'frozenset.max_items'
    msg_template = 'ensure this value has at most {limit_value} items'

    def __init__(self, *, limit_value: int) -> None:
        super().__init__(limit_value=limit_value)


class AnyStrMinLengthError(PydanticValueError):
    code = 'any_str.min_length'
    msg_template = 'ensure this value has at least {limit_value} characters'

    def __init__(self, *, limit_value: int) -> None:
        super().__init__(limit_value=limit_value)


class AnyStrMaxLengthError(PydanticValueError):
    code = 'any_str.max_length'
    msg_template = 'ensure this value has at most {limit_value} characters'

    def __init__(self, *, limit_value: int) -> None:
        super().__init__(limit_value=limit_value)


class StrError(PydanticTypeError):
    msg_template = 'str type expected'


class StrRegexError(PydanticValueError):
    code = 'str.regex'
    msg_template = 'string does not match regex "{pattern}"'

    def __init__(self, *, pattern: str) -> None:
        super().__init__(pattern=pattern)


class _NumberBoundError(PydanticValueError):
    def __init__(self, *, limit_value: Union[int, float, Decimal]) -> None:
        super().__init__(limit_value=limit_value)


class NumberNotGtError(_NumberBoundError):
    code = 'number.not_gt'
    msg_template = 'ensure this value is greater than {limit_value}'


class NumberNotGeError(_NumberBoundError):
    code = 'number.not_ge'
    msg_template = 'ensure this value is greater than or equal to {limit_value}'


class NumberNotLtError(_NumberBoundError):
    code = 'number.not_lt'
    msg_template = 'ensure this value is less than {limit_value}'


class NumberNotLeError(_NumberBoundError):
    code = 'number.not_le'
    msg_template = 'ensure this value is less than or equal to {limit_value}'


class NumberNotFiniteError(PydanticValueError):
    code = 'number.not_finite_number'
    msg_template = 'ensure this value is a finite number'


class NumberNotMultipleError(PydanticValueError):
    code = 'number.not_multiple'
    msg_template = 'ensure this value is a multiple of {multiple_of}'

    def __init__(self, *, multiple_of: Union[int, float, Decimal]) -> None:
        super().__init__(multiple_of=multiple_of)


class DecimalError(PydanticTypeError):
    msg_template = 'value is not a valid decimal'


class DecimalIsNotFiniteError(PydanticValueError):
    code = 'decimal.not_finite'
    msg_template = 'value is not a valid decimal'


class DecimalMaxDigitsError(PydanticValueError):
    code = 'decimal.max_digits'
    msg_template = 'ensure that there are no more than {max_digits} digits in total'

    def __init__(self, *, max_digits: int) -> None:
        super().__init__(max_digits=max_digits)


class DecimalMaxPlacesError(PydanticValueError):
    code = 'decimal.max_places'
    msg_template = 'ensure that there are no more than {decimal_places} decimal places'

    def __init__(self, *, decimal_places: int) -> None:
        super().__init__(decimal_places=decimal_places)


class DecimalWholeDigitsError(PydanticValueError):
    code = 'decimal.whole_digits'
    msg_template = 'ensure that there are no more than {whole_digits} digits before the decimal point'

    def __init__(self, *, whole_digits: int) -> None:
        super().__init__(whole_digits=whole_digits)


class DateTimeError(PydanticValueError):
    msg_template = 'invalid datetime format'


class DateError(PydanticValueError):
    msg_template = 'invalid date format'


class DateNotInThePastError(PydanticValueError):
    code = 'date.not_in_the_past'
    msg_template = 'date is not in the past'


class DateNotInTheFutureError(PydanticValueError):
    code = 'date.not_in_the_future'
    msg_template = 'date is not in the future'


class TimeError(PydanticValueError):
    msg_template = 'invalid time format'


class DurationError(PydanticValueError):
    msg_template = 'invalid duration format'


class HashableError(PydanticTypeError):
    msg_template = 'value is not a valid hashable'


class UUIDError(PydanticTypeError):
    msg_template = 'value is not a valid uuid'


class UUIDVersionError(PydanticValueError):
    code = 'uuid.version'
    msg_template = 'uuid version {required_version} expected'

    def __init__(self, *, required_version: int) -> None:
        super().__init__(required_version=required_version)


class ArbitraryTypeError(PydanticTypeError):
    code = 'arbitrary_type'
    msg_template = 'instance of {expected_arbitrary_type} expected'

    def __init__(self, *, expected_arbitrary_type: Type[Any]) -> None:
        super().__init__(expected_arbitrary_type=display_as_type(expected_arbitrary_type))


class ClassError(PydanticTypeError):
    code = 'class'
    msg_template = 'a class is expected'


class SubclassError(PydanticTypeError):
    code = 'subclass'
    msg_template = 'subclass of {expected_class} expected'

    def __init__(self, *, expected_class: Type[Any]) -> None:
        super().__init__(expected_class=display_as_type(expected_class))


class JsonError(PydanticValueError):
    msg_template = 'Invalid JSON'


class JsonTypeError(PydanticTypeError):
    code = 'json'
    msg_template = 'JSON object must be str, bytes or bytearray'


class PatternError(PydanticValueError):
    code = 'regex_pattern'
    msg_template = 'Invalid regular expression'


class DataclassTypeError(PydanticTypeError):
    code = 'dataclass'
    msg_template = 'instance of {class_name}, tuple or dict expected'


class CallableError(PydanticTypeError):
    msg_template = '{value} is not callable'


class EnumError(PydanticTypeError):
    code = 'enum_instance'
    msg_template = '{value} is not a valid Enum instance'


class IntEnumError(PydanticTypeError):
    code = 'int_enum_instance'
    msg_template = '{value} is not a valid IntEnum instance'


class IPvAnyAddressError(PydanticValueError):
    msg_template = 'value is not a valid IPv4 or IPv6 address'


class IPvAnyInterfaceError(PydanticValueError):
    msg_template = 'value is not a valid IPv4 or IPv6 interface'


class IPvAnyNetworkError(PydanticValueError):
    msg_template = 'value is not a valid IPv4 or IPv6 network'


class IPv4AddressError(PydanticValueError):
    msg_template = 'value is not a valid IPv4 address'


class IPv6AddressError(PydanticValueError):
    msg_template = 'value is not a valid IPv6 address'


class IPv4NetworkError(PydanticValueError):
    msg_template = 'value is not a valid IPv4 network'


class IPv6NetworkError(PydanticValueError):
    msg_template = 'value is not a valid IPv6 network'


class IPv4InterfaceError(PydanticValueError):
    msg_template = 'value is not a valid IPv4 interface'


class IPv6InterfaceError(PydanticValueError):
    msg_template = 'value is not a valid IPv6 interface'


class ColorError(PydanticValueError):
    msg_template = 'value is not a valid color: {reason}'


class StrictBoolError(PydanticValueError):
    msg_template = 'value is not a valid boolean'


class NotDigitError(PydanticValueError):
    code = 'payment_card_number.digits'
    msg_template = 'card number is not all digits'


class LuhnValidationError(PydanticValueError):
    code = 'payment_card_number.luhn_check'
    msg_template = 'card number is not luhn valid'


class InvalidLengthForBrand(PydanticValueError):
    code = 'payment_card_number.invalid_length_for_brand'
    msg_template = 'Length for a {brand} card must be {required_length}'


class InvalidByteSize(PydanticValueError):
    msg_template = 'could not parse value and unit from byte string'


class InvalidByteSizeUnit(PydanticValueError):
    msg_template = 'could not interpret byte unit: {unit}'


class MissingDiscriminator(PydanticValueError):
    code = 'discriminated_union.missing_discriminator'
    msg_template = 'Discriminator {discriminator_key!r} is missing in value'


class InvalidDiscriminator(PydanticValueError):
    code = 'discriminated_union.invalid_discriminator'
    msg_template = (
        'No match for discriminator {discriminator_key!r} and value {discriminator_value!r} '
        '(allowed values: {allowed_values})'
    )

    def __init__(self, *, discriminator_key: str, discriminator_value: Any, allowed_values: Sequence[Any]) -> None:
        super().__init__(
            discriminator_key=discriminator_key,
            discriminator_value=discriminator_value,
            allowed_values=', '.join(map(repr, allowed_values)),
        )