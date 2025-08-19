
# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\filters\__init__.py ===
"""
    pygments.filters
    ~~~~~~~~~~~~~~~~

    Module containing filter lookup functions and default
    filters.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pip._vendor.pygments.token import String, Comment, Keyword, Name, Error, Whitespace, \
    string_to_tokentype
from pip._vendor.pygments.filter import Filter
from pip._vendor.pygments.util import get_list_opt, get_int_opt, get_bool_opt, \
    get_choice_opt, ClassNotFound, OptionError
from pip._vendor.pygments.plugin import find_plugin_filters


def find_filter_class(filtername):
    """Lookup a filter by name. Return None if not found."""
    if filtername in FILTERS:
        return FILTERS[filtername]
    for name, cls in find_plugin_filters():
        if name == filtername:
            return cls
    return None


def get_filter_by_name(filtername, **options):
    """Return an instantiated filter.

    Options are passed to the filter initializer if wanted.
    Raise a ClassNotFound if not found.
    """
    cls = find_filter_class(filtername)
    if cls:
        return cls(**options)
    else:
        raise ClassNotFound(f'filter {filtername!r} not found')


def get_all_filters():
    """Return a generator of all filter names."""
    yield from FILTERS
    for name, _ in find_plugin_filters():
        yield name


def _replace_special(ttype, value, regex, specialttype,
                     replacefunc=lambda x: x):
    last = 0
    for match in regex.finditer(value):
        start, end = match.start(), match.end()
        if start != last:
            yield ttype, value[last:start]
        yield specialttype, replacefunc(value[start:end])
        last = end
    if last != len(value):
        yield ttype, value[last:]


class CodeTagFilter(Filter):
    """Highlight special code tags in comments and docstrings.

    Options accepted:

    `codetags` : list of strings
       A list of strings that are flagged as code tags.  The default is to
       highlight ``XXX``, ``TODO``, ``FIXME``, ``BUG`` and ``NOTE``.

    .. versionchanged:: 2.13
       Now recognizes ``FIXME`` by default.
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        tags = get_list_opt(options, 'codetags',
                            ['XXX', 'TODO', 'FIXME', 'BUG', 'NOTE'])
        self.tag_re = re.compile(r'\b({})\b'.format('|'.join([
            re.escape(tag) for tag in tags if tag
        ])))

    def filter(self, lexer, stream):
        regex = self.tag_re
        for ttype, value in stream:
            if ttype in String.Doc or \
               ttype in Comment and \
               ttype not in Comment.Preproc:
                yield from _replace_special(ttype, value, regex, Comment.Special)
            else:
                yield ttype, value


class SymbolFilter(Filter):
    """Convert mathematical symbols such as \\<longrightarrow> in Isabelle
    or \\longrightarrow in LaTeX into Unicode characters.

    This is mostly useful for HTML or console output when you want to
    approximate the source rendering you'd see in an IDE.

    Options accepted:

    `lang` : string
       The symbol language. Must be one of ``'isabelle'`` or
       ``'latex'``.  The default is ``'isabelle'``.
    """

    latex_symbols = {
        '\\alpha'                : '\U000003b1',
        '\\beta'                 : '\U000003b2',
        '\\gamma'                : '\U000003b3',
        '\\delta'                : '\U000003b4',
        '\\varepsilon'           : '\U000003b5',
        '\\zeta'                 : '\U000003b6',
        '\\eta'                  : '\U000003b7',
        '\\vartheta'             : '\U000003b8',
        '\\iota'                 : '\U000003b9',
        '\\kappa'                : '\U000003ba',
        '\\lambda'               : '\U000003bb',
        '\\mu'                   : '\U000003bc',
        '\\nu'                   : '\U000003bd',
        '\\xi'                   : '\U000003be',
        '\\pi'                   : '\U000003c0',
        '\\varrho'               : '\U000003c1',
        '\\sigma'                : '\U000003c3',
        '\\tau'                  : '\U000003c4',
        '\\upsilon'              : '\U000003c5',
        '\\varphi'               : '\U000003c6',
        '\\chi'                  : '\U000003c7',
        '\\psi'                  : '\U000003c8',
        '\\omega'                : '\U000003c9',
        '\\Gamma'                : '\U00000393',
        '\\Delta'                : '\U00000394',
        '\\Theta'                : '\U00000398',
        '\\Lambda'               : '\U0000039b',
        '\\Xi'                   : '\U0000039e',
        '\\Pi'                   : '\U000003a0',
        '\\Sigma'                : '\U000003a3',
        '\\Upsilon'              : '\U000003a5',
        '\\Phi'                  : '\U000003a6',
        '\\Psi'                  : '\U000003a8',
        '\\Omega'                : '\U000003a9',
        '\\leftarrow'            : '\U00002190',
        '\\longleftarrow'        : '\U000027f5',
        '\\rightarrow'           : '\U00002192',
        '\\longrightarrow'       : '\U000027f6',
        '\\Leftarrow'            : '\U000021d0',
        '\\Longleftarrow'        : '\U000027f8',
        '\\Rightarrow'           : '\U000021d2',
        '\\Longrightarrow'       : '\U000027f9',
        '\\leftrightarrow'       : '\U00002194',
        '\\longleftrightarrow'   : '\U000027f7',
        '\\Leftrightarrow'       : '\U000021d4',
        '\\Longleftrightarrow'   : '\U000027fa',
        '\\mapsto'               : '\U000021a6',
        '\\longmapsto'           : '\U000027fc',
        '\\relbar'               : '\U00002500',
        '\\Relbar'               : '\U00002550',
        '\\hookleftarrow'        : '\U000021a9',
        '\\hookrightarrow'       : '\U000021aa',
        '\\leftharpoondown'      : '\U000021bd',
        '\\rightharpoondown'     : '\U000021c1',
        '\\leftharpoonup'        : '\U000021bc',
        '\\rightharpoonup'       : '\U000021c0',
        '\\rightleftharpoons'    : '\U000021cc',
        '\\leadsto'              : '\U0000219d',
        '\\downharpoonleft'      : '\U000021c3',
        '\\downharpoonright'     : '\U000021c2',
        '\\upharpoonleft'        : '\U000021bf',
        '\\upharpoonright'       : '\U000021be',
        '\\restriction'          : '\U000021be',
        '\\uparrow'              : '\U00002191',
        '\\Uparrow'              : '\U000021d1',
        '\\downarrow'            : '\U00002193',
        '\\Downarrow'            : '\U000021d3',
        '\\updownarrow'          : '\U00002195',
        '\\Updownarrow'          : '\U000021d5',
        '\\langle'               : '\U000027e8',
        '\\rangle'               : '\U000027e9',
        '\\lceil'                : '\U00002308',
        '\\rceil'                : '\U00002309',
        '\\lfloor'               : '\U0000230a',
        '\\rfloor'               : '\U0000230b',
        '\\flqq'                 : '\U000000ab',
        '\\frqq'                 : '\U000000bb',
        '\\bot'                  : '\U000022a5',
        '\\top'                  : '\U000022a4',
        '\\wedge'                : '\U00002227',
        '\\bigwedge'             : '\U000022c0',
        '\\vee'                  : '\U00002228',
        '\\bigvee'               : '\U000022c1',
        '\\forall'               : '\U00002200',
        '\\exists'               : '\U00002203',
        '\\nexists'              : '\U00002204',
        '\\neg'                  : '\U000000ac',
        '\\Box'                  : '\U000025a1',
        '\\Diamond'              : '\U000025c7',
        '\\vdash'                : '\U000022a2',
        '\\models'               : '\U000022a8',
        '\\dashv'                : '\U000022a3',
        '\\surd'                 : '\U0000221a',
        '\\le'                   : '\U00002264',
        '\\ge'                   : '\U00002265',
        '\\ll'                   : '\U0000226a',
        '\\gg'                   : '\U0000226b',
        '\\lesssim'              : '\U00002272',
        '\\gtrsim'               : '\U00002273',
        '\\lessapprox'           : '\U00002a85',
        '\\gtrapprox'            : '\U00002a86',
        '\\in'                   : '\U00002208',
        '\\notin'                : '\U00002209',
        '\\subset'               : '\U00002282',
        '\\supset'               : '\U00002283',
        '\\subseteq'             : '\U00002286',
        '\\supseteq'             : '\U00002287',
        '\\sqsubset'             : '\U0000228f',
        '\\sqsupset'             : '\U00002290',
        '\\sqsubseteq'           : '\U00002291',
        '\\sqsupseteq'           : '\U00002292',
        '\\cap'                  : '\U00002229',
        '\\bigcap'               : '\U000022c2',
        '\\cup'                  : '\U0000222a',
        '\\bigcup'               : '\U000022c3',
        '\\sqcup'                : '\U00002294',
        '\\bigsqcup'             : '\U00002a06',
        '\\sqcap'                : '\U00002293',
        '\\Bigsqcap'             : '\U00002a05',
        '\\setminus'             : '\U00002216',
        '\\propto'               : '\U0000221d',
        '\\uplus'                : '\U0000228e',
        '\\bigplus'              : '\U00002a04',
        '\\sim'                  : '\U0000223c',
        '\\doteq'                : '\U00002250',
        '\\simeq'                : '\U00002243',
        '\\approx'               : '\U00002248',
        '\\asymp'                : '\U0000224d',
        '\\cong'                 : '\U00002245',
        '\\equiv'                : '\U00002261',
        '\\Join'                 : '\U000022c8',
        '\\bowtie'               : '\U00002a1d',
        '\\prec'                 : '\U0000227a',
        '\\succ'                 : '\U0000227b',
        '\\preceq'               : '\U0000227c',
        '\\succeq'               : '\U0000227d',
        '\\parallel'             : '\U00002225',
        '\\mid'                  : '\U000000a6',
        '\\pm'                   : '\U000000b1',
        '\\mp'                   : '\U00002213',
        '\\times'                : '\U000000d7',
        '\\div'                  : '\U000000f7',
        '\\cdot'                 : '\U000022c5',
        '\\star'                 : '\U000022c6',
        '\\circ'                 : '\U00002218',
        '\\dagger'               : '\U00002020',
        '\\ddagger'              : '\U00002021',
        '\\lhd'                  : '\U000022b2',
        '\\rhd'                  : '\U000022b3',
        '\\unlhd'                : '\U000022b4',
        '\\unrhd'                : '\U000022b5',
        '\\triangleleft'         : '\U000025c3',
        '\\triangleright'        : '\U000025b9',
        '\\triangle'             : '\U000025b3',
        '\\triangleq'            : '\U0000225c',
        '\\oplus'                : '\U00002295',
        '\\bigoplus'             : '\U00002a01',
        '\\otimes'               : '\U00002297',
        '\\bigotimes'            : '\U00002a02',
        '\\odot'                 : '\U00002299',
        '\\bigodot'              : '\U00002a00',
        '\\ominus'               : '\U00002296',
        '\\oslash'               : '\U00002298',
        '\\dots'                 : '\U00002026',
        '\\cdots'                : '\U000022ef',
        '\\sum'                  : '\U00002211',
        '\\prod'                 : '\U0000220f',
        '\\coprod'               : '\U00002210',
        '\\infty'                : '\U0000221e',
        '\\int'                  : '\U0000222b',
        '\\oint'                 : '\U0000222e',
        '\\clubsuit'             : '\U00002663',
        '\\diamondsuit'          : '\U00002662',
        '\\heartsuit'            : '\U00002661',
        '\\spadesuit'            : '\U00002660',
        '\\aleph'                : '\U00002135',
        '\\emptyset'             : '\U00002205',
        '\\nabla'                : '\U00002207',
        '\\partial'              : '\U00002202',
        '\\flat'                 : '\U0000266d',
        '\\natural'              : '\U0000266e',
        '\\sharp'                : '\U0000266f',
        '\\angle'                : '\U00002220',
        '\\copyright'            : '\U000000a9',
        '\\textregistered'       : '\U000000ae',
        '\\textonequarter'       : '\U000000bc',
        '\\textonehalf'          : '\U000000bd',
        '\\textthreequarters'    : '\U000000be',
        '\\textordfeminine'      : '\U000000aa',
        '\\textordmasculine'     : '\U000000ba',
        '\\euro'                 : '\U000020ac',
        '\\pounds'               : '\U000000a3',
        '\\yen'                  : '\U000000a5',
        '\\textcent'             : '\U000000a2',
        '\\textcurrency'         : '\U000000a4',
        '\\textdegree'           : '\U000000b0',
    }

    isabelle_symbols = {
        '\\<zero>'                 : '\U0001d7ec',
        '\\<one>'                  : '\U0001d7ed',
        '\\<two>'                  : '\U0001d7ee',
        '\\<three>'                : '\U0001d7ef',
        '\\<four>'                 : '\U0001d7f0',
        '\\<five>'                 : '\U0001d7f1',
        '\\<six>'                  : '\U0001d7f2',
        '\\<seven>'                : '\U0001d7f3',
        '\\<eight>'                : '\U0001d7f4',
        '\\<nine>'                 : '\U0001d7f5',
        '\\<A>'                    : '\U0001d49c',
        '\\<B>'                    : '\U0000212c',
        '\\<C>'                    : '\U0001d49e',
        '\\<D>'                    : '\U0001d49f',
        '\\<E>'                    : '\U00002130',
        '\\<F>'                    : '\U00002131',
        '\\<G>'                    : '\U0001d4a2',
        '\\<H>'                    : '\U0000210b',
        '\\<I>'                    : '\U00002110',
        '\\<J>'                    : '\U0001d4a5',
        '\\<K>'                    : '\U0001d4a6',
        '\\<L>'                    : '\U00002112',
        '\\<M>'                    : '\U00002133',
        '\\<N>'                    : '\U0001d4a9',
        '\\<O>'                    : '\U0001d4aa',
        '\\<P>'                    : '\U0001d4ab',
        '\\<Q>'                    : '\U0001d4ac',
        '\\<R>'                    : '\U0000211b',
        '\\<S>'                    : '\U0001d4ae',
        '\\<T>'                    : '\U0001d4af',
        '\\<U>'                    : '\U0001d4b0',
        '\\<V>'                    : '\U0001d4b1',
        '\\<W>'                    : '\U0001d4b2',
        '\\<X>'                    : '\U0001d4b3',
        '\\<Y>'                    : '\U0001d4b4',
        '\\<Z>'                    : '\U0001d4b5',
        '\\<a>'                    : '\U0001d5ba',
        '\\<b>'                    : '\U0001d5bb',
        '\\<c>'                    : '\U0001d5bc',
        '\\<d>'                    : '\U0001d5bd',
        '\\<e>'                    : '\U0001d5be',
        '\\<f>'                    : '\U0001d5bf',
        '\\<g>'                    : '\U0001d5c0',
        '\\<h>'                    : '\U0001d5c1',
        '\\<i>'                    : '\U0001d5c2',
        '\\<j>'                    : '\U0001d5c3',
        '\\<k>'                    : '\U0001d5c4',
        '\\<l>'                    : '\U0001d5c5',
        '\\<m>'                    : '\U0001d5c6',
        '\\<n>'                    : '\U0001d5c7',
        '\\<o>'                    : '\U0001d5c8',
        '\\<p>'                    : '\U0001d5c9',
        '\\<q>'                    : '\U0001d5ca',
        '\\<r>'                    : '\U0001d5cb',
        '\\<s>'                    : '\U0001d5cc',
        '\\<t>'                    : '\U0001d5cd',
        '\\<u>'                    : '\U0001d5ce',
        '\\<v>'                    : '\U0001d5cf',
        '\\<w>'                    : '\U0001d5d0',
        '\\<x>'                    : '\U0001d5d1',
        '\\<y>'                    : '\U0001d5d2',
        '\\<z>'                    : '\U0001d5d3',
        '\\<AA>'                   : '\U0001d504',
        '\\<BB>'                   : '\U0001d505',
        '\\<CC>'                   : '\U0000212d',
        '\\<DD>'                   : '\U0001d507',
        '\\<EE>'                   : '\U0001d508',
        '\\<FF>'                   : '\U0001d509',
        '\\<GG>'                   : '\U0001d50a',
        '\\<HH>'                   : '\U0000210c',
        '\\<II>'                   : '\U00002111',
        '\\<JJ>'                   : '\U0001d50d',
        '\\<KK>'                   : '\U0001d50e',
        '\\<LL>'                   : '\U0001d50f',
        '\\<MM>'                   : '\U0001d510',
        '\\<NN>'                   : '\U0001d511',
        '\\<OO>'                   : '\U0001d512',
        '\\<PP>'                   : '\U0001d513',
        '\\<QQ>'                   : '\U0001d514',
        '\\<RR>'                   : '\U0000211c',
        '\\<SS>'                   : '\U0001d516',
        '\\<TT>'                   : '\U0001d517',
        '\\<UU>'                   : '\U0001d518',
        '\\<VV>'                   : '\U0001d519',
        '\\<WW>'                   : '\U0001d51a',
        '\\<XX>'                   : '\U0001d51b',
        '\\<YY>'                   : '\U0001d51c',
        '\\<ZZ>'                   : '\U00002128',
        '\\<aa>'                   : '\U0001d51e',
        '\\<bb>'                   : '\U0001d51f',
        '\\<cc>'                   : '\U0001d520',
        '\\<dd>'                   : '\U0001d521',
        '\\<ee>'                   : '\U0001d522',
        '\\<ff>'                   : '\U0001d523',
        '\\<gg>'                   : '\U0001d524',
        '\\<hh>'                   : '\U0001d525',
        '\\<ii>'                   : '\U0001d526',
        '\\<jj>'                   : '\U0001d527',
        '\\<kk>'                   : '\U0001d528',
        '\\<ll>'                   : '\U0001d529',
        '\\<mm>'                   : '\U0001d52a',
        '\\<nn>'                   : '\U0001d52b',
        '\\<oo>'                   : '\U0001d52c',
        '\\<pp>'                   : '\U0001d52d',
        '\\<qq>'                   : '\U0001d52e',
        '\\<rr>'                   : '\U0001d52f',
        '\\<ss>'                   : '\U0001d530',
        '\\<tt>'                   : '\U0001d531',
        '\\<uu>'                   : '\U0001d532',
        '\\<vv>'                   : '\U0001d533',
        '\\<ww>'                   : '\U0001d534',
        '\\<xx>'                   : '\U0001d535',
        '\\<yy>'                   : '\U0001d536',
        '\\<zz>'                   : '\U0001d537',
        '\\<alpha>'                : '\U000003b1',
        '\\<beta>'                 : '\U000003b2',
        '\\<gamma>'                : '\U000003b3',
        '\\<delta>'                : '\U000003b4',
        '\\<epsilon>'              : '\U000003b5',
        '\\<zeta>'                 : '\U000003b6',
        '\\<eta>'                  : '\U000003b7',
        '\\<theta>'                : '\U000003b8',
        '\\<iota>'                 : '\U000003b9',
        '\\<kappa>'                : '\U000003ba',
        '\\<lambda>'               : '\U000003bb',
        '\\<mu>'                   : '\U000003bc',
        '\\<nu>'                   : '\U000003bd',
        '\\<xi>'                   : '\U000003be',
        '\\<pi>'                   : '\U000003c0',
        '\\<rho>'                  : '\U000003c1',
        '\\<sigma>'                : '\U000003c3',
        '\\<tau>'                  : '\U000003c4',
        '\\<upsilon>'              : '\U000003c5',
        '\\<phi>'                  : '\U000003c6',
        '\\<chi>'                  : '\U000003c7',
        '\\<psi>'                  : '\U000003c8',
        '\\<omega>'                : '\U000003c9',
        '\\<Gamma>'                : '\U00000393',
        '\\<Delta>'                : '\U00000394',
        '\\<Theta>'                : '\U00000398',
        '\\<Lambda>'               : '\U0000039b',
        '\\<Xi>'                   : '\U0000039e',
        '\\<Pi>'                   : '\U000003a0',
        '\\<Sigma>'                : '\U000003a3',
        '\\<Upsilon>'              : '\U000003a5',
        '\\<Phi>'                  : '\U000003a6',
        '\\<Psi>'                  : '\U000003a8',
        '\\<Omega>'                : '\U000003a9',
        '\\<bool>'                 : '\U0001d539',
        '\\<complex>'              : '\U00002102',
        '\\<nat>'                  : '\U00002115',
        '\\<rat>'                  : '\U0000211a',
        '\\<real>'                 : '\U0000211d',
        '\\<int>'                  : '\U00002124',
        '\\<leftarrow>'            : '\U00002190',
        '\\<longleftarrow>'        : '\U000027f5',
        '\\<rightarrow>'           : '\U00002192',
        '\\<longrightarrow>'       : '\U000027f6',
        '\\<Leftarrow>'            : '\U000021d0',
        '\\<Longleftarrow>'        : '\U000027f8',
        '\\<Rightarrow>'           : '\U000021d2',
        '\\<Longrightarrow>'       : '\U000027f9',
        '\\<leftrightarrow>'       : '\U00002194',
        '\\<longleftrightarrow>'   : '\U000027f7',
        '\\<Leftrightarrow>'       : '\U000021d4',
        '\\<Longleftrightarrow>'   : '\U000027fa',
        '\\<mapsto>'               : '\U000021a6',
        '\\<longmapsto>'           : '\U000027fc',
        '\\<midarrow>'             : '\U00002500',
        '\\<Midarrow>'             : '\U00002550',
        '\\<hookleftarrow>'        : '\U000021a9',
        '\\<hookrightarrow>'       : '\U000021aa',
        '\\<leftharpoondown>'      : '\U000021bd',
        '\\<rightharpoondown>'     : '\U000021c1',
        '\\<leftharpoonup>'        : '\U000021bc',
        '\\<rightharpoonup>'       : '\U000021c0',
        '\\<rightleftharpoons>'    : '\U000021cc',
        '\\<leadsto>'              : '\U0000219d',
        '\\<downharpoonleft>'      : '\U000021c3',
        '\\<downharpoonright>'     : '\U000021c2',
        '\\<upharpoonleft>'        : '\U000021bf',
        '\\<upharpoonright>'       : '\U000021be',
        '\\<restriction>'          : '\U000021be',
        '\\<Colon>'                : '\U00002237',
        '\\<up>'                   : '\U00002191',
        '\\<Up>'                   : '\U000021d1',
        '\\<down>'                 : '\U00002193',
        '\\<Down>'                 : '\U000021d3',
        '\\<updown>'               : '\U00002195',
        '\\<Updown>'               : '\U000021d5',
        '\\<langle>'               : '\U000027e8',
        '\\<rangle>'               : '\U000027e9',
        '\\<lceil>'                : '\U00002308',
        '\\<rceil>'                : '\U00002309',
        '\\<lfloor>'               : '\U0000230a',
        '\\<rfloor>'               : '\U0000230b',
        '\\<lparr>'                : '\U00002987',
        '\\<rparr>'                : '\U00002988',
        '\\<lbrakk>'               : '\U000027e6',
        '\\<rbrakk>'               : '\U000027e7',
        '\\<lbrace>'               : '\U00002983',
        '\\<rbrace>'               : '\U00002984',
        '\\<guillemotleft>'        : '\U000000ab',
        '\\<guillemotright>'       : '\U000000bb',
        '\\<bottom>'               : '\U000022a5',
        '\\<top>'                  : '\U000022a4',
        '\\<and>'                  : '\U00002227',
        '\\<And>'                  : '\U000022c0',
        '\\<or>'                   : '\U00002228',
        '\\<Or>'                   : '\U000022c1',
        '\\<forall>'               : '\U00002200',
        '\\<exists>'               : '\U00002203',
        '\\<nexists>'              : '\U00002204',
        '\\<not>'                  : '\U000000ac',
        '\\<box>'                  : '\U000025a1',
        '\\<diamond>'              : '\U000025c7',
        '\\<turnstile>'            : '\U000022a2',
        '\\<Turnstile>'            : '\U000022a8',
        '\\<tturnstile>'           : '\U000022a9',
        '\\<TTurnstile>'           : '\U000022ab',
        '\\<stileturn>'            : '\U000022a3',
        '\\<surd>'                 : '\U0000221a',
        '\\<le>'                   : '\U00002264',
        '\\<ge>'                   : '\U00002265',
        '\\<lless>'                : '\U0000226a',
        '\\<ggreater>'             : '\U0000226b',
        '\\<lesssim>'              : '\U00002272',
        '\\<greatersim>'           : '\U00002273',
        '\\<lessapprox>'           : '\U00002a85',
        '\\<greaterapprox>'        : '\U00002a86',
        '\\<in>'                   : '\U00002208',
        '\\<notin>'                : '\U00002209',
        '\\<subset>'               : '\U00002282',
        '\\<supset>'               : '\U00002283',
        '\\<subseteq>'             : '\U00002286',
        '\\<supseteq>'             : '\U00002287',
        '\\<sqsubset>'             : '\U0000228f',
        '\\<sqsupset>'             : '\U00002290',
        '\\<sqsubseteq>'           : '\U00002291',
        '\\<sqsupseteq>'           : '\U00002292',
        '\\<inter>'                : '\U00002229',
        '\\<Inter>'                : '\U000022c2',
        '\\<union>'                : '\U0000222a',
        '\\<Union>'                : '\U000022c3',
        '\\<squnion>'              : '\U00002294',
        '\\<Squnion>'              : '\U00002a06',
        '\\<sqinter>'              : '\U00002293',
        '\\<Sqinter>'              : '\U00002a05',
        '\\<setminus>'             : '\U00002216',
        '\\<propto>'               : '\U0000221d',
        '\\<uplus>'                : '\U0000228e',
        '\\<Uplus>'                : '\U00002a04',
        '\\<noteq>'                : '\U00002260',
        '\\<sim>'                  : '\U0000223c',
        '\\<doteq>'                : '\U00002250',
        '\\<simeq>'                : '\U00002243',
        '\\<approx>'               : '\U00002248',
        '\\<asymp>'                : '\U0000224d',
        '\\<cong>'                 : '\U00002245',
        '\\<smile>'                : '\U00002323',
        '\\<equiv>'                : '\U00002261',
        '\\<frown>'                : '\U00002322',
        '\\<Join>'                 : '\U000022c8',
        '\\<bowtie>'               : '\U00002a1d',
        '\\<prec>'                 : '\U0000227a',
        '\\<succ>'                 : '\U0000227b',
        '\\<preceq>'               : '\U0000227c',
        '\\<succeq>'               : '\U0000227d',
        '\\<parallel>'             : '\U00002225',
        '\\<bar>'                  : '\U000000a6',
        '\\<plusminus>'            : '\U000000b1',
        '\\<minusplus>'            : '\U00002213',
        '\\<times>'                : '\U000000d7',
        '\\<div>'                  : '\U000000f7',
        '\\<cdot>'                 : '\U000022c5',
        '\\<star>'                 : '\U000022c6',
        '\\<bullet>'               : '\U00002219',
        '\\<circ>'                 : '\U00002218',
        '\\<dagger>'               : '\U00002020',
        '\\<ddagger>'              : '\U00002021',
        '\\<lhd>'                  : '\U000022b2',
        '\\<rhd>'                  : '\U000022b3',
        '\\<unlhd>'                : '\U000022b4',
        '\\<unrhd>'                : '\U000022b5',
        '\\<triangleleft>'         : '\U000025c3',
        '\\<triangleright>'        : '\U000025b9',
        '\\<triangle>'             : '\U000025b3',
        '\\<triangleq>'            : '\U0000225c',
        '\\<oplus>'                : '\U00002295',
        '\\<Oplus>'                : '\U00002a01',
        '\\<otimes>'               : '\U00002297',
        '\\<Otimes>'               : '\U00002a02',
        '\\<odot>'                 : '\U00002299',
        '\\<Odot>'                 : '\U00002a00',
        '\\<ominus>'               : '\U00002296',
        '\\<oslash>'               : '\U00002298',
        '\\<dots>'                 : '\U00002026',
        '\\<cdots>'                : '\U000022ef',
        '\\<Sum>'                  : '\U00002211',
        '\\<Prod>'                 : '\U0000220f',
        '\\<Coprod>'               : '\U00002210',
        '\\<infinity>'             : '\U0000221e',
        '\\<integral>'             : '\U0000222b',
        '\\<ointegral>'            : '\U0000222e',
        '\\<clubsuit>'             : '\U00002663',
        '\\<diamondsuit>'          : '\U00002662',
        '\\<heartsuit>'            : '\U00002661',
        '\\<spadesuit>'            : '\U00002660',
        '\\<aleph>'                : '\U00002135',
        '\\<emptyset>'             : '\U00002205',
        '\\<nabla>'                : '\U00002207',
        '\\<partial>'              : '\U00002202',
        '\\<flat>'                 : '\U0000266d',
        '\\<natural>'              : '\U0000266e',
        '\\<sharp>'                : '\U0000266f',
        '\\<angle>'                : '\U00002220',
        '\\<copyright>'            : '\U000000a9',
        '\\<registered>'           : '\U000000ae',
        '\\<hyphen>'               : '\U000000ad',
        '\\<inverse>'              : '\U000000af',
        '\\<onequarter>'           : '\U000000bc',
        '\\<onehalf>'              : '\U000000bd',
        '\\<threequarters>'        : '\U000000be',
        '\\<ordfeminine>'          : '\U000000aa',
        '\\<ordmasculine>'         : '\U000000ba',
        '\\<section>'              : '\U000000a7',
        '\\<paragraph>'            : '\U000000b6',
        '\\<exclamdown>'           : '\U000000a1',
        '\\<questiondown>'         : '\U000000bf',
        '\\<euro>'                 : '\U000020ac',
        '\\<pounds>'               : '\U000000a3',
        '\\<yen>'                  : '\U000000a5',
        '\\<cent>'                 : '\U000000a2',
        '\\<currency>'             : '\U000000a4',
        '\\<degree>'               : '\U000000b0',
        '\\<amalg>'                : '\U00002a3f',
        '\\<mho>'                  : '\U00002127',
        '\\<lozenge>'              : '\U000025ca',
        '\\<wp>'                   : '\U00002118',
        '\\<wrong>'                : '\U00002240',
        '\\<struct>'               : '\U000022c4',
        '\\<acute>'                : '\U000000b4',
        '\\<index>'                : '\U00000131',
        '\\<dieresis>'             : '\U000000a8',
        '\\<cedilla>'              : '\U000000b8',
        '\\<hungarumlaut>'         : '\U000002dd',
        '\\<some>'                 : '\U000003f5',
        '\\<newline>'              : '\U000023ce',
        '\\<open>'                 : '\U00002039',
        '\\<close>'                : '\U0000203a',
        '\\<here>'                 : '\U00002302',
        '\\<^sub>'                 : '\U000021e9',
        '\\<^sup>'                 : '\U000021e7',
        '\\<^bold>'                : '\U00002759',
        '\\<^bsub>'                : '\U000021d8',
        '\\<^esub>'                : '\U000021d9',
        '\\<^bsup>'                : '\U000021d7',
        '\\<^esup>'                : '\U000021d6',
    }

    lang_map = {'isabelle' : isabelle_symbols, 'latex' : latex_symbols}

    def __init__(self, **options):
        Filter.__init__(self, **options)
        lang = get_choice_opt(options, 'lang',
                              ['isabelle', 'latex'], 'isabelle')
        self.symbols = self.lang_map[lang]

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if value in self.symbols:
                yield ttype, self.symbols[value]
            else:
                yield ttype, value


class KeywordCaseFilter(Filter):
    """Convert keywords to lowercase or uppercase or capitalize them, which
    means first letter uppercase, rest lowercase.

    This can be useful e.g. if you highlight Pascal code and want to adapt the
    code to your styleguide.

    Options accepted:

    `case` : string
       The casing to convert keywords to. Must be one of ``'lower'``,
       ``'upper'`` or ``'capitalize'``.  The default is ``'lower'``.
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        case = get_choice_opt(options, 'case',
                              ['lower', 'upper', 'capitalize'], 'lower')
        self.convert = getattr(str, case)

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if ttype in Keyword:
                yield ttype, self.convert(value)
            else:
                yield ttype, value


class NameHighlightFilter(Filter):
    """Highlight a normal Name (and Name.*) token with a different token type.

    Example::

        filter = NameHighlightFilter(
            names=['foo', 'bar', 'baz'],
            tokentype=Name.Function,
        )

    This would highlight the names "foo", "bar" and "baz"
    as functions. `Name.Function` is the default token type.

    Options accepted:

    `names` : list of strings
      A list of names that should be given the different token type.
      There is no default.
    `tokentype` : TokenType or string
      A token type or a string containing a token type name that is
      used for highlighting the strings in `names`.  The default is
      `Name.Function`.
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        self.names = set(get_list_opt(options, 'names', []))
        tokentype = options.get('tokentype')
        if tokentype:
            self.tokentype = string_to_tokentype(tokentype)
        else:
            self.tokentype = Name.Function

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if ttype in Name and value in self.names:
                yield self.tokentype, value
            else:
                yield ttype, value


class ErrorToken(Exception):
    pass


class RaiseOnErrorTokenFilter(Filter):
    """Raise an exception when the lexer generates an error token.

    Options accepted:

    `excclass` : Exception class
      The exception class to raise.
      The default is `pygments.filters.ErrorToken`.

    .. versionadded:: 0.8
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        self.exception = options.get('excclass', ErrorToken)
        try:
            # issubclass() will raise TypeError if first argument is not a class
            if not issubclass(self.exception, Exception):
                raise TypeError
        except TypeError:
            raise OptionError('excclass option is not an exception class')

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if ttype is Error:
                raise self.exception(value)
            yield ttype, value


class VisibleWhitespaceFilter(Filter):
    """Convert tabs, newlines and/or spaces to visible characters.

    Options accepted:

    `spaces` : string or bool
      If this is a one-character string, spaces will be replaces by this string.
      If it is another true value, spaces will be replaced by ``·`` (unicode
      MIDDLE DOT).  If it is a false value, spaces will not be replaced.  The
      default is ``False``.
    `tabs` : string or bool
      The same as for `spaces`, but the default replacement character is ``»``
      (unicode RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK).  The default value
      is ``False``.  Note: this will not work if the `tabsize` option for the
      lexer is nonzero, as tabs will already have been expanded then.
    `tabsize` : int
      If tabs are to be replaced by this filter (see the `tabs` option), this
      is the total number of characters that a tab should be expanded to.
      The default is ``8``.
    `newlines` : string or bool
      The same as for `spaces`, but the default replacement character is ``¶``
      (unicode PILCROW SIGN).  The default value is ``False``.
    `wstokentype` : bool
      If true, give whitespace the special `Whitespace` token type.  This allows
      styling the visible whitespace differently (e.g. greyed out), but it can
      disrupt background colors.  The default is ``True``.

    .. versionadded:: 0.8
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        for name, default in [('spaces',   '·'),
                              ('tabs',     '»'),
                              ('newlines', '¶')]:
            opt = options.get(name, False)
            if isinstance(opt, str) and len(opt) == 1:
                setattr(self, name, opt)
            else:
                setattr(self, name, (opt and default or ''))
        tabsize = get_int_opt(options, 'tabsize', 8)
        if self.tabs:
            self.tabs += ' ' * (tabsize - 1)
        if self.newlines:
            self.newlines += '\n'
        self.wstt = get_bool_opt(options, 'wstokentype', True)

    def filter(self, lexer, stream):
        if self.wstt:
            spaces = self.spaces or ' '
            tabs = self.tabs or '\t'
            newlines = self.newlines or '\n'
            regex = re.compile(r'\s')

            def replacefunc(wschar):
                if wschar == ' ':
                    return spaces
                elif wschar == '\t':
                    return tabs
                elif wschar == '\n':
                    return newlines
                return wschar

            for ttype, value in stream:
                yield from _replace_special(ttype, value, regex, Whitespace,
                                            replacefunc)
        else:
            spaces, tabs, newlines = self.spaces, self.tabs, self.newlines
            # simpler processing
            for ttype, value in stream:
                if spaces:
                    value = value.replace(' ', spaces)
                if tabs:
                    value = value.replace('\t', tabs)
                if newlines:
                    value = value.replace('\n', newlines)
                yield ttype, value


class GobbleFilter(Filter):
    """Gobbles source code lines (eats initial characters).

    This filter drops the first ``n`` characters off every line of code.  This
    may be useful when the source code fed to the lexer is indented by a fixed
    amount of space that isn't desired in the output.

    Options accepted:

    `n` : int
       The number of characters to gobble.

    .. versionadded:: 1.2
    """
    def __init__(self, **options):
        Filter.__init__(self, **options)
        self.n = get_int_opt(options, 'n', 0)

    def gobble(self, value, left):
        if left < len(value):
            return value[left:], 0
        else:
            return '', left - len(value)

    def filter(self, lexer, stream):
        n = self.n
        left = n  # How many characters left to gobble.
        for ttype, value in stream:
            # Remove ``left`` tokens from first line, ``n`` from all others.
            parts = value.split('\n')
            (parts[0], left) = self.gobble(parts[0], left)
            for i in range(1, len(parts)):
                (parts[i], left) = self.gobble(parts[i], n)
            value = '\n'.join(parts)

            if value != '':
                yield ttype, value


class TokenMergeFilter(Filter):
    """Merges consecutive tokens with the same token type in the output
    stream of a lexer.

    .. versionadded:: 1.2
    """
    def __init__(self, **options):
        Filter.__init__(self, **options)

    def filter(self, lexer, stream):
        current_type = None
        current_value = None
        for ttype, value in stream:
            if ttype is current_type:
                current_value += value
            else:
                if current_type is not None:
                    yield current_type, current_value
                current_type = ttype
                current_value = value
        if current_type is not None:
            yield current_type, current_value


FILTERS = {
    'codetagify':     CodeTagFilter,
    'keywordcase':    KeywordCaseFilter,
    'highlight':      NameHighlightFilter,
    'raiseonerror':   RaiseOnErrorTokenFilter,
    'whitespace':     VisibleWhitespaceFilter,
    'gobble':         GobbleFilter,
    'tokenmerge':     TokenMergeFilter,
    'symbols':        SymbolFilter,
}

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\filters\__init__.py ===
"""
    pygments.filters
    ~~~~~~~~~~~~~~~~

    Module containing filter lookup functions and default
    filters.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pip._vendor.pygments.token import String, Comment, Keyword, Name, Error, Whitespace, \
    string_to_tokentype
from pip._vendor.pygments.filter import Filter
from pip._vendor.pygments.util import get_list_opt, get_int_opt, get_bool_opt, \
    get_choice_opt, ClassNotFound, OptionError
from pip._vendor.pygments.plugin import find_plugin_filters


def find_filter_class(filtername):
    """Lookup a filter by name. Return None if not found."""
    if filtername in FILTERS:
        return FILTERS[filtername]
    for name, cls in find_plugin_filters():
        if name == filtername:
            return cls
    return None


def get_filter_by_name(filtername, **options):
    """Return an instantiated filter.

    Options are passed to the filter initializer if wanted.
    Raise a ClassNotFound if not found.
    """
    cls = find_filter_class(filtername)
    if cls:
        return cls(**options)
    else:
        raise ClassNotFound(f'filter {filtername!r} not found')


def get_all_filters():
    """Return a generator of all filter names."""
    yield from FILTERS
    for name, _ in find_plugin_filters():
        yield name


def _replace_special(ttype, value, regex, specialttype,
                     replacefunc=lambda x: x):
    last = 0
    for match in regex.finditer(value):
        start, end = match.start(), match.end()
        if start != last:
            yield ttype, value[last:start]
        yield specialttype, replacefunc(value[start:end])
        last = end
    if last != len(value):
        yield ttype, value[last:]


class CodeTagFilter(Filter):
    """Highlight special code tags in comments and docstrings.

    Options accepted:

    `codetags` : list of strings
       A list of strings that are flagged as code tags.  The default is to
       highlight ``XXX``, ``TODO``, ``FIXME``, ``BUG`` and ``NOTE``.

    .. versionchanged:: 2.13
       Now recognizes ``FIXME`` by default.
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        tags = get_list_opt(options, 'codetags',
                            ['XXX', 'TODO', 'FIXME', 'BUG', 'NOTE'])
        self.tag_re = re.compile(r'\b({})\b'.format('|'.join([
            re.escape(tag) for tag in tags if tag
        ])))

    def filter(self, lexer, stream):
        regex = self.tag_re
        for ttype, value in stream:
            if ttype in String.Doc or \
               ttype in Comment and \
               ttype not in Comment.Preproc:
                yield from _replace_special(ttype, value, regex, Comment.Special)
            else:
                yield ttype, value


class SymbolFilter(Filter):
    """Convert mathematical symbols such as \\<longrightarrow> in Isabelle
    or \\longrightarrow in LaTeX into Unicode characters.

    This is mostly useful for HTML or console output when you want to
    approximate the source rendering you'd see in an IDE.

    Options accepted:

    `lang` : string
       The symbol language. Must be one of ``'isabelle'`` or
       ``'latex'``.  The default is ``'isabelle'``.
    """

    latex_symbols = {
        '\\alpha'                : '\U000003b1',
        '\\beta'                 : '\U000003b2',
        '\\gamma'                : '\U000003b3',
        '\\delta'                : '\U000003b4',
        '\\varepsilon'           : '\U000003b5',
        '\\zeta'                 : '\U000003b6',
        '\\eta'                  : '\U000003b7',
        '\\vartheta'             : '\U000003b8',
        '\\iota'                 : '\U000003b9',
        '\\kappa'                : '\U000003ba',
        '\\lambda'               : '\U000003bb',
        '\\mu'                   : '\U000003bc',
        '\\nu'                   : '\U000003bd',
        '\\xi'                   : '\U000003be',
        '\\pi'                   : '\U000003c0',
        '\\varrho'               : '\U000003c1',
        '\\sigma'                : '\U000003c3',
        '\\tau'                  : '\U000003c4',
        '\\upsilon'              : '\U000003c5',
        '\\varphi'               : '\U000003c6',
        '\\chi'                  : '\U000003c7',
        '\\psi'                  : '\U000003c8',
        '\\omega'                : '\U000003c9',
        '\\Gamma'                : '\U00000393',
        '\\Delta'                : '\U00000394',
        '\\Theta'                : '\U00000398',
        '\\Lambda'               : '\U0000039b',
        '\\Xi'                   : '\U0000039e',
        '\\Pi'                   : '\U000003a0',
        '\\Sigma'                : '\U000003a3',
        '\\Upsilon'              : '\U000003a5',
        '\\Phi'                  : '\U000003a6',
        '\\Psi'                  : '\U000003a8',
        '\\Omega'                : '\U000003a9',
        '\\leftarrow'            : '\U00002190',
        '\\longleftarrow'        : '\U000027f5',
        '\\rightarrow'           : '\U00002192',
        '\\longrightarrow'       : '\U000027f6',
        '\\Leftarrow'            : '\U000021d0',
        '\\Longleftarrow'        : '\U000027f8',
        '\\Rightarrow'           : '\U000021d2',
        '\\Longrightarrow'       : '\U000027f9',
        '\\leftrightarrow'       : '\U00002194',
        '\\longleftrightarrow'   : '\U000027f7',
        '\\Leftrightarrow'       : '\U000021d4',
        '\\Longleftrightarrow'   : '\U000027fa',
        '\\mapsto'               : '\U000021a6',
        '\\longmapsto'           : '\U000027fc',
        '\\relbar'               : '\U00002500',
        '\\Relbar'               : '\U00002550',
        '\\hookleftarrow'        : '\U000021a9',
        '\\hookrightarrow'       : '\U000021aa',
        '\\leftharpoondown'      : '\U000021bd',
        '\\rightharpoondown'     : '\U000021c1',
        '\\leftharpoonup'        : '\U000021bc',
        '\\rightharpoonup'       : '\U000021c0',
        '\\rightleftharpoons'    : '\U000021cc',
        '\\leadsto'              : '\U0000219d',
        '\\downharpoonleft'      : '\U000021c3',
        '\\downharpoonright'     : '\U000021c2',
        '\\upharpoonleft'        : '\U000021bf',
        '\\upharpoonright'       : '\U000021be',
        '\\restriction'          : '\U000021be',
        '\\uparrow'              : '\U00002191',
        '\\Uparrow'              : '\U000021d1',
        '\\downarrow'            : '\U00002193',
        '\\Downarrow'            : '\U000021d3',
        '\\updownarrow'          : '\U00002195',
        '\\Updownarrow'          : '\U000021d5',
        '\\langle'               : '\U000027e8',
        '\\rangle'               : '\U000027e9',
        '\\lceil'                : '\U00002308',
        '\\rceil'                : '\U00002309',
        '\\lfloor'               : '\U0000230a',
        '\\rfloor'               : '\U0000230b',
        '\\flqq'                 : '\U000000ab',
        '\\frqq'                 : '\U000000bb',
        '\\bot'                  : '\U000022a5',
        '\\top'                  : '\U000022a4',
        '\\wedge'                : '\U00002227',
        '\\bigwedge'             : '\U000022c0',
        '\\vee'                  : '\U00002228',
        '\\bigvee'               : '\U000022c1',
        '\\forall'               : '\U00002200',
        '\\exists'               : '\U00002203',
        '\\nexists'              : '\U00002204',
        '\\neg'                  : '\U000000ac',
        '\\Box'                  : '\U000025a1',
        '\\Diamond'              : '\U000025c7',
        '\\vdash'                : '\U000022a2',
        '\\models'               : '\U000022a8',
        '\\dashv'                : '\U000022a3',
        '\\surd'                 : '\U0000221a',
        '\\le'                   : '\U00002264',
        '\\ge'                   : '\U00002265',
        '\\ll'                   : '\U0000226a',
        '\\gg'                   : '\U0000226b',
        '\\lesssim'              : '\U00002272',
        '\\gtrsim'               : '\U00002273',
        '\\lessapprox'           : '\U00002a85',
        '\\gtrapprox'            : '\U00002a86',
        '\\in'                   : '\U00002208',
        '\\notin'                : '\U00002209',
        '\\subset'               : '\U00002282',
        '\\supset'               : '\U00002283',
        '\\subseteq'             : '\U00002286',
        '\\supseteq'             : '\U00002287',
        '\\sqsubset'             : '\U0000228f',
        '\\sqsupset'             : '\U00002290',
        '\\sqsubseteq'           : '\U00002291',
        '\\sqsupseteq'           : '\U00002292',
        '\\cap'                  : '\U00002229',
        '\\bigcap'               : '\U000022c2',
        '\\cup'                  : '\U0000222a',
        '\\bigcup'               : '\U000022c3',
        '\\sqcup'                : '\U00002294',
        '\\bigsqcup'             : '\U00002a06',
        '\\sqcap'                : '\U00002293',
        '\\Bigsqcap'             : '\U00002a05',
        '\\setminus'             : '\U00002216',
        '\\propto'               : '\U0000221d',
        '\\uplus'                : '\U0000228e',
        '\\bigplus'              : '\U00002a04',
        '\\sim'                  : '\U0000223c',
        '\\doteq'                : '\U00002250',
        '\\simeq'                : '\U00002243',
        '\\approx'               : '\U00002248',
        '\\asymp'                : '\U0000224d',
        '\\cong'                 : '\U00002245',
        '\\equiv'                : '\U00002261',
        '\\Join'                 : '\U000022c8',
        '\\bowtie'               : '\U00002a1d',
        '\\prec'                 : '\U0000227a',
        '\\succ'                 : '\U0000227b',
        '\\preceq'               : '\U0000227c',
        '\\succeq'               : '\U0000227d',
        '\\parallel'             : '\U00002225',
        '\\mid'                  : '\U000000a6',
        '\\pm'                   : '\U000000b1',
        '\\mp'                   : '\U00002213',
        '\\times'                : '\U000000d7',
        '\\div'                  : '\U000000f7',
        '\\cdot'                 : '\U000022c5',
        '\\star'                 : '\U000022c6',
        '\\circ'                 : '\U00002218',
        '\\dagger'               : '\U00002020',
        '\\ddagger'              : '\U00002021',
        '\\lhd'                  : '\U000022b2',
        '\\rhd'                  : '\U000022b3',
        '\\unlhd'                : '\U000022b4',
        '\\unrhd'                : '\U000022b5',
        '\\triangleleft'         : '\U000025c3',
        '\\triangleright'        : '\U000025b9',
        '\\triangle'             : '\U000025b3',
        '\\triangleq'            : '\U0000225c',
        '\\oplus'                : '\U00002295',
        '\\bigoplus'             : '\U00002a01',
        '\\otimes'               : '\U00002297',
        '\\bigotimes'            : '\U00002a02',
        '\\odot'                 : '\U00002299',
        '\\bigodot'              : '\U00002a00',
        '\\ominus'               : '\U00002296',
        '\\oslash'               : '\U00002298',
        '\\dots'                 : '\U00002026',
        '\\cdots'                : '\U000022ef',
        '\\sum'                  : '\U00002211',
        '\\prod'                 : '\U0000220f',
        '\\coprod'               : '\U00002210',
        '\\infty'                : '\U0000221e',
        '\\int'                  : '\U0000222b',
        '\\oint'                 : '\U0000222e',
        '\\clubsuit'             : '\U00002663',
        '\\diamondsuit'          : '\U00002662',
        '\\heartsuit'            : '\U00002661',
        '\\spadesuit'            : '\U00002660',
        '\\aleph'                : '\U00002135',
        '\\emptyset'             : '\U00002205',
        '\\nabla'                : '\U00002207',
        '\\partial'              : '\U00002202',
        '\\flat'                 : '\U0000266d',
        '\\natural'              : '\U0000266e',
        '\\sharp'                : '\U0000266f',
        '\\angle'                : '\U00002220',
        '\\copyright'            : '\U000000a9',
        '\\textregistered'       : '\U000000ae',
        '\\textonequarter'       : '\U000000bc',
        '\\textonehalf'          : '\U000000bd',
        '\\textthreequarters'    : '\U000000be',
        '\\textordfeminine'      : '\U000000aa',
        '\\textordmasculine'     : '\U000000ba',
        '\\euro'                 : '\U000020ac',
        '\\pounds'               : '\U000000a3',
        '\\yen'                  : '\U000000a5',
        '\\textcent'             : '\U000000a2',
        '\\textcurrency'         : '\U000000a4',
        '\\textdegree'           : '\U000000b0',
    }

    isabelle_symbols = {
        '\\<zero>'                 : '\U0001d7ec',
        '\\<one>'                  : '\U0001d7ed',
        '\\<two>'                  : '\U0001d7ee',
        '\\<three>'                : '\U0001d7ef',
        '\\<four>'                 : '\U0001d7f0',
        '\\<five>'                 : '\U0001d7f1',
        '\\<six>'                  : '\U0001d7f2',
        '\\<seven>'                : '\U0001d7f3',
        '\\<eight>'                : '\U0001d7f4',
        '\\<nine>'                 : '\U0001d7f5',
        '\\<A>'                    : '\U0001d49c',
        '\\<B>'                    : '\U0000212c',
        '\\<C>'                    : '\U0001d49e',
        '\\<D>'                    : '\U0001d49f',
        '\\<E>'                    : '\U00002130',
        '\\<F>'                    : '\U00002131',
        '\\<G>'                    : '\U0001d4a2',
        '\\<H>'                    : '\U0000210b',
        '\\<I>'                    : '\U00002110',
        '\\<J>'                    : '\U0001d4a5',
        '\\<K>'                    : '\U0001d4a6',
        '\\<L>'                    : '\U00002112',
        '\\<M>'                    : '\U00002133',
        '\\<N>'                    : '\U0001d4a9',
        '\\<O>'                    : '\U0001d4aa',
        '\\<P>'                    : '\U0001d4ab',
        '\\<Q>'                    : '\U0001d4ac',
        '\\<R>'                    : '\U0000211b',
        '\\<S>'                    : '\U0001d4ae',
        '\\<T>'                    : '\U0001d4af',
        '\\<U>'                    : '\U0001d4b0',
        '\\<V>'                    : '\U0001d4b1',
        '\\<W>'                    : '\U0001d4b2',
        '\\<X>'                    : '\U0001d4b3',
        '\\<Y>'                    : '\U0001d4b4',
        '\\<Z>'                    : '\U0001d4b5',
        '\\<a>'                    : '\U0001d5ba',
        '\\<b>'                    : '\U0001d5bb',
        '\\<c>'                    : '\U0001d5bc',
        '\\<d>'                    : '\U0001d5bd',
        '\\<e>'                    : '\U0001d5be',
        '\\<f>'                    : '\U0001d5bf',
        '\\<g>'                    : '\U0001d5c0',
        '\\<h>'                    : '\U0001d5c1',
        '\\<i>'                    : '\U0001d5c2',
        '\\<j>'                    : '\U0001d5c3',
        '\\<k>'                    : '\U0001d5c4',
        '\\<l>'                    : '\U0001d5c5',
        '\\<m>'                    : '\U0001d5c6',
        '\\<n>'                    : '\U0001d5c7',
        '\\<o>'                    : '\U0001d5c8',
        '\\<p>'                    : '\U0001d5c9',
        '\\<q>'                    : '\U0001d5ca',
        '\\<r>'                    : '\U0001d5cb',
        '\\<s>'                    : '\U0001d5cc',
        '\\<t>'                    : '\U0001d5cd',
        '\\<u>'                    : '\U0001d5ce',
        '\\<v>'                    : '\U0001d5cf',
        '\\<w>'                    : '\U0001d5d0',
        '\\<x>'                    : '\U0001d5d1',
        '\\<y>'                    : '\U0001d5d2',
        '\\<z>'                    : '\U0001d5d3',
        '\\<AA>'                   : '\U0001d504',
        '\\<BB>'                   : '\U0001d505',
        '\\<CC>'                   : '\U0000212d',
        '\\<DD>'                   : '\U0001d507',
        '\\<EE>'                   : '\U0001d508',
        '\\<FF>'                   : '\U0001d509',
        '\\<GG>'                   : '\U0001d50a',
        '\\<HH>'                   : '\U0000210c',
        '\\<II>'                   : '\U00002111',
        '\\<JJ>'                   : '\U0001d50d',
        '\\<KK>'                   : '\U0001d50e',
        '\\<LL>'                   : '\U0001d50f',
        '\\<MM>'                   : '\U0001d510',
        '\\<NN>'                   : '\U0001d511',
        '\\<OO>'                   : '\U0001d512',
        '\\<PP>'                   : '\U0001d513',
        '\\<QQ>'                   : '\U0001d514',
        '\\<RR>'                   : '\U0000211c',
        '\\<SS>'                   : '\U0001d516',
        '\\<TT>'                   : '\U0001d517',
        '\\<UU>'                   : '\U0001d518',
        '\\<VV>'                   : '\U0001d519',
        '\\<WW>'                   : '\U0001d51a',
        '\\<XX>'                   : '\U0001d51b',
        '\\<YY>'                   : '\U0001d51c',
        '\\<ZZ>'                   : '\U00002128',
        '\\<aa>'                   : '\U0001d51e',
        '\\<bb>'                   : '\U0001d51f',
        '\\<cc>'                   : '\U0001d520',
        '\\<dd>'                   : '\U0001d521',
        '\\<ee>'                   : '\U0001d522',
        '\\<ff>'                   : '\U0001d523',
        '\\<gg>'                   : '\U0001d524',
        '\\<hh>'                   : '\U0001d525',
        '\\<ii>'                   : '\U0001d526',
        '\\<jj>'                   : '\U0001d527',
        '\\<kk>'                   : '\U0001d528',
        '\\<ll>'                   : '\U0001d529',
        '\\<mm>'                   : '\U0001d52a',
        '\\<nn>'                   : '\U0001d52b',
        '\\<oo>'                   : '\U0001d52c',
        '\\<pp>'                   : '\U0001d52d',
        '\\<qq>'                   : '\U0001d52e',
        '\\<rr>'                   : '\U0001d52f',
        '\\<ss>'                   : '\U0001d530',
        '\\<tt>'                   : '\U0001d531',
        '\\<uu>'                   : '\U0001d532',
        '\\<vv>'                   : '\U0001d533',
        '\\<ww>'                   : '\U0001d534',
        '\\<xx>'                   : '\U0001d535',
        '\\<yy>'                   : '\U0001d536',
        '\\<zz>'                   : '\U0001d537',
        '\\<alpha>'                : '\U000003b1',
        '\\<beta>'                 : '\U000003b2',
        '\\<gamma>'                : '\U000003b3',
        '\\<delta>'                : '\U000003b4',
        '\\<epsilon>'              : '\U000003b5',
        '\\<zeta>'                 : '\U000003b6',
        '\\<eta>'                  : '\U000003b7',
        '\\<theta>'                : '\U000003b8',
        '\\<iota>'                 : '\U000003b9',
        '\\<kappa>'                : '\U000003ba',
        '\\<lambda>'               : '\U000003bb',
        '\\<mu>'                   : '\U000003bc',
        '\\<nu>'                   : '\U000003bd',
        '\\<xi>'                   : '\U000003be',
        '\\<pi>'                   : '\U000003c0',
        '\\<rho>'                  : '\U000003c1',
        '\\<sigma>'                : '\U000003c3',
        '\\<tau>'                  : '\U000003c4',
        '\\<upsilon>'              : '\U000003c5',
        '\\<phi>'                  : '\U000003c6',
        '\\<chi>'                  : '\U000003c7',
        '\\<psi>'                  : '\U000003c8',
        '\\<omega>'                : '\U000003c9',
        '\\<Gamma>'                : '\U00000393',
        '\\<Delta>'                : '\U00000394',
        '\\<Theta>'                : '\U00000398',
        '\\<Lambda>'               : '\U0000039b',
        '\\<Xi>'                   : '\U0000039e',
        '\\<Pi>'                   : '\U000003a0',
        '\\<Sigma>'                : '\U000003a3',
        '\\<Upsilon>'              : '\U000003a5',
        '\\<Phi>'                  : '\U000003a6',
        '\\<Psi>'                  : '\U000003a8',
        '\\<Omega>'                : '\U000003a9',
        '\\<bool>'                 : '\U0001d539',
        '\\<complex>'              : '\U00002102',
        '\\<nat>'                  : '\U00002115',
        '\\<rat>'                  : '\U0000211a',
        '\\<real>'                 : '\U0000211d',
        '\\<int>'                  : '\U00002124',
        '\\<leftarrow>'            : '\U00002190',
        '\\<longleftarrow>'        : '\U000027f5',
        '\\<rightarrow>'           : '\U00002192',
        '\\<longrightarrow>'       : '\U000027f6',
        '\\<Leftarrow>'            : '\U000021d0',
        '\\<Longleftarrow>'        : '\U000027f8',
        '\\<Rightarrow>'           : '\U000021d2',
        '\\<Longrightarrow>'       : '\U000027f9',
        '\\<leftrightarrow>'       : '\U00002194',
        '\\<longleftrightarrow>'   : '\U000027f7',
        '\\<Leftrightarrow>'       : '\U000021d4',
        '\\<Longleftrightarrow>'   : '\U000027fa',
        '\\<mapsto>'               : '\U000021a6',
        '\\<longmapsto>'           : '\U000027fc',
        '\\<midarrow>'             : '\U00002500',
        '\\<Midarrow>'             : '\U00002550',
        '\\<hookleftarrow>'        : '\U000021a9',
        '\\<hookrightarrow>'       : '\U000021aa',
        '\\<leftharpoondown>'      : '\U000021bd',
        '\\<rightharpoondown>'     : '\U000021c1',
        '\\<leftharpoonup>'        : '\U000021bc',
        '\\<rightharpoonup>'       : '\U000021c0',
        '\\<rightleftharpoons>'    : '\U000021cc',
        '\\<leadsto>'              : '\U0000219d',
        '\\<downharpoonleft>'      : '\U000021c3',
        '\\<downharpoonright>'     : '\U000021c2',
        '\\<upharpoonleft>'        : '\U000021bf',
        '\\<upharpoonright>'       : '\U000021be',
        '\\<restriction>'          : '\U000021be',
        '\\<Colon>'                : '\U00002237',
        '\\<up>'                   : '\U00002191',
        '\\<Up>'                   : '\U000021d1',
        '\\<down>'                 : '\U00002193',
        '\\<Down>'                 : '\U000021d3',
        '\\<updown>'               : '\U00002195',
        '\\<Updown>'               : '\U000021d5',
        '\\<langle>'               : '\U000027e8',
        '\\<rangle>'               : '\U000027e9',
        '\\<lceil>'                : '\U00002308',
        '\\<rceil>'                : '\U00002309',
        '\\<lfloor>'               : '\U0000230a',
        '\\<rfloor>'               : '\U0000230b',
        '\\<lparr>'                : '\U00002987',
        '\\<rparr>'                : '\U00002988',
        '\\<lbrakk>'               : '\U000027e6',
        '\\<rbrakk>'               : '\U000027e7',
        '\\<lbrace>'               : '\U00002983',
        '\\<rbrace>'               : '\U00002984',
        '\\<guillemotleft>'        : '\U000000ab',
        '\\<guillemotright>'       : '\U000000bb',
        '\\<bottom>'               : '\U000022a5',
        '\\<top>'                  : '\U000022a4',
        '\\<and>'                  : '\U00002227',
        '\\<And>'                  : '\U000022c0',
        '\\<or>'                   : '\U00002228',
        '\\<Or>'                   : '\U000022c1',
        '\\<forall>'               : '\U00002200',
        '\\<exists>'               : '\U00002203',
        '\\<nexists>'              : '\U00002204',
        '\\<not>'                  : '\U000000ac',
        '\\<box>'                  : '\U000025a1',
        '\\<diamond>'              : '\U000025c7',
        '\\<turnstile>'            : '\U000022a2',
        '\\<Turnstile>'            : '\U000022a8',
        '\\<tturnstile>'           : '\U000022a9',
        '\\<TTurnstile>'           : '\U000022ab',
        '\\<stileturn>'            : '\U000022a3',
        '\\<surd>'                 : '\U0000221a',
        '\\<le>'                   : '\U00002264',
        '\\<ge>'                   : '\U00002265',
        '\\<lless>'                : '\U0000226a',
        '\\<ggreater>'             : '\U0000226b',
        '\\<lesssim>'              : '\U00002272',
        '\\<greatersim>'           : '\U00002273',
        '\\<lessapprox>'           : '\U00002a85',
        '\\<greaterapprox>'        : '\U00002a86',
        '\\<in>'                   : '\U00002208',
        '\\<notin>'                : '\U00002209',
        '\\<subset>'               : '\U00002282',
        '\\<supset>'               : '\U00002283',
        '\\<subseteq>'             : '\U00002286',
        '\\<supseteq>'             : '\U00002287',
        '\\<sqsubset>'             : '\U0000228f',
        '\\<sqsupset>'             : '\U00002290',
        '\\<sqsubseteq>'           : '\U00002291',
        '\\<sqsupseteq>'           : '\U00002292',
        '\\<inter>'                : '\U00002229',
        '\\<Inter>'                : '\U000022c2',
        '\\<union>'                : '\U0000222a',
        '\\<Union>'                : '\U000022c3',
        '\\<squnion>'              : '\U00002294',
        '\\<Squnion>'              : '\U00002a06',
        '\\<sqinter>'              : '\U00002293',
        '\\<Sqinter>'              : '\U00002a05',
        '\\<setminus>'             : '\U00002216',
        '\\<propto>'               : '\U0000221d',
        '\\<uplus>'                : '\U0000228e',
        '\\<Uplus>'                : '\U00002a04',
        '\\<noteq>'                : '\U00002260',
        '\\<sim>'                  : '\U0000223c',
        '\\<doteq>'                : '\U00002250',
        '\\<simeq>'                : '\U00002243',
        '\\<approx>'               : '\U00002248',
        '\\<asymp>'                : '\U0000224d',
        '\\<cong>'                 : '\U00002245',
        '\\<smile>'                : '\U00002323',
        '\\<equiv>'                : '\U00002261',
        '\\<frown>'                : '\U00002322',
        '\\<Join>'                 : '\U000022c8',
        '\\<bowtie>'               : '\U00002a1d',
        '\\<prec>'                 : '\U0000227a',
        '\\<succ>'                 : '\U0000227b',
        '\\<preceq>'               : '\U0000227c',
        '\\<succeq>'               : '\U0000227d',
        '\\<parallel>'             : '\U00002225',
        '\\<bar>'                  : '\U000000a6',
        '\\<plusminus>'            : '\U000000b1',
        '\\<minusplus>'            : '\U00002213',
        '\\<times>'                : '\U000000d7',
        '\\<div>'                  : '\U000000f7',
        '\\<cdot>'                 : '\U000022c5',
        '\\<star>'                 : '\U000022c6',
        '\\<bullet>'               : '\U00002219',
        '\\<circ>'                 : '\U00002218',
        '\\<dagger>'               : '\U00002020',
        '\\<ddagger>'              : '\U00002021',
        '\\<lhd>'                  : '\U000022b2',
        '\\<rhd>'                  : '\U000022b3',
        '\\<unlhd>'                : '\U000022b4',
        '\\<unrhd>'                : '\U000022b5',
        '\\<triangleleft>'         : '\U000025c3',
        '\\<triangleright>'        : '\U000025b9',
        '\\<triangle>'             : '\U000025b3',
        '\\<triangleq>'            : '\U0000225c',
        '\\<oplus>'                : '\U00002295',
        '\\<Oplus>'                : '\U00002a01',
        '\\<otimes>'               : '\U00002297',
        '\\<Otimes>'               : '\U00002a02',
        '\\<odot>'                 : '\U00002299',
        '\\<Odot>'                 : '\U00002a00',
        '\\<ominus>'               : '\U00002296',
        '\\<oslash>'               : '\U00002298',
        '\\<dots>'                 : '\U00002026',
        '\\<cdots>'                : '\U000022ef',
        '\\<Sum>'                  : '\U00002211',
        '\\<Prod>'                 : '\U0000220f',
        '\\<Coprod>'               : '\U00002210',
        '\\<infinity>'             : '\U0000221e',
        '\\<integral>'             : '\U0000222b',
        '\\<ointegral>'            : '\U0000222e',
        '\\<clubsuit>'             : '\U00002663',
        '\\<diamondsuit>'          : '\U00002662',
        '\\<heartsuit>'            : '\U00002661',
        '\\<spadesuit>'            : '\U00002660',
        '\\<aleph>'                : '\U00002135',
        '\\<emptyset>'             : '\U00002205',
        '\\<nabla>'                : '\U00002207',
        '\\<partial>'              : '\U00002202',
        '\\<flat>'                 : '\U0000266d',
        '\\<natural>'              : '\U0000266e',
        '\\<sharp>'                : '\U0000266f',
        '\\<angle>'                : '\U00002220',
        '\\<copyright>'            : '\U000000a9',
        '\\<registered>'           : '\U000000ae',
        '\\<hyphen>'               : '\U000000ad',
        '\\<inverse>'              : '\U000000af',
        '\\<onequarter>'           : '\U000000bc',
        '\\<onehalf>'              : '\U000000bd',
        '\\<threequarters>'        : '\U000000be',
        '\\<ordfeminine>'          : '\U000000aa',
        '\\<ordmasculine>'         : '\U000000ba',
        '\\<section>'              : '\U000000a7',
        '\\<paragraph>'            : '\U000000b6',
        '\\<exclamdown>'           : '\U000000a1',
        '\\<questiondown>'         : '\U000000bf',
        '\\<euro>'                 : '\U000020ac',
        '\\<pounds>'               : '\U000000a3',
        '\\<yen>'                  : '\U000000a5',
        '\\<cent>'                 : '\U000000a2',
        '\\<currency>'             : '\U000000a4',
        '\\<degree>'               : '\U000000b0',
        '\\<amalg>'                : '\U00002a3f',
        '\\<mho>'                  : '\U00002127',
        '\\<lozenge>'              : '\U000025ca',
        '\\<wp>'                   : '\U00002118',
        '\\<wrong>'                : '\U00002240',
        '\\<struct>'               : '\U000022c4',
        '\\<acute>'                : '\U000000b4',
        '\\<index>'                : '\U00000131',
        '\\<dieresis>'             : '\U000000a8',
        '\\<cedilla>'              : '\U000000b8',
        '\\<hungarumlaut>'         : '\U000002dd',
        '\\<some>'                 : '\U000003f5',
        '\\<newline>'              : '\U000023ce',
        '\\<open>'                 : '\U00002039',
        '\\<close>'                : '\U0000203a',
        '\\<here>'                 : '\U00002302',
        '\\<^sub>'                 : '\U000021e9',
        '\\<^sup>'                 : '\U000021e7',
        '\\<^bold>'                : '\U00002759',
        '\\<^bsub>'                : '\U000021d8',
        '\\<^esub>'                : '\U000021d9',
        '\\<^bsup>'                : '\U000021d7',
        '\\<^esup>'                : '\U000021d6',
    }

    lang_map = {'isabelle' : isabelle_symbols, 'latex' : latex_symbols}

    def __init__(self, **options):
        Filter.__init__(self, **options)
        lang = get_choice_opt(options, 'lang',
                              ['isabelle', 'latex'], 'isabelle')
        self.symbols = self.lang_map[lang]

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if value in self.symbols:
                yield ttype, self.symbols[value]
            else:
                yield ttype, value


class KeywordCaseFilter(Filter):
    """Convert keywords to lowercase or uppercase or capitalize them, which
    means first letter uppercase, rest lowercase.

    This can be useful e.g. if you highlight Pascal code and want to adapt the
    code to your styleguide.

    Options accepted:

    `case` : string
       The casing to convert keywords to. Must be one of ``'lower'``,
       ``'upper'`` or ``'capitalize'``.  The default is ``'lower'``.
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        case = get_choice_opt(options, 'case',
                              ['lower', 'upper', 'capitalize'], 'lower')
        self.convert = getattr(str, case)

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if ttype in Keyword:
                yield ttype, self.convert(value)
            else:
                yield ttype, value


class NameHighlightFilter(Filter):
    """Highlight a normal Name (and Name.*) token with a different token type.

    Example::

        filter = NameHighlightFilter(
            names=['foo', 'bar', 'baz'],
            tokentype=Name.Function,
        )

    This would highlight the names "foo", "bar" and "baz"
    as functions. `Name.Function` is the default token type.

    Options accepted:

    `names` : list of strings
      A list of names that should be given the different token type.
      There is no default.
    `tokentype` : TokenType or string
      A token type or a string containing a token type name that is
      used for highlighting the strings in `names`.  The default is
      `Name.Function`.
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        self.names = set(get_list_opt(options, 'names', []))
        tokentype = options.get('tokentype')
        if tokentype:
            self.tokentype = string_to_tokentype(tokentype)
        else:
            self.tokentype = Name.Function

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if ttype in Name and value in self.names:
                yield self.tokentype, value
            else:
                yield ttype, value


class ErrorToken(Exception):
    pass


class RaiseOnErrorTokenFilter(Filter):
    """Raise an exception when the lexer generates an error token.

    Options accepted:

    `excclass` : Exception class
      The exception class to raise.
      The default is `pygments.filters.ErrorToken`.

    .. versionadded:: 0.8
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        self.exception = options.get('excclass', ErrorToken)
        try:
            # issubclass() will raise TypeError if first argument is not a class
            if not issubclass(self.exception, Exception):
                raise TypeError
        except TypeError:
            raise OptionError('excclass option is not an exception class')

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if ttype is Error:
                raise self.exception(value)
            yield ttype, value


class VisibleWhitespaceFilter(Filter):
    """Convert tabs, newlines and/or spaces to visible characters.

    Options accepted:

    `spaces` : string or bool
      If this is a one-character string, spaces will be replaces by this string.
      If it is another true value, spaces will be replaced by ``·`` (unicode
      MIDDLE DOT).  If it is a false value, spaces will not be replaced.  The
      default is ``False``.
    `tabs` : string or bool
      The same as for `spaces`, but the default replacement character is ``»``
      (unicode RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK).  The default value
      is ``False``.  Note: this will not work if the `tabsize` option for the
      lexer is nonzero, as tabs will already have been expanded then.
    `tabsize` : int
      If tabs are to be replaced by this filter (see the `tabs` option), this
      is the total number of characters that a tab should be expanded to.
      The default is ``8``.
    `newlines` : string or bool
      The same as for `spaces`, but the default replacement character is ``¶``
      (unicode PILCROW SIGN).  The default value is ``False``.
    `wstokentype` : bool
      If true, give whitespace the special `Whitespace` token type.  This allows
      styling the visible whitespace differently (e.g. greyed out), but it can
      disrupt background colors.  The default is ``True``.

    .. versionadded:: 0.8
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        for name, default in [('spaces',   '·'),
                              ('tabs',     '»'),
                              ('newlines', '¶')]:
            opt = options.get(name, False)
            if isinstance(opt, str) and len(opt) == 1:
                setattr(self, name, opt)
            else:
                setattr(self, name, (opt and default or ''))
        tabsize = get_int_opt(options, 'tabsize', 8)
        if self.tabs:
            self.tabs += ' ' * (tabsize - 1)
        if self.newlines:
            self.newlines += '\n'
        self.wstt = get_bool_opt(options, 'wstokentype', True)

    def filter(self, lexer, stream):
        if self.wstt:
            spaces = self.spaces or ' '
            tabs = self.tabs or '\t'
            newlines = self.newlines or '\n'
            regex = re.compile(r'\s')

            def replacefunc(wschar):
                if wschar == ' ':
                    return spaces
                elif wschar == '\t':
                    return tabs
                elif wschar == '\n':
                    return newlines
                return wschar

            for ttype, value in stream:
                yield from _replace_special(ttype, value, regex, Whitespace,
                                            replacefunc)
        else:
            spaces, tabs, newlines = self.spaces, self.tabs, self.newlines
            # simpler processing
            for ttype, value in stream:
                if spaces:
                    value = value.replace(' ', spaces)
                if tabs:
                    value = value.replace('\t', tabs)
                if newlines:
                    value = value.replace('\n', newlines)
                yield ttype, value


class GobbleFilter(Filter):
    """Gobbles source code lines (eats initial characters).

    This filter drops the first ``n`` characters off every line of code.  This
    may be useful when the source code fed to the lexer is indented by a fixed
    amount of space that isn't desired in the output.

    Options accepted:

    `n` : int
       The number of characters to gobble.

    .. versionadded:: 1.2
    """
    def __init__(self, **options):
        Filter.__init__(self, **options)
        self.n = get_int_opt(options, 'n', 0)

    def gobble(self, value, left):
        if left < len(value):
            return value[left:], 0
        else:
            return '', left - len(value)

    def filter(self, lexer, stream):
        n = self.n
        left = n  # How many characters left to gobble.
        for ttype, value in stream:
            # Remove ``left`` tokens from first line, ``n`` from all others.
            parts = value.split('\n')
            (parts[0], left) = self.gobble(parts[0], left)
            for i in range(1, len(parts)):
                (parts[i], left) = self.gobble(parts[i], n)
            value = '\n'.join(parts)

            if value != '':
                yield ttype, value


class TokenMergeFilter(Filter):
    """Merges consecutive tokens with the same token type in the output
    stream of a lexer.

    .. versionadded:: 1.2
    """
    def __init__(self, **options):
        Filter.__init__(self, **options)

    def filter(self, lexer, stream):
        current_type = None
        current_value = None
        for ttype, value in stream:
            if ttype is current_type:
                current_value += value
            else:
                if current_type is not None:
                    yield current_type, current_value
                current_type = ttype
                current_value = value
        if current_type is not None:
            yield current_type, current_value


FILTERS = {
    'codetagify':     CodeTagFilter,
    'keywordcase':    KeywordCaseFilter,
    'highlight':      NameHighlightFilter,
    'raiseonerror':   RaiseOnErrorTokenFilter,
    'whitespace':     VisibleWhitespaceFilter,
    'gobble':         GobbleFilter,
    'tokenmerge':     TokenMergeFilter,
    'symbols':        SymbolFilter,
}

# === NexusCore/openenv\Lib\site-packages\pygments\filters\__init__.py ===
"""
    pygments.filters
    ~~~~~~~~~~~~~~~~

    Module containing filter lookup functions and default
    filters.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.token import String, Comment, Keyword, Name, Error, Whitespace, \
    string_to_tokentype
from pygments.filter import Filter
from pygments.util import get_list_opt, get_int_opt, get_bool_opt, \
    get_choice_opt, ClassNotFound, OptionError
from pygments.plugin import find_plugin_filters


def find_filter_class(filtername):
    """Lookup a filter by name. Return None if not found."""
    if filtername in FILTERS:
        return FILTERS[filtername]
    for name, cls in find_plugin_filters():
        if name == filtername:
            return cls
    return None


def get_filter_by_name(filtername, **options):
    """Return an instantiated filter.

    Options are passed to the filter initializer if wanted.
    Raise a ClassNotFound if not found.
    """
    cls = find_filter_class(filtername)
    if cls:
        return cls(**options)
    else:
        raise ClassNotFound(f'filter {filtername!r} not found')


def get_all_filters():
    """Return a generator of all filter names."""
    yield from FILTERS
    for name, _ in find_plugin_filters():
        yield name


def _replace_special(ttype, value, regex, specialttype,
                     replacefunc=lambda x: x):
    last = 0
    for match in regex.finditer(value):
        start, end = match.start(), match.end()
        if start != last:
            yield ttype, value[last:start]
        yield specialttype, replacefunc(value[start:end])
        last = end
    if last != len(value):
        yield ttype, value[last:]


class CodeTagFilter(Filter):
    """Highlight special code tags in comments and docstrings.

    Options accepted:

    `codetags` : list of strings
       A list of strings that are flagged as code tags.  The default is to
       highlight ``XXX``, ``TODO``, ``FIXME``, ``BUG`` and ``NOTE``.

    .. versionchanged:: 2.13
       Now recognizes ``FIXME`` by default.
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        tags = get_list_opt(options, 'codetags',
                            ['XXX', 'TODO', 'FIXME', 'BUG', 'NOTE'])
        self.tag_re = re.compile(r'\b({})\b'.format('|'.join([
            re.escape(tag) for tag in tags if tag
        ])))

    def filter(self, lexer, stream):
        regex = self.tag_re
        for ttype, value in stream:
            if ttype in String.Doc or \
               ttype in Comment and \
               ttype not in Comment.Preproc:
                yield from _replace_special(ttype, value, regex, Comment.Special)
            else:
                yield ttype, value


class SymbolFilter(Filter):
    """Convert mathematical symbols such as \\<longrightarrow> in Isabelle
    or \\longrightarrow in LaTeX into Unicode characters.

    This is mostly useful for HTML or console output when you want to
    approximate the source rendering you'd see in an IDE.

    Options accepted:

    `lang` : string
       The symbol language. Must be one of ``'isabelle'`` or
       ``'latex'``.  The default is ``'isabelle'``.
    """

    latex_symbols = {
        '\\alpha'                : '\U000003b1',
        '\\beta'                 : '\U000003b2',
        '\\gamma'                : '\U000003b3',
        '\\delta'                : '\U000003b4',
        '\\varepsilon'           : '\U000003b5',
        '\\zeta'                 : '\U000003b6',
        '\\eta'                  : '\U000003b7',
        '\\vartheta'             : '\U000003b8',
        '\\iota'                 : '\U000003b9',
        '\\kappa'                : '\U000003ba',
        '\\lambda'               : '\U000003bb',
        '\\mu'                   : '\U000003bc',
        '\\nu'                   : '\U000003bd',
        '\\xi'                   : '\U000003be',
        '\\pi'                   : '\U000003c0',
        '\\varrho'               : '\U000003c1',
        '\\sigma'                : '\U000003c3',
        '\\tau'                  : '\U000003c4',
        '\\upsilon'              : '\U000003c5',
        '\\varphi'               : '\U000003c6',
        '\\chi'                  : '\U000003c7',
        '\\psi'                  : '\U000003c8',
        '\\omega'                : '\U000003c9',
        '\\Gamma'                : '\U00000393',
        '\\Delta'                : '\U00000394',
        '\\Theta'                : '\U00000398',
        '\\Lambda'               : '\U0000039b',
        '\\Xi'                   : '\U0000039e',
        '\\Pi'                   : '\U000003a0',
        '\\Sigma'                : '\U000003a3',
        '\\Upsilon'              : '\U000003a5',
        '\\Phi'                  : '\U000003a6',
        '\\Psi'                  : '\U000003a8',
        '\\Omega'                : '\U000003a9',
        '\\leftarrow'            : '\U00002190',
        '\\longleftarrow'        : '\U000027f5',
        '\\rightarrow'           : '\U00002192',
        '\\longrightarrow'       : '\U000027f6',
        '\\Leftarrow'            : '\U000021d0',
        '\\Longleftarrow'        : '\U000027f8',
        '\\Rightarrow'           : '\U000021d2',
        '\\Longrightarrow'       : '\U000027f9',
        '\\leftrightarrow'       : '\U00002194',
        '\\longleftrightarrow'   : '\U000027f7',
        '\\Leftrightarrow'       : '\U000021d4',
        '\\Longleftrightarrow'   : '\U000027fa',
        '\\mapsto'               : '\U000021a6',
        '\\longmapsto'           : '\U000027fc',
        '\\relbar'               : '\U00002500',
        '\\Relbar'               : '\U00002550',
        '\\hookleftarrow'        : '\U000021a9',
        '\\hookrightarrow'       : '\U000021aa',
        '\\leftharpoondown'      : '\U000021bd',
        '\\rightharpoondown'     : '\U000021c1',
        '\\leftharpoonup'        : '\U000021bc',
        '\\rightharpoonup'       : '\U000021c0',
        '\\rightleftharpoons'    : '\U000021cc',
        '\\leadsto'              : '\U0000219d',
        '\\downharpoonleft'      : '\U000021c3',
        '\\downharpoonright'     : '\U000021c2',
        '\\upharpoonleft'        : '\U000021bf',
        '\\upharpoonright'       : '\U000021be',
        '\\restriction'          : '\U000021be',
        '\\uparrow'              : '\U00002191',
        '\\Uparrow'              : '\U000021d1',
        '\\downarrow'            : '\U00002193',
        '\\Downarrow'            : '\U000021d3',
        '\\updownarrow'          : '\U00002195',
        '\\Updownarrow'          : '\U000021d5',
        '\\langle'               : '\U000027e8',
        '\\rangle'               : '\U000027e9',
        '\\lceil'                : '\U00002308',
        '\\rceil'                : '\U00002309',
        '\\lfloor'               : '\U0000230a',
        '\\rfloor'               : '\U0000230b',
        '\\flqq'                 : '\U000000ab',
        '\\frqq'                 : '\U000000bb',
        '\\bot'                  : '\U000022a5',
        '\\top'                  : '\U000022a4',
        '\\wedge'                : '\U00002227',
        '\\bigwedge'             : '\U000022c0',
        '\\vee'                  : '\U00002228',
        '\\bigvee'               : '\U000022c1',
        '\\forall'               : '\U00002200',
        '\\exists'               : '\U00002203',
        '\\nexists'              : '\U00002204',
        '\\neg'                  : '\U000000ac',
        '\\Box'                  : '\U000025a1',
        '\\Diamond'              : '\U000025c7',
        '\\vdash'                : '\U000022a2',
        '\\models'               : '\U000022a8',
        '\\dashv'                : '\U000022a3',
        '\\surd'                 : '\U0000221a',
        '\\le'                   : '\U00002264',
        '\\ge'                   : '\U00002265',
        '\\ll'                   : '\U0000226a',
        '\\gg'                   : '\U0000226b',
        '\\lesssim'              : '\U00002272',
        '\\gtrsim'               : '\U00002273',
        '\\lessapprox'           : '\U00002a85',
        '\\gtrapprox'            : '\U00002a86',
        '\\in'                   : '\U00002208',
        '\\notin'                : '\U00002209',
        '\\subset'               : '\U00002282',
        '\\supset'               : '\U00002283',
        '\\subseteq'             : '\U00002286',
        '\\supseteq'             : '\U00002287',
        '\\sqsubset'             : '\U0000228f',
        '\\sqsupset'             : '\U00002290',
        '\\sqsubseteq'           : '\U00002291',
        '\\sqsupseteq'           : '\U00002292',
        '\\cap'                  : '\U00002229',
        '\\bigcap'               : '\U000022c2',
        '\\cup'                  : '\U0000222a',
        '\\bigcup'               : '\U000022c3',
        '\\sqcup'                : '\U00002294',
        '\\bigsqcup'             : '\U00002a06',
        '\\sqcap'                : '\U00002293',
        '\\Bigsqcap'             : '\U00002a05',
        '\\setminus'             : '\U00002216',
        '\\propto'               : '\U0000221d',
        '\\uplus'                : '\U0000228e',
        '\\bigplus'              : '\U00002a04',
        '\\sim'                  : '\U0000223c',
        '\\doteq'                : '\U00002250',
        '\\simeq'                : '\U00002243',
        '\\approx'               : '\U00002248',
        '\\asymp'                : '\U0000224d',
        '\\cong'                 : '\U00002245',
        '\\equiv'                : '\U00002261',
        '\\Join'                 : '\U000022c8',
        '\\bowtie'               : '\U00002a1d',
        '\\prec'                 : '\U0000227a',
        '\\succ'                 : '\U0000227b',
        '\\preceq'               : '\U0000227c',
        '\\succeq'               : '\U0000227d',
        '\\parallel'             : '\U00002225',
        '\\mid'                  : '\U000000a6',
        '\\pm'                   : '\U000000b1',
        '\\mp'                   : '\U00002213',
        '\\times'                : '\U000000d7',
        '\\div'                  : '\U000000f7',
        '\\cdot'                 : '\U000022c5',
        '\\star'                 : '\U000022c6',
        '\\circ'                 : '\U00002218',
        '\\dagger'               : '\U00002020',
        '\\ddagger'              : '\U00002021',
        '\\lhd'                  : '\U000022b2',
        '\\rhd'                  : '\U000022b3',
        '\\unlhd'                : '\U000022b4',
        '\\unrhd'                : '\U000022b5',
        '\\triangleleft'         : '\U000025c3',
        '\\triangleright'        : '\U000025b9',
        '\\triangle'             : '\U000025b3',
        '\\triangleq'            : '\U0000225c',
        '\\oplus'                : '\U00002295',
        '\\bigoplus'             : '\U00002a01',
        '\\otimes'               : '\U00002297',
        '\\bigotimes'            : '\U00002a02',
        '\\odot'                 : '\U00002299',
        '\\bigodot'              : '\U00002a00',
        '\\ominus'               : '\U00002296',
        '\\oslash'               : '\U00002298',
        '\\dots'                 : '\U00002026',
        '\\cdots'                : '\U000022ef',
        '\\sum'                  : '\U00002211',
        '\\prod'                 : '\U0000220f',
        '\\coprod'               : '\U00002210',
        '\\infty'                : '\U0000221e',
        '\\int'                  : '\U0000222b',
        '\\oint'                 : '\U0000222e',
        '\\clubsuit'             : '\U00002663',
        '\\diamondsuit'          : '\U00002662',
        '\\heartsuit'            : '\U00002661',
        '\\spadesuit'            : '\U00002660',
        '\\aleph'                : '\U00002135',
        '\\emptyset'             : '\U00002205',
        '\\nabla'                : '\U00002207',
        '\\partial'              : '\U00002202',
        '\\flat'                 : '\U0000266d',
        '\\natural'              : '\U0000266e',
        '\\sharp'                : '\U0000266f',
        '\\angle'                : '\U00002220',
        '\\copyright'            : '\U000000a9',
        '\\textregistered'       : '\U000000ae',
        '\\textonequarter'       : '\U000000bc',
        '\\textonehalf'          : '\U000000bd',
        '\\textthreequarters'    : '\U000000be',
        '\\textordfeminine'      : '\U000000aa',
        '\\textordmasculine'     : '\U000000ba',
        '\\euro'                 : '\U000020ac',
        '\\pounds'               : '\U000000a3',
        '\\yen'                  : '\U000000a5',
        '\\textcent'             : '\U000000a2',
        '\\textcurrency'         : '\U000000a4',
        '\\textdegree'           : '\U000000b0',
    }

    isabelle_symbols = {
        '\\<zero>'                 : '\U0001d7ec',
        '\\<one>'                  : '\U0001d7ed',
        '\\<two>'                  : '\U0001d7ee',
        '\\<three>'                : '\U0001d7ef',
        '\\<four>'                 : '\U0001d7f0',
        '\\<five>'                 : '\U0001d7f1',
        '\\<six>'                  : '\U0001d7f2',
        '\\<seven>'                : '\U0001d7f3',
        '\\<eight>'                : '\U0001d7f4',
        '\\<nine>'                 : '\U0001d7f5',
        '\\<A>'                    : '\U0001d49c',
        '\\<B>'                    : '\U0000212c',
        '\\<C>'                    : '\U0001d49e',
        '\\<D>'                    : '\U0001d49f',
        '\\<E>'                    : '\U00002130',
        '\\<F>'                    : '\U00002131',
        '\\<G>'                    : '\U0001d4a2',
        '\\<H>'                    : '\U0000210b',
        '\\<I>'                    : '\U00002110',
        '\\<J>'                    : '\U0001d4a5',
        '\\<K>'                    : '\U0001d4a6',
        '\\<L>'                    : '\U00002112',
        '\\<M>'                    : '\U00002133',
        '\\<N>'                    : '\U0001d4a9',
        '\\<O>'                    : '\U0001d4aa',
        '\\<P>'                    : '\U0001d4ab',
        '\\<Q>'                    : '\U0001d4ac',
        '\\<R>'                    : '\U0000211b',
        '\\<S>'                    : '\U0001d4ae',
        '\\<T>'                    : '\U0001d4af',
        '\\<U>'                    : '\U0001d4b0',
        '\\<V>'                    : '\U0001d4b1',
        '\\<W>'                    : '\U0001d4b2',
        '\\<X>'                    : '\U0001d4b3',
        '\\<Y>'                    : '\U0001d4b4',
        '\\<Z>'                    : '\U0001d4b5',
        '\\<a>'                    : '\U0001d5ba',
        '\\<b>'                    : '\U0001d5bb',
        '\\<c>'                    : '\U0001d5bc',
        '\\<d>'                    : '\U0001d5bd',
        '\\<e>'                    : '\U0001d5be',
        '\\<f>'                    : '\U0001d5bf',
        '\\<g>'                    : '\U0001d5c0',
        '\\<h>'                    : '\U0001d5c1',
        '\\<i>'                    : '\U0001d5c2',
        '\\<j>'                    : '\U0001d5c3',
        '\\<k>'                    : '\U0001d5c4',
        '\\<l>'                    : '\U0001d5c5',
        '\\<m>'                    : '\U0001d5c6',
        '\\<n>'                    : '\U0001d5c7',
        '\\<o>'                    : '\U0001d5c8',
        '\\<p>'                    : '\U0001d5c9',
        '\\<q>'                    : '\U0001d5ca',
        '\\<r>'                    : '\U0001d5cb',
        '\\<s>'                    : '\U0001d5cc',
        '\\<t>'                    : '\U0001d5cd',
        '\\<u>'                    : '\U0001d5ce',
        '\\<v>'                    : '\U0001d5cf',
        '\\<w>'                    : '\U0001d5d0',
        '\\<x>'                    : '\U0001d5d1',
        '\\<y>'                    : '\U0001d5d2',
        '\\<z>'                    : '\U0001d5d3',
        '\\<AA>'                   : '\U0001d504',
        '\\<BB>'                   : '\U0001d505',
        '\\<CC>'                   : '\U0000212d',
        '\\<DD>'                   : '\U0001d507',
        '\\<EE>'                   : '\U0001d508',
        '\\<FF>'                   : '\U0001d509',
        '\\<GG>'                   : '\U0001d50a',
        '\\<HH>'                   : '\U0000210c',
        '\\<II>'                   : '\U00002111',
        '\\<JJ>'                   : '\U0001d50d',
        '\\<KK>'                   : '\U0001d50e',
        '\\<LL>'                   : '\U0001d50f',
        '\\<MM>'                   : '\U0001d510',
        '\\<NN>'                   : '\U0001d511',
        '\\<OO>'                   : '\U0001d512',
        '\\<PP>'                   : '\U0001d513',
        '\\<QQ>'                   : '\U0001d514',
        '\\<RR>'                   : '\U0000211c',
        '\\<SS>'                   : '\U0001d516',
        '\\<TT>'                   : '\U0001d517',
        '\\<UU>'                   : '\U0001d518',
        '\\<VV>'                   : '\U0001d519',
        '\\<WW>'                   : '\U0001d51a',
        '\\<XX>'                   : '\U0001d51b',
        '\\<YY>'                   : '\U0001d51c',
        '\\<ZZ>'                   : '\U00002128',
        '\\<aa>'                   : '\U0001d51e',
        '\\<bb>'                   : '\U0001d51f',
        '\\<cc>'                   : '\U0001d520',
        '\\<dd>'                   : '\U0001d521',
        '\\<ee>'                   : '\U0001d522',
        '\\<ff>'                   : '\U0001d523',
        '\\<gg>'                   : '\U0001d524',
        '\\<hh>'                   : '\U0001d525',
        '\\<ii>'                   : '\U0001d526',
        '\\<jj>'                   : '\U0001d527',
        '\\<kk>'                   : '\U0001d528',
        '\\<ll>'                   : '\U0001d529',
        '\\<mm>'                   : '\U0001d52a',
        '\\<nn>'                   : '\U0001d52b',
        '\\<oo>'                   : '\U0001d52c',
        '\\<pp>'                   : '\U0001d52d',
        '\\<qq>'                   : '\U0001d52e',
        '\\<rr>'                   : '\U0001d52f',
        '\\<ss>'                   : '\U0001d530',
        '\\<tt>'                   : '\U0001d531',
        '\\<uu>'                   : '\U0001d532',
        '\\<vv>'                   : '\U0001d533',
        '\\<ww>'                   : '\U0001d534',
        '\\<xx>'                   : '\U0001d535',
        '\\<yy>'                   : '\U0001d536',
        '\\<zz>'                   : '\U0001d537',
        '\\<alpha>'                : '\U000003b1',
        '\\<beta>'                 : '\U000003b2',
        '\\<gamma>'                : '\U000003b3',
        '\\<delta>'                : '\U000003b4',
        '\\<epsilon>'              : '\U000003b5',
        '\\<zeta>'                 : '\U000003b6',
        '\\<eta>'                  : '\U000003b7',
        '\\<theta>'                : '\U000003b8',
        '\\<iota>'                 : '\U000003b9',
        '\\<kappa>'                : '\U000003ba',
        '\\<lambda>'               : '\U000003bb',
        '\\<mu>'                   : '\U000003bc',
        '\\<nu>'                   : '\U000003bd',
        '\\<xi>'                   : '\U000003be',
        '\\<pi>'                   : '\U000003c0',
        '\\<rho>'                  : '\U000003c1',
        '\\<sigma>'                : '\U000003c3',
        '\\<tau>'                  : '\U000003c4',
        '\\<upsilon>'              : '\U000003c5',
        '\\<phi>'                  : '\U000003c6',
        '\\<chi>'                  : '\U000003c7',
        '\\<psi>'                  : '\U000003c8',
        '\\<omega>'                : '\U000003c9',
        '\\<Gamma>'                : '\U00000393',
        '\\<Delta>'                : '\U00000394',
        '\\<Theta>'                : '\U00000398',
        '\\<Lambda>'               : '\U0000039b',
        '\\<Xi>'                   : '\U0000039e',
        '\\<Pi>'                   : '\U000003a0',
        '\\<Sigma>'                : '\U000003a3',
        '\\<Upsilon>'              : '\U000003a5',
        '\\<Phi>'                  : '\U000003a6',
        '\\<Psi>'                  : '\U000003a8',
        '\\<Omega>'                : '\U000003a9',
        '\\<bool>'                 : '\U0001d539',
        '\\<complex>'              : '\U00002102',
        '\\<nat>'                  : '\U00002115',
        '\\<rat>'                  : '\U0000211a',
        '\\<real>'                 : '\U0000211d',
        '\\<int>'                  : '\U00002124',
        '\\<leftarrow>'            : '\U00002190',
        '\\<longleftarrow>'        : '\U000027f5',
        '\\<rightarrow>'           : '\U00002192',
        '\\<longrightarrow>'       : '\U000027f6',
        '\\<Leftarrow>'            : '\U000021d0',
        '\\<Longleftarrow>'        : '\U000027f8',
        '\\<Rightarrow>'           : '\U000021d2',
        '\\<Longrightarrow>'       : '\U000027f9',
        '\\<leftrightarrow>'       : '\U00002194',
        '\\<longleftrightarrow>'   : '\U000027f7',
        '\\<Leftrightarrow>'       : '\U000021d4',
        '\\<Longleftrightarrow>'   : '\U000027fa',
        '\\<mapsto>'               : '\U000021a6',
        '\\<longmapsto>'           : '\U000027fc',
        '\\<midarrow>'             : '\U00002500',
        '\\<Midarrow>'             : '\U00002550',
        '\\<hookleftarrow>'        : '\U000021a9',
        '\\<hookrightarrow>'       : '\U000021aa',
        '\\<leftharpoondown>'      : '\U000021bd',
        '\\<rightharpoondown>'     : '\U000021c1',
        '\\<leftharpoonup>'        : '\U000021bc',
        '\\<rightharpoonup>'       : '\U000021c0',
        '\\<rightleftharpoons>'    : '\U000021cc',
        '\\<leadsto>'              : '\U0000219d',
        '\\<downharpoonleft>'      : '\U000021c3',
        '\\<downharpoonright>'     : '\U000021c2',
        '\\<upharpoonleft>'        : '\U000021bf',
        '\\<upharpoonright>'       : '\U000021be',
        '\\<restriction>'          : '\U000021be',
        '\\<Colon>'                : '\U00002237',
        '\\<up>'                   : '\U00002191',
        '\\<Up>'                   : '\U000021d1',
        '\\<down>'                 : '\U00002193',
        '\\<Down>'                 : '\U000021d3',
        '\\<updown>'               : '\U00002195',
        '\\<Updown>'               : '\U000021d5',
        '\\<langle>'               : '\U000027e8',
        '\\<rangle>'               : '\U000027e9',
        '\\<lceil>'                : '\U00002308',
        '\\<rceil>'                : '\U00002309',
        '\\<lfloor>'               : '\U0000230a',
        '\\<rfloor>'               : '\U0000230b',
        '\\<lparr>'                : '\U00002987',
        '\\<rparr>'                : '\U00002988',
        '\\<lbrakk>'               : '\U000027e6',
        '\\<rbrakk>'               : '\U000027e7',
        '\\<lbrace>'               : '\U00002983',
        '\\<rbrace>'               : '\U00002984',
        '\\<guillemotleft>'        : '\U000000ab',
        '\\<guillemotright>'       : '\U000000bb',
        '\\<bottom>'               : '\U000022a5',
        '\\<top>'                  : '\U000022a4',
        '\\<and>'                  : '\U00002227',
        '\\<And>'                  : '\U000022c0',
        '\\<or>'                   : '\U00002228',
        '\\<Or>'                   : '\U000022c1',
        '\\<forall>'               : '\U00002200',
        '\\<exists>'               : '\U00002203',
        '\\<nexists>'              : '\U00002204',
        '\\<not>'                  : '\U000000ac',
        '\\<box>'                  : '\U000025a1',
        '\\<diamond>'              : '\U000025c7',
        '\\<turnstile>'            : '\U000022a2',
        '\\<Turnstile>'            : '\U000022a8',
        '\\<tturnstile>'           : '\U000022a9',
        '\\<TTurnstile>'           : '\U000022ab',
        '\\<stileturn>'            : '\U000022a3',
        '\\<surd>'                 : '\U0000221a',
        '\\<le>'                   : '\U00002264',
        '\\<ge>'                   : '\U00002265',
        '\\<lless>'                : '\U0000226a',
        '\\<ggreater>'             : '\U0000226b',
        '\\<lesssim>'              : '\U00002272',
        '\\<greatersim>'           : '\U00002273',
        '\\<lessapprox>'           : '\U00002a85',
        '\\<greaterapprox>'        : '\U00002a86',
        '\\<in>'                   : '\U00002208',
        '\\<notin>'                : '\U00002209',
        '\\<subset>'               : '\U00002282',
        '\\<supset>'               : '\U00002283',
        '\\<subseteq>'             : '\U00002286',
        '\\<supseteq>'             : '\U00002287',
        '\\<sqsubset>'             : '\U0000228f',
        '\\<sqsupset>'             : '\U00002290',
        '\\<sqsubseteq>'           : '\U00002291',
        '\\<sqsupseteq>'           : '\U00002292',
        '\\<inter>'                : '\U00002229',
        '\\<Inter>'                : '\U000022c2',
        '\\<union>'                : '\U0000222a',
        '\\<Union>'                : '\U000022c3',
        '\\<squnion>'              : '\U00002294',
        '\\<Squnion>'              : '\U00002a06',
        '\\<sqinter>'              : '\U00002293',
        '\\<Sqinter>'              : '\U00002a05',
        '\\<setminus>'             : '\U00002216',
        '\\<propto>'               : '\U0000221d',
        '\\<uplus>'                : '\U0000228e',
        '\\<Uplus>'                : '\U00002a04',
        '\\<noteq>'                : '\U00002260',
        '\\<sim>'                  : '\U0000223c',
        '\\<doteq>'                : '\U00002250',
        '\\<simeq>'                : '\U00002243',
        '\\<approx>'               : '\U00002248',
        '\\<asymp>'                : '\U0000224d',
        '\\<cong>'                 : '\U00002245',
        '\\<smile>'                : '\U00002323',
        '\\<equiv>'                : '\U00002261',
        '\\<frown>'                : '\U00002322',
        '\\<Join>'                 : '\U000022c8',
        '\\<bowtie>'               : '\U00002a1d',
        '\\<prec>'                 : '\U0000227a',
        '\\<succ>'                 : '\U0000227b',
        '\\<preceq>'               : '\U0000227c',
        '\\<succeq>'               : '\U0000227d',
        '\\<parallel>'             : '\U00002225',
        '\\<bar>'                  : '\U000000a6',
        '\\<plusminus>'            : '\U000000b1',
        '\\<minusplus>'            : '\U00002213',
        '\\<times>'                : '\U000000d7',
        '\\<div>'                  : '\U000000f7',
        '\\<cdot>'                 : '\U000022c5',
        '\\<star>'                 : '\U000022c6',
        '\\<bullet>'               : '\U00002219',
        '\\<circ>'                 : '\U00002218',
        '\\<dagger>'               : '\U00002020',
        '\\<ddagger>'              : '\U00002021',
        '\\<lhd>'                  : '\U000022b2',
        '\\<rhd>'                  : '\U000022b3',
        '\\<unlhd>'                : '\U000022b4',
        '\\<unrhd>'                : '\U000022b5',
        '\\<triangleleft>'         : '\U000025c3',
        '\\<triangleright>'        : '\U000025b9',
        '\\<triangle>'             : '\U000025b3',
        '\\<triangleq>'            : '\U0000225c',
        '\\<oplus>'                : '\U00002295',
        '\\<Oplus>'                : '\U00002a01',
        '\\<otimes>'               : '\U00002297',
        '\\<Otimes>'               : '\U00002a02',
        '\\<odot>'                 : '\U00002299',
        '\\<Odot>'                 : '\U00002a00',
        '\\<ominus>'               : '\U00002296',
        '\\<oslash>'               : '\U00002298',
        '\\<dots>'                 : '\U00002026',
        '\\<cdots>'                : '\U000022ef',
        '\\<Sum>'                  : '\U00002211',
        '\\<Prod>'                 : '\U0000220f',
        '\\<Coprod>'               : '\U00002210',
        '\\<infinity>'             : '\U0000221e',
        '\\<integral>'             : '\U0000222b',
        '\\<ointegral>'            : '\U0000222e',
        '\\<clubsuit>'             : '\U00002663',
        '\\<diamondsuit>'          : '\U00002662',
        '\\<heartsuit>'            : '\U00002661',
        '\\<spadesuit>'            : '\U00002660',
        '\\<aleph>'                : '\U00002135',
        '\\<emptyset>'             : '\U00002205',
        '\\<nabla>'                : '\U00002207',
        '\\<partial>'              : '\U00002202',
        '\\<flat>'                 : '\U0000266d',
        '\\<natural>'              : '\U0000266e',
        '\\<sharp>'                : '\U0000266f',
        '\\<angle>'                : '\U00002220',
        '\\<copyright>'            : '\U000000a9',
        '\\<registered>'           : '\U000000ae',
        '\\<hyphen>'               : '\U000000ad',
        '\\<inverse>'              : '\U000000af',
        '\\<onequarter>'           : '\U000000bc',
        '\\<onehalf>'              : '\U000000bd',
        '\\<threequarters>'        : '\U000000be',
        '\\<ordfeminine>'          : '\U000000aa',
        '\\<ordmasculine>'         : '\U000000ba',
        '\\<section>'              : '\U000000a7',
        '\\<paragraph>'            : '\U000000b6',
        '\\<exclamdown>'           : '\U000000a1',
        '\\<questiondown>'         : '\U000000bf',
        '\\<euro>'                 : '\U000020ac',
        '\\<pounds>'               : '\U000000a3',
        '\\<yen>'                  : '\U000000a5',
        '\\<cent>'                 : '\U000000a2',
        '\\<currency>'             : '\U000000a4',
        '\\<degree>'               : '\U000000b0',
        '\\<amalg>'                : '\U00002a3f',
        '\\<mho>'                  : '\U00002127',
        '\\<lozenge>'              : '\U000025ca',
        '\\<wp>'                   : '\U00002118',
        '\\<wrong>'                : '\U00002240',
        '\\<struct>'               : '\U000022c4',
        '\\<acute>'                : '\U000000b4',
        '\\<index>'                : '\U00000131',
        '\\<dieresis>'             : '\U000000a8',
        '\\<cedilla>'              : '\U000000b8',
        '\\<hungarumlaut>'         : '\U000002dd',
        '\\<some>'                 : '\U000003f5',
        '\\<newline>'              : '\U000023ce',
        '\\<open>'                 : '\U00002039',
        '\\<close>'                : '\U0000203a',
        '\\<here>'                 : '\U00002302',
        '\\<^sub>'                 : '\U000021e9',
        '\\<^sup>'                 : '\U000021e7',
        '\\<^bold>'                : '\U00002759',
        '\\<^bsub>'                : '\U000021d8',
        '\\<^esub>'                : '\U000021d9',
        '\\<^bsup>'                : '\U000021d7',
        '\\<^esup>'                : '\U000021d6',
    }

    lang_map = {'isabelle' : isabelle_symbols, 'latex' : latex_symbols}

    def __init__(self, **options):
        Filter.__init__(self, **options)
        lang = get_choice_opt(options, 'lang',
                              ['isabelle', 'latex'], 'isabelle')
        self.symbols = self.lang_map[lang]

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if value in self.symbols:
                yield ttype, self.symbols[value]
            else:
                yield ttype, value


class KeywordCaseFilter(Filter):
    """Convert keywords to lowercase or uppercase or capitalize them, which
    means first letter uppercase, rest lowercase.

    This can be useful e.g. if you highlight Pascal code and want to adapt the
    code to your styleguide.

    Options accepted:

    `case` : string
       The casing to convert keywords to. Must be one of ``'lower'``,
       ``'upper'`` or ``'capitalize'``.  The default is ``'lower'``.
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        case = get_choice_opt(options, 'case',
                              ['lower', 'upper', 'capitalize'], 'lower')
        self.convert = getattr(str, case)

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if ttype in Keyword:
                yield ttype, self.convert(value)
            else:
                yield ttype, value


class NameHighlightFilter(Filter):
    """Highlight a normal Name (and Name.*) token with a different token type.

    Example::

        filter = NameHighlightFilter(
            names=['foo', 'bar', 'baz'],
            tokentype=Name.Function,
        )

    This would highlight the names "foo", "bar" and "baz"
    as functions. `Name.Function` is the default token type.

    Options accepted:

    `names` : list of strings
      A list of names that should be given the different token type.
      There is no default.
    `tokentype` : TokenType or string
      A token type or a string containing a token type name that is
      used for highlighting the strings in `names`.  The default is
      `Name.Function`.
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        self.names = set(get_list_opt(options, 'names', []))
        tokentype = options.get('tokentype')
        if tokentype:
            self.tokentype = string_to_tokentype(tokentype)
        else:
            self.tokentype = Name.Function

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if ttype in Name and value in self.names:
                yield self.tokentype, value
            else:
                yield ttype, value


class ErrorToken(Exception):
    pass


class RaiseOnErrorTokenFilter(Filter):
    """Raise an exception when the lexer generates an error token.

    Options accepted:

    `excclass` : Exception class
      The exception class to raise.
      The default is `pygments.filters.ErrorToken`.

    .. versionadded:: 0.8
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        self.exception = options.get('excclass', ErrorToken)
        try:
            # issubclass() will raise TypeError if first argument is not a class
            if not issubclass(self.exception, Exception):
                raise TypeError
        except TypeError:
            raise OptionError('excclass option is not an exception class')

    def filter(self, lexer, stream):
        for ttype, value in stream:
            if ttype is Error:
                raise self.exception(value)
            yield ttype, value


class VisibleWhitespaceFilter(Filter):
    """Convert tabs, newlines and/or spaces to visible characters.

    Options accepted:

    `spaces` : string or bool
      If this is a one-character string, spaces will be replaces by this string.
      If it is another true value, spaces will be replaced by ``·`` (unicode
      MIDDLE DOT).  If it is a false value, spaces will not be replaced.  The
      default is ``False``.
    `tabs` : string or bool
      The same as for `spaces`, but the default replacement character is ``»``
      (unicode RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK).  The default value
      is ``False``.  Note: this will not work if the `tabsize` option for the
      lexer is nonzero, as tabs will already have been expanded then.
    `tabsize` : int
      If tabs are to be replaced by this filter (see the `tabs` option), this
      is the total number of characters that a tab should be expanded to.
      The default is ``8``.
    `newlines` : string or bool
      The same as for `spaces`, but the default replacement character is ``¶``
      (unicode PILCROW SIGN).  The default value is ``False``.
    `wstokentype` : bool
      If true, give whitespace the special `Whitespace` token type.  This allows
      styling the visible whitespace differently (e.g. greyed out), but it can
      disrupt background colors.  The default is ``True``.

    .. versionadded:: 0.8
    """

    def __init__(self, **options):
        Filter.__init__(self, **options)
        for name, default in [('spaces',   '·'),
                              ('tabs',     '»'),
                              ('newlines', '¶')]:
            opt = options.get(name, False)
            if isinstance(opt, str) and len(opt) == 1:
                setattr(self, name, opt)
            else:
                setattr(self, name, (opt and default or ''))
        tabsize = get_int_opt(options, 'tabsize', 8)
        if self.tabs:
            self.tabs += ' ' * (tabsize - 1)
        if self.newlines:
            self.newlines += '\n'
        self.wstt = get_bool_opt(options, 'wstokentype', True)

    def filter(self, lexer, stream):
        if self.wstt:
            spaces = self.spaces or ' '
            tabs = self.tabs or '\t'
            newlines = self.newlines or '\n'
            regex = re.compile(r'\s')

            def replacefunc(wschar):
                if wschar == ' ':
                    return spaces
                elif wschar == '\t':
                    return tabs
                elif wschar == '\n':
                    return newlines
                return wschar

            for ttype, value in stream:
                yield from _replace_special(ttype, value, regex, Whitespace,
                                            replacefunc)
        else:
            spaces, tabs, newlines = self.spaces, self.tabs, self.newlines
            # simpler processing
            for ttype, value in stream:
                if spaces:
                    value = value.replace(' ', spaces)
                if tabs:
                    value = value.replace('\t', tabs)
                if newlines:
                    value = value.replace('\n', newlines)
                yield ttype, value


class GobbleFilter(Filter):
    """Gobbles source code lines (eats initial characters).

    This filter drops the first ``n`` characters off every line of code.  This
    may be useful when the source code fed to the lexer is indented by a fixed
    amount of space that isn't desired in the output.

    Options accepted:

    `n` : int
       The number of characters to gobble.

    .. versionadded:: 1.2
    """
    def __init__(self, **options):
        Filter.__init__(self, **options)
        self.n = get_int_opt(options, 'n', 0)

    def gobble(self, value, left):
        if left < len(value):
            return value[left:], 0
        else:
            return '', left - len(value)

    def filter(self, lexer, stream):
        n = self.n
        left = n  # How many characters left to gobble.
        for ttype, value in stream:
            # Remove ``left`` tokens from first line, ``n`` from all others.
            parts = value.split('\n')
            (parts[0], left) = self.gobble(parts[0], left)
            for i in range(1, len(parts)):
                (parts[i], left) = self.gobble(parts[i], n)
            value = '\n'.join(parts)

            if value != '':
                yield ttype, value


class TokenMergeFilter(Filter):
    """Merges consecutive tokens with the same token type in the output
    stream of a lexer.

    .. versionadded:: 1.2
    """
    def __init__(self, **options):
        Filter.__init__(self, **options)

    def filter(self, lexer, stream):
        current_type = None
        current_value = None
        for ttype, value in stream:
            if ttype is current_type:
                current_value += value
            else:
                if current_type is not None:
                    yield current_type, current_value
                current_type = ttype
                current_value = value
        if current_type is not None:
            yield current_type, current_value


FILTERS = {
    'codetagify':     CodeTagFilter,
    'keywordcase':    KeywordCaseFilter,
    'highlight':      NameHighlightFilter,
    'raiseonerror':   RaiseOnErrorTokenFilter,
    'whitespace':     VisibleWhitespaceFilter,
    'gobble':         GobbleFilter,
    'tokenmerge':     TokenMergeFilter,
    'symbols':        SymbolFilter,
}

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_bytecode_utils.py ===
"""
Bytecode analysing utils. Originally added for using in smart step into.

Note: not importable from Python 2.
"""

from _pydev_bundle import pydev_log
from types import CodeType
from _pydevd_frame_eval.vendored.bytecode.instr import _Variable, Label
from _pydevd_frame_eval.vendored import bytecode
from _pydevd_frame_eval.vendored.bytecode import cfg as bytecode_cfg
import dis
import opcode as _opcode

from _pydevd_bundle.pydevd_constants import KeyifyList, DebugInfoHolder, IS_PY311_OR_GREATER
from bisect import bisect
from collections import deque
import traceback

# When True, throws errors on unknown bytecodes, when False, ignore those as if they didn't change the stack.
STRICT_MODE = False

GO_INTO_INNER_CODES = True

DEBUG = False

_BINARY_OPS = set([opname for opname in dis.opname if opname.startswith("BINARY_")])

_BINARY_OP_MAP = {
    "BINARY_POWER": "__pow__",
    "BINARY_MULTIPLY": "__mul__",
    "BINARY_MATRIX_MULTIPLY": "__matmul__",
    "BINARY_FLOOR_DIVIDE": "__floordiv__",
    "BINARY_TRUE_DIVIDE": "__div__",
    "BINARY_MODULO": "__mod__",
    "BINARY_ADD": "__add__",
    "BINARY_SUBTRACT": "__sub__",
    "BINARY_LSHIFT": "__lshift__",
    "BINARY_RSHIFT": "__rshift__",
    "BINARY_AND": "__and__",
    "BINARY_OR": "__or__",
    "BINARY_XOR": "__xor__",
    "BINARY_SUBSCR": "__getitem__",
    "BINARY_DIVIDE": "__div__",
}

_COMP_OP_MAP = {
    "<": "__lt__",
    "<=": "__le__",
    "==": "__eq__",
    "!=": "__ne__",
    ">": "__gt__",
    ">=": "__ge__",
    "in": "__contains__",
    "not in": "__contains__",
}


class Target(object):
    __slots__ = ["arg", "lineno", "endlineno", "startcol", "endcol", "offset", "children_targets"]

    def __init__(
        self,
        arg,
        lineno,
        offset,
        children_targets=(),
        # These are optional (only Python 3.11 onwards).
        endlineno=-1,
        startcol=-1,
        endcol=-1,
    ):
        self.arg = arg
        self.lineno = lineno
        self.endlineno = endlineno
        self.startcol = startcol
        self.endcol = endcol

        self.offset = offset
        self.children_targets = children_targets

    def __repr__(self):
        ret = []
        for s in self.__slots__:
            ret.append("%s: %s" % (s, getattr(self, s)))
        return "Target(%s)" % ", ".join(ret)

    __str__ = __repr__


class _TargetIdHashable(object):
    def __init__(self, target):
        self.target = target

    def __eq__(self, other):
        if not hasattr(other, "target"):
            return
        return other.target is self.target

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return id(self.target)


class _StackInterpreter(object):
    """
    Good reference: https://github.com/python/cpython/blob/fcb55c0037baab6f98f91ee38ce84b6f874f034a/Python/ceval.c
    """

    def __init__(self, bytecode):
        self.bytecode = bytecode
        self._stack = deque()
        self.function_calls = []
        self.load_attrs = {}
        self.func = set()
        self.func_name_id_to_code_object = {}

    def __str__(self):
        return "Stack:\nFunction calls:\n%s\nLoad attrs:\n%s\n" % (self.function_calls, list(self.load_attrs.values()))

    def _getname(self, instr):
        if instr.opcode in _opcode.hascompare:
            cmp_op = dis.cmp_op[instr.arg]
            if cmp_op not in ("exception match", "BAD"):
                return _COMP_OP_MAP.get(cmp_op, cmp_op)
        return instr.arg

    def _getcallname(self, instr):
        if instr.name == "BINARY_SUBSCR":
            return "__getitem__().__call__"
        if instr.name == "CALL_FUNCTION":
            # Note: previously a '__call__().__call__' was returned, but this was a bit weird
            # and on Python 3.9 this construct could appear for some internal things where
            # it wouldn't be expected.
            # Note: it'd be what we had in func()().
            return None
        if instr.name == "MAKE_FUNCTION":
            return "__func__().__call__"
        if instr.name == "LOAD_ASSERTION_ERROR":
            return "AssertionError"
        name = self._getname(instr)
        if isinstance(name, CodeType):
            name = name.co_qualname  # Note: only available for Python 3.11
        if isinstance(name, _Variable):
            name = name.name
        if isinstance(name, tuple):
            # Load attr in Python 3.12 comes with (bool, name)
            if len(name) == 2 and isinstance(name[0], bool) and isinstance(name[1], str):
                name = name[1]

        if not isinstance(name, str):
            return None
        if name.endswith(">"):  # xxx.<listcomp>, xxx.<lambda>, ...
            return name.split(".")[-1]
        return name

    def _no_stack_change(self, instr):
        pass  # Can be aliased when the instruction does nothing.

    def on_LOAD_GLOBAL(self, instr):
        self._stack.append(instr)

    def on_POP_TOP(self, instr):
        try:
            self._stack.pop()
        except IndexError:
            pass  # Ok (in the end of blocks)

    def on_LOAD_ATTR(self, instr):
        self.on_POP_TOP(instr)  # replaces the current top
        self._stack.append(instr)
        self.load_attrs[_TargetIdHashable(instr)] = Target(self._getname(instr), instr.lineno, instr.offset)

    on_LOOKUP_METHOD = on_LOAD_ATTR  # Improvement in PyPy

    def on_LOAD_CONST(self, instr):
        self._stack.append(instr)

    on_LOAD_DEREF = on_LOAD_CONST
    on_LOAD_NAME = on_LOAD_CONST
    on_LOAD_CLOSURE = on_LOAD_CONST
    on_LOAD_CLASSDEREF = on_LOAD_CONST

    # Although it actually changes the stack, it's inconsequential for us as a function call can't
    # really be found there.
    on_IMPORT_NAME = _no_stack_change
    on_IMPORT_FROM = _no_stack_change
    on_IMPORT_STAR = _no_stack_change
    on_SETUP_ANNOTATIONS = _no_stack_change

    def on_STORE_FAST(self, instr):
        try:
            self._stack.pop()
        except IndexError:
            pass  # Ok, we may have a block just with the store

        # Note: it stores in the locals and doesn't put anything in the stack.

    on_STORE_GLOBAL = on_STORE_FAST
    on_STORE_DEREF = on_STORE_FAST
    on_STORE_ATTR = on_STORE_FAST
    on_STORE_NAME = on_STORE_FAST

    on_DELETE_NAME = on_POP_TOP
    on_DELETE_ATTR = on_POP_TOP
    on_DELETE_GLOBAL = on_POP_TOP
    on_DELETE_FAST = on_POP_TOP
    on_DELETE_DEREF = on_POP_TOP

    on_DICT_UPDATE = on_POP_TOP
    on_SET_UPDATE = on_POP_TOP

    on_GEN_START = on_POP_TOP

    def on_NOP(self, instr):
        pass

    def _handle_call_from_instr(self, func_name_instr, func_call_instr):
        self.load_attrs.pop(_TargetIdHashable(func_name_instr), None)
        call_name = self._getcallname(func_name_instr)
        target = None
        if not call_name:
            pass  # Ignore if we can't identify a name
        elif call_name in ("<listcomp>", "<genexpr>", "<setcomp>", "<dictcomp>"):
            code_obj = self.func_name_id_to_code_object[_TargetIdHashable(func_name_instr)]
            if code_obj is not None and GO_INTO_INNER_CODES:
                children_targets = _get_smart_step_into_targets(code_obj)
                if children_targets:
                    # i.e.: we have targets inside of a <listcomp> or <genexpr>.
                    # Note that to actually match this in the debugger we need to do matches on 2 frames,
                    # the one with the <listcomp> and then the actual target inside the <listcomp>.
                    target = Target(call_name, func_name_instr.lineno, func_call_instr.offset, children_targets)
                    self.function_calls.append(target)

        else:
            # Ok, regular call
            target = Target(call_name, func_name_instr.lineno, func_call_instr.offset)
            self.function_calls.append(target)

        if DEBUG and target is not None:
            print("Created target", target)
        self._stack.append(func_call_instr)  # Keep the func call as the result

    def on_COMPARE_OP(self, instr):
        try:
            _right = self._stack.pop()
        except IndexError:
            return
        try:
            _left = self._stack.pop()
        except IndexError:
            return

        cmp_op = dis.cmp_op[instr.arg]
        if cmp_op not in ("exception match", "BAD"):
            self.function_calls.append(Target(self._getname(instr), instr.lineno, instr.offset))

        self._stack.append(instr)

    def on_IS_OP(self, instr):
        try:
            self._stack.pop()
        except IndexError:
            return
        try:
            self._stack.pop()
        except IndexError:
            return

    def on_BINARY_SUBSCR(self, instr):
        try:
            _sub = self._stack.pop()
        except IndexError:
            return
        try:
            _container = self._stack.pop()
        except IndexError:
            return
        self.function_calls.append(Target(_BINARY_OP_MAP[instr.name], instr.lineno, instr.offset))
        self._stack.append(instr)

    on_BINARY_MATRIX_MULTIPLY = on_BINARY_SUBSCR
    on_BINARY_POWER = on_BINARY_SUBSCR
    on_BINARY_MULTIPLY = on_BINARY_SUBSCR
    on_BINARY_FLOOR_DIVIDE = on_BINARY_SUBSCR
    on_BINARY_TRUE_DIVIDE = on_BINARY_SUBSCR
    on_BINARY_MODULO = on_BINARY_SUBSCR
    on_BINARY_ADD = on_BINARY_SUBSCR
    on_BINARY_SUBTRACT = on_BINARY_SUBSCR
    on_BINARY_LSHIFT = on_BINARY_SUBSCR
    on_BINARY_RSHIFT = on_BINARY_SUBSCR
    on_BINARY_AND = on_BINARY_SUBSCR
    on_BINARY_OR = on_BINARY_SUBSCR
    on_BINARY_XOR = on_BINARY_SUBSCR

    def on_LOAD_METHOD(self, instr):
        self.on_POP_TOP(instr)  # Remove the previous as we're loading something from it.
        self._stack.append(instr)

    def on_MAKE_FUNCTION(self, instr):
        if not IS_PY311_OR_GREATER:
            # The qualifier name is no longer put in the stack.
            qualname = self._stack.pop()
            code_obj_instr = self._stack.pop()
        else:
            # In 3.11 the code object has a co_qualname which we can use.
            qualname = code_obj_instr = self._stack.pop()

        arg = instr.arg
        if arg & 0x08:
            _func_closure = self._stack.pop()
        if arg & 0x04:
            _func_annotations = self._stack.pop()
        if arg & 0x02:
            _func_kwdefaults = self._stack.pop()
        if arg & 0x01:
            _func_defaults = self._stack.pop()

        call_name = self._getcallname(qualname)
        if call_name in ("<genexpr>", "<listcomp>", "<setcomp>", "<dictcomp>"):
            if isinstance(code_obj_instr.arg, CodeType):
                self.func_name_id_to_code_object[_TargetIdHashable(qualname)] = code_obj_instr.arg
        self._stack.append(qualname)

    def on_LOAD_FAST(self, instr):
        self._stack.append(instr)

    on_LOAD_FAST_AND_CLEAR = on_LOAD_FAST
    on_LOAD_FAST_CHECK = on_LOAD_FAST

    def on_LOAD_ASSERTION_ERROR(self, instr):
        self._stack.append(instr)

    on_LOAD_BUILD_CLASS = on_LOAD_FAST

    def on_CALL_METHOD(self, instr):
        # pop the actual args
        for _ in range(instr.arg):
            self._stack.pop()

        func_name_instr = self._stack.pop()
        self._handle_call_from_instr(func_name_instr, instr)

    def on_CALL(self, instr):
        # pop the actual args
        for _ in range(instr.arg):
            self._stack.pop()

        func_name_instr = self._stack.pop()
        if self._getcallname(func_name_instr) is None:
            func_name_instr = self._stack.pop()

        if self._stack:
            peeked = self._stack[-1]
            if peeked.name == "PUSH_NULL":
                self._stack.pop()

        self._handle_call_from_instr(func_name_instr, instr)

    def on_CALL_INTRINSIC_1(self, instr):
        try:
            func_name_instr = self._stack.pop()
        except IndexError:
            return

        if self._stack:
            peeked = self._stack[-1]
            if peeked.name == "PUSH_NULL":
                self._stack.pop()

        self._handle_call_from_instr(func_name_instr, instr)

    def on_PUSH_NULL(self, instr):
        self._stack.append(instr)

    def on_KW_NAMES(self, instr):
        return

    def on_RETURN_CONST(self, instr):
        return

    def on_CALL_FUNCTION(self, instr):
        arg = instr.arg

        argc = arg & 0xFF  # positional args
        argc += (arg >> 8) * 2  # keyword args

        # pop the actual args
        for _ in range(argc):
            try:
                self._stack.pop()
            except IndexError:
                return

        try:
            func_name_instr = self._stack.pop()
        except IndexError:
            return
        self._handle_call_from_instr(func_name_instr, instr)

    def on_CALL_FUNCTION_KW(self, instr):
        # names of kw args
        _names_of_kw_args = self._stack.pop()

        # pop the actual args
        arg = instr.arg

        argc = arg & 0xFF  # positional args
        argc += (arg >> 8) * 2  # keyword args

        for _ in range(argc):
            self._stack.pop()

        func_name_instr = self._stack.pop()
        self._handle_call_from_instr(func_name_instr, instr)

    def on_CALL_FUNCTION_VAR(self, instr):
        # var name
        _var_arg = self._stack.pop()

        # pop the actual args
        arg = instr.arg

        argc = arg & 0xFF  # positional args
        argc += (arg >> 8) * 2  # keyword args

        for _ in range(argc):
            self._stack.pop()

        func_name_instr = self._stack.pop()
        self._handle_call_from_instr(func_name_instr, instr)

    def on_CALL_FUNCTION_VAR_KW(self, instr):
        # names of kw args
        _names_of_kw_args = self._stack.pop()

        arg = instr.arg

        argc = arg & 0xFF  # positional args
        argc += (arg >> 8) * 2  # keyword args

        # also pop **kwargs
        self._stack.pop()

        # pop the actual args
        for _ in range(argc):
            self._stack.pop()

        func_name_instr = self._stack.pop()
        self._handle_call_from_instr(func_name_instr, instr)

    def on_CALL_FUNCTION_EX(self, instr):
        if instr.arg & 0x01:
            _kwargs = self._stack.pop()
        _callargs = self._stack.pop()
        func_name_instr = self._stack.pop()
        self._handle_call_from_instr(func_name_instr, instr)

    on_GET_AITER = _no_stack_change
    on_GET_ANEXT = _no_stack_change
    on_END_FOR = _no_stack_change
    on_END_ASYNC_FOR = _no_stack_change
    on_BEFORE_ASYNC_WITH = _no_stack_change
    on_SETUP_ASYNC_WITH = _no_stack_change
    on_YIELD_FROM = _no_stack_change
    on_SETUP_LOOP = _no_stack_change
    on_FOR_ITER = _no_stack_change
    on_BREAK_LOOP = _no_stack_change
    on_JUMP_ABSOLUTE = _no_stack_change
    on_RERAISE = _no_stack_change
    on_LIST_TO_TUPLE = _no_stack_change
    on_CALL_FINALLY = _no_stack_change
    on_POP_FINALLY = _no_stack_change

    def on_JUMP_IF_FALSE_OR_POP(self, instr):
        try:
            self._stack.pop()
        except IndexError:
            return

    on_JUMP_IF_TRUE_OR_POP = on_JUMP_IF_FALSE_OR_POP

    def on_JUMP_IF_NOT_EXC_MATCH(self, instr):
        try:
            self._stack.pop()
        except IndexError:
            return
        try:
            self._stack.pop()
        except IndexError:
            return

    def on_SWAP(self, instr):
        i = instr.arg
        try:
            self._stack[-i], self._stack[-1] = self._stack[-1], self._stack[-i]
        except:
            pass

    def on_ROT_TWO(self, instr):
        try:
            p0 = self._stack.pop()
        except IndexError:
            return

        try:
            p1 = self._stack.pop()
        except:
            self._stack.append(p0)
            return

        self._stack.append(p0)
        self._stack.append(p1)

    def on_ROT_THREE(self, instr):
        try:
            p0 = self._stack.pop()
        except IndexError:
            return

        try:
            p1 = self._stack.pop()
        except:
            self._stack.append(p0)
            return

        try:
            p2 = self._stack.pop()
        except:
            self._stack.append(p0)
            self._stack.append(p1)
            return

        self._stack.append(p0)
        self._stack.append(p1)
        self._stack.append(p2)

    def on_ROT_FOUR(self, instr):
        try:
            p0 = self._stack.pop()
        except IndexError:
            return

        try:
            p1 = self._stack.pop()
        except:
            self._stack.append(p0)
            return

        try:
            p2 = self._stack.pop()
        except:
            self._stack.append(p0)
            self._stack.append(p1)
            return

        try:
            p3 = self._stack.pop()
        except:
            self._stack.append(p0)
            self._stack.append(p1)
            self._stack.append(p2)
            return

        self._stack.append(p0)
        self._stack.append(p1)
        self._stack.append(p2)
        self._stack.append(p3)

    def on_BUILD_LIST_FROM_ARG(self, instr):
        self._stack.append(instr)

    def on_BUILD_MAP(self, instr):
        for _i in range(instr.arg):
            self._stack.pop()
            self._stack.pop()
        self._stack.append(instr)

    def on_BUILD_CONST_KEY_MAP(self, instr):
        self.on_POP_TOP(instr)  # keys
        for _i in range(instr.arg):
            self.on_POP_TOP(instr)  # value
        self._stack.append(instr)

    on_YIELD_VALUE = on_POP_TOP
    on_RETURN_VALUE = on_POP_TOP
    on_POP_JUMP_IF_FALSE = on_POP_TOP
    on_POP_JUMP_IF_TRUE = on_POP_TOP
    on_DICT_MERGE = on_POP_TOP
    on_LIST_APPEND = on_POP_TOP
    on_SET_ADD = on_POP_TOP
    on_LIST_EXTEND = on_POP_TOP
    on_UNPACK_EX = on_POP_TOP

    # ok: doesn't change the stack (converts top to getiter(top))
    on_GET_ITER = _no_stack_change
    on_GET_AWAITABLE = _no_stack_change
    on_GET_YIELD_FROM_ITER = _no_stack_change

    def on_RETURN_GENERATOR(self, instr):
        self._stack.append(instr)

    on_RETURN_GENERATOR = _no_stack_change
    on_RESUME = _no_stack_change

    def on_MAP_ADD(self, instr):
        self.on_POP_TOP(instr)
        self.on_POP_TOP(instr)

    def on_UNPACK_SEQUENCE(self, instr):
        self._stack.pop()
        for _i in range(instr.arg):
            self._stack.append(instr)

    def on_BUILD_LIST(self, instr):
        for _i in range(instr.arg):
            self.on_POP_TOP(instr)
        self._stack.append(instr)

    on_BUILD_TUPLE = on_BUILD_LIST
    on_BUILD_STRING = on_BUILD_LIST
    on_BUILD_TUPLE_UNPACK_WITH_CALL = on_BUILD_LIST
    on_BUILD_TUPLE_UNPACK = on_BUILD_LIST
    on_BUILD_LIST_UNPACK = on_BUILD_LIST
    on_BUILD_MAP_UNPACK_WITH_CALL = on_BUILD_LIST
    on_BUILD_MAP_UNPACK = on_BUILD_LIST
    on_BUILD_SET = on_BUILD_LIST
    on_BUILD_SET_UNPACK = on_BUILD_LIST

    on_SETUP_FINALLY = _no_stack_change
    on_POP_FINALLY = _no_stack_change
    on_BEGIN_FINALLY = _no_stack_change
    on_END_FINALLY = _no_stack_change

    def on_RAISE_VARARGS(self, instr):
        for _i in range(instr.arg):
            self.on_POP_TOP(instr)

    on_POP_BLOCK = _no_stack_change
    on_JUMP_FORWARD = _no_stack_change
    on_JUMP_BACKWARD = _no_stack_change
    on_JUMP_BACKWARD_NO_INTERRUPT = _no_stack_change
    on_POP_EXCEPT = _no_stack_change
    on_SETUP_EXCEPT = _no_stack_change
    on_WITH_EXCEPT_START = _no_stack_change

    on_END_FINALLY = _no_stack_change
    on_BEGIN_FINALLY = _no_stack_change
    on_SETUP_WITH = _no_stack_change
    on_WITH_CLEANUP_START = _no_stack_change
    on_WITH_CLEANUP_FINISH = _no_stack_change
    on_FORMAT_VALUE = _no_stack_change
    on_EXTENDED_ARG = _no_stack_change

    def on_INPLACE_ADD(self, instr):
        # This would actually pop 2 and leave the value in the stack.
        # In a += 1 it pop `a` and `1` and leave the resulting value
        # for a load. In our case, let's just pop the `1` and leave the `a`
        # instead of leaving the INPLACE_ADD bytecode.
        try:
            self._stack.pop()
        except IndexError:
            pass

    on_INPLACE_POWER = on_INPLACE_ADD
    on_INPLACE_MULTIPLY = on_INPLACE_ADD
    on_INPLACE_MATRIX_MULTIPLY = on_INPLACE_ADD
    on_INPLACE_TRUE_DIVIDE = on_INPLACE_ADD
    on_INPLACE_FLOOR_DIVIDE = on_INPLACE_ADD
    on_INPLACE_MODULO = on_INPLACE_ADD
    on_INPLACE_SUBTRACT = on_INPLACE_ADD
    on_INPLACE_RSHIFT = on_INPLACE_ADD
    on_INPLACE_LSHIFT = on_INPLACE_ADD
    on_INPLACE_AND = on_INPLACE_ADD
    on_INPLACE_OR = on_INPLACE_ADD
    on_INPLACE_XOR = on_INPLACE_ADD

    def on_DUP_TOP(self, instr):
        try:
            i = self._stack[-1]
        except IndexError:
            # ok (in the start of block)
            self._stack.append(instr)
        else:
            self._stack.append(i)

    def on_DUP_TOP_TWO(self, instr):
        if len(self._stack) == 0:
            self._stack.append(instr)
            return

        if len(self._stack) == 1:
            i = self._stack[-1]
            self._stack.append(i)
            self._stack.append(instr)
            return

        i = self._stack[-1]
        j = self._stack[-2]
        self._stack.append(j)
        self._stack.append(i)

    def on_BUILD_SLICE(self, instr):
        for _ in range(instr.arg):
            try:
                self._stack.pop()
            except IndexError:
                pass
        self._stack.append(instr)

    def on_STORE_SUBSCR(self, instr):
        try:
            self._stack.pop()
            self._stack.pop()
            self._stack.pop()
        except IndexError:
            pass

    def on_DELETE_SUBSCR(self, instr):
        try:
            self._stack.pop()
            self._stack.pop()
        except IndexError:
            pass

    # Note: on Python 3 this is only found on interactive mode to print the results of
    # some evaluation.
    on_PRINT_EXPR = on_POP_TOP

    on_LABEL = _no_stack_change
    on_UNARY_POSITIVE = _no_stack_change
    on_UNARY_NEGATIVE = _no_stack_change
    on_UNARY_NOT = _no_stack_change
    on_UNARY_INVERT = _no_stack_change

    on_CACHE = _no_stack_change
    on_PRECALL = _no_stack_change


def _get_smart_step_into_targets(code):
    """
    :return list(Target)
    """
    b = bytecode.Bytecode.from_code(code)
    cfg = bytecode_cfg.ControlFlowGraph.from_bytecode(b)

    ret = []

    for block in cfg:
        if DEBUG:
            print("\nStart block----")
        stack = _StackInterpreter(block)
        for instr in block:
            if isinstance(instr, (Label,)):
                # No name for these
                continue
            try:
                func_name = "on_%s" % (instr.name,)
                func = getattr(stack, func_name, None)

                if func is None:
                    if STRICT_MODE:
                        raise AssertionError("%s not found." % (func_name,))
                    else:
                        if DEBUG:
                            print("Skipping: %s." % (func_name,))

                        continue
                func(instr)

                if DEBUG:
                    if instr.name != "CACHE":  # Filter the ones we don't want to see.
                        print("\nHandled: ", instr, ">>", stack._getname(instr), "<<")
                        print("New stack:")
                        for entry in stack._stack:
                            print("    arg:", stack._getname(entry), "(", entry, ")")
            except:
                if STRICT_MODE:
                    raise  # Error in strict mode.
                else:
                    # In non-strict mode, log it (if in verbose mode) and keep on going.
                    if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 2:
                        pydev_log.exception("Exception computing step into targets (handled).")

        ret.extend(stack.function_calls)
        # No longer considering attr loads as calls (while in theory sometimes it's possible
        # that something as `some.attr` can turn out to be a property which could be stepped
        # in, it's not that common in practice and can be surprising for users, so, disabling
        # step into from stepping into properties).
        # ret.extend(stack.load_attrs.values())

        if DEBUG:
            print("\nEnd block----")
    return ret


# Note that the offset is unique within the frame (so, we can use it as the target id).
# Also, as the offset is the instruction offset within the frame, it's possible to
# to inspect the parent frame for frame.f_lasti to know where we actually are (as the
# caller name may not always match the new frame name).
class Variant(object):
    __slots__ = ["name", "is_visited", "line", "offset", "call_order", "children_variants", "parent", "endlineno", "startcol", "endcol"]

    def __init__(self, name, is_visited, line, offset, call_order, children_variants=None, endlineno=-1, startcol=-1, endcol=-1):
        self.name = name
        self.is_visited = is_visited
        self.line = line
        self.endlineno = endlineno
        self.startcol = startcol
        self.endcol = endcol
        self.offset = offset
        self.call_order = call_order
        self.children_variants = children_variants
        self.parent = None
        if children_variants:
            for variant in children_variants:
                variant.parent = self

    def __repr__(self):
        ret = []
        for s in self.__slots__:
            if s == "parent":
                try:
                    parent = self.parent
                except AttributeError:
                    ret.append("%s: <not set>" % (s,))
                else:
                    if parent is None:
                        ret.append("parent: None")
                    else:
                        ret.append("parent: %s (%s)" % (parent.name, parent.offset))
                continue

            if s == "children_variants":
                ret.append("children_variants: %s" % (len(self.children_variants) if self.children_variants else 0))
                continue

            try:
                ret.append("%s= %s" % (s, getattr(self, s)))
            except AttributeError:
                ret.append("%s: <not set>" % (s,))
        return "Variant(%s)" % ", ".join(ret)

    __str__ = __repr__


def _convert_target_to_variant(target, start_line, end_line, call_order_cache: dict, lasti: int, base: int):
    name = target.arg
    if not isinstance(name, str):
        return
    if target.lineno > end_line:
        return
    if target.lineno < start_line:
        return

    call_order = call_order_cache.get(name, 0) + 1
    call_order_cache[name] = call_order
    is_visited = target.offset <= lasti

    children_targets = target.children_targets
    children_variants = None
    if children_targets:
        children_variants = [
            _convert_target_to_variant(child, start_line, end_line, call_order_cache, lasti, base) for child in target.children_targets
        ]

    return Variant(
        name,
        is_visited,
        target.lineno - base,
        target.offset,
        call_order,
        children_variants,
        # Only really matter in Python 3.11
        target.endlineno - base if target.endlineno >= 0 else -1,
        target.startcol,
        target.endcol,
    )


def calculate_smart_step_into_variants(frame, start_line, end_line, base=0):
    """
    Calculate smart step into variants for the given line range.
    :param frame:
    :type frame: :py:class:`types.FrameType`
    :param start_line:
    :param end_line:
    :return: A list of call names from the first to the last.
    :note: it's guaranteed that the offsets appear in order.
    :raise: :py:class:`RuntimeError` if failed to parse the bytecode or if dis cannot be used.
    """
    if IS_PY311_OR_GREATER:
        from . import pydevd_bytecode_utils_py311

        return pydevd_bytecode_utils_py311.calculate_smart_step_into_variants(frame, start_line, end_line, base)

    variants = []
    code = frame.f_code
    lasti = frame.f_lasti

    call_order_cache = {}
    if DEBUG:
        print("dis.dis:")
        if IS_PY311_OR_GREATER:
            dis.dis(code, show_caches=False)
        else:
            dis.dis(code)

    for target in _get_smart_step_into_targets(code):
        variant = _convert_target_to_variant(target, start_line, end_line, call_order_cache, lasti, base)
        if variant is None:
            continue
        variants.append(variant)

    return variants


def get_smart_step_into_variant_from_frame_offset(frame_f_lasti, variants):
    """
    Given the frame.f_lasti, return the related `Variant`.

    :note: if the offset is found before any variant available or no variants are
           available, None is returned.

    :rtype: Variant|NoneType
    """
    if not variants:
        return None

    i = bisect(KeyifyList(variants, lambda entry: entry.offset), frame_f_lasti)

    if i == 0:
        return None

    else:
        return variants[i - 1]

# === NexusCore/openenv\Lib\site-packages\matplotlib\sphinxext\plot_directive.py ===
"""
A directive for including a Matplotlib plot in a Sphinx document
================================================================

This is a Sphinx extension providing a reStructuredText directive
``.. plot::`` for including a plot in a Sphinx document.

In HTML output, ``.. plot::`` will include a .png file with a link
to a high-res .png and .pdf.  In LaTeX output, it will include a .pdf.

The plot content may be defined in one of three ways:

1. **A path to a source file** as the argument to the directive::

     .. plot:: path/to/plot.py

   When a path to a source file is given, the content of the
   directive may optionally contain a caption for the plot::

     .. plot:: path/to/plot.py

        The plot caption.

   Additionally, one may specify the name of a function to call (with
   no arguments) immediately after importing the module::

     .. plot:: path/to/plot.py plot_function1

2. Included as **inline content** to the directive::

     .. plot::

        import matplotlib.pyplot as plt
        plt.plot([1, 2, 3], [4, 5, 6])
        plt.title("A plotting exammple")

3. Using **doctest** syntax::

     .. plot::

        A plotting example:
        >>> import matplotlib.pyplot as plt
        >>> plt.plot([1, 2, 3], [4, 5, 6])

Options
-------

The ``.. plot::`` directive supports the following options:

``:format:`` : {'python', 'doctest'}
    The format of the input.  If unset, the format is auto-detected.

``:include-source:`` : bool
    Whether to display the source code. The default can be changed using
    the ``plot_include_source`` variable in :file:`conf.py` (which itself
    defaults to False).

``:show-source-link:`` : bool
    Whether to show a link to the source in HTML. The default can be
    changed using the ``plot_html_show_source_link`` variable in
    :file:`conf.py` (which itself defaults to True).

``:context:`` : bool or str
    If provided, the code will be run in the context of all previous plot
    directives for which the ``:context:`` option was specified.  This only
    applies to inline code plot directives, not those run from files. If
    the ``:context: reset`` option is specified, the context is reset
    for this and future plots, and previous figures are closed prior to
    running the code. ``:context: close-figs`` keeps the context but closes
    previous figures before running the code.

``:nofigs:`` : bool
    If specified, the code block will be run, but no figures will be
    inserted.  This is usually useful with the ``:context:`` option.

``:caption:`` : str
    If specified, the option's argument will be used as a caption for the
    figure. This overwrites the caption given in the content, when the plot
    is generated from a file.

Additionally, this directive supports all the options of the `image directive
<https://docutils.sourceforge.io/docs/ref/rst/directives.html#image>`_,
except for ``:target:`` (since plot will add its own target).  These include
``:alt:``, ``:height:``, ``:width:``, ``:scale:``, ``:align:`` and ``:class:``.

Configuration options
---------------------

The plot directive has the following configuration options:

plot_include_source
    Default value for the include-source option (default: False).

plot_html_show_source_link
    Whether to show a link to the source in HTML (default: True).

plot_pre_code
    Code that should be executed before each plot. If None (the default),
    it will default to a string containing::

        import numpy as np
        from matplotlib import pyplot as plt

plot_basedir
    Base directory, to which ``plot::`` file names are relative to.
    If None or empty (the default), file names are relative to the
    directory where the file containing the directive is.

plot_formats
    File formats to generate (default: ['png', 'hires.png', 'pdf']).
    List of tuples or strings::

        [(suffix, dpi), suffix, ...]

    that determine the file format and the DPI. For entries whose
    DPI was omitted, sensible defaults are chosen. When passing from
    the command line through sphinx_build the list should be passed as
    suffix:dpi,suffix:dpi, ...

plot_html_show_formats
    Whether to show links to the files in HTML (default: True).

plot_rcparams
    A dictionary containing any non-standard rcParams that should
    be applied before each plot (default: {}).

plot_apply_rcparams
    By default, rcParams are applied when ``:context:`` option is not used
    in a plot directive.  If set, this configuration option overrides this
    behavior and applies rcParams before each plot.

plot_working_directory
    By default, the working directory will be changed to the directory of
    the example, so the code can get at its data files, if any.  Also its
    path will be added to `sys.path` so it can import any helper modules
    sitting beside it.  This configuration option can be used to specify
    a central directory (also added to `sys.path`) where data files and
    helper modules for all code are located.

plot_template
    Provide a customized template for preparing restructured text.

plot_srcset
    Allow the srcset image option for responsive image resolutions. List of
    strings with the multiplicative factors followed by an "x".
    e.g. ["2.0x", "1.5x"].  "2.0x" will create a png with the default "png"
    resolution from plot_formats, multiplied by 2. If plot_srcset is
    specified, the plot directive uses the
    :doc:`/api/sphinxext_figmpl_directive_api` (instead of the usual figure
    directive) in the intermediary rst file that is generated.
    The plot_srcset option is incompatible with *singlehtml* builds, and an
    error will be raised.

Notes on how it works
---------------------

The plot directive runs the code it is given, either in the source file or the
code under the directive. The figure created (if any) is saved in the sphinx
build directory under a subdirectory named ``plot_directive``.  It then creates
an intermediate rst file that calls a ``.. figure:`` directive (or
``.. figmpl::`` directive if ``plot_srcset`` is being used) and has links to
the ``*.png`` files in the ``plot_directive`` directory.  These translations can
be customized by changing the *plot_template*.  See the source of
:doc:`/api/sphinxext_plot_directive_api` for the templates defined in *TEMPLATE*
and *TEMPLATE_SRCSET*.
"""

import contextlib
import doctest
from io import StringIO
import itertools
import os
from os.path import relpath
from pathlib import Path
import re
import shutil
import sys
import textwrap
import traceback

from docutils.parsers.rst import directives, Directive
from docutils.parsers.rst.directives.images import Image
import jinja2  # Sphinx dependency.

from sphinx.errors import ExtensionError

import matplotlib
from matplotlib.backend_bases import FigureManagerBase
import matplotlib.pyplot as plt
from matplotlib import _pylab_helpers, cbook

matplotlib.use("agg")

__version__ = 2


# -----------------------------------------------------------------------------
# Registration hook
# -----------------------------------------------------------------------------


def _option_boolean(arg):
    if not arg or not arg.strip():
        # no argument given, assume used as a flag
        return True
    elif arg.strip().lower() in ('no', '0', 'false'):
        return False
    elif arg.strip().lower() in ('yes', '1', 'true'):
        return True
    else:
        raise ValueError(f'{arg!r} unknown boolean')


def _option_context(arg):
    if arg in [None, 'reset', 'close-figs']:
        return arg
    raise ValueError("Argument should be None or 'reset' or 'close-figs'")


def _option_format(arg):
    return directives.choice(arg, ('python', 'doctest'))


def mark_plot_labels(app, document):
    """
    To make plots referenceable, we need to move the reference from the
    "htmlonly" (or "latexonly") node to the actual figure node itself.
    """
    for name, explicit in document.nametypes.items():
        if not explicit:
            continue
        labelid = document.nameids[name]
        if labelid is None:
            continue
        node = document.ids[labelid]
        if node.tagname in ('html_only', 'latex_only'):
            for n in node:
                if n.tagname == 'figure':
                    sectname = name
                    for c in n:
                        if c.tagname == 'caption':
                            sectname = c.astext()
                            break

                    node['ids'].remove(labelid)
                    node['names'].remove(name)
                    n['ids'].append(labelid)
                    n['names'].append(name)
                    document.settings.env.labels[name] = \
                        document.settings.env.docname, labelid, sectname
                    break


class PlotDirective(Directive):
    """The ``.. plot::`` directive, as documented in the module's docstring."""

    has_content = True
    required_arguments = 0
    optional_arguments = 2
    final_argument_whitespace = False
    option_spec = {
        'alt': directives.unchanged,
        'height': directives.length_or_unitless,
        'width': directives.length_or_percentage_or_unitless,
        'scale': directives.nonnegative_int,
        'align': Image.align,
        'class': directives.class_option,
        'include-source': _option_boolean,
        'show-source-link': _option_boolean,
        'format': _option_format,
        'context': _option_context,
        'nofigs': directives.flag,
        'caption': directives.unchanged,
        }

    def run(self):
        """Run the plot directive."""
        try:
            return run(self.arguments, self.content, self.options,
                       self.state_machine, self.state, self.lineno)
        except Exception as e:
            raise self.error(str(e))


def _copy_css_file(app, exc):
    if exc is None and app.builder.format == 'html':
        src = cbook._get_data_path('plot_directive/plot_directive.css')
        dst = app.outdir / Path('_static')
        dst.mkdir(exist_ok=True)
        # Use copyfile because we do not want to copy src's permissions.
        shutil.copyfile(src, dst / Path('plot_directive.css'))


def setup(app):
    setup.app = app
    setup.config = app.config
    setup.confdir = app.confdir
    app.add_directive('plot', PlotDirective)
    app.add_config_value('plot_pre_code', None, True)
    app.add_config_value('plot_include_source', False, True)
    app.add_config_value('plot_html_show_source_link', True, True)
    app.add_config_value('plot_formats', ['png', 'hires.png', 'pdf'], True)
    app.add_config_value('plot_basedir', None, True)
    app.add_config_value('plot_html_show_formats', True, True)
    app.add_config_value('plot_rcparams', {}, True)
    app.add_config_value('plot_apply_rcparams', False, True)
    app.add_config_value('plot_working_directory', None, True)
    app.add_config_value('plot_template', None, True)
    app.add_config_value('plot_srcset', [], True)
    app.connect('doctree-read', mark_plot_labels)
    app.add_css_file('plot_directive.css')
    app.connect('build-finished', _copy_css_file)
    metadata = {'parallel_read_safe': True, 'parallel_write_safe': True,
                'version': matplotlib.__version__}
    return metadata


# -----------------------------------------------------------------------------
# Doctest handling
# -----------------------------------------------------------------------------


def contains_doctest(text):
    try:
        # check if it's valid Python as-is
        compile(text, '<string>', 'exec')
        return False
    except SyntaxError:
        pass
    r = re.compile(r'^\s*>>>', re.M)
    m = r.search(text)
    return bool(m)


def _split_code_at_show(text, function_name):
    """Split code at plt.show()."""

    is_doctest = contains_doctest(text)
    if function_name is None:
        parts = []
        part = []
        for line in text.split("\n"):
            if ((not is_doctest and line.startswith('plt.show(')) or
                   (is_doctest and line.strip() == '>>> plt.show()')):
                part.append(line)
                parts.append("\n".join(part))
                part = []
            else:
                part.append(line)
        if "\n".join(part).strip():
            parts.append("\n".join(part))
    else:
        parts = [text]
    return is_doctest, parts


# -----------------------------------------------------------------------------
# Template
# -----------------------------------------------------------------------------

_SOURCECODE = """
{{ source_code }}

.. only:: html

   {% if src_name or (html_show_formats and not multi_image) %}
   (
   {%- if src_name -%}
   :download:`Source code <{{ build_dir }}/{{ src_name }}>`
   {%- endif -%}
   {%- if html_show_formats and not multi_image -%}
     {%- for img in images -%}
       {%- for fmt in img.formats -%}
         {%- if src_name or not loop.first -%}, {% endif -%}
         :download:`{{ fmt }} <{{ build_dir }}/{{ img.basename }}.{{ fmt }}>`
       {%- endfor -%}
     {%- endfor -%}
   {%- endif -%}
   )
   {% endif %}
"""

TEMPLATE_SRCSET = _SOURCECODE + """
   {% for img in images %}
   .. figure-mpl:: {{ build_dir }}/{{ img.basename }}.{{ default_fmt }}
      {% for option in options -%}
      {{ option }}
      {% endfor %}
      {%- if caption -%}
      {{ caption }}  {# appropriate leading whitespace added beforehand #}
      {% endif -%}
      {%- if srcset -%}
        :srcset: {{ build_dir }}/{{ img.basename }}.{{ default_fmt }}
        {%- for sr in srcset -%}
            , {{ build_dir }}/{{ img.basename }}.{{ sr }}.{{ default_fmt }} {{sr}}
        {%- endfor -%}
      {% endif %}

   {% if html_show_formats and multi_image %}
   (
    {%- for fmt in img.formats -%}
    {%- if not loop.first -%}, {% endif -%}
    :download:`{{ fmt }} <{{ build_dir }}/{{ img.basename }}.{{ fmt }}>`
    {%- endfor -%}
   )
   {% endif %}


   {% endfor %}

.. only:: not html

   {% for img in images %}
   .. figure-mpl:: {{ build_dir }}/{{ img.basename }}.*
      {% for option in options -%}
      {{ option }}
      {% endfor -%}

      {{ caption }}  {# appropriate leading whitespace added beforehand #}
   {% endfor %}

"""

TEMPLATE = _SOURCECODE + """

   {% for img in images %}
   .. figure:: {{ build_dir }}/{{ img.basename }}.{{ default_fmt }}
      {% for option in options -%}
      {{ option }}
      {% endfor %}

      {% if html_show_formats and multi_image -%}
        (
        {%- for fmt in img.formats -%}
        {%- if not loop.first -%}, {% endif -%}
        :download:`{{ fmt }} <{{ build_dir }}/{{ img.basename }}.{{ fmt }}>`
        {%- endfor -%}
        )
      {%- endif -%}

      {{ caption }}  {# appropriate leading whitespace added beforehand #}
   {% endfor %}

.. only:: not html

   {% for img in images %}
   .. figure:: {{ build_dir }}/{{ img.basename }}.*
      {% for option in options -%}
      {{ option }}
      {% endfor -%}

      {{ caption }}  {# appropriate leading whitespace added beforehand #}
   {% endfor %}

"""

exception_template = """
.. only:: html

   [`source code <%(linkdir)s/%(basename)s.py>`__]

Exception occurred rendering plot.

"""

# the context of the plot for all directives specified with the
# :context: option
plot_context = dict()


class ImageFile:
    def __init__(self, basename, dirname):
        self.basename = basename
        self.dirname = dirname
        self.formats = []

    def filename(self, format):
        return os.path.join(self.dirname, f"{self.basename}.{format}")

    def filenames(self):
        return [self.filename(fmt) for fmt in self.formats]


def out_of_date(original, derived, includes=None):
    """
    Return whether *derived* is out-of-date relative to *original* or any of
    the RST files included in it using the RST include directive (*includes*).
    *derived* and *original* are full paths, and *includes* is optionally a
    list of full paths which may have been included in the *original*.
    """
    if not os.path.exists(derived):
        return True

    if includes is None:
        includes = []
    files_to_check = [original, *includes]

    def out_of_date_one(original, derived_mtime):
        return (os.path.exists(original) and
                derived_mtime < os.stat(original).st_mtime)

    derived_mtime = os.stat(derived).st_mtime
    return any(out_of_date_one(f, derived_mtime) for f in files_to_check)


class PlotError(RuntimeError):
    pass


def _run_code(code, code_path, ns=None, function_name=None):
    """
    Import a Python module from a path, and run the function given by
    name, if function_name is not None.
    """

    # Change the working directory to the directory of the example, so
    # it can get at its data files, if any.  Add its path to sys.path
    # so it can import any helper modules sitting beside it.
    pwd = os.getcwd()
    if setup.config.plot_working_directory is not None:
        try:
            os.chdir(setup.config.plot_working_directory)
        except OSError as err:
            raise OSError(f'{err}\n`plot_working_directory` option in '
                          f'Sphinx configuration file must be a valid '
                          f'directory path') from err
        except TypeError as err:
            raise TypeError(f'{err}\n`plot_working_directory` option in '
                            f'Sphinx configuration file must be a string or '
                            f'None') from err
    elif code_path is not None:
        dirname = os.path.abspath(os.path.dirname(code_path))
        os.chdir(dirname)

    with cbook._setattr_cm(
            sys, argv=[code_path], path=[os.getcwd(), *sys.path]), \
            contextlib.redirect_stdout(StringIO()):
        try:
            if ns is None:
                ns = {}
            if not ns:
                if setup.config.plot_pre_code is None:
                    exec('import numpy as np\n'
                         'from matplotlib import pyplot as plt\n', ns)
                else:
                    exec(str(setup.config.plot_pre_code), ns)
            if "__main__" in code:
                ns['__name__'] = '__main__'

            # Patch out non-interactive show() to avoid triggering a warning.
            with cbook._setattr_cm(FigureManagerBase, show=lambda self: None):
                exec(code, ns)
                if function_name is not None:
                    exec(function_name + "()", ns)

        except (Exception, SystemExit) as err:
            raise PlotError(traceback.format_exc()) from err
        finally:
            os.chdir(pwd)
    return ns


def clear_state(plot_rcparams, close=True):
    if close:
        plt.close('all')
    matplotlib.rc_file_defaults()
    matplotlib.rcParams.update(plot_rcparams)


def get_plot_formats(config):
    default_dpi = {'png': 80, 'hires.png': 200, 'pdf': 200}
    formats = []
    plot_formats = config.plot_formats
    for fmt in plot_formats:
        if isinstance(fmt, str):
            if ':' in fmt:
                suffix, dpi = fmt.split(':')
                formats.append((str(suffix), int(dpi)))
            else:
                formats.append((fmt, default_dpi.get(fmt, 80)))
        elif isinstance(fmt, (tuple, list)) and len(fmt) == 2:
            formats.append((str(fmt[0]), int(fmt[1])))
        else:
            raise PlotError('invalid image format "%r" in plot_formats' % fmt)
    return formats


def _parse_srcset(entries):
    """
    Parse srcset for multiples...
    """
    srcset = {}
    for entry in entries:
        entry = entry.strip()
        if len(entry) >= 2:
            mult = entry[:-1]
            srcset[float(mult)] = entry
        else:
            raise ExtensionError(f'srcset argument {entry!r} is invalid.')
    return srcset


def render_figures(code, code_path, output_dir, output_base, context,
                   function_name, config, context_reset=False,
                   close_figs=False,
                   code_includes=None):
    """
    Run a pyplot script and save the images in *output_dir*.

    Save the images under *output_dir* with file names derived from
    *output_base*
    """

    if function_name is not None:
        output_base = f'{output_base}_{function_name}'
    formats = get_plot_formats(config)

    # Try to determine if all images already exist

    is_doctest, code_pieces = _split_code_at_show(code, function_name)
    # Look for single-figure output files first
    img = ImageFile(output_base, output_dir)
    for format, dpi in formats:
        if context or out_of_date(code_path, img.filename(format),
                                  includes=code_includes):
            all_exists = False
            break
        img.formats.append(format)
    else:
        all_exists = True

    if all_exists:
        return [(code, [img])]

    # Then look for multi-figure output files
    results = []
    for i, code_piece in enumerate(code_pieces):
        images = []
        for j in itertools.count():
            if len(code_pieces) > 1:
                img = ImageFile('%s_%02d_%02d' % (output_base, i, j),
                                output_dir)
            else:
                img = ImageFile('%s_%02d' % (output_base, j), output_dir)
            for fmt, dpi in formats:
                if context or out_of_date(code_path, img.filename(fmt),
                                          includes=code_includes):
                    all_exists = False
                    break
                img.formats.append(fmt)

            # assume that if we have one, we have them all
            if not all_exists:
                all_exists = (j > 0)
                break
            images.append(img)
        if not all_exists:
            break
        results.append((code_piece, images))
    else:
        all_exists = True

    if all_exists:
        return results

    # We didn't find the files, so build them

    results = []
    ns = plot_context if context else {}

    if context_reset:
        clear_state(config.plot_rcparams)
        plot_context.clear()

    close_figs = not context or close_figs

    for i, code_piece in enumerate(code_pieces):

        if not context or config.plot_apply_rcparams:
            clear_state(config.plot_rcparams, close_figs)
        elif close_figs:
            plt.close('all')

        _run_code(doctest.script_from_examples(code_piece) if is_doctest
                  else code_piece,
                  code_path, ns, function_name)

        images = []
        fig_managers = _pylab_helpers.Gcf.get_all_fig_managers()
        for j, figman in enumerate(fig_managers):
            if len(fig_managers) == 1 and len(code_pieces) == 1:
                img = ImageFile(output_base, output_dir)
            elif len(code_pieces) == 1:
                img = ImageFile("%s_%02d" % (output_base, j), output_dir)
            else:
                img = ImageFile("%s_%02d_%02d" % (output_base, i, j),
                                output_dir)
            images.append(img)

            for fmt, dpi in formats:
                try:
                    figman.canvas.figure.savefig(img.filename(fmt), dpi=dpi)
                    if fmt == formats[0][0] and config.plot_srcset:
                        # save a 2x, 3x etc version of the default...
                        srcset = _parse_srcset(config.plot_srcset)
                        for mult, suffix in srcset.items():
                            fm = f'{suffix}.{fmt}'
                            img.formats.append(fm)
                            figman.canvas.figure.savefig(img.filename(fm),
                                                         dpi=int(dpi * mult))
                except Exception as err:
                    raise PlotError(traceback.format_exc()) from err
                img.formats.append(fmt)

        results.append((code_piece, images))

    if not context or config.plot_apply_rcparams:
        clear_state(config.plot_rcparams, close=not context)

    return results


def run(arguments, content, options, state_machine, state, lineno):
    document = state_machine.document
    config = document.settings.env.config
    nofigs = 'nofigs' in options

    if config.plot_srcset and setup.app.builder.name == 'singlehtml':
        raise ExtensionError(
            'plot_srcset option not compatible with single HTML writer')

    formats = get_plot_formats(config)
    default_fmt = formats[0][0]

    options.setdefault('include-source', config.plot_include_source)
    options.setdefault('show-source-link', config.plot_html_show_source_link)

    if 'class' in options:
        # classes are parsed into a list of string, and output by simply
        # printing the list, abusing the fact that RST guarantees to strip
        # non-conforming characters
        options['class'] = ['plot-directive'] + options['class']
    else:
        options.setdefault('class', ['plot-directive'])
    keep_context = 'context' in options
    context_opt = None if not keep_context else options['context']

    rst_file = document.attributes['source']
    rst_dir = os.path.dirname(rst_file)

    if len(arguments):
        if not config.plot_basedir:
            source_file_name = os.path.join(setup.app.builder.srcdir,
                                            directives.uri(arguments[0]))
        else:
            source_file_name = os.path.join(setup.confdir, config.plot_basedir,
                                            directives.uri(arguments[0]))
        # If there is content, it will be passed as a caption.
        caption = '\n'.join(content)

        # Enforce unambiguous use of captions.
        if "caption" in options:
            if caption:
                raise ValueError(
                    'Caption specified in both content and options.'
                    ' Please remove ambiguity.'
                )
            # Use caption option
            caption = options["caption"]

        # If the optional function name is provided, use it
        if len(arguments) == 2:
            function_name = arguments[1]
        else:
            function_name = None

        code = Path(source_file_name).read_text(encoding='utf-8')
        output_base = os.path.basename(source_file_name)
    else:
        source_file_name = rst_file
        code = textwrap.dedent("\n".join(map(str, content)))
        counter = document.attributes.get('_plot_counter', 0) + 1
        document.attributes['_plot_counter'] = counter
        base, ext = os.path.splitext(os.path.basename(source_file_name))
        output_base = '%s-%d.py' % (base, counter)
        function_name = None
        caption = options.get('caption', '')

    base, source_ext = os.path.splitext(output_base)
    if source_ext in ('.py', '.rst', '.txt'):
        output_base = base
    else:
        source_ext = ''

    # ensure that LaTeX includegraphics doesn't choke in foo.bar.pdf filenames
    output_base = output_base.replace('.', '-')

    # is it in doctest format?
    is_doctest = contains_doctest(code)
    if 'format' in options:
        if options['format'] == 'python':
            is_doctest = False
        else:
            is_doctest = True

    # determine output directory name fragment
    source_rel_name = relpath(source_file_name, setup.confdir)
    source_rel_dir = os.path.dirname(source_rel_name).lstrip(os.path.sep)

    # build_dir: where to place output files (temporarily)
    build_dir = os.path.join(os.path.dirname(setup.app.doctreedir),
                             'plot_directive',
                             source_rel_dir)
    # get rid of .. in paths, also changes pathsep
    # see note in Python docs for warning about symbolic links on Windows.
    # need to compare source and dest paths at end
    build_dir = os.path.normpath(build_dir)
    os.makedirs(build_dir, exist_ok=True)

    # how to link to files from the RST file
    try:
        build_dir_link = relpath(build_dir, rst_dir).replace(os.path.sep, '/')
    except ValueError:
        # on Windows, relpath raises ValueError when path and start are on
        # different mounts/drives
        build_dir_link = build_dir

    # get list of included rst files so that the output is updated when any
    # plots in the included files change. These attributes are modified by the
    # include directive (see the docutils.parsers.rst.directives.misc module).
    try:
        source_file_includes = [os.path.join(os.getcwd(), t[0])
                                for t in state.document.include_log]
    except AttributeError:
        # the document.include_log attribute only exists in docutils >=0.17,
        # before that we need to inspect the state machine
        possible_sources = {os.path.join(setup.confdir, t[0])
                            for t in state_machine.input_lines.items}
        source_file_includes = [f for f in possible_sources
                                if os.path.isfile(f)]
    # remove the source file itself from the includes
    try:
        source_file_includes.remove(source_file_name)
    except ValueError:
        pass

    # save script (if necessary)
    if options['show-source-link']:
        Path(build_dir, output_base + source_ext).write_text(
            doctest.script_from_examples(code)
            if source_file_name == rst_file and is_doctest
            else code,
            encoding='utf-8')

    # make figures
    try:
        results = render_figures(code=code,
                                 code_path=source_file_name,
                                 output_dir=build_dir,
                                 output_base=output_base,
                                 context=keep_context,
                                 function_name=function_name,
                                 config=config,
                                 context_reset=context_opt == 'reset',
                                 close_figs=context_opt == 'close-figs',
                                 code_includes=source_file_includes)
        errors = []
    except PlotError as err:
        reporter = state.memo.reporter
        sm = reporter.system_message(
            2, "Exception occurred in plotting {}\n from {}:\n{}".format(
                output_base, source_file_name, err),
            line=lineno)
        results = [(code, [])]
        errors = [sm]

    # Properly indent the caption
    if caption and config.plot_srcset:
        caption = ':caption: ' + caption.replace('\n', ' ')
    elif caption:
        caption = '\n' + '\n'.join('      ' + line.strip()
                                   for line in caption.split('\n'))
    # generate output restructuredtext
    total_lines = []
    for j, (code_piece, images) in enumerate(results):
        if options['include-source']:
            if is_doctest:
                lines = ['', *code_piece.splitlines()]
            else:
                lines = ['.. code-block:: python', '',
                         *textwrap.indent(code_piece, '    ').splitlines()]
            source_code = "\n".join(lines)
        else:
            source_code = ""

        if nofigs:
            images = []

        if 'alt' in options:
            options['alt'] = options['alt'].replace('\n', ' ')

        opts = [
            f':{key}: {val}' for key, val in options.items()
            if key in ('alt', 'height', 'width', 'scale', 'align', 'class')]

        # Not-None src_name signals the need for a source download in the
        # generated html
        if j == 0 and options['show-source-link']:
            src_name = output_base + source_ext
        else:
            src_name = None
        if config.plot_srcset:
            srcset = [*_parse_srcset(config.plot_srcset).values()]
            template = TEMPLATE_SRCSET
        else:
            srcset = None
            template = TEMPLATE

        result = jinja2.Template(config.plot_template or template).render(
            default_fmt=default_fmt,
            build_dir=build_dir_link,
            src_name=src_name,
            multi_image=len(images) > 1,
            options=opts,
            srcset=srcset,
            images=images,
            source_code=source_code,
            html_show_formats=config.plot_html_show_formats and len(images),
            caption=caption)
        total_lines.extend(result.split("\n"))
        total_lines.extend("\n")

    if total_lines:
        state_machine.insert_input(total_lines, source=source_file_name)

    return errors

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_locator.py ===
# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import pathlib
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from playwright._impl._api_structures import (
    AriaRole,
    FilePayload,
    FloatRect,
    FrameExpectOptions,
    FrameExpectResult,
    Position,
)
from playwright._impl._element_handle import ElementHandle
from playwright._impl._helper import (
    Error,
    KeyboardModifier,
    MouseButton,
    locals_to_params,
    monotonic_time,
    to_impl,
)
from playwright._impl._js_handle import Serializable, parse_value, serialize_argument
from playwright._impl._str_utils import (
    escape_for_attribute_selector,
    escape_for_text_selector,
)

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._frame import Frame
    from playwright._impl._js_handle import JSHandle
    from playwright._impl._page import Page

T = TypeVar("T")


class Locator:
    def __init__(
        self,
        frame: "Frame",
        selector: str,
        has_text: Union[str, Pattern[str]] = None,
        has_not_text: Union[str, Pattern[str]] = None,
        has: "Locator" = None,
        has_not: "Locator" = None,
        visible: bool = None,
    ) -> None:
        self._frame = frame
        self._selector = selector
        self._loop = frame._loop
        self._dispatcher_fiber = frame._connection._dispatcher_fiber

        if has_text:
            self._selector += f" >> internal:has-text={escape_for_text_selector(has_text, exact=False)}"

        if has:
            if has._frame != frame:
                raise Error('Inner "has" locator must belong to the same frame.')
            self._selector += " >> internal:has=" + json.dumps(
                has._selector, ensure_ascii=False
            )

        if has_not_text:
            self._selector += f" >> internal:has-not-text={escape_for_text_selector(has_not_text, exact=False)}"

        if has_not:
            locator = has_not
            if locator._frame != frame:
                raise Error('Inner "has_not" locator must belong to the same frame.')
            self._selector += " >> internal:has-not=" + json.dumps(locator._selector)

        if visible is not None:
            self._selector += f" >> visible={bool_to_js_bool(visible)}"

    def __repr__(self) -> str:
        return f"<Locator frame={self._frame!r} selector={self._selector!r}>"

    async def _with_element(
        self,
        task: Callable[[ElementHandle, float], Awaitable[T]],
        timeout: float = None,
    ) -> T:
        timeout = self._frame.page._timeout_settings.timeout(timeout)
        deadline = (monotonic_time() + timeout) if timeout else 0
        handle = await self.element_handle(timeout=timeout)
        if not handle:
            raise Error(f"Could not resolve {self._selector} to DOM Element")
        try:
            return await task(
                handle,
                (deadline - monotonic_time()) if deadline else 0,
            )
        finally:
            await handle.dispose()

    def _equals(self, locator: "Locator") -> bool:
        return self._frame == locator._frame and self._selector == locator._selector

    @property
    def page(self) -> "Page":
        return self._frame.page

    async def bounding_box(self, timeout: float = None) -> Optional[FloatRect]:
        return await self._with_element(
            lambda h, _: h.bounding_box(),
            timeout,
        )

    async def check(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.check(self._selector, strict=True, **params)

    async def click(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.click(self._selector, strict=True, **params)

    async def dblclick(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.dblclick(self._selector, strict=True, **params)

    async def dispatch_event(
        self,
        type: str,
        eventInit: Dict = None,
        timeout: float = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.dispatch_event(self._selector, strict=True, **params)

    async def evaluate(
        self, expression: str, arg: Serializable = None, timeout: float = None
    ) -> Any:
        return await self._with_element(
            lambda h, _: h.evaluate(expression, arg),
            timeout,
        )

    async def evaluate_all(self, expression: str, arg: Serializable = None) -> Any:
        params = locals_to_params(locals())
        return await self._frame.eval_on_selector_all(self._selector, **params)

    async def evaluate_handle(
        self, expression: str, arg: Serializable = None, timeout: float = None
    ) -> "JSHandle":
        return await self._with_element(
            lambda h, _: h.evaluate_handle(expression, arg), timeout
        )

    async def fill(
        self,
        value: str,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.fill(self._selector, strict=True, **params)

    async def clear(
        self,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
    ) -> None:
        await self.fill("", timeout=timeout, force=force)

    def locator(
        self,
        selectorOrLocator: Union[str, "Locator"],
        hasText: Union[str, Pattern[str]] = None,
        hasNotText: Union[str, Pattern[str]] = None,
        has: "Locator" = None,
        hasNot: "Locator" = None,
    ) -> "Locator":
        if isinstance(selectorOrLocator, str):
            return Locator(
                self._frame,
                f"{self._selector} >> {selectorOrLocator}",
                has_text=hasText,
                has_not_text=hasNotText,
                has_not=hasNot,
                has=has,
            )
        selectorOrLocator = to_impl(selectorOrLocator)
        if selectorOrLocator._frame != self._frame:
            raise Error("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            f"{self._selector} >> internal:chain={json.dumps(selectorOrLocator._selector)}",
            has_text=hasText,
            has_not_text=hasNotText,
            has_not=hasNot,
            has=has,
        )

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_alt_text_selector(text, exact=exact))

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_label_selector(text, exact=exact))

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_placeholder_selector(text, exact=exact))

    def get_by_role(
        self,
        role: AriaRole,
        checked: bool = None,
        disabled: bool = None,
        expanded: bool = None,
        includeHidden: bool = None,
        level: int = None,
        name: Union[str, Pattern[str]] = None,
        pressed: bool = None,
        selected: bool = None,
        exact: bool = None,
    ) -> "Locator":
        return self.locator(
            get_by_role_selector(
                role,
                checked=checked,
                disabled=disabled,
                expanded=expanded,
                includeHidden=includeHidden,
                level=level,
                name=name,
                pressed=pressed,
                selected=selected,
                exact=exact,
            )
        )

    def get_by_test_id(self, testId: Union[str, Pattern[str]]) -> "Locator":
        return self.locator(get_by_test_id_selector(test_id_attribute_name(), testId))

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_text_selector(text, exact=exact))

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_title_selector(text, exact=exact))

    def frame_locator(self, selector: str) -> "FrameLocator":
        return FrameLocator(self._frame, self._selector + " >> " + selector)

    async def element_handle(
        self,
        timeout: float = None,
    ) -> ElementHandle:
        params = locals_to_params(locals())
        handle = await self._frame.wait_for_selector(
            self._selector, strict=True, state="attached", **params
        )
        assert handle
        return handle

    async def element_handles(self) -> List[ElementHandle]:
        return await self._frame.query_selector_all(self._selector)

    @property
    def first(self) -> "Locator":
        return Locator(self._frame, f"{self._selector} >> nth=0")

    @property
    def last(self) -> "Locator":
        return Locator(self._frame, f"{self._selector} >> nth=-1")

    def nth(self, index: int) -> "Locator":
        return Locator(self._frame, f"{self._selector} >> nth={index}")

    @property
    def content_frame(self) -> "FrameLocator":
        return FrameLocator(self._frame, self._selector)

    def filter(
        self,
        hasText: Union[str, Pattern[str]] = None,
        hasNotText: Union[str, Pattern[str]] = None,
        has: "Locator" = None,
        hasNot: "Locator" = None,
        visible: bool = None,
    ) -> "Locator":
        return Locator(
            self._frame,
            self._selector,
            has_text=hasText,
            has_not_text=hasNotText,
            has=has,
            has_not=hasNot,
            visible=visible,
        )

    def or_(self, locator: "Locator") -> "Locator":
        if locator._frame != self._frame:
            raise Error("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            self._selector + " >> internal:or=" + json.dumps(locator._selector),
        )

    def and_(self, locator: "Locator") -> "Locator":
        if locator._frame != self._frame:
            raise Error("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            self._selector + " >> internal:and=" + json.dumps(locator._selector),
        )

    async def focus(self, timeout: float = None) -> None:
        params = locals_to_params(locals())
        return await self._frame.focus(self._selector, strict=True, **params)

    async def blur(self, timeout: float = None) -> None:
        await self._frame._channel.send(
            "blur",
            {
                "selector": self._selector,
                "strict": True,
                **locals_to_params(locals()),
            },
        )

    async def all(
        self,
    ) -> List["Locator"]:
        result = []
        for index in range(await self.count()):
            result.append(self.nth(index))
        return result

    async def count(
        self,
    ) -> int:
        return await self._frame._query_count(self._selector)

    async def drag_to(
        self,
        target: "Locator",
        force: bool = None,
        noWaitAfter: bool = None,
        timeout: float = None,
        trial: bool = None,
        sourcePosition: Position = None,
        targetPosition: Position = None,
    ) -> None:
        params = locals_to_params(locals())
        del params["target"]
        return await self._frame.drag_and_drop(
            self._selector, target._selector, strict=True, **params
        )

    async def get_attribute(self, name: str, timeout: float = None) -> Optional[str]:
        params = locals_to_params(locals())
        return await self._frame.get_attribute(
            self._selector,
            strict=True,
            **params,
        )

    async def hover(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.hover(
            self._selector,
            strict=True,
            **params,
        )

    async def inner_html(self, timeout: float = None) -> str:
        params = locals_to_params(locals())
        return await self._frame.inner_html(
            self._selector,
            strict=True,
            **params,
        )

    async def inner_text(self, timeout: float = None) -> str:
        params = locals_to_params(locals())
        return await self._frame.inner_text(
            self._selector,
            strict=True,
            **params,
        )

    async def input_value(self, timeout: float = None) -> str:
        params = locals_to_params(locals())
        return await self._frame.input_value(
            self._selector,
            strict=True,
            **params,
        )

    async def is_checked(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_checked(
            self._selector,
            strict=True,
            **params,
        )

    async def is_disabled(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_disabled(
            self._selector,
            strict=True,
            **params,
        )

    async def is_editable(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_editable(
            self._selector,
            strict=True,
            **params,
        )

    async def is_enabled(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_enabled(
            self._selector,
            strict=True,
            **params,
        )

    async def is_hidden(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_hidden(
            self._selector,
            strict=True,
            **params,
        )

    async def is_visible(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_visible(
            self._selector,
            strict=True,
            **params,
        )

    async def press(
        self,
        key: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.press(self._selector, strict=True, **params)

    async def screenshot(
        self,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: Union[str, pathlib.Path] = None,
        quality: int = None,
        omitBackground: bool = None,
        animations: Literal["allow", "disabled"] = None,
        caret: Literal["hide", "initial"] = None,
        scale: Literal["css", "device"] = None,
        mask: Sequence["Locator"] = None,
        maskColor: str = None,
        style: str = None,
    ) -> bytes:
        params = locals_to_params(locals())
        return await self._with_element(
            lambda h, timeout: h.screenshot(
                **{**params, "timeout": timeout},
            ),
        )

    async def aria_snapshot(self, timeout: float = None, ref: bool = None) -> str:
        return await self._frame._channel.send(
            "ariaSnapshot",
            {
                "selector": self._selector,
                **locals_to_params(locals()),
            },
        )

    async def scroll_into_view_if_needed(
        self,
        timeout: float = None,
    ) -> None:
        return await self._with_element(
            lambda h, timeout: h.scroll_into_view_if_needed(timeout=timeout),
            timeout,
        )

    async def select_option(
        self,
        value: Union[str, Sequence[str]] = None,
        index: Union[int, Sequence[int]] = None,
        label: Union[str, Sequence[str]] = None,
        element: Union["ElementHandle", Sequence["ElementHandle"]] = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
    ) -> List[str]:
        params = locals_to_params(locals())
        return await self._frame.select_option(
            self._selector,
            strict=True,
            **params,
        )

    async def select_text(self, force: bool = None, timeout: float = None) -> None:
        params = locals_to_params(locals())
        return await self._with_element(
            lambda h, timeout: h.select_text(**{**params, "timeout": timeout}),
            timeout,
        )

    async def set_input_files(
        self,
        files: Union[
            str,
            pathlib.Path,
            FilePayload,
            Sequence[Union[str, pathlib.Path]],
            Sequence[FilePayload],
        ],
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.set_input_files(
            self._selector,
            strict=True,
            **params,
        )

    async def tap(
        self,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.tap(
            self._selector,
            strict=True,
            **params,
        )

    async def text_content(self, timeout: float = None) -> Optional[str]:
        params = locals_to_params(locals())
        return await self._frame.text_content(
            self._selector,
            strict=True,
            **params,
        )

    async def type(
        self,
        text: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.type(
            self._selector,
            strict=True,
            **params,
        )

    async def press_sequentially(
        self,
        text: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self.type(text, delay=delay, timeout=timeout)

    async def uncheck(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.uncheck(
            self._selector,
            strict=True,
            **params,
        )

    async def all_inner_texts(
        self,
    ) -> List[str]:
        return await self._frame.eval_on_selector_all(
            self._selector, "ee => ee.map(e => e.innerText)"
        )

    async def all_text_contents(
        self,
    ) -> List[str]:
        return await self._frame.eval_on_selector_all(
            self._selector, "ee => ee.map(e => e.textContent || '')"
        )

    async def wait_for(
        self,
        timeout: float = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
    ) -> None:
        await self._frame.wait_for_selector(
            self._selector, strict=True, timeout=timeout, state=state
        )

    async def set_checked(
        self,
        checked: bool,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        if checked:
            await self.check(
                position=position,
                timeout=timeout,
                force=force,
                trial=trial,
            )
        else:
            await self.uncheck(
                position=position,
                timeout=timeout,
                force=force,
                trial=trial,
            )

    async def _expect(
        self, expression: str, options: FrameExpectOptions
    ) -> FrameExpectResult:
        if "expectedValue" in options:
            options["expectedValue"] = serialize_argument(options["expectedValue"])
        result = await self._frame._channel.send_return_as_dict(
            "expect",
            {
                "selector": self._selector,
                "expression": expression,
                **options,
            },
        )
        if result.get("received"):
            result["received"] = parse_value(result["received"])
        return result

    async def highlight(self) -> None:
        await self._frame._highlight(self._selector)


class FrameLocator:
    def __init__(self, frame: "Frame", frame_selector: str) -> None:
        self._frame = frame
        self._loop = frame._loop
        self._dispatcher_fiber = frame._connection._dispatcher_fiber
        self._frame_selector = frame_selector

    def locator(
        self,
        selectorOrLocator: Union["Locator", str],
        hasText: Union[str, Pattern[str]] = None,
        hasNotText: Union[str, Pattern[str]] = None,
        has: Locator = None,
        hasNot: Locator = None,
    ) -> Locator:
        if isinstance(selectorOrLocator, str):
            return Locator(
                self._frame,
                f"{self._frame_selector} >> internal:control=enter-frame >> {selectorOrLocator}",
                has_text=hasText,
                has_not_text=hasNotText,
                has=has,
                has_not=hasNot,
            )
        selectorOrLocator = to_impl(selectorOrLocator)
        if selectorOrLocator._frame != self._frame:
            raise ValueError("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            f"{self._frame_selector} >> internal:control=enter-frame >> {selectorOrLocator._selector}",
            has_text=hasText,
            has_not_text=hasNotText,
            has=has,
            has_not=hasNot,
        )

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_alt_text_selector(text, exact=exact))

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_label_selector(text, exact=exact))

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_placeholder_selector(text, exact=exact))

    def get_by_role(
        self,
        role: AriaRole,
        checked: bool = None,
        disabled: bool = None,
        expanded: bool = None,
        includeHidden: bool = None,
        level: int = None,
        name: Union[str, Pattern[str]] = None,
        pressed: bool = None,
        selected: bool = None,
        exact: bool = None,
    ) -> "Locator":
        return self.locator(
            get_by_role_selector(
                role,
                checked=checked,
                disabled=disabled,
                expanded=expanded,
                includeHidden=includeHidden,
                level=level,
                name=name,
                pressed=pressed,
                selected=selected,
                exact=exact,
            )
        )

    def get_by_test_id(self, testId: Union[str, Pattern[str]]) -> "Locator":
        return self.locator(get_by_test_id_selector(test_id_attribute_name(), testId))

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_text_selector(text, exact=exact))

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_title_selector(text, exact=exact))

    def frame_locator(self, selector: str) -> "FrameLocator":
        return FrameLocator(
            self._frame,
            f"{self._frame_selector} >> internal:control=enter-frame >> {selector}",
        )

    @property
    def first(self) -> "FrameLocator":
        return FrameLocator(self._frame, f"{self._frame_selector} >> nth=0")

    @property
    def last(self) -> "FrameLocator":
        return FrameLocator(self._frame, f"{self._frame_selector} >> nth=-1")

    @property
    def owner(self) -> "Locator":
        return Locator(self._frame, self._frame_selector)

    def nth(self, index: int) -> "FrameLocator":
        return FrameLocator(self._frame, f"{self._frame_selector} >> nth={index}")

    def __repr__(self) -> str:
        return f"<FrameLocator frame={self._frame!r} selector={self._frame_selector!r}>"


_test_id_attribute_name: str = "data-testid"


def test_id_attribute_name() -> str:
    return _test_id_attribute_name


def set_test_id_attribute_name(attribute_name: str) -> None:
    global _test_id_attribute_name
    _test_id_attribute_name = attribute_name


def get_by_test_id_selector(
    test_id_attribute_name: str, test_id: Union[str, Pattern[str]]
) -> str:
    return f"internal:testid=[{test_id_attribute_name}={escape_for_attribute_selector(test_id, True)}]"


def get_by_attribute_text_selector(
    attr_name: str, text: Union[str, Pattern[str]], exact: bool = None
) -> str:
    return f"internal:attr=[{attr_name}={escape_for_attribute_selector(text, exact=exact)}]"


def get_by_label_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return "internal:label=" + escape_for_text_selector(text, exact=exact)


def get_by_alt_text_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return get_by_attribute_text_selector("alt", text, exact=exact)


def get_by_title_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return get_by_attribute_text_selector("title", text, exact=exact)


def get_by_placeholder_selector(
    text: Union[str, Pattern[str]], exact: bool = None
) -> str:
    return get_by_attribute_text_selector("placeholder", text, exact=exact)


def get_by_text_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return "internal:text=" + escape_for_text_selector(text, exact=exact)


def bool_to_js_bool(value: bool) -> str:
    return "true" if value else "false"


def get_by_role_selector(
    role: AriaRole,
    checked: bool = None,
    disabled: bool = None,
    expanded: bool = None,
    includeHidden: bool = None,
    level: int = None,
    name: Union[str, Pattern[str]] = None,
    pressed: bool = None,
    selected: bool = None,
    exact: bool = None,
) -> str:
    props: List[Tuple[str, str]] = []
    if checked is not None:
        props.append(("checked", bool_to_js_bool(checked)))
    if disabled is not None:
        props.append(("disabled", bool_to_js_bool(disabled)))
    if selected is not None:
        props.append(("selected", bool_to_js_bool(selected)))
    if expanded is not None:
        props.append(("expanded", bool_to_js_bool(expanded)))
    if includeHidden is not None:
        props.append(("include-hidden", bool_to_js_bool(includeHidden)))
    if level is not None:
        props.append(("level", str(level)))
    if name is not None:
        props.append(
            (
                "name",
                escape_for_attribute_selector(name, exact=exact),
            )
        )
    if pressed is not None:
        props.append(("pressed", bool_to_js_bool(pressed)))
    props_str = "".join([f"[{t[0]}={t[1]}]" for t in props])
    return f"internal:role={role}{props_str}"

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\haxe.py ===
"""
    pygments.lexers.haxe
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for Haxe and related stuff.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import ExtendedRegexLexer, RegexLexer, include, bygroups, \
    default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Whitespace

__all__ = ['HaxeLexer', 'HxmlLexer']


class HaxeLexer(ExtendedRegexLexer):
    """
    For Haxe source code.
    """

    name = 'Haxe'
    url = 'http://haxe.org/'
    aliases = ['haxe', 'hxsl', 'hx']
    filenames = ['*.hx', '*.hxsl']
    mimetypes = ['text/haxe', 'text/x-haxe', 'text/x-hx']
    version_added = '1.3'

    # keywords extracted from lexer.mll in the haxe compiler source
    keyword = (r'(?:function|class|static|var|if|else|while|do|for|'
               r'break|return|continue|extends|implements|import|'
               r'switch|case|default|public|private|try|untyped|'
               r'catch|new|this|throw|extern|enum|in|interface|'
               r'cast|override|dynamic|typedef|package|'
               r'inline|using|null|true|false|abstract)\b')

    # idtype in lexer.mll
    typeid = r'_*[A-Z]\w*'

    # combined ident and dollar and idtype
    ident = r'(?:_*[a-z]\w*|_+[0-9]\w*|' + typeid + r'|_+|\$\w+)'

    binop = (r'(?:%=|&=|\|=|\^=|\+=|\-=|\*=|/=|<<=|>\s*>\s*=|>\s*>\s*>\s*=|==|'
             r'!=|<=|>\s*=|&&|\|\||<<|>>>|>\s*>|\.\.\.|<|>|%|&|\||\^|\+|\*|'
             r'/|\-|=>|=)')

    # ident except keywords
    ident_no_keyword = r'(?!' + keyword + ')' + ident

    flags = re.DOTALL | re.MULTILINE

    preproc_stack = []

    def preproc_callback(self, match, ctx):
        proc = match.group(2)

        if proc == 'if':
            # store the current stack
            self.preproc_stack.append(ctx.stack[:])
        elif proc in ['else', 'elseif']:
            # restore the stack back to right before #if
            if self.preproc_stack:
                ctx.stack = self.preproc_stack[-1][:]
        elif proc == 'end':
            # remove the saved stack of previous #if
            if self.preproc_stack:
                self.preproc_stack.pop()

        # #if and #elseif should follow by an expr
        if proc in ['if', 'elseif']:
            ctx.stack.append('preproc-expr')

        # #error can be optionally follow by the error msg
        if proc in ['error']:
            ctx.stack.append('preproc-error')

        yield match.start(), Comment.Preproc, '#' + proc
        ctx.pos = match.end()

    tokens = {
        'root': [
            include('spaces'),
            include('meta'),
            (r'(?:package)\b', Keyword.Namespace, ('semicolon', 'package')),
            (r'(?:import)\b', Keyword.Namespace, ('semicolon', 'import')),
            (r'(?:using)\b', Keyword.Namespace, ('semicolon', 'using')),
            (r'(?:extern|private)\b', Keyword.Declaration),
            (r'(?:abstract)\b', Keyword.Declaration, 'abstract'),
            (r'(?:class|interface)\b', Keyword.Declaration, 'class'),
            (r'(?:enum)\b', Keyword.Declaration, 'enum'),
            (r'(?:typedef)\b', Keyword.Declaration, 'typedef'),

            # top-level expression
            # although it is not supported in haxe, but it is common to write
            # expression in web pages the positive lookahead here is to prevent
            # an infinite loop at the EOF
            (r'(?=.)', Text, 'expr-statement'),
        ],

        # space/tab/comment/preproc
        'spaces': [
            (r'\s+', Whitespace),
            (r'//[^\n\r]*', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'(#)(if|elseif|else|end|error)\b', preproc_callback),
        ],

        'string-single-interpol': [
            (r'\$\{', String.Interpol, ('string-interpol-close', 'expr')),
            (r'\$\$', String.Escape),
            (r'\$(?=' + ident + ')', String.Interpol, 'ident'),
            include('string-single'),
        ],

        'string-single': [
            (r"'", String.Single, '#pop'),
            (r'\\.', String.Escape),
            (r'.', String.Single),
        ],

        'string-double': [
            (r'"', String.Double, '#pop'),
            (r'\\.', String.Escape),
            (r'.', String.Double),
        ],

        'string-interpol-close': [
            (r'\$'+ident, String.Interpol),
            (r'\}', String.Interpol, '#pop'),
        ],

        'package': [
            include('spaces'),
            (ident, Name.Namespace),
            (r'\.', Punctuation, 'import-ident'),
            default('#pop'),
        ],

        'import': [
            include('spaces'),
            (ident, Name.Namespace),
            (r'\*', Keyword),  # wildcard import
            (r'\.', Punctuation, 'import-ident'),
            (r'in', Keyword.Namespace, 'ident'),
            default('#pop'),
        ],

        'import-ident': [
            include('spaces'),
            (r'\*', Keyword, '#pop'),  # wildcard import
            (ident, Name.Namespace, '#pop'),
        ],

        'using': [
            include('spaces'),
            (ident, Name.Namespace),
            (r'\.', Punctuation, 'import-ident'),
            default('#pop'),
        ],

        'preproc-error': [
            (r'\s+', Whitespace),
            (r"'", String.Single, ('#pop', 'string-single')),
            (r'"', String.Double, ('#pop', 'string-double')),
            default('#pop'),
        ],

        'preproc-expr': [
            (r'\s+', Whitespace),
            (r'\!', Comment.Preproc),
            (r'\(', Comment.Preproc, ('#pop', 'preproc-parenthesis')),

            (ident, Comment.Preproc, '#pop'),

            # Float
            (r'\.[0-9]+', Number.Float),
            (r'[0-9]+[eE][+\-]?[0-9]+', Number.Float),
            (r'[0-9]+\.[0-9]*[eE][+\-]?[0-9]+', Number.Float),
            (r'[0-9]+\.[0-9]+', Number.Float),
            (r'[0-9]+\.(?!' + ident + r'|\.\.)', Number.Float),

            # Int
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),

            # String
            (r"'", String.Single, ('#pop', 'string-single')),
            (r'"', String.Double, ('#pop', 'string-double')),
        ],

        'preproc-parenthesis': [
            (r'\s+', Whitespace),
            (r'\)', Comment.Preproc, '#pop'),
            default('preproc-expr-in-parenthesis'),
        ],

        'preproc-expr-chain': [
            (r'\s+', Whitespace),
            (binop, Comment.Preproc, ('#pop', 'preproc-expr-in-parenthesis')),
            default('#pop'),
        ],

        # same as 'preproc-expr' but able to chain 'preproc-expr-chain'
        'preproc-expr-in-parenthesis': [
            (r'\s+', Whitespace),
            (r'\!', Comment.Preproc),
            (r'\(', Comment.Preproc,
             ('#pop', 'preproc-expr-chain', 'preproc-parenthesis')),

            (ident, Comment.Preproc, ('#pop', 'preproc-expr-chain')),

            # Float
            (r'\.[0-9]+', Number.Float, ('#pop', 'preproc-expr-chain')),
            (r'[0-9]+[eE][+\-]?[0-9]+', Number.Float, ('#pop', 'preproc-expr-chain')),
            (r'[0-9]+\.[0-9]*[eE][+\-]?[0-9]+', Number.Float, ('#pop', 'preproc-expr-chain')),
            (r'[0-9]+\.[0-9]+', Number.Float, ('#pop', 'preproc-expr-chain')),
            (r'[0-9]+\.(?!' + ident + r'|\.\.)', Number.Float, ('#pop', 'preproc-expr-chain')),

            # Int
            (r'0x[0-9a-fA-F]+', Number.Hex, ('#pop', 'preproc-expr-chain')),
            (r'[0-9]+', Number.Integer, ('#pop', 'preproc-expr-chain')),

            # String
            (r"'", String.Single,
             ('#pop', 'preproc-expr-chain', 'string-single')),
            (r'"', String.Double,
             ('#pop', 'preproc-expr-chain', 'string-double')),
        ],

        'abstract': [
            include('spaces'),
            default(('#pop', 'abstract-body', 'abstract-relation',
                    'abstract-opaque', 'type-param-constraint', 'type-name')),
        ],

        'abstract-body': [
            include('spaces'),
            (r'\{', Punctuation, ('#pop', 'class-body')),
        ],

        'abstract-opaque': [
            include('spaces'),
            (r'\(', Punctuation, ('#pop', 'parenthesis-close', 'type')),
            default('#pop'),
        ],

        'abstract-relation': [
            include('spaces'),
            (r'(?:to|from)', Keyword.Declaration, 'type'),
            (r',', Punctuation),
            default('#pop'),
        ],

        'meta': [
            include('spaces'),
            (r'@', Name.Decorator, ('meta-body', 'meta-ident', 'meta-colon')),
        ],

        # optional colon
        'meta-colon': [
            include('spaces'),
            (r':', Name.Decorator, '#pop'),
            default('#pop'),
        ],

        # same as 'ident' but set token as Name.Decorator instead of Name
        'meta-ident': [
            include('spaces'),
            (ident, Name.Decorator, '#pop'),
        ],

        'meta-body': [
            include('spaces'),
            (r'\(', Name.Decorator, ('#pop', 'meta-call')),
            default('#pop'),
        ],

        'meta-call': [
            include('spaces'),
            (r'\)', Name.Decorator, '#pop'),
            default(('#pop', 'meta-call-sep', 'expr')),
        ],

        'meta-call-sep': [
            include('spaces'),
            (r'\)', Name.Decorator, '#pop'),
            (r',', Punctuation, ('#pop', 'meta-call')),
        ],

        'typedef': [
            include('spaces'),
            default(('#pop', 'typedef-body', 'type-param-constraint',
                     'type-name')),
        ],

        'typedef-body': [
            include('spaces'),
            (r'=', Operator, ('#pop', 'optional-semicolon', 'type')),
        ],

        'enum': [
            include('spaces'),
            default(('#pop', 'enum-body', 'bracket-open',
                     'type-param-constraint', 'type-name')),
        ],

        'enum-body': [
            include('spaces'),
            include('meta'),
            (r'\}', Punctuation, '#pop'),
            (ident_no_keyword, Name, ('enum-member', 'type-param-constraint')),
        ],

        'enum-member': [
            include('spaces'),
            (r'\(', Punctuation,
             ('#pop', 'semicolon', 'flag', 'function-param')),
            default(('#pop', 'semicolon', 'flag')),
        ],

        'class': [
            include('spaces'),
            default(('#pop', 'class-body', 'bracket-open', 'extends',
                     'type-param-constraint', 'type-name')),
        ],

        'extends': [
            include('spaces'),
            (r'(?:extends|implements)\b', Keyword.Declaration, 'type'),
            (r',', Punctuation),  # the comma is made optional here, since haxe2
                                  # requires the comma but haxe3 does not allow it
            default('#pop'),
        ],

        'bracket-open': [
            include('spaces'),
            (r'\{', Punctuation, '#pop'),
        ],

        'bracket-close': [
            include('spaces'),
            (r'\}', Punctuation, '#pop'),
        ],

        'class-body': [
            include('spaces'),
            include('meta'),
            (r'\}', Punctuation, '#pop'),
            (r'(?:static|public|private|override|dynamic|inline|macro)\b',
             Keyword.Declaration),
            default('class-member'),
        ],

        'class-member': [
            include('spaces'),
            (r'(var)\b', Keyword.Declaration,
             ('#pop', 'optional-semicolon', 'var')),
            (r'(function)\b', Keyword.Declaration,
             ('#pop', 'optional-semicolon', 'class-method')),
        ],

        # local function, anonymous or not
        'function-local': [
            include('spaces'),
            (ident_no_keyword, Name.Function,
             ('#pop', 'optional-expr', 'flag', 'function-param',
              'parenthesis-open', 'type-param-constraint')),
            default(('#pop', 'optional-expr', 'flag', 'function-param',
                     'parenthesis-open', 'type-param-constraint')),
        ],

        'optional-expr': [
            include('spaces'),
            include('expr'),
            default('#pop'),
        ],

        'class-method': [
            include('spaces'),
            (ident, Name.Function, ('#pop', 'optional-expr', 'flag',
                                    'function-param', 'parenthesis-open',
                                    'type-param-constraint')),
        ],

        # function arguments
        'function-param': [
            include('spaces'),
            (r'\)', Punctuation, '#pop'),
            (r'\?', Punctuation),
            (ident_no_keyword, Name,
             ('#pop', 'function-param-sep', 'assign', 'flag')),
        ],

        'function-param-sep': [
            include('spaces'),
            (r'\)', Punctuation, '#pop'),
            (r',', Punctuation, ('#pop', 'function-param')),
        ],

        'prop-get-set': [
            include('spaces'),
            (r'\(', Punctuation, ('#pop', 'parenthesis-close',
                                  'prop-get-set-opt', 'comma', 'prop-get-set-opt')),
            default('#pop'),
        ],

        'prop-get-set-opt': [
            include('spaces'),
            (r'(?:default|null|never|dynamic|get|set)\b', Keyword, '#pop'),
            (ident_no_keyword, Text, '#pop'),  # custom getter/setter
        ],

        'expr-statement': [
            include('spaces'),
            # makes semicolon optional here, just to avoid checking the last
            # one is bracket or not.
            default(('#pop', 'optional-semicolon', 'expr')),
        ],

        'expr': [
            include('spaces'),
            (r'@', Name.Decorator, ('#pop', 'optional-expr', 'meta-body',
                                    'meta-ident', 'meta-colon')),
            (r'(?:\+\+|\-\-|~(?!/)|!|\-)', Operator),
            (r'\(', Punctuation, ('#pop', 'expr-chain', 'parenthesis')),
            (r'(?:static|public|private|override|dynamic|inline)\b',
             Keyword.Declaration),
            (r'(?:function)\b', Keyword.Declaration, ('#pop', 'expr-chain',
                                                      'function-local')),
            (r'\{', Punctuation, ('#pop', 'expr-chain', 'bracket')),
            (r'(?:true|false|null)\b', Keyword.Constant, ('#pop', 'expr-chain')),
            (r'(?:this)\b', Keyword, ('#pop', 'expr-chain')),
            (r'(?:cast)\b', Keyword, ('#pop', 'expr-chain', 'cast')),
            (r'(?:try)\b', Keyword, ('#pop', 'catch', 'expr')),
            (r'(?:var)\b', Keyword.Declaration, ('#pop', 'var')),
            (r'(?:new)\b', Keyword, ('#pop', 'expr-chain', 'new')),
            (r'(?:switch)\b', Keyword, ('#pop', 'switch')),
            (r'(?:if)\b', Keyword, ('#pop', 'if')),
            (r'(?:do)\b', Keyword, ('#pop', 'do')),
            (r'(?:while)\b', Keyword, ('#pop', 'while')),
            (r'(?:for)\b', Keyword, ('#pop', 'for')),
            (r'(?:untyped|throw)\b', Keyword),
            (r'(?:return)\b', Keyword, ('#pop', 'optional-expr')),
            (r'(?:macro)\b', Keyword, ('#pop', 'macro')),
            (r'(?:continue|break)\b', Keyword, '#pop'),
            (r'(?:\$\s*[a-z]\b|\$(?!'+ident+'))', Name, ('#pop', 'dollar')),
            (ident_no_keyword, Name, ('#pop', 'expr-chain')),

            # Float
            (r'\.[0-9]+', Number.Float, ('#pop', 'expr-chain')),
            (r'[0-9]+[eE][+\-]?[0-9]+', Number.Float, ('#pop', 'expr-chain')),
            (r'[0-9]+\.[0-9]*[eE][+\-]?[0-9]+', Number.Float, ('#pop', 'expr-chain')),
            (r'[0-9]+\.[0-9]+', Number.Float, ('#pop', 'expr-chain')),
            (r'[0-9]+\.(?!' + ident + r'|\.\.)', Number.Float, ('#pop', 'expr-chain')),

            # Int
            (r'0x[0-9a-fA-F]+', Number.Hex, ('#pop', 'expr-chain')),
            (r'[0-9]+', Number.Integer, ('#pop', 'expr-chain')),

            # String
            (r"'", String.Single, ('#pop', 'expr-chain', 'string-single-interpol')),
            (r'"', String.Double, ('#pop', 'expr-chain', 'string-double')),

            # EReg
            (r'~/(\\\\|\\[^\\]|[^/\\\n])*/[gimsu]*', String.Regex, ('#pop', 'expr-chain')),

            # Array
            (r'\[', Punctuation, ('#pop', 'expr-chain', 'array-decl')),
        ],

        'expr-chain': [
            include('spaces'),
            (r'(?:\+\+|\-\-)', Operator),
            (binop, Operator, ('#pop', 'expr')),
            (r'(?:in)\b', Keyword, ('#pop', 'expr')),
            (r'\?', Operator, ('#pop', 'expr', 'ternary', 'expr')),
            (r'(\.)(' + ident_no_keyword + ')', bygroups(Punctuation, Name)),
            (r'\[', Punctuation, 'array-access'),
            (r'\(', Punctuation, 'call'),
            default('#pop'),
        ],

        # macro reification
        'macro': [
            include('spaces'),
            include('meta'),
            (r':', Punctuation, ('#pop', 'type')),

            (r'(?:extern|private)\b', Keyword.Declaration),
            (r'(?:abstract)\b', Keyword.Declaration, ('#pop', 'optional-semicolon', 'abstract')),
            (r'(?:class|interface)\b', Keyword.Declaration, ('#pop', 'optional-semicolon', 'macro-class')),
            (r'(?:enum)\b', Keyword.Declaration, ('#pop', 'optional-semicolon', 'enum')),
            (r'(?:typedef)\b', Keyword.Declaration, ('#pop', 'optional-semicolon', 'typedef')),

            default(('#pop', 'expr')),
        ],

        'macro-class': [
            (r'\{', Punctuation, ('#pop', 'class-body')),
            include('class')
        ],

        # cast can be written as "cast expr" or "cast(expr, type)"
        'cast': [
            include('spaces'),
            (r'\(', Punctuation, ('#pop', 'parenthesis-close',
                                  'cast-type', 'expr')),
            default(('#pop', 'expr')),
        ],

        # optionally give a type as the 2nd argument of cast()
        'cast-type': [
            include('spaces'),
            (r',', Punctuation, ('#pop', 'type')),
            default('#pop'),
        ],

        'catch': [
            include('spaces'),
            (r'(?:catch)\b', Keyword, ('expr', 'function-param',
                                       'parenthesis-open')),
            default('#pop'),
        ],

        # do-while loop
        'do': [
            include('spaces'),
            default(('#pop', 'do-while', 'expr')),
        ],

        # the while after do
        'do-while': [
            include('spaces'),
            (r'(?:while)\b', Keyword, ('#pop', 'parenthesis',
                                       'parenthesis-open')),
        ],

        'while': [
            include('spaces'),
            (r'\(', Punctuation, ('#pop', 'expr', 'parenthesis')),
        ],

        'for': [
            include('spaces'),
            (r'\(', Punctuation, ('#pop', 'expr', 'parenthesis')),
        ],

        'if': [
            include('spaces'),
            (r'\(', Punctuation, ('#pop', 'else', 'optional-semicolon', 'expr',
                                  'parenthesis')),
        ],

        'else': [
            include('spaces'),
            (r'(?:else)\b', Keyword, ('#pop', 'expr')),
            default('#pop'),
        ],

        'switch': [
            include('spaces'),
            default(('#pop', 'switch-body', 'bracket-open', 'expr')),
        ],

        'switch-body': [
            include('spaces'),
            (r'(?:case|default)\b', Keyword, ('case-block', 'case')),
            (r'\}', Punctuation, '#pop'),
        ],

        'case': [
            include('spaces'),
            (r':', Punctuation, '#pop'),
            default(('#pop', 'case-sep', 'case-guard', 'expr')),
        ],

        'case-sep': [
            include('spaces'),
            (r':', Punctuation, '#pop'),
            (r',', Punctuation, ('#pop', 'case')),
        ],

        'case-guard': [
            include('spaces'),
            (r'(?:if)\b', Keyword, ('#pop', 'parenthesis', 'parenthesis-open')),
            default('#pop'),
        ],

        # optional multiple expr under a case
        'case-block': [
            include('spaces'),
            (r'(?!(?:case|default)\b|\})', Keyword, 'expr-statement'),
            default('#pop'),
        ],

        'new': [
            include('spaces'),
            default(('#pop', 'call', 'parenthesis-open', 'type')),
        ],

        'array-decl': [
            include('spaces'),
            (r'\]', Punctuation, '#pop'),
            default(('#pop', 'array-decl-sep', 'expr')),
        ],

        'array-decl-sep': [
            include('spaces'),
            (r'\]', Punctuation, '#pop'),
            (r',', Punctuation, ('#pop', 'array-decl')),
        ],

        'array-access': [
            include('spaces'),
            default(('#pop', 'array-access-close', 'expr')),
        ],

        'array-access-close': [
            include('spaces'),
            (r'\]', Punctuation, '#pop'),
        ],

        'comma': [
            include('spaces'),
            (r',', Punctuation, '#pop'),
        ],

        'colon': [
            include('spaces'),
            (r':', Punctuation, '#pop'),
        ],

        'semicolon': [
            include('spaces'),
            (r';', Punctuation, '#pop'),
        ],

        'optional-semicolon': [
            include('spaces'),
            (r';', Punctuation, '#pop'),
            default('#pop'),
        ],

        # identity that CAN be a Haxe keyword
        'ident': [
            include('spaces'),
            (ident, Name, '#pop'),
        ],

        'dollar': [
            include('spaces'),
            (r'\{', Punctuation, ('#pop', 'expr-chain', 'bracket-close', 'expr')),
            default(('#pop', 'expr-chain')),
        ],

        'type-name': [
            include('spaces'),
            (typeid, Name, '#pop'),
        ],

        'type-full-name': [
            include('spaces'),
            (r'\.', Punctuation, 'ident'),
            default('#pop'),
        ],

        'type': [
            include('spaces'),
            (r'\?', Punctuation),
            (ident, Name, ('#pop', 'type-check', 'type-full-name')),
            (r'\{', Punctuation, ('#pop', 'type-check', 'type-struct')),
            (r'\(', Punctuation, ('#pop', 'type-check', 'type-parenthesis')),
        ],

        'type-parenthesis': [
            include('spaces'),
            default(('#pop', 'parenthesis-close', 'type')),
        ],

        'type-check': [
            include('spaces'),
            (r'->', Punctuation, ('#pop', 'type')),
            (r'<(?!=)', Punctuation, 'type-param'),
            default('#pop'),
        ],

        'type-struct': [
            include('spaces'),
            (r'\}', Punctuation, '#pop'),
            (r'\?', Punctuation),
            (r'>', Punctuation, ('comma', 'type')),
            (ident_no_keyword, Name, ('#pop', 'type-struct-sep', 'type', 'colon')),
            include('class-body'),
        ],

        'type-struct-sep': [
            include('spaces'),
            (r'\}', Punctuation, '#pop'),
            (r',', Punctuation, ('#pop', 'type-struct')),
        ],

        # type-param can be a normal type or a constant literal...
        'type-param-type': [
            # Float
            (r'\.[0-9]+', Number.Float, '#pop'),
            (r'[0-9]+[eE][+\-]?[0-9]+', Number.Float, '#pop'),
            (r'[0-9]+\.[0-9]*[eE][+\-]?[0-9]+', Number.Float, '#pop'),
            (r'[0-9]+\.[0-9]+', Number.Float, '#pop'),
            (r'[0-9]+\.(?!' + ident + r'|\.\.)', Number.Float, '#pop'),

            # Int
            (r'0x[0-9a-fA-F]+', Number.Hex, '#pop'),
            (r'[0-9]+', Number.Integer, '#pop'),

            # String
            (r"'", String.Single, ('#pop', 'string-single')),
            (r'"', String.Double, ('#pop', 'string-double')),

            # EReg
            (r'~/(\\\\|\\[^\\]|[^/\\\n])*/[gim]*', String.Regex, '#pop'),

            # Array
            (r'\[', Operator, ('#pop', 'array-decl')),

            include('type'),
        ],

        # type-param part of a type
        # ie. the <A,B> path in Map<A,B>
        'type-param': [
            include('spaces'),
            default(('#pop', 'type-param-sep', 'type-param-type')),
        ],

        'type-param-sep': [
            include('spaces'),
            (r'>', Punctuation, '#pop'),
            (r',', Punctuation, ('#pop', 'type-param')),
        ],

        # optional type-param that may include constraint
        # ie. <T:Constraint, T2:(ConstraintA,ConstraintB)>
        'type-param-constraint': [
            include('spaces'),
            (r'<(?!=)', Punctuation, ('#pop', 'type-param-constraint-sep',
                                      'type-param-constraint-flag', 'type-name')),
            default('#pop'),
        ],

        'type-param-constraint-sep': [
            include('spaces'),
            (r'>', Punctuation, '#pop'),
            (r',', Punctuation, ('#pop', 'type-param-constraint-sep',
                                 'type-param-constraint-flag', 'type-name')),
        ],

        # the optional constraint inside type-param
        'type-param-constraint-flag': [
            include('spaces'),
            (r':', Punctuation, ('#pop', 'type-param-constraint-flag-type')),
            default('#pop'),
        ],

        'type-param-constraint-flag-type': [
            include('spaces'),
            (r'\(', Punctuation, ('#pop', 'type-param-constraint-flag-type-sep',
                                  'type')),
            default(('#pop', 'type')),
        ],

        'type-param-constraint-flag-type-sep': [
            include('spaces'),
            (r'\)', Punctuation, '#pop'),
            (r',', Punctuation, 'type'),
        ],

        # a parenthesis expr that contain exactly one expr
        'parenthesis': [
            include('spaces'),
            default(('#pop', 'parenthesis-close', 'flag', 'expr')),
        ],

        'parenthesis-open': [
            include('spaces'),
            (r'\(', Punctuation, '#pop'),
        ],

        'parenthesis-close': [
            include('spaces'),
            (r'\)', Punctuation, '#pop'),
        ],

        'var': [
            include('spaces'),
            (ident_no_keyword, Text, ('#pop', 'var-sep', 'assign', 'flag', 'prop-get-set')),
        ],

        # optional more var decl.
        'var-sep': [
            include('spaces'),
            (r',', Punctuation, ('#pop', 'var')),
            default('#pop'),
        ],

        # optional assignment
        'assign': [
            include('spaces'),
            (r'=', Operator, ('#pop', 'expr')),
            default('#pop'),
        ],

        # optional type flag
        'flag': [
            include('spaces'),
            (r':', Punctuation, ('#pop', 'type')),
            default('#pop'),
        ],

        # colon as part of a ternary operator (?:)
        'ternary': [
            include('spaces'),
            (r':', Operator, '#pop'),
        ],

        # function call
        'call': [
            include('spaces'),
            (r'\)', Punctuation, '#pop'),
            default(('#pop', 'call-sep', 'expr')),
        ],

        # after a call param
        'call-sep': [
            include('spaces'),
            (r'\)', Punctuation, '#pop'),
            (r',', Punctuation, ('#pop', 'call')),
        ],

        # bracket can be block or object
        'bracket': [
            include('spaces'),
            (r'(?!(?:\$\s*[a-z]\b|\$(?!'+ident+')))' + ident_no_keyword, Name,
             ('#pop', 'bracket-check')),
            (r"'", String.Single, ('#pop', 'bracket-check', 'string-single')),
            (r'"', String.Double, ('#pop', 'bracket-check', 'string-double')),
            default(('#pop', 'block')),
        ],

        'bracket-check': [
            include('spaces'),
            (r':', Punctuation, ('#pop', 'object-sep', 'expr')),  # is object
            default(('#pop', 'block', 'optional-semicolon', 'expr-chain')),  # is block
        ],

        # code block
        'block': [
            include('spaces'),
            (r'\}', Punctuation, '#pop'),
            default('expr-statement'),
        ],

        # object in key-value pairs
        'object': [
            include('spaces'),
            (r'\}', Punctuation, '#pop'),
            default(('#pop', 'object-sep', 'expr', 'colon', 'ident-or-string'))
        ],

        # a key of an object
        'ident-or-string': [
            include('spaces'),
            (ident_no_keyword, Name, '#pop'),
            (r"'", String.Single, ('#pop', 'string-single')),
            (r'"', String.Double, ('#pop', 'string-double')),
        ],

        # after a key-value pair in object
        'object-sep': [
            include('spaces'),
            (r'\}', Punctuation, '#pop'),
            (r',', Punctuation, ('#pop', 'object')),
        ],



    }

    def analyse_text(text):
        if re.match(r'\w+\s*:\s*\w', text):
            return 0.3


class HxmlLexer(RegexLexer):
    """
    Lexer for haXe build files.
    """
    name = 'Hxml'
    url = 'https://haxe.org/manual/compiler-usage-hxml.html'
    aliases = ['haxeml', 'hxml']
    filenames = ['*.hxml']
    version_added = '1.6'

    tokens = {
        'root': [
            # Separator
            (r'(--)(next)', bygroups(Punctuation, Generic.Heading)),
            # Compiler switches with one dash
            (r'(-)(prompt|debug|v)', bygroups(Punctuation, Keyword.Keyword)),
            # Compilerswitches with two dashes
            (r'(--)(neko-source|flash-strict|flash-use-stage|no-opt|no-traces|'
             r'no-inline|times|no-output)', bygroups(Punctuation, Keyword)),
            # Targets and other options that take an argument
            (r'(-)(cpp|js|neko|x|as3|swf9?|swf-lib|php|xml|main|lib|D|resource|'
             r'cp|cmd)( +)(.+)',
             bygroups(Punctuation, Keyword, Whitespace, String)),
            # Options that take only numerical arguments
            (r'(-)(swf-version)( +)(\d+)',
             bygroups(Punctuation, Keyword, Whitespace, Number.Integer)),
            # An Option that defines the size, the fps and the background
            # color of an flash movie
            (r'(-)(swf-header)( +)(\d+)(:)(\d+)(:)(\d+)(:)([A-Fa-f0-9]{6})',
             bygroups(Punctuation, Keyword, Whitespace, Number.Integer,
                      Punctuation, Number.Integer, Punctuation, Number.Integer,
                      Punctuation, Number.Hex)),
            # options with two dashes that takes arguments
            (r'(--)(js-namespace|php-front|php-lib|remap|gen-hx-classes)( +)'
             r'(.+)', bygroups(Punctuation, Keyword, Whitespace, String)),
            # Single line comment, multiline ones are not allowed.
            (r'#.*', Comment.Single)
        ]
    }

# === NexusCore/myenv\Lib\site-packages\pip\_internal\req\req_install.py ===
import functools
import logging
import os
import shutil
import sys
import uuid
import zipfile
from optparse import Values
from pathlib import Path
from typing import Any, Collection, Dict, Iterable, List, Optional, Sequence, Union

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version
from pip._vendor.packaging.version import parse as parse_version
from pip._vendor.pyproject_hooks import BuildBackendHookCaller

from pip._internal.build_env import BuildEnvironment, NoOpBuildEnvironment
from pip._internal.exceptions import InstallationError, PreviousBuildDirError
from pip._internal.locations import get_scheme
from pip._internal.metadata import (
    BaseDistribution,
    get_default_environment,
    get_directory_distribution,
    get_wheel_distribution,
)
from pip._internal.metadata.base import FilesystemWheel
from pip._internal.models.direct_url import DirectUrl
from pip._internal.models.link import Link
from pip._internal.operations.build.metadata import generate_metadata
from pip._internal.operations.build.metadata_editable import generate_editable_metadata
from pip._internal.operations.build.metadata_legacy import (
    generate_metadata as generate_metadata_legacy,
)
from pip._internal.operations.install.editable_legacy import (
    install_editable as install_editable_legacy,
)
from pip._internal.operations.install.wheel import install_wheel
from pip._internal.pyproject import load_pyproject_toml, make_pyproject_path
from pip._internal.req.req_uninstall import UninstallPathSet
from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.misc import (
    ConfiguredBuildBackendHookCaller,
    ask_path_exists,
    backup_dir,
    display_path,
    hide_url,
    is_installable_dir,
    redact_auth_from_requirement,
    redact_auth_from_url,
)
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.subprocess import runner_with_spinner_message
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds
from pip._internal.utils.unpacking import unpack_file
from pip._internal.utils.virtualenv import running_under_virtualenv
from pip._internal.vcs import vcs

logger = logging.getLogger(__name__)


class InstallRequirement:
    """
    Represents something that may be installed later on, may have information
    about where to fetch the relevant requirement and also contains logic for
    installing the said requirement.
    """

    def __init__(
        self,
        req: Optional[Requirement],
        comes_from: Optional[Union[str, "InstallRequirement"]],
        editable: bool = False,
        link: Optional[Link] = None,
        markers: Optional[Marker] = None,
        use_pep517: Optional[bool] = None,
        isolated: bool = False,
        *,
        global_options: Optional[List[str]] = None,
        hash_options: Optional[Dict[str, List[str]]] = None,
        config_settings: Optional[Dict[str, Union[str, List[str]]]] = None,
        constraint: bool = False,
        extras: Collection[str] = (),
        user_supplied: bool = False,
        permit_editable_wheels: bool = False,
    ) -> None:
        assert req is None or isinstance(req, Requirement), req
        self.req = req
        self.comes_from = comes_from
        self.constraint = constraint
        self.editable = editable
        self.permit_editable_wheels = permit_editable_wheels

        # source_dir is the local directory where the linked requirement is
        # located, or unpacked. In case unpacking is needed, creating and
        # populating source_dir is done by the RequirementPreparer. Note this
        # is not necessarily the directory where pyproject.toml or setup.py is
        # located - that one is obtained via unpacked_source_directory.
        self.source_dir: Optional[str] = None
        if self.editable:
            assert link
            if link.is_file:
                self.source_dir = os.path.normpath(os.path.abspath(link.file_path))

        # original_link is the direct URL that was provided by the user for the
        # requirement, either directly or via a constraints file.
        if link is None and req and req.url:
            # PEP 508 URL requirement
            link = Link(req.url)
        self.link = self.original_link = link

        # When this InstallRequirement is a wheel obtained from the cache of locally
        # built wheels, this is the source link corresponding to the cache entry, which
        # was used to download and build the cached wheel.
        self.cached_wheel_source_link: Optional[Link] = None

        # Information about the location of the artifact that was downloaded . This
        # property is guaranteed to be set in resolver results.
        self.download_info: Optional[DirectUrl] = None

        # Path to any downloaded or already-existing package.
        self.local_file_path: Optional[str] = None
        if self.link and self.link.is_file:
            self.local_file_path = self.link.file_path

        if extras:
            self.extras = extras
        elif req:
            self.extras = req.extras
        else:
            self.extras = set()
        if markers is None and req:
            markers = req.marker
        self.markers = markers

        # This holds the Distribution object if this requirement is already installed.
        self.satisfied_by: Optional[BaseDistribution] = None
        # Whether the installation process should try to uninstall an existing
        # distribution before installing this requirement.
        self.should_reinstall = False
        # Temporary build location
        self._temp_build_dir: Optional[TempDirectory] = None
        # Set to True after successful installation
        self.install_succeeded: Optional[bool] = None
        # Supplied options
        self.global_options = global_options if global_options else []
        self.hash_options = hash_options if hash_options else {}
        self.config_settings = config_settings
        # Set to True after successful preparation of this requirement
        self.prepared = False
        # User supplied requirement are explicitly requested for installation
        # by the user via CLI arguments or requirements files, as opposed to,
        # e.g. dependencies, extras or constraints.
        self.user_supplied = user_supplied

        self.isolated = isolated
        self.build_env: BuildEnvironment = NoOpBuildEnvironment()

        # For PEP 517, the directory where we request the project metadata
        # gets stored. We need this to pass to build_wheel, so the backend
        # can ensure that the wheel matches the metadata (see the PEP for
        # details).
        self.metadata_directory: Optional[str] = None

        # The static build requirements (from pyproject.toml)
        self.pyproject_requires: Optional[List[str]] = None

        # Build requirements that we will check are available
        self.requirements_to_check: List[str] = []

        # The PEP 517 backend we should use to build the project
        self.pep517_backend: Optional[BuildBackendHookCaller] = None

        # Are we using PEP 517 for this requirement?
        # After pyproject.toml has been loaded, the only valid values are True
        # and False. Before loading, None is valid (meaning "use the default").
        # Setting an explicit value before loading pyproject.toml is supported,
        # but after loading this flag should be treated as read only.
        self.use_pep517 = use_pep517

        # If config settings are provided, enforce PEP 517.
        if self.config_settings:
            if self.use_pep517 is False:
                logger.warning(
                    "--no-use-pep517 ignored for %s "
                    "because --config-settings are specified.",
                    self,
                )
            self.use_pep517 = True

        # This requirement needs more preparation before it can be built
        self.needs_more_preparation = False

        # This requirement needs to be unpacked before it can be installed.
        self._archive_source: Optional[Path] = None

    def __str__(self) -> str:
        if self.req:
            s = redact_auth_from_requirement(self.req)
            if self.link:
                s += f" from {redact_auth_from_url(self.link.url)}"
        elif self.link:
            s = redact_auth_from_url(self.link.url)
        else:
            s = "<InstallRequirement>"
        if self.satisfied_by is not None:
            if self.satisfied_by.location is not None:
                location = display_path(self.satisfied_by.location)
            else:
                location = "<memory>"
            s += f" in {location}"
        if self.comes_from:
            if isinstance(self.comes_from, str):
                comes_from: Optional[str] = self.comes_from
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += f" (from {comes_from})"
        return s

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} object: "
            f"{str(self)} editable={self.editable!r}>"
        )

    def format_debug(self) -> str:
        """An un-tested helper for getting state, for debugging."""
        attributes = vars(self)
        names = sorted(attributes)

        state = (f"{attr}={attributes[attr]!r}" for attr in sorted(names))
        return "<{name} object: {{{state}}}>".format(
            name=self.__class__.__name__,
            state=", ".join(state),
        )

    # Things that are valid for all kinds of requirements?
    @property
    def name(self) -> Optional[str]:
        if self.req is None:
            return None
        return self.req.name

    @functools.cached_property
    def supports_pyproject_editable(self) -> bool:
        if not self.use_pep517:
            return False
        assert self.pep517_backend
        with self.build_env:
            runner = runner_with_spinner_message(
                "Checking if build backend supports build_editable"
            )
            with self.pep517_backend.subprocess_runner(runner):
                return "build_editable" in self.pep517_backend._supported_features()

    @property
    def specifier(self) -> SpecifierSet:
        assert self.req is not None
        return self.req.specifier

    @property
    def is_direct(self) -> bool:
        """Whether this requirement was specified as a direct URL."""
        return self.original_link is not None

    @property
    def is_pinned(self) -> bool:
        """Return whether I am pinned to an exact version.

        For example, some-package==1.2 is pinned; some-package>1.2 is not.
        """
        assert self.req is not None
        specifiers = self.req.specifier
        return len(specifiers) == 1 and next(iter(specifiers)).operator in {"==", "==="}

    def match_markers(self, extras_requested: Optional[Iterable[str]] = None) -> bool:
        if not extras_requested:
            # Provide an extra to safely evaluate the markers
            # without matching any extra
            extras_requested = ("",)
        if self.markers is not None:
            return any(
                self.markers.evaluate({"extra": extra}) for extra in extras_requested
            )
        else:
            return True

    @property
    def has_hash_options(self) -> bool:
        """Return whether any known-good hashes are specified as options.

        These activate --require-hashes mode; hashes specified as part of a
        URL do not.

        """
        return bool(self.hash_options)

    def hashes(self, trust_internet: bool = True) -> Hashes:
        """Return a hash-comparer that considers my option- and URL-based
        hashes to be known-good.

        Hashes in URLs--ones embedded in the requirements file, not ones
        downloaded from an index server--are almost peers with ones from
        flags. They satisfy --require-hashes (whether it was implicitly or
        explicitly activated) but do not activate it. md5 and sha224 are not
        allowed in flags, which should nudge people toward good algos. We
        always OR all hashes together, even ones from URLs.

        :param trust_internet: Whether to trust URL-based (#md5=...) hashes
            downloaded from the internet, as by populate_link()

        """
        good_hashes = self.hash_options.copy()
        if trust_internet:
            link = self.link
        elif self.is_direct and self.user_supplied:
            link = self.original_link
        else:
            link = None
        if link and link.hash:
            assert link.hash_name is not None
            good_hashes.setdefault(link.hash_name, []).append(link.hash)
        return Hashes(good_hashes)

    def from_path(self) -> Optional[str]:
        """Format a nice indicator to show where this "comes from" """
        if self.req is None:
            return None
        s = str(self.req)
        if self.comes_from:
            comes_from: Optional[str]
            if isinstance(self.comes_from, str):
                comes_from = self.comes_from
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += "->" + comes_from
        return s

    def ensure_build_location(
        self, build_dir: str, autodelete: bool, parallel_builds: bool
    ) -> str:
        assert build_dir is not None
        if self._temp_build_dir is not None:
            assert self._temp_build_dir.path
            return self._temp_build_dir.path
        if self.req is None:
            # Some systems have /tmp as a symlink which confuses custom
            # builds (such as numpy). Thus, we ensure that the real path
            # is returned.
            self._temp_build_dir = TempDirectory(
                kind=tempdir_kinds.REQ_BUILD, globally_managed=True
            )

            return self._temp_build_dir.path

        # This is the only remaining place where we manually determine the path
        # for the temporary directory. It is only needed for editables where
        # it is the value of the --src option.

        # When parallel builds are enabled, add a UUID to the build directory
        # name so multiple builds do not interfere with each other.
        dir_name: str = canonicalize_name(self.req.name)
        if parallel_builds:
            dir_name = f"{dir_name}_{uuid.uuid4().hex}"

        # FIXME: Is there a better place to create the build_dir? (hg and bzr
        # need this)
        if not os.path.exists(build_dir):
            logger.debug("Creating directory %s", build_dir)
            os.makedirs(build_dir)
        actual_build_dir = os.path.join(build_dir, dir_name)
        # `None` indicates that we respect the globally-configured deletion
        # settings, which is what we actually want when auto-deleting.
        delete_arg = None if autodelete else False
        return TempDirectory(
            path=actual_build_dir,
            delete=delete_arg,
            kind=tempdir_kinds.REQ_BUILD,
            globally_managed=True,
        ).path

    def _set_requirement(self) -> None:
        """Set requirement after generating metadata."""
        assert self.req is None
        assert self.metadata is not None
        assert self.source_dir is not None

        # Construct a Requirement object from the generated metadata
        if isinstance(parse_version(self.metadata["Version"]), Version):
            op = "=="
        else:
            op = "==="

        self.req = get_requirement(
            "".join(
                [
                    self.metadata["Name"],
                    op,
                    self.metadata["Version"],
                ]
            )
        )

    def warn_on_mismatching_name(self) -> None:
        assert self.req is not None
        metadata_name = canonicalize_name(self.metadata["Name"])
        if canonicalize_name(self.req.name) == metadata_name:
            # Everything is fine.
            return

        # If we're here, there's a mismatch. Log a warning about it.
        logger.warning(
            "Generating metadata for package %s "
            "produced metadata for project name %s. Fix your "
            "#egg=%s fragments.",
            self.name,
            metadata_name,
            self.name,
        )
        self.req = get_requirement(metadata_name)

    def check_if_exists(self, use_user_site: bool) -> None:
        """Find an installed distribution that satisfies or conflicts
        with this requirement, and set self.satisfied_by or
        self.should_reinstall appropriately.
        """
        if self.req is None:
            return
        existing_dist = get_default_environment().get_distribution(self.req.name)
        if not existing_dist:
            return

        version_compatible = self.req.specifier.contains(
            existing_dist.version,
            prereleases=True,
        )
        if not version_compatible:
            self.satisfied_by = None
            if use_user_site:
                if existing_dist.in_usersite:
                    self.should_reinstall = True
                elif running_under_virtualenv() and existing_dist.in_site_packages:
                    raise InstallationError(
                        f"Will not install to the user site because it will "
                        f"lack sys.path precedence to {existing_dist.raw_name} "
                        f"in {existing_dist.location}"
                    )
            else:
                self.should_reinstall = True
        else:
            if self.editable:
                self.should_reinstall = True
                # when installing editables, nothing pre-existing should ever
                # satisfy
                self.satisfied_by = None
            else:
                self.satisfied_by = existing_dist

    # Things valid for wheels
    @property
    def is_wheel(self) -> bool:
        if not self.link:
            return False
        return self.link.is_wheel

    @property
    def is_wheel_from_cache(self) -> bool:
        # When True, it means that this InstallRequirement is a local wheel file in the
        # cache of locally built wheels.
        return self.cached_wheel_source_link is not None

    # Things valid for sdists
    @property
    def unpacked_source_directory(self) -> str:
        assert self.source_dir, f"No source dir for {self}"
        return os.path.join(
            self.source_dir, self.link and self.link.subdirectory_fragment or ""
        )

    @property
    def setup_py_path(self) -> str:
        assert self.source_dir, f"No source dir for {self}"
        setup_py = os.path.join(self.unpacked_source_directory, "setup.py")

        return setup_py

    @property
    def setup_cfg_path(self) -> str:
        assert self.source_dir, f"No source dir for {self}"
        setup_cfg = os.path.join(self.unpacked_source_directory, "setup.cfg")

        return setup_cfg

    @property
    def pyproject_toml_path(self) -> str:
        assert self.source_dir, f"No source dir for {self}"
        return make_pyproject_path(self.unpacked_source_directory)

    def load_pyproject_toml(self) -> None:
        """Load the pyproject.toml file.

        After calling this routine, all of the attributes related to PEP 517
        processing for this requirement have been set. In particular, the
        use_pep517 attribute can be used to determine whether we should
        follow the PEP 517 or legacy (setup.py) code path.
        """
        pyproject_toml_data = load_pyproject_toml(
            self.use_pep517, self.pyproject_toml_path, self.setup_py_path, str(self)
        )

        if pyproject_toml_data is None:
            assert not self.config_settings
            self.use_pep517 = False
            return

        self.use_pep517 = True
        requires, backend, check, backend_path = pyproject_toml_data
        self.requirements_to_check = check
        self.pyproject_requires = requires
        self.pep517_backend = ConfiguredBuildBackendHookCaller(
            self,
            self.unpacked_source_directory,
            backend,
            backend_path=backend_path,
        )

    def isolated_editable_sanity_check(self) -> None:
        """Check that an editable requirement if valid for use with PEP 517/518.

        This verifies that an editable that has a pyproject.toml either supports PEP 660
        or as a setup.py or a setup.cfg
        """
        if (
            self.editable
            and self.use_pep517
            and not self.supports_pyproject_editable
            and not os.path.isfile(self.setup_py_path)
            and not os.path.isfile(self.setup_cfg_path)
        ):
            raise InstallationError(
                f"Project {self} has a 'pyproject.toml' and its build "
                f"backend is missing the 'build_editable' hook. Since it does not "
                f"have a 'setup.py' nor a 'setup.cfg', "
                f"it cannot be installed in editable mode. "
                f"Consider using a build backend that supports PEP 660."
            )

    def prepare_metadata(self) -> None:
        """Ensure that project metadata is available.

        Under PEP 517 and PEP 660, call the backend hook to prepare the metadata.
        Under legacy processing, call setup.py egg-info.
        """
        assert self.source_dir, f"No source dir for {self}"
        details = self.name or f"from {self.link}"

        if self.use_pep517:
            assert self.pep517_backend is not None
            if (
                self.editable
                and self.permit_editable_wheels
                and self.supports_pyproject_editable
            ):
                self.metadata_directory = generate_editable_metadata(
                    build_env=self.build_env,
                    backend=self.pep517_backend,
                    details=details,
                )
            else:
                self.metadata_directory = generate_metadata(
                    build_env=self.build_env,
                    backend=self.pep517_backend,
                    details=details,
                )
        else:
            self.metadata_directory = generate_metadata_legacy(
                build_env=self.build_env,
                setup_py_path=self.setup_py_path,
                source_dir=self.unpacked_source_directory,
                isolated=self.isolated,
                details=details,
            )

        # Act on the newly generated metadata, based on the name and version.
        if not self.name:
            self._set_requirement()
        else:
            self.warn_on_mismatching_name()

        self.assert_source_matches_version()

    @property
    def metadata(self) -> Any:
        if not hasattr(self, "_metadata"):
            self._metadata = self.get_dist().metadata

        return self._metadata

    def get_dist(self) -> BaseDistribution:
        if self.metadata_directory:
            return get_directory_distribution(self.metadata_directory)
        elif self.local_file_path and self.is_wheel:
            assert self.req is not None
            return get_wheel_distribution(
                FilesystemWheel(self.local_file_path),
                canonicalize_name(self.req.name),
            )
        raise AssertionError(
            f"InstallRequirement {self} has no metadata directory and no wheel: "
            f"can't make a distribution."
        )

    def assert_source_matches_version(self) -> None:
        assert self.source_dir, f"No source dir for {self}"
        version = self.metadata["version"]
        if self.req and self.req.specifier and version not in self.req.specifier:
            logger.warning(
                "Requested %s, but installing version %s",
                self,
                version,
            )
        else:
            logger.debug(
                "Source in %s has version %s, which satisfies requirement %s",
                display_path(self.source_dir),
                version,
                self,
            )

    # For both source distributions and editables
    def ensure_has_source_dir(
        self,
        parent_dir: str,
        autodelete: bool = False,
        parallel_builds: bool = False,
    ) -> None:
        """Ensure that a source_dir is set.

        This will create a temporary build dir if the name of the requirement
        isn't known yet.

        :param parent_dir: The ideal pip parent_dir for the source_dir.
            Generally src_dir for editables and build_dir for sdists.
        :return: self.source_dir
        """
        if self.source_dir is None:
            self.source_dir = self.ensure_build_location(
                parent_dir,
                autodelete=autodelete,
                parallel_builds=parallel_builds,
            )

    def needs_unpacked_archive(self, archive_source: Path) -> None:
        assert self._archive_source is None
        self._archive_source = archive_source

    def ensure_pristine_source_checkout(self) -> None:
        """Ensure the source directory has not yet been built in."""
        assert self.source_dir is not None
        if self._archive_source is not None:
            unpack_file(str(self._archive_source), self.source_dir)
        elif is_installable_dir(self.source_dir):
            # If a checkout exists, it's unwise to keep going.
            # version inconsistencies are logged later, but do not fail
            # the installation.
            raise PreviousBuildDirError(
                f"pip can't proceed with requirements '{self}' due to a "
                f"pre-existing build directory ({self.source_dir}). This is likely "
                "due to a previous installation that failed . pip is "
                "being responsible and not assuming it can delete this. "
                "Please delete it and try again."
            )

    # For editable installations
    def update_editable(self) -> None:
        if not self.link:
            logger.debug(
                "Cannot update repository at %s; repository location is unknown",
                self.source_dir,
            )
            return
        assert self.editable
        assert self.source_dir
        if self.link.scheme == "file":
            # Static paths don't get updated
            return
        vcs_backend = vcs.get_backend_for_scheme(self.link.scheme)
        # Editable requirements are validated in Requirement constructors.
        # So here, if it's neither a path nor a valid VCS URL, it's a bug.
        assert vcs_backend, f"Unsupported VCS URL {self.link.url}"
        hidden_url = hide_url(self.link.url)
        vcs_backend.obtain(self.source_dir, url=hidden_url, verbosity=0)

    # Top-level Actions
    def uninstall(
        self, auto_confirm: bool = False, verbose: bool = False
    ) -> Optional[UninstallPathSet]:
        """
        Uninstall the distribution currently satisfying this requirement.

        Prompts before removing or modifying files unless
        ``auto_confirm`` is True.

        Refuses to delete or modify files outside of ``sys.prefix`` -
        thus uninstallation within a virtual environment can only
        modify that virtual environment, even if the virtualenv is
        linked to global site-packages.

        """
        assert self.req
        dist = get_default_environment().get_distribution(self.req.name)
        if not dist:
            logger.warning("Skipping %s as it is not installed.", self.name)
            return None
        logger.info("Found existing installation: %s", dist)

        uninstalled_pathset = UninstallPathSet.from_dist(dist)
        uninstalled_pathset.remove(auto_confirm, verbose)
        return uninstalled_pathset

    def _get_archive_name(self, path: str, parentdir: str, rootdir: str) -> str:
        def _clean_zip_name(name: str, prefix: str) -> str:
            assert name.startswith(
                prefix + os.path.sep
            ), f"name {name!r} doesn't start with prefix {prefix!r}"
            name = name[len(prefix) + 1 :]
            name = name.replace(os.path.sep, "/")
            return name

        assert self.req is not None
        path = os.path.join(parentdir, path)
        name = _clean_zip_name(path, rootdir)
        return self.req.name + "/" + name

    def archive(self, build_dir: Optional[str]) -> None:
        """Saves archive to provided build_dir.

        Used for saving downloaded VCS requirements as part of `pip download`.
        """
        assert self.source_dir
        if build_dir is None:
            return

        create_archive = True
        archive_name = "{}-{}.zip".format(self.name, self.metadata["version"])
        archive_path = os.path.join(build_dir, archive_name)

        if os.path.exists(archive_path):
            response = ask_path_exists(
                f"The file {display_path(archive_path)} exists. (i)gnore, (w)ipe, "
                "(b)ackup, (a)bort ",
                ("i", "w", "b", "a"),
            )
            if response == "i":
                create_archive = False
            elif response == "w":
                logger.warning("Deleting %s", display_path(archive_path))
                os.remove(archive_path)
            elif response == "b":
                dest_file = backup_dir(archive_path)
                logger.warning(
                    "Backing up %s to %s",
                    display_path(archive_path),
                    display_path(dest_file),
                )
                shutil.move(archive_path, dest_file)
            elif response == "a":
                sys.exit(-1)

        if not create_archive:
            return

        zip_output = zipfile.ZipFile(
            archive_path,
            "w",
            zipfile.ZIP_DEFLATED,
            allowZip64=True,
        )
        with zip_output:
            dir = os.path.normcase(os.path.abspath(self.unpacked_source_directory))
            for dirpath, dirnames, filenames in os.walk(dir):
                for dirname in dirnames:
                    dir_arcname = self._get_archive_name(
                        dirname,
                        parentdir=dirpath,
                        rootdir=dir,
                    )
                    zipdir = zipfile.ZipInfo(dir_arcname + "/")
                    zipdir.external_attr = 0x1ED << 16  # 0o755
                    zip_output.writestr(zipdir, "")
                for filename in filenames:
                    file_arcname = self._get_archive_name(
                        filename,
                        parentdir=dirpath,
                        rootdir=dir,
                    )
                    filename = os.path.join(dirpath, filename)
                    zip_output.write(filename, file_arcname)

        logger.info("Saved %s", display_path(archive_path))

    def install(
        self,
        global_options: Optional[Sequence[str]] = None,
        root: Optional[str] = None,
        home: Optional[str] = None,
        prefix: Optional[str] = None,
        warn_script_location: bool = True,
        use_user_site: bool = False,
        pycompile: bool = True,
    ) -> None:
        assert self.req is not None
        scheme = get_scheme(
            self.req.name,
            user=use_user_site,
            home=home,
            root=root,
            isolated=self.isolated,
            prefix=prefix,
        )

        if self.editable and not self.is_wheel:
            deprecated(
                reason=(
                    f"Legacy editable install of {self} (setup.py develop) "
                    "is deprecated."
                ),
                replacement=(
                    "to add a pyproject.toml or enable --use-pep517, "
                    "and use setuptools >= 64. "
                    "If the resulting installation is not behaving as expected, "
                    "try using --config-settings editable_mode=compat. "
                    "Please consult the setuptools documentation for more information"
                ),
                gone_in="25.1",
                issue=11457,
            )
            if self.config_settings:
                logger.warning(
                    "--config-settings ignored for legacy editable install of %s. "
                    "Consider upgrading to a version of setuptools "
                    "that supports PEP 660 (>= 64).",
                    self,
                )
            install_editable_legacy(
                global_options=global_options if global_options is not None else [],
                prefix=prefix,
                home=home,
                use_user_site=use_user_site,
                name=self.req.name,
                setup_py_path=self.setup_py_path,
                isolated=self.isolated,
                build_env=self.build_env,
                unpacked_source_directory=self.unpacked_source_directory,
            )
            self.install_succeeded = True
            return

        assert self.is_wheel
        assert self.local_file_path

        install_wheel(
            self.req.name,
            self.local_file_path,
            scheme=scheme,
            req_description=str(self.req),
            pycompile=pycompile,
            warn_script_location=warn_script_location,
            direct_url=self.download_info if self.is_direct else None,
            requested=self.user_supplied,
        )
        self.install_succeeded = True


def check_invalid_constraint_type(req: InstallRequirement) -> str:
    # Check for unsupported forms
    problem = ""
    if not req.name:
        problem = "Unnamed requirements are not allowed as constraints"
    elif req.editable:
        problem = "Editable requirements are not allowed as constraints"
    elif req.extras:
        problem = "Constraints cannot have extras"

    if problem:
        deprecated(
            reason=(
                "Constraints are only allowed to take the form of a package "
                "name and a version specifier. Other forms were originally "
                "permitted as an accident of the implementation, but were "
                "undocumented. The new implementation of the resolver no "
                "longer supports these forms."
            ),
            replacement="replacing the constraint with a requirement",
            # No plan yet for when the new resolver becomes default
            gone_in=None,
            issue=8210,
        )

    return problem


def _has_option(options: Values, reqs: List[InstallRequirement], option: str) -> bool:
    if getattr(options, option, None):
        return True
    for req in reqs:
        if getattr(req, option, None):
            return True
    return False


def check_legacy_setup_py_options(
    options: Values,
    reqs: List[InstallRequirement],
) -> None:
    has_build_options = _has_option(options, reqs, "build_options")
    has_global_options = _has_option(options, reqs, "global_options")
    if has_build_options or has_global_options:
        deprecated(
            reason="--build-option and --global-option are deprecated.",
            issue=11859,
            replacement="to use --config-settings",
            gone_in=None,
        )
        logger.warning(
            "Implying --no-binary=:all: due to the presence of "
            "--build-option / --global-option. "
        )
        options.format_control.disallow_binaries()

# === NexusCore/openenv\Lib\site-packages\pip\_internal\req\req_install.py ===
import functools
import logging
import os
import shutil
import sys
import uuid
import zipfile
from optparse import Values
from pathlib import Path
from typing import Any, Collection, Dict, Iterable, List, Optional, Sequence, Union

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version
from pip._vendor.packaging.version import parse as parse_version
from pip._vendor.pyproject_hooks import BuildBackendHookCaller

from pip._internal.build_env import BuildEnvironment, NoOpBuildEnvironment
from pip._internal.exceptions import InstallationError, PreviousBuildDirError
from pip._internal.locations import get_scheme
from pip._internal.metadata import (
    BaseDistribution,
    get_default_environment,
    get_directory_distribution,
    get_wheel_distribution,
)
from pip._internal.metadata.base import FilesystemWheel
from pip._internal.models.direct_url import DirectUrl
from pip._internal.models.link import Link
from pip._internal.operations.build.metadata import generate_metadata
from pip._internal.operations.build.metadata_editable import generate_editable_metadata
from pip._internal.operations.build.metadata_legacy import (
    generate_metadata as generate_metadata_legacy,
)
from pip._internal.operations.install.editable_legacy import (
    install_editable as install_editable_legacy,
)
from pip._internal.operations.install.wheel import install_wheel
from pip._internal.pyproject import load_pyproject_toml, make_pyproject_path
from pip._internal.req.req_uninstall import UninstallPathSet
from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.misc import (
    ConfiguredBuildBackendHookCaller,
    ask_path_exists,
    backup_dir,
    display_path,
    hide_url,
    is_installable_dir,
    redact_auth_from_requirement,
    redact_auth_from_url,
)
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.subprocess import runner_with_spinner_message
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds
from pip._internal.utils.unpacking import unpack_file
from pip._internal.utils.virtualenv import running_under_virtualenv
from pip._internal.vcs import vcs

logger = logging.getLogger(__name__)


class InstallRequirement:
    """
    Represents something that may be installed later on, may have information
    about where to fetch the relevant requirement and also contains logic for
    installing the said requirement.
    """

    def __init__(
        self,
        req: Optional[Requirement],
        comes_from: Optional[Union[str, "InstallRequirement"]],
        editable: bool = False,
        link: Optional[Link] = None,
        markers: Optional[Marker] = None,
        use_pep517: Optional[bool] = None,
        isolated: bool = False,
        *,
        global_options: Optional[List[str]] = None,
        hash_options: Optional[Dict[str, List[str]]] = None,
        config_settings: Optional[Dict[str, Union[str, List[str]]]] = None,
        constraint: bool = False,
        extras: Collection[str] = (),
        user_supplied: bool = False,
        permit_editable_wheels: bool = False,
    ) -> None:
        assert req is None or isinstance(req, Requirement), req
        self.req = req
        self.comes_from = comes_from
        self.constraint = constraint
        self.editable = editable
        self.permit_editable_wheels = permit_editable_wheels

        # source_dir is the local directory where the linked requirement is
        # located, or unpacked. In case unpacking is needed, creating and
        # populating source_dir is done by the RequirementPreparer. Note this
        # is not necessarily the directory where pyproject.toml or setup.py is
        # located - that one is obtained via unpacked_source_directory.
        self.source_dir: Optional[str] = None
        if self.editable:
            assert link
            if link.is_file:
                self.source_dir = os.path.normpath(os.path.abspath(link.file_path))

        # original_link is the direct URL that was provided by the user for the
        # requirement, either directly or via a constraints file.
        if link is None and req and req.url:
            # PEP 508 URL requirement
            link = Link(req.url)
        self.link = self.original_link = link

        # When this InstallRequirement is a wheel obtained from the cache of locally
        # built wheels, this is the source link corresponding to the cache entry, which
        # was used to download and build the cached wheel.
        self.cached_wheel_source_link: Optional[Link] = None

        # Information about the location of the artifact that was downloaded . This
        # property is guaranteed to be set in resolver results.
        self.download_info: Optional[DirectUrl] = None

        # Path to any downloaded or already-existing package.
        self.local_file_path: Optional[str] = None
        if self.link and self.link.is_file:
            self.local_file_path = self.link.file_path

        if extras:
            self.extras = extras
        elif req:
            self.extras = req.extras
        else:
            self.extras = set()
        if markers is None and req:
            markers = req.marker
        self.markers = markers

        # This holds the Distribution object if this requirement is already installed.
        self.satisfied_by: Optional[BaseDistribution] = None
        # Whether the installation process should try to uninstall an existing
        # distribution before installing this requirement.
        self.should_reinstall = False
        # Temporary build location
        self._temp_build_dir: Optional[TempDirectory] = None
        # Set to True after successful installation
        self.install_succeeded: Optional[bool] = None
        # Supplied options
        self.global_options = global_options if global_options else []
        self.hash_options = hash_options if hash_options else {}
        self.config_settings = config_settings
        # Set to True after successful preparation of this requirement
        self.prepared = False
        # User supplied requirement are explicitly requested for installation
        # by the user via CLI arguments or requirements files, as opposed to,
        # e.g. dependencies, extras or constraints.
        self.user_supplied = user_supplied

        self.isolated = isolated
        self.build_env: BuildEnvironment = NoOpBuildEnvironment()

        # For PEP 517, the directory where we request the project metadata
        # gets stored. We need this to pass to build_wheel, so the backend
        # can ensure that the wheel matches the metadata (see the PEP for
        # details).
        self.metadata_directory: Optional[str] = None

        # The static build requirements (from pyproject.toml)
        self.pyproject_requires: Optional[List[str]] = None

        # Build requirements that we will check are available
        self.requirements_to_check: List[str] = []

        # The PEP 517 backend we should use to build the project
        self.pep517_backend: Optional[BuildBackendHookCaller] = None

        # Are we using PEP 517 for this requirement?
        # After pyproject.toml has been loaded, the only valid values are True
        # and False. Before loading, None is valid (meaning "use the default").
        # Setting an explicit value before loading pyproject.toml is supported,
        # but after loading this flag should be treated as read only.
        self.use_pep517 = use_pep517

        # If config settings are provided, enforce PEP 517.
        if self.config_settings:
            if self.use_pep517 is False:
                logger.warning(
                    "--no-use-pep517 ignored for %s "
                    "because --config-settings are specified.",
                    self,
                )
            self.use_pep517 = True

        # This requirement needs more preparation before it can be built
        self.needs_more_preparation = False

        # This requirement needs to be unpacked before it can be installed.
        self._archive_source: Optional[Path] = None

    def __str__(self) -> str:
        if self.req:
            s = redact_auth_from_requirement(self.req)
            if self.link:
                s += f" from {redact_auth_from_url(self.link.url)}"
        elif self.link:
            s = redact_auth_from_url(self.link.url)
        else:
            s = "<InstallRequirement>"
        if self.satisfied_by is not None:
            if self.satisfied_by.location is not None:
                location = display_path(self.satisfied_by.location)
            else:
                location = "<memory>"
            s += f" in {location}"
        if self.comes_from:
            if isinstance(self.comes_from, str):
                comes_from: Optional[str] = self.comes_from
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += f" (from {comes_from})"
        return s

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} object: "
            f"{str(self)} editable={self.editable!r}>"
        )

    def format_debug(self) -> str:
        """An un-tested helper for getting state, for debugging."""
        attributes = vars(self)
        names = sorted(attributes)

        state = (f"{attr}={attributes[attr]!r}" for attr in sorted(names))
        return "<{name} object: {{{state}}}>".format(
            name=self.__class__.__name__,
            state=", ".join(state),
        )

    # Things that are valid for all kinds of requirements?
    @property
    def name(self) -> Optional[str]:
        if self.req is None:
            return None
        return self.req.name

    @functools.cached_property
    def supports_pyproject_editable(self) -> bool:
        if not self.use_pep517:
            return False
        assert self.pep517_backend
        with self.build_env:
            runner = runner_with_spinner_message(
                "Checking if build backend supports build_editable"
            )
            with self.pep517_backend.subprocess_runner(runner):
                return "build_editable" in self.pep517_backend._supported_features()

    @property
    def specifier(self) -> SpecifierSet:
        assert self.req is not None
        return self.req.specifier

    @property
    def is_direct(self) -> bool:
        """Whether this requirement was specified as a direct URL."""
        return self.original_link is not None

    @property
    def is_pinned(self) -> bool:
        """Return whether I am pinned to an exact version.

        For example, some-package==1.2 is pinned; some-package>1.2 is not.
        """
        assert self.req is not None
        specifiers = self.req.specifier
        return len(specifiers) == 1 and next(iter(specifiers)).operator in {"==", "==="}

    def match_markers(self, extras_requested: Optional[Iterable[str]] = None) -> bool:
        if not extras_requested:
            # Provide an extra to safely evaluate the markers
            # without matching any extra
            extras_requested = ("",)
        if self.markers is not None:
            return any(
                self.markers.evaluate({"extra": extra}) for extra in extras_requested
            )
        else:
            return True

    @property
    def has_hash_options(self) -> bool:
        """Return whether any known-good hashes are specified as options.

        These activate --require-hashes mode; hashes specified as part of a
        URL do not.

        """
        return bool(self.hash_options)

    def hashes(self, trust_internet: bool = True) -> Hashes:
        """Return a hash-comparer that considers my option- and URL-based
        hashes to be known-good.

        Hashes in URLs--ones embedded in the requirements file, not ones
        downloaded from an index server--are almost peers with ones from
        flags. They satisfy --require-hashes (whether it was implicitly or
        explicitly activated) but do not activate it. md5 and sha224 are not
        allowed in flags, which should nudge people toward good algos. We
        always OR all hashes together, even ones from URLs.

        :param trust_internet: Whether to trust URL-based (#md5=...) hashes
            downloaded from the internet, as by populate_link()

        """
        good_hashes = self.hash_options.copy()
        if trust_internet:
            link = self.link
        elif self.is_direct and self.user_supplied:
            link = self.original_link
        else:
            link = None
        if link and link.hash:
            assert link.hash_name is not None
            good_hashes.setdefault(link.hash_name, []).append(link.hash)
        return Hashes(good_hashes)

    def from_path(self) -> Optional[str]:
        """Format a nice indicator to show where this "comes from" """
        if self.req is None:
            return None
        s = str(self.req)
        if self.comes_from:
            comes_from: Optional[str]
            if isinstance(self.comes_from, str):
                comes_from = self.comes_from
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += "->" + comes_from
        return s

    def ensure_build_location(
        self, build_dir: str, autodelete: bool, parallel_builds: bool
    ) -> str:
        assert build_dir is not None
        if self._temp_build_dir is not None:
            assert self._temp_build_dir.path
            return self._temp_build_dir.path
        if self.req is None:
            # Some systems have /tmp as a symlink which confuses custom
            # builds (such as numpy). Thus, we ensure that the real path
            # is returned.
            self._temp_build_dir = TempDirectory(
                kind=tempdir_kinds.REQ_BUILD, globally_managed=True
            )

            return self._temp_build_dir.path

        # This is the only remaining place where we manually determine the path
        # for the temporary directory. It is only needed for editables where
        # it is the value of the --src option.

        # When parallel builds are enabled, add a UUID to the build directory
        # name so multiple builds do not interfere with each other.
        dir_name: str = canonicalize_name(self.req.name)
        if parallel_builds:
            dir_name = f"{dir_name}_{uuid.uuid4().hex}"

        # FIXME: Is there a better place to create the build_dir? (hg and bzr
        # need this)
        if not os.path.exists(build_dir):
            logger.debug("Creating directory %s", build_dir)
            os.makedirs(build_dir)
        actual_build_dir = os.path.join(build_dir, dir_name)
        # `None` indicates that we respect the globally-configured deletion
        # settings, which is what we actually want when auto-deleting.
        delete_arg = None if autodelete else False
        return TempDirectory(
            path=actual_build_dir,
            delete=delete_arg,
            kind=tempdir_kinds.REQ_BUILD,
            globally_managed=True,
        ).path

    def _set_requirement(self) -> None:
        """Set requirement after generating metadata."""
        assert self.req is None
        assert self.metadata is not None
        assert self.source_dir is not None

        # Construct a Requirement object from the generated metadata
        if isinstance(parse_version(self.metadata["Version"]), Version):
            op = "=="
        else:
            op = "==="

        self.req = get_requirement(
            "".join(
                [
                    self.metadata["Name"],
                    op,
                    self.metadata["Version"],
                ]
            )
        )

    def warn_on_mismatching_name(self) -> None:
        assert self.req is not None
        metadata_name = canonicalize_name(self.metadata["Name"])
        if canonicalize_name(self.req.name) == metadata_name:
            # Everything is fine.
            return

        # If we're here, there's a mismatch. Log a warning about it.
        logger.warning(
            "Generating metadata for package %s "
            "produced metadata for project name %s. Fix your "
            "#egg=%s fragments.",
            self.name,
            metadata_name,
            self.name,
        )
        self.req = get_requirement(metadata_name)

    def check_if_exists(self, use_user_site: bool) -> None:
        """Find an installed distribution that satisfies or conflicts
        with this requirement, and set self.satisfied_by or
        self.should_reinstall appropriately.
        """
        if self.req is None:
            return
        existing_dist = get_default_environment().get_distribution(self.req.name)
        if not existing_dist:
            return

        version_compatible = self.req.specifier.contains(
            existing_dist.version,
            prereleases=True,
        )
        if not version_compatible:
            self.satisfied_by = None
            if use_user_site:
                if existing_dist.in_usersite:
                    self.should_reinstall = True
                elif running_under_virtualenv() and existing_dist.in_site_packages:
                    raise InstallationError(
                        f"Will not install to the user site because it will "
                        f"lack sys.path precedence to {existing_dist.raw_name} "
                        f"in {existing_dist.location}"
                    )
            else:
                self.should_reinstall = True
        else:
            if self.editable:
                self.should_reinstall = True
                # when installing editables, nothing pre-existing should ever
                # satisfy
                self.satisfied_by = None
            else:
                self.satisfied_by = existing_dist

    # Things valid for wheels
    @property
    def is_wheel(self) -> bool:
        if not self.link:
            return False
        return self.link.is_wheel

    @property
    def is_wheel_from_cache(self) -> bool:
        # When True, it means that this InstallRequirement is a local wheel file in the
        # cache of locally built wheels.
        return self.cached_wheel_source_link is not None

    # Things valid for sdists
    @property
    def unpacked_source_directory(self) -> str:
        assert self.source_dir, f"No source dir for {self}"
        return os.path.join(
            self.source_dir, self.link and self.link.subdirectory_fragment or ""
        )

    @property
    def setup_py_path(self) -> str:
        assert self.source_dir, f"No source dir for {self}"
        setup_py = os.path.join(self.unpacked_source_directory, "setup.py")

        return setup_py

    @property
    def setup_cfg_path(self) -> str:
        assert self.source_dir, f"No source dir for {self}"
        setup_cfg = os.path.join(self.unpacked_source_directory, "setup.cfg")

        return setup_cfg

    @property
    def pyproject_toml_path(self) -> str:
        assert self.source_dir, f"No source dir for {self}"
        return make_pyproject_path(self.unpacked_source_directory)

    def load_pyproject_toml(self) -> None:
        """Load the pyproject.toml file.

        After calling this routine, all of the attributes related to PEP 517
        processing for this requirement have been set. In particular, the
        use_pep517 attribute can be used to determine whether we should
        follow the PEP 517 or legacy (setup.py) code path.
        """
        pyproject_toml_data = load_pyproject_toml(
            self.use_pep517, self.pyproject_toml_path, self.setup_py_path, str(self)
        )

        if pyproject_toml_data is None:
            assert not self.config_settings
            self.use_pep517 = False
            return

        self.use_pep517 = True
        requires, backend, check, backend_path = pyproject_toml_data
        self.requirements_to_check = check
        self.pyproject_requires = requires
        self.pep517_backend = ConfiguredBuildBackendHookCaller(
            self,
            self.unpacked_source_directory,
            backend,
            backend_path=backend_path,
        )

    def isolated_editable_sanity_check(self) -> None:
        """Check that an editable requirement if valid for use with PEP 517/518.

        This verifies that an editable that has a pyproject.toml either supports PEP 660
        or as a setup.py or a setup.cfg
        """
        if (
            self.editable
            and self.use_pep517
            and not self.supports_pyproject_editable
            and not os.path.isfile(self.setup_py_path)
            and not os.path.isfile(self.setup_cfg_path)
        ):
            raise InstallationError(
                f"Project {self} has a 'pyproject.toml' and its build "
                f"backend is missing the 'build_editable' hook. Since it does not "
                f"have a 'setup.py' nor a 'setup.cfg', "
                f"it cannot be installed in editable mode. "
                f"Consider using a build backend that supports PEP 660."
            )

    def prepare_metadata(self) -> None:
        """Ensure that project metadata is available.

        Under PEP 517 and PEP 660, call the backend hook to prepare the metadata.
        Under legacy processing, call setup.py egg-info.
        """
        assert self.source_dir, f"No source dir for {self}"
        details = self.name or f"from {self.link}"

        if self.use_pep517:
            assert self.pep517_backend is not None
            if (
                self.editable
                and self.permit_editable_wheels
                and self.supports_pyproject_editable
            ):
                self.metadata_directory = generate_editable_metadata(
                    build_env=self.build_env,
                    backend=self.pep517_backend,
                    details=details,
                )
            else:
                self.metadata_directory = generate_metadata(
                    build_env=self.build_env,
                    backend=self.pep517_backend,
                    details=details,
                )
        else:
            self.metadata_directory = generate_metadata_legacy(
                build_env=self.build_env,
                setup_py_path=self.setup_py_path,
                source_dir=self.unpacked_source_directory,
                isolated=self.isolated,
                details=details,
            )

        # Act on the newly generated metadata, based on the name and version.
        if not self.name:
            self._set_requirement()
        else:
            self.warn_on_mismatching_name()

        self.assert_source_matches_version()

    @property
    def metadata(self) -> Any:
        if not hasattr(self, "_metadata"):
            self._metadata = self.get_dist().metadata

        return self._metadata

    def get_dist(self) -> BaseDistribution:
        if self.metadata_directory:
            return get_directory_distribution(self.metadata_directory)
        elif self.local_file_path and self.is_wheel:
            assert self.req is not None
            return get_wheel_distribution(
                FilesystemWheel(self.local_file_path),
                canonicalize_name(self.req.name),
            )
        raise AssertionError(
            f"InstallRequirement {self} has no metadata directory and no wheel: "
            f"can't make a distribution."
        )

    def assert_source_matches_version(self) -> None:
        assert self.source_dir, f"No source dir for {self}"
        version = self.metadata["version"]
        if self.req and self.req.specifier and version not in self.req.specifier:
            logger.warning(
                "Requested %s, but installing version %s",
                self,
                version,
            )
        else:
            logger.debug(
                "Source in %s has version %s, which satisfies requirement %s",
                display_path(self.source_dir),
                version,
                self,
            )

    # For both source distributions and editables
    def ensure_has_source_dir(
        self,
        parent_dir: str,
        autodelete: bool = False,
        parallel_builds: bool = False,
    ) -> None:
        """Ensure that a source_dir is set.

        This will create a temporary build dir if the name of the requirement
        isn't known yet.

        :param parent_dir: The ideal pip parent_dir for the source_dir.
            Generally src_dir for editables and build_dir for sdists.
        :return: self.source_dir
        """
        if self.source_dir is None:
            self.source_dir = self.ensure_build_location(
                parent_dir,
                autodelete=autodelete,
                parallel_builds=parallel_builds,
            )

    def needs_unpacked_archive(self, archive_source: Path) -> None:
        assert self._archive_source is None
        self._archive_source = archive_source

    def ensure_pristine_source_checkout(self) -> None:
        """Ensure the source directory has not yet been built in."""
        assert self.source_dir is not None
        if self._archive_source is not None:
            unpack_file(str(self._archive_source), self.source_dir)
        elif is_installable_dir(self.source_dir):
            # If a checkout exists, it's unwise to keep going.
            # version inconsistencies are logged later, but do not fail
            # the installation.
            raise PreviousBuildDirError(
                f"pip can't proceed with requirements '{self}' due to a "
                f"pre-existing build directory ({self.source_dir}). This is likely "
                "due to a previous installation that failed . pip is "
                "being responsible and not assuming it can delete this. "
                "Please delete it and try again."
            )

    # For editable installations
    def update_editable(self) -> None:
        if not self.link:
            logger.debug(
                "Cannot update repository at %s; repository location is unknown",
                self.source_dir,
            )
            return
        assert self.editable
        assert self.source_dir
        if self.link.scheme == "file":
            # Static paths don't get updated
            return
        vcs_backend = vcs.get_backend_for_scheme(self.link.scheme)
        # Editable requirements are validated in Requirement constructors.
        # So here, if it's neither a path nor a valid VCS URL, it's a bug.
        assert vcs_backend, f"Unsupported VCS URL {self.link.url}"
        hidden_url = hide_url(self.link.url)
        vcs_backend.obtain(self.source_dir, url=hidden_url, verbosity=0)

    # Top-level Actions
    def uninstall(
        self, auto_confirm: bool = False, verbose: bool = False
    ) -> Optional[UninstallPathSet]:
        """
        Uninstall the distribution currently satisfying this requirement.

        Prompts before removing or modifying files unless
        ``auto_confirm`` is True.

        Refuses to delete or modify files outside of ``sys.prefix`` -
        thus uninstallation within a virtual environment can only
        modify that virtual environment, even if the virtualenv is
        linked to global site-packages.

        """
        assert self.req
        dist = get_default_environment().get_distribution(self.req.name)
        if not dist:
            logger.warning("Skipping %s as it is not installed.", self.name)
            return None
        logger.info("Found existing installation: %s", dist)

        uninstalled_pathset = UninstallPathSet.from_dist(dist)
        uninstalled_pathset.remove(auto_confirm, verbose)
        return uninstalled_pathset

    def _get_archive_name(self, path: str, parentdir: str, rootdir: str) -> str:
        def _clean_zip_name(name: str, prefix: str) -> str:
            assert name.startswith(
                prefix + os.path.sep
            ), f"name {name!r} doesn't start with prefix {prefix!r}"
            name = name[len(prefix) + 1 :]
            name = name.replace(os.path.sep, "/")
            return name

        assert self.req is not None
        path = os.path.join(parentdir, path)
        name = _clean_zip_name(path, rootdir)
        return self.req.name + "/" + name

    def archive(self, build_dir: Optional[str]) -> None:
        """Saves archive to provided build_dir.

        Used for saving downloaded VCS requirements as part of `pip download`.
        """
        assert self.source_dir
        if build_dir is None:
            return

        create_archive = True
        archive_name = "{}-{}.zip".format(self.name, self.metadata["version"])
        archive_path = os.path.join(build_dir, archive_name)

        if os.path.exists(archive_path):
            response = ask_path_exists(
                f"The file {display_path(archive_path)} exists. (i)gnore, (w)ipe, "
                "(b)ackup, (a)bort ",
                ("i", "w", "b", "a"),
            )
            if response == "i":
                create_archive = False
            elif response == "w":
                logger.warning("Deleting %s", display_path(archive_path))
                os.remove(archive_path)
            elif response == "b":
                dest_file = backup_dir(archive_path)
                logger.warning(
                    "Backing up %s to %s",
                    display_path(archive_path),
                    display_path(dest_file),
                )
                shutil.move(archive_path, dest_file)
            elif response == "a":
                sys.exit(-1)

        if not create_archive:
            return

        zip_output = zipfile.ZipFile(
            archive_path,
            "w",
            zipfile.ZIP_DEFLATED,
            allowZip64=True,
        )
        with zip_output:
            dir = os.path.normcase(os.path.abspath(self.unpacked_source_directory))
            for dirpath, dirnames, filenames in os.walk(dir):
                for dirname in dirnames:
                    dir_arcname = self._get_archive_name(
                        dirname,
                        parentdir=dirpath,
                        rootdir=dir,
                    )
                    zipdir = zipfile.ZipInfo(dir_arcname + "/")
                    zipdir.external_attr = 0x1ED << 16  # 0o755
                    zip_output.writestr(zipdir, "")
                for filename in filenames:
                    file_arcname = self._get_archive_name(
                        filename,
                        parentdir=dirpath,
                        rootdir=dir,
                    )
                    filename = os.path.join(dirpath, filename)
                    zip_output.write(filename, file_arcname)

        logger.info("Saved %s", display_path(archive_path))

    def install(
        self,
        global_options: Optional[Sequence[str]] = None,
        root: Optional[str] = None,
        home: Optional[str] = None,
        prefix: Optional[str] = None,
        warn_script_location: bool = True,
        use_user_site: bool = False,
        pycompile: bool = True,
    ) -> None:
        assert self.req is not None
        scheme = get_scheme(
            self.req.name,
            user=use_user_site,
            home=home,
            root=root,
            isolated=self.isolated,
            prefix=prefix,
        )

        if self.editable and not self.is_wheel:
            deprecated(
                reason=(
                    f"Legacy editable install of {self} (setup.py develop) "
                    "is deprecated."
                ),
                replacement=(
                    "to add a pyproject.toml or enable --use-pep517, "
                    "and use setuptools >= 64. "
                    "If the resulting installation is not behaving as expected, "
                    "try using --config-settings editable_mode=compat. "
                    "Please consult the setuptools documentation for more information"
                ),
                gone_in="25.1",
                issue=11457,
            )
            if self.config_settings:
                logger.warning(
                    "--config-settings ignored for legacy editable install of %s. "
                    "Consider upgrading to a version of setuptools "
                    "that supports PEP 660 (>= 64).",
                    self,
                )
            install_editable_legacy(
                global_options=global_options if global_options is not None else [],
                prefix=prefix,
                home=home,
                use_user_site=use_user_site,
                name=self.req.name,
                setup_py_path=self.setup_py_path,
                isolated=self.isolated,
                build_env=self.build_env,
                unpacked_source_directory=self.unpacked_source_directory,
            )
            self.install_succeeded = True
            return

        assert self.is_wheel
        assert self.local_file_path

        install_wheel(
            self.req.name,
            self.local_file_path,
            scheme=scheme,
            req_description=str(self.req),
            pycompile=pycompile,
            warn_script_location=warn_script_location,
            direct_url=self.download_info if self.is_direct else None,
            requested=self.user_supplied,
        )
        self.install_succeeded = True


def check_invalid_constraint_type(req: InstallRequirement) -> str:
    # Check for unsupported forms
    problem = ""
    if not req.name:
        problem = "Unnamed requirements are not allowed as constraints"
    elif req.editable:
        problem = "Editable requirements are not allowed as constraints"
    elif req.extras:
        problem = "Constraints cannot have extras"

    if problem:
        deprecated(
            reason=(
                "Constraints are only allowed to take the form of a package "
                "name and a version specifier. Other forms were originally "
                "permitted as an accident of the implementation, but were "
                "undocumented. The new implementation of the resolver no "
                "longer supports these forms."
            ),
            replacement="replacing the constraint with a requirement",
            # No plan yet for when the new resolver becomes default
            gone_in=None,
            issue=8210,
        )

    return problem


def _has_option(options: Values, reqs: List[InstallRequirement], option: str) -> bool:
    if getattr(options, option, None):
        return True
    for req in reqs:
        if getattr(req, option, None):
            return True
    return False


def check_legacy_setup_py_options(
    options: Values,
    reqs: List[InstallRequirement],
) -> None:
    has_build_options = _has_option(options, reqs, "build_options")
    has_global_options = _has_option(options, reqs, "global_options")
    if has_build_options or has_global_options:
        deprecated(
            reason="--build-option and --global-option are deprecated.",
            issue=11859,
            replacement="to use --config-settings",
            gone_in=None,
        )
        logger.warning(
            "Implying --no-binary=:all: due to the presence of "
            "--build-option / --global-option. "
        )
        options.format_control.disallow_binaries()

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\http_sync.py ===
"""This file is largely copied from http.py"""

import io
import logging
import re
import urllib.error
import urllib.parse
from copy import copy
from json import dumps, loads
from urllib.parse import urlparse

try:
    import yarl
except (ImportError, ModuleNotFoundError, OSError):
    yarl = False

from fsspec.callbacks import _DEFAULT_CALLBACK
from fsspec.registry import register_implementation
from fsspec.spec import AbstractBufferedFile, AbstractFileSystem
from fsspec.utils import DEFAULT_BLOCK_SIZE, isfilelike, nullcontext, tokenize

from ..caching import AllBytes

# https://stackoverflow.com/a/15926317/3821154
ex = re.compile(r"""<(a|A)\s+(?:[^>]*?\s+)?(href|HREF)=["'](?P<url>[^"']+)""")
ex2 = re.compile(r"""(?P<url>http[s]?://[-a-zA-Z0-9@:%_+.~#?&/=]+)""")
logger = logging.getLogger("fsspec.http")


class JsHttpException(urllib.error.HTTPError): ...


class StreamIO(io.BytesIO):
    # fake class, so you can set attributes on it
    # will eventually actually stream
    ...


class ResponseProxy:
    """Looks like a requests response"""

    def __init__(self, req, stream=False):
        self.request = req
        self.stream = stream
        self._data = None
        self._headers = None

    @property
    def raw(self):
        if self._data is None:
            b = self.request.response.to_bytes()
            if self.stream:
                self._data = StreamIO(b)
            else:
                self._data = b
        return self._data

    def close(self):
        if hasattr(self, "_data"):
            del self._data

    @property
    def headers(self):
        if self._headers is None:
            self._headers = dict(
                [
                    _.split(": ")
                    for _ in self.request.getAllResponseHeaders().strip().split("\r\n")
                ]
            )
        return self._headers

    @property
    def status_code(self):
        return int(self.request.status)

    def raise_for_status(self):
        if not self.ok:
            raise JsHttpException(
                self.url, self.status_code, self.reason, self.headers, None
            )

    def iter_content(self, chunksize, *_, **__):
        while True:
            out = self.raw.read(chunksize)
            if out:
                yield out
            else:
                break

    @property
    def reason(self):
        return self.request.statusText

    @property
    def ok(self):
        return self.status_code < 400

    @property
    def url(self):
        return self.request.response.responseURL

    @property
    def text(self):
        # TODO: encoding from headers
        return self.content.decode()

    @property
    def content(self):
        self.stream = False
        return self.raw

    def json(self):
        return loads(self.text)


class RequestsSessionShim:
    def __init__(self):
        self.headers = {}

    def request(
        self,
        method,
        url,
        params=None,
        data=None,
        headers=None,
        cookies=None,
        files=None,
        auth=None,
        timeout=None,
        allow_redirects=None,
        proxies=None,
        hooks=None,
        stream=None,
        verify=None,
        cert=None,
        json=None,
    ):
        from js import Blob, XMLHttpRequest

        logger.debug("JS request: %s %s", method, url)

        if cert or verify or proxies or files or cookies or hooks:
            raise NotImplementedError
        if data and json:
            raise ValueError("Use json= or data=, not both")
        req = XMLHttpRequest.new()
        extra = auth if auth else ()
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        req.open(method, url, False, *extra)
        if timeout:
            req.timeout = timeout
        if headers:
            for k, v in headers.items():
                req.setRequestHeader(k, v)

        req.setRequestHeader("Accept", "application/octet-stream")
        req.responseType = "arraybuffer"
        if json:
            blob = Blob.new([dumps(data)], {type: "application/json"})
            req.send(blob)
        elif data:
            if isinstance(data, io.IOBase):
                data = data.read()
            blob = Blob.new([data], {type: "application/octet-stream"})
            req.send(blob)
        else:
            req.send(None)
        return ResponseProxy(req, stream=stream)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def head(self, url, **kwargs):
        return self.request("HEAD", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST}", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)


class HTTPFileSystem(AbstractFileSystem):
    """
    Simple File-System for fetching data via HTTP(S)

    This is the BLOCKING version of the normal HTTPFileSystem. It uses
    requests in normal python and the JS runtime in pyodide.

    ***This implementation is extremely experimental, do not use unless
    you are testing pyodide/pyscript integration***
    """

    protocol = ("http", "https", "sync-http", "sync-https")
    sep = "/"

    def __init__(
        self,
        simple_links=True,
        block_size=None,
        same_scheme=True,
        cache_type="readahead",
        cache_options=None,
        client_kwargs=None,
        encoded=False,
        **storage_options,
    ):
        """

        Parameters
        ----------
        block_size: int
            Blocks to read bytes; if 0, will default to raw requests file-like
            objects instead of HTTPFile instances
        simple_links: bool
            If True, will consider both HTML <a> tags and anything that looks
            like a URL; if False, will consider only the former.
        same_scheme: True
            When doing ls/glob, if this is True, only consider paths that have
            http/https matching the input URLs.
        size_policy: this argument is deprecated
        client_kwargs: dict
            Passed to aiohttp.ClientSession, see
            https://docs.aiohttp.org/en/stable/client_reference.html
            For example, ``{'auth': aiohttp.BasicAuth('user', 'pass')}``
        storage_options: key-value
            Any other parameters passed on to requests
        cache_type, cache_options: defaults used in open
        """
        super().__init__(self, **storage_options)
        self.block_size = block_size if block_size is not None else DEFAULT_BLOCK_SIZE
        self.simple_links = simple_links
        self.same_schema = same_scheme
        self.cache_type = cache_type
        self.cache_options = cache_options
        self.client_kwargs = client_kwargs or {}
        self.encoded = encoded
        self.kwargs = storage_options

        try:
            import js  # noqa: F401

            logger.debug("Starting JS session")
            self.session = RequestsSessionShim()
            self.js = True
        except Exception as e:
            import requests

            logger.debug("Starting cpython session because of: %s", e)
            self.session = requests.Session(**(client_kwargs or {}))
            self.js = False

        request_options = copy(storage_options)
        self.use_listings_cache = request_options.pop("use_listings_cache", False)
        request_options.pop("listings_expiry_time", None)
        request_options.pop("max_paths", None)
        request_options.pop("skip_instance_cache", None)
        self.kwargs = request_options

    @property
    def fsid(self):
        return "sync-http"

    def encode_url(self, url):
        if yarl:
            return yarl.URL(url, encoded=self.encoded)
        return url

    @classmethod
    def _strip_protocol(cls, path: str) -> str:
        """For HTTP, we always want to keep the full URL"""
        path = path.replace("sync-http://", "http://").replace(
            "sync-https://", "https://"
        )
        return path

    @classmethod
    def _parent(cls, path):
        # override, since _strip_protocol is different for URLs
        par = super()._parent(path)
        if len(par) > 7:  # "http://..."
            return par
        return ""

    def _ls_real(self, url, detail=True, **kwargs):
        # ignoring URL-encoded arguments
        kw = self.kwargs.copy()
        kw.update(kwargs)
        logger.debug(url)
        r = self.session.get(self.encode_url(url), **self.kwargs)
        self._raise_not_found_for_status(r, url)
        text = r.text
        if self.simple_links:
            links = ex2.findall(text) + [u[2] for u in ex.findall(text)]
        else:
            links = [u[2] for u in ex.findall(text)]
        out = set()
        parts = urlparse(url)
        for l in links:
            if isinstance(l, tuple):
                l = l[1]
            if l.startswith("/") and len(l) > 1:
                # absolute URL on this server
                l = parts.scheme + "://" + parts.netloc + l
            if l.startswith("http"):
                if self.same_schema and l.startswith(url.rstrip("/") + "/"):
                    out.add(l)
                elif l.replace("https", "http").startswith(
                    url.replace("https", "http").rstrip("/") + "/"
                ):
                    # allowed to cross http <-> https
                    out.add(l)
            else:
                if l not in ["..", "../"]:
                    # Ignore FTP-like "parent"
                    out.add("/".join([url.rstrip("/"), l.lstrip("/")]))
        if not out and url.endswith("/"):
            out = self._ls_real(url.rstrip("/"), detail=False)
        if detail:
            return [
                {
                    "name": u,
                    "size": None,
                    "type": "directory" if u.endswith("/") else "file",
                }
                for u in out
            ]
        else:
            return sorted(out)

    def ls(self, url, detail=True, **kwargs):
        if self.use_listings_cache and url in self.dircache:
            out = self.dircache[url]
        else:
            out = self._ls_real(url, detail=detail, **kwargs)
            self.dircache[url] = out
        return out

    def _raise_not_found_for_status(self, response, url):
        """
        Raises FileNotFoundError for 404s, otherwise uses raise_for_status.
        """
        if response.status_code == 404:
            raise FileNotFoundError(url)
        response.raise_for_status()

    def cat_file(self, url, start=None, end=None, **kwargs):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        logger.debug(url)

        if start is not None or end is not None:
            if start == end:
                return b""
            headers = kw.pop("headers", {}).copy()

            headers["Range"] = self._process_limits(url, start, end)
            kw["headers"] = headers
        r = self.session.get(self.encode_url(url), **kw)
        self._raise_not_found_for_status(r, url)
        return r.content

    def get_file(
        self, rpath, lpath, chunk_size=5 * 2**20, callback=_DEFAULT_CALLBACK, **kwargs
    ):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        logger.debug(rpath)
        r = self.session.get(self.encode_url(rpath), **kw)
        try:
            size = int(
                r.headers.get("content-length", None)
                or r.headers.get("Content-Length", None)
            )
        except (ValueError, KeyError, TypeError):
            size = None

        callback.set_size(size)
        self._raise_not_found_for_status(r, rpath)
        if not isfilelike(lpath):
            lpath = open(lpath, "wb")
        for chunk in r.iter_content(chunk_size, decode_unicode=False):
            lpath.write(chunk)
            callback.relative_update(len(chunk))

    def put_file(
        self,
        lpath,
        rpath,
        chunk_size=5 * 2**20,
        callback=_DEFAULT_CALLBACK,
        method="post",
        **kwargs,
    ):
        def gen_chunks():
            # Support passing arbitrary file-like objects
            # and use them instead of streams.
            if isinstance(lpath, io.IOBase):
                context = nullcontext(lpath)
                use_seek = False  # might not support seeking
            else:
                context = open(lpath, "rb")
                use_seek = True

            with context as f:
                if use_seek:
                    callback.set_size(f.seek(0, 2))
                    f.seek(0)
                else:
                    callback.set_size(getattr(f, "size", None))

                chunk = f.read(chunk_size)
                while chunk:
                    yield chunk
                    callback.relative_update(len(chunk))
                    chunk = f.read(chunk_size)

        kw = self.kwargs.copy()
        kw.update(kwargs)

        method = method.lower()
        if method not in ("post", "put"):
            raise ValueError(
                f"method has to be either 'post' or 'put', not: {method!r}"
            )

        meth = getattr(self.session, method)
        resp = meth(rpath, data=gen_chunks(), **kw)
        self._raise_not_found_for_status(resp, rpath)

    def _process_limits(self, url, start, end):
        """Helper for "Range"-based _cat_file"""
        size = None
        suff = False
        if start is not None and start < 0:
            # if start is negative and end None, end is the "suffix length"
            if end is None:
                end = -start
                start = ""
                suff = True
            else:
                size = size or self.info(url)["size"]
                start = size + start
        elif start is None:
            start = 0
        if not suff:
            if end is not None and end < 0:
                if start is not None:
                    size = size or self.info(url)["size"]
                    end = size + end
            elif end is None:
                end = ""
            if isinstance(end, int):
                end -= 1  # bytes range is inclusive
        return f"bytes={start}-{end}"

    def exists(self, path, **kwargs):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        try:
            logger.debug(path)
            r = self.session.get(self.encode_url(path), **kw)
            return r.status_code < 400
        except Exception:
            return False

    def isfile(self, path, **kwargs):
        return self.exists(path, **kwargs)

    def _open(
        self,
        path,
        mode="rb",
        block_size=None,
        autocommit=None,  # XXX: This differs from the base class.
        cache_type=None,
        cache_options=None,
        size=None,
        **kwargs,
    ):
        """Make a file-like object

        Parameters
        ----------
        path: str
            Full URL with protocol
        mode: string
            must be "rb"
        block_size: int or None
            Bytes to download in one request; use instance value if None. If
            zero, will return a streaming Requests file-like instance.
        kwargs: key-value
            Any other parameters, passed to requests calls
        """
        if mode != "rb":
            raise NotImplementedError
        block_size = block_size if block_size is not None else self.block_size
        kw = self.kwargs.copy()
        kw.update(kwargs)
        size = size or self.info(path, **kwargs)["size"]
        if block_size and size:
            return HTTPFile(
                self,
                path,
                session=self.session,
                block_size=block_size,
                mode=mode,
                size=size,
                cache_type=cache_type or self.cache_type,
                cache_options=cache_options or self.cache_options,
                **kw,
            )
        else:
            return HTTPStreamFile(
                self,
                path,
                mode=mode,
                session=self.session,
                **kw,
            )

    def ukey(self, url):
        """Unique identifier; assume HTTP files are static, unchanging"""
        return tokenize(url, self.kwargs, self.protocol)

    def info(self, url, **kwargs):
        """Get info of URL

        Tries to access location via HEAD, and then GET methods, but does
        not fetch the data.

        It is possible that the server does not supply any size information, in
        which case size will be given as None (and certain operations on the
        corresponding file will not work).
        """
        info = {}
        for policy in ["head", "get"]:
            try:
                info.update(
                    _file_info(
                        self.encode_url(url),
                        size_policy=policy,
                        session=self.session,
                        **self.kwargs,
                        **kwargs,
                    )
                )
                if info.get("size") is not None:
                    break
            except Exception as exc:
                if policy == "get":
                    # If get failed, then raise a FileNotFoundError
                    raise FileNotFoundError(url) from exc
                logger.debug(str(exc))

        return {"name": url, "size": None, **info, "type": "file"}

    def glob(self, path, maxdepth=None, **kwargs):
        """
        Find files by glob-matching.

        This implementation is idntical to the one in AbstractFileSystem,
        but "?" is not considered as a character for globbing, because it is
        so common in URLs, often identifying the "query" part.
        """
        import re

        ends = path.endswith("/")
        path = self._strip_protocol(path)
        indstar = path.find("*") if path.find("*") >= 0 else len(path)
        indbrace = path.find("[") if path.find("[") >= 0 else len(path)

        ind = min(indstar, indbrace)

        detail = kwargs.pop("detail", False)

        if not has_magic(path):
            root = path
            depth = 1
            if ends:
                path += "/*"
            elif self.exists(path):
                if not detail:
                    return [path]
                else:
                    return {path: self.info(path)}
            else:
                if not detail:
                    return []  # glob of non-existent returns empty
                else:
                    return {}
        elif "/" in path[:ind]:
            ind2 = path[:ind].rindex("/")
            root = path[: ind2 + 1]
            depth = None if "**" in path else path[ind2 + 1 :].count("/") + 1
        else:
            root = ""
            depth = None if "**" in path else path[ind + 1 :].count("/") + 1

        allpaths = self.find(
            root, maxdepth=maxdepth or depth, withdirs=True, detail=True, **kwargs
        )
        # Escape characters special to python regex, leaving our supported
        # special characters in place.
        # See https://www.gnu.org/software/bash/manual/html_node/Pattern-Matching.html
        # for shell globbing details.
        pattern = (
            "^"
            + (
                path.replace("\\", r"\\")
                .replace(".", r"\.")
                .replace("+", r"\+")
                .replace("//", "/")
                .replace("(", r"\(")
                .replace(")", r"\)")
                .replace("|", r"\|")
                .replace("^", r"\^")
                .replace("$", r"\$")
                .replace("{", r"\{")
                .replace("}", r"\}")
                .rstrip("/")
            )
            + "$"
        )
        pattern = re.sub("[*]{2}", "=PLACEHOLDER=", pattern)
        pattern = re.sub("[*]", "[^/]*", pattern)
        pattern = re.compile(pattern.replace("=PLACEHOLDER=", ".*"))
        out = {
            p: allpaths[p]
            for p in sorted(allpaths)
            if pattern.match(p.replace("//", "/").rstrip("/"))
        }
        if detail:
            return out
        else:
            return list(out)

    def isdir(self, path):
        # override, since all URLs are (also) files
        try:
            return bool(self.ls(path))
        except (FileNotFoundError, ValueError):
            return False


class HTTPFile(AbstractBufferedFile):
    """
    A file-like object pointing to a remove HTTP(S) resource

    Supports only reading, with read-ahead of a predermined block-size.

    In the case that the server does not supply the filesize, only reading of
    the complete file in one go is supported.

    Parameters
    ----------
    url: str
        Full URL of the remote resource, including the protocol
    session: requests.Session or None
        All calls will be made within this session, to avoid restarting
        connections where the server allows this
    block_size: int or None
        The amount of read-ahead to do, in bytes. Default is 5MB, or the value
        configured for the FileSystem creating this file
    size: None or int
        If given, this is the size of the file in bytes, and we don't attempt
        to call the server to find the value.
    kwargs: all other key-values are passed to requests calls.
    """

    def __init__(
        self,
        fs,
        url,
        session=None,
        block_size=None,
        mode="rb",
        cache_type="bytes",
        cache_options=None,
        size=None,
        **kwargs,
    ):
        if mode != "rb":
            raise NotImplementedError("File mode not supported")
        self.url = url
        self.session = session
        self.details = {"name": url, "size": size, "type": "file"}
        super().__init__(
            fs=fs,
            path=url,
            mode=mode,
            block_size=block_size,
            cache_type=cache_type,
            cache_options=cache_options,
            **kwargs,
        )

    def read(self, length=-1):
        """Read bytes from file

        Parameters
        ----------
        length: int
            Read up to this many bytes. If negative, read all content to end of
            file. If the server has not supplied the filesize, attempting to
            read only part of the data will raise a ValueError.
        """
        if (
            (length < 0 and self.loc == 0)  # explicit read all
            # but not when the size is known and fits into a block anyways
            and not (self.size is not None and self.size <= self.blocksize)
        ):
            self._fetch_all()
        if self.size is None:
            if length < 0:
                self._fetch_all()
        else:
            length = min(self.size - self.loc, length)
        return super().read(length)

    def _fetch_all(self):
        """Read whole file in one shot, without caching

        This is only called when position is still at zero,
        and read() is called without a byte-count.
        """
        logger.debug(f"Fetch all for {self}")
        if not isinstance(self.cache, AllBytes):
            r = self.session.get(self.fs.encode_url(self.url), **self.kwargs)
            r.raise_for_status()
            out = r.content
            self.cache = AllBytes(size=len(out), fetcher=None, blocksize=None, data=out)
            self.size = len(out)

    def _parse_content_range(self, headers):
        """Parse the Content-Range header"""
        s = headers.get("Content-Range", "")
        m = re.match(r"bytes (\d+-\d+|\*)/(\d+|\*)", s)
        if not m:
            return None, None, None

        if m[1] == "*":
            start = end = None
        else:
            start, end = [int(x) for x in m[1].split("-")]
        total = None if m[2] == "*" else int(m[2])
        return start, end, total

    def _fetch_range(self, start, end):
        """Download a block of data

        The expectation is that the server returns only the requested bytes,
        with HTTP code 206. If this is not the case, we first check the headers,
        and then stream the output - if the data size is bigger than we
        requested, an exception is raised.
        """
        logger.debug(f"Fetch range for {self}: {start}-{end}")
        kwargs = self.kwargs.copy()
        headers = kwargs.pop("headers", {}).copy()
        headers["Range"] = f"bytes={start}-{end - 1}"
        logger.debug("%s : %s", self.url, headers["Range"])
        r = self.session.get(self.fs.encode_url(self.url), headers=headers, **kwargs)
        if r.status_code == 416:
            # range request outside file
            return b""
        r.raise_for_status()

        # If the server has handled the range request, it should reply
        # with status 206 (partial content). But we'll guess that a suitable
        # Content-Range header or a Content-Length no more than the
        # requested range also mean we have got the desired range.
        cl = r.headers.get("Content-Length", r.headers.get("content-length", end + 1))
        response_is_range = (
            r.status_code == 206
            or self._parse_content_range(r.headers)[0] == start
            or int(cl) <= end - start
        )

        if response_is_range:
            # partial content, as expected
            out = r.content
        elif start > 0:
            raise ValueError(
                "The HTTP server doesn't appear to support range requests. "
                "Only reading this file from the beginning is supported. "
                "Open with block_size=0 for a streaming file interface."
            )
        else:
            # Response is not a range, but we want the start of the file,
            # so we can read the required amount anyway.
            cl = 0
            out = []
            for chunk in r.iter_content(2**20, False):
                out.append(chunk)
                cl += len(chunk)
            out = b"".join(out)[: end - start]
        return out


magic_check = re.compile("([*[])")


def has_magic(s):
    match = magic_check.search(s)
    return match is not None


class HTTPStreamFile(AbstractBufferedFile):
    def __init__(self, fs, url, mode="rb", session=None, **kwargs):
        self.url = url
        self.session = session
        if mode != "rb":
            raise ValueError
        self.details = {"name": url, "size": None}
        super().__init__(fs=fs, path=url, mode=mode, cache_type="readahead", **kwargs)

        r = self.session.get(self.fs.encode_url(url), stream=True, **kwargs)
        self.fs._raise_not_found_for_status(r, url)
        self.it = r.iter_content(1024, False)
        self.leftover = b""

        self.r = r

    def seek(self, *args, **kwargs):
        raise ValueError("Cannot seek streaming HTTP file")

    def read(self, num=-1):
        bufs = [self.leftover]
        leng = len(self.leftover)
        while leng < num or num < 0:
            try:
                out = self.it.__next__()
            except StopIteration:
                break
            if out:
                bufs.append(out)
            else:
                break
            leng += len(out)
        out = b"".join(bufs)
        if num >= 0:
            self.leftover = out[num:]
            out = out[:num]
        else:
            self.leftover = b""
        self.loc += len(out)
        return out

    def close(self):
        self.r.close()
        self.closed = True


def get_range(session, url, start, end, **kwargs):
    # explicit get a range when we know it must be safe
    kwargs = kwargs.copy()
    headers = kwargs.pop("headers", {}).copy()
    headers["Range"] = f"bytes={start}-{end - 1}"
    r = session.get(url, headers=headers, **kwargs)
    r.raise_for_status()
    return r.content


def _file_info(url, session, size_policy="head", **kwargs):
    """Call HEAD on the server to get details about the file (size/checksum etc.)

    Default operation is to explicitly allow redirects and use encoding
    'identity' (no compression) to get the true size of the target.
    """
    logger.debug("Retrieve file size for %s", url)
    kwargs = kwargs.copy()
    ar = kwargs.pop("allow_redirects", True)
    head = kwargs.get("headers", {}).copy()
    # TODO: not allowed in JS
    # head["Accept-Encoding"] = "identity"
    kwargs["headers"] = head

    info = {}
    if size_policy == "head":
        r = session.head(url, allow_redirects=ar, **kwargs)
    elif size_policy == "get":
        r = session.get(url, allow_redirects=ar, **kwargs)
    else:
        raise TypeError(f'size_policy must be "head" or "get", got {size_policy}')
    r.raise_for_status()

    # TODO:
    #  recognise lack of 'Accept-Ranges',
    #                 or 'Accept-Ranges': 'none' (not 'bytes')
    #  to mean streaming only, no random access => return None
    if "Content-Length" in r.headers:
        info["size"] = int(r.headers["Content-Length"])
    elif "Content-Range" in r.headers:
        info["size"] = int(r.headers["Content-Range"].split("/")[1])
    elif "content-length" in r.headers:
        info["size"] = int(r.headers["content-length"])
    elif "content-range" in r.headers:
        info["size"] = int(r.headers["content-range"].split("/")[1])

    for checksum_field in ["ETag", "Content-MD5", "Digest"]:
        if r.headers.get(checksum_field):
            info[checksum_field] = r.headers[checksum_field]

    return info


# importing this is enough to register it
def register():
    register_implementation("http", HTTPFileSystem, clobber=True)
    register_implementation("https", HTTPFileSystem, clobber=True)
    register_implementation("sync-http", HTTPFileSystem, clobber=True)
    register_implementation("sync-https", HTTPFileSystem, clobber=True)


register()


def unregister():
    from fsspec.implementations.http import HTTPFileSystem

    register_implementation("http", HTTPFileSystem, clobber=True)
    register_implementation("https", HTTPFileSystem, clobber=True)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\msgpack\fallback.py ===
"""Fallback pure Python implementation of msgpack"""

import struct
import sys
from datetime import datetime as _DateTime

if hasattr(sys, "pypy_version_info"):
    from __pypy__ import newlist_hint
    from __pypy__.builders import BytesBuilder

    _USING_STRINGBUILDER = True

    class BytesIO:
        def __init__(self, s=b""):
            if s:
                self.builder = BytesBuilder(len(s))
                self.builder.append(s)
            else:
                self.builder = BytesBuilder()

        def write(self, s):
            if isinstance(s, memoryview):
                s = s.tobytes()
            elif isinstance(s, bytearray):
                s = bytes(s)
            self.builder.append(s)

        def getvalue(self):
            return self.builder.build()

else:
    from io import BytesIO

    _USING_STRINGBUILDER = False

    def newlist_hint(size):
        return []


from .exceptions import BufferFull, ExtraData, FormatError, OutOfData, StackError
from .ext import ExtType, Timestamp

EX_SKIP = 0
EX_CONSTRUCT = 1
EX_READ_ARRAY_HEADER = 2
EX_READ_MAP_HEADER = 3

TYPE_IMMEDIATE = 0
TYPE_ARRAY = 1
TYPE_MAP = 2
TYPE_RAW = 3
TYPE_BIN = 4
TYPE_EXT = 5

DEFAULT_RECURSE_LIMIT = 511


def _check_type_strict(obj, t, type=type, tuple=tuple):
    if type(t) is tuple:
        return type(obj) in t
    else:
        return type(obj) is t


def _get_data_from_buffer(obj):
    view = memoryview(obj)
    if view.itemsize != 1:
        raise ValueError("cannot unpack from multi-byte object")
    return view


def unpackb(packed, **kwargs):
    """
    Unpack an object from `packed`.

    Raises ``ExtraData`` when *packed* contains extra bytes.
    Raises ``ValueError`` when *packed* is incomplete.
    Raises ``FormatError`` when *packed* is not valid msgpack.
    Raises ``StackError`` when *packed* contains too nested.
    Other exceptions can be raised during unpacking.

    See :class:`Unpacker` for options.
    """
    unpacker = Unpacker(None, max_buffer_size=len(packed), **kwargs)
    unpacker.feed(packed)
    try:
        ret = unpacker._unpack()
    except OutOfData:
        raise ValueError("Unpack failed: incomplete input")
    except RecursionError:
        raise StackError
    if unpacker._got_extradata():
        raise ExtraData(ret, unpacker._get_extradata())
    return ret


_NO_FORMAT_USED = ""
_MSGPACK_HEADERS = {
    0xC4: (1, _NO_FORMAT_USED, TYPE_BIN),
    0xC5: (2, ">H", TYPE_BIN),
    0xC6: (4, ">I", TYPE_BIN),
    0xC7: (2, "Bb", TYPE_EXT),
    0xC8: (3, ">Hb", TYPE_EXT),
    0xC9: (5, ">Ib", TYPE_EXT),
    0xCA: (4, ">f"),
    0xCB: (8, ">d"),
    0xCC: (1, _NO_FORMAT_USED),
    0xCD: (2, ">H"),
    0xCE: (4, ">I"),
    0xCF: (8, ">Q"),
    0xD0: (1, "b"),
    0xD1: (2, ">h"),
    0xD2: (4, ">i"),
    0xD3: (8, ">q"),
    0xD4: (1, "b1s", TYPE_EXT),
    0xD5: (2, "b2s", TYPE_EXT),
    0xD6: (4, "b4s", TYPE_EXT),
    0xD7: (8, "b8s", TYPE_EXT),
    0xD8: (16, "b16s", TYPE_EXT),
    0xD9: (1, _NO_FORMAT_USED, TYPE_RAW),
    0xDA: (2, ">H", TYPE_RAW),
    0xDB: (4, ">I", TYPE_RAW),
    0xDC: (2, ">H", TYPE_ARRAY),
    0xDD: (4, ">I", TYPE_ARRAY),
    0xDE: (2, ">H", TYPE_MAP),
    0xDF: (4, ">I", TYPE_MAP),
}


class Unpacker:
    """Streaming unpacker.

    Arguments:

    :param file_like:
        File-like object having `.read(n)` method.
        If specified, unpacker reads serialized data from it and `.feed()` is not usable.

    :param int read_size:
        Used as `file_like.read(read_size)`. (default: `min(16*1024, max_buffer_size)`)

    :param bool use_list:
        If true, unpack msgpack array to Python list.
        Otherwise, unpack to Python tuple. (default: True)

    :param bool raw:
        If true, unpack msgpack raw to Python bytes.
        Otherwise, unpack to Python str by decoding with UTF-8 encoding (default).

    :param int timestamp:
        Control how timestamp type is unpacked:

            0 - Timestamp
            1 - float  (Seconds from the EPOCH)
            2 - int  (Nanoseconds from the EPOCH)
            3 - datetime.datetime  (UTC).

    :param bool strict_map_key:
        If true (default), only str or bytes are accepted for map (dict) keys.

    :param object_hook:
        When specified, it should be callable.
        Unpacker calls it with a dict argument after unpacking msgpack map.
        (See also simplejson)

    :param object_pairs_hook:
        When specified, it should be callable.
        Unpacker calls it with a list of key-value pairs after unpacking msgpack map.
        (See also simplejson)

    :param str unicode_errors:
        The error handler for decoding unicode. (default: 'strict')
        This option should be used only when you have msgpack data which
        contains invalid UTF-8 string.

    :param int max_buffer_size:
        Limits size of data waiting unpacked.  0 means 2**32-1.
        The default value is 100*1024*1024 (100MiB).
        Raises `BufferFull` exception when it is insufficient.
        You should set this parameter when unpacking data from untrusted source.

    :param int max_str_len:
        Deprecated, use *max_buffer_size* instead.
        Limits max length of str. (default: max_buffer_size)

    :param int max_bin_len:
        Deprecated, use *max_buffer_size* instead.
        Limits max length of bin. (default: max_buffer_size)

    :param int max_array_len:
        Limits max length of array.
        (default: max_buffer_size)

    :param int max_map_len:
        Limits max length of map.
        (default: max_buffer_size//2)

    :param int max_ext_len:
        Deprecated, use *max_buffer_size* instead.
        Limits max size of ext type.  (default: max_buffer_size)

    Example of streaming deserialize from file-like object::

        unpacker = Unpacker(file_like)
        for o in unpacker:
            process(o)

    Example of streaming deserialize from socket::

        unpacker = Unpacker()
        while True:
            buf = sock.recv(1024**2)
            if not buf:
                break
            unpacker.feed(buf)
            for o in unpacker:
                process(o)

    Raises ``ExtraData`` when *packed* contains extra bytes.
    Raises ``OutOfData`` when *packed* is incomplete.
    Raises ``FormatError`` when *packed* is not valid msgpack.
    Raises ``StackError`` when *packed* contains too nested.
    Other exceptions can be raised during unpacking.
    """

    def __init__(
        self,
        file_like=None,
        *,
        read_size=0,
        use_list=True,
        raw=False,
        timestamp=0,
        strict_map_key=True,
        object_hook=None,
        object_pairs_hook=None,
        list_hook=None,
        unicode_errors=None,
        max_buffer_size=100 * 1024 * 1024,
        ext_hook=ExtType,
        max_str_len=-1,
        max_bin_len=-1,
        max_array_len=-1,
        max_map_len=-1,
        max_ext_len=-1,
    ):
        if unicode_errors is None:
            unicode_errors = "strict"

        if file_like is None:
            self._feeding = True
        else:
            if not callable(file_like.read):
                raise TypeError("`file_like.read` must be callable")
            self.file_like = file_like
            self._feeding = False

        #: array of bytes fed.
        self._buffer = bytearray()
        #: Which position we currently reads
        self._buff_i = 0

        # When Unpacker is used as an iterable, between the calls to next(),
        # the buffer is not "consumed" completely, for efficiency sake.
        # Instead, it is done sloppily.  To make sure we raise BufferFull at
        # the correct moments, we have to keep track of how sloppy we were.
        # Furthermore, when the buffer is incomplete (that is: in the case
        # we raise an OutOfData) we need to rollback the buffer to the correct
        # state, which _buf_checkpoint records.
        self._buf_checkpoint = 0

        if not max_buffer_size:
            max_buffer_size = 2**31 - 1
        if max_str_len == -1:
            max_str_len = max_buffer_size
        if max_bin_len == -1:
            max_bin_len = max_buffer_size
        if max_array_len == -1:
            max_array_len = max_buffer_size
        if max_map_len == -1:
            max_map_len = max_buffer_size // 2
        if max_ext_len == -1:
            max_ext_len = max_buffer_size

        self._max_buffer_size = max_buffer_size
        if read_size > self._max_buffer_size:
            raise ValueError("read_size must be smaller than max_buffer_size")
        self._read_size = read_size or min(self._max_buffer_size, 16 * 1024)
        self._raw = bool(raw)
        self._strict_map_key = bool(strict_map_key)
        self._unicode_errors = unicode_errors
        self._use_list = use_list
        if not (0 <= timestamp <= 3):
            raise ValueError("timestamp must be 0..3")
        self._timestamp = timestamp
        self._list_hook = list_hook
        self._object_hook = object_hook
        self._object_pairs_hook = object_pairs_hook
        self._ext_hook = ext_hook
        self._max_str_len = max_str_len
        self._max_bin_len = max_bin_len
        self._max_array_len = max_array_len
        self._max_map_len = max_map_len
        self._max_ext_len = max_ext_len
        self._stream_offset = 0

        if list_hook is not None and not callable(list_hook):
            raise TypeError("`list_hook` is not callable")
        if object_hook is not None and not callable(object_hook):
            raise TypeError("`object_hook` is not callable")
        if object_pairs_hook is not None and not callable(object_pairs_hook):
            raise TypeError("`object_pairs_hook` is not callable")
        if object_hook is not None and object_pairs_hook is not None:
            raise TypeError("object_pairs_hook and object_hook are mutually exclusive")
        if not callable(ext_hook):
            raise TypeError("`ext_hook` is not callable")

    def feed(self, next_bytes):
        assert self._feeding
        view = _get_data_from_buffer(next_bytes)
        if len(self._buffer) - self._buff_i + len(view) > self._max_buffer_size:
            raise BufferFull

        # Strip buffer before checkpoint before reading file.
        if self._buf_checkpoint > 0:
            del self._buffer[: self._buf_checkpoint]
            self._buff_i -= self._buf_checkpoint
            self._buf_checkpoint = 0

        # Use extend here: INPLACE_ADD += doesn't reliably typecast memoryview in jython
        self._buffer.extend(view)
        view.release()

    def _consume(self):
        """Gets rid of the used parts of the buffer."""
        self._stream_offset += self._buff_i - self._buf_checkpoint
        self._buf_checkpoint = self._buff_i

    def _got_extradata(self):
        return self._buff_i < len(self._buffer)

    def _get_extradata(self):
        return self._buffer[self._buff_i :]

    def read_bytes(self, n):
        ret = self._read(n, raise_outofdata=False)
        self._consume()
        return ret

    def _read(self, n, raise_outofdata=True):
        # (int) -> bytearray
        self._reserve(n, raise_outofdata=raise_outofdata)
        i = self._buff_i
        ret = self._buffer[i : i + n]
        self._buff_i = i + len(ret)
        return ret

    def _reserve(self, n, raise_outofdata=True):
        remain_bytes = len(self._buffer) - self._buff_i - n

        # Fast path: buffer has n bytes already
        if remain_bytes >= 0:
            return

        if self._feeding:
            self._buff_i = self._buf_checkpoint
            raise OutOfData

        # Strip buffer before checkpoint before reading file.
        if self._buf_checkpoint > 0:
            del self._buffer[: self._buf_checkpoint]
            self._buff_i -= self._buf_checkpoint
            self._buf_checkpoint = 0

        # Read from file
        remain_bytes = -remain_bytes
        if remain_bytes + len(self._buffer) > self._max_buffer_size:
            raise BufferFull
        while remain_bytes > 0:
            to_read_bytes = max(self._read_size, remain_bytes)
            read_data = self.file_like.read(to_read_bytes)
            if not read_data:
                break
            assert isinstance(read_data, bytes)
            self._buffer += read_data
            remain_bytes -= len(read_data)

        if len(self._buffer) < n + self._buff_i and raise_outofdata:
            self._buff_i = 0  # rollback
            raise OutOfData

    def _read_header(self):
        typ = TYPE_IMMEDIATE
        n = 0
        obj = None
        self._reserve(1)
        b = self._buffer[self._buff_i]
        self._buff_i += 1
        if b & 0b10000000 == 0:
            obj = b
        elif b & 0b11100000 == 0b11100000:
            obj = -1 - (b ^ 0xFF)
        elif b & 0b11100000 == 0b10100000:
            n = b & 0b00011111
            typ = TYPE_RAW
            if n > self._max_str_len:
                raise ValueError(f"{n} exceeds max_str_len({self._max_str_len})")
            obj = self._read(n)
        elif b & 0b11110000 == 0b10010000:
            n = b & 0b00001111
            typ = TYPE_ARRAY
            if n > self._max_array_len:
                raise ValueError(f"{n} exceeds max_array_len({self._max_array_len})")
        elif b & 0b11110000 == 0b10000000:
            n = b & 0b00001111
            typ = TYPE_MAP
            if n > self._max_map_len:
                raise ValueError(f"{n} exceeds max_map_len({self._max_map_len})")
        elif b == 0xC0:
            obj = None
        elif b == 0xC2:
            obj = False
        elif b == 0xC3:
            obj = True
        elif 0xC4 <= b <= 0xC6:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            if len(fmt) > 0:
                n = struct.unpack_from(fmt, self._buffer, self._buff_i)[0]
            else:
                n = self._buffer[self._buff_i]
            self._buff_i += size
            if n > self._max_bin_len:
                raise ValueError(f"{n} exceeds max_bin_len({self._max_bin_len})")
            obj = self._read(n)
        elif 0xC7 <= b <= 0xC9:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            L, n = struct.unpack_from(fmt, self._buffer, self._buff_i)
            self._buff_i += size
            if L > self._max_ext_len:
                raise ValueError(f"{L} exceeds max_ext_len({self._max_ext_len})")
            obj = self._read(L)
        elif 0xCA <= b <= 0xD3:
            size, fmt = _MSGPACK_HEADERS[b]
            self._reserve(size)
            if len(fmt) > 0:
                obj = struct.unpack_from(fmt, self._buffer, self._buff_i)[0]
            else:
                obj = self._buffer[self._buff_i]
            self._buff_i += size
        elif 0xD4 <= b <= 0xD8:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            if self._max_ext_len < size:
                raise ValueError(f"{size} exceeds max_ext_len({self._max_ext_len})")
            self._reserve(size + 1)
            n, obj = struct.unpack_from(fmt, self._buffer, self._buff_i)
            self._buff_i += size + 1
        elif 0xD9 <= b <= 0xDB:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            if len(fmt) > 0:
                (n,) = struct.unpack_from(fmt, self._buffer, self._buff_i)
            else:
                n = self._buffer[self._buff_i]
            self._buff_i += size
            if n > self._max_str_len:
                raise ValueError(f"{n} exceeds max_str_len({self._max_str_len})")
            obj = self._read(n)
        elif 0xDC <= b <= 0xDD:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            (n,) = struct.unpack_from(fmt, self._buffer, self._buff_i)
            self._buff_i += size
            if n > self._max_array_len:
                raise ValueError(f"{n} exceeds max_array_len({self._max_array_len})")
        elif 0xDE <= b <= 0xDF:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            (n,) = struct.unpack_from(fmt, self._buffer, self._buff_i)
            self._buff_i += size
            if n > self._max_map_len:
                raise ValueError(f"{n} exceeds max_map_len({self._max_map_len})")
        else:
            raise FormatError("Unknown header: 0x%x" % b)
        return typ, n, obj

    def _unpack(self, execute=EX_CONSTRUCT):
        typ, n, obj = self._read_header()

        if execute == EX_READ_ARRAY_HEADER:
            if typ != TYPE_ARRAY:
                raise ValueError("Expected array")
            return n
        if execute == EX_READ_MAP_HEADER:
            if typ != TYPE_MAP:
                raise ValueError("Expected map")
            return n
        # TODO should we eliminate the recursion?
        if typ == TYPE_ARRAY:
            if execute == EX_SKIP:
                for i in range(n):
                    # TODO check whether we need to call `list_hook`
                    self._unpack(EX_SKIP)
                return
            ret = newlist_hint(n)
            for i in range(n):
                ret.append(self._unpack(EX_CONSTRUCT))
            if self._list_hook is not None:
                ret = self._list_hook(ret)
            # TODO is the interaction between `list_hook` and `use_list` ok?
            return ret if self._use_list else tuple(ret)
        if typ == TYPE_MAP:
            if execute == EX_SKIP:
                for i in range(n):
                    # TODO check whether we need to call hooks
                    self._unpack(EX_SKIP)
                    self._unpack(EX_SKIP)
                return
            if self._object_pairs_hook is not None:
                ret = self._object_pairs_hook(
                    (self._unpack(EX_CONSTRUCT), self._unpack(EX_CONSTRUCT)) for _ in range(n)
                )
            else:
                ret = {}
                for _ in range(n):
                    key = self._unpack(EX_CONSTRUCT)
                    if self._strict_map_key and type(key) not in (str, bytes):
                        raise ValueError("%s is not allowed for map key" % str(type(key)))
                    if isinstance(key, str):
                        key = sys.intern(key)
                    ret[key] = self._unpack(EX_CONSTRUCT)
                if self._object_hook is not None:
                    ret = self._object_hook(ret)
            return ret
        if execute == EX_SKIP:
            return
        if typ == TYPE_RAW:
            if self._raw:
                obj = bytes(obj)
            else:
                obj = obj.decode("utf_8", self._unicode_errors)
            return obj
        if typ == TYPE_BIN:
            return bytes(obj)
        if typ == TYPE_EXT:
            if n == -1:  # timestamp
                ts = Timestamp.from_bytes(bytes(obj))
                if self._timestamp == 1:
                    return ts.to_unix()
                elif self._timestamp == 2:
                    return ts.to_unix_nano()
                elif self._timestamp == 3:
                    return ts.to_datetime()
                else:
                    return ts
            else:
                return self._ext_hook(n, bytes(obj))
        assert typ == TYPE_IMMEDIATE
        return obj

    def __iter__(self):
        return self

    def __next__(self):
        try:
            ret = self._unpack(EX_CONSTRUCT)
            self._consume()
            return ret
        except OutOfData:
            self._consume()
            raise StopIteration
        except RecursionError:
            raise StackError

    next = __next__

    def skip(self):
        self._unpack(EX_SKIP)
        self._consume()

    def unpack(self):
        try:
            ret = self._unpack(EX_CONSTRUCT)
        except RecursionError:
            raise StackError
        self._consume()
        return ret

    def read_array_header(self):
        ret = self._unpack(EX_READ_ARRAY_HEADER)
        self._consume()
        return ret

    def read_map_header(self):
        ret = self._unpack(EX_READ_MAP_HEADER)
        self._consume()
        return ret

    def tell(self):
        return self._stream_offset


class Packer:
    """
    MessagePack Packer

    Usage::

        packer = Packer()
        astream.write(packer.pack(a))
        astream.write(packer.pack(b))

    Packer's constructor has some keyword arguments:

    :param default:
        When specified, it should be callable.
        Convert user type to builtin type that Packer supports.
        See also simplejson's document.

    :param bool use_single_float:
        Use single precision float type for float. (default: False)

    :param bool autoreset:
        Reset buffer after each pack and return its content as `bytes`. (default: True).
        If set this to false, use `bytes()` to get content and `.reset()` to clear buffer.

    :param bool use_bin_type:
        Use bin type introduced in msgpack spec 2.0 for bytes.
        It also enables str8 type for unicode. (default: True)

    :param bool strict_types:
        If set to true, types will be checked to be exact. Derived classes
        from serializable types will not be serialized and will be
        treated as unsupported type and forwarded to default.
        Additionally tuples will not be serialized as lists.
        This is useful when trying to implement accurate serialization
        for python types.

    :param bool datetime:
        If set to true, datetime with tzinfo is packed into Timestamp type.
        Note that the tzinfo is stripped in the timestamp.
        You can get UTC datetime with `timestamp=3` option of the Unpacker.

    :param str unicode_errors:
        The error handler for encoding unicode. (default: 'strict')
        DO NOT USE THIS!!  This option is kept for very specific usage.

    :param int buf_size:
        Internal buffer size. This option is used only for C implementation.
    """

    def __init__(
        self,
        *,
        default=None,
        use_single_float=False,
        autoreset=True,
        use_bin_type=True,
        strict_types=False,
        datetime=False,
        unicode_errors=None,
        buf_size=None,
    ):
        self._strict_types = strict_types
        self._use_float = use_single_float
        self._autoreset = autoreset
        self._use_bin_type = use_bin_type
        self._buffer = BytesIO()
        self._datetime = bool(datetime)
        self._unicode_errors = unicode_errors or "strict"
        if default is not None and not callable(default):
            raise TypeError("default must be callable")
        self._default = default

    def _pack(
        self,
        obj,
        nest_limit=DEFAULT_RECURSE_LIMIT,
        check=isinstance,
        check_type_strict=_check_type_strict,
    ):
        default_used = False
        if self._strict_types:
            check = check_type_strict
            list_types = list
        else:
            list_types = (list, tuple)
        while True:
            if nest_limit < 0:
                raise ValueError("recursion limit exceeded")
            if obj is None:
                return self._buffer.write(b"\xc0")
            if check(obj, bool):
                if obj:
                    return self._buffer.write(b"\xc3")
                return self._buffer.write(b"\xc2")
            if check(obj, int):
                if 0 <= obj < 0x80:
                    return self._buffer.write(struct.pack("B", obj))
                if -0x20 <= obj < 0:
                    return self._buffer.write(struct.pack("b", obj))
                if 0x80 <= obj <= 0xFF:
                    return self._buffer.write(struct.pack("BB", 0xCC, obj))
                if -0x80 <= obj < 0:
                    return self._buffer.write(struct.pack(">Bb", 0xD0, obj))
                if 0xFF < obj <= 0xFFFF:
                    return self._buffer.write(struct.pack(">BH", 0xCD, obj))
                if -0x8000 <= obj < -0x80:
                    return self._buffer.write(struct.pack(">Bh", 0xD1, obj))
                if 0xFFFF < obj <= 0xFFFFFFFF:
                    return self._buffer.write(struct.pack(">BI", 0xCE, obj))
                if -0x80000000 <= obj < -0x8000:
                    return self._buffer.write(struct.pack(">Bi", 0xD2, obj))
                if 0xFFFFFFFF < obj <= 0xFFFFFFFFFFFFFFFF:
                    return self._buffer.write(struct.pack(">BQ", 0xCF, obj))
                if -0x8000000000000000 <= obj < -0x80000000:
                    return self._buffer.write(struct.pack(">Bq", 0xD3, obj))
                if not default_used and self._default is not None:
                    obj = self._default(obj)
                    default_used = True
                    continue
                raise OverflowError("Integer value out of range")
            if check(obj, (bytes, bytearray)):
                n = len(obj)
                if n >= 2**32:
                    raise ValueError("%s is too large" % type(obj).__name__)
                self._pack_bin_header(n)
                return self._buffer.write(obj)
            if check(obj, str):
                obj = obj.encode("utf-8", self._unicode_errors)
                n = len(obj)
                if n >= 2**32:
                    raise ValueError("String is too large")
                self._pack_raw_header(n)
                return self._buffer.write(obj)
            if check(obj, memoryview):
                n = obj.nbytes
                if n >= 2**32:
                    raise ValueError("Memoryview is too large")
                self._pack_bin_header(n)
                return self._buffer.write(obj)
            if check(obj, float):
                if self._use_float:
                    return self._buffer.write(struct.pack(">Bf", 0xCA, obj))
                return self._buffer.write(struct.pack(">Bd", 0xCB, obj))
            if check(obj, (ExtType, Timestamp)):
                if check(obj, Timestamp):
                    code = -1
                    data = obj.to_bytes()
                else:
                    code = obj.code
                    data = obj.data
                assert isinstance(code, int)
                assert isinstance(data, bytes)
                L = len(data)
                if L == 1:
                    self._buffer.write(b"\xd4")
                elif L == 2:
                    self._buffer.write(b"\xd5")
                elif L == 4:
                    self._buffer.write(b"\xd6")
                elif L == 8:
                    self._buffer.write(b"\xd7")
                elif L == 16:
                    self._buffer.write(b"\xd8")
                elif L <= 0xFF:
                    self._buffer.write(struct.pack(">BB", 0xC7, L))
                elif L <= 0xFFFF:
                    self._buffer.write(struct.pack(">BH", 0xC8, L))
                else:
                    self._buffer.write(struct.pack(">BI", 0xC9, L))
                self._buffer.write(struct.pack("b", code))
                self._buffer.write(data)
                return
            if check(obj, list_types):
                n = len(obj)
                self._pack_array_header(n)
                for i in range(n):
                    self._pack(obj[i], nest_limit - 1)
                return
            if check(obj, dict):
                return self._pack_map_pairs(len(obj), obj.items(), nest_limit - 1)

            if self._datetime and check(obj, _DateTime) and obj.tzinfo is not None:
                obj = Timestamp.from_datetime(obj)
                default_used = 1
                continue

            if not default_used and self._default is not None:
                obj = self._default(obj)
                default_used = 1
                continue

            if self._datetime and check(obj, _DateTime):
                raise ValueError(f"Cannot serialize {obj!r} where tzinfo=None")

            raise TypeError(f"Cannot serialize {obj!r}")

    def pack(self, obj):
        try:
            self._pack(obj)
        except:
            self._buffer = BytesIO()  # force reset
            raise
        if self._autoreset:
            ret = self._buffer.getvalue()
            self._buffer = BytesIO()
            return ret

    def pack_map_pairs(self, pairs):
        self._pack_map_pairs(len(pairs), pairs)
        if self._autoreset:
            ret = self._buffer.getvalue()
            self._buffer = BytesIO()
            return ret

    def pack_array_header(self, n):
        if n >= 2**32:
            raise ValueError
        self._pack_array_header(n)
        if self._autoreset:
            ret = self._buffer.getvalue()
            self._buffer = BytesIO()
            return ret

    def pack_map_header(self, n):
        if n >= 2**32:
            raise ValueError
        self._pack_map_header(n)
        if self._autoreset:
            ret = self._buffer.getvalue()
            self._buffer = BytesIO()
            return ret

    def pack_ext_type(self, typecode, data):
        if not isinstance(typecode, int):
            raise TypeError("typecode must have int type.")
        if not 0 <= typecode <= 127:
            raise ValueError("typecode should be 0-127")
        if not isinstance(data, bytes):
            raise TypeError("data must have bytes type")
        L = len(data)
        if L > 0xFFFFFFFF:
            raise ValueError("Too large data")
        if L == 1:
            self._buffer.write(b"\xd4")
        elif L == 2:
            self._buffer.write(b"\xd5")
        elif L == 4:
            self._buffer.write(b"\xd6")
        elif L == 8:
            self._buffer.write(b"\xd7")
        elif L == 16:
            self._buffer.write(b"\xd8")
        elif L <= 0xFF:
            self._buffer.write(b"\xc7" + struct.pack("B", L))
        elif L <= 0xFFFF:
            self._buffer.write(b"\xc8" + struct.pack(">H", L))
        else:
            self._buffer.write(b"\xc9" + struct.pack(">I", L))
        self._buffer.write(struct.pack("B", typecode))
        self._buffer.write(data)

    def _pack_array_header(self, n):
        if n <= 0x0F:
            return self._buffer.write(struct.pack("B", 0x90 + n))
        if n <= 0xFFFF:
            return self._buffer.write(struct.pack(">BH", 0xDC, n))
        if n <= 0xFFFFFFFF:
            return self._buffer.write(struct.pack(">BI", 0xDD, n))
        raise ValueError("Array is too large")

    def _pack_map_header(self, n):
        if n <= 0x0F:
            return self._buffer.write(struct.pack("B", 0x80 + n))
        if n <= 0xFFFF:
            return self._buffer.write(struct.pack(">BH", 0xDE, n))
        if n <= 0xFFFFFFFF:
            return self._buffer.write(struct.pack(">BI", 0xDF, n))
        raise ValueError("Dict is too large")

    def _pack_map_pairs(self, n, pairs, nest_limit=DEFAULT_RECURSE_LIMIT):
        self._pack_map_header(n)
        for k, v in pairs:
            self._pack(k, nest_limit - 1)
            self._pack(v, nest_limit - 1)

    def _pack_raw_header(self, n):
        if n <= 0x1F:
            self._buffer.write(struct.pack("B", 0xA0 + n))
        elif self._use_bin_type and n <= 0xFF:
            self._buffer.write(struct.pack(">BB", 0xD9, n))
        elif n <= 0xFFFF:
            self._buffer.write(struct.pack(">BH", 0xDA, n))
        elif n <= 0xFFFFFFFF:
            self._buffer.write(struct.pack(">BI", 0xDB, n))
        else:
            raise ValueError("Raw is too large")

    def _pack_bin_header(self, n):
        if not self._use_bin_type:
            return self._pack_raw_header(n)
        elif n <= 0xFF:
            return self._buffer.write(struct.pack(">BB", 0xC4, n))
        elif n <= 0xFFFF:
            return self._buffer.write(struct.pack(">BH", 0xC5, n))
        elif n <= 0xFFFFFFFF:
            return self._buffer.write(struct.pack(">BI", 0xC6, n))
        else:
            raise ValueError("Bin is too large")

    def bytes(self):
        """Return internal buffer contents as bytes object"""
        return self._buffer.getvalue()

    def reset(self):
        """Reset internal buffer.

        This method is useful only when autoreset=False.
        """
        self._buffer = BytesIO()

    def getbuffer(self):
        """Return view of internal buffer."""
        if _USING_STRINGBUILDER:
            return memoryview(self.bytes())
        else:
            return self._buffer.getbuffer()