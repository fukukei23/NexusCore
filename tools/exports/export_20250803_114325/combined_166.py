
# === NexusCore/openenv\Lib\site-packages\click\parser.py ===
"""
This module started out as largely a copy paste from the stdlib's
optparse module with the features removed that we do not need from
optparse because we implement them in Click on a higher level (for
instance type handling, help formatting and a lot more).

The plan is to remove more and more from here over time.

The reason this is a different module and not optparse from the stdlib
is that there are differences in 2.x and 3.x about the error messages
generated and optparse in the stdlib uses gettext for no good reason
and might cause us issues.

Click uses parts of optparse written by Gregory P. Ward and maintained
by the Python Software Foundation. This is limited to code in parser.py.

Copyright 2001-2006 Gregory P. Ward. All rights reserved.
Copyright 2002-2006 Python Software Foundation. All rights reserved.
"""

# This code uses parts of optparse written by Gregory P. Ward and
# maintained by the Python Software Foundation.
# Copyright 2001-2006 Gregory P. Ward
# Copyright 2002-2006 Python Software Foundation
from __future__ import annotations

import collections.abc as cabc
import typing as t
from collections import deque
from gettext import gettext as _
from gettext import ngettext

from .exceptions import BadArgumentUsage
from .exceptions import BadOptionUsage
from .exceptions import NoSuchOption
from .exceptions import UsageError

if t.TYPE_CHECKING:
    from .core import Argument as CoreArgument
    from .core import Context
    from .core import Option as CoreOption
    from .core import Parameter as CoreParameter

V = t.TypeVar("V")

# Sentinel value that indicates an option was passed as a flag without a
# value but is not a flag option. Option.consume_value uses this to
# prompt or use the flag_value.
_flag_needs_value = object()


def _unpack_args(
    args: cabc.Sequence[str], nargs_spec: cabc.Sequence[int]
) -> tuple[cabc.Sequence[str | cabc.Sequence[str | None] | None], list[str]]:
    """Given an iterable of arguments and an iterable of nargs specifications,
    it returns a tuple with all the unpacked arguments at the first index
    and all remaining arguments as the second.

    The nargs specification is the number of arguments that should be consumed
    or `-1` to indicate that this position should eat up all the remainders.

    Missing items are filled with `None`.
    """
    args = deque(args)
    nargs_spec = deque(nargs_spec)
    rv: list[str | tuple[str | None, ...] | None] = []
    spos: int | None = None

    def _fetch(c: deque[V]) -> V | None:
        try:
            if spos is None:
                return c.popleft()
            else:
                return c.pop()
        except IndexError:
            return None

    while nargs_spec:
        nargs = _fetch(nargs_spec)

        if nargs is None:
            continue

        if nargs == 1:
            rv.append(_fetch(args))
        elif nargs > 1:
            x = [_fetch(args) for _ in range(nargs)]

            # If we're reversed, we're pulling in the arguments in reverse,
            # so we need to turn them around.
            if spos is not None:
                x.reverse()

            rv.append(tuple(x))
        elif nargs < 0:
            if spos is not None:
                raise TypeError("Cannot have two nargs < 0")

            spos = len(rv)
            rv.append(None)

    # spos is the position of the wildcard (star).  If it's not `None`,
    # we fill it with the remainder.
    if spos is not None:
        rv[spos] = tuple(args)
        args = []
        rv[spos + 1 :] = reversed(rv[spos + 1 :])

    return tuple(rv), list(args)


def _split_opt(opt: str) -> tuple[str, str]:
    first = opt[:1]
    if first.isalnum():
        return "", opt
    if opt[1:2] == first:
        return opt[:2], opt[2:]
    return first, opt[1:]


def _normalize_opt(opt: str, ctx: Context | None) -> str:
    if ctx is None or ctx.token_normalize_func is None:
        return opt
    prefix, opt = _split_opt(opt)
    return f"{prefix}{ctx.token_normalize_func(opt)}"


class _Option:
    def __init__(
        self,
        obj: CoreOption,
        opts: cabc.Sequence[str],
        dest: str | None,
        action: str | None = None,
        nargs: int = 1,
        const: t.Any | None = None,
    ):
        self._short_opts = []
        self._long_opts = []
        self.prefixes: set[str] = set()

        for opt in opts:
            prefix, value = _split_opt(opt)
            if not prefix:
                raise ValueError(f"Invalid start character for option ({opt})")
            self.prefixes.add(prefix[0])
            if len(prefix) == 1 and len(value) == 1:
                self._short_opts.append(opt)
            else:
                self._long_opts.append(opt)
                self.prefixes.add(prefix)

        if action is None:
            action = "store"

        self.dest = dest
        self.action = action
        self.nargs = nargs
        self.const = const
        self.obj = obj

    @property
    def takes_value(self) -> bool:
        return self.action in ("store", "append")

    def process(self, value: t.Any, state: _ParsingState) -> None:
        if self.action == "store":
            state.opts[self.dest] = value  # type: ignore
        elif self.action == "store_const":
            state.opts[self.dest] = self.const  # type: ignore
        elif self.action == "append":
            state.opts.setdefault(self.dest, []).append(value)  # type: ignore
        elif self.action == "append_const":
            state.opts.setdefault(self.dest, []).append(self.const)  # type: ignore
        elif self.action == "count":
            state.opts[self.dest] = state.opts.get(self.dest, 0) + 1  # type: ignore
        else:
            raise ValueError(f"unknown action '{self.action}'")
        state.order.append(self.obj)


class _Argument:
    def __init__(self, obj: CoreArgument, dest: str | None, nargs: int = 1):
        self.dest = dest
        self.nargs = nargs
        self.obj = obj

    def process(
        self,
        value: str | cabc.Sequence[str | None] | None,
        state: _ParsingState,
    ) -> None:
        if self.nargs > 1:
            assert value is not None
            holes = sum(1 for x in value if x is None)
            if holes == len(value):
                value = None
            elif holes != 0:
                raise BadArgumentUsage(
                    _("Argument {name!r} takes {nargs} values.").format(
                        name=self.dest, nargs=self.nargs
                    )
                )

        if self.nargs == -1 and self.obj.envvar is not None and value == ():
            # Replace empty tuple with None so that a value from the
            # environment may be tried.
            value = None

        state.opts[self.dest] = value  # type: ignore
        state.order.append(self.obj)


class _ParsingState:
    def __init__(self, rargs: list[str]) -> None:
        self.opts: dict[str, t.Any] = {}
        self.largs: list[str] = []
        self.rargs = rargs
        self.order: list[CoreParameter] = []


class _OptionParser:
    """The option parser is an internal class that is ultimately used to
    parse options and arguments.  It's modelled after optparse and brings
    a similar but vastly simplified API.  It should generally not be used
    directly as the high level Click classes wrap it for you.

    It's not nearly as extensible as optparse or argparse as it does not
    implement features that are implemented on a higher level (such as
    types or defaults).

    :param ctx: optionally the :class:`~click.Context` where this parser
                should go with.

    .. deprecated:: 8.2
        Will be removed in Click 9.0.
    """

    def __init__(self, ctx: Context | None = None) -> None:
        #: The :class:`~click.Context` for this parser.  This might be
        #: `None` for some advanced use cases.
        self.ctx = ctx
        #: This controls how the parser deals with interspersed arguments.
        #: If this is set to `False`, the parser will stop on the first
        #: non-option.  Click uses this to implement nested subcommands
        #: safely.
        self.allow_interspersed_args: bool = True
        #: This tells the parser how to deal with unknown options.  By
        #: default it will error out (which is sensible), but there is a
        #: second mode where it will ignore it and continue processing
        #: after shifting all the unknown options into the resulting args.
        self.ignore_unknown_options: bool = False

        if ctx is not None:
            self.allow_interspersed_args = ctx.allow_interspersed_args
            self.ignore_unknown_options = ctx.ignore_unknown_options

        self._short_opt: dict[str, _Option] = {}
        self._long_opt: dict[str, _Option] = {}
        self._opt_prefixes = {"-", "--"}
        self._args: list[_Argument] = []

    def add_option(
        self,
        obj: CoreOption,
        opts: cabc.Sequence[str],
        dest: str | None,
        action: str | None = None,
        nargs: int = 1,
        const: t.Any | None = None,
    ) -> None:
        """Adds a new option named `dest` to the parser.  The destination
        is not inferred (unlike with optparse) and needs to be explicitly
        provided.  Action can be any of ``store``, ``store_const``,
        ``append``, ``append_const`` or ``count``.

        The `obj` can be used to identify the option in the order list
        that is returned from the parser.
        """
        opts = [_normalize_opt(opt, self.ctx) for opt in opts]
        option = _Option(obj, opts, dest, action=action, nargs=nargs, const=const)
        self._opt_prefixes.update(option.prefixes)
        for opt in option._short_opts:
            self._short_opt[opt] = option
        for opt in option._long_opts:
            self._long_opt[opt] = option

    def add_argument(self, obj: CoreArgument, dest: str | None, nargs: int = 1) -> None:
        """Adds a positional argument named `dest` to the parser.

        The `obj` can be used to identify the option in the order list
        that is returned from the parser.
        """
        self._args.append(_Argument(obj, dest=dest, nargs=nargs))

    def parse_args(
        self, args: list[str]
    ) -> tuple[dict[str, t.Any], list[str], list[CoreParameter]]:
        """Parses positional arguments and returns ``(values, args, order)``
        for the parsed options and arguments as well as the leftover
        arguments if there are any.  The order is a list of objects as they
        appear on the command line.  If arguments appear multiple times they
        will be memorized multiple times as well.
        """
        state = _ParsingState(args)
        try:
            self._process_args_for_options(state)
            self._process_args_for_args(state)
        except UsageError:
            if self.ctx is None or not self.ctx.resilient_parsing:
                raise
        return state.opts, state.largs, state.order

    def _process_args_for_args(self, state: _ParsingState) -> None:
        pargs, args = _unpack_args(
            state.largs + state.rargs, [x.nargs for x in self._args]
        )

        for idx, arg in enumerate(self._args):
            arg.process(pargs[idx], state)

        state.largs = args
        state.rargs = []

    def _process_args_for_options(self, state: _ParsingState) -> None:
        while state.rargs:
            arg = state.rargs.pop(0)
            arglen = len(arg)
            # Double dashes always handled explicitly regardless of what
            # prefixes are valid.
            if arg == "--":
                return
            elif arg[:1] in self._opt_prefixes and arglen > 1:
                self._process_opts(arg, state)
            elif self.allow_interspersed_args:
                state.largs.append(arg)
            else:
                state.rargs.insert(0, arg)
                return

        # Say this is the original argument list:
        # [arg0, arg1, ..., arg(i-1), arg(i), arg(i+1), ..., arg(N-1)]
        #                            ^
        # (we are about to process arg(i)).
        #
        # Then rargs is [arg(i), ..., arg(N-1)] and largs is a *subset* of
        # [arg0, ..., arg(i-1)] (any options and their arguments will have
        # been removed from largs).
        #
        # The while loop will usually consume 1 or more arguments per pass.
        # If it consumes 1 (eg. arg is an option that takes no arguments),
        # then after _process_arg() is done the situation is:
        #
        #   largs = subset of [arg0, ..., arg(i)]
        #   rargs = [arg(i+1), ..., arg(N-1)]
        #
        # If allow_interspersed_args is false, largs will always be
        # *empty* -- still a subset of [arg0, ..., arg(i-1)], but
        # not a very interesting subset!

    def _match_long_opt(
        self, opt: str, explicit_value: str | None, state: _ParsingState
    ) -> None:
        if opt not in self._long_opt:
            from difflib import get_close_matches

            possibilities = get_close_matches(opt, self._long_opt)
            raise NoSuchOption(opt, possibilities=possibilities, ctx=self.ctx)

        option = self._long_opt[opt]
        if option.takes_value:
            # At this point it's safe to modify rargs by injecting the
            # explicit value, because no exception is raised in this
            # branch.  This means that the inserted value will be fully
            # consumed.
            if explicit_value is not None:
                state.rargs.insert(0, explicit_value)

            value = self._get_value_from_state(opt, option, state)

        elif explicit_value is not None:
            raise BadOptionUsage(
                opt, _("Option {name!r} does not take a value.").format(name=opt)
            )

        else:
            value = None

        option.process(value, state)

    def _match_short_opt(self, arg: str, state: _ParsingState) -> None:
        stop = False
        i = 1
        prefix = arg[0]
        unknown_options = []

        for ch in arg[1:]:
            opt = _normalize_opt(f"{prefix}{ch}", self.ctx)
            option = self._short_opt.get(opt)
            i += 1

            if not option:
                if self.ignore_unknown_options:
                    unknown_options.append(ch)
                    continue
                raise NoSuchOption(opt, ctx=self.ctx)
            if option.takes_value:
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    state.rargs.insert(0, arg[i:])
                    stop = True

                value = self._get_value_from_state(opt, option, state)

            else:
                value = None

            option.process(value, state)

            if stop:
                break

        # If we got any unknown options we recombine the string of the
        # remaining options and re-attach the prefix, then report that
        # to the state as new larg.  This way there is basic combinatorics
        # that can be achieved while still ignoring unknown arguments.
        if self.ignore_unknown_options and unknown_options:
            state.largs.append(f"{prefix}{''.join(unknown_options)}")

    def _get_value_from_state(
        self, option_name: str, option: _Option, state: _ParsingState
    ) -> t.Any:
        nargs = option.nargs

        if len(state.rargs) < nargs:
            if option.obj._flag_needs_value:
                # Option allows omitting the value.
                value = _flag_needs_value
            else:
                raise BadOptionUsage(
                    option_name,
                    ngettext(
                        "Option {name!r} requires an argument.",
                        "Option {name!r} requires {nargs} arguments.",
                        nargs,
                    ).format(name=option_name, nargs=nargs),
                )
        elif nargs == 1:
            next_rarg = state.rargs[0]

            if (
                option.obj._flag_needs_value
                and isinstance(next_rarg, str)
                and next_rarg[:1] in self._opt_prefixes
                and len(next_rarg) > 1
            ):
                # The next arg looks like the start of an option, don't
                # use it as the value if omitting the value is allowed.
                value = _flag_needs_value
            else:
                value = state.rargs.pop(0)
        else:
            value = tuple(state.rargs[:nargs])
            del state.rargs[:nargs]

        return value

    def _process_opts(self, arg: str, state: _ParsingState) -> None:
        explicit_value = None
        # Long option handling happens in two parts.  The first part is
        # supporting explicitly attached values.  In any case, we will try
        # to long match the option first.
        if "=" in arg:
            long_opt, explicit_value = arg.split("=", 1)
        else:
            long_opt = arg
        norm_long_opt = _normalize_opt(long_opt, self.ctx)

        # At this point we will match the (assumed) long option through
        # the long option matching code.  Note that this allows options
        # like "-foo" to be matched as long options.
        try:
            self._match_long_opt(norm_long_opt, explicit_value, state)
        except NoSuchOption:
            # At this point the long option matching failed, and we need
            # to try with short options.  However there is a special rule
            # which says, that if we have a two character options prefix
            # (applies to "--foo" for instance), we do not dispatch to the
            # short option code and will instead raise the no option
            # error.
            if arg[:2] not in self._opt_prefixes:
                self._match_short_opt(arg, state)
                return

            if not self.ignore_unknown_options:
                raise

            state.largs.append(arg)


def __getattr__(name: str) -> object:
    import warnings

    if name in {
        "OptionParser",
        "Argument",
        "Option",
        "split_opt",
        "normalize_opt",
        "ParsingState",
    }:
        warnings.warn(
            f"'parser.{name}' is deprecated and will be removed in Click 9.0."
            " The old parser is available in 'optparse'.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[f"_{name}"]

    if name == "split_arg_string":
        from .shell_completion import split_arg_string

        warnings.warn(
            "Importing 'parser.split_arg_string' is deprecated, it will only be"
            " available in 'shell_completion' in Click 9.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return split_arg_string

    raise AttributeError(name)

# === NexusCore/openenv\Lib\site-packages\matplotlib\_afm.py ===
"""
A python interface to Adobe Font Metrics Files.

Although a number of other Python implementations exist, and may be more
complete than this, it was decided not to go with them because they were
either:

1) copyrighted or used a non-BSD compatible license
2) had too many dependencies and a free standing lib was needed
3) did more than needed and it was easier to write afresh rather than
   figure out how to get just what was needed.

It is pretty easy to use, and has no external dependencies:

>>> import matplotlib as mpl
>>> from pathlib import Path
>>> afm_path = Path(mpl.get_data_path(), 'fonts', 'afm', 'ptmr8a.afm')
>>>
>>> from matplotlib.afm import AFM
>>> with afm_path.open('rb') as fh:
...     afm = AFM(fh)
>>> afm.string_width_height('What the heck?')
(6220.0, 694)
>>> afm.get_fontname()
'Times-Roman'
>>> afm.get_kern_dist('A', 'f')
0
>>> afm.get_kern_dist('A', 'y')
-92.0
>>> afm.get_bbox_char('!')
[130, -9, 238, 676]

As in the Adobe Font Metrics File Format Specification, all dimensions
are given in units of 1/1000 of the scale factor (point size) of the font
being used.
"""

from collections import namedtuple
import logging
import re

from ._mathtext_data import uni2type1


_log = logging.getLogger(__name__)


def _to_int(x):
    # Some AFM files have floats where we are expecting ints -- there is
    # probably a better way to handle this (support floats, round rather than
    # truncate).  But I don't know what the best approach is now and this
    # change to _to_int should at least prevent Matplotlib from crashing on
    # these.  JDH (2009-11-06)
    return int(float(x))


def _to_float(x):
    # Some AFM files use "," instead of "." as decimal separator -- this
    # shouldn't be ambiguous (unless someone is wicked enough to use "," as
    # thousands separator...).
    if isinstance(x, bytes):
        # Encoding doesn't really matter -- if we have codepoints >127 the call
        # to float() will error anyways.
        x = x.decode('latin-1')
    return float(x.replace(',', '.'))


def _to_str(x):
    return x.decode('utf8')


def _to_list_of_ints(s):
    s = s.replace(b',', b' ')
    return [_to_int(val) for val in s.split()]


def _to_list_of_floats(s):
    return [_to_float(val) for val in s.split()]


def _to_bool(s):
    if s.lower().strip() in (b'false', b'0', b'no'):
        return False
    else:
        return True


def _parse_header(fh):
    """
    Read the font metrics header (up to the char metrics) and returns
    a dictionary mapping *key* to *val*.  *val* will be converted to the
    appropriate python type as necessary; e.g.:

        * 'False'->False
        * '0'->0
        * '-168 -218 1000 898'-> [-168, -218, 1000, 898]

    Dictionary keys are

      StartFontMetrics, FontName, FullName, FamilyName, Weight,
      ItalicAngle, IsFixedPitch, FontBBox, UnderlinePosition,
      UnderlineThickness, Version, Notice, EncodingScheme, CapHeight,
      XHeight, Ascender, Descender, StartCharMetrics
    """
    header_converters = {
        b'StartFontMetrics': _to_float,
        b'FontName': _to_str,
        b'FullName': _to_str,
        b'FamilyName': _to_str,
        b'Weight': _to_str,
        b'ItalicAngle': _to_float,
        b'IsFixedPitch': _to_bool,
        b'FontBBox': _to_list_of_ints,
        b'UnderlinePosition': _to_float,
        b'UnderlineThickness': _to_float,
        b'Version': _to_str,
        # Some AFM files have non-ASCII characters (which are not allowed by
        # the spec).  Given that there is actually no public API to even access
        # this field, just return it as straight bytes.
        b'Notice': lambda x: x,
        b'EncodingScheme': _to_str,
        b'CapHeight': _to_float,  # Is the second version a mistake, or
        b'Capheight': _to_float,  # do some AFM files contain 'Capheight'? -JKS
        b'XHeight': _to_float,
        b'Ascender': _to_float,
        b'Descender': _to_float,
        b'StdHW': _to_float,
        b'StdVW': _to_float,
        b'StartCharMetrics': _to_int,
        b'CharacterSet': _to_str,
        b'Characters': _to_int,
    }
    d = {}
    first_line = True
    for line in fh:
        line = line.rstrip()
        if line.startswith(b'Comment'):
            continue
        lst = line.split(b' ', 1)
        key = lst[0]
        if first_line:
            # AFM spec, Section 4: The StartFontMetrics keyword
            # [followed by a version number] must be the first line in
            # the file, and the EndFontMetrics keyword must be the
            # last non-empty line in the file.  We just check the
            # first header entry.
            if key != b'StartFontMetrics':
                raise RuntimeError('Not an AFM file')
            first_line = False
        if len(lst) == 2:
            val = lst[1]
        else:
            val = b''
        try:
            converter = header_converters[key]
        except KeyError:
            _log.error("Found an unknown keyword in AFM header (was %r)", key)
            continue
        try:
            d[key] = converter(val)
        except ValueError:
            _log.error('Value error parsing header in AFM: %s, %s', key, val)
            continue
        if key == b'StartCharMetrics':
            break
    else:
        raise RuntimeError('Bad parse')
    return d


CharMetrics = namedtuple('CharMetrics', 'width, name, bbox')
CharMetrics.__doc__ = """
    Represents the character metrics of a single character.

    Notes
    -----
    The fields do currently only describe a subset of character metrics
    information defined in the AFM standard.
    """
CharMetrics.width.__doc__ = """The character width (WX)."""
CharMetrics.name.__doc__ = """The character name (N)."""
CharMetrics.bbox.__doc__ = """
    The bbox of the character (B) as a tuple (*llx*, *lly*, *urx*, *ury*)."""


def _parse_char_metrics(fh):
    """
    Parse the given filehandle for character metrics information and return
    the information as dicts.

    It is assumed that the file cursor is on the line behind
    'StartCharMetrics'.

    Returns
    -------
    ascii_d : dict
         A mapping "ASCII num of the character" to `.CharMetrics`.
    name_d : dict
         A mapping "character name" to `.CharMetrics`.

    Notes
    -----
    This function is incomplete per the standard, but thus far parses
    all the sample afm files tried.
    """
    required_keys = {'C', 'WX', 'N', 'B'}

    ascii_d = {}
    name_d = {}
    for line in fh:
        # We are defensively letting values be utf8. The spec requires
        # ascii, but there are non-compliant fonts in circulation
        line = _to_str(line.rstrip())  # Convert from byte-literal
        if line.startswith('EndCharMetrics'):
            return ascii_d, name_d
        # Split the metric line into a dictionary, keyed by metric identifiers
        vals = dict(s.strip().split(' ', 1) for s in line.split(';') if s)
        # There may be other metrics present, but only these are needed
        if not required_keys.issubset(vals):
            raise RuntimeError('Bad char metrics line: %s' % line)
        num = _to_int(vals['C'])
        wx = _to_float(vals['WX'])
        name = vals['N']
        bbox = _to_list_of_floats(vals['B'])
        bbox = list(map(int, bbox))
        metrics = CharMetrics(wx, name, bbox)
        # Workaround: If the character name is 'Euro', give it the
        # corresponding character code, according to WinAnsiEncoding (see PDF
        # Reference).
        if name == 'Euro':
            num = 128
        elif name == 'minus':
            num = ord("\N{MINUS SIGN}")  # 0x2212
        if num != -1:
            ascii_d[num] = metrics
        name_d[name] = metrics
    raise RuntimeError('Bad parse')


def _parse_kern_pairs(fh):
    """
    Return a kern pairs dictionary; keys are (*char1*, *char2*) tuples and
    values are the kern pair value.  For example, a kern pairs line like
    ``KPX A y -50``

    will be represented as::

      d[ ('A', 'y') ] = -50

    """

    line = next(fh)
    if not line.startswith(b'StartKernPairs'):
        raise RuntimeError('Bad start of kern pairs data: %s' % line)

    d = {}
    for line in fh:
        line = line.rstrip()
        if not line:
            continue
        if line.startswith(b'EndKernPairs'):
            next(fh)  # EndKernData
            return d
        vals = line.split()
        if len(vals) != 4 or vals[0] != b'KPX':
            raise RuntimeError('Bad kern pairs line: %s' % line)
        c1, c2, val = _to_str(vals[1]), _to_str(vals[2]), _to_float(vals[3])
        d[(c1, c2)] = val
    raise RuntimeError('Bad kern pairs parse')


CompositePart = namedtuple('CompositePart', 'name, dx, dy')
CompositePart.__doc__ = """
    Represents the information on a composite element of a composite char."""
CompositePart.name.__doc__ = """Name of the part, e.g. 'acute'."""
CompositePart.dx.__doc__ = """x-displacement of the part from the origin."""
CompositePart.dy.__doc__ = """y-displacement of the part from the origin."""


def _parse_composites(fh):
    """
    Parse the given filehandle for composites information return them as a
    dict.

    It is assumed that the file cursor is on the line behind 'StartComposites'.

    Returns
    -------
    dict
        A dict mapping composite character names to a parts list. The parts
        list is a list of `.CompositePart` entries describing the parts of
        the composite.

    Examples
    --------
    A composite definition line::

      CC Aacute 2 ; PCC A 0 0 ; PCC acute 160 170 ;

    will be represented as::

      composites['Aacute'] = [CompositePart(name='A', dx=0, dy=0),
                              CompositePart(name='acute', dx=160, dy=170)]

    """
    composites = {}
    for line in fh:
        line = line.rstrip()
        if not line:
            continue
        if line.startswith(b'EndComposites'):
            return composites
        vals = line.split(b';')
        cc = vals[0].split()
        name, _num_parts = cc[1], _to_int(cc[2])
        pccParts = []
        for s in vals[1:-1]:
            pcc = s.split()
            part = CompositePart(pcc[1], _to_float(pcc[2]), _to_float(pcc[3]))
            pccParts.append(part)
        composites[name] = pccParts

    raise RuntimeError('Bad composites parse')


def _parse_optional(fh):
    """
    Parse the optional fields for kern pair data and composites.

    Returns
    -------
    kern_data : dict
        A dict containing kerning information. May be empty.
        See `._parse_kern_pairs`.
    composites : dict
        A dict containing composite information. May be empty.
        See `._parse_composites`.
    """
    optional = {
        b'StartKernData': _parse_kern_pairs,
        b'StartComposites':  _parse_composites,
        }

    d = {b'StartKernData': {},
         b'StartComposites': {}}
    for line in fh:
        line = line.rstrip()
        if not line:
            continue
        key = line.split()[0]

        if key in optional:
            d[key] = optional[key](fh)

    return d[b'StartKernData'], d[b'StartComposites']


class AFM:

    def __init__(self, fh):
        """Parse the AFM file in file object *fh*."""
        self._header = _parse_header(fh)
        self._metrics, self._metrics_by_name = _parse_char_metrics(fh)
        self._kern, self._composite = _parse_optional(fh)

    def get_bbox_char(self, c, isord=False):
        if not isord:
            c = ord(c)
        return self._metrics[c].bbox

    def string_width_height(self, s):
        """
        Return the string width (including kerning) and string height
        as a (*w*, *h*) tuple.
        """
        if not len(s):
            return 0, 0
        total_width = 0
        namelast = None
        miny = 1e9
        maxy = 0
        for c in s:
            if c == '\n':
                continue
            wx, name, bbox = self._metrics[ord(c)]

            total_width += wx + self._kern.get((namelast, name), 0)
            l, b, w, h = bbox
            miny = min(miny, b)
            maxy = max(maxy, b + h)

            namelast = name

        return total_width, maxy - miny

    def get_str_bbox_and_descent(self, s):
        """Return the string bounding box and the maximal descent."""
        if not len(s):
            return 0, 0, 0, 0, 0
        total_width = 0
        namelast = None
        miny = 1e9
        maxy = 0
        left = 0
        if not isinstance(s, str):
            s = _to_str(s)
        for c in s:
            if c == '\n':
                continue
            name = uni2type1.get(ord(c), f"uni{ord(c):04X}")
            try:
                wx, _, bbox = self._metrics_by_name[name]
            except KeyError:
                name = 'question'
                wx, _, bbox = self._metrics_by_name[name]
            total_width += wx + self._kern.get((namelast, name), 0)
            l, b, w, h = bbox
            left = min(left, l)
            miny = min(miny, b)
            maxy = max(maxy, b + h)

            namelast = name

        return left, miny, total_width, maxy - miny, -miny

    def get_str_bbox(self, s):
        """Return the string bounding box."""
        return self.get_str_bbox_and_descent(s)[:4]

    def get_name_char(self, c, isord=False):
        """Get the name of the character, i.e., ';' is 'semicolon'."""
        if not isord:
            c = ord(c)
        return self._metrics[c].name

    def get_width_char(self, c, isord=False):
        """
        Get the width of the character from the character metric WX field.
        """
        if not isord:
            c = ord(c)
        return self._metrics[c].width

    def get_width_from_char_name(self, name):
        """Get the width of the character from a type1 character name."""
        return self._metrics_by_name[name].width

    def get_height_char(self, c, isord=False):
        """Get the bounding box (ink) height of character *c* (space is 0)."""
        if not isord:
            c = ord(c)
        return self._metrics[c].bbox[-1]

    def get_kern_dist(self, c1, c2):
        """
        Return the kerning pair distance (possibly 0) for chars *c1* and *c2*.
        """
        name1, name2 = self.get_name_char(c1), self.get_name_char(c2)
        return self.get_kern_dist_from_name(name1, name2)

    def get_kern_dist_from_name(self, name1, name2):
        """
        Return the kerning pair distance (possibly 0) for chars
        *name1* and *name2*.
        """
        return self._kern.get((name1, name2), 0)

    def get_fontname(self):
        """Return the font name, e.g., 'Times-Roman'."""
        return self._header[b'FontName']

    @property
    def postscript_name(self):  # For consistency with FT2Font.
        return self.get_fontname()

    def get_fullname(self):
        """Return the font full name, e.g., 'Times-Roman'."""
        name = self._header.get(b'FullName')
        if name is None:  # use FontName as a substitute
            name = self._header[b'FontName']
        return name

    def get_familyname(self):
        """Return the font family name, e.g., 'Times'."""
        name = self._header.get(b'FamilyName')
        if name is not None:
            return name

        # FamilyName not specified so we'll make a guess
        name = self.get_fullname()
        extras = (r'(?i)([ -](regular|plain|italic|oblique|bold|semibold|'
                  r'light|ultralight|extra|condensed))+$')
        return re.sub(extras, '', name)

    @property
    def family_name(self):
        """The font family name, e.g., 'Times'."""
        return self.get_familyname()

    def get_weight(self):
        """Return the font weight, e.g., 'Bold' or 'Roman'."""
        return self._header[b'Weight']

    def get_angle(self):
        """Return the fontangle as float."""
        return self._header[b'ItalicAngle']

    def get_capheight(self):
        """Return the cap height as float."""
        return self._header[b'CapHeight']

    def get_xheight(self):
        """Return the xheight as float."""
        return self._header[b'XHeight']

    def get_underline_thickness(self):
        """Return the underline thickness as float."""
        return self._header[b'UnderlineThickness']

    def get_horizontal_stem_width(self):
        """
        Return the standard horizontal stem width as float, or *None* if
        not specified in AFM file.
        """
        return self._header.get(b'StdHW', None)

    def get_vertical_stem_width(self):
        """
        Return the standard vertical stem width as float, or *None* if
        not specified in AFM file.
        """
        return self._header.get(b'StdVW', None)

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_validators.py ===
"""Validator functions for standard library types.

Import of this module is deferred since it contains imports of many standard library modules.
"""

from __future__ import annotations as _annotations

import collections.abc
import math
import re
import typing
from decimal import Decimal
from fractions import Fraction
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from typing import Any, Callable, Union, cast, get_origin
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import typing_extensions
from pydantic_core import PydanticCustomError, core_schema
from pydantic_core._pydantic_core import PydanticKnownError
from typing_inspection import typing_objects

from pydantic._internal._import_utils import import_cached_field_info
from pydantic.errors import PydanticSchemaGenerationError


def sequence_validator(
    input_value: typing.Sequence[Any],
    /,
    validator: core_schema.ValidatorFunctionWrapHandler,
) -> typing.Sequence[Any]:
    """Validator for `Sequence` types, isinstance(v, Sequence) has already been called."""
    value_type = type(input_value)

    # We don't accept any plain string as a sequence
    # Relevant issue: https://github.com/pydantic/pydantic/issues/5595
    if issubclass(value_type, (str, bytes)):
        raise PydanticCustomError(
            'sequence_str',
            "'{type_name}' instances are not allowed as a Sequence value",
            {'type_name': value_type.__name__},
        )

    # TODO: refactor sequence validation to validate with either a list or a tuple
    # schema, depending on the type of the value.
    # Additionally, we should be able to remove one of either this validator or the
    # SequenceValidator in _std_types_schema.py (preferably this one, while porting over some logic).
    # Effectively, a refactor for sequence validation is needed.
    if value_type is tuple:
        input_value = list(input_value)

    v_list = validator(input_value)

    # the rest of the logic is just re-creating the original type from `v_list`
    if value_type is list:
        return v_list
    elif issubclass(value_type, range):
        # return the list as we probably can't re-create the range
        return v_list
    elif value_type is tuple:
        return tuple(v_list)
    else:
        # best guess at how to re-create the original type, more custom construction logic might be required
        return value_type(v_list)  # type: ignore[call-arg]


def import_string(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return _import_string_logic(value)
        except ImportError as e:
            raise PydanticCustomError('import_error', 'Invalid python path: {error}', {'error': str(e)}) from e
    else:
        # otherwise we just return the value and let the next validator do the rest of the work
        return value


def _import_string_logic(dotted_path: str) -> Any:
    """Inspired by uvicorn — dotted paths should include a colon before the final item if that item is not a module.
    (This is necessary to distinguish between a submodule and an attribute when there is a conflict.).

    If the dotted path does not include a colon and the final item is not a valid module, importing as an attribute
    rather than a submodule will be attempted automatically.

    So, for example, the following values of `dotted_path` result in the following returned values:
    * 'collections': <module 'collections'>
    * 'collections.abc': <module 'collections.abc'>
    * 'collections.abc:Mapping': <class 'collections.abc.Mapping'>
    * `collections.abc.Mapping`: <class 'collections.abc.Mapping'> (though this is a bit slower than the previous line)

    An error will be raised under any of the following scenarios:
    * `dotted_path` contains more than one colon (e.g., 'collections:abc:Mapping')
    * the substring of `dotted_path` before the colon is not a valid module in the environment (e.g., '123:Mapping')
    * the substring of `dotted_path` after the colon is not an attribute of the module (e.g., 'collections:abc123')
    """
    from importlib import import_module

    components = dotted_path.strip().split(':')
    if len(components) > 2:
        raise ImportError(f"Import strings should have at most one ':'; received {dotted_path!r}")

    module_path = components[0]
    if not module_path:
        raise ImportError(f'Import strings should have a nonempty module name; received {dotted_path!r}')

    try:
        module = import_module(module_path)
    except ModuleNotFoundError as e:
        if '.' in module_path:
            # Check if it would be valid if the final item was separated from its module with a `:`
            maybe_module_path, maybe_attribute = dotted_path.strip().rsplit('.', 1)
            try:
                return _import_string_logic(f'{maybe_module_path}:{maybe_attribute}')
            except ImportError:
                pass
            raise ImportError(f'No module named {module_path!r}') from e
        raise e

    if len(components) > 1:
        attribute = components[1]
        try:
            return getattr(module, attribute)
        except AttributeError as e:
            raise ImportError(f'cannot import name {attribute!r} from {module_path!r}') from e
    else:
        return module


def pattern_either_validator(input_value: Any, /) -> typing.Pattern[Any]:
    if isinstance(input_value, typing.Pattern):
        return input_value
    elif isinstance(input_value, (str, bytes)):
        # todo strict mode
        return compile_pattern(input_value)  # type: ignore
    else:
        raise PydanticCustomError('pattern_type', 'Input should be a valid pattern')


def pattern_str_validator(input_value: Any, /) -> typing.Pattern[str]:
    if isinstance(input_value, typing.Pattern):
        if isinstance(input_value.pattern, str):
            return input_value
        else:
            raise PydanticCustomError('pattern_str_type', 'Input should be a string pattern')
    elif isinstance(input_value, str):
        return compile_pattern(input_value)
    elif isinstance(input_value, bytes):
        raise PydanticCustomError('pattern_str_type', 'Input should be a string pattern')
    else:
        raise PydanticCustomError('pattern_type', 'Input should be a valid pattern')


def pattern_bytes_validator(input_value: Any, /) -> typing.Pattern[bytes]:
    if isinstance(input_value, typing.Pattern):
        if isinstance(input_value.pattern, bytes):
            return input_value
        else:
            raise PydanticCustomError('pattern_bytes_type', 'Input should be a bytes pattern')
    elif isinstance(input_value, bytes):
        return compile_pattern(input_value)
    elif isinstance(input_value, str):
        raise PydanticCustomError('pattern_bytes_type', 'Input should be a bytes pattern')
    else:
        raise PydanticCustomError('pattern_type', 'Input should be a valid pattern')


PatternType = typing.TypeVar('PatternType', str, bytes)


def compile_pattern(pattern: PatternType) -> typing.Pattern[PatternType]:
    try:
        return re.compile(pattern)
    except re.error:
        raise PydanticCustomError('pattern_regex', 'Input should be a valid regular expression')


def ip_v4_address_validator(input_value: Any, /) -> IPv4Address:
    if isinstance(input_value, IPv4Address):
        return input_value

    try:
        return IPv4Address(input_value)
    except ValueError:
        raise PydanticCustomError('ip_v4_address', 'Input is not a valid IPv4 address')


def ip_v6_address_validator(input_value: Any, /) -> IPv6Address:
    if isinstance(input_value, IPv6Address):
        return input_value

    try:
        return IPv6Address(input_value)
    except ValueError:
        raise PydanticCustomError('ip_v6_address', 'Input is not a valid IPv6 address')


def ip_v4_network_validator(input_value: Any, /) -> IPv4Network:
    """Assume IPv4Network initialised with a default `strict` argument.

    See more:
    https://docs.python.org/library/ipaddress.html#ipaddress.IPv4Network
    """
    if isinstance(input_value, IPv4Network):
        return input_value

    try:
        return IPv4Network(input_value)
    except ValueError:
        raise PydanticCustomError('ip_v4_network', 'Input is not a valid IPv4 network')


def ip_v6_network_validator(input_value: Any, /) -> IPv6Network:
    """Assume IPv6Network initialised with a default `strict` argument.

    See more:
    https://docs.python.org/library/ipaddress.html#ipaddress.IPv6Network
    """
    if isinstance(input_value, IPv6Network):
        return input_value

    try:
        return IPv6Network(input_value)
    except ValueError:
        raise PydanticCustomError('ip_v6_network', 'Input is not a valid IPv6 network')


def ip_v4_interface_validator(input_value: Any, /) -> IPv4Interface:
    if isinstance(input_value, IPv4Interface):
        return input_value

    try:
        return IPv4Interface(input_value)
    except ValueError:
        raise PydanticCustomError('ip_v4_interface', 'Input is not a valid IPv4 interface')


def ip_v6_interface_validator(input_value: Any, /) -> IPv6Interface:
    if isinstance(input_value, IPv6Interface):
        return input_value

    try:
        return IPv6Interface(input_value)
    except ValueError:
        raise PydanticCustomError('ip_v6_interface', 'Input is not a valid IPv6 interface')


def fraction_validator(input_value: Any, /) -> Fraction:
    if isinstance(input_value, Fraction):
        return input_value

    try:
        return Fraction(input_value)
    except ValueError:
        raise PydanticCustomError('fraction_parsing', 'Input is not a valid fraction')


def forbid_inf_nan_check(x: Any) -> Any:
    if not math.isfinite(x):
        raise PydanticKnownError('finite_number')
    return x


def _safe_repr(v: Any) -> int | float | str:
    """The context argument for `PydanticKnownError` requires a number or str type, so we do a simple repr() coercion for types like timedelta.

    See tests/test_types.py::test_annotated_metadata_any_order for some context.
    """
    if isinstance(v, (int, float, str)):
        return v
    return repr(v)


def greater_than_validator(x: Any, gt: Any) -> Any:
    try:
        if not (x > gt):
            raise PydanticKnownError('greater_than', {'gt': _safe_repr(gt)})
        return x
    except TypeError:
        raise TypeError(f"Unable to apply constraint 'gt' to supplied value {x}")


def greater_than_or_equal_validator(x: Any, ge: Any) -> Any:
    try:
        if not (x >= ge):
            raise PydanticKnownError('greater_than_equal', {'ge': _safe_repr(ge)})
        return x
    except TypeError:
        raise TypeError(f"Unable to apply constraint 'ge' to supplied value {x}")


def less_than_validator(x: Any, lt: Any) -> Any:
    try:
        if not (x < lt):
            raise PydanticKnownError('less_than', {'lt': _safe_repr(lt)})
        return x
    except TypeError:
        raise TypeError(f"Unable to apply constraint 'lt' to supplied value {x}")


def less_than_or_equal_validator(x: Any, le: Any) -> Any:
    try:
        if not (x <= le):
            raise PydanticKnownError('less_than_equal', {'le': _safe_repr(le)})
        return x
    except TypeError:
        raise TypeError(f"Unable to apply constraint 'le' to supplied value {x}")


def multiple_of_validator(x: Any, multiple_of: Any) -> Any:
    try:
        if x % multiple_of:
            raise PydanticKnownError('multiple_of', {'multiple_of': _safe_repr(multiple_of)})
        return x
    except TypeError:
        raise TypeError(f"Unable to apply constraint 'multiple_of' to supplied value {x}")


def min_length_validator(x: Any, min_length: Any) -> Any:
    try:
        if not (len(x) >= min_length):
            raise PydanticKnownError(
                'too_short', {'field_type': 'Value', 'min_length': min_length, 'actual_length': len(x)}
            )
        return x
    except TypeError:
        raise TypeError(f"Unable to apply constraint 'min_length' to supplied value {x}")


def max_length_validator(x: Any, max_length: Any) -> Any:
    try:
        if len(x) > max_length:
            raise PydanticKnownError(
                'too_long',
                {'field_type': 'Value', 'max_length': max_length, 'actual_length': len(x)},
            )
        return x
    except TypeError:
        raise TypeError(f"Unable to apply constraint 'max_length' to supplied value {x}")


def _extract_decimal_digits_info(decimal: Decimal) -> tuple[int, int]:
    """Compute the total number of digits and decimal places for a given [`Decimal`][decimal.Decimal] instance.

    This function handles both normalized and non-normalized Decimal instances.
    Example: Decimal('1.230') -> 4 digits, 3 decimal places

    Args:
        decimal (Decimal): The decimal number to analyze.

    Returns:
        tuple[int, int]: A tuple containing the number of decimal places and total digits.

    Though this could be divided into two separate functions, the logic is easier to follow if we couple the computation
    of the number of decimals and digits together.
    """
    try:
        decimal_tuple = decimal.as_tuple()

        assert isinstance(decimal_tuple.exponent, int)

        exponent = decimal_tuple.exponent
        num_digits = len(decimal_tuple.digits)

        if exponent >= 0:
            # A positive exponent adds that many trailing zeros
            # Ex: digit_tuple=(1, 2, 3), exponent=2 -> 12300 -> 0 decimal places, 5 digits
            num_digits += exponent
            decimal_places = 0
        else:
            # If the absolute value of the negative exponent is larger than the
            # number of digits, then it's the same as the number of digits,
            # because it'll consume all the digits in digit_tuple and then
            # add abs(exponent) - len(digit_tuple) leading zeros after the decimal point.
            # Ex: digit_tuple=(1, 2, 3), exponent=-2 -> 1.23 -> 2 decimal places, 3 digits
            # Ex: digit_tuple=(1, 2, 3), exponent=-4 -> 0.0123 -> 4 decimal places, 4 digits
            decimal_places = abs(exponent)
            num_digits = max(num_digits, decimal_places)

        return decimal_places, num_digits
    except (AssertionError, AttributeError):
        raise TypeError(f'Unable to extract decimal digits info from supplied value {decimal}')


def max_digits_validator(x: Any, max_digits: Any) -> Any:
    try:
        _, num_digits = _extract_decimal_digits_info(x)
        _, normalized_num_digits = _extract_decimal_digits_info(x.normalize())
        if (num_digits > max_digits) and (normalized_num_digits > max_digits):
            raise PydanticKnownError(
                'decimal_max_digits',
                {'max_digits': max_digits},
            )
        return x
    except TypeError:
        raise TypeError(f"Unable to apply constraint 'max_digits' to supplied value {x}")


def decimal_places_validator(x: Any, decimal_places: Any) -> Any:
    try:
        decimal_places_, _ = _extract_decimal_digits_info(x)
        if decimal_places_ > decimal_places:
            normalized_decimal_places, _ = _extract_decimal_digits_info(x.normalize())
            if normalized_decimal_places > decimal_places:
                raise PydanticKnownError(
                    'decimal_max_places',
                    {'decimal_places': decimal_places},
                )
        return x
    except TypeError:
        raise TypeError(f"Unable to apply constraint 'decimal_places' to supplied value {x}")


def deque_validator(input_value: Any, handler: core_schema.ValidatorFunctionWrapHandler) -> collections.deque[Any]:
    return collections.deque(handler(input_value), maxlen=getattr(input_value, 'maxlen', None))


def defaultdict_validator(
    input_value: Any, handler: core_schema.ValidatorFunctionWrapHandler, default_default_factory: Callable[[], Any]
) -> collections.defaultdict[Any, Any]:
    if isinstance(input_value, collections.defaultdict):
        default_factory = input_value.default_factory
        return collections.defaultdict(default_factory, handler(input_value))
    else:
        return collections.defaultdict(default_default_factory, handler(input_value))


def get_defaultdict_default_default_factory(values_source_type: Any) -> Callable[[], Any]:
    FieldInfo = import_cached_field_info()

    values_type_origin = get_origin(values_source_type)

    def infer_default() -> Callable[[], Any]:
        allowed_default_types: dict[Any, Any] = {
            tuple: tuple,
            collections.abc.Sequence: tuple,
            collections.abc.MutableSequence: list,
            list: list,
            typing.Sequence: list,
            set: set,
            typing.MutableSet: set,
            collections.abc.MutableSet: set,
            collections.abc.Set: frozenset,
            typing.MutableMapping: dict,
            typing.Mapping: dict,
            collections.abc.Mapping: dict,
            collections.abc.MutableMapping: dict,
            float: float,
            int: int,
            str: str,
            bool: bool,
        }
        values_type = values_type_origin or values_source_type
        instructions = 'set using `DefaultDict[..., Annotated[..., Field(default_factory=...)]]`'
        if typing_objects.is_typevar(values_type):

            def type_var_default_factory() -> None:
                raise RuntimeError(
                    'Generic defaultdict cannot be used without a concrete value type or an'
                    ' explicit default factory, ' + instructions
                )

            return type_var_default_factory
        elif values_type not in allowed_default_types:
            # a somewhat subjective set of types that have reasonable default values
            allowed_msg = ', '.join([t.__name__ for t in set(allowed_default_types.values())])
            raise PydanticSchemaGenerationError(
                f'Unable to infer a default factory for keys of type {values_source_type}.'
                f' Only {allowed_msg} are supported, other types require an explicit default factory'
                ' ' + instructions
            )
        return allowed_default_types[values_type]

    # Assume Annotated[..., Field(...)]
    if typing_objects.is_annotated(values_type_origin):
        field_info = next((v for v in typing_extensions.get_args(values_source_type) if isinstance(v, FieldInfo)), None)
    else:
        field_info = None
    if field_info and field_info.default_factory:
        # Assume the default factory does not take any argument:
        default_default_factory = cast(Callable[[], Any], field_info.default_factory)
    else:
        default_default_factory = infer_default()
    return default_default_factory


def validate_str_is_valid_iana_tz(value: Any, /) -> ZoneInfo:
    if isinstance(value, ZoneInfo):
        return value
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise PydanticCustomError('zoneinfo_str', 'invalid timezone: {value}', {'value': value})


NUMERIC_VALIDATOR_LOOKUP: dict[str, Callable] = {
    'gt': greater_than_validator,
    'ge': greater_than_or_equal_validator,
    'lt': less_than_validator,
    'le': less_than_or_equal_validator,
    'multiple_of': multiple_of_validator,
    'min_length': min_length_validator,
    'max_length': max_length_validator,
    'max_digits': max_digits_validator,
    'decimal_places': decimal_places_validator,
}

IpType = Union[IPv4Address, IPv6Address, IPv4Network, IPv6Network, IPv4Interface, IPv6Interface]

IP_VALIDATOR_LOOKUP: dict[type[IpType], Callable] = {
    IPv4Address: ip_v4_address_validator,
    IPv6Address: ip_v6_address_validator,
    IPv4Network: ip_v4_network_validator,
    IPv6Network: ip_v6_network_validator,
    IPv4Interface: ip_v4_interface_validator,
    IPv6Interface: ip_v6_interface_validator,
}

MAPPING_ORIGIN_MAP: dict[Any, Any] = {
    typing.DefaultDict: collections.defaultdict,  # noqa: UP006
    collections.defaultdict: collections.defaultdict,
    typing.OrderedDict: collections.OrderedDict,  # noqa: UP006
    collections.OrderedDict: collections.OrderedDict,
    typing_extensions.OrderedDict: collections.OrderedDict,
    typing.Counter: collections.Counter,
    collections.Counter: collections.Counter,
    # this doesn't handle subclasses of these
    typing.Mapping: dict,
    typing.MutableMapping: dict,
    # parametrized typing.{Mutable}Mapping creates one of these
    collections.abc.Mapping: dict,
    collections.abc.MutableMapping: dict,
}

# === NexusCore/openenv\Lib\site-packages\fontTools\cu2qu\cu2qu.py ===
# cython: language_level=3
# distutils: define_macros=CYTHON_TRACE_NOGIL=1

# Copyright 2015 Google Inc. All Rights Reserved.
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

try:
    import cython
except (AttributeError, ImportError):
    # if cython not installed, use mock module with no-op decorators and types
    from fontTools.misc import cython
COMPILED = cython.compiled

import math

from .errors import Error as Cu2QuError, ApproxNotFoundError


__all__ = ["curve_to_quadratic", "curves_to_quadratic"]

MAX_N = 100

NAN = float("NaN")


@cython.cfunc
@cython.inline
@cython.returns(cython.double)
@cython.locals(v1=cython.complex, v2=cython.complex)
def dot(v1, v2):
    """Return the dot product of two vectors.

    Args:
        v1 (complex): First vector.
        v2 (complex): Second vector.

    Returns:
        double: Dot product.
    """
    return (v1 * v2.conjugate()).real


@cython.cfunc
@cython.inline
@cython.locals(a=cython.complex, b=cython.complex, c=cython.complex, d=cython.complex)
@cython.locals(
    _1=cython.complex, _2=cython.complex, _3=cython.complex, _4=cython.complex
)
def calc_cubic_points(a, b, c, d):
    _1 = d
    _2 = (c / 3.0) + d
    _3 = (b + c) / 3.0 + _2
    _4 = a + d + c + b
    return _1, _2, _3, _4


@cython.cfunc
@cython.inline
@cython.locals(
    p0=cython.complex, p1=cython.complex, p2=cython.complex, p3=cython.complex
)
@cython.locals(a=cython.complex, b=cython.complex, c=cython.complex, d=cython.complex)
def calc_cubic_parameters(p0, p1, p2, p3):
    c = (p1 - p0) * 3.0
    b = (p2 - p1) * 3.0 - c
    d = p0
    a = p3 - d - c - b
    return a, b, c, d


@cython.cfunc
@cython.inline
@cython.locals(
    p0=cython.complex, p1=cython.complex, p2=cython.complex, p3=cython.complex
)
def split_cubic_into_n_iter(p0, p1, p2, p3, n):
    """Split a cubic Bezier into n equal parts.

    Splits the curve into `n` equal parts by curve time.
    (t=0..1/n, t=1/n..2/n, ...)

    Args:
        p0 (complex): Start point of curve.
        p1 (complex): First handle of curve.
        p2 (complex): Second handle of curve.
        p3 (complex): End point of curve.

    Returns:
        An iterator yielding the control points (four complex values) of the
        subcurves.
    """
    # Hand-coded special-cases
    if n == 2:
        return iter(split_cubic_into_two(p0, p1, p2, p3))
    if n == 3:
        return iter(split_cubic_into_three(p0, p1, p2, p3))
    if n == 4:
        a, b = split_cubic_into_two(p0, p1, p2, p3)
        return iter(
            split_cubic_into_two(a[0], a[1], a[2], a[3])
            + split_cubic_into_two(b[0], b[1], b[2], b[3])
        )
    if n == 6:
        a, b = split_cubic_into_two(p0, p1, p2, p3)
        return iter(
            split_cubic_into_three(a[0], a[1], a[2], a[3])
            + split_cubic_into_three(b[0], b[1], b[2], b[3])
        )

    return _split_cubic_into_n_gen(p0, p1, p2, p3, n)


@cython.locals(
    p0=cython.complex,
    p1=cython.complex,
    p2=cython.complex,
    p3=cython.complex,
    n=cython.int,
)
@cython.locals(a=cython.complex, b=cython.complex, c=cython.complex, d=cython.complex)
@cython.locals(
    dt=cython.double, delta_2=cython.double, delta_3=cython.double, i=cython.int
)
@cython.locals(
    a1=cython.complex, b1=cython.complex, c1=cython.complex, d1=cython.complex
)
def _split_cubic_into_n_gen(p0, p1, p2, p3, n):
    a, b, c, d = calc_cubic_parameters(p0, p1, p2, p3)
    dt = 1 / n
    delta_2 = dt * dt
    delta_3 = dt * delta_2
    for i in range(n):
        t1 = i * dt
        t1_2 = t1 * t1
        # calc new a, b, c and d
        a1 = a * delta_3
        b1 = (3 * a * t1 + b) * delta_2
        c1 = (2 * b * t1 + c + 3 * a * t1_2) * dt
        d1 = a * t1 * t1_2 + b * t1_2 + c * t1 + d
        yield calc_cubic_points(a1, b1, c1, d1)


@cython.cfunc
@cython.inline
@cython.locals(
    p0=cython.complex, p1=cython.complex, p2=cython.complex, p3=cython.complex
)
@cython.locals(mid=cython.complex, deriv3=cython.complex)
def split_cubic_into_two(p0, p1, p2, p3):
    """Split a cubic Bezier into two equal parts.

    Splits the curve into two equal parts at t = 0.5

    Args:
        p0 (complex): Start point of curve.
        p1 (complex): First handle of curve.
        p2 (complex): Second handle of curve.
        p3 (complex): End point of curve.

    Returns:
        tuple: Two cubic Beziers (each expressed as a tuple of four complex
        values).
    """
    mid = (p0 + 3 * (p1 + p2) + p3) * 0.125
    deriv3 = (p3 + p2 - p1 - p0) * 0.125
    return (
        (p0, (p0 + p1) * 0.5, mid - deriv3, mid),
        (mid, mid + deriv3, (p2 + p3) * 0.5, p3),
    )


@cython.cfunc
@cython.inline
@cython.locals(
    p0=cython.complex,
    p1=cython.complex,
    p2=cython.complex,
    p3=cython.complex,
)
@cython.locals(
    mid1=cython.complex,
    deriv1=cython.complex,
    mid2=cython.complex,
    deriv2=cython.complex,
)
def split_cubic_into_three(p0, p1, p2, p3):
    """Split a cubic Bezier into three equal parts.

    Splits the curve into three equal parts at t = 1/3 and t = 2/3

    Args:
        p0 (complex): Start point of curve.
        p1 (complex): First handle of curve.
        p2 (complex): Second handle of curve.
        p3 (complex): End point of curve.

    Returns:
        tuple: Three cubic Beziers (each expressed as a tuple of four complex
        values).
    """
    mid1 = (8 * p0 + 12 * p1 + 6 * p2 + p3) * (1 / 27)
    deriv1 = (p3 + 3 * p2 - 4 * p0) * (1 / 27)
    mid2 = (p0 + 6 * p1 + 12 * p2 + 8 * p3) * (1 / 27)
    deriv2 = (4 * p3 - 3 * p1 - p0) * (1 / 27)
    return (
        (p0, (2 * p0 + p1) / 3.0, mid1 - deriv1, mid1),
        (mid1, mid1 + deriv1, mid2 - deriv2, mid2),
        (mid2, mid2 + deriv2, (p2 + 2 * p3) / 3.0, p3),
    )


@cython.cfunc
@cython.inline
@cython.returns(cython.complex)
@cython.locals(
    t=cython.double,
    p0=cython.complex,
    p1=cython.complex,
    p2=cython.complex,
    p3=cython.complex,
)
@cython.locals(_p1=cython.complex, _p2=cython.complex)
def cubic_approx_control(t, p0, p1, p2, p3):
    """Approximate a cubic Bezier using a quadratic one.

    Args:
        t (double): Position of control point.
        p0 (complex): Start point of curve.
        p1 (complex): First handle of curve.
        p2 (complex): Second handle of curve.
        p3 (complex): End point of curve.

    Returns:
        complex: Location of candidate control point on quadratic curve.
    """
    _p1 = p0 + (p1 - p0) * 1.5
    _p2 = p3 + (p2 - p3) * 1.5
    return _p1 + (_p2 - _p1) * t


@cython.cfunc
@cython.inline
@cython.returns(cython.complex)
@cython.locals(a=cython.complex, b=cython.complex, c=cython.complex, d=cython.complex)
@cython.locals(ab=cython.complex, cd=cython.complex, p=cython.complex, h=cython.double)
def calc_intersect(a, b, c, d):
    """Calculate the intersection of two lines.

    Args:
        a (complex): Start point of first line.
        b (complex): End point of first line.
        c (complex): Start point of second line.
        d (complex): End point of second line.

    Returns:
        complex: Location of intersection if one present, ``complex(NaN,NaN)``
        if no intersection was found.
    """
    ab = b - a
    cd = d - c
    p = ab * 1j
    try:
        h = dot(p, a - c) / dot(p, cd)
    except ZeroDivisionError:
        return complex(NAN, NAN)
    return c + cd * h


@cython.cfunc
@cython.returns(cython.int)
@cython.locals(
    tolerance=cython.double,
    p0=cython.complex,
    p1=cython.complex,
    p2=cython.complex,
    p3=cython.complex,
)
@cython.locals(mid=cython.complex, deriv3=cython.complex)
def cubic_farthest_fit_inside(p0, p1, p2, p3, tolerance):
    """Check if a cubic Bezier lies within a given distance of the origin.

    "Origin" means *the* origin (0,0), not the start of the curve. Note that no
    checks are made on the start and end positions of the curve; this function
    only checks the inside of the curve.

    Args:
        p0 (complex): Start point of curve.
        p1 (complex): First handle of curve.
        p2 (complex): Second handle of curve.
        p3 (complex): End point of curve.
        tolerance (double): Distance from origin.

    Returns:
        bool: True if the cubic Bezier ``p`` entirely lies within a distance
        ``tolerance`` of the origin, False otherwise.
    """
    # First check p2 then p1, as p2 has higher error early on.
    if abs(p2) <= tolerance and abs(p1) <= tolerance:
        return True

    # Split.
    mid = (p0 + 3 * (p1 + p2) + p3) * 0.125
    if abs(mid) > tolerance:
        return False
    deriv3 = (p3 + p2 - p1 - p0) * 0.125
    return cubic_farthest_fit_inside(
        p0, (p0 + p1) * 0.5, mid - deriv3, mid, tolerance
    ) and cubic_farthest_fit_inside(mid, mid + deriv3, (p2 + p3) * 0.5, p3, tolerance)


@cython.cfunc
@cython.inline
@cython.locals(tolerance=cython.double)
@cython.locals(
    q1=cython.complex,
    c0=cython.complex,
    c1=cython.complex,
    c2=cython.complex,
    c3=cython.complex,
)
def cubic_approx_quadratic(cubic, tolerance):
    """Approximate a cubic Bezier with a single quadratic within a given tolerance.

    Args:
        cubic (sequence): Four complex numbers representing control points of
            the cubic Bezier curve.
        tolerance (double): Permitted deviation from the original curve.

    Returns:
        Three complex numbers representing control points of the quadratic
        curve if it fits within the given tolerance, or ``None`` if no suitable
        curve could be calculated.
    """

    q1 = calc_intersect(cubic[0], cubic[1], cubic[2], cubic[3])
    if math.isnan(q1.imag):
        return None
    c0 = cubic[0]
    c3 = cubic[3]
    c1 = c0 + (q1 - c0) * (2 / 3)
    c2 = c3 + (q1 - c3) * (2 / 3)
    if not cubic_farthest_fit_inside(0, c1 - cubic[1], c2 - cubic[2], 0, tolerance):
        return None
    return c0, q1, c3


@cython.cfunc
@cython.locals(n=cython.int, tolerance=cython.double)
@cython.locals(i=cython.int)
@cython.locals(all_quadratic=cython.int)
@cython.locals(
    c0=cython.complex, c1=cython.complex, c2=cython.complex, c3=cython.complex
)
@cython.locals(
    q0=cython.complex,
    q1=cython.complex,
    next_q1=cython.complex,
    q2=cython.complex,
    d1=cython.complex,
)
def cubic_approx_spline(cubic, n, tolerance, all_quadratic):
    """Approximate a cubic Bezier curve with a spline of n quadratics.

    Args:
        cubic (sequence): Four complex numbers representing control points of
            the cubic Bezier curve.
        n (int): Number of quadratic Bezier curves in the spline.
        tolerance (double): Permitted deviation from the original curve.

    Returns:
        A list of ``n+2`` complex numbers, representing control points of the
        quadratic spline if it fits within the given tolerance, or ``None`` if
        no suitable spline could be calculated.
    """

    if n == 1:
        return cubic_approx_quadratic(cubic, tolerance)
    if n == 2 and all_quadratic == False:
        return cubic

    cubics = split_cubic_into_n_iter(cubic[0], cubic[1], cubic[2], cubic[3], n)

    # calculate the spline of quadratics and check errors at the same time.
    next_cubic = next(cubics)
    next_q1 = cubic_approx_control(
        0, next_cubic[0], next_cubic[1], next_cubic[2], next_cubic[3]
    )
    q2 = cubic[0]
    d1 = 0j
    spline = [cubic[0], next_q1]
    for i in range(1, n + 1):
        # Current cubic to convert
        c0, c1, c2, c3 = next_cubic

        # Current quadratic approximation of current cubic
        q0 = q2
        q1 = next_q1
        if i < n:
            next_cubic = next(cubics)
            next_q1 = cubic_approx_control(
                i / (n - 1), next_cubic[0], next_cubic[1], next_cubic[2], next_cubic[3]
            )
            spline.append(next_q1)
            q2 = (q1 + next_q1) * 0.5
        else:
            q2 = c3

        # End-point deltas
        d0 = d1
        d1 = q2 - c3

        if abs(d1) > tolerance or not cubic_farthest_fit_inside(
            d0,
            q0 + (q1 - q0) * (2 / 3) - c1,
            q2 + (q1 - q2) * (2 / 3) - c2,
            d1,
            tolerance,
        ):
            return None
    spline.append(cubic[3])

    return spline


@cython.locals(max_err=cython.double)
@cython.locals(n=cython.int)
@cython.locals(all_quadratic=cython.int)
def curve_to_quadratic(curve, max_err, all_quadratic=True):
    """Approximate a cubic Bezier curve with a spline of n quadratics.

    Args:
        cubic (sequence): Four 2D tuples representing control points of
            the cubic Bezier curve.
        max_err (double): Permitted deviation from the original curve.
        all_quadratic (bool): If True (default) returned value is a
            quadratic spline. If False, it's either a single quadratic
            curve or a single cubic curve.

    Returns:
        If all_quadratic is True: A list of 2D tuples, representing
        control points of the quadratic spline if it fits within the
        given tolerance, or ``None`` if no suitable spline could be
        calculated.

        If all_quadratic is False: Either a quadratic curve (if length
        of output is 3), or a cubic curve (if length of output is 4).
    """

    curve = [complex(*p) for p in curve]

    for n in range(1, MAX_N + 1):
        spline = cubic_approx_spline(curve, n, max_err, all_quadratic)
        if spline is not None:
            # done. go home
            return [(s.real, s.imag) for s in spline]

    raise ApproxNotFoundError(curve)


@cython.locals(l=cython.int, last_i=cython.int, i=cython.int)
@cython.locals(all_quadratic=cython.int)
def curves_to_quadratic(curves, max_errors, all_quadratic=True):
    """Return quadratic Bezier splines approximating the input cubic Beziers.

    Args:
        curves: A sequence of *n* curves, each curve being a sequence of four
            2D tuples.
        max_errors: A sequence of *n* floats representing the maximum permissible
            deviation from each of the cubic Bezier curves.
        all_quadratic (bool): If True (default) returned values are a
            quadratic spline. If False, they are either a single quadratic
            curve or a single cubic curve.

    Example::

        >>> curves_to_quadratic( [
        ...   [ (50,50), (100,100), (150,100), (200,50) ],
        ...   [ (75,50), (120,100), (150,75),  (200,60) ]
        ... ], [1,1] )
        [[(50.0, 50.0), (75.0, 75.0), (125.0, 91.66666666666666), (175.0, 75.0), (200.0, 50.0)], [(75.0, 50.0), (97.5, 75.0), (135.41666666666666, 82.08333333333333), (175.0, 67.5), (200.0, 60.0)]]

    The returned splines have "implied oncurve points" suitable for use in
    TrueType ``glif`` outlines - i.e. in the first spline returned above,
    the first quadratic segment runs from (50,50) to
    ( (75 + 125)/2 , (120 + 91.666..)/2 ) = (100, 83.333...).

    Returns:
        If all_quadratic is True, a list of splines, each spline being a list
        of 2D tuples.

        If all_quadratic is False, a list of curves, each curve being a quadratic
        (length 3), or cubic (length 4).

    Raises:
        fontTools.cu2qu.Errors.ApproxNotFoundError: if no suitable approximation
        can be found for all curves with the given parameters.
    """

    curves = [[complex(*p) for p in curve] for curve in curves]
    assert len(max_errors) == len(curves)

    l = len(curves)
    splines = [None] * l
    last_i = i = 0
    n = 1
    while True:
        spline = cubic_approx_spline(curves[i], n, max_errors[i], all_quadratic)
        if spline is None:
            if n == MAX_N:
                break
            n += 1
            last_i = i
            continue
        splines[i] = spline
        i = (i + 1) % l
        if i == last_i:
            # done. go home
            return [[(s.real, s.imag) for s in spline] for spline in splines]

    raise ApproxNotFoundError(curves)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\batches_endpoints\endpoints.py ===
######################################################################

#                          /v1/batches Endpoints


######################################################################
import asyncio
from typing import Dict, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.batches.main import CancelBatchRequest, RetrieveBatchRequest
from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.common_request_processing import ProxyBaseLLMRequestProcessing
from litellm.proxy.common_utils.http_parsing_utils import _read_request_body
from litellm.proxy.common_utils.openai_endpoint_utils import (
    get_custom_llm_provider_from_request_body,
)
from litellm.proxy.openai_files_endpoints.common_utils import (
    _is_base64_encoded_unified_file_id,
    get_models_from_unified_file_id,
)
from litellm.proxy.utils import handle_exception_on_proxy, is_known_model
from litellm.types.llms.openai import LiteLLMBatchCreateRequest

router = APIRouter()


@router.post(
    "/{provider}/v1/batches",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
@router.post(
    "/v1/batches",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
@router.post(
    "/batches",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
async def create_batch(
    request: Request,
    fastapi_response: Response,
    provider: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Create large batches of API requests for asynchronous processing.
    This is the equivalent of POST https://api.openai.com/v1/batch
    Supports Identical Params as: https://platform.openai.com/docs/api-reference/batch

    Example Curl
    ```
    curl http://localhost:4000/v1/batches \
        -H "Authorization: Bearer sk-1234" \
        -H "Content-Type: application/json" \
        -d '{
            "input_file_id": "file-abc123",
            "endpoint": "/v1/chat/completions",
            "completion_window": "24h"
    }'
    ```
    """
    from litellm.proxy.proxy_server import (
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data: Dict = {}
    try:
        data = await _read_request_body(request=request)
        verbose_proxy_logger.debug(
            "Request received by LiteLLM:\n{}".format(json.dumps(data, indent=4)),
        )
        base_llm_response_processor = ProxyBaseLLMRequestProcessing(data=data)
        (
            data,
            litellm_logging_obj,
        ) = await base_llm_response_processor.common_processing_pre_call_logic(
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_logging_obj=proxy_logging_obj,
            proxy_config=proxy_config,
            route_type="acreate_batch",
        )

        ## check if model is a loadbalanced model
        router_model: Optional[str] = None
        is_router_model = False
        if litellm.enable_loadbalancing_on_batch_endpoints is True:
            router_model = data.get("model", None)
            is_router_model = is_known_model(model=router_model, llm_router=llm_router)

        custom_llm_provider = (
            provider or data.pop("custom_llm_provider", None) or "openai"
        )
        _create_batch_data = LiteLLMBatchCreateRequest(**data)
        input_file_id = _create_batch_data.get("input_file_id", None)
        unified_file_id: Union[str, Literal[False]] = False
        if input_file_id:
            unified_file_id = _is_base64_encoded_unified_file_id(input_file_id)
        if (
            litellm.enable_loadbalancing_on_batch_endpoints is True
            and is_router_model
            and router_model is not None
        ):
            if llm_router is None:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "LLM Router not initialized. Ensure models added to proxy."
                    },
                )

            response = await llm_router.acreate_batch(**_create_batch_data)  # type: ignore
        elif (
            unified_file_id and input_file_id
        ):  # litellm_proxy:application/octet-stream;unified_id,c4843482-b176-4901-8292-7523fd0f2c6e;target_model_names,gpt-4o-mini
            target_model_names = get_models_from_unified_file_id(unified_file_id)
            ## EXPECTS 1 MODEL
            if len(target_model_names) != 1:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Expected 1 model, got {}".format(
                            len(target_model_names)
                        )
                    },
                )
            model = target_model_names[0]
            _create_batch_data["model"] = model
            if llm_router is None:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "LLM Router not initialized. Ensure models added to proxy."
                    },
                )

            response = await llm_router.acreate_batch(**_create_batch_data)
            response.input_file_id = input_file_id
            response._hidden_params["unified_file_id"] = unified_file_id
        else:
            response = await litellm.acreate_batch(
                custom_llm_provider=custom_llm_provider, **_create_batch_data  # type: ignore
            )

        ### CALL HOOKS ### - modify outgoing data
        response = await proxy_logging_obj.post_call_success_hook(
            data=data, user_api_key_dict=user_api_key_dict, response=response
        )

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.create_batch(): Exception occured - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)


@router.get(
    "/{provider}/v1/batches/{batch_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
@router.get(
    "/v1/batches/{batch_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
@router.get(
    "/batches/{batch_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
async def retrieve_batch(
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    provider: Optional[str] = None,
    batch_id: str = Path(
        title="Batch ID to retrieve", description="The ID of the batch to retrieve"
    ),
):
    """
    Retrieves a batch.
    This is the equivalent of GET https://api.openai.com/v1/batches/{batch_id}
    Supports Identical Params as: https://platform.openai.com/docs/api-reference/batch/retrieve

    Example Curl
    ```
    curl http://localhost:4000/v1/batches/batch_abc123 \
    -H "Authorization: Bearer sk-1234" \
    -H "Content-Type: application/json" \

    ```
    """
    from litellm.proxy.proxy_server import (
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data: Dict = {}
    try:
        ## check if model is a loadbalanced model
        _retrieve_batch_request = RetrieveBatchRequest(
            batch_id=batch_id,
        )

        data = cast(dict, _retrieve_batch_request)
        unified_batch_id = _is_base64_encoded_unified_file_id(batch_id)

        base_llm_response_processor = ProxyBaseLLMRequestProcessing(data=data)
        (
            data,
            litellm_logging_obj,
        ) = await base_llm_response_processor.common_processing_pre_call_logic(
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_logging_obj=proxy_logging_obj,
            proxy_config=proxy_config,
            route_type="aretrieve_batch",
        )

        if litellm.enable_loadbalancing_on_batch_endpoints is True or unified_batch_id:
            if llm_router is None:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "LLM Router not initialized. Ensure models added to proxy."
                    },
                )

            response = await llm_router.aretrieve_batch(**data)  # type: ignore
            response._hidden_params["unified_batch_id"] = unified_batch_id
        else:
            custom_llm_provider = (
                provider
                or await get_custom_llm_provider_from_request_body(request=request)
                or "openai"
            )
            response = await litellm.aretrieve_batch(
                custom_llm_provider=custom_llm_provider, **data  # type: ignore
            )

        ### CALL HOOKS ### - modify outgoing data
        response = await proxy_logging_obj.post_call_success_hook(
            data=data, user_api_key_dict=user_api_key_dict, response=response
        )

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.retrieve_batch(): Exception occured - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)


@router.get(
    "/{provider}/v1/batches",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
@router.get(
    "/v1/batches",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
@router.get(
    "/batches",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
async def list_batches(
    request: Request,
    fastapi_response: Response,
    provider: Optional[str] = None,
    limit: Optional[int] = None,
    after: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Lists 
    This is the equivalent of GET https://api.openai.com/v1/batches/
    Supports Identical Params as: https://platform.openai.com/docs/api-reference/batch/list

    Example Curl
    ```
    curl http://localhost:4000/v1/batches?limit=2 \
    -H "Authorization: Bearer sk-1234" \
    -H "Content-Type: application/json" \

    ```
    """
    from litellm.proxy.proxy_server import proxy_logging_obj, version

    verbose_proxy_logger.debug("GET /v1/batches after={} limit={}".format(after, limit))
    try:
        custom_llm_provider = (
            provider
            or await get_custom_llm_provider_from_request_body(request=request)
            or "openai"
        )
        response = await litellm.alist_batches(
            custom_llm_provider=custom_llm_provider,  # type: ignore
            after=after,
            limit=limit,
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict,
            original_exception=e,
            request_data={"after": after, "limit": limit},
        )
        verbose_proxy_logger.error(
            "litellm.proxy.proxy_server.retrieve_batch(): Exception occured - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)


@router.post(
    "/{provider}/v1/batches/{batch_id:path}/cancel",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
@router.post(
    "/v1/batches/{batch_id:path}/cancel",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
@router.post(
    "/batches/{batch_id:path}/cancel",
    dependencies=[Depends(user_api_key_auth)],
    tags=["batch"],
)
async def cancel_batch(
    request: Request,
    batch_id: str,
    fastapi_response: Response,
    provider: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Cancel a batch.
    This is the equivalent of POST https://api.openai.com/v1/batches/{batch_id}/cancel

    Supports Identical Params as: https://platform.openai.com/docs/api-reference/batch/cancel

    Example Curl
    ```
    curl http://localhost:4000/v1/batches/batch_abc123/cancel \
        -H "Authorization: Bearer sk-1234" \
        -H "Content-Type: application/json" \
        -X POST

    ```
    """
    from litellm.proxy.proxy_server import (
        add_litellm_data_to_request,
        general_settings,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data: Dict = {}
    try:
        data = await _read_request_body(request=request)
        verbose_proxy_logger.debug(
            "Request received by LiteLLM:\n{}".format(json.dumps(data, indent=4)),
        )

        # Include original request and headers in the data
        data = await add_litellm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        custom_llm_provider = (
            provider or data.pop("custom_llm_provider", None) or "openai"
        )
        _cancel_batch_data = CancelBatchRequest(batch_id=batch_id, **data)
        response = await litellm.acancel_batch(
            custom_llm_provider=custom_llm_provider,  # type: ignore
            **_cancel_batch_data
        )

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.create_batch(): Exception occured - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)


######################################################################

#            END OF  /v1/batches Endpoints Implementation

######################################################################

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\services\generative_service\transports\grpc_asyncio.py ===
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

from google.ai.generativelanguage_v1.types import generative_service

from .base import DEFAULT_CLIENT_INFO, GenerativeServiceTransport
from .grpc import GenerativeServiceGrpcTransport


class GenerativeServiceGrpcAsyncIOTransport(GenerativeServiceTransport):
    """gRPC AsyncIO backend transport for GenerativeService.

    API for using Large Models that generate multimodal content
    and have additional capabilities beyond text generation.

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
    def generate_content(
        self,
    ) -> Callable[
        [generative_service.GenerateContentRequest],
        Awaitable[generative_service.GenerateContentResponse],
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
                    Awaitable[~.GenerateContentResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_content" not in self._stubs:
            self._stubs["generate_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1.GenerativeService/GenerateContent",
                request_serializer=generative_service.GenerateContentRequest.serialize,
                response_deserializer=generative_service.GenerateContentResponse.deserialize,
            )
        return self._stubs["generate_content"]

    @property
    def stream_generate_content(
        self,
    ) -> Callable[
        [generative_service.GenerateContentRequest],
        Awaitable[generative_service.GenerateContentResponse],
    ]:
        r"""Return a callable for the stream generate content method over gRPC.

        Generates a streamed response from the model given an input
        ``GenerateContentRequest``.

        Returns:
            Callable[[~.GenerateContentRequest],
                    Awaitable[~.GenerateContentResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "stream_generate_content" not in self._stubs:
            self._stubs["stream_generate_content"] = self.grpc_channel.unary_stream(
                "/google.ai.generativelanguage.v1.GenerativeService/StreamGenerateContent",
                request_serializer=generative_service.GenerateContentRequest.serialize,
                response_deserializer=generative_service.GenerateContentResponse.deserialize,
            )
        return self._stubs["stream_generate_content"]

    @property
    def embed_content(
        self,
    ) -> Callable[
        [generative_service.EmbedContentRequest],
        Awaitable[generative_service.EmbedContentResponse],
    ]:
        r"""Return a callable for the embed content method over gRPC.

        Generates an embedding from the model given an input
        ``Content``.

        Returns:
            Callable[[~.EmbedContentRequest],
                    Awaitable[~.EmbedContentResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "embed_content" not in self._stubs:
            self._stubs["embed_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1.GenerativeService/EmbedContent",
                request_serializer=generative_service.EmbedContentRequest.serialize,
                response_deserializer=generative_service.EmbedContentResponse.deserialize,
            )
        return self._stubs["embed_content"]

    @property
    def batch_embed_contents(
        self,
    ) -> Callable[
        [generative_service.BatchEmbedContentsRequest],
        Awaitable[generative_service.BatchEmbedContentsResponse],
    ]:
        r"""Return a callable for the batch embed contents method over gRPC.

        Generates multiple embeddings from the model given
        input text in a synchronous call.

        Returns:
            Callable[[~.BatchEmbedContentsRequest],
                    Awaitable[~.BatchEmbedContentsResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_embed_contents" not in self._stubs:
            self._stubs["batch_embed_contents"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1.GenerativeService/BatchEmbedContents",
                request_serializer=generative_service.BatchEmbedContentsRequest.serialize,
                response_deserializer=generative_service.BatchEmbedContentsResponse.deserialize,
            )
        return self._stubs["batch_embed_contents"]

    @property
    def count_tokens(
        self,
    ) -> Callable[
        [generative_service.CountTokensRequest],
        Awaitable[generative_service.CountTokensResponse],
    ]:
        r"""Return a callable for the count tokens method over gRPC.

        Runs a model's tokenizer on input content and returns
        the token count.

        Returns:
            Callable[[~.CountTokensRequest],
                    Awaitable[~.CountTokensResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_tokens" not in self._stubs:
            self._stubs["count_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1.GenerativeService/CountTokens",
                request_serializer=generative_service.CountTokensRequest.serialize,
                response_deserializer=generative_service.CountTokensResponse.deserialize,
            )
        return self._stubs["count_tokens"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.generate_content: gapic_v1.method_async.wrap_method(
                self.generate_content,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=600.0,
                ),
                default_timeout=600.0,
                client_info=client_info,
            ),
            self.stream_generate_content: gapic_v1.method_async.wrap_method(
                self.stream_generate_content,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=600.0,
                ),
                default_timeout=600.0,
                client_info=client_info,
            ),
            self.embed_content: gapic_v1.method_async.wrap_method(
                self.embed_content,
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
            self.batch_embed_contents: gapic_v1.method_async.wrap_method(
                self.batch_embed_contents,
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
            self.count_tokens: gapic_v1.method_async.wrap_method(
                self.count_tokens,
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

    @property
    def cancel_operation(
        self,
    ) -> Callable[[operations_pb2.CancelOperationRequest], None]:
        r"""Return a callable for the cancel_operation method over gRPC."""
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "cancel_operation" not in self._stubs:
            self._stubs["cancel_operation"] = self.grpc_channel.unary_unary(
                "/google.longrunning.Operations/CancelOperation",
                request_serializer=operations_pb2.CancelOperationRequest.SerializeToString,
                response_deserializer=None,
            )
        return self._stubs["cancel_operation"]

    @property
    def get_operation(
        self,
    ) -> Callable[[operations_pb2.GetOperationRequest], operations_pb2.Operation]:
        r"""Return a callable for the get_operation method over gRPC."""
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_operation" not in self._stubs:
            self._stubs["get_operation"] = self.grpc_channel.unary_unary(
                "/google.longrunning.Operations/GetOperation",
                request_serializer=operations_pb2.GetOperationRequest.SerializeToString,
                response_deserializer=operations_pb2.Operation.FromString,
            )
        return self._stubs["get_operation"]

    @property
    def list_operations(
        self,
    ) -> Callable[
        [operations_pb2.ListOperationsRequest], operations_pb2.ListOperationsResponse
    ]:
        r"""Return a callable for the list_operations method over gRPC."""
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_operations" not in self._stubs:
            self._stubs["list_operations"] = self.grpc_channel.unary_unary(
                "/google.longrunning.Operations/ListOperations",
                request_serializer=operations_pb2.ListOperationsRequest.SerializeToString,
                response_deserializer=operations_pb2.ListOperationsResponse.FromString,
            )
        return self._stubs["list_operations"]


__all__ = ("GenerativeServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\backend_cairo.py ===
"""
A Cairo backend for Matplotlib
==============================
:Author: Steve Chaplin and others

This backend depends on cairocffi or pycairo.
"""

import functools
import gzip
import math

import numpy as np

try:
    import cairo
    if cairo.version_info < (1, 14, 0):  # Introduced set_device_scale.
        raise ImportError(f"Cairo backend requires cairo>=1.14.0, "
                          f"but only {cairo.version_info} is available")
except ImportError:
    try:
        import cairocffi as cairo
    except ImportError as err:
        raise ImportError(
            "cairo backend requires that pycairo>=1.14.0 or cairocffi "
            "is installed") from err

from .. import _api, cbook, font_manager
from matplotlib.backend_bases import (
    _Backend, FigureCanvasBase, FigureManagerBase, GraphicsContextBase,
    RendererBase)
from matplotlib.font_manager import ttfFontProperty
from matplotlib.path import Path
from matplotlib.transforms import Affine2D


def _set_rgba(ctx, color, alpha, forced_alpha):
    if len(color) == 3 or forced_alpha:
        ctx.set_source_rgba(*color[:3], alpha)
    else:
        ctx.set_source_rgba(*color)


def _append_path(ctx, path, transform, clip=None):
    for points, code in path.iter_segments(
            transform, remove_nans=True, clip=clip):
        if code == Path.MOVETO:
            ctx.move_to(*points)
        elif code == Path.CLOSEPOLY:
            ctx.close_path()
        elif code == Path.LINETO:
            ctx.line_to(*points)
        elif code == Path.CURVE3:
            cur = np.asarray(ctx.get_current_point())
            a = points[:2]
            b = points[-2:]
            ctx.curve_to(*(cur / 3 + a * 2 / 3), *(a * 2 / 3 + b / 3), *b)
        elif code == Path.CURVE4:
            ctx.curve_to(*points)


def _cairo_font_args_from_font_prop(prop):
    """
    Convert a `.FontProperties` or a `.FontEntry` to arguments that can be
    passed to `.Context.select_font_face`.
    """
    def attr(field):
        try:
            return getattr(prop, f"get_{field}")()
        except AttributeError:
            return getattr(prop, field)

    name = attr("name")
    slant = getattr(cairo, f"FONT_SLANT_{attr('style').upper()}")
    weight = attr("weight")
    weight = (cairo.FONT_WEIGHT_NORMAL
              if font_manager.weight_dict.get(weight, weight) < 550
              else cairo.FONT_WEIGHT_BOLD)
    return name, slant, weight


class RendererCairo(RendererBase):
    def __init__(self, dpi):
        self.dpi = dpi
        self.gc = GraphicsContextCairo(renderer=self)
        self.width = None
        self.height = None
        self.text_ctx = cairo.Context(
           cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
        super().__init__()

    def set_context(self, ctx):
        surface = ctx.get_target()
        if hasattr(surface, "get_width") and hasattr(surface, "get_height"):
            size = surface.get_width(), surface.get_height()
        elif hasattr(surface, "get_extents"):  # GTK4 RecordingSurface.
            ext = surface.get_extents()
            size = ext.width, ext.height
        else:  # vector surfaces.
            ctx.save()
            ctx.reset_clip()
            rect, *rest = ctx.copy_clip_rectangle_list()
            if rest:
                raise TypeError("Cannot infer surface size")
            _, _, *size = rect
            ctx.restore()
        self.gc.ctx = ctx
        self.width, self.height = size

    @staticmethod
    def _fill_and_stroke(ctx, fill_c, alpha, alpha_overrides):
        if fill_c is not None:
            ctx.save()
            _set_rgba(ctx, fill_c, alpha, alpha_overrides)
            ctx.fill_preserve()
            ctx.restore()
        ctx.stroke()

    def draw_path(self, gc, path, transform, rgbFace=None):
        # docstring inherited
        ctx = gc.ctx
        # Clip the path to the actual rendering extents if it isn't filled.
        clip = (ctx.clip_extents()
                if rgbFace is None and gc.get_hatch() is None
                else None)
        transform = (transform
                     + Affine2D().scale(1, -1).translate(0, self.height))
        ctx.new_path()
        _append_path(ctx, path, transform, clip)
        if rgbFace is not None:
            ctx.save()
            _set_rgba(ctx, rgbFace, gc.get_alpha(), gc.get_forced_alpha())
            ctx.fill_preserve()
            ctx.restore()
        hatch_path = gc.get_hatch_path()
        if hatch_path:
            dpi = int(self.dpi)
            hatch_surface = ctx.get_target().create_similar(
                cairo.Content.COLOR_ALPHA, dpi, dpi)
            hatch_ctx = cairo.Context(hatch_surface)
            _append_path(hatch_ctx, hatch_path,
                         Affine2D().scale(dpi, -dpi).translate(0, dpi),
                         None)
            hatch_ctx.set_line_width(self.points_to_pixels(gc.get_hatch_linewidth()))
            hatch_ctx.set_source_rgba(*gc.get_hatch_color())
            hatch_ctx.fill_preserve()
            hatch_ctx.stroke()
            hatch_pattern = cairo.SurfacePattern(hatch_surface)
            hatch_pattern.set_extend(cairo.Extend.REPEAT)
            ctx.save()
            ctx.set_source(hatch_pattern)
            ctx.fill_preserve()
            ctx.restore()
        ctx.stroke()

    def draw_markers(self, gc, marker_path, marker_trans, path, transform,
                     rgbFace=None):
        # docstring inherited

        ctx = gc.ctx
        ctx.new_path()
        # Create the path for the marker; it needs to be flipped here already!
        _append_path(ctx, marker_path, marker_trans + Affine2D().scale(1, -1))
        marker_path = ctx.copy_path_flat()

        # Figure out whether the path has a fill
        x1, y1, x2, y2 = ctx.fill_extents()
        if x1 == 0 and y1 == 0 and x2 == 0 and y2 == 0:
            filled = False
            # No fill, just unset this (so we don't try to fill it later on)
            rgbFace = None
        else:
            filled = True

        transform = (transform
                     + Affine2D().scale(1, -1).translate(0, self.height))

        ctx.new_path()
        for i, (vertices, codes) in enumerate(
                path.iter_segments(transform, simplify=False)):
            if len(vertices):
                x, y = vertices[-2:]
                ctx.save()

                # Translate and apply path
                ctx.translate(x, y)
                ctx.append_path(marker_path)

                ctx.restore()

                # Slower code path if there is a fill; we need to draw
                # the fill and stroke for each marker at the same time.
                # Also flush out the drawing every once in a while to
                # prevent the paths from getting way too long.
                if filled or i % 1000 == 0:
                    self._fill_and_stroke(
                        ctx, rgbFace, gc.get_alpha(), gc.get_forced_alpha())

        # Fast path, if there is no fill, draw everything in one step
        if not filled:
            self._fill_and_stroke(
                ctx, rgbFace, gc.get_alpha(), gc.get_forced_alpha())

    def draw_image(self, gc, x, y, im):
        im = cbook._unmultiplied_rgba8888_to_premultiplied_argb32(im[::-1])
        surface = cairo.ImageSurface.create_for_data(
            im.ravel().data, cairo.FORMAT_ARGB32,
            im.shape[1], im.shape[0], im.shape[1] * 4)
        ctx = gc.ctx
        y = self.height - y - im.shape[0]

        ctx.save()
        ctx.set_source_surface(surface, float(x), float(y))
        ctx.paint()
        ctx.restore()

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False, mtext=None):
        # docstring inherited

        # Note: (x, y) are device/display coords, not user-coords, unlike other
        # draw_* methods
        if ismath:
            self._draw_mathtext(gc, x, y, s, prop, angle)

        else:
            ctx = gc.ctx
            ctx.new_path()
            ctx.move_to(x, y)

            ctx.save()
            ctx.select_font_face(*_cairo_font_args_from_font_prop(prop))
            ctx.set_font_size(self.points_to_pixels(prop.get_size_in_points()))
            opts = cairo.FontOptions()
            opts.set_antialias(gc.get_antialiased())
            ctx.set_font_options(opts)
            if angle:
                ctx.rotate(np.deg2rad(-angle))
            ctx.show_text(s)
            ctx.restore()

    def _draw_mathtext(self, gc, x, y, s, prop, angle):
        ctx = gc.ctx
        width, height, descent, glyphs, rects = \
            self._text2path.mathtext_parser.parse(s, self.dpi, prop)

        ctx.save()
        ctx.translate(x, y)
        if angle:
            ctx.rotate(np.deg2rad(-angle))

        for font, fontsize, idx, ox, oy in glyphs:
            ctx.new_path()
            ctx.move_to(ox, -oy)
            ctx.select_font_face(
                *_cairo_font_args_from_font_prop(ttfFontProperty(font)))
            ctx.set_font_size(self.points_to_pixels(fontsize))
            ctx.show_text(chr(idx))

        for ox, oy, w, h in rects:
            ctx.new_path()
            ctx.rectangle(ox, -oy, w, -h)
            ctx.set_source_rgb(0, 0, 0)
            ctx.fill_preserve()

        ctx.restore()

    def get_canvas_width_height(self):
        # docstring inherited
        return self.width, self.height

    def get_text_width_height_descent(self, s, prop, ismath):
        # docstring inherited

        if ismath == 'TeX':
            return super().get_text_width_height_descent(s, prop, ismath)

        if ismath:
            width, height, descent, *_ = \
                self._text2path.mathtext_parser.parse(s, self.dpi, prop)
            return width, height, descent

        ctx = self.text_ctx
        # problem - scale remembers last setting and font can become
        # enormous causing program to crash
        # save/restore prevents the problem
        ctx.save()
        ctx.select_font_face(*_cairo_font_args_from_font_prop(prop))
        ctx.set_font_size(self.points_to_pixels(prop.get_size_in_points()))

        y_bearing, w, h = ctx.text_extents(s)[1:4]
        ctx.restore()

        return w, h, h + y_bearing

    def new_gc(self):
        # docstring inherited
        self.gc.ctx.save()
        # FIXME: The following doesn't properly implement a stack-like behavior
        # and relies instead on the (non-guaranteed) fact that artists never
        # rely on nesting gc states, so directly resetting the attributes (IOW
        # a single-level stack) is enough.
        self.gc._alpha = 1
        self.gc._forced_alpha = False  # if True, _alpha overrides A from RGBA
        self.gc._hatch = None
        return self.gc

    def points_to_pixels(self, points):
        # docstring inherited
        return points / 72 * self.dpi


class GraphicsContextCairo(GraphicsContextBase):
    _joind = {
        'bevel':  cairo.LINE_JOIN_BEVEL,
        'miter':  cairo.LINE_JOIN_MITER,
        'round':  cairo.LINE_JOIN_ROUND,
    }

    _capd = {
        'butt':        cairo.LINE_CAP_BUTT,
        'projecting':  cairo.LINE_CAP_SQUARE,
        'round':       cairo.LINE_CAP_ROUND,
    }

    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer

    def restore(self):
        self.ctx.restore()

    def set_alpha(self, alpha):
        super().set_alpha(alpha)
        _set_rgba(
            self.ctx, self._rgb, self.get_alpha(), self.get_forced_alpha())

    def set_antialiased(self, b):
        self.ctx.set_antialias(
            cairo.ANTIALIAS_DEFAULT if b else cairo.ANTIALIAS_NONE)

    def get_antialiased(self):
        return self.ctx.get_antialias()

    def set_capstyle(self, cs):
        self.ctx.set_line_cap(_api.check_getitem(self._capd, capstyle=cs))
        self._capstyle = cs

    def set_clip_rectangle(self, rectangle):
        if not rectangle:
            return
        x, y, w, h = np.round(rectangle.bounds)
        ctx = self.ctx
        ctx.new_path()
        ctx.rectangle(x, self.renderer.height - h - y, w, h)
        ctx.clip()

    def set_clip_path(self, path):
        if not path:
            return
        tpath, affine = path.get_transformed_path_and_affine()
        ctx = self.ctx
        ctx.new_path()
        affine = (affine
                  + Affine2D().scale(1, -1).translate(0, self.renderer.height))
        _append_path(ctx, tpath, affine)
        ctx.clip()

    def set_dashes(self, offset, dashes):
        self._dashes = offset, dashes
        if dashes is None:
            self.ctx.set_dash([], 0)  # switch dashes off
        else:
            self.ctx.set_dash(
                list(self.renderer.points_to_pixels(np.asarray(dashes))),
                offset)

    def set_foreground(self, fg, isRGBA=None):
        super().set_foreground(fg, isRGBA)
        if len(self._rgb) == 3:
            self.ctx.set_source_rgb(*self._rgb)
        else:
            self.ctx.set_source_rgba(*self._rgb)

    def get_rgb(self):
        return self.ctx.get_source().get_rgba()[:3]

    def set_joinstyle(self, js):
        self.ctx.set_line_join(_api.check_getitem(self._joind, joinstyle=js))
        self._joinstyle = js

    def set_linewidth(self, w):
        self._linewidth = float(w)
        self.ctx.set_line_width(self.renderer.points_to_pixels(w))


class _CairoRegion:
    def __init__(self, slices, data):
        self._slices = slices
        self._data = data


class FigureCanvasCairo(FigureCanvasBase):
    @property
    def _renderer(self):
        # In theory, _renderer should be set in __init__, but GUI canvas
        # subclasses (FigureCanvasFooCairo) don't always interact well with
        # multiple inheritance (FigureCanvasFoo inits but doesn't super-init
        # FigureCanvasCairo), so initialize it in the getter instead.
        if not hasattr(self, "_cached_renderer"):
            self._cached_renderer = RendererCairo(self.figure.dpi)
        return self._cached_renderer

    def get_renderer(self):
        return self._renderer

    def copy_from_bbox(self, bbox):
        surface = self._renderer.gc.ctx.get_target()
        if not isinstance(surface, cairo.ImageSurface):
            raise RuntimeError(
                "copy_from_bbox only works when rendering to an ImageSurface")
        sw = surface.get_width()
        sh = surface.get_height()
        x0 = math.ceil(bbox.x0)
        x1 = math.floor(bbox.x1)
        y0 = math.ceil(sh - bbox.y1)
        y1 = math.floor(sh - bbox.y0)
        if not (0 <= x0 and x1 <= sw and bbox.x0 <= bbox.x1
                and 0 <= y0 and y1 <= sh and bbox.y0 <= bbox.y1):
            raise ValueError("Invalid bbox")
        sls = slice(y0, y0 + max(y1 - y0, 0)), slice(x0, x0 + max(x1 - x0, 0))
        data = (np.frombuffer(surface.get_data(), np.uint32)
                .reshape((sh, sw))[sls].copy())
        return _CairoRegion(sls, data)

    def restore_region(self, region):
        surface = self._renderer.gc.ctx.get_target()
        if not isinstance(surface, cairo.ImageSurface):
            raise RuntimeError(
                "restore_region only works when rendering to an ImageSurface")
        surface.flush()
        sw = surface.get_width()
        sh = surface.get_height()
        sly, slx = region._slices
        (np.frombuffer(surface.get_data(), np.uint32)
         .reshape((sh, sw))[sly, slx]) = region._data
        surface.mark_dirty_rectangle(
            slx.start, sly.start, slx.stop - slx.start, sly.stop - sly.start)

    def print_png(self, fobj):
        self._get_printed_image_surface().write_to_png(fobj)

    def print_rgba(self, fobj):
        width, height = self.get_width_height()
        buf = self._get_printed_image_surface().get_data()
        fobj.write(cbook._premultiplied_argb32_to_unmultiplied_rgba8888(
            np.asarray(buf).reshape((width, height, 4))))

    print_raw = print_rgba

    def _get_printed_image_surface(self):
        self._renderer.dpi = self.figure.dpi
        width, height = self.get_width_height()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self._renderer.set_context(cairo.Context(surface))
        self.figure.draw(self._renderer)
        return surface

    def _save(self, fmt, fobj, *, orientation='portrait'):
        # save PDF/PS/SVG

        dpi = 72
        self.figure.dpi = dpi
        w_in, h_in = self.figure.get_size_inches()
        width_in_points, height_in_points = w_in * dpi, h_in * dpi

        if orientation == 'landscape':
            width_in_points, height_in_points = (
                height_in_points, width_in_points)

        if fmt == 'ps':
            if not hasattr(cairo, 'PSSurface'):
                raise RuntimeError('cairo has not been compiled with PS '
                                   'support enabled')
            surface = cairo.PSSurface(fobj, width_in_points, height_in_points)
        elif fmt == 'pdf':
            if not hasattr(cairo, 'PDFSurface'):
                raise RuntimeError('cairo has not been compiled with PDF '
                                   'support enabled')
            surface = cairo.PDFSurface(fobj, width_in_points, height_in_points)
        elif fmt in ('svg', 'svgz'):
            if not hasattr(cairo, 'SVGSurface'):
                raise RuntimeError('cairo has not been compiled with SVG '
                                   'support enabled')
            if fmt == 'svgz':
                if isinstance(fobj, str):
                    fobj = gzip.GzipFile(fobj, 'wb')
                else:
                    fobj = gzip.GzipFile(None, 'wb', fileobj=fobj)
            surface = cairo.SVGSurface(fobj, width_in_points, height_in_points)
        else:
            raise ValueError(f"Unknown format: {fmt!r}")

        self._renderer.dpi = self.figure.dpi
        self._renderer.set_context(cairo.Context(surface))
        ctx = self._renderer.gc.ctx

        if orientation == 'landscape':
            ctx.rotate(np.pi / 2)
            ctx.translate(0, -height_in_points)
            # Perhaps add an '%%Orientation: Landscape' comment?

        self.figure.draw(self._renderer)

        ctx.show_page()
        surface.finish()
        if fmt == 'svgz':
            fobj.close()

    print_pdf = functools.partialmethod(_save, "pdf")
    print_ps = functools.partialmethod(_save, "ps")
    print_svg = functools.partialmethod(_save, "svg")
    print_svgz = functools.partialmethod(_save, "svgz")


@_Backend.export
class _BackendCairo(_Backend):
    backend_version = cairo.version
    FigureCanvas = FigureCanvasCairo
    FigureManager = FigureManagerBase

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_plugins\jinja2_debug.py ===
from _pydevd_bundle.pydevd_constants import STATE_SUSPEND, JINJA2_SUSPEND
from _pydevd_bundle.pydevd_comm import CMD_SET_BREAK, CMD_ADD_EXCEPTION_BREAK
from pydevd_file_utils import canonical_normalized_path
from _pydevd_bundle.pydevd_frame_utils import add_exception_to_frame, FCode
from _pydev_bundle import pydev_log
from pydevd_plugins.pydevd_line_validation import LineBreakpointWithLazyValidation, ValidationInfo
from _pydev_bundle.pydev_override import overrides
from _pydevd_bundle.pydevd_api import PyDevdAPI


class Jinja2LineBreakpoint(LineBreakpointWithLazyValidation):
    def __init__(
        self, canonical_normalized_filename, breakpoint_id, line, condition, func_name, expression, hit_condition=None, is_logpoint=False
    ):
        self.canonical_normalized_filename = canonical_normalized_filename
        LineBreakpointWithLazyValidation.__init__(
            self, breakpoint_id, line, condition, func_name, expression, hit_condition=hit_condition, is_logpoint=is_logpoint
        )

    def __str__(self):
        return "Jinja2LineBreakpoint: %s-%d" % (self.canonical_normalized_filename, self.line)


class _Jinja2ValidationInfo(ValidationInfo):
    @overrides(ValidationInfo._collect_valid_lines_in_template_uncached)
    def _collect_valid_lines_in_template_uncached(self, template):
        lineno_mapping = _get_frame_lineno_mapping(template)
        if not lineno_mapping:
            return set()

        return set(x[0] for x in lineno_mapping)


def add_line_breakpoint(
    pydb,
    type,
    canonical_normalized_filename,
    breakpoint_id,
    line,
    condition,
    expression,
    func_name,
    hit_condition=None,
    is_logpoint=False,
    add_breakpoint_result=None,
    on_changed_breakpoint_state=None,
):
    if type == "jinja2-line":
        jinja2_line_breakpoint = Jinja2LineBreakpoint(
            canonical_normalized_filename,
            breakpoint_id,
            line,
            condition,
            func_name,
            expression,
            hit_condition=hit_condition,
            is_logpoint=is_logpoint,
        )
        if not hasattr(pydb, "jinja2_breakpoints"):
            _init_plugin_breaks(pydb)

        add_breakpoint_result.error_code = PyDevdAPI.ADD_BREAKPOINT_LAZY_VALIDATION
        jinja2_line_breakpoint.add_breakpoint_result = add_breakpoint_result
        jinja2_line_breakpoint.on_changed_breakpoint_state = on_changed_breakpoint_state

        return jinja2_line_breakpoint, pydb.jinja2_breakpoints
    return None


def after_breakpoints_consolidated(py_db, canonical_normalized_filename, id_to_pybreakpoint, file_to_line_to_breakpoints):
    jinja2_breakpoints_for_file = file_to_line_to_breakpoints.get(canonical_normalized_filename)
    if not jinja2_breakpoints_for_file:
        return

    if not hasattr(py_db, "jinja2_validation_info"):
        _init_plugin_breaks(py_db)

    # In general we validate the breakpoints only when the template is loaded, but if the template
    # was already loaded, we can validate the breakpoints based on the last loaded value.
    py_db.jinja2_validation_info.verify_breakpoints_from_template_cached_lines(
        py_db, canonical_normalized_filename, jinja2_breakpoints_for_file
    )


def add_exception_breakpoint(pydb, type, exception):
    if type == "jinja2":
        if not hasattr(pydb, "jinja2_exception_break"):
            _init_plugin_breaks(pydb)
        pydb.jinja2_exception_break[exception] = True
        return True
    return False


def _init_plugin_breaks(pydb):
    pydb.jinja2_exception_break = {}
    pydb.jinja2_breakpoints = {}

    pydb.jinja2_validation_info = _Jinja2ValidationInfo()


def remove_all_exception_breakpoints(pydb):
    if hasattr(pydb, "jinja2_exception_break"):
        pydb.jinja2_exception_break = {}
        return True
    return False


def remove_exception_breakpoint(pydb, exception_type, exception):
    if exception_type == "jinja2":
        try:
            del pydb.jinja2_exception_break[exception]
            return True
        except KeyError:
            pass
    return False


def get_breakpoints(pydb, breakpoint_type):
    if breakpoint_type == "jinja2-line":
        return pydb.jinja2_breakpoints
    return None


def _is_jinja2_render_call(frame):
    try:
        name = frame.f_code.co_name
        if "__jinja_template__" in frame.f_globals and name in ("root", "loop", "macro") or name.startswith("block_"):
            return True
        return False
    except:
        pydev_log.exception()
        return False


def _suspend_jinja2(pydb, thread, frame, cmd=CMD_SET_BREAK, message=None):
    frame = Jinja2TemplateFrame(frame)

    if frame.f_lineno is None:
        return None

    pydb.set_suspend(thread, cmd)

    thread.additional_info.suspend_type = JINJA2_SUSPEND
    if cmd == CMD_ADD_EXCEPTION_BREAK:
        # send exception name as message
        if message:
            message = str(message)
        thread.additional_info.pydev_message = message

    return frame


def _is_jinja2_suspended(thread):
    return thread.additional_info.suspend_type == JINJA2_SUSPEND


def _is_jinja2_context_call(frame):
    return "_Context__obj" in frame.f_locals


def _is_jinja2_internal_function(frame):
    return "self" in frame.f_locals and frame.f_locals["self"].__class__.__name__ in (
        "LoopContext",
        "TemplateReference",
        "Macro",
        "BlockReference",
    )


def _find_jinja2_render_frame(frame):
    while frame is not None and not _is_jinja2_render_call(frame):
        frame = frame.f_back

    return frame


# =======================================================================================================================
# Jinja2 Frame
# =======================================================================================================================


class Jinja2TemplateFrame(object):
    IS_PLUGIN_FRAME = True

    def __init__(self, frame, original_filename=None, template_lineno=None):
        if original_filename is None:
            original_filename = _get_jinja2_template_original_filename(frame)

        if template_lineno is None:
            template_lineno = _get_jinja2_template_line(frame)

        self.back_context = None
        if "context" in frame.f_locals:
            # sometimes we don't have 'context', e.g. in macros
            self.back_context = frame.f_locals["context"]
        self.f_code = FCode("template", original_filename)
        self.f_lineno = template_lineno
        self.f_back = frame
        self.f_globals = {}
        self.f_locals = self.collect_context(frame)
        self.f_trace = None

    def _get_real_var_name(self, orig_name):
        # replace leading number for local variables
        parts = orig_name.split("_")
        if len(parts) > 1 and parts[0].isdigit():
            return parts[1]
        return orig_name

    def collect_context(self, frame):
        res = {}
        for k, v in frame.f_locals.items():
            if not k.startswith("l_"):
                res[k] = v
            elif v and not _is_missing(v):
                res[self._get_real_var_name(k[2:])] = v
        if self.back_context is not None:
            for k, v in self.back_context.items():
                res[k] = v
        return res

    def _change_variable(self, frame, name, value):
        in_vars_or_parents = False
        if "context" in frame.f_locals:
            if name in frame.f_locals["context"].parent:
                self.back_context.parent[name] = value
                in_vars_or_parents = True
            if name in frame.f_locals["context"].vars:
                self.back_context.vars[name] = value
                in_vars_or_parents = True

        l_name = "l_" + name
        if l_name in frame.f_locals:
            if in_vars_or_parents:
                frame.f_locals[l_name] = self.back_context.resolve(name)
            else:
                frame.f_locals[l_name] = value


class Jinja2TemplateSyntaxErrorFrame(object):
    IS_PLUGIN_FRAME = True

    def __init__(self, frame, exception_cls_name, filename, lineno, f_locals):
        self.f_code = FCode("Jinja2 %s" % (exception_cls_name,), filename)
        self.f_lineno = lineno
        self.f_back = frame
        self.f_globals = {}
        self.f_locals = f_locals
        self.f_trace = None


def change_variable(frame, attr, expression, default, scope=None):
    if isinstance(frame, Jinja2TemplateFrame):
        result = eval(expression, frame.f_globals, frame.f_locals)
        frame._change_variable(frame.f_back, attr, result, scope=scope)
        return result
    return default


def _is_missing(item):
    if item.__class__.__name__ == "MissingType":
        return True
    return False


def _find_render_function_frame(frame):
    # in order to hide internal rendering functions
    old_frame = frame
    try:
        while not (
            "self" in frame.f_locals and frame.f_locals["self"].__class__.__name__ == "Template" and frame.f_code.co_name == "render"
        ):
            frame = frame.f_back
            if frame is None:
                return old_frame
        return frame
    except:
        return old_frame


def _get_jinja2_template_debug_info(frame):
    frame_globals = frame.f_globals

    jinja_template = frame_globals.get("__jinja_template__")

    if jinja_template is None:
        return None

    return _get_frame_lineno_mapping(jinja_template)


def _get_frame_lineno_mapping(jinja_template):
    """
    :rtype: list(tuple(int,int))
    :return: list((original_line, line_in_frame))
    """
    # _debug_info is a string with the mapping from frame line to actual line
    # i.e.: "5=13&8=14"
    _debug_info = jinja_template._debug_info
    if not _debug_info:
        # Sometimes template contains only plain text.
        return None

    # debug_info is a list with the mapping from frame line to actual line
    # i.e.: [(5, 13), (8, 14)]
    return jinja_template.debug_info


def _get_jinja2_template_line(frame):
    debug_info = _get_jinja2_template_debug_info(frame)
    if debug_info is None:
        return None

    lineno = frame.f_lineno

    for pair in debug_info:
        if pair[1] == lineno:
            return pair[0]

    return None


def _convert_to_str(s):
    return s


def _get_jinja2_template_original_filename(frame):
    if "__jinja_template__" in frame.f_globals:
        return _convert_to_str(frame.f_globals["__jinja_template__"].filename)

    return None


# =======================================================================================================================
# Jinja2 Step Commands
# =======================================================================================================================


def has_exception_breaks(py_db):
    if len(py_db.jinja2_exception_break) > 0:
        return True
    return False


def has_line_breaks(py_db):
    for _canonical_normalized_filename, breakpoints in py_db.jinja2_breakpoints.items():
        if len(breakpoints) > 0:
            return True
    return False


def can_skip(pydb, frame):
    if pydb.jinja2_breakpoints and _is_jinja2_render_call(frame):
        filename = _get_jinja2_template_original_filename(frame)
        if filename is not None:
            canonical_normalized_filename = canonical_normalized_path(filename)
            jinja2_breakpoints_for_file = pydb.jinja2_breakpoints.get(canonical_normalized_filename)
            if jinja2_breakpoints_for_file:
                return False

    if pydb.jinja2_exception_break:
        name = frame.f_code.co_name

        # errors in compile time
        if name in ("template", "top-level template code", "<module>") or name.startswith("block "):
            f_back = frame.f_back
            module_name = ""
            if f_back is not None:
                module_name = f_back.f_globals.get("__name__", "")
            if module_name.startswith("jinja2."):
                return False

    return True


is_tracked_frame = _is_jinja2_render_call


def required_events_breakpoint():
    return ("line",)


def required_events_stepping():
    return ("call", "line", "return")


def cmd_step_into(pydb, frame, event, info, thread, stop_info, stop):
    plugin_stop = False
    if _is_jinja2_suspended(thread):
        plugin_stop = stop_info["jinja2_stop"] = event in ("call", "line") and _is_jinja2_render_call(frame)
        stop = False
        if info.pydev_call_from_jinja2 is not None:
            if _is_jinja2_internal_function(frame):
                # if internal Jinja2 function was called, we should continue debugging inside template
                info.pydev_call_from_jinja2 = None
            else:
                # we go into python code from Jinja2 rendering frame
                stop = True

        if event == "call" and _is_jinja2_context_call(frame.f_back):
            # we called function from context, the next step will be in function
            info.pydev_call_from_jinja2 = 1

    if event == "return" and _is_jinja2_context_call(frame.f_back):
        # we return from python code to Jinja2 rendering frame
        info.pydev_step_stop = info.pydev_call_from_jinja2
        info.pydev_call_from_jinja2 = None
        thread.additional_info.suspend_type = JINJA2_SUSPEND
        stop = False

        # print "info.pydev_call_from_jinja2", info.pydev_call_from_jinja2, "stop_info", stop_info, \
        #    "thread.additional_info.suspend_type", thread.additional_info.suspend_type
        # print "event", event, "farme.locals", frame.f_locals
    return stop, plugin_stop


def cmd_step_over(pydb, frame, event, info, thread, stop_info, stop):
    plugin_stop = False
    if _is_jinja2_suspended(thread):
        stop = False

        if info.pydev_call_inside_jinja2 is None:
            if _is_jinja2_render_call(frame):
                if event == "call":
                    info.pydev_call_inside_jinja2 = frame.f_back
                if event in ("line", "return"):
                    info.pydev_call_inside_jinja2 = frame
        else:
            if event == "line":
                if _is_jinja2_render_call(frame) and info.pydev_call_inside_jinja2 is frame:
                    plugin_stop = stop_info["jinja2_stop"] = True
            if event == "return":
                if frame is info.pydev_call_inside_jinja2 and "event" not in frame.f_back.f_locals:
                    info.pydev_call_inside_jinja2 = _find_jinja2_render_frame(frame.f_back)
        return stop, plugin_stop
    else:
        if event == "return" and _is_jinja2_context_call(frame.f_back):
            # we return from python code to Jinja2 rendering frame
            info.pydev_call_from_jinja2 = None
            info.pydev_call_inside_jinja2 = _find_jinja2_render_frame(frame)
            thread.additional_info.suspend_type = JINJA2_SUSPEND
            stop = False
            return stop, plugin_stop
    # print "info.pydev_call_from_jinja2", info.pydev_call_from_jinja2, "stop", stop, "jinja_stop", jinja2_stop, \
    #    "thread.additional_info.suspend_type", thread.additional_info.suspend_type
    # print "event", event, "info.pydev_call_inside_jinja2", info.pydev_call_inside_jinja2
    # print "frame", frame, "frame.f_back", frame.f_back, "step_stop", info.pydev_step_stop
    # print "is_context_call", _is_jinja2_context_call(frame)
    # print "render", _is_jinja2_render_call(frame)
    # print "-------------"
    return stop, plugin_stop


def stop(pydb, frame, event, thread, stop_info, arg, step_cmd):
    if "jinja2_stop" in stop_info and stop_info["jinja2_stop"]:
        frame = _suspend_jinja2(pydb, thread, frame, step_cmd)
        if frame:
            pydb.do_wait_suspend(thread, frame, event, arg)
            return True
    return False


def get_breakpoint(py_db, frame, event, info):
    break_type = "jinja2"

    if event == "line" and info.pydev_state != STATE_SUSPEND and py_db.jinja2_breakpoints and _is_jinja2_render_call(frame):
        jinja_template = frame.f_globals.get("__jinja_template__")
        if jinja_template is None:
            return None

        original_filename = _get_jinja2_template_original_filename(frame)
        if original_filename is not None:
            pydev_log.debug("Jinja2 is rendering a template: %s", original_filename)
            canonical_normalized_filename = canonical_normalized_path(original_filename)
            jinja2_breakpoints_for_file = py_db.jinja2_breakpoints.get(canonical_normalized_filename)

            if jinja2_breakpoints_for_file:
                jinja2_validation_info = py_db.jinja2_validation_info
                jinja2_validation_info.verify_breakpoints(py_db, canonical_normalized_filename, jinja2_breakpoints_for_file, jinja_template)

                template_lineno = _get_jinja2_template_line(frame)
                if template_lineno is not None:
                    jinja2_breakpoint = jinja2_breakpoints_for_file.get(template_lineno)
                    if jinja2_breakpoint is not None:
                        new_frame = Jinja2TemplateFrame(frame, original_filename, template_lineno)
                        return jinja2_breakpoint, new_frame, break_type

    return None


def suspend(pydb, thread, frame, bp_type):
    if bp_type == "jinja2":
        return _suspend_jinja2(pydb, thread, frame)
    return None


def exception_break(pydb, frame, thread, arg, is_unwind):
    exception, value, trace = arg
    if pydb.jinja2_exception_break and exception is not None:
        exception_type = list(pydb.jinja2_exception_break.keys())[0]
        if exception.__name__ in ("UndefinedError", "TemplateNotFound", "TemplatesNotFound"):
            # errors in rendering
            render_frame = _find_jinja2_render_frame(frame)
            if render_frame:
                suspend_frame = _suspend_jinja2(pydb, thread, render_frame, CMD_ADD_EXCEPTION_BREAK, message=exception_type)
                if suspend_frame:
                    add_exception_to_frame(suspend_frame, (exception, value, trace))
                    suspend_frame.f_back = frame
                    frame = suspend_frame
                    return True, frame

        elif exception.__name__ in ("TemplateSyntaxError", "TemplateAssertionError"):
            name = frame.f_code.co_name

            # errors in compile time
            if name in ("template", "top-level template code", "<module>") or name.startswith("block "):
                f_back = frame.f_back
                if f_back is not None:
                    module_name = f_back.f_globals.get("__name__", "")

                if module_name.startswith("jinja2."):
                    # Jinja2 translates exception info and creates fake frame on his own
                    pydb.set_suspend(thread, CMD_ADD_EXCEPTION_BREAK)
                    add_exception_to_frame(frame, (exception, value, trace))
                    thread.additional_info.suspend_type = JINJA2_SUSPEND
                    thread.additional_info.pydev_message = str(exception_type)
                    return True, frame
    return None

# === NexusCore/openenv\Lib\site-packages\google\auth\identity_pool.py ===
# Copyright 2020 Google LLC
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

"""Identity Pool Credentials.

This module provides credentials to access Google Cloud resources from on-prem
or non-Google Cloud platforms which support external credentials (e.g. OIDC ID
tokens) retrieved from local file locations or local servers. This includes
Microsoft Azure and OIDC identity providers (e.g. K8s workloads registered with
Hub with Hub workload identity enabled).

These credentials are recommended over the use of service account credentials
in on-prem/non-Google Cloud platforms as they do not involve the management of
long-live service account private keys.

Identity Pool Credentials are initialized using external_account
arguments which are typically loaded from an external credentials file or
an external credentials URL.

This module also provides a definition for an abstract subject token supplier.
This supplier can be implemented to return a valid OIDC or SAML2.0 subject token
and used to create Identity Pool credentials. The credentials will then call the
supplier instead of using pre-defined methods such as reading a local file or
calling a URL.
"""

try:
    from collections.abc import Mapping
# Python 2.7 compatibility
except ImportError:  # pragma: NO COVER
    from collections import Mapping  # type: ignore
import abc
import base64
import json
import os
from typing import NamedTuple

from google.auth import _helpers
from google.auth import exceptions
from google.auth import external_account
from google.auth.transport import _mtls_helper


class SubjectTokenSupplier(metaclass=abc.ABCMeta):
    """Base class for subject token suppliers. This can be implemented with custom logic to retrieve
    a subject token to exchange for a Google Cloud access token when using Workload or
    Workforce Identity Federation. The identity pool credential does not cache the subject token,
    so caching logic should be added in the implementation.
    """

    @abc.abstractmethod
    def get_subject_token(self, context, request):
        """Returns the requested subject token. The subject token must be valid.

        .. warning: This is not cached by the calling Google credential, so caching logic should be implemented in the supplier.

        Args:
            context (google.auth.externalaccount.SupplierContext): The context object
                containing information about the requested audience and subject token type.
            request (google.auth.transport.Request): The object used to make
                HTTP requests.

        Raises:
            google.auth.exceptions.RefreshError: If an error is encountered during
                subject token retrieval logic.

        Returns:
            str: The requested subject token string.
        """
        raise NotImplementedError("")


class _TokenContent(NamedTuple):
    """Models the token content response from file and url internal suppliers.
        Attributes:
            content (str): The string content of the file or URL response.
            location (str): The location the content was retrieved from. This will either be a file location or a URL.
    """

    content: str
    location: str


class _FileSupplier(SubjectTokenSupplier):
    """ Internal implementation of subject token supplier which supports reading a subject token from a file."""

    def __init__(self, path, format_type, subject_token_field_name):
        self._path = path
        self._format_type = format_type
        self._subject_token_field_name = subject_token_field_name

    @_helpers.copy_docstring(SubjectTokenSupplier)
    def get_subject_token(self, context, request):
        if not os.path.exists(self._path):
            raise exceptions.RefreshError("File '{}' was not found.".format(self._path))

        with open(self._path, "r", encoding="utf-8") as file_obj:
            token_content = _TokenContent(file_obj.read(), self._path)

        return _parse_token_data(
            token_content, self._format_type, self._subject_token_field_name
        )


class _UrlSupplier(SubjectTokenSupplier):
    """ Internal implementation of subject token supplier which supports retrieving a subject token by calling a URL endpoint."""

    def __init__(self, url, format_type, subject_token_field_name, headers):
        self._url = url
        self._format_type = format_type
        self._subject_token_field_name = subject_token_field_name
        self._headers = headers

    @_helpers.copy_docstring(SubjectTokenSupplier)
    def get_subject_token(self, context, request):
        response = request(url=self._url, method="GET", headers=self._headers)

        # support both string and bytes type response.data
        response_body = (
            response.data.decode("utf-8")
            if hasattr(response.data, "decode")
            else response.data
        )

        if response.status != 200:
            raise exceptions.RefreshError(
                "Unable to retrieve Identity Pool subject token", response_body
            )
        token_content = _TokenContent(response_body, self._url)
        return _parse_token_data(
            token_content, self._format_type, self._subject_token_field_name
        )


class _X509Supplier(SubjectTokenSupplier):
    """Internal supplier for X509 workload credentials. This class is used internally and always returns an empty string as the subject token."""

    def __init__(self, trust_chain_path, leaf_cert_callback):
        self._trust_chain_path = trust_chain_path
        self._leaf_cert_callback = leaf_cert_callback

    @_helpers.copy_docstring(SubjectTokenSupplier)
    def get_subject_token(self, context, request):
        # Import OpennSSL inline because it is an extra import only required by customers
        # using mTLS.
        from OpenSSL import crypto

        leaf_cert = crypto.load_certificate(
            crypto.FILETYPE_PEM, self._leaf_cert_callback()
        )
        trust_chain = self._read_trust_chain()
        cert_chain = []

        cert_chain.append(_X509Supplier._encode_cert(leaf_cert))

        if trust_chain is None or len(trust_chain) == 0:
            return json.dumps(cert_chain)

        # Append the first cert if it is not the leaf cert.
        first_cert = _X509Supplier._encode_cert(trust_chain[0])
        if first_cert != cert_chain[0]:
            cert_chain.append(first_cert)

        for i in range(1, len(trust_chain)):
            encoded = _X509Supplier._encode_cert(trust_chain[i])
            # Check if the current cert is the leaf cert and raise an exception if it is.
            if encoded == cert_chain[0]:
                raise exceptions.RefreshError(
                    "The leaf certificate must be at the top of the trust chain file"
                )
            else:
                cert_chain.append(encoded)
        return json.dumps(cert_chain)

    def _read_trust_chain(self):
        # Import OpennSSL inline because it is an extra import only required by customers
        # using mTLS.
        from OpenSSL import crypto

        certificate_trust_chain = []
        # If no trust chain path was provided, return an empty list.
        if self._trust_chain_path is None or self._trust_chain_path == "":
            return certificate_trust_chain
        try:
            # Open the trust chain file.
            with open(self._trust_chain_path, "rb") as f:
                trust_chain_data = f.read()
                # Split PEM data into individual certificates.
                cert_blocks = trust_chain_data.split(b"-----BEGIN CERTIFICATE-----")
                for cert_block in cert_blocks:
                    # Skip empty blocks.
                    if cert_block.strip():
                        cert_data = b"-----BEGIN CERTIFICATE-----" + cert_block
                        try:
                            # Load each certificate and add it to the trust chain.
                            cert = crypto.load_certificate(
                                crypto.FILETYPE_PEM, cert_data
                            )
                            certificate_trust_chain.append(cert)
                        except Exception as e:
                            raise exceptions.RefreshError(
                                "Error loading PEM certificates from the trust chain file '{}'".format(
                                    self._trust_chain_path
                                )
                            ) from e
                return certificate_trust_chain
        except FileNotFoundError:
            raise exceptions.RefreshError(
                "Trust chain file '{}' was not found.".format(self._trust_chain_path)
            )

    def _encode_cert(cert):
        # Import OpennSSL inline because it is an extra import only required by customers
        # using mTLS.
        from OpenSSL import crypto

        return base64.b64encode(
            crypto.dump_certificate(crypto.FILETYPE_ASN1, cert)
        ).decode("utf-8")


def _parse_token_data(token_content, format_type="text", subject_token_field_name=None):
    if format_type == "text":
        token = token_content.content
    else:
        try:
            # Parse file content as JSON.
            response_data = json.loads(token_content.content)
            # Get the subject_token.
            token = response_data[subject_token_field_name]
        except (KeyError, ValueError):
            raise exceptions.RefreshError(
                "Unable to parse subject_token from JSON file '{}' using key '{}'".format(
                    token_content.location, subject_token_field_name
                )
            )
    if not token:
        raise exceptions.RefreshError(
            "Missing subject_token in the credential_source file"
        )
    return token


class Credentials(external_account.Credentials):
    """External account credentials sourced from files and URLs."""

    def __init__(
        self,
        audience,
        subject_token_type,
        token_url=external_account._DEFAULT_TOKEN_URL,
        credential_source=None,
        subject_token_supplier=None,
        *args,
        **kwargs
    ):
        """Instantiates an external account credentials object from a file/URL.

        Args:
            audience (str): The STS audience field.
            subject_token_type (str): The subject token type based on the Oauth2.0 token exchange spec.
                Expected values include::

                    “urn:ietf:params:oauth:token-type:jwt”
                    “urn:ietf:params:oauth:token-type:id-token”
                    “urn:ietf:params:oauth:token-type:saml2”

            token_url (Optional [str]): The STS endpoint URL. If not provided, will default to "https://sts.googleapis.com/v1/token".
            credential_source (Optional [Mapping]): The credential source dictionary used to
                provide instructions on how to retrieve external credential to be
                exchanged for Google access tokens. Either a credential source or
                a subject token supplier must be provided.

                Example credential_source for url-sourced credential::

                    {
                        "url": "http://www.example.com",
                        "format": {
                            "type": "json",
                            "subject_token_field_name": "access_token",
                        },
                        "headers": {"foo": "bar"},
                    }

                Example credential_source for file-sourced credential::

                    {
                        "file": "/path/to/token/file.txt"
                    }
            subject_token_supplier (Optional [SubjectTokenSupplier]): Optional subject token supplier.
                This will be called to supply a valid subject token which will then
                be exchanged for Google access tokens. Either a subject token  supplier
                or a credential source must be provided.
            args (List): Optional positional arguments passed into the underlying :meth:`~external_account.Credentials.__init__` method.
            kwargs (Mapping): Optional keyword arguments passed into the underlying :meth:`~external_account.Credentials.__init__` method.

        Raises:
            google.auth.exceptions.RefreshError: If an error is encountered during
                access token retrieval logic.
            ValueError: For invalid parameters.

        .. note:: Typically one of the helper constructors
            :meth:`from_file` or
            :meth:`from_info` are used instead of calling the constructor directly.
        """

        super(Credentials, self).__init__(
            audience=audience,
            subject_token_type=subject_token_type,
            token_url=token_url,
            credential_source=credential_source,
            *args,
            **kwargs
        )
        if credential_source is None and subject_token_supplier is None:
            raise exceptions.InvalidValue(
                "A valid credential source or a subject token supplier must be provided."
            )
        if credential_source is not None and subject_token_supplier is not None:
            raise exceptions.InvalidValue(
                "Identity pool credential cannot have both a credential source and a subject token supplier."
            )

        if subject_token_supplier is not None:
            self._subject_token_supplier = subject_token_supplier
            self._credential_source_file = None
            self._credential_source_url = None
            self._credential_source_certificate = None
        else:
            if not isinstance(credential_source, Mapping):
                self._credential_source_executable = None
                raise exceptions.MalformedError(
                    "Invalid credential_source. The credential_source is not a dict."
                )
            self._credential_source_file = credential_source.get("file")
            self._credential_source_url = credential_source.get("url")
            self._credential_source_certificate = credential_source.get("certificate")

            # environment_id is only supported in AWS or dedicated future external
            # account credentials.
            if "environment_id" in credential_source:
                raise exceptions.MalformedError(
                    "Invalid Identity Pool credential_source field 'environment_id'"
                )

            # check that only one of file, url, or certificate are provided.
            self._validate_single_source()

            if self._credential_source_certificate:
                self._validate_certificate_config()
            else:
                self._validate_file_or_url_config(credential_source)

            if self._credential_source_file:
                self._subject_token_supplier = _FileSupplier(
                    self._credential_source_file,
                    self._credential_source_format_type,
                    self._credential_source_field_name,
                )
            elif self._credential_source_url:
                self._subject_token_supplier = _UrlSupplier(
                    self._credential_source_url,
                    self._credential_source_format_type,
                    self._credential_source_field_name,
                    self._credential_source_headers,
                )
            else:  # self._credential_source_certificate
                self._subject_token_supplier = _X509Supplier(
                    self._trust_chain_path, self._get_cert_bytes
                )

    @_helpers.copy_docstring(external_account.Credentials)
    def retrieve_subject_token(self, request):
        return self._subject_token_supplier.get_subject_token(
            self._supplier_context, request
        )

    def _get_mtls_cert_and_key_paths(self):
        if self._credential_source_certificate is None:
            raise exceptions.RefreshError(
                'The credential is not configured to use mtls requests. The credential should include a "certificate" section in the credential source.'
            )
        else:
            return _mtls_helper._get_workload_cert_and_key_paths(
                self._certificate_config_location
            )

    def _get_cert_bytes(self):
        cert_path, _ = self._get_mtls_cert_and_key_paths()
        return _mtls_helper._read_cert_file(cert_path)

    def _mtls_required(self):
        return self._credential_source_certificate is not None

    def _create_default_metrics_options(self):
        metrics_options = super(Credentials, self)._create_default_metrics_options()
        # Check that credential source is a dict before checking for credential type. This check needs to be done
        # here because the external_account credential constructor needs to pass the metrics options to the
        # impersonated credential object before the identity_pool credentials are validated.
        if isinstance(self._credential_source, Mapping):
            if self._credential_source.get("file"):
                metrics_options["source"] = "file"
            elif self._credential_source.get("url"):
                metrics_options["source"] = "url"
            else:
                metrics_options["source"] = "x509"
        else:
            metrics_options["source"] = "programmatic"
        return metrics_options

    def _has_custom_supplier(self):
        return self._credential_source is None

    def _constructor_args(self):
        args = super(Credentials, self)._constructor_args()
        # If a custom supplier was used, append it to the args dict.
        if self._has_custom_supplier():
            args.update({"subject_token_supplier": self._subject_token_supplier})
        return args

    def _validate_certificate_config(self):
        self._certificate_config_location = self._credential_source_certificate.get(
            "certificate_config_location"
        )
        use_default = self._credential_source_certificate.get(
            "use_default_certificate_config"
        )
        self._trust_chain_path = self._credential_source_certificate.get(
            "trust_chain_path"
        )
        if self._certificate_config_location and use_default:
            raise exceptions.MalformedError(
                "Invalid certificate configuration, certificate_config_location cannot be specified when use_default_certificate_config = true."
            )
        if not self._certificate_config_location and not use_default:
            raise exceptions.MalformedError(
                "Invalid certificate configuration, use_default_certificate_config should be true if no certificate_config_location is provided."
            )

    def _validate_file_or_url_config(self, credential_source):
        self._credential_source_headers = credential_source.get("headers")
        credential_source_format = credential_source.get("format", {})
        # Get credential_source format type. When not provided, this
        # defaults to text.
        self._credential_source_format_type = (
            credential_source_format.get("type") or "text"
        )
        if self._credential_source_format_type not in ["text", "json"]:
            raise exceptions.MalformedError(
                "Invalid credential_source format '{}'".format(
                    self._credential_source_format_type
                )
            )
        # For JSON types, get the required subject_token field name.
        if self._credential_source_format_type == "json":
            self._credential_source_field_name = credential_source_format.get(
                "subject_token_field_name"
            )
            if self._credential_source_field_name is None:
                raise exceptions.MalformedError(
                    "Missing subject_token_field_name for JSON credential_source format"
                )
        else:
            self._credential_source_field_name = None

    def _validate_single_source(self):
        credential_sources = [
            self._credential_source_file,
            self._credential_source_url,
            self._credential_source_certificate,
        ]
        valid_credential_sources = list(
            filter(lambda source: source is not None, credential_sources)
        )

        if len(valid_credential_sources) > 1:
            raise exceptions.MalformedError(
                "Ambiguous credential_source. 'file', 'url', and 'certificate' are mutually exclusive.."
            )
        if len(valid_credential_sources) != 1:
            raise exceptions.MalformedError(
                "Missing credential_source. A 'file', 'url', or 'certificate' must be provided."
            )

    @classmethod
    def from_info(cls, info, **kwargs):
        """Creates an Identity Pool Credentials instance from parsed external account info.

        Args:
            info (Mapping[str, str]): The Identity Pool external account info in Google
                format.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.identity_pool.Credentials: The constructed
                credentials.

        Raises:
            ValueError: For invalid parameters.
        """
        subject_token_supplier = info.get("subject_token_supplier")
        kwargs.update({"subject_token_supplier": subject_token_supplier})
        return super(Credentials, cls).from_info(info, **kwargs)

    @classmethod
    def from_file(cls, filename, **kwargs):
        """Creates an IdentityPool Credentials instance from an external account json file.

        Args:
            filename (str): The path to the IdentityPool external account json file.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.identity_pool.Credentials: The constructed
                credentials.
        """
        return super(Credentials, cls).from_file(filename, **kwargs)

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\backend_agg.py ===
"""
An `Anti-Grain Geometry`_ (AGG) backend.

Features that are implemented:

* capstyles and join styles
* dashes
* linewidth
* lines, rectangles, ellipses
* clipping to a rectangle
* output to RGBA and Pillow-supported image formats
* alpha blending
* DPI scaling properly - everything scales properly (dashes, linewidths, etc)
* draw polygon
* freetype2 w/ ft2font

Still TODO:

* integrate screen dpi w/ ppi and text

.. _Anti-Grain Geometry: http://agg.sourceforge.net/antigrain.com
"""

from contextlib import nullcontext
from math import radians, cos, sin

import numpy as np

import matplotlib as mpl
from matplotlib import _api, cbook
from matplotlib.backend_bases import (
    _Backend, FigureCanvasBase, FigureManagerBase, RendererBase)
from matplotlib.font_manager import fontManager as _fontManager, get_font
from matplotlib.ft2font import LoadFlags
from matplotlib.mathtext import MathTextParser
from matplotlib.path import Path
from matplotlib.transforms import Bbox, BboxBase
from matplotlib.backends._backend_agg import RendererAgg as _RendererAgg


def get_hinting_flag():
    mapping = {
        'default': LoadFlags.DEFAULT,
        'no_autohint': LoadFlags.NO_AUTOHINT,
        'force_autohint': LoadFlags.FORCE_AUTOHINT,
        'no_hinting': LoadFlags.NO_HINTING,
        True: LoadFlags.FORCE_AUTOHINT,
        False: LoadFlags.NO_HINTING,
        'either': LoadFlags.DEFAULT,
        'native': LoadFlags.NO_AUTOHINT,
        'auto': LoadFlags.FORCE_AUTOHINT,
        'none': LoadFlags.NO_HINTING,
    }
    return mapping[mpl.rcParams['text.hinting']]


class RendererAgg(RendererBase):
    """
    The renderer handles all the drawing primitives using a graphics
    context instance that controls the colors/styles
    """

    def __init__(self, width, height, dpi):
        super().__init__()

        self.dpi = dpi
        self.width = width
        self.height = height
        self._renderer = _RendererAgg(int(width), int(height), dpi)
        self._filter_renderers = []

        self._update_methods()
        self.mathtext_parser = MathTextParser('agg')

        self.bbox = Bbox.from_bounds(0, 0, self.width, self.height)

    def __getstate__(self):
        # We only want to preserve the init keywords of the Renderer.
        # Anything else can be re-created.
        return {'width': self.width, 'height': self.height, 'dpi': self.dpi}

    def __setstate__(self, state):
        self.__init__(state['width'], state['height'], state['dpi'])

    def _update_methods(self):
        self.draw_gouraud_triangles = self._renderer.draw_gouraud_triangles
        self.draw_image = self._renderer.draw_image
        self.draw_markers = self._renderer.draw_markers
        self.draw_path_collection = self._renderer.draw_path_collection
        self.draw_quad_mesh = self._renderer.draw_quad_mesh
        self.copy_from_bbox = self._renderer.copy_from_bbox

    def draw_path(self, gc, path, transform, rgbFace=None):
        # docstring inherited
        nmax = mpl.rcParams['agg.path.chunksize']  # here at least for testing
        npts = path.vertices.shape[0]

        if (npts > nmax > 100 and path.should_simplify and
                rgbFace is None and gc.get_hatch() is None):
            nch = np.ceil(npts / nmax)
            chsize = int(np.ceil(npts / nch))
            i0 = np.arange(0, npts, chsize)
            i1 = np.zeros_like(i0)
            i1[:-1] = i0[1:] - 1
            i1[-1] = npts
            for ii0, ii1 in zip(i0, i1):
                v = path.vertices[ii0:ii1, :]
                c = path.codes
                if c is not None:
                    c = c[ii0:ii1]
                    c[0] = Path.MOVETO  # move to end of last chunk
                p = Path(v, c)
                p.simplify_threshold = path.simplify_threshold
                try:
                    self._renderer.draw_path(gc, p, transform, rgbFace)
                except OverflowError:
                    msg = (
                        "Exceeded cell block limit in Agg.\n\n"
                        "Please reduce the value of "
                        f"rcParams['agg.path.chunksize'] (currently {nmax}) "
                        "or increase the path simplification threshold"
                        "(rcParams['path.simplify_threshold'] = "
                        f"{mpl.rcParams['path.simplify_threshold']:.2f} by "
                        "default and path.simplify_threshold = "
                        f"{path.simplify_threshold:.2f} on the input)."
                    )
                    raise OverflowError(msg) from None
        else:
            try:
                self._renderer.draw_path(gc, path, transform, rgbFace)
            except OverflowError:
                cant_chunk = ''
                if rgbFace is not None:
                    cant_chunk += "- cannot split filled path\n"
                if gc.get_hatch() is not None:
                    cant_chunk += "- cannot split hatched path\n"
                if not path.should_simplify:
                    cant_chunk += "- path.should_simplify is False\n"
                if len(cant_chunk):
                    msg = (
                        "Exceeded cell block limit in Agg, however for the "
                        "following reasons:\n\n"
                        f"{cant_chunk}\n"
                        "we cannot automatically split up this path to draw."
                        "\n\nPlease manually simplify your path."
                    )

                else:
                    inc_threshold = (
                        "or increase the path simplification threshold"
                        "(rcParams['path.simplify_threshold'] = "
                        f"{mpl.rcParams['path.simplify_threshold']} "
                        "by default and path.simplify_threshold "
                        f"= {path.simplify_threshold} "
                        "on the input)."
                        )
                    if nmax > 100:
                        msg = (
                            "Exceeded cell block limit in Agg.  Please reduce "
                            "the value of rcParams['agg.path.chunksize'] "
                            f"(currently {nmax}) {inc_threshold}"
                        )
                    else:
                        msg = (
                            "Exceeded cell block limit in Agg.  Please set "
                            "the value of rcParams['agg.path.chunksize'], "
                            f"(currently {nmax}) to be greater than 100 "
                            + inc_threshold
                        )

                raise OverflowError(msg) from None

    def draw_mathtext(self, gc, x, y, s, prop, angle):
        """Draw mathtext using :mod:`matplotlib.mathtext`."""
        ox, oy, width, height, descent, font_image = \
            self.mathtext_parser.parse(s, self.dpi, prop,
                                       antialiased=gc.get_antialiased())

        xd = descent * sin(radians(angle))
        yd = descent * cos(radians(angle))
        x = round(x + ox + xd)
        y = round(y - oy + yd)
        self._renderer.draw_text_image(font_image, x, y + 1, angle, gc)

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False, mtext=None):
        # docstring inherited
        if ismath:
            return self.draw_mathtext(gc, x, y, s, prop, angle)
        font = self._prepare_font(prop)
        # We pass '0' for angle here, since it will be rotated (in raster
        # space) in the following call to draw_text_image).
        font.set_text(s, 0, flags=get_hinting_flag())
        font.draw_glyphs_to_bitmap(
            antialiased=gc.get_antialiased())
        d = font.get_descent() / 64.0
        # The descent needs to be adjusted for the angle.
        xo, yo = font.get_bitmap_offset()
        xo /= 64.0
        yo /= 64.0
        xd = d * sin(radians(angle))
        yd = d * cos(radians(angle))
        x = round(x + xo + xd)
        y = round(y + yo + yd)
        self._renderer.draw_text_image(font, x, y + 1, angle, gc)

    def get_text_width_height_descent(self, s, prop, ismath):
        # docstring inherited

        _api.check_in_list(["TeX", True, False], ismath=ismath)
        if ismath == "TeX":
            return super().get_text_width_height_descent(s, prop, ismath)

        if ismath:
            ox, oy, width, height, descent, font_image = \
                self.mathtext_parser.parse(s, self.dpi, prop)
            return width, height, descent

        font = self._prepare_font(prop)
        font.set_text(s, 0.0, flags=get_hinting_flag())
        w, h = font.get_width_height()  # width and height of unrotated string
        d = font.get_descent()
        w /= 64.0  # convert from subpixels
        h /= 64.0
        d /= 64.0
        return w, h, d

    def draw_tex(self, gc, x, y, s, prop, angle, *, mtext=None):
        # docstring inherited
        # todo, handle props, angle, origins
        size = prop.get_size_in_points()

        texmanager = self.get_texmanager()

        Z = texmanager.get_grey(s, size, self.dpi)
        Z = np.array(Z * 255.0, np.uint8)

        w, h, d = self.get_text_width_height_descent(s, prop, ismath="TeX")
        xd = d * sin(radians(angle))
        yd = d * cos(radians(angle))
        x = round(x + xd)
        y = round(y + yd)
        self._renderer.draw_text_image(Z, x, y, angle, gc)

    def get_canvas_width_height(self):
        # docstring inherited
        return self.width, self.height

    def _prepare_font(self, font_prop):
        """
        Get the `.FT2Font` for *font_prop*, clear its buffer, and set its size.
        """
        font = get_font(_fontManager._find_fonts_by_props(font_prop))
        font.clear()
        size = font_prop.get_size_in_points()
        font.set_size(size, self.dpi)
        return font

    def points_to_pixels(self, points):
        # docstring inherited
        return points * self.dpi / 72

    def buffer_rgba(self):
        return memoryview(self._renderer)

    def tostring_argb(self):
        return np.asarray(self._renderer).take([3, 0, 1, 2], axis=2).tobytes()

    def clear(self):
        self._renderer.clear()

    def option_image_nocomposite(self):
        # docstring inherited

        # It is generally faster to composite each image directly to
        # the Figure, and there's no file size benefit to compositing
        # with the Agg backend
        return True

    def option_scale_image(self):
        # docstring inherited
        return False

    def restore_region(self, region, bbox=None, xy=None):
        """
        Restore the saved region. If bbox (instance of BboxBase, or
        its extents) is given, only the region specified by the bbox
        will be restored. *xy* (a pair of floats) optionally
        specifies the new position (the LLC of the original region,
        not the LLC of the bbox) where the region will be restored.

        >>> region = renderer.copy_from_bbox()
        >>> x1, y1, x2, y2 = region.get_extents()
        >>> renderer.restore_region(region, bbox=(x1+dx, y1, x2, y2),
        ...                         xy=(x1-dx, y1))

        """
        if bbox is not None or xy is not None:
            if bbox is None:
                x1, y1, x2, y2 = region.get_extents()
            elif isinstance(bbox, BboxBase):
                x1, y1, x2, y2 = bbox.extents
            else:
                x1, y1, x2, y2 = bbox

            if xy is None:
                ox, oy = x1, y1
            else:
                ox, oy = xy

            # The incoming data is float, but the _renderer type-checking wants
            # to see integers.
            self._renderer.restore_region(region, int(x1), int(y1),
                                          int(x2), int(y2), int(ox), int(oy))

        else:
            self._renderer.restore_region(region)

    def start_filter(self):
        """
        Start filtering. It simply creates a new canvas (the old one is saved).
        """
        self._filter_renderers.append(self._renderer)
        self._renderer = _RendererAgg(int(self.width), int(self.height),
                                      self.dpi)
        self._update_methods()

    def stop_filter(self, post_processing):
        """
        Save the current canvas as an image and apply post processing.

        The *post_processing* function::

           def post_processing(image, dpi):
             # ny, nx, depth = image.shape
             # image (numpy array) has RGBA channels and has a depth of 4.
             ...
             # create a new_image (numpy array of 4 channels, size can be
             # different). The resulting image may have offsets from
             # lower-left corner of the original image
             return new_image, offset_x, offset_y

        The saved renderer is restored and the returned image from
        post_processing is plotted (using draw_image) on it.
        """
        orig_img = np.asarray(self.buffer_rgba())
        slice_y, slice_x = cbook._get_nonzero_slices(orig_img[..., 3])
        cropped_img = orig_img[slice_y, slice_x]

        self._renderer = self._filter_renderers.pop()
        self._update_methods()

        if cropped_img.size:
            img, ox, oy = post_processing(cropped_img / 255, self.dpi)
            gc = self.new_gc()
            if img.dtype.kind == 'f':
                img = np.asarray(img * 255., np.uint8)
            self._renderer.draw_image(
                gc, slice_x.start + ox, int(self.height) - slice_y.stop + oy,
                img[::-1])


class FigureCanvasAgg(FigureCanvasBase):
    # docstring inherited

    _lastKey = None  # Overwritten per-instance on the first draw.

    def copy_from_bbox(self, bbox):
        renderer = self.get_renderer()
        return renderer.copy_from_bbox(bbox)

    def restore_region(self, region, bbox=None, xy=None):
        renderer = self.get_renderer()
        return renderer.restore_region(region, bbox, xy)

    def draw(self):
        # docstring inherited
        self.renderer = self.get_renderer()
        self.renderer.clear()
        # Acquire a lock on the shared font cache.
        with (self.toolbar._wait_cursor_for_draw_cm() if self.toolbar
              else nullcontext()):
            self.figure.draw(self.renderer)
            # A GUI class may be need to update a window using this draw, so
            # don't forget to call the superclass.
            super().draw()

    def get_renderer(self):
        w, h = self.figure.bbox.size
        key = w, h, self.figure.dpi
        reuse_renderer = (self._lastKey == key)
        if not reuse_renderer:
            self.renderer = RendererAgg(w, h, self.figure.dpi)
            self._lastKey = key
        return self.renderer

    def tostring_argb(self):
        """
        Get the image as ARGB `bytes`.

        `draw` must be called at least once before this function will work and
        to update the renderer for any subsequent changes to the Figure.
        """
        return self.renderer.tostring_argb()

    def buffer_rgba(self):
        """
        Get the image as a `memoryview` to the renderer's buffer.

        `draw` must be called at least once before this function will work and
        to update the renderer for any subsequent changes to the Figure.
        """
        return self.renderer.buffer_rgba()

    def print_raw(self, filename_or_obj, *, metadata=None):
        if metadata is not None:
            raise ValueError("metadata not supported for raw/rgba")
        FigureCanvasAgg.draw(self)
        renderer = self.get_renderer()
        with cbook.open_file_cm(filename_or_obj, "wb") as fh:
            fh.write(renderer.buffer_rgba())

    print_rgba = print_raw

    def _print_pil(self, filename_or_obj, fmt, pil_kwargs, metadata=None):
        """
        Draw the canvas, then save it using `.image.imsave` (to which
        *pil_kwargs* and *metadata* are forwarded).
        """
        FigureCanvasAgg.draw(self)
        mpl.image.imsave(
            filename_or_obj, self.buffer_rgba(), format=fmt, origin="upper",
            dpi=self.figure.dpi, metadata=metadata, pil_kwargs=pil_kwargs)

    def print_png(self, filename_or_obj, *, metadata=None, pil_kwargs=None):
        """
        Write the figure to a PNG file.

        Parameters
        ----------
        filename_or_obj : str or path-like or file-like
            The file to write to.

        metadata : dict, optional
            Metadata in the PNG file as key-value pairs of bytes or latin-1
            encodable strings.
            According to the PNG specification, keys must be shorter than 79
            chars.

            The `PNG specification`_ defines some common keywords that may be
            used as appropriate:

            - Title: Short (one line) title or caption for image.
            - Author: Name of image's creator.
            - Description: Description of image (possibly long).
            - Copyright: Copyright notice.
            - Creation Time: Time of original image creation
              (usually RFC 1123 format).
            - Software: Software used to create the image.
            - Disclaimer: Legal disclaimer.
            - Warning: Warning of nature of content.
            - Source: Device used to create the image.
            - Comment: Miscellaneous comment;
              conversion from other image format.

            Other keywords may be invented for other purposes.

            If 'Software' is not given, an autogenerated value for Matplotlib
            will be used.  This can be removed by setting it to *None*.

            For more details see the `PNG specification`_.

            .. _PNG specification: \
                https://www.w3.org/TR/2003/REC-PNG-20031110/#11keywords

        pil_kwargs : dict, optional
            Keyword arguments passed to `PIL.Image.Image.save`.

            If the 'pnginfo' key is present, it completely overrides
            *metadata*, including the default 'Software' key.
        """
        self._print_pil(filename_or_obj, "png", pil_kwargs, metadata)

    def print_to_buffer(self):
        FigureCanvasAgg.draw(self)
        renderer = self.get_renderer()
        return (bytes(renderer.buffer_rgba()),
                (int(renderer.width), int(renderer.height)))

    # Note that these methods should typically be called via savefig() and
    # print_figure(), and the latter ensures that `self.figure.dpi` already
    # matches the dpi kwarg (if any).

    def print_jpg(self, filename_or_obj, *, metadata=None, pil_kwargs=None):
        # savefig() has already applied savefig.facecolor; we now set it to
        # white to make imsave() blend semi-transparent figures against an
        # assumed white background.
        with mpl.rc_context({"savefig.facecolor": "white"}):
            self._print_pil(filename_or_obj, "jpeg", pil_kwargs, metadata)

    print_jpeg = print_jpg

    def print_tif(self, filename_or_obj, *, metadata=None, pil_kwargs=None):
        self._print_pil(filename_or_obj, "tiff", pil_kwargs, metadata)

    print_tiff = print_tif

    def print_webp(self, filename_or_obj, *, metadata=None, pil_kwargs=None):
        self._print_pil(filename_or_obj, "webp", pil_kwargs, metadata)

    print_jpg.__doc__, print_tif.__doc__, print_webp.__doc__ = map(
        """
        Write the figure to a {} file.

        Parameters
        ----------
        filename_or_obj : str or path-like or file-like
            The file to write to.
        pil_kwargs : dict, optional
            Additional keyword arguments that are passed to
            `PIL.Image.Image.save` when saving the figure.
        """.format, ["JPEG", "TIFF", "WebP"])


@_Backend.export
class _BackendAgg(_Backend):
    backend_version = 'v2.2'
    FigureCanvas = FigureCanvasAgg
    FigureManager = FigureManagerBase

# === NexusCore/openenv\Lib\site-packages\tornado\test\template_test.py ===
import os
import traceback
import unittest

from tornado.escape import utf8, native_str, to_unicode
from tornado.template import Template, DictLoader, ParseError, Loader
from tornado.util import ObjectDict

import typing  # noqa: F401


class TemplateTest(unittest.TestCase):
    def test_simple(self):
        template = Template("Hello {{ name }}!")
        self.assertEqual(template.generate(name="Ben"), b"Hello Ben!")

    def test_bytes(self):
        template = Template("Hello {{ name }}!")
        self.assertEqual(template.generate(name=utf8("Ben")), b"Hello Ben!")

    def test_expressions(self):
        template = Template("2 + 2 = {{ 2 + 2 }}")
        self.assertEqual(template.generate(), b"2 + 2 = 4")

    def test_comment(self):
        template = Template("Hello{# TODO i18n #} {{ name }}!")
        self.assertEqual(template.generate(name=utf8("Ben")), b"Hello Ben!")

    def test_include(self):
        loader = DictLoader(
            {
                "index.html": '{% include "header.html" %}\nbody text',
                "header.html": "header text",
            }
        )
        self.assertEqual(
            loader.load("index.html").generate(), b"header text\nbody text"
        )

    def test_extends(self):
        loader = DictLoader(
            {
                "base.html": """\
<title>{% block title %}default title{% end %}</title>
<body>{% block body %}default body{% end %}</body>
""",
                "page.html": """\
{% extends "base.html" %}
{% block title %}page title{% end %}
{% block body %}page body{% end %}
""",
            }
        )
        self.assertEqual(
            loader.load("page.html").generate(),
            b"<title>page title</title>\n<body>page body</body>\n",
        )

    def test_relative_load(self):
        loader = DictLoader(
            {
                "a/1.html": "{% include '2.html' %}",
                "a/2.html": "{% include '../b/3.html' %}",
                "b/3.html": "ok",
            }
        )
        self.assertEqual(loader.load("a/1.html").generate(), b"ok")

    def test_escaping(self):
        self.assertRaises(ParseError, lambda: Template("{{"))
        self.assertRaises(ParseError, lambda: Template("{%"))
        self.assertEqual(Template("{{!").generate(), b"{{")
        self.assertEqual(Template("{%!").generate(), b"{%")
        self.assertEqual(Template("{#!").generate(), b"{#")
        self.assertEqual(
            Template("{{ 'expr' }} {{!jquery expr}}").generate(),
            b"expr {{jquery expr}}",
        )

    def test_unicode_template(self):
        template = Template(utf8("\u00e9"))
        self.assertEqual(template.generate(), utf8("\u00e9"))

    def test_unicode_literal_expression(self):
        # Unicode literals should be usable in templates.  Note that this
        # test simulates unicode characters appearing directly in the
        # template file (with utf8 encoding), i.e. \u escapes would not
        # be used in the template file itself.
        template = Template(utf8('{{ "\u00e9" }}'))
        self.assertEqual(template.generate(), utf8("\u00e9"))

    def test_custom_namespace(self):
        loader = DictLoader(
            {"test.html": "{{ inc(5) }}"}, namespace={"inc": lambda x: x + 1}
        )
        self.assertEqual(loader.load("test.html").generate(), b"6")

    def test_apply(self):
        def upper(s):
            return s.upper()

        template = Template(utf8("{% apply upper %}foo{% end %}"))
        self.assertEqual(template.generate(upper=upper), b"FOO")

    def test_unicode_apply(self):
        def upper(s):
            return to_unicode(s).upper()

        template = Template(utf8("{% apply upper %}foo \u00e9{% end %}"))
        self.assertEqual(template.generate(upper=upper), utf8("FOO \u00c9"))

    def test_bytes_apply(self):
        def upper(s):
            return utf8(to_unicode(s).upper())

        template = Template(utf8("{% apply upper %}foo \u00e9{% end %}"))
        self.assertEqual(template.generate(upper=upper), utf8("FOO \u00c9"))

    def test_if(self):
        template = Template(utf8("{% if x > 4 %}yes{% else %}no{% end %}"))
        self.assertEqual(template.generate(x=5), b"yes")
        self.assertEqual(template.generate(x=3), b"no")

    def test_if_empty_body(self):
        template = Template(utf8("{% if True %}{% else %}{% end %}"))
        self.assertEqual(template.generate(), b"")

    def test_try(self):
        template = Template(
            utf8(
                """{% try %}
try{% set y = 1/x %}
{% except %}-except
{% else %}-else
{% finally %}-finally
{% end %}"""
            )
        )
        self.assertEqual(template.generate(x=1), b"\ntry\n-else\n-finally\n")
        self.assertEqual(template.generate(x=0), b"\ntry-except\n-finally\n")

    def test_comment_directive(self):
        template = Template(utf8("{% comment blah blah %}foo"))
        self.assertEqual(template.generate(), b"foo")

    def test_break_continue(self):
        template = Template(
            utf8(
                """\
{% for i in range(10) %}
    {% if i == 2 %}
        {% continue %}
    {% end %}
    {{ i }}
    {% if i == 6 %}
        {% break %}
    {% end %}
{% end %}"""
            )
        )
        result = template.generate()
        # remove extraneous whitespace
        result = b"".join(result.split())
        self.assertEqual(result, b"013456")

    def test_break_outside_loop(self):
        with self.assertRaises(ParseError, msg="Did not get expected exception"):
            Template(utf8("{% break %}"))

    def test_break_in_apply(self):
        # This test verifies current behavior, although of course it would
        # be nice if apply didn't cause seemingly unrelated breakage
        with self.assertRaises(ParseError, msg="Did not get expected exception"):
            Template(
                utf8("{% for i in [] %}{% apply foo %}{% break %}{% end %}{% end %}")
            )

    @unittest.skip("no testable future imports")
    def test_no_inherit_future(self):
        # TODO(bdarnell): make a test like this for one of the future
        # imports available in python 3. Unfortunately they're harder
        # to use in a template than division was.

        # This file has from __future__ import division...
        self.assertEqual(1 / 2, 0.5)
        # ...but the template doesn't
        template = Template("{{ 1 / 2 }}")
        self.assertEqual(template.generate(), "0")

    def test_non_ascii_name(self):
        loader = DictLoader({"t\u00e9st.html": "hello"})
        self.assertEqual(loader.load("t\u00e9st.html").generate(), b"hello")


class StackTraceTest(unittest.TestCase):
    def test_error_line_number_expression(self):
        loader = DictLoader(
            {
                "test.html": """one
two{{1/0}}
three
        """
            }
        )
        try:
            loader.load("test.html").generate()
            self.fail("did not get expected exception")
        except ZeroDivisionError:
            self.assertTrue("# test.html:2" in traceback.format_exc())

    def test_error_line_number_directive(self):
        loader = DictLoader(
            {
                "test.html": """one
two{%if 1/0%}
three{%end%}
        """
            }
        )
        try:
            loader.load("test.html").generate()
            self.fail("did not get expected exception")
        except ZeroDivisionError:
            self.assertTrue("# test.html:2" in traceback.format_exc())

    def test_error_line_number_module(self):
        loader = None  # type: typing.Optional[DictLoader]

        def load_generate(path, **kwargs):
            assert loader is not None
            return loader.load(path).generate(**kwargs)

        loader = DictLoader(
            {"base.html": "{% module Template('sub.html') %}", "sub.html": "{{1/0}}"},
            namespace={"_tt_modules": ObjectDict(Template=load_generate)},
        )
        try:
            loader.load("base.html").generate()
            self.fail("did not get expected exception")
        except ZeroDivisionError:
            exc_stack = traceback.format_exc()
            self.assertTrue("# base.html:1" in exc_stack)
            self.assertTrue("# sub.html:1" in exc_stack)

    def test_error_line_number_include(self):
        loader = DictLoader(
            {"base.html": "{% include 'sub.html' %}", "sub.html": "{{1/0}}"}
        )
        try:
            loader.load("base.html").generate()
            self.fail("did not get expected exception")
        except ZeroDivisionError:
            self.assertTrue("# sub.html:1 (via base.html:1)" in traceback.format_exc())

    def test_error_line_number_extends_base_error(self):
        loader = DictLoader(
            {"base.html": "{{1/0}}", "sub.html": "{% extends 'base.html' %}"}
        )
        try:
            loader.load("sub.html").generate()
            self.fail("did not get expected exception")
        except ZeroDivisionError:
            exc_stack = traceback.format_exc()
        self.assertIn("# base.html:1", exc_stack)

    def test_error_line_number_extends_sub_error(self):
        loader = DictLoader(
            {
                "base.html": "{% block 'block' %}{% end %}",
                "sub.html": """
{% extends 'base.html' %}
{% block 'block' %}
{{1/0}}
{% end %}
            """,
            }
        )
        try:
            loader.load("sub.html").generate()
            self.fail("did not get expected exception")
        except ZeroDivisionError:
            self.assertIn("# sub.html:4 (via base.html:1)", traceback.format_exc())

    def test_multi_includes(self):
        loader = DictLoader(
            {
                "a.html": "{% include 'b.html' %}",
                "b.html": "{% include 'c.html' %}",
                "c.html": "{{1/0}}",
            }
        )
        try:
            loader.load("a.html").generate()
            self.fail("did not get expected exception")
        except ZeroDivisionError:
            self.assertIn("# c.html:1 (via b.html:1, a.html:1)", traceback.format_exc())


class ParseErrorDetailTest(unittest.TestCase):
    def test_details(self):
        loader = DictLoader({"foo.html": "\n\n{{"})
        with self.assertRaises(ParseError) as cm:
            loader.load("foo.html")
        self.assertEqual("Missing end expression }} at foo.html:3", str(cm.exception))
        self.assertEqual("foo.html", cm.exception.filename)
        self.assertEqual(3, cm.exception.lineno)

    def test_custom_parse_error(self):
        # Make sure that ParseErrors remain compatible with their
        # pre-4.3 signature.
        self.assertEqual("asdf at None:0", str(ParseError("asdf")))


class AutoEscapeTest(unittest.TestCase):
    def setUp(self):
        self.templates = {
            "escaped.html": "{% autoescape xhtml_escape %}{{ name }}",
            "unescaped.html": "{% autoescape None %}{{ name }}",
            "default.html": "{{ name }}",
            "include.html": """\
escaped: {% include 'escaped.html' %}
unescaped: {% include 'unescaped.html' %}
default: {% include 'default.html' %}
""",
            "escaped_block.html": """\
{% autoescape xhtml_escape %}\
{% block name %}base: {{ name }}{% end %}""",
            "unescaped_block.html": """\
{% autoescape None %}\
{% block name %}base: {{ name }}{% end %}""",
            # Extend a base template with different autoescape policy,
            # with and without overriding the base's blocks
            "escaped_extends_unescaped.html": """\
{% autoescape xhtml_escape %}\
{% extends "unescaped_block.html" %}""",
            "escaped_overrides_unescaped.html": """\
{% autoescape xhtml_escape %}\
{% extends "unescaped_block.html" %}\
{% block name %}extended: {{ name }}{% end %}""",
            "unescaped_extends_escaped.html": """\
{% autoescape None %}\
{% extends "escaped_block.html" %}""",
            "unescaped_overrides_escaped.html": """\
{% autoescape None %}\
{% extends "escaped_block.html" %}\
{% block name %}extended: {{ name }}{% end %}""",
            "raw_expression.html": """\
{% autoescape xhtml_escape %}\
expr: {{ name }}
raw: {% raw name %}""",
        }

    def test_default_off(self):
        loader = DictLoader(self.templates, autoescape=None)
        name = "Bobby <table>s"
        self.assertEqual(
            loader.load("escaped.html").generate(name=name), b"Bobby &lt;table&gt;s"
        )
        self.assertEqual(
            loader.load("unescaped.html").generate(name=name), b"Bobby <table>s"
        )
        self.assertEqual(
            loader.load("default.html").generate(name=name), b"Bobby <table>s"
        )

        self.assertEqual(
            loader.load("include.html").generate(name=name),
            b"escaped: Bobby &lt;table&gt;s\n"
            b"unescaped: Bobby <table>s\n"
            b"default: Bobby <table>s\n",
        )

    def test_default_on(self):
        loader = DictLoader(self.templates, autoescape="xhtml_escape")
        name = "Bobby <table>s"
        self.assertEqual(
            loader.load("escaped.html").generate(name=name), b"Bobby &lt;table&gt;s"
        )
        self.assertEqual(
            loader.load("unescaped.html").generate(name=name), b"Bobby <table>s"
        )
        self.assertEqual(
            loader.load("default.html").generate(name=name), b"Bobby &lt;table&gt;s"
        )

        self.assertEqual(
            loader.load("include.html").generate(name=name),
            b"escaped: Bobby &lt;table&gt;s\n"
            b"unescaped: Bobby <table>s\n"
            b"default: Bobby &lt;table&gt;s\n",
        )

    def test_unextended_block(self):
        loader = DictLoader(self.templates)
        name = "<script>"
        self.assertEqual(
            loader.load("escaped_block.html").generate(name=name),
            b"base: &lt;script&gt;",
        )
        self.assertEqual(
            loader.load("unescaped_block.html").generate(name=name), b"base: <script>"
        )

    def test_extended_block(self):
        loader = DictLoader(self.templates)

        def render(name):
            return loader.load(name).generate(name="<script>")

        self.assertEqual(render("escaped_extends_unescaped.html"), b"base: <script>")
        self.assertEqual(
            render("escaped_overrides_unescaped.html"), b"extended: &lt;script&gt;"
        )

        self.assertEqual(
            render("unescaped_extends_escaped.html"), b"base: &lt;script&gt;"
        )
        self.assertEqual(
            render("unescaped_overrides_escaped.html"), b"extended: <script>"
        )

    def test_raw_expression(self):
        loader = DictLoader(self.templates)

        def render(name):
            return loader.load(name).generate(name='<>&"')

        self.assertEqual(
            render("raw_expression.html"), b"expr: &lt;&gt;&amp;&quot;\n" b'raw: <>&"'
        )

    def test_custom_escape(self):
        loader = DictLoader({"foo.py": "{% autoescape py_escape %}s = {{ name }}\n"})

        def py_escape(s):
            self.assertEqual(type(s), bytes)
            return repr(native_str(s))

        def render(template, name):
            return loader.load(template).generate(py_escape=py_escape, name=name)

        self.assertEqual(render("foo.py", "<html>"), b"s = '<html>'\n")
        self.assertEqual(render("foo.py", "';sys.exit()"), b"""s = "';sys.exit()"\n""")
        self.assertEqual(
            render("foo.py", ["not a string"]), b"""s = "['not a string']"\n"""
        )

    def test_manual_minimize_whitespace(self):
        # Whitespace including newlines is allowed within template tags
        # and directives, and this is one way to avoid long lines while
        # keeping extra whitespace out of the rendered output.
        loader = DictLoader(
            {
                "foo.txt": """\
{% for i in items
  %}{% if i > 0 %}, {% end %}{#
  #}{{i
  }}{% end
%}"""
            }
        )
        self.assertEqual(
            loader.load("foo.txt").generate(items=range(5)), b"0, 1, 2, 3, 4"
        )

    def test_whitespace_by_filename(self):
        # Default whitespace handling depends on the template filename.
        loader = DictLoader(
            {
                "foo.html": "   \n\t\n asdf\t   ",
                "bar.js": " \n\n\n\t qwer     ",
                "baz.txt": "\t    zxcv\n\n",
                "include.html": "  {% include baz.txt %} \n ",
                "include.txt": "\t\t{% include foo.html %}    ",
            }
        )

        # HTML and JS files have whitespace compressed by default.
        self.assertEqual(loader.load("foo.html").generate(), b"\nasdf ")
        self.assertEqual(loader.load("bar.js").generate(), b"\nqwer ")
        # TXT files do not.
        self.assertEqual(loader.load("baz.txt").generate(), b"\t    zxcv\n\n")

        # Each file maintains its own status even when included in
        # a file of the other type.
        self.assertEqual(loader.load("include.html").generate(), b" \t    zxcv\n\n\n")
        self.assertEqual(loader.load("include.txt").generate(), b"\t\t\nasdf     ")

    def test_whitespace_by_loader(self):
        templates = {"foo.html": "\t\tfoo\n\n", "bar.txt": "\t\tbar\n\n"}
        loader = DictLoader(templates, whitespace="all")
        self.assertEqual(loader.load("foo.html").generate(), b"\t\tfoo\n\n")
        self.assertEqual(loader.load("bar.txt").generate(), b"\t\tbar\n\n")

        loader = DictLoader(templates, whitespace="single")
        self.assertEqual(loader.load("foo.html").generate(), b" foo\n")
        self.assertEqual(loader.load("bar.txt").generate(), b" bar\n")

        loader = DictLoader(templates, whitespace="oneline")
        self.assertEqual(loader.load("foo.html").generate(), b" foo ")
        self.assertEqual(loader.load("bar.txt").generate(), b" bar ")

    def test_whitespace_directive(self):
        loader = DictLoader(
            {
                "foo.html": """\
{% whitespace oneline %}
    {% for i in range(3) %}
        {{ i }}
    {% end %}
{% whitespace all %}
    pre\tformatted
"""
            }
        )
        self.assertEqual(
            loader.load("foo.html").generate(), b"  0  1  2  \n    pre\tformatted\n"
        )


class TemplateLoaderTest(unittest.TestCase):
    def setUp(self):
        self.loader = Loader(os.path.join(os.path.dirname(__file__), "templates"))

    def test_utf8_in_file(self):
        tmpl = self.loader.load("utf8.html")
        result = tmpl.generate()
        self.assertEqual(to_unicode(result).strip(), "H\u00e9llo")

# === NexusCore/myenv\Lib\site-packages\pip\_internal\vcs\git.py ===
import logging
import os.path
import pathlib
import re
import urllib.parse
import urllib.request
from dataclasses import replace
from typing import List, Optional, Tuple

from pip._internal.exceptions import BadCommand, InstallationError
from pip._internal.utils.misc import HiddenText, display_path, hide_url
from pip._internal.utils.subprocess import make_command
from pip._internal.vcs.versioncontrol import (
    AuthInfo,
    RemoteNotFoundError,
    RemoteNotValidError,
    RevOptions,
    VersionControl,
    find_path_to_project_root_from_repo_root,
    vcs,
)

urlsplit = urllib.parse.urlsplit
urlunsplit = urllib.parse.urlunsplit


logger = logging.getLogger(__name__)


GIT_VERSION_REGEX = re.compile(
    r"^git version "  # Prefix.
    r"(\d+)"  # Major.
    r"\.(\d+)"  # Dot, minor.
    r"(?:\.(\d+))?"  # Optional dot, patch.
    r".*$"  # Suffix, including any pre- and post-release segments we don't care about.
)

HASH_REGEX = re.compile("^[a-fA-F0-9]{40}$")

# SCP (Secure copy protocol) shorthand. e.g. 'git@example.com:foo/bar.git'
SCP_REGEX = re.compile(
    r"""^
    # Optional user, e.g. 'git@'
    (\w+@)?
    # Server, e.g. 'github.com'.
    ([^/:]+):
    # The server-side path. e.g. 'user/project.git'. Must start with an
    # alphanumeric character so as not to be confusable with a Windows paths
    # like 'C:/foo/bar' or 'C:\foo\bar'.
    (\w[^:]*)
    $""",
    re.VERBOSE,
)


def looks_like_hash(sha: str) -> bool:
    return bool(HASH_REGEX.match(sha))


class Git(VersionControl):
    name = "git"
    dirname = ".git"
    repo_name = "clone"
    schemes = (
        "git+http",
        "git+https",
        "git+ssh",
        "git+git",
        "git+file",
    )
    # Prevent the user's environment variables from interfering with pip:
    # https://github.com/pypa/pip/issues/1130
    unset_environ = ("GIT_DIR", "GIT_WORK_TREE")
    default_arg_rev = "HEAD"

    @staticmethod
    def get_base_rev_args(rev: str) -> List[str]:
        return [rev]

    def is_immutable_rev_checkout(self, url: str, dest: str) -> bool:
        _, rev_options = self.get_url_rev_options(hide_url(url))
        if not rev_options.rev:
            return False
        if not self.is_commit_id_equal(dest, rev_options.rev):
            # the current commit is different from rev,
            # which means rev was something else than a commit hash
            return False
        # return False in the rare case rev is both a commit hash
        # and a tag or a branch; we don't want to cache in that case
        # because that branch/tag could point to something else in the future
        is_tag_or_branch = bool(self.get_revision_sha(dest, rev_options.rev)[0])
        return not is_tag_or_branch

    def get_git_version(self) -> Tuple[int, ...]:
        version = self.run_command(
            ["version"],
            command_desc="git version",
            show_stdout=False,
            stdout_only=True,
        )
        match = GIT_VERSION_REGEX.match(version)
        if not match:
            logger.warning("Can't parse git version: %s", version)
            return ()
        return (int(match.group(1)), int(match.group(2)))

    @classmethod
    def get_current_branch(cls, location: str) -> Optional[str]:
        """
        Return the current branch, or None if HEAD isn't at a branch
        (e.g. detached HEAD).
        """
        # git-symbolic-ref exits with empty stdout if "HEAD" is a detached
        # HEAD rather than a symbolic ref.  In addition, the -q causes the
        # command to exit with status code 1 instead of 128 in this case
        # and to suppress the message to stderr.
        args = ["symbolic-ref", "-q", "HEAD"]
        output = cls.run_command(
            args,
            extra_ok_returncodes=(1,),
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        )
        ref = output.strip()

        if ref.startswith("refs/heads/"):
            return ref[len("refs/heads/") :]

        return None

    @classmethod
    def get_revision_sha(cls, dest: str, rev: str) -> Tuple[Optional[str], bool]:
        """
        Return (sha_or_none, is_branch), where sha_or_none is a commit hash
        if the revision names a remote branch or tag, otherwise None.

        Args:
          dest: the repository directory.
          rev: the revision name.
        """
        # Pass rev to pre-filter the list.
        output = cls.run_command(
            ["show-ref", rev],
            cwd=dest,
            show_stdout=False,
            stdout_only=True,
            on_returncode="ignore",
        )
        refs = {}
        # NOTE: We do not use splitlines here since that would split on other
        #       unicode separators, which can be maliciously used to install a
        #       different revision.
        for line in output.strip().split("\n"):
            line = line.rstrip("\r")
            if not line:
                continue
            try:
                ref_sha, ref_name = line.split(" ", maxsplit=2)
            except ValueError:
                # Include the offending line to simplify troubleshooting if
                # this error ever occurs.
                raise ValueError(f"unexpected show-ref line: {line!r}")

            refs[ref_name] = ref_sha

        branch_ref = f"refs/remotes/origin/{rev}"
        tag_ref = f"refs/tags/{rev}"

        sha = refs.get(branch_ref)
        if sha is not None:
            return (sha, True)

        sha = refs.get(tag_ref)

        return (sha, False)

    @classmethod
    def _should_fetch(cls, dest: str, rev: str) -> bool:
        """
        Return true if rev is a ref or is a commit that we don't have locally.

        Branches and tags are not considered in this method because they are
        assumed to be always available locally (which is a normal outcome of
        ``git clone`` and ``git fetch --tags``).
        """
        if rev.startswith("refs/"):
            # Always fetch remote refs.
            return True

        if not looks_like_hash(rev):
            # Git fetch would fail with abbreviated commits.
            return False

        if cls.has_commit(dest, rev):
            # Don't fetch if we have the commit locally.
            return False

        return True

    @classmethod
    def resolve_revision(
        cls, dest: str, url: HiddenText, rev_options: RevOptions
    ) -> RevOptions:
        """
        Resolve a revision to a new RevOptions object with the SHA1 of the
        branch, tag, or ref if found.

        Args:
          rev_options: a RevOptions object.
        """
        rev = rev_options.arg_rev
        # The arg_rev property's implementation for Git ensures that the
        # rev return value is always non-None.
        assert rev is not None

        sha, is_branch = cls.get_revision_sha(dest, rev)

        if sha is not None:
            rev_options = rev_options.make_new(sha)
            rev_options = replace(rev_options, branch_name=(rev if is_branch else None))

            return rev_options

        # Do not show a warning for the common case of something that has
        # the form of a Git commit hash.
        if not looks_like_hash(rev):
            logger.warning(
                "Did not find branch or tag '%s', assuming revision or ref.",
                rev,
            )

        if not cls._should_fetch(dest, rev):
            return rev_options

        # fetch the requested revision
        cls.run_command(
            make_command("fetch", "-q", url, rev_options.to_args()),
            cwd=dest,
        )
        # Change the revision to the SHA of the ref we fetched
        sha = cls.get_revision(dest, rev="FETCH_HEAD")
        rev_options = rev_options.make_new(sha)

        return rev_options

    @classmethod
    def is_commit_id_equal(cls, dest: str, name: Optional[str]) -> bool:
        """
        Return whether the current commit hash equals the given name.

        Args:
          dest: the repository directory.
          name: a string name.
        """
        if not name:
            # Then avoid an unnecessary subprocess call.
            return False

        return cls.get_revision(dest) == name

    def fetch_new(
        self, dest: str, url: HiddenText, rev_options: RevOptions, verbosity: int
    ) -> None:
        rev_display = rev_options.to_display()
        logger.info("Cloning %s%s to %s", url, rev_display, display_path(dest))
        if verbosity <= 0:
            flags: Tuple[str, ...] = ("--quiet",)
        elif verbosity == 1:
            flags = ()
        else:
            flags = ("--verbose", "--progress")
        if self.get_git_version() >= (2, 17):
            # Git added support for partial clone in 2.17
            # https://git-scm.com/docs/partial-clone
            # Speeds up cloning by functioning without a complete copy of repository
            self.run_command(
                make_command(
                    "clone",
                    "--filter=blob:none",
                    *flags,
                    url,
                    dest,
                )
            )
        else:
            self.run_command(make_command("clone", *flags, url, dest))

        if rev_options.rev:
            # Then a specific revision was requested.
            rev_options = self.resolve_revision(dest, url, rev_options)
            branch_name = getattr(rev_options, "branch_name", None)
            logger.debug("Rev options %s, branch_name %s", rev_options, branch_name)
            if branch_name is None:
                # Only do a checkout if the current commit id doesn't match
                # the requested revision.
                if not self.is_commit_id_equal(dest, rev_options.rev):
                    cmd_args = make_command(
                        "checkout",
                        "-q",
                        rev_options.to_args(),
                    )
                    self.run_command(cmd_args, cwd=dest)
            elif self.get_current_branch(dest) != branch_name:
                # Then a specific branch was requested, and that branch
                # is not yet checked out.
                track_branch = f"origin/{branch_name}"
                cmd_args = [
                    "checkout",
                    "-b",
                    branch_name,
                    "--track",
                    track_branch,
                ]
                self.run_command(cmd_args, cwd=dest)
        else:
            sha = self.get_revision(dest)
            rev_options = rev_options.make_new(sha)

        logger.info("Resolved %s to commit %s", url, rev_options.rev)

        #: repo may contain submodules
        self.update_submodules(dest)

    def switch(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        self.run_command(
            make_command("config", "remote.origin.url", url),
            cwd=dest,
        )
        cmd_args = make_command("checkout", "-q", rev_options.to_args())
        self.run_command(cmd_args, cwd=dest)

        self.update_submodules(dest)

    def update(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        # First fetch changes from the default remote
        if self.get_git_version() >= (1, 9):
            # fetch tags in addition to everything else
            self.run_command(["fetch", "-q", "--tags"], cwd=dest)
        else:
            self.run_command(["fetch", "-q"], cwd=dest)
        # Then reset to wanted revision (maybe even origin/master)
        rev_options = self.resolve_revision(dest, url, rev_options)
        cmd_args = make_command("reset", "--hard", "-q", rev_options.to_args())
        self.run_command(cmd_args, cwd=dest)
        #: update submodules
        self.update_submodules(dest)

    @classmethod
    def get_remote_url(cls, location: str) -> str:
        """
        Return URL of the first remote encountered.

        Raises RemoteNotFoundError if the repository does not have a remote
        url configured.
        """
        # We need to pass 1 for extra_ok_returncodes since the command
        # exits with return code 1 if there are no matching lines.
        stdout = cls.run_command(
            ["config", "--get-regexp", r"remote\..*\.url"],
            extra_ok_returncodes=(1,),
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        )
        remotes = stdout.splitlines()
        try:
            found_remote = remotes[0]
        except IndexError:
            raise RemoteNotFoundError

        for remote in remotes:
            if remote.startswith("remote.origin.url "):
                found_remote = remote
                break
        url = found_remote.split(" ")[1]
        return cls._git_remote_to_pip_url(url.strip())

    @staticmethod
    def _git_remote_to_pip_url(url: str) -> str:
        """
        Convert a remote url from what git uses to what pip accepts.

        There are 3 legal forms **url** may take:

            1. A fully qualified url: ssh://git@example.com/foo/bar.git
            2. A local project.git folder: /path/to/bare/repository.git
            3. SCP shorthand for form 1: git@example.com:foo/bar.git

        Form 1 is output as-is. Form 2 must be converted to URI and form 3 must
        be converted to form 1.

        See the corresponding test test_git_remote_url_to_pip() for examples of
        sample inputs/outputs.
        """
        if re.match(r"\w+://", url):
            # This is already valid. Pass it though as-is.
            return url
        if os.path.exists(url):
            # A local bare remote (git clone --mirror).
            # Needs a file:// prefix.
            return pathlib.PurePath(url).as_uri()
        scp_match = SCP_REGEX.match(url)
        if scp_match:
            # Add an ssh:// prefix and replace the ':' with a '/'.
            return scp_match.expand(r"ssh://\1\2/\3")
        # Otherwise, bail out.
        raise RemoteNotValidError(url)

    @classmethod
    def has_commit(cls, location: str, rev: str) -> bool:
        """
        Check if rev is a commit that is available in the local repository.
        """
        try:
            cls.run_command(
                ["rev-parse", "-q", "--verify", "sha^" + rev],
                cwd=location,
                log_failed_cmd=False,
            )
        except InstallationError:
            return False
        else:
            return True

    @classmethod
    def get_revision(cls, location: str, rev: Optional[str] = None) -> str:
        if rev is None:
            rev = "HEAD"
        current_rev = cls.run_command(
            ["rev-parse", rev],
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        )
        return current_rev.strip()

    @classmethod
    def get_subdirectory(cls, location: str) -> Optional[str]:
        """
        Return the path to Python project root, relative to the repo root.
        Return None if the project root is in the repo root.
        """
        # find the repo root
        git_dir = cls.run_command(
            ["rev-parse", "--git-dir"],
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        ).strip()
        if not os.path.isabs(git_dir):
            git_dir = os.path.join(location, git_dir)
        repo_root = os.path.abspath(os.path.join(git_dir, ".."))
        return find_path_to_project_root_from_repo_root(location, repo_root)

    @classmethod
    def get_url_rev_and_auth(cls, url: str) -> Tuple[str, Optional[str], AuthInfo]:
        """
        Prefixes stub URLs like 'user@hostname:user/repo.git' with 'ssh://'.
        That's required because although they use SSH they sometimes don't
        work with a ssh:// scheme (e.g. GitHub). But we need a scheme for
        parsing. Hence we remove it again afterwards and return it as a stub.
        """
        # Works around an apparent Git bug
        # (see https://article.gmane.org/gmane.comp.version-control.git/146500)
        scheme, netloc, path, query, fragment = urlsplit(url)
        if scheme.endswith("file"):
            initial_slashes = path[: -len(path.lstrip("/"))]
            newpath = initial_slashes + urllib.request.url2pathname(path).replace(
                "\\", "/"
            ).lstrip("/")
            after_plus = scheme.find("+") + 1
            url = scheme[:after_plus] + urlunsplit(
                (scheme[after_plus:], netloc, newpath, query, fragment),
            )

        if "://" not in url:
            assert "file:" not in url
            url = url.replace("git+", "git+ssh://")
            url, rev, user_pass = super().get_url_rev_and_auth(url)
            url = url.replace("ssh://", "")
        else:
            url, rev, user_pass = super().get_url_rev_and_auth(url)

        return url, rev, user_pass

    @classmethod
    def update_submodules(cls, location: str) -> None:
        if not os.path.exists(os.path.join(location, ".gitmodules")):
            return
        cls.run_command(
            ["submodule", "update", "--init", "--recursive", "-q"],
            cwd=location,
        )

    @classmethod
    def get_repository_root(cls, location: str) -> Optional[str]:
        loc = super().get_repository_root(location)
        if loc:
            return loc
        try:
            r = cls.run_command(
                ["rev-parse", "--show-toplevel"],
                cwd=location,
                show_stdout=False,
                stdout_only=True,
                on_returncode="raise",
                log_failed_cmd=False,
            )
        except BadCommand:
            logger.debug(
                "could not determine if %s is under git control "
                "because git is not available",
                location,
            )
            return None
        except InstallationError:
            return None
        return os.path.normpath(r.rstrip("\r\n"))

    @staticmethod
    def should_add_vcs_url_prefix(repo_url: str) -> bool:
        """In either https or ssh form, requirements must be prefixed with git+."""
        return True


vcs.register(Git)

# === NexusCore/openenv\Lib\site-packages\anyio\from_thread.py ===
from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable, Generator
from concurrent.futures import Future
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    contextmanager,
)
from dataclasses import dataclass, field
from inspect import isawaitable
from threading import Lock, Thread, get_ident
from types import TracebackType
from typing import (
    Any,
    Generic,
    TypeVar,
    cast,
    overload,
)

from ._core import _eventloop
from ._core._eventloop import get_async_backend, get_cancelled_exc_class, threadlocals
from ._core._synchronization import Event
from ._core._tasks import CancelScope, create_task_group
from .abc import AsyncBackend
from .abc._tasks import TaskStatus

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from typing_extensions import TypeVarTuple, Unpack

T_Retval = TypeVar("T_Retval")
T_co = TypeVar("T_co", covariant=True)
PosArgsT = TypeVarTuple("PosArgsT")


def run(
    func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval]], *args: Unpack[PosArgsT]
) -> T_Retval:
    """
    Call a coroutine function from a worker thread.

    :param func: a coroutine function
    :param args: positional arguments for the callable
    :return: the return value of the coroutine function

    """
    try:
        async_backend = threadlocals.current_async_backend
        token = threadlocals.current_token
    except AttributeError:
        raise RuntimeError(
            "This function can only be run from an AnyIO worker thread"
        ) from None

    return async_backend.run_async_from_thread(func, args, token=token)


def run_sync(
    func: Callable[[Unpack[PosArgsT]], T_Retval], *args: Unpack[PosArgsT]
) -> T_Retval:
    """
    Call a function in the event loop thread from a worker thread.

    :param func: a callable
    :param args: positional arguments for the callable
    :return: the return value of the callable

    """
    try:
        async_backend = threadlocals.current_async_backend
        token = threadlocals.current_token
    except AttributeError:
        raise RuntimeError(
            "This function can only be run from an AnyIO worker thread"
        ) from None

    return async_backend.run_sync_from_thread(func, args, token=token)


class _BlockingAsyncContextManager(Generic[T_co], AbstractContextManager):
    _enter_future: Future[T_co]
    _exit_future: Future[bool | None]
    _exit_event: Event
    _exit_exc_info: tuple[
        type[BaseException] | None, BaseException | None, TracebackType | None
    ] = (None, None, None)

    def __init__(
        self, async_cm: AbstractAsyncContextManager[T_co], portal: BlockingPortal
    ):
        self._async_cm = async_cm
        self._portal = portal

    async def run_async_cm(self) -> bool | None:
        try:
            self._exit_event = Event()
            value = await self._async_cm.__aenter__()
        except BaseException as exc:
            self._enter_future.set_exception(exc)
            raise
        else:
            self._enter_future.set_result(value)

        try:
            # Wait for the sync context manager to exit.
            # This next statement can raise `get_cancelled_exc_class()` if
            # something went wrong in a task group in this async context
            # manager.
            await self._exit_event.wait()
        finally:
            # In case of cancellation, it could be that we end up here before
            # `_BlockingAsyncContextManager.__exit__` is called, and an
            # `_exit_exc_info` has been set.
            result = await self._async_cm.__aexit__(*self._exit_exc_info)
            return result

    def __enter__(self) -> T_co:
        self._enter_future = Future()
        self._exit_future = self._portal.start_task_soon(self.run_async_cm)
        return self._enter_future.result()

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None,
    ) -> bool | None:
        self._exit_exc_info = __exc_type, __exc_value, __traceback
        self._portal.call(self._exit_event.set)
        return self._exit_future.result()


class _BlockingPortalTaskStatus(TaskStatus):
    def __init__(self, future: Future):
        self._future = future

    def started(self, value: object = None) -> None:
        self._future.set_result(value)


class BlockingPortal:
    """An object that lets external threads run code in an asynchronous event loop."""

    def __new__(cls) -> BlockingPortal:
        return get_async_backend().create_blocking_portal()

    def __init__(self) -> None:
        self._event_loop_thread_id: int | None = get_ident()
        self._stop_event = Event()
        self._task_group = create_task_group()
        self._cancelled_exc_class = get_cancelled_exc_class()

    async def __aenter__(self) -> BlockingPortal:
        await self._task_group.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        await self.stop()
        return await self._task_group.__aexit__(exc_type, exc_val, exc_tb)

    def _check_running(self) -> None:
        if self._event_loop_thread_id is None:
            raise RuntimeError("This portal is not running")
        if self._event_loop_thread_id == get_ident():
            raise RuntimeError(
                "This method cannot be called from the event loop thread"
            )

    async def sleep_until_stopped(self) -> None:
        """Sleep until :meth:`stop` is called."""
        await self._stop_event.wait()

    async def stop(self, cancel_remaining: bool = False) -> None:
        """
        Signal the portal to shut down.

        This marks the portal as no longer accepting new calls and exits from
        :meth:`sleep_until_stopped`.

        :param cancel_remaining: ``True`` to cancel all the remaining tasks, ``False``
            to let them finish before returning

        """
        self._event_loop_thread_id = None
        self._stop_event.set()
        if cancel_remaining:
            self._task_group.cancel_scope.cancel()

    async def _call_func(
        self,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval] | T_Retval],
        args: tuple[Unpack[PosArgsT]],
        kwargs: dict[str, Any],
        future: Future[T_Retval],
    ) -> None:
        def callback(f: Future[T_Retval]) -> None:
            if f.cancelled() and self._event_loop_thread_id not in (
                None,
                get_ident(),
            ):
                self.call(scope.cancel)

        try:
            retval_or_awaitable = func(*args, **kwargs)
            if isawaitable(retval_or_awaitable):
                with CancelScope() as scope:
                    if future.cancelled():
                        scope.cancel()
                    else:
                        future.add_done_callback(callback)

                    retval = await retval_or_awaitable
            else:
                retval = retval_or_awaitable
        except self._cancelled_exc_class:
            future.cancel()
            future.set_running_or_notify_cancel()
        except BaseException as exc:
            if not future.cancelled():
                future.set_exception(exc)

            # Let base exceptions fall through
            if not isinstance(exc, Exception):
                raise
        else:
            if not future.cancelled():
                future.set_result(retval)
        finally:
            scope = None  # type: ignore[assignment]

    def _spawn_task_from_thread(
        self,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval] | T_Retval],
        args: tuple[Unpack[PosArgsT]],
        kwargs: dict[str, Any],
        name: object,
        future: Future[T_Retval],
    ) -> None:
        """
        Spawn a new task using the given callable.

        Implementers must ensure that the future is resolved when the task finishes.

        :param func: a callable
        :param args: positional arguments to be passed to the callable
        :param kwargs: keyword arguments to be passed to the callable
        :param name: name of the task (will be coerced to a string if not ``None``)
        :param future: a future that will resolve to the return value of the callable,
            or the exception raised during its execution

        """
        raise NotImplementedError

    @overload
    def call(
        self,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval]],
        *args: Unpack[PosArgsT],
    ) -> T_Retval: ...

    @overload
    def call(
        self, func: Callable[[Unpack[PosArgsT]], T_Retval], *args: Unpack[PosArgsT]
    ) -> T_Retval: ...

    def call(
        self,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval] | T_Retval],
        *args: Unpack[PosArgsT],
    ) -> T_Retval:
        """
        Call the given function in the event loop thread.

        If the callable returns a coroutine object, it is awaited on.

        :param func: any callable
        :raises RuntimeError: if the portal is not running or if this method is called
            from within the event loop thread

        """
        return cast(T_Retval, self.start_task_soon(func, *args).result())

    @overload
    def start_task_soon(
        self,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval]],
        *args: Unpack[PosArgsT],
        name: object = None,
    ) -> Future[T_Retval]: ...

    @overload
    def start_task_soon(
        self,
        func: Callable[[Unpack[PosArgsT]], T_Retval],
        *args: Unpack[PosArgsT],
        name: object = None,
    ) -> Future[T_Retval]: ...

    def start_task_soon(
        self,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval] | T_Retval],
        *args: Unpack[PosArgsT],
        name: object = None,
    ) -> Future[T_Retval]:
        """
        Start a task in the portal's task group.

        The task will be run inside a cancel scope which can be cancelled by cancelling
        the returned future.

        :param func: the target function
        :param args: positional arguments passed to ``func``
        :param name: name of the task (will be coerced to a string if not ``None``)
        :return: a future that resolves with the return value of the callable if the
            task completes successfully, or with the exception raised in the task
        :raises RuntimeError: if the portal is not running or if this method is called
            from within the event loop thread
        :rtype: concurrent.futures.Future[T_Retval]

        .. versionadded:: 3.0

        """
        self._check_running()
        f: Future[T_Retval] = Future()
        self._spawn_task_from_thread(func, args, {}, name, f)
        return f

    def start_task(
        self,
        func: Callable[..., Awaitable[T_Retval]],
        *args: object,
        name: object = None,
    ) -> tuple[Future[T_Retval], Any]:
        """
        Start a task in the portal's task group and wait until it signals for readiness.

        This method works the same way as :meth:`.abc.TaskGroup.start`.

        :param func: the target function
        :param args: positional arguments passed to ``func``
        :param name: name of the task (will be coerced to a string if not ``None``)
        :return: a tuple of (future, task_status_value) where the ``task_status_value``
            is the value passed to ``task_status.started()`` from within the target
            function
        :rtype: tuple[concurrent.futures.Future[T_Retval], Any]

        .. versionadded:: 3.0

        """

        def task_done(future: Future[T_Retval]) -> None:
            if not task_status_future.done():
                if future.cancelled():
                    task_status_future.cancel()
                elif future.exception():
                    task_status_future.set_exception(future.exception())
                else:
                    exc = RuntimeError(
                        "Task exited without calling task_status.started()"
                    )
                    task_status_future.set_exception(exc)

        self._check_running()
        task_status_future: Future = Future()
        task_status = _BlockingPortalTaskStatus(task_status_future)
        f: Future = Future()
        f.add_done_callback(task_done)
        self._spawn_task_from_thread(func, args, {"task_status": task_status}, name, f)
        return f, task_status_future.result()

    def wrap_async_context_manager(
        self, cm: AbstractAsyncContextManager[T_co]
    ) -> AbstractContextManager[T_co]:
        """
        Wrap an async context manager as a synchronous context manager via this portal.

        Spawns a task that will call both ``__aenter__()`` and ``__aexit__()``, stopping
        in the middle until the synchronous context manager exits.

        :param cm: an asynchronous context manager
        :return: a synchronous context manager

        .. versionadded:: 2.1

        """
        return _BlockingAsyncContextManager(cm, self)


@dataclass
class BlockingPortalProvider:
    """
    A manager for a blocking portal. Used as a context manager. The first thread to
    enter this context manager causes a blocking portal to be started with the specific
    parameters, and the last thread to exit causes the portal to be shut down. Thus,
    there will be exactly one blocking portal running in this context as long as at
    least one thread has entered this context manager.

    The parameters are the same as for :func:`~anyio.run`.

    :param backend: name of the backend
    :param backend_options: backend options

    .. versionadded:: 4.4
    """

    backend: str = "asyncio"
    backend_options: dict[str, Any] | None = None
    _lock: Lock = field(init=False, default_factory=Lock)
    _leases: int = field(init=False, default=0)
    _portal: BlockingPortal = field(init=False)
    _portal_cm: AbstractContextManager[BlockingPortal] | None = field(
        init=False, default=None
    )

    def __enter__(self) -> BlockingPortal:
        with self._lock:
            if self._portal_cm is None:
                self._portal_cm = start_blocking_portal(
                    self.backend, self.backend_options
                )
                self._portal = self._portal_cm.__enter__()

            self._leases += 1
            return self._portal

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        portal_cm: AbstractContextManager[BlockingPortal] | None = None
        with self._lock:
            assert self._portal_cm
            assert self._leases > 0
            self._leases -= 1
            if not self._leases:
                portal_cm = self._portal_cm
                self._portal_cm = None
                del self._portal

        if portal_cm:
            portal_cm.__exit__(None, None, None)


@contextmanager
def start_blocking_portal(
    backend: str = "asyncio", backend_options: dict[str, Any] | None = None
) -> Generator[BlockingPortal, Any, None]:
    """
    Start a new event loop in a new thread and run a blocking portal in its main task.

    The parameters are the same as for :func:`~anyio.run`.

    :param backend: name of the backend
    :param backend_options: backend options
    :return: a context manager that yields a blocking portal

    .. versionchanged:: 3.0
        Usage as a context manager is now required.

    """

    async def run_portal() -> None:
        async with BlockingPortal() as portal_:
            future.set_result(portal_)
            await portal_.sleep_until_stopped()

    def run_blocking_portal() -> None:
        if future.set_running_or_notify_cancel():
            try:
                _eventloop.run(
                    run_portal, backend=backend, backend_options=backend_options
                )
            except BaseException as exc:
                if not future.done():
                    future.set_exception(exc)

    future: Future[BlockingPortal] = Future()
    thread = Thread(target=run_blocking_portal, daemon=True)
    thread.start()
    try:
        cancel_remaining_tasks = False
        portal = future.result()
        try:
            yield portal
        except BaseException:
            cancel_remaining_tasks = True
            raise
        finally:
            try:
                portal.call(portal.stop, cancel_remaining_tasks)
            except RuntimeError:
                pass
    finally:
        thread.join()


def check_cancelled() -> None:
    """
    Check if the cancel scope of the host task's running the current worker thread has
    been cancelled.

    If the host task's current cancel scope has indeed been cancelled, the
    backend-specific cancellation exception will be raised.

    :raises RuntimeError: if the current thread was not spawned by
        :func:`.to_thread.run_sync`

    """
    try:
        async_backend: AsyncBackend = threadlocals.current_async_backend
    except AttributeError:
        raise RuntimeError(
            "This function can only be run from an AnyIO worker thread"
        ) from None

    async_backend.check_cancelled()

# === NexusCore/openenv\Lib\site-packages\httpx\_urlparse.py ===
"""
An implementation of `urlparse` that provides URL validation and normalization
as described by RFC3986.

We rely on this implementation rather than the one in Python's stdlib, because:

* It provides more complete URL validation.
* It properly differentiates between an empty querystring and an absent querystring,
  to distinguish URLs with a trailing '?'.
* It handles scheme, hostname, port, and path normalization.
* It supports IDNA hostnames, normalizing them to their encoded form.
* The API supports passing individual components, as well as the complete URL string.

Previously we relied on the excellent `rfc3986` package to handle URL parsing and
validation, but this module provides a simpler alternative, with less indirection
required.
"""

from __future__ import annotations

import ipaddress
import re
import typing

import idna

from ._exceptions import InvalidURL

MAX_URL_LENGTH = 65536

# https://datatracker.ietf.org/doc/html/rfc3986.html#section-2.3
UNRESERVED_CHARACTERS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)
SUB_DELIMS = "!$&'()*+,;="

PERCENT_ENCODED_REGEX = re.compile("%[A-Fa-f0-9]{2}")

# https://url.spec.whatwg.org/#percent-encoded-bytes

# The fragment percent-encode set is the C0 control percent-encode set
# and U+0020 SPACE, U+0022 ("), U+003C (<), U+003E (>), and U+0060 (`).
FRAG_SAFE = "".join(
    [chr(i) for i in range(0x20, 0x7F) if i not in (0x20, 0x22, 0x3C, 0x3E, 0x60)]
)

# The query percent-encode set is the C0 control percent-encode set
# and U+0020 SPACE, U+0022 ("), U+0023 (#), U+003C (<), and U+003E (>).
QUERY_SAFE = "".join(
    [chr(i) for i in range(0x20, 0x7F) if i not in (0x20, 0x22, 0x23, 0x3C, 0x3E)]
)

# The path percent-encode set is the query percent-encode set
# and U+003F (?), U+0060 (`), U+007B ({), and U+007D (}).
PATH_SAFE = "".join(
    [
        chr(i)
        for i in range(0x20, 0x7F)
        if i not in (0x20, 0x22, 0x23, 0x3C, 0x3E) + (0x3F, 0x60, 0x7B, 0x7D)
    ]
)

# The userinfo percent-encode set is the path percent-encode set
# and U+002F (/), U+003A (:), U+003B (;), U+003D (=), U+0040 (@),
# U+005B ([) to U+005E (^), inclusive, and U+007C (|).
USERNAME_SAFE = "".join(
    [
        chr(i)
        for i in range(0x20, 0x7F)
        if i
        not in (0x20, 0x22, 0x23, 0x3C, 0x3E)
        + (0x3F, 0x60, 0x7B, 0x7D)
        + (0x2F, 0x3A, 0x3B, 0x3D, 0x40, 0x5B, 0x5C, 0x5D, 0x5E, 0x7C)
    ]
)
PASSWORD_SAFE = "".join(
    [
        chr(i)
        for i in range(0x20, 0x7F)
        if i
        not in (0x20, 0x22, 0x23, 0x3C, 0x3E)
        + (0x3F, 0x60, 0x7B, 0x7D)
        + (0x2F, 0x3A, 0x3B, 0x3D, 0x40, 0x5B, 0x5C, 0x5D, 0x5E, 0x7C)
    ]
)
# Note... The terminology 'userinfo' percent-encode set in the WHATWG document
# is used for the username and password quoting. For the joint userinfo component
# we remove U+003A (:) from the safe set.
USERINFO_SAFE = "".join(
    [
        chr(i)
        for i in range(0x20, 0x7F)
        if i
        not in (0x20, 0x22, 0x23, 0x3C, 0x3E)
        + (0x3F, 0x60, 0x7B, 0x7D)
        + (0x2F, 0x3B, 0x3D, 0x40, 0x5B, 0x5C, 0x5D, 0x5E, 0x7C)
    ]
)


# {scheme}:      (optional)
# //{authority}  (optional)
# {path}
# ?{query}       (optional)
# #{fragment}    (optional)
URL_REGEX = re.compile(
    (
        r"(?:(?P<scheme>{scheme}):)?"
        r"(?://(?P<authority>{authority}))?"
        r"(?P<path>{path})"
        r"(?:\?(?P<query>{query}))?"
        r"(?:#(?P<fragment>{fragment}))?"
    ).format(
        scheme="([a-zA-Z][a-zA-Z0-9+.-]*)?",
        authority="[^/?#]*",
        path="[^?#]*",
        query="[^#]*",
        fragment=".*",
    )
)

# {userinfo}@    (optional)
# {host}
# :{port}        (optional)
AUTHORITY_REGEX = re.compile(
    (
        r"(?:(?P<userinfo>{userinfo})@)?" r"(?P<host>{host})" r":?(?P<port>{port})?"
    ).format(
        userinfo=".*",  # Any character sequence.
        host="(\\[.*\\]|[^:@]*)",  # Either any character sequence excluding ':' or '@',
        # or an IPv6 address enclosed within square brackets.
        port=".*",  # Any character sequence.
    )
)


# If we call urlparse with an individual component, then we need to regex
# validate that component individually.
# Note that we're duplicating the same strings as above. Shock! Horror!!
COMPONENT_REGEX = {
    "scheme": re.compile("([a-zA-Z][a-zA-Z0-9+.-]*)?"),
    "authority": re.compile("[^/?#]*"),
    "path": re.compile("[^?#]*"),
    "query": re.compile("[^#]*"),
    "fragment": re.compile(".*"),
    "userinfo": re.compile("[^@]*"),
    "host": re.compile("(\\[.*\\]|[^:]*)"),
    "port": re.compile(".*"),
}


# We use these simple regexs as a first pass before handing off to
# the stdlib 'ipaddress' module for IP address validation.
IPv4_STYLE_HOSTNAME = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$")
IPv6_STYLE_HOSTNAME = re.compile(r"^\[.*\]$")


class ParseResult(typing.NamedTuple):
    scheme: str
    userinfo: str
    host: str
    port: int | None
    path: str
    query: str | None
    fragment: str | None

    @property
    def authority(self) -> str:
        return "".join(
            [
                f"{self.userinfo}@" if self.userinfo else "",
                f"[{self.host}]" if ":" in self.host else self.host,
                f":{self.port}" if self.port is not None else "",
            ]
        )

    @property
    def netloc(self) -> str:
        return "".join(
            [
                f"[{self.host}]" if ":" in self.host else self.host,
                f":{self.port}" if self.port is not None else "",
            ]
        )

    def copy_with(self, **kwargs: str | None) -> ParseResult:
        if not kwargs:
            return self

        defaults = {
            "scheme": self.scheme,
            "authority": self.authority,
            "path": self.path,
            "query": self.query,
            "fragment": self.fragment,
        }
        defaults.update(kwargs)
        return urlparse("", **defaults)

    def __str__(self) -> str:
        authority = self.authority
        return "".join(
            [
                f"{self.scheme}:" if self.scheme else "",
                f"//{authority}" if authority else "",
                self.path,
                f"?{self.query}" if self.query is not None else "",
                f"#{self.fragment}" if self.fragment is not None else "",
            ]
        )


def urlparse(url: str = "", **kwargs: str | None) -> ParseResult:
    # Initial basic checks on allowable URLs.
    # ---------------------------------------

    # Hard limit the maximum allowable URL length.
    if len(url) > MAX_URL_LENGTH:
        raise InvalidURL("URL too long")

    # If a URL includes any ASCII control characters including \t, \r, \n,
    # then treat it as invalid.
    if any(char.isascii() and not char.isprintable() for char in url):
        char = next(char for char in url if char.isascii() and not char.isprintable())
        idx = url.find(char)
        error = (
            f"Invalid non-printable ASCII character in URL, {char!r} at position {idx}."
        )
        raise InvalidURL(error)

    # Some keyword arguments require special handling.
    # ------------------------------------------------

    # Coerce "port" to a string, if it is provided as an integer.
    if "port" in kwargs:
        port = kwargs["port"]
        kwargs["port"] = str(port) if isinstance(port, int) else port

    # Replace "netloc" with "host and "port".
    if "netloc" in kwargs:
        netloc = kwargs.pop("netloc") or ""
        kwargs["host"], _, kwargs["port"] = netloc.partition(":")

    # Replace "username" and/or "password" with "userinfo".
    if "username" in kwargs or "password" in kwargs:
        username = quote(kwargs.pop("username", "") or "", safe=USERNAME_SAFE)
        password = quote(kwargs.pop("password", "") or "", safe=PASSWORD_SAFE)
        kwargs["userinfo"] = f"{username}:{password}" if password else username

    # Replace "raw_path" with "path" and "query".
    if "raw_path" in kwargs:
        raw_path = kwargs.pop("raw_path") or ""
        kwargs["path"], seperator, kwargs["query"] = raw_path.partition("?")
        if not seperator:
            kwargs["query"] = None

    # Ensure that IPv6 "host" addresses are always escaped with "[...]".
    if "host" in kwargs:
        host = kwargs.get("host") or ""
        if ":" in host and not (host.startswith("[") and host.endswith("]")):
            kwargs["host"] = f"[{host}]"

    # If any keyword arguments are provided, ensure they are valid.
    # -------------------------------------------------------------

    for key, value in kwargs.items():
        if value is not None:
            if len(value) > MAX_URL_LENGTH:
                raise InvalidURL(f"URL component '{key}' too long")

            # If a component includes any ASCII control characters including \t, \r, \n,
            # then treat it as invalid.
            if any(char.isascii() and not char.isprintable() for char in value):
                char = next(
                    char for char in value if char.isascii() and not char.isprintable()
                )
                idx = value.find(char)
                error = (
                    f"Invalid non-printable ASCII character in URL {key} component, "
                    f"{char!r} at position {idx}."
                )
                raise InvalidURL(error)

            # Ensure that keyword arguments match as a valid regex.
            if not COMPONENT_REGEX[key].fullmatch(value):
                raise InvalidURL(f"Invalid URL component '{key}'")

    # The URL_REGEX will always match, but may have empty components.
    url_match = URL_REGEX.match(url)
    assert url_match is not None
    url_dict = url_match.groupdict()

    # * 'scheme', 'authority', and 'path' may be empty strings.
    # * 'query' may be 'None', indicating no trailing "?" portion.
    #   Any string including the empty string, indicates a trailing "?".
    # * 'fragment' may be 'None', indicating no trailing "#" portion.
    #   Any string including the empty string, indicates a trailing "#".
    scheme = kwargs.get("scheme", url_dict["scheme"]) or ""
    authority = kwargs.get("authority", url_dict["authority"]) or ""
    path = kwargs.get("path", url_dict["path"]) or ""
    query = kwargs.get("query", url_dict["query"])
    frag = kwargs.get("fragment", url_dict["fragment"])

    # The AUTHORITY_REGEX will always match, but may have empty components.
    authority_match = AUTHORITY_REGEX.match(authority)
    assert authority_match is not None
    authority_dict = authority_match.groupdict()

    # * 'userinfo' and 'host' may be empty strings.
    # * 'port' may be 'None'.
    userinfo = kwargs.get("userinfo", authority_dict["userinfo"]) or ""
    host = kwargs.get("host", authority_dict["host"]) or ""
    port = kwargs.get("port", authority_dict["port"])

    # Normalize and validate each component.
    # We end up with a parsed representation of the URL,
    # with components that are plain ASCII bytestrings.
    parsed_scheme: str = scheme.lower()
    parsed_userinfo: str = quote(userinfo, safe=USERINFO_SAFE)
    parsed_host: str = encode_host(host)
    parsed_port: int | None = normalize_port(port, scheme)

    has_scheme = parsed_scheme != ""
    has_authority = (
        parsed_userinfo != "" or parsed_host != "" or parsed_port is not None
    )
    validate_path(path, has_scheme=has_scheme, has_authority=has_authority)
    if has_scheme or has_authority:
        path = normalize_path(path)

    parsed_path: str = quote(path, safe=PATH_SAFE)
    parsed_query: str | None = None if query is None else quote(query, safe=QUERY_SAFE)
    parsed_frag: str | None = None if frag is None else quote(frag, safe=FRAG_SAFE)

    # The parsed ASCII bytestrings are our canonical form.
    # All properties of the URL are derived from these.
    return ParseResult(
        parsed_scheme,
        parsed_userinfo,
        parsed_host,
        parsed_port,
        parsed_path,
        parsed_query,
        parsed_frag,
    )


def encode_host(host: str) -> str:
    if not host:
        return ""

    elif IPv4_STYLE_HOSTNAME.match(host):
        # Validate IPv4 hostnames like #.#.#.#
        #
        # From https://datatracker.ietf.org/doc/html/rfc3986/#section-3.2.2
        #
        # IPv4address = dec-octet "." dec-octet "." dec-octet "." dec-octet
        try:
            ipaddress.IPv4Address(host)
        except ipaddress.AddressValueError:
            raise InvalidURL(f"Invalid IPv4 address: {host!r}")
        return host

    elif IPv6_STYLE_HOSTNAME.match(host):
        # Validate IPv6 hostnames like [...]
        #
        # From https://datatracker.ietf.org/doc/html/rfc3986/#section-3.2.2
        #
        # "A host identified by an Internet Protocol literal address, version 6
        # [RFC3513] or later, is distinguished by enclosing the IP literal
        # within square brackets ("[" and "]").  This is the only place where
        # square bracket characters are allowed in the URI syntax."
        try:
            ipaddress.IPv6Address(host[1:-1])
        except ipaddress.AddressValueError:
            raise InvalidURL(f"Invalid IPv6 address: {host!r}")
        return host[1:-1]

    elif host.isascii():
        # Regular ASCII hostnames
        #
        # From https://datatracker.ietf.org/doc/html/rfc3986/#section-3.2.2
        #
        # reg-name    = *( unreserved / pct-encoded / sub-delims )
        WHATWG_SAFE = '"`{}%|\\'
        return quote(host.lower(), safe=SUB_DELIMS + WHATWG_SAFE)

    # IDNA hostnames
    try:
        return idna.encode(host.lower()).decode("ascii")
    except idna.IDNAError:
        raise InvalidURL(f"Invalid IDNA hostname: {host!r}")


def normalize_port(port: str | int | None, scheme: str) -> int | None:
    # From https://tools.ietf.org/html/rfc3986#section-3.2.3
    #
    # "A scheme may define a default port.  For example, the "http" scheme
    # defines a default port of "80", corresponding to its reserved TCP
    # port number.  The type of port designated by the port number (e.g.,
    # TCP, UDP, SCTP) is defined by the URI scheme.  URI producers and
    # normalizers should omit the port component and its ":" delimiter if
    # port is empty or if its value would be the same as that of the
    # scheme's default."
    if port is None or port == "":
        return None

    try:
        port_as_int = int(port)
    except ValueError:
        raise InvalidURL(f"Invalid port: {port!r}")

    # See https://url.spec.whatwg.org/#url-miscellaneous
    default_port = {"ftp": 21, "http": 80, "https": 443, "ws": 80, "wss": 443}.get(
        scheme
    )
    if port_as_int == default_port:
        return None
    return port_as_int


def validate_path(path: str, has_scheme: bool, has_authority: bool) -> None:
    """
    Path validation rules that depend on if the URL contains
    a scheme or authority component.

    See https://datatracker.ietf.org/doc/html/rfc3986.html#section-3.3
    """
    if has_authority:
        # If a URI contains an authority component, then the path component
        # must either be empty or begin with a slash ("/") character."
        if path and not path.startswith("/"):
            raise InvalidURL("For absolute URLs, path must be empty or begin with '/'")

    if not has_scheme and not has_authority:
        # If a URI does not contain an authority component, then the path cannot begin
        # with two slash characters ("//").
        if path.startswith("//"):
            raise InvalidURL("Relative URLs cannot have a path starting with '//'")

        # In addition, a URI reference (Section 4.1) may be a relative-path reference,
        # in which case the first path segment cannot contain a colon (":") character.
        if path.startswith(":"):
            raise InvalidURL("Relative URLs cannot have a path starting with ':'")


def normalize_path(path: str) -> str:
    """
    Drop "." and ".." segments from a URL path.

    For example:

        normalize_path("/path/./to/somewhere/..") == "/path/to"
    """
    # Fast return when no '.' characters in the path.
    if "." not in path:
        return path

    components = path.split("/")

    # Fast return when no '.' or '..' components in the path.
    if "." not in components and ".." not in components:
        return path

    # https://datatracker.ietf.org/doc/html/rfc3986#section-5.2.4
    output: list[str] = []
    for component in components:
        if component == ".":
            pass
        elif component == "..":
            if output and output != [""]:
                output.pop()
        else:
            output.append(component)
    return "/".join(output)


def PERCENT(string: str) -> str:
    return "".join([f"%{byte:02X}" for byte in string.encode("utf-8")])


def percent_encoded(string: str, safe: str) -> str:
    """
    Use percent-encoding to quote a string.
    """
    NON_ESCAPED_CHARS = UNRESERVED_CHARACTERS + safe

    # Fast path for strings that don't need escaping.
    if not string.rstrip(NON_ESCAPED_CHARS):
        return string

    return "".join(
        [char if char in NON_ESCAPED_CHARS else PERCENT(char) for char in string]
    )


def quote(string: str, safe: str) -> str:
    """
    Use percent-encoding to quote a string, omitting existing '%xx' escape sequences.

    See: https://www.rfc-editor.org/rfc/rfc3986#section-2.1

    * `string`: The string to be percent-escaped.
    * `safe`: A string containing characters that may be treated as safe, and do not
        need to be escaped. Unreserved characters are always treated as safe.
        See: https://www.rfc-editor.org/rfc/rfc3986#section-2.3
    """
    parts = []
    current_position = 0
    for match in re.finditer(PERCENT_ENCODED_REGEX, string):
        start_position, end_position = match.start(), match.end()
        matched_text = match.group(0)
        # Add any text up to the '%xx' escape sequence.
        if start_position != current_position:
            leading_text = string[current_position:start_position]
            parts.append(percent_encoded(leading_text, safe=safe))

        # Add the '%xx' escape sequence.
        parts.append(matched_text)
        current_position = end_position

    # Add any text after the final '%xx' escape sequence.
    if current_position != len(string):
        trailing_text = string[current_position:]
        parts.append(percent_encoded(trailing_text, safe=safe))

    return "".join(parts)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\bedrock\chat\invoke_agent\transformation.py ===
"""
Transformation for Bedrock Invoke Agent

https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_InvokeAgent.html
"""
import base64
import json
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

import httpx

from litellm._logging import verbose_logger
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    convert_content_list_to_str,
)
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.llms.bedrock.base_aws_llm import BaseAWSLLM
from litellm.llms.bedrock.common_utils import BedrockError
from litellm.types.llms.bedrock_invoke_agents import (
    InvokeAgentChunkPayload,
    InvokeAgentEvent,
    InvokeAgentEventHeaders,
    InvokeAgentEventList,
    InvokeAgentTrace,
    InvokeAgentTracePayload,
    InvokeAgentUsage,
)
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import Choices, Message, ModelResponse

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class AmazonInvokeAgentConfig(BaseConfig, BaseAWSLLM):
    def __init__(self, **kwargs):
        BaseConfig.__init__(self, **kwargs)
        BaseAWSLLM.__init__(self, **kwargs)

    def get_supported_openai_params(self, model: str) -> List[str]:
        """
        This is a base invoke agent model mapping. For Invoke Agent - define a bedrock provider specific config that extends this class.

        Bedrock Invoke Agents has 0 OpenAI compatible params

        As of May 29th, 2025 - they don't support streaming.
        """
        return []

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        """
        This is a base invoke agent model mapping. For Invoke Agent - define a bedrock provider specific config that extends this class.
        """
        return optional_params

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        """
        Get the complete url for the request
        """
        ### SET RUNTIME ENDPOINT ###
        aws_bedrock_runtime_endpoint = optional_params.get(
            "aws_bedrock_runtime_endpoint", None
        )  # https://bedrock-runtime.{region_name}.amazonaws.com
        endpoint_url, _ = self.get_runtime_endpoint(
            api_base=api_base,
            aws_bedrock_runtime_endpoint=aws_bedrock_runtime_endpoint,
            aws_region_name=self._get_aws_region_name(
                optional_params=optional_params, model=model
            ),
            endpoint_type="agent",
        )

        agent_id, agent_alias_id = self._get_agent_id_and_alias_id(model)
        session_id = self._get_session_id(optional_params)

        endpoint_url = f"{endpoint_url}/agents/{agent_id}/agentAliases/{agent_alias_id}/sessions/{session_id}/text"

        return endpoint_url

    def sign_request(
        self,
        headers: dict,
        optional_params: dict,
        request_data: dict,
        api_base: str,
        model: Optional[str] = None,
        stream: Optional[bool] = None,
        fake_stream: Optional[bool] = None,
    ) -> Tuple[dict, Optional[bytes]]:
        return self._sign_request(
            service_name="bedrock",
            headers=headers,
            optional_params=optional_params,
            request_data=request_data,
            api_base=api_base,
            model=model,
            stream=stream,
            fake_stream=fake_stream,
        )

    def _get_agent_id_and_alias_id(self, model: str) -> tuple[str, str]:
        """
        model = "agent/L1RT58GYRW/MFPSBCXYTW"
        agent_id = "L1RT58GYRW"
        agent_alias_id = "MFPSBCXYTW"
        """
        # Split the model string by '/' and extract components
        parts = model.split("/")
        if len(parts) != 3 or parts[0] != "agent":
            raise ValueError(
                "Invalid model format. Expected format: 'model=agent/AGENT_ID/ALIAS_ID'"
            )

        return parts[1], parts[2]  # Return (agent_id, agent_alias_id)

    def _get_session_id(self, optional_params: dict) -> str:
        """ """
        return optional_params.get("sessionID", None) or str(uuid.uuid4())

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        # use the last message content as the query
        query: str = convert_content_list_to_str(messages[-1])
        return {
            "inputText": query,
            "enableTrace": True,
            **optional_params,
        }

    def _parse_aws_event_stream(self, raw_content: bytes) -> InvokeAgentEventList:
        """
        Parse AWS event stream format using boto3/botocore's built-in parser.
        This is the same approach used in the existing AWSEventStreamDecoder.
        """
        try:
            from botocore.eventstream import EventStreamBuffer
            from botocore.parsers import EventStreamJSONParser
        except ImportError:
            raise ImportError("boto3/botocore is required for AWS event stream parsing")

        events: InvokeAgentEventList = []
        parser = EventStreamJSONParser()
        event_stream_buffer = EventStreamBuffer()

        # Add the entire response to the buffer
        event_stream_buffer.add_data(raw_content)

        # Process all events in the buffer
        for event in event_stream_buffer:
            try:
                headers = self._extract_headers_from_event(event)

                event_type = headers.get("event_type", "")

                if event_type == "chunk":
                    # Handle chunk events specially - they contain decoded content, not JSON
                    message = self._parse_message_from_event(event, parser)
                    parsed_event: InvokeAgentEvent = InvokeAgentEvent()
                    if message:
                        # For chunk events, create a payload with the decoded content
                        parsed_event = {
                            "headers": headers,
                            "payload": {
                                "bytes": base64.b64encode(
                                    message.encode("utf-8")
                                ).decode("utf-8")
                            },  # Re-encode for consistency
                        }
                        events.append(parsed_event)

                elif event_type == "trace":
                    # Handle trace events normally - they contain JSON
                    message = self._parse_message_from_event(event, parser)

                    if message:
                        try:
                            event_data = json.loads(message)
                            parsed_event = {
                                "headers": headers,
                                "payload": event_data,
                            }
                            events.append(parsed_event)
                        except json.JSONDecodeError as e:
                            verbose_logger.warning(
                                f"Failed to parse trace event JSON: {e}"
                            )
                else:
                    verbose_logger.debug(f"Unknown event type: {event_type}")

            except Exception as e:
                verbose_logger.error(f"Error processing event: {e}")
                continue

        return events

    def _parse_message_from_event(self, event, parser) -> Optional[str]:
        """Extract message content from an AWS event, adapted from AWSEventStreamDecoder."""
        try:
            response_dict = event.to_response_dict()
            verbose_logger.debug(f"Response dict: {response_dict}")

            # Use the same response shape parsing as the existing decoder
            parsed_response = parser.parse(
                response_dict, self._get_response_stream_shape()
            )
            verbose_logger.debug(f"Parsed response: {parsed_response}")

            if response_dict["status_code"] != 200:
                decoded_body = response_dict["body"].decode()
                if isinstance(decoded_body, dict):
                    error_message = decoded_body.get("message")
                elif isinstance(decoded_body, str):
                    error_message = decoded_body
                else:
                    error_message = ""
                exception_status = response_dict["headers"].get(":exception-type")
                error_message = exception_status + " " + error_message
                raise BedrockError(
                    status_code=response_dict["status_code"],
                    message=(
                        json.dumps(error_message)
                        if isinstance(error_message, dict)
                        else error_message
                    ),
                )

            if "chunk" in parsed_response:
                chunk = parsed_response.get("chunk")
                if not chunk:
                    return None
                return chunk.get("bytes").decode()
            else:
                chunk = response_dict.get("body")
                if not chunk:
                    return None
                return chunk.decode()

        except Exception as e:
            verbose_logger.debug(f"Error parsing message from event: {e}")
            return None

    def _extract_headers_from_event(self, event) -> InvokeAgentEventHeaders:
        """Extract headers from an AWS event for categorization."""
        try:
            response_dict = event.to_response_dict()
            headers = response_dict.get("headers", {})

            # Extract the event-type and content-type headers that we care about
            return InvokeAgentEventHeaders(
                event_type=headers.get(":event-type", ""),
                content_type=headers.get(":content-type", ""),
                message_type=headers.get(":message-type", ""),
            )
        except Exception as e:
            verbose_logger.debug(f"Error extracting headers: {e}")
            return InvokeAgentEventHeaders(
                event_type="", content_type="", message_type=""
            )

    def _get_response_stream_shape(self):
        """Get the response stream shape for parsing, reusing existing logic."""
        try:
            # Try to reuse the cached shape from the existing decoder
            from litellm.llms.bedrock.chat.invoke_handler import (
                get_response_stream_shape,
            )

            return get_response_stream_shape()
        except ImportError:
            # Fallback: create our own shape
            try:
                from botocore.loaders import Loader
                from botocore.model import ServiceModel

                loader = Loader()
                bedrock_service_dict = loader.load_service_model(
                    "bedrock-runtime", "service-2"
                )
                bedrock_service_model = ServiceModel(bedrock_service_dict)
                return bedrock_service_model.shape_for("ResponseStream")
            except Exception as e:
                verbose_logger.warning(f"Could not load response stream shape: {e}")
                return None

    def _extract_response_content(self, events: InvokeAgentEventList) -> str:
        """Extract the final response content from parsed events."""
        response_parts = []

        for event in events:
            headers = event.get("headers", {})
            payload = event.get("payload")

            event_type = headers.get(
                "event_type"
            )  # Note: using event_type not event-type

            if event_type == "chunk" and payload:
                # Extract base64 encoded content from chunk events
                chunk_payload: InvokeAgentChunkPayload = payload  # type: ignore
                encoded_bytes = chunk_payload.get("bytes", "")
                if encoded_bytes:
                    try:
                        decoded_content = base64.b64decode(encoded_bytes).decode(
                            "utf-8"
                        )
                        response_parts.append(decoded_content)
                    except Exception as e:
                        verbose_logger.warning(f"Failed to decode chunk content: {e}")

        return "".join(response_parts)

    def _extract_usage_info(self, events: InvokeAgentEventList) -> InvokeAgentUsage:
        """Extract token usage information from trace events."""
        usage_info = InvokeAgentUsage(
            inputTokens=0,
            outputTokens=0,
            model=None,
        )

        response_model: Optional[str] = None

        for event in events:
            if not self._is_trace_event(event):
                continue

            trace_data = self._get_trace_data(event)
            if not trace_data:
                continue

            verbose_logger.debug(f"Trace event: {trace_data}")

            # Extract usage from pre-processing trace
            self._extract_and_update_preprocessing_usage(
                trace_data=trace_data,
                usage_info=usage_info,
            )

            # Extract model from orchestration trace
            if response_model is None:
                response_model = self._extract_orchestration_model(trace_data)

        usage_info["model"] = response_model
        return usage_info

    def _is_trace_event(self, event: InvokeAgentEvent) -> bool:
        """Check if the event is a trace event."""
        headers = event.get("headers", {})
        event_type = headers.get("event_type")
        payload = event.get("payload")
        return event_type == "trace" and payload is not None

    def _get_trace_data(self, event: InvokeAgentEvent) -> Optional[InvokeAgentTrace]:
        """Extract trace data from a trace event."""
        payload = event.get("payload")
        if not payload:
            return None

        trace_payload: InvokeAgentTracePayload = payload  # type: ignore
        return trace_payload.get("trace", {})

    def _extract_and_update_preprocessing_usage(
        self, trace_data: InvokeAgentTrace, usage_info: InvokeAgentUsage
    ) -> None:
        """Extract usage information from preprocessing trace."""
        pre_processing = trace_data.get("preProcessingTrace", {})
        if not pre_processing:
            return

        model_output = pre_processing.get("modelInvocationOutput", {})
        if not model_output:
            return

        metadata = model_output.get("metadata", {})
        if not metadata:
            return

        usage: Optional[Union[InvokeAgentUsage, Dict]] = metadata.get("usage", {})
        if not usage:
            return

        usage_info["inputTokens"] += usage.get("inputTokens", 0)
        usage_info["outputTokens"] += usage.get("outputTokens", 0)

    def _extract_orchestration_model(
        self, trace_data: InvokeAgentTrace
    ) -> Optional[str]:
        """Extract model information from orchestration trace."""
        orchestration_trace = trace_data.get("orchestrationTrace", {})
        if not orchestration_trace:
            return None

        model_invocation = orchestration_trace.get("modelInvocationInput", {})
        if not model_invocation:
            return None

        return model_invocation.get("foundationModel")

    def _build_model_response(
        self,
        content: str,
        model: str,
        usage_info: InvokeAgentUsage,
        model_response: ModelResponse,
    ) -> ModelResponse:
        """Build the final ModelResponse object."""

        # Create the message content
        message = Message(content=content, role="assistant")

        # Create choices
        choice = Choices(finish_reason="stop", index=0, message=message)

        # Update model response
        model_response.choices = [choice]
        model_response.model = usage_info.get("model", model)

        # Add usage information if available
        if usage_info:
            from litellm.types.utils import Usage

            usage = Usage(
                prompt_tokens=usage_info.get("inputTokens", 0),
                completion_tokens=usage_info.get("outputTokens", 0),
                total_tokens=usage_info.get("inputTokens", 0)
                + usage_info.get("outputTokens", 0),
            )
            setattr(model_response, "usage", usage)

        return model_response

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        try:
            # Get the raw binary content
            raw_content = raw_response.content
            verbose_logger.debug(
                f"Processing {len(raw_content)} bytes of AWS event stream data"
            )

            # Parse the AWS event stream format
            events = self._parse_aws_event_stream(raw_content)
            verbose_logger.debug(f"Parsed {len(events)} events from stream")

            # Extract response content from chunk events
            content = self._extract_response_content(events)

            # Extract usage information from trace events
            usage_info = self._extract_usage_info(events)

            # Build and return the model response
            return self._build_model_response(
                content=content,
                model=model,
                usage_info=usage_info,
                model_response=model_response,
            )

        except Exception as e:
            verbose_logger.error(
                f"Error processing Bedrock Invoke Agent response: {str(e)}"
            )
            raise BedrockError(
                message=f"Error processing response: {str(e)}",
                status_code=raw_response.status_code,
            )

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        return headers

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return BedrockError(status_code=status_code, message=error_message)

    def should_fake_stream(
        self,
        model: Optional[str],
        stream: Optional[bool],
        custom_llm_provider: Optional[str] = None,
    ) -> bool:
        return True

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\backend_webagg_core.py ===
"""Displays Agg images in the browser, with interactivity."""
# The WebAgg backend is divided into two modules:
#
# - `backend_webagg_core.py` contains code necessary to embed a WebAgg
#   plot inside of a web application, and communicate in an abstract
#   way over a web socket.
#
# - `backend_webagg.py` contains a concrete implementation of a basic
#   application, implemented with asyncio.

import asyncio
import datetime
from io import BytesIO, StringIO
import json
import logging
import os
from pathlib import Path

import numpy as np
from PIL import Image

from matplotlib import _api, backend_bases, backend_tools
from matplotlib.backends import backend_agg
from matplotlib.backend_bases import (
    _Backend, MouseButton, KeyEvent, LocationEvent, MouseEvent, ResizeEvent)

_log = logging.getLogger(__name__)

_SPECIAL_KEYS_LUT = {'Alt': 'alt',
                     'AltGraph': 'alt',
                     'CapsLock': 'caps_lock',
                     'Control': 'control',
                     'Meta': 'meta',
                     'NumLock': 'num_lock',
                     'ScrollLock': 'scroll_lock',
                     'Shift': 'shift',
                     'Super': 'super',
                     'Enter': 'enter',
                     'Tab': 'tab',
                     'ArrowDown': 'down',
                     'ArrowLeft': 'left',
                     'ArrowRight': 'right',
                     'ArrowUp': 'up',
                     'End': 'end',
                     'Home': 'home',
                     'PageDown': 'pagedown',
                     'PageUp': 'pageup',
                     'Backspace': 'backspace',
                     'Delete': 'delete',
                     'Insert': 'insert',
                     'Escape': 'escape',
                     'Pause': 'pause',
                     'Select': 'select',
                     'Dead': 'dead',
                     'F1': 'f1',
                     'F2': 'f2',
                     'F3': 'f3',
                     'F4': 'f4',
                     'F5': 'f5',
                     'F6': 'f6',
                     'F7': 'f7',
                     'F8': 'f8',
                     'F9': 'f9',
                     'F10': 'f10',
                     'F11': 'f11',
                     'F12': 'f12'}


def _handle_key(key):
    """Handle key values"""
    value = key[key.index('k') + 1:]
    if 'shift+' in key:
        if len(value) == 1:
            key = key.replace('shift+', '')
    if value in _SPECIAL_KEYS_LUT:
        value = _SPECIAL_KEYS_LUT[value]
    key = key[:key.index('k')] + value
    return key


class TimerTornado(backend_bases.TimerBase):
    def __init__(self, *args, **kwargs):
        self._timer = None
        super().__init__(*args, **kwargs)

    def _timer_start(self):
        import tornado

        self._timer_stop()
        if self._single:
            ioloop = tornado.ioloop.IOLoop.instance()
            self._timer = ioloop.add_timeout(
                datetime.timedelta(milliseconds=self.interval),
                self._on_timer)
        else:
            self._timer = tornado.ioloop.PeriodicCallback(
                self._on_timer,
                max(self.interval, 1e-6))
            self._timer.start()

    def _timer_stop(self):
        import tornado

        if self._timer is None:
            return
        elif self._single:
            ioloop = tornado.ioloop.IOLoop.instance()
            ioloop.remove_timeout(self._timer)
        else:
            self._timer.stop()
        self._timer = None

    def _timer_set_interval(self):
        # Only stop and restart it if the timer has already been started
        if self._timer is not None:
            self._timer_stop()
            self._timer_start()


class TimerAsyncio(backend_bases.TimerBase):
    def __init__(self, *args, **kwargs):
        self._task = None
        super().__init__(*args, **kwargs)

    async def _timer_task(self, interval):
        while True:
            try:
                await asyncio.sleep(interval)
                self._on_timer()

                if self._single:
                    break
            except asyncio.CancelledError:
                break

    def _timer_start(self):
        self._timer_stop()

        self._task = asyncio.ensure_future(
            self._timer_task(max(self.interval / 1_000., 1e-6))
        )

    def _timer_stop(self):
        if self._task is not None:
            self._task.cancel()
        self._task = None

    def _timer_set_interval(self):
        # Only stop and restart it if the timer has already been started
        if self._task is not None:
            self._timer_stop()
            self._timer_start()


class FigureCanvasWebAggCore(backend_agg.FigureCanvasAgg):
    manager_class = _api.classproperty(lambda cls: FigureManagerWebAgg)
    _timer_cls = TimerAsyncio
    # Webagg and friends having the right methods, but still
    # having bugs in practice.  Do not advertise that it works until
    # we can debug this.
    supports_blit = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set to True when the renderer contains data that is newer
        # than the PNG buffer.
        self._png_is_old = True
        # Set to True by the `refresh` message so that the next frame
        # sent to the clients will be a full frame.
        self._force_full = True
        # The last buffer, for diff mode.
        self._last_buff = np.empty((0, 0))
        # Store the current image mode so that at any point, clients can
        # request the information. This should be changed by calling
        # self.set_image_mode(mode) so that the notification can be given
        # to the connected clients.
        self._current_image_mode = 'full'
        # Track mouse events to fill in the x, y position of key events.
        self._last_mouse_xy = (None, None)

    def show(self):
        # show the figure window
        from matplotlib.pyplot import show
        show()

    def draw(self):
        self._png_is_old = True
        try:
            super().draw()
        finally:
            self.manager.refresh_all()  # Swap the frames.

    def blit(self, bbox=None):
        self._png_is_old = True
        self.manager.refresh_all()

    def draw_idle(self):
        self.send_event("draw")

    def set_cursor(self, cursor):
        # docstring inherited
        cursor = _api.check_getitem({
            backend_tools.Cursors.HAND: 'pointer',
            backend_tools.Cursors.POINTER: 'default',
            backend_tools.Cursors.SELECT_REGION: 'crosshair',
            backend_tools.Cursors.MOVE: 'move',
            backend_tools.Cursors.WAIT: 'wait',
            backend_tools.Cursors.RESIZE_HORIZONTAL: 'ew-resize',
            backend_tools.Cursors.RESIZE_VERTICAL: 'ns-resize',
        }, cursor=cursor)
        self.send_event('cursor', cursor=cursor)

    def set_image_mode(self, mode):
        """
        Set the image mode for any subsequent images which will be sent
        to the clients. The modes may currently be either 'full' or 'diff'.

        Note: diff images may not contain transparency, therefore upon
        draw this mode may be changed if the resulting image has any
        transparent component.
        """
        _api.check_in_list(['full', 'diff'], mode=mode)
        if self._current_image_mode != mode:
            self._current_image_mode = mode
            self.handle_send_image_mode(None)

    def get_diff_image(self):
        if self._png_is_old:
            renderer = self.get_renderer()

            pixels = np.asarray(renderer.buffer_rgba())
            # The buffer is created as type uint32 so that entire
            # pixels can be compared in one numpy call, rather than
            # needing to compare each plane separately.
            buff = pixels.view(np.uint32).squeeze(2)

            if (self._force_full
                    # If the buffer has changed size we need to do a full draw.
                    or buff.shape != self._last_buff.shape
                    # If any pixels have transparency, we need to force a full
                    # draw as we cannot overlay new on top of old.
                    or (pixels[:, :, 3] != 255).any()):
                self.set_image_mode('full')
                output = buff
            else:
                self.set_image_mode('diff')
                diff = buff != self._last_buff
                output = np.where(diff, buff, 0)

            # Store the current buffer so we can compute the next diff.
            self._last_buff = buff.copy()
            self._force_full = False
            self._png_is_old = False

            data = output.view(dtype=np.uint8).reshape((*output.shape, 4))
            with BytesIO() as png:
                Image.fromarray(data).save(png, format="png")
                return png.getvalue()

    def handle_event(self, event):
        e_type = event['type']
        handler = getattr(self, f'handle_{e_type}',
                          self.handle_unknown_event)
        return handler(event)

    def handle_unknown_event(self, event):
        _log.warning('Unhandled message type %s. %s', event["type"], event)

    def handle_ack(self, event):
        # Network latency tends to decrease if traffic is flowing
        # in both directions.  Therefore, the browser sends back
        # an "ack" message after each image frame is received.
        # This could also be used as a simple sanity check in the
        # future, but for now the performance increase is enough
        # to justify it, even if the server does nothing with it.
        pass

    def handle_draw(self, event):
        self.draw()

    def _handle_mouse(self, event):
        x = event['x']
        y = event['y']
        y = self.get_renderer().height - y
        self._last_mouse_xy = x, y
        e_type = event['type']
        button = event['button'] + 1  # JS numbers off by 1 compared to mpl.
        buttons = {  # JS ordering different compared to mpl.
            button for button, mask in [
                (MouseButton.LEFT, 1),
                (MouseButton.RIGHT, 2),
                (MouseButton.MIDDLE, 4),
                (MouseButton.BACK, 8),
                (MouseButton.FORWARD, 16),
            ] if event['buttons'] & mask  # State *after* press/release.
        }
        modifiers = event['modifiers']
        guiEvent = event.get('guiEvent')
        if e_type in ['button_press', 'button_release']:
            MouseEvent(e_type + '_event', self, x, y, button,
                       modifiers=modifiers, guiEvent=guiEvent)._process()
        elif e_type == 'dblclick':
            MouseEvent('button_press_event', self, x, y, button, dblclick=True,
                       modifiers=modifiers, guiEvent=guiEvent)._process()
        elif e_type == 'scroll':
            MouseEvent('scroll_event', self, x, y, step=event['step'],
                       modifiers=modifiers, guiEvent=guiEvent)._process()
        elif e_type == 'motion_notify':
            MouseEvent(e_type + '_event', self, x, y,
                       buttons=buttons, modifiers=modifiers, guiEvent=guiEvent,
                       )._process()
        elif e_type in ['figure_enter', 'figure_leave']:
            LocationEvent(e_type + '_event', self, x, y,
                          modifiers=modifiers, guiEvent=guiEvent)._process()

    handle_button_press = handle_button_release = handle_dblclick = \
        handle_figure_enter = handle_figure_leave = handle_motion_notify = \
        handle_scroll = _handle_mouse

    def _handle_key(self, event):
        KeyEvent(event['type'] + '_event', self,
                 _handle_key(event['key']), *self._last_mouse_xy,
                 guiEvent=event.get('guiEvent'))._process()
    handle_key_press = handle_key_release = _handle_key

    def handle_toolbar_button(self, event):
        # TODO: Be more suspicious of the input
        getattr(self.toolbar, event['name'])()

    def handle_refresh(self, event):
        figure_label = self.figure.get_label()
        if not figure_label:
            figure_label = f"Figure {self.manager.num}"
        self.send_event('figure_label', label=figure_label)
        self._force_full = True
        if self.toolbar:
            # Normal toolbar init would refresh this, but it happens before the
            # browser canvas is set up.
            self.toolbar.set_history_buttons()
        self.draw_idle()

    def handle_resize(self, event):
        x = int(event.get('width', 800)) * self.device_pixel_ratio
        y = int(event.get('height', 800)) * self.device_pixel_ratio
        fig = self.figure
        # An attempt at approximating the figure size in pixels.
        fig.set_size_inches(x / fig.dpi, y / fig.dpi, forward=False)
        # Acknowledge the resize, and force the viewer to update the
        # canvas size to the figure's new size (which is hopefully
        # identical or within a pixel or so).
        self._png_is_old = True
        self.manager.resize(*fig.bbox.size, forward=False)
        ResizeEvent('resize_event', self)._process()
        self.draw_idle()

    def handle_send_image_mode(self, event):
        # The client requests notification of what the current image mode is.
        self.send_event('image_mode', mode=self._current_image_mode)

    def handle_set_device_pixel_ratio(self, event):
        self._handle_set_device_pixel_ratio(event.get('device_pixel_ratio', 1))

    def handle_set_dpi_ratio(self, event):
        # This handler is for backwards-compatibility with older ipympl.
        self._handle_set_device_pixel_ratio(event.get('dpi_ratio', 1))

    def _handle_set_device_pixel_ratio(self, device_pixel_ratio):
        if self._set_device_pixel_ratio(device_pixel_ratio):
            self._force_full = True
            self.draw_idle()

    def send_event(self, event_type, **kwargs):
        if self.manager:
            self.manager._send_event(event_type, **kwargs)


_ALLOWED_TOOL_ITEMS = {
    'home',
    'back',
    'forward',
    'pan',
    'zoom',
    'download',
    None,
}


class NavigationToolbar2WebAgg(backend_bases.NavigationToolbar2):

    # Use the standard toolbar items + download button
    toolitems = [
        (text, tooltip_text, image_file, name_of_method)
        for text, tooltip_text, image_file, name_of_method
        in (*backend_bases.NavigationToolbar2.toolitems,
            ('Download', 'Download plot', 'filesave', 'download'))
        if name_of_method in _ALLOWED_TOOL_ITEMS
    ]

    def __init__(self, canvas):
        self.message = ''
        super().__init__(canvas)

    def set_message(self, message):
        if message != self.message:
            self.canvas.send_event("message", message=message)
        self.message = message

    def draw_rubberband(self, event, x0, y0, x1, y1):
        self.canvas.send_event("rubberband", x0=x0, y0=y0, x1=x1, y1=y1)

    def remove_rubberband(self):
        self.canvas.send_event("rubberband", x0=-1, y0=-1, x1=-1, y1=-1)

    def save_figure(self, *args):
        """Save the current figure."""
        self.canvas.send_event('save')
        return self.UNKNOWN_SAVED_STATUS

    def pan(self):
        super().pan()
        self.canvas.send_event('navigate_mode', mode=self.mode.name)

    def zoom(self):
        super().zoom()
        self.canvas.send_event('navigate_mode', mode=self.mode.name)

    def set_history_buttons(self):
        can_backward = self._nav_stack._pos > 0
        can_forward = self._nav_stack._pos < len(self._nav_stack) - 1
        self.canvas.send_event('history_buttons',
                               Back=can_backward, Forward=can_forward)


class FigureManagerWebAgg(backend_bases.FigureManagerBase):
    # This must be None to not break ipympl
    _toolbar2_class = None
    ToolbarCls = NavigationToolbar2WebAgg
    _window_title = "Matplotlib"

    def __init__(self, canvas, num):
        self.web_sockets = set()
        super().__init__(canvas, num)

    def show(self):
        pass

    def resize(self, w, h, forward=True):
        self._send_event(
            'resize',
            size=(w / self.canvas.device_pixel_ratio,
                  h / self.canvas.device_pixel_ratio),
            forward=forward)

    def set_window_title(self, title):
        self._send_event('figure_label', label=title)
        self._window_title = title

    def get_window_title(self):
        return self._window_title

    # The following methods are specific to FigureManagerWebAgg

    def add_web_socket(self, web_socket):
        assert hasattr(web_socket, 'send_binary')
        assert hasattr(web_socket, 'send_json')
        self.web_sockets.add(web_socket)
        self.resize(*self.canvas.figure.bbox.size)
        self._send_event('refresh')

    def remove_web_socket(self, web_socket):
        self.web_sockets.remove(web_socket)

    def handle_json(self, content):
        self.canvas.handle_event(content)

    def refresh_all(self):
        if self.web_sockets:
            diff = self.canvas.get_diff_image()
            if diff is not None:
                for s in self.web_sockets:
                    s.send_binary(diff)

    @classmethod
    def get_javascript(cls, stream=None):
        if stream is None:
            output = StringIO()
        else:
            output = stream

        output.write((Path(__file__).parent / "web_backend/js/mpl.js")
                     .read_text(encoding="utf-8"))

        toolitems = []
        for name, tooltip, image, method in cls.ToolbarCls.toolitems:
            if name is None:
                toolitems.append(['', '', '', ''])
            else:
                toolitems.append([name, tooltip, image, method])
        output.write(f"mpl.toolbar_items = {json.dumps(toolitems)};\n\n")

        extensions = []
        for filetype, ext in sorted(FigureCanvasWebAggCore.
                                    get_supported_filetypes_grouped().
                                    items()):
            extensions.append(ext[0])
        output.write(f"mpl.extensions = {json.dumps(extensions)};\n\n")

        output.write("mpl.default_extension = {};".format(
            json.dumps(FigureCanvasWebAggCore.get_default_filetype())))

        if stream is None:
            return output.getvalue()

    @classmethod
    def get_static_file_path(cls):
        return os.path.join(os.path.dirname(__file__), 'web_backend')

    def _send_event(self, event_type, **kwargs):
        payload = {'type': event_type, **kwargs}
        for s in self.web_sockets:
            s.send_json(payload)


@_Backend.export
class _BackendWebAggCoreAgg(_Backend):
    FigureCanvas = FigureCanvasWebAggCore
    FigureManager = FigureManagerWebAgg

# === NexusCore/openenv\Lib\site-packages\matplotlib\testing\compare.py ===
"""
Utilities for comparing image results.
"""

import atexit
import functools
import hashlib
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory, TemporaryFile
import weakref
import re

import numpy as np
from PIL import Image

import matplotlib as mpl
from matplotlib import cbook
from matplotlib.testing.exceptions import ImageComparisonFailure

_log = logging.getLogger(__name__)

__all__ = ['calculate_rms', 'comparable_formats', 'compare_images']


def make_test_filename(fname, purpose):
    """
    Make a new filename by inserting *purpose* before the file's extension.
    """
    base, ext = os.path.splitext(fname)
    return f'{base}-{purpose}{ext}'


def _get_cache_path():
    cache_dir = Path(mpl.get_cachedir(), 'test_cache')
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cache_dir():
    return str(_get_cache_path())


def get_file_hash(path, block_size=2 ** 20):
    sha256 = hashlib.sha256(usedforsecurity=False)
    with open(path, 'rb') as fd:
        while True:
            data = fd.read(block_size)
            if not data:
                break
            sha256.update(data)

    if Path(path).suffix == '.pdf':
        sha256.update(str(mpl._get_executable_info("gs").version).encode('utf-8'))
    elif Path(path).suffix == '.svg':
        sha256.update(str(mpl._get_executable_info("inkscape").version).encode('utf-8'))

    return sha256.hexdigest()


class _ConverterError(Exception):
    pass


class _Converter:
    def __init__(self):
        self._proc = None
        # Explicitly register deletion from an atexit handler because if we
        # wait until the object is GC'd (which occurs later), then some module
        # globals (e.g. signal.SIGKILL) has already been set to None, and
        # kill() doesn't work anymore...
        atexit.register(self.__del__)

    def __del__(self):
        if self._proc:
            self._proc.kill()
            self._proc.wait()
            for stream in filter(None, [self._proc.stdin,
                                        self._proc.stdout,
                                        self._proc.stderr]):
                stream.close()
            self._proc = None

    def _read_until(self, terminator):
        """Read until the prompt is reached."""
        buf = bytearray()
        while True:
            c = self._proc.stdout.read(1)
            if not c:
                raise _ConverterError(os.fsdecode(bytes(buf)))
            buf.extend(c)
            if buf.endswith(terminator):
                return bytes(buf)


class _GSConverter(_Converter):
    def __call__(self, orig, dest):
        if not self._proc:
            self._proc = subprocess.Popen(
                [mpl._get_executable_info("gs").executable,
                 "-dNOSAFER", "-dNOPAUSE", "-dEPSCrop", "-sDEVICE=png16m"],
                # As far as I can see, ghostscript never outputs to stderr.
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            try:
                self._read_until(b"\nGS")
            except _ConverterError as e:
                raise OSError(f"Failed to start Ghostscript:\n\n{e.args[0]}") from None

        def encode_and_escape(name):
            return (os.fsencode(name)
                    .replace(b"\\", b"\\\\")
                    .replace(b"(", br"\(")
                    .replace(b")", br"\)"))

        self._proc.stdin.write(
            b"<< /OutputFile ("
            + encode_and_escape(dest)
            + b") >> setpagedevice ("
            + encode_and_escape(orig)
            + b") run flush\n")
        self._proc.stdin.flush()
        # GS> if nothing left on the stack; GS<n> if n items left on the stack.
        err = self._read_until((b"GS<", b"GS>"))
        stack = self._read_until(b">") if err.endswith(b"GS<") else b""
        if stack or not os.path.exists(dest):
            stack_size = int(stack[:-1]) if stack else 0
            self._proc.stdin.write(b"pop\n" * stack_size)
            # Using the systemencoding should at least get the filenames right.
            raise ImageComparisonFailure(
                (err + stack).decode(sys.getfilesystemencoding(), "replace"))


class _SVGConverter(_Converter):
    def __call__(self, orig, dest):
        old_inkscape = mpl._get_executable_info("inkscape").version.major < 1
        terminator = b"\n>" if old_inkscape else b"> "
        if not hasattr(self, "_tmpdir"):
            self._tmpdir = TemporaryDirectory()
            # On Windows, we must make sure that self._proc has terminated
            # (which __del__ does) before clearing _tmpdir.
            weakref.finalize(self._tmpdir, self.__del__)
        if (not self._proc  # First run.
                or self._proc.poll() is not None):  # Inkscape terminated.
            if self._proc is not None and self._proc.poll() is not None:
                for stream in filter(None, [self._proc.stdin,
                                            self._proc.stdout,
                                            self._proc.stderr]):
                    stream.close()
            env = {
                **os.environ,
                # If one passes e.g. a png file to Inkscape, it will try to
                # query the user for conversion options via a GUI (even with
                # `--without-gui`).  Unsetting `DISPLAY` prevents this (and
                # causes GTK to crash and Inkscape to terminate, but that'll
                # just be reported as a regular exception below).
                "DISPLAY": "",
                # Do not load any user options.
                "INKSCAPE_PROFILE_DIR": self._tmpdir.name,
            }
            # Old versions of Inkscape (e.g. 0.48.3.1) seem to sometimes
            # deadlock when stderr is redirected to a pipe, so we redirect it
            # to a temporary file instead.  This is not necessary anymore as of
            # Inkscape 0.92.1.
            stderr = TemporaryFile()
            self._proc = subprocess.Popen(
                ["inkscape", "--without-gui", "--shell"] if old_inkscape else
                ["inkscape", "--shell"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr,
                env=env, cwd=self._tmpdir.name)
            # Slight abuse, but makes shutdown handling easier.
            self._proc.stderr = stderr
            try:
                self._read_until(terminator)
            except _ConverterError as err:
                raise OSError(
                    "Failed to start Inkscape in interactive mode:\n\n"
                    + err.args[0]) from err

        # Inkscape's shell mode does not support escaping metacharacters in the
        # filename ("\n", and ":;" for inkscape>=1).  Avoid any problems by
        # running from a temporary directory and using fixed filenames.
        inkscape_orig = Path(self._tmpdir.name, os.fsdecode(b"f.svg"))
        inkscape_dest = Path(self._tmpdir.name, os.fsdecode(b"f.png"))
        try:
            inkscape_orig.symlink_to(Path(orig).resolve())
        except OSError:
            shutil.copyfile(orig, inkscape_orig)
        self._proc.stdin.write(
            b"f.svg --export-png=f.png\n" if old_inkscape else
            b"file-open:f.svg;export-filename:f.png;export-do;file-close\n")
        self._proc.stdin.flush()
        try:
            self._read_until(terminator)
        except _ConverterError as err:
            # Inkscape's output is not localized but gtk's is, so the output
            # stream probably has a mixed encoding.  Using the filesystem
            # encoding should at least get the filenames right...
            self._proc.stderr.seek(0)
            raise ImageComparisonFailure(
                self._proc.stderr.read().decode(
                    sys.getfilesystemencoding(), "replace")) from err
        os.remove(inkscape_orig)
        shutil.move(inkscape_dest, dest)

    def __del__(self):
        super().__del__()
        if hasattr(self, "_tmpdir"):
            self._tmpdir.cleanup()


class _SVGWithMatplotlibFontsConverter(_SVGConverter):
    """
    A SVG converter which explicitly adds the fonts shipped by Matplotlib to
    Inkspace's font search path, to better support `svg.fonttype = "none"`
    (which is in particular used by certain mathtext tests).
    """

    def __call__(self, orig, dest):
        if not hasattr(self, "_tmpdir"):
            self._tmpdir = TemporaryDirectory()
            shutil.copytree(cbook._get_data_path("fonts/ttf"),
                            Path(self._tmpdir.name, "fonts"))
        return super().__call__(orig, dest)


def _update_converter():
    try:
        mpl._get_executable_info("gs")
    except mpl.ExecutableNotFoundError:
        pass
    else:
        converter['pdf'] = converter['eps'] = _GSConverter()
    try:
        mpl._get_executable_info("inkscape")
    except mpl.ExecutableNotFoundError:
        pass
    else:
        converter['svg'] = _SVGConverter()


#: A dictionary that maps filename extensions to functions which themselves
#: convert between arguments `old` and `new` (filenames).
converter = {}
_update_converter()
_svg_with_matplotlib_fonts_converter = _SVGWithMatplotlibFontsConverter()


def comparable_formats():
    """
    Return the list of file formats that `.compare_images` can compare
    on this system.

    Returns
    -------
    list of str
        E.g. ``['png', 'pdf', 'svg', 'eps']``.

    """
    return ['png', *converter]


def convert(filename, cache):
    """
    Convert the named file to png; return the name of the created file.

    If *cache* is True, the result of the conversion is cached in
    `matplotlib.get_cachedir() + '/test_cache/'`.  The caching is based on a
    hash of the exact contents of the input file.  Old cache entries are
    automatically deleted as needed to keep the size of the cache capped to
    twice the size of all baseline images.
    """
    path = Path(filename)
    if not path.exists():
        raise OSError(f"{path} does not exist")
    if path.suffix[1:] not in converter:
        import pytest
        pytest.skip(f"Don't know how to convert {path.suffix} files to png")
    newpath = path.parent / f"{path.stem}_{path.suffix[1:]}.png"

    # Only convert the file if the destination doesn't already exist or
    # is out of date.
    if not newpath.exists() or newpath.stat().st_mtime < path.stat().st_mtime:
        cache_dir = _get_cache_path() if cache else None

        if cache_dir is not None:
            _register_conversion_cache_cleaner_once()
            hash_value = get_file_hash(path)
            cached_path = cache_dir / (hash_value + newpath.suffix)
            if cached_path.exists():
                _log.debug("For %s: reusing cached conversion.", filename)
                shutil.copyfile(cached_path, newpath)
                return str(newpath)

        _log.debug("For %s: converting to png.", filename)
        convert = converter[path.suffix[1:]]
        if path.suffix == ".svg":
            contents = path.read_text()
            # NOTE: This check should be kept in sync with font styling in
            # `lib/matplotlib/backends/backend_svg.py`. If it changes, then be sure to
            # re-generate any SVG test files using this mode, or else such tests will
            # fail to use the converter for the expected images (but will for the
            # results), and the tests will fail strangely.
            if re.search(
                # searches for attributes :
                #   style=[font|font-size|font-weight|
                #          font-family|font-variant|font-style]
                # taking care of the possibility of multiple style attributes
                # before the font styling (i.e. opacity)
                r'style="[^"]*font(|-size|-weight|-family|-variant|-style):',
                contents  # raw contents of the svg file
                    ):
                # for svg.fonttype = none, we explicitly patch the font search
                # path so that fonts shipped by Matplotlib are found.
                convert = _svg_with_matplotlib_fonts_converter
        convert(path, newpath)

        if cache_dir is not None:
            _log.debug("For %s: caching conversion result.", filename)
            shutil.copyfile(newpath, cached_path)

    return str(newpath)


def _clean_conversion_cache():
    # This will actually ignore mpl_toolkits baseline images, but they're
    # relatively small.
    baseline_images_size = sum(
        path.stat().st_size
        for path in Path(mpl.__file__).parent.glob("**/baseline_images/**/*"))
    # 2x: one full copy of baselines, and one full copy of test results
    # (actually an overestimate: we don't convert png baselines and results).
    max_cache_size = 2 * baseline_images_size
    # Reduce cache until it fits.
    with cbook._lock_path(_get_cache_path()):
        cache_stat = {
            path: path.stat() for path in _get_cache_path().glob("*")}
        cache_size = sum(stat.st_size for stat in cache_stat.values())
        paths_by_atime = sorted(  # Oldest at the end.
            cache_stat, key=lambda path: cache_stat[path].st_atime,
            reverse=True)
        while cache_size > max_cache_size:
            path = paths_by_atime.pop()
            cache_size -= cache_stat[path].st_size
            path.unlink()


@functools.cache  # Ensure this is only registered once.
def _register_conversion_cache_cleaner_once():
    atexit.register(_clean_conversion_cache)


def crop_to_same(actual_path, actual_image, expected_path, expected_image):
    # clip the images to the same size -- this is useful only when
    # comparing eps to pdf
    if actual_path[-7:-4] == 'eps' and expected_path[-7:-4] == 'pdf':
        aw, ah, ad = actual_image.shape
        ew, eh, ed = expected_image.shape
        actual_image = actual_image[int(aw / 2 - ew / 2):int(
            aw / 2 + ew / 2), int(ah / 2 - eh / 2):int(ah / 2 + eh / 2)]
    return actual_image, expected_image


def calculate_rms(expected_image, actual_image):
    """
    Calculate the per-pixel errors, then compute the root mean square error.
    """
    if expected_image.shape != actual_image.shape:
        raise ImageComparisonFailure(
            f"Image sizes do not match expected size: {expected_image.shape} "
            f"actual size {actual_image.shape}")
    # Convert to float to avoid overflowing finite integer types.
    return np.sqrt(((expected_image - actual_image).astype(float) ** 2).mean())


# NOTE: compare_image and save_diff_image assume that the image does not have
# 16-bit depth, as Pillow converts these to RGB incorrectly.


def _load_image(path):
    img = Image.open(path)
    # In an RGBA image, if the smallest value in the alpha channel is 255, all
    # values in it must be 255, meaning that the image is opaque. If so,
    # discard the alpha channel so that it may compare equal to an RGB image.
    if img.mode != "RGBA" or img.getextrema()[3][0] == 255:
        img = img.convert("RGB")
    return np.asarray(img)


def compare_images(expected, actual, tol, in_decorator=False):
    """
    Compare two "image" files checking differences within a tolerance.

    The two given filenames may point to files which are convertible to
    PNG via the `.converter` dictionary. The underlying RMS is calculated
    with the `.calculate_rms` function.

    Parameters
    ----------
    expected : str
        The filename of the expected image.
    actual : str
        The filename of the actual image.
    tol : float
        The tolerance (a color value difference, where 255 is the
        maximal difference).  The test fails if the average pixel
        difference is greater than this value.
    in_decorator : bool
        Determines the output format. If called from image_comparison
        decorator, this should be True. (default=False)

    Returns
    -------
    None or dict or str
        Return *None* if the images are equal within the given tolerance.

        If the images differ, the return value depends on  *in_decorator*.
        If *in_decorator* is true, a dict with the following entries is
        returned:

        - *rms*: The RMS of the image difference.
        - *expected*: The filename of the expected image.
        - *actual*: The filename of the actual image.
        - *diff_image*: The filename of the difference image.
        - *tol*: The comparison tolerance.

        Otherwise, a human-readable multi-line string representation of this
        information is returned.

    Examples
    --------
    ::

        img1 = "./baseline/plot.png"
        img2 = "./output/plot.png"
        compare_images(img1, img2, 0.001)

    """
    actual = os.fspath(actual)
    if not os.path.exists(actual):
        raise Exception(f"Output image {actual} does not exist.")
    if os.stat(actual).st_size == 0:
        raise Exception(f"Output image file {actual} is empty.")

    # Convert the image to png
    expected = os.fspath(expected)
    if not os.path.exists(expected):
        raise OSError(f'Baseline image {expected!r} does not exist.')
    extension = expected.split('.')[-1]
    if extension != 'png':
        actual = convert(actual, cache=True)
        expected = convert(expected, cache=True)

    # open the image files
    expected_image = _load_image(expected)
    actual_image = _load_image(actual)

    actual_image, expected_image = crop_to_same(
        actual, actual_image, expected, expected_image)

    diff_image = make_test_filename(actual, 'failed-diff')

    if tol <= 0:
        if np.array_equal(expected_image, actual_image):
            return None

    # convert to signed integers, so that the images can be subtracted without
    # overflow
    expected_image = expected_image.astype(np.int16)
    actual_image = actual_image.astype(np.int16)

    rms = calculate_rms(expected_image, actual_image)

    if rms <= tol:
        return None

    save_diff_image(expected, actual, diff_image)

    results = dict(rms=rms, expected=str(expected),
                   actual=str(actual), diff=str(diff_image), tol=tol)

    if not in_decorator:
        # Then the results should be a string suitable for stdout.
        template = ['Error: Image files did not match.',
                    'RMS Value: {rms}',
                    'Expected:  \n    {expected}',
                    'Actual:    \n    {actual}',
                    'Difference:\n    {diff}',
                    'Tolerance: \n    {tol}', ]
        results = '\n  '.join([line.format(**results) for line in template])
    return results


def save_diff_image(expected, actual, output):
    """
    Parameters
    ----------
    expected : str
        File path of expected image.
    actual : str
        File path of actual image.
    output : str
        File path to save difference image to.
    """
    expected_image = _load_image(expected)
    actual_image = _load_image(actual)
    actual_image, expected_image = crop_to_same(
        actual, actual_image, expected, expected_image)
    expected_image = np.array(expected_image, float)
    actual_image = np.array(actual_image, float)
    if expected_image.shape != actual_image.shape:
        raise ImageComparisonFailure(
            f"Image sizes do not match expected size: {expected_image.shape} "
            f"actual size {actual_image.shape}")
    abs_diff = np.abs(expected_image - actual_image)

    # expand differences in luminance domain
    abs_diff *= 10
    abs_diff = np.clip(abs_diff, 0, 255).astype(np.uint8)

    if abs_diff.shape[2] == 4:  # Hard-code the alpha channel to fully solid
        abs_diff[:, :, 3] = 255

    Image.fromarray(abs_diff).save(output, format="png")

# === NexusCore/openenv\Lib\site-packages\pip\_internal\vcs\git.py ===
import logging
import os.path
import pathlib
import re
import urllib.parse
import urllib.request
from dataclasses import replace
from typing import List, Optional, Tuple

from pip._internal.exceptions import BadCommand, InstallationError
from pip._internal.utils.misc import HiddenText, display_path, hide_url
from pip._internal.utils.subprocess import make_command
from pip._internal.vcs.versioncontrol import (
    AuthInfo,
    RemoteNotFoundError,
    RemoteNotValidError,
    RevOptions,
    VersionControl,
    find_path_to_project_root_from_repo_root,
    vcs,
)

urlsplit = urllib.parse.urlsplit
urlunsplit = urllib.parse.urlunsplit


logger = logging.getLogger(__name__)


GIT_VERSION_REGEX = re.compile(
    r"^git version "  # Prefix.
    r"(\d+)"  # Major.
    r"\.(\d+)"  # Dot, minor.
    r"(?:\.(\d+))?"  # Optional dot, patch.
    r".*$"  # Suffix, including any pre- and post-release segments we don't care about.
)

HASH_REGEX = re.compile("^[a-fA-F0-9]{40}$")

# SCP (Secure copy protocol) shorthand. e.g. 'git@example.com:foo/bar.git'
SCP_REGEX = re.compile(
    r"""^
    # Optional user, e.g. 'git@'
    (\w+@)?
    # Server, e.g. 'github.com'.
    ([^/:]+):
    # The server-side path. e.g. 'user/project.git'. Must start with an
    # alphanumeric character so as not to be confusable with a Windows paths
    # like 'C:/foo/bar' or 'C:\foo\bar'.
    (\w[^:]*)
    $""",
    re.VERBOSE,
)


def looks_like_hash(sha: str) -> bool:
    return bool(HASH_REGEX.match(sha))


class Git(VersionControl):
    name = "git"
    dirname = ".git"
    repo_name = "clone"
    schemes = (
        "git+http",
        "git+https",
        "git+ssh",
        "git+git",
        "git+file",
    )
    # Prevent the user's environment variables from interfering with pip:
    # https://github.com/pypa/pip/issues/1130
    unset_environ = ("GIT_DIR", "GIT_WORK_TREE")
    default_arg_rev = "HEAD"

    @staticmethod
    def get_base_rev_args(rev: str) -> List[str]:
        return [rev]

    def is_immutable_rev_checkout(self, url: str, dest: str) -> bool:
        _, rev_options = self.get_url_rev_options(hide_url(url))
        if not rev_options.rev:
            return False
        if not self.is_commit_id_equal(dest, rev_options.rev):
            # the current commit is different from rev,
            # which means rev was something else than a commit hash
            return False
        # return False in the rare case rev is both a commit hash
        # and a tag or a branch; we don't want to cache in that case
        # because that branch/tag could point to something else in the future
        is_tag_or_branch = bool(self.get_revision_sha(dest, rev_options.rev)[0])
        return not is_tag_or_branch

    def get_git_version(self) -> Tuple[int, ...]:
        version = self.run_command(
            ["version"],
            command_desc="git version",
            show_stdout=False,
            stdout_only=True,
        )
        match = GIT_VERSION_REGEX.match(version)
        if not match:
            logger.warning("Can't parse git version: %s", version)
            return ()
        return (int(match.group(1)), int(match.group(2)))

    @classmethod
    def get_current_branch(cls, location: str) -> Optional[str]:
        """
        Return the current branch, or None if HEAD isn't at a branch
        (e.g. detached HEAD).
        """
        # git-symbolic-ref exits with empty stdout if "HEAD" is a detached
        # HEAD rather than a symbolic ref.  In addition, the -q causes the
        # command to exit with status code 1 instead of 128 in this case
        # and to suppress the message to stderr.
        args = ["symbolic-ref", "-q", "HEAD"]
        output = cls.run_command(
            args,
            extra_ok_returncodes=(1,),
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        )
        ref = output.strip()

        if ref.startswith("refs/heads/"):
            return ref[len("refs/heads/") :]

        return None

    @classmethod
    def get_revision_sha(cls, dest: str, rev: str) -> Tuple[Optional[str], bool]:
        """
        Return (sha_or_none, is_branch), where sha_or_none is a commit hash
        if the revision names a remote branch or tag, otherwise None.

        Args:
          dest: the repository directory.
          rev: the revision name.
        """
        # Pass rev to pre-filter the list.
        output = cls.run_command(
            ["show-ref", rev],
            cwd=dest,
            show_stdout=False,
            stdout_only=True,
            on_returncode="ignore",
        )
        refs = {}
        # NOTE: We do not use splitlines here since that would split on other
        #       unicode separators, which can be maliciously used to install a
        #       different revision.
        for line in output.strip().split("\n"):
            line = line.rstrip("\r")
            if not line:
                continue
            try:
                ref_sha, ref_name = line.split(" ", maxsplit=2)
            except ValueError:
                # Include the offending line to simplify troubleshooting if
                # this error ever occurs.
                raise ValueError(f"unexpected show-ref line: {line!r}")

            refs[ref_name] = ref_sha

        branch_ref = f"refs/remotes/origin/{rev}"
        tag_ref = f"refs/tags/{rev}"

        sha = refs.get(branch_ref)
        if sha is not None:
            return (sha, True)

        sha = refs.get(tag_ref)

        return (sha, False)

    @classmethod
    def _should_fetch(cls, dest: str, rev: str) -> bool:
        """
        Return true if rev is a ref or is a commit that we don't have locally.

        Branches and tags are not considered in this method because they are
        assumed to be always available locally (which is a normal outcome of
        ``git clone`` and ``git fetch --tags``).
        """
        if rev.startswith("refs/"):
            # Always fetch remote refs.
            return True

        if not looks_like_hash(rev):
            # Git fetch would fail with abbreviated commits.
            return False

        if cls.has_commit(dest, rev):
            # Don't fetch if we have the commit locally.
            return False

        return True

    @classmethod
    def resolve_revision(
        cls, dest: str, url: HiddenText, rev_options: RevOptions
    ) -> RevOptions:
        """
        Resolve a revision to a new RevOptions object with the SHA1 of the
        branch, tag, or ref if found.

        Args:
          rev_options: a RevOptions object.
        """
        rev = rev_options.arg_rev
        # The arg_rev property's implementation for Git ensures that the
        # rev return value is always non-None.
        assert rev is not None

        sha, is_branch = cls.get_revision_sha(dest, rev)

        if sha is not None:
            rev_options = rev_options.make_new(sha)
            rev_options = replace(rev_options, branch_name=(rev if is_branch else None))

            return rev_options

        # Do not show a warning for the common case of something that has
        # the form of a Git commit hash.
        if not looks_like_hash(rev):
            logger.warning(
                "Did not find branch or tag '%s', assuming revision or ref.",
                rev,
            )

        if not cls._should_fetch(dest, rev):
            return rev_options

        # fetch the requested revision
        cls.run_command(
            make_command("fetch", "-q", url, rev_options.to_args()),
            cwd=dest,
        )
        # Change the revision to the SHA of the ref we fetched
        sha = cls.get_revision(dest, rev="FETCH_HEAD")
        rev_options = rev_options.make_new(sha)

        return rev_options

    @classmethod
    def is_commit_id_equal(cls, dest: str, name: Optional[str]) -> bool:
        """
        Return whether the current commit hash equals the given name.

        Args:
          dest: the repository directory.
          name: a string name.
        """
        if not name:
            # Then avoid an unnecessary subprocess call.
            return False

        return cls.get_revision(dest) == name

    def fetch_new(
        self, dest: str, url: HiddenText, rev_options: RevOptions, verbosity: int
    ) -> None:
        rev_display = rev_options.to_display()
        logger.info("Cloning %s%s to %s", url, rev_display, display_path(dest))
        if verbosity <= 0:
            flags: Tuple[str, ...] = ("--quiet",)
        elif verbosity == 1:
            flags = ()
        else:
            flags = ("--verbose", "--progress")
        if self.get_git_version() >= (2, 17):
            # Git added support for partial clone in 2.17
            # https://git-scm.com/docs/partial-clone
            # Speeds up cloning by functioning without a complete copy of repository
            self.run_command(
                make_command(
                    "clone",
                    "--filter=blob:none",
                    *flags,
                    url,
                    dest,
                )
            )
        else:
            self.run_command(make_command("clone", *flags, url, dest))

        if rev_options.rev:
            # Then a specific revision was requested.
            rev_options = self.resolve_revision(dest, url, rev_options)
            branch_name = getattr(rev_options, "branch_name", None)
            logger.debug("Rev options %s, branch_name %s", rev_options, branch_name)
            if branch_name is None:
                # Only do a checkout if the current commit id doesn't match
                # the requested revision.
                if not self.is_commit_id_equal(dest, rev_options.rev):
                    cmd_args = make_command(
                        "checkout",
                        "-q",
                        rev_options.to_args(),
                    )
                    self.run_command(cmd_args, cwd=dest)
            elif self.get_current_branch(dest) != branch_name:
                # Then a specific branch was requested, and that branch
                # is not yet checked out.
                track_branch = f"origin/{branch_name}"
                cmd_args = [
                    "checkout",
                    "-b",
                    branch_name,
                    "--track",
                    track_branch,
                ]
                self.run_command(cmd_args, cwd=dest)
        else:
            sha = self.get_revision(dest)
            rev_options = rev_options.make_new(sha)

        logger.info("Resolved %s to commit %s", url, rev_options.rev)

        #: repo may contain submodules
        self.update_submodules(dest)

    def switch(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        self.run_command(
            make_command("config", "remote.origin.url", url),
            cwd=dest,
        )
        cmd_args = make_command("checkout", "-q", rev_options.to_args())
        self.run_command(cmd_args, cwd=dest)

        self.update_submodules(dest)

    def update(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        # First fetch changes from the default remote
        if self.get_git_version() >= (1, 9):
            # fetch tags in addition to everything else
            self.run_command(["fetch", "-q", "--tags"], cwd=dest)
        else:
            self.run_command(["fetch", "-q"], cwd=dest)
        # Then reset to wanted revision (maybe even origin/master)
        rev_options = self.resolve_revision(dest, url, rev_options)
        cmd_args = make_command("reset", "--hard", "-q", rev_options.to_args())
        self.run_command(cmd_args, cwd=dest)
        #: update submodules
        self.update_submodules(dest)

    @classmethod
    def get_remote_url(cls, location: str) -> str:
        """
        Return URL of the first remote encountered.

        Raises RemoteNotFoundError if the repository does not have a remote
        url configured.
        """
        # We need to pass 1 for extra_ok_returncodes since the command
        # exits with return code 1 if there are no matching lines.
        stdout = cls.run_command(
            ["config", "--get-regexp", r"remote\..*\.url"],
            extra_ok_returncodes=(1,),
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        )
        remotes = stdout.splitlines()
        try:
            found_remote = remotes[0]
        except IndexError:
            raise RemoteNotFoundError

        for remote in remotes:
            if remote.startswith("remote.origin.url "):
                found_remote = remote
                break
        url = found_remote.split(" ")[1]
        return cls._git_remote_to_pip_url(url.strip())

    @staticmethod
    def _git_remote_to_pip_url(url: str) -> str:
        """
        Convert a remote url from what git uses to what pip accepts.

        There are 3 legal forms **url** may take:

            1. A fully qualified url: ssh://git@example.com/foo/bar.git
            2. A local project.git folder: /path/to/bare/repository.git
            3. SCP shorthand for form 1: git@example.com:foo/bar.git

        Form 1 is output as-is. Form 2 must be converted to URI and form 3 must
        be converted to form 1.

        See the corresponding test test_git_remote_url_to_pip() for examples of
        sample inputs/outputs.
        """
        if re.match(r"\w+://", url):
            # This is already valid. Pass it though as-is.
            return url
        if os.path.exists(url):
            # A local bare remote (git clone --mirror).
            # Needs a file:// prefix.
            return pathlib.PurePath(url).as_uri()
        scp_match = SCP_REGEX.match(url)
        if scp_match:
            # Add an ssh:// prefix and replace the ':' with a '/'.
            return scp_match.expand(r"ssh://\1\2/\3")
        # Otherwise, bail out.
        raise RemoteNotValidError(url)

    @classmethod
    def has_commit(cls, location: str, rev: str) -> bool:
        """
        Check if rev is a commit that is available in the local repository.
        """
        try:
            cls.run_command(
                ["rev-parse", "-q", "--verify", "sha^" + rev],
                cwd=location,
                log_failed_cmd=False,
            )
        except InstallationError:
            return False
        else:
            return True

    @classmethod
    def get_revision(cls, location: str, rev: Optional[str] = None) -> str:
        if rev is None:
            rev = "HEAD"
        current_rev = cls.run_command(
            ["rev-parse", rev],
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        )
        return current_rev.strip()

    @classmethod
    def get_subdirectory(cls, location: str) -> Optional[str]:
        """
        Return the path to Python project root, relative to the repo root.
        Return None if the project root is in the repo root.
        """
        # find the repo root
        git_dir = cls.run_command(
            ["rev-parse", "--git-dir"],
            show_stdout=False,
            stdout_only=True,
            cwd=location,
        ).strip()
        if not os.path.isabs(git_dir):
            git_dir = os.path.join(location, git_dir)
        repo_root = os.path.abspath(os.path.join(git_dir, ".."))
        return find_path_to_project_root_from_repo_root(location, repo_root)

    @classmethod
    def get_url_rev_and_auth(cls, url: str) -> Tuple[str, Optional[str], AuthInfo]:
        """
        Prefixes stub URLs like 'user@hostname:user/repo.git' with 'ssh://'.
        That's required because although they use SSH they sometimes don't
        work with a ssh:// scheme (e.g. GitHub). But we need a scheme for
        parsing. Hence we remove it again afterwards and return it as a stub.
        """
        # Works around an apparent Git bug
        # (see https://article.gmane.org/gmane.comp.version-control.git/146500)
        scheme, netloc, path, query, fragment = urlsplit(url)
        if scheme.endswith("file"):
            initial_slashes = path[: -len(path.lstrip("/"))]
            newpath = initial_slashes + urllib.request.url2pathname(path).replace(
                "\\", "/"
            ).lstrip("/")
            after_plus = scheme.find("+") + 1
            url = scheme[:after_plus] + urlunsplit(
                (scheme[after_plus:], netloc, newpath, query, fragment),
            )

        if "://" not in url:
            assert "file:" not in url
            url = url.replace("git+", "git+ssh://")
            url, rev, user_pass = super().get_url_rev_and_auth(url)
            url = url.replace("ssh://", "")
        else:
            url, rev, user_pass = super().get_url_rev_and_auth(url)

        return url, rev, user_pass

    @classmethod
    def update_submodules(cls, location: str) -> None:
        if not os.path.exists(os.path.join(location, ".gitmodules")):
            return
        cls.run_command(
            ["submodule", "update", "--init", "--recursive", "-q"],
            cwd=location,
        )

    @classmethod
    def get_repository_root(cls, location: str) -> Optional[str]:
        loc = super().get_repository_root(location)
        if loc:
            return loc
        try:
            r = cls.run_command(
                ["rev-parse", "--show-toplevel"],
                cwd=location,
                show_stdout=False,
                stdout_only=True,
                on_returncode="raise",
                log_failed_cmd=False,
            )
        except BadCommand:
            logger.debug(
                "could not determine if %s is under git control "
                "because git is not available",
                location,
            )
            return None
        except InstallationError:
            return None
        return os.path.normpath(r.rstrip("\r\n"))

    @staticmethod
    def should_add_vcs_url_prefix(repo_url: str) -> bool:
        """In either https or ssh form, requirements must be prefixed with git+."""
        return True


vcs.register(Git)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\gdi32.py ===
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2014, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Wrapper for gdi32.dll in ctypes.
"""

__revision__ = "$Id$"

from winappdbg.win32.defines import *
from winappdbg.win32.kernel32 import GetLastError, SetLastError

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================

# --- Helpers ------------------------------------------------------------------

# --- Types --------------------------------------------------------------------

# --- Constants ----------------------------------------------------------------

# GDI object types
OBJ_PEN = 1
OBJ_BRUSH = 2
OBJ_DC = 3
OBJ_METADC = 4
OBJ_PAL = 5
OBJ_FONT = 6
OBJ_BITMAP = 7
OBJ_REGION = 8
OBJ_METAFILE = 9
OBJ_MEMDC = 10
OBJ_EXTPEN = 11
OBJ_ENHMETADC = 12
OBJ_ENHMETAFILE = 13
OBJ_COLORSPACE = 14
GDI_OBJ_LAST = OBJ_COLORSPACE

# Ternary raster operations
SRCCOPY = 0x00CC0020  # dest = source
SRCPAINT = 0x00EE0086  # dest = source OR dest
SRCAND = 0x008800C6  # dest = source AND dest
SRCINVERT = 0x00660046  # dest = source XOR dest
SRCERASE = 0x00440328  # dest = source AND (NOT dest)
NOTSRCCOPY = 0x00330008  # dest = (NOT source)
NOTSRCERASE = 0x001100A6  # dest = (NOT src) AND (NOT dest)
MERGECOPY = 0x00C000CA  # dest = (source AND pattern)
MERGEPAINT = 0x00BB0226  # dest = (NOT source) OR dest
PATCOPY = 0x00F00021  # dest = pattern
PATPAINT = 0x00FB0A09  # dest = DPSnoo
PATINVERT = 0x005A0049  # dest = pattern XOR dest
DSTINVERT = 0x00550009  # dest = (NOT dest)
BLACKNESS = 0x00000042  # dest = BLACK
WHITENESS = 0x00FF0062  # dest = WHITE
NOMIRRORBITMAP = 0x80000000  # Do not Mirror the bitmap in this call
CAPTUREBLT = 0x40000000  # Include layered windows

# Region flags
ERROR = 0
NULLREGION = 1
SIMPLEREGION = 2
COMPLEXREGION = 3
RGN_ERROR = ERROR

# CombineRgn() styles
RGN_AND = 1
RGN_OR = 2
RGN_XOR = 3
RGN_DIFF = 4
RGN_COPY = 5
RGN_MIN = RGN_AND
RGN_MAX = RGN_COPY

# StretchBlt() modes
BLACKONWHITE = 1
WHITEONBLACK = 2
COLORONCOLOR = 3
HALFTONE = 4
MAXSTRETCHBLTMODE = 4
STRETCH_ANDSCANS = BLACKONWHITE
STRETCH_ORSCANS = WHITEONBLACK
STRETCH_DELETESCANS = COLORONCOLOR
STRETCH_HALFTONE = HALFTONE

# PolyFill() modes
ALTERNATE = 1
WINDING = 2
POLYFILL_LAST = 2

# Layout orientation options
LAYOUT_RTL = 0x00000001  # Right to left
LAYOUT_BTT = 0x00000002  # Bottom to top
LAYOUT_VBH = 0x00000004  # Vertical before horizontal
LAYOUT_ORIENTATIONMASK = LAYOUT_RTL + LAYOUT_BTT + LAYOUT_VBH
LAYOUT_BITMAPORIENTATIONPRESERVED = 0x00000008

# Stock objects
WHITE_BRUSH = 0
LTGRAY_BRUSH = 1
GRAY_BRUSH = 2
DKGRAY_BRUSH = 3
BLACK_BRUSH = 4
NULL_BRUSH = 5
HOLLOW_BRUSH = NULL_BRUSH
WHITE_PEN = 6
BLACK_PEN = 7
NULL_PEN = 8
OEM_FIXED_FONT = 10
ANSI_FIXED_FONT = 11
ANSI_VAR_FONT = 12
SYSTEM_FONT = 13
DEVICE_DEFAULT_FONT = 14
DEFAULT_PALETTE = 15
SYSTEM_FIXED_FONT = 16

# Metafile functions
META_SETBKCOLOR = 0x0201
META_SETBKMODE = 0x0102
META_SETMAPMODE = 0x0103
META_SETROP2 = 0x0104
META_SETRELABS = 0x0105
META_SETPOLYFILLMODE = 0x0106
META_SETSTRETCHBLTMODE = 0x0107
META_SETTEXTCHAREXTRA = 0x0108
META_SETTEXTCOLOR = 0x0209
META_SETTEXTJUSTIFICATION = 0x020A
META_SETWINDOWORG = 0x020B
META_SETWINDOWEXT = 0x020C
META_SETVIEWPORTORG = 0x020D
META_SETVIEWPORTEXT = 0x020E
META_OFFSETWINDOWORG = 0x020F
META_SCALEWINDOWEXT = 0x0410
META_OFFSETVIEWPORTORG = 0x0211
META_SCALEVIEWPORTEXT = 0x0412
META_LINETO = 0x0213
META_MOVETO = 0x0214
META_EXCLUDECLIPRECT = 0x0415
META_INTERSECTCLIPRECT = 0x0416
META_ARC = 0x0817
META_ELLIPSE = 0x0418
META_FLOODFILL = 0x0419
META_PIE = 0x081A
META_RECTANGLE = 0x041B
META_ROUNDRECT = 0x061C
META_PATBLT = 0x061D
META_SAVEDC = 0x001E
META_SETPIXEL = 0x041F
META_OFFSETCLIPRGN = 0x0220
META_TEXTOUT = 0x0521
META_BITBLT = 0x0922
META_STRETCHBLT = 0x0B23
META_POLYGON = 0x0324
META_POLYLINE = 0x0325
META_ESCAPE = 0x0626
META_RESTOREDC = 0x0127
META_FILLREGION = 0x0228
META_FRAMEREGION = 0x0429
META_INVERTREGION = 0x012A
META_PAINTREGION = 0x012B
META_SELECTCLIPREGION = 0x012C
META_SELECTOBJECT = 0x012D
META_SETTEXTALIGN = 0x012E
META_CHORD = 0x0830
META_SETMAPPERFLAGS = 0x0231
META_EXTTEXTOUT = 0x0A32
META_SETDIBTODEV = 0x0D33
META_SELECTPALETTE = 0x0234
META_REALIZEPALETTE = 0x0035
META_ANIMATEPALETTE = 0x0436
META_SETPALENTRIES = 0x0037
META_POLYPOLYGON = 0x0538
META_RESIZEPALETTE = 0x0139
META_DIBBITBLT = 0x0940
META_DIBSTRETCHBLT = 0x0B41
META_DIBCREATEPATTERNBRUSH = 0x0142
META_STRETCHDIB = 0x0F43
META_EXTFLOODFILL = 0x0548
META_SETLAYOUT = 0x0149
META_DELETEOBJECT = 0x01F0
META_CREATEPALETTE = 0x00F7
META_CREATEPATTERNBRUSH = 0x01F9
META_CREATEPENINDIRECT = 0x02FA
META_CREATEFONTINDIRECT = 0x02FB
META_CREATEBRUSHINDIRECT = 0x02FC
META_CREATEREGION = 0x06FF

# Metafile escape codes
NEWFRAME = 1
ABORTDOC = 2
NEXTBAND = 3
SETCOLORTABLE = 4
GETCOLORTABLE = 5
FLUSHOUTPUT = 6
DRAFTMODE = 7
QUERYESCSUPPORT = 8
SETABORTPROC = 9
STARTDOC = 10
ENDDOC = 11
GETPHYSPAGESIZE = 12
GETPRINTINGOFFSET = 13
GETSCALINGFACTOR = 14
MFCOMMENT = 15
GETPENWIDTH = 16
SETCOPYCOUNT = 17
SELECTPAPERSOURCE = 18
DEVICEDATA = 19
PASSTHROUGH = 19
GETTECHNOLGY = 20
GETTECHNOLOGY = 20
SETLINECAP = 21
SETLINEJOIN = 22
SETMITERLIMIT = 23
BANDINFO = 24
DRAWPATTERNRECT = 25
GETVECTORPENSIZE = 26
GETVECTORBRUSHSIZE = 27
ENABLEDUPLEX = 28
GETSETPAPERBINS = 29
GETSETPRINTORIENT = 30
ENUMPAPERBINS = 31
SETDIBSCALING = 32
EPSPRINTING = 33
ENUMPAPERMETRICS = 34
GETSETPAPERMETRICS = 35
POSTSCRIPT_DATA = 37
POSTSCRIPT_IGNORE = 38
MOUSETRAILS = 39
GETDEVICEUNITS = 42
GETEXTENDEDTEXTMETRICS = 256
GETEXTENTTABLE = 257
GETPAIRKERNTABLE = 258
GETTRACKKERNTABLE = 259
EXTTEXTOUT = 512
GETFACENAME = 513
DOWNLOADFACE = 514
ENABLERELATIVEWIDTHS = 768
ENABLEPAIRKERNING = 769
SETKERNTRACK = 770
SETALLJUSTVALUES = 771
SETCHARSET = 772
STRETCHBLT = 2048
METAFILE_DRIVER = 2049
GETSETSCREENPARAMS = 3072
QUERYDIBSUPPORT = 3073
BEGIN_PATH = 4096
CLIP_TO_PATH = 4097
END_PATH = 4098
EXT_DEVICE_CAPS = 4099
RESTORE_CTM = 4100
SAVE_CTM = 4101
SET_ARC_DIRECTION = 4102
SET_BACKGROUND_COLOR = 4103
SET_POLY_MODE = 4104
SET_SCREEN_ANGLE = 4105
SET_SPREAD = 4106
TRANSFORM_CTM = 4107
SET_CLIP_BOX = 4108
SET_BOUNDS = 4109
SET_MIRROR_MODE = 4110
OPENCHANNEL = 4110
DOWNLOADHEADER = 4111
CLOSECHANNEL = 4112
POSTSCRIPT_PASSTHROUGH = 4115
ENCAPSULATED_POSTSCRIPT = 4116
POSTSCRIPT_IDENTIFY = 4117
POSTSCRIPT_INJECTION = 4118
CHECKJPEGFORMAT = 4119
CHECKPNGFORMAT = 4120
GET_PS_FEATURESETTING = 4121
GDIPLUS_TS_QUERYVER = 4122
GDIPLUS_TS_RECORD = 4123
SPCLPASSTHROUGH2 = 4568

# --- Structures ---------------------------------------------------------------


# typedef struct _RECT {
#   LONG left;
#   LONG top;
#   LONG right;
#   LONG bottom;
# }RECT, *PRECT;
class RECT(Structure):
    _fields_ = [
        ("left", LONG),
        ("top", LONG),
        ("right", LONG),
        ("bottom", LONG),
    ]


PRECT = POINTER(RECT)
LPRECT = PRECT


# typedef struct tagPOINT {
#   LONG x;
#   LONG y;
# } POINT;
class POINT(Structure):
    _fields_ = [
        ("x", LONG),
        ("y", LONG),
    ]


PPOINT = POINTER(POINT)
LPPOINT = PPOINT


# typedef struct tagBITMAP {
#   LONG   bmType;
#   LONG   bmWidth;
#   LONG   bmHeight;
#   LONG   bmWidthBytes;
#   WORD   bmPlanes;
#   WORD   bmBitsPixel;
#   LPVOID bmBits;
# } BITMAP, *PBITMAP;
class BITMAP(Structure):
    _fields_ = [
        ("bmType", LONG),
        ("bmWidth", LONG),
        ("bmHeight", LONG),
        ("bmWidthBytes", LONG),
        ("bmPlanes", WORD),
        ("bmBitsPixel", WORD),
        ("bmBits", LPVOID),
    ]


PBITMAP = POINTER(BITMAP)
LPBITMAP = PBITMAP

# --- High level classes -------------------------------------------------------

# --- gdi32.dll ----------------------------------------------------------------


# HDC GetDC(
#   __in  HWND hWnd
# );
def GetDC(hWnd):
    _GetDC = windll.gdi32.GetDC
    _GetDC.argtypes = [HWND]
    _GetDC.restype = HDC
    _GetDC.errcheck = RaiseIfZero
    return _GetDC(hWnd)


# HDC GetWindowDC(
#   __in  HWND hWnd
# );
def GetWindowDC(hWnd):
    _GetWindowDC = windll.gdi32.GetWindowDC
    _GetWindowDC.argtypes = [HWND]
    _GetWindowDC.restype = HDC
    _GetWindowDC.errcheck = RaiseIfZero
    return _GetWindowDC(hWnd)


# int ReleaseDC(
#   __in  HWND hWnd,
#   __in  HDC hDC
# );
def ReleaseDC(hWnd, hDC):
    _ReleaseDC = windll.gdi32.ReleaseDC
    _ReleaseDC.argtypes = [HWND, HDC]
    _ReleaseDC.restype = ctypes.c_int
    _ReleaseDC.errcheck = RaiseIfZero
    _ReleaseDC(hWnd, hDC)


# HGDIOBJ SelectObject(
#   __in  HDC hdc,
#   __in  HGDIOBJ hgdiobj
# );
def SelectObject(hdc, hgdiobj):
    _SelectObject = windll.gdi32.SelectObject
    _SelectObject.argtypes = [HDC, HGDIOBJ]
    _SelectObject.restype = HGDIOBJ
    _SelectObject.errcheck = RaiseIfZero
    return _SelectObject(hdc, hgdiobj)


# HGDIOBJ GetStockObject(
#   __in  int fnObject
# );
def GetStockObject(fnObject):
    _GetStockObject = windll.gdi32.GetStockObject
    _GetStockObject.argtypes = [ctypes.c_int]
    _GetStockObject.restype = HGDIOBJ
    _GetStockObject.errcheck = RaiseIfZero
    return _GetStockObject(fnObject)


# DWORD GetObjectType(
#   __in  HGDIOBJ h
# );
def GetObjectType(h):
    _GetObjectType = windll.gdi32.GetObjectType
    _GetObjectType.argtypes = [HGDIOBJ]
    _GetObjectType.restype = DWORD
    _GetObjectType.errcheck = RaiseIfZero
    return _GetObjectType(h)


# int GetObject(
#   __in   HGDIOBJ hgdiobj,
#   __in   int cbBuffer,
#   __out  LPVOID lpvObject
# );
def GetObject(hgdiobj, cbBuffer=None, lpvObject=None):
    _GetObject = windll.gdi32.GetObject
    _GetObject.argtypes = [HGDIOBJ, ctypes.c_int, LPVOID]
    _GetObject.restype = ctypes.c_int
    _GetObject.errcheck = RaiseIfZero

    # Both cbBuffer and lpvObject can be omitted, the correct
    # size and structure to return are automatically deduced.
    # If lpvObject is given it must be a ctypes object, not a pointer.
    # Always returns a ctypes object.

    if cbBuffer is not None:
        if lpvObject is None:
            lpvObject = ctypes.create_string_buffer("", cbBuffer)
    elif lpvObject is not None:
        cbBuffer = sizeof(lpvObject)
    else:  # most likely case, both are None
        t = GetObjectType(hgdiobj)
        if t == OBJ_PEN:
            cbBuffer = sizeof(LOGPEN)
            lpvObject = LOGPEN()
        elif t == OBJ_BRUSH:
            cbBuffer = sizeof(LOGBRUSH)
            lpvObject = LOGBRUSH()
        elif t == OBJ_PAL:
            cbBuffer = _GetObject(hgdiobj, 0, None)
            lpvObject = (WORD * (cbBuffer // sizeof(WORD)))()
        elif t == OBJ_FONT:
            cbBuffer = sizeof(LOGFONT)
            lpvObject = LOGFONT()
        elif t == OBJ_BITMAP:  # try the two possible types of bitmap
            cbBuffer = sizeof(DIBSECTION)
            lpvObject = DIBSECTION()
            try:
                _GetObject(hgdiobj, cbBuffer, byref(lpvObject))
                return lpvObject
            except WindowsError:
                cbBuffer = sizeof(BITMAP)
                lpvObject = BITMAP()
        elif t == OBJ_EXTPEN:
            cbBuffer = sizeof(LOGEXTPEN)
            lpvObject = LOGEXTPEN()
        else:
            cbBuffer = _GetObject(hgdiobj, 0, None)
            lpvObject = ctypes.create_string_buffer("", cbBuffer)
    _GetObject(hgdiobj, cbBuffer, byref(lpvObject))
    return lpvObject


# LONG GetBitmapBits(
#   __in   HBITMAP hbmp,
#   __in   LONG cbBuffer,
#   __out  LPVOID lpvBits
# );
def GetBitmapBits(hbmp):
    _GetBitmapBits = windll.gdi32.GetBitmapBits
    _GetBitmapBits.argtypes = [HBITMAP, LONG, LPVOID]
    _GetBitmapBits.restype = LONG
    _GetBitmapBits.errcheck = RaiseIfZero

    bitmap = GetObject(hbmp, lpvObject=BITMAP())
    cbBuffer = bitmap.bmWidthBytes * bitmap.bmHeight
    lpvBits = ctypes.create_string_buffer("", cbBuffer)
    _GetBitmapBits(hbmp, cbBuffer, byref(lpvBits))
    return lpvBits.raw


# HBITMAP CreateBitmapIndirect(
#   __in  const BITMAP *lpbm
# );
def CreateBitmapIndirect(lpbm):
    _CreateBitmapIndirect = windll.gdi32.CreateBitmapIndirect
    _CreateBitmapIndirect.argtypes = [PBITMAP]
    _CreateBitmapIndirect.restype = HBITMAP
    _CreateBitmapIndirect.errcheck = RaiseIfZero
    return _CreateBitmapIndirect(lpbm)


# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================