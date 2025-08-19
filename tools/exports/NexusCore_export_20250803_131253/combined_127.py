
# === NexusCore/tools\exports\export_20250803_114325\combined_181.py ===

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\textfmts.py ===
"""
    pygments.lexers.textfmts
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for various text formats.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexers import guess_lexer, get_lexer_by_name
from pygments.lexer import RegexLexer, bygroups, default, include
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Generic, Literal, Punctuation
from pygments.util import ClassNotFound

__all__ = ['IrcLogsLexer', 'TodotxtLexer', 'HttpLexer', 'GettextLexer',
           'NotmuchLexer', 'KernelLogLexer']


class IrcLogsLexer(RegexLexer):
    """
    Lexer for IRC logs in *irssi*, *xchat* or *weechat* style.
    """

    name = 'IRC logs'
    aliases = ['irc']
    filenames = ['*.weechatlog']
    mimetypes = ['text/x-irclog']
    url = 'https://en.wikipedia.org/wiki/Internet_Relay_Chat'
    version_added = ''

    flags = re.VERBOSE | re.MULTILINE
    timestamp = r"""
        (
          # irssi / xchat and others
          (?: \[|\()?                  # Opening bracket or paren for the timestamp
            (?:                        # Timestamp
                (?: (?:\d{1,4} [-/])*  # Date as - or /-separated groups of digits
                    (?:\d{1,4})
                 [T ])?                # Date/time separator: T or space
                (?: \d?\d [:.])*       # Time as :/.-separated groups of 1 or 2 digits
                    (?: \d?\d)
            )
          (?: \]|\))?\s+               # Closing bracket or paren for the timestamp
        |
          # weechat
          \d{4}\s\w{3}\s\d{2}\s        # Date
          \d{2}:\d{2}:\d{2}\s+         # Time + Whitespace
        |
          # xchat
          \w{3}\s\d{2}\s               # Date
          \d{2}:\d{2}:\d{2}\s+         # Time + Whitespace
        )?
    """
    tokens = {
        'root': [
            # log start/end
            (r'^\*\*\*\*(.*)\*\*\*\*$', Comment),
            # hack
            ("^" + timestamp + r'(\s*<[^>]*>\s*)$', bygroups(Comment.Preproc, Name.Tag)),
            # normal msgs
            ("^" + timestamp + r"""
                (\s*<.*?>\s*)          # Nick """,
             bygroups(Comment.Preproc, Name.Tag), 'msg'),
            # /me msgs
            ("^" + timestamp + r"""
                (\s*[*]\s+)            # Star
                (\S+\s+.*?\n)          # Nick + rest of message """,
             bygroups(Comment.Preproc, Keyword, Generic.Inserted)),
            # join/part msgs
            ("^" + timestamp + r"""
                (\s*(?:\*{3}|<?-[!@=P]?->?)\s*)  # Star(s) or symbols
                (\S+\s+)                     # Nick + Space
                (.*?\n)                         # Rest of message """,
             bygroups(Comment.Preproc, Keyword, String, Comment)),
            (r"^.*?\n", Text),
        ],
        'msg': [
            (r"\S+:(?!//)", Name.Attribute),  # Prefix
            (r".*\n", Text, '#pop'),
        ],
    }


class GettextLexer(RegexLexer):
    """
    Lexer for Gettext catalog files.
    """
    name = 'Gettext Catalog'
    aliases = ['pot', 'po']
    filenames = ['*.pot', '*.po']
    mimetypes = ['application/x-gettext', 'text/x-gettext', 'text/gettext']
    url = 'https://www.gnu.org/software/gettext'
    version_added = '0.9'

    tokens = {
        'root': [
            (r'^#,\s.*?$', Keyword.Type),
            (r'^#:\s.*?$', Keyword.Declaration),
            # (r'^#$', Comment),
            (r'^(#|#\.\s|#\|\s|#~\s|#\s).*$', Comment.Single),
            (r'^(")([A-Za-z-]+:)(.*")$',
             bygroups(String, Name.Property, String)),
            (r'^".*"$', String),
            (r'^(msgid|msgid_plural|msgstr|msgctxt)(\s+)(".*")$',
             bygroups(Name.Variable, Text, String)),
            (r'^(msgstr\[)(\d)(\])(\s+)(".*")$',
             bygroups(Name.Variable, Number.Integer, Name.Variable, Text, String)),
        ]
    }


class HttpLexer(RegexLexer):
    """
    Lexer for HTTP sessions.
    """

    name = 'HTTP'
    aliases = ['http']
    url = 'https://httpwg.org/specs'
    version_added = '1.5'

    flags = re.DOTALL

    def get_tokens_unprocessed(self, text, stack=('root',)):
        """Reset the content-type state."""
        self.content_type = None
        return RegexLexer.get_tokens_unprocessed(self, text, stack)

    def header_callback(self, match):
        if match.group(1).lower() == 'content-type':
            content_type = match.group(5).strip()
            if ';' in content_type:
                content_type = content_type[:content_type.find(';')].strip()
            self.content_type = content_type
        yield match.start(1), Name.Attribute, match.group(1)
        yield match.start(2), Text, match.group(2)
        yield match.start(3), Operator, match.group(3)
        yield match.start(4), Text, match.group(4)
        yield match.start(5), Literal, match.group(5)
        yield match.start(6), Text, match.group(6)

    def continuous_header_callback(self, match):
        yield match.start(1), Text, match.group(1)
        yield match.start(2), Literal, match.group(2)
        yield match.start(3), Text, match.group(3)

    def content_callback(self, match):
        content_type = getattr(self, 'content_type', None)
        content = match.group()
        offset = match.start()
        if content_type:
            from pygments.lexers import get_lexer_for_mimetype
            possible_lexer_mimetypes = [content_type]
            if '+' in content_type:
                # application/calendar+xml can be treated as application/xml
                # if there's not a better match.
                general_type = re.sub(r'^(.*)/.*\+(.*)$', r'\1/\2',
                                      content_type)
                possible_lexer_mimetypes.append(general_type)

            for i in possible_lexer_mimetypes:
                try:
                    lexer = get_lexer_for_mimetype(i)
                except ClassNotFound:
                    pass
                else:
                    for idx, token, value in lexer.get_tokens_unprocessed(content):
                        yield offset + idx, token, value
                    return
        yield offset, Text, content

    tokens = {
        'root': [
            (r'([a-zA-Z][-_a-zA-Z]+)( +)([^ ]+)( +)'
             r'(HTTP)(/)(1\.[01]|2(?:\.0)?|3)(\r?\n|\Z)',
             bygroups(Name.Function, Text, Name.Namespace, Text,
                      Keyword.Reserved, Operator, Number, Text),
             'headers'),
            (r'(HTTP)(/)(1\.[01]|2(?:\.0)?|3)( +)(\d{3})(?:( +)([^\r\n]*))?(\r?\n|\Z)',
             bygroups(Keyword.Reserved, Operator, Number, Text, Number, Text,
                      Name.Exception, Text),
             'headers'),
        ],
        'headers': [
            (r'([^\s:]+)( *)(:)( *)([^\r\n]*)(\r?\n|\Z)', header_callback),
            (r'([\t ]+)([^\r\n]+)(\r?\n|\Z)', continuous_header_callback),
            (r'\r?\n', Text, 'content')
        ],
        'content': [
            (r'.+', content_callback)
        ]
    }

    def analyse_text(text):
        return any (
            re.search(pattern, text) is not None
            for pattern in (
                r'^([a-zA-Z][-_a-zA-Z]+)( +)([^ ]+)( +)(HTTP)(/)(1\.[01]|2(?:\.0)?|3)(\r?\n|\Z)',
                r'^(HTTP)(/)(1\.[01]|2(?:\.0)?|3)( +)(\d{3})(?:( +)([^\r\n]*))?(\r?\n|\Z)',
            )
        )


class TodotxtLexer(RegexLexer):
    """
    Lexer for Todo.txt todo list format.
    """

    name = 'Todotxt'
    url = 'http://todotxt.com/'
    aliases = ['todotxt']
    version_added = '2.0'
    # *.todotxt is not a standard extension for Todo.txt files; including it
    # makes testing easier, and also makes autodetecting file type easier.
    filenames = ['todo.txt', '*.todotxt']
    mimetypes = ['text/x-todo']

    # Aliases mapping standard token types of Todo.txt format concepts
    CompleteTaskText = Operator  # Chosen to de-emphasize complete tasks
    IncompleteTaskText = Text    # Incomplete tasks should look like plain text

    # Priority should have most emphasis to indicate importance of tasks
    Priority = Generic.Heading
    # Dates should have next most emphasis because time is important
    Date = Generic.Subheading

    # Project and context should have equal weight, and be in different colors
    Project = Generic.Error
    Context = String

    # If tag functionality is added, it should have the same weight as Project
    # and Context, and a different color. Generic.Traceback would work well.

    # Regex patterns for building up rules; dates, priorities, projects, and
    # contexts are all atomic
    # TODO: Make date regex more ISO 8601 compliant
    date_regex = r'\d{4,}-\d{2}-\d{2}'
    priority_regex = r'\([A-Z]\)'
    project_regex = r'\+\S+'
    context_regex = r'@\S+'

    # Compound regex expressions
    complete_one_date_regex = r'(x )(' + date_regex + r')'
    complete_two_date_regex = (complete_one_date_regex + r'( )(' +
                               date_regex + r')')
    priority_date_regex = r'(' + priority_regex + r')( )(' + date_regex + r')'

    tokens = {
        # Should parse starting at beginning of line; each line is a task
        'root': [
            # Complete task entry points: two total:
            # 1. Complete task with two dates
            (complete_two_date_regex, bygroups(CompleteTaskText, Date,
                                               CompleteTaskText, Date),
             'complete'),
            # 2. Complete task with one date
            (complete_one_date_regex, bygroups(CompleteTaskText, Date),
             'complete'),

            # Incomplete task entry points: six total:
            # 1. Priority plus date
            (priority_date_regex, bygroups(Priority, IncompleteTaskText, Date),
             'incomplete'),
            # 2. Priority only
            (priority_regex, Priority, 'incomplete'),
            # 3. Leading date
            (date_regex, Date, 'incomplete'),
            # 4. Leading context
            (context_regex, Context, 'incomplete'),
            # 5. Leading project
            (project_regex, Project, 'incomplete'),
            # 6. Non-whitespace catch-all
            (r'\S+', IncompleteTaskText, 'incomplete'),
        ],

        # Parse a complete task
        'complete': [
            # Newline indicates end of task, should return to root
            (r'\s*\n', CompleteTaskText, '#pop'),
            # Tokenize contexts and projects
            (context_regex, Context),
            (project_regex, Project),
            # Tokenize non-whitespace text
            (r'\S+', CompleteTaskText),
            # Tokenize whitespace not containing a newline
            (r'\s+', CompleteTaskText),
        ],

        # Parse an incomplete task
        'incomplete': [
            # Newline indicates end of task, should return to root
            (r'\s*\n', IncompleteTaskText, '#pop'),
            # Tokenize contexts and projects
            (context_regex, Context),
            (project_regex, Project),
            # Tokenize non-whitespace text
            (r'\S+', IncompleteTaskText),
            # Tokenize whitespace not containing a newline
            (r'\s+', IncompleteTaskText),
        ],
    }


class NotmuchLexer(RegexLexer):
    """
    For Notmuch email text format.

    Additional options accepted:

    `body_lexer`
        If given, highlight the contents of the message body with the specified
        lexer, else guess it according to the body content (default: ``None``).
    """

    name = 'Notmuch'
    url = 'https://notmuchmail.org/'
    aliases = ['notmuch']
    version_added = '2.5'

    def _highlight_code(self, match):
        code = match.group(1)

        try:
            if self.body_lexer:
                lexer = get_lexer_by_name(self.body_lexer)
            else:
                lexer = guess_lexer(code.strip())
        except ClassNotFound:
            lexer = get_lexer_by_name('text')

        yield from lexer.get_tokens_unprocessed(code)

    tokens = {
        'root': [
            (r'\fmessage\{\s*', Keyword, ('message', 'message-attr')),
        ],
        'message-attr': [
            (r'(\s*id:\s*)(\S+)', bygroups(Name.Attribute, String)),
            (r'(\s*(?:depth|match|excluded):\s*)(\d+)',
             bygroups(Name.Attribute, Number.Integer)),
            (r'(\s*filename:\s*)(.+\n)',
             bygroups(Name.Attribute, String)),
            default('#pop'),
        ],
        'message': [
            (r'\fmessage\}\n', Keyword, '#pop'),
            (r'\fheader\{\n', Keyword, 'header'),
            (r'\fbody\{\n', Keyword, 'body'),
        ],
        'header': [
            (r'\fheader\}\n', Keyword, '#pop'),
            (r'((?:Subject|From|To|Cc|Date):\s*)(.*\n)',
             bygroups(Name.Attribute, String)),
            (r'(.*)(\s*\(.*\))(\s*\(.*\)\n)',
             bygroups(Generic.Strong, Literal, Name.Tag)),
        ],
        'body': [
            (r'\fpart\{\n', Keyword, 'part'),
            (r'\f(part|attachment)\{\s*', Keyword, ('part', 'part-attr')),
            (r'\fbody\}\n', Keyword, '#pop'),
        ],
        'part-attr': [
            (r'(ID:\s*)(\d+)', bygroups(Name.Attribute, Number.Integer)),
            (r'(,\s*)((?:Filename|Content-id):\s*)([^,]+)',
             bygroups(Punctuation, Name.Attribute, String)),
            (r'(,\s*)(Content-type:\s*)(.+\n)',
             bygroups(Punctuation, Name.Attribute, String)),
            default('#pop'),
        ],
        'part': [
            (r'\f(?:part|attachment)\}\n', Keyword, '#pop'),
            (r'\f(?:part|attachment)\{\s*', Keyword, ('#push', 'part-attr')),
            (r'^Non-text part: .*\n', Comment),
            (r'(?s)(.*?(?=\f(?:part|attachment)\}\n))', _highlight_code),
        ],
    }

    def analyse_text(text):
        return 1.0 if text.startswith('\fmessage{') else 0.0

    def __init__(self, **options):
        self.body_lexer = options.get('body_lexer', None)
        RegexLexer.__init__(self, **options)


class KernelLogLexer(RegexLexer):
    """
    For Linux Kernel log ("dmesg") output.
    """
    name = 'Kernel log'
    aliases = ['kmsg', 'dmesg']
    filenames = ['*.kmsg', '*.dmesg']
    url = 'https://fr.wikipedia.org/wiki/Dmesg'
    version_added = '2.6'

    tokens = {
        'root': [
            (r'^[^:]+:debug : (?=\[)', Text, 'debug'),
            (r'^[^:]+:info  : (?=\[)', Text, 'info'),
            (r'^[^:]+:warn  : (?=\[)', Text, 'warn'),
            (r'^[^:]+:notice: (?=\[)', Text, 'warn'),
            (r'^[^:]+:err   : (?=\[)', Text, 'error'),
            (r'^[^:]+:crit  : (?=\[)', Text, 'error'),
            (r'^(?=\[)', Text, 'unknown'),
        ],
        'unknown': [
            (r'^(?=.+(warning|notice|audit|deprecated))', Text, 'warn'),
            (r'^(?=.+(error|critical|fail|Bug))', Text, 'error'),
            default('info'),
        ],
        'base': [
            (r'\[[0-9. ]+\] ', Number),
            (r'(?<=\] ).+?:', Keyword),
            (r'\n', Text, '#pop'),
        ],
        'debug': [
            include('base'),
            (r'.+\n', Comment, '#pop')
        ],
        'info': [
            include('base'),
            (r'.+\n', Text, '#pop')
        ],
        'warn': [
            include('base'),
            (r'.+\n', Generic.Strong, '#pop')
        ],
        'error': [
            include('base'),
            (r'.+\n', Generic.Error, '#pop')
        ]
    }

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\util\url.py ===
from __future__ import absolute_import

import re
from collections import namedtuple

from ..exceptions import LocationParseError
from ..packages import six

url_attrs = ["scheme", "auth", "host", "port", "path", "query", "fragment"]

# We only want to normalize urls with an HTTP(S) scheme.
# urllib3 infers URLs without a scheme (None) to be http.
NORMALIZABLE_SCHEMES = ("http", "https", None)

# Almost all of these patterns were derived from the
# 'rfc3986' module: https://github.com/python-hyper/rfc3986
PERCENT_RE = re.compile(r"%[a-fA-F0-9]{2}")
SCHEME_RE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+-]*:|/)")
URI_RE = re.compile(
    r"^(?:([a-zA-Z][a-zA-Z0-9+.-]*):)?"
    r"(?://([^\\/?#]*))?"
    r"([^?#]*)"
    r"(?:\?([^#]*))?"
    r"(?:#(.*))?$",
    re.UNICODE | re.DOTALL,
)

IPV4_PAT = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
HEX_PAT = "[0-9A-Fa-f]{1,4}"
LS32_PAT = "(?:{hex}:{hex}|{ipv4})".format(hex=HEX_PAT, ipv4=IPV4_PAT)
_subs = {"hex": HEX_PAT, "ls32": LS32_PAT}
_variations = [
    #                            6( h16 ":" ) ls32
    "(?:%(hex)s:){6}%(ls32)s",
    #                       "::" 5( h16 ":" ) ls32
    "::(?:%(hex)s:){5}%(ls32)s",
    # [               h16 ] "::" 4( h16 ":" ) ls32
    "(?:%(hex)s)?::(?:%(hex)s:){4}%(ls32)s",
    # [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
    "(?:(?:%(hex)s:)?%(hex)s)?::(?:%(hex)s:){3}%(ls32)s",
    # [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
    "(?:(?:%(hex)s:){0,2}%(hex)s)?::(?:%(hex)s:){2}%(ls32)s",
    # [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32
    "(?:(?:%(hex)s:){0,3}%(hex)s)?::%(hex)s:%(ls32)s",
    # [ *4( h16 ":" ) h16 ] "::"              ls32
    "(?:(?:%(hex)s:){0,4}%(hex)s)?::%(ls32)s",
    # [ *5( h16 ":" ) h16 ] "::"              h16
    "(?:(?:%(hex)s:){0,5}%(hex)s)?::%(hex)s",
    # [ *6( h16 ":" ) h16 ] "::"
    "(?:(?:%(hex)s:){0,6}%(hex)s)?::",
]

UNRESERVED_PAT = r"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._\-~"
IPV6_PAT = "(?:" + "|".join([x % _subs for x in _variations]) + ")"
ZONE_ID_PAT = "(?:%25|%)(?:[" + UNRESERVED_PAT + "]|%[a-fA-F0-9]{2})+"
IPV6_ADDRZ_PAT = r"\[" + IPV6_PAT + r"(?:" + ZONE_ID_PAT + r")?\]"
REG_NAME_PAT = r"(?:[^\[\]%:/?#]|%[a-fA-F0-9]{2})*"
TARGET_RE = re.compile(r"^(/[^?#]*)(?:\?([^#]*))?(?:#.*)?$")

IPV4_RE = re.compile("^" + IPV4_PAT + "$")
IPV6_RE = re.compile("^" + IPV6_PAT + "$")
IPV6_ADDRZ_RE = re.compile("^" + IPV6_ADDRZ_PAT + "$")
BRACELESS_IPV6_ADDRZ_RE = re.compile("^" + IPV6_ADDRZ_PAT[2:-2] + "$")
ZONE_ID_RE = re.compile("(" + ZONE_ID_PAT + r")\]$")

_HOST_PORT_PAT = ("^(%s|%s|%s)(?::0*?(|0|[1-9][0-9]{0,4}))?$") % (
    REG_NAME_PAT,
    IPV4_PAT,
    IPV6_ADDRZ_PAT,
)
_HOST_PORT_RE = re.compile(_HOST_PORT_PAT, re.UNICODE | re.DOTALL)

UNRESERVED_CHARS = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-~"
)
SUB_DELIM_CHARS = set("!$&'()*+,;=")
USERINFO_CHARS = UNRESERVED_CHARS | SUB_DELIM_CHARS | {":"}
PATH_CHARS = USERINFO_CHARS | {"@", "/"}
QUERY_CHARS = FRAGMENT_CHARS = PATH_CHARS | {"?"}


class Url(namedtuple("Url", url_attrs)):
    """
    Data structure for representing an HTTP URL. Used as a return value for
    :func:`parse_url`. Both the scheme and host are normalized as they are
    both case-insensitive according to RFC 3986.
    """

    __slots__ = ()

    def __new__(
        cls,
        scheme=None,
        auth=None,
        host=None,
        port=None,
        path=None,
        query=None,
        fragment=None,
    ):
        if path and not path.startswith("/"):
            path = "/" + path
        if scheme is not None:
            scheme = scheme.lower()
        return super(Url, cls).__new__(
            cls, scheme, auth, host, port, path, query, fragment
        )

    @property
    def hostname(self):
        """For backwards-compatibility with urlparse. We're nice like that."""
        return self.host

    @property
    def request_uri(self):
        """Absolute path including the query string."""
        uri = self.path or "/"

        if self.query is not None:
            uri += "?" + self.query

        return uri

    @property
    def netloc(self):
        """Network location including host and port"""
        if self.port:
            return "%s:%d" % (self.host, self.port)
        return self.host

    @property
    def url(self):
        """
        Convert self into a url

        This function should more or less round-trip with :func:`.parse_url`. The
        returned url may not be exactly the same as the url inputted to
        :func:`.parse_url`, but it should be equivalent by the RFC (e.g., urls
        with a blank port will have : removed).

        Example: ::

            >>> U = parse_url('http://google.com/mail/')
            >>> U.url
            'http://google.com/mail/'
            >>> Url('http', 'username:password', 'host.com', 80,
            ... '/path', 'query', 'fragment').url
            'http://username:password@host.com:80/path?query#fragment'
        """
        scheme, auth, host, port, path, query, fragment = self
        url = u""

        # We use "is not None" we want things to happen with empty strings (or 0 port)
        if scheme is not None:
            url += scheme + u"://"
        if auth is not None:
            url += auth + u"@"
        if host is not None:
            url += host
        if port is not None:
            url += u":" + str(port)
        if path is not None:
            url += path
        if query is not None:
            url += u"?" + query
        if fragment is not None:
            url += u"#" + fragment

        return url

    def __str__(self):
        return self.url


def split_first(s, delims):
    """
    .. deprecated:: 1.25

    Given a string and an iterable of delimiters, split on the first found
    delimiter. Return two split parts and the matched delimiter.

    If not found, then the first part is the full input string.

    Example::

        >>> split_first('foo/bar?baz', '?/=')
        ('foo', 'bar?baz', '/')
        >>> split_first('foo/bar?baz', '123')
        ('foo/bar?baz', '', None)

    Scales linearly with number of delims. Not ideal for large number of delims.
    """
    min_idx = None
    min_delim = None
    for d in delims:
        idx = s.find(d)
        if idx < 0:
            continue

        if min_idx is None or idx < min_idx:
            min_idx = idx
            min_delim = d

    if min_idx is None or min_idx < 0:
        return s, "", None

    return s[:min_idx], s[min_idx + 1 :], min_delim


def _encode_invalid_chars(component, allowed_chars, encoding="utf-8"):
    """Percent-encodes a URI component without reapplying
    onto an already percent-encoded component.
    """
    if component is None:
        return component

    component = six.ensure_text(component)

    # Normalize existing percent-encoded bytes.
    # Try to see if the component we're encoding is already percent-encoded
    # so we can skip all '%' characters but still encode all others.
    component, percent_encodings = PERCENT_RE.subn(
        lambda match: match.group(0).upper(), component
    )

    uri_bytes = component.encode("utf-8", "surrogatepass")
    is_percent_encoded = percent_encodings == uri_bytes.count(b"%")
    encoded_component = bytearray()

    for i in range(0, len(uri_bytes)):
        # Will return a single character bytestring on both Python 2 & 3
        byte = uri_bytes[i : i + 1]
        byte_ord = ord(byte)
        if (is_percent_encoded and byte == b"%") or (
            byte_ord < 128 and byte.decode() in allowed_chars
        ):
            encoded_component += byte
            continue
        encoded_component.extend(b"%" + (hex(byte_ord)[2:].encode().zfill(2).upper()))

    return encoded_component.decode(encoding)


def _remove_path_dot_segments(path):
    # See http://tools.ietf.org/html/rfc3986#section-5.2.4 for pseudo-code
    segments = path.split("/")  # Turn the path into a list of segments
    output = []  # Initialize the variable to use to store output

    for segment in segments:
        # '.' is the current directory, so ignore it, it is superfluous
        if segment == ".":
            continue
        # Anything other than '..', should be appended to the output
        elif segment != "..":
            output.append(segment)
        # In this case segment == '..', if we can, we should pop the last
        # element
        elif output:
            output.pop()

    # If the path starts with '/' and the output is empty or the first string
    # is non-empty
    if path.startswith("/") and (not output or output[0]):
        output.insert(0, "")

    # If the path starts with '/.' or '/..' ensure we add one more empty
    # string to add a trailing '/'
    if path.endswith(("/.", "/..")):
        output.append("")

    return "/".join(output)


def _normalize_host(host, scheme):
    if host:
        if isinstance(host, six.binary_type):
            host = six.ensure_str(host)

        if scheme in NORMALIZABLE_SCHEMES:
            is_ipv6 = IPV6_ADDRZ_RE.match(host)
            if is_ipv6:
                # IPv6 hosts of the form 'a::b%zone' are encoded in a URL as
                # such per RFC 6874: 'a::b%25zone'. Unquote the ZoneID
                # separator as necessary to return a valid RFC 4007 scoped IP.
                match = ZONE_ID_RE.search(host)
                if match:
                    start, end = match.span(1)
                    zone_id = host[start:end]

                    if zone_id.startswith("%25") and zone_id != "%25":
                        zone_id = zone_id[3:]
                    else:
                        zone_id = zone_id[1:]
                    zone_id = "%" + _encode_invalid_chars(zone_id, UNRESERVED_CHARS)
                    return host[:start].lower() + zone_id + host[end:]
                else:
                    return host.lower()
            elif not IPV4_RE.match(host):
                return six.ensure_str(
                    b".".join([_idna_encode(label) for label in host.split(".")])
                )
    return host


def _idna_encode(name):
    if name and any(ord(x) >= 128 for x in name):
        try:
            from pip._vendor import idna
        except ImportError:
            six.raise_from(
                LocationParseError("Unable to parse URL without the 'idna' module"),
                None,
            )
        try:
            return idna.encode(name.lower(), strict=True, std3_rules=True)
        except idna.IDNAError:
            six.raise_from(
                LocationParseError(u"Name '%s' is not a valid IDNA label" % name), None
            )
    return name.lower().encode("ascii")


def _encode_target(target):
    """Percent-encodes a request target so that there are no invalid characters"""
    path, query = TARGET_RE.match(target).groups()
    target = _encode_invalid_chars(path, PATH_CHARS)
    query = _encode_invalid_chars(query, QUERY_CHARS)
    if query is not None:
        target += "?" + query
    return target


def parse_url(url):
    """
    Given a url, return a parsed :class:`.Url` namedtuple. Best-effort is
    performed to parse incomplete urls. Fields not provided will be None.
    This parser is RFC 3986 and RFC 6874 compliant.

    The parser logic and helper functions are based heavily on
    work done in the ``rfc3986`` module.

    :param str url: URL to parse into a :class:`.Url` namedtuple.

    Partly backwards-compatible with :mod:`urlparse`.

    Example::

        >>> parse_url('http://google.com/mail/')
        Url(scheme='http', host='google.com', port=None, path='/mail/', ...)
        >>> parse_url('google.com:80')
        Url(scheme=None, host='google.com', port=80, path=None, ...)
        >>> parse_url('/foo?bar')
        Url(scheme=None, host=None, port=None, path='/foo', query='bar', ...)
    """
    if not url:
        # Empty
        return Url()

    source_url = url
    if not SCHEME_RE.search(url):
        url = "//" + url

    try:
        scheme, authority, path, query, fragment = URI_RE.match(url).groups()
        normalize_uri = scheme is None or scheme.lower() in NORMALIZABLE_SCHEMES

        if scheme:
            scheme = scheme.lower()

        if authority:
            auth, _, host_port = authority.rpartition("@")
            auth = auth or None
            host, port = _HOST_PORT_RE.match(host_port).groups()
            if auth and normalize_uri:
                auth = _encode_invalid_chars(auth, USERINFO_CHARS)
            if port == "":
                port = None
        else:
            auth, host, port = None, None, None

        if port is not None:
            port = int(port)
            if not (0 <= port <= 65535):
                raise LocationParseError(url)

        host = _normalize_host(host, scheme)

        if normalize_uri and path:
            path = _remove_path_dot_segments(path)
            path = _encode_invalid_chars(path, PATH_CHARS)
        if normalize_uri and query:
            query = _encode_invalid_chars(query, QUERY_CHARS)
        if normalize_uri and fragment:
            fragment = _encode_invalid_chars(fragment, FRAGMENT_CHARS)

    except (ValueError, AttributeError):
        return six.raise_from(LocationParseError(source_url), None)

    # For the sake of backwards compatibility we put empty
    # string values for path if there are any defined values
    # beyond the path in the URL.
    # TODO: Remove this when we break backwards compatibility.
    if not path:
        if query is not None or fragment is not None:
            path = ""
        else:
            path = None

    # Ensure that each part of the URL is a `str` for
    # backwards compatibility.
    if isinstance(url, six.text_type):
        ensure_func = six.ensure_text
    else:
        ensure_func = six.ensure_str

    def ensure_type(x):
        return x if x is None else ensure_func(x)

    return Url(
        scheme=ensure_type(scheme),
        auth=ensure_type(auth),
        host=ensure_type(host),
        port=port,
        path=ensure_type(path),
        query=ensure_type(query),
        fragment=ensure_type(fragment),
    )


def get_host(url):
    """
    Deprecated. Use :func:`parse_url` instead.
    """
    p = parse_url(url)
    return p.scheme or "http", p.hostname, p.port

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\streaming_chunk_builder_utils.py ===
import base64
import time
from typing import Any, Dict, List, Optional, Union, cast

from litellm.types.llms.openai import (
    ChatCompletionAssistantContentValue,
    ChatCompletionAudioDelta,
)
from litellm.types.utils import (
    ChatCompletionAudioResponse,
    ChatCompletionMessageToolCall,
    Choices,
    CompletionTokensDetails,
    CompletionTokensDetailsWrapper,
    Function,
    FunctionCall,
    ModelResponse,
    ModelResponseStream,
    PromptTokensDetails,
    Usage,
)
from litellm.utils import print_verbose, token_counter


class ChunkProcessor:
    def __init__(self, chunks: List, messages: Optional[list] = None):
        self.chunks = self._sort_chunks(chunks)
        self.messages = messages
        self.first_chunk = chunks[0]

    def _sort_chunks(self, chunks: list) -> list:
        if not chunks:
            return []
        if chunks[0]._hidden_params.get("created_at"):
            return sorted(
                chunks, key=lambda x: x._hidden_params.get("created_at", float("inf"))
            )
        return chunks

    def update_model_response_with_hidden_params(
        self, model_response: ModelResponse, chunk: Optional[Dict[str, Any]] = None
    ) -> ModelResponse:
        if chunk is None:
            return model_response
        # set hidden params from chunk to model_response
        if model_response is not None and hasattr(model_response, "_hidden_params"):
            model_response._hidden_params = chunk.get("_hidden_params", {})
        return model_response

    @staticmethod
    def _get_chunk_id(chunks: List[Dict[str, Any]]) -> str:
        """
        Chunks:
        [{"id": ""}, {"id": "1"}, {"id": "1"}]
        """
        for chunk in chunks:
            if chunk.get("id"):
                return chunk["id"]
        return ""

    def build_base_response(self, chunks: List[Dict[str, Any]]) -> ModelResponse:
        chunk = self.first_chunk
        id = ChunkProcessor._get_chunk_id(chunks)
        object = chunk["object"]
        created = chunk["created"]
        model = chunk["model"]
        system_fingerprint = chunk.get("system_fingerprint", None)

        role = chunk["choices"][0]["delta"]["role"]
        finish_reason = "stop"
        for chunk in chunks:
            if "choices" in chunk and len(chunk["choices"]) > 0:
                if hasattr(chunk["choices"][0], "finish_reason"):
                    finish_reason = chunk["choices"][0].finish_reason
                elif "finish_reason" in chunk["choices"][0]:
                    finish_reason = chunk["choices"][0]["finish_reason"]

        # Initialize the response dictionary
        response = ModelResponse(
            **{
                "id": id,
                "object": object,
                "created": created,
                "model": model,
                "system_fingerprint": system_fingerprint,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": role, "content": ""},
                        "finish_reason": finish_reason,
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,  # Modify as needed
                    "completion_tokens": 0,  # Modify as needed
                    "total_tokens": 0,  # Modify as needed
                },
            }
        )

        response = self.update_model_response_with_hidden_params(
            model_response=response, chunk=chunk
        )
        return response

    def get_combined_tool_content(
        self, tool_call_chunks: List[Dict[str, Any]]
    ) -> List[ChatCompletionMessageToolCall]:
        tool_calls_list: List[ChatCompletionMessageToolCall] = []
        tool_call_map: Dict[
            int, Dict[str, Any]
        ] = {}  # Map to store tool calls by index

        for chunk in tool_call_chunks:
            choices = chunk["choices"]
            for choice in choices:
                delta = choice.get("delta", {})
                tool_calls = delta.get("tool_calls", [])

                for tool_call in tool_calls:
                    if not tool_call or not hasattr(tool_call, "function"):
                        continue

                    index = getattr(tool_call, "index", 0)
                    if index not in tool_call_map:
                        tool_call_map[index] = {
                            "id": None,
                            "name": None,
                            "type": None,
                            "arguments": [],
                        }

                    if hasattr(tool_call, "id") and tool_call.id:
                        tool_call_map[index]["id"] = tool_call.id
                    if hasattr(tool_call, "type") and tool_call.type:
                        tool_call_map[index]["type"] = tool_call.type
                    if hasattr(tool_call, "function"):
                        if (
                            hasattr(tool_call.function, "name")
                            and tool_call.function.name
                        ):
                            tool_call_map[index]["name"] = tool_call.function.name
                        if (
                            hasattr(tool_call.function, "arguments")
                            and tool_call.function.arguments
                        ):
                            tool_call_map[index]["arguments"].append(
                                tool_call.function.arguments
                            )

        # Convert the map to a list of tool calls
        for index in sorted(tool_call_map.keys()):
            tool_call_data = tool_call_map[index]
            if tool_call_data["id"] and tool_call_data["name"]:
                combined_arguments = "".join(tool_call_data["arguments"]) or "{}"
                tool_calls_list.append(
                    ChatCompletionMessageToolCall(
                        id=tool_call_data["id"],
                        function=Function(
                            arguments=combined_arguments,
                            name=tool_call_data["name"],
                        ),
                        type=tool_call_data["type"] or "function",
                    )
                )

        return tool_calls_list

    def get_combined_function_call_content(
        self, function_call_chunks: List[Dict[str, Any]]
    ) -> FunctionCall:
        argument_list = []
        delta = function_call_chunks[0]["choices"][0]["delta"]
        function_call = delta.get("function_call", "")
        function_call_name = function_call.name

        for chunk in function_call_chunks:
            choices = chunk["choices"]
            for choice in choices:
                delta = choice.get("delta", {})
                function_call = delta.get("function_call", "")

                # Check if a function call is present
                if function_call:
                    # Now, function_call is expected to be a dictionary
                    arguments = function_call.arguments
                    argument_list.append(arguments)

        combined_arguments = "".join(argument_list)

        return FunctionCall(
            name=function_call_name,
            arguments=combined_arguments,
        )

    def get_combined_content(
        self, chunks: List[Dict[str, Any]], delta_key: str = "content"
    ) -> ChatCompletionAssistantContentValue:
        content_list: List[str] = []
        for chunk in chunks:
            choices = chunk["choices"]
            for choice in choices:
                delta = choice.get("delta", {})
                content = delta.get(delta_key, "")
                if content is None:
                    continue  # openai v1.0.0 sets content = None for chunks
                content_list.append(content)

        # Combine the "content" strings into a single string || combine the 'function' strings into a single string
        combined_content = "".join(content_list)

        # Update the "content" field within the response dictionary
        return combined_content

    def get_combined_reasoning_content(
        self, chunks: List[Dict[str, Any]]
    ) -> ChatCompletionAssistantContentValue:
        return self.get_combined_content(chunks, delta_key="reasoning_content")

    def get_combined_audio_content(
        self, chunks: List[Dict[str, Any]]
    ) -> ChatCompletionAudioResponse:
        base64_data_list: List[str] = []
        transcript_list: List[str] = []
        expires_at: Optional[int] = None
        id: Optional[str] = None

        for chunk in chunks:
            choices = chunk["choices"]
            for choice in choices:
                delta = choice.get("delta") or {}
                audio: Optional[ChatCompletionAudioDelta] = delta.get("audio")
                if audio is not None:
                    for k, v in audio.items():
                        if k == "data" and v is not None and isinstance(v, str):
                            base64_data_list.append(v)
                        elif k == "transcript" and v is not None and isinstance(v, str):
                            transcript_list.append(v)
                        elif k == "expires_at" and v is not None and isinstance(v, int):
                            expires_at = v
                        elif k == "id" and v is not None and isinstance(v, str):
                            id = v

        concatenated_audio = concatenate_base64_list(base64_data_list)
        return ChatCompletionAudioResponse(
            data=concatenated_audio,
            expires_at=expires_at or int(time.time() + 3600),
            transcript="".join(transcript_list),
            id=id,
        )

    def _usage_chunk_calculation_helper(self, usage_chunk: Usage) -> dict:
        prompt_tokens = 0
        completion_tokens = 0
        ## anthropic prompt caching information ##
        cache_creation_input_tokens: Optional[int] = None
        cache_read_input_tokens: Optional[int] = None
        completion_tokens_details: Optional[CompletionTokensDetails] = None
        prompt_tokens_details: Optional[PromptTokensDetails] = None

        if "prompt_tokens" in usage_chunk:
            prompt_tokens = usage_chunk.get("prompt_tokens", 0) or 0
        if "completion_tokens" in usage_chunk:
            completion_tokens = usage_chunk.get("completion_tokens", 0) or 0
        if "cache_creation_input_tokens" in usage_chunk:
            cache_creation_input_tokens = usage_chunk.get("cache_creation_input_tokens")
        if "cache_read_input_tokens" in usage_chunk:
            cache_read_input_tokens = usage_chunk.get("cache_read_input_tokens")
        if hasattr(usage_chunk, "completion_tokens_details"):
            if isinstance(usage_chunk.completion_tokens_details, dict):
                completion_tokens_details = CompletionTokensDetails(
                    **usage_chunk.completion_tokens_details
                )
            elif isinstance(
                usage_chunk.completion_tokens_details, CompletionTokensDetails
            ):
                completion_tokens_details = usage_chunk.completion_tokens_details
        if hasattr(usage_chunk, "prompt_tokens_details"):
            if isinstance(usage_chunk.prompt_tokens_details, dict):
                prompt_tokens_details = PromptTokensDetails(
                    **usage_chunk.prompt_tokens_details
                )
            elif isinstance(usage_chunk.prompt_tokens_details, PromptTokensDetails):
                prompt_tokens_details = usage_chunk.prompt_tokens_details

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cache_creation_input_tokens": cache_creation_input_tokens,
            "cache_read_input_tokens": cache_read_input_tokens,
            "completion_tokens_details": completion_tokens_details,
            "prompt_tokens_details": prompt_tokens_details,
        }

    def count_reasoning_tokens(self, response: ModelResponse) -> int:
        reasoning_tokens = 0
        for choice in response.choices:
            if (
                hasattr(cast(Choices, choice).message, "reasoning_content")
                and cast(Choices, choice).message.reasoning_content is not None
            ):
                reasoning_tokens += token_counter(
                    text=cast(Choices, choice).message.reasoning_content,
                    count_response_tokens=True,
                )

        return reasoning_tokens

    def calculate_usage(
        self,
        chunks: List[Union[Dict[str, Any], ModelResponse]],
        model: str,
        completion_output: str,
        messages: Optional[List] = None,
        reasoning_tokens: Optional[int] = None,
    ) -> Usage:
        """
        Calculate usage for the given chunks.
        """
        returned_usage = Usage()
        # # Update usage information if needed
        prompt_tokens = 0
        completion_tokens = 0
        ## anthropic prompt caching information ##
        cache_creation_input_tokens: Optional[int] = None
        cache_read_input_tokens: Optional[int] = None
        completion_tokens_details: Optional[CompletionTokensDetails] = None
        prompt_tokens_details: Optional[PromptTokensDetails] = None
        for chunk in chunks:
            usage_chunk: Optional[Usage] = None
            if "usage" in chunk:
                usage_chunk = chunk["usage"]
            elif (
                isinstance(chunk, ModelResponse)
                or isinstance(chunk, ModelResponseStream)
            ) and hasattr(chunk, "_hidden_params"):
                usage_chunk = chunk._hidden_params.get("usage", None)

            if usage_chunk is not None:
                usage_chunk_dict = self._usage_chunk_calculation_helper(usage_chunk)
                if (
                    usage_chunk_dict["prompt_tokens"] is not None
                    and usage_chunk_dict["prompt_tokens"] > 0
                ):
                    prompt_tokens = usage_chunk_dict["prompt_tokens"]
                if (
                    usage_chunk_dict["completion_tokens"] is not None
                    and usage_chunk_dict["completion_tokens"] > 0
                ):
                    completion_tokens = usage_chunk_dict["completion_tokens"]
                if usage_chunk_dict["cache_creation_input_tokens"] is not None and (
                    usage_chunk_dict["cache_creation_input_tokens"] > 0
                    or cache_creation_input_tokens is None
                ):
                    cache_creation_input_tokens = usage_chunk_dict[
                        "cache_creation_input_tokens"
                    ]
                if usage_chunk_dict["cache_read_input_tokens"] is not None and (
                    usage_chunk_dict["cache_read_input_tokens"] > 0
                    or cache_read_input_tokens is None
                ):
                    cache_read_input_tokens = usage_chunk_dict[
                        "cache_read_input_tokens"
                    ]
                if usage_chunk_dict["completion_tokens_details"] is not None:
                    completion_tokens_details = usage_chunk_dict[
                        "completion_tokens_details"
                    ]
                prompt_tokens_details = usage_chunk_dict["prompt_tokens_details"]
        try:
            returned_usage.prompt_tokens = prompt_tokens or token_counter(
                model=model, messages=messages
            )
        except (
            Exception
        ):  # don't allow this failing to block a complete streaming response from being returned
            print_verbose("token_counter failed, assuming prompt tokens is 0")
            returned_usage.prompt_tokens = 0
        returned_usage.completion_tokens = completion_tokens or token_counter(
            model=model,
            text=completion_output,
            count_response_tokens=True,  # count_response_tokens is a Flag to tell token counter this is a response, No need to add extra tokens we do for input messages
        )
        returned_usage.total_tokens = (
            returned_usage.prompt_tokens + returned_usage.completion_tokens
        )

        if cache_creation_input_tokens is not None:
            returned_usage._cache_creation_input_tokens = cache_creation_input_tokens
            setattr(
                returned_usage,
                "cache_creation_input_tokens",
                cache_creation_input_tokens,
            )  # for anthropic
        if cache_read_input_tokens is not None:
            returned_usage._cache_read_input_tokens = cache_read_input_tokens
            setattr(
                returned_usage, "cache_read_input_tokens", cache_read_input_tokens
            )  # for anthropic
        if completion_tokens_details is not None:
            returned_usage.completion_tokens_details = completion_tokens_details

        if reasoning_tokens is not None:
            if returned_usage.completion_tokens_details is None:
                returned_usage.completion_tokens_details = (
                    CompletionTokensDetailsWrapper(reasoning_tokens=reasoning_tokens)
                )
            elif (
                returned_usage.completion_tokens_details is not None
                and returned_usage.completion_tokens_details.reasoning_tokens is None
            ):
                returned_usage.completion_tokens_details.reasoning_tokens = (
                    reasoning_tokens
                )
        if prompt_tokens_details is not None:
            returned_usage.prompt_tokens_details = prompt_tokens_details

        return returned_usage


def concatenate_base64_list(base64_strings: List[str]) -> str:
    """
    Concatenates a list of base64-encoded strings.

    Args:
        base64_strings (List[str]): A list of base64 strings to concatenate.

    Returns:
        str: The concatenated result as a base64-encoded string.
    """
    # Decode each base64 string and collect the resulting bytes
    combined_bytes = b"".join(base64.b64decode(b64_str) for b64_str in base64_strings)

    # Encode the concatenated bytes back to base64
    return base64.b64encode(combined_bytes).decode("utf-8")

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\util\url.py ===
from __future__ import absolute_import

import re
from collections import namedtuple

from ..exceptions import LocationParseError
from ..packages import six

url_attrs = ["scheme", "auth", "host", "port", "path", "query", "fragment"]

# We only want to normalize urls with an HTTP(S) scheme.
# urllib3 infers URLs without a scheme (None) to be http.
NORMALIZABLE_SCHEMES = ("http", "https", None)

# Almost all of these patterns were derived from the
# 'rfc3986' module: https://github.com/python-hyper/rfc3986
PERCENT_RE = re.compile(r"%[a-fA-F0-9]{2}")
SCHEME_RE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+-]*:|/)")
URI_RE = re.compile(
    r"^(?:([a-zA-Z][a-zA-Z0-9+.-]*):)?"
    r"(?://([^\\/?#]*))?"
    r"([^?#]*)"
    r"(?:\?([^#]*))?"
    r"(?:#(.*))?$",
    re.UNICODE | re.DOTALL,
)

IPV4_PAT = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
HEX_PAT = "[0-9A-Fa-f]{1,4}"
LS32_PAT = "(?:{hex}:{hex}|{ipv4})".format(hex=HEX_PAT, ipv4=IPV4_PAT)
_subs = {"hex": HEX_PAT, "ls32": LS32_PAT}
_variations = [
    #                            6( h16 ":" ) ls32
    "(?:%(hex)s:){6}%(ls32)s",
    #                       "::" 5( h16 ":" ) ls32
    "::(?:%(hex)s:){5}%(ls32)s",
    # [               h16 ] "::" 4( h16 ":" ) ls32
    "(?:%(hex)s)?::(?:%(hex)s:){4}%(ls32)s",
    # [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
    "(?:(?:%(hex)s:)?%(hex)s)?::(?:%(hex)s:){3}%(ls32)s",
    # [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
    "(?:(?:%(hex)s:){0,2}%(hex)s)?::(?:%(hex)s:){2}%(ls32)s",
    # [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32
    "(?:(?:%(hex)s:){0,3}%(hex)s)?::%(hex)s:%(ls32)s",
    # [ *4( h16 ":" ) h16 ] "::"              ls32
    "(?:(?:%(hex)s:){0,4}%(hex)s)?::%(ls32)s",
    # [ *5( h16 ":" ) h16 ] "::"              h16
    "(?:(?:%(hex)s:){0,5}%(hex)s)?::%(hex)s",
    # [ *6( h16 ":" ) h16 ] "::"
    "(?:(?:%(hex)s:){0,6}%(hex)s)?::",
]

UNRESERVED_PAT = r"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._\-~"
IPV6_PAT = "(?:" + "|".join([x % _subs for x in _variations]) + ")"
ZONE_ID_PAT = "(?:%25|%)(?:[" + UNRESERVED_PAT + "]|%[a-fA-F0-9]{2})+"
IPV6_ADDRZ_PAT = r"\[" + IPV6_PAT + r"(?:" + ZONE_ID_PAT + r")?\]"
REG_NAME_PAT = r"(?:[^\[\]%:/?#]|%[a-fA-F0-9]{2})*"
TARGET_RE = re.compile(r"^(/[^?#]*)(?:\?([^#]*))?(?:#.*)?$")

IPV4_RE = re.compile("^" + IPV4_PAT + "$")
IPV6_RE = re.compile("^" + IPV6_PAT + "$")
IPV6_ADDRZ_RE = re.compile("^" + IPV6_ADDRZ_PAT + "$")
BRACELESS_IPV6_ADDRZ_RE = re.compile("^" + IPV6_ADDRZ_PAT[2:-2] + "$")
ZONE_ID_RE = re.compile("(" + ZONE_ID_PAT + r")\]$")

_HOST_PORT_PAT = ("^(%s|%s|%s)(?::0*?(|0|[1-9][0-9]{0,4}))?$") % (
    REG_NAME_PAT,
    IPV4_PAT,
    IPV6_ADDRZ_PAT,
)
_HOST_PORT_RE = re.compile(_HOST_PORT_PAT, re.UNICODE | re.DOTALL)

UNRESERVED_CHARS = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-~"
)
SUB_DELIM_CHARS = set("!$&'()*+,;=")
USERINFO_CHARS = UNRESERVED_CHARS | SUB_DELIM_CHARS | {":"}
PATH_CHARS = USERINFO_CHARS | {"@", "/"}
QUERY_CHARS = FRAGMENT_CHARS = PATH_CHARS | {"?"}


class Url(namedtuple("Url", url_attrs)):
    """
    Data structure for representing an HTTP URL. Used as a return value for
    :func:`parse_url`. Both the scheme and host are normalized as they are
    both case-insensitive according to RFC 3986.
    """

    __slots__ = ()

    def __new__(
        cls,
        scheme=None,
        auth=None,
        host=None,
        port=None,
        path=None,
        query=None,
        fragment=None,
    ):
        if path and not path.startswith("/"):
            path = "/" + path
        if scheme is not None:
            scheme = scheme.lower()
        return super(Url, cls).__new__(
            cls, scheme, auth, host, port, path, query, fragment
        )

    @property
    def hostname(self):
        """For backwards-compatibility with urlparse. We're nice like that."""
        return self.host

    @property
    def request_uri(self):
        """Absolute path including the query string."""
        uri = self.path or "/"

        if self.query is not None:
            uri += "?" + self.query

        return uri

    @property
    def netloc(self):
        """Network location including host and port"""
        if self.port:
            return "%s:%d" % (self.host, self.port)
        return self.host

    @property
    def url(self):
        """
        Convert self into a url

        This function should more or less round-trip with :func:`.parse_url`. The
        returned url may not be exactly the same as the url inputted to
        :func:`.parse_url`, but it should be equivalent by the RFC (e.g., urls
        with a blank port will have : removed).

        Example: ::

            >>> U = parse_url('http://google.com/mail/')
            >>> U.url
            'http://google.com/mail/'
            >>> Url('http', 'username:password', 'host.com', 80,
            ... '/path', 'query', 'fragment').url
            'http://username:password@host.com:80/path?query#fragment'
        """
        scheme, auth, host, port, path, query, fragment = self
        url = u""

        # We use "is not None" we want things to happen with empty strings (or 0 port)
        if scheme is not None:
            url += scheme + u"://"
        if auth is not None:
            url += auth + u"@"
        if host is not None:
            url += host
        if port is not None:
            url += u":" + str(port)
        if path is not None:
            url += path
        if query is not None:
            url += u"?" + query
        if fragment is not None:
            url += u"#" + fragment

        return url

    def __str__(self):
        return self.url


def split_first(s, delims):
    """
    .. deprecated:: 1.25

    Given a string and an iterable of delimiters, split on the first found
    delimiter. Return two split parts and the matched delimiter.

    If not found, then the first part is the full input string.

    Example::

        >>> split_first('foo/bar?baz', '?/=')
        ('foo', 'bar?baz', '/')
        >>> split_first('foo/bar?baz', '123')
        ('foo/bar?baz', '', None)

    Scales linearly with number of delims. Not ideal for large number of delims.
    """
    min_idx = None
    min_delim = None
    for d in delims:
        idx = s.find(d)
        if idx < 0:
            continue

        if min_idx is None or idx < min_idx:
            min_idx = idx
            min_delim = d

    if min_idx is None or min_idx < 0:
        return s, "", None

    return s[:min_idx], s[min_idx + 1 :], min_delim


def _encode_invalid_chars(component, allowed_chars, encoding="utf-8"):
    """Percent-encodes a URI component without reapplying
    onto an already percent-encoded component.
    """
    if component is None:
        return component

    component = six.ensure_text(component)

    # Normalize existing percent-encoded bytes.
    # Try to see if the component we're encoding is already percent-encoded
    # so we can skip all '%' characters but still encode all others.
    component, percent_encodings = PERCENT_RE.subn(
        lambda match: match.group(0).upper(), component
    )

    uri_bytes = component.encode("utf-8", "surrogatepass")
    is_percent_encoded = percent_encodings == uri_bytes.count(b"%")
    encoded_component = bytearray()

    for i in range(0, len(uri_bytes)):
        # Will return a single character bytestring on both Python 2 & 3
        byte = uri_bytes[i : i + 1]
        byte_ord = ord(byte)
        if (is_percent_encoded and byte == b"%") or (
            byte_ord < 128 and byte.decode() in allowed_chars
        ):
            encoded_component += byte
            continue
        encoded_component.extend(b"%" + (hex(byte_ord)[2:].encode().zfill(2).upper()))

    return encoded_component.decode(encoding)


def _remove_path_dot_segments(path):
    # See http://tools.ietf.org/html/rfc3986#section-5.2.4 for pseudo-code
    segments = path.split("/")  # Turn the path into a list of segments
    output = []  # Initialize the variable to use to store output

    for segment in segments:
        # '.' is the current directory, so ignore it, it is superfluous
        if segment == ".":
            continue
        # Anything other than '..', should be appended to the output
        elif segment != "..":
            output.append(segment)
        # In this case segment == '..', if we can, we should pop the last
        # element
        elif output:
            output.pop()

    # If the path starts with '/' and the output is empty or the first string
    # is non-empty
    if path.startswith("/") and (not output or output[0]):
        output.insert(0, "")

    # If the path starts with '/.' or '/..' ensure we add one more empty
    # string to add a trailing '/'
    if path.endswith(("/.", "/..")):
        output.append("")

    return "/".join(output)


def _normalize_host(host, scheme):
    if host:
        if isinstance(host, six.binary_type):
            host = six.ensure_str(host)

        if scheme in NORMALIZABLE_SCHEMES:
            is_ipv6 = IPV6_ADDRZ_RE.match(host)
            if is_ipv6:
                # IPv6 hosts of the form 'a::b%zone' are encoded in a URL as
                # such per RFC 6874: 'a::b%25zone'. Unquote the ZoneID
                # separator as necessary to return a valid RFC 4007 scoped IP.
                match = ZONE_ID_RE.search(host)
                if match:
                    start, end = match.span(1)
                    zone_id = host[start:end]

                    if zone_id.startswith("%25") and zone_id != "%25":
                        zone_id = zone_id[3:]
                    else:
                        zone_id = zone_id[1:]
                    zone_id = "%" + _encode_invalid_chars(zone_id, UNRESERVED_CHARS)
                    return host[:start].lower() + zone_id + host[end:]
                else:
                    return host.lower()
            elif not IPV4_RE.match(host):
                return six.ensure_str(
                    b".".join([_idna_encode(label) for label in host.split(".")])
                )
    return host


def _idna_encode(name):
    if name and any(ord(x) >= 128 for x in name):
        try:
            from pip._vendor import idna
        except ImportError:
            six.raise_from(
                LocationParseError("Unable to parse URL without the 'idna' module"),
                None,
            )
        try:
            return idna.encode(name.lower(), strict=True, std3_rules=True)
        except idna.IDNAError:
            six.raise_from(
                LocationParseError(u"Name '%s' is not a valid IDNA label" % name), None
            )
    return name.lower().encode("ascii")


def _encode_target(target):
    """Percent-encodes a request target so that there are no invalid characters"""
    path, query = TARGET_RE.match(target).groups()
    target = _encode_invalid_chars(path, PATH_CHARS)
    query = _encode_invalid_chars(query, QUERY_CHARS)
    if query is not None:
        target += "?" + query
    return target


def parse_url(url):
    """
    Given a url, return a parsed :class:`.Url` namedtuple. Best-effort is
    performed to parse incomplete urls. Fields not provided will be None.
    This parser is RFC 3986 and RFC 6874 compliant.

    The parser logic and helper functions are based heavily on
    work done in the ``rfc3986`` module.

    :param str url: URL to parse into a :class:`.Url` namedtuple.

    Partly backwards-compatible with :mod:`urlparse`.

    Example::

        >>> parse_url('http://google.com/mail/')
        Url(scheme='http', host='google.com', port=None, path='/mail/', ...)
        >>> parse_url('google.com:80')
        Url(scheme=None, host='google.com', port=80, path=None, ...)
        >>> parse_url('/foo?bar')
        Url(scheme=None, host=None, port=None, path='/foo', query='bar', ...)
    """
    if not url:
        # Empty
        return Url()

    source_url = url
    if not SCHEME_RE.search(url):
        url = "//" + url

    try:
        scheme, authority, path, query, fragment = URI_RE.match(url).groups()
        normalize_uri = scheme is None or scheme.lower() in NORMALIZABLE_SCHEMES

        if scheme:
            scheme = scheme.lower()

        if authority:
            auth, _, host_port = authority.rpartition("@")
            auth = auth or None
            host, port = _HOST_PORT_RE.match(host_port).groups()
            if auth and normalize_uri:
                auth = _encode_invalid_chars(auth, USERINFO_CHARS)
            if port == "":
                port = None
        else:
            auth, host, port = None, None, None

        if port is not None:
            port = int(port)
            if not (0 <= port <= 65535):
                raise LocationParseError(url)

        host = _normalize_host(host, scheme)

        if normalize_uri and path:
            path = _remove_path_dot_segments(path)
            path = _encode_invalid_chars(path, PATH_CHARS)
        if normalize_uri and query:
            query = _encode_invalid_chars(query, QUERY_CHARS)
        if normalize_uri and fragment:
            fragment = _encode_invalid_chars(fragment, FRAGMENT_CHARS)

    except (ValueError, AttributeError):
        return six.raise_from(LocationParseError(source_url), None)

    # For the sake of backwards compatibility we put empty
    # string values for path if there are any defined values
    # beyond the path in the URL.
    # TODO: Remove this when we break backwards compatibility.
    if not path:
        if query is not None or fragment is not None:
            path = ""
        else:
            path = None

    # Ensure that each part of the URL is a `str` for
    # backwards compatibility.
    if isinstance(url, six.text_type):
        ensure_func = six.ensure_text
    else:
        ensure_func = six.ensure_str

    def ensure_type(x):
        return x if x is None else ensure_func(x)

    return Url(
        scheme=ensure_type(scheme),
        auth=ensure_type(auth),
        host=ensure_type(host),
        port=port,
        path=ensure_type(path),
        query=ensure_type(query),
        fragment=ensure_type(fragment),
    )


def get_host(url):
    """
    Deprecated. Use :func:`parse_url` instead.
    """
    p = parse_url(url)
    return p.scheme or "http", p.hostname, p.port

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\igor.py ===
"""
    pygments.lexers.igor
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for Igor Pro.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, words
from pygments.token import Text, Comment, Keyword, Name, String, Whitespace

__all__ = ['IgorLexer']


class IgorLexer(RegexLexer):
    """
    Pygments Lexer for Igor Pro procedure files (.ipf).
    """

    name = 'Igor'
    aliases = ['igor', 'igorpro']
    filenames = ['*.ipf']
    mimetypes = ['text/ipf']
    url = 'http://www.wavemetrics.com'
    version_added = '2.0'

    flags = re.IGNORECASE | re.MULTILINE

    flowControl = (
        'if', 'else', 'elseif', 'endif', 'for', 'endfor', 'strswitch', 'switch',
        'case', 'default', 'endswitch', 'do', 'while', 'try', 'catch', 'endtry',
        'break', 'continue', 'return', 'AbortOnRTE', 'AbortOnValue'
    )
    types = (
        'variable', 'string', 'constant', 'strconstant', 'NVAR', 'SVAR', 'WAVE',
        'STRUCT', 'dfref', 'funcref', 'char', 'uchar', 'int16', 'uint16', 'int32',
        'uint32', 'int64', 'uint64', 'float', 'double', 'int'
    )
    keywords = (
        'override', 'ThreadSafe', 'MultiThread', 'static',  'Proc',
        'Picture', 'Prompt', 'DoPrompt', 'macro', 'window', 'function', 'end',
        'Structure', 'EndStructure', 'EndMacro', 'Menu', 'SubMenu'
    )
    operations = (
        'Abort', 'AddFIFOData', 'AddFIFOVectData', 'AddMovieAudio', 'AddMovieFrame',
        'AddWavesToBoxPlot', 'AddWavesToViolinPlot', 'AdoptFiles', 'APMath', 'Append',
        'AppendBoxPlot', 'AppendImage', 'AppendLayoutObject', 'AppendMatrixContour',
        'AppendText', 'AppendToGizmo', 'AppendToGraph', 'AppendToLayout',
        'AppendToTable', 'AppendViolinPlot', 'AppendXYZContour', 'AutoPositionWindow',
        'AxonTelegraphFindServers', 'BackgroundInfo', 'Beep', 'BezierToPolygon',
        'BoundingBall', 'BoxSmooth', 'BrowseURL', 'BuildMenu', 'Button', 'cd', 'Chart',
        'CheckBox', 'CheckDisplayed', 'ChooseColor', 'Close', 'CloseHelp', 'CloseMovie',
        'CloseProc', 'ColorScale', 'ColorTab2Wave', 'Concatenate', 'ControlBar',
        'ControlInfo', 'ControlUpdate', 'ConvertGlobalStringTextEncoding', 'ConvexHull',
        'Convolve', 'CopyDimLabels', 'CopyFile', 'CopyFolder', 'CopyScales', 'Correlate',
        'CreateAliasShortcut', 'CreateBrowser', 'Cross', 'CtrlBackground', 'CtrlFIFO',
        'CtrlNamedBackground', 'Cursor', 'CurveFit', 'CustomControl', 'CWT',
        'DAQmx_AI_SetupReader', 'DAQmx_AO_SetOutputs', 'DAQmx_CTR_CountEdges',
        'DAQmx_CTR_OutputPulse', 'DAQmx_CTR_Period', 'DAQmx_CTR_PulseWidth',
        'DAQmx_DeviceInfo', 'DAQmx_DIO_Config', 'DAQmx_DIO_WriteNewData', 'DAQmx_Scan',
        'DAQmx_WaveformGen', 'Debugger', 'DebuggerOptions', 'DefaultFont',
        'DefaultGuiControls', 'DefaultGuiFont', 'DefaultTextEncoding', 'DefineGuide',
        'DelayUpdate', 'DeleteAnnotations', 'DeleteFile', 'DeleteFolder', 'DeletePoints',
        'Differentiate', 'dir', 'Display', 'DisplayHelpTopic', 'DisplayProcedure',
        'DoAlert', 'DoIgorMenu', 'DoUpdate', 'DoWindow', 'DoXOPIdle', 'DPSS',
        'DrawAction', 'DrawArc', 'DrawBezier', 'DrawLine', 'DrawOval', 'DrawPICT',
        'DrawPoly', 'DrawRect', 'DrawRRect', 'DrawText', 'DrawUserShape', 'DSPDetrend',
        'DSPPeriodogram', 'Duplicate', 'DuplicateDataFolder', 'DWT', 'EdgeStats', 'Edit',
        'ErrorBars', 'EstimatePeakSizes', 'Execute', 'ExecuteScriptText',
        'ExperimentInfo', 'ExperimentModified', 'ExportGizmo', 'Extract',
        'FastGaussTransform', 'FastOp', 'FBinRead', 'FBinWrite', 'FCALL_CallFunction',
        'FCALL_FreeLibrary', 'FCALL_GetFunctionList', 'FCALL_GetParamTypeList',
        'FCALL_LoadLibrary', 'FCALL_Version', 'FFT', 'FGetPos', 'FIFOStatus',
        'FIFO2Wave', 'FilterFIR', 'FilterIIR', 'FindAPeak', 'FindContour',
        'FindDuplicates', 'FindLevel', 'FindLevels', 'FindPeak', 'FindPointsInPoly',
        'FindRoots', 'FindSequence', 'FindValue', 'FMaxFlat', 'FPClustering', 'fprintf',
        'FReadLine', 'FSetPos', 'FStatus', 'FTPCreateDirectory', 'FTPDelete',
        'FTPDownload', 'FTPUpload', 'FuncFit', 'FuncFitMD', 'GBLoadWave', 'GetAxis',
        'GetCamera', 'GetFileFolderInfo', 'GetGizmo', 'GetLastUserMenuInfo',
        'GetMarquee', 'GetMouse', 'GetSelection', 'GetWindow', 'GISCreateVectorLayer',
        'GISGetRasterInfo', 'GISGetRegisteredFileInfo', 'GISGetVectorLayerInfo',
        'GISLoadRasterData', 'GISLoadVectorData', 'GISRasterizeVectorData',
        'GISRegisterFile', 'GISTransformCoords', 'GISUnRegisterFile',
        'GISWriteFieldData', 'GISWriteGeometryData', 'GISWriteRaster',
        'GPIBReadBinaryWave2', 'GPIBReadBinary2', 'GPIBReadWave2', 'GPIBRead2',
        'GPIBWriteBinaryWave2', 'GPIBWriteBinary2', 'GPIBWriteWave2', 'GPIBWrite2',
        'GPIB2', 'GraphNormal', 'GraphWaveDraw', 'GraphWaveEdit', 'Grep', 'GroupBox',
        'Hanning', 'HCluster', 'HDFInfo', 'HDFReadImage', 'HDFReadSDS', 'HDFReadVset',
        'HDF5CloseFile', 'HDF5CloseGroup', 'HDF5Control', 'HDF5CreateFile',
        'HDF5CreateGroup', 'HDF5CreateLink', 'HDF5DimensionScale', 'HDF5Dump',
        'HDF5DumpErrors', 'HDF5FlushFile', 'HDF5ListAttributes', 'HDF5ListGroup',
        'HDF5LoadData', 'HDF5LoadGroup', 'HDF5LoadImage', 'HDF5OpenFile',
         'HDF5OpenGroup', 'HDF5SaveData', 'HDF5SaveGroup', 'HDF5SaveImage',
         'HDF5UnlinkObject', 'HideIgorMenus', 'HideInfo', 'HideProcedures', 'HideTools',
         'HilbertTransform', 'Histogram', 'ICA', 'IFFT', 'ImageAnalyzeParticles',
         'ImageBlend', 'ImageBoundaryToMask', 'ImageComposite', 'ImageEdgeDetection',
         'ImageFileInfo', 'ImageFilter', 'ImageFocus', 'ImageFromXYZ',
         'ImageGenerateROIMask', 'ImageGLCM', 'ImageHistModification', 'ImageHistogram',
         'ImageInterpolate', 'ImageLineProfile', 'ImageLoad', 'ImageMorphology',
         'ImageRegistration', 'ImageRemoveBackground', 'ImageRestore', 'ImageRotate',
         'ImageSave', 'ImageSeedFill', 'ImageSkeleton3d', 'ImageSnake', 'ImageStats',
         'ImageThreshold', 'ImageTransform', 'ImageUnwrapPhase', 'ImageWindow',
         'IndexSort', 'InsertPoints', 'InstantFrequency', 'Integrate', 'IntegrateODE',
         'Integrate2D', 'Interpolate2', 'Interpolate3D', 'Interp3DPath', 'ITCCloseAll2',
         'ITCCloseDevice2', 'ITCConfigAllChannels2', 'ITCConfigChannelReset2',
         'ITCConfigChannelUpload2', 'ITCConfigChannel2', 'ITCFIFOAvailableAll2',
         'ITCFIFOAvailable2', 'ITCGetAllChannelsConfig2', 'ITCGetChannelConfig2',
         'ITCGetCurrentDevice2', 'ITCGetDeviceInfo2', 'ITCGetDevices2',
         'ITCGetErrorString2', 'ITCGetSerialNumber2', 'ITCGetState2', 'ITCGetVersions2',
         'ITCInitialize2', 'ITCOpenDevice2', 'ITCReadADC2', 'ITCReadDigital2',
         'ITCReadTimer2', 'ITCSelectDevice2', 'ITCSetDAC2', 'ITCSetGlobals2',
         'ITCSetModes2', 'ITCSetState2', 'ITCStartAcq2', 'ITCStopAcq2',
         'ITCUpdateFIFOPositionAll2', 'ITCUpdateFIFOPosition2', 'ITCWriteDigital2',
         'JCAMPLoadWave', 'JointHistogram', 'JSONXOP_AddTree', 'JSONXOP_AddValue',
         'JSONXOP_Dump', 'JSONXOP_GetArraySize', 'JSONXOP_GetKeys',
         'JSONXOP_GetMaxArraySize', 'JSONXOP_GetType', 'JSONXOP_GetValue', 'JSONXOP_New',
         'JSONXOP_Parse', 'JSONXOP_Release', 'JSONXOP_Remove', 'JSONXOP_Version',
         'KillBackground', 'KillControl', 'KillDataFolder', 'KillFIFO', 'KillFreeAxis',
         'KillPath', 'KillPICTs', 'KillStrings', 'KillVariables', 'KillWaves',
         'KillWindow', 'KMeans', 'Label', 'Layout', 'LayoutPageAction',
         'LayoutSlideShow', 'Legend', 'LinearFeedbackShiftRegister', 'ListBox',
         'LoadData', 'LoadPackagePreferences', 'LoadPICT', 'LoadWave', 'Loess',
         'LombPeriodogram', 'Make', 'MakeIndex', 'MarkPerfTestTime', 'MatrixBalance',
         'MatrixConvolve', 'MatrixCorr', 'MatrixEigenV', 'MatrixFactor', 'MatrixFilter',
         'MatrixGaussJ', 'MatrixGLM', 'MatrixInverse', 'MatrixLinearSolve',
         'MatrixLinearSolveTD', 'MatrixLLS', 'MatrixLUBkSub', 'MatrixLUD', 'MatrixLUDTD',
         'MatrixMultiply', 'MatrixMultiplyAdd', 'MatrixOP', 'MatrixReverseBalance',
         'MatrixSchur', 'MatrixSolve', 'MatrixSparse', 'MatrixSVBkSub', 'MatrixSVD',
         'MatrixTranspose', 'MCC_FindServers', 'MeasureStyledText',
         'MFR_CheckForNewBricklets', 'MFR_CloseResultFile', 'MFR_CreateOverviewTable',
         'MFR_GetBrickletCount', 'MFR_GetBrickletData', 'MFR_GetBrickletDeployData',
         'MFR_GetBrickletMetaData', 'MFR_GetBrickletRawData', 'MFR_GetReportTemplate',
         'MFR_GetResultFileMetaData', 'MFR_GetResultFileName',
         'MFR_GetVernissageVersion', 'MFR_GetVersion', 'MFR_GetXOPErrorMessage',
         'MFR_OpenResultFile', 'MLLoadWave', 'Modify', 'ModifyBoxPlot', 'ModifyBrowser',
         'ModifyCamera', 'ModifyContour', 'ModifyControl', 'ModifyControlList',
         'ModifyFreeAxis', 'ModifyGizmo', 'ModifyGraph', 'ModifyImage', 'ModifyLayout',
         'ModifyPanel', 'ModifyProcedure', 'ModifyTable', 'ModifyViolinPlot',
         'ModifyWaterfall', 'MoveDataFolder', 'MoveFile', 'MoveFolder', 'MoveString',
         'MoveSubwindow', 'MoveVariable', 'MoveWave', 'MoveWindow', 'MultiTaperPSD',
         'MultiThreadingControl', 'NC_CloseFile', 'NC_DumpErrors', 'NC_Inquire',
         'NC_ListAttributes', 'NC_ListObjects', 'NC_LoadData', 'NC_OpenFile',
         'NeuralNetworkRun', 'NeuralNetworkTrain', 'NewCamera', 'NewDataFolder',
         'NewFIFO', 'NewFIFOChan', 'NewFreeAxis', 'NewGizmo', 'NewImage', 'NewLayout',
         'NewMovie', 'NewNotebook', 'NewPanel', 'NewPath', 'NewWaterfall', 'NILoadWave',
         'NI4882', 'Note', 'Notebook', 'NotebookAction', 'Open', 'OpenHelp',
         'OpenNotebook', 'Optimize', 'ParseOperationTemplate', 'PathInfo',
         'PauseForUser', 'PauseUpdate', 'PCA', 'PlayMovie', 'PlayMovieAction',
         'PlaySound', 'PolygonOp', 'PopupContextualMenu', 'PopupMenu', 'Preferences',
         'PrimeFactors', 'Print', 'printf', 'PrintGraphs', 'PrintLayout',
         'PrintNotebook', 'PrintSettings', 'PrintTable', 'Project', 'PulseStats',
         'PutScrapText', 'pwd', 'Quit', 'RatioFromNumber', 'Redimension', 'Remez',
         'Remove', 'RemoveContour', 'RemoveFromGizmo', 'RemoveFromGraph',
         'RemoveFromLayout', 'RemoveFromTable', 'RemoveImage', 'RemoveLayoutObjects',
         'RemovePath', 'Rename', 'RenameDataFolder', 'RenamePath', 'RenamePICT',
         'RenameWindow', 'ReorderImages', 'ReorderTraces', 'ReplaceText', 'ReplaceWave',
         'Resample', 'ResumeUpdate', 'Reverse', 'Rotate', 'Save', 'SaveData',
         'SaveExperiment', 'SaveGizmoCopy', 'SaveGraphCopy', 'SaveNotebook',
         'SavePackagePreferences', 'SavePICT', 'SaveTableCopy', 'SetActiveSubwindow',
         'SetAxis', 'SetBackground', 'SetDashPattern', 'SetDataFolder', 'SetDimLabel',
         'SetDrawEnv', 'SetDrawLayer', 'SetFileFolderInfo', 'SetFormula',
         'SetIdlePeriod', 'SetIgorHook', 'SetIgorMenuMode', 'SetIgorOption',
         'SetMarquee', 'SetProcessSleep', 'SetRandomSeed', 'SetScale', 'SetVariable',
         'SetWaveLock', 'SetWaveTextEncoding', 'SetWindow', 'ShowIgorMenus', 'ShowInfo',
         'ShowTools', 'Silent', 'Sleep', 'Slider', 'Smooth', 'SmoothCustom', 'Sort',
         'SortColumns', 'SoundInRecord', 'SoundInSet', 'SoundInStartChart',
         'SoundInStatus', 'SoundInStopChart', 'SoundLoadWave', 'SoundSaveWave',
         'SphericalInterpolate', 'SphericalTriangulate', 'SplitString', 'SplitWave',
         'sprintf', 'SQLHighLevelOp', 'sscanf', 'Stack', 'StackWindows',
         'StatsAngularDistanceTest', 'StatsANOVA1Test', 'StatsANOVA2NRTest',
         'StatsANOVA2RMTest', 'StatsANOVA2Test', 'StatsChiTest',
         'StatsCircularCorrelationTest', 'StatsCircularMeans', 'StatsCircularMoments',
         'StatsCircularTwoSampleTest', 'StatsCochranTest', 'StatsContingencyTable',
         'StatsDIPTest', 'StatsDunnettTest', 'StatsFriedmanTest', 'StatsFTest',
         'StatsHodgesAjneTest', 'StatsJBTest', 'StatsKDE', 'StatsKendallTauTest',
         'StatsKSTest', 'StatsKWTest', 'StatsLinearCorrelationTest',
         'StatsLinearRegression', 'StatsMultiCorrelationTest', 'StatsNPMCTest',
         'StatsNPNominalSRTest', 'StatsQuantiles', 'StatsRankCorrelationTest',
         'StatsResample', 'StatsSample', 'StatsScheffeTest', 'StatsShapiroWilkTest',
         'StatsSignTest', 'StatsSRTest', 'StatsTTest', 'StatsTukeyTest',
         'StatsVariancesTest', 'StatsWatsonUSquaredTest', 'StatsWatsonWilliamsTest',
         'StatsWheelerWatsonTest', 'StatsWilcoxonRankTest', 'StatsWRCorrelationTest',
         'STFT', 'StructFill', 'StructGet', 'StructPut', 'SumDimension', 'SumSeries',
         'TabControl', 'Tag', 'TDMLoadData', 'TDMSaveData', 'TextBox', 'TextHistogram',
         'Text2Bezier', 'ThreadGroupPutDF', 'ThreadStart', 'TickWavesFromAxis', 'Tile',
         'TileWindows', 'TitleBox', 'ToCommandLine', 'ToolsGrid', 'Triangulate3d',
         'TUFXOP_AcquireLock', 'TUFXOP_Clear', 'TUFXOP_GetStorage', 'TUFXOP_Init',
         'TUFXOP_ReleaseLock', 'TUFXOP_RunningInMainThread', 'TUFXOP_Version', 'Unwrap',
         'UnzipFile', 'URLRequest', 'ValDisplay', 'VDTClosePort2', 'VDTGetPortList2',
         'VDTGetStatus2', 'VDTOpenPort2', 'VDTOperationsPort2', 'VDTReadBinaryWave2',
         'VDTReadBinary2', 'VDTReadHexWave2', 'VDTReadHex2', 'VDTReadWave2', 'VDTRead2',
         'VDTTerminalPort2', 'VDTWriteBinaryWave2', 'VDTWriteBinary2',
         'VDTWriteHexWave2', 'VDTWriteHex2', 'VDTWriteWave2', 'VDTWrite2', 'VDT2',
         'VISAControl', 'VISARead', 'VISAReadBinary', 'VISAReadBinaryWave',
         'VISAReadWave', 'VISAWrite', 'VISAWriteBinary', 'VISAWriteBinaryWave',
         'VISAWriteWave', 'WaveMeanStdv', 'WaveStats', 'WaveTracking', 'WaveTransform',
         'wfprintf', 'WignerTransform', 'WindowFunction', 'XLLoadWave'
    )
    functions = (
        'abs', 'acos', 'acosh', 'AddListItem', 'AiryA', 'AiryAD', 'AiryB', 'AiryBD',
         'alog', 'AnnotationInfo', 'AnnotationList', 'area', 'areaXY', 'asin', 'asinh',
         'atan', 'atanh', 'atan2', 'AxisInfo', 'AxisLabel', 'AxisList',
         'AxisValFromPixel', 'AxonTelegraphAGetDataNum', 'AxonTelegraphAGetDataString',
         'AxonTelegraphAGetDataStruct', 'AxonTelegraphGetDataNum',
         'AxonTelegraphGetDataString', 'AxonTelegraphGetDataStruct',
         'AxonTelegraphGetTimeoutMs', 'AxonTelegraphSetTimeoutMs', 'Base64Decode',
         'Base64Encode', 'Besseli', 'Besselj', 'Besselk', 'Bessely', 'beta', 'betai',
         'BinarySearch', 'BinarySearchInterp', 'binomial', 'binomialln', 'binomialNoise',
         'cabs', 'CaptureHistory', 'CaptureHistoryStart', 'ceil', 'centerOfMass',
         'centerOfMassXY', 'cequal', 'char2num', 'chebyshev', 'chebyshevU', 'CheckName',
         'ChildWindowList', 'CleanupName', 'cmplx', 'cmpstr', 'conj', 'ContourInfo',
         'ContourNameList', 'ContourNameToWaveRef', 'ContourZ', 'ControlNameList',
         'ConvertTextEncoding', 'cos', 'cosh', 'cosIntegral', 'cot', 'coth',
         'CountObjects', 'CountObjectsDFR', 'cpowi', 'CreateDataObjectName',
         'CreationDate', 'csc', 'csch', 'CsrInfo', 'CsrWave', 'CsrWaveRef', 'CsrXWave',
         'CsrXWaveRef', 'CTabList', 'DataFolderDir', 'DataFolderExists',
         'DataFolderList', 'DataFolderRefChanges', 'DataFolderRefsEqual',
         'DataFolderRefStatus', 'date', 'datetime', 'DateToJulian', 'date2secs',
         'Dawson', 'defined', 'deltax', 'digamma', 'dilogarithm', 'DimDelta',
         'DimOffset', 'DimSize', 'ei', 'ellipticE', 'ellipticK', 'enoise', 'equalWaves',
         'erf', 'erfc', 'erfcw', 'erfcx', 'exists', 'exp', 'expInt', 'expIntegralE1',
         'expNoise', 'factorial', 'Faddeeva', 'fakedata', 'faverage', 'faverageXY',
         'fDAQmx_AI_ChannelConfigs', 'fDAQmx_AI_GetReader', 'fDAQmx_AO_UpdateOutputs',
         'fDAQmx_ConnectTerminals', 'fDAQmx_CTR_Finished', 'fDAQmx_CTR_IsFinished',
         'fDAQmx_CTR_IsPulseFinished', 'fDAQmx_CTR_ReadCounter',
         'fDAQmx_CTR_ReadWithOptions', 'fDAQmx_CTR_SetPulseFrequency',
         'fDAQmx_CTR_Start', 'fDAQmx_DeviceNames', 'fDAQmx_DIO_Finished',
         'fDAQmx_DIO_PortWidth', 'fDAQmx_DIO_Read', 'fDAQmx_DIO_Write',
         'fDAQmx_DisconnectTerminals', 'fDAQmx_ErrorString', 'fDAQmx_ExternalCalDate',
         'fDAQmx_NumAnalogInputs', 'fDAQmx_NumAnalogOutputs', 'fDAQmx_NumCounters',
         'fDAQmx_NumDIOPorts', 'fDAQmx_ReadChan', 'fDAQmx_ReadNamedChan',
         'fDAQmx_ResetDevice', 'fDAQmx_ScanGetAvailable', 'fDAQmx_ScanGetNextIndex',
         'fDAQmx_ScanStart', 'fDAQmx_ScanStop', 'fDAQmx_ScanWait',
         'fDAQmx_ScanWaitWithTimeout', 'fDAQmx_SelfCalDate', 'fDAQmx_SelfCalibration',
         'fDAQmx_WaveformStart', 'fDAQmx_WaveformStop', 'fDAQmx_WF_IsFinished',
         'fDAQmx_WF_WaitUntilFinished', 'fDAQmx_WriteChan', 'FetchURL', 'FindDimLabel',
         'FindListItem', 'floor', 'FontList', 'FontSizeHeight', 'FontSizeStringWidth',
         'FresnelCos', 'FresnelSin', 'FuncRefInfo', 'FunctionInfo', 'FunctionList',
         'FunctionPath', 'gamma', 'gammaEuler', 'gammaInc', 'gammaNoise', 'gammln',
         'gammp', 'gammq', 'Gauss', 'Gauss1D', 'Gauss2D', 'gcd', 'GeometricMean',
         'GetBrowserLine', 'GetBrowserSelection', 'GetDataFolder', 'GetDataFolderDFR',
         'GetDefaultFont', 'GetDefaultFontSize', 'GetDefaultFontStyle', 'GetDimLabel',
         'GetEnvironmentVariable', 'GetErrMessage', 'GetFormula',
         'GetIndependentModuleName', 'GetIndexedObjName', 'GetIndexedObjNameDFR',
         'GetKeyState', 'GetRTErrMessage', 'GetRTError', 'GetRTLocation', 'GetRTLocInfo',
         'GetRTStackInfo', 'GetScrapText', 'GetUserData', 'GetWavesDataFolder',
         'GetWavesDataFolderDFR', 'GetWindowBrowserSelection', 'GISGetAllFileFormats',
         'GISSRefsAreEqual', 'GizmoInfo', 'GizmoScale', 'gnoise', 'GrepList',
         'GrepString', 'GuideInfo', 'GuideNameList', 'Hash', 'hcsr', 'HDF5AttributeInfo',
         'HDF5DatasetInfo', 'HDF5LibraryInfo', 'HDF5LinkInfo', 'HDF5TypeInfo', 'hermite',
         'hermiteGauss', 'HyperGNoise', 'HyperGPFQ', 'HyperG0F1', 'HyperG1F1',
         'HyperG2F1', 'i', 'IgorInfo', 'IgorVersion', 'imag', 'ImageInfo',
         'ImageNameList', 'ImageNameToWaveRef', 'IndependentModuleList', 'IndexedDir',
         'IndexedFile', 'IndexToScale', 'Inf', 'Integrate1D', 'interp', 'Interp2D',
         'Interp3D', 'inverseERF', 'inverseERFC', 'ItemsInList', 'JacobiCn', 'JacobiSn',
         'JulianToDate', 'Laguerre', 'LaguerreA', 'LaguerreGauss', 'LambertW',
         'LayoutInfo', 'leftx', 'LegendreA', 'limit', 'ListMatch', 'ListToTextWave',
         'ListToWaveRefWave', 'ln', 'log', 'logNormalNoise', 'lorentzianNoise',
         'LowerStr', 'MacroInfo', 'MacroList', 'MacroPath', 'magsqr', 'MandelbrotPoint',
         'MarcumQ', 'MatrixCondition', 'MatrixDet', 'MatrixDot', 'MatrixRank',
         'MatrixTrace', 'max', 'MCC_AutoBridgeBal', 'MCC_AutoFastComp',
         'MCC_AutoPipetteOffset', 'MCC_AutoSlowComp', 'MCC_AutoWholeCellComp',
         'MCC_GetBridgeBalEnable', 'MCC_GetBridgeBalResist', 'MCC_GetFastCompCap',
         'MCC_GetFastCompTau', 'MCC_GetHolding', 'MCC_GetHoldingEnable', 'MCC_GetMode',
         'MCC_GetNeutralizationCap', 'MCC_GetNeutralizationEnable',
         'MCC_GetOscKillerEnable', 'MCC_GetPipetteOffset', 'MCC_GetPrimarySignalGain',
         'MCC_GetPrimarySignalHPF', 'MCC_GetPrimarySignalLPF', 'MCC_GetRsCompBandwidth',
         'MCC_GetRsCompCorrection', 'MCC_GetRsCompEnable', 'MCC_GetRsCompPrediction',
         'MCC_GetSecondarySignalGain', 'MCC_GetSecondarySignalLPF', 'MCC_GetSlowCompCap',
         'MCC_GetSlowCompTau', 'MCC_GetSlowCompTauX20Enable',
        'MCC_GetSlowCurrentInjEnable', 'MCC_GetSlowCurrentInjLevel',
        'MCC_GetSlowCurrentInjSetlTime', 'MCC_GetWholeCellCompCap',
        'MCC_GetWholeCellCompEnable', 'MCC_GetWholeCellCompResist',
        'MCC_SelectMultiClamp700B', 'MCC_SetBridgeBalEnable', 'MCC_SetBridgeBalResist',
        'MCC_SetFastCompCap', 'MCC_SetFastCompTau', 'MCC_SetHolding',
        'MCC_SetHoldingEnable', 'MCC_SetMode', 'MCC_SetNeutralizationCap',
        'MCC_SetNeutralizationEnable', 'MCC_SetOscKillerEnable', 'MCC_SetPipetteOffset',
        'MCC_SetPrimarySignalGain', 'MCC_SetPrimarySignalHPF', 'MCC_SetPrimarySignalLPF',
        'MCC_SetRsCompBandwidth', 'MCC_SetRsCompCorrection', 'MCC_SetRsCompEnable',
        'MCC_SetRsCompPrediction', 'MCC_SetSecondarySignalGain',
        'MCC_SetSecondarySignalLPF', 'MCC_SetSlowCompCap', 'MCC_SetSlowCompTau',
        'MCC_SetSlowCompTauX20Enable', 'MCC_SetSlowCurrentInjEnable',
        'MCC_SetSlowCurrentInjLevel', 'MCC_SetSlowCurrentInjSetlTime',
        'MCC_SetTimeoutMs', 'MCC_SetWholeCellCompCap', 'MCC_SetWholeCellCompEnable',
        'MCC_SetWholeCellCompResist', 'mean', 'median', 'min', 'mod', 'ModDate',
        'MPFXEMGPeak', 'MPFXExpConvExpPeak', 'MPFXGaussPeak', 'MPFXLorentzianPeak',
        'MPFXVoigtPeak', 'NameOfWave', 'NaN', 'NewFreeDataFolder', 'NewFreeWave', 'norm',
        'NormalizeUnicode', 'note', 'NumberByKey', 'numpnts', 'numtype',
        'NumVarOrDefault', 'num2char', 'num2istr', 'num2str', 'NVAR_Exists',
        'OperationList', 'PadString', 'PanelResolution', 'ParamIsDefault',
        'ParseFilePath', 'PathList', 'pcsr', 'Pi', 'PICTInfo', 'PICTList',
        'PixelFromAxisVal', 'pnt2x', 'poissonNoise', 'poly', 'PolygonArea', 'poly2D',
        'PossiblyQuoteName', 'ProcedureText', 'ProcedureVersion', 'p2rect', 'qcsr',
        'real', 'RemoveByKey', 'RemoveEnding', 'RemoveFromList', 'RemoveListItem',
        'ReplaceNumberByKey', 'ReplaceString', 'ReplaceStringByKey', 'ReplicateString',
        'rightx', 'round', 'r2polar', 'sawtooth', 'scaleToIndex', 'ScreenResolution',
        'sec', 'sech', 'Secs2Date', 'Secs2Time', 'SelectNumber', 'SelectString',
        'SetEnvironmentVariable', 'sign', 'sin', 'sinc', 'sinh', 'sinIntegral',
        'SortList', 'SpecialCharacterInfo', 'SpecialCharacterList', 'SpecialDirPath',
        'SphericalBessJ', 'SphericalBessJD', 'SphericalBessY', 'SphericalBessYD',
        'SphericalHarmonics', 'SQLAllocHandle', 'SQLAllocStmt',
        'SQLBinaryWavesToTextWave', 'SQLBindCol', 'SQLBindParameter', 'SQLBrowseConnect',
        'SQLBulkOperations', 'SQLCancel', 'SQLCloseCursor', 'SQLColAttributeNum',
        'SQLColAttributeStr', 'SQLColumnPrivileges', 'SQLColumns', 'SQLConnect',
        'SQLDataSources', 'SQLDescribeCol', 'SQLDescribeParam', 'SQLDisconnect',
        'SQLDriverConnect', 'SQLDrivers', 'SQLEndTran', 'SQLError', 'SQLExecDirect',
        'SQLExecute', 'SQLFetch', 'SQLFetchScroll', 'SQLForeignKeys', 'SQLFreeConnect',
        'SQLFreeEnv', 'SQLFreeHandle', 'SQLFreeStmt', 'SQLGetConnectAttrNum',
        'SQLGetConnectAttrStr', 'SQLGetCursorName', 'SQLGetDataNum', 'SQLGetDataStr',
        'SQLGetDescFieldNum', 'SQLGetDescFieldStr', 'SQLGetDescRec',
        'SQLGetDiagFieldNum', 'SQLGetDiagFieldStr', 'SQLGetDiagRec', 'SQLGetEnvAttrNum',
        'SQLGetEnvAttrStr', 'SQLGetFunctions', 'SQLGetInfoNum', 'SQLGetInfoStr',
        'SQLGetStmtAttrNum', 'SQLGetStmtAttrStr', 'SQLGetTypeInfo', 'SQLMoreResults',
        'SQLNativeSql', 'SQLNumParams', 'SQLNumResultCols', 'SQLNumResultRowsIfKnown',
        'SQLNumRowsFetched', 'SQLParamData', 'SQLPrepare', 'SQLPrimaryKeys',
        'SQLProcedureColumns', 'SQLProcedures', 'SQLPutData', 'SQLReinitialize',
        'SQLRowCount', 'SQLSetConnectAttrNum', 'SQLSetConnectAttrStr',
        'SQLSetCursorName', 'SQLSetDescFieldNum', 'SQLSetDescFieldStr', 'SQLSetDescRec',
        'SQLSetEnvAttrNum', 'SQLSetEnvAttrStr', 'SQLSetPos', 'SQLSetStmtAttrNum',
        'SQLSetStmtAttrStr', 'SQLSpecialColumns', 'SQLStatistics', 'SQLTablePrivileges',
        'SQLTables', 'SQLTextWaveToBinaryWaves', 'SQLTextWaveTo2DBinaryWave',
        'SQLUpdateBoundValues', 'SQLXOPCheckState', 'SQL2DBinaryWaveToTextWave', 'sqrt',
        'StartMSTimer', 'StatsBetaCDF', 'StatsBetaPDF', 'StatsBinomialCDF',
        'StatsBinomialPDF', 'StatsCauchyCDF', 'StatsCauchyPDF', 'StatsChiCDF',
        'StatsChiPDF', 'StatsCMSSDCDF', 'StatsCorrelation', 'StatsDExpCDF',
        'StatsDExpPDF', 'StatsErlangCDF', 'StatsErlangPDF', 'StatsErrorPDF',
        'StatsEValueCDF', 'StatsEValuePDF', 'StatsExpCDF', 'StatsExpPDF', 'StatsFCDF',
        'StatsFPDF', 'StatsFriedmanCDF', 'StatsGammaCDF', 'StatsGammaPDF',
        'StatsGeometricCDF', 'StatsGeometricPDF', 'StatsGEVCDF', 'StatsGEVPDF',
        'StatsHyperGCDF', 'StatsHyperGPDF', 'StatsInvBetaCDF', 'StatsInvBinomialCDF',
        'StatsInvCauchyCDF', 'StatsInvChiCDF', 'StatsInvCMSSDCDF', 'StatsInvDExpCDF',
        'StatsInvEValueCDF', 'StatsInvExpCDF', 'StatsInvFCDF', 'StatsInvFriedmanCDF',
        'StatsInvGammaCDF', 'StatsInvGeometricCDF', 'StatsInvKuiperCDF',
        'StatsInvLogisticCDF', 'StatsInvLogNormalCDF', 'StatsInvMaxwellCDF',
        'StatsInvMooreCDF', 'StatsInvNBinomialCDF', 'StatsInvNCChiCDF', 'StatsInvNCFCDF',
        'StatsInvNormalCDF', 'StatsInvParetoCDF', 'StatsInvPoissonCDF',
        'StatsInvPowerCDF', 'StatsInvQCDF', 'StatsInvQpCDF', 'StatsInvRayleighCDF',
        'StatsInvRectangularCDF', 'StatsInvSpearmanCDF', 'StatsInvStudentCDF',
        'StatsInvTopDownCDF', 'StatsInvTriangularCDF', 'StatsInvUsquaredCDF',
        'StatsInvVonMisesCDF', 'StatsInvWeibullCDF', 'StatsKuiperCDF',
        'StatsLogisticCDF', 'StatsLogisticPDF', 'StatsLogNormalCDF', 'StatsLogNormalPDF',
        'StatsMaxwellCDF', 'StatsMaxwellPDF', 'StatsMedian', 'StatsMooreCDF',
        'StatsNBinomialCDF', 'StatsNBinomialPDF', 'StatsNCChiCDF', 'StatsNCChiPDF',
        'StatsNCFCDF', 'StatsNCFPDF', 'StatsNCTCDF', 'StatsNCTPDF', 'StatsNormalCDF',
        'StatsNormalPDF', 'StatsParetoCDF', 'StatsParetoPDF', 'StatsPermute',
        'StatsPoissonCDF', 'StatsPoissonPDF', 'StatsPowerCDF', 'StatsPowerNoise',
        'StatsPowerPDF', 'StatsQCDF', 'StatsQpCDF', 'StatsRayleighCDF',
        'StatsRayleighPDF', 'StatsRectangularCDF', 'StatsRectangularPDF', 'StatsRunsCDF',
        'StatsSpearmanRhoCDF', 'StatsStudentCDF', 'StatsStudentPDF', 'StatsTopDownCDF',
        'StatsTriangularCDF', 'StatsTriangularPDF', 'StatsTrimmedMean',
        'StatsUSquaredCDF', 'StatsVonMisesCDF', 'StatsVonMisesNoise', 'StatsVonMisesPDF',
        'StatsWaldCDF', 'StatsWaldPDF', 'StatsWeibullCDF', 'StatsWeibullPDF',
        'StopMSTimer', 'StringByKey', 'stringCRC', 'StringFromList', 'StringList',
        'stringmatch', 'StringToUnsignedByteWave', 'strlen', 'strsearch',
        'StrVarOrDefault', 'str2num', 'StudentA', 'StudentT', 'sum', 'SVAR_Exists',
        'TableInfo', 'TagVal', 'TagWaveRef', 'tan', 'tanh', 'TDMAddChannel',
        'TDMAddGroup', 'TDMAppendDataValues', 'TDMAppendDataValuesTime',
        'TDMChannelPropertyExists', 'TDMCloseChannel', 'TDMCloseFile', 'TDMCloseGroup',
        'TDMCreateChannelProperty', 'TDMCreateFile', 'TDMCreateFileProperty',
        'TDMCreateGroupProperty', 'TDMFilePropertyExists', 'TDMGetChannelPropertyNames',
        'TDMGetChannelPropertyNum', 'TDMGetChannelPropertyStr',
        'TDMGetChannelPropertyTime', 'TDMGetChannelPropertyType', 'TDMGetChannels',
        'TDMGetChannelStringPropertyLen', 'TDMGetDataType', 'TDMGetDataValues',
        'TDMGetDataValuesTime', 'TDMGetFilePropertyNames', 'TDMGetFilePropertyNum',
        'TDMGetFilePropertyStr', 'TDMGetFilePropertyTime', 'TDMGetFilePropertyType',
        'TDMGetFileStringPropertyLen', 'TDMGetGroupPropertyNames',
        'TDMGetGroupPropertyNum', 'TDMGetGroupPropertyStr', 'TDMGetGroupPropertyTime',
        'TDMGetGroupPropertyType', 'TDMGetGroups', 'TDMGetGroupStringPropertyLen',
        'TDMGetLibraryErrorDescription', 'TDMGetNumChannelProperties',
        'TDMGetNumChannels', 'TDMGetNumDataValues', 'TDMGetNumFileProperties',
        'TDMGetNumGroupProperties', 'TDMGetNumGroups', 'TDMGroupPropertyExists',
        'TDMOpenFile', 'TDMOpenFileEx', 'TDMRemoveChannel', 'TDMRemoveGroup',
        'TDMReplaceDataValues', 'TDMReplaceDataValuesTime', 'TDMSaveFile',
        'TDMSetChannelPropertyNum', 'TDMSetChannelPropertyStr',
        'TDMSetChannelPropertyTime', 'TDMSetDataValues', 'TDMSetDataValuesTime',
        'TDMSetFilePropertyNum', 'TDMSetFilePropertyStr', 'TDMSetFilePropertyTime',
        'TDMSetGroupPropertyNum', 'TDMSetGroupPropertyStr', 'TDMSetGroupPropertyTime',
        'TextEncodingCode', 'TextEncodingName', 'TextFile', 'ThreadGroupCreate',
        'ThreadGroupGetDF', 'ThreadGroupGetDFR', 'ThreadGroupRelease', 'ThreadGroupWait',
        'ThreadProcessorCount', 'ThreadReturnValue', 'ticks', 'time', 'TraceFromPixel',
        'TraceInfo', 'TraceNameList', 'TraceNameToWaveRef', 'TrimString', 'trunc',
        'UniqueName', 'UnPadString', 'UnsetEnvironmentVariable', 'UpperStr', 'URLDecode',
        'URLEncode', 'VariableList', 'Variance', 'vcsr', 'viAssertIntrSignal',
        'viAssertTrigger', 'viAssertUtilSignal', 'viClear', 'viClose', 'viDisableEvent',
        'viDiscardEvents', 'viEnableEvent', 'viFindNext', 'viFindRsrc', 'viGetAttribute',
        'viGetAttributeString', 'viGpibCommand', 'viGpibControlATN', 'viGpibControlREN',
        'viGpibPassControl', 'viGpibSendIFC', 'viIn8', 'viIn16', 'viIn32', 'viLock',
        'viMapAddress', 'viMapTrigger', 'viMemAlloc', 'viMemFree', 'viMoveIn8',
        'viMoveIn16', 'viMoveIn32', 'viMoveOut8', 'viMoveOut16', 'viMoveOut32', 'viOpen',
        'viOpenDefaultRM', 'viOut8', 'viOut16', 'viOut32', 'viPeek8', 'viPeek16',
        'viPeek32', 'viPoke8', 'viPoke16', 'viPoke32', 'viRead', 'viReadSTB',
        'viSetAttribute', 'viSetAttributeString', 'viStatusDesc', 'viTerminate',
        'viUnlock', 'viUnmapAddress', 'viUnmapTrigger', 'viUsbControlIn',
        'viUsbControlOut', 'viVxiCommandQuery', 'viWaitOnEvent', 'viWrite', 'VoigtFunc',
        'VoigtPeak', 'WaveCRC', 'WaveDataToString', 'WaveDims', 'WaveExists', 'WaveHash',
        'WaveInfo', 'WaveList', 'WaveMax', 'WaveMin', 'WaveMinAndMax', 'WaveModCount',
        'WaveName', 'WaveRefIndexed', 'WaveRefIndexedDFR', 'WaveRefsEqual',
        'WaveRefWaveToList', 'WaveTextEncoding', 'WaveType', 'WaveUnits',
        'WhichListItem', 'WinList', 'WinName', 'WinRecreation', 'WinType', 'wnoise',
        'xcsr', 'XWaveName', 'XWaveRefFromTrace', 'x2pnt', 'zcsr', 'ZernikeR',
        'zeromq_client_connect', 'zeromq_client_recv', 'zeromq_client_send',
        'zeromq_handler_start', 'zeromq_handler_stop', 'zeromq_pub_bind',
        'zeromq_pub_send', 'zeromq_server_bind', 'zeromq_server_recv',
        'zeromq_server_send', 'zeromq_set', 'zeromq_set_logging_template', 'zeromq_stop',
        'zeromq_sub_add_filter', 'zeromq_sub_connect', 'zeromq_sub_recv',
        'zeromq_sub_remove_filter', 'zeromq_test_callfunction',
        'zeromq_test_serializeWave', 'zeta'
    )

    tokens = {
        'root': [
            (r'//.*$', Comment.Single),
            (r'"([^"\\]|\\.)*"', String),
            # Flow Control.
            (words(flowControl, prefix=r'\b', suffix=r'\b'), Keyword),
            # Types.
            (words(types, prefix=r'\b', suffix=r'\b'), Keyword.Type),
            # Keywords.
            (words(keywords, prefix=r'\b', suffix=r'\b'), Keyword.Reserved),
            # Built-in operations.
            (words(operations, prefix=r'\b', suffix=r'\b'), Name.Class),
            # Built-in functions.
            (words(functions, prefix=r'\b', suffix=r'\b'), Name.Function),
            # Compiler directives.
            (r'^#(include|pragma|define|undef|ifdef|ifndef|if|elif|else|endif)',
             Name.Decorator),
            (r'\s+', Whitespace),
            (r'[^a-z"/]+$', Text),
            (r'.', Text),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\zmq\backend\cffi\socket.py ===
"""zmq Socket class"""

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.

import errno as errno_mod
import warnings

import zmq
from zmq.constants import SocketOption, _OptType
from zmq.error import ZMQError, _check_rc, _check_version

from ._cffi import ffi
from ._cffi import lib as C
from .message import Frame
from .utils import _retry_sys_call

nsp = new_sizet_pointer = lambda length: ffi.new('size_t*', length)


def new_uint64_pointer():
    return ffi.new('uint64_t*'), nsp(ffi.sizeof('uint64_t'))


def new_int64_pointer():
    return ffi.new('int64_t*'), nsp(ffi.sizeof('int64_t'))


def new_int_pointer():
    return ffi.new('int*'), nsp(ffi.sizeof('int'))


def new_binary_data(length):
    return ffi.new(f'char[{length:d}]'), nsp(ffi.sizeof('char') * length)


def value_uint64_pointer(val):
    return ffi.new('uint64_t*', val), ffi.sizeof('uint64_t')


def value_int64_pointer(val):
    return ffi.new('int64_t*', val), ffi.sizeof('int64_t')


def value_int_pointer(val):
    return ffi.new('int*', val), ffi.sizeof('int')


def value_binary_data(val, length):
    return ffi.new(f'char[{length + 1:d}]', val), ffi.sizeof('char') * length


_fd_size = ffi.sizeof('ZMQ_FD_T')
ZMQ_FD_64BIT = _fd_size == 8

IPC_PATH_MAX_LEN = C.get_ipc_path_max_len()


def new_pointer_from_opt(option, length=0):
    opt_type = getattr(option, "_opt_type", _OptType.int)

    if opt_type == _OptType.int64 or (ZMQ_FD_64BIT and opt_type == _OptType.fd):
        return new_int64_pointer()
    elif opt_type == _OptType.bytes:
        return new_binary_data(length)
    else:
        # default
        return new_int_pointer()


def value_from_opt_pointer(option, opt_pointer, length=0):
    try:
        option = SocketOption(option)
    except ValueError:
        # unrecognized option,
        # assume from the future,
        # let EINVAL raise
        opt_type = _OptType.int
    else:
        opt_type = option._opt_type

    if opt_type == _OptType.bytes:
        return ffi.buffer(opt_pointer, length)[:]
    else:
        return int(opt_pointer[0])


def initialize_opt_pointer(option, value, length=0):
    opt_type = getattr(option, "_opt_type", _OptType.int)
    if opt_type == _OptType.int64 or (ZMQ_FD_64BIT and opt_type == _OptType.fd):
        return value_int64_pointer(value)
    elif opt_type == _OptType.bytes:
        return value_binary_data(value, length)
    else:
        return value_int_pointer(value)


class Socket:
    context = None
    socket_type = None
    _zmq_socket = None
    _closed = None
    _ref = None
    _shadow = False
    _draft_poller = None
    _draft_poller_ptr = None
    copy_threshold = 0

    def __init__(self, context=None, socket_type=None, shadow=0, copy_threshold=None):
        if copy_threshold is None:
            copy_threshold = zmq.COPY_THRESHOLD
        self.copy_threshold = copy_threshold

        self.context = context
        self._draft_poller = self._draft_poller_ptr = None
        if shadow:
            self._zmq_socket = ffi.cast("void *", shadow)
            self._shadow = True
        else:
            self._shadow = False
            self._zmq_socket = C.zmq_socket(context._zmq_ctx, socket_type)
        if self._zmq_socket == ffi.NULL:
            raise ZMQError()
        self._closed = False

    @property
    def underlying(self):
        """The address of the underlying libzmq socket"""
        return int(ffi.cast('size_t', self._zmq_socket))

    def _check_closed_deep(self):
        """thorough check of whether the socket has been closed,
        even if by another entity (e.g. ctx.destroy).

        Only used by the `closed` property.

        returns True if closed, False otherwise
        """
        if self._closed:
            return True
        try:
            self.get(zmq.TYPE)
        except ZMQError as e:
            if e.errno == zmq.ENOTSOCK:
                self._closed = True
                return True
            elif e.errno == zmq.ETERM:
                pass
            else:
                raise
        return False

    @property
    def closed(self):
        return self._check_closed_deep()

    def close(self, linger=None):
        rc = 0
        if not self._closed and hasattr(self, '_zmq_socket'):
            if self._draft_poller_ptr is not None:
                rc = C.zmq_poller_destroy(self._draft_poller_ptr)
                self._draft_poller = self._draft_poller_ptr = None

            if self._zmq_socket is not None:
                if linger is not None:
                    self.set(zmq.LINGER, linger)
                rc = C.zmq_close(self._zmq_socket)
            self._closed = True
        if rc < 0:
            _check_rc(rc)

    def bind(self, address):
        if isinstance(address, str):
            address_b = address.encode('utf8')
        else:
            address_b = address
        if isinstance(address, bytes):
            address = address_b.decode('utf8')
        rc = C.zmq_bind(self._zmq_socket, address_b)
        if rc < 0:
            if IPC_PATH_MAX_LEN and C.zmq_errno() == errno_mod.ENAMETOOLONG:
                path = address.split('://', 1)[-1]
                msg = (
                    f'ipc path "{path}" is longer than {IPC_PATH_MAX_LEN} '
                    'characters (sizeof(sockaddr_un.sun_path)).'
                )
                raise ZMQError(C.zmq_errno(), msg=msg)
            elif C.zmq_errno() == errno_mod.ENOENT:
                path = address.split('://', 1)[-1]
                msg = f'No such file or directory for ipc path "{path}".'
                raise ZMQError(C.zmq_errno(), msg=msg)
            else:
                _check_rc(rc)

    def unbind(self, address):
        if isinstance(address, str):
            address = address.encode('utf8')
        rc = C.zmq_unbind(self._zmq_socket, address)
        _check_rc(rc)

    def connect(self, address):
        if isinstance(address, str):
            address = address.encode('utf8')
        rc = C.zmq_connect(self._zmq_socket, address)
        _check_rc(rc)

    def disconnect(self, address):
        if isinstance(address, str):
            address = address.encode('utf8')
        rc = C.zmq_disconnect(self._zmq_socket, address)
        _check_rc(rc)

    def set(self, option, value):
        length = None
        if isinstance(value, str):
            raise TypeError("unicode not allowed, use bytes")

        try:
            option = SocketOption(option)
        except ValueError:
            # unrecognized option,
            # assume from the future,
            # let EINVAL raise
            opt_type = _OptType.int
        else:
            opt_type = option._opt_type

        if isinstance(value, bytes):
            if opt_type != _OptType.bytes:
                raise TypeError(f"not a bytes sockopt: {option}")
            length = len(value)

        c_value_pointer, c_sizet = initialize_opt_pointer(option, value, length)

        _retry_sys_call(
            C.zmq_setsockopt,
            self._zmq_socket,
            option,
            ffi.cast('void*', c_value_pointer),
            c_sizet,
        )

    def get(self, option):
        try:
            option = SocketOption(option)
        except ValueError:
            # unrecognized option,
            # assume from the future,
            # let EINVAL raise
            opt_type = _OptType.int
        else:
            opt_type = option._opt_type

        if option == zmq.FD and self._draft_poller is not None:
            c_value_pointer, _ = new_pointer_from_opt(option)
            C.zmq_poller_fd(self._draft_poller, ffi.cast('void*', c_value_pointer))
            return int(c_value_pointer[0])

        c_value_pointer, c_sizet_pointer = new_pointer_from_opt(option, length=255)

        try:
            _retry_sys_call(
                C.zmq_getsockopt,
                self._zmq_socket,
                option,
                c_value_pointer,
                c_sizet_pointer,
            )
        except ZMQError as e:
            if (
                option == SocketOption.FD
                and e.errno == zmq.Errno.EINVAL
                and self.get(SocketOption.THREAD_SAFE)
            ):
                _check_version((4, 3, 2), "draft socket FD support via zmq_poller_fd")
                if not zmq.has('draft'):
                    raise RuntimeError("libzmq must be built with draft support")
                warnings.warn(zmq.error.DraftFDWarning(), stacklevel=2)

                # create a poller and retrieve its fd
                self._draft_poller_ptr = ffi.new("void*[1]")
                self._draft_poller_ptr[0] = self._draft_poller = C.zmq_poller_new()
                if self._draft_poller == ffi.NULL:
                    # failed (why?), raise original error
                    self._draft_poller_ptr = self._draft_poller = None
                    raise
                # register self with poller
                rc = C.zmq_poller_add(
                    self._draft_poller,
                    self._zmq_socket,
                    ffi.NULL,
                    zmq.POLLIN | zmq.POLLOUT,
                )
                _check_rc(rc)
                # use poller fd as proxy for ours
                rc = C.zmq_poller_fd(
                    self._draft_poller, ffi.cast('void *', c_value_pointer)
                )
                _check_rc(rc)
                return int(c_value_pointer[0])
            else:
                raise

        sz = c_sizet_pointer[0]
        v = value_from_opt_pointer(option, c_value_pointer, sz)
        if (
            option != zmq.SocketOption.ROUTING_ID
            and opt_type == _OptType.bytes
            and v.endswith(b'\0')
        ):
            v = v[:-1]
        return v

    def _send_copy(self, buf, flags):
        """Send a copy of a bufferable"""
        zmq_msg = ffi.new('zmq_msg_t*')
        if not isinstance(buf, bytes):
            # cast any bufferable data to bytes via memoryview
            buf = memoryview(buf).tobytes()

        c_message = ffi.new('char[]', buf)
        rc = C.zmq_msg_init_size(zmq_msg, len(buf))
        _check_rc(rc)
        C.memcpy(C.zmq_msg_data(zmq_msg), c_message, len(buf))
        _retry_sys_call(C.zmq_msg_send, zmq_msg, self._zmq_socket, flags)
        rc2 = C.zmq_msg_close(zmq_msg)
        _check_rc(rc2)

    def _send_frame(self, frame, flags):
        """Send a Frame on this socket in a non-copy manner."""
        # Always copy the Frame so the original message isn't garbage collected.
        # This doesn't do a real copy, just a reference.
        frame_copy = frame.fast_copy()
        zmq_msg = frame_copy.zmq_msg
        _retry_sys_call(C.zmq_msg_send, zmq_msg, self._zmq_socket, flags)
        tracker = frame_copy.tracker
        frame_copy.close()
        return tracker

    def send(self, data, flags=0, copy=False, track=False):
        if isinstance(data, str):
            raise TypeError("Message must be in bytes, not a unicode object")

        if copy and not isinstance(data, Frame):
            return self._send_copy(data, flags)
        else:
            close_frame = False
            if isinstance(data, Frame):
                if track and not data.tracker:
                    raise ValueError('Not a tracked message')
                frame = data
            else:
                if self.copy_threshold:
                    buf = memoryview(data)
                    # always copy messages smaller than copy_threshold
                    if buf.nbytes < self.copy_threshold:
                        self._send_copy(buf, flags)
                        return zmq._FINISHED_TRACKER
                frame = Frame(data, track=track, copy_threshold=self.copy_threshold)
                close_frame = True

            tracker = self._send_frame(frame, flags)
            if close_frame:
                frame.close()
            return tracker

    def recv(self, flags=0, copy=True, track=False):
        if copy:
            zmq_msg = ffi.new('zmq_msg_t*')
            C.zmq_msg_init(zmq_msg)
        else:
            frame = zmq.Frame(track=track)
            zmq_msg = frame.zmq_msg

        try:
            _retry_sys_call(C.zmq_msg_recv, zmq_msg, self._zmq_socket, flags)
        except Exception:
            if copy:
                C.zmq_msg_close(zmq_msg)
            raise

        if not copy:
            return frame

        _buffer = ffi.buffer(C.zmq_msg_data(zmq_msg), C.zmq_msg_size(zmq_msg))
        _bytes = _buffer[:]
        rc = C.zmq_msg_close(zmq_msg)
        _check_rc(rc)
        return _bytes

    def recv_into(self, buffer, /, *, nbytes: int = 0, flags: int = 0) -> int:
        view = memoryview(buffer)
        if not view.contiguous:
            raise BufferError("Can only recv_into contiguous buffers")
        if view.readonly:
            raise BufferError("Cannot recv_into readonly buffer")
        if nbytes < 0:
            raise ValueError(f"{nbytes=} must be non-negative")
        view_bytes = view.nbytes
        if nbytes == 0:
            nbytes = view_bytes
        elif nbytes > view_bytes:
            raise ValueError(f"{nbytes=} too big for memoryview of {view_bytes}B")
        c_buf = ffi.from_buffer(view)
        rc: int = _retry_sys_call(C.zmq_recv, self._zmq_socket, c_buf, nbytes, flags)
        _check_rc(rc)
        return rc

    def monitor(self, addr, events=-1):
        """s.monitor(addr, flags)

        Start publishing socket events on inproc.
        See libzmq docs for zmq_monitor for details.

        Note: requires libzmq >= 3.2

        Parameters
        ----------
        addr : str
            The inproc url used for monitoring. Passing None as
            the addr will cause an existing socket monitor to be
            deregistered.
        events : int [default: zmq.EVENT_ALL]
            The zmq event bitmask for which events will be sent to the monitor.
        """
        if events < 0:
            events = zmq.EVENT_ALL
        if addr is None:
            addr = ffi.NULL
        if isinstance(addr, str):
            addr = addr.encode('utf8')
        C.zmq_socket_monitor(self._zmq_socket, addr, events)


__all__ = ['Socket', 'IPC_PATH_MAX_LEN']

# === NexusCore/openenv\Lib\site-packages\pyparsing\common.py ===
# common.py
from .core import *
from .helpers import DelimitedList, any_open_tag, any_close_tag
from datetime import datetime


# some other useful expressions - using lower-case class name since we are really using this as a namespace
class pyparsing_common:
    """Here are some common low-level expressions that may be useful in
    jump-starting parser development:

    - numeric forms (:class:`integers<integer>`, :class:`reals<real>`,
      :class:`scientific notation<sci_real>`)
    - common :class:`programming identifiers<identifier>`
    - network addresses (:class:`MAC<mac_address>`,
      :class:`IPv4<ipv4_address>`, :class:`IPv6<ipv6_address>`)
    - ISO8601 :class:`dates<iso8601_date>` and
      :class:`datetime<iso8601_datetime>`
    - :class:`UUID<uuid>`
    - :class:`comma-separated list<comma_separated_list>`
    - :class:`url`

    Parse actions:

    - :class:`convert_to_integer`
    - :class:`convert_to_float`
    - :class:`convert_to_date`
    - :class:`convert_to_datetime`
    - :class:`strip_html_tags`
    - :class:`upcase_tokens`
    - :class:`downcase_tokens`

    Example::

        pyparsing_common.number.run_tests('''
            # any int or real number, returned as the appropriate type
            100
            -100
            +100
            3.14159
            6.02e23
            1e-12
            ''')

        pyparsing_common.fnumber.run_tests('''
            # any int or real number, returned as float
            100
            -100
            +100
            3.14159
            6.02e23
            1e-12
            ''')

        pyparsing_common.hex_integer.run_tests('''
            # hex numbers
            100
            FF
            ''')

        pyparsing_common.fraction.run_tests('''
            # fractions
            1/2
            -3/4
            ''')

        pyparsing_common.mixed_integer.run_tests('''
            # mixed fractions
            1
            1/2
            -3/4
            1-3/4
            ''')

        import uuid
        pyparsing_common.uuid.set_parse_action(token_map(uuid.UUID))
        pyparsing_common.uuid.run_tests('''
            # uuid
            12345678-1234-5678-1234-567812345678
            ''')

    prints::

        # any int or real number, returned as the appropriate type
        100
        [100]

        -100
        [-100]

        +100
        [100]

        3.14159
        [3.14159]

        6.02e23
        [6.02e+23]

        1e-12
        [1e-12]

        # any int or real number, returned as float
        100
        [100.0]

        -100
        [-100.0]

        +100
        [100.0]

        3.14159
        [3.14159]

        6.02e23
        [6.02e+23]

        1e-12
        [1e-12]

        # hex numbers
        100
        [256]

        FF
        [255]

        # fractions
        1/2
        [0.5]

        -3/4
        [-0.75]

        # mixed fractions
        1
        [1]

        1/2
        [0.5]

        -3/4
        [-0.75]

        1-3/4
        [1.75]

        # uuid
        12345678-1234-5678-1234-567812345678
        [UUID('12345678-1234-5678-1234-567812345678')]
    """

    convert_to_integer = token_map(int)
    """
    Parse action for converting parsed integers to Python int
    """

    convert_to_float = token_map(float)
    """
    Parse action for converting parsed numbers to Python float
    """

    integer = Word(nums).set_name("integer").set_parse_action(convert_to_integer)
    """expression that parses an unsigned integer, returns an int"""

    hex_integer = (
        Word(hexnums).set_name("hex integer").set_parse_action(token_map(int, 16))
    )
    """expression that parses a hexadecimal integer, returns an int"""

    signed_integer = (
        Regex(r"[+-]?\d+")
        .set_name("signed integer")
        .set_parse_action(convert_to_integer)
    )
    """expression that parses an integer with optional leading sign, returns an int"""

    fraction = (
        signed_integer().set_parse_action(convert_to_float)
        + "/"
        + signed_integer().set_parse_action(convert_to_float)
    ).set_name("fraction")
    """fractional expression of an integer divided by an integer, returns a float"""
    fraction.add_parse_action(lambda tt: tt[0] / tt[-1])

    mixed_integer = (
        fraction | signed_integer + Opt(Opt("-").suppress() + fraction)
    ).set_name("fraction or mixed integer-fraction")
    """mixed integer of the form 'integer - fraction', with optional leading integer, returns float"""
    mixed_integer.add_parse_action(sum)

    real = (
        Regex(r"[+-]?(?:\d+\.\d*|\.\d+)")
        .set_name("real number")
        .set_parse_action(convert_to_float)
    )
    """expression that parses a floating point number and returns a float"""

    sci_real = (
        Regex(r"[+-]?(?:\d+(?:[eE][+-]?\d+)|(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?)")
        .set_name("real number with scientific notation")
        .set_parse_action(convert_to_float)
    )
    """expression that parses a floating point number with optional
    scientific notation and returns a float"""

    # streamlining this expression makes the docs nicer-looking
    number = (sci_real | real | signed_integer).set_name("number").streamline()
    """any numeric expression, returns the corresponding Python type"""

    fnumber = (
        Regex(r"[+-]?\d+\.?\d*(?:[eE][+-]?\d+)?")
        .set_name("fnumber")
        .set_parse_action(convert_to_float)
    )
    """any int or real number, returned as float"""

    ieee_float = (
        Regex(r"(?i:[+-]?(?:(?:\d+\.?\d*(?:e[+-]?\d+)?)|nan|inf(?:inity)?))")
        .set_name("ieee_float")
        .set_parse_action(convert_to_float)
    )
    """any floating-point literal (int, real number, infinity, or NaN), returned as float"""

    identifier = Word(identchars, identbodychars).set_name("identifier")
    """typical code identifier (leading alpha or '_', followed by 0 or more alphas, nums, or '_')"""

    ipv4_address = Regex(
        r"(25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})(\.(25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})){3}"
    ).set_name("IPv4 address")
    "IPv4 address (``0.0.0.0 - 255.255.255.255``)"

    _ipv6_part = Regex(r"[0-9a-fA-F]{1,4}").set_name("hex_integer")
    _full_ipv6_address = (_ipv6_part + (":" + _ipv6_part) * 7).set_name(
        "full IPv6 address"
    )
    _short_ipv6_address = (
        Opt(_ipv6_part + (":" + _ipv6_part) * (0, 6))
        + "::"
        + Opt(_ipv6_part + (":" + _ipv6_part) * (0, 6))
    ).set_name("short IPv6 address")
    _short_ipv6_address.add_condition(
        lambda t: sum(1 for tt in t if pyparsing_common._ipv6_part.matches(tt)) < 8
    )
    _mixed_ipv6_address = ("::ffff:" + ipv4_address).set_name("mixed IPv6 address")
    ipv6_address = Combine(
        (_full_ipv6_address | _mixed_ipv6_address | _short_ipv6_address).set_name(
            "IPv6 address"
        )
    ).set_name("IPv6 address")
    "IPv6 address (long, short, or mixed form)"

    mac_address = Regex(
        r"[0-9a-fA-F]{2}([:.-])[0-9a-fA-F]{2}(?:\1[0-9a-fA-F]{2}){4}"
    ).set_name("MAC address")
    "MAC address xx:xx:xx:xx:xx (may also have '-' or '.' delimiters)"

    @staticmethod
    def convert_to_date(fmt: str = "%Y-%m-%d"):
        """
        Helper to create a parse action for converting parsed date string to Python datetime.date

        Params -
        - fmt - format to be passed to datetime.strptime (default= ``"%Y-%m-%d"``)

        Example::

            date_expr = pyparsing_common.iso8601_date.copy()
            date_expr.set_parse_action(pyparsing_common.convert_to_date())
            print(date_expr.parse_string("1999-12-31"))

        prints::

            [datetime.date(1999, 12, 31)]
        """

        def cvt_fn(ss, ll, tt):
            try:
                return datetime.strptime(tt[0], fmt).date()
            except ValueError as ve:
                raise ParseException(ss, ll, str(ve))

        return cvt_fn

    @staticmethod
    def convert_to_datetime(fmt: str = "%Y-%m-%dT%H:%M:%S.%f"):
        """Helper to create a parse action for converting parsed
        datetime string to Python datetime.datetime

        Params -
        - fmt - format to be passed to datetime.strptime (default= ``"%Y-%m-%dT%H:%M:%S.%f"``)

        Example::

            dt_expr = pyparsing_common.iso8601_datetime.copy()
            dt_expr.set_parse_action(pyparsing_common.convert_to_datetime())
            print(dt_expr.parse_string("1999-12-31T23:59:59.999"))

        prints::

            [datetime.datetime(1999, 12, 31, 23, 59, 59, 999000)]
        """

        def cvt_fn(s, l, t):
            try:
                return datetime.strptime(t[0], fmt)
            except ValueError as ve:
                raise ParseException(s, l, str(ve))

        return cvt_fn

    iso8601_date = Regex(
        r"(?P<year>\d{4})(?:-(?P<month>\d\d)(?:-(?P<day>\d\d))?)?"
    ).set_name("ISO8601 date")
    "ISO8601 date (``yyyy-mm-dd``)"

    iso8601_datetime = Regex(
        r"(?P<year>\d{4})-(?P<month>\d\d)-(?P<day>\d\d)[T ](?P<hour>\d\d):(?P<minute>\d\d)(:(?P<second>\d\d(\.\d*)?)?)?(?P<tz>Z|[+-]\d\d:?\d\d)?"
    ).set_name("ISO8601 datetime")
    "ISO8601 datetime (``yyyy-mm-ddThh:mm:ss.s(Z|+-00:00)``) - trailing seconds, milliseconds, and timezone optional; accepts separating ``'T'`` or ``' '``"

    uuid = Regex(r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}").set_name("UUID")
    "UUID (``xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx``)"

    _html_stripper = any_open_tag.suppress() | any_close_tag.suppress()

    @staticmethod
    def strip_html_tags(s: str, l: int, tokens: ParseResults):
        """Parse action to remove HTML tags from web page HTML source

        Example::

            # strip HTML links from normal text
            text = '<td>More info at the <a href="https://github.com/pyparsing/pyparsing/wiki">pyparsing</a> wiki page</td>'
            td, td_end = make_html_tags("TD")
            table_text = td + SkipTo(td_end).set_parse_action(pyparsing_common.strip_html_tags)("body") + td_end
            print(table_text.parse_string(text).body)

        Prints::

            More info at the pyparsing wiki page
        """
        return pyparsing_common._html_stripper.transform_string(tokens[0])

    _commasepitem = (
        Combine(
            OneOrMore(
                ~Literal(",")
                + ~LineEnd()
                + Word(printables, exclude_chars=",")
                + Opt(White(" \t") + ~FollowedBy(LineEnd() | ","))
            )
        )
        .streamline()
        .set_name("commaItem")
    )
    comma_separated_list = DelimitedList(
        Opt(quoted_string.copy() | _commasepitem, default="")
    ).set_name("comma separated list")
    """Predefined expression of 1 or more printable words or quoted strings, separated by commas."""

    upcase_tokens = staticmethod(token_map(lambda t: t.upper()))
    """Parse action to convert tokens to upper case."""

    downcase_tokens = staticmethod(token_map(lambda t: t.lower()))
    """Parse action to convert tokens to lower case."""

    # fmt: off
    url = Regex(
        # https://mathiasbynens.be/demo/url-regex
        # https://gist.github.com/dperini/729294
        r"(?P<url>" +
        # protocol identifier (optional)
        # short syntax // still required
        r"(?:(?:(?P<scheme>https?|ftp):)?\/\/)" +
        # user:pass BasicAuth (optional)
        r"(?:(?P<auth>\S+(?::\S*)?)@)?" +
        r"(?P<host>" +
        # IP address exclusion
        # private & local networks
        r"(?!(?:10|127)(?:\.\d{1,3}){3})" +
        r"(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})" +
        r"(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})" +
        # IP address dotted notation octets
        # excludes loopback network 0.0.0.0
        # excludes reserved space >= 224.0.0.0
        # excludes network & broadcast addresses
        # (first & last IP address of each class)
        r"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])" +
        r"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}" +
        r"(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))" +
        r"|" +
        # host & domain names, may end with dot
        # can be replaced by a shortest alternative
        # (?![-_])(?:[-\w\u00a1-\uffff]{0,63}[^-_]\.)+
        r"(?:" +
        r"(?:" +
        r"[a-z0-9\u00a1-\uffff]" +
        r"[a-z0-9\u00a1-\uffff_-]{0,62}" +
        r")?" +
        r"[a-z0-9\u00a1-\uffff]\." +
        r")+" +
        # TLD identifier name, may end with dot
        r"(?:[a-z\u00a1-\uffff]{2,}\.?)" +
        r")" +
        # port number (optional)
        r"(:(?P<port>\d{2,5}))?" +
        # resource path (optional)
        r"(?P<path>\/[^?# ]*)?" +
        # query string (optional)
        r"(\?(?P<query>[^#]*))?" +
        # fragment (optional)
        r"(#(?P<fragment>\S*))?" +
        r")"
    ).set_name("url")
    """URL (http/https/ftp scheme)"""
    # fmt: on

    # pre-PEP8 compatibility names
    # fmt: off
    convertToInteger = staticmethod(replaced_by_pep8("convertToInteger", convert_to_integer))
    convertToFloat = staticmethod(replaced_by_pep8("convertToFloat", convert_to_float))
    convertToDate = staticmethod(replaced_by_pep8("convertToDate", convert_to_date))
    convertToDatetime = staticmethod(replaced_by_pep8("convertToDatetime", convert_to_datetime))
    stripHTMLTags = staticmethod(replaced_by_pep8("stripHTMLTags", strip_html_tags))
    upcaseTokens = staticmethod(replaced_by_pep8("upcaseTokens", upcase_tokens))
    downcaseTokens = staticmethod(replaced_by_pep8("downcaseTokens", downcase_tokens))
    # fmt: on


_builtin_exprs = [
    v for v in vars(pyparsing_common).values() if isinstance(v, ParserElement)
]

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_xml.py ===
from _pydev_bundle import pydev_log
from _pydevd_bundle import pydevd_extension_utils
from _pydevd_bundle import pydevd_resolver
import sys
from _pydevd_bundle.pydevd_constants import (
    BUILTINS_MODULE_NAME,
    MAXIMUM_VARIABLE_REPRESENTATION_SIZE,
    RETURN_VALUES_DICT,
    LOAD_VALUES_ASYNC,
    DEFAULT_VALUE,
)
from _pydev_bundle.pydev_imports import quote
from _pydevd_bundle.pydevd_extension_api import TypeResolveProvider, StrPresentationProvider
from _pydevd_bundle.pydevd_utils import isinstance_checked, hasattr_checked, DAPGrouper
from _pydevd_bundle.pydevd_resolver import get_var_scope, MoreItems, MoreItemsRange
from typing import Optional

try:
    import types

    frame_type = types.FrameType
except:
    frame_type = None


def make_valid_xml_value(s):
    # Same thing as xml.sax.saxutils.escape but also escaping double quotes.
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class ExceptionOnEvaluate:
    def __init__(self, result, etype, tb):
        self.result = result
        self.etype = etype
        self.tb = tb


_IS_JYTHON = sys.platform.startswith("java")


def _create_default_type_map():
    default_type_map = [
        # None means that it should not be treated as a compound variable
        # isintance does not accept a tuple on some versions of python, so, we must declare it expanded
        (
            type(None),
            None,
        ),
        (int, None),
        (float, None),
        (complex, None),
        (str, None),
        (tuple, pydevd_resolver.tupleResolver),
        (list, pydevd_resolver.tupleResolver),
        (dict, pydevd_resolver.dictResolver),
    ]
    try:
        from collections import OrderedDict

        default_type_map.insert(0, (OrderedDict, pydevd_resolver.orderedDictResolver))
        # we should put it before dict
    except:
        pass

    try:
        default_type_map.append((long, None))  # @UndefinedVariable
    except:
        pass  # not available on all python versions

    default_type_map.append((DAPGrouper, pydevd_resolver.dapGrouperResolver))
    default_type_map.append((MoreItems, pydevd_resolver.forwardInternalResolverToObject))
    default_type_map.append((MoreItemsRange, pydevd_resolver.forwardInternalResolverToObject))

    try:
        default_type_map.append((set, pydevd_resolver.setResolver))
    except:
        pass  # not available on all python versions

    try:
        default_type_map.append((frozenset, pydevd_resolver.setResolver))
    except:
        pass  # not available on all python versions

    try:
        from django.utils.datastructures import MultiValueDict

        default_type_map.insert(0, (MultiValueDict, pydevd_resolver.multiValueDictResolver))
        # we should put it before dict
    except:
        pass  # django may not be installed

    try:
        from django.forms import BaseForm

        default_type_map.insert(0, (BaseForm, pydevd_resolver.djangoFormResolver))
        # we should put it before instance resolver
    except:
        pass  # django may not be installed

    try:
        from collections import deque

        default_type_map.append((deque, pydevd_resolver.dequeResolver))
    except:
        pass

    try:
        from ctypes import Array

        default_type_map.append((Array, pydevd_resolver.tupleResolver))
    except:
        pass

    if frame_type is not None:
        default_type_map.append((frame_type, pydevd_resolver.frameResolver))

    if _IS_JYTHON:
        from org.python import core  # @UnresolvedImport

        default_type_map.append((core.PyNone, None))
        default_type_map.append((core.PyInteger, None))
        default_type_map.append((core.PyLong, None))
        default_type_map.append((core.PyFloat, None))
        default_type_map.append((core.PyComplex, None))
        default_type_map.append((core.PyString, None))
        default_type_map.append((core.PyTuple, pydevd_resolver.tupleResolver))
        default_type_map.append((core.PyList, pydevd_resolver.tupleResolver))
        default_type_map.append((core.PyDictionary, pydevd_resolver.dictResolver))
        default_type_map.append((core.PyStringMap, pydevd_resolver.dictResolver))

        if hasattr(core, "PyJavaInstance"):
            # Jython 2.5b3 removed it.
            default_type_map.append((core.PyJavaInstance, pydevd_resolver.instanceResolver))

    return default_type_map


class TypeResolveHandler(object):
    NO_PROVIDER = []  # Sentinel value (any mutable object to be used as a constant would be valid).

    def __init__(self):
        # Note: don't initialize with the types we already know about so that the extensions can override
        # the default resolvers that are already available if they want.
        self._type_to_resolver_cache = {}
        self._type_to_str_provider_cache = {}
        self._initialized = False

    def _initialize(self):
        self._default_type_map = _create_default_type_map()
        self._resolve_providers = pydevd_extension_utils.extensions_of_type(TypeResolveProvider)
        self._str_providers = pydevd_extension_utils.extensions_of_type(StrPresentationProvider)
        self._initialized = True

    def get_type(self, o):
        try:
            try:
                # Faster than type(o) as we don't need the function call.
                type_object = o.__class__  # could fail here
                type_name = type_object.__name__
                return self._get_type(o, type_object, type_name)  # could fail here
            except:
                # Not all objects have __class__ (i.e.: there are bad bindings around).
                type_object = type(o)
                type_name = type_object.__name__

                try:
                    return self._get_type(o, type_object, type_name)
                except:
                    if isinstance(type_object, type):
                        # If it's still something manageable, use the default resolver, otherwise
                        # fallback to saying that it wasn't possible to get any info on it.
                        return type_object, str(type_name), pydevd_resolver.defaultResolver

                    return "Unable to get Type", "Unable to get Type", None
        except:
            # This happens for org.python.core.InitModule
            return "Unable to get Type", "Unable to get Type", None

    def _get_type(self, o, type_object, type_name):
        # Note: we could have an exception here if the type_object is not hashable...
        resolver = self._type_to_resolver_cache.get(type_object)
        if resolver is not None:
            return type_object, type_name, resolver

        if not self._initialized:
            self._initialize()

        try:
            for resolver in self._resolve_providers:
                if resolver.can_provide(type_object, type_name):
                    # Cache it
                    self._type_to_resolver_cache[type_object] = resolver
                    return type_object, type_name, resolver

            for t in self._default_type_map:
                if isinstance_checked(o, t[0]):
                    # Cache it
                    resolver = t[1]
                    self._type_to_resolver_cache[type_object] = resolver
                    return (type_object, type_name, resolver)
        except:
            pydev_log.exception()

        # No match return default (and cache it).
        resolver = pydevd_resolver.defaultResolver
        self._type_to_resolver_cache[type_object] = resolver
        return type_object, type_name, resolver

    if _IS_JYTHON:
        _base_get_type = _get_type

        def _get_type(self, o, type_object, type_name):
            if type_name == "org.python.core.PyJavaInstance":
                return type_object, type_name, pydevd_resolver.instanceResolver

            if type_name == "org.python.core.PyArray":
                return type_object, type_name, pydevd_resolver.jyArrayResolver

            return self._base_get_type(o, type_object, type_name)

    def _get_str_from_provider(self, provider, o, context: Optional[str] = None):
        if context is not None:
            get_str_in_context = getattr(provider, "get_str_in_context", None)
            if get_str_in_context is not None:
                return get_str_in_context(o, context)

        return provider.get_str(o)

    def str_from_providers(self, o, type_object, type_name, context: Optional[str] = None):
        provider = self._type_to_str_provider_cache.get(type_object)

        if provider is self.NO_PROVIDER:
            return None

        if provider is not None:
            return self._get_str_from_provider(provider, o, context)

        if not self._initialized:
            self._initialize()

        for provider in self._str_providers:
            if provider.can_provide(type_object, type_name):
                self._type_to_str_provider_cache[type_object] = provider
                try:
                    return self._get_str_from_provider(provider, o, context)
                except:
                    pydev_log.exception("Error when getting str with custom provider: %s." % (provider,))

        self._type_to_str_provider_cache[type_object] = self.NO_PROVIDER
        return None


_TYPE_RESOLVE_HANDLER = TypeResolveHandler()

"""
def get_type(o):
    Receives object and returns a triple (type_object, type_string, resolver).

    resolver != None means that variable is a container, and should be displayed as a hierarchy.

    Use the resolver to get its attributes.

    All container objects (i.e.: dict, list, tuple, object, etc) should have a resolver.
"""
get_type = _TYPE_RESOLVE_HANDLER.get_type

_str_from_providers = _TYPE_RESOLVE_HANDLER.str_from_providers


def is_builtin(x):
    return getattr(x, "__module__", None) == BUILTINS_MODULE_NAME


def should_evaluate_full_value(val):
    return not LOAD_VALUES_ASYNC or (is_builtin(type(val)) and not isinstance_checked(val, (list, tuple, dict)))


def return_values_from_dict_to_xml(return_dict):
    res = []
    for name, val in return_dict.items():
        res.append(var_to_xml(val, name, additional_in_xml=' isRetVal="True"'))
    return "".join(res)


def frame_vars_to_xml(frame_f_locals, hidden_ns=None):
    """dumps frame variables to XML
    <var name="var_name" scope="local" type="type" value="value"/>
    """
    xml = []

    keys = sorted(frame_f_locals)

    return_values_xml = []

    for k in keys:
        try:
            v = frame_f_locals[k]
            eval_full_val = should_evaluate_full_value(v)

            if k == "_pydev_stop_at_break":
                continue

            if k == RETURN_VALUES_DICT:
                for name, val in v.items():
                    return_values_xml.append(var_to_xml(val, name, additional_in_xml=' isRetVal="True"'))

            else:
                if hidden_ns is not None and k in hidden_ns:
                    xml.append(var_to_xml(v, str(k), additional_in_xml=' isIPythonHidden="True"', evaluate_full_value=eval_full_val))
                else:
                    xml.append(var_to_xml(v, str(k), evaluate_full_value=eval_full_val))
        except Exception:
            pydev_log.exception("Unexpected error, recovered safely.")

    # Show return values as the first entry.
    return_values_xml.extend(xml)
    return "".join(return_values_xml)


def get_variable_details(val, evaluate_full_value=True, to_string=None, context: Optional[str] = None):
    """
    :param context:
        This is the context in which the variable is being requested. Valid values:
            "watch",
            "repl",
            "hover",
            "clipboard"
    """
    try:
        # This should be faster than isinstance (but we have to protect against not having a '__class__' attribute).
        is_exception_on_eval = val.__class__ == ExceptionOnEvaluate
    except:
        is_exception_on_eval = False

    if is_exception_on_eval:
        v = val.result
    else:
        v = val

    _type, type_name, resolver = get_type(v)
    type_qualifier = getattr(_type, "__module__", "")
    if not evaluate_full_value:
        value = DEFAULT_VALUE
    else:
        try:
            str_from_provider = _str_from_providers(v, _type, type_name, context)
            if str_from_provider is not None:
                value = str_from_provider

            elif to_string is not None:
                value = to_string(v)

            elif hasattr_checked(v, "__class__"):
                if v.__class__ == frame_type:
                    value = pydevd_resolver.frameResolver.get_frame_name(v)

                elif v.__class__ in (list, tuple):
                    if len(v) > 300:
                        value = "%s: %s" % (str(v.__class__), "<Too big to print. Len: %s>" % (len(v),))
                    else:
                        value = "%s: %s" % (str(v.__class__), v)
                else:
                    try:
                        cName = str(v.__class__)
                        if cName.find(".") != -1:
                            cName = cName.split(".")[-1]

                        elif cName.find("'") != -1:  # does not have '.' (could be something like <type 'int'>)
                            cName = cName[cName.index("'") + 1 :]

                        if cName.endswith("'>"):
                            cName = cName[:-2]
                    except:
                        cName = str(v.__class__)

                    value = "%s: %s" % (cName, v)
            else:
                value = str(v)
        except:
            try:
                value = repr(v)
            except:
                value = "Unable to get repr for %s" % v.__class__

    # fix to work with unicode values
    try:
        if value.__class__ == bytes:
            value = value.decode("utf-8", "replace")
    except TypeError:
        pass

    return type_name, type_qualifier, is_exception_on_eval, resolver, value


def var_to_xml(val, name, trim_if_too_big=True, additional_in_xml="", evaluate_full_value=True):
    """single variable or dictionary to xml representation"""

    type_name, type_qualifier, is_exception_on_eval, resolver, value = get_variable_details(val, evaluate_full_value)

    scope = get_var_scope(name, val, "", True)
    try:
        name = quote(name, "/>_= ")  # TODO: Fix PY-5834 without using quote
    except:
        pass

    xml = '<var name="%s" type="%s" ' % (make_valid_xml_value(name), make_valid_xml_value(type_name))

    if type_qualifier:
        xml_qualifier = 'qualifier="%s"' % make_valid_xml_value(type_qualifier)
    else:
        xml_qualifier = ""

    if value:
        # cannot be too big... communication may not handle it.
        if len(value) > MAXIMUM_VARIABLE_REPRESENTATION_SIZE and trim_if_too_big:
            value = value[0:MAXIMUM_VARIABLE_REPRESENTATION_SIZE]
            value += "..."

        xml_value = ' value="%s"' % (make_valid_xml_value(quote(value, "/>_= ")))
    else:
        xml_value = ""

    if is_exception_on_eval:
        xml_container = ' isErrorOnEval="True"'
    else:
        if resolver is not None:
            xml_container = ' isContainer="True"'
        else:
            xml_container = ""

    if scope:
        return "".join((xml, xml_qualifier, xml_value, xml_container, additional_in_xml, ' scope="', scope, '"', " />\n"))
    else:
        return "".join((xml, xml_qualifier, xml_value, xml_container, additional_in_xml, " />\n"))

# === NexusCore/openenv\Lib\site-packages\IPython\testing\tools.py ===
"""Generic testing tools.

Authors
-------
- Fernando Perez <Fernando.Perez@berkeley.edu>
"""


# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import os
from pathlib import Path
import re
import sys
import tempfile
import unittest

from contextlib import contextmanager
from io import StringIO
from subprocess import Popen, PIPE
from unittest.mock import patch

from traitlets.config.loader import Config
from IPython.utils.process import get_output_error_code
from IPython.utils.text import list_strings
from IPython.utils.io import temp_pyfile, Tee
from IPython.utils import py3compat

from . import decorators as dec
from . import skipdoctest


# The docstring for full_path doctests differently on win32 (different path
# separator) so just skip the doctest there.  The example remains informative.
doctest_deco = skipdoctest.skip_doctest if sys.platform == 'win32' else dec.null_deco

@doctest_deco
def full_path(startPath: str, files: list[str]) -> list[str]:
    """Make full paths for all the listed files, based on startPath.

    Only the base part of startPath is kept, since this routine is typically
    used with a script's ``__file__`` variable as startPath. The base of startPath
    is then prepended to all the listed files, forming the output list.

    Parameters
    ----------
    startPath : string
      Initial path to use as the base for the results.  This path is split
      using os.path.split() and only its first component is kept.

    files : list
      One or more files.

    Examples
    --------

    >>> full_path('/foo/bar.py',['a.txt','b.txt'])
    ['/foo/a.txt', '/foo/b.txt']

    >>> full_path('/foo',['a.txt','b.txt'])
    ['/a.txt', '/b.txt']

    """
    assert isinstance(files, list)
    base = os.path.split(startPath)[0]
    return [ os.path.join(base,f) for f in files ]


def parse_test_output(txt):
    """Parse the output of a test run and return errors, failures.

    Parameters
    ----------
    txt : str
      Text output of a test run, assumed to contain a line of one of the
      following forms::

        'FAILED (errors=1)'
        'FAILED (failures=1)'
        'FAILED (errors=1, failures=1)'

    Returns
    -------
    nerr, nfail
      number of errors and failures.
    """

    err_m = re.search(r'^FAILED \(errors=(\d+)\)', txt, re.MULTILINE)
    if err_m:
        nerr = int(err_m.group(1))
        nfail = 0
        return  nerr, nfail

    fail_m = re.search(r'^FAILED \(failures=(\d+)\)', txt, re.MULTILINE)
    if fail_m:
        nerr = 0
        nfail = int(fail_m.group(1))
        return  nerr, nfail

    both_m = re.search(r'^FAILED \(errors=(\d+), failures=(\d+)\)', txt,
                       re.MULTILINE)
    if both_m:
        nerr = int(both_m.group(1))
        nfail = int(both_m.group(2))
        return  nerr, nfail

    # If the input didn't match any of these forms, assume no error/failures
    return 0, 0


# So nose doesn't think this is a test
parse_test_output.__test__ = False


def default_argv():
    """Return a valid default argv for creating testing instances of ipython"""

    return [
        "--quick",  # so no config file is loaded
        # Other defaults to minimize side effects on stdout
        "--colors=nocolor",
        "--no-term-title",
        "--no-banner",
        "--autocall=0",
    ]


def default_config():
    """Return a config object with good defaults for testing."""
    config = Config()
    config.TerminalInteractiveShell.colors = "nocolor"
    config.TerminalTerminalInteractiveShell.term_title = (False,)
    config.TerminalInteractiveShell.autocall = 0
    f = tempfile.NamedTemporaryFile(suffix="test_hist.sqlite", delete=False)
    config.HistoryManager.hist_file = Path(f.name)
    f.close()
    config.HistoryManager.db_cache_size = 10000
    return config


def get_ipython_cmd(as_string=False):
    """
    Return appropriate IPython command line name. By default, this will return
    a list that can be used with subprocess.Popen, for example, but passing
    `as_string=True` allows for returning the IPython command as a string.

    Parameters
    ----------
    as_string: bool
        Flag to allow to return the command as a string.
    """
    ipython_cmd = [sys.executable, "-m", "IPython"]

    if as_string:
        ipython_cmd = " ".join(ipython_cmd)

    return ipython_cmd

def ipexec(fname, options=None, commands=()):
    """Utility to call 'ipython filename'.

    Starts IPython with a minimal and safe configuration to make startup as fast
    as possible.

    Note that this starts IPython in a subprocess!

    Parameters
    ----------
    fname : str, Path
      Name of file to be executed (should have .py or .ipy extension).

    options : optional, list
      Extra command-line flags to be passed to IPython.

    commands : optional, list
      Commands to send in on stdin

    Returns
    -------
    ``(stdout, stderr)`` of ipython subprocess.
    """
    __tracebackhide__ = True

    if options is None:
        options = []

    cmdargs = default_argv() + options

    test_dir = os.path.dirname(__file__)

    ipython_cmd = get_ipython_cmd()
    # Absolute path for filename
    full_fname = os.path.join(test_dir, fname)
    full_cmd = ipython_cmd + cmdargs + ['--', full_fname]
    env = os.environ.copy()
    # FIXME: ignore all warnings in ipexec while we have shims
    # should we keep suppressing warnings here, even after removing shims?
    env['PYTHONWARNINGS'] = 'ignore'
    # env.pop('PYTHONWARNINGS', None)  # Avoid extraneous warnings appearing on stderr
    # Prevent coloring under PyCharm ("\x1b[0m" at the end of the stdout)
    env.pop("PYCHARM_HOSTED", None)
    for k, v in env.items():
        # Debug a bizarre failure we've seen on Windows:
        # TypeError: environment can only contain strings
        if not isinstance(v, str):
            print(k, v)
    p = Popen(full_cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE, env=env)
    out, err = p.communicate(input=py3compat.encode('\n'.join(commands)) or None)
    out, err = py3compat.decode(out), py3compat.decode(err)
    # `import readline` causes 'ESC[?1034h' to be output sometimes,
    # so strip that out before doing comparisons
    if out:
        out = re.sub(r'\x1b\[[^h]+h', '', out)
    return out, err


def ipexec_validate(fname, expected_out, expected_err='',
                    options=None, commands=()):
    """Utility to call 'ipython filename' and validate output/error.

    This function raises an AssertionError if the validation fails.

    Note that this starts IPython in a subprocess!

    Parameters
    ----------
    fname : str, Path
      Name of the file to be executed (should have .py or .ipy extension).

    expected_out : str
      Expected stdout of the process.

    expected_err : optional, str
      Expected stderr of the process.

    options : optional, list
      Extra command-line flags to be passed to IPython.

    Returns
    -------
    None
    """
    __tracebackhide__ = True

    out, err = ipexec(fname, options, commands)
    # print('OUT', out)  # dbg
    # print('ERR', err)  # dbg
    # If there are any errors, we must check those before stdout, as they may be
    # more informative than simply having an empty stdout.
    if err:
        if expected_err:
            assert "\n".join(err.strip().splitlines()) == "\n".join(
                expected_err.strip().splitlines()
            )
        else:
            raise ValueError('Running file %r produced error: %r' %
                             (fname, err))
    # If no errors or output on stderr was expected, match stdout
    assert "\n".join(out.strip().splitlines()) == "\n".join(
        expected_out.strip().splitlines()
    )


class TempFileMixin(unittest.TestCase):
    """Utility class to create temporary Python/IPython files.

    Meant as a mixin class for test cases."""

    def mktmp(self, src, ext='.py'):
        """Make a valid python temp file."""
        fname = temp_pyfile(src, ext)
        if not hasattr(self, 'tmps'):
            self.tmps=[]
        self.tmps.append(fname)
        self.fname = fname

    def tearDown(self):
        # If the tmpfile wasn't made because of skipped tests, like in
        # win32, there's nothing to cleanup.
        if hasattr(self, 'tmps'):
            for fname in self.tmps:
                # If the tmpfile wasn't made because of skipped tests, like in
                # win32, there's nothing to cleanup.
                try:
                    os.unlink(fname)
                except:
                    # On Windows, even though we close the file, we still can't
                    # delete it.  I have no clue why
                    pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.tearDown()


MyStringIO = StringIO

_re_type = type(re.compile(r''))

notprinted_msg = """Did not find {0!r} in printed output (on {1}):
-------
{2!s}
-------
"""

class AssertPrints:
    """Context manager for testing that code prints certain text.

    Examples
    --------
    >>> with AssertPrints("abc", suppress=False):
    ...     print("abcd")
    ...     print("def")
    ...
    abcd
    def
    """
    def __init__(self, s, channel='stdout', suppress=True):
        self.s = s
        if isinstance(self.s, (str, _re_type)):
            self.s = [self.s]
        self.channel = channel
        self.suppress = suppress

    def __enter__(self):
        self.orig_stream = getattr(sys, self.channel)
        self.buffer = MyStringIO()
        self.tee = Tee(self.buffer, channel=self.channel)
        setattr(sys, self.channel, self.buffer if self.suppress else self.tee)

    def __exit__(self, etype, value, traceback):
        __tracebackhide__ = True

        try:
            if value is not None:
                # If an error was raised, don't check anything else
                return False
            self.tee.flush()
            setattr(sys, self.channel, self.orig_stream)
            printed = self.buffer.getvalue()
            for s in self.s:
                if isinstance(s, _re_type):
                    assert s.search(printed), notprinted_msg.format(s.pattern, self.channel, printed)
                else:
                    assert s in printed, notprinted_msg.format(s, self.channel, printed)
            return False
        finally:
            self.tee.close()

printed_msg = """Found {0!r} in printed output (on {1}):
-------
{2!s}
-------
"""

class AssertNotPrints(AssertPrints):
    """Context manager for checking that certain output *isn't* produced.

    Counterpart of AssertPrints"""
    def __exit__(self, etype, value, traceback):
        __tracebackhide__ = True

        try:
            if value is not None:
                # If an error was raised, don't check anything else
                self.tee.close()
                return False
            self.tee.flush()
            setattr(sys, self.channel, self.orig_stream)
            printed = self.buffer.getvalue()
            for s in self.s:
                if isinstance(s, _re_type):
                    assert not s.search(printed),printed_msg.format(
                        s.pattern, self.channel, printed)
                else:
                    assert s not in printed, printed_msg.format(
                        s, self.channel, printed)
            return False
        finally:
            self.tee.close()

@contextmanager
def make_tempfile(name):
    """Create an empty, named, temporary file for the duration of the context."""
    open(name, "w", encoding="utf-8").close()
    try:
        yield
    finally:
        os.unlink(name)

def fake_input(inputs):
    """Temporarily replace the input() function to return the given values

    Use as a context manager:

    with fake_input(['result1', 'result2']):
        ...

    Values are returned in order. If input() is called again after the last value
    was used, EOFError is raised.
    """
    it = iter(inputs)
    def mock_input(prompt=''):
        try:
            return next(it)
        except StopIteration as e:
            raise EOFError('No more inputs given') from e

    return patch('builtins.input', mock_input)

def help_output_test(subcommand=''):
    """test that `ipython [subcommand] -h` works"""
    cmd = get_ipython_cmd() + [subcommand, '-h']
    out, err, rc = get_output_error_code(cmd)
    assert rc == 0, err
    assert "Traceback" not in err
    assert "Options" in out
    assert "--help-all" in out
    return out, err


def help_all_output_test(subcommand=''):
    """test that `ipython [subcommand] --help-all` works"""
    cmd = get_ipython_cmd() + [subcommand, '--help-all']
    out, err, rc = get_output_error_code(cmd)
    assert rc == 0, err
    assert "Traceback" not in err
    assert "Options" in out
    assert "Class" in out
    return out, err


# === NexusCore/openenv\Lib\site-packages\jedi\inference\gradual\base.py ===
from jedi.inference.cache import inference_state_method_cache
from jedi.inference.base_value import ValueSet, NO_VALUES, Value, \
    iterator_to_value_set, LazyValueWrapper, ValueWrapper
from jedi.inference.compiled import builtin_from_name
from jedi.inference.value.klass import ClassFilter
from jedi.inference.value.klass import ClassMixin
from jedi.inference.utils import to_list
from jedi.inference.names import AbstractNameDefinition, ValueName
from jedi.inference.context import ClassContext
from jedi.inference.gradual.generics import TupleGenericManager


class _BoundTypeVarName(AbstractNameDefinition):
    """
    This type var was bound to a certain type, e.g. int.
    """
    def __init__(self, type_var, value_set):
        self._type_var = type_var
        self.parent_context = type_var.parent_context
        self._value_set = value_set

    def infer(self):
        def iter_():
            for value in self._value_set:
                # Replace any with the constraints if they are there.
                from jedi.inference.gradual.typing import AnyClass
                if isinstance(value, AnyClass):
                    yield from self._type_var.constraints
                else:
                    yield value
        return ValueSet(iter_())

    def py__name__(self):
        return self._type_var.py__name__()

    def __repr__(self):
        return '<%s %s -> %s>' % (self.__class__.__name__, self.py__name__(), self._value_set)


class _TypeVarFilter:
    """
    A filter for all given variables in a class.

        A = TypeVar('A')
        B = TypeVar('B')
        class Foo(Mapping[A, B]):
            ...

    In this example we would have two type vars given: A and B
    """
    def __init__(self, generics, type_vars):
        self._generics = generics
        self._type_vars = type_vars

    def get(self, name):
        for i, type_var in enumerate(self._type_vars):
            if type_var.py__name__() == name:
                try:
                    return [_BoundTypeVarName(type_var, self._generics[i])]
                except IndexError:
                    return [type_var.name]
        return []

    def values(self):
        # The values are not relevant. If it's not searched exactly, the type
        # vars are just global and should be looked up as that.
        return []


class _AnnotatedClassContext(ClassContext):
    def get_filters(self, *args, **kwargs):
        filters = super().get_filters(
            *args, **kwargs
        )
        yield from filters

        # The type vars can only be looked up if it's a global search and
        # not a direct lookup on the class.
        yield self._value.get_type_var_filter()


class DefineGenericBaseClass(LazyValueWrapper):
    def __init__(self, generics_manager):
        self._generics_manager = generics_manager

    def _create_instance_with_generics(self, generics_manager):
        raise NotImplementedError

    @inference_state_method_cache()
    def get_generics(self):
        return self._generics_manager.to_tuple()

    def define_generics(self, type_var_dict):
        from jedi.inference.gradual.type_var import TypeVar
        changed = False
        new_generics = []
        for generic_set in self.get_generics():
            values = NO_VALUES
            for generic in generic_set:
                if isinstance(generic, (DefineGenericBaseClass, TypeVar)):
                    result = generic.define_generics(type_var_dict)
                    values |= result
                    if result != ValueSet({generic}):
                        changed = True
                else:
                    values |= ValueSet([generic])
            new_generics.append(values)

        if not changed:
            # There might not be any type vars that change. In that case just
            # return itself, because it does not make sense to potentially lose
            # cached results.
            return ValueSet([self])

        return ValueSet([self._create_instance_with_generics(
            TupleGenericManager(tuple(new_generics))
        )])

    def is_same_class(self, other):
        if not isinstance(other, DefineGenericBaseClass):
            return False

        if self.tree_node != other.tree_node:
            # TODO not sure if this is nice.
            return False
        given_params1 = self.get_generics()
        given_params2 = other.get_generics()

        if len(given_params1) != len(given_params2):
            # If the amount of type vars doesn't match, the class doesn't
            # match.
            return False

        # Now compare generics
        return all(
            any(
                # TODO why is this ordering the correct one?
                cls2.is_same_class(cls1)
                # TODO I'm still not sure gather_annotation_classes is a good
                # idea. They are essentially here to avoid comparing Tuple <=>
                # tuple and instead compare tuple <=> tuple, but at the moment
                # the whole `is_same_class` and `is_sub_class` matching is just
                # not in the best shape.
                for cls1 in class_set1.gather_annotation_classes()
                for cls2 in class_set2.gather_annotation_classes()
            ) for class_set1, class_set2 in zip(given_params1, given_params2)
        )

    def get_signatures(self):
        return []

    def __repr__(self):
        return '<%s: %s%s>' % (
            self.__class__.__name__,
            self._wrapped_value,
            list(self.get_generics()),
        )


class GenericClass(DefineGenericBaseClass, ClassMixin):
    """
    A class that is defined with generics, might be something simple like:

        class Foo(Generic[T]): ...
        my_foo_int_cls = Foo[int]
    """
    def __init__(self, class_value, generics_manager):
        super().__init__(generics_manager)
        self._class_value = class_value

    def _get_wrapped_value(self):
        return self._class_value

    def get_type_hint(self, add_class_info=True):
        n = self.py__name__()
        # Not sure if this is the best way to do this, but all of these types
        # are a bit special in that they have type aliases and other ways to
        # become lower case. It's probably better to make them upper case,
        # because that's what you can use in annotations.
        n = dict(list="List", dict="Dict", set="Set", tuple="Tuple").get(n, n)
        s = n + self._generics_manager.get_type_hint()
        if add_class_info:
            return 'Type[%s]' % s
        return s

    def get_type_var_filter(self):
        return _TypeVarFilter(self.get_generics(), self.list_type_vars())

    def py__call__(self, arguments):
        instance, = super().py__call__(arguments)
        return ValueSet([_GenericInstanceWrapper(instance)])

    def _as_context(self):
        return _AnnotatedClassContext(self)

    @to_list
    def py__bases__(self):
        for base in self._wrapped_value.py__bases__():
            yield _LazyGenericBaseClass(self, base, self._generics_manager)

    def _create_instance_with_generics(self, generics_manager):
        return GenericClass(self._class_value, generics_manager)

    def is_sub_class_of(self, class_value):
        if super().is_sub_class_of(class_value):
            return True
        return self._class_value.is_sub_class_of(class_value)

    def with_generics(self, generics_tuple):
        return self._class_value.with_generics(generics_tuple)

    def infer_type_vars(self, value_set):
        # Circular
        from jedi.inference.gradual.annotation import merge_pairwise_generics, merge_type_var_dicts

        annotation_name = self.py__name__()
        type_var_dict = {}
        if annotation_name == 'Iterable':
            annotation_generics = self.get_generics()
            if annotation_generics:
                return annotation_generics[0].infer_type_vars(
                    value_set.merge_types_of_iterate(),
                )
        else:
            # Note: we need to handle the MRO _in order_, so we need to extract
            # the elements from the set first, then handle them, even if we put
            # them back in a set afterwards.
            for py_class in value_set:
                if py_class.is_instance() and not py_class.is_compiled():
                    py_class = py_class.get_annotated_class_object()
                else:
                    continue

                if py_class.api_type != 'class':
                    # Functions & modules don't have an MRO and we're not
                    # expecting a Callable (those are handled separately within
                    # TypingClassValueWithIndex).
                    continue

                for parent_class in py_class.py__mro__():
                    class_name = parent_class.py__name__()
                    if annotation_name == class_name:
                        merge_type_var_dicts(
                            type_var_dict,
                            merge_pairwise_generics(self, parent_class),
                        )
                        break

        return type_var_dict


class _LazyGenericBaseClass:
    def __init__(self, class_value, lazy_base_class, generics_manager):
        self._class_value = class_value
        self._lazy_base_class = lazy_base_class
        self._generics_manager = generics_manager

    @iterator_to_value_set
    def infer(self):
        for base in self._lazy_base_class.infer():
            if isinstance(base, GenericClass):
                # Here we have to recalculate the given types.
                yield GenericClass.create_cached(
                    base.inference_state,
                    base._wrapped_value,
                    TupleGenericManager(tuple(self._remap_type_vars(base))),
                )
            else:
                if base.is_class_mixin():
                    # This case basically allows classes like `class Foo(List)`
                    # to be used like `Foo[int]`. The generics are not
                    # necessary and can be used later.
                    yield GenericClass.create_cached(
                        base.inference_state,
                        base,
                        self._generics_manager,
                    )
                else:
                    yield base

    def _remap_type_vars(self, base):
        from jedi.inference.gradual.type_var import TypeVar
        filter = self._class_value.get_type_var_filter()
        for type_var_set in base.get_generics():
            new = NO_VALUES
            for type_var in type_var_set:
                if isinstance(type_var, TypeVar):
                    names = filter.get(type_var.py__name__())
                    new |= ValueSet.from_sets(
                        name.infer() for name in names
                    )
                else:
                    # Mostly will be type vars, except if in some cases
                    # a concrete type will already be there. In that
                    # case just add it to the value set.
                    new |= ValueSet([type_var])
            yield new

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self._lazy_base_class)


class _GenericInstanceWrapper(ValueWrapper):
    def py__stop_iteration_returns(self):
        for cls in self._wrapped_value.class_value.py__mro__():
            if cls.py__name__() == 'Generator':
                generics = cls.get_generics()
                try:
                    return generics[2].execute_annotation()
                except IndexError:
                    pass
            elif cls.py__name__() == 'Iterator':
                return ValueSet([builtin_from_name(self.inference_state, 'None')])
        return self._wrapped_value.py__stop_iteration_returns()

    def get_type_hint(self, add_class_info=True):
        return self._wrapped_value.class_value.get_type_hint(add_class_info=False)


class _PseudoTreeNameClass(Value):
    """
    In typeshed, some classes are defined like this:

        Tuple: _SpecialForm = ...

    Now this is not a real class, therefore we have to do some workarounds like
    this class. Essentially this class makes it possible to goto that `Tuple`
    name, without affecting anything else negatively.
    """
    api_type = 'class'

    def __init__(self, parent_context, tree_name):
        super().__init__(
            parent_context.inference_state,
            parent_context
        )
        self._tree_name = tree_name

    @property
    def tree_node(self):
        return self._tree_name

    def get_filters(self, *args, **kwargs):
        # TODO this is obviously wrong. Is it though?
        class EmptyFilter(ClassFilter):
            def __init__(self):
                pass

            def get(self, name, **kwargs):
                return []

            def values(self, **kwargs):
                return []

        yield EmptyFilter()

    def py__class__(self):
        # This might not be 100% correct, but it is good enough. The details of
        # the typing library are not really an issue for Jedi.
        return builtin_from_name(self.inference_state, 'type')

    @property
    def name(self):
        return ValueName(self, self._tree_name)

    def get_qualified_names(self):
        return (self._tree_name.value,)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._tree_name.value)


class BaseTypingValue(LazyValueWrapper):
    def __init__(self, parent_context, tree_name):
        self.inference_state = parent_context.inference_state
        self.parent_context = parent_context
        self._tree_name = tree_name

    @property
    def name(self):
        return ValueName(self, self._tree_name)

    def _get_wrapped_value(self):
        return _PseudoTreeNameClass(self.parent_context, self._tree_name)

    def get_signatures(self):
        return self._wrapped_value.get_signatures()

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._tree_name.value)


class BaseTypingClassWithGenerics(DefineGenericBaseClass):
    def __init__(self, parent_context, tree_name, generics_manager):
        super().__init__(generics_manager)
        self.inference_state = parent_context.inference_state
        self.parent_context = parent_context
        self._tree_name = tree_name

    def _get_wrapped_value(self):
        return _PseudoTreeNameClass(self.parent_context, self._tree_name)

    def __repr__(self):
        return '%s(%s%s)' % (self.__class__.__name__, self._tree_name.value,
                             self._generics_manager)


class BaseTypingInstance(LazyValueWrapper):
    def __init__(self, parent_context, class_value, tree_name, generics_manager):
        self.inference_state = class_value.inference_state
        self.parent_context = parent_context
        self._class_value = class_value
        self._tree_name = tree_name
        self._generics_manager = generics_manager

    def py__class__(self):
        return self._class_value

    def get_annotated_class_object(self):
        return self._class_value

    def get_qualified_names(self):
        return (self.py__name__(),)

    @property
    def name(self):
        return ValueName(self, self._tree_name)

    def _get_wrapped_value(self):
        object_, = builtin_from_name(self.inference_state, 'object').execute_annotation()
        return object_

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self._generics_manager)

# === NexusCore/openenv\Lib\site-packages\tornado\test\tcpclient_test.py ===
#
# Copyright 2014 Facebook
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
from contextlib import closing
import getpass
import socket
import unittest

from tornado.concurrent import Future
from tornado.netutil import bind_sockets, Resolver
from tornado.queues import Queue
from tornado.tcpclient import TCPClient, _Connector
from tornado.tcpserver import TCPServer
from tornado.testing import AsyncTestCase, gen_test
from tornado.test.util import skipIfNoIPv6, refusing_port, skipIfNonUnix
from tornado.gen import TimeoutError

import typing

if typing.TYPE_CHECKING:
    from tornado.iostream import IOStream  # noqa: F401
    from typing import List, Dict, Tuple  # noqa: F401

# Fake address families for testing.  Used in place of AF_INET
# and AF_INET6 because some installations do not have AF_INET6.
AF1, AF2 = 1, 2


class TestTCPServer(TCPServer):
    def __init__(self, family):
        super().__init__()
        self.streams = []  # type: List[IOStream]
        self.queue = Queue()  # type: Queue[IOStream]
        sockets = bind_sockets(0, "localhost", family)
        self.add_sockets(sockets)
        self.port = sockets[0].getsockname()[1]

    def handle_stream(self, stream, address):
        self.streams.append(stream)
        self.queue.put(stream)

    def stop(self):
        super().stop()
        for stream in self.streams:
            stream.close()


class TCPClientTest(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.server = None
        self.client = TCPClient()

    def start_server(self, family):
        self.server = TestTCPServer(family)
        return self.server.port

    def stop_server(self):
        if self.server is not None:
            self.server.stop()
            self.server = None

    def tearDown(self):
        self.client.close()
        self.stop_server()
        super().tearDown()

    def skipIfLocalhostV4(self):
        # The port used here doesn't matter, but some systems require it
        # to be non-zero if we do not also pass AI_PASSIVE.
        addrinfo = self.io_loop.run_sync(lambda: Resolver().resolve("localhost", 80))
        families = {addr[0] for addr in addrinfo}
        if socket.AF_INET6 not in families:
            self.skipTest("localhost does not resolve to ipv6")

    @gen_test
    def do_test_connect(self, family, host, source_ip=None, source_port=None):
        port = self.start_server(family)
        stream = yield self.client.connect(
            host,
            port,
            source_ip=source_ip,
            source_port=source_port,
            af=family,
        )
        assert self.server is not None
        server_stream = yield self.server.queue.get()
        with closing(stream):
            stream.write(b"hello")
            data = yield server_stream.read_bytes(5)
            self.assertEqual(data, b"hello")

    def test_connect_ipv4_ipv4(self):
        self.do_test_connect(socket.AF_INET, "127.0.0.1")

    def test_connect_ipv4_dual(self):
        self.do_test_connect(socket.AF_INET, "localhost")

    @skipIfNoIPv6
    def test_connect_ipv6_ipv6(self):
        self.skipIfLocalhostV4()
        self.do_test_connect(socket.AF_INET6, "::1")

    @skipIfNoIPv6
    def test_connect_ipv6_dual(self):
        self.skipIfLocalhostV4()
        self.do_test_connect(socket.AF_INET6, "localhost")

    def test_connect_unspec_ipv4(self):
        self.do_test_connect(socket.AF_UNSPEC, "127.0.0.1")

    @skipIfNoIPv6
    def test_connect_unspec_ipv6(self):
        self.skipIfLocalhostV4()
        self.do_test_connect(socket.AF_UNSPEC, "::1")

    def test_connect_unspec_dual(self):
        self.do_test_connect(socket.AF_UNSPEC, "localhost")

    @gen_test
    def test_refused_ipv4(self):
        cleanup_func, port = refusing_port()
        self.addCleanup(cleanup_func)
        with self.assertRaises(IOError):
            yield self.client.connect("127.0.0.1", port)

    def test_source_ip_fail(self):
        """Fail when trying to use the source IP Address '8.8.8.8'."""
        self.assertRaises(
            socket.error,
            self.do_test_connect,
            socket.AF_INET,
            "127.0.0.1",
            source_ip="8.8.8.8",
        )

    def test_source_ip_success(self):
        """Success when trying to use the source IP Address '127.0.0.1'."""
        self.do_test_connect(socket.AF_INET, "127.0.0.1", source_ip="127.0.0.1")

    @skipIfNonUnix
    def test_source_port_fail(self):
        """Fail when trying to use source port 1."""
        if getpass.getuser() == "root":
            # Root can use any port so we can't easily force this to fail.
            # This is mainly relevant for docker.
            self.skipTest("running as root")
        self.assertRaises(
            socket.error,
            self.do_test_connect,
            socket.AF_INET,
            "127.0.0.1",
            source_port=1,
        )

    @gen_test
    def test_connect_timeout(self):
        timeout = 0.05

        class TimeoutResolver(Resolver):
            def resolve(self, *args, **kwargs):
                return Future()  # never completes

        with self.assertRaises(TimeoutError):
            yield TCPClient(resolver=TimeoutResolver()).connect(
                "1.2.3.4", 12345, timeout=timeout
            )


class TestConnectorSplit(unittest.TestCase):
    def test_one_family(self):
        # These addresses aren't in the right format, but split doesn't care.
        primary, secondary = _Connector.split([(AF1, "a"), (AF1, "b")])
        self.assertEqual(primary, [(AF1, "a"), (AF1, "b")])
        self.assertEqual(secondary, [])

    def test_mixed(self):
        primary, secondary = _Connector.split(
            [(AF1, "a"), (AF2, "b"), (AF1, "c"), (AF2, "d")]
        )
        self.assertEqual(primary, [(AF1, "a"), (AF1, "c")])
        self.assertEqual(secondary, [(AF2, "b"), (AF2, "d")])


class ConnectorTest(AsyncTestCase):
    class FakeStream:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    def setUp(self):
        super().setUp()
        self.connect_futures = (
            {}
        )  # type: Dict[Tuple[int, typing.Any], Future[ConnectorTest.FakeStream]]
        self.streams = {}  # type: Dict[typing.Any, ConnectorTest.FakeStream]
        self.addrinfo = [(AF1, "a"), (AF1, "b"), (AF2, "c"), (AF2, "d")]

    def tearDown(self):
        # Unless explicitly checked (and popped) in the test, we shouldn't
        # be closing any streams
        for stream in self.streams.values():
            self.assertFalse(stream.closed)
        super().tearDown()

    def create_stream(self, af, addr):
        stream = ConnectorTest.FakeStream()
        self.streams[addr] = stream
        future = Future()  # type: Future[ConnectorTest.FakeStream]
        self.connect_futures[(af, addr)] = future
        return stream, future

    def assert_pending(self, *keys):
        self.assertEqual(sorted(self.connect_futures.keys()), sorted(keys))

    def resolve_connect(self, af, addr, success):
        future = self.connect_futures.pop((af, addr))
        if success:
            future.set_result(self.streams[addr])
        else:
            self.streams.pop(addr)
            future.set_exception(IOError())
        # Run the loop to allow callbacks to be run.
        self.io_loop.add_callback(self.stop)
        self.wait()

    def assert_connector_streams_closed(self, conn):
        for stream in conn.streams:
            self.assertTrue(stream.closed)

    def start_connect(self, addrinfo):
        conn = _Connector(addrinfo, self.create_stream)
        # Give it a huge timeout; we'll trigger timeouts manually.
        future = conn.start(3600, connect_timeout=self.io_loop.time() + 3600)
        return conn, future

    def test_immediate_success(self):
        conn, future = self.start_connect(self.addrinfo)
        self.assertEqual(list(self.connect_futures.keys()), [(AF1, "a")])
        self.resolve_connect(AF1, "a", True)
        self.assertEqual(future.result(), (AF1, "a", self.streams["a"]))

    def test_immediate_failure(self):
        # Fail with just one address.
        conn, future = self.start_connect([(AF1, "a")])
        self.assert_pending((AF1, "a"))
        self.resolve_connect(AF1, "a", False)
        self.assertRaises(IOError, future.result)

    def test_one_family_second_try(self):
        conn, future = self.start_connect([(AF1, "a"), (AF1, "b")])
        self.assert_pending((AF1, "a"))
        self.resolve_connect(AF1, "a", False)
        self.assert_pending((AF1, "b"))
        self.resolve_connect(AF1, "b", True)
        self.assertEqual(future.result(), (AF1, "b", self.streams["b"]))

    def test_one_family_second_try_failure(self):
        conn, future = self.start_connect([(AF1, "a"), (AF1, "b")])
        self.assert_pending((AF1, "a"))
        self.resolve_connect(AF1, "a", False)
        self.assert_pending((AF1, "b"))
        self.resolve_connect(AF1, "b", False)
        self.assertRaises(IOError, future.result)

    def test_one_family_second_try_timeout(self):
        conn, future = self.start_connect([(AF1, "a"), (AF1, "b")])
        self.assert_pending((AF1, "a"))
        # trigger the timeout while the first lookup is pending;
        # nothing happens.
        conn.on_timeout()
        self.assert_pending((AF1, "a"))
        self.resolve_connect(AF1, "a", False)
        self.assert_pending((AF1, "b"))
        self.resolve_connect(AF1, "b", True)
        self.assertEqual(future.result(), (AF1, "b", self.streams["b"]))

    def test_two_families_immediate_failure(self):
        conn, future = self.start_connect(self.addrinfo)
        self.assert_pending((AF1, "a"))
        self.resolve_connect(AF1, "a", False)
        self.assert_pending((AF1, "b"), (AF2, "c"))
        self.resolve_connect(AF1, "b", False)
        self.resolve_connect(AF2, "c", True)
        self.assertEqual(future.result(), (AF2, "c", self.streams["c"]))

    def test_two_families_timeout(self):
        conn, future = self.start_connect(self.addrinfo)
        self.assert_pending((AF1, "a"))
        conn.on_timeout()
        self.assert_pending((AF1, "a"), (AF2, "c"))
        self.resolve_connect(AF2, "c", True)
        self.assertEqual(future.result(), (AF2, "c", self.streams["c"]))
        # resolving 'a' after the connection has completed doesn't start 'b'
        self.resolve_connect(AF1, "a", False)
        self.assert_pending()

    def test_success_after_timeout(self):
        conn, future = self.start_connect(self.addrinfo)
        self.assert_pending((AF1, "a"))
        conn.on_timeout()
        self.assert_pending((AF1, "a"), (AF2, "c"))
        self.resolve_connect(AF1, "a", True)
        self.assertEqual(future.result(), (AF1, "a", self.streams["a"]))
        # resolving 'c' after completion closes the connection.
        self.resolve_connect(AF2, "c", True)
        self.assertTrue(self.streams.pop("c").closed)

    def test_all_fail(self):
        conn, future = self.start_connect(self.addrinfo)
        self.assert_pending((AF1, "a"))
        conn.on_timeout()
        self.assert_pending((AF1, "a"), (AF2, "c"))
        self.resolve_connect(AF2, "c", False)
        self.assert_pending((AF1, "a"), (AF2, "d"))
        self.resolve_connect(AF2, "d", False)
        # one queue is now empty
        self.assert_pending((AF1, "a"))
        self.resolve_connect(AF1, "a", False)
        self.assert_pending((AF1, "b"))
        self.assertFalse(future.done())
        self.resolve_connect(AF1, "b", False)
        self.assertRaises(IOError, future.result)

    def test_one_family_timeout_after_connect_timeout(self):
        conn, future = self.start_connect([(AF1, "a"), (AF1, "b")])
        self.assert_pending((AF1, "a"))
        conn.on_connect_timeout()
        # the connector will close all streams on connect timeout, we
        # should explicitly pop the connect_future.
        self.connect_futures.pop((AF1, "a"))
        self.assertTrue(self.streams.pop("a").closed)
        conn.on_timeout()
        # if the future is set with TimeoutError, we will not iterate next
        # possible address.
        self.assert_pending()
        self.assertEqual(len(conn.streams), 1)
        self.assert_connector_streams_closed(conn)
        self.assertRaises(TimeoutError, future.result)

    def test_one_family_success_before_connect_timeout(self):
        conn, future = self.start_connect([(AF1, "a"), (AF1, "b")])
        self.assert_pending((AF1, "a"))
        self.resolve_connect(AF1, "a", True)
        conn.on_connect_timeout()
        self.assert_pending()
        self.assertFalse(self.streams["a"].closed)
        # success stream will be pop
        self.assertEqual(len(conn.streams), 0)
        # streams in connector should be closed after connect timeout
        self.assert_connector_streams_closed(conn)
        self.assertEqual(future.result(), (AF1, "a", self.streams["a"]))

    def test_one_family_second_try_after_connect_timeout(self):
        conn, future = self.start_connect([(AF1, "a"), (AF1, "b")])
        self.assert_pending((AF1, "a"))
        self.resolve_connect(AF1, "a", False)
        self.assert_pending((AF1, "b"))
        conn.on_connect_timeout()
        self.connect_futures.pop((AF1, "b"))
        self.assertTrue(self.streams.pop("b").closed)
        self.assert_pending()
        self.assertEqual(len(conn.streams), 2)
        self.assert_connector_streams_closed(conn)
        self.assertRaises(TimeoutError, future.result)

    def test_one_family_second_try_failure_before_connect_timeout(self):
        conn, future = self.start_connect([(AF1, "a"), (AF1, "b")])
        self.assert_pending((AF1, "a"))
        self.resolve_connect(AF1, "a", False)
        self.assert_pending((AF1, "b"))
        self.resolve_connect(AF1, "b", False)
        conn.on_connect_timeout()
        self.assert_pending()
        self.assertEqual(len(conn.streams), 2)
        self.assert_connector_streams_closed(conn)
        self.assertRaises(IOError, future.result)

    def test_two_family_timeout_before_connect_timeout(self):
        conn, future = self.start_connect(self.addrinfo)
        self.assert_pending((AF1, "a"))
        conn.on_timeout()
        self.assert_pending((AF1, "a"), (AF2, "c"))
        conn.on_connect_timeout()
        self.connect_futures.pop((AF1, "a"))
        self.assertTrue(self.streams.pop("a").closed)
        self.connect_futures.pop((AF2, "c"))
        self.assertTrue(self.streams.pop("c").closed)
        self.assert_pending()
        self.assertEqual(len(conn.streams), 2)
        self.assert_connector_streams_closed(conn)
        self.assertRaises(TimeoutError, future.result)

    def test_two_family_success_after_timeout(self):
        conn, future = self.start_connect(self.addrinfo)
        self.assert_pending((AF1, "a"))
        conn.on_timeout()
        self.assert_pending((AF1, "a"), (AF2, "c"))
        self.resolve_connect(AF1, "a", True)
        # if one of streams succeed, connector will close all other streams
        self.connect_futures.pop((AF2, "c"))
        self.assertTrue(self.streams.pop("c").closed)
        self.assert_pending()
        self.assertEqual(len(conn.streams), 1)
        self.assert_connector_streams_closed(conn)
        self.assertEqual(future.result(), (AF1, "a", self.streams["a"]))

    def test_two_family_timeout_after_connect_timeout(self):
        conn, future = self.start_connect(self.addrinfo)
        self.assert_pending((AF1, "a"))
        conn.on_connect_timeout()
        self.connect_futures.pop((AF1, "a"))
        self.assertTrue(self.streams.pop("a").closed)
        self.assert_pending()
        conn.on_timeout()
        # if the future is set with TimeoutError, connector will not
        # trigger secondary address.
        self.assert_pending()
        self.assertEqual(len(conn.streams), 1)
        self.assert_connector_streams_closed(conn)
        self.assertRaises(TimeoutError, future.result)

# === NexusCore/openenv\Lib\site-packages\win32com\demos\excelRTDServer.py ===
"""Excel IRTDServer implementation.

This module is a functional example of how to implement the IRTDServer interface
in python, using the pywin32 extensions. Further details, about this interface
and it can be found at:
     https://learn.microsoft.com/en-us/previous-versions/office/developer/office-xp/aa140060(v=office.10)
"""

# Copyright (c) 2003-2004 by Chris Nilsson <chris@slort.org>
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Christopher Nilsson (the author) not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.

import datetime  # For the example classes...
import threading

import pythoncom
import win32com.client
from win32com import universal
from win32com.client import gencache
from win32com.server.exception import COMException

# Typelib info for version 10 - aka Excel XP.
# This is the minimum version of excel that we can work with as this is when
# Microsoft introduced these interfaces.
EXCEL_TLB_GUID = "{00020813-0000-0000-C000-000000000046}"
EXCEL_TLB_LCID = 0
EXCEL_TLB_MAJOR = 1
EXCEL_TLB_MINOR = 4

# Import the excel typelib to make sure we've got early-binding going on.
# The "ByRef" parameters we use later won't work without this.
gencache.EnsureModule(EXCEL_TLB_GUID, EXCEL_TLB_LCID, EXCEL_TLB_MAJOR, EXCEL_TLB_MINOR)

# Tell pywin to import these extra interfaces.
# --
# QUESTION: Why? The interfaces seem to descend from IDispatch, so
# I'd have thought, for example, calling callback.UpdateNotify() (on the
# IRTDUpdateEvent callback excel gives us) would work without molestation.
# But the callback needs to be cast to a "real" IRTDUpdateEvent type. Hmm...
# This is where my small knowledge of the pywin framework / COM gets hazy.
# --
# Again, we feed in the Excel typelib as the source of these interfaces.
universal.RegisterInterfaces(
    EXCEL_TLB_GUID,
    EXCEL_TLB_LCID,
    EXCEL_TLB_MAJOR,
    EXCEL_TLB_MINOR,
    ["IRtdServer", "IRTDUpdateEvent"],
)


class ExcelRTDServer:
    """Base RTDServer class.

    Provides most of the features needed to implement the IRtdServer interface.
    Manages topic adding, removal, and packing up the values for excel.

    Shouldn't be instanciated directly.

    Instead, descendant classes should override the CreateTopic() method.
    Topic objects only need to provide a GetValue() function to play nice here.
    The values given need to be atomic (eg. string, int, float... etc).

    Also note: nothing has been done within this class to ensure that we get
    time to check our topics for updates. I've left that up to the subclass
    since the ways, and needs, of refreshing your topics will vary greatly. For
    example, the sample implementation uses a timer thread to wake itself up.
    Whichever way you choose to do it, your class needs to be able to wake up
    occaisionally, since excel will never call your class without being asked to
    first.

    Excel will communicate with our object in this order:
      1. Excel instanciates our object and calls ServerStart, providing us with
         an IRTDUpdateEvent callback object.
      2. Excel calls ConnectData when it wants to subscribe to a new "topic".
      3. When we have new data to provide, we call the UpdateNotify method of the
         callback object we were given.
      4. Excel calls our RefreshData method, and receives a 2d SafeArray (row-major)
         containing the Topic ids in the 1st dim, and the topic values in the
         2nd dim.
      5. When not needed anymore, Excel will call our DisconnectData to
         unsubscribe from a topic.
      6. When there are no more topics left, Excel will call our ServerTerminate
         method to kill us.

    Throughout, at undetermined periods, Excel will call our Heartbeat
    method to see if we're still alive. It must return a non-zero value, or
    we'll be killed.

    NOTE: By default, excel will at most call RefreshData once every 2 seconds.
          This is a setting that needs to be changed excel-side. To change this,
          you can set the throttle interval like this in the excel VBA object model:
            Application.RTD.ThrottleInterval = 1000 ' milliseconds
    """

    _com_interfaces_ = ["IRtdServer"]
    _public_methods_ = [
        "ConnectData",
        "DisconnectData",
        "Heartbeat",
        "RefreshData",
        "ServerStart",
        "ServerTerminate",
    ]
    _reg_clsctx_ = pythoncom.CLSCTX_INPROC_SERVER
    # _reg_clsid_ = "# subclass must provide this class attribute"
    # _reg_desc_ = "# subclass should provide this description"
    # _reg_progid_ = "# subclass must provide this class attribute"

    ALIVE = 1
    NOT_ALIVE = 0

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.IsAlive = self.ALIVE
        self.__callback = None
        self.topics = {}

    def SignalExcel(self):
        """Use the callback we were given to tell excel new data is available."""
        if self.__callback is None:
            raise COMException(desc="Callback excel provided is Null")
        self.__callback.UpdateNotify()

    def ConnectData(self, TopicID, Strings, GetNewValues):
        """Creates a new topic out of the Strings excel gives us."""
        try:
            self.topics[TopicID] = self.CreateTopic(Strings)
        except Exception as why:
            raise COMException(desc=str(why))
        GetNewValues = True
        result = self.topics[TopicID]
        if result is None:
            result = "# %s: Waiting for update" % self.__class__.__name__
        else:
            result = result.GetValue()

        # fire out internal event...
        self.OnConnectData(TopicID)

        # GetNewValues as per interface is ByRef, so we need to pass it back too.
        return result, GetNewValues

    def DisconnectData(self, TopicID):
        """Deletes the given topic."""
        self.OnDisconnectData(TopicID)

        if TopicID in self.topics:
            self.topics[TopicID] = None
            del self.topics[TopicID]

    def Heartbeat(self):
        """Called by excel to see if we're still here."""
        return self.IsAlive

    def RefreshData(self, TopicCount):
        """Packs up the topic values. Called by excel when it's ready for an update.

        Needs to:
          * Return the current number of topics, via the "ByRef" TopicCount
          * Return a 2d SafeArray of the topic data.
            - 1st dim: topic numbers
            - 2nd dim: topic values

        We could do some caching, instead of repacking everytime...
        But this works for demonstration purposes."""
        TopicCount = len(self.topics)
        self.OnRefreshData()

        # Grow the lists, so we don't need a heap of calls to append()
        results = [[None] * TopicCount, [None] * TopicCount]

        # Excel expects a 2-dimensional array. The first dim contains the
        # topic numbers, and the second contains the values for the topics.
        # In true VBA style (yuck), we need to pack the array in row-major format,
        # which looks like:
        #   ( (topic_num1, topic_num2, ..., topic_numN), \
        #     (topic_val1, topic_val2, ..., topic_valN) )
        for idx, topicdata in enumerate(self.topics.items()):
            topicNum, topic = topicdata
            results[0][idx] = topicNum
            results[1][idx] = topic.GetValue()

        # TopicCount is meant to be passed to us ByRef, so return it as well, as per
        # the way pywin32 handles ByRef arguments.
        return tuple(results), TopicCount

    def ServerStart(self, CallbackObject):
        """Excel has just created us... We take its callback for later, and set up shop."""
        self.IsAlive = self.ALIVE

        if CallbackObject is None:
            raise COMException(desc="Excel did not provide a callback")

        # Need to "cast" the raw PyIDispatch object to the IRTDUpdateEvent interface
        IRTDUpdateEventKlass = win32com.client.CLSIDToClass.GetClass(
            "{A43788C1-D91B-11D3-8F39-00C04F3651B8}"
        )
        self.__callback = IRTDUpdateEventKlass(CallbackObject)

        self.OnServerStart()

        return self.IsAlive

    def ServerTerminate(self):
        """Called when excel no longer wants us."""
        self.IsAlive = self.NOT_ALIVE  # On next heartbeat, excel will free us
        self.OnServerTerminate()

    def CreateTopic(self, TopicStrings=None):
        """Topic factory method. Subclass must override.

        Topic objects need to provide:
          * GetValue() method which returns an atomic value.

        Will raise NotImplemented if not overridden.
        """
        raise NotImplemented("Subclass must implement")

    # Overridable class events...
    def OnConnectData(self, TopicID):
        """Called when a new topic has been created, at excel's request."""
        pass

    def OnDisconnectData(self, TopicID):
        """Called when a topic is about to be deleted, at excel's request."""
        pass

    def OnRefreshData(self):
        """Called when excel has requested all current topic data."""
        pass

    def OnServerStart(self):
        """Called when excel has instanciated us."""
        pass

    def OnServerTerminate(self):
        """Called when excel is about to destroy us."""
        pass


class RTDTopic:
    """Base RTD Topic.
    Only method required by our RTDServer implementation is GetValue().
    The others are more for convenience."""

    def __init__(self, TopicStrings):
        super().__init__()
        self.TopicStrings = TopicStrings
        self.__currentValue = None
        self.__dirty = False

    def Update(self, sender):
        """Called by the RTD Server.
        Gives us a chance to check if our topic data needs to be
        changed (eg. check a file, quiz a database, etc)."""
        raise NotImplemented("subclass must implement")

    def Reset(self):
        """Call when this topic isn't considered "dirty" anymore."""
        self.__dirty = False

    def GetValue(self):
        return self.__currentValue

    def SetValue(self, value):
        self.__dirty = True
        self.__currentValue = value

    def HasChanged(self):
        return self.__dirty


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

######################################
# Example classes
######################################


class TimeServer(ExcelRTDServer):
    """Example Time RTD server.

    Sends time updates back to excel.

    example of use, in an excel sheet:
      =RTD("Python.RTD.TimeServer","","seconds","5")

    This will cause a timestamp string to fill the cell, and update its value
    every 5 seconds (or as close as possible depending on how busy excel is).

    The empty string parameter denotes the com server is running on the local
    machine. Otherwise, put in the hostname to look on. For more info
    on this, lookup the Excel help for its "RTD" worksheet function.

    Obviously, you'd want to wrap this kind of thing in a friendlier VBA
    function.

    Also, remember that the RTD function accepts a maximum of 28 arguments!
    If you want to pass more, you may need to concatenate arguments into one
    string, and have your topic parse them appropriately.
    """

    # win32com.server setup attributes...
    # Never copy the _reg_clsid_ value in your own classes!
    _reg_clsid_ = "{EA7F2CF1-11A2-45E4-B2D5-68E240DB8CB1}"
    _reg_progid_ = "Python.RTD.TimeServer"
    _reg_desc_ = "Python class implementing Excel IRTDServer -- feeds time"

    # other class attributes...
    INTERVAL = 0.5  # secs. Threaded timer will wake us up at this interval.

    def __init__(self):
        super().__init__()

        # Simply timer thread to ensure we get to update our topics, and
        # tell excel about any changes. This is a pretty basic and dirty way to
        # do this. Ideally, there should be some sort of waitable (eg. either win32
        # event, socket data event...) and be kicked off by that event triggering.
        # As soon as we set up shop here, we _must_ return control back to excel.
        # (ie. we can't block and do our own thing...)
        self.ticker = threading.Timer(self.INTERVAL, self.Update)

    def OnServerStart(self):
        self.ticker.start()

    def OnServerTerminate(self):
        if not self.ticker.finished.isSet():
            self.ticker.cancel()  # Cancel our wake-up thread. Excel has killed us.

    def Update(self):
        # Get our wake-up thread ready...
        self.ticker = threading.Timer(self.INTERVAL, self.Update)
        try:
            # Check if any of our topics have new info to pass on
            if len(self.topics):
                refresh = False
                for topic in self.topics.values():
                    topic.Update(self)
                    if topic.HasChanged():
                        refresh = True
                    topic.Reset()

                if refresh:
                    self.SignalExcel()
        finally:
            self.ticker.start()  # Make sure we get to run again

    def CreateTopic(self, TopicStrings=None):
        """Topic factory. Builds a TimeTopic object out of the given TopicStrings."""
        return TimeTopic(TopicStrings)


class TimeTopic(RTDTopic):
    """Example topic for example RTD server.

    Will accept some simple commands to alter how long to delay value updates.

    Commands:
      * seconds, delay_in_seconds
      * minutes, delay_in_minutes
      * hours, delay_in_hours
    """

    def __init__(self, TopicStrings):
        super().__init__(TopicStrings)
        try:
            self.cmd, self.delay = self.TopicStrings
        except Exception as E:
            # We could simply return a "# ERROR" type string as the
            # topic value, but explosions like this should be able to get handled by
            # the VBA-side "On Error" stuff.
            raise ValueError("Invalid topic strings: %s" % str(TopicStrings))

        # self.cmd = str(self.cmd)
        self.delay = float(self.delay)

        # setup our initial value
        self.checkpoint = self.timestamp()
        self.SetValue(str(self.checkpoint))

    def timestamp(self):
        return datetime.datetime.now()

    def Update(self, sender):
        now = self.timestamp()
        delta = now - self.checkpoint
        refresh = False
        if self.cmd == "seconds":
            if delta.seconds >= self.delay:
                refresh = True
        elif self.cmd == "minutes":
            if delta.minutes >= self.delay:
                refresh = True
        elif self.cmd == "hours":
            if delta.hours >= self.delay:
                refresh = True
        else:
            self.SetValue("#Unknown command: " + self.cmd)

        if refresh:
            self.SetValue(str(now))
            self.checkpoint = now


if __name__ == "__main__":
    import win32com.server.register

    # Register/Unregister TimeServer example
    # eg. at the command line: excelrtd.py --register
    # Then type in an excel cell something like:
    # =RTD("Python.RTD.TimeServer","","seconds","5")
    win32com.server.register.UseCommandLine(TimeServer)

# === NexusCore/exported_projects\project_export_cdru4snl\single_file_project\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()

# === NexusCore/exported_projects\project_export_njaqxffz\single_file_project\buyma_catalog_manager.py ===
import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_reload.py ===
"""
Based on the python xreload.

Changes
======================

1. we don't recreate the old namespace from new classes. Rather, we keep the existing namespace,
load a new version of it and update only some of the things we can inplace. That way, we don't break
things such as singletons or end up with a second representation of the same class in memory.

2. If we find it to be a __metaclass__, we try to update it as a regular class.

3. We don't remove old attributes (and leave them lying around even if they're no longer used).

4. Reload hooks were changed

These changes make it more stable, especially in the common case (where in a debug session only the
contents of a function are changed), besides providing flexibility for users that want to extend
on it.



Hooks
======================

Classes/modules can be specially crafted to work with the reload (so that it can, for instance,
update some constant which was changed).

1. To participate in the change of some attribute:

    In a module:

    __xreload_old_new__(namespace, name, old, new)

    in a class:

    @classmethod
    __xreload_old_new__(cls, name, old, new)

    A class or module may include a method called '__xreload_old_new__' which is called when we're
    unable to reload a given attribute.



2. To do something after the whole reload is finished:

    In a module:

    __xreload_after_reload_update__(namespace):

    In a class:

    @classmethod
    __xreload_after_reload_update__(cls):


    A class or module may include a method called '__xreload_after_reload_update__' which is called
    after the reload finishes.


Important: when providing a hook, always use the namespace or cls provided and not anything in the global
namespace, as the global namespace are only temporarily created during the reload and may not reflect the
actual application state (while the cls and namespace passed are).


Current limitations
======================


- Attributes/constants are added, but not changed (so singletons and the application state is not
  broken -- use provided hooks to workaround it).

- Code using metaclasses may not always work.

- Functions and methods using decorators (other than classmethod and staticmethod) are not handled
  correctly.

- Renamings are not handled correctly.

- Dependent modules are not reloaded.

- New __slots__ can't be added to existing classes.


Info
======================

Original: http://svn.python.org/projects/sandbox/trunk/xreload/xreload.py
Note: it seems https://github.com/plone/plone.reload/blob/master/plone/reload/xreload.py enhances it (to check later)

Interesting alternative: https://code.google.com/p/reimport/

Alternative to reload().

This works by executing the module in a scratch namespace, and then patching classes, methods and
functions in place.  This avoids the need to patch instances.  New objects are copied into the
target namespace.

"""

from _pydev_bundle.pydev_imports import execfile
from _pydevd_bundle import pydevd_dont_trace
import types
from _pydev_bundle import pydev_log
from _pydevd_bundle.pydevd_constants import get_global_debugger

NO_DEBUG = 0
LEVEL1 = 1
LEVEL2 = 2

DEBUG = NO_DEBUG


def write_err(*args):
    py_db = get_global_debugger()
    if py_db is not None:
        new_lst = []
        for a in args:
            new_lst.append(str(a))

        msg = " ".join(new_lst)
        s = "code reload: %s\n" % (msg,)
        cmd = py_db.cmd_factory.make_io_message(s, 2)
        if py_db.writer is not None:
            py_db.writer.add_command(cmd)


def notify_info0(*args):
    write_err(*args)


def notify_info(*args):
    if DEBUG >= LEVEL1:
        write_err(*args)


def notify_info2(*args):
    if DEBUG >= LEVEL2:
        write_err(*args)


def notify_error(*args):
    write_err(*args)


# =======================================================================================================================
# code_objects_equal
# =======================================================================================================================
def code_objects_equal(code0, code1):
    for d in dir(code0):
        if d.startswith("_") or "line" in d or d in ("replace", "co_positions", "co_qualname"):
            continue
        if getattr(code0, d) != getattr(code1, d):
            return False
    return True


# =======================================================================================================================
# xreload
# =======================================================================================================================
def xreload(mod):
    """Reload a module in place, updating classes, methods and functions.

    mod: a module object

    Returns a boolean indicating whether a change was done.
    """
    r = Reload(mod)
    r.apply()
    found_change = r.found_change
    r = None
    pydevd_dont_trace.clear_trace_filter_cache()
    return found_change


# This isn't actually used... Initially I planned to reload variables which are immutable on the
# namespace, but this can destroy places where we're saving state, which may not be what we want,
# so, we're being conservative and giving the user hooks if he wants to do a reload.
#
# immutable_types = [int, str, float, tuple] #That should be common to all Python versions
#
# for name in 'long basestr unicode frozenset'.split():
#     try:
#         immutable_types.append(__builtins__[name])
#     except:
#         pass #Just ignore: not all python versions are created equal.
# immutable_types = tuple(immutable_types)


# =======================================================================================================================
# Reload
# =======================================================================================================================
class Reload:
    def __init__(self, mod, mod_name=None, mod_filename=None):
        self.mod = mod
        if mod_name:
            self.mod_name = mod_name
        else:
            self.mod_name = mod.__name__ if mod is not None else None

        if mod_filename:
            self.mod_filename = mod_filename
        else:
            self.mod_filename = mod.__file__ if mod is not None else None

        self.found_change = False

    def apply(self):
        mod = self.mod
        self._on_finish_callbacks = []
        try:
            # Get the module namespace (dict) early; this is part of the type check
            modns = mod.__dict__

            # Execute the code.  We copy the module dict to a temporary; then
            # clear the module dict; then execute the new code in the module
            # dict; then swap things back and around.  This trick (due to
            # Glyph Lefkowitz) ensures that the (readonly) __globals__
            # attribute of methods and functions is set to the correct dict
            # object.
            new_namespace = modns.copy()
            new_namespace.clear()
            if self.mod_filename:
                new_namespace["__file__"] = self.mod_filename
                try:
                    new_namespace["__builtins__"] = __builtins__
                except NameError:
                    raise  # Ok if not there.

            if self.mod_name:
                new_namespace["__name__"] = self.mod_name
                if new_namespace["__name__"] == "__main__":
                    # We do this because usually the __main__ starts-up the program, guarded by
                    # the if __name__ == '__main__', but we don't want to start the program again
                    # on a reload.
                    new_namespace["__name__"] = "__main_reloaded__"

            execfile(self.mod_filename, new_namespace, new_namespace)
            # Now we get to the hard part
            oldnames = set(modns)
            newnames = set(new_namespace)

            # Create new tokens (note: not deleting existing)
            for name in newnames - oldnames:
                notify_info0("Added:", name, "to namespace")
                self.found_change = True
                modns[name] = new_namespace[name]

            # Update in-place what we can
            for name in oldnames & newnames:
                self._update(modns, name, modns[name], new_namespace[name])

            self._handle_namespace(modns)

            for c in self._on_finish_callbacks:
                c()
            del self._on_finish_callbacks[:]
        except:
            pydev_log.exception()

    def _handle_namespace(self, namespace, is_class_namespace=False):
        on_finish = None
        if is_class_namespace:
            xreload_after_update = getattr(namespace, "__xreload_after_reload_update__", None)
            if xreload_after_update is not None:
                self.found_change = True
                on_finish = lambda: xreload_after_update()

        elif "__xreload_after_reload_update__" in namespace:
            xreload_after_update = namespace["__xreload_after_reload_update__"]
            self.found_change = True
            on_finish = lambda: xreload_after_update(namespace)

        if on_finish is not None:
            # If a client wants to know about it, give him a chance.
            self._on_finish_callbacks.append(on_finish)

    def _update(self, namespace, name, oldobj, newobj, is_class_namespace=False):
        """Update oldobj, if possible in place, with newobj.

        If oldobj is immutable, this simply returns newobj.

        Args:
          oldobj: the object to be updated
          newobj: the object used as the source for the update
        """
        try:
            notify_info2("Updating: ", oldobj)
            if oldobj is newobj:
                # Probably something imported
                return

            if type(oldobj) is not type(newobj):
                # Cop-out: if the type changed, give up
                if name not in ("__builtins__",):
                    notify_error("Type of: %s (old: %s != new: %s) changed... Skipping." % (name, type(oldobj), type(newobj)))
                return

            if isinstance(newobj, types.FunctionType):
                self._update_function(oldobj, newobj)
                return

            if isinstance(newobj, types.MethodType):
                self._update_method(oldobj, newobj)
                return

            if isinstance(newobj, classmethod):
                self._update_classmethod(oldobj, newobj)
                return

            if isinstance(newobj, staticmethod):
                self._update_staticmethod(oldobj, newobj)
                return

            if hasattr(types, "ClassType"):
                classtype = (types.ClassType, type)  # object is not instance of types.ClassType.
            else:
                classtype = type

            if isinstance(newobj, classtype):
                self._update_class(oldobj, newobj)
                return

            # New: dealing with metaclasses.
            if hasattr(newobj, "__metaclass__") and hasattr(newobj, "__class__") and newobj.__metaclass__ == newobj.__class__:
                self._update_class(oldobj, newobj)
                return

            if namespace is not None:
                # Check for the `__xreload_old_new__` protocol (don't even compare things
                # as even doing a comparison may break things -- see: https://github.com/microsoft/debugpy/issues/615).
                xreload_old_new = None
                if is_class_namespace:
                    xreload_old_new = getattr(namespace, "__xreload_old_new__", None)
                    if xreload_old_new is not None:
                        self.found_change = True
                        xreload_old_new(name, oldobj, newobj)

                elif "__xreload_old_new__" in namespace:
                    xreload_old_new = namespace["__xreload_old_new__"]
                    xreload_old_new(namespace, name, oldobj, newobj)
                    self.found_change = True

                # Too much information to the user...
                # else:
                #     notify_info0('%s NOT updated. Create __xreload_old_new__(name, old, new) for custom reload' % (name,))

        except:
            notify_error("Exception found when updating %s. Proceeding for other items." % (name,))
            pydev_log.exception()

    # All of the following functions have the same signature as _update()

    def _update_function(self, oldfunc, newfunc):
        """Update a function object."""
        oldfunc.__doc__ = newfunc.__doc__
        oldfunc.__dict__.update(newfunc.__dict__)

        try:
            newfunc.__code__
            attr_name = "__code__"
        except AttributeError:
            newfunc.func_code
            attr_name = "func_code"

        old_code = getattr(oldfunc, attr_name)
        new_code = getattr(newfunc, attr_name)
        if not code_objects_equal(old_code, new_code):
            notify_info0("Updated function code:", oldfunc)
            setattr(oldfunc, attr_name, new_code)
            self.found_change = True

        try:
            oldfunc.__defaults__ = newfunc.__defaults__
        except AttributeError:
            oldfunc.func_defaults = newfunc.func_defaults

        return oldfunc

    def _update_method(self, oldmeth, newmeth):
        """Update a method object."""
        # XXX What if im_func is not a function?
        if hasattr(oldmeth, "im_func") and hasattr(newmeth, "im_func"):
            self._update(None, None, oldmeth.im_func, newmeth.im_func)
        elif hasattr(oldmeth, "__func__") and hasattr(newmeth, "__func__"):
            self._update(None, None, oldmeth.__func__, newmeth.__func__)
        return oldmeth

    def _update_class(self, oldclass, newclass):
        """Update a class object."""
        olddict = oldclass.__dict__
        newdict = newclass.__dict__

        oldnames = set(olddict)
        newnames = set(newdict)

        for name in newnames - oldnames:
            setattr(oldclass, name, newdict[name])
            notify_info0("Added:", name, "to", oldclass)
            self.found_change = True

        # Note: not removing old things...
        # for name in oldnames - newnames:
        #    notify_info('Removed:', name, 'from', oldclass)
        #    delattr(oldclass, name)

        for name in (oldnames & newnames) - set(["__dict__", "__doc__"]):
            self._update(oldclass, name, olddict[name], newdict[name], is_class_namespace=True)

        old_bases = getattr(oldclass, "__bases__", None)
        new_bases = getattr(newclass, "__bases__", None)
        if str(old_bases) != str(new_bases):
            notify_error("Changing the hierarchy of a class is not supported. %s may be inconsistent." % (oldclass,))

        self._handle_namespace(oldclass, is_class_namespace=True)

    def _update_classmethod(self, oldcm, newcm):
        """Update a classmethod update."""
        # While we can't modify the classmethod object itself (it has no
        # mutable attributes), we *can* extract the underlying function
        # (by calling __get__(), which returns a method object) and update
        # it in-place.  We don't have the class available to pass to
        # __get__() but any object except None will do.
        self._update(None, None, oldcm.__get__(0), newcm.__get__(0))

    def _update_staticmethod(self, oldsm, newsm):
        """Update a staticmethod update."""
        # While we can't modify the staticmethod object itself (it has no
        # mutable attributes), we *can* extract the underlying function
        # (by calling __get__(), which returns it) and update it in-place.
        # We don't have the class available to pass to __get__() but any
        # object except None will do.
        self._update(None, None, oldsm.__get__(0), newsm.__get__(0))

# === NexusCore/openenv\Lib\site-packages\annotated_types\__init__.py ===
import math
import sys
import types
from dataclasses import dataclass
from datetime import tzinfo
from typing import TYPE_CHECKING, Any, Callable, Iterator, Optional, SupportsFloat, SupportsIndex, TypeVar, Union

if sys.version_info < (3, 8):
    from typing_extensions import Protocol, runtime_checkable
else:
    from typing import Protocol, runtime_checkable

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, Literal
else:
    from typing import Annotated, Literal

if sys.version_info < (3, 10):
    EllipsisType = type(Ellipsis)
    KW_ONLY = {}
    SLOTS = {}
else:
    from types import EllipsisType

    KW_ONLY = {"kw_only": True}
    SLOTS = {"slots": True}


__all__ = (
    'BaseMetadata',
    'GroupedMetadata',
    'Gt',
    'Ge',
    'Lt',
    'Le',
    'Interval',
    'MultipleOf',
    'MinLen',
    'MaxLen',
    'Len',
    'Timezone',
    'Predicate',
    'LowerCase',
    'UpperCase',
    'IsDigits',
    'IsFinite',
    'IsNotFinite',
    'IsNan',
    'IsNotNan',
    'IsInfinite',
    'IsNotInfinite',
    'doc',
    'DocInfo',
    '__version__',
)

__version__ = '0.7.0'


T = TypeVar('T')


# arguments that start with __ are considered
# positional only
# see https://peps.python.org/pep-0484/#positional-only-arguments


class SupportsGt(Protocol):
    def __gt__(self: T, __other: T) -> bool:
        ...


class SupportsGe(Protocol):
    def __ge__(self: T, __other: T) -> bool:
        ...


class SupportsLt(Protocol):
    def __lt__(self: T, __other: T) -> bool:
        ...


class SupportsLe(Protocol):
    def __le__(self: T, __other: T) -> bool:
        ...


class SupportsMod(Protocol):
    def __mod__(self: T, __other: T) -> T:
        ...


class SupportsDiv(Protocol):
    def __div__(self: T, __other: T) -> T:
        ...


class BaseMetadata:
    """Base class for all metadata.

    This exists mainly so that implementers
    can do `isinstance(..., BaseMetadata)` while traversing field annotations.
    """

    __slots__ = ()


@dataclass(frozen=True, **SLOTS)
class Gt(BaseMetadata):
    """Gt(gt=x) implies that the value must be greater than x.

    It can be used with any type that supports the ``>`` operator,
    including numbers, dates and times, strings, sets, and so on.
    """

    gt: SupportsGt


@dataclass(frozen=True, **SLOTS)
class Ge(BaseMetadata):
    """Ge(ge=x) implies that the value must be greater than or equal to x.

    It can be used with any type that supports the ``>=`` operator,
    including numbers, dates and times, strings, sets, and so on.
    """

    ge: SupportsGe


@dataclass(frozen=True, **SLOTS)
class Lt(BaseMetadata):
    """Lt(lt=x) implies that the value must be less than x.

    It can be used with any type that supports the ``<`` operator,
    including numbers, dates and times, strings, sets, and so on.
    """

    lt: SupportsLt


@dataclass(frozen=True, **SLOTS)
class Le(BaseMetadata):
    """Le(le=x) implies that the value must be less than or equal to x.

    It can be used with any type that supports the ``<=`` operator,
    including numbers, dates and times, strings, sets, and so on.
    """

    le: SupportsLe


@runtime_checkable
class GroupedMetadata(Protocol):
    """A grouping of multiple objects, like typing.Unpack.

    `GroupedMetadata` on its own is not metadata and has no meaning.
    All of the constraints and metadata should be fully expressable
    in terms of the `BaseMetadata`'s returned by `GroupedMetadata.__iter__()`.

    Concrete implementations should override `GroupedMetadata.__iter__()`
    to add their own metadata.
    For example:

    >>> @dataclass
    >>> class Field(GroupedMetadata):
    >>>     gt: float | None = None
    >>>     description: str | None = None
    ...
    >>>     def __iter__(self) -> Iterable[object]:
    >>>         if self.gt is not None:
    >>>             yield Gt(self.gt)
    >>>         if self.description is not None:
    >>>             yield Description(self.gt)

    Also see the implementation of `Interval` below for an example.

    Parsers should recognize this and unpack it so that it can be used
    both with and without unpacking:

    - `Annotated[int, Field(...)]` (parser must unpack Field)
    - `Annotated[int, *Field(...)]` (PEP-646)
    """  # noqa: trailing-whitespace

    @property
    def __is_annotated_types_grouped_metadata__(self) -> Literal[True]:
        return True

    def __iter__(self) -> Iterator[object]:
        ...

    if not TYPE_CHECKING:
        __slots__ = ()  # allow subclasses to use slots

        def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
            # Basic ABC like functionality without the complexity of an ABC
            super().__init_subclass__(*args, **kwargs)
            if cls.__iter__ is GroupedMetadata.__iter__:
                raise TypeError("Can't subclass GroupedMetadata without implementing __iter__")

        def __iter__(self) -> Iterator[object]:  # noqa: F811
            raise NotImplementedError  # more helpful than "None has no attribute..." type errors


@dataclass(frozen=True, **KW_ONLY, **SLOTS)
class Interval(GroupedMetadata):
    """Interval can express inclusive or exclusive bounds with a single object.

    It accepts keyword arguments ``gt``, ``ge``, ``lt``, and/or ``le``, which
    are interpreted the same way as the single-bound constraints.
    """

    gt: Union[SupportsGt, None] = None
    ge: Union[SupportsGe, None] = None
    lt: Union[SupportsLt, None] = None
    le: Union[SupportsLe, None] = None

    def __iter__(self) -> Iterator[BaseMetadata]:
        """Unpack an Interval into zero or more single-bounds."""
        if self.gt is not None:
            yield Gt(self.gt)
        if self.ge is not None:
            yield Ge(self.ge)
        if self.lt is not None:
            yield Lt(self.lt)
        if self.le is not None:
            yield Le(self.le)


@dataclass(frozen=True, **SLOTS)
class MultipleOf(BaseMetadata):
    """MultipleOf(multiple_of=x) might be interpreted in two ways:

    1. Python semantics, implying ``value % multiple_of == 0``, or
    2. JSONschema semantics, where ``int(value / multiple_of) == value / multiple_of``

    We encourage users to be aware of these two common interpretations,
    and libraries to carefully document which they implement.
    """

    multiple_of: Union[SupportsDiv, SupportsMod]


@dataclass(frozen=True, **SLOTS)
class MinLen(BaseMetadata):
    """
    MinLen() implies minimum inclusive length,
    e.g. ``len(value) >= min_length``.
    """

    min_length: Annotated[int, Ge(0)]


@dataclass(frozen=True, **SLOTS)
class MaxLen(BaseMetadata):
    """
    MaxLen() implies maximum inclusive length,
    e.g. ``len(value) <= max_length``.
    """

    max_length: Annotated[int, Ge(0)]


@dataclass(frozen=True, **SLOTS)
class Len(GroupedMetadata):
    """
    Len() implies that ``min_length <= len(value) <= max_length``.

    Upper bound may be omitted or ``None`` to indicate no upper length bound.
    """

    min_length: Annotated[int, Ge(0)] = 0
    max_length: Optional[Annotated[int, Ge(0)]] = None

    def __iter__(self) -> Iterator[BaseMetadata]:
        """Unpack a Len into zone or more single-bounds."""
        if self.min_length > 0:
            yield MinLen(self.min_length)
        if self.max_length is not None:
            yield MaxLen(self.max_length)


@dataclass(frozen=True, **SLOTS)
class Timezone(BaseMetadata):
    """Timezone(tz=...) requires a datetime to be aware (or ``tz=None``, naive).

    ``Annotated[datetime, Timezone(None)]`` must be a naive datetime.
    ``Timezone[...]`` (the ellipsis literal) expresses that the datetime must be
    tz-aware but any timezone is allowed.

    You may also pass a specific timezone string or tzinfo object such as
    ``Timezone(timezone.utc)`` or ``Timezone("Africa/Abidjan")`` to express that
    you only allow a specific timezone, though we note that this is often
    a symptom of poor design.
    """

    tz: Union[str, tzinfo, EllipsisType, None]


@dataclass(frozen=True, **SLOTS)
class Unit(BaseMetadata):
    """Indicates that the value is a physical quantity with the specified unit.

    It is intended for usage with numeric types, where the value represents the
    magnitude of the quantity. For example, ``distance: Annotated[float, Unit('m')]``
    or ``speed: Annotated[float, Unit('m/s')]``.

    Interpretation of the unit string is left to the discretion of the consumer.
    It is suggested to follow conventions established by python libraries that work
    with physical quantities, such as

    - ``pint`` : <https://pint.readthedocs.io/en/stable/>
    - ``astropy.units``: <https://docs.astropy.org/en/stable/units/>

    For indicating a quantity with a certain dimensionality but without a specific unit
    it is recommended to use square brackets, e.g. `Annotated[float, Unit('[time]')]`.
    Note, however, ``annotated_types`` itself makes no use of the unit string.
    """

    unit: str


@dataclass(frozen=True, **SLOTS)
class Predicate(BaseMetadata):
    """``Predicate(func: Callable)`` implies `func(value)` is truthy for valid values.

    Users should prefer statically inspectable metadata, but if you need the full
    power and flexibility of arbitrary runtime predicates... here it is.

    We provide a few predefined predicates for common string constraints:
    ``IsLower = Predicate(str.islower)``, ``IsUpper = Predicate(str.isupper)``, and
    ``IsDigits = Predicate(str.isdigit)``. Users are encouraged to use methods which
    can be given special handling, and avoid indirection like ``lambda s: s.lower()``.

    Some libraries might have special logic to handle certain predicates, e.g. by
    checking for `str.isdigit` and using its presence to both call custom logic to
    enforce digit-only strings, and customise some generated external schema.

    We do not specify what behaviour should be expected for predicates that raise
    an exception.  For example `Annotated[int, Predicate(str.isdigit)]` might silently
    skip invalid constraints, or statically raise an error; or it might try calling it
    and then propagate or discard the resulting exception.
    """

    func: Callable[[Any], bool]

    def __repr__(self) -> str:
        if getattr(self.func, "__name__", "<lambda>") == "<lambda>":
            return f"{self.__class__.__name__}({self.func!r})"
        if isinstance(self.func, (types.MethodType, types.BuiltinMethodType)) and (
            namespace := getattr(self.func.__self__, "__name__", None)
        ):
            return f"{self.__class__.__name__}({namespace}.{self.func.__name__})"
        if isinstance(self.func, type(str.isascii)):  # method descriptor
            return f"{self.__class__.__name__}({self.func.__qualname__})"
        return f"{self.__class__.__name__}({self.func.__name__})"


@dataclass
class Not:
    func: Callable[[Any], bool]

    def __call__(self, __v: Any) -> bool:
        return not self.func(__v)


_StrType = TypeVar("_StrType", bound=str)

LowerCase = Annotated[_StrType, Predicate(str.islower)]
"""
Return True if the string is a lowercase string, False otherwise.

A string is lowercase if all cased characters in the string are lowercase and there is at least one cased character in the string.
"""  # noqa: E501
UpperCase = Annotated[_StrType, Predicate(str.isupper)]
"""
Return True if the string is an uppercase string, False otherwise.

A string is uppercase if all cased characters in the string are uppercase and there is at least one cased character in the string.
"""  # noqa: E501
IsDigit = Annotated[_StrType, Predicate(str.isdigit)]
IsDigits = IsDigit  # type: ignore  # plural for backwards compatibility, see #63
"""
Return True if the string is a digit string, False otherwise.

A string is a digit string if all characters in the string are digits and there is at least one character in the string.
"""  # noqa: E501
IsAscii = Annotated[_StrType, Predicate(str.isascii)]
"""
Return True if all characters in the string are ASCII, False otherwise.

ASCII characters have code points in the range U+0000-U+007F. Empty string is ASCII too.
"""

_NumericType = TypeVar('_NumericType', bound=Union[SupportsFloat, SupportsIndex])
IsFinite = Annotated[_NumericType, Predicate(math.isfinite)]
"""Return True if x is neither an infinity nor a NaN, and False otherwise."""
IsNotFinite = Annotated[_NumericType, Predicate(Not(math.isfinite))]
"""Return True if x is one of infinity or NaN, and False otherwise"""
IsNan = Annotated[_NumericType, Predicate(math.isnan)]
"""Return True if x is a NaN (not a number), and False otherwise."""
IsNotNan = Annotated[_NumericType, Predicate(Not(math.isnan))]
"""Return True if x is anything but NaN (not a number), and False otherwise."""
IsInfinite = Annotated[_NumericType, Predicate(math.isinf)]
"""Return True if x is a positive or negative infinity, and False otherwise."""
IsNotInfinite = Annotated[_NumericType, Predicate(Not(math.isinf))]
"""Return True if x is neither a positive or negative infinity, and False otherwise."""

try:
    from typing_extensions import DocInfo, doc  # type: ignore [attr-defined]
except ImportError:

    @dataclass(frozen=True, **SLOTS)
    class DocInfo:  # type: ignore [no-redef]
        """ "
        The return value of doc(), mainly to be used by tools that want to extract the
        Annotated documentation at runtime.
        """

        documentation: str
        """The documentation string passed to doc()."""

    def doc(
        documentation: str,
    ) -> DocInfo:
        """
        Add documentation to a type annotation inside of Annotated.

        For example:

        >>> def hi(name: Annotated[int, doc("The name of the user")]) -> None: ...
        """
        return DocInfo(documentation)

# === NexusCore/openenv\Lib\site-packages\litellm\types\llms\anthropic.py ===
from typing import Any, Dict, Iterable, List, Optional, Union

from pydantic import BaseModel, validator
from typing_extensions import Literal, Required, TypedDict

from .openai import ChatCompletionCachedContent, ChatCompletionThinkingBlock


class AnthropicMessagesToolChoice(TypedDict, total=False):
    type: Required[Literal["auto", "any", "tool", "none"]]
    name: str
    disable_parallel_tool_use: bool  # default is false


class AnthropicInputSchema(TypedDict, total=False):
    type: Optional[str]
    properties: Optional[dict]
    additionalProperties: Optional[bool]


class AnthropicMessagesTool(TypedDict, total=False):
    name: Required[str]
    description: str
    input_schema: Optional[AnthropicInputSchema]
    type: Literal["custom"]
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]


class AnthropicComputerTool(TypedDict, total=False):
    display_width_px: Required[int]
    display_height_px: Required[int]
    display_number: int
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]
    type: Required[str]
    name: Required[str]


class AnthropicWebSearchUserLocation(TypedDict, total=False):
    city: Optional[str]
    country: Optional[str]
    region: Optional[str]
    timezone: Optional[str]
    type: Required[Literal["approximate"]]


class AnthropicWebSearchTool(TypedDict, total=False):
    name: Required[Literal["web_search"]]
    type: Required[str]
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]
    max_uses: Optional[int]
    user_location: Optional[AnthropicWebSearchUserLocation]


class AnthropicHostedTools(TypedDict, total=False):  # for bash_tool and text_editor
    type: Required[str]
    name: Required[str]
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]


class AnthropicCodeExecutionTool(TypedDict, total=False):
    type: Required[str]
    name: Required[Literal["code_execution"]]
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]


AllAnthropicToolsValues = Union[
    AnthropicComputerTool,
    AnthropicHostedTools,
    AnthropicMessagesTool,
    AnthropicWebSearchTool,
    AnthropicCodeExecutionTool,
]


class AnthropicMcpServerToolConfiguration(TypedDict, total=False):
    allowed_tools: Optional[List[str]]


class AnthropicMcpServerTool(TypedDict, total=False):
    type: Required[Literal["url"]]
    url: Required[str]
    name: Required[str]
    tool_configuration: AnthropicMcpServerToolConfiguration
    authorization_token: str


class AnthropicMessagesTextParam(TypedDict, total=False):
    type: Required[Literal["text"]]
    text: Required[str]
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]


class AnthropicMessagesToolUseParam(TypedDict, total=False):
    type: Required[Literal["tool_use"]]
    id: str
    name: str
    input: dict
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]


AnthropicMessagesAssistantMessageValues = Union[
    AnthropicMessagesTextParam,
    AnthropicMessagesToolUseParam,
    ChatCompletionThinkingBlock,
]


class AnthopicMessagesAssistantMessageParam(TypedDict, total=False):
    content: Required[Union[str, Iterable[AnthropicMessagesAssistantMessageValues]]]
    """The contents of the system message."""

    role: Required[Literal["assistant"]]
    """The role of the messages author, in this case `author`."""

    name: str
    """An optional name for the participant.

    Provides the model information to differentiate between participants of the same
    role.
    """


class AnthropicContentParamSource(TypedDict):
    type: Literal["base64"]
    media_type: str
    data: str


class AnthropicContentParamSourceUrl(TypedDict):
    type: Literal["url"]
    url: str


class AnthropicContentParamSourceFileId(TypedDict):
    type: Literal["file"]
    file_id: str


class AnthropicMessagesContainerUploadParam(TypedDict, total=False):
    type: Required[Literal["container_upload"]]
    file_id: str
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]


class AnthropicMessagesImageParam(TypedDict, total=False):
    type: Required[Literal["image"]]
    source: Required[
        Union[AnthropicContentParamSource, AnthropicContentParamSourceFileId]
    ]
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]


class CitationsObject(TypedDict):
    enabled: bool


class AnthropicMessagesDocumentParam(TypedDict, total=False):
    type: Required[Literal["document"]]
    source: Required[
        Union[
            AnthropicContentParamSource,
            AnthropicContentParamSourceFileId,
            AnthropicContentParamSourceUrl,
        ]
    ]
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]
    title: str
    context: str
    citations: Optional[CitationsObject]


class AnthropicMessagesToolResultContent(TypedDict):
    type: Literal["text"]
    text: str


class AnthropicMessagesToolResultParam(TypedDict, total=False):
    type: Required[Literal["tool_result"]]
    tool_use_id: Required[str]
    is_error: bool
    content: Union[
        str,
        Iterable[
            Union[AnthropicMessagesToolResultContent, AnthropicMessagesImageParam]
        ],
    ]
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]


AnthropicMessagesUserMessageValues = Union[
    AnthropicMessagesTextParam,
    AnthropicMessagesImageParam,
    AnthropicMessagesToolResultParam,
    AnthropicMessagesDocumentParam,
    AnthropicMessagesContainerUploadParam,
]


class AnthropicMessagesUserMessageParam(TypedDict, total=False):
    role: Required[Literal["user"]]
    content: Required[Union[str, Iterable[AnthropicMessagesUserMessageValues]]]


class AnthropicMetadata(TypedDict, total=False):
    user_id: str


class AnthropicSystemMessageContent(TypedDict, total=False):
    type: str
    text: str
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]


AllAnthropicMessageValues = Union[
    AnthropicMessagesUserMessageParam, AnthopicMessagesAssistantMessageParam
]


class AnthropicMessagesRequestOptionalParams(TypedDict, total=False):
    max_tokens: Optional[int]
    metadata: Optional[Union[AnthropicMetadata, Dict]]
    stop_sequences: Optional[List[str]]
    stream: Optional[bool]
    system: Optional[Union[str, List]]
    temperature: Optional[float]
    thinking: Optional[Dict]
    tool_choice: Optional[Union[AnthropicMessagesToolChoice, Dict]]
    tools: Optional[List[Union[AllAnthropicToolsValues, Dict]]]
    top_k: Optional[int]
    top_p: Optional[float]
    mcp_servers: Optional[List[AnthropicMcpServerTool]]


class AnthropicMessagesRequest(AnthropicMessagesRequestOptionalParams, total=False):
    model: Required[str]
    messages: Required[Union[List[AllAnthropicMessageValues], List[Dict]]]
    # litellm param - used for tracking litellm proxy metadata in the request
    litellm_metadata: dict


class ContentTextBlockDelta(TypedDict):
    """
    'delta': {'type': 'text_delta', 'text': 'Hello'}
    """

    type: str
    text: str


class ContentCitationsBlockDelta(TypedDict):
    type: Literal["citations"]
    citation: dict


class ContentJsonBlockDelta(TypedDict):
    """
    "delta": {"type": "input_json_delta","partial_json": "{\"location\": \"San Fra"}}
    """

    type: str
    partial_json: str


class ContentBlockDelta(TypedDict):
    type: Literal["content_block_delta"]
    index: int
    delta: Union[
        ContentTextBlockDelta, ContentJsonBlockDelta, ContentCitationsBlockDelta
    ]


class ContentBlockStop(TypedDict):
    type: Literal["content_block_stop"]
    index: int


class ToolUseBlock(TypedDict):
    """
    "content_block":{"type":"tool_use","id":"toolu_01T1x1fJ34qAmk2tNTrN7Up6","name":"get_weather","input":{}}
    """

    id: str

    input: dict

    name: str

    type: Literal["tool_use"]


class TextBlock(TypedDict):
    text: str

    type: Literal["text"]


class ContentBlockStart(TypedDict):
    """
    event: content_block_start
    data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_01T1x1fJ34qAmk2tNTrN7Up6","name":"get_weather","input":{}}}
    """

    type: str
    index: int
    content_block: Union[ToolUseBlock, TextBlock]


class MessageDelta(TypedDict, total=False):
    stop_reason: Optional[str]


class UsageDelta(TypedDict, total=False):
    input_tokens: int
    output_tokens: int


class MessageBlockDelta(TypedDict):
    """
    Anthropic
    chunk = {'type': 'message_delta', 'delta': {'stop_reason': 'max_tokens', 'stop_sequence': None}, 'usage': {'output_tokens': 10}}
    """

    type: Literal["message_delta"]
    delta: MessageDelta
    usage: UsageDelta


class MessageChunk(TypedDict, total=False):
    id: str
    type: str
    role: str
    model: str
    content: List
    stop_reason: Optional[str]
    stop_sequence: Optional[str]
    usage: UsageDelta


class MessageStartBlock(TypedDict):
    """
        Anthropic
        chunk = {
        "type": "message_start",
        "message": {
            "id": "msg_vrtx_011PqREFEMzd3REdCoUFAmdG",
            "type": "message",
            "role": "assistant",
            "model": "claude-3-sonnet-20240229",
            "content": [],
            "stop_reason": null,
            "stop_sequence": null,
            "usage": {
                "input_tokens": 270,
                "output_tokens": 1
            }
        }
    }
    """

    type: Literal["message_start"]
    message: MessageChunk


class AnthropicResponseContentBlockText(BaseModel):
    type: Literal["text"]
    text: str


class AnthropicResponseContentBlockToolUse(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: dict


class AnthropicResponseUsageBlock(BaseModel):
    input_tokens: int
    output_tokens: int


AnthropicFinishReason = Literal["end_turn", "max_tokens", "stop_sequence", "tool_use"]


class AnthropicResponse(BaseModel):
    id: str
    """Unique object identifier."""

    type: Literal["message"]
    """For Messages, this is always "message"."""

    role: Literal["assistant"]
    """Conversational role of the generated message. This will always be "assistant"."""

    content: List[
        Union[AnthropicResponseContentBlockText, AnthropicResponseContentBlockToolUse]
    ]
    """Content generated by the model."""

    model: str
    """The model that handled the request."""

    stop_reason: Optional[AnthropicFinishReason]
    """The reason that we stopped."""

    stop_sequence: Optional[str]
    """Which custom stop sequence was generated, if any."""

    usage: AnthropicResponseUsageBlock
    """Billing and rate-limit usage."""


from .openai import ChatCompletionUsageBlock


class AnthropicChatCompletionUsageBlock(ChatCompletionUsageBlock, total=False):
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


ANTHROPIC_API_HEADERS = {
    "anthropic-version",
    "anthropic-beta",
}

ANTHROPIC_API_ONLY_HEADERS = {  # fails if calling anthropic on vertex ai / bedrock
    "anthropic-beta",
}


class AnthropicThinkingParam(TypedDict, total=False):
    type: Literal["enabled"]
    budget_tokens: int

# === NexusCore/openenv\Lib\site-packages\jupyter_client\adapter.py ===
"""Adapters for Jupyter msg spec versions."""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
import re
from typing import Any, Dict, List, Tuple

from ._version import protocol_version_info


def code_to_line(code: str, cursor_pos: int) -> Tuple[str, int]:
    """Turn a multiline code block and cursor position into a single line
    and new cursor position.

    For adapting ``complete_`` and ``object_info_request``.
    """
    if not code:
        return "", 0
    for line in code.splitlines(True):
        n = len(line)
        if cursor_pos > n:
            cursor_pos -= n
        else:
            break
    return line, cursor_pos


_match_bracket = re.compile(r"\([^\(\)]+\)", re.UNICODE)
_end_bracket = re.compile(r"\([^\(]*$", re.UNICODE)
_identifier = re.compile(r"[a-z_][0-9a-z._]*", re.I | re.UNICODE)


def extract_oname_v4(code: str, cursor_pos: int) -> str:
    """Reimplement token-finding logic from IPython 2.x javascript

    for adapting object_info_request from v5 to v4
    """

    line, _ = code_to_line(code, cursor_pos)

    oldline = line
    line = _match_bracket.sub("", line)
    while oldline != line:
        oldline = line
        line = _match_bracket.sub("", line)

    # remove everything after last open bracket
    line = _end_bracket.sub("", line)
    matches = _identifier.findall(line)
    if matches:
        return matches[-1]
    else:
        return ""


class Adapter:
    """Base class for adapting messages

    Override message_type(msg) methods to create adapters.
    """

    msg_type_map: Dict[str, str] = {}

    def update_header(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Update the header."""
        return msg

    def update_metadata(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Update the metadata."""
        return msg

    def update_msg_type(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Update the message type."""
        header = msg["header"]
        msg_type = header["msg_type"]
        if msg_type in self.msg_type_map:
            msg["msg_type"] = header["msg_type"] = self.msg_type_map[msg_type]
        return msg

    def handle_reply_status_error(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """This will be called *instead of* the regular handler

        on any reply with status != ok
        """
        return msg

    def __call__(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        msg = self.update_header(msg)
        msg = self.update_metadata(msg)
        msg = self.update_msg_type(msg)
        header = msg["header"]

        handler = getattr(self, header["msg_type"], None)
        if handler is None:
            return msg

        # handle status=error replies separately (no change, at present)
        if msg["content"].get("status", None) in {"error", "aborted"}:
            return self.handle_reply_status_error(msg)
        return handler(msg)


def _version_str_to_list(version: str) -> List[int]:
    """convert a version string to a list of ints

    non-int segments are excluded
    """
    v = []
    for part in version.split("."):
        try:
            v.append(int(part))
        except ValueError:
            pass
    return v


class V5toV4(Adapter):
    """Adapt msg protocol v5 to v4"""

    version = "4.1"

    msg_type_map = {
        "execute_result": "pyout",
        "execute_input": "pyin",
        "error": "pyerr",
        "inspect_request": "object_info_request",
        "inspect_reply": "object_info_reply",
    }

    def update_header(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Update the header."""
        msg["header"].pop("version", None)
        msg["parent_header"].pop("version", None)
        return msg

    # shell channel

    def kernel_info_reply(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a kernel info reply."""
        v4c = {}
        content = msg["content"]
        for key in ("language_version", "protocol_version"):
            if key in content:
                v4c[key] = _version_str_to_list(content[key])
        if content.get("implementation", "") == "ipython" and "implementation_version" in content:
            v4c["ipython_version"] = _version_str_to_list(content["implementation_version"])
        language_info = content.get("language_info", {})
        language = language_info.get("name", "")
        v4c.setdefault("language", language)
        if "version" in language_info:
            v4c.setdefault("language_version", _version_str_to_list(language_info["version"]))
        msg["content"] = v4c
        return msg

    def execute_request(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an execute request."""
        content = msg["content"]
        content.setdefault("user_variables", [])
        return msg

    def execute_reply(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an execute reply."""
        content = msg["content"]
        content.setdefault("user_variables", {})
        # TODO: handle payloads
        return msg

    def complete_request(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a complete request."""
        content = msg["content"]
        code = content["code"]
        cursor_pos = content["cursor_pos"]
        line, cursor_pos = code_to_line(code, cursor_pos)

        new_content = msg["content"] = {}
        new_content["text"] = ""
        new_content["line"] = line
        new_content["block"] = None
        new_content["cursor_pos"] = cursor_pos
        return msg

    def complete_reply(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a complete reply."""
        content = msg["content"]
        cursor_start = content.pop("cursor_start")
        cursor_end = content.pop("cursor_end")
        match_len = cursor_end - cursor_start
        content["matched_text"] = content["matches"][0][:match_len]
        content.pop("metadata", None)
        return msg

    def object_info_request(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an object info request."""
        content = msg["content"]
        code = content["code"]
        cursor_pos = content["cursor_pos"]
        line, _ = code_to_line(code, cursor_pos)

        new_content = msg["content"] = {}
        new_content["oname"] = extract_oname_v4(code, cursor_pos)
        new_content["detail_level"] = content["detail_level"]
        return msg

    def object_info_reply(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """inspect_reply can't be easily backward compatible"""
        msg["content"] = {"found": False, "oname": "unknown"}
        return msg

    # iopub channel

    def stream(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a stream message."""
        content = msg["content"]
        content["data"] = content.pop("text")
        return msg

    def display_data(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a display data message."""
        content = msg["content"]
        content.setdefault("source", "display")
        data = content["data"]
        if "application/json" in data:
            try:
                data["application/json"] = json.dumps(data["application/json"])
            except Exception:
                # warn?
                pass
        return msg

    # stdin channel

    def input_request(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an input request."""
        msg["content"].pop("password", None)
        return msg


class V4toV5(Adapter):
    """Convert msg spec V4 to V5"""

    version = "5.0"

    # invert message renames above
    msg_type_map = {v: k for k, v in V5toV4.msg_type_map.items()}

    def update_header(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Update the header."""
        msg["header"]["version"] = self.version
        if msg["parent_header"]:
            msg["parent_header"]["version"] = self.version
        return msg

    # shell channel

    def kernel_info_reply(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a kernel info reply."""
        content = msg["content"]
        for key in ("protocol_version", "ipython_version"):
            if key in content:
                content[key] = ".".join(map(str, content[key]))

        content.setdefault("protocol_version", "4.1")

        if content["language"].startswith("python") and "ipython_version" in content:
            content["implementation"] = "ipython"
            content["implementation_version"] = content.pop("ipython_version")

        language = content.pop("language")
        language_info = content.setdefault("language_info", {})
        language_info.setdefault("name", language)
        if "language_version" in content:
            language_version = ".".join(map(str, content.pop("language_version")))
            language_info.setdefault("version", language_version)

        content["banner"] = ""
        return msg

    def execute_request(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an execute request."""
        content = msg["content"]
        user_variables = content.pop("user_variables", [])
        user_expressions = content.setdefault("user_expressions", {})
        for v in user_variables:
            user_expressions[v] = v
        return msg

    def execute_reply(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an execute reply."""
        content = msg["content"]
        user_expressions = content.setdefault("user_expressions", {})
        user_variables = content.pop("user_variables", {})
        if user_variables:
            user_expressions.update(user_variables)

        # Pager payloads became a mime bundle
        for payload in content.get("payload", []):
            if payload.get("source", None) == "page" and ("text" in payload):
                if "data" not in payload:
                    payload["data"] = {}
                payload["data"]["text/plain"] = payload.pop("text")

        return msg

    def complete_request(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a complete request."""
        old_content = msg["content"]

        new_content = msg["content"] = {}
        new_content["code"] = old_content["line"]
        new_content["cursor_pos"] = old_content["cursor_pos"]
        return msg

    def complete_reply(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a complete reply."""
        # complete_reply needs more context than we have to get cursor_start and end.
        # use special end=null to indicate current cursor position and negative offset
        # for start relative to the cursor.
        # start=None indicates that start == end (accounts for no -0).
        content = msg["content"]
        new_content = msg["content"] = {"status": "ok"}
        new_content["matches"] = content["matches"]
        if content["matched_text"]:
            new_content["cursor_start"] = -len(content["matched_text"])
        else:
            # no -0, use None to indicate that start == end
            new_content["cursor_start"] = None
        new_content["cursor_end"] = None
        new_content["metadata"] = {}
        return msg

    def inspect_request(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an inspect request."""
        content = msg["content"]
        name = content["oname"]

        new_content = msg["content"] = {}
        new_content["code"] = name
        new_content["cursor_pos"] = len(name)
        new_content["detail_level"] = content["detail_level"]
        return msg

    def inspect_reply(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """inspect_reply can't be easily backward compatible"""
        content = msg["content"]
        new_content = msg["content"] = {"status": "ok"}
        found = new_content["found"] = content["found"]
        new_content["data"] = data = {}
        new_content["metadata"] = {}
        if found:
            lines = []
            for key in ("call_def", "init_definition", "definition"):
                if content.get(key, False):
                    lines.append(content[key])
                    break
            for key in ("call_docstring", "init_docstring", "docstring"):
                if content.get(key, False):
                    lines.append(content[key])
                    break
            if not lines:
                lines.append("<empty docstring>")
            data["text/plain"] = "\n".join(lines)
        return msg

    # iopub channel

    def stream(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a stream message."""
        content = msg["content"]
        content["text"] = content.pop("data")
        return msg

    def display_data(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle display data."""
        content = msg["content"]
        content.pop("source", None)
        data = content["data"]
        if "application/json" in data:
            try:
                data["application/json"] = json.loads(data["application/json"])
            except Exception:
                # warn?
                pass
        return msg

    # stdin channel

    def input_request(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an input request."""
        msg["content"].setdefault("password", False)
        return msg


def adapt(msg: Dict[str, Any], to_version: int = protocol_version_info[0]) -> Dict[str, Any]:
    """Adapt a single message to a target version

    Parameters
    ----------

    msg : dict
        A Jupyter message.
    to_version : int, optional
        The target major version.
        If unspecified, adapt to the current version.

    Returns
    -------

    msg : dict
        A Jupyter message appropriate in the new version.
    """
    from .session import utcnow

    header = msg["header"]
    if "date" not in header:
        header["date"] = utcnow()
    if "version" in header:
        from_version = int(header["version"].split(".")[0])
    else:
        # assume last version before adding the key to the header
        from_version = 4
    adapter = adapters.get((from_version, to_version), None)
    if adapter is None:
        return msg
    return adapter(msg)


# one adapter per major version from,to
adapters = {
    (5, 4): V5toV4(),
    (4, 5): V4toV5(),
}

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\tuned_model.py ===
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

from google.protobuf import timestamp_pb2  # type: ignore
import proto  # type: ignore

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "TunedModel",
        "TunedModelSource",
        "TuningTask",
        "Hyperparameters",
        "Dataset",
        "TuningExamples",
        "TuningExample",
        "TuningSnapshot",
    },
)


class TunedModel(proto.Message):
    r"""A fine-tuned model created using
    ModelService.CreateTunedModel.

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        tuned_model_source (google.ai.generativelanguage_v1beta.types.TunedModelSource):
            Optional. TunedModel to use as the starting
            point for training the new model.

            This field is a member of `oneof`_ ``source_model``.
        base_model (str):
            Immutable. The name of the ``Model`` to tune. Example:
            ``models/text-bison-001``

            This field is a member of `oneof`_ ``source_model``.
        name (str):
            Output only. The tuned model name. A unique name will be
            generated on create. Example: ``tunedModels/az2mb0bpw6i`` If
            display_name is set on create, the id portion of the name
            will be set by concatenating the words of the display_name
            with hyphens and adding a random portion for uniqueness.
            Example: display_name = "Sentence Translator" name =
            "tunedModels/sentence-translator-u3b7m".
        display_name (str):
            Optional. The name to display for this model
            in user interfaces. The display name must be up
            to 40 characters including spaces.
        description (str):
            Optional. A short description of this model.
        temperature (float):
            Optional. Controls the randomness of the output.

            Values can range over ``[0.0,1.0]``, inclusive. A value
            closer to ``1.0`` will produce responses that are more
            varied, while a value closer to ``0.0`` will typically
            result in less surprising responses from the model.

            This value specifies default to be the one used by the base
            model while creating the model.

            This field is a member of `oneof`_ ``_temperature``.
        top_p (float):
            Optional. For Nucleus sampling.

            Nucleus sampling considers the smallest set of tokens whose
            probability sum is at least ``top_p``.

            This value specifies default to be the one used by the base
            model while creating the model.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            Optional. For Top-k sampling.

            Top-k sampling considers the set of ``top_k`` most probable
            tokens. This value specifies default to be used by the
            backend while making the call to the model.

            This value specifies default to be the one used by the base
            model while creating the model.

            This field is a member of `oneof`_ ``_top_k``.
        state (google.ai.generativelanguage_v1beta.types.TunedModel.State):
            Output only. The state of the tuned model.
        create_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp when this model
            was created.
        update_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp when this model
            was updated.
        tuning_task (google.ai.generativelanguage_v1beta.types.TuningTask):
            Required. The tuning task that creates the
            tuned model.
    """

    class State(proto.Enum):
        r"""The state of the tuned model.

        Values:
            STATE_UNSPECIFIED (0):
                The default value. This value is unused.
            CREATING (1):
                The model is being created.
            ACTIVE (2):
                The model is ready to be used.
            FAILED (3):
                The model failed to be created.
        """
        STATE_UNSPECIFIED = 0
        CREATING = 1
        ACTIVE = 2
        FAILED = 3

    tuned_model_source: "TunedModelSource" = proto.Field(
        proto.MESSAGE,
        number=3,
        oneof="source_model",
        message="TunedModelSource",
    )
    base_model: str = proto.Field(
        proto.STRING,
        number=4,
        oneof="source_model",
    )
    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=5,
    )
    description: str = proto.Field(
        proto.STRING,
        number=6,
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=11,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=12,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=13,
        optional=True,
    )
    state: State = proto.Field(
        proto.ENUM,
        number=7,
        enum=State,
    )
    create_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=8,
        message=timestamp_pb2.Timestamp,
    )
    update_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=9,
        message=timestamp_pb2.Timestamp,
    )
    tuning_task: "TuningTask" = proto.Field(
        proto.MESSAGE,
        number=10,
        message="TuningTask",
    )


class TunedModelSource(proto.Message):
    r"""Tuned model as a source for training a new model.

    Attributes:
        tuned_model (str):
            Immutable. The name of the ``TunedModel`` to use as the
            starting point for training the new model. Example:
            ``tunedModels/my-tuned-model``
        base_model (str):
            Output only. The name of the base ``Model`` this
            ``TunedModel`` was tuned from. Example:
            ``models/text-bison-001``
    """

    tuned_model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    base_model: str = proto.Field(
        proto.STRING,
        number=2,
    )


class TuningTask(proto.Message):
    r"""Tuning tasks that create tuned models.

    Attributes:
        start_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp when tuning this
            model started.
        complete_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp when tuning this
            model completed.
        snapshots (MutableSequence[google.ai.generativelanguage_v1beta.types.TuningSnapshot]):
            Output only. Metrics collected during tuning.
        training_data (google.ai.generativelanguage_v1beta.types.Dataset):
            Required. Input only. Immutable. The model
            training data.
        hyperparameters (google.ai.generativelanguage_v1beta.types.Hyperparameters):
            Immutable. Hyperparameters controlling the
            tuning process. If not provided, default values
            will be used.
    """

    start_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=1,
        message=timestamp_pb2.Timestamp,
    )
    complete_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=2,
        message=timestamp_pb2.Timestamp,
    )
    snapshots: MutableSequence["TuningSnapshot"] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message="TuningSnapshot",
    )
    training_data: "Dataset" = proto.Field(
        proto.MESSAGE,
        number=4,
        message="Dataset",
    )
    hyperparameters: "Hyperparameters" = proto.Field(
        proto.MESSAGE,
        number=5,
        message="Hyperparameters",
    )


class Hyperparameters(proto.Message):
    r"""Hyperparameters controlling the tuning process. Read more at
    https://ai.google.dev/docs/model_tuning_guidance

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        learning_rate (float):
            Optional. Immutable. The learning rate
            hyperparameter for tuning. If not set, a default
            of 0.001 or 0.0002 will be calculated based on
            the number of training examples.

            This field is a member of `oneof`_ ``learning_rate_option``.
        learning_rate_multiplier (float):
            Optional. Immutable. The learning rate multiplier is used to
            calculate a final learning_rate based on the default
            (recommended) value. Actual learning rate :=
            learning_rate_multiplier \* default learning rate Default
            learning rate is dependent on base model and dataset size.
            If not set, a default of 1.0 will be used.

            This field is a member of `oneof`_ ``learning_rate_option``.
        epoch_count (int):
            Immutable. The number of training epochs. An
            epoch is one pass through the training data. If
            not set, a default of 5 will be used.

            This field is a member of `oneof`_ ``_epoch_count``.
        batch_size (int):
            Immutable. The batch size hyperparameter for
            tuning. If not set, a default of 4 or 16 will be
            used based on the number of training examples.

            This field is a member of `oneof`_ ``_batch_size``.
    """

    learning_rate: float = proto.Field(
        proto.FLOAT,
        number=16,
        oneof="learning_rate_option",
    )
    learning_rate_multiplier: float = proto.Field(
        proto.FLOAT,
        number=17,
        oneof="learning_rate_option",
    )
    epoch_count: int = proto.Field(
        proto.INT32,
        number=14,
        optional=True,
    )
    batch_size: int = proto.Field(
        proto.INT32,
        number=15,
        optional=True,
    )


class Dataset(proto.Message):
    r"""Dataset for training or validation.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        examples (google.ai.generativelanguage_v1beta.types.TuningExamples):
            Optional. Inline examples.

            This field is a member of `oneof`_ ``dataset``.
    """

    examples: "TuningExamples" = proto.Field(
        proto.MESSAGE,
        number=1,
        oneof="dataset",
        message="TuningExamples",
    )


class TuningExamples(proto.Message):
    r"""A set of tuning examples. Can be training or validation data.

    Attributes:
        examples (MutableSequence[google.ai.generativelanguage_v1beta.types.TuningExample]):
            Required. The examples. Example input can be
            for text or discuss, but all examples in a set
            must be of the same type.
    """

    examples: MutableSequence["TuningExample"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="TuningExample",
    )


class TuningExample(proto.Message):
    r"""A single example for tuning.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        text_input (str):
            Optional. Text model input.

            This field is a member of `oneof`_ ``model_input``.
        output (str):
            Required. The expected model output.
    """

    text_input: str = proto.Field(
        proto.STRING,
        number=1,
        oneof="model_input",
    )
    output: str = proto.Field(
        proto.STRING,
        number=3,
    )


class TuningSnapshot(proto.Message):
    r"""Record for a single tuning step.

    Attributes:
        step (int):
            Output only. The tuning step.
        epoch (int):
            Output only. The epoch this step was part of.
        mean_loss (float):
            Output only. The mean loss of the training
            examples for this step.
        compute_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp when this metric
            was computed.
    """

    step: int = proto.Field(
        proto.INT32,
        number=1,
    )
    epoch: int = proto.Field(
        proto.INT32,
        number=2,
    )
    mean_loss: float = proto.Field(
        proto.FLOAT,
        number=3,
    )
    compute_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=4,
        message=timestamp_pb2.Timestamp,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\generative_service\transports\grpc.py ===
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
from typing import Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, grpc_helpers
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
import grpc  # type: ignore

from google.ai.generativelanguage_v1beta.types import generative_service

from .base import DEFAULT_CLIENT_INFO, GenerativeServiceTransport


class GenerativeServiceGrpcTransport(GenerativeServiceTransport):
    """gRPC backend transport for GenerativeService.

    API for using Large Models that generate multimodal content
    and have additional capabilities beyond text generation.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _stubs: Dict[str, Callable]

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]] = None,
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
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if a ``channel`` instance is provided.
            channel (Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]]):
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
          google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
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

        if isinstance(channel, grpc.Channel):
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

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> grpc.Channel:
        """Create and return a gRPC channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            grpc.Channel: A gRPC channel object.

        Raises:
            google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """

        return grpc_helpers.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    @property
    def grpc_channel(self) -> grpc.Channel:
        """Return the channel designed to connect to this service."""
        return self._grpc_channel

    @property
    def generate_content(
        self,
    ) -> Callable[
        [generative_service.GenerateContentRequest],
        generative_service.GenerateContentResponse,
    ]:
        r"""Return a callable for the generate content method over gRPC.

        Generates a response from the model given an input
        ``GenerateContentRequest``.

        Input capabilities differ between models, including tuned
        models. See the `model
        guide <https://ai.google.dev/models/gemini>`__ and `tuning
        guide <https://ai.google.dev/docs/model_tuning_guidance>`__ for
        details.

        Returns:
            Callable[[~.GenerateContentRequest],
                    ~.GenerateContentResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_content" not in self._stubs:
            self._stubs["generate_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.GenerativeService/GenerateContent",
                request_serializer=generative_service.GenerateContentRequest.serialize,
                response_deserializer=generative_service.GenerateContentResponse.deserialize,
            )
        return self._stubs["generate_content"]

    @property
    def generate_answer(
        self,
    ) -> Callable[
        [generative_service.GenerateAnswerRequest],
        generative_service.GenerateAnswerResponse,
    ]:
        r"""Return a callable for the generate answer method over gRPC.

        Generates a grounded answer from the model given an input
        ``GenerateAnswerRequest``.

        Returns:
            Callable[[~.GenerateAnswerRequest],
                    ~.GenerateAnswerResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_answer" not in self._stubs:
            self._stubs["generate_answer"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.GenerativeService/GenerateAnswer",
                request_serializer=generative_service.GenerateAnswerRequest.serialize,
                response_deserializer=generative_service.GenerateAnswerResponse.deserialize,
            )
        return self._stubs["generate_answer"]

    @property
    def stream_generate_content(
        self,
    ) -> Callable[
        [generative_service.GenerateContentRequest],
        generative_service.GenerateContentResponse,
    ]:
        r"""Return a callable for the stream generate content method over gRPC.

        Generates a streamed response from the model given an input
        ``GenerateContentRequest``.

        Returns:
            Callable[[~.GenerateContentRequest],
                    ~.GenerateContentResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "stream_generate_content" not in self._stubs:
            self._stubs["stream_generate_content"] = self.grpc_channel.unary_stream(
                "/google.ai.generativelanguage.v1beta.GenerativeService/StreamGenerateContent",
                request_serializer=generative_service.GenerateContentRequest.serialize,
                response_deserializer=generative_service.GenerateContentResponse.deserialize,
            )
        return self._stubs["stream_generate_content"]

    @property
    def embed_content(
        self,
    ) -> Callable[
        [generative_service.EmbedContentRequest],
        generative_service.EmbedContentResponse,
    ]:
        r"""Return a callable for the embed content method over gRPC.

        Generates an embedding from the model given an input
        ``Content``.

        Returns:
            Callable[[~.EmbedContentRequest],
                    ~.EmbedContentResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "embed_content" not in self._stubs:
            self._stubs["embed_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.GenerativeService/EmbedContent",
                request_serializer=generative_service.EmbedContentRequest.serialize,
                response_deserializer=generative_service.EmbedContentResponse.deserialize,
            )
        return self._stubs["embed_content"]

    @property
    def batch_embed_contents(
        self,
    ) -> Callable[
        [generative_service.BatchEmbedContentsRequest],
        generative_service.BatchEmbedContentsResponse,
    ]:
        r"""Return a callable for the batch embed contents method over gRPC.

        Generates multiple embeddings from the model given
        input text in a synchronous call.

        Returns:
            Callable[[~.BatchEmbedContentsRequest],
                    ~.BatchEmbedContentsResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_embed_contents" not in self._stubs:
            self._stubs["batch_embed_contents"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.GenerativeService/BatchEmbedContents",
                request_serializer=generative_service.BatchEmbedContentsRequest.serialize,
                response_deserializer=generative_service.BatchEmbedContentsResponse.deserialize,
            )
        return self._stubs["batch_embed_contents"]

    @property
    def count_tokens(
        self,
    ) -> Callable[
        [generative_service.CountTokensRequest], generative_service.CountTokensResponse
    ]:
        r"""Return a callable for the count tokens method over gRPC.

        Runs a model's tokenizer on input content and returns
        the token count.

        Returns:
            Callable[[~.CountTokensRequest],
                    ~.CountTokensResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_tokens" not in self._stubs:
            self._stubs["count_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.GenerativeService/CountTokens",
                request_serializer=generative_service.CountTokensRequest.serialize,
                response_deserializer=generative_service.CountTokensResponse.deserialize,
            )
        return self._stubs["count_tokens"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("GenerativeServiceGrpcTransport",)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\shortcuts\progress_bar\formatters.py ===
"""
Formatter classes for the progress bar.
Each progress bar consists of a list of these formatters.
"""

from __future__ import annotations

import datetime
import time
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import (
    HTML,
    AnyFormattedText,
    StyleAndTextTuples,
    to_formatted_text,
)
from prompt_toolkit.formatted_text.utils import fragment_list_width
from prompt_toolkit.layout.dimension import AnyDimension, D
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.utils import get_cwidth

if TYPE_CHECKING:
    from .base import ProgressBar, ProgressBarCounter

__all__ = [
    "Formatter",
    "Text",
    "Label",
    "Percentage",
    "Bar",
    "Progress",
    "TimeElapsed",
    "TimeLeft",
    "IterationsPerSecond",
    "SpinningWheel",
    "Rainbow",
    "create_default_formatters",
]


class Formatter(metaclass=ABCMeta):
    """
    Base class for any formatter.
    """

    @abstractmethod
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText:
        pass

    def get_width(self, progress_bar: ProgressBar) -> AnyDimension:
        return D()


class Text(Formatter):
    """
    Display plain text.
    """

    def __init__(self, text: AnyFormattedText, style: str = "") -> None:
        self.text = to_formatted_text(text, style=style)

    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText:
        return self.text

    def get_width(self, progress_bar: ProgressBar) -> AnyDimension:
        return fragment_list_width(self.text)


class Label(Formatter):
    """
    Display the name of the current task.

    :param width: If a `width` is given, use this width. Scroll the text if it
        doesn't fit in this width.
    :param suffix: String suffix to be added after the task name, e.g. ': '.
        If no task name was given, no suffix will be added.
    """

    def __init__(self, width: AnyDimension = None, suffix: str = "") -> None:
        self.width = width
        self.suffix = suffix

    def _add_suffix(self, label: AnyFormattedText) -> StyleAndTextTuples:
        label = to_formatted_text(label, style="class:label")
        return label + [("", self.suffix)]

    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText:
        label = self._add_suffix(progress.label)
        cwidth = fragment_list_width(label)

        if cwidth > width:
            # It doesn't fit -> scroll task name.
            label = explode_text_fragments(label)
            max_scroll = cwidth - width
            current_scroll = int(time.time() * 3 % max_scroll)
            label = label[current_scroll:]

        return label

    def get_width(self, progress_bar: ProgressBar) -> AnyDimension:
        if self.width:
            return self.width

        all_labels = [self._add_suffix(c.label) for c in progress_bar.counters]
        if all_labels:
            max_widths = max(fragment_list_width(l) for l in all_labels)
            return D(preferred=max_widths, max=max_widths)
        else:
            return D()


class Percentage(Formatter):
    """
    Display the progress as a percentage.
    """

    template = HTML("<percentage>{percentage:>5}%</percentage>")

    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText:
        return self.template.format(percentage=round(progress.percentage, 1))

    def get_width(self, progress_bar: ProgressBar) -> AnyDimension:
        return D.exact(6)


class Bar(Formatter):
    """
    Display the progress bar itself.
    """

    template = HTML(
        "<bar>{start}<bar-a>{bar_a}</bar-a><bar-b>{bar_b}</bar-b><bar-c>{bar_c}</bar-c>{end}</bar>"
    )

    def __init__(
        self,
        start: str = "[",
        end: str = "]",
        sym_a: str = "=",
        sym_b: str = ">",
        sym_c: str = " ",
        unknown: str = "#",
    ) -> None:
        assert len(sym_a) == 1 and get_cwidth(sym_a) == 1
        assert len(sym_c) == 1 and get_cwidth(sym_c) == 1

        self.start = start
        self.end = end
        self.sym_a = sym_a
        self.sym_b = sym_b
        self.sym_c = sym_c
        self.unknown = unknown

    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText:
        if progress.done or progress.total or progress.stopped:
            sym_a, sym_b, sym_c = self.sym_a, self.sym_b, self.sym_c

            # Compute pb_a based on done, total, or stopped states.
            if progress.done:
                # 100% completed irrelevant of how much was actually marked as completed.
                percent = 1.0
            else:
                # Show percentage completed.
                percent = progress.percentage / 100
        else:
            # Total is unknown and bar is still running.
            sym_a, sym_b, sym_c = self.sym_c, self.unknown, self.sym_c

            # Compute percent based on the time.
            percent = time.time() * 20 % 100 / 100

        # Subtract left, sym_b, and right.
        width -= get_cwidth(self.start + sym_b + self.end)

        # Scale percent by width
        pb_a = int(percent * width)
        bar_a = sym_a * pb_a
        bar_b = sym_b
        bar_c = sym_c * (width - pb_a)

        return self.template.format(
            start=self.start, end=self.end, bar_a=bar_a, bar_b=bar_b, bar_c=bar_c
        )

    def get_width(self, progress_bar: ProgressBar) -> AnyDimension:
        return D(min=9)


class Progress(Formatter):
    """
    Display the progress as text.  E.g. "8/20"
    """

    template = HTML("<current>{current:>3}</current>/<total>{total:>3}</total>")

    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText:
        return self.template.format(
            current=progress.items_completed, total=progress.total or "?"
        )

    def get_width(self, progress_bar: ProgressBar) -> AnyDimension:
        all_lengths = [
            len("{:>3}".format(c.total or "?")) for c in progress_bar.counters
        ]
        all_lengths.append(1)
        return D.exact(max(all_lengths) * 2 + 1)


def _format_timedelta(timedelta: datetime.timedelta) -> str:
    """
    Return hh:mm:ss, or mm:ss if the amount of hours is zero.
    """
    result = f"{timedelta}".split(".")[0]
    if result.startswith("0:"):
        result = result[2:]
    return result


class TimeElapsed(Formatter):
    """
    Display the elapsed time.
    """

    template = HTML("<time-elapsed>{time_elapsed}</time-elapsed>")

    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText:
        text = _format_timedelta(progress.time_elapsed).rjust(width)
        return self.template.format(time_elapsed=text)

    def get_width(self, progress_bar: ProgressBar) -> AnyDimension:
        all_values = [
            len(_format_timedelta(c.time_elapsed)) for c in progress_bar.counters
        ]
        if all_values:
            return max(all_values)
        return 0


class TimeLeft(Formatter):
    """
    Display the time left.
    """

    template = HTML("<time-left>{time_left}</time-left>")
    unknown = "?:??:??"

    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText:
        time_left = progress.time_left
        if time_left is not None:
            formatted_time_left = _format_timedelta(time_left)
        else:
            formatted_time_left = self.unknown

        return self.template.format(time_left=formatted_time_left.rjust(width))

    def get_width(self, progress_bar: ProgressBar) -> AnyDimension:
        all_values = [
            len(_format_timedelta(c.time_left)) if c.time_left is not None else 7
            for c in progress_bar.counters
        ]
        if all_values:
            return max(all_values)
        return 0


class IterationsPerSecond(Formatter):
    """
    Display the iterations per second.
    """

    template = HTML(
        "<iterations-per-second>{iterations_per_second:.2f}</iterations-per-second>"
    )

    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText:
        value = progress.items_completed / progress.time_elapsed.total_seconds()
        return self.template.format(iterations_per_second=value)

    def get_width(self, progress_bar: ProgressBar) -> AnyDimension:
        all_values = [
            len(f"{c.items_completed / c.time_elapsed.total_seconds():.2f}")
            for c in progress_bar.counters
        ]
        if all_values:
            return max(all_values)
        return 0


class SpinningWheel(Formatter):
    """
    Display a spinning wheel.
    """

    template = HTML("<spinning-wheel>{0}</spinning-wheel>")
    characters = r"/-\|"

    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText:
        index = int(time.time() * 3) % len(self.characters)
        return self.template.format(self.characters[index])

    def get_width(self, progress_bar: ProgressBar) -> AnyDimension:
        return D.exact(1)


def _hue_to_rgb(hue: float) -> tuple[int, int, int]:
    """
    Take hue between 0 and 1, return (r, g, b).
    """
    i = int(hue * 6.0)
    f = (hue * 6.0) - i

    q = int(255 * (1.0 - f))
    t = int(255 * (1.0 - (1.0 - f)))

    i %= 6

    return [
        (255, t, 0),
        (q, 255, 0),
        (0, 255, t),
        (0, q, 255),
        (t, 0, 255),
        (255, 0, q),
    ][i]


class Rainbow(Formatter):
    """
    For the fun. Add rainbow colors to any of the other formatters.
    """

    colors = ["#%.2x%.2x%.2x" % _hue_to_rgb(h / 100.0) for h in range(0, 100)]

    def __init__(self, formatter: Formatter) -> None:
        self.formatter = formatter

    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText:
        # Get formatted text from nested formatter, and explode it in
        # text/style tuples.
        result = self.formatter.format(progress_bar, progress, width)
        result = explode_text_fragments(to_formatted_text(result))

        # Insert colors.
        result2: StyleAndTextTuples = []
        shift = int(time.time() * 3) % len(self.colors)

        for i, (style, text, *_) in enumerate(result):
            result2.append(
                (style + " " + self.colors[(i + shift) % len(self.colors)], text)
            )
        return result2

    def get_width(self, progress_bar: ProgressBar) -> AnyDimension:
        return self.formatter.get_width(progress_bar)


def create_default_formatters() -> list[Formatter]:
    """
    Return the list of default formatters.
    """
    return [
        Label(),
        Text(" "),
        Percentage(),
        Text(" "),
        Bar(),
        Text(" "),
        Progress(),
        Text(" "),
        Text("eta [", style="class:time-left"),
        TimeLeft(),
        Text("]", style="class:time-left"),
        Text(" "),
    ]

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_utils.py ===
"""Bucket of reusable internal utilities.

This should be reduced as much as possible with functions only used in one place, moved to that place.
"""

from __future__ import annotations as _annotations

import dataclasses
import keyword
import sys
import typing
import warnings
import weakref
from collections import OrderedDict, defaultdict, deque
from collections.abc import Mapping
from copy import deepcopy
from functools import cached_property
from inspect import Parameter
from itertools import zip_longest
from types import BuiltinFunctionType, CodeType, FunctionType, GeneratorType, LambdaType, ModuleType
from typing import Any, Callable, Generic, TypeVar, overload

from typing_extensions import TypeAlias, TypeGuard, deprecated

from pydantic import PydanticDeprecatedSince211

from . import _repr, _typing_extra
from ._import_utils import import_cached_base_model

if typing.TYPE_CHECKING:
    MappingIntStrAny: TypeAlias = 'typing.Mapping[int, Any] | typing.Mapping[str, Any]'
    AbstractSetIntStr: TypeAlias = 'typing.AbstractSet[int] | typing.AbstractSet[str]'
    from ..main import BaseModel


# these are types that are returned unchanged by deepcopy
IMMUTABLE_NON_COLLECTIONS_TYPES: set[type[Any]] = {
    int,
    float,
    complex,
    str,
    bool,
    bytes,
    type,
    _typing_extra.NoneType,
    FunctionType,
    BuiltinFunctionType,
    LambdaType,
    weakref.ref,
    CodeType,
    # note: including ModuleType will differ from behaviour of deepcopy by not producing error.
    # It might be not a good idea in general, but considering that this function used only internally
    # against default values of fields, this will allow to actually have a field with module as default value
    ModuleType,
    NotImplemented.__class__,
    Ellipsis.__class__,
}

# these are types that if empty, might be copied with simple copy() instead of deepcopy()
BUILTIN_COLLECTIONS: set[type[Any]] = {
    list,
    set,
    tuple,
    frozenset,
    dict,
    OrderedDict,
    defaultdict,
    deque,
}


def can_be_positional(param: Parameter) -> bool:
    """Return whether the parameter accepts a positional argument.

    ```python {test="skip" lint="skip"}
    def func(a, /, b, *, c):
        pass

    params = inspect.signature(func).parameters
    can_be_positional(params['a'])
    #> True
    can_be_positional(params['b'])
    #> True
    can_be_positional(params['c'])
    #> False
    ```
    """
    return param.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)


def sequence_like(v: Any) -> bool:
    return isinstance(v, (list, tuple, set, frozenset, GeneratorType, deque))


def lenient_isinstance(o: Any, class_or_tuple: type[Any] | tuple[type[Any], ...] | None) -> bool:  # pragma: no cover
    try:
        return isinstance(o, class_or_tuple)  # type: ignore[arg-type]
    except TypeError:
        return False


def lenient_issubclass(cls: Any, class_or_tuple: Any) -> bool:  # pragma: no cover
    try:
        return isinstance(cls, type) and issubclass(cls, class_or_tuple)
    except TypeError:
        if isinstance(cls, _typing_extra.WithArgsTypes):
            return False
        raise  # pragma: no cover


def is_model_class(cls: Any) -> TypeGuard[type[BaseModel]]:
    """Returns true if cls is a _proper_ subclass of BaseModel, and provides proper type-checking,
    unlike raw calls to lenient_issubclass.
    """
    BaseModel = import_cached_base_model()

    return lenient_issubclass(cls, BaseModel) and cls is not BaseModel


def is_valid_identifier(identifier: str) -> bool:
    """Checks that a string is a valid identifier and not a Python keyword.
    :param identifier: The identifier to test.
    :return: True if the identifier is valid.
    """
    return identifier.isidentifier() and not keyword.iskeyword(identifier)


KeyType = TypeVar('KeyType')


def deep_update(mapping: dict[KeyType, Any], *updating_mappings: dict[KeyType, Any]) -> dict[KeyType, Any]:
    updated_mapping = mapping.copy()
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if k in updated_mapping and isinstance(updated_mapping[k], dict) and isinstance(v, dict):
                updated_mapping[k] = deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping


def update_not_none(mapping: dict[Any, Any], **update: Any) -> None:
    mapping.update({k: v for k, v in update.items() if v is not None})


T = TypeVar('T')


def unique_list(
    input_list: list[T] | tuple[T, ...],
    *,
    name_factory: typing.Callable[[T], str] = str,
) -> list[T]:
    """Make a list unique while maintaining order.
    We update the list if another one with the same name is set
    (e.g. model validator overridden in subclass).
    """
    result: list[T] = []
    result_names: list[str] = []
    for v in input_list:
        v_name = name_factory(v)
        if v_name not in result_names:
            result_names.append(v_name)
            result.append(v)
        else:
            result[result_names.index(v_name)] = v

    return result


class ValueItems(_repr.Representation):
    """Class for more convenient calculation of excluded or included fields on values."""

    __slots__ = ('_items', '_type')

    def __init__(self, value: Any, items: AbstractSetIntStr | MappingIntStrAny) -> None:
        items = self._coerce_items(items)

        if isinstance(value, (list, tuple)):
            items = self._normalize_indexes(items, len(value))  # type: ignore

        self._items: MappingIntStrAny = items  # type: ignore

    def is_excluded(self, item: Any) -> bool:
        """Check if item is fully excluded.

        :param item: key or index of a value
        """
        return self.is_true(self._items.get(item))

    def is_included(self, item: Any) -> bool:
        """Check if value is contained in self._items.

        :param item: key or index of value
        """
        return item in self._items

    def for_element(self, e: int | str) -> AbstractSetIntStr | MappingIntStrAny | None:
        """:param e: key or index of element on value
        :return: raw values for element if self._items is dict and contain needed element
        """
        item = self._items.get(e)  # type: ignore
        return item if not self.is_true(item) else None

    def _normalize_indexes(self, items: MappingIntStrAny, v_length: int) -> dict[int | str, Any]:
        """:param items: dict or set of indexes which will be normalized
        :param v_length: length of sequence indexes of which will be

        >>> self._normalize_indexes({0: True, -2: True, -1: True}, 4)
        {0: True, 2: True, 3: True}
        >>> self._normalize_indexes({'__all__': True}, 4)
        {0: True, 1: True, 2: True, 3: True}
        """
        normalized_items: dict[int | str, Any] = {}
        all_items = None
        for i, v in items.items():
            if not (isinstance(v, typing.Mapping) or isinstance(v, typing.AbstractSet) or self.is_true(v)):
                raise TypeError(f'Unexpected type of exclude value for index "{i}" {v.__class__}')
            if i == '__all__':
                all_items = self._coerce_value(v)
                continue
            if not isinstance(i, int):
                raise TypeError(
                    'Excluding fields from a sequence of sub-models or dicts must be performed index-wise: '
                    'expected integer keys or keyword "__all__"'
                )
            normalized_i = v_length + i if i < 0 else i
            normalized_items[normalized_i] = self.merge(v, normalized_items.get(normalized_i))

        if not all_items:
            return normalized_items
        if self.is_true(all_items):
            for i in range(v_length):
                normalized_items.setdefault(i, ...)
            return normalized_items
        for i in range(v_length):
            normalized_item = normalized_items.setdefault(i, {})
            if not self.is_true(normalized_item):
                normalized_items[i] = self.merge(all_items, normalized_item)
        return normalized_items

    @classmethod
    def merge(cls, base: Any, override: Any, intersect: bool = False) -> Any:
        """Merge a `base` item with an `override` item.

        Both `base` and `override` are converted to dictionaries if possible.
        Sets are converted to dictionaries with the sets entries as keys and
        Ellipsis as values.

        Each key-value pair existing in `base` is merged with `override`,
        while the rest of the key-value pairs are updated recursively with this function.

        Merging takes place based on the "union" of keys if `intersect` is
        set to `False` (default) and on the intersection of keys if
        `intersect` is set to `True`.
        """
        override = cls._coerce_value(override)
        base = cls._coerce_value(base)
        if override is None:
            return base
        if cls.is_true(base) or base is None:
            return override
        if cls.is_true(override):
            return base if intersect else override

        # intersection or union of keys while preserving ordering:
        if intersect:
            merge_keys = [k for k in base if k in override] + [k for k in override if k in base]
        else:
            merge_keys = list(base) + [k for k in override if k not in base]

        merged: dict[int | str, Any] = {}
        for k in merge_keys:
            merged_item = cls.merge(base.get(k), override.get(k), intersect=intersect)
            if merged_item is not None:
                merged[k] = merged_item

        return merged

    @staticmethod
    def _coerce_items(items: AbstractSetIntStr | MappingIntStrAny) -> MappingIntStrAny:
        if isinstance(items, typing.Mapping):
            pass
        elif isinstance(items, typing.AbstractSet):
            items = dict.fromkeys(items, ...)  # type: ignore
        else:
            class_name = getattr(items, '__class__', '???')
            raise TypeError(f'Unexpected type of exclude value {class_name}')
        return items  # type: ignore

    @classmethod
    def _coerce_value(cls, value: Any) -> Any:
        if value is None or cls.is_true(value):
            return value
        return cls._coerce_items(value)

    @staticmethod
    def is_true(v: Any) -> bool:
        return v is True or v is ...

    def __repr_args__(self) -> _repr.ReprArgs:
        return [(None, self._items)]


if typing.TYPE_CHECKING:

    def LazyClassAttribute(name: str, get_value: Callable[[], T]) -> T: ...

else:

    class LazyClassAttribute:
        """A descriptor exposing an attribute only accessible on a class (hidden from instances).

        The attribute is lazily computed and cached during the first access.
        """

        def __init__(self, name: str, get_value: Callable[[], Any]) -> None:
            self.name = name
            self.get_value = get_value

        @cached_property
        def value(self) -> Any:
            return self.get_value()

        def __get__(self, instance: Any, owner: type[Any]) -> None:
            if instance is None:
                return self.value
            raise AttributeError(f'{self.name!r} attribute of {owner.__name__!r} is class-only')


Obj = TypeVar('Obj')


def smart_deepcopy(obj: Obj) -> Obj:
    """Return type as is for immutable built-in types
    Use obj.copy() for built-in empty collections
    Use copy.deepcopy() for non-empty collections and unknown objects.
    """
    obj_type = obj.__class__
    if obj_type in IMMUTABLE_NON_COLLECTIONS_TYPES:
        return obj  # fastest case: obj is immutable and not collection therefore will not be copied anyway
    try:
        if not obj and obj_type in BUILTIN_COLLECTIONS:
            # faster way for empty collections, no need to copy its members
            return obj if obj_type is tuple else obj.copy()  # tuple doesn't have copy method  # type: ignore
    except (TypeError, ValueError, RuntimeError):
        # do we really dare to catch ALL errors? Seems a bit risky
        pass

    return deepcopy(obj)  # slowest way when we actually might need a deepcopy


_SENTINEL = object()


def all_identical(left: typing.Iterable[Any], right: typing.Iterable[Any]) -> bool:
    """Check that the items of `left` are the same objects as those in `right`.

    >>> a, b = object(), object()
    >>> all_identical([a, b, a], [a, b, a])
    True
    >>> all_identical([a, b, [a]], [a, b, [a]])  # new list object, while "equal" is not "identical"
    False
    """
    for left_item, right_item in zip_longest(left, right, fillvalue=_SENTINEL):
        if left_item is not right_item:
            return False
    return True


@dataclasses.dataclass(frozen=True)
class SafeGetItemProxy:
    """Wrapper redirecting `__getitem__` to `get` with a sentinel value as default

    This makes is safe to use in `operator.itemgetter` when some keys may be missing
    """

    # Define __slots__manually for performances
    # @dataclasses.dataclass() only support slots=True in python>=3.10
    __slots__ = ('wrapped',)

    wrapped: Mapping[str, Any]

    def __getitem__(self, key: str, /) -> Any:
        return self.wrapped.get(key, _SENTINEL)

    # required to pass the object to operator.itemgetter() instances due to a quirk of typeshed
    # https://github.com/python/mypy/issues/13713
    # https://github.com/python/typeshed/pull/8785
    # Since this is typing-only, hide it in a typing.TYPE_CHECKING block
    if typing.TYPE_CHECKING:

        def __contains__(self, key: str, /) -> bool:
            return self.wrapped.__contains__(key)


_ModelT = TypeVar('_ModelT', bound='BaseModel')
_RT = TypeVar('_RT')


class deprecated_instance_property(Generic[_ModelT, _RT]):
    """A decorator exposing the decorated class method as a property, with a warning on instance access.

    This decorator takes a class method defined on the `BaseModel` class and transforms it into
    an attribute. The attribute can be accessed on both the class and instances of the class. If accessed
    via an instance, a deprecation warning is emitted stating that instance access will be removed in V3.
    """

    def __init__(self, fget: Callable[[type[_ModelT]], _RT], /) -> None:
        # Note: fget should be a classmethod:
        self.fget = fget

    @overload
    def __get__(self, instance: None, objtype: type[_ModelT]) -> _RT: ...
    @overload
    @deprecated(
        'Accessing this attribute on the instance is deprecated, and will be removed in Pydantic V3. '
        'Instead, you should access this attribute from the model class.',
        category=None,
    )
    def __get__(self, instance: _ModelT, objtype: type[_ModelT]) -> _RT: ...
    def __get__(self, instance: _ModelT | None, objtype: type[_ModelT]) -> _RT:
        if instance is not None:
            attr_name = self.fget.__name__ if sys.version_info >= (3, 10) else self.fget.__func__.__name__
            warnings.warn(
                f'Accessing the {attr_name!r} attribute on the instance is deprecated. '
                'Instead, you should access this attribute from the model class.',
                category=PydanticDeprecatedSince211,
                stacklevel=2,
            )
        return self.fget.__get__(instance, objtype)()

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\filelist.py ===
"""distutils.filelist

Provides the FileList class, used for poking about the filesystem
and building lists of files.
"""

from __future__ import annotations

import fnmatch
import functools
import os
import re
from collections.abc import Iterable
from typing import Literal, overload

from ._log import log
from .errors import DistutilsInternalError, DistutilsTemplateError
from .util import convert_path


class FileList:
    """A list of files built by on exploring the filesystem and filtered by
    applying various patterns to what we find there.

    Instance attributes:
      dir
        directory from which files will be taken -- only used if
        'allfiles' not supplied to constructor
      files
        list of filenames currently being built/filtered/manipulated
      allfiles
        complete list of files under consideration (ie. without any
        filtering applied)
    """

    def __init__(self, warn: object = None, debug_print: object = None) -> None:
        # ignore argument to FileList, but keep them for backwards
        # compatibility
        self.allfiles: Iterable[str] | None = None
        self.files: list[str] = []

    def set_allfiles(self, allfiles: Iterable[str]) -> None:
        self.allfiles = allfiles

    def findall(self, dir: str | os.PathLike[str] = os.curdir) -> None:
        self.allfiles = findall(dir)

    def debug_print(self, msg: object) -> None:
        """Print 'msg' to stdout if the global DEBUG (taken from the
        DISTUTILS_DEBUG environment variable) flag is true.
        """
        from distutils.debug import DEBUG

        if DEBUG:
            print(msg)

    # Collection methods

    def append(self, item: str) -> None:
        self.files.append(item)

    def extend(self, items: Iterable[str]) -> None:
        self.files.extend(items)

    def sort(self) -> None:
        # Not a strict lexical sort!
        sortable_files = sorted(map(os.path.split, self.files))
        self.files = []
        for sort_tuple in sortable_files:
            self.files.append(os.path.join(*sort_tuple))

    # Other miscellaneous utility methods

    def remove_duplicates(self) -> None:
        # Assumes list has been sorted!
        for i in range(len(self.files) - 1, 0, -1):
            if self.files[i] == self.files[i - 1]:
                del self.files[i]

    # "File template" methods

    def _parse_template_line(self, line):
        words = line.split()
        action = words[0]

        patterns = dir = dir_pattern = None

        if action in ('include', 'exclude', 'global-include', 'global-exclude'):
            if len(words) < 2:
                raise DistutilsTemplateError(
                    f"'{action}' expects <pattern1> <pattern2> ..."
                )
            patterns = [convert_path(w) for w in words[1:]]
        elif action in ('recursive-include', 'recursive-exclude'):
            if len(words) < 3:
                raise DistutilsTemplateError(
                    f"'{action}' expects <dir> <pattern1> <pattern2> ..."
                )
            dir = convert_path(words[1])
            patterns = [convert_path(w) for w in words[2:]]
        elif action in ('graft', 'prune'):
            if len(words) != 2:
                raise DistutilsTemplateError(
                    f"'{action}' expects a single <dir_pattern>"
                )
            dir_pattern = convert_path(words[1])
        else:
            raise DistutilsTemplateError(f"unknown action '{action}'")

        return (action, patterns, dir, dir_pattern)

    def process_template_line(self, line: str) -> None:  # noqa: C901
        # Parse the line: split it up, make sure the right number of words
        # is there, and return the relevant words.  'action' is always
        # defined: it's the first word of the line.  Which of the other
        # three are defined depends on the action; it'll be either
        # patterns, (dir and patterns), or (dir_pattern).
        (action, patterns, dir, dir_pattern) = self._parse_template_line(line)

        # OK, now we know that the action is valid and we have the
        # right number of words on the line for that action -- so we
        # can proceed with minimal error-checking.
        if action == 'include':
            self.debug_print("include " + ' '.join(patterns))
            for pattern in patterns:
                if not self.include_pattern(pattern, anchor=True):
                    log.warning("warning: no files found matching '%s'", pattern)

        elif action == 'exclude':
            self.debug_print("exclude " + ' '.join(patterns))
            for pattern in patterns:
                if not self.exclude_pattern(pattern, anchor=True):
                    log.warning(
                        "warning: no previously-included files found matching '%s'",
                        pattern,
                    )

        elif action == 'global-include':
            self.debug_print("global-include " + ' '.join(patterns))
            for pattern in patterns:
                if not self.include_pattern(pattern, anchor=False):
                    log.warning(
                        (
                            "warning: no files found matching '%s' "
                            "anywhere in distribution"
                        ),
                        pattern,
                    )

        elif action == 'global-exclude':
            self.debug_print("global-exclude " + ' '.join(patterns))
            for pattern in patterns:
                if not self.exclude_pattern(pattern, anchor=False):
                    log.warning(
                        (
                            "warning: no previously-included files matching "
                            "'%s' found anywhere in distribution"
                        ),
                        pattern,
                    )

        elif action == 'recursive-include':
            self.debug_print("recursive-include {} {}".format(dir, ' '.join(patterns)))
            for pattern in patterns:
                if not self.include_pattern(pattern, prefix=dir):
                    msg = "warning: no files found matching '%s' under directory '%s'"
                    log.warning(msg, pattern, dir)

        elif action == 'recursive-exclude':
            self.debug_print("recursive-exclude {} {}".format(dir, ' '.join(patterns)))
            for pattern in patterns:
                if not self.exclude_pattern(pattern, prefix=dir):
                    log.warning(
                        (
                            "warning: no previously-included files matching "
                            "'%s' found under directory '%s'"
                        ),
                        pattern,
                        dir,
                    )

        elif action == 'graft':
            self.debug_print("graft " + dir_pattern)
            if not self.include_pattern(None, prefix=dir_pattern):
                log.warning("warning: no directories found matching '%s'", dir_pattern)

        elif action == 'prune':
            self.debug_print("prune " + dir_pattern)
            if not self.exclude_pattern(None, prefix=dir_pattern):
                log.warning(
                    ("no previously-included directories found matching '%s'"),
                    dir_pattern,
                )
        else:
            raise DistutilsInternalError(
                f"this cannot happen: invalid action '{action}'"
            )

    # Filtering/selection methods
    @overload
    def include_pattern(
        self,
        pattern: str,
        anchor: bool = True,
        prefix: str | None = None,
        is_regex: Literal[False] = False,
    ) -> bool: ...
    @overload
    def include_pattern(
        self,
        pattern: str | re.Pattern[str],
        anchor: bool = True,
        prefix: str | None = None,
        *,
        is_regex: Literal[True],
    ) -> bool: ...
    @overload
    def include_pattern(
        self,
        pattern: str | re.Pattern[str],
        anchor: bool,
        prefix: str | None,
        is_regex: Literal[True],
    ) -> bool: ...
    def include_pattern(
        self,
        pattern: str | re.Pattern,
        anchor: bool = True,
        prefix: str | None = None,
        is_regex: bool = False,
    ) -> bool:
        """Select strings (presumably filenames) from 'self.files' that
        match 'pattern', a Unix-style wildcard (glob) pattern.  Patterns
        are not quite the same as implemented by the 'fnmatch' module: '*'
        and '?'  match non-special characters, where "special" is platform-
        dependent: slash on Unix; colon, slash, and backslash on
        DOS/Windows; and colon on Mac OS.

        If 'anchor' is true (the default), then the pattern match is more
        stringent: "*.py" will match "foo.py" but not "foo/bar.py".  If
        'anchor' is false, both of these will match.

        If 'prefix' is supplied, then only filenames starting with 'prefix'
        (itself a pattern) and ending with 'pattern', with anything in between
        them, will match.  'anchor' is ignored in this case.

        If 'is_regex' is true, 'anchor' and 'prefix' are ignored, and
        'pattern' is assumed to be either a string containing a regex or a
        regex object -- no translation is done, the regex is just compiled
        and used as-is.

        Selected strings will be added to self.files.

        Return True if files are found, False otherwise.
        """
        # XXX docstring lying about what the special chars are?
        files_found = False
        pattern_re = translate_pattern(pattern, anchor, prefix, is_regex)
        self.debug_print(f"include_pattern: applying regex r'{pattern_re.pattern}'")

        # delayed loading of allfiles list
        if self.allfiles is None:
            self.findall()

        for name in self.allfiles:
            if pattern_re.search(name):
                self.debug_print(" adding " + name)
                self.files.append(name)
                files_found = True
        return files_found

    @overload
    def exclude_pattern(
        self,
        pattern: str,
        anchor: bool = True,
        prefix: str | None = None,
        is_regex: Literal[False] = False,
    ) -> bool: ...
    @overload
    def exclude_pattern(
        self,
        pattern: str | re.Pattern[str],
        anchor: bool = True,
        prefix: str | None = None,
        *,
        is_regex: Literal[True],
    ) -> bool: ...
    @overload
    def exclude_pattern(
        self,
        pattern: str | re.Pattern[str],
        anchor: bool,
        prefix: str | None,
        is_regex: Literal[True],
    ) -> bool: ...
    def exclude_pattern(
        self,
        pattern: str | re.Pattern,
        anchor: bool = True,
        prefix: str | None = None,
        is_regex: bool = False,
    ) -> bool:
        """Remove strings (presumably filenames) from 'files' that match
        'pattern'.  Other parameters are the same as for
        'include_pattern()', above.
        The list 'self.files' is modified in place.
        Return True if files are found, False otherwise.
        """
        files_found = False
        pattern_re = translate_pattern(pattern, anchor, prefix, is_regex)
        self.debug_print(f"exclude_pattern: applying regex r'{pattern_re.pattern}'")
        for i in range(len(self.files) - 1, -1, -1):
            if pattern_re.search(self.files[i]):
                self.debug_print(" removing " + self.files[i])
                del self.files[i]
                files_found = True
        return files_found


# Utility functions


def _find_all_simple(path):
    """
    Find all files under 'path'
    """
    all_unique = _UniqueDirs.filter(os.walk(path, followlinks=True))
    results = (
        os.path.join(base, file) for base, dirs, files in all_unique for file in files
    )
    return filter(os.path.isfile, results)


class _UniqueDirs(set):
    """
    Exclude previously-seen dirs from walk results,
    avoiding infinite recursion.
    Ref https://bugs.python.org/issue44497.
    """

    def __call__(self, walk_item):
        """
        Given an item from an os.walk result, determine
        if the item represents a unique dir for this instance
        and if not, prevent further traversal.
        """
        base, dirs, files = walk_item
        stat = os.stat(base)
        candidate = stat.st_dev, stat.st_ino
        found = candidate in self
        if found:
            del dirs[:]
        self.add(candidate)
        return not found

    @classmethod
    def filter(cls, items):
        return filter(cls(), items)


def findall(dir: str | os.PathLike[str] = os.curdir):
    """
    Find all files under 'dir' and return the list of full filenames.
    Unless dir is '.', return full filenames with dir prepended.
    """
    files = _find_all_simple(dir)
    if dir == os.curdir:
        make_rel = functools.partial(os.path.relpath, start=dir)
        files = map(make_rel, files)
    return list(files)


def glob_to_re(pattern):
    """Translate a shell-like glob pattern to a regular expression; return
    a string containing the regex.  Differs from 'fnmatch.translate()' in
    that '*' does not match "special characters" (which are
    platform-specific).
    """
    pattern_re = fnmatch.translate(pattern)

    # '?' and '*' in the glob pattern become '.' and '.*' in the RE, which
    # IMHO is wrong -- '?' and '*' aren't supposed to match slash in Unix,
    # and by extension they shouldn't match such "special characters" under
    # any OS.  So change all non-escaped dots in the RE to match any
    # character except the special characters (currently: just os.sep).
    sep = os.sep
    if os.sep == '\\':
        # we're using a regex to manipulate a regex, so we need
        # to escape the backslash twice
        sep = r'\\\\'
    escaped = rf'\1[^{sep}]'
    pattern_re = re.sub(r'((?<!\\)(\\\\)*)\.', escaped, pattern_re)
    return pattern_re


def translate_pattern(pattern, anchor=True, prefix=None, is_regex=False):
    """Translate a shell-like wildcard pattern to a compiled regular
    expression.  Return the compiled regex.  If 'is_regex' true,
    then 'pattern' is directly compiled to a regex (if it's a string)
    or just returned as-is (assumes it's a regex object).
    """
    if is_regex:
        if isinstance(pattern, str):
            return re.compile(pattern)
        else:
            return pattern

    # ditch start and end characters
    start, _, end = glob_to_re('_').partition('_')

    if pattern:
        pattern_re = glob_to_re(pattern)
        assert pattern_re.startswith(start) and pattern_re.endswith(end)
    else:
        pattern_re = ''

    if prefix is not None:
        prefix_re = glob_to_re(prefix)
        assert prefix_re.startswith(start) and prefix_re.endswith(end)
        prefix_re = prefix_re[len(start) : len(prefix_re) - len(end)]
        sep = os.sep
        if os.sep == '\\':
            sep = r'\\'
        pattern_re = pattern_re[len(start) : len(pattern_re) - len(end)]
        pattern_re = rf'{start}\A{prefix_re}{sep}.*{pattern_re}{end}'
    else:  # no prefix -- respect anchor flag
        if anchor:
            pattern_re = rf'{start}\A{pattern_re[len(start) :]}'

    return re.compile(pattern_re)

# === NexusCore/openenv\Lib\site-packages\tornado\test\queues_test.py ===
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

import asyncio
from datetime import timedelta
from random import random
import unittest

from tornado import gen, queues
from tornado.gen import TimeoutError
from tornado.testing import gen_test, AsyncTestCase


class QueueBasicTest(AsyncTestCase):
    def test_repr_and_str(self):
        q = queues.Queue(maxsize=1)  # type: queues.Queue[None]
        self.assertIn(hex(id(q)), repr(q))
        self.assertNotIn(hex(id(q)), str(q))
        q.get()

        for q_str in repr(q), str(q):
            self.assertTrue(q_str.startswith("<Queue"))
            self.assertIn("maxsize=1", q_str)
            self.assertIn("getters[1]", q_str)
            self.assertNotIn("putters", q_str)
            self.assertNotIn("tasks", q_str)

        q.put(None)
        q.put(None)
        # Now the queue is full, this putter blocks.
        q.put(None)

        for q_str in repr(q), str(q):
            self.assertNotIn("getters", q_str)
            self.assertIn("putters[1]", q_str)
            self.assertIn("tasks=2", q_str)

    def test_order(self):
        q = queues.Queue()  # type: queues.Queue[int]
        for i in [1, 3, 2]:
            q.put_nowait(i)

        items = [q.get_nowait() for _ in range(3)]
        self.assertEqual([1, 3, 2], items)

    @gen_test
    def test_maxsize(self):
        self.assertRaises(TypeError, queues.Queue, maxsize=None)
        self.assertRaises(ValueError, queues.Queue, maxsize=-1)

        q = queues.Queue(maxsize=2)  # type: queues.Queue[int]
        self.assertTrue(q.empty())
        self.assertFalse(q.full())
        self.assertEqual(2, q.maxsize)
        self.assertTrue(q.put(0).done())
        self.assertTrue(q.put(1).done())
        self.assertFalse(q.empty())
        self.assertTrue(q.full())
        put2 = q.put(2)
        self.assertFalse(put2.done())
        self.assertEqual(0, (yield q.get()))  # Make room.
        self.assertTrue(put2.done())
        self.assertFalse(q.empty())
        self.assertTrue(q.full())


class QueueGetTest(AsyncTestCase):
    @gen_test
    def test_blocking_get(self):
        q = queues.Queue()  # type: queues.Queue[int]
        q.put_nowait(0)
        self.assertEqual(0, (yield q.get()))

    def test_nonblocking_get(self):
        q = queues.Queue()  # type: queues.Queue[int]
        q.put_nowait(0)
        self.assertEqual(0, q.get_nowait())

    def test_nonblocking_get_exception(self):
        q = queues.Queue()  # type: queues.Queue[int]
        self.assertRaises(queues.QueueEmpty, q.get_nowait)

    @gen_test
    def test_get_with_putters(self):
        q = queues.Queue(1)  # type: queues.Queue[int]
        q.put_nowait(0)
        put = q.put(1)
        self.assertEqual(0, (yield q.get()))
        self.assertIsNone((yield put))

    @gen_test
    def test_blocking_get_wait(self):
        q = queues.Queue()  # type: queues.Queue[int]
        q.put(0)
        self.io_loop.call_later(0.01, q.put_nowait, 1)
        self.io_loop.call_later(0.02, q.put_nowait, 2)
        self.assertEqual(0, (yield q.get(timeout=timedelta(seconds=1))))
        self.assertEqual(1, (yield q.get(timeout=timedelta(seconds=1))))

    @gen_test
    def test_get_timeout(self):
        q = queues.Queue()  # type: queues.Queue[int]
        get_timeout = q.get(timeout=timedelta(seconds=0.01))
        get = q.get()
        with self.assertRaises(TimeoutError):
            yield get_timeout

        q.put_nowait(0)
        self.assertEqual(0, (yield get))

    @gen_test
    def test_get_timeout_preempted(self):
        q = queues.Queue()  # type: queues.Queue[int]
        get = q.get(timeout=timedelta(seconds=0.01))
        q.put(0)
        yield gen.sleep(0.02)
        self.assertEqual(0, (yield get))

    @gen_test
    def test_get_clears_timed_out_putters(self):
        q = queues.Queue(1)  # type: queues.Queue[int]
        # First putter succeeds, remainder block.
        putters = [q.put(i, timedelta(seconds=0.01)) for i in range(10)]
        put = q.put(10)
        self.assertEqual(10, len(q._putters))
        yield gen.sleep(0.02)
        self.assertEqual(10, len(q._putters))
        self.assertFalse(put.done())  # Final waiter is still active.
        q.put(11)
        self.assertEqual(0, (yield q.get()))  # get() clears the waiters.
        self.assertEqual(1, len(q._putters))
        for putter in putters[1:]:
            self.assertRaises(TimeoutError, putter.result)

    @gen_test
    def test_get_clears_timed_out_getters(self):
        q = queues.Queue()  # type: queues.Queue[int]
        getters = [
            asyncio.ensure_future(q.get(timedelta(seconds=0.01))) for _ in range(10)
        ]
        get = asyncio.ensure_future(q.get())
        self.assertEqual(11, len(q._getters))
        yield gen.sleep(0.02)
        self.assertEqual(11, len(q._getters))
        self.assertFalse(get.done())  # Final waiter is still active.
        q.get()  # get() clears the waiters.
        self.assertEqual(2, len(q._getters))
        for getter in getters:
            self.assertRaises(TimeoutError, getter.result)

    @gen_test
    def test_async_for(self):
        q = queues.Queue()  # type: queues.Queue[int]
        for i in range(5):
            q.put(i)

        async def f():
            results = []
            async for i in q:
                results.append(i)
                if i == 4:
                    return results

        results = yield f()
        self.assertEqual(results, list(range(5)))


class QueuePutTest(AsyncTestCase):
    @gen_test
    def test_blocking_put(self):
        q = queues.Queue()  # type: queues.Queue[int]
        q.put(0)
        self.assertEqual(0, q.get_nowait())

    def test_nonblocking_put_exception(self):
        q = queues.Queue(1)  # type: queues.Queue[int]
        q.put(0)
        self.assertRaises(queues.QueueFull, q.put_nowait, 1)

    @gen_test
    def test_put_with_getters(self):
        q = queues.Queue()  # type: queues.Queue[int]
        get0 = q.get()
        get1 = q.get()
        yield q.put(0)
        self.assertEqual(0, (yield get0))
        yield q.put(1)
        self.assertEqual(1, (yield get1))

    @gen_test
    def test_nonblocking_put_with_getters(self):
        q = queues.Queue()  # type: queues.Queue[int]
        get0 = q.get()
        get1 = q.get()
        q.put_nowait(0)
        # put_nowait does *not* immediately unblock getters.
        yield gen.moment
        self.assertEqual(0, (yield get0))
        q.put_nowait(1)
        yield gen.moment
        self.assertEqual(1, (yield get1))

    @gen_test
    def test_blocking_put_wait(self):
        q = queues.Queue(1)  # type: queues.Queue[int]
        q.put_nowait(0)

        def get_and_discard():
            q.get()

        self.io_loop.call_later(0.01, get_and_discard)
        self.io_loop.call_later(0.02, get_and_discard)
        futures = [q.put(0), q.put(1)]
        self.assertFalse(any(f.done() for f in futures))
        yield futures

    @gen_test
    def test_put_timeout(self):
        q = queues.Queue(1)  # type: queues.Queue[int]
        q.put_nowait(0)  # Now it's full.
        put_timeout = q.put(1, timeout=timedelta(seconds=0.01))
        put = q.put(2)
        with self.assertRaises(TimeoutError):
            yield put_timeout

        self.assertEqual(0, q.get_nowait())
        # 1 was never put in the queue.
        self.assertEqual(2, (yield q.get()))

        # Final get() unblocked this putter.
        yield put

    @gen_test
    def test_put_timeout_preempted(self):
        q = queues.Queue(1)  # type: queues.Queue[int]
        q.put_nowait(0)
        put = q.put(1, timeout=timedelta(seconds=0.01))
        q.get()
        yield gen.sleep(0.02)
        yield put  # No TimeoutError.

    @gen_test
    def test_put_clears_timed_out_putters(self):
        q = queues.Queue(1)  # type: queues.Queue[int]
        # First putter succeeds, remainder block.
        putters = [q.put(i, timedelta(seconds=0.01)) for i in range(10)]
        put = q.put(10)
        self.assertEqual(10, len(q._putters))
        yield gen.sleep(0.02)
        self.assertEqual(10, len(q._putters))
        self.assertFalse(put.done())  # Final waiter is still active.
        q.put(11)  # put() clears the waiters.
        self.assertEqual(2, len(q._putters))
        for putter in putters[1:]:
            self.assertRaises(TimeoutError, putter.result)

    @gen_test
    def test_put_clears_timed_out_getters(self):
        q = queues.Queue()  # type: queues.Queue[int]
        getters = [
            asyncio.ensure_future(q.get(timedelta(seconds=0.01))) for _ in range(10)
        ]
        get = asyncio.ensure_future(q.get())
        q.get()
        self.assertEqual(12, len(q._getters))
        yield gen.sleep(0.02)
        self.assertEqual(12, len(q._getters))
        self.assertFalse(get.done())  # Final waiters still active.
        q.put(0)  # put() clears the waiters.
        self.assertEqual(1, len(q._getters))
        self.assertEqual(0, (yield get))
        for getter in getters:
            self.assertRaises(TimeoutError, getter.result)

    @gen_test
    def test_float_maxsize(self):
        # If a float is passed for maxsize, a reasonable limit should
        # be enforced, instead of being treated as unlimited.
        # It happens to be rounded up.
        # http://bugs.python.org/issue21723
        q = queues.Queue(maxsize=1.3)  # type: ignore
        self.assertTrue(q.empty())
        self.assertFalse(q.full())
        q.put_nowait(0)
        q.put_nowait(1)
        self.assertFalse(q.empty())
        self.assertTrue(q.full())
        self.assertRaises(queues.QueueFull, q.put_nowait, 2)
        self.assertEqual(0, q.get_nowait())
        self.assertFalse(q.empty())
        self.assertFalse(q.full())

        yield q.put(2)
        put = q.put(3)
        self.assertFalse(put.done())
        self.assertEqual(1, (yield q.get()))
        yield put
        self.assertTrue(q.full())


class QueueJoinTest(AsyncTestCase):
    queue_class = queues.Queue

    def test_task_done_underflow(self):
        q = self.queue_class()  # type: queues.Queue
        self.assertRaises(ValueError, q.task_done)

    @gen_test
    def test_task_done(self):
        q = self.queue_class()  # type: queues.Queue
        for i in range(100):
            q.put_nowait(i)

        self.accumulator = 0

        @gen.coroutine
        def worker():
            while True:
                item = yield q.get()
                self.accumulator += item
                q.task_done()
                yield gen.sleep(random() * 0.01)

        # Two coroutines share work.
        worker()
        worker()
        yield q.join()
        self.assertEqual(sum(range(100)), self.accumulator)

    @gen_test
    def test_task_done_delay(self):
        # Verify it is task_done(), not get(), that unblocks join().
        q = self.queue_class()  # type: queues.Queue
        q.put_nowait(0)
        join = asyncio.ensure_future(q.join())
        self.assertFalse(join.done())
        yield q.get()
        self.assertFalse(join.done())
        yield gen.moment
        self.assertFalse(join.done())
        q.task_done()
        self.assertTrue(join.done())

    @gen_test
    def test_join_empty_queue(self):
        q = self.queue_class()  # type: queues.Queue
        yield q.join()
        yield q.join()

    @gen_test
    def test_join_timeout(self):
        q = self.queue_class()  # type: queues.Queue
        q.put(0)
        with self.assertRaises(TimeoutError):
            yield q.join(timeout=timedelta(seconds=0.01))


class PriorityQueueJoinTest(QueueJoinTest):
    queue_class = queues.PriorityQueue

    @gen_test
    def test_order(self):
        q = self.queue_class(maxsize=2)
        q.put_nowait((1, "a"))
        q.put_nowait((0, "b"))
        self.assertTrue(q.full())
        q.put((3, "c"))
        q.put((2, "d"))
        self.assertEqual((0, "b"), q.get_nowait())
        self.assertEqual((1, "a"), (yield q.get()))
        self.assertEqual((2, "d"), q.get_nowait())
        self.assertEqual((3, "c"), (yield q.get()))
        self.assertTrue(q.empty())


class LifoQueueJoinTest(QueueJoinTest):
    queue_class = queues.LifoQueue

    @gen_test
    def test_order(self):
        q = self.queue_class(maxsize=2)
        q.put_nowait(1)
        q.put_nowait(0)
        self.assertTrue(q.full())
        q.put(3)
        q.put(2)
        self.assertEqual(3, q.get_nowait())
        self.assertEqual(2, (yield q.get()))
        self.assertEqual(0, q.get_nowait())
        self.assertEqual(1, (yield q.get()))
        self.assertTrue(q.empty())


class ProducerConsumerTest(AsyncTestCase):
    @gen_test
    def test_producer_consumer(self):
        q = queues.Queue(maxsize=3)  # type: queues.Queue[int]
        history = []

        # We don't yield between get() and task_done(), so get() must wait for
        # the next tick. Otherwise we'd immediately call task_done and unblock
        # join() before q.put() resumes, and we'd only process the first four
        # items.
        @gen.coroutine
        def consumer():
            while True:
                history.append((yield q.get()))
                q.task_done()

        @gen.coroutine
        def producer():
            for item in range(10):
                yield q.put(item)

        consumer()
        yield producer()
        yield q.join()
        self.assertEqual(list(range(10)), history)


if __name__ == "__main__":
    unittest.main()