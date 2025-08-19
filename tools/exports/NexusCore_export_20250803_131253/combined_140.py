
# === NexusCore/tools\exports\export_20250803_114325\combined_53.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_utils.py ===
from io import StringIO

import pytest

import numpy as np
import numpy.lib._utils_impl as _utils_impl
from numpy.testing import assert_raises_regex


def test_assert_raises_regex_context_manager():
    with assert_raises_regex(ValueError, 'no deprecation warning'):
        raise ValueError('no deprecation warning')


def test_info_method_heading():
    # info(class) should only print "Methods:" heading if methods exist

    class NoPublicMethods:
        pass

    class WithPublicMethods:
        def first_method():
            pass

    def _has_method_heading(cls):
        out = StringIO()
        np.info(cls, output=out)
        return 'Methods:' in out.getvalue()

    assert _has_method_heading(WithPublicMethods)
    assert not _has_method_heading(NoPublicMethods)


def test_drop_metadata():
    def _compare_dtypes(dt1, dt2):
        return np.can_cast(dt1, dt2, casting='no')

    # structured dtype
    dt = np.dtype([('l1', [('l2', np.dtype('S8', metadata={'msg': 'toto'}))])],
                  metadata={'msg': 'titi'})
    dt_m = _utils_impl.drop_metadata(dt)
    assert _compare_dtypes(dt, dt_m) is True
    assert dt_m.metadata is None
    assert dt_m['l1'].metadata is None
    assert dt_m['l1']['l2'].metadata is None

    # alignment
    dt = np.dtype([('x', '<f8'), ('y', '<i4')],
                  align=True,
                  metadata={'msg': 'toto'})
    dt_m = _utils_impl.drop_metadata(dt)
    assert _compare_dtypes(dt, dt_m) is True
    assert dt_m.metadata is None

    # subdtype
    dt = np.dtype('8f',
                  metadata={'msg': 'toto'})
    dt_m = _utils_impl.drop_metadata(dt)
    assert _compare_dtypes(dt, dt_m) is True
    assert dt_m.metadata is None

    # scalar
    dt = np.dtype('uint32',
                  metadata={'msg': 'toto'})
    dt_m = _utils_impl.drop_metadata(dt)
    assert _compare_dtypes(dt, dt_m) is True
    assert dt_m.metadata is None


@pytest.mark.parametrize("dtype",
        [np.dtype("i,i,i,i")[["f1", "f3"]],
        np.dtype("f8"),
        np.dtype("10i")])
def test_drop_metadata_identity_and_copy(dtype):
    # If there is no metadata, the identity is preserved:
    assert _utils_impl.drop_metadata(dtype) is dtype

    # If there is any, it is dropped (subforms are checked above)
    dtype = np.dtype(dtype, metadata={1: 2})
    assert _utils_impl.drop_metadata(dtype).metadata is None

# === NexusCore/openenv\Lib\site-packages\nltk\probability.py ===
# Natural Language Toolkit: Probability and Statistics
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com> (additions)
#         Trevor Cohn <tacohn@cs.mu.oz.au> (additions)
#         Peter Ljunglöf <peter.ljunglof@heatherleaf.se> (additions)
#         Liang Dong <ldong@clemson.edu> (additions)
#         Geoffrey Sampson <sampson@cantab.net> (additions)
#         Ilia Kurenkov <ilia.kurenkov@gmail.com> (additions)
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Classes for representing and processing probabilistic information.

The ``FreqDist`` class is used to encode "frequency distributions",
which count the number of times that each outcome of an experiment
occurs.

The ``ProbDistI`` class defines a standard interface for "probability
distributions", which encode the probability of each outcome for an
experiment.  There are two types of probability distribution:

  - "derived probability distributions" are created from frequency
    distributions.  They attempt to model the probability distribution
    that generated the frequency distribution.
  - "analytic probability distributions" are created directly from
    parameters (such as variance).

The ``ConditionalFreqDist`` class and ``ConditionalProbDistI`` interface
are used to encode conditional distributions.  Conditional probability
distributions can be derived or analytic; but currently the only
implementation of the ``ConditionalProbDistI`` interface is
``ConditionalProbDist``, a derived distribution.

"""

import array
import math
import random
import warnings
from abc import ABCMeta, abstractmethod
from collections import Counter, defaultdict
from functools import reduce

from nltk.internals import raise_unorderable_types

_NINF = float("-1e300")

##//////////////////////////////////////////////////////
##  Frequency Distributions
##//////////////////////////////////////////////////////


class FreqDist(Counter):
    """
    A frequency distribution for the outcomes of an experiment.  A
    frequency distribution records the number of times each outcome of
    an experiment has occurred.  For example, a frequency distribution
    could be used to record the frequency of each word type in a
    document.  Formally, a frequency distribution can be defined as a
    function mapping from each sample to the number of times that
    sample occurred as an outcome.

    Frequency distributions are generally constructed by running a
    number of experiments, and incrementing the count for a sample
    every time it is an outcome of an experiment.  For example, the
    following code will produce a frequency distribution that encodes
    how often each word occurs in a text:

        >>> from nltk.tokenize import word_tokenize
        >>> from nltk.probability import FreqDist
        >>> sent = 'This is an example sentence'
        >>> fdist = FreqDist()
        >>> for word in word_tokenize(sent):
        ...    fdist[word.lower()] += 1

    An equivalent way to do this is with the initializer:

        >>> fdist = FreqDist(word.lower() for word in word_tokenize(sent))

    """

    def __init__(self, samples=None):
        """
        Construct a new frequency distribution.  If ``samples`` is
        given, then the frequency distribution will be initialized
        with the count of each object in ``samples``; otherwise, it
        will be initialized to be empty.

        In particular, ``FreqDist()`` returns an empty frequency
        distribution; and ``FreqDist(samples)`` first creates an empty
        frequency distribution, and then calls ``update`` with the
        list ``samples``.

        :param samples: The samples to initialize the frequency
            distribution with.
        :type samples: Sequence
        """
        Counter.__init__(self, samples)

        # Cached number of samples in this FreqDist
        self._N = None

    def N(self):
        """
        Return the total number of sample outcomes that have been
        recorded by this FreqDist.  For the number of unique
        sample values (or bins) with counts greater than zero, use
        ``FreqDist.B()``.

        :rtype: int
        """
        if self._N is None:
            # Not already cached, or cache has been invalidated
            self._N = sum(self.values())
        return self._N

    def __setitem__(self, key, val):
        """
        Override ``Counter.__setitem__()`` to invalidate the cached N
        """
        self._N = None
        super().__setitem__(key, val)

    def __delitem__(self, key):
        """
        Override ``Counter.__delitem__()`` to invalidate the cached N
        """
        self._N = None
        super().__delitem__(key)

    def update(self, *args, **kwargs):
        """
        Override ``Counter.update()`` to invalidate the cached N
        """
        self._N = None
        super().update(*args, **kwargs)

    def setdefault(self, key, val):
        """
        Override ``Counter.setdefault()`` to invalidate the cached N
        """
        self._N = None
        super().setdefault(key, val)

    def B(self):
        """
        Return the total number of sample values (or "bins") that
        have counts greater than zero.  For the total
        number of sample outcomes recorded, use ``FreqDist.N()``.
        (FreqDist.B() is the same as len(FreqDist).)

        :rtype: int
        """
        return len(self)

    def hapaxes(self):
        """
        Return a list of all samples that occur once (hapax legomena)

        :rtype: list
        """
        return [item for item in self if self[item] == 1]

    def Nr(self, r, bins=None):
        return self.r_Nr(bins)[r]

    def r_Nr(self, bins=None):
        """
        Return the dictionary mapping r to Nr, the number of samples with frequency r, where Nr > 0.

        :type bins: int
        :param bins: The number of possible sample outcomes.  ``bins``
            is used to calculate Nr(0).  In particular, Nr(0) is
            ``bins-self.B()``.  If ``bins`` is not specified, it
            defaults to ``self.B()`` (so Nr(0) will be 0).
        :rtype: int
        """

        _r_Nr = defaultdict(int)
        for count in self.values():
            _r_Nr[count] += 1

        # Special case for Nr[0]:
        _r_Nr[0] = bins - self.B() if bins is not None else 0

        return _r_Nr

    def _cumulative_frequencies(self, samples):
        """
        Return the cumulative frequencies of the specified samples.
        If no samples are specified, all counts are returned, starting
        with the largest.

        :param samples: the samples whose frequencies should be returned.
        :type samples: any
        :rtype: list(float)
        """
        cf = 0.0
        for sample in samples:
            cf += self[sample]
            yield cf

    # slightly odd nomenclature freq() if FreqDist does counts and ProbDist does probs,
    # here, freq() does probs
    def freq(self, sample):
        """
        Return the frequency of a given sample.  The frequency of a
        sample is defined as the count of that sample divided by the
        total number of sample outcomes that have been recorded by
        this FreqDist.  The count of a sample is defined as the
        number of times that sample outcome was recorded by this
        FreqDist.  Frequencies are always real numbers in the range
        [0, 1].

        :param sample: the sample whose frequency
               should be returned.
        :type sample: any
        :rtype: float
        """
        n = self.N()
        if n == 0:
            return 0
        return self[sample] / n

    def max(self):
        """
        Return the sample with the greatest number of outcomes in this
        frequency distribution.  If two or more samples have the same
        number of outcomes, return one of them; which sample is
        returned is undefined.  If no outcomes have occurred in this
        frequency distribution, return None.

        :return: The sample with the maximum number of outcomes in this
                frequency distribution.
        :rtype: any or None
        """
        if len(self) == 0:
            raise ValueError(
                "A FreqDist must have at least one sample before max is defined."
            )
        return self.most_common(1)[0][0]

    def plot(
        self, *args, title="", cumulative=False, percents=False, show=False, **kwargs
    ):
        """
        Plot samples from the frequency distribution
        displaying the most frequent sample first.  If an integer
        parameter is supplied, stop after this many samples have been
        plotted.  For a cumulative plot, specify cumulative=True. Additional
        ``**kwargs`` are passed to matplotlib's plot function.
        (Requires Matplotlib to be installed.)

        :param title: The title for the graph.
        :type title: str
        :param cumulative: Whether the plot is cumulative. (default = False)
        :type cumulative: bool
        :param percents: Whether the plot uses percents instead of counts. (default = False)
        :type percents: bool
        :param show: Whether to show the plot, or only return the ax.
        :type show: bool
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError as e:
            raise ValueError(
                "The plot function requires matplotlib to be installed."
                "See https://matplotlib.org/"
            ) from e

        if len(args) == 0:
            args = [len(self)]
        samples = [item for item, _ in self.most_common(*args)]

        if cumulative:
            freqs = list(self._cumulative_frequencies(samples))
            ylabel = "Cumulative "
        else:
            freqs = [self[sample] for sample in samples]
            ylabel = ""

        if percents:
            freqs = [f / self.N() * 100 for f in freqs]
            ylabel += "Percents"
        else:
            ylabel += "Counts"

        ax = plt.gca()
        ax.grid(True, color="silver")

        if "linewidth" not in kwargs:
            kwargs["linewidth"] = 2
        if title:
            ax.set_title(title)

        ax.plot(freqs, **kwargs)
        ax.set_xticks(range(len(samples)))
        ax.set_xticklabels([str(s) for s in samples], rotation=90)
        ax.set_xlabel("Samples")
        ax.set_ylabel(ylabel)

        if show:
            plt.show()

        return ax

    def tabulate(self, *args, **kwargs):
        """
        Tabulate the given samples from the frequency distribution (cumulative),
        displaying the most frequent sample first.  If an integer
        parameter is supplied, stop after this many samples have been
        plotted.

        :param samples: The samples to plot (default is all samples)
        :type samples: list
        :param cumulative: A flag to specify whether the freqs are cumulative (default = False)
        :type title: bool
        """
        if len(args) == 0:
            args = [len(self)]
        samples = _get_kwarg(
            kwargs, "samples", [item for item, _ in self.most_common(*args)]
        )

        cumulative = _get_kwarg(kwargs, "cumulative", False)
        if cumulative:
            freqs = list(self._cumulative_frequencies(samples))
        else:
            freqs = [self[sample] for sample in samples]
        # percents = [f * 100 for f in freqs]  only in ProbDist?

        width = max(len(f"{s}") for s in samples)
        width = max(width, max(len("%d" % f) for f in freqs))

        for i in range(len(samples)):
            print("%*s" % (width, samples[i]), end=" ")
        print()
        for i in range(len(samples)):
            print("%*d" % (width, freqs[i]), end=" ")
        print()

    def copy(self):
        """
        Create a copy of this frequency distribution.

        :rtype: FreqDist
        """
        return self.__class__(self)

    # Mathematical operatiors

    def __add__(self, other):
        """
        Add counts from two counters.

        >>> FreqDist('abbb') + FreqDist('bcc')
        FreqDist({'b': 4, 'c': 2, 'a': 1})

        """
        return self.__class__(super().__add__(other))

    def __sub__(self, other):
        """
        Subtract count, but keep only results with positive counts.

        >>> FreqDist('abbbc') - FreqDist('bccd')
        FreqDist({'b': 2, 'a': 1})

        """
        return self.__class__(super().__sub__(other))

    def __or__(self, other):
        """
        Union is the maximum of value in either of the input counters.

        >>> FreqDist('abbb') | FreqDist('bcc')
        FreqDist({'b': 3, 'c': 2, 'a': 1})

        """
        return self.__class__(super().__or__(other))

    def __and__(self, other):
        """
        Intersection is the minimum of corresponding counts.

        >>> FreqDist('abbb') & FreqDist('bcc')
        FreqDist({'b': 1})

        """
        return self.__class__(super().__and__(other))

    def __le__(self, other):
        """
        Returns True if this frequency distribution is a subset of the other
        and for no key the value exceeds the value of the same key from
        the other frequency distribution.

        The <= operator forms partial order and satisfying the axioms
        reflexivity, antisymmetry and transitivity.

        >>> FreqDist('a') <= FreqDist('a')
        True
        >>> a = FreqDist('abc')
        >>> b = FreqDist('aabc')
        >>> (a <= b, b <= a)
        (True, False)
        >>> FreqDist('a') <= FreqDist('abcd')
        True
        >>> FreqDist('abc') <= FreqDist('xyz')
        False
        >>> FreqDist('xyz') <= FreqDist('abc')
        False
        >>> c = FreqDist('a')
        >>> d = FreqDist('aa')
        >>> e = FreqDist('aaa')
        >>> c <= d and d <= e and c <= e
        True
        """
        if not isinstance(other, FreqDist):
            raise_unorderable_types("<=", self, other)
        return set(self).issubset(other) and all(
            self[key] <= other[key] for key in self
        )

    def __ge__(self, other):
        if not isinstance(other, FreqDist):
            raise_unorderable_types(">=", self, other)
        return set(self).issuperset(other) and all(
            self[key] >= other[key] for key in other
        )

    __lt__ = lambda self, other: self <= other and not self == other
    __gt__ = lambda self, other: self >= other and not self == other

    def __repr__(self):
        """
        Return a string representation of this FreqDist.

        :rtype: string
        """
        return self.pformat()

    def pprint(self, maxlen=10, stream=None):
        """
        Print a string representation of this FreqDist to 'stream'

        :param maxlen: The maximum number of items to print
        :type maxlen: int
        :param stream: The stream to print to. stdout by default
        """
        print(self.pformat(maxlen=maxlen), file=stream)

    def pformat(self, maxlen=10):
        """
        Return a string representation of this FreqDist.

        :param maxlen: The maximum number of items to display
        :type maxlen: int
        :rtype: string
        """
        items = ["{!r}: {!r}".format(*item) for item in self.most_common(maxlen)]
        if len(self) > maxlen:
            items.append("...")
        return "FreqDist({{{0}}})".format(", ".join(items))

    def __str__(self):
        """
        Return a string representation of this FreqDist.

        :rtype: string
        """
        return "<FreqDist with %d samples and %d outcomes>" % (len(self), self.N())

    def __iter__(self):
        """
        Return an iterator which yields tokens ordered by frequency.

        :rtype: iterator
        """
        for token, _ in self.most_common(self.B()):
            yield token


##//////////////////////////////////////////////////////
##  Probability Distributions
##//////////////////////////////////////////////////////


class ProbDistI(metaclass=ABCMeta):
    """
    A probability distribution for the outcomes of an experiment.  A
    probability distribution specifies how likely it is that an
    experiment will have any given outcome.  For example, a
    probability distribution could be used to predict the probability
    that a token in a document will have a given type.  Formally, a
    probability distribution can be defined as a function mapping from
    samples to nonnegative real numbers, such that the sum of every
    number in the function's range is 1.0.  A ``ProbDist`` is often
    used to model the probability distribution of the experiment used
    to generate a frequency distribution.
    """

    SUM_TO_ONE = True
    """True if the probabilities of the samples in this probability
       distribution will always sum to one."""

    @abstractmethod
    def __init__(self):
        """
        Classes inheriting from ProbDistI should implement __init__.
        """

    @abstractmethod
    def prob(self, sample):
        """
        Return the probability for a given sample.  Probabilities
        are always real numbers in the range [0, 1].

        :param sample: The sample whose probability
               should be returned.
        :type sample: any
        :rtype: float
        """

    def logprob(self, sample):
        """
        Return the base 2 logarithm of the probability for a given sample.

        :param sample: The sample whose probability
               should be returned.
        :type sample: any
        :rtype: float
        """
        # Default definition, in terms of prob()
        p = self.prob(sample)
        return math.log(p, 2) if p != 0 else _NINF

    @abstractmethod
    def max(self):
        """
        Return the sample with the greatest probability.  If two or
        more samples have the same probability, return one of them;
        which sample is returned is undefined.

        :rtype: any
        """

    @abstractmethod
    def samples(self):
        """
        Return a list of all samples that have nonzero probabilities.
        Use ``prob`` to find the probability of each sample.

        :rtype: list
        """

    # cf self.SUM_TO_ONE
    def discount(self):
        """
        Return the ratio by which counts are discounted on average: c*/c

        :rtype: float
        """
        return 0.0

    # Subclasses should define more efficient implementations of this,
    # where possible.
    def generate(self):
        """
        Return a randomly selected sample from this probability distribution.
        The probability of returning each sample ``samp`` is equal to
        ``self.prob(samp)``.
        """
        p = random.random()
        p_init = p
        for sample in self.samples():
            p -= self.prob(sample)
            if p <= 0:
                return sample
        # allow for some rounding error:
        if p < 0.0001:
            return sample
        # we *should* never get here
        if self.SUM_TO_ONE:
            warnings.warn(
                "Probability distribution %r sums to %r; generate()"
                " is returning an arbitrary sample." % (self, p_init - p)
            )
        return random.choice(list(self.samples()))


class UniformProbDist(ProbDistI):
    """
    A probability distribution that assigns equal probability to each
    sample in a given set; and a zero probability to all other
    samples.
    """

    def __init__(self, samples):
        """
        Construct a new uniform probability distribution, that assigns
        equal probability to each sample in ``samples``.

        :param samples: The samples that should be given uniform
            probability.
        :type samples: list
        :raise ValueError: If ``samples`` is empty.
        """
        if len(samples) == 0:
            raise ValueError(
                "A Uniform probability distribution must " + "have at least one sample."
            )
        self._sampleset = set(samples)
        self._prob = 1.0 / len(self._sampleset)
        self._samples = list(self._sampleset)

    def prob(self, sample):
        return self._prob if sample in self._sampleset else 0

    def max(self):
        return self._samples[0]

    def samples(self):
        return self._samples

    def __repr__(self):
        return "<UniformProbDist with %d samples>" % len(self._sampleset)


class RandomProbDist(ProbDistI):
    """
    Generates a random probability distribution whereby each sample
    will be between 0 and 1 with equal probability (uniform random distribution.
    Also called a continuous uniform distribution).
    """

    def __init__(self, samples):
        if len(samples) == 0:
            raise ValueError(
                "A probability distribution must " + "have at least one sample."
            )
        self._probs = self.unirand(samples)
        self._samples = list(self._probs.keys())

    @classmethod
    def unirand(cls, samples):
        """
        The key function that creates a randomized initial distribution
        that still sums to 1. Set as a dictionary of prob values so that
        it can still be passed to MutableProbDist and called with identical
        syntax to UniformProbDist
        """
        samples = set(samples)
        randrow = [random.random() for i in range(len(samples))]
        total = sum(randrow)
        for i, x in enumerate(randrow):
            randrow[i] = x / total

        total = sum(randrow)
        if total != 1:
            # this difference, if present, is so small (near NINF) that it
            # can be subtracted from any element without risking probs not (0 1)
            randrow[-1] -= total - 1

        return {s: randrow[i] for i, s in enumerate(samples)}

    def max(self):
        if not hasattr(self, "_max"):
            self._max = max((p, v) for (v, p) in self._probs.items())[1]
        return self._max

    def prob(self, sample):
        return self._probs.get(sample, 0)

    def samples(self):
        return self._samples

    def __repr__(self):
        return "<RandomUniformProbDist with %d samples>" % len(self._probs)


class DictionaryProbDist(ProbDistI):
    """
    A probability distribution whose probabilities are directly
    specified by a given dictionary.  The given dictionary maps
    samples to probabilities.
    """

    def __init__(self, prob_dict=None, log=False, normalize=False):
        """
        Construct a new probability distribution from the given
        dictionary, which maps values to probabilities (or to log
        probabilities, if ``log`` is true).  If ``normalize`` is
        true, then the probability values are scaled by a constant
        factor such that they sum to 1.

        If called without arguments, the resulting probability
        distribution assigns zero probability to all values.
        """

        self._prob_dict = prob_dict.copy() if prob_dict is not None else {}
        self._log = log

        # Normalize the distribution, if requested.
        if normalize:
            if len(prob_dict) == 0:
                raise ValueError(
                    "A DictionaryProbDist must have at least one sample "
                    + "before it can be normalized."
                )
            if log:
                value_sum = sum_logs(list(self._prob_dict.values()))
                if value_sum <= _NINF:
                    logp = math.log(1.0 / len(prob_dict), 2)
                    for x in prob_dict:
                        self._prob_dict[x] = logp
                else:
                    for x, p in self._prob_dict.items():
                        self._prob_dict[x] -= value_sum
            else:
                value_sum = sum(self._prob_dict.values())
                if value_sum == 0:
                    p = 1.0 / len(prob_dict)
                    for x in prob_dict:
                        self._prob_dict[x] = p
                else:
                    norm_factor = 1.0 / value_sum
                    for x, p in self._prob_dict.items():
                        self._prob_dict[x] *= norm_factor

    def prob(self, sample):
        if self._log:
            return 2 ** (self._prob_dict[sample]) if sample in self._prob_dict else 0
        else:
            return self._prob_dict.get(sample, 0)

    def logprob(self, sample):
        if self._log:
            return self._prob_dict.get(sample, _NINF)
        else:
            if sample not in self._prob_dict:
                return _NINF
            elif self._prob_dict[sample] == 0:
                return _NINF
            else:
                return math.log(self._prob_dict[sample], 2)

    def max(self):
        if not hasattr(self, "_max"):
            self._max = max((p, v) for (v, p) in self._prob_dict.items())[1]
        return self._max

    def samples(self):
        return self._prob_dict.keys()

    def __repr__(self):
        return "<ProbDist with %d samples>" % len(self._prob_dict)


class MLEProbDist(ProbDistI):
    """
    The maximum likelihood estimate for the probability distribution
    of the experiment used to generate a frequency distribution.  The
    "maximum likelihood estimate" approximates the probability of
    each sample as the frequency of that sample in the frequency
    distribution.
    """

    def __init__(self, freqdist, bins=None):
        """
        Use the maximum likelihood estimate to create a probability
        distribution for the experiment used to generate ``freqdist``.

        :type freqdist: FreqDist
        :param freqdist: The frequency distribution that the
            probability estimates should be based on.
        """
        self._freqdist = freqdist

    def freqdist(self):
        """
        Return the frequency distribution that this probability
        distribution is based on.

        :rtype: FreqDist
        """
        return self._freqdist

    def prob(self, sample):
        return self._freqdist.freq(sample)

    def max(self):
        return self._freqdist.max()

    def samples(self):
        return self._freqdist.keys()

    def __repr__(self):
        """
        :rtype: str
        :return: A string representation of this ``ProbDist``.
        """
        return "<MLEProbDist based on %d samples>" % self._freqdist.N()


class LidstoneProbDist(ProbDistI):
    """
    The Lidstone estimate for the probability distribution of the
    experiment used to generate a frequency distribution.  The
    "Lidstone estimate" is parameterized by a real number *gamma*,
    which typically ranges from 0 to 1.  The Lidstone estimate
    approximates the probability of a sample with count *c* from an
    experiment with *N* outcomes and *B* bins as
    ``c+gamma)/(N+B*gamma)``.  This is equivalent to adding
    *gamma* to the count for each bin, and taking the maximum
    likelihood estimate of the resulting frequency distribution.
    """

    SUM_TO_ONE = False

    def __init__(self, freqdist, gamma, bins=None):
        """
        Use the Lidstone estimate to create a probability distribution
        for the experiment used to generate ``freqdist``.

        :type freqdist: FreqDist
        :param freqdist: The frequency distribution that the
            probability estimates should be based on.
        :type gamma: float
        :param gamma: A real number used to parameterize the
            estimate.  The Lidstone estimate is equivalent to adding
            *gamma* to the count for each bin, and taking the
            maximum likelihood estimate of the resulting frequency
            distribution.
        :type bins: int
        :param bins: The number of sample values that can be generated
            by the experiment that is described by the probability
            distribution.  This value must be correctly set for the
            probabilities of the sample values to sum to one.  If
            ``bins`` is not specified, it defaults to ``freqdist.B()``.
        """
        if (bins == 0) or (bins is None and freqdist.N() == 0):
            name = self.__class__.__name__[:-8]
            raise ValueError(
                "A %s probability distribution " % name + "must have at least one bin."
            )
        if (bins is not None) and (bins < freqdist.B()):
            name = self.__class__.__name__[:-8]
            raise ValueError(
                "\nThe number of bins in a %s distribution " % name
                + "(%d) must be greater than or equal to\n" % bins
                + "the number of bins in the FreqDist used "
                + "to create it (%d)." % freqdist.B()
            )

        self._freqdist = freqdist
        self._gamma = float(gamma)
        self._N = self._freqdist.N()

        if bins is None:
            bins = freqdist.B()
        self._bins = bins

        self._divisor = self._N + bins * gamma
        if self._divisor == 0.0:
            # In extreme cases we force the probability to be 0,
            # which it will be, since the count will be 0:
            self._gamma = 0
            self._divisor = 1

    def freqdist(self):
        """
        Return the frequency distribution that this probability
        distribution is based on.

        :rtype: FreqDist
        """
        return self._freqdist

    def prob(self, sample):
        c = self._freqdist[sample]
        return (c + self._gamma) / self._divisor

    def max(self):
        # For Lidstone distributions, probability is monotonic with
        # frequency, so the most probable sample is the one that
        # occurs most frequently.
        return self._freqdist.max()

    def samples(self):
        return self._freqdist.keys()

    def discount(self):
        gb = self._gamma * self._bins
        return gb / (self._N + gb)

    def __repr__(self):
        """
        Return a string representation of this ``ProbDist``.

        :rtype: str
        """
        return "<LidstoneProbDist based on %d samples>" % self._freqdist.N()


class LaplaceProbDist(LidstoneProbDist):
    """
    The Laplace estimate for the probability distribution of the
    experiment used to generate a frequency distribution.  The
    "Laplace estimate" approximates the probability of a sample with
    count *c* from an experiment with *N* outcomes and *B* bins as
    *(c+1)/(N+B)*.  This is equivalent to adding one to the count for
    each bin, and taking the maximum likelihood estimate of the
    resulting frequency distribution.
    """

    def __init__(self, freqdist, bins=None):
        """
        Use the Laplace estimate to create a probability distribution
        for the experiment used to generate ``freqdist``.

        :type freqdist: FreqDist
        :param freqdist: The frequency distribution that the
            probability estimates should be based on.
        :type bins: int
        :param bins: The number of sample values that can be generated
            by the experiment that is described by the probability
            distribution.  This value must be correctly set for the
            probabilities of the sample values to sum to one.  If
            ``bins`` is not specified, it defaults to ``freqdist.B()``.
        """
        LidstoneProbDist.__init__(self, freqdist, 1, bins)

    def __repr__(self):
        """
        :rtype: str
        :return: A string representation of this ``ProbDist``.
        """
        return "<LaplaceProbDist based on %d samples>" % self._freqdist.N()


class ELEProbDist(LidstoneProbDist):
    """
    The expected likelihood estimate for the probability distribution
    of the experiment used to generate a frequency distribution.  The
    "expected likelihood estimate" approximates the probability of a
    sample with count *c* from an experiment with *N* outcomes and
    *B* bins as *(c+0.5)/(N+B/2)*.  This is equivalent to adding 0.5
    to the count for each bin, and taking the maximum likelihood
    estimate of the resulting frequency distribution.
    """

    def __init__(self, freqdist, bins=None):
        """
        Use the expected likelihood estimate to create a probability
        distribution for the experiment used to generate ``freqdist``.

        :type freqdist: FreqDist
        :param freqdist: The frequency distribution that the
            probability estimates should be based on.
        :type bins: int
        :param bins: The number of sample values that can be generated
            by the experiment that is described by the probability
            distribution.  This value must be correctly set for the
            probabilities of the sample values to sum to one.  If
            ``bins`` is not specified, it defaults to ``freqdist.B()``.
        """
        LidstoneProbDist.__init__(self, freqdist, 0.5, bins)

    def __repr__(self):
        """
        Return a string representation of this ``ProbDist``.

        :rtype: str
        """
        return "<ELEProbDist based on %d samples>" % self._freqdist.N()


class HeldoutProbDist(ProbDistI):
    """
    The heldout estimate for the probability distribution of the
    experiment used to generate two frequency distributions.  These
    two frequency distributions are called the "heldout frequency
    distribution" and the "base frequency distribution."  The
    "heldout estimate" uses uses the "heldout frequency
    distribution" to predict the probability of each sample, given its
    frequency in the "base frequency distribution".

    In particular, the heldout estimate approximates the probability
    for a sample that occurs *r* times in the base distribution as
    the average frequency in the heldout distribution of all samples
    that occur *r* times in the base distribution.

    This average frequency is *Tr[r]/(Nr[r].N)*, where:

    - *Tr[r]* is the total count in the heldout distribution for
      all samples that occur *r* times in the base distribution.
    - *Nr[r]* is the number of samples that occur *r* times in
      the base distribution.
    - *N* is the number of outcomes recorded by the heldout
      frequency distribution.

    In order to increase the efficiency of the ``prob`` member
    function, *Tr[r]/(Nr[r].N)* is precomputed for each value of *r*
    when the ``HeldoutProbDist`` is created.

    :type _estimate: list(float)
    :ivar _estimate: A list mapping from *r*, the number of
        times that a sample occurs in the base distribution, to the
        probability estimate for that sample.  ``_estimate[r]`` is
        calculated by finding the average frequency in the heldout
        distribution of all samples that occur *r* times in the base
        distribution.  In particular, ``_estimate[r]`` =
        *Tr[r]/(Nr[r].N)*.
    :type _max_r: int
    :ivar _max_r: The maximum number of times that any sample occurs
        in the base distribution.  ``_max_r`` is used to decide how
        large ``_estimate`` must be.
    """

    SUM_TO_ONE = False

    def __init__(self, base_fdist, heldout_fdist, bins=None):
        """
        Use the heldout estimate to create a probability distribution
        for the experiment used to generate ``base_fdist`` and
        ``heldout_fdist``.

        :type base_fdist: FreqDist
        :param base_fdist: The base frequency distribution.
        :type heldout_fdist: FreqDist
        :param heldout_fdist: The heldout frequency distribution.
        :type bins: int
        :param bins: The number of sample values that can be generated
            by the experiment that is described by the probability
            distribution.  This value must be correctly set for the
            probabilities of the sample values to sum to one.  If
            ``bins`` is not specified, it defaults to ``freqdist.B()``.
        """

        self._base_fdist = base_fdist
        self._heldout_fdist = heldout_fdist

        # The max number of times any sample occurs in base_fdist.
        self._max_r = base_fdist[base_fdist.max()]

        # Calculate Tr, Nr, and N.
        Tr = self._calculate_Tr()
        r_Nr = base_fdist.r_Nr(bins)
        Nr = [r_Nr[r] for r in range(self._max_r + 1)]
        N = heldout_fdist.N()

        # Use Tr, Nr, and N to compute the probability estimate for
        # each value of r.
        self._estimate = self._calculate_estimate(Tr, Nr, N)

    def _calculate_Tr(self):
        """
        Return the list *Tr*, where *Tr[r]* is the total count in
        ``heldout_fdist`` for all samples that occur *r*
        times in ``base_fdist``.

        :rtype: list(float)
        """
        Tr = [0.0] * (self._max_r + 1)
        for sample in self._heldout_fdist:
            r = self._base_fdist[sample]
            Tr[r] += self._heldout_fdist[sample]
        return Tr

    def _calculate_estimate(self, Tr, Nr, N):
        """
        Return the list *estimate*, where *estimate[r]* is the probability
        estimate for any sample that occurs *r* times in the base frequency
        distribution.  In particular, *estimate[r]* is *Tr[r]/(N[r].N)*.
        In the special case that *N[r]=0*, *estimate[r]* will never be used;
        so we define *estimate[r]=None* for those cases.

        :rtype: list(float)
        :type Tr: list(float)
        :param Tr: the list *Tr*, where *Tr[r]* is the total count in
            the heldout distribution for all samples that occur *r*
            times in base distribution.
        :type Nr: list(float)
        :param Nr: The list *Nr*, where *Nr[r]* is the number of
            samples that occur *r* times in the base distribution.
        :type N: int
        :param N: The total number of outcomes recorded by the heldout
            frequency distribution.
        """
        estimate = []
        for r in range(self._max_r + 1):
            if Nr[r] == 0:
                estimate.append(None)
            else:
                estimate.append(Tr[r] / (Nr[r] * N))
        return estimate

    def base_fdist(self):
        """
        Return the base frequency distribution that this probability
        distribution is based on.

        :rtype: FreqDist
        """
        return self._base_fdist

    def heldout_fdist(self):
        """
        Return the heldout frequency distribution that this
        probability distribution is based on.

        :rtype: FreqDist
        """
        return self._heldout_fdist

    def samples(self):
        return self._base_fdist.keys()

    def prob(self, sample):
        # Use our precomputed probability estimate.
        r = self._base_fdist[sample]
        return self._estimate[r]

    def max(self):
        # Note: the Heldout estimation is *not* necessarily monotonic;
        # so this implementation is currently broken.  However, it
        # should give the right answer *most* of the time. :)
        return self._base_fdist.max()

    def discount(self):
        raise NotImplementedError()

    def __repr__(self):
        """
        :rtype: str
        :return: A string representation of this ``ProbDist``.
        """
        s = "<HeldoutProbDist: %d base samples; %d heldout samples>"
        return s % (self._base_fdist.N(), self._heldout_fdist.N())


class CrossValidationProbDist(ProbDistI):
    """
    The cross-validation estimate for the probability distribution of
    the experiment used to generate a set of frequency distribution.
    The "cross-validation estimate" for the probability of a sample
    is found by averaging the held-out estimates for the sample in
    each pair of frequency distributions.
    """

    SUM_TO_ONE = False

    def __init__(self, freqdists, bins):
        """
        Use the cross-validation estimate to create a probability
        distribution for the experiment used to generate
        ``freqdists``.

        :type freqdists: list(FreqDist)
        :param freqdists: A list of the frequency distributions
            generated by the experiment.
        :type bins: int
        :param bins: The number of sample values that can be generated
            by the experiment that is described by the probability
            distribution.  This value must be correctly set for the
            probabilities of the sample values to sum to one.  If
            ``bins`` is not specified, it defaults to ``freqdist.B()``.
        """
        self._freqdists = freqdists

        # Create a heldout probability distribution for each pair of
        # frequency distributions in freqdists.
        self._heldout_probdists = []
        for fdist1 in freqdists:
            for fdist2 in freqdists:
                if fdist1 is not fdist2:
                    probdist = HeldoutProbDist(fdist1, fdist2, bins)
                    self._heldout_probdists.append(probdist)

    def freqdists(self):
        """
        Return the list of frequency distributions that this ``ProbDist`` is based on.

        :rtype: list(FreqDist)
        """
        return self._freqdists

    def samples(self):
        # [xx] nb: this is not too efficient
        return set(sum((list(fd) for fd in self._freqdists), []))

    def prob(self, sample):
        # Find the average probability estimate returned by each
        # heldout distribution.
        prob = 0.0
        for heldout_probdist in self._heldout_probdists:
            prob += heldout_probdist.prob(sample)
        return prob / len(self._heldout_probdists)

    def discount(self):
        raise NotImplementedError()

    def __repr__(self):
        """
        Return a string representation of this ``ProbDist``.

        :rtype: str
        """
        return "<CrossValidationProbDist: %d-way>" % len(self._freqdists)


class WittenBellProbDist(ProbDistI):
    """
    The Witten-Bell estimate of a probability distribution. This distribution
    allocates uniform probability mass to as yet unseen events by using the
    number of events that have only been seen once. The probability mass
    reserved for unseen events is equal to *T / (N + T)*
    where *T* is the number of observed event types and *N* is the total
    number of observed events. This equates to the maximum likelihood estimate
    of a new type event occurring. The remaining probability mass is discounted
    such that all probability estimates sum to one, yielding:

        - *p = T / Z (N + T)*, if count = 0
        - *p = c / (N + T)*, otherwise
    """

    def __init__(self, freqdist, bins=None):
        """
        Creates a distribution of Witten-Bell probability estimates.  This
        distribution allocates uniform probability mass to as yet unseen
        events by using the number of events that have only been seen once. The
        probability mass reserved for unseen events is equal to *T / (N + T)*
        where *T* is the number of observed event types and *N* is the total
        number of observed events. This equates to the maximum likelihood
        estimate of a new type event occurring. The remaining probability mass
        is discounted such that all probability estimates sum to one,
        yielding:

            - *p = T / Z (N + T)*, if count = 0
            - *p = c / (N + T)*, otherwise

        The parameters *T* and *N* are taken from the ``freqdist`` parameter
        (the ``B()`` and ``N()`` values). The normalizing factor *Z* is
        calculated using these values along with the ``bins`` parameter.

        :param freqdist: The frequency counts upon which to base the
            estimation.
        :type freqdist: FreqDist
        :param bins: The number of possible event types. This must be at least
            as large as the number of bins in the ``freqdist``. If None, then
            it's assumed to be equal to that of the ``freqdist``
        :type bins: int
        """
        assert bins is None or bins >= freqdist.B(), (
            "bins parameter must not be less than %d=freqdist.B()" % freqdist.B()
        )
        if bins is None:
            bins = freqdist.B()
        self._freqdist = freqdist
        self._T = self._freqdist.B()
        self._Z = bins - self._freqdist.B()
        self._N = self._freqdist.N()
        # self._P0 is P(0), precalculated for efficiency:
        if self._N == 0:
            # if freqdist is empty, we approximate P(0) by a UniformProbDist:
            self._P0 = 1.0 / self._Z
        else:
            self._P0 = self._T / (self._Z * (self._N + self._T))

    def prob(self, sample):
        # inherit docs from ProbDistI
        c = self._freqdist[sample]
        return c / (self._N + self._T) if c != 0 else self._P0

    def max(self):
        return self._freqdist.max()

    def samples(self):
        return self._freqdist.keys()

    def freqdist(self):
        return self._freqdist

    def discount(self):
        raise NotImplementedError()

    def __repr__(self):
        """
        Return a string representation of this ``ProbDist``.

        :rtype: str
        """
        return "<WittenBellProbDist based on %d samples>" % self._freqdist.N()


##//////////////////////////////////////////////////////
##  Good-Turing Probability Distributions
##//////////////////////////////////////////////////////

# Good-Turing frequency estimation was contributed by Alan Turing and
# his statistical assistant I.J. Good, during their collaboration in
# the WWII.  It is a statistical technique for predicting the
# probability of occurrence of objects belonging to an unknown number
# of species, given past observations of such objects and their
# species. (In drawing balls from an urn, the 'objects' would be balls
# and the 'species' would be the distinct colors of the balls (finite
# but unknown in number).
#
# Good-Turing method calculates the probability mass to assign to
# events with zero or low counts based on the number of events with
# higher counts. It does so by using the adjusted count *c\**:
#
#     - *c\* = (c + 1) N(c + 1) / N(c)*   for c >= 1
#     - *things with frequency zero in training* = N(1)  for c == 0
#
# where *c* is the original count, *N(i)* is the number of event types
# observed with count *i*. We can think the count of unseen as the count
# of frequency one (see Jurafsky & Martin 2nd Edition, p101).
#
# This method is problematic because the situation ``N(c+1) == 0``
# is quite common in the original Good-Turing estimation; smoothing or
# interpolation of *N(i)* values is essential in practice.
#
# Bill Gale and Geoffrey Sampson present a simple and effective approach,
# Simple Good-Turing.  As a smoothing curve they simply use a power curve:
#
#     Nr = a*r^b (with b < -1 to give the appropriate hyperbolic
#     relationship)
#
# They estimate a and b by simple linear regression technique on the
# logarithmic form of the equation:
#
#     log Nr = a + b*log(r)
#
# However, they suggest that such a simple curve is probably only
# appropriate for high values of r. For low values of r, they use the
# measured Nr directly.  (see M&S, p.213)
#
# Gale and Sampson propose to use r while the difference between r and
# r* is 1.96 greater than the standard deviation, and switch to r* if
# it is less or equal:
#
#     |r - r*| > 1.96 * sqrt((r + 1)^2 (Nr+1 / Nr^2) (1 + Nr+1 / Nr))
#
# The 1.96 coefficient correspond to a 0.05 significance criterion,
# some implementations can use a coefficient of 1.65 for a 0.1
# significance criterion.
#

##//////////////////////////////////////////////////////
##  Simple Good-Turing Probablity Distributions
##//////////////////////////////////////////////////////


class SimpleGoodTuringProbDist(ProbDistI):
    """
    SimpleGoodTuring ProbDist approximates from frequency to frequency of
    frequency into a linear line under log space by linear regression.
    Details of Simple Good-Turing algorithm can be found in:

    - Good Turing smoothing without tears" (Gale & Sampson 1995),
      Journal of Quantitative Linguistics, vol. 2 pp. 217-237.
    - "Speech and Language Processing (Jurafsky & Martin),
      2nd Edition, Chapter 4.5 p103 (log(Nc) =  a + b*log(c))
    - https://www.grsampson.net/RGoodTur.html

    Given a set of pair (xi, yi),  where the xi denotes the frequency and
    yi denotes the frequency of frequency, we want to minimize their
    square variation. E(x) and E(y) represent the mean of xi and yi.

    - slope: b = sigma ((xi-E(x)(yi-E(y))) / sigma ((xi-E(x))(xi-E(x)))
    - intercept: a = E(y) - b.E(x)
    """

    SUM_TO_ONE = False

    def __init__(self, freqdist, bins=None):
        """
        :param freqdist: The frequency counts upon which to base the
            estimation.
        :type freqdist: FreqDist
        :param bins: The number of possible event types. This must be
            larger than the number of bins in the ``freqdist``. If None,
            then it's assumed to be equal to ``freqdist``.B() + 1
        :type bins: int
        """
        assert (
            bins is None or bins > freqdist.B()
        ), "bins parameter must not be less than %d=freqdist.B()+1" % (freqdist.B() + 1)
        if bins is None:
            bins = freqdist.B() + 1
        self._freqdist = freqdist
        self._bins = bins
        r, nr = self._r_Nr()
        self.find_best_fit(r, nr)
        self._switch(r, nr)
        self._renormalize(r, nr)

    def _r_Nr_non_zero(self):
        r_Nr = self._freqdist.r_Nr()
        del r_Nr[0]
        return r_Nr

    def _r_Nr(self):
        """
        Split the frequency distribution in two list (r, Nr), where Nr(r) > 0
        """
        nonzero = self._r_Nr_non_zero()

        if not nonzero:
            return [], []
        return zip(*sorted(nonzero.items()))

    def find_best_fit(self, r, nr):
        """
        Use simple linear regression to tune parameters self._slope and
        self._intercept in the log-log space based on count and Nr(count)
        (Work in log space to avoid floating point underflow.)
        """
        # For higher sample frequencies the data points becomes horizontal
        # along line Nr=1. To create a more evident linear model in log-log
        # space, we average positive Nr values with the surrounding zero
        # values. (Church and Gale, 1991)

        if not r or not nr:
            # Empty r or nr?
            return

        zr = []
        for j in range(len(r)):
            i = r[j - 1] if j > 0 else 0
            k = 2 * r[j] - i if j == len(r) - 1 else r[j + 1]
            zr_ = 2.0 * nr[j] / (k - i)
            zr.append(zr_)

        log_r = [math.log(i) for i in r]
        log_zr = [math.log(i) for i in zr]

        xy_cov = x_var = 0.0
        x_mean = sum(log_r) / len(log_r)
        y_mean = sum(log_zr) / len(log_zr)
        for x, y in zip(log_r, log_zr):
            xy_cov += (x - x_mean) * (y - y_mean)
            x_var += (x - x_mean) ** 2
        self._slope = xy_cov / x_var if x_var != 0 else 0.0
        if self._slope >= -1:
            warnings.warn(
                "SimpleGoodTuring did not find a proper best fit "
                "line for smoothing probabilities of occurrences. "
                "The probability estimates are likely to be "
                "unreliable."
            )
        self._intercept = y_mean - self._slope * x_mean

    def _switch(self, r, nr):
        """
        Calculate the r frontier where we must switch from Nr to Sr
        when estimating E[Nr].
        """
        for i, r_ in enumerate(r):
            if len(r) == i + 1 or r[i + 1] != r_ + 1:
                # We are at the end of r, or there is a gap in r
                self._switch_at = r_
                break

            Sr = self.smoothedNr
            smooth_r_star = (r_ + 1) * Sr(r_ + 1) / Sr(r_)
            unsmooth_r_star = (r_ + 1) * nr[i + 1] / nr[i]

            std = math.sqrt(self._variance(r_, nr[i], nr[i + 1]))
            if abs(unsmooth_r_star - smooth_r_star) <= 1.96 * std:
                self._switch_at = r_
                break

    def _variance(self, r, nr, nr_1):
        r = float(r)
        nr = float(nr)
        nr_1 = float(nr_1)
        return (r + 1.0) ** 2 * (nr_1 / nr**2) * (1.0 + nr_1 / nr)

    def _renormalize(self, r, nr):
        """
        It is necessary to renormalize all the probability estimates to
        ensure a proper probability distribution results. This can be done
        by keeping the estimate of the probability mass for unseen items as
        N(1)/N and renormalizing all the estimates for previously seen items
        (as Gale and Sampson (1995) propose). (See M&S P.213, 1999)
        """
        prob_cov = 0.0
        for r_, nr_ in zip(r, nr):
            prob_cov += nr_ * self._prob_measure(r_)
        if prob_cov:
            self._renormal = (1 - self._prob_measure(0)) / prob_cov

    def smoothedNr(self, r):
        """
        Return the number of samples with count r.

        :param r: The amount of frequency.
        :type r: int
        :rtype: float
        """

        # Nr = a*r^b (with b < -1 to give the appropriate hyperbolic
        # relationship)
        # Estimate a and b by simple linear regression technique on
        # the logarithmic form of the equation: log Nr = a + b*log(r)

        return math.exp(self._intercept + self._slope * math.log(r))

    def prob(self, sample):
        """
        Return the sample's probability.

        :param sample: sample of the event
        :type sample: str
        :rtype: float
        """
        count = self._freqdist[sample]
        p = self._prob_measure(count)
        if count == 0:
            if self._bins == self._freqdist.B():
                p = 0.0
            else:
                p = p / (self._bins - self._freqdist.B())
        else:
            p = p * self._renormal
        return p

    def _prob_measure(self, count):
        if count == 0 and self._freqdist.N() == 0:
            return 1.0
        elif count == 0 and self._freqdist.N() != 0:
            return self._freqdist.Nr(1) / self._freqdist.N()

        if self._switch_at > count:
            Er_1 = self._freqdist.Nr(count + 1)
            Er = self._freqdist.Nr(count)
        else:
            Er_1 = self.smoothedNr(count + 1)
            Er = self.smoothedNr(count)

        r_star = (count + 1) * Er_1 / Er
        return r_star / self._freqdist.N()

    def check(self):
        prob_sum = 0.0
        for i in range(0, len(self._Nr)):
            prob_sum += self._Nr[i] * self._prob_measure(i) / self._renormal
        print("Probability Sum:", prob_sum)
        # assert prob_sum != 1.0, "probability sum should be one!"

    def discount(self):
        """
        This function returns the total mass of probability transfers from the
        seen samples to the unseen samples.
        """
        return self.smoothedNr(1) / self._freqdist.N()

    def max(self):
        return self._freqdist.max()

    def samples(self):
        return self._freqdist.keys()

    def freqdist(self):
        return self._freqdist

    def __repr__(self):
        """
        Return a string representation of this ``ProbDist``.

        :rtype: str
        """
        return "<SimpleGoodTuringProbDist based on %d samples>" % self._freqdist.N()


class MutableProbDist(ProbDistI):
    """
    An mutable probdist where the probabilities may be easily modified. This
    simply copies an existing probdist, storing the probability values in a
    mutable dictionary and providing an update method.
    """

    def __init__(self, prob_dist, samples, store_logs=True):
        """
        Creates the mutable probdist based on the given prob_dist and using
        the list of samples given. These values are stored as log
        probabilities if the store_logs flag is set.

        :param prob_dist: the distribution from which to garner the
            probabilities
        :type prob_dist: ProbDist
        :param samples: the complete set of samples
        :type samples: sequence of any
        :param store_logs: whether to store the probabilities as logarithms
        :type store_logs: bool
        """
        self._samples = samples
        self._sample_dict = {samples[i]: i for i in range(len(samples))}
        self._data = array.array("d", [0.0]) * len(samples)
        for i in range(len(samples)):
            if store_logs:
                self._data[i] = prob_dist.logprob(samples[i])
            else:
                self._data[i] = prob_dist.prob(samples[i])
        self._logs = store_logs

    def max(self):
        # inherit documentation
        return max((p, v) for (v, p) in self._sample_dict.items())[1]

    def samples(self):
        # inherit documentation
        return self._samples

    def prob(self, sample):
        # inherit documentation
        i = self._sample_dict.get(sample)
        if i is None:
            return 0.0
        return 2 ** (self._data[i]) if self._logs else self._data[i]

    def logprob(self, sample):
        # inherit documentation
        i = self._sample_dict.get(sample)
        if i is None:
            return float("-inf")
        return self._data[i] if self._logs else math.log(self._data[i], 2)

    def update(self, sample, prob, log=True):
        """
        Update the probability for the given sample. This may cause the object
        to stop being the valid probability distribution - the user must
        ensure that they update the sample probabilities such that all samples
        have probabilities between 0 and 1 and that all probabilities sum to
        one.

        :param sample: the sample for which to update the probability
        :type sample: any
        :param prob: the new probability
        :type prob: float
        :param log: is the probability already logged
        :type log: bool
        """
        i = self._sample_dict.get(sample)
        assert i is not None
        if self._logs:
            self._data[i] = prob if log else math.log(prob, 2)
        else:
            self._data[i] = 2 ** (prob) if log else prob


##/////////////////////////////////////////////////////
##  Kneser-Ney Probability Distribution
##//////////////////////////////////////////////////////

# This method for calculating probabilities was introduced in 1995 by Reinhard
# Kneser and Hermann Ney. It was meant to improve the accuracy of language
# models that use backing-off to deal with sparse data. The authors propose two
# ways of doing so: a marginal distribution constraint on the back-off
# distribution and a leave-one-out distribution. For a start, the first one is
# implemented as a class below.
#
# The idea behind a back-off n-gram model is that we have a series of
# frequency distributions for our n-grams so that in case we have not seen a
# given n-gram during training (and as a result have a 0 probability for it) we
# can 'back off' (hence the name!) and try testing whether we've seen the
# n-1-gram part of the n-gram in training.
#
# The novelty of Kneser and Ney's approach was that they decided to fiddle
# around with the way this latter, backed off probability was being calculated
# whereas their peers seemed to focus on the primary probability.
#
# The implementation below uses one of the techniques described in their paper
# titled "Improved backing-off for n-gram language modeling." In the same paper
# another technique is introduced to attempt to smooth the back-off
# distribution as well as the primary one. There is also a much-cited
# modification of this method proposed by Chen and Goodman.
#
# In order for the implementation of Kneser-Ney to be more efficient, some
# changes have been made to the original algorithm. Namely, the calculation of
# the normalizing function gamma has been significantly simplified and
# combined slightly differently with beta. None of these changes affect the
# nature of the algorithm, but instead aim to cut out unnecessary calculations
# and take advantage of storing and retrieving information in dictionaries
# where possible.


class KneserNeyProbDist(ProbDistI):
    """
    Kneser-Ney estimate of a probability distribution. This is a version of
    back-off that counts how likely an n-gram is provided the n-1-gram had
    been seen in training. Extends the ProbDistI interface, requires a trigram
    FreqDist instance to train on. Optionally, a different from default discount
    value can be specified. The default discount is set to 0.75.

    """

    def __init__(self, freqdist, bins=None, discount=0.75):
        """
        :param freqdist: The trigram frequency distribution upon which to base
            the estimation
        :type freqdist: FreqDist
        :param bins: Included for compatibility with nltk.tag.hmm
        :type bins: int or float
        :param discount: The discount applied when retrieving counts of
            trigrams
        :type discount: float (preferred, but can be set to int)
        """

        if not bins:
            self._bins = freqdist.B()
        else:
            self._bins = bins
        self._D = discount

        # cache for probability calculation
        self._cache = {}

        # internal bigram and trigram frequency distributions
        self._bigrams = defaultdict(int)
        self._trigrams = freqdist

        # helper dictionaries used to calculate probabilities
        self._wordtypes_after = defaultdict(float)
        self._trigrams_contain = defaultdict(float)
        self._wordtypes_before = defaultdict(float)
        for w0, w1, w2 in freqdist:
            self._bigrams[(w0, w1)] += freqdist[(w0, w1, w2)]
            self._wordtypes_after[(w0, w1)] += 1
            self._trigrams_contain[w1] += 1
            self._wordtypes_before[(w1, w2)] += 1

    def prob(self, trigram):
        # sample must be a triple
        if len(trigram) != 3:
            raise ValueError("Expected an iterable with 3 members.")
        trigram = tuple(trigram)
        w0, w1, w2 = trigram

        if trigram in self._cache:
            return self._cache[trigram]
        else:
            # if the sample trigram was seen during training
            if trigram in self._trigrams:
                prob = (self._trigrams[trigram] - self.discount()) / self._bigrams[
                    (w0, w1)
                ]

            # else if the 'rougher' environment was seen during training
            elif (w0, w1) in self._bigrams and (w1, w2) in self._wordtypes_before:
                aftr = self._wordtypes_after[(w0, w1)]
                bfr = self._wordtypes_before[(w1, w2)]

                # the probability left over from alphas
                leftover_prob = (aftr * self.discount()) / self._bigrams[(w0, w1)]

                # the beta (including normalization)
                beta = bfr / (self._trigrams_contain[w1] - aftr)

                prob = leftover_prob * beta

            # else the sample was completely unseen during training
            else:
                prob = 0.0

            self._cache[trigram] = prob
            return prob

    def discount(self):
        """
        Return the value by which counts are discounted. By default set to 0.75.

        :rtype: float
        """
        return self._D

    def set_discount(self, discount):
        """
        Set the value by which counts are discounted to the value of discount.

        :param discount: the new value to discount counts by
        :type discount: float (preferred, but int possible)
        :rtype: None
        """
        self._D = discount

    def samples(self):
        return self._trigrams.keys()

    def max(self):
        return self._trigrams.max()

    def __repr__(self):
        """
        Return a string representation of this ProbDist

        :rtype: str
        """
        return f"<KneserNeyProbDist based on {self._trigrams.N()} trigrams"


##//////////////////////////////////////////////////////
##  Probability Distribution Operations
##//////////////////////////////////////////////////////


def log_likelihood(test_pdist, actual_pdist):
    if not isinstance(test_pdist, ProbDistI) or not isinstance(actual_pdist, ProbDistI):
        raise ValueError("expected a ProbDist.")
    # Is this right?
    return sum(
        actual_pdist.prob(s) * math.log(test_pdist.prob(s), 2) for s in actual_pdist
    )


def entropy(pdist):
    probs = (pdist.prob(s) for s in pdist.samples())
    return -sum(p * math.log(p, 2) for p in probs)


##//////////////////////////////////////////////////////
##  Conditional Distributions
##//////////////////////////////////////////////////////


class ConditionalFreqDist(defaultdict):
    """
    A collection of frequency distributions for a single experiment
    run under different conditions.  Conditional frequency
    distributions are used to record the number of times each sample
    occurred, given the condition under which the experiment was run.
    For example, a conditional frequency distribution could be used to
    record the frequency of each word (type) in a document, given its
    length.  Formally, a conditional frequency distribution can be
    defined as a function that maps from each condition to the
    FreqDist for the experiment under that condition.

    Conditional frequency distributions are typically constructed by
    repeatedly running an experiment under a variety of conditions,
    and incrementing the sample outcome counts for the appropriate
    conditions.  For example, the following code will produce a
    conditional frequency distribution that encodes how often each
    word type occurs, given the length of that word type:

        >>> from nltk.probability import ConditionalFreqDist
        >>> from nltk.tokenize import word_tokenize
        >>> sent = "the the the dog dog some other words that we do not care about"
        >>> cfdist = ConditionalFreqDist()
        >>> for word in word_tokenize(sent):
        ...     condition = len(word)
        ...     cfdist[condition][word] += 1

    An equivalent way to do this is with the initializer:

        >>> cfdist = ConditionalFreqDist((len(word), word) for word in word_tokenize(sent))

    The frequency distribution for each condition is accessed using
    the indexing operator:

        >>> cfdist[3]
        FreqDist({'the': 3, 'dog': 2, 'not': 1})
        >>> cfdist[3].freq('the')
        0.5
        >>> cfdist[3]['dog']
        2

    When the indexing operator is used to access the frequency
    distribution for a condition that has not been accessed before,
    ``ConditionalFreqDist`` creates a new empty FreqDist for that
    condition.

    """

    def __init__(self, cond_samples=None):
        """
        Construct a new empty conditional frequency distribution.  In
        particular, the count for every sample, under every condition,
        is zero.

        :param cond_samples: The samples to initialize the conditional
            frequency distribution with
        :type cond_samples: Sequence of (condition, sample) tuples
        """
        defaultdict.__init__(self, FreqDist)

        if cond_samples:
            for cond, sample in cond_samples:
                self[cond][sample] += 1

    def __reduce__(self):
        kv_pairs = ((cond, self[cond]) for cond in self.conditions())
        return (self.__class__, (), None, None, kv_pairs)

    def conditions(self):
        """
        Return a list of the conditions that have been accessed for
        this ``ConditionalFreqDist``.  Use the indexing operator to
        access the frequency distribution for a given condition.
        Note that the frequency distributions for some conditions
        may contain zero sample outcomes.

        :rtype: list
        """
        return list(self.keys())

    def N(self):
        """
        Return the total number of sample outcomes that have been
        recorded by this ``ConditionalFreqDist``.

        :rtype: int
        """
        return sum(fdist.N() for fdist in self.values())

    def plot(
        self,
        *args,
        samples=None,
        title="",
        cumulative=False,
        percents=False,
        conditions=None,
        show=False,
        **kwargs,
    ):
        """
        Plot the given samples from the conditional frequency distribution.
        For a cumulative plot, specify cumulative=True. Additional ``*args`` and
        ``**kwargs`` are passed to matplotlib's plot function.
        (Requires Matplotlib to be installed.)

        :param samples: The samples to plot
        :type samples: list
        :param title: The title for the graph
        :type title: str
        :param cumulative: Whether the plot is cumulative. (default = False)
        :type cumulative: bool
        :param percents: Whether the plot uses percents instead of counts. (default = False)
        :type percents: bool
        :param conditions: The conditions to plot (default is all)
        :type conditions: list
        :param show: Whether to show the plot, or only return the ax.
        :type show: bool
        """
        try:
            import matplotlib.pyplot as plt  # import statement fix
        except ImportError as e:
            raise ValueError(
                "The plot function requires matplotlib to be installed."
                "See https://matplotlib.org/"
            ) from e

        if not conditions:
            conditions = self.conditions()
        else:
            conditions = [c for c in conditions if c in self]
        if not samples:
            samples = sorted({v for c in conditions for v in self[c]})
        if "linewidth" not in kwargs:
            kwargs["linewidth"] = 2
        ax = plt.gca()
        if conditions:
            freqs = []
            for condition in conditions:
                if cumulative:
                    # freqs should be a list of list where each sub list will be a frequency of a condition
                    freq = list(self[condition]._cumulative_frequencies(samples))
                else:
                    freq = [self[condition][sample] for sample in samples]

                if percents:
                    freq = [f / self[condition].N() * 100 for f in freq]

                freqs.append(freq)

            if cumulative:
                ylabel = "Cumulative "
                legend_loc = "lower right"
            else:
                ylabel = ""
                legend_loc = "upper right"

            if percents:
                ylabel += "Percents"
            else:
                ylabel += "Counts"

            i = 0
            for freq in freqs:
                kwargs["label"] = conditions[i]  # label for each condition
                i += 1
                ax.plot(freq, *args, **kwargs)
            ax.legend(loc=legend_loc)
            ax.grid(True, color="silver")
            ax.set_xticks(range(len(samples)))
            ax.set_xticklabels([str(s) for s in samples], rotation=90)
            if title:
                ax.set_title(title)
            ax.set_xlabel("Samples")
            ax.set_ylabel(ylabel)

        if show:
            plt.show()

        return ax

    def tabulate(self, *args, **kwargs):
        """
        Tabulate the given samples from the conditional frequency distribution.

        :param samples: The samples to plot
        :type samples: list
        :param conditions: The conditions to plot (default is all)
        :type conditions: list
        :param cumulative: A flag to specify whether the freqs are cumulative (default = False)
        :type title: bool
        """

        cumulative = _get_kwarg(kwargs, "cumulative", False)
        conditions = _get_kwarg(kwargs, "conditions", sorted(self.conditions()))
        samples = _get_kwarg(
            kwargs,
            "samples",
            sorted({v for c in conditions if c in self for v in self[c]}),
        )  # this computation could be wasted

        width = max(len("%s" % s) for s in samples)
        freqs = dict()
        for c in conditions:
            if cumulative:
                freqs[c] = list(self[c]._cumulative_frequencies(samples))
            else:
                freqs[c] = [self[c][sample] for sample in samples]
            width = max(width, max(len("%d" % f) for f in freqs[c]))

        condition_size = max(len("%s" % c) for c in conditions)
        print(" " * condition_size, end=" ")
        for s in samples:
            print("%*s" % (width, s), end=" ")
        print()
        for c in conditions:
            print("%*s" % (condition_size, c), end=" ")
            for f in freqs[c]:
                print("%*d" % (width, f), end=" ")
            print()

    # Mathematical operators

    def __add__(self, other):
        """
        Add counts from two ConditionalFreqDists.
        """
        if not isinstance(other, ConditionalFreqDist):
            return NotImplemented
        result = self.copy()
        for cond in other.conditions():
            result[cond] += other[cond]
        return result

    def __sub__(self, other):
        """
        Subtract count, but keep only results with positive counts.
        """
        if not isinstance(other, ConditionalFreqDist):
            return NotImplemented
        result = self.copy()
        for cond in other.conditions():
            result[cond] -= other[cond]
            if not result[cond]:
                del result[cond]
        return result

    def __or__(self, other):
        """
        Union is the maximum of value in either of the input counters.
        """
        if not isinstance(other, ConditionalFreqDist):
            return NotImplemented
        result = self.copy()
        for cond in other.conditions():
            result[cond] |= other[cond]
        return result

    def __and__(self, other):
        """
        Intersection is the minimum of corresponding counts.
        """
        if not isinstance(other, ConditionalFreqDist):
            return NotImplemented
        result = ConditionalFreqDist()
        for cond in self.conditions():
            newfreqdist = self[cond] & other[cond]
            if newfreqdist:
                result[cond] = newfreqdist
        return result

    # @total_ordering doesn't work here, since the class inherits from a builtin class
    def __le__(self, other):
        if not isinstance(other, ConditionalFreqDist):
            raise_unorderable_types("<=", self, other)
        return set(self.conditions()).issubset(other.conditions()) and all(
            self[c] <= other[c] for c in self.conditions()
        )

    def __lt__(self, other):
        if not isinstance(other, ConditionalFreqDist):
            raise_unorderable_types("<", self, other)
        return self <= other and self != other

    def __ge__(self, other):
        if not isinstance(other, ConditionalFreqDist):
            raise_unorderable_types(">=", self, other)
        return other <= self

    def __gt__(self, other):
        if not isinstance(other, ConditionalFreqDist):
            raise_unorderable_types(">", self, other)
        return other < self

    def deepcopy(self):
        from copy import deepcopy

        return deepcopy(self)

    copy = deepcopy

    def __repr__(self):
        """
        Return a string representation of this ``ConditionalFreqDist``.

        :rtype: str
        """
        return "<ConditionalFreqDist with %d conditions>" % len(self)


class ConditionalProbDistI(dict, metaclass=ABCMeta):
    """
    A collection of probability distributions for a single experiment
    run under different conditions.  Conditional probability
    distributions are used to estimate the likelihood of each sample,
    given the condition under which the experiment was run.  For
    example, a conditional probability distribution could be used to
    estimate the probability of each word type in a document, given
    the length of the word type.  Formally, a conditional probability
    distribution can be defined as a function that maps from each
    condition to the ``ProbDist`` for the experiment under that
    condition.
    """

    @abstractmethod
    def __init__(self):
        """
        Classes inheriting from ConditionalProbDistI should implement __init__.
        """

    def conditions(self):
        """
        Return a list of the conditions that are represented by
        this ``ConditionalProbDist``.  Use the indexing operator to
        access the probability distribution for a given condition.

        :rtype: list
        """
        return list(self.keys())

    def __repr__(self):
        """
        Return a string representation of this ``ConditionalProbDist``.

        :rtype: str
        """
        return "<%s with %d conditions>" % (type(self).__name__, len(self))


class ConditionalProbDist(ConditionalProbDistI):
    """
    A conditional probability distribution modeling the experiments
    that were used to generate a conditional frequency distribution.
    A ConditionalProbDist is constructed from a
    ``ConditionalFreqDist`` and a ``ProbDist`` factory:

    - The ``ConditionalFreqDist`` specifies the frequency
      distribution for each condition.
    - The ``ProbDist`` factory is a function that takes a
      condition's frequency distribution, and returns its
      probability distribution.  A ``ProbDist`` class's name (such as
      ``MLEProbDist`` or ``HeldoutProbDist``) can be used to specify
      that class's constructor.

    The first argument to the ``ProbDist`` factory is the frequency
    distribution that it should model; and the remaining arguments are
    specified by the ``factory_args`` parameter to the
    ``ConditionalProbDist`` constructor.  For example, the following
    code constructs a ``ConditionalProbDist``, where the probability
    distribution for each condition is an ``ELEProbDist`` with 10 bins:

        >>> from nltk.corpus import brown
        >>> from nltk.probability import ConditionalFreqDist
        >>> from nltk.probability import ConditionalProbDist, ELEProbDist
        >>> cfdist = ConditionalFreqDist(brown.tagged_words()[:5000])
        >>> cpdist = ConditionalProbDist(cfdist, ELEProbDist, 10)
        >>> cpdist['passed'].max()
        'VBD'
        >>> cpdist['passed'].prob('VBD') #doctest: +ELLIPSIS
        0.423...

    """

    def __init__(self, cfdist, probdist_factory, *factory_args, **factory_kw_args):
        """
        Construct a new conditional probability distribution, based on
        the given conditional frequency distribution and ``ProbDist``
        factory.

        :type cfdist: ConditionalFreqDist
        :param cfdist: The ``ConditionalFreqDist`` specifying the
            frequency distribution for each condition.
        :type probdist_factory: class or function
        :param probdist_factory: The function or class that maps
            a condition's frequency distribution to its probability
            distribution.  The function is called with the frequency
            distribution as its first argument,
            ``factory_args`` as its remaining arguments, and
            ``factory_kw_args`` as keyword arguments.
        :type factory_args: (any)
        :param factory_args: Extra arguments for ``probdist_factory``.
            These arguments are usually used to specify extra
            properties for the probability distributions of individual
            conditions, such as the number of bins they contain.
        :type factory_kw_args: (any)
        :param factory_kw_args: Extra keyword arguments for ``probdist_factory``.
        """
        self._probdist_factory = probdist_factory
        self._factory_args = factory_args
        self._factory_kw_args = factory_kw_args

        for condition in cfdist:
            self[condition] = probdist_factory(
                cfdist[condition], *factory_args, **factory_kw_args
            )

    def __missing__(self, key):
        self[key] = self._probdist_factory(
            FreqDist(), *self._factory_args, **self._factory_kw_args
        )
        return self[key]


class DictionaryConditionalProbDist(ConditionalProbDistI):
    """
    An alternative ConditionalProbDist that simply wraps a dictionary of
    ProbDists rather than creating these from FreqDists.
    """

    def __init__(self, probdist_dict):
        """
        :param probdist_dict: a dictionary containing the probdists indexed
            by the conditions
        :type probdist_dict: dict any -> probdist
        """
        self.update(probdist_dict)

    def __missing__(self, key):
        self[key] = DictionaryProbDist()
        return self[key]


##//////////////////////////////////////////////////////
## Adding in log-space.
##//////////////////////////////////////////////////////

# If the difference is bigger than this, then just take the bigger one:
_ADD_LOGS_MAX_DIFF = math.log(1e-30, 2)


def add_logs(logx, logy):
    """
    Given two numbers ``logx`` = *log(x)* and ``logy`` = *log(y)*, return
    *log(x+y)*.  Conceptually, this is the same as returning
    ``log(2**(logx)+2**(logy))``, but the actual implementation
    avoids overflow errors that could result from direct computation.
    """
    if logx < logy + _ADD_LOGS_MAX_DIFF:
        return logy
    if logy < logx + _ADD_LOGS_MAX_DIFF:
        return logx
    base = min(logx, logy)
    return base + math.log(2 ** (logx - base) + 2 ** (logy - base), 2)


def sum_logs(logs):
    return reduce(add_logs, logs[1:], logs[0]) if len(logs) != 0 else _NINF


##//////////////////////////////////////////////////////
##  Probabilistic Mix-in
##//////////////////////////////////////////////////////


class ProbabilisticMixIn:
    """
    A mix-in class to associate probabilities with other classes
    (trees, rules, etc.).  To use the ``ProbabilisticMixIn`` class,
    define a new class that derives from an existing class and from
    ProbabilisticMixIn.  You will need to define a new constructor for
    the new class, which explicitly calls the constructors of both its
    parent classes.  For example:

        >>> from nltk.probability import ProbabilisticMixIn
        >>> class A:
        ...     def __init__(self, x, y): self.data = (x,y)
        ...
        >>> class ProbabilisticA(A, ProbabilisticMixIn):
        ...     def __init__(self, x, y, **prob_kwarg):
        ...         A.__init__(self, x, y)
        ...         ProbabilisticMixIn.__init__(self, **prob_kwarg)

    See the documentation for the ProbabilisticMixIn
    ``constructor<__init__>`` for information about the arguments it
    expects.

    You should generally also redefine the string representation
    methods, the comparison methods, and the hashing method.
    """

    def __init__(self, **kwargs):
        """
        Initialize this object's probability.  This initializer should
        be called by subclass constructors.  ``prob`` should generally be
        the first argument for those constructors.

        :param prob: The probability associated with the object.
        :type prob: float
        :param logprob: The log of the probability associated with
            the object.
        :type logprob: float
        """
        if "prob" in kwargs:
            if "logprob" in kwargs:
                raise TypeError("Must specify either prob or logprob " "(not both)")
            else:
                ProbabilisticMixIn.set_prob(self, kwargs["prob"])
        elif "logprob" in kwargs:
            ProbabilisticMixIn.set_logprob(self, kwargs["logprob"])
        else:
            self.__prob = self.__logprob = None

    def set_prob(self, prob):
        """
        Set the probability associated with this object to ``prob``.

        :param prob: The new probability
        :type prob: float
        """
        self.__prob = prob
        self.__logprob = None

    def set_logprob(self, logprob):
        """
        Set the log probability associated with this object to
        ``logprob``.  I.e., set the probability associated with this
        object to ``2**(logprob)``.

        :param logprob: The new log probability
        :type logprob: float
        """
        self.__logprob = logprob
        self.__prob = None

    def prob(self):
        """
        Return the probability associated with this object.

        :rtype: float
        """
        if self.__prob is None:
            if self.__logprob is None:
                return None
            self.__prob = 2 ** (self.__logprob)
        return self.__prob

    def logprob(self):
        """
        Return ``log(p)``, where ``p`` is the probability associated
        with this object.

        :rtype: float
        """
        if self.__logprob is None:
            if self.__prob is None:
                return None
            self.__logprob = math.log(self.__prob, 2)
        return self.__logprob


class ImmutableProbabilisticMixIn(ProbabilisticMixIn):
    def set_prob(self, prob):
        raise ValueError("%s is immutable" % self.__class__.__name__)

    def set_logprob(self, prob):
        raise ValueError("%s is immutable" % self.__class__.__name__)


## Helper function for processing keyword arguments


def _get_kwarg(kwargs, key, default):
    if key in kwargs:
        arg = kwargs[key]
        del kwargs[key]
    else:
        arg = default
    return arg


##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////


def _create_rand_fdist(numsamples, numoutcomes):
    """
    Create a new frequency distribution, with random samples.  The
    samples are numbers from 1 to ``numsamples``, and are generated by
    summing two numbers, each of which has a uniform distribution.
    """

    fdist = FreqDist()
    for x in range(numoutcomes):
        y = random.randint(1, (1 + numsamples) // 2) + random.randint(
            0, numsamples // 2
        )
        fdist[y] += 1
    return fdist


def _create_sum_pdist(numsamples):
    """
    Return the true probability distribution for the experiment
    ``_create_rand_fdist(numsamples, x)``.
    """
    fdist = FreqDist()
    for x in range(1, (1 + numsamples) // 2 + 1):
        for y in range(0, numsamples // 2 + 1):
            fdist[x + y] += 1
    return MLEProbDist(fdist)


def demo(numsamples=6, numoutcomes=500):
    """
    A demonstration of frequency distributions and probability
    distributions.  This demonstration creates three frequency
    distributions with, and uses them to sample a random process with
    ``numsamples`` samples.  Each frequency distribution is sampled
    ``numoutcomes`` times.  These three frequency distributions are
    then used to build six probability distributions.  Finally, the
    probability estimates of these distributions are compared to the
    actual probability of each sample.

    :type numsamples: int
    :param numsamples: The number of samples to use in each demo
        frequency distributions.
    :type numoutcomes: int
    :param numoutcomes: The total number of outcomes for each
        demo frequency distribution.  These outcomes are divided into
        ``numsamples`` bins.
    :rtype: None
    """

    # Randomly sample a stochastic process three times.
    fdist1 = _create_rand_fdist(numsamples, numoutcomes)
    fdist2 = _create_rand_fdist(numsamples, numoutcomes)
    fdist3 = _create_rand_fdist(numsamples, numoutcomes)

    # Use our samples to create probability distributions.
    pdists = [
        MLEProbDist(fdist1),
        LidstoneProbDist(fdist1, 0.5, numsamples),
        HeldoutProbDist(fdist1, fdist2, numsamples),
        HeldoutProbDist(fdist2, fdist1, numsamples),
        CrossValidationProbDist([fdist1, fdist2, fdist3], numsamples),
        SimpleGoodTuringProbDist(fdist1),
        SimpleGoodTuringProbDist(fdist1, 7),
        _create_sum_pdist(numsamples),
    ]

    # Find the probability of each sample.
    vals = []
    for n in range(1, numsamples + 1):
        vals.append(tuple([n, fdist1.freq(n)] + [pdist.prob(n) for pdist in pdists]))

    # Print the results in a formatted table.
    print(
        "%d samples (1-%d); %d outcomes were sampled for each FreqDist"
        % (numsamples, numsamples, numoutcomes)
    )
    print("=" * 9 * (len(pdists) + 2))
    FORMATSTR = "      FreqDist " + "%8s " * (len(pdists) - 1) + "|  Actual"
    print(FORMATSTR % tuple(repr(pdist)[1:9] for pdist in pdists[:-1]))
    print("-" * 9 * (len(pdists) + 2))
    FORMATSTR = "%3d   %8.6f " + "%8.6f " * (len(pdists) - 1) + "| %8.6f"
    for val in vals:
        print(FORMATSTR % val)

    # Print the totals for each column (should all be 1.0)
    zvals = list(zip(*vals))
    sums = [sum(val) for val in zvals[1:]]
    print("-" * 9 * (len(pdists) + 2))
    FORMATSTR = "Total " + "%8.6f " * (len(pdists)) + "| %8.6f"
    print(FORMATSTR % tuple(sums))
    print("=" * 9 * (len(pdists) + 2))

    # Display the distributions themselves, if they're short enough.
    if len("%s" % fdist1) < 70:
        print("  fdist1: %s" % fdist1)
        print("  fdist2: %s" % fdist2)
        print("  fdist3: %s" % fdist3)
    print()

    print("Generating:")
    for pdist in pdists:
        fdist = FreqDist(pdist.generate() for i in range(5000))
        print("{:>20} {}".format(pdist.__class__.__name__[:20], ("%s" % fdist)[:55]))
    print()


def gt_demo():
    from nltk import corpus

    emma_words = corpus.gutenberg.words("austen-emma.txt")
    fd = FreqDist(emma_words)
    sgt = SimpleGoodTuringProbDist(fd)
    print("{:>18} {:>8}  {:>14}".format("word", "frequency", "SimpleGoodTuring"))
    fd_keys_sorted = (
        key for key, value in sorted(fd.items(), key=lambda item: item[1], reverse=True)
    )
    for key in fd_keys_sorted:
        print("%18s %8d  %14e" % (key, fd[key], sgt.prob(key)))


if __name__ == "__main__":
    demo(6, 10)
    demo(5, 5000)
    gt_demo()

__all__ = [
    "ConditionalFreqDist",
    "ConditionalProbDist",
    "ConditionalProbDistI",
    "CrossValidationProbDist",
    "DictionaryConditionalProbDist",
    "DictionaryProbDist",
    "ELEProbDist",
    "FreqDist",
    "SimpleGoodTuringProbDist",
    "HeldoutProbDist",
    "ImmutableProbabilisticMixIn",
    "LaplaceProbDist",
    "LidstoneProbDist",
    "MLEProbDist",
    "MutableProbDist",
    "KneserNeyProbDist",
    "ProbDistI",
    "ProbabilisticMixIn",
    "UniformProbDist",
    "WittenBellProbDist",
    "add_logs",
    "log_likelihood",
    "sum_logs",
    "entropy",
]

# === NexusCore/openenv\Lib\site-packages\nltk\draw\util.py ===
# Natural Language Toolkit: Drawing utilities
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Tools for graphically displaying and interacting with the objects and
processing classes defined by the Toolkit.  These tools are primarily
intended to help students visualize the objects that they create.

The graphical tools are typically built using "canvas widgets", each
of which encapsulates the graphical elements and bindings used to
display a complex object on a Tkinter ``Canvas``.  For example, NLTK
defines canvas widgets for displaying trees and directed graphs, as
well as a number of simpler widgets.  These canvas widgets make it
easier to build new graphical tools and demos.  See the class
documentation for ``CanvasWidget`` for more information.

The ``nltk.draw`` module defines the abstract ``CanvasWidget`` base
class, and a number of simple canvas widgets.  The remaining canvas
widgets are defined by submodules, such as ``nltk.draw.tree``.

The ``nltk.draw`` module also defines ``CanvasFrame``, which
encapsulates a ``Canvas`` and its scrollbars.  It uses a
``ScrollWatcherWidget`` to ensure that all canvas widgets contained on
its canvas are within the scroll region.

Acknowledgements: Many of the ideas behind the canvas widget system
are derived from ``CLIG``, a Tk-based grapher for linguistic data
structures.  For more information, see the CLIG
homepage (http://www.ags.uni-sb.de/~konrad/clig.html).

"""
from abc import ABCMeta, abstractmethod
from tkinter import (
    RAISED,
    Button,
    Canvas,
    Entry,
    Frame,
    Label,
    Menu,
    Menubutton,
    Scrollbar,
    StringVar,
    Text,
    Tk,
    Toplevel,
    Widget,
)
from tkinter.filedialog import asksaveasfilename

from nltk.util import in_idle

##//////////////////////////////////////////////////////
##  CanvasWidget
##//////////////////////////////////////////////////////


class CanvasWidget(metaclass=ABCMeta):
    """
    A collection of graphical elements and bindings used to display a
    complex object on a Tkinter ``Canvas``.  A canvas widget is
    responsible for managing the ``Canvas`` tags and callback bindings
    necessary to display and interact with the object.  Canvas widgets
    are often organized into hierarchies, where parent canvas widgets
    control aspects of their child widgets.

    Each canvas widget is bound to a single ``Canvas``.  This ``Canvas``
    is specified as the first argument to the ``CanvasWidget``'s
    constructor.

    Attributes.  Each canvas widget can support a variety of
    "attributes", which control how the canvas widget is displayed.
    Some typical examples attributes are ``color``, ``font``, and
    ``radius``.  Each attribute has a default value.  This default
    value can be overridden in the constructor, using keyword
    arguments of the form ``attribute=value``:

        >>> from nltk.draw.util import TextWidget
        >>> cn = TextWidget(Canvas(), 'test', color='red')  # doctest: +SKIP

    Attribute values can also be changed after a canvas widget has
    been constructed, using the ``__setitem__`` operator:

        >>> cn['font'] = 'times'  # doctest: +SKIP

    The current value of an attribute value can be queried using the
    ``__getitem__`` operator:

        >>> cn['color']  # doctest: +SKIP
        'red'

    For a list of the attributes supported by a type of canvas widget,
    see its class documentation.

    Interaction.  The attribute ``'draggable'`` controls whether the
    user can drag a canvas widget around the canvas.  By default,
    canvas widgets are not draggable.

    ``CanvasWidget`` provides callback support for two types of user
    interaction: clicking and dragging.  The method ``bind_click``
    registers a callback function that is called whenever the canvas
    widget is clicked.  The method ``bind_drag`` registers a callback
    function that is called after the canvas widget is dragged.  If
    the user clicks or drags a canvas widget with no registered
    callback function, then the interaction event will propagate to
    its parent.  For each canvas widget, only one callback function
    may be registered for an interaction event.  Callback functions
    can be deregistered with the ``unbind_click`` and ``unbind_drag``
    methods.

    Subclassing.  ``CanvasWidget`` is an abstract class.  Subclasses
    are required to implement the following methods:

      - ``__init__``: Builds a new canvas widget.  It must perform the
        following three tasks (in order):

          - Create any new graphical elements.
          - Call ``_add_child_widget`` on each child widget.
          - Call the ``CanvasWidget`` constructor.
      - ``_tags``: Returns a list of the canvas tags for all graphical
        elements managed by this canvas widget, not including
        graphical elements managed by its child widgets.
      - ``_manage``: Arranges the child widgets of this canvas widget.
        This is typically only called when the canvas widget is
        created.
      - ``_update``: Update this canvas widget in response to a
        change in a single child.

    For a ``CanvasWidget`` with no child widgets, the default
    definitions for ``_manage`` and ``_update`` may be used.

    If a subclass defines any attributes, then it should implement
    ``__getitem__`` and ``__setitem__``.  If either of these methods is
    called with an unknown attribute, then they should propagate the
    request to ``CanvasWidget``.

    Most subclasses implement a number of additional methods that
    modify the ``CanvasWidget`` in some way.  These methods must call
    ``parent.update(self)`` after making any changes to the canvas
    widget's graphical elements.  The canvas widget must also call
    ``parent.update(self)`` after changing any attribute value that
    affects the shape or position of the canvas widget's graphical
    elements.

    :type __canvas: Tkinter.Canvas
    :ivar __canvas: This ``CanvasWidget``'s canvas.

    :type __parent: CanvasWidget or None
    :ivar __parent: This ``CanvasWidget``'s hierarchical parent widget.
    :type __children: list(CanvasWidget)
    :ivar __children: This ``CanvasWidget``'s hierarchical child widgets.

    :type __updating: bool
    :ivar __updating: Is this canvas widget currently performing an
        update?  If it is, then it will ignore any new update requests
        from child widgets.

    :type __draggable: bool
    :ivar __draggable: Is this canvas widget draggable?
    :type __press: event
    :ivar __press: The ButtonPress event that we're currently handling.
    :type __drag_x: int
    :ivar __drag_x: Where it's been moved to (to find dx)
    :type __drag_y: int
    :ivar __drag_y: Where it's been moved to (to find dy)
    :type __callbacks: dictionary
    :ivar __callbacks: Registered callbacks.  Currently, four keys are
        used: ``1``, ``2``, ``3``, and ``'drag'``.  The values are
        callback functions.  Each callback function takes a single
        argument, which is the ``CanvasWidget`` that triggered the
        callback.
    """

    def __init__(self, canvas, parent=None, **attribs):
        """
        Create a new canvas widget.  This constructor should only be
        called by subclass constructors; and it should be called only
        "after" the subclass has constructed all graphical canvas
        objects and registered all child widgets.

        :param canvas: This canvas widget's canvas.
        :type canvas: Tkinter.Canvas
        :param parent: This canvas widget's hierarchical parent.
        :type parent: CanvasWidget
        :param attribs: The new canvas widget's attributes.
        """
        if self.__class__ == CanvasWidget:
            raise TypeError("CanvasWidget is an abstract base class")

        if not isinstance(canvas, Canvas):
            raise TypeError("Expected a canvas!")

        self.__canvas = canvas
        self.__parent = parent

        # If the subclass constructor called _add_child_widget, then
        # self.__children will already exist.
        if not hasattr(self, "_CanvasWidget__children"):
            self.__children = []

        # Is this widget hidden?
        self.__hidden = 0

        # Update control (prevents infinite loops)
        self.__updating = 0

        # Button-press and drag callback handling.
        self.__press = None
        self.__drag_x = self.__drag_y = 0
        self.__callbacks = {}
        self.__draggable = 0

        # Set up attributes.
        for attr, value in list(attribs.items()):
            self[attr] = value

        # Manage this canvas widget
        self._manage()

        # Register any new bindings
        for tag in self._tags():
            self.__canvas.tag_bind(tag, "<ButtonPress-1>", self.__press_cb)
            self.__canvas.tag_bind(tag, "<ButtonPress-2>", self.__press_cb)
            self.__canvas.tag_bind(tag, "<ButtonPress-3>", self.__press_cb)

    ##//////////////////////////////////////////////////////
    ##  Inherited methods.
    ##//////////////////////////////////////////////////////

    def bbox(self):
        """
        :return: A bounding box for this ``CanvasWidget``. The bounding
            box is a tuple of four coordinates, *(xmin, ymin, xmax, ymax)*,
            for a rectangle which encloses all of the canvas
            widget's graphical elements.  Bounding box coordinates are
            specified with respect to the coordinate space of the ``Canvas``.
        :rtype: tuple(int, int, int, int)
        """
        if self.__hidden:
            return (0, 0, 0, 0)
        if len(self.tags()) == 0:
            raise ValueError("No tags")
        return self.__canvas.bbox(*self.tags())

    def width(self):
        """
        :return: The width of this canvas widget's bounding box, in
            its ``Canvas``'s coordinate space.
        :rtype: int
        """
        if len(self.tags()) == 0:
            raise ValueError("No tags")
        bbox = self.__canvas.bbox(*self.tags())
        return bbox[2] - bbox[0]

    def height(self):
        """
        :return: The height of this canvas widget's bounding box, in
            its ``Canvas``'s coordinate space.
        :rtype: int
        """
        if len(self.tags()) == 0:
            raise ValueError("No tags")
        bbox = self.__canvas.bbox(*self.tags())
        return bbox[3] - bbox[1]

    def parent(self):
        """
        :return: The hierarchical parent of this canvas widget.
            ``self`` is considered a subpart of its parent for
            purposes of user interaction.
        :rtype: CanvasWidget or None
        """
        return self.__parent

    def child_widgets(self):
        """
        :return: A list of the hierarchical children of this canvas
            widget.  These children are considered part of ``self``
            for purposes of user interaction.
        :rtype: list of CanvasWidget
        """
        return self.__children

    def canvas(self):
        """
        :return: The canvas that this canvas widget is bound to.
        :rtype: Tkinter.Canvas
        """
        return self.__canvas

    def move(self, dx, dy):
        """
        Move this canvas widget by a given distance.  In particular,
        shift the canvas widget right by ``dx`` pixels, and down by
        ``dy`` pixels.  Both ``dx`` and ``dy`` may be negative, resulting
        in leftward or upward movement.

        :type dx: int
        :param dx: The number of pixels to move this canvas widget
            rightwards.
        :type dy: int
        :param dy: The number of pixels to move this canvas widget
            downwards.
        :rtype: None
        """
        if dx == dy == 0:
            return
        for tag in self.tags():
            self.__canvas.move(tag, dx, dy)
        if self.__parent:
            self.__parent.update(self)

    def moveto(self, x, y, anchor="NW"):
        """
        Move this canvas widget to the given location.  In particular,
        shift the canvas widget such that the corner or side of the
        bounding box specified by ``anchor`` is at location (``x``,
        ``y``).

        :param x,y: The location that the canvas widget should be moved
            to.
        :param anchor: The corner or side of the canvas widget that
            should be moved to the specified location.  ``'N'``
            specifies the top center; ``'NE'`` specifies the top right
            corner; etc.
        """
        x1, y1, x2, y2 = self.bbox()
        if anchor == "NW":
            self.move(x - x1, y - y1)
        if anchor == "N":
            self.move(x - x1 / 2 - x2 / 2, y - y1)
        if anchor == "NE":
            self.move(x - x2, y - y1)
        if anchor == "E":
            self.move(x - x2, y - y1 / 2 - y2 / 2)
        if anchor == "SE":
            self.move(x - x2, y - y2)
        if anchor == "S":
            self.move(x - x1 / 2 - x2 / 2, y - y2)
        if anchor == "SW":
            self.move(x - x1, y - y2)
        if anchor == "W":
            self.move(x - x1, y - y1 / 2 - y2 / 2)

    def destroy(self):
        """
        Remove this ``CanvasWidget`` from its ``Canvas``.  After a
        ``CanvasWidget`` has been destroyed, it should not be accessed.

        Note that you only need to destroy a top-level
        ``CanvasWidget``; its child widgets will be destroyed
        automatically.  If you destroy a non-top-level
        ``CanvasWidget``, then the entire top-level widget will be
        destroyed.

        :raise ValueError: if this ``CanvasWidget`` has a parent.
        :rtype: None
        """
        if self.__parent is not None:
            self.__parent.destroy()
            return

        for tag in self.tags():
            self.__canvas.tag_unbind(tag, "<ButtonPress-1>")
            self.__canvas.tag_unbind(tag, "<ButtonPress-2>")
            self.__canvas.tag_unbind(tag, "<ButtonPress-3>")
        self.__canvas.delete(*self.tags())
        self.__canvas = None

    def update(self, child):
        """
        Update the graphical display of this canvas widget, and all of
        its ancestors, in response to a change in one of this canvas
        widget's children.

        :param child: The child widget that changed.
        :type child: CanvasWidget
        """
        if self.__hidden or child.__hidden:
            return
        # If we're already updating, then do nothing.  This prevents
        # infinite loops when _update modifies its children.
        if self.__updating:
            return
        self.__updating = 1

        # Update this CanvasWidget.
        self._update(child)

        # Propagate update request to the parent.
        if self.__parent:
            self.__parent.update(self)

        # We're done updating.
        self.__updating = 0

    def manage(self):
        """
        Arrange this canvas widget and all of its descendants.

        :rtype: None
        """
        if self.__hidden:
            return
        for child in self.__children:
            child.manage()
        self._manage()

    def tags(self):
        """
        :return: a list of the canvas tags for all graphical
            elements managed by this canvas widget, including
            graphical elements managed by its child widgets.
        :rtype: list of int
        """
        if self.__canvas is None:
            raise ValueError("Attempt to access a destroyed canvas widget")
        tags = []
        tags += self._tags()
        for child in self.__children:
            tags += child.tags()
        return tags

    def __setitem__(self, attr, value):
        """
        Set the value of the attribute ``attr`` to ``value``.  See the
        class documentation for a list of attributes supported by this
        canvas widget.

        :rtype: None
        """
        if attr == "draggable":
            self.__draggable = value
        else:
            raise ValueError("Unknown attribute %r" % attr)

    def __getitem__(self, attr):
        """
        :return: the value of the attribute ``attr``.  See the class
            documentation for a list of attributes supported by this
            canvas widget.
        :rtype: (any)
        """
        if attr == "draggable":
            return self.__draggable
        else:
            raise ValueError("Unknown attribute %r" % attr)

    def __repr__(self):
        """
        :return: a string representation of this canvas widget.
        :rtype: str
        """
        return "<%s>" % self.__class__.__name__

    def hide(self):
        """
        Temporarily hide this canvas widget.

        :rtype: None
        """
        self.__hidden = 1
        for tag in self.tags():
            self.__canvas.itemconfig(tag, state="hidden")

    def show(self):
        """
        Show a hidden canvas widget.

        :rtype: None
        """
        self.__hidden = 0
        for tag in self.tags():
            self.__canvas.itemconfig(tag, state="normal")

    def hidden(self):
        """
        :return: True if this canvas widget is hidden.
        :rtype: bool
        """
        return self.__hidden

    ##//////////////////////////////////////////////////////
    ##  Callback interface
    ##//////////////////////////////////////////////////////

    def bind_click(self, callback, button=1):
        """
        Register a new callback that will be called whenever this
        ``CanvasWidget`` is clicked on.

        :type callback: function
        :param callback: The callback function that will be called
            whenever this ``CanvasWidget`` is clicked.  This function
            will be called with this ``CanvasWidget`` as its argument.
        :type button: int
        :param button: Which button the user should use to click on
            this ``CanvasWidget``.  Typically, this should be 1 (left
            button), 3 (right button), or 2 (middle button).
        """
        self.__callbacks[button] = callback

    def bind_drag(self, callback):
        """
        Register a new callback that will be called after this
        ``CanvasWidget`` is dragged.  This implicitly makes this
        ``CanvasWidget`` draggable.

        :type callback: function
        :param callback: The callback function that will be called
            whenever this ``CanvasWidget`` is clicked.  This function
            will be called with this ``CanvasWidget`` as its argument.
        """
        self.__draggable = 1
        self.__callbacks["drag"] = callback

    def unbind_click(self, button=1):
        """
        Remove a callback that was registered with ``bind_click``.

        :type button: int
        :param button: Which button the user should use to click on
            this ``CanvasWidget``.  Typically, this should be 1 (left
            button), 3 (right button), or 2 (middle button).
        """
        try:
            del self.__callbacks[button]
        except:
            pass

    def unbind_drag(self):
        """
        Remove a callback that was registered with ``bind_drag``.
        """
        try:
            del self.__callbacks["drag"]
        except:
            pass

    ##//////////////////////////////////////////////////////
    ##  Callback internals
    ##//////////////////////////////////////////////////////

    def __press_cb(self, event):
        """
        Handle a button-press event:
          - record the button press event in ``self.__press``
          - register a button-release callback.
          - if this CanvasWidget or any of its ancestors are
            draggable, then register the appropriate motion callback.
        """
        # If we're already waiting for a button release, then ignore
        # this new button press.
        if (
            self.__canvas.bind("<ButtonRelease-1>")
            or self.__canvas.bind("<ButtonRelease-2>")
            or self.__canvas.bind("<ButtonRelease-3>")
        ):
            return

        # Unbind motion (just in case; this shouldn't be necessary)
        self.__canvas.unbind("<Motion>")

        # Record the button press event.
        self.__press = event

        # If any ancestor is draggable, set up a motion callback.
        # (Only if they pressed button number 1)
        if event.num == 1:
            widget = self
            while widget is not None:
                if widget["draggable"]:
                    widget.__start_drag(event)
                    break
                widget = widget.parent()

        # Set up the button release callback.
        self.__canvas.bind("<ButtonRelease-%d>" % event.num, self.__release_cb)

    def __start_drag(self, event):
        """
        Begin dragging this object:
          - register a motion callback
          - record the drag coordinates
        """
        self.__canvas.bind("<Motion>", self.__motion_cb)
        self.__drag_x = event.x
        self.__drag_y = event.y

    def __motion_cb(self, event):
        """
        Handle a motion event:
          - move this object to the new location
          - record the new drag coordinates
        """
        self.move(event.x - self.__drag_x, event.y - self.__drag_y)
        self.__drag_x = event.x
        self.__drag_y = event.y

    def __release_cb(self, event):
        """
        Handle a release callback:
          - unregister motion & button release callbacks.
          - decide whether they clicked, dragged, or cancelled
          - call the appropriate handler.
        """
        # Unbind the button release & motion callbacks.
        self.__canvas.unbind("<ButtonRelease-%d>" % event.num)
        self.__canvas.unbind("<Motion>")

        # Is it a click or a drag?
        if (
            event.time - self.__press.time < 100
            and abs(event.x - self.__press.x) + abs(event.y - self.__press.y) < 5
        ):
            # Move it back, if we were dragging.
            if self.__draggable and event.num == 1:
                self.move(
                    self.__press.x - self.__drag_x, self.__press.y - self.__drag_y
                )
            self.__click(event.num)
        elif event.num == 1:
            self.__drag()

        self.__press = None

    def __drag(self):
        """
        If this ``CanvasWidget`` has a drag callback, then call it;
        otherwise, find the closest ancestor with a drag callback, and
        call it.  If no ancestors have a drag callback, do nothing.
        """
        if self.__draggable:
            if "drag" in self.__callbacks:
                cb = self.__callbacks["drag"]
                try:
                    cb(self)
                except:
                    print("Error in drag callback for %r" % self)
        elif self.__parent is not None:
            self.__parent.__drag()

    def __click(self, button):
        """
        If this ``CanvasWidget`` has a drag callback, then call it;
        otherwise, find the closest ancestor with a click callback, and
        call it.  If no ancestors have a click callback, do nothing.
        """
        if button in self.__callbacks:
            cb = self.__callbacks[button]
            # try:
            cb(self)
            # except:
            #    print('Error in click callback for %r' % self)
            #    raise
        elif self.__parent is not None:
            self.__parent.__click(button)

    ##//////////////////////////////////////////////////////
    ##  Child/parent Handling
    ##//////////////////////////////////////////////////////

    def _add_child_widget(self, child):
        """
        Register a hierarchical child widget.  The child will be
        considered part of this canvas widget for purposes of user
        interaction.  ``_add_child_widget`` has two direct effects:
          - It sets ``child``'s parent to this canvas widget.
          - It adds ``child`` to the list of canvas widgets returned by
            the ``child_widgets`` member function.

        :param child: The new child widget.  ``child`` must not already
            have a parent.
        :type child: CanvasWidget
        """
        if not hasattr(self, "_CanvasWidget__children"):
            self.__children = []
        if child.__parent is not None:
            raise ValueError(f"{child} already has a parent")
        child.__parent = self
        self.__children.append(child)

    def _remove_child_widget(self, child):
        """
        Remove a hierarchical child widget.  This child will no longer
        be considered part of this canvas widget for purposes of user
        interaction.  ``_add_child_widget`` has two direct effects:
          - It sets ``child``'s parent to None.
          - It removes ``child`` from the list of canvas widgets
            returned by the ``child_widgets`` member function.

        :param child: The child widget to remove.  ``child`` must be a
            child of this canvas widget.
        :type child: CanvasWidget
        """
        self.__children.remove(child)
        child.__parent = None

    ##//////////////////////////////////////////////////////
    ##  Defined by subclass
    ##//////////////////////////////////////////////////////

    @abstractmethod
    def _tags(self):
        """
        :return: a list of canvas tags for all graphical elements
            managed by this canvas widget, not including graphical
            elements managed by its child widgets.
        :rtype: list of int
        """

    def _manage(self):
        """
        Arrange the child widgets of this canvas widget.  This method
        is called when the canvas widget is initially created.  It is
        also called if the user calls the ``manage`` method on this
        canvas widget or any of its ancestors.

        :rtype: None
        """

    def _update(self, child):
        """
        Update this canvas widget in response to a change in one of
        its children.

        :param child: The child that changed.
        :type child: CanvasWidget
        :rtype: None
        """


##//////////////////////////////////////////////////////
##  Basic widgets.
##//////////////////////////////////////////////////////


class TextWidget(CanvasWidget):
    """
    A canvas widget that displays a single string of text.

    Attributes:
      - ``color``: the color of the text.
      - ``font``: the font used to display the text.
      - ``justify``: justification for multi-line texts.  Valid values
        are ``left``, ``center``, and ``right``.
      - ``width``: the width of the text.  If the text is wider than
        this width, it will be line-wrapped at whitespace.
      - ``draggable``: whether the text can be dragged by the user.
    """

    def __init__(self, canvas, text, **attribs):
        """
        Create a new text widget.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :type text: str
        :param text: The string of text to display.
        :param attribs: The new canvas widget's attributes.
        """
        self._text = text
        self._tag = canvas.create_text(1, 1, text=text)
        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        if attr in ("color", "font", "justify", "width"):
            if attr == "color":
                attr = "fill"
            self.canvas().itemconfig(self._tag, {attr: value})
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == "width":
            return int(self.canvas().itemcget(self._tag, attr))
        elif attr in ("color", "font", "justify"):
            if attr == "color":
                attr = "fill"
            return self.canvas().itemcget(self._tag, attr)
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _tags(self):
        return [self._tag]

    def text(self):
        """
        :return: The text displayed by this text widget.
        :rtype: str
        """
        return self.canvas().itemcget(self._tag, "TEXT")

    def set_text(self, text):
        """
        Change the text that is displayed by this text widget.

        :type text: str
        :param text: The string of text to display.
        :rtype: None
        """
        self.canvas().itemconfig(self._tag, text=text)
        if self.parent() is not None:
            self.parent().update(self)

    def __repr__(self):
        return "[Text: %r]" % self._text


class SymbolWidget(TextWidget):
    """
    A canvas widget that displays special symbols, such as the
    negation sign and the exists operator.  Symbols are specified by
    name.  Currently, the following symbol names are defined: ``neg``,
    ``disj``, ``conj``, ``lambda``, ``merge``, ``forall``, ``exists``,
    ``subseteq``, ``subset``, ``notsubset``, ``emptyset``, ``imp``,
    ``rightarrow``, ``equal``, ``notequal``, ``epsilon``.

    Attributes:

    - ``color``: the color of the text.
    - ``draggable``: whether the text can be dragged by the user.

    :cvar SYMBOLS: A dictionary mapping from symbols to the character
        in the ``symbol`` font used to render them.
    """

    SYMBOLS = {
        "neg": "\330",
        "disj": "\332",
        "conj": "\331",
        "lambda": "\154",
        "merge": "\304",
        "forall": "\042",
        "exists": "\044",
        "subseteq": "\315",
        "subset": "\314",
        "notsubset": "\313",
        "emptyset": "\306",
        "imp": "\336",
        "rightarrow": chr(222),  #'\256',
        "equal": "\75",
        "notequal": "\271",
        "intersection": "\307",
        "union": "\310",
        "epsilon": "e",
    }

    def __init__(self, canvas, symbol, **attribs):
        """
        Create a new symbol widget.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :type symbol: str
        :param symbol: The name of the symbol to display.
        :param attribs: The new canvas widget's attributes.
        """
        attribs["font"] = "symbol"
        TextWidget.__init__(self, canvas, "", **attribs)
        self.set_symbol(symbol)

    def symbol(self):
        """
        :return: the name of the symbol that is displayed by this
            symbol widget.
        :rtype: str
        """
        return self._symbol

    def set_symbol(self, symbol):
        """
        Change the symbol that is displayed by this symbol widget.

        :type symbol: str
        :param symbol: The name of the symbol to display.
        """
        if symbol not in SymbolWidget.SYMBOLS:
            raise ValueError("Unknown symbol: %s" % symbol)
        self._symbol = symbol
        self.set_text(SymbolWidget.SYMBOLS[symbol])

    def __repr__(self):
        return "[Symbol: %r]" % self._symbol

    @staticmethod
    def symbolsheet(size=20):
        """
        Open a new Tkinter window that displays the entire alphabet
        for the symbol font.  This is useful for constructing the
        ``SymbolWidget.SYMBOLS`` dictionary.
        """
        top = Tk()

        def destroy(e, top=top):
            top.destroy()

        top.bind("q", destroy)
        Button(top, text="Quit", command=top.destroy).pack(side="bottom")
        text = Text(top, font=("helvetica", -size), width=20, height=30)
        text.pack(side="left")
        sb = Scrollbar(top, command=text.yview)
        text["yscrollcommand"] = sb.set
        sb.pack(side="right", fill="y")
        text.tag_config("symbol", font=("symbol", -size))
        for i in range(256):
            if i in (0, 10):
                continue  # null and newline
            for k, v in list(SymbolWidget.SYMBOLS.items()):
                if v == chr(i):
                    text.insert("end", "%-10s\t" % k)
                    break
            else:
                text.insert("end", "%-10d  \t" % i)
            text.insert("end", "[%s]\n" % chr(i), "symbol")
        top.mainloop()


class AbstractContainerWidget(CanvasWidget):
    """
    An abstract class for canvas widgets that contain a single child,
    such as ``BoxWidget`` and ``OvalWidget``.  Subclasses must define
    a constructor, which should create any new graphical elements and
    then call the ``AbstractCanvasContainer`` constructor.  Subclasses
    must also define the ``_update`` method and the ``_tags`` method;
    and any subclasses that define attributes should define
    ``__setitem__`` and ``__getitem__``.
    """

    def __init__(self, canvas, child, **attribs):
        """
        Create a new container widget.  This constructor should only
        be called by subclass constructors.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :param child: The container's child widget.  ``child`` must not
            have a parent.
        :type child: CanvasWidget
        :param attribs: The new canvas widget's attributes.
        """
        self._child = child
        self._add_child_widget(child)
        CanvasWidget.__init__(self, canvas, **attribs)

    def _manage(self):
        self._update(self._child)

    def child(self):
        """
        :return: The child widget contained by this container widget.
        :rtype: CanvasWidget
        """
        return self._child

    def set_child(self, child):
        """
        Change the child widget contained by this container widget.

        :param child: The new child widget.  ``child`` must not have a
            parent.
        :type child: CanvasWidget
        :rtype: None
        """
        self._remove_child_widget(self._child)
        self._add_child_widget(child)
        self._child = child
        self.update(child)

    def __repr__(self):
        name = self.__class__.__name__
        if name[-6:] == "Widget":
            name = name[:-6]
        return f"[{name}: {self._child!r}]"


class BoxWidget(AbstractContainerWidget):
    """
    A canvas widget that places a box around a child widget.

    Attributes:
      - ``fill``: The color used to fill the interior of the box.
      - ``outline``: The color used to draw the outline of the box.
      - ``width``: The width of the outline of the box.
      - ``margin``: The number of pixels space left between the child
        and the box.
      - ``draggable``: whether the text can be dragged by the user.
    """

    def __init__(self, canvas, child, **attribs):
        """
        Create a new box widget.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :param child: The child widget.  ``child`` must not have a
            parent.
        :type child: CanvasWidget
        :param attribs: The new canvas widget's attributes.
        """
        self._child = child
        self._margin = 1
        self._box = canvas.create_rectangle(1, 1, 1, 1)
        canvas.tag_lower(self._box)
        AbstractContainerWidget.__init__(self, canvas, child, **attribs)

    def __setitem__(self, attr, value):
        if attr == "margin":
            self._margin = value
        elif attr in ("outline", "fill", "width"):
            self.canvas().itemconfig(self._box, {attr: value})
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == "margin":
            return self._margin
        elif attr == "width":
            return float(self.canvas().itemcget(self._box, attr))
        elif attr in ("outline", "fill", "width"):
            return self.canvas().itemcget(self._box, attr)
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _update(self, child):
        (x1, y1, x2, y2) = child.bbox()
        margin = self._margin + self["width"] / 2
        self.canvas().coords(
            self._box, x1 - margin, y1 - margin, x2 + margin, y2 + margin
        )

    def _tags(self):
        return [self._box]


class OvalWidget(AbstractContainerWidget):
    """
    A canvas widget that places a oval around a child widget.

    Attributes:
      - ``fill``: The color used to fill the interior of the oval.
      - ``outline``: The color used to draw the outline of the oval.
      - ``width``: The width of the outline of the oval.
      - ``margin``: The number of pixels space left between the child
        and the oval.
      - ``draggable``: whether the text can be dragged by the user.
      - ``double``: If true, then a double-oval is drawn.
    """

    def __init__(self, canvas, child, **attribs):
        """
        Create a new oval widget.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :param child: The child widget.  ``child`` must not have a
            parent.
        :type child: CanvasWidget
        :param attribs: The new canvas widget's attributes.
        """
        self._child = child
        self._margin = 1
        self._oval = canvas.create_oval(1, 1, 1, 1)
        self._circle = attribs.pop("circle", False)
        self._double = attribs.pop("double", False)
        if self._double:
            self._oval2 = canvas.create_oval(1, 1, 1, 1)
        else:
            self._oval2 = None
        canvas.tag_lower(self._oval)
        AbstractContainerWidget.__init__(self, canvas, child, **attribs)

    def __setitem__(self, attr, value):
        c = self.canvas()
        if attr == "margin":
            self._margin = value
        elif attr == "double":
            if value == True and self._oval2 is None:
                # Copy attributes & position from self._oval.
                x1, y1, x2, y2 = c.bbox(self._oval)
                w = self["width"] * 2
                self._oval2 = c.create_oval(
                    x1 - w,
                    y1 - w,
                    x2 + w,
                    y2 + w,
                    outline=c.itemcget(self._oval, "outline"),
                    width=c.itemcget(self._oval, "width"),
                )
                c.tag_lower(self._oval2)
            if value == False and self._oval2 is not None:
                c.delete(self._oval2)
                self._oval2 = None
        elif attr in ("outline", "fill", "width"):
            c.itemconfig(self._oval, {attr: value})
            if self._oval2 is not None and attr != "fill":
                c.itemconfig(self._oval2, {attr: value})
            if self._oval2 is not None and attr != "fill":
                self.canvas().itemconfig(self._oval2, {attr: value})
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == "margin":
            return self._margin
        elif attr == "double":
            return self._double is not None
        elif attr == "width":
            return float(self.canvas().itemcget(self._oval, attr))
        elif attr in ("outline", "fill", "width"):
            return self.canvas().itemcget(self._oval, attr)
        else:
            return CanvasWidget.__getitem__(self, attr)

    # The ratio between inscribed & circumscribed ovals
    RATIO = 1.4142135623730949

    def _update(self, child):
        R = OvalWidget.RATIO
        (x1, y1, x2, y2) = child.bbox()
        margin = self._margin

        # If we're a circle, pretend our contents are square.
        if self._circle:
            dx, dy = abs(x1 - x2), abs(y1 - y2)
            if dx > dy:
                y = (y1 + y2) / 2
                y1, y2 = y - dx / 2, y + dx / 2
            elif dy > dx:
                x = (x1 + x2) / 2
                x1, x2 = x - dy / 2, x + dy / 2

        # Find the four corners.
        left = int((x1 * (1 + R) + x2 * (1 - R)) / 2)
        right = left + int((x2 - x1) * R)
        top = int((y1 * (1 + R) + y2 * (1 - R)) / 2)
        bot = top + int((y2 - y1) * R)
        self.canvas().coords(
            self._oval, left - margin, top - margin, right + margin, bot + margin
        )
        if self._oval2 is not None:
            self.canvas().coords(
                self._oval2,
                left - margin + 2,
                top - margin + 2,
                right + margin - 2,
                bot + margin - 2,
            )

    def _tags(self):
        if self._oval2 is None:
            return [self._oval]
        else:
            return [self._oval, self._oval2]


class ParenWidget(AbstractContainerWidget):
    """
    A canvas widget that places a pair of parenthases around a child
    widget.

    Attributes:
      - ``color``: The color used to draw the parenthases.
      - ``width``: The width of the parenthases.
      - ``draggable``: whether the text can be dragged by the user.
    """

    def __init__(self, canvas, child, **attribs):
        """
        Create a new parenthasis widget.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :param child: The child widget.  ``child`` must not have a
            parent.
        :type child: CanvasWidget
        :param attribs: The new canvas widget's attributes.
        """
        self._child = child
        self._oparen = canvas.create_arc(1, 1, 1, 1, style="arc", start=90, extent=180)
        self._cparen = canvas.create_arc(1, 1, 1, 1, style="arc", start=-90, extent=180)
        AbstractContainerWidget.__init__(self, canvas, child, **attribs)

    def __setitem__(self, attr, value):
        if attr == "color":
            self.canvas().itemconfig(self._oparen, outline=value)
            self.canvas().itemconfig(self._cparen, outline=value)
        elif attr == "width":
            self.canvas().itemconfig(self._oparen, width=value)
            self.canvas().itemconfig(self._cparen, width=value)
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == "color":
            return self.canvas().itemcget(self._oparen, "outline")
        elif attr == "width":
            return self.canvas().itemcget(self._oparen, "width")
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _update(self, child):
        (x1, y1, x2, y2) = child.bbox()
        width = max((y2 - y1) / 6, 4)
        self.canvas().coords(self._oparen, x1 - width, y1, x1 + width, y2)
        self.canvas().coords(self._cparen, x2 - width, y1, x2 + width, y2)

    def _tags(self):
        return [self._oparen, self._cparen]


class BracketWidget(AbstractContainerWidget):
    """
    A canvas widget that places a pair of brackets around a child
    widget.

    Attributes:
      - ``color``: The color used to draw the brackets.
      - ``width``: The width of the brackets.
      - ``draggable``: whether the text can be dragged by the user.
    """

    def __init__(self, canvas, child, **attribs):
        """
        Create a new bracket widget.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :param child: The child widget.  ``child`` must not have a
            parent.
        :type child: CanvasWidget
        :param attribs: The new canvas widget's attributes.
        """
        self._child = child
        self._obrack = canvas.create_line(1, 1, 1, 1, 1, 1, 1, 1)
        self._cbrack = canvas.create_line(1, 1, 1, 1, 1, 1, 1, 1)
        AbstractContainerWidget.__init__(self, canvas, child, **attribs)

    def __setitem__(self, attr, value):
        if attr == "color":
            self.canvas().itemconfig(self._obrack, fill=value)
            self.canvas().itemconfig(self._cbrack, fill=value)
        elif attr == "width":
            self.canvas().itemconfig(self._obrack, width=value)
            self.canvas().itemconfig(self._cbrack, width=value)
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == "color":
            return self.canvas().itemcget(self._obrack, "outline")
        elif attr == "width":
            return self.canvas().itemcget(self._obrack, "width")
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _update(self, child):
        (x1, y1, x2, y2) = child.bbox()
        width = max((y2 - y1) / 8, 2)
        self.canvas().coords(
            self._obrack, x1, y1, x1 - width, y1, x1 - width, y2, x1, y2
        )
        self.canvas().coords(
            self._cbrack, x2, y1, x2 + width, y1, x2 + width, y2, x2, y2
        )

    def _tags(self):
        return [self._obrack, self._cbrack]


class SequenceWidget(CanvasWidget):
    """
    A canvas widget that keeps a list of canvas widgets in a
    horizontal line.

    Attributes:
      - ``align``: The vertical alignment of the children.  Possible
        values are ``'top'``, ``'center'``, and ``'bottom'``.  By
        default, children are center-aligned.
      - ``space``: The amount of horizontal space to place between
        children.  By default, one pixel of space is used.
      - ``ordered``: If true, then keep the children in their
        original order.
    """

    def __init__(self, canvas, *children, **attribs):
        """
        Create a new sequence widget.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :param children: The widgets that should be aligned
            horizontally.  Each child must not have a parent.
        :type children: list(CanvasWidget)
        :param attribs: The new canvas widget's attributes.
        """
        self._align = "center"
        self._space = 1
        self._ordered = False
        self._children = list(children)
        for child in children:
            self._add_child_widget(child)
        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        if attr == "align":
            if value not in ("top", "bottom", "center"):
                raise ValueError("Bad alignment: %r" % value)
            self._align = value
        elif attr == "space":
            self._space = value
        elif attr == "ordered":
            self._ordered = value
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == "align":
            return self._align
        elif attr == "space":
            return self._space
        elif attr == "ordered":
            return self._ordered
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _tags(self):
        return []

    def _yalign(self, top, bot):
        if self._align == "top":
            return top
        if self._align == "bottom":
            return bot
        if self._align == "center":
            return (top + bot) / 2

    def _update(self, child):
        # Align all children with child.
        (left, top, right, bot) = child.bbox()
        y = self._yalign(top, bot)
        for c in self._children:
            (x1, y1, x2, y2) = c.bbox()
            c.move(0, y - self._yalign(y1, y2))

        if self._ordered and len(self._children) > 1:
            index = self._children.index(child)

            x = right + self._space
            for i in range(index + 1, len(self._children)):
                (x1, y1, x2, y2) = self._children[i].bbox()
                if x > x1:
                    self._children[i].move(x - x1, 0)
                    x += x2 - x1 + self._space

            x = left - self._space
            for i in range(index - 1, -1, -1):
                (x1, y1, x2, y2) = self._children[i].bbox()
                if x < x2:
                    self._children[i].move(x - x2, 0)
                    x -= x2 - x1 + self._space

    def _manage(self):
        if len(self._children) == 0:
            return
        child = self._children[0]

        # Align all children with child.
        (left, top, right, bot) = child.bbox()
        y = self._yalign(top, bot)

        index = self._children.index(child)

        # Line up children to the right of child.
        x = right + self._space
        for i in range(index + 1, len(self._children)):
            (x1, y1, x2, y2) = self._children[i].bbox()
            self._children[i].move(x - x1, y - self._yalign(y1, y2))
            x += x2 - x1 + self._space

        # Line up children to the left of child.
        x = left - self._space
        for i in range(index - 1, -1, -1):
            (x1, y1, x2, y2) = self._children[i].bbox()
            self._children[i].move(x - x2, y - self._yalign(y1, y2))
            x -= x2 - x1 + self._space

    def __repr__(self):
        return "[Sequence: " + repr(self._children)[1:-1] + "]"

    # Provide an alias for the child_widgets() member.
    children = CanvasWidget.child_widgets

    def replace_child(self, oldchild, newchild):
        """
        Replace the child canvas widget ``oldchild`` with ``newchild``.
        ``newchild`` must not have a parent.  ``oldchild``'s parent will
        be set to None.

        :type oldchild: CanvasWidget
        :param oldchild: The child canvas widget to remove.
        :type newchild: CanvasWidget
        :param newchild: The canvas widget that should replace
            ``oldchild``.
        """
        index = self._children.index(oldchild)
        self._children[index] = newchild
        self._remove_child_widget(oldchild)
        self._add_child_widget(newchild)
        self.update(newchild)

    def remove_child(self, child):
        """
        Remove the given child canvas widget.  ``child``'s parent will
        be set to None.

        :type child: CanvasWidget
        :param child: The child canvas widget to remove.
        """
        index = self._children.index(child)
        del self._children[index]
        self._remove_child_widget(child)
        if len(self._children) > 0:
            self.update(self._children[0])

    def insert_child(self, index, child):
        """
        Insert a child canvas widget before a given index.

        :type child: CanvasWidget
        :param child: The canvas widget that should be inserted.
        :type index: int
        :param index: The index where the child widget should be
            inserted.  In particular, the index of ``child`` will be
            ``index``; and the index of any children whose indices were
            greater than equal to ``index`` before ``child`` was
            inserted will be incremented by one.
        """
        self._children.insert(index, child)
        self._add_child_widget(child)


class StackWidget(CanvasWidget):
    """
    A canvas widget that keeps a list of canvas widgets in a vertical
    line.

    Attributes:
      - ``align``: The horizontal alignment of the children.  Possible
        values are ``'left'``, ``'center'``, and ``'right'``.  By
        default, children are center-aligned.
      - ``space``: The amount of vertical space to place between
        children.  By default, one pixel of space is used.
      - ``ordered``: If true, then keep the children in their
        original order.
    """

    def __init__(self, canvas, *children, **attribs):
        """
        Create a new stack widget.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :param children: The widgets that should be aligned
            vertically.  Each child must not have a parent.
        :type children: list(CanvasWidget)
        :param attribs: The new canvas widget's attributes.
        """
        self._align = "center"
        self._space = 1
        self._ordered = False
        self._children = list(children)
        for child in children:
            self._add_child_widget(child)
        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        if attr == "align":
            if value not in ("left", "right", "center"):
                raise ValueError("Bad alignment: %r" % value)
            self._align = value
        elif attr == "space":
            self._space = value
        elif attr == "ordered":
            self._ordered = value
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == "align":
            return self._align
        elif attr == "space":
            return self._space
        elif attr == "ordered":
            return self._ordered
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _tags(self):
        return []

    def _xalign(self, left, right):
        if self._align == "left":
            return left
        if self._align == "right":
            return right
        if self._align == "center":
            return (left + right) / 2

    def _update(self, child):
        # Align all children with child.
        (left, top, right, bot) = child.bbox()
        x = self._xalign(left, right)
        for c in self._children:
            (x1, y1, x2, y2) = c.bbox()
            c.move(x - self._xalign(x1, x2), 0)

        if self._ordered and len(self._children) > 1:
            index = self._children.index(child)

            y = bot + self._space
            for i in range(index + 1, len(self._children)):
                (x1, y1, x2, y2) = self._children[i].bbox()
                if y > y1:
                    self._children[i].move(0, y - y1)
                    y += y2 - y1 + self._space

            y = top - self._space
            for i in range(index - 1, -1, -1):
                (x1, y1, x2, y2) = self._children[i].bbox()
                if y < y2:
                    self._children[i].move(0, y - y2)
                    y -= y2 - y1 + self._space

    def _manage(self):
        if len(self._children) == 0:
            return
        child = self._children[0]

        # Align all children with child.
        (left, top, right, bot) = child.bbox()
        x = self._xalign(left, right)

        index = self._children.index(child)

        # Line up children below the child.
        y = bot + self._space
        for i in range(index + 1, len(self._children)):
            (x1, y1, x2, y2) = self._children[i].bbox()
            self._children[i].move(x - self._xalign(x1, x2), y - y1)
            y += y2 - y1 + self._space

        # Line up children above the child.
        y = top - self._space
        for i in range(index - 1, -1, -1):
            (x1, y1, x2, y2) = self._children[i].bbox()
            self._children[i].move(x - self._xalign(x1, x2), y - y2)
            y -= y2 - y1 + self._space

    def __repr__(self):
        return "[Stack: " + repr(self._children)[1:-1] + "]"

    # Provide an alias for the child_widgets() member.
    children = CanvasWidget.child_widgets

    def replace_child(self, oldchild, newchild):
        """
        Replace the child canvas widget ``oldchild`` with ``newchild``.
        ``newchild`` must not have a parent.  ``oldchild``'s parent will
        be set to None.

        :type oldchild: CanvasWidget
        :param oldchild: The child canvas widget to remove.
        :type newchild: CanvasWidget
        :param newchild: The canvas widget that should replace
            ``oldchild``.
        """
        index = self._children.index(oldchild)
        self._children[index] = newchild
        self._remove_child_widget(oldchild)
        self._add_child_widget(newchild)
        self.update(newchild)

    def remove_child(self, child):
        """
        Remove the given child canvas widget.  ``child``'s parent will
        be set to None.

        :type child: CanvasWidget
        :param child: The child canvas widget to remove.
        """
        index = self._children.index(child)
        del self._children[index]
        self._remove_child_widget(child)
        if len(self._children) > 0:
            self.update(self._children[0])

    def insert_child(self, index, child):
        """
        Insert a child canvas widget before a given index.

        :type child: CanvasWidget
        :param child: The canvas widget that should be inserted.
        :type index: int
        :param index: The index where the child widget should be
            inserted.  In particular, the index of ``child`` will be
            ``index``; and the index of any children whose indices were
            greater than equal to ``index`` before ``child`` was
            inserted will be incremented by one.
        """
        self._children.insert(index, child)
        self._add_child_widget(child)


class SpaceWidget(CanvasWidget):
    """
    A canvas widget that takes up space but does not display
    anything.  A ``SpaceWidget`` can be used to add space between
    elements.  Each space widget is characterized by a width and a
    height.  If you wish to only create horizontal space, then use a
    height of zero; and if you wish to only create vertical space, use
    a width of zero.
    """

    def __init__(self, canvas, width, height, **attribs):
        """
        Create a new space widget.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :type width: int
        :param width: The width of the new space widget.
        :type height: int
        :param height: The height of the new space widget.
        :param attribs: The new canvas widget's attributes.
        """
        # For some reason,
        if width > 4:
            width -= 4
        if height > 4:
            height -= 4
        self._tag = canvas.create_line(1, 1, width, height, fill="")
        CanvasWidget.__init__(self, canvas, **attribs)

    # note: width() and height() are already defined by CanvasWidget.
    def set_width(self, width):
        """
        Change the width of this space widget.

        :param width: The new width.
        :type width: int
        :rtype: None
        """
        [x1, y1, x2, y2] = self.bbox()
        self.canvas().coords(self._tag, x1, y1, x1 + width, y2)

    def set_height(self, height):
        """
        Change the height of this space widget.

        :param height: The new height.
        :type height: int
        :rtype: None
        """
        [x1, y1, x2, y2] = self.bbox()
        self.canvas().coords(self._tag, x1, y1, x2, y1 + height)

    def _tags(self):
        return [self._tag]

    def __repr__(self):
        return "[Space]"


class ScrollWatcherWidget(CanvasWidget):
    """
    A special canvas widget that adjusts its ``Canvas``'s scrollregion
    to always include the bounding boxes of all of its children.  The
    scroll-watcher widget will only increase the size of the
    ``Canvas``'s scrollregion; it will never decrease it.
    """

    def __init__(self, canvas, *children, **attribs):
        """
        Create a new scroll-watcher widget.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :type children: list(CanvasWidget)
        :param children: The canvas widgets watched by the
            scroll-watcher.  The scroll-watcher will ensure that these
            canvas widgets are always contained in their canvas's
            scrollregion.
        :param attribs: The new canvas widget's attributes.
        """
        for child in children:
            self._add_child_widget(child)
        CanvasWidget.__init__(self, canvas, **attribs)

    def add_child(self, canvaswidget):
        """
        Add a new canvas widget to the scroll-watcher.  The
        scroll-watcher will ensure that the new canvas widget is
        always contained in its canvas's scrollregion.

        :param canvaswidget: The new canvas widget.
        :type canvaswidget: CanvasWidget
        :rtype: None
        """
        self._add_child_widget(canvaswidget)
        self.update(canvaswidget)

    def remove_child(self, canvaswidget):
        """
        Remove a canvas widget from the scroll-watcher.  The
        scroll-watcher will no longer ensure that the new canvas
        widget is always contained in its canvas's scrollregion.

        :param canvaswidget: The canvas widget to remove.
        :type canvaswidget: CanvasWidget
        :rtype: None
        """
        self._remove_child_widget(canvaswidget)

    def _tags(self):
        return []

    def _update(self, child):
        self._adjust_scrollregion()

    def _adjust_scrollregion(self):
        """
        Adjust the scrollregion of this scroll-watcher's ``Canvas`` to
        include the bounding boxes of all of its children.
        """
        bbox = self.bbox()
        canvas = self.canvas()
        scrollregion = [int(n) for n in canvas["scrollregion"].split()]
        if len(scrollregion) != 4:
            return
        if (
            bbox[0] < scrollregion[0]
            or bbox[1] < scrollregion[1]
            or bbox[2] > scrollregion[2]
            or bbox[3] > scrollregion[3]
        ):
            scrollregion = "%d %d %d %d" % (
                min(bbox[0], scrollregion[0]),
                min(bbox[1], scrollregion[1]),
                max(bbox[2], scrollregion[2]),
                max(bbox[3], scrollregion[3]),
            )
            canvas["scrollregion"] = scrollregion


##//////////////////////////////////////////////////////
##  Canvas Frame
##//////////////////////////////////////////////////////


class CanvasFrame:
    """
    A ``Tkinter`` frame containing a canvas and scrollbars.
    ``CanvasFrame`` uses a ``ScrollWatcherWidget`` to ensure that all of
    the canvas widgets contained on its canvas are within its
    scrollregion.  In order for ``CanvasFrame`` to make these checks,
    all canvas widgets must be registered with ``add_widget`` when they
    are added to the canvas; and destroyed with ``destroy_widget`` when
    they are no longer needed.

    If a ``CanvasFrame`` is created with no parent, then it will create
    its own main window, including a "Done" button and a "Print"
    button.
    """

    def __init__(self, parent=None, **kw):
        """
        Create a new ``CanvasFrame``.

        :type parent: Tkinter.BaseWidget or Tkinter.Tk
        :param parent: The parent ``Tkinter`` widget.  If no parent is
            specified, then ``CanvasFrame`` will create a new main
            window.
        :param kw: Keyword arguments for the new ``Canvas``.  See the
            documentation for ``Tkinter.Canvas`` for more information.
        """
        # If no parent was given, set up a top-level window.
        if parent is None:
            self._parent = Tk()
            self._parent.title("NLTK")
            self._parent.bind("<Control-p>", lambda e: self.print_to_file())
            self._parent.bind("<Control-x>", self.destroy)
            self._parent.bind("<Control-q>", self.destroy)
        else:
            self._parent = parent

        # Create a frame for the canvas & scrollbars
        self._frame = frame = Frame(self._parent)
        self._canvas = canvas = Canvas(frame, **kw)
        xscrollbar = Scrollbar(self._frame, orient="horizontal")
        yscrollbar = Scrollbar(self._frame, orient="vertical")
        xscrollbar["command"] = canvas.xview
        yscrollbar["command"] = canvas.yview
        canvas["xscrollcommand"] = xscrollbar.set
        canvas["yscrollcommand"] = yscrollbar.set
        yscrollbar.pack(fill="y", side="right")
        xscrollbar.pack(fill="x", side="bottom")
        canvas.pack(expand=1, fill="both", side="left")

        # Set initial scroll region.
        scrollregion = "0 0 {} {}".format(canvas["width"], canvas["height"])
        canvas["scrollregion"] = scrollregion

        self._scrollwatcher = ScrollWatcherWidget(canvas)

        # If no parent was given, pack the frame, and add a menu.
        if parent is None:
            self.pack(expand=1, fill="both")
            self._init_menubar()

    def _init_menubar(self):
        menubar = Menu(self._parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Print to Postscript",
            underline=0,
            command=self.print_to_file,
            accelerator="Ctrl-p",
        )
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        self._parent.config(menu=menubar)

    def print_to_file(self, filename=None):
        """
        Print the contents of this ``CanvasFrame`` to a postscript
        file.  If no filename is given, then prompt the user for one.

        :param filename: The name of the file to print the tree to.
        :type filename: str
        :rtype: None
        """
        if filename is None:
            ftypes = [("Postscript files", ".ps"), ("All files", "*")]
            filename = asksaveasfilename(filetypes=ftypes, defaultextension=".ps")
            if not filename:
                return
        (x0, y0, w, h) = self.scrollregion()
        postscript = self._canvas.postscript(
            x=x0,
            y=y0,
            width=w + 2,
            height=h + 2,
            pagewidth=w + 2,  # points = 1/72 inch
            pageheight=h + 2,  # points = 1/72 inch
            pagex=0,
            pagey=0,
        )
        # workaround for bug in Tk font handling
        postscript = postscript.replace(" 0 scalefont ", " 9 scalefont ")
        with open(filename, "wb") as f:
            f.write(postscript.encode("utf8"))

    def scrollregion(self):
        """
        :return: The current scroll region for the canvas managed by
            this ``CanvasFrame``.
        :rtype: 4-tuple of int
        """
        (x1, y1, x2, y2) = self._canvas["scrollregion"].split()
        return (int(x1), int(y1), int(x2), int(y2))

    def canvas(self):
        """
        :return: The canvas managed by this ``CanvasFrame``.
        :rtype: Tkinter.Canvas
        """
        return self._canvas

    def add_widget(self, canvaswidget, x=None, y=None):
        """
        Register a canvas widget with this ``CanvasFrame``.  The
        ``CanvasFrame`` will ensure that this canvas widget is always
        within the ``Canvas``'s scrollregion.  If no coordinates are
        given for the canvas widget, then the ``CanvasFrame`` will
        attempt to find a clear area of the canvas for it.

        :type canvaswidget: CanvasWidget
        :param canvaswidget: The new canvas widget.  ``canvaswidget``
            must have been created on this ``CanvasFrame``'s canvas.
        :type x: int
        :param x: The initial x coordinate for the upper left hand
            corner of ``canvaswidget``, in the canvas's coordinate
            space.
        :type y: int
        :param y: The initial y coordinate for the upper left hand
            corner of ``canvaswidget``, in the canvas's coordinate
            space.
        """
        if x is None or y is None:
            (x, y) = self._find_room(canvaswidget, x, y)

        # Move to (x,y)
        (x1, y1, x2, y2) = canvaswidget.bbox()
        canvaswidget.move(x - x1, y - y1)

        # Register with scrollwatcher.
        self._scrollwatcher.add_child(canvaswidget)

    def _find_room(self, widget, desired_x, desired_y):
        """
        Try to find a space for a given widget.
        """
        (left, top, right, bot) = self.scrollregion()
        w = widget.width()
        h = widget.height()

        if w >= (right - left):
            return (0, 0)
        if h >= (bot - top):
            return (0, 0)

        # Move the widget out of the way, for now.
        (x1, y1, x2, y2) = widget.bbox()
        widget.move(left - x2 - 50, top - y2 - 50)

        if desired_x is not None:
            x = desired_x
            for y in range(top, bot - h, int((bot - top - h) / 10)):
                if not self._canvas.find_overlapping(
                    x - 5, y - 5, x + w + 5, y + h + 5
                ):
                    return (x, y)

        if desired_y is not None:
            y = desired_y
            for x in range(left, right - w, int((right - left - w) / 10)):
                if not self._canvas.find_overlapping(
                    x - 5, y - 5, x + w + 5, y + h + 5
                ):
                    return (x, y)

        for y in range(top, bot - h, int((bot - top - h) / 10)):
            for x in range(left, right - w, int((right - left - w) / 10)):
                if not self._canvas.find_overlapping(
                    x - 5, y - 5, x + w + 5, y + h + 5
                ):
                    return (x, y)
        return (0, 0)

    def destroy_widget(self, canvaswidget):
        """
        Remove a canvas widget from this ``CanvasFrame``.  This
        deregisters the canvas widget, and destroys it.
        """
        self.remove_widget(canvaswidget)
        canvaswidget.destroy()

    def remove_widget(self, canvaswidget):
        # Deregister with scrollwatcher.
        self._scrollwatcher.remove_child(canvaswidget)

    def pack(self, cnf={}, **kw):
        """
        Pack this ``CanvasFrame``.  See the documentation for
        ``Tkinter.Pack`` for more information.
        """
        self._frame.pack(cnf, **kw)
        # Adjust to be big enough for kids?

    def destroy(self, *e):
        """
        Destroy this ``CanvasFrame``.  If this ``CanvasFrame`` created a
        top-level window, then this will close that window.
        """
        if self._parent is None:
            return
        self._parent.destroy()
        self._parent = None

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this frame is created from a non-interactive program (e.g.
        from a secript); otherwise, the frame will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._parent.mainloop(*args, **kwargs)


##//////////////////////////////////////////////////////
##  Text display
##//////////////////////////////////////////////////////


class ShowText:
    """
    A ``Tkinter`` window used to display a text.  ``ShowText`` is
    typically used by graphical tools to display help text, or similar
    information.
    """

    def __init__(self, root, title, text, width=None, height=None, **textbox_options):
        if width is None or height is None:
            (width, height) = self.find_dimentions(text, width, height)

        # Create the main window.
        if root is None:
            self._top = top = Tk()
        else:
            self._top = top = Toplevel(root)
        top.title(title)

        b = Button(top, text="Ok", command=self.destroy)
        b.pack(side="bottom")

        tbf = Frame(top)
        tbf.pack(expand=1, fill="both")
        scrollbar = Scrollbar(tbf, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        textbox = Text(tbf, wrap="word", width=width, height=height, **textbox_options)
        textbox.insert("end", text)
        textbox["state"] = "disabled"
        textbox.pack(side="left", expand=1, fill="both")
        scrollbar["command"] = textbox.yview
        textbox["yscrollcommand"] = scrollbar.set

        # Make it easy to close the window.
        top.bind("q", self.destroy)
        top.bind("x", self.destroy)
        top.bind("c", self.destroy)
        top.bind("<Return>", self.destroy)
        top.bind("<Escape>", self.destroy)

        # Focus the scrollbar, so they can use up/down, etc.
        scrollbar.focus()

    def find_dimentions(self, text, width, height):
        lines = text.split("\n")
        if width is None:
            maxwidth = max(len(line) for line in lines)
            width = min(maxwidth, 80)

        # Now, find height.
        height = 0
        for line in lines:
            while len(line) > width:
                brk = line[:width].rfind(" ")
                line = line[brk:]
                height += 1
            height += 1
        height = min(height, 25)

        return (width, height)

    def destroy(self, *e):
        if self._top is None:
            return
        self._top.destroy()
        self._top = None

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this window is created from a non-interactive program (e.g.
        from a secript); otherwise, the window will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._top.mainloop(*args, **kwargs)


##//////////////////////////////////////////////////////
##  Entry dialog
##//////////////////////////////////////////////////////


class EntryDialog:
    """
    A dialog box for entering
    """

    def __init__(
        self, parent, original_text="", instructions="", set_callback=None, title=None
    ):
        self._parent = parent
        self._original_text = original_text
        self._set_callback = set_callback

        width = int(max(30, len(original_text) * 3 / 2))
        self._top = Toplevel(parent)

        if title:
            self._top.title(title)

        # The text entry box.
        entryframe = Frame(self._top)
        entryframe.pack(expand=1, fill="both", padx=5, pady=5, ipady=10)
        if instructions:
            l = Label(entryframe, text=instructions)
            l.pack(side="top", anchor="w", padx=30)
        self._entry = Entry(entryframe, width=width)
        self._entry.pack(expand=1, fill="x", padx=30)
        self._entry.insert(0, original_text)

        # A divider
        divider = Frame(self._top, borderwidth=1, relief="sunken")
        divider.pack(fill="x", ipady=1, padx=10)

        # The buttons.
        buttons = Frame(self._top)
        buttons.pack(expand=0, fill="x", padx=5, pady=5)
        b = Button(buttons, text="Cancel", command=self._cancel, width=8)
        b.pack(side="right", padx=5)
        b = Button(buttons, text="Ok", command=self._ok, width=8, default="active")
        b.pack(side="left", padx=5)
        b = Button(buttons, text="Apply", command=self._apply, width=8)
        b.pack(side="left")

        self._top.bind("<Return>", self._ok)
        self._top.bind("<Control-q>", self._cancel)
        self._top.bind("<Escape>", self._cancel)

        self._entry.focus()

    def _reset(self, *e):
        self._entry.delete(0, "end")
        self._entry.insert(0, self._original_text)
        if self._set_callback:
            self._set_callback(self._original_text)

    def _cancel(self, *e):
        try:
            self._reset()
        except:
            pass
        self._destroy()

    def _ok(self, *e):
        self._apply()
        self._destroy()

    def _apply(self, *e):
        if self._set_callback:
            self._set_callback(self._entry.get())

    def _destroy(self, *e):
        if self._top is None:
            return
        self._top.destroy()
        self._top = None


##//////////////////////////////////////////////////////
##  Colorized List
##//////////////////////////////////////////////////////


class ColorizedList:
    """
    An abstract base class for displaying a colorized list of items.
    Subclasses should define:

    - ``_init_colortags``, which sets up Text color tags that
      will be used by the list.
    - ``_item_repr``, which returns a list of (text,colortag)
      tuples that make up the colorized representation of the
      item.

    :note: Typically, you will want to register a callback for
        ``'select'`` that calls ``mark`` on the given item.
    """

    def __init__(self, parent, items=[], **options):
        """
        Construct a new list.

        :param parent: The Tk widget that contains the colorized list
        :param items: The initial contents of the colorized list.
        :param options:
        """
        self._parent = parent
        self._callbacks = {}

        # Which items are marked?
        self._marks = {}

        # Initialize the Tkinter frames.
        self._init_itemframe(options.copy())

        # Set up key & mouse bindings.
        self._textwidget.bind("<KeyPress>", self._keypress)
        self._textwidget.bind("<ButtonPress>", self._buttonpress)

        # Fill in the given CFG's items.
        self._items = None
        self.set(items)

    # ////////////////////////////////////////////////////////////
    # Abstract methods
    # ////////////////////////////////////////////////////////////
    @abstractmethod
    def _init_colortags(self, textwidget, options):
        """
        Set up any colortags that will be used by this colorized list.
        E.g.:
            textwidget.tag_config('terminal', foreground='black')
        """

    @abstractmethod
    def _item_repr(self, item):
        """
        Return a list of (text, colortag) tuples that make up the
        colorized representation of the item.  Colorized
        representations may not span multiple lines.  I.e., the text
        strings returned may not contain newline characters.
        """

    # ////////////////////////////////////////////////////////////
    # Item Access
    # ////////////////////////////////////////////////////////////

    def get(self, index=None):
        """
        :return: A list of the items contained by this list.
        """
        if index is None:
            return self._items[:]
        else:
            return self._items[index]

    def set(self, items):
        """
        Modify the list of items contained by this list.
        """
        items = list(items)
        if self._items == items:
            return
        self._items = list(items)

        self._textwidget["state"] = "normal"
        self._textwidget.delete("1.0", "end")
        for item in items:
            for text, colortag in self._item_repr(item):
                assert "\n" not in text, "item repr may not contain newline"
                self._textwidget.insert("end", text, colortag)
            self._textwidget.insert("end", "\n")
        # Remove the final newline
        self._textwidget.delete("end-1char", "end")
        self._textwidget.mark_set("insert", "1.0")
        self._textwidget["state"] = "disabled"
        # Clear all marks
        self._marks.clear()

    def unmark(self, item=None):
        """
        Remove highlighting from the given item; or from every item,
        if no item is given.
        :raise ValueError: If ``item`` is not contained in the list.
        :raise KeyError: If ``item`` is not marked.
        """
        if item is None:
            self._marks.clear()
            self._textwidget.tag_remove("highlight", "1.0", "end+1char")
        else:
            index = self._items.index(item)
            del self._marks[item]
            (start, end) = ("%d.0" % (index + 1), "%d.0" % (index + 2))
            self._textwidget.tag_remove("highlight", start, end)

    def mark(self, item):
        """
        Highlight the given item.
        :raise ValueError: If ``item`` is not contained in the list.
        """
        self._marks[item] = 1
        index = self._items.index(item)
        (start, end) = ("%d.0" % (index + 1), "%d.0" % (index + 2))
        self._textwidget.tag_add("highlight", start, end)

    def markonly(self, item):
        """
        Remove any current highlighting, and mark the given item.
        :raise ValueError: If ``item`` is not contained in the list.
        """
        self.unmark()
        self.mark(item)

    def view(self, item):
        """
        Adjust the view such that the given item is visible.  If
        the item is already visible, then do nothing.
        """
        index = self._items.index(item)
        self._textwidget.see("%d.0" % (index + 1))

    # ////////////////////////////////////////////////////////////
    # Callbacks
    # ////////////////////////////////////////////////////////////

    def add_callback(self, event, func):
        """
        Register a callback function with the list.  This function
        will be called whenever the given event occurs.

        :param event: The event that will trigger the callback
            function.  Valid events are: click1, click2, click3,
            space, return, select, up, down, next, prior, move
        :param func: The function that should be called when
            the event occurs.  ``func`` will be called with a
            single item as its argument.  (The item selected
            or the item moved to).
        """
        if event == "select":
            events = ["click1", "space", "return"]
        elif event == "move":
            events = ["up", "down", "next", "prior"]
        else:
            events = [event]

        for e in events:
            self._callbacks.setdefault(e, {})[func] = 1

    def remove_callback(self, event, func=None):
        """
        Deregister a callback function.  If ``func`` is none, then
        all callbacks are removed for the given event.
        """
        if event is None:
            events = list(self._callbacks.keys())
        elif event == "select":
            events = ["click1", "space", "return"]
        elif event == "move":
            events = ["up", "down", "next", "prior"]
        else:
            events = [event]

        for e in events:
            if func is None:
                del self._callbacks[e]
            else:
                try:
                    del self._callbacks[e][func]
                except:
                    pass

    # ////////////////////////////////////////////////////////////
    # Tkinter Methods
    # ////////////////////////////////////////////////////////////

    def pack(self, cnf={}, **kw):
        #        "@include: Tkinter.Pack.pack"
        self._itemframe.pack(cnf, **kw)

    def grid(self, cnf={}, **kw):
        #        "@include: Tkinter.Grid.grid"
        self._itemframe.grid(cnf, *kw)

    def focus(self):
        #        "@include: Tkinter.Widget.focus"
        self._textwidget.focus()

    # ////////////////////////////////////////////////////////////
    # Internal Methods
    # ////////////////////////////////////////////////////////////

    def _init_itemframe(self, options):
        self._itemframe = Frame(self._parent)

        # Create the basic Text widget & scrollbar.
        options.setdefault("background", "#e0e0e0")
        self._textwidget = Text(self._itemframe, **options)
        self._textscroll = Scrollbar(self._itemframe, takefocus=0, orient="vertical")
        self._textwidget.config(yscrollcommand=self._textscroll.set)
        self._textscroll.config(command=self._textwidget.yview)
        self._textscroll.pack(side="right", fill="y")
        self._textwidget.pack(expand=1, fill="both", side="left")

        # Initialize the colorization tags
        self._textwidget.tag_config(
            "highlight", background="#e0ffff", border="1", relief="raised"
        )
        self._init_colortags(self._textwidget, options)

        # How do I want to mark keyboard selection?
        self._textwidget.tag_config("sel", foreground="")
        self._textwidget.tag_config(
            "sel", foreground="", background="", border="", underline=1
        )
        self._textwidget.tag_lower("highlight", "sel")

    def _fire_callback(self, event, itemnum):
        if event not in self._callbacks:
            return
        if 0 <= itemnum < len(self._items):
            item = self._items[itemnum]
        else:
            item = None
        for cb_func in list(self._callbacks[event].keys()):
            cb_func(item)

    def _buttonpress(self, event):
        clickloc = "@%d,%d" % (event.x, event.y)
        insert_point = self._textwidget.index(clickloc)
        itemnum = int(insert_point.split(".")[0]) - 1
        self._fire_callback("click%d" % event.num, itemnum)

    def _keypress(self, event):
        if event.keysym == "Return" or event.keysym == "space":
            insert_point = self._textwidget.index("insert")
            itemnum = int(insert_point.split(".")[0]) - 1
            self._fire_callback(event.keysym.lower(), itemnum)
            return
        elif event.keysym == "Down":
            delta = "+1line"
        elif event.keysym == "Up":
            delta = "-1line"
        elif event.keysym == "Next":
            delta = "+10lines"
        elif event.keysym == "Prior":
            delta = "-10lines"
        else:
            return "continue"

        self._textwidget.mark_set("insert", "insert" + delta)
        self._textwidget.see("insert")
        self._textwidget.tag_remove("sel", "1.0", "end+1char")
        self._textwidget.tag_add("sel", "insert linestart", "insert lineend")

        insert_point = self._textwidget.index("insert")
        itemnum = int(insert_point.split(".")[0]) - 1
        self._fire_callback(event.keysym.lower(), itemnum)

        return "break"


##//////////////////////////////////////////////////////
##  Improved OptionMenu
##//////////////////////////////////////////////////////


class MutableOptionMenu(Menubutton):
    def __init__(self, master, values, **options):
        self._callback = options.get("command")
        if "command" in options:
            del options["command"]

        # Create a variable
        self._variable = variable = StringVar()
        if len(values) > 0:
            variable.set(values[0])

        kw = {
            "borderwidth": 2,
            "textvariable": variable,
            "indicatoron": 1,
            "relief": RAISED,
            "anchor": "c",
            "highlightthickness": 2,
        }
        kw.update(options)
        Widget.__init__(self, master, "menubutton", kw)
        self.widgetName = "tk_optionMenu"
        self._menu = Menu(self, name="menu", tearoff=0)
        self.menuname = self._menu._w

        self._values = []
        for value in values:
            self.add(value)

        self["menu"] = self._menu

    def add(self, value):
        if value in self._values:
            return

        def set(value=value):
            self.set(value)

        self._menu.add_command(label=value, command=set)
        self._values.append(value)

    def set(self, value):
        self._variable.set(value)
        if self._callback:
            self._callback(value)

    def remove(self, value):
        # Might raise indexerror: pass to parent.
        i = self._values.index(value)
        del self._values[i]
        self._menu.delete(i, i)

    def __getitem__(self, name):
        if name == "menu":
            return self.__menu
        return Widget.__getitem__(self, name)

    def destroy(self):
        """Destroy this widget and the associated menu."""
        Menubutton.destroy(self)
        self._menu = None


##//////////////////////////////////////////////////////
##  Test code.
##//////////////////////////////////////////////////////


def demo():
    """
    A simple demonstration showing how to use canvas widgets.
    """

    def fill(cw):
        from random import randint

        cw["fill"] = "#00%04d" % randint(0, 9999)

    def color(cw):
        from random import randint

        cw["color"] = "#ff%04d" % randint(0, 9999)

    cf = CanvasFrame(closeenough=10, width=300, height=300)
    c = cf.canvas()
    ct3 = TextWidget(c, "hiya there", draggable=1)
    ct2 = TextWidget(c, "o  o\n||\n___\n  U", draggable=1, justify="center")
    co = OvalWidget(c, ct2, outline="red")
    ct = TextWidget(c, "o  o\n||\n\\___/", draggable=1, justify="center")
    cp = ParenWidget(c, ct, color="red")
    cb = BoxWidget(c, cp, fill="cyan", draggable=1, width=3, margin=10)
    equation = SequenceWidget(
        c,
        SymbolWidget(c, "forall"),
        TextWidget(c, "x"),
        SymbolWidget(c, "exists"),
        TextWidget(c, "y: "),
        TextWidget(c, "x"),
        SymbolWidget(c, "notequal"),
        TextWidget(c, "y"),
    )
    space = SpaceWidget(c, 0, 30)
    cstack = StackWidget(c, cb, ct3, space, co, equation, align="center")
    prompt_msg = TextWidget(
        c, "try clicking\nand dragging", draggable=1, justify="center"
    )
    cs = SequenceWidget(c, cstack, prompt_msg)
    zz = BracketWidget(c, cs, color="green4", width=3)
    cf.add_widget(zz, 60, 30)

    cb.bind_click(fill)
    ct.bind_click(color)
    co.bind_click(fill)
    ct2.bind_click(color)
    ct3.bind_click(color)

    cf.mainloop()
    # ShowText(None, 'title', ((('this is text'*150)+'\n')*5))


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\matplotlib\collections.py ===
"""
Classes for the efficient drawing of large collections of objects that
share most properties, e.g., a large number of line segments or
polygons.

The classes are not meant to be as flexible as their single element
counterparts (e.g., you may not be able to select all line styles) but
they are meant to be fast for common use cases (e.g., a large set of solid
line segments).
"""

import itertools
import functools
import math
from numbers import Number, Real
import warnings

import numpy as np

import matplotlib as mpl
from . import (_api, _path, artist, cbook, colorizer as mcolorizer, colors as mcolors,
               _docstring, hatch as mhatch, lines as mlines, path as mpath, transforms)
from ._enums import JoinStyle, CapStyle


# "color" is excluded; it is a compound setter, and its docstring differs
# in LineCollection.
@_api.define_aliases({
    "antialiased": ["antialiaseds", "aa"],
    "edgecolor": ["edgecolors", "ec"],
    "facecolor": ["facecolors", "fc"],
    "linestyle": ["linestyles", "dashes", "ls"],
    "linewidth": ["linewidths", "lw"],
    "offset_transform": ["transOffset"],
})
class Collection(mcolorizer.ColorizingArtist):
    r"""
    Base class for Collections. Must be subclassed to be usable.

    A Collection represents a sequence of `.Patch`\es that can be drawn
    more efficiently together than individually. For example, when a single
    path is being drawn repeatedly at different offsets, the renderer can
    typically execute a ``draw_marker()`` call much more efficiently than a
    series of repeated calls to ``draw_path()`` with the offsets put in
    one-by-one.

    Most properties of a collection can be configured per-element. Therefore,
    Collections have "plural" versions of many of the properties of a `.Patch`
    (e.g. `.Collection.get_paths` instead of `.Patch.get_path`). Exceptions are
    the *zorder*, *hatch*, *pickradius*, *capstyle* and *joinstyle* properties,
    which can only be set globally for the whole collection.

    Besides these exceptions, all properties can be specified as single values
    (applying to all elements) or sequences of values. The property of the
    ``i``\th element of the collection is::

      prop[i % len(prop)]

    Each Collection can optionally be used as its own `.ScalarMappable` by
    passing the *norm* and *cmap* parameters to its constructor. If the
    Collection's `.ScalarMappable` matrix ``_A`` has been set (via a call
    to `.Collection.set_array`), then at draw time this internal scalar
    mappable will be used to set the ``facecolors`` and ``edgecolors``,
    ignoring those that were manually passed in.
    """
    #: Either a list of 3x3 arrays or an Nx3x3 array (representing N
    #: transforms), suitable for the `all_transforms` argument to
    #: `~matplotlib.backend_bases.RendererBase.draw_path_collection`;
    #: each 3x3 array is used to initialize an
    #: `~matplotlib.transforms.Affine2D` object.
    #: Each kind of collection defines this based on its arguments.
    _transforms = np.empty((0, 3, 3))

    # Whether to draw an edge by default.  Set on a
    # subclass-by-subclass basis.
    _edge_default = False

    @_docstring.interpd
    def __init__(self, *,
                 edgecolors=None,
                 facecolors=None,
                 linewidths=None,
                 linestyles='solid',
                 capstyle=None,
                 joinstyle=None,
                 antialiaseds=None,
                 offsets=None,
                 offset_transform=None,
                 norm=None,  # optional for ScalarMappable
                 cmap=None,  # ditto
                 colorizer=None,
                 pickradius=5.0,
                 hatch=None,
                 urls=None,
                 zorder=1,
                 **kwargs
                 ):
        """
        Parameters
        ----------
        edgecolors : :mpltype:`color` or list of colors, default: :rc:`patch.edgecolor`
            Edge color for each patch making up the collection. The special
            value 'face' can be passed to make the edgecolor match the
            facecolor.
        facecolors : :mpltype:`color` or list of colors, default: :rc:`patch.facecolor`
            Face color for each patch making up the collection.
        linewidths : float or list of floats, default: :rc:`patch.linewidth`
            Line width for each patch making up the collection.
        linestyles : str or tuple or list thereof, default: 'solid'
            Valid strings are ['solid', 'dashed', 'dashdot', 'dotted', '-',
            '--', '-.', ':']. Dash tuples should be of the form::

                (offset, onoffseq),

            where *onoffseq* is an even length tuple of on and off ink lengths
            in points. For examples, see
            :doc:`/gallery/lines_bars_and_markers/linestyles`.
        capstyle : `.CapStyle`-like, default: 'butt'
            Style to use for capping lines for all paths in the collection.
            Allowed values are %(CapStyle)s.
        joinstyle : `.JoinStyle`-like, default: 'round'
            Style to use for joining lines for all paths in the collection.
            Allowed values are %(JoinStyle)s.
        antialiaseds : bool or list of bool, default: :rc:`patch.antialiased`
            Whether each patch in the collection should be drawn with
            antialiasing.
        offsets : (float, float) or list thereof, default: (0, 0)
            A vector by which to translate each patch after rendering (default
            is no translation). The translation is performed in screen (pixel)
            coordinates (i.e. after the Artist's transform is applied).
        offset_transform : `~.Transform`, default: `.IdentityTransform`
            A single transform which will be applied to each *offsets* vector
            before it is used.
        cmap, norm
            Data normalization and colormapping parameters. See
            `.ScalarMappable` for a detailed description.
        hatch : str, optional
            Hatching pattern to use in filled paths, if any. Valid strings are
            ['/', '\\', '|', '-', '+', 'x', 'o', 'O', '.', '*']. See
            :doc:`/gallery/shapes_and_collections/hatch_style_reference` for
            the meaning of each hatch type.
        pickradius : float, default: 5.0
            If ``pickradius <= 0``, then `.Collection.contains` will return
            ``True`` whenever the test point is inside of one of the polygons
            formed by the control points of a Path in the Collection. On the
            other hand, if it is greater than 0, then we instead check if the
            test point is contained in a stroke of width ``2*pickradius``
            following any of the Paths in the Collection.
        urls : list of str, default: None
            A URL for each patch to link to once drawn. Currently only works
            for the SVG backend. See :doc:`/gallery/misc/hyperlinks_sgskip` for
            examples.
        zorder : float, default: 1
            The drawing order, shared by all Patches in the Collection. See
            :doc:`/gallery/misc/zorder_demo` for all defaults and examples.
        **kwargs
            Remaining keyword arguments will be used to set properties as
            ``Collection.set_{key}(val)`` for each key-value pair in *kwargs*.
        """

        super().__init__(self._get_colorizer(cmap, norm, colorizer))
        # list of un-scaled dash patterns
        # this is needed scaling the dash pattern by linewidth
        self._us_linestyles = [(0, None)]
        # list of dash patterns
        self._linestyles = [(0, None)]
        # list of unbroadcast/scaled linewidths
        self._us_lw = [0]
        self._linewidths = [0]

        self._gapcolor = None  # Currently only used by LineCollection.

        # Flags set by _set_mappable_flags: are colors from mapping an array?
        self._face_is_mapped = None
        self._edge_is_mapped = None
        self._mapped_colors = None  # calculated in update_scalarmappable
        self._hatch_color = mcolors.to_rgba(mpl.rcParams['hatch.color'])
        self._hatch_linewidth = mpl.rcParams['hatch.linewidth']
        self.set_facecolor(facecolors)
        self.set_edgecolor(edgecolors)
        self.set_linewidth(linewidths)
        self.set_linestyle(linestyles)
        self.set_antialiased(antialiaseds)
        self.set_pickradius(pickradius)
        self.set_urls(urls)
        self.set_hatch(hatch)
        self.set_zorder(zorder)

        if capstyle:
            self.set_capstyle(capstyle)
        else:
            self._capstyle = None

        if joinstyle:
            self.set_joinstyle(joinstyle)
        else:
            self._joinstyle = None

        if offsets is not None:
            offsets = np.asanyarray(offsets, float)
            # Broadcast (2,) -> (1, 2) but nothing else.
            if offsets.shape == (2,):
                offsets = offsets[None, :]

        self._offsets = offsets
        self._offset_transform = offset_transform

        self._path_effects = None
        self._internal_update(kwargs)
        self._paths = None

    def get_paths(self):
        return self._paths

    def set_paths(self, paths):
        self._paths = paths
        self.stale = True

    def get_transforms(self):
        return self._transforms

    def get_offset_transform(self):
        """Return the `.Transform` instance used by this artist offset."""
        if self._offset_transform is None:
            self._offset_transform = transforms.IdentityTransform()
        elif (not isinstance(self._offset_transform, transforms.Transform)
              and hasattr(self._offset_transform, '_as_mpl_transform')):
            self._offset_transform = \
                self._offset_transform._as_mpl_transform(self.axes)
        return self._offset_transform

    def set_offset_transform(self, offset_transform):
        """
        Set the artist offset transform.

        Parameters
        ----------
        offset_transform : `.Transform`
        """
        self._offset_transform = offset_transform

    def get_datalim(self, transData):
        # Calculate the data limits and return them as a `.Bbox`.
        #
        # This operation depends on the transforms for the data in the
        # collection and whether the collection has offsets:
        #
        # 1. offsets = None, transform child of transData: use the paths for
        # the automatic limits (i.e. for LineCollection in streamline).
        # 2. offsets != None: offset_transform is child of transData:
        #
        #    a. transform is child of transData: use the path + offset for
        #       limits (i.e for bar).
        #    b. transform is not a child of transData: just use the offsets
        #       for the limits (i.e. for scatter)
        #
        # 3. otherwise return a null Bbox.

        transform = self.get_transform()
        offset_trf = self.get_offset_transform()
        if not (isinstance(offset_trf, transforms.IdentityTransform)
                or offset_trf.contains_branch(transData)):
            # if the offsets are in some coords other than data,
            # then don't use them for autoscaling.
            return transforms.Bbox.null()

        paths = self.get_paths()
        if not len(paths):
            # No paths to transform
            return transforms.Bbox.null()

        if not transform.is_affine:
            paths = [transform.transform_path_non_affine(p) for p in paths]
            # Don't convert transform to transform.get_affine() here because
            # we may have transform.contains_branch(transData) but not
            # transforms.get_affine().contains_branch(transData).  But later,
            # be careful to only apply the affine part that remains.

        offsets = self.get_offsets()

        if any(transform.contains_branch_seperately(transData)):
            # collections that are just in data units (like quiver)
            # can properly have the axes limits set by their shape +
            # offset.  LineCollections that have no offsets can
            # also use this algorithm (like streamplot).
            if isinstance(offsets, np.ma.MaskedArray):
                offsets = offsets.filled(np.nan)
                # get_path_collection_extents handles nan but not masked arrays
            return mpath.get_path_collection_extents(
                transform.get_affine() - transData, paths,
                self.get_transforms(),
                offset_trf.transform_non_affine(offsets),
                offset_trf.get_affine().frozen())

        # NOTE: None is the default case where no offsets were passed in
        if self._offsets is not None:
            # this is for collections that have their paths (shapes)
            # in physical, axes-relative, or figure-relative units
            # (i.e. like scatter). We can't uniquely set limits based on
            # those shapes, so we just set the limits based on their
            # location.
            offsets = (offset_trf - transData).transform(offsets)
            # note A-B means A B^{-1}
            offsets = np.ma.masked_invalid(offsets)
            if not offsets.mask.all():
                bbox = transforms.Bbox.null()
                bbox.update_from_data_xy(offsets)
                return bbox
        return transforms.Bbox.null()

    def get_window_extent(self, renderer=None):
        # TODO: check to ensure that this does not fail for
        # cases other than scatter plot legend
        return self.get_datalim(transforms.IdentityTransform())

    def _prepare_points(self):
        # Helper for drawing and hit testing.

        transform = self.get_transform()
        offset_trf = self.get_offset_transform()
        offsets = self.get_offsets()
        paths = self.get_paths()

        if self.have_units():
            paths = []
            for path in self.get_paths():
                vertices = path.vertices
                xs, ys = vertices[:, 0], vertices[:, 1]
                xs = self.convert_xunits(xs)
                ys = self.convert_yunits(ys)
                paths.append(mpath.Path(np.column_stack([xs, ys]), path.codes))
            xs = self.convert_xunits(offsets[:, 0])
            ys = self.convert_yunits(offsets[:, 1])
            offsets = np.ma.column_stack([xs, ys])

        if not transform.is_affine:
            paths = [transform.transform_path_non_affine(path)
                     for path in paths]
            transform = transform.get_affine()
        if not offset_trf.is_affine:
            offsets = offset_trf.transform_non_affine(offsets)
            # This might have changed an ndarray into a masked array.
            offset_trf = offset_trf.get_affine()

        if isinstance(offsets, np.ma.MaskedArray):
            offsets = offsets.filled(np.nan)
            # Changing from a masked array to nan-filled ndarray
            # is probably most efficient at this point.

        return transform, offset_trf, offsets, paths

    @artist.allow_rasterization
    def draw(self, renderer):
        if not self.get_visible():
            return
        renderer.open_group(self.__class__.__name__, self.get_gid())

        self.update_scalarmappable()

        transform, offset_trf, offsets, paths = self._prepare_points()

        gc = renderer.new_gc()
        self._set_gc_clip(gc)
        gc.set_snap(self.get_snap())

        if self._hatch:
            gc.set_hatch(self._hatch)
            gc.set_hatch_color(self._hatch_color)
            gc.set_hatch_linewidth(self._hatch_linewidth)

        if self.get_sketch_params() is not None:
            gc.set_sketch_params(*self.get_sketch_params())

        if self.get_path_effects():
            from matplotlib.patheffects import PathEffectRenderer
            renderer = PathEffectRenderer(self.get_path_effects(), renderer)

        # If the collection is made up of a single shape/color/stroke,
        # it can be rendered once and blitted multiple times, using
        # `draw_markers` rather than `draw_path_collection`.  This is
        # *much* faster for Agg, and results in smaller file sizes in
        # PDF/SVG/PS.

        trans = self.get_transforms()
        facecolors = self.get_facecolor()
        edgecolors = self.get_edgecolor()
        do_single_path_optimization = False
        if (len(paths) == 1 and len(trans) <= 1 and
                len(facecolors) == 1 and len(edgecolors) == 1 and
                len(self._linewidths) == 1 and
                all(ls[1] is None for ls in self._linestyles) and
                len(self._antialiaseds) == 1 and len(self._urls) == 1 and
                self.get_hatch() is None):
            if len(trans):
                combined_transform = transforms.Affine2D(trans[0]) + transform
            else:
                combined_transform = transform
            extents = paths[0].get_extents(combined_transform)
            if (extents.width < self.get_figure(root=True).bbox.width
                    and extents.height < self.get_figure(root=True).bbox.height):
                do_single_path_optimization = True

        if self._joinstyle:
            gc.set_joinstyle(self._joinstyle)

        if self._capstyle:
            gc.set_capstyle(self._capstyle)

        if do_single_path_optimization:
            gc.set_foreground(tuple(edgecolors[0]))
            gc.set_linewidth(self._linewidths[0])
            gc.set_dashes(*self._linestyles[0])
            gc.set_antialiased(self._antialiaseds[0])
            gc.set_url(self._urls[0])
            renderer.draw_markers(
                gc, paths[0], combined_transform.frozen(),
                mpath.Path(offsets), offset_trf, tuple(facecolors[0]))
        else:
            if self._gapcolor is not None:
                # First draw paths within the gaps.
                ipaths, ilinestyles = self._get_inverse_paths_linestyles()
                renderer.draw_path_collection(
                    gc, transform.frozen(), ipaths,
                    self.get_transforms(), offsets, offset_trf,
                    [mcolors.to_rgba("none")], self._gapcolor,
                    self._linewidths, ilinestyles,
                    self._antialiaseds, self._urls,
                    "screen")

            renderer.draw_path_collection(
                gc, transform.frozen(), paths,
                self.get_transforms(), offsets, offset_trf,
                self.get_facecolor(), self.get_edgecolor(),
                self._linewidths, self._linestyles,
                self._antialiaseds, self._urls,
                "screen")  # offset_position, kept for backcompat.

        gc.restore()
        renderer.close_group(self.__class__.__name__)
        self.stale = False

    def set_pickradius(self, pickradius):
        """
        Set the pick radius used for containment tests.

        Parameters
        ----------
        pickradius : float
            Pick radius, in points.
        """
        if not isinstance(pickradius, Real):
            raise ValueError(
                f"pickradius must be a real-valued number, not {pickradius!r}")
        self._pickradius = pickradius

    def get_pickradius(self):
        return self._pickradius

    def contains(self, mouseevent):
        """
        Test whether the mouse event occurred in the collection.

        Returns ``bool, dict(ind=itemlist)``, where every item in itemlist
        contains the event.
        """
        if self._different_canvas(mouseevent) or not self.get_visible():
            return False, {}
        pickradius = (
            float(self._picker)
            if isinstance(self._picker, Number) and
               self._picker is not True  # the bool, not just nonzero or 1
            else self._pickradius)
        if self.axes:
            self.axes._unstale_viewLim()
        transform, offset_trf, offsets, paths = self._prepare_points()
        # Tests if the point is contained on one of the polygons formed
        # by the control points of each of the paths. A point is considered
        # "on" a path if it would lie within a stroke of width 2*pickradius
        # following the path. If pickradius <= 0, then we instead simply check
        # if the point is *inside* of the path instead.
        ind = _path.point_in_path_collection(
            mouseevent.x, mouseevent.y, pickradius,
            transform.frozen(), paths, self.get_transforms(),
            offsets, offset_trf, pickradius <= 0)
        return len(ind) > 0, dict(ind=ind)

    def set_urls(self, urls):
        """
        Parameters
        ----------
        urls : list of str or None

        Notes
        -----
        URLs are currently only implemented by the SVG backend. They are
        ignored by all other backends.
        """
        self._urls = urls if urls is not None else [None]
        self.stale = True

    def get_urls(self):
        """
        Return a list of URLs, one for each element of the collection.

        The list contains *None* for elements without a URL. See
        :doc:`/gallery/misc/hyperlinks_sgskip` for an example.
        """
        return self._urls

    def set_hatch(self, hatch):
        r"""
        Set the hatching pattern

        *hatch* can be one of::

          /   - diagonal hatching
          \   - back diagonal
          |   - vertical
          -   - horizontal
          +   - crossed
          x   - crossed diagonal
          o   - small circle
          O   - large circle
          .   - dots
          *   - stars

        Letters can be combined, in which case all the specified
        hatchings are done.  If same letter repeats, it increases the
        density of hatching of that pattern.

        Unlike other properties such as linewidth and colors, hatching
        can only be specified for the collection as a whole, not separately
        for each member.

        Parameters
        ----------
        hatch : {'/', '\\', '|', '-', '+', 'x', 'o', 'O', '.', '*'}
        """
        # Use validate_hatch(list) after deprecation.
        mhatch._validate_hatch_pattern(hatch)
        self._hatch = hatch
        self.stale = True

    def get_hatch(self):
        """Return the current hatching pattern."""
        return self._hatch

    def set_hatch_linewidth(self, lw):
        """Set the hatch linewidth."""
        self._hatch_linewidth = lw

    def get_hatch_linewidth(self):
        """Return the hatch linewidth."""
        return self._hatch_linewidth

    def set_offsets(self, offsets):
        """
        Set the offsets for the collection.

        Parameters
        ----------
        offsets : (N, 2) or (2,) array-like
        """
        offsets = np.asanyarray(offsets)
        if offsets.shape == (2,):  # Broadcast (2,) -> (1, 2) but nothing else.
            offsets = offsets[None, :]
        cstack = (np.ma.column_stack if isinstance(offsets, np.ma.MaskedArray)
                  else np.column_stack)
        self._offsets = cstack(
            (np.asanyarray(self.convert_xunits(offsets[:, 0]), float),
             np.asanyarray(self.convert_yunits(offsets[:, 1]), float)))
        self.stale = True

    def get_offsets(self):
        """Return the offsets for the collection."""
        # Default to zeros in the no-offset (None) case
        return np.zeros((1, 2)) if self._offsets is None else self._offsets

    def _get_default_linewidth(self):
        # This may be overridden in a subclass.
        return mpl.rcParams['patch.linewidth']  # validated as float

    def set_linewidth(self, lw):
        """
        Set the linewidth(s) for the collection.  *lw* can be a scalar
        or a sequence; if it is a sequence the patches will cycle
        through the sequence

        Parameters
        ----------
        lw : float or list of floats
        """
        if lw is None:
            lw = self._get_default_linewidth()
        # get the un-scaled/broadcast lw
        self._us_lw = np.atleast_1d(lw)

        # scale all of the dash patterns.
        self._linewidths, self._linestyles = self._bcast_lwls(
            self._us_lw, self._us_linestyles)
        self.stale = True

    def set_linestyle(self, ls):
        """
        Set the linestyle(s) for the collection.

        ===========================   =================
        linestyle                     description
        ===========================   =================
        ``'-'`` or ``'solid'``        solid line
        ``'--'`` or  ``'dashed'``     dashed line
        ``'-.'`` or  ``'dashdot'``    dash-dotted line
        ``':'`` or ``'dotted'``       dotted line
        ===========================   =================

        Alternatively a dash tuple of the following form can be provided::

            (offset, onoffseq),

        where ``onoffseq`` is an even length tuple of on and off ink in points.

        Parameters
        ----------
        ls : str or tuple or list thereof
            Valid values for individual linestyles include {'-', '--', '-.',
            ':', '', (offset, on-off-seq)}. See `.Line2D.set_linestyle` for a
            complete description.
        """
        # get the list of raw 'unscaled' dash patterns
        self._us_linestyles = mlines._get_dash_patterns(ls)

        # broadcast and scale the lw and dash patterns
        self._linewidths, self._linestyles = self._bcast_lwls(
            self._us_lw, self._us_linestyles)

    @_docstring.interpd
    def set_capstyle(self, cs):
        """
        Set the `.CapStyle` for the collection (for all its elements).

        Parameters
        ----------
        cs : `.CapStyle` or %(CapStyle)s
        """
        self._capstyle = CapStyle(cs)

    @_docstring.interpd
    def get_capstyle(self):
        """
        Return the cap style for the collection (for all its elements).

        Returns
        -------
        %(CapStyle)s or None
        """
        return self._capstyle.name if self._capstyle else None

    @_docstring.interpd
    def set_joinstyle(self, js):
        """
        Set the `.JoinStyle` for the collection (for all its elements).

        Parameters
        ----------
        js : `.JoinStyle` or %(JoinStyle)s
        """
        self._joinstyle = JoinStyle(js)

    @_docstring.interpd
    def get_joinstyle(self):
        """
        Return the join style for the collection (for all its elements).

        Returns
        -------
        %(JoinStyle)s or None
        """
        return self._joinstyle.name if self._joinstyle else None

    @staticmethod
    def _bcast_lwls(linewidths, dashes):
        """
        Internal helper function to broadcast + scale ls/lw

        In the collection drawing code, the linewidth and linestyle are cycled
        through as circular buffers (via ``v[i % len(v)]``).  Thus, if we are
        going to scale the dash pattern at set time (not draw time) we need to
        do the broadcasting now and expand both lists to be the same length.

        Parameters
        ----------
        linewidths : list
            line widths of collection
        dashes : list
            dash specification (offset, (dash pattern tuple))

        Returns
        -------
        linewidths, dashes : list
            Will be the same length, dashes are scaled by paired linewidth
        """
        if mpl.rcParams['_internal.classic_mode']:
            return linewidths, dashes
        # make sure they are the same length so we can zip them
        if len(dashes) != len(linewidths):
            l_dashes = len(dashes)
            l_lw = len(linewidths)
            gcd = math.gcd(l_dashes, l_lw)
            dashes = list(dashes) * (l_lw // gcd)
            linewidths = list(linewidths) * (l_dashes // gcd)

        # scale the dash patterns
        dashes = [mlines._scale_dashes(o, d, lw)
                  for (o, d), lw in zip(dashes, linewidths)]

        return linewidths, dashes

    def get_antialiased(self):
        """
        Get the antialiasing state for rendering.

        Returns
        -------
        array of bools
        """
        return self._antialiaseds

    def set_antialiased(self, aa):
        """
        Set the antialiasing state for rendering.

        Parameters
        ----------
        aa : bool or list of bools
        """
        if aa is None:
            aa = self._get_default_antialiased()
        self._antialiaseds = np.atleast_1d(np.asarray(aa, bool))
        self.stale = True

    def _get_default_antialiased(self):
        # This may be overridden in a subclass.
        return mpl.rcParams['patch.antialiased']

    def set_color(self, c):
        """
        Set both the edgecolor and the facecolor.

        Parameters
        ----------
        c : :mpltype:`color` or list of RGBA tuples

        See Also
        --------
        Collection.set_facecolor, Collection.set_edgecolor
            For setting the edge or face color individually.
        """
        self.set_facecolor(c)
        self.set_edgecolor(c)

    def _get_default_facecolor(self):
        # This may be overridden in a subclass.
        return mpl.rcParams['patch.facecolor']

    def _set_facecolor(self, c):
        if c is None:
            c = self._get_default_facecolor()

        self._facecolors = mcolors.to_rgba_array(c, self._alpha)
        self.stale = True

    def set_facecolor(self, c):
        """
        Set the facecolor(s) of the collection. *c* can be a color (all patches
        have same color), or a sequence of colors; if it is a sequence the
        patches will cycle through the sequence.

        If *c* is 'none', the patch will not be filled.

        Parameters
        ----------
        c : :mpltype:`color` or list of :mpltype:`color`
        """
        if isinstance(c, str) and c.lower() in ("none", "face"):
            c = c.lower()
        self._original_facecolor = c
        self._set_facecolor(c)

    def get_facecolor(self):
        return self._facecolors

    def get_edgecolor(self):
        if cbook._str_equal(self._edgecolors, 'face'):
            return self.get_facecolor()
        else:
            return self._edgecolors

    def _get_default_edgecolor(self):
        # This may be overridden in a subclass.
        return mpl.rcParams['patch.edgecolor']

    def _set_edgecolor(self, c):
        set_hatch_color = True
        if c is None:
            if (mpl.rcParams['patch.force_edgecolor']
                    or self._edge_default
                    or cbook._str_equal(self._original_facecolor, 'none')):
                c = self._get_default_edgecolor()
            else:
                c = 'none'
                set_hatch_color = False
        if cbook._str_lower_equal(c, 'face'):
            self._edgecolors = 'face'
            self.stale = True
            return
        self._edgecolors = mcolors.to_rgba_array(c, self._alpha)
        if set_hatch_color and len(self._edgecolors):
            self._hatch_color = tuple(self._edgecolors[0])
        self.stale = True

    def set_edgecolor(self, c):
        """
        Set the edgecolor(s) of the collection.

        Parameters
        ----------
        c : :mpltype:`color` or list of :mpltype:`color` or 'face'
            The collection edgecolor(s).  If a sequence, the patches cycle
            through it.  If 'face', match the facecolor.
        """
        # We pass through a default value for use in LineCollection.
        # This allows us to maintain None as the default indicator in
        # _original_edgecolor.
        if isinstance(c, str) and c.lower() in ("none", "face"):
            c = c.lower()
        self._original_edgecolor = c
        self._set_edgecolor(c)

    def set_alpha(self, alpha):
        """
        Set the transparency of the collection.

        Parameters
        ----------
        alpha : float or array of float or None
            If not None, *alpha* values must be between 0 and 1, inclusive.
            If an array is provided, its length must match the number of
            elements in the collection.  Masked values and nans are not
            supported.
        """
        artist.Artist._set_alpha_for_array(self, alpha)
        self._set_facecolor(self._original_facecolor)
        self._set_edgecolor(self._original_edgecolor)

    set_alpha.__doc__ = artist.Artist._set_alpha_for_array.__doc__

    def get_linewidth(self):
        return self._linewidths

    def get_linestyle(self):
        return self._linestyles

    def _set_mappable_flags(self):
        """
        Determine whether edges and/or faces are color-mapped.

        This is a helper for update_scalarmappable.
        It sets Boolean flags '_edge_is_mapped' and '_face_is_mapped'.

        Returns
        -------
        mapping_change : bool
            True if either flag is True, or if a flag has changed.
        """
        # The flags are initialized to None to ensure this returns True
        # the first time it is called.
        edge0 = self._edge_is_mapped
        face0 = self._face_is_mapped
        # After returning, the flags must be Booleans, not None.
        self._edge_is_mapped = False
        self._face_is_mapped = False
        if self._A is not None:
            if not cbook._str_equal(self._original_facecolor, 'none'):
                self._face_is_mapped = True
                if cbook._str_equal(self._original_edgecolor, 'face'):
                    self._edge_is_mapped = True
            else:
                if self._original_edgecolor is None:
                    self._edge_is_mapped = True

        mapped = self._face_is_mapped or self._edge_is_mapped
        changed = (edge0 is None or face0 is None
                   or self._edge_is_mapped != edge0
                   or self._face_is_mapped != face0)
        return mapped or changed

    def update_scalarmappable(self):
        """
        Update colors from the scalar mappable array, if any.

        Assign colors to edges and faces based on the array and/or
        colors that were directly set, as appropriate.
        """
        if not self._set_mappable_flags():
            return
        # Allow possibility to call 'self.set_array(None)'.
        if self._A is not None:
            # QuadMesh can map 2d arrays (but pcolormesh supplies 1d array)
            if self._A.ndim > 1 and not isinstance(self, _MeshData):
                raise ValueError('Collections can only map rank 1 arrays')
            if np.iterable(self._alpha):
                if self._alpha.size != self._A.size:
                    raise ValueError(
                        f'Data array shape, {self._A.shape} '
                        'is incompatible with alpha array shape, '
                        f'{self._alpha.shape}. '
                        'This can occur with the deprecated '
                        'behavior of the "flat" shading option, '
                        'in which a row and/or column of the data '
                        'array is dropped.')
                # pcolormesh, scatter, maybe others flatten their _A
                self._alpha = self._alpha.reshape(self._A.shape)
            self._mapped_colors = self.to_rgba(self._A, self._alpha)

        if self._face_is_mapped:
            self._facecolors = self._mapped_colors
        else:
            self._set_facecolor(self._original_facecolor)
        if self._edge_is_mapped:
            self._edgecolors = self._mapped_colors
        else:
            self._set_edgecolor(self._original_edgecolor)
        self.stale = True

    def get_fill(self):
        """Return whether face is colored."""
        return not cbook._str_lower_equal(self._original_facecolor, "none")

    def update_from(self, other):
        """Copy properties from other to self."""

        artist.Artist.update_from(self, other)
        self._antialiaseds = other._antialiaseds
        self._mapped_colors = other._mapped_colors
        self._edge_is_mapped = other._edge_is_mapped
        self._original_edgecolor = other._original_edgecolor
        self._edgecolors = other._edgecolors
        self._face_is_mapped = other._face_is_mapped
        self._original_facecolor = other._original_facecolor
        self._facecolors = other._facecolors
        self._linewidths = other._linewidths
        self._linestyles = other._linestyles
        self._us_linestyles = other._us_linestyles
        self._pickradius = other._pickradius
        self._hatch = other._hatch

        # update_from for scalarmappable
        self._A = other._A
        self.norm = other.norm
        self.cmap = other.cmap
        self.stale = True


class _CollectionWithSizes(Collection):
    """
    Base class for collections that have an array of sizes.
    """
    _factor = 1.0

    def get_sizes(self):
        """
        Return the sizes ('areas') of the elements in the collection.

        Returns
        -------
        array
            The 'area' of each element.
        """
        return self._sizes

    def set_sizes(self, sizes, dpi=72.0):
        """
        Set the sizes of each member of the collection.

        Parameters
        ----------
        sizes : `numpy.ndarray` or None
            The size to set for each element of the collection.  The
            value is the 'area' of the element.
        dpi : float, default: 72
            The dpi of the canvas.
        """
        if sizes is None:
            self._sizes = np.array([])
            self._transforms = np.empty((0, 3, 3))
        else:
            self._sizes = np.asarray(sizes)
            self._transforms = np.zeros((len(self._sizes), 3, 3))
            scale = np.sqrt(self._sizes) * dpi / 72.0 * self._factor
            self._transforms[:, 0, 0] = scale
            self._transforms[:, 1, 1] = scale
            self._transforms[:, 2, 2] = 1.0
        self.stale = True

    @artist.allow_rasterization
    def draw(self, renderer):
        self.set_sizes(self._sizes, self.get_figure(root=True).dpi)
        super().draw(renderer)


class PathCollection(_CollectionWithSizes):
    r"""
    A collection of `~.path.Path`\s, as created by e.g. `~.Axes.scatter`.
    """

    def __init__(self, paths, sizes=None, **kwargs):
        """
        Parameters
        ----------
        paths : list of `.path.Path`
            The paths that will make up the `.Collection`.
        sizes : array-like
            The factor by which to scale each drawn `~.path.Path`. One unit
            squared in the Path's data space is scaled to be ``sizes**2``
            points when rendered.
        **kwargs
            Forwarded to `.Collection`.
        """

        super().__init__(**kwargs)
        self.set_paths(paths)
        self.set_sizes(sizes)
        self.stale = True

    def get_paths(self):
        return self._paths

    def legend_elements(self, prop="colors", num="auto",
                        fmt=None, func=lambda x: x, **kwargs):
        """
        Create legend handles and labels for a PathCollection.

        Each legend handle is a `.Line2D` representing the Path that was drawn,
        and each label is a string that represents the Path.

        This is useful for obtaining a legend for a `~.Axes.scatter` plot;
        e.g.::

            scatter = plt.scatter([1, 2, 3],  [4, 5, 6],  c=[7, 2, 3], num=None)
            plt.legend(*scatter.legend_elements())

        creates three legend elements, one for each color with the numerical
        values passed to *c* as the labels.

        Also see the :ref:`automatedlegendcreation` example.

        Parameters
        ----------
        prop : {"colors", "sizes"}, default: "colors"
            If "colors", the legend handles will show the different colors of
            the collection. If "sizes", the legend will show the different
            sizes. To set both, use *kwargs* to directly edit the `.Line2D`
            properties.
        num : int, None, "auto" (default), array-like, or `~.ticker.Locator`
            Target number of elements to create.
            If None, use all unique elements of the mappable array. If an
            integer, target to use *num* elements in the normed range.
            If *"auto"*, try to determine which option better suits the nature
            of the data.
            The number of created elements may slightly deviate from *num* due
            to a `~.ticker.Locator` being used to find useful locations.
            If a list or array, use exactly those elements for the legend.
            Finally, a `~.ticker.Locator` can be provided.
        fmt : str, `~matplotlib.ticker.Formatter`, or None (default)
            The format or formatter to use for the labels. If a string must be
            a valid input for a `.StrMethodFormatter`. If None (the default),
            use a `.ScalarFormatter`.
        func : function, default: ``lambda x: x``
            Function to calculate the labels.  Often the size (or color)
            argument to `~.Axes.scatter` will have been pre-processed by the
            user using a function ``s = f(x)`` to make the markers visible;
            e.g. ``size = np.log10(x)``.  Providing the inverse of this
            function here allows that pre-processing to be inverted, so that
            the legend labels have the correct values; e.g. ``func = lambda
            x: 10**x``.
        **kwargs
            Allowed keyword arguments are *color* and *size*. E.g. it may be
            useful to set the color of the markers if *prop="sizes"* is used;
            similarly to set the size of the markers if *prop="colors"* is
            used. Any further parameters are passed onto the `.Line2D`
            instance. This may be useful to e.g. specify a different
            *markeredgecolor* or *alpha* for the legend handles.

        Returns
        -------
        handles : list of `.Line2D`
            Visual representation of each element of the legend.
        labels : list of str
            The string labels for elements of the legend.
        """
        handles = []
        labels = []
        hasarray = self.get_array() is not None
        if fmt is None:
            fmt = mpl.ticker.ScalarFormatter(useOffset=False, useMathText=True)
        elif isinstance(fmt, str):
            fmt = mpl.ticker.StrMethodFormatter(fmt)
        fmt.create_dummy_axis()

        if prop == "colors":
            if not hasarray:
                warnings.warn("Collection without array used. Make sure to "
                              "specify the values to be colormapped via the "
                              "`c` argument.")
                return handles, labels
            u = np.unique(self.get_array())
            size = kwargs.pop("size", mpl.rcParams["lines.markersize"])
        elif prop == "sizes":
            u = np.unique(self.get_sizes())
            color = kwargs.pop("color", "k")
        else:
            raise ValueError("Valid values for `prop` are 'colors' or "
                             f"'sizes'. You supplied '{prop}' instead.")

        fu = func(u)
        fmt.axis.set_view_interval(fu.min(), fu.max())
        fmt.axis.set_data_interval(fu.min(), fu.max())
        if num == "auto":
            num = 9
            if len(u) <= num:
                num = None
        if num is None:
            values = u
            label_values = func(values)
        else:
            if prop == "colors":
                arr = self.get_array()
            elif prop == "sizes":
                arr = self.get_sizes()
            if isinstance(num, mpl.ticker.Locator):
                loc = num
            elif np.iterable(num):
                loc = mpl.ticker.FixedLocator(num)
            else:
                num = int(num)
                loc = mpl.ticker.MaxNLocator(nbins=num, min_n_ticks=num-1,
                                             steps=[1, 2, 2.5, 3, 5, 6, 8, 10])
            label_values = loc.tick_values(func(arr).min(), func(arr).max())
            cond = ((label_values >= func(arr).min()) &
                    (label_values <= func(arr).max()))
            label_values = label_values[cond]
            yarr = np.linspace(arr.min(), arr.max(), 256)
            xarr = func(yarr)
            ix = np.argsort(xarr)
            values = np.interp(label_values, xarr[ix], yarr[ix])

        kw = {"markeredgewidth": self.get_linewidths()[0],
              "alpha": self.get_alpha(),
              **kwargs}

        for val, lab in zip(values, label_values):
            if prop == "colors":
                color = self.cmap(self.norm(val))
            elif prop == "sizes":
                size = np.sqrt(val)
                if np.isclose(size, 0.0):
                    continue
            h = mlines.Line2D([0], [0], ls="", color=color, ms=size,
                              marker=self.get_paths()[0], **kw)
            handles.append(h)
            if hasattr(fmt, "set_locs"):
                fmt.set_locs(label_values)
            l = fmt(lab)
            labels.append(l)

        return handles, labels


class PolyCollection(_CollectionWithSizes):

    def __init__(self, verts, sizes=None, *, closed=True, **kwargs):
        """
        Parameters
        ----------
        verts : list of array-like
            The sequence of polygons [*verts0*, *verts1*, ...] where each
            element *verts_i* defines the vertices of polygon *i* as a 2D
            array-like of shape (M, 2).
        sizes : array-like, default: None
            Squared scaling factors for the polygons. The coordinates of each
            polygon *verts_i* are multiplied by the square-root of the
            corresponding entry in *sizes* (i.e., *sizes* specify the scaling
            of areas). The scaling is applied before the Artist master
            transform.
        closed : bool, default: True
            Whether the polygon should be closed by adding a CLOSEPOLY
            connection at the end.
        **kwargs
            Forwarded to `.Collection`.
        """
        super().__init__(**kwargs)
        self.set_sizes(sizes)
        self.set_verts(verts, closed)
        self.stale = True

    def set_verts(self, verts, closed=True):
        """
        Set the vertices of the polygons.

        Parameters
        ----------
        verts : list of array-like
            The sequence of polygons [*verts0*, *verts1*, ...] where each
            element *verts_i* defines the vertices of polygon *i* as a 2D
            array-like of shape (M, 2).
        closed : bool, default: True
            Whether the polygon should be closed by adding a CLOSEPOLY
            connection at the end.
        """
        self.stale = True
        if isinstance(verts, np.ma.MaskedArray):
            verts = verts.astype(float).filled(np.nan)

        # No need to do anything fancy if the path isn't closed.
        if not closed:
            self._paths = [mpath.Path(xy) for xy in verts]
            return

        # Fast path for arrays
        if isinstance(verts, np.ndarray) and len(verts.shape) == 3:
            verts_pad = np.concatenate((verts, verts[:, :1]), axis=1)
            # Creating the codes once is much faster than having Path do it
            # separately each time by passing closed=True.
            codes = np.empty(verts_pad.shape[1], dtype=mpath.Path.code_type)
            codes[:] = mpath.Path.LINETO
            codes[0] = mpath.Path.MOVETO
            codes[-1] = mpath.Path.CLOSEPOLY
            self._paths = [mpath.Path(xy, codes) for xy in verts_pad]
            return

        self._paths = []
        for xy in verts:
            if len(xy):
                self._paths.append(mpath.Path._create_closed(xy))
            else:
                self._paths.append(mpath.Path(xy))

    set_paths = set_verts

    def set_verts_and_codes(self, verts, codes):
        """Initialize vertices with path codes."""
        if len(verts) != len(codes):
            raise ValueError("'codes' must be a 1D list or array "
                             "with the same length of 'verts'")
        self._paths = [mpath.Path(xy, cds) if len(xy) else mpath.Path(xy)
                       for xy, cds in zip(verts, codes)]
        self.stale = True


class FillBetweenPolyCollection(PolyCollection):
    """
    `.PolyCollection` that fills the area between two x- or y-curves.
    """
    def __init__(
            self, t_direction, t, f1, f2, *,
            where=None, interpolate=False, step=None, **kwargs):
        """
        Parameters
        ----------
        t_direction : {{'x', 'y'}}
            The axes on which the variable lies.

            - 'x': the curves are ``(t, f1)`` and ``(t, f2)``.
            - 'y': the curves are ``(f1, t)`` and ``(f2, t)``.

        t : array-like
            The ``t_direction`` coordinates of the nodes defining the curves.

        f1 : array-like or float
            The other coordinates of the nodes defining the first curve.

        f2 : array-like or float
            The other coordinates of the nodes defining the second curve.

        where : array-like of bool, optional
            Define *where* to exclude some {dir} regions from being filled.
            The filled regions are defined by the coordinates ``t[where]``.
            More precisely, fill between ``t[i]`` and ``t[i+1]`` if
            ``where[i] and where[i+1]``.  Note that this definition implies
            that an isolated *True* value between two *False* values in *where*
            will not result in filling.  Both sides of the *True* position
            remain unfilled due to the adjacent *False* values.

        interpolate : bool, default: False
            This option is only relevant if *where* is used and the two curves
            are crossing each other.

            Semantically, *where* is often used for *f1* > *f2* or
            similar.  By default, the nodes of the polygon defining the filled
            region will only be placed at the positions in the *t* array.
            Such a polygon cannot describe the above semantics close to the
            intersection.  The t-sections containing the intersection are
            simply clipped.

            Setting *interpolate* to *True* will calculate the actual
            intersection point and extend the filled region up to this point.

        step : {{'pre', 'post', 'mid'}}, optional
            Define *step* if the filling should be a step function,
            i.e. constant in between *t*.  The value determines where the
            step will occur:

            - 'pre': The f value is continued constantly to the left from
              every *t* position, i.e. the interval ``(t[i-1], t[i]]`` has the
              value ``f[i]``.
            - 'post': The y value is continued constantly to the right from
              every *x* position, i.e. the interval ``[t[i], t[i+1])`` has the
              value ``f[i]``.
            - 'mid': Steps occur half-way between the *t* positions.

        **kwargs
            Forwarded to `.PolyCollection`.

        See Also
        --------
        .Axes.fill_between, .Axes.fill_betweenx
        """
        self.t_direction = t_direction
        self._interpolate = interpolate
        self._step = step
        verts = self._make_verts(t, f1, f2, where)
        super().__init__(verts, **kwargs)

    @staticmethod
    def _f_dir_from_t(t_direction):
        """The direction that is other than `t_direction`."""
        if t_direction == "x":
            return "y"
        elif t_direction == "y":
            return "x"
        else:
            msg = f"t_direction must be 'x' or 'y', got {t_direction!r}"
            raise ValueError(msg)

    @property
    def _f_direction(self):
        """The direction that is other than `self.t_direction`."""
        return self._f_dir_from_t(self.t_direction)

    def set_data(self, t, f1, f2, *, where=None):
        """
        Set new values for the two bounding curves.

        Parameters
        ----------
        t : array-like
            The ``self.t_direction`` coordinates of the nodes defining the curves.

        f1 : array-like or float
            The other coordinates of the nodes defining the first curve.

        f2 : array-like or float
            The other coordinates of the nodes defining the second curve.

        where : array-like of bool, optional
            Define *where* to exclude some {dir} regions from being filled.
            The filled regions are defined by the coordinates ``t[where]``.
            More precisely, fill between ``t[i]`` and ``t[i+1]`` if
            ``where[i] and where[i+1]``.  Note that this definition implies
            that an isolated *True* value between two *False* values in *where*
            will not result in filling.  Both sides of the *True* position
            remain unfilled due to the adjacent *False* values.

        See Also
        --------
        .PolyCollection.set_verts, .Line2D.set_data
        """
        t, f1, f2 = self.axes._fill_between_process_units(
            self.t_direction, self._f_direction, t, f1, f2)

        verts = self._make_verts(t, f1, f2, where)
        self.set_verts(verts)

    def get_datalim(self, transData):
        """Calculate the data limits and return them as a `.Bbox`."""
        datalim = transforms.Bbox.null()
        datalim.update_from_data_xy((self.get_transform() - transData).transform(
            np.concatenate([self._bbox, [self._bbox.minpos]])))
        return datalim

    def _make_verts(self, t, f1, f2, where):
        """
        Make verts that can be forwarded to `.PolyCollection`.
        """
        self._validate_shapes(self.t_direction, self._f_direction, t, f1, f2)

        where = self._get_data_mask(t, f1, f2, where)
        t, f1, f2 = np.broadcast_arrays(np.atleast_1d(t), f1, f2, subok=True)

        self._bbox = transforms.Bbox.null()
        self._bbox.update_from_data_xy(self._fix_pts_xy_order(np.concatenate([
            np.stack((t[where], f[where]), axis=-1) for f in (f1, f2)])))

        return [
            self._make_verts_for_region(t, f1, f2, idx0, idx1)
            for idx0, idx1 in cbook.contiguous_regions(where)
        ]

    def _get_data_mask(self, t, f1, f2, where):
        """
        Return a bool array, with True at all points that should eventually be rendered.

        The array is True at a point if none of the data inputs
        *t*, *f1*, *f2* is masked and if the input *where* is true at that point.
        """
        if where is None:
            where = True
        else:
            where = np.asarray(where, dtype=bool)
            if where.size != t.size:
                msg = "where size ({}) does not match {!r} size ({})".format(
                    where.size, self.t_direction, t.size)
                raise ValueError(msg)
        return where & ~functools.reduce(
            np.logical_or, map(np.ma.getmaskarray, [t, f1, f2]))

    @staticmethod
    def _validate_shapes(t_dir, f_dir, t, f1, f2):
        """Validate that t, f1 and f2 are 1-dimensional and have the same length."""
        names = (d + s for d, s in zip((t_dir, f_dir, f_dir), ("", "1", "2")))
        for name, array in zip(names, [t, f1, f2]):
            if array.ndim > 1:
                raise ValueError(f"{name!r} is not 1-dimensional")
            if t.size > 1 and array.size > 1 and t.size != array.size:
                msg = "{!r} has size {}, but {!r} has an unequal size of {}".format(
                    t_dir, t.size, name, array.size)
                raise ValueError(msg)

    def _make_verts_for_region(self, t, f1, f2, idx0, idx1):
        """
        Make ``verts`` for a contiguous region between ``idx0`` and ``idx1``, taking
        into account ``step`` and ``interpolate``.
        """
        t_slice = t[idx0:idx1]
        f1_slice = f1[idx0:idx1]
        f2_slice = f2[idx0:idx1]
        if self._step is not None:
            step_func = cbook.STEP_LOOKUP_MAP["steps-" + self._step]
            t_slice, f1_slice, f2_slice = step_func(t_slice, f1_slice, f2_slice)

        if self._interpolate:
            start = self._get_interpolating_points(t, f1, f2, idx0)
            end = self._get_interpolating_points(t, f1, f2, idx1)
        else:
            # Handle scalar f2 (e.g. 0): the fill should go all
            # the way down to 0 even if none of the dep1 sample points do.
            start = t_slice[0], f2_slice[0]
            end = t_slice[-1], f2_slice[-1]

        pts = np.concatenate((
            np.asarray([start]),
            np.stack((t_slice, f1_slice), axis=-1),
            np.asarray([end]),
            np.stack((t_slice, f2_slice), axis=-1)[::-1]))

        return self._fix_pts_xy_order(pts)

    @classmethod
    def _get_interpolating_points(cls, t, f1, f2, idx):
        """Calculate interpolating points."""
        im1 = max(idx - 1, 0)
        t_values = t[im1:idx+1]
        diff_values = f1[im1:idx+1] - f2[im1:idx+1]
        f1_values = f1[im1:idx+1]

        if len(diff_values) == 2:
            if np.ma.is_masked(diff_values[1]):
                return t[im1], f1[im1]
            elif np.ma.is_masked(diff_values[0]):
                return t[idx], f1[idx]

        diff_root_t = cls._get_diff_root(0, diff_values, t_values)
        diff_root_f = cls._get_diff_root(diff_root_t, t_values, f1_values)
        return diff_root_t, diff_root_f

    @staticmethod
    def _get_diff_root(x, xp, fp):
        """Calculate diff root."""
        order = xp.argsort()
        return np.interp(x, xp[order], fp[order])

    def _fix_pts_xy_order(self, pts):
        """
        Fix pts calculation results with `self.t_direction`.

        In the workflow, it is assumed that `self.t_direction` is 'x'. If this
        is not true, we need to exchange the coordinates.
        """
        return pts[:, ::-1] if self.t_direction == "y" else pts


class RegularPolyCollection(_CollectionWithSizes):
    """A collection of n-sided regular polygons."""

    _path_generator = mpath.Path.unit_regular_polygon
    _factor = np.pi ** (-1/2)

    def __init__(self,
                 numsides,
                 *,
                 rotation=0,
                 sizes=(1,),
                 **kwargs):
        """
        Parameters
        ----------
        numsides : int
            The number of sides of the polygon.
        rotation : float
            The rotation of the polygon in radians.
        sizes : tuple of float
            The area of the circle circumscribing the polygon in points^2.
        **kwargs
            Forwarded to `.Collection`.

        Examples
        --------
        See :doc:`/gallery/event_handling/lasso_demo` for a complete example::

            offsets = np.random.rand(20, 2)
            facecolors = [cm.jet(x) for x in np.random.rand(20)]

            collection = RegularPolyCollection(
                numsides=5, # a pentagon
                rotation=0, sizes=(50,),
                facecolors=facecolors,
                edgecolors=("black",),
                linewidths=(1,),
                offsets=offsets,
                offset_transform=ax.transData,
                )
        """
        super().__init__(**kwargs)
        self.set_sizes(sizes)
        self._numsides = numsides
        self._paths = [self._path_generator(numsides)]
        self._rotation = rotation
        self.set_transform(transforms.IdentityTransform())

    def get_numsides(self):
        return self._numsides

    def get_rotation(self):
        return self._rotation

    @artist.allow_rasterization
    def draw(self, renderer):
        self.set_sizes(self._sizes, self.get_figure(root=True).dpi)
        self._transforms = [
            transforms.Affine2D(x).rotate(-self._rotation).get_matrix()
            for x in self._transforms
        ]
        # Explicitly not super().draw, because set_sizes must be called before
        # updating self._transforms.
        Collection.draw(self, renderer)


class StarPolygonCollection(RegularPolyCollection):
    """Draw a collection of regular stars with *numsides* points."""
    _path_generator = mpath.Path.unit_regular_star


class AsteriskPolygonCollection(RegularPolyCollection):
    """Draw a collection of regular asterisks with *numsides* points."""
    _path_generator = mpath.Path.unit_regular_asterisk


class LineCollection(Collection):
    r"""
    Represents a sequence of `.Line2D`\s that should be drawn together.

    This class extends `.Collection` to represent a sequence of
    `.Line2D`\s instead of just a sequence of `.Patch`\s.
    Just as in `.Collection`, each property of a *LineCollection* may be either
    a single value or a list of values. This list is then used cyclically for
    each element of the LineCollection, so the property of the ``i``\th element
    of the collection is::

      prop[i % len(prop)]

    The properties of each member of a *LineCollection* default to their values
    in :rc:`lines.*` instead of :rc:`patch.*`, and the property *colors* is
    added in place of *edgecolors*.
    """

    _edge_default = True

    def __init__(self, segments,  # Can be None.
                 *,
                 zorder=2,        # Collection.zorder is 1
                 **kwargs
                 ):
        """
        Parameters
        ----------
        segments : list of (N, 2) array-like
            A sequence ``[line0, line1, ...]`` where each line is a (N, 2)-shape
            array-like containing points::

                line0 = [(x0, y0), (x1, y1), ...]

            Each line can contain a different number of points.
        linewidths : float or list of float, default: :rc:`lines.linewidth`
            The width of each line in points.
        colors : :mpltype:`color` or list of color, default: :rc:`lines.color`
            A sequence of RGBA tuples (e.g., arbitrary color strings, etc, not
            allowed).
        antialiaseds : bool or list of bool, default: :rc:`lines.antialiased`
            Whether to use antialiasing for each line.
        zorder : float, default: 2
            zorder of the lines once drawn.

        facecolors : :mpltype:`color` or list of :mpltype:`color`, default: 'none'
            When setting *facecolors*, each line is interpreted as a boundary
            for an area, implicitly closing the path from the last point to the
            first point. The enclosed area is filled with *facecolor*.
            In order to manually specify what should count as the "interior" of
            each line, please use `.PathCollection` instead, where the
            "interior" can be specified by appropriate usage of
            `~.path.Path.CLOSEPOLY`.

        **kwargs
            Forwarded to `.Collection`.
        """
        # Unfortunately, mplot3d needs this explicit setting of 'facecolors'.
        kwargs.setdefault('facecolors', 'none')
        super().__init__(
            zorder=zorder,
            **kwargs)
        self.set_segments(segments)

    def set_segments(self, segments):
        if segments is None:
            return

        self._paths = [mpath.Path(seg) if isinstance(seg, np.ma.MaskedArray)
                       else mpath.Path(np.asarray(seg, float))
                       for seg in segments]
        self.stale = True

    set_verts = set_segments  # for compatibility with PolyCollection
    set_paths = set_segments

    def get_segments(self):
        """
        Returns
        -------
        list
            List of segments in the LineCollection. Each list item contains an
            array of vertices.
        """
        segments = []

        for path in self._paths:
            vertices = [
                vertex
                for vertex, _
                # Never simplify here, we want to get the data-space values
                # back and there in no way to know the "right" simplification
                # threshold so never try.
                in path.iter_segments(simplify=False)
            ]
            vertices = np.asarray(vertices)
            segments.append(vertices)

        return segments

    def _get_default_linewidth(self):
        return mpl.rcParams['lines.linewidth']

    def _get_default_antialiased(self):
        return mpl.rcParams['lines.antialiased']

    def _get_default_edgecolor(self):
        return mpl.rcParams['lines.color']

    def _get_default_facecolor(self):
        return 'none'

    def set_alpha(self, alpha):
        # docstring inherited
        super().set_alpha(alpha)
        if self._gapcolor is not None:
            self.set_gapcolor(self._original_gapcolor)

    def set_color(self, c):
        """
        Set the edgecolor(s) of the LineCollection.

        Parameters
        ----------
        c : :mpltype:`color` or list of :mpltype:`color`
            Single color (all lines have same color), or a
            sequence of RGBA tuples; if it is a sequence the lines will
            cycle through the sequence.
        """
        self.set_edgecolor(c)

    set_colors = set_color

    def get_color(self):
        return self._edgecolors

    get_colors = get_color  # for compatibility with old versions

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
        gapcolor : :mpltype:`color` or list of :mpltype:`color` or None
            The color with which to fill the gaps. If None, the gaps are
            unfilled.
        """
        self._original_gapcolor = gapcolor
        self._set_gapcolor(gapcolor)

    def _set_gapcolor(self, gapcolor):
        if gapcolor is not None:
            gapcolor = mcolors.to_rgba_array(gapcolor, self._alpha)
        self._gapcolor = gapcolor
        self.stale = True

    def get_gapcolor(self):
        return self._gapcolor

    def _get_inverse_paths_linestyles(self):
        """
        Returns the path and pattern for the gaps in the non-solid lines.

        This path and pattern is the inverse of the path and pattern used to
        construct the non-solid lines. For solid lines, we set the inverse path
        to nans to prevent drawing an inverse line.
        """
        path_patterns = [
            (mpath.Path(np.full((1, 2), np.nan)), ls)
            if ls == (0, None) else
            (path, mlines._get_inverse_dash_pattern(*ls))
            for (path, ls) in
            zip(self._paths, itertools.cycle(self._linestyles))]

        return zip(*path_patterns)


class EventCollection(LineCollection):
    """
    A collection of locations along a single axis at which an "event" occurred.

    The events are given by a 1-dimensional array. They do not have an
    amplitude and are displayed as parallel lines.
    """

    _edge_default = True

    def __init__(self,
                 positions,  # Cannot be None.
                 orientation='horizontal',
                 *,
                 lineoffset=0,
                 linelength=1,
                 linewidth=None,
                 color=None,
                 linestyle='solid',
                 antialiased=None,
                 **kwargs
                 ):
        """
        Parameters
        ----------
        positions : 1D array-like
            Each value is an event.
        orientation : {'horizontal', 'vertical'}, default: 'horizontal'
            The sequence of events is plotted along this direction.
            The marker lines of the single events are along the orthogonal
            direction.
        lineoffset : float, default: 0
            The offset of the center of the markers from the origin, in the
            direction orthogonal to *orientation*.
        linelength : float, default: 1
            The total height of the marker (i.e. the marker stretches from
            ``lineoffset - linelength/2`` to ``lineoffset + linelength/2``).
        linewidth : float or list thereof, default: :rc:`lines.linewidth`
            The line width of the event lines, in points.
        color : :mpltype:`color` or list of :mpltype:`color`, default: :rc:`lines.color`
            The color of the event lines.
        linestyle : str or tuple or list thereof, default: 'solid'
            Valid strings are ['solid', 'dashed', 'dashdot', 'dotted',
            '-', '--', '-.', ':']. Dash tuples should be of the form::

                (offset, onoffseq),

            where *onoffseq* is an even length tuple of on and off ink
            in points.
        antialiased : bool or list thereof, default: :rc:`lines.antialiased`
            Whether to use antialiasing for drawing the lines.
        **kwargs
            Forwarded to `.LineCollection`.

        Examples
        --------
        .. plot:: gallery/lines_bars_and_markers/eventcollection_demo.py
        """
        super().__init__([],
                         linewidths=linewidth, linestyles=linestyle,
                         colors=color, antialiaseds=antialiased,
                         **kwargs)
        self._is_horizontal = True  # Initial value, may be switched below.
        self._linelength = linelength
        self._lineoffset = lineoffset
        self.set_orientation(orientation)
        self.set_positions(positions)

    def get_positions(self):
        """
        Return an array containing the floating-point values of the positions.
        """
        pos = 0 if self.is_horizontal() else 1
        return [segment[0, pos] for segment in self.get_segments()]

    def set_positions(self, positions):
        """Set the positions of the events."""
        if positions is None:
            positions = []
        if np.ndim(positions) != 1:
            raise ValueError('positions must be one-dimensional')
        lineoffset = self.get_lineoffset()
        linelength = self.get_linelength()
        pos_idx = 0 if self.is_horizontal() else 1
        segments = np.empty((len(positions), 2, 2))
        segments[:, :, pos_idx] = np.sort(positions)[:, None]
        segments[:, 0, 1 - pos_idx] = lineoffset + linelength / 2
        segments[:, 1, 1 - pos_idx] = lineoffset - linelength / 2
        self.set_segments(segments)

    def add_positions(self, position):
        """Add one or more events at the specified positions."""
        if position is None or (hasattr(position, 'len') and
                                len(position) == 0):
            return
        positions = self.get_positions()
        positions = np.hstack([positions, np.asanyarray(position)])
        self.set_positions(positions)
    extend_positions = append_positions = add_positions

    def is_horizontal(self):
        """True if the eventcollection is horizontal, False if vertical."""
        return self._is_horizontal

    def get_orientation(self):
        """
        Return the orientation of the event line ('horizontal' or 'vertical').
        """
        return 'horizontal' if self.is_horizontal() else 'vertical'

    def switch_orientation(self):
        """
        Switch the orientation of the event line, either from vertical to
        horizontal or vice versus.
        """
        segments = self.get_segments()
        for i, segment in enumerate(segments):
            segments[i] = np.fliplr(segment)
        self.set_segments(segments)
        self._is_horizontal = not self.is_horizontal()
        self.stale = True

    def set_orientation(self, orientation):
        """
        Set the orientation of the event line.

        Parameters
        ----------
        orientation : {'horizontal', 'vertical'}
        """
        is_horizontal = _api.check_getitem(
            {"horizontal": True, "vertical": False},
            orientation=orientation)
        if is_horizontal == self.is_horizontal():
            return
        self.switch_orientation()

    def get_linelength(self):
        """Return the length of the lines used to mark each event."""
        return self._linelength

    def set_linelength(self, linelength):
        """Set the length of the lines used to mark each event."""
        if linelength == self.get_linelength():
            return
        lineoffset = self.get_lineoffset()
        segments = self.get_segments()
        pos = 1 if self.is_horizontal() else 0
        for segment in segments:
            segment[0, pos] = lineoffset + linelength / 2.
            segment[1, pos] = lineoffset - linelength / 2.
        self.set_segments(segments)
        self._linelength = linelength

    def get_lineoffset(self):
        """Return the offset of the lines used to mark each event."""
        return self._lineoffset

    def set_lineoffset(self, lineoffset):
        """Set the offset of the lines used to mark each event."""
        if lineoffset == self.get_lineoffset():
            return
        linelength = self.get_linelength()
        segments = self.get_segments()
        pos = 1 if self.is_horizontal() else 0
        for segment in segments:
            segment[0, pos] = lineoffset + linelength / 2.
            segment[1, pos] = lineoffset - linelength / 2.
        self.set_segments(segments)
        self._lineoffset = lineoffset

    def get_linewidth(self):
        """Get the width of the lines used to mark each event."""
        return super().get_linewidth()[0]

    def get_linewidths(self):
        return super().get_linewidth()

    def get_color(self):
        """Return the color of the lines used to mark each event."""
        return self.get_colors()[0]


class CircleCollection(_CollectionWithSizes):
    """A collection of circles, drawn using splines."""

    _factor = np.pi ** (-1/2)

    def __init__(self, sizes, **kwargs):
        """
        Parameters
        ----------
        sizes : float or array-like
            The area of each circle in points^2.
        **kwargs
            Forwarded to `.Collection`.
        """
        super().__init__(**kwargs)
        self.set_sizes(sizes)
        self.set_transform(transforms.IdentityTransform())
        self._paths = [mpath.Path.unit_circle()]


class EllipseCollection(Collection):
    """A collection of ellipses, drawn using splines."""

    def __init__(self, widths, heights, angles, *, units='points', **kwargs):
        """
        Parameters
        ----------
        widths : array-like
            The lengths of the first axes (e.g., major axis lengths).
        heights : array-like
            The lengths of second axes.
        angles : array-like
            The angles of the first axes, degrees CCW from the x-axis.
        units : {'points', 'inches', 'dots', 'width', 'height', 'x', 'y', 'xy'}
            The units in which majors and minors are given; 'width' and
            'height' refer to the dimensions of the axes, while 'x' and 'y'
            refer to the *offsets* data units. 'xy' differs from all others in
            that the angle as plotted varies with the aspect ratio, and equals
            the specified angle only when the aspect ratio is unity.  Hence
            it behaves the same as the `~.patches.Ellipse` with
            ``axes.transData`` as its transform.
        **kwargs
            Forwarded to `Collection`.
        """
        super().__init__(**kwargs)
        self.set_widths(widths)
        self.set_heights(heights)
        self.set_angles(angles)
        self._units = units
        self.set_transform(transforms.IdentityTransform())
        self._transforms = np.empty((0, 3, 3))
        self._paths = [mpath.Path.unit_circle()]

    def _set_transforms(self):
        """Calculate transforms immediately before drawing."""

        ax = self.axes
        fig = self.get_figure(root=False)

        if self._units == 'xy':
            sc = 1
        elif self._units == 'x':
            sc = ax.bbox.width / ax.viewLim.width
        elif self._units == 'y':
            sc = ax.bbox.height / ax.viewLim.height
        elif self._units == 'inches':
            sc = fig.dpi
        elif self._units == 'points':
            sc = fig.dpi / 72.0
        elif self._units == 'width':
            sc = ax.bbox.width
        elif self._units == 'height':
            sc = ax.bbox.height
        elif self._units == 'dots':
            sc = 1.0
        else:
            raise ValueError(f'Unrecognized units: {self._units!r}')

        self._transforms = np.zeros((len(self._widths), 3, 3))
        widths = self._widths * sc
        heights = self._heights * sc
        sin_angle = np.sin(self._angles)
        cos_angle = np.cos(self._angles)
        self._transforms[:, 0, 0] = widths * cos_angle
        self._transforms[:, 0, 1] = heights * -sin_angle
        self._transforms[:, 1, 0] = widths * sin_angle
        self._transforms[:, 1, 1] = heights * cos_angle
        self._transforms[:, 2, 2] = 1.0

        _affine = transforms.Affine2D
        if self._units == 'xy':
            m = ax.transData.get_affine().get_matrix().copy()
            m[:2, 2:] = 0
            self.set_transform(_affine(m))

    def set_widths(self, widths):
        """Set the lengths of the first axes (e.g., major axis)."""
        self._widths = 0.5 * np.asarray(widths).ravel()
        self.stale = True

    def set_heights(self, heights):
        """Set the lengths of second axes (e.g., minor axes)."""
        self._heights = 0.5 * np.asarray(heights).ravel()
        self.stale = True

    def set_angles(self, angles):
        """Set the angles of the first axes, degrees CCW from the x-axis."""
        self._angles = np.deg2rad(angles).ravel()
        self.stale = True

    def get_widths(self):
        """Get the lengths of the first axes (e.g., major axis)."""
        return self._widths * 2

    def get_heights(self):
        """Set the lengths of second axes (e.g., minor axes)."""
        return self._heights * 2

    def get_angles(self):
        """Get the angles of the first axes, degrees CCW from the x-axis."""
        return np.rad2deg(self._angles)

    @artist.allow_rasterization
    def draw(self, renderer):
        self._set_transforms()
        super().draw(renderer)


class PatchCollection(Collection):
    """
    A generic collection of patches.

    PatchCollection draws faster than a large number of equivalent individual
    Patches. It also makes it easier to assign a colormap to a heterogeneous
    collection of patches.
    """

    def __init__(self, patches, *, match_original=False, **kwargs):
        """
        Parameters
        ----------
        patches : list of `.Patch`
            A sequence of Patch objects.  This list may include
            a heterogeneous assortment of different patch types.

        match_original : bool, default: False
            If True, use the colors and linewidths of the original
            patches.  If False, new colors may be assigned by
            providing the standard collection arguments, facecolor,
            edgecolor, linewidths, norm or cmap.

        **kwargs
            All other parameters are forwarded to `.Collection`.

            If any of *edgecolors*, *facecolors*, *linewidths*, *antialiaseds*
            are None, they default to their `.rcParams` patch setting, in
            sequence form.

        Notes
        -----
        The use of `~matplotlib.cm.ScalarMappable` functionality is optional.
        If the `~matplotlib.cm.ScalarMappable` matrix ``_A`` has been set (via
        a call to `~.ScalarMappable.set_array`), at draw time a call to scalar
        mappable will be made to set the face colors.
        """

        if match_original:
            def determine_facecolor(patch):
                if patch.get_fill():
                    return patch.get_facecolor()
                return [0, 0, 0, 0]

            kwargs['facecolors'] = [determine_facecolor(p) for p in patches]
            kwargs['edgecolors'] = [p.get_edgecolor() for p in patches]
            kwargs['linewidths'] = [p.get_linewidth() for p in patches]
            kwargs['linestyles'] = [p.get_linestyle() for p in patches]
            kwargs['antialiaseds'] = [p.get_antialiased() for p in patches]

        super().__init__(**kwargs)

        self.set_paths(patches)

    def set_paths(self, patches):
        paths = [p.get_transform().transform_path(p.get_path())
                 for p in patches]
        self._paths = paths


class TriMesh(Collection):
    """
    Class for the efficient drawing of a triangular mesh using Gouraud shading.

    A triangular mesh is a `~matplotlib.tri.Triangulation` object.
    """
    def __init__(self, triangulation, **kwargs):
        super().__init__(**kwargs)
        self._triangulation = triangulation
        self._shading = 'gouraud'

        self._bbox = transforms.Bbox.unit()

        # Unfortunately this requires a copy, unless Triangulation
        # was rewritten.
        xy = np.hstack((triangulation.x.reshape(-1, 1),
                        triangulation.y.reshape(-1, 1)))
        self._bbox.update_from_data_xy(xy)

    def get_paths(self):
        if self._paths is None:
            self.set_paths()
        return self._paths

    def set_paths(self):
        self._paths = self.convert_mesh_to_paths(self._triangulation)

    @staticmethod
    def convert_mesh_to_paths(tri):
        """
        Convert a given mesh into a sequence of `.Path` objects.

        This function is primarily of use to implementers of backends that do
        not directly support meshes.
        """
        triangles = tri.get_masked_triangles()
        verts = np.stack((tri.x[triangles], tri.y[triangles]), axis=-1)
        return [mpath.Path(x) for x in verts]

    @artist.allow_rasterization
    def draw(self, renderer):
        if not self.get_visible():
            return
        renderer.open_group(self.__class__.__name__, gid=self.get_gid())
        transform = self.get_transform()

        # Get a list of triangles and the color at each vertex.
        tri = self._triangulation
        triangles = tri.get_masked_triangles()

        verts = np.stack((tri.x[triangles], tri.y[triangles]), axis=-1)

        self.update_scalarmappable()
        colors = self._facecolors[triangles]

        gc = renderer.new_gc()
        self._set_gc_clip(gc)
        gc.set_linewidth(self.get_linewidth()[0])
        renderer.draw_gouraud_triangles(gc, verts, colors, transform.frozen())
        gc.restore()
        renderer.close_group(self.__class__.__name__)


class _MeshData:
    r"""
    Class for managing the two dimensional coordinates of Quadrilateral meshes
    and the associated data with them. This class is a mixin and is intended to
    be used with another collection that will implement the draw separately.

    A quadrilateral mesh is a grid of M by N adjacent quadrilaterals that are
    defined via a (M+1, N+1) grid of vertices. The quadrilateral (m, n) is
    defined by the vertices ::

               (m+1, n) ----------- (m+1, n+1)
                  /                   /
                 /                 /
                /               /
            (m, n) -------- (m, n+1)

    The mesh need not be regular and the polygons need not be convex.

    Parameters
    ----------
    coordinates : (M+1, N+1, 2) array-like
        The vertices. ``coordinates[m, n]`` specifies the (x, y) coordinates
        of vertex (m, n).

    shading : {'flat', 'gouraud'}, default: 'flat'
    """
    def __init__(self, coordinates, *, shading='flat'):
        _api.check_shape((None, None, 2), coordinates=coordinates)
        self._coordinates = coordinates
        self._shading = shading

    def set_array(self, A):
        """
        Set the data values.

        Parameters
        ----------
        A : array-like
            The mesh data. Supported array shapes are:

            - (M, N) or (M*N,): a mesh with scalar data. The values are mapped
              to colors using normalization and a colormap. See parameters
              *norm*, *cmap*, *vmin*, *vmax*.
            - (M, N, 3): an image with RGB values (0-1 float or 0-255 int).
            - (M, N, 4): an image with RGBA values (0-1 float or 0-255 int),
              i.e. including transparency.

            If the values are provided as a 2D grid, the shape must match the
            coordinates grid. If the values are 1D, they are reshaped to 2D.
            M, N follow from the coordinates grid, where the coordinates grid
            shape is (M, N) for 'gouraud' *shading* and (M+1, N+1) for 'flat'
            shading.
        """
        height, width = self._coordinates.shape[0:-1]
        if self._shading == 'flat':
            h, w = height - 1, width - 1
        else:
            h, w = height, width
        ok_shapes = [(h, w, 3), (h, w, 4), (h, w), (h * w,)]
        if A is not None:
            shape = np.shape(A)
            if shape not in ok_shapes:
                raise ValueError(
                    f"For X ({width}) and Y ({height}) with {self._shading} "
                    f"shading, A should have shape "
                    f"{' or '.join(map(str, ok_shapes))}, not {A.shape}")
        return super().set_array(A)

    def get_coordinates(self):
        """
        Return the vertices of the mesh as an (M+1, N+1, 2) array.

        M, N are the number of quadrilaterals in the rows / columns of the
        mesh, corresponding to (M+1, N+1) vertices.
        The last dimension specifies the components (x, y).
        """
        return self._coordinates

    def get_edgecolor(self):
        # docstring inherited
        # Note that we want to return an array of shape (N*M, 4)
        # a flattened RGBA collection
        return super().get_edgecolor().reshape(-1, 4)

    def get_facecolor(self):
        # docstring inherited
        # Note that we want to return an array of shape (N*M, 4)
        # a flattened RGBA collection
        return super().get_facecolor().reshape(-1, 4)

    @staticmethod
    def _convert_mesh_to_paths(coordinates):
        """
        Convert a given mesh into a sequence of `.Path` objects.

        This function is primarily of use to implementers of backends that do
        not directly support quadmeshes.
        """
        if isinstance(coordinates, np.ma.MaskedArray):
            c = coordinates.data
        else:
            c = coordinates
        points = np.concatenate([
            c[:-1, :-1],
            c[:-1, 1:],
            c[1:, 1:],
            c[1:, :-1],
            c[:-1, :-1]
        ], axis=2).reshape((-1, 5, 2))
        return [mpath.Path(x) for x in points]

    def _convert_mesh_to_triangles(self, coordinates):
        """
        Convert a given mesh into a sequence of triangles, each point
        with its own color.  The result can be used to construct a call to
        `~.RendererBase.draw_gouraud_triangles`.
        """
        if isinstance(coordinates, np.ma.MaskedArray):
            p = coordinates.data
        else:
            p = coordinates

        p_a = p[:-1, :-1]
        p_b = p[:-1, 1:]
        p_c = p[1:, 1:]
        p_d = p[1:, :-1]
        p_center = (p_a + p_b + p_c + p_d) / 4.0
        triangles = np.concatenate([
            p_a, p_b, p_center,
            p_b, p_c, p_center,
            p_c, p_d, p_center,
            p_d, p_a, p_center,
        ], axis=2).reshape((-1, 3, 2))

        c = self.get_facecolor().reshape((*coordinates.shape[:2], 4))
        z = self.get_array()
        mask = z.mask if np.ma.is_masked(z) else None
        if mask is not None:
            c[mask, 3] = np.nan
        c_a = c[:-1, :-1]
        c_b = c[:-1, 1:]
        c_c = c[1:, 1:]
        c_d = c[1:, :-1]
        c_center = (c_a + c_b + c_c + c_d) / 4.0
        colors = np.concatenate([
            c_a, c_b, c_center,
            c_b, c_c, c_center,
            c_c, c_d, c_center,
            c_d, c_a, c_center,
        ], axis=2).reshape((-1, 3, 4))
        tmask = np.isnan(colors[..., 2, 3])
        return triangles[~tmask], colors[~tmask]


class QuadMesh(_MeshData, Collection):
    r"""
    Class for the efficient drawing of a quadrilateral mesh.

    A quadrilateral mesh is a grid of M by N adjacent quadrilaterals that are
    defined via a (M+1, N+1) grid of vertices. The quadrilateral (m, n) is
    defined by the vertices ::

               (m+1, n) ----------- (m+1, n+1)
                  /                   /
                 /                 /
                /               /
            (m, n) -------- (m, n+1)

    The mesh need not be regular and the polygons need not be convex.

    Parameters
    ----------
    coordinates : (M+1, N+1, 2) array-like
        The vertices. ``coordinates[m, n]`` specifies the (x, y) coordinates
        of vertex (m, n).

    antialiased : bool, default: True

    shading : {'flat', 'gouraud'}, default: 'flat'

    Notes
    -----
    Unlike other `.Collection`\s, the default *pickradius* of `.QuadMesh` is 0,
    i.e. `~.Artist.contains` checks whether the test point is within any of the
    mesh quadrilaterals.

    """

    def __init__(self, coordinates, *, antialiased=True, shading='flat',
                 **kwargs):
        kwargs.setdefault("pickradius", 0)
        super().__init__(coordinates=coordinates, shading=shading)
        Collection.__init__(self, **kwargs)

        self._antialiased = antialiased
        self._bbox = transforms.Bbox.unit()
        self._bbox.update_from_data_xy(self._coordinates.reshape(-1, 2))
        self.set_mouseover(False)

    def get_paths(self):
        if self._paths is None:
            self.set_paths()
        return self._paths

    def set_paths(self):
        self._paths = self._convert_mesh_to_paths(self._coordinates)
        self.stale = True

    def get_datalim(self, transData):
        return (self.get_transform() - transData).transform_bbox(self._bbox)

    @artist.allow_rasterization
    def draw(self, renderer):
        if not self.get_visible():
            return
        renderer.open_group(self.__class__.__name__, self.get_gid())
        transform = self.get_transform()
        offset_trf = self.get_offset_transform()
        offsets = self.get_offsets()

        if self.have_units():
            xs = self.convert_xunits(offsets[:, 0])
            ys = self.convert_yunits(offsets[:, 1])
            offsets = np.column_stack([xs, ys])

        self.update_scalarmappable()

        if not transform.is_affine:
            coordinates = self._coordinates.reshape((-1, 2))
            coordinates = transform.transform(coordinates)
            coordinates = coordinates.reshape(self._coordinates.shape)
            transform = transforms.IdentityTransform()
        else:
            coordinates = self._coordinates

        if not offset_trf.is_affine:
            offsets = offset_trf.transform_non_affine(offsets)
            offset_trf = offset_trf.get_affine()

        gc = renderer.new_gc()
        gc.set_snap(self.get_snap())
        self._set_gc_clip(gc)
        gc.set_linewidth(self.get_linewidth()[0])

        if self._shading == 'gouraud':
            triangles, colors = self._convert_mesh_to_triangles(coordinates)
            renderer.draw_gouraud_triangles(
                gc, triangles, colors, transform.frozen())
        else:
            renderer.draw_quad_mesh(
                gc, transform.frozen(),
                coordinates.shape[1] - 1, coordinates.shape[0] - 1,
                coordinates, offsets, offset_trf,
                # Backends expect flattened rgba arrays (n*m, 4) for fc and ec
                self.get_facecolor().reshape((-1, 4)),
                self._antialiased, self.get_edgecolors().reshape((-1, 4)))
        gc.restore()
        renderer.close_group(self.__class__.__name__)
        self.stale = False

    def get_cursor_data(self, event):
        contained, info = self.contains(event)
        if contained and self.get_array() is not None:
            return self.get_array().ravel()[info["ind"]]
        return None


class PolyQuadMesh(_MeshData, PolyCollection):
    """
    Class for drawing a quadrilateral mesh as individual Polygons.

    A quadrilateral mesh is a grid of M by N adjacent quadrilaterals that are
    defined via a (M+1, N+1) grid of vertices. The quadrilateral (m, n) is
    defined by the vertices ::

               (m+1, n) ----------- (m+1, n+1)
                  /                   /
                 /                 /
                /               /
            (m, n) -------- (m, n+1)

    The mesh need not be regular and the polygons need not be convex.

    Parameters
    ----------
    coordinates : (M+1, N+1, 2) array-like
        The vertices. ``coordinates[m, n]`` specifies the (x, y) coordinates
        of vertex (m, n).

    Notes
    -----
    Unlike `.QuadMesh`, this class will draw each cell as an individual Polygon.
    This is significantly slower, but allows for more flexibility when wanting
    to add additional properties to the cells, such as hatching.

    Another difference from `.QuadMesh` is that if any of the vertices or data
    of a cell are masked, that Polygon will **not** be drawn and it won't be in
    the list of paths returned.
    """

    def __init__(self, coordinates, **kwargs):
        super().__init__(coordinates=coordinates)
        PolyCollection.__init__(self, verts=[], **kwargs)
        # Setting the verts updates the paths of the PolyCollection
        # This is called after the initializers to make sure the kwargs
        # have all been processed and available for the masking calculations
        self._set_unmasked_verts()

    def _get_unmasked_polys(self):
        """Get the unmasked regions using the coordinates and array"""
        # mask(X) | mask(Y)
        mask = np.any(np.ma.getmaskarray(self._coordinates), axis=-1)

        # We want the shape of the polygon, which is the corner of each X/Y array
        mask = (mask[0:-1, 0:-1] | mask[1:, 1:] | mask[0:-1, 1:] | mask[1:, 0:-1])
        arr = self.get_array()
        if arr is not None:
            arr = np.ma.getmaskarray(arr)
            if arr.ndim == 3:
                # RGB(A) case
                mask |= np.any(arr, axis=-1)
            elif arr.ndim == 2:
                mask |= arr
            else:
                mask |= arr.reshape(self._coordinates[:-1, :-1, :].shape[:2])
        return ~mask

    def _set_unmasked_verts(self):
        X = self._coordinates[..., 0]
        Y = self._coordinates[..., 1]

        unmask = self._get_unmasked_polys()
        X1 = np.ma.filled(X[:-1, :-1])[unmask]
        Y1 = np.ma.filled(Y[:-1, :-1])[unmask]
        X2 = np.ma.filled(X[1:, :-1])[unmask]
        Y2 = np.ma.filled(Y[1:, :-1])[unmask]
        X3 = np.ma.filled(X[1:, 1:])[unmask]
        Y3 = np.ma.filled(Y[1:, 1:])[unmask]
        X4 = np.ma.filled(X[:-1, 1:])[unmask]
        Y4 = np.ma.filled(Y[:-1, 1:])[unmask]
        npoly = len(X1)

        xy = np.ma.stack([X1, Y1, X2, Y2, X3, Y3, X4, Y4, X1, Y1], axis=-1)
        verts = xy.reshape((npoly, 5, 2))
        self.set_verts(verts)

    def get_edgecolor(self):
        # docstring inherited
        # We only want to return the facecolors of the polygons
        # that were drawn.
        ec = super().get_edgecolor()
        unmasked_polys = self._get_unmasked_polys().ravel()
        if len(ec) != len(unmasked_polys):
            # Mapping is off
            return ec
        return ec[unmasked_polys, :]

    def get_facecolor(self):
        # docstring inherited
        # We only want to return the facecolors of the polygons
        # that were drawn.
        fc = super().get_facecolor()
        unmasked_polys = self._get_unmasked_polys().ravel()
        if len(fc) != len(unmasked_polys):
            # Mapping is off
            return fc
        return fc[unmasked_polys, :]

    def set_array(self, A):
        # docstring inherited
        prev_unmask = self._get_unmasked_polys()
        super().set_array(A)
        # If the mask has changed at all we need to update
        # the set of Polys that we are drawing
        if not np.array_equal(prev_unmask, self._get_unmasked_polys()):
            self._set_unmasked_verts()

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\css.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: CSS (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import page


class StyleSheetId(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> StyleSheetId:
        return cls(json)

    def __repr__(self):
        return 'StyleSheetId({})'.format(super().__repr__())


class StyleSheetOrigin(enum.Enum):
    '''
    Stylesheet type: "injected" for stylesheets injected via extension, "user-agent" for user-agent
    stylesheets, "inspector" for stylesheets created by the inspector (i.e. those holding the "via
    inspector" rules), "regular" for regular stylesheets.
    '''
    INJECTED = "injected"
    USER_AGENT = "user-agent"
    INSPECTOR = "inspector"
    REGULAR = "regular"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PseudoElementMatches:
    '''
    CSS rule collection for a single pseudo style.
    '''
    #: Pseudo element type.
    pseudo_type: dom.PseudoType

    #: Matches of CSS rules applicable to the pseudo style.
    matches: typing.List[RuleMatch]

    #: Pseudo element custom ident.
    pseudo_identifier: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['pseudoType'] = self.pseudo_type.to_json()
        json['matches'] = [i.to_json() for i in self.matches]
        if self.pseudo_identifier is not None:
            json['pseudoIdentifier'] = self.pseudo_identifier
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            pseudo_type=dom.PseudoType.from_json(json['pseudoType']),
            matches=[RuleMatch.from_json(i) for i in json['matches']],
            pseudo_identifier=str(json['pseudoIdentifier']) if 'pseudoIdentifier' in json else None,
        )


@dataclass
class CSSAnimationStyle:
    '''
    CSS style coming from animations with the name of the animation.
    '''
    #: The style coming from the animation.
    style: CSSStyle

    #: The name of the animation.
    name: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['style'] = self.style.to_json()
        if self.name is not None:
            json['name'] = self.name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            style=CSSStyle.from_json(json['style']),
            name=str(json['name']) if 'name' in json else None,
        )


@dataclass
class InheritedStyleEntry:
    '''
    Inherited CSS rule collection from ancestor node.
    '''
    #: Matches of CSS rules matching the ancestor node in the style inheritance chain.
    matched_css_rules: typing.List[RuleMatch]

    #: The ancestor node's inline style, if any, in the style inheritance chain.
    inline_style: typing.Optional[CSSStyle] = None

    def to_json(self):
        json = dict()
        json['matchedCSSRules'] = [i.to_json() for i in self.matched_css_rules]
        if self.inline_style is not None:
            json['inlineStyle'] = self.inline_style.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            matched_css_rules=[RuleMatch.from_json(i) for i in json['matchedCSSRules']],
            inline_style=CSSStyle.from_json(json['inlineStyle']) if 'inlineStyle' in json else None,
        )


@dataclass
class InheritedAnimatedStyleEntry:
    '''
    Inherited CSS style collection for animated styles from ancestor node.
    '''
    #: Styles coming from the animations of the ancestor, if any, in the style inheritance chain.
    animation_styles: typing.Optional[typing.List[CSSAnimationStyle]] = None

    #: The style coming from the transitions of the ancestor, if any, in the style inheritance chain.
    transitions_style: typing.Optional[CSSStyle] = None

    def to_json(self):
        json = dict()
        if self.animation_styles is not None:
            json['animationStyles'] = [i.to_json() for i in self.animation_styles]
        if self.transitions_style is not None:
            json['transitionsStyle'] = self.transitions_style.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            animation_styles=[CSSAnimationStyle.from_json(i) for i in json['animationStyles']] if 'animationStyles' in json else None,
            transitions_style=CSSStyle.from_json(json['transitionsStyle']) if 'transitionsStyle' in json else None,
        )


@dataclass
class InheritedPseudoElementMatches:
    '''
    Inherited pseudo element matches from pseudos of an ancestor node.
    '''
    #: Matches of pseudo styles from the pseudos of an ancestor node.
    pseudo_elements: typing.List[PseudoElementMatches]

    def to_json(self):
        json = dict()
        json['pseudoElements'] = [i.to_json() for i in self.pseudo_elements]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            pseudo_elements=[PseudoElementMatches.from_json(i) for i in json['pseudoElements']],
        )


@dataclass
class RuleMatch:
    '''
    Match data for a CSS rule.
    '''
    #: CSS rule in the match.
    rule: CSSRule

    #: Matching selector indices in the rule's selectorList selectors (0-based).
    matching_selectors: typing.List[int]

    def to_json(self):
        json = dict()
        json['rule'] = self.rule.to_json()
        json['matchingSelectors'] = [i for i in self.matching_selectors]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            rule=CSSRule.from_json(json['rule']),
            matching_selectors=[int(i) for i in json['matchingSelectors']],
        )


@dataclass
class Value:
    '''
    Data for a simple selector (these are delimited by commas in a selector list).
    '''
    #: Value text.
    text: str

    #: Value range in the underlying resource (if available).
    range_: typing.Optional[SourceRange] = None

    #: Specificity of the selector.
    specificity: typing.Optional[Specificity] = None

    def to_json(self):
        json = dict()
        json['text'] = self.text
        if self.range_ is not None:
            json['range'] = self.range_.to_json()
        if self.specificity is not None:
            json['specificity'] = self.specificity.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            text=str(json['text']),
            range_=SourceRange.from_json(json['range']) if 'range' in json else None,
            specificity=Specificity.from_json(json['specificity']) if 'specificity' in json else None,
        )


@dataclass
class Specificity:
    '''
    Specificity:
    https://drafts.csswg.org/selectors/#specificity-rules
    '''
    #: The a component, which represents the number of ID selectors.
    a: int

    #: The b component, which represents the number of class selectors, attributes selectors, and
    #: pseudo-classes.
    b: int

    #: The c component, which represents the number of type selectors and pseudo-elements.
    c: int

    def to_json(self):
        json = dict()
        json['a'] = self.a
        json['b'] = self.b
        json['c'] = self.c
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            a=int(json['a']),
            b=int(json['b']),
            c=int(json['c']),
        )


@dataclass
class SelectorList:
    '''
    Selector list data.
    '''
    #: Selectors in the list.
    selectors: typing.List[Value]

    #: Rule selector text.
    text: str

    def to_json(self):
        json = dict()
        json['selectors'] = [i.to_json() for i in self.selectors]
        json['text'] = self.text
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            selectors=[Value.from_json(i) for i in json['selectors']],
            text=str(json['text']),
        )


@dataclass
class CSSStyleSheetHeader:
    '''
    CSS stylesheet metainformation.
    '''
    #: The stylesheet identifier.
    style_sheet_id: StyleSheetId

    #: Owner frame identifier.
    frame_id: page.FrameId

    #: Stylesheet resource URL. Empty if this is a constructed stylesheet created using
    #: new CSSStyleSheet() (but non-empty if this is a constructed stylesheet imported
    #: as a CSS module script).
    source_url: str

    #: Stylesheet origin.
    origin: StyleSheetOrigin

    #: Stylesheet title.
    title: str

    #: Denotes whether the stylesheet is disabled.
    disabled: bool

    #: Whether this stylesheet is created for STYLE tag by parser. This flag is not set for
    #: document.written STYLE tags.
    is_inline: bool

    #: Whether this stylesheet is mutable. Inline stylesheets become mutable
    #: after they have been modified via CSSOM API.
    #: ``<link>`` element's stylesheets become mutable only if DevTools modifies them.
    #: Constructed stylesheets (new CSSStyleSheet()) are mutable immediately after creation.
    is_mutable: bool

    #: True if this stylesheet is created through new CSSStyleSheet() or imported as a
    #: CSS module script.
    is_constructed: bool

    #: Line offset of the stylesheet within the resource (zero based).
    start_line: float

    #: Column offset of the stylesheet within the resource (zero based).
    start_column: float

    #: Size of the content (in characters).
    length: float

    #: Line offset of the end of the stylesheet within the resource (zero based).
    end_line: float

    #: Column offset of the end of the stylesheet within the resource (zero based).
    end_column: float

    #: URL of source map associated with the stylesheet (if any).
    source_map_url: typing.Optional[str] = None

    #: The backend id for the owner node of the stylesheet.
    owner_node: typing.Optional[dom.BackendNodeId] = None

    #: Whether the sourceURL field value comes from the sourceURL comment.
    has_source_url: typing.Optional[bool] = None

    #: If the style sheet was loaded from a network resource, this indicates when the resource failed to load
    loading_failed: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['styleSheetId'] = self.style_sheet_id.to_json()
        json['frameId'] = self.frame_id.to_json()
        json['sourceURL'] = self.source_url
        json['origin'] = self.origin.to_json()
        json['title'] = self.title
        json['disabled'] = self.disabled
        json['isInline'] = self.is_inline
        json['isMutable'] = self.is_mutable
        json['isConstructed'] = self.is_constructed
        json['startLine'] = self.start_line
        json['startColumn'] = self.start_column
        json['length'] = self.length
        json['endLine'] = self.end_line
        json['endColumn'] = self.end_column
        if self.source_map_url is not None:
            json['sourceMapURL'] = self.source_map_url
        if self.owner_node is not None:
            json['ownerNode'] = self.owner_node.to_json()
        if self.has_source_url is not None:
            json['hasSourceURL'] = self.has_source_url
        if self.loading_failed is not None:
            json['loadingFailed'] = self.loading_failed
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']),
            frame_id=page.FrameId.from_json(json['frameId']),
            source_url=str(json['sourceURL']),
            origin=StyleSheetOrigin.from_json(json['origin']),
            title=str(json['title']),
            disabled=bool(json['disabled']),
            is_inline=bool(json['isInline']),
            is_mutable=bool(json['isMutable']),
            is_constructed=bool(json['isConstructed']),
            start_line=float(json['startLine']),
            start_column=float(json['startColumn']),
            length=float(json['length']),
            end_line=float(json['endLine']),
            end_column=float(json['endColumn']),
            source_map_url=str(json['sourceMapURL']) if 'sourceMapURL' in json else None,
            owner_node=dom.BackendNodeId.from_json(json['ownerNode']) if 'ownerNode' in json else None,
            has_source_url=bool(json['hasSourceURL']) if 'hasSourceURL' in json else None,
            loading_failed=bool(json['loadingFailed']) if 'loadingFailed' in json else None,
        )


@dataclass
class CSSRule:
    '''
    CSS rule representation.
    '''
    #: Rule selector data.
    selector_list: SelectorList

    #: Parent stylesheet's origin.
    origin: StyleSheetOrigin

    #: Associated style declaration.
    style: CSSStyle

    #: The css style sheet identifier (absent for user agent stylesheet and user-specified
    #: stylesheet rules) this rule came from.
    style_sheet_id: typing.Optional[StyleSheetId] = None

    #: Array of selectors from ancestor style rules, sorted by distance from the current rule.
    nesting_selectors: typing.Optional[typing.List[str]] = None

    #: Media list array (for rules involving media queries). The array enumerates media queries
    #: starting with the innermost one, going outwards.
    media: typing.Optional[typing.List[CSSMedia]] = None

    #: Container query list array (for rules involving container queries).
    #: The array enumerates container queries starting with the innermost one, going outwards.
    container_queries: typing.Optional[typing.List[CSSContainerQuery]] = None

    #: @supports CSS at-rule array.
    #: The array enumerates @supports at-rules starting with the innermost one, going outwards.
    supports: typing.Optional[typing.List[CSSSupports]] = None

    #: Cascade layer array. Contains the layer hierarchy that this rule belongs to starting
    #: with the innermost layer and going outwards.
    layers: typing.Optional[typing.List[CSSLayer]] = None

    #: @scope CSS at-rule array.
    #: The array enumerates @scope at-rules starting with the innermost one, going outwards.
    scopes: typing.Optional[typing.List[CSSScope]] = None

    #: The array keeps the types of ancestor CSSRules from the innermost going outwards.
    rule_types: typing.Optional[typing.List[CSSRuleType]] = None

    #: @starting-style CSS at-rule array.
    #: The array enumerates @starting-style at-rules starting with the innermost one, going outwards.
    starting_styles: typing.Optional[typing.List[CSSStartingStyle]] = None

    def to_json(self):
        json = dict()
        json['selectorList'] = self.selector_list.to_json()
        json['origin'] = self.origin.to_json()
        json['style'] = self.style.to_json()
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        if self.nesting_selectors is not None:
            json['nestingSelectors'] = [i for i in self.nesting_selectors]
        if self.media is not None:
            json['media'] = [i.to_json() for i in self.media]
        if self.container_queries is not None:
            json['containerQueries'] = [i.to_json() for i in self.container_queries]
        if self.supports is not None:
            json['supports'] = [i.to_json() for i in self.supports]
        if self.layers is not None:
            json['layers'] = [i.to_json() for i in self.layers]
        if self.scopes is not None:
            json['scopes'] = [i.to_json() for i in self.scopes]
        if self.rule_types is not None:
            json['ruleTypes'] = [i.to_json() for i in self.rule_types]
        if self.starting_styles is not None:
            json['startingStyles'] = [i.to_json() for i in self.starting_styles]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            selector_list=SelectorList.from_json(json['selectorList']),
            origin=StyleSheetOrigin.from_json(json['origin']),
            style=CSSStyle.from_json(json['style']),
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
            nesting_selectors=[str(i) for i in json['nestingSelectors']] if 'nestingSelectors' in json else None,
            media=[CSSMedia.from_json(i) for i in json['media']] if 'media' in json else None,
            container_queries=[CSSContainerQuery.from_json(i) for i in json['containerQueries']] if 'containerQueries' in json else None,
            supports=[CSSSupports.from_json(i) for i in json['supports']] if 'supports' in json else None,
            layers=[CSSLayer.from_json(i) for i in json['layers']] if 'layers' in json else None,
            scopes=[CSSScope.from_json(i) for i in json['scopes']] if 'scopes' in json else None,
            rule_types=[CSSRuleType.from_json(i) for i in json['ruleTypes']] if 'ruleTypes' in json else None,
            starting_styles=[CSSStartingStyle.from_json(i) for i in json['startingStyles']] if 'startingStyles' in json else None,
        )


class CSSRuleType(enum.Enum):
    '''
    Enum indicating the type of a CSS rule, used to represent the order of a style rule's ancestors.
    This list only contains rule types that are collected during the ancestor rule collection.
    '''
    MEDIA_RULE = "MediaRule"
    SUPPORTS_RULE = "SupportsRule"
    CONTAINER_RULE = "ContainerRule"
    LAYER_RULE = "LayerRule"
    SCOPE_RULE = "ScopeRule"
    STYLE_RULE = "StyleRule"
    STARTING_STYLE_RULE = "StartingStyleRule"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class RuleUsage:
    '''
    CSS coverage information.
    '''
    #: The css style sheet identifier (absent for user agent stylesheet and user-specified
    #: stylesheet rules) this rule came from.
    style_sheet_id: StyleSheetId

    #: Offset of the start of the rule (including selector) from the beginning of the stylesheet.
    start_offset: float

    #: Offset of the end of the rule body from the beginning of the stylesheet.
    end_offset: float

    #: Indicates whether the rule was actually used by some element in the page.
    used: bool

    def to_json(self):
        json = dict()
        json['styleSheetId'] = self.style_sheet_id.to_json()
        json['startOffset'] = self.start_offset
        json['endOffset'] = self.end_offset
        json['used'] = self.used
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']),
            start_offset=float(json['startOffset']),
            end_offset=float(json['endOffset']),
            used=bool(json['used']),
        )


@dataclass
class SourceRange:
    '''
    Text range within a resource. All numbers are zero-based.
    '''
    #: Start line of range.
    start_line: int

    #: Start column of range (inclusive).
    start_column: int

    #: End line of range
    end_line: int

    #: End column of range (exclusive).
    end_column: int

    def to_json(self):
        json = dict()
        json['startLine'] = self.start_line
        json['startColumn'] = self.start_column
        json['endLine'] = self.end_line
        json['endColumn'] = self.end_column
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            start_line=int(json['startLine']),
            start_column=int(json['startColumn']),
            end_line=int(json['endLine']),
            end_column=int(json['endColumn']),
        )


@dataclass
class ShorthandEntry:
    #: Shorthand name.
    name: str

    #: Shorthand value.
    value: str

    #: Whether the property has "!important" annotation (implies ``false`` if absent).
    important: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        if self.important is not None:
            json['important'] = self.important
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
            important=bool(json['important']) if 'important' in json else None,
        )


@dataclass
class CSSComputedStyleProperty:
    #: Computed style property name.
    name: str

    #: Computed style property value.
    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


@dataclass
class CSSStyle:
    '''
    CSS style representation.
    '''
    #: CSS properties in the style.
    css_properties: typing.List[CSSProperty]

    #: Computed values for all shorthands found in the style.
    shorthand_entries: typing.List[ShorthandEntry]

    #: The css style sheet identifier (absent for user agent stylesheet and user-specified
    #: stylesheet rules) this rule came from.
    style_sheet_id: typing.Optional[StyleSheetId] = None

    #: Style declaration text (if available).
    css_text: typing.Optional[str] = None

    #: Style declaration range in the enclosing stylesheet (if available).
    range_: typing.Optional[SourceRange] = None

    def to_json(self):
        json = dict()
        json['cssProperties'] = [i.to_json() for i in self.css_properties]
        json['shorthandEntries'] = [i.to_json() for i in self.shorthand_entries]
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        if self.css_text is not None:
            json['cssText'] = self.css_text
        if self.range_ is not None:
            json['range'] = self.range_.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            css_properties=[CSSProperty.from_json(i) for i in json['cssProperties']],
            shorthand_entries=[ShorthandEntry.from_json(i) for i in json['shorthandEntries']],
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
            css_text=str(json['cssText']) if 'cssText' in json else None,
            range_=SourceRange.from_json(json['range']) if 'range' in json else None,
        )


@dataclass
class CSSProperty:
    '''
    CSS property declaration data.
    '''
    #: The property name.
    name: str

    #: The property value.
    value: str

    #: Whether the property has "!important" annotation (implies ``false`` if absent).
    important: typing.Optional[bool] = None

    #: Whether the property is implicit (implies ``false`` if absent).
    implicit: typing.Optional[bool] = None

    #: The full property text as specified in the style.
    text: typing.Optional[str] = None

    #: Whether the property is understood by the browser (implies ``true`` if absent).
    parsed_ok: typing.Optional[bool] = None

    #: Whether the property is disabled by the user (present for source-based properties only).
    disabled: typing.Optional[bool] = None

    #: The entire property range in the enclosing style declaration (if available).
    range_: typing.Optional[SourceRange] = None

    #: Parsed longhand components of this property if it is a shorthand.
    #: This field will be empty if the given property is not a shorthand.
    longhand_properties: typing.Optional[typing.List[CSSProperty]] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        if self.important is not None:
            json['important'] = self.important
        if self.implicit is not None:
            json['implicit'] = self.implicit
        if self.text is not None:
            json['text'] = self.text
        if self.parsed_ok is not None:
            json['parsedOk'] = self.parsed_ok
        if self.disabled is not None:
            json['disabled'] = self.disabled
        if self.range_ is not None:
            json['range'] = self.range_.to_json()
        if self.longhand_properties is not None:
            json['longhandProperties'] = [i.to_json() for i in self.longhand_properties]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
            important=bool(json['important']) if 'important' in json else None,
            implicit=bool(json['implicit']) if 'implicit' in json else None,
            text=str(json['text']) if 'text' in json else None,
            parsed_ok=bool(json['parsedOk']) if 'parsedOk' in json else None,
            disabled=bool(json['disabled']) if 'disabled' in json else None,
            range_=SourceRange.from_json(json['range']) if 'range' in json else None,
            longhand_properties=[CSSProperty.from_json(i) for i in json['longhandProperties']] if 'longhandProperties' in json else None,
        )


@dataclass
class CSSMedia:
    '''
    CSS media rule descriptor.
    '''
    #: Media query text.
    text: str

    #: Source of the media query: "mediaRule" if specified by a @media rule, "importRule" if
    #: specified by an @import rule, "linkedSheet" if specified by a "media" attribute in a linked
    #: stylesheet's LINK tag, "inlineSheet" if specified by a "media" attribute in an inline
    #: stylesheet's STYLE tag.
    source: str

    #: URL of the document containing the media query description.
    source_url: typing.Optional[str] = None

    #: The associated rule (@media or @import) header range in the enclosing stylesheet (if
    #: available).
    range_: typing.Optional[SourceRange] = None

    #: Identifier of the stylesheet containing this object (if exists).
    style_sheet_id: typing.Optional[StyleSheetId] = None

    #: Array of media queries.
    media_list: typing.Optional[typing.List[MediaQuery]] = None

    def to_json(self):
        json = dict()
        json['text'] = self.text
        json['source'] = self.source
        if self.source_url is not None:
            json['sourceURL'] = self.source_url
        if self.range_ is not None:
            json['range'] = self.range_.to_json()
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        if self.media_list is not None:
            json['mediaList'] = [i.to_json() for i in self.media_list]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            text=str(json['text']),
            source=str(json['source']),
            source_url=str(json['sourceURL']) if 'sourceURL' in json else None,
            range_=SourceRange.from_json(json['range']) if 'range' in json else None,
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
            media_list=[MediaQuery.from_json(i) for i in json['mediaList']] if 'mediaList' in json else None,
        )


@dataclass
class MediaQuery:
    '''
    Media query descriptor.
    '''
    #: Array of media query expressions.
    expressions: typing.List[MediaQueryExpression]

    #: Whether the media query condition is satisfied.
    active: bool

    def to_json(self):
        json = dict()
        json['expressions'] = [i.to_json() for i in self.expressions]
        json['active'] = self.active
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            expressions=[MediaQueryExpression.from_json(i) for i in json['expressions']],
            active=bool(json['active']),
        )


@dataclass
class MediaQueryExpression:
    '''
    Media query expression descriptor.
    '''
    #: Media query expression value.
    value: float

    #: Media query expression units.
    unit: str

    #: Media query expression feature.
    feature: str

    #: The associated range of the value text in the enclosing stylesheet (if available).
    value_range: typing.Optional[SourceRange] = None

    #: Computed length of media query expression (if applicable).
    computed_length: typing.Optional[float] = None

    def to_json(self):
        json = dict()
        json['value'] = self.value
        json['unit'] = self.unit
        json['feature'] = self.feature
        if self.value_range is not None:
            json['valueRange'] = self.value_range.to_json()
        if self.computed_length is not None:
            json['computedLength'] = self.computed_length
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=float(json['value']),
            unit=str(json['unit']),
            feature=str(json['feature']),
            value_range=SourceRange.from_json(json['valueRange']) if 'valueRange' in json else None,
            computed_length=float(json['computedLength']) if 'computedLength' in json else None,
        )


@dataclass
class CSSContainerQuery:
    '''
    CSS container query rule descriptor.
    '''
    #: Container query text.
    text: str

    #: The associated rule header range in the enclosing stylesheet (if
    #: available).
    range_: typing.Optional[SourceRange] = None

    #: Identifier of the stylesheet containing this object (if exists).
    style_sheet_id: typing.Optional[StyleSheetId] = None

    #: Optional name for the container.
    name: typing.Optional[str] = None

    #: Optional physical axes queried for the container.
    physical_axes: typing.Optional[dom.PhysicalAxes] = None

    #: Optional logical axes queried for the container.
    logical_axes: typing.Optional[dom.LogicalAxes] = None

    #: true if the query contains scroll-state() queries.
    queries_scroll_state: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['text'] = self.text
        if self.range_ is not None:
            json['range'] = self.range_.to_json()
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        if self.name is not None:
            json['name'] = self.name
        if self.physical_axes is not None:
            json['physicalAxes'] = self.physical_axes.to_json()
        if self.logical_axes is not None:
            json['logicalAxes'] = self.logical_axes.to_json()
        if self.queries_scroll_state is not None:
            json['queriesScrollState'] = self.queries_scroll_state
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            text=str(json['text']),
            range_=SourceRange.from_json(json['range']) if 'range' in json else None,
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
            name=str(json['name']) if 'name' in json else None,
            physical_axes=dom.PhysicalAxes.from_json(json['physicalAxes']) if 'physicalAxes' in json else None,
            logical_axes=dom.LogicalAxes.from_json(json['logicalAxes']) if 'logicalAxes' in json else None,
            queries_scroll_state=bool(json['queriesScrollState']) if 'queriesScrollState' in json else None,
        )


@dataclass
class CSSSupports:
    '''
    CSS Supports at-rule descriptor.
    '''
    #: Supports rule text.
    text: str

    #: Whether the supports condition is satisfied.
    active: bool

    #: The associated rule header range in the enclosing stylesheet (if
    #: available).
    range_: typing.Optional[SourceRange] = None

    #: Identifier of the stylesheet containing this object (if exists).
    style_sheet_id: typing.Optional[StyleSheetId] = None

    def to_json(self):
        json = dict()
        json['text'] = self.text
        json['active'] = self.active
        if self.range_ is not None:
            json['range'] = self.range_.to_json()
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            text=str(json['text']),
            active=bool(json['active']),
            range_=SourceRange.from_json(json['range']) if 'range' in json else None,
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
        )


@dataclass
class CSSScope:
    '''
    CSS Scope at-rule descriptor.
    '''
    #: Scope rule text.
    text: str

    #: The associated rule header range in the enclosing stylesheet (if
    #: available).
    range_: typing.Optional[SourceRange] = None

    #: Identifier of the stylesheet containing this object (if exists).
    style_sheet_id: typing.Optional[StyleSheetId] = None

    def to_json(self):
        json = dict()
        json['text'] = self.text
        if self.range_ is not None:
            json['range'] = self.range_.to_json()
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            text=str(json['text']),
            range_=SourceRange.from_json(json['range']) if 'range' in json else None,
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
        )


@dataclass
class CSSLayer:
    '''
    CSS Layer at-rule descriptor.
    '''
    #: Layer name.
    text: str

    #: The associated rule header range in the enclosing stylesheet (if
    #: available).
    range_: typing.Optional[SourceRange] = None

    #: Identifier of the stylesheet containing this object (if exists).
    style_sheet_id: typing.Optional[StyleSheetId] = None

    def to_json(self):
        json = dict()
        json['text'] = self.text
        if self.range_ is not None:
            json['range'] = self.range_.to_json()
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            text=str(json['text']),
            range_=SourceRange.from_json(json['range']) if 'range' in json else None,
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
        )


@dataclass
class CSSStartingStyle:
    '''
    CSS Starting Style at-rule descriptor.
    '''
    #: The associated rule header range in the enclosing stylesheet (if
    #: available).
    range_: typing.Optional[SourceRange] = None

    #: Identifier of the stylesheet containing this object (if exists).
    style_sheet_id: typing.Optional[StyleSheetId] = None

    def to_json(self):
        json = dict()
        if self.range_ is not None:
            json['range'] = self.range_.to_json()
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            range_=SourceRange.from_json(json['range']) if 'range' in json else None,
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
        )


@dataclass
class CSSLayerData:
    '''
    CSS Layer data.
    '''
    #: Layer name.
    name: str

    #: Layer order. The order determines the order of the layer in the cascade order.
    #: A higher number has higher priority in the cascade order.
    order: float

    #: Direct sub-layers
    sub_layers: typing.Optional[typing.List[CSSLayerData]] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['order'] = self.order
        if self.sub_layers is not None:
            json['subLayers'] = [i.to_json() for i in self.sub_layers]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            order=float(json['order']),
            sub_layers=[CSSLayerData.from_json(i) for i in json['subLayers']] if 'subLayers' in json else None,
        )


@dataclass
class PlatformFontUsage:
    '''
    Information about amount of glyphs that were rendered with given font.
    '''
    #: Font's family name reported by platform.
    family_name: str

    #: Font's PostScript name reported by platform.
    post_script_name: str

    #: Indicates if the font was downloaded or resolved locally.
    is_custom_font: bool

    #: Amount of glyphs that were rendered with this font.
    glyph_count: float

    def to_json(self):
        json = dict()
        json['familyName'] = self.family_name
        json['postScriptName'] = self.post_script_name
        json['isCustomFont'] = self.is_custom_font
        json['glyphCount'] = self.glyph_count
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            family_name=str(json['familyName']),
            post_script_name=str(json['postScriptName']),
            is_custom_font=bool(json['isCustomFont']),
            glyph_count=float(json['glyphCount']),
        )


@dataclass
class FontVariationAxis:
    '''
    Information about font variation axes for variable fonts
    '''
    #: The font-variation-setting tag (a.k.a. "axis tag").
    tag: str

    #: Human-readable variation name in the default language (normally, "en").
    name: str

    #: The minimum value (inclusive) the font supports for this tag.
    min_value: float

    #: The maximum value (inclusive) the font supports for this tag.
    max_value: float

    #: The default value.
    default_value: float

    def to_json(self):
        json = dict()
        json['tag'] = self.tag
        json['name'] = self.name
        json['minValue'] = self.min_value
        json['maxValue'] = self.max_value
        json['defaultValue'] = self.default_value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            tag=str(json['tag']),
            name=str(json['name']),
            min_value=float(json['minValue']),
            max_value=float(json['maxValue']),
            default_value=float(json['defaultValue']),
        )


@dataclass
class FontFace:
    '''
    Properties of a web font: https://www.w3.org/TR/2008/REC-CSS2-20080411/fonts.html#font-descriptions
    and additional information such as platformFontFamily and fontVariationAxes.
    '''
    #: The font-family.
    font_family: str

    #: The font-style.
    font_style: str

    #: The font-variant.
    font_variant: str

    #: The font-weight.
    font_weight: str

    #: The font-stretch.
    font_stretch: str

    #: The font-display.
    font_display: str

    #: The unicode-range.
    unicode_range: str

    #: The src.
    src: str

    #: The resolved platform font family
    platform_font_family: str

    #: Available variation settings (a.k.a. "axes").
    font_variation_axes: typing.Optional[typing.List[FontVariationAxis]] = None

    def to_json(self):
        json = dict()
        json['fontFamily'] = self.font_family
        json['fontStyle'] = self.font_style
        json['fontVariant'] = self.font_variant
        json['fontWeight'] = self.font_weight
        json['fontStretch'] = self.font_stretch
        json['fontDisplay'] = self.font_display
        json['unicodeRange'] = self.unicode_range
        json['src'] = self.src
        json['platformFontFamily'] = self.platform_font_family
        if self.font_variation_axes is not None:
            json['fontVariationAxes'] = [i.to_json() for i in self.font_variation_axes]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            font_family=str(json['fontFamily']),
            font_style=str(json['fontStyle']),
            font_variant=str(json['fontVariant']),
            font_weight=str(json['fontWeight']),
            font_stretch=str(json['fontStretch']),
            font_display=str(json['fontDisplay']),
            unicode_range=str(json['unicodeRange']),
            src=str(json['src']),
            platform_font_family=str(json['platformFontFamily']),
            font_variation_axes=[FontVariationAxis.from_json(i) for i in json['fontVariationAxes']] if 'fontVariationAxes' in json else None,
        )


@dataclass
class CSSTryRule:
    '''
    CSS try rule representation.
    '''
    #: Parent stylesheet's origin.
    origin: StyleSheetOrigin

    #: Associated style declaration.
    style: CSSStyle

    #: The css style sheet identifier (absent for user agent stylesheet and user-specified
    #: stylesheet rules) this rule came from.
    style_sheet_id: typing.Optional[StyleSheetId] = None

    def to_json(self):
        json = dict()
        json['origin'] = self.origin.to_json()
        json['style'] = self.style.to_json()
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            origin=StyleSheetOrigin.from_json(json['origin']),
            style=CSSStyle.from_json(json['style']),
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
        )


@dataclass
class CSSPositionTryRule:
    '''
    CSS @position-try rule representation.
    '''
    #: The prelude dashed-ident name
    name: Value

    #: Parent stylesheet's origin.
    origin: StyleSheetOrigin

    #: Associated style declaration.
    style: CSSStyle

    active: bool

    #: The css style sheet identifier (absent for user agent stylesheet and user-specified
    #: stylesheet rules) this rule came from.
    style_sheet_id: typing.Optional[StyleSheetId] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name.to_json()
        json['origin'] = self.origin.to_json()
        json['style'] = self.style.to_json()
        json['active'] = self.active
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=Value.from_json(json['name']),
            origin=StyleSheetOrigin.from_json(json['origin']),
            style=CSSStyle.from_json(json['style']),
            active=bool(json['active']),
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
        )


@dataclass
class CSSKeyframesRule:
    '''
    CSS keyframes rule representation.
    '''
    #: Animation name.
    animation_name: Value

    #: List of keyframes.
    keyframes: typing.List[CSSKeyframeRule]

    def to_json(self):
        json = dict()
        json['animationName'] = self.animation_name.to_json()
        json['keyframes'] = [i.to_json() for i in self.keyframes]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            animation_name=Value.from_json(json['animationName']),
            keyframes=[CSSKeyframeRule.from_json(i) for i in json['keyframes']],
        )


@dataclass
class CSSPropertyRegistration:
    '''
    Representation of a custom property registration through CSS.registerProperty
    '''
    property_name: str

    inherits: bool

    syntax: str

    initial_value: typing.Optional[Value] = None

    def to_json(self):
        json = dict()
        json['propertyName'] = self.property_name
        json['inherits'] = self.inherits
        json['syntax'] = self.syntax
        if self.initial_value is not None:
            json['initialValue'] = self.initial_value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            property_name=str(json['propertyName']),
            inherits=bool(json['inherits']),
            syntax=str(json['syntax']),
            initial_value=Value.from_json(json['initialValue']) if 'initialValue' in json else None,
        )


@dataclass
class CSSFontPaletteValuesRule:
    '''
    CSS font-palette-values rule representation.
    '''
    #: Parent stylesheet's origin.
    origin: StyleSheetOrigin

    #: Associated font palette name.
    font_palette_name: Value

    #: Associated style declaration.
    style: CSSStyle

    #: The css style sheet identifier (absent for user agent stylesheet and user-specified
    #: stylesheet rules) this rule came from.
    style_sheet_id: typing.Optional[StyleSheetId] = None

    def to_json(self):
        json = dict()
        json['origin'] = self.origin.to_json()
        json['fontPaletteName'] = self.font_palette_name.to_json()
        json['style'] = self.style.to_json()
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            origin=StyleSheetOrigin.from_json(json['origin']),
            font_palette_name=Value.from_json(json['fontPaletteName']),
            style=CSSStyle.from_json(json['style']),
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
        )


@dataclass
class CSSPropertyRule:
    '''
    CSS property at-rule representation.
    '''
    #: Parent stylesheet's origin.
    origin: StyleSheetOrigin

    #: Associated property name.
    property_name: Value

    #: Associated style declaration.
    style: CSSStyle

    #: The css style sheet identifier (absent for user agent stylesheet and user-specified
    #: stylesheet rules) this rule came from.
    style_sheet_id: typing.Optional[StyleSheetId] = None

    def to_json(self):
        json = dict()
        json['origin'] = self.origin.to_json()
        json['propertyName'] = self.property_name.to_json()
        json['style'] = self.style.to_json()
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            origin=StyleSheetOrigin.from_json(json['origin']),
            property_name=Value.from_json(json['propertyName']),
            style=CSSStyle.from_json(json['style']),
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
        )


@dataclass
class CSSFunctionParameter:
    '''
    CSS function argument representation.
    '''
    #: The parameter name.
    name: str

    #: The parameter type.
    type_: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            type_=str(json['type']),
        )


@dataclass
class CSSFunctionConditionNode:
    '''
    CSS function conditional block representation.
    '''
    #: Block body.
    children: typing.List[CSSFunctionNode]

    #: The condition text.
    condition_text: str

    #: Media query for this conditional block. Only one type of condition should be set.
    media: typing.Optional[CSSMedia] = None

    #: Container query for this conditional block. Only one type of condition should be set.
    container_queries: typing.Optional[CSSContainerQuery] = None

    #: @supports CSS at-rule condition. Only one type of condition should be set.
    supports: typing.Optional[CSSSupports] = None

    def to_json(self):
        json = dict()
        json['children'] = [i.to_json() for i in self.children]
        json['conditionText'] = self.condition_text
        if self.media is not None:
            json['media'] = self.media.to_json()
        if self.container_queries is not None:
            json['containerQueries'] = self.container_queries.to_json()
        if self.supports is not None:
            json['supports'] = self.supports.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            children=[CSSFunctionNode.from_json(i) for i in json['children']],
            condition_text=str(json['conditionText']),
            media=CSSMedia.from_json(json['media']) if 'media' in json else None,
            container_queries=CSSContainerQuery.from_json(json['containerQueries']) if 'containerQueries' in json else None,
            supports=CSSSupports.from_json(json['supports']) if 'supports' in json else None,
        )


@dataclass
class CSSFunctionNode:
    '''
    Section of the body of a CSS function rule.
    '''
    #: A conditional block. If set, style should not be set.
    condition: typing.Optional[CSSFunctionConditionNode] = None

    #: Values set by this node. If set, condition should not be set.
    style: typing.Optional[CSSStyle] = None

    def to_json(self):
        json = dict()
        if self.condition is not None:
            json['condition'] = self.condition.to_json()
        if self.style is not None:
            json['style'] = self.style.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            condition=CSSFunctionConditionNode.from_json(json['condition']) if 'condition' in json else None,
            style=CSSStyle.from_json(json['style']) if 'style' in json else None,
        )


@dataclass
class CSSFunctionRule:
    '''
    CSS function at-rule representation.
    '''
    #: Name of the function.
    name: Value

    #: Parent stylesheet's origin.
    origin: StyleSheetOrigin

    #: List of parameters.
    parameters: typing.List[CSSFunctionParameter]

    #: Function body.
    children: typing.List[CSSFunctionNode]

    #: The css style sheet identifier (absent for user agent stylesheet and user-specified
    #: stylesheet rules) this rule came from.
    style_sheet_id: typing.Optional[StyleSheetId] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name.to_json()
        json['origin'] = self.origin.to_json()
        json['parameters'] = [i.to_json() for i in self.parameters]
        json['children'] = [i.to_json() for i in self.children]
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=Value.from_json(json['name']),
            origin=StyleSheetOrigin.from_json(json['origin']),
            parameters=[CSSFunctionParameter.from_json(i) for i in json['parameters']],
            children=[CSSFunctionNode.from_json(i) for i in json['children']],
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
        )


@dataclass
class CSSKeyframeRule:
    '''
    CSS keyframe rule representation.
    '''
    #: Parent stylesheet's origin.
    origin: StyleSheetOrigin

    #: Associated key text.
    key_text: Value

    #: Associated style declaration.
    style: CSSStyle

    #: The css style sheet identifier (absent for user agent stylesheet and user-specified
    #: stylesheet rules) this rule came from.
    style_sheet_id: typing.Optional[StyleSheetId] = None

    def to_json(self):
        json = dict()
        json['origin'] = self.origin.to_json()
        json['keyText'] = self.key_text.to_json()
        json['style'] = self.style.to_json()
        if self.style_sheet_id is not None:
            json['styleSheetId'] = self.style_sheet_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            origin=StyleSheetOrigin.from_json(json['origin']),
            key_text=Value.from_json(json['keyText']),
            style=CSSStyle.from_json(json['style']),
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']) if 'styleSheetId' in json else None,
        )


@dataclass
class StyleDeclarationEdit:
    '''
    A descriptor of operation to mutate style declaration text.
    '''
    #: The css style sheet identifier.
    style_sheet_id: StyleSheetId

    #: The range of the style text in the enclosing stylesheet.
    range_: SourceRange

    #: New style text.
    text: str

    def to_json(self):
        json = dict()
        json['styleSheetId'] = self.style_sheet_id.to_json()
        json['range'] = self.range_.to_json()
        json['text'] = self.text
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId']),
            range_=SourceRange.from_json(json['range']),
            text=str(json['text']),
        )


def add_rule(
        style_sheet_id: StyleSheetId,
        rule_text: str,
        location: SourceRange,
        node_for_property_syntax_validation: typing.Optional[dom.NodeId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,CSSRule]:
    '''
    Inserts a new rule with the given ``ruleText`` in a stylesheet with given ``styleSheetId``, at the
    position specified by ``location``.

    :param style_sheet_id: The css style sheet identifier where a new rule should be inserted.
    :param rule_text: The text of a new rule.
    :param location: Text position of a new rule in the target style sheet.
    :param node_for_property_syntax_validation: **(EXPERIMENTAL)** *(Optional)* NodeId for the DOM node in whose context custom property declarations for registered properties should be validated. If omitted, declarations in the new rule text can only be validated statically, which may produce incorrect results if the declaration contains a var() for example.
    :returns: The newly created rule.
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    params['ruleText'] = rule_text
    params['location'] = location.to_json()
    if node_for_property_syntax_validation is not None:
        params['nodeForPropertySyntaxValidation'] = node_for_property_syntax_validation.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.addRule',
        'params': params,
    }
    json = yield cmd_dict
    return CSSRule.from_json(json['rule'])


def collect_class_names(
        style_sheet_id: StyleSheetId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Returns all class names from specified stylesheet.

    :param style_sheet_id:
    :returns: Class name list.
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.collectClassNames',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['classNames']]


def create_style_sheet(
        frame_id: page.FrameId,
        force: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,StyleSheetId]:
    '''
    Creates a new special "via-inspector" stylesheet in the frame with given ``frameId``.

    :param frame_id: Identifier of the frame where "via-inspector" stylesheet should be created.
    :param force: *(Optional)* If true, creates a new stylesheet for every call. If false, returns a stylesheet previously created by a call with force=false for the frame's document if it exists or creates a new stylesheet (default: false).
    :returns: Identifier of the created "via-inspector" stylesheet.
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    if force is not None:
        params['force'] = force
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.createStyleSheet',
        'params': params,
    }
    json = yield cmd_dict
    return StyleSheetId.from_json(json['styleSheetId'])


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables the CSS agent for the given page.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables the CSS agent for the given page. Clients should not assume that the CSS agent has been
    enabled until the result of this command is received.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.enable',
    }
    json = yield cmd_dict


def force_pseudo_state(
        node_id: dom.NodeId,
        forced_pseudo_classes: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Ensures that the given node will have specified pseudo-classes whenever its style is computed by
    the browser.

    :param node_id: The element id for which to force the pseudo state.
    :param forced_pseudo_classes: Element pseudo classes to force when computing the element's style.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['forcedPseudoClasses'] = [i for i in forced_pseudo_classes]
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.forcePseudoState',
        'params': params,
    }
    json = yield cmd_dict


def force_starting_style(
        node_id: dom.NodeId,
        forced: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Ensures that the given node is in its starting-style state.

    :param node_id: The element id for which to force the starting-style state.
    :param forced: Boolean indicating if this is on or off.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['forced'] = forced
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.forceStartingStyle',
        'params': params,
    }
    json = yield cmd_dict


def get_background_colors(
        node_id: dom.NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[typing.List[str]], typing.Optional[str], typing.Optional[str]]]:
    '''
    :param node_id: Id of the node to get background colors for.
    :returns: A tuple with the following items:

        0. **backgroundColors** - *(Optional)* The range of background colors behind this element, if it contains any visible text. If no visible text is present, this will be undefined. In the case of a flat background color, this will consist of simply that color. In the case of a gradient, this will consist of each of the color stops. For anything more complicated, this will be an empty array. Images will be ignored (as if the image had failed to load).
        1. **computedFontSize** - *(Optional)* The computed font size for this node, as a CSS computed value string (e.g. '12px').
        2. **computedFontWeight** - *(Optional)* The computed font weight for this node, as a CSS computed value string (e.g. 'normal' or '100').
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.getBackgroundColors',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [str(i) for i in json['backgroundColors']] if 'backgroundColors' in json else None,
        str(json['computedFontSize']) if 'computedFontSize' in json else None,
        str(json['computedFontWeight']) if 'computedFontWeight' in json else None
    )


def get_computed_style_for_node(
        node_id: dom.NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[CSSComputedStyleProperty]]:
    '''
    Returns the computed style for a DOM node identified by ``nodeId``.

    :param node_id:
    :returns: Computed style for the specified DOM node.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.getComputedStyleForNode',
        'params': params,
    }
    json = yield cmd_dict
    return [CSSComputedStyleProperty.from_json(i) for i in json['computedStyle']]


def resolve_values(
        values: typing.List[str],
        node_id: dom.NodeId,
        property_name: typing.Optional[str] = None,
        pseudo_type: typing.Optional[dom.PseudoType] = None,
        pseudo_identifier: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Resolve the specified values in the context of the provided element.
    For example, a value of '1em' is evaluated according to the computed
    'font-size' of the element and a value 'calc(1px + 2px)' will be
    resolved to '3px'.
    If the ``propertyName`` was specified the ``values`` are resolved as if
    they were property's declaration. If a value cannot be parsed according
    to the provided property syntax, the value is parsed using combined
    syntax as if null ``propertyName`` was provided. If the value cannot be
    resolved even then, return the provided value without any changes.

    **EXPERIMENTAL**

    :param values: Substitution functions (var()/env()/attr()) and cascade-dependent keywords (revert/revert-layer) do not work.
    :param node_id: Id of the node in whose context the expression is evaluated
    :param property_name: *(Optional)* Only longhands and custom property names are accepted.
    :param pseudo_type: *(Optional)* Pseudo element type, only works for pseudo elements that generate elements in the tree, such as ::before and ::after.
    :param pseudo_identifier: *(Optional)* Pseudo element custom ident.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['values'] = [i for i in values]
    params['nodeId'] = node_id.to_json()
    if property_name is not None:
        params['propertyName'] = property_name
    if pseudo_type is not None:
        params['pseudoType'] = pseudo_type.to_json()
    if pseudo_identifier is not None:
        params['pseudoIdentifier'] = pseudo_identifier
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.resolveValues',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['results']]


def get_longhand_properties(
        shorthand_name: str,
        value: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[CSSProperty]]:
    '''


    **EXPERIMENTAL**

    :param shorthand_name:
    :param value:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['shorthandName'] = shorthand_name
    params['value'] = value
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.getLonghandProperties',
        'params': params,
    }
    json = yield cmd_dict
    return [CSSProperty.from_json(i) for i in json['longhandProperties']]


def get_inline_styles_for_node(
        node_id: dom.NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[CSSStyle], typing.Optional[CSSStyle]]]:
    '''
    Returns the styles defined inline (explicitly in the "style" attribute and implicitly, using DOM
    attributes) for a DOM node identified by ``nodeId``.

    :param node_id:
    :returns: A tuple with the following items:

        0. **inlineStyle** - *(Optional)* Inline style for the specified DOM node.
        1. **attributesStyle** - *(Optional)* Attribute-defined element style (e.g. resulting from "width=20 height=100%").
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.getInlineStylesForNode',
        'params': params,
    }
    json = yield cmd_dict
    return (
        CSSStyle.from_json(json['inlineStyle']) if 'inlineStyle' in json else None,
        CSSStyle.from_json(json['attributesStyle']) if 'attributesStyle' in json else None
    )


def get_animated_styles_for_node(
        node_id: dom.NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[typing.List[CSSAnimationStyle]], typing.Optional[CSSStyle], typing.Optional[typing.List[InheritedAnimatedStyleEntry]]]]:
    '''
    Returns the styles coming from animations & transitions
    including the animation & transition styles coming from inheritance chain.

    **EXPERIMENTAL**

    :param node_id:
    :returns: A tuple with the following items:

        0. **animationStyles** - *(Optional)* Styles coming from animations.
        1. **transitionsStyle** - *(Optional)* Style coming from transitions.
        2. **inherited** - *(Optional)* Inherited style entries for animationsStyle and transitionsStyle from the inheritance chain of the element.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.getAnimatedStylesForNode',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [CSSAnimationStyle.from_json(i) for i in json['animationStyles']] if 'animationStyles' in json else None,
        CSSStyle.from_json(json['transitionsStyle']) if 'transitionsStyle' in json else None,
        [InheritedAnimatedStyleEntry.from_json(i) for i in json['inherited']] if 'inherited' in json else None
    )


def get_matched_styles_for_node(
        node_id: dom.NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[CSSStyle], typing.Optional[CSSStyle], typing.Optional[typing.List[RuleMatch]], typing.Optional[typing.List[PseudoElementMatches]], typing.Optional[typing.List[InheritedStyleEntry]], typing.Optional[typing.List[InheritedPseudoElementMatches]], typing.Optional[typing.List[CSSKeyframesRule]], typing.Optional[typing.List[CSSPositionTryRule]], typing.Optional[int], typing.Optional[typing.List[CSSPropertyRule]], typing.Optional[typing.List[CSSPropertyRegistration]], typing.Optional[CSSFontPaletteValuesRule], typing.Optional[dom.NodeId], typing.Optional[typing.List[CSSFunctionRule]]]]:
    '''
    Returns requested styles for a DOM node identified by ``nodeId``.

    :param node_id:
    :returns: A tuple with the following items:

        0. **inlineStyle** - *(Optional)* Inline style for the specified DOM node.
        1. **attributesStyle** - *(Optional)* Attribute-defined element style (e.g. resulting from "width=20 height=100%").
        2. **matchedCSSRules** - *(Optional)* CSS rules matching this node, from all applicable stylesheets.
        3. **pseudoElements** - *(Optional)* Pseudo style matches for this node.
        4. **inherited** - *(Optional)* A chain of inherited styles (from the immediate node parent up to the DOM tree root).
        5. **inheritedPseudoElements** - *(Optional)* A chain of inherited pseudo element styles (from the immediate node parent up to the DOM tree root).
        6. **cssKeyframesRules** - *(Optional)* A list of CSS keyframed animations matching this node.
        7. **cssPositionTryRules** - *(Optional)* A list of CSS @position-try rules matching this node, based on the position-try-fallbacks property.
        8. **activePositionFallbackIndex** - *(Optional)* Index of the active fallback in the applied position-try-fallback property, will not be set if there is no active position-try fallback.
        9. **cssPropertyRules** - *(Optional)* A list of CSS at-property rules matching this node.
        10. **cssPropertyRegistrations** - *(Optional)* A list of CSS property registrations matching this node.
        11. **cssFontPaletteValuesRule** - *(Optional)* A font-palette-values rule matching this node.
        12. **parentLayoutNodeId** - *(Optional)* Id of the first parent element that does not have display: contents.
        13. **cssFunctionRules** - *(Optional)* A list of CSS at-function rules referenced by styles of this node.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.getMatchedStylesForNode',
        'params': params,
    }
    json = yield cmd_dict
    return (
        CSSStyle.from_json(json['inlineStyle']) if 'inlineStyle' in json else None,
        CSSStyle.from_json(json['attributesStyle']) if 'attributesStyle' in json else None,
        [RuleMatch.from_json(i) for i in json['matchedCSSRules']] if 'matchedCSSRules' in json else None,
        [PseudoElementMatches.from_json(i) for i in json['pseudoElements']] if 'pseudoElements' in json else None,
        [InheritedStyleEntry.from_json(i) for i in json['inherited']] if 'inherited' in json else None,
        [InheritedPseudoElementMatches.from_json(i) for i in json['inheritedPseudoElements']] if 'inheritedPseudoElements' in json else None,
        [CSSKeyframesRule.from_json(i) for i in json['cssKeyframesRules']] if 'cssKeyframesRules' in json else None,
        [CSSPositionTryRule.from_json(i) for i in json['cssPositionTryRules']] if 'cssPositionTryRules' in json else None,
        int(json['activePositionFallbackIndex']) if 'activePositionFallbackIndex' in json else None,
        [CSSPropertyRule.from_json(i) for i in json['cssPropertyRules']] if 'cssPropertyRules' in json else None,
        [CSSPropertyRegistration.from_json(i) for i in json['cssPropertyRegistrations']] if 'cssPropertyRegistrations' in json else None,
        CSSFontPaletteValuesRule.from_json(json['cssFontPaletteValuesRule']) if 'cssFontPaletteValuesRule' in json else None,
        dom.NodeId.from_json(json['parentLayoutNodeId']) if 'parentLayoutNodeId' in json else None,
        [CSSFunctionRule.from_json(i) for i in json['cssFunctionRules']] if 'cssFunctionRules' in json else None
    )


def get_media_queries() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[CSSMedia]]:
    '''
    Returns all media queries parsed by the rendering engine.

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.getMediaQueries',
    }
    json = yield cmd_dict
    return [CSSMedia.from_json(i) for i in json['medias']]


def get_platform_fonts_for_node(
        node_id: dom.NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[PlatformFontUsage]]:
    '''
    Requests information about platform fonts which we used to render child TextNodes in the given
    node.

    :param node_id:
    :returns: Usage statistics for every employed platform font.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.getPlatformFontsForNode',
        'params': params,
    }
    json = yield cmd_dict
    return [PlatformFontUsage.from_json(i) for i in json['fonts']]


def get_style_sheet_text(
        style_sheet_id: StyleSheetId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Returns the current textual content for a stylesheet.

    :param style_sheet_id:
    :returns: The stylesheet text.
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.getStyleSheetText',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['text'])


def get_layers_for_node(
        node_id: dom.NodeId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,CSSLayerData]:
    '''
    Returns all layers parsed by the rendering engine for the tree scope of a node.
    Given a DOM element identified by nodeId, getLayersForNode returns the root
    layer for the nearest ancestor document or shadow root. The layer root contains
    the full layer tree for the tree scope and their ordering.

    **EXPERIMENTAL**

    :param node_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.getLayersForNode',
        'params': params,
    }
    json = yield cmd_dict
    return CSSLayerData.from_json(json['rootLayer'])


def get_location_for_selector(
        style_sheet_id: StyleSheetId,
        selector_text: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[SourceRange]]:
    '''
    Given a CSS selector text and a style sheet ID, getLocationForSelector
    returns an array of locations of the CSS selector in the style sheet.

    **EXPERIMENTAL**

    :param style_sheet_id:
    :param selector_text:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    params['selectorText'] = selector_text
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.getLocationForSelector',
        'params': params,
    }
    json = yield cmd_dict
    return [SourceRange.from_json(i) for i in json['ranges']]


def track_computed_style_updates_for_node(
        node_id: typing.Optional[dom.NodeId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Starts tracking the given node for the computed style updates
    and whenever the computed style is updated for node, it queues
    a ``computedStyleUpdated`` event with throttling.
    There can only be 1 node tracked for computed style updates
    so passing a new node id removes tracking from the previous node.
    Pass ``undefined`` to disable tracking.

    **EXPERIMENTAL**

    :param node_id: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    if node_id is not None:
        params['nodeId'] = node_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.trackComputedStyleUpdatesForNode',
        'params': params,
    }
    json = yield cmd_dict


def track_computed_style_updates(
        properties_to_track: typing.List[CSSComputedStyleProperty]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Starts tracking the given computed styles for updates. The specified array of properties
    replaces the one previously specified. Pass empty array to disable tracking.
    Use takeComputedStyleUpdates to retrieve the list of nodes that had properties modified.
    The changes to computed style properties are only tracked for nodes pushed to the front-end
    by the DOM agent. If no changes to the tracked properties occur after the node has been pushed
    to the front-end, no updates will be issued for the node.

    **EXPERIMENTAL**

    :param properties_to_track:
    '''
    params: T_JSON_DICT = dict()
    params['propertiesToTrack'] = [i.to_json() for i in properties_to_track]
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.trackComputedStyleUpdates',
        'params': params,
    }
    json = yield cmd_dict


def take_computed_style_updates() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[dom.NodeId]]:
    '''
    Polls the next batch of computed style updates.

    **EXPERIMENTAL**

    :returns: The list of node Ids that have their tracked computed styles updated.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.takeComputedStyleUpdates',
    }
    json = yield cmd_dict
    return [dom.NodeId.from_json(i) for i in json['nodeIds']]


def set_effective_property_value_for_node(
        node_id: dom.NodeId,
        property_name: str,
        value: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Find a rule with the given active property for the given node and set the new value for this
    property

    :param node_id: The element id for which to set property.
    :param property_name:
    :param value:
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['propertyName'] = property_name
    params['value'] = value
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.setEffectivePropertyValueForNode',
        'params': params,
    }
    json = yield cmd_dict


def set_property_rule_property_name(
        style_sheet_id: StyleSheetId,
        range_: SourceRange,
        property_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,Value]:
    '''
    Modifies the property rule property name.

    :param style_sheet_id:
    :param range_:
    :param property_name:
    :returns: The resulting key text after modification.
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    params['range'] = range_.to_json()
    params['propertyName'] = property_name
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.setPropertyRulePropertyName',
        'params': params,
    }
    json = yield cmd_dict
    return Value.from_json(json['propertyName'])


def set_keyframe_key(
        style_sheet_id: StyleSheetId,
        range_: SourceRange,
        key_text: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,Value]:
    '''
    Modifies the keyframe rule key text.

    :param style_sheet_id:
    :param range_:
    :param key_text:
    :returns: The resulting key text after modification.
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    params['range'] = range_.to_json()
    params['keyText'] = key_text
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.setKeyframeKey',
        'params': params,
    }
    json = yield cmd_dict
    return Value.from_json(json['keyText'])


def set_media_text(
        style_sheet_id: StyleSheetId,
        range_: SourceRange,
        text: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,CSSMedia]:
    '''
    Modifies the rule selector.

    :param style_sheet_id:
    :param range_:
    :param text:
    :returns: The resulting CSS media rule after modification.
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    params['range'] = range_.to_json()
    params['text'] = text
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.setMediaText',
        'params': params,
    }
    json = yield cmd_dict
    return CSSMedia.from_json(json['media'])


def set_container_query_text(
        style_sheet_id: StyleSheetId,
        range_: SourceRange,
        text: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,CSSContainerQuery]:
    '''
    Modifies the expression of a container query.

    **EXPERIMENTAL**

    :param style_sheet_id:
    :param range_:
    :param text:
    :returns: The resulting CSS container query rule after modification.
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    params['range'] = range_.to_json()
    params['text'] = text
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.setContainerQueryText',
        'params': params,
    }
    json = yield cmd_dict
    return CSSContainerQuery.from_json(json['containerQuery'])


def set_supports_text(
        style_sheet_id: StyleSheetId,
        range_: SourceRange,
        text: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,CSSSupports]:
    '''
    Modifies the expression of a supports at-rule.

    **EXPERIMENTAL**

    :param style_sheet_id:
    :param range_:
    :param text:
    :returns: The resulting CSS Supports rule after modification.
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    params['range'] = range_.to_json()
    params['text'] = text
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.setSupportsText',
        'params': params,
    }
    json = yield cmd_dict
    return CSSSupports.from_json(json['supports'])


def set_scope_text(
        style_sheet_id: StyleSheetId,
        range_: SourceRange,
        text: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,CSSScope]:
    '''
    Modifies the expression of a scope at-rule.

    **EXPERIMENTAL**

    :param style_sheet_id:
    :param range_:
    :param text:
    :returns: The resulting CSS Scope rule after modification.
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    params['range'] = range_.to_json()
    params['text'] = text
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.setScopeText',
        'params': params,
    }
    json = yield cmd_dict
    return CSSScope.from_json(json['scope'])


def set_rule_selector(
        style_sheet_id: StyleSheetId,
        range_: SourceRange,
        selector: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SelectorList]:
    '''
    Modifies the rule selector.

    :param style_sheet_id:
    :param range_:
    :param selector:
    :returns: The resulting selector list after modification.
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    params['range'] = range_.to_json()
    params['selector'] = selector
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.setRuleSelector',
        'params': params,
    }
    json = yield cmd_dict
    return SelectorList.from_json(json['selectorList'])


def set_style_sheet_text(
        style_sheet_id: StyleSheetId,
        text: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Optional[str]]:
    '''
    Sets the new stylesheet text.

    :param style_sheet_id:
    :param text:
    :returns: *(Optional)* URL of source map associated with script (if any).
    '''
    params: T_JSON_DICT = dict()
    params['styleSheetId'] = style_sheet_id.to_json()
    params['text'] = text
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.setStyleSheetText',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['sourceMapURL']) if 'sourceMapURL' in json else None


def set_style_texts(
        edits: typing.List[StyleDeclarationEdit],
        node_for_property_syntax_validation: typing.Optional[dom.NodeId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[CSSStyle]]:
    '''
    Applies specified style edits one after another in the given order.

    :param edits:
    :param node_for_property_syntax_validation: **(EXPERIMENTAL)** *(Optional)* NodeId for the DOM node in whose context custom property declarations for registered properties should be validated. If omitted, declarations in the new rule text can only be validated statically, which may produce incorrect results if the declaration contains a var() for example.
    :returns: The resulting styles after modification.
    '''
    params: T_JSON_DICT = dict()
    params['edits'] = [i.to_json() for i in edits]
    if node_for_property_syntax_validation is not None:
        params['nodeForPropertySyntaxValidation'] = node_for_property_syntax_validation.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.setStyleTexts',
        'params': params,
    }
    json = yield cmd_dict
    return [CSSStyle.from_json(i) for i in json['styles']]


def start_rule_usage_tracking() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables the selector recording.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.startRuleUsageTracking',
    }
    json = yield cmd_dict


def stop_rule_usage_tracking() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[RuleUsage]]:
    '''
    Stop tracking rule usage and return the list of rules that were used since last call to
    ``takeCoverageDelta`` (or since start of coverage instrumentation).

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.stopRuleUsageTracking',
    }
    json = yield cmd_dict
    return [RuleUsage.from_json(i) for i in json['ruleUsage']]


def take_coverage_delta() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[RuleUsage], float]]:
    '''
    Obtain list of rules that became used since last call to this method (or since start of coverage
    instrumentation).

    :returns: A tuple with the following items:

        0. **coverage** - 
        1. **timestamp** - Monotonically increasing time, in seconds.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.takeCoverageDelta',
    }
    json = yield cmd_dict
    return (
        [RuleUsage.from_json(i) for i in json['coverage']],
        float(json['timestamp'])
    )


def set_local_fonts_enabled(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/disables rendering of local CSS fonts (enabled by default).

    **EXPERIMENTAL**

    :param enabled: Whether rendering of local fonts is enabled.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'CSS.setLocalFontsEnabled',
        'params': params,
    }
    json = yield cmd_dict


@event_class('CSS.fontsUpdated')
@dataclass
class FontsUpdated:
    '''
    Fires whenever a web font is updated.  A non-empty font parameter indicates a successfully loaded
    web font.
    '''
    #: The web font that has loaded.
    font: typing.Optional[FontFace]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FontsUpdated:
        return cls(
            font=FontFace.from_json(json['font']) if 'font' in json else None
        )


@event_class('CSS.mediaQueryResultChanged')
@dataclass
class MediaQueryResultChanged:
    '''
    Fires whenever a MediaQuery result changes (for example, after a browser window has been
    resized.) The current implementation considers only viewport-dependent media features.
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> MediaQueryResultChanged:
        return cls(

        )


@event_class('CSS.styleSheetAdded')
@dataclass
class StyleSheetAdded:
    '''
    Fired whenever an active document stylesheet is added.
    '''
    #: Added stylesheet metainfo.
    header: CSSStyleSheetHeader

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> StyleSheetAdded:
        return cls(
            header=CSSStyleSheetHeader.from_json(json['header'])
        )


@event_class('CSS.styleSheetChanged')
@dataclass
class StyleSheetChanged:
    '''
    Fired whenever a stylesheet is changed as a result of the client operation.
    '''
    style_sheet_id: StyleSheetId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> StyleSheetChanged:
        return cls(
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId'])
        )


@event_class('CSS.styleSheetRemoved')
@dataclass
class StyleSheetRemoved:
    '''
    Fired whenever an active document stylesheet is removed.
    '''
    #: Identifier of the removed stylesheet.
    style_sheet_id: StyleSheetId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> StyleSheetRemoved:
        return cls(
            style_sheet_id=StyleSheetId.from_json(json['styleSheetId'])
        )


@event_class('CSS.computedStyleUpdated')
@dataclass
class ComputedStyleUpdated:
    '''
    **EXPERIMENTAL**


    '''
    #: The node id that has updated computed styles.
    node_id: dom.NodeId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ComputedStyleUpdated:
        return cls(
            node_id=dom.NodeId.from_json(json['nodeId'])
        )