
# === NexusCore/openenv\Lib\site-packages\pygments\lexers\jvm.py ===
"""
    pygments.lexers.jvm
    ~~~~~~~~~~~~~~~~~~~

    Pygments lexers for JVM languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer, RegexLexer, include, bygroups, using, \
    this, combined, default, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace
from pygments.util import shebang_matches
from pygments import unistring as uni

__all__ = ['JavaLexer', 'ScalaLexer', 'GosuLexer', 'GosuTemplateLexer',
           'GroovyLexer', 'IokeLexer', 'ClojureLexer', 'ClojureScriptLexer',
           'KotlinLexer', 'XtendLexer', 'AspectJLexer', 'CeylonLexer',
           'PigLexer', 'GoloLexer', 'JasminLexer', 'SarlLexer']


class JavaLexer(RegexLexer):
    """
    For Java source code.
    """

    name = 'Java'
    url = 'https://www.oracle.com/technetwork/java/'
    aliases = ['java']
    filenames = ['*.java']
    mimetypes = ['text/x-java']
    version_added = ''

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            (r'(^\s*)((?:(?:public|private|protected|static|strictfp)(?:\s+))*)(record)\b',
             bygroups(Whitespace, using(this), Keyword.Declaration), 'class'),
            (r'[^\S\n]+', Whitespace),
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'/\*.*?\*/', Comment.Multiline),
            # keywords: go before method names to avoid lexing "throw new XYZ"
            # as a method signature
            (r'(assert|break|case|catch|continue|default|do|else|finally|for|'
             r'if|goto|instanceof|new|return|switch|this|throw|try|while)\b',
             Keyword),
            # method names
            (r'((?:(?:[^\W\d]|\$)[\w.\[\]$<>?]*\s+)+?)'  # return arguments
             r'((?:[^\W\d]|\$)[\w$]*)'                  # method name
             r'(\s*)(\()',                              # signature start
             bygroups(using(this), Name.Function, Whitespace, Punctuation)),
            (r'@[^\W\d][\w.]*', Name.Decorator),
            (r'(abstract|const|enum|extends|final|implements|native|private|'
             r'protected|public|sealed|static|strictfp|super|synchronized|throws|'
             r'transient|volatile|yield)\b', Keyword.Declaration),
            (r'(boolean|byte|char|double|float|int|long|short|void)\b',
             Keyword.Type),
            (r'(package)(\s+)', bygroups(Keyword.Namespace, Whitespace), 'import'),
            (r'(true|false|null)\b', Keyword.Constant),
            (r'(class|interface)\b', Keyword.Declaration, 'class'),
            (r'(var)(\s+)', bygroups(Keyword.Declaration, Whitespace), 'var'),
            (r'(import(?:\s+static)?)(\s+)', bygroups(Keyword.Namespace, Whitespace),
             'import'),
            (r'"""\n', String, 'multiline_string'),
            (r'"', String, 'string'),
            (r"'\\.'|'[^\\]'|'\\u[0-9a-fA-F]{4}'", String.Char),
            (r'(\.)((?:[^\W\d]|\$)[\w$]*)', bygroups(Punctuation,
                                                     Name.Attribute)),
            (r'^(\s*)(default)(:)', bygroups(Whitespace, Keyword, Punctuation)),
            (r'^(\s*)((?:[^\W\d]|\$)[\w$]*)(:)', bygroups(Whitespace, Name.Label,
                                                          Punctuation)),
            (r'([^\W\d]|\$)[\w$]*', Name),
            (r'([0-9][0-9_]*\.([0-9][0-9_]*)?|'
             r'\.[0-9][0-9_]*)'
             r'([eE][+\-]?[0-9][0-9_]*)?[fFdD]?|'
             r'[0-9][eE][+\-]?[0-9][0-9_]*[fFdD]?|'
             r'[0-9]([eE][+\-]?[0-9][0-9_]*)?[fFdD]|'
             r'0[xX]([0-9a-fA-F][0-9a-fA-F_]*\.?|'
             r'([0-9a-fA-F][0-9a-fA-F_]*)?\.[0-9a-fA-F][0-9a-fA-F_]*)'
             r'[pP][+\-]?[0-9][0-9_]*[fFdD]?', Number.Float),
            (r'0[xX][0-9a-fA-F][0-9a-fA-F_]*[lL]?', Number.Hex),
            (r'0[bB][01][01_]*[lL]?', Number.Bin),
            (r'0[0-7_]+[lL]?', Number.Oct),
            (r'0|[1-9][0-9_]*[lL]?', Number.Integer),
            (r'[~^*!%&\[\]<>|+=/?-]', Operator),
            (r'[{}();:.,]', Punctuation),
            (r'\n', Whitespace)
        ],
        'class': [
            (r'\s+', Text),
            (r'([^\W\d]|\$)[\w$]*', Name.Class, '#pop')
        ],
        'var': [
            (r'([^\W\d]|\$)[\w$]*', Name, '#pop')
        ],
        'import': [
            (r'[\w.]+\*?', Name.Namespace, '#pop')
        ],
        'multiline_string': [
            (r'"""', String, '#pop'),
            (r'"', String),
            include('string')
        ],
        'string': [
            (r'[^\\"]+', String),
            (r'\\\\', String),  # Escaped backslash
            (r'\\"', String),  # Escaped quote
            (r'\\', String),  # Bare backslash
            (r'"', String, '#pop'),  # Closing quote
        ],
    }


class AspectJLexer(JavaLexer):
    """
    For AspectJ source code.
    """

    name = 'AspectJ'
    url = 'http://www.eclipse.org/aspectj/'
    aliases = ['aspectj']
    filenames = ['*.aj']
    mimetypes = ['text/x-aspectj']
    version_added = '1.6'

    aj_keywords = {
        'aspect', 'pointcut', 'privileged', 'call', 'execution',
        'initialization', 'preinitialization', 'handler', 'get', 'set',
        'staticinitialization', 'target', 'args', 'within', 'withincode',
        'cflow', 'cflowbelow', 'annotation', 'before', 'after', 'around',
        'proceed', 'throwing', 'returning', 'adviceexecution', 'declare',
        'parents', 'warning', 'error', 'soft', 'precedence', 'thisJoinPoint',
        'thisJoinPointStaticPart', 'thisEnclosingJoinPointStaticPart',
        'issingleton', 'perthis', 'pertarget', 'percflow', 'percflowbelow',
        'pertypewithin', 'lock', 'unlock', 'thisAspectInstance'
    }
    aj_inter_type = {'parents:', 'warning:', 'error:', 'soft:', 'precedence:'}
    aj_inter_type_annotation = {'@type', '@method', '@constructor', '@field'}

    def get_tokens_unprocessed(self, text):
        for index, token, value in JavaLexer.get_tokens_unprocessed(self, text):
            if token is Name and value in self.aj_keywords:
                yield index, Keyword, value
            elif token is Name.Label and value in self.aj_inter_type:
                yield index, Keyword, value[:-1]
                yield index, Operator, value[-1]
            elif token is Name.Decorator and value in self.aj_inter_type_annotation:
                yield index, Keyword, value
            else:
                yield index, token, value


class ScalaLexer(RegexLexer):
    """
    For Scala source code.
    """

    name = 'Scala'
    url = 'http://www.scala-lang.org'
    aliases = ['scala']
    filenames = ['*.scala']
    mimetypes = ['text/x-scala']
    version_added = ''

    flags = re.MULTILINE | re.DOTALL

    opchar = '[!#%&*\\-\\/:?@^' + uni.combine('Sm', 'So') + ']'
    letter = '[_\\$' + uni.combine('Ll', 'Lu', 'Lo', 'Nl', 'Lt') + ']'
    upperLetter = '[' + uni.combine('Lu', 'Lt') + ']'
    letterOrDigit = f'(?:{letter}|[0-9])'
    letterOrDigitNoDollarSign = '(?:{}|[0-9])'.format(letter.replace('\\$', ''))
    alphaId = f'{letter}+'
    simpleInterpolatedVariable  = f'{letter}{letterOrDigitNoDollarSign}*'
    idrest = f'{letter}{letterOrDigit}*(?:(?<=_){opchar}+)?'
    idUpper = f'{upperLetter}{letterOrDigit}*(?:(?<=_){opchar}+)?'
    plainid = f'(?:{idrest}|{opchar}+)'
    backQuotedId = r'`[^`]+`'
    anyId = rf'(?:{plainid}|{backQuotedId})'
    notStartOfComment = r'(?!//|/\*)'
    endOfLineMaybeWithComment = r'(?=\s*(//|$))'

    keywords = (
        'new', 'return', 'throw', 'classOf', 'isInstanceOf', 'asInstanceOf',
        'else', 'if', 'then', 'do', 'while', 'for', 'yield', 'match', 'case',
        'catch', 'finally', 'try'
    )

    operators = (
        '<%', '=:=', '<:<', '<%<', '>:', '<:', '=', '==', '!=', '<=', '>=',
        '<>', '<', '>', '<-', '←', '->', '→', '=>', '⇒', '?', '@', '|', '-',
        '+', '*', '%', '~', '\\'
    )

    storage_modifiers = (
        'private', 'protected', 'synchronized', '@volatile', 'abstract',
        'final', 'lazy', 'sealed', 'implicit', 'override', '@transient',
        '@native'
    )

    tokens = {
        'root': [
            include('whitespace'),
            include('comments'),
            include('script-header'),
            include('imports'),
            include('exports'),
            include('storage-modifiers'),
            include('annotations'),
            include('using'),
            include('declarations'),
            include('inheritance'),
            include('extension'),
            include('end'),
            include('constants'),
            include('strings'),
            include('symbols'),
            include('singleton-type'),
            include('inline'),
            include('quoted'),
            include('keywords'),
            include('operators'),
            include('punctuation'),
            include('names'),
        ],

        # Includes:
        'whitespace': [
            (r'\s+', Whitespace),
        ],
        'comments': [
            (r'//.*?\n', Comment.Single),
            (r'/\*', Comment.Multiline, 'comment'),
        ],
        'script-header': [
            (r'^#!([^\n]*)$', Comment.Hashbang),
        ],
        'imports': [
            (r'\b(import)(\s+)', bygroups(Keyword, Whitespace), 'import-path'),
        ],
        'exports': [
            (r'\b(export)(\s+)(given)(\s+)',
                bygroups(Keyword, Whitespace, Keyword, Whitespace), 'export-path'),
            (r'\b(export)(\s+)', bygroups(Keyword, Whitespace), 'export-path'),
        ],
        'storage-modifiers': [
            (words(storage_modifiers, prefix=r'\b', suffix=r'\b'), Keyword),
            # Only highlight soft modifiers if they are eventually followed by
            # the correct keyword. Note that soft modifiers can be followed by a
            # sequence of regular modifiers; [a-z\s]* skips those, and we just
            # check that the soft modifier is applied to a supported statement.
            (r'\b(transparent|opaque|infix|open|inline)\b(?=[a-z\s]*\b'
             r'(def|val|var|given|type|class|trait|object|enum)\b)', Keyword),
        ],
        'annotations': [
            (rf'@{idrest}', Name.Decorator),
        ],
        'using': [
            # using is a soft keyword, can only be used in the first position of
            # a parameter or argument list.
            (r'(\()(\s*)(using)(\s)', bygroups(Punctuation, Whitespace, Keyword, Whitespace)),
        ],
        'declarations': [
            (rf'\b(def)\b(\s*){notStartOfComment}({anyId})?',
             bygroups(Keyword, Whitespace, Name.Function)),
            (rf'\b(trait)\b(\s*){notStartOfComment}({anyId})?',
                bygroups(Keyword, Whitespace, Name.Class)),
            (rf'\b(?:(case)(\s+))?(class|object|enum)\b(\s*){notStartOfComment}({anyId})?',
                bygroups(Keyword, Whitespace, Keyword, Whitespace, Name.Class)),
            (rf'(?<!\.)\b(type)\b(\s*){notStartOfComment}({anyId})?',
                bygroups(Keyword, Whitespace, Name.Class)),
            (r'\b(val|var)\b', Keyword.Declaration),
            (rf'\b(package)(\s+)(object)\b(\s*){notStartOfComment}({anyId})?',
                bygroups(Keyword, Whitespace, Keyword, Whitespace, Name.Namespace)),
            (r'\b(package)(\s+)', bygroups(Keyword, Whitespace), 'package'),
            (rf'\b(given)\b(\s*)({idUpper})',
                bygroups(Keyword, Whitespace, Name.Class)),
            (rf'\b(given)\b(\s*)({anyId})?',
                bygroups(Keyword, Whitespace, Name)),
        ],
        'inheritance': [
            (r'\b(extends|with|derives)\b(\s*)'
             rf'({idUpper}|{backQuotedId}|(?=\([^\)]+=>)|(?={plainid})|(?="))?',
                bygroups(Keyword, Whitespace, Name.Class)),
        ],
        'extension': [
            (r'\b(extension)(\s+)(?=[\[\(])', bygroups(Keyword, Whitespace)),
        ],
        'end': [
            # end is a soft keyword, should only be highlighted in certain cases
            (r'\b(end)(\s+)(if|while|for|match|new|extension|val|var)\b',
                bygroups(Keyword, Whitespace, Keyword)),
            (rf'\b(end)(\s+)({idUpper}){endOfLineMaybeWithComment}',
                bygroups(Keyword, Whitespace, Name.Class)),
            (rf'\b(end)(\s+)({backQuotedId}|{plainid})?{endOfLineMaybeWithComment}',
                bygroups(Keyword, Whitespace, Name.Namespace)),
        ],
        'punctuation': [
            (r'[{}()\[\];,.]', Punctuation),
            (r'(?<!:):(?!:)', Punctuation),
        ],
        'keywords': [
            (words(keywords, prefix=r'\b', suffix=r'\b'), Keyword),
        ],
        'operators': [
            (rf'({opchar}{{2,}})(\s+)', bygroups(Operator, Whitespace)),
            (r'/(?![/*])', Operator),
            (words(operators), Operator),
            (rf'(?<!{opchar})(!|&&|\|\|)(?!{opchar})', Operator),
        ],
        'constants': [
            (r'\b(this|super)\b', Name.Builtin.Pseudo),
            (r'(true|false|null)\b', Keyword.Constant),
            (r'0[xX][0-9a-fA-F_]*', Number.Hex),
            (r'([0-9][0-9_]*\.[0-9][0-9_]*|\.[0-9][0-9_]*)'
             r'([eE][+-]?[0-9][0-9_]*)?[fFdD]?', Number.Float),
            (r'[0-9]+([eE][+-]?[0-9]+)?[fFdD]', Number.Float),
            (r'[0-9]+([eE][+-]?[0-9]+)[fFdD]?', Number.Float),
            (r'[0-9]+[lL]', Number.Integer.Long),
            (r'[0-9]+', Number.Integer),
            (r'""".*?"""(?!")', String),
            (r'"(\\\\|\\"|[^"])*"', String),
            (r"(')(\\.)(')", bygroups(String.Char, String.Escape, String.Char)),
            (r"'[^\\]'|'\\u[0-9a-fA-F]{4}'", String.Char),
        ],
        "strings": [
            (r'[fs]"""', String, 'interpolated-string-triple'),
            (r'[fs]"', String, 'interpolated-string'),
            (r'raw"(\\\\|\\"|[^"])*"', String),
        ],
        'symbols': [
            (rf"('{plainid})(?!')", String.Symbol),
        ],
        'singleton-type': [
            (r'(\.)(type)\b', bygroups(Punctuation, Keyword)),
        ],
        'inline': [
            # inline is a soft modifier, only highlighted if followed by if,
            # match or parameters.
            (rf'\b(inline)(?=\s+({plainid}|{backQuotedId})\s*:)',
                Keyword),
            (r'\b(inline)\b(?=(?:.(?!\b(?:val|def|given)\b))*\b(if|match)\b)',
                Keyword),
        ],
        'quoted': [
            # '{...} or ${...}
            (r"['$]\{(?!')", Punctuation),
            # '[...]
            (r"'\[(?!')", Punctuation),
        ],
        'names': [
            (idUpper, Name.Class),
            (anyId, Name),
        ],

        # States
        'comment': [
            (r'[^/*]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ],
        'import-path': [
            (r'(?<=[\n;:])', Text, '#pop'),
            include('comments'),
            (r'\b(given)\b', Keyword),
            include('qualified-name'),
            (r'\{', Punctuation, 'import-path-curly-brace'),
        ],
        'import-path-curly-brace': [
            include('whitespace'),
            include('comments'),
            (r'\b(given)\b', Keyword),
            (r'=>', Operator),
            (r'\}', Punctuation, '#pop'),
            (r',', Punctuation),
            (r'[\[\]]', Punctuation),
            include('qualified-name'),
        ],
        'export-path': [
            (r'(?<=[\n;:])', Text, '#pop'),
            include('comments'),
            include('qualified-name'),
            (r'\{', Punctuation, 'export-path-curly-brace'),
        ],
        'export-path-curly-brace': [
            include('whitespace'),
            include('comments'),
            (r'=>', Operator),
            (r'\}', Punctuation, '#pop'),
            (r',', Punctuation),
            include('qualified-name'),
        ],
        'package': [
            (r'(?<=[\n;])', Text, '#pop'),
            (r':', Punctuation, '#pop'),
            include('comments'),
            include('qualified-name'),
        ],
        'interpolated-string-triple': [
            (r'"""(?!")', String, '#pop'),
            (r'"', String),
            include('interpolated-string-common'),
        ],
        'interpolated-string': [
            (r'"', String, '#pop'),
            include('interpolated-string-common'),
        ],
        'interpolated-string-brace': [
            (r'\}', String.Interpol, '#pop'),
            (r'\{', Punctuation, 'interpolated-string-nested-brace'),
            include('root'),
        ],
        'interpolated-string-nested-brace': [
            (r'\{', Punctuation, '#push'),
            (r'\}', Punctuation, '#pop'),
            include('root'),
        ],

        # Helpers
        'qualified-name': [
            (idUpper, Name.Class),
            (rf'({anyId})(\.)', bygroups(Name.Namespace, Punctuation)),
            (r'\.', Punctuation),
            (anyId, Name),
            (r'[^\S\n]+', Whitespace),
        ],
        'interpolated-string-common': [
            (r'[^"$\\]+', String),
            (r'\$\$', String.Escape),
            (rf'(\$)({simpleInterpolatedVariable})',
                bygroups(String.Interpol, Name)),
            (r'\$\{', String.Interpol, 'interpolated-string-brace'),
            (r'\\.', String),
        ],
    }


class GosuLexer(RegexLexer):
    """
    For Gosu source code.
    """

    name = 'Gosu'
    aliases = ['gosu']
    filenames = ['*.gs', '*.gsx', '*.gsp', '*.vark']
    mimetypes = ['text/x-gosu']
    url = 'https://gosu-lang.github.io'
    version_added = '1.5'

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            # method names
            (r'^(\s*(?:[a-zA-Z_][\w.\[\]]*\s+)+?)'  # modifiers etc.
             r'([a-zA-Z_]\w*)'                       # method name
             r'(\s*)(\()',                           # signature start
             bygroups(using(this), Name.Function, Whitespace, Operator)),
            (r'[^\S\n]+', Whitespace),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'@[a-zA-Z_][\w.]*', Name.Decorator),
            (r'(in|as|typeof|statictypeof|typeis|typeas|if|else|foreach|for|'
             r'index|while|do|continue|break|return|try|catch|finally|this|'
             r'throw|new|switch|case|default|eval|super|outer|classpath|'
             r'using)\b', Keyword),
            (r'(var|delegate|construct|function|private|internal|protected|'
             r'public|abstract|override|final|static|extends|transient|'
             r'implements|represents|readonly)\b', Keyword.Declaration),
            (r'(property)(\s+)(get|set)?', bygroups(Keyword.Declaration, Whitespace, Keyword.Declaration)),
            (r'(boolean|byte|char|double|float|int|long|short|void|block)\b',
             Keyword.Type),
            (r'(package)(\s+)', bygroups(Keyword.Namespace, Whitespace)),
            (r'(true|false|null|NaN|Infinity)\b', Keyword.Constant),
            (r'(class|interface|enhancement|enum)(\s+)([a-zA-Z_]\w*)',
             bygroups(Keyword.Declaration, Whitespace, Name.Class)),
            (r'(uses)(\s+)([\w.]+\*?)',
             bygroups(Keyword.Namespace, Whitespace, Name.Namespace)),
            (r'"', String, 'string'),
            (r'(\??[.#])([a-zA-Z_]\w*)',
             bygroups(Operator, Name.Attribute)),
            (r'(:)([a-zA-Z_]\w*)',
             bygroups(Operator, Name.Attribute)),
            (r'[a-zA-Z_$]\w*', Name),
            (r'and|or|not|[\\~^*!%&\[\](){}<>|+=:;,./?-]', Operator),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r'\n', Whitespace)
        ],
        'templateText': [
            (r'(\\<)|(\\\$)', String),
            (r'(<%@\s+)(extends|params)',
             bygroups(Operator, Name.Decorator), 'stringTemplate'),
            (r'<%!--.*?--%>', Comment.Multiline),
            (r'(<%)|(<%=)', Operator, 'stringTemplate'),
            (r'\$\{', Operator, 'stringTemplateShorthand'),
            (r'.', String)
        ],
        'string': [
            (r'"', String, '#pop'),
            include('templateText')
        ],
        'stringTemplate': [
            (r'"', String, 'string'),
            (r'%>', Operator, '#pop'),
            include('root')
        ],
        'stringTemplateShorthand': [
            (r'"', String, 'string'),
            (r'\{', Operator, 'stringTemplateShorthand'),
            (r'\}', Operator, '#pop'),
            include('root')
        ],
    }


class GosuTemplateLexer(Lexer):
    """
    For Gosu templates.
    """

    name = 'Gosu Template'
    aliases = ['gst']
    filenames = ['*.gst']
    mimetypes = ['text/x-gosu-template']
    url = 'https://gosu-lang.github.io'
    version_added = '1.5'

    def get_tokens_unprocessed(self, text):
        lexer = GosuLexer()
        stack = ['templateText']
        yield from lexer.get_tokens_unprocessed(text, stack)


class GroovyLexer(RegexLexer):
    """
    For Groovy source code.
    """

    name = 'Groovy'
    url = 'https://groovy-lang.org/'
    aliases = ['groovy']
    filenames = ['*.groovy','*.gradle']
    mimetypes = ['text/x-groovy']
    version_added = '1.5'

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            # Groovy allows a file to start with a shebang
            (r'#!(.*?)$', Comment.Preproc, 'base'),
            default('base'),
        ],
        'base': [
            (r'[^\S\n]+', Whitespace),
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'/\*.*?\*/', Comment.Multiline),
            # keywords: go before method names to avoid lexing "throw new XYZ"
            # as a method signature
            (r'(assert|break|case|catch|continue|default|do|else|finally|for|'
             r'if|goto|instanceof|new|return|switch|this|throw|try|while|in|as)\b',
             Keyword),
            # method names
            (r'^(\s*(?:[a-zA-Z_][\w.\[\]]*\s+)+?)'  # return arguments
             r'('
             r'[a-zA-Z_]\w*'                        # method name
             r'|"(?:\\\\|\\[^\\]|[^"\\])*"'         # or double-quoted method name
             r"|'(?:\\\\|\\[^\\]|[^'\\])*'"         # or single-quoted method name
             r')'
             r'(\s*)(\()',                          # signature start
             bygroups(using(this), Name.Function, Whitespace, Operator)),
            (r'@[a-zA-Z_][\w.]*', Name.Decorator),
            (r'(abstract|const|enum|extends|final|implements|native|private|'
             r'protected|public|static|strictfp|super|synchronized|throws|'
             r'transient|volatile)\b', Keyword.Declaration),
            (r'(def|boolean|byte|char|double|float|int|long|short|void)\b',
             Keyword.Type),
            (r'(package)(\s+)', bygroups(Keyword.Namespace, Whitespace)),
            (r'(true|false|null)\b', Keyword.Constant),
            (r'(class|interface)(\s+)', bygroups(Keyword.Declaration, Whitespace),
             'class'),
            (r'(import)(\s+)', bygroups(Keyword.Namespace, Whitespace), 'import'),
            (r'""".*?"""', String.Double),
            (r"'''.*?'''", String.Single),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r'\$/((?!/\$).)*/\$', String),
            (r'/(\\\\|\\[^\\]|[^/\\])*/', String),
            (r"'\\.'|'[^\\]'|'\\u[0-9a-fA-F]{4}'", String.Char),
            (r'(\.)([a-zA-Z_]\w*)', bygroups(Operator, Name.Attribute)),
            (r'[a-zA-Z_]\w*:', Name.Label),
            (r'[a-zA-Z_$]\w*', Name),
            (r'[~^*!%&\[\](){}<>|+=:;,./?-]', Operator),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+L?', Number.Integer),
            (r'\n', Whitespace)
        ],
        'class': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'[\w.]+\*?', Name.Namespace, '#pop')
        ],
    }

    def analyse_text(text):
        return shebang_matches(text, r'groovy')


class IokeLexer(RegexLexer):
    """
    For Ioke (a strongly typed, dynamic,
    prototype based programming language) source.
    """
    name = 'Ioke'
    url = 'https://ioke.org/'
    filenames = ['*.ik']
    aliases = ['ioke', 'ik']
    mimetypes = ['text/x-iokesrc']
    version_added = '1.4'
    tokens = {
        'interpolatableText': [
            (r'(\\b|\\e|\\t|\\n|\\f|\\r|\\"|\\\\|\\#|\\\Z|\\u[0-9a-fA-F]{1,4}'
             r'|\\[0-3]?[0-7]?[0-7])', String.Escape),
            (r'#\{', Punctuation, 'textInterpolationRoot')
        ],

        'text': [
            (r'(?<!\\)"', String, '#pop'),
            include('interpolatableText'),
            (r'[^"]', String)
        ],

        'documentation': [
            (r'(?<!\\)"', String.Doc, '#pop'),
            include('interpolatableText'),
            (r'[^"]', String.Doc)
        ],

        'textInterpolationRoot': [
            (r'\}', Punctuation, '#pop'),
            include('root')
        ],

        'slashRegexp': [
            (r'(?<!\\)/[im-psux]*', String.Regex, '#pop'),
            include('interpolatableText'),
            (r'\\/', String.Regex),
            (r'[^/]', String.Regex)
        ],

        'squareRegexp': [
            (r'(?<!\\)][im-psux]*', String.Regex, '#pop'),
            include('interpolatableText'),
            (r'\\]', String.Regex),
            (r'[^\]]', String.Regex)
        ],

        'squareText': [
            (r'(?<!\\)]', String, '#pop'),
            include('interpolatableText'),
            (r'[^\]]', String)
        ],

        'root': [
            (r'\n', Whitespace),
            (r'\s+', Whitespace),

            # Comments
            (r';(.*?)\n', Comment),
            (r'\A#!(.*?)\n', Comment),

            # Regexps
            (r'#/', String.Regex, 'slashRegexp'),
            (r'#r\[', String.Regex, 'squareRegexp'),

            # Symbols
            (r':[\w!:?]+', String.Symbol),
            (r'[\w!:?]+:(?![\w!?])', String.Other),
            (r':"(\\\\|\\[^\\]|[^"\\])*"', String.Symbol),

            # Documentation
            (r'((?<=fn\()|(?<=fnx\()|(?<=method\()|(?<=macro\()|(?<=lecro\()'
             r'|(?<=syntax\()|(?<=dmacro\()|(?<=dlecro\()|(?<=dlecrox\()'
             r'|(?<=dsyntax\())(\s*)"', String.Doc, 'documentation'),

            # Text
            (r'"', String, 'text'),
            (r'#\[', String, 'squareText'),

            # Mimic
            (r'\w[\w!:?]+(?=\s*=.*mimic\s)', Name.Entity),

            # Assignment
            (r'[a-zA-Z_][\w!:?]*(?=[\s]*[+*/-]?=[^=].*($|\.))',
             Name.Variable),

            # keywords
            (r'(break|cond|continue|do|ensure|for|for:dict|for:set|if|let|'
             r'loop|p:for|p:for:dict|p:for:set|return|unless|until|while|'
             r'with)(?![\w!:?])', Keyword.Reserved),

            # Origin
            (r'(eval|mimic|print|println)(?![\w!:?])', Keyword),

            # Base
            (r'(cell\?|cellNames|cellOwner\?|cellOwner|cells|cell|'
             r'documentation|hash|identity|mimic|removeCell\!|undefineCell\!)'
             r'(?![\w!:?])', Keyword),

            # Ground
            (r'(stackTraceAsText)(?![\w!:?])', Keyword),

            # DefaultBehaviour Literals
            (r'(dict|list|message|set)(?![\w!:?])', Keyword.Reserved),

            # DefaultBehaviour Case
            (r'(case|case:and|case:else|case:nand|case:nor|case:not|case:or|'
             r'case:otherwise|case:xor)(?![\w!:?])', Keyword.Reserved),

            # DefaultBehaviour Reflection
            (r'(asText|become\!|derive|freeze\!|frozen\?|in\?|is\?|kind\?|'
             r'mimic\!|mimics|mimics\?|prependMimic\!|removeAllMimics\!|'
             r'removeMimic\!|same\?|send|thaw\!|uniqueHexId)'
             r'(?![\w!:?])', Keyword),

            # DefaultBehaviour Aspects
            (r'(after|around|before)(?![\w!:?])', Keyword.Reserved),

            # DefaultBehaviour
            (r'(kind|cellDescriptionDict|cellSummary|genSym|inspect|notice)'
             r'(?![\w!:?])', Keyword),
            (r'(use|destructuring)', Keyword.Reserved),

            # DefaultBehavior BaseBehavior
            (r'(cell\?|cellOwner\?|cellOwner|cellNames|cells|cell|'
             r'documentation|identity|removeCell!|undefineCell)'
             r'(?![\w!:?])', Keyword),

            # DefaultBehavior Internal
            (r'(internal:compositeRegexp|internal:concatenateText|'
             r'internal:createDecimal|internal:createNumber|'
             r'internal:createRegexp|internal:createText)'
             r'(?![\w!:?])', Keyword.Reserved),

            # DefaultBehaviour Conditions
            (r'(availableRestarts|bind|error\!|findRestart|handle|'
             r'invokeRestart|rescue|restart|signal\!|warn\!)'
             r'(?![\w!:?])', Keyword.Reserved),

            # constants
            (r'(nil|false|true)(?![\w!:?])', Name.Constant),

            # names
            (r'(Arity|Base|Call|Condition|DateTime|Aspects|Pointcut|'
             r'Assignment|BaseBehavior|Boolean|Case|AndCombiner|Else|'
             r'NAndCombiner|NOrCombiner|NotCombiner|OrCombiner|XOrCombiner|'
             r'Conditions|Definitions|FlowControl|Internal|Literals|'
             r'Reflection|DefaultMacro|DefaultMethod|DefaultSyntax|Dict|'
             r'FileSystem|Ground|Handler|Hook|IO|IokeGround|Struct|'
             r'LexicalBlock|LexicalMacro|List|Message|Method|Mixins|'
             r'NativeMethod|Number|Origin|Pair|Range|Reflector|Regexp Match|'
             r'Regexp|Rescue|Restart|Runtime|Sequence|Set|Symbol|'
             r'System|Text|Tuple)(?![\w!:?])', Name.Builtin),

            # functions
            ('(generateMatchMethod|aliasMethod|\u03bb|\u028E|fnx|fn|method|'
             'dmacro|dlecro|syntax|macro|dlecrox|lecrox|lecro|syntax)'
             '(?![\\w!:?])', Name.Function),

            # Numbers
            (r'-?0[xX][0-9a-fA-F]+', Number.Hex),
            (r'-?(\d+\.?\d*|\d*\.\d+)([eE][+-]?[0-9]+)?', Number.Float),
            (r'-?\d+', Number.Integer),

            (r'#\(', Punctuation),

            # Operators
            (r'(&&>>|\|\|>>|\*\*>>|:::|::|\.\.\.|===|\*\*>|\*\*=|&&>|&&=|'
             r'\|\|>|\|\|=|\->>|\+>>|!>>|<>>>|<>>|&>>|%>>|#>>|@>>|/>>|\*>>|'
             r'\?>>|\|>>|\^>>|~>>|\$>>|=>>|<<=|>>=|<=>|<\->|=~|!~|=>|\+\+|'
             r'\-\-|<=|>=|==|!=|&&|\.\.|\+=|\-=|\*=|\/=|%=|&=|\^=|\|=|<\-|'
             r'\+>|!>|<>|&>|%>|#>|\@>|\/>|\*>|\?>|\|>|\^>|~>|\$>|<\->|\->|'
             r'<<|>>|\*\*|\?\||\?&|\|\||>|<|\*|\/|%|\+|\-|&|\^|\||=|\$|!|~|'
             r'\?|#|\u2260|\u2218|\u2208|\u2209)', Operator),
            (r'(and|nand|or|xor|nor|return|import)(?![\w!?])',
             Operator),

            # Punctuation
            (r'(\`\`|\`|\'\'|\'|\.|\,|@@|@|\[|\]|\(|\)|\{|\})', Punctuation),

            # kinds
            (r'[A-Z][\w!:?]*', Name.Class),

            # default cellnames
            (r'[a-z_][\w!:?]*', Name)
        ]
    }


class ClojureLexer(RegexLexer):
    """
    Lexer for Clojure source code.
    """
    name = 'Clojure'
    url = 'http://clojure.org/'
    aliases = ['clojure', 'clj']
    filenames = ['*.clj', '*.cljc']
    mimetypes = ['text/x-clojure', 'application/x-clojure']
    version_added = '0.11'

    special_forms = (
        '.', 'def', 'do', 'fn', 'if', 'let', 'new', 'quote', 'var', 'loop'
    )

    # It's safe to consider 'ns' a declaration thing because it defines a new
    # namespace.
    declarations = (
        'def-', 'defn', 'defn-', 'defmacro', 'defmulti', 'defmethod',
        'defstruct', 'defonce', 'declare', 'definline', 'definterface',
        'defprotocol', 'defrecord', 'deftype', 'defproject', 'ns'
    )

    builtins = (
        '*', '+', '-', '->', '/', '<', '<=', '=', '==', '>', '>=', '..',
        'accessor', 'agent', 'agent-errors', 'aget', 'alength', 'all-ns',
        'alter', 'and', 'append-child', 'apply', 'array-map', 'aset',
        'aset-boolean', 'aset-byte', 'aset-char', 'aset-double', 'aset-float',
        'aset-int', 'aset-long', 'aset-short', 'assert', 'assoc', 'await',
        'await-for', 'bean', 'binding', 'bit-and', 'bit-not', 'bit-or',
        'bit-shift-left', 'bit-shift-right', 'bit-xor', 'boolean', 'branch?',
        'butlast', 'byte', 'cast', 'char', 'children', 'class',
        'clear-agent-errors', 'comment', 'commute', 'comp', 'comparator',
        'complement', 'concat', 'conj', 'cons', 'constantly', 'cond', 'if-not',
        'construct-proxy', 'contains?', 'count', 'create-ns', 'create-struct',
        'cycle', 'dec',  'deref', 'difference', 'disj', 'dissoc', 'distinct',
        'doall', 'doc', 'dorun', 'doseq', 'dosync', 'dotimes', 'doto',
        'double', 'down', 'drop', 'drop-while', 'edit', 'end?', 'ensure',
        'eval', 'every?', 'false?', 'ffirst', 'file-seq', 'filter', 'find',
        'find-doc', 'find-ns', 'find-var', 'first', 'float', 'flush', 'for',
        'fnseq', 'frest', 'gensym', 'get-proxy-class', 'get',
        'hash-map', 'hash-set', 'identical?', 'identity', 'if-let', 'import',
        'in-ns', 'inc', 'index', 'insert-child', 'insert-left', 'insert-right',
        'inspect-table', 'inspect-tree', 'instance?', 'int', 'interleave',
        'intersection', 'into', 'into-array', 'iterate', 'join', 'key', 'keys',
        'keyword', 'keyword?', 'last', 'lazy-cat', 'lazy-cons', 'left',
        'lefts', 'line-seq', 'list*', 'list', 'load', 'load-file',
        'locking', 'long', 'loop', 'macroexpand', 'macroexpand-1',
        'make-array', 'make-node', 'map', 'map-invert', 'map?', 'mapcat',
        'max', 'max-key', 'memfn', 'merge', 'merge-with', 'meta', 'min',
        'min-key', 'name', 'namespace', 'neg?', 'new', 'newline', 'next',
        'nil?', 'node', 'not', 'not-any?', 'not-every?', 'not=', 'ns-imports',
        'ns-interns', 'ns-map', 'ns-name', 'ns-publics', 'ns-refers',
        'ns-resolve', 'ns-unmap', 'nth', 'nthrest', 'or', 'parse', 'partial',
        'path', 'peek', 'pop', 'pos?', 'pr', 'pr-str', 'print', 'print-str',
        'println', 'println-str', 'prn', 'prn-str', 'project', 'proxy',
        'proxy-mappings', 'quot', 'rand', 'rand-int', 'range', 're-find',
        're-groups', 're-matcher', 're-matches', 're-pattern', 're-seq',
        'read', 'read-line', 'reduce', 'ref', 'ref-set', 'refer', 'rem',
        'remove', 'remove-method', 'remove-ns', 'rename', 'rename-keys',
        'repeat', 'replace', 'replicate', 'resolve', 'rest', 'resultset-seq',
        'reverse', 'rfirst', 'right', 'rights', 'root', 'rrest', 'rseq',
        'second', 'select', 'select-keys', 'send', 'send-off', 'seq',
        'seq-zip', 'seq?', 'set', 'short', 'slurp', 'some', 'sort',
        'sort-by', 'sorted-map', 'sorted-map-by', 'sorted-set',
        'special-symbol?', 'split-at', 'split-with', 'str', 'string?',
        'struct', 'struct-map', 'subs', 'subvec', 'symbol', 'symbol?',
        'sync', 'take', 'take-nth', 'take-while', 'test', 'time', 'to-array',
        'to-array-2d', 'tree-seq', 'true?', 'union', 'up', 'update-proxy',
        'val', 'vals', 'var-get', 'var-set', 'var?', 'vector', 'vector-zip',
        'vector?', 'when', 'when-first', 'when-let', 'when-not',
        'with-local-vars', 'with-meta', 'with-open', 'with-out-str',
        'xml-seq', 'xml-zip', 'zero?', 'zipmap', 'zipper')

    # valid names for identifiers
    # well, names can only not consist fully of numbers
    # but this should be good enough for now

    # TODO / should divide keywords/symbols into namespace/rest
    # but that's hard, so just pretend / is part of the name
    valid_name = r'(?!#)[\w!$%*+<=>?/.#|-]+'

    tokens = {
        'root': [
            # the comments - always starting with semicolon
            # and going to the end of the line
            (r';.*$', Comment.Single),

            # whitespaces - usually not relevant
            (r',+', Text),
            (r'\s+', Whitespace),

            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+/\d+', Number),
            (r'-?\d+', Number.Integer),
            (r'0x-?[abcdef\d]+', Number.Hex),

            # strings, symbols and characters
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
            (r"'" + valid_name, String.Symbol),
            (r"\\(.|[a-z]+)", String.Char),

            # keywords
            (r'::?#?' + valid_name, String.Symbol),

            # special operators
            (r'~@|[`\'#^~&@]', Operator),

            # highlight the special forms
            (words(special_forms, suffix=' '), Keyword),

            # Technically, only the special forms are 'keywords'. The problem
            # is that only treating them as keywords means that things like
            # 'defn' and 'ns' need to be highlighted as builtins. This is ugly
            # and weird for most styles. So, as a compromise we're going to
            # highlight them as Keyword.Declarations.
            (words(declarations, suffix=' '), Keyword.Declaration),

            # highlight the builtins
            (words(builtins, suffix=' '), Name.Builtin),

            # the remaining functions
            (r'(?<=\()' + valid_name, Name.Function),

            # find the remaining variables
            (valid_name, Name.Variable),

            # Clojure accepts vector notation
            (r'(\[|\])', Punctuation),

            # Clojure accepts map notation
            (r'(\{|\})', Punctuation),

            # the famous parentheses!
            (r'(\(|\))', Punctuation),
        ],
    }


class ClojureScriptLexer(ClojureLexer):
    """
    Lexer for ClojureScript source code.
    """
    name = 'ClojureScript'
    url = 'http://clojure.org/clojurescript'
    aliases = ['clojurescript', 'cljs']
    filenames = ['*.cljs']
    mimetypes = ['text/x-clojurescript', 'application/x-clojurescript']
    version_added = '2.0'


class TeaLangLexer(RegexLexer):
    """
    For Tea source code. Only used within a
    TeaTemplateLexer.

    .. versionadded:: 1.5
    """

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            # method names
            (r'^(\s*(?:[a-zA-Z_][\w\.\[\]]*\s+)+?)'  # return arguments
             r'([a-zA-Z_]\w*)'                       # method name
             r'(\s*)(\()',                           # signature start
             bygroups(using(this), Name.Function, Whitespace, Operator)),
            (r'[^\S\n]+', Whitespace),
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'@[a-zA-Z_][\w\.]*', Name.Decorator),
            (r'(and|break|else|foreach|if|in|not|or|reverse)\b',
             Keyword),
            (r'(as|call|define)\b', Keyword.Declaration),
            (r'(true|false|null)\b', Keyword.Constant),
            (r'(template)(\s+)', bygroups(Keyword.Declaration, Whitespace), 'template'),
            (r'(import)(\s+)', bygroups(Keyword.Namespace, Whitespace), 'import'),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r'(\.)([a-zA-Z_]\w*)', bygroups(Operator, Name.Attribute)),
            (r'[a-zA-Z_]\w*:', Name.Label),
            (r'[a-zA-Z_\$]\w*', Name),
            (r'(isa|[.]{3}|[.]{2}|[=#!<>+-/%&;,.\*\\\(\)\[\]\{\}])', Operator),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+L?', Number.Integer),
            (r'\n', Whitespace)
        ],
        'template': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'[\w.]+\*?', Name.Namespace, '#pop')
        ],
    }


class CeylonLexer(RegexLexer):
    """
    For Ceylon source code.
    """

    name = 'Ceylon'
    url = 'http://ceylon-lang.org/'
    aliases = ['ceylon']
    filenames = ['*.ceylon']
    mimetypes = ['text/x-ceylon']
    version_added = '1.6'

    flags = re.MULTILINE | re.DOTALL

    #: optional Comment or Whitespace
    _ws = r'(?:\s|//.*?\n|/[*].*?[*]/)+'

    tokens = {
        'root': [
            # method names
            (r'^(\s*(?:[a-zA-Z_][\w.\[\]]*\s+)+?)'  # return arguments
             r'([a-zA-Z_]\w*)'                      # method name
             r'(\s*)(\()',                          # signature start
             bygroups(using(this), Name.Function, Whitespace, Operator)),
            (r'[^\S\n]+', Whitespace),
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'/\*', Comment.Multiline, 'comment'),
            (r'(shared|abstract|formal|default|actual|variable|deprecated|small|'
             r'late|literal|doc|by|see|throws|optional|license|tagged|final|native|'
             r'annotation|sealed)\b', Name.Decorator),
            (r'(break|case|catch|continue|else|finally|for|in|'
             r'if|return|switch|this|throw|try|while|is|exists|dynamic|'
             r'nonempty|then|outer|assert|let)\b', Keyword),
            (r'(abstracts|extends|satisfies|'
             r'super|given|of|out|assign)\b', Keyword.Declaration),
            (r'(function|value|void|new)\b',
             Keyword.Type),
            (r'(assembly|module|package)(\s+)', bygroups(Keyword.Namespace, Whitespace)),
            (r'(true|false|null)\b', Keyword.Constant),
            (r'(class|interface|object|alias)(\s+)',
             bygroups(Keyword.Declaration, Whitespace), 'class'),
            (r'(import)(\s+)', bygroups(Keyword.Namespace, Whitespace), 'import'),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
            (r"'\\.'|'[^\\]'|'\\\{#[0-9a-fA-F]{4}\}'", String.Char),
            (r'(\.)([a-z_]\w*)',
             bygroups(Operator, Name.Attribute)),
            (r'[a-zA-Z_]\w*:', Name.Label),
            (r'[a-zA-Z_]\w*', Name),
            (r'[~^*!%&\[\](){}<>|+=:;,./?-]', Operator),
            (r'\d{1,3}(_\d{3})+\.\d{1,3}(_\d{3})+[kMGTPmunpf]?', Number.Float),
            (r'\d{1,3}(_\d{3})+\.[0-9]+([eE][+-]?[0-9]+)?[kMGTPmunpf]?',
             Number.Float),
            (r'[0-9][0-9]*\.\d{1,3}(_\d{3})+[kMGTPmunpf]?', Number.Float),
            (r'[0-9][0-9]*\.[0-9]+([eE][+-]?[0-9]+)?[kMGTPmunpf]?',
             Number.Float),
            (r'#([0-9a-fA-F]{4})(_[0-9a-fA-F]{4})+', Number.Hex),
            (r'#[0-9a-fA-F]+', Number.Hex),
            (r'\$([01]{4})(_[01]{4})+', Number.Bin),
            (r'\$[01]+', Number.Bin),
            (r'\d{1,3}(_\d{3})+[kMGTP]?', Number.Integer),
            (r'[0-9]+[kMGTP]?', Number.Integer),
            (r'\n', Whitespace)
        ],
        'class': [
            (r'[A-Za-z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'[a-z][\w.]*',
             Name.Namespace, '#pop')
        ],
        'comment': [
            (r'[^*/]', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline)
        ],
    }


class KotlinLexer(RegexLexer):
    """
    For Kotlin source code.
    """

    name = 'Kotlin'
    url = 'http://kotlinlang.org/'
    aliases = ['kotlin']
    filenames = ['*.kt', '*.kts']
    mimetypes = ['text/x-kotlin']
    version_added = '1.5'

    flags = re.MULTILINE | re.DOTALL

    kt_name = ('@?[_' + uni.combine('Lu', 'Ll', 'Lt', 'Lm', 'Nl') + ']' +
               '[' + uni.combine('Lu', 'Ll', 'Lt', 'Lm', 'Nl', 'Nd', 'Pc', 'Cf',
                                 'Mn', 'Mc') + ']*')

    kt_space_name = ('@?[_' + uni.combine('Lu', 'Ll', 'Lt', 'Lm', 'Nl') + ']' +
               '[' + uni.combine('Lu', 'Ll', 'Lt', 'Lm', 'Nl', 'Nd', 'Pc', 'Cf',
                                 'Mn', 'Mc', 'Zs')
                + r'\'~!%^&*()+=|\[\]:;,.<>/\?-]*')

    kt_id = '(' + kt_name + '|`' + kt_space_name + '`)'

    modifiers = (r'actual|abstract|annotation|companion|const|crossinline|'
                r'data|enum|expect|external|final|infix|inline|inner|'
                r'internal|lateinit|noinline|open|operator|override|private|'
                r'protected|public|sealed|suspend|tailrec|value')

    tokens = {
        'root': [
            # Whitespaces
            (r'[^\S\n]+', Whitespace),
            (r'\s+', Whitespace),
            (r'\\$', String.Escape),  # line continuation
            (r'\n', Whitespace),
            # Comments
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'^(#!/.+?)(\n)', bygroups(Comment.Single, Whitespace)),  # shebang for kotlin scripts
            (r'/[*].*?[*]/', Comment.Multiline),
            # Keywords
            (r'as\?', Keyword),
            (r'(as|break|by|catch|constructor|continue|do|dynamic|else|finally|'
             r'get|for|if|init|[!]*in|[!]*is|out|reified|return|set|super|this|'
             r'throw|try|typealias|typeof|vararg|when|where|while)\b', Keyword),
            (r'it\b', Name.Builtin),
            # Built-in types
            (words(('Boolean?', 'Byte?', 'Char?', 'Double?', 'Float?',
             'Int?', 'Long?', 'Short?', 'String?', 'Any?', 'Unit?')), Keyword.Type),
            (words(('Boolean', 'Byte', 'Char', 'Double', 'Float',
             'Int', 'Long', 'Short', 'String', 'Any', 'Unit'), suffix=r'\b'), Keyword.Type),
            # Constants
            (r'(true|false|null)\b', Keyword.Constant),
            # Imports
            (r'(package|import)(\s+)(\S+)', bygroups(Keyword, Whitespace, Name.Namespace)),
            # Dot access
            (r'(\?\.)((?:[^\W\d]|\$)[\w$]*)', bygroups(Operator, Name.Attribute)),
            (r'(\.)((?:[^\W\d]|\$)[\w$]*)', bygroups(Punctuation, Name.Attribute)),
            # Annotations
            (r'@[^\W\d][\w.]*', Name.Decorator),
            # Labels
            (r'[^\W\d][\w.]+@', Name.Decorator),
            # Object expression
            (r'(object)(\s+)(:)(\s+)', bygroups(Keyword, Whitespace, Punctuation, Whitespace), 'class'),
            # Types
            (r'((?:(?:' + modifiers + r'|fun)\s+)*)(class|interface|object)(\s+)',
             bygroups(using(this, state='modifiers'), Keyword.Declaration, Whitespace), 'class'),
            # Variables
            (r'(var|val)(\s+)(\()', bygroups(Keyword.Declaration, Whitespace, Punctuation),
             'destructuring_assignment'),
            (r'((?:(?:' + modifiers + r')\s+)*)(var|val)(\s+)',
             bygroups(using(this, state='modifiers'), Keyword.Declaration, Whitespace), 'variable'),
            # Functions
            (r'((?:(?:' + modifiers + r')\s+)*)(fun)(\s+)',
             bygroups(using(this, state='modifiers'), Keyword.Declaration, Whitespace), 'function'),
            # Operators
            (r'::|!!|\?[:.]', Operator),
            (r'[~^*!%&\[\]<>|+=/?-]', Operator),
            # Punctuation
            (r'[{}();:.,]', Punctuation),
            # Strings
            (r'"""', String, 'multiline_string'),
            (r'"', String, 'string'),
            (r"'\\.'|'[^\\]'", String.Char),
            # Numbers
            (r"[0-9](\.[0-9]*)?([eE][+-][0-9]+)?[flFL]?|"
             r"0[xX][0-9a-fA-F]+[Ll]?", Number),
            # Identifiers
            (r'' + kt_id + r'((\?[^.])?)', Name) # additionally handle nullable types
        ],
        'class': [
            (kt_id, Name.Class, '#pop')
        ],
        'variable': [
            (kt_id, Name.Variable, '#pop')
        ],
        'destructuring_assignment': [
            (r',', Punctuation),
            (r'\s+', Whitespace),
            (kt_id, Name.Variable),
            (r'(:)(\s+)(' + kt_id + ')', bygroups(Punctuation, Whitespace, Name)),
            (r'<', Operator, 'generic'),
            (r'\)', Punctuation, '#pop')
        ],
        'function': [
            (r'<', Operator, 'generic'),
            (r'' + kt_id + r'(\.)' + kt_id, bygroups(Name, Punctuation, Name.Function), '#pop'),
            (kt_id, Name.Function, '#pop')
        ],
        'generic': [
            (r'(>)(\s*)', bygroups(Operator, Whitespace), '#pop'),
            (r':', Punctuation),
            (r'(reified|out|in)\b', Keyword),
            (r',', Punctuation),
            (r'\s+', Whitespace),
            (kt_id, Name)
        ],
        'modifiers': [
            (r'\w+', Keyword.Declaration),
            (r'\s+', Whitespace),
            default('#pop')
        ],
        'string': [
            (r'"', String, '#pop'),
            include('string_common')
        ],
        'multiline_string': [
            (r'"""', String, '#pop'),
            (r'"', String),
            include('string_common')
        ],
        'string_common': [
            (r'\\\\', String),  # escaped backslash
            (r'\\"', String),  # escaped quote
            (r'\\', String),  # bare backslash
            (r'\$\{', String.Interpol, 'interpolation'),
            (r'(\$)(\w+)', bygroups(String.Interpol, Name)),
            (r'[^\\"$]+', String)
        ],
        'interpolation': [
            (r'"', String),
            (r'\$\{', String.Interpol, 'interpolation'),
            (r'\{', Punctuation, 'scope'),
            (r'\}', String.Interpol, '#pop'),
            include('root')
        ],
        'scope': [
            (r'\{', Punctuation, 'scope'),
            (r'\}', Punctuation, '#pop'),
            include('root')
        ]
    }


class XtendLexer(RegexLexer):
    """
    For Xtend source code.
    """

    name = 'Xtend'
    url = 'https://www.eclipse.org/xtend/'
    aliases = ['xtend']
    filenames = ['*.xtend']
    mimetypes = ['text/x-xtend']
    version_added = '1.6'

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            # method names
            (r'^(\s*(?:[a-zA-Z_][\w.\[\]]*\s+)+?)'  # return arguments
             r'([a-zA-Z_$][\w$]*)'                  # method name
             r'(\s*)(\()',                          # signature start
             bygroups(using(this), Name.Function, Whitespace, Operator)),
            (r'[^\S\n]+', Whitespace),
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'@[a-zA-Z_][\w.]*', Name.Decorator),
            (r'(assert|break|case|catch|continue|default|do|else|finally|for|'
             r'if|goto|instanceof|new|return|switch|this|throw|try|while|IF|'
             r'ELSE|ELSEIF|ENDIF|FOR|ENDFOR|SEPARATOR|BEFORE|AFTER)\b',
             Keyword),
            (r'(def|abstract|const|enum|extends|final|implements|native|private|'
             r'protected|public|static|strictfp|super|synchronized|throws|'
             r'transient|volatile|val|var)\b', Keyword.Declaration),
            (r'(boolean|byte|char|double|float|int|long|short|void)\b',
             Keyword.Type),
            (r'(package)(\s+)', bygroups(Keyword.Namespace, Whitespace)),
            (r'(true|false|null)\b', Keyword.Constant),
            (r'(class|interface)(\s+)', bygroups(Keyword.Declaration, Whitespace),
             'class'),
            (r'(import)(\s+)', bygroups(Keyword.Namespace, Whitespace), 'import'),
            (r"(''')", String, 'template'),
            (r'(\u00BB)', String, 'template'),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r'[a-zA-Z_]\w*:', Name.Label),
            (r'[a-zA-Z_$]\w*', Name),
            (r'[~^*!%&\[\](){}<>\|+=:;,./?-]', Operator),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+L?', Number.Integer),
            (r'\n', Whitespace)
        ],
        'class': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'[\w.]+\*?', Name.Namespace, '#pop')
        ],
        'template': [
            (r"'''", String, '#pop'),
            (r'\u00AB', String, '#pop'),
            (r'.', String)
        ],
    }


class PigLexer(RegexLexer):
    """
    For Pig Latin source code.
    """

    name = 'Pig'
    url = 'https://pig.apache.org/'
    aliases = ['pig']
    filenames = ['*.pig']
    mimetypes = ['text/x-pig']
    version_added = '2.0'

    flags = re.MULTILINE | re.IGNORECASE

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'--.*', Comment),
            (r'/\*[\w\W]*?\*/', Comment.Multiline),
            (r'\\$', String.Escape),
            (r'\\', Text),
            (r'\'(?:\\[ntbrf\\\']|\\u[0-9a-f]{4}|[^\'\\\n\r])*\'', String),
            include('keywords'),
            include('types'),
            include('builtins'),
            include('punct'),
            include('operators'),
            (r'[0-9]*\.[0-9]+(e[0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-f]+', Number.Hex),
            (r'[0-9]+L?', Number.Integer),
            (r'\n', Whitespace),
            (r'([a-z_]\w*)(\s*)(\()',
             bygroups(Name.Function, Whitespace, Punctuation)),
            (r'[()#:]', Text),
            (r'[^(:#\'")\s]+', Text),
            (r'\S+\s+', Text)   # TODO: make tests pass without \s+
        ],
        'keywords': [
            (r'(assert|and|any|all|arrange|as|asc|bag|by|cache|CASE|cat|cd|cp|'
             r'%declare|%default|define|dense|desc|describe|distinct|du|dump|'
             r'eval|exex|explain|filter|flatten|foreach|full|generate|group|'
             r'help|if|illustrate|import|inner|input|into|is|join|kill|left|'
             r'limit|load|ls|map|matches|mkdir|mv|not|null|onschema|or|order|'
             r'outer|output|parallel|pig|pwd|quit|register|returns|right|rm|'
             r'rmf|rollup|run|sample|set|ship|split|stderr|stdin|stdout|store|'
             r'stream|through|union|using|void)\b', Keyword)
        ],
        'builtins': [
            (r'(AVG|BinStorage|cogroup|CONCAT|copyFromLocal|copyToLocal|COUNT|'
             r'cross|DIFF|MAX|MIN|PigDump|PigStorage|SIZE|SUM|TextLoader|'
             r'TOKENIZE)\b', Name.Builtin)
        ],
        'types': [
            (r'(bytearray|BIGINTEGER|BIGDECIMAL|chararray|datetime|double|float|'
             r'int|long|tuple)\b', Keyword.Type)
        ],
        'punct': [
            (r'[;(){}\[\]]', Punctuation),
        ],
        'operators': [
            (r'[#=,./%+\-?]', Operator),
            (r'(eq|gt|lt|gte|lte|neq|matches)\b', Operator),
            (r'(==|<=|<|>=|>|!=)', Operator),
        ],
    }


class GoloLexer(RegexLexer):
    """
    For Golo source code.
    """

    name = 'Golo'
    url = 'http://golo-lang.org/'
    filenames = ['*.golo']
    aliases = ['golo']
    version_added = '2.0'

    tokens = {
        'root': [
            (r'[^\S\n]+', Whitespace),

            (r'#.*$', Comment),

            (r'(\^|\.\.\.|:|\?:|->|==|!=|=|\+|\*|%|/|<=|<|>=|>|=|\.)',
                Operator),
            (r'(?<=[^-])(-)(?=[^-])', Operator),

            (r'(?<=[^`])(is|isnt|and|or|not|oftype|in|orIfNull)\b', Operator.Word),
            (r'[]{}|(),[]', Punctuation),

            (r'(module|import)(\s+)',
                bygroups(Keyword.Namespace, Whitespace),
                'modname'),
            (r'\b([a-zA-Z_][\w$.]*)(::)',  bygroups(Name.Namespace, Punctuation)),
            (r'\b([a-zA-Z_][\w$]*(?:\.[a-zA-Z_][\w$]*)+)\b', Name.Namespace),

            (r'(let|var)(\s+)',
                bygroups(Keyword.Declaration, Whitespace),
                'varname'),
            (r'(struct)(\s+)',
                bygroups(Keyword.Declaration, Whitespace),
                'structname'),
            (r'(function)(\s+)',
                bygroups(Keyword.Declaration, Whitespace),
                'funcname'),

            (r'(null|true|false)\b', Keyword.Constant),
            (r'(augment|pimp'
             r'|if|else|case|match|return'
             r'|case|when|then|otherwise'
             r'|while|for|foreach'
             r'|try|catch|finally|throw'
             r'|local'
             r'|continue|break)\b', Keyword),

            (r'(map|array|list|set|vector|tuple)(\[)',
                bygroups(Name.Builtin, Punctuation)),
            (r'(print|println|readln|raise|fun'
             r'|asInterfaceInstance)\b', Name.Builtin),
            (r'(`?[a-zA-Z_][\w$]*)(\()',
                bygroups(Name.Function, Punctuation)),

            (r'-?[\d_]*\.[\d_]*([eE][+-]?\d[\d_]*)?F?', Number.Float),
            (r'0[0-7]+j?', Number.Oct),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'-?\d[\d_]*L', Number.Integer.Long),
            (r'-?\d[\d_]*', Number.Integer),

            (r'`?[a-zA-Z_][\w$]*', Name),
            (r'@[a-zA-Z_][\w$.]*', Name.Decorator),

            (r'"""', String, combined('stringescape', 'triplestring')),
            (r'"', String, combined('stringescape', 'doublestring')),
            (r"'", String, combined('stringescape', 'singlestring')),
            (r'----((.|\n)*?)----', String.Doc)

        ],

        'funcname': [
            (r'`?[a-zA-Z_][\w$]*', Name.Function, '#pop'),
        ],
        'modname': [
            (r'[a-zA-Z_][\w$.]*\*?', Name.Namespace, '#pop')
        ],
        'structname': [
            (r'`?[\w.]+\*?', Name.Class, '#pop')
        ],
        'varname': [
            (r'`?[a-zA-Z_][\w$]*', Name.Variable, '#pop'),
        ],
        'string': [
            (r'[^\\\'"\n]+', String),
            (r'[\'"\\]', String)
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'triplestring': [
            (r'"""', String, '#pop'),
            include('string'),
            (r'\n', String),
        ],
        'doublestring': [
            (r'"', String.Double, '#pop'),
            include('string'),
        ],
        'singlestring': [
            (r"'", String, '#pop'),
            include('string'),
        ],
        'operators': [
            (r'[#=,./%+\-?]', Operator),
            (r'(eq|gt|lt|gte|lte|neq|matches)\b', Operator),
            (r'(==|<=|<|>=|>|!=)', Operator),
        ],
    }


class JasminLexer(RegexLexer):
    """
    For Jasmin assembly code.
    """

    name = 'Jasmin'
    url = 'http://jasmin.sourceforge.net/'
    aliases = ['jasmin', 'jasminxt']
    filenames = ['*.j']
    version_added = '2.0'

    _whitespace = r' \n\t\r'
    _ws = rf'(?:[{_whitespace}]+)'
    _separator = rf'{_whitespace}:='
    _break = rf'(?=[{_separator}]|$)'
    _name = rf'[^{_separator}]+'
    _unqualified_name = rf'(?:[^{_separator}.;\[/]+)'

    tokens = {
        'default': [
            (r'\n', Whitespace, '#pop'),
            (r"'", String.Single, ('#pop', 'quote')),
            (r'"', String.Double, 'string'),
            (r'=', Punctuation),
            (r':', Punctuation, 'label'),
            (_ws, Whitespace),
            (r';.*', Comment.Single),
            (rf'(\$[-+])?0x-?[\da-fA-F]+{_break}', Number.Hex),
            (rf'(\$[-+]|\+)?-?\d+{_break}', Number.Integer),
            (r'-?(\d+\.\d*|\.\d+)([eE][-+]?\d+)?[fFdD]?'
             rf'[\x00-\x08\x0b\x0c\x0e-\x1f]*{_break}', Number.Float),
            (rf'\${_name}', Name.Variable),

            # Directives
            (rf'\.annotation{_break}', Keyword.Reserved, 'annotation'),
            (r'(\.attribute|\.bytecode|\.debug|\.deprecated|\.enclosing|'
             r'\.interface|\.line|\.signature|\.source|\.stack|\.var|abstract|'
             r'annotation|bridge|class|default|enum|field|final|fpstrict|'
             r'interface|native|private|protected|public|signature|static|'
             rf'synchronized|synthetic|transient|varargs|volatile){_break}',
             Keyword.Reserved),
            (rf'\.catch{_break}', Keyword.Reserved, 'caught-exception'),
            (r'(\.class|\.implements|\.inner|\.super|inner|invisible|'
             rf'invisibleparam|outer|visible|visibleparam){_break}',
             Keyword.Reserved, 'class/convert-dots'),
            (rf'\.field{_break}', Keyword.Reserved,
             ('descriptor/convert-dots', 'field')),
            (rf'(\.end|\.limit|use){_break}', Keyword.Reserved,
             'no-verification'),
            (rf'\.method{_break}', Keyword.Reserved, 'method'),
            (rf'\.set{_break}', Keyword.Reserved, 'var'),
            (rf'\.throws{_break}', Keyword.Reserved, 'exception'),
            (rf'(from|offset|to|using){_break}', Keyword.Reserved, 'label'),
            (rf'is{_break}', Keyword.Reserved,
             ('descriptor/convert-dots', 'var')),
            (rf'(locals|stack){_break}', Keyword.Reserved, 'verification'),
            (rf'method{_break}', Keyword.Reserved, 'enclosing-method'),

            # Instructions
            (words((
                'aaload', 'aastore', 'aconst_null', 'aload', 'aload_0', 'aload_1', 'aload_2',
                'aload_3', 'aload_w', 'areturn', 'arraylength', 'astore', 'astore_0', 'astore_1',
                'astore_2', 'astore_3', 'astore_w', 'athrow', 'baload', 'bastore', 'bipush',
                'breakpoint', 'caload', 'castore', 'd2f', 'd2i', 'd2l', 'dadd', 'daload', 'dastore',
                'dcmpg', 'dcmpl', 'dconst_0', 'dconst_1', 'ddiv', 'dload', 'dload_0', 'dload_1',
                'dload_2', 'dload_3', 'dload_w', 'dmul', 'dneg', 'drem', 'dreturn', 'dstore', 'dstore_0',
                'dstore_1', 'dstore_2', 'dstore_3', 'dstore_w', 'dsub', 'dup', 'dup2', 'dup2_x1',
                'dup2_x2', 'dup_x1', 'dup_x2', 'f2d', 'f2i', 'f2l', 'fadd', 'faload', 'fastore', 'fcmpg',
                'fcmpl', 'fconst_0', 'fconst_1', 'fconst_2', 'fdiv', 'fload', 'fload_0', 'fload_1',
                'fload_2', 'fload_3', 'fload_w', 'fmul', 'fneg', 'frem', 'freturn', 'fstore', 'fstore_0',
                'fstore_1', 'fstore_2', 'fstore_3', 'fstore_w', 'fsub', 'i2b', 'i2c', 'i2d', 'i2f', 'i2l',
                'i2s', 'iadd', 'iaload', 'iand', 'iastore', 'iconst_0', 'iconst_1', 'iconst_2',
                'iconst_3', 'iconst_4', 'iconst_5', 'iconst_m1', 'idiv', 'iinc', 'iinc_w', 'iload',
                'iload_0', 'iload_1', 'iload_2', 'iload_3', 'iload_w', 'imul', 'ineg', 'int2byte',
                'int2char', 'int2short', 'ior', 'irem', 'ireturn', 'ishl', 'ishr', 'istore', 'istore_0',
                'istore_1', 'istore_2', 'istore_3', 'istore_w', 'isub', 'iushr', 'ixor', 'l2d', 'l2f',
                'l2i', 'ladd', 'laload', 'land', 'lastore', 'lcmp', 'lconst_0', 'lconst_1', 'ldc2_w',
                'ldiv', 'lload', 'lload_0', 'lload_1', 'lload_2', 'lload_3', 'lload_w', 'lmul', 'lneg',
                'lookupswitch', 'lor', 'lrem', 'lreturn', 'lshl', 'lshr', 'lstore', 'lstore_0',
                'lstore_1', 'lstore_2', 'lstore_3', 'lstore_w', 'lsub', 'lushr', 'lxor',
                'monitorenter', 'monitorexit', 'nop', 'pop', 'pop2', 'ret', 'ret_w', 'return', 'saload',
                'sastore', 'sipush', 'swap'), suffix=_break), Keyword.Reserved),
            (rf'(anewarray|checkcast|instanceof|ldc|ldc_w|new){_break}',
             Keyword.Reserved, 'class/no-dots'),
            (r'invoke(dynamic|interface|nonvirtual|special|'
             rf'static|virtual){_break}', Keyword.Reserved,
             'invocation'),
            (rf'(getfield|putfield){_break}', Keyword.Reserved,
             ('descriptor/no-dots', 'field')),
            (rf'(getstatic|putstatic){_break}', Keyword.Reserved,
             ('descriptor/no-dots', 'static')),
            (words((
                'goto', 'goto_w', 'if_acmpeq', 'if_acmpne', 'if_icmpeq',
                'if_icmpge', 'if_icmpgt', 'if_icmple', 'if_icmplt', 'if_icmpne',
                'ifeq', 'ifge', 'ifgt', 'ifle', 'iflt', 'ifne', 'ifnonnull',
                'ifnull', 'jsr', 'jsr_w'), suffix=_break),
             Keyword.Reserved, 'label'),
            (rf'(multianewarray|newarray){_break}', Keyword.Reserved,
             'descriptor/convert-dots'),
            (rf'tableswitch{_break}', Keyword.Reserved, 'table')
        ],
        'quote': [
            (r"'", String.Single, '#pop'),
            (r'\\u[\da-fA-F]{4}', String.Escape),
            (r"[^'\\]+", String.Single)
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (r'\\([nrtfb"\'\\]|u[\da-fA-F]{4}|[0-3]?[0-7]{1,2})',
             String.Escape),
            (r'[^"\\]+', String.Double)
        ],
        'root': [
            (r'\n+', Whitespace),
            (r"'", String.Single, 'quote'),
            include('default'),
            (rf'({_name})([ \t\r]*)(:)',
             bygroups(Name.Label, Whitespace, Punctuation)),
            (_name, String.Other)
        ],
        'annotation': [
            (r'\n', Whitespace, ('#pop', 'annotation-body')),
            (rf'default{_break}', Keyword.Reserved,
             ('#pop', 'annotation-default')),
            include('default')
        ],
        'annotation-body': [
            (r'\n+', Whitespace),
            (rf'\.end{_break}', Keyword.Reserved, '#pop'),
            include('default'),
            (_name, String.Other, ('annotation-items', 'descriptor/no-dots'))
        ],
        'annotation-default': [
            (r'\n+', Whitespace),
            (rf'\.end{_break}', Keyword.Reserved, '#pop'),
            include('default'),
            default(('annotation-items', 'descriptor/no-dots'))
        ],
        'annotation-items': [
            (r"'", String.Single, 'quote'),
            include('default'),
            (_name, String.Other)
        ],
        'caught-exception': [
            (rf'all{_break}', Keyword, '#pop'),
            include('exception')
        ],
        'class/convert-dots': [
            include('default'),
            (rf'(L)((?:{_unqualified_name}[/.])*)({_name})(;)',
             bygroups(Keyword.Type, Name.Namespace, Name.Class, Punctuation),
             '#pop'),
            (rf'((?:{_unqualified_name}[/.])*)({_name})',
             bygroups(Name.Namespace, Name.Class), '#pop')
        ],
        'class/no-dots': [
            include('default'),
            (r'\[+', Punctuation, ('#pop', 'descriptor/no-dots')),
            (rf'(L)((?:{_unqualified_name}/)*)({_name})(;)',
             bygroups(Keyword.Type, Name.Namespace, Name.Class, Punctuation),
             '#pop'),
            (rf'((?:{_unqualified_name}/)*)({_name})',
             bygroups(Name.Namespace, Name.Class), '#pop')
        ],
        'descriptor/convert-dots': [
            include('default'),
            (r'\[+', Punctuation),
            (rf'(L)((?:{_unqualified_name}[/.])*)({_name}?)(;)',
             bygroups(Keyword.Type, Name.Namespace, Name.Class, Punctuation),
             '#pop'),
            (rf'[^{_separator}\[)L]+', Keyword.Type, '#pop'),
            default('#pop')
        ],
        'descriptor/no-dots': [
            include('default'),
            (r'\[+', Punctuation),
            (rf'(L)((?:{_unqualified_name}/)*)({_name})(;)',
             bygroups(Keyword.Type, Name.Namespace, Name.Class, Punctuation),
             '#pop'),
            (rf'[^{_separator}\[)L]+', Keyword.Type, '#pop'),
            default('#pop')
        ],
        'descriptors/convert-dots': [
            (r'\)', Punctuation, '#pop'),
            default('descriptor/convert-dots')
        ],
        'enclosing-method': [
            (_ws, Whitespace),
            (rf'(?=[^{_separator}]*\()', Text, ('#pop', 'invocation')),
            default(('#pop', 'class/convert-dots'))
        ],
        'exception': [
            include('default'),
            (rf'((?:{_unqualified_name}[/.])*)({_name})',
             bygroups(Name.Namespace, Name.Exception), '#pop')
        ],
        'field': [
            (rf'static{_break}', Keyword.Reserved, ('#pop', 'static')),
            include('default'),
            (rf'((?:{_unqualified_name}[/.](?=[^{_separator}]*[/.]))*)({_unqualified_name}[/.])?({_name})',
             bygroups(Name.Namespace, Name.Class, Name.Variable.Instance),
             '#pop')
        ],
        'invocation': [
            include('default'),
            (rf'((?:{_unqualified_name}[/.](?=[^{_separator}(]*[/.]))*)({_unqualified_name}[/.])?({_name})(\()',
             bygroups(Name.Namespace, Name.Class, Name.Function, Punctuation),
             ('#pop', 'descriptor/convert-dots', 'descriptors/convert-dots',
              'descriptor/convert-dots'))
        ],
        'label': [
            include('default'),
            (_name, Name.Label, '#pop')
        ],
        'method': [
            include('default'),
            (rf'({_name})(\()', bygroups(Name.Function, Punctuation),
             ('#pop', 'descriptor/convert-dots', 'descriptors/convert-dots',
              'descriptor/convert-dots'))
        ],
        'no-verification': [
            (rf'(locals|method|stack){_break}', Keyword.Reserved, '#pop'),
            include('default')
        ],
        'static': [
            include('default'),
            (rf'((?:{_unqualified_name}[/.](?=[^{_separator}]*[/.]))*)({_unqualified_name}[/.])?({_name})',
             bygroups(Name.Namespace, Name.Class, Name.Variable.Class), '#pop')
        ],
        'table': [
            (r'\n+', Whitespace),
            (rf'default{_break}', Keyword.Reserved, '#pop'),
            include('default'),
            (_name, Name.Label)
        ],
        'var': [
            include('default'),
            (_name, Name.Variable, '#pop')
        ],
        'verification': [
            include('default'),
            (rf'(Double|Float|Integer|Long|Null|Top|UninitializedThis){_break}', Keyword, '#pop'),
            (rf'Object{_break}', Keyword, ('#pop', 'class/no-dots')),
            (rf'Uninitialized{_break}', Keyword, ('#pop', 'label'))
        ]
    }

    def analyse_text(text):
        score = 0
        if re.search(r'^\s*\.class\s', text, re.MULTILINE):
            score += 0.5
            if re.search(r'^\s*[a-z]+_[a-z]+\b', text, re.MULTILINE):
                score += 0.3
        if re.search(r'^\s*\.(attribute|bytecode|debug|deprecated|enclosing|'
                     r'inner|interface|limit|set|signature|stack)\b', text,
                     re.MULTILINE):
            score += 0.6
        return min(score, 1.0)


class SarlLexer(RegexLexer):
    """
    For SARL source code.
    """

    name = 'SARL'
    url = 'http://www.sarl.io'
    aliases = ['sarl']
    filenames = ['*.sarl']
    mimetypes = ['text/x-sarl']
    version_added = '2.4'

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            # method names
            (r'^(\s*(?:[a-zA-Z_][\w.\[\]]*\s+)+?)'  # return arguments
             r'([a-zA-Z_$][\w$]*)'                      # method name
             r'(\s*)(\()',                             # signature start
             bygroups(using(this), Name.Function, Whitespace, Operator)),
            (r'[^\S\n]+', Whitespace),
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'@[a-zA-Z_][\w.]*', Name.Decorator),
            (r'(as|break|case|catch|default|do|else|extends|extension|finally|'
             r'fires|for|if|implements|instanceof|new|on|requires|return|super|'
             r'switch|throw|throws|try|typeof|uses|while|with)\b',
             Keyword),
            (r'(abstract|def|dispatch|final|native|override|private|protected|'
             r'public|static|strictfp|synchronized|transient|val|var|volatile)\b',
             Keyword.Declaration),
            (r'(boolean|byte|char|double|float|int|long|short|void)\b',
             Keyword.Type),
            (r'(package)(\s+)', bygroups(Keyword.Namespace, Whitespace)),
            (r'(false|it|null|occurrence|this|true|void)\b', Keyword.Constant),
            (r'(agent|annotation|artifact|behavior|capacity|class|enum|event|'
             r'interface|skill|space)(\s+)', bygroups(Keyword.Declaration, Whitespace),
             'class'),
            (r'(import)(\s+)', bygroups(Keyword.Namespace, Whitespace), 'import'),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r'[a-zA-Z_]\w*:', Name.Label),
            (r'[a-zA-Z_$]\w*', Name),
            (r'[~^*!%&\[\](){}<>\|+=:;,./?-]', Operator),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+L?', Number.Integer),
            (r'\n', Whitespace)
        ],
        'class': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'[\w.]+\*?', Name.Namespace, '#pop')
        ],
    }

# === NexusCore/openenv\Lib\site-packages\httplib2\__init__.py ===
# -*- coding: utf-8 -*-
"""Small, fast HTTP client library for Python."""

__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = [
    "Thomas Broyer (t.broyer@ltgt.net)",
    "James Antill",
    "Xavier Verges Farrero",
    "Jonathan Feinberg",
    "Blair Zajac",
    "Sam Ruby",
    "Louis Nyffenegger",
    "Mark Pilgrim",
    "Alex Yu",
    "Lai Han",
]
__license__ = "MIT"
__version__ = "0.22.0"

import base64
import calendar
import copy
import email
import email.feedparser
from email import header
import email.message
import email.utils
import errno
from gettext import gettext as _
import gzip
from hashlib import md5 as _md5
from hashlib import sha1 as _sha
import hmac
import http.client
import io
import os
import random
import re
import socket
import ssl
import sys
import time
import urllib.parse
import zlib

try:
    import socks
except ImportError:
    # TODO: remove this fallback and copypasted socksipy module upon py2/3 merge,
    # idea is to have soft-dependency on any compatible module called socks
    from . import socks
from . import auth
from .error import *
from .iri2uri import iri2uri


def has_timeout(timeout):
    if hasattr(socket, "_GLOBAL_DEFAULT_TIMEOUT"):
        return timeout is not None and timeout is not socket._GLOBAL_DEFAULT_TIMEOUT
    return timeout is not None


__all__ = [
    "debuglevel",
    "FailedToDecompressContent",
    "Http",
    "HttpLib2Error",
    "ProxyInfo",
    "RedirectLimit",
    "RedirectMissingLocation",
    "Response",
    "RETRIES",
    "UnimplementedDigestAuthOptionError",
    "UnimplementedHmacDigestAuthOptionError",
]

# The httplib debug level, set to a non-zero value to get debug output
debuglevel = 0

# A request will be tried 'RETRIES' times if it fails at the socket/connection level.
RETRIES = 2


# Open Items:
# -----------

# Are we removing the cached content too soon on PUT (only delete on 200 Maybe?)

# Pluggable cache storage (supports storing the cache in
#   flat files by default. We need a plug-in architecture
#   that can support Berkeley DB and Squid)

# == Known Issues ==
# Does not handle a resource that uses conneg and Last-Modified but no ETag as a cache validator.
# Does not handle Cache-Control: max-stale
# Does not use Age: headers when calculating cache freshness.

# The number of redirections to follow before giving up.
# Note that only GET redirects are automatically followed.
# Will also honor 301 requests by saving that info and never
# requesting that URI again.
DEFAULT_MAX_REDIRECTS = 5

# Which headers are hop-by-hop headers by default
HOP_BY_HOP = [
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
]

# https://tools.ietf.org/html/rfc7231#section-8.1.3
SAFE_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")

# To change, assign to `Http().redirect_codes`
REDIRECT_CODES = frozenset((300, 301, 302, 303, 307, 308))


from httplib2 import certs

CA_CERTS = certs.where()

# PROTOCOL_TLS is python 3.5.3+. PROTOCOL_SSLv23 is deprecated.
# Both PROTOCOL_TLS and PROTOCOL_SSLv23 are equivalent and means:
# > Selects the highest protocol version that both the client and server support.
# > Despite the name, this option can select “TLS” protocols as well as “SSL”.
# source: https://docs.python.org/3.5/library/ssl.html#ssl.PROTOCOL_SSLv23

# PROTOCOL_TLS_CLIENT is python 3.10.0+. PROTOCOL_TLS is deprecated.
# > Auto-negotiate the highest protocol version that both the client and server support, and configure the context client-side connections.
# > The protocol enables CERT_REQUIRED and check_hostname by default.
# source: https://docs.python.org/3.10/library/ssl.html#ssl.PROTOCOL_TLS

DEFAULT_TLS_VERSION = getattr(ssl, "PROTOCOL_TLS_CLIENT", None) or getattr(ssl, "PROTOCOL_TLS", None) or getattr(ssl, "PROTOCOL_SSLv23")


def _build_ssl_context(
    disable_ssl_certificate_validation,
    ca_certs,
    cert_file=None,
    key_file=None,
    maximum_version=None,
    minimum_version=None,
    key_password=None,
):
    if not hasattr(ssl, "SSLContext"):
        raise RuntimeError("httplib2 requires Python 3.2+ for ssl.SSLContext")

    context = ssl.SSLContext(DEFAULT_TLS_VERSION)
    # check_hostname and verify_mode should be set in opposite order during disable
    # https://bugs.python.org/issue31431
    if disable_ssl_certificate_validation and hasattr(context, "check_hostname"):
        context.check_hostname = not disable_ssl_certificate_validation
    context.verify_mode = ssl.CERT_NONE if disable_ssl_certificate_validation else ssl.CERT_REQUIRED

    # SSLContext.maximum_version and SSLContext.minimum_version are python 3.7+.
    # source: https://docs.python.org/3/library/ssl.html#ssl.SSLContext.maximum_version
    if maximum_version is not None:
        if hasattr(context, "maximum_version"):
            if isinstance(maximum_version, str):
                maximum_version = getattr(ssl.TLSVersion, maximum_version)
            context.maximum_version = maximum_version
        else:
            raise RuntimeError("setting tls_maximum_version requires Python 3.7 and OpenSSL 1.1 or newer")
    if minimum_version is not None:
        if hasattr(context, "minimum_version"):
            if isinstance(minimum_version, str):
                minimum_version = getattr(ssl.TLSVersion, minimum_version)
            context.minimum_version = minimum_version
        else:
            raise RuntimeError("setting tls_minimum_version requires Python 3.7 and OpenSSL 1.1 or newer")
    # check_hostname requires python 3.4+
    # we will perform the equivalent in HTTPSConnectionWithTimeout.connect() by calling ssl.match_hostname
    # if check_hostname is not supported.
    if hasattr(context, "check_hostname"):
        context.check_hostname = not disable_ssl_certificate_validation

    context.load_verify_locations(ca_certs)

    if cert_file:
        context.load_cert_chain(cert_file, key_file, key_password)

    return context


def _get_end2end_headers(response):
    hopbyhop = list(HOP_BY_HOP)
    hopbyhop.extend([x.strip() for x in response.get("connection", "").split(",")])
    return [header for header in list(response.keys()) if header not in hopbyhop]


_missing = object()


def _errno_from_exception(e):
    # TODO python 3.11+ cheap try: return e.errno except AttributeError: pass
    errno = getattr(e, "errno", _missing)
    if errno is not _missing:
        return errno

    # socket.error and common wrap in .args
    args = getattr(e, "args", None)
    if args:
        return _errno_from_exception(args[0])

    # pysocks.ProxyError wraps in .socket_err
    # https://github.com/httplib2/httplib2/pull/202
    socket_err = getattr(e, "socket_err", None)
    if socket_err:
        return _errno_from_exception(socket_err)

    return None


URI = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")


def parse_uri(uri):
    """Parses a URI using the regex given in Appendix B of RFC 3986.

        (scheme, authority, path, query, fragment) = parse_uri(uri)
    """
    groups = URI.match(uri).groups()
    return (groups[1], groups[3], groups[4], groups[6], groups[8])


def urlnorm(uri):
    (scheme, authority, path, query, fragment) = parse_uri(uri)
    if not scheme or not authority:
        raise RelativeURIError("Only absolute URIs are allowed. uri = %s" % uri)
    authority = authority.lower()
    scheme = scheme.lower()
    if not path:
        path = "/"
    # Could do syntax based normalization of the URI before
    # computing the digest. See Section 6.2.2 of Std 66.
    request_uri = query and "?".join([path, query]) or path
    scheme = scheme.lower()
    defrag_uri = scheme + "://" + authority + request_uri
    return scheme, authority, request_uri, defrag_uri


# Cache filename construction (original borrowed from Venus http://intertwingly.net/code/venus/)
re_url_scheme = re.compile(r"^\w+://")
re_unsafe = re.compile(r"[^\w\-_.()=!]+", re.ASCII)


def safename(filename):
    """Return a filename suitable for the cache.
    Strips dangerous and common characters to create a filename we
    can use to store the cache in.
    """
    if isinstance(filename, bytes):
        filename_bytes = filename
        filename = filename.decode("utf-8")
    else:
        filename_bytes = filename.encode("utf-8")
    filemd5 = _md5(filename_bytes).hexdigest()
    filename = re_url_scheme.sub("", filename)
    filename = re_unsafe.sub("", filename)

    # limit length of filename (vital for Windows)
    # https://github.com/httplib2/httplib2/pull/74
    # C:\Users\    <username>    \AppData\Local\Temp\  <safe_filename>  ,   <md5>
    #   9 chars + max 104 chars  +     20 chars      +       x       +  1  +  32  = max 259 chars
    # Thus max safe filename x = 93 chars. Let it be 90 to make a round sum:
    filename = filename[:90]

    return ",".join((filename, filemd5))


NORMALIZE_SPACE = re.compile(r"(?:\r\n)?[ \t]+")


def _normalize_headers(headers):
    return dict(
        [
            (_convert_byte_str(key).lower(), NORMALIZE_SPACE.sub(_convert_byte_str(value), " ").strip(),)
            for (key, value) in headers.items()
        ]
    )


def _convert_byte_str(s):
    if not isinstance(s, str):
        return str(s, "utf-8")
    return s


def _parse_cache_control(headers):
    retval = {}
    if "cache-control" in headers:
        parts = headers["cache-control"].split(",")
        parts_with_args = [
            tuple([x.strip().lower() for x in part.split("=", 1)]) for part in parts if -1 != part.find("=")
        ]
        parts_wo_args = [(name.strip().lower(), 1) for name in parts if -1 == name.find("=")]
        retval = dict(parts_with_args + parts_wo_args)
    return retval


# Whether to use a strict mode to parse WWW-Authenticate headers
# Might lead to bad results in case of ill-formed header value,
# so disabled by default, falling back to relaxed parsing.
# Set to true to turn on, useful for testing servers.
USE_WWW_AUTH_STRICT_PARSING = 0


def _entry_disposition(response_headers, request_headers):
    """Determine freshness from the Date, Expires and Cache-Control headers.

    We don't handle the following:

    1. Cache-Control: max-stale
    2. Age: headers are not used in the calculations.

    Not that this algorithm is simpler than you might think
    because we are operating as a private (non-shared) cache.
    This lets us ignore 's-maxage'. We can also ignore
    'proxy-invalidate' since we aren't a proxy.
    We will never return a stale document as
    fresh as a design decision, and thus the non-implementation
    of 'max-stale'. This also lets us safely ignore 'must-revalidate'
    since we operate as if every server has sent 'must-revalidate'.
    Since we are private we get to ignore both 'public' and
    'private' parameters. We also ignore 'no-transform' since
    we don't do any transformations.
    The 'no-store' parameter is handled at a higher level.
    So the only Cache-Control parameters we look at are:

    no-cache
    only-if-cached
    max-age
    min-fresh
    """

    retval = "STALE"
    cc = _parse_cache_control(request_headers)
    cc_response = _parse_cache_control(response_headers)

    if "pragma" in request_headers and request_headers["pragma"].lower().find("no-cache") != -1:
        retval = "TRANSPARENT"
        if "cache-control" not in request_headers:
            request_headers["cache-control"] = "no-cache"
    elif "no-cache" in cc:
        retval = "TRANSPARENT"
    elif "no-cache" in cc_response:
        retval = "STALE"
    elif "only-if-cached" in cc:
        retval = "FRESH"
    elif "date" in response_headers:
        date = calendar.timegm(email.utils.parsedate_tz(response_headers["date"]))
        now = time.time()
        current_age = max(0, now - date)
        if "max-age" in cc_response:
            try:
                freshness_lifetime = int(cc_response["max-age"])
            except ValueError:
                freshness_lifetime = 0
        elif "expires" in response_headers:
            expires = email.utils.parsedate_tz(response_headers["expires"])
            if None == expires:
                freshness_lifetime = 0
            else:
                freshness_lifetime = max(0, calendar.timegm(expires) - date)
        else:
            freshness_lifetime = 0
        if "max-age" in cc:
            try:
                freshness_lifetime = int(cc["max-age"])
            except ValueError:
                freshness_lifetime = 0
        if "min-fresh" in cc:
            try:
                min_fresh = int(cc["min-fresh"])
            except ValueError:
                min_fresh = 0
            current_age += min_fresh
        if freshness_lifetime > current_age:
            retval = "FRESH"
    return retval


def _decompressContent(response, new_content):
    content = new_content
    try:
        encoding = response.get("content-encoding", None)
        if encoding in ["gzip", "deflate"]:
            if encoding == "gzip":
                content = gzip.GzipFile(fileobj=io.BytesIO(new_content)).read()
            if encoding == "deflate":
                try:
                    content = zlib.decompress(content, zlib.MAX_WBITS)
                except (IOError, zlib.error):
                    content = zlib.decompress(content, -zlib.MAX_WBITS)
            response["content-length"] = str(len(content))
            # Record the historical presence of the encoding in a way the won't interfere.
            response["-content-encoding"] = response["content-encoding"]
            del response["content-encoding"]
    except (IOError, zlib.error):
        content = ""
        raise FailedToDecompressContent(
            _("Content purported to be compressed with %s but failed to decompress.") % response.get("content-encoding"),
            response,
            content,
        )
    return content


def _bind_write_headers(msg):
    def _write_headers(self):
        # Self refers to the Generator object.
        for h, v in msg.items():
            print("%s:" % h, end=" ", file=self._fp)
            if isinstance(v, header.Header):
                print(v.encode(maxlinelen=self._maxheaderlen), file=self._fp)
            else:
                # email.Header got lots of smarts, so use it.
                headers = header.Header(v, maxlinelen=self._maxheaderlen, charset="utf-8", header_name=h)
                print(headers.encode(), file=self._fp)
        # A blank line always separates headers from body.
        print(file=self._fp)

    return _write_headers


def _updateCache(request_headers, response_headers, content, cache, cachekey):
    if cachekey:
        cc = _parse_cache_control(request_headers)
        cc_response = _parse_cache_control(response_headers)
        if "no-store" in cc or "no-store" in cc_response:
            cache.delete(cachekey)
        else:
            info = email.message.Message()
            for key, value in response_headers.items():
                if key not in ["status", "content-encoding", "transfer-encoding"]:
                    info[key] = value

            # Add annotations to the cache to indicate what headers
            # are variant for this request.
            vary = response_headers.get("vary", None)
            if vary:
                vary_headers = vary.lower().replace(" ", "").split(",")
                for header in vary_headers:
                    key = "-varied-%s" % header
                    try:
                        info[key] = request_headers[header]
                    except KeyError:
                        pass

            status = response_headers.status
            if status == 304:
                status = 200

            status_header = "status: %d\r\n" % status

            try:
                header_str = info.as_string()
            except UnicodeEncodeError:
                setattr(info, "_write_headers", _bind_write_headers(info))
                header_str = info.as_string()

            header_str = re.sub("\r(?!\n)|(?<!\r)\n", "\r\n", header_str)
            text = b"".join([status_header.encode("utf-8"), header_str.encode("utf-8"), content])

            cache.set(cachekey, text)


def _cnonce():
    dig = _md5(
        ("%s:%s" % (time.ctime(), ["0123456789"[random.randrange(0, 9)] for i in range(20)])).encode("utf-8")
    ).hexdigest()
    return dig[:16]


def _wsse_username_token(cnonce, iso_now, password):
    return (
        base64.b64encode(_sha(("%s%s%s" % (cnonce, iso_now, password)).encode("utf-8")).digest()).strip().decode("utf-8")
    )


# For credentials we need two things, first
# a pool of credential to try (not necesarily tied to BAsic, Digest, etc.)
# Then we also need a list of URIs that have already demanded authentication
# That list is tricky since sub-URIs can take the same auth, or the
# auth scheme may change as you descend the tree.
# So we also need each Auth instance to be able to tell us
# how close to the 'top' it is.


class Authentication(object):
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        (scheme, authority, path, query, fragment) = parse_uri(request_uri)
        self.path = path
        self.host = host
        self.credentials = credentials
        self.http = http

    def depth(self, request_uri):
        (scheme, authority, path, query, fragment) = parse_uri(request_uri)
        return request_uri[len(self.path) :].count("/")

    def inscope(self, host, request_uri):
        # XXX Should we normalize the request_uri?
        (scheme, authority, path, query, fragment) = parse_uri(request_uri)
        return (host == self.host) and path.startswith(self.path)

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header. Over-rise this in sub-classes."""
        pass

    def response(self, response, content):
        """Gives us a chance to update with new nonces
        or such returned from the last authorized response.
        Over-rise this in sub-classes if necessary.

        Return TRUE is the request is to be retried, for
        example Digest may return stale=true.
        """
        return False

    def __eq__(self, auth):
        return False

    def __ne__(self, auth):
        return True

    def __lt__(self, auth):
        return True

    def __gt__(self, auth):
        return False

    def __le__(self, auth):
        return True

    def __ge__(self, auth):
        return False

    def __bool__(self):
        return True


class BasicAuthentication(Authentication):
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header."""
        headers["authorization"] = "Basic " + base64.b64encode(
            ("%s:%s" % self.credentials).encode("utf-8")
        ).strip().decode("utf-8")


class DigestAuthentication(Authentication):
    """Only do qop='auth' and MD5, since that
    is all Apache currently implements"""

    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)
        self.challenge = auth._parse_www_authenticate(response, "www-authenticate")["digest"]
        qop = self.challenge.get("qop", "auth")
        self.challenge["qop"] = ("auth" in [x.strip() for x in qop.split()]) and "auth" or None
        if self.challenge["qop"] is None:
            raise UnimplementedDigestAuthOptionError(_("Unsupported value for qop: %s." % qop))
        self.challenge["algorithm"] = self.challenge.get("algorithm", "MD5").upper()
        if self.challenge["algorithm"] != "MD5":
            raise UnimplementedDigestAuthOptionError(
                _("Unsupported value for algorithm: %s." % self.challenge["algorithm"])
            )
        self.A1 = "".join([self.credentials[0], ":", self.challenge["realm"], ":", self.credentials[1],])
        self.challenge["nc"] = 1

    def request(self, method, request_uri, headers, content, cnonce=None):
        """Modify the request headers"""
        H = lambda x: _md5(x.encode("utf-8")).hexdigest()
        KD = lambda s, d: H("%s:%s" % (s, d))
        A2 = "".join([method, ":", request_uri])
        self.challenge["cnonce"] = cnonce or _cnonce()
        request_digest = '"%s"' % KD(
            H(self.A1),
            "%s:%s:%s:%s:%s"
            % (
                self.challenge["nonce"],
                "%08x" % self.challenge["nc"],
                self.challenge["cnonce"],
                self.challenge["qop"],
                H(A2),
            ),
        )
        headers["authorization"] = (
            'Digest username="%s", realm="%s", nonce="%s", '
            'uri="%s", algorithm=%s, response=%s, qop=%s, '
            'nc=%08x, cnonce="%s"'
        ) % (
            self.credentials[0],
            self.challenge["realm"],
            self.challenge["nonce"],
            request_uri,
            self.challenge["algorithm"],
            request_digest,
            self.challenge["qop"],
            self.challenge["nc"],
            self.challenge["cnonce"],
        )
        if self.challenge.get("opaque"):
            headers["authorization"] += ', opaque="%s"' % self.challenge["opaque"]
        self.challenge["nc"] += 1

    def response(self, response, content):
        if "authentication-info" not in response:
            challenge = auth._parse_www_authenticate(response, "www-authenticate").get("digest", {})
            if "true" == challenge.get("stale"):
                self.challenge["nonce"] = challenge["nonce"]
                self.challenge["nc"] = 1
                return True
        else:
            updated_challenge = auth._parse_authentication_info(response, "authentication-info")

            if "nextnonce" in updated_challenge:
                self.challenge["nonce"] = updated_challenge["nextnonce"]
                self.challenge["nc"] = 1
        return False


class HmacDigestAuthentication(Authentication):
    """Adapted from Robert Sayre's code and DigestAuthentication above."""

    __author__ = "Thomas Broyer (t.broyer@ltgt.net)"

    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)
        challenge = auth._parse_www_authenticate(response, "www-authenticate")
        self.challenge = challenge["hmacdigest"]
        # TODO: self.challenge['domain']
        self.challenge["reason"] = self.challenge.get("reason", "unauthorized")
        if self.challenge["reason"] not in ["unauthorized", "integrity"]:
            self.challenge["reason"] = "unauthorized"
        self.challenge["salt"] = self.challenge.get("salt", "")
        if not self.challenge.get("snonce"):
            raise UnimplementedHmacDigestAuthOptionError(
                _("The challenge doesn't contain a server nonce, or this one is empty.")
            )
        self.challenge["algorithm"] = self.challenge.get("algorithm", "HMAC-SHA-1")
        if self.challenge["algorithm"] not in ["HMAC-SHA-1", "HMAC-MD5"]:
            raise UnimplementedHmacDigestAuthOptionError(
                _("Unsupported value for algorithm: %s." % self.challenge["algorithm"])
            )
        self.challenge["pw-algorithm"] = self.challenge.get("pw-algorithm", "SHA-1")
        if self.challenge["pw-algorithm"] not in ["SHA-1", "MD5"]:
            raise UnimplementedHmacDigestAuthOptionError(
                _("Unsupported value for pw-algorithm: %s." % self.challenge["pw-algorithm"])
            )
        if self.challenge["algorithm"] == "HMAC-MD5":
            self.hashmod = _md5
        else:
            self.hashmod = _sha
        if self.challenge["pw-algorithm"] == "MD5":
            self.pwhashmod = _md5
        else:
            self.pwhashmod = _sha
        self.key = "".join(
            [
                self.credentials[0],
                ":",
                self.pwhashmod.new("".join([self.credentials[1], self.challenge["salt"]])).hexdigest().lower(),
                ":",
                self.challenge["realm"],
            ]
        )
        self.key = self.pwhashmod.new(self.key).hexdigest().lower()

    def request(self, method, request_uri, headers, content):
        """Modify the request headers"""
        keys = _get_end2end_headers(headers)
        keylist = "".join(["%s " % k for k in keys])
        headers_val = "".join([headers[k] for k in keys])
        created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cnonce = _cnonce()
        request_digest = "%s:%s:%s:%s:%s" % (method, request_uri, cnonce, self.challenge["snonce"], headers_val,)
        request_digest = hmac.new(self.key, request_digest, self.hashmod).hexdigest().lower()
        headers["authorization"] = (
            'HMACDigest username="%s", realm="%s", snonce="%s",'
            ' cnonce="%s", uri="%s", created="%s", '
            'response="%s", headers="%s"'
        ) % (
            self.credentials[0],
            self.challenge["realm"],
            self.challenge["snonce"],
            cnonce,
            request_uri,
            created,
            request_digest,
            keylist,
        )

    def response(self, response, content):
        challenge = auth._parse_www_authenticate(response, "www-authenticate").get("hmacdigest", {})
        if challenge.get("reason") in ["integrity", "stale"]:
            return True
        return False


class WsseAuthentication(Authentication):
    """This is thinly tested and should not be relied upon.
    At this time there isn't any third party server to test against.
    Blogger and TypePad implemented this algorithm at one point
    but Blogger has since switched to Basic over HTTPS and
    TypePad has implemented it wrong, by never issuing a 401
    challenge but instead requiring your client to telepathically know that
    their endpoint is expecting WSSE profile="UsernameToken"."""

    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header."""
        headers["authorization"] = 'WSSE profile="UsernameToken"'
        iso_now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cnonce = _cnonce()
        password_digest = _wsse_username_token(cnonce, iso_now, self.credentials[1])
        headers["X-WSSE"] = ('UsernameToken Username="%s", PasswordDigest="%s", ' 'Nonce="%s", Created="%s"') % (
            self.credentials[0],
            password_digest,
            cnonce,
            iso_now,
        )


class GoogleLoginAuthentication(Authentication):
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        from urllib.parse import urlencode

        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)
        challenge = auth._parse_www_authenticate(response, "www-authenticate")
        service = challenge["googlelogin"].get("service", "xapi")
        # Bloggger actually returns the service in the challenge
        # For the rest we guess based on the URI
        if service == "xapi" and request_uri.find("calendar") > 0:
            service = "cl"
        # No point in guessing Base or Spreadsheet
        # elif request_uri.find("spreadsheets") > 0:
        #    service = "wise"

        auth = dict(Email=credentials[0], Passwd=credentials[1], service=service, source=headers["user-agent"],)
        resp, content = self.http.request(
            "https://www.google.com/accounts/ClientLogin",
            method="POST",
            body=urlencode(auth),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        lines = content.split("\n")
        d = dict([tuple(line.split("=", 1)) for line in lines if line])
        if resp.status == 403:
            self.Auth = ""
        else:
            self.Auth = d["Auth"]

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header."""
        headers["authorization"] = "GoogleLogin Auth=" + self.Auth


AUTH_SCHEME_CLASSES = {
    "basic": BasicAuthentication,
    "wsse": WsseAuthentication,
    "digest": DigestAuthentication,
    "hmacdigest": HmacDigestAuthentication,
    "googlelogin": GoogleLoginAuthentication,
}

AUTH_SCHEME_ORDER = ["hmacdigest", "googlelogin", "digest", "wsse", "basic"]


class FileCache(object):
    """Uses a local directory as a store for cached files.
    Not really safe to use if multiple threads or processes are going to
    be running on the same cache.
    """

    def __init__(self, cache, safe=safename):  # use safe=lambda x: md5.new(x).hexdigest() for the old behavior
        self.cache = cache
        self.safe = safe
        if not os.path.exists(cache):
            os.makedirs(self.cache)

    def get(self, key):
        retval = None
        cacheFullPath = os.path.join(self.cache, self.safe(key))
        try:
            f = open(cacheFullPath, "rb")
            retval = f.read()
            f.close()
        except IOError:
            pass
        return retval

    def set(self, key, value):
        cacheFullPath = os.path.join(self.cache, self.safe(key))
        f = open(cacheFullPath, "wb")
        f.write(value)
        f.close()

    def delete(self, key):
        cacheFullPath = os.path.join(self.cache, self.safe(key))
        if os.path.exists(cacheFullPath):
            os.remove(cacheFullPath)


class Credentials(object):
    def __init__(self):
        self.credentials = []

    def add(self, name, password, domain=""):
        self.credentials.append((domain.lower(), name, password))

    def clear(self):
        self.credentials = []

    def iter(self, domain):
        for (cdomain, name, password) in self.credentials:
            if cdomain == "" or domain == cdomain:
                yield (name, password)


class KeyCerts(Credentials):
    """Identical to Credentials except that
    name/password are mapped to key/cert."""

    def add(self, key, cert, domain, password):
        self.credentials.append((domain.lower(), key, cert, password))

    def iter(self, domain):
        for (cdomain, key, cert, password) in self.credentials:
            if cdomain == "" or domain == cdomain:
                yield (key, cert, password)


class AllHosts(object):
    pass


class ProxyInfo(object):
    """Collect information required to use a proxy."""

    bypass_hosts = ()

    def __init__(
        self, proxy_type, proxy_host, proxy_port, proxy_rdns=True, proxy_user=None, proxy_pass=None, proxy_headers=None,
    ):
        """Args:

          proxy_type: The type of proxy server.  This must be set to one of
          socks.PROXY_TYPE_XXX constants.  For example:  p =
          ProxyInfo(proxy_type=socks.PROXY_TYPE_HTTP, proxy_host='localhost',
          proxy_port=8000)
          proxy_host: The hostname or IP address of the proxy server.
          proxy_port: The port that the proxy server is running on.
          proxy_rdns: If True (default), DNS queries will not be performed
          locally, and instead, handed to the proxy to resolve.  This is useful
          if the network does not allow resolution of non-local names. In
          httplib2 0.9 and earlier, this defaulted to False.
          proxy_user: The username used to authenticate with the proxy server.
          proxy_pass: The password used to authenticate with the proxy server.
          proxy_headers: Additional or modified headers for the proxy connect
          request.
        """
        if isinstance(proxy_user, bytes):
            proxy_user = proxy_user.decode()
        if isinstance(proxy_pass, bytes):
            proxy_pass = proxy_pass.decode()
        (
            self.proxy_type,
            self.proxy_host,
            self.proxy_port,
            self.proxy_rdns,
            self.proxy_user,
            self.proxy_pass,
            self.proxy_headers,
        ) = (
            proxy_type,
            proxy_host,
            proxy_port,
            proxy_rdns,
            proxy_user,
            proxy_pass,
            proxy_headers,
        )

    def astuple(self):
        return (
            self.proxy_type,
            self.proxy_host,
            self.proxy_port,
            self.proxy_rdns,
            self.proxy_user,
            self.proxy_pass,
            self.proxy_headers,
        )

    def isgood(self):
        return socks and (self.proxy_host != None) and (self.proxy_port != None)

    def applies_to(self, hostname):
        return not self.bypass_host(hostname)

    def bypass_host(self, hostname):
        """Has this host been excluded from the proxy config"""
        if self.bypass_hosts is AllHosts:
            return True

        hostname = "." + hostname.lstrip(".")
        for skip_name in self.bypass_hosts:
            # *.suffix
            if skip_name.startswith(".") and hostname.endswith(skip_name):
                return True
            # exact match
            if hostname == "." + skip_name:
                return True
        return False

    def __repr__(self):
        return (
            "<ProxyInfo type={p.proxy_type} "
            "host:port={p.proxy_host}:{p.proxy_port} rdns={p.proxy_rdns}"
            + " user={p.proxy_user} headers={p.proxy_headers}>"
        ).format(p=self)


def proxy_info_from_environment(method="http"):
    """Read proxy info from the environment variables.
    """
    if method not in ("http", "https"):
        return

    env_var = method + "_proxy"
    url = os.environ.get(env_var, os.environ.get(env_var.upper()))
    if not url:
        return
    return proxy_info_from_url(url, method, noproxy=None)


def proxy_info_from_url(url, method="http", noproxy=None):
    """Construct a ProxyInfo from a URL (such as http_proxy env var)
    """
    url = urllib.parse.urlparse(url)

    proxy_type = 3  # socks.PROXY_TYPE_HTTP
    pi = ProxyInfo(
        proxy_type=proxy_type,
        proxy_host=url.hostname,
        proxy_port=url.port or dict(https=443, http=80)[method],
        proxy_user=url.username or None,
        proxy_pass=url.password or None,
        proxy_headers=None,
    )

    bypass_hosts = []
    # If not given an explicit noproxy value, respect values in env vars.
    if noproxy is None:
        noproxy = os.environ.get("no_proxy", os.environ.get("NO_PROXY", ""))
    # Special case: A single '*' character means all hosts should be bypassed.
    if noproxy == "*":
        bypass_hosts = AllHosts
    elif noproxy.strip():
        bypass_hosts = noproxy.split(",")
        bypass_hosts = tuple(filter(bool, bypass_hosts))  # To exclude empty string.

    pi.bypass_hosts = bypass_hosts
    return pi


class HTTPConnectionWithTimeout(http.client.HTTPConnection):
    """HTTPConnection subclass that supports timeouts

    HTTPConnection subclass that supports timeouts

    All timeouts are in seconds. If None is passed for timeout then
    Python's default timeout for sockets will be used. See for example
    the docs of socket.setdefaulttimeout():
    http://docs.python.org/library/socket.html#socket.setdefaulttimeout
    """

    def __init__(self, host, port=None, timeout=None, proxy_info=None):
        http.client.HTTPConnection.__init__(self, host, port=port, timeout=timeout)

        self.proxy_info = proxy_info
        if proxy_info and not isinstance(proxy_info, ProxyInfo):
            self.proxy_info = proxy_info("http")

    def connect(self):
        """Connect to the host and port specified in __init__."""
        if self.proxy_info and socks is None:
            raise ProxiesUnavailableError("Proxy support missing but proxy use was requested!")
        if self.proxy_info and self.proxy_info.isgood() and self.proxy_info.applies_to(self.host):
            use_proxy = True
            (
                proxy_type,
                proxy_host,
                proxy_port,
                proxy_rdns,
                proxy_user,
                proxy_pass,
                proxy_headers,
            ) = self.proxy_info.astuple()

            host = proxy_host
            port = proxy_port
        else:
            use_proxy = False

            host = self.host
            port = self.port
            proxy_type = None

        socket_err = None

        for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                if use_proxy:
                    self.sock = socks.socksocket(af, socktype, proto)
                    self.sock.setproxy(
                        proxy_type, proxy_host, proxy_port, proxy_rdns, proxy_user, proxy_pass,
                    )
                else:
                    self.sock = socket.socket(af, socktype, proto)
                    self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                if has_timeout(self.timeout):
                    self.sock.settimeout(self.timeout)
                if self.debuglevel > 0:
                    print("connect: ({0}, {1}) ************".format(self.host, self.port))
                    if use_proxy:
                        print(
                            "proxy: {0} ************".format(
                                str((proxy_host, proxy_port, proxy_rdns, proxy_user, proxy_pass, proxy_headers,))
                            )
                        )

                self.sock.connect((self.host, self.port) + sa[2:])
            except socket.error as e:
                socket_err = e
                if self.debuglevel > 0:
                    print("connect fail: ({0}, {1})".format(self.host, self.port))
                    if use_proxy:
                        print(
                            "proxy: {0}".format(
                                str((proxy_host, proxy_port, proxy_rdns, proxy_user, proxy_pass, proxy_headers,))
                            )
                        )
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket_err


class HTTPSConnectionWithTimeout(http.client.HTTPSConnection):
    """This class allows communication via SSL.

    All timeouts are in seconds. If None is passed for timeout then
    Python's default timeout for sockets will be used. See for example
    the docs of socket.setdefaulttimeout():
    http://docs.python.org/library/socket.html#socket.setdefaulttimeout
    """

    def __init__(
        self,
        host,
        port=None,
        key_file=None,
        cert_file=None,
        timeout=None,
        proxy_info=None,
        ca_certs=None,
        disable_ssl_certificate_validation=False,
        tls_maximum_version=None,
        tls_minimum_version=None,
        key_password=None,
    ):

        self.disable_ssl_certificate_validation = disable_ssl_certificate_validation
        self.ca_certs = ca_certs if ca_certs else CA_CERTS

        self.proxy_info = proxy_info
        if proxy_info and not isinstance(proxy_info, ProxyInfo):
            self.proxy_info = proxy_info("https")

        context = _build_ssl_context(
            self.disable_ssl_certificate_validation,
            self.ca_certs,
            cert_file,
            key_file,
            maximum_version=tls_maximum_version,
            minimum_version=tls_minimum_version,
            key_password=key_password,
        )
        super(HTTPSConnectionWithTimeout, self).__init__(
            host, port=port, timeout=timeout, context=context,
        )
        self.key_file = key_file
        self.cert_file = cert_file
        self.key_password = key_password

    def connect(self):
        """Connect to a host on a given (SSL) port."""
        if self.proxy_info and self.proxy_info.isgood() and self.proxy_info.applies_to(self.host):
            use_proxy = True
            (
                proxy_type,
                proxy_host,
                proxy_port,
                proxy_rdns,
                proxy_user,
                proxy_pass,
                proxy_headers,
            ) = self.proxy_info.astuple()

            host = proxy_host
            port = proxy_port
        else:
            use_proxy = False

            host = self.host
            port = self.port
            proxy_type = None
            proxy_headers = None

        socket_err = None

        address_info = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
        for family, socktype, proto, canonname, sockaddr in address_info:
            try:
                if use_proxy:
                    sock = socks.socksocket(family, socktype, proto)

                    sock.setproxy(
                        proxy_type, proxy_host, proxy_port, proxy_rdns, proxy_user, proxy_pass,
                    )
                else:
                    sock = socket.socket(family, socktype, proto)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                if has_timeout(self.timeout):
                    sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))

                self.sock = self._context.wrap_socket(sock, server_hostname=self.host)

                # Python 3.3 compatibility: emulate the check_hostname behavior
                if not hasattr(self._context, "check_hostname") and not self.disable_ssl_certificate_validation:
                    try:
                        ssl.match_hostname(self.sock.getpeercert(), self.host)
                    except Exception:
                        self.sock.shutdown(socket.SHUT_RDWR)
                        self.sock.close()
                        raise

                if self.debuglevel > 0:
                    print("connect: ({0}, {1})".format(self.host, self.port))
                    if use_proxy:
                        print(
                            "proxy: {0}".format(
                                str((proxy_host, proxy_port, proxy_rdns, proxy_user, proxy_pass, proxy_headers,))
                            )
                        )
            except (ssl.SSLError, ssl.CertificateError) as e:
                if sock:
                    sock.close()
                if self.sock:
                    self.sock.close()
                self.sock = None
                raise
            except (socket.timeout, socket.gaierror):
                raise
            except socket.error as e:
                socket_err = e
                if self.debuglevel > 0:
                    print("connect fail: ({0}, {1})".format(self.host, self.port))
                    if use_proxy:
                        print(
                            "proxy: {0}".format(
                                str((proxy_host, proxy_port, proxy_rdns, proxy_user, proxy_pass, proxy_headers,))
                            )
                        )
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket_err


SCHEME_TO_CONNECTION = {
    "http": HTTPConnectionWithTimeout,
    "https": HTTPSConnectionWithTimeout,
}


class Http(object):
    """An HTTP client that handles:

    - all methods
    - caching
    - ETags
    - compression,
    - HTTPS
    - Basic
    - Digest
    - WSSE

    and more.
    """

    def __init__(
        self,
        cache=None,
        timeout=None,
        proxy_info=proxy_info_from_environment,
        ca_certs=None,
        disable_ssl_certificate_validation=False,
        tls_maximum_version=None,
        tls_minimum_version=None,
    ):
        """If 'cache' is a string then it is used as a directory name for
        a disk cache. Otherwise it must be an object that supports the
        same interface as FileCache.

        All timeouts are in seconds. If None is passed for timeout
        then Python's default timeout for sockets will be used. See
        for example the docs of socket.setdefaulttimeout():
        http://docs.python.org/library/socket.html#socket.setdefaulttimeout

        `proxy_info` may be:
          - a callable that takes the http scheme ('http' or 'https') and
            returns a ProxyInfo instance per request. By default, uses
            proxy_info_from_environment.
          - a ProxyInfo instance (static proxy config).
          - None (proxy disabled).

        ca_certs is the path of a file containing root CA certificates for SSL
        server certificate validation.  By default, a CA cert file bundled with
        httplib2 is used.

        If disable_ssl_certificate_validation is true, SSL cert validation will
        not be performed.

        tls_maximum_version / tls_minimum_version require Python 3.7+ /
        OpenSSL 1.1.0g+. A value of "TLSv1_3" requires OpenSSL 1.1.1+.
        """
        self.proxy_info = proxy_info
        self.ca_certs = ca_certs
        self.disable_ssl_certificate_validation = disable_ssl_certificate_validation
        self.tls_maximum_version = tls_maximum_version
        self.tls_minimum_version = tls_minimum_version
        # Map domain name to an httplib connection
        self.connections = {}
        # The location of the cache, for now a directory
        # where cached responses are held.
        if cache and isinstance(cache, str):
            self.cache = FileCache(cache)
        else:
            self.cache = cache

        # Name/password
        self.credentials = Credentials()

        # Key/cert
        self.certificates = KeyCerts()

        # authorization objects
        self.authorizations = []

        # If set to False then no redirects are followed, even safe ones.
        self.follow_redirects = True

        self.redirect_codes = REDIRECT_CODES

        # Which HTTP methods do we apply optimistic concurrency to, i.e.
        # which methods get an "if-match:" etag header added to them.
        self.optimistic_concurrency_methods = ["PUT", "PATCH"]

        self.safe_methods = list(SAFE_METHODS)

        # If 'follow_redirects' is True, and this is set to True then
        # all redirecs are followed, including unsafe ones.
        self.follow_all_redirects = False

        self.ignore_etag = False

        self.force_exception_to_status_code = False

        self.timeout = timeout

        # Keep Authorization: headers on a redirect.
        self.forward_authorization_headers = False

    def close(self):
        """Close persistent connections, clear sensitive data.
        Not thread-safe, requires external synchronization against concurrent requests.
        """
        existing, self.connections = self.connections, {}
        for _, c in existing.items():
            c.close()
        self.certificates.clear()
        self.clear_credentials()

    def __getstate__(self):
        state_dict = copy.copy(self.__dict__)
        # In case request is augmented by some foreign object such as
        # credentials which handle auth
        if "request" in state_dict:
            del state_dict["request"]
        if "connections" in state_dict:
            del state_dict["connections"]
        return state_dict

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.connections = {}

    def _auth_from_challenge(self, host, request_uri, headers, response, content):
        """A generator that creates Authorization objects
           that can be applied to requests.
        """
        challenges = auth._parse_www_authenticate(response, "www-authenticate")
        for cred in self.credentials.iter(host):
            for scheme in AUTH_SCHEME_ORDER:
                if scheme in challenges:
                    yield AUTH_SCHEME_CLASSES[scheme](cred, host, request_uri, headers, response, content, self)

    def add_credentials(self, name, password, domain=""):
        """Add a name and password that will be used
        any time a request requires authentication."""
        self.credentials.add(name, password, domain)

    def add_certificate(self, key, cert, domain, password=None):
        """Add a key and cert that will be used
        any time a request requires authentication."""
        self.certificates.add(key, cert, domain, password)

    def clear_credentials(self):
        """Remove all the names and passwords
        that are used for authentication"""
        self.credentials.clear()
        self.authorizations = []

    def _conn_request(self, conn, request_uri, method, body, headers):
        i = 0
        seen_bad_status_line = False
        while i < RETRIES:
            i += 1
            try:
                if conn.sock is None:
                    conn.connect()
                conn.request(method, request_uri, body, headers)
            except socket.timeout:
                conn.close()
                raise
            except socket.gaierror:
                conn.close()
                raise ServerNotFoundError("Unable to find the server at %s" % conn.host)
            except socket.error as e:
                errno_ = _errno_from_exception(e)
                if errno_ in (errno.ENETUNREACH, errno.EADDRNOTAVAIL) and i < RETRIES:
                    continue  # retry on potentially transient errors
                raise
            except http.client.HTTPException:
                if conn.sock is None:
                    if i < RETRIES - 1:
                        conn.close()
                        conn.connect()
                        continue
                    else:
                        conn.close()
                        raise
                if i < RETRIES - 1:
                    conn.close()
                    conn.connect()
                    continue
                # Just because the server closed the connection doesn't apparently mean
                # that the server didn't send a response.
                pass
            try:
                response = conn.getresponse()
            except (http.client.BadStatusLine, http.client.ResponseNotReady):
                # If we get a BadStatusLine on the first try then that means
                # the connection just went stale, so retry regardless of the
                # number of RETRIES set.
                if not seen_bad_status_line and i == 1:
                    i = 0
                    seen_bad_status_line = True
                    conn.close()
                    conn.connect()
                    continue
                else:
                    conn.close()
                    raise
            except socket.timeout:
                raise
            except (socket.error, http.client.HTTPException):
                conn.close()
                if i == 0:
                    conn.close()
                    conn.connect()
                    continue
                else:
                    raise
            else:
                content = b""
                if method == "HEAD":
                    conn.close()
                else:
                    content = response.read()
                response = Response(response)
                if method != "HEAD":
                    content = _decompressContent(response, content)

            break
        return (response, content)

    def _request(
        self, conn, host, absolute_uri, request_uri, method, body, headers, redirections, cachekey,
    ):
        """Do the actual request using the connection object
        and also follow one level of redirects if necessary"""

        auths = [(auth.depth(request_uri), auth) for auth in self.authorizations if auth.inscope(host, request_uri)]
        auth = auths and sorted(auths)[0][1] or None
        if auth:
            auth.request(method, request_uri, headers, body)

        (response, content) = self._conn_request(conn, request_uri, method, body, headers)

        if auth:
            if auth.response(response, body):
                auth.request(method, request_uri, headers, body)
                (response, content) = self._conn_request(conn, request_uri, method, body, headers)
                response._stale_digest = 1

        if response.status == 401:
            for authorization in self._auth_from_challenge(host, request_uri, headers, response, content):
                authorization.request(method, request_uri, headers, body)
                (response, content) = self._conn_request(conn, request_uri, method, body, headers)
                if response.status != 401:
                    self.authorizations.append(authorization)
                    authorization.response(response, body)
                    break

        if self.follow_all_redirects or method in self.safe_methods or response.status in (303, 308):
            if self.follow_redirects and response.status in self.redirect_codes:
                # Pick out the location header and basically start from the beginning
                # remembering first to strip the ETag header and decrement our 'depth'
                if redirections:
                    if "location" not in response and response.status != 300:
                        raise RedirectMissingLocation(
                            _("Redirected but the response is missing a Location: header."), response, content,
                        )
                    # Fix-up relative redirects (which violate an RFC 2616 MUST)
                    if "location" in response:
                        location = response["location"]
                        (scheme, authority, path, query, fragment) = parse_uri(location)
                        if authority == None:
                            response["location"] = urllib.parse.urljoin(absolute_uri, location)
                    if response.status == 308 or (response.status == 301 and (method in self.safe_methods)):
                        response["-x-permanent-redirect-url"] = response["location"]
                        if "content-location" not in response:
                            response["content-location"] = absolute_uri
                        _updateCache(headers, response, content, self.cache, cachekey)
                    if "if-none-match" in headers:
                        del headers["if-none-match"]
                    if "if-modified-since" in headers:
                        del headers["if-modified-since"]
                    if "authorization" in headers and not self.forward_authorization_headers:
                        del headers["authorization"]
                    if "location" in response:
                        location = response["location"]
                        old_response = copy.deepcopy(response)
                        if "content-location" not in old_response:
                            old_response["content-location"] = absolute_uri
                        redirect_method = method
                        if response.status in [302, 303]:
                            redirect_method = "GET"
                            body = None
                        (response, content) = self.request(
                            location, method=redirect_method, body=body, headers=headers, redirections=redirections - 1,
                        )
                        response.previous = old_response
                else:
                    raise RedirectLimit(
                        "Redirected more times than redirection_limit allows.", response, content,
                    )
            elif response.status in [200, 203] and method in self.safe_methods:
                # Don't cache 206's since we aren't going to handle byte range requests
                if "content-location" not in response:
                    response["content-location"] = absolute_uri
                _updateCache(headers, response, content, self.cache, cachekey)

        return (response, content)

    def _normalize_headers(self, headers):
        return _normalize_headers(headers)

    # Need to catch and rebrand some exceptions
    # Then need to optionally turn all exceptions into status codes
    # including all socket.* and httplib.* exceptions.

    def request(
        self, uri, method="GET", body=None, headers=None, redirections=DEFAULT_MAX_REDIRECTS, connection_type=None,
    ):
        """ Performs a single HTTP request.
The 'uri' is the URI of the HTTP resource and can begin
with either 'http' or 'https'. The value of 'uri' must be an absolute URI.

The 'method' is the HTTP method to perform, such as GET, POST, DELETE, etc.
There is no restriction on the methods allowed.

The 'body' is the entity body to be sent with the request. It is a string
object.

Any extra headers that are to be sent with the request should be provided in the
'headers' dictionary.

The maximum number of redirect to follow before raising an
exception is 'redirections. The default is 5.

The return value is a tuple of (response, content), the first
being and instance of the 'Response' class, the second being
a string that contains the response entity body.
        """
        conn_key = ""

        try:
            if headers is None:
                headers = {}
            else:
                headers = self._normalize_headers(headers)

            if "user-agent" not in headers:
                headers["user-agent"] = "Python-httplib2/%s (gzip)" % __version__

            uri = iri2uri(uri)
            # Prevent CWE-75 space injection to manipulate request via part of uri.
            # Prevent CWE-93 CRLF injection to modify headers via part of uri.
            uri = uri.replace(" ", "%20").replace("\r", "%0D").replace("\n", "%0A")

            (scheme, authority, request_uri, defrag_uri) = urlnorm(uri)

            conn_key = scheme + ":" + authority
            conn = self.connections.get(conn_key)
            if conn is None:
                if not connection_type:
                    connection_type = SCHEME_TO_CONNECTION[scheme]
                certs = list(self.certificates.iter(authority))
                if issubclass(connection_type, HTTPSConnectionWithTimeout):
                    if certs:
                        conn = self.connections[conn_key] = connection_type(
                            authority,
                            key_file=certs[0][0],
                            cert_file=certs[0][1],
                            timeout=self.timeout,
                            proxy_info=self.proxy_info,
                            ca_certs=self.ca_certs,
                            disable_ssl_certificate_validation=self.disable_ssl_certificate_validation,
                            tls_maximum_version=self.tls_maximum_version,
                            tls_minimum_version=self.tls_minimum_version,
                            key_password=certs[0][2],
                        )
                    else:
                        conn = self.connections[conn_key] = connection_type(
                            authority,
                            timeout=self.timeout,
                            proxy_info=self.proxy_info,
                            ca_certs=self.ca_certs,
                            disable_ssl_certificate_validation=self.disable_ssl_certificate_validation,
                            tls_maximum_version=self.tls_maximum_version,
                            tls_minimum_version=self.tls_minimum_version,
                        )
                else:
                    conn = self.connections[conn_key] = connection_type(
                        authority, timeout=self.timeout, proxy_info=self.proxy_info
                    )
                conn.set_debuglevel(debuglevel)

            if "range" not in headers and "accept-encoding" not in headers:
                headers["accept-encoding"] = "gzip, deflate"

            info = email.message.Message()
            cachekey = None
            cached_value = None
            if self.cache:
                cachekey = defrag_uri
                cached_value = self.cache.get(cachekey)
                if cached_value:
                    try:
                        info, content = cached_value.split(b"\r\n\r\n", 1)
                        info = email.message_from_bytes(info)
                        for k, v in info.items():
                            if v.startswith("=?") and v.endswith("?="):
                                info.replace_header(k, str(*email.header.decode_header(v)[0]))
                    except (IndexError, ValueError):
                        self.cache.delete(cachekey)
                        cachekey = None
                        cached_value = None

            if (
                method in self.optimistic_concurrency_methods
                and self.cache
                and "etag" in info
                and not self.ignore_etag
                and "if-match" not in headers
            ):
                # http://www.w3.org/1999/04/Editing/
                headers["if-match"] = info["etag"]

            # https://tools.ietf.org/html/rfc7234
            # A cache MUST invalidate the effective Request URI as well as [...] Location and Content-Location
            # when a non-error status code is received in response to an unsafe request method.
            if self.cache and cachekey and method not in self.safe_methods:
                self.cache.delete(cachekey)

            # Check the vary header in the cache to see if this request
            # matches what varies in the cache.
            if method in self.safe_methods and "vary" in info:
                vary = info["vary"]
                vary_headers = vary.lower().replace(" ", "").split(",")
                for header in vary_headers:
                    key = "-varied-%s" % header
                    value = info[key]
                    if headers.get(header, None) != value:
                        cached_value = None
                        break

            if (
                self.cache
                and cached_value
                and (method in self.safe_methods or info["status"] == "308")
                and "range" not in headers
            ):
                redirect_method = method
                if info["status"] not in ("307", "308"):
                    redirect_method = "GET"
                if "-x-permanent-redirect-url" in info:
                    # Should cached permanent redirects be counted in our redirection count? For now, yes.
                    if redirections <= 0:
                        raise RedirectLimit(
                            "Redirected more times than redirection_limit allows.", {}, "",
                        )
                    (response, new_content) = self.request(
                        info["-x-permanent-redirect-url"],
                        method=redirect_method,
                        headers=headers,
                        redirections=redirections - 1,
                    )
                    response.previous = Response(info)
                    response.previous.fromcache = True
                else:
                    # Determine our course of action:
                    #   Is the cached entry fresh or stale?
                    #   Has the client requested a non-cached response?
                    #
                    # There seems to be three possible answers:
                    # 1. [FRESH] Return the cache entry w/o doing a GET
                    # 2. [STALE] Do the GET (but add in cache validators if available)
                    # 3. [TRANSPARENT] Do a GET w/o any cache validators (Cache-Control: no-cache) on the request
                    entry_disposition = _entry_disposition(info, headers)

                    if entry_disposition == "FRESH":
                        response = Response(info)
                        response.fromcache = True
                        return (response, content)

                    if entry_disposition == "STALE":
                        if "etag" in info and not self.ignore_etag and not "if-none-match" in headers:
                            headers["if-none-match"] = info["etag"]
                        if "last-modified" in info and not "last-modified" in headers:
                            headers["if-modified-since"] = info["last-modified"]
                    elif entry_disposition == "TRANSPARENT":
                        pass

                    (response, new_content) = self._request(
                        conn, authority, uri, request_uri, method, body, headers, redirections, cachekey,
                    )

                if response.status == 304 and method == "GET":
                    # Rewrite the cache entry with the new end-to-end headers
                    # Take all headers that are in response
                    # and overwrite their values in info.
                    # unless they are hop-by-hop, or are listed in the connection header.

                    for key in _get_end2end_headers(response):
                        info[key] = response[key]
                    merged_response = Response(info)
                    if hasattr(response, "_stale_digest"):
                        merged_response._stale_digest = response._stale_digest
                    _updateCache(headers, merged_response, content, self.cache, cachekey)
                    response = merged_response
                    response.status = 200
                    response.fromcache = True

                elif response.status == 200:
                    content = new_content
                else:
                    self.cache.delete(cachekey)
                    content = new_content
            else:
                cc = _parse_cache_control(headers)
                if "only-if-cached" in cc:
                    info["status"] = "504"
                    response = Response(info)
                    content = b""
                else:
                    (response, content) = self._request(
                        conn, authority, uri, request_uri, method, body, headers, redirections, cachekey,
                    )
        except Exception as e:
            is_timeout = isinstance(e, socket.timeout)
            if is_timeout:
                conn = self.connections.pop(conn_key, None)
                if conn:
                    conn.close()

            if self.force_exception_to_status_code:
                if isinstance(e, HttpLib2ErrorWithResponse):
                    response = e.response
                    content = e.content
                    response.status = 500
                    response.reason = str(e)
                elif isinstance(e, socket.timeout):
                    content = b"Request Timeout"
                    response = Response({"content-type": "text/plain", "status": "408", "content-length": len(content),})
                    response.reason = "Request Timeout"
                else:
                    content = str(e).encode("utf-8")
                    response = Response({"content-type": "text/plain", "status": "400", "content-length": len(content),})
                    response.reason = "Bad Request"
            else:
                raise

        return (response, content)


class Response(dict):
    """An object more like email.message than httplib.HTTPResponse."""

    """Is this response from our local cache"""
    fromcache = False
    """HTTP protocol version used by server.

    10 for HTTP/1.0, 11 for HTTP/1.1.
    """
    version = 11

    "Status code returned by server. "
    status = 200
    """Reason phrase returned by server."""
    reason = "Ok"

    previous = None

    def __init__(self, info):
        # info is either an email.message or
        # an httplib.HTTPResponse object.
        if isinstance(info, http.client.HTTPResponse):
            for key, value in info.getheaders():
                key = key.lower()
                prev = self.get(key)
                if prev is not None:
                    value = ", ".join((prev, value))
                self[key] = value
            self.status = info.status
            self["status"] = str(self.status)
            self.reason = info.reason
            self.version = info.version
        elif isinstance(info, email.message.Message):
            for key, value in list(info.items()):
                self[key.lower()] = value
            self.status = int(self["status"])
        else:
            for key, value in info.items():
                self[key.lower()] = value
            self.status = int(self.get("status", self.status))

    def __getattr__(self, name):
        if name == "dict":
            return self
        else:
            raise AttributeError(name)

# === NexusCore/openenv\Lib\site-packages\fontTools\feaLib\builder.py ===
from fontTools.misc import sstruct
from fontTools.misc.textTools import Tag, tostr, binary2num, safeEval
from fontTools.feaLib.error import FeatureLibError
from fontTools.feaLib.lookupDebugInfo import (
    LookupDebugInfo,
    LOOKUP_DEBUG_INFO_KEY,
    LOOKUP_DEBUG_ENV_VAR,
)
from fontTools.feaLib.parser import Parser
from fontTools.feaLib.ast import FeatureFile
from fontTools.feaLib.variableScalar import VariableScalar
from fontTools.otlLib import builder as otl
from fontTools.otlLib.maxContextCalc import maxCtxFont
from fontTools.ttLib import newTable, getTableModule
from fontTools.ttLib.tables import otBase, otTables
from fontTools.otlLib.builder import (
    AlternateSubstBuilder,
    ChainContextPosBuilder,
    ChainContextSubstBuilder,
    LigatureSubstBuilder,
    MultipleSubstBuilder,
    CursivePosBuilder,
    MarkBasePosBuilder,
    MarkLigPosBuilder,
    MarkMarkPosBuilder,
    ReverseChainSingleSubstBuilder,
    SingleSubstBuilder,
    ClassPairPosSubtableBuilder,
    PairPosBuilder,
    SinglePosBuilder,
    ChainContextualRule,
    AnySubstBuilder,
)
from fontTools.otlLib.error import OpenTypeLibError
from fontTools.varLib.varStore import OnlineVarStoreBuilder
from fontTools.varLib.builder import buildVarDevTable
from fontTools.varLib.featureVars import addFeatureVariationsRaw
from fontTools.varLib.models import normalizeValue, piecewiseLinearMap
from collections import defaultdict
import copy
import itertools
from io import StringIO
import logging
import warnings
import os


log = logging.getLogger(__name__)


def addOpenTypeFeatures(font, featurefile, tables=None, debug=False):
    """Add features from a file to a font. Note that this replaces any features
    currently present.

    Args:
        font (feaLib.ttLib.TTFont): The font object.
        featurefile: Either a path or file object (in which case we
            parse it into an AST), or a pre-parsed AST instance.
        tables: If passed, restrict the set of affected tables to those in the
            list.
        debug: Whether to add source debugging information to the font in the
            ``Debg`` table

    """
    builder = Builder(font, featurefile)
    builder.build(tables=tables, debug=debug)


def addOpenTypeFeaturesFromString(
    font, features, filename=None, tables=None, debug=False
):
    """Add features from a string to a font. Note that this replaces any
    features currently present.

    Args:
        font (feaLib.ttLib.TTFont): The font object.
        features: A string containing feature code.
        filename: The directory containing ``filename`` is used as the root of
            relative ``include()`` paths; if ``None`` is provided, the current
            directory is assumed.
        tables: If passed, restrict the set of affected tables to those in the
            list.
        debug: Whether to add source debugging information to the font in the
            ``Debg`` table

    """

    featurefile = StringIO(tostr(features))
    if filename:
        featurefile.name = filename
    addOpenTypeFeatures(font, featurefile, tables=tables, debug=debug)


class Builder(object):
    supportedTables = frozenset(
        Tag(tag)
        for tag in [
            "BASE",
            "GDEF",
            "GPOS",
            "GSUB",
            "OS/2",
            "head",
            "hhea",
            "name",
            "vhea",
            "STAT",
        ]
    )

    def __init__(self, font, featurefile):
        self.font = font
        # 'featurefile' can be either a path or file object (in which case we
        # parse it into an AST), or a pre-parsed AST instance
        if isinstance(featurefile, FeatureFile):
            self.parseTree, self.file = featurefile, None
        else:
            self.parseTree, self.file = None, featurefile
        self.glyphMap = font.getReverseGlyphMap()
        self.varstorebuilder = None
        if "fvar" in font:
            self.axes = font["fvar"].axes
            self.varstorebuilder = OnlineVarStoreBuilder(
                [ax.axisTag for ax in self.axes]
            )
        self.default_language_systems_ = set()
        self.script_ = None
        self.lookupflag_ = 0
        self.lookupflag_markFilterSet_ = None
        self.use_extension_ = False
        self.language_systems = set()
        self.seen_non_DFLT_script_ = False
        self.named_lookups_ = {}
        self.cur_lookup_ = None
        self.cur_lookup_name_ = None
        self.cur_feature_name_ = None
        self.lookups_ = []
        self.lookup_locations = {"GSUB": {}, "GPOS": {}}
        self.features_ = {}  # ('latn', 'DEU ', 'smcp') --> [LookupBuilder*]
        self.required_features_ = {}  # ('latn', 'DEU ') --> 'scmp'
        self.feature_variations_ = {}
        # for feature 'aalt'
        self.aalt_features_ = []  # [(location, featureName)*], for 'aalt'
        self.aalt_location_ = None
        self.aalt_alternates_ = {}
        self.aalt_use_extension_ = False
        # for 'featureNames'
        self.featureNames_ = set()
        self.featureNames_ids_ = {}
        # for 'cvParameters'
        self.cv_parameters_ = set()
        self.cv_parameters_ids_ = {}
        self.cv_num_named_params_ = {}
        self.cv_characters_ = defaultdict(list)
        # for feature 'size'
        self.size_parameters_ = None
        # for table 'head'
        self.fontRevision_ = None  # 2.71
        # for table 'name'
        self.names_ = []
        # for table 'BASE'
        self.base_horiz_axis_ = None
        self.base_vert_axis_ = None
        # for table 'GDEF'
        self.attachPoints_ = {}  # "a" --> {3, 7}
        self.ligCaretCoords_ = {}  # "f_f_i" --> {300, 600}
        self.ligCaretPoints_ = {}  # "f_f_i" --> {3, 7}
        self.glyphClassDefs_ = {}  # "fi" --> (2, (file, line, column))
        self.markAttach_ = {}  # "acute" --> (4, (file, line, column))
        self.markAttachClassID_ = {}  # frozenset({"acute", "grave"}) --> 4
        self.markFilterSets_ = {}  # frozenset({"acute", "grave"}) --> 4
        # for table 'OS/2'
        self.os2_ = {}
        # for table 'hhea'
        self.hhea_ = {}
        # for table 'vhea'
        self.vhea_ = {}
        # for table 'STAT'
        self.stat_ = {}
        # for conditionsets
        self.conditionsets_ = {}
        # We will often use exactly the same locations (i.e. the font's masters)
        # for a large number of variable scalars. Instead of creating a model
        # for each, let's share the models.
        self.model_cache = {}

    def build(self, tables=None, debug=False):
        if self.parseTree is None:
            self.parseTree = Parser(self.file, self.glyphMap).parse()
        self.parseTree.build(self)
        # by default, build all the supported tables
        if tables is None:
            tables = self.supportedTables
        else:
            tables = frozenset(tables)
            unsupported = tables - self.supportedTables
            if unsupported:
                unsupported_string = ", ".join(sorted(unsupported))
                raise NotImplementedError(
                    "The following tables were requested but are unsupported: "
                    f"{unsupported_string}."
                )
        if "GSUB" in tables:
            self.build_feature_aalt_()
        if "head" in tables:
            self.build_head()
        if "hhea" in tables:
            self.build_hhea()
        if "vhea" in tables:
            self.build_vhea()
        if "name" in tables:
            self.build_name()
        if "OS/2" in tables:
            self.build_OS_2()
        if "STAT" in tables:
            self.build_STAT()
        for tag in ("GPOS", "GSUB"):
            if tag not in tables:
                continue
            table = self.makeTable(tag)
            if self.feature_variations_:
                self.makeFeatureVariations(table, tag)
            if (
                table.ScriptList.ScriptCount > 0
                or table.FeatureList.FeatureCount > 0
                or table.LookupList.LookupCount > 0
            ):
                fontTable = self.font[tag] = newTable(tag)
                fontTable.table = table
            elif tag in self.font:
                del self.font[tag]
        if any(tag in self.font for tag in ("GPOS", "GSUB")) and "OS/2" in self.font:
            self.font["OS/2"].usMaxContext = maxCtxFont(self.font)
        if "GDEF" in tables:
            gdef = self.buildGDEF()
            if gdef:
                self.font["GDEF"] = gdef
            elif "GDEF" in self.font:
                del self.font["GDEF"]
        if "BASE" in tables:
            base = self.buildBASE()
            if base:
                self.font["BASE"] = base
            elif "BASE" in self.font:
                del self.font["BASE"]
        if debug or os.environ.get(LOOKUP_DEBUG_ENV_VAR):
            self.buildDebg()

    def get_chained_lookup_(self, location, builder_class):
        result = builder_class(self.font, location)
        result.lookupflag = self.lookupflag_
        result.markFilterSet = self.lookupflag_markFilterSet_
        result.extension = self.use_extension_
        self.lookups_.append(result)
        return result

    def add_lookup_to_feature_(self, lookup, feature_name):
        for script, lang in self.language_systems:
            key = (script, lang, feature_name)
            self.features_.setdefault(key, []).append(lookup)

    def get_lookup_(self, location, builder_class):
        if (
            self.cur_lookup_
            and type(self.cur_lookup_) == builder_class
            and self.cur_lookup_.lookupflag == self.lookupflag_
            and self.cur_lookup_.markFilterSet == self.lookupflag_markFilterSet_
        ):
            return self.cur_lookup_
        if self.cur_lookup_name_ and self.cur_lookup_:
            raise FeatureLibError(
                "Within a named lookup block, all rules must be of "
                "the same lookup type and flag",
                location,
            )
        self.cur_lookup_ = builder_class(self.font, location)
        self.cur_lookup_.lookupflag = self.lookupflag_
        self.cur_lookup_.markFilterSet = self.lookupflag_markFilterSet_
        self.cur_lookup_.extension = self.use_extension_
        self.lookups_.append(self.cur_lookup_)
        if self.cur_lookup_name_:
            # We are starting a lookup rule inside a named lookup block.
            self.named_lookups_[self.cur_lookup_name_] = self.cur_lookup_
        if self.cur_feature_name_:
            # We are starting a lookup rule inside a feature. This includes
            # lookup rules inside named lookups inside features.
            self.add_lookup_to_feature_(self.cur_lookup_, self.cur_feature_name_)
        return self.cur_lookup_

    def build_feature_aalt_(self):
        if not self.aalt_features_ and not self.aalt_alternates_:
            return
        # > alternate glyphs will be sorted in the order that the source features
        # > are named in the aalt definition, not the order of the feature definitions
        # > in the file. Alternates defined explicitly ... will precede all others.
        # https://github.com/fonttools/fonttools/issues/836
        alternates = {g: list(a) for g, a in self.aalt_alternates_.items()}
        for location, name in self.aalt_features_ + [(None, "aalt")]:
            feature = [
                (script, lang, feature, lookups)
                for (script, lang, feature), lookups in self.features_.items()
                if feature == name
            ]
            # "aalt" does not have to specify its own lookups, but it might.
            if not feature and name != "aalt":
                warnings.warn("%s: Feature %s has not been defined" % (location, name))
                continue
            for script, lang, feature, lookups in feature:
                for lookuplist in lookups:
                    if not isinstance(lookuplist, list):
                        lookuplist = [lookuplist]
                    for lookup in lookuplist:
                        for glyph, alts in lookup.getAlternateGlyphs().items():
                            alts_for_glyph = alternates.setdefault(glyph, [])
                            alts_for_glyph.extend(
                                g for g in alts if g not in alts_for_glyph
                            )
        single = {
            glyph: repl[0] for glyph, repl in alternates.items() if len(repl) == 1
        }
        multi = {glyph: repl for glyph, repl in alternates.items() if len(repl) > 1}
        if not single and not multi:
            return
        self.features_ = {
            (script, lang, feature): lookups
            for (script, lang, feature), lookups in self.features_.items()
            if feature != "aalt"
        }
        old_lookups = self.lookups_
        self.lookups_ = []
        self.start_feature(self.aalt_location_, "aalt", self.aalt_use_extension_)
        if single:
            single_lookup = self.get_lookup_(location, SingleSubstBuilder)
            single_lookup.mapping = single
        if multi:
            multi_lookup = self.get_lookup_(location, AlternateSubstBuilder)
            multi_lookup.alternates = multi
        self.end_feature()
        self.lookups_.extend(old_lookups)

    def build_head(self):
        if not self.fontRevision_:
            return
        table = self.font.get("head")
        if not table:  # this only happens for unit tests
            table = self.font["head"] = newTable("head")
            table.decompile(b"\0" * 54, self.font)
            table.tableVersion = 1.0
            table.magicNumber = 0x5F0F3CF5
            table.created = table.modified = 3406620153  # 2011-12-13 11:22:33
        table.fontRevision = self.fontRevision_

    def build_hhea(self):
        if not self.hhea_:
            return
        table = self.font.get("hhea")
        if not table:  # this only happens for unit tests
            table = self.font["hhea"] = newTable("hhea")
            table.decompile(b"\0" * 36, self.font)
            table.tableVersion = 0x00010000
        if "caretoffset" in self.hhea_:
            table.caretOffset = self.hhea_["caretoffset"]
        if "ascender" in self.hhea_:
            table.ascent = self.hhea_["ascender"]
        if "descender" in self.hhea_:
            table.descent = self.hhea_["descender"]
        if "linegap" in self.hhea_:
            table.lineGap = self.hhea_["linegap"]

    def build_vhea(self):
        if not self.vhea_:
            return
        table = self.font.get("vhea")
        if not table:  # this only happens for unit tests
            table = self.font["vhea"] = newTable("vhea")
            table.decompile(b"\0" * 36, self.font)
            table.tableVersion = 0x00011000
        if "verttypoascender" in self.vhea_:
            table.ascent = self.vhea_["verttypoascender"]
        if "verttypodescender" in self.vhea_:
            table.descent = self.vhea_["verttypodescender"]
        if "verttypolinegap" in self.vhea_:
            table.lineGap = self.vhea_["verttypolinegap"]

    def get_user_name_id(self, table):
        # Try to find first unused font-specific name id
        nameIDs = [name.nameID for name in table.names]
        for user_name_id in range(256, 32767):
            if user_name_id not in nameIDs:
                return user_name_id

    def buildFeatureParams(self, tag):
        params = None
        if tag == "size":
            params = otTables.FeatureParamsSize()
            (
                params.DesignSize,
                params.SubfamilyID,
                params.RangeStart,
                params.RangeEnd,
            ) = self.size_parameters_
            if tag in self.featureNames_ids_:
                params.SubfamilyNameID = self.featureNames_ids_[tag]
            else:
                params.SubfamilyNameID = 0
        elif tag in self.featureNames_:
            if not self.featureNames_ids_:
                # name table wasn't selected among the tables to build; skip
                pass
            else:
                assert tag in self.featureNames_ids_
                params = otTables.FeatureParamsStylisticSet()
                params.Version = 0
                params.UINameID = self.featureNames_ids_[tag]
        elif tag in self.cv_parameters_:
            params = otTables.FeatureParamsCharacterVariants()
            params.Format = 0
            params.FeatUILabelNameID = self.cv_parameters_ids_.get(
                (tag, "FeatUILabelNameID"), 0
            )
            params.FeatUITooltipTextNameID = self.cv_parameters_ids_.get(
                (tag, "FeatUITooltipTextNameID"), 0
            )
            params.SampleTextNameID = self.cv_parameters_ids_.get(
                (tag, "SampleTextNameID"), 0
            )
            params.NumNamedParameters = self.cv_num_named_params_.get(tag, 0)
            params.FirstParamUILabelNameID = self.cv_parameters_ids_.get(
                (tag, "ParamUILabelNameID_0"), 0
            )
            params.CharCount = len(self.cv_characters_[tag])
            params.Character = self.cv_characters_[tag]
        return params

    def build_name(self):
        if not self.names_:
            return
        table = self.font.get("name")
        if not table:  # this only happens for unit tests
            table = self.font["name"] = newTable("name")
            table.names = []
        for name in self.names_:
            nameID, platformID, platEncID, langID, string = name
            # For featureNames block, nameID is 'feature tag'
            # For cvParameters blocks, nameID is ('feature tag', 'block name')
            if not isinstance(nameID, int):
                tag = nameID
                if tag in self.featureNames_:
                    if tag not in self.featureNames_ids_:
                        self.featureNames_ids_[tag] = self.get_user_name_id(table)
                        assert self.featureNames_ids_[tag] is not None
                    nameID = self.featureNames_ids_[tag]
                elif tag[0] in self.cv_parameters_:
                    if tag not in self.cv_parameters_ids_:
                        self.cv_parameters_ids_[tag] = self.get_user_name_id(table)
                        assert self.cv_parameters_ids_[tag] is not None
                    nameID = self.cv_parameters_ids_[tag]
            table.setName(string, nameID, platformID, platEncID, langID)
        table.names.sort()

    def build_OS_2(self):
        if not self.os2_:
            return
        table = self.font.get("OS/2")
        if not table:  # this only happens for unit tests
            table = self.font["OS/2"] = newTable("OS/2")
            data = b"\0" * sstruct.calcsize(getTableModule("OS/2").OS2_format_0)
            table.decompile(data, self.font)
        version = 0
        if "fstype" in self.os2_:
            table.fsType = self.os2_["fstype"]
        if "panose" in self.os2_:
            panose = getTableModule("OS/2").Panose()
            (
                panose.bFamilyType,
                panose.bSerifStyle,
                panose.bWeight,
                panose.bProportion,
                panose.bContrast,
                panose.bStrokeVariation,
                panose.bArmStyle,
                panose.bLetterForm,
                panose.bMidline,
                panose.bXHeight,
            ) = self.os2_["panose"]
            table.panose = panose
        if "typoascender" in self.os2_:
            table.sTypoAscender = self.os2_["typoascender"]
        if "typodescender" in self.os2_:
            table.sTypoDescender = self.os2_["typodescender"]
        if "typolinegap" in self.os2_:
            table.sTypoLineGap = self.os2_["typolinegap"]
        if "winascent" in self.os2_:
            table.usWinAscent = self.os2_["winascent"]
        if "windescent" in self.os2_:
            table.usWinDescent = self.os2_["windescent"]
        if "vendor" in self.os2_:
            table.achVendID = safeEval("'''" + self.os2_["vendor"] + "'''")
        if "weightclass" in self.os2_:
            table.usWeightClass = self.os2_["weightclass"]
        if "widthclass" in self.os2_:
            table.usWidthClass = self.os2_["widthclass"]
        if "unicoderange" in self.os2_:
            table.setUnicodeRanges(self.os2_["unicoderange"])
        if "codepagerange" in self.os2_:
            pages = self.build_codepages_(self.os2_["codepagerange"])
            table.ulCodePageRange1, table.ulCodePageRange2 = pages
            version = 1
        if "xheight" in self.os2_:
            table.sxHeight = self.os2_["xheight"]
            version = 2
        if "capheight" in self.os2_:
            table.sCapHeight = self.os2_["capheight"]
            version = 2
        if "loweropsize" in self.os2_:
            table.usLowerOpticalPointSize = self.os2_["loweropsize"]
            version = 5
        if "upperopsize" in self.os2_:
            table.usUpperOpticalPointSize = self.os2_["upperopsize"]
            version = 5

        def checkattr(table, attrs):
            for attr in attrs:
                if not hasattr(table, attr):
                    setattr(table, attr, 0)

        table.version = max(version, table.version)
        # this only happens for unit tests
        if version >= 1:
            checkattr(table, ("ulCodePageRange1", "ulCodePageRange2"))
        if version >= 2:
            checkattr(
                table,
                (
                    "sxHeight",
                    "sCapHeight",
                    "usDefaultChar",
                    "usBreakChar",
                    "usMaxContext",
                ),
            )
        if version >= 5:
            checkattr(table, ("usLowerOpticalPointSize", "usUpperOpticalPointSize"))

    def setElidedFallbackName(self, value, location):
        # ElidedFallbackName is a convenience method for setting
        # ElidedFallbackNameID so only one can be allowed
        for token in ("ElidedFallbackName", "ElidedFallbackNameID"):
            if token in self.stat_:
                raise FeatureLibError(
                    f"{token} is already set.",
                    location,
                )
        if isinstance(value, int):
            self.stat_["ElidedFallbackNameID"] = value
        elif isinstance(value, list):
            self.stat_["ElidedFallbackName"] = value
        else:
            raise AssertionError(value)

    def addDesignAxis(self, designAxis, location):
        if "DesignAxes" not in self.stat_:
            self.stat_["DesignAxes"] = []
        if designAxis.tag in (r.tag for r in self.stat_["DesignAxes"]):
            raise FeatureLibError(
                f'DesignAxis already defined for tag "{designAxis.tag}".',
                location,
            )
        if designAxis.axisOrder in (r.axisOrder for r in self.stat_["DesignAxes"]):
            raise FeatureLibError(
                f"DesignAxis already defined for axis number {designAxis.axisOrder}.",
                location,
            )
        self.stat_["DesignAxes"].append(designAxis)

    def addAxisValueRecord(self, axisValueRecord, location):
        if "AxisValueRecords" not in self.stat_:
            self.stat_["AxisValueRecords"] = []
        # Check for duplicate AxisValueRecords
        for record_ in self.stat_["AxisValueRecords"]:
            if (
                {n.asFea() for n in record_.names}
                == {n.asFea() for n in axisValueRecord.names}
                and {n.asFea() for n in record_.locations}
                == {n.asFea() for n in axisValueRecord.locations}
                and record_.flags == axisValueRecord.flags
            ):
                raise FeatureLibError(
                    "An AxisValueRecord with these values is already defined.",
                    location,
                )
        self.stat_["AxisValueRecords"].append(axisValueRecord)

    def build_STAT(self):
        if not self.stat_:
            return

        axes = self.stat_.get("DesignAxes")
        if not axes:
            raise FeatureLibError("DesignAxes not defined", None)
        axisValueRecords = self.stat_.get("AxisValueRecords")
        axisValues = {}
        format4_locations = []
        for tag in axes:
            axisValues[tag.tag] = []
        if axisValueRecords is not None:
            for avr in axisValueRecords:
                valuesDict = {}
                if avr.flags > 0:
                    valuesDict["flags"] = avr.flags
                if len(avr.locations) == 1:
                    location = avr.locations[0]
                    values = location.values
                    if len(values) == 1:  # format1
                        valuesDict.update({"value": values[0], "name": avr.names})
                    if len(values) == 2:  # format3
                        valuesDict.update(
                            {
                                "value": values[0],
                                "linkedValue": values[1],
                                "name": avr.names,
                            }
                        )
                    if len(values) == 3:  # format2
                        nominal, minVal, maxVal = values
                        valuesDict.update(
                            {
                                "nominalValue": nominal,
                                "rangeMinValue": minVal,
                                "rangeMaxValue": maxVal,
                                "name": avr.names,
                            }
                        )
                    axisValues[location.tag].append(valuesDict)
                else:
                    valuesDict.update(
                        {
                            "location": {i.tag: i.values[0] for i in avr.locations},
                            "name": avr.names,
                        }
                    )
                    format4_locations.append(valuesDict)

        designAxes = [
            {
                "ordering": a.axisOrder,
                "tag": a.tag,
                "name": a.names,
                "values": axisValues[a.tag],
            }
            for a in axes
        ]

        nameTable = self.font.get("name")
        if not nameTable:  # this only happens for unit tests
            nameTable = self.font["name"] = newTable("name")
            nameTable.names = []

        if "ElidedFallbackNameID" in self.stat_:
            nameID = self.stat_["ElidedFallbackNameID"]
            name = nameTable.getDebugName(nameID)
            if not name:
                raise FeatureLibError(
                    f"ElidedFallbackNameID {nameID} points "
                    "to a nameID that does not exist in the "
                    '"name" table',
                    None,
                )
        elif "ElidedFallbackName" in self.stat_:
            nameID = self.stat_["ElidedFallbackName"]

        otl.buildStatTable(
            self.font,
            designAxes,
            locations=format4_locations,
            elidedFallbackName=nameID,
        )

    def build_codepages_(self, pages):
        pages2bits = {
            1252: 0,
            1250: 1,
            1251: 2,
            1253: 3,
            1254: 4,
            1255: 5,
            1256: 6,
            1257: 7,
            1258: 8,
            874: 16,
            932: 17,
            936: 18,
            949: 19,
            950: 20,
            1361: 21,
            869: 48,
            866: 49,
            865: 50,
            864: 51,
            863: 52,
            862: 53,
            861: 54,
            860: 55,
            857: 56,
            855: 57,
            852: 58,
            775: 59,
            737: 60,
            708: 61,
            850: 62,
            437: 63,
        }
        bits = [pages2bits[p] for p in pages if p in pages2bits]
        pages = []
        for i in range(2):
            pages.append("")
            for j in range(i * 32, (i + 1) * 32):
                if j in bits:
                    pages[i] += "1"
                else:
                    pages[i] += "0"
        return [binary2num(p[::-1]) for p in pages]

    def buildBASE(self):
        if not self.base_horiz_axis_ and not self.base_vert_axis_:
            return None
        base = otTables.BASE()
        base.Version = 0x00010000
        base.HorizAxis = self.buildBASEAxis(self.base_horiz_axis_)
        base.VertAxis = self.buildBASEAxis(self.base_vert_axis_)

        result = newTable("BASE")
        result.table = base
        return result

    def buildBASECoord(self, c):
        coord = otTables.BaseCoord()
        coord.Format = 1
        coord.Coordinate = c
        return coord

    def buildBASEAxis(self, axis):
        if not axis:
            return
        bases, scripts, minmax = axis
        axis = otTables.Axis()
        axis.BaseTagList = otTables.BaseTagList()
        axis.BaseTagList.BaselineTag = bases
        axis.BaseTagList.BaseTagCount = len(bases)
        axis.BaseScriptList = otTables.BaseScriptList()
        axis.BaseScriptList.BaseScriptRecord = []
        axis.BaseScriptList.BaseScriptCount = len(scripts)
        for script in sorted(scripts):
            minmax_for_script = [
                record[1:] for record in minmax if record[0] == script[0]
            ]
            record = otTables.BaseScriptRecord()
            record.BaseScriptTag = script[0]
            record.BaseScript = otTables.BaseScript()
            record.BaseScript.BaseValues = otTables.BaseValues()
            record.BaseScript.BaseValues.DefaultIndex = bases.index(script[1])
            record.BaseScript.BaseValues.BaseCoord = []
            record.BaseScript.BaseValues.BaseCoordCount = len(script[2])
            record.BaseScript.BaseLangSysRecord = []

            for c in script[2]:
                record.BaseScript.BaseValues.BaseCoord.append(self.buildBASECoord(c))
            for language, min_coord, max_coord in minmax_for_script:
                minmax_record = otTables.MinMax()
                minmax_record.MinCoord = self.buildBASECoord(min_coord)
                minmax_record.MaxCoord = self.buildBASECoord(max_coord)
                minmax_record.FeatMinMaxCount = 0
                if language == "dflt":
                    record.BaseScript.DefaultMinMax = minmax_record
                else:
                    lang_record = otTables.BaseLangSysRecord()
                    lang_record.BaseLangSysTag = language
                    lang_record.MinMax = minmax_record
                    record.BaseScript.BaseLangSysRecord.append(lang_record)
            record.BaseScript.BaseLangSysCount = len(
                record.BaseScript.BaseLangSysRecord
            )
            axis.BaseScriptList.BaseScriptRecord.append(record)
        return axis

    def buildGDEF(self):
        gdef = otTables.GDEF()
        gdef.GlyphClassDef = self.buildGDEFGlyphClassDef_()
        gdef.AttachList = otl.buildAttachList(self.attachPoints_, self.glyphMap)
        gdef.LigCaretList = otl.buildLigCaretList(
            self.ligCaretCoords_, self.ligCaretPoints_, self.glyphMap
        )
        gdef.MarkAttachClassDef = self.buildGDEFMarkAttachClassDef_()
        gdef.MarkGlyphSetsDef = self.buildGDEFMarkGlyphSetsDef_()
        gdef.Version = 0x00010002 if gdef.MarkGlyphSetsDef else 0x00010000
        if self.varstorebuilder:
            store = self.varstorebuilder.finish()
            if store:
                gdef.Version = 0x00010003
                gdef.VarStore = store
                varidx_map = store.optimize()

                gdef.remap_device_varidxes(varidx_map)
                if "GPOS" in self.font:
                    self.font["GPOS"].table.remap_device_varidxes(varidx_map)
            self.model_cache.clear()
        if any(
            (
                gdef.GlyphClassDef,
                gdef.AttachList,
                gdef.LigCaretList,
                gdef.MarkAttachClassDef,
                gdef.MarkGlyphSetsDef,
            )
        ) or hasattr(gdef, "VarStore"):
            result = newTable("GDEF")
            result.table = gdef
            return result
        else:
            return None

    def buildGDEFGlyphClassDef_(self):
        if self.glyphClassDefs_:
            classes = {g: c for (g, (c, _)) in self.glyphClassDefs_.items()}
        else:
            classes = {}
            for lookup in self.lookups_:
                classes.update(lookup.inferGlyphClasses())
            for markClass in self.parseTree.markClasses.values():
                for markClassDef in markClass.definitions:
                    for glyph in markClassDef.glyphSet():
                        classes[glyph] = 3
        if classes:
            result = otTables.GlyphClassDef()
            result.classDefs = classes
            return result
        else:
            return None

    def buildGDEFMarkAttachClassDef_(self):
        classDefs = {g: c for g, (c, _) in self.markAttach_.items()}
        if not classDefs:
            return None
        result = otTables.MarkAttachClassDef()
        result.classDefs = classDefs
        return result

    def buildGDEFMarkGlyphSetsDef_(self):
        sets = []
        for glyphs, id_ in sorted(
            self.markFilterSets_.items(), key=lambda item: item[1]
        ):
            sets.append(glyphs)
        return otl.buildMarkGlyphSetsDef(sets, self.glyphMap)

    def buildDebg(self):
        if "Debg" not in self.font:
            self.font["Debg"] = newTable("Debg")
            self.font["Debg"].data = {}
        self.font["Debg"].data[LOOKUP_DEBUG_INFO_KEY] = self.lookup_locations

    def buildLookups_(self, tag):
        assert tag in ("GPOS", "GSUB"), tag
        for lookup in self.lookups_:
            lookup.lookup_index = None
        lookups = []
        for lookup in self.lookups_:
            if lookup.table != tag:
                continue
            name = self.get_lookup_name_(lookup)
            resolved = lookup.promote_lookup_type(is_named_lookup=name is not None)
            if resolved is None:
                raise FeatureLibError(
                    "Within a named lookup block, all rules must be of "
                    "the same lookup type and flag",
                    lookup.location,
                )
            for l in resolved:
                lookup.lookup_index = len(lookups)
                self.lookup_locations[tag][str(lookup.lookup_index)] = LookupDebugInfo(
                    location=str(lookup.location),
                    name=name,
                    feature=None,
                )
                lookups.append(l)
        otLookups = []
        for l in lookups:
            try:
                otLookups.append(l.build())
            except OpenTypeLibError as e:
                raise FeatureLibError(str(e), e.location) from e
            except Exception as e:
                location = self.lookup_locations[tag][str(l.lookup_index)].location
                raise FeatureLibError(str(e), location) from e
        return otLookups

    def makeTable(self, tag):
        table = getattr(otTables, tag, None)()
        table.Version = 0x00010000
        table.ScriptList = otTables.ScriptList()
        table.ScriptList.ScriptRecord = []
        table.FeatureList = otTables.FeatureList()
        table.FeatureList.FeatureRecord = []
        table.LookupList = otTables.LookupList()
        table.LookupList.Lookup = self.buildLookups_(tag)

        # Build a table for mapping (tag, lookup_indices) to feature_index.
        # For example, ('liga', (2,3,7)) --> 23.
        feature_indices = {}
        required_feature_indices = {}  # ('latn', 'DEU') --> 23
        scripts = {}  # 'latn' --> {'DEU': [23, 24]} for feature #23,24
        # Sort the feature table by feature tag:
        # https://github.com/fonttools/fonttools/issues/568
        sortFeatureTag = lambda f: (f[0][2], f[0][1], f[0][0], f[1])
        for key, lookups in sorted(self.features_.items(), key=sortFeatureTag):
            script, lang, feature_tag = key
            # l.lookup_index will be None when a lookup is not needed
            # for the table under construction. For example, substitution
            # rules will have no lookup_index while building GPOS tables.
            # We also deduplicate lookup indices, as they only get applied once
            # within a given feature:
            # https://github.com/fonttools/fonttools/issues/2946
            lookup_indices = tuple(
                dict.fromkeys(
                    l.lookup_index for l in lookups if l.lookup_index is not None
                )
            )

            size_feature = tag == "GPOS" and feature_tag == "size"
            force_feature = self.any_feature_variations(feature_tag, tag)
            if len(lookup_indices) == 0 and not size_feature and not force_feature:
                continue

            for ix in lookup_indices:
                try:
                    self.lookup_locations[tag][str(ix)] = self.lookup_locations[tag][
                        str(ix)
                    ]._replace(feature=key)
                except KeyError:
                    warnings.warn(
                        "feaLib.Builder subclass needs upgrading to "
                        "stash debug information. See fonttools#2065."
                    )

            feature_key = (feature_tag, lookup_indices)
            feature_index = feature_indices.get(feature_key)
            if feature_index is None:
                feature_index = len(table.FeatureList.FeatureRecord)
                frec = otTables.FeatureRecord()
                frec.FeatureTag = feature_tag
                frec.Feature = otTables.Feature()
                frec.Feature.FeatureParams = self.buildFeatureParams(feature_tag)
                frec.Feature.LookupListIndex = list(lookup_indices)
                frec.Feature.LookupCount = len(lookup_indices)
                table.FeatureList.FeatureRecord.append(frec)
                feature_indices[feature_key] = feature_index
            scripts.setdefault(script, {}).setdefault(lang, []).append(feature_index)
            if self.required_features_.get((script, lang)) == feature_tag:
                required_feature_indices[(script, lang)] = feature_index

        # Build ScriptList.
        for script, lang_features in sorted(scripts.items()):
            srec = otTables.ScriptRecord()
            srec.ScriptTag = script
            srec.Script = otTables.Script()
            srec.Script.DefaultLangSys = None
            srec.Script.LangSysRecord = []
            for lang, feature_indices in sorted(lang_features.items()):
                langrec = otTables.LangSysRecord()
                langrec.LangSys = otTables.LangSys()
                langrec.LangSys.LookupOrder = None

                req_feature_index = required_feature_indices.get((script, lang))
                if req_feature_index is None:
                    langrec.LangSys.ReqFeatureIndex = 0xFFFF
                else:
                    langrec.LangSys.ReqFeatureIndex = req_feature_index

                langrec.LangSys.FeatureIndex = [
                    i for i in feature_indices if i != req_feature_index
                ]
                langrec.LangSys.FeatureCount = len(langrec.LangSys.FeatureIndex)

                if lang == "dflt":
                    srec.Script.DefaultLangSys = langrec.LangSys
                else:
                    langrec.LangSysTag = lang
                    srec.Script.LangSysRecord.append(langrec)
            srec.Script.LangSysCount = len(srec.Script.LangSysRecord)
            table.ScriptList.ScriptRecord.append(srec)

        table.ScriptList.ScriptCount = len(table.ScriptList.ScriptRecord)
        table.FeatureList.FeatureCount = len(table.FeatureList.FeatureRecord)
        table.LookupList.LookupCount = len(table.LookupList.Lookup)
        return table

    def makeFeatureVariations(self, table, table_tag):
        feature_vars = {}
        has_any_variations = False
        # Sort out which lookups to build, gather their indices
        for (_, _, feature_tag), variations in self.feature_variations_.items():
            feature_vars[feature_tag] = []
            for conditionset, builders in variations.items():
                raw_conditionset = self.conditionsets_[conditionset]
                indices = []
                for b in builders:
                    if b.table != table_tag:
                        continue
                    assert b.lookup_index is not None
                    indices.append(b.lookup_index)
                    has_any_variations = True
                feature_vars[feature_tag].append((raw_conditionset, indices))

        if has_any_variations:
            for feature_tag, conditions_and_lookups in feature_vars.items():
                addFeatureVariationsRaw(
                    self.font, table, conditions_and_lookups, feature_tag
                )

    def any_feature_variations(self, feature_tag, table_tag):
        for (_, _, feature), variations in self.feature_variations_.items():
            if feature != feature_tag:
                continue
            for conditionset, builders in variations.items():
                if any(b.table == table_tag for b in builders):
                    return True
        return False

    def get_lookup_name_(self, lookup):
        rev = {v: k for k, v in self.named_lookups_.items()}
        if lookup in rev:
            return rev[lookup]
        return None

    def add_language_system(self, location, script, language):
        # OpenType Feature File Specification, section 4.b.i
        if script == "DFLT" and language == "dflt" and self.default_language_systems_:
            raise FeatureLibError(
                'If "languagesystem DFLT dflt" is present, it must be '
                "the first of the languagesystem statements",
                location,
            )
        if script == "DFLT":
            if self.seen_non_DFLT_script_:
                raise FeatureLibError(
                    'languagesystems using the "DFLT" script tag must '
                    "precede all other languagesystems",
                    location,
                )
        else:
            self.seen_non_DFLT_script_ = True
        if (script, language) in self.default_language_systems_:
            raise FeatureLibError(
                '"languagesystem %s %s" has already been specified'
                % (script.strip(), language.strip()),
                location,
            )
        self.default_language_systems_.add((script, language))

    def get_default_language_systems_(self):
        # OpenType Feature File specification, 4.b.i. languagesystem:
        # If no "languagesystem" statement is present, then the
        # implementation must behave exactly as though the following
        # statement were present at the beginning of the feature file:
        # languagesystem DFLT dflt;
        if self.default_language_systems_:
            return frozenset(self.default_language_systems_)
        else:
            return frozenset({("DFLT", "dflt")})

    def start_feature(self, location, name, use_extension=False):
        if use_extension and name != "aalt":
            raise FeatureLibError(
                "'useExtension' keyword for feature blocks is allowed only for 'aalt' feature",
                location,
            )
        self.language_systems = self.get_default_language_systems_()
        self.script_ = "DFLT"
        self.cur_lookup_ = None
        self.cur_feature_name_ = name
        self.lookupflag_ = 0
        self.lookupflag_markFilterSet_ = None
        self.use_extension_ = use_extension
        if name == "aalt":
            self.aalt_location_ = location
            self.aalt_use_extension_ = use_extension

    def end_feature(self):
        assert self.cur_feature_name_ is not None
        self.cur_feature_name_ = None
        self.language_systems = None
        self.cur_lookup_ = None
        self.lookupflag_ = 0
        self.lookupflag_markFilterSet_ = None
        self.use_extension_ = False

    def start_lookup_block(self, location, name, use_extension=False):
        if name in self.named_lookups_:
            raise FeatureLibError(
                'Lookup "%s" has already been defined' % name, location
            )
        if self.cur_feature_name_ == "aalt":
            raise FeatureLibError(
                "Lookup blocks cannot be placed inside 'aalt' features; "
                "move it out, and then refer to it with a lookup statement",
                location,
            )
        self.cur_lookup_name_ = name
        self.named_lookups_[name] = None
        self.cur_lookup_ = None
        self.use_extension_ = use_extension
        if self.cur_feature_name_ is None:
            self.lookupflag_ = 0
            self.lookupflag_markFilterSet_ = None

    def end_lookup_block(self):
        assert self.cur_lookup_name_ is not None
        self.cur_lookup_name_ = None
        self.cur_lookup_ = None
        self.use_extension_ = False
        if self.cur_feature_name_ is None:
            self.lookupflag_ = 0
            self.lookupflag_markFilterSet_ = None

    def add_lookup_call(self, lookup_name):
        assert lookup_name in self.named_lookups_, lookup_name
        self.cur_lookup_ = None
        lookup = self.named_lookups_[lookup_name]
        if lookup is not None:  # skip empty named lookup
            self.add_lookup_to_feature_(lookup, self.cur_feature_name_)

    def set_font_revision(self, location, revision):
        self.fontRevision_ = revision

    def set_language(self, location, language, include_default, required):
        assert len(language) == 4
        if self.cur_feature_name_ in ("aalt", "size"):
            raise FeatureLibError(
                "Language statements are not allowed "
                'within "feature %s"' % self.cur_feature_name_,
                location,
            )
        if self.cur_feature_name_ is None:
            raise FeatureLibError(
                "Language statements are not allowed "
                "within standalone lookup blocks",
                location,
            )
        self.cur_lookup_ = None

        key = (self.script_, language, self.cur_feature_name_)
        lookups = self.features_.get((key[0], "dflt", key[2]))
        if (language == "dflt" or include_default) and lookups:
            self.features_[key] = lookups[:]
        else:
            # if we aren't including default we need to manually remove the
            # default lookups, which were added to all declared langsystems
            # as they were encountered (we don't remove all lookups because
            # we want to allow duplicate script/lang statements;
            # see https://github.com/fonttools/fonttools/issues/3748
            cur_lookups = self.features_.get(key, [])
            self.features_[key] = [x for x in cur_lookups if x not in lookups]
        self.language_systems = frozenset([(self.script_, language)])

        if required:
            key = (self.script_, language)
            if key in self.required_features_:
                raise FeatureLibError(
                    "Language %s (script %s) has already "
                    "specified feature %s as its required feature"
                    % (
                        language.strip(),
                        self.script_.strip(),
                        self.required_features_[key].strip(),
                    ),
                    location,
                )
            self.required_features_[key] = self.cur_feature_name_

    def getMarkAttachClass_(self, location, glyphs):
        glyphs = frozenset(glyphs)
        id_ = self.markAttachClassID_.get(glyphs)
        if id_ is not None:
            return id_
        id_ = len(self.markAttachClassID_) + 1
        self.markAttachClassID_[glyphs] = id_
        for glyph in glyphs:
            if glyph in self.markAttach_:
                _, loc = self.markAttach_[glyph]
                raise FeatureLibError(
                    "Glyph %s already has been assigned "
                    "a MarkAttachmentType at %s" % (glyph, loc),
                    location,
                )
            self.markAttach_[glyph] = (id_, location)
        return id_

    def getMarkFilterSet_(self, location, glyphs):
        glyphs = frozenset(glyphs)
        id_ = self.markFilterSets_.get(glyphs)
        if id_ is not None:
            return id_
        id_ = len(self.markFilterSets_)
        self.markFilterSets_[glyphs] = id_
        return id_

    def set_lookup_flag(self, location, value, markAttach, markFilter):
        value = value & 0xFF
        if markAttach is not None:
            markAttachClass = self.getMarkAttachClass_(location, markAttach)
            value = value | (markAttachClass << 8)
        if markFilter is not None:
            markFilterSet = self.getMarkFilterSet_(location, markFilter)
            value = value | 0x10
            self.lookupflag_markFilterSet_ = markFilterSet
        else:
            self.lookupflag_markFilterSet_ = None
        self.lookupflag_ = value

    def set_script(self, location, script):
        if self.cur_feature_name_ in ("aalt", "size"):
            raise FeatureLibError(
                "Script statements are not allowed "
                'within "feature %s"' % self.cur_feature_name_,
                location,
            )
        if self.cur_feature_name_ is None:
            raise FeatureLibError(
                "Script statements are not allowed " "within standalone lookup blocks",
                location,
            )
        if self.language_systems == {(script, "dflt")}:
            # Nothing to do.
            return
        self.cur_lookup_ = None
        self.script_ = script
        self.lookupflag_ = 0
        self.lookupflag_markFilterSet_ = None
        self.set_language(location, "dflt", include_default=True, required=False)

    def find_lookup_builders_(self, lookups):
        """Helper for building chain contextual substitutions

        Given a list of lookup names, finds the LookupBuilder for each name.
        If an input name is None, it gets mapped to a None LookupBuilder.
        """
        lookup_builders = []
        for lookuplist in lookups:
            if lookuplist is not None:
                lookup_builders.append(
                    [self.named_lookups_.get(l.name) for l in lookuplist]
                )
            else:
                lookup_builders.append(None)
        return lookup_builders

    def add_attach_points(self, location, glyphs, contourPoints):
        for glyph in glyphs:
            self.attachPoints_.setdefault(glyph, set()).update(contourPoints)

    def add_feature_reference(self, location, featureName):
        if self.cur_feature_name_ != "aalt":
            raise FeatureLibError(
                'Feature references are only allowed inside "feature aalt"', location
            )
        self.aalt_features_.append((location, featureName))

    def add_featureName(self, tag):
        self.featureNames_.add(tag)

    def add_cv_parameter(self, tag):
        self.cv_parameters_.add(tag)

    def add_to_cv_num_named_params(self, tag):
        """Adds new items to ``self.cv_num_named_params_``
        or increments the count of existing items."""
        if tag in self.cv_num_named_params_:
            self.cv_num_named_params_[tag] += 1
        else:
            self.cv_num_named_params_[tag] = 1

    def add_cv_character(self, character, tag):
        self.cv_characters_[tag].append(character)

    def set_base_axis(self, bases, scripts, vertical, minmax=[]):
        if vertical:
            self.base_vert_axis_ = (bases, scripts, minmax)
        else:
            self.base_horiz_axis_ = (bases, scripts, minmax)

    def set_size_parameters(
        self, location, DesignSize, SubfamilyID, RangeStart, RangeEnd
    ):
        if self.cur_feature_name_ != "size":
            raise FeatureLibError(
                "Parameters statements are not allowed "
                'within "feature %s"' % self.cur_feature_name_,
                location,
            )
        self.size_parameters_ = [DesignSize, SubfamilyID, RangeStart, RangeEnd]
        for script, lang in self.language_systems:
            key = (script, lang, self.cur_feature_name_)
            self.features_.setdefault(key, [])

    # GSUB rules

    def add_any_subst_(self, location, mapping):
        lookup = self.get_lookup_(location, AnySubstBuilder)
        for key, value in mapping.items():
            if key in lookup.mapping:
                if value == lookup.mapping[key]:
                    log.info(
                        'Removing duplicate substitution from "%s" to "%s" at %s',
                        ", ".join(key),
                        ", ".join(value),
                        location,
                    )
                else:
                    raise FeatureLibError(
                        'Already defined substitution for "%s"' % ", ".join(key),
                        location,
                    )
            lookup.mapping[key] = value

    # GSUB 1
    def add_single_subst(self, location, prefix, suffix, mapping, forceChain):
        if self.cur_feature_name_ == "aalt":
            for from_glyph, to_glyph in mapping.items():
                alts = self.aalt_alternates_.setdefault(from_glyph, [])
                if to_glyph not in alts:
                    alts.append(to_glyph)
            return
        if prefix or suffix or forceChain:
            self.add_single_subst_chained_(location, prefix, suffix, mapping)
            return

        self.add_any_subst_(
            location,
            {(key,): (value,) for key, value in mapping.items()},
        )

    # GSUB 2
    def add_multiple_subst(
        self, location, prefix, glyph, suffix, replacements, forceChain=False
    ):
        if prefix or suffix or forceChain:
            self.add_multi_subst_chained_(location, prefix, glyph, suffix, replacements)
            return
        self.add_any_subst_(
            location,
            {(glyph,): tuple(replacements)},
        )

    # GSUB 3
    def add_alternate_subst(self, location, prefix, glyph, suffix, replacement):
        if self.cur_feature_name_ == "aalt":
            alts = self.aalt_alternates_.setdefault(glyph, [])
            alts.extend(g for g in replacement if g not in alts)
            return
        if prefix or suffix:
            chain = self.get_lookup_(location, ChainContextSubstBuilder)
            lookup = self.get_chained_lookup_(location, AlternateSubstBuilder)
            chain.rules.append(ChainContextualRule(prefix, [{glyph}], suffix, [lookup]))
        else:
            lookup = self.get_lookup_(location, AlternateSubstBuilder)
        if glyph in lookup.alternates:
            raise FeatureLibError(
                'Already defined alternates for glyph "%s"' % glyph, location
            )
        # We allow empty replacement glyphs here.
        lookup.alternates[glyph] = replacement

    # GSUB 4
    def add_ligature_subst(
        self, location, prefix, glyphs, suffix, replacement, forceChain
    ):
        if prefix or suffix or forceChain:
            self.add_ligature_subst_chained_(
                location, prefix, glyphs, suffix, replacement
            )
            return
        if not all(glyphs):
            raise FeatureLibError("Empty glyph class in substitution", location)

        # OpenType feature file syntax, section 5.d, "Ligature substitution":
        # "Since the OpenType specification does not allow ligature
        # substitutions to be specified on target sequences that contain
        # glyph classes, the implementation software will enumerate
        # all specific glyph sequences if glyph classes are detected"
        self.add_any_subst_(
            location,
            {g: (replacement,) for g in itertools.product(*glyphs)},
        )

    # GSUB 5/6
    def add_chain_context_subst(self, location, prefix, glyphs, suffix, lookups):
        if not all(glyphs) or not all(prefix) or not all(suffix):
            raise FeatureLibError(
                "Empty glyph class in contextual substitution", location
            )
        lookup = self.get_lookup_(location, ChainContextSubstBuilder)
        lookup.rules.append(
            ChainContextualRule(
                prefix, glyphs, suffix, self.find_lookup_builders_(lookups)
            )
        )

    def add_single_subst_chained_(self, location, prefix, suffix, mapping):
        if not mapping or not all(prefix) or not all(suffix):
            raise FeatureLibError(
                "Empty glyph class in contextual substitution", location
            )
        # https://github.com/fonttools/fonttools/issues/512
        # https://github.com/fonttools/fonttools/issues/2150
        chain = self.get_lookup_(location, ChainContextSubstBuilder)
        sub = chain.find_chainable_subst(mapping, SingleSubstBuilder)
        if sub is None:
            sub = self.get_chained_lookup_(location, SingleSubstBuilder)
        sub.mapping.update(mapping)
        chain.rules.append(
            ChainContextualRule(prefix, [list(mapping.keys())], suffix, [sub])
        )

    def add_multi_subst_chained_(self, location, prefix, glyph, suffix, replacements):
        if not all(prefix) or not all(suffix):
            raise FeatureLibError(
                "Empty glyph class in contextual substitution", location
            )
        # https://github.com/fonttools/fonttools/issues/3551
        chain = self.get_lookup_(location, ChainContextSubstBuilder)
        sub = chain.find_chainable_subst({glyph: replacements}, MultipleSubstBuilder)
        if sub is None:
            sub = self.get_chained_lookup_(location, MultipleSubstBuilder)
        sub.mapping[glyph] = replacements
        chain.rules.append(ChainContextualRule(prefix, [{glyph}], suffix, [sub]))

    def add_ligature_subst_chained_(
        self, location, prefix, glyphs, suffix, replacement
    ):
        # https://github.com/fonttools/fonttools/issues/3701
        if not all(prefix) or not all(suffix):
            raise FeatureLibError(
                "Empty glyph class in contextual substitution", location
            )
        chain = self.get_lookup_(location, ChainContextSubstBuilder)
        sub = chain.find_chainable_ligature_subst(glyphs, replacement)
        if sub is None:
            sub = self.get_chained_lookup_(location, LigatureSubstBuilder)

        for g in itertools.product(*glyphs):
            existing = sub.ligatures.get(g, replacement)
            if existing != replacement:
                raise FeatureLibError(
                    f"Conflicting ligature sub rules: '{g}' maps to '{existing}' and '{replacement}'",
                    location,
                )

            sub.ligatures[g] = replacement

        chain.rules.append(ChainContextualRule(prefix, glyphs, suffix, [sub]))

    # GSUB 8
    def add_reverse_chain_single_subst(self, location, old_prefix, old_suffix, mapping):
        if not mapping:
            raise FeatureLibError("Empty glyph class in substitution", location)
        lookup = self.get_lookup_(location, ReverseChainSingleSubstBuilder)
        lookup.rules.append((old_prefix, old_suffix, mapping))

    # GPOS rules

    # GPOS 1
    def add_single_pos(self, location, prefix, suffix, pos, forceChain):
        if prefix or suffix or forceChain:
            self.add_single_pos_chained_(location, prefix, suffix, pos)
        else:
            lookup = self.get_lookup_(location, SinglePosBuilder)
            for glyphs, value in pos:
                if not glyphs:
                    raise FeatureLibError(
                        "Empty glyph class in positioning rule", location
                    )
                otValueRecord = self.makeOpenTypeValueRecord(
                    location, value, pairPosContext=False
                )
                for glyph in glyphs:
                    try:
                        lookup.add_pos(location, glyph, otValueRecord)
                    except OpenTypeLibError as e:
                        raise FeatureLibError(str(e), e.location) from e

    # GPOS 2
    def add_class_pair_pos(self, location, glyphclass1, value1, glyphclass2, value2):
        if not glyphclass1 or not glyphclass2:
            raise FeatureLibError("Empty glyph class in positioning rule", location)
        lookup = self.get_lookup_(location, PairPosBuilder)
        v1 = self.makeOpenTypeValueRecord(location, value1, pairPosContext=True)
        v2 = self.makeOpenTypeValueRecord(location, value2, pairPosContext=True)
        cls1 = tuple(sorted(set(glyphclass1)))
        cls2 = tuple(sorted(set(glyphclass2)))
        lookup.addClassPair(location, cls1, v1, cls2, v2)

    def add_specific_pair_pos(self, location, glyph1, value1, glyph2, value2):
        if not glyph1 or not glyph2:
            raise FeatureLibError("Empty glyph class in positioning rule", location)
        lookup = self.get_lookup_(location, PairPosBuilder)
        v1 = self.makeOpenTypeValueRecord(location, value1, pairPosContext=True)
        v2 = self.makeOpenTypeValueRecord(location, value2, pairPosContext=True)
        lookup.addGlyphPair(location, glyph1, v1, glyph2, v2)

    # GPOS 3
    def add_cursive_pos(self, location, glyphclass, entryAnchor, exitAnchor):
        if not glyphclass:
            raise FeatureLibError("Empty glyph class in positioning rule", location)
        lookup = self.get_lookup_(location, CursivePosBuilder)
        lookup.add_attachment(
            location,
            glyphclass,
            self.makeOpenTypeAnchor(location, entryAnchor),
            self.makeOpenTypeAnchor(location, exitAnchor),
        )

    # GPOS 4
    def add_mark_base_pos(self, location, bases, marks):
        builder = self.get_lookup_(location, MarkBasePosBuilder)
        self.add_marks_(location, builder, marks)
        if not bases:
            raise FeatureLibError("Empty glyph class in positioning rule", location)
        for baseAnchor, markClass in marks:
            otBaseAnchor = self.makeOpenTypeAnchor(location, baseAnchor)
            for base in bases:
                builder.bases.setdefault(base, {})[markClass.name] = otBaseAnchor

    # GPOS 5
    def add_mark_lig_pos(self, location, ligatures, components):
        builder = self.get_lookup_(location, MarkLigPosBuilder)
        componentAnchors = []
        if not ligatures:
            raise FeatureLibError("Empty glyph class in positioning rule", location)
        for marks in components:
            anchors = {}
            self.add_marks_(location, builder, marks)
            for ligAnchor, markClass in marks:
                anchors[markClass.name] = self.makeOpenTypeAnchor(location, ligAnchor)
            componentAnchors.append(anchors)
        for glyph in ligatures:
            builder.ligatures[glyph] = componentAnchors

    # GPOS 6
    def add_mark_mark_pos(self, location, baseMarks, marks):
        builder = self.get_lookup_(location, MarkMarkPosBuilder)
        self.add_marks_(location, builder, marks)
        if not baseMarks:
            raise FeatureLibError("Empty glyph class in positioning rule", location)
        for baseAnchor, markClass in marks:
            otBaseAnchor = self.makeOpenTypeAnchor(location, baseAnchor)
            for baseMark in baseMarks:
                builder.baseMarks.setdefault(baseMark, {})[
                    markClass.name
                ] = otBaseAnchor

    # GPOS 7/8
    def add_chain_context_pos(self, location, prefix, glyphs, suffix, lookups):
        if not all(glyphs) or not all(prefix) or not all(suffix):
            raise FeatureLibError(
                "Empty glyph class in contextual positioning rule", location
            )
        lookup = self.get_lookup_(location, ChainContextPosBuilder)
        lookup.rules.append(
            ChainContextualRule(
                prefix, glyphs, suffix, self.find_lookup_builders_(lookups)
            )
        )

    def add_single_pos_chained_(self, location, prefix, suffix, pos):
        if not pos or not all(prefix) or not all(suffix):
            raise FeatureLibError(
                "Empty glyph class in contextual positioning rule", location
            )
        # https://github.com/fonttools/fonttools/issues/514
        chain = self.get_lookup_(location, ChainContextPosBuilder)
        targets = []
        for _, _, _, lookups in chain.rules:
            targets.extend(lookups)
        subs = []
        for glyphs, value in pos:
            if value is None:
                subs.append(None)
                continue
            otValue = self.makeOpenTypeValueRecord(
                location, value, pairPosContext=False
            )
            sub = chain.find_chainable_single_pos(targets, glyphs, otValue)
            if sub is None:
                sub = self.get_chained_lookup_(location, SinglePosBuilder)
                targets.append(sub)
            for glyph in glyphs:
                sub.add_pos(location, glyph, otValue)
            subs.append(sub)
        assert len(pos) == len(subs), (pos, subs)
        chain.rules.append(
            ChainContextualRule(prefix, [g for g, v in pos], suffix, subs)
        )

    def add_marks_(self, location, lookupBuilder, marks):
        """Helper for add_mark_{base,liga,mark}_pos."""
        for _, markClass in marks:
            for markClassDef in markClass.definitions:
                for mark in markClassDef.glyphs.glyphSet():
                    if mark not in lookupBuilder.marks:
                        otMarkAnchor = self.makeOpenTypeAnchor(
                            location, copy.deepcopy(markClassDef.anchor)
                        )
                        lookupBuilder.marks[mark] = (markClass.name, otMarkAnchor)
                    else:
                        existingMarkClass = lookupBuilder.marks[mark][0]
                        if markClass.name != existingMarkClass:
                            raise FeatureLibError(
                                "Glyph %s cannot be in both @%s and @%s"
                                % (mark, existingMarkClass, markClass.name),
                                location,
                            )

    def add_subtable_break(self, location):
        self.cur_lookup_.add_subtable_break(location)

    def setGlyphClass_(self, location, glyph, glyphClass):
        oldClass, oldLocation = self.glyphClassDefs_.get(glyph, (None, None))
        if oldClass and oldClass != glyphClass:
            raise FeatureLibError(
                "Glyph %s was assigned to a different class at %s"
                % (glyph, oldLocation),
                location,
            )
        self.glyphClassDefs_[glyph] = (glyphClass, location)

    def add_glyphClassDef(
        self, location, baseGlyphs, ligatureGlyphs, markGlyphs, componentGlyphs
    ):
        for glyph in baseGlyphs:
            self.setGlyphClass_(location, glyph, 1)
        for glyph in ligatureGlyphs:
            self.setGlyphClass_(location, glyph, 2)
        for glyph in markGlyphs:
            self.setGlyphClass_(location, glyph, 3)
        for glyph in componentGlyphs:
            self.setGlyphClass_(location, glyph, 4)

    def add_ligatureCaretByIndex_(self, location, glyphs, carets):
        for glyph in glyphs:
            if glyph not in self.ligCaretPoints_:
                self.ligCaretPoints_[glyph] = carets

    def makeLigCaret(self, location, caret):
        if not isinstance(caret, VariableScalar):
            return caret
        default, device = self.makeVariablePos(location, caret)
        if device is not None:
            return (default, device)
        return default

    def add_ligatureCaretByPos_(self, location, glyphs, carets):
        carets = [self.makeLigCaret(location, caret) for caret in carets]
        for glyph in glyphs:
            if glyph not in self.ligCaretCoords_:
                self.ligCaretCoords_[glyph] = carets

    def add_name_record(self, location, nameID, platformID, platEncID, langID, string):
        self.names_.append([nameID, platformID, platEncID, langID, string])

    def add_os2_field(self, key, value):
        self.os2_[key] = value

    def add_hhea_field(self, key, value):
        self.hhea_[key] = value

    def add_vhea_field(self, key, value):
        self.vhea_[key] = value

    def add_conditionset(self, location, key, value):
        if "fvar" not in self.font:
            raise FeatureLibError(
                "Cannot add feature variations to a font without an 'fvar' table",
                location,
            )

        # Normalize
        axisMap = {
            axis.axisTag: (axis.minValue, axis.defaultValue, axis.maxValue)
            for axis in self.axes
        }

        value = {
            tag: (
                normalizeValue(bottom, axisMap[tag]),
                normalizeValue(top, axisMap[tag]),
            )
            for tag, (bottom, top) in value.items()
        }

        # NOTE: This might result in rounding errors (off-by-ones) compared to
        # rules in Designspace files, since we're working with what's in the
        # `avar` table rather than the original values.
        if "avar" in self.font:
            mapping = self.font["avar"].segments
            value = {
                axis: tuple(
                    piecewiseLinearMap(v, mapping[axis]) if axis in mapping else v
                    for v in condition_range
                )
                for axis, condition_range in value.items()
            }

        self.conditionsets_[key] = value

    def makeVariablePos(self, location, varscalar):
        if not self.varstorebuilder:
            raise FeatureLibError(
                "Can't define a variable scalar in a non-variable font", location
            )

        varscalar.axes = self.axes
        if not varscalar.does_vary:
            return varscalar.default, None

        default, index = varscalar.add_to_variation_store(
            self.varstorebuilder, self.model_cache, self.font.get("avar")
        )

        device = None
        if index is not None and index != 0xFFFFFFFF:
            device = buildVarDevTable(index)

        return default, device

    def makeAnchorPos(self, varscalar, deviceTable, location):
        device = None
        if not isinstance(varscalar, VariableScalar):
            if deviceTable is not None:
                device = otl.buildDevice(dict(deviceTable))
            return varscalar, device
        default, device = self.makeVariablePos(location, varscalar)
        if device is not None and deviceTable is not None:
            raise FeatureLibError(
                "Can't define a device coordinate and variable scalar", location
            )
        return default, device

    def makeOpenTypeAnchor(self, location, anchor):
        """ast.Anchor --> otTables.Anchor"""
        if anchor is None:
            return None
        deviceX, deviceY = None, None
        if anchor.xDeviceTable is not None:
            deviceX = otl.buildDevice(dict(anchor.xDeviceTable))
        if anchor.yDeviceTable is not None:
            deviceY = otl.buildDevice(dict(anchor.yDeviceTable))
        x, deviceX = self.makeAnchorPos(anchor.x, anchor.xDeviceTable, location)
        y, deviceY = self.makeAnchorPos(anchor.y, anchor.yDeviceTable, location)
        otlanchor = otl.buildAnchor(x, y, anchor.contourpoint, deviceX, deviceY)
        return otlanchor

    _VALUEREC_ATTRS = {
        name[0].lower() + name[1:]: (name, isDevice)
        for _, name, isDevice, _ in otBase.valueRecordFormat
        if not name.startswith("Reserved")
    }

    def makeOpenTypeValueRecord(self, location, v, pairPosContext):
        """ast.ValueRecord --> otBase.ValueRecord"""
        if not v:
            return None

        vr = {}
        for astName, (otName, isDevice) in self._VALUEREC_ATTRS.items():
            val = getattr(v, astName, None)
            if not val:
                continue
            if isDevice:
                vr[otName] = otl.buildDevice(dict(val))
            elif isinstance(val, VariableScalar):
                otDeviceName = otName[0:4] + "Device"
                feaDeviceName = otDeviceName[0].lower() + otDeviceName[1:]
                if getattr(v, feaDeviceName):
                    raise FeatureLibError(
                        "Can't define a device coordinate and variable scalar", location
                    )
                vr[otName], device = self.makeVariablePos(location, val)
                if device is not None:
                    vr[otDeviceName] = device
            else:
                vr[otName] = val

        if pairPosContext and not vr:
            vr = {"YAdvance": 0} if v.vertical else {"XAdvance": 0}
        valRec = otl.buildValue(vr)
        return valRec

# === NexusCore/openenv\Lib\site-packages\matplotlib\image.py ===
"""
The image module supports basic image loading, rescaling and display
operations.
"""

import math
import os
import logging
from pathlib import Path
import warnings

import numpy as np
import PIL.Image
import PIL.PngImagePlugin

import matplotlib as mpl
from matplotlib import _api, cbook
# For clarity, names from _image are given explicitly in this module
from matplotlib import _image
# For user convenience, the names from _image are also imported into
# the image namespace
from matplotlib._image import *  # noqa: F401, F403
import matplotlib.artist as martist
import matplotlib.colorizer as mcolorizer
from matplotlib.backend_bases import FigureCanvasBase
import matplotlib.colors as mcolors
from matplotlib.transforms import (
    Affine2D, BboxBase, Bbox, BboxTransform, BboxTransformTo,
    IdentityTransform, TransformedBbox)

_log = logging.getLogger(__name__)

# map interpolation strings to module constants
_interpd_ = {
    'auto': _image.NEAREST,  # this will use nearest or Hanning...
    'none': _image.NEAREST,  # fall back to nearest when not supported
    'nearest': _image.NEAREST,
    'bilinear': _image.BILINEAR,
    'bicubic': _image.BICUBIC,
    'spline16': _image.SPLINE16,
    'spline36': _image.SPLINE36,
    'hanning': _image.HANNING,
    'hamming': _image.HAMMING,
    'hermite': _image.HERMITE,
    'kaiser': _image.KAISER,
    'quadric': _image.QUADRIC,
    'catrom': _image.CATROM,
    'gaussian': _image.GAUSSIAN,
    'bessel': _image.BESSEL,
    'mitchell': _image.MITCHELL,
    'sinc': _image.SINC,
    'lanczos': _image.LANCZOS,
    'blackman': _image.BLACKMAN,
    'antialiased': _image.NEAREST,  # this will use nearest or Hanning...
}

interpolations_names = set(_interpd_)


def composite_images(images, renderer, magnification=1.0):
    """
    Composite a number of RGBA images into one.  The images are
    composited in the order in which they appear in the *images* list.

    Parameters
    ----------
    images : list of Images
        Each must have a `make_image` method.  For each image,
        `can_composite` should return `True`, though this is not
        enforced by this function.  Each image must have a purely
        affine transformation with no shear.

    renderer : `.RendererBase`

    magnification : float, default: 1
        The additional magnification to apply for the renderer in use.

    Returns
    -------
    image : (M, N, 4) `numpy.uint8` array
        The composited RGBA image.
    offset_x, offset_y : float
        The (left, bottom) offset where the composited image should be placed
        in the output figure.
    """
    if len(images) == 0:
        return np.empty((0, 0, 4), dtype=np.uint8), 0, 0

    parts = []
    bboxes = []
    for image in images:
        data, x, y, trans = image.make_image(renderer, magnification)
        if data is not None:
            x *= magnification
            y *= magnification
            parts.append((data, x, y, image._get_scalar_alpha()))
            bboxes.append(
                Bbox([[x, y], [x + data.shape[1], y + data.shape[0]]]))

    if len(parts) == 0:
        return np.empty((0, 0, 4), dtype=np.uint8), 0, 0

    bbox = Bbox.union(bboxes)

    output = np.zeros(
        (int(bbox.height), int(bbox.width), 4), dtype=np.uint8)

    for data, x, y, alpha in parts:
        trans = Affine2D().translate(x - bbox.x0, y - bbox.y0)
        _image.resample(data, output, trans, _image.NEAREST,
                        resample=False, alpha=alpha)

    return output, bbox.x0 / magnification, bbox.y0 / magnification


def _draw_list_compositing_images(
        renderer, parent, artists, suppress_composite=None):
    """
    Draw a sorted list of artists, compositing images into a single
    image where possible.

    For internal Matplotlib use only: It is here to reduce duplication
    between `Figure.draw` and `Axes.draw`, but otherwise should not be
    generally useful.
    """
    has_images = any(isinstance(x, _ImageBase) for x in artists)

    # override the renderer default if suppressComposite is not None
    not_composite = (suppress_composite if suppress_composite is not None
                     else renderer.option_image_nocomposite())

    if not_composite or not has_images:
        for a in artists:
            a.draw(renderer)
    else:
        # Composite any adjacent images together
        image_group = []
        mag = renderer.get_image_magnification()

        def flush_images():
            if len(image_group) == 1:
                image_group[0].draw(renderer)
            elif len(image_group) > 1:
                data, l, b = composite_images(image_group, renderer, mag)
                if data.size != 0:
                    gc = renderer.new_gc()
                    gc.set_clip_rectangle(parent.bbox)
                    gc.set_clip_path(parent.get_clip_path())
                    renderer.draw_image(gc, round(l), round(b), data)
                    gc.restore()
            del image_group[:]

        for a in artists:
            if (isinstance(a, _ImageBase) and a.can_composite() and
                    a.get_clip_on() and not a.get_clip_path()):
                image_group.append(a)
            else:
                flush_images()
                a.draw(renderer)
        flush_images()


def _resample(
        image_obj, data, out_shape, transform, *, resample=None, alpha=1):
    """
    Convenience wrapper around `._image.resample` to resample *data* to
    *out_shape* (with a third dimension if *data* is RGBA) that takes care of
    allocating the output array and fetching the relevant properties from the
    Image object *image_obj*.
    """
    # AGG can only handle coordinates smaller than 24-bit signed integers,
    # so raise errors if the input data is larger than _image.resample can
    # handle.
    msg = ('Data with more than {n} cannot be accurately displayed. '
           'Downsampling to less than {n} before displaying. '
           'To remove this warning, manually downsample your data.')
    if data.shape[1] > 2**23:
        warnings.warn(msg.format(n='2**23 columns'))
        step = int(np.ceil(data.shape[1] / 2**23))
        data = data[:, ::step]
        transform = Affine2D().scale(step, 1) + transform
    if data.shape[0] > 2**24:
        warnings.warn(msg.format(n='2**24 rows'))
        step = int(np.ceil(data.shape[0] / 2**24))
        data = data[::step, :]
        transform = Affine2D().scale(1, step) + transform
    # decide if we need to apply anti-aliasing if the data is upsampled:
    # compare the number of displayed pixels to the number of
    # the data pixels.
    interpolation = image_obj.get_interpolation()
    if interpolation in ['antialiased', 'auto']:
        # don't antialias if upsampling by an integer number or
        # if zooming in more than a factor of 3
        pos = np.array([[0, 0], [data.shape[1], data.shape[0]]])
        disp = transform.transform(pos)
        dispx = np.abs(np.diff(disp[:, 0]))
        dispy = np.abs(np.diff(disp[:, 1]))
        if ((dispx > 3 * data.shape[1] or
                dispx == data.shape[1] or
                dispx == 2 * data.shape[1]) and
            (dispy > 3 * data.shape[0] or
                dispy == data.shape[0] or
                dispy == 2 * data.shape[0])):
            interpolation = 'nearest'
        else:
            interpolation = 'hanning'
    out = np.zeros(out_shape + data.shape[2:], data.dtype)  # 2D->2D, 3D->3D.
    if resample is None:
        resample = image_obj.get_resample()
    _image.resample(data, out, transform,
                    _interpd_[interpolation],
                    resample,
                    alpha,
                    image_obj.get_filternorm(),
                    image_obj.get_filterrad())
    return out


def _rgb_to_rgba(A):
    """
    Convert an RGB image to RGBA, as required by the image resample C++
    extension.
    """
    rgba = np.zeros((A.shape[0], A.shape[1], 4), dtype=A.dtype)
    rgba[:, :, :3] = A
    if rgba.dtype == np.uint8:
        rgba[:, :, 3] = 255
    else:
        rgba[:, :, 3] = 1.0
    return rgba


class _ImageBase(mcolorizer.ColorizingArtist):
    """
    Base class for images.

    interpolation and cmap default to their rc settings

    cmap is a colors.Colormap instance
    norm is a colors.Normalize instance to map luminance to 0-1

    extent is data axes (left, right, bottom, top) for making image plots
    registered with data plots.  Default is to label the pixel
    centers with the zero-based row and column indices.

    Additional kwargs are matplotlib.artist properties
    """
    zorder = 0

    def __init__(self, ax,
                 cmap=None,
                 norm=None,
                 colorizer=None,
                 interpolation=None,
                 origin=None,
                 filternorm=True,
                 filterrad=4.0,
                 resample=False,
                 *,
                 interpolation_stage=None,
                 **kwargs
                 ):
        super().__init__(self._get_colorizer(cmap, norm, colorizer))
        if origin is None:
            origin = mpl.rcParams['image.origin']
        _api.check_in_list(["upper", "lower"], origin=origin)
        self.origin = origin
        self.set_filternorm(filternorm)
        self.set_filterrad(filterrad)
        self.set_interpolation(interpolation)
        self.set_interpolation_stage(interpolation_stage)
        self.set_resample(resample)
        self.axes = ax

        self._imcache = None

        self._internal_update(kwargs)

    def __str__(self):
        try:
            shape = self.get_shape()
            return f"{type(self).__name__}(shape={shape!r})"
        except RuntimeError:
            return type(self).__name__

    def __getstate__(self):
        # Save some space on the pickle by not saving the cache.
        return {**super().__getstate__(), "_imcache": None}

    def get_size(self):
        """Return the size of the image as tuple (numrows, numcols)."""
        return self.get_shape()[:2]

    def get_shape(self):
        """
        Return the shape of the image as tuple (numrows, numcols, channels).
        """
        if self._A is None:
            raise RuntimeError('You must first set the image array')

        return self._A.shape

    def set_alpha(self, alpha):
        """
        Set the alpha value used for blending - not supported on all backends.

        Parameters
        ----------
        alpha : float or 2D array-like or None
        """
        martist.Artist._set_alpha_for_array(self, alpha)
        if np.ndim(alpha) not in (0, 2):
            raise TypeError('alpha must be a float, two-dimensional '
                            'array, or None')
        self._imcache = None

    def _get_scalar_alpha(self):
        """
        Get a scalar alpha value to be applied to the artist as a whole.

        If the alpha value is a matrix, the method returns 1.0 because pixels
        have individual alpha values (see `~._ImageBase._make_image` for
        details). If the alpha value is a scalar, the method returns said value
        to be applied to the artist as a whole because pixels do not have
        individual alpha values.
        """
        return 1.0 if self._alpha is None or np.ndim(self._alpha) > 0 \
            else self._alpha

    def changed(self):
        """
        Call this whenever the mappable is changed so observers can update.
        """
        self._imcache = None
        super().changed()

    def _make_image(self, A, in_bbox, out_bbox, clip_bbox, magnification=1.0,
                    unsampled=False, round_to_pixel_border=True):
        """
        Normalize, rescale, and colormap the image *A* from the given *in_bbox*
        (in data space), to the given *out_bbox* (in pixel space) clipped to
        the given *clip_bbox* (also in pixel space), and magnified by the
        *magnification* factor.

        Parameters
        ----------
        A : ndarray

            - a (M, N) array interpreted as scalar (greyscale) image,
              with one of the dtypes `~numpy.float32`, `~numpy.float64`,
              `~numpy.float128`, `~numpy.uint16` or `~numpy.uint8`.
            - (M, N, 4) RGBA image with a dtype of `~numpy.float32`,
              `~numpy.float64`, `~numpy.float128`, or `~numpy.uint8`.

        in_bbox : `~matplotlib.transforms.Bbox`

        out_bbox : `~matplotlib.transforms.Bbox`

        clip_bbox : `~matplotlib.transforms.Bbox`

        magnification : float, default: 1

        unsampled : bool, default: False
            If True, the image will not be scaled, but an appropriate
            affine transformation will be returned instead.

        round_to_pixel_border : bool, default: True
            If True, the output image size will be rounded to the nearest pixel
            boundary.  This makes the images align correctly with the Axes.
            It should not be used if exact scaling is needed, such as for
            `.FigureImage`.

        Returns
        -------
        image : (M, N, 4) `numpy.uint8` array
            The RGBA image, resampled unless *unsampled* is True.
        x, y : float
            The upper left corner where the image should be drawn, in pixel
            space.
        trans : `~matplotlib.transforms.Affine2D`
            The affine transformation from image to pixel space.
        """
        if A is None:
            raise RuntimeError('You must first set the image '
                               'array or the image attribute')
        if A.size == 0:
            raise RuntimeError("_make_image must get a non-empty image. "
                               "Your Artist's draw method must filter before "
                               "this method is called.")

        clipped_bbox = Bbox.intersection(out_bbox, clip_bbox)

        if clipped_bbox is None:
            return None, 0, 0, None

        out_width_base = clipped_bbox.width * magnification
        out_height_base = clipped_bbox.height * magnification

        if out_width_base == 0 or out_height_base == 0:
            return None, 0, 0, None

        if self.origin == 'upper':
            # Flip the input image using a transform.  This avoids the
            # problem with flipping the array, which results in a copy
            # when it is converted to contiguous in the C wrapper
            t0 = Affine2D().translate(0, -A.shape[0]).scale(1, -1)
        else:
            t0 = IdentityTransform()

        t0 += (
            Affine2D()
            .scale(
                in_bbox.width / A.shape[1],
                in_bbox.height / A.shape[0])
            .translate(in_bbox.x0, in_bbox.y0)
            + self.get_transform())

        t = (t0
             + (Affine2D()
                .translate(-clipped_bbox.x0, -clipped_bbox.y0)
                .scale(magnification)))

        # So that the image is aligned with the edge of the Axes, we want to
        # round up the output width to the next integer.  This also means
        # scaling the transform slightly to account for the extra subpixel.
        if ((not unsampled) and t.is_affine and round_to_pixel_border and
                (out_width_base % 1.0 != 0.0 or out_height_base % 1.0 != 0.0)):
            out_width = math.ceil(out_width_base)
            out_height = math.ceil(out_height_base)
            extra_width = (out_width - out_width_base) / out_width_base
            extra_height = (out_height - out_height_base) / out_height_base
            t += Affine2D().scale(1.0 + extra_width, 1.0 + extra_height)
        else:
            out_width = int(out_width_base)
            out_height = int(out_height_base)
        out_shape = (out_height, out_width)

        if not unsampled:
            if not (A.ndim == 2 or A.ndim == 3 and A.shape[-1] in (3, 4)):
                raise ValueError(f"Invalid shape {A.shape} for image data")

            # if antialiased, this needs to change as window sizes
            # change:
            interpolation_stage = self._interpolation_stage
            if interpolation_stage in ['antialiased', 'auto']:
                pos = np.array([[0, 0], [A.shape[1], A.shape[0]]])
                disp = t.transform(pos)
                dispx = np.abs(np.diff(disp[:, 0])) / A.shape[1]
                dispy = np.abs(np.diff(disp[:, 1])) / A.shape[0]
                if (dispx < 3) or (dispy < 3):
                    interpolation_stage = 'rgba'
                else:
                    interpolation_stage = 'data'

            if A.ndim == 2 and interpolation_stage == 'data':
                # if we are a 2D array, then we are running through the
                # norm + colormap transformation.  However, in general the
                # input data is not going to match the size on the screen so we
                # have to resample to the correct number of pixels

                if A.dtype.kind == 'f':  # Float dtype: scale to same dtype.
                    scaled_dtype = np.dtype("f8" if A.dtype.itemsize > 4 else "f4")
                    if scaled_dtype.itemsize < A.dtype.itemsize:
                        _api.warn_external(f"Casting input data from {A.dtype}"
                                           f" to {scaled_dtype} for imshow.")
                else:  # Int dtype, likely.
                    # TODO slice input array first
                    # Scale to appropriately sized float: use float32 if the
                    # dynamic range is small, to limit the memory footprint.
                    da = A.max().astype("f8") - A.min().astype("f8")
                    scaled_dtype = "f8" if da > 1e8 else "f4"

                # resample the input data to the correct resolution and shape
                A_resampled = _resample(self, A.astype(scaled_dtype), out_shape, t)

                # if using NoNorm, cast back to the original datatype
                if isinstance(self.norm, mcolors.NoNorm):
                    A_resampled = A_resampled.astype(A.dtype)

                # Compute out_mask (what screen pixels include "bad" data
                # pixels) and out_alpha (to what extent screen pixels are
                # covered by data pixels: 0 outside the data extent, 1 inside
                # (even for bad data), and intermediate values at the edges).
                mask = (np.where(A.mask, np.float32(np.nan), np.float32(1))
                        if A.mask.shape == A.shape  # nontrivial mask
                        else np.ones_like(A, np.float32))
                # we always have to interpolate the mask to account for
                # non-affine transformations
                out_alpha = _resample(self, mask, out_shape, t, resample=True)
                del mask  # Make sure we don't use mask anymore!
                out_mask = np.isnan(out_alpha)
                out_alpha[out_mask] = 1
                # Apply the pixel-by-pixel alpha values if present
                alpha = self.get_alpha()
                if alpha is not None and np.ndim(alpha) > 0:
                    out_alpha *= _resample(self, alpha, out_shape, t, resample=True)
                # mask and run through the norm
                resampled_masked = np.ma.masked_array(A_resampled, out_mask)
                output = self.norm(resampled_masked)
            else:
                if A.ndim == 2:  # interpolation_stage = 'rgba'
                    self.norm.autoscale_None(A)
                    A = self.to_rgba(A)
                alpha = self.get_alpha()
                if alpha is None:  # alpha parameter not specified
                    if A.shape[2] == 3:  # image has no alpha channel
                        output_alpha = 255 if A.dtype == np.uint8 else 1.0
                    else:
                        output_alpha = _resample(  # resample alpha channel
                            self, A[..., 3], out_shape, t)
                    output = _resample(  # resample rgb channels
                        self, _rgb_to_rgba(A[..., :3]), out_shape, t)
                elif np.ndim(alpha) > 0:  # Array alpha
                    # user-specified array alpha overrides the existing alpha channel
                    output_alpha = _resample(self, alpha, out_shape, t)
                    output = _resample(
                        self, _rgb_to_rgba(A[..., :3]), out_shape, t)
                else:  # Scalar alpha
                    if A.shape[2] == 3:  # broadcast scalar alpha
                        output_alpha = (255 * alpha) if A.dtype == np.uint8 else alpha
                    else:  # or apply scalar alpha to existing alpha channel
                        output_alpha = _resample(self, A[..., 3], out_shape, t) * alpha
                    output = _resample(
                        self, _rgb_to_rgba(A[..., :3]), out_shape, t)
                output[..., 3] = output_alpha  # recombine rgb and alpha

            # output is now either a 2D array of normed (int or float) data
            # or an RGBA array of re-sampled input
            output = self.to_rgba(output, bytes=True, norm=False)
            # output is now a correctly sized RGBA array of uint8

            # Apply alpha *after* if the input was greyscale without a mask
            if A.ndim == 2:
                alpha = self._get_scalar_alpha()
                alpha_channel = output[:, :, 3]
                alpha_channel[:] = (  # Assignment will cast to uint8.
                    alpha_channel.astype(np.float32) * out_alpha * alpha)

        else:
            if self._imcache is None:
                self._imcache = self.to_rgba(A, bytes=True, norm=(A.ndim == 2))
            output = self._imcache

            # Subset the input image to only the part that will be displayed.
            subset = TransformedBbox(clip_bbox, t0.inverted()).frozen()
            output = output[
                int(max(subset.ymin, 0)):
                int(min(subset.ymax + 1, output.shape[0])),
                int(max(subset.xmin, 0)):
                int(min(subset.xmax + 1, output.shape[1]))]

            t = Affine2D().translate(
                int(max(subset.xmin, 0)), int(max(subset.ymin, 0))) + t

        return output, clipped_bbox.x0, clipped_bbox.y0, t

    def make_image(self, renderer, magnification=1.0, unsampled=False):
        """
        Normalize, rescale, and colormap this image's data for rendering using
        *renderer*, with the given *magnification*.

        If *unsampled* is True, the image will not be scaled, but an
        appropriate affine transformation will be returned instead.

        Returns
        -------
        image : (M, N, 4) `numpy.uint8` array
            The RGBA image, resampled unless *unsampled* is True.
        x, y : float
            The upper left corner where the image should be drawn, in pixel
            space.
        trans : `~matplotlib.transforms.Affine2D`
            The affine transformation from image to pixel space.
        """
        raise NotImplementedError('The make_image method must be overridden')

    def _check_unsampled_image(self):
        """
        Return whether the image is better to be drawn unsampled.

        The derived class needs to override it.
        """
        return False

    @martist.allow_rasterization
    def draw(self, renderer):
        # if not visible, declare victory and return
        if not self.get_visible():
            self.stale = False
            return
        # for empty images, there is nothing to draw!
        if self.get_array().size == 0:
            self.stale = False
            return
        # actually render the image.
        gc = renderer.new_gc()
        self._set_gc_clip(gc)
        gc.set_alpha(self._get_scalar_alpha())
        gc.set_url(self.get_url())
        gc.set_gid(self.get_gid())
        if (renderer.option_scale_image()  # Renderer supports transform kwarg.
                and self._check_unsampled_image()
                and self.get_transform().is_affine):
            im, l, b, trans = self.make_image(renderer, unsampled=True)
            if im is not None:
                trans = Affine2D().scale(im.shape[1], im.shape[0]) + trans
                renderer.draw_image(gc, l, b, im, trans)
        else:
            im, l, b, trans = self.make_image(
                renderer, renderer.get_image_magnification())
            if im is not None:
                renderer.draw_image(gc, l, b, im)
        gc.restore()
        self.stale = False

    def contains(self, mouseevent):
        """Test whether the mouse event occurred within the image."""
        if (self._different_canvas(mouseevent)
                # This doesn't work for figimage.
                or not self.axes.contains(mouseevent)[0]):
            return False, {}
        # TODO: make sure this is consistent with patch and patch
        # collection on nonlinear transformed coordinates.
        # TODO: consider returning image coordinates (shouldn't
        # be too difficult given that the image is rectilinear
        trans = self.get_transform().inverted()
        x, y = trans.transform([mouseevent.x, mouseevent.y])
        xmin, xmax, ymin, ymax = self.get_extent()
        # This checks xmin <= x <= xmax *or* xmax <= x <= xmin.
        inside = (x is not None and (x - xmin) * (x - xmax) <= 0
                  and y is not None and (y - ymin) * (y - ymax) <= 0)
        return inside, {}

    def write_png(self, fname):
        """Write the image to png file *fname*."""
        im = self.to_rgba(self._A[::-1] if self.origin == 'lower' else self._A,
                          bytes=True, norm=True)
        PIL.Image.fromarray(im).save(fname, format="png")

    @staticmethod
    def _normalize_image_array(A):
        """
        Check validity of image-like input *A* and normalize it to a format suitable for
        Image subclasses.
        """
        A = cbook.safe_masked_invalid(A, copy=True)
        if A.dtype != np.uint8 and not np.can_cast(A.dtype, float, "same_kind"):
            raise TypeError(f"Image data of dtype {A.dtype} cannot be "
                            f"converted to float")
        if A.ndim == 3 and A.shape[-1] == 1:
            A = A.squeeze(-1)  # If just (M, N, 1), assume scalar and apply colormap.
        if not (A.ndim == 2 or A.ndim == 3 and A.shape[-1] in [3, 4]):
            raise TypeError(f"Invalid shape {A.shape} for image data")
        if A.ndim == 3:
            # If the input data has values outside the valid range (after
            # normalisation), we issue a warning and then clip X to the bounds
            # - otherwise casting wraps extreme values, hiding outliers and
            # making reliable interpretation impossible.
            high = 255 if np.issubdtype(A.dtype, np.integer) else 1
            if A.min() < 0 or high < A.max():
                _log.warning(
                    'Clipping input data to the valid range for imshow with '
                    'RGB data ([0..1] for floats or [0..255] for integers). '
                    'Got range [%s..%s].',
                    A.min(), A.max()
                )
                A = np.clip(A, 0, high)
            # Cast unsupported integer types to uint8
            if A.dtype != np.uint8 and np.issubdtype(A.dtype, np.integer):
                A = A.astype(np.uint8)
        return A

    def set_data(self, A):
        """
        Set the image array.

        Note that this function does *not* update the normalization used.

        Parameters
        ----------
        A : array-like or `PIL.Image.Image`
        """
        if isinstance(A, PIL.Image.Image):
            A = pil_to_array(A)  # Needed e.g. to apply png palette.
        self._A = self._normalize_image_array(A)
        self._imcache = None
        self.stale = True

    def set_array(self, A):
        """
        Retained for backwards compatibility - use set_data instead.

        Parameters
        ----------
        A : array-like
        """
        # This also needs to be here to override the inherited
        # cm.ScalarMappable.set_array method so it is not invoked by mistake.
        self.set_data(A)

    def get_interpolation(self):
        """
        Return the interpolation method the image uses when resizing.

        One of 'auto', 'antialiased', 'nearest', 'bilinear', 'bicubic',
        'spline16', 'spline36', 'hanning', 'hamming', 'hermite', 'kaiser',
        'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos',
        or 'none'.
        """
        return self._interpolation

    def set_interpolation(self, s):
        """
        Set the interpolation method the image uses when resizing.

        If None, use :rc:`image.interpolation`. If 'none', the image is
        shown as is without interpolating. 'none' is only supported in
        agg, ps and pdf backends and will fall back to 'nearest' mode
        for other backends.

        Parameters
        ----------
        s : {'auto', 'nearest', 'bilinear', 'bicubic', 'spline16', \
'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom', \
'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'none'} or None
        """
        s = mpl._val_or_rc(s, 'image.interpolation').lower()
        _api.check_in_list(interpolations_names, interpolation=s)
        self._interpolation = s
        self.stale = True

    def get_interpolation_stage(self):
        """
        Return when interpolation happens during the transform to RGBA.

        One of 'data', 'rgba', 'auto'.
        """
        return self._interpolation_stage

    def set_interpolation_stage(self, s):
        """
        Set when interpolation happens during the transform to RGBA.

        Parameters
        ----------
        s : {'data', 'rgba', 'auto'} or None
            Whether to apply up/downsampling interpolation in data or RGBA
            space.  If None, use :rc:`image.interpolation_stage`.
            If 'auto' we will check upsampling rate and if less
            than 3 then use 'rgba', otherwise use 'data'.
        """
        s = mpl._val_or_rc(s, 'image.interpolation_stage')
        _api.check_in_list(['data', 'rgba', 'auto'], s=s)
        self._interpolation_stage = s
        self.stale = True

    def can_composite(self):
        """Return whether the image can be composited with its neighbors."""
        trans = self.get_transform()
        return (
            self._interpolation != 'none' and
            trans.is_affine and
            trans.is_separable)

    def set_resample(self, v):
        """
        Set whether image resampling is used.

        Parameters
        ----------
        v : bool or None
            If None, use :rc:`image.resample`.
        """
        v = mpl._val_or_rc(v, 'image.resample')
        self._resample = v
        self.stale = True

    def get_resample(self):
        """Return whether image resampling is used."""
        return self._resample

    def set_filternorm(self, filternorm):
        """
        Set whether the resize filter normalizes the weights.

        See help for `~.Axes.imshow`.

        Parameters
        ----------
        filternorm : bool
        """
        self._filternorm = bool(filternorm)
        self.stale = True

    def get_filternorm(self):
        """Return whether the resize filter normalizes the weights."""
        return self._filternorm

    def set_filterrad(self, filterrad):
        """
        Set the resize filter radius only applicable to some
        interpolation schemes -- see help for imshow

        Parameters
        ----------
        filterrad : positive float
        """
        r = float(filterrad)
        if r <= 0:
            raise ValueError("The filter radius must be a positive number")
        self._filterrad = r
        self.stale = True

    def get_filterrad(self):
        """Return the filterrad setting."""
        return self._filterrad


class AxesImage(_ImageBase):
    """
    An image with pixels on a regular grid, attached to an Axes.

    Parameters
    ----------
    ax : `~matplotlib.axes.Axes`
        The Axes the image will belong to.
    cmap : str or `~matplotlib.colors.Colormap`, default: :rc:`image.cmap`
        The Colormap instance or registered colormap name used to map scalar
        data to colors.
    norm : str or `~matplotlib.colors.Normalize`
        Maps luminance to 0-1.
    interpolation : str, default: :rc:`image.interpolation`
        Supported values are 'none', 'auto', 'nearest', 'bilinear',
        'bicubic', 'spline16', 'spline36', 'hanning', 'hamming', 'hermite',
        'kaiser', 'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell',
        'sinc', 'lanczos', 'blackman'.
    interpolation_stage : {'data', 'rgba'}, default: 'data'
        If 'data', interpolation
        is carried out on the data provided by the user.  If 'rgba', the
        interpolation is carried out after the colormapping has been
        applied (visual interpolation).
    origin : {'upper', 'lower'}, default: :rc:`image.origin`
        Place the [0, 0] index of the array in the upper left or lower left
        corner of the Axes. The convention 'upper' is typically used for
        matrices and images.
    extent : tuple, optional
        The data axes (left, right, bottom, top) for making image plots
        registered with data plots.  Default is to label the pixel
        centers with the zero-based row and column indices.
    filternorm : bool, default: True
        A parameter for the antigrain image resize filter
        (see the antigrain documentation).
        If filternorm is set, the filter normalizes integer values and corrects
        the rounding errors. It doesn't do anything with the source floating
        point values, it corrects only integers according to the rule of 1.0
        which means that any sum of pixel weights must be equal to 1.0. So,
        the filter function must produce a graph of the proper shape.
    filterrad : float > 0, default: 4
        The filter radius for filters that have a radius parameter, i.e. when
        interpolation is one of: 'sinc', 'lanczos' or 'blackman'.
    resample : bool, default: False
        When True, use a full resampling method. When False, only resample when
        the output image is larger than the input image.
    **kwargs : `~matplotlib.artist.Artist` properties
    """

    def __init__(self, ax,
                 *,
                 cmap=None,
                 norm=None,
                 colorizer=None,
                 interpolation=None,
                 origin=None,
                 extent=None,
                 filternorm=True,
                 filterrad=4.0,
                 resample=False,
                 interpolation_stage=None,
                 **kwargs
                 ):

        self._extent = extent

        super().__init__(
            ax,
            cmap=cmap,
            norm=norm,
            colorizer=colorizer,
            interpolation=interpolation,
            origin=origin,
            filternorm=filternorm,
            filterrad=filterrad,
            resample=resample,
            interpolation_stage=interpolation_stage,
            **kwargs
        )

    def get_window_extent(self, renderer=None):
        x0, x1, y0, y1 = self._extent
        bbox = Bbox.from_extents([x0, y0, x1, y1])
        return bbox.transformed(self.get_transform())

    def make_image(self, renderer, magnification=1.0, unsampled=False):
        # docstring inherited
        trans = self.get_transform()
        # image is created in the canvas coordinate.
        x1, x2, y1, y2 = self.get_extent()
        bbox = Bbox(np.array([[x1, y1], [x2, y2]]))
        transformed_bbox = TransformedBbox(bbox, trans)
        clip = ((self.get_clip_box() or self.axes.bbox) if self.get_clip_on()
                else self.get_figure(root=True).bbox)
        return self._make_image(self._A, bbox, transformed_bbox, clip,
                                magnification, unsampled=unsampled)

    def _check_unsampled_image(self):
        """Return whether the image would be better drawn unsampled."""
        return self.get_interpolation() == "none"

    def set_extent(self, extent, **kwargs):
        """
        Set the image extent.

        Parameters
        ----------
        extent : 4-tuple of float
            The position and size of the image as tuple
            ``(left, right, bottom, top)`` in data coordinates.
        **kwargs
            Other parameters from which unit info (i.e., the *xunits*,
            *yunits*, *zunits* (for 3D Axes), *runits* and *thetaunits* (for
            polar Axes) entries are applied, if present.

        Notes
        -----
        This updates `.Axes.dataLim`, and, if autoscaling, sets `.Axes.viewLim`
        to tightly fit the image, regardless of `~.Axes.dataLim`.  Autoscaling
        state is not changed, so a subsequent call to `.Axes.autoscale_view`
        will redo the autoscaling in accord with `~.Axes.dataLim`.
        """
        (xmin, xmax), (ymin, ymax) = self.axes._process_unit_info(
            [("x", [extent[0], extent[1]]),
             ("y", [extent[2], extent[3]])],
            kwargs)
        if kwargs:
            raise _api.kwarg_error("set_extent", kwargs)
        xmin = self.axes._validate_converted_limits(
            xmin, self.convert_xunits)
        xmax = self.axes._validate_converted_limits(
            xmax, self.convert_xunits)
        ymin = self.axes._validate_converted_limits(
            ymin, self.convert_yunits)
        ymax = self.axes._validate_converted_limits(
            ymax, self.convert_yunits)
        extent = [xmin, xmax, ymin, ymax]

        self._extent = extent
        corners = (xmin, ymin), (xmax, ymax)
        self.axes.update_datalim(corners)
        self.sticky_edges.x[:] = [xmin, xmax]
        self.sticky_edges.y[:] = [ymin, ymax]
        if self.axes.get_autoscalex_on():
            self.axes.set_xlim((xmin, xmax), auto=None)
        if self.axes.get_autoscaley_on():
            self.axes.set_ylim((ymin, ymax), auto=None)
        self.stale = True

    def get_extent(self):
        """Return the image extent as tuple (left, right, bottom, top)."""
        if self._extent is not None:
            return self._extent
        else:
            sz = self.get_size()
            numrows, numcols = sz
            if self.origin == 'upper':
                return (-0.5, numcols-0.5, numrows-0.5, -0.5)
            else:
                return (-0.5, numcols-0.5, -0.5, numrows-0.5)

    def get_cursor_data(self, event):
        """
        Return the image value at the event position or *None* if the event is
        outside the image.

        See Also
        --------
        matplotlib.artist.Artist.get_cursor_data
        """
        xmin, xmax, ymin, ymax = self.get_extent()
        if self.origin == 'upper':
            ymin, ymax = ymax, ymin
        arr = self.get_array()
        data_extent = Bbox([[xmin, ymin], [xmax, ymax]])
        array_extent = Bbox([[0, 0], [arr.shape[1], arr.shape[0]]])
        trans = self.get_transform().inverted()
        trans += BboxTransform(boxin=data_extent, boxout=array_extent)
        point = trans.transform([event.x, event.y])
        if any(np.isnan(point)):
            return None
        j, i = point.astype(int)
        # Clip the coordinates at array bounds
        if not (0 <= i < arr.shape[0]) or not (0 <= j < arr.shape[1]):
            return None
        else:
            return arr[i, j]


class NonUniformImage(AxesImage):
    """
    An image with pixels on a rectilinear grid.

    In contrast to `.AxesImage`, where pixels are on a regular grid,
    NonUniformImage allows rows and columns with individual heights / widths.

    See also :doc:`/gallery/images_contours_and_fields/image_nonuniform`.
    """

    def __init__(self, ax, *, interpolation='nearest', **kwargs):
        """
        Parameters
        ----------
        ax : `~matplotlib.axes.Axes`
            The Axes the image will belong to.
        interpolation : {'nearest', 'bilinear'}, default: 'nearest'
            The interpolation scheme used in the resampling.
        **kwargs
            All other keyword arguments are identical to those of `.AxesImage`.
        """
        super().__init__(ax, **kwargs)
        self.set_interpolation(interpolation)

    def _check_unsampled_image(self):
        """Return False. Do not use unsampled image."""
        return False

    def make_image(self, renderer, magnification=1.0, unsampled=False):
        # docstring inherited
        if self._A is None:
            raise RuntimeError('You must first set the image array')
        if unsampled:
            raise ValueError('unsampled not supported on NonUniformImage')
        A = self._A
        if A.ndim == 2:
            if A.dtype != np.uint8:
                A = self.to_rgba(A, bytes=True)
            else:
                A = np.repeat(A[:, :, np.newaxis], 4, 2)
                A[:, :, 3] = 255
        else:
            if A.dtype != np.uint8:
                A = (255*A).astype(np.uint8)
            if A.shape[2] == 3:
                B = np.zeros(tuple([*A.shape[0:2], 4]), np.uint8)
                B[:, :, 0:3] = A
                B[:, :, 3] = 255
                A = B
        l, b, r, t = self.axes.bbox.extents
        width = int(((round(r) + 0.5) - (round(l) - 0.5)) * magnification)
        height = int(((round(t) + 0.5) - (round(b) - 0.5)) * magnification)

        invertedTransform = self.axes.transData.inverted()
        x_pix = invertedTransform.transform(
            [(x, b) for x in np.linspace(l, r, width)])[:, 0]
        y_pix = invertedTransform.transform(
            [(l, y) for y in np.linspace(b, t, height)])[:, 1]

        if self._interpolation == "nearest":
            x_mid = (self._Ax[:-1] + self._Ax[1:]) / 2
            y_mid = (self._Ay[:-1] + self._Ay[1:]) / 2
            x_int = x_mid.searchsorted(x_pix)
            y_int = y_mid.searchsorted(y_pix)
            # The following is equal to `A[y_int[:, None], x_int[None, :]]`,
            # but many times faster.  Both casting to uint32 (to have an
            # effectively 1D array) and manual index flattening matter.
            im = (
                np.ascontiguousarray(A).view(np.uint32).ravel()[
                    np.add.outer(y_int * A.shape[1], x_int)]
                .view(np.uint8).reshape((height, width, 4)))
        else:  # self._interpolation == "bilinear"
            # Use np.interp to compute x_int/x_float has similar speed.
            x_int = np.clip(
                self._Ax.searchsorted(x_pix) - 1, 0, len(self._Ax) - 2)
            y_int = np.clip(
                self._Ay.searchsorted(y_pix) - 1, 0, len(self._Ay) - 2)
            idx_int = np.add.outer(y_int * A.shape[1], x_int)
            x_frac = np.clip(
                np.divide(x_pix - self._Ax[x_int], np.diff(self._Ax)[x_int],
                          dtype=np.float32),  # Downcasting helps with speed.
                0, 1)
            y_frac = np.clip(
                np.divide(y_pix - self._Ay[y_int], np.diff(self._Ay)[y_int],
                          dtype=np.float32),
                0, 1)
            f00 = np.outer(1 - y_frac, 1 - x_frac)
            f10 = np.outer(y_frac, 1 - x_frac)
            f01 = np.outer(1 - y_frac, x_frac)
            f11 = np.outer(y_frac, x_frac)
            im = np.empty((height, width, 4), np.uint8)
            for chan in range(4):
                ac = A[:, :, chan].reshape(-1)  # reshape(-1) avoids a copy.
                # Shifting the buffer start (`ac[offset:]`) avoids an array
                # addition (`ac[idx_int + offset]`).
                buf = f00 * ac[idx_int]
                buf += f10 * ac[A.shape[1]:][idx_int]
                buf += f01 * ac[1:][idx_int]
                buf += f11 * ac[A.shape[1] + 1:][idx_int]
                im[:, :, chan] = buf  # Implicitly casts to uint8.
        return im, l, b, IdentityTransform()

    def set_data(self, x, y, A):
        """
        Set the grid for the pixel centers, and the pixel values.

        Parameters
        ----------
        x, y : 1D array-like
            Monotonic arrays of shapes (N,) and (M,), respectively, specifying
            pixel centers.
        A : array-like
            (M, N) `~numpy.ndarray` or masked array of values to be
            colormapped, or (M, N, 3) RGB array, or (M, N, 4) RGBA array.
        """
        A = self._normalize_image_array(A)
        x = np.array(x, np.float32)
        y = np.array(y, np.float32)
        if not (x.ndim == y.ndim == 1 and A.shape[:2] == y.shape + x.shape):
            raise TypeError("Axes don't match array shape")
        self._A = A
        self._Ax = x
        self._Ay = y
        self._imcache = None
        self.stale = True

    def set_array(self, *args):
        raise NotImplementedError('Method not supported')

    def set_interpolation(self, s):
        """
        Parameters
        ----------
        s : {'nearest', 'bilinear'} or None
            If None, use :rc:`image.interpolation`.
        """
        if s is not None and s not in ('nearest', 'bilinear'):
            raise NotImplementedError('Only nearest neighbor and '
                                      'bilinear interpolations are supported')
        super().set_interpolation(s)

    def get_extent(self):
        if self._A is None:
            raise RuntimeError('Must set data first')
        return self._Ax[0], self._Ax[-1], self._Ay[0], self._Ay[-1]

    def set_filternorm(self, filternorm):
        pass

    def set_filterrad(self, filterrad):
        pass

    def set_norm(self, norm):
        if self._A is not None:
            raise RuntimeError('Cannot change colors after loading data')
        super().set_norm(norm)

    def set_cmap(self, cmap):
        if self._A is not None:
            raise RuntimeError('Cannot change colors after loading data')
        super().set_cmap(cmap)

    def get_cursor_data(self, event):
        # docstring inherited
        x, y = event.xdata, event.ydata
        if (x < self._Ax[0] or x > self._Ax[-1] or
                y < self._Ay[0] or y > self._Ay[-1]):
            return None
        j = np.searchsorted(self._Ax, x) - 1
        i = np.searchsorted(self._Ay, y) - 1
        return self._A[i, j]


class PcolorImage(AxesImage):
    """
    Make a pcolor-style plot with an irregular rectangular grid.

    This uses a variation of the original irregular image code,
    and it is used by pcolorfast for the corresponding grid type.
    """

    def __init__(self, ax,
                 x=None,
                 y=None,
                 A=None,
                 *,
                 cmap=None,
                 norm=None,
                 colorizer=None,
                 **kwargs
                 ):
        """
        Parameters
        ----------
        ax : `~matplotlib.axes.Axes`
            The Axes the image will belong to.
        x, y : 1D array-like, optional
            Monotonic arrays of length N+1 and M+1, respectively, specifying
            rectangle boundaries.  If not given, will default to
            ``range(N + 1)`` and ``range(M + 1)``, respectively.
        A : array-like
            The data to be color-coded. The interpretation depends on the
            shape:

            - (M, N) `~numpy.ndarray` or masked array: values to be colormapped
            - (M, N, 3): RGB array
            - (M, N, 4): RGBA array

        cmap : str or `~matplotlib.colors.Colormap`, default: :rc:`image.cmap`
            The Colormap instance or registered colormap name used to map
            scalar data to colors.
        norm : str or `~matplotlib.colors.Normalize`
            Maps luminance to 0-1.
        **kwargs : `~matplotlib.artist.Artist` properties
        """
        super().__init__(ax, norm=norm, cmap=cmap, colorizer=colorizer)
        self._internal_update(kwargs)
        if A is not None:
            self.set_data(x, y, A)

    def make_image(self, renderer, magnification=1.0, unsampled=False):
        # docstring inherited
        if self._A is None:
            raise RuntimeError('You must first set the image array')
        if unsampled:
            raise ValueError('unsampled not supported on PColorImage')

        if self._imcache is None:
            A = self.to_rgba(self._A, bytes=True)
            self._imcache = np.pad(A, [(1, 1), (1, 1), (0, 0)], "constant")
        padded_A = self._imcache
        bg = mcolors.to_rgba(self.axes.patch.get_facecolor(), 0)
        bg = (np.array(bg) * 255).astype(np.uint8)
        if (padded_A[0, 0] != bg).all():
            padded_A[[0, -1], :] = padded_A[:, [0, -1]] = bg

        l, b, r, t = self.axes.bbox.extents
        width = (round(r) + 0.5) - (round(l) - 0.5)
        height = (round(t) + 0.5) - (round(b) - 0.5)
        width = round(width * magnification)
        height = round(height * magnification)
        vl = self.axes.viewLim

        x_pix = np.linspace(vl.x0, vl.x1, width)
        y_pix = np.linspace(vl.y0, vl.y1, height)
        x_int = self._Ax.searchsorted(x_pix)
        y_int = self._Ay.searchsorted(y_pix)
        im = (  # See comment in NonUniformImage.make_image re: performance.
            padded_A.view(np.uint32).ravel()[
                np.add.outer(y_int * padded_A.shape[1], x_int)]
            .view(np.uint8).reshape((height, width, 4)))
        return im, l, b, IdentityTransform()

    def _check_unsampled_image(self):
        return False

    def set_data(self, x, y, A):
        """
        Set the grid for the rectangle boundaries, and the data values.

        Parameters
        ----------
        x, y : 1D array-like, optional
            Monotonic arrays of length N+1 and M+1, respectively, specifying
            rectangle boundaries.  If not given, will default to
            ``range(N + 1)`` and ``range(M + 1)``, respectively.
        A : array-like
            The data to be color-coded. The interpretation depends on the
            shape:

            - (M, N) `~numpy.ndarray` or masked array: values to be colormapped
            - (M, N, 3): RGB array
            - (M, N, 4): RGBA array
        """
        A = self._normalize_image_array(A)
        x = np.arange(0., A.shape[1] + 1) if x is None else np.array(x, float).ravel()
        y = np.arange(0., A.shape[0] + 1) if y is None else np.array(y, float).ravel()
        if A.shape[:2] != (y.size - 1, x.size - 1):
            raise ValueError(
                "Axes don't match array shape. Got %s, expected %s." %
                (A.shape[:2], (y.size - 1, x.size - 1)))
        # For efficient cursor readout, ensure x and y are increasing.
        if x[-1] < x[0]:
            x = x[::-1]
            A = A[:, ::-1]
        if y[-1] < y[0]:
            y = y[::-1]
            A = A[::-1]
        self._A = A
        self._Ax = x
        self._Ay = y
        self._imcache = None
        self.stale = True

    def set_array(self, *args):
        raise NotImplementedError('Method not supported')

    def get_cursor_data(self, event):
        # docstring inherited
        x, y = event.xdata, event.ydata
        if (x < self._Ax[0] or x > self._Ax[-1] or
                y < self._Ay[0] or y > self._Ay[-1]):
            return None
        j = np.searchsorted(self._Ax, x) - 1
        i = np.searchsorted(self._Ay, y) - 1
        return self._A[i, j]


class FigureImage(_ImageBase):
    """An image attached to a figure."""

    zorder = 0

    _interpolation = 'nearest'

    def __init__(self, fig,
                 *,
                 cmap=None,
                 norm=None,
                 colorizer=None,
                 offsetx=0,
                 offsety=0,
                 origin=None,
                 **kwargs
                 ):
        """
        cmap is a colors.Colormap instance
        norm is a colors.Normalize instance to map luminance to 0-1

        kwargs are an optional list of Artist keyword args
        """
        super().__init__(
            None,
            norm=norm,
            cmap=cmap,
            colorizer=colorizer,
            origin=origin
        )
        self.set_figure(fig)
        self.ox = offsetx
        self.oy = offsety
        self._internal_update(kwargs)
        self.magnification = 1.0

    def get_extent(self):
        """Return the image extent as tuple (left, right, bottom, top)."""
        numrows, numcols = self.get_size()
        return (-0.5 + self.ox, numcols-0.5 + self.ox,
                -0.5 + self.oy, numrows-0.5 + self.oy)

    def make_image(self, renderer, magnification=1.0, unsampled=False):
        # docstring inherited
        fig = self.get_figure(root=True)
        fac = renderer.dpi/fig.dpi
        # fac here is to account for pdf, eps, svg backends where
        # figure.dpi is set to 72.  This means we need to scale the
        # image (using magnification) and offset it appropriately.
        bbox = Bbox([[self.ox/fac, self.oy/fac],
                     [(self.ox/fac + self._A.shape[1]),
                     (self.oy/fac + self._A.shape[0])]])
        width, height = fig.get_size_inches()
        width *= renderer.dpi
        height *= renderer.dpi
        clip = Bbox([[0, 0], [width, height]])
        return self._make_image(
            self._A, bbox, bbox, clip, magnification=magnification / fac,
            unsampled=unsampled, round_to_pixel_border=False)

    def set_data(self, A):
        """Set the image array."""
        super().set_data(A)
        self.stale = True


class BboxImage(_ImageBase):
    """The Image class whose size is determined by the given bbox."""

    def __init__(self, bbox,
                 *,
                 cmap=None,
                 norm=None,
                 colorizer=None,
                 interpolation=None,
                 origin=None,
                 filternorm=True,
                 filterrad=4.0,
                 resample=False,
                 **kwargs
                 ):
        """
        cmap is a colors.Colormap instance
        norm is a colors.Normalize instance to map luminance to 0-1

        kwargs are an optional list of Artist keyword args
        """
        super().__init__(
            None,
            cmap=cmap,
            norm=norm,
            colorizer=colorizer,
            interpolation=interpolation,
            origin=origin,
            filternorm=filternorm,
            filterrad=filterrad,
            resample=resample,
            **kwargs
        )
        self.bbox = bbox

    def get_window_extent(self, renderer=None):
        if renderer is None:
            renderer = self.get_figure()._get_renderer()

        if isinstance(self.bbox, BboxBase):
            return self.bbox
        elif callable(self.bbox):
            return self.bbox(renderer)
        else:
            raise ValueError("Unknown type of bbox")

    def contains(self, mouseevent):
        """Test whether the mouse event occurred within the image."""
        if self._different_canvas(mouseevent) or not self.get_visible():
            return False, {}
        x, y = mouseevent.x, mouseevent.y
        inside = self.get_window_extent().contains(x, y)
        return inside, {}

    def make_image(self, renderer, magnification=1.0, unsampled=False):
        # docstring inherited
        width, height = renderer.get_canvas_width_height()
        bbox_in = self.get_window_extent(renderer).frozen()
        bbox_in._points /= [width, height]
        bbox_out = self.get_window_extent(renderer)
        clip = Bbox([[0, 0], [width, height]])
        self._transform = BboxTransformTo(clip)
        return self._make_image(
            self._A,
            bbox_in, bbox_out, clip, magnification, unsampled=unsampled)


def imread(fname, format=None):
    """
    Read an image from a file into an array.

    .. note::

        This function exists for historical reasons.  It is recommended to
        use `PIL.Image.open` instead for loading images.

    Parameters
    ----------
    fname : str or file-like
        The image file to read: a filename, a URL or a file-like object opened
        in read-binary mode.

        Passing a URL is deprecated.  Please open the URL
        for reading and pass the result to Pillow, e.g. with
        ``np.array(PIL.Image.open(urllib.request.urlopen(url)))``.
    format : str, optional
        The image file format assumed for reading the data.  The image is
        loaded as a PNG file if *format* is set to "png", if *fname* is a path
        or opened file with a ".png" extension, or if it is a URL.  In all
        other cases, *format* is ignored and the format is auto-detected by
        `PIL.Image.open`.

    Returns
    -------
    `numpy.array`
        The image data. The returned array has shape

        - (M, N) for grayscale images.
        - (M, N, 3) for RGB images.
        - (M, N, 4) for RGBA images.

        PNG images are returned as float arrays (0-1).  All other formats are
        returned as int arrays, with a bit depth determined by the file's
        contents.
    """
    # hide imports to speed initial import on systems with slow linkers
    from urllib import parse

    if format is None:
        if isinstance(fname, str):
            parsed = parse.urlparse(fname)
            # If the string is a URL (Windows paths appear as if they have a
            # length-1 scheme), assume png.
            if len(parsed.scheme) > 1:
                ext = 'png'
            else:
                ext = Path(fname).suffix.lower()[1:]
        elif hasattr(fname, 'geturl'):  # Returned by urlopen().
            # We could try to parse the url's path and use the extension, but
            # returning png is consistent with the block above.  Note that this
            # if clause has to come before checking for fname.name as
            # urlopen("file:///...") also has a name attribute (with the fixed
            # value "<urllib response>").
            ext = 'png'
        elif hasattr(fname, 'name'):
            ext = Path(fname.name).suffix.lower()[1:]
        else:
            ext = 'png'
    else:
        ext = format
    img_open = (
        PIL.PngImagePlugin.PngImageFile if ext == 'png' else PIL.Image.open)
    if isinstance(fname, str) and len(parse.urlparse(fname).scheme) > 1:
        # Pillow doesn't handle URLs directly.
        raise ValueError(
            "Please open the URL for reading and pass the "
            "result to Pillow, e.g. with "
            "``np.array(PIL.Image.open(urllib.request.urlopen(url)))``."
            )
    with img_open(fname) as image:
        return (_pil_png_to_float_array(image)
                if isinstance(image, PIL.PngImagePlugin.PngImageFile) else
                pil_to_array(image))


def imsave(fname, arr, vmin=None, vmax=None, cmap=None, format=None,
           origin=None, dpi=100, *, metadata=None, pil_kwargs=None):
    """
    Colormap and save an array as an image file.

    RGB(A) images are passed through.  Single channel images will be
    colormapped according to *cmap* and *norm*.

    .. note::

       If you want to save a single channel image as gray scale please use an
       image I/O library (such as pillow, tifffile, or imageio) directly.

    Parameters
    ----------
    fname : str or path-like or file-like
        A path or a file-like object to store the image in.
        If *format* is not set, then the output format is inferred from the
        extension of *fname*, if any, and from :rc:`savefig.format` otherwise.
        If *format* is set, it determines the output format.
    arr : array-like
        The image data. Accepts NumPy arrays or sequences
        (e.g., lists or tuples). The shape can be one of
        MxN (luminance), MxNx3 (RGB) or MxNx4 (RGBA).
    vmin, vmax : float, optional
        *vmin* and *vmax* set the color scaling for the image by fixing the
        values that map to the colormap color limits. If either *vmin*
        or *vmax* is None, that limit is determined from the *arr*
        min/max value.
    cmap : str or `~matplotlib.colors.Colormap`, default: :rc:`image.cmap`
        A Colormap instance or registered colormap name. The colormap
        maps scalar data to colors. It is ignored for RGB(A) data.
    format : str, optional
        The file format, e.g. 'png', 'pdf', 'svg', ...  The behavior when this
        is unset is documented under *fname*.
    origin : {'upper', 'lower'}, default: :rc:`image.origin`
        Indicates whether the ``(0, 0)`` index of the array is in the upper
        left or lower left corner of the Axes.
    dpi : float
        The DPI to store in the metadata of the file.  This does not affect the
        resolution of the output image.  Depending on file format, this may be
        rounded to the nearest integer.
    metadata : dict, optional
        Metadata in the image file.  The supported keys depend on the output
        format, see the documentation of the respective backends for more
        information.
        Currently only supported for "png", "pdf", "ps", "eps", and "svg".
    pil_kwargs : dict, optional
        Keyword arguments passed to `PIL.Image.Image.save`.  If the 'pnginfo'
        key is present, it completely overrides *metadata*, including the
        default 'Software' key.
    """
    from matplotlib.figure import Figure

    # Normalizing input (e.g., list or tuples) to NumPy array if needed
    arr = np.asanyarray(arr)

    if isinstance(fname, os.PathLike):
        fname = os.fspath(fname)
    if format is None:
        format = (Path(fname).suffix[1:] if isinstance(fname, str)
                  else mpl.rcParams["savefig.format"]).lower()
    if format in ["pdf", "ps", "eps", "svg"]:
        # Vector formats that are not handled by PIL.
        if pil_kwargs is not None:
            raise ValueError(
                f"Cannot use 'pil_kwargs' when saving to {format}")
        fig = Figure(dpi=dpi, frameon=False)
        fig.figimage(arr, cmap=cmap, vmin=vmin, vmax=vmax, origin=origin,
                     resize=True)
        fig.savefig(fname, dpi=dpi, format=format, transparent=True,
                    metadata=metadata)
    else:
        # Don't bother creating an image; this avoids rounding errors on the
        # size when dividing and then multiplying by dpi.
        if origin is None:
            origin = mpl.rcParams["image.origin"]
        else:
            _api.check_in_list(('upper', 'lower'), origin=origin)
        if origin == "lower":
            arr = arr[::-1]
        if (isinstance(arr, memoryview) and arr.format == "B"
                and arr.ndim == 3 and arr.shape[-1] == 4):
            # Such an ``arr`` would also be handled fine by sm.to_rgba below
            # (after casting with asarray), but it is useful to special-case it
            # because that's what backend_agg passes, and can be in fact used
            # as is, saving a few operations.
            rgba = arr
        else:
            sm = mcolorizer.Colorizer(cmap=cmap)
            sm.set_clim(vmin, vmax)
            rgba = sm.to_rgba(arr, bytes=True)
        if pil_kwargs is None:
            pil_kwargs = {}
        else:
            # we modify this below, so make a copy (don't modify caller's dict)
            pil_kwargs = pil_kwargs.copy()
        pil_shape = (rgba.shape[1], rgba.shape[0])
        rgba = np.require(rgba, requirements='C')
        image = PIL.Image.frombuffer(
            "RGBA", pil_shape, rgba, "raw", "RGBA", 0, 1)
        if format == "png":
            # Only use the metadata kwarg if pnginfo is not set, because the
            # semantics of duplicate keys in pnginfo is unclear.
            if "pnginfo" in pil_kwargs:
                if metadata:
                    _api.warn_external("'metadata' is overridden by the "
                                       "'pnginfo' entry in 'pil_kwargs'.")
            else:
                metadata = {
                    "Software": (f"Matplotlib version{mpl.__version__}, "
                                 f"https://matplotlib.org/"),
                    **(metadata if metadata is not None else {}),
                }
                pil_kwargs["pnginfo"] = pnginfo = PIL.PngImagePlugin.PngInfo()
                for k, v in metadata.items():
                    if v is not None:
                        pnginfo.add_text(k, v)
        elif metadata is not None:
            raise ValueError(f"metadata not supported for format {format!r}")
        if format in ["jpg", "jpeg"]:
            format = "jpeg"  # Pillow doesn't recognize "jpg".
            facecolor = mpl.rcParams["savefig.facecolor"]
            if cbook._str_equal(facecolor, "auto"):
                facecolor = mpl.rcParams["figure.facecolor"]
            color = tuple(int(x * 255) for x in mcolors.to_rgb(facecolor))
            background = PIL.Image.new("RGB", pil_shape, color)
            background.paste(image, image)
            image = background
        pil_kwargs.setdefault("format", format)
        pil_kwargs.setdefault("dpi", (dpi, dpi))
        image.save(fname, **pil_kwargs)


def pil_to_array(pilImage):
    """
    Load a `PIL image`_ and return it as a numpy int array.

    .. _PIL image: https://pillow.readthedocs.io/en/latest/reference/Image.html

    Returns
    -------
    numpy.array

        The array shape depends on the image type:

        - (M, N) for grayscale images.
        - (M, N, 3) for RGB images.
        - (M, N, 4) for RGBA images.
    """
    if pilImage.mode in ['RGBA', 'RGBX', 'RGB', 'L']:
        # return MxNx4 RGBA, MxNx3 RBA, or MxN luminance array
        return np.asarray(pilImage)
    elif pilImage.mode.startswith('I;16'):
        # return MxN luminance array of uint16
        raw = pilImage.tobytes('raw', pilImage.mode)
        if pilImage.mode.endswith('B'):
            x = np.frombuffer(raw, '>u2')
        else:
            x = np.frombuffer(raw, '<u2')
        return x.reshape(pilImage.size[::-1]).astype('=u2')
    else:  # try to convert to an rgba image
        try:
            pilImage = pilImage.convert('RGBA')
        except ValueError as err:
            raise RuntimeError('Unknown image mode') from err
        return np.asarray(pilImage)  # return MxNx4 RGBA array


def _pil_png_to_float_array(pil_png):
    """Convert a PIL `PNGImageFile` to a 0-1 float array."""
    # Unlike pil_to_array this converts to 0-1 float32s for backcompat with the
    # old libpng-based loader.
    # The supported rawmodes are from PIL.PngImagePlugin._MODES.  When
    # mode == "RGB(A)", the 16-bit raw data has already been coarsened to 8-bit
    # by Pillow.
    mode = pil_png.mode
    rawmode = pil_png.png.im_rawmode
    if rawmode == "1":  # Grayscale.
        return np.asarray(pil_png, np.float32)
    if rawmode == "L;2":  # Grayscale.
        return np.divide(pil_png, 2**2 - 1, dtype=np.float32)
    if rawmode == "L;4":  # Grayscale.
        return np.divide(pil_png, 2**4 - 1, dtype=np.float32)
    if rawmode == "L":  # Grayscale.
        return np.divide(pil_png, 2**8 - 1, dtype=np.float32)
    if rawmode == "I;16B":  # Grayscale.
        return np.divide(pil_png, 2**16 - 1, dtype=np.float32)
    if mode == "RGB":  # RGB.
        return np.divide(pil_png, 2**8 - 1, dtype=np.float32)
    if mode == "P":  # Palette.
        return np.divide(pil_png.convert("RGBA"), 2**8 - 1, dtype=np.float32)
    if mode == "LA":  # Grayscale + alpha.
        return np.divide(pil_png.convert("RGBA"), 2**8 - 1, dtype=np.float32)
    if mode == "RGBA":  # RGBA.
        return np.divide(pil_png, 2**8 - 1, dtype=np.float32)
    raise ValueError(f"Unknown PIL rawmode: {rawmode}")


def thumbnail(infile, thumbfile, scale=0.1, interpolation='bilinear',
              preview=False):
    """
    Make a thumbnail of image in *infile* with output filename *thumbfile*.

    See :doc:`/gallery/misc/image_thumbnail_sgskip`.

    Parameters
    ----------
    infile : str or file-like
        The image file. Matplotlib relies on Pillow_ for image reading, and
        thus supports a wide range of file formats, including PNG, JPG, TIFF
        and others.

        .. _Pillow: https://python-pillow.github.io

    thumbfile : str or file-like
        The thumbnail filename.

    scale : float, default: 0.1
        The scale factor for the thumbnail.

    interpolation : str, default: 'bilinear'
        The interpolation scheme used in the resampling. See the
        *interpolation* parameter of `~.Axes.imshow` for possible values.

    preview : bool, default: False
        If True, the default backend (presumably a user interface
        backend) will be used which will cause a figure to be raised if
        `~matplotlib.pyplot.show` is called.  If it is False, the figure is
        created using `.FigureCanvasBase` and the drawing backend is selected
        as `.Figure.savefig` would normally do.

    Returns
    -------
    `.Figure`
        The figure instance containing the thumbnail.
    """

    im = imread(infile)
    rows, cols, depth = im.shape

    # This doesn't really matter (it cancels in the end) but the API needs it.
    dpi = 100

    height = rows / dpi * scale
    width = cols / dpi * scale

    if preview:
        # Let the UI backend do everything.
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(width, height), dpi=dpi)
    else:
        from matplotlib.figure import Figure
        fig = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvasBase(fig)

    ax = fig.add_axes([0, 0, 1, 1], aspect='auto',
                      frameon=False, xticks=[], yticks=[])
    ax.imshow(im, aspect='auto', resample=True, interpolation=interpolation)
    fig.savefig(thumbfile, dpi=dpi)
    return fig

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_csound_builtins.py ===
"""
    pygments.lexers._csound_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

REMOVED_OPCODES = set('''
OSCsendA
beadsynt
beosc
buchla
getrowlin
lua_exec
lua_iaopcall
lua_iaopcall_off
lua_ikopcall
lua_ikopcall_off
lua_iopcall
lua_iopcall_off
lua_opdef
mp3scal_check
mp3scal_load
mp3scal_load2
mp3scal_play
mp3scal_play2
pvsgendy
socksend_k
signalflowgraph
sumTableFilter
systime
tabrowlin
vbap1move
'''.split())

# Opcodes in Csound 6.18.0 using:
#   python3 -c "
#   import re
#   from subprocess import Popen, PIPE
#   output = Popen(['csound', '--list-opcodes0'], stderr=PIPE, text=True).communicate()[1]
#   opcodes = output[re.search(r'^\$', output, re.M).end() : re.search(r'^\d+ opcodes\$', output, re.M).start()].split()
#   output = Popen(['csound', '--list-opcodes2'], stderr=PIPE, text=True).communicate()[1]
#   all_opcodes = output[re.search(r'^\$', output, re.M).end() : re.search(r'^\d+ opcodes\$', output, re.M).start()].split()
#   deprecated_opcodes = [opcode for opcode in all_opcodes if opcode not in opcodes]
#   # Remove opcodes that csound.py treats as keywords.
#   keyword_opcodes = [
#       'cggoto',   # https://csound.com/docs/manual/cggoto.html
#       'cigoto',   # https://csound.com/docs/manual/cigoto.html
#       'cingoto',  # (undocumented)
#       'ckgoto',   # https://csound.com/docs/manual/ckgoto.html
#       'cngoto',   # https://csound.com/docs/manual/cngoto.html
#       'cnkgoto',  # (undocumented)
#       'endin',    # https://csound.com/docs/manual/endin.html
#       'endop',    # https://csound.com/docs/manual/endop.html
#       'goto',     # https://csound.com/docs/manual/goto.html
#       'igoto',    # https://csound.com/docs/manual/igoto.html
#       'instr',    # https://csound.com/docs/manual/instr.html
#       'kgoto',    # https://csound.com/docs/manual/kgoto.html
#       'loop_ge',  # https://csound.com/docs/manual/loop_ge.html
#       'loop_gt',  # https://csound.com/docs/manual/loop_gt.html
#       'loop_le',  # https://csound.com/docs/manual/loop_le.html
#       'loop_lt',  # https://csound.com/docs/manual/loop_lt.html
#       'opcode',   # https://csound.com/docs/manual/opcode.html
#       'reinit',   # https://csound.com/docs/manual/reinit.html
#       'return',   # https://csound.com/docs/manual/return.html
#       'rireturn', # https://csound.com/docs/manual/rireturn.html
#       'rigoto',   # https://csound.com/docs/manual/rigoto.html
#       'tigoto',   # https://csound.com/docs/manual/tigoto.html
#       'timout'    # https://csound.com/docs/manual/timout.html
#   ]
#   opcodes = [opcode for opcode in opcodes if opcode not in keyword_opcodes]
#   newline = '\n'
#   print(f'''OPCODES = set(\'''
#   {newline.join(opcodes)}
#   \'''.split())
#
#   DEPRECATED_OPCODES = set(\'''
#   {newline.join(deprecated_opcodes)}
#   \'''.split())
#   ''')
#   "

OPCODES = set('''
ATSadd
ATSaddnz
ATSbufread
ATScross
ATSinfo
ATSinterpread
ATSpartialtap
ATSread
ATSreadnz
ATSsinnoi
FLbox
FLbutBank
FLbutton
FLcloseButton
FLcolor
FLcolor2
FLcount
FLexecButton
FLgetsnap
FLgroup
FLgroupEnd
FLgroup_end
FLhide
FLhvsBox
FLhvsBoxSetValue
FLjoy
FLkeyIn
FLknob
FLlabel
FLloadsnap
FLmouse
FLpack
FLpackEnd
FLpack_end
FLpanel
FLpanelEnd
FLpanel_end
FLprintk
FLprintk2
FLroller
FLrun
FLsavesnap
FLscroll
FLscrollEnd
FLscroll_end
FLsetAlign
FLsetBox
FLsetColor
FLsetColor2
FLsetFont
FLsetPosition
FLsetSize
FLsetSnapGroup
FLsetText
FLsetTextColor
FLsetTextSize
FLsetTextType
FLsetVal
FLsetVal_i
FLsetVali
FLsetsnap
FLshow
FLslidBnk
FLslidBnk2
FLslidBnk2Set
FLslidBnk2Setk
FLslidBnkGetHandle
FLslidBnkSet
FLslidBnkSetk
FLslider
FLtabs
FLtabsEnd
FLtabs_end
FLtext
FLupdate
FLvalue
FLvkeybd
FLvslidBnk
FLvslidBnk2
FLxyin
JackoAudioIn
JackoAudioInConnect
JackoAudioOut
JackoAudioOutConnect
JackoFreewheel
JackoInfo
JackoInit
JackoMidiInConnect
JackoMidiOut
JackoMidiOutConnect
JackoNoteOut
JackoOn
JackoTransport
K35_hpf
K35_lpf
MixerClear
MixerGetLevel
MixerReceive
MixerSend
MixerSetLevel
MixerSetLevel_i
OSCbundle
OSCcount
OSCinit
OSCinitM
OSClisten
OSCraw
OSCsend
OSCsend_lo
S
STKBandedWG
STKBeeThree
STKBlowBotl
STKBlowHole
STKBowed
STKBrass
STKClarinet
STKDrummer
STKFMVoices
STKFlute
STKHevyMetl
STKMandolin
STKModalBar
STKMoog
STKPercFlut
STKPlucked
STKResonate
STKRhodey
STKSaxofony
STKShakers
STKSimple
STKSitar
STKStifKarp
STKTubeBell
STKVoicForm
STKWhistle
STKWurley
a
abs
active
adsr
adsyn
adsynt
adsynt2
aftouch
allpole
alpass
alwayson
ampdb
ampdbfs
ampmidi
ampmidicurve
ampmidid
apoleparams
arduinoRead
arduinoReadF
arduinoStart
arduinoStop
areson
aresonk
atone
atonek
atonex
autocorr
babo
balance
balance2
bamboo
barmodel
bbcutm
bbcuts
betarand
bexprnd
bformdec1
bformdec2
bformenc1
binit
biquad
biquada
birnd
bob
bpf
bpfcos
bqrez
butbp
butbr
buthp
butlp
butterbp
butterbr
butterhp
butterlp
button
buzz
c2r
cabasa
cauchy
cauchyi
cbrt
ceil
cell
cent
centroid
ceps
cepsinv
chanctrl
changed
changed2
chani
chano
chebyshevpoly
checkbox
chn_S
chn_a
chn_k
chnclear
chnexport
chnget
chngeta
chngeti
chngetk
chngetks
chngets
chnmix
chnparams
chnset
chnseta
chnseti
chnsetk
chnsetks
chnsets
chuap
clear
clfilt
clip
clockoff
clockon
cmp
cmplxprod
cntCreate
cntCycles
cntDelete
cntDelete_i
cntRead
cntReset
cntState
comb
combinv
compilecsd
compileorc
compilestr
compress
compress2
connect
control
convle
convolve
copya2ftab
copyf2array
cos
cosh
cosinv
cosseg
cossegb
cossegr
count
count_i
cps2pch
cpsmidi
cpsmidib
cpsmidinn
cpsoct
cpspch
cpstmid
cpstun
cpstuni
cpsxpch
cpumeter
cpuprc
cross2
crossfm
crossfmi
crossfmpm
crossfmpmi
crosspm
crosspmi
crunch
ctlchn
ctrl14
ctrl21
ctrl7
ctrlinit
ctrlpreset
ctrlprint
ctrlprintpresets
ctrlsave
ctrlselect
cuserrnd
dam
date
dates
db
dbamp
dbfsamp
dcblock
dcblock2
dconv
dct
dctinv
deinterleave
delay
delay1
delayk
delayr
delayw
deltap
deltap3
deltapi
deltapn
deltapx
deltapxw
denorm
diff
diode_ladder
directory
diskgrain
diskin
diskin2
dispfft
display
distort
distort1
divz
doppler
dot
downsamp
dripwater
dssiactivate
dssiaudio
dssictls
dssiinit
dssilist
dumpk
dumpk2
dumpk3
dumpk4
duserrnd
dust
dust2
elapsedcycles
elapsedtime
envlpx
envlpxr
ephasor
eqfil
evalstr
event
event_i
eventcycles
eventtime
exciter
exitnow
exp
expcurve
expon
exprand
exprandi
expseg
expsega
expsegb
expsegba
expsegr
fareylen
fareyleni
faustaudio
faustcompile
faustctl
faustdsp
faustgen
faustplay
fft
fftinv
ficlose
filebit
filelen
filenchnls
filepeak
filescal
filesr
filevalid
fillarray
filter2
fin
fini
fink
fiopen
flanger
flashtxt
flooper
flooper2
floor
fluidAllOut
fluidCCi
fluidCCk
fluidControl
fluidEngine
fluidInfo
fluidLoad
fluidNote
fluidOut
fluidProgramSelect
fluidSetInterpMethod
fmanal
fmax
fmb3
fmbell
fmin
fmmetal
fmod
fmpercfl
fmrhode
fmvoice
fmwurlie
fof
fof2
fofilter
fog
fold
follow
follow2
foscil
foscili
fout
fouti
foutir
foutk
fprintks
fprints
frac
fractalnoise
framebuffer
freeverb
ftaudio
ftchnls
ftconv
ftcps
ftexists
ftfree
ftgen
ftgenonce
ftgentmp
ftlen
ftload
ftloadk
ftlptim
ftmorf
ftom
ftprint
ftresize
ftresizei
ftsamplebank
ftsave
ftsavek
ftset
ftslice
ftslicei
ftsr
gain
gainslider
gauss
gaussi
gausstrig
gbuzz
genarray
genarray_i
gendy
gendyc
gendyx
getcfg
getcol
getftargs
getrow
getseed
gogobel
grain
grain2
grain3
granule
gtadsr
gtf
guiro
harmon
harmon2
harmon3
harmon4
hdf5read
hdf5write
hilbert
hilbert2
hrtfearly
hrtfmove
hrtfmove2
hrtfreverb
hrtfstat
hsboscil
hvs1
hvs2
hvs3
hypot
i
ihold
imagecreate
imagefree
imagegetpixel
imageload
imagesave
imagesetpixel
imagesize
in
in32
inch
inh
init
initc14
initc21
initc7
inleta
inletf
inletk
inletkid
inletv
ino
inq
inrg
ins
insglobal
insremot
int
integ
interleave
interp
invalue
inx
inz
jacktransport
jitter
jitter2
joystick
jspline
k
la_i_add_mc
la_i_add_mr
la_i_add_vc
la_i_add_vr
la_i_assign_mc
la_i_assign_mr
la_i_assign_t
la_i_assign_vc
la_i_assign_vr
la_i_conjugate_mc
la_i_conjugate_mr
la_i_conjugate_vc
la_i_conjugate_vr
la_i_distance_vc
la_i_distance_vr
la_i_divide_mc
la_i_divide_mr
la_i_divide_vc
la_i_divide_vr
la_i_dot_mc
la_i_dot_mc_vc
la_i_dot_mr
la_i_dot_mr_vr
la_i_dot_vc
la_i_dot_vr
la_i_get_mc
la_i_get_mr
la_i_get_vc
la_i_get_vr
la_i_invert_mc
la_i_invert_mr
la_i_lower_solve_mc
la_i_lower_solve_mr
la_i_lu_det_mc
la_i_lu_det_mr
la_i_lu_factor_mc
la_i_lu_factor_mr
la_i_lu_solve_mc
la_i_lu_solve_mr
la_i_mc_create
la_i_mc_set
la_i_mr_create
la_i_mr_set
la_i_multiply_mc
la_i_multiply_mr
la_i_multiply_vc
la_i_multiply_vr
la_i_norm1_mc
la_i_norm1_mr
la_i_norm1_vc
la_i_norm1_vr
la_i_norm_euclid_mc
la_i_norm_euclid_mr
la_i_norm_euclid_vc
la_i_norm_euclid_vr
la_i_norm_inf_mc
la_i_norm_inf_mr
la_i_norm_inf_vc
la_i_norm_inf_vr
la_i_norm_max_mc
la_i_norm_max_mr
la_i_print_mc
la_i_print_mr
la_i_print_vc
la_i_print_vr
la_i_qr_eigen_mc
la_i_qr_eigen_mr
la_i_qr_factor_mc
la_i_qr_factor_mr
la_i_qr_sym_eigen_mc
la_i_qr_sym_eigen_mr
la_i_random_mc
la_i_random_mr
la_i_random_vc
la_i_random_vr
la_i_size_mc
la_i_size_mr
la_i_size_vc
la_i_size_vr
la_i_subtract_mc
la_i_subtract_mr
la_i_subtract_vc
la_i_subtract_vr
la_i_t_assign
la_i_trace_mc
la_i_trace_mr
la_i_transpose_mc
la_i_transpose_mr
la_i_upper_solve_mc
la_i_upper_solve_mr
la_i_vc_create
la_i_vc_set
la_i_vr_create
la_i_vr_set
la_k_a_assign
la_k_add_mc
la_k_add_mr
la_k_add_vc
la_k_add_vr
la_k_assign_a
la_k_assign_f
la_k_assign_mc
la_k_assign_mr
la_k_assign_t
la_k_assign_vc
la_k_assign_vr
la_k_conjugate_mc
la_k_conjugate_mr
la_k_conjugate_vc
la_k_conjugate_vr
la_k_current_f
la_k_current_vr
la_k_distance_vc
la_k_distance_vr
la_k_divide_mc
la_k_divide_mr
la_k_divide_vc
la_k_divide_vr
la_k_dot_mc
la_k_dot_mc_vc
la_k_dot_mr
la_k_dot_mr_vr
la_k_dot_vc
la_k_dot_vr
la_k_f_assign
la_k_get_mc
la_k_get_mr
la_k_get_vc
la_k_get_vr
la_k_invert_mc
la_k_invert_mr
la_k_lower_solve_mc
la_k_lower_solve_mr
la_k_lu_det_mc
la_k_lu_det_mr
la_k_lu_factor_mc
la_k_lu_factor_mr
la_k_lu_solve_mc
la_k_lu_solve_mr
la_k_mc_set
la_k_mr_set
la_k_multiply_mc
la_k_multiply_mr
la_k_multiply_vc
la_k_multiply_vr
la_k_norm1_mc
la_k_norm1_mr
la_k_norm1_vc
la_k_norm1_vr
la_k_norm_euclid_mc
la_k_norm_euclid_mr
la_k_norm_euclid_vc
la_k_norm_euclid_vr
la_k_norm_inf_mc
la_k_norm_inf_mr
la_k_norm_inf_vc
la_k_norm_inf_vr
la_k_norm_max_mc
la_k_norm_max_mr
la_k_qr_eigen_mc
la_k_qr_eigen_mr
la_k_qr_factor_mc
la_k_qr_factor_mr
la_k_qr_sym_eigen_mc
la_k_qr_sym_eigen_mr
la_k_random_mc
la_k_random_mr
la_k_random_vc
la_k_random_vr
la_k_subtract_mc
la_k_subtract_mr
la_k_subtract_vc
la_k_subtract_vr
la_k_t_assign
la_k_trace_mc
la_k_trace_mr
la_k_upper_solve_mc
la_k_upper_solve_mr
la_k_vc_set
la_k_vr_set
lag
lagud
lastcycle
lenarray
lfo
lfsr
limit
limit1
lincos
line
linen
linenr
lineto
link_beat_force
link_beat_get
link_beat_request
link_create
link_enable
link_is_enabled
link_metro
link_peers
link_tempo_get
link_tempo_set
linlin
linrand
linseg
linsegb
linsegr
liveconv
locsend
locsig
log
log10
log2
logbtwo
logcurve
loopseg
loopsegp
looptseg
loopxseg
lorenz
loscil
loscil3
loscil3phs
loscilphs
loscilx
lowpass2
lowres
lowresx
lpcanal
lpcfilter
lpf18
lpform
lpfreson
lphasor
lpinterp
lposcil
lposcil3
lposcila
lposcilsa
lposcilsa2
lpread
lpreson
lpshold
lpsholdp
lpslot
lufs
mac
maca
madsr
mags
mandel
mandol
maparray
maparray_i
marimba
massign
max
max_k
maxabs
maxabsaccum
maxaccum
maxalloc
maxarray
mclock
mdelay
median
mediank
metro
metro2
metrobpm
mfb
midglobal
midiarp
midic14
midic21
midic7
midichannelaftertouch
midichn
midicontrolchange
midictrl
mididefault
midifilestatus
midiin
midinoteoff
midinoteoncps
midinoteonkey
midinoteonoct
midinoteonpch
midion
midion2
midiout
midiout_i
midipgm
midipitchbend
midipolyaftertouch
midiprogramchange
miditempo
midremot
min
minabs
minabsaccum
minaccum
minarray
mincer
mirror
mode
modmatrix
monitor
moog
moogladder
moogladder2
moogvcf
moogvcf2
moscil
mp3bitrate
mp3in
mp3len
mp3nchnls
mp3out
mp3scal
mp3sr
mpulse
mrtmsg
ms2st
mtof
mton
multitap
mute
mvchpf
mvclpf1
mvclpf2
mvclpf3
mvclpf4
mvmfilter
mxadsr
nchnls_hw
nestedap
nlalp
nlfilt
nlfilt2
noise
noteoff
noteon
noteondur
noteondur2
notnum
nreverb
nrpn
nsamp
nstance
nstrnum
nstrstr
ntof
ntom
ntrpol
nxtpow2
octave
octcps
octmidi
octmidib
octmidinn
octpch
olabuffer
oscbnk
oscil
oscil1
oscil1i
oscil3
oscili
oscilikt
osciliktp
oscilikts
osciln
oscils
oscilx
out
out32
outall
outc
outch
outh
outiat
outic
outic14
outipat
outipb
outipc
outkat
outkc
outkc14
outkpat
outkpb
outkpc
outleta
outletf
outletk
outletkid
outletv
outo
outq
outq1
outq2
outq3
outq4
outrg
outs
outs1
outs2
outvalue
outx
outz
p
p5gconnect
p5gdata
pan
pan2
pareq
part2txt
partials
partikkel
partikkelget
partikkelset
partikkelsync
passign
paulstretch
pcauchy
pchbend
pchmidi
pchmidib
pchmidinn
pchoct
pchtom
pconvolve
pcount
pdclip
pdhalf
pdhalfy
peak
pgmassign
pgmchn
phaser1
phaser2
phasor
phasorbnk
phs
pindex
pinker
pinkish
pitch
pitchac
pitchamdf
planet
platerev
plltrack
pluck
poisson
pol2rect
polyaft
polynomial
port
portk
poscil
poscil3
pow
powershape
powoftwo
pows
prealloc
prepiano
print
print_type
printarray
printf
printf_i
printk
printk2
printks
printks2
println
prints
printsk
product
pset
ptablew
ptrack
puts
pvadd
pvbufread
pvcross
pvinterp
pvoc
pvread
pvs2array
pvs2tab
pvsadsyn
pvsanal
pvsarp
pvsbandp
pvsbandr
pvsbandwidth
pvsbin
pvsblur
pvsbuffer
pvsbufread
pvsbufread2
pvscale
pvscent
pvsceps
pvscfs
pvscross
pvsdemix
pvsdiskin
pvsdisp
pvsenvftw
pvsfilter
pvsfread
pvsfreeze
pvsfromarray
pvsftr
pvsftw
pvsfwrite
pvsgain
pvsgendy
pvshift
pvsifd
pvsin
pvsinfo
pvsinit
pvslock
pvslpc
pvsmaska
pvsmix
pvsmooth
pvsmorph
pvsosc
pvsout
pvspitch
pvstanal
pvstencil
pvstrace
pvsvoc
pvswarp
pvsynth
pwd
pyassign
pyassigni
pyassignt
pycall
pycall1
pycall1i
pycall1t
pycall2
pycall2i
pycall2t
pycall3
pycall3i
pycall3t
pycall4
pycall4i
pycall4t
pycall5
pycall5i
pycall5t
pycall6
pycall6i
pycall6t
pycall7
pycall7i
pycall7t
pycall8
pycall8i
pycall8t
pycalli
pycalln
pycallni
pycallt
pyeval
pyevali
pyevalt
pyexec
pyexeci
pyexect
pyinit
pylassign
pylassigni
pylassignt
pylcall
pylcall1
pylcall1i
pylcall1t
pylcall2
pylcall2i
pylcall2t
pylcall3
pylcall3i
pylcall3t
pylcall4
pylcall4i
pylcall4t
pylcall5
pylcall5i
pylcall5t
pylcall6
pylcall6i
pylcall6t
pylcall7
pylcall7i
pylcall7t
pylcall8
pylcall8i
pylcall8t
pylcalli
pylcalln
pylcallni
pylcallt
pyleval
pylevali
pylevalt
pylexec
pylexeci
pylexect
pylrun
pylruni
pylrunt
pyrun
pyruni
pyrunt
qinf
qnan
r2c
rand
randc
randh
randi
random
randomh
randomi
rbjeq
readclock
readf
readfi
readk
readk2
readk3
readk4
readks
readscore
readscratch
rect2pol
release
remoteport
remove
repluck
reshapearray
reson
resonbnk
resonk
resonr
resonx
resonxk
resony
resonz
resyn
reverb
reverb2
reverbsc
rewindscore
rezzy
rfft
rifft
rms
rnd
rnd31
rndseed
round
rspline
rtclock
s16b14
s32b14
samphold
sandpaper
sc_lag
sc_lagud
sc_phasor
sc_trig
scale
scale2
scalearray
scanhammer
scanmap
scans
scansmap
scantable
scanu
scanu2
schedkwhen
schedkwhennamed
schedule
schedulek
schedwhen
scoreline
scoreline_i
seed
sekere
select
semitone
sense
sensekey
seqtime
seqtime2
sequ
sequstate
serialBegin
serialEnd
serialFlush
serialPrint
serialRead
serialWrite
serialWrite_i
setcol
setctrl
setksmps
setrow
setscorepos
sfilist
sfinstr
sfinstr3
sfinstr3m
sfinstrm
sfload
sflooper
sfpassign
sfplay
sfplay3
sfplay3m
sfplaym
sfplist
sfpreset
shaker
shiftin
shiftout
signum
sin
sinh
sininv
sinsyn
skf
sleighbells
slicearray
slicearray_i
slider16
slider16f
slider16table
slider16tablef
slider32
slider32f
slider32table
slider32tablef
slider64
slider64f
slider64table
slider64tablef
slider8
slider8f
slider8table
slider8tablef
sliderKawai
sndloop
sndwarp
sndwarpst
sockrecv
sockrecvs
socksend
socksends
sorta
sortd
soundin
space
spat3d
spat3di
spat3dt
spdist
spf
splitrig
sprintf
sprintfk
spsend
sqrt
squinewave
st2ms
statevar
sterrain
stix
strcat
strcatk
strchar
strchark
strcmp
strcmpk
strcpy
strcpyk
strecv
streson
strfromurl
strget
strindex
strindexk
string2array
strlen
strlenk
strlower
strlowerk
strrindex
strrindexk
strset
strstrip
strsub
strsubk
strtod
strtodk
strtol
strtolk
strupper
strupperk
stsend
subinstr
subinstrinit
sum
sumarray
svfilter
svn
syncgrain
syncloop
syncphasor
system
system_i
tab
tab2array
tab2pvs
tab_i
tabifd
table
table3
table3kt
tablecopy
tablefilter
tablefilteri
tablegpw
tablei
tableicopy
tableigpw
tableikt
tableimix
tablekt
tablemix
tableng
tablera
tableseg
tableshuffle
tableshufflei
tablew
tablewa
tablewkt
tablexkt
tablexseg
tabmorph
tabmorpha
tabmorphak
tabmorphi
tabplay
tabrec
tabsum
tabw
tabw_i
tambourine
tan
tanh
taninv
taninv2
tbvcf
tempest
tempo
temposcal
tempoval
timedseq
timeinstk
timeinsts
timek
times
tival
tlineto
tone
tonek
tonex
tradsyn
trandom
transeg
transegb
transegr
trcross
trfilter
trhighest
trigExpseg
trigLinseg
trigexpseg
trigger
trighold
triglinseg
trigphasor
trigseq
trim
trim_i
trirand
trlowest
trmix
trscale
trshift
trsplit
turnoff
turnoff2
turnoff2_i
turnoff3
turnon
tvconv
unirand
unwrap
upsamp
urandom
urd
vactrol
vadd
vadd_i
vaddv
vaddv_i
vaget
valpass
vaset
vbap
vbapg
vbapgmove
vbaplsinit
vbapmove
vbapz
vbapzmove
vcella
vclpf
vco
vco2
vco2ft
vco2ift
vco2init
vcomb
vcopy
vcopy_i
vdel_k
vdelay
vdelay3
vdelayk
vdelayx
vdelayxq
vdelayxs
vdelayxw
vdelayxwq
vdelayxws
vdivv
vdivv_i
vecdelay
veloc
vexp
vexp_i
vexpseg
vexpv
vexpv_i
vibes
vibr
vibrato
vincr
vlimit
vlinseg
vlowres
vmap
vmirror
vmult
vmult_i
vmultv
vmultv_i
voice
vosim
vphaseseg
vport
vpow
vpow_i
vpowv
vpowv_i
vps
vpvoc
vrandh
vrandi
vsubv
vsubv_i
vtaba
vtabi
vtabk
vtable1k
vtablea
vtablei
vtablek
vtablewa
vtablewi
vtablewk
vtabwa
vtabwi
vtabwk
vwrap
waveset
websocket
weibull
wgbow
wgbowedbar
wgbrass
wgclar
wgflute
wgpluck
wgpluck2
wguide1
wguide2
wiiconnect
wiidata
wiirange
wiisend
window
wrap
writescratch
wterrain
wterrain2
xadsr
xin
xout
xtratim
xyscale
zacl
zakinit
zamod
zar
zarg
zaw
zawm
zdf_1pole
zdf_1pole_mode
zdf_2pole
zdf_2pole_mode
zdf_ladder
zfilter2
zir
ziw
ziwm
zkcl
zkmod
zkr
zkw
zkwm
'''.split())

DEPRECATED_OPCODES = set('''
array
bformdec
bformenc
copy2ftab
copy2ttab
hrtfer
ktableseg
lentab
maxtab
mintab
pop
pop_f
ptable
ptable3
ptablei
ptableiw
push
push_f
scalet
sndload
soundout
soundouts
specaddm
specdiff
specdisp
specfilt
spechist
specptrk
specscal
specsum
spectrum
stack
sumtab
tabgen
tableiw
tabmap
tabmap_i
tabslice
tb0
tb0_init
tb1
tb10
tb10_init
tb11
tb11_init
tb12
tb12_init
tb13
tb13_init
tb14
tb14_init
tb15
tb15_init
tb1_init
tb2
tb2_init
tb3
tb3_init
tb4
tb4_init
tb5
tb5_init
tb6
tb6_init
tb7
tb7_init
tb8
tb8_init
tb9
tb9_init
vbap16
vbap4
vbap4move
vbap8
vbap8move
xscanmap
xscans
xscansmap
xscanu
xyin
'''.split())

# === NexusCore/openenv\Lib\site-packages\numpy\_core\arrayprint.py ===
"""Array printing function

$Id: arrayprint.py,v 1.9 2005/09/13 13:58:44 teoliphant Exp $

"""
__all__ = ["array2string", "array_str", "array_repr",
           "set_printoptions", "get_printoptions", "printoptions",
           "format_float_positional", "format_float_scientific"]
__docformat__ = 'restructuredtext'

#
# Written by Konrad Hinsen <hinsenk@ere.umontreal.ca>
# last revision: 1996-3-13
# modified by Jim Hugunin 1997-3-3 for repr's and str's (and other details)
# and by Perry Greenfield 2000-4-1 for numarray
# and by Travis Oliphant  2005-8-22 for numpy


# Note: Both scalartypes.c.src and arrayprint.py implement strs for numpy
# scalars but for different purposes. scalartypes.c.src has str/reprs for when
# the scalar is printed on its own, while arrayprint.py has strs for when
# scalars are printed inside an ndarray. Only the latter strs are currently
# user-customizable.

import functools
import numbers
import sys

try:
    from _thread import get_ident
except ImportError:
    from _dummy_thread import get_ident

import contextlib
import operator
import warnings

import numpy as np

from . import numerictypes as _nt
from .fromnumeric import any
from .multiarray import (
    array,
    datetime_as_string,
    datetime_data,
    dragon4_positional,
    dragon4_scientific,
    ndarray,
)
from .numeric import asarray, concatenate, errstate
from .numerictypes import complex128, flexible, float64, int_
from .overrides import array_function_dispatch, set_module
from .printoptions import format_options
from .umath import absolute, isfinite, isinf, isnat


def _make_options_dict(precision=None, threshold=None, edgeitems=None,
                       linewidth=None, suppress=None, nanstr=None, infstr=None,
                       sign=None, formatter=None, floatmode=None, legacy=None,
                       override_repr=None):
    """
    Make a dictionary out of the non-None arguments, plus conversion of
    *legacy* and sanity checks.
    """

    options = {k: v for k, v in list(locals().items()) if v is not None}

    if suppress is not None:
        options['suppress'] = bool(suppress)

    modes = ['fixed', 'unique', 'maxprec', 'maxprec_equal']
    if floatmode not in modes + [None]:
        raise ValueError("floatmode option must be one of " +
                         ", ".join(f'"{m}"' for m in modes))

    if sign not in [None, '-', '+', ' ']:
        raise ValueError("sign option must be one of ' ', '+', or '-'")

    if legacy is False:
        options['legacy'] = sys.maxsize
    elif legacy == False:  # noqa: E712
        warnings.warn(
            f"Passing `legacy={legacy!r}` is deprecated.",
            FutureWarning, stacklevel=3
        )
        options['legacy'] = sys.maxsize
    elif legacy == '1.13':
        options['legacy'] = 113
    elif legacy == '1.21':
        options['legacy'] = 121
    elif legacy == '1.25':
        options['legacy'] = 125
    elif legacy == '2.1':
        options['legacy'] = 201
    elif legacy == '2.2':
        options['legacy'] = 202
    elif legacy is None:
        pass  # OK, do nothing.
    else:
        warnings.warn(
            "legacy printing option can currently only be '1.13', '1.21', "
            "'1.25', '2.1', '2.2' or `False`", stacklevel=3)

    if threshold is not None:
        # forbid the bad threshold arg suggested by stack overflow, gh-12351
        if not isinstance(threshold, numbers.Number):
            raise TypeError("threshold must be numeric")
        if np.isnan(threshold):
            raise ValueError("threshold must be non-NAN, try "
                             "sys.maxsize for untruncated representation")

    if precision is not None:
        # forbid the bad precision arg as suggested by issue #18254
        try:
            options['precision'] = operator.index(precision)
        except TypeError as e:
            raise TypeError('precision must be an integer') from e

    return options


@set_module('numpy')
def set_printoptions(precision=None, threshold=None, edgeitems=None,
                     linewidth=None, suppress=None, nanstr=None,
                     infstr=None, formatter=None, sign=None, floatmode=None,
                     *, legacy=None, override_repr=None):
    """
    Set printing options.

    These options determine the way floating point numbers, arrays and
    other NumPy objects are displayed.

    Parameters
    ----------
    precision : int or None, optional
        Number of digits of precision for floating point output (default 8).
        May be None if `floatmode` is not `fixed`, to print as many digits as
        necessary to uniquely specify the value.
    threshold : int, optional
        Total number of array elements which trigger summarization
        rather than full repr (default 1000).
        To always use the full repr without summarization, pass `sys.maxsize`.
    edgeitems : int, optional
        Number of array items in summary at beginning and end of
        each dimension (default 3).
    linewidth : int, optional
        The number of characters per line for the purpose of inserting
        line breaks (default 75).
    suppress : bool, optional
        If True, always print floating point numbers using fixed point
        notation, in which case numbers equal to zero in the current precision
        will print as zero.  If False, then scientific notation is used when
        absolute value of the smallest number is < 1e-4 or the ratio of the
        maximum absolute value to the minimum is > 1e3. The default is False.
    nanstr : str, optional
        String representation of floating point not-a-number (default nan).
    infstr : str, optional
        String representation of floating point infinity (default inf).
    sign : string, either '-', '+', or ' ', optional
        Controls printing of the sign of floating-point types. If '+', always
        print the sign of positive values. If ' ', always prints a space
        (whitespace character) in the sign position of positive values.  If
        '-', omit the sign character of positive values. (default '-')

        .. versionchanged:: 2.0
             The sign parameter can now be an integer type, previously
             types were floating-point types.

    formatter : dict of callables, optional
        If not None, the keys should indicate the type(s) that the respective
        formatting function applies to.  Callables should return a string.
        Types that are not specified (by their corresponding keys) are handled
        by the default formatters.  Individual types for which a formatter
        can be set are:

        - 'bool'
        - 'int'
        - 'timedelta' : a `numpy.timedelta64`
        - 'datetime' : a `numpy.datetime64`
        - 'float'
        - 'longfloat' : 128-bit floats
        - 'complexfloat'
        - 'longcomplexfloat' : composed of two 128-bit floats
        - 'numpystr' : types `numpy.bytes_` and `numpy.str_`
        - 'object' : `np.object_` arrays

        Other keys that can be used to set a group of types at once are:

        - 'all' : sets all types
        - 'int_kind' : sets 'int'
        - 'float_kind' : sets 'float' and 'longfloat'
        - 'complex_kind' : sets 'complexfloat' and 'longcomplexfloat'
        - 'str_kind' : sets 'numpystr'
    floatmode : str, optional
        Controls the interpretation of the `precision` option for
        floating-point types. Can take the following values
        (default maxprec_equal):

        * 'fixed': Always print exactly `precision` fractional digits,
                even if this would print more or fewer digits than
                necessary to specify the value uniquely.
        * 'unique': Print the minimum number of fractional digits necessary
                to represent each value uniquely. Different elements may
                have a different number of digits. The value of the
                `precision` option is ignored.
        * 'maxprec': Print at most `precision` fractional digits, but if
                an element can be uniquely represented with fewer digits
                only print it with that many.
        * 'maxprec_equal': Print at most `precision` fractional digits,
                but if every element in the array can be uniquely
                represented with an equal number of fewer digits, use that
                many digits for all elements.
    legacy : string or `False`, optional
        If set to the string ``'1.13'`` enables 1.13 legacy printing mode. This
        approximates numpy 1.13 print output by including a space in the sign
        position of floats and different behavior for 0d arrays. This also
        enables 1.21 legacy printing mode (described below).

        If set to the string ``'1.21'`` enables 1.21 legacy printing mode. This
        approximates numpy 1.21 print output of complex structured dtypes
        by not inserting spaces after commas that separate fields and after
        colons.

        If set to ``'1.25'`` approximates printing of 1.25 which mainly means
        that numeric scalars are printed without their type information, e.g.
        as ``3.0`` rather than ``np.float64(3.0)``.

        If set to ``'2.1'``, shape information is not given when arrays are
        summarized (i.e., multiple elements replaced with ``...``).

        If set to ``'2.2'``, the transition to use scientific notation for
        printing ``np.float16`` and ``np.float32`` types may happen later or
        not at all for larger values.

        If set to `False`, disables legacy mode.

        Unrecognized strings will be ignored with a warning for forward
        compatibility.

        .. versionchanged:: 1.22.0
        .. versionchanged:: 2.2

    override_repr: callable, optional
        If set a passed function will be used for generating arrays' repr.
        Other options will be ignored.

    See Also
    --------
    get_printoptions, printoptions, array2string

    Notes
    -----
    `formatter` is always reset with a call to `set_printoptions`.

    Use `printoptions` as a context manager to set the values temporarily.

    Examples
    --------
    Floating point precision can be set:

    >>> import numpy as np
    >>> np.set_printoptions(precision=4)
    >>> np.array([1.123456789])
    [1.1235]

    Long arrays can be summarised:

    >>> np.set_printoptions(threshold=5)
    >>> np.arange(10)
    array([0, 1, 2, ..., 7, 8, 9], shape=(10,))

    Small results can be suppressed:

    >>> eps = np.finfo(float).eps
    >>> x = np.arange(4.)
    >>> x**2 - (x + eps)**2
    array([-4.9304e-32, -4.4409e-16,  0.0000e+00,  0.0000e+00])
    >>> np.set_printoptions(suppress=True)
    >>> x**2 - (x + eps)**2
    array([-0., -0.,  0.,  0.])

    A custom formatter can be used to display array elements as desired:

    >>> np.set_printoptions(formatter={'all':lambda x: 'int: '+str(-x)})
    >>> x = np.arange(3)
    >>> x
    array([int: 0, int: -1, int: -2])
    >>> np.set_printoptions()  # formatter gets reset
    >>> x
    array([0, 1, 2])

    To put back the default options, you can use:

    >>> np.set_printoptions(edgeitems=3, infstr='inf',
    ... linewidth=75, nanstr='nan', precision=8,
    ... suppress=False, threshold=1000, formatter=None)

    Also to temporarily override options, use `printoptions`
    as a context manager:

    >>> with np.printoptions(precision=2, suppress=True, threshold=5):
    ...     np.linspace(0, 10, 10)
    array([ 0.  ,  1.11,  2.22, ...,  7.78,  8.89, 10.  ], shape=(10,))

    """
    _set_printoptions(precision, threshold, edgeitems, linewidth, suppress,
                      nanstr, infstr, formatter, sign, floatmode,
                      legacy=legacy, override_repr=override_repr)


def _set_printoptions(precision=None, threshold=None, edgeitems=None,
                      linewidth=None, suppress=None, nanstr=None,
                      infstr=None, formatter=None, sign=None, floatmode=None,
                      *, legacy=None, override_repr=None):
    new_opt = _make_options_dict(precision, threshold, edgeitems, linewidth,
                                 suppress, nanstr, infstr, sign, formatter,
                                 floatmode, legacy)
    # formatter and override_repr are always reset
    new_opt['formatter'] = formatter
    new_opt['override_repr'] = override_repr

    updated_opt = format_options.get() | new_opt
    updated_opt.update(new_opt)

    if updated_opt['legacy'] == 113:
        updated_opt['sign'] = '-'

    return format_options.set(updated_opt)


@set_module('numpy')
def get_printoptions():
    """
    Return the current print options.

    Returns
    -------
    print_opts : dict
        Dictionary of current print options with keys

        - precision : int
        - threshold : int
        - edgeitems : int
        - linewidth : int
        - suppress : bool
        - nanstr : str
        - infstr : str
        - sign : str
        - formatter : dict of callables
        - floatmode : str
        - legacy : str or False

        For a full description of these options, see `set_printoptions`.

    See Also
    --------
    set_printoptions, printoptions

    Examples
    --------
    >>> import numpy as np

    >>> np.get_printoptions()
    {'edgeitems': 3, 'threshold': 1000, ..., 'override_repr': None}

    >>> np.get_printoptions()['linewidth']
    75
    >>> np.set_printoptions(linewidth=100)
    >>> np.get_printoptions()['linewidth']
    100

    """
    opts = format_options.get().copy()
    opts['legacy'] = {
        113: '1.13', 121: '1.21', 125: '1.25', 201: '2.1',
        202: '2.2', sys.maxsize: False,
    }[opts['legacy']]
    return opts


def _get_legacy_print_mode():
    """Return the legacy print mode as an int."""
    return format_options.get()['legacy']


@set_module('numpy')
@contextlib.contextmanager
def printoptions(*args, **kwargs):
    """Context manager for setting print options.

    Set print options for the scope of the `with` block, and restore the old
    options at the end. See `set_printoptions` for the full description of
    available options.

    Examples
    --------
    >>> import numpy as np

    >>> from numpy.testing import assert_equal
    >>> with np.printoptions(precision=2):
    ...     np.array([2.0]) / 3
    array([0.67])

    The `as`-clause of the `with`-statement gives the current print options:

    >>> with np.printoptions(precision=2) as opts:
    ...      assert_equal(opts, np.get_printoptions())

    See Also
    --------
    set_printoptions, get_printoptions

    """
    token = _set_printoptions(*args, **kwargs)

    try:
        yield get_printoptions()
    finally:
        format_options.reset(token)


def _leading_trailing(a, edgeitems, index=()):
    """
    Keep only the N-D corners (leading and trailing edges) of an array.

    Should be passed a base-class ndarray, since it makes no guarantees about
    preserving subclasses.
    """
    axis = len(index)
    if axis == a.ndim:
        return a[index]

    if a.shape[axis] > 2 * edgeitems:
        return concatenate((
            _leading_trailing(a, edgeitems, index + np.index_exp[:edgeitems]),
            _leading_trailing(a, edgeitems, index + np.index_exp[-edgeitems:])
        ), axis=axis)
    else:
        return _leading_trailing(a, edgeitems, index + np.index_exp[:])


def _object_format(o):
    """ Object arrays containing lists should be printed unambiguously """
    if type(o) is list:
        fmt = 'list({!r})'
    else:
        fmt = '{!r}'
    return fmt.format(o)

def repr_format(x):
    if isinstance(x, (np.str_, np.bytes_)):
        return repr(x.item())
    return repr(x)

def str_format(x):
    if isinstance(x, (np.str_, np.bytes_)):
        return str(x.item())
    return str(x)

def _get_formatdict(data, *, precision, floatmode, suppress, sign, legacy,
                    formatter, **kwargs):
    # note: extra arguments in kwargs are ignored

    # wrapped in lambdas to avoid taking a code path
    # with the wrong type of data
    formatdict = {
        'bool': lambda: BoolFormat(data),
        'int': lambda: IntegerFormat(data, sign),
        'float': lambda: FloatingFormat(
            data, precision, floatmode, suppress, sign, legacy=legacy),
        'longfloat': lambda: FloatingFormat(
            data, precision, floatmode, suppress, sign, legacy=legacy),
        'complexfloat': lambda: ComplexFloatingFormat(
            data, precision, floatmode, suppress, sign, legacy=legacy),
        'longcomplexfloat': lambda: ComplexFloatingFormat(
            data, precision, floatmode, suppress, sign, legacy=legacy),
        'datetime': lambda: DatetimeFormat(data, legacy=legacy),
        'timedelta': lambda: TimedeltaFormat(data),
        'object': lambda: _object_format,
        'void': lambda: str_format,
        'numpystr': lambda: repr_format}

    # we need to wrap values in `formatter` in a lambda, so that the interface
    # is the same as the above values.
    def indirect(x):
        return lambda: x

    if formatter is not None:
        fkeys = [k for k in formatter.keys() if formatter[k] is not None]
        if 'all' in fkeys:
            for key in formatdict.keys():
                formatdict[key] = indirect(formatter['all'])
        if 'int_kind' in fkeys:
            for key in ['int']:
                formatdict[key] = indirect(formatter['int_kind'])
        if 'float_kind' in fkeys:
            for key in ['float', 'longfloat']:
                formatdict[key] = indirect(formatter['float_kind'])
        if 'complex_kind' in fkeys:
            for key in ['complexfloat', 'longcomplexfloat']:
                formatdict[key] = indirect(formatter['complex_kind'])
        if 'str_kind' in fkeys:
            formatdict['numpystr'] = indirect(formatter['str_kind'])
        for key in formatdict.keys():
            if key in fkeys:
                formatdict[key] = indirect(formatter[key])

    return formatdict

def _get_format_function(data, **options):
    """
    find the right formatting function for the dtype_
    """
    dtype_ = data.dtype
    dtypeobj = dtype_.type
    formatdict = _get_formatdict(data, **options)
    if dtypeobj is None:
        return formatdict["numpystr"]()
    elif issubclass(dtypeobj, _nt.bool):
        return formatdict['bool']()
    elif issubclass(dtypeobj, _nt.integer):
        if issubclass(dtypeobj, _nt.timedelta64):
            return formatdict['timedelta']()
        else:
            return formatdict['int']()
    elif issubclass(dtypeobj, _nt.floating):
        if issubclass(dtypeobj, _nt.longdouble):
            return formatdict['longfloat']()
        else:
            return formatdict['float']()
    elif issubclass(dtypeobj, _nt.complexfloating):
        if issubclass(dtypeobj, _nt.clongdouble):
            return formatdict['longcomplexfloat']()
        else:
            return formatdict['complexfloat']()
    elif issubclass(dtypeobj, (_nt.str_, _nt.bytes_)):
        return formatdict['numpystr']()
    elif issubclass(dtypeobj, _nt.datetime64):
        return formatdict['datetime']()
    elif issubclass(dtypeobj, _nt.object_):
        return formatdict['object']()
    elif issubclass(dtypeobj, _nt.void):
        if dtype_.names is not None:
            return StructuredVoidFormat.from_data(data, **options)
        else:
            return formatdict['void']()
    else:
        return formatdict['numpystr']()


def _recursive_guard(fillvalue='...'):
    """
    Like the python 3.2 reprlib.recursive_repr, but forwards *args and **kwargs

    Decorates a function such that if it calls itself with the same first
    argument, it returns `fillvalue` instead of recursing.

    Largely copied from reprlib.recursive_repr
    """

    def decorating_function(f):
        repr_running = set()

        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            key = id(self), get_ident()
            if key in repr_running:
                return fillvalue
            repr_running.add(key)
            try:
                return f(self, *args, **kwargs)
            finally:
                repr_running.discard(key)

        return wrapper

    return decorating_function


# gracefully handle recursive calls, when object arrays contain themselves
@_recursive_guard()
def _array2string(a, options, separator=' ', prefix=""):
    # The formatter __init__s in _get_format_function cannot deal with
    # subclasses yet, and we also need to avoid recursion issues in
    # _formatArray with subclasses which return 0d arrays in place of scalars
    data = asarray(a)
    if a.shape == ():
        a = data

    if a.size > options['threshold']:
        summary_insert = "..."
        data = _leading_trailing(data, options['edgeitems'])
    else:
        summary_insert = ""

    # find the right formatting function for the array
    format_function = _get_format_function(data, **options)

    # skip over "["
    next_line_prefix = " "
    # skip over array(
    next_line_prefix += " " * len(prefix)

    lst = _formatArray(a, format_function, options['linewidth'],
                       next_line_prefix, separator, options['edgeitems'],
                       summary_insert, options['legacy'])
    return lst


def _array2string_dispatcher(
        a, max_line_width=None, precision=None,
        suppress_small=None, separator=None, prefix=None,
        style=None, formatter=None, threshold=None,
        edgeitems=None, sign=None, floatmode=None, suffix=None,
        *, legacy=None):
    return (a,)


@array_function_dispatch(_array2string_dispatcher, module='numpy')
def array2string(a, max_line_width=None, precision=None,
                 suppress_small=None, separator=' ', prefix="",
                 style=np._NoValue, formatter=None, threshold=None,
                 edgeitems=None, sign=None, floatmode=None, suffix="",
                 *, legacy=None):
    """
    Return a string representation of an array.

    Parameters
    ----------
    a : ndarray
        Input array.
    max_line_width : int, optional
        Inserts newlines if text is longer than `max_line_width`.
        Defaults to ``numpy.get_printoptions()['linewidth']``.
    precision : int or None, optional
        Floating point precision.
        Defaults to ``numpy.get_printoptions()['precision']``.
    suppress_small : bool, optional
        Represent numbers "very close" to zero as zero; default is False.
        Very close is defined by precision: if the precision is 8, e.g.,
        numbers smaller (in absolute value) than 5e-9 are represented as
        zero.
        Defaults to ``numpy.get_printoptions()['suppress']``.
    separator : str, optional
        Inserted between elements.
    prefix : str, optional
    suffix : str, optional
        The length of the prefix and suffix strings are used to respectively
        align and wrap the output. An array is typically printed as::

          prefix + array2string(a) + suffix

        The output is left-padded by the length of the prefix string, and
        wrapping is forced at the column ``max_line_width - len(suffix)``.
        It should be noted that the content of prefix and suffix strings are
        not included in the output.
    style : _NoValue, optional
        Has no effect, do not use.

        .. deprecated:: 1.14.0
    formatter : dict of callables, optional
        If not None, the keys should indicate the type(s) that the respective
        formatting function applies to.  Callables should return a string.
        Types that are not specified (by their corresponding keys) are handled
        by the default formatters.  Individual types for which a formatter
        can be set are:

        - 'bool'
        - 'int'
        - 'timedelta' : a `numpy.timedelta64`
        - 'datetime' : a `numpy.datetime64`
        - 'float'
        - 'longfloat' : 128-bit floats
        - 'complexfloat'
        - 'longcomplexfloat' : composed of two 128-bit floats
        - 'void' : type `numpy.void`
        - 'numpystr' : types `numpy.bytes_` and `numpy.str_`

        Other keys that can be used to set a group of types at once are:

        - 'all' : sets all types
        - 'int_kind' : sets 'int'
        - 'float_kind' : sets 'float' and 'longfloat'
        - 'complex_kind' : sets 'complexfloat' and 'longcomplexfloat'
        - 'str_kind' : sets 'numpystr'
    threshold : int, optional
        Total number of array elements which trigger summarization
        rather than full repr.
        Defaults to ``numpy.get_printoptions()['threshold']``.
    edgeitems : int, optional
        Number of array items in summary at beginning and end of
        each dimension.
        Defaults to ``numpy.get_printoptions()['edgeitems']``.
    sign : string, either '-', '+', or ' ', optional
        Controls printing of the sign of floating-point types. If '+', always
        print the sign of positive values. If ' ', always prints a space
        (whitespace character) in the sign position of positive values.  If
        '-', omit the sign character of positive values.
        Defaults to ``numpy.get_printoptions()['sign']``.

        .. versionchanged:: 2.0
             The sign parameter can now be an integer type, previously
             types were floating-point types.

    floatmode : str, optional
        Controls the interpretation of the `precision` option for
        floating-point types.
        Defaults to ``numpy.get_printoptions()['floatmode']``.
        Can take the following values:

        - 'fixed': Always print exactly `precision` fractional digits,
          even if this would print more or fewer digits than
          necessary to specify the value uniquely.
        - 'unique': Print the minimum number of fractional digits necessary
          to represent each value uniquely. Different elements may
          have a different number of digits.  The value of the
          `precision` option is ignored.
        - 'maxprec': Print at most `precision` fractional digits, but if
          an element can be uniquely represented with fewer digits
          only print it with that many.
        - 'maxprec_equal': Print at most `precision` fractional digits,
          but if every element in the array can be uniquely
          represented with an equal number of fewer digits, use that
          many digits for all elements.
    legacy : string or `False`, optional
        If set to the string ``'1.13'`` enables 1.13 legacy printing mode. This
        approximates numpy 1.13 print output by including a space in the sign
        position of floats and different behavior for 0d arrays. If set to
        `False`, disables legacy mode. Unrecognized strings will be ignored
        with a warning for forward compatibility.

    Returns
    -------
    array_str : str
        String representation of the array.

    Raises
    ------
    TypeError
        if a callable in `formatter` does not return a string.

    See Also
    --------
    array_str, array_repr, set_printoptions, get_printoptions

    Notes
    -----
    If a formatter is specified for a certain type, the `precision` keyword is
    ignored for that type.

    This is a very flexible function; `array_repr` and `array_str` are using
    `array2string` internally so keywords with the same name should work
    identically in all three functions.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1e-16,1,2,3])
    >>> np.array2string(x, precision=2, separator=',',
    ...                       suppress_small=True)
    '[0.,1.,2.,3.]'

    >>> x  = np.arange(3.)
    >>> np.array2string(x, formatter={'float_kind':lambda x: "%.2f" % x})
    '[0.00 1.00 2.00]'

    >>> x  = np.arange(3)
    >>> np.array2string(x, formatter={'int':lambda x: hex(x)})
    '[0x0 0x1 0x2]'

    """

    overrides = _make_options_dict(precision, threshold, edgeitems,
                                   max_line_width, suppress_small, None, None,
                                   sign, formatter, floatmode, legacy)
    options = format_options.get().copy()
    options.update(overrides)

    if options['legacy'] <= 113:
        if style is np._NoValue:
            style = repr

        if a.shape == () and a.dtype.names is None:
            return style(a.item())
    elif style is not np._NoValue:
        # Deprecation 11-9-2017  v1.14
        warnings.warn("'style' argument is deprecated and no longer functional"
                      " except in 1.13 'legacy' mode",
                      DeprecationWarning, stacklevel=2)

    if options['legacy'] > 113:
        options['linewidth'] -= len(suffix)

    # treat as a null array if any of shape elements == 0
    if a.size == 0:
        return "[]"

    return _array2string(a, options, separator, prefix)


def _extendLine(s, line, word, line_width, next_line_prefix, legacy):
    needs_wrap = len(line) + len(word) > line_width
    if legacy > 113:
        # don't wrap lines if it won't help
        if len(line) <= len(next_line_prefix):
            needs_wrap = False

    if needs_wrap:
        s += line.rstrip() + "\n"
        line = next_line_prefix
    line += word
    return s, line


def _extendLine_pretty(s, line, word, line_width, next_line_prefix, legacy):
    """
    Extends line with nicely formatted (possibly multi-line) string ``word``.
    """
    words = word.splitlines()
    if len(words) == 1 or legacy <= 113:
        return _extendLine(s, line, word, line_width, next_line_prefix, legacy)

    max_word_length = max(len(word) for word in words)
    if (len(line) + max_word_length > line_width and
            len(line) > len(next_line_prefix)):
        s += line.rstrip() + '\n'
        line = next_line_prefix + words[0]
        indent = next_line_prefix
    else:
        indent = len(line) * ' '
        line += words[0]

    for word in words[1::]:
        s += line.rstrip() + '\n'
        line = indent + word

    suffix_length = max_word_length - len(words[-1])
    line += suffix_length * ' '

    return s, line

def _formatArray(a, format_function, line_width, next_line_prefix,
                 separator, edge_items, summary_insert, legacy):
    """formatArray is designed for two modes of operation:

    1. Full output

    2. Summarized output

    """
    def recurser(index, hanging_indent, curr_width):
        """
        By using this local function, we don't need to recurse with all the
        arguments. Since this function is not created recursively, the cost is
        not significant
        """
        axis = len(index)
        axes_left = a.ndim - axis

        if axes_left == 0:
            return format_function(a[index])

        # when recursing, add a space to align with the [ added, and reduce the
        # length of the line by 1
        next_hanging_indent = hanging_indent + ' '
        if legacy <= 113:
            next_width = curr_width
        else:
            next_width = curr_width - len(']')

        a_len = a.shape[axis]
        show_summary = summary_insert and 2 * edge_items < a_len
        if show_summary:
            leading_items = edge_items
            trailing_items = edge_items
        else:
            leading_items = 0
            trailing_items = a_len

        # stringify the array with the hanging indent on the first line too
        s = ''

        # last axis (rows) - wrap elements if they would not fit on one line
        if axes_left == 1:
            # the length up until the beginning of the separator / bracket
            if legacy <= 113:
                elem_width = curr_width - len(separator.rstrip())
            else:
                elem_width = curr_width - max(
                    len(separator.rstrip()), len(']')
                )

            line = hanging_indent
            for i in range(leading_items):
                word = recurser(index + (i,), next_hanging_indent, next_width)
                s, line = _extendLine_pretty(
                    s, line, word, elem_width, hanging_indent, legacy)
                line += separator

            if show_summary:
                s, line = _extendLine(
                    s, line, summary_insert, elem_width, hanging_indent, legacy
                )
                if legacy <= 113:
                    line += ", "
                else:
                    line += separator

            for i in range(trailing_items, 1, -1):
                word = recurser(index + (-i,), next_hanging_indent, next_width)
                s, line = _extendLine_pretty(
                    s, line, word, elem_width, hanging_indent, legacy)
                line += separator

            if legacy <= 113:
                # width of the separator is not considered on 1.13
                elem_width = curr_width
            word = recurser(index + (-1,), next_hanging_indent, next_width)
            s, line = _extendLine_pretty(
                s, line, word, elem_width, hanging_indent, legacy)

            s += line

        # other axes - insert newlines between rows
        else:
            s = ''
            line_sep = separator.rstrip() + '\n' * (axes_left - 1)

            for i in range(leading_items):
                nested = recurser(
                    index + (i,), next_hanging_indent, next_width
                )
                s += hanging_indent + nested + line_sep

            if show_summary:
                if legacy <= 113:
                    # trailing space, fixed nbr of newlines,
                    # and fixed separator
                    s += hanging_indent + summary_insert + ", \n"
                else:
                    s += hanging_indent + summary_insert + line_sep

            for i in range(trailing_items, 1, -1):
                nested = recurser(index + (-i,), next_hanging_indent,
                                  next_width)
                s += hanging_indent + nested + line_sep

            nested = recurser(index + (-1,), next_hanging_indent, next_width)
            s += hanging_indent + nested

        # remove the hanging indent, and wrap in []
        s = '[' + s[len(hanging_indent):] + ']'
        return s

    try:
        # invoke the recursive part with an initial index and prefix
        return recurser(index=(),
                        hanging_indent=next_line_prefix,
                        curr_width=line_width)
    finally:
        # recursive closures have a cyclic reference to themselves, which
        # requires gc to collect (gh-10620). To avoid this problem, for
        # performance and PyPy friendliness, we break the cycle:
        recurser = None

def _none_or_positive_arg(x, name):
    if x is None:
        return -1
    if x < 0:
        raise ValueError(f"{name} must be >= 0")
    return x

class FloatingFormat:
    """ Formatter for subtypes of np.floating """
    def __init__(self, data, precision, floatmode, suppress_small, sign=False,
                 *, legacy=None):
        # for backcompatibility, accept bools
        if isinstance(sign, bool):
            sign = '+' if sign else '-'

        self._legacy = legacy
        if self._legacy <= 113:
            # when not 0d, legacy does not support '-'
            if data.shape != () and sign == '-':
                sign = ' '

        self.floatmode = floatmode
        if floatmode == 'unique':
            self.precision = None
        else:
            self.precision = precision

        self.precision = _none_or_positive_arg(self.precision, 'precision')

        self.suppress_small = suppress_small
        self.sign = sign
        self.exp_format = False
        self.large_exponent = False
        self.fillFormat(data)

    def fillFormat(self, data):
        # only the finite values are used to compute the number of digits
        finite_vals = data[isfinite(data)]

        # choose exponential mode based on the non-zero finite values:
        abs_non_zero = absolute(finite_vals[finite_vals != 0])
        if len(abs_non_zero) != 0:
            max_val = np.max(abs_non_zero)
            min_val = np.min(abs_non_zero)
            if self._legacy <= 202:
                exp_cutoff_max = 1.e8
            else:
                # consider data type while deciding the max cutoff for exp format
                exp_cutoff_max = 10.**min(8, np.finfo(data.dtype).precision)
            with errstate(over='ignore'):  # division can overflow
                if max_val >= exp_cutoff_max or (not self.suppress_small and
                        (min_val < 0.0001 or max_val / min_val > 1000.)):
                    self.exp_format = True

        # do a first pass of printing all the numbers, to determine sizes
        if len(finite_vals) == 0:
            self.pad_left = 0
            self.pad_right = 0
            self.trim = '.'
            self.exp_size = -1
            self.unique = True
            self.min_digits = None
        elif self.exp_format:
            trim, unique = '.', True
            if self.floatmode == 'fixed' or self._legacy <= 113:
                trim, unique = 'k', False
            strs = (dragon4_scientific(x, precision=self.precision,
                               unique=unique, trim=trim, sign=self.sign == '+')
                    for x in finite_vals)
            frac_strs, _, exp_strs = zip(*(s.partition('e') for s in strs))
            int_part, frac_part = zip(*(s.split('.') for s in frac_strs))
            self.exp_size = max(len(s) for s in exp_strs) - 1

            self.trim = 'k'
            self.precision = max(len(s) for s in frac_part)
            self.min_digits = self.precision
            self.unique = unique

            # for back-compat with np 1.13, use 2 spaces & sign and full prec
            if self._legacy <= 113:
                self.pad_left = 3
            else:
                # this should be only 1 or 2. Can be calculated from sign.
                self.pad_left = max(len(s) for s in int_part)
            # pad_right is only needed for nan length calculation
            self.pad_right = self.exp_size + 2 + self.precision
        else:
            trim, unique = '.', True
            if self.floatmode == 'fixed':
                trim, unique = 'k', False
            strs = (dragon4_positional(x, precision=self.precision,
                                       fractional=True,
                                       unique=unique, trim=trim,
                                       sign=self.sign == '+')
                    for x in finite_vals)
            int_part, frac_part = zip(*(s.split('.') for s in strs))
            if self._legacy <= 113:
                self.pad_left = 1 + max(len(s.lstrip('-+')) for s in int_part)
            else:
                self.pad_left = max(len(s) for s in int_part)
            self.pad_right = max(len(s) for s in frac_part)
            self.exp_size = -1
            self.unique = unique

            if self.floatmode in ['fixed', 'maxprec_equal']:
                self.precision = self.min_digits = self.pad_right
                self.trim = 'k'
            else:
                self.trim = '.'
                self.min_digits = 0

        if self._legacy > 113:
            # account for sign = ' ' by adding one to pad_left
            if self.sign == ' ' and not any(np.signbit(finite_vals)):
                self.pad_left += 1

        # if there are non-finite values, may need to increase pad_left
        if data.size != finite_vals.size:
            neginf = self.sign != '-' or any(data[isinf(data)] < 0)
            offset = self.pad_right + 1  # +1 for decimal pt
            current_options = format_options.get()
            self.pad_left = max(
                self.pad_left, len(current_options['nanstr']) - offset,
                len(current_options['infstr']) + neginf - offset
            )

    def __call__(self, x):
        if not np.isfinite(x):
            with errstate(invalid='ignore'):
                current_options = format_options.get()
                if np.isnan(x):
                    sign = '+' if self.sign == '+' else ''
                    ret = sign + current_options['nanstr']
                else:  # isinf
                    sign = '-' if x < 0 else '+' if self.sign == '+' else ''
                    ret = sign + current_options['infstr']
                return ' ' * (
                    self.pad_left + self.pad_right + 1 - len(ret)
                ) + ret

        if self.exp_format:
            return dragon4_scientific(x,
                                      precision=self.precision,
                                      min_digits=self.min_digits,
                                      unique=self.unique,
                                      trim=self.trim,
                                      sign=self.sign == '+',
                                      pad_left=self.pad_left,
                                      exp_digits=self.exp_size)
        else:
            return dragon4_positional(x,
                                      precision=self.precision,
                                      min_digits=self.min_digits,
                                      unique=self.unique,
                                      fractional=True,
                                      trim=self.trim,
                                      sign=self.sign == '+',
                                      pad_left=self.pad_left,
                                      pad_right=self.pad_right)


@set_module('numpy')
def format_float_scientific(x, precision=None, unique=True, trim='k',
                            sign=False, pad_left=None, exp_digits=None,
                            min_digits=None):
    """
    Format a floating-point scalar as a decimal string in scientific notation.

    Provides control over rounding, trimming and padding. Uses and assumes
    IEEE unbiased rounding. Uses the "Dragon4" algorithm.

    Parameters
    ----------
    x : python float or numpy floating scalar
        Value to format.
    precision : non-negative integer or None, optional
        Maximum number of digits to print. May be None if `unique` is
        `True`, but must be an integer if unique is `False`.
    unique : boolean, optional
        If `True`, use a digit-generation strategy which gives the shortest
        representation which uniquely identifies the floating-point number from
        other values of the same type, by judicious rounding. If `precision`
        is given fewer digits than necessary can be printed. If `min_digits`
        is given more can be printed, in which cases the last digit is rounded
        with unbiased rounding.
        If `False`, digits are generated as if printing an infinite-precision
        value and stopping after `precision` digits, rounding the remaining
        value with unbiased rounding
    trim : one of 'k', '.', '0', '-', optional
        Controls post-processing trimming of trailing digits, as follows:

        * 'k' : keep trailing zeros, keep decimal point (no trimming)
        * '.' : trim all trailing zeros, leave decimal point
        * '0' : trim all but the zero before the decimal point. Insert the
          zero if it is missing.
        * '-' : trim trailing zeros and any trailing decimal point
    sign : boolean, optional
        Whether to show the sign for positive values.
    pad_left : non-negative integer, optional
        Pad the left side of the string with whitespace until at least that
        many characters are to the left of the decimal point.
    exp_digits : non-negative integer, optional
        Pad the exponent with zeros until it contains at least this
        many digits. If omitted, the exponent will be at least 2 digits.
    min_digits : non-negative integer or None, optional
        Minimum number of digits to print. This only has an effect for
        `unique=True`. In that case more digits than necessary to uniquely
        identify the value may be printed and rounded unbiased.

        .. versionadded:: 1.21.0

    Returns
    -------
    rep : string
        The string representation of the floating point value

    See Also
    --------
    format_float_positional

    Examples
    --------
    >>> import numpy as np
    >>> np.format_float_scientific(np.float32(np.pi))
    '3.1415927e+00'
    >>> s = np.float32(1.23e24)
    >>> np.format_float_scientific(s, unique=False, precision=15)
    '1.230000071797338e+24'
    >>> np.format_float_scientific(s, exp_digits=4)
    '1.23e+0024'
    """
    precision = _none_or_positive_arg(precision, 'precision')
    pad_left = _none_or_positive_arg(pad_left, 'pad_left')
    exp_digits = _none_or_positive_arg(exp_digits, 'exp_digits')
    min_digits = _none_or_positive_arg(min_digits, 'min_digits')
    if min_digits > 0 and precision > 0 and min_digits > precision:
        raise ValueError("min_digits must be less than or equal to precision")
    return dragon4_scientific(x, precision=precision, unique=unique,
                              trim=trim, sign=sign, pad_left=pad_left,
                              exp_digits=exp_digits, min_digits=min_digits)


@set_module('numpy')
def format_float_positional(x, precision=None, unique=True,
                            fractional=True, trim='k', sign=False,
                            pad_left=None, pad_right=None, min_digits=None):
    """
    Format a floating-point scalar as a decimal string in positional notation.

    Provides control over rounding, trimming and padding. Uses and assumes
    IEEE unbiased rounding. Uses the "Dragon4" algorithm.

    Parameters
    ----------
    x : python float or numpy floating scalar
        Value to format.
    precision : non-negative integer or None, optional
        Maximum number of digits to print. May be None if `unique` is
        `True`, but must be an integer if unique is `False`.
    unique : boolean, optional
        If `True`, use a digit-generation strategy which gives the shortest
        representation which uniquely identifies the floating-point number from
        other values of the same type, by judicious rounding. If `precision`
        is given fewer digits than necessary can be printed, or if `min_digits`
        is given more can be printed, in which cases the last digit is rounded
        with unbiased rounding.
        If `False`, digits are generated as if printing an infinite-precision
        value and stopping after `precision` digits, rounding the remaining
        value with unbiased rounding
    fractional : boolean, optional
        If `True`, the cutoffs of `precision` and `min_digits` refer to the
        total number of digits after the decimal point, including leading
        zeros.
        If `False`, `precision` and `min_digits` refer to the total number of
        significant digits, before or after the decimal point, ignoring leading
        zeros.
    trim : one of 'k', '.', '0', '-', optional
        Controls post-processing trimming of trailing digits, as follows:

        * 'k' : keep trailing zeros, keep decimal point (no trimming)
        * '.' : trim all trailing zeros, leave decimal point
        * '0' : trim all but the zero before the decimal point. Insert the
          zero if it is missing.
        * '-' : trim trailing zeros and any trailing decimal point
    sign : boolean, optional
        Whether to show the sign for positive values.
    pad_left : non-negative integer, optional
        Pad the left side of the string with whitespace until at least that
        many characters are to the left of the decimal point.
    pad_right : non-negative integer, optional
        Pad the right side of the string with whitespace until at least that
        many characters are to the right of the decimal point.
    min_digits : non-negative integer or None, optional
        Minimum number of digits to print. Only has an effect if `unique=True`
        in which case additional digits past those necessary to uniquely
        identify the value may be printed, rounding the last additional digit.

        .. versionadded:: 1.21.0

    Returns
    -------
    rep : string
        The string representation of the floating point value

    See Also
    --------
    format_float_scientific

    Examples
    --------
    >>> import numpy as np
    >>> np.format_float_positional(np.float32(np.pi))
    '3.1415927'
    >>> np.format_float_positional(np.float16(np.pi))
    '3.14'
    >>> np.format_float_positional(np.float16(0.3))
    '0.3'
    >>> np.format_float_positional(np.float16(0.3), unique=False, precision=10)
    '0.3000488281'
    """
    precision = _none_or_positive_arg(precision, 'precision')
    pad_left = _none_or_positive_arg(pad_left, 'pad_left')
    pad_right = _none_or_positive_arg(pad_right, 'pad_right')
    min_digits = _none_or_positive_arg(min_digits, 'min_digits')
    if not fractional and precision == 0:
        raise ValueError("precision must be greater than 0 if "
                         "fractional=False")
    if min_digits > 0 and precision > 0 and min_digits > precision:
        raise ValueError("min_digits must be less than or equal to precision")
    return dragon4_positional(x, precision=precision, unique=unique,
                              fractional=fractional, trim=trim,
                              sign=sign, pad_left=pad_left,
                              pad_right=pad_right, min_digits=min_digits)

class IntegerFormat:
    def __init__(self, data, sign='-'):
        if data.size > 0:
            data_max = np.max(data)
            data_min = np.min(data)
            data_max_str_len = len(str(data_max))
            if sign == ' ' and data_min < 0:
                sign = '-'
            if data_max >= 0 and sign in "+ ":
                data_max_str_len += 1
            max_str_len = max(data_max_str_len,
                              len(str(data_min)))
        else:
            max_str_len = 0
        self.format = f'{{:{sign}{max_str_len}d}}'

    def __call__(self, x):
        return self.format.format(x)

class BoolFormat:
    def __init__(self, data, **kwargs):
        # add an extra space so " True" and "False" have the same length and
        # array elements align nicely when printed, except in 0d arrays
        self.truestr = ' True' if data.shape != () else 'True'

    def __call__(self, x):
        return self.truestr if x else "False"


class ComplexFloatingFormat:
    """ Formatter for subtypes of np.complexfloating """
    def __init__(self, x, precision, floatmode, suppress_small,
                 sign=False, *, legacy=None):
        # for backcompatibility, accept bools
        if isinstance(sign, bool):
            sign = '+' if sign else '-'

        floatmode_real = floatmode_imag = floatmode
        if legacy <= 113:
            floatmode_real = 'maxprec_equal'
            floatmode_imag = 'maxprec'

        self.real_format = FloatingFormat(
            x.real, precision, floatmode_real, suppress_small,
            sign=sign, legacy=legacy
        )
        self.imag_format = FloatingFormat(
            x.imag, precision, floatmode_imag, suppress_small,
            sign='+', legacy=legacy
        )

    def __call__(self, x):
        r = self.real_format(x.real)
        i = self.imag_format(x.imag)

        # add the 'j' before the terminal whitespace in i
        sp = len(i.rstrip())
        i = i[:sp] + 'j' + i[sp:]

        return r + i


class _TimelikeFormat:
    def __init__(self, data):
        non_nat = data[~isnat(data)]
        if len(non_nat) > 0:
            # Max str length of non-NaT elements
            max_str_len = max(len(self._format_non_nat(np.max(non_nat))),
                              len(self._format_non_nat(np.min(non_nat))))
        else:
            max_str_len = 0
        if len(non_nat) < data.size:
            # data contains a NaT
            max_str_len = max(max_str_len, 5)
        self._format = f'%{max_str_len}s'
        self._nat = "'NaT'".rjust(max_str_len)

    def _format_non_nat(self, x):
        # override in subclass
        raise NotImplementedError

    def __call__(self, x):
        if isnat(x):
            return self._nat
        else:
            return self._format % self._format_non_nat(x)


class DatetimeFormat(_TimelikeFormat):
    def __init__(self, x, unit=None, timezone=None, casting='same_kind',
                 legacy=False):
        # Get the unit from the dtype
        if unit is None:
            if x.dtype.kind == 'M':
                unit = datetime_data(x.dtype)[0]
            else:
                unit = 's'

        if timezone is None:
            timezone = 'naive'
        self.timezone = timezone
        self.unit = unit
        self.casting = casting
        self.legacy = legacy

        # must be called after the above are configured
        super().__init__(x)

    def __call__(self, x):
        if self.legacy <= 113:
            return self._format_non_nat(x)
        return super().__call__(x)

    def _format_non_nat(self, x):
        return "'%s'" % datetime_as_string(x,
                                    unit=self.unit,
                                    timezone=self.timezone,
                                    casting=self.casting)


class TimedeltaFormat(_TimelikeFormat):
    def _format_non_nat(self, x):
        return str(x.astype('i8'))


class SubArrayFormat:
    def __init__(self, format_function, **options):
        self.format_function = format_function
        self.threshold = options['threshold']
        self.edge_items = options['edgeitems']

    def __call__(self, a):
        self.summary_insert = "..." if a.size > self.threshold else ""
        return self.format_array(a)

    def format_array(self, a):
        if np.ndim(a) == 0:
            return self.format_function(a)

        if self.summary_insert and a.shape[0] > 2 * self.edge_items:
            formatted = (
                [self.format_array(a_) for a_ in a[:self.edge_items]]
                + [self.summary_insert]
                + [self.format_array(a_) for a_ in a[-self.edge_items:]]
            )
        else:
            formatted = [self.format_array(a_) for a_ in a]

        return "[" + ", ".join(formatted) + "]"


class StructuredVoidFormat:
    """
    Formatter for structured np.void objects.

    This does not work on structured alias types like
    np.dtype(('i4', 'i2,i2')), as alias scalars lose their field information,
    and the implementation relies upon np.void.__getitem__.
    """
    def __init__(self, format_functions):
        self.format_functions = format_functions

    @classmethod
    def from_data(cls, data, **options):
        """
        This is a second way to initialize StructuredVoidFormat,
        using the raw data as input. Added to avoid changing
        the signature of __init__.
        """
        format_functions = []
        for field_name in data.dtype.names:
            format_function = _get_format_function(data[field_name], **options)
            if data.dtype[field_name].shape != ():
                format_function = SubArrayFormat(format_function, **options)
            format_functions.append(format_function)
        return cls(format_functions)

    def __call__(self, x):
        str_fields = [
            format_function(field)
            for field, format_function in zip(x, self.format_functions)
        ]
        if len(str_fields) == 1:
            return f"({str_fields[0]},)"
        else:
            return f"({', '.join(str_fields)})"


def _void_scalar_to_string(x, is_repr=True):
    """
    Implements the repr for structured-void scalars. It is called from the
    scalartypes.c.src code, and is placed here because it uses the elementwise
    formatters defined above.
    """
    options = format_options.get().copy()

    if options["legacy"] <= 125:
        return StructuredVoidFormat.from_data(array(x), **options)(x)

    if options.get('formatter') is None:
        options['formatter'] = {}
    options['formatter'].setdefault('float_kind', str)
    val_repr = StructuredVoidFormat.from_data(array(x), **options)(x)
    if not is_repr:
        return val_repr
    cls = type(x)
    cls_fqn = cls.__module__.replace("numpy", "np") + "." + cls.__name__
    void_dtype = np.dtype((np.void, x.dtype))
    return f"{cls_fqn}({val_repr}, dtype={void_dtype!s})"


_typelessdata = [int_, float64, complex128, _nt.bool]


def dtype_is_implied(dtype):
    """
    Determine if the given dtype is implied by the representation
    of its values.

    Parameters
    ----------
    dtype : dtype
        Data type

    Returns
    -------
    implied : bool
        True if the dtype is implied by the representation of its values.

    Examples
    --------
    >>> import numpy as np
    >>> np._core.arrayprint.dtype_is_implied(int)
    True
    >>> np.array([1, 2, 3], int)
    array([1, 2, 3])
    >>> np._core.arrayprint.dtype_is_implied(np.int8)
    False
    >>> np.array([1, 2, 3], np.int8)
    array([1, 2, 3], dtype=int8)
    """
    dtype = np.dtype(dtype)
    if format_options.get()['legacy'] <= 113 and dtype.type == np.bool:
        return False

    # not just void types can be structured, and names are not part of the repr
    if dtype.names is not None:
        return False

    # should care about endianness *unless size is 1* (e.g., int8, bool)
    if not dtype.isnative:
        return False

    return dtype.type in _typelessdata


def dtype_short_repr(dtype):
    """
    Convert a dtype to a short form which evaluates to the same dtype.

    The intent is roughly that the following holds

    >>> from numpy import *
    >>> dt = np.int64([1, 2]).dtype
    >>> assert eval(dtype_short_repr(dt)) == dt
    """
    if type(dtype).__repr__ != np.dtype.__repr__:
        # TODO: Custom repr for user DTypes, logic should likely move.
        return repr(dtype)
    if dtype.names is not None:
        # structured dtypes give a list or tuple repr
        return str(dtype)
    elif issubclass(dtype.type, flexible):
        # handle these separately so they don't give garbage like str256
        return f"'{str(dtype)}'"

    typename = dtype.name
    if not dtype.isnative:
        # deal with cases like dtype('<u2') that are identical to an
        # established dtype (in this case uint16)
        # except that they have a different endianness.
        return f"'{str(dtype)}'"
    # quote typenames which can't be represented as python variable names
    if typename and not (typename[0].isalpha() and typename.isalnum()):
        typename = repr(typename)
    return typename


def _array_repr_implementation(
        arr, max_line_width=None, precision=None, suppress_small=None,
        array2string=array2string):
    """Internal version of array_repr() that allows overriding array2string."""
    current_options = format_options.get()
    override_repr = current_options["override_repr"]
    if override_repr is not None:
        return override_repr(arr)

    if max_line_width is None:
        max_line_width = current_options['linewidth']

    if type(arr) is not ndarray:
        class_name = type(arr).__name__
    else:
        class_name = "array"

    prefix = class_name + "("
    if (current_options['legacy'] <= 113 and
            arr.shape == () and not arr.dtype.names):
        lst = repr(arr.item())
    else:
        lst = array2string(arr, max_line_width, precision, suppress_small,
                           ', ', prefix, suffix=")")

    # Add dtype and shape information if these cannot be inferred from
    # the array string.
    extras = []
    if ((arr.size == 0 and arr.shape != (0,))
            or (current_options['legacy'] > 210
            and arr.size > current_options['threshold'])):
        extras.append(f"shape={arr.shape}")
    if not dtype_is_implied(arr.dtype) or arr.size == 0:
        extras.append(f"dtype={dtype_short_repr(arr.dtype)}")

    if not extras:
        return prefix + lst + ")"

    arr_str = prefix + lst + ","
    extra_str = ", ".join(extras) + ")"
    # compute whether we should put extras on a new line: Do so if adding the
    # extras would extend the last line past max_line_width.
    # Note: This line gives the correct result even when rfind returns -1.
    last_line_len = len(arr_str) - (arr_str.rfind('\n') + 1)
    spacer = " "
    if current_options['legacy'] <= 113:
        if issubclass(arr.dtype.type, flexible):
            spacer = '\n' + ' ' * len(prefix)
    elif last_line_len + len(extra_str) + 1 > max_line_width:
        spacer = '\n' + ' ' * len(prefix)

    return arr_str + spacer + extra_str


def _array_repr_dispatcher(
        arr, max_line_width=None, precision=None, suppress_small=None):
    return (arr,)


@array_function_dispatch(_array_repr_dispatcher, module='numpy')
def array_repr(arr, max_line_width=None, precision=None, suppress_small=None):
    """
    Return the string representation of an array.

    Parameters
    ----------
    arr : ndarray
        Input array.
    max_line_width : int, optional
        Inserts newlines if text is longer than `max_line_width`.
        Defaults to ``numpy.get_printoptions()['linewidth']``.
    precision : int, optional
        Floating point precision.
        Defaults to ``numpy.get_printoptions()['precision']``.
    suppress_small : bool, optional
        Represent numbers "very close" to zero as zero; default is False.
        Very close is defined by precision: if the precision is 8, e.g.,
        numbers smaller (in absolute value) than 5e-9 are represented as
        zero.
        Defaults to ``numpy.get_printoptions()['suppress']``.

    Returns
    -------
    string : str
      The string representation of an array.

    See Also
    --------
    array_str, array2string, set_printoptions

    Examples
    --------
    >>> import numpy as np
    >>> np.array_repr(np.array([1,2]))
    'array([1, 2])'
    >>> np.array_repr(np.ma.array([0.]))
    'MaskedArray([0.])'
    >>> np.array_repr(np.array([], np.int32))
    'array([], dtype=int32)'

    >>> x = np.array([1e-6, 4e-7, 2, 3])
    >>> np.array_repr(x, precision=6, suppress_small=True)
    'array([0.000001,  0.      ,  2.      ,  3.      ])'

    """
    return _array_repr_implementation(
        arr, max_line_width, precision, suppress_small)


@_recursive_guard()
def _guarded_repr_or_str(v):
    if isinstance(v, bytes):
        return repr(v)
    return str(v)


def _array_str_implementation(
        a, max_line_width=None, precision=None, suppress_small=None,
        array2string=array2string):
    """Internal version of array_str() that allows overriding array2string."""
    if (format_options.get()['legacy'] <= 113 and
            a.shape == () and not a.dtype.names):
        return str(a.item())

    # the str of 0d arrays is a special case: It should appear like a scalar,
    # so floats are not truncated by `precision`, and strings are not wrapped
    # in quotes. So we return the str of the scalar value.
    if a.shape == ():
        # obtain a scalar and call str on it, avoiding problems for subclasses
        # for which indexing with () returns a 0d instead of a scalar by using
        # ndarray's getindex. Also guard against recursive 0d object arrays.
        return _guarded_repr_or_str(np.ndarray.__getitem__(a, ()))

    return array2string(a, max_line_width, precision, suppress_small, ' ', "")


def _array_str_dispatcher(
        a, max_line_width=None, precision=None, suppress_small=None):
    return (a,)


@array_function_dispatch(_array_str_dispatcher, module='numpy')
def array_str(a, max_line_width=None, precision=None, suppress_small=None):
    """
    Return a string representation of the data in an array.

    The data in the array is returned as a single string.  This function is
    similar to `array_repr`, the difference being that `array_repr` also
    returns information on the kind of array and its data type.

    Parameters
    ----------
    a : ndarray
        Input array.
    max_line_width : int, optional
        Inserts newlines if text is longer than `max_line_width`.
        Defaults to ``numpy.get_printoptions()['linewidth']``.
    precision : int, optional
        Floating point precision.
        Defaults to ``numpy.get_printoptions()['precision']``.
    suppress_small : bool, optional
        Represent numbers "very close" to zero as zero; default is False.
        Very close is defined by precision: if the precision is 8, e.g.,
        numbers smaller (in absolute value) than 5e-9 are represented as
        zero.
        Defaults to ``numpy.get_printoptions()['suppress']``.

    See Also
    --------
    array2string, array_repr, set_printoptions

    Examples
    --------
    >>> import numpy as np
    >>> np.array_str(np.arange(3))
    '[0 1 2]'

    """
    return _array_str_implementation(
        a, max_line_width, precision, suppress_small)


# needed if __array_function__ is disabled
_array2string_impl = getattr(array2string, '__wrapped__', array2string)
_default_array_str = functools.partial(_array_str_implementation,
                                       array2string=_array2string_impl)
_default_array_repr = functools.partial(_array_repr_implementation,
                                        array2string=_array2string_impl)