
# === NexusCore/openenv\Lib\site-packages\nltk\featstruct.py ===
# Natural Language Toolkit: Feature Structures
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>,
#         Rob Speer,
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

"""
Basic data classes for representing feature structures, and for
performing basic operations on those feature structures.  A feature
structure is a mapping from feature identifiers to feature values,
where each feature value is either a basic value (such as a string or
an integer), or a nested feature structure.  There are two types of
feature structure, implemented by two subclasses of ``FeatStruct``:

    - feature dictionaries, implemented by ``FeatDict``, act like
      Python dictionaries.  Feature identifiers may be strings or
      instances of the ``Feature`` class.
    - feature lists, implemented by ``FeatList``, act like Python
      lists.  Feature identifiers are integers.

Feature structures are typically used to represent partial information
about objects.  A feature identifier that is not mapped to a value
stands for a feature whose value is unknown (*not* a feature without
a value).  Two feature structures that represent (potentially
overlapping) information about the same object can be combined by
unification.  When two inconsistent feature structures are unified,
the unification fails and returns None.

Features can be specified using "feature paths", or tuples of feature
identifiers that specify path through the nested feature structures to
a value.  Feature structures may contain reentrant feature values.  A
"reentrant feature value" is a single feature value that can be
accessed via multiple feature paths.  Unification preserves the
reentrance relations imposed by both of the unified feature
structures.  In the feature structure resulting from unification, any
modifications to a reentrant feature value will be visible using any
of its feature paths.

Feature structure variables are encoded using the ``nltk.sem.Variable``
class.  The variables' values are tracked using a bindings
dictionary, which maps variables to their values.  When two feature
structures are unified, a fresh bindings dictionary is created to
track their values; and before unification completes, all bound
variables are replaced by their values.  Thus, the bindings
dictionaries are usually strictly internal to the unification process.
However, it is possible to track the bindings of variables if you
choose to, by supplying your own initial bindings dictionary to the
``unify()`` function.

When unbound variables are unified with one another, they become
aliased.  This is encoded by binding one variable to the other.

Lightweight Feature Structures
==============================
Many of the functions defined by ``nltk.featstruct`` can be applied
directly to simple Python dictionaries and lists, rather than to
full-fledged ``FeatDict`` and ``FeatList`` objects.  In other words,
Python ``dicts`` and ``lists`` can be used as "light-weight" feature
structures.

    >>> from nltk.featstruct import unify
    >>> unify(dict(x=1, y=dict()), dict(a='a', y=dict(b='b')))  # doctest: +SKIP
    {'y': {'b': 'b'}, 'x': 1, 'a': 'a'}

However, you should keep in mind the following caveats:

  - Python dictionaries & lists ignore reentrance when checking for
    equality between values.  But two FeatStructs with different
    reentrances are considered nonequal, even if all their base
    values are equal.

  - FeatStructs can be easily frozen, allowing them to be used as
    keys in hash tables.  Python dictionaries and lists can not.

  - FeatStructs display reentrance in their string representations;
    Python dictionaries and lists do not.

  - FeatStructs may *not* be mixed with Python dictionaries and lists
    (e.g., when performing unification).

  - FeatStructs provide a number of useful methods, such as ``walk()``
    and ``cyclic()``, which are not available for Python dicts and lists.

In general, if your feature structures will contain any reentrances,
or if you plan to use them as dictionary keys, it is strongly
recommended that you use full-fledged ``FeatStruct`` objects.
"""

import copy
import re
from functools import total_ordering

from nltk.internals import raise_unorderable_types, read_str
from nltk.sem.logic import (
    Expression,
    LogicalExpressionException,
    LogicParser,
    SubstituteBindingsI,
    Variable,
)

######################################################################
# Feature Structure
######################################################################


@total_ordering
class FeatStruct(SubstituteBindingsI):
    """
    A mapping from feature identifiers to feature values, where each
    feature value is either a basic value (such as a string or an
    integer), or a nested feature structure.  There are two types of
    feature structure:

      - feature dictionaries, implemented by ``FeatDict``, act like
        Python dictionaries.  Feature identifiers may be strings or
        instances of the ``Feature`` class.
      - feature lists, implemented by ``FeatList``, act like Python
        lists.  Feature identifiers are integers.

    Feature structures may be indexed using either simple feature
    identifiers or 'feature paths.'  A feature path is a sequence
    of feature identifiers that stand for a corresponding sequence of
    indexing operations.  In particular, ``fstruct[(f1,f2,...,fn)]`` is
    equivalent to ``fstruct[f1][f2]...[fn]``.

    Feature structures may contain reentrant feature structures.  A
    "reentrant feature structure" is a single feature structure
    object that can be accessed via multiple feature paths.  Feature
    structures may also be cyclic.  A feature structure is "cyclic"
    if there is any feature path from the feature structure to itself.

    Two feature structures are considered equal if they assign the
    same values to all features, and have the same reentrancies.

    By default, feature structures are mutable.  They may be made
    immutable with the ``freeze()`` method.  Once they have been
    frozen, they may be hashed, and thus used as dictionary keys.
    """

    _frozen = False
    """:ivar: A flag indicating whether this feature structure is
       frozen or not.  Once this flag is set, it should never be
       un-set; and no further modification should be made to this
       feature structure."""

    ##////////////////////////////////////////////////////////////
    # { Constructor
    ##////////////////////////////////////////////////////////////

    def __new__(cls, features=None, **morefeatures):
        """
        Construct and return a new feature structure.  If this
        constructor is called directly, then the returned feature
        structure will be an instance of either the ``FeatDict`` class
        or the ``FeatList`` class.

        :param features: The initial feature values for this feature
            structure:

            - FeatStruct(string) -> FeatStructReader().read(string)
            - FeatStruct(mapping) -> FeatDict(mapping)
            - FeatStruct(sequence) -> FeatList(sequence)
            - FeatStruct() -> FeatDict()
        :param morefeatures: If ``features`` is a mapping or None,
            then ``morefeatures`` provides additional features for the
            ``FeatDict`` constructor.
        """
        # If the FeatStruct constructor is called directly, then decide
        # whether to create a FeatDict or a FeatList, based on the
        # contents of the `features` argument.
        if cls is FeatStruct:
            if features is None:
                return FeatDict.__new__(FeatDict, **morefeatures)
            elif _is_mapping(features):
                return FeatDict.__new__(FeatDict, features, **morefeatures)
            elif morefeatures:
                raise TypeError(
                    "Keyword arguments may only be specified "
                    "if features is None or is a mapping."
                )
            if isinstance(features, str):
                if FeatStructReader._START_FDICT_RE.match(features):
                    return FeatDict.__new__(FeatDict, features, **morefeatures)
                else:
                    return FeatList.__new__(FeatList, features, **morefeatures)
            elif _is_sequence(features):
                return FeatList.__new__(FeatList, features)
            else:
                raise TypeError("Expected string or mapping or sequence")

        # Otherwise, construct the object as normal.
        else:
            return super().__new__(cls, features, **morefeatures)

    ##////////////////////////////////////////////////////////////
    # { Uniform Accessor Methods
    ##////////////////////////////////////////////////////////////
    # These helper functions allow the methods defined by FeatStruct
    # to treat all feature structures as mappings, even if they're
    # really lists.  (Lists are treated as mappings from ints to vals)

    def _keys(self):
        """Return an iterable of the feature identifiers used by this
        FeatStruct."""
        raise NotImplementedError()  # Implemented by subclasses.

    def _values(self):
        """Return an iterable of the feature values directly defined
        by this FeatStruct."""
        raise NotImplementedError()  # Implemented by subclasses.

    def _items(self):
        """Return an iterable of (fid,fval) pairs, where fid is a
        feature identifier and fval is the corresponding feature
        value, for all features defined by this FeatStruct."""
        raise NotImplementedError()  # Implemented by subclasses.

    ##////////////////////////////////////////////////////////////
    # { Equality & Hashing
    ##////////////////////////////////////////////////////////////

    def equal_values(self, other, check_reentrance=False):
        """
        Return True if ``self`` and ``other`` assign the same value to
        to every feature.  In particular, return true if
        ``self[p]==other[p]`` for every feature path *p* such
        that ``self[p]`` or ``other[p]`` is a base value (i.e.,
        not a nested feature structure).

        :param check_reentrance: If True, then also return False if
            there is any difference between the reentrances of ``self``
            and ``other``.
        :note: the ``==`` is equivalent to ``equal_values()`` with
            ``check_reentrance=True``.
        """
        return self._equal(other, check_reentrance, set(), set(), set())

    def __eq__(self, other):
        """
        Return true if ``self`` and ``other`` are both feature structures,
        assign the same values to all features, and contain the same
        reentrances.  I.e., return
        ``self.equal_values(other, check_reentrance=True)``.

        :see: ``equal_values()``
        """
        return self._equal(other, True, set(), set(), set())

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, FeatStruct):
            # raise_unorderable_types("<", self, other)
            # Sometimes feature values can be pure strings,
            # so we need to be able to compare with non-featstructs:
            return self.__class__.__name__ < other.__class__.__name__
        else:
            return len(self) < len(other)

    def __hash__(self):
        """
        If this feature structure is frozen, return its hash value;
        otherwise, raise ``TypeError``.
        """
        if not self._frozen:
            raise TypeError("FeatStructs must be frozen before they " "can be hashed.")
        try:
            return self._hash
        except AttributeError:
            self._hash = self._calculate_hashvalue(set())
            return self._hash

    def _equal(
        self, other, check_reentrance, visited_self, visited_other, visited_pairs
    ):
        """
        Return True iff self and other have equal values.

        :param visited_self: A set containing the ids of all ``self``
            feature structures we've already visited.
        :param visited_other: A set containing the ids of all ``other``
            feature structures we've already visited.
        :param visited_pairs: A set containing ``(selfid, otherid)`` pairs
            for all pairs of feature structures we've already visited.
        """
        # If we're the same object, then we're equal.
        if self is other:
            return True

        # If we have different classes, we're definitely not equal.
        if self.__class__ != other.__class__:
            return False

        # If we define different features, we're definitely not equal.
        # (Perform len test first because it's faster -- we should
        # do profiling to see if this actually helps)
        if len(self) != len(other):
            return False
        if set(self._keys()) != set(other._keys()):
            return False

        # If we're checking reentrance, then any time we revisit a
        # structure, make sure that it was paired with the same
        # feature structure that it is now.  Note: if check_reentrance,
        # then visited_pairs will never contain two pairs whose first
        # values are equal, or two pairs whose second values are equal.
        if check_reentrance:
            if id(self) in visited_self or id(other) in visited_other:
                return (id(self), id(other)) in visited_pairs

        # If we're not checking reentrance, then we still need to deal
        # with cycles.  If we encounter the same (self, other) pair a
        # second time, then we won't learn anything more by examining
        # their children a second time, so just return true.
        else:
            if (id(self), id(other)) in visited_pairs:
                return True

        # Keep track of which nodes we've visited.
        visited_self.add(id(self))
        visited_other.add(id(other))
        visited_pairs.add((id(self), id(other)))

        # Now we have to check all values.  If any of them don't match,
        # then return false.
        for fname, self_fval in self._items():
            other_fval = other[fname]
            if isinstance(self_fval, FeatStruct):
                if not self_fval._equal(
                    other_fval,
                    check_reentrance,
                    visited_self,
                    visited_other,
                    visited_pairs,
                ):
                    return False
            else:
                if self_fval != other_fval:
                    return False

        # Everything matched up; return true.
        return True

    def _calculate_hashvalue(self, visited):
        """
        Return a hash value for this feature structure.

        :require: ``self`` must be frozen.
        :param visited: A set containing the ids of all feature
            structures we've already visited while hashing.
        """
        if id(self) in visited:
            return 1
        visited.add(id(self))

        hashval = 5831
        for fname, fval in sorted(self._items()):
            hashval *= 37
            hashval += hash(fname)
            hashval *= 37
            if isinstance(fval, FeatStruct):
                hashval += fval._calculate_hashvalue(visited)
            else:
                hashval += hash(fval)
            # Convert to a 32 bit int.
            hashval = int(hashval & 0x7FFFFFFF)
        return hashval

    ##////////////////////////////////////////////////////////////
    # { Freezing
    ##////////////////////////////////////////////////////////////

    #: Error message used by mutating methods when called on a frozen
    #: feature structure.
    _FROZEN_ERROR = "Frozen FeatStructs may not be modified."

    def freeze(self):
        """
        Make this feature structure, and any feature structures it
        contains, immutable.  Note: this method does not attempt to
        'freeze' any feature value that is not a ``FeatStruct``; it
        is recommended that you use only immutable feature values.
        """
        if self._frozen:
            return
        self._freeze(set())

    def frozen(self):
        """
        Return True if this feature structure is immutable.  Feature
        structures can be made immutable with the ``freeze()`` method.
        Immutable feature structures may not be made mutable again,
        but new mutable copies can be produced with the ``copy()`` method.
        """
        return self._frozen

    def _freeze(self, visited):
        """
        Make this feature structure, and any feature structure it
        contains, immutable.

        :param visited: A set containing the ids of all feature
            structures we've already visited while freezing.
        """
        if id(self) in visited:
            return
        visited.add(id(self))
        self._frozen = True
        for fname, fval in sorted(self._items()):
            if isinstance(fval, FeatStruct):
                fval._freeze(visited)

    ##////////////////////////////////////////////////////////////
    # { Copying
    ##////////////////////////////////////////////////////////////

    def copy(self, deep=True):
        """
        Return a new copy of ``self``.  The new copy will not be frozen.

        :param deep: If true, create a deep copy; if false, create
            a shallow copy.
        """
        if deep:
            return copy.deepcopy(self)
        else:
            return self.__class__(self)

    # Subclasses should define __deepcopy__ to ensure that the new
    # copy will not be frozen.
    def __deepcopy__(self, memo):
        raise NotImplementedError()  # Implemented by subclasses.

    ##////////////////////////////////////////////////////////////
    # { Structural Information
    ##////////////////////////////////////////////////////////////

    def cyclic(self):
        """
        Return True if this feature structure contains itself.
        """
        return self._find_reentrances({})[id(self)]

    def walk(self):
        """
        Return an iterator that generates this feature structure, and
        each feature structure it contains.  Each feature structure will
        be generated exactly once.
        """
        return self._walk(set())

    def _walk(self, visited):
        """
        Return an iterator that generates this feature structure, and
        each feature structure it contains.

        :param visited: A set containing the ids of all feature
            structures we've already visited while freezing.
        """
        raise NotImplementedError()  # Implemented by subclasses.

    def _walk(self, visited):
        if id(self) in visited:
            return
        visited.add(id(self))
        yield self
        for fval in self._values():
            if isinstance(fval, FeatStruct):
                yield from fval._walk(visited)

    # Walk through the feature tree.  The first time we see a feature
    # value, map it to False (not reentrant).  If we see a feature
    # value more than once, then map it to True (reentrant).
    def _find_reentrances(self, reentrances):
        """
        Return a dictionary that maps from the ``id`` of each feature
        structure contained in ``self`` (including ``self``) to a
        boolean value, indicating whether it is reentrant or not.
        """
        if id(self) in reentrances:
            # We've seen it more than once.
            reentrances[id(self)] = True
        else:
            # This is the first time we've seen it.
            reentrances[id(self)] = False

            # Recurse to contained feature structures.
            for fval in self._values():
                if isinstance(fval, FeatStruct):
                    fval._find_reentrances(reentrances)

        return reentrances

    ##////////////////////////////////////////////////////////////
    # { Variables & Bindings
    ##////////////////////////////////////////////////////////////

    def substitute_bindings(self, bindings):
        """:see: ``nltk.featstruct.substitute_bindings()``"""
        return substitute_bindings(self, bindings)

    def retract_bindings(self, bindings):
        """:see: ``nltk.featstruct.retract_bindings()``"""
        return retract_bindings(self, bindings)

    def variables(self):
        """:see: ``nltk.featstruct.find_variables()``"""
        return find_variables(self)

    def rename_variables(self, vars=None, used_vars=(), new_vars=None):
        """:see: ``nltk.featstruct.rename_variables()``"""
        return rename_variables(self, vars, used_vars, new_vars)

    def remove_variables(self):
        """
        Return the feature structure that is obtained by deleting
        any feature whose value is a ``Variable``.

        :rtype: FeatStruct
        """
        return remove_variables(self)

    ##////////////////////////////////////////////////////////////
    # { Unification
    ##////////////////////////////////////////////////////////////

    def unify(self, other, bindings=None, trace=False, fail=None, rename_vars=True):
        return unify(self, other, bindings, trace, fail, rename_vars)

    def subsumes(self, other):
        """
        Return True if ``self`` subsumes ``other``.  I.e., return true
        If unifying ``self`` with ``other`` would result in a feature
        structure equal to ``other``.
        """
        return subsumes(self, other)

    ##////////////////////////////////////////////////////////////
    # { String Representations
    ##////////////////////////////////////////////////////////////

    def __repr__(self):
        """
        Display a single-line representation of this feature structure,
        suitable for embedding in other representations.
        """
        return self._repr(self._find_reentrances({}), {})

    def _repr(self, reentrances, reentrance_ids):
        """
        Return a string representation of this feature structure.

        :param reentrances: A dictionary that maps from the ``id`` of
            each feature value in self, indicating whether that value
            is reentrant or not.
        :param reentrance_ids: A dictionary mapping from each ``id``
            of a feature value to a unique identifier.  This is modified
            by ``repr``: the first time a reentrant feature value is
            displayed, an identifier is added to ``reentrance_ids`` for it.
        """
        raise NotImplementedError()


# Mutation: disable if frozen.
_FROZEN_ERROR = "Frozen FeatStructs may not be modified."
_FROZEN_NOTICE = "\n%sIf self is frozen, raise ValueError."


def _check_frozen(method, indent=""):
    """
    Given a method function, return a new method function that first
    checks if ``self._frozen`` is true; and if so, raises ``ValueError``
    with an appropriate message.  Otherwise, call the method and return
    its result.
    """

    def wrapped(self, *args, **kwargs):
        if self._frozen:
            raise ValueError(_FROZEN_ERROR)
        else:
            return method(self, *args, **kwargs)

    wrapped.__name__ = method.__name__
    wrapped.__doc__ = (method.__doc__ or "") + (_FROZEN_NOTICE % indent)
    return wrapped


######################################################################
# Feature Dictionary
######################################################################


class FeatDict(FeatStruct, dict):
    """
    A feature structure that acts like a Python dictionary.  I.e., a
    mapping from feature identifiers to feature values, where a feature
    identifier can be a string or a ``Feature``; and where a feature value
    can be either a basic value (such as a string or an integer), or a nested
    feature structure.  A feature identifiers for a ``FeatDict`` is
    sometimes called a "feature name".

    Two feature dicts are considered equal if they assign the same
    values to all features, and have the same reentrances.

    :see: ``FeatStruct`` for information about feature paths, reentrance,
        cyclic feature structures, mutability, freezing, and hashing.
    """

    def __init__(self, features=None, **morefeatures):
        """
        Create a new feature dictionary, with the specified features.

        :param features: The initial value for this feature
            dictionary.  If ``features`` is a ``FeatStruct``, then its
            features are copied (shallow copy).  If ``features`` is a
            dict, then a feature is created for each item, mapping its
            key to its value.  If ``features`` is a string, then it is
            processed using ``FeatStructReader``.  If ``features`` is a list of
            tuples ``(name, val)``, then a feature is created for each tuple.
        :param morefeatures: Additional features for the new feature
            dictionary.  If a feature is listed under both ``features`` and
            ``morefeatures``, then the value from ``morefeatures`` will be
            used.
        """
        if isinstance(features, str):
            FeatStructReader().fromstring(features, self)
            self.update(**morefeatures)
        else:
            # update() checks the types of features.
            self.update(features, **morefeatures)

    # ////////////////////////////////////////////////////////////
    # { Dict methods
    # ////////////////////////////////////////////////////////////
    _INDEX_ERROR = "Expected feature name or path.  Got %r."

    def __getitem__(self, name_or_path):
        """If the feature with the given name or path exists, return
        its value; otherwise, raise ``KeyError``."""
        if isinstance(name_or_path, (str, Feature)):
            return dict.__getitem__(self, name_or_path)
        elif isinstance(name_or_path, tuple):
            try:
                val = self
                for fid in name_or_path:
                    if not isinstance(val, FeatStruct):
                        raise KeyError  # path contains base value
                    val = val[fid]
                return val
            except (KeyError, IndexError) as e:
                raise KeyError(name_or_path) from e
        else:
            raise TypeError(self._INDEX_ERROR % name_or_path)

    def get(self, name_or_path, default=None):
        """If the feature with the given name or path exists, return its
        value; otherwise, return ``default``."""
        try:
            return self[name_or_path]
        except KeyError:
            return default

    def __contains__(self, name_or_path):
        """Return true if a feature with the given name or path exists."""
        try:
            self[name_or_path]
            return True
        except KeyError:
            return False

    def has_key(self, name_or_path):
        """Return true if a feature with the given name or path exists."""
        return name_or_path in self

    def __delitem__(self, name_or_path):
        """If the feature with the given name or path exists, delete
        its value; otherwise, raise ``KeyError``."""
        if self._frozen:
            raise ValueError(_FROZEN_ERROR)
        if isinstance(name_or_path, (str, Feature)):
            return dict.__delitem__(self, name_or_path)
        elif isinstance(name_or_path, tuple):
            if len(name_or_path) == 0:
                raise ValueError("The path () can not be set")
            else:
                parent = self[name_or_path[:-1]]
                if not isinstance(parent, FeatStruct):
                    raise KeyError(name_or_path)  # path contains base value
                del parent[name_or_path[-1]]
        else:
            raise TypeError(self._INDEX_ERROR % name_or_path)

    def __setitem__(self, name_or_path, value):
        """Set the value for the feature with the given name or path
        to ``value``.  If ``name_or_path`` is an invalid path, raise
        ``KeyError``."""
        if self._frozen:
            raise ValueError(_FROZEN_ERROR)
        if isinstance(name_or_path, (str, Feature)):
            return dict.__setitem__(self, name_or_path, value)
        elif isinstance(name_or_path, tuple):
            if len(name_or_path) == 0:
                raise ValueError("The path () can not be set")
            else:
                parent = self[name_or_path[:-1]]
                if not isinstance(parent, FeatStruct):
                    raise KeyError(name_or_path)  # path contains base value
                parent[name_or_path[-1]] = value
        else:
            raise TypeError(self._INDEX_ERROR % name_or_path)

    clear = _check_frozen(dict.clear)
    pop = _check_frozen(dict.pop)
    popitem = _check_frozen(dict.popitem)
    setdefault = _check_frozen(dict.setdefault)

    def update(self, features=None, **morefeatures):
        if self._frozen:
            raise ValueError(_FROZEN_ERROR)
        if features is None:
            items = ()
        elif hasattr(features, "items") and callable(features.items):
            items = features.items()
        elif hasattr(features, "__iter__"):
            items = features
        else:
            raise ValueError("Expected mapping or list of tuples")

        for key, val in items:
            if not isinstance(key, (str, Feature)):
                raise TypeError("Feature names must be strings")
            self[key] = val
        for key, val in morefeatures.items():
            if not isinstance(key, (str, Feature)):
                raise TypeError("Feature names must be strings")
            self[key] = val

    ##////////////////////////////////////////////////////////////
    # { Copying
    ##////////////////////////////////////////////////////////////

    def __deepcopy__(self, memo):
        memo[id(self)] = selfcopy = self.__class__()
        for key, val in self._items():
            selfcopy[copy.deepcopy(key, memo)] = copy.deepcopy(val, memo)
        return selfcopy

    ##////////////////////////////////////////////////////////////
    # { Uniform Accessor Methods
    ##////////////////////////////////////////////////////////////

    def _keys(self):
        return self.keys()

    def _values(self):
        return self.values()

    def _items(self):
        return self.items()

    ##////////////////////////////////////////////////////////////
    # { String Representations
    ##////////////////////////////////////////////////////////////

    def __str__(self):
        """
        Display a multi-line representation of this feature dictionary
        as an FVM (feature value matrix).
        """
        return "\n".join(self._str(self._find_reentrances({}), {}))

    def _repr(self, reentrances, reentrance_ids):
        segments = []
        prefix = ""
        suffix = ""

        # If this is the first time we've seen a reentrant structure,
        # then assign it a unique identifier.
        if reentrances[id(self)]:
            assert id(self) not in reentrance_ids
            reentrance_ids[id(self)] = repr(len(reentrance_ids) + 1)

        # sorting note: keys are unique strings, so we'll never fall
        # through to comparing values.
        for fname, fval in sorted(self.items()):
            display = getattr(fname, "display", None)
            if id(fval) in reentrance_ids:
                segments.append(f"{fname}->({reentrance_ids[id(fval)]})")
            elif (
                display == "prefix" and not prefix and isinstance(fval, (Variable, str))
            ):
                prefix = "%s" % fval
            elif display == "slash" and not suffix:
                if isinstance(fval, Variable):
                    suffix = "/%s" % fval.name
                else:
                    suffix = "/%s" % repr(fval)
            elif isinstance(fval, Variable):
                segments.append(f"{fname}={fval.name}")
            elif fval is True:
                segments.append("+%s" % fname)
            elif fval is False:
                segments.append("-%s" % fname)
            elif isinstance(fval, Expression):
                segments.append(f"{fname}=<{fval}>")
            elif not isinstance(fval, FeatStruct):
                segments.append(f"{fname}={repr(fval)}")
            else:
                fval_repr = fval._repr(reentrances, reentrance_ids)
                segments.append(f"{fname}={fval_repr}")
        # If it's reentrant, then add on an identifier tag.
        if reentrances[id(self)]:
            prefix = f"({reentrance_ids[id(self)]}){prefix}"
        return "{}[{}]{}".format(prefix, ", ".join(segments), suffix)

    def _str(self, reentrances, reentrance_ids):
        """
        :return: A list of lines composing a string representation of
            this feature dictionary.
        :param reentrances: A dictionary that maps from the ``id`` of
            each feature value in self, indicating whether that value
            is reentrant or not.
        :param reentrance_ids: A dictionary mapping from each ``id``
            of a feature value to a unique identifier.  This is modified
            by ``repr``: the first time a reentrant feature value is
            displayed, an identifier is added to ``reentrance_ids`` for
            it.
        """
        # If this is the first time we've seen a reentrant structure,
        # then tack on an id string.
        if reentrances[id(self)]:
            assert id(self) not in reentrance_ids
            reentrance_ids[id(self)] = repr(len(reentrance_ids) + 1)

        # Special case: empty feature dict.
        if len(self) == 0:
            if reentrances[id(self)]:
                return ["(%s) []" % reentrance_ids[id(self)]]
            else:
                return ["[]"]

        # What's the longest feature name?  Use this to align names.
        maxfnamelen = max(len("%s" % k) for k in self.keys())

        lines = []
        # sorting note: keys are unique strings, so we'll never fall
        # through to comparing values.
        for fname, fval in sorted(self.items()):
            fname = ("%s" % fname).ljust(maxfnamelen)
            if isinstance(fval, Variable):
                lines.append(f"{fname} = {fval.name}")

            elif isinstance(fval, Expression):
                lines.append(f"{fname} = <{fval}>")

            elif isinstance(fval, FeatList):
                fval_repr = fval._repr(reentrances, reentrance_ids)
                lines.append(f"{fname} = {repr(fval_repr)}")

            elif not isinstance(fval, FeatDict):
                # It's not a nested feature structure -- just print it.
                lines.append(f"{fname} = {repr(fval)}")

            elif id(fval) in reentrance_ids:
                # It's a feature structure we've seen before -- print
                # the reentrance id.
                lines.append(f"{fname} -> ({reentrance_ids[id(fval)]})")

            else:
                # It's a new feature structure.  Separate it from
                # other values by a blank line.
                if lines and lines[-1] != "":
                    lines.append("")

                # Recursively print the feature's value (fval).
                fval_lines = fval._str(reentrances, reentrance_ids)

                # Indent each line to make room for fname.
                fval_lines = [(" " * (maxfnamelen + 3)) + l for l in fval_lines]

                # Pick which line we'll display fname on, & splice it in.
                nameline = (len(fval_lines) - 1) // 2
                fval_lines[nameline] = (
                    fname + " =" + fval_lines[nameline][maxfnamelen + 2 :]
                )

                # Add the feature structure to the output.
                lines += fval_lines

                # Separate FeatStructs by a blank line.
                lines.append("")

        # Get rid of any excess blank lines.
        if lines[-1] == "":
            lines.pop()

        # Add brackets around everything.
        maxlen = max(len(line) for line in lines)
        lines = ["[ {}{} ]".format(line, " " * (maxlen - len(line))) for line in lines]

        # If it's reentrant, then add on an identifier tag.
        if reentrances[id(self)]:
            idstr = "(%s) " % reentrance_ids[id(self)]
            lines = [(" " * len(idstr)) + l for l in lines]
            idline = (len(lines) - 1) // 2
            lines[idline] = idstr + lines[idline][len(idstr) :]

        return lines


######################################################################
# Feature List
######################################################################


class FeatList(FeatStruct, list):
    """
    A list of feature values, where each feature value is either a
    basic value (such as a string or an integer), or a nested feature
    structure.

    Feature lists may contain reentrant feature values.  A "reentrant
    feature value" is a single feature value that can be accessed via
    multiple feature paths.  Feature lists may also be cyclic.

    Two feature lists are considered equal if they assign the same
    values to all features, and have the same reentrances.

    :see: ``FeatStruct`` for information about feature paths, reentrance,
        cyclic feature structures, mutability, freezing, and hashing.
    """

    def __init__(self, features=()):
        """
        Create a new feature list, with the specified features.

        :param features: The initial list of features for this feature
            list.  If ``features`` is a string, then it is paresd using
            ``FeatStructReader``.  Otherwise, it should be a sequence
            of basic values and nested feature structures.
        """
        if isinstance(features, str):
            FeatStructReader().fromstring(features, self)
        else:
            list.__init__(self, features)

    # ////////////////////////////////////////////////////////////
    # { List methods
    # ////////////////////////////////////////////////////////////
    _INDEX_ERROR = "Expected int or feature path.  Got %r."

    def __getitem__(self, name_or_path):
        if isinstance(name_or_path, int):
            return list.__getitem__(self, name_or_path)
        elif isinstance(name_or_path, tuple):
            try:
                val = self
                for fid in name_or_path:
                    if not isinstance(val, FeatStruct):
                        raise KeyError  # path contains base value
                    val = val[fid]
                return val
            except (KeyError, IndexError) as e:
                raise KeyError(name_or_path) from e
        else:
            raise TypeError(self._INDEX_ERROR % name_or_path)

    def __delitem__(self, name_or_path):
        """If the feature with the given name or path exists, delete
        its value; otherwise, raise ``KeyError``."""
        if self._frozen:
            raise ValueError(_FROZEN_ERROR)
        if isinstance(name_or_path, (int, slice)):
            return list.__delitem__(self, name_or_path)
        elif isinstance(name_or_path, tuple):
            if len(name_or_path) == 0:
                raise ValueError("The path () can not be set")
            else:
                parent = self[name_or_path[:-1]]
                if not isinstance(parent, FeatStruct):
                    raise KeyError(name_or_path)  # path contains base value
                del parent[name_or_path[-1]]
        else:
            raise TypeError(self._INDEX_ERROR % name_or_path)

    def __setitem__(self, name_or_path, value):
        """Set the value for the feature with the given name or path
        to ``value``.  If ``name_or_path`` is an invalid path, raise
        ``KeyError``."""
        if self._frozen:
            raise ValueError(_FROZEN_ERROR)
        if isinstance(name_or_path, (int, slice)):
            return list.__setitem__(self, name_or_path, value)
        elif isinstance(name_or_path, tuple):
            if len(name_or_path) == 0:
                raise ValueError("The path () can not be set")
            else:
                parent = self[name_or_path[:-1]]
                if not isinstance(parent, FeatStruct):
                    raise KeyError(name_or_path)  # path contains base value
                parent[name_or_path[-1]] = value
        else:
            raise TypeError(self._INDEX_ERROR % name_or_path)

    #    __delslice__ = _check_frozen(list.__delslice__, '               ')
    #    __setslice__ = _check_frozen(list.__setslice__, '               ')
    __iadd__ = _check_frozen(list.__iadd__)
    __imul__ = _check_frozen(list.__imul__)
    append = _check_frozen(list.append)
    extend = _check_frozen(list.extend)
    insert = _check_frozen(list.insert)
    pop = _check_frozen(list.pop)
    remove = _check_frozen(list.remove)
    reverse = _check_frozen(list.reverse)
    sort = _check_frozen(list.sort)

    ##////////////////////////////////////////////////////////////
    # { Copying
    ##////////////////////////////////////////////////////////////

    def __deepcopy__(self, memo):
        memo[id(self)] = selfcopy = self.__class__()
        selfcopy.extend(copy.deepcopy(fval, memo) for fval in self)
        return selfcopy

    ##////////////////////////////////////////////////////////////
    # { Uniform Accessor Methods
    ##////////////////////////////////////////////////////////////

    def _keys(self):
        return list(range(len(self)))

    def _values(self):
        return self

    def _items(self):
        return enumerate(self)

    ##////////////////////////////////////////////////////////////
    # { String Representations
    ##////////////////////////////////////////////////////////////

    # Special handling for: reentrances, variables, expressions.
    def _repr(self, reentrances, reentrance_ids):
        # If this is the first time we've seen a reentrant structure,
        # then assign it a unique identifier.
        if reentrances[id(self)]:
            assert id(self) not in reentrance_ids
            reentrance_ids[id(self)] = repr(len(reentrance_ids) + 1)
            prefix = "(%s)" % reentrance_ids[id(self)]
        else:
            prefix = ""

        segments = []
        for fval in self:
            if id(fval) in reentrance_ids:
                segments.append("->(%s)" % reentrance_ids[id(fval)])
            elif isinstance(fval, Variable):
                segments.append(fval.name)
            elif isinstance(fval, Expression):
                segments.append("%s" % fval)
            elif isinstance(fval, FeatStruct):
                segments.append(fval._repr(reentrances, reentrance_ids))
            else:
                segments.append("%s" % repr(fval))

        return "{}[{}]".format(prefix, ", ".join(segments))


######################################################################
# Variables & Bindings
######################################################################


def substitute_bindings(fstruct, bindings, fs_class="default"):
    """
    Return the feature structure that is obtained by replacing each
    variable bound by ``bindings`` with its binding.  If a variable is
    aliased to a bound variable, then it will be replaced by that
    variable's value.  If a variable is aliased to an unbound
    variable, then it will be replaced by that variable.

    :type bindings: dict(Variable -> any)
    :param bindings: A dictionary mapping from variables to values.
    """
    if fs_class == "default":
        fs_class = _default_fs_class(fstruct)
    fstruct = copy.deepcopy(fstruct)
    _substitute_bindings(fstruct, bindings, fs_class, set())
    return fstruct


def _substitute_bindings(fstruct, bindings, fs_class, visited):
    # Visit each node only once:
    if id(fstruct) in visited:
        return
    visited.add(id(fstruct))

    if _is_mapping(fstruct):
        items = fstruct.items()
    elif _is_sequence(fstruct):
        items = enumerate(fstruct)
    else:
        raise ValueError("Expected mapping or sequence")
    for fname, fval in items:
        while isinstance(fval, Variable) and fval in bindings:
            fval = fstruct[fname] = bindings[fval]
        if isinstance(fval, fs_class):
            _substitute_bindings(fval, bindings, fs_class, visited)
        elif isinstance(fval, SubstituteBindingsI):
            fstruct[fname] = fval.substitute_bindings(bindings)


def retract_bindings(fstruct, bindings, fs_class="default"):
    """
    Return the feature structure that is obtained by replacing each
    feature structure value that is bound by ``bindings`` with the
    variable that binds it.  A feature structure value must be
    identical to a bound value (i.e., have equal id) to be replaced.

    ``bindings`` is modified to point to this new feature structure,
    rather than the original feature structure.  Feature structure
    values in ``bindings`` may be modified if they are contained in
    ``fstruct``.
    """
    if fs_class == "default":
        fs_class = _default_fs_class(fstruct)
    (fstruct, new_bindings) = copy.deepcopy((fstruct, bindings))
    bindings.update(new_bindings)
    inv_bindings = {id(val): var for (var, val) in bindings.items()}
    _retract_bindings(fstruct, inv_bindings, fs_class, set())
    return fstruct


def _retract_bindings(fstruct, inv_bindings, fs_class, visited):
    # Visit each node only once:
    if id(fstruct) in visited:
        return
    visited.add(id(fstruct))

    if _is_mapping(fstruct):
        items = fstruct.items()
    elif _is_sequence(fstruct):
        items = enumerate(fstruct)
    else:
        raise ValueError("Expected mapping or sequence")
    for fname, fval in items:
        if isinstance(fval, fs_class):
            if id(fval) in inv_bindings:
                fstruct[fname] = inv_bindings[id(fval)]
            _retract_bindings(fval, inv_bindings, fs_class, visited)


def find_variables(fstruct, fs_class="default"):
    """
    :return: The set of variables used by this feature structure.
    :rtype: set(Variable)
    """
    if fs_class == "default":
        fs_class = _default_fs_class(fstruct)
    return _variables(fstruct, set(), fs_class, set())


def _variables(fstruct, vars, fs_class, visited):
    # Visit each node only once:
    if id(fstruct) in visited:
        return
    visited.add(id(fstruct))
    if _is_mapping(fstruct):
        items = fstruct.items()
    elif _is_sequence(fstruct):
        items = enumerate(fstruct)
    else:
        raise ValueError("Expected mapping or sequence")
    for fname, fval in items:
        if isinstance(fval, Variable):
            vars.add(fval)
        elif isinstance(fval, fs_class):
            _variables(fval, vars, fs_class, visited)
        elif isinstance(fval, SubstituteBindingsI):
            vars.update(fval.variables())
    return vars


def rename_variables(
    fstruct, vars=None, used_vars=(), new_vars=None, fs_class="default"
):
    """
    Return the feature structure that is obtained by replacing
    any of this feature structure's variables that are in ``vars``
    with new variables.  The names for these new variables will be
    names that are not used by any variable in ``vars``, or in
    ``used_vars``, or in this feature structure.

    :type vars: set
    :param vars: The set of variables that should be renamed.
        If not specified, ``find_variables(fstruct)`` is used; i.e., all
        variables will be given new names.
    :type used_vars: set
    :param used_vars: A set of variables whose names should not be
        used by the new variables.
    :type new_vars: dict(Variable -> Variable)
    :param new_vars: A dictionary that is used to hold the mapping
        from old variables to new variables.  For each variable *v*
        in this feature structure:

        - If ``new_vars`` maps *v* to *v'*, then *v* will be
          replaced by *v'*.
        - If ``new_vars`` does not contain *v*, but ``vars``
          does contain *v*, then a new entry will be added to
          ``new_vars``, mapping *v* to the new variable that is used
          to replace it.

    To consistently rename the variables in a set of feature
    structures, simply apply rename_variables to each one, using
    the same dictionary:

        >>> from nltk.featstruct import FeatStruct
        >>> fstruct1 = FeatStruct('[subj=[agr=[gender=?y]], obj=[agr=[gender=?y]]]')
        >>> fstruct2 = FeatStruct('[subj=[agr=[number=?z,gender=?y]], obj=[agr=[number=?z,gender=?y]]]')
        >>> new_vars = {}  # Maps old vars to alpha-renamed vars
        >>> fstruct1.rename_variables(new_vars=new_vars)
        [obj=[agr=[gender=?y2]], subj=[agr=[gender=?y2]]]
        >>> fstruct2.rename_variables(new_vars=new_vars)
        [obj=[agr=[gender=?y2, number=?z2]], subj=[agr=[gender=?y2, number=?z2]]]

    If new_vars is not specified, then an empty dictionary is used.
    """
    if fs_class == "default":
        fs_class = _default_fs_class(fstruct)

    # Default values:
    if new_vars is None:
        new_vars = {}
    if vars is None:
        vars = find_variables(fstruct, fs_class)
    else:
        vars = set(vars)

    # Add our own variables to used_vars.
    used_vars = find_variables(fstruct, fs_class).union(used_vars)

    # Copy ourselves, and rename variables in the copy.
    return _rename_variables(
        copy.deepcopy(fstruct), vars, used_vars, new_vars, fs_class, set()
    )


def _rename_variables(fstruct, vars, used_vars, new_vars, fs_class, visited):
    if id(fstruct) in visited:
        return
    visited.add(id(fstruct))
    if _is_mapping(fstruct):
        items = fstruct.items()
    elif _is_sequence(fstruct):
        items = enumerate(fstruct)
    else:
        raise ValueError("Expected mapping or sequence")
    for fname, fval in items:
        if isinstance(fval, Variable):
            # If it's in new_vars, then rebind it.
            if fval in new_vars:
                fstruct[fname] = new_vars[fval]
            # If it's in vars, pick a new name for it.
            elif fval in vars:
                new_vars[fval] = _rename_variable(fval, used_vars)
                fstruct[fname] = new_vars[fval]
                used_vars.add(new_vars[fval])
        elif isinstance(fval, fs_class):
            _rename_variables(fval, vars, used_vars, new_vars, fs_class, visited)
        elif isinstance(fval, SubstituteBindingsI):
            # Pick new names for any variables in `vars`
            for var in fval.variables():
                if var in vars and var not in new_vars:
                    new_vars[var] = _rename_variable(var, used_vars)
                    used_vars.add(new_vars[var])
            # Replace all variables in `new_vars`.
            fstruct[fname] = fval.substitute_bindings(new_vars)
    return fstruct


def _rename_variable(var, used_vars):
    name, n = re.sub(r"\d+$", "", var.name), 2
    if not name:
        name = "?"
    while Variable(f"{name}{n}") in used_vars:
        n += 1
    return Variable(f"{name}{n}")


def remove_variables(fstruct, fs_class="default"):
    """
    :rtype: FeatStruct
    :return: The feature structure that is obtained by deleting
        all features whose values are ``Variables``.
    """
    if fs_class == "default":
        fs_class = _default_fs_class(fstruct)
    return _remove_variables(copy.deepcopy(fstruct), fs_class, set())


def _remove_variables(fstruct, fs_class, visited):
    if id(fstruct) in visited:
        return
    visited.add(id(fstruct))

    if _is_mapping(fstruct):
        items = list(fstruct.items())
    elif _is_sequence(fstruct):
        items = list(enumerate(fstruct))
    else:
        raise ValueError("Expected mapping or sequence")

    for fname, fval in items:
        if isinstance(fval, Variable):
            del fstruct[fname]
        elif isinstance(fval, fs_class):
            _remove_variables(fval, fs_class, visited)
    return fstruct


######################################################################
# Unification
######################################################################


class _UnificationFailure:
    def __repr__(self):
        return "nltk.featstruct.UnificationFailure"


UnificationFailure = _UnificationFailure()
"""A unique value used to indicate unification failure.  It can be
   returned by ``Feature.unify_base_values()`` or by custom ``fail()``
   functions to indicate that unificaiton should fail."""


# The basic unification algorithm:
#   1. Make copies of self and other (preserving reentrance)
#   2. Destructively unify self and other
#   3. Apply forward pointers, to preserve reentrance.
#   4. Replace bound variables with their values.
def unify(
    fstruct1,
    fstruct2,
    bindings=None,
    trace=False,
    fail=None,
    rename_vars=True,
    fs_class="default",
):
    """
    Unify ``fstruct1`` with ``fstruct2``, and return the resulting feature
    structure.  This unified feature structure is the minimal
    feature structure that contains all feature value assignments from both
    ``fstruct1`` and ``fstruct2``, and that preserves all reentrancies.

    If no such feature structure exists (because ``fstruct1`` and
    ``fstruct2`` specify incompatible values for some feature), then
    unification fails, and ``unify`` returns None.

    Bound variables are replaced by their values.  Aliased
    variables are replaced by their representative variable
    (if unbound) or the value of their representative variable
    (if bound).  I.e., if variable *v* is in ``bindings``,
    then *v* is replaced by ``bindings[v]``.  This will
    be repeated until the variable is replaced by an unbound
    variable or a non-variable value.

    Unbound variables are bound when they are unified with
    values; and aliased when they are unified with variables.
    I.e., if variable *v* is not in ``bindings``, and is
    unified with a variable or value *x*, then
    ``bindings[v]`` is set to *x*.

    If ``bindings`` is unspecified, then all variables are
    assumed to be unbound.  I.e., ``bindings`` defaults to an
    empty dict.

        >>> from nltk.featstruct import FeatStruct
        >>> FeatStruct('[a=?x]').unify(FeatStruct('[b=?x]'))
        [a=?x, b=?x2]

    :type bindings: dict(Variable -> any)
    :param bindings: A set of variable bindings to be used and
        updated during unification.
    :type trace: bool
    :param trace: If true, generate trace output.
    :type rename_vars: bool
    :param rename_vars: If True, then rename any variables in
        ``fstruct2`` that are also used in ``fstruct1``, in order to
        avoid collisions on variable names.
    """
    # Decide which class(es) will be treated as feature structures,
    # for the purposes of unification.
    if fs_class == "default":
        fs_class = _default_fs_class(fstruct1)
        if _default_fs_class(fstruct2) != fs_class:
            raise ValueError(
                "Mixing FeatStruct objects with Python "
                "dicts and lists is not supported."
            )
    assert isinstance(fstruct1, fs_class)
    assert isinstance(fstruct2, fs_class)

    # If bindings are unspecified, use an empty set of bindings.
    user_bindings = bindings is not None
    if bindings is None:
        bindings = {}

    # Make copies of fstruct1 and fstruct2 (since the unification
    # algorithm is destructive). Do it all at once, to preserve
    # reentrance links between fstruct1 and fstruct2.  Copy bindings
    # as well, in case there are any bound vars that contain parts
    # of fstruct1 or fstruct2.
    (fstruct1copy, fstruct2copy, bindings_copy) = copy.deepcopy(
        (fstruct1, fstruct2, bindings)
    )

    # Copy the bindings back to the original bindings dict.
    bindings.update(bindings_copy)

    if rename_vars:
        vars1 = find_variables(fstruct1copy, fs_class)
        vars2 = find_variables(fstruct2copy, fs_class)
        _rename_variables(fstruct2copy, vars1, vars2, {}, fs_class, set())

    # Do the actual unification.  If it fails, return None.
    forward = {}
    if trace:
        _trace_unify_start((), fstruct1copy, fstruct2copy)
    try:
        result = _destructively_unify(
            fstruct1copy, fstruct2copy, bindings, forward, trace, fail, fs_class, ()
        )
    except _UnificationFailureError:
        return None

    # _destructively_unify might return UnificationFailure, e.g. if we
    # tried to unify a mapping with a sequence.
    if result is UnificationFailure:
        if fail is None:
            return None
        else:
            return fail(fstruct1copy, fstruct2copy, ())

    # Replace any feature structure that has a forward pointer
    # with the target of its forward pointer.
    result = _apply_forwards(result, forward, fs_class, set())
    if user_bindings:
        _apply_forwards_to_bindings(forward, bindings)

    # Replace bound vars with values.
    _resolve_aliases(bindings)
    _substitute_bindings(result, bindings, fs_class, set())

    # Return the result.
    if trace:
        _trace_unify_succeed((), result)
    if trace:
        _trace_bindings((), bindings)
    return result


class _UnificationFailureError(Exception):
    """An exception that is used by ``_destructively_unify`` to abort
    unification when a failure is encountered."""


def _destructively_unify(
    fstruct1, fstruct2, bindings, forward, trace, fail, fs_class, path
):
    """
    Attempt to unify ``fstruct1`` and ``fstruct2`` by modifying them
    in-place.  If the unification succeeds, then ``fstruct1`` will
    contain the unified value, the value of ``fstruct2`` is undefined,
    and forward[id(fstruct2)] is set to fstruct1.  If the unification
    fails, then a _UnificationFailureError is raised, and the
    values of ``fstruct1`` and ``fstruct2`` are undefined.

    :param bindings: A dictionary mapping variables to values.
    :param forward: A dictionary mapping feature structures ids
        to replacement structures.  When two feature structures
        are merged, a mapping from one to the other will be added
        to the forward dictionary; and changes will be made only
        to the target of the forward dictionary.
        ``_destructively_unify`` will always 'follow' any links
        in the forward dictionary for fstruct1 and fstruct2 before
        actually unifying them.
    :param trace: If true, generate trace output
    :param path: The feature path that led us to this unification
        step.  Used for trace output.
    """
    # If fstruct1 is already identical to fstruct2, we're done.
    # Note: this, together with the forward pointers, ensures
    # that unification will terminate even for cyclic structures.
    if fstruct1 is fstruct2:
        if trace:
            _trace_unify_identity(path, fstruct1)
        return fstruct1

    # Set fstruct2's forward pointer to point to fstruct1; this makes
    # fstruct1 the canonical copy for fstruct2.  Note that we need to
    # do this before we recurse into any child structures, in case
    # they're cyclic.
    forward[id(fstruct2)] = fstruct1

    # Unifying two mappings:
    if _is_mapping(fstruct1) and _is_mapping(fstruct2):
        for fname in fstruct1:
            if getattr(fname, "default", None) is not None:
                fstruct2.setdefault(fname, fname.default)
        for fname in fstruct2:
            if getattr(fname, "default", None) is not None:
                fstruct1.setdefault(fname, fname.default)

        # Unify any values that are defined in both fstruct1 and
        # fstruct2.  Copy any values that are defined in fstruct2 but
        # not in fstruct1 to fstruct1.  Note: sorting fstruct2's
        # features isn't actually necessary; but we do it to give
        # deterministic behavior, e.g. for tracing.
        for fname, fval2 in sorted(fstruct2.items()):
            if fname in fstruct1:
                fstruct1[fname] = _unify_feature_values(
                    fname,
                    fstruct1[fname],
                    fval2,
                    bindings,
                    forward,
                    trace,
                    fail,
                    fs_class,
                    path + (fname,),
                )
            else:
                fstruct1[fname] = fval2

        return fstruct1  # Contains the unified value.

    # Unifying two sequences:
    elif _is_sequence(fstruct1) and _is_sequence(fstruct2):
        # If the lengths don't match, fail.
        if len(fstruct1) != len(fstruct2):
            return UnificationFailure

        # Unify corresponding values in fstruct1 and fstruct2.
        for findex in range(len(fstruct1)):
            fstruct1[findex] = _unify_feature_values(
                findex,
                fstruct1[findex],
                fstruct2[findex],
                bindings,
                forward,
                trace,
                fail,
                fs_class,
                path + (findex,),
            )

        return fstruct1  # Contains the unified value.

    # Unifying sequence & mapping: fail.  The failure function
    # doesn't get a chance to recover in this case.
    elif (_is_sequence(fstruct1) or _is_mapping(fstruct1)) and (
        _is_sequence(fstruct2) or _is_mapping(fstruct2)
    ):
        return UnificationFailure

    # Unifying anything else: not allowed!
    raise TypeError("Expected mappings or sequences")


def _unify_feature_values(
    fname, fval1, fval2, bindings, forward, trace, fail, fs_class, fpath
):
    """
    Attempt to unify ``fval1`` and and ``fval2``, and return the
    resulting unified value.  The method of unification will depend on
    the types of ``fval1`` and ``fval2``:

      1. If they're both feature structures, then destructively
         unify them (see ``_destructively_unify()``.
      2. If they're both unbound variables, then alias one variable
         to the other (by setting bindings[v2]=v1).
      3. If one is an unbound variable, and the other is a value,
         then bind the unbound variable to the value.
      4. If one is a feature structure, and the other is a base value,
         then fail.
      5. If they're both base values, then unify them.  By default,
         this will succeed if they are equal, and fail otherwise.
    """
    if trace:
        _trace_unify_start(fpath, fval1, fval2)

    # Look up the "canonical" copy of fval1 and fval2
    while id(fval1) in forward:
        fval1 = forward[id(fval1)]
    while id(fval2) in forward:
        fval2 = forward[id(fval2)]

    # If fval1 or fval2 is a bound variable, then
    # replace it by the variable's bound value.  This
    # includes aliased variables, which are encoded as
    # variables bound to other variables.
    fvar1 = fvar2 = None
    while isinstance(fval1, Variable) and fval1 in bindings:
        fvar1 = fval1
        fval1 = bindings[fval1]
    while isinstance(fval2, Variable) and fval2 in bindings:
        fvar2 = fval2
        fval2 = bindings[fval2]

    # Case 1: Two feature structures (recursive case)
    if isinstance(fval1, fs_class) and isinstance(fval2, fs_class):
        result = _destructively_unify(
            fval1, fval2, bindings, forward, trace, fail, fs_class, fpath
        )

    # Case 2: Two unbound variables (create alias)
    elif isinstance(fval1, Variable) and isinstance(fval2, Variable):
        if fval1 != fval2:
            bindings[fval2] = fval1
        result = fval1

    # Case 3: An unbound variable and a value (bind)
    elif isinstance(fval1, Variable):
        bindings[fval1] = fval2
        result = fval1
    elif isinstance(fval2, Variable):
        bindings[fval2] = fval1
        result = fval2

    # Case 4: A feature structure & a base value (fail)
    elif isinstance(fval1, fs_class) or isinstance(fval2, fs_class):
        result = UnificationFailure

    # Case 5: Two base values
    else:
        # Case 5a: Feature defines a custom unification method for base values
        if isinstance(fname, Feature):
            result = fname.unify_base_values(fval1, fval2, bindings)
        # Case 5b: Feature value defines custom unification method
        elif isinstance(fval1, CustomFeatureValue):
            result = fval1.unify(fval2)
            # Sanity check: unify value should be symmetric
            if isinstance(fval2, CustomFeatureValue) and result != fval2.unify(fval1):
                raise AssertionError(
                    "CustomFeatureValue objects %r and %r disagree "
                    "about unification value: %r vs. %r"
                    % (fval1, fval2, result, fval2.unify(fval1))
                )
        elif isinstance(fval2, CustomFeatureValue):
            result = fval2.unify(fval1)
        # Case 5c: Simple values -- check if they're equal.
        else:
            if fval1 == fval2:
                result = fval1
            else:
                result = UnificationFailure

        # If either value was a bound variable, then update the
        # bindings.  (This is really only necessary if fname is a
        # Feature or if either value is a CustomFeatureValue.)
        if result is not UnificationFailure:
            if fvar1 is not None:
                bindings[fvar1] = result
                result = fvar1
            if fvar2 is not None and fvar2 != fvar1:
                bindings[fvar2] = result
                result = fvar2

    # If we unification failed, call the failure function; it
    # might decide to continue anyway.
    if result is UnificationFailure:
        if fail is not None:
            result = fail(fval1, fval2, fpath)
        if trace:
            _trace_unify_fail(fpath[:-1], result)
        if result is UnificationFailure:
            raise _UnificationFailureError

    # Normalize the result.
    if isinstance(result, fs_class):
        result = _apply_forwards(result, forward, fs_class, set())

    if trace:
        _trace_unify_succeed(fpath, result)
    if trace and isinstance(result, fs_class):
        _trace_bindings(fpath, bindings)

    return result


def _apply_forwards_to_bindings(forward, bindings):
    """
    Replace any feature structure that has a forward pointer with
    the target of its forward pointer (to preserve reentrancy).
    """
    for var, value in bindings.items():
        while id(value) in forward:
            value = forward[id(value)]
        bindings[var] = value


def _apply_forwards(fstruct, forward, fs_class, visited):
    """
    Replace any feature structure that has a forward pointer with
    the target of its forward pointer (to preserve reentrancy).
    """
    # Follow our own forwards pointers (if any)
    while id(fstruct) in forward:
        fstruct = forward[id(fstruct)]

    # Visit each node only once:
    if id(fstruct) in visited:
        return
    visited.add(id(fstruct))

    if _is_mapping(fstruct):
        items = fstruct.items()
    elif _is_sequence(fstruct):
        items = enumerate(fstruct)
    else:
        raise ValueError("Expected mapping or sequence")
    for fname, fval in items:
        if isinstance(fval, fs_class):
            # Replace w/ forwarded value.
            while id(fval) in forward:
                fval = forward[id(fval)]
            fstruct[fname] = fval
            # Recurse to child.
            _apply_forwards(fval, forward, fs_class, visited)

    return fstruct


def _resolve_aliases(bindings):
    """
    Replace any bound aliased vars with their binding; and replace
    any unbound aliased vars with their representative var.
    """
    for var, value in bindings.items():
        while isinstance(value, Variable) and value in bindings:
            value = bindings[var] = bindings[value]


def _trace_unify_start(path, fval1, fval2):
    if path == ():
        print("\nUnification trace:")
    else:
        fullname = ".".join("%s" % n for n in path)
        print("  " + "|   " * (len(path) - 1) + "|")
        print("  " + "|   " * (len(path) - 1) + "| Unify feature: %s" % fullname)
    print("  " + "|   " * len(path) + " / " + _trace_valrepr(fval1))
    print("  " + "|   " * len(path) + "|\\ " + _trace_valrepr(fval2))


def _trace_unify_identity(path, fval1):
    print("  " + "|   " * len(path) + "|")
    print("  " + "|   " * len(path) + "| (identical objects)")
    print("  " + "|   " * len(path) + "|")
    print("  " + "|   " * len(path) + "+-->" + repr(fval1))


def _trace_unify_fail(path, result):
    if result is UnificationFailure:
        resume = ""
    else:
        resume = " (nonfatal)"
    print("  " + "|   " * len(path) + "|   |")
    print("  " + "X   " * len(path) + "X   X <-- FAIL" + resume)


def _trace_unify_succeed(path, fval1):
    # Print the result.
    print("  " + "|   " * len(path) + "|")
    print("  " + "|   " * len(path) + "+-->" + repr(fval1))


def _trace_bindings(path, bindings):
    # Print the bindings (if any).
    if len(bindings) > 0:
        binditems = sorted(bindings.items(), key=lambda v: v[0].name)
        bindstr = "{%s}" % ", ".join(
            f"{var}: {_trace_valrepr(val)}" for (var, val) in binditems
        )
        print("  " + "|   " * len(path) + "    Bindings: " + bindstr)


def _trace_valrepr(val):
    if isinstance(val, Variable):
        return "%s" % val
    else:
        return "%s" % repr(val)


def subsumes(fstruct1, fstruct2):
    """
    Return True if ``fstruct1`` subsumes ``fstruct2``.  I.e., return
    true if unifying ``fstruct1`` with ``fstruct2`` would result in a
    feature structure equal to ``fstruct2.``

    :rtype: bool
    """
    return fstruct2 == unify(fstruct1, fstruct2)


def conflicts(fstruct1, fstruct2, trace=0):
    """
    Return a list of the feature paths of all features which are
    assigned incompatible values by ``fstruct1`` and ``fstruct2``.

    :rtype: list(tuple)
    """
    conflict_list = []

    def add_conflict(fval1, fval2, path):
        conflict_list.append(path)
        return fval1

    unify(fstruct1, fstruct2, fail=add_conflict, trace=trace)
    return conflict_list


######################################################################
# Helper Functions
######################################################################


def _is_mapping(v):
    return hasattr(v, "__contains__") and hasattr(v, "keys")


def _is_sequence(v):
    return hasattr(v, "__iter__") and hasattr(v, "__len__") and not isinstance(v, str)


def _default_fs_class(obj):
    if isinstance(obj, FeatStruct):
        return FeatStruct
    if isinstance(obj, (dict, list)):
        return (dict, list)
    else:
        raise ValueError(
            "To unify objects of type %s, you must specify "
            "fs_class explicitly." % obj.__class__.__name__
        )


######################################################################
# FeatureValueSet & FeatureValueTuple
######################################################################


class SubstituteBindingsSequence(SubstituteBindingsI):
    """
    A mixin class for sequence classes that distributes variables() and
    substitute_bindings() over the object's elements.
    """

    def variables(self):
        return [elt for elt in self if isinstance(elt, Variable)] + sum(
            (
                list(elt.variables())
                for elt in self
                if isinstance(elt, SubstituteBindingsI)
            ),
            [],
        )

    def substitute_bindings(self, bindings):
        return self.__class__([self.subst(v, bindings) for v in self])

    def subst(self, v, bindings):
        if isinstance(v, SubstituteBindingsI):
            return v.substitute_bindings(bindings)
        else:
            return bindings.get(v, v)


class FeatureValueTuple(SubstituteBindingsSequence, tuple):
    """
    A base feature value that is a tuple of other base feature values.
    FeatureValueTuple implements ``SubstituteBindingsI``, so it any
    variable substitutions will be propagated to the elements
    contained by the set.  A ``FeatureValueTuple`` is immutable.
    """

    def __repr__(self):  # [xx] really use %s here?
        if len(self) == 0:
            return "()"
        return "(%s)" % ", ".join(f"{b}" for b in self)


class FeatureValueSet(SubstituteBindingsSequence, frozenset):
    """
    A base feature value that is a set of other base feature values.
    FeatureValueSet implements ``SubstituteBindingsI``, so it any
    variable substitutions will be propagated to the elements
    contained by the set.  A ``FeatureValueSet`` is immutable.
    """

    def __repr__(self):  # [xx] really use %s here?
        if len(self) == 0:
            return "{/}"  # distinguish from dict.
        # n.b., we sort the string reprs of our elements, to ensure
        # that our own repr is deterministic.
        return "{%s}" % ", ".join(sorted(f"{b}" for b in self))

    __str__ = __repr__


class FeatureValueUnion(SubstituteBindingsSequence, frozenset):
    """
    A base feature value that represents the union of two or more
    ``FeatureValueSet`` or ``Variable``.
    """

    def __new__(cls, values):
        # If values contains FeatureValueUnions, then collapse them.
        values = _flatten(values, FeatureValueUnion)

        # If the resulting list contains no variables, then
        # use a simple FeatureValueSet instead.
        if sum(isinstance(v, Variable) for v in values) == 0:
            values = _flatten(values, FeatureValueSet)
            return FeatureValueSet(values)

        # If we contain a single variable, return that variable.
        if len(values) == 1:
            return list(values)[0]

        # Otherwise, build the FeatureValueUnion.
        return frozenset.__new__(cls, values)

    def __repr__(self):
        # n.b., we sort the string reprs of our elements, to ensure
        # that our own repr is deterministic.  also, note that len(self)
        # is guaranteed to be 2 or more.
        return "{%s}" % "+".join(sorted(f"{b}" for b in self))


class FeatureValueConcat(SubstituteBindingsSequence, tuple):
    """
    A base feature value that represents the concatenation of two or
    more ``FeatureValueTuple`` or ``Variable``.
    """

    def __new__(cls, values):
        # If values contains FeatureValueConcats, then collapse them.
        values = _flatten(values, FeatureValueConcat)

        # If the resulting list contains no variables, then
        # use a simple FeatureValueTuple instead.
        if sum(isinstance(v, Variable) for v in values) == 0:
            values = _flatten(values, FeatureValueTuple)
            return FeatureValueTuple(values)

        # If we contain a single variable, return that variable.
        if len(values) == 1:
            return list(values)[0]

        # Otherwise, build the FeatureValueConcat.
        return tuple.__new__(cls, values)

    def __repr__(self):
        # n.b.: len(self) is guaranteed to be 2 or more.
        return "(%s)" % "+".join(f"{b}" for b in self)


def _flatten(lst, cls):
    """
    Helper function -- return a copy of list, with all elements of
    type ``cls`` spliced in rather than appended in.
    """
    result = []
    for elt in lst:
        if isinstance(elt, cls):
            result.extend(elt)
        else:
            result.append(elt)
    return result


######################################################################
# Specialized Features
######################################################################


@total_ordering
class Feature:
    """
    A feature identifier that's specialized to put additional
    constraints, default values, etc.
    """

    def __init__(self, name, default=None, display=None):
        assert display in (None, "prefix", "slash")

        self._name = name  # [xx] rename to .identifier?
        self._default = default  # [xx] not implemented yet.
        self._display = display

        if self._display == "prefix":
            self._sortkey = (-1, self._name)
        elif self._display == "slash":
            self._sortkey = (1, self._name)
        else:
            self._sortkey = (0, self._name)

    @property
    def name(self):
        """The name of this feature."""
        return self._name

    @property
    def default(self):
        """Default value for this feature."""
        return self._default

    @property
    def display(self):
        """Custom display location: can be prefix, or slash."""
        return self._display

    def __repr__(self):
        return "*%s*" % self.name

    def __lt__(self, other):
        if isinstance(other, str):
            return True
        if not isinstance(other, Feature):
            raise_unorderable_types("<", self, other)
        return self._sortkey < other._sortkey

    def __eq__(self, other):
        return type(self) == type(other) and self._name == other._name

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self._name)

    # ////////////////////////////////////////////////////////////
    # These can be overridden by subclasses:
    # ////////////////////////////////////////////////////////////

    def read_value(self, s, position, reentrances, parser):
        return parser.read_value(s, position, reentrances)

    def unify_base_values(self, fval1, fval2, bindings):
        """
        If possible, return a single value..  If not, return
        the value ``UnificationFailure``.
        """
        if fval1 == fval2:
            return fval1
        else:
            return UnificationFailure


class SlashFeature(Feature):
    def read_value(self, s, position, reentrances, parser):
        return parser.read_partial(s, position, reentrances)


class RangeFeature(Feature):
    RANGE_RE = re.compile(r"(-?\d+):(-?\d+)")

    def read_value(self, s, position, reentrances, parser):
        m = self.RANGE_RE.match(s, position)
        if not m:
            raise ValueError("range", position)
        return (int(m.group(1)), int(m.group(2))), m.end()

    def unify_base_values(self, fval1, fval2, bindings):
        if fval1 is None:
            return fval2
        if fval2 is None:
            return fval1
        rng = max(fval1[0], fval2[0]), min(fval1[1], fval2[1])
        if rng[1] < rng[0]:
            return UnificationFailure
        return rng


SLASH = SlashFeature("slash", default=False, display="slash")
TYPE = Feature("type", display="prefix")


######################################################################
# Specialized Feature Values
######################################################################


@total_ordering
class CustomFeatureValue:
    """
    An abstract base class for base values that define a custom
    unification method.  The custom unification method of
    ``CustomFeatureValue`` will be used during unification if:

      - The ``CustomFeatureValue`` is unified with another base value.
      - The ``CustomFeatureValue`` is not the value of a customized
        ``Feature`` (which defines its own unification method).

    If two ``CustomFeatureValue`` objects are unified with one another
    during feature structure unification, then the unified base values
    they return *must* be equal; otherwise, an ``AssertionError`` will
    be raised.

    Subclasses must define ``unify()``, ``__eq__()`` and ``__lt__()``.
    Subclasses may also wish to define ``__hash__()``.
    """

    def unify(self, other):
        """
        If this base value unifies with ``other``, then return the
        unified value.  Otherwise, return ``UnificationFailure``.
        """
        raise NotImplementedError("abstract base class")

    def __eq__(self, other):
        return NotImplemented

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return NotImplemented

    def __hash__(self):
        raise TypeError("%s objects or unhashable" % self.__class__.__name__)


######################################################################
# Feature Structure Reader
######################################################################


class FeatStructReader:
    def __init__(
        self,
        features=(SLASH, TYPE),
        fdict_class=FeatStruct,
        flist_class=FeatList,
        logic_parser=None,
    ):
        self._features = {f.name: f for f in features}
        self._fdict_class = fdict_class
        self._flist_class = flist_class
        self._prefix_feature = None
        self._slash_feature = None
        for feature in features:
            if feature.display == "slash":
                if self._slash_feature:
                    raise ValueError("Multiple features w/ display=slash")
                self._slash_feature = feature
            if feature.display == "prefix":
                if self._prefix_feature:
                    raise ValueError("Multiple features w/ display=prefix")
                self._prefix_feature = feature
        self._features_with_defaults = [
            feature for feature in features if feature.default is not None
        ]
        if logic_parser is None:
            logic_parser = LogicParser()
        self._logic_parser = logic_parser

    def fromstring(self, s, fstruct=None):
        """
        Convert a string representation of a feature structure (as
        displayed by repr) into a ``FeatStruct``.  This process
        imposes the following restrictions on the string
        representation:

        - Feature names cannot contain any of the following:
          whitespace, parentheses, quote marks, equals signs,
          dashes, commas, and square brackets.  Feature names may
          not begin with plus signs or minus signs.
        - Only the following basic feature value are supported:
          strings, integers, variables, None, and unquoted
          alphanumeric strings.
        - For reentrant values, the first mention must specify
          a reentrance identifier and a value; and any subsequent
          mentions must use arrows (``'->'``) to reference the
          reentrance identifier.
        """
        s = s.strip()
        value, position = self.read_partial(s, 0, {}, fstruct)
        if position != len(s):
            self._error(s, "end of string", position)
        return value

    _START_FSTRUCT_RE = re.compile(r"\s*(?:\((\d+)\)\s*)?(\??[\w-]+)?(\[)")
    _END_FSTRUCT_RE = re.compile(r"\s*]\s*")
    _SLASH_RE = re.compile(r"/")
    _FEATURE_NAME_RE = re.compile(r'\s*([+-]?)([^\s\(\)<>"\'\-=\[\],]+)\s*')
    _REENTRANCE_RE = re.compile(r"\s*->\s*")
    _TARGET_RE = re.compile(r"\s*\((\d+)\)\s*")
    _ASSIGN_RE = re.compile(r"\s*=\s*")
    _COMMA_RE = re.compile(r"\s*,\s*")
    _BARE_PREFIX_RE = re.compile(r"\s*(?:\((\d+)\)\s*)?(\??[\w-]+\s*)()")
    # This one is used to distinguish fdicts from flists:
    _START_FDICT_RE = re.compile(
        r"(%s)|(%s\s*(%s\s*(=|->)|[+-]%s|\]))"
        % (
            _BARE_PREFIX_RE.pattern,
            _START_FSTRUCT_RE.pattern,
            _FEATURE_NAME_RE.pattern,
            _FEATURE_NAME_RE.pattern,
        )
    )

    def read_partial(self, s, position=0, reentrances=None, fstruct=None):
        """
        Helper function that reads in a feature structure.

        :param s: The string to read.
        :param position: The position in the string to start parsing.
        :param reentrances: A dictionary from reentrance ids to values.
            Defaults to an empty dictionary.
        :return: A tuple (val, pos) of the feature structure created by
            parsing and the position where the parsed feature structure ends.
        :rtype: bool
        """
        if reentrances is None:
            reentrances = {}
        try:
            return self._read_partial(s, position, reentrances, fstruct)
        except ValueError as e:
            if len(e.args) != 2:
                raise
            self._error(s, *e.args)

    def _read_partial(self, s, position, reentrances, fstruct=None):
        # Create the new feature structure
        if fstruct is None:
            if self._START_FDICT_RE.match(s, position):
                fstruct = self._fdict_class()
            else:
                fstruct = self._flist_class()

        # Read up to the open bracket.
        match = self._START_FSTRUCT_RE.match(s, position)
        if not match:
            match = self._BARE_PREFIX_RE.match(s, position)
            if not match:
                raise ValueError("open bracket or identifier", position)
        position = match.end()

        # If there as an identifier, record it.
        if match.group(1):
            identifier = match.group(1)
            if identifier in reentrances:
                raise ValueError("new identifier", match.start(1))
            reentrances[identifier] = fstruct

        if isinstance(fstruct, FeatDict):
            fstruct.clear()
            return self._read_partial_featdict(s, position, match, reentrances, fstruct)
        else:
            del fstruct[:]
            return self._read_partial_featlist(s, position, match, reentrances, fstruct)

    def _read_partial_featlist(self, s, position, match, reentrances, fstruct):
        # Prefix features are not allowed:
        if match.group(2):
            raise ValueError("open bracket")
        # Bare prefixes are not allowed:
        if not match.group(3):
            raise ValueError("open bracket")

        # Build a list of the features defined by the structure.
        while position < len(s):
            # Check for the close bracket.
            match = self._END_FSTRUCT_RE.match(s, position)
            if match is not None:
                return fstruct, match.end()

            # Reentances have the form "-> (target)"
            match = self._REENTRANCE_RE.match(s, position)
            if match:
                position = match.end()
                match = self._TARGET_RE.match(s, position)
                if not match:
                    raise ValueError("identifier", position)
                target = match.group(1)
                if target not in reentrances:
                    raise ValueError("bound identifier", position)
                position = match.end()
                fstruct.append(reentrances[target])

            # Anything else is a value.
            else:
                value, position = self._read_value(0, s, position, reentrances)
                fstruct.append(value)

            # If there's a close bracket, handle it at the top of the loop.
            if self._END_FSTRUCT_RE.match(s, position):
                continue

            # Otherwise, there should be a comma
            match = self._COMMA_RE.match(s, position)
            if match is None:
                raise ValueError("comma", position)
            position = match.end()

        # We never saw a close bracket.
        raise ValueError("close bracket", position)

    def _read_partial_featdict(self, s, position, match, reentrances, fstruct):
        # If there was a prefix feature, record it.
        if match.group(2):
            if self._prefix_feature is None:
                raise ValueError("open bracket or identifier", match.start(2))
            prefixval = match.group(2).strip()
            if prefixval.startswith("?"):
                prefixval = Variable(prefixval)
            fstruct[self._prefix_feature] = prefixval

        # If group 3 is empty, then we just have a bare prefix, so
        # we're done.
        if not match.group(3):
            return self._finalize(s, match.end(), reentrances, fstruct)

        # Build a list of the features defined by the structure.
        # Each feature has one of the three following forms:
        #     name = value
        #     name -> (target)
        #     +name
        #     -name
        while position < len(s):
            # Use these variables to hold info about each feature:
            name = value = None

            # Check for the close bracket.
            match = self._END_FSTRUCT_RE.match(s, position)
            if match is not None:
                return self._finalize(s, match.end(), reentrances, fstruct)

            # Get the feature name's name
            match = self._FEATURE_NAME_RE.match(s, position)
            if match is None:
                raise ValueError("feature name", position)
            name = match.group(2)
            position = match.end()

            # Check if it's a special feature.
            if name[0] == "*" and name[-1] == "*":
                name = self._features.get(name[1:-1])
                if name is None:
                    raise ValueError("known special feature", match.start(2))

            # Check if this feature has a value already.
            if name in fstruct:
                raise ValueError("new name", match.start(2))

            # Boolean value ("+name" or "-name")
            if match.group(1) == "+":
                value = True
            if match.group(1) == "-":
                value = False

            # Reentrance link ("-> (target)")
            if value is None:
                match = self._REENTRANCE_RE.match(s, position)
                if match is not None:
                    position = match.end()
                    match = self._TARGET_RE.match(s, position)
                    if not match:
                        raise ValueError("identifier", position)
                    target = match.group(1)
                    if target not in reentrances:
                        raise ValueError("bound identifier", position)
                    position = match.end()
                    value = reentrances[target]

            # Assignment ("= value").
            if value is None:
                match = self._ASSIGN_RE.match(s, position)
                if match:
                    position = match.end()
                    value, position = self._read_value(name, s, position, reentrances)
                # None of the above: error.
                else:
                    raise ValueError("equals sign", position)

            # Store the value.
            fstruct[name] = value

            # If there's a close bracket, handle it at the top of the loop.
            if self._END_FSTRUCT_RE.match(s, position):
                continue

            # Otherwise, there should be a comma
            match = self._COMMA_RE.match(s, position)
            if match is None:
                raise ValueError("comma", position)
            position = match.end()

        # We never saw a close bracket.
        raise ValueError("close bracket", position)

    def _finalize(self, s, pos, reentrances, fstruct):
        """
        Called when we see the close brace -- checks for a slash feature,
        and adds in default values.
        """
        # Add the slash feature (if any)
        match = self._SLASH_RE.match(s, pos)
        if match:
            name = self._slash_feature
            v, pos = self._read_value(name, s, match.end(), reentrances)
            fstruct[name] = v
        ## Add any default features.  -- handle in unficiation instead?
        # for feature in self._features_with_defaults:
        #    fstruct.setdefault(feature, feature.default)
        # Return the value.
        return fstruct, pos

    def _read_value(self, name, s, position, reentrances):
        if isinstance(name, Feature):
            return name.read_value(s, position, reentrances, self)
        else:
            return self.read_value(s, position, reentrances)

    def read_value(self, s, position, reentrances):
        for handler, regexp in self.VALUE_HANDLERS:
            match = regexp.match(s, position)
            if match:
                handler_func = getattr(self, handler)
                return handler_func(s, position, reentrances, match)
        raise ValueError("value", position)

    def _error(self, s, expected, position):
        lines = s.split("\n")
        while position > len(lines[0]):
            position -= len(lines.pop(0)) + 1  # +1 for the newline.
        estr = (
            "Error parsing feature structure\n    "
            + lines[0]
            + "\n    "
            + " " * position
            + "^ "
            + "Expected %s" % expected
        )
        raise ValueError(estr)

    # ////////////////////////////////////////////////////////////
    # { Value Readers
    # ////////////////////////////////////////////////////////////

    #: A table indicating how feature values should be processed.  Each
    #: entry in the table is a pair (handler, regexp).  The first entry
    #: with a matching regexp will have its handler called.  Handlers
    #: should have the following signature::
    #:
    #:    def handler(s, position, reentrances, match): ...
    #:
    #: and should return a tuple (value, position), where position is
    #: the string position where the value ended.  (n.b.: order is
    #: important here!)
    VALUE_HANDLERS = [
        ("read_fstruct_value", _START_FSTRUCT_RE),
        ("read_var_value", re.compile(r"\?[a-zA-Z_][a-zA-Z0-9_]*")),
        ("read_str_value", re.compile("[uU]?[rR]?(['\"])")),
        ("read_int_value", re.compile(r"-?\d+")),
        ("read_sym_value", re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")),
        (
            "read_app_value",
            re.compile(r"<(app)\((\?[a-z][a-z]*)\s*," r"\s*(\?[a-z][a-z]*)\)>"),
        ),
        #       ('read_logic_value', re.compile(r'<([^>]*)>')),
        # lazily match any character after '<' until we hit a '>' not preceded by '-'
        ("read_logic_value", re.compile(r"<(.*?)(?<!-)>")),
        ("read_set_value", re.compile(r"{")),
        ("read_tuple_value", re.compile(r"\(")),
    ]

    def read_fstruct_value(self, s, position, reentrances, match):
        return self.read_partial(s, position, reentrances)

    def read_str_value(self, s, position, reentrances, match):
        return read_str(s, position)

    def read_int_value(self, s, position, reentrances, match):
        return int(match.group()), match.end()

    # Note: the '?' is included in the variable name.
    def read_var_value(self, s, position, reentrances, match):
        return Variable(match.group()), match.end()

    _SYM_CONSTS = {"None": None, "True": True, "False": False}

    def read_sym_value(self, s, position, reentrances, match):
        val, end = match.group(), match.end()
        return self._SYM_CONSTS.get(val, val), end

    def read_app_value(self, s, position, reentrances, match):
        """Mainly included for backwards compat."""
        return self._logic_parser.parse("%s(%s)" % match.group(2, 3)), match.end()

    def read_logic_value(self, s, position, reentrances, match):
        try:
            try:
                expr = self._logic_parser.parse(match.group(1))
            except LogicalExpressionException as e:
                raise ValueError from e
            return expr, match.end()
        except ValueError as e:
            raise ValueError("logic expression", match.start(1)) from e

    def read_tuple_value(self, s, position, reentrances, match):
        return self._read_seq_value(
            s, position, reentrances, match, ")", FeatureValueTuple, FeatureValueConcat
        )

    def read_set_value(self, s, position, reentrances, match):
        return self._read_seq_value(
            s, position, reentrances, match, "}", FeatureValueSet, FeatureValueUnion
        )

    def _read_seq_value(
        self, s, position, reentrances, match, close_paren, seq_class, plus_class
    ):
        """
        Helper function used by read_tuple_value and read_set_value.
        """
        cp = re.escape(close_paren)
        position = match.end()
        # Special syntax of empty tuples:
        m = re.compile(r"\s*/?\s*%s" % cp).match(s, position)
        if m:
            return seq_class(), m.end()
        # Read values:
        values = []
        seen_plus = False
        while True:
            # Close paren: return value.
            m = re.compile(r"\s*%s" % cp).match(s, position)
            if m:
                if seen_plus:
                    return plus_class(values), m.end()
                else:
                    return seq_class(values), m.end()

            # Read the next value.
            val, position = self.read_value(s, position, reentrances)
            values.append(val)

            # Comma or looking at close paren
            m = re.compile(r"\s*(,|\+|(?=%s))\s*" % cp).match(s, position)
            if not m:
                raise ValueError("',' or '+' or '%s'" % cp, position)
            if m.group(1) == "+":
                seen_plus = True
            position = m.end()


######################################################################
# { Demo
######################################################################


def display_unification(fs1, fs2, indent="  "):
    # Print the two input feature structures, side by side.
    fs1_lines = ("%s" % fs1).split("\n")
    fs2_lines = ("%s" % fs2).split("\n")
    if len(fs1_lines) > len(fs2_lines):
        blankline = "[" + " " * (len(fs2_lines[0]) - 2) + "]"
        fs2_lines += [blankline] * len(fs1_lines)
    else:
        blankline = "[" + " " * (len(fs1_lines[0]) - 2) + "]"
        fs1_lines += [blankline] * len(fs2_lines)
    for fs1_line, fs2_line in zip(fs1_lines, fs2_lines):
        print(indent + fs1_line + "   " + fs2_line)
    print(indent + "-" * len(fs1_lines[0]) + "   " + "-" * len(fs2_lines[0]))

    linelen = len(fs1_lines[0]) * 2 + 3
    print(indent + "|               |".center(linelen))
    print(indent + "+-----UNIFY-----+".center(linelen))
    print(indent + "|".center(linelen))
    print(indent + "V".center(linelen))

    bindings = {}

    result = fs1.unify(fs2, bindings)
    if result is None:
        print(indent + "(FAILED)".center(linelen))
    else:
        print(
            "\n".join(indent + l.center(linelen) for l in ("%s" % result).split("\n"))
        )
        if bindings and len(bindings.bound_variables()) > 0:
            print(repr(bindings).center(linelen))
    return result


def interactive_demo(trace=False):
    import random
    import sys

    HELP = """
    1-%d: Select the corresponding feature structure
    q: Quit
    t: Turn tracing on or off
    l: List all feature structures
    ?: Help
    """

    print(
        """
    This demo will repeatedly present you with a list of feature
    structures, and ask you to choose two for unification.  Whenever a
    new feature structure is generated, it is added to the list of
    choices that you can pick from.  However, since this can be a
    large number of feature structures, the demo will only print out a
    random subset for you to choose between at a given time.  If you
    want to see the complete lists, type "l".  For a list of valid
    commands, type "?".
    """
    )
    print('Press "Enter" to continue...')
    sys.stdin.readline()

    fstruct_strings = [
        "[agr=[number=sing, gender=masc]]",
        "[agr=[gender=masc, person=3]]",
        "[agr=[gender=fem, person=3]]",
        "[subj=[agr=(1)[]], agr->(1)]",
        "[obj=?x]",
        "[subj=?x]",
        "[/=None]",
        "[/=NP]",
        "[cat=NP]",
        "[cat=VP]",
        "[cat=PP]",
        "[subj=[agr=[gender=?y]], obj=[agr=[gender=?y]]]",
        "[gender=masc, agr=?C]",
        "[gender=?S, agr=[gender=?S,person=3]]",
    ]

    all_fstructs = [
        (i, FeatStruct(fstruct_strings[i])) for i in range(len(fstruct_strings))
    ]

    def list_fstructs(fstructs):
        for i, fstruct in fstructs:
            print()
            lines = ("%s" % fstruct).split("\n")
            print("%3d: %s" % (i + 1, lines[0]))
            for line in lines[1:]:
                print("     " + line)
        print()

    while True:
        # Pick 5 feature structures at random from the master list.
        MAX_CHOICES = 5
        if len(all_fstructs) > MAX_CHOICES:
            fstructs = sorted(random.sample(all_fstructs, MAX_CHOICES))
        else:
            fstructs = all_fstructs

        print("_" * 75)

        print("Choose two feature structures to unify:")
        list_fstructs(fstructs)

        selected = [None, None]
        for nth, i in (("First", 0), ("Second", 1)):
            while selected[i] is None:
                print(
                    (
                        "%s feature structure (1-%d,q,t,l,?): "
                        % (nth, len(all_fstructs))
                    ),
                    end=" ",
                )
                try:
                    input = sys.stdin.readline().strip()
                    if input in ("q", "Q", "x", "X"):
                        return
                    if input in ("t", "T"):
                        trace = not trace
                        print("   Trace = %s" % trace)
                        continue
                    if input in ("h", "H", "?"):
                        print(HELP % len(fstructs))
                        continue
                    if input in ("l", "L"):
                        list_fstructs(all_fstructs)
                        continue
                    num = int(input) - 1
                    selected[i] = all_fstructs[num][1]
                    print()
                except:
                    print("Bad sentence number")
                    continue

        if trace:
            result = selected[0].unify(selected[1], trace=1)
        else:
            result = display_unification(selected[0], selected[1])
        if result is not None:
            for i, fstruct in all_fstructs:
                if repr(result) == repr(fstruct):
                    break
            else:
                all_fstructs.append((len(all_fstructs), result))

        print('\nType "Enter" to continue unifying; or "q" to quit.')
        input = sys.stdin.readline().strip()
        if input in ("q", "Q", "x", "X"):
            return


def demo(trace=False):
    """
    Just for testing
    """
    # import random

    # processor breaks with values like '3rd'
    fstruct_strings = [
        "[agr=[number=sing, gender=masc]]",
        "[agr=[gender=masc, person=3]]",
        "[agr=[gender=fem, person=3]]",
        "[subj=[agr=(1)[]], agr->(1)]",
        "[obj=?x]",
        "[subj=?x]",
        "[/=None]",
        "[/=NP]",
        "[cat=NP]",
        "[cat=VP]",
        "[cat=PP]",
        "[subj=[agr=[gender=?y]], obj=[agr=[gender=?y]]]",
        "[gender=masc, agr=?C]",
        "[gender=?S, agr=[gender=?S,person=3]]",
    ]
    all_fstructs = [FeatStruct(fss) for fss in fstruct_strings]
    # MAX_CHOICES = 5
    # if len(all_fstructs) > MAX_CHOICES:
    # fstructs = random.sample(all_fstructs, MAX_CHOICES)
    # fstructs.sort()
    # else:
    # fstructs = all_fstructs

    for fs1 in all_fstructs:
        for fs2 in all_fstructs:
            print(
                "\n*******************\nfs1 is:\n%s\n\nfs2 is:\n%s\n\nresult is:\n%s"
                % (fs1, fs2, unify(fs1, fs2))
            )


if __name__ == "__main__":
    demo()

__all__ = [
    "FeatStruct",
    "FeatDict",
    "FeatList",
    "unify",
    "subsumes",
    "conflicts",
    "Feature",
    "SlashFeature",
    "RangeFeature",
    "SLASH",
    "TYPE",
    "FeatStructReader",
]

# === NexusCore/openenv\Lib\site-packages\numpy\_core\numeric.py ===
import builtins
import functools
import itertools
import math
import numbers
import operator
import sys
import warnings

import numpy as np
from numpy.exceptions import AxisError

from . import multiarray, numerictypes, overrides, shape_base, umath
from . import numerictypes as nt
from ._ufunc_config import errstate
from .multiarray import (  # noqa: F401
    ALLOW_THREADS,
    BUFSIZE,
    CLIP,
    MAXDIMS,
    MAY_SHARE_BOUNDS,
    MAY_SHARE_EXACT,
    RAISE,
    WRAP,
    arange,
    array,
    asanyarray,
    asarray,
    ascontiguousarray,
    asfortranarray,
    broadcast,
    can_cast,
    concatenate,
    copyto,
    dot,
    dtype,
    empty,
    empty_like,
    flatiter,
    from_dlpack,
    frombuffer,
    fromfile,
    fromiter,
    fromstring,
    inner,
    lexsort,
    matmul,
    may_share_memory,
    min_scalar_type,
    ndarray,
    nditer,
    nested_iters,
    normalize_axis_index,
    promote_types,
    putmask,
    result_type,
    shares_memory,
    vdot,
    vecdot,
    where,
    zeros,
)
from .overrides import finalize_array_function_like, set_module
from .umath import NAN, PINF, invert, multiply, sin

bitwise_not = invert
ufunc = type(sin)
newaxis = None

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


__all__ = [
    'newaxis', 'ndarray', 'flatiter', 'nditer', 'nested_iters', 'ufunc',
    'arange', 'array', 'asarray', 'asanyarray', 'ascontiguousarray',
    'asfortranarray', 'zeros', 'count_nonzero', 'empty', 'broadcast', 'dtype',
    'fromstring', 'fromfile', 'frombuffer', 'from_dlpack', 'where',
    'argwhere', 'copyto', 'concatenate', 'lexsort', 'astype',
    'can_cast', 'promote_types', 'min_scalar_type',
    'result_type', 'isfortran', 'empty_like', 'zeros_like', 'ones_like',
    'correlate', 'convolve', 'inner', 'dot', 'outer', 'vdot', 'roll',
    'rollaxis', 'moveaxis', 'cross', 'tensordot', 'little_endian',
    'fromiter', 'array_equal', 'array_equiv', 'indices', 'fromfunction',
    'isclose', 'isscalar', 'binary_repr', 'base_repr', 'ones',
    'identity', 'allclose', 'putmask',
    'flatnonzero', 'inf', 'nan', 'False_', 'True_', 'bitwise_not',
    'full', 'full_like', 'matmul', 'vecdot', 'shares_memory',
    'may_share_memory']


def _zeros_like_dispatcher(
    a, dtype=None, order=None, subok=None, shape=None, *, device=None
):
    return (a,)


@array_function_dispatch(_zeros_like_dispatcher)
def zeros_like(
    a, dtype=None, order='K', subok=True, shape=None, *, device=None
):
    """
    Return an array of zeros with the same shape and type as a given array.

    Parameters
    ----------
    a : array_like
        The shape and data-type of `a` define these same attributes of
        the returned array.
    dtype : data-type, optional
        Overrides the data type of the result.
    order : {'C', 'F', 'A', or 'K'}, optional
        Overrides the memory layout of the result. 'C' means C-order,
        'F' means F-order, 'A' means 'F' if `a` is Fortran contiguous,
        'C' otherwise. 'K' means match the layout of `a` as closely
        as possible.
    subok : bool, optional.
        If True, then the newly created array will use the sub-class
        type of `a`, otherwise it will be a base-class array. Defaults
        to True.
    shape : int or sequence of ints, optional.
        Overrides the shape of the result. If order='K' and the number of
        dimensions is unchanged, will try to keep order, otherwise,
        order='C' is implied.
    device : str, optional
        The device on which to place the created array. Default: None.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : ndarray
        Array of zeros with the same shape and type as `a`.

    See Also
    --------
    empty_like : Return an empty array with shape and type of input.
    ones_like : Return an array of ones with shape and type of input.
    full_like : Return a new array with shape of input filled with value.
    zeros : Return a new array setting values to zero.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(6)
    >>> x = x.reshape((2, 3))
    >>> x
    array([[0, 1, 2],
           [3, 4, 5]])
    >>> np.zeros_like(x)
    array([[0, 0, 0],
           [0, 0, 0]])

    >>> y = np.arange(3, dtype=float)
    >>> y
    array([0., 1., 2.])
    >>> np.zeros_like(y)
    array([0.,  0.,  0.])

    """
    res = empty_like(
        a, dtype=dtype, order=order, subok=subok, shape=shape, device=device
    )
    # needed instead of a 0 to get same result as zeros for string dtypes
    z = zeros(1, dtype=res.dtype)
    multiarray.copyto(res, z, casting='unsafe')
    return res


@finalize_array_function_like
@set_module('numpy')
def ones(shape, dtype=None, order='C', *, device=None, like=None):
    """
    Return a new array of given shape and type, filled with ones.

    Parameters
    ----------
    shape : int or sequence of ints
        Shape of the new array, e.g., ``(2, 3)`` or ``2``.
    dtype : data-type, optional
        The desired data-type for the array, e.g., `numpy.int8`.  Default is
        `numpy.float64`.
    order : {'C', 'F'}, optional, default: C
        Whether to store multi-dimensional data in row-major
        (C-style) or column-major (Fortran-style) order in
        memory.
    device : str, optional
        The device on which to place the created array. Default: None.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        Array of ones with the given shape, dtype, and order.

    See Also
    --------
    ones_like : Return an array of ones with shape and type of input.
    empty : Return a new uninitialized array.
    zeros : Return a new array setting values to zero.
    full : Return a new array of given shape filled with value.

    Examples
    --------
    >>> import numpy as np
    >>> np.ones(5)
    array([1., 1., 1., 1., 1.])

    >>> np.ones((5,), dtype=int)
    array([1, 1, 1, 1, 1])

    >>> np.ones((2, 1))
    array([[1.],
           [1.]])

    >>> s = (2,2)
    >>> np.ones(s)
    array([[1.,  1.],
           [1.,  1.]])

    """
    if like is not None:
        return _ones_with_like(
            like, shape, dtype=dtype, order=order, device=device
        )

    a = empty(shape, dtype, order, device=device)
    multiarray.copyto(a, 1, casting='unsafe')
    return a


_ones_with_like = array_function_dispatch()(ones)


def _ones_like_dispatcher(
    a, dtype=None, order=None, subok=None, shape=None, *, device=None
):
    return (a,)


@array_function_dispatch(_ones_like_dispatcher)
def ones_like(
    a, dtype=None, order='K', subok=True, shape=None, *, device=None
):
    """
    Return an array of ones with the same shape and type as a given array.

    Parameters
    ----------
    a : array_like
        The shape and data-type of `a` define these same attributes of
        the returned array.
    dtype : data-type, optional
        Overrides the data type of the result.
    order : {'C', 'F', 'A', or 'K'}, optional
        Overrides the memory layout of the result. 'C' means C-order,
        'F' means F-order, 'A' means 'F' if `a` is Fortran contiguous,
        'C' otherwise. 'K' means match the layout of `a` as closely
        as possible.
    subok : bool, optional.
        If True, then the newly created array will use the sub-class
        type of `a`, otherwise it will be a base-class array. Defaults
        to True.
    shape : int or sequence of ints, optional.
        Overrides the shape of the result. If order='K' and the number of
        dimensions is unchanged, will try to keep order, otherwise,
        order='C' is implied.
    device : str, optional
        The device on which to place the created array. Default: None.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : ndarray
        Array of ones with the same shape and type as `a`.

    See Also
    --------
    empty_like : Return an empty array with shape and type of input.
    zeros_like : Return an array of zeros with shape and type of input.
    full_like : Return a new array with shape of input filled with value.
    ones : Return a new array setting values to one.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(6)
    >>> x = x.reshape((2, 3))
    >>> x
    array([[0, 1, 2],
           [3, 4, 5]])
    >>> np.ones_like(x)
    array([[1, 1, 1],
           [1, 1, 1]])

    >>> y = np.arange(3, dtype=float)
    >>> y
    array([0., 1., 2.])
    >>> np.ones_like(y)
    array([1.,  1.,  1.])

    """
    res = empty_like(
        a, dtype=dtype, order=order, subok=subok, shape=shape, device=device
    )
    multiarray.copyto(res, 1, casting='unsafe')
    return res


def _full_dispatcher(
    shape, fill_value, dtype=None, order=None, *, device=None, like=None
):
    return (like,)


@finalize_array_function_like
@set_module('numpy')
def full(shape, fill_value, dtype=None, order='C', *, device=None, like=None):
    """
    Return a new array of given shape and type, filled with `fill_value`.

    Parameters
    ----------
    shape : int or sequence of ints
        Shape of the new array, e.g., ``(2, 3)`` or ``2``.
    fill_value : scalar or array_like
        Fill value.
    dtype : data-type, optional
        The desired data-type for the array  The default, None, means
         ``np.array(fill_value).dtype``.
    order : {'C', 'F'}, optional
        Whether to store multidimensional data in C- or Fortran-contiguous
        (row- or column-wise) order in memory.
    device : str, optional
        The device on which to place the created array. Default: None.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        Array of `fill_value` with the given shape, dtype, and order.

    See Also
    --------
    full_like : Return a new array with shape of input filled with value.
    empty : Return a new uninitialized array.
    ones : Return a new array setting values to one.
    zeros : Return a new array setting values to zero.

    Examples
    --------
    >>> import numpy as np
    >>> np.full((2, 2), np.inf)
    array([[inf, inf],
           [inf, inf]])
    >>> np.full((2, 2), 10)
    array([[10, 10],
           [10, 10]])

    >>> np.full((2, 2), [1, 2])
    array([[1, 2],
           [1, 2]])

    """
    if like is not None:
        return _full_with_like(
            like, shape, fill_value, dtype=dtype, order=order, device=device
        )

    if dtype is None:
        fill_value = asarray(fill_value)
        dtype = fill_value.dtype
    a = empty(shape, dtype, order, device=device)
    multiarray.copyto(a, fill_value, casting='unsafe')
    return a


_full_with_like = array_function_dispatch()(full)


def _full_like_dispatcher(
    a, fill_value, dtype=None, order=None, subok=None, shape=None,
    *, device=None
):
    return (a,)


@array_function_dispatch(_full_like_dispatcher)
def full_like(
    a, fill_value, dtype=None, order='K', subok=True, shape=None,
    *, device=None
):
    """
    Return a full array with the same shape and type as a given array.

    Parameters
    ----------
    a : array_like
        The shape and data-type of `a` define these same attributes of
        the returned array.
    fill_value : array_like
        Fill value.
    dtype : data-type, optional
        Overrides the data type of the result.
    order : {'C', 'F', 'A', or 'K'}, optional
        Overrides the memory layout of the result. 'C' means C-order,
        'F' means F-order, 'A' means 'F' if `a` is Fortran contiguous,
        'C' otherwise. 'K' means match the layout of `a` as closely
        as possible.
    subok : bool, optional.
        If True, then the newly created array will use the sub-class
        type of `a`, otherwise it will be a base-class array. Defaults
        to True.
    shape : int or sequence of ints, optional.
        Overrides the shape of the result. If order='K' and the number of
        dimensions is unchanged, will try to keep order, otherwise,
        order='C' is implied.
    device : str, optional
        The device on which to place the created array. Default: None.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : ndarray
        Array of `fill_value` with the same shape and type as `a`.

    See Also
    --------
    empty_like : Return an empty array with shape and type of input.
    ones_like : Return an array of ones with shape and type of input.
    zeros_like : Return an array of zeros with shape and type of input.
    full : Return a new array of given shape filled with value.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(6, dtype=int)
    >>> np.full_like(x, 1)
    array([1, 1, 1, 1, 1, 1])
    >>> np.full_like(x, 0.1)
    array([0, 0, 0, 0, 0, 0])
    >>> np.full_like(x, 0.1, dtype=np.double)
    array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
    >>> np.full_like(x, np.nan, dtype=np.double)
    array([nan, nan, nan, nan, nan, nan])

    >>> y = np.arange(6, dtype=np.double)
    >>> np.full_like(y, 0.1)
    array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1])

    >>> y = np.zeros([2, 2, 3], dtype=int)
    >>> np.full_like(y, [0, 0, 255])
    array([[[  0,   0, 255],
            [  0,   0, 255]],
           [[  0,   0, 255],
            [  0,   0, 255]]])
    """
    res = empty_like(
        a, dtype=dtype, order=order, subok=subok, shape=shape, device=device
    )
    multiarray.copyto(res, fill_value, casting='unsafe')
    return res


def _count_nonzero_dispatcher(a, axis=None, *, keepdims=None):
    return (a,)


@array_function_dispatch(_count_nonzero_dispatcher)
def count_nonzero(a, axis=None, *, keepdims=False):
    """
    Counts the number of non-zero values in the array ``a``.

    The word "non-zero" is in reference to the Python 2.x
    built-in method ``__nonzero__()`` (renamed ``__bool__()``
    in Python 3.x) of Python objects that tests an object's
    "truthfulness". For example, any number is considered
    truthful if it is nonzero, whereas any string is considered
    truthful if it is not the empty string. Thus, this function
    (recursively) counts how many elements in ``a`` (and in
    sub-arrays thereof) have their ``__nonzero__()`` or ``__bool__()``
    method evaluated to ``True``.

    Parameters
    ----------
    a : array_like
        The array for which to count non-zeros.
    axis : int or tuple, optional
        Axis or tuple of axes along which to count non-zeros.
        Default is None, meaning that non-zeros will be counted
        along a flattened version of ``a``.
    keepdims : bool, optional
        If this is set to True, the axes that are counted are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the input array.

    Returns
    -------
    count : int or array of int
        Number of non-zero values in the array along a given axis.
        Otherwise, the total number of non-zero values in the array
        is returned.

    See Also
    --------
    nonzero : Return the coordinates of all the non-zero values.

    Examples
    --------
    >>> import numpy as np
    >>> np.count_nonzero(np.eye(4))
    4
    >>> a = np.array([[0, 1, 7, 0],
    ...               [3, 0, 2, 19]])
    >>> np.count_nonzero(a)
    5
    >>> np.count_nonzero(a, axis=0)
    array([1, 1, 2, 1])
    >>> np.count_nonzero(a, axis=1)
    array([2, 3])
    >>> np.count_nonzero(a, axis=1, keepdims=True)
    array([[2],
           [3]])
    """
    if axis is None and not keepdims:
        return multiarray.count_nonzero(a)

    a = asanyarray(a)

    # TODO: this works around .astype(bool) not working properly (gh-9847)
    if np.issubdtype(a.dtype, np.character):
        a_bool = a != a.dtype.type()
    else:
        a_bool = a.astype(np.bool, copy=False)

    return a_bool.sum(axis=axis, dtype=np.intp, keepdims=keepdims)


@set_module('numpy')
def isfortran(a):
    """
    Check if the array is Fortran contiguous but *not* C contiguous.

    This function is obsolete. If you only want to check if an array is Fortran
    contiguous use ``a.flags.f_contiguous`` instead.

    Parameters
    ----------
    a : ndarray
        Input array.

    Returns
    -------
    isfortran : bool
        Returns True if the array is Fortran contiguous but *not* C contiguous.


    Examples
    --------

    np.array allows to specify whether the array is written in C-contiguous
    order (last index varies the fastest), or FORTRAN-contiguous order in
    memory (first index varies the fastest).

    >>> import numpy as np
    >>> a = np.array([[1, 2, 3], [4, 5, 6]], order='C')
    >>> a
    array([[1, 2, 3],
           [4, 5, 6]])
    >>> np.isfortran(a)
    False

    >>> b = np.array([[1, 2, 3], [4, 5, 6]], order='F')
    >>> b
    array([[1, 2, 3],
           [4, 5, 6]])
    >>> np.isfortran(b)
    True


    The transpose of a C-ordered array is a FORTRAN-ordered array.

    >>> a = np.array([[1, 2, 3], [4, 5, 6]], order='C')
    >>> a
    array([[1, 2, 3],
           [4, 5, 6]])
    >>> np.isfortran(a)
    False
    >>> b = a.T
    >>> b
    array([[1, 4],
           [2, 5],
           [3, 6]])
    >>> np.isfortran(b)
    True

    C-ordered arrays evaluate as False even if they are also FORTRAN-ordered.

    >>> np.isfortran(np.array([1, 2], order='F'))
    False

    """
    return a.flags.fnc


def _argwhere_dispatcher(a):
    return (a,)


@array_function_dispatch(_argwhere_dispatcher)
def argwhere(a):
    """
    Find the indices of array elements that are non-zero, grouped by element.

    Parameters
    ----------
    a : array_like
        Input data.

    Returns
    -------
    index_array : (N, a.ndim) ndarray
        Indices of elements that are non-zero. Indices are grouped by element.
        This array will have shape ``(N, a.ndim)`` where ``N`` is the number of
        non-zero items.

    See Also
    --------
    where, nonzero

    Notes
    -----
    ``np.argwhere(a)`` is almost the same as ``np.transpose(np.nonzero(a))``,
    but produces a result of the correct shape for a 0D array.

    The output of ``argwhere`` is not suitable for indexing arrays.
    For this purpose use ``nonzero(a)`` instead.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(6).reshape(2,3)
    >>> x
    array([[0, 1, 2],
           [3, 4, 5]])
    >>> np.argwhere(x>1)
    array([[0, 2],
           [1, 0],
           [1, 1],
           [1, 2]])

    """
    # nonzero does not behave well on 0d, so promote to 1d
    if np.ndim(a) == 0:
        a = shape_base.atleast_1d(a)
        # then remove the added dimension
        return argwhere(a)[:, :0]
    return transpose(nonzero(a))


def _flatnonzero_dispatcher(a):
    return (a,)


@array_function_dispatch(_flatnonzero_dispatcher)
def flatnonzero(a):
    """
    Return indices that are non-zero in the flattened version of a.

    This is equivalent to ``np.nonzero(np.ravel(a))[0]``.

    Parameters
    ----------
    a : array_like
        Input data.

    Returns
    -------
    res : ndarray
        Output array, containing the indices of the elements of ``a.ravel()``
        that are non-zero.

    See Also
    --------
    nonzero : Return the indices of the non-zero elements of the input array.
    ravel : Return a 1-D array containing the elements of the input array.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(-2, 3)
    >>> x
    array([-2, -1,  0,  1,  2])
    >>> np.flatnonzero(x)
    array([0, 1, 3, 4])

    Use the indices of the non-zero elements as an index array to extract
    these elements:

    >>> x.ravel()[np.flatnonzero(x)]
    array([-2, -1,  1,  2])

    """
    return np.nonzero(np.ravel(a))[0]


def _correlate_dispatcher(a, v, mode=None):
    return (a, v)


@array_function_dispatch(_correlate_dispatcher)
def correlate(a, v, mode='valid'):
    r"""
    Cross-correlation of two 1-dimensional sequences.

    This function computes the correlation as generally defined in signal
    processing texts [1]_:

    .. math:: c_k = \sum_n a_{n+k} \cdot \overline{v}_n

    with a and v sequences being zero-padded where necessary and
    :math:`\overline v` denoting complex conjugation.

    Parameters
    ----------
    a, v : array_like
        Input sequences.
    mode : {'valid', 'same', 'full'}, optional
        Refer to the `convolve` docstring.  Note that the default
        is 'valid', unlike `convolve`, which uses 'full'.

    Returns
    -------
    out : ndarray
        Discrete cross-correlation of `a` and `v`.

    See Also
    --------
    convolve : Discrete, linear convolution of two one-dimensional sequences.
    scipy.signal.correlate : uses FFT which has superior performance
        on large arrays.

    Notes
    -----
    The definition of correlation above is not unique and sometimes
    correlation may be defined differently. Another common definition is [1]_:

    .. math:: c'_k = \sum_n a_{n} \cdot \overline{v_{n+k}}

    which is related to :math:`c_k` by :math:`c'_k = c_{-k}`.

    `numpy.correlate` may perform slowly in large arrays (i.e. n = 1e5)
    because it does not use the FFT to compute the convolution; in that case,
    `scipy.signal.correlate` might be preferable.

    References
    ----------
    .. [1] Wikipedia, "Cross-correlation",
           https://en.wikipedia.org/wiki/Cross-correlation

    Examples
    --------
    >>> import numpy as np
    >>> np.correlate([1, 2, 3], [0, 1, 0.5])
    array([3.5])
    >>> np.correlate([1, 2, 3], [0, 1, 0.5], "same")
    array([2. ,  3.5,  3. ])
    >>> np.correlate([1, 2, 3], [0, 1, 0.5], "full")
    array([0.5,  2. ,  3.5,  3. ,  0. ])

    Using complex sequences:

    >>> np.correlate([1+1j, 2, 3-1j], [0, 1, 0.5j], 'full')
    array([ 0.5-0.5j,  1.0+0.j ,  1.5-1.5j,  3.0-1.j ,  0.0+0.j ])

    Note that you get the time reversed, complex conjugated result
    (:math:`\overline{c_{-k}}`) when the two input sequences a and v change
    places:

    >>> np.correlate([0, 1, 0.5j], [1+1j, 2, 3-1j], 'full')
    array([ 0.0+0.j ,  3.0+1.j ,  1.5+1.5j,  1.0+0.j ,  0.5+0.5j])

    """
    return multiarray.correlate2(a, v, mode)


def _convolve_dispatcher(a, v, mode=None):
    return (a, v)


@array_function_dispatch(_convolve_dispatcher)
def convolve(a, v, mode='full'):
    """
    Returns the discrete, linear convolution of two one-dimensional sequences.

    The convolution operator is often seen in signal processing, where it
    models the effect of a linear time-invariant system on a signal [1]_.  In
    probability theory, the sum of two independent random variables is
    distributed according to the convolution of their individual
    distributions.

    If `v` is longer than `a`, the arrays are swapped before computation.

    Parameters
    ----------
    a : (N,) array_like
        First one-dimensional input array.
    v : (M,) array_like
        Second one-dimensional input array.
    mode : {'full', 'valid', 'same'}, optional
        'full':
          By default, mode is 'full'.  This returns the convolution
          at each point of overlap, with an output shape of (N+M-1,). At
          the end-points of the convolution, the signals do not overlap
          completely, and boundary effects may be seen.

        'same':
          Mode 'same' returns output of length ``max(M, N)``.  Boundary
          effects are still visible.

        'valid':
          Mode 'valid' returns output of length
          ``max(M, N) - min(M, N) + 1``.  The convolution product is only given
          for points where the signals overlap completely.  Values outside
          the signal boundary have no effect.

    Returns
    -------
    out : ndarray
        Discrete, linear convolution of `a` and `v`.

    See Also
    --------
    scipy.signal.fftconvolve : Convolve two arrays using the Fast Fourier
                               Transform.
    scipy.linalg.toeplitz : Used to construct the convolution operator.
    polymul : Polynomial multiplication. Same output as convolve, but also
              accepts poly1d objects as input.

    Notes
    -----
    The discrete convolution operation is defined as

    .. math:: (a * v)_n = \\sum_{m = -\\infty}^{\\infty} a_m v_{n - m}

    It can be shown that a convolution :math:`x(t) * y(t)` in time/space
    is equivalent to the multiplication :math:`X(f) Y(f)` in the Fourier
    domain, after appropriate padding (padding is necessary to prevent
    circular convolution).  Since multiplication is more efficient (faster)
    than convolution, the function `scipy.signal.fftconvolve` exploits the
    FFT to calculate the convolution of large data-sets.

    References
    ----------
    .. [1] Wikipedia, "Convolution",
        https://en.wikipedia.org/wiki/Convolution

    Examples
    --------
    Note how the convolution operator flips the second array
    before "sliding" the two across one another:

    >>> import numpy as np
    >>> np.convolve([1, 2, 3], [0, 1, 0.5])
    array([0. , 1. , 2.5, 4. , 1.5])

    Only return the middle values of the convolution.
    Contains boundary effects, where zeros are taken
    into account:

    >>> np.convolve([1,2,3],[0,1,0.5], 'same')
    array([1. ,  2.5,  4. ])

    The two arrays are of the same length, so there
    is only one position where they completely overlap:

    >>> np.convolve([1,2,3],[0,1,0.5], 'valid')
    array([2.5])

    """
    a, v = array(a, copy=None, ndmin=1), array(v, copy=None, ndmin=1)
    if (len(v) > len(a)):
        a, v = v, a
    if len(a) == 0:
        raise ValueError('a cannot be empty')
    if len(v) == 0:
        raise ValueError('v cannot be empty')
    return multiarray.correlate(a, v[::-1], mode)


def _outer_dispatcher(a, b, out=None):
    return (a, b, out)


@array_function_dispatch(_outer_dispatcher)
def outer(a, b, out=None):
    """
    Compute the outer product of two vectors.

    Given two vectors `a` and `b` of length ``M`` and ``N``, respectively,
    the outer product [1]_ is::

      [[a_0*b_0  a_0*b_1 ... a_0*b_{N-1} ]
       [a_1*b_0    .
       [ ...          .
       [a_{M-1}*b_0            a_{M-1}*b_{N-1} ]]

    Parameters
    ----------
    a : (M,) array_like
        First input vector.  Input is flattened if
        not already 1-dimensional.
    b : (N,) array_like
        Second input vector.  Input is flattened if
        not already 1-dimensional.
    out : (M, N) ndarray, optional
        A location where the result is stored

    Returns
    -------
    out : (M, N) ndarray
        ``out[i, j] = a[i] * b[j]``

    See also
    --------
    inner
    einsum : ``einsum('i,j->ij', a.ravel(), b.ravel())`` is the equivalent.
    ufunc.outer : A generalization to dimensions other than 1D and other
                  operations. ``np.multiply.outer(a.ravel(), b.ravel())``
                  is the equivalent.
    linalg.outer : An Array API compatible variation of ``np.outer``,
                   which accepts 1-dimensional inputs only.
    tensordot : ``np.tensordot(a.ravel(), b.ravel(), axes=((), ()))``
                is the equivalent.

    References
    ----------
    .. [1] G. H. Golub and C. F. Van Loan, *Matrix Computations*, 3rd
           ed., Baltimore, MD, Johns Hopkins University Press, 1996,
           pg. 8.

    Examples
    --------
    Make a (*very* coarse) grid for computing a Mandelbrot set:

    >>> import numpy as np
    >>> rl = np.outer(np.ones((5,)), np.linspace(-2, 2, 5))
    >>> rl
    array([[-2., -1.,  0.,  1.,  2.],
           [-2., -1.,  0.,  1.,  2.],
           [-2., -1.,  0.,  1.,  2.],
           [-2., -1.,  0.,  1.,  2.],
           [-2., -1.,  0.,  1.,  2.]])
    >>> im = np.outer(1j*np.linspace(2, -2, 5), np.ones((5,)))
    >>> im
    array([[0.+2.j, 0.+2.j, 0.+2.j, 0.+2.j, 0.+2.j],
           [0.+1.j, 0.+1.j, 0.+1.j, 0.+1.j, 0.+1.j],
           [0.+0.j, 0.+0.j, 0.+0.j, 0.+0.j, 0.+0.j],
           [0.-1.j, 0.-1.j, 0.-1.j, 0.-1.j, 0.-1.j],
           [0.-2.j, 0.-2.j, 0.-2.j, 0.-2.j, 0.-2.j]])
    >>> grid = rl + im
    >>> grid
    array([[-2.+2.j, -1.+2.j,  0.+2.j,  1.+2.j,  2.+2.j],
           [-2.+1.j, -1.+1.j,  0.+1.j,  1.+1.j,  2.+1.j],
           [-2.+0.j, -1.+0.j,  0.+0.j,  1.+0.j,  2.+0.j],
           [-2.-1.j, -1.-1.j,  0.-1.j,  1.-1.j,  2.-1.j],
           [-2.-2.j, -1.-2.j,  0.-2.j,  1.-2.j,  2.-2.j]])

    An example using a "vector" of letters:

    >>> x = np.array(['a', 'b', 'c'], dtype=object)
    >>> np.outer(x, [1, 2, 3])
    array([['a', 'aa', 'aaa'],
           ['b', 'bb', 'bbb'],
           ['c', 'cc', 'ccc']], dtype=object)

    """
    a = asarray(a)
    b = asarray(b)
    return multiply(a.ravel()[:, newaxis], b.ravel()[newaxis, :], out)


def _tensordot_dispatcher(a, b, axes=None):
    return (a, b)


@array_function_dispatch(_tensordot_dispatcher)
def tensordot(a, b, axes=2):
    """
    Compute tensor dot product along specified axes.

    Given two tensors, `a` and `b`, and an array_like object containing
    two array_like objects, ``(a_axes, b_axes)``, sum the products of
    `a`'s and `b`'s elements (components) over the axes specified by
    ``a_axes`` and ``b_axes``. The third argument can be a single non-negative
    integer_like scalar, ``N``; if it is such, then the last ``N`` dimensions
    of `a` and the first ``N`` dimensions of `b` are summed over.

    Parameters
    ----------
    a, b : array_like
        Tensors to "dot".

    axes : int or (2,) array_like
        * integer_like
          If an int N, sum over the last N axes of `a` and the first N axes
          of `b` in order. The sizes of the corresponding axes must match.
        * (2,) array_like
          Or, a list of axes to be summed over, first sequence applying to `a`,
          second to `b`. Both elements array_like must be of the same length.

    Returns
    -------
    output : ndarray
        The tensor dot product of the input.

    See Also
    --------
    dot, einsum

    Notes
    -----
    Three common use cases are:
        * ``axes = 0`` : tensor product :math:`a\\otimes b`
        * ``axes = 1`` : tensor dot product :math:`a\\cdot b`
        * ``axes = 2`` : (default) tensor double contraction :math:`a:b`

    When `axes` is integer_like, the sequence of axes for evaluation
    will be: from the -Nth axis to the -1th axis in `a`,
    and from the 0th axis to (N-1)th axis in `b`.
    For example, ``axes = 2`` is the equal to
    ``axes = [[-2, -1], [0, 1]]``.
    When N-1 is smaller than 0, or when -N is larger than -1,
    the element of `a` and `b` are defined as the `axes`.

    When there is more than one axis to sum over - and they are not the last
    (first) axes of `a` (`b`) - the argument `axes` should consist of
    two sequences of the same length, with the first axis to sum over given
    first in both sequences, the second axis second, and so forth.
    The calculation can be referred to ``numpy.einsum``.

    The shape of the result consists of the non-contracted axes of the
    first tensor, followed by the non-contracted axes of the second.

    Examples
    --------
    An example on integer_like:

    >>> a_0 = np.array([[1, 2], [3, 4]])
    >>> b_0 = np.array([[5, 6], [7, 8]])
    >>> c_0 = np.tensordot(a_0, b_0, axes=0)
    >>> c_0.shape
    (2, 2, 2, 2)
    >>> c_0
    array([[[[ 5,  6],
             [ 7,  8]],
            [[10, 12],
             [14, 16]]],
           [[[15, 18],
             [21, 24]],
            [[20, 24],
             [28, 32]]]])

    An example on array_like:

    >>> a = np.arange(60.).reshape(3,4,5)
    >>> b = np.arange(24.).reshape(4,3,2)
    >>> c = np.tensordot(a,b, axes=([1,0],[0,1]))
    >>> c.shape
    (5, 2)
    >>> c
    array([[4400., 4730.],
           [4532., 4874.],
           [4664., 5018.],
           [4796., 5162.],
           [4928., 5306.]])

    A slower but equivalent way of computing the same...

    >>> d = np.zeros((5,2))
    >>> for i in range(5):
    ...   for j in range(2):
    ...     for k in range(3):
    ...       for n in range(4):
    ...         d[i,j] += a[k,n,i] * b[n,k,j]
    >>> c == d
    array([[ True,  True],
           [ True,  True],
           [ True,  True],
           [ True,  True],
           [ True,  True]])

    An extended example taking advantage of the overloading of + and \\*:

    >>> a = np.array(range(1, 9))
    >>> a.shape = (2, 2, 2)
    >>> A = np.array(('a', 'b', 'c', 'd'), dtype=object)
    >>> A.shape = (2, 2)
    >>> a; A
    array([[[1, 2],
            [3, 4]],
           [[5, 6],
            [7, 8]]])
    array([['a', 'b'],
           ['c', 'd']], dtype=object)

    >>> np.tensordot(a, A) # third argument default is 2 for double-contraction
    array(['abbcccdddd', 'aaaaabbbbbbcccccccdddddddd'], dtype=object)

    >>> np.tensordot(a, A, 1)
    array([[['acc', 'bdd'],
            ['aaacccc', 'bbbdddd']],
           [['aaaaacccccc', 'bbbbbdddddd'],
            ['aaaaaaacccccccc', 'bbbbbbbdddddddd']]], dtype=object)

    >>> np.tensordot(a, A, 0) # tensor product (result too long to incl.)
    array([[[[['a', 'b'],
              ['c', 'd']],
              ...

    >>> np.tensordot(a, A, (0, 1))
    array([[['abbbbb', 'cddddd'],
            ['aabbbbbb', 'ccdddddd']],
           [['aaabbbbbbb', 'cccddddddd'],
            ['aaaabbbbbbbb', 'ccccdddddddd']]], dtype=object)

    >>> np.tensordot(a, A, (2, 1))
    array([[['abb', 'cdd'],
            ['aaabbbb', 'cccdddd']],
           [['aaaaabbbbbb', 'cccccdddddd'],
            ['aaaaaaabbbbbbbb', 'cccccccdddddddd']]], dtype=object)

    >>> np.tensordot(a, A, ((0, 1), (0, 1)))
    array(['abbbcccccddddddd', 'aabbbbccccccdddddddd'], dtype=object)

    >>> np.tensordot(a, A, ((2, 1), (1, 0)))
    array(['acccbbdddd', 'aaaaacccccccbbbbbbdddddddd'], dtype=object)

    """
    try:
        iter(axes)
    except Exception:
        axes_a = list(range(-axes, 0))
        axes_b = list(range(axes))
    else:
        axes_a, axes_b = axes
    try:
        na = len(axes_a)
        axes_a = list(axes_a)
    except TypeError:
        axes_a = [axes_a]
        na = 1
    try:
        nb = len(axes_b)
        axes_b = list(axes_b)
    except TypeError:
        axes_b = [axes_b]
        nb = 1

    a, b = asarray(a), asarray(b)
    as_ = a.shape
    nda = a.ndim
    bs = b.shape
    ndb = b.ndim
    equal = True
    if na != nb:
        equal = False
    else:
        for k in range(na):
            if as_[axes_a[k]] != bs[axes_b[k]]:
                equal = False
                break
            if axes_a[k] < 0:
                axes_a[k] += nda
            if axes_b[k] < 0:
                axes_b[k] += ndb
    if not equal:
        raise ValueError("shape-mismatch for sum")

    # Move the axes to sum over to the end of "a"
    # and to the front of "b"
    notin = [k for k in range(nda) if k not in axes_a]
    newaxes_a = notin + axes_a
    N2 = math.prod(as_[axis] for axis in axes_a)
    newshape_a = (math.prod(as_[ax] for ax in notin), N2)
    olda = [as_[axis] for axis in notin]

    notin = [k for k in range(ndb) if k not in axes_b]
    newaxes_b = axes_b + notin
    N2 = math.prod(bs[axis] for axis in axes_b)
    newshape_b = (N2, math.prod(bs[ax] for ax in notin))
    oldb = [bs[axis] for axis in notin]

    at = a.transpose(newaxes_a).reshape(newshape_a)
    bt = b.transpose(newaxes_b).reshape(newshape_b)
    res = dot(at, bt)
    return res.reshape(olda + oldb)


def _roll_dispatcher(a, shift, axis=None):
    return (a,)


@array_function_dispatch(_roll_dispatcher)
def roll(a, shift, axis=None):
    """
    Roll array elements along a given axis.

    Elements that roll beyond the last position are re-introduced at
    the first.

    Parameters
    ----------
    a : array_like
        Input array.
    shift : int or tuple of ints
        The number of places by which elements are shifted.  If a tuple,
        then `axis` must be a tuple of the same size, and each of the
        given axes is shifted by the corresponding number.  If an int
        while `axis` is a tuple of ints, then the same value is used for
        all given axes.
    axis : int or tuple of ints, optional
        Axis or axes along which elements are shifted.  By default, the
        array is flattened before shifting, after which the original
        shape is restored.

    Returns
    -------
    res : ndarray
        Output array, with the same shape as `a`.

    See Also
    --------
    rollaxis : Roll the specified axis backwards, until it lies in a
               given position.

    Notes
    -----
    Supports rolling over multiple dimensions simultaneously.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(10)
    >>> np.roll(x, 2)
    array([8, 9, 0, 1, 2, 3, 4, 5, 6, 7])
    >>> np.roll(x, -2)
    array([2, 3, 4, 5, 6, 7, 8, 9, 0, 1])

    >>> x2 = np.reshape(x, (2, 5))
    >>> x2
    array([[0, 1, 2, 3, 4],
           [5, 6, 7, 8, 9]])
    >>> np.roll(x2, 1)
    array([[9, 0, 1, 2, 3],
           [4, 5, 6, 7, 8]])
    >>> np.roll(x2, -1)
    array([[1, 2, 3, 4, 5],
           [6, 7, 8, 9, 0]])
    >>> np.roll(x2, 1, axis=0)
    array([[5, 6, 7, 8, 9],
           [0, 1, 2, 3, 4]])
    >>> np.roll(x2, -1, axis=0)
    array([[5, 6, 7, 8, 9],
           [0, 1, 2, 3, 4]])
    >>> np.roll(x2, 1, axis=1)
    array([[4, 0, 1, 2, 3],
           [9, 5, 6, 7, 8]])
    >>> np.roll(x2, -1, axis=1)
    array([[1, 2, 3, 4, 0],
           [6, 7, 8, 9, 5]])
    >>> np.roll(x2, (1, 1), axis=(1, 0))
    array([[9, 5, 6, 7, 8],
           [4, 0, 1, 2, 3]])
    >>> np.roll(x2, (2, 1), axis=(1, 0))
    array([[8, 9, 5, 6, 7],
           [3, 4, 0, 1, 2]])

    """
    a = asanyarray(a)
    if axis is None:
        return roll(a.ravel(), shift, 0).reshape(a.shape)

    else:
        axis = normalize_axis_tuple(axis, a.ndim, allow_duplicate=True)
        broadcasted = broadcast(shift, axis)
        if broadcasted.ndim > 1:
            raise ValueError(
                "'shift' and 'axis' should be scalars or 1D sequences")
        shifts = dict.fromkeys(range(a.ndim), 0)
        for sh, ax in broadcasted:
            shifts[ax] += int(sh)

        rolls = [((slice(None), slice(None)),)] * a.ndim
        for ax, offset in shifts.items():
            offset %= a.shape[ax] or 1  # If `a` is empty, nothing matters.
            if offset:
                # (original, result), (original, result)
                rolls[ax] = ((slice(None, -offset), slice(offset, None)),
                             (slice(-offset, None), slice(None, offset)))

        result = empty_like(a)
        for indices in itertools.product(*rolls):
            arr_index, res_index = zip(*indices)
            result[res_index] = a[arr_index]

        return result


def _rollaxis_dispatcher(a, axis, start=None):
    return (a,)


@array_function_dispatch(_rollaxis_dispatcher)
def rollaxis(a, axis, start=0):
    """
    Roll the specified axis backwards, until it lies in a given position.

    This function continues to be supported for backward compatibility, but you
    should prefer `moveaxis`. The `moveaxis` function was added in NumPy
    1.11.

    Parameters
    ----------
    a : ndarray
        Input array.
    axis : int
        The axis to be rolled. The positions of the other axes do not
        change relative to one another.
    start : int, optional
        When ``start <= axis``, the axis is rolled back until it lies in
        this position. When ``start > axis``, the axis is rolled until it
        lies before this position. The default, 0, results in a "complete"
        roll. The following table describes how negative values of ``start``
        are interpreted:

        .. table::
           :align: left

           +-------------------+----------------------+
           |     ``start``     | Normalized ``start`` |
           +===================+======================+
           | ``-(arr.ndim+1)`` | raise ``AxisError``  |
           +-------------------+----------------------+
           | ``-arr.ndim``     | 0                    |
           +-------------------+----------------------+
           | |vdots|           | |vdots|              |
           +-------------------+----------------------+
           | ``-1``            | ``arr.ndim-1``       |
           +-------------------+----------------------+
           | ``0``             | ``0``                |
           +-------------------+----------------------+
           | |vdots|           | |vdots|              |
           +-------------------+----------------------+
           | ``arr.ndim``      | ``arr.ndim``         |
           +-------------------+----------------------+
           | ``arr.ndim + 1``  | raise ``AxisError``  |
           +-------------------+----------------------+

        .. |vdots|   unicode:: U+22EE .. Vertical Ellipsis

    Returns
    -------
    res : ndarray
        For NumPy >= 1.10.0 a view of `a` is always returned. For earlier
        NumPy versions a view of `a` is returned only if the order of the
        axes is changed, otherwise the input array is returned.

    See Also
    --------
    moveaxis : Move array axes to new positions.
    roll : Roll the elements of an array by a number of positions along a
        given axis.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.ones((3,4,5,6))
    >>> np.rollaxis(a, 3, 1).shape
    (3, 6, 4, 5)
    >>> np.rollaxis(a, 2).shape
    (5, 3, 4, 6)
    >>> np.rollaxis(a, 1, 4).shape
    (3, 5, 6, 4)

    """
    n = a.ndim
    axis = normalize_axis_index(axis, n)
    if start < 0:
        start += n
    msg = "'%s' arg requires %d <= %s < %d, but %d was passed in"
    if not (0 <= start < n + 1):
        raise AxisError(msg % ('start', -n, 'start', n + 1, start))
    if axis < start:
        # it's been removed
        start -= 1
    if axis == start:
        return a[...]
    axes = list(range(n))
    axes.remove(axis)
    axes.insert(start, axis)
    return a.transpose(axes)


@set_module("numpy.lib.array_utils")
def normalize_axis_tuple(axis, ndim, argname=None, allow_duplicate=False):
    """
    Normalizes an axis argument into a tuple of non-negative integer axes.

    This handles shorthands such as ``1`` and converts them to ``(1,)``,
    as well as performing the handling of negative indices covered by
    `normalize_axis_index`.

    By default, this forbids axes from being specified multiple times.

    Used internally by multi-axis-checking logic.

    Parameters
    ----------
    axis : int, iterable of int
        The un-normalized index or indices of the axis.
    ndim : int
        The number of dimensions of the array that `axis` should be normalized
        against.
    argname : str, optional
        A prefix to put before the error message, typically the name of the
        argument.
    allow_duplicate : bool, optional
        If False, the default, disallow an axis from being specified twice.

    Returns
    -------
    normalized_axes : tuple of int
        The normalized axis index, such that `0 <= normalized_axis < ndim`

    Raises
    ------
    AxisError
        If any axis provided is out of range
    ValueError
        If an axis is repeated

    See also
    --------
    normalize_axis_index : normalizing a single scalar axis
    """
    # Optimization to speed-up the most common cases.
    if not isinstance(axis, (tuple, list)):
        try:
            axis = [operator.index(axis)]
        except TypeError:
            pass
    # Going via an iterator directly is slower than via list comprehension.
    axis = tuple(normalize_axis_index(ax, ndim, argname) for ax in axis)
    if not allow_duplicate and len(set(axis)) != len(axis):
        if argname:
            raise ValueError(f'repeated axis in `{argname}` argument')
        else:
            raise ValueError('repeated axis')
    return axis


def _moveaxis_dispatcher(a, source, destination):
    return (a,)


@array_function_dispatch(_moveaxis_dispatcher)
def moveaxis(a, source, destination):
    """
    Move axes of an array to new positions.

    Other axes remain in their original order.

    Parameters
    ----------
    a : np.ndarray
        The array whose axes should be reordered.
    source : int or sequence of int
        Original positions of the axes to move. These must be unique.
    destination : int or sequence of int
        Destination positions for each of the original axes. These must also be
        unique.

    Returns
    -------
    result : np.ndarray
        Array with moved axes. This array is a view of the input array.

    See Also
    --------
    transpose : Permute the dimensions of an array.
    swapaxes : Interchange two axes of an array.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.zeros((3, 4, 5))
    >>> np.moveaxis(x, 0, -1).shape
    (4, 5, 3)
    >>> np.moveaxis(x, -1, 0).shape
    (5, 3, 4)

    These all achieve the same result:

    >>> np.transpose(x).shape
    (5, 4, 3)
    >>> np.swapaxes(x, 0, -1).shape
    (5, 4, 3)
    >>> np.moveaxis(x, [0, 1], [-1, -2]).shape
    (5, 4, 3)
    >>> np.moveaxis(x, [0, 1, 2], [-1, -2, -3]).shape
    (5, 4, 3)

    """
    try:
        # allow duck-array types if they define transpose
        transpose = a.transpose
    except AttributeError:
        a = asarray(a)
        transpose = a.transpose

    source = normalize_axis_tuple(source, a.ndim, 'source')
    destination = normalize_axis_tuple(destination, a.ndim, 'destination')
    if len(source) != len(destination):
        raise ValueError('`source` and `destination` arguments must have '
                         'the same number of elements')

    order = [n for n in range(a.ndim) if n not in source]

    for dest, src in sorted(zip(destination, source)):
        order.insert(dest, src)

    result = transpose(order)
    return result


def _cross_dispatcher(a, b, axisa=None, axisb=None, axisc=None, axis=None):
    return (a, b)


@array_function_dispatch(_cross_dispatcher)
def cross(a, b, axisa=-1, axisb=-1, axisc=-1, axis=None):
    """
    Return the cross product of two (arrays of) vectors.

    The cross product of `a` and `b` in :math:`R^3` is a vector perpendicular
    to both `a` and `b`.  If `a` and `b` are arrays of vectors, the vectors
    are defined by the last axis of `a` and `b` by default, and these axes
    can have dimensions 2 or 3.  Where the dimension of either `a` or `b` is
    2, the third component of the input vector is assumed to be zero and the
    cross product calculated accordingly.  In cases where both input vectors
    have dimension 2, the z-component of the cross product is returned.

    Parameters
    ----------
    a : array_like
        Components of the first vector(s).
    b : array_like
        Components of the second vector(s).
    axisa : int, optional
        Axis of `a` that defines the vector(s).  By default, the last axis.
    axisb : int, optional
        Axis of `b` that defines the vector(s).  By default, the last axis.
    axisc : int, optional
        Axis of `c` containing the cross product vector(s).  Ignored if
        both input vectors have dimension 2, as the return is scalar.
        By default, the last axis.
    axis : int, optional
        If defined, the axis of `a`, `b` and `c` that defines the vector(s)
        and cross product(s).  Overrides `axisa`, `axisb` and `axisc`.

    Returns
    -------
    c : ndarray
        Vector cross product(s).

    Raises
    ------
    ValueError
        When the dimension of the vector(s) in `a` and/or `b` does not
        equal 2 or 3.

    See Also
    --------
    inner : Inner product
    outer : Outer product.
    linalg.cross : An Array API compatible variation of ``np.cross``,
                   which accepts (arrays of) 3-element vectors only.
    ix_ : Construct index arrays.

    Notes
    -----
    Supports full broadcasting of the inputs.

    Dimension-2 input arrays were deprecated in 2.0.0. If you do need this
    functionality, you can use::

        def cross2d(x, y):
            return x[..., 0] * y[..., 1] - x[..., 1] * y[..., 0]

    Examples
    --------
    Vector cross-product.

    >>> import numpy as np
    >>> x = [1, 2, 3]
    >>> y = [4, 5, 6]
    >>> np.cross(x, y)
    array([-3,  6, -3])

    One vector with dimension 2.

    >>> x = [1, 2]
    >>> y = [4, 5, 6]
    >>> np.cross(x, y)
    array([12, -6, -3])

    Equivalently:

    >>> x = [1, 2, 0]
    >>> y = [4, 5, 6]
    >>> np.cross(x, y)
    array([12, -6, -3])

    Both vectors with dimension 2.

    >>> x = [1,2]
    >>> y = [4,5]
    >>> np.cross(x, y)
    array(-3)

    Multiple vector cross-products. Note that the direction of the cross
    product vector is defined by the *right-hand rule*.

    >>> x = np.array([[1,2,3], [4,5,6]])
    >>> y = np.array([[4,5,6], [1,2,3]])
    >>> np.cross(x, y)
    array([[-3,  6, -3],
           [ 3, -6,  3]])

    The orientation of `c` can be changed using the `axisc` keyword.

    >>> np.cross(x, y, axisc=0)
    array([[-3,  3],
           [ 6, -6],
           [-3,  3]])

    Change the vector definition of `x` and `y` using `axisa` and `axisb`.

    >>> x = np.array([[1,2,3], [4,5,6], [7, 8, 9]])
    >>> y = np.array([[7, 8, 9], [4,5,6], [1,2,3]])
    >>> np.cross(x, y)
    array([[ -6,  12,  -6],
           [  0,   0,   0],
           [  6, -12,   6]])
    >>> np.cross(x, y, axisa=0, axisb=0)
    array([[-24,  48, -24],
           [-30,  60, -30],
           [-36,  72, -36]])

    """
    if axis is not None:
        axisa, axisb, axisc = (axis,) * 3
    a = asarray(a)
    b = asarray(b)

    if (a.ndim < 1) or (b.ndim < 1):
        raise ValueError("At least one array has zero dimension")

    # Check axisa and axisb are within bounds
    axisa = normalize_axis_index(axisa, a.ndim, msg_prefix='axisa')
    axisb = normalize_axis_index(axisb, b.ndim, msg_prefix='axisb')

    # Move working axis to the end of the shape
    a = moveaxis(a, axisa, -1)
    b = moveaxis(b, axisb, -1)
    msg = ("incompatible dimensions for cross product\n"
           "(dimension must be 2 or 3)")
    if a.shape[-1] not in (2, 3) or b.shape[-1] not in (2, 3):
        raise ValueError(msg)
    if a.shape[-1] == 2 or b.shape[-1] == 2:
        # Deprecated in NumPy 2.0, 2023-09-26
        warnings.warn(
            "Arrays of 2-dimensional vectors are deprecated. Use arrays of "
            "3-dimensional vectors instead. (deprecated in NumPy 2.0)",
            DeprecationWarning, stacklevel=2
        )

    # Create the output array
    shape = broadcast(a[..., 0], b[..., 0]).shape
    if a.shape[-1] == 3 or b.shape[-1] == 3:
        shape += (3,)
        # Check axisc is within bounds
        axisc = normalize_axis_index(axisc, len(shape), msg_prefix='axisc')
    dtype = promote_types(a.dtype, b.dtype)
    cp = empty(shape, dtype)

    # recast arrays as dtype
    a = a.astype(dtype)
    b = b.astype(dtype)

    # create local aliases for readability
    a0 = a[..., 0]
    a1 = a[..., 1]
    if a.shape[-1] == 3:
        a2 = a[..., 2]
    b0 = b[..., 0]
    b1 = b[..., 1]
    if b.shape[-1] == 3:
        b2 = b[..., 2]
    if cp.ndim != 0 and cp.shape[-1] == 3:
        cp0 = cp[..., 0]
        cp1 = cp[..., 1]
        cp2 = cp[..., 2]

    if a.shape[-1] == 2:
        if b.shape[-1] == 2:
            # a0 * b1 - a1 * b0
            multiply(a0, b1, out=cp)
            cp -= a1 * b0
            return cp
        else:
            assert b.shape[-1] == 3
            # cp0 = a1 * b2 - 0  (a2 = 0)
            # cp1 = 0 - a0 * b2  (a2 = 0)
            # cp2 = a0 * b1 - a1 * b0
            multiply(a1, b2, out=cp0)
            multiply(a0, b2, out=cp1)
            negative(cp1, out=cp1)
            multiply(a0, b1, out=cp2)
            cp2 -= a1 * b0
    else:
        assert a.shape[-1] == 3
        if b.shape[-1] == 3:
            # cp0 = a1 * b2 - a2 * b1
            # cp1 = a2 * b0 - a0 * b2
            # cp2 = a0 * b1 - a1 * b0
            multiply(a1, b2, out=cp0)
            tmp = np.multiply(a2, b1, out=...)
            cp0 -= tmp
            multiply(a2, b0, out=cp1)
            multiply(a0, b2, out=tmp)
            cp1 -= tmp
            multiply(a0, b1, out=cp2)
            multiply(a1, b0, out=tmp)
            cp2 -= tmp
        else:
            assert b.shape[-1] == 2
            # cp0 = 0 - a2 * b1  (b2 = 0)
            # cp1 = a2 * b0 - 0  (b2 = 0)
            # cp2 = a0 * b1 - a1 * b0
            multiply(a2, b1, out=cp0)
            negative(cp0, out=cp0)
            multiply(a2, b0, out=cp1)
            multiply(a0, b1, out=cp2)
            cp2 -= a1 * b0

    return moveaxis(cp, -1, axisc)


little_endian = (sys.byteorder == 'little')


@set_module('numpy')
def indices(dimensions, dtype=int, sparse=False):
    """
    Return an array representing the indices of a grid.

    Compute an array where the subarrays contain index values 0, 1, ...
    varying only along the corresponding axis.

    Parameters
    ----------
    dimensions : sequence of ints
        The shape of the grid.
    dtype : dtype, optional
        Data type of the result.
    sparse : boolean, optional
        Return a sparse representation of the grid instead of a dense
        representation. Default is False.

    Returns
    -------
    grid : one ndarray or tuple of ndarrays
        If sparse is False:
            Returns one array of grid indices,
            ``grid.shape = (len(dimensions),) + tuple(dimensions)``.
        If sparse is True:
            Returns a tuple of arrays, with
            ``grid[i].shape = (1, ..., 1, dimensions[i], 1, ..., 1)`` with
            dimensions[i] in the ith place

    See Also
    --------
    mgrid, ogrid, meshgrid

    Notes
    -----
    The output shape in the dense case is obtained by prepending the number
    of dimensions in front of the tuple of dimensions, i.e. if `dimensions`
    is a tuple ``(r0, ..., rN-1)`` of length ``N``, the output shape is
    ``(N, r0, ..., rN-1)``.

    The subarrays ``grid[k]`` contains the N-D array of indices along the
    ``k-th`` axis. Explicitly::

        grid[k, i0, i1, ..., iN-1] = ik

    Examples
    --------
    >>> import numpy as np
    >>> grid = np.indices((2, 3))
    >>> grid.shape
    (2, 2, 3)
    >>> grid[0]        # row indices
    array([[0, 0, 0],
           [1, 1, 1]])
    >>> grid[1]        # column indices
    array([[0, 1, 2],
           [0, 1, 2]])

    The indices can be used as an index into an array.

    >>> x = np.arange(20).reshape(5, 4)
    >>> row, col = np.indices((2, 3))
    >>> x[row, col]
    array([[0, 1, 2],
           [4, 5, 6]])

    Note that it would be more straightforward in the above example to
    extract the required elements directly with ``x[:2, :3]``.

    If sparse is set to true, the grid will be returned in a sparse
    representation.

    >>> i, j = np.indices((2, 3), sparse=True)
    >>> i.shape
    (2, 1)
    >>> j.shape
    (1, 3)
    >>> i        # row indices
    array([[0],
           [1]])
    >>> j        # column indices
    array([[0, 1, 2]])

    """
    dimensions = tuple(dimensions)
    N = len(dimensions)
    shape = (1,) * N
    if sparse:
        res = ()
    else:
        res = empty((N,) + dimensions, dtype=dtype)
    for i, dim in enumerate(dimensions):
        idx = arange(dim, dtype=dtype).reshape(
            shape[:i] + (dim,) + shape[i + 1:]
        )
        if sparse:
            res = res + (idx,)
        else:
            res[i] = idx
    return res


@finalize_array_function_like
@set_module('numpy')
def fromfunction(function, shape, *, dtype=float, like=None, **kwargs):
    """
    Construct an array by executing a function over each coordinate.

    The resulting array therefore has a value ``fn(x, y, z)`` at
    coordinate ``(x, y, z)``.

    Parameters
    ----------
    function : callable
        The function is called with N parameters, where N is the rank of
        `shape`.  Each parameter represents the coordinates of the array
        varying along a specific axis.  For example, if `shape`
        were ``(2, 2)``, then the parameters would be
        ``array([[0, 0], [1, 1]])`` and ``array([[0, 1], [0, 1]])``
    shape : (N,) tuple of ints
        Shape of the output array, which also determines the shape of
        the coordinate arrays passed to `function`.
    dtype : data-type, optional
        Data-type of the coordinate arrays passed to `function`.
        By default, `dtype` is float.
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    fromfunction : any
        The result of the call to `function` is passed back directly.
        Therefore the shape of `fromfunction` is completely determined by
        `function`.  If `function` returns a scalar value, the shape of
        `fromfunction` would not match the `shape` parameter.

    See Also
    --------
    indices, meshgrid

    Notes
    -----
    Keywords other than `dtype` and `like` are passed to `function`.

    Examples
    --------
    >>> import numpy as np
    >>> np.fromfunction(lambda i, j: i, (2, 2), dtype=float)
    array([[0., 0.],
           [1., 1.]])

    >>> np.fromfunction(lambda i, j: j, (2, 2), dtype=float)
    array([[0., 1.],
           [0., 1.]])

    >>> np.fromfunction(lambda i, j: i == j, (3, 3), dtype=int)
    array([[ True, False, False],
           [False,  True, False],
           [False, False,  True]])

    >>> np.fromfunction(lambda i, j: i + j, (3, 3), dtype=int)
    array([[0, 1, 2],
           [1, 2, 3],
           [2, 3, 4]])

    """
    if like is not None:
        return _fromfunction_with_like(
                like, function, shape, dtype=dtype, **kwargs)

    args = indices(shape, dtype=dtype)
    return function(*args, **kwargs)


_fromfunction_with_like = array_function_dispatch()(fromfunction)


def _frombuffer(buf, dtype, shape, order, axis_order=None):
    array = frombuffer(buf, dtype=dtype)
    if order == 'K' and axis_order is not None:
        return array.reshape(shape, order='C').transpose(axis_order)
    return array.reshape(shape, order=order)


@set_module('numpy')
def isscalar(element):
    """
    Returns True if the type of `element` is a scalar type.

    Parameters
    ----------
    element : any
        Input argument, can be of any type and shape.

    Returns
    -------
    val : bool
        True if `element` is a scalar type, False if it is not.

    See Also
    --------
    ndim : Get the number of dimensions of an array

    Notes
    -----
    If you need a stricter way to identify a *numerical* scalar, use
    ``isinstance(x, numbers.Number)``, as that returns ``False`` for most
    non-numerical elements such as strings.

    In most cases ``np.ndim(x) == 0`` should be used instead of this function,
    as that will also return true for 0d arrays. This is how numpy overloads
    functions in the style of the ``dx`` arguments to `gradient` and
    the ``bins`` argument to `histogram`. Some key differences:

    +------------------------------------+---------------+-------------------+
    | x                                  |``isscalar(x)``|``np.ndim(x) == 0``|
    +====================================+===============+===================+
    | PEP 3141 numeric objects           | ``True``      | ``True``          |
    | (including builtins)               |               |                   |
    +------------------------------------+---------------+-------------------+
    | builtin string and buffer objects  | ``True``      | ``True``          |
    +------------------------------------+---------------+-------------------+
    | other builtin objects, like        | ``False``     | ``True``          |
    | `pathlib.Path`, `Exception`,       |               |                   |
    | the result of `re.compile`         |               |                   |
    +------------------------------------+---------------+-------------------+
    | third-party objects like           | ``False``     | ``True``          |
    | `matplotlib.figure.Figure`         |               |                   |
    +------------------------------------+---------------+-------------------+
    | zero-dimensional numpy arrays      | ``False``     | ``True``          |
    +------------------------------------+---------------+-------------------+
    | other numpy arrays                 | ``False``     | ``False``         |
    +------------------------------------+---------------+-------------------+
    | `list`, `tuple`, and other         | ``False``     | ``False``         |
    | sequence objects                   |               |                   |
    +------------------------------------+---------------+-------------------+

    Examples
    --------
    >>> import numpy as np

    >>> np.isscalar(3.1)
    True

    >>> np.isscalar(np.array(3.1))
    False

    >>> np.isscalar([3.1])
    False

    >>> np.isscalar(False)
    True

    >>> np.isscalar('numpy')
    True

    NumPy supports PEP 3141 numbers:

    >>> from fractions import Fraction
    >>> np.isscalar(Fraction(5, 17))
    True
    >>> from numbers import Number
    >>> np.isscalar(Number())
    True

    """
    return (isinstance(element, generic)
            or type(element) in ScalarType
            or isinstance(element, numbers.Number))


@set_module('numpy')
def binary_repr(num, width=None):
    """
    Return the binary representation of the input number as a string.

    For negative numbers, if width is not given, a minus sign is added to the
    front. If width is given, the two's complement of the number is
    returned, with respect to that width.

    In a two's-complement system negative numbers are represented by the two's
    complement of the absolute value. This is the most common method of
    representing signed integers on computers [1]_. A N-bit two's-complement
    system can represent every integer in the range
    :math:`-2^{N-1}` to :math:`+2^{N-1}-1`.

    Parameters
    ----------
    num : int
        Only an integer decimal number can be used.
    width : int, optional
        The length of the returned string if `num` is positive, or the length
        of the two's complement if `num` is negative, provided that `width` is
        at least a sufficient number of bits for `num` to be represented in
        the designated form. If the `width` value is insufficient, an error is
        raised.

    Returns
    -------
    bin : str
        Binary representation of `num` or two's complement of `num`.

    See Also
    --------
    base_repr: Return a string representation of a number in the given base
               system.
    bin: Python's built-in binary representation generator of an integer.

    Notes
    -----
    `binary_repr` is equivalent to using `base_repr` with base 2, but about 25x
    faster.

    References
    ----------
    .. [1] Wikipedia, "Two's complement",
        https://en.wikipedia.org/wiki/Two's_complement

    Examples
    --------
    >>> import numpy as np
    >>> np.binary_repr(3)
    '11'
    >>> np.binary_repr(-3)
    '-11'
    >>> np.binary_repr(3, width=4)
    '0011'

    The two's complement is returned when the input number is negative and
    width is specified:

    >>> np.binary_repr(-3, width=3)
    '101'
    >>> np.binary_repr(-3, width=5)
    '11101'

    """
    def err_if_insufficient(width, binwidth):
        if width is not None and width < binwidth:
            raise ValueError(
                f"Insufficient bit {width=} provided for {binwidth=}"
            )

    # Ensure that num is a Python integer to avoid overflow or unwanted
    # casts to floating point.
    num = operator.index(num)

    if num == 0:
        return '0' * (width or 1)

    elif num > 0:
        binary = f'{num:b}'
        binwidth = len(binary)
        outwidth = (binwidth if width is None
                    else builtins.max(binwidth, width))
        err_if_insufficient(width, binwidth)
        return binary.zfill(outwidth)

    elif width is None:
        return f'-{-num:b}'

    else:
        poswidth = len(f'{-num:b}')

        # See gh-8679: remove extra digit
        # for numbers at boundaries.
        if 2**(poswidth - 1) == -num:
            poswidth -= 1

        twocomp = 2**(poswidth + 1) + num
        binary = f'{twocomp:b}'
        binwidth = len(binary)

        outwidth = builtins.max(binwidth, width)
        err_if_insufficient(width, binwidth)
        return '1' * (outwidth - binwidth) + binary


@set_module('numpy')
def base_repr(number, base=2, padding=0):
    """
    Return a string representation of a number in the given base system.

    Parameters
    ----------
    number : int
        The value to convert. Positive and negative values are handled.
    base : int, optional
        Convert `number` to the `base` number system. The valid range is 2-36,
        the default value is 2.
    padding : int, optional
        Number of zeros padded on the left. Default is 0 (no padding).

    Returns
    -------
    out : str
        String representation of `number` in `base` system.

    See Also
    --------
    binary_repr : Faster version of `base_repr` for base 2.

    Examples
    --------
    >>> import numpy as np
    >>> np.base_repr(5)
    '101'
    >>> np.base_repr(6, 5)
    '11'
    >>> np.base_repr(7, base=5, padding=3)
    '00012'

    >>> np.base_repr(10, base=16)
    'A'
    >>> np.base_repr(32, base=16)
    '20'

    """
    digits = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if base > len(digits):
        raise ValueError("Bases greater than 36 not handled in base_repr.")
    elif base < 2:
        raise ValueError("Bases less than 2 not handled in base_repr.")

    num = abs(int(number))
    res = []
    while num:
        res.append(digits[num % base])
        num //= base
    if padding:
        res.append('0' * padding)
    if number < 0:
        res.append('-')
    return ''.join(reversed(res or '0'))


# These are all essentially abbreviations
# These might wind up in a special abbreviations module


def _maketup(descr, val):
    dt = dtype(descr)
    # Place val in all scalar tuples:
    fields = dt.fields
    if fields is None:
        return val
    else:
        res = [_maketup(fields[name][0], val) for name in dt.names]
        return tuple(res)


@finalize_array_function_like
@set_module('numpy')
def identity(n, dtype=None, *, like=None):
    """
    Return the identity array.

    The identity array is a square array with ones on
    the main diagonal.

    Parameters
    ----------
    n : int
        Number of rows (and columns) in `n` x `n` output.
    dtype : data-type, optional
        Data-type of the output.  Defaults to ``float``.
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        `n` x `n` array with its main diagonal set to one,
        and all other elements 0.

    Examples
    --------
    >>> import numpy as np
    >>> np.identity(3)
    array([[1.,  0.,  0.],
           [0.,  1.,  0.],
           [0.,  0.,  1.]])

    """
    if like is not None:
        return _identity_with_like(like, n, dtype=dtype)

    from numpy import eye
    return eye(n, dtype=dtype, like=like)


_identity_with_like = array_function_dispatch()(identity)


def _allclose_dispatcher(a, b, rtol=None, atol=None, equal_nan=None):
    return (a, b, rtol, atol)


@array_function_dispatch(_allclose_dispatcher)
def allclose(a, b, rtol=1.e-5, atol=1.e-8, equal_nan=False):
    """
    Returns True if two arrays are element-wise equal within a tolerance.

    The tolerance values are positive, typically very small numbers.  The
    relative difference (`rtol` * abs(`b`)) and the absolute difference
    `atol` are added together to compare against the absolute difference
    between `a` and `b`.

    .. warning:: The default `atol` is not appropriate for comparing numbers
                 with magnitudes much smaller than one (see Notes).

    NaNs are treated as equal if they are in the same place and if
    ``equal_nan=True``.  Infs are treated as equal if they are in the same
    place and of the same sign in both arrays.

    Parameters
    ----------
    a, b : array_like
        Input arrays to compare.
    rtol : array_like
        The relative tolerance parameter (see Notes).
    atol : array_like
        The absolute tolerance parameter (see Notes).
    equal_nan : bool
        Whether to compare NaN's as equal.  If True, NaN's in `a` will be
        considered equal to NaN's in `b` in the output array.

    Returns
    -------
    allclose : bool
        Returns True if the two arrays are equal within the given
        tolerance; False otherwise.

    See Also
    --------
    isclose, all, any, equal

    Notes
    -----
    If the following equation is element-wise True, then allclose returns
    True.::

     absolute(a - b) <= (atol + rtol * absolute(b))

    The above equation is not symmetric in `a` and `b`, so that
    ``allclose(a, b)`` might be different from ``allclose(b, a)`` in
    some rare cases.

    The default value of `atol` is not appropriate when the reference value
    `b` has magnitude smaller than one. For example, it is unlikely that
    ``a = 1e-9`` and ``b = 2e-9`` should be considered "close", yet
    ``allclose(1e-9, 2e-9)`` is ``True`` with default settings. Be sure
    to select `atol` for the use case at hand, especially for defining the
    threshold below which a non-zero value in `a` will be considered "close"
    to a very small or zero value in `b`.

    The comparison of `a` and `b` uses standard broadcasting, which
    means that `a` and `b` need not have the same shape in order for
    ``allclose(a, b)`` to evaluate to True.  The same is true for
    `equal` but not `array_equal`.

    `allclose` is not defined for non-numeric data types.
    `bool` is considered a numeric data-type for this purpose.

    Examples
    --------
    >>> import numpy as np
    >>> np.allclose([1e10,1e-7], [1.00001e10,1e-8])
    False

    >>> np.allclose([1e10,1e-8], [1.00001e10,1e-9])
    True

    >>> np.allclose([1e10,1e-8], [1.0001e10,1e-9])
    False

    >>> np.allclose([1.0, np.nan], [1.0, np.nan])
    False

    >>> np.allclose([1.0, np.nan], [1.0, np.nan], equal_nan=True)
    True


    """
    res = all(isclose(a, b, rtol=rtol, atol=atol, equal_nan=equal_nan))
    return builtins.bool(res)


def _isclose_dispatcher(a, b, rtol=None, atol=None, equal_nan=None):
    return (a, b, rtol, atol)


@array_function_dispatch(_isclose_dispatcher)
def isclose(a, b, rtol=1.e-5, atol=1.e-8, equal_nan=False):
    """
    Returns a boolean array where two arrays are element-wise equal within a
    tolerance.

    The tolerance values are positive, typically very small numbers.  The
    relative difference (`rtol` * abs(`b`)) and the absolute difference
    `atol` are added together to compare against the absolute difference
    between `a` and `b`.

    .. warning:: The default `atol` is not appropriate for comparing numbers
                 with magnitudes much smaller than one (see Notes).

    Parameters
    ----------
    a, b : array_like
        Input arrays to compare.
    rtol : array_like
        The relative tolerance parameter (see Notes).
    atol : array_like
        The absolute tolerance parameter (see Notes).
    equal_nan : bool
        Whether to compare NaN's as equal.  If True, NaN's in `a` will be
        considered equal to NaN's in `b` in the output array.

    Returns
    -------
    y : array_like
        Returns a boolean array of where `a` and `b` are equal within the
        given tolerance. If both `a` and `b` are scalars, returns a single
        boolean value.

    See Also
    --------
    allclose
    math.isclose

    Notes
    -----
    For finite values, isclose uses the following equation to test whether
    two floating point values are equivalent.::

     absolute(a - b) <= (atol + rtol * absolute(b))

    Unlike the built-in `math.isclose`, the above equation is not symmetric
    in `a` and `b` -- it assumes `b` is the reference value -- so that
    `isclose(a, b)` might be different from `isclose(b, a)`.

    The default value of `atol` is not appropriate when the reference value
    `b` has magnitude smaller than one. For example, it is unlikely that
    ``a = 1e-9`` and ``b = 2e-9`` should be considered "close", yet
    ``isclose(1e-9, 2e-9)`` is ``True`` with default settings. Be sure
    to select `atol` for the use case at hand, especially for defining the
    threshold below which a non-zero value in `a` will be considered "close"
    to a very small or zero value in `b`.

    `isclose` is not defined for non-numeric data types.
    :class:`bool` is considered a numeric data-type for this purpose.

    Examples
    --------
    >>> import numpy as np
    >>> np.isclose([1e10,1e-7], [1.00001e10,1e-8])
    array([ True, False])

    >>> np.isclose([1e10,1e-8], [1.00001e10,1e-9])
    array([ True, True])

    >>> np.isclose([1e10,1e-8], [1.0001e10,1e-9])
    array([False,  True])

    >>> np.isclose([1.0, np.nan], [1.0, np.nan])
    array([ True, False])

    >>> np.isclose([1.0, np.nan], [1.0, np.nan], equal_nan=True)
    array([ True, True])

    >>> np.isclose([1e-8, 1e-7], [0.0, 0.0])
    array([ True, False])

    >>> np.isclose([1e-100, 1e-7], [0.0, 0.0], atol=0.0)
    array([False, False])

    >>> np.isclose([1e-10, 1e-10], [1e-20, 0.0])
    array([ True,  True])

    >>> np.isclose([1e-10, 1e-10], [1e-20, 0.999999e-10], atol=0.0)
    array([False,  True])

    """
    # Turn all but python scalars into arrays.
    x, y, atol, rtol = (
        a if isinstance(a, (int, float, complex)) else asanyarray(a)
        for a in (a, b, atol, rtol))

    # Make sure y is an inexact type to avoid bad behavior on abs(MIN_INT).
    # This will cause casting of x later. Also, make sure to allow subclasses
    # (e.g., for numpy.ma).
    # NOTE: We explicitly allow timedelta, which used to work. This could
    #       possibly be deprecated. See also gh-18286.
    #       timedelta works if `atol` is an integer or also a timedelta.
    #       Although, the default tolerances are unlikely to be useful
    if (dtype := getattr(y, "dtype", None)) is not None and dtype.kind != "m":
        dt = multiarray.result_type(y, 1.)
        y = asanyarray(y, dtype=dt)
    elif isinstance(y, int):
        y = float(y)

    # atol and rtol can be arrays
    if not (np.all(np.isfinite(atol)) and np.all(np.isfinite(rtol))):
        err_s = np.geterr()["invalid"]
        err_msg = f"One of rtol or atol is not valid, atol: {atol}, rtol: {rtol}"

        if err_s == "warn":
            warnings.warn(err_msg, RuntimeWarning, stacklevel=2)
        elif err_s == "raise":
            raise FloatingPointError(err_msg)
        elif err_s == "print":
            print(err_msg)

    with errstate(invalid='ignore'):

        result = (less_equal(abs(x - y), atol + rtol * abs(y))
                  & isfinite(y)
                  | (x == y))
        if equal_nan:
            result |= isnan(x) & isnan(y)

    return result[()]  # Flatten 0d arrays to scalars


def _array_equal_dispatcher(a1, a2, equal_nan=None):
    return (a1, a2)


_no_nan_types = {
    # should use np.dtype.BoolDType, but as of writing
    # that fails the reloading test.
    type(dtype(nt.bool)),
    type(dtype(nt.int8)),
    type(dtype(nt.int16)),
    type(dtype(nt.int32)),
    type(dtype(nt.int64)),
}


def _dtype_cannot_hold_nan(dtype):
    return type(dtype) in _no_nan_types


@array_function_dispatch(_array_equal_dispatcher)
def array_equal(a1, a2, equal_nan=False):
    """
    True if two arrays have the same shape and elements, False otherwise.

    Parameters
    ----------
    a1, a2 : array_like
        Input arrays.
    equal_nan : bool
        Whether to compare NaN's as equal. If the dtype of a1 and a2 is
        complex, values will be considered equal if either the real or the
        imaginary component of a given value is ``nan``.

    Returns
    -------
    b : bool
        Returns True if the arrays are equal.

    See Also
    --------
    allclose: Returns True if two arrays are element-wise equal within a
              tolerance.
    array_equiv: Returns True if input arrays are shape consistent and all
                 elements equal.

    Examples
    --------
    >>> import numpy as np

    >>> np.array_equal([1, 2], [1, 2])
    True

    >>> np.array_equal(np.array([1, 2]), np.array([1, 2]))
    True

    >>> np.array_equal([1, 2], [1, 2, 3])
    False

    >>> np.array_equal([1, 2], [1, 4])
    False

    >>> a = np.array([1, np.nan])
    >>> np.array_equal(a, a)
    False

    >>> np.array_equal(a, a, equal_nan=True)
    True

    When ``equal_nan`` is True, complex values with nan components are
    considered equal if either the real *or* the imaginary components are nan.

    >>> a = np.array([1 + 1j])
    >>> b = a.copy()
    >>> a.real = np.nan
    >>> b.imag = np.nan
    >>> np.array_equal(a, b, equal_nan=True)
    True
    """
    try:
        a1, a2 = asarray(a1), asarray(a2)
    except Exception:
        return False
    if a1.shape != a2.shape:
        return False
    if not equal_nan:
        return builtins.bool((asanyarray(a1 == a2)).all())

    if a1 is a2:
        # nan will compare equal so an array will compare equal to itself.
        return True

    cannot_have_nan = (_dtype_cannot_hold_nan(a1.dtype)
                       and _dtype_cannot_hold_nan(a2.dtype))
    if cannot_have_nan:
        return builtins.bool(asarray(a1 == a2).all())

    # Handling NaN values if equal_nan is True
    a1nan, a2nan = isnan(a1), isnan(a2)
    # NaN's occur at different locations
    if not (a1nan == a2nan).all():
        return False
    # Shapes of a1, a2 and masks are guaranteed to be consistent by this point
    return builtins.bool((a1[~a1nan] == a2[~a1nan]).all())


def _array_equiv_dispatcher(a1, a2):
    return (a1, a2)


@array_function_dispatch(_array_equiv_dispatcher)
def array_equiv(a1, a2):
    """
    Returns True if input arrays are shape consistent and all elements equal.

    Shape consistent means they are either the same shape, or one input array
    can be broadcasted to create the same shape as the other one.

    Parameters
    ----------
    a1, a2 : array_like
        Input arrays.

    Returns
    -------
    out : bool
        True if equivalent, False otherwise.

    Examples
    --------
    >>> import numpy as np
    >>> np.array_equiv([1, 2], [1, 2])
    True
    >>> np.array_equiv([1, 2], [1, 3])
    False

    Showing the shape equivalence:

    >>> np.array_equiv([1, 2], [[1, 2], [1, 2]])
    True
    >>> np.array_equiv([1, 2], [[1, 2, 1, 2], [1, 2, 1, 2]])
    False

    >>> np.array_equiv([1, 2], [[1, 2], [1, 3]])
    False

    """
    try:
        a1, a2 = asarray(a1), asarray(a2)
    except Exception:
        return False
    try:
        multiarray.broadcast(a1, a2)
    except Exception:
        return False

    return builtins.bool(asanyarray(a1 == a2).all())


def _astype_dispatcher(x, dtype, /, *, copy=None, device=None):
    return (x, dtype)


@array_function_dispatch(_astype_dispatcher)
def astype(x, dtype, /, *, copy=True, device=None):
    """
    Copies an array to a specified data type.

    This function is an Array API compatible alternative to
    `numpy.ndarray.astype`.

    Parameters
    ----------
    x : ndarray
        Input NumPy array to cast. ``array_likes`` are explicitly not
        supported here.
    dtype : dtype
        Data type of the result.
    copy : bool, optional
        Specifies whether to copy an array when the specified dtype matches
        the data type of the input array ``x``. If ``True``, a newly allocated
        array must always be returned. If ``False`` and the specified dtype
        matches the data type of the input array, the input array must be
        returned; otherwise, a newly allocated array must be returned.
        Defaults to ``True``.
    device : str, optional
        The device on which to place the returned array. Default: None.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.1.0

    Returns
    -------
    out : ndarray
        An array having the specified data type.

    See Also
    --------
    ndarray.astype

    Examples
    --------
    >>> import numpy as np
    >>> arr = np.array([1, 2, 3]); arr
    array([1, 2, 3])
    >>> np.astype(arr, np.float64)
    array([1., 2., 3.])

    Non-copy case:

    >>> arr = np.array([1, 2, 3])
    >>> arr_noncpy = np.astype(arr, arr.dtype, copy=False)
    >>> np.shares_memory(arr, arr_noncpy)
    True

    """
    if not (isinstance(x, np.ndarray) or isscalar(x)):
        raise TypeError(
            "Input should be a NumPy array or scalar. "
            f"It is a {type(x)} instead."
        )
    if device is not None and device != "cpu":
        raise ValueError(
            'Device not understood. Only "cpu" is allowed, but received:'
            f' {device}'
        )
    return x.astype(dtype, copy=copy)


inf = PINF
nan = NAN
False_ = nt.bool(False)
True_ = nt.bool(True)


def extend_all(module):
    existing = set(__all__)
    mall = module.__all__
    for a in mall:
        if a not in existing:
            __all__.append(a)


from . import _asarray, _ufunc_config, arrayprint, fromnumeric
from ._asarray import *
from ._ufunc_config import *
from .arrayprint import *
from .fromnumeric import *
from .numerictypes import *
from .umath import *

extend_all(fromnumeric)
extend_all(umath)
extend_all(numerictypes)
extend_all(arrayprint)
extend_all(_asarray)
extend_all(_ufunc_config)

# === NexusCore/openenv\Lib\site-packages\numpy\testing\_private\utils.py ===
"""
Utility function to facilitate testing.

"""
import concurrent.futures
import contextlib
import gc
import importlib.metadata
import operator
import os
import pathlib
import platform
import pprint
import re
import shutil
import sys
import sysconfig
import threading
import warnings
from functools import partial, wraps
from io import StringIO
from tempfile import mkdtemp, mkstemp
from unittest.case import SkipTest
from warnings import WarningMessage

import numpy as np
import numpy.linalg._umath_linalg
from numpy import isfinite, isinf, isnan
from numpy._core import arange, array, array_repr, empty, float32, intp, isnat, ndarray

__all__ = [
        'assert_equal', 'assert_almost_equal', 'assert_approx_equal',
        'assert_array_equal', 'assert_array_less', 'assert_string_equal',
        'assert_array_almost_equal', 'assert_raises', 'build_err_msg',
        'decorate_methods', 'jiffies', 'memusage', 'print_assert_equal',
        'rundocs', 'runstring', 'verbose', 'measure',
        'assert_', 'assert_array_almost_equal_nulp', 'assert_raises_regex',
        'assert_array_max_ulp', 'assert_warns', 'assert_no_warnings',
        'assert_allclose', 'IgnoreException', 'clear_and_catch_warnings',
        'SkipTest', 'KnownFailureException', 'temppath', 'tempdir', 'IS_PYPY',
        'HAS_REFCOUNT', "IS_WASM", 'suppress_warnings', 'assert_array_compare',
        'assert_no_gc_cycles', 'break_cycles', 'HAS_LAPACK64', 'IS_PYSTON',
        'IS_MUSL', 'check_support_sve', 'NOGIL_BUILD',
        'IS_EDITABLE', 'IS_INSTALLED', 'NUMPY_ROOT', 'run_threaded', 'IS_64BIT',
        'BLAS_SUPPORTS_FPE',
        ]


class KnownFailureException(Exception):
    '''Raise this exception to mark a test as a known failing test.'''
    pass


KnownFailureTest = KnownFailureException  # backwards compat
verbose = 0

NUMPY_ROOT = pathlib.Path(np.__file__).parent

try:
    np_dist = importlib.metadata.distribution('numpy')
except importlib.metadata.PackageNotFoundError:
    IS_INSTALLED = IS_EDITABLE = False
else:
    IS_INSTALLED = True
    try:
        if sys.version_info >= (3, 13):
            IS_EDITABLE = np_dist.origin.dir_info.editable
        else:
            # Backport importlib.metadata.Distribution.origin
            import json  # noqa: E401
            import types
            origin = json.loads(
                np_dist.read_text('direct_url.json') or '{}',
                object_hook=lambda data: types.SimpleNamespace(**data),
            )
            IS_EDITABLE = origin.dir_info.editable
    except AttributeError:
        IS_EDITABLE = False

    # spin installs numpy directly via meson, instead of using meson-python, and
    # runs the module by setting PYTHONPATH. This is problematic because the
    # resulting installation lacks the Python metadata (.dist-info), and numpy
    # might already be installed on the environment, causing us to find its
    # metadata, even though we are not actually loading that package.
    # Work around this issue by checking if the numpy root matches.
    if not IS_EDITABLE and np_dist.locate_file('numpy') != NUMPY_ROOT:
        IS_INSTALLED = False

IS_WASM = platform.machine() in ["wasm32", "wasm64"]
IS_PYPY = sys.implementation.name == 'pypy'
IS_PYSTON = hasattr(sys, "pyston_version_info")
HAS_REFCOUNT = getattr(sys, 'getrefcount', None) is not None and not IS_PYSTON
BLAS_SUPPORTS_FPE = True
if platform.system() == 'Darwin' or platform.machine() == 'arm64':
    try:
        blas = np.__config__.CONFIG['Build Dependencies']['blas']
        if blas['name'] == 'accelerate':
            BLAS_SUPPORTS_FPE = False
    except KeyError:
        pass

HAS_LAPACK64 = numpy.linalg._umath_linalg._ilp64

IS_MUSL = False
# alternate way is
# from packaging.tags import sys_tags
#     _tags = list(sys_tags())
#     if 'musllinux' in _tags[0].platform:
_v = sysconfig.get_config_var('HOST_GNU_TYPE') or ''
if 'musl' in _v:
    IS_MUSL = True

NOGIL_BUILD = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
IS_64BIT = np.dtype(np.intp).itemsize == 8

def assert_(val, msg=''):
    """
    Assert that works in release mode.
    Accepts callable msg to allow deferring evaluation until failure.

    The Python built-in ``assert`` does not work when executing code in
    optimized mode (the ``-O`` flag) - no byte-code is generated for it.

    For documentation on usage, refer to the Python documentation.

    """
    __tracebackhide__ = True  # Hide traceback for py.test
    if not val:
        try:
            smsg = msg()
        except TypeError:
            smsg = msg
        raise AssertionError(smsg)


if os.name == 'nt':
    # Code "stolen" from enthought/debug/memusage.py
    def GetPerformanceAttributes(object, counter, instance=None,
                                 inum=-1, format=None, machine=None):
        # NOTE: Many counters require 2 samples to give accurate results,
        # including "% Processor Time" (as by definition, at any instant, a
        # thread's CPU usage is either 0 or 100).  To read counters like this,
        # you should copy this function, but keep the counter open, and call
        # CollectQueryData() each time you need to know.
        # See http://msdn.microsoft.com/library/en-us/dnperfmo/html/perfmonpt2.asp
        # (dead link)
        # My older explanation for this was that the "AddCounter" process
        # forced the CPU to 100%, but the above makes more sense :)
        import win32pdh
        if format is None:
            format = win32pdh.PDH_FMT_LONG
        path = win32pdh.MakeCounterPath((machine, object, instance, None,
                                         inum, counter))
        hq = win32pdh.OpenQuery()
        try:
            hc = win32pdh.AddCounter(hq, path)
            try:
                win32pdh.CollectQueryData(hq)
                type, val = win32pdh.GetFormattedCounterValue(hc, format)
                return val
            finally:
                win32pdh.RemoveCounter(hc)
        finally:
            win32pdh.CloseQuery(hq)

    def memusage(processName="python", instance=0):
        # from win32pdhutil, part of the win32all package
        import win32pdh
        return GetPerformanceAttributes("Process", "Virtual Bytes",
                                        processName, instance,
                                        win32pdh.PDH_FMT_LONG, None)
elif sys.platform[:5] == 'linux':

    def memusage(_proc_pid_stat=None):
        """
        Return virtual memory size in bytes of the running python.

        """
        _proc_pid_stat = _proc_pid_stat or f'/proc/{os.getpid()}/stat'
        try:
            with open(_proc_pid_stat) as f:
                l = f.readline().split(' ')
            return int(l[22])
        except Exception:
            return
else:
    def memusage():
        """
        Return memory usage of running python. [Not implemented]

        """
        raise NotImplementedError


if sys.platform[:5] == 'linux':
    def jiffies(_proc_pid_stat=None, _load_time=None):
        """
        Return number of jiffies elapsed.

        Return number of jiffies (1/100ths of a second) that this
        process has been scheduled in user mode. See man 5 proc.

        """
        _proc_pid_stat = _proc_pid_stat or f'/proc/{os.getpid()}/stat'
        _load_time = _load_time or []
        import time
        if not _load_time:
            _load_time.append(time.time())
        try:
            with open(_proc_pid_stat) as f:
                l = f.readline().split(' ')
            return int(l[13])
        except Exception:
            return int(100 * (time.time() - _load_time[0]))
else:
    # os.getpid is not in all platforms available.
    # Using time is safe but inaccurate, especially when process
    # was suspended or sleeping.
    def jiffies(_load_time=[]):
        """
        Return number of jiffies elapsed.

        Return number of jiffies (1/100ths of a second) that this
        process has been scheduled in user mode. See man 5 proc.

        """
        import time
        if not _load_time:
            _load_time.append(time.time())
        return int(100 * (time.time() - _load_time[0]))


def build_err_msg(arrays, err_msg, header='Items are not equal:',
                  verbose=True, names=('ACTUAL', 'DESIRED'), precision=8):
    msg = ['\n' + header]
    err_msg = str(err_msg)
    if err_msg:
        if err_msg.find('\n') == -1 and len(err_msg) < 79 - len(header):
            msg = [msg[0] + ' ' + err_msg]
        else:
            msg.append(err_msg)
    if verbose:
        for i, a in enumerate(arrays):

            if isinstance(a, ndarray):
                # precision argument is only needed if the objects are ndarrays
                r_func = partial(array_repr, precision=precision)
            else:
                r_func = repr

            try:
                r = r_func(a)
            except Exception as exc:
                r = f'[repr failed for <{type(a).__name__}>: {exc}]'
            if r.count('\n') > 3:
                r = '\n'.join(r.splitlines()[:3])
                r += '...'
            msg.append(f' {names[i]}: {r}')
    return '\n'.join(msg)


def assert_equal(actual, desired, err_msg='', verbose=True, *, strict=False):
    """
    Raises an AssertionError if two objects are not equal.

    Given two objects (scalars, lists, tuples, dictionaries or numpy arrays),
    check that all elements of these objects are equal. An exception is raised
    at the first conflicting values.

    This function handles NaN comparisons as if NaN was a "normal" number.
    That is, AssertionError is not raised if both objects have NaNs in the same
    positions.  This is in contrast to the IEEE standard on NaNs, which says
    that NaN compared to anything must return False.

    Parameters
    ----------
    actual : array_like
        The object to check.
    desired : array_like
        The expected object.
    err_msg : str, optional
        The error message to be printed in case of failure.
    verbose : bool, optional
        If True, the conflicting values are appended to the error message.
    strict : bool, optional
        If True and either of the `actual` and `desired` arguments is an array,
        raise an ``AssertionError`` when either the shape or the data type of
        the arguments does not match. If neither argument is an array, this
        parameter has no effect.

        .. versionadded:: 2.0.0

    Raises
    ------
    AssertionError
        If actual and desired are not equal.

    See Also
    --------
    assert_allclose
    assert_array_almost_equal_nulp,
    assert_array_max_ulp,

    Notes
    -----
    By default, when one of `actual` and `desired` is a scalar and the other is
    an array, the function checks that each element of the array is equal to
    the scalar. This behaviour can be disabled by setting ``strict==True``.

    Examples
    --------
    >>> np.testing.assert_equal([4, 5], [4, 6])
    Traceback (most recent call last):
        ...
    AssertionError:
    Items are not equal:
    item=1
     ACTUAL: 5
     DESIRED: 6

    The following comparison does not raise an exception.  There are NaNs
    in the inputs, but they are in the same positions.

    >>> np.testing.assert_equal(np.array([1.0, 2.0, np.nan]), [1, 2, np.nan])

    As mentioned in the Notes section, `assert_equal` has special
    handling for scalars when one of the arguments is an array.
    Here, the test checks that each value in `x` is 3:

    >>> x = np.full((2, 5), fill_value=3)
    >>> np.testing.assert_equal(x, 3)

    Use `strict` to raise an AssertionError when comparing a scalar with an
    array of a different shape:

    >>> np.testing.assert_equal(x, 3, strict=True)
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not equal
    <BLANKLINE>
    (shapes (2, 5), () mismatch)
     ACTUAL: array([[3, 3, 3, 3, 3],
           [3, 3, 3, 3, 3]])
     DESIRED: array(3)

    The `strict` parameter also ensures that the array data types match:

    >>> x = np.array([2, 2, 2])
    >>> y = np.array([2., 2., 2.], dtype=np.float32)
    >>> np.testing.assert_equal(x, y, strict=True)
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not equal
    <BLANKLINE>
    (dtypes int64, float32 mismatch)
     ACTUAL: array([2, 2, 2])
     DESIRED: array([2., 2., 2.], dtype=float32)
    """
    __tracebackhide__ = True  # Hide traceback for py.test
    if isinstance(desired, dict):
        if not isinstance(actual, dict):
            raise AssertionError(repr(type(actual)))
        assert_equal(len(actual), len(desired), err_msg, verbose)
        for k, i in desired.items():
            if k not in actual:
                raise AssertionError(repr(k))
            assert_equal(actual[k], desired[k], f'key={k!r}\n{err_msg}',
                         verbose)
        return
    if isinstance(desired, (list, tuple)) and isinstance(actual, (list, tuple)):
        assert_equal(len(actual), len(desired), err_msg, verbose)
        for k in range(len(desired)):
            assert_equal(actual[k], desired[k], f'item={k!r}\n{err_msg}',
                         verbose)
        return
    from numpy import imag, iscomplexobj, real
    from numpy._core import isscalar, ndarray, signbit
    if isinstance(actual, ndarray) or isinstance(desired, ndarray):
        return assert_array_equal(actual, desired, err_msg, verbose,
                                  strict=strict)
    msg = build_err_msg([actual, desired], err_msg, verbose=verbose)

    # Handle complex numbers: separate into real/imag to handle
    # nan/inf/negative zero correctly
    # XXX: catch ValueError for subclasses of ndarray where iscomplex fail
    try:
        usecomplex = iscomplexobj(actual) or iscomplexobj(desired)
    except (ValueError, TypeError):
        usecomplex = False

    if usecomplex:
        if iscomplexobj(actual):
            actualr = real(actual)
            actuali = imag(actual)
        else:
            actualr = actual
            actuali = 0
        if iscomplexobj(desired):
            desiredr = real(desired)
            desiredi = imag(desired)
        else:
            desiredr = desired
            desiredi = 0
        try:
            assert_equal(actualr, desiredr)
            assert_equal(actuali, desiredi)
        except AssertionError:
            raise AssertionError(msg)

    # isscalar test to check cases such as [np.nan] != np.nan
    if isscalar(desired) != isscalar(actual):
        raise AssertionError(msg)

    try:
        isdesnat = isnat(desired)
        isactnat = isnat(actual)
        dtypes_match = (np.asarray(desired).dtype.type ==
                        np.asarray(actual).dtype.type)
        if isdesnat and isactnat:
            # If both are NaT (and have the same dtype -- datetime or
            # timedelta) they are considered equal.
            if dtypes_match:
                return
            else:
                raise AssertionError(msg)

    except (TypeError, ValueError, NotImplementedError):
        pass

    # Inf/nan/negative zero handling
    try:
        isdesnan = isnan(desired)
        isactnan = isnan(actual)
        if isdesnan and isactnan:
            return  # both nan, so equal

        # handle signed zero specially for floats
        array_actual = np.asarray(actual)
        array_desired = np.asarray(desired)
        if (array_actual.dtype.char in 'Mm' or
                array_desired.dtype.char in 'Mm'):
            # version 1.18
            # until this version, isnan failed for datetime64 and timedelta64.
            # Now it succeeds but comparison to scalar with a different type
            # emits a DeprecationWarning.
            # Avoid that by skipping the next check
            raise NotImplementedError('cannot compare to a scalar '
                                      'with a different type')

        if desired == 0 and actual == 0:
            if not signbit(desired) == signbit(actual):
                raise AssertionError(msg)

    except (TypeError, ValueError, NotImplementedError):
        pass

    try:
        # Explicitly use __eq__ for comparison, gh-2552
        if not (desired == actual):
            raise AssertionError(msg)

    except (DeprecationWarning, FutureWarning) as e:
        # this handles the case when the two types are not even comparable
        if 'elementwise == comparison' in e.args[0]:
            raise AssertionError(msg)
        else:
            raise


def print_assert_equal(test_string, actual, desired):
    """
    Test if two objects are equal, and print an error message if test fails.

    The test is performed with ``actual == desired``.

    Parameters
    ----------
    test_string : str
        The message supplied to AssertionError.
    actual : object
        The object to test for equality against `desired`.
    desired : object
        The expected result.

    Examples
    --------
    >>> np.testing.print_assert_equal('Test XYZ of func xyz', [0, 1], [0, 1])
    >>> np.testing.print_assert_equal('Test XYZ of func xyz', [0, 1], [0, 2])
    Traceback (most recent call last):
    ...
    AssertionError: Test XYZ of func xyz failed
    ACTUAL:
    [0, 1]
    DESIRED:
    [0, 2]

    """
    __tracebackhide__ = True  # Hide traceback for py.test
    import pprint

    if not (actual == desired):
        msg = StringIO()
        msg.write(test_string)
        msg.write(' failed\nACTUAL: \n')
        pprint.pprint(actual, msg)
        msg.write('DESIRED: \n')
        pprint.pprint(desired, msg)
        raise AssertionError(msg.getvalue())


def assert_almost_equal(actual, desired, decimal=7, err_msg='', verbose=True):
    """
    Raises an AssertionError if two items are not equal up to desired
    precision.

    .. note:: It is recommended to use one of `assert_allclose`,
              `assert_array_almost_equal_nulp` or `assert_array_max_ulp`
              instead of this function for more consistent floating point
              comparisons.

    The test verifies that the elements of `actual` and `desired` satisfy::

        abs(desired-actual) < float64(1.5 * 10**(-decimal))

    That is a looser test than originally documented, but agrees with what the
    actual implementation in `assert_array_almost_equal` did up to rounding
    vagaries. An exception is raised at conflicting values. For ndarrays this
    delegates to assert_array_almost_equal

    Parameters
    ----------
    actual : array_like
        The object to check.
    desired : array_like
        The expected object.
    decimal : int, optional
        Desired precision, default is 7.
    err_msg : str, optional
        The error message to be printed in case of failure.
    verbose : bool, optional
        If True, the conflicting values are appended to the error message.

    Raises
    ------
    AssertionError
      If actual and desired are not equal up to specified precision.

    See Also
    --------
    assert_allclose: Compare two array_like objects for equality with desired
                     relative and/or absolute precision.
    assert_array_almost_equal_nulp, assert_array_max_ulp, assert_equal

    Examples
    --------
    >>> from numpy.testing import assert_almost_equal
    >>> assert_almost_equal(2.3333333333333, 2.33333334)
    >>> assert_almost_equal(2.3333333333333, 2.33333334, decimal=10)
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not almost equal to 10 decimals
     ACTUAL: 2.3333333333333
     DESIRED: 2.33333334

    >>> assert_almost_equal(np.array([1.0,2.3333333333333]),
    ...                     np.array([1.0,2.33333334]), decimal=9)
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not almost equal to 9 decimals
    <BLANKLINE>
    Mismatched elements: 1 / 2 (50%)
    Max absolute difference among violations: 6.66669964e-09
    Max relative difference among violations: 2.85715698e-09
     ACTUAL: array([1.         , 2.333333333])
     DESIRED: array([1.        , 2.33333334])

    """
    __tracebackhide__ = True  # Hide traceback for py.test
    from numpy import imag, iscomplexobj, real
    from numpy._core import ndarray

    # Handle complex numbers: separate into real/imag to handle
    # nan/inf/negative zero correctly
    # XXX: catch ValueError for subclasses of ndarray where iscomplex fail
    try:
        usecomplex = iscomplexobj(actual) or iscomplexobj(desired)
    except ValueError:
        usecomplex = False

    def _build_err_msg():
        header = ('Arrays are not almost equal to %d decimals' % decimal)
        return build_err_msg([actual, desired], err_msg, verbose=verbose,
                             header=header)

    if usecomplex:
        if iscomplexobj(actual):
            actualr = real(actual)
            actuali = imag(actual)
        else:
            actualr = actual
            actuali = 0
        if iscomplexobj(desired):
            desiredr = real(desired)
            desiredi = imag(desired)
        else:
            desiredr = desired
            desiredi = 0
        try:
            assert_almost_equal(actualr, desiredr, decimal=decimal)
            assert_almost_equal(actuali, desiredi, decimal=decimal)
        except AssertionError:
            raise AssertionError(_build_err_msg())

    if isinstance(actual, (ndarray, tuple, list)) \
            or isinstance(desired, (ndarray, tuple, list)):
        return assert_array_almost_equal(actual, desired, decimal, err_msg)
    try:
        # If one of desired/actual is not finite, handle it specially here:
        # check that both are nan if any is a nan, and test for equality
        # otherwise
        if not (isfinite(desired) and isfinite(actual)):
            if isnan(desired) or isnan(actual):
                if not (isnan(desired) and isnan(actual)):
                    raise AssertionError(_build_err_msg())
            elif not desired == actual:
                raise AssertionError(_build_err_msg())
            return
    except (NotImplementedError, TypeError):
        pass
    if abs(desired - actual) >= np.float64(1.5 * 10.0**(-decimal)):
        raise AssertionError(_build_err_msg())


def assert_approx_equal(actual, desired, significant=7, err_msg='',
                        verbose=True):
    """
    Raises an AssertionError if two items are not equal up to significant
    digits.

    .. note:: It is recommended to use one of `assert_allclose`,
              `assert_array_almost_equal_nulp` or `assert_array_max_ulp`
              instead of this function for more consistent floating point
              comparisons.

    Given two numbers, check that they are approximately equal.
    Approximately equal is defined as the number of significant digits
    that agree.

    Parameters
    ----------
    actual : scalar
        The object to check.
    desired : scalar
        The expected object.
    significant : int, optional
        Desired precision, default is 7.
    err_msg : str, optional
        The error message to be printed in case of failure.
    verbose : bool, optional
        If True, the conflicting values are appended to the error message.

    Raises
    ------
    AssertionError
      If actual and desired are not equal up to specified precision.

    See Also
    --------
    assert_allclose: Compare two array_like objects for equality with desired
                     relative and/or absolute precision.
    assert_array_almost_equal_nulp, assert_array_max_ulp, assert_equal

    Examples
    --------
    >>> np.testing.assert_approx_equal(0.12345677777777e-20, 0.1234567e-20)
    >>> np.testing.assert_approx_equal(0.12345670e-20, 0.12345671e-20,
    ...                                significant=8)
    >>> np.testing.assert_approx_equal(0.12345670e-20, 0.12345672e-20,
    ...                                significant=8)
    Traceback (most recent call last):
        ...
    AssertionError:
    Items are not equal to 8 significant digits:
     ACTUAL: 1.234567e-21
     DESIRED: 1.2345672e-21

    the evaluated condition that raises the exception is

    >>> abs(0.12345670e-20/1e-21 - 0.12345672e-20/1e-21) >= 10**-(8-1)
    True

    """
    __tracebackhide__ = True  # Hide traceback for py.test
    import numpy as np

    (actual, desired) = map(float, (actual, desired))
    if desired == actual:
        return
    # Normalized the numbers to be in range (-10.0,10.0)
    # scale = float(pow(10,math.floor(math.log10(0.5*(abs(desired)+abs(actual))))))
    with np.errstate(invalid='ignore'):
        scale = 0.5 * (np.abs(desired) + np.abs(actual))
        scale = np.power(10, np.floor(np.log10(scale)))
    try:
        sc_desired = desired / scale
    except ZeroDivisionError:
        sc_desired = 0.0
    try:
        sc_actual = actual / scale
    except ZeroDivisionError:
        sc_actual = 0.0
    msg = build_err_msg(
        [actual, desired], err_msg,
        header='Items are not equal to %d significant digits:' % significant,
        verbose=verbose)
    try:
        # If one of desired/actual is not finite, handle it specially here:
        # check that both are nan if any is a nan, and test for equality
        # otherwise
        if not (isfinite(desired) and isfinite(actual)):
            if isnan(desired) or isnan(actual):
                if not (isnan(desired) and isnan(actual)):
                    raise AssertionError(msg)
            elif not desired == actual:
                raise AssertionError(msg)
            return
    except (TypeError, NotImplementedError):
        pass
    if np.abs(sc_desired - sc_actual) >= np.power(10., -(significant - 1)):
        raise AssertionError(msg)


def assert_array_compare(comparison, x, y, err_msg='', verbose=True, header='',
                         precision=6, equal_nan=True, equal_inf=True,
                         *, strict=False, names=('ACTUAL', 'DESIRED')):
    __tracebackhide__ = True  # Hide traceback for py.test
    from numpy._core import all, array2string, errstate, inf, isnan, max, object_

    x = np.asanyarray(x)
    y = np.asanyarray(y)

    # original array for output formatting
    ox, oy = x, y

    def isnumber(x):
        return x.dtype.char in '?bhilqpBHILQPefdgFDG'

    def istime(x):
        return x.dtype.char in "Mm"

    def isvstring(x):
        return x.dtype.char == "T"

    def func_assert_same_pos(x, y, func=isnan, hasval='nan'):
        """Handling nan/inf.

        Combine results of running func on x and y, checking that they are True
        at the same locations.

        """
        __tracebackhide__ = True  # Hide traceback for py.test

        x_id = func(x)
        y_id = func(y)
        # We include work-arounds here to handle three types of slightly
        # pathological ndarray subclasses:
        # (1) all() on `masked` array scalars can return masked arrays, so we
        #     use != True
        # (2) __eq__ on some ndarray subclasses returns Python booleans
        #     instead of element-wise comparisons, so we cast to np.bool() and
        #     use isinstance(..., bool) checks
        # (3) subclasses with bare-bones __array_function__ implementations may
        #     not implement np.all(), so favor using the .all() method
        # We are not committed to supporting such subclasses, but it's nice to
        # support them if possible.
        if np.bool(x_id == y_id).all() != True:
            msg = build_err_msg(
                [x, y],
                err_msg + '\n%s location mismatch:'
                % (hasval), verbose=verbose, header=header,
                names=names,
                precision=precision)
            raise AssertionError(msg)
        # If there is a scalar, then here we know the array has the same
        # flag as it everywhere, so we should return the scalar flag.
        if isinstance(x_id, bool) or x_id.ndim == 0:
            return np.bool(x_id)
        elif isinstance(y_id, bool) or y_id.ndim == 0:
            return np.bool(y_id)
        else:
            return y_id

    try:
        if strict:
            cond = x.shape == y.shape and x.dtype == y.dtype
        else:
            cond = (x.shape == () or y.shape == ()) or x.shape == y.shape
        if not cond:
            if x.shape != y.shape:
                reason = f'\n(shapes {x.shape}, {y.shape} mismatch)'
            else:
                reason = f'\n(dtypes {x.dtype}, {y.dtype} mismatch)'
            msg = build_err_msg([x, y],
                                err_msg
                                + reason,
                                verbose=verbose, header=header,
                                names=names,
                                precision=precision)
            raise AssertionError(msg)

        flagged = np.bool(False)
        if isnumber(x) and isnumber(y):
            if equal_nan:
                flagged = func_assert_same_pos(x, y, func=isnan, hasval='nan')

            if equal_inf:
                flagged |= func_assert_same_pos(x, y,
                                                func=lambda xy: xy == +inf,
                                                hasval='+inf')
                flagged |= func_assert_same_pos(x, y,
                                                func=lambda xy: xy == -inf,
                                                hasval='-inf')

        elif istime(x) and istime(y):
            # If one is datetime64 and the other timedelta64 there is no point
            if equal_nan and x.dtype.type == y.dtype.type:
                flagged = func_assert_same_pos(x, y, func=isnat, hasval="NaT")

        elif isvstring(x) and isvstring(y):
            dt = x.dtype
            if equal_nan and dt == y.dtype and hasattr(dt, 'na_object'):
                is_nan = (isinstance(dt.na_object, float) and
                          np.isnan(dt.na_object))
                bool_errors = 0
                try:
                    bool(dt.na_object)
                except TypeError:
                    bool_errors = 1
                if is_nan or bool_errors:
                    # nan-like NA object
                    flagged = func_assert_same_pos(
                        x, y, func=isnan, hasval=x.dtype.na_object)

        if flagged.ndim > 0:
            x, y = x[~flagged], y[~flagged]
            # Only do the comparison if actual values are left
            if x.size == 0:
                return
        elif flagged:
            # no sense doing comparison if everything is flagged.
            return

        val = comparison(x, y)
        invalids = np.logical_not(val)

        if isinstance(val, bool):
            cond = val
            reduced = array([val])
        else:
            reduced = val.ravel()
            cond = reduced.all()

        # The below comparison is a hack to ensure that fully masked
        # results, for which val.ravel().all() returns np.ma.masked,
        # do not trigger a failure (np.ma.masked != True evaluates as
        # np.ma.masked, which is falsy).
        if cond != True:
            n_mismatch = reduced.size - reduced.sum(dtype=intp)
            n_elements = flagged.size if flagged.ndim != 0 else reduced.size
            percent_mismatch = 100 * n_mismatch / n_elements
            remarks = [f'Mismatched elements: {n_mismatch} / {n_elements} '
                       f'({percent_mismatch:.3g}%)']

            with errstate(all='ignore'):
                # ignore errors for non-numeric types
                with contextlib.suppress(TypeError):
                    error = abs(x - y)
                    if np.issubdtype(x.dtype, np.unsignedinteger):
                        error2 = abs(y - x)
                        np.minimum(error, error2, out=error)

                    reduced_error = error[invalids]
                    max_abs_error = max(reduced_error)
                    if getattr(error, 'dtype', object_) == object_:
                        remarks.append(
                            'Max absolute difference among violations: '
                            + str(max_abs_error))
                    else:
                        remarks.append(
                            'Max absolute difference among violations: '
                            + array2string(max_abs_error))

                    # note: this definition of relative error matches that one
                    # used by assert_allclose (found in np.isclose)
                    # Filter values where the divisor would be zero
                    nonzero = np.bool(y != 0)
                    nonzero_and_invalid = np.logical_and(invalids, nonzero)

                    if all(~nonzero_and_invalid):
                        max_rel_error = array(inf)
                    else:
                        nonzero_invalid_error = error[nonzero_and_invalid]
                        broadcasted_y = np.broadcast_to(y, error.shape)
                        nonzero_invalid_y = broadcasted_y[nonzero_and_invalid]
                        max_rel_error = max(nonzero_invalid_error
                                            / abs(nonzero_invalid_y))

                    if getattr(error, 'dtype', object_) == object_:
                        remarks.append(
                            'Max relative difference among violations: '
                            + str(max_rel_error))
                    else:
                        remarks.append(
                            'Max relative difference among violations: '
                            + array2string(max_rel_error))
            err_msg = str(err_msg)
            err_msg += '\n' + '\n'.join(remarks)
            msg = build_err_msg([ox, oy], err_msg,
                                verbose=verbose, header=header,
                                names=names,
                                precision=precision)
            raise AssertionError(msg)
    except ValueError:
        import traceback
        efmt = traceback.format_exc()
        header = f'error during assertion:\n\n{efmt}\n\n{header}'

        msg = build_err_msg([x, y], err_msg, verbose=verbose, header=header,
                            names=names, precision=precision)
        raise ValueError(msg)


def assert_array_equal(actual, desired, err_msg='', verbose=True, *,
                       strict=False):
    """
    Raises an AssertionError if two array_like objects are not equal.

    Given two array_like objects, check that the shape is equal and all
    elements of these objects are equal (but see the Notes for the special
    handling of a scalar). An exception is raised at shape mismatch or
    conflicting values. In contrast to the standard usage in numpy, NaNs
    are compared like numbers, no assertion is raised if both objects have
    NaNs in the same positions.

    The usual caution for verifying equality with floating point numbers is
    advised.

    .. note:: When either `actual` or `desired` is already an instance of
        `numpy.ndarray` and `desired` is not a ``dict``, the behavior of
        ``assert_equal(actual, desired)`` is identical to the behavior of this
        function. Otherwise, this function performs `np.asanyarray` on the
        inputs before comparison, whereas `assert_equal` defines special
        comparison rules for common Python types. For example, only
        `assert_equal` can be used to compare nested Python lists. In new code,
        consider using only `assert_equal`, explicitly converting either
        `actual` or `desired` to arrays if the behavior of `assert_array_equal`
        is desired.

    Parameters
    ----------
    actual : array_like
        The actual object to check.
    desired : array_like
        The desired, expected object.
    err_msg : str, optional
        The error message to be printed in case of failure.
    verbose : bool, optional
        If True, the conflicting values are appended to the error message.
    strict : bool, optional
        If True, raise an AssertionError when either the shape or the data
        type of the array_like objects does not match. The special
        handling for scalars mentioned in the Notes section is disabled.

        .. versionadded:: 1.24.0

    Raises
    ------
    AssertionError
        If actual and desired objects are not equal.

    See Also
    --------
    assert_allclose: Compare two array_like objects for equality with desired
                     relative and/or absolute precision.
    assert_array_almost_equal_nulp, assert_array_max_ulp, assert_equal

    Notes
    -----
    When one of `actual` and `desired` is a scalar and the other is array_like,
    the function checks that each element of the array_like object is equal to
    the scalar. This behaviour can be disabled with the `strict` parameter.

    Examples
    --------
    The first assert does not raise an exception:

    >>> np.testing.assert_array_equal([1.0,2.33333,np.nan],
    ...                               [np.exp(0),2.33333, np.nan])

    Assert fails with numerical imprecision with floats:

    >>> np.testing.assert_array_equal([1.0,np.pi,np.nan],
    ...                               [1, np.sqrt(np.pi)**2, np.nan])
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not equal
    <BLANKLINE>
    Mismatched elements: 1 / 3 (33.3%)
    Max absolute difference among violations: 4.4408921e-16
    Max relative difference among violations: 1.41357986e-16
     ACTUAL: array([1.      , 3.141593,      nan])
     DESIRED: array([1.      , 3.141593,      nan])

    Use `assert_allclose` or one of the nulp (number of floating point values)
    functions for these cases instead:

    >>> np.testing.assert_allclose([1.0,np.pi,np.nan],
    ...                            [1, np.sqrt(np.pi)**2, np.nan],
    ...                            rtol=1e-10, atol=0)

    As mentioned in the Notes section, `assert_array_equal` has special
    handling for scalars. Here the test checks that each value in `x` is 3:

    >>> x = np.full((2, 5), fill_value=3)
    >>> np.testing.assert_array_equal(x, 3)

    Use `strict` to raise an AssertionError when comparing a scalar with an
    array:

    >>> np.testing.assert_array_equal(x, 3, strict=True)
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not equal
    <BLANKLINE>
    (shapes (2, 5), () mismatch)
     ACTUAL: array([[3, 3, 3, 3, 3],
           [3, 3, 3, 3, 3]])
     DESIRED: array(3)

    The `strict` parameter also ensures that the array data types match:

    >>> x = np.array([2, 2, 2])
    >>> y = np.array([2., 2., 2.], dtype=np.float32)
    >>> np.testing.assert_array_equal(x, y, strict=True)
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not equal
    <BLANKLINE>
    (dtypes int64, float32 mismatch)
     ACTUAL: array([2, 2, 2])
     DESIRED: array([2., 2., 2.], dtype=float32)
    """
    __tracebackhide__ = True  # Hide traceback for py.test
    assert_array_compare(operator.__eq__, actual, desired, err_msg=err_msg,
                         verbose=verbose, header='Arrays are not equal',
                         strict=strict)


def assert_array_almost_equal(actual, desired, decimal=6, err_msg='',
                              verbose=True):
    """
    Raises an AssertionError if two objects are not equal up to desired
    precision.

    .. note:: It is recommended to use one of `assert_allclose`,
              `assert_array_almost_equal_nulp` or `assert_array_max_ulp`
              instead of this function for more consistent floating point
              comparisons.

    The test verifies identical shapes and that the elements of ``actual`` and
    ``desired`` satisfy::

        abs(desired-actual) < 1.5 * 10**(-decimal)

    That is a looser test than originally documented, but agrees with what the
    actual implementation did up to rounding vagaries. An exception is raised
    at shape mismatch or conflicting values. In contrast to the standard usage
    in numpy, NaNs are compared like numbers, no assertion is raised if both
    objects have NaNs in the same positions.

    Parameters
    ----------
    actual : array_like
        The actual object to check.
    desired : array_like
        The desired, expected object.
    decimal : int, optional
        Desired precision, default is 6.
    err_msg : str, optional
      The error message to be printed in case of failure.
    verbose : bool, optional
        If True, the conflicting values are appended to the error message.

    Raises
    ------
    AssertionError
        If actual and desired are not equal up to specified precision.

    See Also
    --------
    assert_allclose: Compare two array_like objects for equality with desired
                     relative and/or absolute precision.
    assert_array_almost_equal_nulp, assert_array_max_ulp, assert_equal

    Examples
    --------
    the first assert does not raise an exception

    >>> np.testing.assert_array_almost_equal([1.0,2.333,np.nan],
    ...                                      [1.0,2.333,np.nan])

    >>> np.testing.assert_array_almost_equal([1.0,2.33333,np.nan],
    ...                                      [1.0,2.33339,np.nan], decimal=5)
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not almost equal to 5 decimals
    <BLANKLINE>
    Mismatched elements: 1 / 3 (33.3%)
    Max absolute difference among violations: 6.e-05
    Max relative difference among violations: 2.57136612e-05
     ACTUAL: array([1.     , 2.33333,     nan])
     DESIRED: array([1.     , 2.33339,     nan])

    >>> np.testing.assert_array_almost_equal([1.0,2.33333,np.nan],
    ...                                      [1.0,2.33333, 5], decimal=5)
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not almost equal to 5 decimals
    <BLANKLINE>
    nan location mismatch:
     ACTUAL: array([1.     , 2.33333,     nan])
     DESIRED: array([1.     , 2.33333, 5.     ])

    """
    __tracebackhide__ = True  # Hide traceback for py.test
    from numpy._core import number, result_type
    from numpy._core.fromnumeric import any as npany
    from numpy._core.numerictypes import issubdtype

    def compare(x, y):
        try:
            if npany(isinf(x)) or npany(isinf(y)):
                xinfid = isinf(x)
                yinfid = isinf(y)
                if not (xinfid == yinfid).all():
                    return False
                # if one item, x and y is +- inf
                if x.size == y.size == 1:
                    return x == y
                x = x[~xinfid]
                y = y[~yinfid]
        except (TypeError, NotImplementedError):
            pass

        # make sure y is an inexact type to avoid abs(MIN_INT); will cause
        # casting of x later.
        dtype = result_type(y, 1.)
        y = np.asanyarray(y, dtype)
        z = abs(x - y)

        if not issubdtype(z.dtype, number):
            z = z.astype(np.float64)  # handle object arrays

        return z < 1.5 * 10.0**(-decimal)

    assert_array_compare(compare, actual, desired, err_msg=err_msg,
                         verbose=verbose,
             header=('Arrays are not almost equal to %d decimals' % decimal),
             precision=decimal)


def assert_array_less(x, y, err_msg='', verbose=True, *, strict=False):
    """
    Raises an AssertionError if two array_like objects are not ordered by less
    than.

    Given two array_like objects `x` and `y`, check that the shape is equal and
    all elements of `x` are strictly less than the corresponding elements of
    `y` (but see the Notes for the special handling of a scalar). An exception
    is raised at shape mismatch or values that are not correctly ordered. In
    contrast to the  standard usage in NumPy, no assertion is raised if both
    objects have NaNs in the same positions.

    Parameters
    ----------
    x : array_like
      The smaller object to check.
    y : array_like
      The larger object to compare.
    err_msg : string
      The error message to be printed in case of failure.
    verbose : bool
        If True, the conflicting values are appended to the error message.
    strict : bool, optional
        If True, raise an AssertionError when either the shape or the data
        type of the array_like objects does not match. The special
        handling for scalars mentioned in the Notes section is disabled.

        .. versionadded:: 2.0.0

    Raises
    ------
    AssertionError
      If x is not strictly smaller than y, element-wise.

    See Also
    --------
    assert_array_equal: tests objects for equality
    assert_array_almost_equal: test objects for equality up to precision

    Notes
    -----
    When one of `x` and `y` is a scalar and the other is array_like, the
    function performs the comparison as though the scalar were broadcasted
    to the shape of the array. This behaviour can be disabled with the `strict`
    parameter.

    Examples
    --------
    The following assertion passes because each finite element of `x` is
    strictly less than the corresponding element of `y`, and the NaNs are in
    corresponding locations.

    >>> x = [1.0, 1.0, np.nan]
    >>> y = [1.1, 2.0, np.nan]
    >>> np.testing.assert_array_less(x, y)

    The following assertion fails because the zeroth element of `x` is no
    longer strictly less than the zeroth element of `y`.

    >>> y[0] = 1
    >>> np.testing.assert_array_less(x, y)
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not strictly ordered `x < y`
    <BLANKLINE>
    Mismatched elements: 1 / 3 (33.3%)
    Max absolute difference among violations: 0.
    Max relative difference among violations: 0.
     x: array([ 1.,  1., nan])
     y: array([ 1.,  2., nan])

    Here, `y` is a scalar, so each element of `x` is compared to `y`, and
    the assertion passes.

    >>> x = [1.0, 4.0]
    >>> y = 5.0
    >>> np.testing.assert_array_less(x, y)

    However, with ``strict=True``, the assertion will fail because the shapes
    do not match.

    >>> np.testing.assert_array_less(x, y, strict=True)
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not strictly ordered `x < y`
    <BLANKLINE>
    (shapes (2,), () mismatch)
     x: array([1., 4.])
     y: array(5.)

    With ``strict=True``, the assertion also fails if the dtypes of the two
    arrays do not match.

    >>> y = [5, 5]
    >>> np.testing.assert_array_less(x, y, strict=True)
    Traceback (most recent call last):
        ...
    AssertionError:
    Arrays are not strictly ordered `x < y`
    <BLANKLINE>
    (dtypes float64, int64 mismatch)
     x: array([1., 4.])
     y: array([5, 5])
    """
    __tracebackhide__ = True  # Hide traceback for py.test
    assert_array_compare(operator.__lt__, x, y, err_msg=err_msg,
                         verbose=verbose,
                         header='Arrays are not strictly ordered `x < y`',
                         equal_inf=False,
                         strict=strict,
                         names=('x', 'y'))


def runstring(astr, dict):
    exec(astr, dict)


def assert_string_equal(actual, desired):
    """
    Test if two strings are equal.

    If the given strings are equal, `assert_string_equal` does nothing.
    If they are not equal, an AssertionError is raised, and the diff
    between the strings is shown.

    Parameters
    ----------
    actual : str
        The string to test for equality against the expected string.
    desired : str
        The expected string.

    Examples
    --------
    >>> np.testing.assert_string_equal('abc', 'abc')
    >>> np.testing.assert_string_equal('abc', 'abcd')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    ...
    AssertionError: Differences in strings:
    - abc+ abcd?    +

    """
    # delay import of difflib to reduce startup time
    __tracebackhide__ = True  # Hide traceback for py.test
    import difflib

    if not isinstance(actual, str):
        raise AssertionError(repr(type(actual)))
    if not isinstance(desired, str):
        raise AssertionError(repr(type(desired)))
    if desired == actual:
        return

    diff = list(difflib.Differ().compare(actual.splitlines(True),
                desired.splitlines(True)))
    diff_list = []
    while diff:
        d1 = diff.pop(0)
        if d1.startswith('  '):
            continue
        if d1.startswith('- '):
            l = [d1]
            d2 = diff.pop(0)
            if d2.startswith('? '):
                l.append(d2)
                d2 = diff.pop(0)
            if not d2.startswith('+ '):
                raise AssertionError(repr(d2))
            l.append(d2)
            if diff:
                d3 = diff.pop(0)
                if d3.startswith('? '):
                    l.append(d3)
                else:
                    diff.insert(0, d3)
            if d2[2:] == d1[2:]:
                continue
            diff_list.extend(l)
            continue
        raise AssertionError(repr(d1))
    if not diff_list:
        return
    msg = f"Differences in strings:\n{''.join(diff_list).rstrip()}"
    if actual != desired:
        raise AssertionError(msg)


def rundocs(filename=None, raise_on_error=True):
    """
    Run doctests found in the given file.

    By default `rundocs` raises an AssertionError on failure.

    Parameters
    ----------
    filename : str
        The path to the file for which the doctests are run.
    raise_on_error : bool
        Whether to raise an AssertionError when a doctest fails. Default is
        True.

    Notes
    -----
    The doctests can be run by the user/developer by adding the ``doctests``
    argument to the ``test()`` call. For example, to run all tests (including
    doctests) for ``numpy.lib``:

    >>> np.lib.test(doctests=True)  # doctest: +SKIP
    """
    import doctest

    from numpy.distutils.misc_util import exec_mod_from_location
    if filename is None:
        f = sys._getframe(1)
        filename = f.f_globals['__file__']
    name = os.path.splitext(os.path.basename(filename))[0]
    m = exec_mod_from_location(name, filename)

    tests = doctest.DocTestFinder().find(m)
    runner = doctest.DocTestRunner(verbose=False)

    msg = []
    if raise_on_error:
        out = msg.append
    else:
        out = None

    for test in tests:
        runner.run(test, out=out)

    if runner.failures > 0 and raise_on_error:
        raise AssertionError("Some doctests failed:\n%s" % "\n".join(msg))


def check_support_sve(__cache=[]):
    """
    gh-22982
    """

    if __cache:
        return __cache[0]

    import subprocess
    cmd = 'lscpu'
    try:
        output = subprocess.run(cmd, capture_output=True, text=True)
        result = 'sve' in output.stdout
    except (OSError, subprocess.SubprocessError):
        result = False
    __cache.append(result)
    return __cache[0]


#
# assert_raises and assert_raises_regex are taken from unittest.
#
import unittest


class _Dummy(unittest.TestCase):
    def nop(self):
        pass


_d = _Dummy('nop')


def assert_raises(*args, **kwargs):
    """
    assert_raises(exception_class, callable, *args, **kwargs)
    assert_raises(exception_class)

    Fail unless an exception of class exception_class is thrown
    by callable when invoked with arguments args and keyword
    arguments kwargs. If a different type of exception is
    thrown, it will not be caught, and the test case will be
    deemed to have suffered an error, exactly as for an
    unexpected exception.

    Alternatively, `assert_raises` can be used as a context manager:

    >>> from numpy.testing import assert_raises
    >>> with assert_raises(ZeroDivisionError):
    ...     1 / 0

    is equivalent to

    >>> def div(x, y):
    ...     return x / y
    >>> assert_raises(ZeroDivisionError, div, 1, 0)

    """
    __tracebackhide__ = True  # Hide traceback for py.test
    return _d.assertRaises(*args, **kwargs)


def assert_raises_regex(exception_class, expected_regexp, *args, **kwargs):
    """
    assert_raises_regex(exception_class, expected_regexp, callable, *args,
                        **kwargs)
    assert_raises_regex(exception_class, expected_regexp)

    Fail unless an exception of class exception_class and with message that
    matches expected_regexp is thrown by callable when invoked with arguments
    args and keyword arguments kwargs.

    Alternatively, can be used as a context manager like `assert_raises`.
    """
    __tracebackhide__ = True  # Hide traceback for py.test
    return _d.assertRaisesRegex(exception_class, expected_regexp, *args, **kwargs)


def decorate_methods(cls, decorator, testmatch=None):
    """
    Apply a decorator to all methods in a class matching a regular expression.

    The given decorator is applied to all public methods of `cls` that are
    matched by the regular expression `testmatch`
    (``testmatch.search(methodname)``). Methods that are private, i.e. start
    with an underscore, are ignored.

    Parameters
    ----------
    cls : class
        Class whose methods to decorate.
    decorator : function
        Decorator to apply to methods
    testmatch : compiled regexp or str, optional
        The regular expression. Default value is None, in which case the
        nose default (``re.compile(r'(?:^|[\\b_\\.%s-])[Tt]est' % os.sep)``)
        is used.
        If `testmatch` is a string, it is compiled to a regular expression
        first.

    """
    if testmatch is None:
        testmatch = re.compile(r'(?:^|[\\b_\\.%s-])[Tt]est' % os.sep)
    else:
        testmatch = re.compile(testmatch)
    cls_attr = cls.__dict__

    # delayed import to reduce startup time
    from inspect import isfunction

    methods = [_m for _m in cls_attr.values() if isfunction(_m)]
    for function in methods:
        try:
            if hasattr(function, 'compat_func_name'):
                funcname = function.compat_func_name
            else:
                funcname = function.__name__
        except AttributeError:
            # not a function
            continue
        if testmatch.search(funcname) and not funcname.startswith('_'):
            setattr(cls, funcname, decorator(function))


def measure(code_str, times=1, label=None):
    """
    Return elapsed time for executing code in the namespace of the caller.

    The supplied code string is compiled with the Python builtin ``compile``.
    The precision of the timing is 10 milli-seconds. If the code will execute
    fast on this timescale, it can be executed many times to get reasonable
    timing accuracy.

    Parameters
    ----------
    code_str : str
        The code to be timed.
    times : int, optional
        The number of times the code is executed. Default is 1. The code is
        only compiled once.
    label : str, optional
        A label to identify `code_str` with. This is passed into ``compile``
        as the second argument (for run-time error messages).

    Returns
    -------
    elapsed : float
        Total elapsed time in seconds for executing `code_str` `times` times.

    Examples
    --------
    >>> times = 10
    >>> etime = np.testing.measure('for i in range(1000): np.sqrt(i**2)', times=times)
    >>> print("Time for a single execution : ", etime / times, "s")  # doctest: +SKIP
    Time for a single execution :  0.005 s

    """
    frame = sys._getframe(1)
    locs, globs = frame.f_locals, frame.f_globals

    code = compile(code_str, f'Test name: {label} ', 'exec')
    i = 0
    elapsed = jiffies()
    while i < times:
        i += 1
        exec(code, globs, locs)
    elapsed = jiffies() - elapsed
    return 0.01 * elapsed


def _assert_valid_refcount(op):
    """
    Check that ufuncs don't mishandle refcount of object `1`.
    Used in a few regression tests.
    """
    if not HAS_REFCOUNT:
        return True

    import gc

    import numpy as np

    b = np.arange(100 * 100).reshape(100, 100)
    c = b
    i = 1

    gc.disable()
    try:
        rc = sys.getrefcount(i)
        for j in range(15):
            d = op(b, c)
        assert_(sys.getrefcount(i) >= rc)
    finally:
        gc.enable()


def assert_allclose(actual, desired, rtol=1e-7, atol=0, equal_nan=True,
                    err_msg='', verbose=True, *, strict=False):
    """
    Raises an AssertionError if two objects are not equal up to desired
    tolerance.

    Given two array_like objects, check that their shapes and all elements
    are equal (but see the Notes for the special handling of a scalar). An
    exception is raised if the shapes mismatch or any values conflict. In
    contrast to the standard usage in numpy, NaNs are compared like numbers,
    no assertion is raised if both objects have NaNs in the same positions.

    The test is equivalent to ``allclose(actual, desired, rtol, atol)`` (note
    that ``allclose`` has different default values). It compares the difference
    between `actual` and `desired` to ``atol + rtol * abs(desired)``.

    Parameters
    ----------
    actual : array_like
        Array obtained.
    desired : array_like
        Array desired.
    rtol : float, optional
        Relative tolerance.
    atol : float, optional
        Absolute tolerance.
    equal_nan : bool, optional.
        If True, NaNs will compare equal.
    err_msg : str, optional
        The error message to be printed in case of failure.
    verbose : bool, optional
        If True, the conflicting values are appended to the error message.
    strict : bool, optional
        If True, raise an ``AssertionError`` when either the shape or the data
        type of the arguments does not match. The special handling of scalars
        mentioned in the Notes section is disabled.

        .. versionadded:: 2.0.0

    Raises
    ------
    AssertionError
        If actual and desired are not equal up to specified precision.

    See Also
    --------
    assert_array_almost_equal_nulp, assert_array_max_ulp

    Notes
    -----
    When one of `actual` and `desired` is a scalar and the other is
    array_like, the function performs the comparison as if the scalar were
    broadcasted to the shape of the array.
    This behaviour can be disabled with the `strict` parameter.

    Examples
    --------
    >>> x = [1e-5, 1e-3, 1e-1]
    >>> y = np.arccos(np.cos(x))
    >>> np.testing.assert_allclose(x, y, rtol=1e-5, atol=0)

    As mentioned in the Notes section, `assert_allclose` has special
    handling for scalars. Here, the test checks that the value of `numpy.sin`
    is nearly zero at integer multiples of π.

    >>> x = np.arange(3) * np.pi
    >>> np.testing.assert_allclose(np.sin(x), 0, atol=1e-15)

    Use `strict` to raise an ``AssertionError`` when comparing an array
    with one or more dimensions against a scalar.

    >>> np.testing.assert_allclose(np.sin(x), 0, atol=1e-15, strict=True)
    Traceback (most recent call last):
        ...
    AssertionError:
    Not equal to tolerance rtol=1e-07, atol=1e-15
    <BLANKLINE>
    (shapes (3,), () mismatch)
     ACTUAL: array([ 0.000000e+00,  1.224647e-16, -2.449294e-16])
     DESIRED: array(0)

    The `strict` parameter also ensures that the array data types match:

    >>> y = np.zeros(3, dtype=np.float32)
    >>> np.testing.assert_allclose(np.sin(x), y, atol=1e-15, strict=True)
    Traceback (most recent call last):
        ...
    AssertionError:
    Not equal to tolerance rtol=1e-07, atol=1e-15
    <BLANKLINE>
    (dtypes float64, float32 mismatch)
     ACTUAL: array([ 0.000000e+00,  1.224647e-16, -2.449294e-16])
     DESIRED: array([0., 0., 0.], dtype=float32)

    """
    __tracebackhide__ = True  # Hide traceback for py.test
    import numpy as np

    def compare(x, y):
        return np._core.numeric.isclose(x, y, rtol=rtol, atol=atol,
                                       equal_nan=equal_nan)

    actual, desired = np.asanyarray(actual), np.asanyarray(desired)
    header = f'Not equal to tolerance rtol={rtol:g}, atol={atol:g}'
    assert_array_compare(compare, actual, desired, err_msg=str(err_msg),
                         verbose=verbose, header=header, equal_nan=equal_nan,
                         strict=strict)


def assert_array_almost_equal_nulp(x, y, nulp=1):
    """
    Compare two arrays relatively to their spacing.

    This is a relatively robust method to compare two arrays whose amplitude
    is variable.

    Parameters
    ----------
    x, y : array_like
        Input arrays.
    nulp : int, optional
        The maximum number of unit in the last place for tolerance (see Notes).
        Default is 1.

    Returns
    -------
    None

    Raises
    ------
    AssertionError
        If the spacing between `x` and `y` for one or more elements is larger
        than `nulp`.

    See Also
    --------
    assert_array_max_ulp : Check that all items of arrays differ in at most
        N Units in the Last Place.
    spacing : Return the distance between x and the nearest adjacent number.

    Notes
    -----
    An assertion is raised if the following condition is not met::

        abs(x - y) <= nulp * spacing(maximum(abs(x), abs(y)))

    Examples
    --------
    >>> x = np.array([1., 1e-10, 1e-20])
    >>> eps = np.finfo(x.dtype).eps
    >>> np.testing.assert_array_almost_equal_nulp(x, x*eps/2 + x)

    >>> np.testing.assert_array_almost_equal_nulp(x, x*eps + x)
    Traceback (most recent call last):
      ...
    AssertionError: Arrays are not equal to 1 ULP (max is 2)

    """
    __tracebackhide__ = True  # Hide traceback for py.test
    import numpy as np
    ax = np.abs(x)
    ay = np.abs(y)
    ref = nulp * np.spacing(np.where(ax > ay, ax, ay))
    if not np.all(np.abs(x - y) <= ref):
        if np.iscomplexobj(x) or np.iscomplexobj(y):
            msg = f"Arrays are not equal to {nulp} ULP"
        else:
            max_nulp = np.max(nulp_diff(x, y))
            msg = f"Arrays are not equal to {nulp} ULP (max is {max_nulp:g})"
        raise AssertionError(msg)


def assert_array_max_ulp(a, b, maxulp=1, dtype=None):
    """
    Check that all items of arrays differ in at most N Units in the Last Place.

    Parameters
    ----------
    a, b : array_like
        Input arrays to be compared.
    maxulp : int, optional
        The maximum number of units in the last place that elements of `a` and
        `b` can differ. Default is 1.
    dtype : dtype, optional
        Data-type to convert `a` and `b` to if given. Default is None.

    Returns
    -------
    ret : ndarray
        Array containing number of representable floating point numbers between
        items in `a` and `b`.

    Raises
    ------
    AssertionError
        If one or more elements differ by more than `maxulp`.

    Notes
    -----
    For computing the ULP difference, this API does not differentiate between
    various representations of NAN (ULP difference between 0x7fc00000 and 0xffc00000
    is zero).

    See Also
    --------
    assert_array_almost_equal_nulp : Compare two arrays relatively to their
        spacing.

    Examples
    --------
    >>> a = np.linspace(0., 1., 100)
    >>> res = np.testing.assert_array_max_ulp(a, np.arcsin(np.sin(a)))

    """
    __tracebackhide__ = True  # Hide traceback for py.test
    import numpy as np
    ret = nulp_diff(a, b, dtype)
    if not np.all(ret <= maxulp):
        raise AssertionError("Arrays are not almost equal up to %g "
                             "ULP (max difference is %g ULP)" %
                             (maxulp, np.max(ret)))
    return ret


def nulp_diff(x, y, dtype=None):
    """For each item in x and y, return the number of representable floating
    points between them.

    Parameters
    ----------
    x : array_like
        first input array
    y : array_like
        second input array
    dtype : dtype, optional
        Data-type to convert `x` and `y` to if given. Default is None.

    Returns
    -------
    nulp : array_like
        number of representable floating point numbers between each item in x
        and y.

    Notes
    -----
    For computing the ULP difference, this API does not differentiate between
    various representations of NAN (ULP difference between 0x7fc00000 and 0xffc00000
    is zero).

    Examples
    --------
    # By definition, epsilon is the smallest number such as 1 + eps != 1, so
    # there should be exactly one ULP between 1 and 1 + eps
    >>> nulp_diff(1, 1 + np.finfo(x.dtype).eps)
    1.0
    """
    import numpy as np
    if dtype:
        x = np.asarray(x, dtype=dtype)
        y = np.asarray(y, dtype=dtype)
    else:
        x = np.asarray(x)
        y = np.asarray(y)

    t = np.common_type(x, y)
    if np.iscomplexobj(x) or np.iscomplexobj(y):
        raise NotImplementedError("_nulp not implemented for complex array")

    x = np.array([x], dtype=t)
    y = np.array([y], dtype=t)

    x[np.isnan(x)] = np.nan
    y[np.isnan(y)] = np.nan

    if not x.shape == y.shape:
        raise ValueError(f"Arrays do not have the same shape: {x.shape} - {y.shape}")

    def _diff(rx, ry, vdt):
        diff = np.asarray(rx - ry, dtype=vdt)
        return np.abs(diff)

    rx = integer_repr(x)
    ry = integer_repr(y)
    return _diff(rx, ry, t)


def _integer_repr(x, vdt, comp):
    # Reinterpret binary representation of the float as sign-magnitude:
    # take into account two-complement representation
    # See also
    # https://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/
    rx = x.view(vdt)
    if not (rx.size == 1):
        rx[rx < 0] = comp - rx[rx < 0]
    elif rx < 0:
        rx = comp - rx

    return rx


def integer_repr(x):
    """Return the signed-magnitude interpretation of the binary representation
    of x."""
    import numpy as np
    if x.dtype == np.float16:
        return _integer_repr(x, np.int16, np.int16(-2**15))
    elif x.dtype == np.float32:
        return _integer_repr(x, np.int32, np.int32(-2**31))
    elif x.dtype == np.float64:
        return _integer_repr(x, np.int64, np.int64(-2**63))
    else:
        raise ValueError(f'Unsupported dtype {x.dtype}')


@contextlib.contextmanager
def _assert_warns_context(warning_class, name=None):
    __tracebackhide__ = True  # Hide traceback for py.test
    with suppress_warnings() as sup:
        l = sup.record(warning_class)
        yield
        if not len(l) > 0:
            name_str = f' when calling {name}' if name is not None else ''
            raise AssertionError("No warning raised" + name_str)


def assert_warns(warning_class, *args, **kwargs):
    """
    Fail unless the given callable throws the specified warning.

    A warning of class warning_class should be thrown by the callable when
    invoked with arguments args and keyword arguments kwargs.
    If a different type of warning is thrown, it will not be caught.

    If called with all arguments other than the warning class omitted, may be
    used as a context manager::

        with assert_warns(SomeWarning):
            do_something()

    The ability to be used as a context manager is new in NumPy v1.11.0.

    Parameters
    ----------
    warning_class : class
        The class defining the warning that `func` is expected to throw.
    func : callable, optional
        Callable to test
    *args : Arguments
        Arguments for `func`.
    **kwargs : Kwargs
        Keyword arguments for `func`.

    Returns
    -------
    The value returned by `func`.

    Examples
    --------
    >>> import warnings
    >>> def deprecated_func(num):
    ...     warnings.warn("Please upgrade", DeprecationWarning)
    ...     return num*num
    >>> with np.testing.assert_warns(DeprecationWarning):
    ...     assert deprecated_func(4) == 16
    >>> # or passing a func
    >>> ret = np.testing.assert_warns(DeprecationWarning, deprecated_func, 4)
    >>> assert ret == 16
    """
    if not args and not kwargs:
        return _assert_warns_context(warning_class)
    elif len(args) < 1:
        if "match" in kwargs:
            raise RuntimeError(
                "assert_warns does not use 'match' kwarg, "
                "use pytest.warns instead"
                )
        raise RuntimeError("assert_warns(...) needs at least one arg")

    func = args[0]
    args = args[1:]
    with _assert_warns_context(warning_class, name=func.__name__):
        return func(*args, **kwargs)


@contextlib.contextmanager
def _assert_no_warnings_context(name=None):
    __tracebackhide__ = True  # Hide traceback for py.test
    with warnings.catch_warnings(record=True) as l:
        warnings.simplefilter('always')
        yield
        if len(l) > 0:
            name_str = f' when calling {name}' if name is not None else ''
            raise AssertionError(f'Got warnings{name_str}: {l}')


def assert_no_warnings(*args, **kwargs):
    """
    Fail if the given callable produces any warnings.

    If called with all arguments omitted, may be used as a context manager::

        with assert_no_warnings():
            do_something()

    The ability to be used as a context manager is new in NumPy v1.11.0.

    Parameters
    ----------
    func : callable
        The callable to test.
    \\*args : Arguments
        Arguments passed to `func`.
    \\*\\*kwargs : Kwargs
        Keyword arguments passed to `func`.

    Returns
    -------
    The value returned by `func`.

    """
    if not args:
        return _assert_no_warnings_context()

    func = args[0]
    args = args[1:]
    with _assert_no_warnings_context(name=func.__name__):
        return func(*args, **kwargs)


def _gen_alignment_data(dtype=float32, type='binary', max_size=24):
    """
    generator producing data with different alignment and offsets
    to test simd vectorization

    Parameters
    ----------
    dtype : dtype
        data type to produce
    type : string
        'unary': create data for unary operations, creates one input
                 and output array
        'binary': create data for unary operations, creates two input
                 and output array
    max_size : integer
        maximum size of data to produce

    Returns
    -------
    if type is 'unary' yields one output, one input array and a message
    containing information on the data
    if type is 'binary' yields one output array, two input array and a message
    containing information on the data

    """
    ufmt = 'unary offset=(%d, %d), size=%d, dtype=%r, %s'
    bfmt = 'binary offset=(%d, %d, %d), size=%d, dtype=%r, %s'
    for o in range(3):
        for s in range(o + 2, max(o + 3, max_size)):
            if type == 'unary':
                inp = lambda: arange(s, dtype=dtype)[o:]
                out = empty((s,), dtype=dtype)[o:]
                yield out, inp(), ufmt % (o, o, s, dtype, 'out of place')
                d = inp()
                yield d, d, ufmt % (o, o, s, dtype, 'in place')
                yield out[1:], inp()[:-1], ufmt % \
                    (o + 1, o, s - 1, dtype, 'out of place')
                yield out[:-1], inp()[1:], ufmt % \
                    (o, o + 1, s - 1, dtype, 'out of place')
                yield inp()[:-1], inp()[1:], ufmt % \
                    (o, o + 1, s - 1, dtype, 'aliased')
                yield inp()[1:], inp()[:-1], ufmt % \
                    (o + 1, o, s - 1, dtype, 'aliased')
            if type == 'binary':
                inp1 = lambda: arange(s, dtype=dtype)[o:]
                inp2 = lambda: arange(s, dtype=dtype)[o:]
                out = empty((s,), dtype=dtype)[o:]
                yield out, inp1(), inp2(), bfmt % \
                    (o, o, o, s, dtype, 'out of place')
                d = inp1()
                yield d, d, inp2(), bfmt % \
                    (o, o, o, s, dtype, 'in place1')
                d = inp2()
                yield d, inp1(), d, bfmt % \
                    (o, o, o, s, dtype, 'in place2')
                yield out[1:], inp1()[:-1], inp2()[:-1], bfmt % \
                    (o + 1, o, o, s - 1, dtype, 'out of place')
                yield out[:-1], inp1()[1:], inp2()[:-1], bfmt % \
                    (o, o + 1, o, s - 1, dtype, 'out of place')
                yield out[:-1], inp1()[:-1], inp2()[1:], bfmt % \
                    (o, o, o + 1, s - 1, dtype, 'out of place')
                yield inp1()[1:], inp1()[:-1], inp2()[:-1], bfmt % \
                    (o + 1, o, o, s - 1, dtype, 'aliased')
                yield inp1()[:-1], inp1()[1:], inp2()[:-1], bfmt % \
                    (o, o + 1, o, s - 1, dtype, 'aliased')
                yield inp1()[:-1], inp1()[:-1], inp2()[1:], bfmt % \
                    (o, o, o + 1, s - 1, dtype, 'aliased')


class IgnoreException(Exception):
    "Ignoring this exception due to disabled feature"
    pass


@contextlib.contextmanager
def tempdir(*args, **kwargs):
    """Context manager to provide a temporary test folder.

    All arguments are passed as this to the underlying tempfile.mkdtemp
    function.

    """
    tmpdir = mkdtemp(*args, **kwargs)
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir)


@contextlib.contextmanager
def temppath(*args, **kwargs):
    """Context manager for temporary files.

    Context manager that returns the path to a closed temporary file. Its
    parameters are the same as for tempfile.mkstemp and are passed directly
    to that function. The underlying file is removed when the context is
    exited, so it should be closed at that time.

    Windows does not allow a temporary file to be opened if it is already
    open, so the underlying file must be closed after opening before it
    can be opened again.

    """
    fd, path = mkstemp(*args, **kwargs)
    os.close(fd)
    try:
        yield path
    finally:
        os.remove(path)


class clear_and_catch_warnings(warnings.catch_warnings):
    """ Context manager that resets warning registry for catching warnings

    Warnings can be slippery, because, whenever a warning is triggered, Python
    adds a ``__warningregistry__`` member to the *calling* module.  This makes
    it impossible to retrigger the warning in this module, whatever you put in
    the warnings filters.  This context manager accepts a sequence of `modules`
    as a keyword argument to its constructor and:

    * stores and removes any ``__warningregistry__`` entries in given `modules`
      on entry;
    * resets ``__warningregistry__`` to its previous state on exit.

    This makes it possible to trigger any warning afresh inside the context
    manager without disturbing the state of warnings outside.

    For compatibility with Python, please consider all arguments to be
    keyword-only.

    Parameters
    ----------
    record : bool, optional
        Specifies whether warnings should be captured by a custom
        implementation of ``warnings.showwarning()`` and be appended to a list
        returned by the context manager. Otherwise None is returned by the
        context manager. The objects appended to the list are arguments whose
        attributes mirror the arguments to ``showwarning()``.
    modules : sequence, optional
        Sequence of modules for which to reset warnings registry on entry and
        restore on exit. To work correctly, all 'ignore' filters should
        filter by one of these modules.

    Examples
    --------
    >>> import warnings
    >>> with np.testing.clear_and_catch_warnings(
    ...         modules=[np._core.fromnumeric]):
    ...     warnings.simplefilter('always')
    ...     warnings.filterwarnings('ignore', module='np._core.fromnumeric')
    ...     # do something that raises a warning but ignore those in
    ...     # np._core.fromnumeric
    """
    class_modules = ()

    def __init__(self, record=False, modules=()):
        self.modules = set(modules).union(self.class_modules)
        self._warnreg_copies = {}
        super().__init__(record=record)

    def __enter__(self):
        for mod in self.modules:
            if hasattr(mod, '__warningregistry__'):
                mod_reg = mod.__warningregistry__
                self._warnreg_copies[mod] = mod_reg.copy()
                mod_reg.clear()
        return super().__enter__()

    def __exit__(self, *exc_info):
        super().__exit__(*exc_info)
        for mod in self.modules:
            if hasattr(mod, '__warningregistry__'):
                mod.__warningregistry__.clear()
            if mod in self._warnreg_copies:
                mod.__warningregistry__.update(self._warnreg_copies[mod])


class suppress_warnings:
    """
    Context manager and decorator doing much the same as
    ``warnings.catch_warnings``.

    However, it also provides a filter mechanism to work around
    https://bugs.python.org/issue4180.

    This bug causes Python before 3.4 to not reliably show warnings again
    after they have been ignored once (even within catch_warnings). It
    means that no "ignore" filter can be used easily, since following
    tests might need to see the warning. Additionally it allows easier
    specificity for testing warnings and can be nested.

    Parameters
    ----------
    forwarding_rule : str, optional
        One of "always", "once", "module", or "location". Analogous to
        the usual warnings module filter mode, it is useful to reduce
        noise mostly on the outmost level. Unsuppressed and unrecorded
        warnings will be forwarded based on this rule. Defaults to "always".
        "location" is equivalent to the warnings "default", match by exact
        location the warning warning originated from.

    Notes
    -----
    Filters added inside the context manager will be discarded again
    when leaving it. Upon entering all filters defined outside a
    context will be applied automatically.

    When a recording filter is added, matching warnings are stored in the
    ``log`` attribute as well as in the list returned by ``record``.

    If filters are added and the ``module`` keyword is given, the
    warning registry of this module will additionally be cleared when
    applying it, entering the context, or exiting it. This could cause
    warnings to appear a second time after leaving the context if they
    were configured to be printed once (default) and were already
    printed before the context was entered.

    Nesting this context manager will work as expected when the
    forwarding rule is "always" (default). Unfiltered and unrecorded
    warnings will be passed out and be matched by the outer level.
    On the outmost level they will be printed (or caught by another
    warnings context). The forwarding rule argument can modify this
    behaviour.

    Like ``catch_warnings`` this context manager is not threadsafe.

    Examples
    --------

    With a context manager::

        with np.testing.suppress_warnings() as sup:
            sup.filter(DeprecationWarning, "Some text")
            sup.filter(module=np.ma.core)
            log = sup.record(FutureWarning, "Does this occur?")
            command_giving_warnings()
            # The FutureWarning was given once, the filtered warnings were
            # ignored. All other warnings abide outside settings (may be
            # printed/error)
            assert_(len(log) == 1)
            assert_(len(sup.log) == 1)  # also stored in log attribute

    Or as a decorator::

        sup = np.testing.suppress_warnings()
        sup.filter(module=np.ma.core)  # module must match exactly
        @sup
        def some_function():
            # do something which causes a warning in np.ma.core
            pass
    """
    def __init__(self, forwarding_rule="always"):
        self._entered = False

        # Suppressions are either instance or defined inside one with block:
        self._suppressions = []

        if forwarding_rule not in {"always", "module", "once", "location"}:
            raise ValueError("unsupported forwarding rule.")
        self._forwarding_rule = forwarding_rule

    def _clear_registries(self):
        if hasattr(warnings, "_filters_mutated"):
            # clearing the registry should not be necessary on new pythons,
            # instead the filters should be mutated.
            warnings._filters_mutated()
            return
        # Simply clear the registry, this should normally be harmless,
        # note that on new pythons it would be invalidated anyway.
        for module in self._tmp_modules:
            if hasattr(module, "__warningregistry__"):
                module.__warningregistry__.clear()

    def _filter(self, category=Warning, message="", module=None, record=False):
        if record:
            record = []  # The log where to store warnings
        else:
            record = None
        if self._entered:
            if module is None:
                warnings.filterwarnings(
                    "always", category=category, message=message)
            else:
                module_regex = module.__name__.replace('.', r'\.') + '$'
                warnings.filterwarnings(
                    "always", category=category, message=message,
                    module=module_regex)
                self._tmp_modules.add(module)
                self._clear_registries()

            self._tmp_suppressions.append(
                (category, message, re.compile(message, re.I), module, record))
        else:
            self._suppressions.append(
                (category, message, re.compile(message, re.I), module, record))

        return record

    def filter(self, category=Warning, message="", module=None):
        """
        Add a new suppressing filter or apply it if the state is entered.

        Parameters
        ----------
        category : class, optional
            Warning class to filter
        message : string, optional
            Regular expression matching the warning message.
        module : module, optional
            Module to filter for. Note that the module (and its file)
            must match exactly and cannot be a submodule. This may make
            it unreliable for external modules.

        Notes
        -----
        When added within a context, filters are only added inside
        the context and will be forgotten when the context is exited.
        """
        self._filter(category=category, message=message, module=module,
                     record=False)

    def record(self, category=Warning, message="", module=None):
        """
        Append a new recording filter or apply it if the state is entered.

        All warnings matching will be appended to the ``log`` attribute.

        Parameters
        ----------
        category : class, optional
            Warning class to filter
        message : string, optional
            Regular expression matching the warning message.
        module : module, optional
            Module to filter for. Note that the module (and its file)
            must match exactly and cannot be a submodule. This may make
            it unreliable for external modules.

        Returns
        -------
        log : list
            A list which will be filled with all matched warnings.

        Notes
        -----
        When added within a context, filters are only added inside
        the context and will be forgotten when the context is exited.
        """
        return self._filter(category=category, message=message, module=module,
                            record=True)

    def __enter__(self):
        if self._entered:
            raise RuntimeError("cannot enter suppress_warnings twice.")

        self._orig_show = warnings.showwarning
        self._filters = warnings.filters
        warnings.filters = self._filters[:]

        self._entered = True
        self._tmp_suppressions = []
        self._tmp_modules = set()
        self._forwarded = set()

        self.log = []  # reset global log (no need to keep same list)

        for cat, mess, _, mod, log in self._suppressions:
            if log is not None:
                del log[:]  # clear the log
            if mod is None:
                warnings.filterwarnings(
                    "always", category=cat, message=mess)
            else:
                module_regex = mod.__name__.replace('.', r'\.') + '$'
                warnings.filterwarnings(
                    "always", category=cat, message=mess,
                    module=module_regex)
                self._tmp_modules.add(mod)
        warnings.showwarning = self._showwarning
        self._clear_registries()

        return self

    def __exit__(self, *exc_info):
        warnings.showwarning = self._orig_show
        warnings.filters = self._filters
        self._clear_registries()
        self._entered = False
        del self._orig_show
        del self._filters

    def _showwarning(self, message, category, filename, lineno,
                     *args, use_warnmsg=None, **kwargs):
        for cat, _, pattern, mod, rec in (
                self._suppressions + self._tmp_suppressions)[::-1]:
            if (issubclass(category, cat) and
                    pattern.match(message.args[0]) is not None):
                if mod is None:
                    # Message and category match, either recorded or ignored
                    if rec is not None:
                        msg = WarningMessage(message, category, filename,
                                             lineno, **kwargs)
                        self.log.append(msg)
                        rec.append(msg)
                    return
                # Use startswith, because warnings strips the c or o from
                # .pyc/.pyo files.
                elif mod.__file__.startswith(filename):
                    # The message and module (filename) match
                    if rec is not None:
                        msg = WarningMessage(message, category, filename,
                                             lineno, **kwargs)
                        self.log.append(msg)
                        rec.append(msg)
                    return

        # There is no filter in place, so pass to the outside handler
        # unless we should only pass it once
        if self._forwarding_rule == "always":
            if use_warnmsg is None:
                self._orig_show(message, category, filename, lineno,
                                *args, **kwargs)
            else:
                self._orig_showmsg(use_warnmsg)
            return

        if self._forwarding_rule == "once":
            signature = (message.args, category)
        elif self._forwarding_rule == "module":
            signature = (message.args, category, filename)
        elif self._forwarding_rule == "location":
            signature = (message.args, category, filename, lineno)

        if signature in self._forwarded:
            return
        self._forwarded.add(signature)
        if use_warnmsg is None:
            self._orig_show(message, category, filename, lineno, *args,
                            **kwargs)
        else:
            self._orig_showmsg(use_warnmsg)

    def __call__(self, func):
        """
        Function decorator to apply certain suppressions to a whole
        function.
        """
        @wraps(func)
        def new_func(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return new_func


@contextlib.contextmanager
def _assert_no_gc_cycles_context(name=None):
    __tracebackhide__ = True  # Hide traceback for py.test

    # not meaningful to test if there is no refcounting
    if not HAS_REFCOUNT:
        yield
        return

    assert_(gc.isenabled())
    gc.disable()
    gc_debug = gc.get_debug()
    try:
        for i in range(100):
            if gc.collect() == 0:
                break
        else:
            raise RuntimeError(
                "Unable to fully collect garbage - perhaps a __del__ method "
                "is creating more reference cycles?")

        gc.set_debug(gc.DEBUG_SAVEALL)
        yield
        # gc.collect returns the number of unreachable objects in cycles that
        # were found -- we are checking that no cycles were created in the context
        n_objects_in_cycles = gc.collect()
        objects_in_cycles = gc.garbage[:]
    finally:
        del gc.garbage[:]
        gc.set_debug(gc_debug)
        gc.enable()

    if n_objects_in_cycles:
        name_str = f' when calling {name}' if name is not None else ''
        raise AssertionError(
            "Reference cycles were found{}: {} objects were collected, "
            "of which {} are shown below:{}"
            .format(
                name_str,
                n_objects_in_cycles,
                len(objects_in_cycles),
                ''.join(
                    "\n  {} object with id={}:\n    {}".format(
                        type(o).__name__,
                        id(o),
                        pprint.pformat(o).replace('\n', '\n    ')
                    ) for o in objects_in_cycles
                )
            )
        )


def assert_no_gc_cycles(*args, **kwargs):
    """
    Fail if the given callable produces any reference cycles.

    If called with all arguments omitted, may be used as a context manager::

        with assert_no_gc_cycles():
            do_something()

    Parameters
    ----------
    func : callable
        The callable to test.
    \\*args : Arguments
        Arguments passed to `func`.
    \\*\\*kwargs : Kwargs
        Keyword arguments passed to `func`.

    Returns
    -------
    Nothing. The result is deliberately discarded to ensure that all cycles
    are found.

    """
    if not args:
        return _assert_no_gc_cycles_context()

    func = args[0]
    args = args[1:]
    with _assert_no_gc_cycles_context(name=func.__name__):
        func(*args, **kwargs)


def break_cycles():
    """
    Break reference cycles by calling gc.collect
    Objects can call other objects' methods (for instance, another object's
     __del__) inside their own __del__. On PyPy, the interpreter only runs
    between calls to gc.collect, so multiple calls are needed to completely
    release all cycles.
    """

    gc.collect()
    if IS_PYPY:
        # a few more, just to make sure all the finalizers are called
        gc.collect()
        gc.collect()
        gc.collect()
        gc.collect()


def requires_memory(free_bytes):
    """Decorator to skip a test if not enough memory is available"""
    import pytest

    def decorator(func):
        @wraps(func)
        def wrapper(*a, **kw):
            msg = check_free_memory(free_bytes)
            if msg is not None:
                pytest.skip(msg)

            try:
                return func(*a, **kw)
            except MemoryError:
                # Probably ran out of memory regardless: don't regard as failure
                pytest.xfail("MemoryError raised")

        return wrapper

    return decorator


def check_free_memory(free_bytes):
    """
    Check whether `free_bytes` amount of memory is currently free.
    Returns: None if enough memory available, otherwise error message
    """
    env_var = 'NPY_AVAILABLE_MEM'
    env_value = os.environ.get(env_var)
    if env_value is not None:
        try:
            mem_free = _parse_size(env_value)
        except ValueError as exc:
            raise ValueError(f'Invalid environment variable {env_var}: {exc}')

        msg = (f'{free_bytes / 1e9} GB memory required, but environment variable '
               f'NPY_AVAILABLE_MEM={env_value} set')
    else:
        mem_free = _get_mem_available()

        if mem_free is None:
            msg = ("Could not determine available memory; set NPY_AVAILABLE_MEM "
                   "environment variable (e.g. NPY_AVAILABLE_MEM=16GB) to run "
                   "the test.")
            mem_free = -1
        else:
            free_bytes_gb = free_bytes / 1e9
            mem_free_gb = mem_free / 1e9
            msg = f'{free_bytes_gb} GB memory required, but {mem_free_gb} GB available'

    return msg if mem_free < free_bytes else None


def _parse_size(size_str):
    """Convert memory size strings ('12 GB' etc.) to float"""
    suffixes = {'': 1, 'b': 1,
                'k': 1000, 'm': 1000**2, 'g': 1000**3, 't': 1000**4,
                'kb': 1000, 'mb': 1000**2, 'gb': 1000**3, 'tb': 1000**4,
                'kib': 1024, 'mib': 1024**2, 'gib': 1024**3, 'tib': 1024**4}

    pipe_suffixes = "|".join(suffixes.keys())

    size_re = re.compile(fr'^\s*(\d+|\d+\.\d+)\s*({pipe_suffixes})\s*$', re.I)

    m = size_re.match(size_str.lower())
    if not m or m.group(2) not in suffixes:
        raise ValueError(f'value {size_str!r} not a valid size')
    return int(float(m.group(1)) * suffixes[m.group(2)])


def _get_mem_available():
    """Return available memory in bytes, or None if unknown."""
    try:
        import psutil
        return psutil.virtual_memory().available
    except (ImportError, AttributeError):
        pass

    if sys.platform.startswith('linux'):
        info = {}
        with open('/proc/meminfo') as f:
            for line in f:
                p = line.split()
                info[p[0].strip(':').lower()] = int(p[1]) * 1024

        if 'memavailable' in info:
            # Linux >= 3.14
            return info['memavailable']
        else:
            return info['memfree'] + info['cached']

    return None


def _no_tracing(func):
    """
    Decorator to temporarily turn off tracing for the duration of a test.
    Needed in tests that check refcounting, otherwise the tracing itself
    influences the refcounts
    """
    if not hasattr(sys, 'gettrace'):
        return func
    else:
        @wraps(func)
        def wrapper(*args, **kwargs):
            original_trace = sys.gettrace()
            try:
                sys.settrace(None)
                return func(*args, **kwargs)
            finally:
                sys.settrace(original_trace)
        return wrapper


def _get_glibc_version():
    try:
        ver = os.confstr('CS_GNU_LIBC_VERSION').rsplit(' ')[1]
    except Exception:
        ver = '0.0'

    return ver


_glibcver = _get_glibc_version()
_glibc_older_than = lambda x: (_glibcver != '0.0' and _glibcver < x)


def run_threaded(func, max_workers=8, pass_count=False,
                 pass_barrier=False, outer_iterations=1,
                 prepare_args=None):
    """Runs a function many times in parallel"""
    for _ in range(outer_iterations):
        with (concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
              as tpe):
            if prepare_args is None:
                args = []
            else:
                args = prepare_args()
            if pass_barrier:
                barrier = threading.Barrier(max_workers)
                args.append(barrier)
            if pass_count:
                all_args = [(func, i, *args) for i in range(max_workers)]
            else:
                all_args = [(func, *args) for i in range(max_workers)]
            try:
                futures = []
                for arg in all_args:
                    futures.append(tpe.submit(*arg))
            except RuntimeError as e:
                import pytest
                pytest.skip(f"Spawning {max_workers} threads failed with "
                            f"error {e!r} (likely due to resource limits on the "
                            "system running the tests)")
            finally:
                if len(futures) < max_workers and pass_barrier:
                    barrier.abort()
            for f in futures:
                f.result()

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\layout\containers.py ===
"""
Container for the layout.
(Containers can contain other containers or user interface controls.)
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, Callable, Sequence, Union, cast

from prompt_toolkit.application.current import get_app
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import (
    FilterOrBool,
    emacs_insert_mode,
    to_filter,
    vi_insert_mode,
)
from prompt_toolkit.formatted_text import (
    AnyFormattedText,
    StyleAndTextTuples,
    to_formatted_text,
)
from prompt_toolkit.formatted_text.utils import (
    fragment_list_to_text,
    fragment_list_width,
)
from prompt_toolkit.key_binding import KeyBindingsBase
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth, take_using_weights, to_int, to_str

from .controls import (
    DummyControl,
    FormattedTextControl,
    GetLinePrefixCallable,
    UIContent,
    UIControl,
)
from .dimension import (
    AnyDimension,
    Dimension,
    max_layout_dimensions,
    sum_layout_dimensions,
    to_dimension,
)
from .margins import Margin
from .mouse_handlers import MouseHandlers
from .screen import _CHAR_CACHE, Screen, WritePosition
from .utils import explode_text_fragments

if TYPE_CHECKING:
    from typing_extensions import Protocol, TypeGuard

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone


__all__ = [
    "AnyContainer",
    "Container",
    "HorizontalAlign",
    "VerticalAlign",
    "HSplit",
    "VSplit",
    "FloatContainer",
    "Float",
    "WindowAlign",
    "Window",
    "WindowRenderInfo",
    "ConditionalContainer",
    "ScrollOffsets",
    "ColorColumn",
    "to_container",
    "to_window",
    "is_container",
    "DynamicContainer",
]


class Container(metaclass=ABCMeta):
    """
    Base class for user interface layout.
    """

    @abstractmethod
    def reset(self) -> None:
        """
        Reset the state of this container and all the children.
        (E.g. reset scroll offsets, etc...)
        """

    @abstractmethod
    def preferred_width(self, max_available_width: int) -> Dimension:
        """
        Return a :class:`~prompt_toolkit.layout.Dimension` that represents the
        desired width for this container.
        """

    @abstractmethod
    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """
        Return a :class:`~prompt_toolkit.layout.Dimension` that represents the
        desired height for this container.
        """

    @abstractmethod
    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """
        Write the actual content to the screen.

        :param screen: :class:`~prompt_toolkit.layout.screen.Screen`
        :param mouse_handlers: :class:`~prompt_toolkit.layout.mouse_handlers.MouseHandlers`.
        :param parent_style: Style string to pass to the :class:`.Window`
            object. This will be applied to all content of the windows.
            :class:`.VSplit` and :class:`.HSplit` can use it to pass their
            style down to the windows that they contain.
        :param z_index: Used for propagating z_index from parent to child.
        """

    def is_modal(self) -> bool:
        """
        When this container is modal, key bindings from parent containers are
        not taken into account if a user control in this container is focused.
        """
        return False

    def get_key_bindings(self) -> KeyBindingsBase | None:
        """
        Returns a :class:`.KeyBindings` object. These bindings become active when any
        user control in this container has the focus, except if any containers
        between this container and the focused user control is modal.
        """
        return None

    @abstractmethod
    def get_children(self) -> list[Container]:
        """
        Return the list of child :class:`.Container` objects.
        """
        return []


if TYPE_CHECKING:

    class MagicContainer(Protocol):
        """
        Any object that implements ``__pt_container__`` represents a container.
        """

        def __pt_container__(self) -> AnyContainer: ...


AnyContainer = Union[Container, "MagicContainer"]


def _window_too_small() -> Window:
    "Create a `Window` that displays the 'Window too small' text."
    return Window(
        FormattedTextControl(text=[("class:window-too-small", " Window too small... ")])
    )


class VerticalAlign(Enum):
    "Alignment for `HSplit`."

    TOP = "TOP"
    CENTER = "CENTER"
    BOTTOM = "BOTTOM"
    JUSTIFY = "JUSTIFY"


class HorizontalAlign(Enum):
    "Alignment for `VSplit`."

    LEFT = "LEFT"
    CENTER = "CENTER"
    RIGHT = "RIGHT"
    JUSTIFY = "JUSTIFY"


class _Split(Container):
    """
    The common parts of `VSplit` and `HSplit`.
    """

    def __init__(
        self,
        children: Sequence[AnyContainer],
        window_too_small: Container | None = None,
        padding: AnyDimension = Dimension.exact(0),
        padding_char: str | None = None,
        padding_style: str = "",
        width: AnyDimension = None,
        height: AnyDimension = None,
        z_index: int | None = None,
        modal: bool = False,
        key_bindings: KeyBindingsBase | None = None,
        style: str | Callable[[], str] = "",
    ) -> None:
        self.children = [to_container(c) for c in children]
        self.window_too_small = window_too_small or _window_too_small()
        self.padding = padding
        self.padding_char = padding_char
        self.padding_style = padding_style

        self.width = width
        self.height = height
        self.z_index = z_index

        self.modal = modal
        self.key_bindings = key_bindings
        self.style = style

    def is_modal(self) -> bool:
        return self.modal

    def get_key_bindings(self) -> KeyBindingsBase | None:
        return self.key_bindings

    def get_children(self) -> list[Container]:
        return self.children


class HSplit(_Split):
    """
    Several layouts, one stacked above/under the other. ::

        +--------------------+
        |                    |
        +--------------------+
        |                    |
        +--------------------+

    By default, this doesn't display a horizontal line between the children,
    but if this is something you need, then create a HSplit as follows::

        HSplit(children=[ ... ], padding_char='-',
               padding=1, padding_style='#ffff00')

    :param children: List of child :class:`.Container` objects.
    :param window_too_small: A :class:`.Container` object that is displayed if
        there is not enough space for all the children. By default, this is a
        "Window too small" message.
    :param align: `VerticalAlign` value.
    :param width: When given, use this width instead of looking at the children.
    :param height: When given, use this height instead of looking at the children.
    :param z_index: (int or None) When specified, this can be used to bring
        element in front of floating elements.  `None` means: inherit from parent.
    :param style: A style string.
    :param modal: ``True`` or ``False``.
    :param key_bindings: ``None`` or a :class:`.KeyBindings` object.

    :param padding: (`Dimension` or int), size to be used for the padding.
    :param padding_char: Character to be used for filling in the padding.
    :param padding_style: Style to applied to the padding.
    """

    def __init__(
        self,
        children: Sequence[AnyContainer],
        window_too_small: Container | None = None,
        align: VerticalAlign = VerticalAlign.JUSTIFY,
        padding: AnyDimension = 0,
        padding_char: str | None = None,
        padding_style: str = "",
        width: AnyDimension = None,
        height: AnyDimension = None,
        z_index: int | None = None,
        modal: bool = False,
        key_bindings: KeyBindingsBase | None = None,
        style: str | Callable[[], str] = "",
    ) -> None:
        super().__init__(
            children=children,
            window_too_small=window_too_small,
            padding=padding,
            padding_char=padding_char,
            padding_style=padding_style,
            width=width,
            height=height,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style,
        )

        self.align = align

        self._children_cache: SimpleCache[tuple[Container, ...], list[Container]] = (
            SimpleCache(maxsize=1)
        )
        self._remaining_space_window = Window()  # Dummy window.

    def preferred_width(self, max_available_width: int) -> Dimension:
        if self.width is not None:
            return to_dimension(self.width)

        if self.children:
            dimensions = [c.preferred_width(max_available_width) for c in self.children]
            return max_layout_dimensions(dimensions)
        else:
            return Dimension()

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        if self.height is not None:
            return to_dimension(self.height)

        dimensions = [
            c.preferred_height(width, max_available_height) for c in self._all_children
        ]
        return sum_layout_dimensions(dimensions)

    def reset(self) -> None:
        for c in self.children:
            c.reset()

    @property
    def _all_children(self) -> list[Container]:
        """
        List of child objects, including padding.
        """

        def get() -> list[Container]:
            result: list[Container] = []

            # Padding Top.
            if self.align in (VerticalAlign.CENTER, VerticalAlign.BOTTOM):
                result.append(Window(width=Dimension(preferred=0)))

            # The children with padding.
            for child in self.children:
                result.append(child)
                result.append(
                    Window(
                        height=self.padding,
                        char=self.padding_char,
                        style=self.padding_style,
                    )
                )
            if result:
                result.pop()

            # Padding right.
            if self.align in (VerticalAlign.CENTER, VerticalAlign.TOP):
                result.append(Window(width=Dimension(preferred=0)))

            return result

        return self._children_cache.get(tuple(self.children), get)

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """
        Render the prompt to a `Screen` instance.

        :param screen: The :class:`~prompt_toolkit.layout.screen.Screen` class
            to which the output has to be written.
        """
        sizes = self._divide_heights(write_position)
        style = parent_style + " " + to_str(self.style)
        z_index = z_index if self.z_index is None else self.z_index

        if sizes is None:
            self.window_too_small.write_to_screen(
                screen, mouse_handlers, write_position, style, erase_bg, z_index
            )
        else:
            #
            ypos = write_position.ypos
            xpos = write_position.xpos
            width = write_position.width

            # Draw child panes.
            for s, c in zip(sizes, self._all_children):
                c.write_to_screen(
                    screen,
                    mouse_handlers,
                    WritePosition(xpos, ypos, width, s),
                    style,
                    erase_bg,
                    z_index,
                )
                ypos += s

            # Fill in the remaining space. This happens when a child control
            # refuses to take more space and we don't have any padding. Adding a
            # dummy child control for this (in `self._all_children`) is not
            # desired, because in some situations, it would take more space, even
            # when it's not required. This is required to apply the styling.
            remaining_height = write_position.ypos + write_position.height - ypos
            if remaining_height > 0:
                self._remaining_space_window.write_to_screen(
                    screen,
                    mouse_handlers,
                    WritePosition(xpos, ypos, width, remaining_height),
                    style,
                    erase_bg,
                    z_index,
                )

    def _divide_heights(self, write_position: WritePosition) -> list[int] | None:
        """
        Return the heights for all rows.
        Or None when there is not enough space.
        """
        if not self.children:
            return []

        width = write_position.width
        height = write_position.height

        # Calculate heights.
        dimensions = [c.preferred_height(width, height) for c in self._all_children]

        # Sum dimensions
        sum_dimensions = sum_layout_dimensions(dimensions)

        # If there is not enough space for both.
        # Don't do anything.
        if sum_dimensions.min > height:
            return None

        # Find optimal sizes. (Start with minimal size, increase until we cover
        # the whole height.)
        sizes = [d.min for d in dimensions]

        child_generator = take_using_weights(
            items=list(range(len(dimensions))), weights=[d.weight for d in dimensions]
        )

        i = next(child_generator)

        # Increase until we meet at least the 'preferred' size.
        preferred_stop = min(height, sum_dimensions.preferred)
        preferred_dimensions = [d.preferred for d in dimensions]

        while sum(sizes) < preferred_stop:
            if sizes[i] < preferred_dimensions[i]:
                sizes[i] += 1
            i = next(child_generator)

        # Increase until we use all the available space. (or until "max")
        if not get_app().is_done:
            max_stop = min(height, sum_dimensions.max)
            max_dimensions = [d.max for d in dimensions]

            while sum(sizes) < max_stop:
                if sizes[i] < max_dimensions[i]:
                    sizes[i] += 1
                i = next(child_generator)

        return sizes


class VSplit(_Split):
    """
    Several layouts, one stacked left/right of the other. ::

        +---------+----------+
        |         |          |
        |         |          |
        +---------+----------+

    By default, this doesn't display a vertical line between the children, but
    if this is something you need, then create a HSplit as follows::

        VSplit(children=[ ... ], padding_char='|',
               padding=1, padding_style='#ffff00')

    :param children: List of child :class:`.Container` objects.
    :param window_too_small: A :class:`.Container` object that is displayed if
        there is not enough space for all the children. By default, this is a
        "Window too small" message.
    :param align: `HorizontalAlign` value.
    :param width: When given, use this width instead of looking at the children.
    :param height: When given, use this height instead of looking at the children.
    :param z_index: (int or None) When specified, this can be used to bring
        element in front of floating elements.  `None` means: inherit from parent.
    :param style: A style string.
    :param modal: ``True`` or ``False``.
    :param key_bindings: ``None`` or a :class:`.KeyBindings` object.

    :param padding: (`Dimension` or int), size to be used for the padding.
    :param padding_char: Character to be used for filling in the padding.
    :param padding_style: Style to applied to the padding.
    """

    def __init__(
        self,
        children: Sequence[AnyContainer],
        window_too_small: Container | None = None,
        align: HorizontalAlign = HorizontalAlign.JUSTIFY,
        padding: AnyDimension = 0,
        padding_char: str | None = None,
        padding_style: str = "",
        width: AnyDimension = None,
        height: AnyDimension = None,
        z_index: int | None = None,
        modal: bool = False,
        key_bindings: KeyBindingsBase | None = None,
        style: str | Callable[[], str] = "",
    ) -> None:
        super().__init__(
            children=children,
            window_too_small=window_too_small,
            padding=padding,
            padding_char=padding_char,
            padding_style=padding_style,
            width=width,
            height=height,
            z_index=z_index,
            modal=modal,
            key_bindings=key_bindings,
            style=style,
        )

        self.align = align

        self._children_cache: SimpleCache[tuple[Container, ...], list[Container]] = (
            SimpleCache(maxsize=1)
        )
        self._remaining_space_window = Window()  # Dummy window.

    def preferred_width(self, max_available_width: int) -> Dimension:
        if self.width is not None:
            return to_dimension(self.width)

        dimensions = [
            c.preferred_width(max_available_width) for c in self._all_children
        ]

        return sum_layout_dimensions(dimensions)

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        if self.height is not None:
            return to_dimension(self.height)

        # At the point where we want to calculate the heights, the widths have
        # already been decided. So we can trust `width` to be the actual
        # `width` that's going to be used for the rendering. So,
        # `divide_widths` is supposed to use all of the available width.
        # Using only the `preferred` width caused a bug where the reported
        # height was more than required. (we had a `BufferControl` which did
        # wrap lines because of the smaller width returned by `_divide_widths`.

        sizes = self._divide_widths(width)
        children = self._all_children

        if sizes is None:
            return Dimension()
        else:
            dimensions = [
                c.preferred_height(s, max_available_height)
                for s, c in zip(sizes, children)
            ]
            return max_layout_dimensions(dimensions)

    def reset(self) -> None:
        for c in self.children:
            c.reset()

    @property
    def _all_children(self) -> list[Container]:
        """
        List of child objects, including padding.
        """

        def get() -> list[Container]:
            result: list[Container] = []

            # Padding left.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.RIGHT):
                result.append(Window(width=Dimension(preferred=0)))

            # The children with padding.
            for child in self.children:
                result.append(child)
                result.append(
                    Window(
                        width=self.padding,
                        char=self.padding_char,
                        style=self.padding_style,
                    )
                )
            if result:
                result.pop()

            # Padding right.
            if self.align in (HorizontalAlign.CENTER, HorizontalAlign.LEFT):
                result.append(Window(width=Dimension(preferred=0)))

            return result

        return self._children_cache.get(tuple(self.children), get)

    def _divide_widths(self, width: int) -> list[int] | None:
        """
        Return the widths for all columns.
        Or None when there is not enough space.
        """
        children = self._all_children

        if not children:
            return []

        # Calculate widths.
        dimensions = [c.preferred_width(width) for c in children]
        preferred_dimensions = [d.preferred for d in dimensions]

        # Sum dimensions
        sum_dimensions = sum_layout_dimensions(dimensions)

        # If there is not enough space for both.
        # Don't do anything.
        if sum_dimensions.min > width:
            return None

        # Find optimal sizes. (Start with minimal size, increase until we cover
        # the whole width.)
        sizes = [d.min for d in dimensions]

        child_generator = take_using_weights(
            items=list(range(len(dimensions))), weights=[d.weight for d in dimensions]
        )

        i = next(child_generator)

        # Increase until we meet at least the 'preferred' size.
        preferred_stop = min(width, sum_dimensions.preferred)

        while sum(sizes) < preferred_stop:
            if sizes[i] < preferred_dimensions[i]:
                sizes[i] += 1
            i = next(child_generator)

        # Increase until we use all the available space.
        max_dimensions = [d.max for d in dimensions]
        max_stop = min(width, sum_dimensions.max)

        while sum(sizes) < max_stop:
            if sizes[i] < max_dimensions[i]:
                sizes[i] += 1
            i = next(child_generator)

        return sizes

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """
        Render the prompt to a `Screen` instance.

        :param screen: The :class:`~prompt_toolkit.layout.screen.Screen` class
            to which the output has to be written.
        """
        if not self.children:
            return

        children = self._all_children
        sizes = self._divide_widths(write_position.width)
        style = parent_style + " " + to_str(self.style)
        z_index = z_index if self.z_index is None else self.z_index

        # If there is not enough space.
        if sizes is None:
            self.window_too_small.write_to_screen(
                screen, mouse_handlers, write_position, style, erase_bg, z_index
            )
            return

        # Calculate heights, take the largest possible, but not larger than
        # write_position.height.
        heights = [
            child.preferred_height(width, write_position.height).preferred
            for width, child in zip(sizes, children)
        ]
        height = max(write_position.height, min(write_position.height, max(heights)))

        #
        ypos = write_position.ypos
        xpos = write_position.xpos

        # Draw all child panes.
        for s, c in zip(sizes, children):
            c.write_to_screen(
                screen,
                mouse_handlers,
                WritePosition(xpos, ypos, s, height),
                style,
                erase_bg,
                z_index,
            )
            xpos += s

        # Fill in the remaining space. This happens when a child control
        # refuses to take more space and we don't have any padding. Adding a
        # dummy child control for this (in `self._all_children`) is not
        # desired, because in some situations, it would take more space, even
        # when it's not required. This is required to apply the styling.
        remaining_width = write_position.xpos + write_position.width - xpos
        if remaining_width > 0:
            self._remaining_space_window.write_to_screen(
                screen,
                mouse_handlers,
                WritePosition(xpos, ypos, remaining_width, height),
                style,
                erase_bg,
                z_index,
            )


class FloatContainer(Container):
    """
    Container which can contain another container for the background, as well
    as a list of floating containers on top of it.

    Example Usage::

        FloatContainer(content=Window(...),
                       floats=[
                           Float(xcursor=True,
                                ycursor=True,
                                content=CompletionsMenu(...))
                       ])

    :param z_index: (int or None) When specified, this can be used to bring
        element in front of floating elements.  `None` means: inherit from parent.
        This is the z_index for the whole `Float` container as a whole.
    """

    def __init__(
        self,
        content: AnyContainer,
        floats: list[Float],
        modal: bool = False,
        key_bindings: KeyBindingsBase | None = None,
        style: str | Callable[[], str] = "",
        z_index: int | None = None,
    ) -> None:
        self.content = to_container(content)
        self.floats = floats

        self.modal = modal
        self.key_bindings = key_bindings
        self.style = style
        self.z_index = z_index

    def reset(self) -> None:
        self.content.reset()

        for f in self.floats:
            f.content.reset()

    def preferred_width(self, max_available_width: int) -> Dimension:
        return self.content.preferred_width(max_available_width)

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """
        Return the preferred height of the float container.
        (We don't care about the height of the floats, they should always fit
        into the dimensions provided by the container.)
        """
        return self.content.preferred_height(width, max_available_height)

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        style = parent_style + " " + to_str(self.style)
        z_index = z_index if self.z_index is None else self.z_index

        self.content.write_to_screen(
            screen, mouse_handlers, write_position, style, erase_bg, z_index
        )

        for number, fl in enumerate(self.floats):
            # z_index of a Float is computed by summing the z_index of the
            # container and the `Float`.
            new_z_index = (z_index or 0) + fl.z_index
            style = parent_style + " " + to_str(self.style)

            # If the float that we have here, is positioned relative to the
            # cursor position, but the Window that specifies the cursor
            # position is not drawn yet, because it's a Float itself, we have
            # to postpone this calculation. (This is a work-around, but good
            # enough for now.)
            postpone = fl.xcursor is not None or fl.ycursor is not None

            if postpone:
                new_z_index = (
                    number + 10**8
                )  # Draw as late as possible, but keep the order.
                screen.draw_with_z_index(
                    z_index=new_z_index,
                    draw_func=partial(
                        self._draw_float,
                        fl,
                        screen,
                        mouse_handlers,
                        write_position,
                        style,
                        erase_bg,
                        new_z_index,
                    ),
                )
            else:
                self._draw_float(
                    fl,
                    screen,
                    mouse_handlers,
                    write_position,
                    style,
                    erase_bg,
                    new_z_index,
                )

    def _draw_float(
        self,
        fl: Float,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        "Draw a single Float."
        # When a menu_position was given, use this instead of the cursor
        # position. (These cursor positions are absolute, translate again
        # relative to the write_position.)
        # Note: This should be inside the for-loop, because one float could
        #       set the cursor position to be used for the next one.
        cpos = screen.get_menu_position(
            fl.attach_to_window or get_app().layout.current_window
        )
        cursor_position = Point(
            x=cpos.x - write_position.xpos, y=cpos.y - write_position.ypos
        )

        fl_width = fl.get_width()
        fl_height = fl.get_height()
        width: int
        height: int
        xpos: int
        ypos: int

        # Left & width given.
        if fl.left is not None and fl_width is not None:
            xpos = fl.left
            width = fl_width
        # Left & right given -> calculate width.
        elif fl.left is not None and fl.right is not None:
            xpos = fl.left
            width = write_position.width - fl.left - fl.right
        # Width & right given -> calculate left.
        elif fl_width is not None and fl.right is not None:
            xpos = write_position.width - fl.right - fl_width
            width = fl_width
        # Near x position of cursor.
        elif fl.xcursor:
            if fl_width is None:
                width = fl.content.preferred_width(write_position.width).preferred
                width = min(write_position.width, width)
            else:
                width = fl_width

            xpos = cursor_position.x
            if xpos + width > write_position.width:
                xpos = max(0, write_position.width - width)
        # Only width given -> center horizontally.
        elif fl_width:
            xpos = int((write_position.width - fl_width) / 2)
            width = fl_width
        # Otherwise, take preferred width from float content.
        else:
            width = fl.content.preferred_width(write_position.width).preferred

            if fl.left is not None:
                xpos = fl.left
            elif fl.right is not None:
                xpos = max(0, write_position.width - width - fl.right)
            else:  # Center horizontally.
                xpos = max(0, int((write_position.width - width) / 2))

            # Trim.
            width = min(width, write_position.width - xpos)

        # Top & height given.
        if fl.top is not None and fl_height is not None:
            ypos = fl.top
            height = fl_height
        # Top & bottom given -> calculate height.
        elif fl.top is not None and fl.bottom is not None:
            ypos = fl.top
            height = write_position.height - fl.top - fl.bottom
        # Height & bottom given -> calculate top.
        elif fl_height is not None and fl.bottom is not None:
            ypos = write_position.height - fl_height - fl.bottom
            height = fl_height
        # Near cursor.
        elif fl.ycursor:
            ypos = cursor_position.y + (0 if fl.allow_cover_cursor else 1)

            if fl_height is None:
                height = fl.content.preferred_height(
                    width, write_position.height
                ).preferred
            else:
                height = fl_height

            # Reduce height if not enough space. (We can use the height
            # when the content requires it.)
            if height > write_position.height - ypos:
                if write_position.height - ypos + 1 >= ypos:
                    # When the space below the cursor is more than
                    # the space above, just reduce the height.
                    height = write_position.height - ypos
                else:
                    # Otherwise, fit the float above the cursor.
                    height = min(height, cursor_position.y)
                    ypos = cursor_position.y - height

        # Only height given -> center vertically.
        elif fl_height:
            ypos = int((write_position.height - fl_height) / 2)
            height = fl_height
        # Otherwise, take preferred height from content.
        else:
            height = fl.content.preferred_height(width, write_position.height).preferred

            if fl.top is not None:
                ypos = fl.top
            elif fl.bottom is not None:
                ypos = max(0, write_position.height - height - fl.bottom)
            else:  # Center vertically.
                ypos = max(0, int((write_position.height - height) / 2))

            # Trim.
            height = min(height, write_position.height - ypos)

        # Write float.
        # (xpos and ypos can be negative: a float can be partially visible.)
        if height > 0 and width > 0:
            wp = WritePosition(
                xpos=xpos + write_position.xpos,
                ypos=ypos + write_position.ypos,
                width=width,
                height=height,
            )

            if not fl.hide_when_covering_content or self._area_is_empty(screen, wp):
                fl.content.write_to_screen(
                    screen,
                    mouse_handlers,
                    wp,
                    style,
                    erase_bg=not fl.transparent(),
                    z_index=z_index,
                )

    def _area_is_empty(self, screen: Screen, write_position: WritePosition) -> bool:
        """
        Return True when the area below the write position is still empty.
        (For floats that should not hide content underneath.)
        """
        wp = write_position

        for y in range(wp.ypos, wp.ypos + wp.height):
            if y in screen.data_buffer:
                row = screen.data_buffer[y]

                for x in range(wp.xpos, wp.xpos + wp.width):
                    c = row[x]
                    if c.char != " ":
                        return False

        return True

    def is_modal(self) -> bool:
        return self.modal

    def get_key_bindings(self) -> KeyBindingsBase | None:
        return self.key_bindings

    def get_children(self) -> list[Container]:
        children = [self.content]
        children.extend(f.content for f in self.floats)
        return children


class Float:
    """
    Float for use in a :class:`.FloatContainer`.
    Except for the `content` parameter, all other options are optional.

    :param content: :class:`.Container` instance.

    :param width: :class:`.Dimension` or callable which returns a :class:`.Dimension`.
    :param height: :class:`.Dimension` or callable which returns a :class:`.Dimension`.

    :param left: Distance to the left edge of the :class:`.FloatContainer`.
    :param right: Distance to the right edge of the :class:`.FloatContainer`.
    :param top: Distance to the top of the :class:`.FloatContainer`.
    :param bottom: Distance to the bottom of the :class:`.FloatContainer`.

    :param attach_to_window: Attach to the cursor from this window, instead of
        the current window.
    :param hide_when_covering_content: Hide the float when it covers content underneath.
    :param allow_cover_cursor: When `False`, make sure to display the float
        below the cursor. Not on top of the indicated position.
    :param z_index: Z-index position. For a Float, this needs to be at least
        one. It is relative to the z_index of the parent container.
    :param transparent: :class:`.Filter` indicating whether this float needs to be
        drawn transparently.
    """

    def __init__(
        self,
        content: AnyContainer,
        top: int | None = None,
        right: int | None = None,
        bottom: int | None = None,
        left: int | None = None,
        width: int | Callable[[], int] | None = None,
        height: int | Callable[[], int] | None = None,
        xcursor: bool = False,
        ycursor: bool = False,
        attach_to_window: AnyContainer | None = None,
        hide_when_covering_content: bool = False,
        allow_cover_cursor: bool = False,
        z_index: int = 1,
        transparent: bool = False,
    ) -> None:
        assert z_index >= 1

        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom

        self.width = width
        self.height = height

        self.xcursor = xcursor
        self.ycursor = ycursor

        self.attach_to_window = (
            to_window(attach_to_window) if attach_to_window else None
        )

        self.content = to_container(content)
        self.hide_when_covering_content = hide_when_covering_content
        self.allow_cover_cursor = allow_cover_cursor
        self.z_index = z_index
        self.transparent = to_filter(transparent)

    def get_width(self) -> int | None:
        if callable(self.width):
            return self.width()
        return self.width

    def get_height(self) -> int | None:
        if callable(self.height):
            return self.height()
        return self.height

    def __repr__(self) -> str:
        return f"Float(content={self.content!r})"


class WindowRenderInfo:
    """
    Render information for the last render time of this control.
    It stores mapping information between the input buffers (in case of a
    :class:`~prompt_toolkit.layout.controls.BufferControl`) and the actual
    render position on the output screen.

    (Could be used for implementation of the Vi 'H' and 'L' key bindings as
    well as implementing mouse support.)

    :param ui_content: The original :class:`.UIContent` instance that contains
        the whole input, without clipping. (ui_content)
    :param horizontal_scroll: The horizontal scroll of the :class:`.Window` instance.
    :param vertical_scroll: The vertical scroll of the :class:`.Window` instance.
    :param window_width: The width of the window that displays the content,
        without the margins.
    :param window_height: The height of the window that displays the content.
    :param configured_scroll_offsets: The scroll offsets as configured for the
        :class:`Window` instance.
    :param visible_line_to_row_col: Mapping that maps the row numbers on the
        displayed screen (starting from zero for the first visible line) to
        (row, col) tuples pointing to the row and column of the :class:`.UIContent`.
    :param rowcol_to_yx: Mapping that maps (row, column) tuples representing
        coordinates of the :class:`UIContent` to (y, x) absolute coordinates at
        the rendered screen.
    """

    def __init__(
        self,
        window: Window,
        ui_content: UIContent,
        horizontal_scroll: int,
        vertical_scroll: int,
        window_width: int,
        window_height: int,
        configured_scroll_offsets: ScrollOffsets,
        visible_line_to_row_col: dict[int, tuple[int, int]],
        rowcol_to_yx: dict[tuple[int, int], tuple[int, int]],
        x_offset: int,
        y_offset: int,
        wrap_lines: bool,
    ) -> None:
        self.window = window
        self.ui_content = ui_content
        self.vertical_scroll = vertical_scroll
        self.window_width = window_width  # Width without margins.
        self.window_height = window_height

        self.configured_scroll_offsets = configured_scroll_offsets
        self.visible_line_to_row_col = visible_line_to_row_col
        self.wrap_lines = wrap_lines

        self._rowcol_to_yx = rowcol_to_yx  # row/col from input to absolute y/x
        # screen coordinates.
        self._x_offset = x_offset
        self._y_offset = y_offset

    @property
    def visible_line_to_input_line(self) -> dict[int, int]:
        return {
            visible_line: rowcol[0]
            for visible_line, rowcol in self.visible_line_to_row_col.items()
        }

    @property
    def cursor_position(self) -> Point:
        """
        Return the cursor position coordinates, relative to the left/top corner
        of the rendered screen.
        """
        cpos = self.ui_content.cursor_position
        try:
            y, x = self._rowcol_to_yx[cpos.y, cpos.x]
        except KeyError:
            # For `DummyControl` for instance, the content can be empty, and so
            # will `_rowcol_to_yx` be. Return 0/0 by default.
            return Point(x=0, y=0)
        else:
            return Point(x=x - self._x_offset, y=y - self._y_offset)

    @property
    def applied_scroll_offsets(self) -> ScrollOffsets:
        """
        Return a :class:`.ScrollOffsets` instance that indicates the actual
        offset. This can be less than or equal to what's configured. E.g, when
        the cursor is completely at the top, the top offset will be zero rather
        than what's configured.
        """
        if self.displayed_lines[0] == 0:
            top = 0
        else:
            # Get row where the cursor is displayed.
            y = self.input_line_to_visible_line[self.ui_content.cursor_position.y]
            top = min(y, self.configured_scroll_offsets.top)

        return ScrollOffsets(
            top=top,
            bottom=min(
                self.ui_content.line_count - self.displayed_lines[-1] - 1,
                self.configured_scroll_offsets.bottom,
            ),
            # For left/right, it probably doesn't make sense to return something.
            # (We would have to calculate the widths of all the lines and keep
            # double width characters in mind.)
            left=0,
            right=0,
        )

    @property
    def displayed_lines(self) -> list[int]:
        """
        List of all the visible rows. (Line numbers of the input buffer.)
        The last line may not be entirely visible.
        """
        return sorted(row for row, col in self.visible_line_to_row_col.values())

    @property
    def input_line_to_visible_line(self) -> dict[int, int]:
        """
        Return the dictionary mapping the line numbers of the input buffer to
        the lines of the screen. When a line spans several rows at the screen,
        the first row appears in the dictionary.
        """
        result: dict[int, int] = {}
        for k, v in self.visible_line_to_input_line.items():
            if v in result:
                result[v] = min(result[v], k)
            else:
                result[v] = k
        return result

    def first_visible_line(self, after_scroll_offset: bool = False) -> int:
        """
        Return the line number (0 based) of the input document that corresponds
        with the first visible line.
        """
        if after_scroll_offset:
            return self.displayed_lines[self.applied_scroll_offsets.top]
        else:
            return self.displayed_lines[0]

    def last_visible_line(self, before_scroll_offset: bool = False) -> int:
        """
        Like `first_visible_line`, but for the last visible line.
        """
        if before_scroll_offset:
            return self.displayed_lines[-1 - self.applied_scroll_offsets.bottom]
        else:
            return self.displayed_lines[-1]

    def center_visible_line(
        self, before_scroll_offset: bool = False, after_scroll_offset: bool = False
    ) -> int:
        """
        Like `first_visible_line`, but for the center visible line.
        """
        return (
            self.first_visible_line(after_scroll_offset)
            + (
                self.last_visible_line(before_scroll_offset)
                - self.first_visible_line(after_scroll_offset)
            )
            // 2
        )

    @property
    def content_height(self) -> int:
        """
        The full height of the user control.
        """
        return self.ui_content.line_count

    @property
    def full_height_visible(self) -> bool:
        """
        True when the full height is visible (There is no vertical scroll.)
        """
        return (
            self.vertical_scroll == 0
            and self.last_visible_line() == self.content_height
        )

    @property
    def top_visible(self) -> bool:
        """
        True when the top of the buffer is visible.
        """
        return self.vertical_scroll == 0

    @property
    def bottom_visible(self) -> bool:
        """
        True when the bottom of the buffer is visible.
        """
        return self.last_visible_line() == self.content_height - 1

    @property
    def vertical_scroll_percentage(self) -> int:
        """
        Vertical scroll as a percentage. (0 means: the top is visible,
        100 means: the bottom is visible.)
        """
        if self.bottom_visible:
            return 100
        else:
            return 100 * self.vertical_scroll // self.content_height

    def get_height_for_line(self, lineno: int) -> int:
        """
        Return the height of the given line.
        (The height that it would take, if this line became visible.)
        """
        if self.wrap_lines:
            return self.ui_content.get_height_for_line(
                lineno, self.window_width, self.window.get_line_prefix
            )
        else:
            return 1


class ScrollOffsets:
    """
    Scroll offsets for the :class:`.Window` class.

    Note that left/right offsets only make sense if line wrapping is disabled.
    """

    def __init__(
        self,
        top: int | Callable[[], int] = 0,
        bottom: int | Callable[[], int] = 0,
        left: int | Callable[[], int] = 0,
        right: int | Callable[[], int] = 0,
    ) -> None:
        self._top = top
        self._bottom = bottom
        self._left = left
        self._right = right

    @property
    def top(self) -> int:
        return to_int(self._top)

    @property
    def bottom(self) -> int:
        return to_int(self._bottom)

    @property
    def left(self) -> int:
        return to_int(self._left)

    @property
    def right(self) -> int:
        return to_int(self._right)

    def __repr__(self) -> str:
        return f"ScrollOffsets(top={self._top!r}, bottom={self._bottom!r}, left={self._left!r}, right={self._right!r})"


class ColorColumn:
    """
    Column for a :class:`.Window` to be colored.
    """

    def __init__(self, position: int, style: str = "class:color-column") -> None:
        self.position = position
        self.style = style


_in_insert_mode = vi_insert_mode | emacs_insert_mode


class WindowAlign(Enum):
    """
    Alignment of the Window content.

    Note that this is different from `HorizontalAlign` and `VerticalAlign`,
    which are used for the alignment of the child containers in respectively
    `VSplit` and `HSplit`.
    """

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    CENTER = "CENTER"


class Window(Container):
    """
    Container that holds a control.

    :param content: :class:`.UIControl` instance.
    :param width: :class:`.Dimension` instance or callable.
    :param height: :class:`.Dimension` instance or callable.
    :param z_index: When specified, this can be used to bring element in front
        of floating elements.
    :param dont_extend_width: When `True`, don't take up more width then the
                              preferred width reported by the control.
    :param dont_extend_height: When `True`, don't take up more width then the
                               preferred height reported by the control.
    :param ignore_content_width: A `bool` or :class:`.Filter` instance. Ignore
        the :class:`.UIContent` width when calculating the dimensions.
    :param ignore_content_height: A `bool` or :class:`.Filter` instance. Ignore
        the :class:`.UIContent` height when calculating the dimensions.
    :param left_margins: A list of :class:`.Margin` instance to be displayed on
        the left. For instance: :class:`~prompt_toolkit.layout.NumberedMargin`
        can be one of them in order to show line numbers.
    :param right_margins: Like `left_margins`, but on the other side.
    :param scroll_offsets: :class:`.ScrollOffsets` instance, representing the
        preferred amount of lines/columns to be always visible before/after the
        cursor. When both top and bottom are a very high number, the cursor
        will be centered vertically most of the time.
    :param allow_scroll_beyond_bottom: A `bool` or
        :class:`.Filter` instance. When True, allow scrolling so far, that the
        top part of the content is not visible anymore, while there is still
        empty space available at the bottom of the window. In the Vi editor for
        instance, this is possible. You will see tildes while the top part of
        the body is hidden.
    :param wrap_lines: A `bool` or :class:`.Filter` instance. When True, don't
        scroll horizontally, but wrap lines instead.
    :param get_vertical_scroll: Callable that takes this window
        instance as input and returns a preferred vertical scroll.
        (When this is `None`, the scroll is only determined by the last and
        current cursor position.)
    :param get_horizontal_scroll: Callable that takes this window
        instance as input and returns a preferred vertical scroll.
    :param always_hide_cursor: A `bool` or
        :class:`.Filter` instance. When True, never display the cursor, even
        when the user control specifies a cursor position.
    :param cursorline: A `bool` or :class:`.Filter` instance. When True,
        display a cursorline.
    :param cursorcolumn: A `bool` or :class:`.Filter` instance. When True,
        display a cursorcolumn.
    :param colorcolumns: A list of :class:`.ColorColumn` instances that
        describe the columns to be highlighted, or a callable that returns such
        a list.
    :param align: :class:`.WindowAlign` value or callable that returns an
        :class:`.WindowAlign` value. alignment of content.
    :param style: A style string. Style to be applied to all the cells in this
        window. (This can be a callable that returns a string.)
    :param char: (string) Character to be used for filling the background. This
        can also be a callable that returns a character.
    :param get_line_prefix: None or a callable that returns formatted text to
        be inserted before a line. It takes a line number (int) and a
        wrap_count and returns formatted text. This can be used for
        implementation of line continuations, things like Vim "breakindent" and
        so on.
    """

    def __init__(
        self,
        content: UIControl | None = None,
        width: AnyDimension = None,
        height: AnyDimension = None,
        z_index: int | None = None,
        dont_extend_width: FilterOrBool = False,
        dont_extend_height: FilterOrBool = False,
        ignore_content_width: FilterOrBool = False,
        ignore_content_height: FilterOrBool = False,
        left_margins: Sequence[Margin] | None = None,
        right_margins: Sequence[Margin] | None = None,
        scroll_offsets: ScrollOffsets | None = None,
        allow_scroll_beyond_bottom: FilterOrBool = False,
        wrap_lines: FilterOrBool = False,
        get_vertical_scroll: Callable[[Window], int] | None = None,
        get_horizontal_scroll: Callable[[Window], int] | None = None,
        always_hide_cursor: FilterOrBool = False,
        cursorline: FilterOrBool = False,
        cursorcolumn: FilterOrBool = False,
        colorcolumns: (
            None | list[ColorColumn] | Callable[[], list[ColorColumn]]
        ) = None,
        align: WindowAlign | Callable[[], WindowAlign] = WindowAlign.LEFT,
        style: str | Callable[[], str] = "",
        char: None | str | Callable[[], str] = None,
        get_line_prefix: GetLinePrefixCallable | None = None,
    ) -> None:
        self.allow_scroll_beyond_bottom = to_filter(allow_scroll_beyond_bottom)
        self.always_hide_cursor = to_filter(always_hide_cursor)
        self.wrap_lines = to_filter(wrap_lines)
        self.cursorline = to_filter(cursorline)
        self.cursorcolumn = to_filter(cursorcolumn)

        self.content = content or DummyControl()
        self.dont_extend_width = to_filter(dont_extend_width)
        self.dont_extend_height = to_filter(dont_extend_height)
        self.ignore_content_width = to_filter(ignore_content_width)
        self.ignore_content_height = to_filter(ignore_content_height)
        self.left_margins = left_margins or []
        self.right_margins = right_margins or []
        self.scroll_offsets = scroll_offsets or ScrollOffsets()
        self.get_vertical_scroll = get_vertical_scroll
        self.get_horizontal_scroll = get_horizontal_scroll
        self.colorcolumns = colorcolumns or []
        self.align = align
        self.style = style
        self.char = char
        self.get_line_prefix = get_line_prefix

        self.width = width
        self.height = height
        self.z_index = z_index

        # Cache for the screens generated by the margin.
        self._ui_content_cache: SimpleCache[tuple[int, int, int], UIContent] = (
            SimpleCache(maxsize=8)
        )
        self._margin_width_cache: SimpleCache[tuple[Margin, int], int] = SimpleCache(
            maxsize=1
        )

        self.reset()

    def __repr__(self) -> str:
        return f"Window(content={self.content!r})"

    def reset(self) -> None:
        self.content.reset()

        #: Scrolling position of the main content.
        self.vertical_scroll = 0
        self.horizontal_scroll = 0

        # Vertical scroll 2: this is the vertical offset that a line is
        # scrolled if a single line (the one that contains the cursor) consumes
        # all of the vertical space.
        self.vertical_scroll_2 = 0

        #: Keep render information (mappings between buffer input and render
        #: output.)
        self.render_info: WindowRenderInfo | None = None

    def _get_margin_width(self, margin: Margin) -> int:
        """
        Return the width for this margin.
        (Calculate only once per render time.)
        """

        # Margin.get_width, needs to have a UIContent instance.
        def get_ui_content() -> UIContent:
            return self._get_ui_content(width=0, height=0)

        def get_width() -> int:
            return margin.get_width(get_ui_content)

        key = (margin, get_app().render_counter)
        return self._margin_width_cache.get(key, get_width)

    def _get_total_margin_width(self) -> int:
        """
        Calculate and return the width of the margin (left + right).
        """
        return sum(self._get_margin_width(m) for m in self.left_margins) + sum(
            self._get_margin_width(m) for m in self.right_margins
        )

    def preferred_width(self, max_available_width: int) -> Dimension:
        """
        Calculate the preferred width for this window.
        """

        def preferred_content_width() -> int | None:
            """Content width: is only calculated if no exact width for the
            window was given."""
            if self.ignore_content_width():
                return None

            # Calculate the width of the margin.
            total_margin_width = self._get_total_margin_width()

            # Window of the content. (Can be `None`.)
            preferred_width = self.content.preferred_width(
                max_available_width - total_margin_width
            )

            if preferred_width is not None:
                # Include width of the margins.
                preferred_width += total_margin_width
            return preferred_width

        # Merge.
        return self._merge_dimensions(
            dimension=to_dimension(self.width),
            get_preferred=preferred_content_width,
            dont_extend=self.dont_extend_width(),
        )

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        """
        Calculate the preferred height for this window.
        """

        def preferred_content_height() -> int | None:
            """Content height: is only calculated if no exact height for the
            window was given."""
            if self.ignore_content_height():
                return None

            total_margin_width = self._get_total_margin_width()
            wrap_lines = self.wrap_lines()

            return self.content.preferred_height(
                width - total_margin_width,
                max_available_height,
                wrap_lines,
                self.get_line_prefix,
            )

        return self._merge_dimensions(
            dimension=to_dimension(self.height),
            get_preferred=preferred_content_height,
            dont_extend=self.dont_extend_height(),
        )

    @staticmethod
    def _merge_dimensions(
        dimension: Dimension | None,
        get_preferred: Callable[[], int | None],
        dont_extend: bool = False,
    ) -> Dimension:
        """
        Take the Dimension from this `Window` class and the received preferred
        size from the `UIControl` and return a `Dimension` to report to the
        parent container.
        """
        dimension = dimension or Dimension()

        # When a preferred dimension was explicitly given to the Window,
        # ignore the UIControl.
        preferred: int | None

        if dimension.preferred_specified:
            preferred = dimension.preferred
        else:
            # Otherwise, calculate the preferred dimension from the UI control
            # content.
            preferred = get_preferred()

        # When a 'preferred' dimension is given by the UIControl, make sure
        # that it stays within the bounds of the Window.
        if preferred is not None:
            if dimension.max_specified:
                preferred = min(preferred, dimension.max)

            if dimension.min_specified:
                preferred = max(preferred, dimension.min)

        # When a `dont_extend` flag has been given, use the preferred dimension
        # also as the max dimension.
        max_: int | None
        min_: int | None

        if dont_extend and preferred is not None:
            max_ = min(dimension.max, preferred)
        else:
            max_ = dimension.max if dimension.max_specified else None

        min_ = dimension.min if dimension.min_specified else None

        return Dimension(
            min=min_, max=max_, preferred=preferred, weight=dimension.weight
        )

    def _get_ui_content(self, width: int, height: int) -> UIContent:
        """
        Create a `UIContent` instance.
        """

        def get_content() -> UIContent:
            return self.content.create_content(width=width, height=height)

        key = (get_app().render_counter, width, height)
        return self._ui_content_cache.get(key, get_content)

    def _get_digraph_char(self) -> str | None:
        "Return `False`, or the Digraph symbol to be used."
        app = get_app()
        if app.quoted_insert:
            return "^"
        if app.vi_state.waiting_for_digraph:
            if app.vi_state.digraph_symbol1:
                return app.vi_state.digraph_symbol1
            return "?"
        return None

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """
        Write window to screen. This renders the user control, the margins and
        copies everything over to the absolute position at the given screen.
        """
        # If dont_extend_width/height was given. Then reduce width/height in
        # WritePosition if the parent wanted us to paint in a bigger area.
        # (This happens if this window is bundled with another window in a
        # HSplit/VSplit, but with different size requirements.)
        write_position = WritePosition(
            xpos=write_position.xpos,
            ypos=write_position.ypos,
            width=write_position.width,
            height=write_position.height,
        )

        if self.dont_extend_width():
            write_position.width = min(
                write_position.width,
                self.preferred_width(write_position.width).preferred,
            )

        if self.dont_extend_height():
            write_position.height = min(
                write_position.height,
                self.preferred_height(
                    write_position.width, write_position.height
                ).preferred,
            )

        # Draw
        z_index = z_index if self.z_index is None else self.z_index

        draw_func = partial(
            self._write_to_screen_at_index,
            screen,
            mouse_handlers,
            write_position,
            parent_style,
            erase_bg,
        )

        if z_index is None or z_index <= 0:
            # When no z_index is given, draw right away.
            draw_func()
        else:
            # Otherwise, postpone.
            screen.draw_with_z_index(z_index=z_index, draw_func=draw_func)

    def _write_to_screen_at_index(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
    ) -> None:
        # Don't bother writing invisible windows.
        # (We save some time, but also avoid applying last-line styling.)
        if write_position.height <= 0 or write_position.width <= 0:
            return

        # Calculate margin sizes.
        left_margin_widths = [self._get_margin_width(m) for m in self.left_margins]
        right_margin_widths = [self._get_margin_width(m) for m in self.right_margins]
        total_margin_width = sum(left_margin_widths + right_margin_widths)

        # Render UserControl.
        ui_content = self.content.create_content(
            write_position.width - total_margin_width, write_position.height
        )
        assert isinstance(ui_content, UIContent)

        # Scroll content.
        wrap_lines = self.wrap_lines()
        self._scroll(
            ui_content, write_position.width - total_margin_width, write_position.height
        )

        # Erase background and fill with `char`.
        self._fill_bg(screen, write_position, erase_bg)

        # Resolve `align` attribute.
        align = self.align() if callable(self.align) else self.align

        # Write body
        visible_line_to_row_col, rowcol_to_yx = self._copy_body(
            ui_content,
            screen,
            write_position,
            sum(left_margin_widths),
            write_position.width - total_margin_width,
            self.vertical_scroll,
            self.horizontal_scroll,
            wrap_lines=wrap_lines,
            highlight_lines=True,
            vertical_scroll_2=self.vertical_scroll_2,
            always_hide_cursor=self.always_hide_cursor(),
            has_focus=get_app().layout.current_control == self.content,
            align=align,
            get_line_prefix=self.get_line_prefix,
        )

        # Remember render info. (Set before generating the margins. They need this.)
        x_offset = write_position.xpos + sum(left_margin_widths)
        y_offset = write_position.ypos

        render_info = WindowRenderInfo(
            window=self,
            ui_content=ui_content,
            horizontal_scroll=self.horizontal_scroll,
            vertical_scroll=self.vertical_scroll,
            window_width=write_position.width - total_margin_width,
            window_height=write_position.height,
            configured_scroll_offsets=self.scroll_offsets,
            visible_line_to_row_col=visible_line_to_row_col,
            rowcol_to_yx=rowcol_to_yx,
            x_offset=x_offset,
            y_offset=y_offset,
            wrap_lines=wrap_lines,
        )
        self.render_info = render_info

        # Set mouse handlers.
        def mouse_handler(mouse_event: MouseEvent) -> NotImplementedOrNone:
            """
            Wrapper around the mouse_handler of the `UIControl` that turns
            screen coordinates into line coordinates.
            Returns `NotImplemented` if no UI invalidation should be done.
            """
            # Don't handle mouse events outside of the current modal part of
            # the UI.
            if self not in get_app().layout.walk_through_modal_area():
                return NotImplemented

            # Find row/col position first.
            yx_to_rowcol = {v: k for k, v in rowcol_to_yx.items()}
            y = mouse_event.position.y
            x = mouse_event.position.x

            # If clicked below the content area, look for a position in the
            # last line instead.
            max_y = write_position.ypos + len(visible_line_to_row_col) - 1
            y = min(max_y, y)
            result: NotImplementedOrNone

            while x >= 0:
                try:
                    row, col = yx_to_rowcol[y, x]
                except KeyError:
                    # Try again. (When clicking on the right side of double
                    # width characters, or on the right side of the input.)
                    x -= 1
                else:
                    # Found position, call handler of UIControl.
                    result = self.content.mouse_handler(
                        MouseEvent(
                            position=Point(x=col, y=row),
                            event_type=mouse_event.event_type,
                            button=mouse_event.button,
                            modifiers=mouse_event.modifiers,
                        )
                    )
                    break
            else:
                # nobreak.
                # (No x/y coordinate found for the content. This happens in
                # case of a DummyControl, that does not have any content.
                # Report (0,0) instead.)
                result = self.content.mouse_handler(
                    MouseEvent(
                        position=Point(x=0, y=0),
                        event_type=mouse_event.event_type,
                        button=mouse_event.button,
                        modifiers=mouse_event.modifiers,
                    )
                )

            # If it returns NotImplemented, handle it here.
            if result == NotImplemented:
                result = self._mouse_handler(mouse_event)

            return result

        mouse_handlers.set_mouse_handler_for_range(
            x_min=write_position.xpos + sum(left_margin_widths),
            x_max=write_position.xpos + write_position.width - total_margin_width,
            y_min=write_position.ypos,
            y_max=write_position.ypos + write_position.height,
            handler=mouse_handler,
        )

        # Render and copy margins.
        move_x = 0

        def render_margin(m: Margin, width: int) -> UIContent:
            "Render margin. Return `Screen`."
            # Retrieve margin fragments.
            fragments = m.create_margin(render_info, width, write_position.height)

            # Turn it into a UIContent object.
            # already rendered those fragments using this size.)
            return FormattedTextControl(fragments).create_content(
                width + 1, write_position.height
            )

        for m, width in zip(self.left_margins, left_margin_widths):
            if width > 0:  # (ConditionalMargin returns a zero width. -- Don't render.)
                # Create screen for margin.
                margin_content = render_margin(m, width)

                # Copy and shift X.
                self._copy_margin(margin_content, screen, write_position, move_x, width)
                move_x += width

        move_x = write_position.width - sum(right_margin_widths)

        for m, width in zip(self.right_margins, right_margin_widths):
            # Create screen for margin.
            margin_content = render_margin(m, width)

            # Copy and shift X.
            self._copy_margin(margin_content, screen, write_position, move_x, width)
            move_x += width

        # Apply 'self.style'
        self._apply_style(screen, write_position, parent_style)

        # Tell the screen that this user control has been painted at this
        # position.
        screen.visible_windows_to_write_positions[self] = write_position

    def _copy_body(
        self,
        ui_content: UIContent,
        new_screen: Screen,
        write_position: WritePosition,
        move_x: int,
        width: int,
        vertical_scroll: int = 0,
        horizontal_scroll: int = 0,
        wrap_lines: bool = False,
        highlight_lines: bool = False,
        vertical_scroll_2: int = 0,
        always_hide_cursor: bool = False,
        has_focus: bool = False,
        align: WindowAlign = WindowAlign.LEFT,
        get_line_prefix: Callable[[int, int], AnyFormattedText] | None = None,
    ) -> tuple[dict[int, tuple[int, int]], dict[tuple[int, int], tuple[int, int]]]:
        """
        Copy the UIContent into the output screen.
        Return (visible_line_to_row_col, rowcol_to_yx) tuple.

        :param get_line_prefix: None or a callable that takes a line number
            (int) and a wrap_count (int) and returns formatted text.
        """
        xpos = write_position.xpos + move_x
        ypos = write_position.ypos
        line_count = ui_content.line_count
        new_buffer = new_screen.data_buffer
        empty_char = _CHAR_CACHE["", ""]

        # Map visible line number to (row, col) of input.
        # 'col' will always be zero if line wrapping is off.
        visible_line_to_row_col: dict[int, tuple[int, int]] = {}

        # Maps (row, col) from the input to (y, x) screen coordinates.
        rowcol_to_yx: dict[tuple[int, int], tuple[int, int]] = {}

        def copy_line(
            line: StyleAndTextTuples,
            lineno: int,
            x: int,
            y: int,
            is_input: bool = False,
        ) -> tuple[int, int]:
            """
            Copy over a single line to the output screen. This can wrap over
            multiple lines in the output. It will call the prefix (prompt)
            function before every line.
            """
            if is_input:
                current_rowcol_to_yx = rowcol_to_yx
            else:
                current_rowcol_to_yx = {}  # Throwaway dictionary.

            # Draw line prefix.
            if is_input and get_line_prefix:
                prompt = to_formatted_text(get_line_prefix(lineno, 0))
                x, y = copy_line(prompt, lineno, x, y, is_input=False)

            # Scroll horizontally.
            skipped = 0  # Characters skipped because of horizontal scrolling.
            if horizontal_scroll and is_input:
                h_scroll = horizontal_scroll
                line = explode_text_fragments(line)
                while h_scroll > 0 and line:
                    h_scroll -= get_cwidth(line[0][1])
                    skipped += 1
                    del line[:1]  # Remove first character.

                x -= h_scroll  # When scrolling over double width character,
                # this can end up being negative.

            # Align this line. (Note that this doesn't work well when we use
            # get_line_prefix and that function returns variable width prefixes.)
            if align == WindowAlign.CENTER:
                line_width = fragment_list_width(line)
                if line_width < width:
                    x += (width - line_width) // 2
            elif align == WindowAlign.RIGHT:
                line_width = fragment_list_width(line)
                if line_width < width:
                    x += width - line_width

            col = 0
            wrap_count = 0
            for style, text, *_ in line:
                new_buffer_row = new_buffer[y + ypos]

                # Remember raw VT escape sequences. (E.g. FinalTerm's
                # escape sequences.)
                if "[ZeroWidthEscape]" in style:
                    new_screen.zero_width_escapes[y + ypos][x + xpos] += text
                    continue

                for c in text:
                    char = _CHAR_CACHE[c, style]
                    char_width = char.width

                    # Wrap when the line width is exceeded.
                    if wrap_lines and x + char_width > width:
                        visible_line_to_row_col[y + 1] = (
                            lineno,
                            visible_line_to_row_col[y][1] + x,
                        )
                        y += 1
                        wrap_count += 1
                        x = 0

                        # Insert line prefix (continuation prompt).
                        if is_input and get_line_prefix:
                            prompt = to_formatted_text(
                                get_line_prefix(lineno, wrap_count)
                            )
                            x, y = copy_line(prompt, lineno, x, y, is_input=False)

                        new_buffer_row = new_buffer[y + ypos]

                        if y >= write_position.height:
                            return x, y  # Break out of all for loops.

                    # Set character in screen and shift 'x'.
                    if x >= 0 and y >= 0 and x < width:
                        new_buffer_row[x + xpos] = char

                        # When we print a multi width character, make sure
                        # to erase the neighbors positions in the screen.
                        # (The empty string if different from everything,
                        # so next redraw this cell will repaint anyway.)
                        if char_width > 1:
                            for i in range(1, char_width):
                                new_buffer_row[x + xpos + i] = empty_char

                        # If this is a zero width characters, then it's
                        # probably part of a decomposed unicode character.
                        # See: https://en.wikipedia.org/wiki/Unicode_equivalence
                        # Merge it in the previous cell.
                        elif char_width == 0:
                            # Handle all character widths. If the previous
                            # character is a multiwidth character, then
                            # merge it two positions back.
                            for pw in [2, 1]:  # Previous character width.
                                if (
                                    x - pw >= 0
                                    and new_buffer_row[x + xpos - pw].width == pw
                                ):
                                    prev_char = new_buffer_row[x + xpos - pw]
                                    char2 = _CHAR_CACHE[
                                        prev_char.char + c, prev_char.style
                                    ]
                                    new_buffer_row[x + xpos - pw] = char2

                        # Keep track of write position for each character.
                        current_rowcol_to_yx[lineno, col + skipped] = (
                            y + ypos,
                            x + xpos,
                        )

                    col += 1
                    x += char_width
            return x, y

        # Copy content.
        def copy() -> int:
            y = -vertical_scroll_2
            lineno = vertical_scroll

            while y < write_position.height and lineno < line_count:
                # Take the next line and copy it in the real screen.
                line = ui_content.get_line(lineno)

                visible_line_to_row_col[y] = (lineno, horizontal_scroll)

                # Copy margin and actual line.
                x = 0
                x, y = copy_line(line, lineno, x, y, is_input=True)

                lineno += 1
                y += 1
            return y

        copy()

        def cursor_pos_to_screen_pos(row: int, col: int) -> Point:
            "Translate row/col from UIContent to real Screen coordinates."
            try:
                y, x = rowcol_to_yx[row, col]
            except KeyError:
                # Normally this should never happen. (It is a bug, if it happens.)
                # But to be sure, return (0, 0)
                return Point(x=0, y=0)

                # raise ValueError(
                #     'Invalid position. row=%r col=%r, vertical_scroll=%r, '
                #     'horizontal_scroll=%r, height=%r' %
                #     (row, col, vertical_scroll, horizontal_scroll, write_position.height))
            else:
                return Point(x=x, y=y)

        # Set cursor and menu positions.
        if ui_content.cursor_position:
            screen_cursor_position = cursor_pos_to_screen_pos(
                ui_content.cursor_position.y, ui_content.cursor_position.x
            )

            if has_focus:
                new_screen.set_cursor_position(self, screen_cursor_position)

                if always_hide_cursor:
                    new_screen.show_cursor = False
                else:
                    new_screen.show_cursor = ui_content.show_cursor

                self._highlight_digraph(new_screen)

            if highlight_lines:
                self._highlight_cursorlines(
                    new_screen,
                    screen_cursor_position,
                    xpos,
                    ypos,
                    width,
                    write_position.height,
                )

        # Draw input characters from the input processor queue.
        if has_focus and ui_content.cursor_position:
            self._show_key_processor_key_buffer(new_screen)

        # Set menu position.
        if ui_content.menu_position:
            new_screen.set_menu_position(
                self,
                cursor_pos_to_screen_pos(
                    ui_content.menu_position.y, ui_content.menu_position.x
                ),
            )

        # Update output screen height.
        new_screen.height = max(new_screen.height, ypos + write_position.height)

        return visible_line_to_row_col, rowcol_to_yx

    def _fill_bg(
        self, screen: Screen, write_position: WritePosition, erase_bg: bool
    ) -> None:
        """
        Erase/fill the background.
        (Useful for floats and when a `char` has been given.)
        """
        char: str | None
        if callable(self.char):
            char = self.char()
        else:
            char = self.char

        if erase_bg or char:
            wp = write_position
            char_obj = _CHAR_CACHE[char or " ", ""]

            for y in range(wp.ypos, wp.ypos + wp.height):
                row = screen.data_buffer[y]
                for x in range(wp.xpos, wp.xpos + wp.width):
                    row[x] = char_obj

    def _apply_style(
        self, new_screen: Screen, write_position: WritePosition, parent_style: str
    ) -> None:
        # Apply `self.style`.
        style = parent_style + " " + to_str(self.style)

        new_screen.fill_area(write_position, style=style, after=False)

        # Apply the 'last-line' class to the last line of each Window. This can
        # be used to apply an 'underline' to the user control.
        wp = WritePosition(
            write_position.xpos,
            write_position.ypos + write_position.height - 1,
            write_position.width,
            1,
        )
        new_screen.fill_area(wp, "class:last-line", after=True)

    def _highlight_digraph(self, new_screen: Screen) -> None:
        """
        When we are in Vi digraph mode, put a question mark underneath the
        cursor.
        """
        digraph_char = self._get_digraph_char()
        if digraph_char:
            cpos = new_screen.get_cursor_position(self)
            new_screen.data_buffer[cpos.y][cpos.x] = _CHAR_CACHE[
                digraph_char, "class:digraph"
            ]

    def _show_key_processor_key_buffer(self, new_screen: Screen) -> None:
        """
        When the user is typing a key binding that consists of several keys,
        display the last pressed key if the user is in insert mode and the key
        is meaningful to be displayed.
        E.g. Some people want to bind 'jj' to escape in Vi insert mode. But the
             first 'j' needs to be displayed in order to get some feedback.
        """
        app = get_app()
        key_buffer = app.key_processor.key_buffer

        if key_buffer and _in_insert_mode() and not app.is_done:
            # The textual data for the given key. (Can be a VT100 escape
            # sequence.)
            data = key_buffer[-1].data

            # Display only if this is a 1 cell width character.
            if get_cwidth(data) == 1:
                cpos = new_screen.get_cursor_position(self)
                new_screen.data_buffer[cpos.y][cpos.x] = _CHAR_CACHE[
                    data, "class:partial-key-binding"
                ]

    def _highlight_cursorlines(
        self, new_screen: Screen, cpos: Point, x: int, y: int, width: int, height: int
    ) -> None:
        """
        Highlight cursor row/column.
        """
        cursor_line_style = " class:cursor-line "
        cursor_column_style = " class:cursor-column "

        data_buffer = new_screen.data_buffer

        # Highlight cursor line.
        if self.cursorline():
            row = data_buffer[cpos.y]
            for x in range(x, x + width):
                original_char = row[x]
                row[x] = _CHAR_CACHE[
                    original_char.char, original_char.style + cursor_line_style
                ]

        # Highlight cursor column.
        if self.cursorcolumn():
            for y2 in range(y, y + height):
                row = data_buffer[y2]
                original_char = row[cpos.x]
                row[cpos.x] = _CHAR_CACHE[
                    original_char.char, original_char.style + cursor_column_style
                ]

        # Highlight color columns
        colorcolumns = self.colorcolumns
        if callable(colorcolumns):
            colorcolumns = colorcolumns()

        for cc in colorcolumns:
            assert isinstance(cc, ColorColumn)
            column = cc.position

            if column < x + width:  # Only draw when visible.
                color_column_style = " " + cc.style

                for y2 in range(y, y + height):
                    row = data_buffer[y2]
                    original_char = row[column + x]
                    row[column + x] = _CHAR_CACHE[
                        original_char.char, original_char.style + color_column_style
                    ]

    def _copy_margin(
        self,
        margin_content: UIContent,
        new_screen: Screen,
        write_position: WritePosition,
        move_x: int,
        width: int,
    ) -> None:
        """
        Copy characters from the margin screen to the real screen.
        """
        xpos = write_position.xpos + move_x
        ypos = write_position.ypos

        margin_write_position = WritePosition(xpos, ypos, width, write_position.height)
        self._copy_body(margin_content, new_screen, margin_write_position, 0, width)

    def _scroll(self, ui_content: UIContent, width: int, height: int) -> None:
        """
        Scroll body. Ensure that the cursor is visible.
        """
        if self.wrap_lines():
            func = self._scroll_when_linewrapping
        else:
            func = self._scroll_without_linewrapping

        func(ui_content, width, height)

    def _scroll_when_linewrapping(
        self, ui_content: UIContent, width: int, height: int
    ) -> None:
        """
        Scroll to make sure the cursor position is visible and that we maintain
        the requested scroll offset.

        Set `self.horizontal_scroll/vertical_scroll`.
        """
        scroll_offsets_bottom = self.scroll_offsets.bottom
        scroll_offsets_top = self.scroll_offsets.top

        # We don't have horizontal scrolling.
        self.horizontal_scroll = 0

        def get_line_height(lineno: int) -> int:
            return ui_content.get_height_for_line(lineno, width, self.get_line_prefix)

        # When there is no space, reset `vertical_scroll_2` to zero and abort.
        # This can happen if the margin is bigger than the window width.
        # Otherwise the text height will become "infinite" (a big number) and
        # the copy_line will spend a huge amount of iterations trying to render
        # nothing.
        if width <= 0:
            self.vertical_scroll = ui_content.cursor_position.y
            self.vertical_scroll_2 = 0
            return

        # If the current line consumes more than the whole window height,
        # then we have to scroll vertically inside this line. (We don't take
        # the scroll offsets into account for this.)
        # Also, ignore the scroll offsets in this case. Just set the vertical
        # scroll to this line.
        line_height = get_line_height(ui_content.cursor_position.y)
        if line_height > height - scroll_offsets_top:
            # Calculate the height of the text before the cursor (including
            # line prefixes).
            text_before_height = ui_content.get_height_for_line(
                ui_content.cursor_position.y,
                width,
                self.get_line_prefix,
                slice_stop=ui_content.cursor_position.x,
            )

            # Adjust scroll offset.
            self.vertical_scroll = ui_content.cursor_position.y
            self.vertical_scroll_2 = min(
                text_before_height - 1,  # Keep the cursor visible.
                line_height
                - height,  # Avoid blank lines at the bottom when scrolling up again.
                self.vertical_scroll_2,
            )
            self.vertical_scroll_2 = max(
                0, text_before_height - height, self.vertical_scroll_2
            )
            return
        else:
            self.vertical_scroll_2 = 0

        # Current line doesn't consume the whole height. Take scroll offsets into account.
        def get_min_vertical_scroll() -> int:
            # Make sure that the cursor line is not below the bottom.
            # (Calculate how many lines can be shown between the cursor and the .)
            used_height = 0
            prev_lineno = ui_content.cursor_position.y

            for lineno in range(ui_content.cursor_position.y, -1, -1):
                used_height += get_line_height(lineno)

                if used_height > height - scroll_offsets_bottom:
                    return prev_lineno
                else:
                    prev_lineno = lineno
            return 0

        def get_max_vertical_scroll() -> int:
            # Make sure that the cursor line is not above the top.
            prev_lineno = ui_content.cursor_position.y
            used_height = 0

            for lineno in range(ui_content.cursor_position.y - 1, -1, -1):
                used_height += get_line_height(lineno)

                if used_height > scroll_offsets_top:
                    return prev_lineno
                else:
                    prev_lineno = lineno
            return prev_lineno

        def get_topmost_visible() -> int:
            """
            Calculate the upper most line that can be visible, while the bottom
            is still visible. We should not allow scroll more than this if
            `allow_scroll_beyond_bottom` is false.
            """
            prev_lineno = ui_content.line_count - 1
            used_height = 0
            for lineno in range(ui_content.line_count - 1, -1, -1):
                used_height += get_line_height(lineno)
                if used_height > height:
                    return prev_lineno
                else:
                    prev_lineno = lineno
            return prev_lineno

        # Scroll vertically. (Make sure that the whole line which contains the
        # cursor is visible.
        topmost_visible = get_topmost_visible()

        # Note: the `min(topmost_visible, ...)` is to make sure that we
        # don't require scrolling up because of the bottom scroll offset,
        # when we are at the end of the document.
        self.vertical_scroll = max(
            self.vertical_scroll, min(topmost_visible, get_min_vertical_scroll())
        )
        self.vertical_scroll = min(self.vertical_scroll, get_max_vertical_scroll())

        # Disallow scrolling beyond bottom?
        if not self.allow_scroll_beyond_bottom():
            self.vertical_scroll = min(self.vertical_scroll, topmost_visible)

    def _scroll_without_linewrapping(
        self, ui_content: UIContent, width: int, height: int
    ) -> None:
        """
        Scroll to make sure the cursor position is visible and that we maintain
        the requested scroll offset.

        Set `self.horizontal_scroll/vertical_scroll`.
        """
        cursor_position = ui_content.cursor_position or Point(x=0, y=0)

        # Without line wrapping, we will never have to scroll vertically inside
        # a single line.
        self.vertical_scroll_2 = 0

        if ui_content.line_count == 0:
            self.vertical_scroll = 0
            self.horizontal_scroll = 0
            return
        else:
            current_line_text = fragment_list_to_text(
                ui_content.get_line(cursor_position.y)
            )

        def do_scroll(
            current_scroll: int,
            scroll_offset_start: int,
            scroll_offset_end: int,
            cursor_pos: int,
            window_size: int,
            content_size: int,
        ) -> int:
            "Scrolling algorithm. Used for both horizontal and vertical scrolling."
            # Calculate the scroll offset to apply.
            # This can obviously never be more than have the screen size. Also, when the
            # cursor appears at the top or bottom, we don't apply the offset.
            scroll_offset_start = int(
                min(scroll_offset_start, window_size / 2, cursor_pos)
            )
            scroll_offset_end = int(
                min(scroll_offset_end, window_size / 2, content_size - 1 - cursor_pos)
            )

            # Prevent negative scroll offsets.
            if current_scroll < 0:
                current_scroll = 0

            # Scroll back if we scrolled to much and there's still space to show more of the document.
            if (
                not self.allow_scroll_beyond_bottom()
                and current_scroll > content_size - window_size
            ):
                current_scroll = max(0, content_size - window_size)

            # Scroll up if cursor is before visible part.
            if current_scroll > cursor_pos - scroll_offset_start:
                current_scroll = max(0, cursor_pos - scroll_offset_start)

            # Scroll down if cursor is after visible part.
            if current_scroll < (cursor_pos + 1) - window_size + scroll_offset_end:
                current_scroll = (cursor_pos + 1) - window_size + scroll_offset_end

            return current_scroll

        # When a preferred scroll is given, take that first into account.
        if self.get_vertical_scroll:
            self.vertical_scroll = self.get_vertical_scroll(self)
            assert isinstance(self.vertical_scroll, int)
        if self.get_horizontal_scroll:
            self.horizontal_scroll = self.get_horizontal_scroll(self)
            assert isinstance(self.horizontal_scroll, int)

        # Update horizontal/vertical scroll to make sure that the cursor
        # remains visible.
        offsets = self.scroll_offsets

        self.vertical_scroll = do_scroll(
            current_scroll=self.vertical_scroll,
            scroll_offset_start=offsets.top,
            scroll_offset_end=offsets.bottom,
            cursor_pos=ui_content.cursor_position.y,
            window_size=height,
            content_size=ui_content.line_count,
        )

        if self.get_line_prefix:
            current_line_prefix_width = fragment_list_width(
                to_formatted_text(self.get_line_prefix(ui_content.cursor_position.y, 0))
            )
        else:
            current_line_prefix_width = 0

        self.horizontal_scroll = do_scroll(
            current_scroll=self.horizontal_scroll,
            scroll_offset_start=offsets.left,
            scroll_offset_end=offsets.right,
            cursor_pos=get_cwidth(current_line_text[: ui_content.cursor_position.x]),
            window_size=width - current_line_prefix_width,
            # We can only analyze the current line. Calculating the width off
            # all the lines is too expensive.
            content_size=max(
                get_cwidth(current_line_text), self.horizontal_scroll + width
            ),
        )

    def _mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """
        Mouse handler. Called when the UI control doesn't handle this
        particular event.

        Return `NotImplemented` if nothing was done as a consequence of this
        key binding (no UI invalidate required in that case).
        """
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self._scroll_down()
            return None
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            self._scroll_up()
            return None

        return NotImplemented

    def _scroll_down(self) -> None:
        "Scroll window down."
        info = self.render_info

        if info is None:
            return

        if self.vertical_scroll < info.content_height - info.window_height:
            if info.cursor_position.y <= info.configured_scroll_offsets.top:
                self.content.move_cursor_down()

            self.vertical_scroll += 1

    def _scroll_up(self) -> None:
        "Scroll window up."
        info = self.render_info

        if info is None:
            return

        if info.vertical_scroll > 0:
            # TODO: not entirely correct yet in case of line wrapping and long lines.
            if (
                info.cursor_position.y
                >= info.window_height - 1 - info.configured_scroll_offsets.bottom
            ):
                self.content.move_cursor_up()

            self.vertical_scroll -= 1

    def get_key_bindings(self) -> KeyBindingsBase | None:
        return self.content.get_key_bindings()

    def get_children(self) -> list[Container]:
        return []


class ConditionalContainer(Container):
    """
    Wrapper around any other container that can change the visibility. The
    received `filter` determines whether the given container should be
    displayed or not.

    :param content: :class:`.Container` instance.
    :param filter: :class:`.Filter` instance.
    """

    def __init__(self, content: AnyContainer, filter: FilterOrBool) -> None:
        self.content = to_container(content)
        self.filter = to_filter(filter)

    def __repr__(self) -> str:
        return f"ConditionalContainer({self.content!r}, filter={self.filter!r})"

    def reset(self) -> None:
        self.content.reset()

    def preferred_width(self, max_available_width: int) -> Dimension:
        if self.filter():
            return self.content.preferred_width(max_available_width)
        else:
            return Dimension.zero()

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        if self.filter():
            return self.content.preferred_height(width, max_available_height)
        else:
            return Dimension.zero()

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        if self.filter():
            return self.content.write_to_screen(
                screen, mouse_handlers, write_position, parent_style, erase_bg, z_index
            )

    def get_children(self) -> list[Container]:
        return [self.content]


class DynamicContainer(Container):
    """
    Container class that dynamically returns any Container.

    :param get_container: Callable that returns a :class:`.Container` instance
        or any widget with a ``__pt_container__`` method.
    """

    def __init__(self, get_container: Callable[[], AnyContainer]) -> None:
        self.get_container = get_container

    def _get_container(self) -> Container:
        """
        Return the current container object.

        We call `to_container`, because `get_container` can also return a
        widget with a ``__pt_container__`` method.
        """
        obj = self.get_container()
        return to_container(obj)

    def reset(self) -> None:
        self._get_container().reset()

    def preferred_width(self, max_available_width: int) -> Dimension:
        return self._get_container().preferred_width(max_available_width)

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        return self._get_container().preferred_height(width, max_available_height)

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        self._get_container().write_to_screen(
            screen, mouse_handlers, write_position, parent_style, erase_bg, z_index
        )

    def is_modal(self) -> bool:
        return False

    def get_key_bindings(self) -> KeyBindingsBase | None:
        # Key bindings will be collected when `layout.walk()` finds the child
        # container.
        return None

    def get_children(self) -> list[Container]:
        # Here we have to return the current active container itself, not its
        # children. Otherwise, we run into issues where `layout.walk()` will
        # never see an object of type `Window` if this contains a window. We
        # can't/shouldn't proxy the "isinstance" check.
        return [self._get_container()]


def to_container(container: AnyContainer) -> Container:
    """
    Make sure that the given object is a :class:`.Container`.
    """
    if isinstance(container, Container):
        return container
    elif hasattr(container, "__pt_container__"):
        return to_container(container.__pt_container__())
    else:
        raise ValueError(f"Not a container object: {container!r}")


def to_window(container: AnyContainer) -> Window:
    """
    Make sure that the given argument is a :class:`.Window`.
    """
    if isinstance(container, Window):
        return container
    elif hasattr(container, "__pt_container__"):
        return to_window(cast("MagicContainer", container).__pt_container__())
    else:
        raise ValueError(f"Not a Window object: {container!r}.")


def is_container(value: object) -> TypeGuard[AnyContainer]:
    """
    Checks whether the given value is a container object
    (for use in assert statements).
    """
    if isinstance(value, Container):
        return True
    if hasattr(value, "__pt_container__"):
        return is_container(cast("MagicContainer", value).__pt_container__())
    return False