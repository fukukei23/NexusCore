
# === NexusCore/openenv\Lib\site-packages\dateutil\rrule.py ===
# -*- coding: utf-8 -*-
"""
The rrule module offers a small, complete, and very fast, implementation of
the recurrence rules documented in the
`iCalendar RFC <https://tools.ietf.org/html/rfc5545>`_,
including support for caching of results.
"""
import calendar
import datetime
import heapq
import itertools
import re
import sys
from functools import wraps
# For warning about deprecation of until and count
from warnings import warn

from six import advance_iterator, integer_types

from six.moves import _thread, range

from ._common import weekday as weekdaybase

try:
    from math import gcd
except ImportError:
    from fractions import gcd

__all__ = ["rrule", "rruleset", "rrulestr",
           "YEARLY", "MONTHLY", "WEEKLY", "DAILY",
           "HOURLY", "MINUTELY", "SECONDLY",
           "MO", "TU", "WE", "TH", "FR", "SA", "SU"]

# Every mask is 7 days longer to handle cross-year weekly periods.
M366MASK = tuple([1]*31+[2]*29+[3]*31+[4]*30+[5]*31+[6]*30 +
                 [7]*31+[8]*31+[9]*30+[10]*31+[11]*30+[12]*31+[1]*7)
M365MASK = list(M366MASK)
M29, M30, M31 = list(range(1, 30)), list(range(1, 31)), list(range(1, 32))
MDAY366MASK = tuple(M31+M29+M31+M30+M31+M30+M31+M31+M30+M31+M30+M31+M31[:7])
MDAY365MASK = list(MDAY366MASK)
M29, M30, M31 = list(range(-29, 0)), list(range(-30, 0)), list(range(-31, 0))
NMDAY366MASK = tuple(M31+M29+M31+M30+M31+M30+M31+M31+M30+M31+M30+M31+M31[:7])
NMDAY365MASK = list(NMDAY366MASK)
M366RANGE = (0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366)
M365RANGE = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365)
WDAYMASK = [0, 1, 2, 3, 4, 5, 6]*55
del M29, M30, M31, M365MASK[59], MDAY365MASK[59], NMDAY365MASK[31]
MDAY365MASK = tuple(MDAY365MASK)
M365MASK = tuple(M365MASK)

FREQNAMES = ['YEARLY', 'MONTHLY', 'WEEKLY', 'DAILY', 'HOURLY', 'MINUTELY', 'SECONDLY']

(YEARLY,
 MONTHLY,
 WEEKLY,
 DAILY,
 HOURLY,
 MINUTELY,
 SECONDLY) = list(range(7))

# Imported on demand.
easter = None
parser = None


class weekday(weekdaybase):
    """
    This version of weekday does not allow n = 0.
    """
    def __init__(self, wkday, n=None):
        if n == 0:
            raise ValueError("Can't create weekday with n==0")

        super(weekday, self).__init__(wkday, n)


MO, TU, WE, TH, FR, SA, SU = weekdays = tuple(weekday(x) for x in range(7))


def _invalidates_cache(f):
    """
    Decorator for rruleset methods which may invalidate the
    cached length.
    """
    @wraps(f)
    def inner_func(self, *args, **kwargs):
        rv = f(self, *args, **kwargs)
        self._invalidate_cache()
        return rv

    return inner_func


class rrulebase(object):
    def __init__(self, cache=False):
        if cache:
            self._cache = []
            self._cache_lock = _thread.allocate_lock()
            self._invalidate_cache()
        else:
            self._cache = None
            self._cache_complete = False
            self._len = None

    def __iter__(self):
        if self._cache_complete:
            return iter(self._cache)
        elif self._cache is None:
            return self._iter()
        else:
            return self._iter_cached()

    def _invalidate_cache(self):
        if self._cache is not None:
            self._cache = []
            self._cache_complete = False
            self._cache_gen = self._iter()

            if self._cache_lock.locked():
                self._cache_lock.release()

        self._len = None

    def _iter_cached(self):
        i = 0
        gen = self._cache_gen
        cache = self._cache
        acquire = self._cache_lock.acquire
        release = self._cache_lock.release
        while gen:
            if i == len(cache):
                acquire()
                if self._cache_complete:
                    break
                try:
                    for j in range(10):
                        cache.append(advance_iterator(gen))
                except StopIteration:
                    self._cache_gen = gen = None
                    self._cache_complete = True
                    break
                release()
            yield cache[i]
            i += 1
        while i < self._len:
            yield cache[i]
            i += 1

    def __getitem__(self, item):
        if self._cache_complete:
            return self._cache[item]
        elif isinstance(item, slice):
            if item.step and item.step < 0:
                return list(iter(self))[item]
            else:
                return list(itertools.islice(self,
                                             item.start or 0,
                                             item.stop or sys.maxsize,
                                             item.step or 1))
        elif item >= 0:
            gen = iter(self)
            try:
                for i in range(item+1):
                    res = advance_iterator(gen)
            except StopIteration:
                raise IndexError
            return res
        else:
            return list(iter(self))[item]

    def __contains__(self, item):
        if self._cache_complete:
            return item in self._cache
        else:
            for i in self:
                if i == item:
                    return True
                elif i > item:
                    return False
        return False

    # __len__() introduces a large performance penalty.
    def count(self):
        """ Returns the number of recurrences in this set. It will have go
            through the whole recurrence, if this hasn't been done before. """
        if self._len is None:
            for x in self:
                pass
        return self._len

    def before(self, dt, inc=False):
        """ Returns the last recurrence before the given datetime instance. The
            inc keyword defines what happens if dt is an occurrence. With
            inc=True, if dt itself is an occurrence, it will be returned. """
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        last = None
        if inc:
            for i in gen:
                if i > dt:
                    break
                last = i
        else:
            for i in gen:
                if i >= dt:
                    break
                last = i
        return last

    def after(self, dt, inc=False):
        """ Returns the first recurrence after the given datetime instance. The
            inc keyword defines what happens if dt is an occurrence. With
            inc=True, if dt itself is an occurrence, it will be returned.  """
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        if inc:
            for i in gen:
                if i >= dt:
                    return i
        else:
            for i in gen:
                if i > dt:
                    return i
        return None

    def xafter(self, dt, count=None, inc=False):
        """
        Generator which yields up to `count` recurrences after the given
        datetime instance, equivalent to `after`.

        :param dt:
            The datetime at which to start generating recurrences.

        :param count:
            The maximum number of recurrences to generate. If `None` (default),
            dates are generated until the recurrence rule is exhausted.

        :param inc:
            If `dt` is an instance of the rule and `inc` is `True`, it is
            included in the output.

        :yields: Yields a sequence of `datetime` objects.
        """

        if self._cache_complete:
            gen = self._cache
        else:
            gen = self

        # Select the comparison function
        if inc:
            comp = lambda dc, dtc: dc >= dtc
        else:
            comp = lambda dc, dtc: dc > dtc

        # Generate dates
        n = 0
        for d in gen:
            if comp(d, dt):
                if count is not None:
                    n += 1
                    if n > count:
                        break

                yield d

    def between(self, after, before, inc=False, count=1):
        """ Returns all the occurrences of the rrule between after and before.
        The inc keyword defines what happens if after and/or before are
        themselves occurrences. With inc=True, they will be included in the
        list, if they are found in the recurrence set. """
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        started = False
        l = []
        if inc:
            for i in gen:
                if i > before:
                    break
                elif not started:
                    if i >= after:
                        started = True
                        l.append(i)
                else:
                    l.append(i)
        else:
            for i in gen:
                if i >= before:
                    break
                elif not started:
                    if i > after:
                        started = True
                        l.append(i)
                else:
                    l.append(i)
        return l


class rrule(rrulebase):
    """
    That's the base of the rrule operation. It accepts all the keywords
    defined in the RFC as its constructor parameters (except byday,
    which was renamed to byweekday) and more. The constructor prototype is::

            rrule(freq)

    Where freq must be one of YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY,
    or SECONDLY.

    .. note::
        Per RFC section 3.3.10, recurrence instances falling on invalid dates
        and times are ignored rather than coerced:

            Recurrence rules may generate recurrence instances with an invalid
            date (e.g., February 30) or nonexistent local time (e.g., 1:30 AM
            on a day where the local time is moved forward by an hour at 1:00
            AM).  Such recurrence instances MUST be ignored and MUST NOT be
            counted as part of the recurrence set.

        This can lead to possibly surprising behavior when, for example, the
        start date occurs at the end of the month:

        >>> from dateutil.rrule import rrule, MONTHLY
        >>> from datetime import datetime
        >>> start_date = datetime(2014, 12, 31)
        >>> list(rrule(freq=MONTHLY, count=4, dtstart=start_date))
        ... # doctest: +NORMALIZE_WHITESPACE
        [datetime.datetime(2014, 12, 31, 0, 0),
         datetime.datetime(2015, 1, 31, 0, 0),
         datetime.datetime(2015, 3, 31, 0, 0),
         datetime.datetime(2015, 5, 31, 0, 0)]

    Additionally, it supports the following keyword arguments:

    :param dtstart:
        The recurrence start. Besides being the base for the recurrence,
        missing parameters in the final recurrence instances will also be
        extracted from this date. If not given, datetime.now() will be used
        instead.
    :param interval:
        The interval between each freq iteration. For example, when using
        YEARLY, an interval of 2 means once every two years, but with HOURLY,
        it means once every two hours. The default interval is 1.
    :param wkst:
        The week start day. Must be one of the MO, TU, WE constants, or an
        integer, specifying the first day of the week. This will affect
        recurrences based on weekly periods. The default week start is got
        from calendar.firstweekday(), and may be modified by
        calendar.setfirstweekday().
    :param count:
        If given, this determines how many occurrences will be generated.

        .. note::
            As of version 2.5.0, the use of the keyword ``until`` in conjunction
            with ``count`` is deprecated, to make sure ``dateutil`` is fully
            compliant with `RFC-5545 Sec. 3.3.10 <https://tools.ietf.org/
            html/rfc5545#section-3.3.10>`_. Therefore, ``until`` and ``count``
            **must not** occur in the same call to ``rrule``.
    :param until:
        If given, this must be a datetime instance specifying the upper-bound
        limit of the recurrence. The last recurrence in the rule is the greatest
        datetime that is less than or equal to the value specified in the
        ``until`` parameter.

        .. note::
            As of version 2.5.0, the use of the keyword ``until`` in conjunction
            with ``count`` is deprecated, to make sure ``dateutil`` is fully
            compliant with `RFC-5545 Sec. 3.3.10 <https://tools.ietf.org/
            html/rfc5545#section-3.3.10>`_. Therefore, ``until`` and ``count``
            **must not** occur in the same call to ``rrule``.
    :param bysetpos:
        If given, it must be either an integer, or a sequence of integers,
        positive or negative. Each given integer will specify an occurrence
        number, corresponding to the nth occurrence of the rule inside the
        frequency period. For example, a bysetpos of -1 if combined with a
        MONTHLY frequency, and a byweekday of (MO, TU, WE, TH, FR), will
        result in the last work day of every month.
    :param bymonth:
        If given, it must be either an integer, or a sequence of integers,
        meaning the months to apply the recurrence to.
    :param bymonthday:
        If given, it must be either an integer, or a sequence of integers,
        meaning the month days to apply the recurrence to.
    :param byyearday:
        If given, it must be either an integer, or a sequence of integers,
        meaning the year days to apply the recurrence to.
    :param byeaster:
        If given, it must be either an integer, or a sequence of integers,
        positive or negative. Each integer will define an offset from the
        Easter Sunday. Passing the offset 0 to byeaster will yield the Easter
        Sunday itself. This is an extension to the RFC specification.
    :param byweekno:
        If given, it must be either an integer, or a sequence of integers,
        meaning the week numbers to apply the recurrence to. Week numbers
        have the meaning described in ISO8601, that is, the first week of
        the year is that containing at least four days of the new year.
    :param byweekday:
        If given, it must be either an integer (0 == MO), a sequence of
        integers, one of the weekday constants (MO, TU, etc), or a sequence
        of these constants. When given, these variables will define the
        weekdays where the recurrence will be applied. It's also possible to
        use an argument n for the weekday instances, which will mean the nth
        occurrence of this weekday in the period. For example, with MONTHLY,
        or with YEARLY and BYMONTH, using FR(+1) in byweekday will specify the
        first friday of the month where the recurrence happens. Notice that in
        the RFC documentation, this is specified as BYDAY, but was renamed to
        avoid the ambiguity of that keyword.
    :param byhour:
        If given, it must be either an integer, or a sequence of integers,
        meaning the hours to apply the recurrence to.
    :param byminute:
        If given, it must be either an integer, or a sequence of integers,
        meaning the minutes to apply the recurrence to.
    :param bysecond:
        If given, it must be either an integer, or a sequence of integers,
        meaning the seconds to apply the recurrence to.
    :param cache:
        If given, it must be a boolean value specifying to enable or disable
        caching of results. If you will use the same rrule instance multiple
        times, enabling caching will improve the performance considerably.
     """
    def __init__(self, freq, dtstart=None,
                 interval=1, wkst=None, count=None, until=None, bysetpos=None,
                 bymonth=None, bymonthday=None, byyearday=None, byeaster=None,
                 byweekno=None, byweekday=None,
                 byhour=None, byminute=None, bysecond=None,
                 cache=False):
        super(rrule, self).__init__(cache)
        global easter
        if not dtstart:
            if until and until.tzinfo:
                dtstart = datetime.datetime.now(tz=until.tzinfo).replace(microsecond=0)
            else:
                dtstart = datetime.datetime.now().replace(microsecond=0)
        elif not isinstance(dtstart, datetime.datetime):
            dtstart = datetime.datetime.fromordinal(dtstart.toordinal())
        else:
            dtstart = dtstart.replace(microsecond=0)
        self._dtstart = dtstart
        self._tzinfo = dtstart.tzinfo
        self._freq = freq
        self._interval = interval
        self._count = count

        # Cache the original byxxx rules, if they are provided, as the _byxxx
        # attributes do not necessarily map to the inputs, and this can be
        # a problem in generating the strings. Only store things if they've
        # been supplied (the string retrieval will just use .get())
        self._original_rule = {}

        if until and not isinstance(until, datetime.datetime):
            until = datetime.datetime.fromordinal(until.toordinal())
        self._until = until

        if self._dtstart and self._until:
            if (self._dtstart.tzinfo is not None) != (self._until.tzinfo is not None):
                # According to RFC5545 Section 3.3.10:
                # https://tools.ietf.org/html/rfc5545#section-3.3.10
                #
                # > If the "DTSTART" property is specified as a date with UTC
                # > time or a date with local time and time zone reference,
                # > then the UNTIL rule part MUST be specified as a date with
                # > UTC time.
                raise ValueError(
                    'RRULE UNTIL values must be specified in UTC when DTSTART '
                    'is timezone-aware'
                )

        if count is not None and until:
            warn("Using both 'count' and 'until' is inconsistent with RFC 5545"
                 " and has been deprecated in dateutil. Future versions will "
                 "raise an error.", DeprecationWarning)

        if wkst is None:
            self._wkst = calendar.firstweekday()
        elif isinstance(wkst, integer_types):
            self._wkst = wkst
        else:
            self._wkst = wkst.weekday

        if bysetpos is None:
            self._bysetpos = None
        elif isinstance(bysetpos, integer_types):
            if bysetpos == 0 or not (-366 <= bysetpos <= 366):
                raise ValueError("bysetpos must be between 1 and 366, "
                                 "or between -366 and -1")
            self._bysetpos = (bysetpos,)
        else:
            self._bysetpos = tuple(bysetpos)
            for pos in self._bysetpos:
                if pos == 0 or not (-366 <= pos <= 366):
                    raise ValueError("bysetpos must be between 1 and 366, "
                                     "or between -366 and -1")

        if self._bysetpos:
            self._original_rule['bysetpos'] = self._bysetpos

        if (byweekno is None and byyearday is None and bymonthday is None and
                byweekday is None and byeaster is None):
            if freq == YEARLY:
                if bymonth is None:
                    bymonth = dtstart.month
                    self._original_rule['bymonth'] = None
                bymonthday = dtstart.day
                self._original_rule['bymonthday'] = None
            elif freq == MONTHLY:
                bymonthday = dtstart.day
                self._original_rule['bymonthday'] = None
            elif freq == WEEKLY:
                byweekday = dtstart.weekday()
                self._original_rule['byweekday'] = None

        # bymonth
        if bymonth is None:
            self._bymonth = None
        else:
            if isinstance(bymonth, integer_types):
                bymonth = (bymonth,)

            self._bymonth = tuple(sorted(set(bymonth)))

            if 'bymonth' not in self._original_rule:
                self._original_rule['bymonth'] = self._bymonth

        # byyearday
        if byyearday is None:
            self._byyearday = None
        else:
            if isinstance(byyearday, integer_types):
                byyearday = (byyearday,)

            self._byyearday = tuple(sorted(set(byyearday)))
            self._original_rule['byyearday'] = self._byyearday

        # byeaster
        if byeaster is not None:
            if not easter:
                from dateutil import easter
            if isinstance(byeaster, integer_types):
                self._byeaster = (byeaster,)
            else:
                self._byeaster = tuple(sorted(byeaster))

            self._original_rule['byeaster'] = self._byeaster
        else:
            self._byeaster = None

        # bymonthday
        if bymonthday is None:
            self._bymonthday = ()
            self._bynmonthday = ()
        else:
            if isinstance(bymonthday, integer_types):
                bymonthday = (bymonthday,)

            bymonthday = set(bymonthday)            # Ensure it's unique

            self._bymonthday = tuple(sorted(x for x in bymonthday if x > 0))
            self._bynmonthday = tuple(sorted(x for x in bymonthday if x < 0))

            # Storing positive numbers first, then negative numbers
            if 'bymonthday' not in self._original_rule:
                self._original_rule['bymonthday'] = tuple(
                    itertools.chain(self._bymonthday, self._bynmonthday))

        # byweekno
        if byweekno is None:
            self._byweekno = None
        else:
            if isinstance(byweekno, integer_types):
                byweekno = (byweekno,)

            self._byweekno = tuple(sorted(set(byweekno)))

            self._original_rule['byweekno'] = self._byweekno

        # byweekday / bynweekday
        if byweekday is None:
            self._byweekday = None
            self._bynweekday = None
        else:
            # If it's one of the valid non-sequence types, convert to a
            # single-element sequence before the iterator that builds the
            # byweekday set.
            if isinstance(byweekday, integer_types) or hasattr(byweekday, "n"):
                byweekday = (byweekday,)

            self._byweekday = set()
            self._bynweekday = set()
            for wday in byweekday:
                if isinstance(wday, integer_types):
                    self._byweekday.add(wday)
                elif not wday.n or freq > MONTHLY:
                    self._byweekday.add(wday.weekday)
                else:
                    self._bynweekday.add((wday.weekday, wday.n))

            if not self._byweekday:
                self._byweekday = None
            elif not self._bynweekday:
                self._bynweekday = None

            if self._byweekday is not None:
                self._byweekday = tuple(sorted(self._byweekday))
                orig_byweekday = [weekday(x) for x in self._byweekday]
            else:
                orig_byweekday = ()

            if self._bynweekday is not None:
                self._bynweekday = tuple(sorted(self._bynweekday))
                orig_bynweekday = [weekday(*x) for x in self._bynweekday]
            else:
                orig_bynweekday = ()

            if 'byweekday' not in self._original_rule:
                self._original_rule['byweekday'] = tuple(itertools.chain(
                    orig_byweekday, orig_bynweekday))

        # byhour
        if byhour is None:
            if freq < HOURLY:
                self._byhour = {dtstart.hour}
            else:
                self._byhour = None
        else:
            if isinstance(byhour, integer_types):
                byhour = (byhour,)

            if freq == HOURLY:
                self._byhour = self.__construct_byset(start=dtstart.hour,
                                                      byxxx=byhour,
                                                      base=24)
            else:
                self._byhour = set(byhour)

            self._byhour = tuple(sorted(self._byhour))
            self._original_rule['byhour'] = self._byhour

        # byminute
        if byminute is None:
            if freq < MINUTELY:
                self._byminute = {dtstart.minute}
            else:
                self._byminute = None
        else:
            if isinstance(byminute, integer_types):
                byminute = (byminute,)

            if freq == MINUTELY:
                self._byminute = self.__construct_byset(start=dtstart.minute,
                                                        byxxx=byminute,
                                                        base=60)
            else:
                self._byminute = set(byminute)

            self._byminute = tuple(sorted(self._byminute))
            self._original_rule['byminute'] = self._byminute

        # bysecond
        if bysecond is None:
            if freq < SECONDLY:
                self._bysecond = ((dtstart.second,))
            else:
                self._bysecond = None
        else:
            if isinstance(bysecond, integer_types):
                bysecond = (bysecond,)

            self._bysecond = set(bysecond)

            if freq == SECONDLY:
                self._bysecond = self.__construct_byset(start=dtstart.second,
                                                        byxxx=bysecond,
                                                        base=60)
            else:
                self._bysecond = set(bysecond)

            self._bysecond = tuple(sorted(self._bysecond))
            self._original_rule['bysecond'] = self._bysecond

        if self._freq >= HOURLY:
            self._timeset = None
        else:
            self._timeset = []
            for hour in self._byhour:
                for minute in self._byminute:
                    for second in self._bysecond:
                        self._timeset.append(
                            datetime.time(hour, minute, second,
                                          tzinfo=self._tzinfo))
            self._timeset.sort()
            self._timeset = tuple(self._timeset)

    def __str__(self):
        """
        Output a string that would generate this RRULE if passed to rrulestr.
        This is mostly compatible with RFC5545, except for the
        dateutil-specific extension BYEASTER.
        """

        output = []
        h, m, s = [None] * 3
        if self._dtstart:
            output.append(self._dtstart.strftime('DTSTART:%Y%m%dT%H%M%S'))
            h, m, s = self._dtstart.timetuple()[3:6]

        parts = ['FREQ=' + FREQNAMES[self._freq]]
        if self._interval != 1:
            parts.append('INTERVAL=' + str(self._interval))

        if self._wkst:
            parts.append('WKST=' + repr(weekday(self._wkst))[0:2])

        if self._count is not None:
            parts.append('COUNT=' + str(self._count))

        if self._until:
            parts.append(self._until.strftime('UNTIL=%Y%m%dT%H%M%S'))

        if self._original_rule.get('byweekday') is not None:
            # The str() method on weekday objects doesn't generate
            # RFC5545-compliant strings, so we should modify that.
            original_rule = dict(self._original_rule)
            wday_strings = []
            for wday in original_rule['byweekday']:
                if wday.n:
                    wday_strings.append('{n:+d}{wday}'.format(
                        n=wday.n,
                        wday=repr(wday)[0:2]))
                else:
                    wday_strings.append(repr(wday))

            original_rule['byweekday'] = wday_strings
        else:
            original_rule = self._original_rule

        partfmt = '{name}={vals}'
        for name, key in [('BYSETPOS', 'bysetpos'),
                          ('BYMONTH', 'bymonth'),
                          ('BYMONTHDAY', 'bymonthday'),
                          ('BYYEARDAY', 'byyearday'),
                          ('BYWEEKNO', 'byweekno'),
                          ('BYDAY', 'byweekday'),
                          ('BYHOUR', 'byhour'),
                          ('BYMINUTE', 'byminute'),
                          ('BYSECOND', 'bysecond'),
                          ('BYEASTER', 'byeaster')]:
            value = original_rule.get(key)
            if value:
                parts.append(partfmt.format(name=name, vals=(','.join(str(v)
                                                             for v in value))))

        output.append('RRULE:' + ';'.join(parts))
        return '\n'.join(output)

    def replace(self, **kwargs):
        """Return new rrule with same attributes except for those attributes given new
           values by whichever keyword arguments are specified."""
        new_kwargs = {"interval": self._interval,
                      "count": self._count,
                      "dtstart": self._dtstart,
                      "freq": self._freq,
                      "until": self._until,
                      "wkst": self._wkst,
                      "cache": False if self._cache is None else True }
        new_kwargs.update(self._original_rule)
        new_kwargs.update(kwargs)
        return rrule(**new_kwargs)

    def _iter(self):
        year, month, day, hour, minute, second, weekday, yearday, _ = \
            self._dtstart.timetuple()

        # Some local variables to speed things up a bit
        freq = self._freq
        interval = self._interval
        wkst = self._wkst
        until = self._until
        bymonth = self._bymonth
        byweekno = self._byweekno
        byyearday = self._byyearday
        byweekday = self._byweekday
        byeaster = self._byeaster
        bymonthday = self._bymonthday
        bynmonthday = self._bynmonthday
        bysetpos = self._bysetpos
        byhour = self._byhour
        byminute = self._byminute
        bysecond = self._bysecond

        ii = _iterinfo(self)
        ii.rebuild(year, month)

        getdayset = {YEARLY: ii.ydayset,
                     MONTHLY: ii.mdayset,
                     WEEKLY: ii.wdayset,
                     DAILY: ii.ddayset,
                     HOURLY: ii.ddayset,
                     MINUTELY: ii.ddayset,
                     SECONDLY: ii.ddayset}[freq]

        if freq < HOURLY:
            timeset = self._timeset
        else:
            gettimeset = {HOURLY: ii.htimeset,
                          MINUTELY: ii.mtimeset,
                          SECONDLY: ii.stimeset}[freq]
            if ((freq >= HOURLY and
                 self._byhour and hour not in self._byhour) or
                (freq >= MINUTELY and
                 self._byminute and minute not in self._byminute) or
                (freq >= SECONDLY and
                 self._bysecond and second not in self._bysecond)):
                timeset = ()
            else:
                timeset = gettimeset(hour, minute, second)

        total = 0
        count = self._count
        while True:
            # Get dayset with the right frequency
            dayset, start, end = getdayset(year, month, day)

            # Do the "hard" work ;-)
            filtered = False
            for i in dayset[start:end]:
                if ((bymonth and ii.mmask[i] not in bymonth) or
                    (byweekno and not ii.wnomask[i]) or
                    (byweekday and ii.wdaymask[i] not in byweekday) or
                    (ii.nwdaymask and not ii.nwdaymask[i]) or
                    (byeaster and not ii.eastermask[i]) or
                    ((bymonthday or bynmonthday) and
                     ii.mdaymask[i] not in bymonthday and
                     ii.nmdaymask[i] not in bynmonthday) or
                    (byyearday and
                     ((i < ii.yearlen and i+1 not in byyearday and
                       -ii.yearlen+i not in byyearday) or
                      (i >= ii.yearlen and i+1-ii.yearlen not in byyearday and
                       -ii.nextyearlen+i-ii.yearlen not in byyearday)))):
                    dayset[i] = None
                    filtered = True

            # Output results
            if bysetpos and timeset:
                poslist = []
                for pos in bysetpos:
                    if pos < 0:
                        daypos, timepos = divmod(pos, len(timeset))
                    else:
                        daypos, timepos = divmod(pos-1, len(timeset))
                    try:
                        i = [x for x in dayset[start:end]
                             if x is not None][daypos]
                        time = timeset[timepos]
                    except IndexError:
                        pass
                    else:
                        date = datetime.date.fromordinal(ii.yearordinal+i)
                        res = datetime.datetime.combine(date, time)
                        if res not in poslist:
                            poslist.append(res)
                poslist.sort()
                for res in poslist:
                    if until and res > until:
                        self._len = total
                        return
                    elif res >= self._dtstart:
                        if count is not None:
                            count -= 1
                            if count < 0:
                                self._len = total
                                return
                        total += 1
                        yield res
            else:
                for i in dayset[start:end]:
                    if i is not None:
                        date = datetime.date.fromordinal(ii.yearordinal + i)
                        for time in timeset:
                            res = datetime.datetime.combine(date, time)
                            if until and res > until:
                                self._len = total
                                return
                            elif res >= self._dtstart:
                                if count is not None:
                                    count -= 1
                                    if count < 0:
                                        self._len = total
                                        return

                                total += 1
                                yield res

            # Handle frequency and interval
            fixday = False
            if freq == YEARLY:
                year += interval
                if year > datetime.MAXYEAR:
                    self._len = total
                    return
                ii.rebuild(year, month)
            elif freq == MONTHLY:
                month += interval
                if month > 12:
                    div, mod = divmod(month, 12)
                    month = mod
                    year += div
                    if month == 0:
                        month = 12
                        year -= 1
                    if year > datetime.MAXYEAR:
                        self._len = total
                        return
                ii.rebuild(year, month)
            elif freq == WEEKLY:
                if wkst > weekday:
                    day += -(weekday+1+(6-wkst))+self._interval*7
                else:
                    day += -(weekday-wkst)+self._interval*7
                weekday = wkst
                fixday = True
            elif freq == DAILY:
                day += interval
                fixday = True
            elif freq == HOURLY:
                if filtered:
                    # Jump to one iteration before next day
                    hour += ((23-hour)//interval)*interval

                if byhour:
                    ndays, hour = self.__mod_distance(value=hour,
                                                      byxxx=self._byhour,
                                                      base=24)
                else:
                    ndays, hour = divmod(hour+interval, 24)

                if ndays:
                    day += ndays
                    fixday = True

                timeset = gettimeset(hour, minute, second)
            elif freq == MINUTELY:
                if filtered:
                    # Jump to one iteration before next day
                    minute += ((1439-(hour*60+minute))//interval)*interval

                valid = False
                rep_rate = (24*60)
                for j in range(rep_rate // gcd(interval, rep_rate)):
                    if byminute:
                        nhours, minute = \
                            self.__mod_distance(value=minute,
                                                byxxx=self._byminute,
                                                base=60)
                    else:
                        nhours, minute = divmod(minute+interval, 60)

                    div, hour = divmod(hour+nhours, 24)
                    if div:
                        day += div
                        fixday = True
                        filtered = False

                    if not byhour or hour in byhour:
                        valid = True
                        break

                if not valid:
                    raise ValueError('Invalid combination of interval and ' +
                                     'byhour resulting in empty rule.')

                timeset = gettimeset(hour, minute, second)
            elif freq == SECONDLY:
                if filtered:
                    # Jump to one iteration before next day
                    second += (((86399 - (hour * 3600 + minute * 60 + second))
                                // interval) * interval)

                rep_rate = (24 * 3600)
                valid = False
                for j in range(0, rep_rate // gcd(interval, rep_rate)):
                    if bysecond:
                        nminutes, second = \
                            self.__mod_distance(value=second,
                                                byxxx=self._bysecond,
                                                base=60)
                    else:
                        nminutes, second = divmod(second+interval, 60)

                    div, minute = divmod(minute+nminutes, 60)
                    if div:
                        hour += div
                        div, hour = divmod(hour, 24)
                        if div:
                            day += div
                            fixday = True

                    if ((not byhour or hour in byhour) and
                            (not byminute or minute in byminute) and
                            (not bysecond or second in bysecond)):
                        valid = True
                        break

                if not valid:
                    raise ValueError('Invalid combination of interval, ' +
                                     'byhour and byminute resulting in empty' +
                                     ' rule.')

                timeset = gettimeset(hour, minute, second)

            if fixday and day > 28:
                daysinmonth = calendar.monthrange(year, month)[1]
                if day > daysinmonth:
                    while day > daysinmonth:
                        day -= daysinmonth
                        month += 1
                        if month == 13:
                            month = 1
                            year += 1
                            if year > datetime.MAXYEAR:
                                self._len = total
                                return
                        daysinmonth = calendar.monthrange(year, month)[1]
                    ii.rebuild(year, month)

    def __construct_byset(self, start, byxxx, base):
        """
        If a `BYXXX` sequence is passed to the constructor at the same level as
        `FREQ` (e.g. `FREQ=HOURLY,BYHOUR={2,4,7},INTERVAL=3`), there are some
        specifications which cannot be reached given some starting conditions.

        This occurs whenever the interval is not coprime with the base of a
        given unit and the difference between the starting position and the
        ending position is not coprime with the greatest common denominator
        between the interval and the base. For example, with a FREQ of hourly
        starting at 17:00 and an interval of 4, the only valid values for
        BYHOUR would be {21, 1, 5, 9, 13, 17}, because 4 and 24 are not
        coprime.

        :param start:
            Specifies the starting position.
        :param byxxx:
            An iterable containing the list of allowed values.
        :param base:
            The largest allowable value for the specified frequency (e.g.
            24 hours, 60 minutes).

        This does not preserve the type of the iterable, returning a set, since
        the values should be unique and the order is irrelevant, this will
        speed up later lookups.

        In the event of an empty set, raises a :exception:`ValueError`, as this
        results in an empty rrule.
        """

        cset = set()

        # Support a single byxxx value.
        if isinstance(byxxx, integer_types):
            byxxx = (byxxx, )

        for num in byxxx:
            i_gcd = gcd(self._interval, base)
            # Use divmod rather than % because we need to wrap negative nums.
            if i_gcd == 1 or divmod(num - start, i_gcd)[1] == 0:
                cset.add(num)

        if len(cset) == 0:
            raise ValueError("Invalid rrule byxxx generates an empty set.")

        return cset

    def __mod_distance(self, value, byxxx, base):
        """
        Calculates the next value in a sequence where the `FREQ` parameter is
        specified along with a `BYXXX` parameter at the same "level"
        (e.g. `HOURLY` specified with `BYHOUR`).

        :param value:
            The old value of the component.
        :param byxxx:
            The `BYXXX` set, which should have been generated by
            `rrule._construct_byset`, or something else which checks that a
            valid rule is present.
        :param base:
            The largest allowable value for the specified frequency (e.g.
            24 hours, 60 minutes).

        If a valid value is not found after `base` iterations (the maximum
        number before the sequence would start to repeat), this raises a
        :exception:`ValueError`, as no valid values were found.

        This returns a tuple of `divmod(n*interval, base)`, where `n` is the
        smallest number of `interval` repetitions until the next specified
        value in `byxxx` is found.
        """
        accumulator = 0
        for ii in range(1, base + 1):
            # Using divmod() over % to account for negative intervals
            div, value = divmod(value + self._interval, base)
            accumulator += div
            if value in byxxx:
                return (accumulator, value)


class _iterinfo(object):
    __slots__ = ["rrule", "lastyear", "lastmonth",
                 "yearlen", "nextyearlen", "yearordinal", "yearweekday",
                 "mmask", "mrange", "mdaymask", "nmdaymask",
                 "wdaymask", "wnomask", "nwdaymask", "eastermask"]

    def __init__(self, rrule):
        for attr in self.__slots__:
            setattr(self, attr, None)
        self.rrule = rrule

    def rebuild(self, year, month):
        # Every mask is 7 days longer to handle cross-year weekly periods.
        rr = self.rrule
        if year != self.lastyear:
            self.yearlen = 365 + calendar.isleap(year)
            self.nextyearlen = 365 + calendar.isleap(year + 1)
            firstyday = datetime.date(year, 1, 1)
            self.yearordinal = firstyday.toordinal()
            self.yearweekday = firstyday.weekday()

            wday = datetime.date(year, 1, 1).weekday()
            if self.yearlen == 365:
                self.mmask = M365MASK
                self.mdaymask = MDAY365MASK
                self.nmdaymask = NMDAY365MASK
                self.wdaymask = WDAYMASK[wday:]
                self.mrange = M365RANGE
            else:
                self.mmask = M366MASK
                self.mdaymask = MDAY366MASK
                self.nmdaymask = NMDAY366MASK
                self.wdaymask = WDAYMASK[wday:]
                self.mrange = M366RANGE

            if not rr._byweekno:
                self.wnomask = None
            else:
                self.wnomask = [0]*(self.yearlen+7)
                # no1wkst = firstwkst = self.wdaymask.index(rr._wkst)
                no1wkst = firstwkst = (7-self.yearweekday+rr._wkst) % 7
                if no1wkst >= 4:
                    no1wkst = 0
                    # Number of days in the year, plus the days we got
                    # from last year.
                    wyearlen = self.yearlen+(self.yearweekday-rr._wkst) % 7
                else:
                    # Number of days in the year, minus the days we
                    # left in last year.
                    wyearlen = self.yearlen-no1wkst
                div, mod = divmod(wyearlen, 7)
                numweeks = div+mod//4
                for n in rr._byweekno:
                    if n < 0:
                        n += numweeks+1
                    if not (0 < n <= numweeks):
                        continue
                    if n > 1:
                        i = no1wkst+(n-1)*7
                        if no1wkst != firstwkst:
                            i -= 7-firstwkst
                    else:
                        i = no1wkst
                    for j in range(7):
                        self.wnomask[i] = 1
                        i += 1
                        if self.wdaymask[i] == rr._wkst:
                            break
                if 1 in rr._byweekno:
                    # Check week number 1 of next year as well
                    # TODO: Check -numweeks for next year.
                    i = no1wkst+numweeks*7
                    if no1wkst != firstwkst:
                        i -= 7-firstwkst
                    if i < self.yearlen:
                        # If week starts in next year, we
                        # don't care about it.
                        for j in range(7):
                            self.wnomask[i] = 1
                            i += 1
                            if self.wdaymask[i] == rr._wkst:
                                break
                if no1wkst:
                    # Check last week number of last year as
                    # well. If no1wkst is 0, either the year
                    # started on week start, or week number 1
                    # got days from last year, so there are no
                    # days from last year's last week number in
                    # this year.
                    if -1 not in rr._byweekno:
                        lyearweekday = datetime.date(year-1, 1, 1).weekday()
                        lno1wkst = (7-lyearweekday+rr._wkst) % 7
                        lyearlen = 365+calendar.isleap(year-1)
                        if lno1wkst >= 4:
                            lno1wkst = 0
                            lnumweeks = 52+(lyearlen +
                                            (lyearweekday-rr._wkst) % 7) % 7//4
                        else:
                            lnumweeks = 52+(self.yearlen-no1wkst) % 7//4
                    else:
                        lnumweeks = -1
                    if lnumweeks in rr._byweekno:
                        for i in range(no1wkst):
                            self.wnomask[i] = 1

        if (rr._bynweekday and (month != self.lastmonth or
                                year != self.lastyear)):
            ranges = []
            if rr._freq == YEARLY:
                if rr._bymonth:
                    for month in rr._bymonth:
                        ranges.append(self.mrange[month-1:month+1])
                else:
                    ranges = [(0, self.yearlen)]
            elif rr._freq == MONTHLY:
                ranges = [self.mrange[month-1:month+1]]
            if ranges:
                # Weekly frequency won't get here, so we may not
                # care about cross-year weekly periods.
                self.nwdaymask = [0]*self.yearlen
                for first, last in ranges:
                    last -= 1
                    for wday, n in rr._bynweekday:
                        if n < 0:
                            i = last+(n+1)*7
                            i -= (self.wdaymask[i]-wday) % 7
                        else:
                            i = first+(n-1)*7
                            i += (7-self.wdaymask[i]+wday) % 7
                        if first <= i <= last:
                            self.nwdaymask[i] = 1

        if rr._byeaster:
            self.eastermask = [0]*(self.yearlen+7)
            eyday = easter.easter(year).toordinal()-self.yearordinal
            for offset in rr._byeaster:
                self.eastermask[eyday+offset] = 1

        self.lastyear = year
        self.lastmonth = month

    def ydayset(self, year, month, day):
        return list(range(self.yearlen)), 0, self.yearlen

    def mdayset(self, year, month, day):
        dset = [None]*self.yearlen
        start, end = self.mrange[month-1:month+1]
        for i in range(start, end):
            dset[i] = i
        return dset, start, end

    def wdayset(self, year, month, day):
        # We need to handle cross-year weeks here.
        dset = [None]*(self.yearlen+7)
        i = datetime.date(year, month, day).toordinal()-self.yearordinal
        start = i
        for j in range(7):
            dset[i] = i
            i += 1
            # if (not (0 <= i < self.yearlen) or
            #    self.wdaymask[i] == self.rrule._wkst):
            # This will cross the year boundary, if necessary.
            if self.wdaymask[i] == self.rrule._wkst:
                break
        return dset, start, i

    def ddayset(self, year, month, day):
        dset = [None] * self.yearlen
        i = datetime.date(year, month, day).toordinal() - self.yearordinal
        dset[i] = i
        return dset, i, i + 1

    def htimeset(self, hour, minute, second):
        tset = []
        rr = self.rrule
        for minute in rr._byminute:
            for second in rr._bysecond:
                tset.append(datetime.time(hour, minute, second,
                                          tzinfo=rr._tzinfo))
        tset.sort()
        return tset

    def mtimeset(self, hour, minute, second):
        tset = []
        rr = self.rrule
        for second in rr._bysecond:
            tset.append(datetime.time(hour, minute, second, tzinfo=rr._tzinfo))
        tset.sort()
        return tset

    def stimeset(self, hour, minute, second):
        return (datetime.time(hour, minute, second,
                tzinfo=self.rrule._tzinfo),)


class rruleset(rrulebase):
    """ The rruleset type allows more complex recurrence setups, mixing
    multiple rules, dates, exclusion rules, and exclusion dates. The type
    constructor takes the following keyword arguments:

    :param cache: If True, caching of results will be enabled, improving
                  performance of multiple queries considerably. """

    class _genitem(object):
        def __init__(self, genlist, gen):
            try:
                self.dt = advance_iterator(gen)
                genlist.append(self)
            except StopIteration:
                pass
            self.genlist = genlist
            self.gen = gen

        def __next__(self):
            try:
                self.dt = advance_iterator(self.gen)
            except StopIteration:
                if self.genlist[0] is self:
                    heapq.heappop(self.genlist)
                else:
                    self.genlist.remove(self)
                    heapq.heapify(self.genlist)

        next = __next__

        def __lt__(self, other):
            return self.dt < other.dt

        def __gt__(self, other):
            return self.dt > other.dt

        def __eq__(self, other):
            return self.dt == other.dt

        def __ne__(self, other):
            return self.dt != other.dt

    def __init__(self, cache=False):
        super(rruleset, self).__init__(cache)
        self._rrule = []
        self._rdate = []
        self._exrule = []
        self._exdate = []

    @_invalidates_cache
    def rrule(self, rrule):
        """ Include the given :py:class:`rrule` instance in the recurrence set
            generation. """
        self._rrule.append(rrule)

    @_invalidates_cache
    def rdate(self, rdate):
        """ Include the given :py:class:`datetime` instance in the recurrence
            set generation. """
        self._rdate.append(rdate)

    @_invalidates_cache
    def exrule(self, exrule):
        """ Include the given rrule instance in the recurrence set exclusion
            list. Dates which are part of the given recurrence rules will not
            be generated, even if some inclusive rrule or rdate matches them.
        """
        self._exrule.append(exrule)

    @_invalidates_cache
    def exdate(self, exdate):
        """ Include the given datetime instance in the recurrence set
            exclusion list. Dates included that way will not be generated,
            even if some inclusive rrule or rdate matches them. """
        self._exdate.append(exdate)

    def _iter(self):
        rlist = []
        self._rdate.sort()
        self._genitem(rlist, iter(self._rdate))
        for gen in [iter(x) for x in self._rrule]:
            self._genitem(rlist, gen)
        exlist = []
        self._exdate.sort()
        self._genitem(exlist, iter(self._exdate))
        for gen in [iter(x) for x in self._exrule]:
            self._genitem(exlist, gen)
        lastdt = None
        total = 0
        heapq.heapify(rlist)
        heapq.heapify(exlist)
        while rlist:
            ritem = rlist[0]
            if not lastdt or lastdt != ritem.dt:
                while exlist and exlist[0] < ritem:
                    exitem = exlist[0]
                    advance_iterator(exitem)
                    if exlist and exlist[0] is exitem:
                        heapq.heapreplace(exlist, exitem)
                if not exlist or ritem != exlist[0]:
                    total += 1
                    yield ritem.dt
                lastdt = ritem.dt
            advance_iterator(ritem)
            if rlist and rlist[0] is ritem:
                heapq.heapreplace(rlist, ritem)
        self._len = total




class _rrulestr(object):
    """ Parses a string representation of a recurrence rule or set of
    recurrence rules.

    :param s:
        Required, a string defining one or more recurrence rules.

    :param dtstart:
        If given, used as the default recurrence start if not specified in the
        rule string.

    :param cache:
        If set ``True`` caching of results will be enabled, improving
        performance of multiple queries considerably.

    :param unfold:
        If set ``True`` indicates that a rule string is split over more
        than one line and should be joined before processing.

    :param forceset:
        If set ``True`` forces a :class:`dateutil.rrule.rruleset` to
        be returned.

    :param compatible:
        If set ``True`` forces ``unfold`` and ``forceset`` to be ``True``.

    :param ignoretz:
        If set ``True``, time zones in parsed strings are ignored and a naive
        :class:`datetime.datetime` object is returned.

    :param tzids:
        If given, a callable or mapping used to retrieve a
        :class:`datetime.tzinfo` from a string representation.
        Defaults to :func:`dateutil.tz.gettz`.

    :param tzinfos:
        Additional time zone names / aliases which may be present in a string
        representation.  See :func:`dateutil.parser.parse` for more
        information.

    :return:
        Returns a :class:`dateutil.rrule.rruleset` or
        :class:`dateutil.rrule.rrule`
    """

    _freq_map = {"YEARLY": YEARLY,
                 "MONTHLY": MONTHLY,
                 "WEEKLY": WEEKLY,
                 "DAILY": DAILY,
                 "HOURLY": HOURLY,
                 "MINUTELY": MINUTELY,
                 "SECONDLY": SECONDLY}

    _weekday_map = {"MO": 0, "TU": 1, "WE": 2, "TH": 3,
                    "FR": 4, "SA": 5, "SU": 6}

    def _handle_int(self, rrkwargs, name, value, **kwargs):
        rrkwargs[name.lower()] = int(value)

    def _handle_int_list(self, rrkwargs, name, value, **kwargs):
        rrkwargs[name.lower()] = [int(x) for x in value.split(',')]

    _handle_INTERVAL = _handle_int
    _handle_COUNT = _handle_int
    _handle_BYSETPOS = _handle_int_list
    _handle_BYMONTH = _handle_int_list
    _handle_BYMONTHDAY = _handle_int_list
    _handle_BYYEARDAY = _handle_int_list
    _handle_BYEASTER = _handle_int_list
    _handle_BYWEEKNO = _handle_int_list
    _handle_BYHOUR = _handle_int_list
    _handle_BYMINUTE = _handle_int_list
    _handle_BYSECOND = _handle_int_list

    def _handle_FREQ(self, rrkwargs, name, value, **kwargs):
        rrkwargs["freq"] = self._freq_map[value]

    def _handle_UNTIL(self, rrkwargs, name, value, **kwargs):
        global parser
        if not parser:
            from dateutil import parser
        try:
            rrkwargs["until"] = parser.parse(value,
                                             ignoretz=kwargs.get("ignoretz"),
                                             tzinfos=kwargs.get("tzinfos"))
        except ValueError:
            raise ValueError("invalid until date")

    def _handle_WKST(self, rrkwargs, name, value, **kwargs):
        rrkwargs["wkst"] = self._weekday_map[value]

    def _handle_BYWEEKDAY(self, rrkwargs, name, value, **kwargs):
        """
        Two ways to specify this: +1MO or MO(+1)
        """
        l = []
        for wday in value.split(','):
            if '(' in wday:
                # If it's of the form TH(+1), etc.
                splt = wday.split('(')
                w = splt[0]
                n = int(splt[1][:-1])
            elif len(wday):
                # If it's of the form +1MO
                for i in range(len(wday)):
                    if wday[i] not in '+-0123456789':
                        break
                n = wday[:i] or None
                w = wday[i:]
                if n:
                    n = int(n)
            else:
                raise ValueError("Invalid (empty) BYDAY specification.")

            l.append(weekdays[self._weekday_map[w]](n))
        rrkwargs["byweekday"] = l

    _handle_BYDAY = _handle_BYWEEKDAY

    def _parse_rfc_rrule(self, line,
                         dtstart=None,
                         cache=False,
                         ignoretz=False,
                         tzinfos=None):
        if line.find(':') != -1:
            name, value = line.split(':')
            if name != "RRULE":
                raise ValueError("unknown parameter name")
        else:
            value = line
        rrkwargs = {}
        for pair in value.split(';'):
            name, value = pair.split('=')
            name = name.upper()
            value = value.upper()
            try:
                getattr(self, "_handle_"+name)(rrkwargs, name, value,
                                               ignoretz=ignoretz,
                                               tzinfos=tzinfos)
            except AttributeError:
                raise ValueError("unknown parameter '%s'" % name)
            except (KeyError, ValueError):
                raise ValueError("invalid '%s': %s" % (name, value))
        return rrule(dtstart=dtstart, cache=cache, **rrkwargs)

    def _parse_date_value(self, date_value, parms, rule_tzids,
                          ignoretz, tzids, tzinfos):
        global parser
        if not parser:
            from dateutil import parser

        datevals = []
        value_found = False
        TZID = None

        for parm in parms:
            if parm.startswith("TZID="):
                try:
                    tzkey = rule_tzids[parm.split('TZID=')[-1]]
                except KeyError:
                    continue
                if tzids is None:
                    from . import tz
                    tzlookup = tz.gettz
                elif callable(tzids):
                    tzlookup = tzids
                else:
                    tzlookup = getattr(tzids, 'get', None)
                    if tzlookup is None:
                        msg = ('tzids must be a callable, mapping, or None, '
                               'not %s' % tzids)
                        raise ValueError(msg)

                TZID = tzlookup(tzkey)
                continue

            # RFC 5445 3.8.2.4: The VALUE parameter is optional, but may be found
            # only once.
            if parm not in {"VALUE=DATE-TIME", "VALUE=DATE"}:
                raise ValueError("unsupported parm: " + parm)
            else:
                if value_found:
                    msg = ("Duplicate value parameter found in: " + parm)
                    raise ValueError(msg)
                value_found = True

        for datestr in date_value.split(','):
            date = parser.parse(datestr, ignoretz=ignoretz, tzinfos=tzinfos)
            if TZID is not None:
                if date.tzinfo is None:
                    date = date.replace(tzinfo=TZID)
                else:
                    raise ValueError('DTSTART/EXDATE specifies multiple timezone')
            datevals.append(date)

        return datevals

    def _parse_rfc(self, s,
                   dtstart=None,
                   cache=False,
                   unfold=False,
                   forceset=False,
                   compatible=False,
                   ignoretz=False,
                   tzids=None,
                   tzinfos=None):
        global parser
        if compatible:
            forceset = True
            unfold = True

        TZID_NAMES = dict(map(
            lambda x: (x.upper(), x),
            re.findall('TZID=(?P<name>[^:]+):', s)
        ))
        s = s.upper()
        if not s.strip():
            raise ValueError("empty string")
        if unfold:
            lines = s.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].rstrip()
                if not line:
                    del lines[i]
                elif i > 0 and line[0] == " ":
                    lines[i-1] += line[1:]
                    del lines[i]
                else:
                    i += 1
        else:
            lines = s.split()
        if (not forceset and len(lines) == 1 and (s.find(':') == -1 or
                                                  s.startswith('RRULE:'))):
            return self._parse_rfc_rrule(lines[0], cache=cache,
                                         dtstart=dtstart, ignoretz=ignoretz,
                                         tzinfos=tzinfos)
        else:
            rrulevals = []
            rdatevals = []
            exrulevals = []
            exdatevals = []
            for line in lines:
                if not line:
                    continue
                if line.find(':') == -1:
                    name = "RRULE"
                    value = line
                else:
                    name, value = line.split(':', 1)
                parms = name.split(';')
                if not parms:
                    raise ValueError("empty property name")
                name = parms[0]
                parms = parms[1:]
                if name == "RRULE":
                    for parm in parms:
                        raise ValueError("unsupported RRULE parm: "+parm)
                    rrulevals.append(value)
                elif name == "RDATE":
                    for parm in parms:
                        if parm != "VALUE=DATE-TIME":
                            raise ValueError("unsupported RDATE parm: "+parm)
                    rdatevals.append(value)
                elif name == "EXRULE":
                    for parm in parms:
                        raise ValueError("unsupported EXRULE parm: "+parm)
                    exrulevals.append(value)
                elif name == "EXDATE":
                    exdatevals.extend(
                        self._parse_date_value(value, parms,
                                               TZID_NAMES, ignoretz,
                                               tzids, tzinfos)
                    )
                elif name == "DTSTART":
                    dtvals = self._parse_date_value(value, parms, TZID_NAMES,
                                                    ignoretz, tzids, tzinfos)
                    if len(dtvals) != 1:
                        raise ValueError("Multiple DTSTART values specified:" +
                                         value)
                    dtstart = dtvals[0]
                else:
                    raise ValueError("unsupported property: "+name)
            if (forceset or len(rrulevals) > 1 or rdatevals
                    or exrulevals or exdatevals):
                if not parser and (rdatevals or exdatevals):
                    from dateutil import parser
                rset = rruleset(cache=cache)
                for value in rrulevals:
                    rset.rrule(self._parse_rfc_rrule(value, dtstart=dtstart,
                                                     ignoretz=ignoretz,
                                                     tzinfos=tzinfos))
                for value in rdatevals:
                    for datestr in value.split(','):
                        rset.rdate(parser.parse(datestr,
                                                ignoretz=ignoretz,
                                                tzinfos=tzinfos))
                for value in exrulevals:
                    rset.exrule(self._parse_rfc_rrule(value, dtstart=dtstart,
                                                      ignoretz=ignoretz,
                                                      tzinfos=tzinfos))
                for value in exdatevals:
                    rset.exdate(value)
                if compatible and dtstart:
                    rset.rdate(dtstart)
                return rset
            else:
                return self._parse_rfc_rrule(rrulevals[0],
                                             dtstart=dtstart,
                                             cache=cache,
                                             ignoretz=ignoretz,
                                             tzinfos=tzinfos)

    def __call__(self, s, **kwargs):
        return self._parse_rfc(s, **kwargs)


rrulestr = _rrulestr()

# vim:ts=4:sw=4:et

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\audits.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Audits (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import network
from . import page
from . import runtime


@dataclass
class AffectedCookie:
    '''
    Information about a cookie that is affected by an inspector issue.
    '''
    #: The following three properties uniquely identify a cookie
    name: str

    path: str

    domain: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['path'] = self.path
        json['domain'] = self.domain
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            path=str(json['path']),
            domain=str(json['domain']),
        )


@dataclass
class AffectedRequest:
    '''
    Information about a request that is affected by an inspector issue.
    '''
    url: str

    #: The unique request id.
    request_id: typing.Optional[network.RequestId] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        if self.request_id is not None:
            json['requestId'] = self.request_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            request_id=network.RequestId.from_json(json['requestId']) if 'requestId' in json else None,
        )


@dataclass
class AffectedFrame:
    '''
    Information about the frame affected by an inspector issue.
    '''
    frame_id: page.FrameId

    def to_json(self):
        json = dict()
        json['frameId'] = self.frame_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            frame_id=page.FrameId.from_json(json['frameId']),
        )


class CookieExclusionReason(enum.Enum):
    EXCLUDE_SAME_SITE_UNSPECIFIED_TREATED_AS_LAX = "ExcludeSameSiteUnspecifiedTreatedAsLax"
    EXCLUDE_SAME_SITE_NONE_INSECURE = "ExcludeSameSiteNoneInsecure"
    EXCLUDE_SAME_SITE_LAX = "ExcludeSameSiteLax"
    EXCLUDE_SAME_SITE_STRICT = "ExcludeSameSiteStrict"
    EXCLUDE_INVALID_SAME_PARTY = "ExcludeInvalidSameParty"
    EXCLUDE_SAME_PARTY_CROSS_PARTY_CONTEXT = "ExcludeSamePartyCrossPartyContext"
    EXCLUDE_DOMAIN_NON_ASCII = "ExcludeDomainNonASCII"
    EXCLUDE_THIRD_PARTY_COOKIE_BLOCKED_IN_FIRST_PARTY_SET = "ExcludeThirdPartyCookieBlockedInFirstPartySet"
    EXCLUDE_THIRD_PARTY_PHASEOUT = "ExcludeThirdPartyPhaseout"
    EXCLUDE_PORT_MISMATCH = "ExcludePortMismatch"
    EXCLUDE_SCHEME_MISMATCH = "ExcludeSchemeMismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieWarningReason(enum.Enum):
    WARN_SAME_SITE_UNSPECIFIED_CROSS_SITE_CONTEXT = "WarnSameSiteUnspecifiedCrossSiteContext"
    WARN_SAME_SITE_NONE_INSECURE = "WarnSameSiteNoneInsecure"
    WARN_SAME_SITE_UNSPECIFIED_LAX_ALLOW_UNSAFE = "WarnSameSiteUnspecifiedLaxAllowUnsafe"
    WARN_SAME_SITE_STRICT_LAX_DOWNGRADE_STRICT = "WarnSameSiteStrictLaxDowngradeStrict"
    WARN_SAME_SITE_STRICT_CROSS_DOWNGRADE_STRICT = "WarnSameSiteStrictCrossDowngradeStrict"
    WARN_SAME_SITE_STRICT_CROSS_DOWNGRADE_LAX = "WarnSameSiteStrictCrossDowngradeLax"
    WARN_SAME_SITE_LAX_CROSS_DOWNGRADE_STRICT = "WarnSameSiteLaxCrossDowngradeStrict"
    WARN_SAME_SITE_LAX_CROSS_DOWNGRADE_LAX = "WarnSameSiteLaxCrossDowngradeLax"
    WARN_ATTRIBUTE_VALUE_EXCEEDS_MAX_SIZE = "WarnAttributeValueExceedsMaxSize"
    WARN_DOMAIN_NON_ASCII = "WarnDomainNonASCII"
    WARN_THIRD_PARTY_PHASEOUT = "WarnThirdPartyPhaseout"
    WARN_CROSS_SITE_REDIRECT_DOWNGRADE_CHANGES_INCLUSION = "WarnCrossSiteRedirectDowngradeChangesInclusion"
    WARN_DEPRECATION_TRIAL_METADATA = "WarnDeprecationTrialMetadata"
    WARN_THIRD_PARTY_COOKIE_HEURISTIC = "WarnThirdPartyCookieHeuristic"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieOperation(enum.Enum):
    SET_COOKIE = "SetCookie"
    READ_COOKIE = "ReadCookie"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class InsightType(enum.Enum):
    '''
    Represents the category of insight that a cookie issue falls under.
    '''
    GIT_HUB_RESOURCE = "GitHubResource"
    GRACE_PERIOD = "GracePeriod"
    HEURISTICS = "Heuristics"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CookieIssueInsight:
    '''
    Information about the suggested solution to a cookie issue.
    '''
    type_: InsightType

    #: Link to table entry in third-party cookie migration readiness list.
    table_entry_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_.to_json()
        if self.table_entry_url is not None:
            json['tableEntryUrl'] = self.table_entry_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=InsightType.from_json(json['type']),
            table_entry_url=str(json['tableEntryUrl']) if 'tableEntryUrl' in json else None,
        )


@dataclass
class CookieIssueDetails:
    '''
    This information is currently necessary, as the front-end has a difficult
    time finding a specific cookie. With this, we can convey specific error
    information without the cookie.
    '''
    cookie_warning_reasons: typing.List[CookieWarningReason]

    cookie_exclusion_reasons: typing.List[CookieExclusionReason]

    #: Optionally identifies the site-for-cookies and the cookie url, which
    #: may be used by the front-end as additional context.
    operation: CookieOperation

    #: If AffectedCookie is not set then rawCookieLine contains the raw
    #: Set-Cookie header string. This hints at a problem where the
    #: cookie line is syntactically or semantically malformed in a way
    #: that no valid cookie could be created.
    cookie: typing.Optional[AffectedCookie] = None

    raw_cookie_line: typing.Optional[str] = None

    site_for_cookies: typing.Optional[str] = None

    cookie_url: typing.Optional[str] = None

    request: typing.Optional[AffectedRequest] = None

    #: The recommended solution to the issue.
    insight: typing.Optional[CookieIssueInsight] = None

    def to_json(self):
        json = dict()
        json['cookieWarningReasons'] = [i.to_json() for i in self.cookie_warning_reasons]
        json['cookieExclusionReasons'] = [i.to_json() for i in self.cookie_exclusion_reasons]
        json['operation'] = self.operation.to_json()
        if self.cookie is not None:
            json['cookie'] = self.cookie.to_json()
        if self.raw_cookie_line is not None:
            json['rawCookieLine'] = self.raw_cookie_line
        if self.site_for_cookies is not None:
            json['siteForCookies'] = self.site_for_cookies
        if self.cookie_url is not None:
            json['cookieUrl'] = self.cookie_url
        if self.request is not None:
            json['request'] = self.request.to_json()
        if self.insight is not None:
            json['insight'] = self.insight.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cookie_warning_reasons=[CookieWarningReason.from_json(i) for i in json['cookieWarningReasons']],
            cookie_exclusion_reasons=[CookieExclusionReason.from_json(i) for i in json['cookieExclusionReasons']],
            operation=CookieOperation.from_json(json['operation']),
            cookie=AffectedCookie.from_json(json['cookie']) if 'cookie' in json else None,
            raw_cookie_line=str(json['rawCookieLine']) if 'rawCookieLine' in json else None,
            site_for_cookies=str(json['siteForCookies']) if 'siteForCookies' in json else None,
            cookie_url=str(json['cookieUrl']) if 'cookieUrl' in json else None,
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
            insight=CookieIssueInsight.from_json(json['insight']) if 'insight' in json else None,
        )


class MixedContentResolutionStatus(enum.Enum):
    MIXED_CONTENT_BLOCKED = "MixedContentBlocked"
    MIXED_CONTENT_AUTOMATICALLY_UPGRADED = "MixedContentAutomaticallyUpgraded"
    MIXED_CONTENT_WARNING = "MixedContentWarning"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class MixedContentResourceType(enum.Enum):
    ATTRIBUTION_SRC = "AttributionSrc"
    AUDIO = "Audio"
    BEACON = "Beacon"
    CSP_REPORT = "CSPReport"
    DOWNLOAD = "Download"
    EVENT_SOURCE = "EventSource"
    FAVICON = "Favicon"
    FONT = "Font"
    FORM = "Form"
    FRAME = "Frame"
    IMAGE = "Image"
    IMPORT = "Import"
    JSON = "JSON"
    MANIFEST = "Manifest"
    PING = "Ping"
    PLUGIN_DATA = "PluginData"
    PLUGIN_RESOURCE = "PluginResource"
    PREFETCH = "Prefetch"
    RESOURCE = "Resource"
    SCRIPT = "Script"
    SERVICE_WORKER = "ServiceWorker"
    SHARED_WORKER = "SharedWorker"
    SPECULATION_RULES = "SpeculationRules"
    STYLESHEET = "Stylesheet"
    TRACK = "Track"
    VIDEO = "Video"
    WORKER = "Worker"
    XML_HTTP_REQUEST = "XMLHttpRequest"
    XSLT = "XSLT"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class MixedContentIssueDetails:
    #: The way the mixed content issue is being resolved.
    resolution_status: MixedContentResolutionStatus

    #: The unsafe http url causing the mixed content issue.
    insecure_url: str

    #: The url responsible for the call to an unsafe url.
    main_resource_url: str

    #: The type of resource causing the mixed content issue (css, js, iframe,
    #: form,...). Marked as optional because it is mapped to from
    #: blink::mojom::RequestContextType, which will be replaced
    #: by network::mojom::RequestDestination
    resource_type: typing.Optional[MixedContentResourceType] = None

    #: The mixed content request.
    #: Does not always exist (e.g. for unsafe form submission urls).
    request: typing.Optional[AffectedRequest] = None

    #: Optional because not every mixed content issue is necessarily linked to a frame.
    frame: typing.Optional[AffectedFrame] = None

    def to_json(self):
        json = dict()
        json['resolutionStatus'] = self.resolution_status.to_json()
        json['insecureURL'] = self.insecure_url
        json['mainResourceURL'] = self.main_resource_url
        if self.resource_type is not None:
            json['resourceType'] = self.resource_type.to_json()
        if self.request is not None:
            json['request'] = self.request.to_json()
        if self.frame is not None:
            json['frame'] = self.frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            resolution_status=MixedContentResolutionStatus.from_json(json['resolutionStatus']),
            insecure_url=str(json['insecureURL']),
            main_resource_url=str(json['mainResourceURL']),
            resource_type=MixedContentResourceType.from_json(json['resourceType']) if 'resourceType' in json else None,
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
            frame=AffectedFrame.from_json(json['frame']) if 'frame' in json else None,
        )


class BlockedByResponseReason(enum.Enum):
    '''
    Enum indicating the reason a response has been blocked. These reasons are
    refinements of the net error BLOCKED_BY_RESPONSE.
    '''
    COEP_FRAME_RESOURCE_NEEDS_COEP_HEADER = "CoepFrameResourceNeedsCoepHeader"
    COOP_SANDBOXED_I_FRAME_CANNOT_NAVIGATE_TO_COOP_PAGE = "CoopSandboxedIFrameCannotNavigateToCoopPage"
    CORP_NOT_SAME_ORIGIN = "CorpNotSameOrigin"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_COEP = "CorpNotSameOriginAfterDefaultedToSameOriginByCoep"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_DIP = "CorpNotSameOriginAfterDefaultedToSameOriginByDip"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_COEP_AND_DIP = "CorpNotSameOriginAfterDefaultedToSameOriginByCoepAndDip"
    CORP_NOT_SAME_SITE = "CorpNotSameSite"
    SRI_MESSAGE_SIGNATURE_MISMATCH = "SRIMessageSignatureMismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class BlockedByResponseIssueDetails:
    '''
    Details for a request that has been blocked with the BLOCKED_BY_RESPONSE
    code. Currently only used for COEP/COOP, but may be extended to include
    some CSP errors in the future.
    '''
    request: AffectedRequest

    reason: BlockedByResponseReason

    parent_frame: typing.Optional[AffectedFrame] = None

    blocked_frame: typing.Optional[AffectedFrame] = None

    def to_json(self):
        json = dict()
        json['request'] = self.request.to_json()
        json['reason'] = self.reason.to_json()
        if self.parent_frame is not None:
            json['parentFrame'] = self.parent_frame.to_json()
        if self.blocked_frame is not None:
            json['blockedFrame'] = self.blocked_frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request=AffectedRequest.from_json(json['request']),
            reason=BlockedByResponseReason.from_json(json['reason']),
            parent_frame=AffectedFrame.from_json(json['parentFrame']) if 'parentFrame' in json else None,
            blocked_frame=AffectedFrame.from_json(json['blockedFrame']) if 'blockedFrame' in json else None,
        )


class HeavyAdResolutionStatus(enum.Enum):
    HEAVY_AD_BLOCKED = "HeavyAdBlocked"
    HEAVY_AD_WARNING = "HeavyAdWarning"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class HeavyAdReason(enum.Enum):
    NETWORK_TOTAL_LIMIT = "NetworkTotalLimit"
    CPU_TOTAL_LIMIT = "CpuTotalLimit"
    CPU_PEAK_LIMIT = "CpuPeakLimit"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class HeavyAdIssueDetails:
    #: The resolution status, either blocking the content or warning.
    resolution: HeavyAdResolutionStatus

    #: The reason the ad was blocked, total network or cpu or peak cpu.
    reason: HeavyAdReason

    #: The frame that was blocked.
    frame: AffectedFrame

    def to_json(self):
        json = dict()
        json['resolution'] = self.resolution.to_json()
        json['reason'] = self.reason.to_json()
        json['frame'] = self.frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            resolution=HeavyAdResolutionStatus.from_json(json['resolution']),
            reason=HeavyAdReason.from_json(json['reason']),
            frame=AffectedFrame.from_json(json['frame']),
        )


class ContentSecurityPolicyViolationType(enum.Enum):
    K_INLINE_VIOLATION = "kInlineViolation"
    K_EVAL_VIOLATION = "kEvalViolation"
    K_URL_VIOLATION = "kURLViolation"
    K_SRI_VIOLATION = "kSRIViolation"
    K_TRUSTED_TYPES_SINK_VIOLATION = "kTrustedTypesSinkViolation"
    K_TRUSTED_TYPES_POLICY_VIOLATION = "kTrustedTypesPolicyViolation"
    K_WASM_EVAL_VIOLATION = "kWasmEvalViolation"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SourceCodeLocation:
    url: str

    line_number: int

    column_number: int

    script_id: typing.Optional[runtime.ScriptId] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        if self.script_id is not None:
            json['scriptId'] = self.script_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
            script_id=runtime.ScriptId.from_json(json['scriptId']) if 'scriptId' in json else None,
        )


@dataclass
class ContentSecurityPolicyIssueDetails:
    #: Specific directive that is violated, causing the CSP issue.
    violated_directive: str

    is_report_only: bool

    content_security_policy_violation_type: ContentSecurityPolicyViolationType

    #: The url not included in allowed sources.
    blocked_url: typing.Optional[str] = None

    frame_ancestor: typing.Optional[AffectedFrame] = None

    source_code_location: typing.Optional[SourceCodeLocation] = None

    violating_node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['violatedDirective'] = self.violated_directive
        json['isReportOnly'] = self.is_report_only
        json['contentSecurityPolicyViolationType'] = self.content_security_policy_violation_type.to_json()
        if self.blocked_url is not None:
            json['blockedURL'] = self.blocked_url
        if self.frame_ancestor is not None:
            json['frameAncestor'] = self.frame_ancestor.to_json()
        if self.source_code_location is not None:
            json['sourceCodeLocation'] = self.source_code_location.to_json()
        if self.violating_node_id is not None:
            json['violatingNodeId'] = self.violating_node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            violated_directive=str(json['violatedDirective']),
            is_report_only=bool(json['isReportOnly']),
            content_security_policy_violation_type=ContentSecurityPolicyViolationType.from_json(json['contentSecurityPolicyViolationType']),
            blocked_url=str(json['blockedURL']) if 'blockedURL' in json else None,
            frame_ancestor=AffectedFrame.from_json(json['frameAncestor']) if 'frameAncestor' in json else None,
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']) if 'sourceCodeLocation' in json else None,
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']) if 'violatingNodeId' in json else None,
        )


class SharedArrayBufferIssueType(enum.Enum):
    TRANSFER_ISSUE = "TransferIssue"
    CREATION_ISSUE = "CreationIssue"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SharedArrayBufferIssueDetails:
    '''
    Details for a issue arising from an SAB being instantiated in, or
    transferred to a context that is not cross-origin isolated.
    '''
    source_code_location: SourceCodeLocation

    is_warning: bool

    type_: SharedArrayBufferIssueType

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['isWarning'] = self.is_warning
        json['type'] = self.type_.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            is_warning=bool(json['isWarning']),
            type_=SharedArrayBufferIssueType.from_json(json['type']),
        )


@dataclass
class LowTextContrastIssueDetails:
    violating_node_id: dom.BackendNodeId

    violating_node_selector: str

    contrast_ratio: float

    threshold_aa: float

    threshold_aaa: float

    font_size: str

    font_weight: str

    def to_json(self):
        json = dict()
        json['violatingNodeId'] = self.violating_node_id.to_json()
        json['violatingNodeSelector'] = self.violating_node_selector
        json['contrastRatio'] = self.contrast_ratio
        json['thresholdAA'] = self.threshold_aa
        json['thresholdAAA'] = self.threshold_aaa
        json['fontSize'] = self.font_size
        json['fontWeight'] = self.font_weight
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']),
            violating_node_selector=str(json['violatingNodeSelector']),
            contrast_ratio=float(json['contrastRatio']),
            threshold_aa=float(json['thresholdAA']),
            threshold_aaa=float(json['thresholdAAA']),
            font_size=str(json['fontSize']),
            font_weight=str(json['fontWeight']),
        )


@dataclass
class CorsIssueDetails:
    '''
    Details for a CORS related issue, e.g. a warning or error related to
    CORS RFC1918 enforcement.
    '''
    cors_error_status: network.CorsErrorStatus

    is_warning: bool

    request: AffectedRequest

    location: typing.Optional[SourceCodeLocation] = None

    initiator_origin: typing.Optional[str] = None

    resource_ip_address_space: typing.Optional[network.IPAddressSpace] = None

    client_security_state: typing.Optional[network.ClientSecurityState] = None

    def to_json(self):
        json = dict()
        json['corsErrorStatus'] = self.cors_error_status.to_json()
        json['isWarning'] = self.is_warning
        json['request'] = self.request.to_json()
        if self.location is not None:
            json['location'] = self.location.to_json()
        if self.initiator_origin is not None:
            json['initiatorOrigin'] = self.initiator_origin
        if self.resource_ip_address_space is not None:
            json['resourceIPAddressSpace'] = self.resource_ip_address_space.to_json()
        if self.client_security_state is not None:
            json['clientSecurityState'] = self.client_security_state.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cors_error_status=network.CorsErrorStatus.from_json(json['corsErrorStatus']),
            is_warning=bool(json['isWarning']),
            request=AffectedRequest.from_json(json['request']),
            location=SourceCodeLocation.from_json(json['location']) if 'location' in json else None,
            initiator_origin=str(json['initiatorOrigin']) if 'initiatorOrigin' in json else None,
            resource_ip_address_space=network.IPAddressSpace.from_json(json['resourceIPAddressSpace']) if 'resourceIPAddressSpace' in json else None,
            client_security_state=network.ClientSecurityState.from_json(json['clientSecurityState']) if 'clientSecurityState' in json else None,
        )


class AttributionReportingIssueType(enum.Enum):
    PERMISSION_POLICY_DISABLED = "PermissionPolicyDisabled"
    UNTRUSTWORTHY_REPORTING_ORIGIN = "UntrustworthyReportingOrigin"
    INSECURE_CONTEXT = "InsecureContext"
    INVALID_HEADER = "InvalidHeader"
    INVALID_REGISTER_TRIGGER_HEADER = "InvalidRegisterTriggerHeader"
    SOURCE_AND_TRIGGER_HEADERS = "SourceAndTriggerHeaders"
    SOURCE_IGNORED = "SourceIgnored"
    TRIGGER_IGNORED = "TriggerIgnored"
    OS_SOURCE_IGNORED = "OsSourceIgnored"
    OS_TRIGGER_IGNORED = "OsTriggerIgnored"
    INVALID_REGISTER_OS_SOURCE_HEADER = "InvalidRegisterOsSourceHeader"
    INVALID_REGISTER_OS_TRIGGER_HEADER = "InvalidRegisterOsTriggerHeader"
    WEB_AND_OS_HEADERS = "WebAndOsHeaders"
    NO_WEB_OR_OS_SUPPORT = "NoWebOrOsSupport"
    NAVIGATION_REGISTRATION_WITHOUT_TRANSIENT_USER_ACTIVATION = "NavigationRegistrationWithoutTransientUserActivation"
    INVALID_INFO_HEADER = "InvalidInfoHeader"
    NO_REGISTER_SOURCE_HEADER = "NoRegisterSourceHeader"
    NO_REGISTER_TRIGGER_HEADER = "NoRegisterTriggerHeader"
    NO_REGISTER_OS_SOURCE_HEADER = "NoRegisterOsSourceHeader"
    NO_REGISTER_OS_TRIGGER_HEADER = "NoRegisterOsTriggerHeader"
    NAVIGATION_REGISTRATION_UNIQUE_SCOPE_ALREADY_SET = "NavigationRegistrationUniqueScopeAlreadySet"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SharedDictionaryError(enum.Enum):
    USE_ERROR_CROSS_ORIGIN_NO_CORS_REQUEST = "UseErrorCrossOriginNoCorsRequest"
    USE_ERROR_DICTIONARY_LOAD_FAILURE = "UseErrorDictionaryLoadFailure"
    USE_ERROR_MATCHING_DICTIONARY_NOT_USED = "UseErrorMatchingDictionaryNotUsed"
    USE_ERROR_UNEXPECTED_CONTENT_DICTIONARY_HEADER = "UseErrorUnexpectedContentDictionaryHeader"
    WRITE_ERROR_COSS_ORIGIN_NO_CORS_REQUEST = "WriteErrorCossOriginNoCorsRequest"
    WRITE_ERROR_DISALLOWED_BY_SETTINGS = "WriteErrorDisallowedBySettings"
    WRITE_ERROR_EXPIRED_RESPONSE = "WriteErrorExpiredResponse"
    WRITE_ERROR_FEATURE_DISABLED = "WriteErrorFeatureDisabled"
    WRITE_ERROR_INSUFFICIENT_RESOURCES = "WriteErrorInsufficientResources"
    WRITE_ERROR_INVALID_MATCH_FIELD = "WriteErrorInvalidMatchField"
    WRITE_ERROR_INVALID_STRUCTURED_HEADER = "WriteErrorInvalidStructuredHeader"
    WRITE_ERROR_NAVIGATION_REQUEST = "WriteErrorNavigationRequest"
    WRITE_ERROR_NO_MATCH_FIELD = "WriteErrorNoMatchField"
    WRITE_ERROR_NON_LIST_MATCH_DEST_FIELD = "WriteErrorNonListMatchDestField"
    WRITE_ERROR_NON_SECURE_CONTEXT = "WriteErrorNonSecureContext"
    WRITE_ERROR_NON_STRING_ID_FIELD = "WriteErrorNonStringIdField"
    WRITE_ERROR_NON_STRING_IN_MATCH_DEST_LIST = "WriteErrorNonStringInMatchDestList"
    WRITE_ERROR_NON_STRING_MATCH_FIELD = "WriteErrorNonStringMatchField"
    WRITE_ERROR_NON_TOKEN_TYPE_FIELD = "WriteErrorNonTokenTypeField"
    WRITE_ERROR_REQUEST_ABORTED = "WriteErrorRequestAborted"
    WRITE_ERROR_SHUTTING_DOWN = "WriteErrorShuttingDown"
    WRITE_ERROR_TOO_LONG_ID_FIELD = "WriteErrorTooLongIdField"
    WRITE_ERROR_UNSUPPORTED_TYPE = "WriteErrorUnsupportedType"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SRIMessageSignatureError(enum.Enum):
    MISSING_SIGNATURE_HEADER = "MissingSignatureHeader"
    MISSING_SIGNATURE_INPUT_HEADER = "MissingSignatureInputHeader"
    INVALID_SIGNATURE_HEADER = "InvalidSignatureHeader"
    INVALID_SIGNATURE_INPUT_HEADER = "InvalidSignatureInputHeader"
    SIGNATURE_HEADER_VALUE_IS_NOT_BYTE_SEQUENCE = "SignatureHeaderValueIsNotByteSequence"
    SIGNATURE_HEADER_VALUE_IS_PARAMETERIZED = "SignatureHeaderValueIsParameterized"
    SIGNATURE_HEADER_VALUE_IS_INCORRECT_LENGTH = "SignatureHeaderValueIsIncorrectLength"
    SIGNATURE_INPUT_HEADER_MISSING_LABEL = "SignatureInputHeaderMissingLabel"
    SIGNATURE_INPUT_HEADER_VALUE_NOT_INNER_LIST = "SignatureInputHeaderValueNotInnerList"
    SIGNATURE_INPUT_HEADER_VALUE_MISSING_COMPONENTS = "SignatureInputHeaderValueMissingComponents"
    SIGNATURE_INPUT_HEADER_INVALID_COMPONENT_TYPE = "SignatureInputHeaderInvalidComponentType"
    SIGNATURE_INPUT_HEADER_INVALID_COMPONENT_NAME = "SignatureInputHeaderInvalidComponentName"
    SIGNATURE_INPUT_HEADER_INVALID_HEADER_COMPONENT_PARAMETER = "SignatureInputHeaderInvalidHeaderComponentParameter"
    SIGNATURE_INPUT_HEADER_INVALID_DERIVED_COMPONENT_PARAMETER = "SignatureInputHeaderInvalidDerivedComponentParameter"
    SIGNATURE_INPUT_HEADER_KEY_ID_LENGTH = "SignatureInputHeaderKeyIdLength"
    SIGNATURE_INPUT_HEADER_INVALID_PARAMETER = "SignatureInputHeaderInvalidParameter"
    SIGNATURE_INPUT_HEADER_MISSING_REQUIRED_PARAMETERS = "SignatureInputHeaderMissingRequiredParameters"
    VALIDATION_FAILED_SIGNATURE_EXPIRED = "ValidationFailedSignatureExpired"
    VALIDATION_FAILED_INVALID_LENGTH = "ValidationFailedInvalidLength"
    VALIDATION_FAILED_SIGNATURE_MISMATCH = "ValidationFailedSignatureMismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AttributionReportingIssueDetails:
    '''
    Details for issues around "Attribution Reporting API" usage.
    Explainer: https://github.com/WICG/attribution-reporting-api
    '''
    violation_type: AttributionReportingIssueType

    request: typing.Optional[AffectedRequest] = None

    violating_node_id: typing.Optional[dom.BackendNodeId] = None

    invalid_parameter: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['violationType'] = self.violation_type.to_json()
        if self.request is not None:
            json['request'] = self.request.to_json()
        if self.violating_node_id is not None:
            json['violatingNodeId'] = self.violating_node_id.to_json()
        if self.invalid_parameter is not None:
            json['invalidParameter'] = self.invalid_parameter
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            violation_type=AttributionReportingIssueType.from_json(json['violationType']),
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']) if 'violatingNodeId' in json else None,
            invalid_parameter=str(json['invalidParameter']) if 'invalidParameter' in json else None,
        )


@dataclass
class QuirksModeIssueDetails:
    '''
    Details for issues about documents in Quirks Mode
    or Limited Quirks Mode that affects page layouting.
    '''
    #: If false, it means the document's mode is "quirks"
    #: instead of "limited-quirks".
    is_limited_quirks_mode: bool

    document_node_id: dom.BackendNodeId

    url: str

    frame_id: page.FrameId

    loader_id: network.LoaderId

    def to_json(self):
        json = dict()
        json['isLimitedQuirksMode'] = self.is_limited_quirks_mode
        json['documentNodeId'] = self.document_node_id.to_json()
        json['url'] = self.url
        json['frameId'] = self.frame_id.to_json()
        json['loaderId'] = self.loader_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            is_limited_quirks_mode=bool(json['isLimitedQuirksMode']),
            document_node_id=dom.BackendNodeId.from_json(json['documentNodeId']),
            url=str(json['url']),
            frame_id=page.FrameId.from_json(json['frameId']),
            loader_id=network.LoaderId.from_json(json['loaderId']),
        )


@dataclass
class NavigatorUserAgentIssueDetails:
    url: str

    location: typing.Optional[SourceCodeLocation] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        if self.location is not None:
            json['location'] = self.location.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            location=SourceCodeLocation.from_json(json['location']) if 'location' in json else None,
        )


@dataclass
class SharedDictionaryIssueDetails:
    shared_dictionary_error: SharedDictionaryError

    request: AffectedRequest

    def to_json(self):
        json = dict()
        json['sharedDictionaryError'] = self.shared_dictionary_error.to_json()
        json['request'] = self.request.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            shared_dictionary_error=SharedDictionaryError.from_json(json['sharedDictionaryError']),
            request=AffectedRequest.from_json(json['request']),
        )


@dataclass
class SRIMessageSignatureIssueDetails:
    error: SRIMessageSignatureError

    request: AffectedRequest

    def to_json(self):
        json = dict()
        json['error'] = self.error.to_json()
        json['request'] = self.request.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error=SRIMessageSignatureError.from_json(json['error']),
            request=AffectedRequest.from_json(json['request']),
        )


class GenericIssueErrorType(enum.Enum):
    FORM_LABEL_FOR_NAME_ERROR = "FormLabelForNameError"
    FORM_DUPLICATE_ID_FOR_INPUT_ERROR = "FormDuplicateIdForInputError"
    FORM_INPUT_WITH_NO_LABEL_ERROR = "FormInputWithNoLabelError"
    FORM_AUTOCOMPLETE_ATTRIBUTE_EMPTY_ERROR = "FormAutocompleteAttributeEmptyError"
    FORM_EMPTY_ID_AND_NAME_ATTRIBUTES_FOR_INPUT_ERROR = "FormEmptyIdAndNameAttributesForInputError"
    FORM_ARIA_LABELLED_BY_TO_NON_EXISTING_ID = "FormAriaLabelledByToNonExistingId"
    FORM_INPUT_ASSIGNED_AUTOCOMPLETE_VALUE_TO_ID_OR_NAME_ATTRIBUTE_ERROR = "FormInputAssignedAutocompleteValueToIdOrNameAttributeError"
    FORM_LABEL_HAS_NEITHER_FOR_NOR_NESTED_INPUT = "FormLabelHasNeitherForNorNestedInput"
    FORM_LABEL_FOR_MATCHES_NON_EXISTING_ID_ERROR = "FormLabelForMatchesNonExistingIdError"
    FORM_INPUT_HAS_WRONG_BUT_WELL_INTENDED_AUTOCOMPLETE_VALUE_ERROR = "FormInputHasWrongButWellIntendedAutocompleteValueError"
    RESPONSE_WAS_BLOCKED_BY_ORB = "ResponseWasBlockedByORB"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class GenericIssueDetails:
    '''
    Depending on the concrete errorType, different properties are set.
    '''
    #: Issues with the same errorType are aggregated in the frontend.
    error_type: GenericIssueErrorType

    frame_id: typing.Optional[page.FrameId] = None

    violating_node_id: typing.Optional[dom.BackendNodeId] = None

    violating_node_attribute: typing.Optional[str] = None

    request: typing.Optional[AffectedRequest] = None

    def to_json(self):
        json = dict()
        json['errorType'] = self.error_type.to_json()
        if self.frame_id is not None:
            json['frameId'] = self.frame_id.to_json()
        if self.violating_node_id is not None:
            json['violatingNodeId'] = self.violating_node_id.to_json()
        if self.violating_node_attribute is not None:
            json['violatingNodeAttribute'] = self.violating_node_attribute
        if self.request is not None:
            json['request'] = self.request.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error_type=GenericIssueErrorType.from_json(json['errorType']),
            frame_id=page.FrameId.from_json(json['frameId']) if 'frameId' in json else None,
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']) if 'violatingNodeId' in json else None,
            violating_node_attribute=str(json['violatingNodeAttribute']) if 'violatingNodeAttribute' in json else None,
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
        )


@dataclass
class DeprecationIssueDetails:
    '''
    This issue tracks information needed to print a deprecation message.
    https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/renderer/core/frame/third_party/blink/renderer/core/frame/deprecation/README.md
    '''
    source_code_location: SourceCodeLocation

    #: One of the deprecation names from third_party/blink/renderer/core/frame/deprecation/deprecation.json5
    type_: str

    affected_frame: typing.Optional[AffectedFrame] = None

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['type'] = self.type_
        if self.affected_frame is not None:
            json['affectedFrame'] = self.affected_frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            type_=str(json['type']),
            affected_frame=AffectedFrame.from_json(json['affectedFrame']) if 'affectedFrame' in json else None,
        )


@dataclass
class BounceTrackingIssueDetails:
    '''
    This issue warns about sites in the redirect chain of a finished navigation
    that may be flagged as trackers and have their state cleared if they don't
    receive a user interaction. Note that in this context 'site' means eTLD+1.
    For example, if the URL ``https://example.test:80/bounce`` was in the
    redirect chain, the site reported would be ``example.test``.
    '''
    tracking_sites: typing.List[str]

    def to_json(self):
        json = dict()
        json['trackingSites'] = [i for i in self.tracking_sites]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            tracking_sites=[str(i) for i in json['trackingSites']],
        )


@dataclass
class CookieDeprecationMetadataIssueDetails:
    '''
    This issue warns about third-party sites that are accessing cookies on the
    current page, and have been permitted due to having a global metadata grant.
    Note that in this context 'site' means eTLD+1. For example, if the URL
    ``https://example.test:80/web_page`` was accessing cookies, the site reported
    would be ``example.test``.
    '''
    allowed_sites: typing.List[str]

    opt_out_percentage: float

    is_opt_out_top_level: bool

    operation: CookieOperation

    def to_json(self):
        json = dict()
        json['allowedSites'] = [i for i in self.allowed_sites]
        json['optOutPercentage'] = self.opt_out_percentage
        json['isOptOutTopLevel'] = self.is_opt_out_top_level
        json['operation'] = self.operation.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            allowed_sites=[str(i) for i in json['allowedSites']],
            opt_out_percentage=float(json['optOutPercentage']),
            is_opt_out_top_level=bool(json['isOptOutTopLevel']),
            operation=CookieOperation.from_json(json['operation']),
        )


class ClientHintIssueReason(enum.Enum):
    META_TAG_ALLOW_LIST_INVALID_ORIGIN = "MetaTagAllowListInvalidOrigin"
    META_TAG_MODIFIED_HTML = "MetaTagModifiedHTML"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class FederatedAuthRequestIssueDetails:
    federated_auth_request_issue_reason: FederatedAuthRequestIssueReason

    def to_json(self):
        json = dict()
        json['federatedAuthRequestIssueReason'] = self.federated_auth_request_issue_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            federated_auth_request_issue_reason=FederatedAuthRequestIssueReason.from_json(json['federatedAuthRequestIssueReason']),
        )


class FederatedAuthRequestIssueReason(enum.Enum):
    '''
    Represents the failure reason when a federated authentication reason fails.
    Should be updated alongside RequestIdTokenStatus in
    third_party/blink/public/mojom/devtools/inspector_issue.mojom to include
    all cases except for success.
    '''
    SHOULD_EMBARGO = "ShouldEmbargo"
    TOO_MANY_REQUESTS = "TooManyRequests"
    WELL_KNOWN_HTTP_NOT_FOUND = "WellKnownHttpNotFound"
    WELL_KNOWN_NO_RESPONSE = "WellKnownNoResponse"
    WELL_KNOWN_INVALID_RESPONSE = "WellKnownInvalidResponse"
    WELL_KNOWN_LIST_EMPTY = "WellKnownListEmpty"
    WELL_KNOWN_INVALID_CONTENT_TYPE = "WellKnownInvalidContentType"
    CONFIG_NOT_IN_WELL_KNOWN = "ConfigNotInWellKnown"
    WELL_KNOWN_TOO_BIG = "WellKnownTooBig"
    CONFIG_HTTP_NOT_FOUND = "ConfigHttpNotFound"
    CONFIG_NO_RESPONSE = "ConfigNoResponse"
    CONFIG_INVALID_RESPONSE = "ConfigInvalidResponse"
    CONFIG_INVALID_CONTENT_TYPE = "ConfigInvalidContentType"
    CLIENT_METADATA_HTTP_NOT_FOUND = "ClientMetadataHttpNotFound"
    CLIENT_METADATA_NO_RESPONSE = "ClientMetadataNoResponse"
    CLIENT_METADATA_INVALID_RESPONSE = "ClientMetadataInvalidResponse"
    CLIENT_METADATA_INVALID_CONTENT_TYPE = "ClientMetadataInvalidContentType"
    IDP_NOT_POTENTIALLY_TRUSTWORTHY = "IdpNotPotentiallyTrustworthy"
    DISABLED_IN_SETTINGS = "DisabledInSettings"
    DISABLED_IN_FLAGS = "DisabledInFlags"
    ERROR_FETCHING_SIGNIN = "ErrorFetchingSignin"
    INVALID_SIGNIN_RESPONSE = "InvalidSigninResponse"
    ACCOUNTS_HTTP_NOT_FOUND = "AccountsHttpNotFound"
    ACCOUNTS_NO_RESPONSE = "AccountsNoResponse"
    ACCOUNTS_INVALID_RESPONSE = "AccountsInvalidResponse"
    ACCOUNTS_LIST_EMPTY = "AccountsListEmpty"
    ACCOUNTS_INVALID_CONTENT_TYPE = "AccountsInvalidContentType"
    ID_TOKEN_HTTP_NOT_FOUND = "IdTokenHttpNotFound"
    ID_TOKEN_NO_RESPONSE = "IdTokenNoResponse"
    ID_TOKEN_INVALID_RESPONSE = "IdTokenInvalidResponse"
    ID_TOKEN_IDP_ERROR_RESPONSE = "IdTokenIdpErrorResponse"
    ID_TOKEN_CROSS_SITE_IDP_ERROR_RESPONSE = "IdTokenCrossSiteIdpErrorResponse"
    ID_TOKEN_INVALID_REQUEST = "IdTokenInvalidRequest"
    ID_TOKEN_INVALID_CONTENT_TYPE = "IdTokenInvalidContentType"
    ERROR_ID_TOKEN = "ErrorIdToken"
    CANCELED = "Canceled"
    RP_PAGE_NOT_VISIBLE = "RpPageNotVisible"
    SILENT_MEDIATION_FAILURE = "SilentMediationFailure"
    THIRD_PARTY_COOKIES_BLOCKED = "ThirdPartyCookiesBlocked"
    NOT_SIGNED_IN_WITH_IDP = "NotSignedInWithIdp"
    MISSING_TRANSIENT_USER_ACTIVATION = "MissingTransientUserActivation"
    REPLACED_BY_ACTIVE_MODE = "ReplacedByActiveMode"
    INVALID_FIELDS_SPECIFIED = "InvalidFieldsSpecified"
    RELYING_PARTY_ORIGIN_IS_OPAQUE = "RelyingPartyOriginIsOpaque"
    TYPE_NOT_MATCHING = "TypeNotMatching"
    UI_DISMISSED_NO_EMBARGO = "UiDismissedNoEmbargo"
    CORS_ERROR = "CorsError"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class FederatedAuthUserInfoRequestIssueDetails:
    federated_auth_user_info_request_issue_reason: FederatedAuthUserInfoRequestIssueReason

    def to_json(self):
        json = dict()
        json['federatedAuthUserInfoRequestIssueReason'] = self.federated_auth_user_info_request_issue_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            federated_auth_user_info_request_issue_reason=FederatedAuthUserInfoRequestIssueReason.from_json(json['federatedAuthUserInfoRequestIssueReason']),
        )


class FederatedAuthUserInfoRequestIssueReason(enum.Enum):
    '''
    Represents the failure reason when a getUserInfo() call fails.
    Should be updated alongside FederatedAuthUserInfoRequestResult in
    third_party/blink/public/mojom/devtools/inspector_issue.mojom.
    '''
    NOT_SAME_ORIGIN = "NotSameOrigin"
    NOT_IFRAME = "NotIframe"
    NOT_POTENTIALLY_TRUSTWORTHY = "NotPotentiallyTrustworthy"
    NO_API_PERMISSION = "NoApiPermission"
    NOT_SIGNED_IN_WITH_IDP = "NotSignedInWithIdp"
    NO_ACCOUNT_SHARING_PERMISSION = "NoAccountSharingPermission"
    INVALID_CONFIG_OR_WELL_KNOWN = "InvalidConfigOrWellKnown"
    INVALID_ACCOUNTS_RESPONSE = "InvalidAccountsResponse"
    NO_RETURNING_USER_FROM_FETCHED_ACCOUNTS = "NoReturningUserFromFetchedAccounts"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ClientHintIssueDetails:
    '''
    This issue tracks client hints related issues. It's used to deprecate old
    features, encourage the use of new ones, and provide general guidance.
    '''
    source_code_location: SourceCodeLocation

    client_hint_issue_reason: ClientHintIssueReason

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['clientHintIssueReason'] = self.client_hint_issue_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            client_hint_issue_reason=ClientHintIssueReason.from_json(json['clientHintIssueReason']),
        )


@dataclass
class FailedRequestInfo:
    #: The URL that failed to load.
    url: str

    #: The failure message for the failed request.
    failure_message: str

    request_id: typing.Optional[network.RequestId] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['failureMessage'] = self.failure_message
        if self.request_id is not None:
            json['requestId'] = self.request_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            failure_message=str(json['failureMessage']),
            request_id=network.RequestId.from_json(json['requestId']) if 'requestId' in json else None,
        )


class PartitioningBlobURLInfo(enum.Enum):
    BLOCKED_CROSS_PARTITION_FETCHING = "BlockedCrossPartitionFetching"
    ENFORCE_NOOPENER_FOR_NAVIGATION = "EnforceNoopenerForNavigation"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PartitioningBlobURLIssueDetails:
    #: The BlobURL that failed to load.
    url: str

    #: Additional information about the Partitioning Blob URL issue.
    partitioning_blob_url_info: PartitioningBlobURLInfo

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['partitioningBlobURLInfo'] = self.partitioning_blob_url_info.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            partitioning_blob_url_info=PartitioningBlobURLInfo.from_json(json['partitioningBlobURLInfo']),
        )


class SelectElementAccessibilityIssueReason(enum.Enum):
    DISALLOWED_SELECT_CHILD = "DisallowedSelectChild"
    DISALLOWED_OPT_GROUP_CHILD = "DisallowedOptGroupChild"
    NON_PHRASING_CONTENT_OPTION_CHILD = "NonPhrasingContentOptionChild"
    INTERACTIVE_CONTENT_OPTION_CHILD = "InteractiveContentOptionChild"
    INTERACTIVE_CONTENT_LEGEND_CHILD = "InteractiveContentLegendChild"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SelectElementAccessibilityIssueDetails:
    '''
    This issue warns about errors in the select element content model.
    '''
    node_id: dom.BackendNodeId

    select_element_accessibility_issue_reason: SelectElementAccessibilityIssueReason

    has_disallowed_attributes: bool

    def to_json(self):
        json = dict()
        json['nodeId'] = self.node_id.to_json()
        json['selectElementAccessibilityIssueReason'] = self.select_element_accessibility_issue_reason.to_json()
        json['hasDisallowedAttributes'] = self.has_disallowed_attributes
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            node_id=dom.BackendNodeId.from_json(json['nodeId']),
            select_element_accessibility_issue_reason=SelectElementAccessibilityIssueReason.from_json(json['selectElementAccessibilityIssueReason']),
            has_disallowed_attributes=bool(json['hasDisallowedAttributes']),
        )


class StyleSheetLoadingIssueReason(enum.Enum):
    LATE_IMPORT_RULE = "LateImportRule"
    REQUEST_FAILED = "RequestFailed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class StylesheetLoadingIssueDetails:
    '''
    This issue warns when a referenced stylesheet couldn't be loaded.
    '''
    #: Source code position that referenced the failing stylesheet.
    source_code_location: SourceCodeLocation

    #: Reason why the stylesheet couldn't be loaded.
    style_sheet_loading_issue_reason: StyleSheetLoadingIssueReason

    #: Contains additional info when the failure was due to a request.
    failed_request_info: typing.Optional[FailedRequestInfo] = None

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['styleSheetLoadingIssueReason'] = self.style_sheet_loading_issue_reason.to_json()
        if self.failed_request_info is not None:
            json['failedRequestInfo'] = self.failed_request_info.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            style_sheet_loading_issue_reason=StyleSheetLoadingIssueReason.from_json(json['styleSheetLoadingIssueReason']),
            failed_request_info=FailedRequestInfo.from_json(json['failedRequestInfo']) if 'failedRequestInfo' in json else None,
        )


class PropertyRuleIssueReason(enum.Enum):
    INVALID_SYNTAX = "InvalidSyntax"
    INVALID_INITIAL_VALUE = "InvalidInitialValue"
    INVALID_INHERITS = "InvalidInherits"
    INVALID_NAME = "InvalidName"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PropertyRuleIssueDetails:
    '''
    This issue warns about errors in property rules that lead to property
    registrations being ignored.
    '''
    #: Source code position of the property rule.
    source_code_location: SourceCodeLocation

    #: Reason why the property rule was discarded.
    property_rule_issue_reason: PropertyRuleIssueReason

    #: The value of the property rule property that failed to parse
    property_value: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['propertyRuleIssueReason'] = self.property_rule_issue_reason.to_json()
        if self.property_value is not None:
            json['propertyValue'] = self.property_value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            property_rule_issue_reason=PropertyRuleIssueReason.from_json(json['propertyRuleIssueReason']),
            property_value=str(json['propertyValue']) if 'propertyValue' in json else None,
        )


class InspectorIssueCode(enum.Enum):
    '''
    A unique identifier for the type of issue. Each type may use one of the
    optional fields in InspectorIssueDetails to convey more specific
    information about the kind of issue.
    '''
    COOKIE_ISSUE = "CookieIssue"
    MIXED_CONTENT_ISSUE = "MixedContentIssue"
    BLOCKED_BY_RESPONSE_ISSUE = "BlockedByResponseIssue"
    HEAVY_AD_ISSUE = "HeavyAdIssue"
    CONTENT_SECURITY_POLICY_ISSUE = "ContentSecurityPolicyIssue"
    SHARED_ARRAY_BUFFER_ISSUE = "SharedArrayBufferIssue"
    LOW_TEXT_CONTRAST_ISSUE = "LowTextContrastIssue"
    CORS_ISSUE = "CorsIssue"
    ATTRIBUTION_REPORTING_ISSUE = "AttributionReportingIssue"
    QUIRKS_MODE_ISSUE = "QuirksModeIssue"
    PARTITIONING_BLOB_URL_ISSUE = "PartitioningBlobURLIssue"
    NAVIGATOR_USER_AGENT_ISSUE = "NavigatorUserAgentIssue"
    GENERIC_ISSUE = "GenericIssue"
    DEPRECATION_ISSUE = "DeprecationIssue"
    CLIENT_HINT_ISSUE = "ClientHintIssue"
    FEDERATED_AUTH_REQUEST_ISSUE = "FederatedAuthRequestIssue"
    BOUNCE_TRACKING_ISSUE = "BounceTrackingIssue"
    COOKIE_DEPRECATION_METADATA_ISSUE = "CookieDeprecationMetadataIssue"
    STYLESHEET_LOADING_ISSUE = "StylesheetLoadingIssue"
    FEDERATED_AUTH_USER_INFO_REQUEST_ISSUE = "FederatedAuthUserInfoRequestIssue"
    PROPERTY_RULE_ISSUE = "PropertyRuleIssue"
    SHARED_DICTIONARY_ISSUE = "SharedDictionaryIssue"
    SELECT_ELEMENT_ACCESSIBILITY_ISSUE = "SelectElementAccessibilityIssue"
    SRI_MESSAGE_SIGNATURE_ISSUE = "SRIMessageSignatureIssue"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class InspectorIssueDetails:
    '''
    This struct holds a list of optional fields with additional information
    specific to the kind of issue. When adding a new issue code, please also
    add a new optional field to this type.
    '''
    cookie_issue_details: typing.Optional[CookieIssueDetails] = None

    mixed_content_issue_details: typing.Optional[MixedContentIssueDetails] = None

    blocked_by_response_issue_details: typing.Optional[BlockedByResponseIssueDetails] = None

    heavy_ad_issue_details: typing.Optional[HeavyAdIssueDetails] = None

    content_security_policy_issue_details: typing.Optional[ContentSecurityPolicyIssueDetails] = None

    shared_array_buffer_issue_details: typing.Optional[SharedArrayBufferIssueDetails] = None

    low_text_contrast_issue_details: typing.Optional[LowTextContrastIssueDetails] = None

    cors_issue_details: typing.Optional[CorsIssueDetails] = None

    attribution_reporting_issue_details: typing.Optional[AttributionReportingIssueDetails] = None

    quirks_mode_issue_details: typing.Optional[QuirksModeIssueDetails] = None

    partitioning_blob_url_issue_details: typing.Optional[PartitioningBlobURLIssueDetails] = None

    navigator_user_agent_issue_details: typing.Optional[NavigatorUserAgentIssueDetails] = None

    generic_issue_details: typing.Optional[GenericIssueDetails] = None

    deprecation_issue_details: typing.Optional[DeprecationIssueDetails] = None

    client_hint_issue_details: typing.Optional[ClientHintIssueDetails] = None

    federated_auth_request_issue_details: typing.Optional[FederatedAuthRequestIssueDetails] = None

    bounce_tracking_issue_details: typing.Optional[BounceTrackingIssueDetails] = None

    cookie_deprecation_metadata_issue_details: typing.Optional[CookieDeprecationMetadataIssueDetails] = None

    stylesheet_loading_issue_details: typing.Optional[StylesheetLoadingIssueDetails] = None

    property_rule_issue_details: typing.Optional[PropertyRuleIssueDetails] = None

    federated_auth_user_info_request_issue_details: typing.Optional[FederatedAuthUserInfoRequestIssueDetails] = None

    shared_dictionary_issue_details: typing.Optional[SharedDictionaryIssueDetails] = None

    select_element_accessibility_issue_details: typing.Optional[SelectElementAccessibilityIssueDetails] = None

    sri_message_signature_issue_details: typing.Optional[SRIMessageSignatureIssueDetails] = None

    def to_json(self):
        json = dict()
        if self.cookie_issue_details is not None:
            json['cookieIssueDetails'] = self.cookie_issue_details.to_json()
        if self.mixed_content_issue_details is not None:
            json['mixedContentIssueDetails'] = self.mixed_content_issue_details.to_json()
        if self.blocked_by_response_issue_details is not None:
            json['blockedByResponseIssueDetails'] = self.blocked_by_response_issue_details.to_json()
        if self.heavy_ad_issue_details is not None:
            json['heavyAdIssueDetails'] = self.heavy_ad_issue_details.to_json()
        if self.content_security_policy_issue_details is not None:
            json['contentSecurityPolicyIssueDetails'] = self.content_security_policy_issue_details.to_json()
        if self.shared_array_buffer_issue_details is not None:
            json['sharedArrayBufferIssueDetails'] = self.shared_array_buffer_issue_details.to_json()
        if self.low_text_contrast_issue_details is not None:
            json['lowTextContrastIssueDetails'] = self.low_text_contrast_issue_details.to_json()
        if self.cors_issue_details is not None:
            json['corsIssueDetails'] = self.cors_issue_details.to_json()
        if self.attribution_reporting_issue_details is not None:
            json['attributionReportingIssueDetails'] = self.attribution_reporting_issue_details.to_json()
        if self.quirks_mode_issue_details is not None:
            json['quirksModeIssueDetails'] = self.quirks_mode_issue_details.to_json()
        if self.partitioning_blob_url_issue_details is not None:
            json['partitioningBlobURLIssueDetails'] = self.partitioning_blob_url_issue_details.to_json()
        if self.navigator_user_agent_issue_details is not None:
            json['navigatorUserAgentIssueDetails'] = self.navigator_user_agent_issue_details.to_json()
        if self.generic_issue_details is not None:
            json['genericIssueDetails'] = self.generic_issue_details.to_json()
        if self.deprecation_issue_details is not None:
            json['deprecationIssueDetails'] = self.deprecation_issue_details.to_json()
        if self.client_hint_issue_details is not None:
            json['clientHintIssueDetails'] = self.client_hint_issue_details.to_json()
        if self.federated_auth_request_issue_details is not None:
            json['federatedAuthRequestIssueDetails'] = self.federated_auth_request_issue_details.to_json()
        if self.bounce_tracking_issue_details is not None:
            json['bounceTrackingIssueDetails'] = self.bounce_tracking_issue_details.to_json()
        if self.cookie_deprecation_metadata_issue_details is not None:
            json['cookieDeprecationMetadataIssueDetails'] = self.cookie_deprecation_metadata_issue_details.to_json()
        if self.stylesheet_loading_issue_details is not None:
            json['stylesheetLoadingIssueDetails'] = self.stylesheet_loading_issue_details.to_json()
        if self.property_rule_issue_details is not None:
            json['propertyRuleIssueDetails'] = self.property_rule_issue_details.to_json()
        if self.federated_auth_user_info_request_issue_details is not None:
            json['federatedAuthUserInfoRequestIssueDetails'] = self.federated_auth_user_info_request_issue_details.to_json()
        if self.shared_dictionary_issue_details is not None:
            json['sharedDictionaryIssueDetails'] = self.shared_dictionary_issue_details.to_json()
        if self.select_element_accessibility_issue_details is not None:
            json['selectElementAccessibilityIssueDetails'] = self.select_element_accessibility_issue_details.to_json()
        if self.sri_message_signature_issue_details is not None:
            json['sriMessageSignatureIssueDetails'] = self.sri_message_signature_issue_details.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cookie_issue_details=CookieIssueDetails.from_json(json['cookieIssueDetails']) if 'cookieIssueDetails' in json else None,
            mixed_content_issue_details=MixedContentIssueDetails.from_json(json['mixedContentIssueDetails']) if 'mixedContentIssueDetails' in json else None,
            blocked_by_response_issue_details=BlockedByResponseIssueDetails.from_json(json['blockedByResponseIssueDetails']) if 'blockedByResponseIssueDetails' in json else None,
            heavy_ad_issue_details=HeavyAdIssueDetails.from_json(json['heavyAdIssueDetails']) if 'heavyAdIssueDetails' in json else None,
            content_security_policy_issue_details=ContentSecurityPolicyIssueDetails.from_json(json['contentSecurityPolicyIssueDetails']) if 'contentSecurityPolicyIssueDetails' in json else None,
            shared_array_buffer_issue_details=SharedArrayBufferIssueDetails.from_json(json['sharedArrayBufferIssueDetails']) if 'sharedArrayBufferIssueDetails' in json else None,
            low_text_contrast_issue_details=LowTextContrastIssueDetails.from_json(json['lowTextContrastIssueDetails']) if 'lowTextContrastIssueDetails' in json else None,
            cors_issue_details=CorsIssueDetails.from_json(json['corsIssueDetails']) if 'corsIssueDetails' in json else None,
            attribution_reporting_issue_details=AttributionReportingIssueDetails.from_json(json['attributionReportingIssueDetails']) if 'attributionReportingIssueDetails' in json else None,
            quirks_mode_issue_details=QuirksModeIssueDetails.from_json(json['quirksModeIssueDetails']) if 'quirksModeIssueDetails' in json else None,
            partitioning_blob_url_issue_details=PartitioningBlobURLIssueDetails.from_json(json['partitioningBlobURLIssueDetails']) if 'partitioningBlobURLIssueDetails' in json else None,
            navigator_user_agent_issue_details=NavigatorUserAgentIssueDetails.from_json(json['navigatorUserAgentIssueDetails']) if 'navigatorUserAgentIssueDetails' in json else None,
            generic_issue_details=GenericIssueDetails.from_json(json['genericIssueDetails']) if 'genericIssueDetails' in json else None,
            deprecation_issue_details=DeprecationIssueDetails.from_json(json['deprecationIssueDetails']) if 'deprecationIssueDetails' in json else None,
            client_hint_issue_details=ClientHintIssueDetails.from_json(json['clientHintIssueDetails']) if 'clientHintIssueDetails' in json else None,
            federated_auth_request_issue_details=FederatedAuthRequestIssueDetails.from_json(json['federatedAuthRequestIssueDetails']) if 'federatedAuthRequestIssueDetails' in json else None,
            bounce_tracking_issue_details=BounceTrackingIssueDetails.from_json(json['bounceTrackingIssueDetails']) if 'bounceTrackingIssueDetails' in json else None,
            cookie_deprecation_metadata_issue_details=CookieDeprecationMetadataIssueDetails.from_json(json['cookieDeprecationMetadataIssueDetails']) if 'cookieDeprecationMetadataIssueDetails' in json else None,
            stylesheet_loading_issue_details=StylesheetLoadingIssueDetails.from_json(json['stylesheetLoadingIssueDetails']) if 'stylesheetLoadingIssueDetails' in json else None,
            property_rule_issue_details=PropertyRuleIssueDetails.from_json(json['propertyRuleIssueDetails']) if 'propertyRuleIssueDetails' in json else None,
            federated_auth_user_info_request_issue_details=FederatedAuthUserInfoRequestIssueDetails.from_json(json['federatedAuthUserInfoRequestIssueDetails']) if 'federatedAuthUserInfoRequestIssueDetails' in json else None,
            shared_dictionary_issue_details=SharedDictionaryIssueDetails.from_json(json['sharedDictionaryIssueDetails']) if 'sharedDictionaryIssueDetails' in json else None,
            select_element_accessibility_issue_details=SelectElementAccessibilityIssueDetails.from_json(json['selectElementAccessibilityIssueDetails']) if 'selectElementAccessibilityIssueDetails' in json else None,
            sri_message_signature_issue_details=SRIMessageSignatureIssueDetails.from_json(json['sriMessageSignatureIssueDetails']) if 'sriMessageSignatureIssueDetails' in json else None,
        )


class IssueId(str):
    '''
    A unique id for a DevTools inspector issue. Allows other entities (e.g.
    exceptions, CDP message, console messages, etc.) to reference an issue.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> IssueId:
        return cls(json)

    def __repr__(self):
        return 'IssueId({})'.format(super().__repr__())


@dataclass
class InspectorIssue:
    '''
    An inspector issue reported from the back-end.
    '''
    code: InspectorIssueCode

    details: InspectorIssueDetails

    #: A unique id for this issue. May be omitted if no other entity (e.g.
    #: exception, CDP message, etc.) is referencing this issue.
    issue_id: typing.Optional[IssueId] = None

    def to_json(self):
        json = dict()
        json['code'] = self.code.to_json()
        json['details'] = self.details.to_json()
        if self.issue_id is not None:
            json['issueId'] = self.issue_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            code=InspectorIssueCode.from_json(json['code']),
            details=InspectorIssueDetails.from_json(json['details']),
            issue_id=IssueId.from_json(json['issueId']) if 'issueId' in json else None,
        )


def get_encoded_response(
        request_id: network.RequestId,
        encoding: str,
        quality: typing.Optional[float] = None,
        size_only: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[str], int, int]]:
    '''
    Returns the response body and size if it were re-encoded with the specified settings. Only
    applies to images.

    :param request_id: Identifier of the network request to get content for.
    :param encoding: The encoding to use.
    :param quality: *(Optional)* The quality of the encoding (0-1). (defaults to 1)
    :param size_only: *(Optional)* Whether to only return the size information (defaults to false).
    :returns: A tuple with the following items:

        0. **body** - *(Optional)* The encoded body as a base64 string. Omitted if sizeOnly is true.
        1. **originalSize** - Size before re-encoding.
        2. **encodedSize** - Size after re-encoding.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['encoding'] = encoding
    if quality is not None:
        params['quality'] = quality
    if size_only is not None:
        params['sizeOnly'] = size_only
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.getEncodedResponse',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['body']) if 'body' in json else None,
        int(json['originalSize']),
        int(json['encodedSize'])
    )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables issues domain, prevents further issues from being reported to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables issues domain, sends the issues collected so far to the client by means of the
    ``issueAdded`` event.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.enable',
    }
    json = yield cmd_dict


def check_contrast(
        report_aaa: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Runs the contrast check for the target page. Found issues are reported
    using Audits.issueAdded event.

    :param report_aaa: *(Optional)* Whether to report WCAG AAA level issues. Default is false.
    '''
    params: T_JSON_DICT = dict()
    if report_aaa is not None:
        params['reportAAA'] = report_aaa
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.checkContrast',
        'params': params,
    }
    json = yield cmd_dict


def check_forms_issues() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[GenericIssueDetails]]:
    '''
    Runs the form issues check for the target page. Found issues are reported
    using Audits.issueAdded event.

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.checkFormsIssues',
    }
    json = yield cmd_dict
    return [GenericIssueDetails.from_json(i) for i in json['formIssues']]


@event_class('Audits.issueAdded')
@dataclass
class IssueAdded:
    issue: InspectorIssue

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> IssueAdded:
        return cls(
            issue=InspectorIssue.from_json(json['issue'])
        )

# === NexusCore/openenv\Lib\site-packages\git\cmd.py ===
# Copyright (C) 2008, 2009 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

from __future__ import annotations

__all__ = ["GitMeta", "Git"]

import contextlib
import io
import itertools
import logging
import os
import re
import signal
import subprocess
from subprocess import DEVNULL, PIPE, Popen
import sys
from textwrap import dedent
import threading
import warnings

from git.compat import defenc, force_bytes, safe_decode
from git.exc import (
    CommandError,
    GitCommandError,
    GitCommandNotFound,
    UnsafeOptionError,
    UnsafeProtocolError,
)
from git.util import (
    cygpath,
    expand_path,
    is_cygwin_git,
    patch_env,
    remove_password_if_present,
    stream_copy,
)

# typing ---------------------------------------------------------------------------

from typing import (
    Any,
    AnyStr,
    BinaryIO,
    Callable,
    Dict,
    IO,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    TYPE_CHECKING,
    TextIO,
    Tuple,
    Union,
    cast,
    overload,
)

from git.types import Literal, PathLike, TBD

if TYPE_CHECKING:
    from git.diff import DiffIndex
    from git.repo.base import Repo

# ---------------------------------------------------------------------------------

execute_kwargs = {
    "istream",
    "with_extended_output",
    "with_exceptions",
    "as_process",
    "output_stream",
    "stdout_as_string",
    "kill_after_timeout",
    "with_stdout",
    "universal_newlines",
    "shell",
    "env",
    "max_chunk_size",
    "strip_newline_in_stdout",
}

_logger = logging.getLogger(__name__)


# ==============================================================================
## @name Utilities
# ------------------------------------------------------------------------------
# Documentation
## @{


def handle_process_output(
    process: "Git.AutoInterrupt" | Popen,
    stdout_handler: Union[
        None,
        Callable[[AnyStr], None],
        Callable[[List[AnyStr]], None],
        Callable[[bytes, "Repo", "DiffIndex"], None],
    ],
    stderr_handler: Union[None, Callable[[AnyStr], None], Callable[[List[AnyStr]], None]],
    finalizer: Union[None, Callable[[Union[Popen, "Git.AutoInterrupt"]], None]] = None,
    decode_streams: bool = True,
    kill_after_timeout: Union[None, float] = None,
) -> None:
    R"""Register for notifications to learn that process output is ready to read, and
    dispatch lines to the respective line handlers.

    This function returns once the finalizer returns.

    :param process:
        :class:`subprocess.Popen` instance.

    :param stdout_handler:
        f(stdout_line_string), or ``None``.

    :param stderr_handler:
        f(stderr_line_string), or ``None``.

    :param finalizer:
        f(proc) - wait for proc to finish.

    :param decode_streams:
        Assume stdout/stderr streams are binary and decode them before pushing their
        contents to handlers.

        This defaults to ``True``. Set it to ``False`` if:

        - ``universal_newlines == True``, as then streams are in text mode, or
        - decoding must happen later, such as for :class:`~git.diff.Diff`\s.

    :param kill_after_timeout:
        :class:`float` or ``None``, Default = ``None``

        To specify a timeout in seconds for the git command, after which the process
        should be killed.
    """

    # Use 2 "pump" threads and wait for both to finish.
    def pump_stream(
        cmdline: List[str],
        name: str,
        stream: Union[BinaryIO, TextIO],
        is_decode: bool,
        handler: Union[None, Callable[[Union[bytes, str]], None]],
    ) -> None:
        try:
            for line in stream:
                if handler:
                    if is_decode:
                        assert isinstance(line, bytes)
                        line_str = line.decode(defenc)
                        handler(line_str)
                    else:
                        handler(line)

        except Exception as ex:
            _logger.error(f"Pumping {name!r} of cmd({remove_password_if_present(cmdline)}) failed due to: {ex!r}")
            if "I/O operation on closed file" not in str(ex):
                # Only reraise if the error was not due to the stream closing.
                raise CommandError([f"<{name}-pump>"] + remove_password_if_present(cmdline), ex) from ex
        finally:
            stream.close()

    if hasattr(process, "proc"):
        process = cast("Git.AutoInterrupt", process)
        cmdline: str | Tuple[str, ...] | List[str] = getattr(process.proc, "args", "")
        p_stdout = process.proc.stdout if process.proc else None
        p_stderr = process.proc.stderr if process.proc else None
    else:
        process = cast(Popen, process)  # type: ignore[redundant-cast]
        cmdline = getattr(process, "args", "")
        p_stdout = process.stdout
        p_stderr = process.stderr

    if not isinstance(cmdline, (tuple, list)):
        cmdline = cmdline.split()

    pumps: List[Tuple[str, IO, Callable[..., None] | None]] = []
    if p_stdout:
        pumps.append(("stdout", p_stdout, stdout_handler))
    if p_stderr:
        pumps.append(("stderr", p_stderr, stderr_handler))

    threads: List[threading.Thread] = []

    for name, stream, handler in pumps:
        t = threading.Thread(target=pump_stream, args=(cmdline, name, stream, decode_streams, handler))
        t.daemon = True
        t.start()
        threads.append(t)

    # FIXME: Why join? Will block if stdin needs feeding...
    for t in threads:
        t.join(timeout=kill_after_timeout)
        if t.is_alive():
            if isinstance(process, Git.AutoInterrupt):
                process._terminate()
            else:  # Don't want to deal with the other case.
                raise RuntimeError(
                    "Thread join() timed out in cmd.handle_process_output()."
                    f" kill_after_timeout={kill_after_timeout} seconds"
                )
            if stderr_handler:
                error_str: Union[str, bytes] = (
                    "error: process killed because it timed out." f" kill_after_timeout={kill_after_timeout} seconds"
                )
                if not decode_streams and isinstance(p_stderr, BinaryIO):
                    # Assume stderr_handler needs binary input.
                    error_str = cast(str, error_str)
                    error_str = error_str.encode()
                # We ignore typing on the next line because mypy does not like the way
                # we inferred that stderr takes str or bytes.
                stderr_handler(error_str)  # type: ignore[arg-type]

    if finalizer:
        finalizer(process)


safer_popen: Callable[..., Popen]

if sys.platform == "win32":

    def _safer_popen_windows(
        command: Union[str, Sequence[Any]],
        *,
        shell: bool = False,
        env: Optional[Mapping[str, str]] = None,
        **kwargs: Any,
    ) -> Popen:
        """Call :class:`subprocess.Popen` on Windows but don't include a CWD in the
        search.

        This avoids an untrusted search path condition where a file like ``git.exe`` in
        a malicious repository would be run when GitPython operates on the repository.
        The process using GitPython may have an untrusted repository's working tree as
        its current working directory. Some operations may temporarily change to that
        directory before running a subprocess. In addition, while by default GitPython
        does not run external commands with a shell, it can be made to do so, in which
        case the CWD of the subprocess, which GitPython usually sets to a repository
        working tree, can itself be searched automatically by the shell. This wrapper
        covers all those cases.

        :note:
            This currently works by setting the
            :envvar:`NoDefaultCurrentDirectoryInExePath` environment variable during
            subprocess creation. It also takes care of passing Windows-specific process
            creation flags, but that is unrelated to path search.

        :note:
            The current implementation contains a race condition on :attr:`os.environ`.
            GitPython isn't thread-safe, but a program using it on one thread should
            ideally be able to mutate :attr:`os.environ` on another, without
            unpredictable results. See comments in:
            https://github.com/gitpython-developers/GitPython/pull/1650
        """
        # CREATE_NEW_PROCESS_GROUP is needed for some ways of killing it afterwards.
        # https://docs.python.org/3/library/subprocess.html#subprocess.Popen.send_signal
        # https://docs.python.org/3/library/subprocess.html#subprocess.CREATE_NEW_PROCESS_GROUP
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP

        # When using a shell, the shell is the direct subprocess, so the variable must
        # be set in its environment, to affect its search behavior.
        if shell:
            # The original may be immutable, or the caller may reuse it. Mutate a copy.
            env = {} if env is None else dict(env)
            env["NoDefaultCurrentDirectoryInExePath"] = "1"  # The "1" can be an value.

        # When not using a shell, the current process does the search in a
        # CreateProcessW API call, so the variable must be set in our environment. With
        # a shell, that's unnecessary if https://github.com/python/cpython/issues/101283
        # is patched. In Python versions where it is unpatched, and in the rare case the
        # ComSpec environment variable is unset, the search for the shell itself is
        # unsafe. Setting NoDefaultCurrentDirectoryInExePath in all cases, as done here,
        # is simpler and protects against that. (As above, the "1" can be any value.)
        with patch_env("NoDefaultCurrentDirectoryInExePath", "1"):
            return Popen(
                command,
                shell=shell,
                env=env,
                creationflags=creationflags,
                **kwargs,
            )

    safer_popen = _safer_popen_windows
else:
    safer_popen = Popen


def dashify(string: str) -> str:
    return string.replace("_", "-")


def slots_to_dict(self: "Git", exclude: Sequence[str] = ()) -> Dict[str, Any]:
    return {s: getattr(self, s) for s in self.__slots__ if s not in exclude}


def dict_to_slots_and__excluded_are_none(self: object, d: Mapping[str, Any], excluded: Sequence[str] = ()) -> None:
    for k, v in d.items():
        setattr(self, k, v)
    for k in excluded:
        setattr(self, k, None)


## -- End Utilities -- @}

_USE_SHELL_DEFAULT_MESSAGE = (
    "Git.USE_SHELL is deprecated, because only its default value of False is safe. "
    "It will be removed in a future release."
)

_USE_SHELL_DANGER_MESSAGE = (
    "Setting Git.USE_SHELL to True is unsafe and insecure, as the effect of special "
    "shell syntax cannot usually be accounted for. This can result in a command "
    "injection vulnerability and arbitrary code execution. Git.USE_SHELL is deprecated "
    "and will be removed in a future release."
)


def _warn_use_shell(extra_danger: bool) -> None:
    warnings.warn(
        _USE_SHELL_DANGER_MESSAGE if extra_danger else _USE_SHELL_DEFAULT_MESSAGE,
        DeprecationWarning,
        stacklevel=3,
    )


class _GitMeta(type):
    """Metaclass for :class:`Git`.

    This helps issue :class:`DeprecationWarning` if :attr:`Git.USE_SHELL` is used.
    """

    def __getattribute(cls, name: str) -> Any:
        if name == "USE_SHELL":
            _warn_use_shell(False)
        return super().__getattribute__(name)

    def __setattr(cls, name: str, value: Any) -> Any:
        if name == "USE_SHELL":
            _warn_use_shell(value)
        super().__setattr__(name, value)

    if not TYPE_CHECKING:
        # To preserve static checking for undefined/misspelled attributes while letting
        # the methods' bodies be type-checked, these are defined as non-special methods,
        # then bound to special names out of view of static type checkers. (The original
        # names invoke name mangling (leading "__") to avoid confusion in other scopes.)
        __getattribute__ = __getattribute
        __setattr__ = __setattr


GitMeta = _GitMeta
"""Alias of :class:`Git`'s metaclass, whether it is :class:`type` or a custom metaclass.

Whether the :class:`Git` class has the default :class:`type` as its metaclass or uses a
custom metaclass is not documented and may change at any time. This statically checkable
metaclass alias is equivalent at runtime to ``type(Git)``. This should almost never be
used. Code that benefits from it is likely to be remain brittle even if it is used.

In view of the :class:`Git` class's intended use and :class:`Git` objects' dynamic
callable attributes representing git subcommands, it rarely makes sense to inherit from
:class:`Git` at all. Using :class:`Git` in multiple inheritance can be especially tricky
to do correctly. Attempting uses of :class:`Git` where its metaclass is relevant, such
as when a sibling class has an unrelated metaclass and a shared lower bound metaclass
might have to be introduced to solve a metaclass conflict, is not recommended.

:note:
    The correct static type of the :class:`Git` class itself, and any subclasses, is
    ``Type[Git]``. (This can be written as ``type[Git]`` in Python 3.9 later.)

    :class:`GitMeta` should never be used in any annotation where ``Type[Git]`` is
    intended or otherwise possible to use. This alias is truly only for very rare and
    inherently precarious situations where it is necessary to deal with the metaclass
    explicitly.
"""


class Git(metaclass=_GitMeta):
    """The Git class manages communication with the Git binary.

    It provides a convenient interface to calling the Git binary, such as in::

     g = Git( git_dir )
     g.init()                   # calls 'git init' program
     rval = g.ls_files()        # calls 'git ls-files' program

    Debugging:

    * Set the :envvar:`GIT_PYTHON_TRACE` environment variable to print each invocation
      of the command to stdout.
    * Set its value to ``full`` to see details about the returned values.
    """

    __slots__ = (
        "_working_dir",
        "cat_file_all",
        "cat_file_header",
        "_version_info",
        "_version_info_token",
        "_git_options",
        "_persistent_git_options",
        "_environment",
    )

    _excluded_ = (
        "cat_file_all",
        "cat_file_header",
        "_version_info",
        "_version_info_token",
    )

    re_unsafe_protocol = re.compile(r"(.+)::.+")

    def __getstate__(self) -> Dict[str, Any]:
        return slots_to_dict(self, exclude=self._excluded_)

    def __setstate__(self, d: Dict[str, Any]) -> None:
        dict_to_slots_and__excluded_are_none(self, d, excluded=self._excluded_)

    # CONFIGURATION

    git_exec_name = "git"
    """Default git command that should work on Linux, Windows, and other systems."""

    GIT_PYTHON_TRACE = os.environ.get("GIT_PYTHON_TRACE", False)
    """Enables debugging of GitPython's git commands."""

    USE_SHELL: bool = False
    """Deprecated. If set to ``True``, a shell will be used when executing git commands.

    Code that uses ``USE_SHELL = True`` or that passes ``shell=True`` to any GitPython
    functions should be updated to use the default value of ``False`` instead. ``True``
    is unsafe unless the effect of syntax treated specially by the shell is fully
    considered and accounted for, which is not possible under most circumstances. As
    detailed below, it is also no longer needed, even where it had been in the past.

    It is in many if not most cases a command injection vulnerability for an application
    to set :attr:`USE_SHELL` to ``True``. Any attacker who can cause a specially crafted
    fragment of text to make its way into any part of any argument to any git command
    (including paths, branch names, etc.) can cause the shell to read and write
    arbitrary files and execute arbitrary commands. Innocent input may also accidentally
    contain special shell syntax, leading to inadvertent malfunctions.

    In addition, how a value of ``True`` interacts with some aspects of GitPython's
    operation is not precisely specified and may change without warning, even before
    GitPython 4.0.0 when :attr:`USE_SHELL` may be removed. This includes:

    * Whether or how GitPython automatically customizes the shell environment.

    * Whether, outside of Windows (where :class:`subprocess.Popen` supports lists of
      separate arguments even when ``shell=True``), this can be used with any GitPython
      functionality other than direct calls to the :meth:`execute` method.

    * Whether any GitPython feature that runs git commands ever attempts to partially
      sanitize data a shell may treat specially. Currently this is not done.

    Prior to GitPython 2.0.8, this had a narrow purpose in suppressing console windows
    in graphical Windows applications. In 2.0.8 and higher, it provides no benefit, as
    GitPython solves that problem more robustly and safely by using the
    ``CREATE_NO_WINDOW`` process creation flag on Windows.

    Because Windows path search differs subtly based on whether a shell is used, in rare
    cases changing this from ``True`` to ``False`` may keep an unusual git "executable",
    such as a batch file, from being found. To fix this, set the command name or full
    path in the :envvar:`GIT_PYTHON_GIT_EXECUTABLE` environment variable or pass the
    full path to :func:`git.refresh` (or invoke the script using a ``.exe`` shim).

    Further reading:

    * :meth:`Git.execute` (on the ``shell`` parameter).
    * https://github.com/gitpython-developers/GitPython/commit/0d9390866f9ce42870d3116094cd49e0019a970a
    * https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags
    * https://github.com/python/cpython/issues/91558#issuecomment-1100942950
    * https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw
    """

    _git_exec_env_var = "GIT_PYTHON_GIT_EXECUTABLE"
    _refresh_env_var = "GIT_PYTHON_REFRESH"

    GIT_PYTHON_GIT_EXECUTABLE = None
    """Provide the full path to the git executable. Otherwise it assumes git is in the
    executable search path.

    :note:
        The git executable is actually found during the refresh step in the top level
        ``__init__``. It can also be changed by explicitly calling :func:`git.refresh`.
    """

    _refresh_token = object()  # Since None would match an initial _version_info_token.

    @classmethod
    def refresh(cls, path: Union[None, PathLike] = None) -> bool:
        """Update information about the git executable :class:`Git` objects will use.

        Called by the :func:`git.refresh` function in the top level ``__init__``.

        :param path:
            Optional path to the git executable. If not absolute, it is resolved
            immediately, relative to the current directory. (See note below.)

        :note:
            The top-level :func:`git.refresh` should be preferred because it calls this
            method and may also update other state accordingly.

        :note:
            There are three different ways to specify the command that refreshing causes
            to be used for git:

            1. Pass no `path` argument and do not set the
               :envvar:`GIT_PYTHON_GIT_EXECUTABLE` environment variable. The command
               name ``git`` is used. It is looked up in a path search by the system, in
               each command run (roughly similar to how git is found when running
               ``git`` commands manually). This is usually the desired behavior.

            2. Pass no `path` argument but set the :envvar:`GIT_PYTHON_GIT_EXECUTABLE`
               environment variable. The command given as the value of that variable is
               used. This may be a simple command or an arbitrary path. It is looked up
               in each command run. Setting :envvar:`GIT_PYTHON_GIT_EXECUTABLE` to
               ``git`` has the same effect as not setting it.

            3. Pass a `path` argument. This path, if not absolute, is immediately
               resolved, relative to the current directory. This resolution occurs at
               the time of the refresh. When git commands are run, they are run using
               that previously resolved path. If a `path` argument is passed, the
               :envvar:`GIT_PYTHON_GIT_EXECUTABLE` environment variable is not
               consulted.

        :note:
            Refreshing always sets the :attr:`Git.GIT_PYTHON_GIT_EXECUTABLE` class
            attribute, which can be read on the :class:`Git` class or any of its
            instances to check what command is used to run git. This attribute should
            not be confused with the related :envvar:`GIT_PYTHON_GIT_EXECUTABLE`
            environment variable. The class attribute is set no matter how refreshing is
            performed.
        """
        # Discern which path to refresh with.
        if path is not None:
            new_git = os.path.expanduser(path)
            new_git = os.path.abspath(new_git)
        else:
            new_git = os.environ.get(cls._git_exec_env_var, cls.git_exec_name)

        # Keep track of the old and new git executable path.
        old_git = cls.GIT_PYTHON_GIT_EXECUTABLE
        old_refresh_token = cls._refresh_token
        cls.GIT_PYTHON_GIT_EXECUTABLE = new_git
        cls._refresh_token = object()

        # Test if the new git executable path is valid. A GitCommandNotFound error is
        # raised by us. A PermissionError is raised if the git executable cannot be
        # executed for whatever reason.
        has_git = False
        try:
            cls().version()
            has_git = True
        except (GitCommandNotFound, PermissionError):
            pass

        # Warn or raise exception if test failed.
        if not has_git:
            err = (
                dedent(
                    """\
                Bad git executable.
                The git executable must be specified in one of the following ways:
                    - be included in your $PATH
                    - be set via $%s
                    - explicitly set via git.refresh(<full-path-to-git-executable>)
                """
                )
                % cls._git_exec_env_var
            )

            # Revert to whatever the old_git was.
            cls.GIT_PYTHON_GIT_EXECUTABLE = old_git
            cls._refresh_token = old_refresh_token

            if old_git is None:
                # On the first refresh (when GIT_PYTHON_GIT_EXECUTABLE is None) we only
                # are quiet, warn, or error depending on the GIT_PYTHON_REFRESH value.

                # Determine what the user wants to happen during the initial refresh. We
                # expect GIT_PYTHON_REFRESH to either be unset or be one of the
                # following values:
                #
                #   0|q|quiet|s|silence|silent|n|none
                #   1|w|warn|warning|l|log
                #   2|r|raise|e|error|exception

                mode = os.environ.get(cls._refresh_env_var, "raise").lower()

                quiet = ["quiet", "q", "silence", "s", "silent", "none", "n", "0"]
                warn = ["warn", "w", "warning", "log", "l", "1"]
                error = ["error", "e", "exception", "raise", "r", "2"]

                if mode in quiet:
                    pass
                elif mode in warn or mode in error:
                    err = dedent(
                        """\
                        %s
                        All git commands will error until this is rectified.

                        This initial message can be silenced or aggravated in the future by setting the
                        $%s environment variable. Use one of the following values:
                            - %s: for no message or exception
                            - %s: for a warning message (logging level CRITICAL, displayed by default)
                            - %s: for a raised exception

                        Example:
                            export %s=%s
                        """
                    ) % (
                        err,
                        cls._refresh_env_var,
                        "|".join(quiet),
                        "|".join(warn),
                        "|".join(error),
                        cls._refresh_env_var,
                        quiet[0],
                    )

                    if mode in warn:
                        _logger.critical(err)
                    else:
                        raise ImportError(err)
                else:
                    err = dedent(
                        """\
                        %s environment variable has been set but it has been set with an invalid value.

                        Use only the following values:
                            - %s: for no message or exception
                            - %s: for a warning message (logging level CRITICAL, displayed by default)
                            - %s: for a raised exception
                        """
                    ) % (
                        cls._refresh_env_var,
                        "|".join(quiet),
                        "|".join(warn),
                        "|".join(error),
                    )
                    raise ImportError(err)

                # We get here if this was the initial refresh and the refresh mode was
                # not error. Go ahead and set the GIT_PYTHON_GIT_EXECUTABLE such that we
                # discern the difference between the first refresh at import time
                # and subsequent calls to git.refresh or this refresh method.
                cls.GIT_PYTHON_GIT_EXECUTABLE = cls.git_exec_name
            else:
                # After the first refresh (when GIT_PYTHON_GIT_EXECUTABLE is no longer
                # None) we raise an exception.
                raise GitCommandNotFound(new_git, err)

        return has_git

    @classmethod
    def is_cygwin(cls) -> bool:
        return is_cygwin_git(cls.GIT_PYTHON_GIT_EXECUTABLE)

    @overload
    @classmethod
    def polish_url(cls, url: str, is_cygwin: Literal[False] = ...) -> str: ...

    @overload
    @classmethod
    def polish_url(cls, url: str, is_cygwin: Union[None, bool] = None) -> str: ...

    @classmethod
    def polish_url(cls, url: str, is_cygwin: Union[None, bool] = None) -> PathLike:
        """Remove any backslashes from URLs to be written in config files.

        Windows might create config files containing paths with backslashes, but git
        stops liking them as it will escape the backslashes. Hence we undo the escaping
        just to be sure.
        """
        if is_cygwin is None:
            is_cygwin = cls.is_cygwin()

        if is_cygwin:
            url = cygpath(url)
        else:
            url = os.path.expandvars(url)
            if url.startswith("~"):
                url = os.path.expanduser(url)
            url = url.replace("\\\\", "\\").replace("\\", "/")
        return url

    @classmethod
    def check_unsafe_protocols(cls, url: str) -> None:
        """Check for unsafe protocols.

        Apart from the usual protocols (http, git, ssh), Git allows "remote helpers"
        that have the form ``<transport>::<address>``. One of these helpers (``ext::``)
        can be used to invoke any arbitrary command.

        See:

        - https://git-scm.com/docs/gitremote-helpers
        - https://git-scm.com/docs/git-remote-ext
        """
        match = cls.re_unsafe_protocol.match(url)
        if match:
            protocol = match.group(1)
            raise UnsafeProtocolError(
                f"The `{protocol}::` protocol looks suspicious, use `allow_unsafe_protocols=True` to allow it."
            )

    @classmethod
    def check_unsafe_options(cls, options: List[str], unsafe_options: List[str]) -> None:
        """Check for unsafe options.

        Some options that are passed to ``git <command>`` can be used to execute
        arbitrary commands. These are blocked by default.
        """
        # Options can be of the form `foo`, `--foo bar`, or `--foo=bar`, so we need to
        # check if they start with "--foo" or if they are equal to "foo".
        bare_unsafe_options = [option.lstrip("-") for option in unsafe_options]
        for option in options:
            for unsafe_option, bare_option in zip(unsafe_options, bare_unsafe_options):
                if option.startswith(unsafe_option) or option == bare_option:
                    raise UnsafeOptionError(
                        f"{unsafe_option} is not allowed, use `allow_unsafe_options=True` to allow it."
                    )

    class AutoInterrupt:
        """Process wrapper that terminates the wrapped process on finalization.

        This kills/interrupts the stored process instance once this instance goes out of
        scope. It is used to prevent processes piling up in case iterators stop reading.

        All attributes are wired through to the contained process object.

        The wait method is overridden to perform automatic status code checking and
        possibly raise.
        """

        __slots__ = ("proc", "args", "status")

        # If this is non-zero it will override any status code during _terminate, used
        # to prevent race conditions in testing.
        _status_code_if_terminate: int = 0

        def __init__(self, proc: Union[None, subprocess.Popen], args: Any) -> None:
            self.proc = proc
            self.args = args
            self.status: Union[int, None] = None

        def _terminate(self) -> None:
            """Terminate the underlying process."""
            if self.proc is None:
                return

            proc = self.proc
            self.proc = None
            if proc.stdin:
                proc.stdin.close()
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()
            # Did the process finish already so we have a return code?
            try:
                if proc.poll() is not None:
                    self.status = self._status_code_if_terminate or proc.poll()
                    return
            except OSError as ex:
                _logger.info("Ignored error after process had died: %r", ex)

            # It can be that nothing really exists anymore...
            if os is None or getattr(os, "kill", None) is None:
                return

            # Try to kill it.
            try:
                proc.terminate()
                status = proc.wait()  # Ensure the process goes away.

                self.status = self._status_code_if_terminate or status
            except OSError as ex:
                _logger.info("Ignored error after process had died: %r", ex)
            # END exception handling

        def __del__(self) -> None:
            self._terminate()

        def __getattr__(self, attr: str) -> Any:
            return getattr(self.proc, attr)

        # TODO: Bad choice to mimic `proc.wait()` but with different args.
        def wait(self, stderr: Union[None, str, bytes] = b"") -> int:
            """Wait for the process and return its status code.

            :param stderr:
                Previously read value of stderr, in case stderr is already closed.

            :warn:
                May deadlock if output or error pipes are used and not handled
                separately.

            :raise git.exc.GitCommandError:
                If the return status is not 0.
            """
            if stderr is None:
                stderr_b = b""
            stderr_b = force_bytes(data=stderr, encoding="utf-8")
            status: Union[int, None]
            if self.proc is not None:
                status = self.proc.wait()
                p_stderr = self.proc.stderr
            else:  # Assume the underlying proc was killed earlier or never existed.
                status = self.status
                p_stderr = None

            def read_all_from_possibly_closed_stream(stream: Union[IO[bytes], None]) -> bytes:
                if stream:
                    try:
                        return stderr_b + force_bytes(stream.read())
                    except (OSError, ValueError):
                        return stderr_b or b""
                else:
                    return stderr_b or b""

            # END status handling

            if status != 0:
                errstr = read_all_from_possibly_closed_stream(p_stderr)
                _logger.debug("AutoInterrupt wait stderr: %r" % (errstr,))
                raise GitCommandError(remove_password_if_present(self.args), status, errstr)
            return status

    # END auto interrupt

    class CatFileContentStream:
        """Object representing a sized read-only stream returning the contents of
        an object.

        This behaves like a stream, but counts the data read and simulates an empty
        stream once our sized content region is empty.

        If not all data are read to the end of the object's lifetime, we read the
        rest to ensure the underlying stream continues to work.
        """

        __slots__ = ("_stream", "_nbr", "_size")

        def __init__(self, size: int, stream: IO[bytes]) -> None:
            self._stream = stream
            self._size = size
            self._nbr = 0  # Number of bytes read.

            # Special case: If the object is empty, has null bytes, get the final
            # newline right away.
            if size == 0:
                stream.read(1)
            # END handle empty streams

        def read(self, size: int = -1) -> bytes:
            bytes_left = self._size - self._nbr
            if bytes_left == 0:
                return b""
            if size > -1:
                # Ensure we don't try to read past our limit.
                size = min(bytes_left, size)
            else:
                # They try to read all, make sure it's not more than what remains.
                size = bytes_left
            # END check early depletion
            data = self._stream.read(size)
            self._nbr += len(data)

            # Check for depletion, read our final byte to make the stream usable by
            # others.
            if self._size - self._nbr == 0:
                self._stream.read(1)  # final newline
            # END finish reading
            return data

        def readline(self, size: int = -1) -> bytes:
            if self._nbr == self._size:
                return b""

            # Clamp size to lowest allowed value.
            bytes_left = self._size - self._nbr
            if size > -1:
                size = min(bytes_left, size)
            else:
                size = bytes_left
            # END handle size

            data = self._stream.readline(size)
            self._nbr += len(data)

            # Handle final byte.
            if self._size - self._nbr == 0:
                self._stream.read(1)
            # END finish reading

            return data

        def readlines(self, size: int = -1) -> List[bytes]:
            if self._nbr == self._size:
                return []

            # Leave all additional logic to our readline method, we just check the size.
            out = []
            nbr = 0
            while True:
                line = self.readline()
                if not line:
                    break
                out.append(line)
                if size > -1:
                    nbr += len(line)
                    if nbr > size:
                        break
                # END handle size constraint
            # END readline loop
            return out

        # skipcq: PYL-E0301
        def __iter__(self) -> "Git.CatFileContentStream":
            return self

        def __next__(self) -> bytes:
            line = self.readline()
            if not line:
                raise StopIteration

            return line

        next = __next__

        def __del__(self) -> None:
            bytes_left = self._size - self._nbr
            if bytes_left:
                # Read and discard - seeking is impossible within a stream.
                # This includes any terminating newline.
                self._stream.read(bytes_left + 1)
            # END handle incomplete read

    def __init__(self, working_dir: Union[None, PathLike] = None) -> None:
        """Initialize this instance with:

        :param working_dir:
            Git directory we should work in. If ``None``, we always work in the current
            directory as returned by :func:`os.getcwd`.
            This is meant to be the working tree directory if available, or the
            ``.git`` directory in case of bare repositories.
        """
        super().__init__()
        self._working_dir = expand_path(working_dir)
        self._git_options: Union[List[str], Tuple[str, ...]] = ()
        self._persistent_git_options: List[str] = []

        # Extra environment variables to pass to git commands
        self._environment: Dict[str, str] = {}

        # Cached version slots
        self._version_info: Union[Tuple[int, ...], None] = None
        self._version_info_token: object = None

        # Cached command slots
        self.cat_file_header: Union[None, TBD] = None
        self.cat_file_all: Union[None, TBD] = None

    def __getattribute__(self, name: str) -> Any:
        if name == "USE_SHELL":
            _warn_use_shell(False)
        return super().__getattribute__(name)

    def __getattr__(self, name: str) -> Any:
        """A convenience method as it allows to call the command as if it was an object.

        :return:
            Callable object that will execute call :meth:`_call_process` with your
            arguments.
        """
        if name.startswith("_"):
            return super().__getattribute__(name)
        return lambda *args, **kwargs: self._call_process(name, *args, **kwargs)

    def set_persistent_git_options(self, **kwargs: Any) -> None:
        """Specify command line options to the git executable for subsequent
        subcommand calls.

        :param kwargs:
            A dict of keyword arguments.
            These arguments are passed as in :meth:`_call_process`, but will be passed
            to the git command rather than the subcommand.
        """

        self._persistent_git_options = self.transform_kwargs(split_single_char_options=True, **kwargs)

    @property
    def working_dir(self) -> Union[None, PathLike]:
        """:return: Git directory we are working on"""
        return self._working_dir

    @property
    def version_info(self) -> Tuple[int, ...]:
        """
        :return: Tuple with integers representing the major, minor and additional
            version numbers as parsed from :manpage:`git-version(1)`. Up to four fields
            are used.

            This value is generated on demand and is cached.
        """
        # Refreshing is global, but version_info caching is per-instance.
        refresh_token = self._refresh_token  # Copy token in case of concurrent refresh.

        # Use the cached version if obtained after the most recent refresh.
        if self._version_info_token is refresh_token:
            assert self._version_info is not None, "Bug: corrupted token-check state"
            return self._version_info

        # Run "git version" and parse it.
        process_version = self._call_process("version")
        version_string = process_version.split(" ")[2]
        version_fields = version_string.split(".")[:4]
        leading_numeric_fields = itertools.takewhile(str.isdigit, version_fields)
        self._version_info = tuple(map(int, leading_numeric_fields))

        # This value will be considered valid until the next refresh.
        self._version_info_token = refresh_token
        return self._version_info

    @overload
    def execute(
        self,
        command: Union[str, Sequence[Any]],
        *,
        as_process: Literal[True],
    ) -> "AutoInterrupt": ...

    @overload
    def execute(
        self,
        command: Union[str, Sequence[Any]],
        *,
        as_process: Literal[False] = False,
        stdout_as_string: Literal[True],
    ) -> Union[str, Tuple[int, str, str]]: ...

    @overload
    def execute(
        self,
        command: Union[str, Sequence[Any]],
        *,
        as_process: Literal[False] = False,
        stdout_as_string: Literal[False] = False,
    ) -> Union[bytes, Tuple[int, bytes, str]]: ...

    @overload
    def execute(
        self,
        command: Union[str, Sequence[Any]],
        *,
        with_extended_output: Literal[False],
        as_process: Literal[False],
        stdout_as_string: Literal[True],
    ) -> str: ...

    @overload
    def execute(
        self,
        command: Union[str, Sequence[Any]],
        *,
        with_extended_output: Literal[False],
        as_process: Literal[False],
        stdout_as_string: Literal[False],
    ) -> bytes: ...

    def execute(
        self,
        command: Union[str, Sequence[Any]],
        istream: Union[None, BinaryIO] = None,
        with_extended_output: bool = False,
        with_exceptions: bool = True,
        as_process: bool = False,
        output_stream: Union[None, BinaryIO] = None,
        stdout_as_string: bool = True,
        kill_after_timeout: Union[None, float] = None,
        with_stdout: bool = True,
        universal_newlines: bool = False,
        shell: Union[None, bool] = None,
        env: Union[None, Mapping[str, str]] = None,
        max_chunk_size: int = io.DEFAULT_BUFFER_SIZE,
        strip_newline_in_stdout: bool = True,
        **subprocess_kwargs: Any,
    ) -> Union[str, bytes, Tuple[int, Union[str, bytes], str], AutoInterrupt]:
        R"""Handle executing the command, and consume and return the returned
        information (stdout).

        :param command:
            The command argument list to execute.
            It should be a sequence of program arguments, or a string. The
            program to execute is the first item in the args sequence or string.

        :param istream:
            Standard input filehandle passed to :class:`subprocess.Popen`.

        :param with_extended_output:
            Whether to return a (status, stdout, stderr) tuple.

        :param with_exceptions:
            Whether to raise an exception when git returns a non-zero status.

        :param as_process:
            Whether to return the created process instance directly from which
            streams can be read on demand. This will render `with_extended_output`
            and `with_exceptions` ineffective - the caller will have to deal with
            the details. It is important to note that the process will be placed
            into an :class:`AutoInterrupt` wrapper that will interrupt the process
            once it goes out of scope. If you use the command in iterators, you
            should pass the whole process instance instead of a single stream.

        :param output_stream:
            If set to a file-like object, data produced by the git command will be
            copied to the given stream instead of being returned as a string.
            This feature only has any effect if `as_process` is ``False``.

        :param stdout_as_string:
            If ``False``, the command's standard output will be bytes. Otherwise, it
            will be decoded into a string using the default encoding (usually UTF-8).
            The latter can fail, if the output contains binary data.

        :param kill_after_timeout:
            Specifies a timeout in seconds for the git command, after which the process
            should be killed. This will have no effect if `as_process` is set to
            ``True``. It is set to ``None`` by default and will let the process run
            until the timeout is explicitly specified. Uses of this feature should be
            carefully considered, due to the following limitations:

            1. This feature is not supported at all on Windows.
            2. Effectiveness may vary by operating system. ``ps --ppid`` is used to
               enumerate child processes, which is available on most GNU/Linux systems
               but not most others.
            3. Deeper descendants do not receive signals, though they may sometimes
               terminate as a consequence of their parent processes being killed.
            4. `kill_after_timeout` uses ``SIGKILL``, which can have negative side
               effects on a repository. For example, stale locks in case of
               :manpage:`git-gc(1)` could render the repository incapable of accepting
               changes until the lock is manually removed.

        :param with_stdout:
            If ``True``, default ``True``, we open stdout on the created process.

        :param universal_newlines:
            If ``True``, pipes will be opened as text, and lines are split at all known
            line endings.

        :param shell:
            Whether to invoke commands through a shell
            (see :class:`Popen(..., shell=True) <subprocess.Popen>`).
            If this is not ``None``, it overrides :attr:`USE_SHELL`.

            Passing ``shell=True`` to this or any other GitPython function should be
            avoided, as it is unsafe under most circumstances. This is because it is
            typically not feasible to fully consider and account for the effect of shell
            expansions, especially when passing ``shell=True`` to other methods that
            forward it to :meth:`Git.execute`. Passing ``shell=True`` is also no longer
            needed (nor useful) to work around any known operating system specific
            issues.

        :param env:
            A dictionary of environment variables to be passed to
            :class:`subprocess.Popen`.

        :param max_chunk_size:
            Maximum number of bytes in one chunk of data passed to the `output_stream`
            in one invocation of its ``write()`` method. If the given number is not
            positive then the default value is used.

        :param strip_newline_in_stdout:
            Whether to strip the trailing ``\n`` of the command stdout.

        :param subprocess_kwargs:
            Keyword arguments to be passed to :class:`subprocess.Popen`. Please note
            that some of the valid kwargs are already set by this method; the ones you
            specify may not be the same ones.

        :return:
            * str(output), if `extended_output` is ``False`` (Default)
            * tuple(int(status), str(stdout), str(stderr)),
              if `extended_output` is ``True``

            If `output_stream` is ``True``, the stdout value will be your output stream:

            * output_stream, if `extended_output` is ``False``
            * tuple(int(status), output_stream, str(stderr)),
              if `extended_output` is ``True``

            Note that git is executed with ``LC_MESSAGES="C"`` to ensure consistent
            output regardless of system language.

        :raise git.exc.GitCommandError:

        :note:
            If you add additional keyword arguments to the signature of this method, you
            must update the ``execute_kwargs`` variable housed in this module.
        """
        # Remove password for the command if present.
        redacted_command = remove_password_if_present(command)
        if self.GIT_PYTHON_TRACE and (self.GIT_PYTHON_TRACE != "full" or as_process):
            _logger.info(" ".join(redacted_command))

        # Allow the user to have the command executed in their working dir.
        try:
            cwd = self._working_dir or os.getcwd()  # type: Union[None, str]
            if not os.access(str(cwd), os.X_OK):
                cwd = None
        except FileNotFoundError:
            cwd = None

        # Start the process.
        inline_env = env
        env = os.environ.copy()
        # Attempt to force all output to plain ASCII English, which is what some parsing
        # code may expect.
        # According to https://askubuntu.com/a/311796, we are setting LANGUAGE as well
        # just to be sure.
        env["LANGUAGE"] = "C"
        env["LC_ALL"] = "C"
        env.update(self._environment)
        if inline_env is not None:
            env.update(inline_env)

        if sys.platform == "win32":
            if kill_after_timeout is not None:
                raise GitCommandError(
                    redacted_command,
                    '"kill_after_timeout" feature is not supported on Windows.',
                )
            cmd_not_found_exception = OSError
        else:
            cmd_not_found_exception = FileNotFoundError
        # END handle

        stdout_sink = PIPE if with_stdout else getattr(subprocess, "DEVNULL", None) or open(os.devnull, "wb")
        if shell is None:
            # Get the value of USE_SHELL with no deprecation warning. Do this without
            # warnings.catch_warnings, to avoid a race condition with application code
            # configuring warnings. The value could be looked up in type(self).__dict__
            # or Git.__dict__, but those can break under some circumstances. This works
            # the same as self.USE_SHELL in more situations; see Git.__getattribute__.
            shell = super().__getattribute__("USE_SHELL")
        _logger.debug(
            "Popen(%s, cwd=%s, stdin=%s, shell=%s, universal_newlines=%s)",
            redacted_command,
            cwd,
            "<valid stream>" if istream else "None",
            shell,
            universal_newlines,
        )
        try:
            proc = safer_popen(
                command,
                env=env,
                cwd=cwd,
                bufsize=-1,
                stdin=(istream or DEVNULL),
                stderr=PIPE,
                stdout=stdout_sink,
                shell=shell,
                universal_newlines=universal_newlines,
                encoding=defenc if universal_newlines else None,
                **subprocess_kwargs,
            )
        except cmd_not_found_exception as err:
            raise GitCommandNotFound(redacted_command, err) from err
        else:
            # Replace with a typeguard for Popen[bytes]?
            proc.stdout = cast(BinaryIO, proc.stdout)
            proc.stderr = cast(BinaryIO, proc.stderr)

        if as_process:
            return self.AutoInterrupt(proc, command)

        if sys.platform != "win32" and kill_after_timeout is not None:
            # Help mypy figure out this is not None even when used inside communicate().
            timeout = kill_after_timeout

            def kill_process(pid: int) -> None:
                """Callback to kill a process.

                This callback implementation would be ineffective and unsafe on Windows.
                """
                p = Popen(["ps", "--ppid", str(pid)], stdout=PIPE)
                child_pids = []
                if p.stdout is not None:
                    for line in p.stdout:
                        if len(line.split()) > 0:
                            local_pid = (line.split())[0]
                            if local_pid.isdigit():
                                child_pids.append(int(local_pid))
                try:
                    os.kill(pid, signal.SIGKILL)
                    for child_pid in child_pids:
                        try:
                            os.kill(child_pid, signal.SIGKILL)
                        except OSError:
                            pass
                    # Tell the main routine that the process was killed.
                    kill_check.set()
                except OSError:
                    # It is possible that the process gets completed in the duration
                    # after timeout happens and before we try to kill the process.
                    pass
                return

            def communicate() -> Tuple[AnyStr, AnyStr]:
                watchdog.start()
                out, err = proc.communicate()
                watchdog.cancel()
                if kill_check.is_set():
                    err = 'Timeout: the command "%s" did not complete in %d ' "secs." % (
                        " ".join(redacted_command),
                        timeout,
                    )
                    if not universal_newlines:
                        err = err.encode(defenc)
                return out, err

            # END helpers

            kill_check = threading.Event()
            watchdog = threading.Timer(timeout, kill_process, args=(proc.pid,))
        else:
            communicate = proc.communicate

        # Wait for the process to return.
        status = 0
        stdout_value: Union[str, bytes] = b""
        stderr_value: Union[str, bytes] = b""
        newline = "\n" if universal_newlines else b"\n"
        try:
            if output_stream is None:
                stdout_value, stderr_value = communicate()
                # Strip trailing "\n".
                if stdout_value.endswith(newline) and strip_newline_in_stdout:  # type: ignore[arg-type]
                    stdout_value = stdout_value[:-1]
                if stderr_value.endswith(newline):  # type: ignore[arg-type]
                    stderr_value = stderr_value[:-1]

                status = proc.returncode
            else:
                max_chunk_size = max_chunk_size if max_chunk_size and max_chunk_size > 0 else io.DEFAULT_BUFFER_SIZE
                stream_copy(proc.stdout, output_stream, max_chunk_size)
                stdout_value = proc.stdout.read()
                stderr_value = proc.stderr.read()
                # Strip trailing "\n".
                if stderr_value.endswith(newline):  # type: ignore[arg-type]
                    stderr_value = stderr_value[:-1]
                status = proc.wait()
            # END stdout handling
        finally:
            proc.stdout.close()
            proc.stderr.close()

        if self.GIT_PYTHON_TRACE == "full":
            cmdstr = " ".join(redacted_command)

            def as_text(stdout_value: Union[bytes, str]) -> str:
                return not output_stream and safe_decode(stdout_value) or "<OUTPUT_STREAM>"

            # END as_text

            if stderr_value:
                _logger.info(
                    "%s -> %d; stdout: '%s'; stderr: '%s'",
                    cmdstr,
                    status,
                    as_text(stdout_value),
                    safe_decode(stderr_value),
                )
            elif stdout_value:
                _logger.info("%s -> %d; stdout: '%s'", cmdstr, status, as_text(stdout_value))
            else:
                _logger.info("%s -> %d", cmdstr, status)
        # END handle debug printing

        if with_exceptions and status != 0:
            raise GitCommandError(redacted_command, status, stderr_value, stdout_value)

        if isinstance(stdout_value, bytes) and stdout_as_string:  # Could also be output_stream.
            stdout_value = safe_decode(stdout_value)

        # Allow access to the command's status code.
        if with_extended_output:
            return (status, stdout_value, safe_decode(stderr_value))
        else:
            return stdout_value

    def environment(self) -> Dict[str, str]:
        return self._environment

    def update_environment(self, **kwargs: Any) -> Dict[str, Union[str, None]]:
        """Set environment variables for future git invocations. Return all changed
        values in a format that can be passed back into this function to revert the
        changes.

        Examples::

            old_env = self.update_environment(PWD='/tmp')
            self.update_environment(**old_env)

        :param kwargs:
            Environment variables to use for git processes.

        :return:
            Dict that maps environment variables to their old values
        """
        old_env = {}
        for key, value in kwargs.items():
            # Set value if it is None.
            if value is not None:
                old_env[key] = self._environment.get(key)
                self._environment[key] = value
            # Remove key from environment if its value is None.
            elif key in self._environment:
                old_env[key] = self._environment[key]
                del self._environment[key]
        return old_env

    @contextlib.contextmanager
    def custom_environment(self, **kwargs: Any) -> Iterator[None]:
        """A context manager around the above :meth:`update_environment` method to
        restore the environment back to its previous state after operation.

        Examples::

            with self.custom_environment(GIT_SSH='/bin/ssh_wrapper'):
                repo.remotes.origin.fetch()

        :param kwargs:
            See :meth:`update_environment`.
        """
        old_env = self.update_environment(**kwargs)
        try:
            yield
        finally:
            self.update_environment(**old_env)

    def transform_kwarg(self, name: str, value: Any, split_single_char_options: bool) -> List[str]:
        if len(name) == 1:
            if value is True:
                return ["-%s" % name]
            elif value not in (False, None):
                if split_single_char_options:
                    return ["-%s" % name, "%s" % value]
                else:
                    return ["-%s%s" % (name, value)]
        else:
            if value is True:
                return ["--%s" % dashify(name)]
            elif value is not False and value is not None:
                return ["--%s=%s" % (dashify(name), value)]
        return []

    def transform_kwargs(self, split_single_char_options: bool = True, **kwargs: Any) -> List[str]:
        """Transform Python-style kwargs into git command line options."""
        args = []
        for k, v in kwargs.items():
            if isinstance(v, (list, tuple)):
                for value in v:
                    args += self.transform_kwarg(k, value, split_single_char_options)
            else:
                args += self.transform_kwarg(k, v, split_single_char_options)
        return args

    @classmethod
    def _unpack_args(cls, arg_list: Sequence[str]) -> List[str]:
        outlist = []
        if isinstance(arg_list, (list, tuple)):
            for arg in arg_list:
                outlist.extend(cls._unpack_args(arg))
        else:
            outlist.append(str(arg_list))

        return outlist

    def __call__(self, **kwargs: Any) -> "Git":
        """Specify command line options to the git executable for a subcommand call.

        :param kwargs:
            A dict of keyword arguments.
            These arguments are passed as in :meth:`_call_process`, but will be passed
            to the git command rather than the subcommand.

        Examples::

            git(work_tree='/tmp').difftool()
        """
        self._git_options = self.transform_kwargs(split_single_char_options=True, **kwargs)
        return self

    @overload
    def _call_process(
        self, method: str, *args: None, **kwargs: None
    ) -> str: ...  # If no args were given, execute the call with all defaults.

    @overload
    def _call_process(
        self,
        method: str,
        istream: int,
        as_process: Literal[True],
        *args: Any,
        **kwargs: Any,
    ) -> "Git.AutoInterrupt": ...

    @overload
    def _call_process(
        self, method: str, *args: Any, **kwargs: Any
    ) -> Union[str, bytes, Tuple[int, Union[str, bytes], str], "Git.AutoInterrupt"]: ...

    def _call_process(
        self, method: str, *args: Any, **kwargs: Any
    ) -> Union[str, bytes, Tuple[int, Union[str, bytes], str], "Git.AutoInterrupt"]:
        """Run the given git command with the specified arguments and return the result
        as a string.

        :param method:
            The command. Contained ``_`` characters will be converted to hyphens, such
            as in ``ls_files`` to call ``ls-files``.

        :param args:
            The list of arguments. If ``None`` is included, it will be pruned.
            This allows your commands to call git more conveniently, as ``None`` is
            realized as non-existent.

        :param kwargs:
            Contains key-values for the following:

            - The :meth:`execute()` kwds, as listed in ``execute_kwargs``.
            - "Command options" to be converted by :meth:`transform_kwargs`.
            - The ``insert_kwargs_after`` key which its value must match one of
              ``*args``.

            It also contains any command options, to be appended after the matched arg.

        Examples::

            git.rev_list('master', max_count=10, header=True)

        turns into::

            git rev-list max-count 10 --header master

        :return:
            Same as :meth:`execute`. If no args are given, used :meth:`execute`'s
            default (especially ``as_process = False``, ``stdout_as_string = True``) and
            return :class:`str`.
        """
        # Handle optional arguments prior to calling transform_kwargs.
        # Otherwise these'll end up in args, which is bad.
        exec_kwargs = {k: v for k, v in kwargs.items() if k in execute_kwargs}
        opts_kwargs = {k: v for k, v in kwargs.items() if k not in execute_kwargs}

        insert_after_this_arg = opts_kwargs.pop("insert_kwargs_after", None)

        # Prepare the argument list.

        opt_args = self.transform_kwargs(**opts_kwargs)
        ext_args = self._unpack_args([a for a in args if a is not None])

        if insert_after_this_arg is None:
            args_list = opt_args + ext_args
        else:
            try:
                index = ext_args.index(insert_after_this_arg)
            except ValueError as err:
                raise ValueError(
                    "Couldn't find argument '%s' in args %s to insert cmd options after"
                    % (insert_after_this_arg, str(ext_args))
                ) from err
            # END handle error
            args_list = ext_args[: index + 1] + opt_args + ext_args[index + 1 :]
        # END handle opts_kwargs

        call = [self.GIT_PYTHON_GIT_EXECUTABLE]

        # Add persistent git options.
        call.extend(self._persistent_git_options)

        # Add the git options, then reset to empty to avoid side effects.
        call.extend(self._git_options)
        self._git_options = ()

        call.append(dashify(method))
        call.extend(args_list)

        return self.execute(call, **exec_kwargs)

    def _parse_object_header(self, header_line: str) -> Tuple[str, str, int]:
        """
        :param header_line:
            A line of the form::

                <hex_sha> type_string size_as_int

        :return:
            (hex_sha, type_string, size_as_int)

        :raise ValueError:
            If the header contains indication for an error due to incorrect input sha.
        """
        tokens = header_line.split()
        if len(tokens) != 3:
            if not tokens:
                err_msg = (
                    f"SHA is empty, possible dubious ownership in the repository "
                    f"""at {self._working_dir}.\n            If this is unintended run:\n\n         """
                    f"""             "git config --global --add safe.directory {self._working_dir}" """
                )
                raise ValueError(err_msg)
            else:
                raise ValueError("SHA %s could not be resolved, git returned: %r" % (tokens[0], header_line.strip()))
            # END handle actual return value
        # END error handling

        if len(tokens[0]) != 40:
            raise ValueError("Failed to parse header: %r" % header_line)
        return (tokens[0], tokens[1], int(tokens[2]))

    def _prepare_ref(self, ref: AnyStr) -> bytes:
        # Required for command to separate refs on stdin, as bytes.
        if isinstance(ref, bytes):
            # Assume 40 bytes hexsha - bin-to-ascii for some reason returns bytes, not text.
            refstr: str = ref.decode("ascii")
        elif not isinstance(ref, str):
            refstr = str(ref)  # Could be ref-object.
        else:
            refstr = ref

        if not refstr.endswith("\n"):
            refstr += "\n"
        return refstr.encode(defenc)

    def _get_persistent_cmd(self, attr_name: str, cmd_name: str, *args: Any, **kwargs: Any) -> "Git.AutoInterrupt":
        cur_val = getattr(self, attr_name)
        if cur_val is not None:
            return cur_val

        options = {"istream": PIPE, "as_process": True}
        options.update(kwargs)

        cmd = self._call_process(cmd_name, *args, **options)
        setattr(self, attr_name, cmd)
        cmd = cast("Git.AutoInterrupt", cmd)
        return cmd

    def __get_object_header(self, cmd: "Git.AutoInterrupt", ref: AnyStr) -> Tuple[str, str, int]:
        if cmd.stdin and cmd.stdout:
            cmd.stdin.write(self._prepare_ref(ref))
            cmd.stdin.flush()
            return self._parse_object_header(cmd.stdout.readline())
        else:
            raise ValueError("cmd stdin was empty")

    def get_object_header(self, ref: str) -> Tuple[str, str, int]:
        """Use this method to quickly examine the type and size of the object behind the
        given ref.

        :note:
            The method will only suffer from the costs of command invocation once and
            reuses the command in subsequent calls.

        :return:
            (hexsha, type_string, size_as_int)
        """
        cmd = self._get_persistent_cmd("cat_file_header", "cat_file", batch_check=True)
        return self.__get_object_header(cmd, ref)

    def get_object_data(self, ref: str) -> Tuple[str, str, int, bytes]:
        """Similar to :meth:`get_object_header`, but returns object data as well.

        :return:
            (hexsha, type_string, size_as_int, data_string)

        :note:
            Not threadsafe.
        """
        hexsha, typename, size, stream = self.stream_object_data(ref)
        data = stream.read(size)
        del stream
        return (hexsha, typename, size, data)

    def stream_object_data(self, ref: str) -> Tuple[str, str, int, "Git.CatFileContentStream"]:
        """Similar to :meth:`get_object_data`, but returns the data as a stream.

        :return:
            (hexsha, type_string, size_as_int, stream)

        :note:
            This method is not threadsafe. You need one independent :class:`Git`
            instance per thread to be safe!
        """
        cmd = self._get_persistent_cmd("cat_file_all", "cat_file", batch=True)
        hexsha, typename, size = self.__get_object_header(cmd, ref)
        cmd_stdout = cmd.stdout if cmd.stdout is not None else io.BytesIO()
        return (hexsha, typename, size, self.CatFileContentStream(size, cmd_stdout))

    def clear_cache(self) -> "Git":
        """Clear all kinds of internal caches to release resources.

        Currently persistent commands will be interrupted.

        :return:
            self
        """
        for cmd in (self.cat_file_all, self.cat_file_header):
            if cmd:
                cmd.__del__()

        self.cat_file_all = None
        self.cat_file_header = None
        return self

# === NexusCore/openenv\Lib\site-packages\matplotlib\lines.py ===
"""
2D lines with support for a variety of line styles, markers, colors, etc.
"""

import copy

from numbers import Integral, Number, Real
import logging

import numpy as np

import matplotlib as mpl
from . import _api, cbook, colors as mcolors, _docstring
from .artist import Artist, allow_rasterization
from .cbook import (
    _to_unmasked_float_array, ls_mapper, ls_mapper_r, STEP_LOOKUP_MAP)
from .markers import MarkerStyle
from .path import Path
from .transforms import Bbox, BboxTransformTo, TransformedPath
from ._enums import JoinStyle, CapStyle

# Imported here for backward compatibility, even though they don't
# really belong.
from . import _path
from .markers import (  # noqa
    CARETLEFT, CARETRIGHT, CARETUP, CARETDOWN,
    CARETLEFTBASE, CARETRIGHTBASE, CARETUPBASE, CARETDOWNBASE,
    TICKLEFT, TICKRIGHT, TICKUP, TICKDOWN)

_log = logging.getLogger(__name__)


def _get_dash_pattern(style):
    """Convert linestyle to dash pattern."""
    # go from short hand -> full strings
    if isinstance(style, str):
        style = ls_mapper.get(style, style)
    # un-dashed styles
    if style in ['solid', 'None']:
        offset = 0
        dashes = None
    # dashed styles
    elif style in ['dashed', 'dashdot', 'dotted']:
        offset = 0
        dashes = tuple(mpl.rcParams[f'lines.{style}_pattern'])
    #
    elif isinstance(style, tuple):
        offset, dashes = style
        if offset is None:
            raise ValueError(f'Unrecognized linestyle: {style!r}')
    else:
        raise ValueError(f'Unrecognized linestyle: {style!r}')

    # normalize offset to be positive and shorter than the dash cycle
    if dashes is not None:
        dsum = sum(dashes)
        if dsum:
            offset %= dsum

    return offset, dashes


def _get_dash_patterns(styles):
    """Convert linestyle or sequence of linestyles to list of dash patterns."""
    try:
        patterns = [_get_dash_pattern(styles)]
    except ValueError:
        try:
            patterns = [_get_dash_pattern(x) for x in styles]
        except ValueError as err:
            emsg = f'Do not know how to convert {styles!r} to dashes'
            raise ValueError(emsg) from err

    return patterns


def _get_inverse_dash_pattern(offset, dashes):
    """Return the inverse of the given dash pattern, for filling the gaps."""
    # Define the inverse pattern by moving the last gap to the start of the
    # sequence.
    gaps = dashes[-1:] + dashes[:-1]
    # Set the offset so that this new first segment is skipped
    # (see backend_bases.GraphicsContextBase.set_dashes for offset definition).
    offset_gaps = offset + dashes[-1]

    return offset_gaps, gaps


def _scale_dashes(offset, dashes, lw):
    if not mpl.rcParams['lines.scale_dashes']:
        return offset, dashes
    scaled_offset = offset * lw
    scaled_dashes = ([x * lw if x is not None else None for x in dashes]
                     if dashes is not None else None)
    return scaled_offset, scaled_dashes


def segment_hits(cx, cy, x, y, radius):
    """
    Return the indices of the segments in the polyline with coordinates (*cx*,
    *cy*) that are within a distance *radius* of the point (*x*, *y*).
    """
    # Process single points specially
    if len(x) <= 1:
        res, = np.nonzero((cx - x) ** 2 + (cy - y) ** 2 <= radius ** 2)
        return res

    # We need to lop the last element off a lot.
    xr, yr = x[:-1], y[:-1]

    # Only look at line segments whose nearest point to C on the line
    # lies within the segment.
    dx, dy = x[1:] - xr, y[1:] - yr
    Lnorm_sq = dx ** 2 + dy ** 2  # Possibly want to eliminate Lnorm==0
    u = ((cx - xr) * dx + (cy - yr) * dy) / Lnorm_sq
    candidates = (u >= 0) & (u <= 1)

    # Note that there is a little area near one side of each point
    # which will be near neither segment, and another which will
    # be near both, depending on the angle of the lines.  The
    # following radius test eliminates these ambiguities.
    point_hits = (cx - x) ** 2 + (cy - y) ** 2 <= radius ** 2
    candidates = candidates & ~(point_hits[:-1] | point_hits[1:])

    # For those candidates which remain, determine how far they lie away
    # from the line.
    px, py = xr + u * dx, yr + u * dy
    line_hits = (cx - px) ** 2 + (cy - py) ** 2 <= radius ** 2
    line_hits = line_hits & candidates
    points, = point_hits.ravel().nonzero()
    lines, = line_hits.ravel().nonzero()
    return np.concatenate((points, lines))


def _mark_every_path(markevery, tpath, affine, ax):
    """
    Helper function that sorts out how to deal the input
    `markevery` and returns the points where markers should be drawn.

    Takes in the `markevery` value and the line path and returns the
    sub-sampled path.
    """
    # pull out the two bits of data we want from the path
    codes, verts = tpath.codes, tpath.vertices

    def _slice_or_none(in_v, slc):
        """Helper function to cope with `codes` being an ndarray or `None`."""
        if in_v is None:
            return None
        return in_v[slc]

    # if just an int, assume starting at 0 and make a tuple
    if isinstance(markevery, Integral):
        markevery = (0, markevery)
    # if just a float, assume starting at 0.0 and make a tuple
    elif isinstance(markevery, Real):
        markevery = (0.0, markevery)

    if isinstance(markevery, tuple):
        if len(markevery) != 2:
            raise ValueError('`markevery` is a tuple but its len is not 2; '
                             f'markevery={markevery}')
        start, step = markevery
        # if step is an int, old behavior
        if isinstance(step, Integral):
            # tuple of 2 int is for backwards compatibility,
            if not isinstance(start, Integral):
                raise ValueError(
                    '`markevery` is a tuple with len 2 and second element is '
                    'an int, but the first element is not an int; '
                    f'markevery={markevery}')
            # just return, we are done here

            return Path(verts[slice(start, None, step)],
                        _slice_or_none(codes, slice(start, None, step)))

        elif isinstance(step, Real):
            if not isinstance(start, Real):
                raise ValueError(
                    '`markevery` is a tuple with len 2 and second element is '
                    'a float, but the first element is not a float or an int; '
                    f'markevery={markevery}')
            if ax is None:
                raise ValueError(
                    "markevery is specified relative to the Axes size, but "
                    "the line does not have a Axes as parent")

            # calc cumulative distance along path (in display coords):
            fin = np.isfinite(verts).all(axis=1)
            fverts = verts[fin]
            disp_coords = affine.transform(fverts)

            delta = np.empty((len(disp_coords), 2))
            delta[0, :] = 0
            delta[1:, :] = disp_coords[1:, :] - disp_coords[:-1, :]
            delta = np.hypot(*delta.T).cumsum()
            # calc distance between markers along path based on the Axes
            # bounding box diagonal being a distance of unity:
            (x0, y0), (x1, y1) = ax.transAxes.transform([[0, 0], [1, 1]])
            scale = np.hypot(x1 - x0, y1 - y0)
            marker_delta = np.arange(start * scale, delta[-1], step * scale)
            # find closest actual data point that is closest to
            # the theoretical distance along the path:
            inds = np.abs(delta[np.newaxis, :] - marker_delta[:, np.newaxis])
            inds = inds.argmin(axis=1)
            inds = np.unique(inds)
            # return, we are done here
            return Path(fverts[inds], _slice_or_none(codes, inds))
        else:
            raise ValueError(
                f"markevery={markevery!r} is a tuple with len 2, but its "
                f"second element is not an int or a float")

    elif isinstance(markevery, slice):
        # mazol tov, it's already a slice, just return
        return Path(verts[markevery], _slice_or_none(codes, markevery))

    elif np.iterable(markevery):
        # fancy indexing
        try:
            return Path(verts[markevery], _slice_or_none(codes, markevery))
        except (ValueError, IndexError) as err:
            raise ValueError(
                f"markevery={markevery!r} is iterable but not a valid numpy "
                f"fancy index") from err
    else:
        raise ValueError(f"markevery={markevery!r} is not a recognized value")


@_docstring.interpd
@_api.define_aliases({
    "antialiased": ["aa"],
    "color": ["c"],
    "drawstyle": ["ds"],
    "linestyle": ["ls"],
    "linewidth": ["lw"],
    "markeredgecolor": ["mec"],
    "markeredgewidth": ["mew"],
    "markerfacecolor": ["mfc"],
    "markerfacecoloralt": ["mfcalt"],
    "markersize": ["ms"],
})
class Line2D(Artist):
    """
    A line - the line can have both a solid linestyle connecting all
    the vertices, and a marker at each vertex.  Additionally, the
    drawing of the solid line is influenced by the drawstyle, e.g., one
    can create "stepped" lines in various styles.
    """

    lineStyles = _lineStyles = {  # hidden names deprecated
        '-':    '_draw_solid',
        '--':   '_draw_dashed',
        '-.':   '_draw_dash_dot',
        ':':    '_draw_dotted',
        'None': '_draw_nothing',
        ' ':    '_draw_nothing',
        '':     '_draw_nothing',
    }

    _drawStyles_l = {
        'default':    '_draw_lines',
        'steps-mid':  '_draw_steps_mid',
        'steps-pre':  '_draw_steps_pre',
        'steps-post': '_draw_steps_post',
    }

    _drawStyles_s = {
        'steps': '_draw_steps_pre',
    }

    # drawStyles should now be deprecated.
    drawStyles = {**_drawStyles_l, **_drawStyles_s}
    # Need a list ordered with long names first:
    drawStyleKeys = [*_drawStyles_l, *_drawStyles_s]

    # Referenced here to maintain API.  These are defined in
    # MarkerStyle
    markers = MarkerStyle.markers
    filled_markers = MarkerStyle.filled_markers
    fillStyles = MarkerStyle.fillstyles

    zorder = 2

    _subslice_optim_min_size = 1000

    def __str__(self):
        if self._label != "":
            return f"Line2D({self._label})"
        elif self._x is None:
            return "Line2D()"
        elif len(self._x) > 3:
            return "Line2D(({:g},{:g}),({:g},{:g}),...,({:g},{:g}))".format(
                self._x[0], self._y[0],
                self._x[1], self._y[1],
                self._x[-1], self._y[-1])
        else:
            return "Line2D(%s)" % ",".join(
                map("({:g},{:g})".format, self._x, self._y))

    def __init__(self, xdata, ydata, *,
                 linewidth=None,  # all Nones default to rc
                 linestyle=None,
                 color=None,
                 gapcolor=None,
                 marker=None,
                 markersize=None,
                 markeredgewidth=None,
                 markeredgecolor=None,
                 markerfacecolor=None,
                 markerfacecoloralt='none',
                 fillstyle=None,
                 antialiased=None,
                 dash_capstyle=None,
                 solid_capstyle=None,
                 dash_joinstyle=None,
                 solid_joinstyle=None,
                 pickradius=5,
                 drawstyle=None,
                 markevery=None,
                 **kwargs
                 ):
        """
        Create a `.Line2D` instance with *x* and *y* data in sequences of
        *xdata*, *ydata*.

        Additional keyword arguments are `.Line2D` properties:

        %(Line2D:kwdoc)s

        See :meth:`set_linestyle` for a description of the line styles,
        :meth:`set_marker` for a description of the markers, and
        :meth:`set_drawstyle` for a description of the draw styles.

        """
        super().__init__()

        # Convert sequences to NumPy arrays.
        if not np.iterable(xdata):
            raise RuntimeError('xdata must be a sequence')
        if not np.iterable(ydata):
            raise RuntimeError('ydata must be a sequence')

        if linewidth is None:
            linewidth = mpl.rcParams['lines.linewidth']

        if linestyle is None:
            linestyle = mpl.rcParams['lines.linestyle']
        if marker is None:
            marker = mpl.rcParams['lines.marker']
        if color is None:
            color = mpl.rcParams['lines.color']

        if markersize is None:
            markersize = mpl.rcParams['lines.markersize']
        if antialiased is None:
            antialiased = mpl.rcParams['lines.antialiased']
        if dash_capstyle is None:
            dash_capstyle = mpl.rcParams['lines.dash_capstyle']
        if dash_joinstyle is None:
            dash_joinstyle = mpl.rcParams['lines.dash_joinstyle']
        if solid_capstyle is None:
            solid_capstyle = mpl.rcParams['lines.solid_capstyle']
        if solid_joinstyle is None:
            solid_joinstyle = mpl.rcParams['lines.solid_joinstyle']

        if drawstyle is None:
            drawstyle = 'default'

        self._dashcapstyle = None
        self._dashjoinstyle = None
        self._solidjoinstyle = None
        self._solidcapstyle = None
        self.set_dash_capstyle(dash_capstyle)
        self.set_dash_joinstyle(dash_joinstyle)
        self.set_solid_capstyle(solid_capstyle)
        self.set_solid_joinstyle(solid_joinstyle)

        self._linestyles = None
        self._drawstyle = None
        self._linewidth = linewidth
        self._unscaled_dash_pattern = (0, None)  # offset, dash
        self._dash_pattern = (0, None)  # offset, dash (scaled by linewidth)

        self.set_linewidth(linewidth)
        self.set_linestyle(linestyle)
        self.set_drawstyle(drawstyle)

        self._color = None
        self.set_color(color)
        if marker is None:
            marker = 'none'  # Default.
        if not isinstance(marker, MarkerStyle):
            self._marker = MarkerStyle(marker, fillstyle)
        else:
            self._marker = marker

        self._gapcolor = None
        self.set_gapcolor(gapcolor)

        self._markevery = None
        self._markersize = None
        self._antialiased = None

        self.set_markevery(markevery)
        self.set_antialiased(antialiased)
        self.set_markersize(markersize)

        self._markeredgecolor = None
        self._markeredgewidth = None
        self._markerfacecolor = None
        self._markerfacecoloralt = None

        self.set_markerfacecolor(markerfacecolor)  # Normalizes None to rc.
        self.set_markerfacecoloralt(markerfacecoloralt)
        self.set_markeredgecolor(markeredgecolor)  # Normalizes None to rc.
        self.set_markeredgewidth(markeredgewidth)

        # update kwargs before updating data to give the caller a
        # chance to init axes (and hence unit support)
        self._internal_update(kwargs)
        self.pickradius = pickradius
        self.ind_offset = 0
        if (isinstance(self._picker, Number) and
                not isinstance(self._picker, bool)):
            self._pickradius = self._picker

        self._xorig = np.asarray([])
        self._yorig = np.asarray([])
        self._invalidx = True
        self._invalidy = True
        self._x = None
        self._y = None
        self._xy = None
        self._path = None
        self._transformed_path = None
        self._subslice = False
        self._x_filled = None  # used in subslicing; only x is needed

        self.set_data(xdata, ydata)

    def contains(self, mouseevent):
        """
        Test whether *mouseevent* occurred on the line.

        An event is deemed to have occurred "on" the line if it is less
        than ``self.pickradius`` (default: 5 points) away from it.  Use
        `~.Line2D.get_pickradius` or `~.Line2D.set_pickradius` to get or set
        the pick radius.

        Parameters
        ----------
        mouseevent : `~matplotlib.backend_bases.MouseEvent`

        Returns
        -------
        contains : bool
            Whether any values are within the radius.
        details : dict
            A dictionary ``{'ind': pointlist}``, where *pointlist* is a
            list of points of the line that are within the pickradius around
            the event position.

            TODO: sort returned indices by distance
        """
        if self._different_canvas(mouseevent):
            return False, {}

        # Make sure we have data to plot
        if self._invalidy or self._invalidx:
            self.recache()
        if len(self._xy) == 0:
            return False, {}

        # Convert points to pixels
        transformed_path = self._get_transformed_path()
        path, affine = transformed_path.get_transformed_path_and_affine()
        path = affine.transform_path(path)
        xy = path.vertices
        xt = xy[:, 0]
        yt = xy[:, 1]

        # Convert pick radius from points to pixels
        fig = self.get_figure(root=True)
        if fig is None:
            _log.warning('no figure set when check if mouse is on line')
            pixels = self._pickradius
        else:
            pixels = fig.dpi / 72. * self._pickradius

        # The math involved in checking for containment (here and inside of
        # segment_hits) assumes that it is OK to overflow, so temporarily set
        # the error flags accordingly.
        with np.errstate(all='ignore'):
            # Check for collision
            if self._linestyle in ['None', None]:
                # If no line, return the nearby point(s)
                ind, = np.nonzero(
                    (xt - mouseevent.x) ** 2 + (yt - mouseevent.y) ** 2
                    <= pixels ** 2)
            else:
                # If line, return the nearby segment(s)
                ind = segment_hits(mouseevent.x, mouseevent.y, xt, yt, pixels)
                if self._drawstyle.startswith("steps"):
                    ind //= 2

        ind += self.ind_offset

        # Return the point(s) within radius
        return len(ind) > 0, dict(ind=ind)

    def get_pickradius(self):
        """
        Return the pick radius used for containment tests.

        See `.contains` for more details.
        """
        return self._pickradius

    def set_pickradius(self, pickradius):
        """
        Set the pick radius used for containment tests.

        See `.contains` for more details.

        Parameters
        ----------
        pickradius : float
            Pick radius, in points.
        """
        if not isinstance(pickradius, Real) or pickradius < 0:
            raise ValueError("pick radius should be a distance")
        self._pickradius = pickradius

    pickradius = property(get_pickradius, set_pickradius)

    def get_fillstyle(self):
        """
        Return the marker fill style.

        See also `~.Line2D.set_fillstyle`.
        """
        return self._marker.get_fillstyle()

    def set_fillstyle(self, fs):
        """
        Set the marker fill style.

        Parameters
        ----------
        fs : {'full', 'left', 'right', 'bottom', 'top', 'none'}
            Possible values:

            - 'full': Fill the whole marker with the *markerfacecolor*.
            - 'left', 'right', 'bottom', 'top': Fill the marker half at
              the given side with the *markerfacecolor*. The other
              half of the marker is filled with *markerfacecoloralt*.
            - 'none': No filling.

            For examples see :ref:`marker_fill_styles`.
        """
        self.set_marker(MarkerStyle(self._marker.get_marker(), fs))
        self.stale = True

    def set_markevery(self, every):
        """
        Set the markevery property to subsample the plot when using markers.

        e.g., if ``every=5``, every 5-th marker will be plotted.

        Parameters
        ----------
        every : None or int or (int, int) or slice or list[int] or float or \
(float, float) or list[bool]
            Which markers to plot.

            - ``every=None``: every point will be plotted.
            - ``every=N``: every N-th marker will be plotted starting with
              marker 0.
            - ``every=(start, N)``: every N-th marker, starting at index
              *start*, will be plotted.
            - ``every=slice(start, end, N)``: every N-th marker, starting at
              index *start*, up to but not including index *end*, will be
              plotted.
            - ``every=[i, j, m, ...]``: only markers at the given indices
              will be plotted.
            - ``every=[True, False, True, ...]``: only positions that are True
              will be plotted. The list must have the same length as the data
              points.
            - ``every=0.1``, (i.e. a float): markers will be spaced at
              approximately equal visual distances along the line; the distance
              along the line between markers is determined by multiplying the
              display-coordinate distance of the Axes bounding-box diagonal
              by the value of *every*.
            - ``every=(0.5, 0.1)`` (i.e. a length-2 tuple of float): similar
              to ``every=0.1`` but the first marker will be offset along the
              line by 0.5 multiplied by the
              display-coordinate-diagonal-distance along the line.

            For examples see
            :doc:`/gallery/lines_bars_and_markers/markevery_demo`.

        Notes
        -----
        Setting *markevery* will still only draw markers at actual data points.
        While the float argument form aims for uniform visual spacing, it has
        to coerce from the ideal spacing to the nearest available data point.
        Depending on the number and distribution of data points, the result
        may still not look evenly spaced.

        When using a start offset to specify the first marker, the offset will
        be from the first data point which may be different from the first
        the visible data point if the plot is zoomed in.

        If zooming in on a plot when using float arguments then the actual
        data points that have markers will change because the distance between
        markers is always determined from the display-coordinates
        axes-bounding-box-diagonal regardless of the actual axes data limits.

        """
        self._markevery = every
        self.stale = True

    def get_markevery(self):
        """
        Return the markevery setting for marker subsampling.

        See also `~.Line2D.set_markevery`.
        """
        return self._markevery

    def set_picker(self, p):
        """
        Set the event picker details for the line.

        Parameters
        ----------
        p : float or callable[[Artist, Event], tuple[bool, dict]]
            If a float, it is used as the pick radius in points.
        """
        if not callable(p):
            self.set_pickradius(p)
        self._picker = p

    def get_bbox(self):
        """Get the bounding box of this line."""
        bbox = Bbox([[0, 0], [0, 0]])
        bbox.update_from_data_xy(self.get_xydata())
        return bbox

    def get_window_extent(self, renderer=None):
        bbox = Bbox([[0, 0], [0, 0]])
        trans_data_to_xy = self.get_transform().transform
        bbox.update_from_data_xy(trans_data_to_xy(self.get_xydata()),
                                 ignore=True)
        # correct for marker size, if any
        if self._marker:
            ms = (self._markersize / 72.0 * self.get_figure(root=True).dpi) * 0.5
            bbox = bbox.padded(ms)
        return bbox

    def set_data(self, *args):
        """
        Set the x and y data.

        Parameters
        ----------
        *args : (2, N) array or two 1D arrays

        See Also
        --------
        set_xdata
        set_ydata
        """
        if len(args) == 1:
            (x, y), = args
        else:
            x, y = args

        self.set_xdata(x)
        self.set_ydata(y)

    def recache_always(self):
        self.recache(always=True)

    def recache(self, always=False):
        if always or self._invalidx:
            xconv = self.convert_xunits(self._xorig)
            x = _to_unmasked_float_array(xconv).ravel()
        else:
            x = self._x
        if always or self._invalidy:
            yconv = self.convert_yunits(self._yorig)
            y = _to_unmasked_float_array(yconv).ravel()
        else:
            y = self._y

        self._xy = np.column_stack(np.broadcast_arrays(x, y)).astype(float)
        self._x, self._y = self._xy.T  # views

        self._subslice = False
        if (self.axes
                and len(x) > self._subslice_optim_min_size
                and _path.is_sorted_and_has_non_nan(x)
                and self.axes.name == 'rectilinear'
                and self.axes.get_xscale() == 'linear'
                and self._markevery is None
                and self.get_clip_on()
                and self.get_transform() == self.axes.transData):
            self._subslice = True
            nanmask = np.isnan(x)
            if nanmask.any():
                self._x_filled = self._x.copy()
                indices = np.arange(len(x))
                self._x_filled[nanmask] = np.interp(
                    indices[nanmask], indices[~nanmask], self._x[~nanmask])
            else:
                self._x_filled = self._x

        if self._path is not None:
            interpolation_steps = self._path._interpolation_steps
        else:
            interpolation_steps = 1
        xy = STEP_LOOKUP_MAP[self._drawstyle](*self._xy.T)
        self._path = Path(np.asarray(xy).T,
                          _interpolation_steps=interpolation_steps)
        self._transformed_path = None
        self._invalidx = False
        self._invalidy = False

    def _transform_path(self, subslice=None):
        """
        Put a TransformedPath instance at self._transformed_path;
        all invalidation of the transform is then handled by the
        TransformedPath instance.
        """
        # Masked arrays are now handled by the Path class itself
        if subslice is not None:
            xy = STEP_LOOKUP_MAP[self._drawstyle](*self._xy[subslice, :].T)
            _path = Path(np.asarray(xy).T,
                         _interpolation_steps=self._path._interpolation_steps)
        else:
            _path = self._path
        self._transformed_path = TransformedPath(_path, self.get_transform())

    def _get_transformed_path(self):
        """Return this line's `~matplotlib.transforms.TransformedPath`."""
        if self._transformed_path is None:
            self._transform_path()
        return self._transformed_path

    def set_transform(self, t):
        # docstring inherited
        self._invalidx = True
        self._invalidy = True
        super().set_transform(t)

    @allow_rasterization
    def draw(self, renderer):
        # docstring inherited

        if not self.get_visible():
            return

        if self._invalidy or self._invalidx:
            self.recache()
        self.ind_offset = 0  # Needed for contains() method.
        if self._subslice and self.axes:
            x0, x1 = self.axes.get_xbound()
            i0 = self._x_filled.searchsorted(x0, 'left')
            i1 = self._x_filled.searchsorted(x1, 'right')
            subslice = slice(max(i0 - 1, 0), i1 + 1)
            self.ind_offset = subslice.start
            self._transform_path(subslice)
        else:
            subslice = None

        if self.get_path_effects():
            from matplotlib.patheffects import PathEffectRenderer
            renderer = PathEffectRenderer(self.get_path_effects(), renderer)

        renderer.open_group('line2d', self.get_gid())
        if self._lineStyles[self._linestyle] != '_draw_nothing':
            tpath, affine = (self._get_transformed_path()
                             .get_transformed_path_and_affine())
            if len(tpath.vertices):
                gc = renderer.new_gc()
                self._set_gc_clip(gc)
                gc.set_url(self.get_url())

                gc.set_antialiased(self._antialiased)
                gc.set_linewidth(self._linewidth)

                if self.is_dashed():
                    cap = self._dashcapstyle
                    join = self._dashjoinstyle
                else:
                    cap = self._solidcapstyle
                    join = self._solidjoinstyle
                gc.set_joinstyle(join)
                gc.set_capstyle(cap)
                gc.set_snap(self.get_snap())
                if self.get_sketch_params() is not None:
                    gc.set_sketch_params(*self.get_sketch_params())

                # We first draw a path within the gaps if needed.
                if self.is_dashed() and self._gapcolor is not None:
                    lc_rgba = mcolors.to_rgba(self._gapcolor, self._alpha)
                    gc.set_foreground(lc_rgba, isRGBA=True)

                    offset_gaps, gaps = _get_inverse_dash_pattern(
                        *self._dash_pattern)

                    gc.set_dashes(offset_gaps, gaps)
                    renderer.draw_path(gc, tpath, affine.frozen())

                lc_rgba = mcolors.to_rgba(self._color, self._alpha)
                gc.set_foreground(lc_rgba, isRGBA=True)

                gc.set_dashes(*self._dash_pattern)
                renderer.draw_path(gc, tpath, affine.frozen())
                gc.restore()

        if self._marker and self._markersize > 0:
            gc = renderer.new_gc()
            self._set_gc_clip(gc)
            gc.set_url(self.get_url())
            gc.set_linewidth(self._markeredgewidth)
            gc.set_antialiased(self._antialiased)

            ec_rgba = mcolors.to_rgba(
                self.get_markeredgecolor(), self._alpha)
            fc_rgba = mcolors.to_rgba(
                self._get_markerfacecolor(), self._alpha)
            fcalt_rgba = mcolors.to_rgba(
                self._get_markerfacecolor(alt=True), self._alpha)
            # If the edgecolor is "auto", it is set according to the *line*
            # color but inherits the alpha value of the *face* color, if any.
            if (cbook._str_equal(self._markeredgecolor, "auto")
                    and not cbook._str_lower_equal(
                        self.get_markerfacecolor(), "none")):
                ec_rgba = ec_rgba[:3] + (fc_rgba[3],)
            gc.set_foreground(ec_rgba, isRGBA=True)
            if self.get_sketch_params() is not None:
                scale, length, randomness = self.get_sketch_params()
                gc.set_sketch_params(scale/2, length/2, 2*randomness)

            marker = self._marker

            # Markers *must* be drawn ignoring the drawstyle (but don't pay the
            # recaching if drawstyle is already "default").
            if self.get_drawstyle() != "default":
                with cbook._setattr_cm(
                        self, _drawstyle="default", _transformed_path=None):
                    self.recache()
                    self._transform_path(subslice)
                    tpath, affine = (self._get_transformed_path()
                                     .get_transformed_points_and_affine())
            else:
                tpath, affine = (self._get_transformed_path()
                                 .get_transformed_points_and_affine())

            if len(tpath.vertices):
                # subsample the markers if markevery is not None
                markevery = self.get_markevery()
                if markevery is not None:
                    subsampled = _mark_every_path(
                        markevery, tpath, affine, self.axes)
                else:
                    subsampled = tpath

                snap = marker.get_snap_threshold()
                if isinstance(snap, Real):
                    snap = renderer.points_to_pixels(self._markersize) >= snap
                gc.set_snap(snap)
                gc.set_joinstyle(marker.get_joinstyle())
                gc.set_capstyle(marker.get_capstyle())
                marker_path = marker.get_path()
                marker_trans = marker.get_transform()
                w = renderer.points_to_pixels(self._markersize)

                if cbook._str_equal(marker.get_marker(), ","):
                    gc.set_linewidth(0)
                else:
                    # Don't scale for pixels, and don't stroke them
                    marker_trans = marker_trans.scale(w)
                renderer.draw_markers(gc, marker_path, marker_trans,
                                      subsampled, affine.frozen(),
                                      fc_rgba)

                alt_marker_path = marker.get_alt_path()
                if alt_marker_path:
                    alt_marker_trans = marker.get_alt_transform()
                    alt_marker_trans = alt_marker_trans.scale(w)
                    renderer.draw_markers(
                            gc, alt_marker_path, alt_marker_trans, subsampled,
                            affine.frozen(), fcalt_rgba)

            gc.restore()

        renderer.close_group('line2d')
        self.stale = False

    def get_antialiased(self):
        """Return whether antialiased rendering is used."""
        return self._antialiased

    def get_color(self):
        """
        Return the line color.

        See also `~.Line2D.set_color`.
        """
        return self._color

    def get_drawstyle(self):
        """
        Return the drawstyle.

        See also `~.Line2D.set_drawstyle`.
        """
        return self._drawstyle

    def get_gapcolor(self):
        """
        Return the line gapcolor.

        See also `~.Line2D.set_gapcolor`.
        """
        return self._gapcolor

    def get_linestyle(self):
        """
        Return the linestyle.

        See also `~.Line2D.set_linestyle`.
        """
        return self._linestyle

    def get_linewidth(self):
        """
        Return the linewidth in points.

        See also `~.Line2D.set_linewidth`.
        """
        return self._linewidth

    def get_marker(self):
        """
        Return the line marker.

        See also `~.Line2D.set_marker`.
        """
        return self._marker.get_marker()

    def get_markeredgecolor(self):
        """
        Return the marker edge color.

        See also `~.Line2D.set_markeredgecolor`.
        """
        mec = self._markeredgecolor
        if cbook._str_equal(mec, 'auto'):
            if mpl.rcParams['_internal.classic_mode']:
                if self._marker.get_marker() in ('.', ','):
                    return self._color
                if (self._marker.is_filled()
                        and self._marker.get_fillstyle() != 'none'):
                    return 'k'  # Bad hard-wired default...
            return self._color
        else:
            return mec

    def get_markeredgewidth(self):
        """
        Return the marker edge width in points.

        See also `~.Line2D.set_markeredgewidth`.
        """
        return self._markeredgewidth

    def _get_markerfacecolor(self, alt=False):
        if self._marker.get_fillstyle() == 'none':
            return 'none'
        fc = self._markerfacecoloralt if alt else self._markerfacecolor
        if cbook._str_lower_equal(fc, 'auto'):
            return self._color
        else:
            return fc

    def get_markerfacecolor(self):
        """
        Return the marker face color.

        See also `~.Line2D.set_markerfacecolor`.
        """
        return self._get_markerfacecolor(alt=False)

    def get_markerfacecoloralt(self):
        """
        Return the alternate marker face color.

        See also `~.Line2D.set_markerfacecoloralt`.
        """
        return self._get_markerfacecolor(alt=True)

    def get_markersize(self):
        """
        Return the marker size in points.

        See also `~.Line2D.set_markersize`.
        """
        return self._markersize

    def get_data(self, orig=True):
        """
        Return the line data as an ``(xdata, ydata)`` pair.

        If *orig* is *True*, return the original data.
        """
        return self.get_xdata(orig=orig), self.get_ydata(orig=orig)

    def get_xdata(self, orig=True):
        """
        Return the xdata.

        If *orig* is *True*, return the original data, else the
        processed data.
        """
        if orig:
            return self._xorig
        if self._invalidx:
            self.recache()
        return self._x

    def get_ydata(self, orig=True):
        """
        Return the ydata.

        If *orig* is *True*, return the original data, else the
        processed data.
        """
        if orig:
            return self._yorig
        if self._invalidy:
            self.recache()
        return self._y

    def get_path(self):
        """Return the `~matplotlib.path.Path` associated with this line."""
        if self._invalidy or self._invalidx:
            self.recache()
        return self._path

    def get_xydata(self):
        """Return the *xy* data as a (N, 2) array."""
        if self._invalidy or self._invalidx:
            self.recache()
        return self._xy

    def set_antialiased(self, b):
        """
        Set whether to use antialiased rendering.

        Parameters
        ----------
        b : bool
        """
        if self._antialiased != b:
            self.stale = True
        self._antialiased = b

    def set_color(self, color):
        """
        Set the color of the line.

        Parameters
        ----------
        color : :mpltype:`color`
        """
        mcolors._check_color_like(color=color)
        self._color = color
        self.stale = True

    def set_drawstyle(self, drawstyle):
        """
        Set the drawstyle of the plot.

        The drawstyle determines how the points are connected.

        Parameters
        ----------
        drawstyle : {'default', 'steps', 'steps-pre', 'steps-mid', \
'steps-post'}, default: 'default'
            For 'default', the points are connected with straight lines.

            The steps variants connect the points with step-like lines,
            i.e. horizontal lines with vertical steps. They differ in the
            location of the step:

            - 'steps-pre': The step is at the beginning of the line segment,
              i.e. the line will be at the y-value of point to the right.
            - 'steps-mid': The step is halfway between the points.
            - 'steps-post: The step is at the end of the line segment,
              i.e. the line will be at the y-value of the point to the left.
            - 'steps' is equal to 'steps-pre' and is maintained for
              backward-compatibility.

            For examples see :doc:`/gallery/lines_bars_and_markers/step_demo`.
        """
        if drawstyle is None:
            drawstyle = 'default'
        _api.check_in_list(self.drawStyles, drawstyle=drawstyle)
        if self._drawstyle != drawstyle:
            self.stale = True
            # invalidate to trigger a recache of the path
            self._invalidx = True
        self._drawstyle = drawstyle

    def set_gapcolor(self, gapcolor):
        """
        Set a color to fill the gaps in the dashed line style.

        .. note::

            Striped lines are created by drawing two interleaved dashed lines.
            There can be overlaps between those two, which may result in
            artifacts when using transparency.

            This functionality is experimental and may change.

        Parameters
        ----------
        gapcolor : :mpltype:`color` or None
            The color with which to fill the gaps. If None, the gaps are
            unfilled.
        """
        if gapcolor is not None:
            mcolors._check_color_like(color=gapcolor)
        self._gapcolor = gapcolor
        self.stale = True

    def set_linewidth(self, w):
        """
        Set the line width in points.

        Parameters
        ----------
        w : float
            Line width, in points.
        """
        w = float(w)
        if self._linewidth != w:
            self.stale = True
        self._linewidth = w
        self._dash_pattern = _scale_dashes(*self._unscaled_dash_pattern, w)

    def set_linestyle(self, ls):
        """
        Set the linestyle of the line.

        Parameters
        ----------
        ls : {'-', '--', '-.', ':', '', (offset, on-off-seq), ...}
            Possible values:

            - A string:

              ==========================================  =================
              linestyle                                   description
              ==========================================  =================
              ``'-'`` or ``'solid'``                      solid line
              ``'--'`` or  ``'dashed'``                   dashed line
              ``'-.'`` or  ``'dashdot'``                  dash-dotted line
              ``':'`` or ``'dotted'``                     dotted line
              ``'none'``, ``'None'``, ``' '``, or ``''``  draw nothing
              ==========================================  =================

            - Alternatively a dash tuple of the following form can be
              provided::

                  (offset, onoffseq)

              where ``onoffseq`` is an even length tuple of on and off ink
              in points. See also :meth:`set_dashes`.

            For examples see :doc:`/gallery/lines_bars_and_markers/linestyles`.
        """
        if isinstance(ls, str):
            if ls in [' ', '', 'none']:
                ls = 'None'
            _api.check_in_list([*self._lineStyles, *ls_mapper_r], ls=ls)
            if ls not in self._lineStyles:
                ls = ls_mapper_r[ls]
            self._linestyle = ls
        else:
            self._linestyle = '--'
        self._unscaled_dash_pattern = _get_dash_pattern(ls)
        self._dash_pattern = _scale_dashes(
            *self._unscaled_dash_pattern, self._linewidth)
        self.stale = True

    @_docstring.interpd
    def set_marker(self, marker):
        """
        Set the line marker.

        Parameters
        ----------
        marker : marker style string, `~.path.Path` or `~.markers.MarkerStyle`
            See `~matplotlib.markers` for full description of possible
            arguments.
        """
        self._marker = MarkerStyle(marker, self._marker.get_fillstyle())
        self.stale = True

    def _set_markercolor(self, name, has_rcdefault, val):
        if val is None:
            val = mpl.rcParams[f"lines.{name}"] if has_rcdefault else "auto"
        attr = f"_{name}"
        current = getattr(self, attr)
        if current is None:
            self.stale = True
        else:
            neq = current != val
            # Much faster than `np.any(current != val)` if no arrays are used.
            if neq.any() if isinstance(neq, np.ndarray) else neq:
                self.stale = True
        setattr(self, attr, val)

    def set_markeredgecolor(self, ec):
        """
        Set the marker edge color.

        Parameters
        ----------
        ec : :mpltype:`color`
        """
        self._set_markercolor("markeredgecolor", True, ec)

    def set_markerfacecolor(self, fc):
        """
        Set the marker face color.

        Parameters
        ----------
        fc : :mpltype:`color`
        """
        self._set_markercolor("markerfacecolor", True, fc)

    def set_markerfacecoloralt(self, fc):
        """
        Set the alternate marker face color.

        Parameters
        ----------
        fc : :mpltype:`color`
        """
        self._set_markercolor("markerfacecoloralt", False, fc)

    def set_markeredgewidth(self, ew):
        """
        Set the marker edge width in points.

        Parameters
        ----------
        ew : float
             Marker edge width, in points.
        """
        if ew is None:
            ew = mpl.rcParams['lines.markeredgewidth']
        if self._markeredgewidth != ew:
            self.stale = True
        self._markeredgewidth = ew

    def set_markersize(self, sz):
        """
        Set the marker size in points.

        Parameters
        ----------
        sz : float
             Marker size, in points.
        """
        sz = float(sz)
        if self._markersize != sz:
            self.stale = True
        self._markersize = sz

    def set_xdata(self, x):
        """
        Set the data array for x.

        Parameters
        ----------
        x : 1D array

        See Also
        --------
        set_data
        set_ydata
        """
        if not np.iterable(x):
            raise RuntimeError('x must be a sequence')
        self._xorig = copy.copy(x)
        self._invalidx = True
        self.stale = True

    def set_ydata(self, y):
        """
        Set the data array for y.

        Parameters
        ----------
        y : 1D array

        See Also
        --------
        set_data
        set_xdata
        """
        if not np.iterable(y):
            raise RuntimeError('y must be a sequence')
        self._yorig = copy.copy(y)
        self._invalidy = True
        self.stale = True

    def set_dashes(self, seq):
        """
        Set the dash sequence.

        The dash sequence is a sequence of floats of even length describing
        the length of dashes and spaces in points.

        For example, (5, 2, 1, 2) describes a sequence of 5 point and 1 point
        dashes separated by 2 point spaces.

        See also `~.Line2D.set_gapcolor`, which allows those spaces to be
        filled with a color.

        Parameters
        ----------
        seq : sequence of floats (on/off ink in points) or (None, None)
            If *seq* is empty or ``(None, None)``, the linestyle will be set
            to solid.
        """
        if seq == (None, None) or len(seq) == 0:
            self.set_linestyle('-')
        else:
            self.set_linestyle((0, seq))

    def update_from(self, other):
        """Copy properties from *other* to self."""
        super().update_from(other)
        self._linestyle = other._linestyle
        self._linewidth = other._linewidth
        self._color = other._color
        self._gapcolor = other._gapcolor
        self._markersize = other._markersize
        self._markerfacecolor = other._markerfacecolor
        self._markerfacecoloralt = other._markerfacecoloralt
        self._markeredgecolor = other._markeredgecolor
        self._markeredgewidth = other._markeredgewidth
        self._unscaled_dash_pattern = other._unscaled_dash_pattern
        self._dash_pattern = other._dash_pattern
        self._dashcapstyle = other._dashcapstyle
        self._dashjoinstyle = other._dashjoinstyle
        self._solidcapstyle = other._solidcapstyle
        self._solidjoinstyle = other._solidjoinstyle

        self._linestyle = other._linestyle
        self._marker = MarkerStyle(marker=other._marker)
        self._drawstyle = other._drawstyle

    @_docstring.interpd
    def set_dash_joinstyle(self, s):
        """
        How to join segments of the line if it `~Line2D.is_dashed`.

        The default joinstyle is :rc:`lines.dash_joinstyle`.

        Parameters
        ----------
        s : `.JoinStyle` or %(JoinStyle)s
        """
        js = JoinStyle(s)
        if self._dashjoinstyle != js:
            self.stale = True
        self._dashjoinstyle = js

    @_docstring.interpd
    def set_solid_joinstyle(self, s):
        """
        How to join segments if the line is solid (not `~Line2D.is_dashed`).

        The default joinstyle is :rc:`lines.solid_joinstyle`.

        Parameters
        ----------
        s : `.JoinStyle` or %(JoinStyle)s
        """
        js = JoinStyle(s)
        if self._solidjoinstyle != js:
            self.stale = True
        self._solidjoinstyle = js

    def get_dash_joinstyle(self):
        """
        Return the `.JoinStyle` for dashed lines.

        See also `~.Line2D.set_dash_joinstyle`.
        """
        return self._dashjoinstyle.name

    def get_solid_joinstyle(self):
        """
        Return the `.JoinStyle` for solid lines.

        See also `~.Line2D.set_solid_joinstyle`.
        """
        return self._solidjoinstyle.name

    @_docstring.interpd
    def set_dash_capstyle(self, s):
        """
        How to draw the end caps if the line is `~Line2D.is_dashed`.

        The default capstyle is :rc:`lines.dash_capstyle`.

        Parameters
        ----------
        s : `.CapStyle` or %(CapStyle)s
        """
        cs = CapStyle(s)
        if self._dashcapstyle != cs:
            self.stale = True
        self._dashcapstyle = cs

    @_docstring.interpd
    def set_solid_capstyle(self, s):
        """
        How to draw the end caps if the line is solid (not `~Line2D.is_dashed`)

        The default capstyle is :rc:`lines.solid_capstyle`.

        Parameters
        ----------
        s : `.CapStyle` or %(CapStyle)s
        """
        cs = CapStyle(s)
        if self._solidcapstyle != cs:
            self.stale = True
        self._solidcapstyle = cs

    def get_dash_capstyle(self):
        """
        Return the `.CapStyle` for dashed lines.

        See also `~.Line2D.set_dash_capstyle`.
        """
        return self._dashcapstyle.name

    def get_solid_capstyle(self):
        """
        Return the `.CapStyle` for solid lines.

        See also `~.Line2D.set_solid_capstyle`.
        """
        return self._solidcapstyle.name

    def is_dashed(self):
        """
        Return whether line has a dashed linestyle.

        A custom linestyle is assumed to be dashed, we do not inspect the
        ``onoffseq`` directly.

        See also `~.Line2D.set_linestyle`.
        """
        return self._linestyle in ('--', '-.', ':')


class AxLine(Line2D):
    """
    A helper class that implements `~.Axes.axline`, by recomputing the artist
    transform at draw time.
    """

    def __init__(self, xy1, xy2, slope, **kwargs):
        """
        Parameters
        ----------
        xy1 : (float, float)
            The first set of (x, y) coordinates for the line to pass through.
        xy2 : (float, float) or None
            The second set of (x, y) coordinates for the line to pass through.
            Both *xy2* and *slope* must be passed, but one of them must be None.
        slope : float or None
            The slope of the line. Both *xy2* and *slope* must be passed, but one of
            them must be None.
        """
        super().__init__([0, 1], [0, 1], **kwargs)

        if (xy2 is None and slope is None or
                xy2 is not None and slope is not None):
            raise TypeError(
                "Exactly one of 'xy2' and 'slope' must be given")

        self._slope = slope
        self._xy1 = xy1
        self._xy2 = xy2

    def get_transform(self):
        ax = self.axes
        points_transform = self._transform - ax.transData + ax.transScale

        if self._xy2 is not None:
            # two points were given
            (x1, y1), (x2, y2) = \
                points_transform.transform([self._xy1, self._xy2])
            dx = x2 - x1
            dy = y2 - y1
            if dx == 0:
                if dy == 0:
                    raise ValueError(
                        f"Cannot draw a line through two identical points "
                        f"(x={(x1, x2)}, y={(y1, y2)})")
                slope = np.inf
            else:
                slope = dy / dx
        else:
            # one point and a slope were given
            x1, y1 = points_transform.transform(self._xy1)
            slope = self._slope
        (vxlo, vylo), (vxhi, vyhi) = ax.transScale.transform(ax.viewLim)
        # General case: find intersections with view limits in either
        # direction, and draw between the middle two points.
        if slope == 0:
            start = vxlo, y1
            stop = vxhi, y1
        elif np.isinf(slope):
            start = x1, vylo
            stop = x1, vyhi
        else:
            _, start, stop, _ = sorted([
                (vxlo, y1 + (vxlo - x1) * slope),
                (vxhi, y1 + (vxhi - x1) * slope),
                (x1 + (vylo - y1) / slope, vylo),
                (x1 + (vyhi - y1) / slope, vyhi),
            ])
        return (BboxTransformTo(Bbox([start, stop]))
                + ax.transLimits + ax.transAxes)

    def draw(self, renderer):
        self._transformed_path = None  # Force regen.
        super().draw(renderer)

    def get_xy1(self):
        """Return the *xy1* value of the line."""
        return self._xy1

    def get_xy2(self):
        """Return the *xy2* value of the line."""
        return self._xy2

    def get_slope(self):
        """Return the *slope* value of the line."""
        return self._slope

    def set_xy1(self, *args, **kwargs):
        """
        Set the *xy1* value of the line.

        Parameters
        ----------
        xy1 : tuple[float, float]
            Points for the line to pass through.
        """
        params = _api.select_matching_signature([
            lambda self, x, y: locals(), lambda self, xy1: locals(),
        ], self, *args, **kwargs)
        if "x" in params:
            _api.warn_deprecated("3.10", message=(
                "Passing x and y separately to AxLine.set_xy1 is deprecated since "
                "%(since)s; pass them as a single tuple instead."))
            xy1 = params["x"], params["y"]
        else:
            xy1 = params["xy1"]
        self._xy1 = xy1

    def set_xy2(self, *args, **kwargs):
        """
        Set the *xy2* value of the line.

        .. note::

            You can only set *xy2* if the line was created using the *xy2*
            parameter. If the line was created using *slope*, please use
            `~.AxLine.set_slope`.

        Parameters
        ----------
        xy2 : tuple[float, float]
            Points for the line to pass through.
        """
        if self._slope is None:
            params = _api.select_matching_signature([
                lambda self, x, y: locals(), lambda self, xy2: locals(),
            ], self, *args, **kwargs)
            if "x" in params:
                _api.warn_deprecated("3.10", message=(
                    "Passing x and y separately to AxLine.set_xy2 is deprecated since "
                    "%(since)s; pass them as a single tuple instead."))
                xy2 = params["x"], params["y"]
            else:
                xy2 = params["xy2"]
            self._xy2 = xy2
        else:
            raise ValueError("Cannot set an 'xy2' value while 'slope' is set;"
                             " they differ but their functionalities overlap")

    def set_slope(self, slope):
        """
        Set the *slope* value of the line.

        .. note::

            You can only set *slope* if the line was created using the *slope*
            parameter. If the line was created using *xy2*, please use
            `~.AxLine.set_xy2`.

        Parameters
        ----------
        slope : float
            The slope of the line.
        """
        if self._xy2 is None:
            self._slope = slope
        else:
            raise ValueError("Cannot set a 'slope' value while 'xy2' is set;"
                             " they differ but their functionalities overlap")


class VertexSelector:
    """
    Manage the callbacks to maintain a list of selected vertices for `.Line2D`.
    Derived classes should override the `process_selected` method to do
    something with the picks.

    Here is an example which highlights the selected verts with red circles::

        import numpy as np
        import matplotlib.pyplot as plt
        import matplotlib.lines as lines

        class HighlightSelected(lines.VertexSelector):
            def __init__(self, line, fmt='ro', **kwargs):
                super().__init__(line)
                self.markers, = self.axes.plot([], [], fmt, **kwargs)

            def process_selected(self, ind, xs, ys):
                self.markers.set_data(xs, ys)
                self.canvas.draw()

        fig, ax = plt.subplots()
        x, y = np.random.rand(2, 30)
        line, = ax.plot(x, y, 'bs-', picker=5)

        selector = HighlightSelected(line)
        plt.show()
    """

    def __init__(self, line):
        """
        Parameters
        ----------
        line : `~matplotlib.lines.Line2D`
            The line must already have been added to an `~.axes.Axes` and must
            have its picker property set.
        """
        if line.axes is None:
            raise RuntimeError('You must first add the line to the Axes')
        if line.get_picker() is None:
            raise RuntimeError('You must first set the picker property '
                               'of the line')
        self.axes = line.axes
        self.line = line
        self.cid = self.canvas.callbacks._connect_picklable(
            'pick_event', self.onpick)
        self.ind = set()

    canvas = property(lambda self: self.axes.get_figure(root=True).canvas)

    def process_selected(self, ind, xs, ys):
        """
        Default "do nothing" implementation of the `process_selected` method.

        Parameters
        ----------
        ind : list of int
            The indices of the selected vertices.
        xs, ys : array-like
            The coordinates of the selected vertices.
        """
        pass

    def onpick(self, event):
        """When the line is picked, update the set of selected indices."""
        if event.artist is not self.line:
            return
        self.ind ^= set(event.ind)
        ind = sorted(self.ind)
        xdata, ydata = self.line.get_data()
        self.process_selected(ind, xdata[ind], ydata[ind])


lineStyles = Line2D._lineStyles
lineMarkers = MarkerStyle.markers
drawStyles = Line2D.drawStyles
fillStyles = MarkerStyle.fillstyles

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\merger.py ===
"""
Merge OpenType Layout tables (GDEF / GPOS / GSUB).
"""

import os
import copy
import enum
from operator import ior
import logging
from fontTools.colorLib.builder import MAX_PAINT_COLR_LAYER_COUNT, LayerReuseCache
from fontTools.misc import classifyTools
from fontTools.misc.roundTools import otRound
from fontTools.misc.treeTools import build_n_ary_tree
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables import otBase as otBase
from fontTools.ttLib.tables.otConverters import BaseFixedValue
from fontTools.ttLib.tables.otTraverse import dfs_base_table
from fontTools.ttLib.tables.DefaultTable import DefaultTable
from fontTools.varLib import builder, models, varStore
from fontTools.varLib.models import nonNone, allNone, allEqual, allEqualTo, subList
from fontTools.varLib.varStore import VarStoreInstancer
from functools import reduce
from fontTools.otlLib.builder import buildSinglePos
from fontTools.otlLib.optimize.gpos import (
    _compression_level_from_env,
    compact_pair_pos,
)

log = logging.getLogger("fontTools.varLib.merger")

from .errors import (
    ShouldBeConstant,
    FoundANone,
    MismatchedTypes,
    NotANone,
    LengthsDiffer,
    KeysDiffer,
    InconsistentGlyphOrder,
    InconsistentExtensions,
    InconsistentFormats,
    UnsupportedFormat,
    VarLibMergeError,
)


class Merger(object):
    def __init__(self, font=None):
        self.font = font
        # mergeTables populates this from the parent's master ttfs
        self.ttfs = None

    @classmethod
    def merger(celf, clazzes, attrs=(None,)):
        assert celf != Merger, "Subclass Merger instead."
        if "mergers" not in celf.__dict__:
            celf.mergers = {}
        if type(clazzes) in (type, enum.EnumMeta):
            clazzes = (clazzes,)
        if type(attrs) == str:
            attrs = (attrs,)

        def wrapper(method):
            assert method.__name__ == "merge"
            done = []
            for clazz in clazzes:
                if clazz in done:
                    continue  # Support multiple names of a clazz
                done.append(clazz)
                mergers = celf.mergers.setdefault(clazz, {})
                for attr in attrs:
                    assert attr not in mergers, (
                        "Oops, class '%s' has merge function for '%s' defined already."
                        % (clazz.__name__, attr)
                    )
                    mergers[attr] = method
            return None

        return wrapper

    @classmethod
    def mergersFor(celf, thing, _default={}):
        typ = type(thing)

        for celf in celf.mro():
            mergers = getattr(celf, "mergers", None)
            if mergers is None:
                break

            m = celf.mergers.get(typ, None)
            if m is not None:
                return m

        return _default

    def mergeObjects(self, out, lst, exclude=()):
        if hasattr(out, "ensureDecompiled"):
            out.ensureDecompiled(recurse=False)
        for item in lst:
            if hasattr(item, "ensureDecompiled"):
                item.ensureDecompiled(recurse=False)
        keys = sorted(vars(out).keys())
        if not all(keys == sorted(vars(v).keys()) for v in lst):
            raise KeysDiffer(
                self, expected=keys, got=[sorted(vars(v).keys()) for v in lst]
            )
        mergers = self.mergersFor(out)
        defaultMerger = mergers.get("*", self.__class__.mergeThings)
        try:
            for key in keys:
                if key in exclude:
                    continue
                value = getattr(out, key)
                values = [getattr(table, key) for table in lst]
                mergerFunc = mergers.get(key, defaultMerger)
                mergerFunc(self, value, values)
        except VarLibMergeError as e:
            e.stack.append("." + key)
            raise

    def mergeLists(self, out, lst):
        if not allEqualTo(out, lst, len):
            raise LengthsDiffer(self, expected=len(out), got=[len(x) for x in lst])
        for i, (value, values) in enumerate(zip(out, zip(*lst))):
            try:
                self.mergeThings(value, values)
            except VarLibMergeError as e:
                e.stack.append("[%d]" % i)
                raise

    def mergeThings(self, out, lst):
        if not allEqualTo(out, lst, type):
            raise MismatchedTypes(
                self, expected=type(out).__name__, got=[type(x).__name__ for x in lst]
            )
        mergerFunc = self.mergersFor(out).get(None, None)
        if mergerFunc is not None:
            mergerFunc(self, out, lst)
        elif isinstance(out, enum.Enum):
            # need to special-case Enums as have __dict__ but are not regular 'objects',
            # otherwise mergeObjects/mergeThings get trapped in a RecursionError
            if not allEqualTo(out, lst):
                raise ShouldBeConstant(self, expected=out, got=lst)
        elif hasattr(out, "__dict__"):
            self.mergeObjects(out, lst)
        elif isinstance(out, list):
            self.mergeLists(out, lst)
        else:
            if not allEqualTo(out, lst):
                raise ShouldBeConstant(self, expected=out, got=lst)

    def mergeTables(self, font, master_ttfs, tableTags):
        for tag in tableTags:
            if tag not in font:
                continue
            try:
                self.ttfs = master_ttfs
                self.mergeThings(font[tag], [m.get(tag) for m in master_ttfs])
            except VarLibMergeError as e:
                e.stack.append(tag)
                raise


#
# Aligning merger
#
class AligningMerger(Merger):
    pass


@AligningMerger.merger(ot.GDEF, "GlyphClassDef")
def merge(merger, self, lst):
    if self is None:
        if not allNone(lst):
            raise NotANone(merger, expected=None, got=lst)
        return

    lst = [l.classDefs for l in lst]
    self.classDefs = {}
    # We only care about the .classDefs
    self = self.classDefs

    allKeys = set()
    allKeys.update(*[l.keys() for l in lst])
    for k in allKeys:
        allValues = nonNone(l.get(k) for l in lst)
        if not allEqual(allValues):
            raise ShouldBeConstant(
                merger, expected=allValues[0], got=lst, stack=["." + k]
            )
        if not allValues:
            self[k] = None
        else:
            self[k] = allValues[0]


def _SinglePosUpgradeToFormat2(self):
    if self.Format == 2:
        return self

    ret = ot.SinglePos()
    ret.Format = 2
    ret.Coverage = self.Coverage
    ret.ValueFormat = self.ValueFormat
    ret.Value = [self.Value for _ in ret.Coverage.glyphs]
    ret.ValueCount = len(ret.Value)

    return ret


def _merge_GlyphOrders(font, lst, values_lst=None, default=None):
    """Takes font and list of glyph lists (must be sorted by glyph id), and returns
    two things:
    - Combined glyph list,
    - If values_lst is None, return input glyph lists, but padded with None when a glyph
      was missing in a list.  Otherwise, return values_lst list-of-list, padded with None
      to match combined glyph lists.
    """
    if values_lst is None:
        dict_sets = [set(l) for l in lst]
    else:
        dict_sets = [{g: v for g, v in zip(l, vs)} for l, vs in zip(lst, values_lst)]
    combined = set()
    combined.update(*dict_sets)

    sortKey = font.getReverseGlyphMap().__getitem__
    order = sorted(combined, key=sortKey)
    # Make sure all input glyphsets were in proper order
    if not all(sorted(vs, key=sortKey) == vs for vs in lst):
        raise InconsistentGlyphOrder()
    del combined

    paddedValues = None
    if values_lst is None:
        padded = [
            [glyph if glyph in dict_set else default for glyph in order]
            for dict_set in dict_sets
        ]
    else:
        assert len(lst) == len(values_lst)
        padded = [
            [dict_set[glyph] if glyph in dict_set else default for glyph in order]
            for dict_set in dict_sets
        ]
    return order, padded


@AligningMerger.merger(otBase.ValueRecord)
def merge(merger, self, lst):
    # Code below sometimes calls us with self being
    # a new object. Copy it from lst and recurse.
    self.__dict__ = lst[0].__dict__.copy()
    merger.mergeObjects(self, lst)


@AligningMerger.merger(ot.Anchor)
def merge(merger, self, lst):
    # Code below sometimes calls us with self being
    # a new object. Copy it from lst and recurse.
    self.__dict__ = lst[0].__dict__.copy()
    merger.mergeObjects(self, lst)


def _Lookup_SinglePos_get_effective_value(merger, subtables, glyph):
    for self in subtables:
        if (
            self is None
            or type(self) != ot.SinglePos
            or self.Coverage is None
            or glyph not in self.Coverage.glyphs
        ):
            continue
        if self.Format == 1:
            return self.Value
        elif self.Format == 2:
            return self.Value[self.Coverage.glyphs.index(glyph)]
        else:
            raise UnsupportedFormat(merger, subtable="single positioning lookup")
    return None


def _Lookup_PairPos_get_effective_value_pair(
    merger, subtables, firstGlyph, secondGlyph
):
    for self in subtables:
        if (
            self is None
            or type(self) != ot.PairPos
            or self.Coverage is None
            or firstGlyph not in self.Coverage.glyphs
        ):
            continue
        if self.Format == 1:
            ps = self.PairSet[self.Coverage.glyphs.index(firstGlyph)]
            pvr = ps.PairValueRecord
            for rec in pvr:  # TODO Speed up
                if rec.SecondGlyph == secondGlyph:
                    return rec
            continue
        elif self.Format == 2:
            klass1 = self.ClassDef1.classDefs.get(firstGlyph, 0)
            klass2 = self.ClassDef2.classDefs.get(secondGlyph, 0)
            return self.Class1Record[klass1].Class2Record[klass2]
        else:
            raise UnsupportedFormat(merger, subtable="pair positioning lookup")
    return None


@AligningMerger.merger(ot.SinglePos)
def merge(merger, self, lst):
    self.ValueFormat = valueFormat = reduce(int.__or__, [l.ValueFormat for l in lst], 0)
    if not (len(lst) == 1 or (valueFormat & ~0xF == 0)):
        raise UnsupportedFormat(merger, subtable="single positioning lookup")

    # If all have same coverage table and all are format 1,
    coverageGlyphs = self.Coverage.glyphs
    if all(v.Format == 1 for v in lst) and all(
        coverageGlyphs == v.Coverage.glyphs for v in lst
    ):
        self.Value = otBase.ValueRecord(valueFormat, self.Value)
        if valueFormat != 0:
            # If v.Value is None, it means a kerning of 0; we want
            # it to participate in the model still.
            # https://github.com/fonttools/fonttools/issues/3111
            merger.mergeThings(
                self.Value,
                [v.Value if v.Value is not None else otBase.ValueRecord() for v in lst],
            )
        self.ValueFormat = self.Value.getFormat()
        return

    # Upgrade everything to Format=2
    self.Format = 2
    lst = [_SinglePosUpgradeToFormat2(v) for v in lst]

    # Align them
    glyphs, padded = _merge_GlyphOrders(
        merger.font, [v.Coverage.glyphs for v in lst], [v.Value for v in lst]
    )

    self.Coverage.glyphs = glyphs
    self.Value = [otBase.ValueRecord(valueFormat) for _ in glyphs]
    self.ValueCount = len(self.Value)

    for i, values in enumerate(padded):
        for j, glyph in enumerate(glyphs):
            if values[j] is not None:
                continue
            # Fill in value from other subtables
            # Note!!! This *might* result in behavior change if ValueFormat2-zeroedness
            # is different between used subtable and current subtable!
            # TODO(behdad) Check and warn if that happens?
            v = _Lookup_SinglePos_get_effective_value(
                merger, merger.lookup_subtables[i], glyph
            )
            if v is None:
                v = otBase.ValueRecord(valueFormat)
            values[j] = v

    merger.mergeLists(self.Value, padded)

    # Merge everything else; though, there shouldn't be anything else. :)
    merger.mergeObjects(
        self, lst, exclude=("Format", "Coverage", "Value", "ValueCount", "ValueFormat")
    )
    self.ValueFormat = reduce(
        int.__or__, [v.getEffectiveFormat() for v in self.Value], 0
    )


@AligningMerger.merger(ot.PairSet)
def merge(merger, self, lst):
    # Align them
    glyphs, padded = _merge_GlyphOrders(
        merger.font,
        [[v.SecondGlyph for v in vs.PairValueRecord] for vs in lst],
        [vs.PairValueRecord for vs in lst],
    )

    self.PairValueRecord = pvrs = []
    for glyph in glyphs:
        pvr = ot.PairValueRecord()
        pvr.SecondGlyph = glyph
        pvr.Value1 = (
            otBase.ValueRecord(merger.valueFormat1) if merger.valueFormat1 else None
        )
        pvr.Value2 = (
            otBase.ValueRecord(merger.valueFormat2) if merger.valueFormat2 else None
        )
        pvrs.append(pvr)
    self.PairValueCount = len(self.PairValueRecord)

    for i, values in enumerate(padded):
        for j, glyph in enumerate(glyphs):
            # Fill in value from other subtables
            v = ot.PairValueRecord()
            v.SecondGlyph = glyph
            if values[j] is not None:
                vpair = values[j]
            else:
                vpair = _Lookup_PairPos_get_effective_value_pair(
                    merger, merger.lookup_subtables[i], self._firstGlyph, glyph
                )
            if vpair is None:
                v1, v2 = None, None
            else:
                v1 = getattr(vpair, "Value1", None)
                v2 = getattr(vpair, "Value2", None)
            v.Value1 = (
                otBase.ValueRecord(merger.valueFormat1, src=v1)
                if merger.valueFormat1
                else None
            )
            v.Value2 = (
                otBase.ValueRecord(merger.valueFormat2, src=v2)
                if merger.valueFormat2
                else None
            )
            values[j] = v
    del self._firstGlyph

    merger.mergeLists(self.PairValueRecord, padded)


def _PairPosFormat1_merge(self, lst, merger):
    assert allEqual(
        [l.ValueFormat2 == 0 for l in lst if l.PairSet]
    ), "Report bug against fonttools."

    # Merge everything else; makes sure Format is the same.
    merger.mergeObjects(
        self,
        lst,
        exclude=("Coverage", "PairSet", "PairSetCount", "ValueFormat1", "ValueFormat2"),
    )

    empty = ot.PairSet()
    empty.PairValueRecord = []
    empty.PairValueCount = 0

    # Align them
    glyphs, padded = _merge_GlyphOrders(
        merger.font,
        [v.Coverage.glyphs for v in lst],
        [v.PairSet for v in lst],
        default=empty,
    )

    self.Coverage.glyphs = glyphs
    self.PairSet = [ot.PairSet() for _ in glyphs]
    self.PairSetCount = len(self.PairSet)
    for glyph, ps in zip(glyphs, self.PairSet):
        ps._firstGlyph = glyph

    merger.mergeLists(self.PairSet, padded)


def _ClassDef_invert(self, allGlyphs=None):
    if isinstance(self, dict):
        classDefs = self
    else:
        classDefs = self.classDefs if self and self.classDefs else {}
    m = max(classDefs.values()) if classDefs else 0

    ret = []
    for _ in range(m + 1):
        ret.append(set())

    for k, v in classDefs.items():
        ret[v].add(k)

    # Class-0 is special.  It's "everything else".
    if allGlyphs is None:
        ret[0] = None
    else:
        # Limit all classes to glyphs in allGlyphs.
        # Collect anything without a non-zero class into class=zero.
        ret[0] = class0 = set(allGlyphs)
        for s in ret[1:]:
            s.intersection_update(class0)
            class0.difference_update(s)

    return ret


def _ClassDef_merge_classify(lst, allGlyphses=None):
    self = ot.ClassDef()
    self.classDefs = classDefs = {}
    allGlyphsesWasNone = allGlyphses is None
    if allGlyphsesWasNone:
        allGlyphses = [None] * len(lst)

    classifier = classifyTools.Classifier()
    for classDef, allGlyphs in zip(lst, allGlyphses):
        sets = _ClassDef_invert(classDef, allGlyphs)
        if allGlyphs is None:
            sets = sets[1:]
        classifier.update(sets)
    classes = classifier.getClasses()

    if allGlyphsesWasNone:
        classes.insert(0, set())

    for i, classSet in enumerate(classes):
        if i == 0:
            continue
        for g in classSet:
            classDefs[g] = i

    return self, classes


def _PairPosFormat2_align_matrices(self, lst, font, transparent=False):
    matrices = [l.Class1Record for l in lst]

    # Align first classes
    self.ClassDef1, classes = _ClassDef_merge_classify(
        [l.ClassDef1 for l in lst], [l.Coverage.glyphs for l in lst]
    )
    self.Class1Count = len(classes)
    new_matrices = []
    for l, matrix in zip(lst, matrices):
        nullRow = None
        coverage = set(l.Coverage.glyphs)
        classDef1 = l.ClassDef1.classDefs
        class1Records = []
        for classSet in classes:
            exemplarGlyph = next(iter(classSet))
            if exemplarGlyph not in coverage:
                # Follow-up to e6125b353e1f54a0280ded5434b8e40d042de69f,
                # Fixes https://github.com/googlei18n/fontmake/issues/470
                # Again, revert 8d441779e5afc664960d848f62c7acdbfc71d7b9
                # when merger becomes selfless.
                nullRow = None
                if nullRow is None:
                    nullRow = ot.Class1Record()
                    class2records = nullRow.Class2Record = []
                    # TODO: When merger becomes selfless, revert e6125b353e1f54a0280ded5434b8e40d042de69f
                    for _ in range(l.Class2Count):
                        if transparent:
                            rec2 = None
                        else:
                            rec2 = ot.Class2Record()
                            rec2.Value1 = (
                                otBase.ValueRecord(self.ValueFormat1)
                                if self.ValueFormat1
                                else None
                            )
                            rec2.Value2 = (
                                otBase.ValueRecord(self.ValueFormat2)
                                if self.ValueFormat2
                                else None
                            )
                        class2records.append(rec2)
                rec1 = nullRow
            else:
                klass = classDef1.get(exemplarGlyph, 0)
                rec1 = matrix[klass]  # TODO handle out-of-range?
            class1Records.append(rec1)
        new_matrices.append(class1Records)
    matrices = new_matrices
    del new_matrices

    # Align second classes
    self.ClassDef2, classes = _ClassDef_merge_classify([l.ClassDef2 for l in lst])
    self.Class2Count = len(classes)
    new_matrices = []
    for l, matrix in zip(lst, matrices):
        classDef2 = l.ClassDef2.classDefs
        class1Records = []
        for rec1old in matrix:
            oldClass2Records = rec1old.Class2Record
            rec1new = ot.Class1Record()
            class2Records = rec1new.Class2Record = []
            for classSet in classes:
                if not classSet:  # class=0
                    rec2 = oldClass2Records[0]
                else:
                    exemplarGlyph = next(iter(classSet))
                    klass = classDef2.get(exemplarGlyph, 0)
                    rec2 = oldClass2Records[klass]
                class2Records.append(copy.deepcopy(rec2))
            class1Records.append(rec1new)
        new_matrices.append(class1Records)
    matrices = new_matrices
    del new_matrices

    return matrices


def _PairPosFormat2_merge(self, lst, merger):
    assert allEqual(
        [l.ValueFormat2 == 0 for l in lst if l.Class1Record]
    ), "Report bug against fonttools."

    merger.mergeObjects(
        self,
        lst,
        exclude=(
            "Coverage",
            "ClassDef1",
            "Class1Count",
            "ClassDef2",
            "Class2Count",
            "Class1Record",
            "ValueFormat1",
            "ValueFormat2",
        ),
    )

    # Align coverages
    glyphs, _ = _merge_GlyphOrders(merger.font, [v.Coverage.glyphs for v in lst])
    self.Coverage.glyphs = glyphs

    # Currently, if the coverage of PairPosFormat2 subtables are different,
    # we do NOT bother walking down the subtable list when filling in new
    # rows for alignment.  As such, this is only correct if current subtable
    # is the last subtable in the lookup.  Ensure that.
    #
    # Note that our canonicalization process merges trailing PairPosFormat2's,
    # so in reality this is rare.
    for l, subtables in zip(lst, merger.lookup_subtables):
        if l.Coverage.glyphs != glyphs:
            assert l == subtables[-1]

    matrices = _PairPosFormat2_align_matrices(self, lst, merger.font)

    self.Class1Record = list(matrices[0])  # TODO move merger to be selfless
    merger.mergeLists(self.Class1Record, matrices)


@AligningMerger.merger(ot.PairPos)
def merge(merger, self, lst):
    merger.valueFormat1 = self.ValueFormat1 = reduce(
        int.__or__, [l.ValueFormat1 for l in lst], 0
    )
    merger.valueFormat2 = self.ValueFormat2 = reduce(
        int.__or__, [l.ValueFormat2 for l in lst], 0
    )

    if self.Format == 1:
        _PairPosFormat1_merge(self, lst, merger)
    elif self.Format == 2:
        _PairPosFormat2_merge(self, lst, merger)
    else:
        raise UnsupportedFormat(merger, subtable="pair positioning lookup")

    del merger.valueFormat1, merger.valueFormat2

    # Now examine the list of value records, and update to the union of format values,
    # as merge might have created new values.
    vf1 = 0
    vf2 = 0
    if self.Format == 1:
        for pairSet in self.PairSet:
            for pairValueRecord in pairSet.PairValueRecord:
                pv1 = getattr(pairValueRecord, "Value1", None)
                if pv1 is not None:
                    vf1 |= pv1.getFormat()
                pv2 = getattr(pairValueRecord, "Value2", None)
                if pv2 is not None:
                    vf2 |= pv2.getFormat()
    elif self.Format == 2:
        for class1Record in self.Class1Record:
            for class2Record in class1Record.Class2Record:
                pv1 = getattr(class2Record, "Value1", None)
                if pv1 is not None:
                    vf1 |= pv1.getFormat()
                pv2 = getattr(class2Record, "Value2", None)
                if pv2 is not None:
                    vf2 |= pv2.getFormat()
    self.ValueFormat1 = vf1
    self.ValueFormat2 = vf2


def _MarkBasePosFormat1_merge(self, lst, merger, Mark="Mark", Base="Base"):
    self.ClassCount = max(l.ClassCount for l in lst)

    MarkCoverageGlyphs, MarkRecords = _merge_GlyphOrders(
        merger.font,
        [getattr(l, Mark + "Coverage").glyphs for l in lst],
        [getattr(l, Mark + "Array").MarkRecord for l in lst],
    )
    getattr(self, Mark + "Coverage").glyphs = MarkCoverageGlyphs

    BaseCoverageGlyphs, BaseRecords = _merge_GlyphOrders(
        merger.font,
        [getattr(l, Base + "Coverage").glyphs for l in lst],
        [getattr(getattr(l, Base + "Array"), Base + "Record") for l in lst],
    )
    getattr(self, Base + "Coverage").glyphs = BaseCoverageGlyphs

    # MarkArray
    records = []
    for g, glyphRecords in zip(MarkCoverageGlyphs, zip(*MarkRecords)):
        allClasses = [r.Class for r in glyphRecords if r is not None]

        # TODO Right now we require that all marks have same class in
        # all masters that cover them.  This is not required.
        #
        # We can relax that by just requiring that all marks that have
        # the same class in a master, have the same class in every other
        # master.  Indeed, if, say, a sparse master only covers one mark,
        # that mark probably will get class 0, which would possibly be
        # different from its class in other masters.
        #
        # We can even go further and reclassify marks to support any
        # input.  But, since, it's unlikely that two marks being both,
        # say, "top" in one master, and one being "top" and other being
        # "top-right" in another master, we shouldn't do that, as any
        # failures in that case will probably signify mistakes in the
        # input masters.

        if not allEqual(allClasses):
            raise ShouldBeConstant(merger, expected=allClasses[0], got=allClasses)
        else:
            rec = ot.MarkRecord()
            rec.Class = allClasses[0]
            allAnchors = [None if r is None else r.MarkAnchor for r in glyphRecords]
            if allNone(allAnchors):
                anchor = None
            else:
                anchor = ot.Anchor()
                anchor.Format = 1
                merger.mergeThings(anchor, allAnchors)
            rec.MarkAnchor = anchor
        records.append(rec)
    array = ot.MarkArray()
    array.MarkRecord = records
    array.MarkCount = len(records)
    setattr(self, Mark + "Array", array)

    # BaseArray
    records = []
    for g, glyphRecords in zip(BaseCoverageGlyphs, zip(*BaseRecords)):
        if allNone(glyphRecords):
            rec = None
        else:
            rec = getattr(ot, Base + "Record")()
            anchors = []
            setattr(rec, Base + "Anchor", anchors)
            glyphAnchors = [
                [] if r is None else getattr(r, Base + "Anchor") for r in glyphRecords
            ]
            for l in glyphAnchors:
                l.extend([None] * (self.ClassCount - len(l)))
            for allAnchors in zip(*glyphAnchors):
                if allNone(allAnchors):
                    anchor = None
                else:
                    anchor = ot.Anchor()
                    anchor.Format = 1
                    merger.mergeThings(anchor, allAnchors)
                anchors.append(anchor)
        records.append(rec)
    array = getattr(ot, Base + "Array")()
    setattr(array, Base + "Record", records)
    setattr(array, Base + "Count", len(records))
    setattr(self, Base + "Array", array)


@AligningMerger.merger(ot.MarkBasePos)
def merge(merger, self, lst):
    if not allEqualTo(self.Format, (l.Format for l in lst)):
        raise InconsistentFormats(
            merger,
            subtable="mark-to-base positioning lookup",
            expected=self.Format,
            got=[l.Format for l in lst],
        )
    if self.Format == 1:
        _MarkBasePosFormat1_merge(self, lst, merger)
    else:
        raise UnsupportedFormat(merger, subtable="mark-to-base positioning lookup")


@AligningMerger.merger(ot.MarkMarkPos)
def merge(merger, self, lst):
    if not allEqualTo(self.Format, (l.Format for l in lst)):
        raise InconsistentFormats(
            merger,
            subtable="mark-to-mark positioning lookup",
            expected=self.Format,
            got=[l.Format for l in lst],
        )
    if self.Format == 1:
        _MarkBasePosFormat1_merge(self, lst, merger, "Mark1", "Mark2")
    else:
        raise UnsupportedFormat(merger, subtable="mark-to-mark positioning lookup")


def _PairSet_flatten(lst, font):
    self = ot.PairSet()
    self.Coverage = ot.Coverage()

    # Align them
    glyphs, padded = _merge_GlyphOrders(
        font,
        [[v.SecondGlyph for v in vs.PairValueRecord] for vs in lst],
        [vs.PairValueRecord for vs in lst],
    )

    self.Coverage.glyphs = glyphs
    self.PairValueRecord = pvrs = []
    for values in zip(*padded):
        for v in values:
            if v is not None:
                pvrs.append(v)
                break
        else:
            assert False
    self.PairValueCount = len(self.PairValueRecord)

    return self


def _Lookup_PairPosFormat1_subtables_flatten(lst, font):
    assert allEqual(
        [l.ValueFormat2 == 0 for l in lst if l.PairSet]
    ), "Report bug against fonttools."

    self = ot.PairPos()
    self.Format = 1
    self.Coverage = ot.Coverage()
    self.ValueFormat1 = reduce(int.__or__, [l.ValueFormat1 for l in lst], 0)
    self.ValueFormat2 = reduce(int.__or__, [l.ValueFormat2 for l in lst], 0)

    # Align them
    glyphs, padded = _merge_GlyphOrders(
        font, [v.Coverage.glyphs for v in lst], [v.PairSet for v in lst]
    )

    self.Coverage.glyphs = glyphs
    self.PairSet = [
        _PairSet_flatten([v for v in values if v is not None], font)
        for values in zip(*padded)
    ]
    self.PairSetCount = len(self.PairSet)
    return self


def _Lookup_PairPosFormat2_subtables_flatten(lst, font):
    assert allEqual(
        [l.ValueFormat2 == 0 for l in lst if l.Class1Record]
    ), "Report bug against fonttools."

    self = ot.PairPos()
    self.Format = 2
    self.Coverage = ot.Coverage()
    self.ValueFormat1 = reduce(int.__or__, [l.ValueFormat1 for l in lst], 0)
    self.ValueFormat2 = reduce(int.__or__, [l.ValueFormat2 for l in lst], 0)

    # Align them
    glyphs, _ = _merge_GlyphOrders(font, [v.Coverage.glyphs for v in lst])
    self.Coverage.glyphs = glyphs

    matrices = _PairPosFormat2_align_matrices(self, lst, font, transparent=True)

    matrix = self.Class1Record = []
    for rows in zip(*matrices):
        row = ot.Class1Record()
        matrix.append(row)
        row.Class2Record = []
        row = row.Class2Record
        for cols in zip(*list(r.Class2Record for r in rows)):
            col = next(iter(c for c in cols if c is not None))
            row.append(col)

    return self


def _Lookup_PairPos_subtables_canonicalize(lst, font):
    """Merge multiple Format1 subtables at the beginning of lst,
    and merge multiple consecutive Format2 subtables that have the same
    Class2 (ie. were split because of offset overflows).  Returns new list."""
    lst = list(lst)

    l = len(lst)
    i = 0
    while i < l and lst[i].Format == 1:
        i += 1
    lst[:i] = [_Lookup_PairPosFormat1_subtables_flatten(lst[:i], font)]

    l = len(lst)
    i = l
    while i > 0 and lst[i - 1].Format == 2:
        i -= 1
    lst[i:] = [_Lookup_PairPosFormat2_subtables_flatten(lst[i:], font)]

    return lst


def _Lookup_SinglePos_subtables_flatten(lst, font, min_inclusive_rec_format):
    glyphs, _ = _merge_GlyphOrders(font, [v.Coverage.glyphs for v in lst], None)
    num_glyphs = len(glyphs)
    new = ot.SinglePos()
    new.Format = 2
    new.ValueFormat = min_inclusive_rec_format
    new.Coverage = ot.Coverage()
    new.Coverage.glyphs = glyphs
    new.ValueCount = num_glyphs
    new.Value = [None] * num_glyphs
    for singlePos in lst:
        if singlePos.Format == 1:
            val_rec = singlePos.Value
            for gname in singlePos.Coverage.glyphs:
                i = glyphs.index(gname)
                new.Value[i] = copy.deepcopy(val_rec)
        elif singlePos.Format == 2:
            for j, gname in enumerate(singlePos.Coverage.glyphs):
                val_rec = singlePos.Value[j]
                i = glyphs.index(gname)
                new.Value[i] = copy.deepcopy(val_rec)
    return [new]


@AligningMerger.merger(ot.CursivePos)
def merge(merger, self, lst):
    # Align them
    glyphs, padded = _merge_GlyphOrders(
        merger.font,
        [l.Coverage.glyphs for l in lst],
        [l.EntryExitRecord for l in lst],
    )

    self.Format = 1
    self.Coverage = ot.Coverage()
    self.Coverage.glyphs = glyphs
    self.EntryExitRecord = []
    for _ in glyphs:
        rec = ot.EntryExitRecord()
        rec.EntryAnchor = ot.Anchor()
        rec.EntryAnchor.Format = 1
        rec.ExitAnchor = ot.Anchor()
        rec.ExitAnchor.Format = 1
        self.EntryExitRecord.append(rec)
    merger.mergeLists(self.EntryExitRecord, padded)
    self.EntryExitCount = len(self.EntryExitRecord)


@AligningMerger.merger(ot.EntryExitRecord)
def merge(merger, self, lst):
    if all(master.EntryAnchor is None for master in lst):
        self.EntryAnchor = None
    if all(master.ExitAnchor is None for master in lst):
        self.ExitAnchor = None
    merger.mergeObjects(self, lst)


@AligningMerger.merger(ot.Lookup)
def merge(merger, self, lst):
    subtables = merger.lookup_subtables = [l.SubTable for l in lst]

    # Remove Extension subtables
    for l, sts in list(zip(lst, subtables)) + [(self, self.SubTable)]:
        if not sts:
            continue
        if sts[0].__class__.__name__.startswith("Extension"):
            if not allEqual([st.__class__ for st in sts]):
                raise InconsistentExtensions(
                    merger,
                    expected="Extension",
                    got=[st.__class__.__name__ for st in sts],
                )
            if not allEqual([st.ExtensionLookupType for st in sts]):
                raise InconsistentExtensions(merger)
            l.LookupType = sts[0].ExtensionLookupType
            new_sts = [st.ExtSubTable for st in sts]
            del sts[:]
            sts.extend(new_sts)

    isPairPos = self.SubTable and isinstance(self.SubTable[0], ot.PairPos)

    if isPairPos:
        # AFDKO and feaLib sometimes generate two Format1 subtables instead of one.
        # Merge those before continuing.
        # https://github.com/fonttools/fonttools/issues/719
        self.SubTable = _Lookup_PairPos_subtables_canonicalize(
            self.SubTable, merger.font
        )
        subtables = merger.lookup_subtables = [
            _Lookup_PairPos_subtables_canonicalize(st, merger.font) for st in subtables
        ]
    else:
        isSinglePos = self.SubTable and isinstance(self.SubTable[0], ot.SinglePos)
        if isSinglePos:
            numSubtables = [len(st) for st in subtables]
            if not all([nums == numSubtables[0] for nums in numSubtables]):
                # Flatten list of SinglePos subtables to single Format 2 subtable,
                # with all value records set to the rec format type.
                # We use buildSinglePos() to optimize the lookup after merging.
                valueFormatList = [t.ValueFormat for st in subtables for t in st]
                # Find the minimum value record that can accomodate all the singlePos subtables.
                mirf = reduce(ior, valueFormatList)
                self.SubTable = _Lookup_SinglePos_subtables_flatten(
                    self.SubTable, merger.font, mirf
                )
                subtables = merger.lookup_subtables = [
                    _Lookup_SinglePos_subtables_flatten(st, merger.font, mirf)
                    for st in subtables
                ]
                flattened = True
            else:
                flattened = False

    merger.mergeLists(self.SubTable, subtables)
    self.SubTableCount = len(self.SubTable)

    if isPairPos:
        # If format-1 subtable created during canonicalization is empty, remove it.
        assert len(self.SubTable) >= 1 and self.SubTable[0].Format == 1
        if not self.SubTable[0].Coverage.glyphs:
            self.SubTable.pop(0)
            self.SubTableCount -= 1

        # If format-2 subtable created during canonicalization is empty, remove it.
        assert len(self.SubTable) >= 1 and self.SubTable[-1].Format == 2
        if not self.SubTable[-1].Coverage.glyphs:
            self.SubTable.pop(-1)
            self.SubTableCount -= 1

        # Compact the merged subtables
        # This is a good moment to do it because the compaction should create
        # smaller subtables, which may prevent overflows from happening.
        # Keep reading the value from the ENV until ufo2ft switches to the config system
        level = merger.font.cfg.get(
            "fontTools.otlLib.optimize.gpos:COMPRESSION_LEVEL",
            default=_compression_level_from_env(),
        )
        if level != 0:
            log.info("Compacting GPOS...")
            self.SubTable = compact_pair_pos(merger.font, level, self.SubTable)
            self.SubTableCount = len(self.SubTable)

    elif isSinglePos and flattened:
        singlePosTable = self.SubTable[0]
        glyphs = singlePosTable.Coverage.glyphs
        # We know that singlePosTable is Format 2, as this is set
        # in _Lookup_SinglePos_subtables_flatten.
        singlePosMapping = {
            gname: valRecord for gname, valRecord in zip(glyphs, singlePosTable.Value)
        }
        self.SubTable = buildSinglePos(
            singlePosMapping, merger.font.getReverseGlyphMap()
        )
    merger.mergeObjects(self, lst, exclude=["SubTable", "SubTableCount"])

    del merger.lookup_subtables


#
# InstancerMerger
#


class InstancerMerger(AligningMerger):
    """A merger that takes multiple master fonts, and instantiates
    an instance."""

    def __init__(self, font, model, location):
        Merger.__init__(self, font)
        self.model = model
        self.location = location
        self.masterScalars = model.getMasterScalars(location)


@InstancerMerger.merger(ot.CaretValue)
def merge(merger, self, lst):
    assert self.Format == 1
    Coords = [a.Coordinate for a in lst]
    model = merger.model
    masterScalars = merger.masterScalars
    self.Coordinate = otRound(
        model.interpolateFromValuesAndScalars(Coords, masterScalars)
    )


@InstancerMerger.merger(ot.Anchor)
def merge(merger, self, lst):
    assert self.Format == 1
    XCoords = [a.XCoordinate for a in lst]
    YCoords = [a.YCoordinate for a in lst]
    model = merger.model
    masterScalars = merger.masterScalars
    self.XCoordinate = otRound(
        model.interpolateFromValuesAndScalars(XCoords, masterScalars)
    )
    self.YCoordinate = otRound(
        model.interpolateFromValuesAndScalars(YCoords, masterScalars)
    )


@InstancerMerger.merger(otBase.ValueRecord)
def merge(merger, self, lst):
    model = merger.model
    masterScalars = merger.masterScalars
    # TODO Handle differing valueformats
    for name, tableName in [
        ("XAdvance", "XAdvDevice"),
        ("YAdvance", "YAdvDevice"),
        ("XPlacement", "XPlaDevice"),
        ("YPlacement", "YPlaDevice"),
    ]:
        assert not hasattr(self, tableName)

        if hasattr(self, name):
            values = [getattr(a, name, 0) for a in lst]
            value = otRound(
                model.interpolateFromValuesAndScalars(values, masterScalars)
            )
            setattr(self, name, value)


#
# MutatorMerger
#


class MutatorMerger(AligningMerger):
    """A merger that takes a variable font, and instantiates
    an instance.  While there's no "merging" to be done per se,
    the operation can benefit from many operations that the
    aligning merger does."""

    def __init__(self, font, instancer, deleteVariations=True):
        Merger.__init__(self, font)
        self.instancer = instancer
        self.deleteVariations = deleteVariations


@MutatorMerger.merger(ot.CaretValue)
def merge(merger, self, lst):
    # Hack till we become selfless.
    self.__dict__ = lst[0].__dict__.copy()

    if self.Format != 3:
        return

    instancer = merger.instancer
    dev = self.DeviceTable
    if merger.deleteVariations:
        del self.DeviceTable
    if dev:
        assert dev.DeltaFormat == 0x8000
        varidx = (dev.StartSize << 16) + dev.EndSize
        delta = otRound(instancer[varidx])
        self.Coordinate += delta

    if merger.deleteVariations:
        self.Format = 1


@MutatorMerger.merger(ot.Anchor)
def merge(merger, self, lst):
    # Hack till we become selfless.
    self.__dict__ = lst[0].__dict__.copy()

    if self.Format != 3:
        return

    instancer = merger.instancer
    for v in "XY":
        tableName = v + "DeviceTable"
        if not hasattr(self, tableName):
            continue
        dev = getattr(self, tableName)
        if merger.deleteVariations:
            delattr(self, tableName)
        if dev is None:
            continue

        assert dev.DeltaFormat == 0x8000
        varidx = (dev.StartSize << 16) + dev.EndSize
        delta = otRound(instancer[varidx])

        attr = v + "Coordinate"
        setattr(self, attr, getattr(self, attr) + delta)

    if merger.deleteVariations:
        self.Format = 1


@MutatorMerger.merger(otBase.ValueRecord)
def merge(merger, self, lst):
    # Hack till we become selfless.
    self.__dict__ = lst[0].__dict__.copy()

    instancer = merger.instancer
    for name, tableName in [
        ("XAdvance", "XAdvDevice"),
        ("YAdvance", "YAdvDevice"),
        ("XPlacement", "XPlaDevice"),
        ("YPlacement", "YPlaDevice"),
    ]:
        if not hasattr(self, tableName):
            continue
        dev = getattr(self, tableName)
        if merger.deleteVariations:
            delattr(self, tableName)
        if dev is None:
            continue

        assert dev.DeltaFormat == 0x8000
        varidx = (dev.StartSize << 16) + dev.EndSize
        delta = otRound(instancer[varidx])

        setattr(self, name, getattr(self, name, 0) + delta)


#
# VariationMerger
#


class VariationMerger(AligningMerger):
    """A merger that takes multiple master fonts, and builds a
    variable font."""

    def __init__(self, model, axisTags, font):
        Merger.__init__(self, font)
        self.store_builder = varStore.OnlineVarStoreBuilder(axisTags)
        self.setModel(model)

    def setModel(self, model):
        self.model = model
        self.store_builder.setModel(model)

    def mergeThings(self, out, lst):
        masterModel = None
        origTTFs = None
        if None in lst:
            if allNone(lst):
                if out is not None:
                    raise FoundANone(self, got=lst)
                return

            # temporarily subset the list of master ttfs to the ones for which
            # master values are not None
            origTTFs = self.ttfs
            if self.ttfs:
                self.ttfs = subList([v is not None for v in lst], self.ttfs)

            masterModel = self.model
            model, lst = masterModel.getSubModel(lst)
            self.setModel(model)

        super(VariationMerger, self).mergeThings(out, lst)

        if masterModel:
            self.setModel(masterModel)
        if origTTFs:
            self.ttfs = origTTFs


def buildVarDevTable(store_builder, master_values):
    if allEqual(master_values):
        return master_values[0], None
    base, varIdx = store_builder.storeMasters(master_values)
    return base, builder.buildVarDevTable(varIdx)


@VariationMerger.merger(ot.BaseCoord)
def merge(merger, self, lst):
    if self.Format != 1:
        raise UnsupportedFormat(merger, subtable="a baseline coordinate")
    self.Coordinate, DeviceTable = buildVarDevTable(
        merger.store_builder, [a.Coordinate for a in lst]
    )
    if DeviceTable:
        self.Format = 3
        self.DeviceTable = DeviceTable


@VariationMerger.merger(ot.CaretValue)
def merge(merger, self, lst):
    if self.Format != 1:
        raise UnsupportedFormat(merger, subtable="a caret")
    self.Coordinate, DeviceTable = buildVarDevTable(
        merger.store_builder, [a.Coordinate for a in lst]
    )
    if DeviceTable:
        self.Format = 3
        self.DeviceTable = DeviceTable


@VariationMerger.merger(ot.Anchor)
def merge(merger, self, lst):
    if self.Format != 1:
        raise UnsupportedFormat(merger, subtable="an anchor")
    self.XCoordinate, XDeviceTable = buildVarDevTable(
        merger.store_builder, [a.XCoordinate for a in lst]
    )
    self.YCoordinate, YDeviceTable = buildVarDevTable(
        merger.store_builder, [a.YCoordinate for a in lst]
    )
    if XDeviceTable or YDeviceTable:
        self.Format = 3
        self.XDeviceTable = XDeviceTable
        self.YDeviceTable = YDeviceTable


@VariationMerger.merger(otBase.ValueRecord)
def merge(merger, self, lst):
    for name, tableName in [
        ("XAdvance", "XAdvDevice"),
        ("YAdvance", "YAdvDevice"),
        ("XPlacement", "XPlaDevice"),
        ("YPlacement", "YPlaDevice"),
    ]:
        if hasattr(self, name):
            value, deviceTable = buildVarDevTable(
                merger.store_builder, [getattr(a, name, 0) for a in lst]
            )
            setattr(self, name, value)
            if deviceTable:
                setattr(self, tableName, deviceTable)


class COLRVariationMerger(VariationMerger):
    """A specialized VariationMerger that takes multiple master fonts containing
    COLRv1 tables, and builds a variable COLR font.

    COLR tables are special in that variable subtables can be associated with
    multiple delta-set indices (via VarIndexBase).
    They also contain tables that must change their type (not simply the Format)
    as they become variable (e.g. Affine2x3 -> VarAffine2x3) so this merger takes
    care of that too.
    """

    def __init__(self, model, axisTags, font, allowLayerReuse=True):
        VariationMerger.__init__(self, model, axisTags, font)
        # maps {tuple(varIdxes): VarIndexBase} to facilitate reuse of VarIndexBase
        # between variable tables with same varIdxes.
        self.varIndexCache = {}
        # flat list of all the varIdxes generated while merging
        self.varIdxes = []
        # set of id()s of the subtables that contain variations after merging
        # and need to be upgraded to the associated VarType.
        self.varTableIds = set()
        # we keep these around for rebuilding a LayerList while merging PaintColrLayers
        self.layers = []
        self.layerReuseCache = None
        if allowLayerReuse:
            self.layerReuseCache = LayerReuseCache()
        # flag to ensure BaseGlyphList is fully merged before LayerList gets processed
        self._doneBaseGlyphs = False

    def mergeTables(self, font, master_ttfs, tableTags=("COLR",)):
        if "COLR" in tableTags and "COLR" in font:
            # The merger modifies the destination COLR table in-place. If this contains
            # multiple PaintColrLayers referencing the same layers from LayerList, it's
            # a problem because we may risk modifying the same paint more than once, or
            # worse, fail while attempting to do that.
            # We don't know whether the master COLR table was built with layer reuse
            # disabled, thus to be safe we rebuild its LayerList so that it contains only
            # unique layers referenced from non-overlapping PaintColrLayers throughout
            # the base paint graphs.
            self.expandPaintColrLayers(font["COLR"].table)
        VariationMerger.mergeTables(self, font, master_ttfs, tableTags)

    def checkFormatEnum(self, out, lst, validate=lambda _: True):
        fmt = out.Format
        formatEnum = out.formatEnum
        ok = False
        try:
            fmt = formatEnum(fmt)
        except ValueError:
            pass
        else:
            ok = validate(fmt)
        if not ok:
            raise UnsupportedFormat(self, subtable=type(out).__name__, value=fmt)
        expected = fmt
        got = []
        for v in lst:
            fmt = getattr(v, "Format", None)
            try:
                fmt = formatEnum(fmt)
            except ValueError:
                pass
            got.append(fmt)
        if not allEqualTo(expected, got):
            raise InconsistentFormats(
                self,
                subtable=type(out).__name__,
                expected=expected,
                got=got,
            )
        return expected

    def mergeSparseDict(self, out, lst):
        for k in out.keys():
            try:
                self.mergeThings(out[k], [v.get(k) for v in lst])
            except VarLibMergeError as e:
                e.stack.append(f"[{k!r}]")
                raise

    def mergeAttrs(self, out, lst, attrs):
        for attr in attrs:
            value = getattr(out, attr)
            values = [getattr(item, attr) for item in lst]
            try:
                self.mergeThings(value, values)
            except VarLibMergeError as e:
                e.stack.append(f".{attr}")
                raise

    def storeMastersForAttr(self, out, lst, attr):
        master_values = [getattr(item, attr) for item in lst]

        # VarStore treats deltas for fixed-size floats as integers, so we
        # must convert master values to int before storing them in the builder
        # then back to float.
        is_fixed_size_float = False
        conv = out.getConverterByName(attr)
        if isinstance(conv, BaseFixedValue):
            is_fixed_size_float = True
            master_values = [conv.toInt(v) for v in master_values]

        baseValue = master_values[0]
        varIdx = ot.NO_VARIATION_INDEX
        if not allEqual(master_values):
            baseValue, varIdx = self.store_builder.storeMasters(master_values)

        if is_fixed_size_float:
            baseValue = conv.fromInt(baseValue)

        return baseValue, varIdx

    def storeVariationIndices(self, varIdxes) -> int:
        # try to reuse an existing VarIndexBase for the same varIdxes, or else
        # create a new one
        key = tuple(varIdxes)
        varIndexBase = self.varIndexCache.get(key)

        if varIndexBase is None:
            # scan for a full match anywhere in the self.varIdxes
            for i in range(len(self.varIdxes) - len(varIdxes) + 1):
                if self.varIdxes[i : i + len(varIdxes)] == varIdxes:
                    self.varIndexCache[key] = varIndexBase = i
                    break

        if varIndexBase is None:
            # try find a partial match at the end of the self.varIdxes
            for n in range(len(varIdxes) - 1, 0, -1):
                if self.varIdxes[-n:] == varIdxes[:n]:
                    varIndexBase = len(self.varIdxes) - n
                    self.varIndexCache[key] = varIndexBase
                    self.varIdxes.extend(varIdxes[n:])
                    break

        if varIndexBase is None:
            # no match found, append at the end
            self.varIndexCache[key] = varIndexBase = len(self.varIdxes)
            self.varIdxes.extend(varIdxes)

        return varIndexBase

    def mergeVariableAttrs(self, out, lst, attrs) -> int:
        varIndexBase = ot.NO_VARIATION_INDEX
        varIdxes = []
        for attr in attrs:
            baseValue, varIdx = self.storeMastersForAttr(out, lst, attr)
            setattr(out, attr, baseValue)
            varIdxes.append(varIdx)

        if any(v != ot.NO_VARIATION_INDEX for v in varIdxes):
            varIndexBase = self.storeVariationIndices(varIdxes)

        return varIndexBase

    @classmethod
    def convertSubTablesToVarType(cls, table):
        for path in dfs_base_table(
            table,
            skip_root=True,
            predicate=lambda path: (
                getattr(type(path[-1].value), "VarType", None) is not None
            ),
        ):
            st = path[-1]
            subTable = st.value
            varType = type(subTable).VarType
            newSubTable = varType()
            newSubTable.__dict__.update(subTable.__dict__)
            newSubTable.populateDefaults()
            parent = path[-2].value
            if st.index is not None:
                getattr(parent, st.name)[st.index] = newSubTable
            else:
                setattr(parent, st.name, newSubTable)

    @staticmethod
    def expandPaintColrLayers(colr):
        """Rebuild LayerList without PaintColrLayers reuse.

        Each base paint graph is fully DFS-traversed (with exception of PaintColrGlyph
        which are irrelevant for this); any layers referenced via PaintColrLayers are
        collected into a new LayerList and duplicated when reuse is detected, to ensure
        that all paints are distinct objects at the end of the process.
        PaintColrLayers's FirstLayerIndex/NumLayers are updated so that no overlap
        is left. Also, any consecutively nested PaintColrLayers are flattened.
        The COLR table's LayerList is replaced with the new unique layers.
        A side effect is also that any layer from the old LayerList which is not
        referenced by any PaintColrLayers is dropped.
        """
        if not colr.LayerList:
            # if no LayerList, there's nothing to expand
            return
        uniqueLayerIDs = set()
        newLayerList = []
        for rec in colr.BaseGlyphList.BaseGlyphPaintRecord:
            frontier = [rec.Paint]
            while frontier:
                paint = frontier.pop()
                if paint.Format == ot.PaintFormat.PaintColrGlyph:
                    # don't traverse these, we treat them as constant for merging
                    continue
                elif paint.Format == ot.PaintFormat.PaintColrLayers:
                    # de-treeify any nested PaintColrLayers, append unique copies to
                    # the new layer list and update PaintColrLayers index/count
                    children = list(_flatten_layers(paint, colr))
                    first_layer_index = len(newLayerList)
                    for layer in children:
                        if id(layer) in uniqueLayerIDs:
                            layer = copy.deepcopy(layer)
                            assert id(layer) not in uniqueLayerIDs
                        newLayerList.append(layer)
                        uniqueLayerIDs.add(id(layer))
                    paint.FirstLayerIndex = first_layer_index
                    paint.NumLayers = len(children)
                else:
                    children = paint.getChildren(colr)
                frontier.extend(reversed(children))
        # sanity check all the new layers are distinct objects
        assert len(newLayerList) == len(uniqueLayerIDs)
        colr.LayerList.Paint = newLayerList
        colr.LayerList.LayerCount = len(newLayerList)


@COLRVariationMerger.merger(ot.BaseGlyphList)
def merge(merger, self, lst):
    # ignore BaseGlyphCount, allow sparse glyph sets across masters
    out = {rec.BaseGlyph: rec for rec in self.BaseGlyphPaintRecord}
    masters = [{rec.BaseGlyph: rec for rec in m.BaseGlyphPaintRecord} for m in lst]

    for i, g in enumerate(out.keys()):
        try:
            # missing base glyphs don't participate in the merge
            merger.mergeThings(out[g], [v.get(g) for v in masters])
        except VarLibMergeError as e:
            e.stack.append(f".BaseGlyphPaintRecord[{i}]")
            e.cause["location"] = f"base glyph {g!r}"
            raise

    merger._doneBaseGlyphs = True


@COLRVariationMerger.merger(ot.LayerList)
def merge(merger, self, lst):
    # nothing to merge for LayerList, assuming we have already merged all PaintColrLayers
    # found while traversing the paint graphs rooted at BaseGlyphPaintRecords.
    assert merger._doneBaseGlyphs, "BaseGlyphList must be merged before LayerList"
    # Simply flush the final list of layers and go home.
    self.LayerCount = len(merger.layers)
    self.Paint = merger.layers


def _flatten_layers(root, colr):
    assert root.Format == ot.PaintFormat.PaintColrLayers
    for paint in root.getChildren(colr):
        if paint.Format == ot.PaintFormat.PaintColrLayers:
            yield from _flatten_layers(paint, colr)
        else:
            yield paint


def _merge_PaintColrLayers(self, out, lst):
    # we only enforce that the (flat) number of layers is the same across all masters
    # but we allow FirstLayerIndex to differ to acommodate for sparse glyph sets.

    out_layers = list(_flatten_layers(out, self.font["COLR"].table))

    # sanity check ttfs are subset to current values (see VariationMerger.mergeThings)
    # before matching each master PaintColrLayers to its respective COLR by position
    assert len(self.ttfs) == len(lst)
    master_layerses = [
        list(_flatten_layers(lst[i], self.ttfs[i]["COLR"].table))
        for i in range(len(lst))
    ]

    try:
        self.mergeLists(out_layers, master_layerses)
    except VarLibMergeError as e:
        # NOTE: This attribute doesn't actually exist in PaintColrLayers but it's
        # handy to have it in the stack trace for debugging.
        e.stack.append(".Layers")
        raise

    # following block is very similar to LayerListBuilder._beforeBuildPaintColrLayers
    # but I couldn't find a nice way to share the code between the two...

    if self.layerReuseCache is not None:
        # successful reuse can make the list smaller
        out_layers = self.layerReuseCache.try_reuse(out_layers)

    # if the list is still too big we need to tree-fy it
    is_tree = len(out_layers) > MAX_PAINT_COLR_LAYER_COUNT
    out_layers = build_n_ary_tree(out_layers, n=MAX_PAINT_COLR_LAYER_COUNT)

    # We now have a tree of sequences with Paint leaves.
    # Convert the sequences into PaintColrLayers.
    def listToColrLayers(paint):
        if isinstance(paint, list):
            layers = [listToColrLayers(l) for l in paint]
            paint = ot.Paint()
            paint.Format = int(ot.PaintFormat.PaintColrLayers)
            paint.NumLayers = len(layers)
            paint.FirstLayerIndex = len(self.layers)
            self.layers.extend(layers)
            if self.layerReuseCache is not None:
                self.layerReuseCache.add(layers, paint.FirstLayerIndex)
        return paint

    out_layers = [listToColrLayers(l) for l in out_layers]

    if len(out_layers) == 1 and out_layers[0].Format == ot.PaintFormat.PaintColrLayers:
        # special case when the reuse cache finds a single perfect PaintColrLayers match
        # (it can only come from a successful reuse, _flatten_layers has gotten rid of
        # all nested PaintColrLayers already); we assign it directly and avoid creating
        # an extra table
        out.NumLayers = out_layers[0].NumLayers
        out.FirstLayerIndex = out_layers[0].FirstLayerIndex
    else:
        out.NumLayers = len(out_layers)
        out.FirstLayerIndex = len(self.layers)

        self.layers.extend(out_layers)

        # Register our parts for reuse provided we aren't a tree
        # If we are a tree the leaves registered for reuse and that will suffice
        if self.layerReuseCache is not None and not is_tree:
            self.layerReuseCache.add(out_layers, out.FirstLayerIndex)


@COLRVariationMerger.merger((ot.Paint, ot.ClipBox))
def merge(merger, self, lst):
    fmt = merger.checkFormatEnum(self, lst, lambda fmt: not fmt.is_variable())

    if fmt is ot.PaintFormat.PaintColrLayers:
        _merge_PaintColrLayers(merger, self, lst)
        return

    varFormat = fmt.as_variable()

    varAttrs = ()
    if varFormat is not None:
        varAttrs = otBase.getVariableAttrs(type(self), varFormat)
    staticAttrs = (c.name for c in self.getConverters() if c.name not in varAttrs)

    merger.mergeAttrs(self, lst, staticAttrs)

    varIndexBase = merger.mergeVariableAttrs(self, lst, varAttrs)

    subTables = [st.value for st in self.iterSubTables()]

    # Convert table to variable if itself has variations or any subtables have
    isVariable = varIndexBase != ot.NO_VARIATION_INDEX or any(
        id(table) in merger.varTableIds for table in subTables
    )

    if isVariable:
        if varAttrs:
            # Some PaintVar* don't have any scalar attributes that can vary,
            # only indirect offsets to other variable subtables, thus have
            # no VarIndexBase of their own (e.g. PaintVarTransform)
            self.VarIndexBase = varIndexBase

        if subTables:
            # Convert Affine2x3 -> VarAffine2x3, ColorLine -> VarColorLine, etc.
            merger.convertSubTablesToVarType(self)

        assert varFormat is not None
        self.Format = int(varFormat)


@COLRVariationMerger.merger((ot.Affine2x3, ot.ColorStop))
def merge(merger, self, lst):
    varType = type(self).VarType

    varAttrs = otBase.getVariableAttrs(varType)
    staticAttrs = (c.name for c in self.getConverters() if c.name not in varAttrs)

    merger.mergeAttrs(self, lst, staticAttrs)

    varIndexBase = merger.mergeVariableAttrs(self, lst, varAttrs)

    if varIndexBase != ot.NO_VARIATION_INDEX:
        self.VarIndexBase = varIndexBase
        # mark as having variations so the parent table will convert to Var{Type}
        merger.varTableIds.add(id(self))


@COLRVariationMerger.merger(ot.ColorLine)
def merge(merger, self, lst):
    merger.mergeAttrs(self, lst, (c.name for c in self.getConverters()))

    if any(id(stop) in merger.varTableIds for stop in self.ColorStop):
        merger.convertSubTablesToVarType(self)
        merger.varTableIds.add(id(self))


@COLRVariationMerger.merger(ot.ClipList, "clips")
def merge(merger, self, lst):
    # 'sparse' in that we allow non-default masters to omit ClipBox entries
    # for some/all glyphs (i.e. they don't participate)
    merger.mergeSparseDict(self, lst)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\progress.py ===
import io
import sys
import typing
import warnings
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import timedelta
from io import RawIOBase, UnsupportedOperation
from math import ceil
from mmap import mmap
from operator import length_hint
from os import PathLike, stat
from threading import Event, RLock, Thread
from types import TracebackType
from typing import (
    Any,
    BinaryIO,
    Callable,
    ContextManager,
    Deque,
    Dict,
    Generic,
    Iterable,
    List,
    NamedTuple,
    NewType,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from pip._vendor.typing_extensions import Literal  # pragma: no cover

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from pip._vendor.typing_extensions import Self  # pragma: no cover

from . import filesize, get_console
from .console import Console, Group, JustifyMethod, RenderableType
from .highlighter import Highlighter
from .jupyter import JupyterMixin
from .live import Live
from .progress_bar import ProgressBar
from .spinner import Spinner
from .style import StyleType
from .table import Column, Table
from .text import Text, TextType

TaskID = NewType("TaskID", int)

ProgressType = TypeVar("ProgressType")

GetTimeCallable = Callable[[], float]


_I = typing.TypeVar("_I", TextIO, BinaryIO)


class _TrackThread(Thread):
    """A thread to periodically update progress."""

    def __init__(self, progress: "Progress", task_id: "TaskID", update_period: float):
        self.progress = progress
        self.task_id = task_id
        self.update_period = update_period
        self.done = Event()

        self.completed = 0
        super().__init__(daemon=True)

    def run(self) -> None:
        task_id = self.task_id
        advance = self.progress.advance
        update_period = self.update_period
        last_completed = 0
        wait = self.done.wait
        while not wait(update_period) and self.progress.live.is_started:
            completed = self.completed
            if last_completed != completed:
                advance(task_id, completed - last_completed)
                last_completed = completed

        self.progress.update(self.task_id, completed=self.completed, refresh=True)

    def __enter__(self) -> "_TrackThread":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.done.set()
        self.join()


def track(
    sequence: Union[Sequence[ProgressType], Iterable[ProgressType]],
    description: str = "Working...",
    total: Optional[float] = None,
    completed: int = 0,
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    update_period: float = 0.1,
    disable: bool = False,
    show_speed: bool = True,
) -> Iterable[ProgressType]:
    """Track progress by iterating over a sequence.

    Args:
        sequence (Iterable[ProgressType]): A sequence (must support "len") you wish to iterate over.
        description (str, optional): Description of task show next to progress bar. Defaults to "Working".
        total: (float, optional): Total number of steps. Default is len(sequence).
        completed (int, optional): Number of steps completed so far. Defaults to 0.
        auto_refresh (bool, optional): Automatic refresh, disable to force a refresh after each iteration. Default is True.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        console (Console, optional): Console to write to. Default creates internal Console instance.
        refresh_per_second (float): Number of times per second to refresh the progress information. Defaults to 10.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        update_period (float, optional): Minimum time (in seconds) between calls to update(). Defaults to 0.1.
        disable (bool, optional): Disable display of progress.
        show_speed (bool, optional): Show speed if total isn't known. Defaults to True.
    Returns:
        Iterable[ProgressType]: An iterable of the values in the sequence.

    """

    columns: List["ProgressColumn"] = (
        [TextColumn("[progress.description]{task.description}")] if description else []
    )
    columns.extend(
        (
            BarColumn(
                style=style,
                complete_style=complete_style,
                finished_style=finished_style,
                pulse_style=pulse_style,
            ),
            TaskProgressColumn(show_speed=show_speed),
            TimeRemainingColumn(elapsed_when_finished=True),
        )
    )
    progress = Progress(
        *columns,
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

    with progress:
        yield from progress.track(
            sequence,
            total=total,
            completed=completed,
            description=description,
            update_period=update_period,
        )


class _Reader(RawIOBase, BinaryIO):
    """A reader that tracks progress while it's being read from."""

    def __init__(
        self,
        handle: BinaryIO,
        progress: "Progress",
        task: TaskID,
        close_handle: bool = True,
    ) -> None:
        self.handle = handle
        self.progress = progress
        self.task = task
        self.close_handle = close_handle
        self._closed = False

    def __enter__(self) -> "_Reader":
        self.handle.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def __iter__(self) -> BinaryIO:
        return self

    def __next__(self) -> bytes:
        line = next(self.handle)
        self.progress.advance(self.task, advance=len(line))
        return line

    @property
    def closed(self) -> bool:
        return self._closed

    def fileno(self) -> int:
        return self.handle.fileno()

    def isatty(self) -> bool:
        return self.handle.isatty()

    @property
    def mode(self) -> str:
        return self.handle.mode

    @property
    def name(self) -> str:
        return self.handle.name

    def readable(self) -> bool:
        return self.handle.readable()

    def seekable(self) -> bool:
        return self.handle.seekable()

    def writable(self) -> bool:
        return False

    def read(self, size: int = -1) -> bytes:
        block = self.handle.read(size)
        self.progress.advance(self.task, advance=len(block))
        return block

    def readinto(self, b: Union[bytearray, memoryview, mmap]):  # type: ignore[no-untyped-def, override]
        n = self.handle.readinto(b)  # type: ignore[attr-defined]
        self.progress.advance(self.task, advance=n)
        return n

    def readline(self, size: int = -1) -> bytes:  # type: ignore[override]
        line = self.handle.readline(size)
        self.progress.advance(self.task, advance=len(line))
        return line

    def readlines(self, hint: int = -1) -> List[bytes]:
        lines = self.handle.readlines(hint)
        self.progress.advance(self.task, advance=sum(map(len, lines)))
        return lines

    def close(self) -> None:
        if self.close_handle:
            self.handle.close()
        self._closed = True

    def seek(self, offset: int, whence: int = 0) -> int:
        pos = self.handle.seek(offset, whence)
        self.progress.update(self.task, completed=pos)
        return pos

    def tell(self) -> int:
        return self.handle.tell()

    def write(self, s: Any) -> int:
        raise UnsupportedOperation("write")

    def writelines(self, lines: Iterable[Any]) -> None:
        raise UnsupportedOperation("writelines")


class _ReadContext(ContextManager[_I], Generic[_I]):
    """A utility class to handle a context for both a reader and a progress."""

    def __init__(self, progress: "Progress", reader: _I) -> None:
        self.progress = progress
        self.reader: _I = reader

    def __enter__(self) -> _I:
        self.progress.start()
        return self.reader.__enter__()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.progress.stop()
        self.reader.__exit__(exc_type, exc_val, exc_tb)


def wrap_file(
    file: BinaryIO,
    total: int,
    *,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> ContextManager[BinaryIO]:
    """Read bytes from a file while tracking progress.

    Args:
        file (Union[str, PathLike[str], BinaryIO]): The path to the file to read, or a file-like object in binary mode.
        total (int): Total number of bytes to read.
        description (str, optional): Description of task show next to progress bar. Defaults to "Reading".
        auto_refresh (bool, optional): Automatic refresh, disable to force a refresh after each iteration. Default is True.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        console (Console, optional): Console to write to. Default creates internal Console instance.
        refresh_per_second (float): Number of times per second to refresh the progress information. Defaults to 10.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        disable (bool, optional): Disable display of progress.
    Returns:
        ContextManager[BinaryIO]: A context manager yielding a progress reader.

    """

    columns: List["ProgressColumn"] = (
        [TextColumn("[progress.description]{task.description}")] if description else []
    )
    columns.extend(
        (
            BarColumn(
                style=style,
                complete_style=complete_style,
                finished_style=finished_style,
                pulse_style=pulse_style,
            ),
            DownloadColumn(),
            TimeRemainingColumn(),
        )
    )
    progress = Progress(
        *columns,
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

    reader = progress.wrap_file(file, total=total, description=description)
    return _ReadContext(progress, reader)


@typing.overload
def open(
    file: Union[str, "PathLike[str]", bytes],
    mode: Union[Literal["rt"], Literal["r"]],
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    *,
    total: Optional[int] = None,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> ContextManager[TextIO]:
    pass


@typing.overload
def open(
    file: Union[str, "PathLike[str]", bytes],
    mode: Literal["rb"],
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    *,
    total: Optional[int] = None,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> ContextManager[BinaryIO]:
    pass


def open(
    file: Union[str, "PathLike[str]", bytes],
    mode: Union[Literal["rb"], Literal["rt"], Literal["r"]] = "r",
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    *,
    total: Optional[int] = None,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> Union[ContextManager[BinaryIO], ContextManager[TextIO]]:
    """Read bytes from a file while tracking progress.

    Args:
        path (Union[str, PathLike[str], BinaryIO]): The path to the file to read, or a file-like object in binary mode.
        mode (str): The mode to use to open the file. Only supports "r", "rb" or "rt".
        buffering (int): The buffering strategy to use, see :func:`io.open`.
        encoding (str, optional): The encoding to use when reading in text mode, see :func:`io.open`.
        errors (str, optional): The error handling strategy for decoding errors, see :func:`io.open`.
        newline (str, optional): The strategy for handling newlines in text mode, see :func:`io.open`
        total: (int, optional): Total number of bytes to read. Must be provided if reading from a file handle. Default for a path is os.stat(file).st_size.
        description (str, optional): Description of task show next to progress bar. Defaults to "Reading".
        auto_refresh (bool, optional): Automatic refresh, disable to force a refresh after each iteration. Default is True.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        console (Console, optional): Console to write to. Default creates internal Console instance.
        refresh_per_second (float): Number of times per second to refresh the progress information. Defaults to 10.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        disable (bool, optional): Disable display of progress.
        encoding (str, optional): The encoding to use when reading in text mode.

    Returns:
        ContextManager[BinaryIO]: A context manager yielding a progress reader.

    """

    columns: List["ProgressColumn"] = (
        [TextColumn("[progress.description]{task.description}")] if description else []
    )
    columns.extend(
        (
            BarColumn(
                style=style,
                complete_style=complete_style,
                finished_style=finished_style,
                pulse_style=pulse_style,
            ),
            DownloadColumn(),
            TimeRemainingColumn(),
        )
    )
    progress = Progress(
        *columns,
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

    reader = progress.open(
        file,
        mode=mode,
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        newline=newline,
        total=total,
        description=description,
    )
    return _ReadContext(progress, reader)  # type: ignore[return-value, type-var]


class ProgressColumn(ABC):
    """Base class for a widget to use in progress display."""

    max_refresh: Optional[float] = None

    def __init__(self, table_column: Optional[Column] = None) -> None:
        self._table_column = table_column
        self._renderable_cache: Dict[TaskID, Tuple[float, RenderableType]] = {}
        self._update_time: Optional[float] = None

    def get_table_column(self) -> Column:
        """Get a table column, used to build tasks table."""
        return self._table_column or Column()

    def __call__(self, task: "Task") -> RenderableType:
        """Called by the Progress object to return a renderable for the given task.

        Args:
            task (Task): An object containing information regarding the task.

        Returns:
            RenderableType: Anything renderable (including str).
        """
        current_time = task.get_time()
        if self.max_refresh is not None and not task.completed:
            try:
                timestamp, renderable = self._renderable_cache[task.id]
            except KeyError:
                pass
            else:
                if timestamp + self.max_refresh > current_time:
                    return renderable

        renderable = self.render(task)
        self._renderable_cache[task.id] = (current_time, renderable)
        return renderable

    @abstractmethod
    def render(self, task: "Task") -> RenderableType:
        """Should return a renderable object."""


class RenderableColumn(ProgressColumn):
    """A column to insert an arbitrary column.

    Args:
        renderable (RenderableType, optional): Any renderable. Defaults to empty string.
    """

    def __init__(
        self, renderable: RenderableType = "", *, table_column: Optional[Column] = None
    ):
        self.renderable = renderable
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> RenderableType:
        return self.renderable


class SpinnerColumn(ProgressColumn):
    """A column with a 'spinner' animation.

    Args:
        spinner_name (str, optional): Name of spinner animation. Defaults to "dots".
        style (StyleType, optional): Style of spinner. Defaults to "progress.spinner".
        speed (float, optional): Speed factor of spinner. Defaults to 1.0.
        finished_text (TextType, optional): Text used when task is finished. Defaults to " ".
    """

    def __init__(
        self,
        spinner_name: str = "dots",
        style: Optional[StyleType] = "progress.spinner",
        speed: float = 1.0,
        finished_text: TextType = " ",
        table_column: Optional[Column] = None,
    ):
        self.spinner = Spinner(spinner_name, style=style, speed=speed)
        self.finished_text = (
            Text.from_markup(finished_text)
            if isinstance(finished_text, str)
            else finished_text
        )
        super().__init__(table_column=table_column)

    def set_spinner(
        self,
        spinner_name: str,
        spinner_style: Optional[StyleType] = "progress.spinner",
        speed: float = 1.0,
    ) -> None:
        """Set a new spinner.

        Args:
            spinner_name (str): Spinner name, see python -m rich.spinner.
            spinner_style (Optional[StyleType], optional): Spinner style. Defaults to "progress.spinner".
            speed (float, optional): Speed factor of spinner. Defaults to 1.0.
        """
        self.spinner = Spinner(spinner_name, style=spinner_style, speed=speed)

    def render(self, task: "Task") -> RenderableType:
        text = (
            self.finished_text
            if task.finished
            else self.spinner.render(task.get_time())
        )
        return text


class TextColumn(ProgressColumn):
    """A column containing text."""

    def __init__(
        self,
        text_format: str,
        style: StyleType = "none",
        justify: JustifyMethod = "left",
        markup: bool = True,
        highlighter: Optional[Highlighter] = None,
        table_column: Optional[Column] = None,
    ) -> None:
        self.text_format = text_format
        self.justify: JustifyMethod = justify
        self.style = style
        self.markup = markup
        self.highlighter = highlighter
        super().__init__(table_column=table_column or Column(no_wrap=True))

    def render(self, task: "Task") -> Text:
        _text = self.text_format.format(task=task)
        if self.markup:
            text = Text.from_markup(_text, style=self.style, justify=self.justify)
        else:
            text = Text(_text, style=self.style, justify=self.justify)
        if self.highlighter:
            self.highlighter.highlight(text)
        return text


class BarColumn(ProgressColumn):
    """Renders a visual progress bar.

    Args:
        bar_width (Optional[int], optional): Width of bar or None for full width. Defaults to 40.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
    """

    def __init__(
        self,
        bar_width: Optional[int] = 40,
        style: StyleType = "bar.back",
        complete_style: StyleType = "bar.complete",
        finished_style: StyleType = "bar.finished",
        pulse_style: StyleType = "bar.pulse",
        table_column: Optional[Column] = None,
    ) -> None:
        self.bar_width = bar_width
        self.style = style
        self.complete_style = complete_style
        self.finished_style = finished_style
        self.pulse_style = pulse_style
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> ProgressBar:
        """Gets a progress bar widget for a task."""
        return ProgressBar(
            total=max(0, task.total) if task.total is not None else None,
            completed=max(0, task.completed),
            width=None if self.bar_width is None else max(1, self.bar_width),
            pulse=not task.started,
            animation_time=task.get_time(),
            style=self.style,
            complete_style=self.complete_style,
            finished_style=self.finished_style,
            pulse_style=self.pulse_style,
        )


class TimeElapsedColumn(ProgressColumn):
    """Renders time elapsed."""

    def render(self, task: "Task") -> Text:
        """Show time elapsed."""
        elapsed = task.finished_time if task.finished else task.elapsed
        if elapsed is None:
            return Text("-:--:--", style="progress.elapsed")
        delta = timedelta(seconds=max(0, int(elapsed)))
        return Text(str(delta), style="progress.elapsed")


class TaskProgressColumn(TextColumn):
    """Show task progress as a percentage.

    Args:
        text_format (str, optional): Format for percentage display. Defaults to "[progress.percentage]{task.percentage:>3.0f}%".
        text_format_no_percentage (str, optional): Format if percentage is unknown. Defaults to "".
        style (StyleType, optional): Style of output. Defaults to "none".
        justify (JustifyMethod, optional): Text justification. Defaults to "left".
        markup (bool, optional): Enable markup. Defaults to True.
        highlighter (Optional[Highlighter], optional): Highlighter to apply to output. Defaults to None.
        table_column (Optional[Column], optional): Table Column to use. Defaults to None.
        show_speed (bool, optional): Show speed if total is unknown. Defaults to False.
    """

    def __init__(
        self,
        text_format: str = "[progress.percentage]{task.percentage:>3.0f}%",
        text_format_no_percentage: str = "",
        style: StyleType = "none",
        justify: JustifyMethod = "left",
        markup: bool = True,
        highlighter: Optional[Highlighter] = None,
        table_column: Optional[Column] = None,
        show_speed: bool = False,
    ) -> None:
        self.text_format_no_percentage = text_format_no_percentage
        self.show_speed = show_speed
        super().__init__(
            text_format=text_format,
            style=style,
            justify=justify,
            markup=markup,
            highlighter=highlighter,
            table_column=table_column,
        )

    @classmethod
    def render_speed(cls, speed: Optional[float]) -> Text:
        """Render the speed in iterations per second.

        Args:
            task (Task): A Task object.

        Returns:
            Text: Text object containing the task speed.
        """
        if speed is None:
            return Text("", style="progress.percentage")
        unit, suffix = filesize.pick_unit_and_suffix(
            int(speed),
            ["", "×10³", "×10⁶", "×10⁹", "×10¹²"],
            1000,
        )
        data_speed = speed / unit
        return Text(f"{data_speed:.1f}{suffix} it/s", style="progress.percentage")

    def render(self, task: "Task") -> Text:
        if task.total is None and self.show_speed:
            return self.render_speed(task.finished_speed or task.speed)
        text_format = (
            self.text_format_no_percentage if task.total is None else self.text_format
        )
        _text = text_format.format(task=task)
        if self.markup:
            text = Text.from_markup(_text, style=self.style, justify=self.justify)
        else:
            text = Text(_text, style=self.style, justify=self.justify)
        if self.highlighter:
            self.highlighter.highlight(text)
        return text


class TimeRemainingColumn(ProgressColumn):
    """Renders estimated time remaining.

    Args:
        compact (bool, optional): Render MM:SS when time remaining is less than an hour. Defaults to False.
        elapsed_when_finished (bool, optional): Render time elapsed when the task is finished. Defaults to False.
    """

    # Only refresh twice a second to prevent jitter
    max_refresh = 0.5

    def __init__(
        self,
        compact: bool = False,
        elapsed_when_finished: bool = False,
        table_column: Optional[Column] = None,
    ):
        self.compact = compact
        self.elapsed_when_finished = elapsed_when_finished
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> Text:
        """Show time remaining."""
        if self.elapsed_when_finished and task.finished:
            task_time = task.finished_time
            style = "progress.elapsed"
        else:
            task_time = task.time_remaining
            style = "progress.remaining"

        if task.total is None:
            return Text("", style=style)

        if task_time is None:
            return Text("--:--" if self.compact else "-:--:--", style=style)

        # Based on https://github.com/tqdm/tqdm/blob/master/tqdm/std.py
        minutes, seconds = divmod(int(task_time), 60)
        hours, minutes = divmod(minutes, 60)

        if self.compact and not hours:
            formatted = f"{minutes:02d}:{seconds:02d}"
        else:
            formatted = f"{hours:d}:{minutes:02d}:{seconds:02d}"

        return Text(formatted, style=style)


class FileSizeColumn(ProgressColumn):
    """Renders completed filesize."""

    def render(self, task: "Task") -> Text:
        """Show data completed."""
        data_size = filesize.decimal(int(task.completed))
        return Text(data_size, style="progress.filesize")


class TotalFileSizeColumn(ProgressColumn):
    """Renders total filesize."""

    def render(self, task: "Task") -> Text:
        """Show data completed."""
        data_size = filesize.decimal(int(task.total)) if task.total is not None else ""
        return Text(data_size, style="progress.filesize.total")


class MofNCompleteColumn(ProgressColumn):
    """Renders completed count/total, e.g. '  10/1000'.

    Best for bounded tasks with int quantities.

    Space pads the completed count so that progress length does not change as task progresses
    past powers of 10.

    Args:
        separator (str, optional): Text to separate completed and total values. Defaults to "/".
    """

    def __init__(self, separator: str = "/", table_column: Optional[Column] = None):
        self.separator = separator
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> Text:
        """Show completed/total."""
        completed = int(task.completed)
        total = int(task.total) if task.total is not None else "?"
        total_width = len(str(total))
        return Text(
            f"{completed:{total_width}d}{self.separator}{total}",
            style="progress.download",
        )


class DownloadColumn(ProgressColumn):
    """Renders file size downloaded and total, e.g. '0.5/2.3 GB'.

    Args:
        binary_units (bool, optional): Use binary units, KiB, MiB etc. Defaults to False.
    """

    def __init__(
        self, binary_units: bool = False, table_column: Optional[Column] = None
    ) -> None:
        self.binary_units = binary_units
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> Text:
        """Calculate common unit for completed and total."""
        completed = int(task.completed)

        unit_and_suffix_calculation_base = (
            int(task.total) if task.total is not None else completed
        )
        if self.binary_units:
            unit, suffix = filesize.pick_unit_and_suffix(
                unit_and_suffix_calculation_base,
                ["bytes", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"],
                1024,
            )
        else:
            unit, suffix = filesize.pick_unit_and_suffix(
                unit_and_suffix_calculation_base,
                ["bytes", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"],
                1000,
            )
        precision = 0 if unit == 1 else 1

        completed_ratio = completed / unit
        completed_str = f"{completed_ratio:,.{precision}f}"

        if task.total is not None:
            total = int(task.total)
            total_ratio = total / unit
            total_str = f"{total_ratio:,.{precision}f}"
        else:
            total_str = "?"

        download_status = f"{completed_str}/{total_str} {suffix}"
        download_text = Text(download_status, style="progress.download")
        return download_text


class TransferSpeedColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task: "Task") -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("?", style="progress.data.speed")
        data_speed = filesize.decimal(int(speed))
        return Text(f"{data_speed}/s", style="progress.data.speed")


class ProgressSample(NamedTuple):
    """Sample of progress for a given time."""

    timestamp: float
    """Timestamp of sample."""
    completed: float
    """Number of steps completed."""


@dataclass
class Task:
    """Information regarding a progress task.

    This object should be considered read-only outside of the :class:`~Progress` class.

    """

    id: TaskID
    """Task ID associated with this task (used in Progress methods)."""

    description: str
    """str: Description of the task."""

    total: Optional[float]
    """Optional[float]: Total number of steps in this task."""

    completed: float
    """float: Number of steps completed"""

    _get_time: GetTimeCallable
    """Callable to get the current time."""

    finished_time: Optional[float] = None
    """float: Time task was finished."""

    visible: bool = True
    """bool: Indicates if this task is visible in the progress display."""

    fields: Dict[str, Any] = field(default_factory=dict)
    """dict: Arbitrary fields passed in via Progress.update."""

    start_time: Optional[float] = field(default=None, init=False, repr=False)
    """Optional[float]: Time this task was started, or None if not started."""

    stop_time: Optional[float] = field(default=None, init=False, repr=False)
    """Optional[float]: Time this task was stopped, or None if not stopped."""

    finished_speed: Optional[float] = None
    """Optional[float]: The last speed for a finished task."""

    _progress: Deque[ProgressSample] = field(
        default_factory=lambda: deque(maxlen=1000), init=False, repr=False
    )

    _lock: RLock = field(repr=False, default_factory=RLock)
    """Thread lock."""

    def get_time(self) -> float:
        """float: Get the current time, in seconds."""
        return self._get_time()

    @property
    def started(self) -> bool:
        """bool: Check if the task as started."""
        return self.start_time is not None

    @property
    def remaining(self) -> Optional[float]:
        """Optional[float]: Get the number of steps remaining, if a non-None total was set."""
        if self.total is None:
            return None
        return self.total - self.completed

    @property
    def elapsed(self) -> Optional[float]:
        """Optional[float]: Time elapsed since task was started, or ``None`` if the task hasn't started."""
        if self.start_time is None:
            return None
        if self.stop_time is not None:
            return self.stop_time - self.start_time
        return self.get_time() - self.start_time

    @property
    def finished(self) -> bool:
        """Check if the task has finished."""
        return self.finished_time is not None

    @property
    def percentage(self) -> float:
        """float: Get progress of task as a percentage. If a None total was set, returns 0"""
        if not self.total:
            return 0.0
        completed = (self.completed / self.total) * 100.0
        completed = min(100.0, max(0.0, completed))
        return completed

    @property
    def speed(self) -> Optional[float]:
        """Optional[float]: Get the estimated speed in steps per second."""
        if self.start_time is None:
            return None
        with self._lock:
            progress = self._progress
            if not progress:
                return None
            total_time = progress[-1].timestamp - progress[0].timestamp
            if total_time == 0:
                return None
            iter_progress = iter(progress)
            next(iter_progress)
            total_completed = sum(sample.completed for sample in iter_progress)
            speed = total_completed / total_time
            return speed

    @property
    def time_remaining(self) -> Optional[float]:
        """Optional[float]: Get estimated time to completion, or ``None`` if no data."""
        if self.finished:
            return 0.0
        speed = self.speed
        if not speed:
            return None
        remaining = self.remaining
        if remaining is None:
            return None
        estimate = ceil(remaining / speed)
        return estimate

    def _reset(self) -> None:
        """Reset progress."""
        self._progress.clear()
        self.finished_time = None
        self.finished_speed = None


class Progress(JupyterMixin):
    """Renders an auto-updating progress bar(s).

    Args:
        console (Console, optional): Optional Console instance. Defaults to an internal Console instance writing to stdout.
        auto_refresh (bool, optional): Enable auto refresh. If disabled, you will need to call `refresh()`.
        refresh_per_second (Optional[float], optional): Number of times per second to refresh the progress information or None to use default (10). Defaults to None.
        speed_estimate_period: (float, optional): Period (in seconds) used to calculate the speed estimate. Defaults to 30.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        redirect_stdout: (bool, optional): Enable redirection of stdout, so ``print`` may be used. Defaults to True.
        redirect_stderr: (bool, optional): Enable redirection of stderr. Defaults to True.
        get_time: (Callable, optional): A callable that gets the current time, or None to use Console.get_time. Defaults to None.
        disable (bool, optional): Disable progress display. Defaults to False
        expand (bool, optional): Expand tasks table to fit width. Defaults to False.
    """

    def __init__(
        self,
        *columns: Union[str, ProgressColumn],
        console: Optional[Console] = None,
        auto_refresh: bool = True,
        refresh_per_second: float = 10,
        speed_estimate_period: float = 30.0,
        transient: bool = False,
        redirect_stdout: bool = True,
        redirect_stderr: bool = True,
        get_time: Optional[GetTimeCallable] = None,
        disable: bool = False,
        expand: bool = False,
    ) -> None:
        assert refresh_per_second > 0, "refresh_per_second must be > 0"
        self._lock = RLock()
        self.columns = columns or self.get_default_columns()
        self.speed_estimate_period = speed_estimate_period

        self.disable = disable
        self.expand = expand
        self._tasks: Dict[TaskID, Task] = {}
        self._task_index: TaskID = TaskID(0)
        self.live = Live(
            console=console or get_console(),
            auto_refresh=auto_refresh,
            refresh_per_second=refresh_per_second,
            transient=transient,
            redirect_stdout=redirect_stdout,
            redirect_stderr=redirect_stderr,
            get_renderable=self.get_renderable,
        )
        self.get_time = get_time or self.console.get_time
        self.print = self.console.print
        self.log = self.console.log

    @classmethod
    def get_default_columns(cls) -> Tuple[ProgressColumn, ...]:
        """Get the default columns used for a new Progress instance:
           - a text column for the description (TextColumn)
           - the bar itself (BarColumn)
           - a text column showing completion percentage (TextColumn)
           - an estimated-time-remaining column (TimeRemainingColumn)
        If the Progress instance is created without passing a columns argument,
        the default columns defined here will be used.

        You can also create a Progress instance using custom columns before
        and/or after the defaults, as in this example:

            progress = Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                "Elapsed:",
                TimeElapsedColumn(),
            )

        This code shows the creation of a Progress display, containing
        a spinner to the left, the default columns, and a labeled elapsed
        time column.
        """
        return (
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        )

    @property
    def console(self) -> Console:
        return self.live.console

    @property
    def tasks(self) -> List[Task]:
        """Get a list of Task instances."""
        with self._lock:
            return list(self._tasks.values())

    @property
    def task_ids(self) -> List[TaskID]:
        """A list of task IDs."""
        with self._lock:
            return list(self._tasks.keys())

    @property
    def finished(self) -> bool:
        """Check if all tasks have been completed."""
        with self._lock:
            if not self._tasks:
                return True
            return all(task.finished for task in self._tasks.values())

    def start(self) -> None:
        """Start the progress display."""
        if not self.disable:
            self.live.start(refresh=True)

    def stop(self) -> None:
        """Stop the progress display."""
        self.live.stop()
        if not self.console.is_interactive and not self.console.is_jupyter:
            self.console.print()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()

    def track(
        self,
        sequence: Union[Iterable[ProgressType], Sequence[ProgressType]],
        total: Optional[float] = None,
        completed: int = 0,
        task_id: Optional[TaskID] = None,
        description: str = "Working...",
        update_period: float = 0.1,
    ) -> Iterable[ProgressType]:
        """Track progress by iterating over a sequence.

        Args:
            sequence (Sequence[ProgressType]): A sequence of values you want to iterate over and track progress.
            total: (float, optional): Total number of steps. Default is len(sequence).
            completed (int, optional): Number of steps completed so far. Defaults to 0.
            task_id: (TaskID): Task to track. Default is new task.
            description: (str, optional): Description of task, if new task is created.
            update_period (float, optional): Minimum time (in seconds) between calls to update(). Defaults to 0.1.

        Returns:
            Iterable[ProgressType]: An iterable of values taken from the provided sequence.
        """
        if total is None:
            total = float(length_hint(sequence)) or None

        if task_id is None:
            task_id = self.add_task(description, total=total, completed=completed)
        else:
            self.update(task_id, total=total, completed=completed)

        if self.live.auto_refresh:
            with _TrackThread(self, task_id, update_period) as track_thread:
                for value in sequence:
                    yield value
                    track_thread.completed += 1
        else:
            advance = self.advance
            refresh = self.refresh
            for value in sequence:
                yield value
                advance(task_id, 1)
                refresh()

    def wrap_file(
        self,
        file: BinaryIO,
        total: Optional[int] = None,
        *,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> BinaryIO:
        """Track progress file reading from a binary file.

        Args:
            file (BinaryIO): A file-like object opened in binary mode.
            total (int, optional): Total number of bytes to read. This must be provided unless a task with a total is also given.
            task_id (TaskID): Task to track. Default is new task.
            description (str, optional): Description of task, if new task is created.

        Returns:
            BinaryIO: A readable file-like object in binary mode.

        Raises:
            ValueError: When no total value can be extracted from the arguments or the task.
        """
        # attempt to recover the total from the task
        total_bytes: Optional[float] = None
        if total is not None:
            total_bytes = total
        elif task_id is not None:
            with self._lock:
                total_bytes = self._tasks[task_id].total
        if total_bytes is None:
            raise ValueError(
                f"unable to get the total number of bytes, please specify 'total'"
            )

        # update total of task or create new task
        if task_id is None:
            task_id = self.add_task(description, total=total_bytes)
        else:
            self.update(task_id, total=total_bytes)

        return _Reader(file, self, task_id, close_handle=False)

    @typing.overload
    def open(
        self,
        file: Union[str, "PathLike[str]", bytes],
        mode: Literal["rb"],
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        *,
        total: Optional[int] = None,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> BinaryIO:
        pass

    @typing.overload
    def open(
        self,
        file: Union[str, "PathLike[str]", bytes],
        mode: Union[Literal["r"], Literal["rt"]],
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        *,
        total: Optional[int] = None,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> TextIO:
        pass

    def open(
        self,
        file: Union[str, "PathLike[str]", bytes],
        mode: Union[Literal["rb"], Literal["rt"], Literal["r"]] = "r",
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        *,
        total: Optional[int] = None,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> Union[BinaryIO, TextIO]:
        """Track progress while reading from a binary file.

        Args:
            path (Union[str, PathLike[str]]): The path to the file to read.
            mode (str): The mode to use to open the file. Only supports "r", "rb" or "rt".
            buffering (int): The buffering strategy to use, see :func:`io.open`.
            encoding (str, optional): The encoding to use when reading in text mode, see :func:`io.open`.
            errors (str, optional): The error handling strategy for decoding errors, see :func:`io.open`.
            newline (str, optional): The strategy for handling newlines in text mode, see :func:`io.open`.
            total (int, optional): Total number of bytes to read. If none given, os.stat(path).st_size is used.
            task_id (TaskID): Task to track. Default is new task.
            description (str, optional): Description of task, if new task is created.

        Returns:
            BinaryIO: A readable file-like object in binary mode.

        Raises:
            ValueError: When an invalid mode is given.
        """
        # normalize the mode (always rb, rt)
        _mode = "".join(sorted(mode, reverse=False))
        if _mode not in ("br", "rt", "r"):
            raise ValueError(f"invalid mode {mode!r}")

        # patch buffering to provide the same behaviour as the builtin `open`
        line_buffering = buffering == 1
        if _mode == "br" and buffering == 1:
            warnings.warn(
                "line buffering (buffering=1) isn't supported in binary mode, the default buffer size will be used",
                RuntimeWarning,
            )
            buffering = -1
        elif _mode in ("rt", "r"):
            if buffering == 0:
                raise ValueError("can't have unbuffered text I/O")
            elif buffering == 1:
                buffering = -1

        # attempt to get the total with `os.stat`
        if total is None:
            total = stat(file).st_size

        # update total of task or create new task
        if task_id is None:
            task_id = self.add_task(description, total=total)
        else:
            self.update(task_id, total=total)

        # open the file in binary mode,
        handle = io.open(file, "rb", buffering=buffering)
        reader = _Reader(handle, self, task_id, close_handle=True)

        # wrap the reader in a `TextIOWrapper` if text mode
        if mode in ("r", "rt"):
            return io.TextIOWrapper(
                reader,
                encoding=encoding,
                errors=errors,
                newline=newline,
                line_buffering=line_buffering,
            )

        return reader

    def start_task(self, task_id: TaskID) -> None:
        """Start a task.

        Starts a task (used when calculating elapsed time). You may need to call this manually,
        if you called ``add_task`` with ``start=False``.

        Args:
            task_id (TaskID): ID of task.
        """
        with self._lock:
            task = self._tasks[task_id]
            if task.start_time is None:
                task.start_time = self.get_time()

    def stop_task(self, task_id: TaskID) -> None:
        """Stop a task.

        This will freeze the elapsed time on the task.

        Args:
            task_id (TaskID): ID of task.
        """
        with self._lock:
            task = self._tasks[task_id]
            current_time = self.get_time()
            if task.start_time is None:
                task.start_time = current_time
            task.stop_time = current_time

    def update(
        self,
        task_id: TaskID,
        *,
        total: Optional[float] = None,
        completed: Optional[float] = None,
        advance: Optional[float] = None,
        description: Optional[str] = None,
        visible: Optional[bool] = None,
        refresh: bool = False,
        **fields: Any,
    ) -> None:
        """Update information associated with a task.

        Args:
            task_id (TaskID): Task id (returned by add_task).
            total (float, optional): Updates task.total if not None.
            completed (float, optional): Updates task.completed if not None.
            advance (float, optional): Add a value to task.completed if not None.
            description (str, optional): Change task description if not None.
            visible (bool, optional): Set visible flag if not None.
            refresh (bool): Force a refresh of progress information. Default is False.
            **fields (Any): Additional data fields required for rendering.
        """
        with self._lock:
            task = self._tasks[task_id]
            completed_start = task.completed

            if total is not None and total != task.total:
                task.total = total
                task._reset()
            if advance is not None:
                task.completed += advance
            if completed is not None:
                task.completed = completed
            if description is not None:
                task.description = description
            if visible is not None:
                task.visible = visible
            task.fields.update(fields)
            update_completed = task.completed - completed_start

            current_time = self.get_time()
            old_sample_time = current_time - self.speed_estimate_period
            _progress = task._progress

            popleft = _progress.popleft
            while _progress and _progress[0].timestamp < old_sample_time:
                popleft()
            if update_completed > 0:
                _progress.append(ProgressSample(current_time, update_completed))
            if (
                task.total is not None
                and task.completed >= task.total
                and task.finished_time is None
            ):
                task.finished_time = task.elapsed

        if refresh:
            self.refresh()

    def reset(
        self,
        task_id: TaskID,
        *,
        start: bool = True,
        total: Optional[float] = None,
        completed: int = 0,
        visible: Optional[bool] = None,
        description: Optional[str] = None,
        **fields: Any,
    ) -> None:
        """Reset a task so completed is 0 and the clock is reset.

        Args:
            task_id (TaskID): ID of task.
            start (bool, optional): Start the task after reset. Defaults to True.
            total (float, optional): New total steps in task, or None to use current total. Defaults to None.
            completed (int, optional): Number of steps completed. Defaults to 0.
            visible (bool, optional): Enable display of the task. Defaults to True.
            description (str, optional): Change task description if not None. Defaults to None.
            **fields (str): Additional data fields required for rendering.
        """
        current_time = self.get_time()
        with self._lock:
            task = self._tasks[task_id]
            task._reset()
            task.start_time = current_time if start else None
            if total is not None:
                task.total = total
            task.completed = completed
            if visible is not None:
                task.visible = visible
            if fields:
                task.fields = fields
            if description is not None:
                task.description = description
            task.finished_time = None
        self.refresh()

    def advance(self, task_id: TaskID, advance: float = 1) -> None:
        """Advance task by a number of steps.

        Args:
            task_id (TaskID): ID of task.
            advance (float): Number of steps to advance. Default is 1.
        """
        current_time = self.get_time()
        with self._lock:
            task = self._tasks[task_id]
            completed_start = task.completed
            task.completed += advance
            update_completed = task.completed - completed_start
            old_sample_time = current_time - self.speed_estimate_period
            _progress = task._progress

            popleft = _progress.popleft
            while _progress and _progress[0].timestamp < old_sample_time:
                popleft()
            while len(_progress) > 1000:
                popleft()
            _progress.append(ProgressSample(current_time, update_completed))
            if (
                task.total is not None
                and task.completed >= task.total
                and task.finished_time is None
            ):
                task.finished_time = task.elapsed
                task.finished_speed = task.speed

    def refresh(self) -> None:
        """Refresh (render) the progress information."""
        if not self.disable and self.live.is_started:
            self.live.refresh()

    def get_renderable(self) -> RenderableType:
        """Get a renderable for the progress display."""
        renderable = Group(*self.get_renderables())
        return renderable

    def get_renderables(self) -> Iterable[RenderableType]:
        """Get a number of renderables for the progress display."""
        table = self.make_tasks_table(self.tasks)
        yield table

    def make_tasks_table(self, tasks: Iterable[Task]) -> Table:
        """Get a table to render the Progress display.

        Args:
            tasks (Iterable[Task]): An iterable of Task instances, one per row of the table.

        Returns:
            Table: A table instance.
        """
        table_columns = (
            (
                Column(no_wrap=True)
                if isinstance(_column, str)
                else _column.get_table_column().copy()
            )
            for _column in self.columns
        )
        table = Table.grid(*table_columns, padding=(0, 1), expand=self.expand)

        for task in tasks:
            if task.visible:
                table.add_row(
                    *(
                        (
                            column.format(task=task)
                            if isinstance(column, str)
                            else column(task)
                        )
                        for column in self.columns
                    )
                )
        return table

    def __rich__(self) -> RenderableType:
        """Makes the Progress class itself renderable."""
        with self._lock:
            return self.get_renderable()

    def add_task(
        self,
        description: str,
        start: bool = True,
        total: Optional[float] = 100.0,
        completed: int = 0,
        visible: bool = True,
        **fields: Any,
    ) -> TaskID:
        """Add a new 'task' to the Progress display.

        Args:
            description (str): A description of the task.
            start (bool, optional): Start the task immediately (to calculate elapsed time). If set to False,
                you will need to call `start` manually. Defaults to True.
            total (float, optional): Number of total steps in the progress if known.
                Set to None to render a pulsing animation. Defaults to 100.
            completed (int, optional): Number of steps completed so far. Defaults to 0.
            visible (bool, optional): Enable display of the task. Defaults to True.
            **fields (str): Additional data fields required for rendering.

        Returns:
            TaskID: An ID you can use when calling `update`.
        """
        with self._lock:
            task = Task(
                self._task_index,
                description,
                total,
                completed,
                visible=visible,
                fields=fields,
                _get_time=self.get_time,
                _lock=self._lock,
            )
            self._tasks[self._task_index] = task
            if start:
                self.start_task(self._task_index)
            new_task_index = self._task_index
            self._task_index = TaskID(int(self._task_index) + 1)
        self.refresh()
        return new_task_index

    def remove_task(self, task_id: TaskID) -> None:
        """Delete a task if it exists.

        Args:
            task_id (TaskID): A task ID.

        """
        with self._lock:
            del self._tasks[task_id]


if __name__ == "__main__":  # pragma: no coverage
    import random
    import time

    from .panel import Panel
    from .rule import Rule
    from .syntax import Syntax
    from .table import Table

    syntax = Syntax(
        '''def loop_last(values: Iterable[T]) -> Iterable[Tuple[bool, T]]:
    """Iterate and generate a tuple with a flag for last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    for value in iter_values:
        yield False, previous_value
        previous_value = value
    yield True, previous_value''',
        "python",
        line_numbers=True,
    )

    table = Table("foo", "bar", "baz")
    table.add_row("1", "2", "3")

    progress_renderables = [
        "Text may be printed while the progress bars are rendering.",
        Panel("In fact, [i]any[/i] renderable will work"),
        "Such as [magenta]tables[/]...",
        table,
        "Pretty printed structures...",
        {"type": "example", "text": "Pretty printed"},
        "Syntax...",
        syntax,
        Rule("Give it a try!"),
    ]

    from itertools import cycle

    examples = cycle(progress_renderables)

    console = Console(record=True)

    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task1 = progress.add_task("[red]Downloading", total=1000)
        task2 = progress.add_task("[green]Processing", total=1000)
        task3 = progress.add_task("[yellow]Thinking", total=None)

        while not progress.finished:
            progress.update(task1, advance=0.5)
            progress.update(task2, advance=0.3)
            time.sleep(0.01)
            if random.randint(0, 100) < 1:
                progress.log(next(examples))