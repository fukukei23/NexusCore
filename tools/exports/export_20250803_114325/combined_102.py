
# === NexusCore/openenv\Lib\site-packages\pyparsing\helpers.py ===
# helpers.py
import html.entities
import operator
import re
import sys
import typing

from . import __diag__
from .core import *
from .util import (
    _bslash,
    _flatten,
    _escape_regex_range_chars,
    make_compressed_re,
    replaced_by_pep8,
)


#
# global helpers
#
def counted_array(
    expr: ParserElement,
    int_expr: typing.Optional[ParserElement] = None,
    *,
    intExpr: typing.Optional[ParserElement] = None,
) -> ParserElement:
    """Helper to define a counted list of expressions.

    This helper defines a pattern of the form::

        integer expr expr expr...

    where the leading integer tells how many expr expressions follow.
    The matched tokens returns the array of expr tokens as a list - the
    leading count token is suppressed.

    If ``int_expr`` is specified, it should be a pyparsing expression
    that produces an integer value.

    Example::

        counted_array(Word(alphas)).parse_string('2 ab cd ef')  # -> ['ab', 'cd']

        # in this parser, the leading integer value is given in binary,
        # '10' indicating that 2 values are in the array
        binary_constant = Word('01').set_parse_action(lambda t: int(t[0], 2))
        counted_array(Word(alphas), int_expr=binary_constant).parse_string('10 ab cd ef')  # -> ['ab', 'cd']

        # if other fields must be parsed after the count but before the
        # list items, give the fields results names and they will
        # be preserved in the returned ParseResults:
        count_with_metadata = integer + Word(alphas)("type")
        typed_array = counted_array(Word(alphanums), int_expr=count_with_metadata)("items")
        result = typed_array.parse_string("3 bool True True False")
        print(result.dump())

        # prints
        # ['True', 'True', 'False']
        # - items: ['True', 'True', 'False']
        # - type: 'bool'
    """
    intExpr = intExpr or int_expr
    array_expr = Forward()

    def count_field_parse_action(s, l, t):
        nonlocal array_expr
        n = t[0]
        array_expr <<= (expr * n) if n else Empty()
        # clear list contents, but keep any named results
        del t[:]

    if intExpr is None:
        intExpr = Word(nums).set_parse_action(lambda t: int(t[0]))
    else:
        intExpr = intExpr.copy()
    intExpr.set_name("arrayLen")
    intExpr.add_parse_action(count_field_parse_action, call_during_try=True)
    return (intExpr + array_expr).set_name(f"(len) {expr}...")


def match_previous_literal(expr: ParserElement) -> ParserElement:
    """Helper to define an expression that is indirectly defined from
    the tokens matched in a previous expression, that is, it looks for
    a 'repeat' of a previous expression.  For example::

        first = Word(nums)
        second = match_previous_literal(first)
        match_expr = first + ":" + second

    will match ``"1:1"``, but not ``"1:2"``.  Because this
    matches a previous literal, will also match the leading
    ``"1:1"`` in ``"1:10"``. If this is not desired, use
    :class:`match_previous_expr`. Do *not* use with packrat parsing
    enabled.
    """
    rep = Forward()

    def copy_token_to_repeater(s, l, t):
        if not t:
            rep << Empty()
            return

        if len(t) == 1:
            rep << t[0]
            return

        # flatten t tokens
        tflat = _flatten(t.as_list())
        rep << And(Literal(tt) for tt in tflat)

    expr.add_parse_action(copy_token_to_repeater, callDuringTry=True)
    rep.set_name("(prev) " + str(expr))
    return rep


def match_previous_expr(expr: ParserElement) -> ParserElement:
    """Helper to define an expression that is indirectly defined from
    the tokens matched in a previous expression, that is, it looks for
    a 'repeat' of a previous expression.  For example::

        first = Word(nums)
        second = match_previous_expr(first)
        match_expr = first + ":" + second

    will match ``"1:1"``, but not ``"1:2"``.  Because this
    matches by expressions, will *not* match the leading ``"1:1"``
    in ``"1:10"``; the expressions are evaluated first, and then
    compared, so ``"1"`` is compared with ``"10"``. Do *not* use
    with packrat parsing enabled.
    """
    rep = Forward()
    e2 = expr.copy()
    rep <<= e2

    def copy_token_to_repeater(s, l, t):
        matchTokens = _flatten(t.as_list())

        def must_match_these_tokens(s, l, t):
            theseTokens = _flatten(t.as_list())
            if theseTokens != matchTokens:
                raise ParseException(
                    s, l, f"Expected {matchTokens}, found{theseTokens}"
                )

        rep.set_parse_action(must_match_these_tokens, callDuringTry=True)

    expr.add_parse_action(copy_token_to_repeater, callDuringTry=True)
    rep.set_name("(prev) " + str(expr))
    return rep


def one_of(
    strs: Union[typing.Iterable[str], str],
    caseless: bool = False,
    use_regex: bool = True,
    as_keyword: bool = False,
    *,
    useRegex: bool = True,
    asKeyword: bool = False,
) -> ParserElement:
    """Helper to quickly define a set of alternative :class:`Literal` s,
    and makes sure to do longest-first testing when there is a conflict,
    regardless of the input order, but returns
    a :class:`MatchFirst` for best performance.

    Parameters:

    - ``strs`` - a string of space-delimited literals, or a collection of
      string literals
    - ``caseless`` - treat all literals as caseless - (default= ``False``)
    - ``use_regex`` - as an optimization, will
      generate a :class:`Regex` object; otherwise, will generate
      a :class:`MatchFirst` object (if ``caseless=True`` or ``as_keyword=True``, or if
      creating a :class:`Regex` raises an exception) - (default= ``True``)
    - ``as_keyword`` - enforce :class:`Keyword`-style matching on the
      generated expressions - (default= ``False``)
    - ``asKeyword`` and ``useRegex`` are retained for pre-PEP8 compatibility,
      but will be removed in a future release

    Example::

        comp_oper = one_of("< = > <= >= !=")
        var = Word(alphas)
        number = Word(nums)
        term = var | number
        comparison_expr = term + comp_oper + term
        print(comparison_expr.search_string("B = 12  AA=23 B<=AA AA>12"))

    prints::

        [['B', '=', '12'], ['AA', '=', '23'], ['B', '<=', 'AA'], ['AA', '>', '12']]
    """
    asKeyword = asKeyword or as_keyword
    useRegex = useRegex and use_regex

    if (
        isinstance(caseless, str_type)
        and __diag__.warn_on_multiple_string_args_to_oneof
    ):
        warnings.warn(
            "warn_on_multiple_string_args_to_oneof:"
            " More than one string argument passed to one_of, pass"
            " choices as a list or space-delimited string",
            stacklevel=2,
        )

    if caseless:
        is_equal = lambda a, b: a.upper() == b.upper()
        masks = lambda a, b: b.upper().startswith(a.upper())
    else:
        is_equal = operator.eq
        masks = lambda a, b: b.startswith(a)

    symbols: list[str]
    if isinstance(strs, str_type):
        strs = typing.cast(str, strs)
        symbols = strs.split()
    elif isinstance(strs, Iterable):
        symbols = list(strs)
    else:
        raise TypeError("Invalid argument to one_of, expected string or iterable")
    if not symbols:
        return NoMatch()

    # reorder given symbols to take care to avoid masking longer choices with shorter ones
    # (but only if the given symbols are not just single characters)
    i = 0
    while i < len(symbols) - 1:
        cur = symbols[i]
        for j, other in enumerate(symbols[i + 1 :]):
            if is_equal(other, cur):
                del symbols[i + j + 1]
                break
            if len(other) > len(cur) and masks(cur, other):
                del symbols[i + j + 1]
                symbols.insert(i, other)
                break
        else:
            i += 1

    if useRegex:
        re_flags: int = re.IGNORECASE if caseless else 0

        try:
            if all(len(sym) == 1 for sym in symbols):
                # symbols are just single characters, create range regex pattern
                patt = f"[{''.join(_escape_regex_range_chars(sym) for sym in symbols)}]"
            else:
                patt = "|".join(re.escape(sym) for sym in symbols)

            # wrap with \b word break markers if defining as keywords
            if asKeyword:
                patt = rf"\b(?:{patt})\b"

            ret = Regex(patt, flags=re_flags)
            ret.set_name(" | ".join(re.escape(s) for s in symbols))

            if caseless:
                # add parse action to return symbols as specified, not in random
                # casing as found in input string
                symbol_map = {sym.lower(): sym for sym in symbols}
                ret.add_parse_action(lambda s, l, t: symbol_map[t[0].lower()])

            return ret

        except re.error:
            warnings.warn(
                "Exception creating Regex for one_of, building MatchFirst", stacklevel=2
            )

    # last resort, just use MatchFirst of Token class corresponding to caseless
    # and asKeyword settings
    CASELESS = KEYWORD = True
    parse_element_class = {
        (CASELESS, KEYWORD): CaselessKeyword,
        (CASELESS, not KEYWORD): CaselessLiteral,
        (not CASELESS, KEYWORD): Keyword,
        (not CASELESS, not KEYWORD): Literal,
    }[(caseless, asKeyword)]
    return MatchFirst(parse_element_class(sym) for sym in symbols).set_name(
        " | ".join(symbols)
    )


def dict_of(key: ParserElement, value: ParserElement) -> Dict:
    """Helper to easily and clearly define a dictionary by specifying
    the respective patterns for the key and value.  Takes care of
    defining the :class:`Dict`, :class:`ZeroOrMore`, and
    :class:`Group` tokens in the proper order.  The key pattern
    can include delimiting markers or punctuation, as long as they are
    suppressed, thereby leaving the significant key text.  The value
    pattern can include named results, so that the :class:`Dict` results
    can include named token fields.

    Example::

        text = "shape: SQUARE posn: upper left color: light blue texture: burlap"
        attr_expr = (label + Suppress(':') + OneOrMore(data_word, stop_on=label).set_parse_action(' '.join))
        print(attr_expr[1, ...].parse_string(text).dump())

        attr_label = label
        attr_value = Suppress(':') + OneOrMore(data_word, stop_on=label).set_parse_action(' '.join)

        # similar to Dict, but simpler call format
        result = dict_of(attr_label, attr_value).parse_string(text)
        print(result.dump())
        print(result['shape'])
        print(result.shape)  # object attribute access works too
        print(result.as_dict())

    prints::

        [['shape', 'SQUARE'], ['posn', 'upper left'], ['color', 'light blue'], ['texture', 'burlap']]
        - color: 'light blue'
        - posn: 'upper left'
        - shape: 'SQUARE'
        - texture: 'burlap'
        SQUARE
        SQUARE
        {'color': 'light blue', 'shape': 'SQUARE', 'posn': 'upper left', 'texture': 'burlap'}
    """
    return Dict(OneOrMore(Group(key + value)))


def original_text_for(
    expr: ParserElement, as_string: bool = True, *, asString: bool = True
) -> ParserElement:
    """Helper to return the original, untokenized text for a given
    expression.  Useful to restore the parsed fields of an HTML start
    tag into the raw tag text itself, or to revert separate tokens with
    intervening whitespace back to the original matching input text. By
    default, returns a string containing the original parsed text.

    If the optional ``as_string`` argument is passed as
    ``False``, then the return value is
    a :class:`ParseResults` containing any results names that
    were originally matched, and a single token containing the original
    matched text from the input string.  So if the expression passed to
    :class:`original_text_for` contains expressions with defined
    results names, you must set ``as_string`` to ``False`` if you
    want to preserve those results name values.

    The ``asString`` pre-PEP8 argument is retained for compatibility,
    but will be removed in a future release.

    Example::

        src = "this is test <b> bold <i>text</i> </b> normal text "
        for tag in ("b", "i"):
            opener, closer = make_html_tags(tag)
            patt = original_text_for(opener + ... + closer)
            print(patt.search_string(src)[0])

    prints::

        ['<b> bold <i>text</i> </b>']
        ['<i>text</i>']
    """
    asString = asString and as_string

    locMarker = Empty().set_parse_action(lambda s, loc, t: loc)
    endlocMarker = locMarker.copy()
    endlocMarker.callPreparse = False
    matchExpr = locMarker("_original_start") + expr + endlocMarker("_original_end")
    if asString:
        extractText = lambda s, l, t: s[t._original_start : t._original_end]
    else:

        def extractText(s, l, t):
            t[:] = [s[t.pop("_original_start") : t.pop("_original_end")]]

    matchExpr.set_parse_action(extractText)
    matchExpr.ignoreExprs = expr.ignoreExprs
    matchExpr.suppress_warning(Diagnostics.warn_ungrouped_named_tokens_in_collection)
    return matchExpr


def ungroup(expr: ParserElement) -> ParserElement:
    """Helper to undo pyparsing's default grouping of And expressions,
    even if all but one are non-empty.
    """
    return TokenConverter(expr).add_parse_action(lambda t: t[0])


def locatedExpr(expr: ParserElement) -> ParserElement:
    """
    (DEPRECATED - future code should use the :class:`Located` class)
    Helper to decorate a returned token with its starting and ending
    locations in the input string.

    This helper adds the following results names:

    - ``locn_start`` - location where matched expression begins
    - ``locn_end`` - location where matched expression ends
    - ``value`` - the actual parsed results

    Be careful if the input text contains ``<TAB>`` characters, you
    may want to call :class:`ParserElement.parse_with_tabs`

    Example::

        wd = Word(alphas)
        for match in locatedExpr(wd).search_string("ljsdf123lksdjjf123lkkjj1222"):
            print(match)

    prints::

        [[0, 'ljsdf', 5]]
        [[8, 'lksdjjf', 15]]
        [[18, 'lkkjj', 23]]
    """
    locator = Empty().set_parse_action(lambda ss, ll, tt: ll)
    return Group(
        locator("locn_start")
        + expr("value")
        + locator.copy().leaveWhitespace()("locn_end")
    )


# define special default value to permit None as a significant value for
# ignore_expr
_NO_IGNORE_EXPR_GIVEN = NoMatch()


def nested_expr(
    opener: Union[str, ParserElement] = "(",
    closer: Union[str, ParserElement] = ")",
    content: typing.Optional[ParserElement] = None,
    ignore_expr: ParserElement = _NO_IGNORE_EXPR_GIVEN,
    *,
    ignoreExpr: ParserElement = _NO_IGNORE_EXPR_GIVEN,
) -> ParserElement:
    """Helper method for defining nested lists enclosed in opening and
    closing delimiters (``"("`` and ``")"`` are the default).

    Parameters:

    - ``opener`` - opening character for a nested list
      (default= ``"("``); can also be a pyparsing expression
    - ``closer`` - closing character for a nested list
      (default= ``")"``); can also be a pyparsing expression
    - ``content`` - expression for items within the nested lists
      (default= ``None``)
    - ``ignore_expr`` - expression for ignoring opening and closing delimiters
      (default= :class:`quoted_string`)
    - ``ignoreExpr`` - this pre-PEP8 argument is retained for compatibility
      but will be removed in a future release

    If an expression is not provided for the content argument, the
    nested expression will capture all whitespace-delimited content
    between delimiters as a list of separate values.

    Use the ``ignore_expr`` argument to define expressions that may
    contain opening or closing characters that should not be treated as
    opening or closing characters for nesting, such as quoted_string or
    a comment expression.  Specify multiple expressions using an
    :class:`Or` or :class:`MatchFirst`. The default is
    :class:`quoted_string`, but if no expressions are to be ignored, then
    pass ``None`` for this argument.

    Example::

        data_type = one_of("void int short long char float double")
        decl_data_type = Combine(data_type + Opt(Word('*')))
        ident = Word(alphas+'_', alphanums+'_')
        number = pyparsing_common.number
        arg = Group(decl_data_type + ident)
        LPAR, RPAR = map(Suppress, "()")

        code_body = nested_expr('{', '}', ignore_expr=(quoted_string | c_style_comment))

        c_function = (decl_data_type("type")
                      + ident("name")
                      + LPAR + Opt(DelimitedList(arg), [])("args") + RPAR
                      + code_body("body"))
        c_function.ignore(c_style_comment)

        source_code = '''
            int is_odd(int x) {
                return (x%2);
            }

            int dec_to_hex(char hchar) {
                if (hchar >= '0' && hchar <= '9') {
                    return (ord(hchar)-ord('0'));
                } else {
                    return (10+ord(hchar)-ord('A'));
                }
            }
        '''
        for func in c_function.search_string(source_code):
            print("%(name)s (%(type)s) args: %(args)s" % func)


    prints::

        is_odd (int) args: [['int', 'x']]
        dec_to_hex (int) args: [['char', 'hchar']]
    """
    if ignoreExpr != ignore_expr:
        ignoreExpr = ignore_expr if ignoreExpr is _NO_IGNORE_EXPR_GIVEN else ignoreExpr

    if ignoreExpr is _NO_IGNORE_EXPR_GIVEN:
        ignoreExpr = quoted_string()

    if opener == closer:
        raise ValueError("opening and closing strings cannot be the same")

    if content is None:
        if isinstance(opener, str_type) and isinstance(closer, str_type):
            opener = typing.cast(str, opener)
            closer = typing.cast(str, closer)
            if len(opener) == 1 and len(closer) == 1:
                if ignoreExpr is not None:
                    content = Combine(
                        OneOrMore(
                            ~ignoreExpr
                            + CharsNotIn(
                                opener + closer + ParserElement.DEFAULT_WHITE_CHARS,
                                exact=1,
                            )
                        )
                    )
                else:
                    content = Combine(
                        Empty()
                        + CharsNotIn(
                            opener + closer + ParserElement.DEFAULT_WHITE_CHARS
                        )
                    )
            else:
                if ignoreExpr is not None:
                    content = Combine(
                        OneOrMore(
                            ~ignoreExpr
                            + ~Literal(opener)
                            + ~Literal(closer)
                            + CharsNotIn(ParserElement.DEFAULT_WHITE_CHARS, exact=1)
                        )
                    )
                else:
                    content = Combine(
                        OneOrMore(
                            ~Literal(opener)
                            + ~Literal(closer)
                            + CharsNotIn(ParserElement.DEFAULT_WHITE_CHARS, exact=1)
                        )
                    )
        else:
            raise ValueError(
                "opening and closing arguments must be strings if no content expression is given"
            )

        # for these internally-created context expressions, simulate whitespace-skipping
        if ParserElement.DEFAULT_WHITE_CHARS:
            content.set_parse_action(
                lambda t: t[0].strip(ParserElement.DEFAULT_WHITE_CHARS)
            )

    ret = Forward()
    if ignoreExpr is not None:
        ret <<= Group(
            Suppress(opener) + ZeroOrMore(ignoreExpr | ret | content) + Suppress(closer)
        )
    else:
        ret <<= Group(Suppress(opener) + ZeroOrMore(ret | content) + Suppress(closer))

    ret.set_name(f"nested {opener}{closer} expression")

    # don't override error message from content expressions
    ret.errmsg = None
    return ret


def _makeTags(tagStr, xml, suppress_LT=Suppress("<"), suppress_GT=Suppress(">")):
    """Internal helper to construct opening and closing tag expressions, given a tag name"""
    if isinstance(tagStr, str_type):
        resname = tagStr
        tagStr = Keyword(tagStr, caseless=not xml)
    else:
        resname = tagStr.name

    tagAttrName = Word(alphas, alphanums + "_-:")
    if xml:
        tagAttrValue = dbl_quoted_string.copy().set_parse_action(remove_quotes)
        openTag = (
            suppress_LT
            + tagStr("tag")
            + Dict(ZeroOrMore(Group(tagAttrName + Suppress("=") + tagAttrValue)))
            + Opt("/", default=[False])("empty").set_parse_action(
                lambda s, l, t: t[0] == "/"
            )
            + suppress_GT
        )
    else:
        tagAttrValue = quoted_string.copy().set_parse_action(remove_quotes) | Word(
            printables, exclude_chars=">"
        )
        openTag = (
            suppress_LT
            + tagStr("tag")
            + Dict(
                ZeroOrMore(
                    Group(
                        tagAttrName.set_parse_action(lambda t: t[0].lower())
                        + Opt(Suppress("=") + tagAttrValue)
                    )
                )
            )
            + Opt("/", default=[False])("empty").set_parse_action(
                lambda s, l, t: t[0] == "/"
            )
            + suppress_GT
        )
    closeTag = Combine(Literal("</") + tagStr + ">", adjacent=False)

    openTag.set_name(f"<{resname}>")
    # add start<tagname> results name in parse action now that ungrouped names are not reported at two levels
    openTag.add_parse_action(
        lambda t: t.__setitem__(
            "start" + "".join(resname.replace(":", " ").title().split()), t.copy()
        )
    )
    closeTag = closeTag(
        "end" + "".join(resname.replace(":", " ").title().split())
    ).set_name(f"</{resname}>")
    openTag.tag = resname
    closeTag.tag = resname
    openTag.tag_body = SkipTo(closeTag())
    return openTag, closeTag


def make_html_tags(
    tag_str: Union[str, ParserElement],
) -> tuple[ParserElement, ParserElement]:
    """Helper to construct opening and closing tag expressions for HTML,
    given a tag name. Matches tags in either upper or lower case,
    attributes with namespaces and with quoted or unquoted values.

    Example::

        text = '<td>More info at the <a href="https://github.com/pyparsing/pyparsing/wiki">pyparsing</a> wiki page</td>'
        # make_html_tags returns pyparsing expressions for the opening and
        # closing tags as a 2-tuple
        a, a_end = make_html_tags("A")
        link_expr = a + SkipTo(a_end)("link_text") + a_end

        for link in link_expr.search_string(text):
            # attributes in the <A> tag (like "href" shown here) are
            # also accessible as named results
            print(link.link_text, '->', link.href)

    prints::

        pyparsing -> https://github.com/pyparsing/pyparsing/wiki
    """
    return _makeTags(tag_str, False)


def make_xml_tags(
    tag_str: Union[str, ParserElement],
) -> tuple[ParserElement, ParserElement]:
    """Helper to construct opening and closing tag expressions for XML,
    given a tag name. Matches tags only in the given upper/lower case.

    Example: similar to :class:`make_html_tags`
    """
    return _makeTags(tag_str, True)


any_open_tag: ParserElement
any_close_tag: ParserElement
any_open_tag, any_close_tag = make_html_tags(
    Word(alphas, alphanums + "_:").set_name("any tag")
)

_htmlEntityMap = {k.rstrip(";"): v for k, v in html.entities.html5.items()}
_most_common_entities = "nbsp lt gt amp quot apos cent pound euro copy".replace(
    " ", "|"
)
common_html_entity = Regex(
    lambda: f"&(?P<entity>{_most_common_entities}|{make_compressed_re(_htmlEntityMap)});"
).set_name("common HTML entity")


def replace_html_entity(s, l, t):
    """Helper parser action to replace common HTML entities with their special characters"""
    return _htmlEntityMap.get(t.entity)


class OpAssoc(Enum):
    """Enumeration of operator associativity
    - used in constructing InfixNotationOperatorSpec for :class:`infix_notation`"""

    LEFT = 1
    RIGHT = 2


InfixNotationOperatorArgType = Union[
    ParserElement, str, tuple[Union[ParserElement, str], Union[ParserElement, str]]
]
InfixNotationOperatorSpec = Union[
    tuple[
        InfixNotationOperatorArgType,
        int,
        OpAssoc,
        typing.Optional[ParseAction],
    ],
    tuple[
        InfixNotationOperatorArgType,
        int,
        OpAssoc,
    ],
]


def infix_notation(
    base_expr: ParserElement,
    op_list: list[InfixNotationOperatorSpec],
    lpar: Union[str, ParserElement] = Suppress("("),
    rpar: Union[str, ParserElement] = Suppress(")"),
) -> Forward:
    """Helper method for constructing grammars of expressions made up of
    operators working in a precedence hierarchy.  Operators may be unary
    or binary, left- or right-associative.  Parse actions can also be
    attached to operator expressions. The generated parser will also
    recognize the use of parentheses to override operator precedences
    (see example below).

    Note: if you define a deep operator list, you may see performance
    issues when using infix_notation. See
    :class:`ParserElement.enable_packrat` for a mechanism to potentially
    improve your parser performance.

    Parameters:

    - ``base_expr`` - expression representing the most basic operand to
      be used in the expression
    - ``op_list`` - list of tuples, one for each operator precedence level
      in the expression grammar; each tuple is of the form ``(op_expr,
      num_operands, right_left_assoc, (optional)parse_action)``, where:

      - ``op_expr`` is the pyparsing expression for the operator; may also
        be a string, which will be converted to a Literal; if ``num_operands``
        is 3, ``op_expr`` is a tuple of two expressions, for the two
        operators separating the 3 terms
      - ``num_operands`` is the number of terms for this operator (must be 1,
        2, or 3)
      - ``right_left_assoc`` is the indicator whether the operator is right
        or left associative, using the pyparsing-defined constants
        ``OpAssoc.RIGHT`` and ``OpAssoc.LEFT``.
      - ``parse_action`` is the parse action to be associated with
        expressions matching this operator expression (the parse action
        tuple member may be omitted); if the parse action is passed
        a tuple or list of functions, this is equivalent to calling
        ``set_parse_action(*fn)``
        (:class:`ParserElement.set_parse_action`)
    - ``lpar`` - expression for matching left-parentheses; if passed as a
      str, then will be parsed as ``Suppress(lpar)``. If lpar is passed as
      an expression (such as ``Literal('(')``), then it will be kept in
      the parsed results, and grouped with them. (default= ``Suppress('(')``)
    - ``rpar`` - expression for matching right-parentheses; if passed as a
      str, then will be parsed as ``Suppress(rpar)``. If rpar is passed as
      an expression (such as ``Literal(')')``), then it will be kept in
      the parsed results, and grouped with them. (default= ``Suppress(')')``)

    Example::

        # simple example of four-function arithmetic with ints and
        # variable names
        integer = pyparsing_common.signed_integer
        varname = pyparsing_common.identifier

        arith_expr = infix_notation(integer | varname,
            [
            ('-', 1, OpAssoc.RIGHT),
            (one_of('* /'), 2, OpAssoc.LEFT),
            (one_of('+ -'), 2, OpAssoc.LEFT),
            ])

        arith_expr.run_tests('''
            5+3*6
            (5+3)*6
            -2--11
            ''', full_dump=False)

    prints::

        5+3*6
        [[5, '+', [3, '*', 6]]]

        (5+3)*6
        [[[5, '+', 3], '*', 6]]

        (5+x)*y
        [[[5, '+', 'x'], '*', 'y']]

        -2--11
        [[['-', 2], '-', ['-', 11]]]
    """

    # captive version of FollowedBy that does not do parse actions or capture results names
    class _FB(FollowedBy):
        def parseImpl(self, instring, loc, doActions=True):
            self.expr.try_parse(instring, loc)
            return loc, []

    _FB.__name__ = "FollowedBy>"

    ret = Forward()
    ret.set_name(f"{base_expr.name}_expression")
    if isinstance(lpar, str):
        lpar = Suppress(lpar)
    if isinstance(rpar, str):
        rpar = Suppress(rpar)

    nested_expr = (lpar + ret + rpar).set_name(f"nested_{base_expr.name}")

    # if lpar and rpar are not suppressed, wrap in group
    if not (isinstance(lpar, Suppress) and isinstance(rpar, Suppress)):
        lastExpr = base_expr | Group(nested_expr)
    else:
        lastExpr = base_expr | nested_expr

    arity: int
    rightLeftAssoc: opAssoc
    pa: typing.Optional[ParseAction]
    opExpr1: ParserElement
    opExpr2: ParserElement
    matchExpr: ParserElement
    match_lookahead: ParserElement
    for operDef in op_list:
        opExpr, arity, rightLeftAssoc, pa = (operDef + (None,))[:4]  # type: ignore[assignment]
        if isinstance(opExpr, str_type):
            opExpr = ParserElement._literalStringClass(opExpr)
        opExpr = typing.cast(ParserElement, opExpr)
        if arity == 3:
            if not isinstance(opExpr, (tuple, list)) or len(opExpr) != 2:
                raise ValueError(
                    "if numterms=3, opExpr must be a tuple or list of two expressions"
                )
            opExpr1, opExpr2 = opExpr
            term_name = f"{opExpr1}{opExpr2} operations"
        else:
            term_name = f"{opExpr} operations"

        if not 1 <= arity <= 3:
            raise ValueError("operator must be unary (1), binary (2), or ternary (3)")

        if rightLeftAssoc not in (OpAssoc.LEFT, OpAssoc.RIGHT):
            raise ValueError("operator must indicate right or left associativity")

        thisExpr: ParserElement = Forward().set_name(term_name)
        thisExpr = typing.cast(Forward, thisExpr)
        match_lookahead = And([])
        if rightLeftAssoc is OpAssoc.LEFT:
            if arity == 1:
                match_lookahead = _FB(lastExpr + opExpr)
                matchExpr = Group(lastExpr + opExpr[1, ...])
            elif arity == 2:
                if opExpr is not None:
                    match_lookahead = _FB(lastExpr + opExpr + lastExpr)
                    matchExpr = Group(lastExpr + (opExpr + lastExpr)[1, ...])
                else:
                    match_lookahead = _FB(lastExpr + lastExpr)
                    matchExpr = Group(lastExpr[2, ...])
            elif arity == 3:
                match_lookahead = _FB(
                    lastExpr + opExpr1 + lastExpr + opExpr2 + lastExpr
                )
                matchExpr = Group(
                    lastExpr + (opExpr1 + lastExpr + opExpr2 + lastExpr)[1, ...]
                )
        elif rightLeftAssoc is OpAssoc.RIGHT:
            if arity == 1:
                # try to avoid LR with this extra test
                if not isinstance(opExpr, Opt):
                    opExpr = Opt(opExpr)
                match_lookahead = _FB(opExpr.expr + thisExpr)
                matchExpr = Group(opExpr + thisExpr)
            elif arity == 2:
                if opExpr is not None:
                    match_lookahead = _FB(lastExpr + opExpr + thisExpr)
                    matchExpr = Group(lastExpr + (opExpr + thisExpr)[1, ...])
                else:
                    match_lookahead = _FB(lastExpr + thisExpr)
                    matchExpr = Group(lastExpr + thisExpr[1, ...])
            elif arity == 3:
                match_lookahead = _FB(
                    lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr
                )
                matchExpr = Group(lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr)

        # suppress lookahead expr from railroad diagrams
        match_lookahead.show_in_diagram = False

        # TODO - determine why this statement can't be included in the following
        #  if pa block
        matchExpr = match_lookahead + matchExpr

        if pa:
            if isinstance(pa, (tuple, list)):
                matchExpr.set_parse_action(*pa)
            else:
                matchExpr.set_parse_action(pa)

        thisExpr <<= (matchExpr | lastExpr).setName(term_name)
        lastExpr = thisExpr

    ret <<= lastExpr
    return ret


def indentedBlock(blockStatementExpr, indentStack, indent=True, backup_stacks=[]):
    """
    (DEPRECATED - use :class:`IndentedBlock` class instead)
    Helper method for defining space-delimited indentation blocks,
    such as those used to define block statements in Python source code.

    Parameters:

    - ``blockStatementExpr`` - expression defining syntax of statement that
      is repeated within the indented block
    - ``indentStack`` - list created by caller to manage indentation stack
      (multiple ``statementWithIndentedBlock`` expressions within a single
      grammar should share a common ``indentStack``)
    - ``indent`` - boolean indicating whether block must be indented beyond
      the current level; set to ``False`` for block of left-most statements
      (default= ``True``)

    A valid block must contain at least one ``blockStatement``.

    (Note that indentedBlock uses internal parse actions which make it
    incompatible with packrat parsing.)

    Example::

        data = '''
        def A(z):
          A1
          B = 100
          G = A2
          A2
          A3
        B
        def BB(a,b,c):
          BB1
          def BBA():
            bba1
            bba2
            bba3
        C
        D
        def spam(x,y):
             def eggs(z):
                 pass
        '''


        indentStack = [1]
        stmt = Forward()

        identifier = Word(alphas, alphanums)
        funcDecl = ("def" + identifier + Group("(" + Opt(delimitedList(identifier)) + ")") + ":")
        func_body = indentedBlock(stmt, indentStack)
        funcDef = Group(funcDecl + func_body)

        rvalue = Forward()
        funcCall = Group(identifier + "(" + Opt(delimitedList(rvalue)) + ")")
        rvalue << (funcCall | identifier | Word(nums))
        assignment = Group(identifier + "=" + rvalue)
        stmt << (funcDef | assignment | identifier)

        module_body = stmt[1, ...]

        parseTree = module_body.parseString(data)
        parseTree.pprint()

    prints::

        [['def',
          'A',
          ['(', 'z', ')'],
          ':',
          [['A1'], [['B', '=', '100']], [['G', '=', 'A2']], ['A2'], ['A3']]],
         'B',
         ['def',
          'BB',
          ['(', 'a', 'b', 'c', ')'],
          ':',
          [['BB1'], [['def', 'BBA', ['(', ')'], ':', [['bba1'], ['bba2'], ['bba3']]]]]],
         'C',
         'D',
         ['def',
          'spam',
          ['(', 'x', 'y', ')'],
          ':',
          [[['def', 'eggs', ['(', 'z', ')'], ':', [['pass']]]]]]]
    """
    backup_stacks.append(indentStack[:])

    def reset_stack():
        indentStack[:] = backup_stacks[-1]

    def checkPeerIndent(s, l, t):
        if l >= len(s):
            return
        curCol = col(l, s)
        if curCol != indentStack[-1]:
            if curCol > indentStack[-1]:
                raise ParseException(s, l, "illegal nesting")
            raise ParseException(s, l, "not a peer entry")

    def checkSubIndent(s, l, t):
        curCol = col(l, s)
        if curCol > indentStack[-1]:
            indentStack.append(curCol)
        else:
            raise ParseException(s, l, "not a subentry")

    def checkUnindent(s, l, t):
        if l >= len(s):
            return
        curCol = col(l, s)
        if not (indentStack and curCol in indentStack):
            raise ParseException(s, l, "not an unindent")
        if curCol < indentStack[-1]:
            indentStack.pop()

    NL = OneOrMore(LineEnd().set_whitespace_chars("\t ").suppress())
    INDENT = (Empty() + Empty().set_parse_action(checkSubIndent)).set_name("INDENT")
    PEER = Empty().set_parse_action(checkPeerIndent).set_name("")
    UNDENT = Empty().set_parse_action(checkUnindent).set_name("UNINDENT")
    if indent:
        smExpr = Group(
            Opt(NL)
            + INDENT
            + OneOrMore(PEER + Group(blockStatementExpr) + Opt(NL))
            + UNDENT
        )
    else:
        smExpr = Group(
            Opt(NL)
            + OneOrMore(PEER + Group(blockStatementExpr) + Opt(NL))
            + Opt(UNDENT)
        )

    # add a parse action to remove backup_stack from list of backups
    smExpr.add_parse_action(
        lambda: backup_stacks.pop(-1) and None if backup_stacks else None
    )
    smExpr.set_fail_action(lambda a, b, c, d: reset_stack())
    blockStatementExpr.ignore(_bslash + LineEnd())
    return smExpr.set_name("indented block")


# it's easy to get these comment structures wrong - they're very common,
# so may as well make them available
c_style_comment = Regex(r"/\*(?:[^*]|\*(?!/))*\*\/").set_name("C style comment")
"Comment of the form ``/* ... */``"

html_comment = Regex(r"<!--[\s\S]*?-->").set_name("HTML comment")
"Comment of the form ``<!-- ... -->``"

rest_of_line = Regex(r".*").leave_whitespace().set_name("rest of line")
dbl_slash_comment = Regex(r"//(?:\\\n|[^\n])*").set_name("// comment")
"Comment of the form ``// ... (to end of line)``"

cpp_style_comment = Regex(
    r"(?:/\*(?:[^*]|\*(?!/))*\*\/)|(?://(?:\\\n|[^\n])*)"
).set_name("C++ style comment")
"Comment of either form :class:`c_style_comment` or :class:`dbl_slash_comment`"

java_style_comment = cpp_style_comment
"Same as :class:`cpp_style_comment`"

python_style_comment = Regex(r"#.*").set_name("Python style comment")
"Comment of the form ``# ... (to end of line)``"


# build list of built-in expressions, for future reference if a global default value
# gets updated
_builtin_exprs: list[ParserElement] = [
    v for v in vars().values() if isinstance(v, ParserElement)
]


# compatibility function, superseded by DelimitedList class
def delimited_list(
    expr: Union[str, ParserElement],
    delim: Union[str, ParserElement] = ",",
    combine: bool = False,
    min: typing.Optional[int] = None,
    max: typing.Optional[int] = None,
    *,
    allow_trailing_delim: bool = False,
) -> ParserElement:
    """(DEPRECATED - use :class:`DelimitedList` class)"""
    return DelimitedList(
        expr, delim, combine, min, max, allow_trailing_delim=allow_trailing_delim
    )


# Compatibility synonyms
# fmt: off
opAssoc = OpAssoc
anyOpenTag = any_open_tag
anyCloseTag = any_close_tag
commonHTMLEntity = common_html_entity
cStyleComment = c_style_comment
htmlComment = html_comment
restOfLine = rest_of_line
dblSlashComment = dbl_slash_comment
cppStyleComment = cpp_style_comment
javaStyleComment = java_style_comment
pythonStyleComment = python_style_comment
delimitedList = replaced_by_pep8("delimitedList", DelimitedList)
delimited_list = replaced_by_pep8("delimited_list", DelimitedList)
countedArray = replaced_by_pep8("countedArray", counted_array)
matchPreviousLiteral = replaced_by_pep8("matchPreviousLiteral", match_previous_literal)
matchPreviousExpr = replaced_by_pep8("matchPreviousExpr", match_previous_expr)
oneOf = replaced_by_pep8("oneOf", one_of)
dictOf = replaced_by_pep8("dictOf", dict_of)
originalTextFor = replaced_by_pep8("originalTextFor", original_text_for)
nestedExpr = replaced_by_pep8("nestedExpr", nested_expr)
makeHTMLTags = replaced_by_pep8("makeHTMLTags", make_html_tags)
makeXMLTags = replaced_by_pep8("makeXMLTags", make_xml_tags)
replaceHTMLEntity = replaced_by_pep8("replaceHTMLEntity", replace_html_entity)
infixNotation = replaced_by_pep8("infixNotation", infix_notation)
# fmt: on

# === NexusCore/openenv\Lib\site-packages\nltk\draw\tree.py ===
# Natural Language Toolkit: Graphical Representations for Trees
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Graphically display a Tree.
"""

from tkinter import IntVar, Menu, Tk

from nltk.draw.util import (
    BoxWidget,
    CanvasFrame,
    CanvasWidget,
    OvalWidget,
    ParenWidget,
    TextWidget,
)
from nltk.tree import Tree
from nltk.util import in_idle

##//////////////////////////////////////////////////////
##  Tree Segment
##//////////////////////////////////////////////////////


class TreeSegmentWidget(CanvasWidget):
    """
    A canvas widget that displays a single segment of a hierarchical
    tree.  Each ``TreeSegmentWidget`` connects a single "node widget"
    to a sequence of zero or more "subtree widgets".  By default, the
    bottom of the node is connected to the top of each subtree by a
    single line.  However, if the ``roof`` attribute is set, then a
    single triangular "roof" will connect the node to all of its
    children.

    Attributes:
      - ``roof``: What sort of connection to draw between the node and
        its subtrees.  If ``roof`` is true, draw a single triangular
        "roof" over the subtrees.  If ``roof`` is false, draw a line
        between each subtree and the node.  Default value is false.
      - ``xspace``: The amount of horizontal space to leave between
        subtrees when managing this widget.  Default value is 10.
      - ``yspace``: The amount of space to place between the node and
        its children when managing this widget.  Default value is 15.
      - ``color``: The color of the lines connecting the node to its
        subtrees; and of the outline of the triangular roof.  Default
        value is ``'#006060'``.
      - ``fill``: The fill color for the triangular roof.  Default
        value is ``''`` (no fill).
      - ``width``: The width of the lines connecting the node to its
        subtrees; and of the outline of the triangular roof.  Default
        value is 1.
      - ``orientation``: Determines whether the tree branches downwards
        or rightwards.  Possible values are ``'horizontal'`` and
        ``'vertical'``.  The default value is ``'vertical'`` (i.e.,
        branch downwards).
      - ``draggable``: whether the widget can be dragged by the user.
    """

    def __init__(self, canvas, label, subtrees, **attribs):
        """
        :type node:
        :type subtrees: list(CanvasWidgetI)
        """
        self._label = label
        self._subtrees = subtrees

        # Attributes
        self._horizontal = 0
        self._roof = 0
        self._xspace = 10
        self._yspace = 15
        self._ordered = False

        # Create canvas objects.
        self._lines = [canvas.create_line(0, 0, 0, 0, fill="#006060") for c in subtrees]
        self._polygon = canvas.create_polygon(
            0, 0, fill="", state="hidden", outline="#006060"
        )

        # Register child widgets (label + subtrees)
        self._add_child_widget(label)
        for subtree in subtrees:
            self._add_child_widget(subtree)

        # Are we currently managing?
        self._managing = False

        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        canvas = self.canvas()
        if attr == "roof":
            self._roof = value
            if self._roof:
                for l in self._lines:
                    canvas.itemconfig(l, state="hidden")
                canvas.itemconfig(self._polygon, state="normal")
            else:
                for l in self._lines:
                    canvas.itemconfig(l, state="normal")
                canvas.itemconfig(self._polygon, state="hidden")
        elif attr == "orientation":
            if value == "horizontal":
                self._horizontal = 1
            elif value == "vertical":
                self._horizontal = 0
            else:
                raise ValueError("orientation must be horizontal or vertical")
        elif attr == "color":
            for l in self._lines:
                canvas.itemconfig(l, fill=value)
            canvas.itemconfig(self._polygon, outline=value)
        elif isinstance(attr, tuple) and attr[0] == "color":
            # Set the color of an individual line.
            l = self._lines[int(attr[1])]
            canvas.itemconfig(l, fill=value)
        elif attr == "fill":
            canvas.itemconfig(self._polygon, fill=value)
        elif attr == "width":
            canvas.itemconfig(self._polygon, {attr: value})
            for l in self._lines:
                canvas.itemconfig(l, {attr: value})
        elif attr in ("xspace", "yspace"):
            if attr == "xspace":
                self._xspace = value
            elif attr == "yspace":
                self._yspace = value
            self.update(self._label)
        elif attr == "ordered":
            self._ordered = value
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == "roof":
            return self._roof
        elif attr == "width":
            return self.canvas().itemcget(self._polygon, attr)
        elif attr == "color":
            return self.canvas().itemcget(self._polygon, "outline")
        elif isinstance(attr, tuple) and attr[0] == "color":
            l = self._lines[int(attr[1])]
            return self.canvas().itemcget(l, "fill")
        elif attr == "xspace":
            return self._xspace
        elif attr == "yspace":
            return self._yspace
        elif attr == "orientation":
            if self._horizontal:
                return "horizontal"
            else:
                return "vertical"
        elif attr == "ordered":
            return self._ordered
        else:
            return CanvasWidget.__getitem__(self, attr)

    def label(self):
        return self._label

    def subtrees(self):
        return self._subtrees[:]

    def set_label(self, label):
        """
        Set the node label to ``label``.
        """
        self._remove_child_widget(self._label)
        self._add_child_widget(label)
        self._label = label
        self.update(self._label)

    def replace_child(self, oldchild, newchild):
        """
        Replace the child ``oldchild`` with ``newchild``.
        """
        index = self._subtrees.index(oldchild)
        self._subtrees[index] = newchild
        self._remove_child_widget(oldchild)
        self._add_child_widget(newchild)
        self.update(newchild)

    def remove_child(self, child):
        index = self._subtrees.index(child)
        del self._subtrees[index]
        self._remove_child_widget(child)
        self.canvas().delete(self._lines.pop())
        self.update(self._label)

    def insert_child(self, index, child):
        canvas = self.canvas()
        self._subtrees.insert(index, child)
        self._add_child_widget(child)
        self._lines.append(canvas.create_line(0, 0, 0, 0, fill="#006060"))
        self.update(self._label)

    # but.. lines???

    def _tags(self):
        if self._roof:
            return [self._polygon]
        else:
            return self._lines

    def _subtree_top(self, child):
        if isinstance(child, TreeSegmentWidget):
            bbox = child.label().bbox()
        else:
            bbox = child.bbox()
        if self._horizontal:
            return (bbox[0], (bbox[1] + bbox[3]) / 2.0)
        else:
            return ((bbox[0] + bbox[2]) / 2.0, bbox[1])

    def _node_bottom(self):
        bbox = self._label.bbox()
        if self._horizontal:
            return (bbox[2], (bbox[1] + bbox[3]) / 2.0)
        else:
            return ((bbox[0] + bbox[2]) / 2.0, bbox[3])

    def _update(self, child):
        if len(self._subtrees) == 0:
            return
        if self._label.bbox() is None:
            return  # [XX] ???

        # Which lines need to be redrawn?
        if child is self._label:
            need_update = self._subtrees
        else:
            need_update = [child]

        if self._ordered and not self._managing:
            need_update = self._maintain_order(child)

        # Update the polygon.
        (nodex, nodey) = self._node_bottom()
        (xmin, ymin, xmax, ymax) = self._subtrees[0].bbox()
        for subtree in self._subtrees[1:]:
            bbox = subtree.bbox()
            xmin = min(xmin, bbox[0])
            ymin = min(ymin, bbox[1])
            xmax = max(xmax, bbox[2])
            ymax = max(ymax, bbox[3])

        if self._horizontal:
            self.canvas().coords(
                self._polygon, nodex, nodey, xmin, ymin, xmin, ymax, nodex, nodey
            )
        else:
            self.canvas().coords(
                self._polygon, nodex, nodey, xmin, ymin, xmax, ymin, nodex, nodey
            )

        # Redraw all lines that need it.
        for subtree in need_update:
            (nodex, nodey) = self._node_bottom()
            line = self._lines[self._subtrees.index(subtree)]
            (subtreex, subtreey) = self._subtree_top(subtree)
            self.canvas().coords(line, nodex, nodey, subtreex, subtreey)

    def _maintain_order(self, child):
        if self._horizontal:
            return self._maintain_order_horizontal(child)
        else:
            return self._maintain_order_vertical(child)

    def _maintain_order_vertical(self, child):
        (left, top, right, bot) = child.bbox()

        if child is self._label:
            # Check all the leaves
            for subtree in self._subtrees:
                (x1, y1, x2, y2) = subtree.bbox()
                if bot + self._yspace > y1:
                    subtree.move(0, bot + self._yspace - y1)

            return self._subtrees
        else:
            moved = [child]
            index = self._subtrees.index(child)

            # Check leaves to our right.
            x = right + self._xspace
            for i in range(index + 1, len(self._subtrees)):
                (x1, y1, x2, y2) = self._subtrees[i].bbox()
                if x > x1:
                    self._subtrees[i].move(x - x1, 0)
                    x += x2 - x1 + self._xspace
                    moved.append(self._subtrees[i])

            # Check leaves to our left.
            x = left - self._xspace
            for i in range(index - 1, -1, -1):
                (x1, y1, x2, y2) = self._subtrees[i].bbox()
                if x < x2:
                    self._subtrees[i].move(x - x2, 0)
                    x -= x2 - x1 + self._xspace
                    moved.append(self._subtrees[i])

            # Check the node
            (x1, y1, x2, y2) = self._label.bbox()
            if y2 > top - self._yspace:
                self._label.move(0, top - self._yspace - y2)
                moved = self._subtrees

        # Return a list of the nodes we moved
        return moved

    def _maintain_order_horizontal(self, child):
        (left, top, right, bot) = child.bbox()

        if child is self._label:
            # Check all the leaves
            for subtree in self._subtrees:
                (x1, y1, x2, y2) = subtree.bbox()
                if right + self._xspace > x1:
                    subtree.move(right + self._xspace - x1)

            return self._subtrees
        else:
            moved = [child]
            index = self._subtrees.index(child)

            # Check leaves below us.
            y = bot + self._yspace
            for i in range(index + 1, len(self._subtrees)):
                (x1, y1, x2, y2) = self._subtrees[i].bbox()
                if y > y1:
                    self._subtrees[i].move(0, y - y1)
                    y += y2 - y1 + self._yspace
                    moved.append(self._subtrees[i])

            # Check leaves above us
            y = top - self._yspace
            for i in range(index - 1, -1, -1):
                (x1, y1, x2, y2) = self._subtrees[i].bbox()
                if y < y2:
                    self._subtrees[i].move(0, y - y2)
                    y -= y2 - y1 + self._yspace
                    moved.append(self._subtrees[i])

            # Check the node
            (x1, y1, x2, y2) = self._label.bbox()
            if x2 > left - self._xspace:
                self._label.move(left - self._xspace - x2, 0)
                moved = self._subtrees

        # Return a list of the nodes we moved
        return moved

    def _manage_horizontal(self):
        (nodex, nodey) = self._node_bottom()

        # Put the subtrees in a line.
        y = 20
        for subtree in self._subtrees:
            subtree_bbox = subtree.bbox()
            dx = nodex - subtree_bbox[0] + self._xspace
            dy = y - subtree_bbox[1]
            subtree.move(dx, dy)
            y += subtree_bbox[3] - subtree_bbox[1] + self._yspace

        # Find the center of their tops.
        center = 0.0
        for subtree in self._subtrees:
            center += self._subtree_top(subtree)[1]
        center /= len(self._subtrees)

        # Center the subtrees with the node.
        for subtree in self._subtrees:
            subtree.move(0, nodey - center)

    def _manage_vertical(self):
        (nodex, nodey) = self._node_bottom()

        # Put the subtrees in a line.
        x = 0
        for subtree in self._subtrees:
            subtree_bbox = subtree.bbox()
            dy = nodey - subtree_bbox[1] + self._yspace
            dx = x - subtree_bbox[0]
            subtree.move(dx, dy)
            x += subtree_bbox[2] - subtree_bbox[0] + self._xspace

        # Find the center of their tops.
        center = 0.0
        for subtree in self._subtrees:
            center += self._subtree_top(subtree)[0] / len(self._subtrees)

        # Center the subtrees with the node.
        for subtree in self._subtrees:
            subtree.move(nodex - center, 0)

    def _manage(self):
        self._managing = True
        (nodex, nodey) = self._node_bottom()
        if len(self._subtrees) == 0:
            return

        if self._horizontal:
            self._manage_horizontal()
        else:
            self._manage_vertical()

        # Update lines to subtrees.
        for subtree in self._subtrees:
            self._update(subtree)

        self._managing = False

    def __repr__(self):
        return f"[TreeSeg {self._label}: {self._subtrees}]"


def _tree_to_treeseg(
    canvas,
    t,
    make_node,
    make_leaf,
    tree_attribs,
    node_attribs,
    leaf_attribs,
    loc_attribs,
):
    if isinstance(t, Tree):
        label = make_node(canvas, t.label(), **node_attribs)
        subtrees = [
            _tree_to_treeseg(
                canvas,
                child,
                make_node,
                make_leaf,
                tree_attribs,
                node_attribs,
                leaf_attribs,
                loc_attribs,
            )
            for child in t
        ]
        return TreeSegmentWidget(canvas, label, subtrees, **tree_attribs)
    else:
        return make_leaf(canvas, t, **leaf_attribs)


def tree_to_treesegment(
    canvas, t, make_node=TextWidget, make_leaf=TextWidget, **attribs
):
    """
    Convert a Tree into a ``TreeSegmentWidget``.

    :param make_node: A ``CanvasWidget`` constructor or a function that
        creates ``CanvasWidgets``.  ``make_node`` is used to convert
        the Tree's nodes into ``CanvasWidgets``.  If no constructor
        is specified, then ``TextWidget`` will be used.
    :param make_leaf: A ``CanvasWidget`` constructor or a function that
        creates ``CanvasWidgets``.  ``make_leaf`` is used to convert
        the Tree's leafs into ``CanvasWidgets``.  If no constructor
        is specified, then ``TextWidget`` will be used.
    :param attribs: Attributes for the canvas widgets that make up the
        returned ``TreeSegmentWidget``.  Any attribute beginning with
        ``'tree_'`` will be passed to all ``TreeSegmentWidgets`` (with
        the ``'tree_'`` prefix removed.  Any attribute beginning with
        ``'node_'`` will be passed to all nodes.  Any attribute
        beginning with ``'leaf_'`` will be passed to all leaves.  And
        any attribute beginning with ``'loc_'`` will be passed to all
        text locations (for Trees).
    """
    # Process attribs.
    tree_attribs = {}
    node_attribs = {}
    leaf_attribs = {}
    loc_attribs = {}

    for key, value in list(attribs.items()):
        if key[:5] == "tree_":
            tree_attribs[key[5:]] = value
        elif key[:5] == "node_":
            node_attribs[key[5:]] = value
        elif key[:5] == "leaf_":
            leaf_attribs[key[5:]] = value
        elif key[:4] == "loc_":
            loc_attribs[key[4:]] = value
        else:
            raise ValueError("Bad attribute: %s" % key)
    return _tree_to_treeseg(
        canvas,
        t,
        make_node,
        make_leaf,
        tree_attribs,
        node_attribs,
        leaf_attribs,
        loc_attribs,
    )


##//////////////////////////////////////////////////////
##  Tree Widget
##//////////////////////////////////////////////////////


class TreeWidget(CanvasWidget):
    """
    A canvas widget that displays a single Tree.
    ``TreeWidget`` manages a group of ``TreeSegmentWidgets`` that are
    used to display a Tree.

    Attributes:

      - ``node_attr``: Sets the attribute ``attr`` on all of the
        node widgets for this ``TreeWidget``.
      - ``node_attr``: Sets the attribute ``attr`` on all of the
        leaf widgets for this ``TreeWidget``.
      - ``loc_attr``: Sets the attribute ``attr`` on all of the
        location widgets for this ``TreeWidget`` (if it was built from
        a Tree).  Note that a location widget is a ``TextWidget``.

      - ``xspace``: The amount of horizontal space to leave between
        subtrees when managing this widget.  Default value is 10.
      - ``yspace``: The amount of space to place between the node and
        its children when managing this widget.  Default value is 15.

      - ``line_color``: The color of the lines connecting each expanded
        node to its subtrees.
      - ``roof_color``: The color of the outline of the triangular roof
        for collapsed trees.
      - ``roof_fill``: The fill color for the triangular roof for
        collapsed trees.
      - ``width``

      - ``orientation``: Determines whether the tree branches downwards
        or rightwards.  Possible values are ``'horizontal'`` and
        ``'vertical'``.  The default value is ``'vertical'`` (i.e.,
        branch downwards).

      - ``shapeable``: whether the subtrees can be independently
        dragged by the user.  THIS property simply sets the
        ``DRAGGABLE`` property on all of the ``TreeWidget``'s tree
        segments.
      - ``draggable``: whether the widget can be dragged by the user.
    """

    def __init__(
        self, canvas, t, make_node=TextWidget, make_leaf=TextWidget, **attribs
    ):
        # Node & leaf canvas widget constructors
        self._make_node = make_node
        self._make_leaf = make_leaf
        self._tree = t

        # Attributes.
        self._nodeattribs = {}
        self._leafattribs = {}
        self._locattribs = {"color": "#008000"}
        self._line_color = "#008080"
        self._line_width = 1
        self._roof_color = "#008080"
        self._roof_fill = "#c0c0c0"
        self._shapeable = False
        self._xspace = 10
        self._yspace = 10
        self._orientation = "vertical"
        self._ordered = False

        # Build trees.
        self._keys = {}  # treeseg -> key
        self._expanded_trees = {}
        self._collapsed_trees = {}
        self._nodes = []
        self._leaves = []
        # self._locs = []
        self._make_collapsed_trees(canvas, t, ())
        self._treeseg = self._make_expanded_tree(canvas, t, ())
        self._add_child_widget(self._treeseg)

        CanvasWidget.__init__(self, canvas, **attribs)

    def expanded_tree(self, *path_to_tree):
        """
        Return the ``TreeSegmentWidget`` for the specified subtree.

        :param path_to_tree: A list of indices i1, i2, ..., in, where
            the desired widget is the widget corresponding to
            ``tree.children()[i1].children()[i2]....children()[in]``.
            For the root, the path is ``()``.
        """
        return self._expanded_trees[path_to_tree]

    def collapsed_tree(self, *path_to_tree):
        """
        Return the ``TreeSegmentWidget`` for the specified subtree.

        :param path_to_tree: A list of indices i1, i2, ..., in, where
            the desired widget is the widget corresponding to
            ``tree.children()[i1].children()[i2]....children()[in]``.
            For the root, the path is ``()``.
        """
        return self._collapsed_trees[path_to_tree]

    def bind_click_trees(self, callback, button=1):
        """
        Add a binding to all tree segments.
        """
        for tseg in list(self._expanded_trees.values()):
            tseg.bind_click(callback, button)
        for tseg in list(self._collapsed_trees.values()):
            tseg.bind_click(callback, button)

    def bind_drag_trees(self, callback, button=1):
        """
        Add a binding to all tree segments.
        """
        for tseg in list(self._expanded_trees.values()):
            tseg.bind_drag(callback, button)
        for tseg in list(self._collapsed_trees.values()):
            tseg.bind_drag(callback, button)

    def bind_click_leaves(self, callback, button=1):
        """
        Add a binding to all leaves.
        """
        for leaf in self._leaves:
            leaf.bind_click(callback, button)
        for leaf in self._leaves:
            leaf.bind_click(callback, button)

    def bind_drag_leaves(self, callback, button=1):
        """
        Add a binding to all leaves.
        """
        for leaf in self._leaves:
            leaf.bind_drag(callback, button)
        for leaf in self._leaves:
            leaf.bind_drag(callback, button)

    def bind_click_nodes(self, callback, button=1):
        """
        Add a binding to all nodes.
        """
        for node in self._nodes:
            node.bind_click(callback, button)
        for node in self._nodes:
            node.bind_click(callback, button)

    def bind_drag_nodes(self, callback, button=1):
        """
        Add a binding to all nodes.
        """
        for node in self._nodes:
            node.bind_drag(callback, button)
        for node in self._nodes:
            node.bind_drag(callback, button)

    def _make_collapsed_trees(self, canvas, t, key):
        if not isinstance(t, Tree):
            return
        make_node = self._make_node
        make_leaf = self._make_leaf

        node = make_node(canvas, t.label(), **self._nodeattribs)
        self._nodes.append(node)
        leaves = [make_leaf(canvas, l, **self._leafattribs) for l in t.leaves()]
        self._leaves += leaves
        treeseg = TreeSegmentWidget(
            canvas,
            node,
            leaves,
            roof=1,
            color=self._roof_color,
            fill=self._roof_fill,
            width=self._line_width,
        )

        self._collapsed_trees[key] = treeseg
        self._keys[treeseg] = key
        # self._add_child_widget(treeseg)
        treeseg.hide()

        # Build trees for children.
        for i in range(len(t)):
            child = t[i]
            self._make_collapsed_trees(canvas, child, key + (i,))

    def _make_expanded_tree(self, canvas, t, key):
        make_node = self._make_node
        make_leaf = self._make_leaf

        if isinstance(t, Tree):
            node = make_node(canvas, t.label(), **self._nodeattribs)
            self._nodes.append(node)
            children = t
            subtrees = [
                self._make_expanded_tree(canvas, children[i], key + (i,))
                for i in range(len(children))
            ]
            treeseg = TreeSegmentWidget(
                canvas, node, subtrees, color=self._line_color, width=self._line_width
            )
            self._expanded_trees[key] = treeseg
            self._keys[treeseg] = key
            return treeseg
        else:
            leaf = make_leaf(canvas, t, **self._leafattribs)
            self._leaves.append(leaf)
            return leaf

    def __setitem__(self, attr, value):
        if attr[:5] == "node_":
            for node in self._nodes:
                node[attr[5:]] = value
        elif attr[:5] == "leaf_":
            for leaf in self._leaves:
                leaf[attr[5:]] = value
        elif attr == "line_color":
            self._line_color = value
            for tseg in list(self._expanded_trees.values()):
                tseg["color"] = value
        elif attr == "line_width":
            self._line_width = value
            for tseg in list(self._expanded_trees.values()):
                tseg["width"] = value
            for tseg in list(self._collapsed_trees.values()):
                tseg["width"] = value
        elif attr == "roof_color":
            self._roof_color = value
            for tseg in list(self._collapsed_trees.values()):
                tseg["color"] = value
        elif attr == "roof_fill":
            self._roof_fill = value
            for tseg in list(self._collapsed_trees.values()):
                tseg["fill"] = value
        elif attr == "shapeable":
            self._shapeable = value
            for tseg in list(self._expanded_trees.values()):
                tseg["draggable"] = value
            for tseg in list(self._collapsed_trees.values()):
                tseg["draggable"] = value
            for leaf in self._leaves:
                leaf["draggable"] = value
        elif attr == "xspace":
            self._xspace = value
            for tseg in list(self._expanded_trees.values()):
                tseg["xspace"] = value
            for tseg in list(self._collapsed_trees.values()):
                tseg["xspace"] = value
            self.manage()
        elif attr == "yspace":
            self._yspace = value
            for tseg in list(self._expanded_trees.values()):
                tseg["yspace"] = value
            for tseg in list(self._collapsed_trees.values()):
                tseg["yspace"] = value
            self.manage()
        elif attr == "orientation":
            self._orientation = value
            for tseg in list(self._expanded_trees.values()):
                tseg["orientation"] = value
            for tseg in list(self._collapsed_trees.values()):
                tseg["orientation"] = value
            self.manage()
        elif attr == "ordered":
            self._ordered = value
            for tseg in list(self._expanded_trees.values()):
                tseg["ordered"] = value
            for tseg in list(self._collapsed_trees.values()):
                tseg["ordered"] = value
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr[:5] == "node_":
            return self._nodeattribs.get(attr[5:], None)
        elif attr[:5] == "leaf_":
            return self._leafattribs.get(attr[5:], None)
        elif attr[:4] == "loc_":
            return self._locattribs.get(attr[4:], None)
        elif attr == "line_color":
            return self._line_color
        elif attr == "line_width":
            return self._line_width
        elif attr == "roof_color":
            return self._roof_color
        elif attr == "roof_fill":
            return self._roof_fill
        elif attr == "shapeable":
            return self._shapeable
        elif attr == "xspace":
            return self._xspace
        elif attr == "yspace":
            return self._yspace
        elif attr == "orientation":
            return self._orientation
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _tags(self):
        return []

    def _manage(self):
        segs = list(self._expanded_trees.values()) + list(
            self._collapsed_trees.values()
        )
        for tseg in segs:
            if tseg.hidden():
                tseg.show()
                tseg.manage()
                tseg.hide()

    def toggle_collapsed(self, treeseg):
        """
        Collapse/expand a tree.
        """
        old_treeseg = treeseg
        if old_treeseg["roof"]:
            new_treeseg = self._expanded_trees[self._keys[old_treeseg]]
        else:
            new_treeseg = self._collapsed_trees[self._keys[old_treeseg]]

        # Replace the old tree with the new tree.
        if old_treeseg.parent() is self:
            self._remove_child_widget(old_treeseg)
            self._add_child_widget(new_treeseg)
            self._treeseg = new_treeseg
        else:
            old_treeseg.parent().replace_child(old_treeseg, new_treeseg)

        # Move the new tree to where the old tree was.  Show it first,
        # so we can find its bounding box.
        new_treeseg.show()
        (newx, newy) = new_treeseg.label().bbox()[:2]
        (oldx, oldy) = old_treeseg.label().bbox()[:2]
        new_treeseg.move(oldx - newx, oldy - newy)

        # Hide the old tree
        old_treeseg.hide()

        # We could do parent.manage() here instead, if we wanted.
        new_treeseg.parent().update(new_treeseg)


##//////////////////////////////////////////////////////
##  draw_trees
##//////////////////////////////////////////////////////


class TreeView:
    def __init__(self, *trees):
        from math import ceil, sqrt

        self._trees = trees

        self._top = Tk()
        self._top.title("NLTK")
        self._top.bind("<Control-x>", self.destroy)
        self._top.bind("<Control-q>", self.destroy)

        cf = self._cframe = CanvasFrame(self._top)
        self._top.bind("<Control-p>", self._cframe.print_to_file)

        # Size is variable.
        self._size = IntVar(self._top)
        self._size.set(12)
        bold = ("helvetica", -self._size.get(), "bold")
        helv = ("helvetica", -self._size.get())

        # Lay the trees out in a square.
        self._width = int(ceil(sqrt(len(trees))))
        self._widgets = []
        for i in range(len(trees)):
            widget = TreeWidget(
                cf.canvas(),
                trees[i],
                node_font=bold,
                leaf_color="#008040",
                node_color="#004080",
                roof_color="#004040",
                roof_fill="white",
                line_color="#004040",
                draggable=1,
                leaf_font=helv,
            )
            widget.bind_click_trees(widget.toggle_collapsed)
            self._widgets.append(widget)
            cf.add_widget(widget, 0, 0)

        self._layout()
        self._cframe.pack(expand=1, fill="both")
        self._init_menubar()

    def _layout(self):
        i = x = y = ymax = 0
        width = self._width
        for i in range(len(self._widgets)):
            widget = self._widgets[i]
            (oldx, oldy) = widget.bbox()[:2]
            if i % width == 0:
                y = ymax
                x = 0
            widget.move(x - oldx, y - oldy)
            x = widget.bbox()[2] + 10
            ymax = max(ymax, widget.bbox()[3] + 10)

    def _init_menubar(self):
        menubar = Menu(self._top)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Print to Postscript",
            underline=0,
            command=self._cframe.print_to_file,
            accelerator="Ctrl-p",
        )
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        zoommenu = Menu(menubar, tearoff=0)
        zoommenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=12,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=14,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=28,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=50,
            command=self.resize,
        )
        menubar.add_cascade(label="Zoom", underline=0, menu=zoommenu)

        self._top.config(menu=menubar)

    def resize(self, *e):
        bold = ("helvetica", -self._size.get(), "bold")
        helv = ("helvetica", -self._size.get())
        xspace = self._size.get()
        yspace = self._size.get()
        for widget in self._widgets:
            widget["node_font"] = bold
            widget["leaf_font"] = helv
            widget["xspace"] = xspace
            widget["yspace"] = yspace
            if self._size.get() < 20:
                widget["line_width"] = 1
            elif self._size.get() < 30:
                widget["line_width"] = 2
            else:
                widget["line_width"] = 3
        self._layout()

    def destroy(self, *e):
        if self._top is None:
            return
        self._top.destroy()
        self._top = None

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


def draw_trees(*trees):
    """
    Open a new window containing a graphical diagram of the given
    trees.

    :rtype: None
    """
    TreeView(*trees).mainloop()
    return


##//////////////////////////////////////////////////////
##  Demo Code
##//////////////////////////////////////////////////////


def demo():
    import random

    def fill(cw):
        cw["fill"] = "#%06d" % random.randint(0, 999999)

    cf = CanvasFrame(width=550, height=450, closeenough=2)

    t = Tree.fromstring(
        """
    (S (NP the very big cat)
       (VP (Adv sorta) (V saw) (NP (Det the) (N dog))))"""
    )

    tc = TreeWidget(
        cf.canvas(),
        t,
        draggable=1,
        node_font=("helvetica", -14, "bold"),
        leaf_font=("helvetica", -12, "italic"),
        roof_fill="white",
        roof_color="black",
        leaf_color="green4",
        node_color="blue2",
    )
    cf.add_widget(tc, 10, 10)

    def boxit(canvas, text):
        big = ("helvetica", -16, "bold")
        return BoxWidget(canvas, TextWidget(canvas, text, font=big), fill="green")

    def ovalit(canvas, text):
        return OvalWidget(canvas, TextWidget(canvas, text), fill="cyan")

    treetok = Tree.fromstring("(S (NP this tree) (VP (V is) (AdjP shapeable)))")
    tc2 = TreeWidget(cf.canvas(), treetok, boxit, ovalit, shapeable=1)

    def color(node):
        node["color"] = "#%04d00" % random.randint(0, 9999)

    def color2(treeseg):
        treeseg.label()["fill"] = "#%06d" % random.randint(0, 9999)
        treeseg.label().child()["color"] = "white"

    tc.bind_click_trees(tc.toggle_collapsed)
    tc2.bind_click_trees(tc2.toggle_collapsed)
    tc.bind_click_nodes(color, 3)
    tc2.expanded_tree(1).bind_click(color2, 3)
    tc2.expanded_tree().bind_click(color2, 3)

    paren = ParenWidget(cf.canvas(), tc2)
    cf.add_widget(paren, tc.bbox()[2] + 10, 10)

    tree3 = Tree.fromstring(
        """
    (S (NP this tree) (AUX was)
       (VP (V built) (PP (P with) (NP (N tree_to_treesegment)))))"""
    )
    tc3 = tree_to_treesegment(
        cf.canvas(), tree3, tree_color="green4", tree_xspace=2, tree_width=2
    )
    tc3["draggable"] = 1
    cf.add_widget(tc3, 10, tc.bbox()[3] + 10)

    def orientswitch(treewidget):
        if treewidget["orientation"] == "horizontal":
            treewidget.expanded_tree(1, 1).subtrees()[0].set_text("vertical")
            treewidget.collapsed_tree(1, 1).subtrees()[0].set_text("vertical")
            treewidget.collapsed_tree(1).subtrees()[1].set_text("vertical")
            treewidget.collapsed_tree().subtrees()[3].set_text("vertical")
            treewidget["orientation"] = "vertical"
        else:
            treewidget.expanded_tree(1, 1).subtrees()[0].set_text("horizontal")
            treewidget.collapsed_tree(1, 1).subtrees()[0].set_text("horizontal")
            treewidget.collapsed_tree(1).subtrees()[1].set_text("horizontal")
            treewidget.collapsed_tree().subtrees()[3].set_text("horizontal")
            treewidget["orientation"] = "horizontal"

    text = """
Try clicking, right clicking, and dragging
different elements of each of the trees.
The top-left tree is a TreeWidget built from
a Tree.  The top-right is a TreeWidget built
from a Tree, using non-default widget
constructors for the nodes & leaves (BoxWidget
and OvalWidget).  The bottom-left tree is
built from tree_to_treesegment."""
    twidget = TextWidget(cf.canvas(), text.strip())
    textbox = BoxWidget(cf.canvas(), twidget, fill="white", draggable=1)
    cf.add_widget(textbox, tc3.bbox()[2] + 10, tc2.bbox()[3] + 10)

    tree4 = Tree.fromstring("(S (NP this tree) (VP (V is) (Adj horizontal)))")
    tc4 = TreeWidget(
        cf.canvas(),
        tree4,
        draggable=1,
        line_color="brown2",
        roof_color="brown2",
        node_font=("helvetica", -12, "bold"),
        node_color="brown4",
        orientation="horizontal",
    )
    tc4.manage()
    cf.add_widget(tc4, tc3.bbox()[2] + 10, textbox.bbox()[3] + 10)
    tc4.bind_click(orientswitch)
    tc4.bind_click_trees(tc4.toggle_collapsed, 3)

    # Run mainloop
    cf.mainloop()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\traitlets\config\application.py ===
"""A base class for a configurable application."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import functools
import json
import logging
import os
import pprint
import re
import sys
import typing as t
from collections import OrderedDict, defaultdict
from contextlib import suppress
from copy import deepcopy
from logging.config import dictConfig
from textwrap import dedent

from traitlets.config.configurable import Configurable, SingletonConfigurable
from traitlets.config.loader import (
    ArgumentError,
    Config,
    ConfigFileNotFound,
    DeferredConfigString,
    JSONFileConfigLoader,
    KVArgParseConfigLoader,
    PyFileConfigLoader,
)
from traitlets.traitlets import (
    Bool,
    Dict,
    Enum,
    Instance,
    List,
    TraitError,
    Unicode,
    default,
    observe,
    observe_compat,
)
from traitlets.utils.bunch import Bunch
from traitlets.utils.nested_update import nested_update
from traitlets.utils.text import indent, wrap_paragraphs

from ..utils import cast_unicode
from ..utils.importstring import import_item

# -----------------------------------------------------------------------------
# Descriptions for the various sections
# -----------------------------------------------------------------------------
# merge flags&aliases into options
option_description = """
The options below are convenience aliases to configurable class-options,
as listed in the "Equivalent to" description-line of the aliases.
To see all configurable class-options for some <cmd>, use:
    <cmd> --help-all
""".strip()  # trim newlines of front and back

keyvalue_description = """
The command-line option below sets the respective configurable class-parameter:
    --Class.parameter=value
This line is evaluated in Python, so simple expressions are allowed.
For instance, to set `C.a=[0,1,2]`, you may type this:
    --C.a='range(3)'
""".strip()  # trim newlines of front and back

# sys.argv can be missing, for example when python is embedded. See the docs
# for details: http://docs.python.org/2/c-api/intro.html#embedding-python
if not hasattr(sys, "argv"):
    sys.argv = [""]

subcommand_description = """
Subcommands are launched as `{app} cmd [args]`. For information on using
subcommand 'cmd', do: `{app} cmd -h`.
"""
# get running program name

# -----------------------------------------------------------------------------
# Application class
# -----------------------------------------------------------------------------


_envvar = os.environ.get("TRAITLETS_APPLICATION_RAISE_CONFIG_FILE_ERROR", "")
if _envvar.lower() in {"1", "true"}:
    TRAITLETS_APPLICATION_RAISE_CONFIG_FILE_ERROR = True
elif _envvar.lower() in {"0", "false", ""}:
    TRAITLETS_APPLICATION_RAISE_CONFIG_FILE_ERROR = False
else:
    raise ValueError(
        "Unsupported value for environment variable: 'TRAITLETS_APPLICATION_RAISE_CONFIG_FILE_ERROR' is set to '%s' which is none of  {'0', '1', 'false', 'true', ''}."
        % _envvar
    )


IS_PYTHONW = sys.executable and sys.executable.endswith("pythonw.exe")

T = t.TypeVar("T", bound=t.Callable[..., t.Any])
AnyLogger = t.Union[logging.Logger, "logging.LoggerAdapter[t.Any]"]
StrDict = t.Dict[str, t.Any]
ArgvType = t.Optional[t.List[str]]
ClassesType = t.List[t.Type[Configurable]]


def catch_config_error(method: T) -> T:
    """Method decorator for catching invalid config (Trait/ArgumentErrors) during init.

    On a TraitError (generally caused by bad config), this will print the trait's
    message, and exit the app.

    For use on init methods, to prevent invoking excepthook on invalid input.
    """

    @functools.wraps(method)
    def inner(app: Application, *args: t.Any, **kwargs: t.Any) -> t.Any:
        try:
            return method(app, *args, **kwargs)
        except (TraitError, ArgumentError) as e:
            app.log.fatal("Bad config encountered during initialization: %s", e)
            app.log.debug("Config at the time: %s", app.config)
            app.exit(1)

    return t.cast(T, inner)


class ApplicationError(Exception):
    pass


class LevelFormatter(logging.Formatter):
    """Formatter with additional `highlevel` record

    This field is empty if log level is less than highlevel_limit,
    otherwise it is formatted with self.highlevel_format.

    Useful for adding 'WARNING' to warning messages,
    without adding 'INFO' to info, etc.
    """

    highlevel_limit = logging.WARN
    highlevel_format = " %(levelname)s |"

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= self.highlevel_limit:
            record.highlevel = self.highlevel_format % record.__dict__
        else:
            record.highlevel = ""
        return super().format(record)


class Application(SingletonConfigurable):
    """A singleton application with full configuration support."""

    # The name of the application, will usually match the name of the command
    # line application
    name: str | Unicode[str, str | bytes] = Unicode("application")

    # The description of the application that is printed at the beginning
    # of the help.
    description: str | Unicode[str, str | bytes] = Unicode("This is an application.")
    # default section descriptions
    option_description: str | Unicode[str, str | bytes] = Unicode(option_description)
    keyvalue_description: str | Unicode[str, str | bytes] = Unicode(keyvalue_description)
    subcommand_description: str | Unicode[str, str | bytes] = Unicode(subcommand_description)

    python_config_loader_class = PyFileConfigLoader
    json_config_loader_class = JSONFileConfigLoader

    # The usage and example string that goes at the end of the help string.
    examples: str | Unicode[str, str | bytes] = Unicode()

    # A sequence of Configurable subclasses whose config=True attributes will
    # be exposed at the command line.
    classes: ClassesType = []

    def _classes_inc_parents(
        self, classes: ClassesType | None = None
    ) -> t.Generator[type[Configurable], None, None]:
        """Iterate through configurable classes, including configurable parents

        :param classes:
            The list of classes to iterate; if not set, uses :attr:`classes`.

        Children should always be after parents, and each class should only be
        yielded once.
        """
        if classes is None:
            classes = self.classes

        seen = set()
        for c in classes:
            # We want to sort parents before children, so we reverse the MRO
            for parent in reversed(c.mro()):
                if issubclass(parent, Configurable) and (parent not in seen):
                    seen.add(parent)
                    yield parent

    # The version string of this application.
    version: str | Unicode[str, str | bytes] = Unicode("0.0")

    # the argv used to initialize the application
    argv: list[str] | List[str] = List()

    # Whether failing to load config files should prevent startup
    raise_config_file_errors = Bool(TRAITLETS_APPLICATION_RAISE_CONFIG_FILE_ERROR)

    # The log level for the application
    log_level = Enum(
        (0, 10, 20, 30, 40, 50, "DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"),
        default_value=logging.WARN,
        help="Set the log level by value or name.",
    ).tag(config=True)

    _log_formatter_cls = LevelFormatter

    log_datefmt = Unicode(
        "%Y-%m-%d %H:%M:%S", help="The date format used by logging formatters for %(asctime)s"
    ).tag(config=True)

    log_format = Unicode(
        "[%(name)s]%(highlevel)s %(message)s",
        help="The Logging format template",
    ).tag(config=True)

    def get_default_logging_config(self) -> StrDict:
        """Return the base logging configuration.

        The default is to log to stderr using a StreamHandler, if no default
        handler already exists.

        The log handler level starts at logging.WARN, but this can be adjusted
        by setting the ``log_level`` attribute.

        The ``logging_config`` trait is merged into this allowing for finer
        control of logging.

        """
        config: StrDict = {
            "version": 1,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "console",
                    "level": logging.getLevelName(self.log_level),  # type:ignore[arg-type]
                    "stream": "ext://sys.stderr",
                },
            },
            "formatters": {
                "console": {
                    "class": (
                        f"{self._log_formatter_cls.__module__}"
                        f".{self._log_formatter_cls.__name__}"
                    ),
                    "format": self.log_format,
                    "datefmt": self.log_datefmt,
                },
            },
            "loggers": {
                self.__class__.__name__: {
                    "level": "DEBUG",
                    "handlers": ["console"],
                }
            },
            "disable_existing_loggers": False,
        }

        if IS_PYTHONW:
            # disable logging
            # (this should really go to a file, but file-logging is only
            # hooked up in parallel applications)
            del config["handlers"]
            del config["loggers"]

        return config

    @observe("log_datefmt", "log_format", "log_level", "logging_config")
    def _observe_logging_change(self, change: Bunch) -> None:
        # convert log level strings to ints
        log_level = self.log_level
        if isinstance(log_level, str):
            self.log_level = t.cast(int, getattr(logging, log_level))
        self._configure_logging()

    @observe("log", type="default")
    def _observe_logging_default(self, change: Bunch) -> None:
        self._configure_logging()

    def _configure_logging(self) -> None:
        config = self.get_default_logging_config()
        nested_update(config, self.logging_config or {})
        dictConfig(config)
        # make a note that we have configured logging
        self._logging_configured = True

    @default("log")
    def _log_default(self) -> AnyLogger:
        """Start logging for this application."""
        log = logging.getLogger(self.__class__.__name__)
        log.propagate = False
        _log = log  # copied from Logger.hasHandlers() (new in Python 3.2)
        while _log is not None:
            if _log.handlers:
                return log
            if not _log.propagate:
                break
            _log = _log.parent  # type:ignore[assignment]
        return log

    logging_config = Dict(
        help="""
            Configure additional log handlers.

            The default stderr logs handler is configured by the
            log_level, log_datefmt and log_format settings.

            This configuration can be used to configure additional handlers
            (e.g. to output the log to a file) or for finer control over the
            default handlers.

            If provided this should be a logging configuration dictionary, for
            more information see:
            https://docs.python.org/3/library/logging.config.html#logging-config-dictschema

            This dictionary is merged with the base logging configuration which
            defines the following:

            * A logging formatter intended for interactive use called
              ``console``.
            * A logging handler that writes to stderr called
              ``console`` which uses the formatter ``console``.
            * A logger with the name of this application set to ``DEBUG``
              level.

            This example adds a new handler that writes to a file:

            .. code-block:: python

               c.Application.logging_config = {
                   "handlers": {
                       "file": {
                           "class": "logging.FileHandler",
                           "level": "DEBUG",
                           "filename": "<path/to/file>",
                       }
                   },
                   "loggers": {
                       "<application-name>": {
                           "level": "DEBUG",
                           # NOTE: if you don't list the default "console"
                           # handler here then it will be disabled
                           "handlers": ["console", "file"],
                       },
                   },
               }

        """,
    ).tag(config=True)

    #: the alias map for configurables
    #: Keys might strings or tuples for additional options; single-letter alias accessed like `-v`.
    #: Values might be like "Class.trait" strings of two-tuples: (Class.trait, help-text),
    #  or just the "Class.trait" string, in which case the help text is inferred from the
    #  corresponding trait
    aliases: StrDict = {"log-level": "Application.log_level"}

    # flags for loading Configurables or store_const style flags
    # flags are loaded from this dict by '--key' flags
    # this must be a dict of two-tuples, the first element being the Config/dict
    # and the second being the help string for the flag
    flags: StrDict = {
        "debug": (
            {
                "Application": {
                    "log_level": logging.DEBUG,
                },
            },
            "Set log-level to debug, for the most verbose logging.",
        ),
        "show-config": (
            {
                "Application": {
                    "show_config": True,
                },
            },
            "Show the application's configuration (human-readable format)",
        ),
        "show-config-json": (
            {
                "Application": {
                    "show_config_json": True,
                },
            },
            "Show the application's configuration (json format)",
        ),
    }

    # subcommands for launching other applications
    # if this is not empty, this will be a parent Application
    # this must be a dict of two-tuples,
    # the first element being the application class/import string
    # and the second being the help string for the subcommand
    subcommands: dict[str, t.Any] | Dict[str, t.Any] = Dict()
    # parse_command_line will initialize a subapp, if requested
    subapp = Instance("traitlets.config.application.Application", allow_none=True)

    # extra command-line arguments that don't set config values
    extra_args = List(Unicode())

    cli_config = Instance(
        Config,
        (),
        {},
        help="""The subset of our configuration that came from the command-line

        We re-load this configuration after loading config files,
        to ensure that it maintains highest priority.
        """,
    )

    _loaded_config_files: List[str] = List()

    show_config = Bool(
        help="Instead of starting the Application, dump configuration to stdout"
    ).tag(config=True)

    show_config_json = Bool(
        help="Instead of starting the Application, dump configuration to stdout (as JSON)"
    ).tag(config=True)

    @observe("show_config_json")
    def _show_config_json_changed(self, change: Bunch) -> None:
        self.show_config = change.new

    @observe("show_config")
    def _show_config_changed(self, change: Bunch) -> None:
        if change.new:
            self._save_start = self.start
            self.start = self.start_show_config  # type:ignore[method-assign]

    def __init__(self, **kwargs: t.Any) -> None:
        SingletonConfigurable.__init__(self, **kwargs)
        # Ensure my class is in self.classes, so my attributes appear in command line
        # options and config files.
        cls = self.__class__
        if cls not in self.classes:
            if self.classes is cls.classes:
                # class attr, assign instead of insert
                self.classes = [cls, *self.classes]
            else:
                self.classes.insert(0, self.__class__)

    @observe("config")
    @observe_compat
    def _config_changed(self, change: Bunch) -> None:
        super()._config_changed(change)
        self.log.debug("Config changed: %r", change.new)

    @catch_config_error
    def initialize(self, argv: ArgvType = None) -> None:
        """Do the basic steps to configure me.

        Override in subclasses.
        """
        self.parse_command_line(argv)

    def start(self) -> None:
        """Start the app mainloop.

        Override in subclasses.
        """
        if self.subapp is not None:
            assert isinstance(self.subapp, Application)
            return self.subapp.start()

    def start_show_config(self) -> None:
        """start function used when show_config is True"""
        config = self.config.copy()
        # exclude show_config flags from displayed config
        for cls in self.__class__.mro():
            if cls.__name__ in config:
                cls_config = config[cls.__name__]
                cls_config.pop("show_config", None)
                cls_config.pop("show_config_json", None)

        if self.show_config_json:
            json.dump(config, sys.stdout, indent=1, sort_keys=True, default=repr)
            # add trailing newline
            sys.stdout.write("\n")
            return

        if self._loaded_config_files:
            print("Loaded config files:")
            for f in self._loaded_config_files:
                print("  " + f)
            print()

        for classname in sorted(config):
            class_config = config[classname]
            if not class_config:
                continue
            print(classname)
            pformat_kwargs: StrDict = dict(indent=4, compact=True)  # noqa: C408

            for traitname in sorted(class_config):
                value = class_config[traitname]
                print(f"  .{traitname} = {pprint.pformat(value, **pformat_kwargs)}")

    def print_alias_help(self) -> None:
        """Print the alias parts of the help."""
        print("\n".join(self.emit_alias_help()))

    def emit_alias_help(self) -> t.Generator[str, None, None]:
        """Yield the lines for alias part of the help."""
        if not self.aliases:
            return

        classdict: dict[str, type[Configurable]] = {}
        for cls in self.classes:
            # include all parents (up to, but excluding Configurable) in available names
            for c in cls.mro()[:-3]:
                classdict[c.__name__] = t.cast(t.Type[Configurable], c)

        fhelp: str | None
        for alias, longname in self.aliases.items():
            try:
                if isinstance(longname, tuple):
                    longname, fhelp = longname
                else:
                    fhelp = None
                classname, traitname = longname.split(".")[-2:]
                longname = classname + "." + traitname
                cls = classdict[classname]

                trait = cls.class_traits(config=True)[traitname]
                fhelp_lines = cls.class_get_trait_help(trait, helptext=fhelp).splitlines()

                if not isinstance(alias, tuple):  # type:ignore[unreachable]
                    alias = (alias,)  # type:ignore[assignment]
                alias = sorted(alias, key=len)  # type:ignore[assignment]
                alias = ", ".join(("--%s" if len(m) > 1 else "-%s") % m for m in alias)

                # reformat first line
                fhelp_lines[0] = fhelp_lines[0].replace("--" + longname, alias)
                yield from fhelp_lines
                yield indent("Equivalent to: [--%s]" % longname)
            except Exception as ex:
                self.log.error("Failed collecting help-message for alias %r, due to: %s", alias, ex)
                raise

    def print_flag_help(self) -> None:
        """Print the flag part of the help."""
        print("\n".join(self.emit_flag_help()))

    def emit_flag_help(self) -> t.Generator[str, None, None]:
        """Yield the lines for the flag part of the help."""
        if not self.flags:
            return

        for flags, (cfg, fhelp) in self.flags.items():
            try:
                if not isinstance(flags, tuple):  # type:ignore[unreachable]
                    flags = (flags,)  # type:ignore[assignment]
                flags = sorted(flags, key=len)  # type:ignore[assignment]
                flags = ", ".join(("--%s" if len(m) > 1 else "-%s") % m for m in flags)
                yield flags
                yield indent(dedent(fhelp.strip()))
                cfg_list = " ".join(
                    f"--{clname}.{prop}={val}"
                    for clname, props_dict in cfg.items()
                    for prop, val in props_dict.items()
                )
                cfg_txt = "Equivalent to: [%s]" % cfg_list
                yield indent(dedent(cfg_txt))
            except Exception as ex:
                self.log.error("Failed collecting help-message for flag %r, due to: %s", flags, ex)
                raise

    def print_options(self) -> None:
        """Print the options part of the help."""
        print("\n".join(self.emit_options_help()))

    def emit_options_help(self) -> t.Generator[str, None, None]:
        """Yield the lines for the options part of the help."""
        if not self.flags and not self.aliases:
            return
        header = "Options"
        yield header
        yield "=" * len(header)
        for p in wrap_paragraphs(self.option_description):
            yield p
            yield ""

        yield from self.emit_flag_help()
        yield from self.emit_alias_help()
        yield ""

    def print_subcommands(self) -> None:
        """Print the subcommand part of the help."""
        print("\n".join(self.emit_subcommands_help()))

    def emit_subcommands_help(self) -> t.Generator[str, None, None]:
        """Yield the lines for the subcommand part of the help."""
        if not self.subcommands:
            return

        header = "Subcommands"
        yield header
        yield "=" * len(header)
        for p in wrap_paragraphs(self.subcommand_description.format(app=self.name)):
            yield p
            yield ""
        for subc, (_, help) in self.subcommands.items():
            yield subc
            if help:
                yield indent(dedent(help.strip()))
        yield ""

    def emit_help_epilogue(self, classes: bool) -> t.Generator[str, None, None]:
        """Yield the very bottom lines of the help message.

        If classes=False (the default), print `--help-all` msg.
        """
        if not classes:
            yield "To see all available configurables, use `--help-all`."
            yield ""

    def print_help(self, classes: bool = False) -> None:
        """Print the help for each Configurable class in self.classes.

        If classes=False (the default), only flags and aliases are printed.
        """
        print("\n".join(self.emit_help(classes=classes)))

    def emit_help(self, classes: bool = False) -> t.Generator[str, None, None]:
        """Yield the help-lines for each Configurable class in self.classes.

        If classes=False (the default), only flags and aliases are printed.
        """
        yield from self.emit_description()
        yield from self.emit_subcommands_help()
        yield from self.emit_options_help()

        if classes:
            help_classes = self._classes_with_config_traits()
            if help_classes is not None:
                yield "Class options"
                yield "============="
                for p in wrap_paragraphs(self.keyvalue_description):
                    yield p
                    yield ""

            for cls in help_classes:
                yield cls.class_get_help()
                yield ""
        yield from self.emit_examples()

        yield from self.emit_help_epilogue(classes)

    def document_config_options(self) -> str:
        """Generate rST format documentation for the config options this application

        Returns a multiline string.
        """
        return "\n".join(c.class_config_rst_doc() for c in self._classes_inc_parents())

    def print_description(self) -> None:
        """Print the application description."""
        print("\n".join(self.emit_description()))

    def emit_description(self) -> t.Generator[str, None, None]:
        """Yield lines with the application description."""
        for p in wrap_paragraphs(self.description or self.__doc__ or ""):
            yield p
            yield ""

    def print_examples(self) -> None:
        """Print usage and examples (see `emit_examples()`)."""
        print("\n".join(self.emit_examples()))

    def emit_examples(self) -> t.Generator[str, None, None]:
        """Yield lines with the usage and examples.

        This usage string goes at the end of the command line help string
        and should contain examples of the application's usage.
        """
        if self.examples:
            yield "Examples"
            yield "--------"
            yield ""
            yield indent(dedent(self.examples.strip()))
            yield ""

    def print_version(self) -> None:
        """Print the version string."""
        print(self.version)

    @catch_config_error
    def initialize_subcommand(self, subc: str, argv: ArgvType = None) -> None:
        """Initialize a subcommand with argv."""
        val = self.subcommands.get(subc)
        assert val is not None
        subapp, _ = val

        if isinstance(subapp, str):
            subapp = import_item(subapp)

        # Cannot issubclass() on a non-type (SOhttp://stackoverflow.com/questions/8692430)
        if isinstance(subapp, type) and issubclass(subapp, Application):
            # Clear existing instances before...
            self.__class__.clear_instance()
            # instantiating subapp...
            self.subapp = subapp.instance(parent=self)
        elif callable(subapp):
            # or ask factory to create it...
            self.subapp = subapp(self)
        else:
            raise AssertionError("Invalid mappings for subcommand '%s'!" % subc)

        # ... and finally initialize subapp.
        self.subapp.initialize(argv)

    def flatten_flags(self) -> tuple[dict[str, t.Any], dict[str, t.Any]]:
        """Flatten flags and aliases for loaders, so cl-args override as expected.

        This prevents issues such as an alias pointing to InteractiveShell,
        but a config file setting the same trait in TerminalInteraciveShell
        getting inappropriate priority over the command-line arg.
        Also, loaders expect ``(key: longname)`` and not ``key: (longname, help)`` items.

        Only aliases with exactly one descendent in the class list
        will be promoted.

        """
        # build a tree of classes in our list that inherit from a particular
        # it will be a dict by parent classname of classes in our list
        # that are descendents
        mro_tree = defaultdict(list)
        for cls in self.classes:
            clsname = cls.__name__
            for parent in cls.mro()[1:-3]:
                # exclude cls itself and Configurable,HasTraits,object
                mro_tree[parent.__name__].append(clsname)
        # flatten aliases, which have the form:
        # { 'alias' : 'Class.trait' }
        aliases: dict[str, str] = {}
        for alias, longname in self.aliases.items():
            if isinstance(longname, tuple):
                longname, _ = longname
            cls, trait = longname.split(".", 1)
            children = mro_tree[cls]  # type:ignore[index]
            if len(children) == 1:
                # exactly one descendent, promote alias
                cls = children[0]  # type:ignore[assignment]
            if not isinstance(aliases, tuple):  # type:ignore[unreachable]
                alias = (alias,)  # type:ignore[assignment]
            for al in alias:
                aliases[al] = ".".join([cls, trait])  # type:ignore[list-item]

        # flatten flags, which are of the form:
        # { 'key' : ({'Cls' : {'trait' : value}}, 'help')}
        flags = {}
        for key, (flagdict, help) in self.flags.items():
            newflag: dict[t.Any, t.Any] = {}
            for cls, subdict in flagdict.items():
                children = mro_tree[cls]  # type:ignore[index]
                # exactly one descendent, promote flag section
                if len(children) == 1:
                    cls = children[0]  # type:ignore[assignment]

                if cls in newflag:
                    newflag[cls].update(subdict)
                else:
                    newflag[cls] = subdict

            if not isinstance(key, tuple):  # type:ignore[unreachable]
                key = (key,)  # type:ignore[assignment]
            for k in key:
                flags[k] = (newflag, help)
        return flags, aliases

    def _create_loader(
        self,
        argv: list[str] | None,
        aliases: StrDict,
        flags: StrDict,
        classes: ClassesType | None,
    ) -> KVArgParseConfigLoader:
        return KVArgParseConfigLoader(
            argv, aliases, flags, classes=classes, log=self.log, subcommands=self.subcommands
        )

    @classmethod
    def _get_sys_argv(cls, check_argcomplete: bool = False) -> list[str]:
        """Get `sys.argv` or equivalent from `argcomplete`

        `argcomplete`'s strategy is to call the python script with no arguments,
        so ``len(sys.argv) == 1``, and run until the `ArgumentParser` is constructed
        and determine what completions are available.

        On the other hand, `traitlet`'s subcommand-handling strategy is to check
        ``sys.argv[1]`` and see if it matches a subcommand, and if so then dynamically
        load the subcommand app and initialize it with ``sys.argv[1:]``.

        This helper method helps to take the current tokens for `argcomplete` and pass
        them through as `argv`.
        """
        if check_argcomplete and "_ARGCOMPLETE" in os.environ:
            try:
                from traitlets.config.argcomplete_config import get_argcomplete_cwords

                cwords = get_argcomplete_cwords()
                assert cwords is not None
                return cwords
            except (ImportError, ModuleNotFoundError):
                pass
        return sys.argv

    @classmethod
    def _handle_argcomplete_for_subcommand(cls) -> None:
        """Helper for `argcomplete` to recognize `traitlets` subcommands

        `argcomplete` does not know that `traitlets` has already consumed subcommands,
        as it only "sees" the final `argparse.ArgumentParser` that is constructed.
        (Indeed `KVArgParseConfigLoader` does not get passed subcommands at all currently.)
        We explicitly manipulate the environment variables used internally by `argcomplete`
        to get it to skip over the subcommand tokens.
        """
        if "_ARGCOMPLETE" not in os.environ:
            return

        try:
            from traitlets.config.argcomplete_config import increment_argcomplete_index

            increment_argcomplete_index()
        except (ImportError, ModuleNotFoundError):
            pass

    @catch_config_error
    def parse_command_line(self, argv: ArgvType = None) -> None:
        """Parse the command line arguments."""
        assert not isinstance(argv, str)
        if argv is None:
            argv = self._get_sys_argv(check_argcomplete=bool(self.subcommands))[1:]
        self.argv = [cast_unicode(arg) for arg in argv]

        if argv and argv[0] == "help":
            # turn `ipython help notebook` into `ipython notebook -h`
            argv = argv[1:] + ["-h"]

        if self.subcommands and len(argv) > 0:
            # we have subcommands, and one may have been specified
            subc, subargv = argv[0], argv[1:]
            if re.match(r"^\w(\-?\w)*$", subc) and subc in self.subcommands:
                # it's a subcommand, and *not* a flag or class parameter
                self._handle_argcomplete_for_subcommand()
                return self.initialize_subcommand(subc, subargv)

        # Arguments after a '--' argument are for the script IPython may be
        # about to run, not IPython iteslf. For arguments parsed here (help and
        # version), we want to only search the arguments up to the first
        # occurrence of '--', which we're calling interpreted_argv.
        try:
            interpreted_argv = argv[: argv.index("--")]
        except ValueError:
            interpreted_argv = argv

        if any(x in interpreted_argv for x in ("-h", "--help-all", "--help")):
            self.print_help("--help-all" in interpreted_argv)
            self.exit(0)

        if "--version" in interpreted_argv or "-V" in interpreted_argv:
            self.print_version()
            self.exit(0)

        # flatten flags&aliases, so cl-args get appropriate priority:
        flags, aliases = self.flatten_flags()
        classes = list(self._classes_with_config_traits())
        loader = self._create_loader(argv, aliases, flags, classes=classes)
        try:
            self.cli_config = deepcopy(loader.load_config())
        except SystemExit:
            # traitlets 5: no longer print help output on error
            # help output is huge, and comes after the error
            raise
        self.update_config(self.cli_config)
        # store unparsed args in extra_args
        self.extra_args = loader.extra_args

    @classmethod
    def _load_config_files(
        cls,
        basefilename: str,
        path: str | t.Sequence[str | None] | None,
        log: AnyLogger | None = None,
        raise_config_file_errors: bool = False,
    ) -> t.Generator[t.Any, None, None]:
        """Load config files (py,json) by filename and path.

        yield each config object in turn.
        """
        if isinstance(path, str) or path is None:
            path = [path]
        for current in reversed(path):
            # path list is in descending priority order, so load files backwards:
            pyloader = cls.python_config_loader_class(basefilename + ".py", path=current, log=log)
            if log:
                log.debug("Looking for %s in %s", basefilename, current or os.getcwd())
            jsonloader = cls.json_config_loader_class(basefilename + ".json", path=current, log=log)
            loaded: list[t.Any] = []
            filenames: list[str] = []
            for loader in [pyloader, jsonloader]:
                config = None
                try:
                    config = loader.load_config()
                except ConfigFileNotFound:
                    pass
                except Exception:
                    # try to get the full filename, but it will be empty in the
                    # unlikely event that the error raised before filefind finished
                    filename = loader.full_filename or basefilename
                    # problem while running the file
                    if raise_config_file_errors:
                        raise
                    if log:
                        log.error("Exception while loading config file %s", filename, exc_info=True)  # noqa: G201
                else:
                    if log:
                        log.debug("Loaded config file: %s", loader.full_filename)
                if config:
                    for filename, earlier_config in zip(filenames, loaded):
                        collisions = earlier_config.collisions(config)
                        if collisions and log:
                            log.warning(
                                "Collisions detected in {0} and {1} config files."  # noqa: G001
                                " {1} has higher priority: {2}".format(
                                    filename,
                                    loader.full_filename,
                                    json.dumps(collisions, indent=2),
                                )
                            )
                    yield (config, loader.full_filename)
                    loaded.append(config)
                    filenames.append(loader.full_filename)

    @property
    def loaded_config_files(self) -> list[str]:
        """Currently loaded configuration files"""
        return self._loaded_config_files[:]

    @catch_config_error
    def load_config_file(
        self, filename: str, path: str | t.Sequence[str | None] | None = None
    ) -> None:
        """Load config files by filename and path."""
        filename, ext = os.path.splitext(filename)
        new_config = Config()
        for config, fname in self._load_config_files(
            filename,
            path=path,
            log=self.log,
            raise_config_file_errors=self.raise_config_file_errors,
        ):
            new_config.merge(config)
            if (
                fname not in self._loaded_config_files
            ):  # only add to list of loaded files if not previously loaded
                self._loaded_config_files.append(fname)
        # add self.cli_config to preserve CLI config priority
        new_config.merge(self.cli_config)
        self.update_config(new_config)

    @catch_config_error
    def load_config_environ(self) -> None:
        """Load config files by environment."""
        PREFIX = self.name.upper().replace("-", "_")
        new_config = Config()

        self.log.debug('Looping through config variables with prefix "%s"', PREFIX)

        for k, v in os.environ.items():
            if k.startswith(PREFIX):
                self.log.debug('Seeing environ "%s"="%s"', k, v)
                # use __ instead of . as separator in env variable.
                # Warning, case sensitive !
                _, *path, key = k.split("__")
                section = new_config
                for p in path:
                    section = section[p]
                setattr(section, key, DeferredConfigString(v))

        new_config.merge(self.cli_config)
        self.update_config(new_config)

    def _classes_with_config_traits(
        self, classes: ClassesType | None = None
    ) -> t.Generator[type[Configurable], None, None]:
        """
        Yields only classes with configurable traits, and their subclasses.

        :param classes:
            The list of classes to iterate; if not set, uses :attr:`classes`.

        Thus, produced sample config-file will contain all classes
        on which a trait-value may be overridden:

        - either on the class owning the trait,
        - or on its subclasses, even if those subclasses do not define
          any traits themselves.
        """
        if classes is None:
            classes = self.classes

        cls_to_config = OrderedDict(
            (cls, bool(cls.class_own_traits(config=True)))
            for cls in self._classes_inc_parents(classes)
        )

        def is_any_parent_included(cls: t.Any) -> bool:
            return any(b in cls_to_config and cls_to_config[b] for b in cls.__bases__)

        # Mark "empty" classes for inclusion if their parents own-traits,
        #  and loop until no more classes gets marked.
        #
        while True:
            to_incl_orig = cls_to_config.copy()
            cls_to_config = OrderedDict(
                (cls, inc_yes or is_any_parent_included(cls))
                for cls, inc_yes in cls_to_config.items()
            )
            if cls_to_config == to_incl_orig:
                break
        for cl, inc_yes in cls_to_config.items():
            if inc_yes:
                yield cl

    def generate_config_file(self, classes: ClassesType | None = None) -> str:
        """generate default config file from Configurables"""
        lines = ["# Configuration file for %s." % self.name]
        lines.append("")
        lines.append("c = get_config()  #" + "noqa")
        lines.append("")
        classes = self.classes if classes is None else classes
        config_classes = list(self._classes_with_config_traits(classes))
        for cls in config_classes:
            lines.append(cls.class_config_section(config_classes))
        return "\n".join(lines)

    def close_handlers(self) -> None:
        if getattr(self, "_logging_configured", False):
            # don't attempt to close handlers unless they have been opened
            # (note accessing self.log.handlers will create handlers if they
            # have not yet been initialised)
            for handler in self.log.handlers:
                with suppress(Exception):
                    handler.close()
            self._logging_configured = False

    def exit(self, exit_status: int | str | None = 0) -> None:
        self.log.debug("Exiting application: %s", self.name)
        self.close_handlers()
        sys.exit(exit_status)

    def __del__(self) -> None:
        self.close_handlers()

    @classmethod
    def launch_instance(cls, argv: ArgvType = None, **kwargs: t.Any) -> None:
        """Launch a global instance of this Application

        If a global instance already exists, this reinitializes and starts it
        """
        app = cls.instance(**kwargs)
        app.initialize(argv)
        app.start()


# -----------------------------------------------------------------------------
# utility functions, for convenience
# -----------------------------------------------------------------------------

default_aliases = Application.aliases
default_flags = Application.flags


def boolean_flag(name: str, configurable: str, set_help: str = "", unset_help: str = "") -> StrDict:
    """Helper for building basic --trait, --no-trait flags.

    Parameters
    ----------
    name : str
        The name of the flag.
    configurable : str
        The 'Class.trait' string of the trait to be set/unset with the flag
    set_help : unicode
        help string for --name flag
    unset_help : unicode
        help string for --no-name flag

    Returns
    -------
    cfg : dict
        A dict with two keys: 'name', and 'no-name', for setting and unsetting
        the trait, respectively.
    """
    # default helpstrings
    set_help = set_help or "set %s=True" % configurable
    unset_help = unset_help or "set %s=False" % configurable

    cls, trait = configurable.split(".")

    setter = {cls: {trait: True}}
    unsetter = {cls: {trait: False}}
    return {name: (setter, set_help), "no-" + name: (unsetter, unset_help)}


def get_config() -> Config:
    """Get the config object for the global Application instance, if there is one

    otherwise return an empty config object
    """
    if Application.initialized():
        return Application.instance().config
    else:
        return Config()


if __name__ == "__main__":
    Application.launch_instance()

# === NexusCore/openenv\Lib\site-packages\nltk\internals.py ===
# Natural Language Toolkit: Internal utility functions
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
#         Nitin Madnani <nmadnani@ets.org>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import fnmatch
import locale
import os
import re
import stat
import subprocess
import sys
import textwrap
import types
import warnings
from xml.etree import ElementTree

##########################################################################
# Java Via Command-Line
##########################################################################

_java_bin = None
_java_options = []


# [xx] add classpath option to config_java?
def config_java(bin=None, options=None, verbose=False):
    """
    Configure nltk's java interface, by letting nltk know where it can
    find the Java binary, and what extra options (if any) should be
    passed to Java when it is run.

    :param bin: The full path to the Java binary.  If not specified,
        then nltk will search the system for a Java binary; and if
        one is not found, it will raise a ``LookupError`` exception.
    :type bin: str
    :param options: A list of options that should be passed to the
        Java binary when it is called.  A common value is
        ``'-Xmx512m'``, which tells Java binary to increase
        the maximum heap size to 512 megabytes.  If no options are
        specified, then do not modify the options list.
    :type options: list(str)
    """
    global _java_bin, _java_options
    _java_bin = find_binary(
        "java",
        bin,
        env_vars=["JAVAHOME", "JAVA_HOME"],
        verbose=verbose,
        binary_names=["java.exe"],
    )

    if options is not None:
        if isinstance(options, str):
            options = options.split()
        _java_options = list(options)


def java(cmd, classpath=None, stdin=None, stdout=None, stderr=None, blocking=True):
    """
    Execute the given java command, by opening a subprocess that calls
    Java.  If java has not yet been configured, it will be configured
    by calling ``config_java()`` with no arguments.

    :param cmd: The java command that should be called, formatted as
        a list of strings.  Typically, the first string will be the name
        of the java class; and the remaining strings will be arguments
        for that java class.
    :type cmd: list(str)

    :param classpath: A ``':'`` separated list of directories, JAR
        archives, and ZIP archives to search for class files.
    :type classpath: str

    :param stdin: Specify the executed program's
        standard input file handles, respectively.  Valid values are ``subprocess.PIPE``,
        an existing file descriptor (a positive integer), an existing
        file object, 'pipe', 'stdout', 'devnull' and None.  ``subprocess.PIPE`` indicates that a
        new pipe to the child should be created.  With None, no
        redirection will occur; the child's file handles will be
        inherited from the parent.  Additionally, stderr can be
        ``subprocess.STDOUT``, which indicates that the stderr data
        from the applications should be captured into the same file
        handle as for stdout.

    :param stdout: Specify the executed program's standard output file
        handle. See ``stdin`` for valid values.

    :param stderr: Specify the executed program's standard error file
        handle. See ``stdin`` for valid values.


    :param blocking: If ``false``, then return immediately after
        spawning the subprocess.  In this case, the return value is
        the ``Popen`` object, and not a ``(stdout, stderr)`` tuple.

    :return: If ``blocking=True``, then return a tuple ``(stdout,
        stderr)``, containing the stdout and stderr outputs generated
        by the java command if the ``stdout`` and ``stderr`` parameters
        were set to ``subprocess.PIPE``; or None otherwise.  If
        ``blocking=False``, then return a ``subprocess.Popen`` object.

    :raise OSError: If the java command returns a nonzero return code.
    """

    subprocess_output_dict = {
        "pipe": subprocess.PIPE,
        "stdout": subprocess.STDOUT,
        "devnull": subprocess.DEVNULL,
    }

    stdin = subprocess_output_dict.get(stdin, stdin)
    stdout = subprocess_output_dict.get(stdout, stdout)
    stderr = subprocess_output_dict.get(stderr, stderr)

    if isinstance(cmd, str):
        raise TypeError("cmd should be a list of strings")

    # Make sure we know where a java binary is.
    if _java_bin is None:
        config_java()

    # Set up the classpath.
    if isinstance(classpath, str):
        classpaths = [classpath]
    else:
        classpaths = list(classpath)
    classpath = os.path.pathsep.join(classpaths)

    # Construct the full command string.
    cmd = list(cmd)
    cmd = ["-cp", classpath] + cmd
    cmd = [_java_bin] + _java_options + cmd

    # Call java via a subprocess
    p = subprocess.Popen(cmd, stdin=stdin, stdout=stdout, stderr=stderr)
    if not blocking:
        return p
    (stdout, stderr) = p.communicate()

    # Check the return code.
    if p.returncode != 0:
        print(_decode_stdoutdata(stderr))
        raise OSError("Java command failed : " + str(cmd))

    return (stdout, stderr)


######################################################################
# Parsing
######################################################################


class ReadError(ValueError):
    """
    Exception raised by read_* functions when they fail.
    :param position: The index in the input string where an error occurred.
    :param expected: What was expected when an error occurred.
    """

    def __init__(self, expected, position):
        ValueError.__init__(self, expected, position)
        self.expected = expected
        self.position = position

    def __str__(self):
        return f"Expected {self.expected} at {self.position}"


_STRING_START_RE = re.compile(r"[uU]?[rR]?(\"\"\"|\'\'\'|\"|\')")


def read_str(s, start_position):
    """
    If a Python string literal begins at the specified position in the
    given string, then return a tuple ``(val, end_position)``
    containing the value of the string literal and the position where
    it ends.  Otherwise, raise a ``ReadError``.

    :param s: A string that will be checked to see if within which a
        Python string literal exists.
    :type s: str

    :param start_position: The specified beginning position of the string ``s``
        to begin regex matching.
    :type start_position: int

    :return: A tuple containing the matched string literal evaluated as a
        string and the end position of the string literal.
    :rtype: tuple(str, int)

    :raise ReadError: If the ``_STRING_START_RE`` regex doesn't return a
        match in ``s`` at ``start_position``, i.e., open quote. If the
        ``_STRING_END_RE`` regex doesn't return a match in ``s`` at the
        end of the first match, i.e., close quote.
    :raise ValueError: If an invalid string (i.e., contains an invalid
        escape sequence) is passed into the ``eval``.

    :Example:

    >>> from nltk.internals import read_str
    >>> read_str('"Hello", World!', 0)
    ('Hello', 7)

    """
    # Read the open quote, and any modifiers.
    m = _STRING_START_RE.match(s, start_position)
    if not m:
        raise ReadError("open quote", start_position)
    quotemark = m.group(1)

    # Find the close quote.
    _STRING_END_RE = re.compile(r"\\|%s" % quotemark)
    position = m.end()
    while True:
        match = _STRING_END_RE.search(s, position)
        if not match:
            raise ReadError("close quote", position)
        if match.group(0) == "\\":
            position = match.end() + 1
        else:
            break

    # Process it, using eval.  Strings with invalid escape sequences
    # might raise ValueError.
    try:
        return eval(s[start_position : match.end()]), match.end()
    except ValueError as e:
        raise ReadError("valid escape sequence", start_position) from e


_READ_INT_RE = re.compile(r"-?\d+")


def read_int(s, start_position):
    """
    If an integer begins at the specified position in the given
    string, then return a tuple ``(val, end_position)`` containing the
    value of the integer and the position where it ends.  Otherwise,
    raise a ``ReadError``.

    :param s: A string that will be checked to see if within which a
        Python integer exists.
    :type s: str

    :param start_position: The specified beginning position of the string ``s``
        to begin regex matching.
    :type start_position: int

    :return: A tuple containing the matched integer casted to an int,
        and the end position of the int in ``s``.
    :rtype: tuple(int, int)

    :raise ReadError: If the ``_READ_INT_RE`` regex doesn't return a
        match in ``s`` at ``start_position``.

    :Example:

    >>> from nltk.internals import read_int
    >>> read_int('42 is the answer', 0)
    (42, 2)

    """
    m = _READ_INT_RE.match(s, start_position)
    if not m:
        raise ReadError("integer", start_position)
    return int(m.group()), m.end()


_READ_NUMBER_VALUE = re.compile(r"-?(\d*)([.]?\d*)?")


def read_number(s, start_position):
    """
    If an integer or float begins at the specified position in the
    given string, then return a tuple ``(val, end_position)``
    containing the value of the number and the position where it ends.
    Otherwise, raise a ``ReadError``.

    :param s: A string that will be checked to see if within which a
        Python number exists.
    :type s: str

    :param start_position: The specified beginning position of the string ``s``
        to begin regex matching.
    :type start_position: int

    :return: A tuple containing the matched number casted to a ``float``,
        and the end position of the number in ``s``.
    :rtype: tuple(float, int)

    :raise ReadError: If the ``_READ_NUMBER_VALUE`` regex doesn't return a
        match in ``s`` at ``start_position``.

    :Example:

    >>> from nltk.internals import read_number
    >>> read_number('Pi is 3.14159', 6)
    (3.14159, 13)

    """
    m = _READ_NUMBER_VALUE.match(s, start_position)
    if not m or not (m.group(1) or m.group(2)):
        raise ReadError("number", start_position)
    if m.group(2):
        return float(m.group()), m.end()
    else:
        return int(m.group()), m.end()


######################################################################
# Check if a method has been overridden
######################################################################


def overridden(method):
    """
    :return: True if ``method`` overrides some method with the same
        name in a base class.  This is typically used when defining
        abstract base classes or interfaces, to allow subclasses to define
        either of two related methods:

        >>> class EaterI:
        ...     '''Subclass must define eat() or batch_eat().'''
        ...     def eat(self, food):
        ...         if overridden(self.batch_eat):
        ...             return self.batch_eat([food])[0]
        ...         else:
        ...             raise NotImplementedError()
        ...     def batch_eat(self, foods):
        ...         return [self.eat(food) for food in foods]

    :type method: instance method
    """
    if isinstance(method, types.MethodType) and method.__self__.__class__ is not None:
        name = method.__name__
        funcs = [
            cls.__dict__[name]
            for cls in _mro(method.__self__.__class__)
            if name in cls.__dict__
        ]
        return len(funcs) > 1
    else:
        raise TypeError("Expected an instance method.")


def _mro(cls):
    """
    Return the method resolution order for ``cls`` -- i.e., a list
    containing ``cls`` and all its base classes, in the order in which
    they would be checked by ``getattr``.  For new-style classes, this
    is just cls.__mro__.  For classic classes, this can be obtained by
    a depth-first left-to-right traversal of ``__bases__``.
    """
    if isinstance(cls, type):
        return cls.__mro__
    else:
        mro = [cls]
        for base in cls.__bases__:
            mro.extend(_mro(base))
        return mro


######################################################################
# Deprecation decorator & base class
######################################################################
# [xx] dedent msg first if it comes from  a docstring.


def _add_epytext_field(obj, field, message):
    """Add an epytext @field to a given object's docstring."""
    indent = ""
    # If we already have a docstring, then add a blank line to separate
    # it from the new field, and check its indentation.
    if obj.__doc__:
        obj.__doc__ = obj.__doc__.rstrip() + "\n\n"
        indents = re.findall(r"(?<=\n)[ ]+(?!\s)", obj.__doc__.expandtabs())
        if indents:
            indent = min(indents)
    # If we don't have a docstring, add an empty one.
    else:
        obj.__doc__ = ""

    obj.__doc__ += textwrap.fill(
        f"@{field}: {message}",
        initial_indent=indent,
        subsequent_indent=indent + "    ",
    )


def deprecated(message):
    """
    A decorator used to mark functions as deprecated.  This will cause
    a warning to be printed the when the function is used.  Usage:

        >>> from nltk.internals import deprecated
        >>> @deprecated('Use foo() instead')
        ... def bar(x):
        ...     print(x/10)

    """

    def decorator(func):
        msg = f"Function {func.__name__}() has been deprecated.  {message}"
        msg = "\n" + textwrap.fill(msg, initial_indent="  ", subsequent_indent="  ")

        def newFunc(*args, **kwargs):
            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        # Copy the old function's name, docstring, & dict
        newFunc.__dict__.update(func.__dict__)
        newFunc.__name__ = func.__name__
        newFunc.__doc__ = func.__doc__
        newFunc.__deprecated__ = True
        # Add a @deprecated field to the docstring.
        _add_epytext_field(newFunc, "deprecated", message)
        return newFunc

    return decorator


class Deprecated:
    """
    A base class used to mark deprecated classes.  A typical usage is to
    alert users that the name of a class has changed:

        >>> from nltk.internals import Deprecated
        >>> class NewClassName:
        ...     pass # All logic goes here.
        ...
        >>> class OldClassName(Deprecated, NewClassName):
        ...     "Use NewClassName instead."

    The docstring of the deprecated class will be used in the
    deprecation warning message.
    """

    def __new__(cls, *args, **kwargs):
        # Figure out which class is the deprecated one.
        dep_cls = None
        for base in _mro(cls):
            if Deprecated in base.__bases__:
                dep_cls = base
                break
        assert dep_cls, "Unable to determine which base is deprecated."

        # Construct an appropriate warning.
        doc = dep_cls.__doc__ or "".strip()
        # If there's a @deprecated field, strip off the field marker.
        doc = re.sub(r"\A\s*@deprecated:", r"", doc)
        # Strip off any indentation.
        doc = re.sub(r"(?m)^\s*", "", doc)
        # Construct a 'name' string.
        name = "Class %s" % dep_cls.__name__
        if cls != dep_cls:
            name += " (base class for %s)" % cls.__name__
        # Put it all together.
        msg = f"{name} has been deprecated.  {doc}"
        # Wrap it.
        msg = "\n" + textwrap.fill(msg, initial_indent="    ", subsequent_indent="    ")
        warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
        # Do the actual work of __new__.
        return object.__new__(cls)


##########################################################################
# COUNTER, FOR UNIQUE NAMING
##########################################################################


class Counter:
    """
    A counter that auto-increments each time its value is read.
    """

    def __init__(self, initial_value=0):
        self._value = initial_value

    def get(self):
        self._value += 1
        return self._value


##########################################################################
# Search for files/binaries
##########################################################################


def find_file_iter(
    filename,
    env_vars=(),
    searchpath=(),
    file_names=None,
    url=None,
    verbose=False,
    finding_dir=False,
):
    """
    Search for a file to be used by nltk.

    :param filename: The name or path of the file.
    :param env_vars: A list of environment variable names to check.
    :param file_names: A list of alternative file names to check.
    :param searchpath: List of directories to search.
    :param url: URL presented to user for download help.
    :param verbose: Whether or not to print path when a file is found.
    """
    file_names = [filename] + (file_names or [])
    assert isinstance(filename, str)
    assert not isinstance(file_names, str)
    assert not isinstance(searchpath, str)
    if isinstance(env_vars, str):
        env_vars = env_vars.split()
    yielded = False

    # File exists, no magic
    for alternative in file_names:
        path_to_file = os.path.join(filename, alternative)
        if os.path.isfile(path_to_file):
            if verbose:
                print(f"[Found {filename}: {path_to_file}]")
            yielded = True
            yield path_to_file
        # Check the bare alternatives
        if os.path.isfile(alternative):
            if verbose:
                print(f"[Found {filename}: {alternative}]")
            yielded = True
            yield alternative
        # Check if the alternative is inside a 'file' directory
        path_to_file = os.path.join(filename, "file", alternative)
        if os.path.isfile(path_to_file):
            if verbose:
                print(f"[Found {filename}: {path_to_file}]")
            yielded = True
            yield path_to_file

    # Check environment variables
    for env_var in env_vars:
        if env_var in os.environ:
            if finding_dir:  # This is to file a directory instead of file
                yielded = True
                yield os.environ[env_var]

            for env_dir in os.environ[env_var].split(os.pathsep):
                # Check if the environment variable contains a direct path to the bin
                if os.path.isfile(env_dir):
                    if verbose:
                        print(f"[Found {filename}: {env_dir}]")
                    yielded = True
                    yield env_dir
                # Check if the possible bin names exist inside the environment variable directories
                for alternative in file_names:
                    path_to_file = os.path.join(env_dir, alternative)
                    if os.path.isfile(path_to_file):
                        if verbose:
                            print(f"[Found {filename}: {path_to_file}]")
                        yielded = True
                        yield path_to_file
                    # Check if the alternative is inside a 'file' directory
                    # path_to_file = os.path.join(env_dir, 'file', alternative)

                    # Check if the alternative is inside a 'bin' directory
                    path_to_file = os.path.join(env_dir, "bin", alternative)

                    if os.path.isfile(path_to_file):
                        if verbose:
                            print(f"[Found {filename}: {path_to_file}]")
                        yielded = True
                        yield path_to_file

    # Check the path list.
    for directory in searchpath:
        for alternative in file_names:
            path_to_file = os.path.join(directory, alternative)
            if os.path.isfile(path_to_file):
                yielded = True
                yield path_to_file

    # If we're on a POSIX system, then try using the 'which' command
    # to find the file.
    if os.name == "posix":
        for alternative in file_names:
            try:
                p = subprocess.Popen(
                    ["which", alternative],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = p.communicate()
                path = _decode_stdoutdata(stdout).strip()
                if path.endswith(alternative) and os.path.exists(path):
                    if verbose:
                        print(f"[Found {filename}: {path}]")
                    yielded = True
                    yield path
            except (KeyboardInterrupt, SystemExit, OSError):
                raise
            finally:
                pass

    if not yielded:
        msg = (
            "NLTK was unable to find the %s file!"
            "\nUse software specific "
            "configuration parameters" % filename
        )
        if env_vars:
            msg += " or set the %s environment variable" % env_vars[0]
        msg += "."
        if searchpath:
            msg += "\n\n  Searched in:"
            msg += "".join("\n    - %s" % d for d in searchpath)
        if url:
            msg += f"\n\n  For more information on {filename}, see:\n    <{url}>"
        div = "=" * 75
        raise LookupError(f"\n\n{div}\n{msg}\n{div}")


def find_file(
    filename, env_vars=(), searchpath=(), file_names=None, url=None, verbose=False
):
    return next(
        find_file_iter(filename, env_vars, searchpath, file_names, url, verbose)
    )


def find_dir(
    filename, env_vars=(), searchpath=(), file_names=None, url=None, verbose=False
):
    return next(
        find_file_iter(
            filename, env_vars, searchpath, file_names, url, verbose, finding_dir=True
        )
    )


def find_binary_iter(
    name,
    path_to_bin=None,
    env_vars=(),
    searchpath=(),
    binary_names=None,
    url=None,
    verbose=False,
):
    """
    Search for a file to be used by nltk.

    :param name: The name or path of the file.
    :param path_to_bin: The user-supplied binary location (deprecated)
    :param env_vars: A list of environment variable names to check.
    :param file_names: A list of alternative file names to check.
    :param searchpath: List of directories to search.
    :param url: URL presented to user for download help.
    :param verbose: Whether or not to print path when a file is found.
    """
    yield from find_file_iter(
        path_to_bin or name, env_vars, searchpath, binary_names, url, verbose
    )


def find_binary(
    name,
    path_to_bin=None,
    env_vars=(),
    searchpath=(),
    binary_names=None,
    url=None,
    verbose=False,
):
    return next(
        find_binary_iter(
            name, path_to_bin, env_vars, searchpath, binary_names, url, verbose
        )
    )


def find_jar_iter(
    name_pattern,
    path_to_jar=None,
    env_vars=(),
    searchpath=(),
    url=None,
    verbose=False,
    is_regex=False,
):
    """
    Search for a jar that is used by nltk.

    :param name_pattern: The name of the jar file
    :param path_to_jar: The user-supplied jar location, or None.
    :param env_vars: A list of environment variable names to check
                     in addition to the CLASSPATH variable which is
                     checked by default.
    :param searchpath: List of directories to search.
    :param is_regex: Whether name is a regular expression.
    """

    assert isinstance(name_pattern, str)
    assert not isinstance(searchpath, str)
    if isinstance(env_vars, str):
        env_vars = env_vars.split()
    yielded = False

    # Make sure we check the CLASSPATH first
    env_vars = ["CLASSPATH"] + list(env_vars)

    # If an explicit location was given, then check it, and yield it if
    # it's present; otherwise, complain.
    if path_to_jar is not None:
        if os.path.isfile(path_to_jar):
            yielded = True
            yield path_to_jar
        else:
            raise LookupError(
                f"Could not find {name_pattern} jar file at {path_to_jar}"
            )

    # Check environment variables
    for env_var in env_vars:
        if env_var in os.environ:
            if env_var == "CLASSPATH":
                classpath = os.environ["CLASSPATH"]
                for cp in classpath.split(os.path.pathsep):
                    cp = os.path.expanduser(cp)
                    if os.path.isfile(cp):
                        filename = os.path.basename(cp)
                        if (
                            is_regex
                            and re.match(name_pattern, filename)
                            or (not is_regex and filename == name_pattern)
                        ):
                            if verbose:
                                print(f"[Found {name_pattern}: {cp}]")
                            yielded = True
                            yield cp
                    # The case where user put directory containing the jar file in the classpath
                    if os.path.isdir(cp):
                        if not is_regex:
                            if os.path.isfile(os.path.join(cp, name_pattern)):
                                if verbose:
                                    print(f"[Found {name_pattern}: {cp}]")
                                yielded = True
                                yield os.path.join(cp, name_pattern)
                        else:
                            # Look for file using regular expression
                            for file_name in os.listdir(cp):
                                if re.match(name_pattern, file_name):
                                    if verbose:
                                        print(
                                            "[Found %s: %s]"
                                            % (
                                                name_pattern,
                                                os.path.join(cp, file_name),
                                            )
                                        )
                                    yielded = True
                                    yield os.path.join(cp, file_name)

            else:
                jar_env = os.path.expanduser(os.environ[env_var])
                jar_iter = (
                    (
                        os.path.join(jar_env, path_to_jar)
                        for path_to_jar in os.listdir(jar_env)
                    )
                    if os.path.isdir(jar_env)
                    else (jar_env,)
                )
                for path_to_jar in jar_iter:
                    if os.path.isfile(path_to_jar):
                        filename = os.path.basename(path_to_jar)
                        if (
                            is_regex
                            and re.match(name_pattern, filename)
                            or (not is_regex and filename == name_pattern)
                        ):
                            if verbose:
                                print(f"[Found {name_pattern}: {path_to_jar}]")
                            yielded = True
                            yield path_to_jar

    # Check the path list.
    for directory in searchpath:
        if is_regex:
            for filename in os.listdir(directory):
                path_to_jar = os.path.join(directory, filename)
                if os.path.isfile(path_to_jar):
                    if re.match(name_pattern, filename):
                        if verbose:
                            print(f"[Found {filename}: {path_to_jar}]")
                yielded = True
                yield path_to_jar
        else:
            path_to_jar = os.path.join(directory, name_pattern)
            if os.path.isfile(path_to_jar):
                if verbose:
                    print(f"[Found {name_pattern}: {path_to_jar}]")
                yielded = True
                yield path_to_jar

    if not yielded:
        # If nothing was found, raise an error
        msg = "NLTK was unable to find %s!" % name_pattern
        if env_vars:
            msg += " Set the %s environment variable" % env_vars[0]
        msg = textwrap.fill(msg + ".", initial_indent="  ", subsequent_indent="  ")
        if searchpath:
            msg += "\n\n  Searched in:"
            msg += "".join("\n    - %s" % d for d in searchpath)
        if url:
            msg += "\n\n  For more information, on {}, see:\n    <{}>".format(
                name_pattern,
                url,
            )
        div = "=" * 75
        raise LookupError(f"\n\n{div}\n{msg}\n{div}")


def find_jar(
    name_pattern,
    path_to_jar=None,
    env_vars=(),
    searchpath=(),
    url=None,
    verbose=False,
    is_regex=False,
):
    return next(
        find_jar_iter(
            name_pattern, path_to_jar, env_vars, searchpath, url, verbose, is_regex
        )
    )


def find_jars_within_path(path_to_jars):
    return [
        os.path.join(root, filename)
        for root, dirnames, filenames in os.walk(path_to_jars)
        for filename in fnmatch.filter(filenames, "*.jar")
    ]


def _decode_stdoutdata(stdoutdata):
    """Convert data read from stdout/stderr to unicode"""
    if not isinstance(stdoutdata, bytes):
        return stdoutdata

    encoding = getattr(sys.__stdout__, "encoding", locale.getpreferredencoding())
    if encoding is None:
        return stdoutdata.decode()
    return stdoutdata.decode(encoding)


##########################################################################
# Import Stdlib Module
##########################################################################


def import_from_stdlib(module):
    """
    When python is run from within the nltk/ directory tree, the
    current directory is included at the beginning of the search path.
    Unfortunately, that means that modules within nltk can sometimes
    shadow standard library modules.  As an example, the stdlib
    'inspect' module will attempt to import the stdlib 'tokenize'
    module, but will instead end up importing NLTK's 'tokenize' module
    instead (causing the import to fail).
    """
    old_path = sys.path
    sys.path = [d for d in sys.path if d not in ("", ".")]
    m = __import__(module)
    sys.path = old_path
    return m


##########################################################################
# Wrapper for ElementTree Elements
##########################################################################


class ElementWrapper:
    """
    A wrapper around ElementTree Element objects whose main purpose is
    to provide nicer __repr__ and __str__ methods.  In addition, any
    of the wrapped Element's methods that return other Element objects
    are overridden to wrap those values before returning them.

    This makes Elements more convenient to work with in
    interactive sessions and doctests, at the expense of some
    efficiency.
    """

    # Prevent double-wrapping:
    def __new__(cls, etree):
        """
        Create and return a wrapper around a given Element object.
        If ``etree`` is an ``ElementWrapper``, then ``etree`` is
        returned as-is.
        """
        if isinstance(etree, ElementWrapper):
            return etree
        else:
            return object.__new__(ElementWrapper)

    def __init__(self, etree):
        r"""
        Initialize a new Element wrapper for ``etree``.

        If ``etree`` is a string, then it will be converted to an
        Element object using ``ElementTree.fromstring()`` first:

            >>> ElementWrapper("<test></test>")
            <Element "<?xml version='1.0' encoding='utf8'?>\n<test />">

        """
        if isinstance(etree, str):
            etree = ElementTree.fromstring(etree)
        self.__dict__["_etree"] = etree

    def unwrap(self):
        """
        Return the Element object wrapped by this wrapper.
        """
        return self._etree

    ##////////////////////////////////////////////////////////////
    # { String Representation
    ##////////////////////////////////////////////////////////////

    def __repr__(self):
        s = ElementTree.tostring(self._etree, encoding="utf8").decode("utf8")
        if len(s) > 60:
            e = s.rfind("<")
            if (len(s) - e) > 30:
                e = -20
            s = f"{s[:30]}...{s[e:]}"
        return "<Element %r>" % s

    def __str__(self):
        """
        :return: the result of applying ``ElementTree.tostring()`` to
        the wrapped Element object.
        """
        return (
            ElementTree.tostring(self._etree, encoding="utf8").decode("utf8").rstrip()
        )

    ##////////////////////////////////////////////////////////////
    # { Element interface Delegation (pass-through)
    ##////////////////////////////////////////////////////////////

    def __getattr__(self, attrib):
        return getattr(self._etree, attrib)

    def __setattr__(self, attr, value):
        return setattr(self._etree, attr, value)

    def __delattr__(self, attr):
        return delattr(self._etree, attr)

    def __setitem__(self, index, element):
        self._etree[index] = element

    def __delitem__(self, index):
        del self._etree[index]

    def __setslice__(self, start, stop, elements):
        self._etree[start:stop] = elements

    def __delslice__(self, start, stop):
        del self._etree[start:stop]

    def __len__(self):
        return len(self._etree)

    ##////////////////////////////////////////////////////////////
    # { Element interface Delegation (wrap result)
    ##////////////////////////////////////////////////////////////

    def __getitem__(self, index):
        return ElementWrapper(self._etree[index])

    def __getslice__(self, start, stop):
        return [ElementWrapper(elt) for elt in self._etree[start:stop]]

    def getchildren(self):
        return [ElementWrapper(elt) for elt in self._etree]

    def getiterator(self, tag=None):
        return (ElementWrapper(elt) for elt in self._etree.getiterator(tag))

    def makeelement(self, tag, attrib):
        return ElementWrapper(self._etree.makeelement(tag, attrib))

    def find(self, path):
        elt = self._etree.find(path)
        if elt is None:
            return elt
        else:
            return ElementWrapper(elt)

    def findall(self, path):
        return [ElementWrapper(elt) for elt in self._etree.findall(path)]


######################################################################
# Helper for Handling Slicing
######################################################################


def slice_bounds(sequence, slice_obj, allow_step=False):
    """
    Given a slice, return the corresponding (start, stop) bounds,
    taking into account None indices and negative indices.  The
    following guarantees are made for the returned start and stop values:

      - 0 <= start <= len(sequence)
      - 0 <= stop <= len(sequence)
      - start <= stop

    :raise ValueError: If ``slice_obj.step`` is not None.
    :param allow_step: If true, then the slice object may have a
        non-None step.  If it does, then return a tuple
        (start, stop, step).
    """
    start, stop = (slice_obj.start, slice_obj.stop)

    # If allow_step is true, then include the step in our return
    # value tuple.
    if allow_step:
        step = slice_obj.step
        if step is None:
            step = 1
        # Use a recursive call without allow_step to find the slice
        # bounds.  If step is negative, then the roles of start and
        # stop (in terms of default values, etc), are swapped.
        if step < 0:
            start, stop = slice_bounds(sequence, slice(stop, start))
        else:
            start, stop = slice_bounds(sequence, slice(start, stop))
        return start, stop, step

    # Otherwise, make sure that no non-default step value is used.
    elif slice_obj.step not in (None, 1):
        raise ValueError(
            "slices with steps are not supported by %s" % sequence.__class__.__name__
        )

    # Supply default offsets.
    if start is None:
        start = 0
    if stop is None:
        stop = len(sequence)

    # Handle negative indices.
    if start < 0:
        start = max(0, len(sequence) + start)
    if stop < 0:
        stop = max(0, len(sequence) + stop)

    # Make sure stop doesn't go past the end of the list.  Note that
    # we avoid calculating len(sequence) if possible, because for lazy
    # sequences, calculating the length of a sequence can be expensive.
    if stop > 0:
        try:
            sequence[stop - 1]
        except IndexError:
            stop = len(sequence)

    # Make sure start isn't past stop.
    start = min(start, stop)

    # That's all folks!
    return start, stop


######################################################################
# Permission Checking
######################################################################


def is_writable(path):
    # Ensure that it exists.
    if not os.path.exists(path):
        return False

    # If we're on a posix system, check its permissions.
    if hasattr(os, "getuid"):
        statdata = os.stat(path)
        perm = stat.S_IMODE(statdata.st_mode)
        # is it world-writable?
        if perm & 0o002:
            return True
        # do we own it?
        elif statdata.st_uid == os.getuid() and (perm & 0o200):
            return True
        # are we in a group that can write to it?
        elif (statdata.st_gid in [os.getgid()] + os.getgroups()) and (perm & 0o020):
            return True
        # otherwise, we can't write to it.
        else:
            return False

    # Otherwise, we'll assume it's writable.
    # [xx] should we do other checks on other platforms?
    return True


######################################################################
# NLTK Error reporting
######################################################################


def raise_unorderable_types(ordering, a, b):
    raise TypeError(
        "unorderable types: %s() %s %s()"
        % (type(a).__name__, ordering, type(b).__name__)
    )

# === NexusCore/openenv\Lib\site-packages\PIL\ImageCms.py ===
# The Python Imaging Library.
# $Id$

# Optional color management support, based on Kevin Cazabon's PyCMS
# library.

# Originally released under LGPL.  Graciously donated to PIL in
# March 2009, for distribution under the standard PIL license

# History:

# 2009-03-08 fl   Added to PIL.

# Copyright (C) 2002-2003 Kevin Cazabon
# Copyright (c) 2009 by Fredrik Lundh
# Copyright (c) 2013 by Eric Soroos

# See the README file for information on usage and redistribution.  See
# below for the original description.
from __future__ import annotations

import operator
import sys
from enum import IntEnum, IntFlag
from functools import reduce
from typing import Any, Literal, SupportsFloat, SupportsInt, Union

from . import Image, __version__
from ._deprecate import deprecate
from ._typing import SupportsRead

try:
    from . import _imagingcms as core

    _CmsProfileCompatible = Union[
        str, SupportsRead[bytes], core.CmsProfile, "ImageCmsProfile"
    ]
except ImportError as ex:
    # Allow error import for doc purposes, but error out when accessing
    # anything in core.
    from ._util import DeferredError

    core = DeferredError.new(ex)

_DESCRIPTION = """
pyCMS

    a Python / PIL interface to the littleCMS ICC Color Management System
    Copyright (C) 2002-2003 Kevin Cazabon
    kevin@cazabon.com
    https://www.cazabon.com

    pyCMS home page:  https://www.cazabon.com/pyCMS
    littleCMS home page:  https://www.littlecms.com
    (littleCMS is Copyright (C) 1998-2001 Marti Maria)

    Originally released under LGPL.  Graciously donated to PIL in
    March 2009, for distribution under the standard PIL license

    The pyCMS.py module provides a "clean" interface between Python/PIL and
    pyCMSdll, taking care of some of the more complex handling of the direct
    pyCMSdll functions, as well as error-checking and making sure that all
    relevant data is kept together.

    While it is possible to call pyCMSdll functions directly, it's not highly
    recommended.

    Version History:

        1.0.0 pil       Oct 2013 Port to LCMS 2.

        0.1.0 pil mod   March 10, 2009

                        Renamed display profile to proof profile. The proof
                        profile is the profile of the device that is being
                        simulated, not the profile of the device which is
                        actually used to display/print the final simulation
                        (that'd be the output profile) - also see LCMSAPI.txt
                        input colorspace -> using 'renderingIntent' -> proof
                        colorspace -> using 'proofRenderingIntent' -> output
                        colorspace

                        Added LCMS FLAGS support.
                        Added FLAGS["SOFTPROOFING"] as default flag for
                        buildProofTransform (otherwise the proof profile/intent
                        would be ignored).

        0.1.0 pil       March 2009 - added to PIL, as PIL.ImageCms

        0.0.2 alpha     Jan 6, 2002

                        Added try/except statements around type() checks of
                        potential CObjects... Python won't let you use type()
                        on them, and raises a TypeError (stupid, if you ask
                        me!)

                        Added buildProofTransformFromOpenProfiles() function.
                        Additional fixes in DLL, see DLL code for details.

        0.0.1 alpha     first public release, Dec. 26, 2002

    Known to-do list with current version (of Python interface, not pyCMSdll):

        none

"""

_VERSION = "1.0.0 pil"


def __getattr__(name: str) -> Any:
    if name == "DESCRIPTION":
        deprecate("PIL.ImageCms.DESCRIPTION", 12)
        return _DESCRIPTION
    elif name == "VERSION":
        deprecate("PIL.ImageCms.VERSION", 12)
        return _VERSION
    elif name == "FLAGS":
        deprecate("PIL.ImageCms.FLAGS", 12, "PIL.ImageCms.Flags")
        return _FLAGS
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)


# --------------------------------------------------------------------.


#
# intent/direction values


class Intent(IntEnum):
    PERCEPTUAL = 0
    RELATIVE_COLORIMETRIC = 1
    SATURATION = 2
    ABSOLUTE_COLORIMETRIC = 3


class Direction(IntEnum):
    INPUT = 0
    OUTPUT = 1
    PROOF = 2


#
# flags


class Flags(IntFlag):
    """Flags and documentation are taken from ``lcms2.h``."""

    NONE = 0
    NOCACHE = 0x0040
    """Inhibit 1-pixel cache"""
    NOOPTIMIZE = 0x0100
    """Inhibit optimizations"""
    NULLTRANSFORM = 0x0200
    """Don't transform anyway"""
    GAMUTCHECK = 0x1000
    """Out of Gamut alarm"""
    SOFTPROOFING = 0x4000
    """Do softproofing"""
    BLACKPOINTCOMPENSATION = 0x2000
    NOWHITEONWHITEFIXUP = 0x0004
    """Don't fix scum dot"""
    HIGHRESPRECALC = 0x0400
    """Use more memory to give better accuracy"""
    LOWRESPRECALC = 0x0800
    """Use less memory to minimize resources"""
    # this should be 8BITS_DEVICELINK, but that is not a valid name in Python:
    USE_8BITS_DEVICELINK = 0x0008
    """Create 8 bits devicelinks"""
    GUESSDEVICECLASS = 0x0020
    """Guess device class (for ``transform2devicelink``)"""
    KEEP_SEQUENCE = 0x0080
    """Keep profile sequence for devicelink creation"""
    FORCE_CLUT = 0x0002
    """Force CLUT optimization"""
    CLUT_POST_LINEARIZATION = 0x0001
    """create postlinearization tables if possible"""
    CLUT_PRE_LINEARIZATION = 0x0010
    """create prelinearization tables if possible"""
    NONEGATIVES = 0x8000
    """Prevent negative numbers in floating point transforms"""
    COPY_ALPHA = 0x04000000
    """Alpha channels are copied on ``cmsDoTransform()``"""
    NODEFAULTRESOURCEDEF = 0x01000000

    _GRIDPOINTS_1 = 1 << 16
    _GRIDPOINTS_2 = 2 << 16
    _GRIDPOINTS_4 = 4 << 16
    _GRIDPOINTS_8 = 8 << 16
    _GRIDPOINTS_16 = 16 << 16
    _GRIDPOINTS_32 = 32 << 16
    _GRIDPOINTS_64 = 64 << 16
    _GRIDPOINTS_128 = 128 << 16

    @staticmethod
    def GRIDPOINTS(n: int) -> Flags:
        """
        Fine-tune control over number of gridpoints

        :param n: :py:class:`int` in range ``0 <= n <= 255``
        """
        return Flags.NONE | ((n & 0xFF) << 16)


_MAX_FLAG = reduce(operator.or_, Flags)


_FLAGS = {
    "MATRIXINPUT": 1,
    "MATRIXOUTPUT": 2,
    "MATRIXONLY": (1 | 2),
    "NOWHITEONWHITEFIXUP": 4,  # Don't hot fix scum dot
    # Don't create prelinearization tables on precalculated transforms
    # (internal use):
    "NOPRELINEARIZATION": 16,
    "GUESSDEVICECLASS": 32,  # Guess device class (for transform2devicelink)
    "NOTCACHE": 64,  # Inhibit 1-pixel cache
    "NOTPRECALC": 256,
    "NULLTRANSFORM": 512,  # Don't transform anyway
    "HIGHRESPRECALC": 1024,  # Use more memory to give better accuracy
    "LOWRESPRECALC": 2048,  # Use less memory to minimize resources
    "WHITEBLACKCOMPENSATION": 8192,
    "BLACKPOINTCOMPENSATION": 8192,
    "GAMUTCHECK": 4096,  # Out of Gamut alarm
    "SOFTPROOFING": 16384,  # Do softproofing
    "PRESERVEBLACK": 32768,  # Black preservation
    "NODEFAULTRESOURCEDEF": 16777216,  # CRD special
    "GRIDPOINTS": lambda n: (n & 0xFF) << 16,  # Gridpoints
}


# --------------------------------------------------------------------.
# Experimental PIL-level API
# --------------------------------------------------------------------.

##
# Profile.


class ImageCmsProfile:
    def __init__(self, profile: str | SupportsRead[bytes] | core.CmsProfile) -> None:
        """
        :param profile: Either a string representing a filename,
            a file like object containing a profile or a
            low-level profile object

        """

        if isinstance(profile, str):
            if sys.platform == "win32":
                profile_bytes_path = profile.encode()
                try:
                    profile_bytes_path.decode("ascii")
                except UnicodeDecodeError:
                    with open(profile, "rb") as f:
                        self._set(core.profile_frombytes(f.read()))
                    return
            self._set(core.profile_open(profile), profile)
        elif hasattr(profile, "read"):
            self._set(core.profile_frombytes(profile.read()))
        elif isinstance(profile, core.CmsProfile):
            self._set(profile)
        else:
            msg = "Invalid type for Profile"  # type: ignore[unreachable]
            raise TypeError(msg)

    def _set(self, profile: core.CmsProfile, filename: str | None = None) -> None:
        self.profile = profile
        self.filename = filename
        self.product_name = None  # profile.product_name
        self.product_info = None  # profile.product_info

    def tobytes(self) -> bytes:
        """
        Returns the profile in a format suitable for embedding in
        saved images.

        :returns: a bytes object containing the ICC profile.
        """

        return core.profile_tobytes(self.profile)


class ImageCmsTransform(Image.ImagePointHandler):
    """
    Transform.  This can be used with the procedural API, or with the standard
    :py:func:`~PIL.Image.Image.point` method.

    Will return the output profile in the ``output.info['icc_profile']``.
    """

    def __init__(
        self,
        input: ImageCmsProfile,
        output: ImageCmsProfile,
        input_mode: str,
        output_mode: str,
        intent: Intent = Intent.PERCEPTUAL,
        proof: ImageCmsProfile | None = None,
        proof_intent: Intent = Intent.ABSOLUTE_COLORIMETRIC,
        flags: Flags = Flags.NONE,
    ):
        supported_modes = (
            "RGB",
            "RGBA",
            "RGBX",
            "CMYK",
            "I;16",
            "I;16L",
            "I;16B",
            "YCbCr",
            "LAB",
            "L",
            "1",
        )
        for mode in (input_mode, output_mode):
            if mode not in supported_modes:
                deprecate(
                    mode,
                    12,
                    {
                        "L;16": "I;16 or I;16L",
                        "L:16B": "I;16B",
                        "YCCA": "YCbCr",
                        "YCC": "YCbCr",
                    }.get(mode),
                )
        if proof is None:
            self.transform = core.buildTransform(
                input.profile, output.profile, input_mode, output_mode, intent, flags
            )
        else:
            self.transform = core.buildProofTransform(
                input.profile,
                output.profile,
                proof.profile,
                input_mode,
                output_mode,
                intent,
                proof_intent,
                flags,
            )
        # Note: inputMode and outputMode are for pyCMS compatibility only
        self.input_mode = self.inputMode = input_mode
        self.output_mode = self.outputMode = output_mode

        self.output_profile = output

    def point(self, im: Image.Image) -> Image.Image:
        return self.apply(im)

    def apply(self, im: Image.Image, imOut: Image.Image | None = None) -> Image.Image:
        if imOut is None:
            imOut = Image.new(self.output_mode, im.size, None)
        self.transform.apply(im.getim(), imOut.getim())
        imOut.info["icc_profile"] = self.output_profile.tobytes()
        return imOut

    def apply_in_place(self, im: Image.Image) -> Image.Image:
        if im.mode != self.output_mode:
            msg = "mode mismatch"
            raise ValueError(msg)  # wrong output mode
        self.transform.apply(im.getim(), im.getim())
        im.info["icc_profile"] = self.output_profile.tobytes()
        return im


def get_display_profile(handle: SupportsInt | None = None) -> ImageCmsProfile | None:
    """
    (experimental) Fetches the profile for the current display device.

    :returns: ``None`` if the profile is not known.
    """

    if sys.platform != "win32":
        return None

    from . import ImageWin  # type: ignore[unused-ignore, unreachable]

    if isinstance(handle, ImageWin.HDC):
        profile = core.get_display_profile_win32(int(handle), 1)
    else:
        profile = core.get_display_profile_win32(int(handle or 0))
    if profile is None:
        return None
    return ImageCmsProfile(profile)


# --------------------------------------------------------------------.
# pyCMS compatible layer
# --------------------------------------------------------------------.


class PyCMSError(Exception):
    """(pyCMS) Exception class.
    This is used for all errors in the pyCMS API."""

    pass


def profileToProfile(
    im: Image.Image,
    inputProfile: _CmsProfileCompatible,
    outputProfile: _CmsProfileCompatible,
    renderingIntent: Intent = Intent.PERCEPTUAL,
    outputMode: str | None = None,
    inPlace: bool = False,
    flags: Flags = Flags.NONE,
) -> Image.Image | None:
    """
    (pyCMS) Applies an ICC transformation to a given image, mapping from
    ``inputProfile`` to ``outputProfile``.

    If the input or output profiles specified are not valid filenames, a
    :exc:`PyCMSError` will be raised.  If ``inPlace`` is ``True`` and
    ``outputMode != im.mode``, a :exc:`PyCMSError` will be raised.
    If an error occurs during application of the profiles,
    a :exc:`PyCMSError` will be raised.
    If ``outputMode`` is not a mode supported by the ``outputProfile`` (or by pyCMS),
    a :exc:`PyCMSError` will be raised.

    This function applies an ICC transformation to im from ``inputProfile``'s
    color space to ``outputProfile``'s color space using the specified rendering
    intent to decide how to handle out-of-gamut colors.

    ``outputMode`` can be used to specify that a color mode conversion is to
    be done using these profiles, but the specified profiles must be able
    to handle that mode.  I.e., if converting im from RGB to CMYK using
    profiles, the input profile must handle RGB data, and the output
    profile must handle CMYK data.

    :param im: An open :py:class:`~PIL.Image.Image` object (i.e. Image.new(...)
        or Image.open(...), etc.)
    :param inputProfile: String, as a valid filename path to the ICC input
        profile you wish to use for this image, or a profile object
    :param outputProfile: String, as a valid filename path to the ICC output
        profile you wish to use for this image, or a profile object
    :param renderingIntent: Integer (0-3) specifying the rendering intent you
        wish to use for the transform

            ImageCms.Intent.PERCEPTUAL            = 0 (DEFAULT)
            ImageCms.Intent.RELATIVE_COLORIMETRIC = 1
            ImageCms.Intent.SATURATION            = 2
            ImageCms.Intent.ABSOLUTE_COLORIMETRIC = 3

        see the pyCMS documentation for details on rendering intents and what
        they do.
    :param outputMode: A valid PIL mode for the output image (i.e. "RGB",
        "CMYK", etc.).  Note: if rendering the image "inPlace", outputMode
        MUST be the same mode as the input, or omitted completely.  If
        omitted, the outputMode will be the same as the mode of the input
        image (im.mode)
    :param inPlace: Boolean.  If ``True``, the original image is modified in-place,
        and ``None`` is returned.  If ``False`` (default), a new
        :py:class:`~PIL.Image.Image` object is returned with the transform applied.
    :param flags: Integer (0-...) specifying additional flags
    :returns: Either None or a new :py:class:`~PIL.Image.Image` object, depending on
        the value of ``inPlace``
    :exception PyCMSError:
    """

    if outputMode is None:
        outputMode = im.mode

    if not isinstance(renderingIntent, int) or not (0 <= renderingIntent <= 3):
        msg = "renderingIntent must be an integer between 0 and 3"
        raise PyCMSError(msg)

    if not isinstance(flags, int) or not (0 <= flags <= _MAX_FLAG):
        msg = f"flags must be an integer between 0 and {_MAX_FLAG}"
        raise PyCMSError(msg)

    try:
        if not isinstance(inputProfile, ImageCmsProfile):
            inputProfile = ImageCmsProfile(inputProfile)
        if not isinstance(outputProfile, ImageCmsProfile):
            outputProfile = ImageCmsProfile(outputProfile)
        transform = ImageCmsTransform(
            inputProfile,
            outputProfile,
            im.mode,
            outputMode,
            renderingIntent,
            flags=flags,
        )
        if inPlace:
            transform.apply_in_place(im)
            imOut = None
        else:
            imOut = transform.apply(im)
    except (OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v

    return imOut


def getOpenProfile(
    profileFilename: str | SupportsRead[bytes] | core.CmsProfile,
) -> ImageCmsProfile:
    """
    (pyCMS) Opens an ICC profile file.

    The PyCMSProfile object can be passed back into pyCMS for use in creating
    transforms and such (as in ImageCms.buildTransformFromOpenProfiles()).

    If ``profileFilename`` is not a valid filename for an ICC profile,
    a :exc:`PyCMSError` will be raised.

    :param profileFilename: String, as a valid filename path to the ICC profile
        you wish to open, or a file-like object.
    :returns: A CmsProfile class object.
    :exception PyCMSError:
    """

    try:
        return ImageCmsProfile(profileFilename)
    except (OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v


def buildTransform(
    inputProfile: _CmsProfileCompatible,
    outputProfile: _CmsProfileCompatible,
    inMode: str,
    outMode: str,
    renderingIntent: Intent = Intent.PERCEPTUAL,
    flags: Flags = Flags.NONE,
) -> ImageCmsTransform:
    """
    (pyCMS) Builds an ICC transform mapping from the ``inputProfile`` to the
    ``outputProfile``. Use applyTransform to apply the transform to a given
    image.

    If the input or output profiles specified are not valid filenames, a
    :exc:`PyCMSError` will be raised. If an error occurs during creation
    of the transform, a :exc:`PyCMSError` will be raised.

    If ``inMode`` or ``outMode`` are not a mode supported by the ``outputProfile``
    (or by pyCMS), a :exc:`PyCMSError` will be raised.

    This function builds and returns an ICC transform from the ``inputProfile``
    to the ``outputProfile`` using the ``renderingIntent`` to determine what to do
    with out-of-gamut colors.  It will ONLY work for converting images that
    are in ``inMode`` to images that are in ``outMode`` color format (PIL mode,
    i.e. "RGB", "RGBA", "CMYK", etc.).

    Building the transform is a fair part of the overhead in
    ImageCms.profileToProfile(), so if you're planning on converting multiple
    images using the same input/output settings, this can save you time.
    Once you have a transform object, it can be used with
    ImageCms.applyProfile() to convert images without the need to re-compute
    the lookup table for the transform.

    The reason pyCMS returns a class object rather than a handle directly
    to the transform is that it needs to keep track of the PIL input/output
    modes that the transform is meant for.  These attributes are stored in
    the ``inMode`` and ``outMode`` attributes of the object (which can be
    manually overridden if you really want to, but I don't know of any
    time that would be of use, or would even work).

    :param inputProfile: String, as a valid filename path to the ICC input
        profile you wish to use for this transform, or a profile object
    :param outputProfile: String, as a valid filename path to the ICC output
        profile you wish to use for this transform, or a profile object
    :param inMode: String, as a valid PIL mode that the appropriate profile
        also supports (i.e. "RGB", "RGBA", "CMYK", etc.)
    :param outMode: String, as a valid PIL mode that the appropriate profile
        also supports (i.e. "RGB", "RGBA", "CMYK", etc.)
    :param renderingIntent: Integer (0-3) specifying the rendering intent you
        wish to use for the transform

            ImageCms.Intent.PERCEPTUAL            = 0 (DEFAULT)
            ImageCms.Intent.RELATIVE_COLORIMETRIC = 1
            ImageCms.Intent.SATURATION            = 2
            ImageCms.Intent.ABSOLUTE_COLORIMETRIC = 3

        see the pyCMS documentation for details on rendering intents and what
        they do.
    :param flags: Integer (0-...) specifying additional flags
    :returns: A CmsTransform class object.
    :exception PyCMSError:
    """

    if not isinstance(renderingIntent, int) or not (0 <= renderingIntent <= 3):
        msg = "renderingIntent must be an integer between 0 and 3"
        raise PyCMSError(msg)

    if not isinstance(flags, int) or not (0 <= flags <= _MAX_FLAG):
        msg = f"flags must be an integer between 0 and {_MAX_FLAG}"
        raise PyCMSError(msg)

    try:
        if not isinstance(inputProfile, ImageCmsProfile):
            inputProfile = ImageCmsProfile(inputProfile)
        if not isinstance(outputProfile, ImageCmsProfile):
            outputProfile = ImageCmsProfile(outputProfile)
        return ImageCmsTransform(
            inputProfile, outputProfile, inMode, outMode, renderingIntent, flags=flags
        )
    except (OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v


def buildProofTransform(
    inputProfile: _CmsProfileCompatible,
    outputProfile: _CmsProfileCompatible,
    proofProfile: _CmsProfileCompatible,
    inMode: str,
    outMode: str,
    renderingIntent: Intent = Intent.PERCEPTUAL,
    proofRenderingIntent: Intent = Intent.ABSOLUTE_COLORIMETRIC,
    flags: Flags = Flags.SOFTPROOFING,
) -> ImageCmsTransform:
    """
    (pyCMS) Builds an ICC transform mapping from the ``inputProfile`` to the
    ``outputProfile``, but tries to simulate the result that would be
    obtained on the ``proofProfile`` device.

    If the input, output, or proof profiles specified are not valid
    filenames, a :exc:`PyCMSError` will be raised.

    If an error occurs during creation of the transform,
    a :exc:`PyCMSError` will be raised.

    If ``inMode`` or ``outMode`` are not a mode supported by the ``outputProfile``
    (or by pyCMS), a :exc:`PyCMSError` will be raised.

    This function builds and returns an ICC transform from the ``inputProfile``
    to the ``outputProfile``, but tries to simulate the result that would be
    obtained on the ``proofProfile`` device using ``renderingIntent`` and
    ``proofRenderingIntent`` to determine what to do with out-of-gamut
    colors.  This is known as "soft-proofing".  It will ONLY work for
    converting images that are in ``inMode`` to images that are in outMode
    color format (PIL mode, i.e. "RGB", "RGBA", "CMYK", etc.).

    Usage of the resulting transform object is exactly the same as with
    ImageCms.buildTransform().

    Proof profiling is generally used when using an output device to get a
    good idea of what the final printed/displayed image would look like on
    the ``proofProfile`` device when it's quicker and easier to use the
    output device for judging color.  Generally, this means that the
    output device is a monitor, or a dye-sub printer (etc.), and the simulated
    device is something more expensive, complicated, or time consuming
    (making it difficult to make a real print for color judgement purposes).

    Soft-proofing basically functions by adjusting the colors on the
    output device to match the colors of the device being simulated. However,
    when the simulated device has a much wider gamut than the output
    device, you may obtain marginal results.

    :param inputProfile: String, as a valid filename path to the ICC input
        profile you wish to use for this transform, or a profile object
    :param outputProfile: String, as a valid filename path to the ICC output
        (monitor, usually) profile you wish to use for this transform, or a
        profile object
    :param proofProfile: String, as a valid filename path to the ICC proof
        profile you wish to use for this transform, or a profile object
    :param inMode: String, as a valid PIL mode that the appropriate profile
        also supports (i.e. "RGB", "RGBA", "CMYK", etc.)
    :param outMode: String, as a valid PIL mode that the appropriate profile
        also supports (i.e. "RGB", "RGBA", "CMYK", etc.)
    :param renderingIntent: Integer (0-3) specifying the rendering intent you
        wish to use for the input->proof (simulated) transform

            ImageCms.Intent.PERCEPTUAL            = 0 (DEFAULT)
            ImageCms.Intent.RELATIVE_COLORIMETRIC = 1
            ImageCms.Intent.SATURATION            = 2
            ImageCms.Intent.ABSOLUTE_COLORIMETRIC = 3

        see the pyCMS documentation for details on rendering intents and what
        they do.
    :param proofRenderingIntent: Integer (0-3) specifying the rendering intent
        you wish to use for proof->output transform

            ImageCms.Intent.PERCEPTUAL            = 0 (DEFAULT)
            ImageCms.Intent.RELATIVE_COLORIMETRIC = 1
            ImageCms.Intent.SATURATION            = 2
            ImageCms.Intent.ABSOLUTE_COLORIMETRIC = 3

        see the pyCMS documentation for details on rendering intents and what
        they do.
    :param flags: Integer (0-...) specifying additional flags
    :returns: A CmsTransform class object.
    :exception PyCMSError:
    """

    if not isinstance(renderingIntent, int) or not (0 <= renderingIntent <= 3):
        msg = "renderingIntent must be an integer between 0 and 3"
        raise PyCMSError(msg)

    if not isinstance(flags, int) or not (0 <= flags <= _MAX_FLAG):
        msg = f"flags must be an integer between 0 and {_MAX_FLAG}"
        raise PyCMSError(msg)

    try:
        if not isinstance(inputProfile, ImageCmsProfile):
            inputProfile = ImageCmsProfile(inputProfile)
        if not isinstance(outputProfile, ImageCmsProfile):
            outputProfile = ImageCmsProfile(outputProfile)
        if not isinstance(proofProfile, ImageCmsProfile):
            proofProfile = ImageCmsProfile(proofProfile)
        return ImageCmsTransform(
            inputProfile,
            outputProfile,
            inMode,
            outMode,
            renderingIntent,
            proofProfile,
            proofRenderingIntent,
            flags,
        )
    except (OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v


buildTransformFromOpenProfiles = buildTransform
buildProofTransformFromOpenProfiles = buildProofTransform


def applyTransform(
    im: Image.Image, transform: ImageCmsTransform, inPlace: bool = False
) -> Image.Image | None:
    """
    (pyCMS) Applies a transform to a given image.

    If ``im.mode != transform.input_mode``, a :exc:`PyCMSError` is raised.

    If ``inPlace`` is ``True`` and ``transform.input_mode != transform.output_mode``, a
    :exc:`PyCMSError` is raised.

    If ``im.mode``, ``transform.input_mode`` or ``transform.output_mode`` is not
    supported by pyCMSdll or the profiles you used for the transform, a
    :exc:`PyCMSError` is raised.

    If an error occurs while the transform is being applied,
    a :exc:`PyCMSError` is raised.

    This function applies a pre-calculated transform (from
    ImageCms.buildTransform() or ImageCms.buildTransformFromOpenProfiles())
    to an image. The transform can be used for multiple images, saving
    considerable calculation time if doing the same conversion multiple times.

    If you want to modify im in-place instead of receiving a new image as
    the return value, set ``inPlace`` to ``True``.  This can only be done if
    ``transform.input_mode`` and ``transform.output_mode`` are the same, because we
    can't change the mode in-place (the buffer sizes for some modes are
    different).  The default behavior is to return a new :py:class:`~PIL.Image.Image`
    object of the same dimensions in mode ``transform.output_mode``.

    :param im: An :py:class:`~PIL.Image.Image` object, and ``im.mode`` must be the same
        as the ``input_mode`` supported by the transform.
    :param transform: A valid CmsTransform class object
    :param inPlace: Bool.  If ``True``, ``im`` is modified in place and ``None`` is
        returned, if ``False``, a new :py:class:`~PIL.Image.Image` object with the
        transform applied is returned (and ``im`` is not changed). The default is
        ``False``.
    :returns: Either ``None``, or a new :py:class:`~PIL.Image.Image` object,
        depending on the value of ``inPlace``. The profile will be returned in
        the image's ``info['icc_profile']``.
    :exception PyCMSError:
    """

    try:
        if inPlace:
            transform.apply_in_place(im)
            imOut = None
        else:
            imOut = transform.apply(im)
    except (TypeError, ValueError) as v:
        raise PyCMSError(v) from v

    return imOut


def createProfile(
    colorSpace: Literal["LAB", "XYZ", "sRGB"], colorTemp: SupportsFloat = 0
) -> core.CmsProfile:
    """
    (pyCMS) Creates a profile.

    If colorSpace not in ``["LAB", "XYZ", "sRGB"]``,
    a :exc:`PyCMSError` is raised.

    If using LAB and ``colorTemp`` is not a positive integer,
    a :exc:`PyCMSError` is raised.

    If an error occurs while creating the profile,
    a :exc:`PyCMSError` is raised.

    Use this function to create common profiles on-the-fly instead of
    having to supply a profile on disk and knowing the path to it.  It
    returns a normal CmsProfile object that can be passed to
    ImageCms.buildTransformFromOpenProfiles() to create a transform to apply
    to images.

    :param colorSpace: String, the color space of the profile you wish to
        create.
        Currently only "LAB", "XYZ", and "sRGB" are supported.
    :param colorTemp: Positive number for the white point for the profile, in
        degrees Kelvin (i.e. 5000, 6500, 9600, etc.).  The default is for D50
        illuminant if omitted (5000k).  colorTemp is ONLY applied to LAB
        profiles, and is ignored for XYZ and sRGB.
    :returns: A CmsProfile class object
    :exception PyCMSError:
    """

    if colorSpace not in ["LAB", "XYZ", "sRGB"]:
        msg = (
            f"Color space not supported for on-the-fly profile creation ({colorSpace})"
        )
        raise PyCMSError(msg)

    if colorSpace == "LAB":
        try:
            colorTemp = float(colorTemp)
        except (TypeError, ValueError) as e:
            msg = f'Color temperature must be numeric, "{colorTemp}" not valid'
            raise PyCMSError(msg) from e

    try:
        return core.createProfile(colorSpace, colorTemp)
    except (TypeError, ValueError) as v:
        raise PyCMSError(v) from v


def getProfileName(profile: _CmsProfileCompatible) -> str:
    """

    (pyCMS) Gets the internal product name for the given profile.

    If ``profile`` isn't a valid CmsProfile object or filename to a profile,
    a :exc:`PyCMSError` is raised If an error occurs while trying
    to obtain the name tag, a :exc:`PyCMSError` is raised.

    Use this function to obtain the INTERNAL name of the profile (stored
    in an ICC tag in the profile itself), usually the one used when the
    profile was originally created.  Sometimes this tag also contains
    additional information supplied by the creator.

    :param profile: EITHER a valid CmsProfile object, OR a string of the
        filename of an ICC profile.
    :returns: A string containing the internal name of the profile as stored
        in an ICC tag.
    :exception PyCMSError:
    """

    try:
        # add an extra newline to preserve pyCMS compatibility
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        # do it in python, not c.
        #    // name was "%s - %s" (model, manufacturer) || Description ,
        #    // but if the Model and Manufacturer were the same or the model
        #    // was long, Just the model,  in 1.x
        model = profile.profile.model
        manufacturer = profile.profile.manufacturer

        if not (model or manufacturer):
            return (profile.profile.profile_description or "") + "\n"
        if not manufacturer or (model and len(model) > 30):
            return f"{model}\n"
        return f"{model} - {manufacturer}\n"

    except (AttributeError, OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v


def getProfileInfo(profile: _CmsProfileCompatible) -> str:
    """
    (pyCMS) Gets the internal product information for the given profile.

    If ``profile`` isn't a valid CmsProfile object or filename to a profile,
    a :exc:`PyCMSError` is raised.

    If an error occurs while trying to obtain the info tag,
    a :exc:`PyCMSError` is raised.

    Use this function to obtain the information stored in the profile's
    info tag.  This often contains details about the profile, and how it
    was created, as supplied by the creator.

    :param profile: EITHER a valid CmsProfile object, OR a string of the
        filename of an ICC profile.
    :returns: A string containing the internal profile information stored in
        an ICC tag.
    :exception PyCMSError:
    """

    try:
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        # add an extra newline to preserve pyCMS compatibility
        # Python, not C. the white point bits weren't working well,
        # so skipping.
        # info was description \r\n\r\n copyright \r\n\r\n K007 tag \r\n\r\n whitepoint
        description = profile.profile.profile_description
        cpright = profile.profile.copyright
        elements = [element for element in (description, cpright) if element]
        return "\r\n\r\n".join(elements) + "\r\n\r\n"

    except (AttributeError, OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v


def getProfileCopyright(profile: _CmsProfileCompatible) -> str:
    """
    (pyCMS) Gets the copyright for the given profile.

    If ``profile`` isn't a valid CmsProfile object or filename to a profile, a
    :exc:`PyCMSError` is raised.

    If an error occurs while trying to obtain the copyright tag,
    a :exc:`PyCMSError` is raised.

    Use this function to obtain the information stored in the profile's
    copyright tag.

    :param profile: EITHER a valid CmsProfile object, OR a string of the
        filename of an ICC profile.
    :returns: A string containing the internal profile information stored in
        an ICC tag.
    :exception PyCMSError:
    """
    try:
        # add an extra newline to preserve pyCMS compatibility
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        return (profile.profile.copyright or "") + "\n"
    except (AttributeError, OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v


def getProfileManufacturer(profile: _CmsProfileCompatible) -> str:
    """
    (pyCMS) Gets the manufacturer for the given profile.

    If ``profile`` isn't a valid CmsProfile object or filename to a profile, a
    :exc:`PyCMSError` is raised.

    If an error occurs while trying to obtain the manufacturer tag, a
    :exc:`PyCMSError` is raised.

    Use this function to obtain the information stored in the profile's
    manufacturer tag.

    :param profile: EITHER a valid CmsProfile object, OR a string of the
        filename of an ICC profile.
    :returns: A string containing the internal profile information stored in
        an ICC tag.
    :exception PyCMSError:
    """
    try:
        # add an extra newline to preserve pyCMS compatibility
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        return (profile.profile.manufacturer or "") + "\n"
    except (AttributeError, OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v


def getProfileModel(profile: _CmsProfileCompatible) -> str:
    """
    (pyCMS) Gets the model for the given profile.

    If ``profile`` isn't a valid CmsProfile object or filename to a profile, a
    :exc:`PyCMSError` is raised.

    If an error occurs while trying to obtain the model tag,
    a :exc:`PyCMSError` is raised.

    Use this function to obtain the information stored in the profile's
    model tag.

    :param profile: EITHER a valid CmsProfile object, OR a string of the
        filename of an ICC profile.
    :returns: A string containing the internal profile information stored in
        an ICC tag.
    :exception PyCMSError:
    """

    try:
        # add an extra newline to preserve pyCMS compatibility
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        return (profile.profile.model or "") + "\n"
    except (AttributeError, OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v


def getProfileDescription(profile: _CmsProfileCompatible) -> str:
    """
    (pyCMS) Gets the description for the given profile.

    If ``profile`` isn't a valid CmsProfile object or filename to a profile, a
    :exc:`PyCMSError` is raised.

    If an error occurs while trying to obtain the description tag,
    a :exc:`PyCMSError` is raised.

    Use this function to obtain the information stored in the profile's
    description tag.

    :param profile: EITHER a valid CmsProfile object, OR a string of the
        filename of an ICC profile.
    :returns: A string containing the internal profile information stored in an
        ICC tag.
    :exception PyCMSError:
    """

    try:
        # add an extra newline to preserve pyCMS compatibility
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        return (profile.profile.profile_description or "") + "\n"
    except (AttributeError, OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v


def getDefaultIntent(profile: _CmsProfileCompatible) -> int:
    """
    (pyCMS) Gets the default intent name for the given profile.

    If ``profile`` isn't a valid CmsProfile object or filename to a profile, a
    :exc:`PyCMSError` is raised.

    If an error occurs while trying to obtain the default intent, a
    :exc:`PyCMSError` is raised.

    Use this function to determine the default (and usually best optimized)
    rendering intent for this profile.  Most profiles support multiple
    rendering intents, but are intended mostly for one type of conversion.
    If you wish to use a different intent than returned, use
    ImageCms.isIntentSupported() to verify it will work first.

    :param profile: EITHER a valid CmsProfile object, OR a string of the
        filename of an ICC profile.
    :returns: Integer 0-3 specifying the default rendering intent for this
        profile.

            ImageCms.Intent.PERCEPTUAL            = 0 (DEFAULT)
            ImageCms.Intent.RELATIVE_COLORIMETRIC = 1
            ImageCms.Intent.SATURATION            = 2
            ImageCms.Intent.ABSOLUTE_COLORIMETRIC = 3

        see the pyCMS documentation for details on rendering intents and what
            they do.
    :exception PyCMSError:
    """

    try:
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        return profile.profile.rendering_intent
    except (AttributeError, OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v


def isIntentSupported(
    profile: _CmsProfileCompatible, intent: Intent, direction: Direction
) -> Literal[-1, 1]:
    """
    (pyCMS) Checks if a given intent is supported.

    Use this function to verify that you can use your desired
    ``intent`` with ``profile``, and that ``profile`` can be used for the
    input/output/proof profile as you desire.

    Some profiles are created specifically for one "direction", can cannot
    be used for others. Some profiles can only be used for certain
    rendering intents, so it's best to either verify this before trying
    to create a transform with them (using this function), or catch the
    potential :exc:`PyCMSError` that will occur if they don't
    support the modes you select.

    :param profile: EITHER a valid CmsProfile object, OR a string of the
        filename of an ICC profile.
    :param intent: Integer (0-3) specifying the rendering intent you wish to
        use with this profile

            ImageCms.Intent.PERCEPTUAL            = 0 (DEFAULT)
            ImageCms.Intent.RELATIVE_COLORIMETRIC = 1
            ImageCms.Intent.SATURATION            = 2
            ImageCms.Intent.ABSOLUTE_COLORIMETRIC = 3

        see the pyCMS documentation for details on rendering intents and what
            they do.
    :param direction: Integer specifying if the profile is to be used for
        input, output, or proof

            INPUT  = 0 (or use ImageCms.Direction.INPUT)
            OUTPUT = 1 (or use ImageCms.Direction.OUTPUT)
            PROOF  = 2 (or use ImageCms.Direction.PROOF)

    :returns: 1 if the intent/direction are supported, -1 if they are not.
    :exception PyCMSError:
    """

    try:
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        # FIXME: I get different results for the same data w. different
        # compilers.  Bug in LittleCMS or in the binding?
        if profile.profile.is_intent_supported(intent, direction):
            return 1
        else:
            return -1
    except (AttributeError, OSError, TypeError, ValueError) as v:
        raise PyCMSError(v) from v


def versions() -> tuple[str, str | None, str, str]:
    """
    (pyCMS) Fetches versions.
    """

    deprecate(
        "PIL.ImageCms.versions()",
        12,
        '(PIL.features.version("littlecms2"), sys.version, PIL.__version__)',
    )
    return _VERSION, core.littlecms_version, sys.version.split()[0], __version__

# === NexusCore/openenv\Lib\site-packages\pycparser\c_ast.py ===
#-----------------------------------------------------------------
# ** ATTENTION **
# This code was automatically generated from the file:
# _c_ast.cfg
#
# Do not modify it directly. Modify the configuration file and
# run the generator again.
# ** ** *** ** **
#
# pycparser: c_ast.py
#
# AST Node classes.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#-----------------------------------------------------------------


import sys

def _repr(obj):
    """
    Get the representation of an object, with dedicated pprint-like format for lists.
    """
    if isinstance(obj, list):
        return '[' + (',\n '.join((_repr(e).replace('\n', '\n ') for e in obj))) + '\n]'
    else:
        return repr(obj)

class Node(object):
    __slots__ = ()
    """ Abstract base class for AST nodes.
    """
    def __repr__(self):
        """ Generates a python representation of the current node
        """
        result = self.__class__.__name__ + '('

        indent = ''
        separator = ''
        for name in self.__slots__[:-2]:
            result += separator
            result += indent
            result += name + '=' + (_repr(getattr(self, name)).replace('\n', '\n  ' + (' ' * (len(name) + len(self.__class__.__name__)))))

            separator = ','
            indent = '\n ' + (' ' * len(self.__class__.__name__))

        result += indent + ')'

        return result

    def children(self):
        """ A sequence of all children that are Nodes
        """
        pass

    def show(self, buf=sys.stdout, offset=0, attrnames=False, nodenames=False, showcoord=False, _my_node_name=None):
        """ Pretty print the Node and all its attributes and
            children (recursively) to a buffer.

            buf:
                Open IO buffer into which the Node is printed.

            offset:
                Initial offset (amount of leading spaces)

            attrnames:
                True if you want to see the attribute names in
                name=value pairs. False to only see the values.

            nodenames:
                True if you want to see the actual node names
                within their parents.

            showcoord:
                Do you want the coordinates of each Node to be
                displayed.
        """
        lead = ' ' * offset
        if nodenames and _my_node_name is not None:
            buf.write(lead + self.__class__.__name__+ ' <' + _my_node_name + '>: ')
        else:
            buf.write(lead + self.__class__.__name__+ ': ')

        if self.attr_names:
            if attrnames:
                nvlist = [(n, getattr(self,n)) for n in self.attr_names]
                attrstr = ', '.join('%s=%s' % nv for nv in nvlist)
            else:
                vlist = [getattr(self, n) for n in self.attr_names]
                attrstr = ', '.join('%s' % v for v in vlist)
            buf.write(attrstr)

        if showcoord:
            buf.write(' (at %s)' % self.coord)
        buf.write('\n')

        for (child_name, child) in self.children():
            child.show(
                buf,
                offset=offset + 2,
                attrnames=attrnames,
                nodenames=nodenames,
                showcoord=showcoord,
                _my_node_name=child_name)


class NodeVisitor(object):
    """ A base NodeVisitor class for visiting c_ast nodes.
        Subclass it and define your own visit_XXX methods, where
        XXX is the class name you want to visit with these
        methods.

        For example:

        class ConstantVisitor(NodeVisitor):
            def __init__(self):
                self.values = []

            def visit_Constant(self, node):
                self.values.append(node.value)

        Creates a list of values of all the constant nodes
        encountered below the given node. To use it:

        cv = ConstantVisitor()
        cv.visit(node)

        Notes:

        *   generic_visit() will be called for AST nodes for which
            no visit_XXX method was defined.
        *   The children of nodes for which a visit_XXX was
            defined will not be visited - if you need this, call
            generic_visit() on the node.
            You can use:
                NodeVisitor.generic_visit(self, node)
        *   Modeled after Python's own AST visiting facilities
            (the ast module of Python 3.0)
    """

    _method_cache = None

    def visit(self, node):
        """ Visit a node.
        """

        if self._method_cache is None:
            self._method_cache = {}

        visitor = self._method_cache.get(node.__class__.__name__, None)
        if visitor is None:
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            self._method_cache[node.__class__.__name__] = visitor

        return visitor(node)

    def generic_visit(self, node):
        """ Called if no explicit visitor function exists for a
            node. Implements preorder visiting of the node.
        """
        for c in node:
            self.visit(c)

class ArrayDecl(Node):
    __slots__ = ('type', 'dim', 'dim_quals', 'coord', '__weakref__')
    def __init__(self, type, dim, dim_quals, coord=None):
        self.type = type
        self.dim = dim
        self.dim_quals = dim_quals
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        if self.dim is not None: nodelist.append(("dim", self.dim))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type
        if self.dim is not None:
            yield self.dim

    attr_names = ('dim_quals', )

class ArrayRef(Node):
    __slots__ = ('name', 'subscript', 'coord', '__weakref__')
    def __init__(self, name, subscript, coord=None):
        self.name = name
        self.subscript = subscript
        self.coord = coord

    def children(self):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        if self.subscript is not None: nodelist.append(("subscript", self.subscript))
        return tuple(nodelist)

    def __iter__(self):
        if self.name is not None:
            yield self.name
        if self.subscript is not None:
            yield self.subscript

    attr_names = ()

class Assignment(Node):
    __slots__ = ('op', 'lvalue', 'rvalue', 'coord', '__weakref__')
    def __init__(self, op, lvalue, rvalue, coord=None):
        self.op = op
        self.lvalue = lvalue
        self.rvalue = rvalue
        self.coord = coord

    def children(self):
        nodelist = []
        if self.lvalue is not None: nodelist.append(("lvalue", self.lvalue))
        if self.rvalue is not None: nodelist.append(("rvalue", self.rvalue))
        return tuple(nodelist)

    def __iter__(self):
        if self.lvalue is not None:
            yield self.lvalue
        if self.rvalue is not None:
            yield self.rvalue

    attr_names = ('op', )

class Alignas(Node):
    __slots__ = ('alignment', 'coord', '__weakref__')
    def __init__(self, alignment, coord=None):
        self.alignment = alignment
        self.coord = coord

    def children(self):
        nodelist = []
        if self.alignment is not None: nodelist.append(("alignment", self.alignment))
        return tuple(nodelist)

    def __iter__(self):
        if self.alignment is not None:
            yield self.alignment

    attr_names = ()

class BinaryOp(Node):
    __slots__ = ('op', 'left', 'right', 'coord', '__weakref__')
    def __init__(self, op, left, right, coord=None):
        self.op = op
        self.left = left
        self.right = right
        self.coord = coord

    def children(self):
        nodelist = []
        if self.left is not None: nodelist.append(("left", self.left))
        if self.right is not None: nodelist.append(("right", self.right))
        return tuple(nodelist)

    def __iter__(self):
        if self.left is not None:
            yield self.left
        if self.right is not None:
            yield self.right

    attr_names = ('op', )

class Break(Node):
    __slots__ = ('coord', '__weakref__')
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    def __iter__(self):
        return
        yield

    attr_names = ()

class Case(Node):
    __slots__ = ('expr', 'stmts', 'coord', '__weakref__')
    def __init__(self, expr, stmts, coord=None):
        self.expr = expr
        self.stmts = stmts
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(("expr", self.expr))
        for i, child in enumerate(self.stmts or []):
            nodelist.append(("stmts[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        if self.expr is not None:
            yield self.expr
        for child in (self.stmts or []):
            yield child

    attr_names = ()

class Cast(Node):
    __slots__ = ('to_type', 'expr', 'coord', '__weakref__')
    def __init__(self, to_type, expr, coord=None):
        self.to_type = to_type
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.to_type is not None: nodelist.append(("to_type", self.to_type))
        if self.expr is not None: nodelist.append(("expr", self.expr))
        return tuple(nodelist)

    def __iter__(self):
        if self.to_type is not None:
            yield self.to_type
        if self.expr is not None:
            yield self.expr

    attr_names = ()

class Compound(Node):
    __slots__ = ('block_items', 'coord', '__weakref__')
    def __init__(self, block_items, coord=None):
        self.block_items = block_items
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.block_items or []):
            nodelist.append(("block_items[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.block_items or []):
            yield child

    attr_names = ()

class CompoundLiteral(Node):
    __slots__ = ('type', 'init', 'coord', '__weakref__')
    def __init__(self, type, init, coord=None):
        self.type = type
        self.init = init
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        if self.init is not None: nodelist.append(("init", self.init))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type
        if self.init is not None:
            yield self.init

    attr_names = ()

class Constant(Node):
    __slots__ = ('type', 'value', 'coord', '__weakref__')
    def __init__(self, type, value, coord=None):
        self.type = type
        self.value = value
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    def __iter__(self):
        return
        yield

    attr_names = ('type', 'value', )

class Continue(Node):
    __slots__ = ('coord', '__weakref__')
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    def __iter__(self):
        return
        yield

    attr_names = ()

class Decl(Node):
    __slots__ = ('name', 'quals', 'align', 'storage', 'funcspec', 'type', 'init', 'bitsize', 'coord', '__weakref__')
    def __init__(self, name, quals, align, storage, funcspec, type, init, bitsize, coord=None):
        self.name = name
        self.quals = quals
        self.align = align
        self.storage = storage
        self.funcspec = funcspec
        self.type = type
        self.init = init
        self.bitsize = bitsize
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        if self.init is not None: nodelist.append(("init", self.init))
        if self.bitsize is not None: nodelist.append(("bitsize", self.bitsize))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type
        if self.init is not None:
            yield self.init
        if self.bitsize is not None:
            yield self.bitsize

    attr_names = ('name', 'quals', 'align', 'storage', 'funcspec', )

class DeclList(Node):
    __slots__ = ('decls', 'coord', '__weakref__')
    def __init__(self, decls, coord=None):
        self.decls = decls
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.decls or []):
            nodelist.append(("decls[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.decls or []):
            yield child

    attr_names = ()

class Default(Node):
    __slots__ = ('stmts', 'coord', '__weakref__')
    def __init__(self, stmts, coord=None):
        self.stmts = stmts
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.stmts or []):
            nodelist.append(("stmts[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.stmts or []):
            yield child

    attr_names = ()

class DoWhile(Node):
    __slots__ = ('cond', 'stmt', 'coord', '__weakref__')
    def __init__(self, cond, stmt, coord=None):
        self.cond = cond
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.stmt is not None: nodelist.append(("stmt", self.stmt))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.stmt is not None:
            yield self.stmt

    attr_names = ()

class EllipsisParam(Node):
    __slots__ = ('coord', '__weakref__')
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    def __iter__(self):
        return
        yield

    attr_names = ()

class EmptyStatement(Node):
    __slots__ = ('coord', '__weakref__')
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    def __iter__(self):
        return
        yield

    attr_names = ()

class Enum(Node):
    __slots__ = ('name', 'values', 'coord', '__weakref__')
    def __init__(self, name, values, coord=None):
        self.name = name
        self.values = values
        self.coord = coord

    def children(self):
        nodelist = []
        if self.values is not None: nodelist.append(("values", self.values))
        return tuple(nodelist)

    def __iter__(self):
        if self.values is not None:
            yield self.values

    attr_names = ('name', )

class Enumerator(Node):
    __slots__ = ('name', 'value', 'coord', '__weakref__')
    def __init__(self, name, value, coord=None):
        self.name = name
        self.value = value
        self.coord = coord

    def children(self):
        nodelist = []
        if self.value is not None: nodelist.append(("value", self.value))
        return tuple(nodelist)

    def __iter__(self):
        if self.value is not None:
            yield self.value

    attr_names = ('name', )

class EnumeratorList(Node):
    __slots__ = ('enumerators', 'coord', '__weakref__')
    def __init__(self, enumerators, coord=None):
        self.enumerators = enumerators
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.enumerators or []):
            nodelist.append(("enumerators[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.enumerators or []):
            yield child

    attr_names = ()

class ExprList(Node):
    __slots__ = ('exprs', 'coord', '__weakref__')
    def __init__(self, exprs, coord=None):
        self.exprs = exprs
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.exprs or []):
            nodelist.append(("exprs[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.exprs or []):
            yield child

    attr_names = ()

class FileAST(Node):
    __slots__ = ('ext', 'coord', '__weakref__')
    def __init__(self, ext, coord=None):
        self.ext = ext
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.ext or []):
            nodelist.append(("ext[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.ext or []):
            yield child

    attr_names = ()

class For(Node):
    __slots__ = ('init', 'cond', 'next', 'stmt', 'coord', '__weakref__')
    def __init__(self, init, cond, next, stmt, coord=None):
        self.init = init
        self.cond = cond
        self.next = next
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.init is not None: nodelist.append(("init", self.init))
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.next is not None: nodelist.append(("next", self.next))
        if self.stmt is not None: nodelist.append(("stmt", self.stmt))
        return tuple(nodelist)

    def __iter__(self):
        if self.init is not None:
            yield self.init
        if self.cond is not None:
            yield self.cond
        if self.next is not None:
            yield self.next
        if self.stmt is not None:
            yield self.stmt

    attr_names = ()

class FuncCall(Node):
    __slots__ = ('name', 'args', 'coord', '__weakref__')
    def __init__(self, name, args, coord=None):
        self.name = name
        self.args = args
        self.coord = coord

    def children(self):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        if self.args is not None: nodelist.append(("args", self.args))
        return tuple(nodelist)

    def __iter__(self):
        if self.name is not None:
            yield self.name
        if self.args is not None:
            yield self.args

    attr_names = ()

class FuncDecl(Node):
    __slots__ = ('args', 'type', 'coord', '__weakref__')
    def __init__(self, args, type, coord=None):
        self.args = args
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.args is not None: nodelist.append(("args", self.args))
        if self.type is not None: nodelist.append(("type", self.type))
        return tuple(nodelist)

    def __iter__(self):
        if self.args is not None:
            yield self.args
        if self.type is not None:
            yield self.type

    attr_names = ()

class FuncDef(Node):
    __slots__ = ('decl', 'param_decls', 'body', 'coord', '__weakref__')
    def __init__(self, decl, param_decls, body, coord=None):
        self.decl = decl
        self.param_decls = param_decls
        self.body = body
        self.coord = coord

    def children(self):
        nodelist = []
        if self.decl is not None: nodelist.append(("decl", self.decl))
        if self.body is not None: nodelist.append(("body", self.body))
        for i, child in enumerate(self.param_decls or []):
            nodelist.append(("param_decls[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        if self.decl is not None:
            yield self.decl
        if self.body is not None:
            yield self.body
        for child in (self.param_decls or []):
            yield child

    attr_names = ()

class Goto(Node):
    __slots__ = ('name', 'coord', '__weakref__')
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    def __iter__(self):
        return
        yield

    attr_names = ('name', )

class ID(Node):
    __slots__ = ('name', 'coord', '__weakref__')
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    def __iter__(self):
        return
        yield

    attr_names = ('name', )

class IdentifierType(Node):
    __slots__ = ('names', 'coord', '__weakref__')
    def __init__(self, names, coord=None):
        self.names = names
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    def __iter__(self):
        return
        yield

    attr_names = ('names', )

class If(Node):
    __slots__ = ('cond', 'iftrue', 'iffalse', 'coord', '__weakref__')
    def __init__(self, cond, iftrue, iffalse, coord=None):
        self.cond = cond
        self.iftrue = iftrue
        self.iffalse = iffalse
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.iftrue is not None: nodelist.append(("iftrue", self.iftrue))
        if self.iffalse is not None: nodelist.append(("iffalse", self.iffalse))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.iftrue is not None:
            yield self.iftrue
        if self.iffalse is not None:
            yield self.iffalse

    attr_names = ()

class InitList(Node):
    __slots__ = ('exprs', 'coord', '__weakref__')
    def __init__(self, exprs, coord=None):
        self.exprs = exprs
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.exprs or []):
            nodelist.append(("exprs[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.exprs or []):
            yield child

    attr_names = ()

class Label(Node):
    __slots__ = ('name', 'stmt', 'coord', '__weakref__')
    def __init__(self, name, stmt, coord=None):
        self.name = name
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.stmt is not None: nodelist.append(("stmt", self.stmt))
        return tuple(nodelist)

    def __iter__(self):
        if self.stmt is not None:
            yield self.stmt

    attr_names = ('name', )

class NamedInitializer(Node):
    __slots__ = ('name', 'expr', 'coord', '__weakref__')
    def __init__(self, name, expr, coord=None):
        self.name = name
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(("expr", self.expr))
        for i, child in enumerate(self.name or []):
            nodelist.append(("name[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        if self.expr is not None:
            yield self.expr
        for child in (self.name or []):
            yield child

    attr_names = ()

class ParamList(Node):
    __slots__ = ('params', 'coord', '__weakref__')
    def __init__(self, params, coord=None):
        self.params = params
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.params or []):
            nodelist.append(("params[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.params or []):
            yield child

    attr_names = ()

class PtrDecl(Node):
    __slots__ = ('quals', 'type', 'coord', '__weakref__')
    def __init__(self, quals, type, coord=None):
        self.quals = quals
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type

    attr_names = ('quals', )

class Return(Node):
    __slots__ = ('expr', 'coord', '__weakref__')
    def __init__(self, expr, coord=None):
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(("expr", self.expr))
        return tuple(nodelist)

    def __iter__(self):
        if self.expr is not None:
            yield self.expr

    attr_names = ()

class StaticAssert(Node):
    __slots__ = ('cond', 'message', 'coord', '__weakref__')
    def __init__(self, cond, message, coord=None):
        self.cond = cond
        self.message = message
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.message is not None: nodelist.append(("message", self.message))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.message is not None:
            yield self.message

    attr_names = ()

class Struct(Node):
    __slots__ = ('name', 'decls', 'coord', '__weakref__')
    def __init__(self, name, decls, coord=None):
        self.name = name
        self.decls = decls
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.decls or []):
            nodelist.append(("decls[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.decls or []):
            yield child

    attr_names = ('name', )

class StructRef(Node):
    __slots__ = ('name', 'type', 'field', 'coord', '__weakref__')
    def __init__(self, name, type, field, coord=None):
        self.name = name
        self.type = type
        self.field = field
        self.coord = coord

    def children(self):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        if self.field is not None: nodelist.append(("field", self.field))
        return tuple(nodelist)

    def __iter__(self):
        if self.name is not None:
            yield self.name
        if self.field is not None:
            yield self.field

    attr_names = ('type', )

class Switch(Node):
    __slots__ = ('cond', 'stmt', 'coord', '__weakref__')
    def __init__(self, cond, stmt, coord=None):
        self.cond = cond
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.stmt is not None: nodelist.append(("stmt", self.stmt))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.stmt is not None:
            yield self.stmt

    attr_names = ()

class TernaryOp(Node):
    __slots__ = ('cond', 'iftrue', 'iffalse', 'coord', '__weakref__')
    def __init__(self, cond, iftrue, iffalse, coord=None):
        self.cond = cond
        self.iftrue = iftrue
        self.iffalse = iffalse
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.iftrue is not None: nodelist.append(("iftrue", self.iftrue))
        if self.iffalse is not None: nodelist.append(("iffalse", self.iffalse))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.iftrue is not None:
            yield self.iftrue
        if self.iffalse is not None:
            yield self.iffalse

    attr_names = ()

class TypeDecl(Node):
    __slots__ = ('declname', 'quals', 'align', 'type', 'coord', '__weakref__')
    def __init__(self, declname, quals, align, type, coord=None):
        self.declname = declname
        self.quals = quals
        self.align = align
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type

    attr_names = ('declname', 'quals', 'align', )

class Typedef(Node):
    __slots__ = ('name', 'quals', 'storage', 'type', 'coord', '__weakref__')
    def __init__(self, name, quals, storage, type, coord=None):
        self.name = name
        self.quals = quals
        self.storage = storage
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type

    attr_names = ('name', 'quals', 'storage', )

class Typename(Node):
    __slots__ = ('name', 'quals', 'align', 'type', 'coord', '__weakref__')
    def __init__(self, name, quals, align, type, coord=None):
        self.name = name
        self.quals = quals
        self.align = align
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        return tuple(nodelist)

    def __iter__(self):
        if self.type is not None:
            yield self.type

    attr_names = ('name', 'quals', 'align', )

class UnaryOp(Node):
    __slots__ = ('op', 'expr', 'coord', '__weakref__')
    def __init__(self, op, expr, coord=None):
        self.op = op
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None: nodelist.append(("expr", self.expr))
        return tuple(nodelist)

    def __iter__(self):
        if self.expr is not None:
            yield self.expr

    attr_names = ('op', )

class Union(Node):
    __slots__ = ('name', 'decls', 'coord', '__weakref__')
    def __init__(self, name, decls, coord=None):
        self.name = name
        self.decls = decls
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.decls or []):
            nodelist.append(("decls[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        for child in (self.decls or []):
            yield child

    attr_names = ('name', )

class While(Node):
    __slots__ = ('cond', 'stmt', 'coord', '__weakref__')
    def __init__(self, cond, stmt, coord=None):
        self.cond = cond
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.cond is not None: nodelist.append(("cond", self.cond))
        if self.stmt is not None: nodelist.append(("stmt", self.stmt))
        return tuple(nodelist)

    def __iter__(self):
        if self.cond is not None:
            yield self.cond
        if self.stmt is not None:
            yield self.stmt

    attr_names = ()

class Pragma(Node):
    __slots__ = ('string', 'coord', '__weakref__')
    def __init__(self, string, coord=None):
        self.string = string
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    def __iter__(self):
        return
        yield

    attr_names = ('string', )


# === NexusCore/openenv\Lib\site-packages\zmq\sugar\socket.py ===
"""0MQ Socket pure Python methods."""

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import errno
import pickle
import random
import sys
from typing import (
    Any,
    Callable,
    Generic,
    List,
    Literal,
    Sequence,
    TypeVar,
    Union,
    cast,
    overload,
)
from warnings import warn

import zmq
from zmq._typing import TypeAlias
from zmq.backend import Socket as SocketBase
from zmq.error import ZMQBindError, ZMQError
from zmq.utils import jsonapi
from zmq.utils.interop import cast_int_addr

from ..constants import SocketOption, SocketType, _OptType
from .attrsettr import AttributeSetter
from .poll import Poller

try:
    DEFAULT_PROTOCOL = pickle.DEFAULT_PROTOCOL
except AttributeError:
    DEFAULT_PROTOCOL = pickle.HIGHEST_PROTOCOL

_SocketType = TypeVar("_SocketType", bound="Socket")

_JSONType: TypeAlias = "int | str | bool | list[_JSONType] | dict[str, _JSONType]"


class _SocketContext(Generic[_SocketType]):
    """Context Manager for socket bind/unbind"""

    socket: _SocketType
    kind: str
    addr: str

    def __repr__(self):
        return f"<SocketContext({self.kind}={self.addr!r})>"

    def __init__(
        self: _SocketContext[_SocketType], socket: _SocketType, kind: str, addr: str
    ):
        assert kind in {"bind", "connect"}
        self.socket = socket
        self.kind = kind
        self.addr = addr

    def __enter__(self: _SocketContext[_SocketType]) -> _SocketType:
        return self.socket

    def __exit__(self, *args):
        if self.socket.closed:
            return
        if self.kind == "bind":
            self.socket.unbind(self.addr)
        elif self.kind == "connect":
            self.socket.disconnect(self.addr)


SocketReturnType = TypeVar("SocketReturnType")


class Socket(SocketBase, AttributeSetter, Generic[SocketReturnType]):
    """The ZMQ socket object

    To create a Socket, first create a Context::

        ctx = zmq.Context.instance()

    then call ``ctx.socket(socket_type)``::

        s = ctx.socket(zmq.ROUTER)

    .. versionadded:: 25

        Sockets can now be shadowed by passing another Socket.
        This helps in creating an async copy of a sync socket or vice versa::

            s = zmq.Socket(async_socket)

        Which previously had to be::

            s = zmq.Socket.shadow(async_socket.underlying)
    """

    _shadow = False
    _shadow_obj = None
    _monitor_socket = None
    _type_name = 'UNKNOWN'

    @overload
    def __init__(
        self: Socket[bytes],
        ctx_or_socket: zmq.Context,
        socket_type: int,
        *,
        copy_threshold: int | None = None,
    ): ...

    @overload
    def __init__(
        self: Socket[bytes],
        *,
        shadow: Socket | int,
        copy_threshold: int | None = None,
    ): ...

    @overload
    def __init__(
        self: Socket[bytes],
        ctx_or_socket: Socket,
    ): ...

    def __init__(
        self: Socket[bytes],
        ctx_or_socket: zmq.Context | Socket | None = None,
        socket_type: int = 0,
        *,
        shadow: Socket | int = 0,
        copy_threshold: int | None = None,
    ):
        shadow_context: zmq.Context | None = None
        if isinstance(ctx_or_socket, zmq.Socket):
            # positional Socket(other_socket)
            shadow = ctx_or_socket
            ctx_or_socket = None

        shadow_address: int = 0

        if shadow:
            self._shadow = True
            # hold a reference to the shadow object
            self._shadow_obj = shadow
            if not isinstance(shadow, int):
                if isinstance(shadow, zmq.Socket):
                    shadow_context = shadow.context
                try:
                    shadow = cast(int, shadow.underlying)
                except AttributeError:
                    pass
            shadow_address = cast_int_addr(shadow)
        else:
            self._shadow = False

        super().__init__(
            ctx_or_socket,
            socket_type,
            shadow=shadow_address,
            copy_threshold=copy_threshold,
        )
        if self._shadow_obj and shadow_context:
            # keep self.context reference if shadowing a Socket object
            self.context = shadow_context

        try:
            socket_type = cast(int, self.get(zmq.TYPE))
        except Exception:
            pass
        else:
            try:
                self.__dict__["type"] = stype = SocketType(socket_type)
            except ValueError:
                self._type_name = str(socket_type)
            else:
                self._type_name = stype.name

    def __del__(self):
        if not self._shadow and not self.closed:
            if warn is not None:
                # warn can be None during process teardown
                warn(
                    f"Unclosed socket {self}",
                    ResourceWarning,
                    stacklevel=2,
                    source=self,
                )
            self.close()

    _repr_cls = "zmq.Socket"

    def __repr__(self):
        cls = self.__class__
        # look up _repr_cls on exact class, not inherited
        _repr_cls = cls.__dict__.get("_repr_cls", None)
        if _repr_cls is None:
            _repr_cls = f"{cls.__module__}.{cls.__name__}"

        closed = ' closed' if self._closed else ''

        return f"<{_repr_cls}(zmq.{self._type_name}) at {hex(id(self))}{closed}>"

    # socket as context manager:
    def __enter__(self: _SocketType) -> _SocketType:
        """Sockets are context managers

        .. versionadded:: 14.4
        """
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    # -------------------------------------------------------------------------
    # Socket creation
    # -------------------------------------------------------------------------

    def __copy__(self: _SocketType, memo=None) -> _SocketType:
        """Copying a Socket creates a shadow copy"""
        return self.__class__.shadow(self.underlying)

    __deepcopy__ = __copy__

    @classmethod
    def shadow(cls: type[_SocketType], address: int | zmq.Socket) -> _SocketType:
        """Shadow an existing libzmq socket

        address is a zmq.Socket or an integer (or FFI pointer)
        representing the address of the libzmq socket.

        .. versionadded:: 14.1

        .. versionadded:: 25
            Support for shadowing `zmq.Socket` objects,
            instead of just integer addresses.
        """
        return cls(shadow=address)

    def close(self, linger=None) -> None:
        """
        Close the socket.

        If linger is specified, LINGER sockopt will be set prior to closing.

        Note: closing a zmq Socket may not close the underlying sockets
        if there are undelivered messages.
        Only after all messages are delivered or discarded by reaching the socket's LINGER timeout
        (default: forever)
        will the underlying sockets be closed.

        This can be called to close the socket by hand. If this is not
        called, the socket will automatically be closed when it is
        garbage collected,
        in which case you may see a ResourceWarning about the unclosed socket.
        """
        if self.context:
            self.context._rm_socket(self)
        super().close(linger=linger)

    # -------------------------------------------------------------------------
    # Connect/Bind context managers
    # -------------------------------------------------------------------------

    def _connect_cm(self: _SocketType, addr: str) -> _SocketContext[_SocketType]:
        """Context manager to disconnect on exit

        .. versionadded:: 20.0
        """
        return _SocketContext(self, 'connect', addr)

    def _bind_cm(self: _SocketType, addr: str) -> _SocketContext[_SocketType]:
        """Context manager to unbind on exit

        .. versionadded:: 20.0
        """
        try:
            # retrieve last_endpoint
            # to support binding on random ports via
            # `socket.bind('tcp://127.0.0.1:0')`
            addr = cast(bytes, self.get(zmq.LAST_ENDPOINT)).decode("utf8")
        except (AttributeError, ZMQError, UnicodeDecodeError):
            pass
        return _SocketContext(self, 'bind', addr)

    def bind(self: _SocketType, addr: str) -> _SocketContext[_SocketType]:
        """s.bind(addr)

        Bind the socket to an address.

        This causes the socket to listen on a network port. Sockets on the
        other side of this connection will use ``Socket.connect(addr)`` to
        connect to this socket.

        Returns a context manager which will call unbind on exit.

        .. versionadded:: 20.0
            Can be used as a context manager.

        .. versionadded:: 26.0
            binding to port 0 can be used as a context manager
            for binding to a random port.
            The URL can be retrieved as `socket.last_endpoint`.

        Parameters
        ----------
        addr : str
            The address string. This has the form 'protocol://interface:port',
            for example 'tcp://127.0.0.1:5555'. Protocols supported include
            tcp, udp, pgm, epgm, inproc and ipc. If the address is unicode, it is
            encoded to utf-8 first.

        """
        try:
            super().bind(addr)
        except ZMQError as e:
            e.strerror += f" (addr={addr!r})"
            raise
        return self._bind_cm(addr)

    def connect(self: _SocketType, addr: str) -> _SocketContext[_SocketType]:
        """s.connect(addr)

        Connect to a remote 0MQ socket.

        Returns a context manager which will call disconnect on exit.

        .. versionadded:: 20.0
            Can be used as a context manager.

        Parameters
        ----------
        addr : str
            The address string. This has the form 'protocol://interface:port',
            for example 'tcp://127.0.0.1:5555'. Protocols supported are
            tcp, udp, pgm, inproc and ipc. If the address is unicode, it is
            encoded to utf-8 first.

        """
        try:
            super().connect(addr)
        except ZMQError as e:
            e.strerror += f" (addr={addr!r})"
            raise
        return self._connect_cm(addr)

    # -------------------------------------------------------------------------
    # Deprecated aliases
    # -------------------------------------------------------------------------

    @property
    def socket_type(self) -> int:
        warn("Socket.socket_type is deprecated, use Socket.type", DeprecationWarning)
        return cast(int, self.type)

    # -------------------------------------------------------------------------
    # Hooks for sockopt completion
    # -------------------------------------------------------------------------

    def __dir__(self):
        keys = dir(self.__class__)
        keys.extend(SocketOption.__members__)
        return keys

    # -------------------------------------------------------------------------
    # Getting/Setting options
    # -------------------------------------------------------------------------
    setsockopt = SocketBase.set
    getsockopt = SocketBase.get

    def __setattr__(self, key, value):
        """Override to allow setting zmq.[UN]SUBSCRIBE even though we have a subscribe method"""
        if key in self.__dict__:
            object.__setattr__(self, key, value)
            return
        _key = key.lower()
        if _key in ('subscribe', 'unsubscribe'):
            if isinstance(value, str):
                value = value.encode('utf8')
            if _key == 'subscribe':
                self.set(zmq.SUBSCRIBE, value)
            else:
                self.set(zmq.UNSUBSCRIBE, value)
            return
        super().__setattr__(key, value)

    def fileno(self) -> int:
        """Return edge-triggered file descriptor for this socket.

        This is a read-only edge-triggered file descriptor for both read and write events on this socket.
        It is important that all available events be consumed when an event is detected,
        otherwise the read event will not trigger again.

        .. versionadded:: 17.0
        """
        return self.FD

    def subscribe(self, topic: str | bytes) -> None:
        """Subscribe to a topic

        Only for SUB sockets.

        .. versionadded:: 15.3
        """
        if isinstance(topic, str):
            topic = topic.encode('utf8')
        self.set(zmq.SUBSCRIBE, topic)

    def unsubscribe(self, topic: str | bytes) -> None:
        """Unsubscribe from a topic

        Only for SUB sockets.

        .. versionadded:: 15.3
        """
        if isinstance(topic, str):
            topic = topic.encode('utf8')
        self.set(zmq.UNSUBSCRIBE, topic)

    def set_string(self, option: int, optval: str, encoding='utf-8') -> None:
        """Set socket options with a unicode object.

        This is simply a wrapper for setsockopt to protect from encoding ambiguity.

        See the 0MQ documentation for details on specific options.

        Parameters
        ----------
        option : int
            The name of the option to set. Can be any of: SUBSCRIBE,
            UNSUBSCRIBE, IDENTITY
        optval : str
            The value of the option to set.
        encoding : str
            The encoding to be used, default is utf8
        """
        if not isinstance(optval, str):
            raise TypeError(f"strings only, not {type(optval)}: {optval!r}")
        return self.set(option, optval.encode(encoding))

    setsockopt_unicode = setsockopt_string = set_string

    def get_string(self, option: int, encoding='utf-8') -> str:
        """Get the value of a socket option.

        See the 0MQ documentation for details on specific options.

        Parameters
        ----------
        option : int
            The option to retrieve.

        Returns
        -------
        optval : str
            The value of the option as a unicode string.
        """
        if SocketOption(option)._opt_type != _OptType.bytes:
            raise TypeError(f"option {option} will not return a string to be decoded")
        return cast(bytes, self.get(option)).decode(encoding)

    getsockopt_unicode = getsockopt_string = get_string

    def bind_to_random_port(
        self: _SocketType,
        addr: str,
        min_port: int = 49152,
        max_port: int = 65536,
        max_tries: int = 100,
    ) -> int:
        """Bind this socket to a random port in a range.

        If the port range is unspecified, the system will choose the port.

        Parameters
        ----------
        addr : str
            The address string without the port to pass to ``Socket.bind()``.
        min_port : int, optional
            The minimum port in the range of ports to try (inclusive).
        max_port : int, optional
            The maximum port in the range of ports to try (exclusive).
        max_tries : int, optional
            The maximum number of bind attempts to make.

        Returns
        -------
        port : int
            The port the socket was bound to.

        Raises
        ------
        ZMQBindError
            if `max_tries` reached before successful bind
        """
        if min_port == 49152 and max_port == 65536:
            # if LAST_ENDPOINT is supported, and min_port / max_port weren't specified,
            # we can bind to port 0 and let the OS do the work
            self.bind(f"{addr}:*")
            url = cast(bytes, self.last_endpoint).decode('ascii', 'replace')
            _, port_s = url.rsplit(':', 1)
            return int(port_s)

        for i in range(max_tries):
            try:
                port = random.randrange(min_port, max_port)
                self.bind(f'{addr}:{port}')
            except ZMQError as exception:
                en = exception.errno
                if en == zmq.EADDRINUSE:
                    continue
                elif sys.platform == 'win32' and en == errno.EACCES:
                    continue
                else:
                    raise
            else:
                return port
        raise ZMQBindError("Could not bind socket to random port.")

    def get_hwm(self) -> int:
        """Get the High Water Mark.

        On libzmq ≥ 3, this gets SNDHWM if available, otherwise RCVHWM
        """
        # return sndhwm, fallback on rcvhwm
        try:
            return cast(int, self.get(zmq.SNDHWM))
        except zmq.ZMQError:
            pass

        return cast(int, self.get(zmq.RCVHWM))

    def set_hwm(self, value: int) -> None:
        """Set the High Water Mark.

        On libzmq ≥ 3, this sets both SNDHWM and RCVHWM


        .. warning::

            New values only take effect for subsequent socket
            bind/connects.
        """
        raised = None
        try:
            self.sndhwm = value
        except Exception as e:
            raised = e
        try:
            self.rcvhwm = value
        except Exception as e:
            raised = e

        if raised:
            raise raised

    hwm = property(
        get_hwm,
        set_hwm,
        None,
        """Property for High Water Mark.

        Setting hwm sets both SNDHWM and RCVHWM as appropriate.
        It gets SNDHWM if available, otherwise RCVHWM.
        """,
    )

    # -------------------------------------------------------------------------
    # Sending and receiving messages
    # -------------------------------------------------------------------------

    @overload
    def send(
        self,
        data: Any,
        flags: int = ...,
        copy: bool = ...,
        *,
        track: Literal[True],
        routing_id: int | None = ...,
        group: str | None = ...,
    ) -> zmq.MessageTracker: ...

    @overload
    def send(
        self,
        data: Any,
        flags: int = ...,
        copy: bool = ...,
        *,
        track: Literal[False],
        routing_id: int | None = ...,
        group: str | None = ...,
    ) -> None: ...

    @overload
    def send(
        self,
        data: Any,
        flags: int = ...,
        *,
        copy: bool = ...,
        routing_id: int | None = ...,
        group: str | None = ...,
    ) -> None: ...

    @overload
    def send(
        self,
        data: Any,
        flags: int = ...,
        copy: bool = ...,
        track: bool = ...,
        routing_id: int | None = ...,
        group: str | None = ...,
    ) -> zmq.MessageTracker | None: ...

    def send(
        self,
        data: Any,
        flags: int = 0,
        copy: bool = True,
        track: bool = False,
        routing_id: int | None = None,
        group: str | None = None,
    ) -> zmq.MessageTracker | None:
        """Send a single zmq message frame on this socket.

        This queues the message to be sent by the IO thread at a later time.

        With flags=NOBLOCK, this raises :class:`ZMQError` if the queue is full;
        otherwise, this waits until space is available.
        See :class:`Poller` for more general non-blocking I/O.

        Parameters
        ----------
        data : bytes, Frame, memoryview
            The content of the message. This can be any object that provides
            the Python buffer API (i.e. `memoryview(data)` can be called).
        flags : int
            0, NOBLOCK, SNDMORE, or NOBLOCK|SNDMORE.
        copy : bool
            Should the message be sent in a copying or non-copying manner.
        track : bool
            Should the message be tracked for notification that ZMQ has
            finished with it? (ignored if copy=True)
        routing_id : int
            For use with SERVER sockets
        group : str
            For use with RADIO sockets

        Returns
        -------
        None : if `copy` or not track
            None if message was sent, raises an exception otherwise.
        MessageTracker : if track and not copy
            a MessageTracker object, whose `done` property will
            be False until the send is completed.

        Raises
        ------
        TypeError
            If a unicode object is passed
        ValueError
            If `track=True`, but an untracked Frame is passed.
        ZMQError
            If the send does not succeed for any reason (including
            if NOBLOCK is set and the outgoing queue is full).


        .. versionchanged:: 17.0

            DRAFT support for routing_id and group arguments.
        """
        if routing_id is not None:
            if not isinstance(data, zmq.Frame):
                data = zmq.Frame(
                    data,
                    track=track,
                    copy=copy or None,
                    copy_threshold=self.copy_threshold,
                )
            data.routing_id = routing_id
        if group is not None:
            if not isinstance(data, zmq.Frame):
                data = zmq.Frame(
                    data,
                    track=track,
                    copy=copy or None,
                    copy_threshold=self.copy_threshold,
                )
            data.group = group
        return super().send(data, flags=flags, copy=copy, track=track)

    def send_multipart(
        self,
        msg_parts: Sequence,
        flags: int = 0,
        copy: bool = True,
        track: bool = False,
        **kwargs,
    ):
        """Send a sequence of buffers as a multipart message.

        The zmq.SNDMORE flag is added to all msg parts before the last.

        Parameters
        ----------
        msg_parts : iterable
            A sequence of objects to send as a multipart message. Each element
            can be any sendable object (Frame, bytes, buffer-providers)
        flags : int, optional
            Any valid flags for :func:`Socket.send`.
            SNDMORE is added automatically for frames before the last.
        copy : bool, optional
            Should the frame(s) be sent in a copying or non-copying manner.
            If copy=False, frames smaller than self.copy_threshold bytes
            will be copied anyway.
        track : bool, optional
            Should the frame(s) be tracked for notification that ZMQ has
            finished with it (ignored if copy=True).

        Returns
        -------
        None : if copy or not track
        MessageTracker : if track and not copy
            a MessageTracker object, whose `done` property will
            be False until the last send is completed.
        """
        # typecheck parts before sending:
        for i, msg in enumerate(msg_parts):
            if isinstance(msg, (zmq.Frame, bytes, memoryview)):
                continue
            try:
                memoryview(msg)
            except Exception:
                rmsg = repr(msg)
                if len(rmsg) > 32:
                    rmsg = rmsg[:32] + '...'
                raise TypeError(
                    f"Frame {i} ({rmsg}) does not support the buffer interface."
                )
        for msg in msg_parts[:-1]:
            self.send(msg, zmq.SNDMORE | flags, copy=copy, track=track)
        # Send the last part without the extra SNDMORE flag.
        return self.send(msg_parts[-1], flags, copy=copy, track=track)

    @overload
    def recv_multipart(
        self, flags: int = ..., *, copy: Literal[True], track: bool = ...
    ) -> list[bytes]: ...

    @overload
    def recv_multipart(
        self, flags: int = ..., *, copy: Literal[False], track: bool = ...
    ) -> list[zmq.Frame]: ...

    @overload
    def recv_multipart(self, flags: int = ..., *, track: bool = ...) -> list[bytes]: ...

    @overload
    def recv_multipart(
        self, flags: int = 0, copy: bool = True, track: bool = False
    ) -> list[zmq.Frame] | list[bytes]: ...

    def recv_multipart(
        self, flags: int = 0, copy: bool = True, track: bool = False
    ) -> list[zmq.Frame] | list[bytes]:
        """Receive a multipart message as a list of bytes or Frame objects

        Parameters
        ----------
        flags : int, optional
            Any valid flags for :func:`Socket.recv`.
        copy : bool, optional
            Should the message frame(s) be received in a copying or non-copying manner?
            If False a Frame object is returned for each part, if True a copy of
            the bytes is made for each frame.
        track : bool, optional
            Should the message frame(s) be tracked for notification that ZMQ has
            finished with it? (ignored if copy=True)

        Returns
        -------
        msg_parts : list
            A list of frames in the multipart message; either Frames or bytes,
            depending on `copy`.

        Raises
        ------
        ZMQError
            for any of the reasons :func:`~Socket.recv` might fail
        """
        parts = [self.recv(flags, copy=copy, track=track)]
        # have first part already, only loop while more to receive
        while self.getsockopt(zmq.RCVMORE):
            part = self.recv(flags, copy=copy, track=track)
            parts.append(part)
        # cast List[Union] to Union[List]
        # how do we get mypy to recognize that return type is invariant on `copy`?
        return cast(Union[List[zmq.Frame], List[bytes]], parts)

    def _deserialize(
        self,
        recvd: bytes,
        load: Callable[[bytes], Any],
    ) -> Any:
        """Deserialize a received message

        Override in subclass (e.g. Futures) if recvd is not the raw bytes.

        The default implementation expects bytes and returns the deserialized message immediately.

        Parameters
        ----------

        load: callable
            Callable that deserializes bytes
        recvd:
            The object returned by self.recv

        """
        return load(recvd)

    def send_serialized(self, msg, serialize, flags=0, copy=True, **kwargs):
        """Send a message with a custom serialization function.

        .. versionadded:: 17

        Parameters
        ----------
        msg : The message to be sent. Can be any object serializable by `serialize`.
        serialize : callable
            The serialization function to use.
            serialize(msg) should return an iterable of sendable message frames
            (e.g. bytes objects), which will be passed to send_multipart.
        flags : int, optional
            Any valid flags for :func:`Socket.send`.
        copy : bool, optional
            Whether to copy the frames.

        """
        frames = serialize(msg)
        return self.send_multipart(frames, flags=flags, copy=copy, **kwargs)

    def recv_serialized(self, deserialize, flags=0, copy=True):
        """Receive a message with a custom deserialization function.

        .. versionadded:: 17

        Parameters
        ----------
        deserialize : callable
            The deserialization function to use.
            deserialize will be called with one argument: the list of frames
            returned by recv_multipart() and can return any object.
        flags : int, optional
            Any valid flags for :func:`Socket.recv`.
        copy : bool, optional
            Whether to recv bytes or Frame objects.

        Returns
        -------
        obj : object
            The object returned by the deserialization function.

        Raises
        ------
        ZMQError
            for any of the reasons :func:`~Socket.recv` might fail
        """
        frames = self.recv_multipart(flags=flags, copy=copy)
        return self._deserialize(frames, deserialize)

    def send_string(
        self,
        u: str,
        flags: int = 0,
        copy: bool = True,
        encoding: str = 'utf-8',
        **kwargs,
    ) -> zmq.Frame | None:
        """Send a Python unicode string as a message with an encoding.

        0MQ communicates with raw bytes, so you must encode/decode
        text (str) around 0MQ.

        Parameters
        ----------
        u : str
            The unicode string to send.
        flags : int, optional
            Any valid flags for :func:`Socket.send`.
        encoding : str
            The encoding to be used
        """
        if not isinstance(u, str):
            raise TypeError("str objects only")
        return self.send(u.encode(encoding), flags=flags, copy=copy, **kwargs)

    send_unicode = send_string

    def recv_string(self, flags: int = 0, encoding: str = 'utf-8') -> str:
        """Receive a unicode string, as sent by send_string.

        Parameters
        ----------
        flags : int
            Any valid flags for :func:`Socket.recv`.
        encoding : str
            The encoding to be used

        Returns
        -------
        s : str
            The Python unicode string that arrives as encoded bytes.

        Raises
        ------
        ZMQError
            for any of the reasons :func:`Socket.recv` might fail
        """
        msg = self.recv(flags=flags)
        return self._deserialize(msg, lambda buf: buf.decode(encoding))

    recv_unicode = recv_string

    def send_pyobj(
        self, obj: Any, flags: int = 0, protocol: int = DEFAULT_PROTOCOL, **kwargs
    ) -> zmq.Frame | None:
        """
        Send a Python object as a message using pickle to serialize.

        .. warning::

            Never deserialize an untrusted message with pickle,
            which can involve arbitrary code execution.
            Make sure to authenticate the sources of messages
            before unpickling them, e.g. with transport-level security
            (e.g. CURVE, ZAP, or IPC permissions)
            or signed messages.

        Parameters
        ----------
        obj : Python object
            The Python object to send.
        flags : int
            Any valid flags for :func:`Socket.send`.
        protocol : int
            The pickle protocol number to use. The default is pickle.DEFAULT_PROTOCOL
            where defined, and pickle.HIGHEST_PROTOCOL elsewhere.
        """
        msg = pickle.dumps(obj, protocol)
        return self.send(msg, flags=flags, **kwargs)

    def recv_pyobj(self, flags: int = 0) -> Any:
        """
        Receive a Python object as a message using UNSAFE pickle to serialize.

        .. warning::

            Never deserialize an untrusted message with pickle,
            which can involve arbitrary code execution.
            Make sure to authenticate the sources of messages
            before unpickling them, e.g. with transport-level security
            (such as CURVE or IPC permissions)
            or authenticating messages themselves before deserializing.

        Parameters
        ----------
        flags : int
            Any valid flags for :func:`Socket.recv`.

        Returns
        -------
        obj : Python object
            The Python object that arrives as a message.

        Raises
        ------
        ZMQError
            for any of the reasons :func:`~Socket.recv` might fail
        """
        msg = self.recv(flags)
        return self._deserialize(msg, pickle.loads)

    def send_json(self, obj: Any, flags: int = 0, **kwargs) -> None:
        """Send a Python object as a message using json to serialize.

        Keyword arguments are passed on to json.dumps

        Parameters
        ----------
        obj : Python object
            The Python object to send
        flags : int
            Any valid flags for :func:`Socket.send`
        """
        send_kwargs = {}
        for key in ('routing_id', 'group'):
            if key in kwargs:
                send_kwargs[key] = kwargs.pop(key)
        msg = jsonapi.dumps(obj, **kwargs)
        return self.send(msg, flags=flags, **send_kwargs)

    def recv_json(self, flags: int = 0, **kwargs) -> _JSONType:
        """Receive a Python object as a message using json to serialize.

        Keyword arguments are passed on to json.loads

        Parameters
        ----------
        flags : int
            Any valid flags for :func:`Socket.recv`.

        Returns
        -------
        obj : Python object
            The Python object that arrives as a message.

        Raises
        ------
        ZMQError
            for any of the reasons :func:`~Socket.recv` might fail
        """
        msg = self.recv(flags)
        return self._deserialize(msg, lambda buf: jsonapi.loads(buf, **kwargs))

    _poller_class = Poller

    def poll(self, timeout: int | None = None, flags: int = zmq.POLLIN) -> int:
        """Poll the socket for events.

        See :class:`Poller` to wait for multiple sockets at once.

        Parameters
        ----------
        timeout : int
            The timeout (in milliseconds) to wait for an event. If unspecified
            (or specified None), will wait forever for an event.
        flags : int
            default: POLLIN.
            POLLIN, POLLOUT, or POLLIN|POLLOUT. The event flags to poll for.

        Returns
        -------
        event_mask : int
            The poll event mask (POLLIN, POLLOUT),
            0 if the timeout was reached without an event.
        """

        if self.closed:
            raise ZMQError(zmq.ENOTSUP)

        p = self._poller_class()
        p.register(self, flags)
        evts = dict(p.poll(timeout))
        # return 0 if no events, otherwise return event bitfield
        return evts.get(self, 0)

    def get_monitor_socket(
        self: _SocketType, events: int | None = None, addr: str | None = None
    ) -> _SocketType:
        """Return a connected PAIR socket ready to receive the event notifications.

        .. versionadded:: libzmq-4.0
        .. versionadded:: 14.0

        Parameters
        ----------
        events : int
            default: `zmq.EVENT_ALL`
            The bitmask defining which events are wanted.
        addr : str
            The optional endpoint for the monitoring sockets.

        Returns
        -------
        socket : zmq.Socket
            The PAIR socket, connected and ready to receive messages.
        """
        # safe-guard, method only available on libzmq >= 4
        if zmq.zmq_version_info() < (4,):
            raise NotImplementedError(
                f"get_monitor_socket requires libzmq >= 4, have {zmq.zmq_version()}"
            )

        # if already monitoring, return existing socket
        if self._monitor_socket:
            if self._monitor_socket.closed:
                self._monitor_socket = None
            else:
                return self._monitor_socket

        if addr is None:
            # create endpoint name from internal fd
            addr = f"inproc://monitor.s-{self.FD}"
        if events is None:
            # use all events
            events = zmq.EVENT_ALL
        # attach monitoring socket
        self.monitor(addr, events)
        # create new PAIR socket and connect it
        self._monitor_socket = self.context.socket(zmq.PAIR)
        self._monitor_socket.connect(addr)
        return self._monitor_socket

    def disable_monitor(self) -> None:
        """Shutdown the PAIR socket (created using get_monitor_socket)
        that is serving socket events.

        .. versionadded:: 14.4
        """
        self._monitor_socket = None
        self.monitor(None, 0)


SyncSocket: TypeAlias = Socket[bytes]

__all__ = ['Socket', 'SyncSocket']

# === NexusCore/openenv\Lib\site-packages\tornado\test\gen_test.py ===
import asyncio
from concurrent import futures
import gc
import datetime
import platform
import sys
import time
import weakref
import unittest

from tornado.concurrent import Future
from tornado.log import app_log
from tornado.testing import AsyncHTTPTestCase, AsyncTestCase, ExpectLog, gen_test
from tornado.test.util import skipNotCPython
from tornado.web import Application, RequestHandler, HTTPError

from tornado import gen

try:
    import contextvars
except ImportError:
    contextvars = None  # type: ignore

import typing

if typing.TYPE_CHECKING:
    from typing import List, Optional  # noqa: F401


class GenBasicTest(AsyncTestCase):
    @gen.coroutine
    def delay(self, iterations, arg):
        """Returns arg after a number of IOLoop iterations."""
        for i in range(iterations):
            yield gen.moment
        raise gen.Return(arg)

    @gen.coroutine
    def async_future(self, result):
        yield gen.moment
        return result

    @gen.coroutine
    def async_exception(self, e):
        yield gen.moment
        raise e

    @gen.coroutine
    def add_one_async(self, x):
        yield gen.moment
        raise gen.Return(x + 1)

    def test_no_yield(self):
        @gen.coroutine
        def f():
            pass

        self.io_loop.run_sync(f)

    def test_exception_phase1(self):
        @gen.coroutine
        def f():
            1 / 0

        self.assertRaises(ZeroDivisionError, self.io_loop.run_sync, f)

    def test_exception_phase2(self):
        @gen.coroutine
        def f():
            yield gen.moment
            1 / 0

        self.assertRaises(ZeroDivisionError, self.io_loop.run_sync, f)

    def test_bogus_yield(self):
        @gen.coroutine
        def f():
            yield 42

        self.assertRaises(gen.BadYieldError, self.io_loop.run_sync, f)

    def test_bogus_yield_tuple(self):
        @gen.coroutine
        def f():
            yield (1, 2)

        self.assertRaises(gen.BadYieldError, self.io_loop.run_sync, f)

    def test_reuse(self):
        @gen.coroutine
        def f():
            yield gen.moment

        self.io_loop.run_sync(f)
        self.io_loop.run_sync(f)

    def test_none(self):
        @gen.coroutine
        def f():
            yield None

        self.io_loop.run_sync(f)

    def test_multi(self):
        @gen.coroutine
        def f():
            results = yield [self.add_one_async(1), self.add_one_async(2)]
            self.assertEqual(results, [2, 3])

        self.io_loop.run_sync(f)

    def test_multi_dict(self):
        @gen.coroutine
        def f():
            results = yield dict(foo=self.add_one_async(1), bar=self.add_one_async(2))
            self.assertEqual(results, dict(foo=2, bar=3))

        self.io_loop.run_sync(f)

    def test_multi_delayed(self):
        @gen.coroutine
        def f():
            # callbacks run at different times
            responses = yield gen.multi_future(
                [self.delay(3, "v1"), self.delay(1, "v2")]
            )
            self.assertEqual(responses, ["v1", "v2"])

        self.io_loop.run_sync(f)

    def test_multi_dict_delayed(self):
        @gen.coroutine
        def f():
            # callbacks run at different times
            responses = yield gen.multi_future(
                dict(foo=self.delay(3, "v1"), bar=self.delay(1, "v2"))
            )
            self.assertEqual(responses, dict(foo="v1", bar="v2"))

        self.io_loop.run_sync(f)

    @gen_test
    def test_multi_performance(self):
        # Yielding a list used to have quadratic performance; make
        # sure a large list stays reasonable.  On my laptop a list of
        # 2000 used to take 1.8s, now it takes 0.12.
        start = time.time()
        yield [gen.moment for i in range(2000)]
        end = time.time()
        self.assertLess(end - start, 1.0)

    @gen_test
    def test_multi_empty(self):
        # Empty lists or dicts should return the same type.
        x = yield []
        self.assertTrue(isinstance(x, list))
        y = yield {}
        self.assertTrue(isinstance(y, dict))

    @gen_test
    def test_future(self):
        result = yield self.async_future(1)
        self.assertEqual(result, 1)

    @gen_test
    def test_multi_future(self):
        results = yield [self.async_future(1), self.async_future(2)]
        self.assertEqual(results, [1, 2])

    @gen_test
    def test_multi_future_duplicate(self):
        # Note that this doesn't work with native corotines, only with
        # decorated coroutines.
        f = self.async_future(2)
        results = yield [self.async_future(1), f, self.async_future(3), f]
        self.assertEqual(results, [1, 2, 3, 2])

    @gen_test
    def test_multi_dict_future(self):
        results = yield dict(foo=self.async_future(1), bar=self.async_future(2))
        self.assertEqual(results, dict(foo=1, bar=2))

    @gen_test
    def test_multi_exceptions(self):
        with ExpectLog(app_log, "Multiple exceptions in yield list"):
            with self.assertRaises(RuntimeError) as cm:
                yield gen.Multi(
                    [
                        self.async_exception(RuntimeError("error 1")),
                        self.async_exception(RuntimeError("error 2")),
                    ]
                )
        self.assertEqual(str(cm.exception), "error 1")

        # With only one exception, no error is logged.
        with self.assertRaises(RuntimeError):
            yield gen.Multi(
                [self.async_exception(RuntimeError("error 1")), self.async_future(2)]
            )

        # Exception logging may be explicitly quieted.
        with self.assertRaises(RuntimeError):
            yield gen.Multi(
                [
                    self.async_exception(RuntimeError("error 1")),
                    self.async_exception(RuntimeError("error 2")),
                ],
                quiet_exceptions=RuntimeError,
            )

    @gen_test
    def test_multi_future_exceptions(self):
        with ExpectLog(app_log, "Multiple exceptions in yield list"):
            with self.assertRaises(RuntimeError) as cm:
                yield [
                    self.async_exception(RuntimeError("error 1")),
                    self.async_exception(RuntimeError("error 2")),
                ]
        self.assertEqual(str(cm.exception), "error 1")

        # With only one exception, no error is logged.
        with self.assertRaises(RuntimeError):
            yield [self.async_exception(RuntimeError("error 1")), self.async_future(2)]

        # Exception logging may be explicitly quieted.
        with self.assertRaises(RuntimeError):
            yield gen.multi_future(
                [
                    self.async_exception(RuntimeError("error 1")),
                    self.async_exception(RuntimeError("error 2")),
                ],
                quiet_exceptions=RuntimeError,
            )

    def test_sync_raise_return(self):
        @gen.coroutine
        def f():
            raise gen.Return()

        self.io_loop.run_sync(f)

    def test_async_raise_return(self):
        @gen.coroutine
        def f():
            yield gen.moment
            raise gen.Return()

        self.io_loop.run_sync(f)

    def test_sync_raise_return_value(self):
        @gen.coroutine
        def f():
            raise gen.Return(42)

        self.assertEqual(42, self.io_loop.run_sync(f))

    def test_sync_raise_return_value_tuple(self):
        @gen.coroutine
        def f():
            raise gen.Return((1, 2))

        self.assertEqual((1, 2), self.io_loop.run_sync(f))

    def test_async_raise_return_value(self):
        @gen.coroutine
        def f():
            yield gen.moment
            raise gen.Return(42)

        self.assertEqual(42, self.io_loop.run_sync(f))

    def test_async_raise_return_value_tuple(self):
        @gen.coroutine
        def f():
            yield gen.moment
            raise gen.Return((1, 2))

        self.assertEqual((1, 2), self.io_loop.run_sync(f))


class GenCoroutineTest(AsyncTestCase):
    def setUp(self):
        # Stray StopIteration exceptions can lead to tests exiting prematurely,
        # so we need explicit checks here to make sure the tests run all
        # the way through.
        self.finished = False
        super().setUp()

    def tearDown(self):
        super().tearDown()
        assert self.finished

    def test_attributes(self):
        self.finished = True

        def f():
            yield gen.moment

        coro = gen.coroutine(f)
        self.assertEqual(coro.__name__, f.__name__)
        self.assertEqual(coro.__module__, f.__module__)
        self.assertIs(coro.__wrapped__, f)  # type: ignore

    def test_is_coroutine_function(self):
        self.finished = True

        def f():
            yield gen.moment

        coro = gen.coroutine(f)
        self.assertFalse(gen.is_coroutine_function(f))
        self.assertTrue(gen.is_coroutine_function(coro))
        self.assertFalse(gen.is_coroutine_function(coro()))

    @gen_test
    def test_sync_gen_return(self):
        @gen.coroutine
        def f():
            raise gen.Return(42)

        result = yield f()
        self.assertEqual(result, 42)
        self.finished = True

    @gen_test
    def test_async_gen_return(self):
        @gen.coroutine
        def f():
            yield gen.moment
            raise gen.Return(42)

        result = yield f()
        self.assertEqual(result, 42)
        self.finished = True

    @gen_test
    def test_sync_return(self):
        @gen.coroutine
        def f():
            return 42

        result = yield f()
        self.assertEqual(result, 42)
        self.finished = True

    @gen_test
    def test_async_return(self):
        @gen.coroutine
        def f():
            yield gen.moment
            return 42

        result = yield f()
        self.assertEqual(result, 42)
        self.finished = True

    @gen_test
    def test_async_early_return(self):
        # A yield statement exists but is not executed, which means
        # this function "returns" via an exception.  This exception
        # doesn't happen before the exception handling is set up.
        @gen.coroutine
        def f():
            if True:
                return 42
            yield gen.Task(self.io_loop.add_callback)

        result = yield f()
        self.assertEqual(result, 42)
        self.finished = True

    @gen_test
    def test_async_await(self):
        @gen.coroutine
        def f1():
            yield gen.moment
            raise gen.Return(42)

        # This test verifies that an async function can await a
        # yield-based gen.coroutine, and that a gen.coroutine
        # (the test method itself) can yield an async function.
        async def f2():
            result = await f1()
            return result

        result = yield f2()
        self.assertEqual(result, 42)
        self.finished = True

    @gen_test
    def test_asyncio_sleep_zero(self):
        # asyncio.sleep(0) turns into a special case (equivalent to
        # `yield None`)
        async def f():
            import asyncio

            await asyncio.sleep(0)
            return 42

        result = yield f()
        self.assertEqual(result, 42)
        self.finished = True

    @gen_test
    def test_async_await_mixed_multi_native_future(self):
        @gen.coroutine
        def f1():
            yield gen.moment

        async def f2():
            await f1()
            return 42

        @gen.coroutine
        def f3():
            yield gen.moment
            raise gen.Return(43)

        results = yield [f2(), f3()]
        self.assertEqual(results, [42, 43])
        self.finished = True

    @gen_test
    def test_async_with_timeout(self):
        async def f1():
            return 42

        result = yield gen.with_timeout(datetime.timedelta(hours=1), f1())
        self.assertEqual(result, 42)
        self.finished = True

    @gen_test
    def test_sync_return_no_value(self):
        @gen.coroutine
        def f():
            return

        result = yield f()
        self.assertIsNone(result)
        self.finished = True

    @gen_test
    def test_async_return_no_value(self):
        @gen.coroutine
        def f():
            yield gen.moment
            return

        result = yield f()
        self.assertIsNone(result)
        self.finished = True

    @gen_test
    def test_sync_raise(self):
        @gen.coroutine
        def f():
            1 / 0

        # The exception is raised when the future is yielded
        # (or equivalently when its result method is called),
        # not when the function itself is called).
        future = f()
        with self.assertRaises(ZeroDivisionError):
            yield future
        self.finished = True

    @gen_test
    def test_async_raise(self):
        @gen.coroutine
        def f():
            yield gen.moment
            1 / 0

        future = f()
        with self.assertRaises(ZeroDivisionError):
            yield future
        self.finished = True

    @gen_test
    def test_replace_yieldpoint_exception(self):
        # Test exception handling: a coroutine can catch one exception
        # raised by a yield point and raise a different one.
        @gen.coroutine
        def f1():
            1 / 0

        @gen.coroutine
        def f2():
            try:
                yield f1()
            except ZeroDivisionError:
                raise KeyError()

        future = f2()
        with self.assertRaises(KeyError):
            yield future
        self.finished = True

    @gen_test
    def test_swallow_yieldpoint_exception(self):
        # Test exception handling: a coroutine can catch an exception
        # raised by a yield point and not raise a different one.
        @gen.coroutine
        def f1():
            1 / 0

        @gen.coroutine
        def f2():
            try:
                yield f1()
            except ZeroDivisionError:
                raise gen.Return(42)

        result = yield f2()
        self.assertEqual(result, 42)
        self.finished = True

    @gen_test
    def test_moment(self):
        calls = []

        @gen.coroutine
        def f(name, yieldable):
            for i in range(5):
                calls.append(name)
                yield yieldable

        # First, confirm the behavior without moment: each coroutine
        # monopolizes the event loop until it finishes.
        immediate = Future()  # type: Future[None]
        immediate.set_result(None)
        yield [f("a", immediate), f("b", immediate)]
        self.assertEqual("".join(calls), "aaaaabbbbb")

        # With moment, they take turns.
        calls = []
        yield [f("a", gen.moment), f("b", gen.moment)]
        self.assertEqual("".join(calls), "ababababab")
        self.finished = True

        calls = []
        yield [f("a", gen.moment), f("b", immediate)]
        self.assertEqual("".join(calls), "abbbbbaaaa")

    @gen_test
    def test_sleep(self):
        yield gen.sleep(0.01)
        self.finished = True

    @gen_test
    def test_py3_leak_exception_context(self):
        class LeakedException(Exception):
            pass

        @gen.coroutine
        def inner(iteration):
            raise LeakedException(iteration)

        try:
            yield inner(1)
        except LeakedException as e:
            self.assertEqual(str(e), "1")
            self.assertIsNone(e.__context__)

        try:
            yield inner(2)
        except LeakedException as e:
            self.assertEqual(str(e), "2")
            self.assertIsNone(e.__context__)

        self.finished = True

    @skipNotCPython
    def test_coroutine_refcounting(self):
        # On CPython, tasks and their arguments should be released immediately
        # without waiting for garbage collection.
        @gen.coroutine
        def inner():
            class Foo:
                pass

            local_var = Foo()
            self.local_ref = weakref.ref(local_var)

            def dummy():
                pass

            yield gen.coroutine(dummy)()
            raise ValueError("Some error")

        @gen.coroutine
        def inner2():
            try:
                yield inner()
            except ValueError:
                pass

        self.io_loop.run_sync(inner2, timeout=3)

        self.assertIsNone(self.local_ref())
        self.finished = True

    def test_asyncio_future_debug_info(self):
        self.finished = True
        # Enable debug mode
        asyncio_loop = asyncio.get_event_loop()
        self.addCleanup(asyncio_loop.set_debug, asyncio_loop.get_debug())
        asyncio_loop.set_debug(True)

        def f():
            yield gen.moment

        coro = gen.coroutine(f)()
        self.assertIsInstance(coro, asyncio.Future)
        # We expect the coroutine repr() to show the place where
        # it was instantiated
        expected = "created at %s:%d" % (__file__, f.__code__.co_firstlineno + 3)
        actual = repr(coro)
        self.assertIn(expected, actual)

    @gen_test
    def test_asyncio_gather(self):
        # This demonstrates that tornado coroutines can be understood
        # by asyncio (This failed prior to Tornado 5.0).
        @gen.coroutine
        def f():
            yield gen.moment
            raise gen.Return(1)

        ret = yield asyncio.gather(f(), f())
        self.assertEqual(ret, [1, 1])
        self.finished = True


class GenCoroutineSequenceHandler(RequestHandler):
    @gen.coroutine
    def get(self):
        yield gen.moment
        self.write("1")
        yield gen.moment
        self.write("2")
        yield gen.moment
        self.finish("3")


class GenCoroutineUnfinishedSequenceHandler(RequestHandler):
    @gen.coroutine
    def get(self):
        yield gen.moment
        self.write("1")
        yield gen.moment
        self.write("2")
        yield gen.moment
        # just write, don't finish
        self.write("3")


# "Undecorated" here refers to the absence of @asynchronous.
class UndecoratedCoroutinesHandler(RequestHandler):
    @gen.coroutine
    def prepare(self):
        self.chunks = []  # type: List[str]
        yield gen.moment
        self.chunks.append("1")

    @gen.coroutine
    def get(self):
        self.chunks.append("2")
        yield gen.moment
        self.chunks.append("3")
        yield gen.moment
        self.write("".join(self.chunks))


class AsyncPrepareErrorHandler(RequestHandler):
    @gen.coroutine
    def prepare(self):
        yield gen.moment
        raise HTTPError(403)

    def get(self):
        self.finish("ok")


class NativeCoroutineHandler(RequestHandler):
    async def get(self):
        await asyncio.sleep(0)
        self.write("ok")


class GenWebTest(AsyncHTTPTestCase):
    def get_app(self):
        return Application(
            [
                ("/coroutine_sequence", GenCoroutineSequenceHandler),
                (
                    "/coroutine_unfinished_sequence",
                    GenCoroutineUnfinishedSequenceHandler,
                ),
                ("/undecorated_coroutine", UndecoratedCoroutinesHandler),
                ("/async_prepare_error", AsyncPrepareErrorHandler),
                ("/native_coroutine", NativeCoroutineHandler),
            ]
        )

    def test_coroutine_sequence_handler(self):
        response = self.fetch("/coroutine_sequence")
        self.assertEqual(response.body, b"123")

    def test_coroutine_unfinished_sequence_handler(self):
        response = self.fetch("/coroutine_unfinished_sequence")
        self.assertEqual(response.body, b"123")

    def test_undecorated_coroutines(self):
        response = self.fetch("/undecorated_coroutine")
        self.assertEqual(response.body, b"123")

    def test_async_prepare_error_handler(self):
        response = self.fetch("/async_prepare_error")
        self.assertEqual(response.code, 403)

    def test_native_coroutine_handler(self):
        response = self.fetch("/native_coroutine")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b"ok")


class WithTimeoutTest(AsyncTestCase):
    @gen_test
    def test_timeout(self):
        with self.assertRaises(gen.TimeoutError):
            yield gen.with_timeout(datetime.timedelta(seconds=0.1), Future())

    @gen_test
    def test_completes_before_timeout(self):
        future = Future()  # type: Future[str]
        self.io_loop.add_timeout(
            datetime.timedelta(seconds=0.1), lambda: future.set_result("asdf")
        )
        result = yield gen.with_timeout(datetime.timedelta(seconds=3600), future)
        self.assertEqual(result, "asdf")

    @gen_test
    def test_fails_before_timeout(self):
        future = Future()  # type: Future[str]
        self.io_loop.add_timeout(
            datetime.timedelta(seconds=0.1),
            lambda: future.set_exception(ZeroDivisionError()),
        )
        with self.assertRaises(ZeroDivisionError):
            yield gen.with_timeout(datetime.timedelta(seconds=3600), future)

    @gen_test
    def test_already_resolved(self):
        future = Future()  # type: Future[str]
        future.set_result("asdf")
        result = yield gen.with_timeout(datetime.timedelta(seconds=3600), future)
        self.assertEqual(result, "asdf")

    @gen_test
    def test_timeout_concurrent_future(self):
        # A concurrent future that does not resolve before the timeout.
        with futures.ThreadPoolExecutor(1) as executor:
            with self.assertRaises(gen.TimeoutError):
                yield gen.with_timeout(
                    self.io_loop.time(), executor.submit(time.sleep, 0.1)
                )

    @gen_test
    def test_completed_concurrent_future(self):
        # A concurrent future that is resolved before we even submit it
        # to with_timeout.
        with futures.ThreadPoolExecutor(1) as executor:

            def dummy():
                pass

            f = executor.submit(dummy)
            f.result()  # wait for completion
            yield gen.with_timeout(datetime.timedelta(seconds=3600), f)

    @gen_test
    def test_normal_concurrent_future(self):
        # A conccurrent future that resolves while waiting for the timeout.
        with futures.ThreadPoolExecutor(1) as executor:
            yield gen.with_timeout(
                datetime.timedelta(seconds=3600),
                executor.submit(lambda: time.sleep(0.01)),
            )


class WaitIteratorTest(AsyncTestCase):
    @gen_test
    def test_empty_iterator(self):
        g = gen.WaitIterator()
        self.assertTrue(g.done(), "empty generator iterated")

        with self.assertRaises(ValueError):
            g = gen.WaitIterator(Future(), bar=Future())

        self.assertIsNone(g.current_index, "bad nil current index")
        self.assertIsNone(g.current_future, "bad nil current future")

    @gen_test
    def test_already_done(self):
        f1 = Future()  # type: Future[int]
        f2 = Future()  # type: Future[int]
        f3 = Future()  # type: Future[int]
        f1.set_result(24)
        f2.set_result(42)
        f3.set_result(84)

        g = gen.WaitIterator(f1, f2, f3)
        i = 0
        while not g.done():
            r = yield g.next()
            # Order is not guaranteed, but the current implementation
            # preserves ordering of already-done Futures.
            if i == 0:
                self.assertEqual(g.current_index, 0)
                self.assertIs(g.current_future, f1)
                self.assertEqual(r, 24)
            elif i == 1:
                self.assertEqual(g.current_index, 1)
                self.assertIs(g.current_future, f2)
                self.assertEqual(r, 42)
            elif i == 2:
                self.assertEqual(g.current_index, 2)
                self.assertIs(g.current_future, f3)
                self.assertEqual(r, 84)
            i += 1

        self.assertIsNone(g.current_index, "bad nil current index")
        self.assertIsNone(g.current_future, "bad nil current future")

        dg = gen.WaitIterator(f1=f1, f2=f2)

        while not dg.done():
            dr = yield dg.next()
            if dg.current_index == "f1":
                self.assertTrue(
                    dg.current_future == f1 and dr == 24,
                    "WaitIterator dict status incorrect",
                )
            elif dg.current_index == "f2":
                self.assertTrue(
                    dg.current_future == f2 and dr == 42,
                    "WaitIterator dict status incorrect",
                )
            else:
                self.fail(f"got bad WaitIterator index {dg.current_index}")

            i += 1
        self.assertIsNone(g.current_index, "bad nil current index")
        self.assertIsNone(g.current_future, "bad nil current future")

    def finish_coroutines(self, iteration, futures):
        if iteration == 3:
            futures[2].set_result(24)
        elif iteration == 5:
            futures[0].set_exception(ZeroDivisionError())
        elif iteration == 8:
            futures[1].set_result(42)
            futures[3].set_result(84)

        if iteration < 8:
            self.io_loop.add_callback(self.finish_coroutines, iteration + 1, futures)

    @gen_test
    def test_iterator(self):
        futures = [Future(), Future(), Future(), Future()]  # type: List[Future[int]]

        self.finish_coroutines(0, futures)

        g = gen.WaitIterator(*futures)

        i = 0
        while not g.done():
            try:
                r = yield g.next()
            except ZeroDivisionError:
                self.assertIs(g.current_future, futures[0], "exception future invalid")
            else:
                if i == 0:
                    self.assertEqual(r, 24, "iterator value incorrect")
                    self.assertEqual(g.current_index, 2, "wrong index")
                elif i == 2:
                    self.assertEqual(r, 42, "iterator value incorrect")
                    self.assertEqual(g.current_index, 1, "wrong index")
                elif i == 3:
                    self.assertEqual(r, 84, "iterator value incorrect")
                    self.assertEqual(g.current_index, 3, "wrong index")
            i += 1

    @gen_test
    def test_iterator_async_await(self):
        # Recreate the previous test with py35 syntax. It's a little clunky
        # because of the way the previous test handles an exception on
        # a single iteration.
        futures = [Future(), Future(), Future(), Future()]  # type: List[Future[int]]
        self.finish_coroutines(0, futures)
        self.finished = False

        async def f():
            i = 0
            g = gen.WaitIterator(*futures)
            try:
                async for r in g:
                    if i == 0:
                        self.assertEqual(r, 24, "iterator value incorrect")
                        self.assertEqual(g.current_index, 2, "wrong index")
                    else:
                        raise Exception("expected exception on iteration 1")
                    i += 1
            except ZeroDivisionError:
                i += 1
            async for r in g:
                if i == 2:
                    self.assertEqual(r, 42, "iterator value incorrect")
                    self.assertEqual(g.current_index, 1, "wrong index")
                elif i == 3:
                    self.assertEqual(r, 84, "iterator value incorrect")
                    self.assertEqual(g.current_index, 3, "wrong index")
                else:
                    raise Exception("didn't expect iteration %d" % i)
                i += 1
            self.finished = True

        yield f()
        self.assertTrue(self.finished)

    @gen_test
    def test_no_ref(self):
        # In this usage, there is no direct hard reference to the
        # WaitIterator itself, only the Future it returns. Since
        # WaitIterator uses weak references internally to improve GC
        # performance, this used to cause problems.
        yield gen.with_timeout(
            datetime.timedelta(seconds=0.1), gen.WaitIterator(gen.sleep(0)).next()
        )


class RunnerGCTest(AsyncTestCase):
    def is_pypy3(self):
        return platform.python_implementation() == "PyPy" and sys.version_info > (3,)

    @gen_test
    def test_gc(self):
        # GitHub issue 1769: Runner objects can get GCed unexpectedly
        # while their future is alive.
        weakref_scope = [None]  # type: List[Optional[weakref.ReferenceType]]

        def callback():
            gc.collect(2)
            weakref_scope[0]().set_result(123)  # type: ignore

        @gen.coroutine
        def tester():
            fut = Future()  # type: Future[int]
            weakref_scope[0] = weakref.ref(fut)
            self.io_loop.add_callback(callback)
            yield fut

        yield gen.with_timeout(datetime.timedelta(seconds=0.2), tester())

    def test_gc_infinite_coro(self):
        # GitHub issue 2229: suspended coroutines should be GCed when
        # their loop is closed, even if they're involved in a reference
        # cycle.
        loop = self.get_new_ioloop()
        result = []  # type: List[Optional[bool]]
        wfut = []

        @gen.coroutine
        def infinite_coro():
            try:
                while True:
                    yield gen.sleep(1e-3)
                    result.append(True)
            finally:
                # coroutine finalizer
                result.append(None)

        @gen.coroutine
        def do_something():
            fut = infinite_coro()
            fut._refcycle = fut  # type: ignore
            wfut.append(weakref.ref(fut))
            yield gen.sleep(0.2)

        loop.run_sync(do_something)
        loop.close()
        gc.collect()
        # Future was collected
        self.assertIsNone(wfut[0]())
        # At least one wakeup
        self.assertGreaterEqual(len(result), 2)
        if not self.is_pypy3():
            # coroutine finalizer was called (not on PyPy3 apparently)
            self.assertIsNone(result[-1])

    def test_gc_infinite_async_await(self):
        # Same as test_gc_infinite_coro, but with a `async def` function
        import asyncio

        async def infinite_coro(result):
            try:
                while True:
                    await gen.sleep(1e-3)
                    result.append(True)
            finally:
                # coroutine finalizer
                result.append(None)

        loop = self.get_new_ioloop()
        result = []  # type: List[Optional[bool]]
        wfut = []

        @gen.coroutine
        def do_something():
            fut = asyncio.get_event_loop().create_task(infinite_coro(result))
            fut._refcycle = fut  # type: ignore
            wfut.append(weakref.ref(fut))
            yield gen.sleep(0.2)

        loop.run_sync(do_something)
        with ExpectLog("asyncio", "Task was destroyed but it is pending"):
            loop.close()
            gc.collect()
        # Future was collected
        self.assertIsNone(wfut[0]())
        # At least one wakeup and one finally
        self.assertGreaterEqual(len(result), 2)
        if not self.is_pypy3():
            # coroutine finalizer was called (not on PyPy3 apparently)
            self.assertIsNone(result[-1])

    def test_multi_moment(self):
        # Test gen.multi with moment
        # now that it's not a real Future
        @gen.coroutine
        def wait_a_moment():
            result = yield gen.multi([gen.moment, gen.moment])
            raise gen.Return(result)

        loop = self.get_new_ioloop()
        result = loop.run_sync(wait_a_moment)
        self.assertEqual(result, [None, None])


if contextvars is not None:
    ctx_var = contextvars.ContextVar("ctx_var")  # type: contextvars.ContextVar[int]


@unittest.skipIf(contextvars is None, "contextvars module not present")
class ContextVarsTest(AsyncTestCase):
    async def native_root(self, x):
        ctx_var.set(x)
        await self.inner(x)

    @gen.coroutine
    def gen_root(self, x):
        ctx_var.set(x)
        yield
        yield self.inner(x)

    async def inner(self, x):
        self.assertEqual(ctx_var.get(), x)
        await self.gen_inner(x)
        self.assertEqual(ctx_var.get(), x)

        # IOLoop.run_in_executor doesn't automatically copy context
        ctx = contextvars.copy_context()
        await self.io_loop.run_in_executor(None, lambda: ctx.run(self.thread_inner, x))
        self.assertEqual(ctx_var.get(), x)

        # Neither does asyncio's run_in_executor.
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: ctx.run(self.thread_inner, x)
        )
        self.assertEqual(ctx_var.get(), x)

    @gen.coroutine
    def gen_inner(self, x):
        self.assertEqual(ctx_var.get(), x)
        yield
        self.assertEqual(ctx_var.get(), x)

    def thread_inner(self, x):
        self.assertEqual(ctx_var.get(), x)

    @gen_test
    def test_propagate(self):
        # Verify that context vars get propagated across various
        # combinations of native and decorated coroutines.
        yield [
            self.native_root(1),
            self.native_root(2),
            self.gen_root(3),
            self.gen_root(4),
        ]

    @gen_test
    def test_reset(self):
        token = ctx_var.set(1)
        yield
        # reset asserts that we are still at the same level of the context tree,
        # so we must make sure that we maintain that property across yield.
        ctx_var.reset(token)

    @gen_test
    def test_propagate_to_first_yield_with_native_async_function(self):
        x = 10

        async def native_async_function():
            self.assertEqual(ctx_var.get(), x)

        ctx_var.set(x)
        yield native_async_function()


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\interactiveshell.py ===
"""IPython terminal interface using prompt_toolkit"""

import os
import sys
import inspect
from warnings import warn
from typing import Union as UnionType, Optional

from IPython.core.async_helpers import get_asyncio_loop
from IPython.core.interactiveshell import InteractiveShell, InteractiveShellABC
from IPython.utils.py3compat import input
from IPython.utils.PyColorize import theme_table
from IPython.utils.terminal import toggle_set_term_title, set_term_title, restore_term_title
from IPython.utils.process import abbrev_cwd
from traitlets import (
    Any,
    Bool,
    Dict,
    Enum,
    Float,
    Instance,
    Integer,
    List,
    Type,
    Unicode,
    Union,
    default,
    observe,
    validate,
    DottedObjectName,
)
from traitlets.utils.importstring import import_item


from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.enums import DEFAULT_BUFFER, EditingMode
from prompt_toolkit.filters import HasFocus, Condition, IsDone
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.history import History
from prompt_toolkit.layout.processors import ConditionalProcessor, HighlightMatchingBracketProcessor
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession, CompleteStyle, print_formatted_text
from prompt_toolkit.styles import DynamicStyle, merge_styles
from prompt_toolkit.styles.pygments import style_from_pygments_cls, style_from_pygments_dict
from pygments.styles import get_style_by_name
from pygments.style import Style

from .debugger import TerminalPdb, Pdb
from .magics import TerminalMagics
from .pt_inputhooks import get_inputhook_name_and_func
from .prompts import Prompts, ClassicPrompts, RichPromptDisplayHook
from .ptutils import IPythonPTCompleter, IPythonPTLexer
from .shortcuts import (
    KEY_BINDINGS,
    UNASSIGNED_ALLOWED_COMMANDS,
    create_ipython_shortcuts,
    create_identifier,
    RuntimeBinding,
    add_binding,
)
from .shortcuts.filters import KEYBINDING_FILTERS, filter_from_string
from .shortcuts.auto_suggest import (
    NavigableAutoSuggestFromHistory,
    AppendAutoSuggestionInAnyLine,
)


class _NoStyle(Style):
    pass



def _backward_compat_continuation_prompt_tokens(
    method, width: int, *, lineno: int, wrap_count: int
):
    """
    Sagemath use custom prompt and we broke them in 8.19.

    make sure to pass only width if method only support width
    """
    sig = inspect.signature(method)
    extra = {}
    params = inspect.signature(method).parameters
    if "lineno" in inspect.signature(method).parameters or any(
        [p.kind == p.VAR_KEYWORD for p in sig.parameters.values()]
    ):
        extra["lineno"] = lineno
    if "line_number" in inspect.signature(method).parameters or any(
        [p.kind == p.VAR_KEYWORD for p in sig.parameters.values()]
    ):
        extra["line_number"] = lineno

    if "wrap_count" in inspect.signature(method).parameters or any(
        [p.kind == p.VAR_KEYWORD for p in sig.parameters.values()]
    ):
        extra["wrap_count"] = wrap_count
    return method(width, **extra)


def get_default_editor():
    try:
        return os.environ['EDITOR']
    except KeyError:
        pass
    except UnicodeError:
        warn("$EDITOR environment variable is not pure ASCII. Using platform "
             "default editor.")

    if os.name == 'posix':
        return 'vi'  # the only one guaranteed to be there!
    else:
        return "notepad"  # same in Windows!


# conservatively check for tty
# overridden streams can result in things like:
# - sys.stdin = None
# - no isatty method
for _name in ('stdin', 'stdout', 'stderr'):
    _stream = getattr(sys, _name)
    try:
        if not _stream or not hasattr(_stream, "isatty") or not _stream.isatty():
            _is_tty = False
            break
    except ValueError:
        # stream is closed
        _is_tty = False
        break
else:
    _is_tty = True


_use_simple_prompt = ('IPY_TEST_SIMPLE_PROMPT' in os.environ) or (not _is_tty)

def black_reformat_handler(text_before_cursor):
    """
    We do not need to protect against error,
    this is taken care at a higher level where any reformat error is ignored.
    Indeed we may call reformatting on incomplete code.
    """
    import black

    formatted_text = black.format_str(text_before_cursor, mode=black.FileMode())
    if not text_before_cursor.endswith("\n") and formatted_text.endswith("\n"):
        formatted_text = formatted_text[:-1]
    return formatted_text


def yapf_reformat_handler(text_before_cursor):
    from yapf.yapflib import file_resources
    from yapf.yapflib import yapf_api

    style_config = file_resources.GetDefaultStyleForDir(os.getcwd())
    formatted_text, was_formatted = yapf_api.FormatCode(
        text_before_cursor, style_config=style_config
    )
    if was_formatted:
        if not text_before_cursor.endswith("\n") and formatted_text.endswith("\n"):
            formatted_text = formatted_text[:-1]
        return formatted_text
    else:
        return text_before_cursor


class PtkHistoryAdapter(History):
    """
    Prompt toolkit has it's own way of handling history, Where it assumes it can
    Push/pull from history.

    """

    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self._refresh()

    def append_string(self, string):
        # we rely on sql for that.
        self._loaded = False
        self._refresh()

    def _refresh(self):
        if not self._loaded:
            self._loaded_strings = list(self.load_history_strings())

    def load_history_strings(self):
        last_cell = ""
        res = []
        for __, ___, cell in self.shell.history_manager.get_tail(
            self.shell.history_load_length, include_latest=True
        ):
            # Ignore blank lines and consecutive duplicates
            cell = cell.rstrip()
            if cell and (cell != last_cell):
                res.append(cell)
                last_cell = cell
        yield from res[::-1]

    def store_string(self, string: str) -> None:
        pass

class TerminalInteractiveShell(InteractiveShell):
    mime_renderers = Dict().tag(config=True)

    min_elide = Integer(
        30, help="minimum characters for filling with ellipsis in file completions"
    ).tag(config=True)
    space_for_menu = Integer(
        6,
        help="Number of line at the bottom of the screen "
        "to reserve for the tab completion menu, "
        "search history, ...etc, the height of "
        "these menus will at most this value. "
        "Increase it is you prefer long and skinny "
        "menus, decrease for short and wide.",
    ).tag(config=True)

    pt_app: UnionType[PromptSession, None] = None
    auto_suggest: UnionType[
        AutoSuggestFromHistory,
        NavigableAutoSuggestFromHistory,
        None,
    ] = None
    debugger_history = None

    debugger_history_file = Unicode(
        "~/.pdbhistory", help="File in which to store and read history"
    ).tag(config=True)

    simple_prompt = Bool(_use_simple_prompt,
        help="""Use `raw_input` for the REPL, without completion and prompt colors.

            Useful when controlling IPython as a subprocess, and piping
            STDIN/OUT/ERR. Known usage are: IPython's own testing machinery,
            and emacs' inferior-python subprocess (assuming you have set
            `python-shell-interpreter` to "ipython") available through the
            built-in `M-x run-python` and third party packages such as elpy.

            This mode default to `True` if the `IPY_TEST_SIMPLE_PROMPT`
            environment variable is set, or the current terminal is not a tty.
            Thus the Default value reported in --help-all, or config will often
            be incorrectly reported.
            """,
    ).tag(config=True)

    @property
    def debugger_cls(self):
        return Pdb if self.simple_prompt else TerminalPdb

    confirm_exit = Bool(True,
        help="""
        Set to confirm when you try to exit IPython with an EOF (Control-D
        in Unix, Control-Z/Enter in Windows). By typing 'exit' or 'quit',
        you can force a direct exit without any confirmation.""",
    ).tag(config=True)

    editing_mode = Unicode('emacs',
        help="Shortcut style to use at the prompt. 'vi' or 'emacs'.",
    ).tag(config=True)

    emacs_bindings_in_vi_insert_mode = Bool(
        True,
        help="Add shortcuts from 'emacs' insert mode to 'vi' insert mode.",
    ).tag(config=True)

    modal_cursor = Bool(
        True,
        help="""
       Cursor shape changes depending on vi mode: beam in vi insert mode,
       block in nav mode, underscore in replace mode.""",
    ).tag(config=True)

    ttimeoutlen = Float(
        0.01,
        help="""The time in milliseconds that is waited for a key code
       to complete.""",
    ).tag(config=True)

    timeoutlen = Float(
        0.5,
        help="""The time in milliseconds that is waited for a mapped key
       sequence to complete.""",
    ).tag(config=True)

    autoformatter = Unicode(
        None,
        help="Autoformatter to reformat Terminal code. Can be `'black'`, `'yapf'` or `None`",
        allow_none=True
    ).tag(config=True)

    auto_match = Bool(
        False,
        help="""
        Automatically add/delete closing bracket or quote when opening bracket or quote is entered/deleted.
        Brackets: (), [], {}
        Quotes: '', \"\"
        """,
    ).tag(config=True)

    mouse_support = Bool(False,
        help="Enable mouse support in the prompt\n(Note: prevents selecting text with the mouse)"
    ).tag(config=True)

    # We don't load the list of styles for the help string, because loading
    # Pygments plugins takes time and can cause unexpected errors.
    highlighting_style = Union(
        [Unicode("legacy"), Type(klass=Style)],
        help="""Deprecated, and has not effect, use IPython themes

        The name or class of a Pygments style to use for syntax
        highlighting. To see available styles, run `pygmentize -L styles`.""",
    ).tag(config=True)

    @validate('editing_mode')
    def _validate_editing_mode(self, proposal):
        if proposal['value'].lower() == 'vim':
            proposal['value']= 'vi'
        elif proposal['value'].lower() == 'default':
            proposal['value']= 'emacs'

        if hasattr(EditingMode, proposal['value'].upper()):
            return proposal['value'].lower()

        return self.editing_mode

    @observe('editing_mode')
    def _editing_mode(self, change):
        if self.pt_app:
            self.pt_app.editing_mode = getattr(EditingMode, change.new.upper())

    def _set_formatter(self, formatter):
        if formatter is None:
            self.reformat_handler = lambda x:x
        elif formatter == 'black':
            self.reformat_handler = black_reformat_handler
        elif formatter == "yapf":
            self.reformat_handler = yapf_reformat_handler
        else:
            raise ValueError

    @observe("autoformatter")
    def _autoformatter_changed(self, change):
        formatter = change.new
        self._set_formatter(formatter)

    @observe('highlighting_style')
    @observe('colors')
    def _highlighting_style_changed(self, change):
        assert change.new == change.new.lower()
        if change.new != "legacy":
            warn(
                "highlighting_style is deprecated since 9.0 and have no effect, use themeing."
            )
            return

    def refresh_style(self):
        self._style = self._make_style_from_name_or_cls("legacy")

    # TODO: deprecate this
    highlighting_style_overrides = Dict(
        help="Override highlighting format for specific tokens"
    ).tag(config=True)

    true_color = Bool(False,
        help="""Use 24bit colors instead of 256 colors in prompt highlighting.
        If your terminal supports true color, the following command should
        print ``TRUECOLOR`` in orange::

            printf \"\\x1b[38;2;255;100;0mTRUECOLOR\\x1b[0m\\n\"
        """,
    ).tag(config=True)

    editor = Unicode(get_default_editor(),
        help="Set the editor used by IPython (default to $EDITOR/vi/notepad)."
    ).tag(config=True)

    prompts_class = Type(Prompts, help='Class used to generate Prompt token for prompt_toolkit').tag(config=True)

    prompts = Instance(Prompts)

    @default('prompts')
    def _prompts_default(self):
        return self.prompts_class(self)

#    @observe('prompts')
#    def _(self, change):
#        self._update_layout()

    @default('displayhook_class')
    def _displayhook_class_default(self):
        return RichPromptDisplayHook

    term_title = Bool(True,
        help="Automatically set the terminal title"
    ).tag(config=True)

    term_title_format = Unicode("IPython: {cwd}",
        help="Customize the terminal title format.  This is a python format string. " +
             "Available substitutions are: {cwd}."
    ).tag(config=True)

    display_completions = Enum(('column', 'multicolumn','readlinelike'),
        help= ( "Options for displaying tab completions, 'column', 'multicolumn', and "
                "'readlinelike'. These options are for `prompt_toolkit`, see "
                "`prompt_toolkit` documentation for more information."
                ),
        default_value='multicolumn').tag(config=True)

    highlight_matching_brackets = Bool(True,
        help="Highlight matching brackets.",
    ).tag(config=True)

    extra_open_editor_shortcuts = Bool(False,
        help="Enable vi (v) or Emacs (C-X C-E) shortcuts to open an external editor. "
             "This is in addition to the F2 binding, which is always enabled."
    ).tag(config=True)

    handle_return = Any(None,
        help="Provide an alternative handler to be called when the user presses "
             "Return. This is an advanced option intended for debugging, which "
             "may be changed or removed in later releases."
    ).tag(config=True)

    enable_history_search = Bool(True,
        help="Allows to enable/disable the prompt toolkit history search"
    ).tag(config=True)

    autosuggestions_provider = Unicode(
        "NavigableAutoSuggestFromHistory",
        help="Specifies from which source automatic suggestions are provided. "
        "Can be set to ``'NavigableAutoSuggestFromHistory'`` (:kbd:`up` and "
        ":kbd:`down` swap suggestions), ``'AutoSuggestFromHistory'``, "
        " or ``None`` to disable automatic suggestions. "
        "Default is `'NavigableAutoSuggestFromHistory`'.",
        allow_none=True,
    ).tag(config=True)
    _autosuggestions_provider: Any

    llm_constructor_kwargs = Dict(
        {},
        help="""
        Extra arguments to pass to `llm_provider_class` constructor.

        This is used to – for example – set the `model_id`""",
    ).tag(config=True)

    llm_prefix_from_history = DottedObjectName(
        "input_history",
        help="""\
    Fully Qualifed name of a function that takes an IPython history manager and
    return a prefix to pass the llm provider in addition to the current buffer
    text.

    You can use:

     - no_prefix
     - input_history

    As default value. `input_history` (default),  will use all the input history
    of current IPython session

    """,
    ).tag(config=True)
    _llm_prefix_from_history: Any

    @observe("llm_prefix_from_history")
    def _llm_prefix_from_history_changed(self, change):
        name = change.new
        self._llm_prefix_from_history = name
        self._set_autosuggestions()

    llm_provider_class = DottedObjectName(
        None,
        allow_none=True,
        help="""\
        Provisional:
            This is a provisional API in IPython 8.32, before stabilisation
            in 9.0, it may change without warnings.

        class to use for the `NavigableAutoSuggestFromHistory` to request
        completions from a LLM, this should inherit from
        `jupyter_ai_magics:BaseProvider` and implement
        `stream_inline_completions`
    """,
    ).tag(config=True)
    _llm_provider_class: Any = None

    @observe("llm_provider_class")
    def _llm_provider_class_changed(self, change):
        provider_class = change.new
        self._llm_provider_class = provider_class
        self._set_autosuggestions()

    def _set_autosuggestions(self, provider=None):
        if provider is None:
            provider = self.autosuggestions_provider
        # disconnect old handler
        if self.auto_suggest and isinstance(
            self.auto_suggest, NavigableAutoSuggestFromHistory
        ):
            self.auto_suggest.disconnect()
        if provider is None:
            self.auto_suggest = None
        elif provider == "AutoSuggestFromHistory":
            self.auto_suggest = AutoSuggestFromHistory()
        elif provider == "NavigableAutoSuggestFromHistory":
            # LLM stuff are all Provisional in 8.32
            if self._llm_provider_class:

                def init_llm_provider():
                    llm_provider_constructor = import_item(self._llm_provider_class)
                    return llm_provider_constructor(**self.llm_constructor_kwargs)

            else:
                init_llm_provider = None
            self.auto_suggest = NavigableAutoSuggestFromHistory()
            # Provisinal in 8.32
            self.auto_suggest._init_llm_provider = init_llm_provider

            name = self.llm_prefix_from_history

            if name == "no_prefix":

                def no_prefix(history_manager):
                    return ""

                fun = no_prefix

            elif name == "input_history":

                def input_history(history_manager):
                    return "\n".join([s[2] for s in history_manager.get_range()]) + "\n"

                fun = input_history

            else:
                fun = import_item(name)
            self.auto_suggest._llm_prefixer = fun
        else:
            raise ValueError("No valid provider.")
        if self.pt_app:
            self.pt_app.auto_suggest = self.auto_suggest

    @observe("autosuggestions_provider")
    def _autosuggestions_provider_changed(self, change):
        provider = change.new
        self._set_autosuggestions(provider)

    shortcuts = List(
        trait=Dict(
            key_trait=Enum(
                [
                    "command",
                    "match_keys",
                    "match_filter",
                    "new_keys",
                    "new_filter",
                    "create",
                ]
            ),
            per_key_traits={
                "command": Unicode(),
                "match_keys": List(Unicode()),
                "match_filter": Unicode(),
                "new_keys": List(Unicode()),
                "new_filter": Unicode(),
                "create": Bool(False),
            },
        ),
        help="""
        Add, disable or modifying shortcuts.

        Each entry on the list should be a dictionary with ``command`` key
        identifying the target function executed by the shortcut and at least
        one of the following:

          - ``match_keys``: list of keys used to match an existing shortcut,
          - ``match_filter``: shortcut filter used to match an existing shortcut,
          - ``new_keys``: list of keys to set,
          - ``new_filter``: a new shortcut filter to set

        The filters have to be composed of pre-defined verbs and joined by one
        of the following conjunctions: ``&`` (and), ``|`` (or), ``~`` (not).
        The pre-defined verbs are:

        {filters}

        To disable a shortcut set ``new_keys`` to an empty list.
        To add a shortcut add key ``create`` with value ``True``.

        When modifying/disabling shortcuts, ``match_keys``/``match_filter`` can
        be omitted if the provided specification uniquely identifies a shortcut
        to be modified/disabled. When modifying a shortcut ``new_filter`` or
        ``new_keys`` can be omitted which will result in reuse of the existing
        filter/keys.

        Only shortcuts defined in IPython (and not default prompt-toolkit
        shortcuts) can be modified or disabled. The full list of shortcuts,
        command identifiers and filters is available under
        :ref:`terminal-shortcuts-list`.

        Here is an example:

        .. code::

            c.TerminalInteractiveShell.shortcuts = [
               {{
                   "new_keys": ["c-q"],
                   "command": "prompt_toolkit:named_commands.capitalize_word",
                   "create": True,
               }},
               {{
                   "new_keys": ["c-j"],
                   "command": "prompt_toolkit:named_commands.beginning_of_line",
                   "create": True,
               }},
            ]


        """.format(
            filters="\n        ".join([f"  - ``{k}``" for k in KEYBINDING_FILTERS])
        ),
    ).tag(config=True)

    @observe("shortcuts")
    def _shortcuts_changed(self, change):
        if self.pt_app:
            self.pt_app.key_bindings = self._merge_shortcuts(user_shortcuts=change.new)

    def _merge_shortcuts(self, user_shortcuts):
        # rebuild the bindings list from scratch
        key_bindings = create_ipython_shortcuts(self)

        # for now we only allow adding shortcuts for a specific set of
        # commands; this is a security precution.
        allowed_commands = {
            create_identifier(binding.command): binding.command
            for binding in KEY_BINDINGS
        }
        allowed_commands.update(
            {
                create_identifier(command): command
                for command in UNASSIGNED_ALLOWED_COMMANDS
            }
        )
        shortcuts_to_skip = []
        shortcuts_to_add = []

        for shortcut in user_shortcuts:
            command_id = shortcut["command"]
            if command_id not in allowed_commands:
                allowed_commands = "\n - ".join(allowed_commands)
                raise ValueError(
                    f"{command_id} is not a known shortcut command."
                    f" Allowed commands are: \n - {allowed_commands}"
                )
            old_keys = shortcut.get("match_keys", None)
            old_filter = (
                filter_from_string(shortcut["match_filter"])
                if "match_filter" in shortcut
                else None
            )
            matching = [
                binding
                for binding in KEY_BINDINGS
                if (
                    (old_filter is None or binding.filter == old_filter)
                    and (old_keys is None or [k for k in binding.keys] == old_keys)
                    and create_identifier(binding.command) == command_id
                )
            ]

            new_keys = shortcut.get("new_keys", None)
            new_filter = shortcut.get("new_filter", None)

            command = allowed_commands[command_id]

            creating_new = shortcut.get("create", False)
            modifying_existing = not creating_new and (
                new_keys is not None or new_filter
            )

            if creating_new and new_keys == []:
                raise ValueError("Cannot add a shortcut without keys")

            if modifying_existing:
                specification = {
                    key: shortcut[key]
                    for key in ["command", "filter"]
                    if key in shortcut
                }
                if len(matching) == 0:
                    raise ValueError(
                        f"No shortcuts matching {specification} found in {KEY_BINDINGS}"
                    )
                elif len(matching) > 1:
                    raise ValueError(
                        f"Multiple shortcuts matching {specification} found,"
                        f" please add keys/filter to select one of: {matching}"
                    )

                matched = matching[0]
                old_filter = matched.filter
                old_keys = list(matched.keys)
                shortcuts_to_skip.append(
                    RuntimeBinding(
                        command,
                        keys=old_keys,
                        filter=old_filter,
                    )
                )

            if new_keys != []:
                shortcuts_to_add.append(
                    RuntimeBinding(
                        command,
                        keys=new_keys or old_keys,
                        filter=(
                            filter_from_string(new_filter)
                            if new_filter is not None
                            else (
                                old_filter
                                if old_filter is not None
                                else filter_from_string("always")
                            )
                        ),
                    )
                )

        # rebuild the bindings list from scratch
        key_bindings = create_ipython_shortcuts(self, skip=shortcuts_to_skip)
        for binding in shortcuts_to_add:
            add_binding(key_bindings, binding)

        return key_bindings

    prompt_includes_vi_mode = Bool(True,
        help="Display the current vi mode (when using vi editing mode)."
    ).tag(config=True)

    prompt_line_number_format = Unicode(
        "",
        help="The format for line numbering, will be passed `line` (int, 1 based)"
        " the current line number and `rel_line` the relative line number."
        " for example to display both you can use the following template string :"
        " c.TerminalInteractiveShell.prompt_line_number_format='{line: 4d}/{rel_line:+03d} | '"
        " This will display the current line number, with leading space and a width of at least 4"
        " character, as well as the relative line number 0 padded and always with a + or - sign."
        " Note that when using Emacs mode the prompt of the first line may not update.",
    ).tag(config=True)

    @observe('term_title')
    def init_term_title(self, change=None):
        # Enable or disable the terminal title.
        if self.term_title and _is_tty:
            toggle_set_term_title(True)
            set_term_title(self.term_title_format.format(cwd=abbrev_cwd()))
        else:
            toggle_set_term_title(False)

    def restore_term_title(self):
        if self.term_title and _is_tty:
            restore_term_title()

    def init_display_formatter(self):
        super(TerminalInteractiveShell, self).init_display_formatter()
        # terminal only supports plain text
        self.display_formatter.active_types = ["text/plain"]

    def init_prompt_toolkit_cli(self):
        if self.simple_prompt:
            # Fall back to plain non-interactive output for tests.
            # This is very limited.
            def prompt():
                prompt_text = "".join(x[1] for x in self.prompts.in_prompt_tokens())
                lines = [input(prompt_text)]
                prompt_continuation = "".join(
                    x[1] for x in self.prompts.continuation_prompt_tokens()
                )
                while self.check_complete("\n".join(lines))[0] == "incomplete":
                    lines.append(input(prompt_continuation))
                return "\n".join(lines)

            self.prompt_for_code = prompt
            return

        # Set up keyboard shortcuts
        key_bindings = self._merge_shortcuts(user_shortcuts=self.shortcuts)

        # Pre-populate history from IPython's history database
        history = PtkHistoryAdapter(self)

        self.refresh_style()
        ptk_s = DynamicStyle(lambda: self._style)

        editing_mode = getattr(EditingMode, self.editing_mode.upper())

        self._use_asyncio_inputhook = False
        self.pt_app = PromptSession(
            auto_suggest=self.auto_suggest,
            editing_mode=editing_mode,
            key_bindings=key_bindings,
            history=history,
            completer=IPythonPTCompleter(shell=self),
            enable_history_search=self.enable_history_search,
            style=ptk_s,
            include_default_pygments_style=False,
            mouse_support=self.mouse_support,
            enable_open_in_editor=self.extra_open_editor_shortcuts,
            color_depth=self.color_depth,
            tempfile_suffix=".py",
            **self._extra_prompt_options(),
        )
        if isinstance(self.auto_suggest, NavigableAutoSuggestFromHistory):
            self.auto_suggest.connect(self.pt_app)

    def _make_style_from_name_or_cls(self, name_or_cls):
        """
        Small wrapper that make an IPython compatible style from a style name

        We need that to add style for prompt ... etc.
        """
        assert name_or_cls == "legacy"
        legacy = self.colors.lower()

        theme = theme_table.get(legacy, None)
        assert theme is not None, legacy

        if legacy == "nocolor":
            style_overrides = {}
            style_cls = _NoStyle
        else:
            style_overrides = {**theme.extra_style, **self.highlighting_style_overrides}
            if theme.base is not None:
                style_cls = get_style_by_name(theme.base)
            else:
                style_cls = _NoStyle

        style = merge_styles(
            [
                style_from_pygments_cls(style_cls),
                style_from_pygments_dict(style_overrides),
            ]
        )

        return style

    @property
    def pt_complete_style(self):
        return {
            'multicolumn': CompleteStyle.MULTI_COLUMN,
            'column': CompleteStyle.COLUMN,
            'readlinelike': CompleteStyle.READLINE_LIKE,
        }[self.display_completions]

    @property
    def color_depth(self):
        return (ColorDepth.TRUE_COLOR if self.true_color else None)

    def _ptk_prompt_cont(self, width: int, line_number: int, wrap_count: int):
        return PygmentsTokens(
            _backward_compat_continuation_prompt_tokens(
                self.prompts.continuation_prompt_tokens,
                width,
                lineno=line_number,
                wrap_count=wrap_count,
            )
        )

    def _extra_prompt_options(self):
        """
        Return the current layout option for the current Terminal InteractiveShell
        """
        def get_message():
            return PygmentsTokens(self.prompts.in_prompt_tokens())

        if self.editing_mode == "emacs" and self.prompt_line_number_format == "":
            # with emacs mode the prompt is (usually) static, so we call only
            # the function once. With VI mode it can toggle between [ins] and
            # [nor] so we can't precompute.
            # here I'm going to favor the default keybinding which almost
            # everybody uses to decrease CPU usage.
            # if we have issues with users with custom Prompts we can see how to
            # work around this.
            get_message = get_message()

        options = {
            "complete_in_thread": False,
            "lexer": IPythonPTLexer(),
            "reserve_space_for_menu": self.space_for_menu,
            "message": get_message,
            "prompt_continuation": self._ptk_prompt_cont,
            "multiline": True,
            "complete_style": self.pt_complete_style,
            "input_processors": [
                # Highlight matching brackets, but only when this setting is
                # enabled, and only when the DEFAULT_BUFFER has the focus.
                ConditionalProcessor(
                    processor=HighlightMatchingBracketProcessor(chars="[](){}"),
                    filter=HasFocus(DEFAULT_BUFFER)
                    & ~IsDone()
                    & Condition(lambda: self.highlight_matching_brackets),
                ),
                # Show auto-suggestion in lines other than the last line.
                ConditionalProcessor(
                    processor=AppendAutoSuggestionInAnyLine(),
                    filter=HasFocus(DEFAULT_BUFFER)
                    & ~IsDone()
                    & Condition(
                        lambda: isinstance(
                            self.auto_suggest,
                            NavigableAutoSuggestFromHistory,
                        )
                    ),
                ),
            ],
        }

        return options

    def prompt_for_code(self):
        if self.rl_next_input:
            default = self.rl_next_input
            self.rl_next_input = None
        else:
            default = ''

        # In order to make sure that asyncio code written in the
        # interactive shell doesn't interfere with the prompt, we run the
        # prompt in a different event loop.
        # If we don't do this, people could spawn coroutine with a
        # while/true inside which will freeze the prompt.

        with patch_stdout(raw=True):
            if self._use_asyncio_inputhook:
                # When we integrate the asyncio event loop, run the UI in the
                # same event loop as the rest of the code. don't use an actual
                # input hook. (Asyncio is not made for nesting event loops.)
                asyncio_loop = get_asyncio_loop()
                text = asyncio_loop.run_until_complete(
                    self.pt_app.prompt_async(
                        default=default, **self._extra_prompt_options()
                    )
                )
            else:
                text = self.pt_app.prompt(
                    default=default,
                    inputhook=self._inputhook,
                    **self._extra_prompt_options(),
                )

        return text

    def init_io(self):
        if sys.platform not in {'win32', 'cli'}:
            return

        import colorama
        colorama.init()

    def init_magics(self):
        super(TerminalInteractiveShell, self).init_magics()
        self.register_magics(TerminalMagics)

    def init_alias(self):
        # The parent class defines aliases that can be safely used with any
        # frontend.
        super(TerminalInteractiveShell, self).init_alias()

        # Now define aliases that only make sense on the terminal, because they
        # need direct access to the console in a way that we can't emulate in
        # GUI or web frontend
        if os.name == 'posix':
            for cmd in ('clear', 'more', 'less', 'man'):
                self.alias_manager.soft_define_alias(cmd, cmd)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._set_autosuggestions(self.autosuggestions_provider)
        self.init_prompt_toolkit_cli()
        self.init_term_title()
        self.keep_running = True
        self._set_formatter(self.autoformatter)

    def ask_exit(self):
        self.keep_running = False

    rl_next_input = None

    def interact(self):
        self.keep_running = True
        while self.keep_running:
            print(self.separate_in, end='')

            try:
                code = self.prompt_for_code()
            except EOFError:
                if (not self.confirm_exit) \
                        or self.ask_yes_no('Do you really want to exit ([y]/n)?','y','n'):
                    self.ask_exit()

            else:
                if code:
                    self.run_cell(code, store_history=True)

    def mainloop(self):
        # An extra layer of protection in case someone mashing Ctrl-C breaks
        # out of our internal code.
        while True:
            try:
                self.interact()
                break
            except KeyboardInterrupt as e:
                print("\n%s escaped interact()\n" % type(e).__name__)
            finally:
                # An interrupt during the eventloop will mess up the
                # internal state of the prompt_toolkit library.
                # Stopping the eventloop fixes this, see
                # https://github.com/ipython/ipython/pull/9867
                if hasattr(self, '_eventloop'):
                    self._eventloop.stop()

                self.restore_term_title()

        # try to call some at-exit operation optimistically as some things can't
        # be done during interpreter shutdown. this is technically inaccurate as
        # this make mainlool not re-callable, but that should be a rare if not
        # in existent use case.

        self._atexit_once()

    _inputhook = None
    def inputhook(self, context):
        warn(
            "inputkook seem unused, and marked for deprecation/Removal as of IPython 9.0. "
            "Please open an issue if you are using it.",
            category=PendingDeprecationWarning,
            stacklevel=2,
        )
        if self._inputhook is not None:
            self._inputhook(context)

    active_eventloop: Optional[str] = None

    def enable_gui(self, gui: Optional[str] = None) -> None:
        if gui:
            from ..core.pylabtools import _convert_gui_from_matplotlib

            gui = _convert_gui_from_matplotlib(gui)

        if self.simple_prompt is True and gui is not None:
            print(
                f'Cannot install event loop hook for "{gui}" when running with `--simple-prompt`.'
            )
            print(
                "NOTE: Tk is supported natively; use Tk apps and Tk backends with `--simple-prompt`."
            )
            return

        if self._inputhook is None and gui is None:
            print("No event loop hook running.")
            return

        if self._inputhook is not None and gui is not None:
            newev, newinhook = get_inputhook_name_and_func(gui)
            if self._inputhook == newinhook:
                # same inputhook, do nothing
                self.log.info(
                    f"Shell is already running the {self.active_eventloop} eventloop. Doing nothing"
                )
                return
            self.log.warning(
                f"Shell is already running a different gui event loop for {self.active_eventloop}. "
                "Call with no arguments to disable the current loop."
            )
            return
        if self._inputhook is not None and gui is None:
            self.active_eventloop = self._inputhook = None

        if gui and (gui not in {None, "webagg"}):
            # This hook runs with each cycle of the `prompt_toolkit`'s event loop.
            self.active_eventloop, self._inputhook = get_inputhook_name_and_func(gui)
        else:
            self.active_eventloop = self._inputhook = None

        self._use_asyncio_inputhook = gui == "asyncio"

    # Run !system commands directly, not through pipes, so terminal programs
    # work correctly.
    system = InteractiveShell.system_raw

    def auto_rewrite_input(self, cmd):
        """Overridden from the parent class to use fancy rewriting prompt"""
        if not self.show_rewritten_input:
            return

        tokens = self.prompts.rewrite_prompt_tokens()
        if self.pt_app:
            print_formatted_text(PygmentsTokens(tokens), end='',
                                 style=self.pt_app.app.style)
            print(cmd)
        else:
            prompt = ''.join(s for t, s in tokens)
            print(prompt, cmd, sep='')

    _prompts_before = None
    def switch_doctest_mode(self, mode):
        """Switch prompts to classic for %doctest_mode"""
        if mode:
            self._prompts_before = self.prompts
            self.prompts = ClassicPrompts(self)
        elif self._prompts_before:
            self.prompts = self._prompts_before
            self._prompts_before = None
#        self._update_layout()


InteractiveShellABC.register(TerminalInteractiveShell)

if __name__ == '__main__':
    TerminalInteractiveShell.instance().interact()